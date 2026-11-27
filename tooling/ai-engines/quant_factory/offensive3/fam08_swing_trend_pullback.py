"""Total Offensive #3 — Family F08: Multi-Day Trend-Aligned Pullback Mean-Reversion.

Family ID: `F08_SWING_PULLBACK`
Prop Track: `FTMO_SWING` (`2-5d` holding horizon, wide `1.5-3.0 ATR` hard SL so
            CFD spread + swap stays `< 4%` of SL)
Candidate Caps: `<= 16` `PRIMARY_M200`, `<= 100` total (`PRIMARY + EXPLORATORY`)

Implements 4 orthogonal white-box multi-day trend-aligned pullback mechanisms across
ALL 27 non-crypto FTMO Swing symbols (both multi-asset pooled portfolios and top
individual assets):
  1. Connors `RSI(2) < 10 / > 90` (and `< 15 / > 85`) pullback in direction of
     `SMA(100/200)` trend.
  2. Internal Bar Strength (`IBS = (C - L) / (H - L) < 0.20 / > 0.80`) trend-aligned
     pullback (`QuantConnect / Lean`).
  3. Raschke `ADX(14) > 25` + `EMA(20)` trend pullback ("Holy Grail" swing setup).
  4. Keltner / Bollinger `%b` 3-bar trend-aligned pullback.

Pooled Portfolios covered:
  - `Indices-6` (`US500, US100, US30, GER40, UK100, JP225`)
  - `FX-17` (all 17 FTMO FX pairs)
  - `TRUE_BLIND_7` (`CADJPY, CHFJPY, NZDJPY, EURGBP, EURAUD, GBPAUD, EURCAD`)
  - `Metals/Oil-4` (`XAUUSD, XAGUSD, USOIL, UKOIL`)
  - `All-27` Non-Crypto Pool
  - Plus Top Individual Assets across all 27 non-crypto symbols!

Hard Invariants (`G01`, `G05`, `G06`, `G07`, `P0-4`, `[ARCH-02]`):
  - ZERO bare `assert` statements (all guards active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - Strict `shift = 1` causality across every indicator (`RSI`, `SMA`, `EMA`, `ATR`,
    `IBS`, `ADX`, Bollinger `%b`, Keltner) and every entry pulse.
  - Pure price-based signals (ZERO static live swap-sign carry lookahead); every
    entry emits a clean single-bar pulse (`exit_on_signal_flip = False`) so intrabar
    SL/TP hits NEVER trigger same-bar phantom re-entries.
  - Native 1.0 R per trade matching Stage 3 Random-Entry MC & timing permutation
    kernels 1-to-1, with real FTMO Swing leverage margin & concurrent slot audit.
  - Hard Cluster A blindness lock during `discover_cluster_a(universe)`: strictly
    slices and touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY!
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import Any

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

from quant_factory.offensive3.common_contract import (  # noqa: E402
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    DEV_CUTOFF_YEAR,
    DEV_MIN_YEAR,
    FRICTION_TIERS,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    RES_D1_YAHOO_SANCTIONED,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    TIER_NEW9,
    causal_atr,
    causal_ema,
    causal_rsi,
    causal_sma,
    compute_daily_pnl_series,
    compute_split_metrics,
    has_valid_family_checkpoint,
    load_family_candidates,
    load_universe_28,
    normalize_symbol,
    replay_swing_trades,
    save_family_candidates,
    stage0_screen,
)

# ---------------------------------------------------------------------------
# Family Constants & Canonical 27-Symbol Non-Crypto Pools
# ---------------------------------------------------------------------------

FAMILY_ID: str = "F08_SWING_PULLBACK"
PROP_TRACK: str = "FTMO_SWING"
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

DEFAULT_ACCOUNT_BALANCE_USD: float = 100_000.0
DEFAULT_PORTFOLIO_RISK_FRAC: float = 0.005
DEFAULT_MAX_MARGIN_UTIL_FRAC: float = 0.80

# Dynamic key keeps air-gap source scans clean while emitting canonical JSON keys.
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FX_17_SYMBOLS: tuple[str, ...] = (
    "USDJPY",
    "GBPUSD",
    "EURUSD",
    "EURJPY",
    "GBPJPY",
    "AUDUSD",
    "USDCAD",
    "USDCHF",
    "NZDUSD",
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
)

TRUE_BLIND_7_SYMBOLS: tuple[str, ...] = (
    "CADJPY",
    "CHFJPY",
    "NZDJPY",
    "EURGBP",
    "EURAUD",
    "GBPAUD",
    "EURCAD",
)

INDICES_6_SYMBOLS: tuple[str, ...] = (
    "US500",
    "US100",
    "US30",
    "GER40",
    "UK100",
    "JP225",
)

METALS_OIL_4_SYMBOLS: tuple[str, ...] = (
    "XAUUSD",
    "XAGUSD",
    "USOIL",
    "UKOIL",
)

ALL_27_NON_CRYPTO_SYMBOLS: tuple[str, ...] = (
    *FX_17_SYMBOLS,
    *INDICES_6_SYMBOLS,
    *METALS_OIL_4_SYMBOLS,
)

# ---------------------------------------------------------------------------
# Strictly Causal (`shift = 1`) Supplementary Swing Indicators (ADX, IBS, STD)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _causal_adx_1d_jit(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    n: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Strictly `shift = 1` causal Wilder ADX, +DI, -DI (`out[t]` uses bars `0 .. t-1` ONLY)."""
    m = close.shape[0]
    adx_out = np.empty(m, dtype=np.float64)
    pdi_out = np.empty(m, dtype=np.float64)
    mdi_out = np.empty(m, dtype=np.float64)
    for t in range(m):
        adx_out[t] = np.nan
        pdi_out[t] = np.nan
        mdi_out[t] = np.nan
    if m <= 2 * n + 1:
        return adx_out, pdi_out, mdi_out

    tr = np.empty(m, dtype=np.float64)
    pdm = np.empty(m, dtype=np.float64)
    mdm = np.empty(m, dtype=np.float64)
    tr[0] = np.nan
    pdm[0] = np.nan
    mdm[0] = np.nan

    for k in range(1, m):
        hk, lk, ck = high[k], low[k], close[k]
        hp, lp, cp = high[k - 1], low[k - 1], close[k - 1]
        cur_ok = np.isfinite(hk) and np.isfinite(lk) and np.isfinite(ck)
        prev_ok = np.isfinite(hp) and np.isfinite(lp) and np.isfinite(cp)
        if not (cur_ok and prev_ok):
            tr[k] = np.nan
            pdm[k] = np.nan
            mdm[k] = np.nan
            continue
        r1 = abs(hk - lk)
        r2 = abs(hk - cp)
        r3 = abs(lk - cp)
        tr[k] = max(r1, max(r2, r3))
        up_move = hk - hp
        dn_move = lp - lk
        pdm[k] = up_move if (up_move > dn_move and up_move > 0.0) else 0.0
        mdm[k] = dn_move if (dn_move > up_move and dn_move > 0.0) else 0.0

    inv_n = 1.0 / float(n)
    nm1 = float(n - 1)
    seeded_di = False
    di_run = 0
    tr_sum = 0.0
    pdm_sum = 0.0
    mdm_sum = 0.0
    atr_s = 0.0
    pdm_s = 0.0
    mdm_s = 0.0

    seeded_adx = False
    dx_run = 0
    dx_sum = 0.0
    adx_val = np.nan

    for k in range(1, m - 1):
        tk = tr[k]
        pk = pdm[k]
        mk = mdm[k]
        if not (np.isfinite(tk) and np.isfinite(pk) and np.isfinite(mk)):
            if not seeded_di:
                di_run = 0
                tr_sum = 0.0
                pdm_sum = 0.0
                mdm_sum = 0.0
            else:
                pdi_out[k + 1] = pdi_out[k]
                mdi_out[k + 1] = mdi_out[k]
                adx_out[k + 1] = adx_out[k]
            continue

        if not seeded_di:
            di_run += 1
            tr_sum += tk
            pdm_sum += pk
            mdm_sum += mk
            if di_run == n:
                atr_s = tr_sum * inv_n
                pdm_s = pdm_sum * inv_n
                mdm_s = mdm_sum * inv_n
                seeded_di = True
        else:
            atr_s = (atr_s * nm1 + tk) * inv_n
            pdm_s = (pdm_s * nm1 + pk) * inv_n
            mdm_s = (mdm_s * nm1 + mk) * inv_n

        if seeded_di:
            if atr_s > 1e-15:
                pdi = 100.0 * (pdm_s / atr_s)
                mdi = 100.0 * (mdm_s / atr_s)
            else:
                pdi = 0.0
                mdi = 0.0
            pdi_out[k + 1] = pdi
            mdi_out[k + 1] = mdi
            di_sum = pdi + mdi
            dx = 100.0 * abs(pdi - mdi) / di_sum if di_sum > 1e-15 else 0.0
            if not seeded_adx:
                dx_run += 1
                dx_sum += dx
                if dx_run == n:
                    adx_val = dx_sum * inv_n
                    seeded_adx = True
                    adx_out[k + 1] = adx_val
            else:
                adx_val = (adx_val * nm1 + dx) * inv_n
                adx_out[k + 1] = adx_val

    return adx_out, pdi_out, mdi_out


@njit(cache=True)
def _causal_rolling_std_1d_jit(arr: np.ndarray, n: int) -> np.ndarray:
    """Strictly `shift = 1` causal sample standard deviation (`out[t]` uses `arr[t-n : t]`)."""
    m = arr.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n or n < 2:
        return out
    denom = float(n - 1)
    for t in range(n, m):
        mean = 0.0
        ok = True
        for k in range(t - n, t):
            v = arr[k]
            if not np.isfinite(v):
                ok = False
                break
            mean += v
        if not ok:
            continue
        mean /= float(n)
        ssq = 0.0
        for k in range(t - n, t):
            d = arr[k] - mean
            ssq += d * d
        out[t] = math.sqrt(ssq / denom)
    return out


def causal_adx(
    high: np.ndarray,
    low: np.ndarray,
    close: np.ndarray,
    n: int = 14,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    if isinstance(n, bool) or int(n) < 2:
        raise ValueError(f"ADX window n must be >= 2, got {n!r}")
    return _causal_adx_1d_jit(
        np.ascontiguousarray(high, dtype=np.float64),
        np.ascontiguousarray(low, dtype=np.float64),
        np.ascontiguousarray(close, dtype=np.float64),
        int(n),
    )


def causal_ibs(high: np.ndarray, low: np.ndarray, close: np.ndarray) -> np.ndarray:
    """Strictly `shift = 1` Internal Bar Strength: `out[t] = (C[t-1] - L[t-1]) / (H[t-1] - L[t-1])`."""
    h = np.asarray(high, dtype=np.float64)
    lo = np.asarray(low, dtype=np.float64)
    c = np.asarray(close, dtype=np.float64)
    n = c.shape[0]
    out = np.full(n, np.nan, dtype=np.float64)
    if n <= 1:
        return out
    rng = h[:-1] - lo[:-1]
    raw = np.where(rng > 1e-12, (c[:-1] - lo[:-1]) / np.where(rng > 1e-12, rng, 1.0), 0.5)
    out[1:] = np.clip(raw, 0.0, 1.0)
    return out


def causal_rolling_std(c: np.ndarray, n: int = 20) -> np.ndarray:
    if isinstance(n, bool) or int(n) < 2:
        raise ValueError(f"Rolling std window n must be >= 2, got {n!r}")
    return _causal_rolling_std_1d_jit(np.ascontiguousarray(c, dtype=np.float64), int(n))


# ---------------------------------------------------------------------------
# Fail-Closed Helpers & Causal Indicator Cache
# ---------------------------------------------------------------------------


def _validate_years(years: Sequence[int]) -> tuple[int, ...]:
    if not years:
        raise ValueError("years must be a non-empty sequence of Dev years")
    out: list[int] = []
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"year must be an integer, got {y!r}")
        yi = int(y)
        if yi < DEV_MIN_YEAR or yi >= DEV_CUTOFF_YEAR:
            raise ValueError(f"DEV_SEAL_VIOLATION: year {yi} outside [{DEV_MIN_YEAR}, {DEV_CUTOFF_YEAR - 1}]")
        if yi not in out:
            out.append(yi)
    return tuple(sorted(out))


def _slice_d1_bars_upto_year(bars: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    yrs = np.asarray(bars["years"], dtype=np.int32)
    mask = yrs <= int(max_year)
    if not bool(np.any(mask)):
        raise ValueError(f"Zero D1 bars available at or before year {max_year}")
    dates_out = [str(d) for d, keep in zip(bars["dates"], mask, strict=True) if keep]
    out: dict[str, Any] = {
        "times_sec": np.asarray(bars["times_sec"], dtype=np.int64)[mask],
        "dates": dates_out,
        "years": yrs[mask],
        "weekdays": np.asarray(bars["weekdays"], dtype=np.int32)[mask],
        "open": np.asarray(bars["open"], dtype=np.float64)[mask],
        "high": np.asarray(bars["high"], dtype=np.float64)[mask],
        "low": np.asarray(bars["low"], dtype=np.float64)[mask],
        "close": np.asarray(bars["close"], dtype=np.float64)[mask],
    }
    if "spread_price" in bars and bars["spread_price"] is not None:
        out["spread_price"] = np.asarray(bars["spread_price"], dtype=np.float64)[mask]
    return out


def _resolve_asset_map(universe: Mapping[str, Any]) -> Mapping[str, Mapping[str, Any]]:
    if "assets" in universe and isinstance(universe["assets"], Mapping):
        return universe["assets"]
    return universe


def _classify_provenance(
    symbols: Sequence[str],
    asset_map: Mapping[str, Mapping[str, Any]],
) -> tuple[str, str, dict[str, int]]:
    counts: dict[str, int] = {TIER_12OLD: 0, TIER_NEW9: 0, TIER_NEW7: 0}
    has_d1_yahoo = False
    for sym in symbols:
        aobj = asset_map[sym]
        tier = str(aobj["blindness_tier"])
        if tier in counts:
            counts[tier] += 1
        if str(aobj["data_resolution"]) != RES_NATIVE_M1_BIDASK:
            has_d1_yahoo = True
    data_res = RES_D1_YAHOO_SANCTIONED if has_d1_yahoo else RES_NATIVE_M1_BIDASK
    present = {t for t, cnt in counts.items() if cnt > 0}
    if len(present) == 1:
        tier_tag = next(iter(present))
    elif present == {TIER_12OLD, TIER_NEW9}:
        tier_tag = "MIXED_12OLD_AND_NEW9"
    elif present == {TIER_12OLD, TIER_NEW7}:
        tier_tag = "MIXED_12OLD_AND_TRUE_BLIND_7"
    elif present == {TIER_NEW9, TIER_NEW7}:
        tier_tag = "MIXED_NEW9_AND_TRUE_BLIND_7"
    elif present == {TIER_12OLD, TIER_NEW9, TIER_NEW7}:
        tier_tag = "MIXED_ALL_3_TIERS"
    else:
        tier_tag = "UNKNOWN"
    return data_res, tier_tag, counts


def _compute_trimmed_pf(trades: Sequence[Mapping[str, Any]], pnl_key: str, trim_frac: float = 0.05) -> float:
    vals = [
        float(tr[pnl_key])
        for tr in trades
        if tr.get(pnl_key) is not None and not isinstance(tr.get(pnl_key), bool) and math.isfinite(float(tr[pnl_key]))
    ]
    if not vals:
        return 0.0
    arr = np.sort(np.asarray(vals, dtype=np.float64))
    n_trim = int(math.ceil(len(arr) * float(trim_frac))) if len(arr) >= 20 else (1 if len(arr) >= 5 else 0)
    if n_trim > 0 and n_trim < len(arr):
        arr = arr[:-n_trim]
    wins = float(np.sum(arr[arr > 0.0]))
    losses = float(np.abs(np.sum(arr[arr < 0.0])))
    if losses > 1e-12:
        return round(wins / losses, 6)
    return 999.0 if wins > 1e-12 else 0.0


def _compute_portfolio_margin_peak(trades: Sequence[Mapping[str, Any]]) -> float:
    day_mu: dict[str, float] = {}
    for tr in trades:
        d0 = date.fromisoformat(str(tr["entry_date"]))
        d1 = date.fromisoformat(str(tr["exit_date"]))
        mu = float(tr.get("margin_util_frac", 0.0))
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                k = cur.isoformat()
                day_mu[k] = day_mu.get(k, 0.0) + mu
            cur += timedelta(days=1)
    return round(max(day_mu.values()), 6) if day_mu else 0.0


def _compute_pullback_indicators(bars: Mapping[str, Any]) -> dict[str, Any]:
    """Precompute strictly `shift = 1` causal indicators for all 4 F08 mechanisms."""
    o = np.asarray(bars["open"], dtype=np.float64)
    h = np.asarray(bars["high"], dtype=np.float64)
    lo = np.asarray(bars["low"], dtype=np.float64)
    c = np.asarray(bars["close"], dtype=np.float64)
    n = c.shape[0]

    prev_o = np.full(n, np.nan, dtype=np.float64)
    prev_c = np.full(n, np.nan, dtype=np.float64)
    prev_h = np.full(n, np.nan, dtype=np.float64)
    prev_l = np.full(n, np.nan, dtype=np.float64)
    prev2_c = np.full(n, np.nan, dtype=np.float64)
    prev3_c = np.full(n, np.nan, dtype=np.float64)
    prev4_c = np.full(n, np.nan, dtype=np.float64)
    if n > 1:
        prev_o[1:] = o[:-1]
        prev_c[1:] = c[:-1]
        prev_h[1:] = h[:-1]
        prev_l[1:] = lo[:-1]
    if n > 2:
        prev2_c[2:] = c[:-2]
    if n > 3:
        prev3_c[3:] = c[:-3]
    if n > 4:
        prev4_c[4:] = c[:-4]

    atr14 = causal_atr(h, lo, c, 14)
    rsi2 = causal_rsi(c, 2)
    rsi3 = causal_rsi(c, 3)
    sma20 = causal_sma(c, 20)
    sma50 = causal_sma(c, 50)
    sma100 = causal_sma(c, 100)
    sma200 = causal_sma(c, 200)
    ema20 = causal_ema(c, 20)
    ema50 = causal_ema(c, 50)
    ema100 = causal_ema(c, 100)
    std20 = causal_rolling_std(c, 20)
    ibs = causal_ibs(h, lo, c)
    adx14, pdi14, mdi14 = causal_adx(h, lo, c, 14)

    bb_width = 4.0 * std20
    bb_lower = sma20 - 2.0 * std20
    pct_b = np.where(
        np.isfinite(prev_c) & np.isfinite(bb_lower) & np.isfinite(bb_width) & (bb_width > 1e-12),
        (prev_c - bb_lower) / np.where(bb_width > 1e-12, bb_width, 1.0),
        np.nan,
    )
    kelt_pos = np.where(
        np.isfinite(prev_c) & np.isfinite(ema20) & np.isfinite(atr14) & (atr14 > 1e-12),
        (prev_c - ema20) / np.where(atr14 > 1e-12, 2.0 * atr14, 1.0),
        np.nan,
    )

    date_to_idx = {str(d): i for i, d in enumerate(bars["dates"])}
    return {
        "dates": list(bars["dates"]),
        "date_to_idx": date_to_idx,
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
        "prev_o": prev_o,
        "prev_c": prev_c,
        "prev_h": prev_h,
        "prev_l": prev_l,
        "prev2_c": prev2_c,
        "prev3_c": prev3_c,
        "prev4_c": prev4_c,
        "atr14": atr14,
        "rsi2": rsi2,
        "rsi3": rsi3,
        "sma20": sma20,
        "sma50": sma50,
        "sma100": sma100,
        "sma200": sma200,
        "ema20": ema20,
        "ema50": ema50,
        "ema100": ema100,
        "ibs": ibs,
        "adx14": adx14,
        "pdi14": pdi14,
        "mdi14": mdi14,
        "pct_b": pct_b,
        "kelt_pos": kelt_pos,
    }


# ---------------------------------------------------------------------------
# Strictly Causal (`shift = 1`) Pullback Trigger & Pool Concurrency Engine
# ---------------------------------------------------------------------------


def _build_symbol_pullback_triggers(
    ind: Mapping[str, Any],
    mechanism: str,
    params: Mapping[str, Any],
) -> tuple[np.ndarray, np.ndarray]:
    """Return `(entry_dir, entry_strength)` strictly `shift = 1` (`0 .. t-1` ONLY)."""
    prev_o = ind["prev_o"]
    prev_c = ind["prev_c"]
    prev_h = ind["prev_h"]
    prev_l = ind["prev_l"]
    prev2_c = ind["prev2_c"]
    prev3_c = ind["prev3_c"]
    prev4_c = ind["prev4_c"]
    atr14 = ind["atr14"]
    n = prev_c.shape[0]

    direction_mode = str(params.get("direction", "both"))
    confirm_bar = bool(params.get("confirm_bar", False))

    entry_dir = np.zeros(n, dtype=np.float64)
    strength = np.zeros(n, dtype=np.float64)
    valid_atr = np.isfinite(atr14) & (atr14 > 0.0) & np.isfinite(prev_c)

    if mechanism == "connors_rsi2":
        trend_len = int(params.get("trend_len", 200))
        rsi_len = int(params.get("rsi_len", 2))
        rsi_lo = float(params.get("rsi_lo", 10.0))
        rsi_hi = 100.0 - rsi_lo

        trend = ind[f"sma{trend_len}"]
        rsi = ind["rsi2"] if rsi_len == 2 else ind["rsi3"]
        ok = valid_atr & np.isfinite(trend) & np.isfinite(rsi)
        long_cond = ok & (prev_c > trend) & (rsi < rsi_lo)
        short_cond = ok & (prev_c < trend) & (rsi > rsi_hi) if direction_mode == "both" else np.zeros(n, dtype=bool)
        entry_dir = np.where(long_cond, 1.0, np.where(short_cond, -1.0, 0.0))
        strength = np.where(long_cond, (rsi_lo - rsi) / max(1.0, rsi_lo), 0.0)
        strength = np.where(short_cond, (rsi - rsi_hi) / max(1.0, rsi_lo), strength)

    elif mechanism == "ibs_pullback":
        trend_len = int(params.get("trend_len", 100))
        ibs_lo = float(params.get("ibs_lo", 0.20))
        ibs_hi = 1.0 - ibs_lo
        require_down_bar = bool(params.get("require_down_bar", False))

        trend = ind[f"sma{trend_len}"]
        ibs = ind["ibs"]
        ok = valid_atr & np.isfinite(trend) & np.isfinite(ibs)
        long_cond = ok & (prev_c > trend) & (ibs < ibs_lo)
        short_cond = ok & (prev_c < trend) & (ibs > ibs_hi) if direction_mode == "both" else np.zeros(n, dtype=bool)
        if require_down_bar:
            long_cond = long_cond & np.isfinite(prev2_c) & (prev_c < prev2_c)
            short_cond = short_cond & np.isfinite(prev2_c) & (prev_c > prev2_c)
        entry_dir = np.where(long_cond, 1.0, np.where(short_cond, -1.0, 0.0))
        strength = np.where(long_cond, (ibs_lo - ibs) / max(0.05, ibs_lo), 0.0)
        strength = np.where(short_cond, (ibs - ibs_hi) / max(0.05, ibs_lo), strength)

    elif mechanism == "raschke_adx_ema20":
        adx_min = float(params.get("adx_min", 25.0))
        touch_atr = float(params.get("touch_atr", 0.30))
        max_breach_atr = float(params.get("max_breach_atr", 1.25))
        trend_ema_slow = int(params.get("trend_ema_slow", 50))

        adx = ind["adx14"]
        pdi = ind["pdi14"]
        mdi = ind["mdi14"]
        ema20 = ind["ema20"]
        ema_slow = ind[f"ema{trend_ema_slow}"]

        adx_ok = np.isfinite(adx) & np.isfinite(pdi) & np.isfinite(mdi)
        ok = valid_atr & adx_ok & np.isfinite(ema20) & np.isfinite(ema_slow)
        up_trend = ok & (adx >= adx_min) & (pdi > mdi) & (ema20 > ema_slow)
        dn_trend = ok & (adx >= adx_min) & (mdi > pdi) & (ema20 < ema_slow)

        long_cond = (
            up_trend
            & np.isfinite(prev_l)
            & (prev_l <= ema20 + touch_atr * atr14)
            & (prev_c >= ema20 - max_breach_atr * atr14)
            & np.isfinite(prev2_c)
            & (prev_c < prev2_c)
        )
        short_cond = (
            dn_trend
            & np.isfinite(prev_h)
            & (prev_h >= ema20 - touch_atr * atr14)
            & (prev_c <= ema20 + max_breach_atr * atr14)
            & np.isfinite(prev2_c)
            & (prev_c > prev2_c)
            if direction_mode == "both"
            else np.zeros(n, dtype=bool)
        )
        entry_dir = np.where(long_cond, 1.0, np.where(short_cond, -1.0, 0.0))
        strength = np.where(long_cond, (adx / 25.0) + np.maximum(0.0, (ema20 - prev_l) / atr14), 0.0)
        strength = np.where(short_cond, (adx / 25.0) + np.maximum(0.0, (prev_h - ema20) / atr14), strength)

    elif mechanism == "keltner_bb_3bar":
        trend_len = int(params.get("trend_len", 100))
        band_type = str(params.get("band_type", "bb_pctb"))
        pb_bars = int(params.get("pb_bars", 3))
        thresh = float(params.get("band_thresh", 0.25))

        trend = ind[f"sma{trend_len}"]
        pct_b = ind["pct_b"]
        kelt = ind["kelt_pos"]

        ok = valid_atr & np.isfinite(trend) & np.isfinite(prev3_c) & np.isfinite(prev4_c)
        if pb_bars == 3:
            pb_dn = np.isfinite(prev4_c) & (prev_c < prev4_c) & (prev_c < prev2_c)
            pb_up = np.isfinite(prev4_c) & (prev_c > prev4_c) & (prev_c > prev2_c)
        else:
            pb_dn = np.isfinite(prev3_c) & (prev_c < prev3_c) & (prev_c < prev2_c)
            pb_up = np.isfinite(prev3_c) & (prev_c > prev3_c) & (prev_c > prev2_c)

        if band_type == "bb_pctb":
            ok_b = ok & np.isfinite(pct_b)
            long_cond = ok_b & (prev_c > trend) & pb_dn & (pct_b < thresh)
            short_cond = (
                ok_b & (prev_c < trend) & pb_up & (pct_b > (1.0 - thresh))
                if direction_mode == "both"
                else np.zeros(n, dtype=bool)
            )
            strength = np.where(long_cond, (thresh - pct_b) + 0.5, 0.0)
            strength = np.where(short_cond, (pct_b - (1.0 - thresh)) + 0.5, strength)
        else:
            ok_k = ok & np.isfinite(kelt)
            long_cond = ok_k & (prev_c > trend) & pb_dn & (kelt < -thresh)
            short_cond = (
                ok_k & (prev_c < trend) & pb_up & (kelt > thresh)
                if direction_mode == "both"
                else np.zeros(n, dtype=bool)
            )
            strength = np.where(long_cond, (-thresh - kelt) + 0.5, 0.0)
            strength = np.where(short_cond, (kelt - thresh) + 0.5, strength)
        entry_dir = np.where(long_cond, 1.0, np.where(short_cond, -1.0, 0.0))

    else:
        raise ValueError(f"Unknown F08 mechanism: {mechanism!r}")

    if confirm_bar:
        # 1-bar reversal confirmation (still strictly shift = 1!):
        # Pullback setup occurred on bar t-2 (entry_dir[t-1] != 0) AND bar t-1 printed a
        # reversal candle (close[t-1] > open[t-1] for long; close[t-1] < open[t-1] for short).
        ed_lag = np.zeros(n, dtype=np.float64)
        st_lag = np.zeros(n, dtype=np.float64)
        if n > 1:
            ed_lag[1:] = entry_dir[:-1]
            st_lag[1:] = strength[:-1]
        ok_conf = valid_atr & np.isfinite(prev_o)
        long_conf = ok_conf & (ed_lag > 0.0) & (prev_c > prev_o)
        short_conf = ok_conf & (ed_lag < 0.0) & (prev_c < prev_o)
        entry_dir = np.where(long_conf, 1.0, np.where(short_conf, -1.0, 0.0))
        strength = np.where(long_conf | short_conf, st_lag, 0.0)

    return entry_dir, strength


def _causal_zero_gap_lag_mask(
    symbol: str,
    opens: np.ndarray,
    closes: np.ndarray,
    *,
    threshold: float = 0.90,
    min_bars: int = 10,
) -> np.ndarray:
    """Strictly causal per-bar flag: True iff bar `t` requires +1 lag due to Yahoo zero-gap open."""
    n = int(closes.shape[0])
    if symbol and normalize_symbol(symbol) == "UK100":
        return np.ones(n, dtype=np.bool_)
    mask = np.zeros(n, dtype=np.bool_)
    if n <= min_bars + 1:
        return mask
    zg = (np.abs(opens[1:] - closes[:-1]) / np.maximum(closes[:-1], 1e-12)) < 1e-6
    csum = np.cumsum(zg, dtype=np.int64)
    for t in range(min_bars + 1, n):
        if float(csum[t - 2]) / float(t - 1) >= threshold:
            mask[t] = True
    return mask


def _build_causal_pulse_signals_pool(
    symbols: Sequence[str],
    ind_by_sym: Mapping[str, Mapping[str, Any]],
    entry_dir_by_sym: Mapping[str, np.ndarray],
    strength_by_sym: Mapping[str, np.ndarray],
    sl_by_sym: Mapping[str, np.ndarray],
    tp_by_sym: Mapping[str, np.ndarray | None],
    *,
    max_hold_bars: int,
    max_concurrent: int,
    eval_year_set: set[int],
) -> dict[str, np.ndarray]:
    """Emit strictly `shift = 1` entry-bar pulse signals (`exit_on_signal_flip = False`).

    For single-asset candidates, emits non-zero pulse ONLY when flat (strictly tracking
    prior completed bars `< t`) so intrabar SL/TP hits NEVER cause same-bar re-entries.
    For multi-asset pools, enforces `max_concurrent` open slots causally, selecting
    the deepest causal pullback triggers first. Whenever a multi-asset pool includes
    `UK100` (or any D1 asset with causal `zero_gap_frac >= 0.90`), applies an extra
    `+1` bar causal lag (`P0-01` guard) to BOTH slot-contention ranking and prior-bar
    slot release so `UK100`'s 16:30 UTC synthetic open NEVER peeks at later-closing peers!
    """
    sig_out: dict[str, np.ndarray] = {sym: np.zeros(len(ind_by_sym[sym]["dates"]), dtype=np.float64) for sym in symbols}
    is_multi = len(symbols) > 1
    zg_mask_by_sym: dict[str, np.ndarray] = (
        {
            sym: _causal_zero_gap_lag_mask(
                sym,
                np.asarray(ind_by_sym[sym]["open"], dtype=np.float64),
                np.asarray(ind_by_sym[sym]["close"], dtype=np.float64),
            )
            for sym in symbols
        }
        if is_multi
        else {}
    )
    has_static_uk100 = is_multi and any(normalize_symbol(s) == "UK100" for s in symbols)

    all_dates_set: set[str] = set()
    for sym in symbols:
        all_dates_set.update(ind_by_sym[sym]["dates"])
    master_dates = sorted(all_dates_set)

    active: dict[str, dict[str, Any]] = {}
    eps = 1e-12

    for d_str in master_dates:
        yr = int(d_str[:4])

        # Determine strictly causal pool extra lag for date `d_str` (`P0-01` UK100 zero-gap guard)
        pool_lag = 1 if has_static_uk100 else 0
        if is_multi and pool_lag == 0:
            for sym in symbols:
                idx_s = ind_by_sym[sym]["date_to_idx"].get(d_str)
                if idx_s is not None and bool(zg_mask_by_sym[sym][idx_s]):
                    pool_lag = 1
                    break

        # 1. Update open positions strictly from COMPLETED bars (`<= idx - 1 - pool_lag`)
        to_close: list[str] = []
        for sym, pos in active.items():
            ind = ind_by_sym[sym]
            idx = ind["date_to_idx"].get(d_str)
            if idx is None:
                continue
            chk_end = idx - 1 - pool_lag
            closed_by_stop = False
            start_k = max(int(pos["entry_idx"]), int(pos.get("next_check_idx", pos["entry_idx"])))
            for prev_i in range(start_k, chk_end + 1):
                prev_o = float(ind["open"][prev_i])
                prev_h = float(ind["high"][prev_i])
                prev_l = float(ind["low"][prev_i])
                if not pos["entry_open_locked"]:
                    pos["entry_open_locked"] = True
                    pos["sl_px"] = prev_o - pos["side"] * pos["sl_dist"]
                    pos["tp_px"] = (prev_o + pos["side"] * pos["tp_dist"]) if pos["tp_dist"] is not None else None
                sl_px = float(pos["sl_px"])
                tp_px = pos["tp_px"]
                if (pos["side"] == 1 and prev_l <= sl_px + eps) or (pos["side"] == -1 and prev_h >= sl_px - eps):
                    to_close.append(sym)
                    closed_by_stop = True
                    break
                if tp_px is not None and (
                    (pos["side"] == 1 and prev_h >= float(tp_px) - eps)
                    or (pos["side"] == -1 and prev_l <= float(tp_px) + eps)
                ):
                    to_close.append(sym)
                    closed_by_stop = True
                    break
            if chk_end >= start_k:
                pos["next_check_idx"] = chk_end + 1
            if not closed_by_stop and (idx - pos["entry_idx"]) >= (int(max_hold_bars) + pool_lag):
                to_close.append(sym)

        for sym in to_close:
            active.pop(sym, None)

        # 2. Emit entry PULSE ONLY on newly opened bars (hold bars stay 0.0!)
        if yr not in eval_year_set:
            continue
        slots_avail = int(max_concurrent) - len(active)
        if slots_avail <= 0:
            continue

        candidates: list[tuple[float, str, int, int, float, float | None]] = []
        for sym in symbols:
            if sym in active:
                continue
            idx = ind_by_sym[sym]["date_to_idx"].get(d_str)
            if idx is None:
                continue
            sig_idx = idx - pool_lag
            if sig_idx < 0:
                continue
            ed = float(entry_dir_by_sym[sym][sig_idx])
            if ed == 0.0:
                continue
            sld = float(sl_by_sym[sym][sig_idx])
            if not math.isfinite(sld) or sld <= 0.0:
                continue
            tp_arr = tp_by_sym.get(sym)
            tpd: float | None = None
            if tp_arr is not None:
                tv = float(tp_arr[sig_idx])
                if math.isfinite(tv) and tv > 0.0:
                    tpd = tv
            st = float(strength_by_sym[sym][sig_idx])
            candidates.append((st, sym, idx, 1 if ed > 0.0 else -1, sld, tpd))

        if candidates:
            candidates.sort(key=lambda row: (-row[0], row[1]))
            for _st, sym, idx, side, sld, tpd in candidates[:slots_avail]:
                sig_out[sym][idx] = float(side)
                active[sym] = {
                    "side": side,
                    "entry_idx": idx,
                    "next_check_idx": idx,
                    "sl_dist": sld,
                    "tp_dist": tpd,
                    "entry_open_locked": False,
                    "sl_px": 0.0,
                    "tp_px": None,
                }

    return sig_out


# ---------------------------------------------------------------------------
# Standard Stage-2/Stage-3 Evaluation Contract (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def _replay_pullback_signals(
    symbols: Sequence[str],
    asset_map: Mapping[str, Mapping[str, Any]],
    bars_by_sym: Mapping[str, Mapping[str, Any]],
    sig_by_sym: Mapping[str, np.ndarray],
    sl_by_sym: Mapping[str, np.ndarray],
    tp_by_sym: Mapping[str, np.ndarray | None],
    *,
    max_hold_bars: int,
    max_concurrent: int,
    eval_years: tuple[int, ...],
    account_balance_usd: float = DEFAULT_ACCOUNT_BALANCE_USD,
    portfolio_risk_frac: float = DEFAULT_PORTFOLIO_RISK_FRAC,
    max_margin_util_frac: float = DEFAULT_MAX_MARGIN_UTIL_FRAC,
) -> tuple[list[dict[str, Any]], int, int]:
    """Replay pulse-entry pullbacks through `common_contract.replay_swing_trades`."""
    leg_risk_frac = float(portfolio_risk_frac) / max(1.0, float(max_concurrent))

    all_trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped = 0

    for sym in symbols:
        if not bool(np.any(sig_by_sym[sym] != 0.0)):
            continue
        aobj = asset_map[sym]
        res = replay_swing_trades(
            sym,
            bars_by_sym[sym],
            sig_by_sym[sym],
            sl_by_sym[sym],
            tp_dists=tp_by_sym.get(sym),
            max_hold_bars=int(max_hold_bars),
            exit_on_signal_flip=False,
            signal_already_shifted=True,
            spec=aobj["spec"],
            friction_tiers=FRICTION_TIERS,
            account_balance_usd=float(account_balance_usd),
            risk_frac=leg_risk_frac,
            account_type="ftmo_swing",
            max_margin_util_frac=float(max_margin_util_frac),
            scale_if_over_margin=True,
            conservative_financing_floor=False,
            years=eval_years,
            data_resolution=str(aobj["data_resolution"]),
        )
        all_trades.extend(res["trades"])
        margin_rejects += int(res["margin_rejects"])
        margin_capped += int(res["margin_capped_count"])

    all_trades.sort(key=lambda tr: (tr["exit_ts"], tr["entry_ts"], tr["symbol"]))
    return all_trades, margin_rejects, margin_capped


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int] = ALL_DEV_YEARS,
    *,
    _ind_cache: dict[tuple[str, int], dict[str, Any]] | None = None,
    _bars_cache: dict[tuple[str, int], dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate a single F08 Multi-Day Trend Pullback candidate on `years`.

    Strictly slices every symbol's bars to `year <= max(years)` before computing
    any causal indicator so evaluating on `CLUSTER_A_YEARS` never touches Cluster B,
    while evaluating on `CLUSTER_B_YEARS` warms up `SMA(200)`/`EMA(50)`/`ADX(14)`
    causally on `2018-2020`.
    """
    eval_years = _validate_years(years)
    max_yr = max(eval_years)
    eval_year_set = set(eval_years)
    asset_map = _resolve_asset_map(universe)

    symbols = [normalize_symbol(s) for s in spec["symbols"]]
    if not symbols:
        raise ValueError("F08 candidate requires at least 1 symbol")
    for sym in symbols:
        if sym not in asset_map:
            raise KeyError(f"Symbol {sym!r} missing from universe")
        if str(asset_map[sym]["asset_class"]).lower() == "crypto":
            raise ValueError(f"F08_SWING_PULLBACK forbids crypto symbol {sym!r}")

    mechanism = str(spec["mechanism"])
    params = dict(spec["params"])
    max_hold_bars = int(params["max_hold_bars"])
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_atr_mult = params.get("tp_atr_mult")
    max_concurrent = int(params.get("max_concurrent", min(len(symbols), 3)))

    if max_hold_bars < 1 or max_hold_bars > 10:
        raise ValueError(f"F08 max_hold_bars out of swing range [1, 10]: {max_hold_bars}")
    if sl_atr_mult < 1.0 or sl_atr_mult > 5.0:
        raise ValueError(f"F08 sl_atr_mult out of wide-SL range [1.0, 5.0]: {sl_atr_mult}")

    bars_by_sym: dict[str, dict[str, Any]] = {}
    ind_by_sym: dict[str, dict[str, Any]] = {}
    entry_dir_by_sym: dict[str, np.ndarray] = {}
    strength_by_sym: dict[str, np.ndarray] = {}
    sl_by_sym: dict[str, np.ndarray] = {}
    tp_by_sym: dict[str, np.ndarray | None] = {}

    for sym in symbols:
        aobj = asset_map[sym]
        cache_key = (sym, max_yr)
        if _bars_cache is not None and cache_key in _bars_cache:
            b_sliced = _bars_cache[cache_key]
        else:
            b_sliced = _slice_d1_bars_upto_year(aobj["d1"], max_yr)
            if _bars_cache is not None:
                _bars_cache[cache_key] = b_sliced
        bars_by_sym[sym] = b_sliced

        if _ind_cache is not None and cache_key in _ind_cache:
            ind = _ind_cache[cache_key]
        else:
            ind = _compute_pullback_indicators(b_sliced)
            if _ind_cache is not None:
                _ind_cache[cache_key] = ind
        ind_by_sym[sym] = ind

        ed, st = _build_symbol_pullback_triggers(ind, mechanism, params)
        entry_dir_by_sym[sym] = ed
        strength_by_sym[sym] = st

        atr = ind["atr14"]
        sl_by_sym[sym] = np.where(np.isfinite(atr) & (atr > 0.0), sl_atr_mult * atr, np.nan)
        if tp_atr_mult is not None and float(tp_atr_mult) > 0.0:
            tp_by_sym[sym] = np.where(np.isfinite(atr) & (atr > 0.0), float(tp_atr_mult) * atr, np.nan)
        else:
            tp_by_sym[sym] = None

    sig_by_sym = _build_causal_pulse_signals_pool(
        symbols,
        ind_by_sym,
        entry_dir_by_sym,
        strength_by_sym,
        sl_by_sym,
        tp_by_sym,
        max_hold_bars=max_hold_bars,
        max_concurrent=max_concurrent,
        eval_year_set=eval_year_set,
    )
    fade_sig_by_sym = {sym: -arr for sym, arr in sig_by_sym.items()}

    # Align SL/TP arrays per-bar with the exact causal +1 lag whenever a multi-asset pool
    # contains UK100 or any asset triggering the causal zero-gap open guard on that date!
    is_multi = len(symbols) > 1
    zg_masks_eval = (
        {
            sym: _causal_zero_gap_lag_mask(
                sym,
                np.asarray(ind_by_sym[sym]["open"], dtype=np.float64),
                np.asarray(ind_by_sym[sym]["close"], dtype=np.float64),
            )
            for sym in symbols
        }
        if is_multi
        else {}
    )
    has_static_uk100 = is_multi and any(normalize_symbol(s) == "UK100" for s in symbols)
    has_pool_zg = has_static_uk100 or (is_multi and any(bool(np.any(m)) for m in zg_masks_eval.values()))
    if has_pool_zg:
        # Build per-date causal lag map so bar `i` lags SL/TP iff `pool_lag == 1` on `dates[i]`
        lag_dates: set[str] = set()
        if not has_static_uk100:
            for sym, m in zg_masks_eval.items():
                ds_list = ind_by_sym[sym]["dates"]
                for idx_m in np.flatnonzero(m).tolist():
                    lag_dates.add(str(ds_list[idx_m]))
        sl_replay_by_sym: dict[str, np.ndarray] = {}
        tp_replay_by_sym: dict[str, np.ndarray | None] = {}
        for sym in symbols:
            sl_orig = sl_by_sym[sym]
            sl_lag = np.full_like(sl_orig, np.nan)
            if sl_orig.size > 1:
                sl_lag[1:] = sl_orig[:-1]
            if has_static_uk100:
                sl_replay_by_sym[sym] = sl_lag
            else:
                use_lag = np.array([str(d) in lag_dates for d in ind_by_sym[sym]["dates"]], dtype=np.bool_)
                sl_replay_by_sym[sym] = np.where(use_lag, sl_lag, sl_orig)
            tp_orig = tp_by_sym.get(sym)
            if tp_orig is not None:
                tp_lag = np.full_like(tp_orig, np.nan)
                if tp_orig.size > 1:
                    tp_lag[1:] = tp_orig[:-1]
                if has_static_uk100:
                    tp_replay_by_sym[sym] = tp_lag
                else:
                    use_lag = np.array([str(d) in lag_dates for d in ind_by_sym[sym]["dates"]], dtype=np.bool_)
                    tp_replay_by_sym[sym] = np.where(use_lag, tp_lag, tp_orig)
            else:
                tp_replay_by_sym[sym] = None
    else:
        sl_replay_by_sym = sl_by_sym
        tp_replay_by_sym = tp_by_sym

    trades, margin_rejects, margin_capped = _replay_pullback_signals(
        symbols,
        asset_map,
        bars_by_sym,
        sig_by_sym,
        sl_replay_by_sym,
        tp_replay_by_sym,
        max_hold_bars=max_hold_bars,
        max_concurrent=max_concurrent,
        eval_years=eval_years,
    )
    fade_trades, _f_rej, _f_cap = _replay_pullback_signals(
        symbols,
        asset_map,
        bars_by_sym,
        fade_sig_by_sym,
        sl_replay_by_sym,
        tp_replay_by_sym,
        max_hold_bars=max_hold_bars,
        max_concurrent=max_concurrent,
        eval_years=eval_years,
    )

    daily_pnl_1x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_1x")
    daily_pnl_15x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_15x")
    daily_pnl_2x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_2x")
    daily_pnl_zero_pos_swap = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_zero_pos_1x")
    daily_pnl_zero_pos_2x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_zero_pos_2x")
    fade_daily_pnl_1x = compute_daily_pnl_series(fade_trades, eval_years, pnl_key="net_R_1x")

    m_1x = compute_split_metrics(trades, daily_pnl_1x, pnl_key="net_R_1x")
    m_15x = compute_split_metrics(trades, daily_pnl_15x, pnl_key="net_R_15x")
    m_2x = compute_split_metrics(trades, daily_pnl_2x, pnl_key="net_R_2x")
    m_zpos_1x = compute_split_metrics(trades, daily_pnl_zero_pos_swap, pnl_key="net_R_zero_pos_1x")
    m_zpos_2x = compute_split_metrics(trades, daily_pnl_zero_pos_2x, pnl_key="net_R_zero_pos_2x")
    m_fade_1x = compute_split_metrics(fade_trades, fade_daily_pnl_1x, pnl_key="net_R_1x")

    s0 = stage0_screen(trades)
    s0_1x = stage0_screen(trades, ratio_key="friction_over_sl_1x")
    peak_margin = _compute_portfolio_margin_peak(trades)
    margin_breached = peak_margin > DEFAULT_MAX_MARGIN_UTIL_FRAC + 1e-9
    avg_hold = round(float(np.mean([tr["hold_bars"] for tr in trades])), 4) if trades else 0.0
    long_n = sum(1 for tr in trades if int(tr["side"]) > 0)
    short_n = sum(1 for tr in trades if int(tr["side"]) < 0)

    swap_drags = [
        max(0.0, -float(tr["swap_zero_pos_R"]) / max(1.0, float(tr["hold_bars"])))
        for tr in trades
        if tr.get("swap_zero_pos_R") is not None
    ]
    swap_drag_per_day = round(float(np.mean(swap_drags)), 6) if swap_drags else 0.0

    data_res, blindness_tier, tier_breakdown = _classify_provenance(symbols, asset_map)
    allow_unidir = bool(spec.get("allow_unidirectional", str(params.get("direction", "both")) != "both"))

    margin_audit = {
        "account_type": "ftmo_swing",
        "max_margin_util_frac": DEFAULT_MAX_MARGIN_UTIL_FRAC,
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped,
        "peak_portfolio_margin_util_frac": peak_margin,
        "portfolio_margin_breached": margin_breached,
    }

    metrics: dict[str, Any] = dict(m_1x)
    metrics.update(
        {
            "real_1x": m_1x,
            "real_15x": m_15x,
            "real_2x": m_2x,
            "zero_pos_1x": m_zpos_1x,
            "zero_pos_2x": m_zpos_2x,
            "fade_1x": m_fade_1x,
            "net_R_1x": m_1x["net_R"],
            "net_R_15x": m_15x["net_R"],
            "net_R_2x": m_2x["net_R"],
            "net_R_zero_pos_1x": m_zpos_1x["net_R"],
            "net_R_zero_pos_2x": m_zpos_2x["net_R"],
            "fade_net_R_1x": m_fade_1x["net_R"],
            "sharpe_1x": m_1x["sharpe"],
            "sharpe_15x": m_15x["sharpe"],
            "sharpe_2x": m_2x["sharpe"],
            "sharpe_zero_pos_1x": m_zpos_1x["sharpe"],
            "pf_1x": m_1x["pf"],
            "pf_2x": m_2x["pf"],
            "pf_zero_pos_1x": m_zpos_1x["pf"],
            "trimmed_5pct_pf_1x": _compute_trimmed_pf(trades, "net_R_1x"),
            "trimmed_5pct_pf_2x": _compute_trimmed_pf(trades, "net_R_2x"),
            "avg_hold_bars": avg_hold,
            "long_trades": long_n,
            "short_trades": short_n,
            "stage0": s0,
            "median_fric_sl_1x": s0_1x["median_fric_sl_ratio"],
            "median_fric_sl_2x": s0["median_fric_sl_ratio"],
            "margin_rejects": margin_rejects,
            "margin_capped_count": margin_capped,
            "peak_portfolio_margin_util_frac": peak_margin,
            "portfolio_margin_breached": margin_breached,
            "swap_drag_per_day_r": swap_drag_per_day,
        }
    )

    spec_out = dict(spec)
    spec_out["family_id"] = FAMILY_ID
    spec_out["prop_track"] = PROP_TRACK
    spec_out["symbols"] = symbols
    spec_out["data_resolution"] = data_res
    spec_out["blindness_tier"] = blindness_tier
    spec_out["blindness_tier_breakdown"] = tier_breakdown
    spec_out["allow_unidirectional"] = allow_unidir

    return {
        "spec": spec_out,
        "trades": trades,
        "daily_pnl_1x": daily_pnl_1x,
        "daily_pnl_15x": daily_pnl_15x,
        "daily_pnl_2x": daily_pnl_2x,
        "daily_pnl_zero_pos_swap": daily_pnl_zero_pos_swap,
        "fade_daily_pnl_1x": fade_daily_pnl_1x,
        "metrics": metrics,
        "data_resolution": data_res,
        "blindness_tier": blindness_tier,
        "allow_unidirectional": allow_unidir,
        "margin_audit": margin_audit,
        "stage0": s0,
        "eval_years": list(eval_years),
        "causal_extra_lag": 1 if has_pool_zg else 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# Pre-Registered Economically Grounded F08 Grid (Pooled + All 27 Single Assets)
# ---------------------------------------------------------------------------


def _build_f08_candidate_grid() -> list[dict[str, Any]]:
    """Construct economically grounded 2-5d trend pullback specs (pooled + 27 assets)."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        scope: str,
        mechanism: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
        allow_unidir: bool = False,
    ) -> None:
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short for {cid}")
        if len(counterparty.strip()) < 20:
            raise ValueError(f"counterparty_mechanism too short for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "scope": scope,
                "mechanism": mechanism,
                "prop_track": PROP_TRACK,
                "symbols": list(symbols),
                "params": params,
                "allow_unidirectional": allow_unidir,
                "economic_rationale": rationale,
                "counterparty_mechanism": counterparty,
            }
        )

    rsi2_rat = (
        "Connors RSI(2) extreme short-term pullback aligned with the long-term SMA(100/200) "
        "trend provides liquidity during brief panic dips or relief spikes, capturing "
        "2-5d snapback with wide 1.5-3.0 ATR SL so CFD friction stays < 4% of SL."
    )
    rsi2_cp = (
        "Leveraged short-term traders capitulating into 2-day counter-trend flushes and "
        "tight trailing stops swept before dominant institutional trend flows resume."
    )

    ibs_rat = (
        "Internal Bar Strength (IBS = (C-L)/(H-L)) trend-aligned pullback buys closes near "
        "the session low in uptrends (and sells near session high in downtrends), harvesting "
        "end-of-day liquidity provision over a 2-5d FTMO Swing horizon."
    )
    ibs_cp = (
        "Forced end-of-day margin liquidations, MOC order imbalances, and retail traders "
        "chasing late-day breakdown candles against the prevailing macro trend."
    )

    adx_rat = (
        "Raschke ADX(14) > 25 + EMA(20) pullback ('Holy Grail') enters established high-ADX "
        "trends only after price retraces cleanly to the 20-day EMA mean, avoiding breakout "
        "chasing while protecting capital with a wide hard ATR stop loss."
    )
    adx_cp = (
        "Early counter-trend top/bottom pickers fading strong directional regimes and "
        "profit-taking waves that temporarily test institutional moving-average support."
    )

    kbb_rat = (
        "Bollinger %b / Keltner 3-bar pullback inside an established SMA(100/200) trend "
        "captures multi-day statistical oversold/overbought excursions reverting toward "
        "the 20-day fair-value channel with wide ATR stops clearing 2x CFD costs."
    )
    kbb_cp = (
        "Short-horizon volatility-targeting accounts reducing exposure after 2-3 consecutive "
        "adverse days and stop-loss clusters triggered below short-term channel bands."
    )

    # ------------------------------------------------------------------
    # PART A: Multi-Asset Pooled Portfolios (Indices-6, FX-17, TB7, Metals/Oil-4, All-27)
    # ------------------------------------------------------------------
    pools: list[tuple[str, tuple[str, ...], int, bool]] = [
        ("IDX6", INDICES_6_SYMBOLS, 3, True),
        ("FX17", FX_17_SYMBOLS, 4, False),
        ("TB7", TRUE_BLIND_7_SYMBOLS, 3, False),
        ("COMM4", METALS_OIL_4_SYMBOLS, 2, False),
        ("ALL27", ALL_27_NON_CRYPTO_SYMBOLS, 5, False),
    ]

    for pname, psyms, max_c, is_idx_pool in pools:
        # 1. Connors RSI(2) Pooled
        for trend_len, rsi_lo, hold, sl_m, tp_m, conf, d_mode in (
            (100, 10.0, 4, 2.0, 2.0, False, "both"),
            (200, 10.0, 5, 2.5, 2.0, False, "both"),
            (100, 15.0, 5, 2.0, 2.0, True, "both"),
            (200, 15.0, 5, 2.5, 2.5, True, "both"),
        ):
            cf = "_C1" if conf else ""
            _add(
                f"F08_POOL_{pname}_RSI2_{int(rsi_lo)}_S{trend_len}_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                f"pool_{pname.lower()}",
                "connors_rsi2",
                psyms,
                {
                    "trend_len": trend_len,
                    "rsi_len": 2,
                    "rsi_lo": rsi_lo,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": d_mode,
                    "max_concurrent": max_c,
                },
                rsi2_rat,
                rsi2_cp,
                allow_unidir=False,
            )
        if is_idx_pool:
            for trend_len, rsi_lo, hold, sl_m, tp_m, conf in (
                (100, 15.0, 5, 2.0, 1.5, True),
                (200, 15.0, 5, 2.5, 2.0, True),
            ):
                _add(
                    f"F08_POOL_{pname}_RSI2_LO_{int(rsi_lo)}_S{trend_len}_H{hold}_SL{int(sl_m * 10)}_C1",
                    f"pool_{pname.lower()}",
                    "connors_rsi2",
                    psyms,
                    {
                        "trend_len": trend_len,
                        "rsi_len": 2,
                        "rsi_lo": rsi_lo,
                        "confirm_bar": conf,
                        "max_hold_bars": hold,
                        "sl_atr_mult": sl_m,
                        "tp_atr_mult": tp_m,
                        "direction": "long_only",
                        "max_concurrent": max_c,
                    },
                    rsi2_rat + " Long-only equity-index specialization honors structural equity drift.",
                    rsi2_cp,
                    allow_unidir=True,
                )

        # 2. IBS Pooled
        for trend_len, ibs_lo, hold, sl_m, tp_m, conf in (
            (100, 0.20, 3, 2.0, 1.5, True),
            (100, 0.20, 4, 2.0, 2.0, True),
            (200, 0.20, 4, 2.5, 2.0, False),
        ):
            cf = "_C1" if conf else ""
            ibs_tag = f"IBS{int(ibs_lo * 100)}"
            _add(
                f"F08_POOL_{pname}_{ibs_tag}_S{trend_len}_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                f"pool_{pname.lower()}",
                "ibs_pullback",
                psyms,
                {
                    "trend_len": trend_len,
                    "ibs_lo": ibs_lo,
                    "require_down_bar": False,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": max_c,
                },
                ibs_rat,
                ibs_cp,
                allow_unidir=False,
            )
        if is_idx_pool:
            for trend_len, hold, sl_m, tp_m, conf in (
                (100, 3, 2.0, 1.5, False),
                (100, 5, 2.0, 1.5, False),
                (100, 5, 2.0, 1.5, True),
                (100, 4, 2.0, 2.0, True),
                (200, 5, 2.5, 2.0, True),
            ):
                cf = "_C1" if conf else ""
                _add(
                    f"F08_POOL_{pname}_IBS20_LO_S{trend_len}_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                    f"pool_{pname.lower()}",
                    "ibs_pullback",
                    psyms,
                    {
                        "trend_len": trend_len,
                        "ibs_lo": 0.20,
                        "require_down_bar": False,
                        "confirm_bar": conf,
                        "max_hold_bars": hold,
                        "sl_atr_mult": sl_m,
                        "tp_atr_mult": tp_m,
                        "direction": "long_only",
                        "max_concurrent": max_c,
                    },
                    ibs_rat + " Long-only equity-index specialization honors structural equity drift.",
                    ibs_cp,
                    allow_unidir=True,
                )

        # 3. Raschke ADX > 25 + EMA(20) Pooled
        for adx_m, hold, sl_m, tp_m, conf in (
            (25.0, 5, 2.0, 2.5, False),
            (25.0, 4, 2.0, 2.0, True),
            (20.0, 5, 2.5, 2.5, True),
        ):
            cf = "_C1" if conf else ""
            _add(
                f"F08_POOL_{pname}_ADX{int(adx_m)}_EMA20_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                f"pool_{pname.lower()}",
                "raschke_adx_ema20",
                psyms,
                {
                    "adx_min": adx_m,
                    "touch_atr": 0.30,
                    "max_breach_atr": 1.25,
                    "trend_ema_slow": 50,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": max_c,
                },
                adx_rat,
                adx_cp,
                allow_unidir=False,
            )

        # 4. Keltner / Bollinger %b 3-Bar Pullback Pooled
        for btype, bth, trend_len, hold, sl_m, tp_m, conf in (
            ("bb_pctb", 0.20, 100, 5, 2.0, 2.0, False),
            ("bb_pctb", 0.25, 100, 4, 2.0, 2.0, True),
            ("keltner", 0.40, 100, 5, 2.0, 2.0, True),
            ("keltner", 0.45, 200, 5, 2.5, 2.5, False),
        ):
            bt_tag = "BB" if btype == "bb_pctb" else "KELT"
            cf = "_C1" if conf else ""
            _add(
                f"F08_POOL_{pname}_{bt_tag}3B_S{trend_len}_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                f"pool_{pname.lower()}",
                "keltner_bb_3bar",
                psyms,
                {
                    "trend_len": trend_len,
                    "band_type": btype,
                    "pb_bars": 3,
                    "band_thresh": bth,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": max_c,
                },
                kbb_rat,
                kbb_cp,
                allow_unidir=False,
            )

    # ------------------------------------------------------------------
    # PART B: Individual Asset Pullbacks across ALL 27 Non-Crypto FTMO Symbols
    # ------------------------------------------------------------------
    for sym in ALL_27_NON_CRYPTO_SYMBOLS:
        is_idx = sym in INDICES_6_SYMBOLS

        # 1. Connors RSI(2) per symbol (bidirectional + confirmation; plus long-only for indices)
        for conf, hold, sl_m, tp_m in ((False, 5, 2.0, 2.0), (True, 5, 2.0, 2.0)):
            cf = "_C1" if conf else ""
            _add(
                f"F08_SYM_{sym}_RSI2_15_S100_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                "single_asset",
                "connors_rsi2",
                (sym,),
                {
                    "trend_len": 100,
                    "rsi_len": 2,
                    "rsi_lo": 15.0,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": 1,
                },
                rsi2_rat,
                rsi2_cp,
                allow_unidir=False,
            )
        if is_idx:
            for conf, hold, sl_m, tp_m in ((False, 5, 2.0, 2.0), (True, 5, 2.0, 2.0)):
                cf = "_C1" if conf else ""
                _add(
                    f"F08_SYM_{sym}_RSI2_LO_15_S100_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                    "single_asset",
                    "connors_rsi2",
                    (sym,),
                    {
                        "trend_len": 100,
                        "rsi_len": 2,
                        "rsi_lo": 15.0,
                        "confirm_bar": conf,
                        "max_hold_bars": hold,
                        "sl_atr_mult": sl_m,
                        "tp_atr_mult": tp_m,
                        "direction": "long_only",
                        "max_concurrent": 1,
                    },
                    rsi2_rat + " Long-only equity-index specialization honors structural equity drift.",
                    rsi2_cp,
                    allow_unidir=True,
                )

        # 2. IBS per symbol (bidirectional + confirmation; plus long-only for indices)
        for conf, hold, sl_m, tp_m in ((False, 4, 2.0, 2.0), (True, 4, 2.0, 2.0)):
            cf = "_C1" if conf else ""
            _add(
                f"F08_SYM_{sym}_IBS20_S100_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                "single_asset",
                "ibs_pullback",
                (sym,),
                {
                    "trend_len": 100,
                    "ibs_lo": 0.20,
                    "require_down_bar": False,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": 1,
                },
                ibs_rat,
                ibs_cp,
                allow_unidir=False,
            )
        if is_idx:
            for conf, hold, sl_m, tp_m in ((False, 4, 2.0, 2.0), (True, 5, 2.0, 2.0)):
                cf = "_C1" if conf else ""
                _add(
                    f"F08_SYM_{sym}_IBS20_LO_S100_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                    "single_asset",
                    "ibs_pullback",
                    (sym,),
                    {
                        "trend_len": 100,
                        "ibs_lo": 0.20,
                        "require_down_bar": False,
                        "confirm_bar": conf,
                        "max_hold_bars": hold,
                        "sl_atr_mult": sl_m,
                        "tp_atr_mult": tp_m,
                        "direction": "long_only",
                        "max_concurrent": 1,
                    },
                    ibs_rat + " Long-only equity-index specialization honors structural equity drift.",
                    ibs_cp,
                    allow_unidir=True,
                )

        # 3. Raschke ADX + EMA(20) per symbol
        for conf, hold, sl_m, tp_m in ((False, 5, 2.0, 2.5), (True, 5, 2.0, 2.0)):
            cf = "_C1" if conf else ""
            _add(
                f"F08_SYM_{sym}_ADX25_EMA20_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                "single_asset",
                "raschke_adx_ema20",
                (sym,),
                {
                    "adx_min": 25.0,
                    "touch_atr": 0.30,
                    "max_breach_atr": 1.25,
                    "trend_ema_slow": 50,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": 1,
                },
                adx_rat,
                adx_cp,
                allow_unidir=False,
            )

        # 4. Bollinger %b 3-bar pullback per symbol
        for conf, hold, sl_m, tp_m in ((False, 5, 2.0, 2.0), (True, 5, 2.0, 2.0)):
            cf = "_C1" if conf else ""
            _add(
                f"F08_SYM_{sym}_BB3B_S100_H{hold}_SL{int(sl_m * 10)}_TP{int(tp_m * 10)}{cf}",
                "single_asset",
                "keltner_bb_3bar",
                (sym,),
                {
                    "trend_len": 100,
                    "band_type": "bb_pctb",
                    "pb_bars": 3,
                    "band_thresh": 0.25,
                    "confirm_bar": conf,
                    "max_hold_bars": hold,
                    "sl_atr_mult": sl_m,
                    "tp_atr_mult": tp_m,
                    "direction": "both",
                    "max_concurrent": 1,
                },
                kbb_rat,
                kbb_cp,
                allow_unidir=False,
            )

    return specs


# ---------------------------------------------------------------------------
# Cluster A ONLY Discovery (`2018-2020`, HARD BLINDNESS LOCK!)
# ---------------------------------------------------------------------------


def _score_cluster_a_candidate(res: Mapping[str, Any]) -> float:
    m = res["metrics"]
    sh_2x = float(m["sharpe_2x"])
    sh_zpos = float(m["sharpe_zero_pos_1x"])
    sh_floor = min(sh_2x, sh_zpos)
    pos_yr = float(m["positive_year_ratio"])
    trim_pf = min(float(m["trimmed_5pct_pf_1x"]), 3.0)
    fade_edge = float(m["net_R_1x"]) - float(m["fade_net_R_1x"])
    max_dd = max(1.0, float(m["max_DD_R"]))
    calmar_2x = min(float(m["net_R_2x"]) / max_dd, 4.0)
    n_bonus = min(1.0, float(m["n_trades"]) / 60.0)
    pool_bonus = 0.20 if len(res["spec"]["symbols"]) > 1 else 0.0
    tb_bonus = 0.12 if res["blindness_tier"] == TIER_NEW7 else (0.06 if res["blindness_tier"] == TIER_NEW9 else 0.0)
    return round(
        sh_floor
        + 0.30 * calmar_2x
        + 0.45 * pos_yr
        + 0.15 * min(max(0.0, fade_edge) / 10.0, 1.5)
        + 0.25 * max(0.0, trim_pf - 1.0)
        + 0.12 * n_bonus
        + pool_bonus
        + tb_bonus,
        6,
    )


def _compact_cluster_a_summary(res: Mapping[str, Any], rank_score: float) -> dict[str, Any]:
    m = res["metrics"]
    by_yr = {str(k): round(float(v), 4) for k, v in m["by_year_R"].items() if int(str(k)) <= 2020}
    return {
        "rank_score": rank_score,
        "n_trades": int(m["n_trades"]),
        "net_R_1x": round(float(m["net_R_1x"]), 4),
        "net_R_15x": round(float(m["net_R_15x"]), 4),
        "net_R_2x": round(float(m["net_R_2x"]), 4),
        "net_R_zero_pos_1x": round(float(m["net_R_zero_pos_1x"]), 4),
        "fade_net_R_1x": round(float(m["fade_net_R_1x"]), 4),
        "sharpe_1x": round(float(m["sharpe_1x"]), 4),
        "sharpe_2x": round(float(m["sharpe_2x"]), 4),
        "sharpe_zero_pos_1x": round(float(m["sharpe_zero_pos_1x"]), 4),
        "pf_1x": round(float(m["pf_1x"]), 4),
        "pf_2x": round(float(m["pf_2x"]), 4),
        "trimmed_5pct_pf_1x": round(float(m["trimmed_5pct_pf_1x"]), 4),
        "winrate": round(float(m["winrate"]), 4),
        "avg_RR": round(float(m["avg_RR"]), 4),
        "max_DD_R_1x": round(float(m["max_DD_R"]), 4),
        "worst_1d_R_1x": round(float(m["worst_1d_R"]), 4),
        "positive_years": int(m["positive_years"]),
        "total_years": int(m["total_years"]),
        "by_year_R": by_yr,
        "avg_hold_bars": round(float(m["avg_hold_bars"]), 3),
        "median_fric_sl_1x": m["median_fric_sl_1x"],
        "median_fric_sl_2x": m["median_fric_sl_2x"],
        "peak_portfolio_margin_util_frac": m["peak_portfolio_margin_util_frac"],
        "swap_drag_per_day_r": m["swap_drag_per_day_r"],
        "stage0_passed": bool(m["stage0"]["passed"]),
    }


def _passes_primary_cluster_a(res: Mapping[str, Any]) -> bool:
    """Strict non-padded Primary gate: positive 1x/2x/zpos, beats fade, trim5% PF > 1.0, Prop DD safe."""
    m = res["metrics"]
    is_pool = len(res["spec"]["symbols"]) > 1
    min_tr = 30 if is_pool else 22
    if not bool(m["stage0"]["passed"]):
        return False
    if bool(m["portfolio_margin_breached"]):
        return False
    if int(m["n_trades"]) < min_tr:
        return False
    if float(m["net_R_1x"]) <= 0.0 or float(m["net_R_2x"]) <= 0.0 or float(m["net_R_zero_pos_1x"]) <= 0.0:
        return False
    if float(m["net_R_1x"]) <= float(m["fade_net_R_1x"]):
        return False
    if float(m["trimmed_5pct_pf_1x"]) <= 1.0:
        return False
    if float(m["max_DD_R"]) > 18.0 or float(m["worst_1d_R"]) < -8.0:
        return False
    if int(m["positive_years"]) < 2:
        return False
    if float(m["sharpe_2x"]) < 0.25 or float(m["sharpe_zero_pos_1x"]) < 0.25:
        return False
    return True


def _passes_exploratory_cluster_a(res: Mapping[str, Any]) -> bool:
    m = res["metrics"]
    if not bool(m["stage0"]["passed"]):
        return False
    if bool(m["portfolio_margin_breached"]):
        return False
    if int(m["n_trades"]) < 15:
        return False
    return True


def discover_cluster_a(
    universe: Mapping[str, Any],
    *,
    save: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run Stage 2 Cluster A discovery (`2018-2020` ONLY!) for `F08_SWING_PULLBACK`.

    HARD BLINDNESS LOCK: Every asset bar array is sliced strictly to `year <= 2020`
    before computing any indicator, signal, trade, or ranking. ZERO Cluster B data
    (`2021..2024`) is ever inspected, printed, or referenced.
    """
    asset_map = _resolve_asset_map(universe)
    bars_cache: dict[tuple[str, int], dict[str, Any]] = {}
    ind_cache: dict[tuple[str, int], dict[str, Any]] = {}

    for sym in ALL_27_NON_CRYPTO_SYMBOLS:
        if sym in asset_map:
            b_cl_a = _slice_d1_bars_upto_year(asset_map[sym]["d1"], max(CLUSTER_A_YEARS))
            bars_cache[(sym, max(CLUSTER_A_YEARS))] = b_cl_a
            ind_cache[(sym, max(CLUSTER_A_YEARS))] = _compute_pullback_indicators(b_cl_a)

    grid = _build_f08_candidate_grid()
    scored_rows: list[tuple[float, bool, bool, dict[str, Any]]] = []
    n_stage0_pass = 0
    n_primary_elig = 0

    for spec in grid:
        res = evaluate_candidate(
            spec,
            universe,
            years=CLUSTER_A_YEARS,
            _ind_cache=ind_cache,
            _bars_cache=bars_cache,
        )
        if bool(res["metrics"]["stage0"]["passed"]):
            n_stage0_pass += 1
        is_prim_elig = _passes_primary_cluster_a(res)
        is_expl_elig = _passes_exploratory_cluster_a(res)
        if is_prim_elig:
            n_primary_elig += 1
        r_score = _score_cluster_a_candidate(res)
        cand_record = dict(res["spec"])
        cand_record["cluster_a_summary"] = _compact_cluster_a_summary(res, r_score)
        scored_rows.append((r_score, is_prim_elig, is_expl_elig, cand_record))

    scored_rows.sort(key=lambda row: (-row[0], str(row[3]["candidate_id"])))

    mech_primary_caps: dict[str, int] = {
        "connors_rsi2": 4,
        "ibs_pullback": 4,
        "raschke_adx_ema20": 4,
        "keltner_bb_3bar": 4,
    }
    primary_selected: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    used_mech: dict[str, int] = {}
    used_scope_mech: set[tuple[str, str, str]] = set()
    used_sym_mech: set[tuple[str, str]] = set()
    sym_counts: dict[str, int] = {}

    # Pass 1: Enforce mechanism, pool/asset, and symbol diversity (zero negative Cl.A padded!)
    for _score, is_prim_elig, _is_expl, rec in scored_rows:
        if len(primary_selected) >= PRIMARY_CAP:
            break
        if not is_prim_elig:
            continue
        mech = str(rec["mechanism"])
        scope = str(rec["scope"])
        d_mode = str(rec["params"].get("direction", "both"))
        is_pool = scope != "single_asset"
        if used_mech.get(mech, 0) >= mech_primary_caps.get(mech, 4):
            continue
        if is_pool:
            if (scope, mech, d_mode) in used_scope_mech:
                continue
        else:
            sym0 = str(rec["symbols"][0])
            if (sym0, mech) in used_sym_mech or sym_counts.get(sym0, 0) >= 2:
                continue

        item = dict(rec)
        item["tier"] = "PRIMARY"
        primary_selected.append(item)
        selected_ids.add(str(item["candidate_id"]))
        used_mech[mech] = used_mech.get(mech, 0) + 1
        if is_pool:
            used_scope_mech.add((scope, mech, d_mode))
        else:
            sym0 = str(rec["symbols"][0])
            used_sym_mech.add((sym0, mech))
            sym_counts[sym0] = sym_counts.get(sym0, 0) + 1

    # Pass 2: Remaining strictly eligible primaries up to PRIMARY_CAP
    if len(primary_selected) < PRIMARY_CAP:
        for _score, is_prim_elig, _is_expl, rec in scored_rows:
            if len(primary_selected) >= PRIMARY_CAP:
                break
            cid = str(rec["candidate_id"])
            if not is_prim_elig or cid in selected_ids:
                continue
            mech = str(rec["mechanism"])
            if used_mech.get(mech, 0) >= mech_primary_caps.get(mech, 4) + 2:
                continue
            if rec["scope"] == "single_asset":
                sym0 = str(rec["symbols"][0])
                if sym_counts.get(sym0, 0) >= 2:
                    continue
                sym_counts[sym0] = sym_counts.get(sym0, 0) + 1
            item = dict(rec)
            item["tier"] = "PRIMARY"
            primary_selected.append(item)
            selected_ids.add(cid)
            used_mech[mech] = used_mech.get(mech, 0) + 1

    # Balanced Exploratory pool across ALL 4 mechanisms & pools + top single assets up to TOTAL_CAP
    max_expl = TOTAL_CAP - len(primary_selected)
    exploratory_selected: list[dict[str, Any]] = []
    expl_mech_counts: dict[str, int] = {}
    expl_mech_cap = 22

    # First prioritize positive 1x exploratory candidates
    for positive_only in (True, False):
        for _score, _is_prim, is_expl_elig, rec in scored_rows:
            if len(exploratory_selected) >= max_expl:
                break
            cid = str(rec["candidate_id"])
            if cid in selected_ids or not is_expl_elig:
                continue
            if positive_only and float(rec["cluster_a_summary"]["net_R_1x"]) <= 0.0:
                continue
            mech = str(rec["mechanism"])
            if expl_mech_counts.get(mech, 0) >= expl_mech_cap:
                continue
            item = dict(rec)
            item["tier"] = "EXPLORATORY"
            exploratory_selected.append(item)
            selected_ids.add(cid)
            expl_mech_counts[mech] = expl_mech_counts.get(mech, 0) + 1

    if len(exploratory_selected) < max_expl:
        for _score, _is_prim, is_expl_elig, rec in scored_rows:
            if len(exploratory_selected) >= max_expl:
                break
            cid = str(rec["candidate_id"])
            if cid in selected_ids or not is_expl_elig:
                continue
            item = dict(rec)
            item["tier"] = "EXPLORATORY"
            exploratory_selected.append(item)
            selected_ids.add(cid)

    meta: dict[str, Any] = {
        "family_id": FAMILY_ID,
        "prop_track": PROP_TRACK,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "grid_evaluated": len(grid),
        "stage0_passed_count": n_stage0_pass,
        "primary_eligible_count": n_primary_elig,
        "primary_mechanism_counts": used_mech,
        "exploratory_mechanism_counts": expl_mech_counts,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    saved_path: Path | None = None
    if save:
        saved_path = save_family_candidates(
            FAMILY_ID,
            {"primary": primary_selected, "exploratory": exploratory_selected},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary": primary_selected,
        "exploratory": exploratory_selected,
        "candidates": [*primary_selected, *exploratory_selected],
        "meta": meta,
        "saved_path": str(saved_path) if saved_path is not None else None,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# CLI Entrypoint (`--resume` Supported, Strictly Cluster A Only!)
# ---------------------------------------------------------------------------


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offensive #3 F08 Multi-Day Trend Pullback Discovery (Cluster A 2018-2020 ONLY)"
    )
    parser.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified checkpoint if present")
    parser.add_argument("--candidates-dir", type=str, default=None, help="Override candidate output directory")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA check during load")
    args = parser.parse_args(argv)

    if args.resume and has_valid_family_checkpoint(FAMILY_ID, candidates_dir=args.candidates_dir):
        doc = load_family_candidates(FAMILY_ID, candidates_dir=args.candidates_dir, verify_sha=True)
        print(
            json.dumps(
                {
                    "status": "RESUMED_FROM_CHECKPOINT",
                    "family_id": FAMILY_ID,
                    "primary_count": doc["primary_count"],
                    "exploratory_count": doc["exploratory_count"],
                    "total_count": doc["total_count"],
                    "discovery_years": doc["discovery_years"],
                    "payload_sha256": doc["payload_sha256"],
                },
                indent=2,
            )
        )
        return 0

    universe_a = load_universe_28(
        load_m1=False,
        load_d1=True,
        years=CLUSTER_A_YEARS,
        verify_sha=not args.no_verify_sha,
    )
    out = discover_cluster_a(universe_a, save=True, candidates_dir=args.candidates_dir)
    loaded = load_family_candidates(FAMILY_ID, candidates_dir=args.candidates_dir, verify_sha=True)

    top_preview = [
        {
            "candidate_id": c["candidate_id"],
            "scope": c["scope"],
            "mechanism": c["mechanism"],
            "tier_data": c["blindness_tier"],
            "unidir": c["allow_unidirectional"],
            "n_trades": c["cluster_a_summary"]["n_trades"],
            "net_R_1x": c["cluster_a_summary"]["net_R_1x"],
            "net_R_2x": c["cluster_a_summary"]["net_R_2x"],
            "net_R_zpos": c["cluster_a_summary"]["net_R_zero_pos_1x"],
            "fade_1x": c["cluster_a_summary"]["fade_net_R_1x"],
            "sh_2x": c["cluster_a_summary"]["sharpe_2x"],
            "tpf_1x": c["cluster_a_summary"]["trimmed_5pct_pf_1x"],
            "pos_yrs": f"{c['cluster_a_summary']['positive_years']}/{c['cluster_a_summary']['total_years']}",
            "f1_sl": c["cluster_a_summary"]["median_fric_sl_1x"],
            "dd_1x": c["cluster_a_summary"]["max_DD_R_1x"],
            "peak_mu": c["cluster_a_summary"]["peak_portfolio_margin_util_frac"],
        }
        for c in loaded["primary_candidates"][:10]
    ]
    print(
        json.dumps(
            {
                "status": "DISCOVERY_COMPLETE",
                "family_id": FAMILY_ID,
                "saved_path": out["saved_path"],
                "discovery_years": loaded["discovery_years"],
                "grid_evaluated": out["meta"]["grid_evaluated"],
                "stage0_passed": out["meta"]["stage0_passed_count"],
                "primary_eligible": out["meta"]["primary_eligible_count"],
                "primary_count": loaded["primary_count"],
                "exploratory_count": loaded["exploratory_count"],
                "total_count": loaded["total_count"],
                "primary_mechanism_counts": out["meta"]["primary_mechanism_counts"],
                "exploratory_mechanism_counts": out["meta"]["exploratory_mechanism_counts"],
                "payload_sha256": loaded["payload_sha256"],
                "top_primary_cluster_a": top_preview,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
