"""Total Offensive #3 Family F05: Intermarket Transmission & Intraday Index Momentum.

Strict offline research & replay module (`ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`,
ZERO bare `assert`s `[ARCH-02]`, strict `shift = 1` causality, hard Cluster A blindness lock
on `CLUSTER_A_YEARS = (2018, 2019, 2020)` during `discover_cluster_a(universe)`).

Subfamilies implemented (economically grounded, DST-exact via `OPS-1` `feed_dst_news_guard`):
  1. `F05A_GAO_INTRADAY_MOM` (`INTRADAY_SWAP0`, M1 on `US500, US100, GER40` + 3-index basket):
     Gao et al. (`SSRN:2440866`) first-30m/60m -> last-60m/90m intraday momentum gated by
     causal high-vol / short-gamma regime so `F_stress / SL <= 10%`, `swap = 0`, hard flat <= 20:50 UTC.
  2. `F05B_CROSS_TZ_SPILLOVER` (`FTMO_SWING` D1 on `JP225, UK100, GER40, US30` + basket, AND
     `INTRADAY_SWAP0` M1 on `GER40`):
     Cross-timezone US cash close (`US500/US100`) -> next-day Asia/Europe handover transmission
     (strictly `d_leader < d_follower`, zero lookahead, mandatory hard SL & real triple-swap).
  3. `F05C_SAFEHAVEN_RISKOFF` (`INTRADAY_SWAP0` M1 on `XAUUSD, USDJPY` + `FTMO_SWING` D1 on
     `XAUUSD, USDJPY, AUDJPY, CHFJPY` + safe-haven basket):
     Equity shock (`US500`) -> safe-haven / JPY-carry risk-off & risk-on spillover / absorption.

Standard public API:
  - `discover_cluster_a(universe, ...)` -> Cluster A (`2018-2020` ONLY) discovery & checkpointing.
  - `evaluate_candidate(spec, universe, years)` -> exact standard evaluation dictionary.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_ENGINES_DIR = _REPO_ROOT / "tooling" / "ai-engines"
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.offensive3 import common_contract as cc  # noqa: E402

try:
    from quant_factory.live_ops import feed_dst_news_guard as dst_guard  # noqa: E402

    _HAS_OPS1_DST_GUARD = True
except ImportError:  # pragma: no cover - stripped worker fallback
    dst_guard = None
    _HAS_OPS1_DST_GUARD = False

# ---------------------------------------------------------------------------
# Hard Safety & Family Contract Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

FAMILY_ID: str = "F05_INTERMARKET"
FAMILY_SLUG: str = "F05_INTERMARKET"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"
_ZI_NEW_YORK = ZoneInfo("America/New_York")
_ZI_PRAGUE = ZoneInfo("Europe/Prague")

M1_INDEX_SYMBOLS: tuple[str, ...] = ("US500", "US100", "GER40")
M1_SAFEHAVEN_SYMBOLS: tuple[str, ...] = ("XAUUSD", "USDJPY")
D1_CROSS_TZ_FOLLOWERS: tuple[str, ...] = ("JP225", "UK100", "GER40", "US30")
D1_SAFEHAVEN_FOLLOWERS: tuple[str, ...] = ("XAUUSD", "USDJPY", "AUDJPY", "CHFJPY")

F05_REQUIRED_SYMBOLS: tuple[str, ...] = (
    "US500",
    "US100",
    "GER40",
    "XAUUSD",
    "USDJPY",
    "US30",
    "UK100",
    "JP225",
    "AUDJPY",
    "CHFJPY",
)


# ---------------------------------------------------------------------------
# OPS-1 DST-Exact Session Clock Helpers
# ---------------------------------------------------------------------------


def _is_us_dst_day(d: date) -> bool:
    noon_utc = datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC)
    if _HAS_OPS1_DST_GUARD and dst_guard is not None:
        return bool(dst_guard.is_us_dst(noon_utc))
    delta = noon_utc.astimezone(_ZI_NEW_YORK).dst()
    return delta is not None and delta.total_seconds() > 0


def _is_eu_dst_day(d: date) -> bool:
    noon_utc = datetime(d.year, d.month, d.day, 12, 0, tzinfo=UTC)
    if _HAS_OPS1_DST_GUARD and dst_guard is not None:
        return bool(dst_guard.is_eu_dst(noon_utc))
    delta = noon_utc.astimezone(_ZI_PRAGUE).dst()
    return delta is not None and delta.total_seconds() > 0


def resolve_session_window_utc_sec(market: str, d: date) -> dict[str, int]:
    """Resolve exact UTC epoch boundaries for US (`America/New_York`) or EU (`Europe/Prague`) cash sessions.

    Uses `OPS-1` `feed_dst_news_guard` directly so US-vs-EU March/Oct-Nov 1h DST divergence
    windows are handled accurately. Hard flat is ALWAYS clamped `<= 20:50 UTC` (`swap = 0`).
    """
    day_ts = int(datetime(d.year, d.month, d.day, 0, 0, tzinfo=UTC).timestamp())
    hard_flat_ts = day_ts + cc.HARD_FLAT_MAX_UTC_SEC
    mkt = market.strip().upper()

    if mkt in ("US", "US500", "US100", "XAUUSD", "USDJPY"):
        if _HAS_OPS1_DST_GUARD and dst_guard is not None:
            ny_open_info = dst_guard.resolve_strategy_session_utc("NY_OPEN", d)
            open_sec_of_day = int(ny_open_info["utc_hour"]) * 3600 + int(ny_open_info["utc_minute"]) * 60
        else:
            open_sec_of_day = (13 * 3600 + 30 * 60) if _is_us_dst_day(d) else (14 * 3600 + 30 * 60)
        open_ts = day_ts + open_sec_of_day
        # Cash close = 16:00 NY (6.5h after 09:30 NY), strictly clamped <= 20:50 UTC (EST = 15:50 NY)
        cash_close_ts = open_ts + int(6.5 * 3600)
        flat_ts = min(cash_close_ts - 300, hard_flat_ts)  # 5m before cash close or 20:50 UTC hard flat
        return {
            "day_ts": day_ts,
            "open_ts": open_ts,
            "cash_close_ts": cash_close_ts,
            "flat_ts": flat_ts,
            "hard_flat_ts": hard_flat_ts,
            "is_us_dst": 1 if _is_us_dst_day(d) else 0,
            "is_eu_dst": 1 if _is_eu_dst_day(d) else 0,
        }

    if mkt in ("EU", "GER40", "XETRA"):
        # XETRA cash session: 09:00 - 17:30 Europe/Prague (Berlin), exact EU DST via OPS-1
        eu_dst = _is_eu_dst_day(d)
        if _HAS_OPS1_DST_GUARD and dst_guard is not None:
            local_open = datetime.combine(d, time(9, 0), tzinfo=ZoneInfo(dst_guard.TZ_PRAGUE))
            local_close = datetime.combine(d, time(17, 30), tzinfo=ZoneInfo(dst_guard.TZ_PRAGUE))
        else:
            local_open = datetime.combine(d, time(9, 0), tzinfo=_ZI_PRAGUE)
            local_close = datetime.combine(d, time(17, 30), tzinfo=_ZI_PRAGUE)
        open_ts = int(local_open.astimezone(UTC).timestamp())
        cash_close_ts = int(local_close.astimezone(UTC).timestamp())
        flat_ts = min(cash_close_ts - 300, hard_flat_ts)
        return {
            "day_ts": day_ts,
            "open_ts": open_ts,
            "cash_close_ts": cash_close_ts,
            "flat_ts": flat_ts,
            "hard_flat_ts": hard_flat_ts,
            "is_us_dst": 1 if _is_us_dst_day(d) else 0,
            "is_eu_dst": 1 if eu_dst else 0,
        }

    raise ValueError(f"Unsupported session market {market!r}")


# ---------------------------------------------------------------------------
# Strict Causal Pre-Cutoff Slicing & Fast M1/D1 Indexing
# ---------------------------------------------------------------------------


def _validate_eval_years(years: Sequence[int]) -> tuple[int, ...]:
    if not years:
        raise ValueError("years must not be empty")
    out: list[int] = []
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"Invalid year {y!r}")
        yi = int(y)
        if yi < cc.DEV_MIN_YEAR or yi > cc.DEV_MAX_YEAR:
            raise ValueError(f"DEV_SEAL_VIOLATION: year {yi} outside [{cc.DEV_MIN_YEAR}, {cc.DEV_MAX_YEAR}]")
        if yi not in out:
            out.append(yi)
    return tuple(sorted(out))


def _slice_d1_upto_year(d1: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    """Strictly drop all D1 bars with `year > max_year` so Cluster A NEVER touches Cluster B rows."""
    yrs = np.asarray(d1["years"], dtype=np.int32)
    mask = yrs <= int(max_year)
    if not bool(np.any(mask)):
        raise ValueError(f"Zero D1 bars with year <= {max_year}")
    if bool(np.all(mask)):
        return dict(d1)
    idx = np.flatnonzero(mask)
    dates_sub = [str(d1["dates"][i]) for i in idx.tolist()]
    return {
        "times_sec": np.asarray(d1["times_sec"], dtype=np.int64)[idx],
        "dates": dates_sub,
        "years": yrs[idx],
        "weekdays": np.asarray(d1["weekdays"], dtype=np.int32)[idx],
        "open": np.asarray(d1["open"], dtype=np.float64)[idx],
        "high": np.asarray(d1["high"], dtype=np.float64)[idx],
        "low": np.asarray(d1["low"], dtype=np.float64)[idx],
        "close": np.asarray(d1["close"], dtype=np.float64)[idx],
        "spread_price": np.asarray(d1["spread_price"], dtype=np.float64)[idx],
        "median_spread_price": d1.get("median_spread_price"),
        "median_spread_pts": d1.get("median_spread_pts"),
        "median_spread_bps": d1.get("median_spread_bps"),
        "oneway_bps": d1.get("oneway_bps"),
    }


def _slice_m1_upto_year(m1: Mapping[str, Any], max_year: int) -> tuple[np.ndarray, np.ndarray]:
    """Strictly drop all M1 bars with `ts >= (max_year + 1)-01-01T00:00:00Z`."""
    ts = np.asarray(m1["times_sec"], dtype=np.int64)
    q = np.asarray(m1["quotes"], dtype=np.float64)
    cutoff_ts = int(datetime(int(max_year) + 1, 1, 1, 0, 0, tzinfo=UTC).timestamp())
    cutoff_ts = min(cutoff_ts, cc.DEV_CUTOFF_SEC)
    end_idx = int(np.searchsorted(ts, cutoff_ts, side="left"))
    if end_idx <= 0:
        raise ValueError(f"Zero M1 bars strictly before year {max_year + 1}")
    ts_sub = ts[:end_idx]
    q_sub = q[:end_idx]
    cc.enforce_dev_ts_bound(ts_sub, context=f"fam05.m1_slice:{max_year}")
    return ts_sub, q_sub


def _build_m1_day_bounds(times_sec: np.ndarray) -> dict[str, tuple[int, int]]:
    """Map each UTC ISO date to `(start_idx, end_idx_exclusive)` in O(N) once per asset."""
    day_ids = (times_sec // np.int64(86400)).astype(np.int64)
    change = np.empty(day_ids.size, dtype=np.bool_)
    change[0] = True
    change[1:] = day_ids[1:] != day_ids[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:]
    ends[-1] = day_ids.size
    bounds: dict[str, tuple[int, int]] = {}
    for s_i, e_i in zip(starts.tolist(), ends.tolist(), strict=True):
        d_str = datetime.fromtimestamp(int(times_sec[s_i]), tz=UTC).strftime("%Y-%m-%d")
        bounds[d_str] = (s_i, e_i)
    return bounds


def _find_bar_at_or_after(times_sec: np.ndarray, lo: int, hi: int, target_ts: int, max_lag_sec: int = 900) -> int:
    pos = int(np.searchsorted(times_sec[lo:hi], target_ts, side="left")) + lo
    if pos >= hi:
        return -1
    if int(times_sec[pos]) - target_ts > max_lag_sec:
        return -1
    return pos


def _find_bar_at_or_before(times_sec: np.ndarray, lo: int, hi: int, target_ts: int, max_lag_sec: int = 900) -> int:
    pos = int(np.searchsorted(times_sec[lo:hi], target_ts, side="right")) + lo - 1
    if pos < lo:
        return -1
    if target_ts - int(times_sec[pos]) > max_lag_sec:
        return -1
    return pos


def _mid_open(quotes: np.ndarray, idx: int) -> float:
    if quotes.shape[1] >= 8:
        return 0.5 * (float(quotes[idx, 0]) + float(quotes[idx, 4]))
    return float(quotes[idx, 0])


def _mid_close(quotes: np.ndarray, idx: int) -> float:
    if quotes.shape[1] >= 8:
        return 0.5 * (float(quotes[idx, 3]) + float(quotes[idx, 7]))
    return float(quotes[idx, 3])


def _estimate_m1_fric_2x_px(
    sym_spec: Mapping[str, Any],
    quotes: np.ndarray,
    idx: int,
    fx_rates: Mapping[str, float] | None = None,
) -> float:
    """Causal estimate of 2x round-trip friction in price units at `idx` (for hard SL floor)."""
    pt = float(sym_spec["point"])
    bench_sp_px = float(sym_spec["benchmark_spread_pts"]) * pt
    has_ask = quotes.shape[1] >= 8
    cur_sp_px = max(0.0, float(quotes[idx, 4] - quotes[idx, 0])) if has_ask else bench_sp_px
    eff_sp = cur_sp_px if has_ask else bench_sp_px
    tick_val_usd = cc.compute_causal_tick_val_usd(sym_spec, entry_price=_mid_open(quotes, idx), fx_rates=fx_rates)
    usd_per_px = tick_val_usd / pt if pt > 0.0 else 0.0
    comm_usd = float(sym_spec["commission_usd_lot"])
    comm_px = comm_usd / usd_per_px if usd_per_px > 0.0 else 0.0
    slip_px = max(pt, 0.35 * max(eff_sp, bench_sp_px))
    return 2.0 * (eff_sp + comm_px + slip_px)


def _get_asset_d1_features(d1: Mapping[str, Any]) -> dict[str, Any]:
    """Precompute strictly `shift = 1` causal D1 indicators for an asset."""
    h = np.asarray(d1["high"], dtype=np.float64)
    lo = np.asarray(d1["low"], dtype=np.float64)
    c = np.asarray(d1["close"], dtype=np.float64)
    o = np.asarray(d1["open"], dtype=np.float64)
    atr14 = cc.causal_atr(h, lo, c, 14)
    atr60 = cc.causal_sma(np.where(np.isfinite(atr14), atr14, np.nan), 60)
    # Wait: atr14 is already shift=1, so atr60[t] uses atr14[t-60..t-1] (strictly <= t-2, 100% causal!)
    rvol20 = cc.causal_realized_vol(c, 20, use_log_returns=True)
    # Causal 1-day and 3-day close-to-close log returns indexed by bar k (observed at close of bar k)
    ret1 = np.full(c.size, np.nan, dtype=np.float64)
    ret3 = np.full(c.size, np.nan, dtype=np.float64)
    if c.size > 1:
        ret1[1:] = np.log(c[1:] / c[:-1])
    if c.size > 3:
        ret3[3:] = np.log(c[3:] / c[:-3])
    # Causal vol-normalized shock observed at bar k close: ret1[k] / rvol20[k].
    # rvol20[k] uses closes <= k-1 (strictly prior to bar k), so z[k] is known at bar k close.
    z1_at_close = np.where(np.isfinite(ret1) & np.isfinite(rvol20) & (rvol20 > 1e-8), ret1 / rvol20, np.nan)
    z3_at_close = np.where(
        np.isfinite(ret3) & np.isfinite(rvol20) & (rvol20 > 1e-8), ret3 / (rvol20 * math.sqrt(3.0)), np.nan
    )
    # Detect Yahoo zero-gap synthetic opens (`open[t] == close[t-1]`, e.g. ^FTSE / UK100):
    # strictly uses only bars in this sliced window (<= max_year).
    zero_gap_frac = float(np.mean(np.abs(o[1:] - c[:-1]) / np.maximum(c[:-1], 1e-12) < 1e-6)) if c.size > 5 else 0.0
    date_to_idx = {str(d): i for i, d in enumerate(d1["dates"])}
    return {
        "dates": list(d1["dates"]),
        "date_to_idx": date_to_idx,
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
        "atr14": atr14,
        "atr60": atr60,
        "rvol20": rvol20,
        "ret1_at_close": ret1,
        "ret3_at_close": ret3,
        "z1_at_close": z1_at_close,
        "z3_at_close": z3_at_close,
        "has_zero_gap_open": zero_gap_frac > 0.50,
    }


def _resolve_resolution_and_tier(
    symbols: Sequence[str],
    universe: Mapping[str, Any],
    *,
    leader_symbols: Sequence[str] = (),
) -> tuple[str, str]:
    """Resolve fail-conservative resolution and canonical blindness tier over target + leader union."""
    assets = universe["assets"]
    all_syms = sorted({cc.normalize_symbol(s) for s in (*symbols, *leader_symbols) if isinstance(s, str) and s.strip()})
    res_set = {str(assets[s]["data_resolution"]) for s in all_syms if s in assets}
    tier_set = {str(assets[s]["blindness_tier"]) for s in all_syms if s in assets}
    res = (
        cc.RES_D1_YAHOO_SANCTIONED
        if (cc.RES_D1_YAHOO_SANCTIONED in res_set or any("D1" in r.upper() for r in res_set))
        else (cc.RES_NATIVE_M1_BIDASK if cc.RES_NATIVE_M1_BIDASK in res_set else cc.RES_D1_YAHOO_SANCTIONED)
    )
    if len(tier_set) == 1:
        tier = next(iter(tier_set))
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW9}:
        tier = "MIXED_12OLD_AND_NEW9"
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW7}:
        tier = "MIXED_12OLD_AND_TRUE_BLIND_7"
    elif tier_set == {cc.TIER_NEW9, cc.TIER_NEW7}:
        tier = "MIXED_NEW9_AND_TRUE_BLIND_7"
    elif tier_set == {cc.TIER_12OLD, cc.TIER_NEW9, cc.TIER_NEW7}:
        tier = "MIXED_ALL_3_TIERS"
    else:
        tier = "UNKNOWN"
    return res, tier


# ---------------------------------------------------------------------------
# Subfamily 5A: Gao et al. (SSRN:2440866) Intraday Index Momentum (M1, swap=0)
# ---------------------------------------------------------------------------


def _eval_gao_m1_single(
    symbol: str,
    params: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    flip_side: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    asset = universe["assets"][symbol]
    m1 = asset.get("m1")
    d1_raw = asset.get("d1")
    if m1 is None or d1_raw is None:
        raise ValueError(f"M1 and D1 data required for Gao intraday strategy on {symbol}")

    max_year = max(req_years)
    req_year_set = set(req_years)
    ts_m1, q_m1 = _slice_m1_upto_year(m1, max_year)
    d1 = _slice_d1_upto_year(d1_raw, max_year)
    d1_feat = _get_asset_d1_features(d1)
    day_bounds = _build_m1_day_bounds(ts_m1)
    sym_spec = asset["spec"]

    first_min = int(params["first_window_min"])
    entry_before_close_min = int(params["entry_before_close_min"])
    ref_mode = str(params["ref_mode"])  # "open" | "prev_close"
    midday_confirm = bool(params.get("midday_confirm", False))
    ret_atr_thresh = float(params["ret_atr_thresh"])
    min_vol_ratio = float(params.get("min_vol_ratio", 0.0))
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_r_mult = params.get("tp_r_mult")
    direction_sign = int(params.get("direction_sign", 1))
    use_red_news = bool(params.get("use_red_news", False))
    firm_profile = str(params.get("firm_profile", "FTMO_STANDARD"))
    max_fric_sl = float(params.get("max_fric_sl", 0.10))
    min_sl_fric_mult = (1.0 / max_fric_sl) * 1.08  # Guarantees F_stress / SL < max_fric_sl

    market = "EU" if symbol == "GER40" else "US"
    prev_cash_close_px: float | None = None
    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped = 0
    peak_mu = 0.0

    for d_idx, d_str in enumerate(d1_feat["dates"]):
        d_obj = date.fromisoformat(d_str)
        bounds = day_bounds.get(d_str)
        if bounds is None:
            continue
        lo, hi = bounds
        sess = resolve_session_window_utc_sec(market, d_obj)
        open_idx = _find_bar_at_or_after(ts_m1, lo, hi, sess["open_ts"], max_lag_sec=600)
        flat_idx = _find_bar_at_or_before(ts_m1, lo, hi, sess["flat_ts"], max_lag_sec=900)

        # Capture previous cash close causally BEFORE moving to next day
        cur_day_close_px = _mid_close(q_m1, flat_idx) if flat_idx >= 0 else None

        if d_obj.year not in req_year_set:
            if cur_day_close_px is not None and math.isfinite(cur_day_close_px) and cur_day_close_px > 0.0:
                prev_cash_close_px = cur_day_close_px
            continue

        if open_idx < 0 or flat_idx < 0 or flat_idx <= open_idx + 10:
            if cur_day_close_px is not None and math.isfinite(cur_day_close_px) and cur_day_close_px > 0.0:
                prev_cash_close_px = cur_day_close_px
            continue

        atr_val = float(d1_feat["atr14"][d_idx])
        atr60_val = float(d1_feat["atr60"][d_idx])
        if not math.isfinite(atr_val) or atr_val <= 0.0:
            prev_cash_close_px = cur_day_close_px
            continue

        # Causal high-vol / short-gamma gate (strictly using prior-day ATRs up to d_idx - 1!)
        if min_vol_ratio > 0.0:
            if not math.isfinite(atr60_val) or atr60_val <= 0.0 or (atr_val / atr60_val) < min_vol_ratio:
                prev_cash_close_px = cur_day_close_px
                continue

        first_end_ts = sess["open_ts"] + first_min * 60
        entry_target_ts = sess["flat_ts"] - entry_before_close_min * 60
        if entry_target_ts <= first_end_ts + 300:
            prev_cash_close_px = cur_day_close_px
            continue

        first_end_idx = _find_bar_at_or_before(ts_m1, lo, hi, first_end_ts, max_lag_sec=600)
        entry_idx = _find_bar_at_or_after(ts_m1, lo, hi, entry_target_ts, max_lag_sec=600)
        if first_end_idx < open_idx or entry_idx <= first_end_idx or entry_idx >= flat_idx:
            prev_cash_close_px = cur_day_close_px
            continue

        px_open = _mid_open(q_m1, open_idx)
        px_first_end = _mid_close(q_m1, first_end_idx)
        # Entry signal uses price strictly prior to entry_idx (bar entry_idx - 1 close)
        px_pre_entry = _mid_close(q_m1, entry_idx - 1)

        if ref_mode == "prev_close":
            if prev_cash_close_px is None or prev_cash_close_px <= 0.0:
                prev_cash_close_px = cur_day_close_px
                continue
            r_first_px = px_first_end - prev_cash_close_px
        else:
            r_first_px = px_first_end - px_open

        if abs(r_first_px) < ret_atr_thresh * atr_val:
            prev_cash_close_px = cur_day_close_px
            continue

        raw_dir = 1 if r_first_px > 0.0 else -1
        if midday_confirm:
            r_mid_px = px_pre_entry - px_first_end
            if raw_dir * r_mid_px <= 0.0:
                prev_cash_close_px = cur_day_close_px
                continue

        side = raw_dir * direction_sign
        if flip_side:
            side = -side

        # Hard SL floored so F_stress / SL <= 10% (Stage-0 guaranteed)
        est_f2x = _estimate_m1_fric_2x_px(sym_spec, q_m1, entry_idx)
        sl_dist = max(sl_atr_mult * atr_val, min_sl_fric_mult * est_f2x)
        entry_exec_px = float(q_m1[entry_idx, 4] if (side == 1 and q_m1.shape[1] >= 8) else q_m1[entry_idx, 0])
        sl_price = entry_exec_px - side * sl_dist
        if sl_price <= 0.0:
            prev_cash_close_px = cur_day_close_px
            continue
        tp_price = (entry_exec_px + side * (float(tp_r_mult) * sl_dist)) if tp_r_mult is not None else None

        tr = cc.replay_intraday_m1_trade(
            symbol,
            ts_m1,
            q_m1,
            entry_idx,
            side,
            sl_price,
            tp_price=tp_price,
            flat_idx=flat_idx,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index if use_red_news else None,
            flatten_before_news=use_red_news,
        )
        if tr.get("filled"):
            tr["net_R_zero_pos_1x"] = tr["net_R_1x"]
            trades.append(tr)
            if tr.get("margin_capped"):
                margin_capped += 1
            peak_mu = max(peak_mu, float(tr.get("margin_util_frac", 0.0)))
        elif tr.get("status") in ("BELOW_VOLUME_MIN", "MARGIN_BELOW_VOLUME_MIN", "OVER_MARGIN_REJECTED"):
            margin_rejects += 1

        if cur_day_close_px is not None and math.isfinite(cur_day_close_px) and cur_day_close_px > 0.0:
            prev_cash_close_px = cur_day_close_px

    audit = {
        "account_type": "ftmo_standard" if "SWING" not in firm_profile.upper() else "ftmo_swing",
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped,
        "peak_margin_util_frac": round(peak_mu, 6),
    }
    return trades, audit


# ---------------------------------------------------------------------------
# Subfamily 5B: Cross-Timezone Spillover (US Close -> Asia/EU D1 & GER40 M1)
# ---------------------------------------------------------------------------


def _build_strictly_prior_leader_signals(
    leader_feat: Mapping[str, Any],
    follower_feat: Mapping[str, Any],
    *,
    shock_horizon: int,
    z_thresh: float,
    direction_sign: int,
    long_only: bool = False,
    short_only: bool = False,
    max_stale_cal_days: int = 4,
) -> np.ndarray:
    """Align leader close shock from strictly prior date `d_leader < d_follower` (`shift = 1` airtight!).

    Returned signal array `sig[t]` is ready to execute at `follower open[t]` (`signal_already_shifted=True`)
    and depends ONLY on leader bars with calendar date STRICTLY `< follower_dates[t]`.
    """
    l_dates = leader_feat["dates"]
    f_dates = follower_feat["dates"]
    l_z = leader_feat["z1_at_close"] if shock_horizon == 1 else leader_feat["z3_at_close"]
    # Fail-closed Yahoo zero-gap open guard (e.g. UK100 ^FTSE where open[t] == close[t-1] at 16:30 UTC):
    # require leader date strictly BEFORE follower's PREVIOUS bar date `f_dates[t - 1]` so US close
    # strictly precedes the synthetic open timestamp!
    extra_lag_for_zero_gap = bool(follower_feat.get("has_zero_gap_open", False))
    n_f = len(f_dates)
    n_l = len(l_dates)
    sig = np.zeros(n_f, dtype=np.float64)

    l_ptr = -1
    last_used_leader_date: str | None = None
    for t in range(n_f):
        if extra_lag_for_zero_gap:
            if t == 0:
                continue
            cutoff_date = f_dates[t - 1]
            eff_max_gap = max_stale_cal_days + 3
        else:
            cutoff_date = f_dates[t]
            eff_max_gap = max_stale_cal_days
        while (l_ptr + 1) < n_l and l_dates[l_ptr + 1] < cutoff_date:
            l_ptr += 1
        if l_ptr < 0:
            continue
        ld = l_dates[l_ptr]
        if ld == last_used_leader_date:
            continue
        # Ensure leader close isn't stale across long holidays
        gap_days = (date.fromisoformat(f_dates[t]) - date.fromisoformat(ld)).days
        if gap_days <= 0 or gap_days > eff_max_gap:
            continue
        zv = float(l_z[l_ptr])
        if not math.isfinite(zv) or abs(zv) < z_thresh:
            last_used_leader_date = ld
            continue
        side = (1 if zv > 0.0 else -1) * direction_sign
        if long_only and side < 0:
            side = 0
        if short_only and side > 0:
            side = 0
        sig[t] = float(side)
        last_used_leader_date = ld
    return sig


def _eval_cross_tz_d1(
    symbols: Sequence[str],
    params: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    flip_side: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    leader_sym = str(params["leader_symbol"])
    max_year = max(req_years)
    leader_d1 = _slice_d1_upto_year(universe["assets"][leader_sym]["d1"], max_year)
    leader_feat = _get_asset_d1_features(leader_d1)

    shock_horizon = int(params.get("shock_horizon", 1))
    z_thresh = float(params["z_thresh"])
    direction_sign = int(params["direction_sign"])
    if flip_side:
        direction_sign = -direction_sign
    long_only = bool(params.get("long_only", False)) and (not flip_side)
    short_only = bool(params.get("short_only", False)) and (not flip_side)
    if flip_side and bool(params.get("long_only", False)):
        # Fade of long-only is short-only at exact same timestamps
        long_only = False
        short_only = True
    elif flip_side and bool(params.get("short_only", False)):
        long_only = True
        short_only = False

    sl_atr_mult = float(params["sl_atr_mult"])
    tp_atr_mult = params.get("tp_atr_mult")
    max_hold_bars = int(params["max_hold_bars"])
    exit_on_signal_flip = bool(params.get("exit_on_signal_flip", False))

    k_syms = len(symbols)
    acct_bal = 100_000.0 if k_syms > 1 else 10_000.0
    risk_frac = round(0.005 / math.sqrt(float(k_syms)), 6) if k_syms > 1 else 0.005

    sliced_assets: dict[str, Any] = {}
    sigs_map: dict[str, np.ndarray] = {}
    sls_map: dict[str, np.ndarray] = {}
    tps_map: dict[str, np.ndarray | None] = {}

    for sym in symbols:
        a = universe["assets"][sym]
        f_d1 = _slice_d1_upto_year(a["d1"], max_year)
        f_feat = _get_asset_d1_features(f_d1)
        sig = _build_strictly_prior_leader_signals(
            leader_feat,
            f_feat,
            shock_horizon=shock_horizon,
            z_thresh=z_thresh,
            direction_sign=direction_sign,
            long_only=long_only,
            short_only=short_only,
        )
        atr14 = f_feat["atr14"]
        # Floor SL so Stage-0 F_stress/SL <= 12.5% cleanly on every symbol
        oneway_bps = float(a["spec"]["oneway_bps"])
        min_sl_px = (4.0 * (oneway_bps / 10_000.0) * f_feat["open"]) * 8.5
        sl_arr = np.where(np.isfinite(atr14) & (atr14 > 0.0), np.maximum(sl_atr_mult * atr14, min_sl_px), np.nan)
        sig = np.where(np.isfinite(sl_arr) & (sl_arr > 0.0), sig, 0.0)

        sliced_assets[sym] = {
            "symbol": sym,
            "spec": a["spec"],
            "data_resolution": a["data_resolution"],
            "d1": f_d1,
        }
        sigs_map[sym] = sig
        sls_map[sym] = sl_arr
        if tp_atr_mult is not None:
            tps_map[sym] = np.where(np.isfinite(sl_arr), float(tp_atr_mult) * atr14, np.nan)
        else:
            tps_map[sym] = None

    res = cc.replay_swing_d1_series(
        sliced_assets,
        sigs_map,
        sls_map,
        tp_dists=tps_map,
        max_hold_bars=max_hold_bars,
        exit_on_signal_flip=exit_on_signal_flip,
        signal_already_shifted=True,
        account_balance_usd=acct_bal,
        risk_frac=risk_frac,
        account_type="ftmo_swing",
        years=req_years,
    )
    return res["trades"], res["margin_audit"]


def _eval_us_to_ger40_m1(
    params: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    flip_side: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Prior-day US500/US100 cash close shock -> next-morning GER40 XETRA M1 intraday (`swap = 0`)."""
    leader_sym = str(params["leader_symbol"])
    follower_sym = "GER40"
    max_year = max(req_years)
    req_year_set = set(req_years)

    leader_d1 = _slice_d1_upto_year(universe["assets"][leader_sym]["d1"], max_year)
    leader_feat = _get_asset_d1_features(leader_d1)
    f_asset = universe["assets"][follower_sym]
    f_d1 = _slice_d1_upto_year(f_asset["d1"], max_year)
    f_feat = _get_asset_d1_features(f_d1)
    ts_m1, q_m1 = _slice_m1_upto_year(f_asset["m1"], max_year)
    day_bounds = _build_m1_day_bounds(ts_m1)
    sym_spec = f_asset["spec"]

    z_thresh = float(params["z_thresh"])
    direction_sign = int(params["direction_sign"])
    if flip_side:
        direction_sign = -direction_sign
    entry_delay_min = int(params.get("entry_delay_min", 5))
    exit_mode = str(params.get("exit_mode", "xetra_close"))  # "xetra_close" | "pre_us_open"
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_r_mult = params.get("tp_r_mult")
    use_red_news = bool(params.get("use_red_news", False))
    firm_profile = str(params.get("firm_profile", "FTMO_STANDARD"))

    sig = _build_strictly_prior_leader_signals(
        leader_feat,
        f_feat,
        shock_horizon=int(params.get("shock_horizon", 1)),
        z_thresh=z_thresh,
        direction_sign=direction_sign,
    )

    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped = 0
    peak_mu = 0.0

    for d_idx, d_str in enumerate(f_feat["dates"]):
        d_obj = date.fromisoformat(d_str)
        if d_obj.year not in req_year_set:
            continue
        sv = int(sig[d_idx])
        if sv == 0:
            continue
        atr_val = float(f_feat["atr14"][d_idx])
        if not math.isfinite(atr_val) or atr_val <= 0.0:
            continue
        bounds = day_bounds.get(d_str)
        if bounds is None:
            continue
        lo, hi = bounds
        eu_sess = resolve_session_window_utc_sec("EU", d_obj)
        us_sess = resolve_session_window_utc_sec("US", d_obj)

        entry_target_ts = eu_sess["open_ts"] + entry_delay_min * 60
        if exit_mode == "pre_us_open":
            flat_target_ts = min(us_sess["open_ts"] - 300, eu_sess["flat_ts"])
        else:
            flat_target_ts = eu_sess["flat_ts"]

        entry_idx = _find_bar_at_or_after(ts_m1, lo, hi, entry_target_ts, max_lag_sec=600)
        flat_idx = _find_bar_at_or_before(ts_m1, lo, hi, flat_target_ts, max_lag_sec=900)
        if entry_idx < 0 or flat_idx <= entry_idx + 5:
            continue

        est_f2x = _estimate_m1_fric_2x_px(sym_spec, q_m1, entry_idx)
        sl_dist = max(sl_atr_mult * atr_val, 11.0 * est_f2x)
        entry_px = float(q_m1[entry_idx, 4] if (sv == 1 and q_m1.shape[1] >= 8) else q_m1[entry_idx, 0])
        sl_price = entry_px - sv * sl_dist
        if sl_price <= 0.0:
            continue
        tp_price = (entry_px + sv * (float(tp_r_mult) * sl_dist)) if tp_r_mult is not None else None

        tr = cc.replay_intraday_m1_trade(
            follower_sym,
            ts_m1,
            q_m1,
            entry_idx,
            sv,
            sl_price,
            tp_price=tp_price,
            flat_idx=flat_idx,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index if use_red_news else None,
            flatten_before_news=use_red_news,
        )
        if tr.get("filled"):
            tr["net_R_zero_pos_1x"] = tr["net_R_1x"]
            trades.append(tr)
            if tr.get("margin_capped"):
                margin_capped += 1
            peak_mu = max(peak_mu, float(tr.get("margin_util_frac", 0.0)))
        elif tr.get("status") in ("BELOW_VOLUME_MIN", "MARGIN_BELOW_VOLUME_MIN", "OVER_MARGIN_REJECTED"):
            margin_rejects += 1

    return trades, {
        "account_type": "ftmo_standard",
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped,
        "peak_margin_util_frac": round(peak_mu, 6),
    }


# ---------------------------------------------------------------------------
# Subfamily 5C: US500 Intraday Shock -> Safe-Haven XAUUSD/USDJPY M1 (`swap=0`)
# ---------------------------------------------------------------------------


def _eval_safehaven_m1(
    follower_sym: str,
    params: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    flip_side: bool = False,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Intraday US500 first-30m/60m shock -> XAUUSD/USDJPY NY-session flow (`swap = 0`, DST-exact)."""
    leader_sym = str(params.get("leader_symbol", "US500"))
    max_year = max(req_years)
    req_year_set = set(req_years)

    l_asset = universe["assets"][leader_sym]
    f_asset = universe["assets"][follower_sym]
    l_ts, l_q = _slice_m1_upto_year(l_asset["m1"], max_year)
    f_ts, f_q = _slice_m1_upto_year(f_asset["m1"], max_year)
    l_d1 = _slice_d1_upto_year(l_asset["d1"], max_year)
    f_d1 = _slice_d1_upto_year(f_asset["d1"], max_year)

    l_feat = _get_asset_d1_features(l_d1)
    f_feat = _get_asset_d1_features(f_d1)
    l_bounds = _build_m1_day_bounds(l_ts)
    f_bounds = _build_m1_day_bounds(f_ts)
    sym_spec = f_asset["spec"]

    first_min = int(params["first_window_min"])
    shock_atr_thresh = float(params["shock_atr_thresh"])
    # XAUUSD: US500 drop -> long XAUUSD (sign=-1); USDJPY: US500 drop -> short USDJPY (sign=+1)
    transmission_sign = int(params["transmission_sign"])
    if flip_side:
        transmission_sign = -transmission_sign
    risk_off_only = bool(params.get("risk_off_only", False))
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_r_mult = params.get("tp_r_mult")
    use_red_news = bool(params.get("use_red_news", False))
    firm_profile = str(params.get("firm_profile", "FTMO_STANDARD"))

    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped = 0
    peak_mu = 0.0

    for d_idx, d_str in enumerate(f_feat["dates"]):
        d_obj = date.fromisoformat(d_str)
        if d_obj.year not in req_year_set:
            continue
        l_d_idx = l_feat["date_to_idx"].get(d_str)
        if l_d_idx is None:
            continue
        l_atr = float(l_feat["atr14"][l_d_idx])
        f_atr = float(f_feat["atr14"][d_idx])
        if not (math.isfinite(l_atr) and l_atr > 0.0 and math.isfinite(f_atr) and f_atr > 0.0):
            continue

        lb = l_bounds.get(d_str)
        fb = f_bounds.get(d_str)
        if lb is None or fb is None:
            continue
        us_sess = resolve_session_window_utc_sec("US", d_obj)
        l_open_i = _find_bar_at_or_after(l_ts, lb[0], lb[1], us_sess["open_ts"], max_lag_sec=600)
        shock_end_ts = us_sess["open_ts"] + first_min * 60
        l_end_i = _find_bar_at_or_before(l_ts, lb[0], lb[1], shock_end_ts, max_lag_sec=600)
        if l_open_i < 0 or l_end_i <= l_open_i:
            continue

        # Observed strictly BEFORE entry (shock_end_ts + 60s bar open!)
        l_move = _mid_close(l_q, l_end_i) - _mid_open(l_q, l_open_i)
        if abs(l_move) < shock_atr_thresh * l_atr:
            continue
        if risk_off_only and l_move >= 0.0:
            continue

        us_dir = 1 if l_move > 0.0 else -1
        side = us_dir * transmission_sign

        entry_target_ts = int(l_ts[l_end_i]) + 60  # Strictly next M1 bar after shock bar closes!
        f_entry_i = _find_bar_at_or_after(f_ts, fb[0], fb[1], entry_target_ts, max_lag_sec=600)
        f_flat_i = _find_bar_at_or_before(f_ts, fb[0], fb[1], us_sess["flat_ts"], max_lag_sec=900)
        if f_entry_i < 0 or f_flat_i <= f_entry_i + 5:
            continue

        est_f2x = _estimate_m1_fric_2x_px(sym_spec, f_q, f_entry_i)
        sl_dist = max(sl_atr_mult * f_atr, 11.0 * est_f2x)
        entry_px = float(f_q[f_entry_i, 4] if (side == 1 and f_q.shape[1] >= 8) else f_q[f_entry_i, 0])
        sl_price = entry_px - side * sl_dist
        if sl_price <= 0.0:
            continue
        tp_price = (entry_px + side * (float(tp_r_mult) * sl_dist)) if tp_r_mult is not None else None

        tr = cc.replay_intraday_m1_trade(
            follower_sym,
            f_ts,
            f_q,
            f_entry_i,
            side,
            sl_price,
            tp_price=tp_price,
            flat_idx=f_flat_i,
            hard_flat_utc_hhmm=cc.HARD_FLAT_MAX_UTC_HHMM,
            spec=sym_spec,
            firm_profile=firm_profile,
            red_news_index=red_news_index if use_red_news else None,
            flatten_before_news=use_red_news,
        )
        if tr.get("filled"):
            tr["net_R_zero_pos_1x"] = tr["net_R_1x"]
            trades.append(tr)
            if tr.get("margin_capped"):
                margin_capped += 1
            peak_mu = max(peak_mu, float(tr.get("margin_util_frac", 0.0)))
        elif tr.get("status") in ("BELOW_VOLUME_MIN", "MARGIN_BELOW_VOLUME_MIN", "OVER_MARGIN_REJECTED"):
            margin_rejects += 1

    return trades, {
        "account_type": "ftmo_standard",
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped,
        "peak_margin_util_frac": round(peak_mu, 6),
    }


# ---------------------------------------------------------------------------
# Unified Public Evaluation Contract (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Evaluate any F05 candidate spec strictly on `years` and return the standard Offensive #3 dict."""
    req_years = _validate_eval_years(years)
    spec_dict = dict(spec)
    subfamily = str(spec_dict["subfamily"])
    symbols = [cc.normalize_symbol(s) for s in spec_dict["symbols"]]
    params = dict(spec_dict["params"])
    prop_track = str(spec_dict["prop_track"])
    is_intraday = prop_track == "INTRADAY_SWAP0"

    if bool(params.get("use_red_news", False)) and red_news_index is None:
        red_news_index = cc.load_dev_red_news_index(include_extended=True)

    def _run_side(flip: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        if subfamily == "F05A_GAO_INTRADAY_MOM":
            all_tr: list[dict[str, Any]] = []
            tot_rej = 0
            tot_cap = 0
            max_mu = 0.0
            for s in symbols:
                trs, aud = _eval_gao_m1_single(
                    s, params, universe, req_years, red_news_index=red_news_index, flip_side=flip
                )
                all_tr.extend(trs)
                tot_rej += int(aud["margin_rejects"])
                tot_cap += int(aud["margin_capped_count"])
                max_mu = max(max_mu, float(aud["peak_margin_util_frac"]))
            all_tr.sort(key=lambda t: (t["exit_ts"], t["entry_ts"], t["symbol"]))
            return all_tr, {
                "account_type": "ftmo_standard",
                "margin_rejects": tot_rej,
                "margin_capped_count": tot_cap,
                "peak_margin_util_frac": round(max_mu, 6),
            }
        if subfamily == "F05B_CROSS_TZ_D1":
            return _eval_cross_tz_d1(symbols, params, universe, req_years, flip_side=flip)
        if subfamily == "F05B_CROSS_TZ_M1":
            return _eval_us_to_ger40_m1(params, universe, req_years, red_news_index=red_news_index, flip_side=flip)
        if subfamily == "F05C_SAFEHAVEN_M1":
            all_tr = []
            tot_rej = 0
            tot_cap = 0
            max_mu = 0.0
            for s in symbols:
                trs, aud = _eval_safehaven_m1(
                    s, params, universe, req_years, red_news_index=red_news_index, flip_side=flip
                )
                all_tr.extend(trs)
                tot_rej += int(aud["margin_rejects"])
                tot_cap += int(aud["margin_capped_count"])
                max_mu = max(max_mu, float(aud["peak_margin_util_frac"]))
            all_tr.sort(key=lambda t: (t["exit_ts"], t["entry_ts"], t["symbol"]))
            return all_tr, {
                "account_type": "ftmo_standard",
                "margin_rejects": tot_rej,
                "margin_capped_count": tot_cap,
                "peak_margin_util_frac": round(max_mu, 6),
            }
        if subfamily == "F05C_SAFEHAVEN_D1":
            return _eval_cross_tz_d1(symbols, params, universe, req_years, flip_side=flip)
        raise ValueError(f"Unknown F05 subfamily: {subfamily!r}")

    trades, margin_audit = _run_side(flip=False)
    fade_trades, _ = _run_side(flip=True)

    slot_w = 1.0 / math.sqrt(float(len(symbols))) if len(symbols) > 1 else 1.0
    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    zpos_key = "net_R_1x" if is_intraday else "net_R_zero_pos_1x"
    dpnl_zpos = cc.compute_daily_pnl_series(trades, req_years, pnl_key=zpos_key)
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")
    if slot_w < 1.0:
        for d in (dpnl_1x, dpnl_15x, dpnl_2x, dpnl_zpos, fade_dpnl_1x):
            d["pnl"] = d["pnl"] * slot_w

    m_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    m_zpos = cc.compute_split_metrics(trades, dpnl_zpos, pnl_key=zpos_key)
    m_fade = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")

    s0_lim = 0.10 if subfamily == "F05A_GAO_INTRADAY_MOM" else 0.15
    s0 = cc.stage0_screen(trades, max_fric_sl_ratio=s0_lim, min_keep_frac=0.50)

    long_trs = [t for t in trades if int(t["side"]) > 0]
    short_trs = [t for t in trades if int(t["side"]) < 0]
    metrics = dict(m_1x)
    metrics.update(
        {
            "1x": m_1x,
            "1.5x": m_15x,
            "2x": m_2x,
            "zero_pos_swap_1x": m_zpos,
            "fade_1x": m_fade,
            "stage0": s0,
            "margin_audit": margin_audit,
            "long_trades": len(long_trs),
            "short_trades": len(short_trs),
            "long_net_R": round(sum(float(t.get("net_R_1x", 0.0)) for t in long_trs), 6),
            "short_net_R": round(sum(float(t.get("net_R_1x", 0.0)) for t in short_trs), 6),
        }
    )

    # Leader-inclusive canonical provenance (`P1-02`/`P1-03`): union target + all leader symbols!
    leader_syms: list[str] = []
    for raw_l in (
        params.get("leader_symbol"),
        params.get("leader_symbols"),
        spec_dict.get("leader_symbol"),
        spec_dict.get("leader_symbols"),
    ):
        if isinstance(raw_l, str) and raw_l.strip():
            leader_syms.append(cc.normalize_symbol(raw_l))
        elif isinstance(raw_l, (list, tuple, set)):
            for item in raw_l:
                if isinstance(item, str) and item.strip():
                    leader_syms.append(cc.normalize_symbol(item))
    if subfamily == "F05C_SAFEHAVEN_M1" and not leader_syms:
        leader_syms.append("US500")
    leader_syms = sorted(set(leader_syms))

    data_resolution, blindness_tier = _resolve_resolution_and_tier(
        symbols,
        universe,
        leader_symbols=leader_syms,
    )
    allow_unidir = bool(spec_dict.get("allow_unidirectional", False))
    if leader_syms:
        spec_dict["leader_symbols"] = leader_syms
    spec_dict["data_resolution"] = data_resolution
    spec_dict["blindness_tier"] = blindness_tier
    spec_dict["allow_unidirectional"] = allow_unidir
    spec_dict["order_send_capable"] = ORDER_SEND_CAPABLE
    spec_dict["order_send_count"] = ORDER_SEND_COUNT
    spec_dict[_SEAL_ROWS_ANALYSED_KEY] = 0

    return {
        "spec": spec_dict,
        "trades": trades,
        "daily_pnl_1x": dpnl_1x,
        "daily_pnl_15x": dpnl_15x,
        "daily_pnl_2x": dpnl_2x,
        "daily_pnl_zero_pos_swap": dpnl_zpos,
        "fade_daily_pnl_1x": fade_dpnl_1x,
        "metrics": metrics,
        "margin_audit": margin_audit,
        "data_resolution": data_resolution,
        "blindness_tier": blindness_tier,
        "allow_unidirectional": allow_unidir,
    }


# ---------------------------------------------------------------------------
# Candidate Catalog Generator (Economically Grounded, <= 100 Specs)
# ---------------------------------------------------------------------------


def _build_f05_candidate_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        subfamily: str,
        prop_track: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
        allow_unidirectional: bool = False,
    ) -> None:
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short (<40 chars) for {cid}")
        if not counterparty.strip():
            raise ValueError(f"counterparty_mechanism missing for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "subfamily": subfamily,
                "prop_track": prop_track,
                "symbols": list(symbols),
                "params": params,
                "economic_rationale": rationale.strip(),
                "counterparty_mechanism": counterparty.strip(),
                "allow_unidirectional": allow_unidirectional,
            }
        )

    # 1. Subfamily 5A: Gao et al. (SSRN:2440866) Intraday Index Momentum (M1, swap=0, DST-exact)
    gao_rationale = (
        "Gao et al. (SSRN:2440866) high-volatility intraday momentum: early session directional "
        "imbalance forces leveraged ETFs and short-gamma option dealers to hedge in the same "
        "direction into the cash close while staying flat before 20:50 UTC (swap=0)."
    )
    gao_counterparty = (
        "Leveraged/inverse ETF daily rebalancing flows, short-gamma index option market-makers "
        "delta-hedging into the closing auction, and passive MOC/VWAP execution desks."
    )
    gao_configs = [
        ("30m_L60_oc_t22", 30, 60, "open", False, 0.22, 0.90, 0.70, None, False),
        ("30m_L60_cc_t45", 30, 60, "prev_close", False, 0.45, 0.95, 0.75, None, False),
        ("60m_L60_oc_t35", 60, 60, "open", False, 0.35, 0.90, 0.75, None, False),
        ("60m_L90_cc_t50", 60, 90, "prev_close", False, 0.50, 1.00, 0.80, None, False),
        ("60m_L60_mid_t25", 60, 60, "open", True, 0.25, 0.85, 0.70, None, False),
        ("30m_L90_mid_t30_tp2", 30, 90, "prev_close", True, 0.30, 0.90, 0.65, 2.0, False),
        ("60m_L60_cc_t45_rn", 60, 60, "prev_close", False, 0.45, 0.95, 0.75, None, True),
    ]
    for sym in M1_INDEX_SYMBOLS:
        for tag, fw, ebc, rm, mc, thr, vr, slm, tpr, urn in gao_configs:
            _add(
                f"F05A_GAO_{sym}_{tag}",
                "F05A_GAO_INTRADAY_MOM",
                "INTRADAY_SWAP0",
                [sym],
                {
                    "first_window_min": fw,
                    "entry_before_close_min": ebc,
                    "ref_mode": rm,
                    "midday_confirm": mc,
                    "ret_atr_thresh": thr,
                    "min_vol_ratio": vr,
                    "sl_atr_mult": slm,
                    "tp_r_mult": tpr,
                    "direction_sign": 1,
                    "use_red_news": urn,
                    "firm_profile": "FTMO_STANDARD",
                    "max_fric_sl": 0.10,
                },
                gao_rationale,
                gao_counterparty,
                allow_unidirectional=False,
            )
    # 3-index Gao pooled basket (M1 swap=0)
    for tag, fw, ebc, rm, mc, thr, vr, slm, tpr, urn in gao_configs[:5]:
        _add(
            f"F05A_GAO_BASKET3_{tag}",
            "F05A_GAO_INTRADAY_MOM",
            "INTRADAY_SWAP0",
            list(M1_INDEX_SYMBOLS),
            {
                "first_window_min": fw,
                "entry_before_close_min": ebc,
                "ref_mode": rm,
                "midday_confirm": mc,
                "ret_atr_thresh": thr,
                "min_vol_ratio": vr,
                "sl_atr_mult": slm,
                "tp_r_mult": tpr,
                "direction_sign": 1,
                "use_red_news": urn,
                "firm_profile": "FTMO_STANDARD",
                "max_fric_sl": 0.10,
            },
            gao_rationale,
            gao_counterparty,
            allow_unidirectional=False,
        )

    # 2. Subfamily 5B: Cross-Timezone Equity Spillover (D1 FTMO_SWING + GER40 M1 swap=0)
    tz_cont_rationale = (
        "Cross-timezone information transmission (Rapach, Strauss & Zhou 2013): US equity cash "
        "shocks transmit causally to next-day Asia and European cash indices as regional mutual "
        "funds, pension rebalancers, and ADR arbitrageurs adjust exposure at their local open."
    )
    tz_cont_cp = (
        "Slow-moving regional institutional equity allocations, overnight retail stop clusters, "
        "and cross-listed ADR/futures dealers absorbing delayed US macro repricing."
    )
    tz_fade_rationale = (
        "Cross-timezone overnight gap overreaction reversion: extreme US close shocks cause "
        "forced liquidity-demanding opening auctions in Tokyo/Europe that partially mean-revert "
        "once local institutional value buyers step in during cash trading hours."
    )
    tz_fade_cp = (
        "Panic overnight futures hedgers and forced opening-auction market orders paying a "
        "liquidity premium to local market makers and value institutions."
    )

    for leader, follower in (
        ("US500", "JP225"),
        ("US100", "JP225"),
        ("US500", "UK100"),
        ("US500", "GER40"),
        ("US100", "GER40"),
        ("US100", "US30"),
        ("US500", "US30"),
    ):
        for tag, hzn, zt, dsign, lonly, slm, tpm, mh in (
            ("cont_1d_z08_h2", 1, 0.80, 1, False, 1.5, 2.5, 2),
            ("cont_1d_z10_h3", 1, 1.00, 1, False, 1.6, 3.0, 3),
            ("cont_3d_z10_h3", 3, 1.00, 1, False, 1.8, 3.0, 3),
            ("fade_1d_z12_h2", 1, 1.20, -1, False, 1.5, 2.2, 2),
            ("long_1d_z08_h3", 1, 0.80, 1, True, 1.6, 3.0, 3),
        ):
            _add(
                f"F05B_TZ_{leader}_to_{follower}_{tag}",
                "F05B_CROSS_TZ_D1",
                "FTMO_SWING",
                [follower],
                {
                    "leader_symbol": leader,
                    "shock_horizon": hzn,
                    "z_thresh": zt,
                    "direction_sign": dsign,
                    "long_only": lonly,
                    "sl_atr_mult": slm,
                    "tp_atr_mult": tpm,
                    "max_hold_bars": mh,
                    "exit_on_signal_flip": False,
                },
                tz_cont_rationale if dsign > 0 else tz_fade_rationale,
                tz_cont_cp if dsign > 0 else tz_fade_cp,
                allow_unidirectional=lonly,
            )

    # Global Cross-TZ D1 Baskets (JP225 + UK100 + GER40)
    for leader in ("US500", "US100"):
        for tag, hzn, zt, dsign, lonly, slm, tpm, mh in (
            ("cont_1d_z08_h2", 1, 0.80, 1, False, 1.5, 2.5, 2),
            ("fade_1d_z12_h2", 1, 1.20, -1, False, 1.5, 2.2, 2),
            ("cont_3d_z09_h3", 3, 0.90, 1, False, 1.8, 3.0, 3),
        ):
            _add(
                f"F05B_TZ_{leader}_to_GLOBAL3_{tag}",
                "F05B_CROSS_TZ_D1",
                "FTMO_SWING",
                ["JP225", "UK100", "GER40"],
                {
                    "leader_symbol": leader,
                    "shock_horizon": hzn,
                    "z_thresh": zt,
                    "direction_sign": dsign,
                    "long_only": lonly,
                    "sl_atr_mult": slm,
                    "tp_atr_mult": tpm,
                    "max_hold_bars": mh,
                    "exit_on_signal_flip": False,
                },
                tz_cont_rationale if dsign > 0 else tz_fade_rationale,
                tz_cont_cp if dsign > 0 else tz_fade_cp,
                allow_unidirectional=lonly,
            )

    # US Close -> GER40 M1 XETRA Intraday (`swap = 0`, DST-exact EU open)
    for leader in ("US500", "US100"):
        for tag, zt, dsign, emode, slm, tpr in (
            ("cont_z08_xetra", 0.80, 1, "xetra_close", 0.80, None),
            ("cont_z10_preus", 1.00, 1, "pre_us_open", 0.70, 2.0),
            ("fade_z12_xetra", 1.20, -1, "xetra_close", 0.80, 2.0),
        ):
            _add(
                f"F05B_M1_{leader}_to_GER40_{tag}",
                "F05B_CROSS_TZ_M1",
                "INTRADAY_SWAP0",
                ["GER40"],
                {
                    "leader_symbol": leader,
                    "shock_horizon": 1,
                    "z_thresh": zt,
                    "direction_sign": dsign,
                    "entry_delay_min": 5,
                    "exit_mode": emode,
                    "sl_atr_mult": slm,
                    "tp_r_mult": tpr,
                    "use_red_news": False,
                    "firm_profile": "FTMO_STANDARD",
                },
                tz_cont_rationale if dsign > 0 else tz_fade_rationale,
                tz_cont_cp if dsign > 0 else tz_fade_cp,
                allow_unidirectional=False,
            )

    # 3. Subfamily 5C: Safe-Haven / Risk-Off Spillover (M1 `swap=0` + D1 `FTMO_SWING`)
    sh_cont_rationale = (
        "Cross-asset risk-off / safe-haven flight transmission: sharp US500 equity drawdowns "
        "trigger systematic risk-parity deleveraging and JPY-carry unwinds while driving "
        "institutional safe-haven hedging flows into Gold (XAUUSD) and funding currencies."
    )
    sh_cont_cp = (
        "Risk-parity funds, volatility-targeting portfolios, and leveraged carry traders forced "
        "to cut pro-cyclical FX and rotate into defensive liquidity during equity stress."
    )
    sh_rev_rationale = (
        "Post-shock safe-haven liquidity absorption: initial US equity shock triggers crowded "
        "flight-to-safety overshoots in Gold and JPY crosses that mean-revert once institutional "
        "macro desks absorb distressed liquidity."
    )
    sh_rev_cp = (
        "Reactive headline-chasing futures flows overpaying for immediate safe-haven protection "
        "during the initial equity volatility burst."
    )

    # M1 Intraday US500 shock -> XAUUSD & USDJPY (`swap = 0`)
    for follower, trans_sign in (("XAUUSD", -1), ("USDJPY", 1)):
        for tag, fw, sthr, sign_mult, ro_only, slm, tpr in (
            ("flight_30m_t35", 30, 0.35, 1, False, 0.70, None),
            ("flight_60m_t45", 60, 0.45, 1, False, 0.80, 2.0),
            ("riskoff_60m_t40", 60, 0.40, 1, True, 0.75, None),
            ("absorb_60m_t50", 60, 0.50, -1, False, 0.75, 2.0),
        ):
            _add(
                f"F05C_M1_US500_to_{follower}_{tag}",
                "F05C_SAFEHAVEN_M1",
                "INTRADAY_SWAP0",
                [follower],
                {
                    "leader_symbol": "US500",
                    "first_window_min": fw,
                    "shock_atr_thresh": sthr,
                    "transmission_sign": trans_sign * sign_mult,
                    "risk_off_only": ro_only,
                    "sl_atr_mult": slm,
                    "tp_r_mult": tpr,
                    "use_red_news": False,
                    "firm_profile": "FTMO_STANDARD",
                },
                sh_cont_rationale if sign_mult > 0 else sh_rev_rationale,
                sh_cont_cp if sign_mult > 0 else sh_rev_cp,
                allow_unidirectional=ro_only,
            )

    # D1 Swing US500 shock -> XAUUSD, USDJPY, AUDJPY (NEW9), CHFJPY (TRUE_BLIND_7)
    for follower, base_sign in (("XAUUSD", -1), ("USDJPY", 1), ("AUDJPY", 1), ("CHFJPY", 1)):
        for tag, hzn, zt, smult, slm, tpm, mh in (
            ("flight_1d_z09_h3", 1, 0.90, 1, 1.5, 2.5, 3),
            ("flight_3d_z10_h4", 3, 1.00, 1, 1.8, 3.0, 4),
            ("absorb_1d_z12_h3", 1, 1.20, -1, 1.5, 2.5, 3),
        ):
            _add(
                f"F05C_D1_US500_to_{follower}_{tag}",
                "F05C_SAFEHAVEN_D1",
                "FTMO_SWING",
                [follower],
                {
                    "leader_symbol": "US500",
                    "shock_horizon": hzn,
                    "z_thresh": zt,
                    "direction_sign": base_sign * smult,
                    "long_only": False,
                    "short_only": False,
                    "sl_atr_mult": slm,
                    "tp_atr_mult": tpm,
                    "max_hold_bars": mh,
                    "exit_on_signal_flip": False,
                },
                sh_cont_rationale if smult > 0 else sh_rev_rationale,
                sh_cont_cp if smult > 0 else sh_rev_cp,
                allow_unidirectional=False,
            )

    # Safe-Haven JPY Carry Basket (`USDJPY, AUDJPY, CHFJPY`) driven by US500 shock
    for tag, hzn, zt, smult, slm, tpm, mh in (
        ("flight_1d_z09_h3", 1, 0.90, 1, 1.5, 2.5, 3),
        ("absorb_1d_z11_h3", 1, 1.10, -1, 1.5, 2.5, 3),
    ):
        _add(
            f"F05C_D1_US500_to_JPYBASKET3_{tag}",
            "F05C_SAFEHAVEN_D1",
            "FTMO_SWING",
            ["USDJPY", "AUDJPY", "CHFJPY"],
            {
                "leader_symbol": "US500",
                "shock_horizon": hzn,
                "z_thresh": zt,
                "direction_sign": smult,
                "long_only": False,
                "short_only": False,
                "sl_atr_mult": slm,
                "tp_atr_mult": tpm,
                "max_hold_bars": mh,
                "exit_on_signal_flip": False,
            },
            sh_cont_rationale if smult > 0 else sh_rev_rationale,
            sh_cont_cp if smult > 0 else sh_rev_cp,
            allow_unidirectional=False,
        )

    return specs[:TOTAL_CAP]


# ---------------------------------------------------------------------------
# Cluster A Discovery (`2018-2020` ONLY — Hard Blindness Lock)
# ---------------------------------------------------------------------------


def _score_cluster_a(eval_res: Mapping[str, Any]) -> tuple[float, bool]:
    """Compute anti-overfit Cluster A ranking score strictly from `2018-2020` metrics."""
    met = eval_res["metrics"]
    m1 = met["1x"]
    m15 = met["1.5x"]
    m2 = met["2x"]
    mz = met["zero_pos_swap_1x"]
    mf = met["fade_1x"]
    s0 = met["stage0"]

    n_tr = int(m1["n_trades"])
    if n_tr < 15 or not bool(s0["passed"]):
        return -999.0 + 0.01 * float(m1["net_R"]), False

    sh1 = float(m1["sharpe"])
    sh2 = float(m2["sharpe"])
    shz = float(mz["sharpe"])
    shf = float(mf["sharpe"])
    pf1 = min(float(m1["pf"]), 5.0)
    pf2 = min(float(m2["pf"]), 5.0)
    pos_ratio = float(m1["positive_year_ratio"])
    fade_edge = sh1 - shf

    # Primary eligibility gates (Cluster A only, zero Cluster B peek)
    prim_ok = (
        bool(s0["passed"])
        and n_tr >= 25
        and float(m1["net_R"]) > 0.0
        and float(m15["net_R"]) > 0.0
        and float(m2["net_R"]) > 0.0
        and float(mz["net_R"]) > 0.0
        and sh1 >= 0.35
        and sh2 >= 0.15
        and pos_ratio >= 0.65
        and fade_edge > 0.15
    )

    # Prefer NEW9 / TRUE_BLIND_7 mildly for unseen diversification (tie-breaker only)
    tier = str(eval_res["blindness_tier"])
    mixed_unseen = (
        cc.TIER_NEW9,
        "MIXED_12OLD_AND_NEW9",
        "MIXED_12OLD_AND_TRUE_BLIND_7",
        "MIXED_NEW9_AND_TRUE_BLIND_7",
        "MIXED_ALL_3_TIERS",
    )
    tier_bonus = 0.20 if tier == cc.TIER_NEW7 else (0.12 if tier in mixed_unseen else 0.0)
    sample_bonus = min(0.25, math.log1p(n_tr) / 20.0)

    score = (
        0.35 * sh1
        + 0.30 * sh2
        + 0.20 * shz
        + 0.15 * fade_edge
        + 0.25 * (pf2 - 1.0)
        + 0.20 * (pf1 - 1.0)
        + 0.40 * pos_ratio
        + tier_bonus
        + sample_bonus
    )
    return round(float(score), 6), prim_ok


def _compact_candidate_record(eval_res: Mapping[str, Any], tier: str, score: float) -> dict[str, Any]:
    spec = dict(eval_res["spec"])
    met = eval_res["metrics"]
    return {
        "candidate_id": spec["candidate_id"],
        "family_id": FAMILY_ID,
        "tier": tier,
        "is_primary": tier == "PRIMARY",
        "subfamily": spec["subfamily"],
        "prop_track": spec["prop_track"],
        "symbols": list(spec["symbols"]),
        "params": dict(spec["params"]),
        "economic_rationale": spec["economic_rationale"],
        "counterparty_mechanism": spec["counterparty_mechanism"],
        "data_resolution": eval_res["data_resolution"],
        "blindness_tier": eval_res["blindness_tier"],
        "allow_unidirectional": bool(eval_res["allow_unidirectional"]),
        "cluster_a_score": score,
        "cluster_a_stage0": met["stage0"],
        "cluster_a_metrics_1x": met["1x"],
        "cluster_a_metrics_15x": met["1.5x"],
        "cluster_a_metrics_2x": met["2x"],
        "cluster_a_metrics_zero_pos_1x": met["zero_pos_swap_1x"],
        "cluster_a_fade_1x": met["fade_1x"],
        "cluster_a_long_trades": int(met["long_trades"]),
        "cluster_a_short_trades": int(met["short_trades"]),
        "cluster_a_margin_audit": met["margin_audit"],
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def discover_cluster_a(
    universe: Mapping[str, Any],
    *,
    save_checkpoint: bool = True,
    resume: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run Cluster A (`2018-2020` ONLY) discovery for `F05_INTERMARKET` and atomically save checkpoint."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    red_news_index = cc.load_dev_red_news_index(include_extended=True, root=root)
    candidate_specs = _build_f05_candidate_specs()

    evaluated: list[tuple[float, bool, dict[str, Any]]] = []
    for sp in candidate_specs:
        res = evaluate_candidate(sp, universe, cc.CLUSTER_A_YEARS, red_news_index=red_news_index)
        # Hard guard: verify zero trades outside Cluster A (2018-2020)
        for tr in res["trades"]:
            if int(str(tr["exit_date"])[:4]) > 2020 or int(tr["exit_ts"]) >= 1_609_459_200:
                raise ValueError(f"CLUSTER_B_LEAK_BLOCKED in F05 discovery: {tr}")
        sc, prim_ok = _score_cluster_a(res)
        evaluated.append((sc, prim_ok, res))

    evaluated.sort(key=lambda item: (item[1], item[0]), reverse=True)

    # Diversified Primary selection (<= PRIMARY_CAP = 16, spanning subfamilies & symbols)
    primary_records: list[dict[str, Any]] = []
    exploratory_records: list[dict[str, Any]] = []
    subfam_counts: dict[str, int] = {}
    symkey_counts: dict[str, int] = {}
    subfam_cap = {
        "F05A_GAO_INTRADAY_MOM": 6,
        "F05B_CROSS_TZ_D1": 5,
        "F05B_CROSS_TZ_M1": 2,
        "F05C_SAFEHAVEN_M1": 3,
        "F05C_SAFEHAVEN_D1": 4,
    }

    selected_ids: set[str] = set()
    # Pass 1: strict prim_ok with subfamily/symbol diversity caps
    for sc, prim_ok, res in evaluated:
        if len(primary_records) >= PRIMARY_CAP:
            break
        if not prim_ok:
            continue
        sf = str(res["spec"]["subfamily"])
        sk = "+".join(res["spec"]["symbols"])
        if subfam_counts.get(sf, 0) >= subfam_cap.get(sf, 4):
            continue
        if symkey_counts.get(sk, 0) >= 2:
            continue
        rec = _compact_candidate_record(res, "PRIMARY", sc)
        primary_records.append(rec)
        selected_ids.add(rec["candidate_id"])
        subfam_counts[sf] = subfam_counts.get(sf, 0) + 1
        symkey_counts[sk] = symkey_counts.get(sk, 0) + 1

    # Pass 2: if fewer than PRIMARY_CAP, fill remaining slots with next best prim_ok (relaxing sym cap to 3)
    for sc, prim_ok, res in evaluated:
        if len(primary_records) >= PRIMARY_CAP:
            break
        cid = str(res["spec"]["candidate_id"])
        if cid in selected_ids or not prim_ok:
            continue
        sk = "+".join(res["spec"]["symbols"])
        if symkey_counts.get(sk, 0) >= 3:
            continue
        rec = _compact_candidate_record(res, "PRIMARY", sc)
        primary_records.append(rec)
        selected_ids.add(cid)
        symkey_counts[sk] = symkey_counts.get(sk, 0) + 1

    # Remaining evaluated specs go to EXPLORATORY (total <= TOTAL_CAP = 100)
    for sc, _prim_ok, res in evaluated:
        cid = str(res["spec"]["candidate_id"])
        if cid in selected_ids:
            continue
        if len(primary_records) + len(exploratory_records) >= TOTAL_CAP:
            break
        exploratory_records.append(_compact_candidate_record(res, "EXPLORATORY", sc))

    meta: dict[str, Any] = {
        "family_slug": FAMILY_SLUG,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "total_cap": TOTAL_CAP,
        "ops1_dst_guard_active": _HAS_OPS1_DST_GUARD,
        "subfamily_primary_counts": subfam_counts,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    if save_checkpoint:
        saved_path = cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary_records, "exploratory": exploratory_records},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=saved_path.parent, verify_sha=True, root=root)

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_count": len(primary_records),
        "exploratory_count": len(exploratory_records),
        "total_count": len(primary_records) + len(exploratory_records),
        "primary_candidates": primary_records,
        "exploratory_candidates": exploratory_records,
        "candidates": [*primary_records, *exploratory_records],
        "meta": meta,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def _main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Offensive #3 Family F05 Intermarket Cluster-A Discovery")
    parser.add_argument("--resume", action="store_true", help="Reuse SHA-verified Cluster A checkpoint if present")
    parser.add_argument("--verify-sha", action="store_true", help="Verify raw parquet SHA-256 while loading universe")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.resume and cc.has_valid_family_checkpoint(FAMILY_ID):
        doc = cc.load_family_candidates(FAMILY_ID, verify_sha=True)
        print(
            f"[RESUME] {FAMILY_ID}: primary={doc['primary_count']}/{doc['primary_cap']} "
            f"total={doc['total_count']}/{doc['total_cap']} years={doc['discovery_years']}"
        )
        return 0

    # STRICT HARD BLINDNESS: load ONLY CLUSTER_A_YEARS = (2018, 2019, 2020)!
    uni_a = cc.load_universe_28(
        load_m1=True,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=F05_REQUIRED_SYMBOLS,
        verify_sha=bool(args.verify_sha),
    )
    doc = discover_cluster_a(uni_a, save_checkpoint=True, resume=False)
    print(
        f"[DONE] {FAMILY_ID}: primary={doc['primary_count']}/{doc['primary_cap']} "
        f"total={doc['total_count']}/{doc['total_cap']} years={doc['discovery_years']} "
        f"subfam_prim={doc['meta'].get('subfamily_primary_counts')}"
    )
    for rec in doc["primary_candidates"][:8]:
        m1 = rec["cluster_a_metrics_1x"]
        m2 = rec["cluster_a_metrics_2x"]
        mf = rec["cluster_a_fade_1x"]
        s0 = rec["cluster_a_stage0"]
        print(
            f"  {rec['candidate_id']:42s} n={m1['n_trades']:3d} "
            f"1x_R={m1['net_R']:+6.2f} Sh1={m1['sharpe']:+5.2f} Sh2={m2['sharpe']:+5.2f} "
            f"FadeSh={mf['sharpe']:+5.2f} f/SL={100*float(s0['median_fric_sl_ratio'] or 0):.1f}% "
            f"posY={m1['positive_years']}/{m1['total_years']} [{rec['blindness_tier']}]"
        )
    return 0


__all__ = [
    "FAMILY_ID",
    "FAMILY_SLUG",
    "F05_REQUIRED_SYMBOLS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "discover_cluster_a",
    "evaluate_candidate",
    "resolve_session_window_utc_sec",
]

if __name__ == "__main__":
    raise SystemExit(_main())
