"""Wave 3A (`w4-p3-council`) Master Council Unit, Tamper, Safety, and Local SSOT Tests.

Covers:
  - Offline CI-safe (`-m "not local_cache"`) tests (100% synthetic, zero `.runtime/` dependency):
      1. Static AST audit: ZERO bare `assert`s, ZERO `subprocess` calls, ZERO forbidden imports,
         exact safety constants and 40-artifact registry completeness.
      2. Full 40-artifact synthetic reconciliation + `wave4_master_metrics.json` canonical
         `report_sha256` round-trip + 1-byte tamper detection (active under `python -O`).
      3. Fail-closed missing receipt (`MissingArtifactError`) and malformed JSON (`MalformedArtifactError`).
      4. Fail-closed tampered self-hash, tampered cross-artifact SHA-256 link, and tampered pinned file SHA-256.
      5. Fail-closed safety violations (`holdout_rows_analysed > 0`, `holdout_cutoff_date >= 2025`,
         `order_send_count > 0`, `order_send_capable = True`, `spend_vnd > 0`, stripped required invariant key).
      6. Fail-closed Pareto arithmetic drift (`pass + fail + pending != 100%` at `1.0x` or `1.5x`,
         and summary-vs-81case median mismatch).
  - Local artifact `@pytest.mark.local_cache` verification:
      7. Independent verification of `.runtime/offensive4/wave4_master_metrics.json` against ALL 40 raw
         artifacts on disk (exact SHA-256 match, Holdout=0 / OrderSend=0 / Spend=0, 4-tier scorecard,
         9-tier Pareto table + 81 pointers + 100% partitions, and byte-identical council receipts).

All checks use `_check(...)` so every assertion stays active under `python -O`.
"""

from __future__ import annotations

import ast
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory.wave4 import wave4_master_council as council  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` stripping."""
    if not cond:
        raise AssertionError(msg)


def _write_json(path: Path, doc: dict[str, Any], *, self_hash: bool = False) -> tuple[str, dict[str, Any]]:
    payload = dict(doc)
    if self_hash:
        payload["report_sha256"] = council.compute_canonical_report_sha256(payload)
    file_sha, _nbytes = council.write_json_lf(path, payload)
    return file_sha, payload


def _make_partition_5(pass_pct: float = 70.0, fail_pct: float = 0.5) -> dict[str, dict[str, float]]:
    pending = round(100.0 - pass_pct - fail_pct, 2)
    return {
        h: {"pass_pct": pass_pct, "fail_pct": fail_pct, "pending_pct": pending, "sum_pct": 100.0}
        for h in council.PARETO_HORIZONS
    }


def _make_partition_4(pass_pct: float = 45.0, fail_pct: float = 50.0) -> dict[str, dict[str, float]]:
    pending = round(100.0 - pass_pct - fail_pct, 2)
    return {
        h: {"pass_pct": pass_pct, "fail_pct": fail_pct, "pending_pct": pending, "sum_pct": 100.0}
        for h in council.CME_HORIZONS
    }


def _make_synthetic_pareto_case(
    tier_m: int,
    mode: str,
    policy: str,
    *,
    friction_mult: float,
    usd_vnd: float = 25765.94,
) -> dict[str, Any]:
    cid = f"B{tier_m}M__{mode}__{policy}"
    med_36_vnd = float(tier_m * 1_000_000 * (2.5 if friction_mult == 1.0 else 0.4))
    med_24_vnd = round(med_36_vnd * 0.45, 2)
    return {
        "case_id": cid,
        "bankroll_m_vnd": tier_m,
        "bankroll_vnd": tier_m * 1_000_000,
        "bankroll_usd": round((tier_m * 1_000_000) / usd_vnd, 2),
        "concurrency_mode": mode,
        "allocation_policy": policy,
        "is_pareto_in_tier": policy == "P1_RECOUP_FIRST",
        "is_pareto_overall": tier_m == 500 and mode == "AGGRESSIVE_PARALLEL",
        "resolution_label_vi": "XẤP XỈ CẤP NGÀY",
        "resolution_tag": "APPROX_DAILY_RESOLUTION",
        "evidence_stage": "BACKTEST_DEV_SEALED_LE_2024",
        "execution_status": "MEASURED_DEMO_EXECUTION",
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "net_profit_24m_usd": {
            "mean": round(med_24_vnd / usd_vnd * 1.2, 2),
            "median": round(med_24_vnd / usd_vnd, 2),
            "p10": -100.0,
            "p90": round(med_24_vnd / usd_vnd * 3.0, 2),
        },
        "net_profit_24m_vnd": {
            "mean": round(med_24_vnd * 1.2, 2),
            "median": med_24_vnd,
            "p10": -2_576_594.0,
            "p90": round(med_24_vnd * 3.0, 2),
        },
        "net_profit_36m_usd": {
            "mean": round(med_36_vnd / usd_vnd * 1.2, 2),
            "median": round(med_36_vnd / usd_vnd, 2),
            "p10": -100.0,
            "p90": round(med_36_vnd / usd_vnd * 3.0, 2),
        },
        "net_profit_36m_vnd": {
            "mean": round(med_36_vnd * 1.2, 2),
            "median": med_36_vnd,
            "p10": -2_576_594.0,
            "p90": round(med_36_vnd * 3.0, 2),
        },
        "p_net_le_0_24m_pct": 35.0 if friction_mult == 1.0 else 55.0,
        "p_net_le_0_36m_pct": 22.0 if friction_mult == 1.0 else 46.0,
        "p_bankroll_ruin_24m_pct": 0.05,
        "p_bankroll_ruin_pct": 0.15 if friction_mult == 1.0 else 0.45,
        "ev_per_1_vnd_fee_24m": 3.5 if friction_mult == 1.0 else 1.5,
        "ev_per_1_vnd_fee_36m": 6.0 if friction_mult == 1.0 else 2.5,
        "mean_total_fees_36m_usd": 500.0,
        "mean_total_fees_36m_vnd": 12_882_970.0,
        "uncond_med_pay1_cal_days_cap365": 365.0,
        "uncond_med_pay1_cal_days_cap730": 410.0 if friction_mult == 1.0 else 700.0,
        "cond_med_pay1_cal_days": 295.0,
        "funded_12m_blowup": {
            "blowup_12m_pct": 0.25 if friction_mult == 1.0 else 0.55,
            "wilson_95_ub_pct": 0.40 if friction_mult == 1.0 else 0.75,
        },
        "bot_auto_kill_pct": 85.0,
        "firm_hard_breach_pct": 20.0,
        "funded_dry_months_pct": 58.0,
        "longest_starved_month_streak_p50": 7,
        "longest_starved_month_streak_p95": 20,
        "mean_own_book_36m_usd": 5000.0,
        "mean_max_base_funded_usd": 100000.0,
        "monthly_pass_fail_pending": _make_partition_5(75.0 if friction_mult == 1.0 else 55.0, 0.2),
        "friction_mult": friction_mult,
    }


def _build_synthetic_40_workspace(tmp_path: Path) -> Path:
    """Create a complete, internally consistent 40-artifact synthetic Wave 4 workspace."""
    root = tmp_path / "ws"
    spec_map = {s.artifact_id: s for s in council.RAW_ARTIFACT_SPECS}

    def put(aid: str, doc: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        sp = spec_map[aid]
        return _write_json(root / sp.rel_path, doc, self_hash=sp.self_hashed)

    inv_base = {
        "order_send_capable": False,
        "order_send_count": 0,
        "spend_vnd": 0,
        "holdout_cutoff_date": "2024-12-31",
        "holdout_2025_plus_sealed": True,
        "holdout_rows_analysed": 0,
    }
    inv_no_spend = {k: v for k, v in inv_base.items() if k != "spend_vnd"}

    # 1-3. Wave 0A/0B/0C
    put(
        "w4_t0_env_receipt",
        {
            "schema": "naqex-wave4-t0-env-receipt-v1",
            "worker": "w4-t0-env",
            "hard_invariants": dict(inv_base),
            "ml_onnx_environment": {"audited_wheel_count": 31, "copyleft_gpl_lgpl_agpl_count": 0},
            "wave0a_barrier_status": "GREEN_READY_FOR_WAVE_0B",
        },
    )
    put(
        "w4_t0_debt_receipt",
        {
            "schema": "naqex-wave4-t0-debt-receipt-v1",
            "worker": "w4-t0-debt",
            "hard_invariants": dict(inv_base),
            "deliverables": {"item_1_create_no_window_popup_fix": {"status": "PASS", "calls_fixed": 9}},
            "report_sha256": "0" * 64,
        },
    )
    put(
        "w4_t0_ftmo_m1_receipt",
        {
            "schema": "naqex-wave4-t0-ftmo-m1-receipt-v1",
            "worker": "w4-t0-ftmo-m1",
            "status": "PASS_GREEN",
            "hard_invariants": dict(inv_base),
            "export_summary": {"symbol_count": 8, "total_rows": 22_274_151},
        },
    )
    put(
        "w4_t0_parity98_receipt",
        {
            "schema": "naqex-wave4-same-feed-mt5-parity98-receipt-v1",
            "worker": "w4-t0-parity98",
            "w4_g03_verdict": "PASS_SAME_FEED_FORMULA_PARITY_100PCT",
            "safety_invariants": dict(inv_base),
            "headline_summary": {
                "model1_aggregate_trade_match_rate": 1.0,
                "model1_total_matched_trades_60s": 3320,
                "model1_total_expected_trades": 3320,
                "model1_total_ghost_trades": 0,
                "model1_total_missed_trades": 0,
                "model1_gross_r_drift_range": [0.01268, 0.016786],
            },
            "offensive3_before_vs_wave4_after": {
                "Funded_1x_10K_2024_M1": {
                    "before_offensive3_cross_feed": {"trade_match_rate": 0.738386, "ghost_trades": 167}
                },
                "Sprint_Eval_10K_2024_M1": {
                    "before_offensive3_cross_feed": {"trade_match_rate": 0.744417, "ghost_trades": 171}
                },
                "Funded_1x_10K_2024Q4_M4_microstructure_separate": {
                    "after_wave4_same_feed_m1_vs_m4": {"trade_match_rate": 0.954839}
                },
            },
        },
    )
    put(
        "w4_t0_milestones_receipt",
        {
            "schema": "naqex-wave4-t0-milestones-receipt-v1",
            "worker": "w4-t0-milestones",
            "hard_invariants": dict(inv_base),
            "deliverables": {
                "milestone_01_12_preregister_holdout_v2_verify": {"verified_artifacts": 8},
                "milestone_04_12_and_10_12_nfp_cpi_quote_collector_preflight": {"ntp_offset_ms": 85.78},
                "milestone_08_12_free_trial_readonly_harvester": {"offline_fixture_smoke": {"trade_match_rate": 1.0}},
            },
        },
    )

    # 4. Mui 1: ML
    _, ml_doc = put(
        "wave4_ml_arena_summary",
        {
            "schema_version": "naqex-wave4-ml-arena-5families-v1",
            "w4_g04_status": "PASS",
            "verdict": "PROMOTE_V104_ML",
            "hard_invariants": dict(inv_base),
            "budget": {"recorded_trials": 36, "max_trials": 48, "promoted_trials": 2},
            "baseline_v103": {
                "full_oof": {
                    "n_oof_trades": 2799,
                    "economics_1x": {
                        "win_rate": 0.4912,
                        "ev_r": 0.0546,
                        "profit_factor": 1.1666,
                        "max_dd_pct": 5.80,
                    },
                    "slippage_breakeven_24m": 1.643,
                }
            },
            "best_overall_trial": {
                "trial_id": "w4_22_gmm_tf_k2_a15",
                "family_name": "regime_gmm_jump",
                "brier_skill_score": 0.004454,
                "roc_auc": 0.541643,
                "pf_1x": 1.252397,
                "ev_r_1x": 0.073729,
                "max_dd_pct_1x": 6.345779,
                "slippage_breakeven_24m": 1.764805,
            },
            "family_leaderboard": {
                "lightgbm": {
                    "n_trials_run": 7,
                    "n_trials_promoted": 1,
                    "best_trial_id": "w4_09_lgbm_tf_d2_n60",
                    "brier_skill_score": 0.00204,
                    "roc_auc": 0.535361,
                    "pf_1x": 1.207158,
                    "ev_r_1x": 0.060975,
                    "max_dd_pct_1x": 5.707296,
                    "slippage_breakeven_24m": 1.777636,
                    "verdict": "PROMOTE_V104_ML",
                },
                "regime_gmm_jump": {
                    "n_trials_run": 7,
                    "n_trials_promoted": 1,
                    "best_trial_id": "w4_22_gmm_tf_k2_a15",
                    "brier_skill_score": 0.004454,
                    "roc_auc": 0.541643,
                    "pf_1x": 1.252397,
                    "ev_r_1x": 0.073729,
                    "max_dd_pct_1x": 6.345779,
                    "slippage_breakeven_24m": 1.764805,
                    "verdict": "PROMOTE_V104_ML",
                },
            },
        },
    )
    put(
        "w4_m1_feat_receipt",
        {
            "schema": "naqex-wave4-m1-feat-receipt-v1",
            "worker": "w4-m1-feat",
            "hard_invariants": dict(inv_base),
            "feature_count": 24,
            "causality_proof": {"bit_exact_zero_drift": True},
        },
    )
    put(
        "w4_m1_cv_receipt",
        {
            "schema": "naqex-wave4-m1-cv-receipt-v1",
            "worker": "w4-m1-cv",
            "hard_invariants": dict(inv_base),
            "splitter_verification": {"n_splits": 5, "purge_days": 5, "embargo_days": 10},
        },
    )
    put(
        "w4_m1_arena_receipt",
        {
            "schema": "naqex-wave4-m1-arena-receipt-v1",
            "worker": "w4-m1-arena",
            "w4_g04_status": "PASS",
            "hard_invariants": dict(inv_base),
            "deliverables": {"report_sha256": ml_doc["report_sha256"]},
            "test_results": {"forensic_adversarial_diagnostics": {"honest_caveats": ["Dev <= 2024-12-31 only."]}},
        },
    )
    put(
        "w4_m1_onnx_mq5_receipt",
        {
            "schema": "naqex-wave4-m1-onnx-mq5-receipt-v1",
            "worker": "w4-m1-onnx-mq5",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
        },
    )
    put(
        "w4_m1_mt5_onnx_receipt",
        {
            "schema": "naqex-wave4-m1-mt5-onnx-cert-receipt-v1",
            "worker": "w4-m1-mt5-onnx",
            "status": "PASS",
            "w4_g05_verdict": "CERTIFIED_PASS_ONNX_PARITY_AND_FULL2024_ABLATION",
            "hard_invariants": dict(inv_base),
            "independent_parity_500": {
                "four_way_parity_500": {
                    "overall_max_abs_err": 7.28e-8,
                    "all_decision_agreements_100pct": True,
                }
            },
            "full2024_mt5_ablation": {
                "baseline_v103_funded_1x": {
                    "metrics": {
                        "trades": 469,
                        "win_rate_pct": 50.11,
                        "net_pnl_usd": 616.87,
                        "profit_factor": 1.15,
                        "balance_dd_pct": 3.46,
                        "equity_dd_pct": 4.09,
                        "worst_day_pct": 1.4812,
                        "swap_total_usd": 0.0,
                    }
                },
                "v104_ml_onnx": {
                    "metrics": {
                        "trades": 347,
                        "win_rate_pct": 51.87,
                        "net_pnl_usd": 639.18,
                        "profit_factor": 1.21,
                        "balance_dd_pct": 2.54,
                        "equity_dd_pct": 4.21,
                        "swap_total_usd": 0.0,
                    }
                },
                "v104_ml_pure_mql5": {"metrics": {"net_pnl_usd": 639.18}},
                "v104_ml_disabled": {"metrics": {"net_pnl_usd": 616.87}},
                "comparisons": {
                    "v104_ml_onnx_vs_v103_baseline": {"filtered_trades_count": 122, "delta_net_pnl_usd": 22.31},
                    "v104_ml_pure_mql5_vs_v104_ml_onnx": {"exact_match": True},
                    "v104_ml_disabled_vs_v103_baseline": {"exact_reproduction": True},
                },
            },
        },
    )

    # 5. Mui 2A: Pareto 81-cases + summary
    cases_base = [
        _make_synthetic_pareto_case(t, m, p, friction_mult=1.0)
        for t in council.EXPECTED_BANKROLL_TIERS_M_VND
        for m in council.EXPECTED_CONCURRENCY_MODES
        for p in council.EXPECTED_ALLOCATION_POLICIES
    ]
    cases_stress = [
        _make_synthetic_pareto_case(t, m, p, friction_mult=1.5)
        for t in council.EXPECTED_BANKROLL_TIERS_M_VND
        for m in council.EXPECTED_CONCURRENCY_MODES
        for p in council.EXPECTED_ALLOCATION_POLICIES
    ]
    by_id_base = {c["case_id"]: c for c in cases_base}
    by_id_stress = {c["case_id"]: c for c in cases_stress}

    frontier_by_tier = {
        f"{t}M_VND": [f"B{t}M__CONSERVATIVE_1_TICKET__P1_RECOUP_FIRST"] for t in council.EXPECTED_BANKROLL_TIERS_M_VND
    }
    tier_highlights: dict[str, Any] = {}
    for t in council.EXPECTED_BANKROLL_TIERS_M_VND:
        tk = f"{t}M_VND"
        c_safe = by_id_base[f"B{t}M__CONSERVATIVE_1_TICKET__P1_RECOUP_FIRST"]
        c_bal = by_id_base[f"B{t}M__GATED_STAGGER__P1_RECOUP_FIRST"]
        c_up = by_id_base[f"B{t}M__AGGRESSIVE_PARALLEL__P3_SCALE_80_20"]

        def _mk_role(cb: dict[str, Any]) -> dict[str, Any]:
            cs = by_id_stress[cb["case_id"]]
            return {
                "case_id": cb["case_id"],
                "net_profit_36m_vnd": cb["net_profit_36m_vnd"],
                "law15_grade_code": "TOT",
                "law15_grade_vi": "Tốt",
                "own_book_crossover_phase": "PHASE_2_MULTI_PROP_SCALING",
                "own_book_crossover_progress_pct": 25.0,
                "stress_1_5x": {"median_36m_net_vnd": cs["net_profit_36m_vnd"]["median"]},
            }

        tier_highlights[tk] = {
            "bankroll_m_vnd": t,
            "bankroll_usd": c_safe["bankroll_usd"],
            "safest": _mk_role(c_safe),
            "balanced_sweet_spot": _mk_role(c_bal),
            "max_upside": _mk_role(c_up),
        }

    sku_row_1x = {
        "winrate_pct": 48.61,
        "avg_rr": 1.272,
        "ev_per_trade_r": 0.0486,
        "profit_factor": 1.203,
        "peak_dd_pct": 10.78,
        "calmar": 0.86,
        "sharpe": 1.232,
        "ann_pct": 9.268,
        "drag_vs_100k_pct": -3.884,
    }
    sku_row_15x = {
        "winrate_pct": 47.33,
        "avg_rr": 1.245,
        "ev_per_trade_r": 0.0255,
        "profit_factor": 1.119,
        "peak_dd_pct": 12.129,
        "calmar": 0.457,
        "sharpe": 0.753,
    }
    pareto_81_sha, _ = put(
        "wave4_pareto_81cases_10k",
        {
            "schema_version": "naqex-wave4-pareto-81cases-10k-v1",
            "hard_invariants": dict(inv_base),
            "pareto_frontier_by_bankroll_tier": frontier_by_tier,
            "pareto_frontier_by_bankroll_tier_stress_1_5x": frontier_by_tier,
            "pareto_frontier_overall_ids": ["B500M__AGGRESSIVE_PARALLEL__P1_RECOUP_FIRST"],
            "pareto_frontier_overall_ids_stress_1_5x": ["B500M__AGGRESSIVE_PARALLEL__P1_RECOUP_FIRST"],
            "cases": cases_base,
            "cases_stress_1_5x": cases_stress,
        },
    )
    pareto_sum_sha, _ = put(
        "wave4_pareto_summary",
        {
            "schema_version": "naqex-wave4-pareto-summary-v1",
            "report_sha256": pareto_81_sha,
            "hard_invariants": dict(inv_base),
            "resolution_label_vi": "XẤP XỈ CẤP NGÀY",
            "resolution_tag": "APPROX_DAILY_RESOLUTION",
            "evidence_stage": "BACKTEST_DEV_SEALED_LE_2024",
            "execution_status": "MEASURED_DEMO_EXECUTION",
            "pricing_regime": "ALL_REGULAR_SSOT",
            "ssot_provenance": {"usd_vnd_rate": 25765.94, "fx_verified_utc": "2026-11-26T11:26:20+00:00"},
            "grid_shape": {"total_cases": 81, "n_paths": 10000, "horizon_months": 36},
            "shared_path_correlation_proof": {"shared_path": True, "mean_daily_pnl_rho": 0.999987},
            "per_sku_001_lot_audit": {
                "regimes": {"1.00x": {"100K": sku_row_1x, "10K": sku_row_1x}, "1.50x": {"100K": sku_row_15x}}
            },
            "tier_pareto_highlights": tier_highlights,
            "global_sweet_spots": {"min_bankroll_ruin_lt_1pct_m_vnd": 10},
            "stress_1_5x_summary": {"min_bankroll_positive_median_36m_m_vnd": 10},
            "the5ers_reference_compact": [],
        },
    )
    put(
        "w4_m2a_kernel_receipt",
        {
            "schema": "naqex-wave4-m2a-kernel-receipt-v1",
            "worker": "w4-m2a-kernel",
            "status": "DONE_VERIFIED",
            "hard_invariants": dict(inv_base),
        },
    )
    put(
        "w4_m2a_pareto_receipt",
        {
            "schema_version": "naqex-wave4-m2a-pareto-receipt-v1",
            "worker": "w4-m2a-pareto",
            "status": "DONE_VERIFIED",
            "hard_invariants": dict(inv_base),
            "artifacts": {
                "full_pareto_json": {"sha256": pareto_81_sha},
                "compact_summary_json": {"sha256": pareto_sum_sha},
            },
            "global_sweet_spots_summary": {
                "highest_mean_own_book_36m_case": {
                    "crossover": {
                        "crossover_equity_usd": 103159.91,
                        "crossover_equity_vnd": 2_658_012_106.0,
                        "crossover_progress_pct": 53.3,
                        "recommended_phase": "PHASE_3_HYBRID_BARBELL",
                    }
                }
            },
        },
    )

    # 6. Mui 2B: Own-Book + Frontier Blind + VN Playbook
    own_sha, own_doc = put(
        "ownbook_shadow_ops_summary",
        {
            "schema": "naqex-wave4-ownbook-shadow-ops-v1",
            "worker": "w4-m2b-ownops",
            "invariants": {**inv_base, "hard_cex_cap_pct": 25.0},
            "data_provenance": {"composite_window": "2020-01-01..2024-12-31"},
            "ownbook_dev_performance": {
                "guarded_metrics": {"sharpe": 1.36, "calmar": 0.83, "max_dd_pct": 8.09, "cagr_pct": 6.69},
                "ibkr_integer_share_audit_dev": {"clean_without_fractional": True, "total_cost_bps_yr": 144.43},
            },
            "extreme_stress_tests": {
                "STRESS_3_2022_SIMULTANEOUS_STOCK_BOND_CRASH": {
                    "ownbook_2022_max_dd_pct": 7.87,
                    "static_60_40_ief_2022_max_dd_pct": 20.69,
                },
                "STRESS_4_CRYPTO_FLASH_CRASH_MINUS35PCT": {"cross_liq_events": 0},
            },
            "ops4_health_snapshot": {"stress_summary": {"passed": 4, "total": 4, "all_passed": True}},
        },
    )
    fr_sha, _ = put(
        "frontier_cluster_b_blind_verdict",
        {
            "schema_version": "naqex-wave4-frontier-cluster-b-blind-verdict-v1",
            "worker": "w4-m2b-blind",
            "total_trials_logged": 27,
            "budget_cap": 36,
            **inv_base,
            "summary": {
                "surviving_count": 2,
                "killed_count": 1,
                "verdicts_by_sleeve": {
                    "FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY": "PASS_BLIND_CLUSTER_B",
                    "FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR": "KILLED_ON_BLIND_CLUSTER_B",
                    "FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM": "PASS_BLIND_CLUSTER_B",
                },
            },
            "sleeves": {
                "FRONTIER_01_SJM_NCO_REGIME_RISK_PARITY": {
                    "verdict": "PASS_BLIND_CLUSTER_B",
                    "blind_metrics": {
                        "sharpe": 1.203,
                        "calmar": 0.8108,
                        "max_dd_pct": 4.5719,
                        "max_dd_2022_pct": 1.6764,
                        "pbo_cscv": 0.2497,
                        "dsr_empirical": 0.9848,
                        "bh_fdr_q": 0.002575,
                        "corr_vs_7e": -0.0312,
                    },
                },
                "FRONTIER_02_VRP_VIX_TERM_VOL_MANAGED_MULTIFACTOR": {
                    "verdict": "KILLED_ON_BLIND_CLUSTER_B",
                    "failed_gates": ["min_cluster_b_sharpe", "max_pbo_cscv"],
                    "blind_metrics": {"sharpe": 0.7884, "pbo_cscv": 0.7609, "max_dd_2022_pct": 15.8067},
                },
                "FRONTIER_03_CRYPTO_PERP_FUNDING_CARRY_XSEC_MOM": {
                    "verdict": "PASS_BLIND_CLUSTER_B",
                    "blind_metrics": {
                        "sharpe": 7.1683,
                        "calmar": 30.5085,
                        "max_dd_pct": 0.1115,
                        "cagr_pct": 3.4007,
                        "pbo_cscv": 0.3224,
                        "dsr_empirical": 1.0,
                        "corr_vs_7e": -0.0707,
                    },
                    "diagnostics": {"cross_liq_events": 0},
                },
            },
            "pod_blend_impact": {
                "port_7e_baselines": {
                    "cluster_b_2019_2024": {
                        "sharpe": 1.2976,
                        "calmar": 1.268,
                        "max_dd_pct": 5.5237,
                        "cagr_pct": 7.0041,
                        "starved_months": {"starved_month_rate_le_0_pct": 37.5},
                    },
                    "cluster_b_2023_2024": {
                        "sharpe": 0.8724,
                        "calmar": 0.8428,
                        "max_dd_pct": 5.5079,
                        "cagr_pct": 4.6421,
                        "starved_months": {
                            "starved_month_rate_le_0_pct": 45.83,
                            "starved_months_le_0": 11,
                            "n_months": 24,
                        },
                    },
                },
                "combined_blends": {
                    "EQUAL_WEIGHT": {
                        "weights": {"PORT_7E": 0.3333, "F01": 0.3333, "F03": 0.3333},
                        "sharpe": 2.2918,
                        "calmar": 2.5994,
                        "max_dd_pct": 1.8867,
                        "cagr_pct": 4.9042,
                        "starved_months": {"starved_month_rate_le_0_pct": 29.17},
                        "delta_vs_port7e": {"starved_le_0_reduction_pp": 16.66},
                    },
                    "CAUSAL_CLUSTER_A_INV_VOL": {
                        "weights": {"PORT_7E": 0.1378, "F01": 0.2292, "F03": 0.633},
                        "sharpe": 3.8172,
                        "calmar": 4.617,
                        "max_dd_pct": 0.9244,
                        "cagr_pct": 4.268,
                        "starved_months": {"starved_month_rate_le_0_pct": 20.83},
                        "delta_vs_port7e": {"starved_le_0_reduction_pp": 25.0},
                    },
                    "CORE_50_FRONTIER_50": {
                        "weights": {"PORT_7E": 0.5, "F01": 0.25, "F03": 0.25},
                        "sharpe": 1.7134,
                        "calmar": 1.7795,
                        "max_dd_pct": 2.727,
                        "starved_months": {"starved_month_rate_le_0_pct": 41.67},
                    },
                },
            },
        },
    )
    put(
        "w4_m2b_ownops_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2b-ownops",
            "status": "PASS",
            "invariants": dict(inv_base),
            "artifacts": {".runtime/offensive4/frontier/ownbook_shadow_ops_summary.json": {"sha256": own_sha}},
        },
    )
    put(
        "w4_m2b_frontier_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2b-frontier",
            "status": "PASS",
            "invariants": dict(inv_base),
        },
    )
    put(
        "w4_m2b_blind_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2b-blind",
            "status": "PASS",
            "invariants": dict(inv_base),
            "artifacts": {".runtime/offensive4/frontier/frontier_cluster_b_blind_verdict.json": {"sha256": fr_sha}},
        },
    )
    put(
        "w4_m2b_vnbook_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2b-vnbook",
            "status": "PASS",
            "invariants": dict(inv_base),
            "source_provenance": {"ownbook_shadow_ops_summary_report_sha256": own_doc["report_sha256"]},
            "verification": {"playbook_bytes": 17805},
            "artifacts": {"planning/research/VN-OWNBOOK-EXECUTION-PLAYBOOK.md": {"sha256": "a" * 64}},
        },
    )

    # 7. Mui 2C: Fleet & Web UI
    e2e_sha, e2e_doc = put(
        "fleet_e2e_drill_receipt",
        {
            "schema_version": "naqex-wave4-fleet-e2e-drill-receipt-v1",
            "worker": "w4-m2c-sim-runbook",
            "status": "PASS",
            "invariants": dict(inv_no_spend),
            "lifecycle_drill": {
                "canonical_states_visited": [f"S{i}" for i in range(8)],
                "transitions_count": 19,
                "hash_chain_verified": True,
            },
            "guards_e1_to_e6_matrix": {
                "all_6_guards_proven": True,
                "simultaneous_all_6_guards_fired": [f"E{i}" for i in range(1, 7)],
            },
        },
    )
    put(
        "w4_m2c_fsm_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2c-fsm",
            "status": "PASS",
            "invariants": dict(inv_no_spend),
            "fsm_contract": {"canonical_states_count": 8},
        },
    )
    put(
        "w4_m2c_guards_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2c-guards",
            "status": "PASS",
            "invariants": dict(inv_no_spend),
            "guards_contract": {"guards_count": 6},
        },
    )
    put(
        "w4_m2c_ui_contract_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2c-ui-contract",
            "status": "PASS",
            "invariants": dict(inv_no_spend),
        },
    )
    put(
        "w4_m2c_sim_runbook_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2c-sim-runbook",
            "status": "PASS",
            "invariants": dict(inv_no_spend),
            "e2e_drill_summary": {"drill_report_sha256": e2e_doc["report_sha256"]},
            "runbook_summary": {"bytes": 15368},
            "artifacts": {".runtime/offensive4/fleet/fleet_e2e_drill_receipt.json": {"sha256": e2e_sha}},
        },
    )
    put(
        "w4_m2c_web_ui_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m2c-web-ui",
            "status": "PASS",
            "invariants": {**inv_no_spend, "api_requests_on_prop_fleet": 0, "hardcoded_hex_in_prop_fleet_css": 0},
            "bundle_metrics": {
                "critical_startup_graph_delta_bytes": 0,
                "lazy_total_raw_bytes": 118730,
                "lazy_total_gzip_bytes": 31148,
                "within_budget": True,
            },
            "verification": {
                "node_unit_tests_passed": 82,
                "playwright_browser_suites_count": 4,
                "playwright_results": {"tests/prop-fleet.browser.mjs": {"min_contrast_ratio": 16.44}},
            },
        },
    )

    # 8. Mui 3: AI Radar + Supervisor + PIT-24 + Shadow Ledger
    radar_sha, _ = put(
        "ai_model_radar_latest",
        {
            "schema_version": "naqex-wave4-ai-model-radar-v1",
            "hard_invariants": dict(inv_base),
            "sources": {"openrouter": {"status": "OK", "raw_count": 477, "valid_priced_count": 468}},
            "leaderboard_summary": {"budget_eligible_count": 302, "local_full_vram_fit_count": 12},
            "leaderboards": {
                "budget_macro_supervisor_monthly_usd": [
                    {"rank": 1, "id": "qwen/qwen3.7-flash", "monthly_usd": 0.0196, "monthly_vnd": 500}
                ]
            },
        },
    )
    ledger_sha, _ = put(
        "prospective_shadow_ledger",
        {
            "schema_version": "naqex-wave4-prospective-shadow-ledger-v1",
            "prospective_only": True,
            "order_send_capable": False,
            "holdout_cutoff_date": "2024-12-31",
            "first_live_session_date": "2026-11-30",
            "min_audit_calendar_days": 30,
            "summary": {"verified": True, "commitments_count": 0},
        },
    )
    pit24_sha, _ = put(
        "wave4_pit24_and_ai_rubric",
        {
            "schema_version": "naqex-wave4-pit24-and-ai-rubric-v1",
            "hard_invariants": dict(inv_base),
            "pit24_benchmark": {
                "outcome_status": "LIVE_24_PASS",
                "selected_model": "gpt-6-luna",
                "scenarios_ok": 24,
                "scenarios_total": 24,
                "json_schema_valid_rate_of_24_pct": 100.0,
                "regime_agreement_rate_of_ok_pct": 100.0,
                "latency_ms_ok": {"p50_ms": 3708.25, "p95_ms": 6287.86},
            },
            "prospective_shadow_ledger": {"ledger_file_sha256": ledger_sha},
            "ai_architecture_benchmark_6criteria": {
                "ranking_by_composite": [
                    {"rank": 1, "architecture": "MT5 ONNX / Pure-MQL5 v1.04-ML", "composite_score_5": 5.0}
                ]
            },
        },
    )
    put(
        "w4_m3a_radar_receipt",
        {
            "schema": "naqex-wave4-m3a-radar-receipt-v1",
            "worker": "w4-m3a-radar",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
            "deliverables": {"live_snapshot_sha256": radar_sha},
        },
    )
    put(
        "w4_m3b_sup_receipt",
        {
            "schema": "naqex-wave4-m3b-sup-receipt-v1",
            "worker": "w4-m3b-sup",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
        },
    )
    put(
        "w4_m3b_pit24_receipt",
        {
            "schema": "naqex-wave4-m3b-pit24-receipt-v1",
            "worker": "w4-m3b-pit24",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
            "deliverables": {
                "file_hygiene": {
                    ".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json": {"sha256": pit24_sha},
                    ".runtime/offensive4/ai/prospective_shadow_ledger.json": {"sha256": ledger_sha},
                }
            },
        },
    )

    # 9. Mui 4: CME + 16-Symbol M1
    cme_scale = {"XAU": "EV<=0", "DU_DUNG": "EV<3", "TOT": "EV>=3", "TOP_1_PCT": "EV>=5"}
    cme_sha, cme_doc = put(
        "wave4_cme_intraday_feasibility",
        {
            "schema_version": "naqex-wave4-cme-intraday-feasibility-v1",
            "invariants": dict(inv_no_spend),
            "simulation_config": {"n_paths": 10000},
            "dev_strategy_metrics": {"winrate_pct": 52.57, "profit_factor": 1.324},
            "decision": "SKIP",
            "decision_rationale": {
                "vn_eligible_best_tier": "topstep_100k_combine",
                "vn_eligible_best_ev_per_fee": 1.021,
                "failed_gates": ["EV_PER_FEE_BELOW_3X"],
            },
            "vn_kyc_feasibility_matrix": [
                {"firm_id": "topstep", "asset_class": "CME_FUTURES_INTRADAY", "vn_kyc_eligible": True},
                {"firm_id": "mffu", "asset_class": "CME_FUTURES_INTRADAY", "vn_kyc_eligible": False},
                {"firm_id": "tpt", "asset_class": "CME_FUTURES_INTRADAY", "vn_kyc_eligible": False},
                {"firm_id": "tradeify", "asset_class": "CME_FUTURES_INTRADAY", "vn_kyc_eligible": False},
            ],
            "cme_4firm_results": {
                "topstep_100k_combine": {
                    "tier_id": "topstep_100k_combine",
                    "vn_kyc_status": "ALLOWED_XFA_ONLY",
                    "ev_per_usd_fee": 1.021,
                    "median_net_24m_usd": 149.95,
                    "median_net_24m_vnd": 3_863_531.0,
                    "prob_net_le_zero_pct": 48.88,
                    "funded_blowup_12m_pct": 57.85,
                    "funded_blowup_12m_wilson_ub95_pct": 58.9,
                    "median_cal_days_to_payout1_unconditional": 516.0,
                    "pass_fail_pending": _make_partition_4(43.56, 56.40),
                    "domain_scorecard": {"scale_definition": cme_scale},
                },
                "topstep_50k_combine": {
                    "tier_id": "topstep_50k_combine",
                    "ev_per_usd_fee": 0.799,
                    "median_net_24m_usd": -211.1,
                    "median_net_24m_vnd": -5_439_287.0,
                    "prob_net_le_zero_pct": 53.82,
                    "funded_blowup_12m_pct": 32.36,
                    "pass_fail_pending": _make_partition_4(53.86, 46.06),
                },
                "tradeify_50k_growth": {
                    "tier_id": "tradeify_50k_growth",
                    "vn_kyc_status": "RESTRICTED_VN_PROHIBITED",
                    "ev_per_usd_fee": 2.851,
                    "funded_blowup_12m_pct": 31.89,
                    "prob_net_le_zero_pct": 47.48,
                    "pass_fail_pending": _make_partition_4(53.63, 46.34),
                },
            },
            "incumbent_ftmo_results": {
                "ftmo_standard_10k": {"ev_per_usd_fee": 3.485, "pass_fail_pending": _make_partition_4(69.45, 17.88)},
                "ftmo_standard_100k": {"ev_per_usd_fee": 6.628, "pass_fail_pending": _make_partition_4(69.79, 20.16)},
            },
        },
    )
    m1_16_sha, _ = put(
        "wave4_16sym_harvest_summary",
        {
            "schema": "naqex-wave4-16sym-harvest-summary-v1",
            "worker": "w4-m4-exec",
            "hard_invariants": {**inv_base, "existing_hot_m1_symbol_count": 12},
            "target_inventory": {
                "expected_count": 16,
                "sealed_count": 16,
                "total_bars_sealed": 36_825_451,
                "total_parquet_bytes": 480_381_807,
                "provenance_breakdown": {"QDM_PROVIDER_DEFAULT_SINGLE_SIDE": 6, "FTMO_BID_PLUS_SPREAD": 10},
                "depth_breakdown": {"FULL_DEV_7Y_DENSE_M1": 8, "PARTIAL_DEV_DENSE_M1": 8},
            },
        },
    )
    put(
        "w4_m4a_cme_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-m4a-cme",
            "status": "PASS",
            "invariants": dict(inv_base),
        },
    )
    put(
        "w4_m4b_m1pipe_receipt",
        {
            "schema": "naqex-wave4-m4b-m1pipe-receipt-v1",
            "worker": "w4-m4b-m1pipe",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
        },
    )
    put(
        "w4_m4_exec_receipt",
        {
            "schema": "naqex-wave4-m4-exec-receipt-v1",
            "worker": "w4-m4-exec",
            "status": "PASS",
            "hard_invariants": dict(inv_base),
            "cme_verification": {
                "cme_file_sha256": cme_sha,
                "report_sha256": cme_doc["report_sha256"],
                "wave2_summary_sha256": "b" * 64,
            },
            "m1_16sym_harvest": {"summary_sha256": m1_16_sha},
        },
    )

    # 10. Wave 2B/2D Ops & Tests
    put(
        "w4_ops_briefing_wire_receipt",
        {
            "schema_version": "naqex-wave4-worker-receipt-v1",
            "worker": "w4-ops-briefing-wire",
            "status": "PASS",
            "invariants": dict(inv_base),
            "zero_popup_verification": {"pythonw_exit_code": 0},
        },
    )
    put(
        "w4_tests_all_receipt",
        {
            "schema_version": "naqex-wave4-tests-all-receipt-v1",
            "worker": "w4-tests-all",
            "overall_status": "PASS",
            "hard_invariants": dict(inv_base),
            "test_suites": {
                "suite_b_ci_parity_5_testpaths_not_local_cache": {"passed": 2508},
                "suite_d_ruff_check": {"errors": 0},
                "suite_e_ast_zero_popup_w4_g17": {
                    "files_scanned": 48,
                    "subprocess_calls_checked": 57,
                    "missing_creationflags_count": 0,
                },
                "suite_h_immutables_and_hygiene": {
                    "immutables_10_of_10_clean": True,
                    "quant_core_py_count": 41,
                    "private_vault_ex5_count": 0,
                    "tracked_exports_ex5_count": 0,
                },
            },
        },
    )
    return root


# ==============================================================================
# 1. Static AST Safety, Zero-Assert, Zero-Subprocess & Import Hygiene
# ==============================================================================


def test_01_static_ast_zero_assert_zero_subprocess_and_constants() -> None:
    module_path = AI_ENGINES_DIR / "quant_factory" / "wave4" / "wave4_master_council.py"
    test_path = Path(__file__).resolve()

    for path in (module_path, test_path):
        src = path.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(path))
        asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        _check(not asserts, f"Bare assert found in {path.name} at lines {asserts}")

    mod_tree = ast.parse(module_path.read_text(encoding="utf-8"), filename=str(module_path))
    forbidden_roots = (
        "subprocess",
        "scipy",
        "MetaTrader5",
        "backtesting",
        "backtrader",
        "vectorbt",
        "hmmlearn",
        "shap",
        "psycopg",
        "lightgbm",
        "catboost",
        "onnxruntime",
    )
    for node in ast.walk(mod_tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(
                    not alias.name.startswith(forbidden_roots),
                    f"Forbidden import {alias.name!r} at line {node.lineno}",
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            _check(
                not mod.startswith(forbidden_roots),
                f"Forbidden from-import {mod!r} at line {node.lineno}",
            )

    _check(council.HOLDOUT_CUTOFF_DATE == "2024-12-31", "HOLDOUT_CUTOFF_DATE mismatch")
    _check(council.ORDER_SEND_CAPABLE is False, "ORDER_SEND_CAPABLE must be False")
    _check(council.ORDER_SEND_COUNT == 0, "ORDER_SEND_COUNT must be 0")
    _check(council.SPEND_VND == 0, "SPEND_VND must be 0")
    _check(len(council.RAW_ARTIFACT_SPECS) == 40, f"Expected 40 raw specs, got {len(council.RAW_ARTIFACT_SPECS)}")
    _check(
        len({s.artifact_id for s in council.RAW_ARTIFACT_SPECS}) == 40, "Duplicate artifact_id in RAW_ARTIFACT_SPECS"
    )
    _check(len({s.rel_path for s in council.RAW_ARTIFACT_SPECS}) == 40, "Duplicate rel_path in RAW_ARTIFACT_SPECS")


# ==============================================================================
# 2. Synthetic 40-Artifact Reconciliation & Master Metrics 1-Byte Tamper Catch
# ==============================================================================


def test_02_synthetic_full_reconciliation_and_master_tamper_detection(tmp_path: Path) -> None:
    root = _build_synthetic_40_workspace(tmp_path)
    out_file = tmp_path / "wave4_master_metrics.json"
    res = council.run_council_and_write(root=root, out_path=out_file)

    _check(res["status"] == "PASS", f"Unexpected status: {res['status']}")
    _check(res["reconciled_artifact_count"] == 40, f"Expected 40 artifacts, got {res['reconciled_artifact_count']}")
    _check(res["self_hash_verified_count"] == 18, f"Expected 18 self-hashes, got {res['self_hash_verified_count']}")
    _check(res["cross_artifact_sha256_links_verified"] == 16, "Expected 16 cross-artifact links")

    verified = council.verify_master_metrics_file(out_file)
    _check(verified["verified"] is True, "Expected verified True")
    _check(verified["pareto_tiers_count"] == 9, "Expected 9 Pareto tiers")
    _check(verified["pareto_pointers_count"] == 81, "Expected 81 Pareto config pointers")

    # 1-byte tamper on emitted wave4_master_metrics.json MUST fail closed under python & python -O
    tampered = json.loads(out_file.read_text(encoding="utf-8"))
    tampered["hard_invariants"]["quant_core_py_count"] = 42
    council.write_json_lf(out_file, tampered)
    with pytest.raises(council.TamperedArtifactError):
        council.verify_master_metrics_file(out_file)


# ==============================================================================
# 3. Fail-Closed Missing Receipt & Malformed JSON
# ==============================================================================


def test_03_fail_closed_missing_receipt_and_malformed_json(tmp_path: Path) -> None:
    root = _build_synthetic_40_workspace(tmp_path)
    target = root / ".runtime/offensive4/audits/w4_m2c_fsm_receipt.json"
    target.unlink()
    with pytest.raises(council.MissingArtifactError):
        council.build_wave4_master_metrics(root)

    target.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(council.MalformedArtifactError):
        council.build_wave4_master_metrics(root)


# ==============================================================================
# 4. Fail-Closed Tampered Self-Hash, Cross-Hash & Pinned SHA-256
# ==============================================================================


def test_04_fail_closed_tampered_hashes(tmp_path: Path) -> None:
    # (a) Tampered embedded self-hash
    root_a = _build_synthetic_40_workspace(tmp_path / "case_a")
    p_a = root_a / ".runtime/offensive4/fleet/fleet_e2e_drill_receipt.json"
    doc_a = json.loads(p_a.read_text(encoding="utf-8"))
    doc_a["lifecycle_drill"]["transitions_count"] = 999
    council.write_json_lf(p_a, doc_a)
    with pytest.raises(council.TamperedArtifactError):
        council.build_wave4_master_metrics(root_a)

    # (b) Tampered cross-artifact SHA-256 (modify 81-case file without updating pareto summary report_sha256)
    root_b = _build_synthetic_40_workspace(tmp_path / "case_b")
    p_b = root_b / ".runtime/offensive4/pareto/wave4_pareto_81cases_10k.json"
    doc_b = json.loads(p_b.read_text(encoding="utf-8"))
    doc_b["tamper_note"] = "1byte_drift"
    council.write_json_lf(p_b, doc_b)
    with pytest.raises(council.TamperedArtifactError):
        council.build_wave4_master_metrics(root_b)

    # (c) Tampered pinned file_sha256 override
    root_c = _build_synthetic_40_workspace(tmp_path / "case_c")
    with pytest.raises(council.TamperedArtifactError):
        council.build_wave4_master_metrics(root_c, expected_file_sha256={"w4_t0_env_receipt": "f" * 64})


# ==============================================================================
# 5. Fail-Closed Holdout > 0, Cutoff >= 2025, OrderSend > 0, Spend > 0
# ==============================================================================


def test_05_fail_closed_holdout_ordersend_and_spend_violations(tmp_path: Path) -> None:
    # (a) holdout_rows_analysed > 0 (nested)
    root_h = _build_synthetic_40_workspace(tmp_path / "h1")
    p_h = root_h / ".runtime/offensive4/audits/w4_m1_feat_receipt.json"
    d_h = json.loads(p_h.read_text(encoding="utf-8"))
    d_h["hard_invariants"]["holdout_rows_analysed"] = 1
    council.write_json_lf(p_h, d_h)
    with pytest.raises(HoldoutLockError):
        council.build_wave4_master_metrics(root_h)

    # (b) holdout_cutoff_date > 2024-12-31
    root_c = _build_synthetic_40_workspace(tmp_path / "h2")
    p_c = root_c / ".runtime/offensive4/audits/w4_t0_env_receipt.json"
    d_c = json.loads(p_c.read_text(encoding="utf-8"))
    d_c["hard_invariants"]["holdout_cutoff_date"] = "2025-01-15"
    council.write_json_lf(p_c, d_c)
    with pytest.raises(HoldoutLockError):
        council.build_wave4_master_metrics(root_c)

    # (c) order_send_count > 0
    root_o = _build_synthetic_40_workspace(tmp_path / "o1")
    p_o = root_o / ".runtime/offensive4/audits/w4_m1_cv_receipt.json"
    d_o = json.loads(p_o.read_text(encoding="utf-8"))
    d_o["hard_invariants"]["order_send_count"] = 1
    council.write_json_lf(p_o, d_o)
    with pytest.raises(council.SafetyInvariantViolationError):
        council.build_wave4_master_metrics(root_o)

    # (d) order_send_capable = True
    root_cap = _build_synthetic_40_workspace(tmp_path / "o2")
    p_cap = root_cap / ".runtime/offensive4/ai/prospective_shadow_ledger.json"
    d_cap = json.loads(p_cap.read_text(encoding="utf-8"))
    d_cap["order_send_capable"] = True
    new_sha, _ = _write_json(p_cap, d_cap)
    # Update cross-links so safety scanner is the exact blocker triggered
    for rel, keys in (
        (".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json", ("prospective_shadow_ledger", "ledger_file_sha256")),
    ):
        pp = root_cap / rel
        dd = json.loads(pp.read_text(encoding="utf-8"))
        dd[keys[0]][keys[1]] = new_sha
        new_pit_sha, _ = _write_json(pp, dd)
        pr = root_cap / ".runtime/offensive4/audits/w4_m3b_pit24_receipt.json"
        dr = json.loads(pr.read_text(encoding="utf-8"))
        dr["deliverables"]["file_hygiene"][".runtime/offensive4/ai/prospective_shadow_ledger.json"]["sha256"] = new_sha
        dr["deliverables"]["file_hygiene"][".runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json"]["sha256"] = (
            new_pit_sha
        )
        _write_json(pr, dr)
    with pytest.raises(council.SafetyInvariantViolationError):
        council.build_wave4_master_metrics(root_cap)

    # (e) spend_vnd > 0
    root_s = _build_synthetic_40_workspace(tmp_path / "s1")
    p_s = root_s / ".runtime/offensive4/audits/w4_t0_env_receipt.json"
    d_s = json.loads(p_s.read_text(encoding="utf-8"))
    d_s["hard_invariants"]["spend_vnd"] = 500_000
    council.write_json_lf(p_s, d_s)
    with pytest.raises(council.SafetyInvariantViolationError):
        council.build_wave4_master_metrics(root_s)

    # (f) stripped required holdout_rows_analysed key fails closed
    root_m = _build_synthetic_40_workspace(tmp_path / "m1")
    p_m = root_m / ".runtime/offensive4/audits/w4_t0_env_receipt.json"
    d_m = json.loads(p_m.read_text(encoding="utf-8"))
    del d_m["hard_invariants"]["holdout_rows_analysed"]
    council.write_json_lf(p_m, d_m)
    with pytest.raises(HoldoutLockError):
        council.build_wave4_master_metrics(root_m)


# ==============================================================================
# 6. Fail-Closed Pareto Partition Sum & Summary-vs-81case Drift
# ==============================================================================


def test_06_fail_closed_pareto_arithmetic_drift(tmp_path: Path) -> None:
    root = _build_synthetic_40_workspace(tmp_path)
    p81 = root / ".runtime/offensive4/pareto/wave4_pareto_81cases_10k.json"
    psum = root / ".runtime/offensive4/pareto/wave4_pareto_summary.json"
    prec = root / ".runtime/offensive4/audits/w4_m2a_pareto_receipt.json"

    # Mutate one stress_1_5x partition to sum to 99.0% and re-sync SHA links so arithmetic guard catches it
    d81 = json.loads(p81.read_text(encoding="utf-8"))
    d81["cases_stress_1_5x"][0]["monthly_pass_fail_pending"]["24m"]["pending_pct"] -= 1.0
    sha81, _ = _write_json(p81, d81)
    dsum = json.loads(psum.read_text(encoding="utf-8"))
    dsum["report_sha256"] = sha81
    shasum, _ = _write_json(psum, dsum)
    drec = json.loads(prec.read_text(encoding="utf-8"))
    drec["artifacts"]["full_pareto_json"]["sha256"] = sha81
    drec["artifacts"]["compact_summary_json"]["sha256"] = shasum
    _write_json(prec, drec)

    with pytest.raises(council.ArithmeticDriftError):
        council.build_wave4_master_metrics(root)


# ==============================================================================
# 7. Local-Cache Real Workspace Verification (.runtime/offensive4)
# ==============================================================================


@pytest.mark.local_cache
def test_07_local_cache_real_wave4_master_metrics_and_receipts() -> None:
    master_path = council.DEFAULT_MASTER_METRICS_PATH
    _check(master_path.is_file(), f"Missing master SSOT: {master_path}")
    raw_bytes = master_path.read_bytes()
    _check(b"\r\n" not in raw_bytes, "wave4_master_metrics.json must use LF line endings")
    _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), "wave4_master_metrics.json must have 0 BOM")

    verified = council.verify_master_metrics_file(master_path)
    _check(verified["verified"] is True, "Master metrics self-verification failed")
    _check(verified["reconciled_artifact_count"] == 40, f"Expected 40 artifacts, got {verified}")
    _check(verified["pareto_tiers_count"] == 9, "Expected 9 Pareto tiers")
    _check(verified["pareto_pointers_count"] == 81, "Expected 81 Pareto config pointers")

    master = json.loads(raw_bytes.decode("utf-8"))
    _check(master["hard_invariants"]["holdout_rows_analysed"] == 0, "Holdout rows must be 0")
    _check(master["hard_invariants"]["order_send_count"] == 0, "OrderSend count must be 0")
    _check(master["hard_invariants"]["spend_vnd"] == 0, "Spend VND must be 0")

    # Independently recompute disk file_sha256 for ALL 40 raw artifacts and compare 1:1
    artifacts = master["artifact_reconciliation_ledger"]["artifacts"]
    _check(len(artifacts) == 40, f"Expected 40 ledger artifacts, got {len(artifacts)}")
    for entry in artifacts:
        disk_path = REPO_ROOT / entry["rel_path"]
        _check(disk_path.is_file(), f"Reconciled artifact missing on disk: {entry['rel_path']}")
        disk_sha = hashlib.sha256(disk_path.read_bytes()).hexdigest()
        _check(
            disk_sha == entry["file_sha256"],
            f"SHA-256 mismatch on {entry['rel_path']}: ledger={entry['file_sha256']} disk={disk_sha}",
        )

    # Independently cross-check key 4-tier scorecard figures against raw summaries on disk
    sc = master["four_tier_inside_out_scorecard"]
    _check(
        sc["tier_1_single_cfd_prop_bot"]["wave4_achieved"]["same_feed_model1_parity"]["matched_trades"] == 3320,
        "T1 parity mismatch",
    )
    _check(
        sc["tier_1_single_cfd_prop_bot"]["wave4_achieved"]["v104_ml_mt5_onnx_w4g05"]["net_pnl_usd"] == 639.18,
        "T1 v1.04-ML PnL mismatch",
    )
    _check(sc["tier_2_cme_futures_prop"]["verdict"] == "SKIP", "T2 CME verdict must be SKIP")
    _check(
        sc["tier_2_cme_futures_prop"]["wave4_achieved"]["vn_eligible_best_tier"]["ev_per_usd_fee"] == 1.021,
        "T2 CME EV mismatch",
    )
    t3_blends = sc["tier_3_multi_asset_ownbook_frontier_pod"]["wave4_achieved"]["combined_pod_blends_2023_2024"]
    _check(t3_blends["equal_weight"]["sharpe"] == 2.2918, "T3 Equal-Weight Sharpe mismatch")
    _check(t3_blends["causal_cluster_a_inv_vol"]["sharpe"] == 3.8172, "T3 Inv-Vol Sharpe mismatch")
    _check(t3_blends["equal_weight"]["starved_months_le_0_pct"] == 29.17, "T3 Equal-Weight starved mismatch")
    _check(t3_blends["causal_cluster_a_inv_vol"]["starved_months_le_0_pct"] == 20.83, "T3 Inv-Vol starved mismatch")
    t4 = sc["tier_4_live_ops_fleet_cockpit_ai"]["wave4_achieved"]
    _check(t4["web_cockpit_w4g11"]["lazy_total_raw_bytes"] == 119421, "T4 Web UI raw bytes mismatch")
    _check(t4["web_cockpit_w4g11"]["lazy_total_gzip_bytes"] == 31121, "T4 Web UI gzip bytes mismatch")
    _check(t4["web_cockpit_w4g11"]["node_unit_tests_passed"] == 86, "T4 Web UI node tests mismatch")
    _check(t4["ai_stack_w4g13_w4g14"]["pit24_scenarios_ok"] == 24, "T4 PIT-24 ok count mismatch")
    _check(t4["m1_data_lake_w4g02_w4g16"]["wave4_16sym_total_bars"] == 36_825_451, "T4 16sym bars mismatch")

    # Verify byte-identical receipts if present
    audit_receipt = council.DEFAULT_AUDIT_RECEIPT_PATH
    dropbox_receipt = council.DEFAULT_DROPBOX_RECEIPT_PATH
    _check(audit_receipt.is_file(), f"Missing audit receipt: {audit_receipt}")
    _check(dropbox_receipt.is_file(), f"Missing dropbox receipt: {dropbox_receipt}")
    a_bytes = audit_receipt.read_bytes()
    d_bytes = dropbox_receipt.read_bytes()
    _check(a_bytes == d_bytes, "Audit receipt and dropbox receipt must be byte-identical")
    _check(b"\r\n" not in a_bytes and not a_bytes.startswith(b"\xef\xbb\xbf"), "Receipt must be LF / 0-BOM")
    rec_doc = json.loads(a_bytes.decode("utf-8"))
    _check(
        rec_doc["master_metrics_file_sha256"] == verified["file_sha256"],
        "Receipt master_metrics_file_sha256 mismatch",
    )
    _check(
        rec_doc["master_metrics_report_sha256"] == verified["report_sha256"],
        "Receipt master_metrics_report_sha256 mismatch",
    )
    _check(
        council.compute_canonical_report_sha256(rec_doc) == rec_doc["report_sha256"],
        "Receipt self report_sha256 mismatch",
    )
