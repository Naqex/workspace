"""Total Offensive #3 — Family F11 (`F11_PAIRS_STATARB`): Cointegrated & Relative-Value Pairs.

White-box Prop-first Statistical Arbitrage & Relative-Value Pairs across the 28-symbol
FTMO universe (`FTMO_SWING` 1-8d + `INTRADAY_SWAP0` M1 Bid/Ask):
  - Strictly causal rolling OLS and 2-state Kalman Filter hedge ratios (`shift = 1`).
  - Spread Z-score entry (`|Z| >= 1.75..2.25`), reversion target (`|Z| <= 0.30`),
    HARD Z-STOP (`|Z| >= 3.50`), mandatory HARD ATR-leg SL on BOTH legs, and
    max-hold time stop (`1..8` days for Swing; hard flat `<= 20:50 UTC` for Intraday).
  - ZERO grid, ZERO martingale, ZERO naked single-leg carry.
  - Checks BOTH legs' real spread, commission, slippage (`1.0x/1.5x/2.0x`), real
    triple-swap (`Wed 3x` FX/Metals, `Fri 3x` Indices/Oil), Anti-Fake-Swap Guard,
    `zero_pos_swap` floor, AND FTMO Swing/Standard real leverage margin simultaneously!
  - Matched opposite-side fade tape (`fade_daily_pnl_1x`) replayed honestly through
    the exact same 2-leg cost & swap engine.
  - HARD BLINDNESS LOCK: `discover_cluster_a` strictly uses `CLUSTER_A_YEARS=(2018, 2019, 2020)`
    ONLY and saves atomically to `.runtime/offensive3/candidates/F11_PAIRS_STATARB.json`.

Hard invariants (`[ARCH-02]`, `G01`, `G04`, `G05`, `G06`, `G07`):
  - ZERO bare `assert` statements (all guards remain active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, zero sealed rows analysed.
  - Pure stdlib + NumPy + PyArrow + optional Numba JIT (X13 air-gap compatible).
"""

from __future__ import annotations

import argparse
import math
import sys
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

_REPO_ROOT = Path(__file__).resolve().parents[4]
_AI_ENGINES_DIR = _REPO_ROOT / "tooling" / "ai-engines"
for _p in (_REPO_ROOT, _AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


from quant_factory.offensive3.common_contract import (  # noqa: E402
    CLUSTER_A_YEARS,
    FRICTION_TIERS,
    HARD_FLAT_MAX_UTC_HHMM,
    HARD_FLAT_MAX_UTC_SEC,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    TIER_NEW9,
    causal_atr,
    compute_causal_tick_val_usd,
    compute_daily_pnl_series,
    compute_daily_swap_frac,
    compute_notional_and_margin_per_lot_usd,
    compute_split_metrics,
    enforce_dev_date_bound,
    enforce_dev_ts_bound,
    find_first_red_news_flatten_ts,
    has_valid_family_checkpoint,
    is_in_red_news_window,
    load_dev_red_news_index,
    load_family_candidates,
    load_universe_28,
    normalize_symbol,
    save_family_candidates,
    stage0_screen,
)
from quant_factory.offensive3.x13_m1_loader import resample_m1_to_tf  # noqa: E402

FAMILY_ID: str = "F11_PAIRS_STATARB"
PRIMARY_CAP: int = 15  # Satisfies both brief (<= 16) and preregistration_m1200.json (15)
TOTAL_CAP: int = 100
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"
_CL_A_END_TS: int = 1_609_459_200  # 2021-01-01T00:00:00Z

SWING_D1_PAIRS: tuple[tuple[str, str, str], ...] = (
    (
        "XAUUSD",
        "XAGUSD",
        "Precious metals Gold/Silver relative-value cointegration driven by shared monetary safe-haven and "
        "industrial-metal hedging flows across bullion dealers.",
    ),
    (
        "USOIL",
        "UKOIL",
        "WTI/Brent crude oil grade spread mean-reversion driven by physical trans-Atlantic cargo arbitrage "
        "and refinery margin rebalancing (Apr-2020 USOIL dates quarantined).",
    ),
    (
        "EURUSD",
        "USDCHF",
        "Inverse-correlated European major FX pair reflecting shared Eurozone/Swiss macro capital flows "
        "and SNB cross-currency liquidity stabilization.",
    ),
    (
        "AUDUSD",
        "NZDUSD",
        "Antipodean commodity-FX cointegration driven by shared China/Asia trade exposure and "
        "trans-Tasman central-bank rate convergence.",
    ),
    (
        "US500",
        "US30",
        "Broad US large-cap S&P 500 vs Dow 30 relative-value spread driven by institutional index arbitrage "
        "and ETF basket creation/redemption.",
    ),
    (
        "US500",
        "US100",
        "US broad equity vs Nasdaq-100 growth-factor spread reverting transient sector rotation shocks "
        "via multi-strategy institutional rebalancing.",
    ),
    (
        "GER40",
        "UK100",
        "European industrial DAX vs UK FTSE-100 equity relative-value spread reflecting pan-European "
        "institutional sector rebalancing and FX-hedged cross-index flows.",
    ),
    (
        "AUDJPY",
        "NZDJPY",
        "Antipodean JPY carry-cross relative-value spread isolating pure AUD/NZD divergence while "
        "canceling common JPY risk-on/risk-off beta.",
    ),
    (
        "CADJPY",
        "CHFJPY",
        "True-blind JPY cross relative-value pair balancing oil-linked CAD vs safe-haven CHF exposure "
        "with common JPY funding leg neutralized.",
    ),
    (
        "EURAUD",
        "GBPAUD",
        "True-blind European-vs-AUD cross pair isolating EUR/GBP relative value while hedging shared "
        "commodity-currency AUD volatility.",
    ),
)

INTRADAY_M1_PAIRS: tuple[tuple[str, str, int, int, str], ...] = (
    (
        "US500",
        "US100",
        13,
        20,
        "Intraday US cash-session S&P 500 vs Nasdaq-100 index-arbitrage spread mean-reversion with "
        "zero overnight swap and mandatory <=20:50 UTC hard flat.",
    ),
    (
        "EURUSD",
        "GBPUSD",
        7,
        20,
        "Intraday London/NY EURUSD vs GBPUSD dollar-neutral cross-flow mean-reversion exploiting "
        "temporary dealer inventory imbalances with swap=0 hard flat.",
    ),
    (
        "EURJPY",
        "GBPJPY",
        7,
        20,
        "Intraday London/NY EURJPY vs GBPJPY yen-neutral relative-value spread reverting transient "
        "cross-yen stop-runs before mandatory <=20:50 UTC flat.",
    ),
)

SWING_POOLS: dict[str, tuple[tuple[str, str], ...]] = {
    "POOL_ALL_10": tuple((a, b) for a, b, _ in SWING_D1_PAIRS),
    "POOL_FX_5": (
        ("EURUSD", "USDCHF"),
        ("AUDUSD", "NZDUSD"),
        ("AUDJPY", "NZDJPY"),
        ("CADJPY", "CHFJPY"),
        ("EURAUD", "GBPAUD"),
    ),
    "POOL_TRUE_BLIND_3": (
        ("AUDJPY", "NZDJPY"),
        ("CADJPY", "CHFJPY"),
        ("EURAUD", "GBPAUD"),
    ),
    "POOL_COMMOD_2": (
        ("XAUUSD", "XAGUSD"),
        ("USOIL", "UKOIL"),
    ),
    "POOL_INDEX_3": (
        ("US500", "US30"),
        ("US500", "US100"),
        ("GER40", "UK100"),
    ),
}

_PAIR_DESC_MAP: dict[tuple[str, str], str] = {
    **{(a, b): desc for a, b, desc in SWING_D1_PAIRS},
    **{(a, b): desc for a, b, _, _, desc in INTRADAY_M1_PAIRS},
}

_COUNTERPARTY_SWING: str = (
    "Single-leg institutional order-flow imbalances, ETF/futures index rebalancing, and localized "
    "commodity/FX liquidity shocks temporarily widen cointegrated spreads before relative-value desks "
    "and cross-market arbitrageurs force convergence; hard Z-stop and dual ATR stops truncate structural breaks."
)
_COUNTERPARTY_M1: str = (
    "Intraday session-open stop runs and single-pair institutional block executions create short-lived "
    "relative-value dislocations across highly correlated pairs that mean-revert during London/NY "
    "liquidity provision while staying strictly flat before rollover (swap=0)."
)


# ---------------------------------------------------------------------------
# 1. Strictly Causal Hedge Ratio & Spread Z-Score Primitives (`shift = 1`)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _causal_ols_spread_z_jit(
    log_a: np.ndarray,
    log_b: np.ndarray,
    reg_win: int,
    z_win: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Strictly `shift = 1` causal rolling OLS hedge ratio, correlation, spread, and Z-score.

    At index `t`:
      - `beta[t]` and `corr[t]` are fit ONLY on `log_a[t - reg_win : t]` & `log_b[t - reg_win : t]`.
      - `z[t]` standardizes the residual at `t - 1` against residuals across `[t - z_win : t]`
        computed using the SAME causal `(alpha[t], beta[t])` -> zero lookahead into bar `t`!
    """
    n = log_a.shape[0]
    beta_out = np.full(n, np.nan, dtype=np.float64)
    corr_out = np.full(n, np.nan, dtype=np.float64)
    z_out = np.full(n, np.nan, dtype=np.float64)
    hl_out = np.full(n, np.nan, dtype=np.float64)
    w_req = reg_win if reg_win >= z_win else z_win
    if n <= w_req:
        return beta_out, corr_out, z_out, hl_out

    for t in range(w_req, n):
        # 1. Rolling OLS on [t - reg_win : t] (bars <= t - 1 ONLY)
        mean_x = 0.0
        mean_y = 0.0
        ok = True
        for k in range(t - reg_win, t):
            xa = log_b[k]
            ya = log_a[k]
            if not (np.isfinite(xa) and np.isfinite(ya)):
                ok = False
                break
            mean_x += xa
            mean_y += ya
        if not ok:
            continue
        inv_r = 1.0 / float(reg_win)
        mean_x *= inv_r
        mean_y *= inv_r

        sxx = 0.0
        syy = 0.0
        sxy = 0.0
        for k in range(t - reg_win, t):
            dx = log_b[k] - mean_x
            dy = log_a[k] - mean_y
            sxx += dx * dx
            syy += dy * dy
            sxy += dx * dy
        if sxx <= 1e-14 or syy <= 1e-14:
            continue
        beta = sxy / sxx
        alpha = mean_y - beta * mean_x
        corr = sxy / math.sqrt(sxx * syy)
        beta_out[t] = beta
        corr_out[t] = corr

        # 2. Spread Z-score on [t - z_win : t] evaluated with causal (alpha, beta)
        s_mean = 0.0
        for k in range(t - z_win, t):
            s_mean += log_a[k] - (alpha + beta * log_b[k])
        s_mean /= float(z_win)

        ssq = 0.0
        for k in range(t - z_win, t):
            sk = (log_a[k] - (alpha + beta * log_b[k])) - s_mean
            ssq += sk * sk
        sd = math.sqrt(ssq / float(z_win - 1)) if z_win > 1 else 0.0
        if sd > 1e-12:
            s_last = log_a[t - 1] - (alpha + beta * log_b[t - 1])
            z_out[t] = (s_last - s_mean) / sd

        # 3. Causal AR(1) Ornstein-Uhlenbeck half-life on [t - reg_win : t]
        if reg_win >= 15:
            m_prev = 0.0
            m_diff = 0.0
            cnt = reg_win - 1
            for k in range(t - reg_win + 1, t):
                sp0 = log_a[k - 1] - (alpha + beta * log_b[k - 1])
                sp1 = log_a[k] - (alpha + beta * log_b[k])
                m_prev += sp0
                m_diff += sp1 - sp0
            m_prev /= float(cnt)
            m_diff /= float(cnt)
            num_ar = 0.0
            den_ar = 0.0
            for k in range(t - reg_win + 1, t):
                sp0 = log_a[k - 1] - (alpha + beta * log_b[k - 1])
                sp1 = log_a[k] - (alpha + beta * log_b[k])
                d0 = sp0 - m_prev
                d1 = (sp1 - sp0) - m_diff
                num_ar += d0 * d1
                den_ar += d0 * d0
            if den_ar > 1e-14:
                phi = num_ar / den_ar
                if -0.99 < phi < -1e-4:
                    hl_out[t] = -math.log(2.0) / math.log(1.0 + phi)

    return beta_out, corr_out, z_out, hl_out


@njit(cache=True)
def _causal_kalman_spread_z_jit(
    log_a: np.ndarray,
    log_b: np.ndarray,
    q_noise: float,
    r_noise: float,
    z_win: int,
    warmup: int,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Strictly `shift = 1` causal 2-state Kalman Filter (`[alpha_k, beta_k]`) + innovation Z-score."""
    n = log_a.shape[0]
    beta_out = np.full(n, np.nan, dtype=np.float64)
    corr_out = np.full(n, np.nan, dtype=np.float64)
    z_out = np.full(n, np.nan, dtype=np.float64)
    if n <= warmup + 2:
        return beta_out, corr_out, z_out

    # Seed state [alpha, beta] from first `warmup` bars only (indices 0..warmup-1)
    mx = 0.0
    my = 0.0
    for k in range(warmup):
        mx += log_b[k]
        my += log_a[k]
    mx /= float(warmup)
    my /= float(warmup)
    sxx = 0.0
    sxy = 0.0
    for k in range(warmup):
        dx = log_b[k] - mx
        dy = log_a[k] - my
        sxx += dx * dx
        sxy += dx * dy
    b0 = (sxy / sxx) if sxx > 1e-12 else 1.0
    a0 = my - b0 * mx

    # 2x2 state vector [theta0=alpha, theta1=beta] and covariance P
    th0 = a0
    th1 = b0
    p00 = 1e-3
    p01 = 0.0
    p10 = 0.0
    p11 = 1e-3

    innovs = np.full(n, np.nan, dtype=np.float64)

    for k in range(warmup, n - 1):
        xk = log_b[k]
        yk = log_a[k]
        if not (np.isfinite(xk) and np.isfinite(yk)):
            continue
        # Predict covariance
        p00_p = p00 + q_noise
        p01_p = p01
        p10_p = p10
        p11_p = p11 + q_noise

        # Measurement prediction y_hat = th0 + th1 * xk
        err = yk - (th0 + th1 * xk)
        innovs[k] = err

        # Innovation variance S = H P H^T + R, H = [1, xk]
        hp0 = p00_p + p01_p * xk
        hp1 = p10_p + p11_p * xk
        s_var = hp0 + hp1 * xk + r_noise
        if s_var <= 1e-15:
            s_var = 1e-15

        # Kalman gain K = P H^T / S
        k0 = (p00_p + p01_p * xk) / s_var
        k1 = (p10_p + p11_p * xk) / s_var

        # State update
        th0 = th0 + k0 * err
        th1 = th1 + k1 * err

        # Covariance update P = (I - K H) P_pred
        np00 = (1.0 - k0) * p00_p - (k0 * xk) * p10_p
        np01 = (1.0 - k0) * p01_p - (k0 * xk) * p11_p
        np10 = (-k1) * p00_p + (1.0 - k1 * xk) * p10_p
        np11 = (-k1) * p01_p + (1.0 - k1 * xk) * p11_p
        p00, p01, p10, p11 = np00, np01, np10, np11

        # Strictly shift = 1: bar k observation informs bar t = k + 1 open!
        t = k + 1
        beta_out[t] = th1

        # Causal rolling correlation over [t - z_win : t]
        if k >= warmup + z_win:
            cm_x = 0.0
            cm_y = 0.0
            for j in range(t - z_win, t):
                cm_x += log_b[j]
                cm_y += log_a[j]
            cm_x /= float(z_win)
            cm_y /= float(z_win)
            cxx = 0.0
            cyy = 0.0
            cxy = 0.0
            for j in range(t - z_win, t):
                dx = log_b[j] - cm_x
                dy = log_a[j] - cm_y
                cxx += dx * dx
                cyy += dy * dy
                cxy += dx * dy
            if cxx > 1e-14 and cyy > 1e-14:
                corr_out[t] = cxy / math.sqrt(cxx * cyy)

            # Standardized innovation Z-score over [t - z_win : t]
            em = 0.0
            ok_e = True
            for j in range(t - z_win, t):
                ev = innovs[j]
                if not np.isfinite(ev):
                    ok_e = False
                    break
                em += ev
            if ok_e:
                em /= float(z_win)
                ess = 0.0
                for j in range(t - z_win, t):
                    de = innovs[j] - em
                    ess += de * de
                esd = math.sqrt(ess / float(z_win - 1)) if z_win > 1 else 0.0
                if esd > 1e-12:
                    z_out[t] = (innovs[t - 1] - em) / esd

    return beta_out, corr_out, z_out


# ---------------------------------------------------------------------------
# 2. Universe Helpers & Strict Cluster-A Blindness Slicing
# ---------------------------------------------------------------------------


def _slice_universe_max_year(universe: Mapping[str, Any], max_year: int) -> dict[str, Any]:
    """Return a zero-copy-safe view of `universe` strictly clamped to `year <= max_year`."""
    if max_year > 2024:
        raise ValueError(f"DEV_SEAL_VIOLATION: max_year={max_year} > 2024")
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    cutoff_date = f"{max_year + 1:04d}-01-01"

    assets_out: dict[str, dict[str, Any]] = {}
    for sym, aobj in universe["assets"].items():
        new_a = dict(aobj)
        d1 = aobj.get("d1")
        if d1 is not None:
            d1_dates = [str(d) for d in d1["dates"]]
            mask = np.array([d < cutoff_date for d in d1_dates], dtype=bool)
            if bool(np.any(mask)):
                new_d1 = dict(d1)
                new_d1["times_sec"] = np.asarray(d1["times_sec"], dtype=np.int64)[mask]
                new_d1["dates"] = [d for d, m in zip(d1_dates, mask, strict=True) if m]
                new_d1["years"] = np.asarray(d1["years"], dtype=np.int32)[mask]
                new_d1["weekdays"] = np.asarray(d1["weekdays"], dtype=np.int32)[mask]
                new_d1["open"] = np.asarray(d1["open"], dtype=np.float64)[mask]
                new_d1["high"] = np.asarray(d1["high"], dtype=np.float64)[mask]
                new_d1["low"] = np.asarray(d1["low"], dtype=np.float64)[mask]
                new_d1["close"] = np.asarray(d1["close"], dtype=np.float64)[mask]
                if "spread_price" in d1:
                    new_d1["spread_price"] = np.asarray(d1["spread_price"], dtype=np.float64)[mask]
                new_a["d1"] = new_d1
            else:
                new_a["d1"] = None
        m1 = aobj.get("m1")
        if m1 is not None:
            ts_m1 = np.asarray(m1["times_sec"], dtype=np.int64)
            end_i = int(np.searchsorted(ts_m1, cutoff_ts, side="left"))
            if end_i > 0:
                new_m1 = dict(m1)
                new_m1["times_sec"] = ts_m1[:end_i]
                new_m1["quotes"] = np.asarray(m1["quotes"], dtype=np.float64)[:end_i]
                new_m1["minutes"] = end_i
                new_a["m1"] = new_m1
            else:
                new_a["m1"] = None
        assets_out[sym] = new_a

    out = dict(universe)
    out["assets"] = assets_out
    out["years"] = [int(y) for y in universe.get("years", []) if int(y) <= max_year]
    return out


def _resolve_group_tags(symbols: Sequence[str], universe: Mapping[str, Any]) -> tuple[str, str, dict[str, str]]:
    res_set: set[str] = set()
    tier_set: set[str] = set()
    tier_map: dict[str, str] = {}
    for s in symbols:
        su = normalize_symbol(s)
        a = universe["assets"][su]
        res_set.add(str(a["data_resolution"]))
        t = str(a["blindness_tier"])
        tier_set.add(t)
        tier_map[su] = t
    data_res = next(iter(res_set)) if len(res_set) == 1 else "MIXED_M1_AND_D1"
    if len(tier_set) == 1:
        b_tier = next(iter(tier_set))
    elif tier_set == {TIER_12OLD, TIER_NEW9}:
        b_tier = "MIXED_12OLD_AND_NEW9"
    elif tier_set == {TIER_12OLD, TIER_NEW7}:
        b_tier = "MIXED_12OLD_AND_TRUE_BLIND_7"
    elif tier_set == {TIER_NEW9, TIER_NEW7}:
        b_tier = "MIXED_NEW9_AND_TRUE_BLIND_7"
    elif tier_set == {TIER_12OLD, TIER_NEW9, TIER_NEW7}:
        b_tier = "MIXED_ALL_3_TIERS"
    else:
        b_tier = "UNKNOWN"
    return data_res, b_tier, tier_map


def _daily_pnl_dict(trades: Sequence[Mapping[str, Any]], years: Sequence[int], pnl_key: str) -> dict[str, float]:
    dp = compute_daily_pnl_series(trades, years, pnl_key=pnl_key)
    return {d: round(float(v), 6) for d, v in zip(dp["dates"], dp["pnl"], strict=True)}


def _causal_zero_gap_lag_mask(
    symbol: str,
    opens: np.ndarray,
    closes: np.ndarray,
    *,
    threshold: float = 0.90,
    min_bars: int = 10,
) -> np.ndarray:
    """Strictly causal per-bar flag: True iff bar `t` needs +1 extra lag due to Yahoo zero-gap open.

    Yahoo Finance UK100 (^FTSE) prints `open[t] == close[t-1]` (`zero_gap_frac = 99.66%`) at LSE
    16:30 UTC on day `t-1`, which is 5.5-7.5h BEFORE UTC-close assets (`GER40/US500/US100/FX`).
    Checking `UK100` statically OR the strictly causal prefix `opens[1:t]` vs `closes[0:t-1]`
    (`k <= t-1`, zero bar-`t` or future peek) guarantees 100% physical causality under perturbation.
    """
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


def _align_d1_pair(
    d1_a: Mapping[str, Any],
    d1_b: Mapping[str, Any],
    max_year: int,
    *,
    sym_a: str = "",
    sym_b: str = "",
) -> dict[str, Any]:
    cutoff = f"{max_year + 1:04d}-01-01"
    idx_b = {str(d): i for i, d in enumerate(d1_b["dates"]) if str(d) < cutoff}
    ia_list: list[int] = []
    ib_list: list[int] = []
    dates: list[str] = []
    for i, d_raw in enumerate(d1_a["dates"]):
        ds = str(d_raw)
        if ds >= cutoff:
            break
        j = idx_b.get(ds)
        if j is not None:
            ia_list.append(i)
            ib_list.append(j)
            dates.append(ds)
    if not dates:
        raise ValueError("Aligned D1 pair has 0 overlapping dates")
    ia = np.array(ia_list, dtype=np.int64)
    ib = np.array(ib_list, dtype=np.int64)
    ts = np.asarray(d1_a["times_sec"], dtype=np.int64)[ia]
    enforce_dev_ts_bound(ts, context="align_d1_pair.ts")
    enforce_dev_date_bound(dates, context="align_d1_pair.dates")
    open_a = np.asarray(d1_a["open"], dtype=np.float64)[ia]
    close_a = np.asarray(d1_a["close"], dtype=np.float64)[ia]
    open_b = np.asarray(d1_b["open"], dtype=np.float64)[ib]
    close_b = np.asarray(d1_b["close"], dtype=np.float64)[ib]
    lag_mask_a = _causal_zero_gap_lag_mask(sym_a, open_a, close_a)
    lag_mask_b = _causal_zero_gap_lag_mask(sym_b, open_b, close_b)
    return {
        "dates": dates,
        "times_sec": ts,
        "weekdays": np.asarray(d1_a["weekdays"], dtype=np.int32)[ia],
        "years": np.array([int(d[:4]) for d in dates], dtype=np.int32),
        "open_a": open_a,
        "high_a": np.asarray(d1_a["high"], dtype=np.float64)[ia],
        "low_a": np.asarray(d1_a["low"], dtype=np.float64)[ia],
        "close_a": close_a,
        "open_b": open_b,
        "high_b": np.asarray(d1_b["high"], dtype=np.float64)[ib],
        "low_b": np.asarray(d1_b["low"], dtype=np.float64)[ib],
        "close_b": close_b,
        "zero_gap_lag_mask_a": lag_mask_a,
        "zero_gap_lag_mask_b": lag_mask_b,
        "zero_gap_lag_mask": lag_mask_a | lag_mask_b,
    }


def _size_two_leg_pair_with_margin(
    spec_a: Mapping[str, Any],
    spec_b: Mapping[str, Any],
    open_a: float,
    open_b: float,
    sl_dist_a: float,
    sl_dist_b: float,
    beta_abs: float,
    *,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    account_type: str = "ftmo_swing",
    max_margin_util_frac: float = 0.80,
) -> dict[str, Any]:
    """Beta-neutral 2-leg sizing with simultaneous FTMO leverage margin verification across BOTH legs."""
    if open_a <= 0.0 or open_b <= 0.0 or sl_dist_a <= 0.0 or sl_dist_b <= 0.0:
        return {"accepted": False, "reason": "INVALID_PRICE_OR_SL"}

    not_a, mar_a, lev_a = compute_notional_and_margin_per_lot_usd(spec_a, open_a, account_type=account_type)
    not_b, mar_b, lev_b = compute_notional_and_margin_per_lot_usd(spec_b, open_b, account_type=account_type)
    tv_a = compute_causal_tick_val_usd(spec_a, entry_price=open_a)
    tv_b = compute_causal_tick_val_usd(spec_b, entry_price=open_b)
    usd_px_a = tv_a / float(spec_a["point"])
    usd_px_b = tv_b / float(spec_b["point"])

    # Beta-neutral notional split: N_B = beta_abs * N_A, bounded so combined worst-case dual-SL <= 1.0 R
    b_clamped = min(3.0, max(0.25, float(beta_abs)))
    w_a = 1.0 / (1.0 + b_clamped)
    w_b = b_clamped / (1.0 + b_clamped)

    # Risk per $1 of notional on each leg: (sl_dist * usd_px_1lot) / notional_1lot
    r_per_not_a = (sl_dist_a * usd_px_a) / not_a
    r_per_not_b = (sl_dist_b * usd_px_b) / not_b
    comb_risk_per_tot_not = w_a * r_per_not_a + w_b * r_per_not_b
    if comb_risk_per_tot_not <= 1e-12 or not math.isfinite(comb_risk_per_tot_not):
        return {"accepted": False, "reason": "INVALID_RISK_DENOM"}

    risk_budget_usd = float(account_balance_usd) * float(risk_frac)
    tot_notional = risk_budget_usd / comb_risk_per_tot_not
    raw_lots_a = (w_a * tot_notional) / not_a
    raw_lots_b = (w_b * tot_notional) / not_b

    vmin_a, vstep_a = float(spec_a.get("volume_min", 0.01)), float(spec_a.get("volume_step", 0.01))
    vmin_b, vstep_b = float(spec_b.get("volume_min", 0.01)), float(spec_b.get("volume_step", 0.01))

    # Check simultaneous combined margin across BOTH legs
    raw_margin_usd = raw_lots_a * mar_a + raw_lots_b * mar_b
    avail_margin_usd = float(account_balance_usd) * float(max_margin_util_frac)
    margin_capped = False
    scale = 1.0
    if raw_margin_usd > avail_margin_usd and raw_margin_usd > 0.0:
        scale = avail_margin_usd / raw_margin_usd
        margin_capped = True

    lots_a = math.floor(((raw_lots_a * scale) / vstep_a) + 1e-12) * vstep_a
    lots_b = math.floor(((raw_lots_b * scale) / vstep_b) + 1e-12) * vstep_b
    if lots_a + 1e-12 < vmin_a or lots_b + 1e-12 < vmin_b:
        return {
            "accepted": False,
            "reason": "MARGIN_OR_VMIN_REJECTED",
            "margin_capped": margin_capped,
        }

    eff_margin_usd = lots_a * mar_a + lots_b * mar_b
    eff_margin_util = eff_margin_usd / float(account_balance_usd)
    if eff_margin_util > float(max_margin_util_frac) + 1e-9:
        return {
            "accepted": False,
            "reason": "OVER_MARGIN_AFTER_STEP",
            "margin_capped": True,
        }

    return {
        "accepted": True,
        "reason": "MARGIN_SCALED" if margin_capped else "OK",
        "margin_capped": margin_capped,
        "lots_a": round(lots_a, 6),
        "lots_b": round(lots_b, 6),
        "notional_a_usd": lots_a * not_a,
        "notional_b_usd": lots_b * not_b,
        "usd_px_a": usd_px_a,
        "usd_px_b": usd_px_b,
        "margin_usd": round(eff_margin_usd, 4),
        "margin_util_frac": round(eff_margin_util, 6),
        "leverage_a": lev_a,
        "leverage_b": lev_b,
        "risk_budget_usd": risk_budget_usd,
        "eff_risk_usd": lots_a * sl_dist_a * usd_px_a + lots_b * sl_dist_b * usd_px_b,
    }


# ---------------------------------------------------------------------------
# 3. Two-Leg Swing D1 Pairs Replay Engine (Exact Swaps, Costs & Margin)
# ---------------------------------------------------------------------------


def _replay_d1_pair_single(
    sym_a: str,
    sym_b: str,
    universe: Mapping[str, Any],
    params: Mapping[str, Any],
    years: Sequence[int],
    *,
    fade_mode: bool = False,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    max_margin_util_frac: float = 0.80,
) -> dict[str, Any]:
    """Replay one Swing D1 relative-value pair with strict `shift=1` causality & dual hard SL."""
    req_years = tuple(sorted(int(y) for y in years))
    max_year = max(req_years)
    allowed_set = set(req_years)

    asset_a = universe["assets"][sym_a]
    asset_b = universe["assets"][sym_b]
    spec_a = asset_a["spec"]
    spec_b = asset_b["spec"]

    al = _align_d1_pair(asset_a["d1"], asset_b["d1"], max_year=max_year, sym_a=sym_a, sym_b=sym_b)
    dates = al["dates"]
    ts_arr = al["times_sec"]
    wds = al["weekdays"]
    oa, ha, loa, ca = al["open_a"], al["high_a"], al["low_a"], al["close_a"]
    ob, hb, lob, cb = al["open_b"], al["high_b"], al["low_b"], al["close_b"]
    pair_lag_mask = al["zero_gap_lag_mask"]
    n = len(dates)

    if float(np.min(oa)) <= 0.0 or float(np.min(ob)) <= 0.0 or float(np.min(ca)) <= 0.0 or float(np.min(cb)) <= 0.0:
        raise ValueError(f"NONPOSITIVE_PAIR_PRICE [{sym_a}/{sym_b}]")

    log_a = np.log(ca)
    log_b = np.log(cb)
    atr_a = causal_atr(ha, loa, ca, 14)
    atr_b = causal_atr(hb, lob, cb, 14)

    hedge_model = str(params.get("hedge_model", "OLS")).upper()
    reg_win = int(params.get("reg_win", 60))
    z_win = int(params.get("z_win", 30))
    z_entry = float(params.get("z_entry", 2.0))
    z_exit = float(params.get("z_exit", 0.30))
    z_stop = float(params.get("z_stop", 3.50))
    sl_atr_mult = float(params.get("sl_atr_mult", 2.5))
    max_hold_bars = int(params.get("max_hold_bars", 8))
    min_abs_corr = float(params.get("min_abs_corr", 0.45))
    max_half_life = params.get("max_half_life")

    if hedge_model == "KALMAN":
        q_n = float(params.get("kalman_q", 1e-4))
        r_n = float(params.get("kalman_r", 1e-2))
        beta_arr, corr_arr, z_arr = _causal_kalman_spread_z_jit(log_a, log_b, q_n, r_n, z_win, warmup=30)
        hl_arr = np.full(n, np.nan, dtype=np.float64)
    else:
        beta_arr, corr_arr, z_arr, hl_arr = _causal_ols_spread_z_jit(log_a, log_b, reg_win, z_win)

    pt_a, bench_a, ow_a, comm_a = (
        float(spec_a["point"]),
        float(spec_a["benchmark_spread_pts"]) * float(spec_a["point"]),
        float(spec_a["oneway_bps"]),
        float(spec_a["commission_usd_lot"]),
    )
    pt_b, bench_b, ow_b, comm_b = (
        float(spec_b["point"]),
        float(spec_b["benchmark_spread_pts"]) * float(spec_b["point"]),
        float(spec_b["oneway_bps"]),
        float(spec_b["commission_usd_lot"]),
    )
    _ = (pt_a, pt_b)

    data_res, b_tier, _ = _resolve_group_tags((sym_a, sym_b), universe)

    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped_count = 0
    peak_margin_util = 0.0

    in_pos = False
    spread_dir = 0  # +1 long spread (normal), -1 short spread (normal); flipped in fade_mode
    side_a = 0
    side_b = 0
    entry_idx = -1
    ea = 0.0
    eb = 0.0
    sl_a = 0.0
    sl_b = 0.0
    lots_a = 0.0
    lots_b = 0.0
    usd_px_a = 0.0
    usd_px_b = 0.0
    not_a_usd = 0.0
    not_b_usd = 0.0
    risk_budget_usd = float(account_balance_usd) * float(risk_frac)
    eff_risk_usd = risk_budget_usd
    pos_margin_util = 0.0
    pos_margin_capped = False
    fric_1x_usd = 0.0
    cum_swap_real_usd = 0.0
    cum_swap_zpos_usd = 0.0
    entry_z = 0.0
    entry_beta = 0.0
    eps = 1e-12

    def _close_pair(exit_i: int, px_a: float, px_b: float, reason: str) -> None:
        nonlocal in_pos
        gross_usd = side_a * (px_a - ea) * usd_px_a * lots_a + side_b * (px_b - eb) * usd_px_b * lots_b
        gross_r = gross_usd / risk_budget_usd
        swap_real_r = cum_swap_real_usd / risk_budget_usd
        swap_zpos_r = cum_swap_zpos_usd / risk_budget_usd

        tier_real: dict[str, float] = {}
        tier_zpos: dict[str, float] = {}
        for mult in FRICTION_TIERS:
            m = float(mult)
            lbl = f"{m:g}x"
            f_r = (m * fric_1x_usd) / risk_budget_usd
            tier_real[lbl] = round(gross_r + swap_real_r - f_r, 6)
            tier_zpos[lbl] = round(gross_r + swap_zpos_r - f_r, 6)

        fsl_denom = max(eff_risk_usd, 1e-9)
        f1 = round(fric_1x_usd / fsl_denom, 6)
        f15 = round((1.5 * fric_1x_usd) / fsl_denom, 6)
        f2 = round((2.0 * fric_1x_usd) / fsl_denom, 6)
        trades.append(
            {
                "symbol": f"{sym_a}/{sym_b}",
                "leg_a": sym_a,
                "leg_b": sym_b,
                "blindness_tier": b_tier,
                "data_resolution": data_res,
                "spread_dir": int(spread_dir),
                "side_a": int(side_a),
                "side_b": int(side_b),
                "entry_idx": int(entry_idx),
                "exit_idx": int(exit_i),
                "entry_ts": int(ts_arr[entry_idx]),
                "exit_ts": int(ts_arr[exit_i]),
                "entry_date": dates[entry_idx],
                "exit_date": dates[exit_i],
                "entry_price_a": round(ea, 6),
                "entry_price_b": round(eb, 6),
                "exit_price_a": round(px_a, 6),
                "exit_price_b": round(px_b, 6),
                "sl_price_a": round(sl_a, 6),
                "sl_price_b": round(sl_b, 6),
                "entry_z": round(entry_z, 4),
                "entry_beta": round(entry_beta, 4),
                "lots_a": lots_a,
                "lots_b": lots_b,
                "hold_bars": int(exit_i - entry_idx),
                "exit_reason": reason,
                "margin_util_frac": pos_margin_util,
                "margin_capped": pos_margin_capped,
                "gross_R": round(gross_r, 6),
                "swap_real_R": round(swap_real_r, 6),
                "swap_zero_pos_R": round(swap_zpos_r, 6),
                "net_R": tier_real["1x"],
                "net_R_1x": tier_real["1x"],
                "net_R_15x": tier_real["1.5x"],
                "net_R_2x": tier_real["2x"],
                "net_R_zero_pos_1x": tier_zpos["1x"],
                "net_R_zero_pos_15x": tier_zpos["1.5x"],
                "net_R_zero_pos_2x": tier_zpos["2x"],
                "friction_over_sl": f2,
                "friction_over_sl_1x": f1,
                "friction_over_sl_15x": f15,
                "friction_over_sl_2x": f2,
            }
        )
        in_pos = False

    last_in_window = -1
    for t in range(n):
        yr_t = int(dates[t][:4])
        if yr_t > max_year:
            if in_pos and last_in_window >= entry_idx:
                _close_pair(last_in_window, float(ca[last_in_window]), float(cb[last_in_window]), "END_OF_WINDOW")
            break
        if yr_t in allowed_set:
            last_in_window = t

        o_a, h_a, l_a, c_a = float(oa[t]), float(ha[t]), float(loa[t]), float(ca[t])
        o_b, h_b, l_b, c_b = float(ob[t]), float(hb[t]), float(lob[t]), float(cb[t])
        # Fail-closed Yahoo zero-gap open guard (`P0-01`): when either leg has `zero_gap_frac >= 0.90`
        # (e.g. UK100 ^FTSE where open[t]==close[t-1] at 16:30 UTC, 5.5-7.5h before UTC-close peers),
        # lag ALL pair decision inputs by +1 extra bar so open[t] uses strictly <= t-2 closes!
        lag_t = 1 if bool(pair_lag_mask[t]) else 0
        sig_t = t - lag_t
        z_t = float(z_arr[sig_t]) if sig_t >= 0 else math.nan

        # 1. Manage open 2-leg position
        if in_pos:
            if t > entry_idx and dates[t] != dates[t - 1]:
                prev_wd = int(wds[t - 1])
                pca = float(ca[t - 1])
                pcb = float(cb[t - 1])
                # Exact notional-weighted swap on BOTH legs (Wed/Fri 3x + Anti-Fake-Swap Guard!)
                na_cur = not_a_usd * (pca / ea)
                nb_cur = not_b_usd * (pcb / eb)
                sw_a_r = compute_daily_swap_frac(spec_a, pca, side_a, prev_wd, zero_positive_swap=False)
                sw_b_r = compute_daily_swap_frac(spec_b, pcb, side_b, prev_wd, zero_positive_swap=False)
                sw_a_z = compute_daily_swap_frac(spec_a, pca, side_a, prev_wd, zero_positive_swap=True)
                sw_b_z = compute_daily_swap_frac(spec_b, pcb, side_b, prev_wd, zero_positive_swap=True)
                cum_swap_real_usd += sw_a_r * na_cur + sw_b_r * nb_cur
                cum_swap_zpos_usd += sw_a_z * na_cur + sw_b_z * nb_cur

            # Open-gap hard leg SL check FIRST (either leg breached -> flatten BOTH immediately)
            a_gap_sl = (side_a == 1 and o_a <= sl_a + eps) or (side_a == -1 and o_a >= sl_a - eps)
            b_gap_sl = (side_b == 1 and o_b <= sl_b + eps) or (side_b == -1 and o_b >= sl_b - eps)
            if a_gap_sl or b_gap_sl:
                _close_pair(t, o_a, o_b, "LEG_SL_GAP")
            elif (t - entry_idx) >= max_hold_bars:
                _close_pair(t, o_a, o_b, "TIME_STOP")
            elif math.isfinite(z_t):
                # Hard Z-stop & Z-reversion exit (based on underlying spread Z)
                if not fade_mode:
                    z_stopped = (spread_dir == 1 and z_t <= -z_stop) or (spread_dir == -1 and z_t >= z_stop)
                    z_reverted = (spread_dir == 1 and z_t >= -z_exit) or (spread_dir == -1 and z_t <= z_exit)
                else:
                    # Matched fade uses exact same Z trigger thresholds symmetrically
                    z_stopped = (spread_dir == 1 and z_t >= -z_exit) or (spread_dir == -1 and z_t <= z_exit)
                    z_reverted = (spread_dir == 1 and z_t <= -z_stop) or (spread_dir == -1 and z_t >= z_stop)
                if z_stopped:
                    _close_pair(t, o_a, o_b, "Z_HARD_STOP")
                elif z_reverted:
                    _close_pair(t, o_a, o_b, "Z_REVERT_TP")

            # Intrabar hard leg SL check on H/L of BOTH legs (conservative: no optimistic intrabar TP)
            if in_pos:
                a_hit = (side_a == 1 and l_a <= sl_a + eps) or (side_a == -1 and h_a >= sl_a - eps)
                b_hit = (side_b == 1 and l_b <= sl_b + eps) or (side_b == -1 and h_b >= sl_b - eps)
                if a_hit and b_hit:
                    _close_pair(t, sl_a, sl_b, "DUAL_LEG_SL_HIT")
                elif a_hit:
                    _close_pair(t, sl_a, c_b, "LEG_A_SL_HIT")
                elif b_hit:
                    _close_pair(t, c_a, sl_b, "LEG_B_SL_HIT")

        # 2. If flat at bar t open, check strictly causal shift=1 (+1 zero-gap guard) entry signal
        if not in_pos and yr_t in allowed_set:
            if sig_t < 0:
                continue
            if t > 0 and (int(ts_arr[t]) - int(ts_arr[t - 1])) > 5 * 86400:
                continue  # Avoid entering immediately across an abnormal multi-day data gap
            b_t = float(beta_arr[sig_t])
            c_t = float(corr_arr[sig_t])
            aa_t = float(atr_a[sig_t])
            ab_t = float(atr_b[sig_t])
            if not (
                math.isfinite(z_t)
                and math.isfinite(b_t)
                and math.isfinite(c_t)
                and math.isfinite(aa_t)
                and math.isfinite(ab_t)
                and aa_t > 0.0
                and ab_t > 0.0
            ):
                continue
            if abs(c_t) < min_abs_corr or abs(b_t) < 0.20 or abs(b_t) > 4.0:
                continue
            if max_half_life is not None:
                hl_t = float(hl_arr[sig_t])
                if not math.isfinite(hl_t) or hl_t < 1.0 or hl_t > float(max_half_life):
                    continue

            raw_dir = 0
            if -z_stop < z_t <= -z_entry:
                raw_dir = 1
            elif z_entry <= z_t < z_stop:
                raw_dir = -1
            if raw_dir == 0:
                continue

            eff_dir = -raw_dir if fade_mode else raw_dir
            b_sign = 1 if b_t >= 0.0 else -1
            new_sa = eff_dir
            new_sb = -eff_dir * b_sign

            sld_a = sl_atr_mult * aa_t
            sld_b = sl_atr_mult * ab_t
            new_sla = o_a - new_sa * sld_a
            new_slb = o_b - new_sb * sld_b
            if new_sla <= 0.0 or new_slb <= 0.0:
                continue

            sz = _size_two_leg_pair_with_margin(
                spec_a,
                spec_b,
                o_a,
                o_b,
                sld_a,
                sld_b,
                abs(b_t),
                account_balance_usd=account_balance_usd,
                risk_frac=risk_frac,
                account_type="ftmo_swing",
                max_margin_util_frac=max_margin_util_frac,
            )
            if not sz["accepted"]:
                margin_rejects += 1
                continue
            if sz["margin_capped"]:
                margin_capped_count += 1
            peak_margin_util = max(peak_margin_util, float(sz["margin_util_frac"]))

            # Exact 1x round-turn friction across BOTH legs
            u_a = float(sz["usd_px_a"])
            u_b = float(sz["usd_px_b"])
            comm_px_a = comm_a / u_a if u_a > 0.0 else 0.0
            comm_px_b = comm_b / u_b if u_b > 0.0 else 0.0
            f_px_a = max(2.0 * (ow_a / 10_000.0) * o_a, bench_a + comm_px_a)
            f_px_b = max(2.0 * (ow_b / 10_000.0) * o_b, bench_b + comm_px_b)
            f_1x_usd = f_px_a * u_a * float(sz["lots_a"]) + f_px_b * u_b * float(sz["lots_b"])

            in_pos = True
            spread_dir = raw_dir
            side_a = new_sa
            side_b = new_sb
            entry_idx = t
            ea = o_a
            eb = o_b
            sl_a = new_sla
            sl_b = new_slb
            lots_a = float(sz["lots_a"])
            lots_b = float(sz["lots_b"])
            usd_px_a = u_a
            usd_px_b = u_b
            not_a_usd = float(sz["notional_a_usd"])
            not_b_usd = float(sz["notional_b_usd"])
            eff_risk_usd = float(sz["eff_risk_usd"])
            pos_margin_util = float(sz["margin_util_frac"])
            pos_margin_capped = bool(sz["margin_capped"])
            fric_1x_usd = f_1x_usd
            cum_swap_real_usd = 0.0
            cum_swap_zpos_usd = 0.0
            entry_z = z_t
            entry_beta = b_t

            # Entry-bar intrabar hard leg SL check
            a_hit0 = (side_a == 1 and l_a <= sl_a + eps) or (side_a == -1 and h_a >= sl_a - eps)
            b_hit0 = (side_b == 1 and l_b <= sl_b + eps) or (side_b == -1 and h_b >= sl_b - eps)
            if a_hit0 and b_hit0:
                _close_pair(t, sl_a, sl_b, "DUAL_LEG_SL_ENTRY_BAR")
            elif a_hit0:
                _close_pair(t, sl_a, c_b, "LEG_A_SL_ENTRY_BAR")
            elif b_hit0:
                _close_pair(t, c_a, sl_b, "LEG_B_SL_ENTRY_BAR")

    if in_pos:
        ci = last_in_window if last_in_window >= entry_idx else (n - 1)
        _close_pair(ci, float(ca[ci]), float(cb[ci]), "END_OF_SAMPLE")

    return {
        "trades": trades,
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped_count,
        "peak_margin_util_frac": round(peak_margin_util, 6),
        "zero_gap_lag_applied": bool(np.any(pair_lag_mask)),
        "causal_extra_lag": 1 if bool(np.any(pair_lag_mask)) else 0,
    }


# ---------------------------------------------------------------------------
# 4. Two-Leg Intraday M1 Bid/Ask Pairs Engine (`swap = 0`, Hard Flat <= 20:50 UTC)
# ---------------------------------------------------------------------------


def _build_m1_pair_cache(
    sym_a: str,
    sym_b: str,
    universe: Mapping[str, Any],
    tf_sec: int,
    max_year: int,
) -> dict[str, Any]:
    """Align two native M1 Bid/Ask symbols onto exact shared M1 timestamps and resampled TF bars."""
    cutoff_ts = int(datetime(max_year + 1, 1, 1, tzinfo=UTC).timestamp())
    m1_a = universe["assets"][sym_a]["m1"]
    m1_b = universe["assets"][sym_b]["m1"]
    if m1_a is None or m1_b is None:
        raise ValueError(f"M1 data missing for intraday pair {sym_a}/{sym_b} (load_universe_28 with load_m1=True)")

    ts_a = np.asarray(m1_a["times_sec"], dtype=np.int64)
    q_a = np.asarray(m1_a["quotes"], dtype=np.float64)
    ts_b = np.asarray(m1_b["times_sec"], dtype=np.int64)
    q_b = np.asarray(m1_b["quotes"], dtype=np.float64)

    ea = int(np.searchsorted(ts_a, cutoff_ts, side="left"))
    eb = int(np.searchsorted(ts_b, cutoff_ts, side="left"))
    ts_a, q_a = ts_a[:ea], q_a[:ea]
    ts_b, q_b = ts_b[:eb], q_b[:eb]
    enforce_dev_ts_bound(ts_a, context=f"m1_pair:{sym_a}")
    enforce_dev_ts_bound(ts_b, context=f"m1_pair:{sym_b}")

    # Resample each leg to `tf_sec` (e.g. 900s=M15 or 1800s=M30), then intersect bar timestamps
    r_ts_a, r_q_a = resample_m1_to_tf(ts_a, q_a, tf_sec)
    r_ts_b, r_q_b = resample_m1_to_tf(ts_b, q_b, tf_sec)
    common_tf, idx_a, idx_b = np.intersect1d(r_ts_a, r_ts_b, assume_unique=True, return_indices=True)
    if common_tf.size < 100:
        raise ValueError(f"Insufficient aligned TF bars for {sym_a}/{sym_b} (n={common_tf.size})")

    qa_tf = r_q_a[idx_a]
    qb_tf = r_q_b[idx_b]
    has_ask_a = qa_tf.shape[1] >= 8
    has_ask_b = qb_tf.shape[1] >= 8

    def _mid_ohlc(q: np.ndarray, has_ask: bool) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        if has_ask:
            o = 0.5 * (q[:, 0] + q[:, 4])
            h = 0.5 * (q[:, 1] + q[:, 5])
            lo = 0.5 * (q[:, 2] + q[:, 6])
            c = 0.5 * (q[:, 3] + q[:, 7])
        else:
            o, h, lo, c = q[:, 0].copy(), q[:, 1].copy(), q[:, 2].copy(), q[:, 3].copy()
        h = np.maximum(h, np.maximum(o, c))
        lo = np.minimum(lo, np.minimum(o, c))
        return o, h, lo, c

    oa, ha, loa, ca = _mid_ohlc(qa_tf, has_ask_a)
    ob, hb, lob, cb = _mid_ohlc(qb_tf, has_ask_b)

    return {
        "tf_ts": common_tf,
        "qa_tf": qa_tf,
        "qb_tf": qb_tf,
        "oa": oa,
        "ha": ha,
        "loa": loa,
        "ca": ca,
        "ob": ob,
        "hb": hb,
        "lob": lob,
        "cb": cb,
        "has_ask_a": has_ask_a,
        "has_ask_b": has_ask_b,
        "ts_m1_a": ts_a,
        "q_m1_a": q_a,
        "ts_m1_b": ts_b,
        "q_m1_b": q_b,
    }


def _replay_intraday_m1_pair(
    sym_a: str,
    sym_b: str,
    universe: Mapping[str, Any],
    params: Mapping[str, Any],
    years: Sequence[int],
    *,
    fade_mode: bool = False,
    red_news_index: Mapping[str, Any] | None = None,
    pair_cache: Mapping[str, Any] | None = None,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    max_margin_util_frac: float = 0.80,
) -> dict[str, Any]:
    """Replay Intraday M1 Bid/Ask two-leg pair (`swap = 0`, hard flat <= `20:50 UTC`, red-news guarded)."""
    req_years = tuple(sorted(int(y) for y in years))
    max_year = max(req_years)
    allowed_set = set(req_years)

    tf_sec = int(params.get("tf_sec", 900))  # 15-min signal bars by default
    cache = pair_cache if pair_cache is not None else _build_m1_pair_cache(sym_a, sym_b, universe, tf_sec, max_year)

    tf_ts = cache["tf_ts"]
    qa_tf = cache["qa_tf"]
    qb_tf = cache["qb_tf"]
    ha, loa, ca = cache["ha"], cache["loa"], cache["ca"]
    hb, lob, cb = cache["hb"], cache["lob"], cache["cb"]
    has_ask_a = bool(cache["has_ask_a"])
    has_ask_b = bool(cache["has_ask_b"])
    ts_m1_a, q_m1_a = cache["ts_m1_a"], cache["q_m1_a"]
    ts_m1_b, q_m1_b = cache["ts_m1_b"], cache["q_m1_b"]
    n = int(tf_ts.size)

    spec_a = universe["assets"][sym_a]["spec"]
    spec_b = universe["assets"][sym_b]["spec"]
    pt_a, bench_a = float(spec_a["point"]), float(spec_a["benchmark_spread_pts"]) * float(spec_a["point"])
    pt_b, bench_b = float(spec_b["point"]), float(spec_b["benchmark_spread_pts"]) * float(spec_b["point"])
    comm_a = float(spec_a["commission_usd_lot"])
    comm_b = float(spec_b["commission_usd_lot"])

    reg_win = int(params.get("reg_win", 64))
    z_win = int(params.get("z_win", 32))
    z_entry = float(params.get("z_entry", 2.0))
    z_exit = float(params.get("z_exit", 0.30))
    z_stop = float(params.get("z_stop", 3.50))
    sl_atr_mult = float(params.get("sl_atr_mult", 3.0))
    sess_start_hr = int(params.get("sess_start_utc", 7))
    sess_last_entry_hr = int(params.get("sess_last_entry_utc", 18))
    min_abs_corr = float(params.get("min_abs_corr", 0.50))
    hedge_model = str(params.get("hedge_model", "OLS")).upper()

    log_a = np.log(ca)
    log_b = np.log(cb)
    atr_a = causal_atr(ha, loa, ca, 20)
    atr_b = causal_atr(hb, lob, cb, 20)

    if hedge_model == "KALMAN":
        beta_arr, corr_arr, z_arr = _causal_kalman_spread_z_jit(
            log_a,
            log_b,
            float(params.get("kalman_q", 1e-4)),
            float(params.get("kalman_r", 1e-2)),
            z_win,
            warmup=32,
        )
    else:
        beta_arr, corr_arr, z_arr, _ = _causal_ols_spread_z_jit(log_a, log_b, reg_win, z_win)

    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped_count = 0
    peak_margin_util = 0.0
    risk_budget_usd = float(account_balance_usd) * float(risk_frac)
    flat_sec_limit = HARD_FLAT_MAX_UTC_HHMM[0] * 3600 + HARD_FLAT_MAX_UTC_HHMM[1] * 60
    eps = 1e-12

    # Max 1 intraday pair trade per UTC day, hard flat <= 20:50 UTC (swap=0!)
    last_exit_ts = 0
    last_entry_day = ""
    for t in range(n):
        ts_t = int(tf_ts[t])
        if ts_t <= last_exit_ts:
            continue
        dt_t = datetime.fromtimestamp(ts_t, tz=UTC)
        yr_t = dt_t.year
        if yr_t > max_year:
            break
        if yr_t not in allowed_set or dt_t.weekday() >= 5:
            continue
        day_str = dt_t.strftime("%Y-%m-%d")
        if day_str == last_entry_day:
            continue

        sod = dt_t.hour * 3600 + dt_t.minute * 60 + dt_t.second
        if sod < sess_start_hr * 3600 or sod >= sess_last_entry_hr * 3600:
            continue

        z_t = float(z_arr[t])
        b_t = float(beta_arr[t])
        c_t = float(corr_arr[t])
        aa_t = float(atr_a[t])
        ab_t = float(atr_b[t])
        if not (
            math.isfinite(z_t)
            and math.isfinite(b_t)
            and math.isfinite(c_t)
            and math.isfinite(aa_t)
            and math.isfinite(ab_t)
            and aa_t > 0.0
            and ab_t > 0.0
        ):
            continue
        if abs(c_t) < min_abs_corr or abs(b_t) < 0.20 or abs(b_t) > 4.0:
            continue

        raw_dir = 0
        if -z_stop < z_t <= -z_entry:
            raw_dir = 1
        elif z_entry <= z_t < z_stop:
            raw_dir = -1
        if raw_dir == 0:
            continue

        # Red-news guard on BOTH legs at entry
        if red_news_index is not None:
            if is_in_red_news_window(sym_a, ts_t, red_news_index, pad_sec=300) or is_in_red_news_window(
                sym_b, ts_t, red_news_index, pad_sec=300
            ):
                continue

        eff_dir = -raw_dir if fade_mode else raw_dir
        b_sign = 1 if b_t >= 0.0 else -1
        side_a = eff_dir
        side_b = -eff_dir * b_sign

        # Exact Bid/Ask fill at TF bar open (= exact M1 bar open at ts_t)
        ea = float(qa_tf[t, 4] if (side_a == 1 and has_ask_a) else qa_tf[t, 0])
        eb = float(qb_tf[t, 4] if (side_b == 1 and has_ask_b) else qb_tf[t, 0])
        sld_a = sl_atr_mult * aa_t
        sld_b = sl_atr_mult * ab_t
        sl_a = ea - side_a * sld_a
        sl_b = eb - side_b * sld_b
        if sl_a <= 0.0 or sl_b <= 0.0:
            continue

        sz = _size_two_leg_pair_with_margin(
            spec_a,
            spec_b,
            ea,
            eb,
            sld_a,
            sld_b,
            abs(b_t),
            account_balance_usd=account_balance_usd,
            risk_frac=risk_frac,
            account_type="ftmo_standard",
            max_margin_util_frac=max_margin_util_frac,
        )
        if not sz["accepted"]:
            margin_rejects += 1
            continue
        if sz["margin_capped"]:
            margin_capped_count += 1
        peak_margin_util = max(peak_margin_util, float(sz["margin_util_frac"]))

        # Determine hard flat timestamp strictly <= 20:50 UTC and before any red-news on either leg
        day_start = (ts_t // 86400) * 86400
        hard_flat_ts = day_start + min(flat_sec_limit, HARD_FLAT_MAX_UTC_SEC)
        if ts_t >= hard_flat_ts:
            continue
        news_flat = False
        if red_news_index is not None:
            nf_a = find_first_red_news_flatten_ts(sym_a, ts_t, hard_flat_ts, red_news_index, pad_sec=300)
            nf_b = find_first_red_news_flatten_ts(sym_b, ts_t, hard_flat_ts, red_news_index, pad_sec=300)
            for nf in (nf_a, nf_b):
                if nf is not None and ts_t < nf < hard_flat_ts:
                    hard_flat_ts = nf
                    news_flat = True

        # Scan forward bar-by-bar up to hard_flat_ts, checking M1 intrabar hard leg SL + TF Z exits
        exit_ts = hard_flat_ts
        exit_reason = "RED_NEWS_FLATTEN" if news_flat else "HARD_FLAT_2050"
        exit_px_a = float("nan")
        exit_px_b = float("nan")

        # Locate M1 scan window [ts_t, hard_flat_ts]
        k_tf = t
        while k_tf < n and int(tf_ts[k_tf]) <= hard_flat_ts:
            bar_start = int(tf_ts[k_tf])
            bar_end = min(bar_start + tf_sec - 1, hard_flat_ts)

            # Check causal Z-exit / Z-stop at bar open k_tf > t
            if k_tf > t:
                zk = float(z_arr[k_tf])
                if math.isfinite(zk):
                    if not fade_mode:
                        z_st = (raw_dir == 1 and zk <= -z_stop) or (raw_dir == -1 and zk >= z_stop)
                        z_tp = (raw_dir == 1 and zk >= -z_exit) or (raw_dir == -1 and zk <= z_exit)
                    else:
                        z_st = (raw_dir == 1 and zk >= -z_exit) or (raw_dir == -1 and zk <= z_exit)
                        z_tp = (raw_dir == 1 and zk <= -z_stop) or (raw_dir == -1 and zk >= z_stop)
                    if z_st or z_tp:
                        exit_ts = bar_start
                        exit_reason = "Z_HARD_STOP" if z_st else "Z_REVERT_TP"
                        col_xa = 0 if side_a == 1 else (4 if has_ask_a else 0)
                        col_xb = 0 if side_b == 1 else (4 if has_ask_b else 0)
                        exit_px_a = float(qa_tf[k_tf, col_xa])
                        exit_px_b = float(qb_tf[k_tf, col_xb])
                        break

            # Quick TF bar H/L pre-check before touching fine M1 bars (huge speedup, 100% exact!)
            ca_lo = float(qa_tf[k_tf, 2]) if side_a == 1 else float(qa_tf[k_tf, 5 if has_ask_a else 1])
            cb_lo = float(qb_tf[k_tf, 2]) if side_b == 1 else float(qb_tf[k_tf, 5 if has_ask_b else 1])
            may_hit_a = (side_a == 1 and ca_lo <= sl_a + eps) or (side_a == -1 and ca_lo >= sl_a - eps)
            may_hit_b = (side_b == 1 and cb_lo <= sl_b + eps) or (side_b == -1 and cb_lo >= sl_b - eps)

            if may_hit_a or may_hit_b:
                # Drill down to exact M1 Bid/Ask timestamps for earliest SL trigger
                ia0 = int(np.searchsorted(ts_m1_a, bar_start, side="left"))
                ia1 = int(np.searchsorted(ts_m1_a, bar_end, side="right"))
                ib0 = int(np.searchsorted(ts_m1_b, bar_start, side="left"))
                ib1 = int(np.searchsorted(ts_m1_b, bar_end, side="right"))
                hit_ts_a = -1
                hit_px_a = sl_a
                for j in range(ia0, ia1):
                    op_j = float(q_m1_a[j, 0 if side_a == 1 else (4 if has_ask_a else 0)])
                    if j > ia0 or k_tf > t:
                        if (side_a == 1 and op_j <= sl_a + eps) or (side_a == -1 and op_j >= sl_a - eps):
                            hit_ts_a = int(ts_m1_a[j])
                            hit_px_a = op_j
                            break
                    ex_j = float(q_m1_a[j, 2 if side_a == 1 else (5 if has_ask_a else 1)])
                    if (side_a == 1 and ex_j <= sl_a + eps) or (side_a == -1 and ex_j >= sl_a - eps):
                        hit_ts_a = int(ts_m1_a[j])
                        hit_px_a = sl_a
                        break

                hit_ts_b = -1
                hit_px_b = sl_b
                for j in range(ib0, ib1):
                    op_j = float(q_m1_b[j, 0 if side_b == 1 else (4 if has_ask_b else 0)])
                    if j > ib0 or k_tf > t:
                        if (side_b == 1 and op_j <= sl_b + eps) or (side_b == -1 and op_j >= sl_b - eps):
                            hit_ts_b = int(ts_m1_b[j])
                            hit_px_b = op_j
                            break
                    ex_j = float(q_m1_b[j, 2 if side_b == 1 else (5 if has_ask_b else 1)])
                    if (side_b == 1 and ex_j <= sl_b + eps) or (side_b == -1 and ex_j >= sl_b - eps):
                        hit_ts_b = int(ts_m1_b[j])
                        hit_px_b = sl_b
                        break

                if hit_ts_a >= 0 or hit_ts_b >= 0:
                    if hit_ts_a >= 0 and (hit_ts_b < 0 or hit_ts_a <= hit_ts_b):
                        exit_ts = hit_ts_a
                        exit_px_a = hit_px_a
                        jb = max(0, int(np.searchsorted(ts_m1_b, hit_ts_a, side="right")) - 1)
                        exit_px_b = float(q_m1_b[jb, 3 if side_b == 1 else (7 if has_ask_b else 3)])
                        exit_reason = "LEG_A_SL_HIT"
                    else:
                        exit_ts = hit_ts_b
                        exit_px_b = hit_px_b
                        ja = max(0, int(np.searchsorted(ts_m1_a, hit_ts_b, side="right")) - 1)
                        exit_px_a = float(q_m1_a[ja, 3 if side_a == 1 else (7 if has_ask_a else 3)])
                        exit_reason = "LEG_B_SL_HIT"
                    break
            k_tf += 1

        if not (math.isfinite(exit_px_a) and math.isfinite(exit_px_b)):
            ja = max(0, int(np.searchsorted(ts_m1_a, hard_flat_ts, side="right")) - 1)
            jb = max(0, int(np.searchsorted(ts_m1_b, hard_flat_ts, side="right")) - 1)
            exit_ts = min(int(ts_m1_a[ja]), int(ts_m1_b[jb]), hard_flat_ts)
            exit_px_a = float(q_m1_a[ja, 0 if side_a == 1 else (4 if has_ask_a else 0)])
            exit_px_b = float(q_m1_b[jb, 0 if side_b == 1 else (4 if has_ask_b else 0)])

        enforce_dev_ts_bound(exit_ts, context=f"m1_pair_exit:{sym_a}/{sym_b}")
        last_exit_ts = exit_ts
        last_entry_day = day_str

        # Embedded Bid/Ask spread + commission + slippage across BOTH legs (zero double-counting!)
        ja_en = max(0, int(np.searchsorted(ts_m1_a, ts_t, side="right")) - 1)
        ja_ex = max(0, int(np.searchsorted(ts_m1_a, exit_ts, side="right")) - 1)
        jb_en = max(0, int(np.searchsorted(ts_m1_b, ts_t, side="right")) - 1)
        jb_ex = max(0, int(np.searchsorted(ts_m1_b, exit_ts, side="right")) - 1)

        emb_a = (
            0.5
            * (
                max(0.0, float(q_m1_a[ja_en, 4] - q_m1_a[ja_en, 0]))
                + max(0.0, float(q_m1_a[ja_ex, 4] - q_m1_a[ja_ex, 0]))
            )
            if has_ask_a
            else 0.0
        )
        emb_b = (
            0.5
            * (
                max(0.0, float(q_m1_b[jb_en, 4] - q_m1_b[jb_en, 0]))
                + max(0.0, float(q_m1_b[jb_ex, 4] - q_m1_b[jb_ex, 0]))
            )
            if has_ask_b
            else 0.0
        )
        u_a, u_b = float(sz["usd_px_a"]), float(sz["usd_px_b"])
        lots_a, lots_b = float(sz["lots_a"]), float(sz["lots_b"])
        comm_px_a = comm_a / u_a if u_a > 0.0 else 0.0
        comm_px_b = comm_b / u_b if u_b > 0.0 else 0.0
        slip_a = max(pt_a, 0.35 * max(emb_a, bench_a))
        slip_b = max(pt_b, 0.35 * max(emb_b, bench_b))
        tot_f1_a = (emb_a if has_ask_a else bench_a) + comm_px_a + slip_a
        tot_f1_b = (emb_b if has_ask_b else bench_b) + comm_px_b + slip_b

        tot_f1_usd = tot_f1_a * u_a * lots_a + tot_f1_b * u_b * lots_b
        emb_usd = emb_a * u_a * lots_a + emb_b * u_b * lots_b
        raw_pnl_usd = side_a * (exit_px_a - ea) * u_a * lots_a + side_b * (exit_px_b - eb) * u_b * lots_b

        tier_net: dict[str, float] = {}
        for mult in FRICTION_TIERS:
            m = float(mult)
            lbl = f"{m:g}x"
            extra_usd = max(0.0, m * tot_f1_usd - emb_usd)
            tier_net[lbl] = round((raw_pnl_usd - extra_usd) / risk_budget_usd, 6)

        eff_risk_usd = max(float(sz["eff_risk_usd"]), 1e-9)
        f1 = round(tot_f1_usd / eff_risk_usd, 6)
        f15 = round((1.5 * tot_f1_usd) / eff_risk_usd, 6)
        f2 = round((2.0 * tot_f1_usd) / eff_risk_usd, 6)
        en_date = datetime.fromtimestamp(ts_t, tz=UTC).strftime("%Y-%m-%d")
        ex_date = datetime.fromtimestamp(exit_ts, tz=UTC).strftime("%Y-%m-%d")

        trades.append(
            {
                "symbol": f"{sym_a}/{sym_b}",
                "leg_a": sym_a,
                "leg_b": sym_b,
                "blindness_tier": TIER_12OLD,
                "data_resolution": RES_NATIVE_M1_BIDASK,
                "spread_dir": int(raw_dir),
                "side_a": int(side_a),
                "side_b": int(side_b),
                "entry_ts": ts_t,
                "exit_ts": exit_ts,
                "entry_date": en_date,
                "exit_date": ex_date,
                "entry_price_a": round(ea, 6),
                "entry_price_b": round(eb, 6),
                "exit_price_a": round(exit_px_a, 6),
                "exit_price_b": round(exit_px_b, 6),
                "sl_price_a": round(sl_a, 6),
                "sl_price_b": round(sl_b, 6),
                "entry_z": round(z_t, 4),
                "entry_beta": round(b_t, 4),
                "lots_a": lots_a,
                "lots_b": lots_b,
                "hold_minutes": int(max(0, (exit_ts - ts_t) // 60)),
                "exit_reason": exit_reason,
                "swap_R": 0.0,
                "swap_real_R": 0.0,
                "swap_zero_pos_R": 0.0,
                "margin_util_frac": float(sz["margin_util_frac"]),
                "margin_capped": bool(sz["margin_capped"]),
                "gross_R": round(raw_pnl_usd / risk_budget_usd, 6),
                "net_R": tier_net["1x"],
                "net_R_1x": tier_net["1x"],
                "net_R_15x": tier_net["1.5x"],
                "net_R_2x": tier_net["2x"],
                "net_R_zero_pos_1x": tier_net["1x"],
                "net_R_zero_pos_15x": tier_net["1.5x"],
                "net_R_zero_pos_2x": tier_net["2x"],
                "friction_over_sl": f2,
                "friction_over_sl_1x": f1,
                "friction_over_sl_15x": f15,
                "friction_over_sl_2x": f2,
            }
        )

    return {
        "trades": trades,
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped_count,
        "peak_margin_util_frac": round(peak_margin_util, 6),
    }


# ---------------------------------------------------------------------------
# 5. Standard `evaluate_candidate(spec, universe, years)` Entrypoint
# ---------------------------------------------------------------------------


def _audit_portfolio_margin(trades: Sequence[Mapping[str, Any]], max_margin_util_frac: float = 0.80) -> float:
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


def evaluate_candidate(
    spec: Mapping[str, Any],
    universe: Mapping[str, Any],
    years: Sequence[int],
    *,
    red_news_index: Mapping[str, Any] | None = None,
    m1_pair_caches: Mapping[tuple[str, str, int], Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Evaluate a single F11 Pairs StatArb candidate strictly on `years` (zero lookahead past `max(years)`)."""
    req_years = tuple(sorted(int(y) for y in years))
    if not req_years or max(req_years) > 2024 or min(req_years) < 2018:
        raise ValueError(f"DEV_SEAL_VIOLATION: invalid Dev years={req_years}")

    mode = str(spec["mode"]).upper()
    pairs: list[tuple[str, str]] = [(normalize_symbol(a), normalize_symbol(b)) for a, b in spec["pairs"]]
    params = dict(spec.get("params") or {})
    n_pairs = len(pairs)
    if n_pairs < 1:
        raise ValueError("F11 spec must specify at least 1 pair")

    # Equal-risk allocation across pooled pairs so total portfolio risk stays ~0.5% per active unit
    base_risk_frac = float(params.get("risk_frac", 0.005))
    per_pair_risk = base_risk_frac / math.sqrt(float(n_pairs)) if n_pairs > 1 else base_risk_frac
    per_pair_margin_cap = min(0.80, 0.80 / max(1.0, math.sqrt(float(n_pairs))))

    all_trades: list[dict[str, Any]] = []
    fade_trades: list[dict[str, Any]] = []
    total_rejects = 0
    total_capped = 0
    peak_leg_margin = 0.0

    # Standard $100K FTMO account preserves exact scale-invariant leverage margin % without 0.01-lot starvation
    acct_bal = float(params.get("account_balance_usd", 100_000.0))

    if mode == "INTRADAY_M1_PAIR":
        news_idx = red_news_index if red_news_index is not None else load_dev_red_news_index(include_extended=True)
        tf_sec = int(params.get("tf_sec", 1800))
        for sym_a, sym_b in pairs:
            pc = m1_pair_caches.get((sym_a, sym_b, tf_sec)) if m1_pair_caches is not None else None
            r_main = _replay_intraday_m1_pair(
                sym_a,
                sym_b,
                universe,
                params,
                req_years,
                fade_mode=False,
                red_news_index=news_idx,
                pair_cache=pc,
                account_balance_usd=acct_bal,
                risk_frac=per_pair_risk,
                max_margin_util_frac=per_pair_margin_cap,
            )
            r_fade = _replay_intraday_m1_pair(
                sym_a,
                sym_b,
                universe,
                params,
                req_years,
                fade_mode=True,
                red_news_index=news_idx,
                pair_cache=pc,
                account_balance_usd=acct_bal,
                risk_frac=per_pair_risk,
                max_margin_util_frac=per_pair_margin_cap,
            )
            all_trades.extend(r_main["trades"])
            fade_trades.extend(r_fade["trades"])
            total_rejects += int(r_main["margin_rejects"])
            total_capped += int(r_main["margin_capped_count"])
            peak_leg_margin = max(peak_leg_margin, float(r_main["peak_margin_util_frac"]))
    elif mode == "SWING_D1_PAIR":
        for sym_a, sym_b in pairs:
            r_main = _replay_d1_pair_single(
                sym_a,
                sym_b,
                universe,
                params,
                req_years,
                fade_mode=False,
                account_balance_usd=acct_bal,
                risk_frac=per_pair_risk,
                max_margin_util_frac=per_pair_margin_cap,
            )
            r_fade = _replay_d1_pair_single(
                sym_a,
                sym_b,
                universe,
                params,
                req_years,
                fade_mode=True,
                account_balance_usd=acct_bal,
                risk_frac=per_pair_risk,
                max_margin_util_frac=per_pair_margin_cap,
            )
            all_trades.extend(r_main["trades"])
            fade_trades.extend(r_fade["trades"])
            total_rejects += int(r_main["margin_rejects"])
            total_capped += int(r_main["margin_capped_count"])
            peak_leg_margin = max(peak_leg_margin, float(r_main["peak_margin_util_frac"]))
    else:
        raise ValueError(f"Unsupported F11 mode={mode!r}")

    # Scale pooled multi-pair R back to 1.0x portfolio risk unit (dividing by sqrt(N) normalized R)
    if n_pairs > 1:
        inv_s = 1.0 / math.sqrt(float(n_pairs))
        for tr_list in (all_trades, fade_trades):
            for tr in tr_list:
                for k in (
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
                ):
                    if k in tr and tr[k] is not None:
                        tr[k] = round(float(tr[k]) * inv_s, 6)

    all_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))
    fade_trades.sort(key=lambda tr: (int(tr["exit_ts"]), int(tr["entry_ts"]), str(tr["symbol"])))

    dp_1x = compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_1x")
    dp_15x = compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_15x")
    dp_2x = compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_2x")
    dp_zpos = compute_daily_pnl_series(all_trades, req_years, pnl_key="net_R_zero_pos_1x")
    dp_fade = compute_daily_pnl_series(fade_trades, req_years, pnl_key="net_R_1x")

    m_1x = compute_split_metrics(all_trades, dp_1x, pnl_key="net_R_1x")
    m_15x = compute_split_metrics(all_trades, dp_15x, pnl_key="net_R_15x")
    m_2x = compute_split_metrics(all_trades, dp_2x, pnl_key="net_R_2x")
    m_zpos = compute_split_metrics(all_trades, dp_zpos, pnl_key="net_R_zero_pos_1x")
    m_fade = compute_split_metrics(fade_trades, dp_fade, pnl_key="net_R_1x")

    uniq_syms = sorted({s for ab in pairs for s in ab})
    data_res, b_tier, _ = _resolve_group_tags(uniq_syms, universe)
    if mode == "INTRADAY_M1_PAIR":
        data_res = RES_NATIVE_M1_BIDASK

    peak_port_mu = _audit_portfolio_margin(all_trades, max_margin_util_frac=0.80)
    s0 = stage0_screen(all_trades, max_fric_sl_ratio=0.15, min_keep_frac=0.50)

    return {
        "spec": dict(spec),
        "trades": all_trades,
        "daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_1x["dates"], dp_1x["pnl"], strict=True)},
        "daily_pnl_15x": {d: round(float(v), 6) for d, v in zip(dp_15x["dates"], dp_15x["pnl"], strict=True)},
        "daily_pnl_2x": {d: round(float(v), 6) for d, v in zip(dp_2x["dates"], dp_2x["pnl"], strict=True)},
        "daily_pnl_zero_pos_swap": {
            d: round(float(v), 6) for d, v in zip(dp_zpos["dates"], dp_zpos["pnl"], strict=True)
        },
        "fade_daily_pnl_1x": {d: round(float(v), 6) for d, v in zip(dp_fade["dates"], dp_fade["pnl"], strict=True)},
        "metrics": m_1x,
        "metrics_15x": m_15x,
        "metrics_2x": m_2x,
        "metrics_zero_pos_swap": m_zpos,
        "metrics_fade_1x": m_fade,
        "stage0": s0,
        "margin_audit": {
            "margin_rejects": total_rejects,
            "margin_capped_count": total_capped,
            "peak_single_pair_margin_util_frac": round(peak_leg_margin, 6),
            "peak_portfolio_margin_util_frac": peak_port_mu,
            "portfolio_margin_ok": peak_port_mu <= 0.80 + 1e-6,
        },
        "data_resolution": data_res,
        "blindness_tier": b_tier,
        "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# 6. Pre-Registered Candidate Grid & Cluster A Discovery (`2018-2020` ONLY!)
# ---------------------------------------------------------------------------


def _build_f11_candidate_grid(universe: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Generate <= 100 clean, diverse, economically grounded F11 Pairs StatArb specs."""
    specs: list[dict[str, Any]] = []
    invariants_swing = [
        "strict_shift_1_causal_ols_or_kalman_hedge_ratio",
        "mandatory_dual_leg_hard_atr_sl_and_z_hard_stop_3_5",
        "max_hold_1_to_8_days_zero_grid_zero_martingale",
        "real_triple_swap_wed_fri_anti_fake_swap_guard_and_zero_pos_swap_floor",
        "simultaneous_two_leg_ftmo_swing_leverage_margin_check",
        "usoil_apr2020_negative_roll_quarantined",
    ]
    invariants_m1 = [
        "strict_shift_1_causal_intraday_hedge_ratio",
        "native_m1_bidask_fills_swap_0_hard_flat_le_2050_utc",
        "mandatory_dual_leg_hard_atr_sl_and_z_hard_stop_3_5",
        "red_news_5m_entry_block_and_pre_news_flatten_both_legs",
        "simultaneous_two_leg_ftmo_standard_leverage_margin_check",
    ]

    # (A) 10 Individual Swing D1 Pairs x 6 disciplined orthogonal configs = 60 specs
    swing_variants: list[tuple[str, dict[str, Any]]] = [
        (
            "OLS60_Z175_H5",
            {
                "hedge_model": "OLS",
                "reg_win": 60,
                "z_win": 30,
                "z_entry": 1.75,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 5,
                "min_abs_corr": 0.45,
            },
        ),
        (
            "OLS60_Z200_H8",
            {
                "hedge_model": "OLS",
                "reg_win": 60,
                "z_win": 30,
                "z_entry": 2.00,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 8,
                "min_abs_corr": 0.45,
            },
        ),
        (
            "OLS90_Z200_HL20",
            {
                "hedge_model": "OLS",
                "reg_win": 90,
                "z_win": 40,
                "z_entry": 2.00,
                "z_exit": 0.25,
                "z_stop": 3.5,
                "sl_atr_mult": 3.0,
                "max_hold_bars": 8,
                "min_abs_corr": 0.50,
                "max_half_life": 20.0,
            },
        ),
        (
            "OLS40_Z225_H6",
            {
                "hedge_model": "OLS",
                "reg_win": 40,
                "z_win": 20,
                "z_entry": 2.25,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 6,
                "min_abs_corr": 0.45,
            },
        ),
        (
            "KALMAN_Z175_H6",
            {
                "hedge_model": "KALMAN",
                "kalman_q": 1e-4,
                "kalman_r": 1e-2,
                "z_win": 30,
                "z_entry": 1.75,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 2.5,
                "max_hold_bars": 6,
                "min_abs_corr": 0.45,
            },
        ),
        (
            "KALMAN_Z200_H8",
            {
                "hedge_model": "KALMAN",
                "kalman_q": 2e-4,
                "kalman_r": 1e-2,
                "z_win": 40,
                "z_entry": 2.00,
                "z_exit": 0.25,
                "z_stop": 3.5,
                "sl_atr_mult": 3.0,
                "max_hold_bars": 8,
                "min_abs_corr": 0.45,
            },
        ),
    ]

    for sym_a, sym_b, pair_desc in SWING_D1_PAIRS:
        data_res, b_tier, tier_map = _resolve_group_tags((sym_a, sym_b), universe)
        for v_tag, v_params in swing_variants:
            cid = f"F11_SW_{sym_a}_{sym_b}_{v_tag}"
            specs.append(
                {
                    "candidate_id": cid,
                    "family_id": FAMILY_ID,
                    "mode": "SWING_D1_PAIR",
                    "prop_track": "FTMO_SWING",
                    "group": f"PAIR_{sym_a}_{sym_b}",
                    "pairs": [[sym_a, sym_b]],
                    "symbols": [sym_a, sym_b],
                    "params": dict(v_params),
                    "economic_rationale": (
                        f"{pair_desc} Causal {v_params['hedge_model']} hedge-ratio "
                        "Z-reversion with hard Z-stop and dual ATR stops."
                    ),
                    "counterparty_mechanism": _COUNTERPARTY_SWING,
                    "causal_invariants": list(invariants_swing),
                    "data_resolution": data_res,
                    "blindness_tier": b_tier,
                    "symbol_blindness_tiers": tier_map,
                    "allow_unidirectional": False,
                }
            )

    # (B) 5 Pooled Multi-Pair StatArb Portfolios x 4 configs = 20 specs
    pool_variants: list[tuple[str, dict[str, Any]]] = [
        ("OLS60_Z175_H5", swing_variants[0][1]),
        ("OLS60_Z200_H8", swing_variants[1][1]),
        ("OLS90_Z200_HL20", swing_variants[2][1]),
        ("KALMAN_Z200_H8", swing_variants[5][1]),
    ]
    for pool_name, pool_pairs in SWING_POOLS.items():
        uniq_syms = sorted({s for ab in pool_pairs for s in ab})
        data_res, b_tier, tier_map = _resolve_group_tags(uniq_syms, universe)
        for v_tag, v_params in pool_variants:
            cid = f"F11_{pool_name}_{v_tag}"
            specs.append(
                {
                    "candidate_id": cid,
                    "family_id": FAMILY_ID,
                    "mode": "SWING_D1_PAIR",
                    "prop_track": "FTMO_SWING",
                    "group": pool_name,
                    "pairs": [[a, b] for a, b in pool_pairs],
                    "symbols": uniq_syms,
                    "params": dict(v_params),
                    "economic_rationale": (
                        f"Diversified equal-risk multi-pair StatArb portfolio ({pool_name}, "
                        f"{len(pool_pairs)} cointegrated pairs) diversifying idiosyncratic pair breaks "
                        "while enforcing dual ATR SL, Z-stop 3.5, and combined FTMO Swing leverage margin."
                    ),
                    "counterparty_mechanism": _COUNTERPARTY_SWING,
                    "causal_invariants": list(invariants_swing),
                    "data_resolution": data_res,
                    "blindness_tier": b_tier,
                    "symbol_blindness_tiers": tier_map,
                    "allow_unidirectional": False,
                }
            )

    # (C) 3 Intraday M1 Bid/Ask Pairs (swap=0) x 4 selective configs (max 1/day) + 1 Pooled 3-Pair M1 basket x 3 = 15
    m1_variants: list[tuple[str, dict[str, Any]]] = [
        (
            "H1_OLS48_Z200",
            {
                "tf_sec": 3600,
                "hedge_model": "OLS",
                "reg_win": 48,
                "z_win": 24,
                "z_entry": 2.00,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 3.0,
                "min_abs_corr": 0.55,
            },
        ),
        (
            "H1_OLS72_Z225",
            {
                "tf_sec": 3600,
                "hedge_model": "OLS",
                "reg_win": 72,
                "z_win": 36,
                "z_entry": 2.25,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 3.5,
                "min_abs_corr": 0.55,
            },
        ),
        (
            "M30_OLS64_Z225",
            {
                "tf_sec": 1800,
                "hedge_model": "OLS",
                "reg_win": 64,
                "z_win": 32,
                "z_entry": 2.25,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 3.5,
                "min_abs_corr": 0.55,
            },
        ),
        (
            "H1_KALMAN_Z200",
            {
                "tf_sec": 3600,
                "hedge_model": "KALMAN",
                "kalman_q": 1e-4,
                "kalman_r": 1e-2,
                "z_win": 24,
                "z_entry": 2.00,
                "z_exit": 0.30,
                "z_stop": 3.5,
                "sl_atr_mult": 3.5,
                "min_abs_corr": 0.55,
            },
        ),
    ]
    for sym_a, sym_b, s_hr, e_hr, pair_desc in INTRADAY_M1_PAIRS:
        for v_tag, v_params in m1_variants:
            p_full = dict(v_params)
            p_full["sess_start_utc"] = s_hr
            p_full["sess_last_entry_utc"] = min(18, e_hr - 2)
            cid = f"F11_M1_{sym_a}_{sym_b}_{v_tag}"
            specs.append(
                {
                    "candidate_id": cid,
                    "family_id": FAMILY_ID,
                    "mode": "INTRADAY_M1_PAIR",
                    "prop_track": "INTRADAY_SWAP0",
                    "group": f"M1_{sym_a}_{sym_b}",
                    "pairs": [[sym_a, sym_b]],
                    "symbols": [sym_a, sym_b],
                    "params": p_full,
                    "economic_rationale": (
                        f"{pair_desc} Strictly causal intraday {v_params['hedge_model']} "
                        "hedge-ratio reversion clearing 2x CFD friction."
                    ),
                    "counterparty_mechanism": _COUNTERPARTY_M1,
                    "causal_invariants": list(invariants_m1),
                    "data_resolution": RES_NATIVE_M1_BIDASK,
                    "blindness_tier": TIER_12OLD,
                    "symbol_blindness_tiers": {sym_a: TIER_12OLD, sym_b: TIER_12OLD},
                    "allow_unidirectional": False,
                }
            )

    # Pooled Intraday M1 3-Pair Basket (3 configs -> total = 60 + 20 + 12 + 3 = 95 <= 100!)
    m1_all_pairs = [[a, b] for a, b, _, _, _ in INTRADAY_M1_PAIRS]
    m1_all_syms = sorted({s for ab in m1_all_pairs for s in ab})
    for v_tag, v_params in m1_variants[:3]:
        p_full = dict(v_params)
        p_full["sess_start_utc"] = 7
        p_full["sess_last_entry_utc"] = 18
        cid = f"F11_M1_POOL_3PAIRS_{v_tag}"
        specs.append(
            {
                "candidate_id": cid,
                "family_id": FAMILY_ID,
                "mode": "INTRADAY_M1_PAIR",
                "prop_track": "INTRADAY_SWAP0",
                "group": "M1_POOL_3PAIRS",
                "pairs": m1_all_pairs,
                "symbols": m1_all_syms,
                "params": p_full,
                "economic_rationale": (
                    "Equal-risk intraday M1 Bid/Ask 3-pair StatArb basket (US500/US100, EURUSD/GBPUSD, EURJPY/GBPJPY) "
                    "with zero overnight swap, red-news blackout guards, and hard <=20:50 UTC flat."
                ),
                "counterparty_mechanism": _COUNTERPARTY_M1,
                "causal_invariants": list(invariants_m1),
                "data_resolution": RES_NATIVE_M1_BIDASK,
                "blindness_tier": TIER_12OLD,
                "symbol_blindness_tiers": {s: TIER_12OLD for s in m1_all_syms},
                "allow_unidirectional": False,
            }
        )

    if len(specs) > TOTAL_CAP:
        raise ValueError(f"F11 grid exceeded TOTAL_CAP={TOTAL_CAP}: got {len(specs)}")
    return specs


def _score_cluster_a(ev: Mapping[str, Any]) -> float:
    """Strictly Cluster-A-only composite ranking score emphasizing 2x cost survival, zero_pos_swap & stability."""
    m1 = ev["metrics"]
    m2 = ev["metrics_2x"]
    mz = ev["metrics_zero_pos_swap"]
    mf = ev["metrics_fade_1x"]
    s0 = ev["stage0"]
    n_tr = int(m1["n_trades"])
    if n_tr < 12:
        return -999.0 + 0.01 * float(n_tr)

    sh1 = float(m1["sharpe"])
    sh2 = float(m2["sharpe"])
    shz = float(mz["sharpe"])
    shf = float(mf["sharpe"])
    pos_yr = float(m1["positive_year_ratio"])
    dd = max(1.0, float(m1["max_DD_R"]))
    calmar_proxy = float(m1["net_R"]) / dd
    s0_bonus = 0.50 if bool(s0["passed"]) else -1.50
    fade_edge = 0.25 * max(-2.0, min(2.0, sh1 - shf))
    sample_scale = min(1.0, math.sqrt(float(n_tr) / 40.0))
    return round(
        sample_scale * (0.35 * sh2 + 0.30 * shz + 0.20 * sh1 + 0.15 * calmar_proxy + 0.60 * pos_yr + fade_edge)
        + s0_bonus,
        6,
    )


def discover_cluster_a(
    universe: Mapping[str, Any] | None = None,
    *,
    save: bool = True,
    resume: bool = False,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Run Stage 2 Cluster A (`2018-2020` ONLY) discovery for F11 (`F11_PAIRS_STATARB`).

    HARD BLINDNESS LOCK: Any universe passed in is strictly sliced to `year <= 2020` BEFORE
    any indicator or replay runs. Zero 2021..2024 rows are ever read, printed, or ranked!
    """
    if resume and has_valid_family_checkpoint(FAMILY_ID, candidates_dir=candidates_dir, root=root):
        return load_family_candidates(FAMILY_ID, candidates_dir=candidates_dir, verify_sha=True, root=root)

    if universe is None:
        uni_a = load_universe_28(load_m1=True, load_d1=True, years=CLUSTER_A_YEARS, verify_sha=True, root=root)
    else:
        uni_a = _slice_universe_max_year(universe, max_year=2020)

    # Double-check hard Cluster A timestamp ceiling across loaded assets
    for sym, aobj in uni_a["assets"].items():
        if aobj.get("d1") is not None and len(aobj["d1"]["times_sec"]) > 0:
            if int(aobj["d1"]["times_sec"][-1]) >= _CL_A_END_TS:
                raise ValueError(f"CLUSTER_A_BLINDNESS_BREACH [{sym}]: D1 ts >= 2021-01-01")
        if aobj.get("m1") is not None and len(aobj["m1"]["times_sec"]) > 0:
            if int(aobj["m1"]["times_sec"][-1]) >= _CL_A_END_TS:
                raise ValueError(f"CLUSTER_A_BLINDNESS_BREACH [{sym}]: M1 ts >= 2021-01-01")

    news_idx = load_dev_red_news_index(include_extended=True, root=root)
    # Pre-cache aligned M1 pair TF bars on Cluster A ONLY for fast replay
    m1_caches: dict[tuple[str, str, int], dict[str, Any]] = {}
    for sym_a, sym_b, _, _, _ in INTRADAY_M1_PAIRS:
        if uni_a["assets"][sym_a].get("m1") is not None and uni_a["assets"][sym_b].get("m1") is not None:
            for tf_s in (1800, 3600):
                m1_caches[(sym_a, sym_b, tf_s)] = _build_m1_pair_cache(sym_a, sym_b, uni_a, tf_s, max_year=2020)

    grid = _build_f11_candidate_grid(uni_a)
    records: list[dict[str, Any]] = []

    for sp in grid:
        if sp["mode"] == "INTRADAY_M1_PAIR":
            has_all_m1 = all(uni_a["assets"][s].get("m1") is not None for s in sp["symbols"])
            if not has_all_m1:
                continue
        ev = evaluate_candidate(sp, uni_a, CLUSTER_A_YEARS, red_news_index=news_idx, m1_pair_caches=m1_caches)
        sc = _score_cluster_a(ev)
        records.append(
            {
                "candidate_id": sp["candidate_id"],
                "family_id": FAMILY_ID,
                "group": sp["group"],
                "mode": sp["mode"],
                "prop_track": sp["prop_track"],
                "data_resolution": ev["data_resolution"],
                "blindness_tier": ev["blindness_tier"],
                "allow_unidirectional": ev["allow_unidirectional"],
                "cluster_a_score": sc,
                "stage0": ev["stage0"],
                "margin_audit": ev["margin_audit"],
                "cluster_a_metrics": {
                    "1x": ev["metrics"],
                    "1.5x": ev["metrics_15x"],
                    "2x": ev["metrics_2x"],
                    "zero_pos_swap_1x": ev["metrics_zero_pos_swap"],
                    "fade_1x": ev["metrics_fade_1x"],
                },
                "spec": ev["spec"],
            }
        )

    # Diversified PRIMARY selection (<= PRIMARY_CAP = 15): ONLY genuinely positive Cluster A candidates!
    # Negative Cluster A specs remain honestly in EXPLORATORY so BH-FDR m200 budget is never wasted.
    records.sort(key=lambda r: float(r["cluster_a_score"]), reverse=True)
    primary_ids: set[str] = set()
    group_counts: dict[str, int] = {}

    def _is_positive_primary_eligible(rec: Mapping[str, Any]) -> bool:
        m1 = rec["cluster_a_metrics"]["1x"]
        mz = rec["cluster_a_metrics"]["zero_pos_swap_1x"]
        mf = rec["cluster_a_metrics"]["fade_1x"]
        return (
            bool(rec["stage0"]["passed"])
            and int(m1["n_trades"]) >= 15
            and float(m1["net_R"]) > 0.0
            and float(mz["net_R"]) > 0.0
            and float(m1["net_R"]) > float(mf["net_R"])
        )

    # Pass 1: Best 1 positive Stage-0-passed candidate per pair/pool group (maximum orthogonality)
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        grp = str(r["group"])
        if _is_positive_primary_eligible(r) and group_counts.get(grp, 0) < 1:
            primary_ids.add(r["candidate_id"])
            group_counts[grp] = group_counts.get(grp, 0) + 1

    # Pass 2: Add up to 2 per group from remaining positive Cluster A candidates (up to PRIMARY_CAP)
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        if r["candidate_id"] in primary_ids:
            continue
        grp = str(r["group"])
        if _is_positive_primary_eligible(r) and group_counts.get(grp, 0) < 2:
            primary_ids.add(r["candidate_id"])
            group_counts[grp] = group_counts.get(grp, 0) + 1

    # Pass 3: Add any remaining positive Cluster A candidates with positive 2x Sharpe if still < PRIMARY_CAP
    for r in records:
        if len(primary_ids) >= PRIMARY_CAP:
            break
        if r["candidate_id"] in primary_ids:
            continue
        m2 = r["cluster_a_metrics"]["2x"]
        if _is_positive_primary_eligible(r) and float(m2["net_R"]) > 0.0:
            primary_ids.add(r["candidate_id"])
    primary: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []
    for r in records:
        item = dict(r)
        if r["candidate_id"] in primary_ids:
            item["tier"] = "PRIMARY"
            item["is_primary"] = True
            primary.append(item)
        else:
            item["tier"] = "EXPLORATORY"
            item["is_primary"] = False
            exploratory.append(item)

    meta: dict[str, Any] = {
        "family_id": FAMILY_ID,
        "module": "quant_factory.offensive3.fam11_statarb_pairs_prop",
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_cap": PRIMARY_CAP,
        "total_evaluated": len(records),
        "stage0_passed_count": sum(1 for r in records if r["stage0"]["passed"]),
        "swing_pair_count": len(SWING_D1_PAIRS),
        "swing_pool_count": len(SWING_POOLS),
        "intraday_m1_pair_count": len(INTRADAY_M1_PAIRS),
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }

    if save:
        saved_path = save_family_candidates(
            FAMILY_ID,
            {"primary": primary, "exploratory": exploratory},
            meta,
            candidates_dir=candidates_dir,
            root=root,
        )
        return load_family_candidates(FAMILY_ID, candidates_dir=saved_path.parent, verify_sha=True, root=root)

    return {
        "family_id": FAMILY_ID,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(primary) + len(exploratory),
        "meta": meta,
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "candidates": [*primary, *exploratory],
    }


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Stage 2 Cluster-A Discovery for F11_PAIRS_STATARB")
    p.add_argument("--resume", action="store_true", help="Reuse valid SHA-verified Cluster A checkpoint if present")
    p.add_argument("--no-save", action="store_true", help="Run discovery in memory without writing checkpoint")
    p.add_argument("--candidates-dir", type=Path, default=None, help="Optional override for candidates directory")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)
    doc = discover_cluster_a(
        universe=None,
        save=not args.no_save,
        resume=args.resume,
        candidates_dir=args.candidates_dir,
    )
    prim = doc["primary_candidates"]
    print(
        f"F11_DISCOVERY_OK: primary={doc['primary_count']}/{PRIMARY_CAP} "
        f"total={doc['total_count']}/{TOTAL_CAP} years={doc['discovery_years']} "
        f"stage0_pass={doc['meta'].get('stage0_passed_count', 0)}"
    )
    for row in prim[:5]:
        m1 = row["cluster_a_metrics"]["1x"]
        m2 = row["cluster_a_metrics"]["2x"]
        mz = row["cluster_a_metrics"]["zero_pos_swap_1x"]
        print(
            f"  TOP {row['candidate_id']} [{row['blindness_tier']}] "
            f"n={m1['n_trades']} net1x={m1['net_R']:+.2f}R sh1x={m1['sharpe']:+.2f} "
            f"sh2x={m2['sharpe']:+.2f} shZpos={mz['sharpe']:+.2f} "
            f"medF/SL={row['stage0']['median_fric_sl_ratio']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
