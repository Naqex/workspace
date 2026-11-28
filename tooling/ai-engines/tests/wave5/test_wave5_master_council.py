"""Wave 3A (`w5-master-council`) Master Council Unit, Tamper, Safety, and Local SSOT Tests.

Covers:
  - Pure offline CI-safe (`-m "not local_cache"`) tests (ZERO `.runtime/` dependency):
      1. Static AST & hygiene audit: 0 bare `assert`s (`python -O` safe), 0 CRLF / 0 BOM,
         0 `jsonschema` imports, 0 bare dollar signs, and `CREATE_NO_WINDOW` on subprocesses.
      2. LF-normalized SHA-256 verification for 11/11 immutables (CRLF-resilient, tamper-failing),
         plus workspace guards (`quant_core_py_count == 41`, 0 `.ex5`, `MT5_PROCS == 0`, UI schema parity).
      3. Fail-closed safety scanner (`holdout_rows_analysed > 0`, `holdout_cutoff_date >= 2025`,
         `dev_cutoff_sec != 1735689600`, `order_send_count > 0`, bool-as-int, `order_send_capable=True`,
         `spend_vnd > 0`, `auto_deploy_permitted=True`, missing required keys).
      4. Bare-dollar guard, 100%-sum partition guard, and Alpha Factory SHA-256 ledger hash-chain guard.
      5. Synthetic 25-artifact reconciliation (all self-hash modes, all 40 cross-artifact SHA-256 links,
         NPZ & CSV holdout/row checks, 1-byte tamper detection, `PENDING_CONCURRENT_LANE` vs `--resync`
         lock-in for `w5_trader_ui_receipt.json`, Pydantic v2 `EvaluationScorecard` emission & validation,
         and byte-identical receipt writer into `tmp_path`).
  - Local disk reconciliation (`@pytest.mark.local_cache`):
      6. Live `11/11` immutables LF-SHA + workspace hard invariants verification.
      7. Full disk reconciliation (`write_output_path=None` and `tmp_path`), DuckDB/SQLite catalog
         integrity (`1,342` legacy + `1,250` MC = `168 + 20 + 1,062` + `122` runs), direct SQL
         `Wave 4 vs Wave 5` separation (`legacy_grade_code` vs `unified_grade_code` & `funded_mult`),
         and strict SHA-256 invariance of `.runtime/offensive5/wave5_master_metrics.json` before/after pytest!
      8. Byte-identical council receipts `.runtime/offensive5/audits/w5_master_council_receipt.json`
         and `.tmp/swarm_dropbox/w5-master-council.json` self-hash & SSOT pointer verification.

All assertions use `_check(...)` so EVERY check stays 100% active under `python -O`.
"""

from __future__ import annotations

import ast
import copy
import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory.wave5 import evaluation_catalog as ec  # noqa: E402
from quant_factory.wave5 import wave5_master_council as council  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _write_self_hashed(
    path: Path,
    doc: dict[str, Any],
    *,
    field: str | None = None,
    mode: str | None = None,
) -> tuple[str, dict[str, Any]]:
    payload = copy.deepcopy(doc)
    if field and mode:
        payload[field] = council._compute_embedded_digest_by_mode(payload, field=field, mode=mode)
    fsha, _nbytes = council.write_json_lf(path, payload)
    return fsha, payload


def _build_valid_ledger_doc() -> dict[str, Any]:
    e1_body = {"seq": 1, "prev_hash": "0" * 64, "event": "REGISTER", "holdout_rows_analysed": 0, "order_send_count": 0}
    e1_hash = hashlib.sha256(
        json.dumps(e1_body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    e1 = {**e1_body, "entry_hash": e1_hash}
    e2_body = {
        "seq": 2,
        "prev_hash": e1_hash,
        "event": "SWAP_PROPOSAL",
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
    }
    e2_hash = hashlib.sha256(
        json.dumps(e2_body, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    ).hexdigest()
    e2 = {**e2_body, "entry_hash": e2_hash}
    doc = {
        "schema_version": "naqex-wave5-alpha-factory-ledger-v1",
        "factory_id": "synthetic_drill_3",
        "entry_count": 2,
        "ledger_root_sha256": e2_hash,
        "entries": [e1, e2],
        "hard_invariants": {
            "auto_deploy_permitted": False,
            "holdout_cutoff_date": "2024-12-31",
            "holdout_rows_analysed": 0,
            "order_send_capable": False,
            "order_send_count": 0,
        },
    }
    doc["report_sha256"] = council.compute_canonical_report_sha256(doc)
    return doc


def _make_synthetic_tier_a_row(schedule_id: str, contract_id: str, friction_mult: float, cohort: str) -> dict[str, Any]:
    return {
        "cohort": cohort,
        "schedule_id": schedule_id,
        "contract_id": contract_id,
        "friction_mult": friction_mult,
        "overall_grade": "GOOD" if schedule_id in ("V103_SPRINT", "T3_BALANCED_EV") else "ADEQUATE",
        "phase_grades": {"p1": "TOP_1_PCT", "p2": "TOP_1_PCT", "pass_eval": "GOOD", "funded_12m": "TOP_1_PCT"},
        "p1_pass_12m_pct": 80.0,
        "p1_fail_12m_pct": 15.0,
        "p1_pending_12m_pct": 5.0,
        "p2_pass_12m_pct": 88.0,
        "p2_fail_12m_pct": 7.0,
        "p2_pending_12m_pct": 5.0,
        "pass_eval_12m_pct": 68.0,
        "fail_eval_12m_pct": 22.0,
        "pending_eval_12m_pct": 10.0,
        "pass_eval_36m_pct": 75.0,
        "fail_eval_36m_pct": 25.0,
        "pass_eval_3m_pct": 10.0,
        "pass_eval_6m_pct": 35.0,
        "fn12_blowup_pct": 0.30,
        "fn12_wilson_ub_pct": 0.45,
        "ev_per_fee_npv24": 11.5,
        "ev_npv_24m_vnd": 180_000_000.0,
        "p_npv24_le_0_pct": 26.5,
        "uncond_med_pay1_cap730": 235.0,
        "cond_med_pay1_days": 175.0,
        "pf": 1.22,
        "sharpe": 1.32,
        "calmar": 1.12,
        "max_dd_pct": 7.2,
        "winrate_pct": 49.5,
        "avg_rr": 1.26,
        "firm_hard_breach_daily_pct": 0.0,
        "top_bottlenecks": ["PAYOUT_1_SLOW"],
        "mandatory_tags": ["CONSUMED_DEV_CLB_TEMPORAL_OOS"],
    }


def _build_synthetic_wave5_workspace(tmp_path: Path, *, include_trader_ui: bool = False) -> Path:
    """Create a complete, internally consistent 25-artifact synthetic Wave 5 workspace in `tmp_path`."""
    root = tmp_path / "w5_synth"
    spec_map = {s.artifact_id: s for s in council.RAW_ARTIFACT_SPECS}

    # Copy real evaluation_taxonomy.json & UI schema.json into synthetic workspace
    tax_dst = root / "tooling" / "ai-engines" / "configs" / "ssot" / "evaluation_taxonomy.json"
    tax_dst.parent.mkdir(parents=True, exist_ok=True)
    tax_dst.write_bytes(ec.DEFAULT_TAXONOMY_PATH.read_bytes())
    tax_sha = council.compute_file_sha256(tax_dst)

    schema_dst = root / "UI" / "contracts" / "evaluation-scorecard" / "1.0.0" / "schema.json"
    schema_dst.parent.mkdir(parents=True, exist_ok=True)
    schema_dst.write_bytes(ec.DEFAULT_SCORECARD_SCHEMA_PATH.read_bytes())

    inv_base = {
        "order_send_capable": False,
        "order_send_count": 0,
        "spend_vnd": 0,
        "holdout_cutoff_date": "2024-12-31",
        "dev_cutoff_sec": 1735689600,
        "holdout_2025_plus_sealed": True,
        "holdout_rows_analysed": 0,
    }
    inv_no_spend = {k: v for k, v in inv_base.items() if k != "spend_vnd"}

    def put_json(aid: str, doc: dict[str, Any]) -> tuple[str, dict[str, Any]]:
        sp = spec_map[aid]
        return _write_self_hashed(
            root / sp.rel_path,
            doc,
            field=sp.self_hash_field,
            mode=sp.self_hash_mode,
        )

    # Binary & NPZ & CSV artifacts
    npz_path = root / spec_map["port_v5_tapes_npz"].rel_path
    npz_path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        npz_path,
        holdout_rows_analysed=np.int64(0),
        order_send_count=np.int64(0),
        port_v5_equals_port_7e=np.bool_(True),
        n_core7_engines=np.int64(7),
        n_added_engines=np.int64(0),
        cluster_b_dates_iso=np.array(["2021-01-04", "2024-12-31"]),
        dev_all_dates_iso=np.array(["2018-01-02", "2024-12-31"]),
    )
    npz_sha = council.compute_file_sha256(npz_path)

    onnx_path = root / spec_map["naqex_v105_lgbm_onnx"].rel_path
    onnx_path.parent.mkdir(parents=True, exist_ok=True)
    onnx_path.write_bytes(b"SYNTHETIC_ONNX_MODEL_BYTES_V105")
    onnx_sha = council.compute_file_sha256(onnx_path)

    p500_path = root / spec_map["wave5_ml_parity_500_csv"].rel_path
    p500_lines = ["row_idx,f0,f1"] + [f"{i},0.5,0.1" for i in range(500)]
    p500_path.write_bytes(("\n".join(p500_lines) + "\n").encode("utf-8"))
    p500_sha = council.compute_file_sha256(p500_path)

    ref24_path = root / spec_map["wave5_2024_features_ref_csv"].rel_path
    ref24_lines = ["signal_seq,entry_utc_ts,engine_id"] + [f"{i},{1704166120 + i * 60},E1" for i in range(777)]
    ref24_path.write_bytes(("\n".join(ref24_lines) + "\n").encode("utf-8"))
    ref24_sha = council.compute_file_sha256(ref24_path)

    # Dummy DuckDB & SQLite binary placeholders for artifact-loader tests
    for bin_id in ("unified_eval_catalog_duckdb", "unified_eval_registry_sqlite3"):
        bp = root / spec_map[bin_id].rel_path
        bp.parent.mkdir(parents=True, exist_ok=True)
        bp.write_bytes(f"SYNTHETIC_{bin_id}".encode())

    # 1. Wave 0A & 0B
    put_json(
        "w5_t0_env_receipt",
        {
            "schema": "naqex-wave5-t0-env-receipt-v1",
            "worker": "w5-t0-env",
            "verdict": "PASS",
            "hard_invariants": dict(inv_base),
        },
    )
    put_json(
        "w5_taxonomy_ui_receipt",
        {
            "schema": "naqex-wave5-taxonomy-ui-receipt-v1",
            "worker": "w5-taxonomy-ui",
            "verdict": "PASS_W5_G03_AND_W5_G04",
            "hard_invariants": dict(inv_base),
            "w5_g03_taxonomy_and_catalog": {"taxonomy_sha256": tax_sha},
        },
    )
    _, bp_doc = put_json(
        "w5_baseline_4profiles",
        {
            "schema_version": "naqex-wave5-baseline-4profiles-v1",
            "hard_invariants": dict(inv_base),
            "summary_matrix": [{"profile_id": "V103_SPRINT"}] * 20,
            "paired_oof_comparison": {"delta_v104_ml_minus_v103_oof_control": {"delta_ev": -0.5}},
            "catalog_registration": {"runs_recorded_count": 20},
        },
    )
    put_json(
        "w5_baseline_receipt",
        {
            "schema": "naqex-wave5-baseline-receipt-v1",
            "worker": "w5-baseline",
            "verdict": "PASS_W5_G05",
            "hard_invariants": dict(inv_base),
            "report_sha256": bp_doc["report_sha256"],
            "catalog_registration": {
                "mc_cases_recorded": {"source_artifact_sha256": bp_doc["report_sha256"]}
            },
        },
    )

    # 2. Wave 1A + 1B/1C
    put_json(
        "w5_m1_loader_fam_receipt",
        {
            "schema": "naqex-wave5-m1-loader-fam-receipt-v1",
            "worker": "w5-m1-loader",
            "verdict": "PASS_W5_G06",
            "hard_invariants": {**inv_base, "usoil_quarantined_rows": 2753},
            "universe_28_audit": {
                "symbol_count": 28,
                "all_28_present": True,
                "resolution_counts": {"M1_BID_ASK": 12, "M1_BID_SPREAD": 10, "M1_SINGLE_SIDE": 6},
                "mt5_hcc_coverage": {"mt5_hcc_ready_count": 18, "mt5_hcc_missing_count": 10},
                "global_max_date_utc": "2024-12-31",
            },
            "alpha_families_5_summary": {"cluster_a_grid_total": 355},
        },
    )
    fr_fsha, fr_doc = put_json(
        "wave5_m1_cluster_a_frozen",
        {
            "schema": "naqex-wave5-m1-cluster-a-frozen-v1",
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "finalist_count": 6,
        },
    )
    m1_sum_fsha, m1_sum_doc = put_json(
        "wave5_m1_arena_summary",
        {
            "schema": "naqex-wave5-m1-arena-summary-v1",
            "hard_invariants": dict(inv_base),
            "cluster_a_summary": {"cluster_a_frozen_sha256": fr_doc["cluster_a_frozen_sha256"]},
            "port_v5_accretion": {"port_v5_tapes_npz_sha256": npz_sha},
        },
    )
    put_json(
        "w5_m1_arena_receipt",
        {
            "schema": "naqex-wave5-m1-arena-receipt-v1",
            "worker": "w5-m1-arena",
            "verdict": "PASS_W5_G07_W5_G08_W5_G09_HONEST_ZERO_ADDITIONS",
            "hard_invariants": dict(inv_base),
            "arena_summary_report_sha256": m1_sum_doc["report_sha256"],
            "cluster_a_summary": {
                "m_total": 355,
                "budget_cap": 360,
                "finalist_count": 6,
                "cluster_a_frozen_sha256": fr_doc["cluster_a_frozen_sha256"],
            },
            "cluster_b_summary": {
                "tier_1_prop_survivor_count": 0,
                "alpha_bench_reserve_count": 1,
                "killed_on_cluster_b_count": 5,
            },
            "cluster_b_finalists_compact": [
                {
                    "candidate_id": "F5D_US30_TO_UK100_CNV_L2_LB30_A",
                    "family_id": "F5D_CROSS_ASSET_LEAD_LAG",
                    "symbol": "UK100",
                    "leader_symbol": "US30",
                    "n_trades_b": 414,
                    "sharpe_daily_b": 0.4569,
                    "pf_1x_b": 1.1317,
                    "cost_breakeven_mult": 9.92,
                    "corr_vs_port_7e": -0.0105,
                    "failed_gates": ["G1_bh_fdr_q_le_0_10"],
                    "tier_classification": "ALPHA_BENCH_RESERVE",
                }
            ],
            "compute_execution": {"overall_x13_offload_pct": 100.0},
            "port_v5_accretion": {
                "port_v5_equals_port_7e": True,
                "n_core7_engines": 7,
                "n_added_engines": 0,
                "port_v5_tapes_npz_sha256": npz_sha,
            },
            "deliverables": {
                ".runtime/offensive5/alpha/wave5_m1_arena_summary.json": {"sha256": m1_sum_fsha},
                ".runtime/offensive5/alpha/wave5_m1_cluster_a_frozen.json": {"sha256": fr_fsha},
                ".runtime/offensive5/alpha/port_v5_tapes.npz": {"sha256": npz_sha},
            },
        },
    )

    # 3. Wave 2A ML v1.05
    oof_fsha, _ = put_json(
        "wave5_ml_oof_series",
        {
            "schema_version": "naqex-wave5-ml-oof-series-v1",
            "holdout_cutoff_date": "2024-12-31",
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "daily_series": {"dates": ["2018-10-01", "2024-12-31"]},
        },
    )
    _, ml_sum_doc = put_json(
        "wave5_ml_arena_summary",
        {
            "schema_version": "naqex-wave5-v105-ml-arena-v1",
            "verdict": "REJECT_V105_ML_KEEP_V103",
            "hard_invariants": dict(inv_base),
        },
    )
    put_json(
        "w5_ml_v105_arena_receipt",
        {
            "schema": "naqex-wave5-ml-v105-arena-receipt-v1",
            "worker": "w5-ml-features",
            "verdict": "REJECT_V105_ML_KEEP_V103",
            "approval_tag": "RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED",
            "closes_findings": ["W4-RT1-P1-01"],
            "hard_invariants": dict(inv_base),
            "budget": {"recorded_trials": 36, "max_trials": 48, "promoted_trials": 0},
            "feature_alignment_w4_rt1_p1_01": {"n_aligned_candidate_features": 20},
            "guardrail_proofs": {
                "ftmo_m1_zero_bit_drift_causality": {"bit_exact_zero_drift": True},
                "rolling_dd_1x_phase_invariance": {"max_abs_diff_pct_pts": 0.0},
            },
            "head_to_head": {
                "v105_ml_filter": {
                    "best_trial_id": "w5_05_lgbm",
                    "best_family": "lightgbm",
                    "pf_1x": 1.1887,
                    "ev_r_1x": 0.0559,
                    "max_dd_pct_1x": 5.70,
                    "slippage_breakeven_24m": 1.6515,
                    "float32_decision_agreement": 1.0,
                    "verdict": "REJECT_V105_ML_KEEP_V103",
                    "float32_cliff_rejected_trials": [{}, {}, {}, {}],
                },
                "v105_ml_asymfloor": {
                    "best_trial_id": "w5_30_lgbm",
                    "best_family": "lightgbm",
                    "pf_1x": 1.1687,
                    "ev_r_1x": 0.0534,
                    "max_dd_pct_1x": 5.75,
                    "slippage_breakeven_24m": 1.6338,
                    "head_to_head_verdict": "REJECT_ASYMFLOOR_KEEP_V103",
                },
            },
            "deliverables": {
                "onnx_sha256": onnx_sha,
                "summary_report_sha256": ml_sum_doc["report_sha256"],
            },
            "export_artifacts": {
                "n_features_selected": 8,
                "onnx_export": {"onnx_sha256": onnx_sha},
                "parity_500_csv": {"csv_sha256": p500_sha},
                "oof_series_sha256": oof_fsha,
                "ref_2024_ftmo_ml_enabled": {"csv_sha256": ref24_sha},
            },
        },
    )

    # 4. Wave 2C Modular MT5
    put_json(
        "w5_modular_mt5_receipt",
        {
            "schema": "naqex-wave5-modular-v105-mt5-cert-receipt-v1",
            "worker": "w5-modular-mt5",
            "verdict": "CERTIFIED_PASS_W5_G10_G12_G15",
            "closes_findings": ["W4-RT1-P1-01", "W4G05-F01"],
            "mt5_procs_after": 0,
            "hard_invariants": dict(inv_base),
            "gates": {"all_ok": True},
            "metaeditor_compiles": {
                "Naqex_Master_Modular_v105": {
                    "errors": 0,
                    "warnings": 0,
                    "clean_zero": True,
                    "mq5_sha256": "a" * 64,
                    "ex5_sha256": "b" * 64,
                    "ex5_bytes": 206890,
                }
            },
            "w5_g12_parity500": {
                "onnx_model": {"sha256": onnx_sha, "zipmap_node_count": 0},
                "mt5_probe_run": {"onnx_api_version": "1.25.1", "nan_blocked": True, "inf_blocked": True},
                "four_way_parity_500": {
                    "passed": True,
                    "n_vectors": 500,
                    "tolerance": 1e-5,
                    "overall_max_abs_err": 5.9e-8,
                    "all_decision_agreements_100pct": True,
                    "pairwise": {"py_lgbm_vs_mt5_onnx": {"max_abs_err": 5.9e-8}},
                },
            },
            "w5_g15_7e_compat": {
                "modular_v105_7e_compat": {
                    "onnx_sha256": onnx_sha,
                    "metrics": {"profit_factor": 1.15, "equity_dd_pct": 4.09, "swap_total_usd": 0.0},
                },
                "comparison_vs_v103": {
                    "exact_cent_and_trade_match": True,
                    "baseline_trades": 469,
                    "candidate_trades": 469,
                    "delta_trades": 0,
                    "baseline_net_pnl_usd": 616.87,
                    "candidate_net_pnl_usd": 616.87,
                    "delta_net_pnl_usd": 0.0,
                },
            },
            "w5_g10_live_feature_parity": {
                "ref_2024_features_csv_sha256": ref24_sha,
                "modular_v105_ml_onnx": {
                    "onnx_sha256": onnx_sha,
                    "metrics": {"trades": 343, "net_pnl_usd": 586.17, "profit_factor": 1.19, "equity_dd_pct": 4.58},
                    "log_telemetry": {"ml_blocked": 127, "ml_passed": 650},
                },
                "modular_v105_ml_pure_mql5": {"onnx_sha256": onnx_sha},
                "reconcile_onnx_vs_python_ref": {
                    "passed": True,
                    "matched_signals_total": 777,
                    "exact_timestamp_matched": 777,
                    "market_and_structural_f0_f6_max_abs_err": 2.2e-7,
                    "overall_unit_normalized_feature_max_abs_err": 2.9e-5,
                    "f7_pp_raw_max_abs_err": 0.0011,
                    "max_abs_p_win_err": 5.7e-8,
                    "decision_agreement_ratio": 1.0,
                },
                "reconcile_pure_vs_python_ref": {"passed": True, "max_abs_p_win_err": 0.0},
                "comparison_pure_vs_onnx": {"exact_cent_and_trade_match": True},
            },
            "bellman_dp_p1_smoke": {
                "onnx_sha256": onnx_sha,
                "metrics": {"trades": 471, "net_pnl_usd": 1216.15, "profit_factor": 1.13, "equity_dd_pct": 7.21},
                "log_telemetry": {"dp_tiers": 6, "error_lines_count": 0},
            },
        },
    )

    # 5. Wave 2B-DP & 2C-Python Alpha Factory
    dp_fsha, dp_doc = put_json(
        "bellman_dp_schedule",
        {
            "schema_version": "naqex-wave5-bellman-dp-schedule-v1",
            "hard_invariants": dict(inv_no_spend),
            "causal_split": {"train_cluster_a": {"n_days": 666}, "eval_cluster_b_oos": {"n_days": 898}},
            "cluster_b_ablation": {
                "combined_P1_P2": {
                    "BELLMAN_DP_6TIER_SCHEDULE": {
                        "combined_pass_pct": 40.71,
                        "combined_fail_pct": 10.75,
                        "combined_pending_pct": 48.54,
                    }
                },
                "combined_P1_P2_extended_unlimited_view": {
                    "BELLMAN_DP_6TIER_SCHEDULE": {
                        "combined_pass_pct": 60.29,
                        "combined_fail_pct": 22.89,
                        "combined_pending_pct": 16.82,
                    }
                },
            },
        },
    )
    ledger_raw = _build_valid_ledger_doc()
    ledger_fsha, _ = council.write_json_lf(root / spec_map["alpha_factory_ledger"].rel_path, ledger_raw)

    drills_fsha, drills_doc = put_json(
        "alpha_factory_e2e_drills",
        {
            "schema_version": "naqex-wave5-alpha-factory-e2e-drills-v1",
            "verdict": "PASS_W5_G16_AND_W5_G17_ALL_5_DRILLS_GREEN",
            "all_5_drills_passed": True,
            "drills_passed": 5,
            "drills_total": 5,
            "decay_backend_used": "live_decay_monitor",
            "hard_invariants": {**inv_no_spend, "auto_deploy_permitted": False},
            "drills": {
                "DRILL_1_NORMAL_GREEN": {"passed": True, "evaluated_engines": 7, "proposals_emitted": 0},
                "DRILL_2_AMBER_HALVED": {
                    "passed": True,
                    "target_engine": "E3_GBPUSD_VH",
                    "target_weight_mult_after": 0.5,
                    "proposal": {"owner_approval_status": "PENDING_OWNER_APPROVAL"},
                },
                "DRILL_3_RED_WITH_BENCH_SWAP": {
                    "passed": True,
                    "target_engine": "E6_EURJPY_VOLCOMP",
                    "selected_replacement": "B1_XAGUSD_ORTH_VOL",
                    "rejected_candidate_state": "KILLED",
                    "proposal": {"owner_approval_status": "PENDING_OWNER_APPROVAL"},
                    "ledger_integrity": {
                        "ledger_root_sha256": ledger_raw["ledger_root_sha256"],
                        "report_sha256": ledger_raw["report_sha256"],
                    },
                },
                "DRILL_4_RED_EMPTY_BENCH_FAIL_CLOSED": {
                    "passed": True,
                    "unverified_candidate_state": "DISCOVERED",
                    "proposal": {"action_type": "HALT_ONLY_EMPTY_BENCH"},
                },
                "DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER": {
                    "passed": True,
                    "cases_tested": 8,
                    "cases_rejected_fail_closed": 8,
                },
            },
        },
    )
    put_json(
        "w5_dp_closedloop_receipt",
        {
            "schema": "naqex-wave5-dp-closedloop-receipt-v1",
            "worker": "w5-dp-closedloop",
            "verdict": "PASS_W5_G13_W5_G16_W5_G17",
            "hard_invariants": dict(inv_base),
            "deliverables": {
                ".runtime/offensive5/pareto/bellman_dp_schedule.json": {"sha256": dp_fsha},
                ".runtime/offensive5/factory/alpha_factory_ledger.json": {"sha256": ledger_fsha},
                ".runtime/offensive5/factory/alpha_factory_e2e_drills.json": {"sha256": drills_fsha},
            },
            "w5_g13_bellman_dp_summary": {
                "anti_martingale_verified": True,
                "honest_verdict_6m": "BASELINES_HOLD_EDGE",
                "honest_takeaway": "Strict Pareto tradeoff.",
                "cluster_b_ablation_6m_126d": {},
                "cluster_b_ablation_12m_252d_unlimited": {},
                "schedule_report_sha256": dp_doc["report_sha256"],
            },
            "w5_g16_g17_closed_loop_summary": {
                "ledger_report_sha256": ledger_raw["report_sha256"],
                "ledger_root_sha256": ledger_raw["ledger_root_sha256"],
                "drills_report_sha256": drills_doc["report_sha256"],
            },
        },
    )

    # 6. Wave 2B Spectrum MC
    tier_a_core = [
        _make_synthetic_tier_a_row(sched, contract, fric, "CORE_PORT_7E")
        for sched in council.EXPECTED_SPECTRUM_SCHEDULES
        for contract in ("ftmo_standard_10k", "ftmo_standard_100k")
        for fric in (1.0, 1.5, 2.0)
    ]
    tier_a_oof = [
        _make_synthetic_tier_a_row(sched, contract, fric, cohort)
        for cohort in ("PORT_7E_OOF_CONTROL", "V105_ML_FILTER", "V105_ML_ASYMFLOOR")
        for sched in ("T3_BALANCED_EV", "BELLMAN_DP_6TIER")
        for contract in ("ftmo_standard_10k", "ftmo_standard_100k")
        for fric in (1.0, 1.5, 2.0)
    ]
    part5 = {h: {"pass_pct": 70.0, "fail_pct": 20.0, "pending_pct": 10.0} for h in council.PARETO_HORIZONS}
    tier_b_cases = [
        {
            "schedule_id": prof,
            "case_id": f"B{bm}M__M{idx}__P1",
            "bankroll_m_vnd": bm,
            "friction_mult": fric,
            "monthly_pass_fail_pending": copy.deepcopy(part5),
            "p1_pass_rate_pct": 80.0,
            "p1_fail_rate_pct": 15.0,
            "p1_pending_rate_pct": 5.0,
            "p2_pass_rate_pct": 85.0,
            "p2_fail_rate_pct": 10.0,
            "p2_pending_rate_pct": 5.0,
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
        }
        for prof in council.EXPECTED_FLEET_PROFILES
        for fric in (1.0, 1.5)
        for bm in council.EXPECTED_BANKROLL_TIERS_M_VND
        for idx in range(9)
    ]
    rep_pareto = [
        {
            "schedule_id": prof,
            "bankroll_m_vnd": bm,
            "friction_mult": fric,
            "ev_per_1_vnd_fee_36m": 12.5,
            "fn12_blowup_pct": 0.01,
            "p_bankroll_ruin_pct": 0.05,
            "p_net_le_0_24m_pct": 14.0,
            "uncond_med_pay1_cap730": 225.0,
            "p1_pass_12m_pct": 81.5,
            "p2_pass_12m_pct": 88.2,
            "pass_12m_pct": 70.0,
            "median_24m_net_vnd": 150_000_000.0,
            "median_36m_net_vnd": 900_000_000.0,
            "median_36m_net_usd": 35_000.0,
        }
        for prof in council.EXPECTED_FLEET_PROFILES
        for bm in council.EXPECTED_BANKROLL_TIERS_M_VND
        for fric in (1.0, 1.5)
    ]
    _, ac_doc = put_json(
        "mc_spectrum_all_cases",
        {
            "schema_version": "naqex-wave5-mc-spectrum-all-cases-v1",
            "hard_invariants": dict(inv_base),
            "tier_a_core_cases": tier_a_core,
            "tier_a_oof_ml_cases": tier_a_oof,
            "tier_b_fleet_cases": tier_b_cases,
        },
    )
    intraday_4 = [
        {
            "schedule_id": sched,
            "contract_id": contract,
            "modes": {
                "daily_close_only_1_0x": {"p1_pass_pct": 70.0, "p1_fail_pct": 30.0, "p1_pending_pct": 0.0},
                "trade_level_intraday_1_0x": {"p1_pass_pct": 65.0, "p1_fail_pct": 35.0, "p1_pending_pct": 0.0},
            },
        }
        for sched in ("T4_TURBO_FAST", "T5_MAX_THROTTLE_YOLO")
        for contract in ("ftmo_standard_10k", "ftmo_standard_100k")
    ]
    tier_overview = {
        prof: {
            "mean_ev_per_fee_36m_1x": 12.5,
            "mean_fn12_blowup_1x_pct": 0.01,
            "mean_ruin_36m_1x_pct": 0.5,
            "mean_uncond_pay1_1x_days": 230.0,
            "grades_1x": {"GOOD": 60, "ADEQUATE": 21},
        }
        for prof in council.EXPECTED_FLEET_PROFILES
    }
    ms_fsha, ms_doc = put_json(
        "mc_spectrum_summary",
        {
            "schema_version": "naqex-wave5-mc-spectrum-summary-v1",
            "all_cases_sha256": ac_doc["all_cases_sha256"],
            "hard_invariants": dict(inv_base),
            "tier_a_core_summary": tier_a_core,
            "tier_a_oof_ml_summary": tier_a_oof,
            "oof_ml_deltas": [{"variant": "v105_ml_filter"}],
            "tier_b_tier_overview": tier_overview,
            "tier_b_representative_pareto_by_tier_bankroll": rep_pareto,
            "intraday_trade_dd_audit": intraday_4,
            "shared_path_rho_proof": {"shared_path_rho_gt_0_999": True, "independent_rho_near_zero": True},
            "wave4_vs_wave5_sql_comparison": {"bankroll_gated_p2_1x_comparison": []},
            "upstream_provenance": {
                "taxonomy_sha256": tax_sha,
                "usd_vnd_rate": 25765.94,
                "bellman_dp": {"sha256": dp_fsha},
                "ml_oof": {"sha256": oof_fsha},
                "port_v5": {"m1_arena_summary_sha256": m1_sum_fsha, "port_v5_npz_sha256": npz_sha},
            },
        },
    )
    put_json(
        "w5_spectrum_mc_receipt",
        {
            "schema": "naqex-wave5-spectrum-mc-receipt-v1",
            "worker": "w5-spectrum-mc",
            "verdict": "PASS_W5_G14",
            "hard_invariants": dict(inv_base),
            "summary_sha256": ms_fsha,
            "report_sha256": ms_doc["report_sha256"],
            "all_cases_sha256": ac_doc["all_cases_sha256"],
        },
    )

    if include_trader_ui:
        tui_doc = {
            "schema": "naqex-wave5-trader-ui-receipt-v1",
            "worker": "w5-trader-ui",
            "gate": "W5-G21",
            "verdict": "PASS_W5_G21_TRADER_PROP_FLEET_WAVE5_UPGRADE",
            "hard_invariants": dict(inv_no_spend),
        }
        _write_self_hashed(
            root / council.CONCURRENT_TRADER_UI_SPEC.rel_path,
            tui_doc,
            field="report_sha256",
            mode="canonical_ascii",
        )

    return root


# ---------------------------------------------------------------------------
# 1. Pure Offline CI-Safe Tests (`-m "not local_cache"`)
# ---------------------------------------------------------------------------


class TestWave5MasterCouncilOfflineCI:
    def test_static_ast_hygiene_zero_bare_asserts_crlf_bom_jsonschema_and_popup_guard(self) -> None:
        targets = (
            REPO_ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave5" / "wave5_master_council.py",
            Path(__file__).resolve(),
        )
        for fp in targets:
            raw = fp.read_bytes()
            _check(b"\r\n" not in raw, f"{fp.name} must have 0 CRLF")
            _check(not raw.startswith(b"\xef\xbb\xbf"), f"{fp.name} must have 0 BOM")
            tree = ast.parse(raw.decode("utf-8"), filename=str(fp))
            for node in ast.walk(tree):
                _check(
                    not isinstance(node, ast.Assert),
                    f"bare assert forbidden in {fp.name}:{getattr(node, 'lineno', 0)}",
                )
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        _check(not alias.name.startswith("jsonschema"), f"jsonschema forbidden in {fp.name}")
                elif isinstance(node, ast.ImportFrom):
                    _check(
                        not (node.module or "").startswith("jsonschema"),
                        f"jsonschema forbidden in {fp.name}",
                    )
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
                    if node.func.attr == "run" and isinstance(node.func.value, ast.Name):
                        if node.func.value.id == "subprocess":
                            kw_names = {kw.arg for kw in node.keywords}
                            _check(
                                "creationflags" in kw_names,
                                f"subprocess.run without creationflags in {fp.name}:{node.lineno}",
                            )

    def test_lf_normalized_immutables_and_workspace_hard_invariants_fail_closed(self, tmp_path: Path) -> None:
        ws = tmp_path / "ws_inv"
        # Create CRLF file and verify LF-normalized SHA matches pure-LF SHA
        imm_rel = "AGENTS.md"
        lf_content = b"# Naqex\nline2\n"
        crlf_content = b"# Naqex\r\nline2\r\n"
        (ws / imm_rel).parent.mkdir(parents=True, exist_ok=True)
        (ws / imm_rel).write_bytes(crlf_content)
        expected_lf_sha = hashlib.sha256(lf_content).hexdigest()
        obs_len, obs_sha = council.compute_lf_normalized_sha256(ws / imm_rel)
        _check(obs_len == len(lf_content) and obs_sha == expected_lf_sha, "LF normalization mismatch on CRLF file")

        # Populate 41 dummy quant_core/*.py files, empty exports/ & private_vault/, and UI schema.json
        qc_dir = ws / "tooling" / "ai-engines" / "quant_core"
        qc_dir.mkdir(parents=True)
        for i in range(41):
            (qc_dir / f"mod_{i:02d}.py").write_bytes(b"pass\n")
        (ws / "tooling" / "ai-engines" / "exports").mkdir(parents=True)
        (ws / "private_vault").mkdir(parents=True)
        schema_dst = ws / "UI" / "contracts" / "evaluation-scorecard" / "1.0.0" / "schema.json"
        schema_dst.parent.mkdir(parents=True)
        schema_dst.write_bytes(ec.DEFAULT_SCORECARD_SCHEMA_PATH.read_bytes())

        res = council.verify_workspace_hard_invariants(
            ws,
            expected_immutables={imm_rel: (len(lf_content), expected_lf_sha)},
            mt5_process_lister=lambda: [],
        )
        _check(res["immutables_11_of_11_untouched"] is True, "workspace invariants must pass")
        _check(res["quant_core_py_count"] == 41, "quant_core count must be 41")
        _check(res["mt5_procs_count"] == 0, "mt5_procs must be 0")
        _check(res["projects_trader_git_clean"] is None, "synthetic workspace has no projects/trader git repo")

        # Verify MODE_A BelowNormal 64-bit ctypes prototype succeeds cleanly on Windows
        mode_a = council.enforce_mode_a_below_normal()
        _check(mode_a["policy_mode"] == "MODE_A_OWNER_ACTIVE", f"unexpected mode_a: {mode_a}")
        _check(mode_a["priority_class_hex"] == "0x4000", f"unexpected priority class: {mode_a}")
        _check(mode_a["gpu_budget_pct"] == 0, f"gpu budget must be 0: {mode_a}")
        if sys.platform == "win32":
            _check(mode_a["priority_applied"] is True, f"64-bit SetPriorityClass must apply cleanly: {mode_a}")
            _check(mode_a["win_error"] is None, f"64-bit SetPriorityClass win_error must be None: {mode_a}")

        # Fail closed on active MT5 process
        with pytest.raises(council.SafetyInvariantViolationError, match="MT5_PROCS_NON_ZERO"):
            council.verify_workspace_hard_invariants(
                ws,
                expected_immutables={imm_rel: (len(lf_content), expected_lf_sha)},
                mt5_process_lister=lambda: ['"terminal64.exe","1234"'],
            )

        # Fail closed on .ex5 in exports/
        bad_ex5 = ws / "tooling" / "ai-engines" / "exports" / "leak.ex5"
        bad_ex5.write_bytes(b"EX5")
        with pytest.raises(council.SafetyInvariantViolationError, match="EXPORTS_EX5_FORBIDDEN"):
            council.verify_workspace_hard_invariants(
                ws,
                expected_immutables={imm_rel: (len(lf_content), expected_lf_sha)},
                mt5_process_lister=lambda: [],
            )
        bad_ex5.unlink()

        # Fail closed on 1-byte immutable tamper
        (ws / imm_rel).write_bytes(b"# Naqex\nTAMPERED\n")
        with pytest.raises(council.TamperedArtifactError, match="IMMUTABLE_TAMPERED"):
            council.verify_workspace_hard_invariants(
                ws,
                expected_immutables={imm_rel: (len(lf_content), expected_lf_sha)},
                mt5_process_lister=lambda: [],
            )

    def test_safety_scanner_bare_dollar_partition_and_ledger_chain_guards(self) -> None:
        spec = council.ArtifactSpec("test_art", "g", ("W5-G18",), "x.json")
        good_doc = {
            "holdout_rows_analysed": 0,
            "order_send_count": 0,
            "order_send_capable": False,
            "spend_vnd": 0,
            "holdout_cutoff_date": "2024-12-31",
            "dev_cutoff_sec": 1735689600,
            "auto_deploy_permitted": False,
        }
        hits = council.scan_and_enforce_safety_invariants(good_doc, spec=spec)
        _check(hits["holdout_rows_analysed_occurrences"] == 1, "expected 1 holdout hit")

        # Holdout > 0, cutoff >= 2025, OrderSend != 0, bool OrderSend, Spend > 0, auto_deploy True
        with pytest.raises(HoldoutLockError):
            council.scan_and_enforce_safety_invariants({**good_doc, "holdout_rows_analysed": 1}, spec=spec)
        with pytest.raises(HoldoutLockError):
            council.scan_and_enforce_safety_invariants({**good_doc, "holdout_cutoff_date": "2025-01-01"}, spec=spec)
        with pytest.raises(council.SafetyInvariantViolationError):
            council.scan_and_enforce_safety_invariants({**good_doc, "order_send_count": 1}, spec=spec)
        with pytest.raises(council.SafetyInvariantViolationError):
            council.scan_and_enforce_safety_invariants({**good_doc, "order_send_count": False}, spec=spec)
        with pytest.raises(council.SafetyInvariantViolationError):
            council.scan_and_enforce_safety_invariants({**good_doc, "order_send_capable": True}, spec=spec)
        with pytest.raises(council.SafetyInvariantViolationError):
            council.scan_and_enforce_safety_invariants({**good_doc, "spend_vnd": 1000}, spec=spec)
        with pytest.raises(council.SafetyInvariantViolationError):
            council.scan_and_enforce_safety_invariants({**good_doc, "auto_deploy_permitted": True}, spec=spec)

        # Bare dollar guard & 100% partition guard
        with pytest.raises(council.MalformedArtifactError, match="BARE_DOLLAR_FORBIDDEN"):
            council.assert_no_bare_dollar({"note": "fee is $155"})
        with pytest.raises(council.ArithmeticDriftError, match="PARTITION_SUM_NOT_100"):
            council._verify_partition_triple(60.0, 20.0, 19.0, context="bad_sum")

        # Alpha Factory ledger hash chain guard
        ledger_ok = _build_valid_ledger_doc()
        res_ok = council._verify_alpha_factory_ledger_chain(ledger_ok)
        _check(res_ok["chain_verified"] is True and res_ok["entry_count"] == 2, "valid ledger must verify")
        ledger_bad = copy.deepcopy(ledger_ok)
        ledger_bad["entries"][1]["event"] = "TAMPERED"
        with pytest.raises(council.TamperedArtifactError, match="ALPHA_LEDGER_ENTRY_HASH_MISMATCH"):
            council._verify_alpha_factory_ledger_chain(ledger_bad)

    def test_synthetic_25_artifacts_reconcile_tamper_resync_and_pydantic_scorecards(self, tmp_path: Path) -> None:
        # 1. Pending concurrent lane (w5_trader_ui_receipt absent)
        ws = _build_synthetic_wave5_workspace(tmp_path, include_trader_ui=False)
        docs, ledger, cross_checks, concurrent = council.load_and_verify_wave5_artifacts(ws)
        _check(len(ledger) == len(council.RAW_ARTIFACT_SPECS) == 25, f"expected 25 artifacts, got {len(ledger)}")
        _check(len(cross_checks) == len(council.CROSS_ARTIFACT_SHA256_LINKS) + 1 == 40, "expected 40 cross-links")
        _check(
            concurrent["w5_trader_ui_receipt"]["status"] == "PENDING_CONCURRENT_LANE",
            "absent trader UI receipt must report PENDING_CONCURRENT_LANE",
        )

        # --require-trader-ui must fail closed when absent
        with pytest.raises(council.MissingArtifactError, match="MISSING_TRADER_UI_RECEIPT"):
            council.load_and_verify_wave5_artifacts(ws, require_trader_ui=True)

        # Verify domain reconcilers + emitted Pydantic v2 EvaluationScorecards on synthetic docs
        single = council.reconcile_single_ticket_spectrum(docs)
        fleet = council.reconcile_fleet_9bankroll(docs)
        mt5 = council.reconcile_mt5_build_6230_parity(docs)
        factory = council.reconcile_alpha_factory_and_arenas(docs)
        emitted_scs = council.build_and_validate_emitted_scorecards(
            docs, taxonomy_path=ws / "tooling" / "ai-engines" / "configs" / "ssot" / "evaluation_taxonomy.json"
        )
        _check(len(emitted_scs) == 9, f"expected 9 emitted scorecards, got {len(emitted_scs)}")
        for sc_key, sc_dict in emitted_scs.items():
            model = ec.EvaluationScorecard.model_validate(sc_dict)
            _check(model.holdout_rows_analysed == 0 and model.order_send_count == 0, f"bad safety on {sc_key}")
        _check(single["tier_a_core_case_count"] == 54, "expected 54 single-ticket core cases")
        _check(fleet["total_fleet_cases_verified"] == 972, "expected 972 fleet cases")
        _check(mt5["w5_g15_modular_7e_compat"]["exact_cent_and_trade_match"] is True, "expected 7E exact match")
        _check(factory["alpha_factory_e2e_drills_w5_g16_g17"]["all_5_drills_passed"] is True, "expected 5/5 drills")

        # 2. Tamper 1 byte in self-hashed artifact -> TamperedArtifactError
        t0_path = ws / ".runtime" / "offensive5" / "audits" / "w5_t0_env_receipt.json"
        orig_t0 = t0_path.read_bytes()
        t0_doc = json.loads(orig_t0.decode("utf-8"))
        t0_doc["verdict"] = "TAMPERED"
        council.write_json_lf(t0_path, t0_doc)
        with pytest.raises(council.TamperedArtifactError, match="SELF_HASH_MISMATCH"):
            council.load_and_verify_wave5_artifacts(ws)
        t0_path.write_bytes(orig_t0)

        # 3. Tamper cross-artifact ONNX binary -> TamperedArtifactError
        onnx_path = ws / ".runtime" / "offensive5" / "ml" / "naqex_v105_lgbm.onnx"
        orig_onnx = onnx_path.read_bytes()
        onnx_path.write_bytes(orig_onnx + b"X")
        with pytest.raises(council.TamperedArtifactError, match="CROSS_ARTIFACT_SHA256_MISMATCH"):
            council.load_and_verify_wave5_artifacts(ws)
        onnx_path.write_bytes(orig_onnx)

        # 4. --resync locks in w5_trader_ui_receipt.json once present (26 artifacts!)
        ws_ui = _build_synthetic_wave5_workspace(tmp_path / "with_ui", include_trader_ui=True)
        _docs2, ledger2, _links2, concurrent2 = council.load_and_verify_wave5_artifacts(ws_ui, require_trader_ui=True)
        _check(len(ledger2) == 26, f"expected 26 artifacts with trader UI receipt, got {len(ledger2)}")
        _check(concurrent2["w5_trader_ui_receipt"]["status"] == "RECONCILED", "trader UI receipt must lock in")
        _check(concurrent2["w5_trader_ui_receipt"]["self_hash_verified"] is True, "trader UI self-hash verified")

        # 5. Byte-identical receipt writer writes clean LF / 0-BOM identical copies in tmp_path
        sample_receipt = {"schema": council.SCHEMA_COUNCIL_RECEIPT, "ok": True}
        sample_receipt["report_sha256"] = council.compute_canonical_report_sha256(sample_receipt)
        audit_p = tmp_path / "out" / "audit.json"
        drop_p = tmp_path / "out" / "dropbox.json"
        wr = council.write_byte_identical_receipts(sample_receipt, audit_path=audit_p, dropbox_path=drop_p)
        _check(wr["byte_identical"] is True, "receipts must be byte-identical")
        _check(audit_p.read_bytes() == drop_p.read_bytes(), "raw bytes must match identically")
        _check(b"\r\n" not in audit_p.read_bytes(), "receipt must have 0 CRLF")


# ---------------------------------------------------------------------------
# 2. Local Disk Reconciliation & SSOT SHA Invariance (`@pytest.mark.local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
class TestWave5MasterCouncilLocalDiskSSOT:
    def test_local_workspace_11_immutables_lf_sha_and_hard_invariants(self) -> None:
        res = council.verify_workspace_hard_invariants(REPO_ROOT)
        _check(res["immutables_11_of_11_untouched"] is True, "11/11 immutables must be untouched")
        _check(res["immutables_checked_count"] == 11, "must verify all 11 immutables")
        _check(res["quant_core_py_count"] == 41, "quant_core/*.py count must be 41")
        _check(res["exports_ex5_count"] == 0, "exports/ must have 0 .ex5")
        _check(res["private_vault_ex5_count"] == 0, "private_vault/ must have 0 .ex5")
        _check(res["mt5_procs_count"] == 0, "MT5_PROCS must be 0")
        _check(res["ui_scorecard_schema_exact_match"] is True, "UI schema.json must match Pydantic v2 export")

    def test_local_full_reconciliation_and_ssot_sha_invariance(self, tmp_path: Path) -> None:
        ssot_path = council.DEFAULT_MASTER_METRICS_PATH
        _check(ssot_path.is_file(), f"Missing canonical SSOT file on disk: {ssot_path}")
        sha_before = council.compute_file_sha256(ssot_path)

        # Verify on-disk SSOT file directly
        disk_ver = council.verify_master_metrics_file(ssot_path)
        _check(disk_ver["verified"] is True, "on-disk wave5_master_metrics.json failed verification")
        _check(disk_ver["file_sha256"] == sha_before, "disk SHA mismatch")

        # Run full live reconciliation with write_output_path=None AND into tmp_path (NEVER mutating .runtime/)
        in_mem = council.build_wave5_master_metrics(REPO_ROOT, write_output_path=None)
        tmp_out = tmp_path / "wave5_master_metrics_copy.json"
        council.build_wave5_master_metrics(REPO_ROOT, write_output_path=tmp_out)
        tmp_ver = council.verify_master_metrics_file(tmp_out)
        _check(tmp_ver["verified"] is True, "tmp copy verification failed")

        # Assert exact Wave 5 reconciliation counts, DuckDB catalog integrity, and SQL W4 vs W5 separation
        _check(in_mem["reconciled_artifact_count"] >= 25, "must reconcile >= 25 Wave 5 artifacts")
        _check(in_mem["cross_artifact_sha256_links_verified"] == 40, "must verify 40 cross-artifact SHA links")
        _check(
            in_mem["hard_invariants"]["wave5_master_council_mutated_projects_trader"] is False,
            "council must declare wave5_master_council_mutated_projects_trader=False",
        )
        _check(
            "projects_trader_untouched" not in in_mem["hard_invariants"],
            "hardcoded projects_trader_untouched must be removed",
        )
        git_clean_val = in_mem["hard_invariants"]["projects_trader_git_clean"]
        _check(
            isinstance(git_clean_val, bool),
            f"projects_trader_git_clean must be live bool on workspace: {git_clean_val!r}",
        )

        cat_v = in_mem["unified_catalog_verification"]
        _check(cat_v["verified"] is True, "DuckDB catalog must be verified")
        _check(cat_v["legacy_trials_distinct_count"] == 1342, "expected 1,342 distinct legacy trials")
        _check(cat_v["mc_cases_catalog_count"] == 1250, "expected 1,250 MC rows")
        _check(
            cat_v["mc_by_campaign"] == {"offensive4": 168, "offensive5_baseline": 20, "offensive5_spectrum": 1062},
            "mc_by_campaign mismatch",
        )
        _check(cat_v["runs_catalog_count"] == 122, "expected 122 runs")
        _check(
            cat_v["pydantic_v2_scorecards_validated"]["all_valid"] is True,
            "all 1,250 MC + 122 run scorecards must be valid",
        )

        sql_cmp = in_mem["wave4_vs_wave5_sql_comparison"]
        _check(
            sql_cmp["wave4_legacy_vs_unified_grade_matrix"] == {
                "DU_DUNG->ADEQUATE": 9,
                "DU_DUNG->BAD": 69,
                "TOT->ADEQUATE": 75,
                "TOT->BAD": 15,
            },
            f"unexpected W4 legacy->unified matrix: {sql_cmp['wave4_legacy_vs_unified_grade_matrix']}",
        )
        _check(len(sql_cmp["paired_162_cell_fleet_sql_deltas"]) == 6, "expected 6 paired SQL fleet profiles")
        for prow in sql_cmp["paired_162_cell_fleet_sql_deltas"]:
            _check(prow["w4_funded_mult"] == 1.25 and prow["w5_funded_mult"] == 1.0, "funded_mult separation violated")
            _check(prow["n_matched_cells"] == 162, "expected 162 matched paired cells")

        # Verify 1-byte tamper detection on live payload
        tampered = copy.deepcopy(in_mem)
        tampered["reconciled_artifact_count"] = 999
        with pytest.raises(council.TamperedArtifactError, match="MASTER_METRICS_TAMPERED"):
            council.verify_master_metrics_payload(tampered)

        # CRITICAL: Assert wave5_master_metrics.json SHA-256 invariance BEFORE vs AFTER pytest!
        sha_after = council.compute_file_sha256(ssot_path)
        _check(sha_after == sha_before, f"SSOT MUTATED BY PYTEST: before={sha_before} after={sha_after}")

    def test_local_byte_identical_receipts_match_ssot(self) -> None:
        audit_p = council.DEFAULT_AUDIT_RECEIPT_PATH
        drop_p = council.DEFAULT_DROPBOX_RECEIPT_PATH
        ssot_p = council.DEFAULT_MASTER_METRICS_PATH
        _check(audit_p.is_file(), f"Missing audit receipt: {audit_p}")
        _check(drop_p.is_file(), f"Missing swarm_dropbox receipt: {drop_p}")

        raw_a = audit_p.read_bytes()
        raw_d = drop_p.read_bytes()
        _check(raw_a == raw_d, "audit and swarm_dropbox receipts must be byte-for-byte identical")
        _check(b"\r\n" not in raw_a and not raw_a.startswith(b"\xef\xbb\xbf"), "receipt must have 0 CRLF / 0 BOM")

        rec = json.loads(raw_a.decode("utf-8"))
        council.assert_no_bare_dollar(rec, context="receipt_disk")
        recomputed = council.compute_canonical_report_sha256(rec)
        _check(rec["report_sha256"] == recomputed, "receipt report_sha256 mismatch")

        ssot_ver = council.verify_master_metrics_file(ssot_p)
        _check(rec["master_metrics_ssot"]["file_sha256"] == ssot_ver["file_sha256"], "receipt SSOT file_sha256 drift")
        _check(
            rec["master_metrics_ssot"]["report_sha256"] == ssot_ver["report_sha256"],
            "receipt SSOT report_sha256 drift",
        )
