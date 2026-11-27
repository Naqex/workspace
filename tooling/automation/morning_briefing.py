"""Naqex 07:30 ICT Chief-of-Staff Morning Briefing (`OrderSend = 0`, `MT5_PROCS = 0`, `Holdout = 0`).

Composes ONE single unified, deterministic, plain-Vietnamese morning command report covering all 4 Inside-Out tiers:
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
  6. Unified Wave 4 Inside-Out Feeds (W4-G17, graceful `NOT_INITIALIZED` fallback when absent in CI):
     - Section A (Tier 1/4 Prop Fleet `S0..S7` + `E1..E6`): `fleet_ledger.json` (fallback `sample_fleet_ledger.json`)
       + `fleet_admission_and_edge_cases.py` (`400K USD` FTMO cap, active `E1..E6`, `21/27/30d` inactivity countdown)
     - Section B (Tier 3 Own-Book Shadow `OPS-4`): `ownbook_shadow_ops_summary.json`
       (`GREEN/AMBER/RED`, `CEX % <= 25%`, annualized funding % & `FUNDING_COMPRESSION_ALERT < 3%`)
     - Section C (Tier 4 AI Radar & Macro Supervisor): `ai_model_radar_latest.json` (top budget supervisor + price
       delta alerts) + `prospective_shadow_ledger.json` & `wave4_pit24_and_ai_rubric.json` (Prospective Shadow
       session count from `2026-11-30`, hard monthly API cap `<= 5.00 USD`)
  7. Optional `--notify` dispatch reusing `dispatch_alert_message` & `_scrub_secret_text` from
     `tooling/ai-engines/ops_cloud/heroku_deadman/app.py` (degrades gracefully when env vars unset)

Hard Safety Invariants:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0, MT5_PROCS_LAUNCHED = 0
  - HOLDOUT_ROWS_ANALYSED = 0, SPEND_VND = 0
  - ZERO bare `$` in generated Markdown (enforced via explicit `if ...: raise`, zero `assert`)
  - ZERO `G12` prop-firm support nudges in generated Markdown
  - ZERO OPSEC leaks (tokens, webhooks, private IPs, Windows user paths scrubbed)
  - ZERO Windows console popups (`creationflags=_NO_WINDOW_FLAGS` on every subprocess spawn)
  - LF-only atomic file writes (0 CRLF, 0 BOM)
"""

from __future__ import annotations

import argparse
import html
import importlib.util
import json
import math
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

_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

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
FLEET_GUARDS_REL = "tooling/ai-engines/quant_factory/wave4/fleet_admission_and_edge_cases.py"

# Wave 4 Inside-Out feed relative paths (all read-only, graceful NOT_INITIALIZED when absent in CI)
FLEET_LEDGER_LIVE_REL = ".runtime/offensive4/fleet/fleet_ledger.json"
FLEET_LEDGER_SAMPLE_REL = ".runtime/offensive4/fleet/sample_fleet_ledger.json"
OWNBOOK_SHADOW_SUMMARY_REL = ".runtime/offensive4/frontier/ownbook_shadow_ops_summary.json"
AI_MODEL_RADAR_REL = ".runtime/offensive4/ai/ai_model_radar_latest.json"
PROSPECTIVE_SHADOW_LEDGER_REL = ".runtime/offensive4/ai/prospective_shadow_ledger.json"
AI_PIT24_RUBRIC_REL = ".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json"

FTMO_FUNDED_CAP_USD: float = 400_000.0
FTMO_SINGLE_CHALLENGE_CAP_USD: float = 200_000.0
OWNBOOK_HARD_CEX_CAP_PCT: float = 25.0
OWNBOOK_FUNDING_COMPRESSION_THRESHOLD_PCT: float = 3.0
AI_MAX_MONTHLY_API_USD: float = 5.0
DEFAULT_USD_VND_RATE: float = 25_500.0
DEFAULT_FLEET_USD_VND_RATE: float = 25_765.94
INACTIVITY_WARN_DAYS: float = 21.0
INACTIVITY_URGENT_DAYS: float = 27.0
INACTIVITY_LOCK_DAYS: float = 30.0

_FLEET_CANONICAL_STATES: tuple[str, ...] = (
    "S0_PRE_CHALLENGE",
    "S1_CHALLENGE_P1",
    "S2_PASS_P1_HANDOFF",
    "S3_CHALLENGE_P2",
    "S4_PASS_P2_TO_FUNDED_LOCK",
    "S5_FUNDED_ACTIVE",
    "S6_PAYOUT_AUDIT_AND_HARVEST",
    "S7_AFTER_PAYOUT_ALLOCATOR",
)
_FLEET_INCIDENT_STATES: tuple[str, ...] = (
    "E1_EVAL_FAIL_COOLDOWN",
    "E2_FUNDED_DD_FREEZE",
    "E3_FUNDED_BREACH_POSTMORTEM",
    "CLOSED_ARCHIVED",
)
_FLEET_ACTIVE_EVAL_STATES: frozenset[str] = frozenset({"S1_CHALLENGE_P1", "S3_CHALLENGE_P2"})
_FLEET_EVAL_PIPELINE_STATES: frozenset[str] = frozenset(
    {"S1_CHALLENGE_P1", "S2_PASS_P1_HANDOFF", "S3_CHALLENGE_P2"}
)
_FLEET_ACTIVE_FUNDED_STATES: frozenset[str] = frozenset(
    {"S5_FUNDED_ACTIVE", "S6_PAYOUT_AUDIT_AND_HARVEST", "S7_AFTER_PAYOUT_ALLOCATOR"}
)
_FLEET_COMMITTED_FUNDED_STATES: frozenset[str] = frozenset(
    {
        "S4_PASS_P2_TO_FUNDED_LOCK",
        "S5_FUNDED_ACTIVE",
        "S6_PAYOUT_AUDIT_AND_HARVEST",
        "S7_AFTER_PAYOUT_ALLOCATOR",
        "E2_FUNDED_DD_FREEZE",
    }
)
_FLEET_LIVE_RUNNING_STATES: frozenset[str] = frozenset(
    {"S1_CHALLENGE_P1", "S3_CHALLENGE_P2", "S5_FUNDED_ACTIVE", "S6_PAYOUT_AUDIT_AND_HARVEST"}
)
_FLEET_OCCUPYING_SLOT_STATES: frozenset[str] = frozenset(
    {
        "S1_CHALLENGE_P1",
        "S2_PASS_P1_HANDOFF",
        "S3_CHALLENGE_P2",
        "S4_PASS_P2_TO_FUNDED_LOCK",
        "S5_FUNDED_ACTIVE",
        "S6_PAYOUT_AUDIT_AND_HARVEST",
        "S7_AFTER_PAYOUT_ALLOCATOR",
        "E2_FUNDED_DD_FREEZE",
    }
)

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
_G12_SUPPORT_NUDGE_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)\bliên hệ\s+(?:support|hỗ trợ|ftmo|the5ers)"),
    re.compile(r"(?i)\bcontact\s+(?:support|ftmo|the5ers)"),
    re.compile(r"(?i)\bemail\s+(?:support|ftmo|the5ers)"),
    re.compile(r"(?i)\blive[\s-]?chat\b"),
    re.compile(r"(?i)\bnhắn\s+(?:support|hỗ trợ|ftmo|the5ers)"),
    re.compile(r"(?i)\bgửi\s+(?:mail|email|ticket)\s+(?:cho\s+)?(?:support|hỗ trợ|ftmo|the5ers)"),
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

    try:
        proc = subprocess.run(
            cmd,
            cwd=str(root),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=max(5, int(timeout_sec)),
            creationflags=_NO_WINDOW_FLAGS,
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


def _as_finite_float(val: Any) -> float | None:
    if val is None or isinstance(val, bool) or not isinstance(val, (int, float)):
        return None
    out = float(val)
    if not math.isfinite(out):
        return None
    return out


def _as_nonneg_int(val: Any) -> int | None:
    if type(val) is not int or val < 0:
        return None
    return val


def _normalize_firm_id(raw: Any) -> str:
    txt = str(raw or "").strip().lower()
    if txt.startswith("ftmo"):
        return "ftmo"
    if "5ers" in txt or "the5ers" in txt:
        return "the5ers"
    if "ic_funded" in txt or "icfunded" in txt or "ic funded" in txt:
        return "ic_funded"
    return txt


def _load_fleet_guards_module(root: Path = ROOT) -> Any | None:
    """Load canonical Wave 1B `fleet_admission_and_edge_cases.py` (prefer root, fallback to workspace ROOT)."""
    cand = root / FLEET_GUARDS_REL
    if not cand.is_file():
        cand = ROOT / FLEET_GUARDS_REL
    if not cand.is_file():
        return None
    return _load_module_from_path("_naqex_wave4_fleet_guards", cand)


def _extract_vps_telemetry_from_node(node_digest: dict[str, Any] | None, *, now_utc: datetime) -> dict[str, Any] | None:
    """Extract live VPS telemetry dict compatible with E6 when `node_digest` has real probe data."""
    if not isinstance(node_digest, dict):
        return None
    if not node_digest.get("ssh_attempted"):
        return None
    node = node_digest.get("node")
    if not isinstance(node, dict) or not node:
        return None
    ntp_ms = _as_finite_float(node.get("ntp_offset_ms"))
    hb = node.get("heartbeat")
    if ntp_ms is None or not isinstance(hb, dict):
        return None
    return {
        "node_name": str(node.get("hostname") or "naqex-node1"),
        "ntp_offset_ms": ntp_ms,
        "heartbeat": dict(hb),
        "checked_utc": node_digest.get("checked_utc") or now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }


def collect_prop_fleet_summary(
    *,
    root: Path = ROOT,
    now_utc: datetime,
    node_digest: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Section A — Tier 1/4 Prop Fleet (`S0..S7` + `E1..E6`) with graceful fallback to sample / NOT_INITIALIZED."""
    live_path = root / FLEET_LEDGER_LIVE_REL
    sample_path = root / FLEET_LEDGER_SAMPLE_REL

    if live_path.is_file():
        chosen_path = live_path
        chosen_rel = FLEET_LEDGER_LIVE_REL
        source_mode = "LIVE_LEDGER"
    elif sample_path.is_file():
        chosen_path = sample_path
        chosen_rel = FLEET_LEDGER_SAMPLE_REL
        source_mode = "SAMPLE_FALLBACK"
    else:
        return {
            "present": False,
            "status": "NOT_INITIALIZED",
            "source_mode": "NOT_INITIALIZED",
            "path": FLEET_LEDGER_LIVE_REL,
            "fallback_path": FLEET_LEDGER_SAMPLE_REL,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "total_accounts": 0,
            "active_challenges_count": 0,
            "active_funded_count": 0,
            "ftmo_committed_funded_usd": 0.0,
            "ftmo_funded_cap_usd": FTMO_FUNDED_CAP_USD,
            "ftmo_cap_utilization_pct": 0.0,
            "ftmo_cap_headroom_usd": FTMO_FUNDED_CAP_USD,
            "counts_by_state": {st: 0 for st in (*_FLEET_CANONICAL_STATES, *_FLEET_INCIDENT_STATES)},
            "guards_e1_to_e6": {},
            "active_e1_to_e6_alerts": [],
            "blocking_guards": [],
            "warning_guards": [],
            "inactivity_countdown": [],
            "inactivity_thresholds_days": {
                "warning": int(INACTIVITY_WARN_DAYS),
                "urgent": int(INACTIVITY_URGENT_DAYS),
                "lock": int(INACTIVITY_LOCK_DAYS),
            },
            "scaling_eligible_count": 0,
            "scaling_eligible_account_ids": [],
            "next_actions": [],
            "detail": "Chưa khởi tạo sổ đội Prop (fleet_ledger.json & sample_fleet_ledger.json đều chưa có).",
        }

    raw = _safe_read_json(chosen_path)
    if not isinstance(raw, dict):
        return {
            "present": True,
            "status": "INVALID_JSON",
            "source_mode": source_mode,
            "path": chosen_rel,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "active_e1_to_e6_alerts": ["FLEET_LEDGER_INVALID_JSON"],
            "blocking_guards": ["FLEET_LEDGER_INVALID_JSON"],
            "warning_guards": [],
            "inactivity_countdown": [],
            "ftmo_funded_cap_usd": FTMO_FUNDED_CAP_USD,
            "detail": f"Không thể đọc JSON hợp lệ từ {chosen_rel}.",
        }

    # Fail-closed safety tamper detection
    if (
        raw.get("order_send_capable") is not False
        or _as_nonneg_int(raw.get("order_send_count", 0)) != 0
        or _as_nonneg_int(raw.get("holdout_rows_analysed", 0)) != 0
    ):
        return {
            "present": True,
            "status": "SAFETY_TAMPER_BLOCKED",
            "source_mode": source_mode,
            "path": chosen_rel,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "active_e1_to_e6_alerts": ["FLEET_LEDGER_SAFETY_INVARIANT_TAMPER"],
            "blocking_guards": ["SAFETY_INVARIANT_TAMPER"],
            "warning_guards": [],
            "inactivity_countdown": [],
            "ftmo_funded_cap_usd": FTMO_FUNDED_CAP_USD,
            "detail": "Phát hiện vi phạm khóa an toàn (order_send/holdout) trong fleet ledger.",
        }

    accounts_raw = raw.get("accounts")
    transitions_raw = raw.get("transitions")
    accounts = [dict(a) for a in accounts_raw if isinstance(a, dict)] if isinstance(accounts_raw, list) else []
    transitions = [dict(t) for t in transitions_raw if isinstance(t, dict)] if isinstance(transitions_raw, list) else []
    fleet_policy = raw.get("fleet_policy") if isinstance(raw.get("fleet_policy"), dict) else {}
    usd_vnd = _as_finite_float(raw.get("usd_vnd_rate")) or DEFAULT_FLEET_USD_VND_RATE

    counts_by_state: dict[str, int] = {st: 0 for st in (*_FLEET_CANONICAL_STATES, *_FLEET_INCIDENT_STATES)}
    active_challenges = 0
    active_funded = 0
    s4_lock_pending = 0
    s0_queued = 0
    total_funded_nominal_usd = 0.0
    total_eval_nominal_usd = 0.0
    ftmo_committed_funded_usd = 0.0
    ftmo_eval_pipeline_usd = 0.0
    ftmo_max_single_eval_usd = 0.0
    firm_active_counts: dict[str, int] = {}
    inactivity_countdown: list[dict[str, Any]] = []

    for acct in accounts:
        aid = str(acct.get("account_id") or "UNKNOWN")
        st = str(acct.get("state") or "")
        firm = _normalize_firm_id(acct.get("firm_id") or acct.get("firm_profile"))
        counts_by_state[st] = counts_by_state.get(st, 0) + 1
        cap_usd = _as_finite_float(acct.get("capital_usd")) or 0.0
        base_cap_usd = _as_finite_float(acct.get("base_capital_usd", acct.get("capital_usd"))) or 0.0

        if st == "S0_PRE_CHALLENGE":
            s0_queued += 1
        elif st == "S4_PASS_P2_TO_FUNDED_LOCK":
            s4_lock_pending += 1

        if st in _FLEET_ACTIVE_EVAL_STATES:
            active_challenges += 1
            total_eval_nominal_usd += cap_usd
        if st in _FLEET_ACTIVE_FUNDED_STATES:
            active_funded += 1
            total_funded_nominal_usd += cap_usd
        if st in _FLEET_OCCUPYING_SLOT_STATES and firm:
            firm_active_counts[firm] = firm_active_counts.get(firm, 0) + 1

        if firm == "ftmo":
            if st in _FLEET_COMMITTED_FUNDED_STATES:
                ftmo_committed_funded_usd += base_cap_usd
            elif st in _FLEET_EVAL_PIPELINE_STATES:
                ftmo_eval_pipeline_usd += base_cap_usd
                if base_cap_usd > ftmo_max_single_eval_usd:
                    ftmo_max_single_eval_usd = base_cap_usd

        if st in _FLEET_LIVE_RUNNING_STATES:
            days_idle = _as_finite_float(acct.get("days_since_last_trade"))
            if days_idle is None or days_idle < 0.0:
                inactivity_countdown.append(
                    {
                        "account_id": aid,
                        "firm_id": firm,
                        "state": st,
                        "days_since_last_trade": None,
                        "days_to_warn_21d": None,
                        "days_to_urgent_27d": None,
                        "days_to_lock_30d": None,
                        "level": "INVALID_POISONED",
                    }
                )
            else:
                if days_idle >= INACTIVITY_LOCK_DAYS:
                    lvl = "LOCK_30D"
                elif days_idle >= INACTIVITY_URGENT_DAYS:
                    lvl = "URGENT_27D"
                elif days_idle >= INACTIVITY_WARN_DAYS:
                    lvl = "WARNING_21D"
                else:
                    lvl = "GREEN"
                inactivity_countdown.append(
                    {
                        "account_id": aid,
                        "firm_id": firm,
                        "state": st,
                        "days_since_last_trade": round(days_idle, 1),
                        "days_to_warn_21d": round(max(0.0, INACTIVITY_WARN_DAYS - days_idle), 1),
                        "days_to_urgent_27d": round(max(0.0, INACTIVITY_URGENT_DAYS - days_idle), 1),
                        "days_to_lock_30d": round(max(0.0, INACTIVITY_LOCK_DAYS - days_idle), 1),
                        "level": lvl,
                    }
                )

    inactivity_countdown.sort(
        key=lambda r: (
            -(r["days_since_last_trade"] if r["days_since_last_trade"] is not None else 9999.0),
            r["account_id"],
        )
    )

    ftmo_projected_total_usd = ftmo_committed_funded_usd + ftmo_eval_pipeline_usd
    ftmo_cap_util_pct = round((ftmo_committed_funded_usd / FTMO_FUNDED_CAP_USD) * 100.0, 2)
    ftmo_cap_headroom_usd = round(max(0.0, FTMO_FUNDED_CAP_USD - ftmo_committed_funded_usd), 2)

    # Evaluate canonical E1..E6 guards by composing fleet_admission_and_edge_cases.py
    guards_mod = _load_fleet_guards_module(root)
    guard_statuses: dict[str, dict[str, Any]] = {}
    blocking_guards: list[str] = []
    warning_guards: list[str] = []
    active_alerts: list[str] = []
    fleet_scale_factor = 1.0
    scaling_eligible_ids: list[str] = []
    vps_telemetry = raw.get("vps_telemetry") if isinstance(raw.get("vps_telemetry"), dict) else None
    if vps_telemetry is None:
        vps_telemetry = _extract_vps_telemetry_from_node(node_digest, now_utc=now_utc)
    vps_telemetry_mode = "LIVE_OR_FIXTURE" if vps_telemetry is not None else "OFFLINE_ACCOUNT_ONLY"

    if guards_mod is not None:
        ops6_eval_rcpt = raw.get("ops6_eval_receipt") or raw.get("ops6_forensic_review_receipt")
        ops6_pms = raw.get("ops6_postmortems")
        active_sigs = raw.get("active_signals")

        g_e1 = guards_mod.evaluate_e1_eval_fail_cooldown(
            accounts, transitions, now_dt=now_utc, ops6_eval_receipt=ops6_eval_rcpt
        )
        g_e2 = guards_mod.evaluate_e2_funded_dd_freeze(accounts)
        g_e3 = guards_mod.evaluate_e3_funded_breach_postmortem(
            accounts, transitions, now_dt=now_utc, ops6_postmortems=ops6_pms
        )
        g_e5 = guards_mod.evaluate_e5_cross_account_opposite_hedge(
            accounts, None, active_signals=active_sigs
        )
        eff_vps = vps_telemetry or {
            "ntp_offset_ms": 0.0,
            "heartbeat": {
                "utc_ts": now_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "open_positions": 0,
                "terminal_connected": True,
                "kill_switch": False,
                "orphan_no_sl": 0,
            },
        }
        g_e6 = guards_mod.evaluate_e6_inactivity_or_feed_stale_lock(
            accounts, None, eff_vps, now_dt=now_utc
        )
        fleet_scale_factor = float(g_e2.details.get("scale_factor", 1.0))

        # E4 standing fleet cap & concurrency evaluation (no proposed ticket required)
        e4_blocks: list[str] = []
        e4_warns: list[str] = []
        max_evals = _as_nonneg_int(fleet_policy.get("max_concurrent_evals", 2))
        max_funded = _as_nonneg_int(fleet_policy.get("max_concurrent_funded", 4))
        max_per_firm = _as_nonneg_int(fleet_policy.get("max_accounts_per_firm", 3))
        if ftmo_committed_funded_usd > FTMO_FUNDED_CAP_USD + 1e-9:
            e4_blocks.append("E4_FTMO_400K_FUNDED_CAP_EXCEEDED")
        elif ftmo_projected_total_usd > FTMO_FUNDED_CAP_USD + 1e-9:
            e4_blocks.append("E4_FTMO_400K_PROJECTED_ALLOCATION_EXCEEDED")
        elif ftmo_cap_util_pct >= 80.0:
            e4_warns.append("E4_FTMO_400K_CAP_NEAR_LIMIT_GE_80PCT")
        if ftmo_max_single_eval_usd > FTMO_SINGLE_CHALLENGE_CAP_USD + 1e-9:
            e4_blocks.append("E4_FTMO_SINGLE_CHALLENGE_200K_CAP_EXCEEDED")
        if max_evals is not None and active_challenges > max_evals:
            e4_blocks.append("E4_MAX_CONCURRENT_EVALS_EXCEEDED")
        if max_funded is not None and active_funded > max_funded:
            e4_blocks.append("E4_MAX_CONCURRENT_FUNDED_EXCEEDED")
        if max_per_firm is not None and any(cnt > max_per_firm for cnt in firm_active_counts.values()):
            e4_blocks.append("E4_FIRM_SLOT_LIMIT_EXCEEDED")
        e4_status = "BLOCK" if e4_blocks else ("WARNING" if e4_warns else "PASS")

        e4_dict = {
            "guard_id": "E4_CAP_OR_VPS_OVERFLOW",
            "status": e4_status,
            "blocking": bool(e4_blocks),
            "blocking_reasons": e4_blocks,
            "warnings": e4_warns,
        }
        all_guards_list = [
            ("E1_EVAL_FAIL_COOLDOWN", g_e1.to_dict()),
            ("E2_FUNDED_DD_FREEZE", g_e2.to_dict()),
            ("E3_FUNDED_BREACH_POSTMORTEM", g_e3.to_dict()),
            ("E4_CAP_OR_VPS_OVERFLOW", e4_dict),
            ("E5_CROSS_ACCOUNT_OPPOSITE_HEDGE", g_e5.to_dict()),
            ("E6_INACTIVITY_OR_FEED_STALE_LOCK", g_e6.to_dict()),
        ]
        for gid, gdict in all_guards_list:
            g_blocks = list(gdict.get("blocking_reasons") or [])
            g_warns = list(gdict.get("warnings") or [])
            g_st = str(gdict.get("status") or "PASS")
            guard_statuses[gid] = {
                "status": g_st,
                "blocking": bool(gdict.get("blocking")),
                "blocking_reasons": g_blocks,
                "warnings": g_warns,
            }
            if gdict.get("blocking"):
                blocking_guards.append(gid)
                active_alerts.extend(g_blocks)
            elif g_warns or g_st in ("WARNING", "URGENT"):
                warning_guards.append(gid)
                active_alerts.extend(g_warns)

        scaling_summary = guards_mod.evaluate_fleet_scaling_tracker(accounts, now_utc=now_utc)
        scaling_eligible_ids = list(scaling_summary.eligible_account_ids)
    else:
        # Minimal fallback if guards module absent
        if ftmo_committed_funded_usd > FTMO_FUNDED_CAP_USD + 1e-9:
            blocking_guards.append("E4_CAP_OR_VPS_OVERFLOW")
            active_alerts.append("E4_FTMO_400K_FUNDED_CAP_EXCEEDED")
        for row in inactivity_countdown:
            if row["level"] == "LOCK_30D":
                blocking_guards.append("E6_INACTIVITY_OR_FEED_STALE_LOCK")
                active_alerts.append("E6_INACTIVITY_30D_LOCK")
            elif row["level"] in ("URGENT_27D", "WARNING_21D"):
                warning_guards.append("E6_INACTIVITY_OR_FEED_STALE_LOCK")
                active_alerts.append(f"E6_INACTIVITY_{row['level']}")

    # Deduplicate alerts deterministically
    dedup_alerts: list[str] = []
    for code in active_alerts:
        if code and code not in dedup_alerts:
            dedup_alerts.append(code)

    if blocking_guards:
        fleet_status = "BLOCK_ATTENTION"
    elif warning_guards:
        fleet_status = "AMBER_WATCH"
    elif not accounts:
        fleet_status = "EMPTY_LEDGER"
    else:
        fleet_status = "GREEN_READY"

    raw_summary = raw.get("fleet_summary") if isinstance(raw.get("fleet_summary"), dict) else {}
    raw_actions = raw_summary.get("next_actions") if isinstance(raw_summary.get("next_actions"), list) else []
    next_actions = [
        {
            "account_id": str(a.get("account_id") or ""),
            "state": str(a.get("state") or ""),
            "action_code": str(a.get("action_code") or ""),
        }
        for a in raw_actions[:5]
        if isinstance(a, dict)
    ]

    return {
        "present": True,
        "status": fleet_status,
        "source_mode": source_mode,
        "path": chosen_rel,
        "ledger_id": str(raw.get("ledger_id") or ""),
        "updated_utc": raw.get("updated_utc"),
        "order_send_capable": False,
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "usd_vnd_rate": round(usd_vnd, 2),
        "total_accounts": len(accounts),
        "queued_s0_count": s0_queued,
        "funded_lock_pending_s4_count": s4_lock_pending,
        "active_challenges_count": active_challenges,
        "active_funded_count": active_funded,
        "total_eval_nominal_usd": round(total_eval_nominal_usd, 2),
        "total_funded_nominal_usd": round(total_funded_nominal_usd, 2),
        "total_funded_nominal_vnd": round(total_funded_nominal_usd * usd_vnd),
        "ftmo_committed_funded_usd": round(ftmo_committed_funded_usd, 2),
        "ftmo_eval_pipeline_usd": round(ftmo_eval_pipeline_usd, 2),
        "ftmo_projected_total_usd": round(ftmo_projected_total_usd, 2),
        "ftmo_funded_cap_usd": FTMO_FUNDED_CAP_USD,
        "ftmo_cap_utilization_pct": ftmo_cap_util_pct,
        "ftmo_cap_headroom_usd": ftmo_cap_headroom_usd,
        "ftmo_cap_headroom_vnd": round(ftmo_cap_headroom_usd * usd_vnd),
        "counts_by_state": counts_by_state,
        "fleet_scale_factor": round(fleet_scale_factor, 2),
        "guards_module_loaded": guards_mod is not None,
        "vps_telemetry_mode": vps_telemetry_mode,
        "guards_e1_to_e6": guard_statuses,
        "blocking_guards": blocking_guards,
        "warning_guards": warning_guards,
        "active_e1_to_e6_alerts": dedup_alerts,
        "inactivity_thresholds_days": {
            "warning": int(INACTIVITY_WARN_DAYS),
            "urgent": int(INACTIVITY_URGENT_DAYS),
            "lock": int(INACTIVITY_LOCK_DAYS),
        },
        "inactivity_countdown": inactivity_countdown,
        "max_days_since_last_trade": (
            inactivity_countdown[0]["days_since_last_trade"] if inactivity_countdown else None
        ),
        "min_days_to_30d_lock": (
            inactivity_countdown[0]["days_to_lock_30d"] if inactivity_countdown else None
        ),
        "scaling_eligible_count": len(scaling_eligible_ids),
        "scaling_eligible_account_ids": scaling_eligible_ids,
        "next_actions": next_actions,
    }


def collect_ownbook_shadow_summary(*, root: Path = ROOT) -> dict[str, Any]:
    """Section B — Tier 3 Own-Book Shadow (`OPS-4`) from `ownbook_shadow_ops_summary.json`."""
    path = root / OWNBOOK_SHADOW_SUMMARY_REL
    if not path.is_file():
        return {
            "present": False,
            "status": "NOT_INITIALIZED",
            "path": OWNBOOK_SHADOW_SUMMARY_REL,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "traffic_light": "NOT_INITIALIZED",
            "cex_exposure_pct": None,
            "cex_cap_pct": OWNBOOK_HARD_CEX_CAP_PCT,
            "cex_cap_compliant": None,
            "annualized_funding_rate_pct": None,
            "funding_compression_threshold_pct": OWNBOOK_FUNDING_COMPRESSION_THRESHOLD_PCT,
            "funding_compression_active": False,
            "active_alerts": [],
            "detail": "Chưa có file tóm tắt Own-Book Shadow (ownbook_shadow_ops_summary.json).",
        }

    raw = _safe_read_json(path)
    if not isinstance(raw, dict):
        return {
            "present": True,
            "status": "INVALID_JSON",
            "path": OWNBOOK_SHADOW_SUMMARY_REL,
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "traffic_light": "INVALID_JSON",
            "cex_cap_pct": OWNBOOK_HARD_CEX_CAP_PCT,
            "funding_compression_threshold_pct": OWNBOOK_FUNDING_COMPRESSION_THRESHOLD_PCT,
            "funding_compression_active": False,
            "active_alerts": ["OWNBOOK_SUMMARY_INVALID_JSON"],
        }

    snap = raw.get("ops4_health_snapshot") if isinstance(raw.get("ops4_health_snapshot"), dict) else {}
    inv = raw.get("invariants") if isinstance(raw.get("invariants"), dict) else {}
    perf = raw.get("ownbook_dev_performance") if isinstance(raw.get("ownbook_dev_performance"), dict) else {}
    guarded = perf.get("guarded_metrics") if isinstance(perf.get("guarded_metrics"), dict) else {}
    stress_sum = snap.get("stress_summary") if isinstance(snap.get("stress_summary"), dict) else {}

    traffic_light = str(snap.get("traffic_light") or "UNKNOWN").strip().upper()
    action = str(snap.get("action") or "UNKNOWN")
    risk_mult = _as_finite_float(snap.get("risk_multiplier"))
    cex_pct = _as_finite_float(snap.get("cex_exposure_pct"))
    cex_cap = _as_finite_float(snap.get("cex_cap_pct")) or _as_finite_float(inv.get("hard_cex_cap_pct"))
    if cex_cap is None:
        cex_cap = OWNBOOK_HARD_CEX_CAP_PCT
    funding_pct = _as_finite_float(snap.get("annualized_funding_rate_pct"))
    funding_thr = _as_finite_float(snap.get("funding_compression_threshold_pct")) or _as_finite_float(
        inv.get("funding_compression_threshold_pct")
    )
    if funding_thr is None:
        funding_thr = OWNBOOK_FUNDING_COMPRESSION_THRESHOLD_PCT

    alerts = [str(a) for a in (snap.get("active_alerts") or []) if str(a).strip()]
    cex_compliant = bool(snap.get("cex_cap_compliant", True))
    if cex_pct is not None and cex_pct > cex_cap + 1e-9:
        cex_compliant = False
        traffic_light = "RED"
        if "CEX_CAP_25PCT_BREACH" not in alerts:
            alerts.append("CEX_CAP_25PCT_BREACH")

    funding_compression = bool(snap.get("funding_compression_active", False))
    if funding_pct is not None and funding_pct < funding_thr:
        funding_compression = True
    if "FUNDING_COMPRESSION_ALERT" in alerts:
        funding_compression = True
    if funding_compression:
        if "FUNDING_COMPRESSION_ALERT" not in alerts:
            alerts.append("FUNDING_COMPRESSION_ALERT")
        if traffic_light == "GREEN":
            traffic_light = "AMBER"

    if traffic_light == "RED" or not cex_compliant:
        status = "RED_HALT"
    elif traffic_light == "AMBER" or funding_compression:
        status = "AMBER_WATCH"
    elif traffic_light == "GREEN":
        status = "GREEN_READY"
    else:
        status = traffic_light

    return {
        "present": True,
        "status": status,
        "path": OWNBOOK_SHADOW_SUMMARY_REL,
        "generated_utc": raw.get("generated_utc"),
        "as_of_date": snap.get("as_of_date"),
        "order_send_capable": False,
        "order_send_count": int(inv.get("order_send_count", 0) or 0),
        "holdout_cutoff_date": str(
            inv.get("holdout_cutoff_inclusive") or snap.get("holdout_cutoff_date") or "2024-12-31"
        ),
        "holdout_rows_analysed": int(inv.get("holdout_rows_analysed", 0) or 0),
        "traffic_light": traffic_light,
        "action": action,
        "risk_multiplier": risk_mult,
        "cex_exposure_pct": round(cex_pct, 2) if cex_pct is not None else None,
        "cex_cap_pct": round(cex_cap, 2),
        "cex_cap_compliant": cex_compliant,
        "annualized_funding_rate_pct": round(funding_pct, 2) if funding_pct is not None else None,
        "funding_compression_threshold_pct": round(funding_thr, 2),
        "funding_compression_active": funding_compression,
        "rotated_carry_to_tbill_pct": _as_finite_float(snap.get("rotated_carry_to_tbill_pct")) or 0.0,
        "tbill_buffer_vehicle": str(snap.get("tbill_buffer_vehicle") or "SGOV/BIL"),
        "current_dd_pct": _as_finite_float(snap.get("current_dd_pct")),
        "active_alerts": alerts,
        "stress_passed": int(stress_sum.get("passed", 0) or 0),
        "stress_total": int(stress_sum.get("total", 0) or 0),
        "dev_cagr_pct": _as_finite_float(guarded.get("cagr_pct")),
        "dev_sharpe": _as_finite_float(guarded.get("sharpe")),
        "dev_max_dd_pct": _as_finite_float(guarded.get("max_dd_pct")),
        "dev_calmar": _as_finite_float(guarded.get("calmar")),
    }


def collect_ai_radar_and_supervisor_summary(*, root: Path = ROOT) -> dict[str, Any]:
    """Section C — Tier 4 AI Radar & Macro Supervisor (advisory-only, monthly API budget <= 5.00 USD)."""
    radar_path = root / AI_MODEL_RADAR_REL
    ledger_path = root / PROSPECTIVE_SHADOW_LEDGER_REL
    rubric_path = root / AI_PIT24_RUBRIC_REL

    radar_raw = _safe_read_json(radar_path) if radar_path.is_file() else None
    ledger_raw = _safe_read_json(ledger_path) if ledger_path.is_file() else None
    rubric_raw = _safe_read_json(rubric_path) if rubric_path.is_file() else None

    any_present = any(p.is_file() for p in (radar_path, ledger_path, rubric_path))
    if not any_present:
        return {
            "present": False,
            "status": "NOT_INITIALIZED",
            "order_send_capable": False,
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "monthly_api_budget_cap_usd": AI_MAX_MONTHLY_API_USD,
            "monthly_api_budget_cap_vnd": round(AI_MAX_MONTHLY_API_USD * DEFAULT_USD_VND_RATE),
            "budget_compliant": True,
            "radar": {"present": False, "status": "NOT_INITIALIZED", "path": AI_MODEL_RADAR_REL},
            "prospective_shadow": {
                "present": False,
                "status": "NOT_INITIALIZED",
                "path": PROSPECTIVE_SHADOW_LEDGER_REL,
                "first_live_session_date": "2026-11-30",
                "commitments_count": 0,
                "distinct_session_dates": 0,
                "min_audit_calendar_days": 30,
                "ready_for_prospective_oos_audit": False,
            },
            "pit24_and_rubric": {"present": False, "status": "NOT_INITIALIZED", "path": AI_PIT24_RUBRIC_REL},
            "alerts": [],
            "detail": "Chưa có dữ liệu AI Model Radar / Prospective Shadow Ledger / PIT-24 Rubric.",
        }

    alerts: list[str] = []
    usd_vnd = DEFAULT_USD_VND_RATE
    budget_cap_usd = AI_MAX_MONTHLY_API_USD

    # 1. AI Model Radar
    if isinstance(radar_raw, dict):
        wa = radar_raw.get("workload_assumptions") if isinstance(radar_raw.get("workload_assumptions"), dict) else {}
        hi = radar_raw.get("hard_invariants") if isinstance(radar_raw.get("hard_invariants"), dict) else {}
        usd_vnd = _as_finite_float(wa.get("usd_vnd_rate")) or DEFAULT_USD_VND_RATE
        budget_cap_usd = (
            _as_finite_float(wa.get("budget_cap_usd_per_month"))
            or _as_finite_float(hi.get("max_official_api_usd_per_month"))
            or AI_MAX_MONTHLY_API_USD
        )
        lbs = radar_raw.get("leaderboards") if isinstance(radar_raw.get("leaderboards"), dict) else {}
        lb_sum = radar_raw.get("leaderboard_summary") if isinstance(radar_raw.get("leaderboard_summary"), dict) else {}
        budget_rows = lbs.get("budget_macro_supervisor_monthly_usd")
        top_budget: list[dict[str, Any]] = []
        if isinstance(budget_rows, list):
            for row in budget_rows[:3]:
                if not isinstance(row, dict):
                    continue
                m_usd = _as_finite_float(row.get("monthly_usd"))
                m_vnd = _as_finite_float(row.get("monthly_vnd"))
                if m_vnd is None and m_usd is not None:
                    m_vnd = round(m_usd * usd_vnd)
                top_budget.append(
                    {
                        "rank": int(row.get("rank", len(top_budget) + 1) or (len(top_budget) + 1)),
                        "id": str(row.get("id") or "unknown"),
                        "name": str(row.get("name") or row.get("id") or "unknown"),
                        "monthly_usd": round(m_usd, 4) if m_usd is not None else None,
                        "monthly_vnd": int(round(m_vnd)) if m_vnd is not None else None,
                        "budget_utilization_pct": _as_finite_float(row.get("budget_utilization_pct")),
                        "within_budget_cap": bool(row.get("within_budget_cap", True)),
                    }
                )

        local_rows = lbs.get("local_open_weight_fit")
        top_local: dict[str, Any] | None = None
        if isinstance(local_rows, list) and local_rows and isinstance(local_rows[0], dict):
            loc0 = local_rows[0]
            top_local = {
                "id": str(loc0.get("id") or ""),
                "q4_estimated_gb": _as_finite_float(loc0.get("q4_estimated_gb")),
                "q4_fit_tier": str(loc0.get("q4_fit_tier") or ""),
            }

        pdelta = radar_raw.get("price_delta") if isinstance(radar_raw.get("price_delta"), dict) else {}
        pd_counts = pdelta.get("counts") if isinstance(pdelta.get("counts"), dict) else {}
        raw_changes = pdelta.get("price_changes_pct")
        top_price_changes: list[dict[str, Any]] = []
        if isinstance(raw_changes, list):
            for ch in raw_changes[:5]:
                if not isinstance(ch, dict):
                    continue
                top_price_changes.append(
                    {
                        "id": str(ch.get("id") or ""),
                        "direction": str(ch.get("direction") or ""),
                        "monthly_delta_pct": _as_finite_float(ch.get("monthly_delta_pct")),
                        "curr_monthly_usd": _as_finite_float(ch.get("curr_monthly_usd")),
                    }
                )
        n_changes = int(pd_counts.get("price_changes", len(top_price_changes)) or 0)
        n_new = int(pd_counts.get("new_models", len(pdelta.get("new_models") or [])) or 0)
        n_removed = int(pd_counts.get("removed_models", len(pdelta.get("removed_models") or [])) or 0)
        n_drops = int(pd_counts.get("price_drops", 0) or 0)
        n_inc = int(pd_counts.get("price_increases", 0) or 0)
        has_price_delta_alert = (n_changes > 0) or (n_new > 0) or (n_removed > 0)
        if has_price_delta_alert:
            alerts.append(
                f"AI_RADAR_PRICE_DELTA(changes={n_changes},drops={n_drops},increases={n_inc},new={n_new})"
            )

        radar_info: dict[str, Any] = {
            "present": True,
            "status": "AVAILABLE",
            "path": AI_MODEL_RADAR_REL,
            "generated_utc": radar_raw.get("generated_utc"),
            "budget_eligible_count": int(lb_sum.get("budget_eligible_count", 0) or 0),
            "top_budget_supervisor": top_budget[0] if top_budget else None,
            "top_budget_supervisors": top_budget,
            "top_local_ollama_fit": top_local,
            "price_delta": {
                "has_previous_snapshot": bool(pdelta.get("has_previous_snapshot", False)),
                "has_alert": has_price_delta_alert,
                "counts": {
                    "new_models": n_new,
                    "removed_models": n_removed,
                    "price_changes": n_changes,
                    "price_drops": n_drops,
                    "price_increases": n_inc,
                },
                "top_changes": top_price_changes,
            },
        }
    else:
        radar_info = {
            "present": radar_path.is_file(),
            "status": "INVALID_JSON" if radar_path.is_file() else "NOT_INITIALIZED",
            "path": AI_MODEL_RADAR_REL,
            "top_budget_supervisor": None,
            "top_budget_supervisors": [],
            "price_delta": {"has_alert": False, "counts": {}},
        }

    # 2. Prospective Shadow Ledger (with fallback to nested snapshot in rubric JSON)
    nested_shadow = (
        rubric_raw.get("prospective_shadow_ledger")
        if isinstance(rubric_raw, dict) and isinstance(rubric_raw.get("prospective_shadow_ledger"), dict)
        else None
    )
    if isinstance(ledger_raw, dict):
        lsum = ledger_raw.get("summary") if isinstance(ledger_raw.get("summary"), dict) else {}
        commits_raw = ledger_raw.get("commitments")
        commits_cnt = int(
            lsum.get("commitments_count", len(commits_raw) if isinstance(commits_raw, list) else 0) or 0
        )
        distinct_days = int(lsum.get("distinct_session_dates", 0) or 0)
        span_days = int(lsum.get("calendar_span_days", 0) or 0)
        min_days = int(
            lsum.get("min_audit_calendar_days") or ledger_raw.get("min_audit_calendar_days") or 30
        )
        verified_ok = bool(lsum.get("verified", True))
        if not verified_ok:
            alerts.append("PROSPECTIVE_SHADOW_CHAIN_UNVERIFIED")
        shadow_info: dict[str, Any] = {
            "present": True,
            "status": "READY_FOR_OOS_AUDIT" if lsum.get("ready_for_prospective_oos_audit") else "ACCUMULATING",
            "path": PROSPECTIVE_SHADOW_LEDGER_REL,
            "first_live_session_date": str(
                lsum.get("first_live_session_date") or ledger_raw.get("first_live_session_date") or "2026-11-30"
            ),
            "commitments_count": commits_cnt,
            "distinct_session_dates": distinct_days,
            "calendar_span_days": span_days,
            "min_audit_calendar_days": min_days,
            "ready_for_prospective_oos_audit": bool(lsum.get("ready_for_prospective_oos_audit", False)),
            "verified": verified_ok,
            "prospective_only": bool(ledger_raw.get("prospective_only", True)),
            "head_sha256_prefix": str(lsum.get("head_sha256") or "")[:12],
        }
    elif nested_shadow is not None:
        shadow_info = {
            "present": True,
            "status": "READY_FOR_OOS_AUDIT" if nested_shadow.get("ready_for_prospective_oos_audit") else "ACCUMULATING",
            "path": AI_PIT24_RUBRIC_REL,
            "first_live_session_date": str(nested_shadow.get("first_live_session_date") or "2026-11-30"),
            "commitments_count": int(nested_shadow.get("commitments_count", 0) or 0),
            "distinct_session_dates": int(nested_shadow.get("distinct_session_dates", 0) or 0),
            "calendar_span_days": int(nested_shadow.get("calendar_span_days", 0) or 0),
            "min_audit_calendar_days": int(nested_shadow.get("min_audit_calendar_days", 30) or 30),
            "ready_for_prospective_oos_audit": bool(nested_shadow.get("ready_for_prospective_oos_audit", False)),
            "verified": bool(nested_shadow.get("verified", True)),
            "prospective_only": bool(nested_shadow.get("prospective_only", True)),
            "head_sha256_prefix": str(nested_shadow.get("head_sha256") or "")[:12],
        }
    else:
        shadow_info = {
            "present": ledger_path.is_file(),
            "status": "INVALID_JSON" if ledger_path.is_file() else "NOT_INITIALIZED",
            "path": PROSPECTIVE_SHADOW_LEDGER_REL,
            "first_live_session_date": "2026-11-30",
            "commitments_count": 0,
            "distinct_session_dates": 0,
            "calendar_span_days": 0,
            "min_audit_calendar_days": 30,
            "ready_for_prospective_oos_audit": False,
            "verified": False,
        }

    # 3. PIT-24 Benchmark & 6-Criteria AI Architecture Rubric
    if isinstance(rubric_raw, dict):
        pit = rubric_raw.get("pit24_benchmark") if isinstance(rubric_raw.get("pit24_benchmark"), dict) else {}
        rub = (
            rubric_raw.get("ai_architecture_benchmark_6criteria")
            if isinstance(rubric_raw.get("ai_architecture_benchmark_6criteria"), dict)
            else {}
        )
        lat = pit.get("latency_ms_ok") if isinstance(pit.get("latency_ms_ok"), dict) else {}
        stack = rub.get("recommended_hybrid_stack") if isinstance(rub.get("recommended_hybrid_stack"), dict) else {}
        pit_info: dict[str, Any] = {
            "present": True,
            "status": str(pit.get("outcome_status") or "AVAILABLE"),
            "path": AI_PIT24_RUBRIC_REL,
            "generated_utc": rubric_raw.get("generated_utc"),
            "selected_model": str(pit.get("selected_model") or ""),
            "scenarios_ok": int(pit.get("scenarios_ok", 0) or 0),
            "scenarios_total": int(pit.get("scenarios_total", 24) or 24),
            "json_schema_valid_pct": _as_finite_float(pit.get("json_schema_valid_rate_of_24_pct")),
            "regime_agreement_pct": _as_finite_float(pit.get("regime_agreement_rate_of_ok_pct")),
            "latency_p50_ms": _as_finite_float(lat.get("p50_ms")),
            "latency_p95_ms": _as_finite_float(lat.get("p95_ms")),
            "recommended_execution_filter": str(stack.get("execution_path_filter") or ""),
            "recommended_macro_advisory": str(stack.get("pre_session_macro_advisory") or ""),
            "recommended_offline_fallback": str(stack.get("offline_degraded_fallback") or ""),
        }
    else:
        pit_info = {
            "present": rubric_path.is_file(),
            "status": "INVALID_JSON" if rubric_path.is_file() else "NOT_INITIALIZED",
            "path": AI_PIT24_RUBRIC_REL,
        }

    top_sup = radar_info.get("top_budget_supervisor")
    top_monthly_usd = _as_finite_float(top_sup.get("monthly_usd")) if isinstance(top_sup, dict) else None
    budget_compliant = (budget_cap_usd <= AI_MAX_MONTHLY_API_USD + 1e-9) and (
        top_monthly_usd is None or top_monthly_usd <= AI_MAX_MONTHLY_API_USD + 1e-9
    )
    if not budget_compliant:
        alerts.append("AI_MONTHLY_API_BUDGET_CAP_5USD_EXCEEDED")

    if not budget_compliant or "PROSPECTIVE_SHADOW_CHAIN_UNVERIFIED" in alerts:
        overall_ai_status = "BLOCK_ATTENTION"
    elif radar_info.get("price_delta", {}).get("has_alert"):
        overall_ai_status = "AMBER_WATCH"
    else:
        overall_ai_status = "GREEN_READY"

    return {
        "present": True,
        "status": overall_ai_status,
        "order_send_capable": False,
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "usd_vnd_rate": round(usd_vnd, 2),
        "monthly_api_budget_cap_usd": round(budget_cap_usd, 2),
        "monthly_api_budget_cap_vnd": int(round(budget_cap_usd * usd_vnd)),
        "estimated_top_supervisor_monthly_usd": top_monthly_usd,
        "budget_compliant": budget_compliant,
        "radar": radar_info,
        "prospective_shadow": shadow_info,
        "pit24_and_rubric": pit_info,
        "alerts": alerts,
    }


def build_wave4_inside_out_tiers(
    *,
    prop_fleet: dict[str, Any],
    ownbook_shadow: dict[str, Any],
    ai_radar_supervisor: dict[str, Any],
    daily_ops: dict[str, Any],
    node_digest: dict[str, Any],
) -> dict[str, dict[str, Any]]:
    """Build compact 4-tier Inside-Out summary so ONE morning briefing covers all 4 tiers."""
    return {
        "tier_1_cfd_prop_fleet": {
            "label_vi": "Tầng 1 — Đội CFD Prop (S0..S7 + E1..E6)",
            "status": prop_fleet.get("status", "NOT_INITIALIZED"),
            "source_mode": prop_fleet.get("source_mode", "NOT_INITIALIZED"),
            "active_challenges": int(prop_fleet.get("active_challenges_count", 0) or 0),
            "active_funded": int(prop_fleet.get("active_funded_count", 0) or 0),
            "ftmo_cap_utilization_pct": prop_fleet.get("ftmo_cap_utilization_pct", 0.0),
            "active_alerts_count": len(prop_fleet.get("active_e1_to_e6_alerts") or []),
        },
        "tier_2_futures_prop_research": {
            "label_vi": "Tầng 2 — Futures Prop (Nghiên cứu offline, chưa mở live)",
            "status": "RESEARCH_OFFLINE_ONLY",
            "order_send_count": 0,
        },
        "tier_3_ownbook_shadow": {
            "label_vi": "Tầng 3 — Own-Book Shadow (OPS-4, CEX <= 25%)",
            "status": ownbook_shadow.get("status", "NOT_INITIALIZED"),
            "traffic_light": ownbook_shadow.get("traffic_light", "NOT_INITIALIZED"),
            "cex_exposure_pct": ownbook_shadow.get("cex_exposure_pct"),
            "annualized_funding_rate_pct": ownbook_shadow.get("annualized_funding_rate_pct"),
            "funding_compression_active": bool(ownbook_shadow.get("funding_compression_active", False)),
        },
        "tier_4_ai_radar_and_live_ops": {
            "label_vi": "Tầng 4 — Live-Ops, AI Model Radar & Macro Supervisor",
            "status": ai_radar_supervisor.get("status", "NOT_INITIALIZED"),
            "daily_ops_status": daily_ops.get("status", "ABSENT"),
            "node1_status": node_digest.get("overall_status", "ABSENT"),
            "monthly_api_budget_cap_usd": ai_radar_supervisor.get("monthly_api_budget_cap_usd", AI_MAX_MONTHLY_API_USD),
            "prospective_sessions": int(
                (ai_radar_supervisor.get("prospective_shadow") or {}).get("distinct_session_dates", 0) or 0
            ),
        },
    }


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
    pf = briefing.get("prop_fleet", {})
    ob = briefing.get("ownbook_shadow", {})
    ai = briefing.get("ai_radar_supervisor", {})

    gen_ict = briefing.get("generated_ict")
    ov_st = briefing.get("overall_status")
    ops_score = ops.get("health_score", "N/A")
    ops_max = ops.get("max_score", 100)
    ops_st = ops.get("status")
    nd_st = nd.get("overall_status")
    rn_cnt = int(rn.get("upcoming_48h_count", 0))
    pf_st = pf.get("status", "NOT_INITIALIZED")
    ob_tl = ob.get("traffic_light", "NOT_INITIALIZED")
    ai_st = ai.get("status", "NOT_INITIALIZED")

    plain_lines = [
        f"[NAQEX MORNING BRIEFING] {gen_ict} | Status={ov_st} | OrderSend=0",
        f"DailyOps={ops_score}/{ops_max} ({ops_st}) | Node1={nd_st}",
        f"RedNews48h={rn_cnt} events | Fleet={pf_st} | OwnBook={ob_tl} | AISup={ai_st}",
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
    esc_w4 = (
        f"Fleet={html.escape(str(pf_st))} · OwnBook={html.escape(str(ob_tl))} · AISup={html.escape(str(ai_st))}"
    )
    html_lines = [
        f"<b>NAQEX MORNING BRIEFING</b> · <code>{html.escape(str(gen_ict))}</code>",
        f"• Trạng thái: <code>{html.escape(str(ov_st))}</code> · <code>OrderSend=0</code>",
        f"• Daily Ops: <code>{esc_score}</code> · Node1: <code>{esc_nd}</code>",
        f"• Tin đỏ 48h: <code>{rn_cnt}</code> sự kiện",
        f"• 4 Tầng Wave 4: <code>{esc_w4}</code>",
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


def _render_wave4_sections_md(payload: dict[str, Any]) -> list[str]:
    """Render unified Wave 4 Sections (4 Inside-Out Tiers: A Prop Fleet, B Own-Book Shadow, C AI Radar/Supervisor)."""
    pf = payload.get("prop_fleet") if isinstance(payload.get("prop_fleet"), dict) else {"present": False}
    ob = payload.get("ownbook_shadow") if isinstance(payload.get("ownbook_shadow"), dict) else {"present": False}
    ai = (
        payload.get("ai_radar_supervisor")
        if isinstance(payload.get("ai_radar_supervisor"), dict)
        else {"present": False}
    )
    tiers = payload.get("wave4_inside_out_tiers") if isinstance(payload.get("wave4_inside_out_tiers"), dict) else {}

    out: list[str] = [
        "",
        "## 5. Tổng Quan 4 Tầng Inside-Out (Unified Wave 4 Feeds)",
        "",
        "| Tầng | Phạm vi | Trạng thái | Ghi chú chính |",
        "| --- | --- | :---: | --- |",
    ]

    t1_st = str((tiers.get("tier_1_cfd_prop_fleet") or {}).get("status") or pf.get("status") or "NOT_INITIALIZED")
    t2_st = str((tiers.get("tier_2_futures_prop_research") or {}).get("status") or "RESEARCH_OFFLINE_ONLY")
    t3_st = str(
        (tiers.get("tier_3_ownbook_shadow") or {}).get("traffic_light")
        or ob.get("traffic_light")
        or "NOT_INITIALIZED"
    )
    t4_st = str(
        (tiers.get("tier_4_ai_radar_and_live_ops") or {}).get("status")
        or ai.get("status")
        or "NOT_INITIALIZED"
    )

    if pf.get("present") and pf.get("status") not in ("INVALID_JSON", "SAFETY_TAMPER_BLOCKED"):
        ftmo_comm = float(pf.get("ftmo_committed_funded_usd", 0.0) or 0.0)
        ftmo_cap = float(pf.get("ftmo_funded_cap_usd", FTMO_FUNDED_CAP_USD) or FTMO_FUNDED_CAP_USD)
        t1_note = (
            f"Challenge=`{pf.get('active_challenges_count', 0)}` · Funded=`{pf.get('active_funded_count', 0)}` · "
            f"FTMO Cap `{ftmo_comm:,.0f}/{ftmo_cap:,.0f} USD` "
            f"(`{pf.get('ftmo_cap_utilization_pct', 0.0):.2f}%`)"
        )
    else:
        t1_note = f"Nguồn `{pf.get('source_mode', 'NOT_INITIALIZED')}` (chưa khởi tạo sổ đội Prop)"

    if ob.get("present") and ob.get("status") != "INVALID_JSON":
        cex_s = f"{ob['cex_exposure_pct']:.2f}%" if ob.get("cex_exposure_pct") is not None else "N/A"
        fnd_raw = ob.get("annualized_funding_rate_pct")
        fnd_s = f"{fnd_raw:.2f}%" if fnd_raw is not None else "N/A"
        t3_note = f"CEX `{cex_s} <= {ob.get('cex_cap_pct', 25.0):.0f}%` · Funding `{fnd_s}/năm`"
    else:
        t3_note = "Chưa có `ownbook_shadow_ops_summary.json`"

    if ai.get("present"):
        top_sup = (ai.get("radar") or {}).get("top_budget_supervisor")
        sup_lbl = (
            f"`{top_sup['id']}` ({top_sup['monthly_usd']:.4f} USD/tháng)"
            if isinstance(top_sup, dict) and top_sup.get("monthly_usd") is not None
            else "chưa có radar"
        )
        sh = ai.get("prospective_shadow") or {}
        t4_note = (
            f"Top API: {sup_lbl} <= `{ai.get('monthly_api_budget_cap_usd', 5.0):.2f} USD/tháng` · "
            f"Shadow `{sh.get('commitments_count', 0)}` phiên từ `{sh.get('first_live_session_date', '2026-11-30')}`"
        )
    else:
        t4_note = "Chưa có dữ liệu AI Radar / Prospective Shadow"

    out.extend(
        [
            f"| **Tầng 1** | CFD Prop Fleet (`S0..S7` + `E1..E6`) | `{t1_st}` | {t1_note} |",
            f"| **Tầng 2** | Futures Prop (Nghiên cứu offline) | `{t2_st}` | `OrderSend = 0` · chỉ đánh giá offline |",
            f"| **Tầng 3** | Own-Book Shadow (`OPS-4`) | `{t3_st}` | {t3_note} |",
            f"| **Tầng 4** | AI Radar & Macro Supervisor | `{t4_st}` | {t4_note} |",
        ]
    )

    # --- Section 5A: Tier 1/4 Prop Fleet (S0..S7 + E1..E6) ---
    out.extend(["", "### 5A. Tầng 1/4 — Đội Tài Khoản Prop (`S0..S7` & Chốt Chặn `E1..E6`)", ""])
    if not pf.get("present"):
        out.append(
            "- **Trạng thái:** `NOT_INITIALIZED` — chưa có `fleet_ledger.json` hoặc `sample_fleet_ledger.json` "
            "(an toàn khi chạy CI sạch; trần FTMO mặc định `400,000 USD`)."
        )
    elif pf.get("status") in ("INVALID_JSON", "SAFETY_TAMPER_BLOCKED"):
        out.append(f"- **Trạng thái:** `{pf.get('status')}` — {pf.get('detail', 'Sổ đội Prop không hợp lệ.')}")
    else:
        cbs = pf.get("counts_by_state") or {}
        s0_7_parts = [f"{st.split('_')[0]}={cbs.get(st, 0)}" for st in _FLEET_CANONICAL_STATES]
        e_parts = [f"{st.split('_')[0]}={cbs.get(st, 0)}" for st in _FLEET_INCIDENT_STATES[:3]]
        alerts_pf = pf.get("active_e1_to_e6_alerts") or []
        alerts_pf_str = ", ".join(f"`{a}`" for a in alerts_pf) if alerts_pf else "`0` cảnh báo (E1..E6 xanh)"
        ch_cnt = pf.get("active_challenges_count", 0)
        eval_usd = float(pf.get("total_eval_nominal_usd", 0.0) or 0.0)
        fd_cnt = pf.get("active_funded_count", 0)
        fd_usd = float(pf.get("total_funded_nominal_usd", 0.0) or 0.0)
        fd_vnd = float(pf.get("total_funded_nominal_vnd", 0) or 0)
        ftmo_comm_a = float(pf.get("ftmo_committed_funded_usd", 0.0) or 0.0)
        ftmo_cap_a = float(pf.get("ftmo_funded_cap_usd", FTMO_FUNDED_CAP_USD) or FTMO_FUNDED_CAP_USD)
        ftmo_util = float(pf.get("ftmo_cap_utilization_pct", 0.0) or 0.0)
        ftmo_head = float(pf.get("ftmo_cap_headroom_usd", 0.0) or 0.0)
        vps_mode = pf.get("vps_telemetry_mode", "OFFLINE_ACCOUNT_ONLY")
        scale_cnt = pf.get("scaling_eligible_count", 0)
        scale_ids = pf.get("scaling_eligible_account_ids") or []
        scale_suffix = f" ({', '.join(scale_ids)})." if scale_ids else "."
        out.extend(
            [
                (
                    f"- **Nguồn sổ cái:** `{pf.get('source_mode')}` (`{pf.get('path')}`) · "
                    f"Trạng thái: `{pf.get('status')}` · Hệ số rủi ro đội: `{pf.get('fleet_scale_factor', 1.0):.2f}x`."
                ),
                (
                    f"- **Quy mô đang chạy & Trần `400,000 USD`:** Challenge=`{ch_cnt}` (`{eval_usd:,.0f} USD`) · "
                    f"Funded=`{fd_cnt}` (`{fd_usd:,.0f} USD` ~ `{fd_vnd:,.0f} VND`) · "
                    f"FTMO cam kết `{ftmo_comm_a:,.0f}/{ftmo_cap_a:,.0f} USD` "
                    f"(`{ftmo_util:.2f}%`, còn dư `{ftmo_head:,.0f} USD`)."
                ),
                f"- **Phân bổ `S0..S7` / sự cố:** `{' | '.join(s0_7_parts)}` · Sự cố: `{' | '.join(e_parts)}`.",
                f"- **Cảnh báo `E1..E6` đang bật:** {alerts_pf_str} (VPS telemetry: `{vps_mode}`).",
                f"- **FTMO Scaling Plan (`+25% / 4` tháng):** `{scale_cnt}` tài khoản đủ điều kiện{scale_suffix}",
            ]
        )
        inact = pf.get("inactivity_countdown") or []
        if inact:
            out.extend(
                [
                    "",
                    "**Đếm ngược ngừng giao dịch (`21/27/30` ngày):**",
                    "",
                    (
                        "| Tài khoản | Pha | Nghỉ (ngày) | Còn tới 21d (Vàng) "
                        "| Còn tới 27d (Khẩn) | Còn tới 30d (Khóa) | Mức |"
                    ),
                    "| --- | --- | ---: | ---: | ---: | ---: | :---: |",
                ]
            )
            for row in inact:
                idle_v = row.get("days_since_last_trade")
                d_idle = f"{idle_v:.1f}" if idle_v is not None else "N/A"
                d21 = f"{row['days_to_warn_21d']:.1f}" if row.get("days_to_warn_21d") is not None else "N/A"
                d27 = f"{row['days_to_urgent_27d']:.1f}" if row.get("days_to_urgent_27d") is not None else "N/A"
                d30 = f"{row['days_to_lock_30d']:.1f}" if row.get("days_to_lock_30d") is not None else "N/A"
                out.append(
                    f"| `{row['account_id']}` | `{row['state']}` | `{d_idle}` "
                    f"| `{d21}` | `{d27}` | `{d30}` | `{row['level']}` |"
                )
        else:
            out.append("- **Đếm ngược ngừng giao dịch (`21/27/30` ngày):** Không có tài khoản live đang chạy.")

    # --- Section 5B: Tier 3 Own-Book Shadow (OPS-4) ---
    out.extend(["", "### 5B. Tầng 3 — Own-Book Shadow (`OPS-4`)", ""])
    if not ob.get("present"):
        out.append(
            "- **Trạng thái:** `NOT_INITIALIZED` — chưa có `ownbook_shadow_ops_summary.json` "
            "(giữ cứng trần `CEX <= 25%` & cảnh báo nén funding `< 3%`)."
        )
    elif ob.get("status") == "INVALID_JSON":
        out.append("- **Trạng thái:** `INVALID_JSON` — file `ownbook_shadow_ops_summary.json` không đọc được.")
    else:
        cex_val = f"{ob['cex_exposure_pct']:.2f}%" if ob.get("cex_exposure_pct") is not None else "N/A"
        cex_flag = "ĐẠT" if ob.get("cex_cap_compliant") else "VI PHẠM"
        fund_val = (
            f"{ob['annualized_funding_rate_pct']:.2f}%/năm"
            if ob.get("annualized_funding_rate_pct") is not None
            else "N/A"
        )
        rot_pct = float(ob.get("rotated_carry_to_tbill_pct", 0.0) or 0.0)
        tbill_veh = ob.get("tbill_buffer_vehicle", "SGOV/BIL")
        comp_flag = (
            f"KÍCH HOẠT (`FUNDING_COMPRESSION_ALERT`, xoay `{rot_pct:.1f}%` sang `{tbill_veh}`)"
            if ob.get("funding_compression_active")
            else "KHÔNG KÍCH HOẠT (trên ngưỡng 3.00%)"
        )
        ob_alerts = ob.get("active_alerts") or []
        ob_alerts_str = ", ".join(f"`{a}`" for a in ob_alerts) if ob_alerts else "`0` cảnh báo"
        rm_str = f"{ob['risk_multiplier']:.2f}x" if ob.get("risk_multiplier") is not None else "N/A"
        as_of = ob.get("as_of_date", "2024-12-31")
        ho_rows = ob.get("holdout_rows_analysed", 0)
        f_thr = float(ob.get("funding_compression_threshold_pct", 3.0) or 3.0)
        st_pass = ob.get("stress_passed", 0)
        st_tot = ob.get("stress_total", 0)
        out.extend(
            [
                (
                    f"- **Đèn rủi ro `OPS-4`:** `{ob.get('traffic_light')}` · Hành động: `{ob.get('action')}` "
                    f"(hệ số `{rm_str}`, mốc Dev `{as_of}`, `Holdout = {ho_rows}`)."
                ),
                (
                    f"- **Tỷ trọng sàn CEX:** `{cex_val}` so với trần cứng `<= {ob.get('cex_cap_pct', 25.0):.2f}%` "
                    f"(`{cex_flag}`)."
                ),
                (
                    f"- **Lãi suất Funding quy năm:** `{fund_val}` (ngưỡng `< {f_thr:.2f}%`) · "
                    f"`FUNDING_COMPRESSION_ALERT`: {comp_flag}."
                ),
                (
                    f"- **Stress cực đoan & cảnh báo:** `{st_pass}/{st_tot}` bài kiểm tra đạt · "
                    f"Cảnh báo đang bật: {ob_alerts_str}."
                ),
            ]
        )

    # --- Section 5C: Tier 4 AI Radar & Macro Supervisor ---
    out.extend(["", "### 5C. Tầng 4 — AI Model Radar & Macro Supervisor (Chỉ Tư Vấn, `OrderSend = 0`)", ""])
    if not ai.get("present"):
        out.append(
            "- **Trạng thái:** `NOT_INITIALIZED` — chưa có dữ liệu `.runtime/offensive4/ai/` "
            "(trần ngân sách API chính thức giữ cứng `<= 5.00 USD/tháng`, Prospective Shadow bắt đầu từ `2026-11-30`)."
        )
    else:
        rad = ai.get("radar") or {}
        sh = ai.get("prospective_shadow") or {}
        pit = ai.get("pit24_and_rubric") or {}
        top_sup = rad.get("top_budget_supervisor")
        cap_usd = float(ai.get("monthly_api_budget_cap_usd", AI_MAX_MONTHLY_API_USD))
        cap_vnd = int(ai.get("monthly_api_budget_cap_vnd", round(cap_usd * DEFAULT_USD_VND_RATE)))
        bud_flag = "ĐẠT" if ai.get("budget_compliant", True) else "VƯỢT TRẦN"

        if rad.get("present") and isinstance(top_sup, dict):
            m_usd = top_sup.get("monthly_usd")
            m_vnd = top_sup.get("monthly_vnd")
            util_s = (
                f"{top_sup['budget_utilization_pct']:.2f}%"
                if top_sup.get("budget_utilization_pct") is not None
                else "N/A"
            )
            out.append(
                f"- **Top Budget Supervisor (AI Radar):** `{top_sup['id']}` — ước tính `{m_usd:.4f} USD/tháng` "
                f"(`{m_vnd:,} VND/tháng`, chiếm `{util_s}` trần `{cap_usd:.2f} USD/tháng` ~ `{cap_vnd:,} VND/tháng` "
                f"· `{bud_flag}`; `{rad.get('budget_eligible_count', 0)}` model đạt trần)."
            )
        else:
            out.append(
                f"- **AI Model Radar:** `{rad.get('status', 'NOT_INITIALIZED')}` · "
                f"Trần ngân sách API tháng: `<= {cap_usd:.2f} USD/tháng` (`{cap_vnd:,} VND/tháng`, `{bud_flag}`)."
            )

        pd_info = rad.get("price_delta") if isinstance(rad.get("price_delta"), dict) else {}
        pd_cnt = pd_info.get("counts") if isinstance(pd_info.get("counts"), dict) else {}
        if pd_info.get("has_alert"):
            top_ch = pd_info.get("top_changes") or []
            movers = ", ".join(
                f"`{c['id']}` ({c['direction']} {c['monthly_delta_pct']:+.1f}%)"
                if c.get("monthly_delta_pct") is not None
                else f"`{c['id']}` ({c['direction']})"
                for c in top_ch[:3]
            )
            out.append(
                f"- **Cảnh báo biến động giá API (`price_delta`):** Có biến động — "
                f"đổi giá=`{pd_cnt.get('price_changes', 0)}` (giảm=`{pd_cnt.get('price_drops', 0)}`, "
                f"tăng=`{pd_cnt.get('price_increases', 0)}`), mới=`{pd_cnt.get('new_models', 0)}`, "
                f"gỡ=`{pd_cnt.get('removed_models', 0)}`"
                + (f" · Nổi bật: {movers}." if movers else ".")
            )
        else:
            out.append(
                f"- **Cảnh báo biến động giá API (`price_delta`):** `0` biến động giá đáng chú ý "
                f"(mới=`{pd_cnt.get('new_models', 0)}`, gỡ=`{pd_cnt.get('removed_models', 0)}`)."
            )

        sh_start = sh.get("first_live_session_date", "2026-11-30")
        sh_comm = sh.get("commitments_count", 0)
        sh_sess = sh.get("distinct_session_dates", 0)
        sh_span = sh.get("calendar_span_days", 0)
        sh_min = sh.get("min_audit_calendar_days", 30)
        out.append(
            f"- **Prospective Shadow Ledger (từ `{sh_start}`):** "
            f"`{sh_comm}` cam kết SHA-256 · `{sh_sess}` phiên giao dịch / `{sh_span}` ngày dương lịch "
            f"(yêu cầu tối thiểu `{sh_min}` ngày trước audit OOS · trạng thái `{sh.get('status', 'NOT_INITIALIZED')}`)."
        )

        if pit.get("present") and pit.get("status") not in ("NOT_INITIALIZED", "INVALID_JSON"):
            s_ok = pit.get("scenarios_ok", 0)
            s_tot = pit.get("scenarios_total", 24)
            sch_pct = float(pit.get("json_schema_valid_pct", 0.0) or 0.0)
            reg_pct = float(pit.get("regime_agreement_pct", 0.0) or 0.0)
            p50_ms = float(pit.get("latency_p50_ms", 0.0) or 0.0)
            out.append(
                f"- **PIT-24 Benchmark & Rubric 6 tiêu chí:** `{pit.get('status')}` trên `{pit.get('selected_model')}` "
                f"(`{s_ok}/{s_tot}` kịch bản ẩn danh · schema `{sch_pct:.1f}%` · "
                f"đồng thuận regime `{reg_pct:.1f}%` · độ trễ p50 `{p50_ms:.0f} ms`)."
            )

    return out


def render_morning_briefing_md(payload: dict[str, Any], *, root: Path = ROOT) -> str:
    """Render plain-Vietnamese Chief-of-Staff Morning Briefing Markdown (strictly 0 bare `$`, 0 G12, 0 OPSEC leaks)."""
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
        "wave4_tiers_wired: 4",
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

    lines.extend(_render_wave4_sections_md(payload))

    notif = payload.get("notification", {})
    notif_line = (
        f"- **Thông báo tự động (`--notify`):** `attempted={notif.get('attempted')}` · "
        f"`configured={notif.get('configured')}` · `sent={len(notif.get('sent') or [])}`."
    )
    lines.extend(
        [
            "",
            "## 6. Bước Kế Tiếp (< 2 phút)",
            "",
            notif_line,
            f"- **Hành động ưu tiên ngay:** {next_active['action_vi']}",
            "",
        ]
    )

    md_raw = "\n".join(lines)
    md_clean = scrub_opsec_text(md_raw, root=root, strip_dollar=True)
    # Fail-closed guards (work identically under `python -O`, zero bare `assert`!)
    if "$" in md_clean:
        raise ValueError("Formatting guard failed: bare dollar character detected in morning briefing Markdown")
    for pat in _G12_SUPPORT_NUDGE_PATTERNS:
        if pat.search(md_clean) is not None:
            raise ValueError(f"G12 guard failed: prohibited prop-firm support nudge matched {pat.pattern!r}")
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
    prop_fleet = collect_prop_fleet_summary(root=root, now_utc=now, node_digest=node_digest)
    ownbook_shadow = collect_ownbook_shadow_summary(root=root)
    ai_radar_supervisor = collect_ai_radar_and_supervisor_summary(root=root)
    wave4_tiers = build_wave4_inside_out_tiers(
        prop_fleet=prop_fleet,
        ownbook_shadow=ownbook_shadow,
        ai_radar_supervisor=ai_radar_supervisor,
        daily_ops=daily_ops,
        node_digest=node_digest,
    )

    # Determine honest overall status
    ops_grade = str(daily_ops.get("status") or "")
    node_st = str(node_digest.get("overall_status") or "")
    has_fail_fleet = any(str(v.get("status")) == "FAIL" for v in automation_summaries.values() if v.get("present"))
    has_wave4_critical = (
        prop_fleet.get("status") in ("BLOCK_ATTENTION", "SAFETY_TAMPER_BLOCKED")
        or ownbook_shadow.get("status") == "RED_HALT"
        or ai_radar_supervisor.get("status") == "BLOCK_ATTENTION"
    )
    has_wave4_amber = (
        prop_fleet.get("status") == "AMBER_WATCH"
        or ownbook_shadow.get("status") == "AMBER_WATCH"
        or ai_radar_supervisor.get("status") == "AMBER_WATCH"
    )

    if ops_grade == "CRITICAL_FAIL_CLOSED" or has_fail_fleet or has_wave4_critical:
        overall_status = "CRITICAL_ATTENTION"
    elif dry_run:
        overall_status = "DRY_RUN_READY"
    elif red_news_48h["has_48h_tier1_us_alert"] or node_st in ("DEGRADED", "OFFLINE") or has_wave4_amber:
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
        "prop_fleet": prop_fleet,
        "ownbook_shadow": ownbook_shadow,
        "ai_radar_supervisor": ai_radar_supervisor,
        "wave4_inside_out_tiers": wave4_tiers,
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
    ap.add_argument(
        "--offline-dry-run",
        action="store_true",
        help="Combined shorthand for --offline --dry-run (zero SSH, zero network, zero popup)",
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
    eff_offline = bool(args.offline or args.offline_dry_run)
    eff_dry_run = bool(args.dry_run or args.offline_dry_run)

    payload = build_morning_briefing(
        root=args.root,
        contract_path=args.contract,
        out_json=out_json,
        out_md=out_md,
        node_fixture=args.node_fixture,
        notify=args.notify,
        offline=eff_offline,
        dry_run=eff_dry_run,
        now_utc=now_dt,
    )
    if sys.stdout is not None:
        if args.as_json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            rn = payload["red_news_48h"]
            nd = payload["node_digest"]
            pf = payload.get("prop_fleet", {})
            ob = payload.get("ownbook_shadow", {})
            ai = payload.get("ai_radar_supervisor", {})
            next_ms = next((m for m in payload["milestones_6"] if m["delta_sec"] >= 0), payload["milestones_6"][-1])
            print(
                f"[morning_briefing] status={payload['overall_status']} node1={nd.get('overall_status')} "
                f"(rc={nd.get('returncode')}) red_news_48h={rn['upcoming_48h_count']} "
                f"fleet={pf.get('status')} ownbook={ob.get('traffic_light')} ai={ai.get('status')} "
                f"next_milestone={next_ms['id']}({next_ms['countdown_vi']}) OrderSend={ORDER_SEND_COUNT}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
