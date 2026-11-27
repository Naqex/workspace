"""1-to-1 Python-vs-MT5 Parity Forensics, Legacy v1.01/v1.03 Adapter & Trade Geometry Loop (OPS-6).

Provides the complete closed-loop live/demo forensic engine:
  1. Legacy `v1.01/v1.03` & New Blackbox Adapters:
       - `load_exec_audit_records()` (`naqex_exec_audit.csv`)
       - `load_v103_shadow_csv()` (`naqex_master_v103_shadow.csv`)
       - `load_decision_blackbox_jsonl()` (`naqex_decision_blackbox_YYYYMMDD.jsonl`)
       - `aggregate_mt5_deals_by_position()` (split-deal & partial-fill grouping by `POSITION_IDENTIFIER`
         properly combining entry/exit commission, swap, fee, and realized PnL!)
  2. 1-to-1 Python-vs-MT5 Parity Classifier (`classify_parity_events`):
       - `MATCH_CLEAN`
       - `BOT_BUG_GHOST_TRADE` (immediate RED bug escalation)
       - `BOT_BUG_MISSED_TRADE` (immediate RED bug escalation when NO legitimate guard block logged)
       - `LOT_OR_SL_DRIFT` (`> 5%` lot or SL drift — catches `TICK_VALUE_LOSS` bugs!)
       - `EXECUTION_FRICTION_DRIFT` (spread/slippage/swap exceeded backtest budget -> routes to TCA)
       - `LEGITIMATE_GUARD_BLOCK` (Python signaled, MT5 legitimately blocked via `BLOCKED_BY_*` / `ORDER_BLOCKED_*` —
         NEVER misclassified as `BOT_BUG_MISSED_TRADE`!)
  3. MT5 Strategy Tester Parity Gate (`evaluate_tester_parity_gate` — exact `v3.5` formula):
       - `trade_match_rate >= 0.98` within `<= 1` bar
       - `ghost_trades == 0`
       - `max_lot_sl_drift <= 0.02`
       - `gross_r_drift <= 0.05`
  4. Trade Geometry (`W1..L4` + `excursions` on true broker tape) + `postmortem_gen.classify_discrepancy`
     + Anti-Overfit Feedback Protocol:
       - Technical bugs (`GHOST/MISSED/LOT_DRIFT`) -> `IMMEDIATE_FIX_REQUIRED`.
       - Strategy/parameter ideas from `L1/L2/L3` -> HARD-LOCKED behind `N_live >= 30` (recommended `>= 50`);
         emits draft `HypothesisCard` payloads tagged `MUST_VALIDATE_ON_7YR_DEV_BEFORE_CHANGE`
         (NEVER auto-tunes live parameters!).

HARD SAFETY & IMMUTABILITY INVARIANTS (`B5`, `H1`, `[ARCH-02]`, `G02`, `G11`, `G16`):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, NEVER imports `MetaTrader5`.
  - ZERO bare `assert` statements (`[ARCH-02]`).
  - NEVER touches `quant_core/`, `Naqex_PropGuard.mqh`, `v1.01`, or `v1.03`.
"""

from __future__ import annotations

import csv
import json
import math
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import (  # noqa: E402
    ENTRY_EVENT_TYPES,
    EXIT_EVENT_TYPES,
    NON_FILL_EVENT_TYPES,
    VALID_FILL_EVENT_TYPES,
    benchmark_spread_for_symbol,
    extract_comment_tags,
    load_exec_audit_csv,
    normalize_symbol_alias,
    parse_exec_audit_row,
    parse_optional_finite_float,
    parse_optional_strict_int,
    point_size_for_symbol,
    write_atomic_sha256_json,
)
from quant_core.trade_forensics_classifier import LABELS as GEOMETRY_LABELS  # noqa: E402
from quant_core.trade_forensics_classifier import classify as classify_trade_geometry  # noqa: E402
from quant_core.trade_forensics_classifier import concentration as compute_geometry_concentration  # noqa: E402
from quant_core.trade_forensics_classifier import excursions as compute_trade_excursions  # noqa: E402
from quant_core.trade_forensics_classifier import summarize as summarize_trade_geometry  # noqa: E402

from quant_factory.live_ops.live_broker_tape_ingestor import (  # noqa: E402
    extract_executable_price_path,
)
from quant_factory.postmortem_gen import classify_discrepancy  # noqa: E402
from quant_factory.research_council import (  # noqa: E402
    KillCriteria,
    propose_hypothesis,
)

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0

PARITY_MATCH_CLEAN: Final[str] = "MATCH_CLEAN"
PARITY_BOT_BUG_GHOST_TRADE: Final[str] = "BOT_BUG_GHOST_TRADE"
PARITY_BOT_BUG_MISSED_TRADE: Final[str] = "BOT_BUG_MISSED_TRADE"
PARITY_LOT_OR_SL_DRIFT: Final[str] = "LOT_OR_SL_DRIFT"
PARITY_EXECUTION_FRICTION_DRIFT: Final[str] = "EXECUTION_FRICTION_DRIFT"
PARITY_LEGITIMATE_GUARD_BLOCK: Final[str] = "LEGITIMATE_GUARD_BLOCK"

CORE_PARITY_CLASSES: Final[tuple[str, ...]] = (
    PARITY_MATCH_CLEAN,
    PARITY_BOT_BUG_GHOST_TRADE,
    PARITY_BOT_BUG_MISSED_TRADE,
    PARITY_LOT_OR_SL_DRIFT,
    PARITY_EXECUTION_FRICTION_DRIFT,
)

TECHNICAL_BUG_CLASSES: Final[frozenset[str]] = frozenset(
    {
        PARITY_BOT_BUG_GHOST_TRADE,
        PARITY_BOT_BUG_MISSED_TRADE,
        PARITY_LOT_OR_SL_DRIFT,
    }
)

# Canonical legitimate guard-block tokens across DecisionBlackbox + v1.01/v1.03 logs
LEGITIMATE_GUARD_BLOCK_DECISIONS: Final[frozenset[str]] = frozenset(
    {
        "BLOCKED_BY_SPREAD",
        "BLOCKED_BY_NEWS",
        "BLOCKED_BY_RED_NEWS",
        "BLOCKED_BY_SYMCAP",
        "BLOCKED_BY_HEADROOM",
        "BLOCKED_BY_RISK",
        "BLOCKED_BY_FACTOR",
        "BLOCKED_BY_CLUSTER_CAP",
        "BLOCKED_BY_MARGIN",
        "BLOCKED_BY_STOPS",
        "BLOCKED_BY_FEED",
        "BLOCKED_BY_TTL",
        "BLOCKED_BY_HALT",
        "BLOCKED_BY_DRYRUN",
        "BLOCKED_BY_POST_ROUND_CAP",
        "ORDER_BLOCKED_SPREAD",
        "ORDER_BLOCKED_NEWS",
        "ORDER_BLOCKED_SYMCAP",
        "ORDER_BLOCKED_FACTOR",
        "ORDER_BLOCKED_RISK",
        "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP",
        "ORDER_BLOCKED_MARGIN",
        "ORDER_BLOCKED_STOPS",
        "ORDER_BLOCKED_POST_ROUND_CAP",
    }
)

_V103_EVENT_TO_DECISION: Final[dict[str, str]] = {
    "ORDER_BLOCKED_SPREAD": "BLOCKED_BY_SPREAD",
    "ORDER_BLOCKED_NEWS": "BLOCKED_BY_NEWS",
    "ORDER_BLOCKED_SYMCAP": "BLOCKED_BY_SYMCAP",
    "ORDER_BLOCKED_FACTOR": "BLOCKED_BY_HEADROOM",
    "ORDER_BLOCKED_RISK": "BLOCKED_BY_HEADROOM",
    "ORDER_BLOCKED_TOTAL_OR_CLUSTER_CAP": "BLOCKED_BY_HEADROOM",
    "ORDER_BLOCKED_POST_ROUND_CAP": "BLOCKED_BY_HEADROOM",
    "ORDER_BLOCKED_MARGIN": "BLOCKED_BY_MARGIN",
    "ORDER_BLOCKED_STOPS": "BLOCKED_BY_STOPS",
    "DRYRUN_SIGNAL": "BLOCKED_BY_DRYRUN",
    "DRYRUN_SIGNAL_V103": "BLOCKED_BY_DRYRUN",
    "SHADOW_INTENT": "SHADOW_INTENT",
}

ANTI_OVERFIT_MIN_LIVE_TRADES: Final[int] = 30
ANTI_OVERFIT_RECOMMENDED_LIVE_TRADES: Final[int] = 50
MUST_VALIDATE_TAG: Final[str] = "MUST_VALIDATE_ON_7YR_DEV_BEFORE_CHANGE"

TESTER_GATE_SCHEMA: Final[str] = "naqex-tester-parity-gate-v3.5"
WEEKLY_FORENSICS_SCHEMA: Final[str] = "naqex-weekly-live-forensics-v1"

_DOT_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})(.*)$")


# ---------------------------------------------------------------------------
# Timestamp, Side & Field Normalization Helpers
# ---------------------------------------------------------------------------
def _parse_utc_ts_sec(raw: Any, *, field_name: str = "utc_ts") -> float:
    if raw is None or isinstance(raw, bool):
        raise ValueError(f"{field_name} must be a valid timestamp, got {raw!r}")
    if isinstance(raw, (int, float)):
        fv = float(raw)
        if not math.isfinite(fv) or fv < 0.0:
            raise ValueError(f"{field_name} must be finite >= 0, got {raw!r}")
        return fv / 1000.0 if fv >= 1.0e12 else fv
    if isinstance(raw, str):
        s = raw.strip()
        if not s:
            raise ValueError(f"{field_name} cannot be blank")
        try:
            fv = float(s)
            if not math.isfinite(fv) or fv < 0.0:
                raise ValueError(f"{field_name} must be finite >= 0, got {raw!r}")
            return fv / 1000.0 if fv >= 1.0e12 else fv
        except ValueError:
            pass
        dot_m = _DOT_DATE_RE.fullmatch(s)
        if dot_m is not None:
            s = f"{dot_m.group(1)}-{dot_m.group(2)}-{dot_m.group(3)}{dot_m.group(4)}"
        if s.endswith(("Z", "z")):
            s = s[:-1] + "+00:00"
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return float(dt.timestamp())
    raise ValueError(f"{field_name} unsupported timestamp type {type(raw).__name__}")


def _parse_optional_utc_ts_sec(raw: Any, *, field_name: str = "utc_ts") -> float | None:
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return None
    return _parse_utc_ts_sec(raw, field_name=field_name)


def _normalize_side(raw: Any) -> str:
    s = str(raw or "").strip().upper()
    if s in ("BUY", "LONG", "+1", "1", "DEAL_TYPE_BUY", "ORDER_TYPE_BUY"):
        return "BUY"
    if s in ("SELL", "SHORT", "-1", "DEAL_TYPE_SELL", "ORDER_TYPE_SELL"):
        return "SELL"
    return s


def _side_to_sign(side: str) -> int:
    s = _normalize_side(side)
    if s == "BUY":
        return 1
    if s == "SELL":
        return -1
    raise ValueError(f"Unsupported trade side {side!r}; expected BUY or SELL")


def _normalize_guard_decision(raw: Any) -> str:
    s = str(raw or "").strip().upper()
    if not s:
        return ""
    if s in _V103_EVENT_TO_DECISION:
        return _V103_EVENT_TO_DECISION[s]
    return s


def is_legitimate_guard_block(decision_or_event: Any) -> bool:
    """Return True iff `decision_or_event` represents an authorized prop-guard block."""
    raw = str(decision_or_event or "").strip().upper()
    norm = _normalize_guard_decision(raw)
    if raw in LEGITIMATE_GUARD_BLOCK_DECISIONS or norm in LEGITIMATE_GUARD_BLOCK_DECISIONS:
        return True
    return norm.startswith("BLOCKED_BY_") or raw.startswith("ORDER_BLOCKED_")


def _normalize_exit_reason(raw_reason: Any, event_type: str = "", comment: str = "") -> str:
    tokens = f"{raw_reason or ''} {event_type or ''} {comment or ''}".upper()
    if "SL_HIT" in tokens or re.search(r"\bSL\b|\[SL", tokens):
        return "SL"
    if "TP_HIT" in tokens or re.search(r"\bTP\b|\[TP", tokens):
        return "TP"
    if "PRE_FLATTEN" in tokens or "FLATTEN" in tokens:
        return "PRE_FLATTEN"
    if "TIME_EXIT" in tokens or "TIME" in tokens:
        return "TIME_EXIT"
    if str(raw_reason or "").strip():
        return str(raw_reason).strip().upper()
    return "CLOSE"


# ---------------------------------------------------------------------------
# 1. Legacy v1.01/v1.03 & Decision Blackbox Adapters + POSITION_IDENTIFIER Aggregator
# ---------------------------------------------------------------------------
def load_exec_audit_records(csv_path: Path | str) -> list[dict[str, Any]]:
    """Parse native `naqex_exec_audit.csv` (`v1.01` / `v1.03`) through canonical `quant_core.tca`."""
    rows = load_exec_audit_csv(csv_path)
    out: list[dict[str, Any]] = []
    for row in rows:
        rec = dict(row)
        rec["source_format"] = "naqex_exec_audit_csv"
        rec["side"] = _normalize_side(rec.get("side"))
        rec["decision"] = (
            _normalize_guard_decision(rec["event_type"])
            if is_legitimate_guard_block(rec.get("event_type"))
            else ("FIRE" if rec.get("event_type") in VALID_FILL_EVENT_TYPES else str(rec.get("event_type") or ""))
        )
        out.append(rec)
    return out


def load_v103_shadow_csv(csv_path: Path | str) -> list[dict[str, Any]]:
    """Parse native `naqex_master_v103_shadow.csv` (`v1.03`) into normalized decision records."""
    path = Path(csv_path)
    if not path.is_file():
        raise FileNotFoundError(f"v1.03 shadow CSV not found: {path}")

    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not reader.fieldnames:
            raise ValueError(f"Empty header in v1.03 shadow CSV: {path}")
        for line_no, raw in enumerate(reader, start=2):
            if not raw or all(str(v or "").strip() == "" for v in raw.values()):
                continue
            try:
                utc_ts = _parse_utc_ts_sec(raw.get("utc_ts"), field_name="utc_ts")
                symbol = str(raw.get("symbol") or "").strip()
                if not symbol:
                    raise ValueError("symbol is required in v1.03 shadow CSV")
                ev_type = str(raw.get("event_type") or "").strip().upper()
                side = _normalize_side(raw.get("deal_side") or raw.get("side"))
                magic = parse_optional_strict_int(raw.get("magic"), field_name="magic") or 0
                account_login = parse_optional_strict_int(raw.get("account_login"), field_name="account_login")
                sig_px = parse_optional_finite_float(raw.get("signal_price"), field_name="signal_price")
                sl_px = parse_optional_finite_float(raw.get("sl_price"), field_name="sl_price")
                risk_pct = parse_optional_finite_float(raw.get("risk_pct"), field_name="risk_pct")
                lots = parse_optional_finite_float(raw.get("lots"), field_name="lots")
                tick_lag_ms = parse_optional_finite_float(raw.get("tick_lag_ms"), field_name="tick_lag_ms")
                shadow_only = str(raw.get("shadow_only") or "").strip().lower() == "true"
                reason = str(raw.get("reason") or "").strip()
                intent_id = str(raw.get("intent_id") or "").strip()
                engine_id = str(raw.get("engine_id") or "").strip()
                records.append(
                    {
                        "source_format": "naqex_master_v103_shadow_csv",
                        "utc_ts": utc_ts,
                        "utc_time": datetime.fromtimestamp(utc_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "account_login": account_login,
                        "signal_id": intent_id,
                        "intent_id": intent_id,
                        "engine_id": engine_id,
                        "magic": magic,
                        "position_id": "",
                        "symbol": symbol,
                        "canonical_symbol": normalize_symbol_alias(symbol),
                        "side": side,
                        "event_type": ev_type,
                        "decision": _normalize_guard_decision(ev_type),
                        "block_reason": reason,
                        "expected_entry": sig_px,
                        "expected_sl": sl_px,
                        "expected_lot": lots,
                        "risk_pct": risk_pct,
                        "tick_lag_ms": tick_lag_ms,
                        "shadow_only": shadow_only,
                        "indicators": {},
                    }
                )
            except ValueError as exc:
                raise ValueError(f"{path.name}:{line_no}: {exc}") from exc
    return records


def load_decision_blackbox_jsonl(
    path_or_paths: Path | str | Sequence[Path | str],
    *,
    allow_truncated_tail: bool = False,
) -> list[dict[str, Any]]:
    """Parse `naqex_decision_blackbox_YYYYMMDD.jsonl` (single file, directory, or sequence).

    Fail-closed by default (`allow_truncated_tail=False`): any malformed/corrupted JSONL line
    raises `ValueError` instead of being silently dropped to `[]`. Opt-in `allow_truncated_tail=True`
    tolerates ONLY an unterminated trailing line starting with `'{'` (mid-write flush).
    """
    paths: list[Path] = []
    if isinstance(path_or_paths, (str, Path)):
        p = Path(path_or_paths)
        if p.is_dir():
            paths.extend(sorted(p.glob("naqex_decision_blackbox_*.jsonl")))
        elif p.is_file():
            paths.append(p)
        else:
            raise FileNotFoundError(f"Decision blackbox path not found: {p}")
    else:
        for item in path_or_paths:
            p = Path(item)
            if p.is_dir():
                paths.extend(sorted(p.glob("naqex_decision_blackbox_*.jsonl")))
            elif p.is_file():
                paths.append(p)
            else:
                raise FileNotFoundError(f"Decision blackbox file not found: {p}")

    records: list[dict[str, Any]] = []
    for file_path in paths:
        raw_bytes = file_path.read_bytes()
        if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
            raise ValueError(
                f"UTF16_BOM_FORBIDDEN in {file_path.name}: Naqex_DecisionBlackbox.mqh MUST write strict FILE_ANSI"
            )
        text = raw_bytes.decode("utf-8-sig", errors="strict")
        ends_with_newline = text.endswith(("\n", "\r"))
        lines = text.splitlines()
        for line_idx, raw_line in enumerate(lines, start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                obj = json.loads(stripped)
            except json.JSONDecodeError as exc:
                if (
                    allow_truncated_tail
                    and line_idx == len(lines)
                    and not ends_with_newline
                    and stripped.startswith("{")
                ):
                    continue
                raise ValueError(f"{file_path.name}:{line_idx}: malformed JSONL line: {exc}") from exc
            if not isinstance(obj, Mapping):
                raise ValueError(f"{file_path.name}:{line_idx}: expected JSON object")

            ts_raw = obj.get("utc_ts") if obj.get("utc_ts") not in (None, "") else obj.get("utc_time")
            utc_ts = _parse_utc_ts_sec(ts_raw, field_name="blackbox.utc_ts")
            symbol = str(obj.get("symbol") or "").strip()
            if not symbol:
                raise ValueError(f"{file_path.name}:{line_idx}: symbol is required")

            raw_indicators = obj.get("indicators")
            if isinstance(raw_indicators, str):
                indicators = json.loads(raw_indicators) if raw_indicators.strip() else {}
            elif isinstance(raw_indicators, Mapping):
                indicators = dict(raw_indicators)
            else:
                indicators = {}

            raw_decision = str(obj.get("decision") or "").strip().upper()
            if not raw_decision:
                raise ValueError(f"{file_path.name}:{line_idx}: decision is required")

            pos_id = str(obj.get("position_id") or "").strip()
            if pos_id == "0":
                pos_id = ""

            records.append(
                {
                    "source_format": "naqex_decision_blackbox_jsonl",
                    "source_file": file_path.name,
                    "signal_id": str(obj.get("signal_id") or "").strip(),
                    "magic": parse_optional_strict_int(obj.get("magic"), field_name="blackbox.magic") or 0,
                    "position_id": pos_id,
                    "symbol": symbol,
                    "canonical_symbol": normalize_symbol_alias(symbol),
                    "side": _normalize_side(obj.get("side")),
                    "server_time": str(obj.get("server_time") or "").strip(),
                    "utc_time": str(
                        obj.get("utc_time") or datetime.fromtimestamp(utc_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
                    ).strip(),
                    "utc_ts": utc_ts,
                    "bid": parse_optional_finite_float(obj.get("bid"), field_name="blackbox.bid"),
                    "ask": parse_optional_finite_float(obj.get("ask"), field_name="blackbox.ask"),
                    "spread_pts": parse_optional_finite_float(obj.get("spread_pts"), field_name="blackbox.spread_pts"),
                    "indicators": indicators,
                    "expected_entry": parse_optional_finite_float(
                        obj.get("expected_entry"), field_name="blackbox.expected_entry"
                    ),
                    "expected_sl": parse_optional_finite_float(
                        obj.get("expected_sl"), field_name="blackbox.expected_sl"
                    ),
                    "expected_lot": parse_optional_finite_float(
                        obj.get("expected_lot"), field_name="blackbox.expected_lot"
                    ),
                    "decision": _normalize_guard_decision(raw_decision),
                    "raw_decision": raw_decision,
                    "block_reason": str(obj.get("block_reason") or "").strip(),
                    "strategy_sha": str(obj.get("strategy_sha") or "").strip(),
                    "preset_sha": str(obj.get("preset_sha") or "").strip(),
                    "in_tester": bool(obj.get("in_tester", False)),
                }
            )
    records.sort(key=lambda r: (r["utc_ts"], r["canonical_symbol"], r["signal_id"]))
    return records


def _extract_position_key(row: Mapping[str, Any], fallback_idx: int) -> str:
    tags = extract_comment_tags(str(row.get("comment") or ""))
    for cand in (
        row.get("position_id"),
        row.get("POSITION_IDENTIFIER"),
        row.get("position"),
        tags.get("pos"),
        row.get("order_id"),
        tags.get("ord"),
        row.get("ticket"),
        tags.get("tk"),
        row.get("deal_id"),
        tags.get("deal"),
    ):
        s = str(cand or "").strip()
        if s and s != "0":
            return s
    return f"UNKEYED_{fallback_idx}"


def _classify_deal_leg(row: Mapping[str, Any]) -> str:
    ev = str(row.get("event_type") or "").strip().upper()
    leg = str(row.get("leg") or row.get("deal_entry") or row.get("entry") or "").strip().upper()
    if ev in EXIT_EVENT_TYPES or leg in ("EXIT", "OUT", "DEAL_ENTRY_OUT", "OUT_BY", "DEAL_ENTRY_OUT_BY"):
        return "EXIT"
    if ev in ENTRY_EVENT_TYPES or leg in ("ENTRY", "IN", "DEAL_ENTRY_IN"):
        return "ENTRY"
    if leg in ("INOUT", "DEAL_ENTRY_INOUT"):
        return "EXIT"
    # Default single-row fill is ENTRY
    return "ENTRY"


def _sum_optional_costs(values: Sequence[float | None]) -> float | None:
    present = [v for v in values if v is not None]
    if not present:
        return None
    return round(float(sum(present)), 6)


def aggregate_mt5_deals_by_position(
    raw_deals: Iterable[Mapping[str, Any]],
) -> list[dict[str, Any]]:
    """Aggregate partial fills and split entry/exit deals by `POSITION_IDENTIFIER`.

    Properly combines:
      - Volume-weighted `entry_price`, `signal_price`, `exit_price`, `spread_pts`
      - Total `entry_lots` and `closed_lots`
      - Entry + exit `commission_usd`, `swap_usd`, `fee_usd`, and `gross_pnl_usd` / `net_pnl_usd`
      - Preserves `None` when ALL constituent deals have `None` (P0-7 no silent blank -> 0.0 coercion)
    """
    grouped: dict[str, list[dict[str, Any]]] = {}
    order_keys: list[str] = []

    for idx, raw in enumerate(raw_deals):
        ev_raw = str(raw.get("event_type") or "").strip().upper()
        if ev_raw in NON_FILL_EVENT_TYPES:
            continue
        if "event_type" in raw and raw.get("event_type") and "canonical_symbol" not in raw:
            parsed = parse_exec_audit_row(raw, require_core_fields=False)
            # Preserve extra statement/deal fields not in parse_exec_audit_row
            for extra_k in (
                "leg",
                "deal_entry",
                "entry",
                "exit_price",
                "close_price",
                "exit_utc_ts",
                "close_time",
                "exit_reason",
                "fee_usd",
                "fee",
                "initial_risk_usd",
                "gross_R",
                "net_R",
                "family",
                "day_range_ATR",
                "signal_id",
                "POSITION_IDENTIFIER",
            ):
                if extra_k in raw and extra_k not in parsed:
                    parsed[extra_k] = raw[extra_k]
            row = parsed
        else:
            row = dict(raw)
            if "canonical_symbol" not in row:
                row["canonical_symbol"] = normalize_symbol_alias(str(row.get("symbol") or ""))

        pos_key = _extract_position_key(row, idx)
        if pos_key not in grouped:
            grouped[pos_key] = []
            order_keys.append(pos_key)
        grouped[pos_key].append(row)

    positions: list[dict[str, Any]] = []
    for pos_key in order_keys:
        deals = grouped[pos_key]
        deals.sort(
            key=lambda d: _parse_optional_utc_ts_sec(
                d.get("utc_ts") if d.get("utc_ts") not in (None, "") else d.get("entry_utc_ts")
            )
            or 0.0
        )

        entry_deals = [d for d in deals if _classify_deal_leg(d) == "ENTRY"]
        exit_deals = [d for d in deals if _classify_deal_leg(d) == "EXIT"]
        if not entry_deals:
            entry_deals = [deals[0]]
            exit_deals = deals[1:]

        ref = entry_deals[0]
        raw_sym = str(ref.get("symbol") or "").strip()
        canon_sym = normalize_symbol_alias(raw_sym)
        side = _normalize_side(ref.get("position_side") or ref.get("side") or ref.get("deal_side"))
        magic = parse_optional_strict_int(ref.get("magic"), field_name="magic") or 0
        tags_ref = extract_comment_tags(str(ref.get("comment") or ""))
        signal_id = str(ref.get("signal_id") or ref.get("intent_id") or tags_ref.get("intent") or "").strip()

        def _vol(d: Mapping[str, Any]) -> float:
            v = parse_optional_finite_float(
                d.get("lots") if "lots" in d else d.get("volume"), field_name="lots"
            )
            return float(v) if (v is not None and v > 0.0) else 0.0

        def _px(d: Mapping[str, Any], *keys: str) -> float | None:
            for k in keys:
                if k in d and d[k] not in (None, ""):
                    v = parse_optional_finite_float(d[k], field_name=k)
                    if v is not None and v > 0.0:
                        return v
            return None

        entry_lots = sum(_vol(d) for d in entry_deals)
        if entry_lots > 0.0:
            weighted_entry = sum(
                (_px(d, "fill_price", "entry_price", "price") or 0.0) * _vol(d) for d in entry_deals
            )
            entry_price = weighted_entry / entry_lots
            sig_weights = [
                (_px(d, "signal_price", "fill_price", "entry_price", "price") or entry_price, _vol(d))
                for d in entry_deals
            ]
            signal_price = sum(p * w for p, w in sig_weights) / entry_lots
        else:
            entry_price = _px(ref, "fill_price", "entry_price", "price") or 0.0
            signal_price = _px(ref, "signal_price") or entry_price

        sl_candidates = [_px(d, "sl_price", "sl", "initial_sl") for d in entry_deals]
        sl_price = next((s for s in sl_candidates if s is not None), 0.0)

        entry_ts_vals = [
            _parse_optional_utc_ts_sec(d.get("utc_ts") if d.get("utc_ts") not in (None, "") else d.get("entry_utc_ts"))
            for d in entry_deals
        ]
        entry_utc_ts = min((t for t in entry_ts_vals if t is not None), default=0.0)

        closed_lots = sum(_vol(d) for d in exit_deals)
        exit_price: float | None = None
        exit_utc_ts: float | None = None
        exit_reason: str | None = None
        if exit_deals:
            if closed_lots > 0.0:
                weighted_exit = sum(
                    (_px(d, "fill_price", "exit_price", "close_price", "price") or 0.0) * _vol(d)
                    for d in exit_deals
                )
                exit_price = weighted_exit / closed_lots
            else:
                exit_price = _px(exit_deals[-1], "fill_price", "exit_price", "close_price", "price")
            exit_ts_vals = [
                _parse_optional_utc_ts_sec(
                    d.get("utc_ts") if d.get("utc_ts") not in (None, "") else d.get("exit_utc_ts")
                )
                for d in exit_deals
            ]
            exit_utc_ts = max((t for t in exit_ts_vals if t is not None), default=None)
            last_exit = exit_deals[-1]
            exit_reason = _normalize_exit_reason(
                last_exit.get("exit_reason") or last_exit.get("reason"),
                str(last_exit.get("event_type") or ""),
                str(last_exit.get("comment") or ""),
            )
        else:
            # Support pre-paired single-row records carrying exit_price/exit_utc_ts directly
            exit_price = _px(ref, "exit_price", "close_price")
            exit_utc_ts = _parse_optional_utc_ts_sec(
                ref.get("exit_utc_ts") if ref.get("exit_utc_ts") not in (None, "") else ref.get("close_time")
            )
            if exit_price is not None:
                closed_lots = entry_lots
                exit_reason = _normalize_exit_reason(
                    ref.get("exit_reason") or ref.get("reason"),
                    str(ref.get("event_type") or ""),
                    str(ref.get("comment") or ""),
                )

        # Combine entry + exit commissions, swaps, fees, and PnL across ALL deals of the position
        comm_vals = [
            parse_optional_finite_float(
                d.get("commission_usd") if "commission_usd" in d else d.get("commission"),
                field_name="commission_usd",
            )
            for d in deals
        ]
        swap_vals = [
            parse_optional_finite_float(
                d.get("swap_usd") if "swap_usd" in d else d.get("swap"),
                field_name="swap_usd",
            )
            for d in deals
        ]
        fee_vals = [
            parse_optional_finite_float(
                d.get("fee_usd") if "fee_usd" in d else d.get("fee"),
                field_name="fee_usd",
            )
            for d in deals
        ]
        pnl_vals = [
            parse_optional_finite_float(
                d.get("pnl_usd") if "pnl_usd" in d else d.get("profit"),
                field_name="pnl_usd",
            )
            for d in deals
        ]

        commission_usd = _sum_optional_costs(comm_vals)
        swap_usd = _sum_optional_costs(swap_vals)
        fee_usd = _sum_optional_costs(fee_vals)
        gross_pnl_usd = _sum_optional_costs(pnl_vals)
        net_pnl_usd: float | None = None
        if gross_pnl_usd is not None:
            net_pnl_usd = round(
                gross_pnl_usd + (commission_usd or 0.0) + (swap_usd or 0.0) + (fee_usd or 0.0),
                6,
            )

        spread_vals = [
            (
                parse_optional_finite_float(d.get("spread_pts"), field_name="spread_pts"),
                max(_vol(d), 1e-6),
            )
            for d in entry_deals
        ]
        valid_spreads = [(s, w) for s, w in spread_vals if s is not None]
        spread_pts = (
            sum(s * w for s, w in valid_spreads) / sum(w for _, w in valid_spreads)
            if valid_spreads
            else 0.0
        )
        latencies = [
            parse_optional_finite_float(d.get("latency_ms"), field_name="latency_ms") or 0.0 for d in deals
        ]
        max_latency_ms = max(latencies) if latencies else 0.0

        pt = point_size_for_symbol(raw_sym or canon_sym)
        side_sign = 1.0 if side == "BUY" else (-1.0 if side == "SELL" else 0.0)
        adverse_slip_pts = (
            (side_sign * (entry_price - signal_price) / pt)
            if (pt > 0.0 and entry_price > 0.0 and signal_price > 0.0 and side_sign != 0.0)
            else 0.0
        )
        sl_dist = abs(entry_price - sl_price) if (entry_price > 0.0 and sl_price > 0.0) else 0.0

        explicit_gross_r = parse_optional_finite_float(
            ref.get("gross_R") if "gross_R" in ref else ref.get("gross_r"),
            field_name="gross_R",
        )
        computed_gross_r: float | None = explicit_gross_r
        if computed_gross_r is None and exit_price is not None and sl_dist > 1e-12 and side_sign != 0.0:
            computed_gross_r = side_sign * (exit_price - entry_price) / sl_dist

        explicit_net_r = parse_optional_finite_float(
            ref.get("net_R") if "net_R" in ref else ref.get("net_r"),
            field_name="net_R",
        )
        initial_risk_usd = parse_optional_finite_float(ref.get("initial_risk_usd"), field_name="initial_risk_usd")
        computed_net_r = explicit_net_r
        if (
            computed_net_r is None
            and net_pnl_usd is not None
            and initial_risk_usd is not None
            and initial_risk_usd > 0.0
        ):
            computed_net_r = net_pnl_usd / initial_risk_usd
        elif computed_net_r is None and computed_gross_r is not None:
            computed_net_r = computed_gross_r

        deal_ids = [
            str(d.get("deal_id") or extract_comment_tags(str(d.get("comment") or "")).get("deal") or "").strip()
            for d in deals
        ]
        deal_ids = [did for did in deal_ids if did]

        is_closed = exit_price is not None and closed_lots > 0.0
        incomplete_close = bool(
            is_closed and entry_lots > 0.0 and abs(closed_lots - entry_lots) > max(1e-6, 0.01 * entry_lots)
        )

        positions.append(
            {
                "position_id": pos_key,
                "signal_id": signal_id,
                "magic": magic,
                "symbol": raw_sym,
                "canonical_symbol": canon_sym,
                "side": side,
                "entry_utc_ts": entry_utc_ts,
                "utc_ts": entry_utc_ts,
                "exit_utc_ts": exit_utc_ts,
                "signal_price": round(float(signal_price), 8),
                "entry_price": round(float(entry_price), 8),
                "fill_price": round(float(entry_price), 8),
                "sl_price": round(float(sl_price), 8),
                "sl_dist": round(float(sl_dist), 8),
                "exit_price": round(float(exit_price), 8) if exit_price is not None else None,
                "lots": round(float(entry_lots), 6),
                "closed_lots": round(float(closed_lots), 6),
                "is_closed": is_closed,
                "incomplete_close": incomplete_close,
                "exit_reason": exit_reason,
                "spread_pts": round(float(spread_pts), 4),
                "adverse_slip_pts": round(float(adverse_slip_pts), 4),
                "latency_ms": round(float(max_latency_ms), 3),
                "commission_usd": commission_usd,
                "swap_usd": swap_usd,
                "fee_usd": fee_usd,
                "gross_pnl_usd": gross_pnl_usd,
                "net_pnl_usd": net_pnl_usd,
                "initial_risk_usd": initial_risk_usd,
                "gross_R": round(float(computed_gross_r), 6) if computed_gross_r is not None else None,
                "net_R": round(float(computed_net_r), 6) if computed_net_r is not None else None,
                "family": ref.get("family"),
                "day_range_ATR": parse_optional_finite_float(ref.get("day_range_ATR"), field_name="day_range_ATR"),
                "entry_deal_count": len(entry_deals),
                "exit_deal_count": len(exit_deals),
                "total_deal_count": len(deals),
                "deal_ids": deal_ids,
            }
        )

    positions.sort(key=lambda p: (p["entry_utc_ts"], p["canonical_symbol"], p["position_id"]))
    return positions


# ---------------------------------------------------------------------------
# 2. 1-to-1 Python-vs-MT5 Parity Classifier (5 Exact Classes + Guard Blocks)
# ---------------------------------------------------------------------------
def _normalize_parity_trade(raw: Mapping[str, Any], *, role: str, idx: int) -> dict[str, Any]:
    raw_sym = str(raw.get("symbol") or "").strip()
    if not raw_sym:
        raise ValueError(f"{role}[{idx}] missing symbol")
    canon_sym = normalize_symbol_alias(raw_sym)
    side = _normalize_side(raw.get("side") or raw.get("deal_side") or raw.get("direction"))
    if side not in ("BUY", "SELL"):
        raise ValueError(f"{role}[{idx}] invalid side {side!r}; expected BUY or SELL")

    ts_raw = (
        raw.get("entry_utc_ts")
        if raw.get("entry_utc_ts") not in (None, "")
        else (raw.get("utc_ts") if raw.get("utc_ts") not in (None, "") else raw.get("utc_time"))
    )
    utc_ts = _parse_utc_ts_sec(ts_raw, field_name=f"{role}[{idx}].utc_ts")
    magic = parse_optional_strict_int(raw.get("magic"), field_name=f"{role}[{idx}].magic") or 0
    signal_id = str(raw.get("signal_id") or raw.get("intent_id") or "").strip()
    position_id = str(raw.get("position_id") or raw.get("ticket") or "").strip()

    entry_px = parse_optional_finite_float(
        raw.get("entry_price")
        if raw.get("entry_price") not in (None, "")
        else (raw.get("fill_price") if raw.get("fill_price") not in (None, "") else raw.get("expected_entry")),
        field_name=f"{role}[{idx}].entry_price",
    )
    sig_px = parse_optional_finite_float(
        raw.get("signal_price") if raw.get("signal_price") not in (None, "") else entry_px,
        field_name=f"{role}[{idx}].signal_price",
    )
    sl_px = parse_optional_finite_float(
        raw.get("sl_price")
        if raw.get("sl_price") not in (None, "")
        else (raw.get("expected_sl") if raw.get("expected_sl") not in (None, "") else raw.get("sl")),
        field_name=f"{role}[{idx}].sl_price",
    )
    sl_dist = parse_optional_finite_float(raw.get("sl_dist"), field_name=f"{role}[{idx}].sl_dist")
    if sl_dist is None and entry_px is not None and sl_px is not None and entry_px > 0.0 and sl_px > 0.0:
        sl_dist = abs(entry_px - sl_px)
    lots = parse_optional_finite_float(
        raw.get("lots")
        if raw.get("lots") not in (None, "")
        else (raw.get("expected_lot") if raw.get("expected_lot") not in (None, "") else raw.get("volume")),
        field_name=f"{role}[{idx}].lots",
    )
    exit_px = parse_optional_finite_float(
        raw.get("exit_price") if raw.get("exit_price") not in (None, "") else raw.get("close_price"),
        field_name=f"{role}[{idx}].exit_price",
    )
    spread_pts = parse_optional_finite_float(
        raw.get("spread_pts")
        if raw.get("spread_pts") not in (None, "")
        else raw.get("expected_spread_pts"),
        field_name=f"{role}[{idx}].spread_pts",
    )
    spread_budget_pts = parse_optional_finite_float(
        raw.get("spread_budget_pts"), field_name=f"{role}[{idx}].spread_budget_pts"
    )
    slip_budget_pts = parse_optional_finite_float(
        raw.get("slippage_budget_pts"), field_name=f"{role}[{idx}].slippage_budget_pts"
    )
    adverse_slip_pts = parse_optional_finite_float(
        raw.get("adverse_slip_pts"), field_name=f"{role}[{idx}].adverse_slip_pts"
    )
    if adverse_slip_pts is None and entry_px is not None and sig_px is not None:
        pt = point_size_for_symbol(raw_sym or canon_sym)
        if pt > 0.0:
            adverse_slip_pts = _side_to_sign(side) * (entry_px - sig_px) / pt
    swap_usd = parse_optional_finite_float(
        raw.get("swap_usd") if "swap_usd" in raw else raw.get("swap"),
        field_name=f"{role}[{idx}].swap_usd",
    )

    gross_r = parse_optional_finite_float(
        raw.get("gross_R") if raw.get("gross_R") not in (None, "") else raw.get("gross_r"),
        field_name=f"{role}[{idx}].gross_R",
    )
    if gross_r is None and exit_px is not None and entry_px is not None and sl_dist is not None and sl_dist > 1e-12:
        gross_r = _side_to_sign(side) * (exit_px - entry_px) / sl_dist

    return {
        "index": idx,
        "symbol": raw_sym,
        "canonical_symbol": canon_sym,
        "side": side,
        "utc_ts": utc_ts,
        "magic": magic,
        "signal_id": signal_id,
        "position_id": position_id,
        "entry_price": entry_px,
        "signal_price": sig_px,
        "sl_price": sl_px,
        "sl_dist": sl_dist,
        "lots": lots,
        "exit_price": exit_px,
        "spread_pts": spread_pts,
        "spread_budget_pts": spread_budget_pts,
        "slippage_budget_pts": slip_budget_pts,
        "adverse_slip_pts": adverse_slip_pts,
        "swap_usd": swap_usd,
        "gross_R": gross_r,
        "raw": dict(raw),
    }


def _find_matching_guard_block(
    expected: Mapping[str, Any],
    blackbox_records: Sequence[Mapping[str, Any]],
    *,
    time_tolerance_sec: float,
) -> dict[str, Any] | None:
    best: tuple[float, dict[str, Any]] | None = None
    exp_sym = expected["canonical_symbol"]
    exp_side = expected["side"]
    exp_ts = float(expected["utc_ts"])
    exp_magic = int(expected.get("magic") or 0)
    exp_sig_id = str(expected.get("signal_id") or "").strip()

    for bb in blackbox_records:
        dec = bb.get("decision") or bb.get("event_type") or ""
        if not is_legitimate_guard_block(dec):
            continue
        bb_sym = normalize_symbol_alias(str(bb.get("canonical_symbol") or bb.get("symbol") or ""))
        if bb_sym != exp_sym:
            continue
        bb_side = _normalize_side(bb.get("side") or bb.get("deal_side") or "")
        if bb_side and bb_side != exp_side:
            continue
        bb_magic = parse_optional_strict_int(bb.get("magic"), field_name="blackbox.magic") or 0
        if exp_magic > 0 and bb_magic > 0 and bb_magic != exp_magic:
            continue
        bb_sig_id = str(bb.get("signal_id") or bb.get("intent_id") or "").strip()
        if exp_sig_id and bb_sig_id and bb_sig_id == exp_sig_id:
            return dict(bb)
        bb_ts_raw = bb.get("utc_ts") if bb.get("utc_ts") not in (None, "") else bb.get("utc_time")
        bb_ts = _parse_optional_utc_ts_sec(bb_ts_raw)
        if bb_ts is None:
            continue
        dt = abs(bb_ts - exp_ts)
        if dt <= time_tolerance_sec and (best is None or dt < best[0]):
            best = (dt, dict(bb))
    return best[1] if best is not None else None


def classify_parity_events(
    expected_python_trades: Sequence[Mapping[str, Any]],
    actual_mt5_trades: Sequence[Mapping[str, Any]],
    decision_blackbox: Sequence[Mapping[str, Any]] | None = None,
    *,
    time_tolerance_sec: float = 60.0,
    lot_sl_drift_tol: float = 0.05,
    spread_budget_mult: float = 1.50,
    max_slippage_budget_pts: float = 15.0,
    max_slippage_r_budget: float = 0.12,
    swap_tolerance_usd: float = 0.0,
) -> dict[str, Any]:
    """Classify EVERY Python-expected vs MT5-actual event into the 5 canonical parity classes.

    Core 5 classes:
      1. `MATCH_CLEAN`
      2. `BOT_BUG_GHOST_TRADE` (MT5 fired with no matching Python signal -> RED immediate fix)
      3. `BOT_BUG_MISSED_TRADE` (Python signaled, MT5 did NOT fire & no guard block -> RED immediate fix)
      4. `LOT_OR_SL_DRIFT` (signal matched, lot or SL distance drifted > `lot_sl_drift_tol` -> RED immediate fix)
      5. `EXECUTION_FRICTION_DRIFT` (signal/lot/SL matched, realized spread/slippage/swap exceeded budget -> TCA)
    Legitimate guard blocks (`BLOCKED_BY_SPREAD/NEWS/SYMCAP/HEADROOM/...`) are recorded as
    `LEGITIMATE_GUARD_BLOCK` and NEVER misclassified as `BOT_BUG_MISSED_TRADE`.
    """
    if time_tolerance_sec < 0.0 or not math.isfinite(time_tolerance_sec):
        raise ValueError(f"time_tolerance_sec must be finite >= 0, got {time_tolerance_sec!r}")
    if lot_sl_drift_tol < 0.0 or not math.isfinite(lot_sl_drift_tol):
        raise ValueError(f"lot_sl_drift_tol must be finite >= 0, got {lot_sl_drift_tol!r}")

    exp_list = [
        _normalize_parity_trade(t, role="expected_python_trades", idx=i)
        for i, t in enumerate(expected_python_trades)
    ]
    act_list = [
        _normalize_parity_trade(t, role="actual_mt5_trades", idx=i)
        for i, t in enumerate(actual_mt5_trades)
    ]
    bb_list = [dict(r) for r in (decision_blackbox or [])]

    # Build candidate 1-to-1 pairs sorted by (signal_id_mismatch, time_diff_sec, exp_idx, act_idx)
    candidate_pairs: list[tuple[int, float, int, int]] = []
    for ei, exp in enumerate(exp_list):
        for ai, act in enumerate(act_list):
            if exp["canonical_symbol"] != act["canonical_symbol"]:
                continue
            if exp["side"] != act["side"]:
                continue
            if exp["magic"] > 0 and act["magic"] > 0 and exp["magic"] != act["magic"]:
                continue
            dt = abs(act["utc_ts"] - exp["utc_ts"])
            if dt > time_tolerance_sec:
                continue
            sig_mismatch = 0 if (exp["signal_id"] and exp["signal_id"] == act["signal_id"]) else 1
            candidate_pairs.append((sig_mismatch, dt, ei, ai))

    candidate_pairs.sort()
    matched_exp: set[int] = set()
    matched_act: set[int] = set()
    events: list[dict[str, Any]] = []

    for _sig_m, dt, ei, ai in candidate_pairs:
        if ei in matched_exp or ai in matched_act:
            continue
        matched_exp.add(ei)
        matched_act.add(ai)

        exp = exp_list[ei]
        act = act_list[ai]
        sym = exp["canonical_symbol"]
        pt = point_size_for_symbol(sym)

        lot_drift_rel = 0.0
        if exp["lots"] is not None and exp["lots"] > 0.0 and act["lots"] is not None:
            lot_drift_rel = abs(act["lots"] - exp["lots"]) / exp["lots"]

        sl_drift_rel = 0.0
        if exp["sl_dist"] is not None and exp["sl_dist"] > 1e-12 and act["sl_dist"] is not None:
            sl_drift_rel = abs(act["sl_dist"] - exp["sl_dist"]) / exp["sl_dist"]

        # Realized friction checks (spread, adverse slippage, swap)
        friction_reasons: list[str] = []
        actual_spread = act["spread_pts"]
        if actual_spread is not None:
            if exp["spread_budget_pts"] is not None and exp["spread_budget_pts"] > 0.0:
                sp_cap = exp["spread_budget_pts"]
            elif exp["spread_pts"] is not None and exp["spread_pts"] > 0.0:
                sp_cap = exp["spread_pts"] * spread_budget_mult
            else:
                bench = benchmark_spread_for_symbol(sym)
                sp_cap = (bench * spread_budget_mult) if (bench is not None and bench > 0.0) else None
            if sp_cap is not None and actual_spread > sp_cap + 1e-9:
                friction_reasons.append(f"SPREAD_EXCEEDED:{actual_spread:.2f}>{sp_cap:.2f}pts")

        # Adverse slippage vs Python expected entry (or broker signal price)
        ref_entry = exp["entry_price"] if exp["entry_price"] is not None else act["signal_price"]
        adverse_slip_pts = act["adverse_slip_pts"]
        if ref_entry is not None and act["entry_price"] is not None and pt > 0.0:
            adverse_slip_pts = _side_to_sign(exp["side"]) * (act["entry_price"] - ref_entry) / pt

        slip_cap_pts = exp["slippage_budget_pts"] if exp["slippage_budget_pts"] is not None else max_slippage_budget_pts
        adverse_slip_r: float | None = None
        if adverse_slip_pts is not None:
            if adverse_slip_pts > slip_cap_pts + 1e-9:
                friction_reasons.append(f"SLIPPAGE_PTS_EXCEEDED:{adverse_slip_pts:.2f}>{slip_cap_pts:.2f}pts")
            if exp["sl_dist"] is not None and exp["sl_dist"] > 1e-12 and pt > 0.0:
                adverse_slip_r = (adverse_slip_pts * pt) / exp["sl_dist"]
                if adverse_slip_r > max_slippage_r_budget + 1e-9:
                    friction_reasons.append(f"SLIPPAGE_R_EXCEEDED:{adverse_slip_r:.3f}R>{max_slippage_r_budget:.3f}R")

        if act["swap_usd"] is not None and abs(act["swap_usd"]) > swap_tolerance_usd + 1e-9:
            friction_reasons.append(f"NONZERO_SWAP:{act['swap_usd']:.4f}USD")

        drift_reasons: list[str] = []
        if lot_drift_rel > lot_sl_drift_tol + 1e-12:
            drift_reasons.append(
                f"LOT_DRIFT:{lot_drift_rel * 100.0:.2f}%>{lot_sl_drift_tol * 100.0:.2f}% "
                f"(exp={exp['lots']}, act={act['lots']})"
            )
        if sl_drift_rel > lot_sl_drift_tol + 1e-12:
            drift_reasons.append(
                f"SL_DIST_DRIFT:{sl_drift_rel * 100.0:.2f}%>{lot_sl_drift_tol * 100.0:.2f}% "
                f"(exp={exp['sl_dist']}, act={act['sl_dist']})"
            )

        if drift_reasons:
            pclass = PARITY_LOT_OR_SL_DRIFT
            severity = "RED"
            escalation = "IMMEDIATE_FIX_REQUIRED"
            reasons = drift_reasons + friction_reasons
        elif friction_reasons:
            pclass = PARITY_EXECUTION_FRICTION_DRIFT
            severity = "RED" if any(r.startswith("NONZERO_SWAP") for r in friction_reasons) else "AMBER"
            escalation = "ROUTE_TO_TCA"
            reasons = friction_reasons
        else:
            pclass = PARITY_MATCH_CLEAN
            severity = "GREEN"
            escalation = "NONE"
            reasons = []

        events.append(
            {
                "parity_class": pclass,
                "severity": severity,
                "escalation": escalation,
                "is_technical_bug": pclass in TECHNICAL_BUG_CLASSES,
                "canonical_symbol": sym,
                "side": exp["side"],
                "magic": act["magic"] or exp["magic"],
                "signal_id": exp["signal_id"] or act["signal_id"],
                "position_id": act["position_id"],
                "expected_index": ei,
                "actual_index": ai,
                "expected_utc_ts": exp["utc_ts"],
                "actual_utc_ts": act["utc_ts"],
                "time_diff_sec": round(dt, 3),
                "lot_drift_rel": round(lot_drift_rel, 6),
                "sl_drift_rel": round(sl_drift_rel, 6),
                "max_lot_sl_drift_rel": round(max(lot_drift_rel, sl_drift_rel), 6),
                "adverse_slip_pts": round(float(adverse_slip_pts), 4) if adverse_slip_pts is not None else None,
                "adverse_slip_r": round(float(adverse_slip_r), 6) if adverse_slip_r is not None else None,
                "actual_spread_pts": actual_spread,
                "swap_usd": act["swap_usd"],
                "expected_gross_R": exp["gross_R"],
                "actual_gross_R": act["gross_R"],
                "reasons": reasons,
            }
        )

    # Unmatched actual MT5 fills -> BOT_BUG_GHOST_TRADE
    for ai, act in enumerate(act_list):
        if ai in matched_act:
            continue
        events.append(
            {
                "parity_class": PARITY_BOT_BUG_GHOST_TRADE,
                "severity": "RED",
                "escalation": "IMMEDIATE_FIX_REQUIRED",
                "is_technical_bug": True,
                "canonical_symbol": act["canonical_symbol"],
                "side": act["side"],
                "magic": act["magic"],
                "signal_id": act["signal_id"],
                "position_id": act["position_id"],
                "expected_index": None,
                "actual_index": ai,
                "expected_utc_ts": None,
                "actual_utc_ts": act["utc_ts"],
                "time_diff_sec": None,
                "lot_drift_rel": None,
                "sl_drift_rel": None,
                "max_lot_sl_drift_rel": None,
                "adverse_slip_pts": act["adverse_slip_pts"],
                "adverse_slip_r": None,
                "actual_spread_pts": act["spread_pts"],
                "swap_usd": act["swap_usd"],
                "expected_gross_R": None,
                "actual_gross_R": act["gross_R"],
                "reasons": ["MT5_FIRED_WITHOUT_PYTHON_SIGNAL"],
            }
        )

    # Unmatched expected Python signals -> LEGITIMATE_GUARD_BLOCK or BOT_BUG_MISSED_TRADE
    for ei, exp in enumerate(exp_list):
        if ei in matched_exp:
            continue
        guard_block = _find_matching_guard_block(exp, bb_list, time_tolerance_sec=time_tolerance_sec)
        if guard_block is not None:
            guard_dec = _normalize_guard_decision(guard_block.get("decision") or guard_block.get("event_type"))
            events.append(
                {
                    "parity_class": PARITY_LEGITIMATE_GUARD_BLOCK,
                    "severity": "INFO",
                    "escalation": "NONE",
                    "is_technical_bug": False,
                    "canonical_symbol": exp["canonical_symbol"],
                    "side": exp["side"],
                    "magic": exp["magic"],
                    "signal_id": exp["signal_id"] or str(guard_block.get("signal_id") or ""),
                    "position_id": "",
                    "expected_index": ei,
                    "actual_index": None,
                    "expected_utc_ts": exp["utc_ts"],
                    "actual_utc_ts": None,
                    "time_diff_sec": None,
                    "lot_drift_rel": None,
                    "sl_drift_rel": None,
                    "max_lot_sl_drift_rel": None,
                    "adverse_slip_pts": None,
                    "adverse_slip_r": None,
                    "actual_spread_pts": guard_block.get("spread_pts"),
                    "swap_usd": None,
                    "expected_gross_R": exp["gross_R"],
                    "actual_gross_R": None,
                    "guard_decision": guard_dec,
                    "guard_block_reason": str(guard_block.get("block_reason") or guard_dec),
                    "reasons": [f"LEGITIMATE_GUARD_BLOCK:{guard_dec}"],
                }
            )
        else:
            events.append(
                {
                    "parity_class": PARITY_BOT_BUG_MISSED_TRADE,
                    "severity": "RED",
                    "escalation": "IMMEDIATE_FIX_REQUIRED",
                    "is_technical_bug": True,
                    "canonical_symbol": exp["canonical_symbol"],
                    "side": exp["side"],
                    "magic": exp["magic"],
                    "signal_id": exp["signal_id"],
                    "position_id": "",
                    "expected_index": ei,
                    "actual_index": None,
                    "expected_utc_ts": exp["utc_ts"],
                    "actual_utc_ts": None,
                    "time_diff_sec": None,
                    "lot_drift_rel": None,
                    "sl_drift_rel": None,
                    "max_lot_sl_drift_rel": None,
                    "adverse_slip_pts": None,
                    "adverse_slip_r": None,
                    "actual_spread_pts": None,
                    "swap_usd": None,
                    "expected_gross_R": exp["gross_R"],
                    "actual_gross_R": None,
                    "reasons": ["PYTHON_SIGNALED_MT5_SILENT_NO_GUARD_BLOCK"],
                }
            )

    events.sort(
        key=lambda e: (
            e["expected_utc_ts"] if e["expected_utc_ts"] is not None else (e["actual_utc_ts"] or 0.0),
            e["canonical_symbol"],
            e["parity_class"],
        )
    )

    counts: dict[str, int] = {cls: 0 for cls in (*CORE_PARITY_CLASSES, PARITY_LEGITIMATE_GUARD_BLOCK)}
    for ev in events:
        counts[ev["parity_class"]] = counts.get(ev["parity_class"], 0) + 1

    technical_bug_count = (
        counts[PARITY_BOT_BUG_GHOST_TRADE]
        + counts[PARITY_BOT_BUG_MISSED_TRADE]
        + counts[PARITY_LOT_OR_SL_DRIFT]
    )
    friction_drift_count = counts[PARITY_EXECUTION_FRICTION_DRIFT]
    matched_total = len(matched_exp)
    actionable_expected = max(0, len(exp_list) - counts[PARITY_LEGITIMATE_GUARD_BLOCK])
    if actionable_expected > 0:
        match_rate = matched_total / actionable_expected
    else:
        match_rate = 1.0 if len(act_list) == 0 else 0.0

    if technical_bug_count > 0:
        overall_verdict = "RED_BOT_BUG_ESCALATION"
    elif friction_drift_count > 0:
        overall_verdict = "AMBER_ROUTE_TO_TCA"
    else:
        overall_verdict = "GREEN_PARITY_CLEAN"

    return {
        "schema": "naqex-live-parity-classification-v1",
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "verdict": overall_verdict,
        "counts": counts,
        "expected_count": len(exp_list),
        "actual_count": len(act_list),
        "matched_count": matched_total,
        "actionable_expected_count": actionable_expected,
        "trade_match_rate": round(float(match_rate), 6),
        "technical_bug_count": technical_bug_count,
        "friction_drift_count": friction_drift_count,
        "events": events,
    }


# ---------------------------------------------------------------------------
# 3. MT5 Strategy Tester Parity Gate (Exact v3.5 Formula)
# ---------------------------------------------------------------------------
def evaluate_tester_parity_gate(
    expected_python_trades: Sequence[Mapping[str, Any]],
    actual_mt5_trades: Sequence[Mapping[str, Any]],
    *,
    decision_blackbox: Sequence[Mapping[str, Any]] | None = None,
    bar_seconds: float = 60.0,
    max_bar_diff: float = 1.0,
    min_trade_match_rate: float = 0.98,
    max_ghost_trades: int = 0,
    max_lot_sl_drift: float = 0.02,
    max_gross_r_drift: float = 0.05,
    require_gross_r: bool = True,
) -> dict[str, Any]:
    """Evaluate the strict `v3.5` MT5 Strategy Tester Parity Gate before Demo/Live promotion.

    Exact `v3.5` pass invariants:
      - `trade_match_rate >= 0.98` within `<= 1` bar (`<= max_bar_diff * bar_seconds`)
      - `ghost_trades == 0`
      - `max_lot_sl_drift <= 0.02` (`<= 2%`)
      - `gross_r_drift <= 0.05` (`<= 5%`)
    """
    if bar_seconds <= 0.0 or not math.isfinite(bar_seconds):
        raise ValueError(f"bar_seconds must be finite > 0, got {bar_seconds!r}")
    if max_bar_diff < 0.0 or not math.isfinite(max_bar_diff):
        raise ValueError(f"max_bar_diff must be finite >= 0, got {max_bar_diff!r}")

    time_tol_sec = max_bar_diff * bar_seconds
    parity = classify_parity_events(
        expected_python_trades,
        actual_mt5_trades,
        decision_blackbox=decision_blackbox,
        time_tolerance_sec=time_tol_sec,
        lot_sl_drift_tol=max_lot_sl_drift,
    )

    n_expected = len(expected_python_trades)
    matched_events = [e for e in parity["events"] if e["expected_index"] is not None and e["actual_index"] is not None]
    n_matched = len(matched_events)
    ghost_trades = int(parity["counts"][PARITY_BOT_BUG_GHOST_TRADE])
    missed_trades = int(parity["counts"][PARITY_BOT_BUG_MISSED_TRADE])
    guard_blocks = int(parity["counts"][PARITY_LEGITIMATE_GUARD_BLOCK])

    trade_match_rate = (n_matched / n_expected) if n_expected > 0 else 0.0
    max_observed_lot_sl_drift = max(
        (float(e["max_lot_sl_drift_rel"]) for e in matched_events if e["max_lot_sl_drift_rel"] is not None),
        default=0.0,
    )
    max_observed_time_diff = max(
        (float(e["time_diff_sec"]) for e in matched_events if e["time_diff_sec"] is not None),
        default=0.0,
    )

    r_pairs = [
        (float(e["expected_gross_R"]), float(e["actual_gross_R"]))
        for e in matched_events
        if e["expected_gross_R"] is not None and e["actual_gross_R"] is not None
    ]
    missing_gross_r = (len(r_pairs) < n_matched) or (n_matched == 0)

    rel_total_gross_r_drift: float | None = None
    mean_abs_trade_gross_r_drift: float | None = None
    gross_r_drift: float | None = None
    if r_pairs and not missing_gross_r:
        exp_total = sum(p[0] for p in r_pairs)
        act_total = sum(p[1] for p in r_pairs)
        rel_total_gross_r_drift = abs(act_total - exp_total) / max(abs(exp_total), 1.0)
        mean_abs_trade_gross_r_drift = sum(abs(p[1] - p[0]) for p in r_pairs) / len(r_pairs)
        gross_r_drift = max(rel_total_gross_r_drift, mean_abs_trade_gross_r_drift)

    failures: list[str] = []
    if n_expected == 0:
        failures.append("NO_EXPECTED_TRADES")
    trade_match_ok = n_expected > 0 and trade_match_rate >= min_trade_match_rate - 1e-12
    if not trade_match_ok:
        failures.append(f"TRADE_MATCH_RATE_BELOW_GATE:{trade_match_rate:.4f}<{min_trade_match_rate:.4f}")

    ghost_ok = ghost_trades <= max_ghost_trades
    if not ghost_ok:
        failures.append(f"GHOST_TRADES_DETECTED:{ghost_trades}>{max_ghost_trades}")

    lot_sl_ok = n_matched > 0 and max_observed_lot_sl_drift <= max_lot_sl_drift + 1e-12
    if not lot_sl_ok:
        failures.append(f"LOT_SL_DRIFT_EXCEEDED:{max_observed_lot_sl_drift:.4f}>{max_lot_sl_drift:.4f}")

    if require_gross_r:
        gross_r_ok = (gross_r_drift is not None) and (gross_r_drift <= max_gross_r_drift + 1e-12)
        if gross_r_drift is None:
            failures.append("MISSING_GROSS_R_FOR_PARITY_GATE")
        elif not gross_r_ok:
            failures.append(f"GROSS_R_DRIFT_EXCEEDED:{gross_r_drift:.4f}>{max_gross_r_drift:.4f}")
    else:
        gross_r_ok = (gross_r_drift is None) or (gross_r_drift <= max_gross_r_drift + 1e-12)
        if not gross_r_ok and gross_r_drift is not None:
            failures.append(f"GROSS_R_DRIFT_EXCEEDED:{gross_r_drift:.4f}>{max_gross_r_drift:.4f}")

    passed = len(failures) == 0
    return {
        "schema": TESTER_GATE_SCHEMA,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "passed": passed,
        "verdict": "PASS" if passed else "FAIL",
        "metrics": {
            "expected_trades": n_expected,
            "actual_trades": len(actual_mt5_trades),
            "matched_trades": n_matched,
            "trade_match_rate": round(float(trade_match_rate), 6),
            "ghost_trades": ghost_trades,
            "missed_trades": missed_trades,
            "legitimate_guard_blocks": guard_blocks,
            "max_lot_sl_drift": round(float(max_observed_lot_sl_drift), 6),
            "gross_r_drift": round(float(gross_r_drift), 6) if gross_r_drift is not None else None,
            "rel_total_gross_r_drift": (
                round(float(rel_total_gross_r_drift), 6) if rel_total_gross_r_drift is not None else None
            ),
            "mean_abs_trade_gross_r_drift": (
                round(float(mean_abs_trade_gross_r_drift), 6) if mean_abs_trade_gross_r_drift is not None else None
            ),
            "max_time_diff_sec": round(float(max_observed_time_diff), 3),
            "bar_seconds": float(bar_seconds),
            "time_tolerance_sec": float(time_tol_sec),
        },
        "thresholds": {
            "min_trade_match_rate": float(min_trade_match_rate),
            "max_bar_diff": float(max_bar_diff),
            "max_ghost_trades": int(max_ghost_trades),
            "max_lot_sl_drift": float(max_lot_sl_drift),
            "max_gross_r_drift": float(max_gross_r_drift),
        },
        "checks": {
            "trade_match_rate_ok": trade_match_ok,
            "ghost_trades_ok": ghost_ok,
            "max_lot_sl_drift_ok": lot_sl_ok,
            "gross_r_drift_ok": gross_r_ok,
        },
        "failures": failures,
        "parity_report": parity,
    }


# ---------------------------------------------------------------------------
# 4. Trade Geometry (W1..L4 + Broker-Tape Excursions) & Anti-Overfit Loop
# ---------------------------------------------------------------------------
def analyze_trade_geometry_on_broker_tape(
    closed_trades: Sequence[Mapping[str, Any]],
    broker_tape_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    *,
    post_exit_horizon_sec: int = 14_400,
) -> dict[str, Any]:
    """Compute real `MFE_R`, `MAE_R`, `post_MFE_R` and `W1..L4` labels using TRUE broker tape."""
    tape_index: dict[str, Sequence[Mapping[str, Any]]] = {}
    if broker_tape_by_symbol:
        for raw_sym, seq in broker_tape_by_symbol.items():
            tape_index[normalize_symbol_alias(str(raw_sym))] = seq

    classified_rows: list[dict[str, Any]] = []
    skipped_open_count = 0

    for idx, trade in enumerate(closed_trades):
        exit_px = parse_optional_finite_float(
            trade.get("exit_price") if trade.get("exit_price") not in (None, "") else trade.get("close_price"),
            field_name=f"trade[{idx}].exit_price",
        )
        entry_px = parse_optional_finite_float(
            trade.get("entry_price") if trade.get("entry_price") not in (None, "") else trade.get("fill_price"),
            field_name=f"trade[{idx}].entry_price",
        )
        sl_px = parse_optional_finite_float(
            trade.get("sl_price") if trade.get("sl_price") not in (None, "") else trade.get("sl"),
            field_name=f"trade[{idx}].sl_price",
        )
        entry_ts = _parse_optional_utc_ts_sec(
            trade.get("entry_utc_ts") if trade.get("entry_utc_ts") not in (None, "") else trade.get("utc_ts")
        )
        exit_ts = _parse_optional_utc_ts_sec(
            trade.get("exit_utc_ts") if trade.get("exit_utc_ts") not in (None, "") else trade.get("close_time")
        )

        if exit_px is None or entry_px is None or entry_ts is None or exit_ts is None or exit_ts < entry_ts:
            skipped_open_count += 1
            continue

        raw_sym = str(trade.get("symbol") or trade.get("canonical_symbol") or "").strip()
        canon_sym = normalize_symbol_alias(raw_sym)
        side_str = _normalize_side(trade.get("side") or trade.get("direction"))
        side_sign = _side_to_sign(side_str)
        sl_dist = parse_optional_finite_float(trade.get("sl_dist"), field_name=f"trade[{idx}].sl_dist")
        if sl_dist is None and sl_px is not None and sl_px > 0.0:
            sl_dist = abs(entry_px - sl_px)
        if sl_dist is None or sl_dist <= 1e-12:
            skipped_open_count += 1
            continue

        reason = _normalize_exit_reason(trade.get("exit_reason") or trade.get("reason"))
        entry_ms = int(round(entry_ts * 1000.0))
        exit_ms = int(round(exit_ts * 1000.0))
        cutoff_ms = exit_ms + max(0, int(post_exit_horizon_sec)) * 1000

        net_r = parse_optional_finite_float(
            trade.get("net_R") if trade.get("net_R") not in (None, "") else trade.get("net_r"),
            field_name=f"trade[{idx}].net_R",
        )
        if net_r is None:
            net_r = side_sign * (exit_px - entry_px) / sl_dist

        tape_seq = tape_index.get(canon_sym, ())
        open_path_unknown = True
        post_path_unknown = True
        excursion_metrics: dict[str, Any]

        if tape_seq:
            times_ms, exec_px = extract_executable_price_path(
                tape_seq,
                side=side_sign,
                start_ts_ms=entry_ms - 60_000,
                end_ts_ms=cutoff_ms + 60_000,
            )
            if len(times_ms) > 0:
                in_trade_mask = (times_ms >= entry_ms) & (times_ms <= exit_ms)
                post_mask = (times_ms > exit_ms) & (times_ms <= cutoff_ms)
                open_path_unknown = not bool(in_trade_mask.any())
                post_path_unknown = not bool(post_mask.any())
                excursion_metrics = compute_trade_excursions(
                    times_ms,
                    exec_px,
                    entry=entry_ms,
                    exit_at=exit_ms,
                    entry_price=entry_px,
                    natural_units=sl_dist,
                    side=side_sign,
                    exit_price=exit_px,
                    cutoff=cutoff_ms,
                    stop_reason=reason,
                )
            else:
                excursion_metrics = _fallback_endpoint_excursions(net_r)
        else:
            excursion_metrics = _fallback_endpoint_excursions(net_r)

        family = trade.get("family")
        day_range_atr = parse_optional_finite_float(trade.get("day_range_ATR"), field_name="day_range_ATR")
        classifier_input = {
            "net_R": float(net_r),
            "MFE_R": float(excursion_metrics["MFE_R"]),
            "MAE_R": float(excursion_metrics["MAE_R"]),
            "profitable_fraction": float(excursion_metrics["profitable_fraction"]),
            "late_jump_share": float(excursion_metrics["late_jump_share"]),
            "post_MFE_R": float(excursion_metrics["post_MFE_R"]),
            "reason": reason,
            "open_path_unknown": open_path_unknown,
            "post_path_unknown": post_path_unknown,
            "family": family,
            "day_range_ATR": day_range_atr,
        }
        verdict = classify_trade_geometry(classifier_input)
        trade_key = str(trade.get("position_id") or trade.get("signal_id") or f"{canon_sym}_{entry_ms}_{idx}")
        classified_rows.append(
            {
                "trade_key": trade_key,
                "position_id": str(trade.get("position_id") or ""),
                "canonical_symbol": canon_sym,
                "side": side_str,
                "entry_utc_ts": entry_ts,
                "exit_utc_ts": exit_ts,
                "reason": reason,
                "family": family,
                "net_R": round(float(net_r), 6),
                "MFE_R": round(float(excursion_metrics["MFE_R"]), 6),
                "MAE_R": round(float(excursion_metrics["MAE_R"]), 6),
                "post_MFE_R": round(float(excursion_metrics["post_MFE_R"]), 6),
                "post_1R_at": excursion_metrics.get("post_1R_at"),
                "post_2R_at": excursion_metrics.get("post_2R_at"),
                "profitable_fraction": round(float(excursion_metrics["profitable_fraction"]), 4),
                "late_jump_share": round(float(excursion_metrics["late_jump_share"]), 4),
                "open_path_unknown": open_path_unknown,
                "post_path_unknown": post_path_unknown,
                "label": verdict["label"],
                "label_name": verdict["label_name"],
                "flags": verdict["flags"],
                "provisional": verdict["provisional"],
                "giveback_bucket": verdict["giveback_bucket"],
            }
        )

    summary = summarize_trade_geometry(classified_rows)
    conc = compute_geometry_concentration(classified_rows)
    return {
        "schema": "naqex-trade-geometry-forensics-v1",
        "closed_trades_analysed": len(classified_rows),
        "skipped_open_or_incomplete": skipped_open_count,
        "summary": summary,
        "concentration": conc,
        "trades": classified_rows,
    }


def _fallback_endpoint_excursions(net_r: float) -> dict[str, Any]:
    return {
        "MFE_R": max(0.0, float(net_r)),
        "MAE_R": max(0.0, float(-net_r)),
        "profitable_fraction": 1.0 if net_r > 0.0 else 0.0,
        "late_jump_share": 0.0,
        "post_MFE_R": 0.0,
        "post_1R_at": None,
        "post_2R_at": None,
    }


def _build_draft_hypothesis_card(
    *,
    loss_class: str,
    loss_count: int,
    loss_r: float,
    n_live: int,
    symbols: tuple[str, ...],
    timeframe: str,
    account_alias: str,
    period_label: str,
    n_trials_cumulative: int,
) -> dict[str, Any]:
    templates: dict[str, dict[str, Any]] = {
        "L1": {
            "title": "Volatility-Normalized Stop Buffer to Mitigate L1 Stop-Out Reversals",
            "counterparty": (
                "Liquidity sweepers and intraday stop-hunting order flow around tight mechanical stops "
                "prior to institutional session continuation"
            ),
            "rationale": (
                f"Live forensics observed {loss_count} L1 STOP_HUNTED_RIGHT_DIRECTION losses ({loss_r:.2f}R) "
                f"out of N_live={n_live} where executable broker Bid/Ask reached >=1.0R favorably after SL hit. "
                "Testing ATR/spread-aware stop placement on 7-year Dev tests whether counterparties trigger overly "
                "tight stops before directional continuation pays patient liquidity holders."
            ),
            "hypothesis_code": "L1_STOP_BUFFER",
        },
        "L2": {
            "title": "Structural Profit-Protection Exit Study for L2 Round-Trip Giveback",
            "counterparty": (
                "Mean-reversion flow fading extended intraday moves when breakout winners fail to lock "
                "structural excursion gains before session liquidity drains"
            ),
            "rationale": (
                f"Live forensics observed {loss_count} L2 ROUND_TRIP_GIVEBACK losses ({loss_r:.2f}R) "
                f"out of N_live={n_live} where trades reached MFE >= 0.8R before reversing to net <= 0R. "
                "Evaluating causal breakeven/trailing exit mechanics strictly on 7-year Dev Cluster A -> blind "
                "Cluster B determines whether giveback reduction improves net prop pass EV without cutting winners."
            ),
            "hypothesis_code": "L2_GIVEBACK_EXIT",
        },
        "L3": {
            "title": "Causal Exhaustion Admission Filter for L3 Late-Range Chasing Traps",
            "counterparty": (
                "Late retail breakout chasers providing exit liquidity to institutional profit-taking "
                "after >90% of daily ATR range has already been expended"
            ),
            "rationale": (
                f"Live forensics observed {loss_count} L3 EXHAUSTION_OR_CHASING_TRAP losses ({loss_r:.2f}R) "
                f"out of N_live={n_live} with MFE < 0.25R and expanded day_range_ATR > 0.90. "
                "Testing a strictly causal pre-entry range-exhaustion gate on 7-year Dev Cluster A -> blind "
                "Cluster B checks if avoiding late exhaustion entries raises cost-stressed Sharpe and pass EV."
            ),
            "hypothesis_code": "L3_EXHAUSTION_GATE",
        },
    }
    tpl = templates[loss_class]
    safe_period = re.sub(r"[^A-Za-z0-9_-]+", "_", period_label.strip()) or "WEEKLY"
    hyp_id = f"HYP_LIVE_{tpl['hypothesis_code']}_{safe_period}"
    universe = symbols if symbols else ("USDJPY", "GBPUSD", "EURJPY", "US100")

    card = propose_hypothesis(
        hypothesis_id=hyp_id,
        title=tpl["title"],
        asset_universe=universe,
        timeframe=timeframe,
        counterparty_mechanism=tpl["counterparty"],
        economic_rationale=tpl["rationale"],
        causal_invariants=(
            "Strictly causal bar-close signals with zero look-ahead or future-bar peeking",
            "Zero overnight swap (swap=0 intraday flat) and 2x execution cost stress survival",
            "Validated ONLY on 7-year Dev (2018-2024) Cluster A -> blind Cluster B with holdout_rows == 0",
            "NEVER auto-tuned on small live samples; requires Research Council Critic approval before promotion",
        ),
        n_trials_cumulative=max(1, int(n_trials_cumulative)),
        kill_criteria=KillCriteria(
            max_bh_q=0.10,
            min_dsr=0.50,
            min_cluster_b_sharpe=0.40,
            min_cost_breakeven_mult=2.00,
            min_trades_cluster_b=30,
        ),
    )
    validation_errors = card.validate()
    if validation_errors:
        raise ValueError(f"DRAFT_HYPOTHESIS_CARD_INVALID: {validation_errors}")

    return {
        "validation_tag": MUST_VALIDATE_TAG,
        "live_auto_tune_forbidden": True,
        "holdout_untouched_required": True,
        "source_geometry_class": loss_class,
        "source_geometry_name": GEOMETRY_LABELS[loss_class],
        "observed_loss_count": int(loss_count),
        "observed_loss_R": round(float(loss_r), 4),
        "n_live_observed": int(n_live),
        "account_alias": account_alias,
        "period_label": period_label,
        "hypothesis_card": card.to_dict(),
    }


def evaluate_anti_overfit_feedback(
    parity_report: Mapping[str, Any],
    geometry_report: Mapping[str, Any],
    *,
    account_alias: str = "DEMO_LIVE",
    period_label: str = "Weekly",
    timeframe: str = "M1",
    min_live_trades: int = ANTI_OVERFIT_MIN_LIVE_TRADES,
    recommended_live_trades: int = ANTI_OVERFIT_RECOMMENDED_LIVE_TRADES,
    min_pattern_count: int = 2,
    n_trials_cumulative: int = 1,
) -> dict[str, Any]:
    """Enforce the strict 2-lane Anti-Overfit Feedback Protocol.

    Lane 1 (Technical Bugs):
      - `BOT_BUG_GHOST_TRADE`, `BOT_BUG_MISSED_TRADE`, `LOT_OR_SL_DRIFT` -> `IMMEDIATE_FIX_REQUIRED`
        (NEVER gated on sample size!).
      - `EXECUTION_FRICTION_DRIFT` -> `ROUTE_TO_TCA`.
    Lane 2 (Strategy/Parameter Ideas from `L1/L2/L3` geometry):
      - HARD-LOCKED behind `N_live >= 30` (recommended `>= 50`).
      - When unlocked (`N_live >= 30`), emits draft `HypothesisCard` payloads tagged
        `MUST_VALIDATE_ON_7YR_DEV_BEFORE_CHANGE`. Auto-tuning live parameters is ALWAYS forbidden.
    """
    if isinstance(min_live_trades, bool) or not isinstance(min_live_trades, int):
        raise ValueError(
            f"INVALID_MIN_LIVE_TRADES: min_live_trades must be a strict positive int, got {min_live_trades!r}"
        )
    if min_live_trades < ANTI_OVERFIT_MIN_LIVE_TRADES:
        raise ValueError(
            f"ANTI_OVERFIT_FLOOR_VIOLATION: min_live_trades={min_live_trades} "
            f"< hard floor {ANTI_OVERFIT_MIN_LIVE_TRADES}"
        )
    if (
        isinstance(recommended_live_trades, bool)
        or not isinstance(recommended_live_trades, int)
        or recommended_live_trades < ANTI_OVERFIT_MIN_LIVE_TRADES
    ):
        raise ValueError(
            f"INVALID_RECOMMENDED_LIVE_TRADES: recommended_live_trades must be a strict int >= "
            f"{ANTI_OVERFIT_MIN_LIVE_TRADES}, got {recommended_live_trades!r}"
        )
    if isinstance(min_pattern_count, bool) or not isinstance(min_pattern_count, int) or min_pattern_count <= 0:
        raise ValueError(
            f"INVALID_MIN_PATTERN_COUNT: min_pattern_count must be a strict positive int, got {min_pattern_count!r}"
        )
    if (
        isinstance(n_trials_cumulative, bool)
        or not isinstance(n_trials_cumulative, int)
        or n_trials_cumulative <= 0
    ):
        raise ValueError(
            f"INVALID_N_TRIALS_CUMULATIVE: n_trials_cumulative must be a strict positive int, "
            f"got {n_trials_cumulative!r}"
        )
    eff_recommended = max(recommended_live_trades, min_live_trades)

    counts = parity_report.get("counts") or {}
    ghost_n = int(counts.get(PARITY_BOT_BUG_GHOST_TRADE, 0))
    missed_n = int(counts.get(PARITY_BOT_BUG_MISSED_TRADE, 0))
    drift_n = int(counts.get(PARITY_LOT_OR_SL_DRIFT, 0))
    friction_n = int(counts.get(PARITY_EXECUTION_FRICTION_DRIFT, 0))

    technical_escalations: list[dict[str, Any]] = []
    if ghost_n > 0:
        technical_escalations.append(
            {
                "parity_class": PARITY_BOT_BUG_GHOST_TRADE,
                "count": ghost_n,
                "status": "IMMEDIATE_FIX_REQUIRED",
                "action": "Halt EA / inspect ghost trigger source against Naqex_DecisionBlackbox immediately.",
            }
        )
    if missed_n > 0:
        technical_escalations.append(
            {
                "parity_class": PARITY_BOT_BUG_MISSED_TRADE,
                "count": missed_n,
                "status": "IMMEDIATE_FIX_REQUIRED",
                "action": "Inspect silent signal drop (no legitimate guard block logged) before next session.",
            }
        )
    if drift_n > 0:
        technical_escalations.append(
            {
                "parity_class": PARITY_LOT_OR_SL_DRIFT,
                "count": drift_n,
                "status": "IMMEDIATE_FIX_REQUIRED",
                "action": "Audit TICK_VALUE_LOSS / contract_size / stops rounding causing >5% lot or SL drift.",
            }
        )
    if friction_n > 0:
        technical_escalations.append(
            {
                "parity_class": PARITY_EXECUTION_FRICTION_DRIFT,
                "count": friction_n,
                "status": "ROUTE_TO_TCA",
                "action": "Route spread/slippage/swap overrun to TCA & broker execution quality review.",
            }
        )

    summary = geometry_report.get("summary") or {}
    n_live = int(summary.get("trades", 0))
    overlap_flags = summary.get("overlapping_loss_flags") or {}
    trades = geometry_report.get("trades") or []
    observed_symbols = tuple(
        sorted({str(t.get("canonical_symbol") or "") for t in trades if t.get("canonical_symbol")})
    )

    if n_live < min_live_trades:
        return {
            "schema": "naqex-anti-overfit-feedback-v1",
            "auto_tune_permitted": False,
            "technical_bug_status": "IMMEDIATE_FIX_REQUIRED" if (ghost_n + missed_n + drift_n) > 0 else "CLEAN",
            "technical_escalations": technical_escalations,
            "n_live": n_live,
            "min_live_trades_gate": int(min_live_trades),
            "recommended_live_trades": int(eff_recommended),
            "parameter_change_locked": True,
            "lock_status": "HARD_LOCKED_INSUFFICIENT_LIVE_SAMPLE",
            "remaining_trades_to_unlock": int(min_live_trades - n_live),
            "sample_confidence_tier": "LOCKED_BELOW_30",
            "draft_hypothesis_cards": [],
            "notice": (
                f"Strategy/parameter feedback HARD-LOCKED (N_live={n_live} < {min_live_trades}; "
                f"recommended >= {eff_recommended}). Collect {min_live_trades - n_live} more closed "
                "live trades before drafting any Research Council HypothesisCard."
            ),
        }

    draft_cards: list[dict[str, Any]] = []
    trial_counter = max(1, int(n_trials_cumulative))
    for loss_cls in ("L1", "L2", "L3"):
        info = overlap_flags.get(loss_cls) or {}
        cnt = int(info.get("count", 0))
        loss_r = float(info.get("loss_R", 0.0))
        if cnt >= min_pattern_count:
            draft_cards.append(
                _build_draft_hypothesis_card(
                    loss_class=loss_cls,
                    loss_count=cnt,
                    loss_r=loss_r,
                    n_live=n_live,
                    symbols=observed_symbols,
                    timeframe=timeframe,
                    account_alias=account_alias,
                    period_label=period_label,
                    n_trials_cumulative=trial_counter,
                )
            )
            trial_counter += 1

    tier = "RECOMMENDED_N50_PLUS" if n_live >= eff_recommended else "MINIMUM_N30_CAUTIOUS"
    return {
        "schema": "naqex-anti-overfit-feedback-v1",
        "auto_tune_permitted": False,
        "technical_bug_status": "IMMEDIATE_FIX_REQUIRED" if (ghost_n + missed_n + drift_n) > 0 else "CLEAN",
        "technical_escalations": technical_escalations,
        "n_live": n_live,
        "min_live_trades_gate": int(min_live_trades),
        "recommended_live_trades": int(eff_recommended),
        "parameter_change_locked": False,
        "lock_status": "UNLOCKED_DRAFT_HYPOTHESIS_ONLY",
        "remaining_trades_to_unlock": 0,
        "sample_confidence_tier": tier,
        "draft_hypothesis_cards": draft_cards,
        "notice": (
            f"N_live={n_live} reached research feedback gate ({tier}). Emitted {len(draft_cards)} draft "
            f"HypothesisCard(s) tagged {MUST_VALIDATE_TAG}. Direct live parameter tuning remains FORBIDDEN."
        ),
    }


def build_weekly_forensics_report(
    *,
    expected_python_trades: Sequence[Mapping[str, Any]],
    actual_mt5_trades: Sequence[Mapping[str, Any]],
    decision_blackbox: Sequence[Mapping[str, Any]] | None = None,
    broker_tape_by_symbol: Mapping[str, Sequence[Mapping[str, Any]]] | None = None,
    tca_report: Mapping[str, Any] | None = None,
    decay_report: Mapping[str, Any] | None = None,
    ops_report: Mapping[str, Any] | None = None,
    vol_ratio: float = 1.0,
    account_alias: str = "DEMO_PRIMARY",
    period_label: str = "Weekly Review",
    timeframe: str = "M1",
    post_exit_horizon_sec: int = 14_400,
    time_tolerance_sec: float = 60.0,
    lot_sl_drift_tol: float = 0.05,
    min_live_trades: int = ANTI_OVERFIT_MIN_LIVE_TRADES,
    n_trials_cumulative: int = 1,
    output_json: Path | str | None = None,
) -> dict[str, Any]:
    """Run full OPS-6 Weekly Forensics: Parity + W1..L4 Geometry + Postmortem + Anti-Overfit Loop."""
    parity_report = classify_parity_events(
        expected_python_trades,
        actual_mt5_trades,
        decision_blackbox=decision_blackbox,
        time_tolerance_sec=time_tolerance_sec,
        lot_sl_drift_tol=lot_sl_drift_tol,
    )
    geometry_report = analyze_trade_geometry_on_broker_tape(
        actual_mt5_trades,
        broker_tape_by_symbol=broker_tape_by_symbol,
        post_exit_horizon_sec=post_exit_horizon_sec,
    )

    # Wire into postmortem_gen.classify_discrepancy (respecting parity bugs / TCA friction!)
    eff_tca = dict(tca_report) if tca_report is not None else {"verdict": "GREEN", "flags": []}
    if parity_report["technical_bug_count"] > 0 and not str(eff_tca.get("verdict", "")).startswith("RED_"):
        eff_tca["verdict"] = "RED_PARITY_BOT_BUG"
        eff_tca["flags"] = list(eff_tca.get("flags") or []) + [
            f"OPS-6 Parity detected {parity_report['technical_bug_count']} technical bug(s) "
            f"(GHOST={parity_report['counts'][PARITY_BOT_BUG_GHOST_TRADE]}, "
            f"MISSED={parity_report['counts'][PARITY_BOT_BUG_MISSED_TRADE]}, "
            f"LOT_SL_DRIFT={parity_report['counts'][PARITY_LOT_OR_SL_DRIFT]})"
        ]
    elif parity_report["friction_drift_count"] > 0 and str(eff_tca.get("verdict", "GREEN")) == "GREEN":
        eff_tca["verdict"] = "AMBER_WATCH"
        eff_tca["flags"] = list(eff_tca.get("flags") or []) + [
            f"OPS-6 Parity routed {parity_report['friction_drift_count']} EXECUTION_FRICTION_DRIFT event(s) to TCA"
        ]

    eff_decay = dict(decay_report) if decay_report is not None else {"verdict": "GREEN_ON_TRACK", "reasons": []}
    eff_ops = dict(ops_report) if ops_report is not None else {"status": "OK", "alerts": []}

    discrepancy = classify_discrepancy(eff_tca, eff_decay, eff_ops, vol_ratio=vol_ratio)
    feedback = evaluate_anti_overfit_feedback(
        parity_report,
        geometry_report,
        account_alias=account_alias,
        period_label=period_label,
        timeframe=timeframe,
        min_live_trades=min_live_trades,
        n_trials_cumulative=n_trials_cumulative,
    )

    report: dict[str, Any] = {
        "schema": WEEKLY_FORENSICS_SCHEMA,
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_alias": account_alias,
        "period_label": period_label,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "parity_report": parity_report,
        "geometry_report": geometry_report,
        "discrepancy_diagnosis": discrepancy,
        "feedback_protocol": feedback,
    }
    if output_json is not None:
        receipt = write_atomic_sha256_json(output_json, report)
        report["report_sha256"] = receipt["report_sha256"]
    return report


def render_weekly_forensics_markdown(report: Mapping[str, Any]) -> str:
    """Render concise Vietnamese/English Weekly Forensics Markdown (zero bare USD signs, LF-only)."""
    parity = report["parity_report"]
    pcounts = parity["counts"]
    geom = report["geometry_report"]["summary"]
    diag = report["discrepancy_diagnosis"]
    fb = report["feedback_protocol"]

    sev_dot = {"RED": "🔴", "AMBER": "🟡", "GREEN": "🟢"}.get(str(diag.get("severity", "GREEN")), "🟢")
    lines = [
        f"# Weekly Live Parity & Trade Geometry Forensics — {report['account_alias']} ({report['period_label']})",
        "",
        f"- **Generated UTC:** `{report['generated_utc']}`",
        f"- **Discrepancy Classification:** {sev_dot} **`{diag['classification']}`** (`{diag['severity']}`)",
        (
            f"- **Parity Verdict:** `{parity['verdict']}` "
            f"(match_rate=`{parity['trade_match_rate']:.2%}`, bugs=`{parity['technical_bug_count']}`)"
        ),
        (
            f"- **Feedback Gate:** `{fb['lock_status']}` "
            f"(`N_live={fb['n_live']}`, `auto_tune_permitted={fb['auto_tune_permitted']}`)"
        ),
        "",
        "## 1. Python-vs-MT5 1-to-1 Parity Breakdown",
        "",
        f"- 🟢 `MATCH_CLEAN`: {pcounts.get(PARITY_MATCH_CLEAN, 0)}",
        f"- 🔴 `BOT_BUG_GHOST_TRADE`: {pcounts.get(PARITY_BOT_BUG_GHOST_TRADE, 0)}",
        f"- 🔴 `BOT_BUG_MISSED_TRADE`: {pcounts.get(PARITY_BOT_BUG_MISSED_TRADE, 0)}",
        f"- 🔴 `LOT_OR_SL_DRIFT`: {pcounts.get(PARITY_LOT_OR_SL_DRIFT, 0)}",
        f"- 🟡 `EXECUTION_FRICTION_DRIFT`: {pcounts.get(PARITY_EXECUTION_FRICTION_DRIFT, 0)}",
        f"- 🟢 `LEGITIMATE_GUARD_BLOCK`: {pcounts.get(PARITY_LEGITIMATE_GUARD_BLOCK, 0)}",
        "",
        "## 2. Trade Geometry (`W1..L4`, Real Broker Tape Excursions)",
        "",
        (
            f"- Closed trades analysed: `{geom.get('trades', 0)}` "
            f"(provisional=`{geom.get('provisional', 0)}`, W1_share=`{geom.get('W1_share', 0.0):.2%}`)"
        ),
    ]
    for grp in geom.get("groups") or []:
        pct_str = f"{grp['pct']:.1f}%" if grp.get("pct") is not None else "N/A"
        lines.append(
            f"- `{grp['label']}` ({grp['name']}): count={grp['count']} ({pct_str}), "
            f"net_R={grp['net_R']:.2f}R, provisional={grp['provisional']}"
        )

    lines += ["", "## 3. Anti-Overfit Feedback & Actions", ""]
    if fb["technical_escalations"]:
        for esc in fb["technical_escalations"]:
            lines.append(f"- [{esc['status']}] `{esc['parity_class']}` (count={esc['count']}): {esc['action']}")
    else:
        lines.append("- 🟢 Zero technical parity bugs detected.")

    lines.append(f"- {fb['notice']}")
    for card_wrap in fb.get("draft_hypothesis_cards") or []:
        hc = card_wrap["hypothesis_card"]
        lines.append(
            f"- Draft `{hc['hypothesis_id']}` ({card_wrap['source_geometry_class']}) — `{card_wrap['validation_tag']}`"
        )
    lines.append("")
    return "\n".join(lines)


__all__ = [
    "ANTI_OVERFIT_MIN_LIVE_TRADES",
    "ANTI_OVERFIT_RECOMMENDED_LIVE_TRADES",
    "CORE_PARITY_CLASSES",
    "LEGITIMATE_GUARD_BLOCK_DECISIONS",
    "MUST_VALIDATE_TAG",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PARITY_BOT_BUG_GHOST_TRADE",
    "PARITY_BOT_BUG_MISSED_TRADE",
    "PARITY_EXECUTION_FRICTION_DRIFT",
    "PARITY_LEGITIMATE_GUARD_BLOCK",
    "PARITY_LOT_OR_SL_DRIFT",
    "PARITY_MATCH_CLEAN",
    "TECHNICAL_BUG_CLASSES",
    "TESTER_GATE_SCHEMA",
    "WEEKLY_FORENSICS_SCHEMA",
    "aggregate_mt5_deals_by_position",
    "analyze_trade_geometry_on_broker_tape",
    "build_weekly_forensics_report",
    "classify_parity_events",
    "evaluate_anti_overfit_feedback",
    "evaluate_tester_parity_gate",
    "is_legitimate_guard_block",
    "load_decision_blackbox_jsonl",
    "load_exec_audit_records",
    "load_v103_shadow_csv",
    "render_weekly_forensics_markdown",
]
