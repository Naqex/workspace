"""Unit, federation, backfill, and tamper-detection tests for Wave 5 `evaluation_catalog.py`.

Hard invariants verified (ZERO bare asserts, `python -O` safe):
  1. Every test that writes DuckDB or SQLite runs exclusively inside `tmp_path` so production
     `.runtime/experiments/unified_eval_catalog.duckdb` SHA-256 NEVER mutates during pytest.
  2. Canonical `grade_evaluation_record(...)` works across all 4 inside-out tiers, both eval scopes,
     both pricing regimes, instrumented vs legacy-uninstrumented P1/P2, and emits ordered bottlenecks.
  3. Federated DuckDB catalog creates all 4 tables/views (`runs_catalog`, `mc_cases_catalog`,
     `alpha_registry_catalog`, `legacy_trials_federated_view`), prevents double counting on duplicate
     `wave4_frontier_m36.duckdb::experiments`, and detects direct SQL/DuckDB tampering via `SQLiteRunRegistry`.
  4. `@pytest.mark.local_cache` read-only production verification asserts `1,342` distinct legacy trials,
     `168` Wave 4 MC rows (`81 + 81 + 6`), `profile_id="C10_NEWS_ON"`, `funded_mult=1.25`,
     `UNKNOWN_LEGACY_UNINSTRUMENTED` P1/P2 presentation state, and unchanged production file SHA.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any

import duckdb
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import evaluation_catalog as ec  # noqa: E402

from tooling.run_registry.store import JournalCorruptionError  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit guard immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _make_synthetic_legacy_dbs(root: Path) -> list[dict[str, Any]]:
    """Build 3 miniature legacy DuckDB files mimicking exact production schemas (incl. duplicate frontier table)."""
    db1 = root / "experiments.duckdb"
    con1 = duckdb.connect(str(db1))
    con1.execute(
        """
        CREATE TABLE experiments (
            run_id VARCHAR PRIMARY KEY, git_sha VARCHAR, data_sha VARCHAR,
            strategy_id VARCHAR, family_id VARCHAR, sharpe DOUBLE,
            dsr DOUBLE, pbo DOUBLE, spa_p DOUBLE, npv_usd DOUBLE,
            p_le_zero DOUBLE, p_value DOUBLE, created_utc VARCHAR
        )
        """
    )
    for i in range(5):
        con1.execute(
            "INSERT INTO experiments VALUES ("
            "?, 'abc', 'def', ?, 'off3_fam', ?, 0.5, 0.1, NULL, NULL, NULL, 0.02, '2026-11-27T14:00:00Z')",
            [f"off3-run-{i}", f"strat-{i}", 1.1 + 0.1 * i],
        )
    con1.close()

    db2 = root / "wave4_ml_m48.duckdb"
    con2 = duckdb.connect(str(db2))
    con2.execute(
        """
        CREATE TABLE wave4_ml_m48 (
            trial_seq INTEGER, trial_id VARCHAR, family_name VARCHAR,
            config_hash VARCHAR, oos_label VARCHAR, cutoff_utc VARCHAR,
            n_folds INTEGER, n_features_selected INTEGER, brier_model DOUBLE,
            brier_climatology DOUBLE, brier_skill_score DOUBLE, roc_auc DOUBLE,
            min_engine_retention DOUBLE, overall_retention DOUBLE,
            slippage_breakeven_24m DOUBLE, pf_1x DOUBLE, ev_r_1x DOUBLE,
            max_dd_pct_1x DOUBLE, verdict VARCHAR, holdout_rows_analysed INTEGER,
            order_send_count INTEGER, params_json VARCHAR, metrics_json VARCHAR,
            created_utc VARCHAR
        )
        """
    )
    for i in range(3):
        con2.execute(
            """
            INSERT INTO wave4_ml_m48 VALUES (
                ?, ?, 'lightgbm', 'h', 'CONSUMED_DEV_CLB_TEMPORAL_OOS', '2024-12-31',
                5, 10, 0.24, 0.25, 0.01, 0.55, 0.7, 0.8, 1.9, 1.28, 0.07, 4.9,
                'PROMOTE_V104_ML', 0, 0, '{}', '{}', '2026-11-27T19:00:00Z'
            )
            """,
            [i + 1, f"ml-trial-{i}"],
        )
    con2.close()

    db3 = root / "wave4_frontier_m36.duckdb"
    con3 = duckdb.connect(str(db3))
    # Intentionally include BOTH duplicate `experiments` table AND canonical `wave4_frontier_trials`!
    con3.execute(
        """
        CREATE TABLE experiments (
            run_id VARCHAR PRIMARY KEY, git_sha VARCHAR, data_sha VARCHAR,
            strategy_id VARCHAR, family_id VARCHAR, sharpe DOUBLE,
            dsr DOUBLE, pbo DOUBLE, spa_p DOUBLE, npv_usd DOUBLE,
            p_le_zero DOUBLE, p_value DOUBLE, created_utc VARCHAR
        )
        """
    )
    con3.execute(
        """
        CREATE TABLE wave4_frontier_trials (
            trial_id VARCHAR, family_budget_id VARCHAR, sleeve_id VARCHAR,
            split VARCHAR, params_json VARCHAR, params_sha256 VARCHAR,
            cluster_a_sharpe DOUBLE, cluster_a_calmar DOUBLE, cluster_a_dd DOUBLE,
            cluster_a_cagr DOUBLE, cluster_a_turnover DOUBLE, corr_vs_7e DOUBLE,
            tail_corr_vs_7e DOUBLE, cost_2x_net DOUBLE, cost_breakeven_mult DOUBLE,
            holdout_rows_analysed INTEGER, cluster_b_touched BOOLEAN,
            p_value DOUBLE, created_utc VARCHAR
        )
        """
    )
    for i in range(2):
        tid = f"F01_T{i}"
        con3.execute(
            "INSERT INTO experiments VALUES ("
            "?, 'sha', 'dsha', ?, 'wave4_frontier_m36', 1.0, NULL, NULL, NULL, NULL, NULL, 0.001, "
            "'2026-11-27T18:45:00Z')",
            [tid, f"FRONTIER_01:{tid}"],
        )
        con3.execute(
            """
            INSERT INTO wave4_frontier_trials VALUES (
                ?, 'wave4_frontier_m36', 'FRONTIER_01', 'cluster_a', '{}', 'psha',
                1.0, 0.8, 6.0, 5.0, 4.0, 0.02, 0.05, 10.0, 6.0, 0, false, 0.001, '2026-11-27T18:45:00Z'
            )
            """,
            [tid],
        )
    con3.close()

    return [
        {"source_key": "experiments_core", "db_path": db1, "table_name": "experiments"},
        {"source_key": "wave4_ml_m48", "db_path": db2, "table_name": "wave4_ml_m48"},
        {"source_key": "wave4_frontier_m36", "db_path": db3, "table_name": "wave4_frontier_trials"},
    ]


def _make_synthetic_pareto_json(path: Path) -> Path:
    """Create a Wave 4-shaped Pareto JSON where `profile_id` and `funded_mult` live ONLY in `ssot_provenance`."""

    def _one_case(
        cid: str,
        *,
        fric: float = 1.0,
        ev_fee: float = 5.2,
        blowup: float = 0.25,
        ruin: float = 0.1,
        neg24: float = 34.0,
        pay1: float = 420.0,
        legacy_grade: str = "TOT",
        exec_status: str = "MEASURED_DEMO_EXECUTION",
        contract_id: str | None = None,
    ) -> dict[str, Any]:
        # Deliberately OMIT `profile_id` and `funded_mult` on individual case objects!
        obj: dict[str, Any] = {
            "case_id": cid,
            "resolution_label_vi": "XẤP XỈ CẤP NGÀY",
            "resolution_tag": "APPROX_DAILY_RESOLUTION",
            "evidence_stage": "BACKTEST_DEV_SEALED_LE_2024",
            "execution_status": exec_status,
            "pricing_regime": "ALL_REGULAR_SSOT",
            "order_send_count": 0,
            "holdout_rows_analysed": 0,
            "n_paths": 1000,
            "horizon_days": 756,
            "bankroll_m_vnd": 25,
            "bankroll_vnd": 25_000_000.0,
            "bankroll_usd": 970.27,
            "usd_vnd_rate": 25765.94,
            "concurrency_mode": "CONSERVATIVE_1_TICKET",
            "allocation_policy": "P2_BALANCED_40_40_20",
            "monthly_pass_fail_pending": {
                "12m": {"pass_pct": 52.0, "fail_pct": 0.5, "pending_pct": 47.5, "sum_pct": 100.0},
                "36m": {"pass_pct": 81.0, "fail_pct": 0.1, "pending_pct": 18.9, "sum_pct": 100.0},
            },
            "first_ticket_pass_fail_pending": {
                "12m": {"pass_pct": 50.0, "fail_pct": 5.0, "pending_pct": 45.0, "sum_pct": 100.0},
                "36m": {"pass_pct": 74.0, "fail_pct": 10.0, "pending_pct": 16.0, "sum_pct": 100.0},
            },
            "funded_12m_blowup": {"blowup_12m_pct": blowup, "wilson_95_ub_pct": blowup + 0.2},
            "median_24m_net_vnd": 11_000_000.0,
            "median_36m_net_vnd": 28_000_000.0,
            "median_36m_net_usd": 1086.7,
            "mean_36m_net_vnd": 57_000_000.0,
            "ev_per_1_vnd_fee_24m": ev_fee * 0.7,
            "ev_per_1_vnd_fee_36m": ev_fee,
            "p_net_le_0_24m_pct": neg24,
            "p_net_le_0_36m_pct": 22.0,
            "p_bankroll_ruin_24m_pct": ruin * 0.5,
            "p_bankroll_ruin_pct": ruin,
            "uncond_med_pay1_cal_days_cap365": min(pay1, 365.0),
            "uncond_med_pay1_cal_days_cap730": pay1,
            "law15_position": {"grade_code": legacy_grade, "grade_vi": "Tốt"},
            "strategy_quality": {
                "profit_factor": 1.21,
                "calmar": 0.86,
                "sharpe": 1.23,
                "winrate_pct": 48.6,
                "avg_rr": 1.27,
                "ev_per_trade_r": 0.048,
            },
            "is_pareto_in_tier": True,
            "is_pareto_overall": False,
            "friction_mult": fric,
        }
        if contract_id is not None:
            obj["contract_id"] = contract_id
        return obj

    doc = {
        "schema_version": "naqex-wave4-pareto-81cases-10k-v1",
        "generated_utc": "2026-11-27T18:53:49Z",
        "ssot_provenance": {
            "profile_id": "C10_NEWS_ON",
            "funded_mult": 1.25,
        },
        "sku_funded_diagnostics_1_0x": {
            "ftmo_standard_100k": {
                "funded_mult": 1.25,
                "profit_factor": 1.203,
                "calmar": 0.86,
                "sharpe": 1.232,
            }
        },
        "cases": [
            _one_case("B25M__CONSERVATIVE_1_TICKET__P2_BALANCED_40_40_20", fric=1.0, legacy_grade="TOT"),
            _one_case(
                "B10M__AGGRESSIVE_PARALLEL__P1_RECOUP_FIRST",
                fric=1.0,
                ev_fee=2.1,
                ruin=9.0,
                legacy_grade="DU_DUNG",
            ),
        ],
        "cases_stress_1_5x": [
            _one_case(
                "B25M__CONSERVATIVE_1_TICKET__P2_BALANCED_40_40_20",
                fric=1.5,
                ev_fee=2.8,
                neg24=48.0,
                legacy_grade="DU_DUNG",
            ),
        ],
        "the5ers_reference_rows": [
            _one_case(
                "THE5ERS__the5ers_hs_5k_classic__B10M__CONSERVATIVE_1_TICKET__P2_BALANCED_40_40_20",
                fric=1.0,
                ev_fee=8.7,
                blowup=0.1,
                ruin=0.0,
                neg24=39.0,
                pay1=529.0,
                legacy_grade="TOT",
                exec_status="TERMS_VERIFIED_EXECUTION_UNMEASURED",
                contract_id="the5ers_hs_5k_classic",
            )
        ],
    }
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return path


# ---------------------------------------------------------------------------
# 1. Canonical Grader Tests Across Tiers, Phases, Scopes & Bottlenecks
# ---------------------------------------------------------------------------


class TestCanonicalGrader:
    def test_grade_top1_instrumented_t1_cfd_prop(self) -> None:
        sc = ec.grade_evaluation_record(
            {
                "record_id": "w5-ideal-t1",
                "domain_tier": "T1_CFD_PROP",
                "eval_scope": "MULTI_ACCOUNT_FLEET",
                "pricing_regime": "ALL_REGULAR_SSOT",
                "evidence_stage": "LIVE_REAL",
                "data_resolution": "M1_BID_ASK",
                "execution_status": "LIVE_EXECUTION_VERIFIED",
                "risk_spectrum_tier": "T2_CONSERVATIVE",
                "profit_factor": 1.62,
                "calmar": 2.35,
                "sharpe": 2.15,
                "ev_per_fee": 6.4,
                "funded_12m_blowup_pct": 0.2,
                "ruin_36m_pct": 0.3,
                "p_le_zero_24m_pct": 9.5,
                "payout_1_cal_days": 95.0,
                "slippage_breakeven_mult": 2.3,
                "p1_pass_rate_pct": 78.0,
                "p1_fail_rate_pct": 12.0,
                "p1_pending_rate_pct": 10.0,
                "p2_pass_rate_pct": 88.0,
                "p2_fail_rate_pct": 7.0,
                "p2_pending_rate_pct": 5.0,
                "pass_eval_12m_pct": 70.0,
            }
        )
        _check(sc.overall_grade == "TOP_1_PCT", f"expected TOP_1_PCT, got {sc.overall_grade}")
        _check(sc.unified_grade_code == "TOP_1_PCT", "unified_grade_code mismatch")
        for ph in ("p1", "p2", "pass_eval", "funded_12m"):
            _check(sc.phase_grades[ph].grade == "TOP_1_PCT", f"phase {ph} expected TOP_1_PCT")
        _check(
            len(sc.exact_bottlenecks) == 0,
            f"ideal live Top 1% should have 0 bottlenecks, got {sc.exact_bottlenecks}",
        )
        _check(all(sc.metric_pass_map.values()), "all metric_pass_map entries should be True")

    def test_grade_legacy_uninstrumented_p1_p2_and_ordered_bottlenecks(self) -> None:
        sc = ec.grade_evaluation_record(
            {
                "record_id": "w4-legacy-sample",
                "domain_tier": "T1_CFD_PROP",
                "eval_scope": "MULTI_ACCOUNT_FLEET",
                "pricing_regime": "BLACK_FRIDAY_PROMO",
                "evidence_stage": "DEV_CONSUMED_OOS",
                "data_resolution": "APPROX_DAILY",
                "execution_status": "MEASURED_DEMO_EXECUTION",
                "legacy_grade_code": "TOT",
                "ev_per_fee": 5.4,
                "funded_12m_blowup_pct": 0.17,
                "ruin_36m_pct": 0.08,
                "p_le_zero_24m_pct": 35.0,
                "payout_1_cal_days": 560.0,  # BAD (>= 540d) -> must sort BEFORE ADEQUATE p_le_zero_24m!
                "pass_eval_12m_pct": 51.67,
            }
        )
        _check(sc.legacy_grade_code == "TOT", "must preserve legacy_grade_code")
        _check(sc.unified_grade_code == "BAD", f"payout_1=560d must force overall BAD, got {sc.unified_grade_code}")
        for ph in ("p1", "p2"):
            d = sc.phase_grades[ph]
            _check(d.grade == "UNKNOWN_LEGACY_UNINSTRUMENTED", f"{ph} must be UNKNOWN_LEGACY_UNINSTRUMENTED")
            _check(d.presentation_state.availability == "ready", f"{ph} availability must be ready")
            _check(d.presentation_state.freshness == "partial", f"{ph} freshness must be partial")
            _check(d.presentation_state.certainty == "unknown", f"{ph} certainty must be unknown")
            _check(
                d.presentation_state.label == ec.LEGACY_UNINSTRUMENTED_LABEL_VI,
                f"{ph} label mismatch: {d.presentation_state.label!r}",
            )
        codes = [b.code for b in sc.exact_bottlenecks]
        _check(codes[0] == "PAYOUT_1_SLOW", f"worst BAD bottleneck PAYOUT_1_SLOW must be first, got {codes}")
        _check("P_LE_ZERO_24M_HIGH" in codes, "must include P_LE_ZERO_24M_HIGH bottleneck")
        _check("PRICING_PROMO_ASSUMPTION" in codes, "must flag BLACK_FRIDAY_PROMO caveat")
        ranks = [b.severity_rank for b in sc.exact_bottlenecks]
        _check(ranks == list(range(1, len(ranks) + 1)), f"severity_rank must be contiguous 1..N, got {ranks}")

    def test_inside_out_grading_across_all_four_tiers(self) -> None:
        # T3_MULTI_ASSET_OWNBOOK grades Sharpe/Calmar/PF/Slippage cleanly without requiring prop P1/P2
        sc_t3 = ec.grade_evaluation_record(
            {
                "record_id": "ownbook-portfolio",
                "domain_tier": "T3_MULTI_ASSET_OWNBOOK",
                "eval_scope": "SINGLE_TICKET",
                "evidence_stage": "DEV_BLIND_OOS",
                "data_resolution": "M1_BID_SPREAD",
                "profit_factor": 1.38,
                "calmar": 1.65,
                "sharpe": 1.72,
                "slippage_breakeven_mult": 1.85,
            }
        )
        _check(sc_t3.overall_grade == "GOOD", f"T3 expected GOOD, got {sc_t3.overall_grade}")
        _check(sc_t3.phase_grades["p1"].grade == "UNKNOWN_LEGACY_UNINSTRUMENTED", "T3 P1 is not applicable")
        _check(sc_t3.phase_grades["funded_12m"].grade == "GOOD", "T3 funded_12m uses Calmar/Sharpe")

        # T2_CME_FUTURES uses CME trailing EOD blowup threshold (< 5% GOOD)
        sc_t2 = ec.grade_evaluation_record(
            {
                "record_id": "cme-futures-1",
                "domain_tier": "T2_CME_FUTURES",
                "eval_scope": "SINGLE_TICKET",
                "evidence_stage": "DEV_CONSUMED_OOS",
                "data_resolution": "M1_BID_ASK",
                "ev_per_fee": 3.1,
                "funded_12m_blowup_pct": 3.2,
                "ruin_36m_pct": 2.0,
                "p_le_zero_24m_pct": 20.0,
                "payout_1_cal_days": 140.0,
            }
        )
        _check(sc_t2.overall_grade == "GOOD", f"T2 expected GOOD, got {sc_t2.overall_grade}")

        # T4_LIVE_OPS grades live slippage & low funded blowup
        sc_t4 = ec.grade_evaluation_record(
            {
                "record_id": "live-ops-1",
                "domain_tier": "T4_LIVE_OPS",
                "eval_scope": "SINGLE_TICKET",
                "evidence_stage": "SHADOW_DEMO",
                "data_resolution": "TICK_REAL",
                "slippage_breakeven_mult": 2.1,
                "funded_12m_blowup_pct": 0.1,
            }
        )
        _check(sc_t4.overall_grade == "TOP_1_PCT", f"T4 expected TOP_1_PCT, got {sc_t4.overall_grade}")


# ---------------------------------------------------------------------------
# 2. Synthetic Federated DuckDB + SQLiteRunRegistry Tests (Isolated in tmp_path)
# ---------------------------------------------------------------------------


class TestUnifiedCatalogSynthetic:
    def test_federation_dedup_backfill_idempotency_and_tamper_detection(self, tmp_path: Path) -> None:
        legacy_dir = tmp_path / "legacy"
        legacy_dir.mkdir()
        sources = _make_synthetic_legacy_dbs(legacy_dir)
        pareto_json = _make_synthetic_pareto_json(tmp_path / "wave4_pareto.json")

        cat_db = tmp_path / "unified_eval_catalog.duckdb"
        cat_reg = tmp_path / "unified_eval_registry.sqlite3"

        # Negative test: attempting to ingest duplicate wave4_frontier_m36::experiments MUST fail closed!
        with ec.UnifiedEvaluationCatalog(duckdb_path=cat_db, registry_path=cat_reg) as cat:
            bad_sources = [
                {
                    "source_key": "wave4_frontier_m36",
                    "db_path": legacy_dir / "wave4_frontier_m36.duckdb",
                    "table_name": "experiments",
                }
            ]
            with pytest.raises(ValueError, match="DOUBLE_COUNT_GUARD"):
                cat.ingest_legacy_trials(sources=bad_sources)

        # Full build + backfill with write_output_path=None (verifies no side-effect file created)
        res1 = ec.build_and_backfill_unified_catalog(
            duckdb_path=cat_db,
            registry_path=cat_reg,
            pareto_json_path=pareto_json,
            legacy_sources=sources,
            write_output_path=None,
        )
        _check(res1["legacy_federation"]["total_distinct_trials"] == 10, "expected 5+3+2=10 distinct trials")
        _check(res1["wave4_backfill"]["total_mc_cases"] == 4, "expected 2+1+1=4 synthetic MC rows")
        _check(res1["wave4_backfill"]["profile_id"] == "C10_NEWS_ON", "profile_id must come from ssot_provenance")
        _check(res1["wave4_backfill"]["funded_mult"] == 1.25, "funded_mult must come from ssot_provenance")
        _check(res1["integrity"]["verified"] is True, "integrity must verify True")

        # Idempotent re-run MUST yield exact same counts with zero duplicates
        res2 = ec.build_and_backfill_unified_catalog(
            duckdb_path=cat_db,
            registry_path=cat_reg,
            pareto_json_path=pareto_json,
            legacy_sources=sources,
            write_output_path=None,
        )
        _check(res2["integrity"]["legacy_trials_federated_count"] == 10, "re-ingest must not double count")
        _check(res2["integrity"]["mc_cases_catalog_count"] == 4, "re-backfill must not duplicate MC rows")

        # Record single run + alpha entry and verify all 4 tables/views work cleanly
        with ec.UnifiedEvaluationCatalog(duckdb_path=cat_db, registry_path=cat_reg) as cat:
            cat.record_run(
                {
                    "record_id": "w5-run-001",
                    "domain_tier": "T1_CFD_PROP",
                    "ev_per_fee": 4.2,
                    "funded_12m_blowup_pct": 0.4,
                    "ruin_36m_pct": 0.5,
                    "p_le_zero_24m_pct": 22.0,
                    "payout_1_cal_days": 180.0,
                    "p1_pass_rate_pct": 62.0,
                    "p2_pass_rate_pct": 78.0,
                    "pass_eval_12m_pct": 52.0,
                },
                strategy_id="PORT_7E_v105",
                profile_id="C10_NEWS_ON",
                funded_mult=1.25,
                friction_mult=1.0,
            )
            alpha_row = cat.record_alpha(
                {
                    "alpha_id": "F5B_AUDJPY_SWEEP_01",
                    "family_id": "F5B_LIQUIDITY_SWEEP_MEANREV",
                    "symbol": "AUDJPY",
                    "lifecycle_state": "BLIND_B_VERIFIED",
                    "raw_blindness_tier": "TRUE_BLIND_CLB_NEW7_CROSSES",
                    "mt5_hcc_ready": True,
                    "profit_factor": 1.32,
                    "calmar": 1.45,
                    "cluster_a_sharpe": 1.5,
                    "cluster_b_sharpe": 1.35,
                    "slippage_breakeven_mult": 1.9,
                }
            )
            _check(alpha_row["blindness_tier"] == "M1_UNSEEN_D1_VIEWED", "alpha blindness tier mapping mismatch")
            # Verify Wave 5 record_mc_cases(...) supports campaign_id, full P1/P2 grades, and tamper detection
            w5_case = {
                "case_id": "V103_SPRINT__ftmo_standard_10k__1_0x",
                "source_cohort": "W5_BASELINE_1_0X",
                "firm_group": "FTMO",
                "contract_id": "ftmo_standard_10k",
                "profile_id": "V103_SPRINT",
                "funded_mult": 1.0,
                "friction_mult": 1.0,
                "bankroll_m_vnd": 3,
                "bankroll_usd": 101.08,
                "concurrency_mode": "SINGLE_TICKET_ZERO_RETRY",
                "allocation_policy": "SINGLE_TICKET_BASELINE",
                "eval_scope": "SINGLE_TICKET",
                "pricing_regime": "ALL_REGULAR_SSOT",
                "evidence_stage": "DEV_CONSUMED_OOS",
                "data_resolution": "APPROX_DAILY",
                "execution_status": "MEASURED_DEMO_EXECUTION",
                "risk_spectrum_tier": "T4_AGGRESSIVE_SPRINT",
                "n_paths": 1000,
                "horizon_days": 756,
                "median_24m_net_vnd": 12_000_000.0,
                "median_36m_net_vnd": 12_000_000.0,
                "median_36m_net_usd": 465.7,
                "mean_36m_net_vnd": 15_000_000.0,
                "ev_per_1_vnd_fee_24m": 5.9,
                "ev_per_1_vnd_fee_36m": 5.9,
                "p_net_le_0_24m_pct": 33.0,
                "p_net_le_0_36m_pct": 33.0,
                "p_bankroll_ruin_24m_pct": 29.0,
                "p_bankroll_ruin_pct": 29.0,
                "funded_12m_blowup_pct": 0.2,
                "funded_12m_wilson_95_ub_pct": 0.4,
                "uncond_med_pay1_cal_days_cap730": 288.0,
                "p1_pass_rate_pct": 76.0,
                "p1_fail_rate_pct": 18.0,
                "p1_pending_rate_pct": 6.0,
                "p2_pass_rate_pct": 86.0,
                "p2_fail_rate_pct": 10.0,
                "p2_pending_rate_pct": 4.0,
                "monthly_pass_fail_pending": {
                    "12m": {"pass_pct": 65.0, "fail_pct": 28.0, "pending_pct": 7.0},
                    "36m": {"pass_pct": 70.0, "fail_pct": 29.5, "pending_pct": 0.5},
                },
                "strategy_quality": {
                    "profit_factor": 1.24,
                    "calmar": 1.12,
                    "sharpe": 1.29,
                    "winrate_pct": 49.0,
                    "avg_rr": 1.28,
                    "ev_per_trade_r": 0.056,
                },
                "holdout_rows_analysed": 0,
                "order_send_count": 0,
            }
            w5_art_sha = hashlib.sha256(b"w5-synthetic-baseline").hexdigest()
            fixed_ts = "2026-11-28T07:30:00Z"
            rec_mc = cat.record_mc_cases(
                [w5_case],
                campaign_id="offensive5_baseline",
                run_id="w5-baseline-test-run",
                source_artifact_sha256=w5_art_sha,
                created_utc=fixed_ts,
            )
            _check(rec_mc["total_mc_cases"] == 1, "expected 1 recorded Wave 5 MC case")
            _check(rec_mc["campaign_id"] == "offensive5_baseline", "campaign_id mismatch")
            # Re-recording same campaign with identical timestamp must stay bit-idempotent
            rec_mc_2 = cat.record_mc_cases(
                [w5_case],
                campaign_id="offensive5_baseline",
                run_id="w5-baseline-test-run",
                source_artifact_sha256=w5_art_sha,
                created_utc=fixed_ts,
            )
            _check(rec_mc_2["batch_sha256"] == rec_mc["batch_sha256"], "idempotent re-record sha drift")
            with pytest.raises(ValueError, match="CAMPAIGN_PROTECTED"):
                cat.record_mc_cases(
                    [w5_case],
                    campaign_id="offensive4",
                    run_id="bad",
                    source_artifact_sha256=w5_art_sha,
                )

            ver = cat.verify_integrity()
            _check(ver["verified"] is True, "integrity after run+alpha+w5_mc must pass")
            _check(ver["runs_catalog_count"] == 1, "expected 1 run")
            _check(ver["alpha_registry_catalog_count"] == 1, "expected 1 alpha")
            _check(ver["mc_by_campaign"]["offensive4"] == 4, "expected 4 Wave 4 rows")
            _check(ver["mc_by_campaign"]["offensive5_baseline"] == 1, "expected 1 Wave 5 baseline row")

            # Verify read-only SQL rejects writes
            with pytest.raises(ValueError, match="read-only"):
                cat.query_sql("DELETE FROM runs_catalog")

            # Verify P1/P2 presentation state in Wave 4 mc_cases_catalog rows
            mc_check = cat.query_sql(
                "SELECT profile_id, funded_mult, p1_grade, p2_grade, "
                "p1_presentation_state_json, legacy_grade_code, unified_grade_code "
                "FROM mc_cases_catalog WHERE campaign_id = 'offensive4'"
            )
            _check(len(mc_check) == 4, "expected 4 Wave 4 MC rows")
            for prof, fm, p1g, p2g, p1_json, lg, ug in mc_check:
                _check(prof == "C10_NEWS_ON", f"unexpected profile_id: {prof}")
                _check(abs(float(fm) - 1.25) < 1e-9, f"unexpected funded_mult: {fm}")
                _check(p1g == "UNKNOWN_LEGACY_UNINSTRUMENTED", f"expected UNKNOWN p1, got {p1g}")
                _check(p2g == "UNKNOWN_LEGACY_UNINSTRUMENTED", f"expected UNKNOWN p2, got {p2g}")
                pstate = ec.PresentationState.model_validate(json.loads(p1_json))
                _check(
                    pstate.availability == "ready"
                    and pstate.freshness == "partial"
                    and pstate.certainty == "unknown",
                    "invalid p1 presentation state",
                )
                _check(pstate.label == ec.LEGACY_UNINSTRUMENTED_LABEL_VI, "unexpected p1 label")
                _check(bool(lg) and bool(ug), "must preserve both legacy and unified grades")

            # Verify Wave 5 row carries instrumented P1/P2/Pass/Funded grades
            w5_check = cat.query_sql(
                "SELECT profile_id, p1_grade, p2_grade, pass_eval_grade, funded_12m_grade, unified_grade_code "
                "FROM mc_cases_catalog WHERE campaign_id = 'offensive5_baseline'"
            )
            _check(len(w5_check) == 1, "expected 1 Wave 5 MC row")
            _check(w5_check[0][0] == "V103_SPRINT", "unexpected Wave 5 profile_id")
            for gcol in w5_check[0][1:]:
                _check(gcol != "UNKNOWN_LEGACY_UNINSTRUMENTED", f"Wave 5 grade must be instrumented, got {gcol}")

        # Tamper negative mutation #1: directly mutate Wave 5 campaign row -> MUST fail!
        con_tamper_w5 = duckdb.connect(str(cat_db))
        con_tamper_w5.execute(
            "UPDATE mc_cases_catalog SET record_sha256 = ? WHERE campaign_id = 'offensive5_baseline'",
            ["1" * 64],
        )
        con_tamper_w5.close()
        with ec.UnifiedEvaluationCatalog(duckdb_path=cat_db, registry_path=cat_reg, read_only=True) as cat_ro:
            with pytest.raises(JournalCorruptionError, match="MC_CAMPAIGN_BATCH_SHA_TAMPERED"):
                cat_ro.verify_integrity()

        # Restore Wave 5 row and tamper Wave 4 row -> MUST still fail on Wave 4 batch hash!
        con_tamper = duckdb.connect(str(cat_db))
        con_tamper.execute(
            "UPDATE mc_cases_catalog SET record_sha256 = ? "
            "WHERE campaign_id = 'offensive4' AND source_cohort = 'THE5ERS_REF_1_0X'",
            ["0" * 64],
        )
        con_tamper.close()
        with ec.UnifiedEvaluationCatalog(duckdb_path=cat_db, registry_path=cat_reg, read_only=True) as cat_ro:
            with pytest.raises(JournalCorruptionError, match="MC_CATALOG_BATCH_SHA_TAMPERED"):
                cat_ro.verify_integrity()


# ---------------------------------------------------------------------------
# 3. Local-Cache Production Catalog Verification (Read-Only, Zero Mutation)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_unified_catalog_backfill_and_sha_immutability() -> None:
    prod_db = ec.DEFAULT_CATALOG_DUCKDB_PATH
    prod_reg = ec.DEFAULT_CATALOG_REGISTRY_PATH
    _check(prod_db.is_file(), f"production catalog missing: {prod_db}")
    _check(prod_reg.is_file(), f"production registry missing: {prod_reg}")

    sha_before = _sha256_file(prod_db)
    reg_sha_before = _sha256_file(prod_reg)

    with ec.UnifiedEvaluationCatalog(duckdb_path=prod_db, registry_path=prod_reg, read_only=True) as cat:
        ver = cat.verify_integrity()
        _check(ver["verified"] is True, "production catalog integrity failed")
        _check(
            ver["legacy_trials_federated_count"] == 1342,
            f"expected 1342 legacy trials, got {ver['legacy_trials_federated_count']}",
        )
        _check(ver["legacy_trials_distinct_count"] == 1342, "distinct legacy trials must equal 1342")
        _check(
            ver["legacy_by_source"]
            == {
                "experiments_core::experiments": 1279,
                "wave4_frontier_m36::wave4_frontier_trials": 27,
                "wave4_ml_m48::wave4_ml_m48": 36,
            },
            f"unexpected legacy_by_source: {ver['legacy_by_source']}",
        )
        # Strictly verify Wave 4's 168 backfilled rows scoped to campaign_id = 'offensive4'
        w4_count = int(
            cat.query_sql("SELECT COUNT(*) FROM mc_cases_catalog WHERE campaign_id = 'offensive4'")[0][0]
        )
        _check(w4_count == 168, f"expected 168 Wave 4 MC rows, got {w4_count}")
        w4_cohorts = {
            str(r[0]): int(r[1])
            for r in cat.query_sql(
                "SELECT source_cohort, COUNT(*) FROM mc_cases_catalog "
                "WHERE campaign_id = 'offensive4' GROUP BY 1 ORDER BY 1"
            )
        }
        _check(
            w4_cohorts
            == {
                "FTMO_BASELINE_1_0X": 81,
                "FTMO_STRESS_1_5X": 81,
                "THE5ERS_REF_1_0X": 6,
            },
            f"unexpected Wave 4 mc_by_cohort: {w4_cohorts}",
        )

        # Verify every single one of Wave 4's 168 rows carries exact C10_NEWS_ON / 1.25 / UNKNOWN P1&P2
        bad_rows = cat.query_sql(
            """
            SELECT COUNT(*) FROM mc_cases_catalog
            WHERE campaign_id = 'offensive4'
              AND (
                profile_id != 'C10_NEWS_ON'
                OR ABS(funded_mult - 1.25) > 1e-9
                OR p1_grade != 'UNKNOWN_LEGACY_UNINSTRUMENTED'
                OR p2_grade != 'UNKNOWN_LEGACY_UNINSTRUMENTED'
                OR holdout_rows_analysed != 0
                OR order_send_count != 0
                OR legacy_grade_code IS NULL
                OR unified_grade_code IS NULL
              )
            """
        )[0][0]
        _check(int(bad_rows) == 0, f"found {bad_rows} malformed Wave 4 production MC rows")

    # Verify read-only test NEVER mutated production files!
    _check(_sha256_file(prod_db) == sha_before, "production DuckDB SHA mutated during pytest!")
    _check(_sha256_file(prod_reg) == reg_sha_before, "production SQLite registry SHA mutated during pytest!")
