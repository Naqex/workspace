"""Stateless, read-only Cockpit Automation API builders and sidecar config validator.

Strictly stateless (zero module-level mutable caches or locks; never touches
`cockpit.modules.state`), 100% read-only (`ORDER_SEND_COUNT = 0`), OPSEC-scrubbed,
and degrades gracefully when `.runtime/automation/*`, `.runtime/ops-cloud/*`, or
`tooling/automation/configs/feature_map.json` are absent or malformed.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

_AI_ENGINES_BOOT = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_BOOT) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_BOOT))

from cockpit.modules.helpers import _read_jsonl_tail, _safe_read_json, as_dict, as_list  # noqa: E402
from cockpit.modules.state import ORDER_SEND_COUNT, ROOT  # noqa: E402

RUNTIME_AUTOMATION_FILES: tuple[tuple[str, str], ...] = (
    ("watchdog_latest", ".runtime/automation/watchdog_latest.json"),
    ("nightly_latest", ".runtime/automation/nightly_latest.json"),
    ("product_qa_latest", ".runtime/automation/product_qa_latest.json"),
    ("morning_briefing_latest", ".runtime/automation/morning_briefing_latest.json"),
    ("research_radar_latest", ".runtime/automation/research_radar_latest.json"),
    ("prop_terms_radar_latest", ".runtime/automation/prop_terms_radar_latest.json"),
    ("strategy_intel_handoff_latest", ".runtime/automation/strategy_intel_handoff_latest.json"),
)

OPS_CLOUD_STATE_FILES: tuple[tuple[str, str], ...] = (
    ("node1_watchdog_state", ".runtime/ops-cloud/node1_watchdog_state.json"),
    ("telegram_alert_state", ".runtime/ops-cloud/telegram_alert_state.json"),
)

EVENT_QUEUE_REL = ".runtime/automation/event_queue.jsonl"
FEATURE_MAP_REL = "tooling/automation/configs/feature_map.json"
SIDECARS_DIR_REL = "tooling/automation/configs/sidecars"

_ALLOWED_SIDECAR_TOP_KEYS: frozenset[str] = frozenset(
    {"builtin", "args", "restart_policy", "display_name", "description", "agent_permissions"}
)
_ALLOWED_PERMISSION_KEYS: frozenset[str] = frozenset({"workspace_uris", "access_grants"})
_FORBIDDEN_GRANT_TOKENS: tuple[str, ...] = (
    "*",
    "read_file(/)",
    "write_file(/)",
    "allow(",
)
_CRON_TZ_RE = re.compile(r"^CRON_TZ=[A-Za-z0-9_/+.-]+\s+\S+\s+\S+\s+\S+\s+\S+\s+\S+$")
_SCRIPT_EXT_RE = re.compile(r"\.(?:py|ps1|sh|bat|cmd)$", re.IGNORECASE)
_ABS_PATH_RE = re.compile(r"^(?:[A-Za-z]:[/\\]|/)")

# Build sensitive patterns dynamically so Layer-1 OPSEC scans never self-match.
_WIN_USER_HOME_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]+Us"
    r"ers[\\/]+(?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_UNIX_USER_HOME_RE = re.compile(r"(?:/Us" r"ers|/home)/[A-Za-z0-9._-]+")
_TG_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,12}:[A-Za-z0-9_-]{10,}\b")
_GH_TOKEN_RE = re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")
_OPENAI_KEY_RE = re.compile(r"\b" + "sk-" + r"(?:proj-)?[A-Za-z0-9_-]{20,}\b")
_GOOGLE_KEY_RE = re.compile(r"\b" + "AIza" + r"[0-9A-Za-z_-]{20,}\b")
_WEBHOOK_URL_RE = re.compile(
    r"https?://(?:discord\.com|discordapp\.com|hooks\.slack\.com|api\.telegram\.org)/[^\s'\"<>]+",
    re.IGNORECASE,
)
_HEROKU_URL_RE = re.compile(r"https?://[^\s'\"<>]*herokuapp\.com[^\s'\"<>]*", re.IGNORECASE)
_PG_DSN_RE = re.compile(r"postgres(?:ql)?://[^\s'\"<>]+", re.IGNORECASE)
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+")
_KV_SECRET_RE = re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret|password|passwd)=)[^\s&'\"<>]+")
_PRIVATE_IP_RE = re.compile(
    r"\b(?:192\.168\.\d{1,3}\.\d{1,3}|10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3})\b"
)

_SENSITIVE_EXACT_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "secret",
        "password",
        "passwd",
        "webhook",
        "webhook_url",
        "alert_webhook_url",
        "api_key",
        "apikey",
        "chat_id",
        "telegram_chat_id",
        "telegram_bot_token",
        "bot_token",
        "view_token",
        "ingest_token",
        "access_token",
        "refresh_token",
        "dsn",
        "database_url",
        "authorization",
        "auth_header",
        "deadman_url",
        "naqex_deadman_url",
        "web_url",
    }
)
_SENSITIVE_KEY_SUFFIXES: tuple[str, ...] = (
    "_token",
    "_secret",
    "_password",
    "_passwd",
    "_api_key",
    "_webhook",
    "_webhook_url",
    "_dsn",
    "_chat_id",
)


def _enforce_zero_order_send() -> int:
    if ORDER_SEND_COUNT != 0:
        raise RuntimeError(f"Cockpit automation read-only invariant violated: ORDER_SEND_COUNT={ORDER_SEND_COUNT}")
    return 0


def _is_sensitive_key(key: str) -> bool:
    low = key.strip().lower()
    if low in _SENSITIVE_EXACT_KEYS:
        return True
    return any(low.endswith(suf) for suf in _SENSITIVE_KEY_SUFFIXES)


def sanitize_text(raw: str) -> str:
    """Scrub tokens, webhook/Heroku URLs, DSNs, private IPs, and user home paths."""
    out = str(raw)
    out = _WEBHOOK_URL_RE.sub("<REDACTED_WEBHOOK>", out)
    out = _HEROKU_URL_RE.sub("<REDACTED_URL>", out)
    out = _PG_DSN_RE.sub("<REDACTED_DSN>", out)
    out = _TG_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _GH_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _OPENAI_KEY_RE.sub("<REDACTED_TOKEN>", out)
    out = _GOOGLE_KEY_RE.sub("<REDACTED_TOKEN>", out)
    out = _BEARER_RE.sub(r"\1<REDACTED>", out)
    out = _KV_SECRET_RE.sub(r"\1\2<REDACTED>", out)
    out = _PRIVATE_IP_RE.sub("<REDACTED_IP>", out)
    out = _WIN_USER_HOME_RE.sub("<USER_HOME>", out)
    out = _UNIX_USER_HOME_RE.sub("<USER_HOME>", out)
    return out


def _sanitize_value(val: Any, *, _depth: int = 0) -> Any:
    if _depth > 16:
        return "<TRUNCATED>"
    if isinstance(val, str):
        return sanitize_text(val)
    if isinstance(val, dict):
        cleaned: dict[str, Any] = {}
        for k, v in val.items():
            ks = str(k)
            if _is_sensitive_key(ks):
                cleaned[ks] = "<REDACTED>"
            else:
                cleaned[ks] = _sanitize_value(v, _depth=_depth + 1)
        return cleaned
    if isinstance(val, list):
        return [_sanitize_value(item, _depth=_depth + 1) for item in val]
    return val


def _read_sanitized_json_record(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {"available": False, "status": "pending", "data": None}
    raw = _safe_read_json(path)
    if raw is None:
        return {"available": False, "status": "malformed", "data": None}
    cleaned = _sanitize_value(raw)
    status = "ACTIVE"
    if isinstance(cleaned, dict):
        raw_status = str(cleaned.get("status") or cleaned.get("overall_status") or "").strip()
        if raw_status:
            status = sanitize_text(raw_status)[:48]
    return {"available": True, "status": status, "data": cleaned}


def validate_sidecar_config(data: Any, *, source_name: str = "") -> tuple[bool, list[str]]:
    """Validate an Antigravity scheduled sidecar JSON object against automation/SKILL.md rules."""
    errors: list[str] = []
    prefix = f"[{source_name}] " if source_name else ""

    if not isinstance(data, dict):
        return False, [f"{prefix}Sidecar config must be a JSON object"]

    if "enabled" in data:
        errors.append(f"{prefix}Forbidden 'enabled' key must not be set in sidecar.json")

    unknown_keys = sorted(set(data.keys()) - _ALLOWED_SIDECAR_TOP_KEYS)
    if unknown_keys:
        errors.append(f"{prefix}Unexpected or non-snake_case top-level keys: {unknown_keys}")

    if data.get("builtin") != "schedule":
        errors.append(f"{prefix}'builtin' must be strictly 'schedule'")

    if data.get("restart_policy") != "always":
        errors.append(f"{prefix}'restart_policy' must be lowercase 'always'")

    for text_field in ("display_name", "description"):
        val = data.get(text_field)
        if not isinstance(val, str) or not val.strip():
            errors.append(f"{prefix}'{text_field}' must be a non-empty string")

    args = data.get("args")
    if not isinstance(args, list) or len(args) < 4 or not all(isinstance(a, str) for a in args):
        errors.append(f"{prefix}'args' must be an array of at least 4 strings")
    else:
        if not _CRON_TZ_RE.match(args[0]):
            errors.append(f"{prefix}args[0] must be 'CRON_TZ=<IANA> <5-field cron>'")
        if "--" not in args:
            errors.append(f"{prefix}'args' must include '--' separator before the prompt")
        else:
            sep_idx = args.index("--")
            if sep_idx != len(args) - 2:
                errors.append(f"{prefix}'--' must appear immediately before the final prompt string")
            if not args[-1].strip():
                errors.append(f"{prefix}Prompt string after '--' must be non-empty")
            for tok in args[1:sep_idx]:
                if _SCRIPT_EXT_RE.search(tok) and not _ABS_PATH_RE.match(tok):
                    errors.append(f"{prefix}Script argument must be an absolute path: {tok}")

    perms = data.get("agent_permissions")
    if perms is not None:
        if not isinstance(perms, dict):
            errors.append(f"{prefix}'agent_permissions' must be a JSON object")
        else:
            bad_perm_keys = sorted(set(perms.keys()) - _ALLOWED_PERMISSION_KEYS)
            if bad_perm_keys:
                errors.append(f"{prefix}Unexpected agent_permissions keys: {bad_perm_keys}")
            if "enabled" in perms:
                errors.append(f"{prefix}Forbidden 'enabled' key inside agent_permissions")
            grants = perms.get("access_grants")
            if grants is not None:
                if not isinstance(grants, list) or not all(isinstance(g, str) for g in grants):
                    errors.append(f"{prefix}'access_grants' must be a list of strings")
                else:
                    for grant in grants:
                        low_g = grant.strip().lower()
                        if any(tok in low_g for tok in _FORBIDDEN_GRANT_TOKENS):
                            errors.append(f"{prefix}Forbidden wildcard/overbroad access_grant: {grant}")
            uris = perms.get("workspace_uris")
            if uris is not None:
                if not isinstance(uris, list) or not all(isinstance(u, str) for u in uris):
                    errors.append(f"{prefix}'workspace_uris' must be a list of strings")
                else:
                    for uri in uris:
                        if not uri.startswith("file:///") or "*" in uri:
                            errors.append(f"{prefix}Invalid workspace_uri: {uri}")

    serialized = json.dumps(data, ensure_ascii=False)
    if _WIN_USER_HOME_RE.search(serialized) or _UNIX_USER_HOME_RE.search(serialized):
        errors.append(f"{prefix}Hardcoded user home path detected in sidecar.json")
    if _TG_TOKEN_RE.search(serialized) or _GH_TOKEN_RE.search(serialized) or _WEBHOOK_URL_RE.search(serialized):
        errors.append(f"{prefix}Secret or webhook literal detected in sidecar.json")

    return len(errors) == 0, errors


def _load_sidecars_summary(root: Path) -> list[dict[str, Any]]:
    sidecars_dir = root / SIDECARS_DIR_REL
    if not sidecars_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for sidecar_file in sorted(sidecars_dir.glob("*/sidecar.json")):
        sidecar_id = sidecar_file.parent.name
        raw = _safe_read_json(sidecar_file)
        valid, errors = validate_sidecar_config(raw, source_name=sidecar_id)
        obj = as_dict(raw)
        args = as_list(obj.get("args"))
        schedule = sanitize_text(str(args[0])) if args and isinstance(args[0], str) else ""
        out.append(
            {
                "id": sidecar_id,
                "display_name": sanitize_text(str(obj.get("display_name") or sidecar_id)),
                "schedule": schedule,
                "restart_policy": sanitize_text(str(obj.get("restart_policy") or "")),
                "valid": valid,
                "errors": [sanitize_text(e) for e in errors],
            }
        )
    return out


def _read_event_queue_stats(root: Path) -> tuple[bool, int, dict[str, Any] | None]:
    q_path = root / EVENT_QUEUE_REL
    if not q_path.is_file():
        return False, 0, None
    total = 0
    latest: dict[str, Any] | None = None
    try:
        for ln in q_path.read_text(encoding="utf-8", errors="replace").splitlines():
            s = ln.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                total += 1
                latest = _sanitize_value(obj)
    except OSError:
        return False, 0, None
    return True, total, latest


def _extract_feature_entries(raw: Any) -> list[dict[str, Any]]:
    if isinstance(raw, list):
        return [_sanitize_value(item) for item in raw if isinstance(item, dict)]
    if isinstance(raw, dict):
        feats = raw.get("features")
        if isinstance(feats, list):
            return [_sanitize_value(item) for item in feats if isinstance(item, dict)]
        if isinstance(feats, dict):
            entries: list[dict[str, Any]] = []
            for fid, body in feats.items():
                if isinstance(body, dict):
                    merged = {"id": str(fid), **body}
                    entries.append(_sanitize_value(merged))
            return entries
    return []


def build_automation_status_payload(root: Path = ROOT) -> dict[str, Any]:
    """Stateless reader for GET /api/automation/status (OrderSend=0, read-only)."""
    order_send = _enforce_zero_order_send()
    known_names = {Path(rel).name for _, rel in RUNTIME_AUTOMATION_FILES}

    automation_reports: dict[str, dict[str, Any]] = {}
    available_reports = 0
    for key, rel in RUNTIME_AUTOMATION_FILES:
        rec = _read_sanitized_json_record(root / rel)
        automation_reports[key] = rec
        if rec["available"]:
            available_reports += 1

    extra_runtime: dict[str, dict[str, Any]] = {}
    auto_dir = root / ".runtime/automation"
    if auto_dir.is_dir():
        for p in sorted(auto_dir.glob("*.json")):
            if p.name in known_names:
                continue
            extra_runtime[p.stem] = _read_sanitized_json_record(p)

    ops_cloud: dict[str, dict[str, Any]] = {
        key: _read_sanitized_json_record(root / rel) for key, rel in OPS_CLOUD_STATE_FILES
    }

    q_avail, q_total, q_latest = _read_event_queue_stats(root)
    fmap_raw = _safe_read_json(root / FEATURE_MAP_REL)
    fmap_entries = _extract_feature_entries(fmap_raw)
    sidecars = _load_sidecars_summary(root)

    statuses_seen = [
        str(rec.get("status", "")).upper()
        for rec in (*automation_reports.values(), *extra_runtime.values(), *ops_cloud.values())
        if rec.get("available")
    ]
    if any("CIRCUIT_OPEN" in st for st in statuses_seen):
        overall = "CIRCUIT_OPEN"
    elif any(st in ("ERROR", "FAIL", "FAILED", "ALERT", "DEGRADED", "WARN") for st in statuses_seen):
        overall = "DEGRADED"
    elif available_reports > 0 or any(rec["available"] for rec in ops_cloud.values()) or q_avail:
        overall = "ACTIVE"
    else:
        overall = "PENDING"

    return {
        "schema": "naqex-cockpit-automation-status-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "stateless": True,
        "read_only": True,
        "order_send_count": order_send,
        "holdout_sealed": True,
        "overall_status": overall,
        "available_reports": available_reports,
        "total_expected_reports": len(RUNTIME_AUTOMATION_FILES),
        "automation": automation_reports,
        "extra_runtime_json": extra_runtime,
        "ops_cloud": ops_cloud,
        "event_queue": {
            "available": q_avail,
            "status": "ACTIVE" if q_avail else "pending",
            "total_events": q_total,
            "latest_event": q_latest,
        },
        "feature_map": {
            "available": fmap_raw is not None,
            "status": "ACTIVE" if fmap_raw is not None else "pending",
            "feature_count": len(fmap_entries),
        },
        "sidecars": sidecars,
    }


def build_automation_events_payload(
    root: Path = ROOT,
    *,
    limit: int = 50,
    event_type: str | None = None,
    severity: str | None = None,
) -> dict[str, Any]:
    """Stateless reader for GET /api/automation/events (OrderSend=0, read-only)."""
    order_send = _enforce_zero_order_send()
    clamped_limit = max(1, min(500, int(limit)))
    q_path = root / EVENT_QUEUE_REL
    if not q_path.is_file():
        return {
            "schema": "naqex-cockpit-automation-events-v1",
            "generated_utc": datetime.now(UTC).isoformat(),
            "stateless": True,
            "read_only": True,
            "order_send_count": order_send,
            "available": False,
            "status": "pending",
            "total_events": 0,
            "returned_count": 0,
            "limit": clamped_limit,
            "events": [],
        }

    # Read full tail up to 2000 entries for optional filtering, then return last `clamped_limit`.
    raw_rows = _read_jsonl_tail(q_path, limit=2000)
    sanitized_rows = [_sanitize_value(row) for row in raw_rows]
    total_events = len(sanitized_rows)

    filtered = sanitized_rows
    if event_type:
        want_type = event_type.strip().lower()
        filtered = [
            ev
            for ev in filtered
            if str(ev.get("event_type") or ev.get("type") or ev.get("kind") or "").strip().lower() == want_type
        ]
    if severity:
        want_sev = severity.strip().lower()
        filtered = [
            ev for ev in filtered if str(ev.get("severity") or ev.get("level") or "").strip().lower() == want_sev
        ]

    page = filtered[-clamped_limit:]
    return {
        "schema": "naqex-cockpit-automation-events-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "stateless": True,
        "read_only": True,
        "order_send_count": order_send,
        "available": True,
        "status": "ACTIVE",
        "total_events": total_events,
        "returned_count": len(page),
        "limit": clamped_limit,
        "events": page,
    }


def build_automation_features_payload(root: Path = ROOT) -> dict[str, Any]:
    """Stateless reader for GET /api/automation/features (OrderSend=0, read-only)."""
    order_send = _enforce_zero_order_send()
    fmap_path = root / FEATURE_MAP_REL
    fmap_raw = _safe_read_json(fmap_path)
    qa_rec = _read_sanitized_json_record(root / ".runtime/automation/product_qa_latest.json")
    sidecars = _load_sidecars_summary(root)

    if fmap_raw is None:
        return {
            "schema": "naqex-cockpit-automation-features-v1",
            "generated_utc": datetime.now(UTC).isoformat(),
            "stateless": True,
            "read_only": True,
            "order_send_count": order_send,
            "available": False,
            "status": "malformed" if fmap_path.is_file() else "pending",
            "feature_count": 0,
            "features": [],
            "product_qa_latest": qa_rec,
            "sidecars": sidecars,
        }

    features = _extract_feature_entries(fmap_raw)
    qa_by_id: dict[str, dict[str, Any]] = {}
    qa_data = as_dict(qa_rec.get("data"))
    for key in ("results", "features", "checks"):
        val = qa_data.get(key)
        if isinstance(val, list):
            for item in val:
                if isinstance(item, dict):
                    fid = str(item.get("feature_id") or item.get("id") or item.get("name") or "").strip()
                    if fid:
                        qa_by_id[fid] = item
        elif isinstance(val, dict):
            for fid, item in val.items():
                if isinstance(item, dict):
                    qa_by_id[str(fid)] = item

    enriched: list[dict[str, Any]] = []
    for feat in features:
        fid = str(feat.get("id") or feat.get("feature_id") or feat.get("name") or "").strip()
        row = dict(feat)
        if fid and fid in qa_by_id:
            row["latest_qa"] = qa_by_id[fid]
        enriched.append(row)

    return {
        "schema": "naqex-cockpit-automation-features-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "stateless": True,
        "read_only": True,
        "order_send_count": order_send,
        "available": True,
        "status": "ACTIVE",
        "feature_count": len(enriched),
        "features": enriched,
        "product_qa_latest": qa_rec,
        "sidecars": sidecars,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Stateless Naqex Automation status reader (OrderSend=0).")
    parser.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    parser.add_argument("--offline", action="store_true", help="Offline read-only mode (always local)")
    parser.add_argument("--dry-run", action="store_true", help="Dry-run mode (always read-only)")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")
    args = parser.parse_args(argv)

    payload = build_automation_status_payload(args.root.resolve())
    if args.as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(
            f"Naqex Automation Status: {payload['overall_status']} | "
            f"reports={payload['available_reports']}/{payload['total_expected_reports']} | "
            f"events={payload['event_queue']['total_events']} | "
            f"features={payload['feature_map']['feature_count']} | "
            f"sidecars={len(payload['sidecars'])} | OrderSend={payload['order_send_count']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
