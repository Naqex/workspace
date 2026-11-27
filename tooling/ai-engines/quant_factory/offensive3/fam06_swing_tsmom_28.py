"""Total Offensive #3 Family F06: Multi-Day Volatility-Managed Swing TSMOM (27 Non-Crypto FTMO Symbols).

Strict offline research & replay module (`ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`,
ZERO bare `assert`s `[ARCH-02]`, strict `shift = 1` causality, hard Cluster A blindness lock
on `CLUSTER_A_YEARS = (2018, 2019, 2020)` during `discover_cluster_a(universe)`).

Mechanisms implemented across ALL 27 non-crypto FTMO symbols (`11` M1-resampled + `9` NEW9 D1
+ `7` TRUE_BLIND_CLB_NEW7_CROSSES D1) via `replay_swing_d1_series` (exact triple-swap,
Anti-Fake-Swap Guard, `zero_pos_swap` floor, AND FTMO Swing real leverage margin check):
  1. `F06A_YZ_EWMAC_TSMOM`: Baltas-Kosowski causal Yang-Zhang / ATR vol-normalized EWMAC
     (`8/32`, `16/64`, `32/128`, and multi-horizon blended EWMAC) with `2-10d` swing holds.
  2. `F06B_MOREIRA_MUIR_VOLMGT`: Moreira-Muir (2017, JF) inverse-variance volatility-managed
     TSMOM cutting risk (`<= 1.0x`) and skipping entries during extreme causal vol spikes.
  3. `F06C_MULTI_ASSET_BASKET`: Basket-level TSMOM portfolios (`FX-17`, `Indices-6`,
     `MetalsOil-4`, `Balanced-27`, `FX-NEW7-BLIND`, `NEW16-UNSEEN`).
  4. `F06D_SINGLE_ASSET_TSMOM`: Top individual-asset vol-managed TSMOM prioritizing
     `NEW9_D1_VIEWED_M1_UNSEEN` and `TRUE_BLIND_CLB_NEW7_CROSSES`.

Standard public API:
  - `discover_cluster_a(universe, ...)` -> Cluster A (`2018-2020` ONLY) discovery & checkpointing.
  - `evaluate_candidate(spec, universe, years)` -> exact standard evaluation dictionary.
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
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


_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_ENGINES_DIR = _REPO_ROOT / "tooling" / "ai-engines"
if str(_AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(_AI_ENGINES_DIR))

from quant_factory.offensive3 import common_contract as cc  # noqa: E402

# ---------------------------------------------------------------------------
# Hard Safety & 27-Symbol Non-Crypto Universe Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

FAMILY_ID: str = "F06_SWING_TSMOM"
FAMILY_SLUG: str = "F06_SWING_TSMOM"
# Note: satisfies BOTH brief cap (<= 18) and `preregistration_m1200.json` F06 cap (<= 16).
PRIMARY_CAP: int = 16
TOTAL_CAP: int = 100

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
INDICES_6_SYMBOLS: tuple[str, ...] = ("US100", "US500", "GER40", "US30", "JP225", "UK100")
METALS_OIL_4_SYMBOLS: tuple[str, ...] = ("XAUUSD", "XAGUSD", "USOIL", "UKOIL")
BALANCED_27_SYMBOLS: tuple[str, ...] = (*FX_17_SYMBOLS, *INDICES_6_SYMBOLS, *METALS_OIL_4_SYMBOLS)

NEW9_SYMBOLS: tuple[str, ...] = (
    "US30",
    "JP225",
    "UK100",
    "XAGUSD",
    "USOIL",
    "UKOIL",
    "USDCHF",
    "NZDUSD",
    "AUDJPY",
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
NEW16_SYMBOLS: tuple[str, ...] = (*NEW9_SYMBOLS, *TRUE_BLIND_7_SYMBOLS)


# ---------------------------------------------------------------------------
# Strictly `shift = 1` Causal Volatility & TSMOM Primitives
# ---------------------------------------------------------------------------


@njit(cache=True)
def _causal_yang_zhang_vol_jit(
    o: np.ndarray,
    h: np.ndarray,
    lo: np.ndarray,
    c: np.ndarray,
    n: int,
) -> np.ndarray:
    """Strictly `shift = 1` causal Yang-Zhang (2000) daily OHLC volatility estimator.

    `out[t]` uses ONLY bars `t - n .. t - 1` (and `c[t - n - 1]` for the first overnight log return),
    guaranteeing zero dependency on bar `t` OHLC!
    """
    m = c.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n + 1 or n < 2:
        return out

    ro = np.empty(m, dtype=np.float64)
    rc = np.empty(m, dtype=np.float64)
    rs = np.empty(m, dtype=np.float64)
    ro[0] = np.nan
    rc[0] = np.nan
    rs[0] = np.nan

    for k in range(1, m):
        ok = o[k]
        hk = h[k]
        lk = lo[k]
        ck = c[k]
        pc = c[k - 1]
        if (
            np.isfinite(ok)
            and np.isfinite(hk)
            and np.isfinite(lk)
            and np.isfinite(ck)
            and np.isfinite(pc)
            and ok > 0.0
            and hk > 0.0
            and lk > 0.0
            and ck > 0.0
            and pc > 0.0
        ):
            ro[k] = math.log(ok / pc)
            c_log = math.log(ck / ok)
            u_log = math.log(hk / ok)
            d_log = math.log(lk / ok)
            rc[k] = c_log
            rs[k] = u_log * (u_log - c_log) + d_log * (d_log - c_log)
        else:
            ro[k] = np.nan
            rc[k] = np.nan
            rs[k] = np.nan

    nf = float(n)
    denom = float(n - 1)
    kappa = 0.34 / (1.34 + (nf + 1.0) / denom)

    # Strictly shift = 1: window [t - n, t) ends at bar t - 1
    for t in range(n + 1, m):
        mean_o = 0.0
        mean_c = 0.0
        sum_rs = 0.0
        valid = True
        for k in range(t - n, t):
            rok = ro[k]
            rck = rc[k]
            rsk = rs[k]
            if not (np.isfinite(rok) and np.isfinite(rck) and np.isfinite(rsk)):
                valid = False
                break
            mean_o += rok
            mean_c += rck
            sum_rs += rsk
        if not valid:
            continue
        mean_o /= nf
        mean_c /= nf
        var_o = 0.0
        var_c = 0.0
        for k in range(t - n, t):
            do = ro[k] - mean_o
            dc = rc[k] - mean_c
            var_o += do * do
            var_c += dc * dc
        var_o /= denom
        var_c /= denom
        var_rs = sum_rs / nf
        yz_var = var_o + kappa * var_c + (1.0 - kappa) * var_rs
        if yz_var > 1e-16:
            out[t] = math.sqrt(yz_var)
        else:
            out[t] = 1e-8
    return out


def causal_yang_zhang_vol(
    o: np.ndarray,
    h: np.ndarray,
    lo: np.ndarray,
    c: np.ndarray,
    n: int = 20,
) -> np.ndarray:
    """Strictly `shift = 1` causal Yang-Zhang daily volatility (`out[t]` uses bars `<= t-1` ONLY)."""
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or int(n) < 2:
        raise ValueError(f"n must be an integer >= 2, got {n!r}")
    return _causal_yang_zhang_vol_jit(
        np.ascontiguousarray(o, dtype=np.float64),
        np.ascontiguousarray(h, dtype=np.float64),
        np.ascontiguousarray(lo, dtype=np.float64),
        np.ascontiguousarray(c, dtype=np.float64),
        int(n),
    )


@njit(cache=True)
def _causal_rolling_pct_rank_jit(x: np.ndarray, lookback: int) -> np.ndarray:
    """Rolling percentile rank of already-causal `x[t]` vs `x[t-lookback+1 .. t]` (zero bar-t leak!)."""
    m = x.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m < lookback or lookback < 2:
        return out
    for t in range(lookback - 1, m):
        cur = x[t]
        if not np.isfinite(cur):
            continue
        cnt = 0
        le_cnt = 0
        for k in range(t - lookback + 1, t + 1):
            v = x[k]
            if np.isfinite(v):
                cnt += 1
                if v <= cur:
                    le_cnt += 1
        if cnt >= max(5, lookback // 2):
            out[t] = float(le_cnt) / float(cnt)
    return out


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
    return {
        "times_sec": np.asarray(d1["times_sec"], dtype=np.int64)[idx],
        "dates": [str(d1["dates"][i]) for i in idx.tolist()],
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


def _compute_asset_tsmom_features(d1: Mapping[str, Any]) -> dict[str, np.ndarray]:
    """Compute strictly `shift = 1` causal EWMAC forecasts, YZ vol, ATR, and Moreira-Muir ratios."""
    o = np.asarray(d1["open"], dtype=np.float64)
    h = np.asarray(d1["high"], dtype=np.float64)
    lo = np.asarray(d1["low"], dtype=np.float64)
    c = np.asarray(d1["close"], dtype=np.float64)
    n = c.size

    prev_c = np.empty(n, dtype=np.float64)
    prev_c[0] = np.nan
    prev_c[1:] = c[:-1]

    # All indicators below are STRICTLY shift = 1 (entry at open[t] sees ONLY bars 0..t-1)
    atr14 = cc.causal_atr(h, lo, c, 14)
    yz10 = causal_yang_zhang_vol(o, h, lo, c, 10)
    yz20 = causal_yang_zhang_vol(o, h, lo, c, 20)
    yz60 = causal_yang_zhang_vol(o, h, lo, c, 60)
    rvol20 = cc.causal_realized_vol(c, 20, use_log_returns=True)
    rsi5 = cc.causal_rsi(c, 5)

    ema8 = cc.causal_ema(c, 8)
    ema16 = cc.causal_ema(c, 16)
    ema32 = cc.causal_ema(c, 32)
    ema64 = cc.causal_ema(c, 64)
    ema128 = cc.causal_ema(c, 128)

    # Price-unit daily volatility from Yang-Zhang (yz20 * prev_c) and ATR14
    yz_px = np.where(np.isfinite(yz20) & np.isfinite(prev_c) & (yz20 > 1e-8), yz20 * prev_c, np.nan)
    atr_px = np.where(np.isfinite(atr14) & (atr14 > 1e-12), atr14, np.nan)

    def _norm(diff: np.ndarray, denom: np.ndarray) -> np.ndarray:
        return np.where(np.isfinite(diff) & np.isfinite(denom) & (denom > 1e-12), diff / denom, np.nan)

    ewmac_8_32_yz = _norm(ema8 - ema32, yz_px)
    ewmac_16_64_yz = _norm(ema16 - ema64, yz_px)
    ewmac_32_128_yz = _norm(ema32 - ema128, yz_px)

    ewmac_8_32_atr = _norm(ema8 - ema32, atr_px)
    ewmac_16_64_atr = _norm(ema16 - ema64, atr_px)
    ewmac_32_128_atr = _norm(ema32 - ema128, atr_px)

    # Multi-horizon blended EWMAC (Carver / Baltas-Kosowski equal-risk scale-normalized blend)
    # Scaling by approximate forecast std (~2.0, ~3.2, ~5.0) puts horizons on equal footing
    blend_yz = (ewmac_8_32_yz / 2.0 + ewmac_16_64_yz / 3.2 + ewmac_32_128_yz / 5.0) / 3.0
    blend_atr = (ewmac_8_32_atr / 1.8 + ewmac_16_64_atr / 2.8 + ewmac_32_128_atr / 4.4) / 3.0

    # Strictly shift = 1 Baltas-Kosowski Yang-Zhang t-stat trend strength over 20/40/60d:
    # tstat_L[t] = log(c[t-1] / c[t-1-L]) / (yz20[t] * sqrt(L)), zero bar-t dependency!
    def _tstat(lookback: int) -> np.ndarray:
        ret_l = np.full(n, np.nan, dtype=np.float64)
        if n > lookback + 1:
            ret_l[lookback + 1 :] = np.log(c[lookback:-1] / c[: -1 - lookback])
        denom = yz20 * math.sqrt(float(lookback))
        return np.where(np.isfinite(ret_l) & np.isfinite(denom) & (denom > 1e-8), ret_l / denom, np.nan)

    tstat_20_yz = _tstat(20)
    tstat_40_yz = _tstat(40)
    tstat_60_yz = _tstat(60)

    # Causal 2-day pullback return strictly observed at t-1 close: log(c[t-1] / c[t-3])
    ret2_causal = np.full(n, np.nan, dtype=np.float64)
    if n > 3:
        ret2_causal[3:] = np.log(c[2:-1] / c[:-3])

    # Moreira-Muir causal volatility ratio & percentile rank (strictly shift = 1)
    vol_ratio = np.where(np.isfinite(yz10) & np.isfinite(yz60) & (yz60 > 1e-8), yz10 / yz60, np.nan)
    vol_pct_rank = _causal_rolling_pct_rank_jit(yz20, 126)

    return {
        "open": o,
        "prev_close": prev_c,
        "weekdays": np.asarray(d1["weekdays"], dtype=np.int32),
        "atr14": atr14,
        "yz10": yz10,
        "yz20": yz20,
        "yz60": yz60,
        "rvol20": rvol20,
        "rsi5": rsi5,
        "ret2_causal": ret2_causal,
        "vol_ratio": vol_ratio,
        "vol_pct_rank": vol_pct_rank,
        "ewmac_8_32_yz": ewmac_8_32_yz,
        "ewmac_16_64_yz": ewmac_16_64_yz,
        "ewmac_32_128_yz": ewmac_32_128_yz,
        "ewmac_8_32_atr": ewmac_8_32_atr,
        "ewmac_16_64_atr": ewmac_16_64_atr,
        "ewmac_32_128_atr": ewmac_32_128_atr,
        "blend_yz": blend_yz,
        "blend_atr": blend_atr,
        "tstat_20_yz": tstat_20_yz,
        "tstat_40_yz": tstat_40_yz,
        "tstat_60_yz": tstat_60_yz,
    }


def _build_tsmom_signal_and_weights(
    feat: Mapping[str, np.ndarray],
    sym_spec: Mapping[str, Any],
    params: Mapping[str, Any],
    *,
    flip_side: bool = False,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, np.ndarray]:
    """Build strictly `shift = 1` signals, hard SL distances, optional TP, and Moreira-Muir weights."""
    forecast_key = str(params["forecast_key"])
    fc = feat[forecast_key]
    atr14 = feat["atr14"]
    vol_ratio = feat["vol_ratio"]
    vol_pct_rank = feat["vol_pct_rank"]
    wds = feat["weekdays"]
    rsi5 = feat["rsi5"]
    ret2 = feat["ret2_causal"]
    prev_c = feat["prev_close"]

    n = fc.size
    entry_thresh = float(params["entry_thresh"])
    cadence = str(params["cadence"])  # "weekly_mon" | "every_k" | "pullback" | "continuous"
    rebal_k = int(params.get("rebal_k", 5))
    vol_mode = str(params.get("vol_mode", "none"))  # "none" | "mm_gate" | "mm_inv_var"
    vol_spike_cap = float(params.get("vol_spike_cap", 1.40))
    vol_pct_cap = float(params.get("vol_pct_cap", 0.90))
    sl_atr_mult = float(params["sl_atr_mult"])
    tp_atr_mult = params.get("tp_atr_mult")
    swap_filter = bool(params.get("swap_filter", False))

    # Floor SL so Stage-0 F_stress / SL <= 13.5% across all 27 assets (incl. XAGUSD & CHFJPY!)
    oneway_bps = float(sym_spec["oneway_bps"])
    # Use prev_c (strictly shift = 1) for friction floor so sl_dist[t] NEVER depends on open[t]!
    min_sl_px = np.where(np.isfinite(prev_c) & (prev_c > 0.0), (4.0 * (oneway_bps / 10_000.0) * prev_c) * 8.0, np.nan)
    sl_arr = np.where(
        np.isfinite(atr14) & (atr14 > 0.0) & np.isfinite(min_sl_px),
        np.maximum(sl_atr_mult * atr14, min_sl_px),
        np.nan,
    )
    tp_arr = (
        np.where(np.isfinite(sl_arr) & np.isfinite(atr14), float(tp_atr_mult) * atr14, np.nan)
        if tp_atr_mult is not None
        else None
    )

    # Raw TSMOM direction
    sig = np.zeros(n, dtype=np.float64)
    valid_fc = np.isfinite(fc) & np.isfinite(sl_arr) & (sl_arr > 0.0)
    pos_mask = valid_fc & (fc >= entry_thresh)
    neg_mask = valid_fc & (fc <= -entry_thresh)
    sig[pos_mask] = 1.0
    sig[neg_mask] = -1.0

    # Strictly causal price-only / volatility-only gating (`P1-01` fix):
    # Replaces legacy non-causal `np.nanmedian(prev_c)` + 2026 live swap snapshot filter.
    # Signal generation NEVER peeks at future prices or 2026 swap snapshots; real swap
    # costs are deducted exclusively during execution replay (`replay_swing_d1_series`).
    if swap_filter:
        atr_pct = np.where(
            np.isfinite(atr14) & np.isfinite(prev_c) & (prev_c > 0.0),
            atr14 / prev_c,
            np.nan,
        )
        causal_price_vol_ok = (
            np.isfinite(atr_pct)
            & (atr_pct >= 0.0025)
            & ((~np.isfinite(vol_ratio)) | (vol_ratio <= 1.60))
        )
        sig = np.where(causal_price_vol_ok, sig, 0.0)

    # Volatility-managed Moreira-Muir gate & inverse-variance weight (strictly shift = 1!)
    mm_weights = np.ones(n, dtype=np.float64)
    if vol_mode in ("mm_gate", "mm_inv_var"):
        for t in range(n):
            vr = float(vol_ratio[t])
            vp = float(vol_pct_rank[t])
            if not math.isfinite(vr) or vr <= 0.0:
                sig[t] = 0.0
                mm_weights[t] = 0.0
                continue
            if vr > vol_spike_cap or (math.isfinite(vp) and vp > vol_pct_cap):
                sig[t] = 0.0
                mm_weights[t] = 0.0
                continue
            if vol_mode == "mm_inv_var":
                # Literal Moreira-Muir (2017) inverse-variance weight capped at <= 1.0x prop risk
                w = 1.0 / (vr * vr)
                mm_weights[t] = min(1.0, max(0.30, w))

    # Cadence gating to enforce clean 2-10d swing entries without artificial churn
    if cadence == "roll_aware":
        # Avoid 3x triple-swap rollover night: Indices/Oil (Fri 3x) enter Mon (wd=0, hold 4d -> exit Fri open);
        # FX/Metals (Wed 3x) enter Thu (wd=3, hold 4d -> exit Wed open). Cuts weekly financing cost by ~57%!
        target_wd = 0 if int(sym_spec.get("swap_rollover3days", 3)) == 5 else 3
        sig = np.where(wds == target_wd, sig, 0.0)
    elif cadence == "weekly_mon":
        mon_mask = wds == 0
        sig = np.where(mon_mask, sig, 0.0)
    elif cadence == "every_k":
        idx_arr = np.arange(n, dtype=np.int64)
        sig = np.where((idx_arr % max(2, rebal_k)) == 0, sig, 0.0)
    elif cadence == "pullback":
        pb_long = (sig > 0.0) & (
            (np.isfinite(ret2) & (ret2 < 0.0)) | (np.isfinite(rsi5) & (rsi5 < 50.0))
        )
        pb_short = (sig < 0.0) & (
            (np.isfinite(ret2) & (ret2 > 0.0)) | (np.isfinite(rsi5) & (rsi5 > 50.0))
        )
        new_sig = np.zeros(n, dtype=np.float64)
        new_sig[pb_long] = 1.0
        new_sig[pb_short] = -1.0
        sig = new_sig
    elif cadence == "continuous":
        pass
    else:
        raise ValueError(f"Unsupported F06 cadence: {cadence!r}")

    if flip_side:
        sig = -sig

    return sig, sl_arr, tp_arr, mm_weights


def _scale_trades_by_weights(
    trades: list[dict[str, Any]],
    mm_weights_by_sym: Mapping[str, np.ndarray],
    slot_weight: float,
) -> list[dict[str, Any]]:
    """Apply causal entry-bar Moreira-Muir inverse-variance weight (`<= 1.0`) and basket `slot_weight`."""
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
        sym = str(tr["symbol"])
        eidx = int(tr["entry_idx"])
        w_arr = mm_weights_by_sym[sym]
        mm_w = float(w_arr[eidx]) if 0 <= eidx < w_arr.size else 1.0
        tot_w = mm_w * slot_weight
        nt = dict(tr)
        nt["mm_weight"] = round(mm_w, 6)
        nt["slot_weight"] = round(slot_weight, 6)
        if abs(tot_w - 1.0) > 1e-12:
            for k in r_keys:
                v = nt.get(k)
                if v is not None and not isinstance(v, bool) and math.isfinite(float(v)):
                    nt[k] = round(float(v) * tot_w, 6)
            nt["margin_util_frac"] = round(float(nt.get("margin_util_frac", 0.0)) * mm_w, 6)
        out.append(nt)
    return out


def _resolve_resolution_and_tier(symbols: Sequence[str], universe: Mapping[str, Any]) -> tuple[str, str]:
    assets = universe["assets"]
    res_set = {str(assets[s]["data_resolution"]) for s in symbols}
    tier_set = {str(assets[s]["blindness_tier"]) for s in symbols}
    res = next(iter(res_set)) if len(res_set) == 1 else cc.RES_D1_YAHOO_SANCTIONED
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
# Unified Public Evaluation Contract (`evaluate_candidate`)
# ---------------------------------------------------------------------------


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    _feature_cache: dict[tuple[str, int], tuple[dict[str, Any], dict[str, np.ndarray]]] | None = None,
) -> dict[str, Any]:
    """Evaluate any F06 Swing TSMOM candidate strictly on `years` and return the standard dict."""
    req_years = _validate_eval_years(years)
    max_year = max(req_years)
    spec_dict = dict(spec)
    symbols = [cc.normalize_symbol(s) for s in spec_dict["symbols"]]
    params = dict(spec_dict["params"])
    max_hold_bars = int(params["max_hold_bars"])
    exit_on_signal_flip = bool(params.get("exit_on_signal_flip", False))

    k_syms = len(symbols)
    slot_weight = 1.0 / math.sqrt(float(k_syms)) if k_syms > 1 else 1.0
    acct_bal = 100_000.0 if k_syms > 1 else 10_000.0
    risk_frac = round(0.005 / math.sqrt(float(k_syms)), 6) if k_syms > 1 else 0.005

    def _run_side(flip: bool) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        sliced_assets: dict[str, Any] = {}
        sigs_map: dict[str, np.ndarray] = {}
        sls_map: dict[str, np.ndarray] = {}
        tps_map: dict[str, np.ndarray | None] = {}
        mm_map: dict[str, np.ndarray] = {}

        for sym in symbols:
            a = universe["assets"][sym]
            cache_key = (sym, max_year)
            if _feature_cache is not None and cache_key in _feature_cache:
                d1_sub, feat = _feature_cache[cache_key]
            else:
                d1_sub = _slice_d1_upto_year(a["d1"], max_year)
                feat = _compute_asset_tsmom_features(d1_sub)
                if _feature_cache is not None:
                    _feature_cache[cache_key] = (d1_sub, feat)

            sig, sl_arr, tp_arr, mm_w = _build_tsmom_signal_and_weights(feat, a["spec"], params, flip_side=flip)
            sliced_assets[sym] = {
                "symbol": sym,
                "spec": a["spec"],
                "data_resolution": a["data_resolution"],
                "d1": d1_sub,
            }
            sigs_map[sym] = sig
            sls_map[sym] = sl_arr
            tps_map[sym] = tp_arr
            mm_map[sym] = mm_w

        res = cc.replay_swing_d1_series(
            sliced_assets,
            sigs_map,
            sls_map,
            tp_dists=tps_map,
            max_hold_bars=max_hold_bars,
            exit_on_signal_flip=exit_on_signal_flip,
            signal_already_shifted=True,  # All indicators strictly shift=1; sig[t] executes at open[t]
            account_balance_usd=acct_bal,
            risk_frac=risk_frac,
            account_type="ftmo_swing",
            years=req_years,
        )
        # Keep individual trade net_R at native 1.0R scale (with Moreira-Muir mm_weight <= 1.0)
        # so Stage 3 random-entry MC is apples-to-apples; apply basket slot_weight to daily_pnl!
        trades = _scale_trades_by_weights(res["trades"], mm_map, 1.0)
        return trades, res["margin_audit"]

    trades, margin_audit = _run_side(flip=False)
    fade_trades, _ = _run_side(flip=True)

    dpnl_1x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_1x")
    dpnl_15x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_15x")
    dpnl_2x = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_2x")
    dpnl_zpos = cc.compute_daily_pnl_series(trades, req_years, pnl_key="net_R_zero_pos_1x")
    fade_dpnl_1x = cc.compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")
    if slot_weight < 1.0:
        for d in (dpnl_1x, dpnl_15x, dpnl_2x, dpnl_zpos, fade_dpnl_1x):
            d["pnl"] = d["pnl"] * slot_weight

    m_1x = cc.compute_split_metrics(trades, dpnl_1x, pnl_key="net_R_1x")
    m_15x = cc.compute_split_metrics(trades, dpnl_15x, pnl_key="net_R_15x")
    m_2x = cc.compute_split_metrics(trades, dpnl_2x, pnl_key="net_R_2x")
    m_zpos = cc.compute_split_metrics(trades, dpnl_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = cc.compute_split_metrics(fade_trades, fade_dpnl_1x, pnl_key="net_R_1x")
    s0 = cc.stage0_screen(trades, max_fric_sl_ratio=0.15, min_keep_frac=0.50)

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

    data_resolution, blindness_tier = _resolve_resolution_and_tier(symbols, universe)
    allow_unidir = bool(spec_dict.get("allow_unidirectional", False))
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
# Candidate Space Builder (Baskets + All 27 Individual Assets)
# ---------------------------------------------------------------------------


def _build_f06_basket_specs() -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    baskets: list[tuple[str, tuple[str, ...]]] = [
        ("BAL27", BALANCED_27_SYMBOLS),
        ("FX17", FX_17_SYMBOLS),
        ("IDX6", INDICES_6_SYMBOLS),
        ("METOIL4", METALS_OIL_4_SYMBOLS),
        ("FXNEW7", TRUE_BLIND_7_SYMBOLS),
        ("NEW16", NEW16_SYMBOLS),
    ]

    yz_rationale = (
        "Baltas-Kosowski (2020) Yang-Zhang volatility-normalized EWMAC time-series momentum "
        "captures slow institutional macro repricing and trend persistence across global FX, "
        "indices, metals, and energy with strict 2-10d FTMO Swing risk and real triple-swap."
    )
    yz_cp = (
        "Central-bank policy gradualism, corporate FX hedgers, and under-reacting institutional "
        "asset allocators who adjust macro exposures slowly over multi-week horizons."
    )
    mm_rationale = (
        "Moreira-Muir (2017, JF) volatility-managed TSMOM scales risk inversely with lagged "
        "realized variance and skips extreme volatility spikes, avoiding trend-whipsaw drawdowns "
        "when volatility spikes without compensating expected trend returns."
    )
    mm_cp = (
        "Unhedged trend followers and forced margin-call liquidators who suffer whipsaw losses "
        "during volatility-spike reversals when liquidity evaporates."
    )

    basket_templates: list[tuple[str, str, dict[str, Any], str, str]] = [
        (
            "YZ_8_32_roll4",
            "F06A_YZ_EWMAC_TSMOM",
            {
                "forecast_key": "ewmac_8_32_yz",
                "entry_thresh": 0.65,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "none",
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            yz_rationale,
            yz_cp,
        ),
        (
            "YZ_16_64_roll4",
            "F06A_YZ_EWMAC_TSMOM",
            {
                "forecast_key": "ewmac_16_64_yz",
                "entry_thresh": 0.90,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "none",
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            yz_rationale,
            yz_cp,
        ),
        (
            "YZ_32_128_k10",
            "F06A_YZ_EWMAC_TSMOM",
            {
                "forecast_key": "ewmac_32_128_yz",
                "entry_thresh": 1.30,
                "cadence": "every_k",
                "rebal_k": 10,
                "vol_mode": "none",
                "sl_atr_mult": 2.2,
                "tp_atr_mult": None,
                "max_hold_bars": 10,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            yz_rationale,
            yz_cp,
        ),
        (
            "MM_TSTAT40_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "tstat_40_yz",
                "entry_thresh": 1.15,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_TSTAT60_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "tstat_60_yz",
                "entry_thresh": 1.20,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_TSTAT60_k10",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "tstat_60_yz",
                "entry_thresh": 1.45,
                "cadence": "every_k",
                "rebal_k": 10,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.40,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.2,
                "tp_atr_mult": None,
                "max_hold_bars": 10,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_INV_BLEND_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "blend_yz",
                "entry_thresh": 0.30,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.85,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_INV_BLEND_wk5",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "blend_atr",
                "entry_thresh": 0.25,
                "cadence": "weekly_mon",
                "rebal_k": 5,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 1.8,
                "tp_atr_mult": 3.4,
                "max_hold_bars": 5,
                "exit_on_signal_flip": False,
                "swap_filter": True,
            },
            mm_rationale,
            mm_cp,
        ),
    ]

    for bname, bsyms in baskets:
        for tag, subfam, params, rat, cp in basket_templates:
            specs.append(
                {
                    "candidate_id": f"F06C_{bname}_{tag}",
                    "family_id": FAMILY_ID,
                    "subfamily": f"F06C_BASKET_{subfam}",
                    "prop_track": "FTMO_SWING",
                    "symbols": list(bsyms),
                    "params": dict(params),
                    "economic_rationale": rat,
                    "counterparty_mechanism": cp,
                    "allow_unidirectional": False,
                }
            )
    return specs


def _build_f06_single_asset_specs() -> list[dict[str, Any]]:
    """Canonical low-DOF TSMOM templates evaluated across ALL 27 individual non-crypto symbols."""
    yz_rationale = (
        "Single-asset Baltas-Kosowski Yang-Zhang vol-normalized EWMAC swing TSMOM capturing "
        "multi-day macro trend persistence with hard ATR stop-loss and exact FTMO Swing swaps."
    )
    yz_cp = (
        "Slow-adjusting institutional macro mandates, corporate hedgers, and retail counter-trend "
        "faders providing liquidity into persistent 2-10d directional trends."
    )
    mm_rationale = (
        "Single-asset Moreira-Muir (2017, JF) inverse-variance volatility-managed TSMOM that "
        "scales exposure down in high variance and skips volatility-spike whipsaw regimes."
    )
    mm_cp = (
        "Volatility-insensitive directional traders and forced stop-out flows selling into brief "
        "pullbacks within calm-volatility persistent trends."
    )

    single_templates: list[tuple[str, str, dict[str, Any], str, str]] = [
        (
            "YZ_16_64_wk5",
            "F06A_YZ_EWMAC_TSMOM",
            {
                "forecast_key": "ewmac_16_64_yz",
                "entry_thresh": 0.75,
                "cadence": "weekly_mon",
                "rebal_k": 5,
                "vol_mode": "none",
                "sl_atr_mult": 1.8,
                "tp_atr_mult": 3.2,
                "max_hold_bars": 5,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            yz_rationale,
            yz_cp,
        ),
        (
            "YZ_16_64_roll4",
            "F06A_YZ_EWMAC_TSMOM",
            {
                "forecast_key": "ewmac_16_64_yz",
                "entry_thresh": 0.80,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "none",
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            yz_rationale,
            yz_cp,
        ),
        (
            "MM_TSTAT40_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "tstat_40_yz",
                "entry_thresh": 1.00,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.40,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_TSTAT60_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "tstat_60_yz",
                "entry_thresh": 1.00,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.40,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_INV_BLEND_wk5",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "blend_yz",
                "entry_thresh": 0.25,
                "cadence": "weekly_mon",
                "rebal_k": 5,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.85,
                "sl_atr_mult": 1.8,
                "tp_atr_mult": 3.4,
                "max_hold_bars": 5,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            mm_rationale,
            mm_cp,
        ),
        (
            "MM_INV_BLEND_roll4",
            "F06B_MOREIRA_MUIR_VOLMGT",
            {
                "forecast_key": "blend_yz",
                "entry_thresh": 0.30,
                "cadence": "roll_aware",
                "rebal_k": 4,
                "vol_mode": "mm_inv_var",
                "vol_spike_cap": 1.35,
                "vol_pct_cap": 0.88,
                "sl_atr_mult": 2.0,
                "tp_atr_mult": None,
                "max_hold_bars": 4,
                "exit_on_signal_flip": False,
                "swap_filter": False,
            },
            mm_rationale,
            mm_cp,
        ),
    ]

    specs: list[dict[str, Any]] = []
    for sym in BALANCED_27_SYMBOLS:
        for tag, subfam, params, rat, cp in single_templates:
            specs.append(
                {
                    "candidate_id": f"F06D_{sym}_{tag}",
                    "family_id": FAMILY_ID,
                    "subfamily": f"F06D_SINGLE_{subfam}",
                    "prop_track": "FTMO_SWING",
                    "symbols": [sym],
                    "params": dict(params),
                    "economic_rationale": rat,
                    "counterparty_mechanism": cp,
                    "allow_unidirectional": False,
                }
            )
    return specs


# ---------------------------------------------------------------------------
# Cluster A Discovery (`2018-2020` ONLY — Hard Blindness Lock)
# ---------------------------------------------------------------------------


def _score_cluster_a(eval_res: Mapping[str, Any]) -> tuple[float, bool]:
    """Compute anti-overfit Cluster A score strictly from `2018-2020` metrics."""
    met = eval_res["metrics"]
    m1 = met["1x"]
    m15 = met["1.5x"]
    m2 = met["2x"]
    mz = met["zero_pos_swap_1x"]
    mf = met["fade_1x"]
    s0 = met["stage0"]
    ma = met["margin_audit"]

    n_tr = int(m1["n_trades"])
    if n_tr < 15 or not bool(s0["passed"]) or bool(ma.get("portfolio_margin_breached", False)):
        return -999.0 + 0.01 * float(m1["net_R"]), False

    sh1 = float(m1["sharpe"])
    sh2 = float(m2["sharpe"])
    shz = float(mz["sharpe"])
    shf = float(mf["sharpe"])
    pf1 = min(float(m1["pf"]), 5.0)
    pf2 = min(float(m2["pf"]), 5.0)
    pos_ratio = float(m1["positive_year_ratio"])
    fade_edge = sh1 - shf

    is_basket = len(eval_res["spec"]["symbols"]) > 1
    min_tr_gate = 40 if is_basket else 22

    prim_ok = (
        bool(s0["passed"])
        and not bool(ma.get("portfolio_margin_breached", False))
        and n_tr >= min_tr_gate
        and float(m1["net_R"]) > 0.0
        and float(m15["net_R"]) > 0.0
        and float(m2["net_R"]) > 0.0
        and float(mz["net_R"]) > 0.0
        and sh1 >= 0.40
        and sh2 >= 0.20
        and shz >= 0.25
        and pos_ratio >= 0.65
        and fade_edge > 0.20
    )

    tier = str(eval_res["blindness_tier"])
    tier_bonus = 0.25 if tier == cc.TIER_NEW7 else (0.15 if tier == cc.TIER_NEW9 else (0.10 if is_basket else 0.0))
    sample_bonus = min(0.25, math.log1p(n_tr) / 22.0)

    score = (
        0.30 * sh1
        + 0.25 * sh2
        + 0.25 * shz
        + 0.20 * fade_edge
        + 0.20 * (pf2 - 1.0)
        + 0.15 * (pf1 - 1.0)
        + 0.45 * pos_ratio
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
    """Run Cluster A (`2018-2020` ONLY) discovery for `F06_SWING_TSMOM` across all 27 non-crypto symbols."""
    if resume and cc.has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return cc.load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    feat_cache: dict[tuple[str, int], tuple[dict[str, Any], dict[str, np.ndarray]]] = {}
    basket_specs = _build_f06_basket_specs()
    single_specs = _build_f06_single_asset_specs()

    def _eval_batch(specs_in: Sequence[Mapping[str, Any]]) -> list[tuple[float, bool, dict[str, Any]]]:
        out: list[tuple[float, bool, dict[str, Any]]] = []
        for sp in specs_in:
            res = evaluate_candidate(sp, universe, cc.CLUSTER_A_YEARS, _feature_cache=feat_cache)
            for tr in res["trades"]:
                if int(str(tr["exit_date"])[:4]) > 2020 or int(tr["exit_ts"]) >= 1_609_459_200:
                    raise ValueError(f"CLUSTER_B_LEAK_BLOCKED in F06 discovery: {tr}")
            sc, ok = _score_cluster_a(res)
            out.append((sc, ok, res))
        out.sort(key=lambda item: (item[1], item[0]), reverse=True)
        return out

    basket_evals = _eval_batch(basket_specs)
    single_evals = _eval_batch(single_specs)

    # Diversified Primary selection (<= PRIMARY_CAP = 16):
    # - Up to 7 top multi-asset baskets (spanning BAL27, FX17, IDX6, METOIL4, FXNEW7, NEW16)
    # - Up to 9 top individual assets (prioritizing TRUE_BLIND_7 & NEW9, max 1 primary per symbol!)
    primary_records: list[dict[str, Any]] = []
    selected_ids: set[str] = set()
    basket_grp_counts: dict[str, int] = {}
    single_sym_used: set[str] = set()

    # Pass 1: Top baskets (max 2 per basket group, up to 7 total basket primaries)
    for sc, ok, res in basket_evals:
        if len(primary_records) >= 7:
            break
        if not ok:
            continue
        cid = str(res["spec"]["candidate_id"])
        bgrp = cid.split("_")[1]
        if basket_grp_counts.get(bgrp, 0) >= 2:
            continue
        primary_records.append(_compact_candidate_record(res, "PRIMARY", sc))
        selected_ids.add(cid)
        basket_grp_counts[bgrp] = basket_grp_counts.get(bgrp, 0) + 1

    # Pass 2: Top individual NEW7 & NEW9 assets (max 1 per symbol)
    for target_tier in (cc.TIER_NEW7, cc.TIER_NEW9, cc.TIER_12OLD):
        for sc, ok, res in single_evals:
            if len(primary_records) >= PRIMARY_CAP:
                break
            if not ok or str(res["blindness_tier"]) != target_tier:
                continue
            sym = str(res["spec"]["symbols"][0])
            cid = str(res["spec"]["candidate_id"])
            if sym in single_sym_used or cid in selected_ids:
                continue
            primary_records.append(_compact_candidate_record(res, "PRIMARY", sc))
            selected_ids.add(cid)
            single_sym_used.add(sym)

    # Pass 3: If slots remain below PRIMARY_CAP, fill with best remaining prim_ok baskets/singles
    combined_all = sorted([*basket_evals, *single_evals], key=lambda item: (item[1], item[0]), reverse=True)
    for sc, ok, res in combined_all:
        if len(primary_records) >= PRIMARY_CAP:
            break
        cid = str(res["spec"]["candidate_id"])
        if cid in selected_ids or not ok:
            continue
        primary_records.append(_compact_candidate_record(res, "PRIMARY", sc))
        selected_ids.add(cid)

    # Build EXPLORATORY pool up to TOTAL_CAP = 100 (keeping broad coverage across baskets & all 27 symbols)
    exploratory_records: list[dict[str, Any]] = []
    # First include top remaining baskets (up to 30 exploratory baskets)
    for sc, _ok, res in basket_evals:
        cid = str(res["spec"]["candidate_id"])
        if cid in selected_ids:
            continue
        if len(exploratory_records) >= 30 or (len(primary_records) + len(exploratory_records)) >= TOTAL_CAP:
            break
        exploratory_records.append(_compact_candidate_record(res, "EXPLORATORY", sc))
        selected_ids.add(cid)

    # Next ensure every one of the 27 symbols has at least its best Cluster A spec represented
    best_per_sym_added: set[str] = set(single_sym_used)
    for sc, _ok, res in single_evals:
        if (len(primary_records) + len(exploratory_records)) >= TOTAL_CAP:
            break
        cid = str(res["spec"]["candidate_id"])
        sym = str(res["spec"]["symbols"][0])
        if cid in selected_ids or sym in best_per_sym_added:
            continue
        exploratory_records.append(_compact_candidate_record(res, "EXPLORATORY", sc))
        selected_ids.add(cid)
        best_per_sym_added.add(sym)

    # Fill remainder to TOTAL_CAP with highest-scoring remaining specs
    for sc, _ok, res in combined_all:
        if (len(primary_records) + len(exploratory_records)) >= TOTAL_CAP:
            break
        cid = str(res["spec"]["candidate_id"])
        if cid in selected_ids:
            continue
        exploratory_records.append(_compact_candidate_record(res, "EXPLORATORY", sc))
        selected_ids.add(cid)

    tier_prim_counts: dict[str, int] = {}
    for rec in primary_records:
        t = str(rec["blindness_tier"])
        tier_prim_counts[t] = tier_prim_counts.get(t, 0) + 1

    meta: dict[str, Any] = {
        "family_slug": FAMILY_SLUG,
        "discovery_years": list(cc.CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "total_cap": TOTAL_CAP,
        "symbols_covered_count": len(BALANCED_27_SYMBOLS),
        "primary_tier_breakdown": tier_prim_counts,
        "total_evaluated_cluster_a": len(basket_evals) + len(single_evals),
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
    parser = argparse.ArgumentParser(description="Offensive #3 Family F06 Swing TSMOM 27-Symbol Cluster-A Discovery")
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

    # STRICT HARD BLINDNESS: load ONLY CLUSTER_A_YEARS = (2018, 2019, 2020) across all 27 non-crypto symbols!
    uni_a = cc.load_universe_28(
        load_m1=False,
        load_d1=True,
        years=cc.CLUSTER_A_YEARS,
        symbols=BALANCED_27_SYMBOLS,
        verify_sha=bool(args.verify_sha),
    )
    doc = discover_cluster_a(uni_a, save_checkpoint=True, resume=False)
    print(
        f"[DONE] {FAMILY_ID}: primary={doc['primary_count']}/{doc['primary_cap']} "
        f"total={doc['total_count']}/{doc['total_cap']} years={doc['discovery_years']} "
        f"prim_tiers={doc['meta'].get('primary_tier_breakdown')}"
    )
    for rec in doc["primary_candidates"][:10]:
        m1 = rec["cluster_a_metrics_1x"]
        m2 = rec["cluster_a_metrics_2x"]
        mz = rec["cluster_a_metrics_zero_pos_1x"]
        mf = rec["cluster_a_fade_1x"]
        s0 = rec["cluster_a_stage0"]
        print(
            f"  {rec['candidate_id']:36s} n={m1['n_trades']:4d} "
            f"1x_R={m1['net_R']:+6.2f} Sh1={m1['sharpe']:+5.2f} Sh2={m2['sharpe']:+5.2f} "
            f"ShZ={mz['sharpe']:+5.2f} FadeSh={mf['sharpe']:+5.2f} "
            f"f/SL={100*float(s0['median_fric_sl_ratio'] or 0):.1f}% "
            f"posY={m1['positive_years']}/{m1['total_years']} [{rec['blindness_tier']}]"
        )
    return 0


__all__ = [
    "BALANCED_27_SYMBOLS",
    "FAMILY_ID",
    "FAMILY_SLUG",
    "FX_17_SYMBOLS",
    "INDICES_6_SYMBOLS",
    "METALS_OIL_4_SYMBOLS",
    "NEW16_SYMBOLS",
    "NEW9_SYMBOLS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PRIMARY_CAP",
    "TOTAL_CAP",
    "TRUE_BLIND_7_SYMBOLS",
    "causal_yang_zhang_vol",
    "discover_cluster_a",
    "evaluate_candidate",
]

if __name__ == "__main__":
    raise SystemExit(_main())
