"""Wave-2 Cycle 4F — Lab #9: Multi-Coin Diversified Perpetual Funding Carry v2 (S3A v2)
& Tail-Risk Reduction Study (2020-2026, 20 Liquid Binance Perpetuals).

Motivation:
  In Wave-2 Cycle 3 (`portfolio_allocator.py`), incumbent `S3A_FUND_CARRY` (`BTC+ETH` static
  conservative carry) displayed a Frechet heavy left tail (`evt_xi = +0.0718` on 2020-2024
  Mon-Fri compounded returns) and high 2-coin concentration. This study tests whether a
  strictly causal Multi-Coin Funding Carry v2 (`S3A v2`) with hysteresis thresholds,
  inverse-volatility weighting, per-coin caps, 2.0x/2.5x CEX margin buffers, and regime/bear
  circuit breakers dominates `S3A v1` on Blind Cluster B Sharpe, Calmar, MaxDD, AND EVT left-
  tail index `xi` + P99 1-year GARCH-EVT crash drawdown.

STRICT ANTI-BIAS & FAIL-CLOSED BOUNDARIES:
  - 100% offline over cached read-only `.runtime/crypto-spot-cache/funding/` & `1d/` Parquets
    (ZERO network calls, ZERO API keys, OrderSend = 0).
  - Holdout 2025+ FX/Idx remains 100% SEALED (`holdout_rows_analysed = 0`; Gate 4 orthogonality
    vs `S1` uses strictly Dev `<= 2024-12-31` with exact 1-to-1 ISO date alignment).
  - ZERO pre-listing allocation (coins with NaN funding or NaN spot/perp price receive 0.0).
  - Strict `<= t` signal computation executed at `t+1` (zero look-ahead, bit-for-bit verified).
  - Exact 2.0x and 2.5x CEX collateral margin buffer modeling with Mark-Price liquidation audit.
  - Realistic Spot + Perp one-way friction (`10 bps/leg` = `20 bps` pair at 1x, `20 bps/leg` =
    `40 bps` pair at 2x) PLUS explicit entry/exit basis-slippage (`3 bps` 1x / `6 bps` 2x) AND
    adverse negative-funding/basis-widening exit shock penalty.
  - Maker-limit (`6.15 bps/leg` = `12.30 bps` pair) vs Taker (`15.0 bps/leg` = `30.0 bps` pair)
    sensitivity tested explicitly on `F9_TOP6_MAKER_ENTRY`.
  - Does NOT overwrite `.runtime/quant-pod-returns/sleeve3a_funding_carry.json`! Saves complete
    side-by-side summary to `.runtime/crypto-statarb-cache/lab9_funding_carry_v2_summary.json`.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import (
    CACHE_DIR as SPOT_CACHE_DIR,
    RETURNS_DIR,
    compute_daily_metrics,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.funding_rate_carry import (
    FUNDING_CACHE_DIR,
    PERP_UNIVERSE_20,
    SLEEVE3A_RETURNS_PATH,
    _ms_to_date,
    _window_stress,
    load_daily_funding_panel,
    simulate_funding_carry,
)
from quant_factory.portfolio_allocator import (
    _get_garch_evt_kernel,
    align_sleeves_business_days,
    fit_garch11_evt,
    load_sleeve1_dev_daily_returns,
)
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

# Output summary path (does NOT overwrite sleeve3a_funding_carry.json!)
LAB9_CACHE_DIR = ROOT / ".runtime/crypto-statarb-cache"
LAB9_SUMMARY_PATH = LAB9_CACHE_DIR / "lab9_funding_carry_v2_summary.json"

# Exact Lab #9 sample split matching Lab #2 / Lab #2B and Coordinator #85
START_DATE = "2020-01-01"
CLUSTER_A_END = "2023-06-30"
CLUSTER_B_START = "2023-07-01"
DEV_S1_END = "2024-12-31"

# Cost parameters (one-way combined Spot+Perp pair bps on notional)
TAKER_10_LEG_PAIR_1X_BPS = 20.0   # 10.0 bps Spot + 10.0 bps Perp (1x)
TAKER_10_LEG_PAIR_2X_BPS = 40.0   # 20.0 bps Spot + 20.0 bps Perp (2x stress)
BASIS_CROSS_SLIP_1X_BPS = 3.0     # Explicit entry/exit basis crossing spread (1x)
BASIS_CROSS_SLIP_2X_BPS = 6.0     # 2x stress basis crossing spread

# Maker vs Taker sensitivity for F9_TOP6_MAKER_ENTRY (per leg -> x2 for Spot+Perp pair)
MAKER_LEG_1X_BPS = 6.15           # 70% passive limit fill blended leg (from Lab #2B Tier M2)
MAKER_PAIR_1X_BPS = 12.30         # 6.15 bps Spot + 6.15 bps Perp
MAKER_PAIR_2X_BPS = 24.60         # 2x stress Maker pair
TAKER_15_LEG_PAIR_1X_BPS = 30.0   # 15.0 bps Spot + 15.0 bps Perp sensitivity
TAKER_15_LEG_PAIR_2X_BPS = 60.0   # 2x stress Taker 15 bps/leg

# Research Council kill criteria & cumulative trial accounting
LAB9_M_FAMILY = 8
CUMULATIVE_TRIALS_CARRY = 13      # 5 Wave-1 M3.3 trials + 8 Lab #9 variants
LAB9_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.60,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.25,
    max_tail_corr_vs_incumbent=0.40,
    min_trades_cluster_b=30,
)

LAB9_SPEC_ORDER: tuple[str, ...] = (
    "F9_V1_BTC_ETH_BASE",
    "F9_TOP5_HYST_12_4",
    "F9_TOP8_INVVOL_HYST",
    "F9_TOP10_TIER1_CAP20",
    "F9_ALL20_PERSIST_14D",
    "F9_TOP8_REGIME_BRAKE",
    "F9_TOP6_MAKER_ENTRY",
    "F9_TOP5_BEAR_GUARD",
)


# ==============================================================================
# 1. READ-ONLY PANEL LOADER (20 PERPS + EXACT 8H SETTLEMENT COUNTS + PERP VOL)
# ==============================================================================

def load_lab9_funding_panel(
    *,
    symbols: tuple[str, ...] = PERP_UNIVERSE_20,
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
) -> dict[str, Any]:
    """Load 20-perp daily funding/price panel plus exact per-day 8h settlement counts & perp quote volume."""
    panel = load_daily_funding_panel(
        symbols=symbols,
        funding_dir=funding_dir,
        spot_cache_dir=spot_cache_dir,
    )
    dates: list[str] = panel["dates"]
    loaded_syms: list[str] = panel["symbols"]
    n_t, n_k = len(dates), len(loaded_syms)
    d_to_i = {d: i for i, d in enumerate(dates)}

    pos_8h_cnt = np.zeros((n_t, n_k), dtype=np.int32)
    tot_8h_cnt = np.zeros((n_t, n_k), dtype=np.int32)
    perp_quote_vol = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        rp = funding_dir / "rates" / f"{sym}.parquet"
        if rp.exists():
            tbl = pq.read_table(rp, columns=["funding_time_ms", "funding_rate"])
            ft = tbl["funding_time_ms"].to_numpy(zero_copy_only=False)
            fr = tbl["funding_rate"].to_numpy(zero_copy_only=False)
            p_map: dict[str, int] = defaultdict(int)
            t_map: dict[str, int] = defaultdict(int)
            for ts, rate in zip(ft, fr):
                if not np.isfinite(rate):
                    continue
                dk = _ms_to_date(int(ts))
                if dk in d_to_i:
                    t_map[dk] += 1
                    if float(rate) > 0.0:
                        p_map[dk] += 1
            for dk, cnt in t_map.items():
                i = d_to_i[dk]
                tot_8h_cnt[i, j] = int(cnt)
                pos_8h_cnt[i, j] = int(p_map.get(dk, 0))

        kp = funding_dir / "perp_1d" / f"{sym}.parquet"
        if kp.exists():
            kt = pq.read_table(kp, columns=["open_time_ms", "quote_volume"])
            ot = kt["open_time_ms"].to_numpy(zero_copy_only=False)
            qv = kt["quote_volume"].to_numpy(zero_copy_only=False)
            for ts, vol in zip(ot, qv):
                dk = _ms_to_date(int(ts))
                idx = d_to_i.get(dk)
                if idx is not None and np.isfinite(vol) and float(vol) >= 0.0:
                    perp_quote_vol[idx, j] = float(vol)

    panel["pos_8h_cnt"] = pos_8h_cnt
    panel["tot_8h_cnt"] = tot_8h_cnt
    panel["perp_quote_vol"] = perp_quote_vol
    return panel


# ==============================================================================
# 2. STRICTLY CAUSAL FEATURE ENGINE & CAPPED INVERSE-VOL WEIGHTING
# ==============================================================================

def _invvol_capped_weights(
    active_idxs: list[int],
    vol_row: np.ndarray,
    *,
    max_single: float = 0.25,
) -> dict[int, float]:
    """Allocate inverse-volatility weights with strict `<= max_single` per-coin cap and `sum <= 1.0`.

    If `len(active_idxs) * max_single < 1.0`, leaves the residual safely in 0% USDT cash instead
    of violating single-coin concentration limits.
    """
    if not active_idxs:
        return {}
    vols = []
    for j in active_idxs:
        v = float(vol_row[j]) if np.isfinite(vol_row[j]) else 0.04
        vols.append(max(0.005, v))
    inv = np.array([1.0 / v for v in vols], dtype=np.float64)
    w = inv / float(np.sum(inv))
    cap = float(max_single)

    # Cap total budget at min(1.0, n_active * cap) so single-coin limit is never breached
    total_budget = min(1.0, len(active_idxs) * cap)
    w = w * total_budget

    # Water-filling projection onto {0 <= w_i <= cap, sum(w) == total_budget}
    for _ in range(30):
        over = w > cap + 1e-12
        if not np.any(over):
            break
        excess = float(np.sum(w[over] - cap))
        w[over] = cap
        under = w < cap - 1e-12
        if not np.any(under):
            break
        u_sum = float(np.sum(w[under]))
        if u_sum > 1e-12:
            w[under] += excess * (w[under] / u_sum)
        else:
            w[under] += excess / float(np.sum(under))

    w = np.clip(w, 0.0, cap)
    s = float(np.sum(w))
    if s > 1.0 + 1e-12:
        w /= s
    return {active_idxs[i]: float(w[i]) for i in range(len(active_idxs))}


def _compute_causal_features(panel: dict[str, Any]) -> dict[str, Any]:
    """Precompute strictly causal `<= t` rolling funding, persistence, vol, liquidity, and BTC regime features."""
    f_daily = np.asarray(panel["funding_daily"], dtype=np.float64)
    spot_c = np.asarray(panel["spot_close"], dtype=np.float64)
    perp_c = np.asarray(panel["perp_close"], dtype=np.float64)
    pos_8h = np.asarray(panel["pos_8h_cnt"], dtype=np.int32)
    tot_8h = np.asarray(panel["tot_8h_cnt"], dtype=np.int32)
    perp_qv = np.asarray(panel["perp_quote_vol"], dtype=np.float64)
    syms: list[str] = list(panel["symbols"])
    n_t, n_k = f_daily.shape

    # Tradable eligibility mask at day t close (ZERO pre-listing allocation!)
    tradable = (
        np.isfinite(f_daily)
        & np.isfinite(spot_c) & (spot_c > 0.0)
        & np.isfinite(perp_c) & (perp_c > 0.0)
        & (tot_8h > 0)
    )

    roll3 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    roll7 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    roll14 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    persist14_frac = np.full((n_t, n_k), np.nan, dtype=np.float64)
    dv30 = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for t in range(n_t):
        if t >= 2:
            w3 = f_daily[t - 2:t + 1]
            v3 = np.isfinite(w3)
            c3 = np.sum(v3, axis=0)
            s3 = np.sum(np.where(v3, w3, 0.0), axis=0)
            roll3[t] = np.where(c3 >= 3, s3 / np.maximum(1, c3), np.nan)
        if t >= 6:
            w7 = f_daily[t - 6:t + 1]
            v7 = np.isfinite(w7)
            c7 = np.sum(v7, axis=0)
            s7 = np.sum(np.where(v7, w7, 0.0), axis=0)
            roll7[t] = np.where(c7 >= 6, s7 / np.maximum(1, c7), np.nan)
        if t >= 13:
            w14 = f_daily[t - 13:t + 1]
            v14 = np.isfinite(w14)
            c14 = np.sum(v14, axis=0)
            s14 = np.sum(np.where(v14, w14, 0.0), axis=0)
            roll14[t] = np.where(c14 >= 12, s14 / np.maximum(1, c14), np.nan)

            t14 = np.sum(tot_8h[t - 13:t + 1], axis=0)
            p14 = np.sum(pos_8h[t - 13:t + 1], axis=0)
            persist14_frac[t] = np.where(t14 >= 36, p14 / np.maximum(1, t14), np.nan)
        if t >= 14:
            lo = max(0, t - 29)
            wq = perp_qv[lo:t + 1]
            vq = np.isfinite(wq)
            cq = np.sum(vq, axis=0)
            sq = np.sum(np.where(vq, wq, 0.0), axis=0)
            dv30[t] = np.where(cq >= 15, sq / np.maximum(1, cq), np.nan)

    # Strictly causal 20-day realized daily volatility (perp close returns <= t)
    perp_ret = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok_p = np.isfinite(perp_c[1:]) & np.isfinite(perp_c[:-1]) & (perp_c[:-1] > 0.0)
    perp_ret[1:][ok_p] = perp_c[1:][ok_p] / perp_c[:-1][ok_p] - 1.0

    vol20 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for t in range(19, n_t):
        wr = perp_ret[t - 19:t + 1]
        for j in range(n_k):
            vals = wr[:, j]
            vals = vals[np.isfinite(vals)]
            if len(vals) >= 12:
                vol20[t, j] = max(0.005, float(np.std(vals, ddof=1)))

    # BTC causal 14d realized vol, causal expanding 90th percentile, and causal EMA(300)
    btc_idx = syms.index("BTCUSDT") if "BTCUSDT" in syms else 0
    btc_px = np.where(np.isfinite(spot_c[:, btc_idx]) & (spot_c[:, btc_idx] > 0.0), spot_c[:, btc_idx], perp_c[:, btc_idx])
    btc_ret = np.full(n_t, np.nan, dtype=np.float64)
    ok_b = np.isfinite(btc_px[1:]) & np.isfinite(btc_px[:-1]) & (btc_px[:-1] > 0.0)
    btc_ret[1:][ok_b] = btc_px[1:][ok_b] / btc_px[:-1][ok_b] - 1.0

    btc_vol14 = np.full(n_t, np.nan, dtype=np.float64)
    btc_vol14_p90 = np.full(n_t, np.nan, dtype=np.float64)
    seen_vols: list[float] = []
    for t in range(14, n_t):
        wr = btc_ret[t - 13:t + 1]
        wr = wr[np.isfinite(wr)]
        if len(wr) >= 10:
            v = float(np.std(wr, ddof=1))
            btc_vol14[t] = v
            seen_vols.append(v)
            if len(seen_vols) >= 60:
                btc_vol14_p90[t] = float(np.quantile(seen_vols, 0.90))

    # Strictly causal BTC EMA(300)
    btc_ema300 = np.full(n_t, np.nan, dtype=np.float64)
    alpha_ema = 2.0 / (300.0 + 1.0)
    ema_val = np.nan
    for t in range(n_t):
        px = btc_px[t]
        if np.isfinite(px) and px > 0.0:
            ema_val = float(px) if not np.isfinite(ema_val) else (alpha_ema * float(px) + (1.0 - alpha_ema) * ema_val)
            btc_ema300[t] = ema_val

    # Strictly causal cross-sectional median trailing-3d funding
    med_fund3 = np.full(n_t, np.nan, dtype=np.float64)
    for t in range(n_t):
        vals = roll3[t, tradable[t]]
        vals = vals[np.isfinite(vals)]
        if len(vals) >= 2:
            med_fund3[t] = float(np.median(vals))

    return {
        "tradable": tradable,
        "roll3": roll3,
        "roll7": roll7,
        "roll14": roll14,
        "persist14_frac": persist14_frac,
        "dv30": dv30,
        "vol20": vol20,
        "btc_idx": btc_idx,
        "btc_px": btc_px,
        "btc_vol14": btc_vol14,
        "btc_vol14_p90": btc_vol14_p90,
        "btc_ema300": btc_ema300,
        "med_fund3": med_fund3,
    }


# ==============================================================================
# 3. ALL M = 8 WHITE-BOX LAB #9 STRATEGY WEIGHT BUILDERS (100% CAUSAL)
# ==============================================================================

def _build_top_k_hysteresis(
    feat: dict[str, Any],
    *,
    k_max: int,
    keep_rank_limit: int,
    enter_ann: float,
    exit_ann: float,
    max_single: float,
    use_invvol: bool,
    tier1_top_n: int | None = None,
    regime_brake: bool = False,
    bear_guard_scale: float = 1.0,
) -> np.ndarray:
    """Generic strictly causal Top-K funding carry builder with hysteresis, caps & optional guards."""
    tradable = feat["tradable"]
    roll7 = feat["roll7"]
    vol20 = feat["vol20"]
    dv30 = feat["dv30"]
    btc_px = feat["btc_px"]
    btc_ema300 = feat["btc_ema300"]
    btc_vol14 = feat["btc_vol14"]
    btc_vol14_p90 = feat["btc_vol14_p90"]
    med_fund3 = feat["med_fund3"]

    n_t, n_k = roll7.shape
    enter_d = enter_ann / 365.0
    exit_d = exit_ann / 365.0

    w_out = np.zeros((n_t, n_k), dtype=np.float64)
    held: set[int] = set()
    prev_held: set[int] = set()
    prev_scale: float = 1.0
    prev_w: dict[int, float] = {}
    rebal_deadband: float = 0.05  # Ignore <5% notional drift on unchanged coin set (prevents daily vol-noise churn)

    for t in range(14, n_t):
        # Optional causal Tier-1 liquidity filter (Top-N by trailing 30d perp dollar volume)
        if tier1_top_n is not None:
            liq_ranked = [
                (float(dv30[t, j]) if np.isfinite(dv30[t, j]) else 0.0, j)
                for j in range(n_k)
                if tradable[t, j]
            ]
            liq_ranked.sort(reverse=True)
            allowed = {j for _v, j in liq_ranked[:tier1_top_n]}
        else:
            allowed = {j for j in range(n_k) if tradable[t, j]}

        # Optional Regime Brake: drop immediately to 0% cash if BTC vol spikes > p90 OR median 3d funding < 0
        if regime_brake:
            vol_spike = (
                np.isfinite(btc_vol14[t])
                and np.isfinite(btc_vol14_p90[t])
                and btc_vol14[t] > btc_vol14_p90[t]
            )
            neg_med = np.isfinite(med_fund3[t]) and med_fund3[t] < 0.0
            if vol_spike or neg_med:
                held = set()
                prev_held = set()
                prev_w = {}
                continue

        ranked = [
            (float(roll7[t, j]), j)
            for j in sorted(allowed)
            if np.isfinite(roll7[t, j])
        ]
        ranked.sort(key=lambda x: (-x[0], x[1]))
        rank_pos = {j: idx for idx, (_val, j) in enumerate(ranked)}

        # Keep held positions passing hysteresis exit & rank buffer
        next_held = {
            j for j in held
            if j in rank_pos and rank_pos[j] < keep_rank_limit and roll7[t, j] >= exit_d
        }
        # Fill remaining slots up to k_max with coins exceeding entry threshold
        for val7, j in ranked:
            if len(next_held) >= k_max:
                break
            if j not in next_held and val7 > enter_d:
                next_held.add(j)

        held = next_held
        if not held:
            prev_held = set()
            prev_w = {}
            continue

        act = sorted(held)
        if use_invvol:
            w_raw = _invvol_capped_weights(act, vol20[t], max_single=max_single)
        else:
            per_c = min(max_single, 1.0 / len(act))
            w_raw = {j: per_c for j in act}

        scale = 1.0
        if bear_guard_scale < 1.0:
            if np.isfinite(btc_px[t]) and np.isfinite(btc_ema300[t]) and btc_px[t] < btc_ema300[t]:
                scale = float(bear_guard_scale)

        w_fresh = {j: wj * scale for j, wj in w_raw.items()}
        if (
            use_invvol
            and held == prev_held
            and abs(scale - prev_scale) < 1e-12
            and prev_w
            and max(abs(w_fresh[j] - prev_w.get(j, 0.0)) for j in act) < rebal_deadband
        ):
            w_use = prev_w
        else:
            w_use = w_fresh
            prev_held = set(held)
            prev_scale = scale
            prev_w = dict(w_use)

        for j, wj in w_use.items():
            w_out[t, j] = wj

    return w_out


def build_lab9_strategies(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build all M = 8 strictly causal Lab #9 funding-carry strategies + metadata."""
    feat = _compute_causal_features(panel)
    syms: list[str] = list(panel["symbols"])
    tradable = feat["tradable"]
    roll7 = feat["roll7"]
    roll14 = feat["roll14"]
    persist14 = feat["persist14_frac"]
    vol20 = feat["vol20"]
    n_t, n_k = roll7.shape

    # 1. F9_V1_BTC_ETH_BASE: Exact incumbent S3A v1 benchmark (CARRY_BTC_ETH_CONS_2XBUF)
    be_idx = [syms.index(s) for s in ("BTCUSDT", "ETHUSDT") if s in syms]
    w_v1 = np.zeros((n_t, n_k), dtype=np.float64)
    be_state = {j: False for j in be_idx}
    thr_be = 0.03 / 365.0
    for t in range(14, n_t):
        for j in be_idx:
            r7 = roll7[t, j]
            if (not tradable[t, j]) or (not np.isfinite(r7)):
                be_state[j] = False
            elif be_state[j]:
                if r7 <= 0.0:
                    be_state[j] = False
            else:
                if r7 >= thr_be:
                    be_state[j] = True
        for j, on in be_state.items():
            if on:
                w_v1[t, j] = 0.50

    # 2. F9_TOP5_HYST_12_4: Top-5 highest trailing-7d funding among causal Tier-1 (Top-12 dv30), >+12% / <+4%, 2.0x
    w_top5_12_4 = _build_top_k_hysteresis(
        feat, k_max=5, keep_rank_limit=8, enter_ann=0.12, exit_ann=0.04,
        max_single=0.25, use_invvol=False, tier1_top_n=12,
    )

    # 3. F9_TOP8_INVVOL_HYST: Top-8 inverse-vol weighted with hysteresis (>+8% / <+2%), 2.0x
    w_top8_inv = _build_top_k_hysteresis(
        feat, k_max=8, keep_rank_limit=12, enter_ann=0.08, exit_ann=0.02,
        max_single=0.25, use_invvol=True, tier1_top_n=None,
    )

    # 4. F9_TOP10_TIER1_CAP20: Top-10 positive-funding coins capped <= 20% each, 2.5x conservative margin buffer
    w_top10_cap20 = _build_top_k_hysteresis(
        feat, k_max=10, keep_rank_limit=14, enter_ann=0.06, exit_ann=0.01,
        max_single=0.20, use_invvol=True, tier1_top_n=None,
    )

    # 5. F9_ALL20_PERSIST_14D: All 20 perps filtered by 14d persistent positive funding (>= 80% pos 8h prints & >+6% ann)
    w_persist14 = np.zeros((n_t, n_k), dtype=np.float64)
    p_state = np.zeros(n_k, dtype=bool)
    p_prev_act: tuple[int, ...] = ()
    p_prev_w: dict[int, float] = {}
    p_enter_d = 0.06 / 365.0
    p_exit_d = 0.01 / 365.0
    for t in range(14, n_t):
        for j in range(n_k):
            r14 = roll14[t, j]
            pf = persist14[t, j]
            if (not tradable[t, j]) or (not np.isfinite(r14)) or (not np.isfinite(pf)):
                p_state[j] = False
            elif p_state[j]:
                if pf < 0.60 or r14 < p_exit_d:
                    p_state[j] = False
            else:
                if pf >= 0.80 and r14 > p_enter_d:
                    p_state[j] = True
        act = [j for j in range(n_k) if p_state[j]]
        if not act:
            p_prev_act = ()
            p_prev_w = {}
            continue
        w_fresh = _invvol_capped_weights(act, vol20[t], max_single=0.20)
        act_t = tuple(act)
        if act_t == p_prev_act and p_prev_w and max(abs(w_fresh[j] - p_prev_w.get(j, 0.0)) for j in act) < 0.05:
            w_use = p_prev_w
        else:
            w_use = w_fresh
            p_prev_act = act_t
            p_prev_w = dict(w_use)
        for j, wj in w_use.items():
            w_persist14[t, j] = wj

    # 6. F9_TOP8_REGIME_BRAKE: Top-8 inv-vol hysteresis + 0% cash brake when BTC 14d vol > p90 OR med 3d funding < 0
    w_regime_brake = _build_top_k_hysteresis(
        feat, k_max=8, keep_rank_limit=12, enter_ann=0.08, exit_ann=0.02,
        max_single=0.25, use_invvol=True, tier1_top_n=None, regime_brake=True,
    )

    # 7. F9_TOP6_MAKER_ENTRY: Top-6 inv-vol hysteresis (>+10% / <+3%) for Maker (6.15 bps/leg) vs Taker (15 bps/leg)
    w_top6_maker = _build_top_k_hysteresis(
        feat, k_max=6, keep_rank_limit=10, enter_ann=0.10, exit_ann=0.03,
        max_single=0.25, use_invvol=True, tier1_top_n=None,
    )

    # 8. F9_TOP5_BEAR_GUARD: Top-5 inv-vol hysteresis (>+10% / <+3%) scaled 0.5x when BTC < EMA(300) strictly causal
    w_top5_bear = _build_top_k_hysteresis(
        feat, k_max=5, keep_rank_limit=8, enter_ann=0.10, exit_ann=0.03,
        max_single=0.25, use_invvol=True, tier1_top_n=None, bear_guard_scale=0.50,
    )

    return {
        "F9_V1_BTC_ETH_BASE": {
            "weights": w_v1,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.50,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Incumbent S3A v1 BTC+ETH Conservative Carry (2.0x Buffer)",
            "rationale": (
                "Baseline incumbent delta-neutral BTC+ETH perpetual funding carry harvesting structural "
                "long-bias financing paid by retail leveraged perpetual traders at 2.0x collateral buffer."
            ),
        },
        "F9_TOP5_HYST_12_4": {
            "weights": w_top5_12_4,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.25,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Top-5 Causal Tier-1 Carry with +12%/+4% Hysteresis (2.0x Buffer)",
            "rationale": (
                "Rotates across causal Top-12 liquid perps selecting Top-5 highest trailing-7d funding "
                "using wide +12% enter / +4% exit hysteresis to suppress churn while harvesting altcoin leverage demand."
            ),
        },
        "F9_TOP8_INVVOL_HYST": {
            "weights": w_top8_inv,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.25,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Top-8 Inverse-Vol Weighted Hysteresis Carry (2.0x Buffer)",
            "rationale": (
                "Diversifies delta-neutral funding carry across up to 8 positive-funding perps sized by "
                "causal inverse 20d volatility to compress single-coin basis/liquidation tail risk."
            ),
        },
        "F9_TOP10_TIER1_CAP20": {
            "weights": w_top10_cap20,
            "equity_buffer_mult": 2.5,
            "max_single_notional_cap": 0.20,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Top-10 Diversified Carry <=20% Cap & 2.5x Conservative Buffer",
            "rationale": (
                "Spreads delta-neutral carry across up to 10 liquid perps with hard <=20% single-coin "
                "notional cap and 2.5x margin buffer (<=8% equity per coin) to reduce left-tail EVT xi."
            ),
        },
        "F9_ALL20_PERSIST_14D": {
            "weights": w_persist14,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.20,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "All-20 Persistent 14d Funding (>=80% Positive 8h Prints, 2.0x)",
            "rationale": (
                "Requires >=80% positive settled 8h funding prints over trailing 14 days to filter out "
                "transient funding spikes and avoid entering fragile short-squeeze basis reversals."
            ),
        },
        "F9_TOP8_REGIME_BRAKE": {
            "weights": w_regime_brake,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.25,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Top-8 Inv-Vol Hysteresis + Vol-P90 / Neg-Median Regime Brake",
            "rationale": (
                "Combines Top-8 inverse-vol diversified carry with a causal circuit breaker dropping to "
                "0% cash when BTC 14d vol exceeds expanding 90th percentile or cross-sectional funding flips negative."
            ),
        },
        "F9_TOP6_MAKER_ENTRY": {
            "weights": w_top6_maker,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.25,
            "pair_1x_bps": MAKER_PAIR_1X_BPS,
            "pair_2x_bps": MAKER_PAIR_2X_BPS,
            "cost_tier_label": "Maker 6.15bps/leg + 3bps basis + exit-shock (vs Taker 15bps/leg)",
            "title": "Top-6 Inv-Vol Hysteresis with Maker-Limit Execution (6.15bps/leg)",
            "rationale": (
                "Harvests Top-6 inverse-vol hysteresis funding carry via passive limit execution (70% fill "
                "at 6.15 bps/leg effective) audited explicitly against harsher 15 bps/leg Taker execution."
            ),
        },
        "F9_TOP5_BEAR_GUARD": {
            "weights": w_top5_bear,
            "equity_buffer_mult": 2.0,
            "max_single_notional_cap": 0.25,
            "pair_1x_bps": TAKER_10_LEG_PAIR_1X_BPS,
            "pair_2x_bps": TAKER_10_LEG_PAIR_2X_BPS,
            "cost_tier_label": "Taker 10bps/leg + 3bps basis + exit-shock",
            "title": "Top-5 Inv-Vol Hysteresis + 0.5x BTC < EMA(300) Bear Guard",
            "rationale": (
                "Halves carry gross notional whenever BTC spot trades below its causal 300-day EMA so "
                "crypto winter funding-flip cascades and basis dislocations inflict half normal drawdown."
            ),
        },
    }


# ==============================================================================
# 4. CARRY SIMULATOR WITH BASIS-SLIPPAGE & NEGATIVE-FUNDING EXIT SHOCK PENALTY
# ==============================================================================

def simulate_lab9_carry(
    panel: dict[str, Any],
    target_notional_w: np.ndarray,
    *,
    equity_buffer_mult: float = 2.0,
    oneway_pair_cost_bps: float = TAKER_10_LEG_PAIR_1X_BPS,
    basis_cross_slip_bps: float = BASIS_CROSS_SLIP_1X_BPS,
    exit_shock_mult: float = 1.0,
    include_basis_mtm: bool = True,
) -> dict[str, Any]:
    """Run causal delta-neutral carry with base pair friction + entry/exit basis slip + exit shock cost.

    Friction model:
      - Base one-way pair cost + entry/exit basis crossing spread = `oneway_pair_cost_bps + basis_cross_slip_bps`
        charged on every unit of gross notional turnover `|held[t] - held[t-1]|`.
      - Additional adverse exit shock penalty: whenever a position reduces/exits (`delta_w < 0`)
        on a day where realized daily funding `< 0` OR Spot-Perp basis moves adversely (`r_spot - r_perp < 0`),
        charges an extra `exit_shock_mult * min(25 bps, 0.5 * adverse_bps)` on the exited notional to
        penalize crowded deleveraging exits without look-ahead.
    """
    total_oneway_bps = float(oneway_pair_cost_bps) + float(basis_cross_slip_bps)
    base = simulate_funding_carry(
        panel["funding_daily"],
        panel["spot_close"],
        panel["perp_close"],
        panel["perp_high"],
        target_notional_w,
        spot_high=panel["spot_high"],
        equity_buffer_mult=equity_buffer_mult,
        oneway_pair_cost_bps=total_oneway_bps,
        include_basis_mtm=include_basis_mtm,
    )

    held = base["held_notional"]
    n_t, n_k = held.shape
    prev = np.zeros_like(held)
    prev[1:] = held[:-1]
    exit_notional = np.maximum(0.0, prev - held)  # strictly positive on reductions / exits

    # Compute realized day-t Spot-Perp basis move & negative funding magnitude (causal realization cost)
    f_daily = np.nan_to_num(panel["funding_daily"], nan=0.0)
    spot_c = panel["spot_close"]
    perp_c = panel["perp_close"]
    diff_sp = np.zeros((n_t, n_k), dtype=np.float64)
    ok_s = np.isfinite(spot_c[1:]) & np.isfinite(spot_c[:-1]) & (spot_c[:-1] > 0.0)
    ok_p = np.isfinite(perp_c[1:]) & np.isfinite(perp_c[:-1]) & (perp_c[:-1] > 0.0)
    ok_b = ok_s & ok_p
    r_s = np.zeros((n_t, n_k), dtype=np.float64)
    r_p = np.zeros((n_t, n_k), dtype=np.float64)
    r_s[1:][ok_b] = spot_c[1:][ok_b] / spot_c[:-1][ok_b] - 1.0
    r_p[1:][ok_b] = perp_c[1:][ok_b] / perp_c[:-1][ok_b] - 1.0
    diff_sp = np.clip(r_s - r_p, -0.15, 0.15)

    # Adverse shock rate on exit days: half of negative basis widening + full negative daily funding, capped 25 bps @ 1x
    adverse_rate = np.clip(
        0.5 * np.maximum(0.0, -diff_sp) + np.maximum(0.0, -f_daily),
        0.0,
        0.0025,
    ) * float(exit_shock_mult)
    exit_shock_cost = np.sum(exit_notional * adverse_rate, axis=1)

    net = base["net_returns"] - exit_shock_cost
    base["exit_shock_cost"] = exit_shock_cost
    base["net_returns"] = net
    base["total_oneway_bps"] = round(total_oneway_bps, 2)
    base["exit_shock_drag_ann_bps"] = round(float(np.mean(exit_shock_cost)) * 365.0 * 10_000.0, 2)
    return base


# ==============================================================================
# 5. GARCH(1,1)-EVT TAIL INDEX & 1-SLEEVE 252-DAY CRASH DD AUDIT
# ==============================================================================

def _evt_gpd_var_es(fit: dict[str, Any], *, alpha: float = 0.01) -> tuple[float, float]:
    """Analytical EVT-GPD left-tail VaR & Expected Shortfall (positive loss pct) at confidence `1 - alpha`."""
    tail_q = float(fit["tail_quantile"])
    u = float(fit["u_thresh"])
    xi = float(fit["evt_xi"])
    sc = float(fit["evt_scale"])
    sig = float(fit["sigma_uncond"])
    mu = float(fit["mu"])
    if alpha >= tail_q:
        z_a = float(np.quantile(fit["z_sorted"], alpha))
        var_a = max(0.0, -(mu + sig * z_a))
        return var_a, var_a
    p_exc = 1.0 - (alpha / tail_q)
    if abs(xi) > 1e-5:
        exc_q = (sc / xi) * ((1.0 - p_exc) ** (-xi) - 1.0)
    else:
        exc_q = -sc * math.log(max(1e-9, 1.0 - p_exc))
    z_var = u - exc_q
    var_a = max(0.0, -(mu + sig * z_var))
    if xi < 0.95:
        es_exc = (exc_q + sc - xi * 0.0) / max(0.05, 1.0 - xi)
        z_es = u - es_exc
        es_a = max(var_a, -(mu + sig * z_es))
    else:
        es_a = var_a
    return var_a, es_a


def compute_single_sleeve_garch_evt_audit(
    returns: np.ndarray,
    *,
    n_paths: int = 4000,
    horizon: int = 252,
    seed: int = 20261124,
) -> dict[str, Any]:
    """Run `portfolio_allocator.fit_garch11_evt()` + 4,000-path 252d GARCH-EVT crash DD simulation."""
    r = np.asarray(returns, dtype=np.float64)
    r = r[np.isfinite(r)]
    if len(r) < 40 or float(np.std(r, ddof=1)) <= 1e-12:
        return {
            "n_obs": int(len(r)),
            "evt_xi": 0.0,
            "evt_scale": 0.0,
            "persistence": 0.0,
            "emp_p99_daily_loss_pct": 0.0,
            "emp_es99_daily_loss_pct": 0.0,
            "worst_day_pct": 0.0,
            "evt_var99_daily_pct": 0.0,
            "evt_es99_daily_pct": 0.0,
            "p95_stress_dd_252d_pct": 0.0,
            "p99_stress_dd_252d_pct": 0.0,
        }

    fit = fit_garch11_evt(r, tail_quantile=0.10, use_numba=True)
    p1 = float(np.percentile(r, 1.0))
    tail_emp = r[r <= p1]
    emp_var99 = max(0.0, -p1)
    emp_es99 = max(emp_var99, float(-np.mean(tail_emp))) if len(tail_emp) else emp_var99
    evt_var99, evt_es99 = _evt_gpd_var_es(fit, alpha=0.01)

    # Deterministic 1-sleeve GARCH-EVT Student-t stress simulation via Numba kernel
    from scipy.stats import t as student_t

    rng = np.random.default_rng(seed)
    z_norm = rng.standard_normal(size=(n_paths, horizon, 1))
    chi2 = rng.chisquare(df=4.0, size=(n_paths, horizon, 1))
    t_draws = z_norm / np.sqrt(chi2 / 4.0)
    u_cop = np.clip(student_t.cdf(t_draws, df=4.0), 1e-6, 1.0 - 1e-6).astype(np.float64)

    kernel = _get_garch_evt_kernel()
    max_dds, min_daily, _sample_d = kernel(
        u_cop,
        np.array([fit["mu"]], dtype=np.float64),
        np.array([fit["omega"]], dtype=np.float64),
        np.array([fit["alpha"]], dtype=np.float64),
        np.array([fit["beta"]], dtype=np.float64),
        np.array([fit["sigma_uncond"] ** 2], dtype=np.float64),
        np.array([fit["u_thresh"]], dtype=np.float64),
        0.10,
        np.array([fit["evt_xi"]], dtype=np.float64),
        np.array([fit["evt_scale"]], dtype=np.float64),
        np.vstack([fit["z_sorted"]]).astype(np.float64),
        np.array([[1.0]], dtype=np.float64),
    )

    return {
        "n_obs": int(len(r)),
        "evt_xi": float(fit["evt_xi"]),
        "evt_scale": float(fit["evt_scale"]),
        "persistence": float(fit["persistence"]),
        "alpha": round(float(fit["alpha"]), 4),
        "beta": round(float(fit["beta"]), 4),
        "emp_p99_daily_loss_pct": round(100.0 * emp_var99, 3),
        "emp_es99_daily_loss_pct": round(100.0 * emp_es99, 3),
        "worst_day_pct": round(100.0 * float(np.min(r)), 3),
        "evt_var99_daily_pct": round(100.0 * evt_var99, 3),
        "evt_es99_daily_pct": round(100.0 * evt_es99, 3),
        "p95_stress_dd_252d_pct": round(100.0 * float(np.percentile(max_dds[0], 95.0)), 2),
        "p99_stress_dd_252d_pct": round(100.0 * float(np.percentile(max_dds[0], 99.0)), 2),
        "p99_worst_1d_sim_pct": round(100.0 * float(-np.percentile(min_daily[0], 1.0)), 3),
    }


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    n = min(len(a), len(b))
    if n < 20:
        return 0.0
    x, y = np.asarray(a[:n], dtype=np.float64), np.asarray(b[:n], dtype=np.float64)
    if float(np.std(x)) <= 1e-12 or float(np.std(y)) <= 1e-12:
        return 0.0
    c = float(np.corrcoef(x, y)[0, 1])
    return round(c, 4) if math.isfinite(c) else 0.0


def _file_sha256(path: Path) -> str:
    if not path.exists():
        return "MISSING"
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ==============================================================================
# 6. FULL LAB #9 PIPELINE (M=8, RESEARCH COUNCIL, GARCH-EVT, PROMOTION AUDIT)
# ==============================================================================

def run_lab9_study(
    *,
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
    summary_out: Path = LAB9_SUMMARY_PATH,
    n_stress_paths: int = 4000,
) -> dict[str, Any]:
    """Execute complete Lab #9 Multi-Coin Funding Carry v2 & EVT Tail-Risk Reduction Study."""
    t0 = time.perf_counter()

    # Record incumbent sleeve3a_funding_carry.json hash before & after (MUST NEVER BE MODIFIED!)
    incumbent_json_sha_before = _file_sha256(SLEEVE3A_RETURNS_PATH)

    panel = load_lab9_funding_panel(funding_dir=funding_dir, spot_cache_dir=spot_cache_dir)
    dates: list[str] = panel["dates"]
    symbols: list[str] = panel["symbols"]
    strats = build_lab9_strategies(panel)

    # Load frozen Sleeve #1 (PORT_7E Dev <= 2024-12-31, holdout_rows_analysed = 0)
    s1_map, s1_meta = load_sleeve1_dev_daily_returns()
    if max(s1_map.keys()) >= "2025-01-01":
        raise AssertionError(f"HOLDOUT_CONTAMINATION in S1: {max(s1_map.keys())}")

    ma = np.array([START_DATE <= d <= CLUSTER_A_END for d in dates])
    mb = np.array([d >= CLUSTER_B_START for d in dates])
    dates_b = [d for d, flag in zip(dates, mb) if flag]

    # Exact 1-to-1 ISO date prefix of Cluster B overlapping S1 Dev (<= 2024-12-31)
    overlap_b_dates = [d for d in dates_b if d <= DEV_S1_END]
    assert dates_b[:len(overlap_b_dates)] == overlap_b_dates, "Non-contiguous date prefix!"
    inc_s1_b_aligned = np.array([s1_map.get(d, 0.0) for d in overlap_b_dates], dtype=np.float64)

    # First pass: simulate all 8 specs at 1x & 2x friction (plus Maker/Taker sensitivity)
    raw_sims: dict[str, dict[str, Any]] = {}
    family_p_values: list[float] = []

    for name in LAB9_SPEC_ORDER:
        cfg = strats[name]
        w = cfg["weights"]
        buf = float(cfg["equity_buffer_mult"])
        p1 = float(cfg["pair_1x_bps"])
        p2 = float(cfg["pair_2x_bps"])

        sim1 = simulate_lab9_carry(
            panel, w,
            equity_buffer_mult=buf,
            oneway_pair_cost_bps=p1,
            basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS,
            exit_shock_mult=1.0,
            include_basis_mtm=True,
        )
        sim2 = simulate_lab9_carry(
            panel, w,
            equity_buffer_mult=buf,
            oneway_pair_cost_bps=p2,
            basis_cross_slip_bps=BASIS_CROSS_SLIP_2X_BPS,
            exit_shock_mult=2.0,
            include_basis_mtm=True,
        )
        sim_nobasis = simulate_lab9_carry(
            panel, w,
            equity_buffer_mult=buf,
            oneway_pair_cost_bps=p1,
            basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS,
            exit_shock_mult=1.0,
            include_basis_mtm=False,
        )

        exp = sim1["held_notional"].sum(axis=1)
        m_a1 = compute_daily_metrics(sim1["net_returns"][ma], sim1["turnover_notional"][ma], exp[ma])
        m_a2 = compute_daily_metrics(sim2["net_returns"][ma], sim2["turnover_notional"][ma], exp[ma])
        m_b1 = compute_daily_metrics(sim1["net_returns"][mb], sim1["turnover_notional"][mb], exp[mb])
        m_b2 = compute_daily_metrics(sim2["net_returns"][mb], sim2["turnover_notional"][mb], exp[mb])
        m_full1 = compute_daily_metrics(sim1["net_returns"], sim1["turnover_notional"], exp)
        m_full_nb = compute_daily_metrics(sim_nobasis["net_returns"], sim_nobasis["turnover_notional"], exp)

        extra_sens: dict[str, Any] = {}
        if name == "F9_TOP6_MAKER_ENTRY":
            # Explicit sensitivity vs Taker 15 bps/leg (30 bps pair) & Taker 10 bps/leg (20 bps pair)
            sim_t15_1 = simulate_lab9_carry(
                panel, w, equity_buffer_mult=buf,
                oneway_pair_cost_bps=TAKER_15_LEG_PAIR_1X_BPS,
                basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS,
                exit_shock_mult=1.0, include_basis_mtm=True,
            )
            sim_t15_2 = simulate_lab9_carry(
                panel, w, equity_buffer_mult=buf,
                oneway_pair_cost_bps=TAKER_15_LEG_PAIR_2X_BPS,
                basis_cross_slip_bps=BASIS_CROSS_SLIP_2X_BPS,
                exit_shock_mult=2.0, include_basis_mtm=True,
            )
            sim_t10_1 = simulate_lab9_carry(
                panel, w, equity_buffer_mult=buf,
                oneway_pair_cost_bps=TAKER_10_LEG_PAIR_1X_BPS,
                basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS,
                exit_shock_mult=1.0, include_basis_mtm=True,
            )
            sim_t10_2 = simulate_lab9_carry(
                panel, w, equity_buffer_mult=buf,
                oneway_pair_cost_bps=TAKER_10_LEG_PAIR_2X_BPS,
                basis_cross_slip_bps=BASIS_CROSS_SLIP_2X_BPS,
                exit_shock_mult=2.0, include_basis_mtm=True,
            )
            extra_sens = {
                "taker_15bps_leg_1x_b": compute_daily_metrics(sim_t15_1["net_returns"][mb], sim_t15_1["turnover_notional"][mb], exp[mb]),
                "taker_15bps_leg_2x_b": compute_daily_metrics(sim_t15_2["net_returns"][mb], sim_t15_2["turnover_notional"][mb], exp[mb]),
                "taker_10bps_leg_1x_b": compute_daily_metrics(sim_t10_1["net_returns"][mb], sim_t10_1["turnover_notional"][mb], exp[mb]),
                "taker_10bps_leg_2x_b": compute_daily_metrics(sim_t10_2["net_returns"][mb], sim_t10_2["turnover_notional"][mb], exp[mb]),
            }

        raw_sims[name] = {
            "cfg": cfg,
            "sim1": sim1,
            "sim2": sim2,
            "m_a1": m_a1,
            "m_a2": m_a2,
            "m_b1": m_b1,
            "m_b2": m_b2,
            "m_full1": m_full1,
            "m_full_nb": m_full_nb,
            "extra_sens": extra_sens,
        }
        family_p_values.append(float(m_b1["p_one_sided_nw"]))

    bh_q_vals = benjamini_hochberg(family_p_values)
    v1_ret_b = raw_sims["F9_V1_BTC_ETH_BASE"]["sim1"]["net_returns"][mb]

    # Second pass: Research Council critique, GARCH(1,1)-EVT tail audit, crisis stress, and S3A v1 comparison
    variants_out: dict[str, Any] = {}
    for idx, name in enumerate(LAB9_SPEC_ORDER):
        rec = raw_sims[name]
        cfg = rec["cfg"]
        sim1 = rec["sim1"]
        sim2 = rec["sim2"]
        r1 = sim1["net_returns"]
        r2 = sim2["net_returns"]
        r1_a = r1[ma]
        r1_b = r1[mb]
        r2_b = r2[mb]

        held = sim1["held_notional"]
        n_active_days_b = int(np.sum(held[mb].sum(axis=1) > 1e-6))
        n_rebalance_days_b = int(np.sum(sim1["turnover_notional"][mb] > 1e-4))
        avg_coins_held_b = round(float(np.mean(np.sum(held[mb] > 1e-6, axis=1))), 2)
        max_single_eq_w = round(float(np.max(held)) * 100.0, 2)
        max_gross_eq_w = round(float(np.max(held.sum(axis=1))) * 100.0, 2)

        # Build daily map for exact Mon-Fri alignment (apple-to-apple with portfolio_allocator.py!)
        cand_map = {d: float(v) for d, v in zip(dates, r1)}
        mf_days_2024, mf_mat_2024, _ = align_sleeves_business_days(
            {"S1": s1_map, "CAND": cand_map},
            start_day=START_DATE,
            end_day=DEV_S1_END,
        )
        mf_days_b_ov, mf_mat_b_ov, _ = align_sleeves_business_days(
            {"S1": s1_map, "CAND": cand_map},
            start_day=CLUSTER_B_START,
            end_day=DEV_S1_END,
        )
        corr_s1_monfri_b_dev = _safe_corr(mf_mat_b_ov[:, 1], mf_mat_b_ov[:, 0])
        corr_v1_b = _safe_corr(r1_b, v1_ret_b)

        # Research Council critique (exact 1-to-1 date alignment on overlap_b_dates)
        card = propose_hypothesis(
            hypothesis_id=name,
            title=cfg["title"],
            asset_universe=symbols,
            timeframe="D1_8H_FUNDING_SPOT_PERP",
            counterparty_mechanism="Leveraged crypto perpetual long speculators paying positive 8h funding to delta-neutral arbitrageurs",
            economic_rationale=cfg["rationale"],
            causal_invariants=(
                "Zero pre-listing allocation (NaN funding/spot/perp => 0.0 weight)",
                "Strict t -> t+1 causal execution using <= t rolling funding, 8h counts, vol, liquidity, and EMA300",
                f"Explicit {cfg['equity_buffer_mult']:.1f}x CEX collateral buffer + Mark-Price liquidation audit",
                "Zero Holdout 2025+ FX/Idx rows analysed (holdout_rows_analysed = 0)",
            ),
            n_trials_cumulative=CUMULATIVE_TRIALS_CARRY,
            kill_criteria=LAB9_KILL_CRITERIA,
        )
        ev = EvidenceBundle(
            cluster_a_returns=r1_a,
            cluster_b_returns=r1_b,
            p_value_raw=float(rec["m_b1"]["p_one_sided_nw"]),
            family_p_values=tuple(family_p_values),
            candidate_index_in_family=idx,
            cost_1x_net=float(np.sum(r1_b)),
            cost_2x_net=float(np.sum(r2_b)),
            n_trades_cluster_b=n_active_days_b,
            incumbent_daily_returns=inc_s1_b_aligned,
            annualization_days=365.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        dsr_b = deflated_sharpe_ratio(r1_b, n_trials=CUMULATIVE_TRIALS_CARRY, annualization=365.0)

        # GARCH(1,1)-EVT Tail Audit on: (a) 2020-2024 Mon-Fri (exact parity w/ Cycle 3!), (b) Full 24/7, (c) Blind Cl.B
        evt_mf_2024 = compute_single_sleeve_garch_evt_audit(mf_mat_2024[:, 1], n_paths=n_stress_paths, horizon=252)
        evt_full = compute_single_sleeve_garch_evt_audit(r1, n_paths=n_stress_paths, horizon=252)
        evt_b = compute_single_sleeve_garch_evt_audit(r1_b, n_paths=n_stress_paths, horizon=252)

        variants_out[name] = {
            "spec_id": name,
            "title": cfg["title"],
            "equity_buffer_mult": float(cfg["equity_buffer_mult"]),
            "notional_cap_pct": round(sim1["notional_cap"] * 100.0, 1),
            "max_single_notional_cap_pct": round(float(cfg["max_single_notional_cap"]) * 100.0, 1),
            "max_realized_single_equity_pct": max_single_eq_w,
            "max_realized_gross_equity_pct": max_gross_eq_w,
            "avg_coins_held_b": avg_coins_held_b,
            "n_active_days_b": n_active_days_b,
            "n_rebalance_days_b": n_rebalance_days_b,
            "cost_tier_label": cfg["cost_tier_label"],
            "oneway_total_1x_bps": sim1["total_oneway_bps"],
            "oneway_total_2x_bps": sim2["total_oneway_bps"],
            "exit_shock_drag_ann_1x_bps": sim1["exit_shock_drag_ann_bps"],
            "exit_shock_drag_ann_2x_bps": sim2["exit_shock_drag_ann_bps"],
            "cluster_a_1x": rec["m_a1"],
            "cluster_a_2x": rec["m_a2"],
            "cluster_b_1x": rec["m_b1"],
            "cluster_b_2x": rec["m_b2"],
            "full_1x": rec["m_full1"],
            "full_funding_only_no_basis_1x": rec["m_full_nb"],
            "bh_q_b": round(float(bh_q_vals[idx]), 6),
            "dsr_b": dsr_b,
            "corr_vs_s1_cal_b_dev": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_s1_cal_b_dev": verdict["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "corr_vs_s1_monfri_b_dev": corr_s1_monfri_b_dev,
            "corr_vs_s3a_v1_b": corr_v1_b,
            "margin_stress": {
                "max_single_coin_mark_jump_pct": sim1["max_single_coin_mark_jump_pct"],
                "max_last_trade_wick_pct": sim1["max_last_trade_wick_pct"],
                "max_cross_margin_draw_pct": sim1["max_cross_margin_draw_pct"],
                "margin_warn_days": sim1["margin_warn_days"],
                "isolated_liq_events": sim1["isolated_liq_events"],
                "cross_liq_events": sim1["cross_liq_events"],
            },
            "crisis_stress": {
                "may2021_crash": _window_stress(dates, r1, sim1["funding_pnl"], sim1["basis_pnl"], "2021-05-01", "2021-06-30"),
                "ftx2022_collapse": _window_stress(dates, r1, sim1["funding_pnl"], sim1["basis_pnl"], "2022-11-01", "2022-12-31"),
                "bear2022_full": _window_stress(dates, r1, sim1["funding_pnl"], sim1["basis_pnl"], "2022-01-01", "2022-12-31"),
                "aug2024_yen_shock": _window_stress(dates, r1, sim1["funding_pnl"], sim1["basis_pnl"], "2024-08-01", "2024-08-31"),
            },
            "evt_monfri_2020_2024": evt_mf_2024,
            "evt_full_24_7": evt_full,
            "evt_cluster_b_24_7": evt_b,
            "council_verdict": verdict["verdict"],
            "council_failed_gates": verdict["failed_gates"],
            "council_breakeven_mult": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "council_sha256": verdict["verdict_sha256"],
            "extra_sensitivity": rec["extra_sens"],
        }

    # Explicit side-by-side dominance check vs F9_V1_BTC_ETH_BASE
    v1_ref = variants_out["F9_V1_BTC_ETH_BASE"]
    dominance_table: dict[str, dict[str, Any]] = {}
    strict_dominators: list[str] = []
    council_approved: list[str] = []

    for name in LAB9_SPEC_ORDER:
        v = variants_out[name]
        if v["council_verdict"] == "APPROVE_FOR_INCUBATION":
            council_approved.append(name)
        if name == "F9_V1_BTC_ETH_BASE":
            dominance_table[name] = {"role": "INCUMBENT_BASELINE"}
            continue
        beats_sharpe_b1 = v["cluster_b_1x"]["sharpe"] > v1_ref["cluster_b_1x"]["sharpe"]
        beats_sharpe_b2 = v["cluster_b_2x"]["sharpe"] > v1_ref["cluster_b_2x"]["sharpe"]
        beats_cagr_b1 = v["cluster_b_1x"]["cagr_pct"] > v1_ref["cluster_b_1x"]["cagr_pct"]
        beats_calmar_b1 = v["cluster_b_1x"]["calmar"] > v1_ref["cluster_b_1x"]["calmar"]
        beats_maxdd_b1 = v["cluster_b_1x"]["max_dd_pct"] <= v1_ref["cluster_b_1x"]["max_dd_pct"]
        beats_evt_xi_mf = v["evt_monfri_2020_2024"]["evt_xi"] < v1_ref["evt_monfri_2020_2024"]["evt_xi"]
        beats_evt_xi_full = v["evt_full_24_7"]["evt_xi"] < v1_ref["evt_full_24_7"]["evt_xi"]
        beats_p99_dd_mf = v["evt_monfri_2020_2024"]["p99_stress_dd_252d_pct"] < v1_ref["evt_monfri_2020_2024"]["p99_stress_dd_252d_pct"]
        zero_liq = (v["margin_stress"]["isolated_liq_events"] == 0) and (v["margin_stress"]["cross_liq_events"] == 0)
        strict_dom = (
            v["council_verdict"] == "APPROVE_FOR_INCUBATION"
            and zero_liq
            and beats_sharpe_b1
            and beats_calmar_b1
            and beats_maxdd_b1
            and beats_evt_xi_mf
        )
        if strict_dom:
            strict_dominators.append(name)
        dominance_table[name] = {
            "council_approved": v["council_verdict"] == "APPROVE_FOR_INCUBATION",
            "zero_liq": zero_liq,
            "beats_sharpe_b1": beats_sharpe_b1,
            "beats_sharpe_b2": beats_sharpe_b2,
            "beats_cagr_b1": beats_cagr_b1,
            "beats_calmar_b1": beats_calmar_b1,
            "beats_maxdd_b1": beats_maxdd_b1,
            "beats_evt_xi_monfri24": beats_evt_xi_mf,
            "beats_evt_xi_full": beats_evt_xi_full,
            "beats_p99_dd_monfri24": beats_p99_dd_mf,
            "delta_sharpe_b1": round(v["cluster_b_1x"]["sharpe"] - v1_ref["cluster_b_1x"]["sharpe"], 3),
            "delta_cagr_b1_pct": round(v["cluster_b_1x"]["cagr_pct"] - v1_ref["cluster_b_1x"]["cagr_pct"], 2),
            "delta_maxdd_b1_pct": round(v["cluster_b_1x"]["max_dd_pct"] - v1_ref["cluster_b_1x"]["max_dd_pct"], 2),
            "delta_calmar_b1": round(v["cluster_b_1x"]["calmar"] - v1_ref["cluster_b_1x"]["calmar"], 3),
            "delta_evt_xi_monfri24": round(v["evt_monfri_2020_2024"]["evt_xi"] - v1_ref["evt_monfri_2020_2024"]["evt_xi"], 4),
            "delta_p99_dd_monfri24_pct": round(
                v["evt_monfri_2020_2024"]["p99_stress_dd_252d_pct"] - v1_ref["evt_monfri_2020_2024"]["p99_stress_dd_252d_pct"], 2
            ),
            "strict_dominates_v1": strict_dom,
        }

    # Select best Lab #9 v2 challenger among non-baseline Council-approved variants (by composite risk-adjusted score)
    non_base_approved = [n for n in council_approved if n != "F9_V1_BTC_ETH_BASE"]
    best_v2_challenger = None
    if non_base_approved:
        best_v2_challenger = max(
            non_base_approved,
            key=lambda n: (
                1 if dominance_table[n]["strict_dominates_v1"] else 0,
                1 if dominance_table[n]["beats_evt_xi_monfri24"] else 0,
                variants_out[n]["cluster_b_1x"]["calmar"],
                variants_out[n]["cluster_b_1x"]["sharpe"],
            ),
        )

    # Verify incumbent sleeve3a_funding_carry.json was NEVER modified!
    incumbent_json_sha_after = _file_sha256(SLEEVE3A_RETURNS_PATH)
    assert incumbent_json_sha_before == incumbent_json_sha_after, "Incumbent sleeve3a_funding_carry.json modified!"

    # Also compute exact wave-1 incumbent JSON EVT xi on 2020-2024 Mon-Fri for 100% traceability back to Cycle 3!
    s3a_v1_file_evt: dict[str, Any] = {}
    if SLEEVE3A_RETURNS_PATH.exists():
        raw_s3a = json.loads(SLEEVE3A_RETURNS_PATH.read_text(encoding="utf-8"))
        s3a_map = {str(k): float(v) for k, v in raw_s3a["daily_returns"].items()}
        _, mf_s3a_mat, _ = align_sleeves_business_days(
            {"S1": s1_map, "S3A_FILE": s3a_map}, start_day=START_DATE, end_day=DEV_S1_END
        )
        s3a_v1_file_evt = compute_single_sleeve_garch_evt_audit(mf_s3a_mat[:, 1], n_paths=n_stress_paths, horizon=252)

    summary = {
        "schema": "naqex-lab9-multicoin-funding-carry-v2-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "holdout_rows_analysed": 0,
        "holdout_lock_sha256": s1_meta["holdout_lock_sha256"],
        "incumbent_sleeve3a_json_untouched": True,
        "incumbent_sleeve3a_json_sha256": incumbent_json_sha_after,
        "incumbent_s3a_file_evt_monfri_2020_2024": s3a_v1_file_evt,
        "data_source": {
            "funding_cache_dir": str(funding_dir.relative_to(ROOT)).replace("\\", "/"),
            "spot_cache_dir": str(spot_cache_dir.relative_to(ROOT)).replace("\\", "/"),
            "n_symbols": len(symbols),
            "symbols": symbols,
            "date_range": [dates[0], dates[-1]],
            "n_days_total": len(dates),
            "cluster_a_window": [START_DATE, CLUSTER_A_END],
            "cluster_b_window": [CLUSTER_B_START, dates[-1]],
            "s1_dev_overlap_window": [overlap_b_dates[0], overlap_b_dates[-1]] if overlap_b_dates else [],
            "n_overlap_cal_days_s1_b": len(overlap_b_dates),
        },
        "m_family": LAB9_M_FAMILY,
        "n_trials_cumulative": CUMULATIVE_TRIALS_CARRY,
        "n_council_approved": len(council_approved),
        "council_approved_ids": council_approved,
        "strict_dominators_vs_v1": strict_dominators,
        "best_v2_challenger": best_v2_challenger,
        "variants": variants_out,
        "dominance_vs_v1": dominance_table,
    }

    summary_out.parent.mkdir(parents=True, exist_ok=True)
    summary_out.write_text(json.dumps(summary, indent=2), encoding="utf-8")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description="Wave-2 Cycle 4F — Lab #9 Multi-Coin Funding Carry v2 & EVT Audit")
    parser.add_argument("--n-stress-paths", type=int, default=4000)
    args = parser.parse_args()
    out = run_lab9_study(n_stress_paths=args.n_stress_paths)
    print(f"Lab #9 completed in {out['runtime_seconds']}s | Holdout rows={out['holdout_rows_analysed']}")
    print(f"Incumbent S3A file EVT xi (2020-2024 Mon-Fri): {out['incumbent_s3a_file_evt_monfri_2020_2024'].get('evt_xi')}")
    print(f"Council Approved: {out['n_council_approved']}/{out['m_family']} -> {out['council_approved_ids']}")
    print(f"Strict Dominators vs S3A v1: {out['strict_dominators_vs_v1']} | Best v2 Challenger: {out['best_v2_challenger']}")
    print("-" * 130)
    hdr = f"{'Spec':<24} {'Buf':>4} {'A1_SR':>6} {'B1_SR':>6} {'B2_SR':>6} {'B1_CAGR':>8} {'B1_MDD':>7} {'B1_Cal':>7} {'xi_MF24':>8} {'xi_Full':>8} {'P99_DD':>7} {'Liq':>5} {'Verdict'}"
    print(hdr)
    for sid in LAB9_SPEC_ORDER:
        v = out["variants"][sid]
        a1 = v["cluster_a_1x"]
        b1 = v["cluster_b_1x"]
        b2 = v["cluster_b_2x"]
        em = v["evt_monfri_2020_2024"]
        ef = v["evt_full_24_7"]
        liq = f"{v['margin_stress']['isolated_liq_events']}/{v['margin_stress']['cross_liq_events']}"
        print(
            f"{sid:<24} {v['equity_buffer_mult']:>4.1f} {a1['sharpe']:>6.2f} {b1['sharpe']:>6.2f} {b2['sharpe']:>6.2f} "
            f"{b1['cagr_pct']:>7.2f}% {b1['max_dd_pct']:>6.2f}% {b1['calmar']:>7.2f} "
            f"{em['evt_xi']:>8.4f} {ef['evt_xi']:>8.4f} {em['p99_stress_dd_252d_pct']:>6.2f}% {liq:>5} {v['council_verdict']}"
        )


if __name__ == "__main__":
    main()
