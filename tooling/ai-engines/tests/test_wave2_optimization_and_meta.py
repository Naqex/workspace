"""Wave 2 Core Engine Optimization, Allocator v2 (Ledoit-Wolf + NCO + GARCH-EVT),
Purged Embargo Meta-Labeling, and RD-Agent-Q Auto Research Loop Tests.

Strict fail-closed invariants:
  - Holdout 2025-2026 remains 100% SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`).
  - Future-mutation anti-lookahead proofs for Purged Embargo Walk-Forward Meta-Labeling.
  - Pure-Python vs Numba-JIT parity and speedup proofs.
  - Multi-sleeve (4, 6, 8) Ledoit-Wolf + NCO + GARCH-EVT Student-t Copula invariants.
  - Auto Research Loop M_TOTAL_HARD_CAP=20, Holdout-leak kill gate, and white-box .mq5 emitter audit.
"""

from __future__ import annotations

import hashlib
import importlib.util
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from mq5_whitebox_exporter import audit_open_source_mq5
from quant_factory.auto_research_loop import (
    M_TOTAL_HARD_CAP,
    build_demo_batch,
    emit_survivor_templates,
    parse_batch_cards,
    run_research_batch,
)
from quant_factory.data_store import assert_holdout_locked
from quant_factory.meta_labeler import (
    compute_classification_metrics,
    fit_l2_logistic,
    fit_shallow_stump_ensemble,
    predict_proba_logistic,
    predict_proba_stumps,
    purged_embargo_walkforward_predict,
)
from quant_factory.portfolio_allocator import (
    ALLOCATORS,
    discover_available_sleeves,
    fit_garch11_evt,
    garch_evt_tail_stress,
    ledoit_wolf_covariance,
    weights_erc_lw_capped35,
    weights_nco,
    weights_nco_capped35,
)
from quant_factory.speed_audit import benchmark_numba_kernels


def _count_bare_dollar_pairs(md_text: str) -> int:
    """Count lines with 2+ unescaped `$` outside fenced code blocks (prevents broken KaTeX rendering)."""
    in_fence = False
    bad = 0
    for ln in md_text.splitlines():
        if ln.strip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        cleaned = re.sub(r"`[^`]*`", "", ln)
        if cleaned.count("$") >= 2:
            bad += 1
    return bad


def test_wave2_reports_exist_holdout_sealed_and_clean_prose():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    reports = [
        ROOT / "planning/research/LAB6-META-LABELING-AUDIT-20261124.md",
        ROOT / "planning/research/SYSTEM-SPEEDUP-AND-NCO-AUDIT-20261124.md",
    ]
    for rp in reports:
        assert rp.exists(), f"Missing Wave-2 report: {rp}"
        assert rp.stat().st_size < 900_000, f"Report exceeds 900 KB anti-bloat cap: {rp}"
        txt = rp.read_text(encoding="utf-8")
        assert "holdout_rows_analysed: 0" in txt
        assert "order_send_count: 0" in txt
        assert _count_bare_dollar_pairs(txt) == 0, f"Bare $ pair detected in {rp.name}"


@pytest.mark.local_cache
def test_ledoit_wolf_and_nco_multi_sleeve_invariants_4_6_8():
    assert {"ERC_LW_Capped35", "NCO", "NCO_Capped35"}.issubset(set(ALLOCATORS.keys()))

    rng = np.random.default_rng(20261124)
    for k in (4, 6, 8):
        # Construct correlated multi-sleeve return matrix with near-collinear pair to stress condition number
        factor = rng.normal(0.0, 0.01, size=(600, 2))
        loadings = rng.uniform(0.1, 0.9, size=(2, k))
        noise = rng.normal(0.0, 0.002, size=(600, k))
        mat = factor @ loadings + noise
        mat[:, 1] = 0.96 * mat[:, 0] + rng.normal(0.0, 0.0005, size=600)

        cov_lw, meta = ledoit_wolf_covariance(mat)
        assert cov_lw.shape == (k, k)
        assert np.allclose(cov_lw, cov_lw.T, atol=1e-12)
        eigs = np.linalg.eigvalsh(cov_lw)
        assert float(np.min(eigs)) > 0.0
        assert 0.0 <= meta["shrinkage"] <= 1.0
        assert meta["cond_shrunk"] <= meta["cond_sample"] + 1e-6

        w_nco = weights_nco(mat)
        w_nco_cap = weights_nco_capped35(mat)
        w_erc_cap = weights_erc_lw_capped35(mat)
        for w in (w_nco, w_nco_cap, w_erc_cap):
            assert w.shape == (k,)
            assert np.all(np.isfinite(w))
            assert float(np.min(w)) >= -1e-12
            assert abs(float(np.sum(w)) - 1.0) < 1e-6
        assert float(np.max(w_nco_cap)) <= 0.35 + 1e-6
        assert float(np.max(w_erc_cap)) <= 0.35 + 1e-6

    discovered_sleeves, discovered_meta = discover_available_sleeves(max_sleeves=8)
    assert 4 <= len(discovered_sleeves) <= 8
    assert "S1_PROP_FX_IDX" in discovered_sleeves
    assert set(discovered_sleeves.keys()) == set(discovered_meta.keys())


def test_garch_evt_numba_parity_and_copula_determinism():
    rng = np.random.default_rng(1337)
    # Generate GARCH-like heavy-tailed returns
    t_steps = 800
    k = 4
    mat = np.zeros((t_steps, k), dtype=np.float64)
    for j in range(k):
        h = 1e-4
        for t in range(t_steps):
            z = rng.standard_t(df=5.0) * 0.77
            eps = np.sqrt(h) * z
            mat[t, j] = 0.0002 + eps
            h = 1e-5 + 0.10 * (eps ** 2) + 0.82 * h

    fit_py = fit_garch11_evt(mat[:, 0], use_numba=False)
    fit_nb = fit_garch11_evt(mat[:, 0], use_numba=True)
    assert abs(fit_py["alpha"] - fit_nb["alpha"]) < 1e-5
    assert abs(fit_py["beta"] - fit_nb["beta"]) < 1e-5
    assert fit_nb["alpha"] >= 0.0 and fit_nb["beta"] >= 0.0
    assert (fit_nb["alpha"] + fit_nb["beta"]) < 0.995
    assert np.isfinite(fit_nb["evt_xi"]) and fit_nb["evt_scale"] > 0.0

    names = [f"S{j + 1}" for j in range(k)]
    alloc_w = {
        "Equal_Weight": np.full(k, 1.0 / k),
        "NCO_Capped35": weights_nco_capped35(mat),
    }
    st1 = garch_evt_tail_stress(mat, names, alloc_w, n_paths=400, horizon=126, seed=77)
    st2 = garch_evt_tail_stress(mat, names, alloc_w, n_paths=400, horizon=126, seed=77)
    assert st1["per_allocator"] == st2["per_allocator"]
    for ak in alloc_w:
        row = st1["per_allocator"][ak]
        assert row["stress_dd_p99_pct"] >= row["stress_dd_p95_pct"] >= row["stress_dd_p50_pct"] >= 0.0
        assert row["cvar99_daily_pct"] >= row["var99_daily_pct"] >= 0.0


def test_meta_labeler_strict_anti_lookahead_and_purge_embargo():
    """Mutating future X[cut:] and y[cut:] MUST produce EXACT 0.0 change in all earlier walk-forward folds."""
    rng = np.random.default_rng(2026)
    n = 600
    d = 6
    X = rng.normal(0.0, 1.0, size=(n, d))
    logits = 0.7 * X[:, 0] - 0.5 * X[:, 1] + 0.3 * X[:, 2]
    y = (rng.uniform(0.0, 1.0, size=n) < (1.0 / (1.0 + np.exp(-logits)))).astype(np.int8)
    # 1 observation every 2 calendar days -> 1200-day span -> plenty of 90-day folds
    day_ords = np.arange(n, dtype=np.int64) * 2 + 737000

    cut_idx = 420
    cut_ord = int(day_ords[cut_idx])
    X_mut = X.copy()
    y_mut = y.copy()
    X_mut[cut_idx:] = -50.0 * X_mut[cut_idx:] + 999.0
    y_mut[cut_idx:] = 1 - y_mut[cut_idx:]

    # Indices strictly prior to the fold containing cut_ord (first fold starts at day_ords[180])
    # Fold k covers [start + k*90, start + (k+1)*90 - 1]. Check everything before cut_ord - 90.
    safe_pre = day_ords < (cut_ord - 90)

    for model_kind in ("l2_logistic", "shallow_stumps"):
        wf_clean = purged_embargo_walkforward_predict(
            X, y, day_ords, model_kind=model_kind, min_train_obs=180, fold_span_days=90, purge_days=5, embargo_days=10
        )
        wf_mut = purged_embargo_walkforward_predict(
            X_mut, y_mut, day_ords, model_kind=model_kind, min_train_obs=180, fold_span_days=90, purge_days=5, embargo_days=10
        )
        assert wf_clean["n_folds"] >= 5
        assert wf_clean["total_purged_obs"] > 0

        chk = safe_pre & wf_clean["evaluated_mask"]
        assert int(np.sum(chk)) >= 100
        assert np.array_equal(wf_clean["probs"][chk], wf_mut["probs"][chk]), f"Look-ahead leak in {model_kind} probs!"
        assert np.array_equal(wf_clean["sizes_cont"][chk], wf_mut["sizes_cont"][chk])
        assert np.array_equal(wf_clean["sizes_filt"][chk], wf_mut["sizes_filt"][chk])

        # Bet-sizing policy bounds strictly respected
        sc = wf_clean["sizes_cont"][wf_clean["evaluated_mask"]]
        sf = wf_clean["sizes_filt"][wf_clean["evaluated_mask"]]
        assert float(np.min(sc)) >= 0.50 - 1e-12 and float(np.max(sc)) <= 1.25 + 1e-12
        assert set(np.unique(sf).tolist()).issubset({0.0, 1.0})


def test_meta_labeler_classifiers_learn_separable_signal():
    rng = np.random.default_rng(99)
    n_tr, n_te = 800, 400
    X_tr = rng.normal(0.0, 1.0, size=(n_tr, 4))
    X_te = rng.normal(0.0, 1.0, size=(n_te, 4))
    y_tr = (2.2 * X_tr[:, 0] - 1.8 * X_tr[:, 1] + rng.normal(0.0, 0.7, size=n_tr) > 0.0).astype(np.int8)
    y_te = (2.2 * X_te[:, 0] - 1.8 * X_te[:, 1] + rng.normal(0.0, 0.7, size=n_te) > 0.0).astype(np.int8)

    m_log = fit_l2_logistic(X_tr, y_tr, l2_reg=1.0)
    p_log = predict_proba_logistic(m_log, X_te)
    cm_log = compute_classification_metrics(y_te, p_log)
    assert cm_log["roc_auc"] > 0.85
    assert cm_log["brier_skill"] > 0.30

    m_st = fit_shallow_stump_ensemble(X_tr, y_tr, n_stumps=6, learning_rate=0.30, min_leaf=25)
    p_st = predict_proba_stumps(m_st, X_te)
    cm_st = compute_classification_metrics(y_te, p_st)
    assert cm_st["roc_auc"] > 0.80
    assert cm_st["brier_skill"] > 0.20


@pytest.mark.local_cache
def test_auto_research_loop_cap_holdout_kill_and_clean_template_emit(tmp_path: Path):
    # 1. Enforce M_TOTAL_HARD_CAP = 20
    too_many = {
        "batch_id": "OVERFLOW",
        "hypotheses": [
            {
                "hypothesis_id": f"H_{i:02d}",
                "title": f"Hyp {i}",
                "asset_universe": ["USDJPY"],
                "counterparty_mechanism": "Forced session rebalance",
                "economic_rationale": "Session liquidity imbalance",
                "causal_invariants": ["lagged_1bar"],
            }
            for i in range(M_TOTAL_HARD_CAP + 1)
        ],
    }
    with pytest.raises(ValueError, match="M_TOTAL_HARD_CAP"):
        parse_batch_cards(too_many)

    # 2. Holdout contamination MUST trigger REJECT_KILLED and block template emission
    leak_batch = {
        "batch_id": "LEAK_TEST",
        "n_trials_cumulative": 1,
        "hypotheses": [
            {
                "hypothesis_id": "LEAKY_CAND",
                "title": "Contaminated Holdout Test",
                "asset_universe": ["EURUSD"],
                "counterparty_mechanism": "Session flow",
                "economic_rationale": "Testing holdout fail-closed",
                "causal_invariants": ["strict_lag"],
            }
        ],
    }

    def _leaky_eval(_spec: dict) -> dict:
        rng = np.random.default_rng(7)
        ra = rng.normal(0.001, 0.005, size=500)
        rb = rng.normal(0.001, 0.005, size=500)
        return {
            "cluster_a_returns": ra,
            "cluster_b_returns": rb,
            "p_value_raw": 0.001,
            "cost_1x_net": 2500.0,
            "cost_2x_net": 2100.0,
            "n_trades_cluster_b": 200,
            "incumbent_daily_returns": rng.normal(0.0002, 0.004, size=500),
            "holdout_rows_analysed": 12,
        }

    leak_res = run_research_batch(leak_batch, out_dir=tmp_path / "leak", evaluator_fn=_leaky_eval)
    assert leak_res["counts"]["killed"] == 1
    assert leak_res["emitted_templates"] == {}
    with pytest.raises(ValueError, match="non-approved"):
        emit_survivor_templates(leak_res["verdicts"][0], tmp_path / "leak")

    # 3. Demo batch end-to-end: verified SHA-256 ledger + clean white-box .mq5 template passing auditor
    demo_res = run_research_batch(build_demo_batch(), out_dir=tmp_path / "demo", emit_templates=True)
    assert demo_res["holdout_rows_analysed"] == 0
    assert demo_res["order_send_count"] == 0
    assert "DEMO_ORTHO_SURVIVOR" in demo_res["approved_ids"]
    assert "DEMO_COST_FRAGILE_KILL" in demo_res["killed_ids"]

    json_p = Path(demo_res["ledger_json_path"])
    sha_p = json_p.with_suffix(".sha256")
    md_p = Path(demo_res["ledger_md_path"])
    assert json_p.exists() and sha_p.exists() and md_p.exists()
    actual_sha = hashlib.sha256(json_p.read_bytes()).hexdigest()
    assert sha_p.read_text(encoding="utf-8").strip().startswith(actual_sha)

    tpl = demo_res["emitted_templates"]["DEMO_ORTHO_SURVIVOR"]
    mq5_text = Path(tpl["mq5_template"]).read_text(encoding="utf-8")
    audit = audit_open_source_mq5(mq5_text)
    assert audit["red_flags"] == []
    assert audit["intake_verdict"] == "CLEAN_FOR_PYTHON_REPLICATION"
    assert "InpDryRunLogOnly" in mq5_text and "= true" in mq5_text
    assert '#include "Include/Naqex_PropGuard.mqh"' in mq5_text
    for method in (
        "OnNewTickHousekeeping()",
        "IsDailyLossBreached()",
        "IsInsideRedNewsWindow()",
        "IsNearBrokerSessionClose()",
        "IsSpreadAndSessionSafe()",
    ):
        assert method in mq5_text


@pytest.mark.local_cache
def test_speed_audit_numba_speedup_and_conftest_lpt_ordering():
    kb = benchmark_numba_kernels(seed=42)
    assert kb["garch_numba_speedup_x"] > 2.0
    assert kb["garch_parity_max_alpha_diff"] < 1e-5
    assert kb["pod_dashboard_snapshot_ms"] < 2000.0
    assert kb["pod_dashboard_sleeves"] >= 4

    # Verify conftest.py LPT sorting hook directly
    conftest_path = AI_ENGINES / "tests/conftest.py"
    spec = importlib.util.spec_from_file_location("_naqex_tests_conftest", conftest_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    class _FakeItem:
        def __init__(self, fname: str):
            self.fspath = str(AI_ENGINES / "tests" / fname)
            self.nodeid = f"{fname}::test_x"

    items = [_FakeItem("test_zzz_tiny.py"), _FakeItem("test_shadow_reconcile.py"), _FakeItem("test_wave2_cockpit_and_treasury.py")]
    mod.pytest_collection_modifyitems(items)
    ordered = [Path(it.fspath).name for it in items]
    assert ordered[0] == "test_wave2_cockpit_and_treasury.py"
    assert ordered[1] == "test_shadow_reconcile.py"
    assert ordered[2] == "test_zzz_tiny.py"
