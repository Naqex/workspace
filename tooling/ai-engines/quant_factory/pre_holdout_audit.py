"""Quant Factory Parity Benchmark & Quantitative Pre-Holdout Blind-Spot Audit (2018-2024 ONLY; holdout_rows = 0).

Runs strictly on sealed Development data (< 2025-01-01T00:00:00Z):
  1. Warms & benchmarks zero-pickle .npz derived tape cache (cold vs warm load).
  2. Verifies 1:1 parity against frozen Pass 28 M1 floating-equity metrics (PORT_7E Calmar 1.21, PORT_9E Calmar 1.39).
  3. Benchmarks Numba JIT 2,000-path lifecycle speed vs declarative JSON firm/profile configs.
  4. Audits statistical pre-holdout blind spots:
     - Cumulative Deflated Sharpe Ratio (DSR / PSR) across M = 1, 40, 250, 600 trials
     - Worst-5% tail correlation across all 9 engines
     - Year-by-year decay / regime stability (2018-2024)
     - FTMO 1% "trade-idea bundle" per-symbol concurrent risk cap impact (None vs 1.25% vs 1.00%)
     - Combined Red-News ±5m + Per-Symbol Cap production stress test
     - Causal Inverse-DD (Cluster A) + Vol-Targeting 20d (Moreira & Muir) full lifecycle comparison
     - Weekend / rollover swap=0 boundary invariant verification
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AI_ENGINES))

import pass23_ftmo_lifecycle_sim as p23l
from native_ftmo_monfri_seal import ROOT
from quant_factory.data_store import (
    build_or_load_frozen_tapes,
    load_firm_config,
    load_profile_config,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.eval_pipeline import deflated_sharpe_ratio, tail_correlation_report
from quant_factory.prop_engine import (
    apply_vol_targeting_causal,
    compute_cluster_a_invdd_weights,
    evaluate_firm_profile,
    make_block_bootstrap_indices,
    replay_portfolio_m1,
)
from quant_factory.report_gen import write_verified_receipt


def _exits_to_daily_arrays(ext_days: list[str], exits: list[dict], initial: float = 10000.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    by_day = {e["day"]: e for e in exits}
    n = len(ext_days)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    flg = np.zeros(n, dtype=np.int8)
    prev_cash = initial
    for i, dk in enumerate(ext_days):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            start_eq = prev_cash
            dds[i] = max(0.0, start_eq - float(e["day_equity_minimum"]))
            flg[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, flg


def _calmar_from_daily(nets: np.ndarray, dds: np.ndarray, initial: float = 10000.0, years: float = 7.0) -> dict:
    eq = initial
    peak = initial
    max_dd = 0.0
    max_daily = 0.0
    uw_days = 0
    max_uw = 0
    for n, d in zip(nets, dds):
        max_daily = max(max_daily, float(d))
        max_dd = max(max_dd, peak - (eq - float(d)))
        eq += float(n)
        if eq >= peak:
            peak = eq
            uw_days = 0
        else:
            uw_days += 1
            max_uw = max(max_uw, uw_days)
    ann_pct = 100.0 * ((eq - initial) / years) / initial
    dd_pct = 100.0 * max_dd / initial
    return {
        "ann_pct": round(ann_pct, 2),
        "peak_dd_pct": round(dd_pct, 2),
        "daily_dd_pct": round(100.0 * max_daily / initial, 2),
        "calmar": round(ann_pct / dd_pct, 2) if dd_pct > 1e-9 else 0.0,
        "uw_months": round(max_uw / 21.0, 1),
    }


def main() -> int:
    t_all = time.perf_counter()
    reg = load_registry()
    cal = load_red_news_calendar()

    # 1. Cold rebuild + warm cache benchmark
    cold = build_or_load_frozen_tapes(force_rebuild=True)
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    assert warm["cache_hit"] is True
    tapes = warm["tapes"]
    ext_days = warm["ext_days"]
    strict_a_days = warm["strict_cluster_a_days"]

    base_risks_map = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    turbo9 = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    risks7 = {k: base_risks_map[k] for k in core7}
    risks9 = {k: base_risks_map[k] for k in turbo9}

    # 2. Exact Pass 28 M1 Parity Check (Swing profile matches frozen Pass 28 baseline)
    met7, ex7 = replay_portfolio_m1(ext_days, tapes, risks7, 10000.0, profile_mode="Swing")
    met9, ex9 = replay_portfolio_m1(ext_days, tapes, risks9, 10000.0, profile_mode="Swing")

    # 3. Weekend / Rollover swap=0 invariant audit across all 9 engines
    weekend_violations = 0
    post_21utc_exits = 0
    max_trade_day = ""
    for eng, day_map in tapes.items():
        for dk, (row, stamps, _marks) in day_map.items():
            if dk > max_trade_day:
                max_trade_day = dk
            if dk >= "2025-01-01":
                raise AssertionError(f"HOLDOUT_LEAK: {eng} {dk}")
            dt_end = datetime.fromtimestamp(int(stamps[-1]), timezone.utc)
            if dt_end.weekday() >= 5:
                weekend_violations += 1
            if dt_end.hour >= 21 and dt_end.minute > 0:
                post_21utc_exits += 1

    # 4. Build per-engine daily matrix for Tail Correlation & DSR
    eng_mat = np.zeros((len(ext_days), len(turbo9)), dtype=np.float64)
    day_idx = {d: i for i, d in enumerate(ext_days)}
    for j, eng in enumerate(turbo9):
        _, ex_e = replay_portfolio_m1(ext_days, tapes, {eng: base_risks_map[eng]}, 10000.0)
        for e in ex_e:
            eng_mat[day_idx[e["day"]], j] = float(e["net_usd"]) / 10000.0

    nets7, dds7, flg7 = _exits_to_daily_arrays(ext_days, ex7)
    nets9, dds9, flg9 = _exits_to_daily_arrays(ext_days, ex9)
    b_mask = np.array([d >= "2021-01-01" for d in ext_days])

    dsr_audit = {}
    for label, arr in (
        ("PORT_7E_ALL", nets7 / 10000.0),
        ("PORT_7E_BLIND_B", nets7[b_mask] / 10000.0),
        ("PORT_9E_ALL", nets9 / 10000.0),
        ("PORT_9E_BLIND_B", nets9[b_mask] / 10000.0),
    ):
        dsr_audit[label] = {f"M_{m}": deflated_sharpe_ratio(arr, n_trials=m) for m in (1, 40, 250, 600)}

    tail_corr_9e = tail_correlation_report(eng_mat, turbo9, tail_pct=0.05)
    tail_corr_7e = tail_correlation_report(eng_mat[:, :7], core7, tail_pct=0.05)

    # 5. Per-symbol concurrent risk cap stress test (FTMO 1% Funded trade-idea cap + 2% P1 cap)
    sym_cap_tests = {}
    for label, rmap, cap_val, rn_cal in (
        ("PORT_9E_1X_UNCAP", risks9, None, None),
        ("PORT_9E_1X_SYMCAP_100", risks9, 0.0100, None),
        ("PORT_9E_1X_SYMCAP_100_REDNEWS", risks9, 0.0100, cal),
        ("PORT_7E_1X_UNCAP", risks7, None, None),
        ("PORT_7E_1X_SYMCAP_100", risks7, 0.0100, None),
        ("PORT_7E_1X_SYMCAP_100_REDNEWS", risks7, 0.0100, cal),
        ("PORT_9E_25X_UNCAP", {k: v * 2.5 for k, v in risks9.items()}, None, None),
        ("PORT_9E_25X_SYMCAP_200", {k: v * 2.5 for k, v in risks9.items()}, 0.0200, None),
        ("PORT_9E_25X_SYMCAP_150", {k: v * 2.5 for k, v in risks9.items()}, 0.0150, None),
    ):
        m, _ = replay_portfolio_m1(ext_days, tapes, rmap, 10000.0, profile_mode="Swing", max_symbol_concurrent_risk=cap_val, red_news_cal=rn_cal)
        sym_cap_tests[label] = {
            "ann_pct": m["ann_pct"]["all"],
            "ann_A": m["ann_pct"]["A"],
            "ann_B": m["ann_pct"]["B"],
            "peak_dd_pct": m["peak_dd_pct"],
            "daily_loss_pct": m["daily_loss_pct"],
            "calmar": m["calmar"],
            "uw_months": m["underwater_months"],
            "sym_cap_hits": m["sym_cap_hits"],
        }

    # 6. Causal Cluster-A Inverse-DD + Downside Vol Brake vs Symmetric Vol-Targeting 20d
    tot_budget_9 = sum(risks9.values())
    invdd_w9 = compute_cluster_a_invdd_weights(strict_a_days, tapes, turbo9, tot_budget_9)
    met9_invdd, ex9_invdd = replay_portfolio_m1(ext_days, tapes, invdd_w9, 10000.0, profile_mode="Swing")
    nets9_id, dds9_id, flg9_id = _exits_to_daily_arrays(ext_days, ex9_invdd)
    nets9_vt_sym, dds9_vt_sym = apply_vol_targeting_causal(ext_days, nets9_id, dds9_id, window=20, lo=0.55, hi=1.35)
    nets9_vt_brk, dds9_vt_brk = apply_vol_targeting_causal(ext_days, nets9_id, dds9_id, window=20, lo=0.55, hi=1.00)

    invdd_vt_summary = {
        "cluster_a_weights_pct": {k: round(v * 100.0, 3) for k, v in invdd_w9.items()},
        "raw_9e_all": _calmar_from_daily(nets9, dds9, years=7.0),
        "raw_9e_blind_b": _calmar_from_daily(nets9[b_mask], dds9[b_mask], years=4.0),
        "invdd_9e_all": _calmar_from_daily(nets9_id, dds9_id, years=7.0),
        "invdd_9e_blind_b": _calmar_from_daily(nets9_id[b_mask], dds9_id[b_mask], years=4.0),
        "invdd_vt_brake_hi100_all": _calmar_from_daily(nets9_vt_brk, dds9_vt_brk, years=7.0),
        "invdd_vt_brake_hi100_blind_b": _calmar_from_daily(nets9_vt_brk[b_mask], dds9_vt_brk[b_mask], years=4.0),
        "invdd_vt_sym_hi135_all": _calmar_from_daily(nets9_vt_sym, dds9_vt_sym, years=7.0),
        "invdd_vt_sym_hi135_blind_b": _calmar_from_daily(nets9_vt_sym[b_mask], dds9_vt_sym[b_mask], years=4.0),
    }

    # 7. Numba JIT Lifecycle Benchmark across 4 Firms x 3 Profiles (N = 2,000 x 504 days)
    idx_mat = make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=2000, block_len=5, seed=20261123)
    firms = [load_firm_config(f) for f in ("ftmo_swing_10k", "ftmo_standard_10k", "the5ers_high_stakes_5k", "the5ers_hyper_growth_5k")]
    profs = [load_profile_config(p) for p in ("p1_sprint_25x", "p1_sprint_30x", "p1_smooth_invdd_vt")]

    # Warm JIT once, then time all 12 full 2,000-path evaluations!
    _ = evaluate_firm_profile(idx_mat, (nets9, dds9, flg9), (nets7, dds7, flg7), firms[0], profs[0])
    t_jit0 = time.perf_counter()
    lifecycle_matrix = []
    for fcfg in firms:
        for pcfg in profs:
            if pcfg.get("allocation_mode") == "inverse_dd_a":
                p1_ser = (nets9_vt_brk, dds9_vt_brk, flg9_id) if pcfg.get("vol_target_20d") else (nets9_id, dds9_id, flg9_id)
            else:
                p1_ser = (nets9, dds9, flg9)
            res = evaluate_firm_profile(idx_mat, p1_ser, (nets7, dds7, flg7), fcfg, pcfg)
            lifecycle_matrix.append(res)
    jit_12_sec = round(time.perf_counter() - t_jit0, 4)

    # Yearly decay linear slope on PORT_9E & PORT_7E
    yrs = [int(y) for y in sorted(met9["years_pct"].keys())]
    y9 = np.array([met9["years_pct"][str(y)] for y in yrs], dtype=np.float64)
    y7 = np.array([met7["years_pct"][str(y)] for y in yrs], dtype=np.float64)
    slope9 = round(float(np.polyfit(np.arange(len(yrs)), y9, 1)[0]), 3)
    slope7 = round(float(np.polyfit(np.arange(len(yrs)), y7, 1)[0]), 3)

    report = {
        "schema": "naqex-pre-holdout-audit-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": warm["holdout_lock_sha256"],
        "holdout_rows_analysed": 0,
        "max_trade_day": max_trade_day,
        "order_send_count": 0,
        "benchmarks": {
            "cold_tape_build_sec": cold["load_seconds"],
            "warm_npz_tape_load_sec": warm["load_seconds"],
            "tape_speedup_x": round(cold["load_seconds"] / max(1e-4, warm["load_seconds"]), 1),
            "numba_12x2000_lifecycle_sec": jit_12_sec,
            "numba_per_2000_paths_ms": round(1000.0 * jit_12_sec / 12.0, 2),
            "total_audit_sec": round(time.perf_counter() - t_all, 2),
        },
        "pass28_parity": {
            "PORT_7E_P28_CORE": {k: met7[k] for k in ("ann_pct", "peak_dd_pct", "daily_loss_pct", "calmar", "underwater_months", "margin_failures", "years_pct")},
            "PORT_9E_P28_TURBO": {k: met9[k] for k in ("ann_pct", "peak_dd_pct", "daily_loss_pct", "calmar", "underwater_months", "margin_failures", "years_pct")},
            "parity_match_p28": (
                abs(met7["ann_pct"]["all"] - 7.73) <= 0.01
                and abs(met7["peak_dd_pct"] - 6.36) <= 0.01
                and abs(met9["ann_pct"]["all"] - 8.83) <= 0.01
                and abs(met9["peak_dd_pct"] - 6.37) <= 0.01
            ),
        },
        "swap0_and_boundary_invariants": {
            "weekend_violations": weekend_violations,
            "post_21utc_exits": post_21utc_exits,
            "max_trade_day": max_trade_day,
        },
        "yearly_trend_pct_per_year_slope": {"PORT_7E": slope7, "PORT_9E": slope9},
        "dsr_multiple_testing": dsr_audit,
        "tail_correlation": {"PORT_7E": tail_corr_7e, "PORT_9E": tail_corr_9e},
        "per_symbol_risk_cap_stress": sym_cap_tests,
        "invdd_vol_targeting": invdd_vt_summary,
        "lifecycle_matrix": lifecycle_matrix,
    }

    out_path = ROOT / "planning/research/PRE-HOLDOUT-BLINDSPOT-AUDIT-20261123.json"
    digest = write_verified_receipt(out_path, report, overwrite=True)
    print(json.dumps({
        "receipt_sha256": digest[:16],
        "benchmarks": report["benchmarks"],
        "parity_match_p28": report["pass28_parity"]["parity_match_p28"],
        "PORT_7E": report["pass28_parity"]["PORT_7E_P28_CORE"],
        "PORT_9E": report["pass28_parity"]["PORT_9E_P28_TURBO"],
        "swap0": report["swap0_and_boundary_invariants"],
        "yearly_slope": report["yearly_trend_pct_per_year_slope"],
        "dsr": report["dsr_multiple_testing"],
        "tail_corr": report["tail_correlation"],
        "sym_cap": report["per_symbol_risk_cap_stress"],
        "invdd_vt": report["invdd_vol_targeting"],
        "lifecycle": report["lifecycle_matrix"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
