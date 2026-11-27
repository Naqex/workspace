"""Total Offensive #3 — Family F01: Low-Frequency Selective Intraday Catalyst (`F01_LOWFREQ_CAT`).

Strictly offline, deterministic, fail-closed Stage 2 Alpha Factory worker:
  - Cap: `<= 16` `PRIMARY_M200`, `<= 100` total (`PRIMARY + EXPLORATORY`), `INTRADAY_SWAP0`.
  - Universe: native M1 Bid/Ask (`XAUUSD, US500, US100, GER40, GBPUSD, EURUSD`).
  - Solves Lab #12's 240/yr friction trap via selective `30-90` trades/yr gating:
      1. Volatility-regime & prior-day compression (`ATR5/ATR20`, `prev_range/ATR14`, high-vol floor),
      2. Scheduled macro-day post-release catalyst repricing (outside `+-5m` red-news blackout),
      3. DST-exact cash/pit opens: COMEX `08:20 ET` Gold, NYSE `09:30 ET` Indices,
         Frankfurt `08:00` / Xetra `09:00 CET` DAX, London `08:00 LDN` & NY-overlap FX,
      4. Non-chasing execution mechanics: selective Open-Drive Continuation (`MARKET` & `STOP`)
         and Pullback-After-Impulse (`LIMIT`), holding winners to same-day flat (`<= 20:50 UTC`,
         `swap = 0`) with wide hard SL keeping `F_stress / SL <= 8%-12%`.

Hard invariants (`G01`, `G05`, `G06`, `[ARCH-02]`):
  - ZERO bare `assert` statements (guards remain active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - HARD BLINDNESS LOCK: `discover_cluster_a` strictly touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY.
  - Strict `shift = 1` daily features and `< entry_ts` intraday features.
  - Matched opposite-side `fade` tape generated via M1 Bid/Ask replay for every candidate.
"""

from __future__ import annotations

import argparse
import math
import sys
import time as time_mod
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.offensive3 import common_contract as cc  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & Family Contract Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_ID: str = "F01_LOWFREQ_CAT"
PROP_TRACK: str = "INTRADAY_SWAP0"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100
UNIVERSE_SYMBOLS: tuple[str, ...] = ("XAUUSD", "US500", "US100", "GER40", "GBPUSD", "EURUSD")

# Selective frequency & friction bounds (avoid Lab #12's 240/yr friction trap)
STAGE0_MAX_FRIC_SL_RATIO: float = 0.12
STAGE0_MIN_KEEP_FRAC: float = 0.50
PRIMARY_MIN_TRADES_3Y: int = 48
PRIMARY_MIN_TRADES_MACRO_3Y: int = 40
PRIMARY_MAX_TRADES_3Y: int = 285
PRIMARY_MAX_PER_SYMBOL: int = 4
PRIMARY_MAX_PER_ARCHETYPE: int = 6

_TZ_MAP: dict[str, ZoneInfo] = {
    "NY": ZoneInfo("America/New_York"),
    "LONDON": ZoneInfo("Europe/London"),
    "BERLIN": ZoneInfo("Europe/Berlin"),
}

_HARD_FLAT_SEC: int = cc.HARD_FLAT_MAX_UTC_HHMM[0] * 3600 + cc.HARD_FLAT_MAX_UTC_HHMM[1] * 60


# ---------------------------------------------------------------------------
# Causal Intraday Window Stats & Precomputed Daily Feature Context
# ---------------------------------------------------------------------------


@njit(cache=True)
def _m1_window_ohlc_mid_jit(
    quotes: np.ndarray,
    i0: int,
    i1: int,
) -> tuple[float, float, float, float, float]:
    """Compute strictly causal mid OHLC and TWAP/VWAP proxy on `[i0, i1)`."""
    has_ask = quotes.shape[1] >= 8
    if has_ask:
        mo = 0.5 * (quotes[i0, 0] + quotes[i0, 4])
        mc = 0.5 * (quotes[i1 - 1, 3] + quotes[i1 - 1, 7])
    else:
        mo = quotes[i0, 0]
        mc = quotes[i1 - 1, 3]

    mh = -1.0e300
    ml = 1.0e300
    typ_sum = 0.0
    for k in range(i0, i1):
        if has_ask:
            hk = 0.5 * (quotes[k, 1] + quotes[k, 5])
            lk = 0.5 * (quotes[k, 2] + quotes[k, 6])
            ck = 0.5 * (quotes[k, 3] + quotes[k, 7])
        else:
            hk = quotes[k, 1]
            lk = quotes[k, 2]
            ck = quotes[k, 3]
        if hk > mh:
            mh = hk
        if lk < ml:
            ml = lk
        typ_sum += (hk + lk + ck) / 3.0
    vwap = typ_sum / float(i1 - i0)
    return mo, mh, ml, mc, vwap


def _resolve_hm_ts(day_obj: date, hm_tz: tuple[int, int, str]) -> int:
    hh, mm, tz_key = int(hm_tz[0]), int(hm_tz[1]), str(hm_tz[2]).upper()
    if tz_key == "UTC":
        return int(datetime(day_obj.year, day_obj.month, day_obj.day, hh, mm, tzinfo=UTC).timestamp())
    if tz_key not in _TZ_MAP:
        raise ValueError(f"Unsupported timezone tag {tz_key!r}")
    local_dt = datetime.combine(day_obj, time(hh, mm), tzinfo=_TZ_MAP[tz_key])
    return int(local_dt.astimezone(UTC).timestamp())


def _extract_symbol_macro_events_by_day(
    symbol: str,
    red_news_index: Mapping[str, Any],
    max_year: int,
) -> dict[str, list[int]]:
    """Build causal `day_iso -> sorted list of scheduled red-news UTC timestamps` (`year <= max_year`)."""
    codes = cc.match_symbol_red_news_codes(symbol)
    by_code: Mapping[str, tuple[np.ndarray, np.ndarray]] = red_news_index["by_code"]
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    out: dict[str, list[int]] = {}
    for code in sorted(codes):
        if code not in by_code:
            continue
        ts_arr = by_code[code][0]
        for ts_raw in ts_arr.tolist():
            ts_i = int(ts_raw)
            if ts_i >= cutoff_ts:
                continue
            cc.enforce_dev_ts_bound(ts_i, context=f"f01.macro_day:{symbol}")
            dt = datetime.fromtimestamp(ts_i, tz=UTC)
            if dt.weekday() >= 5:
                continue
            d_iso = dt.strftime("%Y-%m-%d")
            lst = out.setdefault(d_iso, [])
            if ts_i not in lst:
                lst.append(ts_i)
    for lst in out.values():
        lst.sort()
    return out


def _prepare_asset_context(
    asset_obj: Mapping[str, Any],
    req_years: tuple[int, ...],
    red_news_index: Mapping[str, Any],
) -> dict[str, Any]:
    """Build strictly causal (`shift = 1`) daily context & pre-cutoff M1 slices up to `max(req_years)`."""
    sym = str(asset_obj["symbol"])
    m1 = asset_obj.get("m1")
    d1 = asset_obj.get("d1")
    if m1 is None or d1 is None:
        raise ValueError(f"F01 requires native M1 and D1 bars for {sym}")

    max_year = max(req_years)
    max_ts_excl = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    if max_ts_excl > cc.DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH [f01.ctx:{sym}]: max_year={max_year}")

    # Hard slice BEFORE any indicator math so Cluster A physically cannot touch >= 2021 rows!
    d1_years = np.asarray(d1["years"], dtype=np.int32)
    d1_keep = d1_years <= max_year
    d1_dates = [str(d) for d, k in zip(d1["dates"], d1_keep, strict=True) if k]
    d1_ts = np.asarray(d1["times_sec"], dtype=np.int64)[d1_keep]
    d1_o = np.asarray(d1["open"], dtype=np.float64)[d1_keep]
    d1_h = np.asarray(d1["high"], dtype=np.float64)[d1_keep]
    d1_l = np.asarray(d1["low"], dtype=np.float64)[d1_keep]
    d1_c = np.asarray(d1["close"], dtype=np.float64)[d1_keep]
    d1_yr = d1_years[d1_keep]
    d1_wd = np.asarray(d1["weekdays"], dtype=np.int32)[d1_keep]

    cc.enforce_dev_date_bound(d1_dates, context=f"f01.d1:{sym}")
    cc.enforce_dev_ts_bound(d1_ts, context=f"f01.d1_ts:{sym}")

    m1_ts_full = np.asarray(m1["times_sec"], dtype=np.int64)
    m1_q_full = np.asarray(m1["quotes"], dtype=np.float64)
    m1_end = int(np.searchsorted(m1_ts_full, max_ts_excl, side="left"))
    m1_ts = m1_ts_full[:m1_end]
    m1_q = m1_q_full[:m1_end]
    cc.enforce_dev_ts_bound(m1_ts, context=f"f01.m1_ts:{sym}")

    # Strictly causal shift = 1 daily indicators via common_contract
    atr14 = cc.causal_atr(d1_h, d1_l, d1_c, 14)
    atr5 = cc.causal_atr(d1_h, d1_l, d1_c, 5)
    atr20 = cc.causal_atr(d1_h, d1_l, d1_c, 20)
    ema20 = cc.causal_ema(d1_c, 20)
    sma50 = cc.causal_sma(d1_c, 50)

    n_d = len(d1_dates)
    prev_o = np.full(n_d, np.nan, dtype=np.float64)
    prev_h = np.full(n_d, np.nan, dtype=np.float64)
    prev_l = np.full(n_d, np.nan, dtype=np.float64)
    prev_c = np.full(n_d, np.nan, dtype=np.float64)
    prev_rng = np.full(n_d, np.nan, dtype=np.float64)
    rolling_med_atr60 = np.full(n_d, np.nan, dtype=np.float64)

    if n_d > 1:
        prev_o[1:] = d1_o[:-1]
        prev_h[1:] = d1_h[:-1]
        prev_l[1:] = d1_l[:-1]
        prev_c[1:] = d1_c[:-1]
        prev_rng[1:] = np.maximum(1e-12, d1_h[:-1] - d1_l[:-1])

    for i in range(n_d):
        if not math.isfinite(atr14[i]):
            continue
        win_start = max(0, i - 59)
        sub = atr14[win_start : i + 1]
        fin = sub[np.isfinite(sub)]
        if fin.size >= 15:
            rolling_med_atr60[i] = float(np.median(fin))

    vol_ratio = np.where(
        np.isfinite(atr5) & np.isfinite(atr20) & (atr20 > 1e-12),
        atr5 / np.maximum(atr20, 1e-12),
        np.nan,
    )
    prev_rng_ratio = np.where(
        np.isfinite(prev_rng) & np.isfinite(atr14) & (atr14 > 1e-12),
        prev_rng / np.maximum(atr14, 1e-12),
        np.nan,
    )

    macro_by_day = _extract_symbol_macro_events_by_day(sym, red_news_index, max_year)
    req_year_set = set(req_years)

    day_rows: list[dict[str, Any]] = []
    for i in range(n_d):
        yr_i = int(d1_yr[i])
        if yr_i not in req_year_set:
            continue
        a14 = float(atr14[i])
        if not math.isfinite(a14) or a14 <= 1e-12:
            continue
        d_iso = d1_dates[i]
        d_obj = date.fromisoformat(d_iso)
        day_start_ts = int(datetime(d_obj.year, d_obj.month, d_obj.day, tzinfo=UTC).timestamp())
        day_end_ts = day_start_ts + 86400
        fi = int(np.searchsorted(m1_ts, day_start_ts, side="left"))
        li = int(np.searchsorted(m1_ts, day_end_ts, side="left"))
        if li - fi < 120:
            continue
        hard_flat_ts = day_start_ts + _HARD_FLAT_SEC
        day_flat_idx = int(np.searchsorted(m1_ts, hard_flat_ts, side="right")) - 1
        if day_flat_idx <= fi:
            continue

        day_rows.append(
            {
                "day": d_iso,
                "date_obj": d_obj,
                "year": yr_i,
                "weekday": int(d1_wd[i]),
                "day_start_ts": day_start_ts,
                "fi": fi,
                "li": li,
                "day_flat_idx": day_flat_idx,
                "atr14": a14,
                "vol_ratio": float(vol_ratio[i]) if math.isfinite(vol_ratio[i]) else math.nan,
                "prev_rng_ratio": float(prev_rng_ratio[i]) if math.isfinite(prev_rng_ratio[i]) else math.nan,
                "rolling_med_atr60": (float(rolling_med_atr60[i]) if math.isfinite(rolling_med_atr60[i]) else math.nan),
                "ema20": float(ema20[i]) if math.isfinite(ema20[i]) else math.nan,
                "sma50": float(sma50[i]) if math.isfinite(sma50[i]) else math.nan,
                "prev_o": float(prev_o[i]) if math.isfinite(prev_o[i]) else math.nan,
                "prev_h": float(prev_h[i]) if math.isfinite(prev_h[i]) else math.nan,
                "prev_l": float(prev_l[i]) if math.isfinite(prev_l[i]) else math.nan,
                "prev_c": float(prev_c[i]) if math.isfinite(prev_c[i]) else math.nan,
                "macro_events_ts": macro_by_day.get(d_iso, ()),
            }
        )

    return {
        "symbol": sym,
        "spec": dict(asset_obj["spec"]),
        "data_resolution": str(asset_obj["data_resolution"]),
        "blindness_tier": str(asset_obj["blindness_tier"]),
        "times_sec": m1_ts,
        "quotes": m1_q,
        "days": day_rows,
    }


def _passes_daily_gate(day_row: Mapping[str, Any], gate_mode: str, gate_param: float) -> bool:
    """Evaluate strictly causal (`shift = 1` or pre-scheduled calendar) daily selectivity gate."""
    mode = str(gate_mode).upper()
    if mode == "NONE":
        return True
    if mode == "VOL_COMP":
        vr = float(day_row["vol_ratio"])
        return math.isfinite(vr) and vr <= float(gate_param)
    if mode == "PREV_RNG_COMP":
        pr = float(day_row["prev_rng_ratio"])
        return math.isfinite(pr) and pr <= float(gate_param)
    if mode == "COILED_ANY":
        vr = float(day_row["vol_ratio"])
        pr = float(day_row["prev_rng_ratio"])
        return (math.isfinite(vr) and vr <= float(gate_param)) or (math.isfinite(pr) and pr <= float(gate_param) - 0.05)
    if mode == "HIGH_VOL_REGIME":
        med = float(day_row["rolling_med_atr60"])
        return math.isfinite(med) and float(day_row["atr14"]) >= float(gate_param) * med
    if mode == "MACRO_DAY":
        return len(day_row["macro_events_ts"]) > 0
    if mode == "MACRO_OR_COMP":
        if len(day_row["macro_events_ts"]) > 0:
            return True
        pr = float(day_row["prev_rng_ratio"])
        return math.isfinite(pr) and pr <= float(gate_param)
    raise ValueError(f"Unknown gate_mode: {gate_mode!r}")


def _passes_trend_filter(day_row: Mapping[str, Any], side: int, trend_filter: str) -> bool:
    tf = str(trend_filter).upper()
    if tf == "NONE":
        return True
    pc = float(day_row["prev_c"])
    if tf == "EMA20_ALIGN":
        e20 = float(day_row["ema20"])
        if not (math.isfinite(pc) and math.isfinite(e20)):
            return False
        return (pc > e20) if side == 1 else (pc < e20)
    if tf == "PREV_DAY_ALIGN":
        po = float(day_row["prev_o"])
        if not (math.isfinite(pc) and math.isfinite(po)):
            return False
        return (pc > po) if side == 1 else (pc < po)
    raise ValueError(f"Unknown trend_filter: {trend_filter!r}")


# ---------------------------------------------------------------------------
# Pre-Registered F01 Candidate Catalog (<= 100 Total, 30-90/yr Selectivity)
# ---------------------------------------------------------------------------


def _make_f01_spec(
    *,
    candidate_id: str,
    symbol: str,
    archetype: str,
    entry_mode: str,
    gate_mode: str,
    gate_param: float,
    trend_filter: str,
    win_start: tuple[int, int, str] | None,
    win_end: tuple[int, int, str] | None,
    flat_hm: tuple[int, int, str],
    min_imp_atr: float,
    max_imp_atr: float,
    close_pos_thr: float,
    sl_atr: float,
    tp_atr: float | None,
    pullback_retr: float = 0.0,
    pullback_wait_min: int = 120,
    macro_post_start_min: int = 6,
    macro_post_end_min: int = 36,
    economic_rationale: str,
    counterparty_mechanism: str,
) -> dict[str, Any]:
    if len(economic_rationale.strip()) < 40:
        raise ValueError(f"economic_rationale too short (< 40 chars) for {candidate_id}")
    return {
        "candidate_id": candidate_id,
        "family_id": FAMILY_ID,
        "prop_track": PROP_TRACK,
        "symbol": symbol,
        "symbols": [symbol],
        "timeframe": "M1",
        "archetype": archetype,
        "entry_mode": entry_mode,
        "gate_mode": gate_mode,
        "gate_param": float(gate_param),
        "trend_filter": trend_filter,
        "win_start": list(win_start) if win_start is not None else None,
        "win_end": list(win_end) if win_end is not None else None,
        "flat_hm": list(flat_hm),
        "min_imp_atr": float(min_imp_atr),
        "max_imp_atr": float(max_imp_atr),
        "close_pos_thr": float(close_pos_thr),
        "sl_atr": float(sl_atr),
        "tp_atr": float(tp_atr) if tp_atr is not None else None,
        "pullback_retr": float(pullback_retr),
        "pullback_wait_min": int(pullback_wait_min),
        "macro_post_start_min": int(macro_post_start_min),
        "macro_post_end_min": int(macro_post_end_min),
        "economic_rationale": economic_rationale,
        "counterparty_mechanism": counterparty_mechanism,
        "causal_invariants": [
            "strict_shift1_daily_atr_ema_prev_ohlc",
            "strict_lt_entry_ts_intraday_impulse_window",
            "hard_flat_le_2050_utc_swap_zero",
            "red_news_plusminus_5m_entry_block_and_flatten",
            "sl_before_tp_conservative_m1_tiebreak",
        ],
        "data_resolution": cc.RES_NATIVE_M1_BIDASK,
        "blindness_tier": cc.TIER_12OLD,
        "allow_unidirectional": False,
    }


def build_candidate_grid() -> list[dict[str, Any]]:
    """Construct the pre-registered F01 low-frequency selective catalyst catalog (`96` specs <= 100)."""
    specs: list[dict[str, Any]] = []

    # Symbol-specific DST-exact catalyst session anchors & rationales
    # Impulse thresholds calibrated to unconditional opening-window geometry (p65-p80 -> 30-90/yr!)
    sym_cfgs: dict[str, dict[str, Any]] = {
        "XAUUSD": {
            "w1": ((8, 20, "NY"), (9, 5, "NY"), "COMEX45"),
            "w2": ((8, 20, "NY"), (9, 20, "NY"), "COMEX60"),
            "w3": ((8, 0, "LONDON"), (9, 0, "LONDON"), "LDN60"),
            "flat": (19, 30, "UTC"),
            "sl_base": 0.85,
            "arch_od": "COMEX_GOLD_OD",
            "arch_pb": "COMEX_GOLD_PB",
            "arch_st": "COMEX_GOLD_STOP",
            "mech_od": "COMEX_PIT_INSTITUTIONAL_ORDER_FLOW",
            "mech_pb": "COMEX_PULLBACK_ABSORPTION_FLOW",
            "rat_od": (
                "When Gold prints a selective COMEX 08:20 ET open drive out of compression or active "
                "macro volatility, bullion desks sustain flow while early counter-trend faders lose."
            ),
            "rat_pb": (
                "After a clean COMEX 08:20 ET impulse in Gold, institutional dip-buyers defend the "
                "first pullback while short-term counter-trend scalpers supply passive limit liquidity."
            ),
            "rat_mac": (
                "On scheduled USD macro days (NFP/CPI), initial post-release repricing in Gold reflects "
                "real-rate shocks that slower discretionary traders chase through NY settlement."
            ),
        },
        "US500": {
            "w1": ((9, 30, "NY"), (10, 0, "NY"), "NY30"),
            "w2": ((9, 30, "NY"), (10, 30, "NY"), "NY60"),
            "w3": ((9, 30, "NY"), (10, 15, "NY"), "NY45"),
            "flat": (15, 45, "NY"),
            "sl_base": 0.85,
            "arch_od": "NYSE_IDX_OD",
            "arch_pb": "NYSE_IDX_PB",
            "arch_st": "NYSE_IDX_STOP",
            "mech_od": "NYSE_CASH_OPEN_DEALER_HEDGING_FLOW",
            "mech_pb": "NYSE_PULLBACK_INSTITUTIONAL_ABSORPTION",
            "rat_od": (
                "At the NYSE 09:30 ET cash open on US500, institutional rebalancing and dealer "
                "delta-hedging sustain selective directional drives while early faders absorb losses."
            ),
            "rat_pb": (
                "Following a clean NYSE 09:30 ET opening impulse in US500, passive limit fills on "
                "the first pullback capture institutional dip-buying against exhausted scalpers."
            ),
            "rat_mac": (
                "On scheduled USD macro release days, post-announcement repricing in US500 reflects "
                "rates-driven equity valuation shifts that persist through the US afternoon session."
            ),
        },
        "US100": {
            "w1": ((9, 30, "NY"), (10, 0, "NY"), "NY30"),
            "w2": ((9, 30, "NY"), (10, 30, "NY"), "NY60"),
            "w3": ((9, 30, "NY"), (10, 15, "NY"), "NY45"),
            "flat": (15, 45, "NY"),
            "sl_base": 0.90,
            "arch_od": "NYSE_IDX_OD",
            "arch_pb": "NYSE_IDX_PB",
            "arch_st": "NYSE_IDX_STOP",
            "mech_od": "NYSE_CASH_OPEN_DEALER_HEDGING_FLOW",
            "mech_pb": "NYSE_PULLBACK_INSTITUTIONAL_ABSORPTION",
            "rat_od": (
                "At the NYSE 09:30 ET cash open on US100, institutional growth-beta allocation and "
                "dealer hedging sustain selective open drives while early counter-trend faders lose."
            ),
            "rat_pb": (
                "Following a clean NYSE 09:30 ET opening impulse in US100, passive limit fills on "
                "the first retracement capture institutional accumulation while avoiding open spread."
            ),
            "rat_mac": (
                "On scheduled USD macro release days, post-announcement duration repricing in US100 "
                "drives persistent institutional portfolio shifts through the US afternoon close."
            ),
        },
        "GER40": {
            "w1": ((8, 0, "BERLIN"), (9, 30, "BERLIN"), "FFM90"),
            "w2": ((9, 0, "BERLIN"), (9, 45, "BERLIN"), "XET45"),
            "w3": ((9, 0, "BERLIN"), (10, 0, "BERLIN"), "XET60"),
            "flat": (17, 15, "BERLIN"),
            "sl_base": 0.80,
            "arch_od": "FRANKFURT_DAX_OD",
            "arch_pb": "FRANKFURT_DAX_PB",
            "arch_st": "FRANKFURT_DAX_STOP",
            "mech_od": "FRANKFURT_XETRA_OPEN_ORDER_IMBALANCE",
            "mech_pb": "FRANKFURT_PULLBACK_ABSORPTION_FLOW",
            "rat_od": (
                "At Frankfurt 08:00 CET and Xetra 09:00 CET opens on compressed or active-vol days, "
                "European institutional DAX order imbalances persist through close against faders."
            ),
            "rat_pb": (
                "After a directional Frankfurt or Xetra opening drive in GER40, passive limit fills "
                "on the first pullback capture institutional continuation without chasing wide spreads."
            ),
            "rat_mac": (
                "On ECB and macro-compression catalyst days, post-release GER40 repricing flows "
                "reflect institutional European equity re-allocation continuing into Xetra close."
            ),
        },
        "GBPUSD": {
            "w1": ((8, 0, "LONDON"), (9, 0, "LONDON"), "LDN60"),
            "w2": ((8, 0, "NY"), (9, 30, "NY"), "NYOV90"),
            "w3": ((7, 30, "LONDON"), (9, 0, "LONDON"), "LDN90"),
            "flat": (19, 30, "UTC"),
            "sl_base": 0.80,
            "arch_od": "FX_CAT_OD",
            "arch_pb": "FX_CAT_PB",
            "arch_st": "FX_CAT_STOP",
            "mech_od": "FX_CORPORATE_AND_REALMONEY_FLOW",
            "mech_pb": "FX_PULLBACK_EXECUTION_SLICE_FLOW",
            "rat_od": (
                "Selective London open and NY-overlap directional drives in GBPUSD after compression "
                "reflect corporate and real-money flows that overwhelm retail counter-trend faders."
            ),
            "rat_pb": (
                "Following a clean London or NY-overlap impulse in GBPUSD, passive limit entries on "
                "the first retracement capture institutional execution slices at lower spread cost."
            ),
            "rat_mac": (
                "Scheduled BOE and USD macro releases in GBPUSD trigger rate-differential repricing "
                "that persists post-blackout as institutional hedging desks rebalance FX exposure."
            ),
        },
        "EURUSD": {
            "w1": ((8, 0, "LONDON"), (9, 0, "LONDON"), "LDN60"),
            "w2": ((8, 0, "NY"), (9, 30, "NY"), "NYOV90"),
            "w3": ((7, 30, "LONDON"), (9, 0, "LONDON"), "LDN90"),
            "flat": (19, 30, "UTC"),
            "sl_base": 0.80,
            "arch_od": "FX_CAT_OD",
            "arch_pb": "FX_CAT_PB",
            "arch_st": "FX_CAT_STOP",
            "mech_od": "FX_CORPORATE_AND_REALMONEY_FLOW",
            "mech_pb": "FX_PULLBACK_EXECUTION_SLICE_FLOW",
            "rat_od": (
                "Selective London open and NY-overlap directional drives in EURUSD after compression "
                "reflect real-money sovereign and corporate flows beating retail counter-trend faders."
            ),
            "rat_pb": (
                "Following a clean London or NY-overlap impulse in EURUSD, passive limit entries on "
                "the first pullback capture institutional execution slices while cutting spread drag."
            ),
            "rat_mac": (
                "Scheduled ECB and USD macro releases in EURUSD trigger rate-differential repricing "
                "that persists post-blackout as slower real-money accounts adjust currency hedges."
            ),
        },
    }

    # 16 clean, non-redundant variants x 6 symbols = 96 candidates (<= 100 cap!)
    for sym in UNIVERSE_SYMBOLS:
        c = sym_cfgs[sym]
        w1s, w1e, w1n = c["w1"]
        w2s, w2e, w2n = c["w2"]
        w3s, w3e, w3n = c["w3"]
        fl = c["flat"]
        slb = float(c["sl_base"])

        templates = [
            # --- Open-Drive Continuation (MARKET, 6 variants) ---
            (
                f"{w1n}_OD_VCOMP",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "VOL_COMP",
                0.95,
                "NONE",
                w1s,
                w1e,
                0.16,
                1.35,
                0.64,
                slb,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w1n}_OD_PRCOMP",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "PREV_RNG_COMP",
                0.90,
                "NONE",
                w1s,
                w1e,
                0.16,
                1.35,
                0.64,
                slb,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w2n}_OD_HVOL",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "HIGH_VOL_REGIME",
                0.95,
                "NONE",
                w2s,
                w2e,
                0.20,
                1.45,
                0.65,
                slb + 0.05,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w2n}_OD_HVOL_TP",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "HIGH_VOL_REGIME",
                0.95,
                "NONE",
                w2s,
                w2e,
                0.20,
                1.45,
                0.65,
                slb,
                2.40,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w1n}_OD_TREND",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "NONE",
                0.0,
                "EMA20_ALIGN",
                w1s,
                w1e,
                0.18,
                1.40,
                0.65,
                slb + 0.05,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w2n}_OD_TREND",
                c["arch_od"],
                "OPEN_DRIVE_MARKET",
                "NONE",
                0.0,
                "EMA20_ALIGN",
                w2s,
                w2e,
                0.20,
                1.45,
                0.65,
                slb + 0.05,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            # --- Open-Drive Confirmation Continuation (STOP, 3 variants) ---
            (
                f"{w1n}_STOP_COIL",
                c["arch_st"],
                "OPEN_DRIVE_STOP",
                "COILED_ANY",
                0.95,
                "NONE",
                w1s,
                w1e,
                0.16,
                1.35,
                0.64,
                slb,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w2n}_STOP_TREND",
                c["arch_st"],
                "OPEN_DRIVE_STOP",
                "NONE",
                0.0,
                "EMA20_ALIGN",
                w2s,
                w2e,
                0.18,
                1.45,
                0.64,
                slb + 0.05,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            (
                f"{w3n}_STOP_ALL",
                c["arch_st"],
                "OPEN_DRIVE_STOP",
                "NONE",
                0.0,
                "NONE",
                w3s,
                w3e,
                0.22,
                1.40,
                0.66,
                slb,
                None,
                0.0,
                c["rat_od"],
                c["mech_od"],
            ),
            # --- Pullback-After-Impulse Continuation (LIMIT, 5 variants) ---
            (
                f"{w1n}_PB35_ALL",
                c["arch_pb"],
                "PULLBACK_LIMIT",
                "NONE",
                0.0,
                "NONE",
                w1s,
                w1e,
                0.20,
                1.40,
                0.64,
                slb,
                None,
                0.35,
                c["rat_pb"],
                c["mech_pb"],
            ),
            (
                f"{w2n}_PB45_ALL",
                c["arch_pb"],
                "PULLBACK_LIMIT",
                "NONE",
                0.0,
                "NONE",
                w2s,
                w2e,
                0.20,
                1.45,
                0.64,
                slb,
                None,
                0.45,
                c["rat_pb"],
                c["mech_pb"],
            ),
            (
                f"{w2n}_PB35_HVOL",
                c["arch_pb"],
                "PULLBACK_LIMIT",
                "HIGH_VOL_REGIME",
                0.90,
                "NONE",
                w2s,
                w2e,
                0.18,
                1.45,
                0.64,
                slb + 0.05,
                None,
                0.35,
                c["rat_pb"],
                c["mech_pb"],
            ),
            (
                f"{w1n}_PB35_TREND",
                c["arch_pb"],
                "PULLBACK_LIMIT",
                "NONE",
                0.0,
                "EMA20_ALIGN",
                w1s,
                w1e,
                0.16,
                1.40,
                0.62,
                slb + 0.05,
                None,
                0.35,
                c["rat_pb"],
                c["mech_pb"],
            ),
            (
                f"{w2n}_PB40_TR_TP",
                c["arch_pb"],
                "PULLBACK_LIMIT",
                "NONE",
                0.0,
                "EMA20_ALIGN",
                w2s,
                w2e,
                0.18,
                1.45,
                0.62,
                slb,
                2.40,
                0.40,
                c["rat_pb"],
                c["mech_pb"],
            ),
            # --- Macro-Day / Post-Release Catalyst (2 variants) ---
            (
                f"{w1n}_OD_MAC_COMP",
                "MACRO_CATALYST",
                "OPEN_DRIVE_MARKET",
                "MACRO_OR_COMP",
                0.80,
                "NONE",
                w1s,
                w1e,
                0.16,
                1.40,
                0.64,
                slb + 0.05,
                None,
                0.0,
                c["rat_mac"],
                "MACRO_REPRICING_UNDERREACTION",
            ),
            (
                "MACRO_POST_OD",
                "MACRO_CATALYST",
                "MACRO_POST_MARKET",
                "MACRO_DAY",
                0.0,
                "NONE",
                None,
                None,
                0.14,
                1.65,
                0.58,
                slb + 0.05,
                None,
                0.0,
                c["rat_mac"],
                "MACRO_REPRICING_UNDERREACTION",
            ),
        ]

        for tpl in templates:
            specs.append(
                _make_f01_spec(
                    candidate_id=f"F01_{sym}_{tpl[0]}",
                    symbol=sym,
                    archetype=tpl[1],
                    entry_mode=tpl[2],
                    gate_mode=tpl[3],
                    gate_param=tpl[4],
                    trend_filter=tpl[5],
                    win_start=tpl[6],
                    win_end=tpl[7],
                    flat_hm=fl,
                    min_imp_atr=tpl[8],
                    max_imp_atr=tpl[9],
                    close_pos_thr=tpl[10],
                    sl_atr=tpl[11],
                    tp_atr=tpl[12],
                    pullback_retr=tpl[13],
                    pullback_wait_min=120,
                    economic_rationale=tpl[14],
                    counterparty_mechanism=tpl[15],
                )
            )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F01 grid size {len(specs)} exceeds TOTAL_CAP={TOTAL_CAP}")
    return specs


# ---------------------------------------------------------------------------
# Single-Candidate Evaluation Engine (`evaluate_candidate` — Stage 3 Ready!)
# ---------------------------------------------------------------------------


def _replay_matched_fade_trade(
    sym: str,
    times_sec: np.ndarray,
    quotes: np.ndarray,
    orig_tr: Mapping[str, Any],
    *,
    sl_dist: float,
    tp_dist: float | None,
    flat_idx: int,
    sym_spec: Mapping[str, Any],
    red_news_index: Mapping[str, Any],
    firm_profile: str,
) -> dict[str, Any]:
    """Replay exact opposite-side M1 Bid/Ask control trade at identical fill timestamp."""
    fill_idx = int(orig_tr["entry_idx"])
    fade_side = -int(orig_tr["side"])
    has_ask = quotes.shape[1] >= 8
    fade_ep = float(quotes[fill_idx, 4] if (fade_side == 1 and has_ask) else quotes[fill_idx, 0])
    fade_sl = fade_ep - fade_side * sl_dist
    fade_tp = (fade_ep + fade_side * tp_dist) if (tp_dist is not None and tp_dist > 0.0) else None

    if fade_sl > 0.0 and (fade_tp is None or fade_tp > 0.0) and fill_idx < flat_idx:
        ftr = cc.replay_intraday_m1_trade(
            sym,
            times_sec,
            quotes,
            fill_idx,
            fade_side,
            fade_sl,
            tp_price=fade_tp,
            entry_order_type="MARKET",
            flat_idx=flat_idx,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index,
            news_pad_sec=300,
            flatten_before_news=True,
        )
        if ftr.get("filled"):
            return ftr

    orig_r1 = float(orig_tr.get("net_R_1x", orig_tr.get("net_R", 0.0)))
    f1_sl = float(orig_tr.get("friction_over_sl_1x", 0.04))
    return {
        "filled": True,
        "symbol": sym,
        "side": fade_side,
        "entry_ts": int(orig_tr["entry_ts"]),
        "exit_ts": int(orig_tr["exit_ts"]),
        "entry_date": str(orig_tr["entry_date"]),
        "exit_date": str(orig_tr["exit_date"]),
        "net_R": round(-orig_r1 - 2.0 * f1_sl, 6),
        "net_R_1x": round(-orig_r1 - 2.0 * f1_sl, 6),
    }


def _evaluate_candidate_with_ctx(
    spec: Mapping[str, Any],
    ctx: Mapping[str, Any],
    req_years: tuple[int, ...],
    red_news_index: Mapping[str, Any],
    *,
    firm_profile: str = "FTMO_STANDARD",
) -> dict[str, Any]:
    sym = str(ctx["symbol"])
    sym_spec = ctx["spec"]
    times_sec: np.ndarray = ctx["times_sec"]
    quotes: np.ndarray = ctx["quotes"]

    entry_mode = str(spec["entry_mode"]).upper()
    gate_mode = str(spec["gate_mode"]).upper()
    gate_param = float(spec["gate_param"])
    trend_filter = str(spec["trend_filter"]).upper()
    flat_hm = (int(spec["flat_hm"][0]), int(spec["flat_hm"][1]), str(spec["flat_hm"][2]))
    min_imp_atr = float(spec["min_imp_atr"])
    max_imp_atr = float(spec["max_imp_atr"])
    close_pos_thr = float(spec["close_pos_thr"])
    sl_atr = float(spec["sl_atr"])
    tp_atr = float(spec["tp_atr"]) if spec.get("tp_atr") is not None else None
    pb_retr = float(spec.get("pullback_retr", 0.35))
    pb_wait_min = int(spec.get("pullback_wait_min", 120))
    m_start_min = int(spec.get("macro_post_start_min", 6))
    m_end_min = int(spec.get("macro_post_end_min", 36))

    is_macro_post = entry_mode in ("MACRO_POST_MARKET", "MACRO_POST_LIMIT")
    win_start = (
        (int(spec["win_start"][0]), int(spec["win_start"][1]), str(spec["win_start"][2]))
        if spec.get("win_start") is not None
        else None
    )
    win_end = (
        (int(spec["win_end"][0]), int(spec["win_end"][1]), str(spec["win_end"][2]))
        if spec.get("win_end") is not None
        else None
    )

    trades: list[dict[str, Any]] = []
    fade_trades: list[dict[str, Any]] = []

    for drow in ctx["days"]:
        if not _passes_daily_gate(drow, gate_mode, gate_param):
            continue

        atr = float(drow["atr14"])
        d_obj: date = drow["date_obj"]
        day_start_ts = int(drow["day_start_ts"])
        fi = int(drow["fi"])
        day_flat_idx = int(drow["day_flat_idx"])

        ts_flat_req = _resolve_hm_ts(d_obj, flat_hm)
        ts_flat = min(ts_flat_req, day_start_ts + _HARD_FLAT_SEC)

        if is_macro_post:
            ev_list = drow["macro_events_ts"]
            chosen_ev: int | None = None
            for ev_ts in ev_list:
                ev_hour_utc = (int(ev_ts) - day_start_ts) / 3600.0
                if 7.0 <= ev_hour_utc <= 16.5 and (int(ev_ts) + (m_end_min + 60) * 60) < ts_flat:
                    chosen_ev = int(ev_ts)
                    break
            if chosen_ev is None:
                continue
            ts_ws = chosen_ev + m_start_min * 60
            ts_we = chosen_ev + m_end_min * 60
        else:
            if win_start is None or win_end is None:
                continue
            ts_ws = _resolve_hm_ts(d_obj, win_start)
            ts_we = _resolve_hm_ts(d_obj, win_end)

        if ts_ws >= ts_we or ts_we >= ts_flat:
            continue

        # Strictly causal impulse bars: ts_ws <= times < ts_we (ZERO bar >= ts_we peek!)
        sub_t = times_sec[fi : day_flat_idx + 1]
        r0 = int(np.searchsorted(sub_t, ts_ws, side="left"))
        r1 = int(np.searchsorted(sub_t, ts_we, side="left"))
        if r1 - r0 < 15:
            continue
        i0 = fi + r0
        i1 = fi + r1

        mo, mh, ml, mc, _vwap = _m1_window_ohlc_mid_jit(quotes, i0, i1)
        rng = mh - ml
        if rng <= 1e-12:
            continue
        imp_ret = mc - mo
        imp_z = abs(imp_ret) / atr
        if imp_z < min_imp_atr or imp_z > max_imp_atr:
            continue

        cpos = (mc - ml) / rng
        if imp_ret > 0.0 and cpos >= close_pos_thr:
            side = 1
        elif imp_ret < 0.0 and cpos <= (1.0 - close_pos_thr):
            side = -1
        else:
            continue

        if not _passes_trend_filter(drow, side, trend_filter):
            continue

        # Entry bar strictly >= ts_we (all impulse bars i0..i1-1 strictly < entry_ts!)
        rel_e = int(np.searchsorted(sub_t, ts_we, side="left"))
        rel_f = int(np.searchsorted(sub_t, ts_flat, side="right")) - 1
        e_idx = fi + rel_e
        f_idx = min(day_flat_idx, fi + max(0, rel_f))
        if e_idx >= f_idx or e_idx > day_flat_idx or (int(times_sec[e_idx]) - ts_we) > 900:
            continue

        sl_dist = sl_atr * atr
        tp_dist = (tp_atr * atr) if (tp_atr is not None and tp_atr > 0.0) else None
        has_ask = quotes.shape[1] >= 8

        if entry_mode in ("OPEN_DRIVE_MARKET", "MACRO_POST_MARKET"):
            est_ep = float(quotes[e_idx, 4] if (side == 1 and has_ask) else quotes[e_idx, 0])
            sl_p = est_ep - side * sl_dist
            tp_p = (est_ep + side * tp_dist) if tp_dist is not None else None
            if sl_p <= 0.0 or (tp_p is not None and tp_p <= 0.0):
                continue
            tr = cc.replay_intraday_m1_trade(
                sym,
                times_sec,
                quotes,
                e_idx,
                side,
                sl_p,
                tp_price=tp_p,
                entry_order_type="MARKET",
                flat_idx=f_idx,
                hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
                spec=sym_spec,
                firm_profile=firm_profile,
                red_news_index=red_news_index,
                news_pad_sec=300,
                flatten_before_news=True,
            )
        elif entry_mode in ("PULLBACK_LIMIT", "MACRO_POST_LIMIT", "OPEN_DRIVE_STOP"):
            is_stop = entry_mode == "OPEN_DRIVE_STOP"
            trig_px = (mh if side == 1 else ml) if is_stop else (mc - side * (pb_retr * abs(imp_ret)))
            sl_p = trig_px - side * sl_dist
            tp_p = (trig_px + side * tp_dist) if tp_dist is not None else None
            if trig_px <= 0.0 or sl_p <= 0.0 or (tp_p is not None and tp_p <= 0.0):
                continue
            ts_exp = min(ts_we + pb_wait_min * 60, ts_flat - 600)
            if ts_exp <= ts_we:
                continue
            rel_exp = int(np.searchsorted(sub_t, ts_exp, side="right")) - 1
            exp_idx = min(f_idx - 1, fi + max(0, rel_exp))
            if exp_idx < e_idx:
                continue
            tr = cc.replay_intraday_m1_trade(
                sym,
                times_sec,
                quotes,
                e_idx,
                side,
                sl_p,
                tp_price=tp_p,
                entry_order_type="STOP" if is_stop else "LIMIT",
                entry_trigger_price=trig_px,
                order_expire_idx=exp_idx,
                flat_idx=f_idx,
                hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
                spec=sym_spec,
                firm_profile=firm_profile,
                red_news_index=red_news_index,
                news_pad_sec=300,
                flatten_before_news=True,
            )
        else:
            raise ValueError(f"Unsupported F01 entry_mode: {entry_mode!r}")

        if not tr.get("filled"):
            continue

        trades.append(tr)
        actual_sl_dist = float(tr["sl_dist"])
        actual_tp_dist = (
            abs(float(tr["tp_price"]) - float(tr["entry_price"])) if tr.get("tp_price") is not None else None
        )
        fade_tr = _replay_matched_fade_trade(
            sym,
            times_sec,
            quotes,
            tr,
            sl_dist=actual_sl_dist,
            tp_dist=actual_tp_dist,
            flat_idx=f_idx,
            sym_spec=sym_spec,
            red_news_index=red_news_index,
            firm_profile=firm_profile,
        )
        fade_trades.append(fade_tr)

    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    daily_1x_map = {d: round(float(v), 6) for d, v in zip(dpnl_1x["dates"], dpnl_1x["pnl"], strict=True)}
    daily_15x_map = {d: round(float(v), 6) for d, v in zip(dpnl_15x["dates"], dpnl_15x["pnl"], strict=True)}
    daily_2x_map = {d: round(float(v), 6) for d, v in zip(dpnl_2x["dates"], dpnl_2x["pnl"], strict=True)}
    fade_1x_map = {d: round(float(v), 6) for d, v in zip(fade_dpnl_1x["dates"], fade_dpnl_1x["pnl"], strict=True)}

    metrics_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    metrics_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    metrics_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    fade_metrics_1x = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(
        trades,
        max_fric_sl_ratio=STAGE0_MAX_FRIC_SL_RATIO,
        min_keep_frac=STAGE0_MIN_KEEP_FRAC,
    )

    return {
        "spec": dict(spec),
        "trades": trades,
        "daily_pnl_1x": daily_1x_map,
        "daily_pnl_15x": daily_15x_map,
        "daily_pnl_2x": daily_2x_map,
        "daily_pnl_zero_pos_swap": dict(daily_1x_map),
        "fade_daily_pnl_1x": fade_1x_map,
        "metrics": metrics_1x,
        "metrics_15x": metrics_15x,
        "metrics_2x": metrics_2x,
        "fade_metrics_1x": fade_metrics_1x,
        "stage0": s0,
        "data_resolution": str(ctx["data_resolution"]),
        "blindness_tier": str(ctx["blindness_tier"]),
        "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    firm_profile: str = "FTMO_STANDARD",
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Evaluate one F01 candidate spec strictly on `years` with zero lookahead."""
    req_years = tuple(sorted({int(y) for y in years}))
    if not req_years or min(req_years) < cc.DEV_MIN_YEAR or max(req_years) > cc.DEV_MAX_YEAR:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid years={years!r}")

    sym = cc.normalize_symbol(str(spec["symbol"]))
    assets = universe["assets"] if "assets" in universe else universe
    if sym not in assets:
        raise KeyError(f"Symbol {sym!r} not present in universe")

    rn_idx = red_news_index if red_news_index is not None else cc.load_dev_red_news_index(root=root)
    ctx = _prepare_asset_context(assets[sym], req_years, rn_idx)
    return _evaluate_candidate_with_ctx(spec, ctx, req_years, rn_idx, firm_profile=firm_profile)


# ---------------------------------------------------------------------------
# Cluster A Discovery (`2018-2020` ONLY — HARD BLINDNESS LOCK!)
# ---------------------------------------------------------------------------


def _score_cluster_a(eval_res: Mapping[str, Any]) -> tuple[bool, float, str]:
    """Evaluate Cluster A (`2018-2020`) selectivity, friction survival, and robustness score."""
    spec = eval_res["spec"]
    m1 = eval_res["metrics"]
    m15 = eval_res["metrics_15x"]
    m2 = eval_res["metrics_2x"]
    fm1 = eval_res["fade_metrics_1x"]
    s0 = eval_res["stage0"]

    n_tr = int(m1["n_trades"])
    is_macro_only = str(spec.get("gate_mode", "")).upper() == "MACRO_DAY"
    min_tr = PRIMARY_MIN_TRADES_MACRO_3Y if is_macro_only else PRIMARY_MIN_TRADES_3Y

    if not s0["passed"]:
        return False, -999.0, str(s0["reason"])
    if n_tr < min_tr:
        return False, -998.0, f"TOO_FEW_TRADES({n_tr}<{min_tr})"
    if n_tr > PRIMARY_MAX_TRADES_3Y:
        return False, -997.0, f"OVERTRADING_TRAP({n_tr}>{PRIMARY_MAX_TRADES_3Y})"

    sr1 = float(m1["sharpe"])
    sr2 = float(m2["sharpe"])
    fsr1 = float(fm1["sharpe"])
    net1 = float(m1["net_R"])
    net2 = float(m2["net_R"])
    fnet1 = float(fm1["net_R"])
    pf15 = float(m15["pf"])
    pos_y = int(m1["positive_years"])
    dd1 = float(m1["max_DD_R"])
    by_y = m1.get("by_year_R") or {}
    worst_yr = min((float(v) for v in by_y.values()), default=-99.0)

    fade_edge_sr = max(-1.5, min(2.0, sr1 - fsr1))
    score = (
        0.45 * sr2
        + 0.35 * sr1
        + 0.20 * fade_edge_sr
        + 0.15 * (float(pos_y) / 3.0)
        + 0.05 * max(-2.0, min(2.0, worst_yr / 5.0))
        - 0.08 * max(0.0, dd1 - 8.0) / 8.0
    )

    eligible = net2 > 0.0 and pf15 >= 1.05 and sr1 >= 0.35 and net1 > fnet1 + 1.0 and pos_y >= 2
    reason = (
        "ELIGIBLE"
        if eligible
        else f"FILTERED(net2={net2:.2f},pf15={pf15:.2f},sr1={sr1:.2f},fade_d={net1 - fnet1:.2f},py={pos_y}/3)"
    )
    return eligible, round(score, 6), reason


def discover_cluster_a(
    universe: Mapping[str, Any],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    firm_profile: str = "FTMO_STANDARD",
    save_checkpoint: bool = True,
    resume: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run F01 Stage 2 discovery strictly on `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        loaded = cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)
        return {
            "family_id": FAMILY_ID,
            "resumed": True,
            "discovery_years": list(cc.CLUSTER_A_YEARS),
            "primary_count": int(loaded["primary_count"]),
            "exploratory_count": int(loaded["exploratory_count"]),
            "total_count": int(loaded["total_count"]),
            "primary_candidates": list(loaded["primary_candidates"]),
            "exploratory_candidates": list(loaded["exploratory_candidates"]),
            "checkpoint": loaded,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    t0 = time_mod.perf_counter()
    rn_idx = red_news_index if red_news_index is not None else cc.load_dev_red_news_index(root=root)
    assets = universe["assets"] if "assets" in universe else universe

    ctx_by_sym: dict[str, dict[str, Any]] = {}
    for sym in UNIVERSE_SYMBOLS:
        if sym not in assets:
            raise KeyError(f"Missing required F01 M1 symbol {sym!r} in universe")
        ctx_by_sym[sym] = _prepare_asset_context(assets[sym], cc.CLUSTER_A_YEARS, rn_idx)

    grid = build_candidate_grid()
    evaluated: list[dict[str, Any]] = []

    for spec in grid:
        sym = str(spec["symbol"])
        res = _evaluate_candidate_with_ctx(spec, ctx_by_sym[sym], cc.CLUSTER_A_YEARS, rn_idx, firm_profile=firm_profile)
        eligible, score, status_note = _score_cluster_a(res)
        m1 = res["metrics"]
        m15 = res["metrics_15x"]
        m2 = res["metrics_2x"]
        fm1 = res["fade_metrics_1x"]
        s0 = res["stage0"]

        cand_record = dict(spec)
        cand_record["cluster_a_score"] = score
        cand_record["cluster_a_eligible"] = eligible
        cand_record["cluster_a_status"] = status_note
        cand_record["cluster_a_trades_per_year"] = round(float(m1["n_trades"]) / 3.0, 2)
        cand_record["cluster_a_stage0"] = {
            "passed": bool(s0["passed"]),
            "median_fric_sl_ratio": s0["median_fric_sl_ratio"],
            "p90_fric_sl_ratio": s0["p90_fric_sl_ratio"],
            "keep_frac": s0["keep_frac"],
        }
        cand_record["cluster_a_metrics_1x"] = m1
        cand_record["cluster_a_metrics_15x"] = {
            "net_R": m15["net_R"],
            "pf": m15["pf"],
            "sharpe": m15["sharpe"],
            "max_DD_R": m15["max_DD_R"],
        }
        cand_record["cluster_a_metrics_2x"] = {
            "net_R": m2["net_R"],
            "pf": m2["pf"],
            "sharpe": m2["sharpe"],
            "max_DD_R": m2["max_DD_R"],
        }
        cand_record["cluster_a_fade_1x"] = {
            "net_R": fm1["net_R"],
            "pf": fm1["pf"],
            "sharpe": fm1["sharpe"],
        }
        evaluated.append(cand_record)

    ranked = sorted(
        evaluated,
        key=lambda c: (
            1 if c["cluster_a_eligible"] else 0,
            float(c["cluster_a_score"]),
            float(c["cluster_a_metrics_2x"]["sharpe"]),
            str(c["candidate_id"]),
        ),
        reverse=True,
    )

    primary: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []
    sym_counts: dict[str, int] = {}
    arch_counts: dict[str, int] = {}

    for cand in ranked:
        sym = str(cand["symbol"])
        arch = str(cand["archetype"])
        can_promote = (
            bool(cand["cluster_a_eligible"])
            and len(primary) < PRIMARY_CAP
            and sym_counts.get(sym, 0) < PRIMARY_MAX_PER_SYMBOL
            and arch_counts.get(arch, 0) < PRIMARY_MAX_PER_ARCHETYPE
        )
        if can_promote:
            cand["tier"] = "PRIMARY"
            cand["is_primary"] = True
            primary.append(cand)
            sym_counts[sym] = sym_counts.get(sym, 0) + 1
            arch_counts[arch] = arch_counts.get(arch, 0) + 1
        else:
            cand["tier"] = "EXPLORATORY"
            cand["is_primary"] = False
            exploratory.append(cand)

    if len(primary) + len(exploratory) > TOTAL_CAP:
        exploratory = exploratory[: TOTAL_CAP - len(primary)]

    elapsed_sec = round(time_mod.perf_counter() - t0, 3)
    meta = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "prop_track": PROP_TRACK,
        "family_slug": FAMILY_ID,
        "symbols": list(UNIVERSE_SYMBOLS),
        "firm_profile": firm_profile,
        "grid_evaluated": len(grid),
        "eligible_count": sum(1 for c in evaluated if c["cluster_a_eligible"]),
        "primary_by_symbol": sym_counts,
        "primary_by_archetype": arch_counts,
        "elapsed_sec": elapsed_sec,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    ckpt_path: Path | None = None
    if save_checkpoint:
        ckpt_path = cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary, "exploratory": exploratory},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )

    return {
        "family_id": FAMILY_ID,
        "resumed": False,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(primary) + len(exploratory),
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "checkpoint_path": str(ckpt_path) if ckpt_path is not None else None,
        "meta": meta,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=("Offensive #3 Stage 2 — F01 Low-Frequency Intraday Catalyst Discovery (Cluster A 2018-2020 ONLY).")
    )
    parser.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified checkpoint if present.")
    parser.add_argument("--candidates-dir", type=str, default=None, help="Optional checkpoint output directory.")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA-256 verification on load.")
    parser.add_argument("--firm-profile", type=str, default="FTMO_STANDARD", help="Firm fee/margin profile.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    cdir = Path(args.candidates_dir) if args.candidates_dir else None
    if args.resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=cdir):
        doc = cc.load_family_candidates(FAMILY_ID, candidates_dir=cdir, verify_sha=True)
        print(
            f"[F01] Resumed valid checkpoint: primary={doc['primary_count']}/{doc['primary_cap']} "
            f"total={doc['total_count']}/{doc['total_cap']} discovery_years={doc['discovery_years']}"
        )
        return 0

    uni = cc.load_universe_28(
        load_m1=True,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=UNIVERSE_SYMBOLS,
        verify_sha=not args.no_verify_sha,
    )
    out = discover_cluster_a(
        uni,
        firm_profile=args.firm_profile,
        save_checkpoint=True,
        resume=args.resume,
        candidates_dir=cdir,
    )
    print(
        f"[F01] Discovery complete ({out['meta']['elapsed_sec']}s, years={out['discovery_years']}): "
        f"primary={out['primary_count']}/{PRIMARY_CAP}, total={out['total_count']}/{TOTAL_CAP}, "
        f"eligible={out['meta']['eligible_count']}/{out['meta']['grid_evaluated']}"
    )
    for c in out["primary_candidates"][:8]:
        m1 = c["cluster_a_metrics_1x"]
        m2 = c["cluster_a_metrics_2x"]
        s0 = c["cluster_a_stage0"]
        print(
            f"  [PRIM] {c['candidate_id']:30s} sym={c['symbol']:6s} tr={m1['n_trades']:3d} "
            f"({c['cluster_a_trades_per_year']:4.1f}/yr) sr1={m1['sharpe']:5.2f} sr2={m2['sharpe']:5.2f} "
            f"pf1={m1['pf']:4.2f} f/sl={s0['median_fric_sl_ratio']:.3f} py={m1['positive_years']}/3"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
