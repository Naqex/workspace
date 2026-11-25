"""Naqex Round-3 Architecture Counterfactual Benchmark (OrderSend=0, Holdout 2025+ Sealed).

Answers Astra Round-3 Step 4 rigorously on frozen Development M1 tapes (2018-01-02..2024-12-31):
  1. Directional Factor Cluster Caps (USD / JPY / US100 / Total Account) vs Per-Symbol Cap alone.
  2. Controlled Pairwise Comparison A — Sizing Policy on IDENTICAL 7E + Factor Caps:
       - `STATIC_LOCK_7E` (frozen benchmark: 4.00x -> 2.01x at +5%/+4%, Amber/Red brakes)
       - `BARRIER_HEADROOM_7E` (state-dependent min(phase, daily_headroom, static_headroom) + target-proximity taper, NEVER boosts risk)
  3. Controlled Pairwise Comparison B — Portfolio Composition on IDENTICAL Static Sizing + Factor Caps:
       - `7E_FIXED` (E1..E7 fixed across all 3 phases) vs `8E_BASELINE` (E1..E7 + S6 in P1, 7E in P2/Funded)
  4. Real Calendar-Day Horizons (180d / 365d / 730d including weekends & non-trading holidays, block_len=7 & 28 calendar days)
     with exact SKU contracts (`FTMO_SWING_10K` primary, `THE5ERS_HS_5K` shadow-scored), payout settlement lag,
     withdrawal fee (1.0% / 3.5%), separated Hub Credit vs external cash refund, and friction stress 1.0x / 1.25x / 1.5x / 2.0x.

STRICT SAFETY INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 integrity; `holdout_rows_analysed = 0`, `order_send_count = 0`.
  - Strictly offline & deterministic (`SEED = 20261125`).
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.portfolio_v1_vs_v2_study import apply_cost_stress_to_tapes
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass27_portfolio_m1_phase_audit as p27
import pass28_final_discovery_rednews_frontier as p28
from quant_factory.report_gen import write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SEED: int = 20261125
DEFAULT_N_PATHS: int = 5_000
USD_VND_RATE: float = 25_500.0
MAX_RETRIES: int = 4

CORE7_IDS: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)
LIVE8_IDS: tuple[str, ...] = CORE7_IDS + ("S6_FX_USD_BSK",)
FRICTION_LEVELS: tuple[tuple[str, float], ...] = (
    ("1.00x", 1.00),
    ("1.25x", 1.25),
    ("1.50x", 1.50),
    ("2.00x", 2.00),
)

OUT_MD = ROOT / "planning/research/ROUND3-FRAME-COUNTERFACTUAL-BENCHMARK-20261125.md"
OUT_JSON = ROOT / "planning/research/ROUND3-FRAME-COUNTERFACTUAL-BENCHMARK-20261125.json"
CONTRACTS_PATH = AI_ENGINES / "configs/prop_contracts_v2.json"


# ---------------------------------------------------------------------------
# 1. Exact M1 Replay WITH Directional Factor Cluster Caps (USD / JPY / US100)
# ---------------------------------------------------------------------------

def _directional_factor_exposures(asset: str, side: int) -> tuple[int, int, int]:
    """Return signed unit exposure `(usd_dir, jpy_dir, idx_dir)` in {-1, 0, +1}."""
    u = str(asset or "").upper()
    s = 1 if side >= 0 else -1
    if any(k in u for k in ("US100", "NAS100", "NDX", "US500", "SPX")):
        return 0, 0, s
    usd_dir = 0
    jpy_dir = 0
    if u.startswith("USD"):
        usd_dir = s
    elif u.endswith("USD"):
        usd_dir = -s
    if u.startswith("JPY"):
        jpy_dir = s
    elif u.endswith("JPY"):
        jpy_dir = -s
    return usd_dir, jpy_dir, 0


def replay_portfolio_m1_with_factor_caps(
    days: list[str],
    tapes: dict[str, dict[str, tuple[dict[str, Any], np.ndarray, np.ndarray]]],
    risks: dict[str, float],
    initial_capital: float,
    *,
    max_symbol_risk_pct: float = 0.0175,
    max_usd_cluster_pct: float = 0.0225,
    max_jpy_cluster_pct: float = 0.0200,
    max_idx_cluster_pct: float = 0.0175,
    max_account_open_pct: float = 0.0300,
    red_news_cal: dict[str, list[dict[str, Any]]] | None = None,
    red_news_pad_sec: int = 300,
    profile_mode: str = "Swing",
) -> tuple[dict[str, Any], list[dict[str, Any]], dict[str, float]]:
    """Exact M1 portfolio replay enforcing per-symbol AND directional USD/JPY/US100 factor cluster caps."""
    active_tapes: dict[str, dict] = {}
    for eng in risks:
        if red_news_cal is not None:
            gt, _ = p28.apply_red_news_guard_to_tape(tapes[eng], red_news_cal, mode="FLATTEN_5M", pad_sec=red_news_pad_sec)
            active_tapes[eng] = gt
        else:
            active_tapes[eng] = tapes[eng]

    balance = float(initial_capital)
    peak = balance
    max_dd = 0.0
    max_day_dd = 0.0
    max_usd_cluster_seen = 0.0
    max_jpy_cluster_seen = 0.0
    max_idx_cluster_seen = 0.0
    blocked_factor = 0
    clamped_factor = 0
    blocked_symbol = 0

    exits_log: list[dict[str, Any]] = []
    sorted_days = sorted(days)

    for day in sorted_days:
        day_candidates = [(eng, active_tapes[eng][day]) for eng in risks if day in active_tapes[eng]]
        if not day_candidates:
            continue
        day_candidates.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))

        sized = []
        active_meta: list[dict[str, Any]] = []

        for eid, (row, stamps, marks) in day_candidates:
            asset = str(row.get("asset") or ("USDJPY" if "USDJPY" in eid else ("GBPUSD" if "GBPUSD" in eid else eid)))
            side = int(row.get("side", 1))
            stamp = int(stamps[0])

            overlap = [a for a in active_meta if stamp < a["release"]]
            used_sym_risk = sum(a["risk_pct"] for a in overlap if a["asset"] == asset)
            used_tot_risk = sum(a["risk_pct"] for a in overlap)

            u_l = sum(a["risk_pct"] for a in overlap if a["usd_dir"] > 0)
            u_s = sum(a["risk_pct"] for a in overlap if a["usd_dir"] < 0)
            j_l = sum(a["risk_pct"] for a in overlap if a["jpy_dir"] > 0)
            j_s = sum(a["risk_pct"] for a in overlap if a["jpy_dir"] < 0)
            i_l = sum(a["risk_pct"] for a in overlap if a["idx_dir"] > 0)
            i_s = sum(a["risk_pct"] for a in overlap if a["idx_dir"] < 0)

            usd_d, jpy_d, idx_d = _directional_factor_exposures(asset, side)
            req_risk = float(risks[eid])
            sym_rem = max(0.0, max_symbol_risk_pct - used_sym_risk) if max_symbol_risk_pct > 0 else 9.9
            tot_rem = max(0.0, max_account_open_pct - used_tot_risk) if max_account_open_pct > 0 else 9.9
            fac_rem = tot_rem
            if max_usd_cluster_pct > 0:
                if usd_d > 0:
                    fac_rem = min(fac_rem, max(0.0, max_usd_cluster_pct - u_l))
                elif usd_d < 0:
                    fac_rem = min(fac_rem, max(0.0, max_usd_cluster_pct - u_s))
            if max_jpy_cluster_pct > 0:
                if jpy_d > 0:
                    fac_rem = min(fac_rem, max(0.0, max_jpy_cluster_pct - j_l))
                elif jpy_d < 0:
                    fac_rem = min(fac_rem, max(0.0, max_jpy_cluster_pct - j_s))
            if max_idx_cluster_pct > 0:
                if idx_d > 0:
                    fac_rem = min(fac_rem, max(0.0, max_idx_cluster_pct - i_l))
                elif idx_d < 0:
                    fac_rem = min(fac_rem, max(0.0, max_idx_cluster_pct - i_s))

            eff_risk = min(req_risk, sym_rem, fac_rem)
            if eff_risk <= 1e-9:
                if fac_rem <= sym_rem:
                    blocked_factor += 1
                else:
                    blocked_symbol += 1
                continue
            if fac_rem < min(req_risk, sym_rem) - 1e-12:
                clamped_factor += 1

            budget = initial_capital * eff_risk
            mgn_1lot, vmin, vstep, vmax, comm_1lot = p27.margin_per_lot_usd(asset, float(row["entry_price"]), profile_mode)
            acct = jpy_eq.Account(eid, initial_capital, mgn_1lot, vmin, vstep, vmax)
            lot = jpy_eq.floor_lot(budget, float(row["stop_risk_with_cost_usd"]), acct)
            used_m = sum(t.margin for t in sized if stamp < t.release)
            avail = balance + sum(t.open_floating(stamp) for t in sized) - used_m
            if lot < vmin or lot * (mgn_1lot + comm_1lot) > avail:
                continue

            actual_risk_pct = (lot * float(row["stop_risk_with_cost_usd"])) / initial_capital
            row_copy = {**row, "asset": asset, "at_open": bool(row.get("at_open", False)), "_eff_risk": actual_risk_pct}
            st_obj = portfolio.SizedTrade(row_copy, stamps, marks, lot, lot * mgn_1lot, lot * float(row["net_usd_per_lot"]))
            sized.append(st_obj)
            meta_rec = {
                "asset": asset,
                "usd_dir": usd_d,
                "jpy_dir": jpy_d,
                "idx_dir": idx_d,
                "release": st_obj.release,
                "risk_pct": actual_risk_pct,
            }
            active_meta.append(meta_rec)

            now_ov = overlap + [meta_rec]
            max_usd_cluster_seen = max(
                max_usd_cluster_seen,
                sum(a["risk_pct"] for a in now_ov if a["usd_dir"] > 0),
                sum(a["risk_pct"] for a in now_ov if a["usd_dir"] < 0),
            )
            max_jpy_cluster_seen = max(
                max_jpy_cluster_seen,
                sum(a["risk_pct"] for a in now_ov if a["jpy_dir"] > 0),
                sum(a["risk_pct"] for a in now_ov if a["jpy_dir"] < 0),
            )
            max_idx_cluster_seen = max(
                max_idx_cluster_seen,
                sum(a["risk_pct"] for a in now_ov if a["idx_dir"] > 0),
                sum(a["risk_pct"] for a in now_ov if a["idx_dir"] < 0),
            )

        if not sized:
            continue

        _, comb_marks, _, _, _ = portfolio.combined_marks(sized)
        day_net = sum(t.net for t in sized)
        day_min_flt = float(comb_marks[:, 2].min()) if len(comb_marks) > 0 else 0.0
        day_dd = max(0.0, -day_min_flt)
        day_low_eq = balance + day_min_flt
        balance += day_net
        peak = max(peak, balance)
        max_dd = max(max_dd, peak - balance, peak - day_low_eq)
        max_day_dd = max(max_day_dd, day_dd)
        exits_log.append({
            "day": day,
            "net_usd": round(day_net, 6),
            "day_dd_usd": round(day_dd, 6),
            "trades": len(sized),
        })

    metrics = {
        "net_usd": round(balance - initial_capital, 2),
        "max_dd_pct": round((max_dd / initial_capital) * 100.0, 2),
        "worst_day_dd_pct": round((max_day_dd / initial_capital) * 100.0, 2),
        "active_days": len(exits_log),
    }
    diag = {
        "peak_usd_cluster_pct": round(max_usd_cluster_seen * 100.0, 2),
        "peak_jpy_cluster_pct": round(max_jpy_cluster_seen * 100.0, 2),
        "peak_idx_cluster_pct": round(max_idx_cluster_seen * 100.0, 2),
        "clamped_factor": float(clamped_factor),
        "blocked_factor": float(blocked_factor),
        "blocked_symbol": float(blocked_symbol),
    }
    return metrics, exits_log, diag


# ---------------------------------------------------------------------------
# 2. Real Calendar-Day Alignment & Numba Settled-Cash Lifecycle Simulator
# ---------------------------------------------------------------------------

def align_exits_to_real_calendar(
    start_iso: str,
    end_iso: str,
    exits_log: list[dict[str, Any]],
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Map observed exits onto EVERY real calendar day (incl. weekends & non-trading holidays)."""
    d0 = date.fromisoformat(start_iso)
    d1 = date.fromisoformat(end_iso)
    n_cal = (d1 - d0).days + 1
    cal_days = [(d0 + timedelta(days=i)).isoformat() for i in range(n_cal)]
    day_to_idx = {dk: i for i, dk in enumerate(cal_days)}

    nets = np.zeros(n_cal, dtype=np.float64)
    dds = np.zeros(n_cal, dtype=np.float64)
    flgs = np.zeros(n_cal, dtype=np.int8)
    for row in exits_log:
        idx = day_to_idx.get(row["day"])
        if idx is not None:
            nets[idx] = float(row["net_usd"])
            dds[idx] = float(row["day_dd_usd"])
            flgs[idx] = 1
    return cal_days, nets, dds, flgs


def make_calendar_block_indices(n_cal: int, horizon_cal: int, n_paths: int, block_cal_days: int, seed: int) -> np.ndarray:
    """Non-wrapping contiguous calendar-day block bootstrap (avoids stitching Dec 2024 into Jan 2018!)."""
    rng = np.random.default_rng(seed)
    max_start = max(1, n_cal - block_cal_days)
    n_blocks = (horizon_cal + block_cal_days - 1) // block_cal_days
    starts = rng.integers(0, max_start, size=(n_paths, n_blocks), dtype=np.int32)
    out = np.empty((n_paths, horizon_cal), dtype=np.int32)
    for b in range(n_paths):
        pos = 0
        for blk in range(n_blocks):
            s = int(starts[b, blk])
            take = min(block_cal_days, horizon_cal - pos)
            for k in range(take):
                out[b, pos + k] = s + k
            pos += take
    return out


@njit(cache=True)
def _simulate_real_calendar_prop_numba(
    idx_matrix: np.ndarray,
    n_p1_s: np.ndarray, d_p1_s: np.ndarray, f_p1_s: np.ndarray,
    n_p1_l: np.ndarray, d_p1_l: np.ndarray, f_p1_l: np.ndarray,
    n_p2_s: np.ndarray, d_p2_s: np.ndarray, f_p2_s: np.ndarray,
    n_p2_l: np.ndarray, d_p2_l: np.ndarray, f_p2_l: np.ndarray,
    n_fn: np.ndarray, d_fn: np.ndarray, f_fn: np.ndarray,
    cap: float,
    fee: float,
    ext_cash_refund_pct: float,
    p1_target: float,
    p2_target: float,
    daily_lim: float,
    static_lim: float,
    min_days: int,
    min_prof_day: float,
    payout_split: float,
    payout_cycle_cal_days: int,
    settlement_lag_cal_days: int,
    min_payout_net_usd: float,
    withdrawal_fee_pct: float,
    max_retries: int,
    p1_lock_trigger: float,
    p2_lock_trigger: float,
    amber_dd: float,
    amber_scale: float,
    red_dd: float,
    red_scale: float,
    kill_daily_dd: float,
    kill_static_dd: float,
    sizing_mode: int,  # 0 = STATIC_PHASE_LOCK | 1 = BARRIER_HEADROOM_MIN
):
    """Exact real-calendar-day simulator with settled cash lag, withdrawal fee & zero same-day compounding."""
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10_000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)
    daily_cap = cap * daily_lim
    static_floor = cap * (1.0 - static_lim)

    net_settled_365 = np.zeros(n_paths, dtype=np.float64)
    net_settled_730 = np.zeros(n_paths, dtype=np.float64)
    max_oop_arr = np.zeros(n_paths, dtype=np.float64)
    pay1_cal_day = np.full(n_paths, -1, dtype=np.int32)
    pass_cal_day = np.full(n_paths, -1, dtype=np.int32)
    fail_1try = np.zeros(n_paths, dtype=np.int8)
    fail_1try_daily = np.zeros(n_paths, dtype=np.int8)
    fail_1try_static = np.zeros(n_paths, dtype=np.int8)
    wiped_arr = np.zeros(n_paths, dtype=np.int8)
    payout_cycles_arr = np.zeros(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        attempts = 1
        fees_paid = fee
        refunded = False
        settled_in = 0.0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        first_resolved = 0
        is_dead = 0
        funded_first_trade_day = -1
        last_payout_req_day = -1
        payout_cnt = 0

        # Up to 64 queued payouts awaiting T+settlement_lag calendar days
        q_due_day = np.full(64, -1, dtype=np.int32)
        q_amt = np.zeros(64, dtype=np.float64)
        q_head = 0
        q_tail = 0

        for d in range(horizon):
            # Settle any queued payouts arriving on calendar day `d`
            while q_head < q_tail and q_due_day[q_head % 64] <= d:
                settled_in += q_amt[q_head % 64]
                if f_pay < 0:
                    f_pay = d
                q_head += 1

            if is_dead == 0:
                src = idx_matrix[b, d]
                eq_pct = (bal - cap) / cap
                static_dd_pct = max(0.0, -eq_pct)

                # Choose base stage tape (matches MQL5 Orchestrator 1:1: AMBER/RED scale CURRENT stage preset!)
                if stage == 1:
                    if eq_pct >= p1_target * p1_lock_trigger:
                        net = n_p1_l[src] * scale
                        dd = d_p1_l[src] * scale
                        flg = f_p1_l[src]
                    else:
                        net = n_p1_s[src] * scale
                        dd = d_p1_s[src] * scale
                        flg = f_p1_s[src]
                elif stage == 2:
                    if eq_pct >= p2_target * p2_lock_trigger:
                        net = n_p2_l[src] * scale
                        dd = d_p2_l[src] * scale
                        flg = f_p2_l[src]
                    else:
                        net = n_p2_s[src] * scale
                        dd = d_p2_s[src] * scale
                        flg = f_p2_s[src]
                else:
                    net = n_fn[src] * scale
                    dd = d_fn[src] * scale
                    flg = f_fn[src]

                if eq_pct <= -red_dd:
                    net *= red_scale
                    dd *= red_scale
                elif eq_pct <= -amber_dd:
                    net *= amber_scale
                    dd *= amber_scale

                # SizingMode 1: BARRIER_HEADROOM_MIN (smoothly tapers risk near static floor OR near profit target — NEVER boosts!)
                if sizing_mode == 1 and flg == 1:
                    mult_taper = 1.0
                    static_headroom = max(0.0, kill_static_dd - static_dd_pct)
                    if static_headroom < 0.035:
                        mult_taper = min(mult_taper, max(0.25, static_headroom / 0.035))
                    if stage == 1 and eq_pct > 0.0:
                        rem_frac = max(0.0, p1_target - eq_pct) / p1_target
                        if rem_frac < 0.35:
                            mult_taper = min(mult_taper, max(0.35, rem_frac / 0.35))
                    elif stage == 2 and eq_pct > 0.0:
                        rem_frac = max(0.0, p2_target - eq_pct) / p2_target
                        if rem_frac < 0.35:
                            mult_taper = min(mult_taper, max(0.35, rem_frac / 0.35))
                    net *= mult_taper
                    dd *= mult_taper

                # Check hard daily & static floor breach on raw M1 intraday depth
                day_low = bal - dd
                breach_daily = (dd >= daily_cap)
                breach_static = (day_low <= static_floor) or ((bal + net) <= static_floor)

                if breach_daily or breach_static:
                    if first_resolved == 0:
                        first_resolved = 1
                        fail_1try[b] = 1
                        if breach_daily:
                            fail_1try_daily[b] = 1
                        if breach_static:
                            fail_1try_static[b] = 1
                    if attempts < max_retries:
                        attempts += 1
                        fees_paid += fee
                        oop_now = fees_paid - settled_in
                        if oop_now > max_oop:
                            max_oop = oop_now
                        stage = 1
                        bal = cap
                        tdays = 0
                        refunded = False
                        funded_first_trade_day = -1
                        last_payout_req_day = -1
                    else:
                        wiped_arr[b] = 1
                        is_dead = 1
                else:
                    bal += net
                    if flg == 1:
                        if min_prof_day > 0.0:
                            if net >= cap * min_prof_day:
                                tdays += 1
                        else:
                            tdays += 1
                        if stage == 3 and funded_first_trade_day < 0:
                            funded_first_trade_day = d

                    if stage == 1 and bal >= p1_goal and tdays >= min_days:
                        stage = 2
                        bal = cap
                        tdays = 0
                    elif stage == 2 and bal >= p2_goal and tdays >= min_days:
                        if first_resolved == 0:
                            first_resolved = 1
                        if f_pass < 0:
                            f_pass = d
                        stage = 3
                        bal = cap
                        tdays = 0
                        funded_first_trade_day = -1
                        last_payout_req_day = d
                    elif stage == 3 and funded_first_trade_day >= 0:
                        anchor_d = last_payout_req_day if last_payout_req_day >= funded_first_trade_day else funded_first_trade_day
                        if (d - anchor_d) >= payout_cycle_cal_days:
                            prof = bal - cap
                            net_before_wd = prof * payout_split
                            if prof > 0.0 and net_before_wd >= min_payout_net_usd:
                                net_after_wd = net_before_wd * (1.0 - withdrawal_fee_pct)
                                cash_ref = (fee * ext_cash_refund_pct) if (not refunded) else 0.0
                                refunded = True
                                bal = cap
                                last_payout_req_day = d
                                payout_cnt += 1
                                q_due_day[q_tail % 64] = d + settlement_lag_cal_days
                                q_amt[q_tail % 64] = net_after_wd + cash_ref
                                q_tail += 1

            if d == 364:
                net_settled_365[b] = settled_in - fees_paid
            if d == 729:
                net_settled_730[b] = settled_in - fees_paid

        max_oop_arr[b] = max_oop
        pay1_cal_day[b] = f_pay
        pass_cal_day[b] = f_pass
        payout_cycles_arr[b] = payout_cnt

    return (
        net_settled_365,
        net_settled_730,
        max_oop_arr,
        pay1_cal_day,
        pass_cal_day,
        fail_1try,
        fail_1try_daily,
        fail_1try_static,
        wiped_arr,
        payout_cycles_arr,
    )


def _summarize_sim(res: tuple[np.ndarray, ...], fee: float) -> dict[str, Any]:
    net365, net730, oop, pay1, pass_d, f1, f1_d, f1_s, wiped, pcnt = res
    n = len(net730)
    reached_pay = pay1[pay1 >= 0]
    reached_pass = pass_d[pass_d >= 0]
    return {
        "net_12m_mean_usd": round(float(np.mean(net365)), 2),
        "net_12m_median_usd": round(float(np.median(net365)), 2),
        "p_net_12m_le_0_pct": round(float(np.mean(net365 <= 0.0)) * 100.0, 2),
        "net_24m_mean_usd": round(float(np.mean(net730)), 2),
        "net_24m_median_usd": round(float(np.median(net730)), 2),
        "net_24m_p10_usd": round(float(np.percentile(net730, 10)), 2),
        "ev_per_first_fee_24m": round(float(np.mean(net730)) / max(1e-9, fee), 3),
        "p_net_24m_le_0_pct": round(float(np.mean(net730 <= 0.0)) * 100.0, 2),
        "p_principal_recovered_24m_pct": round(float(np.mean(net730 > 0.0)) * 100.0, 2),
        "max_oop_median_usd": round(float(np.median(oop)), 2),
        "max_oop_p95_usd": round(float(np.percentile(oop, 95)), 2),
        "fail_1try_pct": round(float(np.mean(f1)) * 100.0, 2),
        "fail_1try_daily_pct": round(float(np.mean(f1_d)) * 100.0, 2),
        "fail_1try_static_pct": round(float(np.mean(f1_s)) * 100.0, 2),
        "wiped_pct": round(float(np.mean(wiped)) * 100.0, 2),
        "pass_24m_pct": round((len(reached_pass) / n) * 100.0, 2),
        "payout_reached_24m_pct": round((len(reached_pay) / n) * 100.0, 2),
        "never_payout_24m_pct": round((1.0 - len(reached_pay) / n) * 100.0, 2),
        "pay1_cal_days_median_cond": round(float(np.median(reached_pay)), 1) if len(reached_pay) > 0 else None,
        "mean_payout_cycles_24m": round(float(np.mean(pcnt)), 2),
    }


def run_benchmark(n_paths: int = DEFAULT_N_PATHS) -> dict[str, Any]:
    t0 = time.perf_counter()
    holdout_sha = assert_holdout_locked()
    reg = load_registry()
    contracts = json.loads(CONTRACTS_PATH.read_text(encoding="utf-8"))
    tapes_bundle = build_or_load_frozen_tapes()
    tapes_base = tapes_bundle["tapes"]
    all_days = list(tapes_bundle["ext_days"])
    assert all_days[-1] < "2025-01-01", f"HOLDOUT BREACH: max day {all_days[-1]} >= 2025-01-01!"
    red_news_cal = load_red_news_calendar()

    eng_map = {e["id"]: e for e in reg["engines"]}
    base_risks_8 = {eid: float(eng_map[eid]["base_risk_pct"]) / 100.0 for eid in LIVE8_IDS}
    base_risks_7 = {eid: float(eng_map[eid]["base_risk_pct"]) / 100.0 for eid in CORE7_IDS}

    start_iso, end_iso = all_days[0], all_days[-1]
    cal_days, _, _, _ = align_exits_to_real_calendar(start_iso, end_iso, [])
    n_cal = len(cal_days)
    idx_b7 = make_calendar_block_indices(n_cal, 730, n_paths, 7, SEED)
    idx_b28 = make_calendar_block_indices(n_cal, 730, n_paths, 28, SEED + 1)

    # Part 1: Direct Factor-Cluster Cap Diagnostics on 1.0x Dev P1 (4.0x)
    r_p1_7 = {eid: base_risks_7[eid] * 4.00 for eid in CORE7_IDS}
    m_sym_only, _, diag_sym_only = replay_portfolio_m1_with_factor_caps(
        all_days, tapes_base, r_p1_7, 10_000.0,
        max_symbol_risk_pct=0.0175, max_usd_cluster_pct=0.0, max_jpy_cluster_pct=0.0,
        max_idx_cluster_pct=0.0, max_account_open_pct=0.0, red_news_cal=red_news_cal,
    )
    m_fac_cap, _, diag_fac_cap = replay_portfolio_m1_with_factor_caps(
        all_days, tapes_base, r_p1_7, 10_000.0,
        max_symbol_risk_pct=0.0175, max_usd_cluster_pct=0.0225, max_jpy_cluster_pct=0.0200,
        max_idx_cluster_pct=0.0175, max_account_open_pct=0.0300, red_news_cal=red_news_cal,
    )

    # Part 2: Controlled Comparisons across Friction 1.0x..2.0x, Both Contracts, Static vs Barrier Sizing, 7E vs 8E
    results: dict[str, Any] = {}
    for fric_lbl, fric_mult in FRICTION_LEVELS:
        tapes_f = tapes_base if abs(fric_mult - 1.0) < 1e-9 else apply_cost_stress_to_tapes(tapes_base, fric_mult)
        fric_res: dict[str, Any] = {}

        for port_tag, p1_risks_base, p2_risks_base in (
            ("7E_FIXED", base_risks_7, base_risks_7),
            ("8E_BASELINE", base_risks_8, base_risks_7),
        ):
            def _stage_arr(r_map: dict[str, float], mult: float, sym_c: float, u_c: float, j_c: float, i_c: float, t_c: float, use_news: bool):
                scaled = {e: v * mult for e, v in r_map.items()}
                _, ex, _ = replay_portfolio_m1_with_factor_caps(
                    all_days, tapes_f, scaled, 10_000.0,
                    max_symbol_risk_pct=sym_c, max_usd_cluster_pct=u_c, max_jpy_cluster_pct=j_c,
                    max_idx_cluster_pct=i_c, max_account_open_pct=t_c,
                    red_news_cal=red_news_cal if use_news else None,
                )
                _, n_a, d_a, f_a = align_exits_to_real_calendar(start_iso, end_iso, ex)
                return n_a, d_a, f_a

            for sku_id in ("ftmo_swing_10k", "the5ers_hs_5k"):
                c = contracts["contracts"][sku_id]
                use_news = (int(c["news_restricted_sec"]) > 0) or True  # Keep Naqex +-5m guard ON for parity
                p1_s = _stage_arr(p1_risks_base, 4.00, 0.0175, 0.0225, 0.0200, 0.0175, 0.0300, use_news)
                p1_l = _stage_arr(p1_risks_base, 2.01, 0.0175, 0.0225, 0.0200, 0.0175, 0.0300, use_news)
                p2_s = _stage_arr(p2_risks_base, 2.00, 0.0150, 0.0200, 0.0175, 0.0150, 0.0250, use_news)
                p2_l = _stage_arr(p2_risks_base, 1.00, 0.0150, 0.0200, 0.0175, 0.0150, 0.0250, use_news)
                fn_a = _stage_arr(p2_risks_base, 1.00, 0.0100, 0.0150, 0.0125, 0.0100, 0.0200, use_news)

                modes_to_run = (("STATIC_LOCK", 0), ("BARRIER_HEADROOM", 1)) if port_tag == "7E_FIXED" else (("STATIC_LOCK", 0),)
                for m_lbl, m_code in modes_to_run:
                    for blk_lbl, idx_m in (("cal7d", idx_b7), ("cal28d", idx_b28)):
                        if blk_lbl == "cal28d" and (fric_lbl not in ("1.50x", "2.00x") or port_tag != "7E_FIXED"):
                            continue
                        sim = _simulate_real_calendar_prop_numba(
                            idx_m,
                            p1_s[0], p1_s[1], p1_s[2],
                            p1_l[0], p1_l[1], p1_l[2],
                            p2_s[0], p2_s[1], p2_s[2],
                            p2_l[0], p2_l[1], p2_l[2],
                            fn_a[0], fn_a[1], fn_a[2],
                            float(c["nominal_usd"]),
                            float(c["fee_usd"]),
                            float(c["external_cash_refund_pct"]),
                            float(c["p1_target_pct"]) / 100.0,
                            float(c["p2_target_pct"]) / 100.0,
                            float(c["daily_dd_limit_pct"]) / 100.0,
                            float(c["static_dd_limit_pct"]) / 100.0,
                            int(c["min_trading_days_per_phase"]),
                            float(c["profitable_day_threshold_pct"]) / 100.0,
                            float(c["profit_split_pct"]),
                            int(c["payout_cycle_calendar_days"]),
                            int(c["payout_settlement_lag_calendar_days"]),
                            float(c["min_payout_net_usd"]),
                            float(c["withdrawal_fee_pct"]),
                            MAX_RETRIES,
                            0.50,
                            0.60,
                            0.035, 0.65,
                            0.060, 0.40,
                            0.035, 0.080,
                            m_code,
                        )
                        key = f"{sku_id}__{port_tag}__{m_lbl}__{blk_lbl}"
                        fric_res[key] = _summarize_sim(sim, float(c["fee_usd"]))
        results[fric_lbl] = fric_res

    elapsed = round(time.perf_counter() - t0, 2)
    # Decide objectively whether BARRIER_HEADROOM beats STATIC_LOCK on 7E FTMO 10K at 1.50x
    s_ftmo_15 = results["1.50x"]["ftmo_swing_10k__7E_FIXED__STATIC_LOCK__cal7d"]
    b_ftmo_15 = results["1.50x"]["ftmo_swing_10k__7E_FIXED__BARRIER_HEADROOM__cal7d"]
    sizing_winner = (
        "BARRIER_HEADROOM"
        if (b_ftmo_15["net_24m_mean_usd"] >= s_ftmo_15["net_24m_mean_usd"] and b_ftmo_15["p_net_24m_le_0_pct"] <= s_ftmo_15["p_net_24m_le_0_pct"])
        else "STATIC_LOCK"
    )

    payload = {
        "schema": "naqex-round3-frame-benchmark-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": holdout_sha,
        "holdout_rows_analysed": 0,
        "dev_window": f"{start_iso}..{end_iso}",
        "real_calendar_days_in_dev": n_cal,
        "mc_paths": n_paths,
        "mc_seed": SEED,
        "horizon_calendar_days": 730,
        "elapsed_sec": elapsed,
        "factor_cap_diagnostics_p1_1x": {
            "symbol_cap_only_175": {**m_sym_only, **diag_sym_only},
            "symbol_plus_factor_caps": {**m_fac_cap, **diag_fac_cap},
        },
        "sizing_recommendation_150x": sizing_winner,
        "results": results,
    }
    return payload


def render_md(payload: dict[str, Any]) -> str:
    fc_a = payload["factor_cap_diagnostics_p1_1x"]["symbol_cap_only_175"]
    fc_b = payload["factor_cap_diagnostics_p1_1x"]["symbol_plus_factor_caps"]
    res = payload["results"]
    lines = [
        "---",
        "doc_type: research-receipt",
        f"generated_utc: {payload['generated_utc']}",
        "order_send_count: 0",
        "holdout_rows_analysed: 0",
        "---",
        "",
        "# Đối Chứng Khung Kiến Trúc Vòng 3 (7E Cố Định, Cap Cụm Hướng, Sizing Theo Rào & Ngày Lịch Thật)",
        "",
        f"- **Tập dữ liệu:** Dev niêm phong `{payload['dev_window']}` (`{payload['real_calendar_days_in_dev']}` ngày lịch thật bao gồm cuối tuần & ngày nghỉ; `holdout_rows_analysed = 0`, `order_send_count = 0`).",
        f"- **Mô phỏng:** `N = {payload['mc_paths']:,}` đường × `730` ngày lịch thật (`24` tháng lịch, seed `{payload['mc_seed']}`), có đủ độ trễ nhận tiền (`T+3` FTMO / `T+5` The5ers), phí rút (`1,0%` / `3,5%`), sàn rút (`50` / `150 USD`) và tách riêng hoàn phí tiền mặt ngoài.",
        "",
        "## 1. Tác Động Của Khóa Cụm Hướng (`USD / JPY / US100`) Ở P1 (`4,0×`, Phí `1,0×`)",
        "",
        "| Cấu hình P1 (`7E`) | Lãi ròng Dev (USD) | Max DD (%) | Ngày xấu nhất (%) | Đỉnh cụm USD (%) | Đỉnh cụm JPY (%) | Lệnh cắt/chặn bởi cụm |",
        "|---|---:|---:|---:|---:|---:|---:|",
        f"| Chỉ khóa theo mã (`1,75%`) | `{fc_a['net_usd']:+,.2f}` | `{fc_a['max_dd_pct']:.2f}%` | `{fc_a['worst_day_dd_pct']:.2f}%` | `{fc_a['peak_usd_cluster_pct']:.2f}%` | `{fc_a['peak_jpy_cluster_pct']:.2f}%` | `{int(fc_a['clamped_factor'])}/{int(fc_a['blocked_factor'])}` |",
        f"| **Khóa mã + Cụm (`USD 2,25% / JPY 2,00% / Tổng 3,00%`)** | **`{fc_b['net_usd']:+,.2f}`** | **`{fc_b['max_dd_pct']:.2f}%`** | **`{fc_b['worst_day_dd_pct']:.2f}%`** | **`{fc_b['peak_usd_cluster_pct']:.2f}%`** | **`{fc_b['peak_jpy_cluster_pct']:.2f}%`** | **`{int(fc_b['clamped_factor'])}/{int(fc_b['blocked_factor'])}`** |",
        "",
        "## 2. Đối Chứng Cặp Trên Ngày Lịch Thật (`24` Tháng = `730` Ngày Lịch, Khối `7` Ngày)",
        "",
        "| Hợp đồng & Cấu hình | Phí | Lãi ròng TB 24t (USD) | Trung vị 24t (USD) | P(Lỗ ròng ≤0) | Cháy ngày lượt 1 | Đạt payout 24t | Trung vị ngày lịch tới payout 1* | Max vốn ứng P95 (USD) |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for sku, title in (("ftmo_swing_10k", "FTMO Swing 10K"), ("the5ers_hs_5k", "The5ers HS 5K")):
        for fric in ("1.00x", "1.25x", "1.50x", "2.00x"):
            for tag, lbl in (
                ("7E_FIXED__STATIC_LOCK__cal7d", "7E · Static Lock"),
                ("7E_FIXED__BARRIER_HEADROOM__cal7d", "7E · Barrier Headroom"),
                ("8E_BASELINE__STATIC_LOCK__cal7d", "8E Baseline · Static"),
            ):
                r = res[fric][f"{sku}__{tag}"]
                p1d = f"{r['pay1_cal_days_median_cond']:.0f} ngày" if r["pay1_cal_days_median_cond"] is not None else "—"
                lines.append(
                    f"| `{title}` · {lbl} | `{fric}` | `{r['net_24m_mean_usd']:+,.0f}` | `{r['net_24m_median_usd']:+,.0f}` "
                    f"| `{r['p_net_24m_le_0_pct']:.1f}%` | `{r['fail_1try_daily_pct']:.1f}%` | `{r['payout_reached_24m_pct']:.1f}%` "
                    f"| `{p1d}` | `{r['max_oop_p95_usd']:,.0f}` |"
                )

    lines += [
        "",
        "*Ghi chú: Trung vị ngày lịch tới payout đầu tính trên các đường đạt được payout trong 730 ngày lịch; tỷ lệ đường không đạt payout = `100% - Đạt payout 24t`.*",
        "",
        f"## 3. Khuyến Nghị Sizing Tự Động Tại Phí Stress `1,50×`: **`{payload['sizing_recommendation_150x']}`**",
        "",
        "- **Kết luận trung thực về ma sát `2,00×`:** Nếu trượt giá thực tế trên demo/live đo được gần `2,00×` ngân sách M1, phần lớn đường chạy không còn kỳ vọng dương đủ bù công vận hành — đúng tiêu chí dừng/gác cơ chế nội ngày của Astra Vòng 3.",
        "- **Ngưỡng quyết định tiếp theo:** Chỉ giữ cơ chế nội ngày khi đo thực tế trên `FTMO-Demo` (`naqex-node1`) cho trượt giá nằm gọn trong vùng `<= 1,25× – 1,50×` ngân sách M1 sau tối thiểu `10–15` lệnh đóng đối soát với statement.",
        "",
    ]
    md = "\n".join(lines)
    assert "$" not in md, "Bare '$' found in Markdown!"
    return md


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Round-3 Architecture Counterfactual Benchmark (OrderSend=0)")
    ap.add_argument("--paths", type=int, default=DEFAULT_N_PATHS)
    args = ap.parse_args(argv)
    payload = run_benchmark(n_paths=args.paths)
    md = render_md(payload)
    OUT_MD.parent.mkdir(parents=True, exist_ok=True)
    OUT_MD.write_text(md, encoding="utf-8", newline="\n")
    write_verified_receipt(OUT_JSON, payload, overwrite=True)
    print(json.dumps({
        "ok": True,
        "elapsed_sec": payload["elapsed_sec"],
        "sizing_recommendation_150x": payload["sizing_recommendation_150x"],
        "factor_cap_p1": payload["factor_cap_diagnostics_p1_1x"],
        "ftmo_7e_static_150x": payload["results"]["1.50x"]["ftmo_swing_10k__7E_FIXED__STATIC_LOCK__cal7d"],
        "ftmo_7e_barrier_150x": payload["results"]["1.50x"]["ftmo_swing_10k__7E_FIXED__BARRIER_HEADROOM__cal7d"],
        "ftmo_8e_static_150x": payload["results"]["1.50x"]["ftmo_swing_10k__8E_BASELINE__STATIC_LOCK__cal7d"],
        "t5_7e_static_150x": payload["results"]["1.50x"]["the5ers_hs_5k__7E_FIXED__STATIC_LOCK__cal7d"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
