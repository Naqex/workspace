"""Daily / Weekly End-to-End Live-Ops Pipeline & Objective Traffic-Light Decision Matrix (OPS-4).

Single-command read-only orchestrator wiring all verified Naqex Live-Ops subsystems:
  1. Daily Statement Reconciler (`quant_factory.daily_statement_reconciler`)
  2. Live TCA & Slippage-Drift Monitor (`quant_factory.prop_live_tca_monitor` + `quant_factory.tca_reconcile`)
  3. Live Alpha Decay CUSUM + Wald SPRT (`quant_factory.live_decay_monitor`)
  4. Blameless Postmortem Discrepancy Classifier (`quant_factory.postmortem_gen`)
  5. Feed Health, US/EU DST & Calendar TTL Guard (`quant_factory.live_ops.feed_dst_news_guard`, OPS-1)
  6. Account Phase Preflight & Inactivity / Compliance (`quant_factory.live_ops.account_phase_preflight`, OPS-2)
  7. 1-to-1 Python-vs-MT5 Parity Forensics & Geometry (`quant_factory.live_ops.live_parity_forensics`, OPS-6)
  8. Heartbeat Watchdog (`quant_factory.ops_monitor`)
  9. Offline Pre-Checkout & Node Digest (`ops_cloud.ftmo_pre_checkout_guard`, `ops_cloud.node_weekly_digest`)

Objective Traffic Light & Action Matrix:
  - `GREEN` (`KEEP_CURRENT_RISK_1_0X`):
      0 parity bugs (`GHOST/MISSED/LOT_DRIFT`), 0 statement orphans, TCA healthy,
      Calendar TTL > 14d, CUSUM/SPRT intact, heartbeat fresh, feed & compliance clean.
  - `AMBER` (`THROTTLE_TO_0_5X_WATCH`):
      Calendar TTL <= 14d OR Inactivity >= 21d OR `Regime Shift` / `AMBER_WATCH_REDUCE_SIZE`
      OR elevated slippage/friction 1.5x-2.0x (ZERO bot bugs, ZERO SPRT rejection).
  - `RED` (`HALT_BOT_ENABLE_DRYRUN_INVESTIGATE`):
      ANY `BOT_BUG_GHOST_TRADE` / `BOT_BUG_MISSED_TRADE` / `LOT_OR_SL_DRIFT` (regardless of PnL)
      OR statement orphan / swap!=0 violation (Standard) OR Calendar TTL <= 3d/expired
      OR `Execution TCA Bug` RED OR `Alpha Decay` (`RED_HALT_ALPHA_DECAY` / SPRT rejection)
      OR stale/unhealthy heartbeat OR RED feed/compliance/pre-checkout failure.

HARD SAFETY & OPSEC INVARIANTS (`[ARCH-02]`, `G02`, `G12`, `G16`):
  - Strictly offline and read-only: `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - NEVER imports `MetaTrader5`, NEVER initiates live SSH writes, NEVER mutates input snapshots.
  - ZERO bare `assert` statements (`[ARCH-02]`).
  - Strict Layer-1 OPSEC redaction: 0 raw account logins, tickets, IPv4/IPv6 addresses,
    Windows user profile paths, secrets, URLs, or bare dollar signs in digest or JSON receipt.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import re
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from ops_cloud import ftmo_pre_checkout_guard as pre_checkout_mod  # noqa: E402
from ops_cloud import node_cutover_dryrun as cutover_mod  # noqa: E402
from ops_cloud import node_weekly_digest as node_digest_mod  # noqa: E402
from quant_core.red_news import RedNewsEvent, load_calendar_events  # noqa: E402
from quant_core.tca import (  # noqa: E402
    canonical_payload_sha256,
    load_exec_audit_csv,
    load_quote_tape,
    normalize_symbol_alias,
    write_atomic_sha256_json,
)

from quant_factory.daily_statement_reconciler import reconcile_daily_statement  # noqa: E402
from quant_factory.live_decay_monitor import evaluate_live_decay  # noqa: E402
from quant_factory.live_ops.account_phase_preflight import (  # noqa: E402
    check_multi_account_compliance,
    normalize_firm_profile,
    validate_account_deployment,
)
from quant_factory.live_ops.feed_dst_news_guard import (  # noqa: E402
    EXTENDED_CALENDAR_SCHEMA,
    TTL_AMBER_DAYS_DEFAULT,
    TTL_RED_DAYS_DEFAULT,
    CalendarTtlStatus,
    ExtendedRedNewsEvent,
    FeedHealthAssessment,
    check_calendar_ttl,
    evaluate_feed_health,
    load_extended_calendar,
    load_merged_live_calendar,
    match_symbol_event_codes,
    resolve_dst_snapshot,
    resolve_firm_daily_reset_utc,
)
from quant_factory.live_ops.live_parity_forensics import (  # noqa: E402
    ANTI_OVERFIT_MIN_LIVE_TRADES,
    PARITY_BOT_BUG_GHOST_TRADE,
    PARITY_BOT_BUG_MISSED_TRADE,
    PARITY_EXECUTION_FRICTION_DRIFT,
    PARITY_LEGITIMATE_GUARD_BLOCK,
    PARITY_LOT_OR_SL_DRIFT,
    PARITY_MATCH_CLEAN,
    aggregate_mt5_deals_by_position,
    build_weekly_forensics_report,
    load_decision_blackbox_jsonl,
    load_exec_audit_records,
    load_v103_shadow_csv,
)
from quant_factory.ops_monitor import inspect_heartbeat  # noqa: E402
from quant_factory.postmortem_gen import classify_discrepancy  # noqa: E402
from quant_factory.prop_live_tca_monitor import evaluate_live_tca  # noqa: E402
from quant_factory.prop_live_tca_monitor import sanitize_path_label as tca_sanitize_path_label  # noqa: E402
from quant_factory.prop_live_tca_monitor import sanitize_text as tca_sanitize_text  # noqa: E402
from quant_factory.tca_reconcile import compute_tca_report  # noqa: E402

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0

PIPELINE_SCHEMA: Final[str] = "naqex-daily-live-ops-pipeline-v1"

TRAFFIC_GREEN: Final[str] = "GREEN"
TRAFFIC_AMBER: Final[str] = "AMBER"
TRAFFIC_RED: Final[str] = "RED"

ACTION_KEEP_1_0X: Final[str] = "KEEP_CURRENT_RISK_1_0X"
ACTION_THROTTLE_0_5X: Final[str] = "THROTTLE_TO_0_5X_WATCH"
ACTION_HALT_DRYRUN: Final[str] = "HALT_BOT_ENABLE_DRYRUN_INVESTIGATE"

TRAFFIC_ACTION_MATRIX: Final[dict[str, dict[str, Any]]] = {
    TRAFFIC_GREEN: {
        "traffic_light": TRAFFIC_GREEN,
        "action": ACTION_KEEP_1_0X,
        "risk_multiplier": 1.0,
        "dry_run_required": False,
        "halt_required": False,
        "label_vi": "XANH - GIU NGUYEN MUC RUI RO 1.0x",
        "label_en": "GREEN - KEEP CURRENT RISK 1.0x",
    },
    TRAFFIC_AMBER: {
        "traffic_light": TRAFFIC_AMBER,
        "action": ACTION_THROTTLE_0_5X,
        "risk_multiplier": 0.5,
        "dry_run_required": False,
        "halt_required": False,
        "label_vi": "VANG - HA RUI RO XUONG 0.5x & THEO DOI CHAT",
        "label_en": "AMBER - THROTTLE TO 0.5x & WATCH",
    },
    TRAFFIC_RED: {
        "traffic_light": TRAFFIC_RED,
        "action": ACTION_HALT_DRYRUN,
        "risk_multiplier": 0.0,
        "dry_run_required": True,
        "halt_required": True,
        "label_vi": "DO - DUNG BOT NGAY, BAT DRY-RUN & DIEU TRA",
        "label_en": "RED - HALT BOT, ENABLE DRY-RUN & INVESTIGATE",
    },
}

DEFAULT_TCA_FRICTION_AMBER: Final[float] = 1.5
DEFAULT_TCA_FRICTION_RED: Final[float] = 2.0
DEFAULT_VOL_HIGH_THRESH: Final[float] = 1.60
DEFAULT_VOL_LOW_THRESH: Final[float] = 0.50

# Strict OPSEC redaction patterns (built cleanly without concrete private IPs or tokens)
_IPV4_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![0-9A-Za-z\.])(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?(?![0-9A-Za-z\.])"
)
_IPV6_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:(?<![0-9A-Fa-f:])(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}(?![0-9A-Fa-f:])"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F:]{1,20}"
    r"|::[0-9a-fA-F:]{1,20})"
)
_WIN_USER_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]Users[\\/](?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+(?:[\\/][^\s'\"<>]*)?"
)
_TAG_ID_RE: Final[re.Pattern[str]] = re.compile(
    r"(?<![A-Za-z0-9])(deal|ord|tk|pos|ticket|order|login|account(?:_login)?)\s*([:=#])\s*#?[A-Za-z0-9_-]{4,}",
    re.IGNORECASE,
)
_SEVEN_PLUS_DIGIT_RE: Final[re.Pattern[str]] = re.compile(r"(?<![A-Za-z0-9\-\.])\d{7,12}(?![A-Za-z0-9\-\.])")
_SECRET_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("GITHUB_TOKEN", re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")),
    ("OPENAI_KEY", re.compile(r"\b" + "sk-" + r"(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\b" + "AIza" + r"[0-9A-Za-z_-]{30,}\b")),
    ("TELEGRAM_TOKEN", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")),
    ("WEBHOOK_URL", re.compile(r"https?://(?:discord\.com|discordapp\.com)/api/webhooks/\S+", re.IGNORECASE)),
    ("CRED_DSN", re.compile(r"postgres(?:ql)?://[^\s:/@<]+:[^\s/@<]{4,}@[^\s/<]+", re.IGNORECASE)),
    ("HEROKU_APP", re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")),
    ("TG_HANDLE", re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")),
)

_FORBIDDEN_PAYLOAD_KEYS: Final[frozenset[str]] = frozenset(
    {
        "account_login",
        "expected_login",
        "actual_login",
        "login",
        "statement_logins",
        "audit_logins",
        "ticket",
        "deal_id",
        "deal_ids",
        "order_id",
        "position_id",
        "ip",
        "wan_ip",
        "public_ip",
        "router_ip",
        "lan_ip",
        "tailscale_ip",
        "hop_ips",
        "raw_hops",
        "host",
        "_ssh_host",
        "isp",
        "org",
        "asn",
        "password",
        "passwd",
        "token",
        "secret",
        "webhook",
        "api_key",
        "bearer",
    }
)


# ---------------------------------------------------------------------------
# Strict OPSEC & Timestamp Utilities
# ---------------------------------------------------------------------------
def _parse_now_utc(now_utc: datetime | str | int | float | None) -> datetime:
    if now_utc is None:
        return datetime.now(UTC).replace(microsecond=0)
    if isinstance(now_utc, datetime):
        if now_utc.tzinfo is None or now_utc.utcoffset() is None:
            raise ValueError(f"now_utc must be timezone-aware (UTC recommended), got naive datetime {now_utc!r}")
        return now_utc.astimezone(UTC)
    if isinstance(now_utc, bool):
        raise ValueError(f"now_utc cannot be bool, got {now_utc!r}")
    if isinstance(now_utc, (int, float)):
        fv = float(now_utc)
        if not math.isfinite(fv) or fv <= 0.0:
            raise ValueError(f"now_utc numeric timestamp must be finite > 0, got {now_utc!r}")
        if fv >= 1.0e12:
            fv = fv / 1000.0
        return datetime.fromtimestamp(fv, tz=UTC)
    if isinstance(now_utc, str):
        s = now_utc.strip()
        if not s:
            raise ValueError("now_utc string cannot be blank")
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None or dt.utcoffset() is None:
            dt = dt.replace(tzinfo=UTC)
        return dt.astimezone(UTC)
    raise ValueError(f"Unsupported now_utc type: {type(now_utc).__name__}")


def _harvest_logins(obj: Any, bucket: set[str]) -> None:
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in ("account_login", "expected_login", "actual_login", "login"):
                if isinstance(v, int) and not isinstance(v, bool) and v > 0:
                    bucket.add(str(v))
                elif isinstance(v, str) and v.strip().isdigit() and len(v.strip()) >= 5:
                    bucket.add(v.strip())
            elif kl in ("statement_logins", "audit_logins") and isinstance(v, Sequence) and not isinstance(v, str):
                for item in v:
                    if isinstance(item, int) and not isinstance(item, bool) and item > 0:
                        bucket.add(str(item))
                    elif isinstance(item, str) and item.strip().isdigit() and len(item.strip()) >= 5:
                        bucket.add(item.strip())
            else:
                _harvest_logins(v, bucket)
    elif isinstance(obj, Sequence) and not isinstance(obj, (str, bytes, bytearray)):
        for item in obj:
            _harvest_logins(item, bucket)


def redact_opsec_text(text: str, *, known_logins: Iterable[str] = ()) -> str:
    """Strip logins, ticket/deal IDs, IPv4/IPv6, Windows user paths, secrets, URLs & bare `$`."""
    out = tca_sanitize_text(str(text))
    out = _WIN_USER_PATH_RE.sub("<WIN_USER_PATH>", out)
    for tag, rx in _SECRET_PATTERNS:
        out = rx.sub(f"[REDACTED_{tag}]", out)
    out = _TAG_ID_RE.sub(lambda m: f"{m.group(1)}{m.group(2)}[REDACTED_ID]", out)
    out = _IPV6_RE.sub("[REDACTED_IPV6]", out)
    out = _IPV4_RE.sub("[REDACTED_IPV4]", out)
    for login_tok in sorted({str(x).strip() for x in known_logins if str(x).strip()}, key=len, reverse=True):
        if login_tok.isdigit() and len(login_tok) >= 5:
            out = re.sub(rf"(?<!\d){re.escape(login_tok)}(?!\d)", "[REDACTED_LOGIN]", out)
    out = _SEVEN_PLUS_DIGIT_RE.sub("[REDACTED_ID]", out)
    out = out.replace("$", "USD ")
    return out


def redact_opsec_payload(obj: Any, *, known_logins: Iterable[str] = ()) -> Any:
    """Recursively sanitize any JSON-serializable payload and enforce finite numeric values."""
    logins = tuple(known_logins)
    if isinstance(obj, str):
        return redact_opsec_text(obj, known_logins=logins)
    if isinstance(obj, bool) or obj is None:
        return obj
    if isinstance(obj, int):
        return obj
    if isinstance(obj, float):
        return obj if math.isfinite(obj) else None
    if isinstance(obj, Path):
        return redact_opsec_text(tca_sanitize_path_label(obj) or obj.name, known_logins=logins)
    if isinstance(obj, Mapping):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            kl = str(k).lower()
            if kl in _FORBIDDEN_PAYLOAD_KEYS:
                continue
            cleaned[redact_opsec_text(str(k), known_logins=logins)] = redact_opsec_payload(v, known_logins=logins)
        return cleaned
    if isinstance(obj, (list, tuple)):
        return [redact_opsec_payload(item, known_logins=logins) for item in obj]
    return redact_opsec_text(str(obj), known_logins=logins)


def _to_finite_float_or_none(val: Any) -> float | None:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    fv = float(val)
    return fv if math.isfinite(fv) else None


def _load_json_if_path(val: Any) -> Any:
    if isinstance(val, (str, Path)):
        p = Path(val)
        return json.loads(p.read_text(encoding="utf-8"))
    return val


def _load_returns_array(src: Sequence[float] | np.ndarray | Path | str) -> np.ndarray:
    """Load a 1D return/R series from ndarray, sequence, JSON, or CSV (strictly read-only)."""
    if isinstance(src, np.ndarray):
        arr = np.asarray(src, dtype=np.float64).ravel()
        return arr[np.isfinite(arr)]
    if isinstance(src, (str, Path)):
        p = Path(src)
        if not p.is_file():
            raise FileNotFoundError(f"Returns series file not found: {p.name}")
        if p.suffix.lower() == ".json":
            doc = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(doc, Mapping):
                for key in ("returns", "r_values", "net_r", "values", "series", "pnl"):
                    if key in doc and isinstance(doc[key], Sequence):
                        doc = doc[key]
                        break
            arr = np.asarray(doc, dtype=np.float64).ravel()
            return arr[np.isfinite(arr)]
        vals: list[float] = []
        with p.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                return np.asarray([], dtype=np.float64)
            preferred = ("net_R", "net_r", "gross_R", "gross_r", "r", "return", "ret", "pnl_usd", "pnl", "value")
            col = next((c for c in preferred if c in reader.fieldnames), reader.fieldnames[0])
            for row in reader:
                raw_v = str(row.get(col) or "").strip()
                if not raw_v:
                    continue
                fv = float(raw_v)
                if math.isfinite(fv):
                    vals.append(fv)
        return np.asarray(vals, dtype=np.float64)
    arr = np.asarray(list(src), dtype=np.float64).ravel()
    return arr[np.isfinite(arr)]


def _finding(code: str, severity: str, subsystem: str, message: str) -> dict[str, str]:
    return {
        "code": str(code),
        "severity": str(severity),
        "subsystem": str(subsystem),
        "message": str(message),
    }


# ---------------------------------------------------------------------------
# Subsystem Adapters (Strictly Reusing Verified Modules — Zero Re-Implementation)
# ---------------------------------------------------------------------------
def _materialize_enriched_audit_csv(
    audit_csv: Path,
    reconcile_rep: Mapping[str, Any],
    temp_dir: Path,
) -> Path:
    """Create a read-only temp copy of `audit_csv` with broker-reconciled `swap_usd`/`pnl_usd`."""
    raw_text = audit_csv.read_text(encoding="utf-8-sig", errors="replace")
    lines = [ln for ln in raw_text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return audit_csv

    reader = csv.DictReader(lines)
    if not reader.fieldnames:
        return audit_csv
    fieldnames = list(reader.fieldnames)

    matched_by_fill_idx: dict[int, Mapping[str, Any]] = {}
    for pair in reconcile_rep.get("matched_pairs") or []:
        if isinstance(pair, Mapping) and isinstance(pair.get("audit_index"), int):
            matched_by_fill_idx[int(pair["audit_index"])] = pair

    if not matched_by_fill_idx:
        return audit_csv

    out_path = temp_dir / "reconciled_exec_audit.csv"
    audit_all = load_exec_audit_csv(audit_csv)
    fill_idx = 0
    rows_out: list[dict[str, Any]] = []

    raw_rows = list(reader)
    for row_idx, raw_row in enumerate(raw_rows):
        row_copy = dict(raw_row)
        if row_idx < len(audit_all):
            ev = str(audit_all[row_idx].get("event_type") or "").strip().upper()
            if ev not in (
                "FILL_UNRESOLVED",
                "DRYRUN_SIGNAL",
                "DRYRUN_SIGNAL_V103",
                "ORDER_REJECT",
                "ORDER_BLOCKED_SYMCAP",
                "ORDER_BLOCKED_FACTOR",
                "ORDER_BLOCKED_RISK",
                "ORDER_BLOCKED_NEWS",
                "ORDER_BLOCKED_SPREAD",
                "ORDER_BLOCKED_STOPS",
                "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP",
                "ORDER_BLOCKED_MARGIN",
                "CLOSE_REJECT",
                "SHADOW_INTENT",
            ):
                pair = matched_by_fill_idx.get(fill_idx)
                if pair is not None:
                    if pair.get("swap_usd") is not None and "swap_usd" in row_copy:
                        row_copy["swap_usd"] = str(pair["swap_usd"])
                    if pair.get("pnl_usd") is not None and "pnl_usd" in row_copy:
                        row_copy["pnl_usd"] = str(pair["pnl_usd"])
                fill_idx += 1
        rows_out.append(row_copy)

    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows_out:
            writer.writerow(r)
    return out_path


def _evaluate_reconciler_subsystem(
    *,
    audit_csv: Path | str | None,
    statement_path: Path | str | None,
    reconcile_report: Mapping[str, Any] | Path | str | None,
    quote_tape_path: Path | str | None,
    expected_login: int | None,
    allowed_magics: Sequence[int] | None,
    require_zero_swap: bool,
    known_logins: set[str],
) -> tuple[dict[str, Any], dict[str, Any] | None, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    raw_rep: dict[str, Any] | None = None

    if reconcile_report is not None:
        loaded = _load_json_if_path(reconcile_report)
        if not isinstance(loaded, Mapping):
            raise ValueError("reconcile_report must be a mapping or JSON object path")
        raw_rep = dict(loaded)
    elif audit_csv is not None and statement_path is not None:
        raw_rep = reconcile_daily_statement(
            audit_csv=audit_csv,
            statement_path=statement_path,
            quote_tape_path=quote_tape_path,
            expected_login=expected_login,
            allowed_magics=allowed_magics,
            require_zero_swap=require_zero_swap,
        )
    else:
        return {"status": "NOT_PROVIDED", "provided": False}, None, findings

    _harvest_logins(raw_rep, known_logins)
    summary = raw_rep.get("summary") or {}
    fail_reasons = [str(x) for x in (raw_rep.get("fail_reasons") or [])]
    passed = bool(raw_rep.get("passed", False))

    orphan_audit = int(summary.get("orphan_audit_count", 0) or 0)
    orphan_stmt = int(summary.get("orphan_statement_count", 0) or 0)
    unresolved = int(summary.get("unresolved_fill_rows", 0) or 0)
    missing_swap = int(summary.get("missing_swap_count", 0) or 0)
    nonzero_swap = int(summary.get("nonzero_swap_count", 0) or 0)
    has_nonzero_swap_reason = any("NONZERO_SWAP_USD" in r for r in fail_reasons)

    if orphan_audit > 0:
        findings.append(
            _finding(
                "RECONCILE_ORPHAN_AUDIT",
                TRAFFIC_RED,
                "reconciler",
                f"{orphan_audit} audit fill(s) missing on broker statement.",
            )
        )
    if orphan_stmt > 0:
        findings.append(
            _finding(
                "RECONCILE_ORPHAN_STATEMENT",
                TRAFFIC_RED,
                "reconciler",
                f"{orphan_stmt} broker statement trade(s) missing from naqex_exec_audit.csv.",
            )
        )
    if unresolved > 0:
        findings.append(
            _finding(
                "RECONCILE_UNRESOLVED_FILLS",
                TRAFFIC_RED,
                "reconciler",
                f"{unresolved} FILL_UNRESOLVED row(s) detected.",
            )
        )
    if missing_swap > 0:
        findings.append(
            _finding(
                "RECONCILE_MISSING_SWAP",
                TRAFFIC_RED,
                "reconciler",
                f"{missing_swap} fill(s) still missing swap_usd after reconciliation.",
            )
        )
    if require_zero_swap and (nonzero_swap > 0 or has_nonzero_swap_reason):
        findings.append(
            _finding(
                "RECONCILE_SWAP_VIOLATION",
                TRAFFIC_RED,
                "reconciler",
                f"Standard swap=0 contract violated: nonzero_swap_count={nonzero_swap}.",
            )
        )
    if not passed and not findings:
        findings.append(
            _finding(
                "RECONCILE_FAIL_CLOSED",
                TRAFFIC_RED,
                "reconciler",
                f"Daily statement reconciliation failed closed: {'; '.join(fail_reasons[:3]) or 'FAIL_CLOSED'}.",
            )
        )

    sub_status = TRAFFIC_RED if findings else TRAFFIC_GREEN
    sub_out = {
        "status": sub_status,
        "provided": True,
        "reconcile_status": str(raw_rep.get("status", "UNKNOWN")),
        "passed": passed,
        "matched_pairs": int(summary.get("matched_pairs", 0) or 0),
        "orphan_audit_count": orphan_audit,
        "orphan_statement_count": orphan_stmt,
        "unresolved_fill_rows": unresolved,
        "missing_swap_count": missing_swap,
        "nonzero_swap_count": nonzero_swap,
        "total_swap_usd": _to_finite_float_or_none(summary.get("total_swap_usd")),
        "net_pnl_usd": _to_finite_float_or_none(summary.get("net_pnl_usd")),
        "adverse_selection_warning": bool(raw_rep.get("adverse_selection_warning", False)),
        "fail_reasons": fail_reasons,
    }
    return sub_out, raw_rep, findings


def _evaluate_tca_subsystem(
    *,
    calibration_fills_csvs: Sequence[Path | str] | None,
    audit_csv: Path | str | None,
    spread_jsonl_path: Path | str | None,
    tca_report: Mapping[str, Any] | Path | str | None,
    raw_reconcile: Mapping[str, Any] | None,
    require_zero_swap: bool,
    use_hot_cache: bool,
    n_bootstrap_draws: int,
    seed: int,
    friction_amber: float,
    friction_red: float,
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    cal_paths = [Path(p) for p in (calibration_fills_csvs or ())]
    spread_p = Path(spread_jsonl_path) if spread_jsonl_path is not None else None
    audit_p = Path(audit_csv) if audit_csv is not None else None

    live_tca: dict[str, Any] | None = None
    audit_tca: dict[str, Any] | None = None

    if tca_report is not None:
        loaded = _load_json_if_path(tca_report)
        if not isinstance(loaded, Mapping):
            raise ValueError("tca_report must be a mapping or JSON object path")
        live_tca = dict(loaded)
    elif cal_paths or audit_p is not None or spread_p is not None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_tca_") as tmp_dir:
            eff_audit_p = audit_p
            if (
                audit_p is not None
                and audit_p.is_file()
                and raw_reconcile is not None
                and (
                    int((raw_reconcile.get("summary") or {}).get("swap_enriched_count", 0) or 0) > 0
                    or int((raw_reconcile.get("summary") or {}).get("pnl_enriched_count", 0) or 0) > 0
                )
            ):
                eff_audit_p = _materialize_enriched_audit_csv(audit_p, raw_reconcile, Path(tmp_dir))

            audit_list = [eff_audit_p] if eff_audit_p is not None else []
            live_tca = evaluate_live_tca(
                fills_csv_paths=cal_paths,
                audit_csv_paths=audit_list,
                spread_jsonl_path=spread_p,
                use_hot_cache=use_hot_cache,
                n_bootstrap_draws=n_bootstrap_draws,
                seed=seed,
                friction_amber_threshold=friction_amber,
                friction_red_threshold=friction_red,
                include_markout=spread_p is not None,
            )
            if eff_audit_p is not None and eff_audit_p.is_file():
                audit_rows = load_exec_audit_csv(eff_audit_p)
                audit_tca = compute_tca_report(
                    audit_rows,
                    enforce_post_reconcile=False,
                )
    else:
        return (
            {"status": "NOT_PROVIDED", "provided": False},
            {"verdict": "NO_DATA", "flags": []},
            findings,
        )

    verdict = str(live_tca.get("verdict", "NO_DATA"))
    alerts = [str(a) for a in (live_tca.get("alerts") or live_tca.get("flags") or [])]
    inp = live_tca.get("inputs") or {}
    port = live_tca.get("portfolio") or {}
    boot_ci = port.get("stratified_friction_multiplier_95ci") or {}
    cusum = live_tca.get("cusum_overall") or {}
    outliers = list(live_tca.get("tail_slip_outliers") or [])

    fric_mean = _to_finite_float_or_none(
        boot_ci.get("mean")
        if boot_ci.get("mean") is not None
        else (live_tca.get("friction_multiplier") or live_tca.get("slippage_multiplier"))
    )
    fric_ci_hi = _to_finite_float_or_none(boot_ci.get("ci_hi"))
    swap_viol = int(inp.get("swap_violations", live_tca.get("swap_violations", 0)) or 0)
    missing_swap = int(inp.get("missing_swap_count", 0) or 0)
    nonfinite_swap = int(inp.get("nonfinite_swap_count", 0) or 0)
    unresolved = int(inp.get("unresolved_fills", live_tca.get("unresolved_fills", 0)) or 0)
    cusum_alert = bool(cusum.get("alert", False))

    audit_verdict = str(audit_tca.get("verdict", "NO_DATA")) if audit_tca else "NO_DATA"
    if audit_tca and audit_tca.get("flags"):
        alerts.extend(str(f) for f in audit_tca["flags"] if str(f) not in alerts)

    # Determine whether RED_FRICTION_BREACH was solely due to finite swap when require_zero_swap=False
    swap_only_red_allowed = (
        not require_zero_swap
        and verdict == "RED_FRICTION_BREACH"
        and swap_viol > 0
        and missing_swap == 0
        and nonfinite_swap == 0
        and unresolved == 0
        and not cusum_alert
        and (fric_mean is None or fric_mean <= friction_red)
    )
    audit_swap_only_allowed = (
        not require_zero_swap
        and audit_verdict == "RED_SWAP_VIOLATION"
        and (audit_tca is not None)
        and float((audit_tca.get("adverse_slippage_pct_of_r0") or {}).get("mean", 0.0)) < 25.0
        and float(audit_tca.get("reject_rate_pct", 0.0)) <= 5.0
    )

    if unresolved > 0:
        findings.append(_finding("TCA_UNRESOLVED_FILL", TRAFFIC_RED, "tca", f"{unresolved} unresolved fill(s) in TCA."))
    if missing_swap > 0 or nonfinite_swap > 0:
        findings.append(
            _finding(
                "TCA_MISSING_OR_NONFINITE_SWAP",
                TRAFFIC_RED,
                "tca",
                f"TCA missing_swap={missing_swap}, nonfinite_swap={nonfinite_swap}.",
            )
        )
    if require_zero_swap and swap_viol > 0:
        findings.append(
            _finding("TCA_SWAP_VIOLATION", TRAFFIC_RED, "tca", f"{swap_viol} fill(s) violated swap=0 contract.")
        )
    if cusum_alert or verdict == "RED_CUSUM_DRIFT_ALERT":
        findings.append(
            _finding(
                "TCA_CUSUM_DRIFT_RED",
                TRAFFIC_RED,
                "tca",
                f"Page CUSUM slippage drift alert (peak={cusum.get('max_stat')}).",
            )
        )
    if fric_mean is not None and fric_mean > friction_red:
        findings.append(
            _finding(
                "TCA_FRICTION_BREACH_RED",
                TRAFFIC_RED,
                "tca",
                f"Realized friction/slippage multiplier {fric_mean:.2f}x > {friction_red:.2f}x.",
            )
        )
    if verdict.startswith("RED_") and not swap_only_red_allowed and not any(
        f["severity"] == TRAFFIC_RED for f in findings
    ):
        findings.append(_finding("TCA_RED_VERDICT", TRAFFIC_RED, "tca", f"Live TCA verdict={verdict}."))
    if audit_verdict.startswith("RED_") and not audit_swap_only_allowed:
        findings.append(
            _finding("TCA_RECONCILE_RED", TRAFFIC_RED, "tca", f"Execution audit TCA verdict={audit_verdict}.")
        )

    has_red = any(f["severity"] == TRAFFIC_RED for f in findings)
    if not has_red:
        if fric_mean is not None and friction_amber <= fric_mean <= friction_red:
            findings.append(
                _finding(
                    "TCA_ELEVATED_SLIPPAGE_AMBER",
                    TRAFFIC_AMBER,
                    "tca",
                    f"Elevated slippage/friction {fric_mean:.2f}x in [{friction_amber:.1f}x, {friction_red:.1f}x].",
                )
            )
        elif fric_ci_hi is not None and fric_ci_hi > friction_amber:
            findings.append(
                _finding(
                    "TCA_FRICTION_CI_UPPER_AMBER",
                    TRAFFIC_AMBER,
                    "tca",
                    f"Friction 95% CI upper {fric_ci_hi:.2f}x > {friction_amber:.1f}x.",
                )
            )
        if verdict in ("AMBER_FRICTION_WATCH", "AMBER_TAIL_SLIP_OUTLIER", "AMBER_WATCH") and not findings:
            findings.append(_finding("TCA_AMBER_VERDICT", TRAFFIC_AMBER, "tca", f"Live TCA verdict={verdict}."))
        if audit_verdict == "AMBER_WATCH":
            findings.append(
                _finding("TCA_RECONCILE_AMBER", TRAFFIC_AMBER, "tca", "Audit TCA flagged AMBER_WATCH (slip/latency).")
            )

    if any(f["severity"] == TRAFFIC_RED for f in findings):
        sub_status = TRAFFIC_RED
        pm_tca_verdict = verdict if verdict.startswith("RED_") else "RED_TCA_BREACH"
    elif any(f["severity"] == TRAFFIC_AMBER for f in findings):
        sub_status = TRAFFIC_AMBER
        pm_tca_verdict = "AMBER_WATCH"
    else:
        sub_status = TRAFFIC_GREEN
        pm_tca_verdict = "GREEN"

    tca_for_postmortem = {"verdict": pm_tca_verdict, "flags": alerts}
    sub_out = {
        "status": sub_status,
        "provided": True,
        "verdict": verdict,
        "audit_tca_verdict": audit_verdict,
        "holdout_rows_analysed": int(live_tca.get("holdout_rows_analysed", 0) or 0),
        "live_fill_legs_analysed": int(inp.get("live_fill_legs_analysed", 0) or 0),
        "friction_multiplier_mean": fric_mean,
        "friction_multiplier_ci_lo": _to_finite_float_or_none(boot_ci.get("ci_lo")),
        "friction_multiplier_ci_hi": fric_ci_hi,
        "cusum_max_stat": _to_finite_float_or_none(cusum.get("max_stat")),
        "cusum_alert": cusum_alert,
        "tail_slip_outlier_count": len(outliers),
        "swap_violations": swap_viol,
        "missing_swap_count": missing_swap,
        "unresolved_fills": unresolved,
        "alerts": alerts,
    }
    return sub_out, tca_for_postmortem, findings


def _evaluate_decay_subsystem(
    *,
    dev_returns: Sequence[float] | np.ndarray | Path | str | None,
    live_returns: Sequence[float] | np.ndarray | Path | str | None,
    decay_report: Mapping[str, Any] | None,
    vol_ratio: float | None,
    seed: int,
) -> tuple[dict[str, Any], dict[str, Any], float, list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    eff_vol_ratio = float(vol_ratio) if vol_ratio is not None else 1.0
    if not math.isfinite(eff_vol_ratio) or eff_vol_ratio <= 0.0:
        raise ValueError(f"vol_ratio must be finite > 0, got {vol_ratio!r}")

    raw_decay: dict[str, Any] | None = None
    if decay_report is not None:
        raw_decay = dict(decay_report)
    elif dev_returns is not None and live_returns is not None:
        dev_arr = _load_returns_array(dev_returns)
        live_arr = _load_returns_array(live_returns)
        raw_decay = evaluate_live_decay(dev_arr, live_arr, seed=seed)
        if vol_ratio is None:
            dev_sd = float(np.std(dev_arr, ddof=1)) if len(dev_arr) > 1 else 1e-9
            live_sd = float(np.std(live_arr, ddof=1)) if len(live_arr) >= 5 else dev_sd
            eff_vol_ratio = live_sd / max(dev_sd, 1e-9)
    else:
        return (
            {"status": "NOT_PROVIDED", "provided": False, "vol_ratio": round(eff_vol_ratio, 3)},
            {"verdict": "NO_LIVE_DATA", "sprt": {"state": "INCONCLUSIVE_CONTINUE"}, "reasons": []},
            eff_vol_ratio,
            findings,
        )

    verdict = str(raw_decay.get("verdict", "NO_LIVE_DATA"))
    sprt = raw_decay.get("sprt") or {}
    sprt_state = str(sprt.get("state", "INCONCLUSIVE_CONTINUE"))
    cusum = raw_decay.get("cusum") or {}
    cone = raw_decay.get("confidence_cone") or {}
    reasons = [str(r) for r in (raw_decay.get("reasons") or [])]

    if sprt_state == "REJECT_EDGE_DECAYED":
        findings.append(
            _finding(
                "ALPHA_DECAY_SPRT_REJECT",
                TRAFFIC_RED,
                "decay",
                f"Wald SPRT rejected edge (LLR={sprt.get('llr')} >= {sprt.get('upper_reject_edge')}).",
            )
        )
    elif verdict == "AMBER_WATCH_REDUCE_SIZE":
        findings.append(
            _finding(
                "DECAY_AMBER_WATCH",
                TRAFFIC_AMBER,
                "decay",
                f"Live decay monitor flagged AMBER_WATCH_REDUCE_SIZE (CUSUM={cusum.get('current_negative_sigma')}).",
            )
        )

    if any(f["severity"] == TRAFFIC_RED for f in findings):
        sub_status = TRAFFIC_RED
    elif verdict == "RED_HALT_ALPHA_DECAY":
        # May be classified Alpha Decay (RED) or Regime Shift (AMBER) by postmortem_gen depending on vol_ratio
        sub_status = TRAFFIC_RED
    elif findings:
        sub_status = TRAFFIC_AMBER
    else:
        sub_status = TRAFFIC_GREEN

    sub_out = {
        "status": sub_status,
        "provided": True,
        "verdict": verdict,
        "n_live": int(raw_decay.get("n_live", 0) or 0),
        "live_cum": _to_finite_float_or_none(raw_decay.get("live_cum")),
        "cusum_current_sigma": _to_finite_float_or_none(cusum.get("current_negative_sigma")),
        "cusum_active_breach": bool(cusum.get("active_breach", False)),
        "sprt_state": sprt_state,
        "sprt_llr": _to_finite_float_or_none(sprt.get("llr")),
        "sprt_upper_reject": _to_finite_float_or_none(sprt.get("upper_reject_edge")),
        "cone_observed_percentile": _to_finite_float_or_none(cone.get("observed_percentile")),
        "vol_ratio": round(eff_vol_ratio, 3),
        "reasons": reasons,
    }
    return sub_out, raw_decay, eff_vol_ratio, findings


def _evaluate_heartbeat_subsystem(
    *,
    heartbeat_path: Path | str | None,
    heartbeat_payload: Mapping[str, Any] | None,
    now_ts: int,
    stale_after_sec: int,
    known_logins: set[str],
) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    if heartbeat_path is None and heartbeat_payload is None:
        return (
            {"status": "NOT_PROVIDED", "provided": False},
            {"status": "OK", "age_seconds": 0, "alerts": [], "payload": None},
            findings,
        )

    if heartbeat_path is not None:
        ops_rep = inspect_heartbeat(Path(heartbeat_path), now_utc_ts=now_ts, stale_after_sec=stale_after_sec)
    else:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_hb_") as tmp_dir:
            hb_file = Path(tmp_dir) / "naqex_heartbeat.json"
            hb_file.write_text(json.dumps(dict(heartbeat_payload or {})), encoding="utf-8")
            ops_rep = inspect_heartbeat(hb_file, now_utc_ts=now_ts, stale_after_sec=stale_after_sec)

    _harvest_logins(ops_rep, known_logins)
    ops_status = str(ops_rep.get("status", "CRITICAL"))
    alerts = [str(a) for a in (ops_rep.get("alerts") or [])]
    payload = ops_rep.get("payload") if isinstance(ops_rep.get("payload"), Mapping) else {}

    if ops_status == "CRITICAL":
        findings.append(
            _finding(
                "HEARTBEAT_CRITICAL",
                TRAFFIC_RED,
                "heartbeat",
                f"Heartbeat unhealthy/stale: {'; '.join(alerts) or 'CRITICAL'}.",
            )
        )
        sub_status = TRAFFIC_RED
    elif ops_status == "WARNING":
        findings.append(
            _finding(
                "HEARTBEAT_WARNING",
                TRAFFIC_AMBER,
                "heartbeat",
                f"Heartbeat risk brake warning: {'; '.join(alerts) or 'WARNING'}.",
            )
        )
        sub_status = TRAFFIC_AMBER
    else:
        sub_status = TRAFFIC_GREEN

    sub_out = {
        "status": sub_status,
        "provided": True,
        "ops_status": ops_status,
        "age_seconds": ops_rep.get("age_seconds"),
        "regime": payload.get("regime"),
        "dry_run": payload.get("dry_run"),
        "kill_switch": bool(payload.get("kill_switch", False)) if payload else None,
        "orphan_no_sl": payload.get("orphan_no_sl"),
        "daily_dd_pct": _to_finite_float_or_none(payload.get("daily_dd_pct")),
        "static_dd_pct": _to_finite_float_or_none(payload.get("static_dd_pct")),
        "risk_mult": _to_finite_float_or_none(payload.get("risk_mult")),
        "alerts": alerts,
    }
    return sub_out, ops_rep, findings


def _load_calendar_for_ttl(
    *,
    calendar_path: Path | str | None,
    extended_calendar_path: Path | str | None,
    calendar_events: Sequence[ExtendedRedNewsEvent | RedNewsEvent] | None,
) -> tuple[bool, list[ExtendedRedNewsEvent | RedNewsEvent] | None, str | None]:
    if calendar_events is not None:
        return True, list(calendar_events), None
    if calendar_path is None and extended_calendar_path is None:
        return False, None, None

    if calendar_path is not None and extended_calendar_path is not None:
        base_p = Path(calendar_path)
        ext_p = Path(extended_calendar_path)
        if not base_p.is_file():
            return True, None, f"CALENDAR_FILE_MISSING:{base_p.name}"
        if not ext_p.is_file():
            return True, None, f"EXTENDED_CALENDAR_FILE_MISSING:{ext_p.name}"
        return True, list(load_merged_live_calendar(base_p, ext_p)), None

    if extended_calendar_path is not None:
        ext_p = Path(extended_calendar_path)
        if not ext_p.is_file():
            return True, None, f"EXTENDED_CALENDAR_FILE_MISSING:{ext_p.name}"
        return True, list(load_extended_calendar(ext_p, sections=("live_2026_2027",))), None

    cal_p = Path(calendar_path)  # type: ignore[arg-type]
    if not cal_p.is_file():
        return True, None, f"CALENDAR_FILE_MISSING:{cal_p.name}"
    if cal_p.suffix.lower() == ".json":
        raw_doc = json.loads(cal_p.read_text(encoding="utf-8"))
        if isinstance(raw_doc, Mapping) and raw_doc.get("schema") == EXTENDED_CALENDAR_SCHEMA:
            return True, list(load_extended_calendar(cal_p, sections=("live_2026_2027",))), None
    return True, list(load_calendar_events(cal_p)), None


def _serialize_ttl_status(ttl: CalendarTtlStatus) -> dict[str, Any]:
    return {
        "status": ttl.status,
        "allow_new_entries": ttl.allow_new_entries,
        "now_utc_iso": ttl.now_utc_iso,
        "overall_max_utc_iso": ttl.overall_max_utc_iso,
        "min_remaining_days": _to_finite_float_or_none(ttl.min_remaining_days),
        "per_code_remaining_days": {
            k: _to_finite_float_or_none(v) for k, v in ttl.per_code_remaining_days.items()
        },
        "per_code_status": dict(ttl.per_code_status),
        "missing_codes": list(ttl.missing_codes),
        "expired_codes": list(ttl.expired_codes),
        "amber_codes": list(ttl.amber_codes),
        "red_codes": list(ttl.red_codes),
        "reasons": list(ttl.reasons),
    }


def _evaluate_feed_dst_ttl_subsystem(
    *,
    now_dt: datetime,
    firm_profile: str,
    symbols: Sequence[str] | None,
    calendar_path: Path | str | None,
    extended_calendar_path: Path | str | None,
    calendar_events: Sequence[ExtendedRedNewsEvent | RedNewsEvent] | None,
    calendar_required_codes: Sequence[str] | None,
    ttl_amber_days: float,
    ttl_red_days: float,
    feed_snapshots: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | Path | str | None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []

    dst_snap = resolve_dst_snapshot(now_dt)
    norm_firm = normalize_firm_profile(firm_profile) or "FTMO_STANDARD"
    reset_key = "the5ers" if "THE5ERS" in norm_firm else "ftmo"
    reset_info = resolve_firm_daily_reset_utc(reset_key, now_dt)

    # Calendar TTL guard (OPS-1)
    cal_provided, loaded_events, cal_err = _load_calendar_for_ttl(
        calendar_path=calendar_path,
        extended_calendar_path=extended_calendar_path,
        calendar_events=calendar_events,
    )
    ttl_dict: dict[str, Any] = {"status": "NOT_PROVIDED", "provided": False}
    if cal_provided:
        if cal_err is not None or loaded_events is None:
            ttl_dict = {
                "status": TRAFFIC_RED,
                "provided": True,
                "allow_new_entries": False,
                "min_remaining_days": None,
                "reasons": [cal_err or "CALENDAR_UNAVAILABLE_FAIL_CLOSED"],
            }
            findings.append(
                _finding(
                    "CALENDAR_TTL_RED_OR_EXPIRED",
                    TRAFFIC_RED,
                    "feed_dst_ttl",
                    f"Red-news calendar fail-closed RED: {cal_err or 'missing'}.",
                )
            )
        else:
            req_codes: set[str] = set()
            if calendar_required_codes:
                req_codes.update(str(c).strip().upper() for c in calendar_required_codes if str(c).strip())
            if symbols:
                for sym in symbols:
                    req_codes.update(match_symbol_event_codes(sym))
            ttl_obj = check_calendar_ttl(
                loaded_events,
                now_utc=now_dt,
                required_codes=sorted(req_codes) if req_codes else None,
                amber_days=ttl_amber_days,
                red_days=ttl_red_days,
            )
            ttl_dict = {"provided": True, **_serialize_ttl_status(ttl_obj)}
            if ttl_obj.status == TRAFFIC_RED or not ttl_obj.allow_new_entries:
                findings.append(
                    _finding(
                        "CALENDAR_TTL_RED_OR_EXPIRED",
                        TRAFFIC_RED,
                        "feed_dst_ttl",
                        f"Red-news calendar TTL RED/expired (min_days={ttl_dict['min_remaining_days']}, "
                        f"reasons={', '.join(ttl_obj.reasons[:3])}).",
                    )
                )
            elif ttl_obj.status == TRAFFIC_AMBER:
                findings.append(
                    _finding(
                        "CALENDAR_TTL_AMBER",
                        TRAFFIC_AMBER,
                        "feed_dst_ttl",
                        f"Red-news calendar TTL <= {ttl_amber_days:g}d (min_days={ttl_dict['min_remaining_days']}).",
                    )
                )

    # Broker Feed Health guard (OPS-1)
    feed_out: dict[str, Any] = {"status": "NOT_PROVIDED", "provided": False, "symbols": {}}
    if feed_snapshots is not None:
        raw_feeds = _load_json_if_path(feed_snapshots)
        snap_items: list[tuple[str, Mapping[str, Any]]] = []
        if isinstance(raw_feeds, Mapping):
            for sym_k, snap_v in raw_feeds.items():
                if isinstance(snap_v, Mapping):
                    snap_items.append((str(sym_k), snap_v))
        elif isinstance(raw_feeds, Sequence) and not isinstance(raw_feeds, str):
            for item in raw_feeds:
                if isinstance(item, Mapping):
                    sym_k = str(item.get("symbol") or "").strip()
                    if sym_k:
                        snap_items.append((sym_k, item))
        else:
            raise ValueError("feed_snapshots must be a mapping, sequence, or JSON path")

        sym_results: dict[str, dict[str, Any]] = {}
        feed_has_red = False
        feed_has_amber = False
        for sym_k, snap in snap_items:
            raw_last = snap.get("last_tick_utc")
            last_dt = _parse_now_utc(raw_last) if raw_last is not None else None
            raw_ts_seq = snap.get("recent_tick_timestamps_utc")
            ts_seq = [_parse_now_utc(t) for t in raw_ts_seq] if raw_ts_seq is not None else None
            assess: FeedHealthAssessment = evaluate_feed_health(
                symbol=str(snap.get("symbol") or sym_k),
                now_utc=now_dt,
                last_tick_utc=last_dt,
                bid=snap.get("bid"),  # type: ignore[arg-type]
                ask=snap.get("ask"),  # type: ignore[arg-type]
                point_size=snap.get("point_size"),
                median_spread_points=snap.get("median_spread_points"),
                recent_mids=snap.get("recent_mids"),
                recent_tick_timestamps_utc=ts_seq,
                max_stale_sec=float(snap.get("max_stale_sec", 30.0)),
                hard_max_spread_points=snap.get("hard_max_spread_points"),
                is_market_open=bool(snap.get("is_market_open", True)),
            )
            sym_results[assess.symbol] = {
                "status": assess.status,
                "allow_trading": assess.allow_trading,
                "tick_age_sec": assess.tick_age_sec,
                "spread_points": assess.spread_points,
                "spread_ratio": assess.spread_ratio,
                "is_stale": assess.is_stale,
                "is_frozen": assess.is_frozen,
                "is_spread_spike": assess.is_spread_spike,
                "is_invalid_quote": assess.is_invalid_quote,
                "reasons": list(assess.reasons),
            }
            if assess.status == TRAFFIC_RED:
                feed_has_red = True
                findings.append(
                    _finding(
                        "FEED_HEALTH_RED",
                        TRAFFIC_RED,
                        "feed_dst_ttl",
                        f"Feed RED on {assess.symbol}: {', '.join(assess.reasons)}.",
                    )
                )
            elif assess.status == TRAFFIC_AMBER:
                feed_has_amber = True
                findings.append(
                    _finding(
                        "FEED_HEALTH_AMBER",
                        TRAFFIC_AMBER,
                        "feed_dst_ttl",
                        f"Feed AMBER on {assess.symbol}: {', '.join(assess.reasons)}.",
                    )
                )

        feed_status = TRAFFIC_RED if feed_has_red else (TRAFFIC_AMBER if feed_has_amber else TRAFFIC_GREEN)
        feed_out = {"status": feed_status, "provided": True, "symbols": sym_results}

    if any(f["severity"] == TRAFFIC_RED for f in findings):
        sub_status = TRAFFIC_RED
    elif any(f["severity"] == TRAFFIC_AMBER for f in findings):
        sub_status = TRAFFIC_AMBER
    elif cal_provided or feed_snapshots is not None:
        sub_status = TRAFFIC_GREEN
    else:
        sub_status = "NOT_PROVIDED"

    sub_out = {
        "status": sub_status,
        "provided": bool(cal_provided or feed_snapshots is not None),
        "dst": {
            "utc_iso": dst_snap.utc_iso,
            "is_dst_divergence_window": dst_snap.is_dst_divergence_window,
            "divergence_season": dst_snap.divergence_season,
            "ny_plus_7_offset_hours": dst_snap.ny_plus_7_offset_hours,
            "athens_confusion_warning": bool(reset_info.get("athens_confusion_warning", False)),
            "next_daily_reset_utc_iso": reset_info.get("next_reset_utc_iso"),
        },
        "calendar_ttl": ttl_dict,
        "feed_health": feed_out,
    }
    return sub_out, findings


def _evaluate_parity_subsystem(
    *,
    expected_python_trades: Sequence[Mapping[str, Any]] | Path | str | None,
    actual_mt5_trades: Sequence[Mapping[str, Any]] | Path | str | None,
    audit_csv: Path | str | None,
    decision_blackbox_path: Path | str | Sequence[Path | str] | None,
    decision_blackbox_records: Sequence[Mapping[str, Any]] | None,
    v103_shadow_csv: Path | str | None,
    broker_tape_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]] | None,
    quote_tape_path: Path | str | None,
    tca_for_postmortem: Mapping[str, Any],
    decay_for_postmortem: Mapping[str, Any],
    ops_for_postmortem: Mapping[str, Any],
    vol_ratio: float,
    account_alias: str,
    period_label: str,
    time_tolerance_sec: float,
    lot_sl_drift_tol: float,
    min_live_trades_feedback: int,
    require_zero_swap: bool,
    known_logins: set[str],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    if expected_python_trades is None:
        return {"status": "NOT_PROVIDED", "provided": False}, findings

    exp_loaded = _load_json_if_path(expected_python_trades)
    if not isinstance(exp_loaded, Sequence) or isinstance(exp_loaded, str):
        raise ValueError("expected_python_trades must be a sequence or JSON list path")
    exp_list = [dict(x) for x in exp_loaded]

    act_list: list[dict[str, Any]]
    if actual_mt5_trades is not None:
        act_loaded = _load_json_if_path(actual_mt5_trades)
        if not isinstance(act_loaded, Sequence) or isinstance(act_loaded, str):
            raise ValueError("actual_mt5_trades must be a sequence or JSON list path")
        act_list = [dict(x) for x in act_loaded]
    elif audit_csv is not None:
        raw_exec = load_exec_audit_records(audit_csv)
        _harvest_logins(raw_exec, known_logins)
        act_list = aggregate_mt5_deals_by_position(raw_exec)
    else:
        act_list = []

    bb_records: list[dict[str, Any]] = []
    if decision_blackbox_path is not None:
        bb_records.extend(load_decision_blackbox_jsonl(decision_blackbox_path))
    if v103_shadow_csv is not None:
        shadow_recs = load_v103_shadow_csv(v103_shadow_csv)
        _harvest_logins(shadow_recs, known_logins)
        bb_records.extend(shadow_recs)
    if decision_blackbox_records is not None:
        bb_records.extend(dict(r) for r in decision_blackbox_records)

    eff_tape = broker_tape_by_symbol
    if eff_tape is None and quote_tape_path is not None and Path(quote_tape_path).is_file():
        tape_rows = load_quote_tape(quote_tape_path)
        grouped_tape: dict[str, list[dict[str, Any]]] = {}
        for row in tape_rows:
            csym = normalize_symbol_alias(str(row.get("symbol") or ""))
            if csym:
                grouped_tape.setdefault(csym, []).append(row)
        eff_tape = grouped_tape

    weekly_rep = build_weekly_forensics_report(
        expected_python_trades=exp_list,
        actual_mt5_trades=act_list,
        decision_blackbox=bb_records or None,
        broker_tape_by_symbol=eff_tape,
        tca_report=tca_for_postmortem,
        decay_report=decay_for_postmortem,
        ops_report=ops_for_postmortem,
        vol_ratio=vol_ratio,
        account_alias=account_alias,
        period_label=period_label,
        time_tolerance_sec=time_tolerance_sec,
        lot_sl_drift_tol=lot_sl_drift_tol,
        min_live_trades=min_live_trades_feedback,
    )

    parity = weekly_rep["parity_report"]
    counts = parity["counts"]
    ghost_n = int(counts.get(PARITY_BOT_BUG_GHOST_TRADE, 0))
    missed_n = int(counts.get(PARITY_BOT_BUG_MISSED_TRADE, 0))
    drift_n = int(counts.get(PARITY_LOT_OR_SL_DRIFT, 0))
    friction_n = int(counts.get(PARITY_EXECUTION_FRICTION_DRIFT, 0))
    guard_n = int(counts.get(PARITY_LEGITIMATE_GUARD_BLOCK, 0))
    clean_n = int(counts.get(PARITY_MATCH_CLEAN, 0))

    red_friction = [
        ev
        for ev in parity.get("events", [])
        if ev.get("parity_class") == PARITY_EXECUTION_FRICTION_DRIFT and ev.get("severity") == TRAFFIC_RED
    ]

    # Technical parity bugs ALWAYS halt RED regardless of PnL!
    if ghost_n > 0:
        findings.append(
            _finding(
                "PARITY_BOT_BUG_GHOST_TRADE",
                TRAFFIC_RED,
                "parity_forensics",
                f"Detected {ghost_n} BOT_BUG_GHOST_TRADE (MT5 fired without Python signal; halt regardless of PnL).",
            )
        )
    if missed_n > 0:
        findings.append(
            _finding(
                "PARITY_BOT_BUG_MISSED_TRADE",
                TRAFFIC_RED,
                "parity_forensics",
                f"Detected {missed_n} BOT_BUG_MISSED_TRADE (Python signaled, MT5 silent with no guard block).",
            )
        )
    if drift_n > 0:
        findings.append(
            _finding(
                "PARITY_LOT_OR_SL_DRIFT",
                TRAFFIC_RED,
                "parity_forensics",
                f"Detected {drift_n} LOT_OR_SL_DRIFT event(s) (> {lot_sl_drift_tol * 100.0:.1f}% drift).",
            )
        )
    if require_zero_swap and red_friction:
        findings.append(
            _finding(
                "PARITY_SWAP_VIOLATION",
                TRAFFIC_RED,
                "parity_forensics",
                f"Parity detected {len(red_friction)} RED swap!=0 execution friction event(s).",
            )
        )
    elif friction_n > 0 and not findings:
        findings.append(
            _finding(
                "PARITY_EXECUTION_FRICTION_DRIFT",
                TRAFFIC_AMBER,
                "parity_forensics",
                f"Parity routed {friction_n} EXECUTION_FRICTION_DRIFT event(s) to TCA watch.",
            )
        )

    sub_status = (
        TRAFFIC_RED
        if any(f["severity"] == TRAFFIC_RED for f in findings)
        else (TRAFFIC_AMBER if findings else TRAFFIC_GREEN)
    )
    geom_sum = (weekly_rep.get("geometry_report") or {}).get("summary") or {}
    fb = weekly_rep.get("feedback_protocol") or {}
    sub_out = {
        "status": sub_status,
        "provided": True,
        "verdict": parity["verdict"],
        "trade_match_rate": parity["trade_match_rate"],
        "technical_bug_count": parity["technical_bug_count"],
        "friction_drift_count": parity["friction_drift_count"],
        "counts": {
            PARITY_MATCH_CLEAN: clean_n,
            PARITY_BOT_BUG_GHOST_TRADE: ghost_n,
            PARITY_BOT_BUG_MISSED_TRADE: missed_n,
            PARITY_LOT_OR_SL_DRIFT: drift_n,
            PARITY_EXECUTION_FRICTION_DRIFT: friction_n,
            PARITY_LEGITIMATE_GUARD_BLOCK: guard_n,
        },
        "geometry_trades_analysed": int(geom_sum.get("trades", 0) or 0),
        "feedback_lock_status": fb.get("lock_status"),
        "draft_hypothesis_count": len(fb.get("draft_hypothesis_cards") or []),
    }
    return sub_out, findings


def _evaluate_compliance_preflight_subsystem(
    *,
    preflight_config: Mapping[str, Any] | Path | str | None,
    days_since_last_trade: float | int | None,
    max_day_profit_usd: float | None,
    daily_profits_usd: Sequence[float] | None,
    total_profit_target_usd: float | None,
    is_sprint_mode: bool,
    active_eas: Sequence[Mapping[str, Any]] | None,
    active_signals: Sequence[Mapping[str, Any]] | None,
    known_logins: set[str],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []

    if preflight_config is not None:
        cfg_loaded = _load_json_if_path(preflight_config)
        if not isinstance(cfg_loaded, Mapping):
            raise ValueError("preflight_config must be a mapping or JSON object path")
        cfg = dict(cfg_loaded)
        _harvest_logins(cfg, known_logins)
        if days_since_last_trade is not None and "days_since_last_trade" not in cfg:
            cfg["days_since_last_trade"] = days_since_last_trade
        rep = validate_account_deployment(**cfg)
        if rep.verdict in ("REJECT", "PASS_WITH_RED"):
            codes = list(rep.reject_codes) + list(rep.red_codes)
            findings.append(
                _finding(
                    "PREFLIGHT_REJECT_OR_RED",
                    TRAFFIC_RED,
                    "preflight_compliance",
                    f"Account preflight {rep.verdict}: {', '.join(codes[:5])}.",
                )
            )
            sub_status = TRAFFIC_RED
        elif rep.verdict == "PASS_WITH_AMBER":
            findings.append(
                _finding(
                    "PREFLIGHT_AMBER",
                    TRAFFIC_AMBER,
                    "preflight_compliance",
                    f"Account preflight AMBER: {', '.join(rep.amber_codes[:5])}.",
                )
            )
            sub_status = TRAFFIC_AMBER
        else:
            sub_status = TRAFFIC_GREEN
        return (
            {
                "status": sub_status,
                "provided": True,
                "mode": "full_preflight",
                "verdict": rep.verdict,
                "can_launch": rep.can_launch,
                "inactivity_status": rep.inactivity_status,
                "days_since_last_trade": cfg.get("days_since_last_trade"),
                "best_day_share": rep.best_day_share,
                "reject_codes": list(rep.reject_codes),
                "red_codes": list(rep.red_codes),
                "amber_codes": list(rep.amber_codes),
            },
            findings,
        )

    has_comp_input = any(
        x is not None
        for x in (days_since_last_trade, max_day_profit_usd, daily_profits_usd, active_eas, active_signals)
    )
    if not has_comp_input:
        return {"status": "NOT_PROVIDED", "provided": False}, findings

    _harvest_logins(active_eas, known_logins)
    _harvest_logins(active_signals, known_logins)
    comp_findings, inact_status, best_day_share = check_multi_account_compliance(
        active_eas=active_eas,
        active_signals=active_signals,
        days_since_last_trade=days_since_last_trade,
        max_day_profit_usd=max_day_profit_usd,
        daily_profits_usd=daily_profits_usd,
        total_profit_target_usd=total_profit_target_usd,
        is_sprint_mode=is_sprint_mode,
    )
    for cf in comp_findings:
        if cf.severity in ("REJECT", "RED"):
            findings.append(_finding(cf.code, TRAFFIC_RED, "preflight_compliance", cf.message))
        elif cf.severity == "AMBER":
            findings.append(_finding(cf.code, TRAFFIC_AMBER, "preflight_compliance", cf.message))

    if any(f["severity"] == TRAFFIC_RED for f in findings):
        sub_status = TRAFFIC_RED
    elif any(f["severity"] == TRAFFIC_AMBER for f in findings):
        sub_status = TRAFFIC_AMBER
    else:
        sub_status = TRAFFIC_GREEN

    return (
        {
            "status": sub_status,
            "provided": True,
            "mode": "compliance_checks",
            "inactivity_status": inact_status,
            "days_since_last_trade": _to_finite_float_or_none(days_since_last_trade),
            "best_day_share": best_day_share,
            "finding_codes": [cf.code for cf in comp_findings],
        },
        findings,
    )


def _g12_safe_network_note(net: Mapping[str, Any]) -> str:
    """Return G12-compliant Vietnamese network note (zero mention of contacting broker support)."""
    if not net.get("geo_lookup_ok"):
        return "Khong xac minh duoc ma quoc gia IP cong cong; kiem tra lai ket noi mang truoc khi giao dich."
    if net.get("is_us_ip_blocked"):
        return "CHAN CUNG: Phat hien IP dinh vi Hoa Ky (US) — khong phu hop dieu khoan dia ly."
    if net.get("is_cgnat"):
        return (
            "CANH BAO CGNAT: Nha mang dang cap dai CGNAT; "
            "uu tien nang cap IPv4 cong cong rieng truoc giai doan Funded."
        )
    if net.get("double_nat_suspected"):
        return "LUU Y DOUBLE-NAT: Phat hien lop NAT trung gian; kiem tra cau hinh bridge mode tren router."
    return "DAT CHUAN: IP ngoai My va khong phat hien dau hieu CGNAT."


def _evaluate_ops_cloud_subsystem(
    *,
    pre_checkout_network: Mapping[str, Any] | None,
    node_snapshot: Mapping[str, Any] | Path | str | None,
    scoreboard_path: Path | str | None,
    upcoming_news_csv: Path | str | None,
    now_dt: datetime,
    known_logins: set[str],
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    findings: list[dict[str, str]] = []
    provided = any(x is not None for x in (pre_checkout_network, node_snapshot, scoreboard_path, upcoming_news_csv))
    if not provided:
        return {"status": "NOT_PROVIDED", "provided": False}, findings

    net_out: dict[str, Any] | None = None
    if pre_checkout_network is not None:
        raw_net = pre_checkout_mod.classify_network_signals(
            country_code=pre_checkout_network.get("country_code"),
            geo_lookup_ok=bool(pre_checkout_network.get("geo_lookup_ok", True)),
            hop_ips=pre_checkout_network.get("hop_ips"),
            non_tailscale_iface_ips=pre_checkout_network.get("non_tailscale_iface_ips"),
            is_cgnat_override=pre_checkout_network.get("is_cgnat"),
            double_nat_override=pre_checkout_network.get("double_nat_suspected"),
            probe_source="offline_snapshot",
        )
        net_out = {**raw_net, "recommendation": _g12_safe_network_note(raw_net)}
        if not net_out.get("geo_lookup_ok") or net_out.get("is_us_ip_blocked"):
            findings.append(
                _finding(
                    "PRE_CHECKOUT_NETWORK_RED",
                    TRAFFIC_RED,
                    "ops_cloud",
                    (
                        f"Pre-checkout network blocked (country={net_out.get('country_code')}, "
                        f"geo_ok={net_out.get('geo_lookup_ok')})."
                    ),
                )
            )
        elif net_out.get("is_cgnat") or net_out.get("double_nat_suspected"):
            findings.append(
                _finding(
                    "PRE_CHECKOUT_NETWORK_AMBER",
                    TRAFFIC_AMBER,
                    "ops_cloud",
                    (
                        f"Pre-checkout network warning (cgnat={net_out.get('is_cgnat')}, "
                        f"double_nat={net_out.get('double_nat_suspected')})."
                    ),
                )
            )

    sb_out: dict[str, Any] = (
        node_digest_mod.load_optional_scoreboard(Path(scoreboard_path))
        if scoreboard_path is not None
        else {"present": False, "status": "ABSENT"}
    )

    node_out: dict[str, Any] | None = None
    if node_snapshot is not None:
        fx = _load_json_if_path(node_snapshot)
        if not isinstance(fx, Mapping):
            raise ValueError("node_snapshot must be a mapping or JSON object path")
        _harvest_logins(fx, known_logins)
        local_kit = fx.get("local_kit") if isinstance(fx.get("local_kit"), Mapping) else None
        if local_kit is None:
            preset_name = str(fx.get("preset") or cutover_mod.DEFAULT_PRESET)
            local_kit = cutover_mod.verify_local_kit_and_preset(preset_name)
        digest_res = node_digest_mod.build_ops_digest(
            status=fx.get("status"),
            integrity=fx.get("integrity"),
            maint=fx.get("maint"),
            audit=fx.get("audit"),
            local_kit=dict(local_kit),
            scoreboard=sb_out,
            now_utc=now_dt,
        )
        ov = str(digest_res.get("overall_status", "OFFLINE"))
        node_out = {
            "overall_status": ov,
            "cutover_verdict": digest_res.get("cutover_verdict"),
            "gates_passed": digest_res.get("gates_passed"),
            "gates_total": digest_res.get("gates_total"),
            "failed_gates": list(digest_res.get("failed_gates") or []),
        }
        if ov == "OFFLINE":
            findings.append(
                _finding("NODE_DIGEST_OFFLINE", TRAFFIC_RED, "ops_cloud", "Node snapshot reported OFFLINE.")
            )
        elif ov == "DEGRADED":
            findings.append(
                _finding(
                    "NODE_DIGEST_DEGRADED",
                    TRAFFIC_AMBER,
                    "ops_cloud",
                    f"Node snapshot DEGRADED (failed_gates={', '.join(node_out['failed_gates'][:3])}).",
                )
            )

    news_out: dict[str, Any] | None = None
    if upcoming_news_csv is not None:
        raw_news = pre_checkout_mod.extract_upcoming_red_news(
            Path(upcoming_news_csv),
            now_utc=now_dt,
            horizon_days=14,
        )
        news_out = {
            "ok": bool(raw_news.get("ok", False)),
            "total_csv_rows": int(raw_news.get("total_csv_rows", 0) or 0),
            "upcoming_count": int(raw_news.get("upcoming_count", 0) or 0),
            "next_event": (raw_news.get("events") or [None])[0],
        }
        if news_out["total_csv_rows"] == 0:
            findings.append(
                _finding(
                    "UPCOMING_NEWS_CSV_MISSING",
                    TRAFFIC_RED,
                    "ops_cloud",
                    "Upcoming red-news CSV is missing or empty.",
                )
            )

    pre_checkout_summary: dict[str, Any] | None = None
    if net_out is not None and news_out is not None and node_out is not None:
        raw_pre = pre_checkout_mod.evaluate_pre_checkout(
            network=net_out,
            news={"ok": news_out["ok"], "events": []},
            cutover_result={
                "verdict": node_out.get("cutover_verdict"),
                "gates_passed": node_out.get("gates_passed"),
                "gates_total": node_out.get("gates_total"),
                "failed_gates": node_out.get("failed_gates", []),
            },
            now_utc=now_dt,
        )
        pre_checkout_summary = {
            "verdict": raw_pre.get("verdict"),
            "hard_blocks": list(raw_pre.get("hard_blocks") or []),
            "warnings": list(raw_pre.get("warnings") or []),
        }

    sub_status = (
        TRAFFIC_RED
        if any(f["severity"] == TRAFFIC_RED for f in findings)
        else (TRAFFIC_AMBER if findings else TRAFFIC_GREEN)
    )
    return (
        {
            "status": sub_status,
            "provided": True,
            "network": net_out,
            "node_digest": node_out,
            "scoreboard": sb_out,
            "upcoming_red_news_14d": news_out,
            "pre_checkout": pre_checkout_summary,
        },
        findings,
    )


# ---------------------------------------------------------------------------
# Main End-to-End Orchestrator (`run_daily_live_ops_pipeline`)
# ---------------------------------------------------------------------------
def run_daily_live_ops_pipeline(
    *,
    account_alias: str = "DEMO_PRIMARY",
    firm_profile: str = "FTMO_STANDARD",
    period_label: str = "Daily Live-Ops",
    mode: str = "daily",
    now_utc: datetime | str | int | float | None = None,
    require_zero_swap: bool = True,
    expected_login: int | None = None,
    allowed_magics: Sequence[int] | None = None,
    symbols: Sequence[str] | None = None,
    # Reconciler inputs
    audit_csv: Path | str | None = None,
    statement_path: Path | str | None = None,
    reconcile_report: Mapping[str, Any] | Path | str | None = None,
    quote_tape_path: Path | str | None = None,
    # Live TCA inputs
    calibration_fills_csvs: Sequence[Path | str] | None = None,
    spread_jsonl_path: Path | str | None = None,
    tca_report: Mapping[str, Any] | Path | str | None = None,
    use_hot_cache: bool = False,
    n_bootstrap_draws: int = 10_000,
    tca_friction_amber: float = DEFAULT_TCA_FRICTION_AMBER,
    tca_friction_red: float = DEFAULT_TCA_FRICTION_RED,
    # Alpha Decay & Postmortem inputs
    dev_returns: Sequence[float] | np.ndarray | Path | str | None = None,
    live_returns: Sequence[float] | np.ndarray | Path | str | None = None,
    decay_report: Mapping[str, Any] | None = None,
    vol_ratio: float | None = None,
    vol_high_thresh: float = DEFAULT_VOL_HIGH_THRESH,
    vol_low_thresh: float = DEFAULT_VOL_LOW_THRESH,
    # Feed / DST / Calendar TTL inputs (OPS-1)
    calendar_path: Path | str | None = None,
    extended_calendar_path: Path | str | None = None,
    calendar_events: Sequence[ExtendedRedNewsEvent | RedNewsEvent] | None = None,
    calendar_required_codes: Sequence[str] | None = None,
    ttl_amber_days: float = TTL_AMBER_DAYS_DEFAULT,
    ttl_red_days: float = TTL_RED_DAYS_DEFAULT,
    feed_snapshots: Sequence[Mapping[str, Any]] | Mapping[str, Mapping[str, Any]] | Path | str | None = None,
    # Heartbeat Watchdog inputs
    heartbeat_path: Path | str | None = None,
    heartbeat_payload: Mapping[str, Any] | None = None,
    heartbeat_stale_sec: int = 180,
    # Live Parity Forensics inputs (OPS-6)
    expected_python_trades: Sequence[Mapping[str, Any]] | Path | str | None = None,
    actual_mt5_trades: Sequence[Mapping[str, Any]] | Path | str | None = None,
    decision_blackbox_path: Path | str | Sequence[Path | str] | None = None,
    decision_blackbox_records: Sequence[Mapping[str, Any]] | None = None,
    v103_shadow_csv: Path | str | None = None,
    broker_tape_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    parity_time_tolerance_sec: float = 60.0,
    parity_lot_sl_drift_tol: float = 0.05,
    min_live_trades_feedback: int = ANTI_OVERFIT_MIN_LIVE_TRADES,
    # Account Preflight & Inactivity / Compliance inputs (OPS-2)
    days_since_last_trade: float | int | None = None,
    max_day_profit_usd: float | None = None,
    daily_profits_usd: Sequence[float] | None = None,
    total_profit_target_usd: float | None = None,
    is_sprint_mode: bool = False,
    active_eas: Sequence[Mapping[str, Any]] | None = None,
    active_signals: Sequence[Mapping[str, Any]] | None = None,
    preflight_config: Mapping[str, Any] | Path | str | None = None,
    # Optional offline Ops-Cloud integration
    pre_checkout_network: Mapping[str, Any] | None = None,
    node_snapshot: Mapping[str, Any] | Path | str | None = None,
    scoreboard_path: Path | str | None = None,
    upcoming_news_csv: Path | str | None = None,
    # Strictness & Output controls
    strict_core_subsystems: bool = False,
    out_json: Path | str | None = None,
    out_digest_txt: Path | str | None = None,
    seed: int = 20261127,
) -> dict[str, Any]:
    """Run all Live-Ops subsystems read-only and compute the Objective Traffic-Light Decision Matrix."""
    if ORDER_SEND_CAPABLE or ORDER_SEND_COUNT != 0:
        raise RuntimeError("READONLY_INVARIANT_VIOLATION: daily_live_ops_pipeline is strictly read-only")

    now_dt = _parse_now_utc(now_utc)
    now_ts = int(now_dt.timestamp())
    now_iso = now_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    norm_mode = str(mode or "daily").strip().lower()
    if norm_mode not in ("daily", "weekly"):
        raise ValueError(f"mode must be 'daily' or 'weekly', got {mode!r}")

    known_logins: set[str] = set()
    if expected_login is not None and isinstance(expected_login, int) and not isinstance(expected_login, bool):
        if expected_login > 0:
            known_logins.add(str(expected_login))

    all_findings: list[dict[str, str]] = []

    # 1. Daily Statement Reconciler
    reconciler_sub, raw_reconcile, rec_findings = _evaluate_reconciler_subsystem(
        audit_csv=audit_csv,
        statement_path=statement_path,
        reconcile_report=reconcile_report,
        quote_tape_path=quote_tape_path,
        expected_login=expected_login,
        allowed_magics=allowed_magics,
        require_zero_swap=require_zero_swap,
        known_logins=known_logins,
    )
    all_findings.extend(rec_findings)

    # 2. Live TCA & Slippage-Drift Monitor
    tca_sub, tca_for_pm, tca_findings = _evaluate_tca_subsystem(
        calibration_fills_csvs=calibration_fills_csvs,
        audit_csv=audit_csv,
        spread_jsonl_path=spread_jsonl_path,
        tca_report=tca_report,
        raw_reconcile=raw_reconcile,
        require_zero_swap=require_zero_swap,
        use_hot_cache=use_hot_cache,
        n_bootstrap_draws=n_bootstrap_draws,
        seed=seed,
        friction_amber=tca_friction_amber,
        friction_red=tca_friction_red,
    )
    all_findings.extend(tca_findings)

    # 3. Live Alpha Decay (CUSUM + Wald SPRT + Bootstrap Cone)
    decay_sub, decay_for_pm, eff_vol_ratio, decay_findings = _evaluate_decay_subsystem(
        dev_returns=dev_returns,
        live_returns=live_returns,
        decay_report=decay_report,
        vol_ratio=vol_ratio,
        seed=seed,
    )
    all_findings.extend(decay_findings)

    # 4. Heartbeat Watchdog (ops_monitor)
    hb_sub, ops_for_pm, hb_findings = _evaluate_heartbeat_subsystem(
        heartbeat_path=heartbeat_path,
        heartbeat_payload=heartbeat_payload,
        now_ts=now_ts,
        stale_after_sec=heartbeat_stale_sec,
        known_logins=known_logins,
    )
    all_findings.extend(hb_findings)

    # 5. Blameless Postmortem Discrepancy Classifier (postmortem_gen)
    pm_provided = any(x["provided"] for x in (tca_sub, decay_sub, hb_sub)) or (vol_ratio is not None)
    postmortem_diag = classify_discrepancy(
        tca_for_pm,
        decay_for_pm,
        ops_for_pm,
        vol_ratio=eff_vol_ratio,
        vol_high_thresh=vol_high_thresh,
        vol_low_thresh=vol_low_thresh,
    )
    pm_cls = str(postmortem_diag.get("classification", "Normal Variance"))
    pm_sev = str(postmortem_diag.get("severity", TRAFFIC_GREEN))

    if pm_provided:
        if pm_cls == "Execution TCA Bug" and pm_sev == TRAFFIC_RED:
            all_findings.append(
                _finding(
                    "POSTMORTEM_EXECUTION_TCA_BUG_RED",
                    TRAFFIC_RED,
                    "postmortem",
                    "Blameless postmortem classified RED Execution TCA Bug.",
                )
            )
        elif pm_cls == "Execution TCA Bug" and pm_sev == TRAFFIC_AMBER:
            all_findings.append(
                _finding(
                    "POSTMORTEM_EXECUTION_TCA_BUG_AMBER",
                    TRAFFIC_AMBER,
                    "postmortem",
                    "Blameless postmortem classified AMBER Execution TCA watch.",
                )
            )
        elif pm_cls == "Alpha Decay":
            all_findings.append(
                _finding(
                    "POSTMORTEM_ALPHA_DECAY_RED",
                    TRAFFIC_RED,
                    "postmortem",
                    "Blameless postmortem classified RED Alpha Decay (structural edge loss).",
                )
            )
        elif pm_cls == "Regime Shift":
            all_findings.append(
                _finding(
                    "POSTMORTEM_REGIME_SHIFT_AMBER",
                    TRAFFIC_AMBER,
                    "postmortem",
                    f"Blameless postmortem classified AMBER Regime Shift (vol_ratio={eff_vol_ratio:.2f}x).",
                )
            )
            # Realign decay subsystem display status if RED_HALT was downgraded to Regime Shift AMBER (no SPRT reject)
            if (
                decay_sub.get("provided")
                and decay_sub.get("verdict") == "RED_HALT_ALPHA_DECAY"
                and decay_sub.get("sprt_state") != "REJECT_EDGE_DECAYED"
            ):
                decay_sub["status"] = TRAFFIC_AMBER

    postmortem_sub = {
        "status": pm_sev if pm_provided else "NOT_PROVIDED",
        "provided": pm_provided,
        "classification": pm_cls,
        "severity": pm_sev,
        "vol_ratio": postmortem_diag.get("vol_ratio"),
        "secondary_signals": list(postmortem_diag.get("secondary_signals") or []),
        "recommended_actions": list(postmortem_diag.get("recommended_actions") or []),
    }

    # 6. Feed Health, US/EU DST & Red-News Calendar TTL (OPS-1)
    feed_dst_sub, fdt_findings = _evaluate_feed_dst_ttl_subsystem(
        now_dt=now_dt,
        firm_profile=firm_profile,
        symbols=symbols,
        calendar_path=calendar_path,
        extended_calendar_path=extended_calendar_path,
        calendar_events=calendar_events,
        calendar_required_codes=calendar_required_codes,
        ttl_amber_days=ttl_amber_days,
        ttl_red_days=ttl_red_days,
        feed_snapshots=feed_snapshots,
    )
    all_findings.extend(fdt_findings)

    # 7. Live Parity Forensics & Trade Geometry (OPS-6)
    parity_sub, parity_findings = _evaluate_parity_subsystem(
        expected_python_trades=expected_python_trades,
        actual_mt5_trades=actual_mt5_trades,
        audit_csv=audit_csv,
        decision_blackbox_path=decision_blackbox_path,
        decision_blackbox_records=decision_blackbox_records,
        v103_shadow_csv=v103_shadow_csv,
        broker_tape_by_symbol=broker_tape_by_symbol,
        quote_tape_path=quote_tape_path,
        tca_for_postmortem=tca_for_pm,
        decay_for_postmortem=decay_for_pm,
        ops_for_postmortem=ops_for_pm,
        vol_ratio=eff_vol_ratio,
        account_alias=account_alias,
        period_label=period_label,
        time_tolerance_sec=parity_time_tolerance_sec,
        lot_sl_drift_tol=parity_lot_sl_drift_tol,
        min_live_trades_feedback=min_live_trades_feedback,
        require_zero_swap=require_zero_swap,
        known_logins=known_logins,
    )
    all_findings.extend(parity_findings)

    # 8. Account Phase Preflight & Inactivity / Compliance (OPS-2)
    comp_sub, comp_findings = _evaluate_compliance_preflight_subsystem(
        preflight_config=preflight_config,
        days_since_last_trade=days_since_last_trade,
        max_day_profit_usd=max_day_profit_usd,
        daily_profits_usd=daily_profits_usd,
        total_profit_target_usd=total_profit_target_usd,
        is_sprint_mode=is_sprint_mode,
        active_eas=active_eas,
        active_signals=active_signals,
        known_logins=known_logins,
    )
    all_findings.extend(comp_findings)

    # 9. Optional Offline Ops-Cloud Pre-Checkout & Node Digest
    ops_cloud_sub, cloud_findings = _evaluate_ops_cloud_subsystem(
        pre_checkout_network=pre_checkout_network,
        node_snapshot=node_snapshot,
        scoreboard_path=scoreboard_path,
        upcoming_news_csv=upcoming_news_csv,
        now_dt=now_dt,
        known_logins=known_logins,
    )
    all_findings.extend(cloud_findings)

    # Optional strict core presence gate (fail-closed if required core telemetry is omitted)
    if strict_core_subsystems:
        for core_name, sub_obj in (
            ("heartbeat", hb_sub),
            ("calendar_ttl", feed_dst_sub["calendar_ttl"]),
            ("tca", tca_sub),
        ):
            if not sub_obj.get("provided"):
                all_findings.append(
                    _finding(
                        f"MISSING_CORE_SUBSYSTEM_{core_name.upper()}",
                        TRAFFIC_RED,
                        core_name,
                        f"strict_core_subsystems=True requires {core_name} snapshot (fail-closed).",
                    )
                )

    # Compute Objective Traffic Light & Action Matrix
    red_findings = [f for f in all_findings if f["severity"] == TRAFFIC_RED]
    amber_findings = [f for f in all_findings if f["severity"] == TRAFFIC_AMBER]

    if red_findings:
        traffic_light = TRAFFIC_RED
    elif amber_findings:
        traffic_light = TRAFFIC_AMBER
    else:
        traffic_light = TRAFFIC_GREEN

    decision = dict(TRAFFIC_ACTION_MATRIX[traffic_light])
    decision["red_trigger_count"] = len(red_findings)
    decision["amber_trigger_count"] = len(amber_findings)
    decision["red_codes"] = [f["code"] for f in red_findings]
    decision["amber_codes"] = [f["code"] for f in amber_findings]

    subsystems = {
        "reconciler": reconciler_sub,
        "tca": tca_sub,
        "parity_forensics": parity_sub,
        "decay": decay_sub,
        "postmortem": postmortem_sub,
        "feed_dst_ttl": feed_dst_sub,
        "heartbeat": hb_sub,
        "preflight_compliance": comp_sub,
        "ops_cloud": ops_cloud_sub,
    }
    subsystems_evaluated = [k for k, v in subsystems.items() if v.get("provided")]
    subsystems_not_provided = [k for k, v in subsystems.items() if not v.get("provided")]

    raw_report: dict[str, Any] = {
        "schema": PIPELINE_SCHEMA,
        "generated_utc": now_iso,
        "mode": norm_mode,
        "account_alias": account_alias,
        "firm_profile": normalize_firm_profile(firm_profile) or str(firm_profile),
        "period_label": period_label,
        "require_zero_swap": bool(require_zero_swap),
        "readonly": True,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "traffic_light": traffic_light,
        "action": decision["action"],
        "risk_multiplier": decision["risk_multiplier"],
        "decision": decision,
        "subsystems_evaluated": subsystems_evaluated,
        "subsystems_not_provided": subsystems_not_provided,
        "findings": all_findings,
        "subsystems": subsystems,
    }

    # Strict OPSEC redaction over the ENTIRE report before computing SHA-256 or rendering digest
    sanitized_report: dict[str, Any] = redact_opsec_payload(raw_report, known_logins=known_logins)
    digest_text = render_daily_ops_digest(sanitized_report, known_logins=known_logins)
    sanitized_report["digest_text"] = digest_text

    if out_json is not None:
        receipt = write_atomic_sha256_json(out_json, sanitized_report)
        sanitized_report["report_sha256"] = receipt["report_sha256"]
        sanitized_report["output_receipt"] = {
            "file_name": tca_sanitize_path_label(out_json),
            "report_sha256": receipt["report_sha256"],
            "file_sha256": receipt["file_sha256"],
            "bytes": receipt["bytes"],
        }
    else:
        sanitized_report["report_sha256"] = canonical_payload_sha256(sanitized_report)

    if out_digest_txt is not None:
        txt_p = Path(out_digest_txt)
        txt_p.parent.mkdir(parents=True, exist_ok=True)
        txt_p.write_text(digest_text + "\n", encoding="utf-8", newline="\n")

    return sanitized_report


# ---------------------------------------------------------------------------
# Telegram-Ready Vietnamese/English Digest Renderer (OPSEC-Redacted, 0 bare `$`)
# ---------------------------------------------------------------------------
def _dot_for_status(status: str) -> str:
    return {
        TRAFFIC_GREEN: "🟢",
        TRAFFIC_AMBER: "🟡",
        TRAFFIC_RED: "🔴",
        "NOT_PROVIDED": "⚪",
    }.get(status, "⚪")


def render_daily_ops_digest(
    report: Mapping[str, Any],
    *,
    known_logins: Iterable[str] = (),
) -> str:
    """Render concise Telegram-ready Vietnamese/English Ops Digest (OPSEC-redacted, 0 bare `$`)."""
    tl = str(report.get("traffic_light", TRAFFIC_RED))
    dot = _dot_for_status(tl)
    dec = report.get("decision") or {}
    subs = report.get("subsystems") or {}
    rec = subs.get("reconciler") or {}
    tca = subs.get("tca") or {}
    par = subs.get("parity_forensics") or {}
    dcy = subs.get("decay") or {}
    pm = subs.get("postmortem") or {}
    fdt = subs.get("feed_dst_ttl") or {}
    hb = subs.get("heartbeat") or {}
    cmp_s = subs.get("preflight_compliance") or {}
    cld = subs.get("ops_cloud") or {}

    lines: list[str] = [
        f"{dot} NAQEX LIVE-OPS [{tl}] | {report.get('account_alias')} ({report.get('firm_profile')})",
        f"Ky bao cao: {report.get('period_label')} | UTC: {report.get('generated_utc')} | OrderSend=0",
        f"Quyet dinh: {dec.get('action')} (risk={dec.get('risk_multiplier')}x | DryRun={dec.get('dry_run_required')})",
        f"Trang thai: {dec.get('label_vi')}",
        "--- Bang kiem tung phan he ---",
    ]

    # 1. Reconciler
    if rec.get("provided"):
        net_pnl = rec.get("net_pnl_usd")
        pnl_txt = f"{net_pnl:+.2f} USD" if isinstance(net_pnl, (int, float)) else "N/A"
        orphan_pair = f"{rec.get('orphan_audit_count')}/{rec.get('orphan_statement_count')}"
        lines.append(
            f"{_dot_for_status(rec['status'])} Reconciler: {rec.get('reconcile_status')} | "
            f"khop={rec.get('matched_pairs')} | orphan={orphan_pair} | "
            f"swap!=0: {rec.get('nonzero_swap_count')} | PnL={pnl_txt}"
        )
    else:
        lines.append("⚪ Reconciler: chua nap snapshot doi soat sao ke")

    # 2. TCA
    if tca.get("provided"):
        fm = tca.get("friction_multiplier_mean")
        fm_txt = f"{fm:.2f}x" if isinstance(fm, (int, float)) else "N/A"
        lines.append(
            f"{_dot_for_status(tca['status'])} Live TCA: {tca.get('verdict')} | "
            f"ma sat={fm_txt} | CUSUM={tca.get('cusum_max_stat')} | swap_viol={tca.get('swap_violations')}"
        )
    else:
        lines.append("⚪ Live TCA: chua nap du lieu khop lenh/spread")

    # 3. Parity Forensics
    if par.get("provided"):
        pc = par.get("counts") or {}
        lines.append(
            f"{_dot_for_status(par['status'])} Parity OPS-6: {par.get('verdict')} | "
            f"clean={pc.get(PARITY_MATCH_CLEAN, 0)} | ghost={pc.get(PARITY_BOT_BUG_GHOST_TRADE, 0)} | "
            f"missed={pc.get(PARITY_BOT_BUG_MISSED_TRADE, 0)} | drift={pc.get(PARITY_LOT_OR_SL_DRIFT, 0)} | "
            f"guard={pc.get(PARITY_LEGITIMATE_GUARD_BLOCK, 0)}"
        )
    else:
        lines.append("⚪ Parity OPS-6: chua nap expected Python trades")

    # 4. Decay & Postmortem
    if dcy.get("provided") or pm.get("provided"):
        d_st = dcy.get("status", "NOT_PROVIDED")
        p_st = pm.get("status", "NOT_PROVIDED")
        comb_st = TRAFFIC_RED if TRAFFIC_RED in (d_st, p_st) else (
            TRAFFIC_AMBER if TRAFFIC_AMBER in (d_st, p_st) else TRAFFIC_GREEN
        )
        lines.append(
            f"{_dot_for_status(comb_st)} Decay/Postmortem: {pm.get('classification')} ({pm.get('severity')}) | "
            f"decay={dcy.get('verdict', 'N/A')} | SPRT={dcy.get('sprt_state', 'N/A')} | vol={pm.get('vol_ratio')}x"
        )
    else:
        lines.append("⚪ Decay/Postmortem: chua nap chuoi loi nhuan Dev/Live")

    # 5. Feed / DST / Calendar TTL
    ttl = fdt.get("calendar_ttl") or {}
    dst = fdt.get("dst") or {}
    feed = fdt.get("feed_health") or {}
    ttl_days = ttl.get("min_remaining_days")
    if isinstance(ttl_days, (int, float)):
        ttl_txt = f"{ttl_days:.1f}d"
    else:
        ttl_txt = "EXPIRED/MISSING" if ttl.get("provided") else "N/A"
    dst_flag = "DST_DIVERGENCE" if dst.get("is_dst_divergence_window") else "DST_SYNC"
    lines.append(
        f"{_dot_for_status(fdt.get('status', 'NOT_PROVIDED'))} Feed/DST/TTL: TTL={ttl.get('status')} ({ttl_txt}) | "
        f"Feed={feed.get('status')} | {dst_flag} (reset={dst.get('next_daily_reset_utc_iso')})"
    )

    # 6. Heartbeat
    if hb.get("provided"):
        lines.append(
            f"{_dot_for_status(hb['status'])} Heartbeat: {hb.get('ops_status')} | "
            f"age={hb.get('age_seconds')}s | kill={hb.get('kill_switch')} | orphan_no_sl={hb.get('orphan_no_sl')}"
        )
    else:
        lines.append("⚪ Heartbeat: chua nap naqex_heartbeat.json")

    # 7. Compliance / Preflight
    if cmp_s.get("provided"):
        lines.append(
            f"{_dot_for_status(cmp_s['status'])} Compliance OPS-2: inactivity={cmp_s.get('inactivity_status')} "
            f"(days={cmp_s.get('days_since_last_trade')}) | preflight={cmp_s.get('verdict', 'CHECKS_ONLY')}"
        )

    # 8. Optional Ops-Cloud
    if cld.get("provided"):
        net = cld.get("network") or {}
        nd = cld.get("node_digest") or {}
        rn = cld.get("upcoming_red_news_14d") or {}
        lines.append(
            f"{_dot_for_status(cld['status'])} Ops-Cloud: geo={net.get('country_code', 'N/A')} | "
            f"cgnat={net.get('is_cgnat', 'N/A')} | node={nd.get('overall_status', 'N/A')} | "
            f"news14d={rn.get('upcoming_count', 'N/A')}"
        )

    # Triggered findings summary
    findings = list(report.get("findings") or [])
    if findings:
        lines.append("--- Co canh bao kich hoat ---")
        for item in findings[:8]:
            lines.append(f"  {_dot_for_status(item['severity'])} [{item['code']}] {item['message']}")
        if len(findings) > 8:
            lines.append(f"  ... (+{len(findings) - 8} co khac trong JSON receipt)")

    # Objective Action Playbook (strictly G12-safe, zero mid-trade discretion / auto-tuning)
    lines.append("--- Hanh dong bat buoc ---")
    if tl == TRAFFIC_RED:
        lines.append("1. DUNG BOT NGAY: bat InpDryRunLogOnly=true (hoac halt file), KHONG mo them lenh moi.")
        lines.append("2. Dieu tra co RED (parity/orphan/swap!=0/TTL/TCA/SPRT) truoc khi bat lai bot.")
        lines.append("3. TUYET DOI khong tu dong tinh chinh tham so chien luoc tren mau live nho.")
    elif tl == TRAFFIC_AMBER:
        lines.append("1. Ha rui ro ve 0.5x (THROTTLE_TO_0_5X_WATCH) va theo doi chat phien tiep theo.")
        lines.append("2. Neu TTL <= 14d: cap nhat lich tin do truoc 3d; neu Inactivity >= 21d: ra soat lich lenh.")
        lines.append("3. Khong can thiep dong tay giua lenh va khong doi tham so chien luoc theo nhieu ngan han.")
    else:
        lines.append("1. Giu nguyen rui ro 1.0x (KEEP_CURRENT_RISK_1_0X); tat ca cong an toan deu dat chuan.")
        lines.append("2. Luu receipt SHA-256 vao chuoi bang chung van hanh hang ngay.")

    sha_short = str(report.get("report_sha256") or "")[:16]
    if sha_short:
        lines.append(f"Receipt SHA-256: {sha_short} | Read-Only | OrderSend=0")
    else:
        lines.append("Read-Only | OrderSend=0")

    return redact_opsec_text("\n".join(lines), known_logins=known_logins)


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def exit_code_for_report(report: Mapping[str, Any]) -> int:
    """Deterministic CLI exit code: `GREEN -> 0`, `AMBER -> 1`, `RED -> 2`."""
    tl = str(report.get("traffic_light", TRAFFIC_RED))
    if tl == TRAFFIC_GREEN:
        return 0
    if tl == TRAFFIC_AMBER:
        return 1
    return 2


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Single-command read-only Daily/Weekly Live-Ops Pipeline outputting GREEN/AMBER/RED "
            "traffic light + Objective Throttle/Halt Decision Matrix (OrderSend=0)."
        )
    )
    ap.add_argument("--config-json", type=Path, default=None, help="Optional JSON config bundle for all inputs.")
    ap.add_argument("--account-alias", type=str, default=None)
    ap.add_argument("--firm-profile", type=str, default=None)
    ap.add_argument("--period-label", type=str, default=None)
    ap.add_argument("--mode", choices=("daily", "weekly"), default=None)
    ap.add_argument("--now-utc", type=str, default=None, help="ISO-8601 UTC evaluation timestamp.")
    ap.add_argument("--audit-csv", type=Path, default=None, help="Path to naqex_exec_audit.csv")
    ap.add_argument("--statement", type=Path, default=None, help="Path to MT5/FTMO statement CSV or HTML")
    ap.add_argument("--reconcile-json", type=Path, default=None, help="Pre-reconciled JSON report")
    ap.add_argument("--quote-tape", type=Path, default=None, help="Broker quote tape (JSONL or CSV)")
    ap.add_argument("--calibration-fills-csv", type=Path, action="append", default=[])
    ap.add_argument("--spread-jsonl", type=Path, default=None)
    ap.add_argument("--expected-trades-json", type=Path, default=None)
    ap.add_argument("--actual-trades-json", type=Path, default=None)
    ap.add_argument("--decision-blackbox", type=Path, action="append", default=[])
    ap.add_argument("--v103-shadow-csv", type=Path, default=None)
    ap.add_argument("--dev-returns", type=Path, default=None)
    ap.add_argument("--live-returns", type=Path, default=None)
    ap.add_argument("--vol-ratio", type=float, default=None)
    ap.add_argument("--calendar", type=Path, default=None, help="Base red-news CSV or JSON calendar")
    ap.add_argument("--extended-calendar", type=Path, default=None, help="Extended 8-CCY+EIA JSON calendar")
    ap.add_argument("--symbols", type=str, default=None, help="Comma-separated symbol list for TTL/DST checks")
    ap.add_argument("--feed-snapshots-json", type=Path, default=None)
    ap.add_argument("--heartbeat-json", type=Path, default=None)
    ap.add_argument("--heartbeat-stale-sec", type=int, default=180)
    ap.add_argument("--days-since-last-trade", type=float, default=None)
    ap.add_argument("--preflight-config-json", type=Path, default=None)
    ap.add_argument("--node-snapshot-json", type=Path, default=None)
    ap.add_argument("--scoreboard-json", type=Path, default=None)
    ap.add_argument("--upcoming-news-csv", type=Path, default=None)
    ap.add_argument("--allow-nonzero-swap", action="store_true", help="Allow finite non-zero swap (Swing profile).")
    ap.add_argument("--strict-core", action="store_true", help="Fail-closed RED if core telemetry is missing.")
    ap.add_argument("--use-hot-cache", action="store_true", help="Use local pre-2025 hot M1 cache for TCA baselines.")
    ap.add_argument("--bootstrap-draws", type=int, default=10_000)
    ap.add_argument("--out-json", type=Path, default=None, help="Atomic SHA-256 JSON receipt output path.")
    ap.add_argument("--out-digest-txt", type=Path, default=None, help="Telegram-ready digest output text path.")
    ap.add_argument("--json", action="store_true", dest="as_json", help="Print sanitized JSON instead of digest text.")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    kwargs: dict[str, Any] = {}
    if args.config_json is not None:
        raw_cfg = json.loads(args.config_json.read_text(encoding="utf-8"))
        if not isinstance(raw_cfg, Mapping):
            raise ValueError("config-json must contain a JSON object")
        kwargs.update(raw_cfg)

    cli_overrides: dict[str, Any] = {
        "account_alias": args.account_alias,
        "firm_profile": args.firm_profile,
        "period_label": args.period_label,
        "mode": args.mode,
        "now_utc": args.now_utc,
        "audit_csv": args.audit_csv,
        "statement_path": args.statement,
        "reconcile_report": args.reconcile_json,
        "quote_tape_path": args.quote_tape,
        "spread_jsonl_path": args.spread_jsonl,
        "expected_python_trades": args.expected_trades_json,
        "actual_mt5_trades": args.actual_trades_json,
        "v103_shadow_csv": args.v103_shadow_csv,
        "dev_returns": args.dev_returns,
        "live_returns": args.live_returns,
        "vol_ratio": args.vol_ratio,
        "calendar_path": args.calendar,
        "extended_calendar_path": args.extended_calendar,
        "feed_snapshots": args.feed_snapshots_json,
        "heartbeat_path": args.heartbeat_json,
        "days_since_last_trade": args.days_since_last_trade,
        "preflight_config": args.preflight_config_json,
        "node_snapshot": args.node_snapshot_json,
        "scoreboard_path": args.scoreboard_json,
        "upcoming_news_csv": args.upcoming_news_csv,
        "out_json": args.out_json,
        "out_digest_txt": args.out_digest_txt,
    }
    for k, v in cli_overrides.items():
        if v is not None:
            kwargs[k] = v

    if args.calibration_fills_csv:
        kwargs["calibration_fills_csvs"] = list(args.calibration_fills_csv)
    if args.decision_blackbox:
        kwargs["decision_blackbox_path"] = list(args.decision_blackbox)
    if args.symbols:
        kwargs["symbols"] = [s.strip() for s in args.symbols.split(",") if s.strip()]
    if args.allow_nonzero_swap:
        kwargs["require_zero_swap"] = False
    if args.strict_core:
        kwargs["strict_core_subsystems"] = True
    if args.use_hot_cache:
        kwargs["use_hot_cache"] = True
    if "heartbeat_stale_sec" not in kwargs:
        kwargs["heartbeat_stale_sec"] = args.heartbeat_stale_sec
    if "n_bootstrap_draws" not in kwargs:
        kwargs["n_bootstrap_draws"] = args.bootstrap_draws

    report = run_daily_live_ops_pipeline(**kwargs)
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(report["digest_text"])
    return exit_code_for_report(report)


__all__ = [
    "ACTION_HALT_DRYRUN",
    "ACTION_KEEP_1_0X",
    "ACTION_THROTTLE_0_5X",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PIPELINE_SCHEMA",
    "TRAFFIC_ACTION_MATRIX",
    "TRAFFIC_AMBER",
    "TRAFFIC_GREEN",
    "TRAFFIC_RED",
    "build_arg_parser",
    "exit_code_for_report",
    "main",
    "redact_opsec_payload",
    "redact_opsec_text",
    "render_daily_ops_digest",
    "run_daily_live_ops_pipeline",
]


if __name__ == "__main__":
    raise SystemExit(main())
