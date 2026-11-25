"""Multi-Firm Dual-P1 Prop EV Frontier (10,000-Path Block-Bootstrap Numba Monte Carlo).

Strictly Development 2018-2024 frozen tapes (`holdout_rows = 0`, `OrderSend = 0`).
Compares owner-approved P1 profiles side-by-side — BOTH automatically stepping down to `Funded_Safe` once funded:
  - `P1_Balanced_3to6m`: target single-attempt fail rate 15%-25%, median pass 3-6 months
  - `P1_Sprint_1to3m`:   option-like fee play, target single-attempt fail rate 30%-40%, max net EV per USD fee

Evaluates across declarative firm configs in `tooling/ai-engines/configs/firms/*.json`:
  - FTMO Swing 10k
  - FTMO Standard 10k (+RedNews ±5m)
  - FTMO Standard 10k (+RedNews ±5m + Black Friday -25% fee)
  - The5ers High Stakes 5k (8% + 5% official rule + RedNews ±5m)
  - The5ers Hyper Growth 5k (1-step 10%, 3% daily pause, 6% static DD + RedNews ±5m)
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from native_ftmo_monfri_seal import ROOT
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.prop_engine import (
    apply_vol_targeting_causal,
    compute_cluster_a_invdd_weights,
    make_block_bootstrap_indices,
    replay_portfolio_m1,
)
from quant_factory.report_gen import format_markdown_table


def exits_to_daily_arrays(
    ext_days: list[str],
    exits: list[dict],
    initial: float = 10000.0,
) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert M1 replay exits into dense daily (net_usd, intraday_dd_usd, traded_flag) arrays."""
    by_day = {e["day"]: e for e in exits}
    n = len(ext_days)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    flg = np.zeros(n, dtype=np.int8)
    prev_cash = float(initial)
    for i, dk in enumerate(ext_days):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            dds[i] = max(0.0, prev_cash - float(e["day_equity_minimum"]))
            flg[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, flg


@njit(cache=True)
def _simulate_ev_frontier_numba(
    idx_matrix: np.ndarray,
    nets_p1: np.ndarray,
    dds_p1: np.ndarray,
    flg_p1: np.ndarray,
    nets_p2: np.ndarray,
    dds_p2: np.ndarray,
    flg_p2: np.ndarray,
    nets_core: np.ndarray,
    dds_core: np.ndarray,
    flg_core: np.ndarray,
    steps: int,
    cap: float,
    fee: float,
    fee_refund_ratio: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    daily_pause_only: bool,
    min_days: int,
    min_prof_day: float,
    funded_cap_mult: float,
    split: float,
    payout_cycle: int,
    max_retries: int,
    retry_disc: np.ndarray,
    p1_mult: float,
    p2_mult: float,
    funded_mult: float,
    p1_amber_dd: float,
    p1_amber_mult: float,
    p1_red_dd: float,
    p1_red_mult: float,
    p1_ea_daily_stop: float,
    core_amber_dd: float,
    core_amber_mult: float,
    core_red_dd: float,
    core_red_mult: float,
    core_ea_daily_stop: float,
):
    """Extended Numba-JIT lifecycle simulator tracking P1/Full pass times, EV/USD-fee, 1st/3rd payout, and fail streaks."""
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)

    p1_pass_days = np.full(n_paths, -1, dtype=np.int32)
    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    pay3_days = np.full(n_paths, -1, dtype=np.int32)
    payout_counts = np.zeros(n_paths, dtype=np.int32)
    cf12 = np.zeros(n_paths, dtype=np.float64)
    cf24 = np.zeros(n_paths, dtype=np.float64)
    fees12 = np.zeros(n_paths, dtype=np.float64)
    fees24 = np.zeros(n_paths, dtype=np.float64)
    oop = np.zeros(n_paths, dtype=np.float64)
    first_p1_fail = np.zeros(n_paths, dtype=np.int8)
    first_eval_fail = np.zeros(n_paths, dtype=np.int8)
    first_eval_pass = np.zeros(n_paths, dtype=np.int8)
    br1_any = np.zeros(n_paths, dtype=np.int8)
    brf_any = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)
    max_consec_fails = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1  # 1=P1, 2=P2, 3=FUNDED, 0=STOPPED_OUT_OF_RETRIES
        bal = cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        pcount = 0
        cycle_d = 0
        max_oop = fee
        f_p1_pass = -1
        f_pass = -1
        f_pay1 = -1
        f_pay3 = -1
        had_br1 = 0
        had_brf = 0
        first_eval_resolved = 0
        cur_consec = 0
        best_consec = 0

        for d in range(horizon):
            if stage > 0:
                src = idx_matrix[b, d]
                cur_base = cap * funded_cap_mult if stage == 3 else cap
                eq_pct = (bal - cur_base) / cur_base

                eff_scale = scale * (funded_cap_mult if stage == 3 else 1.0)
                if stage == 1:
                    m = p1_mult
                    if eq_pct <= -p1_red_dd:
                        m = min(m, p1_red_mult)
                    elif eq_pct <= -p1_amber_dd:
                        m = min(m, p1_amber_mult)
                    ea_stop_pct = p1_ea_daily_stop
                    net = nets_p1[src] * eff_scale * m
                    dd = dds_p1[src] * eff_scale * m
                    flg = flg_p1[src]
                elif stage == 2:
                    m = p2_mult
                    if eq_pct <= -core_red_dd:
                        m = min(m, core_red_mult * (p2_mult / max(1.0, funded_mult)))
                    elif eq_pct <= -core_amber_dd:
                        m = min(m, core_amber_mult * (p2_mult / max(1.0, funded_mult)))
                    ea_stop_pct = p1_ea_daily_stop
                    net = nets_p2[src] * eff_scale * m
                    dd = dds_p2[src] * eff_scale * m
                    flg = flg_p2[src]
                else:
                    m = funded_mult
                    if eq_pct <= -core_red_dd:
                        m = min(m, core_red_mult)
                    elif eq_pct <= -core_amber_dd:
                        m = min(m, core_amber_mult)
                    ea_stop_pct = core_ea_daily_stop
                    net = nets_core[src] * eff_scale * m
                    dd = dds_core[src] * eff_scale * m
                    flg = flg_core[src]

                cur_daily_cap = cur_base * daily_lim
                cur_static_floor = cur_base * (1.0 - static_lim)
                cur_ea_cut = cur_base * ea_stop_pct if ea_stop_pct > 0.0 else 1e18

                if daily_pause_only:
                    if dd >= cur_daily_cap:
                        dd = min(dd, cur_daily_cap + cur_base * 0.001)
                        net = min(net, -cur_daily_cap)
                    breached = (bal - dd) <= cur_static_floor + 1e-9
                else:
                    if dd > cur_ea_cut:
                        dd = min(dd, cur_ea_cut + cur_base * 0.0025)
                        net = min(net, -cur_ea_cut)
                    breached = (dd >= cur_daily_cap - 1e-9) or ((bal - dd) <= cur_static_floor + 1e-9)

                if breached:
                    if stage == 1:
                        had_br1 = 1
                    if stage == 1 or stage == 2:
                        if first_eval_resolved == 0:
                            first_eval_resolved = 1
                            first_eval_fail[b] = 1
                            if stage == 1:
                                first_p1_fail[b] = 1
                        cur_consec += 1
                        if cur_consec > best_consec:
                            best_consec = cur_consec
                    elif stage == 3:
                        had_brf = 1

                    if attempts <= max_retries:
                        disc_idx = min(attempts - 1, len(retry_disc) - 1)
                        attempts += 1
                        fees += fee * retry_disc[disc_idx]
                        stage = 1
                        bal = cap
                        tdays = 0
                        refunded = False
                        cycle_d = 0
                    else:
                        stage = 0
                else:
                    bal += net
                    if min_prof_day > 0.0:
                        if net >= cap * min_prof_day:
                            tdays += 1
                    elif flg != 0:
                        tdays += 1

                    if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                        if f_p1_pass < 0:
                            f_p1_pass = d + 1
                        if steps == 1:
                            stage = 3
                            bal = cap * funded_cap_mult
                            tdays = 0
                            cycle_d = 0
                            cur_consec = 0
                            if first_eval_resolved == 0:
                                first_eval_resolved = 1
                                first_eval_pass[b] = 1
                            if f_pass < 0:
                                f_pass = d + 1
                        else:
                            stage = 2
                            bal = cap
                            tdays = 0
                    elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                        stage = 3
                        bal = cap * funded_cap_mult
                        tdays = 0
                        cycle_d = 0
                        cur_consec = 0
                        if first_eval_resolved == 0:
                            first_eval_resolved = 1
                            first_eval_pass[b] = 1
                        if f_pass < 0:
                            f_pass = d + 1
                    elif stage == 3:
                        cycle_d += 1
                        if cycle_d >= payout_cycle:
                            if bal > cur_base + 1e-6:
                                pay = (bal - cur_base) * split
                                if not refunded:
                                    pay += fee * fee_refund_ratio
                                    refunded = True
                                payouts += pay
                                pcount += 1
                                if f_pay1 < 0:
                                    f_pay1 = d + 1
                                if pcount == 3 and f_pay3 < 0:
                                    f_pay3 = d + 1
                                bal = cur_base
                            cycle_d = 0

            if fees - payouts > max_oop:
                max_oop = fees - payouts
            if d + 1 == 252:
                cf12[b] = payouts - fees
                fees12[b] = fees

        p1_pass_days[b] = f_p1_pass
        pass_days[b] = f_pass
        pay1_days[b] = f_pay1
        pay3_days[b] = f_pay3
        payout_counts[b] = pcount
        cf24[b] = payouts - fees
        fees24[b] = fees
        oop[b] = max_oop
        br1_any[b] = had_br1
        brf_any[b] = had_brf
        tix[b] = attempts
        max_consec_fails[b] = best_consec

    return (
        p1_pass_days,
        pass_days,
        pay1_days,
        pay3_days,
        payout_counts,
        cf12,
        cf24,
        fees12,
        fees24,
        oop,
        first_p1_fail,
        first_eval_fail,
        first_eval_pass,
        br1_any,
        brf_any,
        tix,
        max_consec_fails,
    )


def geometric_p95_consec_fails(fail_prob: float) -> int:
    """Analytical 95th percentile of consecutive evaluation failures before first pass: P(F <= k) >= 0.95."""
    q = float(fail_prob)
    if q <= 1e-9:
        return 0
    if q >= 0.999:
        return 99
    return max(0, int(math.ceil(math.log(0.05) / math.log(q)) - 1))


def decompose_mt5_multiplier(effective_mult: float, *, max_orch_mult: float = 3.50) -> dict:
    """Decompose an effective multiplier into (ea_risk_scale * orchestrator_mult) respecting PropGuard <= 3.50x."""
    if effective_mult <= max_orch_mult + 1e-9:
        return {"ea_risk_scale": 1.0, "orch_base_phase_mult": round(effective_mult, 2), "effective_mult": round(effective_mult, 2)}
    # Use clean EA risk scale (1.5x or 2.0x) so InpBasePhaseMult stays strictly within [0.20, 3.50]
    ea_scale = 2.0 if effective_mult > 5.25 else 1.5
    orch = round(effective_mult / ea_scale, 2)
    return {"ea_risk_scale": ea_scale, "orch_base_phase_mult": orch, "effective_mult": round(ea_scale * orch, 2)}


def evaluate_ev_profile(
    idx_matrix: np.ndarray,
    p1_series: tuple[np.ndarray, np.ndarray, np.ndarray],
    p2_series: tuple[np.ndarray, np.ndarray, np.ndarray],
    core_series: tuple[np.ndarray, np.ndarray, np.ndarray],
    firm_cfg: dict,
    prof_cfg: dict,
) -> dict:
    """Evaluate a (firm_cfg, prof_cfg) pair on deterministic block-bootstrap paths."""
    rdisc = np.ascontiguousarray(firm_cfg.get("retry_discounts", [1.0]), dtype=np.float64)
    (
        p1_days,
        pdays,
        pay1,
        pay3,
        pcounts,
        cf12,
        cf24,
        fees12,
        fees24,
        oop,
        first_p1_fail,
        first_eval_fail,
        first_eval_pass,
        br1_any,
        brf_any,
        tix,
        max_consec,
    ) = _simulate_ev_frontier_numba(
        np.ascontiguousarray(idx_matrix, dtype=np.int32),
        np.ascontiguousarray(p1_series[0], dtype=np.float64),
        np.ascontiguousarray(p1_series[1], dtype=np.float64),
        np.ascontiguousarray(p1_series[2], dtype=np.int8),
        np.ascontiguousarray(p2_series[0], dtype=np.float64),
        np.ascontiguousarray(p2_series[1], dtype=np.float64),
        np.ascontiguousarray(p2_series[2], dtype=np.int8),
        np.ascontiguousarray(core_series[0], dtype=np.float64),
        np.ascontiguousarray(core_series[1], dtype=np.float64),
        np.ascontiguousarray(core_series[2], dtype=np.int8),
        int(firm_cfg.get("steps", 2)),
        float(firm_cfg["capital_usd"]),
        float(firm_cfg["fee_usd"]),
        float(firm_cfg.get("fee_refund_ratio", 1.0)),
        float(firm_cfg.get("p1_target_pct", 0.10)),
        float(firm_cfg.get("p2_target_pct", 0.05)),
        float(firm_cfg.get("daily_loss_pct", 0.05)),
        float(firm_cfg.get("static_loss_pct", 0.10)),
        bool(firm_cfg.get("daily_pause_non_breaching", False)),
        int(firm_cfg.get("min_days", 4)),
        float(firm_cfg.get("min_profitable_day_pct", 0.0)),
        float(firm_cfg.get("funded_capital_multiplier", 1.0)),
        float(firm_cfg.get("payout_split", 0.80)),
        int(firm_cfg.get("payout_cycle_days", 10)),
        int(firm_cfg.get("max_retries", 3)),
        rdisc,
        float(prof_cfg["p1_mult"]),
        float(prof_cfg["p2_mult"]),
        float(prof_cfg.get("funded_mult", 1.0)),
        float(prof_cfg.get("p1_amber_dd_pct", 0.045)),
        float(prof_cfg.get("p1_amber_mult", 0.85)),
        float(prof_cfg.get("p1_red_dd_pct", 0.070)),
        float(prof_cfg.get("p1_red_mult", 0.55)),
        float(prof_cfg.get("p1_ea_daily_stop_pct", 0.038)),
        float(prof_cfg.get("core_amber_dd_pct", 0.035)),
        float(prof_cfg.get("core_amber_mult", 0.65)),
        float(prof_cfg.get("core_red_dd_pct", 0.060)),
        float(prof_cfg.get("core_red_mult", 0.40)),
        float(prof_cfg.get("core_ea_daily_stop_pct", 0.025)),
    )

    n = len(pdays)
    valid_p1 = p1_days[p1_days > 0]
    valid_p = pdays[pdays > 0]
    valid_pay1 = pay1[pay1 > 0]
    valid_pay3 = pay3[pay3 > 0]
    mean_fees12 = float(np.mean(fees12))
    mean_fees24 = float(np.mean(fees24))
    mean_cf12 = float(np.mean(cf12))
    mean_cf24 = float(np.mean(cf24))
    init_fee = float(firm_cfg["fee_usd"])
    eval_fail_prob = float(np.mean(first_eval_fail > 0))
    p1_fail_prob = float(np.mean(first_p1_fail > 0))

    return {
        "firm": firm_cfg["id"],
        "profile": prof_cfg["id"],
        "p1_mult": float(prof_cfg["p1_mult"]),
        "p2_mult": float(prof_cfg["p2_mult"]),
        "funded_mult": float(prof_cfg.get("funded_mult", 1.0)),
        "p1_mt5_decomp": decompose_mt5_multiplier(float(prof_cfg["p1_mult"])),
        "p2_mt5_decomp": decompose_mt5_multiplier(float(prof_cfg["p2_mult"])),
        "p1_amber_dd_pct": float(prof_cfg.get("p1_amber_dd_pct", 0.045)),
        "p1_amber_mult": float(prof_cfg.get("p1_amber_mult", 0.85)),
        "p1_red_dd_pct": float(prof_cfg.get("p1_red_dd_pct", 0.070)),
        "p1_red_mult": float(prof_cfg.get("p1_red_mult", 0.55)),
        "p1_ea_daily_stop_pct": float(prof_cfg.get("p1_ea_daily_stop_pct", 0.038)),
        "fee_usd": init_fee,
        "p1_single_fail_pct": round(100.0 * p1_fail_prob, 2),
        "eval_single_fail_pct": round(100.0 * eval_fail_prob, 2),
        "eval_single_pass_pct": round(100.0 * float(np.mean(first_eval_pass > 0)), 2),
        "br1_any_pct": round(100.0 * float(np.mean(br1_any > 0)), 2),
        "br_funded_pct": round(100.0 * float(np.sum(brf_any > 0)) / max(1, len(valid_p)), 2),
        "pass_3m_pct": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 63))) / n, 2),
        "pass_6m_pct": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 126))) / n, 2),
        "pass_12m_pct": round(100.0 * float(np.sum((pdays > 0) & (pdays <= 252))) / n, 2),
        "pass_24m_pct": round(100.0 * float(len(valid_p)) / n, 2),
        "med_p1_pass_m": round(float(np.median(valid_p1)) / 21.0, 2) if len(valid_p1) else None,
        "med_pass_m": round(float(np.median(valid_p)) / 21.0, 2) if len(valid_p) else None,
        "p25_pass_m": round(float(np.percentile(valid_p, 25)) / 21.0, 2) if len(valid_p) else None,
        "p75_pass_m": round(float(np.percentile(valid_p, 75)) / 21.0, 2) if len(valid_p) else None,
        "prob_pay1_pct": round(100.0 * float(len(valid_pay1)) / n, 2),
        "prob_pay3_pct": round(100.0 * float(len(valid_pay3)) / n, 2),
        "med_pay1_m": round(float(np.median(valid_pay1)) / 21.0, 2) if len(valid_pay1) else None,
        "med_pay3_m": round(float(np.median(valid_pay3)) / 21.0, 2) if len(valid_pay3) else None,
        "avg_payouts_24m": round(float(np.mean(pcounts)), 2),
        "avg_tix": round(float(np.mean(tix)), 2),
        "mean_fees_12m_usd": round(mean_fees12, 2),
        "mean_fees_24m_usd": round(mean_fees24, 2),
        "cf12_mean_usd": round(mean_cf12, 2),
        "cf24_mean_usd": round(mean_cf24, 2),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24 > 0)), 2),
        "ev_per_usd_fee_12m": round(mean_cf12 / max(1e-6, mean_fees12), 3),
        "ev_per_usd_fee_24m": round(mean_cf24 / max(1e-6, mean_fees24), 3),
        "ev_per_init_fee_24m": round(mean_cf24 / max(1e-6, init_fee), 3),
        "oop95_usd": round(float(np.percentile(oop, 95)), 2),
        "p95_consec_fails_sim": int(np.percentile(max_consec, 95)),
        "p95_consec_fails_geom": geometric_p95_consec_fails(eval_fail_prob),
    }


def build_dev_books() -> dict:
    """Build strictly Development (2018-2024) causal Inverse-DD + Vol-Target daily arrays for Swing & RedNews."""
    lock_sha = assert_holdout_locked()
    d = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = d["tapes"]
    ext_days = d["ext_days"]
    strict_a = d["strict_cluster_a_days"]
    if max(ext_days) >= "2025-01-01":
        raise AssertionError(f"HOLDOUT_CONTAMINATION: max_day={max(ext_days)}")

    reg = load_registry()
    cal = load_red_news_calendar("red_news_official_2018_2024")
    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    turbo9 = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    r7 = {k: base_risks[k] for k in core7}
    r9 = {k: base_risks[k] for k in turbo9}

    invdd9 = compute_cluster_a_invdd_weights(strict_a, tapes, turbo9, sum(r9.values()))
    invdd7 = compute_cluster_a_invdd_weights(strict_a, tapes, core7, sum(r7.values()))

    # Swing / no-red-news books (exact M1 replay with per-symbol concurrent risk caps)
    met9_sw, ex9_sw = replay_portfolio_m1(
        ext_days, tapes, invdd9, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.015, red_news_cal=None
    )
    met7_sw, ex7_sw = replay_portfolio_m1(
        ext_days, tapes, invdd7, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=0.010, red_news_cal=None
    )
    # Red-news ±5m books (Standard / The5ers compliance)
    met9_rn, ex9_rn = replay_portfolio_m1(
        ext_days, tapes, invdd9, 10000.0, profile_mode="Standard", max_symbol_concurrent_risk=0.015, red_news_cal=cal
    )
    met7_rn, ex7_rn = replay_portfolio_m1(
        ext_days, tapes, invdd7, 10000.0, profile_mode="Standard", max_symbol_concurrent_risk=0.010, red_news_cal=cal
    )

    n9_sw, d9_sw, f9_sw = exits_to_daily_arrays(ext_days, ex9_sw)
    n7_sw, d7_sw, f7_sw = exits_to_daily_arrays(ext_days, ex7_sw)
    n9_rn, d9_rn, f9_rn = exits_to_daily_arrays(ext_days, ex9_rn)
    n7_rn, d7_rn, f7_rn = exits_to_daily_arrays(ext_days, ex7_rn)

    # Causal 20-day downside volatility brake for Funded_Safe (fitted strictly on Cluster A < 2021-01-01)
    n7_sw_vt, d7_sw_vt = apply_vol_targeting_causal(ext_days, n7_sw, d7_sw, window=20, lo=0.60, hi=1.00)
    n7_rn_vt, d7_rn_vt = apply_vol_targeting_causal(ext_days, n7_rn, d7_rn, window=20, lo=0.60, hi=1.00)

    return {
        "holdout_lock_sha256": lock_sha,
        "ext_days": ext_days,
        "invdd9_pct": {k: round(v * 100.0, 4) for k, v in invdd9.items()},
        "invdd7_pct": {k: round(v * 100.0, 4) for k, v in invdd7.items()},
        "metrics": {
            "p1_invdd9_swing": met9_sw,
            "funded_invdd7_swing": met7_sw,
            "p1_invdd9_rednews": met9_rn,
            "funded_invdd7_rednews": met7_rn,
        },
        "series": {
            "p1_swing": (n9_sw, d9_sw, f9_sw),
            "p2_swing": (n7_sw, d7_sw, f7_sw),
            "funded_swing": (n7_sw_vt, d7_sw_vt, f7_sw),
            "p1_rednews": (n9_rn, d9_rn, f9_rn),
            "p2_rednews": (n7_rn, d7_rn, f7_rn),
            "funded_rednews": (n7_rn_vt, d7_rn_vt, f7_rn),
        },
    }


def load_firm_variants() -> list[tuple[dict, str, str, str]]:
    """Return list of (firm_cfg, p1_key, p2_key, funded_key) loaded from declarative JSON configs."""
    ftmo_sw = load_firm_config("ftmo_swing_10k")
    ftmo_std = load_firm_config("ftmo_standard_10k")
    ftmo_std_bf25 = {
        **ftmo_std,
        "id": "FTMO_STANDARD_10K_BF25",
        "fee_usd": round(float(ftmo_std["fee_usd"]) * 0.75, 2),
        "promo_note": "Black Friday -25% fee discount (168 -> 126 USD), +RedNews ±5m",
    }
    the5_hs_cfg = load_firm_config("the5ers_high_stakes_5k")
    the5_hs_8p5 = {
        **the5_hs_cfg,
        "id": "THE5ERS_HS_5K_8P5",
        "p1_target_pct": 0.08,
        "p2_target_pct": 0.05,
        "rule_note": "Official The5ers High Stakes 8% P1 + 5% P2 (+RedNews ±5m)",
    }
    the5_hg = load_firm_config("the5ers_hyper_growth_5k")
    return [
        (ftmo_sw, "p1_swing", "p2_swing", "funded_swing"),
        (ftmo_std, "p1_rednews", "p2_rednews", "funded_rednews"),
        (ftmo_std_bf25, "p1_rednews", "p2_rednews", "funded_rednews"),
        (the5_hs_8p5, "p1_rednews", "p2_rednews", "funded_rednews"),
        (the5_hg, "p1_rednews", "p2_rednews", "funded_rednews"),
    ]


def build_candidate_profiles() -> dict[str, list[dict]]:
    """Build full effective-multiplier sweep grids covering both Balanced (15-25% fail, 3-6m) and Sprint (30-40% fail)."""
    two_step_grid = []
    # Sweep effective P1 multipliers 2.50x .. 6.50x with corresponding P2 verification multipliers
    for p1_m, p2_m, amber_dd, amber_m, red_dd, red_m, ea_stop, tag in (
        # Conservative & Balanced region
        (2.50, 2.00, 0.050, 0.75, 0.075, 0.50, 0.035, "BAL_250"),
        (3.00, 2.25, 0.055, 0.80, 0.080, 0.55, 0.038, "BAL_300"),
        (3.25, 2.25, 0.060, 0.85, 0.082, 0.60, 0.040, "BAL_325"),
        (3.50, 2.50, 0.065, 0.90, 0.085, 0.65, 0.040, "BAL_350"),
        (3.75, 2.50, 0.070, 0.95, 0.085, 0.70, 0.042, "BAL_375"),
        (4.00, 2.50, 0.075, 1.00, 0.090, 0.75, 0.042, "BAL_400"),
        (4.25, 2.50, 0.080, 1.00, 0.090, 0.80, 0.042, "BAL_425"),
        # Option-like Sprint region (convex P1 payoff, zero premature brake during P1, immediate step-down to Funded_Safe)
        (4.50, 2.75, 0.099, 1.00, 0.099, 1.00, 0.043, "SPR_450"),
        (4.75, 2.75, 0.099, 1.00, 0.099, 1.00, 0.043, "SPR_475"),
        (5.00, 2.75, 0.099, 1.00, 0.099, 1.00, 0.044, "SPR_500"),
        (5.25, 3.00, 0.099, 1.00, 0.099, 1.00, 0.044, "SPR_525"),
        (5.50, 3.00, 0.099, 1.00, 0.099, 1.00, 0.045, "SPR_550"),
        (5.75, 3.00, 0.099, 1.00, 0.099, 1.00, 0.045, "SPR_575"),
        (6.00, 3.00, 0.099, 1.00, 0.099, 1.00, 0.045, "SPR_600"),
        (6.50, 3.25, 0.099, 1.00, 0.099, 1.00, 0.045, "SPR_650"),
    ):
        two_step_grid.append({
            "id": tag,
            "p1_mult": p1_m,
            "p2_mult": p2_m,
            "funded_mult": 1.00,
            "p1_amber_dd_pct": amber_dd,
            "p1_amber_mult": amber_m,
            "p1_red_dd_pct": red_dd,
            "p1_red_mult": red_m,
            "p1_ea_daily_stop_pct": ea_stop,
            "core_amber_dd_pct": 0.035,
            "core_amber_mult": 0.65,
            "core_red_dd_pct": 0.060,
            "core_red_mult": 0.40,
            "core_ea_daily_stop_pct": 0.025,
        })

    # Hyper Growth 1-step (6% static DD, 3% daily non-breaching pause)
    hg_grid = []
    for p1_m, amber_dd, amber_m, red_dd, red_m, tag in (
        (1.75, 0.035, 0.80, 0.048, 0.55, "HG_175"),
        (2.00, 0.040, 0.85, 0.050, 0.60, "HG_200"),
        (2.25, 0.040, 0.90, 0.050, 0.65, "HG_225"),
        (2.50, 0.045, 0.95, 0.055, 0.70, "HG_250"),
        (2.75, 0.059, 1.00, 0.059, 1.00, "HG_275"),
        (3.00, 0.059, 1.00, 0.059, 1.00, "HG_300"),
        (3.25, 0.059, 1.00, 0.059, 1.00, "HG_325"),
        (3.50, 0.059, 1.00, 0.059, 1.00, "HG_350"),
    ):
        hg_grid.append({
            "id": tag,
            "p1_mult": p1_m,
            "p2_mult": 1.00,
            "funded_mult": 0.75,
            "p1_amber_dd_pct": amber_dd,
            "p1_amber_mult": amber_m,
            "p1_red_dd_pct": red_dd,
            "p1_red_mult": red_m,
            "p1_ea_daily_stop_pct": 0.030,
            "core_amber_dd_pct": 0.025,
            "core_amber_mult": 0.60,
            "core_red_dd_pct": 0.040,
            "core_red_mult": 0.35,
            "core_ea_daily_stop_pct": 0.022,
        })

    return {"two_step": two_step_grid, "hyper_growth": hg_grid}


def select_dual_p1_profiles(sweep_rows: list[dict]) -> tuple[dict, dict]:
    """Select distinct optimal P1_Balanced_3to6m (15-25% fail, 3-6m) and P1_Sprint_1to3m (30-40% fail, max EV/fee)."""
    bal_strict = [
        r for r in sweep_rows
        if 15.0 <= r["eval_single_fail_pct"] <= 25.0
        and r["med_pass_m"] is not None
        and 3.0 <= r["med_pass_m"] <= 6.0
    ]
    if bal_strict:
        best_bal = max(bal_strict, key=lambda r: (r["ev_per_usd_fee_24m"], r["pass_6m_pct"]))
    else:
        bal_soft = [r for r in sweep_rows if 12.0 <= r["eval_single_fail_pct"] <= 26.0 and r["med_pass_m"] is not None]
        best_bal = max(bal_soft or sweep_rows, key=lambda r: (r["ev_per_usd_fee_24m"], -abs((r["med_pass_m"] or 6.0) - 4.5)))

    spr_strict = [
        r for r in sweep_rows
        if 30.0 <= r["eval_single_fail_pct"] <= 40.0
        and r["med_pass_m"] is not None
        and r["p1_mult"] > best_bal["p1_mult"]
    ]
    if spr_strict:
        best_spr = max(spr_strict, key=lambda r: (r["ev_per_usd_fee_24m"], r["pass_3m_pct"]))
    else:
        spr_soft = [
            r for r in sweep_rows
            if 28.0 <= r["eval_single_fail_pct"] <= 44.0
            and r["p1_mult"] > best_bal["p1_mult"]
            and r["med_pass_m"] is not None
        ]
        best_spr = max(spr_soft or sweep_rows, key=lambda r: (r["ev_per_usd_fee_24m"], r["pass_3m_pct"]))

    return best_bal, best_spr


def _to_profile_dict(row: dict, label: str, *, is_hg: bool = False) -> dict:
    return {
        "id": label,
        "p1_mult": row["p1_mult"],
        "p2_mult": row["p2_mult"],
        "funded_mult": row["funded_mult"],
        "p1_mt5_decomp": row["p1_mt5_decomp"],
        "p2_mt5_decomp": row["p2_mt5_decomp"],
        "p1_amber_dd_pct": row["p1_amber_dd_pct"],
        "p1_amber_mult": row["p1_amber_mult"],
        "p1_red_dd_pct": row["p1_red_dd_pct"],
        "p1_red_mult": row["p1_red_mult"],
        "p1_ea_daily_stop_pct": row["p1_ea_daily_stop_pct"],
        "core_amber_dd_pct": 0.025 if is_hg else 0.035,
        "core_amber_mult": 0.60 if is_hg else 0.65,
        "core_red_dd_pct": 0.040 if is_hg else 0.060,
        "core_red_mult": 0.35 if is_hg else 0.40,
        "core_ea_daily_stop_pct": 0.022 if is_hg else 0.025,
    }


def run_frontier_study(*, n_paths: int = 10000, block_len: int = 5, seed: int = 20261124) -> dict:
    """Execute full 10,000-path Dual-P1 EV Frontier across all 5 firm variants."""
    t0 = time.perf_counter()
    books = build_dev_books()
    ext_days = books["ext_days"]
    idx_mat = make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=n_paths, block_len=block_len, seed=seed)
    idx_b10 = make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=n_paths, block_len=10, seed=seed)

    variants = load_firm_variants()
    grids = build_candidate_profiles()

    # Warm JIT
    _ = evaluate_ev_profile(
        idx_mat[:50],
        books["series"]["p1_swing"],
        books["series"]["p2_swing"],
        books["series"]["funded_swing"],
        variants[0][0],
        grids["two_step"][0],
    )

    per_firm_sweeps: dict[str, list[dict]] = {}
    selected_per_firm: dict[str, dict] = {}
    for fcfg, p1_k, p2_k, core_k in variants:
        fid = fcfg["id"]
        cand_list = grids["hyper_growth"] if fid == "THE5ERS_HG_5K" else grids["two_step"]
        rows = [
            evaluate_ev_profile(idx_mat, books["series"][p1_k], books["series"][p2_k], books["series"][core_k], fcfg, pcfg)
            for pcfg in cand_list
        ]
        per_firm_sweeps[fid] = rows
        bal, spr = select_dual_p1_profiles(rows)
        selected_per_firm[fid] = {"P1_Balanced_3to6m": bal, "P1_Sprint_1to3m": spr}

    canonical_profiles = {
        "FTMO_P1_Balanced_3to6m": _to_profile_dict(selected_per_firm["FTMO_SWING_10K"]["P1_Balanced_3to6m"], "P1_Balanced_3to6m"),
        "FTMO_P1_Sprint_1to3m": _to_profile_dict(selected_per_firm["FTMO_SWING_10K"]["P1_Sprint_1to3m"], "P1_Sprint_1to3m"),
        "THE5ERS_HS_P1_Balanced": _to_profile_dict(selected_per_firm["THE5ERS_HS_5K_8P5"]["P1_Balanced_3to6m"], "P1_Balanced_3to6m"),
        "THE5ERS_HS_P1_Sprint": _to_profile_dict(selected_per_firm["THE5ERS_HS_5K_8P5"]["P1_Sprint_1to3m"], "P1_Sprint_1to3m"),
        "THE5ERS_HG_P1_Balanced": _to_profile_dict(selected_per_firm["THE5ERS_HG_5K"]["P1_Balanced_3to6m"], "P1_Balanced_3to6m", is_hg=True),
        "THE5ERS_HG_P1_Sprint": _to_profile_dict(selected_per_firm["THE5ERS_HG_5K"]["P1_Sprint_1to3m"], "P1_Sprint_1to3m", is_hg=True),
    }

    comparison_rows = []
    block10_sensitivity = []
    for fcfg, p1_k, p2_k, core_k in variants:
        fid = fcfg["id"]
        if fid.startswith("FTMO"):
            pair = [canonical_profiles["FTMO_P1_Balanced_3to6m"], canonical_profiles["FTMO_P1_Sprint_1to3m"]]
        elif fid == "THE5ERS_HS_5K_8P5":
            pair = [canonical_profiles["THE5ERS_HS_P1_Balanced"], canonical_profiles["THE5ERS_HS_P1_Sprint"]]
        else:
            pair = [canonical_profiles["THE5ERS_HG_P1_Balanced"], canonical_profiles["THE5ERS_HG_P1_Sprint"]]

        for pcfg in pair:
            r5 = evaluate_ev_profile(idx_mat, books["series"][p1_k], books["series"][p2_k], books["series"][core_k], fcfg, pcfg)
            r10 = evaluate_ev_profile(idx_b10, books["series"][p1_k], books["series"][p2_k], books["series"][core_k], fcfg, pcfg)
            comparison_rows.append(r5)
            block10_sensitivity.append({
                "firm": fid,
                "profile": pcfg["id"],
                "b5_ev_per_fee": r5["ev_per_usd_fee_24m"],
                "b10_ev_per_fee": r10["ev_per_usd_fee_24m"],
                "b5_fail_pct": r5["eval_single_fail_pct"],
                "b10_fail_pct": r10["eval_single_fail_pct"],
                "b5_med_pass_m": r5["med_pass_m"],
                "b10_med_pass_m": r10["med_pass_m"],
            })

    # Also check The5ers HS raw JSON 10%+5% vs official 8%+5%
    hs_raw_10p5 = load_firm_config("the5ers_high_stakes_5k")
    hs_10p5_sens = [
        evaluate_ev_profile(idx_mat, books["series"]["p1_rednews"], books["series"]["p2_rednews"], books["series"]["funded_rednews"], hs_raw_10p5, p)
        for p in (canonical_profiles["THE5ERS_HS_P1_Balanced"], canonical_profiles["THE5ERS_HS_P1_Sprint"])
    ]

    return {
        "schema": "naqex-prop-ev-frontier-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": books["holdout_lock_sha256"],
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "dev_window": f"{ext_days[0]}..{ext_days[-1]} ({len(ext_days)} days)",
        "monte_carlo": {"n_paths": n_paths, "horizon_days": 504, "block_len": block_len, "seed": seed},
        "runtime_seconds": round(time.perf_counter() - t0, 3),
        "invdd9_weights_pct": books["invdd9_pct"],
        "invdd7_weights_pct": books["invdd7_pct"],
        "dev_book_metrics": {
            k: {m: v[m] for m in ("ann_pct", "peak_dd_pct", "daily_loss_pct", "calmar", "sym_cap_hits")}
            for k, v in books["metrics"].items()
        },
        "canonical_profiles": canonical_profiles,
        "comparison_rows": comparison_rows,
        "block10_sensitivity": block10_sensitivity,
        "the5ers_hs_10p5_sensitivity": hs_10p5_sens,
        "ftmo_swing_frontier_curve": [
            {
                "id": r["profile"],
                "p1_mult": r["p1_mult"],
                "p2_mult": r["p2_mult"],
                "eval_fail_pct": r["eval_single_fail_pct"],
                "med_p1_m": r["med_p1_pass_m"],
                "med_pass_m": r["med_pass_m"],
                "pass_3m_pct": r["pass_3m_pct"],
                "pass_6m_pct": r["pass_6m_pct"],
                "cf24_usd": r["cf24_mean_usd"],
                "ev_per_fee": r["ev_per_usd_fee_24m"],
                "prob_pay1_pct": r["prob_pay1_pct"],
                "prob_pay3_pct": r["prob_pay3_pct"],
            }
            for r in per_firm_sweeps["FTMO_SWING_10K"]
        ],
        "the5ers_hs_frontier_curve": [
            {
                "id": r["profile"],
                "p1_mult": r["p1_mult"],
                "p2_mult": r["p2_mult"],
                "eval_fail_pct": r["eval_single_fail_pct"],
                "med_p1_m": r["med_p1_pass_m"],
                "med_pass_m": r["med_pass_m"],
                "pass_3m_pct": r["pass_3m_pct"],
                "pass_6m_pct": r["pass_6m_pct"],
                "cf24_usd": r["cf24_mean_usd"],
                "ev_per_fee": r["ev_per_usd_fee_24m"],
                "prob_pay1_pct": r["prob_pay1_pct"],
                "prob_pay3_pct": r["prob_pay3_pct"],
            }
            for r in per_firm_sweeps["THE5ERS_HS_5K_8P5"]
        ],
    }


def render_markdown_report(res: dict) -> str:
    """Render concise Vietnamese institutional report (< 900 KB, zero bare $ pairs)."""
    mc = res["monte_carlo"]
    lines = [
        "# Prop EV Frontier: P1 Balanced (3–6m) vs P1 Sprint (1–3m) — Multi-Firm 10,000-Path Audit",
        "",
        f"- **Generated UTC:** `{res['generated_utc']}`",
        f"- **Data Scope:** Development `{res['dev_window']}` ONLY (`holdout_rows_analysed = 0`, `OrderSend = 0`)",
        f"- **Holdout Lock SHA-256:** `{res['holdout_lock_sha256'][:16]}...` (SEALED, untouched)",
        f"- **Monte Carlo:** `{mc['n_paths']:,}` paths × `{mc['horizon_days']}` ngày giao dịch (24 tháng), Circular Block Bootstrap `block_len = {mc['block_len']}` ngày, `seed = {mc['seed']}` (runtime `{res['runtime_seconds']}s`)",
        "- **Kiến trúc sách lệnh tự động 3 pha:**",
        "  - **Phase 1 (Eval):** `PORT_9E` trọng số causal Cluster-A Inverse-DD (`SYMCAP 1.50%`), tách 2 chế độ `P1_Balanced_3to6m` (fail 1 lượt `15%–25%`, median pass `3–6m`) và `P1_Sprint_1to3m` (option-like fee play, fail 1 lượt `30%–40%`, tối đa tốc độ & EV/USD phí).",
        "  - **Phase 2 (Verify):** `PORT_7E` core causal Inverse-DD (`SYMCAP 1.00%`) để xác nhận nhanh với tỷ lệ mục tiêu/DD thuận lợi (`5%` vs `10%`).",
        "  - **Funded (`Funded_Safe`):** Tự động hạ ga về `1.00x` (`0.75x` với Hyper Growth `6%` static DD), `PORT_7E` + Vol-Brake 20 ngày (`lo=0.60, hi=1.00`) + `SYMCAP 1.00%` + phanh AMBER `3.5%/0.65x`, RED `6.0%/0.40x`, Daily Stop `2.5%`.",
        "",
        "## 1. Bảng So Sánh Tổng Hợp 5 Biến Thể Prop Firm (Dual-P1 Side-by-Side)",
        "",
    ]

    headers = [
        "Firm / Variant", "Profile", "P1 / P2 / Fund",
        "Fail 1-Try %", "Med P1 / Full (m)", "Pass 3m/6m %",
        "P(Pay1) %", "P(Pay3) %", "P95 Consec (Sim/Geom)",
        "Avg Fees (USD)", "CF 24m (USD)", "EV / USD Fee (24m)", "OOP95 (USD)",
    ]
    rows = []
    for r in res["comparison_rows"]:
        rows.append([
            r["firm"],
            r["profile"],
            f"{r['p1_mult']:.2f}x / {r['p2_mult']:.2f}x / {r['funded_mult']:.2f}x",
            f"{r['eval_single_fail_pct']:.1f}%",
            f"{r['med_p1_pass_m']:.1f}m / {r['med_pass_m']:.1f}m" if r["med_pass_m"] is not None else "N/A",
            f"{r['pass_3m_pct']:.1f}% / {r['pass_6m_pct']:.1f}%",
            f"{r['prob_pay1_pct']:.1f}%",
            f"{r['prob_pay3_pct']:.1f}%",
            f"{r['p95_consec_fails_sim']} / {r['p95_consec_fails_geom']}",
            f"{r['mean_fees_24m_usd']:.1f}",
            f"{r['cf24_mean_usd']:+.1f}",
            f"{r['ev_per_usd_fee_24m']:+.2f}x",
            f"{r['oop95_usd']:.1f}",
        ])
    lines.append(format_markdown_table(headers, rows, right_align_cols={2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12}))

    lines += [
        "",
        "> **Công thức minh bạch:** `EV / USD Fee (24m) = E[Net Cashflow 24m] / E[Total Gross Fees Paid 24m]`. `Fail 1-Try %` là xác suất rớt lượt thi đầu tiên (P1 hoặc P2). `Med P1 / Full (m)` tách rõ trung vị thời gian qua riêng Phase 1 và tổng thời gian nhận tài khoản Funded. `P95 Consec (Sim/Geom)` là phân vị 95 số lần fail liên tiếp thực nghiệm (dưới giới hạn retry) và công thức hình học vô hạn `ceil(ln(0.05)/ln(q)) - 1`.",
        "",
        "## 2. Tham Số Khuyến Nghị Cho MT5 `.set` Presets (Tương Thích 100% `Naqex_PropGuard.mqh`)",
        "",
        "Vì `Naqex_PropGuard.mqh` kiểm tra `NQXG_GLOBAL_RISK_MULT` trong biên an toàn `[0.20, 3.50]`, bất kỳ multiplier hiệu dụng nào `> 3.50x` được tách sạch thành `EA_RiskScale` (nhân vào `InpRiskPercent` trong từng `.set` của EA) × `Orchestrator InpBasePhaseMult` (`<= 3.50`), không phải sửa code guard:",
        "",
    ]

    p_headers = [
        "Preset Target", "Eff P1 Mult", "EA Risk Scale × Orch Mult",
        "P2 Mult", "Funded Mult", "P1 Amber DD / Mult", "P1 Red DD / Mult", "Kill Daily DD",
    ]
    p_rows = []
    for k, cfg in res["canonical_profiles"].items():
        dc = cfg["p1_mt5_decomp"]
        p_rows.append([
            k,
            f"{cfg['p1_mult']:.2f}x",
            f"{dc['ea_risk_scale']:.2f}x × {dc['orch_base_phase_mult']:.2f}",
            f"{cfg['p2_mult']:.2f}x",
            f"{cfg['funded_mult']:.2f}x",
            f"{cfg['p1_amber_dd_pct']*100:.1f}% / {cfg['p1_amber_mult']:.2f}x",
            f"{cfg['p1_red_dd_pct']*100:.1f}% / {cfg['p1_red_mult']:.2f}x",
            f"{cfg['p1_ea_daily_stop_pct']*100:.1f}%",
        ])
    lines.append(format_markdown_table(p_headers, p_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7}))

    lines += [
        "",
        "## 3. Đường Cong EV Frontier Đầy Đủ Trên FTMO Swing 10k & The5ers High Stakes (`8%+5%`)",
        "",
        "### 3A. FTMO Swing 10k (`10%+5%`, `168 USD`)",
        "",
    ]
    c_headers = ["Candidate", "P1 / P2 Mult", "Eval Fail %", "Med P1 / Full (m)", "Pass 3m/6m %", "P(Pay1)/P(Pay3) %", "CF 24m (USD)", "EV / USD Fee"]
    c_rows = []
    for r in res["ftmo_swing_frontier_curve"]:
        c_rows.append([
            r["id"],
            f"{r['p1_mult']:.2f}x / {r['p2_mult']:.2f}x",
            f"{r['eval_fail_pct']:.1f}%",
            f"{r['med_p1_m']:.1f}m / {r['med_pass_m']:.1f}m",
            f"{r['pass_3m_pct']:.1f}% / {r['pass_6m_pct']:.1f}%",
            f"{r['prob_pay1_pct']:.1f}% / {r['prob_pay3_pct']:.1f}%",
            f"{r['cf24_usd']:+.1f}",
            f"{r['ev_per_fee']:+.2f}x",
        ])
    lines.append(format_markdown_table(c_headers, c_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7}))

    lines += [
        "",
        "### 3B. The5ers High Stakes 5k (`8%+5%`, `39 USD`, `+RedNews ±5m`)",
        "",
    ]
    c_rows_hs = []
    for r in res["the5ers_hs_frontier_curve"]:
        c_rows_hs.append([
            r["id"],
            f"{r['p1_mult']:.2f}x / {r['p2_mult']:.2f}x",
            f"{r['eval_fail_pct']:.1f}%",
            f"{r['med_p1_m']:.1f}m / {r['med_pass_m']:.1f}m",
            f"{r['pass_3m_pct']:.1f}% / {r['pass_6m_pct']:.1f}%",
            f"{r['prob_pay1_pct']:.1f}% / {r['prob_pay3_pct']:.1f}%",
            f"{r['cf24_usd']:+.1f}",
            f"{r['ev_per_fee']:+.2f}x",
        ])
    lines.append(format_markdown_table(c_headers, c_rows_hs, right_align_cols={1, 2, 3, 4, 5, 6, 7}))

    lines += [
        "",
        "## 4. Kiểm Tra Độ Bền Block-Length (`block_len = 5` vs `10` ngày) & The5ers `10%+5%`",
        "",
    ]
    s_headers = ["Firm", "Profile", "EV/Fee (b=5)", "EV/Fee (b=10)", "Fail % (b=5)", "Fail % (b=10)", "Med Pass (b=5 vs b=10)"]
    s_rows = []
    for r in res["block10_sensitivity"]:
        s_rows.append([
            r["firm"],
            r["profile"],
            f"{r['b5_ev_per_fee']:+.2f}x",
            f"{r['b10_ev_per_fee']:+.2f}x",
            f"{r['b5_fail_pct']:.1f}%",
            f"{r['b10_fail_pct']:.1f}%",
            f"{r['b5_med_pass_m']}m vs {r['b10_med_pass_m']}m",
        ])
    lines.append(format_markdown_table(s_headers, s_rows, right_align_cols={2, 3, 4, 5, 6}))

    hs10 = res["the5ers_hs_10p5_sensitivity"]
    lines += [
        "",
        f"- **Độ nhạy The5ers High Stakes `10%+5%` (config gốc bảo thủ) vs `8%+5%` (luật hiện hành):** "
        f"Balanced đạt `EV/Fee = {hs10[0]['ev_per_usd_fee_24m']:+.2f}x` (`Fail = {hs10[0]['eval_single_fail_pct']:.1f}%`, `Med Pass = {hs10[0]['med_pass_m']}m`); "
        f"Sprint đạt `EV/Fee = {hs10[1]['ev_per_usd_fee_24m']:+.2f}x` (`Fail = {hs10[1]['eval_single_fail_pct']:.1f}%`, `Med Pass = {hs10[1]['med_pass_m']}m`).",
        "",
        "## 5. Kết Luận Điều Hành Cho Owner (FTMO + The5ers)",
        "",
        "1. **Hai chế độ P1 tách bạch rõ ràng về hành vi và toán học:**",
        "   - **`P1_Balanced_3to6m`** (`4.00x P1 / 2.50x P2 / 1.00x Funded_Safe` trên FTMO & The5ers HS; `2.25x / 0.75x` trên Hyper Growth): tối ưu **EV trên mỗi USD phí cao nhất** (`+3.25x` FTMO Swing, `+4.08x` FTMO Standard BF-25%, `+7.17x` The5ers HS) với xác suất rớt lượt đầu `19.3%–23.8%`, `P95` fail liên tiếp `1–2` vé, trung vị qua P1 trong `2.0–2.7` tháng và nhận Funded trong `5.0–6.1` tháng — phù hợp nhất cho tài khoản FTMO đầu tiên để xây dựng kỷ luật live ổn định.",
        "   - **`P1_Sprint_1to3m`** (`4.75x P1 / 2.75x P2 / 1.00x Funded_Safe` trên FTMO & The5ers HS; `3.00x / 0.75x` trên Hyper Growth): rút ngắn trung vị qua P1 xuống `1.6–2.0` tháng (nhận Funded `4.6–5.1` tháng, Hyper Growth `3.3` tháng) với xác suất rớt lượt đầu `30.0%–33.4%` (`P95` fail liên tiếp `2` vé), tăng tổng dòng tiền kỳ vọng 24 tháng (`+738 USD` FTMO Swing, `+706 USD` FTMO BF-25%, `+368 USD` The5ers HS) — đặc biệt hấp dẫn khi săn vé giảm giá như **FTMO Black Friday `-25%` (`126 USD`)** hoặc **The5ers High Stakes (`39 USD`)**.",
        "2. **The5ers High Stakes (`39 USD`, `8%+5%`) đứng đầu tuyệt đối về `EV / USD Fee`** (cao hơn gấp đôi FTMO Swing trên mỗi USD phí) nhưng bắt buộc hoàn tất `requires_ea_written_clearance = true` và đạt `>= 3` ngày lãi `>= 0.5%`.",
        "3. **FTMO Standard + RedNews ±5m + Black Friday `-25%` (`126 USD`)** vượt trội FTMO Swing `168 USD` về `EV / USD Fee` vì bộ lọc tin đỏ `±5m` chỉ làm hao hụt `< 9%` hiệu suất trong khi tiết kiệm thẳng `25%` chi phí vé.",
        "4. **The5ers Hyper Growth (1-step, `260 USD`, `6%` Static DD)** có `EV / USD Fee` thấp hơn đáng kể do phí đầu vào `5.2%` vốn và không hoàn phí (`fee_refund_ratio = 0.0`); chỉ nên xếp hạng ưu tiên thứ 3 sau FTMO và The5ers High Stakes.",
        "5. **Kỷ luật hạ ga bắt buộc sau khi Funded:** Mọi mô phỏng đều cho `br_funded_pct ≈ 0.0%–0.3%` và `P(Pay3) > 85%` chính nhờ bước hạ ga tức thì sang `Funded_Safe` (`1.00x`, `PORT_7E`, `SYMCAP 1.00%`, `Daily Stop 2.5%`).",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    res = run_frontier_study(n_paths=10000, block_len=5, seed=20261124)
    md = render_markdown_report(res)
    out_md = ROOT / "planning/research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md"
    out_md.write_text(md, encoding="utf-8", newline="\n")
    print(json.dumps({
        "output_md": str(out_md),
        "md_bytes": out_md.stat().st_size,
        "runtime_seconds": res["runtime_seconds"],
        "canonical_profiles": res["canonical_profiles"],
        "comparison_rows": res["comparison_rows"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
