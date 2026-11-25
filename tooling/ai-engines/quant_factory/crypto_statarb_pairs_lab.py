"""C1.2 — Lab #2: Crypto Stat-Arb, Pairs & Market-Neutral (beta ~ 0) Research Lab.

STRICT SAFETY & ANTI-BIAS BOUNDARIES:
  - Offline computation strictly over cached public Binance Spot & USD-M Futures funding data
    (`.runtime/crypto-1h-cache/` + `.runtime/crypto-spot-cache/funding/`). ZERO API keys,
    OrderSend = 0, Holdout 2025+ FX untouched (`holdout_rows_analysed = 0`).
  - Strictly causal execution (`<= bar t` signals -> applied on bar `t+1`), causal rolling 30d
    dollar-volume universe selection, causal rolling OLS hedge ratios, causal rolling volatility.
  - Realistic 2-leg Long/Short perpetual friction:
      * Gross leverage strictly capped <= 1.0x (0.50x Long + 0.50x Short => >= 2x margin buffer).
      * Full 2-leg costs: 1x = 15 bps one-way per leg (30 bps RT per leg), 2x stress = 30 bps
        one-way per leg (60 bps RT per leg) + 100 bps delist haircut.
      * Realized 8h Binance USD-M perpetual funding cashflows (`-w_j * funding_j`: longs pay
        positive funding, shorts receive positive funding).
  - Strict split: Cluster A (`2021-01-01..2023-12-31`) -> Blind Cluster B (`2024-01-01..2026-11-22`).
  - Wires ALL 12 preregistered specs across 4 market-neutral families through
    `quant_factory.research_council` (`HypothesisCard` + `SkepticalRedTeamCritic`, BH-FDR,
    DSR, 2x cost survival, orthogonality vs Sleeve #2 `F4_4H_EMA`, plus explicit `|beta_BTC|`).
  - Retains ALL negative/killed results honestly!
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_1h_intraday_lab import (
    CL_A_END_1H,
    CL_B_START_1H,
    LAB1_CACHE_DIR,
    START_1H,
    TOP40_1H_SYMBOLS,
    UNIVERSE_100_SYMBOLS,
    _aggregate_bars_to_daily,
    load_interval_panel,
)
from quant_factory.crypto_causal_universe import (
    RETURNS_DIR,
    _compute_log_or_simple_rets,
    causal_rolling_top_n_mask,
    compute_daily_metrics,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.funding_rate_carry import FUNDING_CACHE_DIR, PERP_UNIVERSE_20
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

LAB2_SUMMARY_PATH = LAB1_CACHE_DIR / "lab2_statarb_summary.json"
LAB2_RETURNS_PATH = RETURNS_DIR / "sleeve_lab2_crypto_statarb.json"

# Explicit static economic crypto sectors (pre-registered, zero post-hoc clustering)
CRYPTO_SECTORS: dict[str, tuple[str, ...]] = {
    "L1_MAJOR": (
        "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "ADAUSDT", "AVAXUSDT",
        "DOTUSDT", "ATOMUSDT", "NEARUSDT", "APTUSDT", "SUIUSDT", "TONUSDT",
        "ALGOUSDT", "ICPUSDT", "HBARUSDT", "EGLDUSDT", "SEIUSDT", "TIAUSDT",
        "STXUSDT", "FLOWUSDT", "MINAUSDT", "ROSEUSDT", "ONEUSDT", "CELOUSDT",
    ),
    "DEFI": (
        "UNIUSDT", "AAVEUSDT", "MKRUSDT", "LDOUSDT", "CRVUSDT", "COMPUSDT",
        "SNXUSDT", "SUSHIUSDT", "RUNEUSDT", "INJUSDT", "DYDXUSDT", "GMXUSDT",
        "CAKEUSDT", "1INCHUSDT", "YFIUSDT", "BALUSDT", "KAVAUSDT", "KNCUSDT",
        "ENAUSDT", "PENDLEUSDT", "ONDOUSDT", "JUPUSDT",
    ),
    "L2_INFRA": (
        "ARBUSDT", "OPUSDT", "LINKUSDT", "GRTUSDT", "FILUSDT", "VETUSDT",
        "THETAUSDT", "IMXUSDT", "FETUSDT", "TAOUSDT", "WLDUSDT", "PYTHUSDT",
        "QNTUSDT", "ANKRUSDT", "STORJUSDT", "SKLUSDT", "LRCUSDT", "CFXUSDT",
    ),
    "GAMING_META": (
        "SANDUSDT", "MANAUSDT", "AXSUSDT", "CHZUSDT", "ENJUSDT", "GALAUSDT",
        "APEUSDT", "BATUSDT", "ZRXUSDT",
    ),
    "LEGACY_ALT": (
        "XRPUSDT", "LTCUSDT", "BCHUSDT", "TRXUSDT", "XLMUSDT", "ETCUSDT",
        "EOSUSDT", "NEOUSDT", "ZECUSDT", "XTZUSDT", "IOTAUSDT", "KSMUSDT",
        "WAVESUSDT", "DASHUSDT", "ZENUSDT", "RVNUSDT", "QTUMUSDT", "ICXUSDT",
        "ONTUSDT", "IOSTUSDT", "ZILUSDT",
    ),
    "MEME_HIGHBETA": (
        "DOGEUSDT", "SHIBUSDT", "PEPEUSDT", "WIFUSDT", "FLOKIUSDT", "BONKUSDT",
    ),
}

# Pre-registered 12 economic same-sector pairs (zero post-hoc pair mining)
PREREGISTERED_PAIRS: tuple[tuple[str, str], ...] = (
    ("ETHUSDT", "BTCUSDT"),
    ("SOLUSDT", "ETHUSDT"),
    ("AVAXUSDT", "SOLUSDT"),
    ("UNIUSDT", "AAVEUSDT"),
    ("ARBUSDT", "OPUSDT"),
    ("LTCUSDT", "BCHUSDT"),
    ("SANDUSDT", "MANAUSDT"),
    ("ADAUSDT", "XRPUSDT"),
    ("DOGEUSDT", "SHIBUSDT"),
    ("DOTUSDT", "ATOMUSDT"),
    ("LINKUSDT", "GRTUSDT"),
    ("CRVUSDT", "SNXUSDT"),
)

LAB2_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.60,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.25,
    max_tail_corr_vs_incumbent=0.40,
    min_trades_cluster_b=30,
)
MAX_ABS_BETA_VS_BTC = 0.20


def load_bar_funding_matrix(
    timestamps_ms: np.ndarray,
    symbols: list[str],
    bar_step_ms: int,
    *,
    funding_dir: Path = FUNDING_CACHE_DIR / "rates",
) -> tuple[np.ndarray, list[str]]:
    """Map real Binance 8h funding settlements onto bar grid `(T, N)` causally.

    A funding settlement at timestamp `ft` occurring inside `(open_ms[t], open_ms[t] + bar_step_ms]`
    is assigned to bar `t` (so a position `held_w[t] = target_w[t-1]` opened at `open_ms[t]` and
    held through `close_ms[t]` legitimately pays/receives that settlement, and signals computed
    at `close_ms[t]` for bar `t+1` only see already-settled funding!).
    For symbols lacking cached funding Parquets, fills settlement bars with the cross-sectional
    median funding rate of the cached 20 liquid perps (zero optimistic bias!).
    """
    n_t = len(timestamps_ms)
    n_s = len(symbols)
    fund = np.zeros((n_t, n_s), dtype=np.float64)
    if n_t == 0 or n_s == 0:
        return fund, []

    ts_start = int(timestamps_ms[0])
    ts_end = int(timestamps_ms[-1]) + bar_step_ms
    # Build lookup from bar close_ms -> bar index `t` (snapping +/- 30s tolerance for Binance ms jitter)
    exact_syms: list[str] = []
    cached_cols: list[int] = []
    sym_to_idx = {s: i for i, s in enumerate(symbols)}

    # Also collect all cached perp funding streams for median fallback
    fallback_streams: dict[int, list[float]] = {}

    if funding_dir.exists():
        for pq_path in sorted(funding_dir.glob("*.parquet")):
            sym = pq_path.stem
            tbl = pq.read_table(pq_path, columns=["funding_time_ms", "funding_rate"])
            ft_arr = tbl["funding_time_ms"].to_numpy()
            fr_arr = tbl["funding_rate"].to_numpy()
            # Vectorized bar assignment: bar t covers (open[t], open[t] + step]
            # Snap ft within +/- 60s of an 8h boundary to nearest multiple of bar_step_ms
            valid = (ft_arr > ts_start) & (ft_arr <= ts_end + 60_000) & np.isfinite(fr_arr)
            ft_v = ft_arr[valid]
            fr_v = fr_arr[valid]
            if len(ft_v) == 0:
                continue
            # Snap funding_time to nearest bar close (`open[t] + bar_step_ms`)
            snapped_close = np.round(ft_v / bar_step_ms).astype(np.int64) * bar_step_ms
            target_open = snapped_close - bar_step_ms
            idx = np.searchsorted(timestamps_ms, target_open)
            in_bounds = (idx >= 0) & (idx < n_t)
            idx = idx[in_bounds]
            fr_v = fr_v[in_bounds]
            target_open = target_open[in_bounds]
            matched = timestamps_ms[idx] == target_open
            idx = idx[matched]
            fr_v = fr_v[matched]

            j = sym_to_idx.get(sym)
            if j is not None:
                np.add.at(fund[:, j], idx, fr_v)
                exact_syms.append(sym)
                cached_cols.append(j)
            for b_i, r_val in zip(idx.tolist(), fr_v.tolist()):
                fallback_streams.setdefault(b_i, []).append(float(r_val))

    # Populate cross-sectional median funding on settlement bars for non-cached altcoins
    if fallback_streams and len(cached_cols) < n_s:
        med_bar = np.zeros(n_t, dtype=np.float64)
        for b_i, vals in fallback_streams.items():
            med_bar[b_i] = float(np.median(vals))
        cached_set = set(cached_cols)
        for j in range(n_s):
            if j not in cached_set:
                fund[:, j] = med_bar

    return fund, exact_syms


def simulate_ls_perp_backtest(
    close: np.ndarray,
    target_w: np.ndarray,
    funding_bar: np.ndarray,
    *,
    cost_bps_oneway: float = 15.0,
    delist_haircut_bps: float = 100.0,
    max_gross_leverage: float = 1.0,
) -> dict[str, Any]:
    """Causal 2-leg Long/Short perpetual simulator (`t -> t+1`) with explicit funding & costs.

    Sign convention (Binance USD-M Perpetual standard):
      - `target_w[t, j] > 0`: Long perp (`+w` price exposure, PAYS `-w * funding_bar` when funding > 0)
      - `target_w[t, j] < 0`: Short perp (`-w` price exposure, RECEIVES `-w * funding_bar > 0` when funding > 0)
      - Turnover = `sum_j |held_w[t, j] - held_w[t-1, j]|`, so entering `0.50` Long + `-0.50` Short
        pays `1.00 * cost_bps_oneway` (full 2-leg friction!).
    """
    n_t, n_s = close.shape
    w_clean = np.where(np.isfinite(target_w) & np.isfinite(close), target_w, 0.0).astype(np.float64)
    gross = np.sum(np.abs(w_clean), axis=1, keepdims=True)
    scale = np.where(gross > max_gross_leverage, max_gross_leverage / np.maximum(gross, 1e-12), 1.0)
    w_clean = w_clean * scale

    held_w = np.zeros_like(w_clean)
    held_w[1:] = w_clean[:-1]

    rets = _compute_log_or_simple_rets(close)
    valid_ret = np.isfinite(rets)
    safe_rets = np.where(valid_ret, np.clip(rets, -0.95, 5.0), 0.0)
    delist_hit = (~valid_ret) & (np.abs(held_w) > 1e-12)
    delist_cost = np.sum(np.abs(held_w) * delist_hit.astype(np.float64), axis=1) * (delist_haircut_bps / 10_000.0)

    dw = np.zeros_like(held_w)
    dw[0] = np.abs(held_w[0])
    dw[1:] = np.abs(held_w[1:] - held_w[:-1])
    turnover = np.sum(dw, axis=1)
    trade_cost = turnover * (cost_bps_oneway / 10_000.0)

    safe_fund = np.where(np.isfinite(funding_bar), funding_bar, 0.0)
    price_pnl = np.sum(held_w * safe_rets, axis=1)
    funding_pnl = np.sum(-held_w * safe_fund, axis=1)
    net_ret = np.clip(price_pnl + funding_pnl - trade_cost - delist_cost, -0.99, 5.0)

    return {
        "net_returns": net_ret,
        "price_pnl": price_pnl,
        "funding_pnl": funding_pnl,
        "cost_drag": trade_cost + delist_cost,
        "turnover": turnover,
        "held_w": held_w,
        "gross_exposure": np.sum(np.abs(held_w), axis=1),
        "net_exposure": np.sum(held_w, axis=1),
    }


def _rolling_vol_causal(rets: np.ndarray, window: int) -> np.ndarray:
    n_t, n_s = rets.shape
    out = np.full((n_t, n_s), np.nan, dtype=np.float64)
    if n_t < window:
        return out
    ok = np.isfinite(rets)
    rz = np.where(ok, rets, 0.0)
    win_r = sliding_window_view(rz, window, axis=0)
    win_ok = sliding_window_view(ok, window, axis=0)
    cnt = np.sum(win_ok, axis=2)
    denom = np.maximum(cnt, 1)
    mean = np.sum(win_r, axis=2) / denom
    diff = np.where(win_ok, win_r - mean[:, :, None], 0.0)
    var = np.sum(diff * diff, axis=2) / denom
    sd = np.where(cnt >= max(10, window // 2), np.sqrt(np.maximum(var, 0.0)), np.nan)
    out[window - 1 :] = sd
    return out


def _normalize_dollar_neutral_weights(
    raw_long: np.ndarray,
    raw_short: np.ndarray,
    target_side_gross: float = 0.50,
) -> np.ndarray:
    """Given non-negative long & short scores `(N,)`, build exact dollar-neutral weights `sum(w)=0`."""
    n = len(raw_long)
    w = np.zeros(n, dtype=np.float64)
    lsum = float(np.sum(raw_long))
    ssum = float(np.sum(raw_short))
    if lsum > 1e-12 and ssum > 1e-12:
        w += (raw_long / lsum) * target_side_gross
        w -= (raw_short / ssum) * target_side_gross
    return w


def _apply_neutral_rebalance_cadence(
    raw_w: np.ndarray,
    *,
    rebal_every_bars: int = 1,
    l1_deadband: float = 0.15,
) -> np.ndarray:
    """Portfolio-level causal rebalance cadence + L1 deadband preserving EXACT dollar neutrality.

    Unlike per-coin deadbands (which break `sum(w) == 0` when one side updates and the other does not),
    portfolio-level atomic rebalancing swaps the entire vector `prev -> cur` on scheduled rebalance bars
    only when total 2-leg L1 drift exceeds `l1_deadband` (or when transitioning to/from flat cash).
    """
    n_t, n_s = raw_w.shape
    out = np.zeros((n_t, n_s), dtype=np.float64)
    prev = np.zeros(n_s, dtype=np.float64)
    step = max(1, int(rebal_every_bars))
    for t in range(n_t):
        cur = raw_w[t]
        if t % step == 0:
            cur_active = float(np.sum(np.abs(cur))) > 1e-12
            prev_active = float(np.sum(np.abs(prev))) > 1e-12
            l1_diff = float(np.sum(np.abs(cur - prev)))
            if (cur_active != prev_active) or (l1_diff >= l1_deadband):
                prev = cur.copy()
        out[t] = prev
    return out


# ---------------------------------------------------------------------------
# Family 1: Sector-Neutral Residual Mean Reversion (4H & 1H)
# ---------------------------------------------------------------------------

def strat_sector_neutral_residual_rev(
    close: np.ndarray,
    symbols: list[str],
    top_mask: np.ndarray,
    *,
    ret_lb: int,
    vol_lb: int,
    deadband: float = 0.20,
    rebal_every_bars: int = 6,
    min_sector_active: int = 4,
) -> np.ndarray:
    """Within each pre-registered crypto sector, buy oversold residual vs sector mean & short overbought.

    Guarantees EXACT sector neutrality AND exact dollar neutrality (`sum(w) == 0`) at every bar `t`
    using strictly data `<= t`.
    """
    n_t, n_s = close.shape
    rets = _compute_log_or_simple_rets(close)
    vol = _rolling_vol_causal(rets, vol_lb)
    cum_r = np.full((n_t, n_s), np.nan, dtype=np.float64)
    cum_r[ret_lb:] = close[ret_lb:] / close[:-ret_lb] - 1.0

    sym_to_idx = {s: i for i, s in enumerate(symbols)}
    sector_idx_lists: list[np.ndarray] = []
    for sec_syms in CRYPTO_SECTORS.values():
        idxs = [sym_to_idx[s] for s in sec_syms if s in sym_to_idx]
        if len(idxs) >= min_sector_active:
            sector_idx_lists.append(np.array(idxs, dtype=np.int64))

    raw_w = np.zeros((n_t, n_s), dtype=np.float64)
    start = max(ret_lb, vol_lb) + 2
    for t in range(start, n_t):
        active_sectors: list[np.ndarray] = []
        for s_idxs in sector_idx_lists:
            ok = (
                top_mask[t, s_idxs]
                & np.isfinite(cum_r[t, s_idxs])
                & np.isfinite(vol[t, s_idxs])
                & (vol[t, s_idxs] > 1e-6)
            )
            valid_idxs = s_idxs[ok]
            if len(valid_idxs) < min_sector_active:
                continue
            r_sec = cum_r[t, valid_idxs]
            v_sec = vol[t, valid_idxs]
            res = r_sec - float(np.mean(r_sec))
            z_res = res / np.maximum(v_sec * math.sqrt(ret_lb), 1e-6)
            order = np.argsort(z_res)
            k = max(1, len(valid_idxs) // 4)
            long_i = valid_idxs[order[:k]]      # Most oversold vs sector
            short_i = valid_idxs[order[-k:]]    # Most overbought vs sector
            inv_l = 1.0 / np.maximum(vol[t, long_i], 1e-4)
            inv_s = 1.0 / np.maximum(vol[t, short_i], 1e-4)
            w_sec = np.zeros(n_s, dtype=np.float64)
            w_sec[long_i] = inv_l / np.sum(inv_l)
            w_sec[short_i] = -inv_s / np.sum(inv_s)
            active_sectors.append(w_sec)

        if active_sectors:
            w_bar = np.mean(active_sectors, axis=0) * 0.50  # 0.50 Long + 0.50 Short => gross 1.0, net 0.0
            raw_w[t] = w_bar

    return _apply_neutral_rebalance_cadence(raw_w, rebal_every_bars=rebal_every_bars, l1_deadband=deadband)


# ---------------------------------------------------------------------------
# Family 2: Rolling Cointegrated Pairs with Causal OLS Hedge + Hard Stop
# ---------------------------------------------------------------------------

def strat_rolling_coint_pairs(
    close: np.ndarray,
    symbols: list[str],
    *,
    window: int = 180,
    z_entry: float = 2.0,
    z_exit: float = 0.5,
    z_stop: float = 4.0,
    min_corr: float = 0.55,
    max_ar1_phi: float = 0.96,
    max_pair_gross: float = 0.25,
) -> np.ndarray:
    """Causal rolling OLS hedge-ratio pairs stat-arb on 12 pre-registered economic crypto pairs."""
    n_t, n_s = close.shape
    log_c = np.where(np.isfinite(close) & (close > 0.0), np.log(close), np.nan)
    dlog = np.full_like(log_c, np.nan)
    dlog[1:] = log_c[1:] - log_c[:-1]
    sym_to_idx = {s: i for i, s in enumerate(symbols)}

    pair_positions: list[tuple[int, int, np.ndarray]] = []
    for sym_y, sym_x in PREREGISTERED_PAIRS:
        if sym_y not in sym_to_idx or sym_x not in sym_to_idx:
            continue
        iy, ix = sym_to_idx[sym_y], sym_to_idx[sym_x]
        y = log_c[:, iy]
        x = log_c[:, ix]
        dy = dlog[:, iy]
        dx = dlog[:, ix]

        pos = np.zeros(n_t, dtype=np.float64)  # +1 => Long Y / Short X; -1 => Short Y / Long X
        if n_t <= window + 2:
            pair_positions.append((iy, ix, pos))
            continue

        # Vectorized rolling OLS & spread stats over strictly causal windows [t-window+1..t]
        wy = sliding_window_view(y, window)      # (M, W) aligned to t = window-1..n_t-1
        wx = sliding_window_view(x, window)
        wdy = sliding_window_view(dy, window)
        wdx = sliding_window_view(dx, window)

        valid_win = np.all(np.isfinite(wy), axis=1) & np.all(np.isfinite(wx), axis=1)
        mean_y = np.mean(wy, axis=1)
        mean_x = np.mean(wx, axis=1)
        xc = wx - mean_x[:, None]
        yc = wy - mean_y[:, None]
        var_x = np.mean(xc * xc, axis=1)
        cov_xy = np.mean(xc * yc, axis=1)
        beta = np.clip(cov_xy / np.maximum(var_x, 1e-12), 0.25, 2.50)
        alpha = mean_y - beta * mean_x

        spread = wy - (alpha[:, None] + beta[:, None] * wx)  # (M, W)
        sp_mean = np.mean(spread, axis=1)
        sp_std = np.std(spread, axis=1)
        z_arr = (spread[:, -1] - sp_mean) / np.maximum(sp_std, 1e-9)

        # Causal AR(1) mean-reversion speed check on spread: s_u = phi * s_{u-1}
        s_prev = spread[:, :-1] - sp_mean[:, None]
        s_curr = spread[:, 1:] - sp_mean[:, None]
        phi = np.sum(s_prev * s_curr, axis=1) / np.maximum(np.sum(s_prev * s_prev, axis=1), 1e-12)

        # Causal return correlation check (warning-free on pre-listing all-NaN slices)
        ok_dy = np.isfinite(wdy)
        ok_dx = np.isfinite(wdx)
        dy_m = np.sum(np.where(ok_dy, wdy, 0.0), axis=1) / np.maximum(np.sum(ok_dy, axis=1), 1)
        dx_m = np.sum(np.where(ok_dx, wdx, 0.0), axis=1) / np.maximum(np.sum(ok_dx, axis=1), 1)
        dy_c = np.where(ok_dy, wdy - dy_m[:, None], 0.0)
        dx_c = np.where(ok_dx, wdx - dx_m[:, None], 0.0)
        corr = np.sum(dy_c * dx_c, axis=1) / np.maximum(
            np.sqrt(np.sum(dy_c * dy_c, axis=1) * np.sum(dx_c * dx_c, axis=1)),
            1e-12,
        )

        coint_ok = valid_win & (sp_std > 1e-5) & (corr >= min_corr) & (phi < max_ar1_phi) & (phi > 0.0)

        state = 0.0
        for m_i in range(len(z_arr)):
            t = m_i + window - 1
            if not valid_win[m_i]:
                state = 0.0
                pos[t] = 0.0
                continue
            z = float(z_arr[m_i])
            if state == 0.0:
                if coint_ok[m_i]:
                    if z >= z_entry and z < z_stop:
                        state = -1.0  # Spread high -> Short Y, Long X
                    elif z <= -z_entry and z > -z_stop:
                        state = 1.0   # Spread low -> Long Y, Short X
            elif state > 0.0:
                if z >= -z_exit or z <= -z_stop:
                    state = 0.0
            else:
                if z <= z_exit or z >= z_stop:
                    state = 0.0
            pos[t] = state

        pair_positions.append((iy, ix, pos))

    # Aggregate dollar-neutral pair positions across active pairs, capping single-pair gross <= max_pair_gross
    w = np.zeros((n_t, n_s), dtype=np.float64)
    for t in range(n_t):
        active = [(iy, ix, float(p[t])) for iy, ix, p in pair_positions if p[t] != 0.0]
        if not active:
            continue
        per_pair_side = min(max_pair_gross / 2.0, 0.50 / len(active))
        for iy, ix, sign in active:
            w[t, iy] += sign * per_pair_side
            w[t, ix] -= sign * per_pair_side
        # Re-normalize total gross to <= 1.0 (preserving exact dollar neutrality sum(w) == 0!)
        gross = float(np.sum(np.abs(w[t])))
        if gross > 1.0:
            w[t] /= gross
    return w


# ---------------------------------------------------------------------------
# Family 3: Funding-Dislocation Long/Short Pair (4H on PERP_UNIVERSE_20)
# ---------------------------------------------------------------------------

def strat_funding_dislocation_ls(
    close: np.ndarray,
    funding_bar: np.ndarray,
    *,
    fund_lb_bars: int,
    vol_lb_bars: int = 84,
    k_side: int = 4,
    min_spread_ann: float = 0.12,
    deadband: float = 0.20,
    rebal_every_bars: int = 18,
    bars_per_day: int = 6,
) -> np.ndarray:
    """Short Top-K highest-funding perps vs Long Bot-K lowest-funding perps (exact dollar-neutral)."""
    n_t, n_s = close.shape
    rets = _compute_log_or_simple_rets(close)
    vol = _rolling_vol_causal(rets, vol_lb_bars)

    # Trailing average annualized funding over strictly causal window [t-fund_lb_bars+1..t]
    # Sum of funding over L bars * (365 * bars_per_day / L) = annualized rate!
    ann_mult = (365.0 * bars_per_day) / float(fund_lb_bars)
    safe_f = np.where(np.isfinite(funding_bar), funding_bar, 0.0)
    cs = np.cumsum(safe_f, axis=0)
    roll_f_ann = np.zeros((n_t, n_s), dtype=np.float64)
    roll_f_ann[fund_lb_bars:] = (cs[fund_lb_bars:] - cs[:-fund_lb_bars]) * ann_mult

    raw_w = np.zeros((n_t, n_s), dtype=np.float64)
    start = max(fund_lb_bars, vol_lb_bars) + 2
    for t in range(start, n_t):
        ok = np.isfinite(close[t]) & np.isfinite(vol[t]) & (vol[t] > 1e-6)
        valid = np.where(ok)[0]
        if len(valid) < 2 * k_side + 2:
            continue
        f_vals = roll_f_ann[t, valid]
        order = np.argsort(f_vals)
        bot_i = valid[order[:k_side]]      # Lowest/negative funding -> LONG
        top_i = valid[order[-k_side:]]     # Highest positive funding -> SHORT
        spread_ann = float(np.mean(roll_f_ann[t, top_i]) - np.mean(roll_f_ann[t, bot_i]))
        if spread_ann < min_spread_ann:
            continue
        raw_l = np.zeros(n_s, dtype=np.float64)
        raw_s = np.zeros(n_s, dtype=np.float64)
        raw_l[bot_i] = 1.0 / np.maximum(vol[t, bot_i], 1e-4)
        raw_s[top_i] = 1.0 / np.maximum(vol[t, top_i], 1e-4)
        raw_w[t] = _normalize_dollar_neutral_weights(raw_l, raw_s, target_side_gross=0.50)

    return _apply_neutral_rebalance_cadence(raw_w, rebal_every_bars=rebal_every_bars, l1_deadband=deadband)


# ---------------------------------------------------------------------------
# Family 4: Market-Neutral Volatility-Managed Cross-Sectional Momentum (4H & 1H)
# ---------------------------------------------------------------------------

def strat_mkt_neutral_vol_mom(
    close: np.ndarray,
    symbols: list[str],
    top_mask: np.ndarray,
    *,
    mom_lb: int,
    vol_lb: int,
    k_side: int = 5,
    beta_neutralize: bool = False,
    beta_lb: int = 180,
    deadband: float = 0.20,
    rebal_every_bars: int = 18,
) -> np.ndarray:
    """Dollar-neutral (and optionally BTC-beta-hedged) vol-managed cross-sectional momentum."""
    n_t, n_s = close.shape
    rets = _compute_log_or_simple_rets(close)
    vol = _rolling_vol_causal(rets, vol_lb)
    cum_r = np.full((n_t, n_s), np.nan, dtype=np.float64)
    cum_r[mom_lb:] = close[mom_lb:] / close[:-mom_lb] - 1.0

    btc_idx = symbols.index("BTCUSDT") if "BTCUSDT" in symbols else -1
    btc_beta = np.ones((n_t, n_s), dtype=np.float64)
    if beta_neutralize and btc_idx >= 0 and n_t > beta_lb:
        btc_r = np.where(np.isfinite(rets[:, btc_idx]), rets[:, btc_idx], 0.0)
        wb = sliding_window_view(btc_r, beta_lb)  # (M, W)
        bm = np.mean(wb, axis=1, keepdims=True)
        bc = wb - bm
        bvar = np.maximum(np.mean(bc * bc, axis=1), 1e-12)
        for j in range(n_s):
            rj = np.where(np.isfinite(rets[:, j]), rets[:, j], 0.0)
            wj = sliding_window_view(rj, beta_lb)
            jc = wj - np.mean(wj, axis=1, keepdims=True)
            cov = np.mean(bc * jc, axis=1)
            btc_beta[beta_lb - 1 :, j] = np.clip(cov / bvar, 0.0, 2.5)

    raw_w = np.zeros((n_t, n_s), dtype=np.float64)
    start = max(mom_lb, vol_lb, beta_lb if beta_neutralize else 0) + 2
    for t in range(start, n_t):
        ok = top_mask[t] & np.isfinite(cum_r[t]) & np.isfinite(vol[t]) & (vol[t] > 1e-6)
        valid = np.where(ok)[0]
        if len(valid) < 2 * k_side + 2:
            continue
        score = cum_r[t, valid] / np.maximum(vol[t, valid], 1e-4)
        order = np.argsort(score)
        bot_i = valid[order[:k_side]]     # Laggards -> SHORT
        top_i = valid[order[-k_side:]]    # Winners -> LONG
        raw_l = np.zeros(n_s, dtype=np.float64)
        raw_s = np.zeros(n_s, dtype=np.float64)
        raw_l[top_i] = 1.0 / np.maximum(vol[t, top_i], 1e-4)
        raw_s[bot_i] = 1.0 / np.maximum(vol[t, bot_i], 1e-4)
        w_t = _normalize_dollar_neutral_weights(raw_l, raw_s, target_side_gross=0.50)

        if beta_neutralize and btc_idx >= 0 and np.isfinite(close[t, btc_idx]):
            port_beta = float(np.dot(w_t, btc_beta[t]))
            # Hedge residual BTC beta while maintaining gross <= 1.0
            hedge = float(np.clip(-port_beta, -0.35, 0.35))
            w_t[btc_idx] += hedge
            g = float(np.sum(np.abs(w_t)))
            if g > 1.0:
                w_t /= g
        raw_w[t] = w_t

    return _apply_neutral_rebalance_cadence(raw_w, rebal_every_bars=rebal_every_bars, l1_deadband=deadband)


def _compute_beta_and_corr(strat_r: np.ndarray, bench_r: np.ndarray) -> tuple[float, float]:
    n = min(len(strat_r), len(bench_r))
    if n < 20:
        return 0.0, 0.0
    a = np.asarray(strat_r[:n], dtype=np.float64)
    b = np.asarray(bench_r[:n], dtype=np.float64)
    vb = float(np.var(b))
    va = float(np.var(a))
    if vb <= 1e-12 or va <= 1e-12:
        return 0.0, 0.0
    cov = float(np.cov(a, b, ddof=0)[0, 1])
    beta = cov / vb
    corr = cov / math.sqrt(va * vb)
    return round(beta if math.isfinite(beta) else 0.0, 4), round(corr if math.isfinite(corr) else 0.0, 4)


def _load_incumbent_daily(path: Path) -> dict[str, float]:
    if not path.exists():
        return {}
    obj = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): float(v) for k, v in obj.get("daily_returns", {}).items()}


def run_lab2(*, cache_dir: Path = LAB1_CACHE_DIR, funding_dir: Path = FUNDING_CACHE_DIR / "rates") -> dict[str, Any]:
    t0 = time.perf_counter()

    # Load 4H 100-coin panel, 1H 40-coin panel, and 4H 20-perp panel
    panel_4h = load_interval_panel("4h", UNIVERSE_100_SYMBOLS, cache_dir=cache_dir, min_date=START_1H)
    panel_1h = load_interval_panel("1h", TOP40_1H_SYMBOLS, cache_dir=cache_dir, min_date=START_1H)
    panel_4h_p20 = load_interval_panel("4h", PERP_UNIVERSE_20, cache_dir=cache_dir, min_date=START_1H)

    fund_4h, exact_4h = load_bar_funding_matrix(panel_4h["timestamps_ms"], panel_4h["symbols"], 4 * 3_600_000, funding_dir=funding_dir)
    fund_1h, exact_1h = load_bar_funding_matrix(panel_1h["timestamps_ms"], panel_1h["symbols"], 3_600_000, funding_dir=funding_dir)
    fund_p20, exact_p20 = load_bar_funding_matrix(panel_4h_p20["timestamps_ms"], panel_4h_p20["symbols"], 4 * 3_600_000, funding_dir=funding_dir)

    # Causal rolling 30-day dollar-volume liquidity masks
    top50_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=50)
    top30_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=30)
    top30_1h = causal_rolling_top_n_mask(panel_1h["quote_volume"], panel_1h["close"], lookback_bars=720, top_n=30)

    # Daily BTC benchmark returns from 4H panel (for beta_vs_BTC verification)
    btc_idx_4h = panel_4h["symbols"].index("BTCUSDT")
    btc_rets_4h = np.nan_to_num(_compute_log_or_simple_rets(panel_4h["close"][:, [btc_idx_4h]])[:, 0], nan=0.0)
    btc_days, btc_daily_r, _, _ = _aggregate_bars_to_daily(
        panel_4h["timestamps_ms"], btc_rets_4h, np.zeros_like(btc_rets_4h), np.ones_like(btc_rets_4h)
    )
    btc_daily_map = {d: float(v) for d, v in zip(btc_days, btc_daily_r)}

    inc_s2_map = _load_incumbent_daily(RETURNS_DIR / "sleeve2_crypto_spot.json")
    inc_s3a_map = _load_incumbent_daily(RETURNS_DIR / "sleeve3a_funding_carry.json")

    specs: list[dict[str, Any]] = [
        # Family 1: Sector-Neutral Residual Mean Reversion (3 specs, daily cadence aligned to horizon)
        {
            "id": "S1_SECTOR_RES_REV_4H_12B", "tf": "4h", "fam": "SECTOR_NEUTRAL_RESIDUAL_REV",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_sector_neutral_residual_rev(panel_4h["close"], panel_4h["symbols"], top50_4h, ret_lb=12, vol_lb=84, deadband=0.25, rebal_every_bars=6),
            "cp": "Short-term single-token retail/perp liquidation overshoots against same-sector peers",
            "rat": "Idiosyncratic 48h shocks within a crypto sector mean-revert once forced perp liquidations clear, while exact sector neutrality hedges common beta.",
        },
        {
            "id": "S1_SECTOR_RES_REV_4H_24B", "tf": "4h", "fam": "SECTOR_NEUTRAL_RESIDUAL_REV",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_sector_neutral_residual_rev(panel_4h["close"], panel_4h["symbols"], top50_4h, ret_lb=24, vol_lb=84, deadband=0.25, rebal_every_bars=12),
            "cp": "Multi-day single-coin narrative spikes and panic dumps within liquid crypto sectors",
            "rat": "96h idiosyncratic return residuals inside equal-beta crypto sectors revert as liquidity providers rebalance inventory across peer tokens.",
        },
        {
            "id": "S1_SECTOR_RES_REV_1H_24B", "tf": "1h", "fam": "SECTOR_NEUTRAL_RESIDUAL_REV",
            "panel": panel_1h, "fund": fund_1h,
            "w": strat_sector_neutral_residual_rev(panel_1h["close"], panel_1h["symbols"], top30_1h, ret_lb=24, vol_lb=168, deadband=0.25, rebal_every_bars=24),
            "cp": "Intraday 24h cross-venue orderflow imbalances across same-sector crypto tokens",
            "rat": "Hourly sector-neutral reversion captures faster cross-coin liquidity provision after localized altcoin spikes while keeping dollar and sector exposure at zero.",
        },
        # Family 2: Rolling Cointegrated Pairs (3 specs)
        {
            "id": "S2_COINT_PAIRS_4H_W180", "tf": "4h", "fam": "ROLLING_COINT_PAIRS",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_rolling_coint_pairs(panel_4h["close"], panel_4h["symbols"], window=180, z_entry=2.0, z_exit=0.5, z_stop=4.0),
            "cp": "Relative-value dislocations between economically linked crypto pairs during isolated flows",
            "rat": "Causal 30-day rolling OLS pairs with correlation and AR(1) mean-reversion filters fade temporary spread dislocations while hard 4-sigma stops cut structural regime breaks.",
        },
        {
            "id": "S2_COINT_PAIRS_4H_W360", "tf": "4h", "fam": "ROLLING_COINT_PAIRS",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_rolling_coint_pairs(panel_4h["close"], panel_4h["symbols"], window=360, z_entry=2.2, z_exit=0.4, z_stop=4.2),
            "cp": "Medium-horizon relative-value dislocations between fundamental crypto sector twins",
            "rat": "60-day rolling OLS hedge ratios reduce estimation noise and turnover while requiring strict causal correlation and finite spread half-life before entry.",
        },
        {
            "id": "S2_COINT_PAIRS_1H_W240", "tf": "1h", "fam": "ROLLING_COINT_PAIRS",
            "panel": panel_1h, "fund": fund_1h,
            "w": strat_rolling_coint_pairs(panel_1h["close"], panel_1h["symbols"], window=240, z_entry=2.2, z_exit=0.5, z_stop=4.0),
            "cp": "Fast intraday relative-value dislocations across correlated crypto pairs",
            "rat": "10-day hourly rolling cointegration pairs capture faster intraday spread convergence between closely linked tokens with strict causal filtering and stop-outs.",
        },
        # Family 3: Funding-Dislocation Long/Short Pair (3 specs on 20-perp exact funding universe, horizon-matched cadence)
        {
            "id": "S3_FUND_DISLOC_4H_3D_K4", "tf": "4h", "fam": "FUNDING_DISLOCATION_LS",
            "panel": panel_4h_p20, "fund": fund_p20,
            "w": strat_funding_dislocation_ls(panel_4h_p20["close"], fund_p20, fund_lb_bars=18, k_side=4, min_spread_ann=0.12, deadband=0.25, rebal_every_bars=6),
            "cp": "Over-leveraged retail perp longs paying extreme funding on hot alts vs uncrowded perp shorts",
            "rat": "Shorting top-4 crowded high-funding perps against longing bottom-4 discounted perps earns cross-sectional funding carry and fades crowded leverage with zero net dollar exposure.",
        },
        {
            "id": "S3_FUND_DISLOC_4H_7D_K4", "tf": "4h", "fam": "FUNDING_DISLOCATION_LS",
            "panel": panel_4h_p20, "fund": fund_p20,
            "w": strat_funding_dislocation_ls(panel_4h_p20["close"], fund_p20, fund_lb_bars=42, k_side=4, min_spread_ann=0.10, deadband=0.25, rebal_every_bars=18),
            "cp": "Persistent week-long speculative perp leverage crowding in top-tier altcoins",
            "rat": "7-day trailing funding-dislocation L/S filters out transient single-settlement noise to harvest persistent funding spreads and unwind crowded long positioning.",
        },
        {
            "id": "S3_FUND_DISLOC_4H_14D_K5", "tf": "4h", "fam": "FUNDING_DISLOCATION_LS",
            "panel": panel_4h_p20, "fund": fund_p20,
            "w": strat_funding_dislocation_ls(panel_4h_p20["close"], fund_p20, fund_lb_bars=84, k_side=5, min_spread_ann=0.08, deadband=0.25, rebal_every_bars=42),
            "cp": "Multi-week structural perp carry imbalances across liquid Binance USD-M futures",
            "rat": "14-day funding-dislocation Top-5/Bot-5 L/S minimizes 2-leg turnover via weekly atomic rebalancing while systematically collecting the cross-sectional funding spread on a dollar-neutral perp book.",
        },
        # Family 4: Market-Neutral Volatility-Managed Momentum (3 specs, horizon-matched cadence)
        {
            "id": "S4_MKT_NEUT_MOM_4H_14D", "tf": "4h", "fam": "MKT_NEUTRAL_VOL_MOM",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_mkt_neutral_vol_mom(panel_4h["close"], panel_4h["symbols"], top30_4h, mom_lb=84, vol_lb=84, k_side=5, beta_neutralize=False, deadband=0.25, rebal_every_bars=18),
            "cp": "Slow capital rotation from decaying altcoins into emerging narrative leaders",
            "rat": "Volatility-managed 14-day cross-sectional momentum longs top-5 risk-adjusted winners and shorts bottom-5 laggards dollar-neutrally on a 3-day rebalance cadence to isolate relative drift from BTC beta.",
        },
        {
            "id": "S4_MKT_NEUT_MOM_4H_30D_BN", "tf": "4h", "fam": "MKT_NEUTRAL_VOL_MOM",
            "panel": panel_4h, "fund": fund_4h,
            "w": strat_mkt_neutral_vol_mom(panel_4h["close"], panel_4h["symbols"], top30_4h, mom_lb=180, vol_lb=84, k_side=5, beta_neutralize=True, beta_lb=180, deadband=0.25, rebal_every_bars=42),
            "cp": "Structural multi-week token dispersion driven by emissions, unlocks, and momentum inflows",
            "rat": "30-day vol-managed XSMOM with weekly atomic rebalancing and explicit causal 30-day rolling BTC-beta hedge neutralizes market direction while capturing persistent dispersion between leaders and structurally decaying tokens.",
        },
        {
            "id": "S4_MKT_NEUT_MOM_1H_7D", "tf": "1h", "fam": "MKT_NEUTRAL_VOL_MOM",
            "panel": panel_1h, "fund": fund_1h,
            "w": strat_mkt_neutral_vol_mom(panel_1h["close"], panel_1h["symbols"], top30_1h, mom_lb=168, vol_lb=168, k_side=5, beta_neutralize=False, deadband=0.25, rebal_every_bars=24),
            "cp": "Weekly intraday relative-strength drift between leading and lagging liquid crypto assets",
            "rat": "7-day hourly vol-managed dollar-neutral momentum tracks weekly rotation across Top-30 liquid coins on a daily atomic rebalance cadence.",
        },
    ]

    eval_items: list[dict[str, Any]] = []
    daily_1x_map: dict[str, dict[str, float]] = {}

    for sp in specs:
        p = sp["panel"]
        s1 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=15.0)
        s2 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=30.0)
        days, r1, to1, ex1 = _aggregate_bars_to_daily(p["timestamps_ms"], s1["net_returns"], s1["turnover"], s1["gross_exposure"])
        _, r2, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], s2["net_returns"], s2["turnover"], s2["gross_exposure"])
        _, px1, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], s1["price_pnl"], s1["turnover"], s1["gross_exposure"])
        _, fn1, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], s1["funding_pnl"], s1["turnover"], s1["gross_exposure"])
        _, cs1, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], s1["cost_drag"], s1["turnover"], s1["gross_exposure"])

        ma = np.array([START_1H <= d <= CL_A_END_1H for d in days])
        mb = np.array([d >= CL_B_START_1H for d in days])
        days_a = [d for d, f in zip(days, ma) if f]
        days_b = [d for d, f in zip(days, mb) if f]
        btc_a = np.array([btc_daily_map.get(d, 0.0) for d in days_a], dtype=np.float64)
        btc_b = np.array([btc_daily_map.get(d, 0.0) for d in days_b], dtype=np.float64)
        s3a_b = np.array([inc_s3a_map.get(d, 0.0) for d in days_b], dtype=np.float64)

        beta_a, corr_btc_a = _compute_beta_and_corr(r1[ma], btc_a)
        beta_b, corr_btc_b = _compute_beta_and_corr(r1[mb], btc_b)
        _, corr_s3a_b = _compute_beta_and_corr(r1[mb], s3a_b)

        eval_items.append({
            "id": sp["id"], "tf": sp["tf"], "fam": sp["fam"], "cp": sp["cp"], "rat": sp["rat"],
            "days": days, "days_b": days_b, "r1": r1, "r2": r2, "ma": ma, "mb": mb,
            "mA1": compute_daily_metrics(r1[ma], to1[ma], ex1[ma]),
            "mA2": compute_daily_metrics(r2[ma], to1[ma], ex1[ma]),
            "mB1": compute_daily_metrics(r1[mb], to1[mb], ex1[mb]),
            "mB2": compute_daily_metrics(r2[mb], to1[mb], ex1[mb]),
            "mF1": compute_daily_metrics(r1, to1, ex1),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
            "avg_abs_net_exp": round(float(np.mean(np.abs(s1["net_exposure"]))), 5),
            "max_gross_exp": round(float(np.max(s1["gross_exposure"])), 5),
            "beta_btc_a": beta_a,
            "corr_btc_a": corr_btc_a,
            "beta_btc_b": beta_b,
            "corr_btc_b": corr_btc_b,
            "corr_s3a_b": corr_s3a_b,
            "price_pnl_b_pct": round(float(np.sum(px1[mb])) * 100.0, 2),
            "funding_pnl_b_pct": round(float(np.sum(fn1[mb])) * 100.0, 2),
            "cost_drag_1x_b_pct": round(float(np.sum(cs1[mb])) * 100.0, 2),
        })
        daily_1x_map[sp["id"]] = {d: float(v) for d, v in zip(days, r1)}

    m_total = len(eval_items)
    family_p_b = tuple(float(it["mB1"]["p_one_sided_nw"]) for it in eval_items)
    qb_all = benjamini_hochberg(list(family_p_b))

    results: list[dict[str, Any]] = []
    approved: list[str] = []

    for idx_i, it in enumerate(eval_items):
        inc_b = np.array([inc_s2_map.get(d, 0.0) for d in it["days_b"]], dtype=np.float64) if inc_s2_map else None
        card = propose_hypothesis(
            hypothesis_id=it["id"],
            title=f"Lab #2 {it['fam']} ({it['tf']})",
            asset_universe=PERP_UNIVERSE_20[:5] if it["fam"] == "FUNDING_DISLOCATION_LS" else UNIVERSE_100_SYMBOLS[:5],
            timeframe=it["tf"],
            counterparty_mechanism=it["cp"],
            economic_rationale=it["rat"],
            causal_invariants=(
                "strict_t_to_t_plus_1_2leg_perp",
                "causal_rolling_topN_and_ols_le_t",
                "real_8h_binance_funding_cashflows",
                "15bps_and_30bps_per_leg_friction",
                "gross_leverage_le_1x_and_beta_neutral",
            ),
            n_trials_cumulative=m_total,
            kill_criteria=LAB2_KILL_CRITERIA,
        )
        ev = EvidenceBundle(
            cluster_a_returns=it["r1"][it["ma"]],
            cluster_b_returns=it["r1"][it["mb"]],
            p_value_raw=float(it["mB1"]["p_one_sided_nw"]),
            family_p_values=family_p_b,
            candidate_index_in_family=idx_i,
            cost_1x_net=float(it["mB1"]["total_ret_pct"]),
            cost_2x_net=float(it["mB2"]["total_ret_pct"]),
            n_trades_cluster_b=it["n_active_days_b"],
            incumbent_daily_returns=inc_b,
            annualization_days=365.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        beta_ok = abs(it["beta_btc_b"]) <= MAX_ABS_BETA_VS_BTC
        failed = list(verdict["failed_gates"])
        final_verdict = verdict["verdict"]
        if not beta_ok:
            failed.append("G_BETA_NEUTRALITY")
            if final_verdict == "APPROVE_FOR_INCUBATION":
                final_verdict = "CONDITIONAL_RETEST"
        if final_verdict == "APPROVE_FOR_INCUBATION":
            approved.append(it["id"])
        dsr_full = deflated_sharpe_ratio(it["r1"], n_trials=m_total, annualization=365.0)
        results.append({
            "id": it["id"],
            "tf": it["tf"],
            "family": it["fam"],
            "cluster_a_1x": it["mA1"],
            "cluster_a_2x": it["mA2"],
            "cluster_b_1x": it["mB1"],
            "cluster_b_2x": it["mB2"],
            "full_1x": it["mF1"],
            "bh_q_b": round(qb_all[idx_i], 5),
            "dsr_b": verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_b": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_sleeve2_b": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_sleeve2_b": verdict["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "corr_vs_sleeve3a_b": it["corr_s3a_b"],
            "beta_btc_a": it["beta_btc_a"],
            "beta_btc_b": it["beta_btc_b"],
            "corr_btc_b": it["corr_btc_b"],
            "avg_abs_net_exp": it["avg_abs_net_exp"],
            "max_gross_exp": it["max_gross_exp"],
            "price_pnl_b_pct": it["price_pnl_b_pct"],
            "funding_pnl_b_pct": it["funding_pnl_b_pct"],
            "cost_drag_1x_b_pct": it["cost_drag_1x_b_pct"],
            "council_verdict": final_verdict,
            "failed_gates": failed,
            "verdict_sha": verdict["verdict_sha256"],
        })

    exported_path = None
    if approved:
        # Select strictly by Cluster A Sharpe among Council-approved survivors (zero Cluster B selection bias!)
        best_id = max(approved, key=lambda aid: next(r["cluster_a_1x"]["sharpe"] for r in results if r["id"] == aid))
        best_r = next(r for r in results if r["id"] == best_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "sleeve_lab2_crypto_statarb",
            "strategy_name": best_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 365.0,
            "calendar_type": "24_7_calendar",
            "cost_assumption": "15 bps one-way per leg (30 bps RT per leg) + real 8h Binance funding + 100 bps delist haircut",
            "metrics_cluster_a": best_r["cluster_a_1x"],
            "metrics_cluster_b": best_r["cluster_b_1x"],
            "metrics_full": best_r["full_1x"],
            "beta_btc_cluster_b": best_r["beta_btc_b"],
            "daily_returns": daily_1x_map[best_id],
        }
        LAB2_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAB2_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(LAB2_RETURNS_PATH)

    summary = {
        "schema": "naqex-lab2-crypto-statarb-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "loaded_4h_coins": len(panel_4h["symbols"]),
        "loaded_1h_coins": len(panel_1h["symbols"]),
        "loaded_p20_coins": len(panel_4h_p20["symbols"]),
        "exact_funding_coins_4h": len(exact_4h),
        "exact_funding_coins_1h": len(exact_1h),
        "exact_funding_coins_p20": len(exact_p20),
        "m_total": m_total,
        "approved_count": len(approved),
        "approved_ids": approved,
        "exported_returns_path": exported_path,
        "results": results,
    }
    LAB2_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAB2_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="C1.2 Lab #2 Crypto Stat-Arb, Pairs & Market-Neutral Lab")
    ap.parse_args()
    s = run_lab2()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "loaded": {"4h": s["loaded_4h_coins"], "1h": s["loaded_1h_coins"], "p20": s["loaded_p20_coins"], "exact_fund_p20": s["exact_funding_coins_p20"]},
        "m_total": s["m_total"],
        "approved_count": s["approved_count"],
        "approved_ids": s["approved_ids"],
        "exported_returns_path": s["exported_returns_path"],
        "rows": [
            (
                r["id"], r["cluster_a_1x"]["cagr_pct"], r["cluster_a_1x"]["sharpe"],
                r["cluster_b_1x"]["cagr_pct"], r["cluster_b_2x"]["cagr_pct"], r["cluster_b_1x"]["sharpe"],
                r["beta_btc_b"], r["corr_vs_sleeve2_b"], r["funding_pnl_b_pct"], r["bh_q_b"], r["council_verdict"],
            )
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
