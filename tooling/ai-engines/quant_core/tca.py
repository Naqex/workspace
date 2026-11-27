"""Single Canonical Fail-Closed TCA Parser, Markout Curve Engine & Post-Reconcile Gate.

Provides the unified Transaction Cost Analysis (TCA) contract across Naqex `quant_core`
and `quant_factory` (ZERO `scipy` imports, ZERO `assert` guards, strictly read-only):

  1. `parse_exec_audit_row()` & `load_exec_audit_csv()`:
     - Preserves blank/missing `swap_usd` (and `pnl_usd`, `commission_usd`) as `None`
       (NEVER silently coerces `""` -> `0.0`), preserving statement-join enrichment.
     - Fails closed (`ValueError`) immediately on `NaN`, `Inf`, `bool`, or malformed numbers.
  2. `enrich_audit_rows_with_statement()`:
     - Deterministic join enrichment from broker statement rows (`deal_id` / `ticket` /
       `order_id` / `position_id`) before final TCA validation.
  3. `validate_tca_post_reconcile()`:
     - Post-reconciliation fail-closed gate raising `ValueError` if ANY closed trade / fill
       still has `swap_usd is None`, non-finite `swap_usd` (or numeric fields),
       `abs(swap_usd) > 0` (when `require_zero_swap=True`), or status `FILL_UNRESOLVED`.
  4. `compute_markout_curve()`:
     - Strictly causal signed post-fill markout in bps and price units relative to arrival
       midprice at `+1s`, `+10s`, `+60s`, and `+5m` (`+300s`) using `asof`/next-quote lookup
       (`quote_ts <= fill_ts` for arrival mid; `quote_ts >= fill_ts + h` for horizon `+h`).
     - Returns `None` whenever arrival or horizon quotes are unavailable (NEVER fabricates).
     - Flags adverse selection whenever mean post-fill markout is negative.
  5. `write_atomic_sha256_json()`:
     - Atomic temp-file + `fsync` + `os.replace` JSON writer with embedded canonical SHA-256.
"""

from __future__ import annotations

import bisect
import csv
import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from pathlib import Path
from typing import Any

import numpy as np

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

DEFAULT_MARKOUT_HORIZONS_SEC: tuple[int, ...] = (1, 10, 60, 300)

# Benchmark median spreads (in broker points) from verified FTMO Demo & Dukascopy M1 snapshots (all 28 symbols)
BENCHMARK_SPREAD_PTS: dict[str, float] = {
    "USDJPY": 7.0,
    "GBPUSD": 6.0,
    "EURUSD": 4.0,
    "EURJPY": 14.0,
    "GBPJPY": 16.0,
    "AUDUSD": 7.0,
    "USDCAD": 9.0,
    "USDCHF": 8.0,
    "NZDUSD": 10.0,
    "AUDJPY": 14.0,
    "CADJPY": 16.0,
    "CHFJPY": 18.0,
    "NZDJPY": 18.0,
    "EURGBP": 8.0,
    "EURAUD": 16.0,
    "GBPAUD": 22.0,
    "EURCAD": 15.0,
    "XAUUSD": 28.0,
    "XAGUSD": 25.0,
    "USOIL": 35.0,
    "USOIL.cash": 35.0,
    "UKOIL": 35.0,
    "UKOIL.cash": 35.0,
    "US100": 20.0,
    "US100.cash": 20.0,
    "US500": 6.0,
    "US500.cash": 6.0,
    "US30": 18.0,
    "US30.cash": 18.0,
    "GER40": 15.0,
    "GER40.cash": 15.0,
    "UK100": 12.0,
    "UK100.cash": 12.0,
    "JP225": 700.0,
    "JP225.cash": 700.0,
    "BTCUSD": 2500.0,
}

POINT_SIZES: dict[str, float] = {
    "USDJPY": 0.001,
    "EURJPY": 0.001,
    "GBPJPY": 0.001,
    "AUDJPY": 0.001,
    "CADJPY": 0.001,
    "CHFJPY": 0.001,
    "NZDJPY": 0.001,
    "GBPUSD": 0.00001,
    "EURUSD": 0.00001,
    "AUDUSD": 0.00001,
    "USDCAD": 0.00001,
    "USDCHF": 0.00001,
    "NZDUSD": 0.00001,
    "EURGBP": 0.00001,
    "EURAUD": 0.00001,
    "GBPAUD": 0.00001,
    "EURCAD": 0.00001,
    "XAUUSD": 0.01,
    "XAGUSD": 0.001,
    "USOIL": 0.001,
    "USOIL.cash": 0.001,
    "UKOIL": 0.001,
    "UKOIL.cash": 0.001,
    "US100": 0.01,
    "US100.cash": 0.01,
    "US500": 0.01,
    "US500.cash": 0.01,
    "US30": 0.01,
    "US30.cash": 0.01,
    "GER40": 0.01,
    "GER40.cash": 0.01,
    "UK100": 0.01,
    "UK100.cash": 0.01,
    "JP225": 0.01,
    "JP225.cash": 0.01,
    "BTCUSD": 0.01,
}

ENTRY_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "ENTRY",
        "ORDER_FILL",
        "ORDER_FILL_RECONCILED",
        "ENTRY_FILLED",
        "PARTIAL_ENTRY",
    }
)

EXIT_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "EXIT",
        "ORDER_CLOSE",
        "CLOSE",
        "POSITION_CLOSE",
        "EXIT_FILLED",
        "PARTIAL_EXIT",
        "SL_HIT",
        "TP_HIT",
        "TIME_EXIT",
        "PRE_FLATTEN_EXIT",
    }
)

SINGLE_ROW_FILL_EVENT_TYPES: frozenset[str] = frozenset(
    {
        "ORDER_FILL",
        "ORDER_FILL_RECONCILED",
    }
)

VALID_FILL_EVENT_TYPES: frozenset[str] = ENTRY_EVENT_TYPES | EXIT_EVENT_TYPES

NON_FILL_EVENT_TYPES: frozenset[str] = frozenset(
    {
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
    }
)

UNRESOLVED_EVENT_TYPES: frozenset[str] = frozenset({"FILL_UNRESOLVED"})

_INDEX_METAL_ALIAS_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"^(?:US100|NAS100|USTEC|NDX100|NDX)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "US100"),
    (re.compile(r"^(?:US500|SPX500|SP500|SPX)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "US500"),
    (re.compile(r"^(?:US30|DJ30|WS30)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "US30"),
    (re.compile(r"^(?:GER40|DE40|DAX40|DAX)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "GER40"),
    (re.compile(r"^(?:UK100|FTSE100|FTSE)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "UK100"),
    (re.compile(r"^(?:JP225|JPN225|NIKKEI225|NI225)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "JP225"),
    (re.compile(r"^(?:XAUUSD|GOLD)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "XAUUSD"),
    (re.compile(r"^(?:XAGUSD|SILVER)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "XAGUSD"),
    (re.compile(r"^(?:USOIL|WTI|XTIUSD|LIGHTCMDUSD)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "USOIL"),
    (re.compile(r"^(?:UKOIL|BRENT|XBRUSD|BRENTCMDUSD)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "UKOIL"),
    (re.compile(r"^(?:BTCUSD)(?:[^A-Z0-9].*|[a-z].*|$)", re.I), "BTCUSD"),
)
_FX6_SUFFIX_RE = re.compile(r"^([A-Za-z]{6})(?:[\._\-\+\#].*|[a-z]{1,4})?$")
_TAG_ID_RE = re.compile(r"\b(deal|ord|tk|pos|intent|magic)=([A-Za-z0-9_-]+)", re.IGNORECASE)

_NUMERIC_AUDIT_FIELDS: tuple[str, ...] = (
    "signal_price",
    "fill_price",
    "sl_price",
    "lots",
    "spread_pts",
    "latency_ms",
    "pnl_usd",
    "swap_usd",
    "commission_usd",
    "pre_spread_pts",
    "pre_spread_bps",
    "adverse_slip_pts",
    "adverse_slip_bps",
    "commission_bps",
)


# ---------------------------------------------------------------------------
# Symbol Normalization & Point Sizing
# ---------------------------------------------------------------------------
def normalize_symbol_alias(symbol: str) -> str:
    """Normalize broker-specific suffixes and index aliases to canonical keys."""
    s = str(symbol or "").strip()
    if not s:
        return ""
    for rx, canonical in _INDEX_METAL_ALIAS_RULES:
        if rx.match(s):
            return canonical
    m = _FX6_SUFFIX_RE.match(s)
    if m:
        return m.group(1).upper()
    head = re.split(r"[\._\-\+\#]", s, maxsplit=1)[0].strip()
    if len(head) >= 6 and head[:6].isalpha():
        return head[:6].upper()
    return head.upper()


def point_size_for_symbol(symbol: str) -> float:
    """Return broker point size with suffix/alias normalization."""
    raw = str(symbol or "").strip()
    if raw in POINT_SIZES:
        return POINT_SIZES[raw]
    canon = normalize_symbol_alias(raw)
    if canon in POINT_SIZES:
        return POINT_SIZES[canon]
    if len(canon) == 6 and canon.endswith("JPY"):
        return 0.001
    if canon.startswith("XAU"):
        return 0.01
    return 0.00001


def benchmark_spread_for_symbol(symbol: str) -> float | None:
    """Return benchmark median spread in broker points using canonical alias normalization."""
    raw = str(symbol or "").strip()
    if raw in BENCHMARK_SPREAD_PTS:
        return BENCHMARK_SPREAD_PTS[raw]
    canon = normalize_symbol_alias(raw)
    return BENCHMARK_SPREAD_PTS.get(canon)


# ---------------------------------------------------------------------------
# Strict Finite Parsing (NEVER coerces blank "" to 0.0; rejects NaN/Inf/bool)
# ---------------------------------------------------------------------------
def parse_optional_finite_float(raw: Any, *, field_name: str = "value") -> float | None:
    """Parse an optional finite float. Blank string / `None` -> `None`. Rejects `NaN`/`Inf`/`bool`."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{field_name} must be a finite number, not bool: {raw!r}")
    if isinstance(raw, (int, float)):
        val = float(raw)
        if not math.isfinite(val):
            raise ValueError(f"{field_name} must be finite (NaN/Inf forbidden), got {raw!r}")
        return val
    if isinstance(raw, str):
        cleaned = raw.replace("\xa0", "").replace(" ", "").strip()
        if cleaned == "":
            return None
        try:
            val = float(cleaned)
        except ValueError as exc:
            raise ValueError(f"{field_name} is not a valid finite float: {raw!r}") from exc
        if not math.isfinite(val):
            raise ValueError(f"{field_name} must be finite (NaN/Inf forbidden), got {raw!r}")
        return val
    raise ValueError(f"{field_name} has unsupported type {type(raw).__name__}: {raw!r}")


def parse_required_finite_float(raw: Any, *, field_name: str = "value") -> float:
    """Parse a required finite float (rejects `None`, blank `""`, `NaN`, `Inf`, `bool`)."""
    val = parse_optional_finite_float(raw, field_name=field_name)
    if val is None:
        raise ValueError(f"{field_name} is required and cannot be blank or None")
    return val


def parse_optional_strict_int(raw: Any, *, field_name: str = "value") -> int | None:
    """Parse an optional integer (rejects `bool`, `NaN`, `Inf`, and non-integer floats)."""
    if raw is None:
        return None
    if isinstance(raw, bool):
        raise ValueError(f"{field_name} must be an integer, not bool: {raw!r}")
    if isinstance(raw, int):
        return raw
    fval = parse_optional_finite_float(raw, field_name=field_name)
    if fval is None:
        return None
    ival = int(fval)
    if float(ival) != fval:
        raise ValueError(f"{field_name} must be an exact integer, got {raw!r}")
    return ival


def parse_required_strict_int(raw: Any, *, field_name: str = "value") -> int:
    """Parse a required integer."""
    ival = parse_optional_strict_int(raw, field_name=field_name)
    if ival is None:
        raise ValueError(f"{field_name} is required and cannot be blank or None")
    return ival


def extract_comment_tags(comment: str) -> dict[str, str]:
    """Extract key=value telemetry tags (`deal=`, `ord=`, `tk=`, `pos=`, `intent=`, `magic=`)."""
    out: dict[str, str] = {}
    for k, v in _TAG_ID_RE.findall(comment or ""):
        out[k.lower()] = v.strip()
    return out


def is_unresolved_record(record: Mapping[str, Any]) -> bool:
    """Return True if a TCA/audit record carries a `FILL_UNRESOLVED` event, status, or comment."""
    ev = str(record.get("event_type") or "").strip().upper()
    st = str(record.get("status") or "").strip().upper()
    cmt = str(record.get("comment") or "").strip().upper()
    return ev in UNRESOLVED_EVENT_TYPES or st in UNRESOLVED_EVENT_TYPES or "FILL_UNRESOLVED" in cmt


# ---------------------------------------------------------------------------
# Canonical Audit CSV Row Parser (P0-7 Safe: blank swap_usd -> None)
# ---------------------------------------------------------------------------
def parse_exec_audit_row(
    raw: Mapping[str, Any],
    *,
    require_core_fields: bool = True,
) -> dict[str, Any]:
    """Parse a single `naqex_exec_audit.csv` row preserving `swap_usd: float | None`.

    CRITICAL P0-7 invariant:
      - Empty/missing `swap_usd` (and `pnl_usd`, `commission_usd`) MUST parse as `None`
        so downstream broker statement enrichment can populate them.
      - Non-finite (`NaN`/`Inf`) or boolean values fail closed immediately with `ValueError`.
    """
    event_type = str(raw.get("event_type") or "").strip().upper()
    status_raw = str(raw.get("status") or "").strip().upper()
    comment = str(raw.get("comment") or "").strip()
    tags = extract_comment_tags(comment)

    utc_ts = parse_optional_strict_int(raw.get("utc_ts"), field_name="utc_ts")
    if utc_ts is None:
        if require_core_fields:
            raise ValueError("utc_ts is required in exec audit row")
        utc_ts = 0
    if utc_ts < 0:
        raise ValueError(f"utc_ts must be non-negative, got {utc_ts}")

    magic = parse_optional_strict_int(raw.get("magic"), field_name="magic")
    if magic is None and "magic" in tags:
        magic = parse_optional_strict_int(tags["magic"], field_name="magic")
    magic_int = 0 if magic is None else magic

    symbol = str(raw.get("symbol") or "").strip()
    if require_core_fields and not symbol:
        raise ValueError("symbol is required in exec audit row")

    side = str(raw.get("deal_side") or raw.get("exec_side") or raw.get("side") or "").strip().upper()
    position_side = str(raw.get("position_side") or "").strip().upper()

    signal_price = parse_optional_finite_float(raw.get("signal_price"), field_name="signal_price")
    fill_price = parse_optional_finite_float(raw.get("fill_price"), field_name="fill_price")
    sl_price = parse_optional_finite_float(raw.get("sl_price"), field_name="sl_price")
    lots = parse_optional_finite_float(raw.get("lots") if "lots" in raw else raw.get("volume"), field_name="lots")
    spread_pts = parse_optional_finite_float(raw.get("spread_pts"), field_name="spread_pts")
    latency_ms = parse_optional_finite_float(raw.get("latency_ms"), field_name="latency_ms")
    retcode = parse_optional_strict_int(raw.get("retcode"), field_name="retcode")

    is_unresolved = (
        event_type in UNRESOLVED_EVENT_TYPES
        or status_raw in UNRESOLVED_EVENT_TYPES
        or "FILL_UNRESOLVED" in comment.upper()
    )
    if require_core_fields and not is_unresolved and event_type in VALID_FILL_EVENT_TYPES:
        if signal_price is None:
            raise ValueError("signal_price is required for executed fill row")
        if fill_price is None:
            raise ValueError("fill_price is required for executed fill row")

    # P0-7 CRITICAL: NEVER silently coerce blank "" -> 0.0! Preserve None for enrichment.
    swap_usd = parse_optional_finite_float(raw.get("swap_usd"), field_name="swap_usd")
    pnl_usd = parse_optional_finite_float(raw.get("pnl_usd"), field_name="pnl_usd")
    commission_usd = parse_optional_finite_float(raw.get("commission_usd"), field_name="commission_usd")
    account_login = parse_optional_strict_int(raw.get("account_login"), field_name="account_login")

    deal_id = str(raw.get("deal_id") or tags.get("deal") or "").strip()
    order_id = str(raw.get("order_id") or tags.get("ord") or "").strip()
    position_id = str(raw.get("position_id") or tags.get("pos") or "").strip()
    ticket = str(raw.get("ticket") or tags.get("tk") or deal_id or order_id or "").strip()
    intent_id = str(raw.get("intent_id") or tags.get("intent") or "").strip()
    engine_id = str(raw.get("engine_id") or "").strip()

    parsed: dict[str, Any] = {
        "utc_ts": utc_ts,
        "magic": magic_int,
        "engine_id": engine_id,
        "symbol": symbol,
        "canonical_symbol": normalize_symbol_alias(symbol),
        "side": side,
        "position_side": position_side,
        "event_type": event_type,
        "status": status_raw or ("FILL_UNRESOLVED" if is_unresolved else ""),
        "signal_price": 0.0 if signal_price is None else signal_price,
        "fill_price": 0.0 if fill_price is None else fill_price,
        "sl_price": 0.0 if sl_price is None else sl_price,
        "lots": 0.0 if lots is None else lots,
        "spread_pts": 0.0 if spread_pts is None else spread_pts,
        "latency_ms": 0.0 if latency_ms is None else latency_ms,
        "retcode": 0 if retcode is None else retcode,
        "pnl_usd": pnl_usd,
        "swap_usd": swap_usd,
        "commission_usd": commission_usd,
        "account_login": account_login,
        "deal_id": deal_id,
        "order_id": order_id,
        "position_id": position_id,
        "ticket": ticket,
        "intent_id": intent_id,
        "comment": comment,
    }
    return parsed


def load_exec_audit_csv(csv_path: Path | str) -> list[dict[str, Any]]:
    """Load `naqex_exec_audit.csv` through canonical `parse_exec_audit_row()` (blank swap_usd -> None)."""
    path = Path(csv_path)
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for line_no, raw in enumerate(reader, start=2):
            if not raw or all(str(v or "").strip() == "" for v in raw.values()):
                continue
            try:
                rows.append(parse_exec_audit_row(raw, require_core_fields=True))
            except ValueError as exc:
                raise ValueError(f"{path.name}:{line_no}: {exc}") from exc
    return rows


# ---------------------------------------------------------------------------
# Statement Enrichment Helper (P0-7 flow: load -> enrich -> validate)
# ---------------------------------------------------------------------------
def enrich_audit_rows_with_statement(
    audit_rows: Sequence[Mapping[str, Any]],
    statement_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Enrich blank `swap_usd`/`pnl_usd`/`commission_usd` on audit rows from broker statement rows."""
    by_deal: dict[str, dict[str, Any]] = {}
    by_ticket: dict[str, dict[str, Any]] = {}
    by_order: dict[str, dict[str, Any]] = {}
    by_pos: dict[str, list[dict[str, Any]]] = {}

    for raw_sr in statement_rows:
        sr = dict(raw_sr)
        deal_id = str(sr.get("deal_id") or sr.get("deal") or "").strip()
        ticket = str(sr.get("ticket") or deal_id or "").strip()
        order_id = str(sr.get("order_id") or sr.get("order") or "").strip()
        pos_id = str(sr.get("position_id") or sr.get("position") or "").strip()
        if deal_id:
            by_deal[deal_id] = sr
        if ticket:
            by_ticket[ticket] = sr
        if order_id:
            by_order[order_id] = sr
        if pos_id:
            by_pos.setdefault(pos_id, []).append(sr)

    enriched: list[dict[str, Any]] = []
    matched = 0
    unmatched = 0
    swap_enriched = 0
    pnl_enriched = 0

    for raw_ar in audit_rows:
        row = dict(raw_ar)
        ev = str(row.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES or is_unresolved_record(row):
            enriched.append(row)
            continue

        is_exit = ev in EXIT_EVENT_TYPES or str(row.get("leg") or "").strip().upper() == "EXIT"
        deal_id = str(row.get("deal_id") or "").strip()
        ticket = str(row.get("ticket") or "").strip()
        order_id = str(row.get("order_id") or "").strip()
        pos_id = str(row.get("position_id") or "").strip()

        sr_match: dict[str, Any] | None = None
        if deal_id and deal_id in by_deal:
            sr_match = by_deal[deal_id]
        elif ticket and ticket in by_ticket:
            sr_match = by_ticket[ticket]
        elif order_id and order_id in by_order:
            sr_match = by_order[order_id]
        elif pos_id and pos_id in by_pos:
            cands = by_pos[pos_id]
            sr_match = cands[-1] if is_exit else cands[0]

        if sr_match is not None:
            matched += 1
            stmt_swap = parse_optional_finite_float(
                sr_match.get("swap_usd") if "swap_usd" in sr_match else sr_match.get("swap"),
                field_name="statement.swap_usd",
            )
            stmt_pnl = parse_optional_finite_float(
                sr_match.get("pnl_usd") if "pnl_usd" in sr_match else sr_match.get("profit"),
                field_name="statement.pnl_usd",
            )
            stmt_comm = parse_optional_finite_float(
                sr_match.get("commission_usd") if "commission_usd" in sr_match else sr_match.get("commission"),
                field_name="statement.commission_usd",
            )
            if row.get("swap_usd") is None and stmt_swap is not None:
                row["swap_usd"] = stmt_swap
                swap_enriched += 1
            if row.get("pnl_usd") is None and stmt_pnl is not None:
                row["pnl_usd"] = stmt_pnl
                pnl_enriched += 1
            if row.get("commission_usd") is None and stmt_comm is not None:
                row["commission_usd"] = stmt_comm
        else:
            unmatched += 1

        enriched.append(row)

    stats = {
        "matched_rows": matched,
        "unmatched_rows": unmatched,
        "swap_enriched_count": swap_enriched,
        "pnl_enriched_count": pnl_enriched,
    }
    return enriched, stats


# ---------------------------------------------------------------------------
# Post-Reconciliation Fail-Closed Gate
# ---------------------------------------------------------------------------
def _requires_resolved_swap(record: Mapping[str, Any], *, check_entries: bool = True) -> bool:
    ev = str(record.get("event_type") or "").strip().upper()
    leg = str(record.get("leg") or "").strip().upper()
    if ev in NON_FILL_EVENT_TYPES:
        return False
    if record.get("is_closed") is True or ev in EXIT_EVENT_TYPES or leg == "EXIT":
        return True
    if ev in SINGLE_ROW_FILL_EVENT_TYPES or (ev == "" and leg != "ENTRY"):
        return True
    if ev in ENTRY_EVENT_TYPES or leg == "ENTRY":
        return check_entries
    # Any unrecognized/unknown event_type MUST fail closed (require resolved swap_usd)
    return True


def validate_tca_post_reconcile(
    records: Iterable[Mapping[str, Any]],
    *,
    require_zero_swap: bool = True,
    swap_tolerance_usd: float = 0.0,
    check_entries_for_missing_swap: bool = True,
) -> dict[str, Any]:
    """Fail-closed post-reconciliation gate for TCA records.

    Raises `ValueError` if ANY record violates:
      1. `FILL_UNRESOLVED` (`event_type`, `status`, or `comment`)
      2. Non-finite (`NaN`/`Inf`) or boolean `swap_usd` (or numeric audit field)
      3. Closed trade / fill still has `swap_usd is None` after statement enrichment
      4. `abs(swap_usd) > swap_tolerance_usd` when `require_zero_swap=True`
    """
    if isinstance(swap_tolerance_usd, bool) or not math.isfinite(float(swap_tolerance_usd)) or swap_tolerance_usd < 0.0:
        raise ValueError(f"swap_tolerance_usd must be finite and >= 0, got {swap_tolerance_usd!r}")

    rec_list = list(records)
    unresolved_indices: list[int] = []
    missing_swap_indices: list[int] = []
    nonzero_swap_indices: list[int] = []
    nonfinite_errors: list[str] = []
    closed_checked = 0

    for idx, rec in enumerate(rec_list):
        if is_unresolved_record(rec):
            unresolved_indices.append(idx)

        # Validate all present numeric fields are finite (never NaN/Inf/bool)
        for field in _NUMERIC_AUDIT_FIELDS:
            if field in rec and rec[field] is not None:
                try:
                    parse_optional_finite_float(rec[field], field_name=field)
                except ValueError as exc:
                    nonfinite_errors.append(f"row[{idx}].{exc}")

        ev = str(rec.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES:
            continue

        try:
            swap_val = parse_optional_finite_float(rec.get("swap_usd"), field_name="swap_usd")
        except ValueError:
            # Already recorded in nonfinite_errors if swap_usd in rec; guard if unusual key state
            if f"row[{idx}].swap_usd" not in " ".join(nonfinite_errors):
                nonfinite_errors.append(f"row[{idx}].swap_usd non-finite")
            continue

        needs_swap = _requires_resolved_swap(rec, check_entries=check_entries_for_missing_swap)
        if needs_swap:
            closed_checked += 1
            if swap_val is None:
                missing_swap_indices.append(idx)

        if swap_val is not None and abs(swap_val) > swap_tolerance_usd:
            nonzero_swap_indices.append(idx)

    failure_parts: list[str] = []
    if unresolved_indices:
        failure_parts.append(f"FILL_UNRESOLVED rows={unresolved_indices}")
    if nonfinite_errors:
        failure_parts.append(f"NONFINITE_VALUES={nonfinite_errors[:5]}")
    if missing_swap_indices:
        failure_parts.append(f"MISSING_SWAP_USD rows={missing_swap_indices}")
    if require_zero_swap and nonzero_swap_indices:
        failure_parts.append(f"NONZERO_SWAP_USD rows={nonzero_swap_indices}")

    if failure_parts:
        raise ValueError("TCA_POST_RECONCILE_FAILED: " + "; ".join(failure_parts))

    return {
        "passed": True,
        "records_checked": len(rec_list),
        "closed_trades_checked": closed_checked,
        "unresolved_fill_count": 0,
        "missing_swap_count": 0,
        "nonzero_swap_count": len(nonzero_swap_indices),
        "nonfinite_count": 0,
    }


# ---------------------------------------------------------------------------
# Strictly Causal Markout Curve (+1s / +10s / +60s / +5m)
# ---------------------------------------------------------------------------
def format_horizon_label(horizon_sec: int) -> str:
    """Format markout horizon seconds (`1->+1s`, `10->+10s`, `60->+60s`, `300->+5m`)."""
    if horizon_sec == 60:
        return "+60s"
    if horizon_sec >= 300 and horizon_sec % 60 == 0:
        return f"+{horizon_sec // 60}m"
    return f"+{horizon_sec}s"


def _parse_quote_mid(q: Mapping[str, Any]) -> float:
    bid = parse_optional_finite_float(q.get("bid"), field_name="quote.bid")
    ask = parse_optional_finite_float(q.get("ask"), field_name="quote.ask")
    if bid is not None or ask is not None:
        if bid is None or ask is None:
            raise ValueError("Quote providing bid or ask must provide both finite bid and ask")
        if bid <= 0.0 or ask < bid:
            raise ValueError(f"Invalid quote bid/ask: bid={bid}, ask={ask}")
        return 0.5 * (bid + ask)
    mid = parse_optional_finite_float(q.get("mid") if "mid" in q else q.get("midprice"), field_name="quote.mid")
    if mid is None or mid <= 0.0:
        raise ValueError(f"Quote must provide finite positive bid/ask or mid, got {q!r}")
    return mid


def _normalize_quote_series(
    quote_series: Mapping[str, Sequence[Mapping[str, Any]]] | Iterable[Mapping[str, Any]],
) -> dict[str, tuple[list[float], list[float]]]:
    """Index quotes into strictly ascending `(timestamps, midprices)` arrays per canonical symbol."""
    grouped: dict[str, list[tuple[float, float]]] = {}

    if isinstance(quote_series, Mapping):
        for raw_sym, seq in quote_series.items():
            sym_key = normalize_symbol_alias(str(raw_sym))
            if not sym_key:
                raise ValueError(f"Empty symbol key in quote_series: {raw_sym!r}")
            for q in seq:
                ts_raw = q.get("utc_ts") if "utc_ts" in q else (q.get("ts") if "ts" in q else q.get("timestamp"))
                ts = parse_required_finite_float(ts_raw, field_name="quote.utc_ts")
                if ts <= 0.0:
                    raise ValueError(f"quote.utc_ts must be > 0, got {ts}")
                mid = _parse_quote_mid(q)
                grouped.setdefault(sym_key, []).append((ts, mid))
    else:
        for row in quote_series:
            if not isinstance(row, Mapping):
                raise ValueError(f"Quote entry must be a mapping, got {type(row).__name__}")
            nested_quotes = row.get("quotes")
            if isinstance(nested_quotes, Mapping):
                ts_raw = row.get("captured_utc_ts") if "captured_utc_ts" in row else row.get("utc_ts")
                ts = parse_required_finite_float(ts_raw, field_name="quote.captured_utc_ts")
                if ts <= 0.0:
                    raise ValueError(f"quote.captured_utc_ts must be > 0, got {ts}")
                for raw_sym, q in nested_quotes.items():
                    if not isinstance(q, Mapping):
                        continue
                    if "available" in q and not q.get("available"):
                        continue
                    sym_key = normalize_symbol_alias(str(raw_sym))
                    if not sym_key:
                        continue
                    mid = _parse_quote_mid(q)
                    grouped.setdefault(sym_key, []).append((ts, mid))
            else:
                sym_key = normalize_symbol_alias(str(row.get("symbol") or ""))
                if not sym_key:
                    raise ValueError(f"Flat quote row missing symbol: {row!r}")
                ts_raw = (
                    row.get("utc_ts") if "utc_ts" in row else (row.get("ts") if "ts" in row else row.get("timestamp"))
                )
                ts = parse_required_finite_float(ts_raw, field_name="quote.utc_ts")
                if ts <= 0.0:
                    raise ValueError(f"quote.utc_ts must be > 0, got {ts}")
                mid = _parse_quote_mid(row)
                grouped.setdefault(sym_key, []).append((ts, mid))

    indexed: dict[str, tuple[list[float], list[float]]] = {}
    for sym_key, pairs in grouped.items():
        pairs.sort(key=lambda item: item[0])
        indexed[sym_key] = ([p[0] for p in pairs], [p[1] for p in pairs])
    return indexed


def load_quote_tape(quote_path: Path | str) -> list[dict[str, Any]]:
    """Load quote tape from JSONL (flat or `mt5_live_spread_log.jsonl` nested) or CSV."""
    path = Path(quote_path)
    suffix = path.suffix.lower()
    quotes: list[dict[str, Any]] = []

    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            for line_no, raw in enumerate(csv.DictReader(f), start=2):
                if not raw or all(str(v or "").strip() == "" for v in raw.values()):
                    continue
                try:
                    ts_raw = raw.get("utc_ts") if "utc_ts" in raw else raw.get("ts")
                    ts = parse_required_finite_float(ts_raw, field_name="utc_ts")
                    sym = str(raw.get("symbol") or "").strip()
                    if not sym:
                        raise ValueError("symbol is required in quote CSV")
                    bid = parse_optional_finite_float(raw.get("bid"), field_name="bid")
                    ask = parse_optional_finite_float(raw.get("ask"), field_name="ask")
                    mid = parse_optional_finite_float(raw.get("mid"), field_name="mid")
                    rec: dict[str, Any] = {"utc_ts": ts, "symbol": sym}
                    if bid is not None and ask is not None:
                        rec["bid"] = bid
                        rec["ask"] = ask
                    elif mid is not None:
                        rec["mid"] = mid
                    else:
                        raise ValueError("quote CSV row requires bid+ask or mid")
                    quotes.append(rec)
                except ValueError as exc:
                    raise ValueError(f"{path.name}:{line_no}: {exc}") from exc
        return quotes

    # JSONL (supports flat rows and nested `mt5_live_spread_log.jsonl` snapshots)
    text = path.read_text(encoding="utf-8-sig", errors="replace")
    for raw_line in text.splitlines():
        s = raw_line.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
        except json.JSONDecodeError:
            # Skip mid-write truncated trailing JSONL line safely
            continue
        if isinstance(obj, dict):
            quotes.append(obj)
    return quotes


def _summarize_markout_horizon(
    *,
    horizon_sec: int,
    n_fills_total: int,
    bps_values: Sequence[float],
    px_values: Sequence[float],
) -> dict[str, Any]:
    n_obs = len(bps_values)
    if n_obs == 0:
        return {
            "horizon_sec": horizon_sec,
            "n_fills_total": n_fills_total,
            "n_observed": 0,
            "n_missing": n_fills_total,
            "mean_markout_bps": None,
            "median_markout_bps": None,
            "min_markout_bps": None,
            "max_markout_bps": None,
            "mean_markout_price": None,
            "median_markout_price": None,
            "adverse_selection_flagged": False,
        }
    bps_arr = np.asarray(bps_values, dtype=np.float64)
    px_arr = np.asarray(px_values, dtype=np.float64)
    mean_bps = float(np.mean(bps_arr))
    return {
        "horizon_sec": horizon_sec,
        "n_fills_total": n_fills_total,
        "n_observed": n_obs,
        "n_missing": n_fills_total - n_obs,
        "mean_markout_bps": round(mean_bps, 6),
        "median_markout_bps": round(float(np.median(bps_arr)), 6),
        "min_markout_bps": round(float(np.min(bps_arr)), 6),
        "max_markout_bps": round(float(np.max(bps_arr)), 6),
        "mean_markout_price": round(float(np.mean(px_arr)), 8),
        "median_markout_price": round(float(np.median(px_arr)), 8),
        "adverse_selection_flagged": bool(mean_bps < 0.0),
    }


def compute_markout_curve(
    fills: Iterable[Mapping[str, Any]],
    quote_series: Mapping[str, Sequence[Mapping[str, Any]]] | Iterable[Mapping[str, Any]],
    horizons_sec: Sequence[int] = DEFAULT_MARKOUT_HORIZONS_SEC,
    *,
    max_arrival_staleness_sec: float | None = None,
    max_horizon_lag_sec: float | None = None,
) -> dict[str, Any]:
    """Compute strictly causal signed markout curve at `+1s/+10s/+60s/+5m` relative to arrival midprice.

    Sign convention (institutional TCA standard):
      - BUY fill (`side_sign = +1`): `markout_px = +(mid_future - arrival_mid)`
      - SELL fill (`side_sign = -1`): `markout_px = -(mid_future - arrival_mid)`
      - `markout_bps = (markout_px / arrival_mid) * 10_000`
      - Negative mean post-fill markout flags adverse selection.

    Causal lookup rules (NEVER fabricates quotes):
      - Arrival midprice: explicit `arrival_mid` if provided, else causal `asof` quote
        (`max quote_ts <= fill_ts`), else fill `pre_bid`/`pre_ask` midpoint, else `None`.
      - Horizon `+h`: earliest quote with `quote_ts >= fill_ts + h`, else `None`.
    """
    if not horizons_sec:
        raise ValueError("horizons_sec must not be empty")
    clean_horizons: list[int] = []
    seen_h: set[int] = set()
    for h in horizons_sec:
        if isinstance(h, bool) or not isinstance(h, int) or h <= 0:
            raise ValueError(f"Each markout horizon must be a positive int, got {h!r}")
        if h in seen_h:
            raise ValueError(f"Duplicate markout horizon: {h}")
        seen_h.add(h)
        clean_horizons.append(h)

    if max_arrival_staleness_sec is not None and (
        isinstance(max_arrival_staleness_sec, bool)
        or not math.isfinite(float(max_arrival_staleness_sec))
        or max_arrival_staleness_sec < 0.0
    ):
        raise ValueError(f"max_arrival_staleness_sec must be finite >= 0, got {max_arrival_staleness_sec!r}")
    if max_horizon_lag_sec is not None and (
        isinstance(max_horizon_lag_sec, bool)
        or not math.isfinite(float(max_horizon_lag_sec))
        or max_horizon_lag_sec < 0.0
    ):
        raise ValueError(f"max_horizon_lag_sec must be finite >= 0, got {max_horizon_lag_sec!r}")

    indexed_quotes = _normalize_quote_series(quote_series)
    horizon_labels = [format_horizon_label(h) for h in clean_horizons]

    per_fill_results: list[dict[str, Any]] = []
    horizon_bps_all: dict[str, list[float]] = {lbl: [] for lbl in horizon_labels}
    horizon_px_all: dict[str, list[float]] = {lbl: [] for lbl in horizon_labels}
    sym_horizon_bps: dict[str, dict[str, list[float]]] = {}
    sym_horizon_px: dict[str, dict[str, list[float]]] = {}
    sym_fill_counts: dict[str, int] = {}
    all_observed_bps: list[float] = []
    fills_with_arrival = 0

    for fill_idx, fill in enumerate(fills):
        if is_unresolved_record(fill):
            raise ValueError(f"FILL_UNRESOLVED row at index {fill_idx} cannot enter markout calculation")
        ev = str(fill.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES:
            continue

        raw_sym = str(fill.get("symbol") or "").strip()
        sym_key = normalize_symbol_alias(raw_sym)
        if not sym_key:
            raise ValueError(f"Fill at index {fill_idx} missing symbol")

        side = str(fill.get("deal_side") or fill.get("exec_side") or fill.get("side") or "").strip().upper()
        if side == "BUY":
            side_sign = 1.0
        elif side == "SELL":
            side_sign = -1.0
        else:
            raise ValueError(f"Fill at index {fill_idx} has unsupported side {side!r}; expected BUY or SELL")

        ts_raw = (
            fill.get("utc_ts") if "utc_ts" in fill else (fill.get("fill_ts") if "fill_ts" in fill else fill.get("ts"))
        )
        fill_ts = parse_required_finite_float(ts_raw, field_name=f"fill[{fill_idx}].utc_ts")
        if fill_ts <= 0.0:
            raise ValueError(f"fill[{fill_idx}].utc_ts must be > 0, got {fill_ts}")

        fill_px = parse_optional_finite_float(fill.get("fill_price"), field_name=f"fill[{fill_idx}].fill_price")
        sym_fill_counts[sym_key] = sym_fill_counts.get(sym_key, 0) + 1
        sym_horizon_bps.setdefault(sym_key, {lbl: [] for lbl in horizon_labels})
        sym_horizon_px.setdefault(sym_key, {lbl: [] for lbl in horizon_labels})

        # Strictly causal arrival mid: explicit arrival_mid -> asof quote -> pre_bid/ask -> None
        arrival_mid: float | None = None
        arrival_quote_ts: float | None = None

        explicit_arr = parse_optional_finite_float(fill.get("arrival_mid"), field_name=f"fill[{fill_idx}].arrival_mid")
        if explicit_arr is not None:
            if explicit_arr <= 0.0:
                raise ValueError(f"fill[{fill_idx}].arrival_mid must be > 0, got {explicit_arr}")
            arrival_mid = explicit_arr
            arrival_quote_ts = fill_ts
        elif sym_key in indexed_quotes:
            q_ts_arr, q_mid_arr = indexed_quotes[sym_key]
            arr_i = bisect.bisect_right(q_ts_arr, fill_ts) - 1
            if arr_i >= 0:
                lag = fill_ts - q_ts_arr[arr_i]
                if max_arrival_staleness_sec is None or lag <= max_arrival_staleness_sec:
                    arrival_mid = q_mid_arr[arr_i]
                    arrival_quote_ts = q_ts_arr[arr_i]

        if arrival_mid is None:
            pre_bid = parse_optional_finite_float(fill.get("pre_bid"), field_name=f"fill[{fill_idx}].pre_bid")
            pre_ask = parse_optional_finite_float(fill.get("pre_ask"), field_name=f"fill[{fill_idx}].pre_ask")
            if pre_bid is not None and pre_ask is not None and pre_bid > 0.0 and pre_ask >= pre_bid:
                arrival_mid = 0.5 * (pre_bid + pre_ask)
                arrival_quote_ts = fill_ts

        if arrival_mid is not None:
            fills_with_arrival += 1

        fill_markouts: dict[str, dict[str, Any]] = {}
        q_pair = indexed_quotes.get(sym_key)

        for h, lbl in zip(clean_horizons, horizon_labels, strict=True):
            if arrival_mid is None or q_pair is None:
                fill_markouts[lbl] = {
                    "horizon_sec": h,
                    "quote_ts": None,
                    "future_mid": None,
                    "markout_price": None,
                    "markout_bps": None,
                }
                continue

            q_ts_arr, q_mid_arr = q_pair
            target_ts = fill_ts + float(h)
            fut_i = bisect.bisect_left(q_ts_arr, target_ts)
            if fut_i >= len(q_ts_arr):
                fill_markouts[lbl] = {
                    "horizon_sec": h,
                    "quote_ts": None,
                    "future_mid": None,
                    "markout_price": None,
                    "markout_bps": None,
                }
                continue

            fut_ts = q_ts_arr[fut_i]
            if max_horizon_lag_sec is not None and (fut_ts - target_ts) > max_horizon_lag_sec:
                fill_markouts[lbl] = {
                    "horizon_sec": h,
                    "quote_ts": None,
                    "future_mid": None,
                    "markout_price": None,
                    "markout_bps": None,
                }
                continue

            fut_mid = q_mid_arr[fut_i]
            mo_px = side_sign * (fut_mid - arrival_mid)
            mo_bps = (mo_px / arrival_mid) * 10_000.0

            horizon_bps_all[lbl].append(mo_bps)
            horizon_px_all[lbl].append(mo_px)
            sym_horizon_bps[sym_key][lbl].append(mo_bps)
            sym_horizon_px[sym_key][lbl].append(mo_px)
            all_observed_bps.append(mo_bps)

            fill_markouts[lbl] = {
                "horizon_sec": h,
                "quote_ts": fut_ts,
                "future_mid": round(fut_mid, 8),
                "markout_price": round(mo_px, 8),
                "markout_bps": round(mo_bps, 6),
            }

        per_fill_results.append(
            {
                "fill_index": fill_idx,
                "utc_ts": fill_ts,
                "symbol": raw_sym,
                "canonical_symbol": sym_key,
                "side": side,
                "fill_price": fill_px,
                "arrival_mid": round(arrival_mid, 8) if arrival_mid is not None else None,
                "arrival_quote_ts": arrival_quote_ts,
                "markouts": fill_markouts,
            }
        )

    n_fills_total = len(per_fill_results)
    by_horizon: dict[str, dict[str, Any]] = {}
    for h, lbl in zip(clean_horizons, horizon_labels, strict=True):
        by_horizon[lbl] = _summarize_markout_horizon(
            horizon_sec=h,
            n_fills_total=n_fills_total,
            bps_values=horizon_bps_all[lbl],
            px_values=horizon_px_all[lbl],
        )

    by_symbol: dict[str, dict[str, Any]] = {}
    for sym_key in sorted(sym_fill_counts.keys()):
        sym_by_h: dict[str, dict[str, Any]] = {}
        sym_obs_bps: list[float] = []
        for h, lbl in zip(clean_horizons, horizon_labels, strict=True):
            sym_by_h[lbl] = _summarize_markout_horizon(
                horizon_sec=h,
                n_fills_total=sym_fill_counts[sym_key],
                bps_values=sym_horizon_bps[sym_key][lbl],
                px_values=sym_horizon_px[sym_key][lbl],
            )
            sym_obs_bps.extend(sym_horizon_bps[sym_key][lbl])
        sym_overall_mean = round(float(np.mean(sym_obs_bps)), 6) if sym_obs_bps else None
        by_symbol[sym_key] = {
            "fills_analysed": sym_fill_counts[sym_key],
            "overall_mean_markout_bps": sym_overall_mean,
            "adverse_selection_flagged": bool(sym_overall_mean is not None and sym_overall_mean < 0.0),
            "by_horizon": sym_by_h,
        }

    overall_mean_bps = round(float(np.mean(all_observed_bps)), 6) if all_observed_bps else None
    adverse_horizons = [lbl for lbl in horizon_labels if by_horizon[lbl]["adverse_selection_flagged"]]
    adverse_overall = bool(overall_mean_bps is not None and overall_mean_bps < 0.0)

    return {
        "schema": "naqex-markout-curve-v1",
        "horizons_sec": clean_horizons,
        "horizon_labels": horizon_labels,
        "fills_analysed": n_fills_total,
        "fills_with_arrival_mid": fills_with_arrival,
        "overall_mean_markout_bps": overall_mean_bps,
        "adverse_selection_flagged": adverse_overall,
        "adverse_selection_any_horizon": bool(adverse_horizons),
        "adverse_selection_horizons": adverse_horizons,
        "by_horizon": by_horizon,
        "by_symbol": by_symbol,
        "per_fill": per_fill_results,
    }


# ---------------------------------------------------------------------------
# Atomic SHA-256 JSON Report Writer
# ---------------------------------------------------------------------------
def canonical_payload_sha256(payload: Mapping[str, Any]) -> str:
    """Compute deterministic SHA-256 over canonical JSON (excluding `report_sha256`)."""
    body = {k: v for k, v in payload.items() if k != "report_sha256"}
    raw = json.dumps(
        body,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=True,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def write_atomic_sha256_json(path: Path | str, payload: Mapping[str, Any]) -> dict[str, Any]:
    """Atomically write JSON report with embedded `report_sha256` and LF newlines."""
    out_path = Path(path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    report_sha = canonical_payload_sha256(payload)
    out_obj: dict[str, Any] = {k: v for k, v in payload.items() if k != "report_sha256"}
    out_obj["report_sha256"] = report_sha

    rendered = json.dumps(out_obj, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    data = rendered.encode("utf-8")

    fd, tmp_name = tempfile.mkstemp(prefix=f".{out_path.name}.", suffix=".tmp", dir=str(out_path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise

    return {
        "path": str(out_path),
        "report_sha256": report_sha,
        "file_sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }


__all__ = [
    "BENCHMARK_SPREAD_PTS",
    "DEFAULT_MARKOUT_HORIZONS_SEC",
    "ENTRY_EVENT_TYPES",
    "EXIT_EVENT_TYPES",
    "NON_FILL_EVENT_TYPES",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "POINT_SIZES",
    "SINGLE_ROW_FILL_EVENT_TYPES",
    "UNRESOLVED_EVENT_TYPES",
    "VALID_FILL_EVENT_TYPES",
    "benchmark_spread_for_symbol",
    "canonical_payload_sha256",
    "compute_markout_curve",
    "enrich_audit_rows_with_statement",
    "extract_comment_tags",
    "format_horizon_label",
    "is_unresolved_record",
    "load_exec_audit_csv",
    "load_quote_tape",
    "normalize_symbol_alias",
    "parse_exec_audit_row",
    "parse_optional_finite_float",
    "parse_optional_strict_int",
    "parse_required_finite_float",
    "parse_required_strict_int",
    "point_size_for_symbol",
    "validate_tca_post_reconcile",
    "write_atomic_sha256_json",
]
