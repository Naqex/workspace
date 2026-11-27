"""One-way read-only bridge from the air-gapped strategy-intel cleanroom into TradingWorkspace.

Hard invariants:
  - 100% READ-ONLY toward `D:/ANNAM/strategy-intel/` (`writes_back_to_cleanroom = 0`).
  - Imports and calls `inbox_intake_scanner.scan_inbox()` purely in-memory (NEVER invokes its CLI).
  - Fail-closed Holdout 2025+ enforcement via `quant_core.holdout_guard` (ZERO `assert` statements;
    remains active under `python -O`).
  - Tags every record with `untrusted_external_data = True` and `order_send_count = 0`.
  - Filters out `TOP1-SOLO-QUANT-MASTER-PLAN.md §3.4` Forbidden List + Grid/Martingale/No-SL leads.
  - CI-safe under `--offline` even when the cleanroom directory does not exist on the runner.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

import inbox_intake_scanner  # noqa: E402
from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
)

DEFAULT_INTEL_DIR = Path(os.environ.get("NAQEX_STRATEGY_INTEL_DIR", "D:/ANNAM/strategy-intel"))
DEFAULT_OUT_PATH = REPO_ROOT / ".runtime" / "automation" / "strategy_intel_handoff_latest.json"

ORDER_SEND_COUNT = 0
SPEND_VND = 0
HOLDOUT_ROWS_ANALYSED = 0
WRITES_BACK_TO_CLEANROOM = 0

_HOLDOUT_TOKEN_RE = re.compile(r"(?:oos2|(?<!\d)202[5-9](?!\d))", re.IGNORECASE)
_ISO_DATE_FIND_RE = re.compile(r"(?<!\d)(\d{4}[-.]\d{2}[-.]\d{2})(?!\d)")

_MARTINGALE_NEGATION_PHRASES: tuple[str, ...] = (
    "no martingale",
    "non-martingale",
    "zero martingale",
    "without martingale",
    "avoids martingale",
    "avoiding martingale",
    "rejects martingale",
    "does not use martingale",
    "never uses martingale",
    "no lot multiplier",
    "no leverage multiplier",
)

_GRID_NEGATION_PHRASES: tuple[str, ...] = (
    "no grid",
    "non-grid",
    "zero grid",
    "without grid",
    "avoids grid",
    "avoiding grid",
    "rejects grid",
    "does not use grid",
    "never uses grid",
    "never averages down",
    "no averaging down",
    "without averaging",
    "no cost averaging",
)

_CLAUSE_SPLIT_RE = re.compile(r"(?:\.(?=\s|$)|[?!\n;])+")

_TOXIC_MARTINGALE_RE = re.compile(
    r"\b(martingale|lot\s*multiplier|recovery\s*lot|double\s*lot|doubles?\s+(?:the\s+)?lot|"
    r"geometric\s+lot\s+sizing)\b",
    re.IGNORECASE,
)

_TOXIC_GRID_RE = re.compile(
    r"\b(grid\s*trading|grid\s*strategy|grid\s*system|grid\s*step|hedging\s*grid|"
    r"averaging\s*down|cost[- ]averaging|adds?\s+losing\s+layers?)\b",
    re.IGNORECASE,
)

_TOXIC_NO_SL_RE = re.compile(
    r"\b(no\s+stop[- ]?loss|without\s+(?:a\s+)?stop[- ]?loss|no\s+hard\s+sl|"
    r"without\s+sl|sl\s*=\s*0(?:\.0+)?(?![\d.])|zero\s+stop[- ]?loss|mental\s+stop\s+only|"
    r"never\s+uses?\s+(?:a\s+)?stop[- ]?loss)\b",
    re.IGNORECASE,
)

_CRYPTO_SYMBOL_RE = re.compile(
    r"(?:^|[^A-Z0-9])"
    r"(?:BTC|ETH|SOL|XRP|BNB|DOGE|ADA|AVAX|LTC|DOT|LINK|MATIC|CRYPTO|USDT|USDC)"
    r"(?:USD|USDT|USDC|EUR|BTC|ETH|PERP)?(?=$|[^A-Z0-9])",
    re.IGNORECASE,
)
_SUB_4H_TF_TOKENS: frozenset[str] = frozenset(
    {"M1", "M2", "M3", "M5", "M10", "M15", "M30", "H1", "H2", "H3", "1M", "5M", "15M", "30M", "1H", "2H", "3H"}
)
_OVERNIGHT_TF_TOKENS: frozenset[str] = frozenset(
    {"H4", "H6", "H8", "H12", "D1", "W1", "MN", "MN1", "DAILY", "WEEKLY", "SWING"}
)
_INTRADAY_CFD_TF_TOKENS: frozenset[str] = frozenset({"M1", "M5", "M15", "M30", "H1", "1M", "5M", "15M", "30M", "1H"})

_CFD_OVERNIGHT_SWAP_SYMBOLS: frozenset[str] = frozenset(
    {
        "XAU",
        "XAG",
        "XAUUSD",
        "XAGUSD",
        "USOIL",
        "UKOIL",
        "WTI",
        "BRENT",
        "US100",
        "US500",
        "US30",
        "NAS100",
        "SPX500",
        "GER40",
    }
)
_CFD_FX_INDEX_SYMBOLS: frozenset[str] = _CFD_OVERNIGHT_SWAP_SYMBOLS | frozenset(
    {"EURUSD", "GBPUSD", "USDJPY", "EURJPY", "GBPJPY", "AUDUSD", "USDCAD", "USDCHF", "NZDUSD", "EURGBP"}
)
_ETF_SPOT_MARKERS_RE = re.compile(
    r"\b(ETF|SPY|TLT|GLD|IAU|EFA|AGG|SHY|QQQ|VTI|T-BILL|ZERO\s+OVERNIGHT\s+CFD\s+SWAP)\b",
    re.IGNORECASE,
)

_ML_FILTER_RE = re.compile(
    r"\b(machine\s+learning|ml\s+filter|xgboost|lightgbm|random\s+forest|neural\s+net|meta[- ]?label|llm\s+filter)\b",
    re.IGNORECASE,
)
_BRIER_PROVEN_RE = re.compile(r"brier\s+skill\s*(?:>|>=)\s*0\.[0-9]*[1-9]", re.IGNORECASE)

VALID_PROFILES: frozenset[str] = frozenset({"default", "offensive3"})
_NON_BREAKOUT_MARKER_RE = re.compile(
    r"\b(non[- ]?breakout|false[- ]?break(?:out)?|liquidity[- ]?sweep|sweep[- ]?reclaim|"
    r"mean[- ]?reversion|pullback|fixing|overnight[- ]?drift|reversal|stat[- ]?arb|pairs|cointegration|"
    r"carry|seasonality|cross[- ]?sectional|tsmom|xsmom|vol[- ]?regime)\b",
    re.IGNORECASE,
)
_PURE_BREAKOUT_RE = re.compile(
    r"\b(breakout|opening\s+range\s+break|orb\b|donchian\s+breakout|london\s+box\s+breakout|"
    r"tokyo\s+box\s+breakout|range\s+breakout|channel\s+breakout)\b",
    re.IGNORECASE,
)
_OFFENSIVE3_CFD_SYMBOLS: frozenset[str] = _CFD_FX_INDEX_SYMBOLS | frozenset(
    {
        "JP225",
        "UK100",
        "AUDJPY",
        "CADJPY",
        "CHFJPY",
        "NZDJPY",
        "EURAUD",
        "GBPAUD",
        "EURCAD",
        "BTCUSD",
    }
)


def validate_no_holdout_leakage(obj: Any, *, context: str = "strategy_intel_bridge", path: str = "root") -> None:
    """Fail-closed recursive scanner rejecting any 2025+ / OOS2 leakage (ZERO `assert`, `-O` safe)."""
    enforce_holdout_zero_rows(HOLDOUT_ROWS_ANALYSED, context=context)

    if isinstance(obj, dict):
        for k, v in obj.items():
            k_str = str(k)
            if _HOLDOUT_TOKEN_RE.search(k_str):
                raise HoldoutLockError(
                    f"HOLDOUT_CONTAMINATION [{context}]: forbidden 2025+/OOS2 key {k_str!r} at {path}"
                )
            for dt_match in _ISO_DATE_FIND_RE.findall(k_str):
                enforce_pre_holdout_dates(
                    dt_match,
                    context=f"{context}:{path}.key({k_str})",
                    cutoff_day=HOLDOUT_CUTOFF_DAY,
                )
            validate_no_holdout_leakage(v, context=context, path=f"{path}.{k_str}")
        return

    if isinstance(obj, list):
        for idx, item in enumerate(obj):
            validate_no_holdout_leakage(item, context=context, path=f"{path}[{idx}]")
        return

    if isinstance(obj, str):
        if _HOLDOUT_TOKEN_RE.search(obj):
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION [{context}]: forbidden 2025+/OOS2 token in string at {path}: {obj[:120]!r}"
            )
        for dt_match in _ISO_DATE_FIND_RE.findall(obj):
            enforce_pre_holdout_dates(dt_match, context=f"{context}:{path}", cutoff_day=HOLDOUT_CUTOFF_DAY)
        return

    if isinstance(obj, (int, float)) and not isinstance(obj, bool):
        if 2025 <= obj <= 2099:
            raise HoldoutLockError(f"HOLDOUT_CONTAMINATION [{context}]: forbidden numeric holdout year {obj} at {path}")


def _split_symbol_tokens(symbol_text: str) -> set[str]:
    tokens: set[str] = set()
    for raw_item in re.split(r"[,;\s|]+", (symbol_text or "").upper()):
        item = raw_item.strip()
        if not item:
            continue
        parts = [p for p in re.split(r"[/\-_]+", item) if p]
        tokens.update(parts)
        # Collapse 2-part slash/dash FX/metal pairs (e.g. XAU/USD -> XAUUSD, EUR-USD -> EURUSD)
        # without collapsing 3+ multi-asset lists (e.g. SPY/TLT/GLD).
        if len(parts) == 2 and all(re.fullmatch(r"[A-Z0-9]{2,6}", p) for p in parts):
            tokens.add(f"{parts[0]}{parts[1]}")
    return tokens


def evaluate_lead_against_s34(lead: dict[str, Any]) -> list[str]:
    """Check a single sanitized lead against TOP1-SOLO-QUANT-MASTER-PLAN §3.4 & Grid/Martingale/No-SL."""
    reasons: list[str] = []

    name = str(lead.get("name", ""))
    family = str(lead.get("family", ""))
    symbol = str(lead.get("symbol", ""))
    timeframe = str(lead.get("timeframe", "")).strip().upper()
    rule_desc = str(lead.get("rule_description", ""))
    stop_rule = str(lead.get("stop_loss_rule", ""))
    flags_text = " ".join(str(x) for x in lead.get("data_quality_flags", []) if x)
    combined = "\n".join(part for part in (name, family, rule_desc, stop_rule, flags_text) if part)

    # 1. Grid / Martingale / No-SL check (per-category negation aware; hard-stop NEVER negates Martingale/Grid)
    has_toxic = False
    for clause in _CLAUSE_SPLIT_RE.split(combined):
        c_low = clause.lower().strip()
        if not c_low:
            continue
        if _TOXIC_NO_SL_RE.search(clause):
            has_toxic = True
            break
        if _TOXIC_MARTINGALE_RE.search(clause) and not any(neg in c_low for neg in _MARTINGALE_NEGATION_PHRASES):
            has_toxic = True
            break
        if _TOXIC_GRID_RE.search(clause) and not any(neg in c_low for neg in _GRID_NEGATION_PHRASES):
            has_toxic = True
            break
    if has_toxic:
        reasons.append("FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL")

    # 2. Crypto Spot < 4H Taker (Lab #1: 0/12)
    is_crypto = bool(_CRYPTO_SYMBOL_RE.search(symbol)) or ("crypto" in family.lower())
    if is_crypto:
        tf_tokens = _split_symbol_tokens(timeframe)
        if tf_tokens & _SUB_4H_TF_TOKENS:
            reasons.append("FORBIDDEN_S34_CRYPTO_SUB_4H_TAKER")
        elif re.search(r"\b(sub[- ]?4h|m1|m5|m15|m30|1h)\b.*taker", combined, re.I) and not re.search(
            r"\b(avoids?|no|without)\s+sub[- ]?4h", combined, re.I
        ):
            reasons.append("FORBIDDEN_S34_CRYPTO_SUB_4H_TAKER")

    # 3. CFD Gold/Oil/Indices overnight negative swap (Labs #3A/#3B: 0/21)
    # 4. Saturated CFD intraday swap=0 space (Labs #11-#12: 0/36, Pass 29-31: 0/66)
    sym_tokens = _split_symbol_tokens(symbol)
    is_etf_spot = bool(_ETF_SPOT_MARKERS_RE.search(f"{family} {symbol} {rule_desc}")) and not bool(
        sym_tokens & _CFD_FX_INDEX_SYMBOLS
    )
    if not is_etf_spot and not is_crypto:
        tf_tokens = _split_symbol_tokens(timeframe)
        if (sym_tokens & _CFD_OVERNIGHT_SWAP_SYMBOLS) and (
            (tf_tokens & _OVERNIGHT_TF_TOKENS)
            or bool(re.search(r"\b(overnight|multi[- ]?day|turn[- ]of[- ]month|swing)\b", combined, re.I))
        ):
            reasons.append("FORBIDDEN_S34_CFD_OVERNIGHT_NEG_SWAP")
        elif (sym_tokens & _CFD_FX_INDEX_SYMBOLS) and (tf_tokens & _INTRADAY_CFD_TF_TOKENS):
            reasons.append("FORBIDDEN_S34_CFD_INTRADAY_SATURATED")

    # 5. ML filter without proven Brier Skill > 0 (Lab #6)
    if _ML_FILTER_RE.search(combined) and not _BRIER_PROVEN_RE.search(combined):
        reasons.append("FORBIDDEN_S34_ML_FILTER_NO_BRIER_SKILL")

    return reasons


def _normalize_offensive3_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """Normalize Total Offensive #3 lead fields cleanly into canonical bridge schema without mutating input."""
    out = dict(lead)
    if not out.get("name") and out.get("title"):
        out["name"] = out["title"]
    if not out.get("family") and out.get("family_tag"):
        out["family"] = out["family_tag"]
    if not out.get("symbol"):
        au = out.get("asset_universe")
        if isinstance(au, list):
            out["symbol"] = "/".join(str(x) for x in au if x)
        elif au:
            out["symbol"] = str(au)
    if not out.get("stop_loss_rule") and out.get("sl_rule"):
        out["stop_loss_rule"] = out["sl_rule"]
    if not out.get("rule_description"):
        parts = [
            str(out.get(k) or "").strip()
            for k in ("economic_rationale", "entry_rule", "exit_rule", "sl_rule")
            if out.get(k)
        ]
        out["rule_description"] = " | ".join(parts)
    if not out.get("timeframe"):
        track = str(out.get("prop_track") or "").upper()
        if "SWING" in track:
            out["timeframe"] = "D1"
        elif "INTRADAY" in track:
            out["timeframe"] = "M15"
    return out


def evaluate_lead_for_offensive3(lead: dict[str, Any]) -> tuple[list[str], str | None]:
    """Evaluate a sanitized lead under opt-in `--profile offensive3` with explicit §3.4 exemption logging.

    Still strictly blocks Grid/Martingale/No-SL, Crypto <4H taker, unproven ML filters, and pure
    breakout leads; admits non-breakout Prop intraday + FTMO Swing white-box leads with an explicit
    audit `section_3_4_exemption_reason`.
    """
    norm = _normalize_offensive3_lead(lead)
    base_reasons = evaluate_lead_against_s34(norm)

    hard_blocks: list[str] = [
        r
        for r in base_reasons
        if r
        in (
            "FORBIDDEN_S34_GRID_MARTINGALE_OR_NO_SL",
            "FORBIDDEN_S34_CRYPTO_SUB_4H_TAKER",
            "FORBIDDEN_S34_ML_FILTER_NO_BRIER_SKILL",
        )
    ]

    name = str(norm.get("name", ""))
    family = str(norm.get("family", ""))
    rule_desc = str(norm.get("rule_description", ""))
    prop_track = str(norm.get("prop_track", "")).strip().upper()
    combined = f"{name}\n{family}\n{rule_desc}"

    # Pure breakout strategies remain excluded under Offensive #3 non-breakout mandate
    is_pure_breakout = (
        ("breakout" in family.lower() and "non-breakout" not in family.lower() and "non_breakout" not in family.lower())
        or (bool(_PURE_BREAKOUT_RE.search(combined)) and not bool(_NON_BREAKOUT_MARKER_RE.search(combined)))
    )
    if is_pure_breakout:
        hard_blocks.append("FORBIDDEN_OFFENSIVE3_PURE_BREAKOUT")

    if hard_blocks:
        return hard_blocks, None

    exemption_parts: list[str] = []
    if "FORBIDDEN_S34_CFD_INTRADAY_SATURATED" in base_reasons:
        exemption_parts.append(
            "OFFENSIVE3_NON_BREAKOUT_PROP_INTRADAY_EXEMPTION: non-breakout white-box intraday mechanism "
            "admitted for 28-symbol M1 Dev screening under pre-registered m200/m1200 BH-FDR + DSR + PBO + 2x cost gates"
        )
    if "FORBIDDEN_S34_CFD_OVERNIGHT_NEG_SWAP" in base_reasons:
        exemption_parts.append(
            "OFFENSIVE3_FTMO_SWING_REAL_SWAP_EXEMPTION: non-breakout FTMO Swing white-box mechanism admitted "
            "subject to ftmo_specs_28.json real swap + Anti-Fake-Swap Guard (-5%/yr cap, zero positive swap stress)"
        )

    sym_tokens = _split_symbol_tokens(str(norm.get("symbol", "")))
    if not exemption_parts and (sym_tokens & _OFFENSIVE3_CFD_SYMBOLS):
        if "SWING" in prop_track:
            exemption_parts.append(
                "OFFENSIVE3_FTMO_SWING_REAL_SWAP_EXEMPTION: non-breakout FTMO Swing white-box mechanism admitted "
                "subject to ftmo_specs_28.json real swap + Anti-Fake-Swap Guard"
            )
        else:
            exemption_parts.append(
                "OFFENSIVE3_NON_BREAKOUT_PROP_INTRADAY_EXEMPTION: non-breakout white-box mechanism admitted "
                "under pre-registered Offensive #3 28-symbol Dev gates"
            )

    reason_str = (
        " ; ".join(exemption_parts) if exemption_parts else "OFFENSIVE3_NO_S34_EXEMPTION_NEEDED"
    )
    return [], reason_str


def _load_handoff_json_readonly(path: Path, *, label: str) -> tuple[bool, list[dict[str, Any]]]:
    if not path.is_file():
        return False, []
    raw_text = path.read_text(encoding="utf-8")
    payload = json.loads(raw_text)
    validate_no_holdout_leakage(payload, context=f"strategy_intel_bridge:{label}")
    leads = payload.get("leads", [])
    if not isinstance(leads, list):
        raise ValueError(f"Expected 'leads' list in {path}")
    return True, [item for item in leads if isinstance(item, dict)]


def _sanitize_inbox_summary(inbox_report: dict[str, Any]) -> dict[str, Any]:
    """Strip host-absolute paths and tag inbox triage output as untrusted read-only metadata."""
    return {
        "untrusted_external_data": True,
        "read_only_in_memory": True,
        "writes_back_to_cleanroom": WRITES_BACK_TO_CLEANROOM,
        "summary": dict(inbox_report.get("summary", {})),
        "ext_counts": dict(inbox_report.get("ext_counts", {})),
        "quarantined_binaries": [
            {
                "path": item.get("path"),
                "ext": item.get("ext"),
                "bytes": item.get("bytes"),
                "sha256_16": item.get("sha256_16"),
                "status": item.get("status"),
                "risk": item.get("risk"),
            }
            for item in inbox_report.get("quarantined_binaries", [])
        ],
        "set_flagged_anti_prop": [
            {
                "path": item.get("path"),
                "red_flags": item.get("red_flags", []),
                "verdict": item.get("verdict"),
            }
            for item in inbox_report.get("set_and_text", [])
            if item.get("red_flags")
        ],
        "open_source_code": [
            {
                "path": item.get("path"),
                "red_flags": item.get("red_flags", []),
                "intake_verdict": item.get("intake_verdict"),
            }
            for item in inbox_report.get("open_source_code", [])
        ],
    }


def _safe_display_cleanroom_root(intel_dir: Path) -> str:
    # Avoid leaking user profile paths if a test or runner passes a temp path under a user home.
    raw = intel_dir.as_posix()
    if re.search(r"(?i)(?:[A-Z]:|/mnt/[a-z])/Users/", raw):
        return f"<TEMP_CLEANROOM>/{intel_dir.name}"
    return raw


def sync_strategy_intel(
    *,
    intel_dir: Path = DEFAULT_INTEL_DIR,
    out_path: Path = DEFAULT_OUT_PATH,
    offline: bool = False,
    dry_run: bool = False,
    profile: str = "default",
) -> dict[str, Any]:
    """Run one-way read-only sync from strategy-intel cleanroom to TradingWorkspace runtime artifact."""
    if profile not in VALID_PROFILES:
        raise ValueError(f"Unsupported profile={profile!r}; expected one of {sorted(VALID_PROFILES)}")
    enforce_holdout_zero_rows(HOLDOUT_ROWS_ANALYSED, context="strategy_intel_bridge.start")
    now_utc = datetime.now(UTC).isoformat()

    if not intel_dir.exists():
        if not offline:
            raise FileNotFoundError(
                f"Cleanroom directory not found: {intel_dir} (pass --offline for CI-safe graceful mode)"
            )
        sources_read_off: dict[str, bool] = {
            "sanitized_master_leads": False,
            "sanitized_auto_leads": False,
            "inbox_scanned_in_memory": False,
        }
        summary_off: dict[str, int] = {
            "master_leads_loaded": 0,
            "auto_leads_loaded": 0,
            "total_leads_inspected": 0,
            "eligible_dev_candidates": 0,
            "filtered_out_s34_or_toxic": 0,
            "inbox_total_files": 0,
            "inbox_quarantined_binaries": 0,
            "inbox_set_flagged_anti_prop": 0,
            "inbox_open_source_clean": 0,
        }
        if profile == "offensive3":
            sources_read_off["sanitized_offensive3_leads"] = False
            summary_off["offensive3_leads_loaded"] = 0
            summary_off["section_3_4_exemptions_granted"] = 0
        payload: dict[str, Any] = {
            "schema": "naqex-strategy-intel-handoff-v1",
            "generated_at_utc": now_utc,
            "status": "OFFLINE_CLEANROOM_UNAVAILABLE",
            "mode": "offline",
            "cleanroom_present": False,
            "cleanroom_root": _safe_display_cleanroom_root(intel_dir),
            "untrusted_external_data": True,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": SPEND_VND,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            "holdout_cutoff_utc": f"{HOLDOUT_CUTOFF_DAY}T00:00:00Z",
            "writes_back_to_cleanroom": WRITES_BACK_TO_CLEANROOM,
            "sources_read": sources_read_off,
            "summary": summary_off,
            "eligible_dev_candidates": [],
            "filtered_out": [],
            "inbox_triage": None,
        }
        if profile == "offensive3":
            payload["profile"] = "offensive3"
        if not dry_run:
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
                newline="\n",
            )
        return payload

    handoff_dir = intel_dir / "handoff"
    master_present = False
    master_leads: list[dict[str, Any]] = []
    auto_present = False
    auto_leads: list[dict[str, Any]] = []
    off3_present = False
    off3_leads: list[dict[str, Any]] = []

    if profile == "offensive3":
        off3_present, off3_leads = _load_handoff_json_readonly(
            handoff_dir / "sanitized_offensive3_leads.json",
            label="sanitized_offensive3_leads",
        )
    else:
        master_present, master_leads = _load_handoff_json_readonly(
            handoff_dir / "sanitized_master_leads.json",
            label="sanitized_master_leads",
        )
        auto_present, auto_leads = _load_handoff_json_readonly(
            handoff_dir / "sanitized_auto_leads.json",
            label="sanitized_auto_leads",
        )

    # Strictly in-memory read-only inbox triage (NEVER invoke inbox_intake_scanner CLI!)
    inbox_dir = intel_dir / "inbox"
    inbox_triage: dict[str, Any] | None = None
    inbox_scanned = False
    if inbox_dir.is_dir():
        raw_inbox = inbox_intake_scanner.scan_inbox(inbox_dir, run_defender=False)
        inbox_triage = _sanitize_inbox_summary(raw_inbox)
        inbox_scanned = True

    if profile == "offensive3":
        combined_leads: list[tuple[str, dict[str, Any]]] = [
            ("sanitized_offensive3_leads", lead) for lead in off3_leads
        ]
    else:
        combined_leads = [("sanitized_master_leads", lead) for lead in master_leads] + [
            ("sanitized_auto_leads", lead) for lead in auto_leads
        ]

    eligible: list[dict[str, Any]] = []
    filtered_out: list[dict[str, Any]] = []
    exemptions_granted = 0

    for bucket, lead in combined_leads:
        if profile == "offensive3":
            norm_lead = _normalize_offensive3_lead(lead)
            filter_reasons, exemption_reason = evaluate_lead_for_offensive3(norm_lead)
            src_lead = norm_lead
        else:
            filter_reasons = evaluate_lead_against_s34(lead)
            exemption_reason = None
            src_lead = lead

        tagged: dict[str, Any] = {
            "lead_id": src_lead.get("lead_id"),
            "original_id": src_lead.get("original_id"),
            "handoff_source": bucket,
            "source": src_lead.get("source") or src_lead.get("source_url"),
            "name": src_lead.get("name"),
            "family": src_lead.get("family"),
            "symbol": src_lead.get("symbol"),
            "timeframe": src_lead.get("timeframe"),
            "direction": src_lead.get("direction"),
            "rule_description": src_lead.get("rule_description"),
            "replicability": src_lead.get("replicability"),
            "source_evidence_tier": src_lead.get("evidence_tier", "SOURCE_CLAIM_ONLY"),
            "data_quality_flags": list(src_lead.get("data_quality_flags", [])),
            "untrusted_external_data": True,
            "order_send_count": ORDER_SEND_COUNT,
            "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
            "dev_screening_window": f"<= 2024-12-31 (strictly pre-{HOLDOUT_CUTOFF_DAY})",
        }
        if profile == "offensive3":
            tagged["prop_track"] = src_lead.get("prop_track")
            tagged["counterparty_mechanism"] = src_lead.get("counterparty_mechanism")
            tagged["section_3_4_exemption_reason"] = exemption_reason
        if filter_reasons:
            tagged["filter_status"] = "FILTERED_OUT"
            tagged["filter_reasons"] = filter_reasons
            filtered_out.append(tagged)
        else:
            tagged["filter_status"] = "ELIGIBLE_FOR_DEV_SCREENING"
            tagged["filter_reasons"] = []
            if (
                profile == "offensive3"
                and exemption_reason
                and exemption_reason != "OFFENSIVE3_NO_S34_EXEMPTION_NEEDED"
            ):
                exemptions_granted += 1
            eligible.append(tagged)

    inbox_sum = inbox_triage["summary"] if inbox_triage else {}
    sources_read_ok: dict[str, bool] = {
        "sanitized_master_leads": master_present,
        "sanitized_auto_leads": auto_present,
        "inbox_scanned_in_memory": inbox_scanned,
    }
    summary_ok: dict[str, int] = {
        "master_leads_loaded": len(master_leads),
        "auto_leads_loaded": len(auto_leads),
        "total_leads_inspected": len(combined_leads),
        "eligible_dev_candidates": len(eligible),
        "filtered_out_s34_or_toxic": len(filtered_out),
        "inbox_total_files": int(inbox_sum.get("total_files", 0)),
        "inbox_quarantined_binaries": int(inbox_sum.get("quarantined_binaries_no_exec", 0)),
        "inbox_set_flagged_anti_prop": int(inbox_sum.get("set_flagged_anti_prop", 0)),
        "inbox_open_source_clean": int(inbox_sum.get("open_source_clean", 0)),
    }
    if profile == "offensive3":
        sources_read_ok["sanitized_offensive3_leads"] = off3_present
        summary_ok["offensive3_leads_loaded"] = len(off3_leads)
        summary_ok["section_3_4_exemptions_granted"] = exemptions_granted

    payload = {
        "schema": "naqex-strategy-intel-handoff-v1",
        "generated_at_utc": now_utc,
        "status": "OK",
        "mode": "offline" if offline else "local_readonly",
        "cleanroom_present": True,
        "cleanroom_root": _safe_display_cleanroom_root(intel_dir),
        "untrusted_external_data": True,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "holdout_cutoff_utc": f"{HOLDOUT_CUTOFF_DAY}T00:00:00Z",
        "writes_back_to_cleanroom": WRITES_BACK_TO_CLEANROOM,
        "sources_read": sources_read_ok,
        "summary": summary_ok,
        "eligible_dev_candidates": eligible,
        "filtered_out": filtered_out,
        "inbox_triage": inbox_triage,
    }
    if profile == "offensive3":
        payload["profile"] = "offensive3"

    if not dry_run:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return payload


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--intel-dir",
        type=Path,
        default=DEFAULT_INTEL_DIR,
        help="Path to the air-gapped strategy-intel cleanroom directory (read-only)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT_PATH,
        help="Output JSON handoff path inside TradingWorkspace .runtime/automation/",
    )
    parser.add_argument(
        "--profile",
        choices=("default", "offensive3"),
        default="default",
        help="Admission profile: 'default' (strict §3.4) or opt-in 'offensive3' (sanitized_offensive3_leads.json).",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        help="CI-safe offline mode: succeed cleanly if cleanroom directory does not exist",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute handoff payload in memory without writing the output JSON file",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        dest="as_json",
        help="Print full JSON handoff payload to stdout",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    payload = sync_strategy_intel(
        intel_dir=args.intel_dir,
        out_path=args.out,
        offline=args.offline,
        dry_run=args.dry_run,
        profile=args.profile,
    )
    if args.as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        s = payload["summary"]
        extra_off3 = (
            f" off3={s.get('offensive3_leads_loaded', 0)} exemptions={s.get('section_3_4_exemptions_granted', 0)}"
            if args.profile == "offensive3"
            else ""
        )
        print(
            f"STRATEGY_INTEL_BRIDGE_{payload['status']}: "
            f"master={s['master_leads_loaded']} auto={s['auto_leads_loaded']}{extra_off3} "
            f"eligible_dev={s['eligible_dev_candidates']} filtered_s34={s['filtered_out_s34_or_toxic']} "
            f"inbox_quarantined={s['inbox_quarantined_binaries']} writes_back={payload['writes_back_to_cleanroom']} "
            f"dry_run={args.dry_run}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
