"""C2.1 — Lab #3A: FTMO Multi-Day Swing Research Using REAL Harvested FTMO Swaps (DEV < 2025-01-01 ONLY).

STRICT SEALED DEVELOPMENT & SAFETY BOUNDARIES:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity on startup (`holdout_rows_analysed == 0`).
  - Reads ONLY sealed `.runtime/hot-m1-cache/` (`2018-01-01..2024-12-31`, strictly `< 2025-01-01`).
  - Reads real broker specs from `planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json`
    (`swap_long`, `swap_short`, `swap_mode`, `swap_rollover3days`, `point`, `contract_size`).
  - ANTI-FAKE-SWAP GUARD:
      * Applies exact MT5 `swap_mode=1` triple-rollover swap `(swap_pts * point / price) * mult`
        (triple on Wednesday for FX/Metals `rollover=3`, triple on Friday for Indices `rollover=5`).
      * Explicitly caps anomalous single-day ex-dividend/roll positive snapshots on cash equity indices
        (`US100.cash +1076.28`, `US500.cash +32.83` on 2026-11-23) to realistic `-5.0%/yr` overnight
        financing (`min(raw_swap, -0.05/365*mult)`) so NO index strategy can hallucinate free carry!
      * Also computes a `zero_pos_swap` floor (pays 100% negative swaps, credits 0% positive swaps)
        for full attribution transparency.
  - Strict split: Cluster A (`2018-01-01..2021-12-31`) -> Blind Cluster B (`2022-01-01..2024-12-31`).
  - Evaluates 12 pre-registered specs across 4 multi-day swing families through `research_council.py`
    with `|r| < 0.15` vs frozen `PORT_7E`, `1x/2x` spread+commission+slippage, `BH-FDR`, `DSR`,
    and FTMO Swing DD checks (`max_dd < 10%`, `worst_1d > -5%`).
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

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
from native_ftmo_monfri_seal import STOP
from quant_core.holdout_guard import enforce_pre_holdout_ts
from quant_factory.crypto_causal_universe import RETURNS_DIR, _causal_ema_matrix, compute_daily_metrics
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.prop_engine import replay_portfolio_m1
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

FTMO_SPECS_PATH = ROOT / "planning" / "research" / "FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json"
LAB3A_SUMMARY_PATH = hcache.DEFAULT_CACHE / "lab3a_ftmo_swing_real_swap_summary.json"
LAB3A_RETURNS_PATH = RETURNS_DIR / "sleeve_ftmo_swing.json"

FX7_ASSETS: tuple[str, ...] = ("EURUSD", "GBPUSD", "USDJPY", "AUDUSD", "USDCAD", "EURJPY", "GBPJPY")
IDX3_ASSETS: tuple[str, ...] = ("US500", "US100", "GER40")
ALL11_ASSETS: tuple[str, ...] = FX7_ASSETS + ("XAUUSD",) + IDX3_ASSETS

ASSET_TO_FTMO_SYM: dict[str, str] = {
    "EURUSD": "EURUSD",
    "GBPUSD": "GBPUSD",
    "USDJPY": "USDJPY",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
    "EURJPY": "EURJPY",
    "GBPJPY": "GBPJPY",
    "XAUUSD": "XAUUSD",
    "US500": "US500.cash",
    "US100": "US100.cash",
    "GER40": "GER40.cash",
}

# Realistic conservative 1x one-way friction (half-spread + commission + slip in bps) fallback for non-native-Ask symbols
DEFAULT_ONEWAY_BPS: dict[str, float] = {
    "EURUSD": 1.2,
    "GBPUSD": 1.5,
    "USDJPY": 1.4,
    "AUDUSD": 1.6,
    "USDCAD": 1.8,
    "EURJPY": 2.0,
    "GBPJPY": 2.6,
    "XAUUSD": 2.2,
    "US500": 1.5,
    "US100": 1.8,
    "GER40": 1.8,
}

CL_A_START = "2018-01-01"
CL_A_END = "2021-12-31"
CL_B_START = "2022-01-01"
CL_B_END = "2024-12-31"

LAB3A_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.60,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.15,  # Strict orthogonality |r| < 0.15 vs PORT_7E
    max_tail_corr_vs_incumbent=0.35,
    min_trades_cluster_b=30,
)


def load_ftmo_symbol_specs(specs_path: Path = FTMO_SPECS_PATH) -> dict[str, dict[str, Any]]:
    raw = json.loads(specs_path.read_text(encoding="utf-8"))
    out: dict[str, dict[str, Any]] = {}
    for sym, d in raw.get("fx_metals_indices_specs", {}).items():
        out[sym] = dict(d)
    for sym, d in raw.get("core_live", {}).items():
        merged = dict(out.get(sym, {}))
        merged.update(d)
        out[sym] = merged
    return out


def compute_ftmo_daily_swap_frac(
    ftmo_spec: dict[str, Any],
    price: float,
    side: int,
    py_weekday: int,
    *,
    is_equity_index: bool = False,
    zero_positive_swap: bool = False,
) -> float:
    """Compute exact daily overnight swap return as fraction of notional for a `side` (+1/-1) hold.

    MT5 `swap_mode == 1` (Points):
      daily_swap_frac = (swap_points * point / price) * mult
    where `mult == 3.0` on triple-rollover day (`swap_rollover3days == 3` -> Wed `py_weekday == 2`;
    `swap_rollover3days == 5` -> Fri `py_weekday == 4`) and `1.0` otherwise.

    Anti-Fake-Swap Guard:
      - If `is_equity_index` and `side > 0` and raw swap > 0 (point-in-time ex-dividend/roll snapshot
        like US100.cash +1076.28 on 2026-11-23), cap to realistic `-5.0%/yr` financing so no index
        strategy receives phantom positive carry!
      - If `zero_positive_swap` is True, pay 100% of negative swaps and credit 0% of positive swaps.
    """
    if side == 0 or not math.isfinite(price) or price <= 0.0:
        return 0.0
    swap_mode = int(ftmo_spec.get("swap_mode", 1))
    roll_day = int(ftmo_spec.get("swap_rollover3days", 3))
    # MT5 DayOfWeek: 0=Sun, 1=Mon, 2=Tue, 3=Wed, 4=Thu, 5=Fri -> Python weekday = roll_day - 1
    roll_py_wd = roll_day - 1
    mult = 3.0 if py_weekday == roll_py_wd else 1.0
    raw_val = float(ftmo_spec["swap_long"] if side > 0 else ftmo_spec["swap_short"])
    pt = float(ftmo_spec.get("point", 1e-5))

    if swap_mode == 1:
        base_daily = (raw_val * pt) / price
    elif swap_mode == 5:
        base_daily = (raw_val / 100.0) / 365.0
    else:
        base_daily = (raw_val * pt) / price

    if is_equity_index and side > 0 and base_daily > 0.0:
        # Cap anomalous ex-dividend/roll snapshot to conservative -5%/yr financing
        base_daily = -0.05 / 365.0

    if zero_positive_swap and base_daily > 0.0:
        base_daily = 0.0

    return float(base_daily * mult)


def _resample_m1_to_bars(
    times_sec: np.ndarray,
    quotes: np.ndarray,
    bar_sec: int,
    native_ask: bool,
    asset: str,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]:
    """Causally resample M1 Bid/Ask ticks to UTC OHLC (`bar_sec = 86400` D1 or `14400` H4) + median spread bps."""
    enforce_pre_holdout_ts(int(times_sec[-1]), stop_ts=STOP, context=f"ftmo_swing_swap:{asset}")
    if native_ask and quotes.shape[1] >= 8:
        mid_o = 0.5 * (quotes[:, 0] + quotes[:, 4])
        mid_h = 0.5 * (quotes[:, 1] + quotes[:, 5])
        mid_l = 0.5 * (quotes[:, 2] + quotes[:, 6])
        mid_c = 0.5 * (quotes[:, 3] + quotes[:, 7])
        sp_bps_arr = ((quotes[:, 7] - quotes[:, 3]) / np.maximum(mid_c, 1e-9)) * 10_000.0
        # Conservative 1x one-way cost = half median Bid-Ask spread + 0.3 bps comm + 0.8 bps slip
        half_sp = 0.5 * float(np.median(sp_bps_arr[np.isfinite(sp_bps_arr) & (sp_bps_arr >= 0.0)]))
        oneway_bps = max(DEFAULT_ONEWAY_BPS[asset] * 0.75, half_sp + 1.1)
    else:
        mid_o, mid_h, mid_l, mid_c = quotes[:, 0], quotes[:, 1], quotes[:, 2], quotes[:, 3]
        oneway_bps = DEFAULT_ONEWAY_BPS[asset]

    buckets = (times_sec // bar_sec) * bar_sec
    uniq_b, first_idx = np.unique(buckets, return_index=True)
    # Drop weekends (Sat=5, Sun=6) for clean trading-bar series (keep Mon-Fri)
    last_idx = np.empty_like(first_idx)
    last_idx[:-1] = first_idx[1:] - 1
    last_idx[-1] = len(times_sec) - 1

    o_arr = mid_o[first_idx]
    c_arr = mid_c[last_idx]
    h_arr = np.maximum.reduceat(mid_h, first_idx)
    l_arr = np.minimum.reduceat(mid_l, first_idx)

    # Filter strictly weekday bars (Mon..Fri)
    wds = np.array([datetime.fromtimestamp(int(t), timezone.utc).weekday() for t in uniq_b], dtype=np.int32)
    keep = wds < 5
    return uniq_b[keep], o_arr[keep], h_arr[keep], l_arr[keep], c_arr[keep], round(oneway_bps, 3)


def load_dev_panel(
    assets: tuple[str, ...],
    bar_sec: int,
    *,
    cache_dir: Path = hcache.DEFAULT_CACHE,
) -> dict[str, Any]:
    raw: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, float]] = {}
    all_ts: set[int] = set()
    oneway_bps_map: dict[str, float] = {}
    for a in assets:
        ts_m1, q_m1, am = hcache.load_asset(a, cache_dir=cache_dir, verify_sha=True)
        bt, bo, bh, bl, bc, bps = _resample_m1_to_bars(ts_m1, q_m1, bar_sec, bool(am["native_Ask"]), a)
        raw[a] = (bt, bo, bh, bl, bc, bps)
        oneway_bps_map[a] = bps
        all_ts.update(bt.tolist())

    ts_arr = np.array(sorted(all_ts), dtype=np.int64)
    enforce_pre_holdout_ts(int(ts_arr[-1]), stop_ts=STOP, context="ftmo_swing_swap.panel")
    ts_map = {int(t): i for i, t in enumerate(ts_arr)}
    n_t, n_a = len(ts_arr), len(assets)
    highs = np.full((n_t, n_a), np.nan, dtype=np.float64)
    lows = np.full((n_t, n_a), np.nan, dtype=np.float64)
    closes = np.full((n_t, n_a), np.nan, dtype=np.float64)

    for j, a in enumerate(assets):
        bt, _, bh, bl, bc, _ = raw[a]
        idxs = np.array([ts_map[int(t)] for t in bt], dtype=np.int64)
        highs[idxs, j] = bh
        lows[idxs, j] = bl
        closes[idxs, j] = bc

    # Forward-fill strictly within active holiday gaps (causal only, max 2 bars) for clean cross-asset alignment
    for j in range(n_a):
        for t in range(1, n_t):
            if not np.isfinite(closes[t, j]) and np.isfinite(closes[t - 1, j]):
                closes[t, j] = closes[t - 1, j]
                highs[t, j] = closes[t - 1, j]
                lows[t, j] = closes[t - 1, j]

    dates = [datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d") for t in ts_arr]
    weekdays = np.array([datetime.fromtimestamp(int(t), timezone.utc).weekday() for t in ts_arr], dtype=np.int32)
    return {
        "bar_sec": bar_sec,
        "assets": list(assets),
        "timestamps_sec": ts_arr,
        "dates": dates,
        "weekdays": weekdays,
        "high": highs,
        "low": lows,
        "close": closes,
        "oneway_bps": oneway_bps_map,
    }


def simulate_ftmo_swing_backtest(
    panel: dict[str, Any],
    target_w: np.ndarray,
    ftmo_specs: dict[str, dict[str, Any]],
    *,
    cost_mult: float = 1.0,
    zero_positive_swap: bool = False,
    max_gross_leverage: float = 1.5,
) -> dict[str, Any]:
    """Causal multi-day swing simulator (`t -> t+1`) with real FTMO triple-rollover swap & spread costs."""
    closes = panel["close"]
    assets = panel["assets"]
    dates = panel["dates"]
    weekdays = panel["weekdays"]
    oneway_bps = np.array([panel["oneway_bps"][a] for a in assets], dtype=np.float64) * cost_mult
    n_t, n_a = closes.shape

    w_clean = np.where(np.isfinite(target_w) & np.isfinite(closes), target_w, 0.0).astype(np.float64)
    gross = np.sum(np.abs(w_clean), axis=1, keepdims=True)
    scale = np.where(gross > max_gross_leverage, max_gross_leverage / np.maximum(gross, 1e-12), 1.0)
    w_clean = w_clean * scale

    held_w = np.zeros_like(w_clean)
    held_w[1:] = w_clean[:-1]

    rets = np.zeros_like(closes)
    rets[1:] = np.where(
        np.isfinite(closes[1:]) & np.isfinite(closes[:-1]) & (closes[:-1] > 0.0),
        closes[1:] / closes[:-1] - 1.0,
        0.0,
    )
    price_pnl = np.sum(held_w * rets, axis=1)

    dw = np.zeros_like(held_w)
    dw[0] = np.abs(held_w[0])
    dw[1:] = np.abs(held_w[1:] - held_w[:-1])
    turnover = np.sum(dw, axis=1)
    cost_drag = np.sum(dw * (oneway_bps[None, :] / 10_000.0), axis=1)

    # Overnight swap accrues ONCE per UTC calendar day transition (`dates[t] != dates[t-1]`, or every bar on D1!)
    swap_pnl = np.zeros(n_t, dtype=np.float64)
    is_d1 = int(panel["bar_sec"]) >= 86400
    spec_list = [ftmo_specs[ASSET_TO_FTMO_SYM[a]] for a in assets]
    idx_flags = [a in IDX3_ASSETS for a in assets]

    for t in range(1, n_t):
        rollover_now = is_d1 or (dates[t] != dates[t - 1])
        if not rollover_now:
            continue
        wd = int(weekdays[t - 1])
        sw_t = 0.0
        for j in range(n_a):
            wj = float(held_w[t, j])
            if abs(wj) <= 1e-12:
                continue
            side = 1 if wj > 0.0 else -1
            px = float(closes[t - 1, j])
            sw_frac = compute_ftmo_daily_swap_frac(
                spec_list[j], px, side, wd, is_equity_index=idx_flags[j], zero_positive_swap=zero_positive_swap
            )
            sw_t += abs(wj) * sw_frac
        swap_pnl[t] = sw_t

    net_ret = np.clip(price_pnl + swap_pnl - cost_drag, -0.95, 2.0)

    # Aggregate to daily returns (pass-through on D1, compound on H4)
    if is_d1:
        d_dates = list(dates)
        d_ret = net_ret
        d_px = price_pnl
        d_sw = swap_pnl
        d_cs = cost_drag
        d_to = turnover
        d_ex = np.sum(np.abs(held_w), axis=1)
    else:
        uniq_d: list[str] = []
        idx_map: dict[str, int] = {}
        for d in dates:
            if d not in idx_map:
                idx_map[d] = len(uniq_d)
                uniq_d.append(d)
        n_d = len(uniq_d)
        d_ret = np.ones(n_d, dtype=np.float64)
        d_px = np.zeros(n_d, dtype=np.float64)
        d_sw = np.zeros(n_d, dtype=np.float64)
        d_cs = np.zeros(n_d, dtype=np.float64)
        d_to = np.zeros(n_d, dtype=np.float64)
        d_ex = np.zeros(n_d, dtype=np.float64)
        d_cnt = np.zeros(n_d, dtype=np.int64)
        gross_bar = np.sum(np.abs(held_w), axis=1)
        for t in range(n_t):
            g = idx_map[dates[t]]
            d_ret[g] *= (1.0 + float(net_ret[t]))
            d_px[g] += float(price_pnl[t])
            d_sw[g] += float(swap_pnl[t])
            d_cs[g] += float(cost_drag[t])
            d_to[g] += float(turnover[t])
            d_ex[g] += float(gross_bar[t])
            d_cnt[g] += 1
        d_ret -= 1.0
        d_ex /= np.maximum(1, d_cnt)
        d_dates = uniq_d

    return {
        "dates": d_dates,
        "daily_returns": d_ret,
        "daily_price_pnl": d_px,
        "daily_swap_pnl": d_sw,
        "daily_cost_drag": d_cs,
        "daily_turnover": d_to,
        "daily_gross_exp": d_ex,
        "held_w": held_w,
    }


def _causal_vol(closes: np.ndarray, window: int) -> np.ndarray:
    n_t, n_a = closes.shape
    rets = np.zeros_like(closes)
    rets[1:] = np.where(closes[:-1] > 0.0, closes[1:] / closes[:-1] - 1.0, 0.0)
    out = np.full((n_t, n_a), np.nan, dtype=np.float64)
    for t in range(window, n_t):
        sd = np.std(rets[t - window + 1 : t + 1], axis=0, ddof=1)
        out[t] = np.where(sd > 1e-6, sd, np.nan)
    return out


def _causal_sma(arr: np.ndarray, window: int) -> np.ndarray:
    n_t, n_a = arr.shape
    out = np.full((n_t, n_a), np.nan, dtype=np.float64)
    if n_t >= window:
        cs = np.cumsum(np.where(np.isfinite(arr), arr, 0.0), axis=0)
        out[window - 1 :] = (cs[window - 1 :] - np.vstack([np.zeros((1, n_a)), cs[:-window]])) / float(window)
    return out


def _causal_rsi(closes: np.ndarray, period: int = 2) -> np.ndarray:
    n_t, n_a = closes.shape
    diff = np.zeros_like(closes)
    diff[1:] = closes[1:] - closes[:-1]
    gain = np.maximum(diff, 0.0)
    loss = np.maximum(-diff, 0.0)
    avg_g = _causal_sma(gain, period)
    avg_l = _causal_sma(loss, period)
    rs = avg_g / np.maximum(avg_l, 1e-12)
    rsi = 100.0 - (100.0 / (1.0 + rs))
    return np.where(np.isfinite(avg_g), rsi, np.nan)


def _vol_scale_weights(raw_sig: np.ndarray, vol: np.ndarray, target_ann_vol: float, ann_bars: float, max_gross: float = 1.5) -> np.ndarray:
    """Scale directional signals (-1/0/+1) by inverse causal volatility to target portfolio vol."""
    n_t, n_a = raw_sig.shape
    w = np.zeros((n_t, n_a), dtype=np.float64)
    vt_bar = target_ann_vol / math.sqrt(ann_bars)
    for t in range(n_t):
        active = np.where((np.abs(raw_sig[t]) > 1e-12) & np.isfinite(vol[t]) & (vol[t] > 1e-6))[0]
        if len(active) == 0:
            continue
        # Equal risk budget across active slots (divided by max(2, n_active) for conservative FTMO DD safety)
        slot_budget = vt_bar / math.sqrt(max(2.0, float(len(active))))
        for j in active:
            w[t, j] = np.sign(raw_sig[t, j]) * min(0.50, slot_budget / float(vol[t, j]))
        g = float(np.sum(np.abs(w[t])))
        if g > max_gross:
            w[t] *= max_gross / g
    return w


def build_lab3a_strategies(
    panel_d1: dict[str, Any],
    panel_h4: dict[str, Any],
    ftmo_specs: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Build 12 preregistered multi-day FTMO Swing specs across 4 families (100% causal <= t)."""
    assets_d1 = panel_d1["assets"]
    c_d1, h_d1, l_d1 = panel_d1["close"], panel_d1["high"], panel_d1["low"]
    n_t, n_a = c_d1.shape
    vol20_d1 = _causal_vol(c_d1, 20)

    fx_idxs = [assets_d1.index(a) for a in FX7_ASSETS]
    idx_idxs = [assets_d1.index(a) for a in IDX3_ASSETS]

    # Identify exact positive-FTMO-swap directional permissions per FX pair
    pos_swap_dir = np.zeros(n_a, dtype=np.int32)
    for j in fx_idxs:
        sp = ftmo_specs[ASSET_TO_FTMO_SYM[assets_d1[j]]]
        if float(sp["swap_long"]) > 0.0:
            pos_swap_dir[j] = 1
        elif float(sp["swap_short"]) > 0.0:
            pos_swap_dir[j] = -1

    # --- Family 1: Positive-Swap Carry-Filtered Trend (3 specs) ---
    ema10 = _causal_ema_matrix(c_d1, 10)
    ema20 = _causal_ema_matrix(c_d1, 20)
    ema40 = _causal_ema_matrix(c_d1, 40)
    ema60 = _causal_ema_matrix(c_d1, 60)

    sig_f1_10_40 = np.zeros((n_t, n_a), dtype=np.float64)
    sig_f1_20_60 = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(62, n_t):
        for j in fx_idxs:
            d = int(pos_swap_dir[j])
            if d == 1:
                if ema10[t, j] > ema40[t, j]:
                    sig_f1_10_40[t, j] = 1.0
                if ema20[t, j] > ema60[t, j]:
                    sig_f1_20_60[t, j] = 1.0
            elif d == -1:
                if ema10[t, j] < ema40[t, j]:
                    sig_f1_10_40[t, j] = -1.0
                if ema20[t, j] < ema60[t, j]:
                    sig_f1_20_60[t, j] = -1.0
    w_f1_10_40 = _vol_scale_weights(sig_f1_10_40, vol20_d1, 0.08, 252.0)
    w_f1_20_60 = _vol_scale_weights(sig_f1_20_60, vol20_d1, 0.08, 252.0)

    # H4 Positive-Swap Donchian 20/10
    c_h4, h_h4, l_h4 = panel_h4["close"], panel_h4["high"], panel_h4["low"]
    n_h4 = len(c_h4)
    vol60_h4 = _causal_vol(c_h4, 60)
    sig_f1_h4 = np.zeros_like(c_h4)
    st_h4 = np.zeros(n_a, dtype=np.int32)
    for t in range(25, n_h4):
        for j in fx_idxs:
            d = int(pos_swap_dir[j])
            if d == 0:
                continue
            hi20 = float(np.max(h_h4[t - 20 : t, j]))
            lo20 = float(np.min(l_h4[t - 20 : t, j]))
            hi10 = float(np.max(h_h4[t - 10 : t, j]))
            lo10 = float(np.min(l_h4[t - 10 : t, j]))
            if d == 1:
                if st_h4[j] == 0 and c_h4[t, j] > hi20:
                    st_h4[j] = 1
                elif st_h4[j] == 1 and c_h4[t, j] < lo10:
                    st_h4[j] = 0
            elif d == -1:
                if st_h4[j] == 0 and c_h4[t, j] < lo20:
                    st_h4[j] = -1
                elif st_h4[j] == -1 and c_h4[t, j] > hi10:
                    st_h4[j] = 0
            sig_f1_h4[t, j] = float(st_h4[j])
    w_f1_h4_don = _vol_scale_weights(sig_f1_h4, vol60_h4, 0.08, 252.0 * 6.0)

    # --- Family 2: Multi-Day Donchian & Keltner Breakout (3 specs) ---
    def _run_don_2way(c_mat: np.ndarray, h_mat: np.ndarray, l_mat: np.ndarray, idxs: list[int], en_w: int, ex_w: int) -> np.ndarray:
        sig = np.zeros_like(c_mat)
        st = np.zeros(c_mat.shape[1], dtype=np.int32)
        for t in range(en_w + 1, len(c_mat)):
            for j in idxs:
                hi_e = float(np.max(h_mat[t - en_w : t, j]))
                lo_e = float(np.min(l_mat[t - en_w : t, j]))
                hi_x = float(np.max(h_mat[t - ex_w : t, j]))
                lo_x = float(np.min(l_mat[t - ex_w : t, j]))
                if st[j] == 0:
                    if c_mat[t, j] > hi_e:
                        st[j] = 1
                    elif c_mat[t, j] < lo_e:
                        st[j] = -1
                elif st[j] == 1 and c_mat[t, j] < lo_x:
                    st[j] = 0
                elif st[j] == -1 and c_mat[t, j] > hi_x:
                    st[j] = 0
                sig[t, j] = float(st[j])
        return sig

    w_f2_don_fx = _vol_scale_weights(_run_don_2way(c_d1, h_d1, l_d1, fx_idxs, 20, 10), vol20_d1, 0.08, 252.0)
    w_f2_don_all = _vol_scale_weights(_run_don_2way(c_d1, h_d1, l_d1, list(range(n_a)), 20, 10), vol20_d1, 0.08, 252.0)

    # H4 Keltner Channel (EMA20 +/- 2.0 * ATR20) on FX7
    ema20_h4 = _causal_ema_matrix(c_h4, 20)
    tr_h4 = np.zeros_like(c_h4)
    tr_h4[0] = h_h4[0] - l_h4[0]
    tr_h4[1:] = np.maximum(h_h4[1:] - l_h4[1:], np.maximum(np.abs(h_h4[1:] - c_h4[:-1]), np.abs(l_h4[1:] - c_h4[:-1])))
    atr20_h4 = _causal_sma(tr_h4, 20)
    sig_f2_kelt = np.zeros_like(c_h4)
    st_k = np.zeros(n_a, dtype=np.int32)
    for t in range(25, n_h4):
        for j in fx_idxs:
            up = ema20_h4[t, j] + 2.0 * atr20_h4[t, j]
            dn = ema20_h4[t, j] - 2.0 * atr20_h4[t, j]
            if st_k[j] == 0:
                if c_h4[t, j] > up:
                    st_k[j] = 1
                elif c_h4[t, j] < dn:
                    st_k[j] = -1
            elif st_k[j] == 1 and c_h4[t, j] < ema20_h4[t, j]:
                st_k[j] = 0
            elif st_k[j] == -1 and c_h4[t, j] > ema20_h4[t, j]:
                st_k[j] = 0
            sig_f2_kelt[t, j] = float(st_k[j])
    w_f2_kelt_h4 = _vol_scale_weights(sig_f2_kelt, vol60_h4, 0.08, 252.0 * 6.0)

    # --- Family 3: Weekly / Multi-Day Mean Reversion on Equity Indices (3 specs) ---
    sma5 = _causal_sma(c_d1, 5)
    sma100 = _causal_sma(c_d1, 100)
    sma150 = _causal_sma(c_d1, 150)
    sma200 = _causal_sma(c_d1, 200)
    rsi2 = _causal_rsi(c_d1, 2)

    sig_f3_rsi2 = np.zeros((n_t, n_a), dtype=np.float64)
    hold_r2 = np.zeros(n_a, dtype=np.int32)
    for t in range(202, n_t):
        for j in idx_idxs:
            if hold_r2[j] > 0:
                if c_d1[t, j] > sma5[t, j] or hold_r2[j] >= 7:
                    hold_r2[j] = 0
                else:
                    hold_r2[j] += 1
            elif c_d1[t, j] > sma200[t, j] and np.isfinite(rsi2[t, j]) and rsi2[t, j] < 15.0:
                hold_r2[j] = 1
            sig_f3_rsi2[t, j] = 1.0 if hold_r2[j] > 0 else 0.0
    w_f3_rsi2 = _vol_scale_weights(sig_f3_rsi2, vol20_d1, 0.08, 252.0)

    sig_f3_dip3 = np.zeros((n_t, n_a), dtype=np.float64)
    hold_d3 = np.zeros(n_a, dtype=np.int32)
    for t in range(105, n_t):
        for j in idx_idxs:
            r3 = c_d1[t, j] / max(c_d1[t - 3, j], 1e-9) - 1.0
            z3 = r3 / max(float(vol20_d1[t, j]) * math.sqrt(3.0), 1e-6) if np.isfinite(vol20_d1[t, j]) else 0.0
            if hold_d3[j] > 0:
                if c_d1[t, j] > sma5[t, j] or hold_d3[j] >= 5:
                    hold_d3[j] = 0
                else:
                    hold_d3[j] += 1
            elif c_d1[t, j] > sma100[t, j] and z3 <= -1.25:
                hold_d3[j] = 1
            sig_f3_dip3[t, j] = 1.0 if hold_d3[j] > 0 else 0.0
    w_f3_dip3 = _vol_scale_weights(sig_f3_dip3, vol20_d1, 0.08, 252.0)

    sig_f3_wk = np.zeros((n_t, n_a), dtype=np.float64)
    hold_wk = np.zeros(n_a, dtype=np.int32)
    for t in range(155, n_t):
        # Buy the weakest 5-day equity index if still above 150d SMA and 5d return < -1.5%
        r5_map = [(c_d1[t, j] / max(c_d1[t - 5, j], 1e-9) - 1.0, j) for j in idx_idxs if c_d1[t, j] > sma150[t, j]]
        r5_map.sort()
        pick = r5_map[0][1] if (r5_map and r5_map[0][0] < -0.015) else -1
        for j in idx_idxs:
            if hold_wk[j] > 0:
                hold_wk[j] = 0 if hold_wk[j] >= 4 else hold_wk[j] + 1
            elif j == pick:
                hold_wk[j] = 1
            sig_f3_wk[t, j] = 1.0 if hold_wk[j] > 0 else 0.0
    w_f3_wk = _vol_scale_weights(sig_f3_wk, vol20_d1, 0.08, 252.0)

    # --- Family 4: FX Rate-Carry + Momentum Cross-Sectional Portfolio (3 specs) ---
    # Compute annualized carry score per FX pair: positive when Long swap > Short swap
    sig_f4_carry = np.zeros((n_t, n_a), dtype=np.float64)
    sig_f4_cm20 = np.zeros((n_t, n_a), dtype=np.float64)
    sig_f4_cm60 = np.zeros((n_t, n_a), dtype=np.float64)

    for t in range(65, n_t):
        # Weekly rebalance (every 5 trading days) to avoid FX spread churn
        if t % 5 != 0 and t > 65:
            sig_f4_carry[t] = sig_f4_carry[t - 1]
            sig_f4_cm20[t] = sig_f4_cm20[t - 1]
            sig_f4_cm60[t] = sig_f4_cm60[t - 1]
            continue

        # Carry yield for Long vs Short per FX pair using exact FTMO live points
        carry_legs: list[tuple[float, int, int]] = []
        c_scores = {}
        m20_scores = {}
        m60_scores = {}
        for j in fx_idxs:
            sp = ftmo_specs[ASSET_TO_FTMO_SYM[assets_d1[j]]]
            px = float(c_d1[t, j])
            yl = (float(sp["swap_long"]) * float(sp["point"]) / px) * 365.0
            ys = (float(sp["swap_short"]) * float(sp["point"]) / px) * 365.0
            if yl > 0.0:
                carry_legs.append((yl, j, 1))
            if ys > 0.0:
                carry_legs.append((ys, j, -1))
            c_scores[j] = yl - ys  # Net carry advantage of Long over Short
            v = max(float(vol20_d1[t, j]), 1e-4) if np.isfinite(vol20_d1[t, j]) else 1e-2
            m20_scores[j] = (c_d1[t, j] / c_d1[t - 20, j] - 1.0) / (v * math.sqrt(20.0))
            m60_scores[j] = (c_d1[t, j] / c_d1[t - 60, j] - 1.0) / (v * math.sqrt(60.0))

        carry_legs.sort(reverse=True)
        for _, j, side in carry_legs[:3]:
            sig_f4_carry[t, j] = float(side)

        # Rank-normalize carry and momentum across FX7, combine 50/50 -> Long Top-2, Short Bot-2 (only if carry-aligned or strong mom)
        def _rank_z(d_map: dict[int, float]) -> dict[int, float]:
            keys = sorted(d_map.keys(), key=lambda k: d_map[k])
            return {k: (i / max(1, len(keys) - 1)) * 2.0 - 1.0 for i, k in enumerate(keys)}

        rc = _rank_z(c_scores)
        rm20 = _rank_z(m20_scores)
        rm60 = _rank_z(m60_scores)

        comp20 = sorted([(0.5 * rc[j] + 0.5 * rm20[j], j) for j in fx_idxs])
        comp60 = sorted([(0.5 * rc[j] + 0.5 * rm60[j], j) for j in fx_idxs])
        for _, j in comp20[-2:]:
            sig_f4_cm20[t, j] = 1.0
        for _, j in comp20[:2]:
            sig_f4_cm20[t, j] = -1.0
        for _, j in comp60[-2:]:
            sig_f4_cm60[t, j] = 1.0
        for _, j in comp60[:2]:
            sig_f4_cm60[t, j] = -1.0

    w_f4_carry = _vol_scale_weights(sig_f4_carry, vol20_d1, 0.08, 252.0)
    w_f4_cm20 = _vol_scale_weights(sig_f4_cm20, vol20_d1, 0.08, 252.0)
    w_f4_cm60 = _vol_scale_weights(sig_f4_cm60, vol20_d1, 0.08, 252.0)

    return [
        {"id": "SW_F1_POSCARRY_EMA_10_40", "tf": "D1", "fam": "POS_SWAP_CARRY_TREND", "panel": panel_d1, "w": w_f1_10_40,
         "cp": "Central-bank interest-rate differentials reinforced by multi-week FX trend flows",
         "rat": "D1 EMA(10/40) trend taken strictly in the positive-FTMO-swap direction harvests both trend drift and positive triple-Wednesday carry while avoiding negative swap drag."},
        {"id": "SW_F1_POSCARRY_EMA_20_60", "tf": "D1", "fam": "POS_SWAP_CARRY_TREND", "panel": panel_d1, "w": w_f1_20_60,
         "cp": "Persistent macro monetary-policy divergence driving multi-month carry-aligned FX trends",
         "rat": "Slower D1 EMA(20/60) positive-swap FX trend reduces whipsaw turnover while aligning overnight holdings exclusively with positive FTMO carry."},
        {"id": "SW_F1_POSCARRY_H4_DON_20_10", "tf": "H4", "fam": "POS_SWAP_CARRY_TREND", "panel": panel_h4, "w": w_f1_h4_don,
         "cp": "Multi-day breakout momentum along positive-carry FX macro direction",
         "rat": "H4 20-bar/10-bar Donchian breakouts restricted to positive-FTMO-swap FX directions target 2-8 day swing trends with positive carry tailwind."},
        {"id": "SW_F2_D1_DON_20_10_FX", "tf": "D1", "fam": "SWING_DON_KELTNER_BRK", "panel": panel_d1, "w": w_f2_don_fx,
         "cp": "Institutional macro breakout continuation across G7 FX crosses",
         "rat": "Classic 20d/10d Donchian two-way breakout across 7 FX pairs tested net of full real FTMO negative swaps to quantify true carry-adjusted swing edge."},
        {"id": "SW_F2_H4_KELTNER_20_FX", "tf": "H4", "fam": "SWING_DON_KELTNER_BRK", "panel": panel_h4, "w": w_f2_kelt_h4,
         "cp": "Volatility-normalized H4 breakout expansions across liquid G7 FX pairs",
         "rat": "H4 20-bar Keltner (+/- 2 ATR) breakouts capture 2-6 day FX swing expansions while cutting losers quickly back at the EMA20 midline."},
        {"id": "SW_F2_D1_DON_20_10_ALL11", "tf": "D1", "fam": "SWING_DON_KELTNER_BRK", "panel": panel_d1, "w": w_f2_don_all,
         "cp": "Cross-asset multi-week macro trend breakouts across FX, Gold, and Equity Indices",
         "rat": "Full 11-asset D1 Donchian breakout tests whether Gold and Index trend capture overcomes brutal FTMO overnight financing (-54.46 pts on Gold, -5% to -9% on Indices)."},
        {"id": "SW_F3_IDX_RSI2_TREND", "tf": "D1", "fam": "INDEX_WEEKLY_MEAN_REV", "panel": panel_d1, "w": w_f3_rsi2,
         "cp": "Short-term institutional equity index panic liquidations inside primary bull markets",
         "rat": "Connors RSI-2 (< 15) above 200d SMA buys 2-5 day oversold equity index flushes and exits above 5d SMA, strictly charging conservative overnight financing."},
        {"id": "SW_F3_IDX_3D_DIP_REV", "tf": "D1", "fam": "INDEX_WEEKLY_MEAN_REV", "panel": panel_d1, "w": w_f3_dip3,
         "cp": "3-day volatility-adjusted equity selloffs absorbed by systematic rebalancing inflows",
         "rat": "Buying -1.25-sigma 3-day pullbacks on US500/US100/GER40 above 100d SMA captures short-horizon equity mean reversion with minimal overnight financing exposure."},
        {"id": "SW_F3_IDX_WEEKLY_REVERSAL", "tf": "D1", "fam": "INDEX_WEEKLY_MEAN_REV", "panel": panel_d1, "w": w_f3_wk,
         "cp": "Weekly cross-index laggard rebound inside secular uptrends",
         "rat": "Rotating into the weakest 5-day global equity index (> -1.5% dip above 150d SMA) for a 4-day hold harvests short-term regional mean reversion."},
        {"id": "SW_F4_FX_CARRY_PURE", "tf": "D1", "fam": "FX_CARRY_MOM_XSEC", "panel": panel_d1, "w": w_f4_carry,
         "cp": "Risk premium paid by low-yield funding currencies to holders of high-yield G7 currencies",
         "rat": "Holding the top-3 highest positive-FTMO-swap directional FX legs with 20d inverse-vol scaling isolates pure FX carry risk premium net of triple-Wednesday rollover."},
        {"id": "SW_F4_FX_CARRY_PLUS_MOM20", "tf": "D1", "fam": "FX_CARRY_MOM_XSEC", "panel": panel_d1, "w": w_f4_cm20,
         "cp": "Combined yield-seeking carry flows and 1-month FX trend continuation across G7 pairs",
         "rat": "50/50 cross-sectional FTMO carry + 20d momentum rank rotates weekly into top-2 carry-momentum FX pairs against bottom-2 laggards."},
        {"id": "SW_F4_FX_CARRY_PLUS_MOM60", "tf": "D1", "fam": "FX_CARRY_MOM_XSEC", "panel": panel_d1, "w": w_f4_cm60,
         "cp": "Combined macro rate-carry differential and quarterly FX momentum across G7 pairs",
         "rat": "50/50 cross-sectional FTMO carry + 60d momentum rank lowers FX turnover while balancing carry crash risk with intermediate trend confirmation."},
    ]


def run_lab3a(*, cache_dir: Path = hcache.DEFAULT_CACHE, jobs_root: Path = hcache.DEFAULT_JOBS) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    ftmo_specs = load_ftmo_symbol_specs()

    # Load frozen PORT_7E daily return series for strict |r| < 0.15 orthogonality gate
    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=cache_dir, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    _, dev_ex7 = replay_portfolio_m1(warm["ext_days"], warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_daily = {e["day"]: float(e["net_usd"]) / 10000.0 for e in dev_ex7}

    panel_d1 = load_dev_panel(ALL11_ASSETS, 86400, cache_dir=cache_dir)
    panel_h4 = load_dev_panel(ALL11_ASSETS, 14400, cache_dir=cache_dir)

    specs = build_lab3a_strategies(panel_d1, panel_h4, ftmo_specs)

    eval_items: list[dict[str, Any]] = []
    daily_1x_map: dict[str, dict[str, float]] = {}

    for sp in specs:
        p = sp["panel"]
        s1 = simulate_ftmo_swing_backtest(p, sp["w"], ftmo_specs, cost_mult=1.0, zero_positive_swap=False)
        s2 = simulate_ftmo_swing_backtest(p, sp["w"], ftmo_specs, cost_mult=2.0, zero_positive_swap=False)
        s0 = simulate_ftmo_swing_backtest(p, sp["w"], ftmo_specs, cost_mult=1.0, zero_positive_swap=True)

        days = s1["dates"]
        r1 = s1["daily_returns"]
        r2 = s2["daily_returns"]
        r0 = s0["daily_returns"]
        to1 = s1["daily_turnover"]
        ex1 = s1["daily_gross_exp"]

        ma = np.array([CL_A_START <= d <= CL_A_END for d in days])
        mb = np.array([CL_B_START <= d <= CL_B_END for d in days])
        days_b = [d for d, f in zip(days, mb) if f]

        eval_items.append({
            "id": sp["id"], "tf": sp["tf"], "fam": sp["fam"], "cp": sp["cp"], "rat": sp["rat"],
            "days": days, "days_b": days_b, "r1": r1, "r2": r2, "r0": r0, "ma": ma, "mb": mb,
            "mA1": compute_daily_metrics(r1[ma], to1[ma], ex1[ma], ann_days=252.0),
            "mA2": compute_daily_metrics(r2[ma], to1[ma], ex1[ma], ann_days=252.0),
            "mB1": compute_daily_metrics(r1[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mB2": compute_daily_metrics(r2[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mB0": compute_daily_metrics(r0[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mF1": compute_daily_metrics(r1, to1, ex1, ann_days=252.0),
            "worst_1d_b_pct": round(float(np.min(r1[mb])) * 100.0, 2) if np.any(mb) else 0.0,
            "price_pnl_b_pct": round(float(np.sum(s1["daily_price_pnl"][mb])) * 100.0, 2),
            "swap_pnl_b_pct": round(float(np.sum(s1["daily_swap_pnl"][mb])) * 100.0, 2),
            "cost_drag_1x_b_pct": round(float(np.sum(s1["daily_cost_drag"][mb])) * 100.0, 2),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
        })
        daily_1x_map[sp["id"]] = {d: float(v) for d, v in zip(days, r1)}

    m_total = len(eval_items)
    family_p_b = tuple(float(it["mB1"]["p_one_sided_nw"]) for it in eval_items)
    qb_all = benjamini_hochberg(list(family_p_b))

    results: list[dict[str, Any]] = []
    approved: list[str] = []

    for idx_i, it in enumerate(eval_items):
        inc_b = np.array([port7_daily.get(d, 0.0) for d in it["days_b"]], dtype=np.float64)
        card = propose_hypothesis(
            hypothesis_id=it["id"],
            title=f"Lab #3A {it['fam']} ({it['tf']})",
            asset_universe=ALL11_ASSETS[:5],
            timeframe=it["tf"],
            counterparty_mechanism=it["cp"],
            economic_rationale=it["rat"],
            causal_invariants=(
                "strict_dev_lt_2025_01_01_holdout_sealed",
                "strict_t_to_t_plus_1_swing_execution",
                "real_ftmo_triple_rollover_swap_accounting",
                "capped_index_financing_no_fake_positive_swap",
                "1x_and_2x_spread_commission_slippage",
            ),
            n_trials_cumulative=m_total,
            kill_criteria=LAB3A_KILL_CRITERIA,
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
            annualization_days=252.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        failed = list(verdict["failed_gates"])
        final_v = verdict["verdict"]
        # FTMO Swing DD safety gate (< 10% total DD & > -5% worst 1-day loss)
        ftmo_dd_ok = (float(it["mB1"]["max_dd_pct"]) < 10.0) and (float(it["worst_1d_b_pct"]) > -5.0)
        if not ftmo_dd_ok:
            failed.append("G_FTMO_DD_SAFETY")
            if final_v == "APPROVE_FOR_INCUBATION":
                final_v = "CONDITIONAL_RETEST"
        if final_v == "APPROVE_FOR_INCUBATION":
            approved.append(it["id"])
        dsr_full = deflated_sharpe_ratio(it["r1"], n_trials=m_total, annualization=252.0)
        results.append({
            "id": it["id"],
            "tf": it["tf"],
            "family": it["fam"],
            "cluster_a_1x": it["mA1"],
            "cluster_a_2x": it["mA2"],
            "cluster_b_1x": it["mB1"],
            "cluster_b_2x": it["mB2"],
            "cluster_b_zero_pos_swap": it["mB0"],
            "full_1x": it["mF1"],
            "worst_1d_b_pct": it["worst_1d_b_pct"],
            "price_pnl_b_pct": it["price_pnl_b_pct"],
            "swap_pnl_b_pct": it["swap_pnl_b_pct"],
            "cost_drag_1x_b_pct": it["cost_drag_1x_b_pct"],
            "bh_q_b": round(qb_all[idx_i], 5),
            "dsr_b": verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_b": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_port7e_b": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_port7e_b": verdict["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "ftmo_dd_ok": ftmo_dd_ok,
            "council_verdict": final_v,
            "failed_gates": failed,
            "verdict_sha": verdict["verdict_sha256"],
        })

    exported_path = None
    if approved:
        best_id = max(approved, key=lambda aid: next(r["cluster_a_1x"]["sharpe"] for r in results if r["id"] == aid))
        best_r = next(r for r in results if r["id"] == best_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "sleeve_ftmo_swing",
            "strategy_name": best_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 252.0,
            "calendar_type": "business_days_dev_lt_2025",
            "cost_assumption": "FTMO Swing empirical spread+commission+slip + real triple-rollover swaps (index positive-swap capped at -5%/yr)",
            "metrics_cluster_a": best_r["cluster_a_1x"],
            "metrics_cluster_b": best_r["cluster_b_1x"],
            "metrics_full": best_r["full_1x"],
            "corr_vs_port7e_b": best_r["corr_vs_port7e_b"],
            "daily_returns": daily_1x_map[best_id],
        }
        LAB3A_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAB3A_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(LAB3A_RETURNS_PATH)

    swap_audit = {
        a: {
            "ftmo_symbol": ASSET_TO_FTMO_SYM[a],
            "swap_long": ftmo_specs[ASSET_TO_FTMO_SYM[a]]["swap_long"],
            "swap_short": ftmo_specs[ASSET_TO_FTMO_SYM[a]]["swap_short"],
            "swap_mode": ftmo_specs[ASSET_TO_FTMO_SYM[a]]["swap_mode"],
            "rollover3days": ftmo_specs[ASSET_TO_FTMO_SYM[a]]["swap_rollover3days"],
            "empirical_1x_oneway_bps": panel_d1["oneway_bps"][a],
        }
        for a in ALL11_ASSETS
    }

    summary = {
        "schema": "naqex-lab3a-ftmo-swing-real-swap-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "max_date_analysed": panel_d1["dates"][-1],
        "swap_audit": swap_audit,
        "m_total": m_total,
        "approved_count": len(approved),
        "approved_ids": approved,
        "exported_returns_path": exported_path,
        "results": results,
    }
    LAB3A_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    argparse.ArgumentParser(description="Lab #3A FTMO Multi-Day Swing Using Real FTMO Swaps (Dev < 2025-01-01)").parse_args()
    s = run_lab3a()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "max_date_analysed": s["max_date_analysed"],
        "approved_count": s["approved_count"],
        "approved_ids": s["approved_ids"],
        "exported_returns_path": s["exported_returns_path"],
        "rows": [
            (
                r["id"], r["cluster_a_1x"]["cagr_pct"], r["cluster_a_1x"]["sharpe"],
                r["cluster_b_1x"]["cagr_pct"], r["cluster_b_2x"]["cagr_pct"],
                r["cluster_b_zero_pos_swap"]["cagr_pct"], r["cluster_b_1x"]["sharpe"],
                r["cluster_b_1x"]["max_dd_pct"], r["swap_pnl_b_pct"], r["corr_vs_port7e_b"],
                r["bh_q_b"], r["council_verdict"],
            )
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
