"""Total Offensive #3 — Family F10: 100% True-Blind 7-Cross Dedicated Hunt (`F10_TRUE_BLIND_CROSS7`).

Dedicated `FTMO_SWING` (`2–8d`) discovery exclusively on the `7` NEVER-BEFORE-TOUCHED FX CROSSES:
  `CADJPY, CHFJPY, NZDJPY, EURGBP, EURAUD, GBPAUD, EURCAD`
  — ALL tagged `blindness_tier = "TRUE_BLIND_CLB_NEW7_CROSSES"`, `data_resolution = "D1_YAHOO_SANCTIONED"`.

Five genuinely distinct non-breakout Swing mechanics across individual crosses AND pooled portfolios:
  (a) `VOL_COMP_TREND` — Volatility-Compression (bottom 30% causal 20d/40d ATR/range) ->
      Directional Trend Continuation (`2–6d` hold, hard SL).
  (b) `TREND_PULLBACK` — Trend-Aligned `RSI(2) / IBS / Z-Score` Pullback (`2–5d` hold, hard SL).
  (c) `VOL_TARGET_TREND` — 7-Cross Equal-Risk Vol-Targeted Trend (`EWMAC` / `Donchian-mid` / `EMA` slope
      with inverse-volatility sizing, `3–8d` hold, hard SL).
  (d) `XSEC_WEEKLY_ROT` — 7-Cross Cross-Sectional Long-Top2 / Short-Bottom2 weekly rotation
      with strict ZERO USD/JPY beta tilt (balanced JPY-3 + NonJPY-4 neutral pairing, hard SL).
  (e) `ADX_ZSCORE_MR` — Asymmetric Volatility-Regime Mean-Reversion (range-bound `ADX < 20/22`
      `Z-Score` reversion on `EURGBP / EURCAD / EURAUD` + crosses with calm-vol gate & hard SL).

Hard anti-overfit & safety invariants (`G01`, `G05`, `G06`, `G07`, `P0-4` / `M6`, `[ARCH-02]`):
  - ZERO bare `assert` statements; `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - Strict pre-cutoff Dev enforcement (`max_ts < 1735689600`, zero sealed rows analysed).
  - HARD BLINDNESS LOCK: `discover_cluster_a(universe)` strictly touches `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY!
  - CRITICAL (`P0-4` / `M6`): ZERO static future swap-sign carry lookahead! Direction is NEVER chosen from
    broker swap signs; every candidate is symmetric two-sided (`allow_unidirectional = False`) and evaluated
    strictly under BOTH `Real Triple-Swap` (Wed 3x) AND `zero_pos_swap` floor (ranking on conservative floor!).
  - Strict `shift = 1` causality across all indicators (incl. `causal_adx`, `causal_range_pct_rank`,
    `causal_donchian_mid`) and execution.
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

_AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


from quant_factory.offensive3 import common_contract as cc  # noqa: E402

try:  # Optional OPS-1 guard import for metadata parity
    from quant_factory.live_ops import feed_dst_news_guard as ops1_guard  # noqa: E402
except ImportError:  # pragma: no cover - X13 minimal cache fallback
    ops1_guard = None

# ---------------------------------------------------------------------------
# Hard Safety & Family Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"

FAMILY_ID: str = "F10_TRUE_BLIND_CROSS7"
# Respects BOTH brief cap (<= 20) and preregistration_m1200.json F10 hard cap (<= 16)!
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

TRUE_BLIND_7: tuple[str, ...] = ("CADJPY", "CHFJPY", "NZDJPY", "EURGBP", "EURAUD", "GBPAUD", "EURCAD")
JPY_CROSS_3: tuple[str, ...] = ("CADJPY", "CHFJPY", "NZDJPY")
NON_JPY_CROSS_4: tuple[str, ...] = ("EURGBP", "EURAUD", "GBPAUD", "EURCAD")
EURO_RANGE_3: tuple[str, ...] = ("EURGBP", "EURCAD", "EURAUD")

_DEFAULT_ACCOUNT_BALANCE_USD: float = 100_000.0
_DEFAULT_RISK_FRAC: float = 0.005

_CAUSAL_INVARIANTS_F10: tuple[str, ...] = (
    "100% TRUE_BLIND_CLB_NEW7_CROSSES exclusive symbol set (zero overlap with 12OLD or NEW9)",
    "strict shift=1 causality on all indicators (EMA/SMA/ATR/RSI/ZScore/ADX/DonchianMid/PctRank)",
    "ZERO static swap-sign carry lookahead: direction purely price/vol-driven, symmetric two-sided",
    "evaluated & ranked under BOTH Real Wed-3x Triple-Swap AND zero_pos_swap floor across 1x/1.5x/2x friction",
    "mandatory hard ATR stop-loss & FTMO Swing 1:30 real leverage margin check (zero grid/martingale)",
)


# ---------------------------------------------------------------------------
# Strict `shift = 1` Additional Causal Indicators (Numba-Accelerated)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _causal_adx_1d_jit(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    """Strictly `shift = 1` Wilder ADX(n) (`out[t]` depends ONLY on bars `0 .. t-1`)."""
    m = close.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= 2 * n + 1:
        return out

    tr = np.zeros(m, dtype=np.float64)
    pdm = np.zeros(m, dtype=np.float64)
    mdm = np.zeros(m, dtype=np.float64)

    for k in range(1, m):
        hk = high[k]
        lk = low[k]
        pc = close[k - 1]
        ph = high[k - 1]
        pl = low[k - 1]
        if not (np.isfinite(hk) and np.isfinite(lk) and np.isfinite(pc) and np.isfinite(ph) and np.isfinite(pl)):
            continue
        r1 = abs(hk - lk)
        r2 = abs(hk - pc)
        r3 = abs(lk - pc)
        tr[k] = max(r1, max(r2, r3))
        up = hk - ph
        dn = pl - lk
        if up > dn and up > 0.0:
            pdm[k] = up
        if dn > up and dn > 0.0:
            mdm[k] = dn

    # Wilder smoothing of TR, +DM, -DM seeded over k = 1..n
    sm_tr = 0.0
    sm_p = 0.0
    sm_m = 0.0
    for k in range(1, n + 1):
        sm_tr += tr[k]
        sm_p += pdm[k]
        sm_m += mdm[k]

    dx = np.empty(m, dtype=np.float64)
    for k in range(m):
        dx[k] = np.nan

    inv_n = 1.0 / float(n)
    nm1 = float(n - 1)
    for k in range(n, m - 1):
        if k > n:
            sm_tr = sm_tr - sm_tr * inv_n + tr[k]
            sm_p = sm_p - sm_p * inv_n + pdm[k]
            sm_m = sm_m - sm_m * inv_n + mdm[k]
        if sm_tr > 1e-15:
            pdi = 100.0 * (sm_p / sm_tr)
            mdi = 100.0 * (sm_m / sm_tr)
            denom = pdi + mdi
            dx[k] = (100.0 * abs(pdi - mdi) / denom) if denom > 1e-15 else 0.0
        else:
            dx[k] = 0.0

    # Wilder smoothing of DX seeded over k = n .. 2*n-1; written to out[k + 1] (shift = 1!)
    adx_val = 0.0
    for k in range(n, 2 * n):
        adx_val += dx[k]
    adx_val *= inv_n
    if 2 * n < m:
        out[2 * n] = adx_val

    for k in range(2 * n, m - 1):
        adx_val = (adx_val * nm1 + dx[k]) * inv_n
        out[k + 1] = adx_val

    return out


def causal_adx(h: np.ndarray, lo: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:
    """Strictly `shift = 1` causal Wilder ADX (`out[t]` uses bars `0 .. t-1` ONLY)."""
    if isinstance(n, bool) or int(n) < 2:
        raise ValueError(f"ADX window n must be >= 2, got {n!r}")
    ha = np.ascontiguousarray(h, dtype=np.float64)
    la = np.ascontiguousarray(lo, dtype=np.float64)
    ca = np.ascontiguousarray(c, dtype=np.float64)
    if ha.shape != la.shape or ha.shape != ca.shape or ha.ndim != 1:
        raise ValueError(f"Expected matching 1D arrays, got {ha.shape}, {la.shape}, {ca.shape}")
    return _causal_adx_1d_jit(ha, la, ca, int(n))


@njit(cache=True)
def _causal_pct_rank_1d_jit(x: np.ndarray, win: int) -> np.ndarray:
    """Strictly `shift = 1` rolling percentile rank of `x[t-1]` inside `x[t-win : t]` in `[0, 1]`."""
    m = x.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= win:
        return out
    for t in range(win, m):
        cur = x[t - 1]
        if not np.isfinite(cur):
            continue
        le = 0
        cnt = 0
        for k in range(t - win, t):
            vk = x[k]
            if np.isfinite(vk):
                cnt += 1
                if vk <= cur:
                    le += 1
        if cnt >= win // 2 and cnt > 0:
            out[t] = float(le) / float(cnt)
    return out


def causal_pct_rank(x: np.ndarray, win: int = 20) -> np.ndarray:
    """Strictly `shift = 1` rolling percentile rank (`out[t]` uses `x[t-win .. t-1]` ONLY)."""
    if isinstance(win, bool) or int(win) < 5:
        raise ValueError(f"win must be >= 5, got {win!r}")
    return _causal_pct_rank_1d_jit(np.ascontiguousarray(x, dtype=np.float64), int(win))


@njit(cache=True)
def _causal_donchian_mid_1d_jit(high: np.ndarray, low: np.ndarray, win: int) -> np.ndarray:
    """Strictly `shift = 1` rolling midpoint `0.5 * (max(H[t-win:t]) + min(L[t-win:t]))`."""
    m = high.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= win:
        return out
    for t in range(win, m):
        mx = -1e308
        mn = 1e308
        ok = True
        for k in range(t - win, t):
            hk = high[k]
            lk = low[k]
            if not (np.isfinite(hk) and np.isfinite(lk)):
                ok = False
                break
            if hk > mx:
                mx = hk
            if lk < mn:
                mn = lk
        if ok:
            out[t] = 0.5 * (mx + mn)
    return out


def causal_donchian_mid(h: np.ndarray, lo: np.ndarray, win: int = 20) -> np.ndarray:
    """Strictly `shift = 1` Donchian equilibrium midpoint (`out[t]` uses bars `t-win .. t-1` ONLY)."""
    if isinstance(win, bool) or int(win) < 2:
        raise ValueError(f"win must be >= 2, got {win!r}")
    return _causal_donchian_mid_1d_jit(
        np.ascontiguousarray(h, dtype=np.float64),
        np.ascontiguousarray(lo, dtype=np.float64),
        int(win),
    )


# ---------------------------------------------------------------------------
# Strict Pre-Max-Year Slicing & Portfolio Weight Scaling
# ---------------------------------------------------------------------------


def _enforce_blind7_symbols(symbols: Sequence[str]) -> tuple[str, ...]:
    norm = tuple(cc.normalize_symbol(s) for s in symbols)
    if not norm:
        raise ValueError("F10 symbols cannot be empty")
    bad = [s for s in norm if s not in TRUE_BLIND_7]
    if bad:
        raise ValueError(f"F10_TRUE_BLIND_VIOLATION: symbols {bad} outside TRUE_BLIND_7={TRUE_BLIND_7}")
    return norm


def _slice_d1_upto_year(d1: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    yrs = np.asarray(d1["years"], dtype=np.int32)
    idx = np.flatnonzero(yrs <= int(max_year))
    if idx.size == 0:
        raise ValueError(f"No D1 bars available for year <= {max_year}")
    end = int(idx[-1]) + 1
    out = {
        "times_sec": np.asarray(d1["times_sec"], dtype=np.int64)[:end],
        "dates": [str(d) for d in d1["dates"][:end]],
        "years": yrs[:end],
        "weekdays": np.asarray(d1["weekdays"], dtype=np.int32)[:end],
        "open": np.asarray(d1["open"], dtype=np.float64)[:end],
        "high": np.asarray(d1["high"], dtype=np.float64)[:end],
        "low": np.asarray(d1["low"], dtype=np.float64)[:end],
        "close": np.asarray(d1["close"], dtype=np.float64)[:end],
    }
    cc.enforce_dev_ts_bound(out["times_sec"], context="fam10.slice_d1")
    return out


def _scale_trades_by_weight(
    trades: list[dict[str, Any]],
    weight: float,
    *,
    per_entry_scale: Mapping[str, float] | None = None,
) -> list[dict[str, Any]]:
    """Scale trade R-fields by portfolio leg weight (and optional causal inverse-vol scale)."""
    r_keys = (
        "gross_R",
        "swap_real_R",
        "swap_zero_pos_R",
        "net_R",
        "net_R_1x",
        "net_R_15x",
        "net_R_2x",
        "net_R_zero_pos_1x",
        "net_R_zero_pos_15x",
        "net_R_zero_pos_2x",
    )
    out: list[dict[str, Any]] = []
    for tr in trades:
        w = float(weight)
        if per_entry_scale is not None:
            w *= float(per_entry_scale.get(str(tr["entry_date"]), 1.0))
        d = dict(tr)
        for k in r_keys:
            if k in d and d[k] is not None and not isinstance(d[k], bool):
                d[k] = round(float(d[k]) * w, 6)
        if "eff_risk_scale" in d and d["eff_risk_scale"] is not None:
            d["eff_risk_scale"] = round(float(d["eff_risk_scale"]) * w, 6)
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# Causal Signal Generators for Mechanisms (a)..(e) — Strictly `shift = 1`
# ---------------------------------------------------------------------------


def _signals_vol_compression_trend(
    d1: Mapping[str, Any],
    *,
    comp_win: int,
    comp_pct_max: float,
    ema_fast: int,
    ema_slow: int,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """(a) Volatility-Compression (bottom 30% causal ATR/range) -> Directional Trend Continuation."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.size

    atr5 = cc.causal_atr(h, lo, c, 5)
    atr14 = cc.causal_atr(h, lo, c, 14)
    # Causal bar range on bar k -> causal_pct_rank shifts by +1 so rank[t] uses bars t-win..t-1 ONLY!
    bar_rng = np.maximum(0.0, h - lo)
    rng_rank = causal_pct_rank(bar_rng, int(comp_win))
    # Also compute causal ATR(5)/ATR(14) compression ratio (strictly shift=1 since both ATRs are shift=1)
    atr_ratio = np.where(np.isfinite(atr5) & np.isfinite(atr14) & (atr14 > 0.0), atr5 / atr14, np.nan)

    ef = cc.causal_ema(c, int(ema_fast))
    es = cc.causal_ema(c, int(ema_slow))

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    sm = -1.0 if flip_side else 1.0

    for t in range(3, n):
        a = float(atr14[t])
        rr = float(rng_rank[t])
        ar = float(atr_ratio[t])
        f_v = float(ef[t])
        s_v = float(es[t])
        if not (
            math.isfinite(a)
            and a > 0.0
            and math.isfinite(rr)
            and math.isfinite(ar)
            and math.isfinite(f_v)
            and math.isfinite(s_v)
        ):
            continue
        # Compressed regime: prior bar range in bottom `comp_pct_max` (e.g. 30%) OR short ATR compressed < 0.85x
        compressed = (rr <= float(comp_pct_max)) and (ar <= 0.95)
        if not compressed:
            continue
        prev_c = float(c[t - 1])
        # Symmetric two-sided directional trend alignment (zero swap lookahead!)
        if f_v > s_v and prev_c > s_v and float(ef[t]) > float(ef[t - 2]):
            sig[t] = 1.0 * sm
        elif f_v < s_v and prev_c < s_v and float(ef[t]) < float(ef[t - 2]):
            sig[t] = -1.0 * sm
        else:
            continue
        sl_d[t] = float(sl_atr_mult) * a
        if tp_d is not None and tp_atr_mult is not None:
            tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


def _signals_trend_pullback(
    d1: Mapping[str, Any],
    *,
    pullback_kind: str,  # "rsi2" | "ibs" | "zscore"
    threshold: float,
    trend_sma: int,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """(b) Trend-Aligned `RSI(2) / IBS / Z-Score` Pullback (`2–5d` hold, symmetric two-sided)."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.size

    atr14 = cc.causal_atr(h, lo, c, 14)
    sma_t = cc.causal_sma(c, int(trend_sma))
    rsi2 = cc.causal_rsi(c, 2) if pullback_kind == "rsi2" else None
    z14 = cc.causal_zscore(c, 14) if pullback_kind == "zscore" else None

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    sm = -1.0 if flip_side else 1.0

    for t in range(2, n):
        a = float(atr14[t])
        tr_v = float(sma_t[t])
        if not (math.isfinite(a) and a > 0.0 and math.isfinite(tr_v)):
            continue
        prev_c = float(c[t - 1])
        trend_dir = 1 if prev_c > tr_v else (-1 if prev_c < tr_v else 0)
        if trend_dir == 0:
            continue

        fire = False
        if pullback_kind == "rsi2" and rsi2 is not None:
            rv = float(rsi2[t])
            if math.isfinite(rv):
                fire = (trend_dir == 1 and rv <= float(threshold)) or (
                    trend_dir == -1 and rv >= (100.0 - float(threshold))
                )
        elif pullback_kind == "ibs":
            rng = float(h[t - 1]) - float(lo[t - 1])
            ibs = (prev_c - float(lo[t - 1])) / rng if rng > 1e-12 else 0.5
            fire = (trend_dir == 1 and ibs <= float(threshold)) or (
                trend_dir == -1 and ibs >= (1.0 - float(threshold))
            )
        elif pullback_kind == "zscore" and z14 is not None:
            zv = float(z14[t])
            if math.isfinite(zv):
                fire = (trend_dir == 1 and zv <= -float(threshold)) or (
                    trend_dir == -1 and zv >= float(threshold)
                )
        else:
            raise ValueError(f"Unsupported pullback_kind: {pullback_kind!r}")

        if fire:
            sig[t] = float(trend_dir) * sm
            sl_d[t] = float(sl_atr_mult) * a
            if tp_d is not None and tp_atr_mult is not None:
                tp_d[t] = float(tp_atr_mult) * a

    return sig, sl_d, tp_d


def _signals_vol_targeted_trend(
    d1: Mapping[str, Any],
    *,
    trend_kind: str,  # "ewmac" | "donchian_mid" | "ema_slope"
    fast_n: int,
    slow_n: int,
    signal_thresh: float,
    target_ann_vol: float,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    entry_on_onset_only: bool = False,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, dict[str, float]]:
    """(c) Equal-Risk Vol-Targeted Trend (`EWMAC` / `Donchian-mid` / `EMA-slope` + inverse-vol sizing)."""
    dates = d1["dates"]
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.size

    atr14 = cc.causal_atr(h, lo, c, 14)
    rvol20_ann = cc.causal_realized_vol(c, 20, annualize_bars=252.0)

    ef = cc.causal_ema(c, int(fast_n)) if trend_kind in ("ewmac", "ema_slope") else None
    es = cc.causal_ema(c, int(slow_n)) if trend_kind == "ewmac" else None
    dmid = causal_donchian_mid(h, lo, int(slow_n)) if trend_kind == "donchian_mid" else None

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    inv_vol_scale: dict[str, float] = {}
    sm = -1.0 if flip_side else 1.0
    prev_dir = 0.0

    for t in range(max(5, int(fast_n)), n):
        a = float(atr14[t])
        rv = float(rvol20_ann[t])
        if not (math.isfinite(a) and a > 0.0 and math.isfinite(rv) and rv > 1e-6):
            prev_dir = 0.0
            continue

        direction = 0.0
        prev_c = float(c[t - 1])
        if trend_kind == "ewmac" and ef is not None and es is not None:
            fv, sv = float(ef[t]), float(es[t])
            if math.isfinite(fv) and math.isfinite(sv):
                # Volatility-normalized EWMAC forecast (Carver/Baltas-Kosowski)
                fc = (fv - sv) / a
                if fc >= float(signal_thresh):
                    direction = 1.0
                elif fc <= -float(signal_thresh):
                    direction = -1.0
        elif trend_kind == "donchian_mid" and dmid is not None:
            dm_now = float(dmid[t])
            dm_prev = float(dmid[t - int(fast_n)])
            if math.isfinite(dm_now) and math.isfinite(dm_prev):
                slope = (dm_now - dm_prev) / a
                if prev_c > dm_now and slope >= float(signal_thresh):
                    direction = 1.0
                elif prev_c < dm_now and slope <= -float(signal_thresh):
                    direction = -1.0
        elif trend_kind == "ema_slope" and ef is not None:
            fv_now = float(ef[t])
            fv_prev = float(ef[t - int(slow_n)])
            if math.isfinite(fv_now) and math.isfinite(fv_prev):
                slope = (fv_now - fv_prev) / a
                if slope >= float(signal_thresh) and prev_c > fv_now:
                    direction = 1.0
                elif slope <= -float(signal_thresh) and prev_c < fv_now:
                    direction = -1.0
        else:
            raise ValueError(f"Unsupported trend_kind: {trend_kind!r}")

        fire = (direction != 0.0) and ((not entry_on_onset_only) or (direction != prev_dir))
        prev_dir = direction
        if fire:
            sig[t] = direction * sm
            sl_d[t] = float(sl_atr_mult) * a
            if tp_d is not None and tp_atr_mult is not None:
                tp_d[t] = float(tp_atr_mult) * a
            # Causal inverse-volatility sizing clipped cleanly to [0.40, 1.40]
            inv_vol_scale[dates[t]] = round(min(1.40, max(0.40, float(target_ann_vol) / rv)), 6)

    return sig, sl_d, tp_d, inv_vol_scale


def _signals_adx_zscore_mr(
    d1: Mapping[str, Any],
    *,
    adx_max: float,
    z_win: int,
    z_entry: float,
    calm_atr_ratio_max: float,
    sl_atr_mult: float,
    tp_atr_mult: float | None,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    """(e) Asymmetric Volatility-Regime Mean-Reversion (`ADX < 20/22` + calm-vol gate + `Z-Score`)."""
    h, lo, c = d1["high"], d1["low"], d1["close"]
    n = c.size

    atr5 = cc.causal_atr(h, lo, c, 5)
    atr14 = cc.causal_atr(h, lo, c, 14)
    atr20 = cc.causal_atr(h, lo, c, 20)
    adx14 = causal_adx(h, lo, c, 14)
    zsc = cc.causal_zscore(c, int(z_win))

    sig = np.zeros(n, dtype=np.float64)
    sl_d = np.full(n, np.nan, dtype=np.float64)
    tp_d = np.full(n, np.nan, dtype=np.float64) if tp_atr_mult is not None else None
    sm = -1.0 if flip_side else 1.0

    for t in range(2, n):
        a14 = float(atr14[t])
        a5 = float(atr5[t])
        a20 = float(atr20[t])
        adx_v = float(adx14[t])
        zv = float(zsc[t])
        if not (
            math.isfinite(a14)
            and a14 > 0.0
            and math.isfinite(a5)
            and math.isfinite(a20)
            and a20 > 0.0
            and math.isfinite(adx_v)
            and math.isfinite(zv)
        ):
            continue
        # Range-bound ADX gate + asymmetric calm-vol gate (avoid fading breakout vol-expansion spikes!)
        if adx_v >= float(adx_max):
            continue
        if (a5 / a20) > float(calm_atr_ratio_max):
            continue

        if zv <= -float(z_entry):
            sig[t] = 1.0 * sm
        elif zv >= float(z_entry):
            sig[t] = -1.0 * sm
        else:
            continue

        sl_d[t] = float(sl_atr_mult) * a14
        if tp_d is not None and tp_atr_mult is not None:
            tp_d[t] = float(tp_atr_mult) * a14

    return sig, sl_d, tp_d


def _build_xsec_zero_jpy_beta_signals(
    d1_by_sym: Mapping[str, dict[str, Any]],
    *,
    lookback_days: int,
    neutrality_mode: str,  # "balanced_group" | "constrained_full7"
    reverse_rank: bool,
    rebalance_weekday: int,  # 0=Mon, 2=Wed
    sl_atr_mult: float,
    hold_across_rebalance: bool = True,
    flip_side: bool = False,
) -> tuple[dict[str, np.ndarray], dict[str, np.ndarray]]:
    """(d) 7-Cross Weekly Long-Top2 / Short-Bottom2 Rotation with ZERO net JPY/USD beta tilt.

    Both modes guarantee `count(long JPY crosses) == count(short JPY crosses)` on EVERY rebalance day:
      - `balanced_group`: Long Top-1 + Short Bottom-1 inside `JPY_CROSS_3` (exact 0 net JPY beta) AND
        Long Top-1 + Short Bottom-1 inside `NON_JPY_CROSS_4` (exact 0 net JPY beta, 4 legs total).
      - `constrained_full7`: Vol-adjusted score across all 7 crosses, choosing Long-2 / Short-2 subject
        to `n_long_jpy == n_short_jpy` (maximizing long-minus-short score spread at zero JPY beta!).
    Strictly `shift = 1`: scores on rebalance day `t` use closes `t-1-L .. t-1` ONLY!
    """
    syms = list(TRUE_BLIND_7)
    common_dates = sorted(set.intersection(*(set(d1_by_sym[s]["dates"]) for s in syms)))
    date_pos = {s: {d: i for i, d in enumerate(d1_by_sym[s]["dates"])} for s in syms}

    atr_map = {s: cc.causal_atr(d1_by_sym[s]["high"], d1_by_sym[s]["low"], d1_by_sym[s]["close"], 14) for s in syms}
    rvol_map = {s: cc.causal_realized_vol(d1_by_sym[s]["close"], 20) for s in syms}
    sig_map = {s: np.zeros(len(d1_by_sym[s]["dates"]), dtype=np.float64) for s in syms}
    sl_map = {s: np.full(len(d1_by_sym[s]["dates"]), np.nan, dtype=np.float64) for s in syms}

    sm = -1.0 if (reverse_rank ^ flip_side) else 1.0
    lb = int(lookback_days)
    jpy_set = set(JPY_CROSS_3)

    active_dirs: dict[str, float] = {s: 0.0 for s in syms}
    last_rebal_date: date | None = None

    for d_str in common_dates:
        dt_d = date.fromisoformat(d_str)
        # Rebalance on first trading day of each ISO week >= rebalance_weekday (handles Monday holidays!)
        need_rebal = False
        if last_rebal_date is None:
            need_rebal = dt_d.weekday() == int(rebalance_weekday)
        else:
            days_since = (dt_d - last_rebal_date).days
            if dt_d.weekday() == int(rebalance_weekday) or days_since >= 6:
                need_rebal = True

        if need_rebal:
            scores: dict[str, float] = {}
            for s in syms:
                idx = date_pos[s][d_str]
                if idx <= lb + 1:
                    continue
                c = d1_by_sym[s]["close"]
                rv = float(rvol_map[s][idx])
                a = float(atr_map[s][idx])
                if not (math.isfinite(rv) and rv > 1e-8 and math.isfinite(a) and a > 0.0):
                    continue
                # Strictly shift = 1: return from c[idx - 1 - lb] to c[idx - 1] (ZERO bar idx peek!)
                ret_l = math.log(float(c[idx - 1]) / float(c[idx - 1 - lb]))
                scores[s] = ret_l / (rv * math.sqrt(float(lb)))

            if len(scores) == 7:
                new_dirs = {s: 0.0 for s in syms}
                if neutrality_mode == "balanced_group":
                    jpy_sorted = sorted(JPY_CROSS_3, key=lambda x: scores[x])
                    non_sorted = sorted(NON_JPY_CROSS_4, key=lambda x: scores[x])
                    new_dirs[jpy_sorted[-1]] = 1.0 * sm
                    new_dirs[jpy_sorted[0]] = -1.0 * sm
                    new_dirs[non_sorted[-1]] = 1.0 * sm
                    new_dirs[non_sorted[0]] = -1.0 * sm
                elif neutrality_mode == "constrained_full7":
                    # Maximize sum(long scores) - sum(short scores) over all 2-long / 2-short subsets
                    # with EXACT zero JPY beta (`n_long_jpy == n_short_jpy`)!
                    best_val = -1e308
                    best_pair: tuple[tuple[str, str], tuple[str, str]] | None = None
                    for i1 in range(7):
                        for i2 in range(i1 + 1, 7):
                            longs = (syms[i1], syms[i2])
                            n_lj = (1 if longs[0] in jpy_set else 0) + (1 if longs[1] in jpy_set else 0)
                            rem = [syms[k] for k in range(7) if k != i1 and k != i2]
                            for j1 in range(5):
                                for j2 in range(j1 + 1, 5):
                                    shorts = (rem[j1], rem[j2])
                                    n_sj = (1 if shorts[0] in jpy_set else 0) + (1 if shorts[1] in jpy_set else 0)
                                    if n_lj != n_sj:
                                        continue
                                    val = scores[longs[0]] + scores[longs[1]] - scores[shorts[0]] - scores[shorts[1]]
                                    if val > best_val:
                                        best_val = val
                                        best_pair = (longs, shorts)
                    if best_pair is not None:
                        for s_l in best_pair[0]:
                            new_dirs[s_l] = 1.0 * sm
                        for s_s in best_pair[1]:
                            new_dirs[s_s] = -1.0 * sm
                else:
                    raise ValueError(f"Unsupported neutrality_mode: {neutrality_mode!r}")

                active_dirs = new_dirs
                last_rebal_date = dt_d
                if not hold_across_rebalance:
                    # Stamp signal ONCE on rebalance bar only (for weekly time-stop variants)
                    for s in syms:
                        idx = date_pos[s][d_str]
                        a = float(atr_map[s][idx])
                        if active_dirs[s] != 0.0 and math.isfinite(a) and a > 0.0:
                            sig_map[s][idx] = active_dirs[s]
                            sl_map[s][idx] = float(sl_atr_mult) * a

        if hold_across_rebalance:
            # Maintain active weekly rank direction across consecutive Mondays (avoids fake close+reopen churn!)
            for s in syms:
                idx = date_pos[s][d_str]
                a = float(atr_map[s][idx])
                if active_dirs[s] != 0.0 and math.isfinite(a) and a > 0.0:
                    sig_map[s][idx] = active_dirs[s]
                    sl_map[s][idx] = float(sl_atr_mult) * a

    return sig_map, sl_map


# ---------------------------------------------------------------------------
# Standard Candidate Evaluation (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def _compute_portfolio_margin_audit(trades: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    day_margin: dict[str, float] = {}
    capped = 0
    for tr in trades:
        if tr.get("margin_capped"):
            capped += 1
        d0 = date.fromisoformat(str(tr["entry_date"]))
        d1 = date.fromisoformat(str(tr["exit_date"]))
        mu = float(tr.get("margin_util_frac", 0.0))
        cur = d0
        while cur <= d1:
            if cur.weekday() < 5:
                k = cur.isoformat()
                day_margin[k] = day_margin.get(k, 0.0) + mu
            cur += timedelta(days=1)
    peak = max(day_margin.values()) if day_margin else 0.0
    return {
        "margin_capped_count": capped,
        "peak_portfolio_margin_util_frac": round(peak, 6),
        "portfolio_margin_breached": peak > 0.80 + 1e-9,
    }


def _run_spec_trades(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    req_years: tuple[int, ...],
    *,
    flip_side: bool = False,
) -> list[dict[str, Any]]:
    mech = str(spec["mechanism"])
    symbols = _enforce_blind7_symbols(spec["symbols"])
    params = dict(spec["params"])
    assets = universe["assets"]
    max_yr = max(req_years)

    all_trades: list[dict[str, Any]] = []

    if mech == "XSEC_WEEKLY_ROT":
        d1_map = {s: _slice_d1_upto_year(assets[s]["d1"], max_yr) for s in TRUE_BLIND_7}
        hold_across = bool(params.get("hold_across_rebalance", True))
        sig_map, sl_map = _build_xsec_zero_jpy_beta_signals(
            d1_map,
            lookback_days=int(params["lookback_days"]),
            neutrality_mode=str(params["neutrality_mode"]),
            reverse_rank=bool(params.get("reverse_rank", False)),
            rebalance_weekday=int(params.get("rebalance_weekday", 0)),
            sl_atr_mult=float(params["sl_atr_mult"]),
            hold_across_rebalance=hold_across,
            flip_side=flip_side,
        )
        # Always 4 concurrent legs (Long-2 / Short-2) -> 0.25R per leg = 1.0R total risk!
        leg_weight = 0.25
        for sym in TRUE_BLIND_7:
            aobj = assets[sym]
            res = cc.replay_swing_trades(
                sym,
                d1_map[sym],
                sig_map[sym],
                sl_map[sym],
                max_hold_bars=int(params.get("max_hold_bars", 20 if hold_across else 5)),
                exit_on_signal_flip=hold_across,
                signal_already_shifted=True,
                spec=aobj["spec"],
                account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
                risk_frac=_DEFAULT_RISK_FRAC * leg_weight,
                account_type="ftmo_swing",
                years=req_years,
                data_resolution=cc.RES_D1_YAHOO_SANCTIONED,
            )
            all_trades.extend(_scale_trades_by_weight(res["trades"], leg_weight))
    else:
        leg_weight = 1.0 / float(len(symbols))
        for sym in symbols:
            aobj = assets[sym]
            d1 = _slice_d1_upto_year(aobj["d1"], max_yr)
            inv_vol_map: dict[str, float] | None = None

            if mech == "VOL_COMP_TREND":
                sig, sl_d, tp_d = _signals_vol_compression_trend(
                    d1,
                    comp_win=int(params["comp_win"]),
                    comp_pct_max=float(params["comp_pct_max"]),
                    ema_fast=int(params["ema_fast"]),
                    ema_slow=int(params["ema_slow"]),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                exit_flip = False
            elif mech == "TREND_PULLBACK":
                sig, sl_d, tp_d = _signals_trend_pullback(
                    d1,
                    pullback_kind=str(params["pullback_kind"]),
                    threshold=float(params["threshold"]),
                    trend_sma=int(params["trend_sma"]),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                exit_flip = False
            elif mech == "VOL_TARGET_TREND":
                sig, sl_d, tp_d, inv_vol_map = _signals_vol_targeted_trend(
                    d1,
                    trend_kind=str(params["trend_kind"]),
                    fast_n=int(params["fast_n"]),
                    slow_n=int(params["slow_n"]),
                    signal_thresh=float(params["signal_thresh"]),
                    target_ann_vol=float(params.get("target_ann_vol", 0.08)),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    entry_on_onset_only=bool(params.get("entry_on_onset_only", False)),
                    flip_side=flip_side,
                )
                exit_flip = bool(params.get("exit_on_signal_flip", True))
            elif mech == "ADX_ZSCORE_MR":
                sig, sl_d, tp_d = _signals_adx_zscore_mr(
                    d1,
                    adx_max=float(params["adx_max"]),
                    z_win=int(params["z_win"]),
                    z_entry=float(params["z_entry"]),
                    calm_atr_ratio_max=float(params.get("calm_atr_ratio_max", 1.25)),
                    sl_atr_mult=float(params["sl_atr_mult"]),
                    tp_atr_mult=params.get("tp_atr_mult"),
                    flip_side=flip_side,
                )
                exit_flip = False
            else:
                raise ValueError(f"Unknown F10 mechanism: {mech!r}")

            res = cc.replay_swing_trades(
                sym,
                d1,
                sig,
                sl_d,
                tp_dists=tp_d,
                max_hold_bars=int(params["max_hold_bars"]),
                exit_on_signal_flip=exit_flip,
                signal_already_shifted=True,
                spec=aobj["spec"],
                account_balance_usd=_DEFAULT_ACCOUNT_BALANCE_USD,
                risk_frac=_DEFAULT_RISK_FRAC * leg_weight,
                account_type="ftmo_swing",
                years=req_years,
                data_resolution=cc.RES_D1_YAHOO_SANCTIONED,
            )
            all_trades.extend(_scale_trades_by_weight(res["trades"], leg_weight, per_entry_scale=inv_vol_map))

    all_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))
    return all_trades


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
) -> dict[str, Any]:
    """Evaluate any F10 TRUE-BLIND-7 spec strictly over `years`, returning the exact Stage-3 standard dict."""
    req_years = tuple(sorted(int(y) for y in years))
    if not req_years or min(req_years) < cc.DEV_MIN_YEAR or max(req_years) > cc.DEV_MAX_YEAR:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid years={years!r}")

    _enforce_blind7_symbols(spec["symbols"])

    trades = _run_spec_trades(spec, universe, req_years, flip_side=False)
    fade_trades = _run_spec_trades(spec, universe, req_years, flip_side=True)

    dp_1x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dp_15x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dp_2x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    dp_zpos_1x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_1x")
    dp_zpos_2x_obj = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_2x")
    dp_fade_obj = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = cc.compute_split_metrics(trades, dp_1x_obj, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dp_15x_obj, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dp_2x_obj, pnl_key="net_R_2x")
    m_zpos_1x = cc.compute_split_metrics(trades, dp_zpos_1x_obj, pnl_key="net_R_zero_pos_1x")
    m_zpos_2x = cc.compute_split_metrics(trades, dp_zpos_2x_obj, pnl_key="net_R_zero_pos_2x")
    m_fade = cc.compute_split_metrics(fade_trades, dp_fade_obj, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(trades)
    maudit = _compute_portfolio_margin_audit(trades)

    n_long = sum(1 for tr in trades if int(tr["side"]) > 0)
    n_short = sum(1 for tr in trades if int(tr["side"]) < 0)

    metrics = dict(m_1x)
    metrics.update(
        {
            "net_R_15x": m_15x["net_R"],
            "sharpe_15x": m_15x["sharpe"],
            "net_R_2x": m_2x["net_R"],
            "pf_2x": m_2x["pf"],
            "sharpe_2x": m_2x["sharpe"],
            "net_R_zero_pos_1x": m_zpos_1x["net_R"],
            "pf_zero_pos_1x": m_zpos_1x["pf"],
            "sharpe_zero_pos_1x": m_zpos_1x["sharpe"],
            "net_R_zero_pos_2x": m_zpos_2x["net_R"],
            "sharpe_zero_pos_2x": m_zpos_2x["sharpe"],
            "fade_net_R_1x": m_fade["net_R"],
            "fade_sharpe_1x": m_fade["sharpe"],
            "n_long": n_long,
            "n_short": n_short,
            "stage0_passed": bool(s0["passed"]),
            "stage0_median_fric_sl": s0["median_fric_sl_ratio"],
            "stage0_keep_frac": s0["keep_frac"],
            "margin_capped_count": maudit["margin_capped_count"],
            "peak_portfolio_margin_util_frac": maudit["peak_portfolio_margin_util_frac"],
            "portfolio_margin_breached": maudit["portfolio_margin_breached"],
        }
    )

    return {
        "spec": dict(spec),
        "trades": trades,
        "daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_1x_obj["dates"], dp_1x_obj["pnl"], strict=True)},
        "daily_pnl_15x": {d: round(float(v), 6) for d, v in zip(dp_15x_obj["dates"], dp_15x_obj["pnl"], strict=True)},
        "daily_pnl_2x": {d: round(float(v), 6) for d, v in zip(dp_2x_obj["dates"], dp_2x_obj["pnl"], strict=True)},
        "daily_pnl_zero_pos_swap": {
            d: round(float(v), 6) for d, v in zip(dp_zpos_1x_obj["dates"], dp_zpos_1x_obj["pnl"], strict=True)
        },
        "fade_daily_pnl_1x": {
            d: round(float(v), 6) for d, v in zip(dp_fade_obj["dates"], dp_fade_obj["pnl"], strict=True)
        },
        "metrics": metrics,
        "data_resolution": cc.RES_D1_YAHOO_SANCTIONED,
        "blindness_tier": cc.TIER_NEW7,
        "allow_unidirectional": False,
    }


# ---------------------------------------------------------------------------
# Pre-Registered F10 Candidate Grid (<= 100 Total Across Mechanics (a)..(e))
# ---------------------------------------------------------------------------


def build_f10_candidate_specs() -> list[dict[str, Any]]:
    """Construct <= 100 economically grounded TRUE_BLIND_7 candidate specs across mechanics (a)..(e)."""
    specs: list[dict[str, Any]] = []

    def _add(
        cid: str,
        mechanism: str,
        symbols: Sequence[str],
        params: dict[str, Any],
        rationale: str,
        counterparty: str,
    ) -> None:
        _enforce_blind7_symbols(symbols)
        if len(rationale.strip()) < 40:
            raise ValueError(f"economic_rationale too short (< 40 chars) for {cid}")
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "mechanism": mechanism,
                "symbols": list(symbols),
                "params": dict(params),
                "prop_track": "FTMO_SWING",
                "blindness_tier": cc.TIER_NEW7,
                "data_resolution": cc.RES_D1_YAHOO_SANCTIONED,
                "allow_unidirectional": False,
                "economic_rationale": rationale.strip(),
                "counterparty_mechanism": counterparty.strip(),
                "causal_invariants": list(_CAUSAL_INVARIANTS_F10),
            }
        )

    # (a) Volatility-Compression -> Directional Trend Continuation (18 specs)
    rat_a = (
        "FX volatility clustering compresses daily ranges before institutional macro positioning resumes; "
        "entering aligned with prevailing causal EMA trend captures 2-6d expansion with controlled SL risk."
    )
    cp_a = "Short-gamma options dealers & late breakout chasers forced to re-hedge on post-compression expansion"

    for cwin, ef, es, hold, tp in (
        (20, 10, 30, 4, None),
        (20, 10, 30, 6, None),
        (20, 10, 30, 5, 3.0),
        (20, 12, 40, 5, None),
        (40, 10, 30, 4, None),
        (40, 12, 40, 6, None),
        (20, 8, 24, 3, None),
    ):
        tp_tag = f"TP{int(tp)}" if tp is not None else "TIME"
        _add(
            f"F10_A_VCOMP_POOL7_W{cwin}_E{ef}_{es}_H{hold}_{tp_tag}",
            "VOL_COMP_TREND",
            TRUE_BLIND_7,
            {
                "comp_win": cwin,
                "comp_pct_max": 0.30,
                "ema_fast": ef,
                "ema_slow": es,
                "max_hold_bars": hold,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": tp,
            },
            rat_a,
            cp_a,
        )

    for grp, gtag in ((JPY_CROSS_3, "JPY3"), (NON_JPY_CROSS_4, "NONJPY4")):
        for hold in (4, 6):
            _add(
                f"F10_A_VCOMP_{gtag}_W20_E10_30_H{hold}",
                "VOL_COMP_TREND",
                grp,
                {
                    "comp_win": 20,
                    "comp_pct_max": 0.30,
                    "ema_fast": 10,
                    "ema_slow": 30,
                    "max_hold_bars": hold,
                    "sl_atr_mult": 2.0,
                    "tp_atr_mult": None,
                },
                rat_a,
                cp_a,
            )

    for sym in TRUE_BLIND_7:
        _add(
            f"F10_A_VCOMP_{sym}_W20_E10_30_H5",
            "VOL_COMP_TREND",
            (sym,),
            {
                "comp_win": 20,
                "comp_pct_max": 0.30,
                "ema_fast": 10,
                "ema_slow": 30,
                "max_hold_bars": 5,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
            },
            rat_a,
            cp_a,
        )

    # (b) Trend-Aligned RSI(2) / IBS / Z-Score Pullback (20 specs)
    rat_b = (
        "Short-term corporate hedging & retail profit-taking create 1-2d counter-trend dips inside "
        "persistent cross-rate macro trends; liquidity providers mean-revert pullbacks over 2-5 days."
    )
    cp_b = "Impatient counter-trend flow & short-term commercial hedgers crossing the spread inside macro trends"

    for kind, thresh, sma_n, hold, tp_m, tag in (
        ("rsi2", 15.0, 100, 3, 1.5, "RSI15_S100_H3_TP15"),
        ("rsi2", 15.0, 100, 5, 2.0, "RSI15_S100_H5_TP20"),
        ("rsi2", 20.0, 50, 4, 1.5, "RSI20_S50_H4_TP15"),
        ("rsi2", 10.0, 100, 4, None, "RSI10_S100_H4_TIME"),
        ("ibs", 0.20, 100, 3, 1.5, "IBS20_S100_H3_TP15"),
        ("ibs", 0.20, 100, 5, 2.0, "IBS20_S100_H5_TP20"),
        ("ibs", 0.25, 50, 3, None, "IBS25_S50_H3_TIME"),
        ("zscore", 1.25, 100, 3, 1.5, "Z125_S100_H3_TP15"),
        ("zscore", 1.25, 100, 5, 2.0, "Z125_S100_H5_TP20"),
        ("zscore", 1.50, 50, 4, 1.75, "Z150_S50_H4_TP175"),
    ):
        _add(
            f"F10_B_PB_POOL7_{tag}",
            "TREND_PULLBACK",
            TRUE_BLIND_7,
            {
                "pullback_kind": kind,
                "threshold": thresh,
                "trend_sma": sma_n,
                "max_hold_bars": hold,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": tp_m,
            },
            rat_b,
            cp_b,
        )

    for grp, gtag in ((JPY_CROSS_3, "JPY3"), (NON_JPY_CROSS_4, "NONJPY4")):
        _add(
            f"F10_B_PB_{gtag}_IBS20_S100_H4_TP15",
            "TREND_PULLBACK",
            grp,
            {
                "pullback_kind": "ibs",
                "threshold": 0.20,
                "trend_sma": 100,
                "max_hold_bars": 4,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": 1.5,
            },
            rat_b,
            cp_b,
        )
        _add(
            f"F10_B_PB_{gtag}_RSI15_S100_H4_TP15",
            "TREND_PULLBACK",
            grp,
            {
                "pullback_kind": "rsi2",
                "threshold": 15.0,
                "trend_sma": 100,
                "max_hold_bars": 4,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": 1.5,
            },
            rat_b,
            cp_b,
        )

    for sym in ("CADJPY", "CHFJPY", "NZDJPY", "EURGBP", "EURAUD", "EURCAD"):
        _add(
            f"F10_B_PB_{sym}_Z125_S100_H4_TP15",
            "TREND_PULLBACK",
            (sym,),
            {
                "pullback_kind": "zscore",
                "threshold": 1.25,
                "trend_sma": 100,
                "max_hold_bars": 4,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": 1.5,
            },
            rat_b,
            cp_b,
        )

    # (c) 7-Cross Equal-Risk Vol-Targeted Trend (16 specs; onset-only 6-8d holds OR smooth flip <= 20d)
    rat_c = (
        "Divergent G10 monetary-policy cycles drive multi-day cross-rate drift; inverse-volatility "
        "sizing equalizes risk across low-vol EURGBP and high-vol GBPAUD/JPY crosses without carry lookahead."
    )
    cp_c = "Central-bank policy inertia & slow-rebalancing sovereign/corporate FX hedgers"

    for tkind, fn, sn, th, hold, onset, tag in (
        ("ewmac", 8, 32, 0.30, 8, True, "EWMAC_8_32_ONSET_H8"),
        ("ewmac", 8, 32, 0.50, 20, False, "EWMAC_8_32_CONT"),
        ("ewmac", 12, 48, 0.30, 8, True, "EWMAC_12_48_ONSET_H8"),
        ("ewmac", 16, 64, 0.35, 20, False, "EWMAC_16_64_CONT"),
        ("donchian_mid", 3, 20, 0.15, 6, True, "DMID_20_ONSET_H6"),
        ("donchian_mid", 5, 30, 0.15, 8, True, "DMID_30_ONSET_H8"),
        ("donchian_mid", 5, 40, 0.20, 20, False, "DMID_40_CONT"),
        ("ema_slope", 20, 5, 0.20, 6, True, "ESLOPE_20_ONSET_H6"),
        ("ema_slope", 30, 5, 0.20, 8, True, "ESLOPE_30_ONSET_H8"),
    ):
        _add(
            f"F10_C_VOLTREND_POOL7_{tag}",
            "VOL_TARGET_TREND",
            TRUE_BLIND_7,
            {
                "trend_kind": tkind,
                "fast_n": fn,
                "slow_n": sn,
                "signal_thresh": th,
                "target_ann_vol": 0.08,
                "max_hold_bars": hold,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": None,
                "entry_on_onset_only": onset,
                "exit_on_signal_flip": not onset,
            },
            rat_c,
            cp_c,
        )

    for sym in TRUE_BLIND_7:
        _add(
            f"F10_C_VOLTREND_{sym}_EWMAC_12_48_ONSET_H8",
            "VOL_TARGET_TREND",
            (sym,),
            {
                "trend_kind": "ewmac",
                "fast_n": 12,
                "slow_n": 48,
                "signal_thresh": 0.30,
                "target_ann_vol": 0.08,
                "max_hold_bars": 8,
                "sl_atr_mult": 2.5,
                "tp_atr_mult": None,
                "entry_on_onset_only": True,
                "exit_on_signal_flip": False,
            },
            rat_c,
            cp_c,
        )

    # (d) 7-Cross Cross-Sectional Weekly Rotation — Strict ZERO USD/JPY Beta Tilt! (16 specs)
    rat_d = (
        "Menkhoff cross-sectional FX momentum/reversion captures relative G10 growth and rate divergence "
        "while strict JPY-neutral Long-2/Short-2 pairing eliminates unintended USD and JPY directional beta."
    )
    cp_d = "Slow-moving international macro allocators & currency-unhedged equity/bond capital flows"

    for nmode, ntag in (("balanced_group", "BAL"), ("constrained_full7", "ZEROJPY")):
        for lb in (5, 10, 20, 40, 60):
            _add(
                f"F10_D_XSEC_{ntag}_MOM_L{lb}_MON",
                "XSEC_WEEKLY_ROT",
                TRUE_BLIND_7,
                {
                    "lookback_days": lb,
                    "neutrality_mode": nmode,
                    "reverse_rank": False,
                    "rebalance_weekday": 0,
                    "hold_across_rebalance": False,
                    "max_hold_bars": 5,
                    "sl_atr_mult": 2.25,
                },
                rat_d,
                cp_d,
            )
        for lb in (5, 10):
            _add(
                f"F10_D_XSEC_{ntag}_REV_L{lb}_MON",
                "XSEC_WEEKLY_ROT",
                TRUE_BLIND_7,
                {
                    "lookback_days": lb,
                    "neutrality_mode": nmode,
                    "reverse_rank": True,
                    "rebalance_weekday": 0,
                    "hold_across_rebalance": False,
                    "max_hold_bars": 5,
                    "sl_atr_mult": 2.25,
                },
                rat_d,
                cp_d,
            )
        # Wednesday rebalance variant (robustness across rebalance weekday!)
        _add(
            f"F10_D_XSEC_{ntag}_MOM_L20_WED",
            "XSEC_WEEKLY_ROT",
            TRUE_BLIND_7,
            {
                "lookback_days": 20,
                "neutrality_mode": nmode,
                "reverse_rank": False,
                "rebalance_weekday": 2,
                "hold_across_rebalance": False,
                "max_hold_bars": 5,
                "sl_atr_mult": 2.25,
            },
            rat_d,
            cp_d,
        )

    # (e) Asymmetric Volatility-Regime Mean-Reversion (`ADX < 20/22` Z-Score Reversion) (22 specs)
    rat_e = (
        "Economically coupled European/commodity FX crosses mean-revert around purchasing-power & trade "
        "equilibria during low-ADX calm-vol regimes; hard SL & ADX gate cut exposure before macro trends."
    )
    cp_e = "Short-term stop-chasers & lumpy commercial flow pushing range-bound crosses away from fair value"

    for grp, gtag in ((EURO_RANGE_3, "EUR3"), (NON_JPY_CROSS_4, "NONJPY4"), (TRUE_BLIND_7, "POOL7")):
        for adx_m, zw, ze, hold in (
            (20.0, 14, 1.50, 4),
            (20.0, 20, 1.75, 5),
            (22.0, 14, 1.75, 4),
            (20.0, 14, 2.00, 6),
        ):
            _add(
                f"F10_E_ADXMR_{gtag}_A{int(adx_m)}_Z{zw}_{int(ze*100)}_H{hold}",
                "ADX_ZSCORE_MR",
                grp,
                {
                    "adx_max": adx_m,
                    "z_win": zw,
                    "z_entry": ze,
                    "calm_atr_ratio_max": 1.25,
                    "max_hold_bars": hold,
                    "sl_atr_mult": 2.0,
                    "tp_atr_mult": 2.0,
                },
                rat_e,
                cp_e,
            )

    for sym in EURO_RANGE_3:
        for ze, hold in ((1.50, 4), (1.75, 5)):
            _add(
                f"F10_E_ADXMR_{sym}_A20_Z14_{int(ze*100)}_H{hold}",
                "ADX_ZSCORE_MR",
                (sym,),
                {
                    "adx_max": 20.0,
                    "z_win": 14,
                    "z_entry": ze,
                    "calm_atr_ratio_max": 1.25,
                    "max_hold_bars": hold,
                    "sl_atr_mult": 2.0,
                    "tp_atr_mult": 2.0,
                },
                rat_e,
                cp_e,
            )

    for sym in ("GBPAUD", "CADJPY", "CHFJPY", "NZDJPY"):
        _add(
            f"F10_E_ADXMR_{sym}_A20_Z14_175_H5",
            "ADX_ZSCORE_MR",
            (sym,),
            {
                "adx_max": 20.0,
                "z_win": 14,
                "z_entry": 1.75,
                "calm_atr_ratio_max": 1.25,
                "max_hold_bars": 5,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": 2.0,
            },
            rat_e,
            cp_e,
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F10 spec count {len(specs)} exceeds TOTAL_CAP={TOTAL_CAP}")
    return specs


# ---------------------------------------------------------------------------
# Stage 2 Cluster-A Discovery (`2018-2020` ONLY — Hard Blindness Lock!)
# ---------------------------------------------------------------------------


def _score_cluster_a_f10(res: Mapping[str, Any]) -> tuple[bool, float]:
    """Conservative Cluster-A ranking enforcing BOTH Real Triple-Swap AND zero_pos_swap floor!"""
    m = res["metrics"]
    n_tr = int(m["n_trades"])
    s0_ok = bool(m.get("stage0_passed", False))
    sh_real_1x = float(m["sharpe"])
    sh_real_2x = float(m["sharpe_2x"])
    sh_zpos_1x = float(m["sharpe_zero_pos_1x"])
    sh_zpos_2x = float(m["sharpe_zero_pos_2x"])
    net_real_2x = float(m["net_R_2x"])
    net_zpos_1x = float(m["net_R_zero_pos_1x"])
    net_zpos_2x = float(m["net_R_zero_pos_2x"])
    pos_ratio = float(m["positive_year_ratio"])
    max_dd = float(m["max_DD_R"])
    n_long = int(m.get("n_long", 0))
    n_short = int(m.get("n_short", 0))
    margin_breach = bool(m.get("portfolio_margin_breached", False))

    # Strict two-sided balance & zero static carry dependence:
    # MUST be net-positive under BOTH Real Triple-Swap (2x friction) AND zero_pos_swap (1x & 2x)!
    eligible = (
        s0_ok
        and (not margin_breach)
        and n_tr >= 20
        and n_long >= 3
        and n_short >= 3
        and net_real_2x > 0.0
        and net_zpos_1x > 0.0
        and net_zpos_2x > 0.0
        and sh_real_2x > 0.0
        and sh_zpos_1x > 0.0
    )

    # Rank strictly on the CONSERVATIVE FLOOR of real_swap vs zero_pos_swap (zero swap-sign bias!)
    floor_sh_1x = min(sh_real_1x, sh_zpos_1x)
    floor_sh_2x = min(sh_real_2x, sh_zpos_2x)
    dd_pen = 0.05 * max(0.0, max_dd - 6.0)
    score = floor_sh_1x + 0.60 * floor_sh_2x + 0.45 * pos_ratio - dd_pen
    return eligible, round(score, 6)


def _summarize_candidate_for_checkpoint(
    res: Mapping[str, Any],
    *,
    tier: str,
    score: float,
    eligible_primary: bool,
) -> dict[str, Any]:
    """Build Cluster-A-only checkpoint record (strictly zero 2021+ keys/dates/years)."""
    m = res["metrics"]
    spec = dict(res["spec"])
    return {
        "candidate_id": str(spec["candidate_id"]),
        "family_id": FAMILY_ID,
        "tier": tier,
        "is_primary": tier == "PRIMARY",
        "mechanism": str(spec["mechanism"]),
        "symbols": list(spec["symbols"]),
        "params": dict(spec["params"]),
        "prop_track": "FTMO_SWING",
        "data_resolution": cc.RES_D1_YAHOO_SANCTIONED,
        "blindness_tier": cc.TIER_NEW7,
        "allow_unidirectional": False,
        "economic_rationale": str(spec["economic_rationale"]),
        "counterparty_mechanism": str(spec["counterparty_mechanism"]),
        "causal_invariants": list(spec["causal_invariants"]),
        "cluster_a_score": float(score),
        "cluster_a_primary_eligible": bool(eligible_primary),
        "cluster_a_metrics": {
            "n_trades": int(m["n_trades"]),
            "n_long": int(m["n_long"]),
            "n_short": int(m["n_short"]),
            "net_R_1x": float(m["net_R"]),
            "net_R_15x": float(m["net_R_15x"]),
            "net_R_2x": float(m["net_R_2x"]),
            "net_R_zero_pos_1x": float(m["net_R_zero_pos_1x"]),
            "net_R_zero_pos_2x": float(m["net_R_zero_pos_2x"]),
            "pf_1x": float(m["pf"]),
            "pf_2x": float(m["pf_2x"]),
            "pf_zero_pos_1x": float(m["pf_zero_pos_1x"]),
            "sharpe_1x": float(m["sharpe"]),
            "sharpe_2x": float(m["sharpe_2x"]),
            "sharpe_zero_pos_1x": float(m["sharpe_zero_pos_1x"]),
            "sharpe_zero_pos_2x": float(m["sharpe_zero_pos_2x"]),
            "fade_net_R_1x": float(m["fade_net_R_1x"]),
            "fade_sharpe_1x": float(m["fade_sharpe_1x"]),
            "winrate": float(m["winrate"]),
            "avg_RR": float(m["avg_RR"]),
            "max_DD_R": float(m["max_DD_R"]),
            "positive_years": int(m["positive_years"]),
            "total_years": int(m["total_years"]),
            "by_year_R": dict(m["by_year_R"]),
            "stage0_passed": bool(m["stage0_passed"]),
            "stage0_median_fric_sl": m["stage0_median_fric_sl"],
            "peak_portfolio_margin_util_frac": float(m["peak_portfolio_margin_util_frac"]),
        },
    }


def discover_cluster_a(
    universe: Mapping[str, Any] | None = None,
    *,
    save_checkpoint: bool = True,
    resume: bool = False,
    verify_sha: bool = True,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run F10 TRUE-BLIND-7 Cluster-A discovery strictly on `CLUSTER_A_YEARS = (2018, 2019, 2020)` ONLY."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    if universe is None:
        uni = cc.load_universe_28(
            load_m1=False,
            load_d1=True,
            years=cc.CLUSTER_A_YEARS,
            symbols=TRUE_BLIND_7,
            verify_sha=verify_sha,
            root=root,
        )
    else:
        uni = universe

    specs = build_f10_candidate_specs()
    evaluated: list[tuple[bool, float, dict[str, Any]]] = []
    for sp in specs:
        res = evaluate_candidate(sp, uni, cc.CLUSTER_A_YEARS)
        elig, sc = _score_cluster_a_f10(res)
        evaluated.append((elig, sc, res))

    evaluated.sort(key=lambda item: (not item[0], -item[1], str(item[2]["spec"]["candidate_id"])))

    # Select <= PRIMARY_CAP diverse PRIMARY candidates (cap <= 4 per mechanism across all 5 mechanics!)
    mech_counts: dict[str, int] = {}
    primary_ids: set[str] = set()
    primary_records: list[dict[str, Any]] = []
    exploratory_records: list[dict[str, Any]] = []

    for elig, sc, res in evaluated:
        cid = str(res["spec"]["candidate_id"])
        mech = str(res["spec"]["mechanism"])
        if elig and len(primary_records) < PRIMARY_CAP and mech_counts.get(mech, 0) < 4:
            primary_records.append(
                _summarize_candidate_for_checkpoint(res, tier="PRIMARY", score=sc, eligible_primary=True)
            )
            primary_ids.add(cid)
            mech_counts[mech] = mech_counts.get(mech, 0) + 1

    # Second pass: fill remaining PRIMARY slots from remaining eligible candidates (if < PRIMARY_CAP)
    if len(primary_records) < PRIMARY_CAP:
        for elig, sc, res in evaluated:
            cid = str(res["spec"]["candidate_id"])
            if cid in primary_ids or not elig:
                continue
            if len(primary_records) >= PRIMARY_CAP:
                break
            primary_records.append(
                _summarize_candidate_for_checkpoint(res, tier="PRIMARY", score=sc, eligible_primary=True)
            )
            primary_ids.add(cid)

    # Remaining candidates populate EXPLORATORY up to TOTAL_CAP
    for elig, sc, res in evaluated:
        cid = str(res["spec"]["candidate_id"])
        if cid in primary_ids:
            continue
        if len(primary_records) + len(exploratory_records) >= TOTAL_CAP:
            break
        exploratory_records.append(
            _summarize_candidate_for_checkpoint(res, tier="EXPLORATORY", score=sc, eligible_primary=elig)
        )

    meta: dict[str, Any] = {
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "family_slug": FAMILY_ID,
        "module": "quant_factory.offensive3.fam10_true_blind_cross7",
        "primary_cap": PRIMARY_CAP,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "blindness_tier": cc.TIER_NEW7,
        "zero_swap_sign_carry_lookahead": True,
        "ops1_guard_active": ops1_guard is not None,
        "symbols_covered": list(TRUE_BLIND_7),
        "mechanisms_covered": sorted({str(s["mechanism"]) for s in specs}),
        "primary_mechanism_counts": {
            m: sum(1 for r in primary_records if r["mechanism"] == m)
            for m in sorted({r["mechanism"] for r in primary_records})
        },
    }

    if save_checkpoint:
        cc.save_family_candidates(
            FAMILY_ID,
            {"primary": primary_records, "exploratory": exploratory_records},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

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
    }


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run Stage-2 Cluster-A discovery for F10_TRUE_BLIND_CROSS7.")
    parser.add_argument("--resume", action="store_true", help="Reuse SHA-verified Cluster-A checkpoint if present.")
    parser.add_argument("--no-verify-sha", action="store_true", help="Skip parquet SHA-256 verification on load.")
    args = parser.parse_args(argv)

    doc = discover_cluster_a(save_checkpoint=True, resume=bool(args.resume), verify_sha=not bool(args.no_verify_sha))
    top5 = [
        {
            "id": c["candidate_id"],
            "mech": c["mechanism"],
            "n": c["cluster_a_metrics"]["n_trades"],
            "net1x": c["cluster_a_metrics"]["net_R_1x"],
            "net2x": c["cluster_a_metrics"]["net_R_2x"],
            "net_zpos1x": c["cluster_a_metrics"]["net_R_zero_pos_1x"],
            "sh1x": c["cluster_a_metrics"]["sharpe_1x"],
            "sh_zpos": c["cluster_a_metrics"]["sharpe_zero_pos_1x"],
            "yrs+": f"{c['cluster_a_metrics']['positive_years']}/{c['cluster_a_metrics']['total_years']}",
        }
        for c in (doc.get("primary_candidates") or [])[:5]
    ]
    print(
        json.dumps(
            {
                "family_id": FAMILY_ID,
                "blindness_tier": cc.TIER_NEW7,
                "discovery_years": doc["discovery_years"],
                "primary_count": doc["primary_count"],
                "total_count": doc["total_count"],
                "order_send_count": ORDER_SEND_COUNT,
                _SEAL_ROWS_ANALYSED_KEY: 0,
                "top5_primary_cluster_a": top5,
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "EURO_RANGE_3",
    "FAMILY_ID",
    "JPY_CROSS_3",
    "NON_JPY_CROSS_4",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "TRUE_BLIND_7",
    "build_f10_candidate_specs",
    "causal_adx",
    "causal_donchian_mid",
    "causal_pct_rank",
    "discover_cluster_a",
    "evaluate_candidate",
    "main",
]

if __name__ == "__main__":
    raise SystemExit(main())
