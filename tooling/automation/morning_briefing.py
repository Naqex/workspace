"""Naqex 07:30 ICT Chief-of-Staff Morning Briefing (`OrderSend = 0`, `MT5_PROCS = 0`, `Holdout = 0`).

Composes a single deterministic, plain-Vietnamese morning command report combining:
  1. `daily_ops_briefing.py` (6-pillar operational health score, if present)
  2. `node_weekly_digest.py` (handling `rc=2` non-HEALTHY/offline gracefully without crashing!)
  3. 48-Hour Red-News Radar merging:
     - `red_news_official_2026_2027_multi_ccy.json` (`events` key, 208 6-CCY events) FIRST
     - `red_news_official_2025_2026.json` (`events_by_day` key, 62 days USD NFP/CPI/FOMC)
  4. Exact 6-Milestone Countdown (from `.tmp/offensive2_h_contract.json` + canonical fallback),
     including explicit FTMO Free Trial expiry (`08/12/2026`) log/statement harvest alert and
     Black Friday 14-day unpaid invoice payment cutoff (`14/12/2026 16:00 ICT`)
  5. Latest automation fleet summaries from `.runtime/automation/`:
     `research_radar_latest`, `prop_terms_radar_latest`, `strategy_intel_handoff_latest`,
     `watchdog_latest`, `nightly_latest`, `product_qa_latest`
  6. Optional `--notify` dispatch reusing `dispatch_alert_message` & `_scrub_secret_text` from
     `tooling/ai-engines/ops_cloud/heroku_deadman/app.py` (degrades gracefully when env vars unset)

Hard Safety Invariants:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0, MT5_PROCS_LAUNCHED = 0
  - HOLDOUT_ROWS_ANALYSED = 0, SPEND_VND = 0
  - ZERO bare `$` in generated Markdown (enforced via explicit `if ...: raise`, zero `assert`)
  - ZERO OPSEC leaks (tokens, webhooks, private IPs, Windows user paths scrubbed)
  - LF-only atomic file writes
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
MT5_PROCS_LAUNCHED: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0
SPEND_VND: int = 0

SCHEMA_VERSION: str = "naqex-morning-briefing-v1"
VN_TZ = timezone(timedelta(hours=7))

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONTRACT_PATH = ROOT / ".tmp/offensive2_h_contract.json"
DEFAULT_OUT_JSON = ROOT / ".runtime/automation/morning_briefing_latest.json"
DEFAULT_OUT_MD = ROOT / ".runtime/automation/morning_briefing_latest.md"
MULTI_CCY_CALENDAR_REL = "tooling/ai-engines/configs/calendars/red_news_official_2026_2027_multi_ccy.json"
LEGACY_CALENDAR_REL = "tooling/ai-engines/configs/calendars/red_news_official_2025_2026.json"
DEADMAN_APP_REL = "tooling/ai-engines/ops_cloud/heroku_deadman/app.py"
DAILY_OPS_REL = "tooling/ai-engines/quant_factory/daily_ops_briefing.py"
NODE_DIGEST_REL = "tooling/ai-engines/ops_cloud/node_weekly_digest.py"

AUTOMATION_SUMMARY_SPECS: tuple[tuple[str, str], ...] = (
    ("research_radar", ".runtime/automation/research_radar_latest.json"),
    ("prop_terms_radar", ".runtime/automation/prop_terms_radar_latest.json"),
    ("strategy_intel_handoff", ".runtime/automation/strategy_intel_handoff_latest.json"),
    ("watchdog", ".runtime/automation/watchdog_latest.json"),
    ("nightly", ".runtime/automation/nightly_latest.json"),
    ("product_qa", ".runtime/automation/product_qa_latest.json"),
)

# Canonical 6-Milestone schedule aligned with `.tmp/offensive2_h_contract.json`
CANONICAL_MILESTONES_6: tuple[dict[str, Any], ...] = (
    {
        "id": "bf_bill_lock",
        "label": "Black Friday Bill Lock (0 VND)",
        "timestamp": "2026-11-30T16:00:00+07:00",
        "display_time": "30/11/2026 16:00 ICT",
        "spend_vnd": 0,
        "action_vi": "Tạo hóa đơn khóa giá Black Friday ở mức 0 VND (chưa thanh toán).",
    },
    {
        "id": "holdout_v2_lock",
        "label": "Holdout v2_prospective Pre-Reg Lock",
        "timestamp": "2026-12-01T00:00:00Z",
        "display_time": "01/12/2026 (07:00 ICT)",
        "action_vi": "Chốt khóa tiền đăng ký Holdout v2_prospective (giữ 2025+ niêm phong).",
    },
    {
        "id": "nfp",
        "label": "Live NFP QUOTE_ONLY Capture",
        "timestamp": "2026-12-04T20:30:00+07:00",
        "display_time": "04/12/2026 20:30 ICT",
        "action_vi": "Thu thập dữ liệu báo giá thực địa NFP ở chế độ QUOTE_ONLY (OrderSend=0).",
    },
    {
        "id": "ftmo_free_trial_end",
        "label": "FTMO Free Trial Expiry on naqex-node1",
        "timestamp": "2026-12-08T23:59:59+07:00",
        "display_time": "08/12/2026",
        "harvest_alert": True,
        "action_vi": (
            "THU HOẠCH KHẨN trước khi hết hạn: sao lưu toàn bộ logs, naqex_exec_audit.csv "
            "và MT5 Statement trên naqex-node1!"
        ),
    },
    {
        "id": "cpi",
        "label": "Live CPI QUOTE_ONLY Capture",
        "timestamp": "2026-12-10T20:30:00+07:00",
        "display_time": "10/12/2026 20:30 ICT",
        "action_vi": "Thu thập dữ liệu báo giá thực địa CPI ở chế độ QUOTE_ONLY (OrderSend=0).",
    },
    {
        "id": "bf_14day_payment_cutoff",
        "label": "Black Friday 14-Day Unpaid Invoice Payment Cutoff",
        "timestamp": "2026-12-14T16:00:00+07:00",
        "display_time": "14/12/2026 16:00 ICT",
        "spend_vnd": 0,
        "action_vi": "Hạn chót Go/No-Go thanh toán hóa đơn 14 ngày (dừng 0 VND nếu Mốc 0 không đạt).",
    },
)

_MILESTONE_META_BY_ID: dict[str, dict[str, Any]] = {m["id"]: m for m in CANONICAL_MILESTONES_6}

_LAN_IP_RE = re.compile(r"\b(?:192" + r"\.168|10\.\d{1,3}|172\.(?:1[6-9]|2\d|3[01]))\.\d{1,3}\.\d{1,3}\b")
_CGNAT_IP_RE = re.compile(r"\b100" + r"\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b")
_WIN_USER_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]" + "Users" + r"[\\/](?!<|YOUR_|user\b|username\b)[A-Za-z0-9._-]+"
)
_HEROKU_APP_RE = re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")
_TG_HANDLE_RE = re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")
_TG_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,}:[A-Za-z0-9_-]{10,}\b")
_URL_RE = re.compile(r"https?://[^\s'\"<>]+")
_KV_SECRET_RE = re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret)=)[^\s&'\"<>]+")
_BEARER_RE = re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+")
_TIER1_EVENT_TOKENS: tuple[str, ...] = (
    "NFP",
    "CPI",
    "FOMC",
    "ECB_RATE",
    "BOE_RATE",
    "BOJ_RATE",
    "RBA_RATE",
    "BOC_RATE",
)


_DEADMAN_HELPERS_CACHE: dict[Path, tuple[Any | None, Any | None]] = {}


def _load_module_from_path(module_name: str, file_path: Path) -> Any | None:
    if not file_path.is_file():
        return None
    resolved = str(file_path.resolve())
    existing = sys.modules.get(module_name)
    if existing is not None:
        existing_file = getattr(existing, "__file__", None)
        if existing_file and str(Path(existing_file).resolve()) == resolved:
            return existing
    try:
        spec = importlib.util.spec_from_file_location(module_name, resolved)
        if spec is None or spec.loader is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = mod
        spec.loader.exec_module(mod)
        return mod
    except Exception:
        sys.modules.pop(module_name, None)
        return None


def _load_deadman_helpers(root: Path = ROOT) -> tuple[Any | None, Any | None]:
    """Reuse `dispatch_alert_message` & `_scrub_secret_text` from heroku_deadman/app.py (cached per root)."""
    app_path = (root / DEADMAN_APP_REL).resolve()
    cached = _DEADMAN_HELPERS_CACHE.get(app_path)
    if cached is not None:
        return cached
    if not app_path.is_file():
        return None, None
    mod = _load_module_from_path("_naqex_heroku_deadman_app", app_path)
    if mod is None:
        return None, None
    helpers = (getattr(mod, "dispatch_alert_message", None), getattr(mod, "_scrub_secret_text", None))
    _DEADMAN_HELPERS_CACHE[app_path] = helpers
    return helpers


def scrub_opsec_text(
    raw: Any,
    *,
    root: Path = ROOT,
    secrets: tuple[str, ...] = (),
    strip_dollar: bool = False,
) -> str:
    """Scrub secrets, URLs, tokens, private IPs, bot handles, and Windows user paths."""
    out = str(raw or "")
    _, app_scrubber = _load_deadman_helpers(root)
    if callable(app_scrubber):
        out = str(app_scrubber(out, secrets=secrets))
    else:
        for sec in sorted({str(s or "").strip() for s in secrets if str(s or "").strip()}, key=len, reverse=True):
            out = out.replace(sec, "<REDACTED>")
        out = _URL_RE.sub("<REDACTED_URL>", out)
        out = _TG_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
        out = _KV_SECRET_RE.sub(r"\1\2<REDACTED>", out)
        out = _BEARER_RE.sub(r"\1<REDACTED>", out)

    out = _LAN_IP_RE.sub("<REDACTED_IP>", out)
    out = _CGNAT_IP_RE.sub("<REDACTED_IP>", out)
    out = _WIN_USER_RE.sub("<USER_HOME>", out)
    out = _HEROKU_APP_RE.sub("<REDACTED_APP>", out)
    out = _TG_HANDLE_RE.sub("<REDACTED_BOT>", out)
    if strip_dollar:
        out = out.replace("$", "USD ")
    return out


def sanitize_value(obj: Any, *, root: Path = ROOT) -> Any:
    if isinstance(obj, dict):
        return {str(k): sanitize_value(v, root=root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [sanitize_value(v, root=root) for v in obj]
    if isinstance(obj, tuple):
        return [sanitize_value(v, root=root) for v in obj]
    if isinstance(obj, str):
        return scrub_opsec_text(obj, root=root)
    return obj


def _replace_with_retry(src: Path, dst: Path, *, retries: int = 12) -> None:
    for attempt in range(retries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if attempt + 1 >= retries:
                raise
            time.sleep(0.01 * (attempt + 1))


def atomic_write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        _replace_with_retry(tmp_path, path)
        tmp_path = None
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def resolve_python(root: Path = ROOT) -> str:
    bundled = root / ".runtime/quant-audit-v24/Scripts/python.exe"
    if bundled.is_file():
        return str(bundled)
    return sys.executable


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _parse_iso_dt(raw: str) -> datetime:
    dt = datetime.fromisoformat(str(raw).strip().replace("Z", "+00:00"))
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _format_countdown_vi(delta_sec: float) -> str:
    if delta_sec < 0:
        mins = int(abs(delta_sec) // 60)
        if mins < 60:
            return f"Đã qua {mins} phút"
        hrs = int(abs(delta_sec) // 3600)
        if hrs < 48:
            return f"Đã qua {hrs} giờ"
        days = int(abs(delta_sec) // 86400)
        return f"Đã qua {days} ngày"

    total_mins = int(delta_sec // 60)
    if total_mins < 60:
        return f"Còn {total_mins} phút"
    hrs, rem_m = divmod(total_mins, 60)
    if hrs < 24:
        return f"Còn {hrs} giờ {rem_m:02d} phút"
    days, rem_h = divmod(hrs, 24)
    return f"Còn {days} ngày {rem_h} giờ"


def build_milestones_countdown(
    *,
    now_utc: datetime,
    contract_path: Path = DEFAULT_CONTRACT_PATH,
) -> list[dict[str, Any]]:
    """Compute exact 6-Milestone Countdown from contract JSON (with canonical fallback)."""
    raw_contract = _safe_read_json(contract_path)
    contract_items = raw_contract.get("milestones_6") if isinstance(raw_contract, dict) else None
    source_rows: list[dict[str, Any]] = []
    if isinstance(contract_items, list) and len(contract_items) == 6:
        all_valid = True
        for row in contract_items:
            if not (isinstance(row, dict) and row.get("id") and row.get("timestamp")):
                all_valid = False
                break
            try:
                _parse_iso_dt(str(row["timestamp"]))
            except Exception:
                all_valid = False
                break
            source_rows.append(dict(row))
        if not all_valid:
            source_rows = []
    if len(source_rows) != 6:
        source_rows = [dict(m) for m in CANONICAL_MILESTONES_6]

    out: list[dict[str, Any]] = []
    for idx, row in enumerate(source_rows, start=1):
        mid = str(row["id"])
        meta = _MILESTONE_META_BY_ID.get(mid, {})
        ts_str = str(row["timestamp"])
        target_dt = _parse_iso_dt(ts_str)
        target_utc = target_dt.astimezone(UTC)
        target_ict = target_dt.astimezone(VN_TZ)
        delta_sec = (target_utc - now_utc).total_seconds()
        hours_rem = round(delta_sec / 3600.0, 2)
        days_rem = round(delta_sec / 86400.0, 2)

        if delta_sec < 0:
            urgency = "PASSED"
        elif delta_sec <= 24 * 3600:
            urgency = "CRITICAL_24H"
        elif delta_sec <= 72 * 3600:
            urgency = "SOON_72H"
        elif mid == "ftmo_free_trial_end" and delta_sec <= 5 * 86400:
            urgency = "HARVEST_SOON"
        else:
            urgency = "UPCOMING"

        out.append(
            {
                "index": idx,
                "id": mid,
                "label": str(meta.get("label") or row.get("label") or mid),
                "contract_label": str(row.get("label") or meta.get("label") or mid),
                "timestamp": ts_str,
                "display_time": str(meta.get("display_time") or target_ict.strftime("%d/%m/%Y %H:%M ICT")),
                "utc_iso": target_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ict_iso": target_ict.strftime("%Y-%m-%d %H:%M:%S ICT"),
                "delta_sec": int(round(delta_sec)),
                "hours_remaining": hours_rem,
                "days_remaining": days_rem,
                "countdown_vi": _format_countdown_vi(delta_sec),
                "urgency": urgency,
                "harvest_alert": bool(meta.get("harvest_alert", mid == "ftmo_free_trial_end")),
                "spend_vnd": int(row.get("spend_vnd", meta.get("spend_vnd", 0)) or 0),
                "action_vi": str(meta.get("action_vi") or ""),
            }
        )
    return out


def load_red_news_48h_radar(
    *,
    root: Path = ROOT,
    now_utc: datetime,
    window_hours: int = 48,
    horizon_limit: int = 5,
) -> dict[str, Any]:
    """Merge 6-CCY 2026-2027 calendar (`events`) FIRST with 2025-2026 USD calendar (`events_by_day`)."""
    multi_path = root / MULTI_CCY_CALENDAR_REL
    legacy_path = root / LEGACY_CALENDAR_REL

    merged_by_key: dict[tuple[int, str], dict[str, Any]] = {}
    multi_count = 0
    legacy_count = 0

    multi_raw = _safe_read_json(multi_path)
    if isinstance(multi_raw, dict) and isinstance(multi_raw.get("events"), list):
        for ev in multi_raw["events"]:
            if not isinstance(ev, dict) or ev.get("utc_ts") is None:
                continue
            try:
                ts = int(float(ev["utc_ts"]))
            except (TypeError, ValueError):
                continue
            ccy = str(ev.get("ccy") or "USD").strip().upper()
            name = str(ev.get("event") or "UNKNOWN").strip()
            multi_count += 1
            key = (ts, ccy)
            if key not in merged_by_key:
                merged_by_key[key] = {
                    "utc_ts": ts,
                    "ccy": ccy,
                    "event": name,
                    "source": str(ev.get("source") or ""),
                    "confidence": str(ev.get("confidence") or "OFFICIAL_CONFIRMED"),
                    "calendar": "multi_ccy_2026_2027",
                }
            elif name not in merged_by_key[key]["event"]:
                merged_by_key[key]["event"] = f"{merged_by_key[key]['event']} + {name}"

    legacy_raw = _safe_read_json(legacy_path)
    if isinstance(legacy_raw, dict) and isinstance(legacy_raw.get("events_by_day"), dict):
        for _day_key, day_events in legacy_raw["events_by_day"].items():
            if not isinstance(day_events, list):
                continue
            for ev in day_events:
                if not isinstance(ev, dict) or ev.get("utc_ts") is None:
                    continue
                try:
                    ts = int(float(ev["utc_ts"]))
                except (TypeError, ValueError):
                    continue
                ccy = str(ev.get("ccy") or "USD").strip().upper()
                name = str(ev.get("event") or "UNKNOWN").strip()
                legacy_count += 1
                key = (ts, ccy)
                if key not in merged_by_key:
                    merged_by_key[key] = {
                        "utc_ts": ts,
                        "ccy": ccy,
                        "event": name,
                        "source": "bls.gov/federalreserve.gov",
                        "confidence": "OFFICIAL_CONFIRMED",
                        "calendar": "official_2025_2026",
                    }
                elif name not in merged_by_key[key]["event"]:
                    merged_by_key[key]["event"] = f"{merged_by_key[key]['event']} + {name}"

    now_ts = now_utc.timestamp()
    window_sec = float(max(1, int(window_hours))) * 3600.0
    upcoming_48h: list[dict[str, Any]] = []
    next_horizon: list[dict[str, Any]] = []

    for rec in sorted(merged_by_key.values(), key=lambda r: (r["utc_ts"], r["ccy"])):
        ts = int(rec["utc_ts"])
        delta_sec = float(ts) - now_ts
        if delta_sec < -300.0:
            continue
        dt_utc = datetime.fromtimestamp(ts, UTC)
        dt_ict = dt_utc.astimezone(VN_TZ)
        ev_upper = rec["event"].upper()
        is_tier1 = any(tok in ev_upper for tok in _TIER1_EVENT_TOKENS)
        enriched = {
            "utc_ts": ts,
            "utc_iso": dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "ict_iso": dt_ict.strftime("%d/%m/%Y %H:%M ICT"),
            "ccy": rec["ccy"],
            "event": rec["event"],
            "hours_away": round(delta_sec / 3600.0, 2),
            "countdown_vi": _format_countdown_vi(delta_sec),
            "in_blackout_window": abs(delta_sec) <= 300.0,
            "is_high_impact_core": is_tier1,
            "calendar": rec["calendar"],
            "confidence": rec["confidence"],
        }
        if delta_sec <= window_sec:
            upcoming_48h.append(enriched)
        elif len(next_horizon) < horizon_limit:
            next_horizon.append(enriched)

    return {
        "window_hours": int(window_hours),
        "sources_loaded": {
            "multi_ccy_2026_2027_present": multi_path.is_file(),
            "multi_ccy_2026_2027_events": multi_count,
            "official_2025_2026_present": legacy_path.is_file(),
            "official_2025_2026_events": legacy_count,
            "merged_unique_events": len(merged_by_key),
        },
        "upcoming_48h_count": len(upcoming_48h),
        "has_48h_alert": len(upcoming_48h) > 0,
        "has_48h_tier1_us_alert": any(
            e["ccy"] == "USD" and any(k in e["event"].upper() for k in ("NFP", "CPI", "FOMC")) for e in upcoming_48h
        ),
        "upcoming_48h": upcoming_48h,
        "next_horizon": next_horizon,
    }


def collect_daily_ops_briefing(*, root: Path = ROOT, now_utc: datetime) -> dict[str, Any]:
    """Compose `daily_ops_briefing.py` in-process (read-only, zero network, graceful if absent)."""
    script_path = root / DAILY_OPS_REL
    if not script_path.is_file():
        return {"present": False, "status": "ABSENT", "detail": f"{DAILY_OPS_REL} not found"}

    mod = _load_module_from_path("_naqex_daily_ops_briefing", script_path)
    if mod is None or not hasattr(mod, "build_daily_ops_briefing"):
        return {"present": False, "status": "IMPORT_ERROR", "detail": "Unable to load build_daily_ops_briefing"}

    try:
        payload = mod.build_daily_ops_briefing(root=root, now_utc=now_utc)
        checks = payload.get("checks") if isinstance(payload.get("checks"), list) else []
        return {
            "present": True,
            "status": str(payload.get("overall_grade") or "AVAILABLE"),
            "health_score": int(payload.get("health_score", 0) or 0),
            "max_score": int(payload.get("max_score", 100) or 100),
            "status_counts": payload.get("status_counts", {}),
            "order_send_count": int(payload.get("order_send_count", 0) or 0),
            "checks_summary": [
                {
                    "id": str(c.get("id")),
                    "status": str(c.get("status")),
                    "score": int(c.get("score", 0) or 0),
                    "max_score": int(c.get("max_score", 0) or 0),
                }
                for c in checks
                if isinstance(c, dict)
            ],
        }
    except Exception as exc:
        return {
            "present": True,
            "status": "ERROR",
            "detail": scrub_opsec_text(f"{type(exc).__name__}: {exc}", root=root),
        }


def collect_node_weekly_digest(
    *,
    root: Path = ROOT,
    offline: bool = False,
    dry_run: bool = False,
    fixture_path: Path | None = None,
    timeout_sec: int = 20,
) -> dict[str, Any]:
    """Invoke `node_weekly_digest.py` and handle `rc=2` (DEGRADED/OFFLINE) gracefully without crashing."""
    script_path = root / NODE_DIGEST_REL
    if not script_path.is_file():
        return {
            "present": False,
            "overall_status": "ABSENT",
            "returncode": None,
            "handled_gracefully": True,
            "detail": f"{NODE_DIGEST_REL} not found",
        }

    py = resolve_python(root)
    if fixture_path is not None:
        cmd = [py, "-X", "utf8", str(script_path), "--offline-fixture", str(fixture_path), "--json"]
    elif offline or dry_run:
        # Read local watchdog/node1 fallback state without attempting SSH
        local_wd = _safe_read_json(root / ".runtime/ops-cloud/node1_watchdog_state.json")
        fallback_status = "OFFLINE_SKIPPED"
        if isinstance(local_wd, dict) and local_wd.get("overall_status"):
            fallback_status = str(local_wd["overall_status"])
        return {
            "present": True,
            "overall_status": fallback_status,
            "returncode": 2,
            "handled_gracefully": True,
            "ssh_attempted": False,
            "cutover_verdict": "SKIPPED_OFFLINE" if offline else "DRY_RUN",
            "detail": ("Offline/dry-run mode: skipped live SSH to naqex-node1 (rc=2 non-HEALTHY handled gracefully)"),
        }
    else:
        cmd = [py, "-X", "utf8", str(script_path), "--live-readonly", "--json"]

    creationflags = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, int(timeout_sec)),
            creationflags=creationflags,
            check=False,
        )
        rc = int(proc.returncode)
        raw_out = (proc.stdout or "").strip()
        parsed: dict[str, Any] | None = None
        if raw_out:
            try:
                obj = json.loads(raw_out)
                if isinstance(obj, dict):
                    parsed = obj
            except json.JSONDecodeError:
                start = raw_out.find("{")
                end = raw_out.rfind("}")
                if start >= 0 and end > start:
                    try:
                        obj = json.loads(raw_out[start : end + 1])
                        if isinstance(obj, dict):
                            parsed = obj
                    except json.JSONDecodeError:
                        parsed = None

        # node_weekly_digest.py returns rc=0 for HEALTHY and rc=2 for DEGRADED/OFFLINE!
        if parsed is not None and rc in (0, 2):
            return {
                "present": True,
                "overall_status": str(parsed.get("overall_status") or ("HEALTHY" if rc == 0 else "OFFLINE")),
                "returncode": rc,
                "handled_gracefully": True,
                "ssh_attempted": fixture_path is None,
                "checked_utc": parsed.get("checked_utc"),
                "cutover_verdict": parsed.get("cutover_verdict"),
                "gates_passed": parsed.get("gates_passed"),
                "gates_total": parsed.get("gates_total"),
                "failed_gates": list(parsed.get("failed_gates") or []),
                "probe_error": scrub_opsec_text(parsed.get("probe_error"), root=root)
                if parsed.get("probe_error")
                else None,
                "node": sanitize_value(parsed.get("node") or {}, root=root),
                "scoreboard": sanitize_value(parsed.get("scoreboard") or {}, root=root),
            }

        return {
            "present": True,
            "overall_status": "OFFLINE",
            "returncode": rc,
            "handled_gracefully": True,
            "ssh_attempted": fixture_path is None,
            "detail": scrub_opsec_text(proc.stderr or raw_out or f"node_weekly_digest exited rc={rc}", root=root),
        }
    except subprocess.TimeoutExpired:
        return {
            "present": True,
            "overall_status": "OFFLINE",
            "returncode": 124,
            "handled_gracefully": True,
            "ssh_attempted": fixture_path is None,
            "detail": f"node_weekly_digest timed out after {timeout_sec}s",
        }
    except OSError as exc:
        return {
            "present": True,
            "overall_status": "OFFLINE",
            "returncode": 127,
            "handled_gracefully": True,
            "ssh_attempted": fixture_path is None,
            "detail": scrub_opsec_text(exc, root=root),
        }


def collect_automation_summaries(*, root: Path = ROOT, now_utc: datetime) -> dict[str, dict[str, Any]]:
    """Read latest JSON receipts from `.runtime/automation/` gracefully (never fails when absent)."""
    summaries: dict[str, dict[str, Any]] = {}
    for key, rel_path in AUTOMATION_SUMMARY_SPECS:
        path = root / rel_path
        if not path.is_file():
            summaries[key] = {"present": False, "status": "ABSENT", "path": rel_path}
            continue
        raw = _safe_read_json(path)
        if not isinstance(raw, dict):
            summaries[key] = {"present": True, "status": "INVALID_JSON", "path": rel_path}
            continue

        ts_raw = (
            raw.get("generated_utc")
            or raw.get("generated_at_utc")
            or raw.get("checked_utc")
            or raw.get("updated_utc")
            or raw.get("timestamp_utc")
        )
        age_hours: float | None = None
        if isinstance(ts_raw, str) and ts_raw.strip():
            try:
                delta_h = (now_utc - _parse_iso_dt(ts_raw).astimezone(UTC)).total_seconds() / 3600.0
                age_hours = round(max(0.0, delta_h), 2)
            except Exception:
                age_hours = None

        status = str(
            raw.get("overall_status")
            or raw.get("status")
            or raw.get("verdict")
            or ("DRY_RUN" if raw.get("dry_run") else "AVAILABLE")
        )
        summary_entry: dict[str, Any] = {
            "present": True,
            "status": status,
            "path": rel_path,
            "generated_utc": ts_raw,
            "age_hours": age_hours,
            "order_send_count": int(raw.get("order_send_count", 0) or 0),
        }
        if isinstance(raw.get("counts"), dict):
            summary_entry["counts"] = sanitize_value(raw["counts"], root=root)
        if raw.get("items_count") is not None:
            summary_entry["items_count"] = raw.get("items_count")
        if raw.get("clean_leads_count") is not None:
            summary_entry["clean_leads_count"] = raw.get("clean_leads_count")
        if raw.get("drift_count") is not None:
            summary_entry["drift_count"] = raw.get("drift_count")
        summaries[key] = summary_entry
    return summaries


def dispatch_morning_notification(
    briefing: dict[str, Any],
    *,
    root: Path = ROOT,
    offline: bool = False,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Send compact Chief-of-Staff briefing via `dispatch_alert_message` (degrades gracefully if unset)."""
    tg_token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    tg_chat = os.environ.get("TELEGRAM_CHAT_ID", "").strip()
    webhook_url = os.environ.get("ALERT_WEBHOOK_URL", "").strip()
    configured = bool((tg_token and tg_chat) or webhook_url)

    if offline or dry_run:
        return {
            "attempted": False,
            "configured": configured,
            "sent": [],
            "errors": [],
            "skipped_reason": "offline_or_dry_run",
        }
    if not configured:
        return {
            "attempted": False,
            "configured": False,
            "sent": [],
            "errors": [],
            "skipped_reason": "env_vars_unset",
        }

    dispatch_fn, _ = _load_deadman_helpers(root)
    if not callable(dispatch_fn):
        return {
            "attempted": False,
            "configured": configured,
            "sent": [],
            "errors": ["dispatch_alert_message_unavailable"],
        }

    next_ms = next((m for m in briefing.get("milestones_6", []) if m.get("delta_sec", -1) >= 0), None)
    rn = briefing.get("red_news_48h", {})
    nd = briefing.get("node_digest", {})
    ops = briefing.get("daily_ops", {})

    gen_ict = briefing.get("generated_ict")
    ov_st = briefing.get("overall_status")
    ops_score = ops.get("health_score", "N/A")
    ops_max = ops.get("max_score", 100)
    ops_st = ops.get("status")
    nd_st = nd.get("overall_status")
    rn_cnt = int(rn.get("upcoming_48h_count", 0))

    plain_lines = [
        f"[NAQEX MORNING BRIEFING] {gen_ict} | Status={ov_st} | OrderSend=0",
        f"DailyOps={ops_score}/{ops_max} ({ops_st}) | Node1={nd_st}",
        f"RedNews48h={rn_cnt} events",
    ]
    if next_ms:
        plain_lines.append(f"NextMilestone={next_ms['label']} ({next_ms['display_time']} | {next_ms['countdown_vi']})")
    plain_text = scrub_opsec_text(
        " | ".join(plain_lines),
        root=root,
        secrets=(tg_token, webhook_url),
        strip_dollar=True,
    )

    esc_score = f"{html.escape(str(ops_score))}/{html.escape(str(ops_max))}"
    esc_nd = html.escape(str(nd_st))
    html_lines = [
        f"<b>NAQEX MORNING BRIEFING</b> · <code>{html.escape(str(gen_ict))}</code>",
        f"• Trạng thái: <code>{html.escape(str(ov_st))}</code> · <code>OrderSend=0</code>",
        f"• Daily Ops: <code>{esc_score}</code> · Node1: <code>{esc_nd}</code>",
        f"• Tin đỏ 48h: <code>{rn_cnt}</code> sự kiện",
    ]
    if next_ms:
        esc_lbl = html.escape(str(next_ms["label"]))
        esc_cd = html.escape(str(next_ms["countdown_vi"]))
        html_lines.append(f"• Mốc kế tiếp: <b>{esc_lbl}</b> ({esc_cd})")
    html_text = scrub_opsec_text(
        "\n".join(html_lines),
        root=root,
        secrets=(tg_token, webhook_url),
        strip_dollar=True,
    )

    try:
        res = dispatch_fn(
            plain_text,
            html_text=html_text,
            telegram_bot_token=tg_token,
            telegram_chat_id=tg_chat,
            webhook_url=webhook_url,
        )
        if not isinstance(res, dict):
            return {"attempted": True, "configured": configured, "sent": [], "errors": ["unexpected_dispatch_result"]}
        safe_errors = [
            scrub_opsec_text(e, root=root, secrets=(tg_token, webhook_url)) for e in list(res.get("errors") or [])
        ]
        return {
            "attempted": True,
            "configured": bool(res.get("configured", configured)),
            "sent": list(res.get("sent") or []),
            "errors": safe_errors,
        }
    except Exception as exc:
        return {
            "attempted": True,
            "configured": configured,
            "sent": [],
            "errors": [scrub_opsec_text(exc, root=root, secrets=(tg_token, webhook_url))],
        }


def render_morning_briefing_md(payload: dict[str, Any], *, root: Path = ROOT) -> str:
    """Render plain-Vietnamese Chief-of-Staff Morning Briefing Markdown (strictly 0 bare `$`, 0 OPSEC leaks)."""
    rn = payload["red_news_48h"]
    ops = payload["daily_ops"]
    nd = payload["node_digest"]
    milestones = payload["milestones_6"]
    fleet = payload["automation_summaries"]

    next_active = next((m for m in milestones if m["delta_sec"] >= 0), milestones[-1])
    ftmo_ms = next((m for m in milestones if m["id"] == "ftmo_free_trial_end"), None)

    lines = [
        "---",
        "doc_type: morning-briefing",
        f"schema: {payload['schema']}",
        f"generated_utc: {payload['generated_utc']}",
        f'generated_ict: "{payload["generated_ict"]}"',
        f"overall_status: {payload['overall_status']}",
        f"order_send_count: {payload['order_send_count']}",
        f"holdout_rows_analysed: {payload['holdout_rows_analysed']}",
        f"spend_vnd: {payload['spend_vnd']}",
        "---",
        "",
        f"# Bản Tin Sáng Chief-of-Staff — Naqex (`{payload['generated_ict']}`)",
        "",
        (
            f"**Kết luận nhanh:** Trạng thái `{payload['overall_status']}` · `OrderSend = 0` · `0 VND` · "
            f"Mốc gần nhất: **{next_active['label']}** "
            f"(`{next_active['display_time']}` — **{next_active['countdown_vi']}**)."
        ),
        "",
        "## 1. Đếm Ngược 6 Mốc Chiến Lược (Milestones)",
        "",
        "| # | Mốc chiến lược | Thời điểm | Đếm ngược | Mức ưu tiên | Hành động trọng tâm |",
        "| :---: | --- | --- | --- | :---: | --- |",
    ]

    for m in milestones:
        row_md = (
            f"| {m['index']} | **{m['label']}** | `{m['display_time']}` "
            f"| `{m['countdown_vi']}` | `{m['urgency']}` | {m['action_vi']} |"
        )
        lines.append(row_md)

    if ftmo_ms is not None:
        ftmo_banner = (
            f"> **CẢNH BÁO THU HOẠCH FTMO FREE TRIAL "
            f"(`{ftmo_ms['display_time']}` — {ftmo_ms['countdown_vi']}):** "
            "Xuất đầy đủ toàn bộ logs, `naqex_exec_audit.csv`, và MT5 Statement "
            "trên `naqex-node1` TRƯỚC khi tài khoản hết hạn."
        )
        lines.extend(["", ftmo_banner])

    src_rn = rn["sources_loaded"]
    rn_src_line = (
        f"- **Nguồn lịch đã hợp nhất:** `2026-2027 6-CCY` (`{src_rn['multi_ccy_2026_2027_events']}` sự kiện) "
        f"+ `2025-2026 USD` (`{src_rn['official_2025_2026_events']}` sự kiện) -> "
        f"**`{src_rn['merged_unique_events']}`** sự kiện duy nhất."
    )
    lines.extend(["", "## 2. Radar Tin Đỏ 48 Giờ (6-CCY + USD NFP/CPI/FOMC)", "", rn_src_line])

    if rn["upcoming_48h"]:
        lines.extend(
            [
                f"- **CẢNH BÁO 48H:** Có **`{rn['upcoming_48h_count']}`** sự kiện tin đỏ trong 48 giờ tới!",
                "",
                "| Thời điểm ICT | Tiền tệ | Sự kiện | Đếm ngược | Blackout ±5m |",
                "| --- | :---: | --- | --- | :---: |",
            ]
        )
        for ev in rn["upcoming_48h"]:
            blk = "CẤM GIAO DỊCH" if ev["in_blackout_window"] else "Theo dõi"
            lines.append(f"| `{ev['ict_iso']}` | `{ev['ccy']}` | `{ev['event']}` | `{ev['countdown_vi']}` | `{blk}` |")
    else:
        lines.append("- **Trạng thái 48h tới:** `0` sự kiện tin đỏ (an toàn lịch tin trong 48 giờ tới).")

    if rn["next_horizon"]:
        lines.extend(["", "**Lịch tin đỏ gần nhất tiếp theo (> 48h):**", ""])
        for ev in rn["next_horizon"][:5]:
            lines.append(f"- `{ev['ict_iso']}` · `{ev['ccy']}` · `{ev['event']}` ({ev['countdown_vi']})")

    lines.extend(
        [
            "",
            "## 3. Sức Khỏe Vận Hành & `naqex-node1`",
            "",
            (
                f"- **Daily Ops Briefing:** `{ops.get('health_score', 'N/A')}/{ops.get('max_score', 100)}` "
                f"(`{ops.get('status')}`)"
                if ops.get("present")
                else f"- **Daily Ops Briefing:** `{ops.get('status')}`"
            ),
            (
                f"- **`naqex-node1` Weekly Digest:** `{nd.get('overall_status')}` "
                f"(rc=`{nd.get('returncode')}`, cutover=`{nd.get('cutover_verdict', 'N/A')}`, "
                f"xử lý an toàn không crash=`{nd.get('handled_gracefully')}`)"
            ),
            "",
            "## 4. Tóm Tắt Hệ Thống Tự Động Hóa (`.runtime/automation/`)",
            "",
            "| Module | Trạng thái | Cập nhật UTC | Độ trễ (giờ) | OrderSend |",
            "| --- | :---: | --- | ---: | :---: |",
        ]
    )

    for key, _rel in AUTOMATION_SUMMARY_SPECS:
        info = fleet.get(key, {"present": False, "status": "ABSENT"})
        upd = str(info.get("generated_utc") or "chưa có")
        age = f"{info['age_hours']:.2f}" if info.get("age_hours") is not None else "—"
        os_cnt = info.get("order_send_count", 0) if info.get("present") else 0
        lines.append(f"| `{key}` | `{info.get('status')}` | `{upd}` | `{age}` | `{os_cnt}` |")

    notif = payload.get("notification", {})
    notif_line = (
        f"- **Thông báo tự động (`--notify`):** `attempted={notif.get('attempted')}` · "
        f"`configured={notif.get('configured')}` · `sent={len(notif.get('sent') or [])}`."
    )
    lines.extend(
        [
            "",
            "## 5. Bước Kế Tiếp (< 2 phút)",
            "",
            notif_line,
            f"- **Hành động ưu tiên ngay:** {next_active['action_vi']}",
            "",
        ]
    )

    md_raw = "\n".join(lines)
    md_clean = scrub_opsec_text(md_raw, root=root, strip_dollar=True)
    # Fail-closed guard (works identically under `python -O`, zero bare `assert`!)
    if "$" in md_clean:
        raise ValueError("Formatting guard failed: bare dollar character detected in morning briefing Markdown")
    return md_clean


def build_morning_briefing(
    *,
    root: Path = ROOT,
    contract_path: Path | None = None,
    out_json: Path | None = DEFAULT_OUT_JSON,
    out_md: Path | None = DEFAULT_OUT_MD,
    node_fixture: Path | None = None,
    notify: bool = False,
    offline: bool = False,
    dry_run: bool = False,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Assemble full Chief-of-Staff morning briefing JSON + Markdown and persist atomically."""
    now = now_utc or datetime.now(UTC)
    now_ict = now.astimezone(VN_TZ)
    c_path = contract_path if contract_path is not None else (root / ".tmp/offensive2_h_contract.json")

    daily_ops = collect_daily_ops_briefing(root=root, now_utc=now)
    node_digest = collect_node_weekly_digest(
        root=root,
        offline=offline,
        dry_run=dry_run,
        fixture_path=node_fixture,
    )
    red_news_48h = load_red_news_48h_radar(root=root, now_utc=now, window_hours=48)
    milestones_6 = build_milestones_countdown(now_utc=now, contract_path=c_path)
    automation_summaries = collect_automation_summaries(root=root, now_utc=now)

    # Determine honest overall status
    ops_grade = str(daily_ops.get("status") or "")
    node_st = str(node_digest.get("overall_status") or "")
    has_fail_fleet = any(str(v.get("status")) == "FAIL" for v in automation_summaries.values() if v.get("present"))

    if ops_grade == "CRITICAL_FAIL_CLOSED" or has_fail_fleet:
        overall_status = "CRITICAL_ATTENTION"
    elif dry_run:
        overall_status = "DRY_RUN_READY"
    elif red_news_48h["has_48h_tier1_us_alert"] or node_st in ("DEGRADED", "OFFLINE"):
        overall_status = "AMBER_WATCH"
    else:
        overall_status = "GREEN_READY"

    payload: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_utc": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "generated_ict": now_ict.strftime("%Y-%m-%d %H:%M:%S ICT"),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "mt5_procs_launched": MT5_PROCS_LAUNCHED,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "spend_vnd": SPEND_VND,
        "offline": bool(offline),
        "dry_run": bool(dry_run),
        "overall_status": overall_status,
        "daily_ops": daily_ops,
        "node_digest": node_digest,
        "red_news_48h": red_news_48h,
        "milestones_6": milestones_6,
        "automation_summaries": automation_summaries,
        "notification": {
            "attempted": False,
            "configured": False,
            "sent": [],
            "errors": [],
            "skipped_reason": "notify_not_requested",
        },
    }

    if notify:
        payload["notification"] = dispatch_morning_notification(
            payload,
            root=root,
            offline=offline,
            dry_run=dry_run,
        )

    sanitized_payload = sanitize_value(payload, root=root)
    md_text = render_morning_briefing_md(sanitized_payload, root=root)

    if out_json is not None:
        atomic_write_text(out_json, json.dumps(sanitized_payload, indent=2, ensure_ascii=False) + "\n")
    if out_md is not None:
        atomic_write_text(out_md, md_text)

    return sanitized_payload


def make_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Naqex 07:30 Chief-of-Staff Morning Briefing (OrderSend=0, 0 bare dollar).",
    )
    ap.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    ap.add_argument("--contract", type=Path, default=None, help="Path to offensive2_h_contract.json")
    ap.add_argument("--out-json", type=Path, default=None, help="Output path for JSON receipt")
    ap.add_argument("--out-md", type=Path, default=None, help="Output path for Vietnamese Markdown briefing")
    ap.add_argument(
        "--node-fixture",
        type=Path,
        default=None,
        help="Optional offline JSON fixture for node_weekly_digest",
    )
    ap.add_argument(
        "--now-utc",
        type=str,
        default=None,
        help="Optional ISO-8601 UTC timestamp override for replay/tests",
    )
    ap.add_argument(
        "--notify",
        action="store_true",
        help="Dispatch Telegram/webhook notification if configured and online",
    )
    ap.add_argument("--offline", action="store_true", help="Skip live SSH & network alert dispatch")
    ap.add_argument(
        "--dry-run",
        action="store_true",
        help="Run read-only composition without sending live notifications",
    )
    ap.add_argument("--json", action="store_true", dest="as_json", help="Emit full JSON payload to stdout")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = make_parser().parse_args(argv)
    now_dt = _parse_iso_dt(args.now_utc).astimezone(UTC) if args.now_utc else None
    default_json = args.root / ".runtime/automation/morning_briefing_latest.json"
    default_md = args.root / ".runtime/automation/morning_briefing_latest.md"
    out_json = args.out_json if args.out_json is not None else default_json
    out_md = args.out_md if args.out_md is not None else default_md

    payload = build_morning_briefing(
        root=args.root,
        contract_path=args.contract,
        out_json=out_json,
        out_md=out_md,
        node_fixture=args.node_fixture,
        notify=args.notify,
        offline=args.offline,
        dry_run=args.dry_run,
        now_utc=now_dt,
    )
    if args.as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        rn = payload["red_news_48h"]
        nd = payload["node_digest"]
        next_ms = next((m for m in payload["milestones_6"] if m["delta_sec"] >= 0), payload["milestones_6"][-1])
        print(
            f"[morning_briefing] status={payload['overall_status']} node1={nd.get('overall_status')} "
            f"(rc={nd.get('returncode')}) red_news_48h={rn['upcoming_48h_count']} "
            f"next_milestone={next_ms['id']}({next_ms['countdown_vi']}) OrderSend={ORDER_SEND_COUNT}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
