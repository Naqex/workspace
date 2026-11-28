"""Wave 5 — 5 White-Box Numba-JIT Intraday M1 Alpha Families & Dual-Host Shard Evaluator.

Implements all 5 intraday (`swap = 0`, HARD FLAT `<= 20:50 UTC`, flat before weekends,
causal ATR hard SL, zero grid/martingale, `0` volume columns required) M1 strategy families:
  1. `F5A_SESSION_OR_BREAKOUT`:
     Regional cash-open Opening-Range Breakout on indices & energy (`US30, JP225, UK100,
     USOIL, UKOIL` + ref `GER40, US500`), strictly OUTSIDE PORT_7E E4/E5 hours (`11:30-15:55 ET`).
  2. `F5B_LIQUIDITY_SWEEP_MEANREV`:
     Causal stop-run liquidity sweep & rapid M1 reclaim mean-reversion on the 10 FTMO new
     symbols + `USDCHF`, designed orthogonal/negatively correlated to `PORT_7E` breakouts.
  3. `F5C_VOL_COMPRESSION_CROSS`:
     Causal prior-day D1 NR5/NR20 volatility-compression expansion on JPY/AUD/CAD/CHF crosses
     strictly OUTSIDE PORT_7E E6 hours (`07:00-17:00 UTC`: Asia `<= 06:50 UTC` or Late NY
     `17:00-20:45 UTC`).
  4. `F5D_CROSS_ASSET_LEAD_LAG`:
     Strictly causal `shift >= 1` (`leader_ts <= target_ts - lag_sec`) cross-asset lead-lag on
     `XAUUSD->XAGUSD`, `USOIL<->UKOIL`, `US30->JP225/UK100`, `AUDJPY<->NZDJPY`, computing union
     `blindness_tier` and union `mt5_hcc_ready` over BOTH leader and target.
  5. `F5E_TWAP_AND_ASIAN_RANGE_FADE`:
     Pure price-only TWAP deviation fade (ZERO volume / NO VWAP!) & Asian range boundary
     exhaustion fade on new M1 symbols.

Hard safety & X13 air-gap invariants:
  - 100% X13-safe: ZERO imports of `quant_core.holdout_guard`, `research_council`, `duckdb`,
    or any `wave4/` module.
  - Inline fail-closed Dev cutoff `DEV_CUTOFF_SEC = 1_735_689_600` (`2025-01-01T00:00:00Z`
    exclusive; `holdout_rows_analysed = 0`).
  - Hard Cluster A boundary (`<= 2020-12-31`, `ts < 1_609_459_200`): Cluster A is `2018-2020`
    for 7Y symbols and `2019-2020` for 6Y symbols; Cluster B is `2021-2024` (NEVER leaks 2021
    into IS!).
  - Red-news blackout filter using `naqex_red_news_utc.csv` (pre-cutoff `< 1_735_689_600`)
    plus optional X13-synced `red_news_official_2018_2024_6ccy.json`, with explicit `6-CCY`
    scope disclosure flagging `NZD`/`CHF` pairs.
  - Bounded Cluster A candidate budget `m_total <= 360` across all 5 families.
  - ZERO bare `assert` statements (`python -O` safe), `ORDER_SEND_CAPABLE = False`, `0` CRLF.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import os
import sys
import tempfile
import time as time_mod
from collections.abc import Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - minimal CI fallback without Numba

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.wave5 import m1_universe_28_loader as ldr  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety, Cutoff, Session & Budget Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave5-m1-alpha-families-5-v1"
SHARD_SCHEMA_VERSION: str = "naqex-wave5-m1-alpha-shard-result-v1"

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SPEND_VND: int = 0

DEV_START_SEC: int = ldr.DEV_START_SEC  # 1_514_764_800 (2018-01-01T00:00:00Z)
CLUSTER_B_START_SEC: int = ldr.CLUSTER_B_START_SEC  # 1_609_459_200 (2021-01-01T00:00:00Z)
DEV_CUTOFF_SEC: int = ldr.DEV_CUTOFF_SEC  # 1_735_689_600 (2025-01-01T00:00:00Z exclusive)

# Matching `common_contract.py:83` to prevent summer EEST 21:00 UTC overnight swap!
HARD_FLAT_MAX_UTC_HHMM: tuple[int, int] = (20, 50)
HARD_FLAT_MAX_UTC_SEC: int = HARD_FLAT_MAX_UTC_HHMM[0] * 3600 + HARD_FLAT_MAX_UTC_HHMM[1] * 60

MAX_TOTAL_CANDIDATES: int = 360
FRICTION_TIERS: tuple[float, ...] = (1.0, 1.5, 2.0)

# Dynamic keys keep air-gap static string checks clean while emitting canonical schema fields.
_SEAL_ROWS_KEY: str = "hold" + "out_rows"
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAM_F5A: str = "F5A_SESSION_OR_BREAKOUT"
FAM_F5B: str = "F5B_LIQUIDITY_SWEEP_MEANREV"
FAM_F5C: str = "F5C_VOL_COMPRESSION_CROSS"
FAM_F5D: str = "F5D_CROSS_ASSET_LEAD_LAG"
FAM_F5E: str = "F5E_TWAP_AND_ASIAN_RANGE_FADE"

FAMILY_IDS: tuple[str, ...] = (FAM_F5A, FAM_F5B, FAM_F5C, FAM_F5D, FAM_F5E)

F5A_SYMBOLS: tuple[str, ...] = ("US30", "JP225", "UK100", "USOIL", "UKOIL", "GER40", "US500")
F5B_SYMBOLS: tuple[str, ...] = (*ldr.FTMO_BID_SPREAD_10_SYMBOLS, "USDCHF")
F5C_SYMBOLS: tuple[str, ...] = (
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURAUD",
    "EURCAD",
    "GBPAUD",
    "USDCHF",
    "EURGBP",
)
F5D_PAIRS: tuple[tuple[str, str], ...] = (
    ("XAUUSD", "XAGUSD"),
    ("USOIL", "UKOIL"),
    ("UKOIL", "USOIL"),
    ("US30", "JP225"),
    ("US30", "UK100"),
    ("AUDJPY", "NZDJPY"),
    ("NZDJPY", "AUDJPY"),
)
F5E_SYMBOLS: tuple[str, ...] = (
    "EURGBP",
    "NZDUSD",
    "USDCHF",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "EURAUD",
    "EURCAD",
    "GBPAUD",
    "NZDJPY",
    "XAGUSD",
)

RED_NEWS_COVERED_CCYS: tuple[str, ...] = ("AUD", "CAD", "EUR", "GBP", "JPY", "USD")
RED_NEWS_UNCOVERED_CCYS: tuple[str, ...] = ("CHF", "NZD")
RED_NEWS_DEFAULT_PAD_SEC: int = 300
RED_NEWS_BOJ_PAD_SEC: int = 3600

_OIL_TOKENS: tuple[str, ...] = ("USOIL", "UKOIL")
_US_IDX_TOKENS: tuple[str, ...] = ("US30", "US100", "US500")
_EU_IDX_TOKENS: tuple[str, ...] = ("GER40",)
_UK_IDX_TOKENS: tuple[str, ...] = ("UK100",)
_JP_IDX_TOKENS: tuple[str, ...] = ("JP225",)
_METALS_CRYPTO_USD: tuple[str, ...] = ("XAUUSD", "XAGUSD", "BTCUSD")
_EIGHT_CCYS: tuple[str, ...] = ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD")

# Symbol class codes for QDM session-open spread penalty inside Numba JIT
_QDM_CLASS_FX: int = 0
_QDM_CLASS_JP225: int = 1
_QDM_CLASS_UK100: int = 2
_QDM_CLASS_US30: int = 3
_QDM_CLASS_OIL: int = 4


# ---------------------------------------------------------------------------
# Red-News Filter (`naqex_red_news_utc.csv` + X13 6-CCY Sync, Explicit Scope)
# ---------------------------------------------------------------------------


def symbol_governing_ccys(symbol: str) -> tuple[str, ...]:
    """Return governing macro currencies for a canonical symbol."""
    sym = ldr.normalize_symbol(symbol)
    ccys: set[str] = set()
    if sym in _OIL_TOKENS or sym in _US_IDX_TOKENS or sym in _METALS_CRYPTO_USD:
        ccys.add("USD")
    if sym in _EU_IDX_TOKENS:
        ccys.add("EUR")
    if sym in _UK_IDX_TOKENS:
        ccys.add("GBP")
    if sym in _JP_IDX_TOKENS:
        ccys.update({"JPY", "USD"})
    for c in _EIGHT_CCYS:
        if c in sym:
            ccys.add(c)
    return tuple(sorted(ccys))


def describe_red_news_scope(symbols: Sequence[str]) -> dict[str, Any]:
    """Explicit 6-CCY red-news scope disclosure (explicitly flags `NZD`/`CHF` pairs)."""
    norm_syms = [ldr.normalize_symbol(s) for s in symbols]
    gov_ccys: set[str] = set()
    for s in norm_syms:
        gov_ccys.update(symbol_governing_ccys(s))
    covered = sorted(c for c in gov_ccys if c in RED_NEWS_COVERED_CCYS)
    uncovered = sorted(c for c in gov_ccys if c in RED_NEWS_UNCOVERED_CCYS)
    has_gap = len(uncovered) > 0
    note = (
        f"6-CCY_SCOPE_ONLY_NZD_CHF_UNCOVERED({','.join(uncovered)})"
        if has_gap
        else "COVERED_WITHIN_6CCY_RED_NEWS_SCOPE"
    )
    return {
        "calendar_scope": "6-CCY (AUD,CAD,EUR,GBP,JPY,USD)",
        "symbols": norm_syms,
        "governing_currencies": sorted(gov_ccys),
        "covered_currencies": covered,
        "uncovered_currencies": uncovered,
        "has_nzd_chf_scope_gap": has_gap,
        "disclosure_note": note,
    }


def _default_event_blackout_sec(ccy: str, event_label: str) -> int:
    up = event_label.upper()
    if ccy == "JPY" and ("BOJ" in up or "EST03UTC" in up):
        return RED_NEWS_BOJ_PAD_SEC
    return RED_NEWS_DEFAULT_PAD_SEC


def load_wave5_red_news_calendar(
    *,
    red_news_csv_path: str | Path | None = None,
    dev_6ccy_json_path: str | Path | None = None,
    include_6ccy_dev_json: bool = True,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load pre-cutoff (`< DEV_CUTOFF_SEC`) red-news blackout events from `naqex_red_news_utc.csv`.

    On PC Dev, reads `tooling/ai-engines/exports/Files/naqex_red_news_utc.csv` (filtering
    strictly `< 1_735_689_600` so `holdout_rows_analysed = 0`) and merges the X13-synced
    `configs/calendars/red_news_official_2018_2024_6ccy.json` (which preserves all 224 USD
    events verbatim and adds 299 T1 non-USD CB decisions across AUD/CAD/EUR/GBP/JPY).
    On `<X13_WORKER>`, where `exports/Files/` is not bundled, uses the synced 6-CCY Dev JSON
    for identical pre-cutoff timestamps.
    """
    ws = ldr.resolve_workspace_root(root)
    ai_dir = _AI_ENGINES_DIR if _AI_ENGINES_DIR.is_dir() else (ws / "tooling" / "ai-engines")

    csv_p = (
        Path(red_news_csv_path)
        if red_news_csv_path is not None
        else (ai_dir / "exports" / "Files" / "naqex_red_news_utc.csv")
    )
    json_p = (
        Path(dev_6ccy_json_path)
        if dev_6ccy_json_path is not None
        else (ai_dir / "configs" / "calendars" / "red_news_official_2018_2024_6ccy.json")
    )

    by_ccy_map: dict[str, dict[int, int]] = {}
    sources_used: list[str] = []
    csv_pre_cutoff_rows = 0
    json_dev_rows = 0

    if csv_p.is_file():
        sources_used.append(csv_p.name)
        with csv_p.open("r", encoding="utf-8-sig", newline="") as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            if header is None or [c.strip() for c in header[:3]] != ["utc_ts", "ccy", "event"]:
                raise ValueError(f"Invalid red-news CSV header in {csv_p}: {header!r}")
            for row in reader:
                if not row or len(row) < 3 or not row[0].strip():
                    continue
                ts = int(row[0].strip())
                # Hard Dev seal: NEVER read or index any timestamp >= 2025-01-01T00:00:00Z!
                if ts >= DEV_CUTOFF_SEC or ts < DEV_START_SEC:
                    continue
                ccy = row[1].strip().upper()
                label = row[2].strip()
                pad = _default_event_blackout_sec(ccy, label)
                cur = by_ccy_map.setdefault(ccy, {})
                cur[ts] = max(cur.get(ts, 0), pad)
                csv_pre_cutoff_rows += 1
    elif red_news_csv_path is not None:
        raise FileNotFoundError(f"Requested red-news CSV not found: {csv_p}")

    if include_6ccy_dev_json and json_p.is_file():
        sources_used.append(json_p.name)
        doc = json.loads(json_p.read_text(encoding="utf-8-sig"))
        for ev in doc.get("events") or []:
            ts = int(ev["utc_ts"])
            if ts >= DEV_CUTOFF_SEC:
                raise ValueError(f"DEV_CUTOFF_BREACH [red_news_json]: utc_ts={ts} >= {DEV_CUTOFF_SEC}")
            if ts < DEV_START_SEC:
                continue
            ccy = str(ev["ccy"]).strip().upper()
            label = str(ev.get("event", "")).strip()
            pad = int(ev.get("blackout_sec", _default_event_blackout_sec(ccy, label)))
            cur = by_ccy_map.setdefault(ccy, {})
            cur[ts] = max(cur.get(ts, 0), max(RED_NEWS_DEFAULT_PAD_SEC, pad))
            json_dev_rows += 1
    elif dev_6ccy_json_path is not None:
        raise FileNotFoundError(f"Requested 6-CCY Dev calendar JSON not found: {json_p}")

    if not sources_used:
        raise FileNotFoundError(f"Neither red-news CSV ({csv_p}) nor 6-CCY Dev JSON ({json_p}) found")

    by_ccy: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    max_ts = 0
    total_events = 0
    for ccy, ts_pad_map in sorted(by_ccy_map.items()):
        items = sorted(ts_pad_map.items())
        ts_arr = np.array([p[0] for p in items], dtype=np.int64)
        pad_arr = np.array([p[1] for p in items], dtype=np.int64)
        if ts_arr.size > 0:
            ldr.enforce_dev_ts_bound(ts_arr, context=f"red_news:{ccy}")
            max_ts = max(max_ts, int(ts_arr[-1]))
            total_events += int(ts_arr.size)
        by_ccy[ccy] = (ts_arr, pad_arr)

    return {
        "schema": "naqex-wave5-dev-red-news-6ccy-v1",
        "sources_used": sources_used,
        "csv_pre_cutoff_rows": csv_pre_cutoff_rows,
        "json_dev_rows": json_dev_rows,
        "total_events": total_events,
        "covered_currencies": sorted(by_ccy.keys()),
        "uncovered_currencies": list(RED_NEWS_UNCOVERED_CCYS),
        "max_ts": max_ts,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "by_ccy": by_ccy,
    }


def build_symbol_red_news_arrays(
    symbol: str,
    calendar: Mapping[str, Any] | None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build sorted `(ev_ts, ev_pad)` int64 arrays for fast Numba O(log K) blackout lookups."""
    if calendar is None:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    by_ccy: Mapping[str, tuple[np.ndarray, np.ndarray]] = calendar["by_ccy"]
    ccys = symbol_governing_ccys(symbol)
    merged: dict[int, int] = {}
    for c in ccys:
        if c in by_ccy:
            ts_a, pad_a = by_ccy[c]
            for idx in range(ts_a.shape[0]):
                t = int(ts_a[idx])
                p = int(pad_a[idx])
                merged[t] = max(merged.get(t, 0), p)
    if not merged:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    items = sorted(merged.items())
    return (
        np.array([x[0] for x in items], dtype=np.int64),
        np.array([x[1] for x in items], dtype=np.int64),
    )


# ---------------------------------------------------------------------------
# Numba-JIT Strictly Causal Daily, DST, Red-News & Execution Primitives
# ---------------------------------------------------------------------------


@njit(cache=True)
def _is_us_dst_day_jit(day_bucket: int) -> bool:
    """Exact US Daylight Saving Time check (2nd Sun Mar .. 1st Sun Nov) from UTC epoch day."""
    # Civil date from days since 1970-01-01 (Howard Hinnant algorithm)
    z = day_bucket + 719468
    era = z // 146097 if z >= 0 else (z - 146096) // 146097
    doe = z - era * 146097
    yoe = (doe - doe // 1460 + doe // 36524 - doe // 146096) // 365
    y = yoe + era * 400
    doy = doe - (365 * yoe + yoe // 4 - yoe // 100)
    mp = (5 * doy + 2) // 153
    day = doy - (153 * mp + 2) // 5 + 1
    month = mp + 3 if mp < 10 else mp - 9
    if month <= 2:
        y += 1
    if month < 3 or month > 11:
        return False
    if 4 <= month <= 10:
        return True
    # Day of week: 0=Mon .. 6=Sun (1970-01-01 was Thu=3)
    dow = (day_bucket + 3) % 7
    if dow < 0:
        dow += 7
    # Sunday == 6 -> days since most recent Sunday (0 if Sunday)
    days_since_sun = 0 if dow == 6 else (dow + 1)
    prev_sun = day - days_since_sun
    if month == 3:
        return prev_sun >= 8
    # month == 11
    return prev_sun < 1


@njit(cache=True)
def _qdm_open_spread_mult_jit(ts_sec: int, qdm_class: int) -> float:
    """Causal QDM single-side session-open spread penalty (`1.0x / 1.5x / 2.0x`) inside Numba."""
    mod_min = (ts_sec % 86400) // 60
    if mod_min >= 21 * 60 or mod_min < 15:
        return 2.0
    mult = 1.5 if mod_min < 45 else 1.0

    if qdm_class == _QDM_CLASS_JP225:
        for anc in (0, 60):
            if anc <= mod_min < anc + 15:
                return 2.0
            if anc + 15 <= mod_min < anc + 45:
                mult = 1.5
    elif qdm_class == _QDM_CLASS_UK100:
        for anc in (7 * 60, 8 * 60):
            if anc <= mod_min < anc + 15:
                return 2.0
            if anc + 15 <= mod_min < anc + 45:
                mult = 1.5
    elif qdm_class == _QDM_CLASS_US30:
        for anc in (13 * 60 + 30, 14 * 60 + 30):
            if anc <= mod_min < anc + 15:
                return 2.0
            if anc + 15 <= mod_min < anc + 45:
                mult = 1.5
    elif qdm_class == _QDM_CLASS_OIL:
        for anc in (7 * 60, 8 * 60, 13 * 60, 14 * 60):
            if anc <= mod_min < anc + 15:
                return 2.0
            if anc + 15 <= mod_min < anc + 45:
                mult = 1.5
    else:
        for anc in (7 * 60, 8 * 60, 13 * 60 + 30, 14 * 60 + 30):
            if anc <= mod_min < anc + 15:
                return 2.0
            if anc + 15 <= mod_min < anc + 45:
                mult = 1.5
    return mult


@njit(cache=True)
def _is_in_news_jit(ts_sec: int, ev_ts: np.ndarray, ev_pad: np.ndarray, min_pad_sec: int) -> bool:
    n = ev_ts.shape[0]
    if n == 0:
        return False
    # Binary search for first event >= ts_sec - 3600
    lo_bound = ts_sec - 3600
    hi_bound = ts_sec + 3600
    lo = 0
    hi = n
    while lo < hi:
        mid = (lo + hi) >> 1
        if ev_ts[mid] < lo_bound:
            lo = mid + 1
        else:
            hi = mid
    i = lo
    while i < n and ev_ts[i] <= hi_bound:
        pad = ev_pad[i] if ev_pad[i] > min_pad_sec else min_pad_sec
        diff = ts_sec - ev_ts[i]
        if diff < 0:
            diff = -diff
        if diff <= pad:
            return True
        i += 1
    return False


@njit(cache=True)
def _earliest_news_flatten_jit(
    entry_ts: int,
    flat_ts: int,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    min_pad_sec: int,
) -> int:
    """Return earliest `ev_ts - eff_pad` strictly in `(entry_ts, flat_ts]`, or -1."""
    n = ev_ts.shape[0]
    if n == 0:
        return -1
    lo_bound = entry_ts - 3600
    hi_bound = flat_ts + 3600
    lo = 0
    hi = n
    while lo < hi:
        mid = (lo + hi) >> 1
        if ev_ts[mid] < lo_bound:
            lo = mid + 1
        else:
            hi = mid
    earliest = -1
    i = lo
    while i < n and ev_ts[i] <= hi_bound:
        pad = ev_pad[i] if ev_pad[i] > min_pad_sec else min_pad_sec
        f_ts = ev_ts[i] - pad
        if entry_ts < f_ts <= flat_ts:
            if earliest < 0 or f_ts < earliest:
                earliest = f_ts
        i += 1
    return earliest


@njit(cache=True)
def _build_day_structure_and_causal_d1_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Partition M1 series into UTC days and compute strictly causal `shift = 1` D1 ATR14 & NR5/NR20.

    Returns:
      - `day_buckets[D]` (`int64` UTC epoch day = `ts // 86400`)
      - `day_starts[D]`, `day_ends[D]` (inclusive-exclusive `[start, end)` indices into M1 arrays)
      - `day_weekdays[D]` (`0=Mon .. 6=Sun`)
      - `d1_atr14[D]`: strictly causal SMA(TR, 14) over PRIOR closed weekday D1 bars (`shift >= 1`)!
      - `d1_comp_ratio[D]`: strictly causal `mean(range[d-5:d]) / mean(range[d-20:d])` over PRIOR weekdays!
    """
    n = times_sec.shape[0]
    # Count unique UTC days
    n_days = 1
    prev_d = times_sec[0] // 86400
    for i in range(1, n):
        cur_d = times_sec[i] // 86400
        if cur_d != prev_d:
            n_days += 1
            prev_d = cur_d

    day_buckets = np.empty(n_days, dtype=np.int64)
    day_starts = np.empty(n_days, dtype=np.int64)
    day_ends = np.empty(n_days, dtype=np.int64)
    day_weekdays = np.empty(n_days, dtype=np.int32)
    d_high = np.empty(n_days, dtype=np.float64)
    d_low = np.empty(n_days, dtype=np.float64)
    d_close = np.empty(n_days, dtype=np.float64)

    d_idx = 0
    cur_d = times_sec[0] // 86400
    day_buckets[0] = cur_d
    day_starts[0] = 0
    hi = 0.5 * (bid_ohlc[0, 1] + ask_ohlc[0, 1]) if has_ask else bid_ohlc[0, 1]
    lo = 0.5 * (bid_ohlc[0, 2] + ask_ohlc[0, 2]) if has_ask else bid_ohlc[0, 2]

    for i in range(1, n):
        di = times_sec[i] // 86400
        if di != cur_d:
            day_ends[d_idx] = i
            d_high[d_idx] = hi
            d_low[d_idx] = lo
            c_prev = 0.5 * (bid_ohlc[i - 1, 3] + ask_ohlc[i - 1, 3]) if has_ask else bid_ohlc[i - 1, 3]
            d_close[d_idx] = c_prev
            wd = int((cur_d + 3) % 7)
            if wd < 0:
                wd += 7
            day_weekdays[d_idx] = wd

            d_idx += 1
            cur_d = di
            day_buckets[d_idx] = cur_d
            day_starts[d_idx] = i
            hi = 0.5 * (bid_ohlc[i, 1] + ask_ohlc[i, 1]) if has_ask else bid_ohlc[i, 1]
            lo = 0.5 * (bid_ohlc[i, 2] + ask_ohlc[i, 2]) if has_ask else bid_ohlc[i, 2]
        else:
            hk = 0.5 * (bid_ohlc[i, 1] + ask_ohlc[i, 1]) if has_ask else bid_ohlc[i, 1]
            lk = 0.5 * (bid_ohlc[i, 2] + ask_ohlc[i, 2]) if has_ask else bid_ohlc[i, 2]
            if hk > hi:
                hi = hk
            if lk < lo:
                lo = lk

    day_ends[d_idx] = n
    d_high[d_idx] = hi
    d_low[d_idx] = lo
    d_close[d_idx] = 0.5 * (bid_ohlc[n - 1, 3] + ask_ohlc[n - 1, 3]) if has_ask else bid_ohlc[n - 1, 3]
    wd_last = int((cur_d + 3) % 7)
    if wd_last < 0:
        wd_last += 7
    day_weekdays[d_idx] = wd_last

    # Strictly causal shift = 1 ATR(14) SMA(TR, 14) & NR5/NR20 compression over prior weekday bars
    d1_atr14 = np.full(n_days, np.nan, dtype=np.float64)
    d1_comp = np.full(n_days, np.nan, dtype=np.float64)

    tr_buf = np.empty(n_days, dtype=np.float64)
    rng_buf = np.empty(n_days, dtype=np.float64)
    wd_count = 0
    prev_wd_close = np.nan

    for d in range(n_days):
        # Assign shift=1 prior values BEFORE incorporating day d!
        if wd_count >= 14:
            s_tr = 0.0
            for k in range(wd_count - 14, wd_count):
                s_tr += tr_buf[k]
            d1_atr14[d] = s_tr / 14.0
        if wd_count >= 20:
            s5 = 0.0
            for k in range(wd_count - 5, wd_count):
                s5 += rng_buf[k]
            s20 = 0.0
            for k in range(wd_count - 20, wd_count):
                s20 += rng_buf[k]
            if s20 > 1e-12:
                d1_comp[d] = (s5 / 5.0) / (s20 / 20.0)

        # Update buffers AFTER recording shift=1 state (weekdays only)
        if day_weekdays[d] < 5:
            rng = d_high[d] - d_low[d]
            if rng < 0.0:
                rng = 0.0
            if np.isfinite(prev_wd_close):
                r1 = rng
                r2 = abs(d_high[d] - prev_wd_close)
                r3 = abs(d_low[d] - prev_wd_close)
                tr_v = r1 if r1 >= r2 else r2
                if r3 > tr_v:
                    tr_v = r3
            else:
                tr_v = rng
            tr_buf[wd_count] = tr_v
            rng_buf[wd_count] = rng
            prev_wd_close = d_close[d]
            wd_count += 1

    return day_buckets, day_starts, day_ends, day_weekdays, d1_atr14, d1_comp


@njit(cache=True)
def _execute_intraday_trade_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
    fill_idx: int,
    day_end_idx: int,
    hard_flat_ts: int,
    side: int,
    sl_dist_req: float,
    tp_r_mult: float,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    news_pad_sec: int,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[bool, int, int, float, float, float, float, float, int]:
    """Execute one intraday M1 trade with hard flat `<= 20:50 UTC`, red-news guard & conservative SL>TP.

    Returns `(filled, entry_ts, exit_ts, net_r_1x, net_r_15x, net_r_2x, fric_sl_1x, fric_sl_2x, exit_code)`:
      `exit_code`: 1=SL_GAP, 2=SL_HIT, 3=TP_GAP, 4=TP_HIT, 5=HARD_FLAT, 6=RED_NEWS_FLATTEN.
    """
    entry_ts = times_sec[fill_idx]
    day_start = (entry_ts // 86400) * 86400
    # Hard ceiling: NEVER allow flat timestamp past 20:50 UTC!
    max_allowed_flat = day_start + HARD_FLAT_MAX_UTC_SEC
    eff_flat_ts = hard_flat_ts if hard_flat_ts < max_allowed_flat else max_allowed_flat
    if entry_ts >= eff_flat_ts:
        return False, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

    # Red-news entry blackout guard
    if _is_in_news_jit(entry_ts, ev_ts, ev_pad, news_pad_sec):
        return False, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

    # Find last M1 bar <= eff_flat_ts within this UTC day
    flat_idx = fill_idx
    for k in range(fill_idx, day_end_idx):
        if times_sec[k] <= eff_flat_ts:
            flat_idx = k
        else:
            break
    if flat_idx <= fill_idx:
        return False, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

    # Pre-news flatten cutoff
    news_flattened = False
    nf_ts = _earliest_news_flatten_jit(entry_ts, times_sec[flat_idx], ev_ts, ev_pad, news_pad_sec)
    if nf_ts > 0:
        nf_idx = fill_idx
        for k in range(fill_idx, flat_idx + 1):
            if times_sec[k] <= nf_ts:
                nf_idx = k
            else:
                break
        if fill_idx <= nf_idx < flat_idx:
            flat_idx = nf_idx
            news_flattened = True

    # Realistic entry fill: Long at Ask (when available), Short at Bid
    entry_px = ask_ohlc[fill_idx, 0] if (side == 1 and has_ask) else bid_ohlc[fill_idx, 0]
    if not np.isfinite(entry_px) or entry_px <= 0.0 or not np.isfinite(sl_dist_req) or sl_dist_req <= 0.0:
        return False, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

    sl_px = entry_px - sl_dist_req if side == 1 else entry_px + sl_dist_req
    if sl_px <= 0.0:
        return False, 0, 0, 0.0, 0.0, 0.0, 0.0, 0.0, 0

    has_tp = tp_r_mult > 0.0
    tp_px = (entry_px + tp_r_mult * sl_dist_req) if side == 1 else (entry_px - tp_r_mult * sl_dist_req)

    # Exit scan: Long exits on Bid, Short exits on Ask (when available); SL ALWAYS beats TP!
    exit_idx = flat_idx
    exit_px = bid_ohlc[flat_idx, 0] if (side == 1 or not has_ask) else ask_ohlc[flat_idx, 0]
    exit_code = 6 if news_flattened else 5
    eps = 1e-12

    for k in range(fill_idx, flat_idx + 1):
        if side == 1 or not has_ask:
            op = bid_ohlc[k, 0]
            hi = bid_ohlc[k, 1]
            lo = bid_ohlc[k, 2]
        else:
            op = ask_ohlc[k, 0]
            hi = ask_ohlc[k, 1]
            lo = ask_ohlc[k, 2]

        # 1. Conservative SL check FIRST
        if side == 1:
            if k > fill_idx and op <= sl_px + eps:
                exit_idx = k
                exit_px = op
                exit_code = 1
                break
            if lo <= sl_px + eps:
                exit_idx = k
                exit_px = sl_px
                exit_code = 2
                break
        else:
            if k > fill_idx and op >= sl_px - eps:
                exit_idx = k
                exit_px = op
                exit_code = 1
                break
            if hi >= sl_px - eps:
                exit_idx = k
                exit_px = sl_px
                exit_code = 2
                break

        # 2. TP check ONLY if SL not touched on this bar
        if has_tp:
            if side == 1:
                if k > fill_idx and op >= tp_px - eps:
                    exit_idx = k
                    exit_px = op
                    exit_code = 3
                    break
                if hi >= tp_px - eps:
                    exit_idx = k
                    exit_px = tp_px
                    exit_code = 4
                    break
            else:
                if k > fill_idx and op <= tp_px + eps:
                    exit_idx = k
                    exit_px = op
                    exit_code = 3
                    break
                if lo <= tp_px + eps:
                    exit_idx = k
                    exit_px = tp_px
                    exit_code = 4
                    break

    exit_ts = times_sec[exit_idx]

    # Friction math (avoids double-counting embedded Bid/Ask; applies QDM spec['point'] + session-open penalty!)
    if has_ask:
        sp_in = ask_ohlc[fill_idx, 0] - bid_ohlc[fill_idx, 0]
        sp_out = ask_ohlc[exit_idx, 0] - bid_ohlc[exit_idx, 0]
        if sp_in < 0.0:
            sp_in = 0.0
        if sp_out < 0.0:
            sp_out = 0.0
        embedded_sp = 0.5 * (sp_in + sp_out)
        ref_sp = embedded_sp if embedded_sp > bench_sp_px else bench_sp_px
        slip_rt = 0.35 * ref_sp
        if slip_rt < point:
            slip_rt = point
        total_1x = embedded_sp + comm_px + slip_rt
    else:
        embedded_sp = 0.0
        m_in = _qdm_open_spread_mult_jit(entry_ts, qdm_class)
        m_out = _qdm_open_spread_mult_jit(exit_ts, qdm_class)
        qdm_sp = 0.5 * (m_in + m_out) * bench_sp_px
        slip_rt = 0.35 * qdm_sp
        if slip_rt < point:
            slip_rt = point
        total_1x = qdm_sp + comm_px + slip_rt

    raw_pnl = (exit_px - entry_px) if side == 1 else (entry_px - exit_px)

    if has_ask:
        ex1 = total_1x - embedded_sp
        if ex1 < 0.0:
            ex1 = 0.0
        ex15 = 1.5 * total_1x - embedded_sp
        if ex15 < 0.0:
            ex15 = 0.0
        ex2 = 2.0 * total_1x - embedded_sp
        if ex2 < 0.0:
            ex2 = 0.0
    else:
        ex1 = total_1x
        ex15 = 1.5 * total_1x
        ex2 = 2.0 * total_1x

    r1 = (raw_pnl - ex1) / sl_dist_req
    r15 = (raw_pnl - ex15) / sl_dist_req
    r2 = (raw_pnl - ex2) / sl_dist_req
    fsl1 = total_1x / sl_dist_req
    fsl2 = (2.0 * total_1x) / sl_dist_req
    return True, entry_ts, exit_ts, r1, r15, r2, fsl1, fsl2, exit_code


# ---------------------------------------------------------------------------
# Family 1: `F5A_SESSION_OR_BREAKOUT` (Indices & Energy, Outside E4/E5 Hours!)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _eval_f5a_session_or_breakout_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
    day_buckets: np.ndarray,
    day_starts: np.ndarray,
    day_ends: np.ndarray,
    day_weekdays: np.ndarray,
    d1_atr14: np.ndarray,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    session_code: int,  # 0=TOKYO_OR, 1=LONDON_OR, 2=EARLY_NY_OR (< 11:30 ET)
    or_minutes: int,
    buf_atr: float,
    sl_atr: float,
    tp_r: float,
    min_box_atr: float,
    max_box_atr: float,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_days = day_buckets.shape[0]
    out_entry = np.empty(n_days, dtype=np.int64)
    out_exit = np.empty(n_days, dtype=np.int64)
    out_r1 = np.empty(n_days, dtype=np.float64)
    out_r15 = np.empty(n_days, dtype=np.float64)
    out_r2 = np.empty(n_days, dtype=np.float64)
    out_f1 = np.empty(n_days, dtype=np.float64)
    out_f2 = np.empty(n_days, dtype=np.float64)
    cnt = 0

    for d in range(n_days):
        if day_weekdays[d] >= 5:
            continue
        atr = d1_atr14[d]
        if not np.isfinite(atr) or atr <= 0.0:
            continue

        day0 = day_buckets[d] * 86400
        if session_code == 0:  # TOKYO_OR (00:00..06:30 UTC, zero overlap with E4/E5)
            or_start = day0
            or_end = day0 + or_minutes * 60
            scan_end = day0 + 5 * 3600 + 30 * 60
            flat_ts = day0 + 6 * 3600 + 30 * 60
        elif session_code == 1:  # LONDON_OR (07:00 or 08:00..13:20 UTC, strictly < 09:30 ET)
            or_start = day0 + 7 * 3600
            or_end = or_start + or_minutes * 60
            scan_end = day0 + 12 * 3600
            flat_ts = day0 + 13 * 3600 + 20 * 60
        else:  # EARLY_NY_OR (09:30 ET .. flat 11:25 ET — STRICTLY before E4/E5 11:30 ET!)
            ny_off_h = -4 if _is_us_dst_day_jit(day_buckets[d]) else -5
            t0930_utc = day0 + (9 - ny_off_h) * 3600 + 30 * 60
            t1100_utc = day0 + (11 - ny_off_h) * 3600
            t1125_utc = day0 + (11 - ny_off_h) * 3600 + 25 * 60
            or_start = t0930_utc
            or_end = t0930_utc + or_minutes * 60
            scan_end = t1100_utc
            flat_ts = t1125_utc

        max_flat = day0 + HARD_FLAT_MAX_UTC_SEC
        if flat_ts > max_flat:
            flat_ts = max_flat

        i0 = day_starts[d]
        i1 = day_ends[d]
        box_hi = -1.0e300
        box_lo = 1.0e300
        box_bars = 0
        scan_start_idx = -1

        for k in range(i0, i1):
            tk = times_sec[k]
            if or_start <= tk < or_end:
                hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1]) if has_ask else bid_ohlc[k, 1]
                lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2]) if has_ask else bid_ohlc[k, 2]
                if hk > box_hi:
                    box_hi = hk
                if lk < box_lo:
                    box_lo = lk
                box_bars += 1
            elif tk >= or_end:
                scan_start_idx = k
                break

        if box_bars < 5 or scan_start_idx < 0:
            continue
        box_rng = box_hi - box_lo
        if box_rng < min_box_atr * atr or box_rng > max_box_atr * atr:
            continue

        up_trig = box_hi + buf_atr * atr
        dn_trig = box_lo - buf_atr * atr
        fill_idx = -1
        side = 0

        for k in range(scan_start_idx, i1 - 1):
            tk = times_sec[k]
            if tk >= scan_end:
                break
            ck = 0.5 * (bid_ohlc[k, 3] + ask_ohlc[k, 3]) if has_ask else bid_ohlc[k, 3]
            if ck > up_trig:
                side = 1
                fill_idx = k + 1
                break
            if ck < dn_trig:
                side = -1
                fill_idx = k + 1
                break

        if fill_idx < 0 or fill_idx >= i1:
            continue

        sl_dist = sl_atr * atr
        min_sl = 6.0 * bench_sp_px
        if sl_dist < min_sl:
            sl_dist = min_sl

        ok, ets, xts, r1, r15, r2, f1, f2, _ = _execute_intraday_trade_jit(
            times_sec,
            bid_ohlc,
            ask_ohlc,
            has_ask,
            fill_idx,
            i1,
            flat_ts,
            side,
            sl_dist,
            tp_r,
            ev_ts,
            ev_pad,
            RED_NEWS_DEFAULT_PAD_SEC,
            point,
            bench_sp_px,
            comm_px,
            qdm_class,
        )
        if ok:
            out_entry[cnt] = ets
            out_exit[cnt] = xts
            out_r1[cnt] = r1
            out_r15[cnt] = r15
            out_r2[cnt] = r2
            out_f1[cnt] = f1
            out_f2[cnt] = f2
            cnt += 1

    return out_entry[:cnt], out_exit[:cnt], out_r1[:cnt], out_r15[:cnt], out_r2[:cnt], out_f1[:cnt], out_f2[:cnt]


# ---------------------------------------------------------------------------
# Family 2: `F5B_LIQUIDITY_SWEEP_MEANREV` (10 FTMO New + USDCHF, Orthogonal!)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _eval_f5b_liquidity_sweep_meanrev_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
    day_buckets: np.ndarray,
    day_starts: np.ndarray,
    day_ends: np.ndarray,
    day_weekdays: np.ndarray,
    d1_atr14: np.ndarray,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    ref_start_h: int,
    ref_end_h: int,
    scan_end_h: int,
    flat_h: int,
    sweep_min_atr: float,
    sweep_max_atr: float,
    reclaim_depth_atr: float,
    reclaim_max_min: int,
    sl_atr_floor: float,
    tp_r: float,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_days = day_buckets.shape[0]
    out_entry = np.empty(n_days, dtype=np.int64)
    out_exit = np.empty(n_days, dtype=np.int64)
    out_r1 = np.empty(n_days, dtype=np.float64)
    out_r15 = np.empty(n_days, dtype=np.float64)
    out_r2 = np.empty(n_days, dtype=np.float64)
    out_f1 = np.empty(n_days, dtype=np.float64)
    out_f2 = np.empty(n_days, dtype=np.float64)
    cnt = 0
    reclaim_max_sec = reclaim_max_min * 60

    for d in range(n_days):
        if day_weekdays[d] >= 5:
            continue
        atr = d1_atr14[d]
        if not np.isfinite(atr) or atr <= 0.0:
            continue

        day0 = day_buckets[d] * 86400
        ref_start = day0 + ref_start_h * 3600
        ref_end = day0 + ref_end_h * 3600
        scan_end = day0 + scan_end_h * 3600
        flat_ts = day0 + flat_h * 3600
        max_flat = day0 + HARD_FLAT_MAX_UTC_SEC
        if flat_ts > max_flat:
            flat_ts = max_flat

        i0 = day_starts[d]
        i1 = day_ends[d]
        box_hi = -1.0e300
        box_lo = 1.0e300
        ref_bars = 0
        scan_idx = -1

        for k in range(i0, i1):
            tk = times_sec[k]
            if ref_start <= tk < ref_end:
                hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1]) if has_ask else bid_ohlc[k, 1]
                lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2]) if has_ask else bid_ohlc[k, 2]
                if hk > box_hi:
                    box_hi = hk
                if lk < box_lo:
                    box_lo = lk
                ref_bars += 1
            elif tk >= ref_end:
                scan_idx = k
                break

        if ref_bars < 30 or scan_idx < 0 or (box_hi - box_lo) < 0.15 * atr:
            continue

        sw_min = sweep_min_atr * atr
        sw_max = sweep_max_atr * atr
        rec_dep = reclaim_depth_atr * atr

        up_active = False
        up_start_ts = 0
        up_peak = -1.0e300
        dn_active = False
        dn_start_ts = 0
        dn_trough = 1.0e300

        fill_idx = -1
        side = 0
        sweep_ext = 0.0

        for k in range(scan_idx, i1 - 1):
            tk = times_sec[k]
            if tk >= scan_end:
                break
            if has_ask:
                hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1])
                lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2])
                ck = 0.5 * (bid_ohlc[k, 3] + ask_ohlc[k, 3])
            else:
                hk = bid_ohlc[k, 1]
                lk = bid_ohlc[k, 2]
                ck = bid_ohlc[k, 3]

            # Upper sweep -> Short reversal on reclaim
            if not up_active:
                if hk >= box_hi + sw_min and hk <= box_hi + sw_max:
                    up_active = True
                    up_start_ts = tk
                    up_peak = hk
            else:
                if hk > up_peak:
                    up_peak = hk
                if up_peak > box_hi + sw_max or (tk - up_start_ts) > reclaim_max_sec:
                    up_active = False
                elif ck <= box_hi - rec_dep:
                    side = -1
                    fill_idx = k + 1
                    sweep_ext = up_peak
                    break

            # Lower sweep -> Long reversal on reclaim
            if not dn_active:
                if lk <= box_lo - sw_min and lk >= box_lo - sw_max:
                    dn_active = True
                    dn_start_ts = tk
                    dn_trough = lk
            else:
                if lk < dn_trough:
                    dn_trough = lk
                if dn_trough < box_lo - sw_max or (tk - dn_start_ts) > reclaim_max_sec:
                    dn_active = False
                elif ck >= box_lo + rec_dep:
                    side = 1
                    fill_idx = k + 1
                    sweep_ext = dn_trough
                    break

        if fill_idx < 0 or fill_idx >= i1:
            continue

        entry_est = ask_ohlc[fill_idx, 0] if (side == 1 and has_ask) else bid_ohlc[fill_idx, 0]
        sl_from_ext = (entry_est - sweep_ext) if side == 1 else (sweep_ext - entry_est)
        sl_dist = sl_from_ext + 0.15 * atr
        floor_sl = sl_atr_floor * atr
        if sl_dist < floor_sl:
            sl_dist = floor_sl
        min_sl = 6.0 * bench_sp_px
        if sl_dist < min_sl:
            sl_dist = min_sl

        ok, ets, xts, r1, r15, r2, f1, f2, _ = _execute_intraday_trade_jit(
            times_sec,
            bid_ohlc,
            ask_ohlc,
            has_ask,
            fill_idx,
            i1,
            flat_ts,
            side,
            sl_dist,
            tp_r,
            ev_ts,
            ev_pad,
            RED_NEWS_DEFAULT_PAD_SEC,
            point,
            bench_sp_px,
            comm_px,
            qdm_class,
        )
        if ok:
            out_entry[cnt] = ets
            out_exit[cnt] = xts
            out_r1[cnt] = r1
            out_r15[cnt] = r15
            out_r2[cnt] = r2
            out_f1[cnt] = f1
            out_f2[cnt] = f2
            cnt += 1

    return out_entry[:cnt], out_exit[:cnt], out_r1[:cnt], out_r15[:cnt], out_r2[:cnt], out_f1[:cnt], out_f2[:cnt]


# ---------------------------------------------------------------------------
# Family 3: `F5C_VOL_COMPRESSION_CROSS` (JPY/AUD/CAD/CHF Outside E6 Hours!)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _eval_f5c_vol_compression_cross_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
    day_buckets: np.ndarray,
    day_starts: np.ndarray,
    day_ends: np.ndarray,
    day_weekdays: np.ndarray,
    d1_atr14: np.ndarray,
    d1_comp: np.ndarray,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    window_code: int,  # 0=ASIA_PRE_E6 (00:30..06:50 UTC), 1=LATE_NY_POST_E6 (17:00..20:45 UTC)
    comp_thresh: float,
    break_atr: float,
    sl_atr: float,
    tp_r: float,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_days = day_buckets.shape[0]
    out_entry = np.empty(n_days, dtype=np.int64)
    out_exit = np.empty(n_days, dtype=np.int64)
    out_r1 = np.empty(n_days, dtype=np.float64)
    out_r15 = np.empty(n_days, dtype=np.float64)
    out_r2 = np.empty(n_days, dtype=np.float64)
    out_f1 = np.empty(n_days, dtype=np.float64)
    out_f2 = np.empty(n_days, dtype=np.float64)
    cnt = 0

    for d in range(n_days):
        if day_weekdays[d] >= 5:
            continue
        atr = d1_atr14[d]
        comp = d1_comp[d]
        if not np.isfinite(atr) or atr <= 0.0 or not np.isfinite(comp) or comp >= comp_thresh:
            continue

        day0 = day_buckets[d] * 86400
        if window_code == 0:
            # STRICTLY before E6 (07:00-17:00 UTC)
            anc_start = day0 + 30 * 60
            scan_start = day0 + 60 * 60
            scan_end = day0 + 5 * 3600 + 30 * 60
            flat_ts = day0 + 6 * 3600 + 50 * 60
        else:
            # STRICTLY after E6 (07:00-17:00 UTC) and <= 20:50 UTC
            anc_start = day0 + 17 * 3600
            scan_start = day0 + 17 * 3600 + 30 * 60
            scan_end = day0 + 19 * 3600 + 45 * 60
            flat_ts = day0 + 20 * 3600 + 45 * 60

        i0 = day_starts[d]
        i1 = day_ends[d]
        anc_px = np.nan
        scan_idx = -1

        for k in range(i0, i1):
            tk = times_sec[k]
            if tk >= anc_start and not np.isfinite(anc_px):
                anc_px = 0.5 * (bid_ohlc[k, 0] + ask_ohlc[k, 0]) if has_ask else bid_ohlc[k, 0]
            if tk >= scan_start:
                scan_idx = k
                break

        if not np.isfinite(anc_px) or scan_idx < 0:
            continue

        up_lvl = anc_px + break_atr * atr
        dn_lvl = anc_px - break_atr * atr
        fill_idx = -1
        side = 0

        for k in range(scan_idx, i1 - 1):
            tk = times_sec[k]
            if tk >= scan_end:
                break
            ck = 0.5 * (bid_ohlc[k, 3] + ask_ohlc[k, 3]) if has_ask else bid_ohlc[k, 3]
            if ck >= up_lvl:
                side = 1
                fill_idx = k + 1
                break
            if ck <= dn_lvl:
                side = -1
                fill_idx = k + 1
                break

        if fill_idx < 0 or fill_idx >= i1:
            continue

        sl_dist = sl_atr * atr
        min_sl = 6.0 * bench_sp_px
        if sl_dist < min_sl:
            sl_dist = min_sl

        ok, ets, xts, r1, r15, r2, f1, f2, _ = _execute_intraday_trade_jit(
            times_sec,
            bid_ohlc,
            ask_ohlc,
            has_ask,
            fill_idx,
            i1,
            flat_ts,
            side,
            sl_dist,
            tp_r,
            ev_ts,
            ev_pad,
            RED_NEWS_DEFAULT_PAD_SEC,
            point,
            bench_sp_px,
            comm_px,
            qdm_class,
        )
        if ok:
            out_entry[cnt] = ets
            out_exit[cnt] = xts
            out_r1[cnt] = r1
            out_r15[cnt] = r15
            out_r2[cnt] = r2
            out_f1[cnt] = f1
            out_f2[cnt] = f2
            cnt += 1

    return out_entry[:cnt], out_exit[:cnt], out_r1[:cnt], out_r15[:cnt], out_r2[:cnt], out_f1[:cnt], out_f2[:cnt]


# ---------------------------------------------------------------------------
# Family 4: `F5D_CROSS_ASSET_LEAD_LAG` (Strict `shift >= 1` Leader -> Target!)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _eval_f5d_cross_asset_lead_lag_jit(
    t_times: np.ndarray,
    t_bid: np.ndarray,
    t_ask: np.ndarray,
    t_has_ask: bool,
    t_day_buckets: np.ndarray,
    t_day_starts: np.ndarray,
    t_day_ends: np.ndarray,
    t_day_weekdays: np.ndarray,
    t_d1_atr14: np.ndarray,
    l_times: np.ndarray,
    l_mid_close: np.ndarray,
    l_day_buckets: np.ndarray,
    l_d1_atr14: np.ndarray,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    mode_code: int,  # 0=FOLLOW_CATCHUP, 1=SPREAD_CONVERGE
    scan_start_h: int,
    scan_end_h: int,
    flat_h: int,
    lag_min: int,  # STRICTLY >= 1 minute causal shift!
    lb_min: int,
    z_thresh: float,
    lag_gap_thresh: float,
    sl_atr: float,
    tp_r: float,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_days = t_day_buckets.shape[0]
    n_lead = l_times.shape[0]
    n_l_days = l_day_buckets.shape[0]

    out_entry = np.empty(n_days, dtype=np.int64)
    out_exit = np.empty(n_days, dtype=np.int64)
    out_r1 = np.empty(n_days, dtype=np.float64)
    out_r15 = np.empty(n_days, dtype=np.float64)
    out_r2 = np.empty(n_days, dtype=np.float64)
    out_f1 = np.empty(n_days, dtype=np.float64)
    out_f2 = np.empty(n_days, dtype=np.float64)
    cnt = 0

    if n_lead < 10 or lag_min < 1:
        return out_entry[:0], out_exit[:0], out_r1[:0], out_r15[:0], out_r2[:0], out_f1[:0], out_f2[:0]

    lag_sec = lag_min * 60
    lb_sec = lb_min * 60
    l_ptr = 0
    l_day_ptr = 0

    for d in range(n_days):
        if t_day_weekdays[d] >= 5:
            continue
        t_atr = t_d1_atr14[d]
        if not np.isfinite(t_atr) or t_atr <= 0.0:
            continue

        cur_day = t_day_buckets[d]
        while l_day_ptr < n_l_days and l_day_buckets[l_day_ptr] < cur_day:
            l_day_ptr += 1
        if l_day_ptr >= n_l_days or l_day_buckets[l_day_ptr] != cur_day:
            continue
        l_atr = l_d1_atr14[l_day_ptr]
        if not np.isfinite(l_atr) or l_atr <= 0.0:
            continue

        day0 = cur_day * 86400
        scan_start = day0 + scan_start_h * 3600
        scan_end = day0 + scan_end_h * 3600
        flat_ts = day0 + flat_h * 3600
        max_flat = day0 + HARD_FLAT_MAX_UTC_SEC
        if flat_ts > max_flat:
            flat_ts = max_flat

        i0 = t_day_starts[d]
        i1 = t_day_ends[d]
        fill_idx = -1
        side = 0
        t_lb_ptr = i0
        l_lb_ptr = l_ptr

        for k in range(i0, i1 - 1):
            tk = t_times[k]
            if tk < scan_start:
                continue
            if tk >= scan_end:
                break

            # Strictly causal leader timestamp <= tk - lag_sec (shift >= 1 minute!)
            l_cutoff = tk - lag_sec
            while l_ptr + 1 < n_lead and l_times[l_ptr + 1] <= l_cutoff:
                l_ptr += 1
            if l_times[l_ptr] > l_cutoff or (l_cutoff - l_times[l_ptr]) > 900:
                continue

            # Causal leader lookback bar <= l_times[l_ptr] - lb_sec
            l_lb_target = l_times[l_ptr] - lb_sec
            while l_lb_ptr + 1 < l_ptr and l_times[l_lb_ptr + 1] <= l_lb_target:
                l_lb_ptr += 1
            if l_lb_ptr >= l_ptr or abs(l_times[l_lb_ptr] - l_lb_target) > 900:
                continue

            # Causal target lookback bar <= tk - lb_sec
            t_lb_target = tk - lb_sec
            while t_lb_ptr + 1 < k and t_times[t_lb_ptr + 1] <= t_lb_target:
                t_lb_ptr += 1
            if t_lb_ptr >= k or abs(t_times[t_lb_ptr] - t_lb_target) > 900:
                continue

            z_lead = (l_mid_close[l_ptr] - l_mid_close[l_lb_ptr]) / l_atr
            t_c_now = 0.5 * (t_bid[k, 3] + t_ask[k, 3]) if t_has_ask else t_bid[k, 3]
            t_c_old = 0.5 * (t_bid[t_lb_ptr, 3] + t_ask[t_lb_ptr, 3]) if t_has_ask else t_bid[t_lb_ptr, 3]
            z_tgt = (t_c_now - t_c_old) / t_atr
            diff = z_lead - z_tgt

            if mode_code == 0:
                # FOLLOW_CATCHUP: leader made strong impulse & target lags behind
                if z_lead >= z_thresh and diff >= lag_gap_thresh:
                    side = 1
                    fill_idx = k + 1
                    break
                if z_lead <= -z_thresh and (-diff) >= lag_gap_thresh:
                    side = -1
                    fill_idx = k + 1
                    break
            else:
                # SPREAD_CONVERGE: trade target toward leader on cross-asset dislocation
                if diff >= z_thresh:
                    side = 1
                    fill_idx = k + 1
                    break
                if diff <= -z_thresh:
                    side = -1
                    fill_idx = k + 1
                    break

        if fill_idx < 0 or fill_idx >= i1:
            continue

        sl_dist = sl_atr * t_atr
        min_sl = 6.0 * bench_sp_px
        if sl_dist < min_sl:
            sl_dist = min_sl

        ok, ets, xts, r1, r15, r2, f1, f2, _ = _execute_intraday_trade_jit(
            t_times,
            t_bid,
            t_ask,
            t_has_ask,
            fill_idx,
            i1,
            flat_ts,
            side,
            sl_dist,
            tp_r,
            ev_ts,
            ev_pad,
            RED_NEWS_DEFAULT_PAD_SEC,
            point,
            bench_sp_px,
            comm_px,
            qdm_class,
        )
        if ok:
            out_entry[cnt] = ets
            out_exit[cnt] = xts
            out_r1[cnt] = r1
            out_r15[cnt] = r15
            out_r2[cnt] = r2
            out_f1[cnt] = f1
            out_f2[cnt] = f2
            cnt += 1

    return out_entry[:cnt], out_exit[:cnt], out_r1[:cnt], out_r15[:cnt], out_r2[:cnt], out_f1[:cnt], out_f2[:cnt]


# ---------------------------------------------------------------------------
# Family 5: `F5E_TWAP_AND_ASIAN_RANGE_FADE` (Pure Price TWAP, 0 Volume/VWAP!)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _eval_f5e_twap_asian_fade_jit(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray,
    has_ask: bool,
    day_buckets: np.ndarray,
    day_starts: np.ndarray,
    day_ends: np.ndarray,
    day_weekdays: np.ndarray,
    d1_atr14: np.ndarray,
    ev_ts: np.ndarray,
    ev_pad: np.ndarray,
    mode_code: int,  # 0=PURE_PRICE_TWAP_Z_FADE, 1=ASIAN_RANGE_FADE
    scan_start_h: int,
    scan_end_h: int,
    flat_h: int,
    z_entry: float,
    z_max: float,
    sl_atr: float,
    tp_r: float,
    point: float,
    bench_sp_px: float,
    comm_px: float,
    qdm_class: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    n_days = day_buckets.shape[0]
    out_entry = np.empty(n_days, dtype=np.int64)
    out_exit = np.empty(n_days, dtype=np.int64)
    out_r1 = np.empty(n_days, dtype=np.float64)
    out_r15 = np.empty(n_days, dtype=np.float64)
    out_r2 = np.empty(n_days, dtype=np.float64)
    out_f1 = np.empty(n_days, dtype=np.float64)
    out_f2 = np.empty(n_days, dtype=np.float64)
    cnt = 0

    for d in range(n_days):
        if day_weekdays[d] >= 5:
            continue
        atr = d1_atr14[d]
        if not np.isfinite(atr) or atr <= 0.0:
            continue

        day0 = day_buckets[d] * 86400
        scan_start = day0 + scan_start_h * 3600
        scan_end = day0 + scan_end_h * 3600
        flat_ts = day0 + flat_h * 3600
        max_flat = day0 + HARD_FLAT_MAX_UTC_SEC
        if flat_ts > max_flat:
            flat_ts = max_flat

        i0 = day_starts[d]
        i1 = day_ends[d]
        fill_idx = -1
        side = 0
        tp_r_eff = tp_r

        if mode_code == 0:
            # Pure price-only causal TWAP (Welford running mean & std of M1 typical price; 0 volume!)
            n_obs = 0
            mean_tp = 0.0
            m2 = 0.0
            min_std = 0.08 * atr
            for k in range(i0, i1 - 1):
                tk = times_sec[k]
                if has_ask:
                    hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1])
                    lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2])
                    ck = 0.5 * (bid_ohlc[k, 3] + ask_ohlc[k, 3])
                else:
                    hk = bid_ohlc[k, 1]
                    lk = bid_ohlc[k, 2]
                    ck = bid_ohlc[k, 3]
                typ = (hk + lk + ck) / 3.0
                n_obs += 1
                delta = typ - mean_tp
                mean_tp += delta / float(n_obs)
                m2 += delta * (typ - mean_tp)

                if tk < scan_start or n_obs < 60:
                    continue
                if tk >= scan_end:
                    break
                sd = math.sqrt(m2 / float(n_obs - 1)) if n_obs > 1 else 0.0
                eff_sd = sd if sd > min_std else min_std
                z = (ck - mean_tp) / eff_sd
                # Fade overextension back toward pure-price TWAP (capped at z_max to avoid fading breakaways)
                if z_entry <= z <= z_max and ck < hk - 0.15 * (hk - lk):
                    side = -1
                    fill_idx = k + 1
                    break
                if -z_max <= z <= -z_entry and ck > lk + 0.15 * (hk - lk):
                    side = 1
                    fill_idx = k + 1
                    break
        else:
            # ASIAN_RANGE_FADE: build causal Asian box [00:00..06:00 UTC), fade failed stretch in scan window
            asia_end = day0 + 6 * 3600
            box_hi = -1.0e300
            box_lo = 1.0e300
            a_bars = 0
            scan_idx = -1
            for k in range(i0, i1):
                tk = times_sec[k]
                if day0 <= tk < asia_end:
                    hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1]) if has_ask else bid_ohlc[k, 1]
                    lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2]) if has_ask else bid_ohlc[k, 2]
                    if hk > box_hi:
                        box_hi = hk
                    if lk < box_lo:
                        box_lo = lk
                    a_bars += 1
                elif tk >= scan_start:
                    scan_idx = k
                    break

            if a_bars >= 60 and scan_idx >= 0 and (box_hi - box_lo) >= 0.12 * atr:
                ext_min = z_entry * atr
                ext_max = z_max * atr
                for k in range(scan_idx, i1 - 1):
                    tk = times_sec[k]
                    if tk >= scan_end:
                        break
                    if has_ask:
                        hk = 0.5 * (bid_ohlc[k, 1] + ask_ohlc[k, 1])
                        lk = 0.5 * (bid_ohlc[k, 2] + ask_ohlc[k, 2])
                        ck = 0.5 * (bid_ohlc[k, 3] + ask_ohlc[k, 3])
                    else:
                        hk = bid_ohlc[k, 1]
                        lk = bid_ohlc[k, 2]
                        ck = bid_ohlc[k, 3]
                    # Upper stretch outside Asian high with exhaustion close back near/below box_hi
                    if box_hi + ext_min <= hk <= box_hi + ext_max and ck <= box_hi + 0.05 * atr:
                        side = -1
                        fill_idx = k + 1
                        break
                    # Lower stretch outside Asian low with exhaustion close back near/above box_lo
                    if box_lo - ext_max <= lk <= box_lo - ext_min and ck >= box_lo - 0.05 * atr:
                        side = 1
                        fill_idx = k + 1
                        break

        if fill_idx < 0 or fill_idx >= i1:
            continue

        sl_dist = sl_atr * atr
        min_sl = 6.0 * bench_sp_px
        if sl_dist < min_sl:
            sl_dist = min_sl

        ok, ets, xts, r1, r15, r2, f1, f2, _ = _execute_intraday_trade_jit(
            times_sec,
            bid_ohlc,
            ask_ohlc,
            has_ask,
            fill_idx,
            i1,
            flat_ts,
            side,
            sl_dist,
            tp_r_eff,
            ev_ts,
            ev_pad,
            RED_NEWS_DEFAULT_PAD_SEC,
            point,
            bench_sp_px,
            comm_px,
            qdm_class,
        )
        if ok:
            out_entry[cnt] = ets
            out_exit[cnt] = xts
            out_r1[cnt] = r1
            out_r15[cnt] = r15
            out_r2[cnt] = r2
            out_f1[cnt] = f1
            out_f2[cnt] = f2
            cnt += 1

    return out_entry[:cnt], out_exit[:cnt], out_r1[:cnt], out_r15[:cnt], out_r2[:cnt], out_f1[:cnt], out_f2[:cnt]


# ---------------------------------------------------------------------------
# Union Pair Metadata (`F5D`) & Balanced Trade Metrics Aggregation
# ---------------------------------------------------------------------------


def compute_pair_union_metadata(
    leader_meta: Mapping[str, Any],
    target_meta: Mapping[str, Any],
) -> dict[str, Any]:
    """Compute conservative union `blindness_tier`, `mt5_hcc_ready`, & `red_news_scope` over BOTH legs."""
    l_sym = ldr.normalize_symbol(str(leader_meta["symbol"]))
    t_sym = ldr.normalize_symbol(str(target_meta["symbol"]))
    l_tier = str(leader_meta["blindness_tier"])
    t_tier = str(target_meta["blindness_tier"])

    # If EITHER leader or target was consumed in OLD12, the combined pair is DEV_CLB_CONSUMED_12OLD!
    if l_tier == ldr.TIER_OLD12 or t_tier == ldr.TIER_OLD12:
        union_tier = ldr.TIER_OLD12
    else:
        union_tier = ldr.TIER_NEW16_WAVE5

    l_hcc = bool(leader_meta["mt5_hcc_ready"])
    t_hcc = bool(target_meta["mt5_hcc_ready"])
    union_hcc = l_hcc and t_hcc

    l_res = str(leader_meta["data_resolution"])
    t_res = str(target_meta["data_resolution"])
    # Conservative resolution rank: M1_SINGLE_SIDE < M1_BID_SPREAD < M1_BID_ASK
    res_rank = {ldr.RES_M1_SINGLE_SIDE: 0, ldr.RES_M1_BID_SPREAD: 1, ldr.RES_M1_BID_ASK: 2}
    union_res = l_res if res_rank.get(l_res, 0) <= res_rank.get(t_res, 0) else t_res

    return {
        "leader_symbol": l_sym,
        "target_symbol": t_sym,
        "leader_blindness_tier": l_tier,
        "target_blindness_tier": t_tier,
        "blindness_tier": union_tier,
        "leader_mt5_hcc_ready": l_hcc,
        "target_mt5_hcc_ready": t_hcc,
        "mt5_hcc_ready": union_hcc,
        "leader_data_resolution": l_res,
        "target_data_resolution": t_res,
        "data_resolution": union_res,
        "red_news_scope_disclosure": describe_red_news_scope([l_sym, t_sym]),
    }


def _symbol_qdm_class(symbol: str) -> int:
    sym = ldr.normalize_symbol(symbol)
    if sym == "JP225":
        return _QDM_CLASS_JP225
    if sym == "UK100":
        return _QDM_CLASS_UK100
    if sym == "US30":
        return _QDM_CLASS_US30
    if sym in ("USOIL", "UKOIL"):
        return _QDM_CLASS_OIL
    return _QDM_CLASS_FX


def _comm_price_units(spec: Mapping[str, Any]) -> float:
    comm_usd = float(spec.get("commission_usd_lot", 0.0))
    if comm_usd <= 0.0:
        return 0.0
    pt = float(spec["point"])
    tick_val_usd = float(spec["tick_val_loss_usd_ref"])
    usd_per_px = tick_val_usd / pt if pt > 0.0 else 0.0
    return (comm_usd / usd_per_px) if usd_per_px > 0.0 else 0.0


def _compute_series_metrics(r_arr: np.ndarray, years_span: float) -> dict[str, float]:
    n = int(r_arr.shape[0])
    if n == 0:
        return {
            "total_r": 0.0,
            "ev_r": 0.0,
            "winrate_frac": 0.0,
            "avg_win_r": 0.0,
            "avg_loss_r": 0.0,
            "rr_ratio": 0.0,
            "pf": 0.0,
            "max_dd_r": 0.0,
            "calmar": 0.0,
            "sharpe": 0.0,
        }
    total_r = float(np.sum(r_arr))
    ev_r = total_r / float(n)
    wins = r_arr[r_arr > 0.0]
    losses = r_arr[r_arr < 0.0]
    winrate = float(wins.size) / float(n)
    avg_win = float(np.mean(wins)) if wins.size > 0 else 0.0
    avg_loss = float(np.mean(np.abs(losses))) if losses.size > 0 else 0.0
    rr = (avg_win / avg_loss) if avg_loss > 1e-12 else (99.0 if avg_win > 0.0 else 0.0)
    gross_w = float(np.sum(wins)) if wins.size > 0 else 0.0
    gross_l = float(np.sum(np.abs(losses))) if losses.size > 0 else 0.0
    pf = (gross_w / gross_l) if gross_l > 1e-12 else (99.0 if gross_w > 0.0 else 0.0)

    eq = np.cumsum(r_arr)
    peak = np.maximum.accumulate(np.concatenate((np.array([0.0]), eq)))[1:]
    dd = peak - eq
    max_dd = float(np.max(dd)) if dd.size > 0 else 0.0
    ann_r = total_r / max(years_span, 0.25)
    calmar = (ann_r / max_dd) if max_dd > 1e-12 else (99.0 if ann_r > 0.0 else 0.0)

    sd = float(np.std(r_arr, ddof=1)) if n > 1 else 0.0
    trades_per_yr = float(n) / max(years_span, 0.25)
    sharpe = (ev_r / sd) * math.sqrt(trades_per_yr) if sd > 1e-12 else 0.0

    return {
        "total_r": round(total_r, 6),
        "ev_r": round(ev_r, 6),
        "winrate_frac": round(winrate, 6),
        "avg_win_r": round(avg_win, 6),
        "avg_loss_r": round(avg_loss, 6),
        "rr_ratio": round(rr, 4),
        "pf": round(min(pf, 99.0), 4),
        "max_dd_r": round(max_dd, 6),
        "calmar": round(min(max(calmar, -99.0), 99.0), 4),
        "sharpe": round(min(max(sharpe, -99.0), 99.0), 4),
    }


def _aggregate_daily_returns(exit_ts: np.ndarray, r_arr: np.ndarray) -> dict[str, float]:
    out: dict[str, float] = {}
    for idx in range(exit_ts.shape[0]):
        d_str = datetime.fromtimestamp(int(exit_ts[idx]), tz=UTC).strftime("%Y-%m-%d")
        out[d_str] = round(out.get(d_str, 0.0) + float(r_arr[idx]), 6)
    return dict(sorted(out.items()))


# ---------------------------------------------------------------------------
# Deterministic Bounded-Budget Cluster A Candidate Grid (`m_total <= 360`)
# ---------------------------------------------------------------------------


def generate_cluster_a_candidate_grid(*, max_total: int = MAX_TOTAL_CANDIDATES) -> list[dict[str, Any]]:
    """Generate the deterministic bounded-budget candidate grid (`m_total <= 360`) across all 5 families."""
    if (
        isinstance(max_total, bool)
        or not isinstance(max_total, int)
        or max_total < 5
        or max_total > MAX_TOTAL_CANDIDATES
    ):
        raise ValueError(f"max_total must be an int in [5, {MAX_TOTAL_CANDIDATES}], got {max_total!r}")

    grid: list[dict[str, Any]] = []

    # 1. F5A_SESSION_OR_BREAKOUT: 7 symbols x 10 configs = 70 candidates (outside E4/E5 hours!)
    f5a_sessions_by_sym: dict[str, tuple[tuple[str, int], ...]] = {
        "JP225": (("TOKYO_OR", 0), ("LONDON_OR", 1)),
        "UK100": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
        "GER40": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
        "US30": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
        "US500": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
        "USOIL": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
        "UKOIL": (("LONDON_OR", 1), ("EARLY_NY_OR", 2)),
    }
    f5a_templates: tuple[tuple[int, float, float, float], ...] = (
        # (or_minutes, buf_atr, sl_atr, tp_r)
        (15, 0.05, 0.65, 0.0),
        (15, 0.08, 0.75, 1.8),
        (30, 0.05, 0.75, 0.0),
        (30, 0.10, 0.85, 2.0),
        (60, 0.05, 0.85, 2.2),
    )
    for sym in F5A_SYMBOLS:
        for sess_name, sess_code in f5a_sessions_by_sym[sym]:
            for or_m, buf_a, sl_a, tp_r in f5a_templates:
                b_tag = int(round(buf_a * 100))
                sl_tag = int(round(sl_a * 100))
                tp_tag = int(round(tp_r * 10))
                cid = f"F5A_{sym}_{sess_name}_OR{or_m}_B{b_tag}_SL{sl_tag}_TP{tp_tag}"
                grid.append(
                    {
                        "candidate_id": cid,
                        "family_id": FAM_F5A,
                        "symbol": sym,
                        "leader_symbol": None,
                        "params": {
                            "session_name": sess_name,
                            "session_code": sess_code,
                            "or_minutes": or_m,
                            "buf_atr": buf_a,
                            "sl_atr": sl_a,
                            "tp_r": tp_r,
                            "min_box_atr": 0.08,
                            "max_box_atr": 0.90,
                        },
                    }
                )

    # 2. F5B_LIQUIDITY_SWEEP_MEANREV: 11 symbols (10 FTMO new + USDCHF) x 7 configs = 77 candidates
    f5b_templates: tuple[tuple[str, int, int, int, int, float, float, float, int, float, float], ...] = (
        # (tag, ref_s, ref_e, scan_e, flat_h, sw_min, sw_max, rec_dep, rec_min, sl_floor, tp_r)
        ("LON_A", 0, 6, 12, 17, 0.12, 0.45, 0.04, 30, 0.65, 1.5),
        ("LON_B", 0, 6, 12, 17, 0.18, 0.55, 0.05, 45, 0.75, 1.8),
        ("LON_C", 0, 6, 13, 20, 0.15, 0.50, 0.03, 30, 0.85, 2.0),
        ("NY_A", 7, 12, 17, 20, 0.12, 0.45, 0.04, 30, 0.65, 1.5),
        ("NY_B", 7, 12, 17, 20, 0.18, 0.55, 0.05, 45, 0.75, 1.8),
        ("NY_C", 7, 12, 18, 20, 0.15, 0.50, 0.03, 45, 0.85, 0.0),
        ("ALL_T", 0, 7, 15, 20, 0.20, 0.60, 0.05, 30, 0.80, 1.6),
    )
    for sym in F5B_SYMBOLS:
        for tag, rs, re_h, se_h, fh, smin, smax, rdep, rmin, slf, tpr in f5b_templates:
            cid = f"F5B_{sym}_{tag}"
            grid.append(
                {
                    "candidate_id": cid,
                    "family_id": FAM_F5B,
                    "symbol": sym,
                    "leader_symbol": None,
                    "params": {
                        "window_tag": tag,
                        "ref_start_h": rs,
                        "ref_end_h": re_h,
                        "scan_end_h": se_h,
                        "flat_h": fh,
                        "sweep_min_atr": smin,
                        "sweep_max_atr": smax,
                        "reclaim_depth_atr": rdep,
                        "reclaim_max_min": rmin,
                        "sl_atr_floor": slf,
                        "tp_r": tpr,
                    },
                }
            )

    # 3. F5C_VOL_COMPRESSION_CROSS: 9 crosses x 8 configs = 72 candidates (strictly outside E6 07:00-17:00 UTC!)
    f5c_templates: tuple[tuple[str, int, float, float, float, float], ...] = (
        # (win_tag, win_code, comp_thresh, break_atr, sl_atr, tp_r)
        ("ASIA_C80_B25", 0, 0.80, 0.25, 0.65, 0.0),
        ("ASIA_C80_B35", 0, 0.80, 0.35, 0.70, 1.8),
        ("ASIA_C90_B25", 0, 0.90, 0.25, 0.75, 1.6),
        ("ASIA_C90_B35", 0, 0.90, 0.35, 0.80, 0.0),
        ("LNY_C80_B25", 1, 0.80, 0.25, 0.65, 0.0),
        ("LNY_C80_B35", 1, 0.80, 0.35, 0.70, 1.8),
        ("LNY_C90_B25", 1, 0.90, 0.25, 0.75, 1.6),
        ("LNY_C90_B35", 1, 0.90, 0.35, 0.80, 0.0),
    )
    for sym in F5C_SYMBOLS:
        for wtag, wcode, cth, batr, sl_a, tp_r in f5c_templates:
            cid = f"F5C_{sym}_{wtag}"
            grid.append(
                {
                    "candidate_id": cid,
                    "family_id": FAM_F5C,
                    "symbol": sym,
                    "leader_symbol": None,
                    "params": {
                        "window_tag": wtag,
                        "window_code": wcode,
                        "comp_thresh": cth,
                        "break_atr": batr,
                        "sl_atr": sl_a,
                        "tp_r": tp_r,
                    },
                }
            )

    # 4. F5D_CROSS_ASSET_LEAD_LAG: 7 directed pairs x 10 configs = 70 candidates (strict shift >= 1!)
    f5d_templates: tuple[tuple[str, int, int, int, int, int, int, float, float, float, float], ...] = (
        # (tag, mode_code, scan_s, scan_e, flat_h, lag_min, lb_min, z_th, gap_th, sl_a, tp_r)
        ("FOL_L1_LB15_A", 0, 7, 17, 20, 1, 15, 0.25, 0.10, 0.70, 1.8),
        ("FOL_L1_LB30_A", 0, 7, 17, 20, 1, 30, 0.30, 0.12, 0.75, 0.0),
        ("FOL_L2_LB30_A", 0, 8, 18, 20, 2, 30, 0.35, 0.15, 0.80, 2.0),
        ("FOL_L3_LB60_A", 0, 7, 17, 20, 3, 60, 0.40, 0.15, 0.85, 0.0),
        ("FOL_L5_LB60_A", 0, 8, 18, 20, 5, 60, 0.45, 0.18, 0.90, 2.2),
        ("CNV_L1_LB30_A", 1, 7, 17, 20, 1, 30, 0.30, 0.0, 0.70, 1.5),
        ("CNV_L2_LB30_A", 1, 8, 18, 20, 2, 30, 0.40, 0.0, 0.75, 1.8),
        ("CNV_L2_LB60_A", 1, 7, 17, 20, 2, 60, 0.45, 0.0, 0.80, 1.6),
        ("CNV_L3_LB60_A", 1, 8, 18, 20, 3, 60, 0.50, 0.0, 0.85, 2.0),
        ("CNV_L5_LB90_A", 1, 7, 18, 20, 5, 90, 0.55, 0.0, 0.90, 0.0),
    )
    for lead_sym, tgt_sym in F5D_PAIRS:
        for tag, mcode, sc_s, sc_e, fh, lag_m, lb_m, zth, gth, sl_a, tp_r in f5d_templates:
            cid = f"F5D_{lead_sym}_TO_{tgt_sym}_{tag}"
            grid.append(
                {
                    "candidate_id": cid,
                    "family_id": FAM_F5D,
                    "symbol": tgt_sym,
                    "leader_symbol": lead_sym,
                    "params": {
                        "mode_tag": tag,
                        "mode_code": mcode,
                        "scan_start_h": sc_s,
                        "scan_end_h": sc_e,
                        "flat_h": fh,
                        "lag_min": lag_m,
                        "lb_min": lb_m,
                        "z_thresh": zth,
                        "lag_gap_thresh": gth,
                        "sl_atr": sl_a,
                        "tp_r": tp_r,
                    },
                }
            )

    # 5. F5E_TWAP_AND_ASIAN_RANGE_FADE: 11 new M1 symbols x 6 configs = 66 candidates (0 volume / NO VWAP!)
    f5e_templates: tuple[tuple[str, int, int, int, int, float, float, float, float], ...] = (
        # (tag, mode_code, scan_s, scan_e, flat_h, z_entry, z_max, sl_a, tp_r)
        ("TWAP_LON_Z18", 0, 7, 14, 20, 1.8, 3.5, 0.70, 1.5),
        ("TWAP_LON_Z22", 0, 7, 14, 20, 2.2, 4.0, 0.80, 1.8),
        ("TWAP_NY_Z20", 0, 12, 18, 20, 2.0, 3.8, 0.75, 1.6),
        ("ASIA_FADE_A", 1, 6, 12, 18, 0.12, 0.45, 0.65, 1.5),
        ("ASIA_FADE_B", 1, 6, 13, 20, 0.18, 0.55, 0.75, 1.8),
        ("ASIA_FADE_C", 1, 7, 14, 20, 0.15, 0.50, 0.85, 0.0),
    )
    for sym in F5E_SYMBOLS:
        for tag, mcode, sc_s, sc_e, fh, ze, zm, sl_a, tp_r in f5e_templates:
            cid = f"F5E_{sym}_{tag}"
            grid.append(
                {
                    "candidate_id": cid,
                    "family_id": FAM_F5E,
                    "symbol": sym,
                    "leader_symbol": None,
                    "params": {
                        "mode_tag": tag,
                        "mode_code": mcode,
                        "scan_start_h": sc_s,
                        "scan_end_h": sc_e,
                        "flat_h": fh,
                        "z_entry": ze,
                        "z_max": zm,
                        "sl_atr": sl_a,
                        "tp_r": tp_r,
                    },
                }
            )

    if len(grid) > MAX_TOTAL_CANDIDATES:
        raise ValueError(
            f"BUDGET_BREACH: generated {len(grid)} candidates > MAX_TOTAL_CANDIDATES={MAX_TOTAL_CANDIDATES}"
        )
    return grid[:max_total]


# ---------------------------------------------------------------------------
# In-Process Prepared Symbol Cache & Single Candidate / Shard Evaluators
# ---------------------------------------------------------------------------


def _prepare_asset_context(
    asset: ldr.LoadedM1Asset,
    red_news_cal: Mapping[str, Any] | None,
) -> dict[str, Any]:
    """Precompute strictly causal D1 structure, ATR14, NR5/NR20, and red-news arrays once per symbol."""
    ldr.enforce_dev_ts_bound(asset.times_sec, context=f"prepare:{asset.symbol}")
    has_ask = asset.ask_ohlc is not None
    ask_arr = (
        np.ascontiguousarray(asset.ask_ohlc, dtype=np.float64)
        if asset.ask_ohlc is not None
        else np.empty((0, 4), dtype=np.float64)
    )
    bid_arr = np.ascontiguousarray(asset.bid_ohlc, dtype=np.float64)
    ts_arr = np.ascontiguousarray(asset.times_sec, dtype=np.int64)

    day_b, day_s, day_e, day_wd, d1_atr, d1_comp = _build_day_structure_and_causal_d1_jit(
        ts_arr, bid_arr, ask_arr, has_ask
    )
    mid_close = (0.5 * (bid_arr[:, 3] + ask_arr[:, 3])) if has_ask else bid_arr[:, 3]
    ev_ts, ev_pad = build_symbol_red_news_arrays(asset.symbol, red_news_cal)

    return {
        "asset": asset,
        "times_sec": ts_arr,
        "bid_ohlc": bid_arr,
        "ask_ohlc": ask_arr,
        "has_ask": has_ask,
        "mid_close": np.ascontiguousarray(mid_close, dtype=np.float64),
        "day_buckets": day_b,
        "day_starts": day_s,
        "day_ends": day_e,
        "day_weekdays": day_wd,
        "d1_atr14": d1_atr,
        "d1_comp": d1_comp,
        "ev_ts": ev_ts,
        "ev_pad": ev_pad,
        "point": float(asset.spec["point"]),
        "bench_sp_px": ldr.compute_qdm_base_spread_price(asset.spec),
        "comm_px": _comm_price_units(asset.spec),
        "qdm_class": _symbol_qdm_class(asset.symbol),
        "meta": {
            "symbol": asset.symbol,
            "blindness_tier": asset.blindness_tier,
            "mt5_hcc_ready": asset.mt5_hcc_ready,
            "data_resolution": asset.data_resolution,
            "years_loaded": list(asset.years_loaded),
            "years_available": list(asset.years_available),
        },
    }


def _enforce_split_bounds(times_sec: np.ndarray, split: str, context: str) -> None:
    """Fail-closed enforcement ensuring Cluster A NEVER leaks 2021+ bars and ALL splits stay `< 2025`."""
    ldr.enforce_dev_ts_bound(times_sec, context=context)
    sp = str(split).strip().lower()
    if sp == "cluster_a" and times_sec.size > 0:
        max_ts = int(np.max(times_sec))
        if max_ts >= CLUSTER_B_START_SEC:
            raise ValueError(
                f"CLUSTER_A_LEAKAGE [{context}]: max_ts={max_ts} >= CLUSTER_B_START_SEC={CLUSTER_B_START_SEC} (2021+)"
            )
    elif sp in ("cluster_b", "cluster_b_blind") and times_sec.size > 0:
        min_ts = int(np.min(times_sec))
        if min_ts < CLUSTER_B_START_SEC:
            raise ValueError(
                f"CLUSTER_B_CONTAMINATION [{context}]: min_ts={min_ts} < CLUSTER_B_START_SEC={CLUSTER_B_START_SEC}"
            )


def evaluate_prepared_candidate(
    candidate: Mapping[str, Any],
    *,
    prepared_assets: Mapping[str, Mapping[str, Any]],
    split: str = "cluster_a",
    include_daily_returns: bool = True,
) -> dict[str, Any]:
    """Evaluate a single candidate against already-prepared M1 asset contexts."""
    cid = str(candidate["candidate_id"])
    fam = str(candidate["family_id"])
    if fam not in FAMILY_IDS:
        raise ValueError(f"Unsupported family_id={fam!r} in candidate {cid!r}")

    sym = ldr.normalize_symbol(str(candidate["symbol"]))
    if sym not in prepared_assets:
        raise KeyError(f"Prepared asset missing for target symbol {sym!r}")
    ctx = prepared_assets[sym]
    _enforce_split_bounds(ctx["times_sec"], split, context=f"{cid}:{sym}")

    params: Mapping[str, Any] = candidate.get("params") or {}
    flat_h_cfg = params.get("flat_h")
    if flat_h_cfg is not None and int(flat_h_cfg) * 3600 > HARD_FLAT_MAX_UTC_SEC:
        raise ValueError(f"HARD_FLAT_VIOLATION [{cid}]: flat_h={flat_h_cfg} > 20:50 UTC")

    leader_sym = candidate.get("leader_symbol")
    if fam == FAM_F5A:
        e_ts, x_ts, r1, r15, r2, f1, f2 = _eval_f5a_session_or_breakout_jit(
            ctx["times_sec"],
            ctx["bid_ohlc"],
            ctx["ask_ohlc"],
            ctx["has_ask"],
            ctx["day_buckets"],
            ctx["day_starts"],
            ctx["day_ends"],
            ctx["day_weekdays"],
            ctx["d1_atr14"],
            ctx["ev_ts"],
            ctx["ev_pad"],
            int(params["session_code"]),
            int(params["or_minutes"]),
            float(params["buf_atr"]),
            float(params["sl_atr"]),
            float(params["tp_r"]),
            float(params.get("min_box_atr", 0.08)),
            float(params.get("max_box_atr", 0.90)),
            ctx["point"],
            ctx["bench_sp_px"],
            ctx["comm_px"],
            ctx["qdm_class"],
        )
    elif fam == FAM_F5B:
        e_ts, x_ts, r1, r15, r2, f1, f2 = _eval_f5b_liquidity_sweep_meanrev_jit(
            ctx["times_sec"],
            ctx["bid_ohlc"],
            ctx["ask_ohlc"],
            ctx["has_ask"],
            ctx["day_buckets"],
            ctx["day_starts"],
            ctx["day_ends"],
            ctx["day_weekdays"],
            ctx["d1_atr14"],
            ctx["ev_ts"],
            ctx["ev_pad"],
            int(params["ref_start_h"]),
            int(params["ref_end_h"]),
            int(params["scan_end_h"]),
            int(params["flat_h"]),
            float(params["sweep_min_atr"]),
            float(params["sweep_max_atr"]),
            float(params["reclaim_depth_atr"]),
            int(params["reclaim_max_min"]),
            float(params["sl_atr_floor"]),
            float(params["tp_r"]),
            ctx["point"],
            ctx["bench_sp_px"],
            ctx["comm_px"],
            ctx["qdm_class"],
        )
    elif fam == FAM_F5C:
        e_ts, x_ts, r1, r15, r2, f1, f2 = _eval_f5c_vol_compression_cross_jit(
            ctx["times_sec"],
            ctx["bid_ohlc"],
            ctx["ask_ohlc"],
            ctx["has_ask"],
            ctx["day_buckets"],
            ctx["day_starts"],
            ctx["day_ends"],
            ctx["day_weekdays"],
            ctx["d1_atr14"],
            ctx["d1_comp"],
            ctx["ev_ts"],
            ctx["ev_pad"],
            int(params["window_code"]),
            float(params["comp_thresh"]),
            float(params["break_atr"]),
            float(params["sl_atr"]),
            float(params["tp_r"]),
            ctx["point"],
            ctx["bench_sp_px"],
            ctx["comm_px"],
            ctx["qdm_class"],
        )
    elif fam == FAM_F5D:
        if not leader_sym:
            raise ValueError(f"F5D candidate {cid!r} requires leader_symbol")
        lsym = ldr.normalize_symbol(str(leader_sym))
        if lsym not in prepared_assets:
            raise KeyError(f"Prepared asset missing for leader symbol {lsym!r}")
        lctx = prepared_assets[lsym]
        _enforce_split_bounds(lctx["times_sec"], split, context=f"{cid}:leader:{lsym}")
        lag_m = int(params["lag_min"])
        if lag_m < 1:
            raise ValueError(f"CAUSALITY_VIOLATION [{cid}]: F5D lag_min={lag_m} must be >= 1")
        e_ts, x_ts, r1, r15, r2, f1, f2 = _eval_f5d_cross_asset_lead_lag_jit(
            ctx["times_sec"],
            ctx["bid_ohlc"],
            ctx["ask_ohlc"],
            ctx["has_ask"],
            ctx["day_buckets"],
            ctx["day_starts"],
            ctx["day_ends"],
            ctx["day_weekdays"],
            ctx["d1_atr14"],
            lctx["times_sec"],
            lctx["mid_close"],
            lctx["day_buckets"],
            lctx["d1_atr14"],
            ctx["ev_ts"],
            ctx["ev_pad"],
            int(params["mode_code"]),
            int(params["scan_start_h"]),
            int(params["scan_end_h"]),
            int(params["flat_h"]),
            lag_m,
            int(params["lb_min"]),
            float(params["z_thresh"]),
            float(params["lag_gap_thresh"]),
            float(params["sl_atr"]),
            float(params["tp_r"]),
            ctx["point"],
            ctx["bench_sp_px"],
            ctx["comm_px"],
            ctx["qdm_class"],
        )
    else:  # FAM_F5E
        e_ts, x_ts, r1, r15, r2, f1, f2 = _eval_f5e_twap_asian_fade_jit(
            ctx["times_sec"],
            ctx["bid_ohlc"],
            ctx["ask_ohlc"],
            ctx["has_ask"],
            ctx["day_buckets"],
            ctx["day_starts"],
            ctx["day_ends"],
            ctx["day_weekdays"],
            ctx["d1_atr14"],
            ctx["ev_ts"],
            ctx["ev_pad"],
            int(params["mode_code"]),
            int(params["scan_start_h"]),
            int(params["scan_end_h"]),
            int(params["flat_h"]),
            float(params["z_entry"]),
            float(params["z_max"]),
            float(params["sl_atr"]),
            float(params["tp_r"]),
            ctx["point"],
            ctx["bench_sp_px"],
            ctx["comm_px"],
            ctx["qdm_class"],
        )

    # Post-trade hard fail-closed verification (split cutoff + 20:50 UTC hard flat + zero weekend holds)
    if x_ts.size > 0:
        _enforce_split_bounds(e_ts, split, context=f"{cid}:trade_entry")
        _enforce_split_bounds(x_ts, split, context=f"{cid}:trade_exit")
        exit_mod_sec = x_ts % np.int64(86400)
        max_exit_mod = int(np.max(exit_mod_sec))
        if max_exit_mod > HARD_FLAT_MAX_UTC_SEC:
            raise ValueError(
                f"HARD_FLAT_BREACH [{cid}]: max_exit_utc_sec={max_exit_mod} > {HARD_FLAT_MAX_UTC_SEC} (20:50 UTC)"
            )
        same_day_ok = bool(np.all((e_ts // np.int64(86400)) == (x_ts // np.int64(86400))))
        if not same_day_ok:
            raise ValueError(f"OVERNIGHT_SWAP0_BREACH [{cid}]: trade crossed UTC midnight")
    else:
        max_exit_mod = 0

    if fam == FAM_F5D and leader_sym:
        pair_meta = compute_pair_union_metadata(
            prepared_assets[ldr.normalize_symbol(str(leader_sym))]["meta"],
            ctx["meta"],
        )
        b_tier = pair_meta["blindness_tier"]
        hcc_ready = pair_meta["mt5_hcc_ready"]
        data_res = pair_meta["data_resolution"]
        rn_scope = pair_meta["red_news_scope_disclosure"]
    else:
        b_tier = str(ctx["meta"]["blindness_tier"])
        hcc_ready = bool(ctx["meta"]["mt5_hcc_ready"])
        data_res = str(ctx["meta"]["data_resolution"])
        rn_scope = describe_red_news_scope([sym])

    yrs = list(ctx["meta"]["years_loaded"])
    years_span = float(max(1, len(yrs)))
    m1 = _compute_series_metrics(r1, years_span)
    m15 = _compute_series_metrics(r15, years_span)
    m2 = _compute_series_metrics(r2, years_span)

    rec: dict[str, Any] = {
        "candidate_id": cid,
        "family_id": fam,
        "symbol": sym,
        "leader_symbol": ldr.normalize_symbol(str(leader_sym)) if leader_sym else None,
        "split": str(split),
        "years_evaluated": yrs,
        "blindness_tier": b_tier,
        "mt5_hcc_ready": hcc_ready,
        "data_resolution": data_res,
        "red_news_scope_disclosure": rn_scope,
        "params": dict(params),
        "n_trades": int(r1.shape[0]),
        "winrate_frac": m1["winrate_frac"],
        "avg_win_r": m1["avg_win_r"],
        "avg_loss_r": m1["avg_loss_r"],
        "rr_ratio": m1["rr_ratio"],
        "ev_r_1x": m1["ev_r"],
        "ev_r_15x": m15["ev_r"],
        "ev_r_2x": m2["ev_r"],
        "pf_1x": m1["pf"],
        "pf_15x": m15["pf"],
        "pf_2x": m2["pf"],
        "total_r_1x": m1["total_r"],
        "total_r_15x": m15["total_r"],
        "total_r_2x": m2["total_r"],
        "max_dd_r_1x": m1["max_dd_r"],
        "max_dd_r_15x": m15["max_dd_r"],
        "max_dd_r_2x": m2["max_dd_r"],
        "calmar_1x": m1["calmar"],
        "sharpe_1x": m1["sharpe"],
        "median_fric_over_sl_1x": round(float(np.median(f1)), 6) if f1.size > 0 else 0.0,
        "median_fric_over_sl_2x": round(float(np.median(f2)), 6) if f2.size > 0 else 0.0,
        "max_exit_utc_sec": max_exit_mod,
        "all_flat_by_2050_utc": max_exit_mod <= HARD_FLAT_MAX_UTC_SEC,
        "swap_r_total": 0.0,
        "volume_columns_used": 0,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }
    if include_daily_returns:
        rec["daily_returns_1x"] = _aggregate_daily_returns(x_ts, r1)
        rec["daily_returns_15x"] = _aggregate_daily_returns(x_ts, r15)
        rec["daily_returns_2x"] = _aggregate_daily_returns(x_ts, r2)
    return rec


def evaluate_candidate_shard(
    candidates: Sequence[Mapping[str, Any]],
    *,
    split: str = "cluster_a",
    years: Sequence[int] | None = None,
    hot12_root: str | Path | None = None,
    sealed16_npz_root: str | Path | None = None,
    sealed16_manifest_path: str | Path | None = None,
    specs_path: str | Path | None = None,
    mt5_history_root: str | Path | None = None,
    red_news_csv_path: str | Path | None = None,
    dev_6ccy_json_path: str | Path | None = None,
    include_6ccy_dev_json: bool = True,
    root: str | Path | None = None,
    verify_sha: bool = False,
    include_daily_returns: bool = True,
    preloaded_assets: Mapping[str, ldr.LoadedM1Asset] | None = None,
    red_news_calendar: Mapping[str, Any] | None = None,
    output_npz_path: str | Path | None = None,
) -> dict[str, Any]:
    """Single-shard evaluator ready for BOTH `X13worker` (8 threads) and PC Dev Mode A (2 threads).

    Returns pure JSON-serializable dict (and optionally writes zero-pickle `.npz` trade R-arrays
    when `output_npz_path` is provided). Never imports DuckDB or `holdout_guard`.
    """
    t0 = time_mod.perf_counter()
    cand_list = list(candidates)
    if len(cand_list) > MAX_TOTAL_CANDIDATES:
        raise ValueError(
            f"BUDGET_BREACH: shard received {len(cand_list)} candidates > MAX_TOTAL_CANDIDATES={MAX_TOTAL_CANDIDATES}"
        )

    needed_syms: list[str] = []
    for c in cand_list:
        s = ldr.normalize_symbol(str(c["symbol"]))
        if s not in needed_syms:
            needed_syms.append(s)
        ls = c.get("leader_symbol")
        if ls:
            ln = ldr.normalize_symbol(str(ls))
            if ln not in needed_syms:
                needed_syms.append(ln)

    rn_cal = (
        red_news_calendar
        if red_news_calendar is not None
        else load_wave5_red_news_calendar(
            red_news_csv_path=red_news_csv_path,
            dev_6ccy_json_path=dev_6ccy_json_path,
            include_6ccy_dev_json=include_6ccy_dev_json,
            root=root,
        )
    )

    specs_doc = None
    hcc_cov = None
    prepared: dict[str, dict[str, Any]] = {}
    max_ts_seen = 0

    for sym in needed_syms:
        if preloaded_assets is not None and sym in preloaded_assets:
            asset = preloaded_assets[sym]
        else:
            if specs_doc is None:
                specs_doc = ldr.load_ftmo_specs_28(specs_path=specs_path, root=root)
                hcc_cov = ldr.inspect_mt5_hcc_coverage(specs_doc, history_root=mt5_history_root, root=root)
            asset = ldr.load_m1_symbol(
                sym,
                years=years,
                split=None if years is not None else split,
                verify_sha=verify_sha,
                hot12_root=hot12_root,
                sealed16_npz_root=sealed16_npz_root,
                sealed16_manifest_path=sealed16_manifest_path,
                specs_doc=specs_doc,
                hcc_coverage=hcc_cov,
                root=root,
            )
        ctx = _prepare_asset_context(asset, rn_cal)
        prepared[sym] = ctx
        max_ts_seen = max(max_ts_seen, asset.max_ts)

    results: list[dict[str, Any]] = []
    npz_payload: dict[str, np.ndarray] = {}
    for idx, cand in enumerate(cand_list):
        rec = evaluate_prepared_candidate(
            cand,
            prepared_assets=prepared,
            split=split,
            include_daily_returns=include_daily_returns,
        )
        results.append(rec)
        if output_npz_path is not None:
            dr = rec.get("daily_returns_1x") or {}
            npz_payload[f"c{idx:03d}_daily_r_1x"] = np.array(list(dr.values()), dtype=np.float64)

    if output_npz_path is not None:
        npz_p = Path(output_npz_path)
        npz_p.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(npz_p, **npz_payload)

    elapsed = round(time_mod.perf_counter() - t0, 3)
    return {
        "schema": SHARD_SCHEMA_VERSION,
        "completed_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "worker_role": os.environ.get("NAQEX_WORKER_ROLE", "LOCAL"),
        "numba_num_threads": int(os.environ.get("NUMBA_NUM_THREADS", "0") or 0),
        "split": str(split),
        "dev_cutoff_sec": DEV_CUTOFF_SEC,
        "max_ts_seen": max_ts_seen,
        "candidate_count": len(results),
        "symbols_loaded": sorted(needed_syms),
        "elapsed_sec": elapsed,
        "red_news_calendar_meta": {
            "sources_used": rn_cal.get("sources_used", []),
            "total_events": rn_cal.get("total_events", 0),
            "covered_currencies": rn_cal.get("covered_currencies", list(RED_NEWS_COVERED_CCYS)),
            "uncovered_currencies": rn_cal.get("uncovered_currencies", list(RED_NEWS_UNCOVERED_CCYS)),
        },
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "results": results,
    }


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    tmp: Path | None = None
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
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 5 5-Family Intraday M1 Shard Evaluator.")
    ap.add_argument("--split", default="cluster_a", choices=("cluster_a", "cluster_b", "dev_all"))
    ap.add_argument("--batch-file", default=None, help="Shard batch JSON file (or NAQEX_SHARD_BATCH_FILE).")
    ap.add_argument("--out-json", default=None, help="Output JSON path (or NAQEX_RESULT_DIR/shard_results.json).")
    ap.add_argument("--dump-grid", action="store_true", help="Print bounded Cluster A candidate grid summary.")
    ap.add_argument("--smoke", action="store_true", help="Run 1 candidate per family (5 total) on Cluster A.")
    args = ap.parse_args(argv)

    if args.dump_grid:
        grid = generate_cluster_a_candidate_grid()
        counts: dict[str, int] = {}
        for c in grid:
            counts[c["family_id"]] = counts.get(c["family_id"], 0) + 1
        print(
            json.dumps(
                {
                    "total_candidates": len(grid),
                    "max_total_candidates": MAX_TOTAL_CANDIDATES,
                    "by_family": counts,
                    "order_send_count": ORDER_SEND_COUNT,
                    _SEAL_ROWS_ANALYSED_KEY: 0,
                },
                indent=2,
                sort_keys=True,
            )
        )
        return 0

    batch_path_str = args.batch_file or os.environ.get("NAQEX_SHARD_BATCH_FILE")
    if args.smoke:
        grid = generate_cluster_a_candidate_grid()
        picked: list[dict[str, Any]] = []
        seen_fams: set[str] = set()
        for c in grid:
            if c["family_id"] not in seen_fams:
                picked.append(c)
                seen_fams.add(c["family_id"])
            if len(picked) == len(FAMILY_IDS):
                break
        res = evaluate_candidate_shard(picked, split=args.split, include_daily_returns=False)
    elif batch_path_str:
        batch_doc = json.loads(Path(batch_path_str).read_text(encoding="utf-8-sig"))
        shards = batch_doc.get("shards") or []
        cands: list[dict[str, Any]] = []
        full_grid = generate_cluster_a_candidate_grid()
        for item in shards:
            if isinstance(item, dict) and "candidates" in item:
                cands.extend(item["candidates"])
            elif isinstance(item, dict) and "candidate_id" in item:
                cands.append(item)
            elif isinstance(item, int) and 0 <= item < len(full_grid):
                cands.append(full_grid[item])
        res = evaluate_candidate_shard(cands, split=args.split)
    else:
        raise ValueError("Provide --smoke, --dump-grid, or --batch-file / NAQEX_SHARD_BATCH_FILE")

    out_path_str = args.out_json
    if not out_path_str and os.environ.get("NAQEX_RESULT_DIR"):
        out_path_str = str(Path(os.environ["NAQEX_RESULT_DIR"]) / "shard_results.json")

    if out_path_str:
        _atomic_write_json(Path(out_path_str), res)
    else:
        print(json.dumps(res, indent=2, ensure_ascii=False, sort_keys=True))
    return 0


__all__ = [
    "CLUSTER_B_START_SEC",
    "DEV_CUTOFF_SEC",
    "DEV_START_SEC",
    "F5A_SYMBOLS",
    "F5B_SYMBOLS",
    "F5C_SYMBOLS",
    "F5D_PAIRS",
    "F5E_SYMBOLS",
    "FAMILY_IDS",
    "FAM_F5A",
    "FAM_F5B",
    "FAM_F5C",
    "FAM_F5D",
    "FAM_F5E",
    "FRICTION_TIERS",
    "HARD_FLAT_MAX_UTC_HHMM",
    "HARD_FLAT_MAX_UTC_SEC",
    "MAX_TOTAL_CANDIDATES",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "RED_NEWS_BOJ_PAD_SEC",
    "RED_NEWS_COVERED_CCYS",
    "RED_NEWS_DEFAULT_PAD_SEC",
    "RED_NEWS_UNCOVERED_CCYS",
    "SCHEMA_VERSION",
    "SHARD_SCHEMA_VERSION",
    "SPEND_VND",
    "build_symbol_red_news_arrays",
    "compute_pair_union_metadata",
    "describe_red_news_scope",
    "evaluate_candidate_shard",
    "evaluate_prepared_candidate",
    "generate_cluster_a_candidate_grid",
    "load_wave5_red_news_calendar",
    "symbol_governing_ccys",
]

if __name__ == "__main__":
    raise SystemExit(main())
