"""C2.3 — Lab #2B: Limit/Maker Execution & Rank-Buffer Hysteresis Study on Crypto Stat-Arb.

Direct follow-up to Lab #2 (`LAB2-CRYPTO-STATARB-NEUTRAL-20261124.md`), which demonstrated that
`S3_FUND_DISLOC` and `S4_MKT_NEUT_MOM` hold genuine positive gross alpha with near-zero BTC beta
and negative/zero correlation vs Sleeve #2, while failing `15 bps` per-leg taker friction.

STRICT ANTI-BIAS & SAFETY BOUNDARIES:
  - Offline computation over cached `.runtime/crypto-1h-cache/` & `.runtime/crypto-spot-cache/funding/`.
  - ZERO API keys, OrderSend = 0, Holdout 2025+ FX untouched (`holdout_rows_analysed = 0`).
  - Realistic passive limit-order execution model (never naive 0 bps!):
        effective_bps = p_fill * (maker_fee_bps + adv_sel_bps)
                      + (1 - p_fill) * (taker_fee_bps + taker_slip_bps)
    Evaluated across:
      * Tier M1 (85% passive fill): 1x = 4.48 bps, 2x stress = 8.95 bps one-way per leg
      * Tier M2 (70% passive fill, PRIMARY GATING TIER): 1x = 6.15 bps, 2x stress = 12.30 bps one-way per leg
      * Tier T0 (Taker control): 1x = 15.0 bps one-way per leg
  - Cumulative trial accounting: passes `n_trials_cumulative = 20` (12 Lab #2 + 8 Lab #2B) into
    Deflated Sharpe Ratio so multi-stage follow-up does NOT understate multiple-testing penalty!
  - Exact dollar neutrality `sum(w) == 0.0`, gross <= 1.0x, `|beta_BTC| <= 0.20`, strict `t -> t+1`.
  - Retains ALL negative/killed results honestly!
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_1h_intraday_lab import (
    CL_A_END_1H,
    CL_B_START_1H,
    LAB1_CACHE_DIR,
    START_1H,
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
from quant_factory.crypto_statarb_pairs_lab import (
    MAX_ABS_BETA_VS_BTC,
    _compute_beta_and_corr,
    _load_incumbent_daily,
    _normalize_dollar_neutral_weights,
    _rolling_vol_causal,
    load_bar_funding_matrix,
    simulate_ls_perp_backtest,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.funding_rate_carry import FUNDING_CACHE_DIR, PERP_UNIVERSE_20
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

LAB2B_SUMMARY_PATH = LAB1_CACHE_DIR / "lab2b_maker_statarb_summary.json"
LAB2B_RETURNS_PATH = RETURNS_DIR / "sleeve_crypto_statarb_maker.json"

LAB2B_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.60,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.25,
    max_tail_corr_vs_incumbent=0.40,
    min_trades_cluster_b=30,
)
CUMULATIVE_TRIALS_LAB2_PLUS_2B = 20  # 12 from Lab #2 + 8 from Lab #2B


def compute_maker_effective_cost_bps(
    *,
    fill_prob: float,
    maker_fee_bps: float = 2.0,
    adverse_selection_bps: float = 2.5,
    taker_fee_bps: float = 5.0,
    taker_slip_bps: float = 5.0,
) -> float:
    """Realistic blended one-way per-leg execution cost under partial passive limit fills."""
    pf = float(np.clip(fill_prob, 0.0, 1.0))
    maker_leg = maker_fee_bps + adverse_selection_bps
    taker_leg = taker_fee_bps + taker_slip_bps
    return round(pf * maker_leg + (1.0 - pf) * taker_leg, 4)


TIER_M1_85_BPS = compute_maker_effective_cost_bps(fill_prob=0.85, maker_fee_bps=2.0, adverse_selection_bps=1.5)  # 4.475
TIER_M2_70_BPS = compute_maker_effective_cost_bps(fill_prob=0.70, maker_fee_bps=2.0, adverse_selection_bps=2.5)  # 6.150
TIER_T0_TAKER_BPS = 15.0


def _select_with_rank_buffer(
    valid_idxs: np.ndarray,
    scores: np.ndarray,
    k_side: int,
    buffer: int,
    prev_longs: set[int],
    prev_shorts: set[int],
    *,
    long_highest: bool = True,
) -> tuple[list[int], list[int]]:
    """Causal rank-buffer hysteresis: keep existing holdings while inside top/bottom `k + buffer`."""
    order_asc = np.argsort(scores)
    ranked_desc = [int(valid_idxs[i]) for i in order_asc[::-1]]
    ranked_asc = [int(valid_idxs[i]) for i in order_asc]

    long_pref = ranked_desc if long_highest else ranked_asc
    short_pref = ranked_asc if long_highest else ranked_desc

    keep_l_zone = set(long_pref[: k_side + buffer])
    keep_s_zone = set(short_pref[: k_side + buffer])

    # Retain existing positions still inside their hysteresis buffer (strictly disjoint)
    new_longs = [idx for idx in long_pref if idx in prev_longs and idx in keep_l_zone][:k_side]
    long_set = set(new_longs)
    for idx in long_pref:
        if len(new_longs) >= k_side:
            break
        if idx not in long_set:
            new_longs.append(idx)
            long_set.add(idx)

    new_shorts = [
        idx for idx in short_pref
        if idx in prev_shorts and idx in keep_s_zone and idx not in long_set
    ][:k_side]
    short_set = set(new_shorts)
    for idx in short_pref:
        if len(new_shorts) >= k_side:
            break
        if idx not in short_set and idx not in long_set:
            new_shorts.append(idx)
            short_set.add(idx)

    return new_longs, new_shorts


def strat_funding_disloc_hysteresis(
    close: np.ndarray,
    funding_bar: np.ndarray,
    *,
    fund_lb_bars: int,
    vol_lb_bars: int = 84,
    k_side: int = 4,
    rank_buffer: int = 3,
    min_spread_ann: float = 0.10,
    exit_spread_ann: float = 0.04,
    rebal_every_bars: int = 18,
    bars_per_day: int = 6,
) -> np.ndarray:
    """Causal Funding-Dislocation L/S with spread hysteresis + rank-buffer retention (exact sum(w)==0)."""
    n_t, n_s = close.shape
    rets = _compute_log_or_simple_rets(close)
    vol = _rolling_vol_causal(rets, vol_lb_bars)

    ann_mult = (365.0 * bars_per_day) / float(fund_lb_bars)
    safe_f = np.where(np.isfinite(funding_bar), funding_bar, 0.0)
    cs = np.cumsum(safe_f, axis=0)
    roll_f_ann = np.zeros((n_t, n_s), dtype=np.float64)
    roll_f_ann[fund_lb_bars:] = (cs[fund_lb_bars:] - cs[:-fund_lb_bars]) * ann_mult

    w_out = np.zeros((n_t, n_s), dtype=np.float64)
    prev_w = np.zeros(n_s, dtype=np.float64)
    prev_l: set[int] = set()
    prev_s: set[int] = set()
    active_book = False

    start = max(fund_lb_bars, vol_lb_bars) + 2
    step = max(1, int(rebal_every_bars))
    for t in range(start, n_t):
        if t % step == 0:
            ok = np.isfinite(close[t]) & np.isfinite(vol[t]) & (vol[t] > 1e-6)
            valid = np.where(ok)[0]
            if len(valid) < 2 * k_side + 2:
                prev_w = np.zeros(n_s, dtype=np.float64)
                prev_l, prev_s, active_book = set(), set(), False
            else:
                f_vals = roll_f_ann[t, valid]
                order = np.argsort(f_vals)
                top_spread = float(np.mean(f_vals[order[-k_side:]]) - np.mean(f_vals[order[:k_side]]))
                thr = exit_spread_ann if active_book else min_spread_ann
                if top_spread < thr:
                    prev_w = np.zeros(n_s, dtype=np.float64)
                    prev_l, prev_s, active_book = set(), set(), False
                else:
                    # Short highest funding, Long lowest funding -> long_highest=False
                    new_l, new_s = _select_with_rank_buffer(
                        valid, f_vals, k_side, rank_buffer, prev_l, prev_s, long_highest=False
                    )
                    if set(new_l) != prev_l or set(new_s) != prev_s or not active_book:
                        raw_l = np.zeros(n_s, dtype=np.float64)
                        raw_s = np.zeros(n_s, dtype=np.float64)
                        raw_l[new_l] = 1.0 / np.maximum(vol[t, new_l], 1e-4)
                        raw_s[new_s] = 1.0 / np.maximum(vol[t, new_s], 1e-4)
                        prev_w = _normalize_dollar_neutral_weights(raw_l, raw_s, target_side_gross=0.50)
                        prev_l, prev_s, active_book = set(new_l), set(new_s), True
        w_out[t] = prev_w
    return w_out


def strat_xsmom_hysteresis(
    close: np.ndarray,
    top_mask: np.ndarray,
    *,
    mom_lb: int,
    vol_lb: int = 84,
    k_side: int = 5,
    rank_buffer: int = 5,
    rebal_every_bars: int = 18,
) -> np.ndarray:
    """Causal Vol-Managed Dollar-Neutral XSMOM with rank-buffer retention (exact sum(w)==0)."""
    n_t, n_s = close.shape
    rets = _compute_log_or_simple_rets(close)
    vol = _rolling_vol_causal(rets, vol_lb)
    cum_r = np.full((n_t, n_s), np.nan, dtype=np.float64)
    cum_r[mom_lb:] = close[mom_lb:] / close[:-mom_lb] - 1.0

    w_out = np.zeros((n_t, n_s), dtype=np.float64)
    prev_w = np.zeros(n_s, dtype=np.float64)
    prev_l: set[int] = set()
    prev_s: set[int] = set()

    start = max(mom_lb, vol_lb) + 2
    step = max(1, int(rebal_every_bars))
    for t in range(start, n_t):
        if t % step == 0:
            ok = top_mask[t] & np.isfinite(cum_r[t]) & np.isfinite(vol[t]) & (vol[t] > 1e-6)
            valid = np.where(ok)[0]
            if len(valid) < 2 * k_side + 2:
                prev_w = np.zeros(n_s, dtype=np.float64)
                prev_l, prev_s = set(), set()
            else:
                score = cum_r[t, valid] / np.maximum(vol[t, valid], 1e-4)
                new_l, new_s = _select_with_rank_buffer(
                    valid, score, k_side, rank_buffer, prev_l, prev_s, long_highest=True
                )
                if set(new_l) != prev_l or set(new_s) != prev_s or float(np.sum(np.abs(prev_w))) < 1e-12:
                    raw_l = np.zeros(n_s, dtype=np.float64)
                    raw_s = np.zeros(n_s, dtype=np.float64)
                    raw_l[new_l] = 1.0 / np.maximum(vol[t, new_l], 1e-4)
                    raw_s[new_s] = 1.0 / np.maximum(vol[t, new_s], 1e-4)
                    prev_w = _normalize_dollar_neutral_weights(raw_l, raw_s, target_side_gross=0.50)
                    prev_l, prev_s = set(new_l), set(new_s)
        w_out[t] = prev_w
    return w_out


def run_lab2b(*, cache_dir: Path = LAB1_CACHE_DIR, funding_dir: Path = FUNDING_CACHE_DIR / "rates") -> dict[str, Any]:
    t0 = time.perf_counter()

    panel_4h = load_interval_panel("4h", UNIVERSE_100_SYMBOLS, cache_dir=cache_dir, min_date=START_1H)
    panel_p20 = load_interval_panel("4h", PERP_UNIVERSE_20, cache_dir=cache_dir, min_date=START_1H)
    fund_4h, _ = load_bar_funding_matrix(panel_4h["timestamps_ms"], panel_4h["symbols"], 4 * 3_600_000, funding_dir=funding_dir)
    fund_p20, _ = load_bar_funding_matrix(panel_p20["timestamps_ms"], panel_p20["symbols"], 4 * 3_600_000, funding_dir=funding_dir)

    top30_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=30)

    # BTC daily benchmark returns
    btc_idx = panel_4h["symbols"].index("BTCUSDT")
    btc_r4 = np.nan_to_num(_compute_log_or_simple_rets(panel_4h["close"][:, [btc_idx]])[:, 0], nan=0.0)
    btc_days, btc_dr, _, _ = _aggregate_bars_to_daily(panel_4h["timestamps_ms"], btc_r4, np.zeros_like(btc_r4), np.ones_like(btc_r4))
    btc_daily_map = {d: float(v) for d, v in zip(btc_days, btc_dr)}
    inc_s2_map = _load_incumbent_daily(RETURNS_DIR / "sleeve2_crypto_spot.json")
    inc_s3a_map = _load_incumbent_daily(RETURNS_DIR / "sleeve3a_funding_carry.json")

    w_f_7d_12h = strat_funding_disloc_hysteresis(panel_p20["close"], fund_p20, fund_lb_bars=42, k_side=4, rank_buffer=2, min_spread_ann=0.10, exit_spread_ann=0.04, rebal_every_bars=3)
    w_f_7d_24h = strat_funding_disloc_hysteresis(panel_p20["close"], fund_p20, fund_lb_bars=42, k_side=4, rank_buffer=3, min_spread_ann=0.10, exit_spread_ann=0.04, rebal_every_bars=6)
    w_f_7d_72h = strat_funding_disloc_hysteresis(panel_p20["close"], fund_p20, fund_lb_bars=42, k_side=4, rank_buffer=3, min_spread_ann=0.10, exit_spread_ann=0.04, rebal_every_bars=18)
    w_f_14d_7d = strat_funding_disloc_hysteresis(panel_p20["close"], fund_p20, fund_lb_bars=84, k_side=5, rank_buffer=3, min_spread_ann=0.08, exit_spread_ann=0.03, rebal_every_bars=42)

    w_m_14d_24h = strat_xsmom_hysteresis(panel_4h["close"], top30_4h, mom_lb=84, k_side=5, rank_buffer=5, rebal_every_bars=6)
    w_m_14d_72h = strat_xsmom_hysteresis(panel_4h["close"], top30_4h, mom_lb=84, k_side=5, rank_buffer=5, rebal_every_bars=18)
    w_m_21d_7d = strat_xsmom_hysteresis(panel_4h["close"], top30_4h, mom_lb=126, k_side=5, rank_buffer=5, rebal_every_bars=42)

    # Composite 50/50 blend aligned on panel_4h grid (embed p20 weights cleanly onto 100-coin panel!)
    w_f_on_100 = np.zeros_like(panel_4h["close"], dtype=np.float64)
    ts_map_4h = {int(ts): i for i, ts in enumerate(panel_4h["timestamps_ms"])}
    sym_map_4h = {s: j for j, s in enumerate(panel_4h["symbols"])}
    row_idxs = np.array([ts_map_4h[int(ts)] for ts in panel_p20["timestamps_ms"]], dtype=np.int64)
    for j_p, sym in enumerate(panel_p20["symbols"]):
        j_100 = sym_map_4h.get(sym)
        if j_100 is not None:
            w_f_on_100[row_idxs, j_100] = w_f_7d_72h[:, j_p]
    w_blend_50_50 = 0.50 * w_f_on_100 + 0.50 * w_m_14d_72h

    specs: list[dict[str, Any]] = [
        {
            "id": "M2B_FUND_7D_K4_12H_BUF2", "fam": "FUNDING_DISLOC_MAKER", "panel": panel_p20, "fund": fund_p20, "w": w_f_7d_12h,
            "cp": "Crowded perp longs paying elevated 8h funding vs uncrowded perp shorts, executed via passive limits",
            "rat": "12h passive-limit rebalancing with rank-buffer +2 cuts churn while capturing 7d funding-dislocation carry and leverage unwind.",
        },
        {
            "id": "M2B_FUND_7D_K4_24H_BUF3", "fam": "FUNDING_DISLOC_MAKER", "panel": panel_p20, "fund": fund_p20, "w": w_f_7d_24h,
            "cp": "Crowded perp longs paying elevated 8h funding vs uncrowded perp shorts, daily passive limit rebalance",
            "rat": "Daily passive-limit rebalancing with rank-buffer +3 holds core funding legs across rank noise, sharply cutting 2-leg execution drag.",
        },
        {
            "id": "M2B_FUND_7D_K4_72H_BUF3", "fam": "FUNDING_DISLOC_MAKER", "panel": panel_p20, "fund": fund_p20, "w": w_f_7d_72h,
            "cp": "Persistent multi-day speculative funding crowding across liquid USD-M perps",
            "rat": "72h passive-limit cadence plus rank-buffer +3 retains persistent funding spreads with ultra-low turnover while staying exact dollar-neutral.",
        },
        {
            "id": "M2B_FUND_14D_K5_7D_BUF3", "fam": "FUNDING_DISLOC_MAKER", "panel": panel_p20, "fund": fund_p20, "w": w_f_14d_7d,
            "cp": "Multi-week structural perpetual funding dispersion across top-20 Binance futures",
            "rat": "Weekly passive-limit Top-5/Bot-5 funding carry minimizes turnover to institutional levels while neutralizing directional BTC beta.",
        },
        {
            "id": "M2B_MOM_14D_K5_24H_BUF5", "fam": "XSMOM_MAKER", "panel": panel_4h, "fund": fund_4h, "w": w_m_14d_24h,
            "cp": "Slow capital rotation from decaying altcoins into emerging Top-30 leaders, daily passive limit execution",
            "rat": "Daily passive-limit vol-managed 14d XSMOM with rank-buffer +5 cuts boundary swaps while harvesting cross-sectional crypto momentum dispersion.",
        },
        {
            "id": "M2B_MOM_14D_K5_72H_BUF5", "fam": "XSMOM_MAKER", "panel": panel_4h, "fund": fund_4h, "w": w_m_14d_72h,
            "cp": "Multi-day cross-sectional crypto dispersion from token unlocks and trend inflows",
            "rat": "72h passive-limit vol-managed 14d XSMOM with rank-buffer +5 slashes annual turnover 3x-5x relative to Lab #2 while keeping zero net dollar exposure.",
        },
        {
            "id": "M2B_MOM_21D_K5_7D_BUF5", "fam": "XSMOM_MAKER", "panel": panel_4h, "fund": fund_4h, "w": w_m_21d_7d,
            "cp": "Weekly persistent relative-strength drift across liquid Top-30 perpetuals",
            "rat": "Weekly passive-limit 21d vol-managed XSMOM targets low-turnover dispersion alpha that can survive conservative 2x maker-fallback friction.",
        },
        {
            "id": "M2B_BLEND_50_FUND_50_MOM", "fam": "COMPOSITE_NEUTRAL_MAKER", "panel": panel_4h, "fund": fund_4h, "w": w_blend_50_50,
            "cp": "Combined speculative funding crowding and multi-week altcoin dispersion on opposite legs",
            "rat": "Equal 50/50 composite of 72h Funding-Dislocation L/S and 72h Vol-Managed XSMOM diversifies carry and momentum regimes while staying dollar-neutral.",
        },
    ]

    eval_items: list[dict[str, Any]] = []
    daily_m2_map: dict[str, dict[str, float]] = {}

    for sp in specs:
        p = sp["panel"]
        # Primary gating tier: Conservative Maker Tier M2 (70% fill -> 6.15 bps 1x / 12.30 bps 2x)
        sm2_1 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=TIER_M2_70_BPS)
        sm2_2 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=2.0 * TIER_M2_70_BPS)
        # Optimistic Maker Tier M1 (85% fill -> 4.475 bps 1x / 8.95 bps 2x) + Taker Control (15 bps)
        sm1_1 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=TIER_M1_85_BPS)
        st0_1 = simulate_ls_perp_backtest(p["close"], sp["w"], sp["fund"], cost_bps_oneway=TIER_T0_TAKER_BPS)

        days, r_m2_1, to1, ex1 = _aggregate_bars_to_daily(p["timestamps_ms"], sm2_1["net_returns"], sm2_1["turnover"], sm2_1["gross_exposure"])
        _, r_m2_2, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], sm2_2["net_returns"], sm2_2["turnover"], sm2_2["gross_exposure"])
        _, r_m1_1, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], sm1_1["net_returns"], sm1_1["turnover"], sm1_1["gross_exposure"])
        _, r_t0_1, _, _ = _aggregate_bars_to_daily(p["timestamps_ms"], st0_1["net_returns"], st0_1["turnover"], st0_1["gross_exposure"])

        ma = np.array([START_1H <= d <= CL_A_END_1H for d in days])
        mb = np.array([d >= CL_B_START_1H for d in days])
        days_b = [d for d, f in zip(days, mb) if f]
        btc_b = np.array([btc_daily_map.get(d, 0.0) for d in days_b], dtype=np.float64)
        s3a_b = np.array([inc_s3a_map.get(d, 0.0) for d in days_b], dtype=np.float64)
        beta_b, corr_btc_b = _compute_beta_and_corr(r_m2_1[mb], btc_b)
        _, corr_s3a_b = _compute_beta_and_corr(r_m2_1[mb], s3a_b)

        eval_items.append({
            "id": sp["id"], "fam": sp["fam"], "cp": sp["cp"], "rat": sp["rat"],
            "days": days, "days_b": days_b, "r1": r_m2_1, "r2": r_m2_2, "ma": ma, "mb": mb,
            "mA_m2_1x": compute_daily_metrics(r_m2_1[ma], to1[ma], ex1[ma]),
            "mA_m2_2x": compute_daily_metrics(r_m2_2[ma], to1[ma], ex1[ma]),
            "mB_m2_1x": compute_daily_metrics(r_m2_1[mb], to1[mb], ex1[mb]),
            "mB_m2_2x": compute_daily_metrics(r_m2_2[mb], to1[mb], ex1[mb]),
            "mB_m1_1x": compute_daily_metrics(r_m1_1[mb], to1[mb], ex1[mb]),
            "mB_t0_1x": compute_daily_metrics(r_t0_1[mb], to1[mb], ex1[mb]),
            "mF_m2_1x": compute_daily_metrics(r_m2_1, to1, ex1),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
            "avg_abs_net_exp": round(float(np.mean(np.abs(sm2_1["net_exposure"]))), 6),
            "max_gross_exp": round(float(np.max(sm2_1["gross_exposure"])), 6),
            "beta_btc_b": beta_b,
            "corr_btc_b": corr_btc_b,
            "corr_s3a_b": corr_s3a_b,
        })
        daily_m2_map[sp["id"]] = {d: float(v) for d, v in zip(days, r_m2_1)}

    m_total = len(eval_items)
    family_p_b = tuple(float(it["mB_m2_1x"]["p_one_sided_nw"]) for it in eval_items)
    qb_all = benjamini_hochberg(list(family_p_b))

    results: list[dict[str, Any]] = []
    approved: list[str] = []

    for idx_i, it in enumerate(eval_items):
        inc_b = np.array([inc_s2_map.get(d, 0.0) for d in it["days_b"]], dtype=np.float64) if inc_s2_map else None
        card = propose_hypothesis(
            hypothesis_id=it["id"],
            title=f"Lab #2B {it['fam']} (Maker M2 70% Fill)",
            asset_universe=PERP_UNIVERSE_20[:5] if "FUND" in it["id"] else UNIVERSE_100_SYMBOLS[:5],
            timeframe="4h",
            counterparty_mechanism=it["cp"],
            economic_rationale=it["rat"],
            causal_invariants=(
                "strict_t_to_t_plus_1_2leg_perp",
                "causal_rank_buffer_hysteresis_le_t",
                "maker_70pct_fill_6p15bps_and_2x_12p30bps",
                "cumulative_n_trials_20_for_dsr",
                "exact_dollar_neutral_gross_le_1x",
            ),
            n_trials_cumulative=CUMULATIVE_TRIALS_LAB2_PLUS_2B,
            kill_criteria=LAB2B_KILL_CRITERIA,
        )
        ev = EvidenceBundle(
            cluster_a_returns=it["r1"][it["ma"]],
            cluster_b_returns=it["r1"][it["mb"]],
            p_value_raw=float(it["mB_m2_1x"]["p_one_sided_nw"]),
            family_p_values=family_p_b,
            candidate_index_in_family=idx_i,
            cost_1x_net=float(it["mB_m2_1x"]["total_ret_pct"]),
            cost_2x_net=float(it["mB_m2_2x"]["total_ret_pct"]),
            n_trades_cluster_b=it["n_active_days_b"],
            incumbent_daily_returns=inc_b,
            annualization_days=365.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        beta_ok = abs(it["beta_btc_b"]) <= MAX_ABS_BETA_VS_BTC
        failed = list(verdict["failed_gates"])
        final_v = verdict["verdict"]
        if not beta_ok:
            failed.append("G_BETA_NEUTRALITY")
            if final_v == "APPROVE_FOR_INCUBATION":
                final_v = "CONDITIONAL_RETEST"
        if final_v == "APPROVE_FOR_INCUBATION":
            approved.append(it["id"])
        dsr_full = deflated_sharpe_ratio(it["r1"], n_trials=CUMULATIVE_TRIALS_LAB2_PLUS_2B, annualization=365.0)
        results.append({
            "id": it["id"],
            "family": it["fam"],
            "cluster_a_m2_1x": it["mA_m2_1x"],
            "cluster_a_m2_2x": it["mA_m2_2x"],
            "cluster_b_m2_1x": it["mB_m2_1x"],
            "cluster_b_m2_2x": it["mB_m2_2x"],
            "cluster_b_m1_1x": it["mB_m1_1x"],
            "cluster_b_t0_1x": it["mB_t0_1x"],
            "full_m2_1x": it["mF_m2_1x"],
            "bh_q_b": round(qb_all[idx_i], 5),
            "dsr_b": verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_m2_b": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_sleeve2_b": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_sleeve2_b": verdict["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "corr_vs_sleeve3a_b": it["corr_s3a_b"],
            "beta_btc_b": it["beta_btc_b"],
            "avg_abs_net_exp": it["avg_abs_net_exp"],
            "max_gross_exp": it["max_gross_exp"],
            "council_verdict": final_v,
            "failed_gates": failed,
            "verdict_sha": verdict["verdict_sha256"],
        })

    exported_path = None
    if approved:
        # Select strictly by Cluster A Sharpe among Council-approved survivors!
        best_id = max(approved, key=lambda aid: next(r["cluster_a_m2_1x"]["sharpe"] for r in results if r["id"] == aid))
        best_r = next(r for r in results if r["id"] == best_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "sleeve_crypto_statarb_maker",
            "strategy_name": best_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 365.0,
            "calendar_type": "24_7_calendar",
            "cost_assumption": f"Maker Tier M2 (70% fill -> {TIER_M2_70_BPS} bps one-way/leg) + real 8h Binance funding",
            "metrics_cluster_a": best_r["cluster_a_m2_1x"],
            "metrics_cluster_b": best_r["cluster_b_m2_1x"],
            "metrics_full": best_r["full_m2_1x"],
            "beta_btc_cluster_b": best_r["beta_btc_b"],
            "daily_returns": daily_m2_map[best_id],
        }
        LAB2B_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAB2B_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(LAB2B_RETURNS_PATH)

    summary = {
        "schema": "naqex-lab2b-crypto-maker-statarb-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "cost_tiers_bps_oneway": {"M1_85pct_fill": TIER_M1_85_BPS, "M2_70pct_fill_primary": TIER_M2_70_BPS, "T0_taker_control": TIER_T0_TAKER_BPS},
        "m_total": m_total,
        "n_trials_cumulative_dsr": CUMULATIVE_TRIALS_LAB2_PLUS_2B,
        "approved_count": len(approved),
        "approved_ids": approved,
        "exported_returns_path": exported_path,
        "results": results,
    }
    LAB2B_SUMMARY_PATH.parent.mkdir(parents=True, exist_ok=True)
    LAB2B_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    argparse.ArgumentParser(description="Lab #2B Maker-Limit Crypto Stat-Arb Study").parse_args()
    s = run_lab2b()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "cost_tiers_bps_oneway": s["cost_tiers_bps_oneway"],
        "approved_count": s["approved_count"],
        "approved_ids": s["approved_ids"],
        "exported_returns_path": s["exported_returns_path"],
        "rows": [
            (
                r["id"], r["cluster_a_m2_1x"]["cagr_pct"], r["cluster_a_m2_1x"]["sharpe"],
                r["cluster_b_m2_1x"]["cagr_pct"], r["cluster_b_m2_2x"]["cagr_pct"],
                r["cluster_b_m2_1x"]["sharpe"], r["cluster_b_m2_1x"]["annual_turnover_x"],
                r["beta_btc_b"], r["corr_vs_sleeve2_b"], r["bh_q_b"], r["dsr_b"], r["council_verdict"],
            )
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
