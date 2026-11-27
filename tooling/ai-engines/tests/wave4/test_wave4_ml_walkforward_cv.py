"""Unit, fail-closed, and leak-mutation tests for Wave 4 Purged+Embargo Walk-Forward CV."""

from __future__ import annotations

import ast
import json
import math
import os
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_factory.wave4 import ml_features_24 as mf
from quant_factory.wave4 import ml_walkforward_cv as mcv

MODULE_PATH = Path(mcv.__file__).resolve()
AI_ENGINES_DIR = MODULE_PATH.parents[2]
_NO_WINDOW_FLAGS = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

_ENGINES_7: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)


# ---------------------------------------------------------------------------
# Deterministic Synthetic Offline Fixtures (100% CI-Safe, Pre-2025 Dev Only)
# ---------------------------------------------------------------------------


def _make_synthetic_trade_dataset(
    *,
    n_trades: int = 900,
    seed: int = 101,
    signal_strength: float = 1.4,
    start_ts: int = 1_577_836_800,  # 2020-01-01T00:00:00Z
    step_days: float = 1.8,
) -> dict[str, Any]:
    """Generate strictly pre-2025 synthetic 24-feature 7-engine dataset with known signal & collinear cols."""
    rng = np.random.default_rng(seed)
    n_feat = len(mf.FEATURE_NAMES_24)
    entry_ts = start_ts + (np.arange(n_trades, dtype=np.float64) * step_days * 86_400.0).astype(np.int64)
    # Mix normal intraday holds (4-12h) with occasional multi-day holds (3-6d)
    hold_sec = rng.integers(4 * 3600, 12 * 3600, size=n_trades, dtype=np.int64)
    hold_sec[::25] = 4 * 86_400
    exit_ts = entry_ts + hold_sec
    # Ensure strict pre-2025 ceiling
    assert int(np.max(exit_ts)) < mcv.DEV_CUTOFF_SEC

    x = rng.normal(0.0, 1.0, size=(n_trades, n_feat))
    # True signal embedded in 5 orthogonal features: indices 0, 6, 9, 12, 21
    logits = (
        signal_strength * (0.9 * x[:, 0] - 0.8 * x[:, 6] + 0.7 * x[:, 9] - 0.65 * x[:, 12] + 0.55 * x[:, 21])
        + 0.15
    )
    probs_true = 1.0 / (1.0 + np.exp(-np.clip(logits, -20.0, 20.0)))
    y = (rng.uniform(0.0, 1.0, size=n_trades) < probs_true).astype(np.float64)

    # Inject collinear duplicates so inside-fold pruning must eliminate redundancy
    x[:, 1] = x[:, 0] * 0.99 + rng.normal(0.0, 0.03, size=n_trades)
    x[:, 4] = -x[:, 0] * 0.98 + rng.normal(0.0, 0.04, size=n_trades)
    x[:, 7] = x[:, 6] * 0.99 + rng.normal(0.0, 0.03, size=n_trades)
    x[:, 13] = x[:, 12] * 0.99 + rng.normal(0.0, 0.03, size=n_trades)
    # Inject 2 constant features
    x[:, 17] = 1.0
    x[:, 19] = 2.0

    # Economics calibrated so baseline raw trades sit near 1.50x slippage breakeven (base_cost_r=0.08)
    net_r = np.where(y >= 0.5, 1.12, -1.00) + rng.normal(0.0, 0.05, size=n_trades)
    engine_ids = [_ENGINES_7[i % len(_ENGINES_7)] for i in range(n_trades)]

    return {
        "X": x.astype(np.float32),
        "y": y,
        "entry_ts": entry_ts,
        "exit_ts": exit_ts,
        "net_r": net_r,
        "engine_ids": engine_ids,
        "feature_names": list(mf.FEATURE_NAMES_24),
    }


def _make_stub_evaluation(
    *,
    brier_skill: float = 0.04,
    verdict: str = mcv.VERDICT_PROMOTE,
    oos_label: str = mcv.CONSUMED_CLB_TAG,
) -> dict[str, Any]:
    return {
        "oos_label": oos_label,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "brier_skill_score": brier_skill,
        "roc_auc": 0.58 if brier_skill > 0 else 0.49,
        "probabilistic_metrics": {
            "brier_model": 0.25 * (1.0 - brier_skill),
            "brier_climatology": 0.25,
            "brier_skill_score": brier_skill,
            "roc_auc": 0.58 if brier_skill > 0 else 0.49,
        },
        "engine_balance": {
            "min_engine_retention_ratio": 0.72,
            "overall_retention_ratio": 0.80,
            "passed": True,
        },
        "slippage_breakeven_24m": {
            "ml_v104_median_mult": 1.85 if verdict == mcv.VERDICT_PROMOTE else 1.45,
            "passed": verdict == mcv.VERDICT_PROMOTE,
        },
        "economics_1x": {
            "ml_v104": {
                "profit_factor": 1.42,
                "ev_r": 0.14,
                "max_dd_pct": 4.2,
            }
        },
        "verdict": verdict,
    }


# ---------------------------------------------------------------------------
# 1. Safety Invariants, Zero Bare `assert`s, Lazy Imports Only & `-O` Subprocess
# ---------------------------------------------------------------------------


def test_constants_zero_bare_asserts_and_zero_hmmlearn_or_shap() -> None:
    assert mcv.ORDER_SEND_CAPABLE is False
    assert mcv.ORDER_SEND_COUNT == 0
    assert mcv.HOLDOUT_CUTOFF_DATE == "2024-12-31"
    assert mcv.DEV_CUTOFF_SEC == int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
    assert mcv.CONSUMED_CLB_TAG == "CONSUMED_DEV_CLB_TEMPORAL_OOS"
    assert "BLIND" not in mcv.CONSUMED_CLB_TAG
    assert mcv.MODEL_FAMILIES == (
        "logit_l2",
        "lightgbm",
        "catboost",
        "regime_gmm_jump",
        "calibrated_bet_sizing",
    )

    src = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(MODULE_PATH))
    bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert bare_asserts == [], f"Bare asserts found at lines {bare_asserts} (unsafe under python -O)"

    imported_roots: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported_roots.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])

    assert "hmmlearn" not in imported_roots
    assert "shap" not in imported_roots


def test_lazy_imports_and_fail_closed_guards_under_python_O_subprocess() -> None:
    """Run clean `python -O` subprocess verifying zero eager ML/DB imports & active guards."""
    code = "\n".join(
        [
            "import sys",
            "import numpy as np",
            f"sys.path.insert(0, {str(AI_ENGINES_DIR)!r})",
            "import quant_factory.wave4.ml_walkforward_cv as mcv",
            "forbidden = ('sklearn', 'lightgbm', 'catboost', 'onnx', 'onnxruntime', "
            "'skl2onnx', 'onnxmltools', 'duckdb', 'scipy', 'pandas', 'hmmlearn', 'shap')",
            "loaded = [m for m in forbidden if m in sys.modules]",
            "if loaded:",
            "    raise RuntimeError(f'Eager imports detected: {loaded}')",
            "# Verify 2025-01-01 fails closed under python -O",
            "try:",
            "    mcv.ExpandingPurgedWalkForwardSplitter(n_splits=3, cutoff_utc='2025-01-01')",
            "    raise RuntimeError('Holdout cutoff did not fail closed under -O!')",
            "except mcv.HoldoutCutoffBreachError:",
            "    pass",
            "# Verify 2025-01-01 entry_ts fails closed under python -O",
            "ent = np.array([1_700_000_000 + i * 86400 for i in range(400)], dtype=np.int64)",
            "ent[-1] = mcv.DEV_CUTOFF_SEC",
            "try:",
            "    list(mcv.ExpandingPurgedWalkForwardSplitter(n_splits=3, min_train_samples=50).split(ent, ent + 3600))",
            "    raise RuntimeError('2025-01-01 trade ts did not fail closed under -O!')",
            "except mcv.HoldoutCutoffBreachError:",
            "    pass",
            "# Verify overlapping trade mutation fails closed under python -O",
            "ent_ok = np.array([1_650_000_000 + i * 86400 for i in range(100)], dtype=np.int64)",
            "ex_ok = ent_ok + 3600",
            "ex_ok[49] = ent_ok[60] + 100  # Overlaps validation fold starting at idx 60!",
            "try:",
            "    mcv.verify_fold_causality(",
            "        np.arange(50), np.arange(60, 100), ent_ok, ex_ok, purge_days=5, embargo_days=10",
            "    )",
            "    raise RuntimeError('Overlapping trade did not fail closed under -O!')",
            "except mcv.CausalityViolationError:",
            "    pass",
            "# Verify BLIND label fails closed under python -O",
            "try:",
            "    mcv.validate_oos_label('BLIND_CLUSTER_B')",
            "    raise RuntimeError('BLIND tag did not fail closed under -O!')",
            "except mcv.Law13HonestyError:",
            "    pass",
        ]
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        capture_output=True,
        text=True,
        check=False,
        creationflags=_NO_WINDOW_FLAGS,
    )
    assert proc.returncode == 0, f"python -O guard verification failed:\nSTDOUT:\n{proc.stdout}\nSTDERR:\n{proc.stderr}"


# ---------------------------------------------------------------------------
# 2. Strictly Chronological Expanding/Rolling Purged + Embargo Splitter Tests
# ---------------------------------------------------------------------------


def test_expanding_and_rolling_splitter_purge_embargo_and_long_holds() -> None:
    ds = _make_synthetic_trade_dataset(n_trades=900, seed=7)
    ent = ds["entry_ts"].copy()
    ex = ds["exit_ts"].copy()
    # Inject several long 35-day holding trades that span across fold boundaries
    ex[280] = ent[280] + 35 * 86_400
    ex[420] = ent[420] + 35 * 86_400
    ex[560] = ent[560] + 35 * 86_400

    splitter = mcv.ExpandingPurgedWalkForwardSplitter(
        n_splits=5,
        purge_days=5,
        embargo_days=10,
        min_train_samples=300,
    )
    folds = list(splitter.split(ent, ex))
    assert len(folds) == 5

    prev_train_len = 0
    seen_val: set[int] = set()
    prev_val_max_ts = -1
    for fold_i, (tr_idx, va_idx) in enumerate(folds):
        assert tr_idx.size >= 300
        assert tr_idx.size >= prev_train_len
        prev_train_len = int(tr_idx.size)

        tr_set = set(tr_idx.tolist())
        va_set = set(va_idx.tolist())
        assert tr_set.isdisjoint(va_set)
        assert seen_val.isdisjoint(va_set)
        seen_val.update(va_set)

        # Strictly forward chronological & strict purge + embargo clearance on EXIT times
        max_tr_exit = int(np.max(ex[tr_idx]))
        min_va_entry = int(np.min(ent[va_idx]))
        assert int(np.max(ent[tr_idx])) < min_va_entry
        assert max_tr_exit + 5 * 86_400 <= min_va_entry
        assert max_tr_exit + (5 + 10) * 86_400 <= min_va_entry
        assert min_va_entry > prev_val_max_ts
        prev_val_max_ts = int(np.max(ent[va_idx]))

        audit = splitter.last_fold_audits[fold_i]
        assert audit.observed_gap_days >= 15.0
        assert audit.n_purged >= 0 and audit.n_embargoed >= 0

    # Shuffling input row order produces identical chronological timestamp sets
    rng = np.random.default_rng(12)
    perm = rng.permutation(ent.size)
    folds_shuf = list(splitter.split(ent[perm], ex[perm]))
    assert len(folds_shuf) == 5
    for (tr0, va0), (tr1, va1) in zip(folds, folds_shuf, strict=True):
        assert np.array_equal(np.sort(ent[tr0]), np.sort(ent[perm][tr1]))
        assert np.array_equal(np.sort(ent[va0]), np.sort(ent[perm][va1]))

    # Rolling mode keeps train window bounded inside rolling_window_days
    rolling = mcv.ExpandingPurgedWalkForwardSplitter(
        n_splits=4,
        purge_days=5,
        embargo_days=10,
        min_train_samples=150,
        mode="rolling",
        rolling_window_days=450,
    )
    r_folds = list(rolling.split(ent, ex))
    assert len(r_folds) == 4
    for tr_idx, va_idx in r_folds:
        span_days = (int(np.max(ent[tr_idx])) - int(np.min(ent[tr_idx]))) / 86_400.0
        assert span_days <= 450.0 + 1e-6
        assert int(np.max(ex[tr_idx])) + 15 * 86_400 <= int(np.min(ent[va_idx]))


def test_splitter_negative_mutations_fail_closed() -> None:
    # 1. Invalid purge/embargo minimums fail closed
    with pytest.raises(ValueError, match="purge_days"):
        mcv.ExpandingPurgedWalkForwardSplitter(n_splits=3, purge_days=4, embargo_days=10)
    with pytest.raises(ValueError, match="embargo_days"):
        mcv.ExpandingPurgedWalkForwardSplitter(n_splits=3, purge_days=5, embargo_days=9)

    # 2. Construct clean baseline fold
    base_ts = 1_650_000_000  # 2022-04-15 UTC
    ent = base_ts + np.arange(120, dtype=np.int64) * np.int64(86_400)
    ex = ent + np.int64(6 * 3600)
    tr_ok = np.arange(0, 60, dtype=np.int64)
    va_ok = np.arange(80, 120, dtype=np.int64)  # 20d gap > 5 + 10 = 15d
    res_ok = mcv.verify_fold_causality(tr_ok, va_ok, ent, ex, purge_days=5, embargo_days=10)
    assert res_ok["passed"] is True

    # Negative Mutation A: Inject overlapping trade (exit_ts spills past min(entry_ts[val]))
    ex_overlap = ex.copy()
    ex_overlap[59] = ent[80] + 3600
    with pytest.raises(mcv.CausalityViolationError, match="OVERLAPPING_TRADE_LEAKAGE"):
        mcv.verify_fold_causality(tr_ok, va_ok, ent, ex_overlap, purge_days=5, embargo_days=10)

    # Negative Mutation B: Trade closes 3 days before val_start (breaches purge_days=5)
    ex_purge = ex.copy()
    ex_purge[59] = ent[80] - 3 * 86_400
    with pytest.raises(mcv.CausalityViolationError, match="PURGE_GAP_BREACH"):
        mcv.verify_fold_causality(tr_ok, va_ok, ent, ex_purge, purge_days=5, embargo_days=10)

    # Negative Mutation C: Trade closes 10 days before val_start (clears purge=5, breaches purge+embargo=15)
    ex_embargo = ex.copy()
    ex_embargo[59] = ent[80] - 10 * 86_400
    with pytest.raises(mcv.CausalityViolationError, match="EMBARGO_GAP_BREACH"):
        mcv.verify_fold_causality(tr_ok, va_ok, ent, ex_embargo, purge_days=5, embargo_days=10)

    # Negative Mutation D: Reverse-time fold (train contains row after val_start)
    tr_rev = np.append(tr_ok, 95)
    va_rev = np.array([i for i in va_ok if i != 95], dtype=np.int64)
    with pytest.raises(mcv.CausalityViolationError, match="REVERSE_TIME_LEAKAGE"):
        mcv.verify_fold_causality(tr_rev, va_rev, ent, ex, purge_days=5, embargo_days=10)

    # Negative Mutation E: Index overlap between train and val
    tr_dup = np.append(tr_ok, 80)
    with pytest.raises(mcv.CausalityViolationError, match="FOLD_OVERLAP_DETECTED"):
        mcv.verify_fold_causality(tr_dup, va_ok, ent, ex, purge_days=5, embargo_days=10)

    # Negative Mutation F: Holdout 2025-01-01 date fails closed
    ent_holdout = ent.copy()
    ex_holdout = ex.copy()
    ent_holdout[-1] = mcv.DEV_CUTOFF_SEC
    ex_holdout[-1] = mcv.DEV_CUTOFF_SEC + 3600
    with pytest.raises(mcv.HoldoutCutoffBreachError, match="HOLDOUT"):
        mcv.verify_fold_causality(tr_ok, va_ok, ent_holdout, ex_holdout, purge_days=5, embargo_days=10)


# ---------------------------------------------------------------------------
# 3. Inside-Fold Feature Pruning (`8 <= k <= 12`) & Val-Perturbation Invariance
# ---------------------------------------------------------------------------


def test_inside_fold_feature_pruning_range_collinearity_and_val_invariance() -> None:
    ds = _make_synthetic_trade_dataset(n_trades=900, seed=21, signal_strength=1.6)
    x_all = ds["X"]
    y_all = ds["y"]
    fnames = ds["feature_names"]

    splitter = mcv.ExpandingPurgedWalkForwardSplitter(
        n_splits=4, purge_days=5, embargo_days=10, min_train_samples=300
    )
    folds = list(splitter.split(ds["entry_ts"], ds["exit_ts"]))

    for tr_idx, va_idx in folds:
        res_clean = mcv.select_inside_fold_features(
            x_all[tr_idx], y_all[tr_idx], fnames, min_k=8, max_k=12
        )
        assert 8 <= res_clean["k"] <= 12
        assert len(res_clean["selected_indices"]) == res_clean["k"]
        assert len(res_clean["selected_names"]) == res_clean["k"]
        assert len(set(res_clean["selected_names"])) == res_clean["k"]

        # True signal features should dominate the top picks & collinear duplicates should be pruned
        assert len(res_clean["dropped_correlated"]) >= 3
        assert len(res_clean["dropped_constant"]) == 2
        top_names = set(res_clean["selected_names"])
        # At least 4 of the 5 true orthogonal signal groups must be retained
        # (collinear twin may occasionally edge out original by noise, so check representative groups)
        signal_groups = (
            {"atr14_pct", "atr5_over_atr20", "parkinson_vol_10d"},
            {"adx14_causal", "ema20_slope_atr"},
            {"breakout_zscore_20"},
            {"spread_over_atr_ratio", "spread_zscore_20"},
            {"recent_10_wr_causal"},
        )
        covered_groups = sum(1 for grp in signal_groups if grp & top_names)
        assert covered_groups >= 4

        # Val-set perturbation invariance: massively corrupt X_val and flip y_val -> bit-identical pruning!
        x_pert = x_all.copy()
        y_pert = y_all.copy()
        x_pert[va_idx] = x_pert[va_idx] * 999.0 + 12345.0
        y_pert[va_idx] = 1.0 - y_pert[va_idx]

        res_pert = mcv.select_inside_fold_features(
            x_pert[tr_idx], y_pert[tr_idx], fnames, min_k=8, max_k=12
        )
        assert res_pert == res_clean


# ---------------------------------------------------------------------------
# 4. Brier Skill > 0 Gate, Engine Balance Guard, 24m Slippage & Law 13 Honesty
# ---------------------------------------------------------------------------


def test_brier_skill_non_positive_hard_rejects_even_with_higher_ev() -> None:
    rng = np.random.default_rng(33)
    n = 420
    y_true = (rng.uniform(0.0, 1.0, size=n) < 0.50).astype(np.float64)
    # Deliberately miscalibrated probabilities: Brier Skill <= 0 (worse than climatology 0.25)
    y_prob = np.where(y_true >= 0.5, 0.25, 0.75)
    net_r = np.where(y_true >= 0.5, 1.8, -1.0)
    engs = [_ENGINES_7[i % 7] for i in range(n)]
    # Even if an adversarial sizing vector lifts EV/PF, Brier Skill <= 0 MUST hard-reject!
    good_sizes = np.where(y_true >= 0.5, 1.2, 0.6)

    ev = mcv.evaluate_oof_brier_and_economics(
        y_true,
        y_prob,
        net_r,
        engs,
        position_sizes=good_sizes,
    )
    assert ev["brier_skill_score"] <= 0.0
    assert ev["gates"]["brier_skill_positive"] is False
    assert ev["verdict"] == mcv.VERDICT_REJECT
    assert any("BRIER_SKILL_NON_POSITIVE" in r for r in ev["rejection_reasons"])
    assert ev["oos_label"] == mcv.CONSUMED_CLB_TAG


def test_engine_balance_guard_rejects_dropping_any_engine() -> None:
    n = 490
    y_true = np.array([1.0 if i % 2 == 0 else 0.0 for i in range(n)], dtype=np.float64)
    # Strong calibrated probabilities (Brier Skill > 0.40)
    y_prob = np.where(y_true >= 0.5, 0.85, 0.15)
    net_r = np.where(y_true >= 0.5, 1.08, -1.00)
    engs = [_ENGINES_7[i % 7] for i in range(n)]

    # Adversarially drop 100% of engine E3_GBPUSD_VH while keeping others at 80%+
    sizes = np.where(y_prob > 0.20, 1.0, 0.0)
    for i, e in enumerate(engs):
        if e == "E3_GBPUSD_VH":
            sizes[i] = 0.0

    ev = mcv.evaluate_oof_brier_and_economics(
        y_true,
        y_prob,
        net_r,
        engs,
        position_sizes=sizes,
    )
    assert ev["brier_skill_score"] > 0.0
    assert ev["engine_balance"]["passed"] is False
    assert ev["engine_balance"]["dropped_engines"] == ["E3_GBPUSD_VH"]
    assert ev["engine_balance"]["min_engine_retention_ratio"] == 0.0
    assert ev["verdict"] == mcv.VERDICT_REJECT
    assert any("ENGINE_BALANCE_BREACH" in r for r in ev["rejection_reasons"])


def test_24m_slippage_breakeven_promote_and_reject_verdicts() -> None:
    # Build 3.5-year pre-2025 timeline (2021-01-01 .. 2024-06-30) across all 7 engines
    n = 700
    t0 = int(datetime(2021, 1, 2, tzinfo=UTC).timestamp())
    entry_ts = t0 + np.arange(n, dtype=np.int64) * np.int64(int(1.8 * 86_400))
    assert int(np.max(entry_ts)) < mcv.DEV_CUTOFF_SEC

    rng = np.random.default_rng(77)
    y_true = np.zeros(n, dtype=np.float64)
    y_true[::2] = 1.0  # exact 50% base winrate
    engs = [_ENGINES_7[i % 7] for i in range(n)]

    # Baseline 1.0x EV = 0.5 * 1.08 + 0.5 * (-1.00) = +0.04 R -> with base_cost_r=0.08, breakeven = 1.50x!
    net_r = np.where(y_true >= 0.5, 1.08, -1.00)

    # Case A: Calibrated ML identifies 40% of losers as toxic (keeps 100% wins + 60% losses => 80%/engine)
    # Kept trades: 350 wins (+1.08) + 210 losses (-1.00) => EV = +0.30 R => breakeven = 4.75x >= 1.75x!
    y_prob_good = np.where(y_true >= 0.5, 0.72, 0.35)
    # Mark bottom 20% (140 losers evenly spread across all 7 engines) as low prob 0.18
    loser_idx = np.flatnonzero(y_true < 0.5)
    toxic_losers = loser_idx[::2][:140]
    y_prob_good[toxic_losers] = 0.18
    # Add tiny jitter to break exact ties
    y_prob_good = np.clip(y_prob_good + rng.normal(0.0, 0.01, size=n), 0.05, 0.95)
    sizes_good = np.ones(n, dtype=np.float64)
    sizes_good[toxic_losers] = 0.0

    ev_promote = mcv.evaluate_oof_brier_and_economics(
        y_true,
        y_prob_good,
        net_r,
        engs,
        slippage_mults=(1.0, 1.5, 1.75, 2.0),
        position_sizes=sizes_good,
        base_cost_r=0.08,
        entry_ts=entry_ts,
        oos_label=mcv.CONSUMED_CLB_TAG,
    )
    assert math.isclose(ev_promote["slippage_breakeven_24m"]["baseline_v103_median_mult"], 1.50, abs_tol=0.05)
    assert ev_promote["slippage_breakeven_24m"]["ml_v104_median_mult"] >= 1.75
    assert ev_promote["brier_skill_score"] > 0.0
    assert ev_promote["roc_auc"] > 0.70
    assert ev_promote["engine_balance"]["passed"] is True
    assert ev_promote["engine_balance"]["min_engine_retention_ratio"] >= 0.70
    assert ev_promote["verdict"] == mcv.VERDICT_PROMOTE
    assert ev_promote["oos_label"] == mcv.CONSUMED_CLB_TAG
    assert "BLIND" not in json.dumps(ev_promote).upper()

    # Case B: Positive Brier Skill + balanced engines, but sizing only nudges breakeven to ~1.58x (< 1.75x) -> REJECT!
    sizes_weak = np.ones(n, dtype=np.float64)
    sizes_weak[toxic_losers[:7]] = 0.0  # drops only 1 loser per engine -> barely moves EV (+0.05 R -> 1.625x < 1.75x)
    ev_weak = mcv.evaluate_oof_brier_and_economics(
        y_true,
        y_prob_good,
        net_r,
        engs,
        slippage_mults=(1.0, 1.5, 1.75, 2.0),
        position_sizes=sizes_weak,
        base_cost_r=0.08,
        entry_ts=entry_ts,
        oos_label=mcv.CONSUMED_CLB_TAG,
    )
    assert ev_weak["brier_skill_score"] > 0.0
    assert ev_weak["slippage_breakeven_24m"]["ml_v104_median_mult"] < 1.75
    assert ev_weak["slippage_breakeven_24m"]["passed"] is False
    assert ev_weak["verdict"] == mcv.VERDICT_REJECT
    assert any("SLIPPAGE_BREAKEVEN_24M_FAILED" in r for r in ev_weak["rejection_reasons"])


def test_law13_honesty_and_holdout_date_guards() -> None:
    for forbidden_tag in ("BLIND", "BLIND_CLUSTER_B", "blind_oos", "DEV_BLIND_2021_2024"):
        with pytest.raises(mcv.Law13HonestyError, match="LAW13_HONESTY_VIOLATION"):
            mcv.validate_oos_label(forbidden_tag)

    y = np.array([0.0, 1.0, 0.0, 1.0])
    p = np.array([0.3, 0.7, 0.3, 0.7])
    r = np.array([-1.0, 1.5, -1.0, 1.5])
    e = ["E1_USDJPY_TOKYO"] * 4

    with pytest.raises(mcv.Law13HonestyError, match="LAW13_HONESTY_VIOLATION"):
        mcv.evaluate_oof_brier_and_economics(y, p, r, e, oos_label="BLIND_CLUSTER_B")

    # 2025-01-01 date in entry_ts fails closed
    ts_bad = np.array([1_700_000_000, 1_700_086_400, 1_700_172_800, mcv.DEV_CUTOFF_SEC], dtype=np.int64)
    with pytest.raises(mcv.HoldoutCutoffBreachError, match="HOLDOUT"):
        mcv.evaluate_oof_brier_and_economics(y, p, r, e, entry_ts=ts_bad)


# ---------------------------------------------------------------------------
# 5. DuckDB `wave4_ml_m48` Budget Ledger (`<= 48` Trials Fail-Closed)
# ---------------------------------------------------------------------------


def test_duckdb_budget_ledger_48_trials_and_49th_raises(tmp_path: Path) -> None:
    pytest.importorskip("duckdb")
    db_file = tmp_path / "wave4_ml_m48.duckdb"

    # Reject attempting to raise max_trials > 48
    with pytest.raises(ValueError, match="max_trials"):
        mcv.Wave4MlBudgetLedger(db_path=db_file, max_trials=49)

    with mcv.Wave4MlBudgetLedger(db_path=db_file, max_trials=48) as ledger:
        assert ledger.get_trial_count() == 0
        assert ledger.remaining_budget() == 48

        # Belt-and-suspenders: cannot record BLIND label, 2025 cutoff, or PROMOTE with Brier Skill <= 0
        with pytest.raises(mcv.Law13HonestyError):
            ledger.record_trial(
                trial_id="bad_blind",
                family_name="logit_l2",
                params={"l2_reg": 1.0},
                evaluation=_make_stub_evaluation(brier_skill=0.05, verdict=mcv.VERDICT_PROMOTE),
                n_folds=5,
                n_features_selected=10,
                oos_label="BLIND",
            )
        with pytest.raises(mcv.HoldoutCutoffBreachError):
            ledger.record_trial(
                trial_id="bad_holdout",
                family_name="logit_l2",
                params={"l2_reg": 1.0},
                evaluation=_make_stub_evaluation(brier_skill=0.05, verdict=mcv.VERDICT_PROMOTE),
                n_folds=5,
                n_features_selected=10,
                cutoff_utc="2025-01-01",
            )
        with pytest.raises(ValueError, match="BRIER_SKILL_GATE_BREACH"):
            ledger.record_trial(
                trial_id="bad_brier_promote",
                family_name="logit_l2",
                params={"l2_reg": 1.0},
                evaluation=_make_stub_evaluation(brier_skill=-0.01, verdict=mcv.VERDICT_PROMOTE),
                n_folds=5,
                n_features_selected=10,
            )

        # Record exactly 48 valid trials across all 5 model families
        for i in range(48):
            fam = mcv.MODEL_FAMILIES[i % len(mcv.MODEL_FAMILIES)]
            is_prom = i % 6 == 0
            rec = ledger.record_trial(
                trial_id=f"trial_{i + 1:02d}",
                family_name=fam,
                params={"trial_idx": i + 1, "family": fam},
                evaluation=_make_stub_evaluation(
                    brier_skill=0.03 + 0.001 * i if is_prom else -0.005,
                    verdict=mcv.VERDICT_PROMOTE if is_prom else mcv.VERDICT_REJECT,
                ),
                n_folds=5,
                n_features_selected=10,
            )
            assert rec["trial_seq"] == i + 1
            assert rec["remaining_trials"] == 48 - (i + 1)

        assert ledger.get_trial_count() == 48
        assert ledger.remaining_budget() == 0

        # Duplicate trial_id rejected
        with pytest.raises(ValueError, match="DUPLICATE_TRIAL_ID"):
            ledger.record_trial(
                trial_id="trial_01",
                family_name="logit_l2",
                params={"trial_idx": 1},
                evaluation=_make_stub_evaluation(brier_skill=-0.01, verdict=mcv.VERDICT_REJECT),
                n_folds=5,
                n_features_selected=10,
            )

        # 49th trial MUST fail closed with BudgetExceededError!
        with pytest.raises(mcv.BudgetExceededError, match="ML_TRIAL_BUDGET_EXCEEDED"):
            ledger.record_trial(
                trial_id="trial_49_overflow",
                family_name="logit_l2",
                params={"trial_idx": 49},
                evaluation=_make_stub_evaluation(brier_skill=0.08, verdict=mcv.VERDICT_PROMOTE),
                n_folds=5,
                n_features_selected=10,
            )
        assert ledger.get_trial_count() == 48

    # Reopen from disk and verify persistence + 49th still blocked
    with mcv.Wave4MlBudgetLedger(db_path=db_file, max_trials=48) as ledger2:
        summary = ledger2.summary()
        assert summary["recorded_trials"] == 48
        assert summary["remaining_trials"] == 0
        assert summary["promoted_trials"] == 8
        assert summary["holdout_rows_analysed"] == 0
        assert summary["best_promoted"] is not None
        with pytest.raises(mcv.BudgetExceededError, match="ML_TRIAL_BUDGET_EXCEEDED"):
            ledger2.record_trial(
                trial_id="trial_49_after_reopen",
                family_name="catboost",
                params={"depth": 3},
                evaluation=_make_stub_evaluation(brier_skill=0.08, verdict=mcv.VERDICT_PROMOTE),
                n_folds=5,
                n_features_selected=10,
            )


# ---------------------------------------------------------------------------
# 6. All 5 Model Families + Native Attribution (Zero `shap`, Zero `hmmlearn`)
# ---------------------------------------------------------------------------


def test_pure_numpy_adapters_and_causal_jump_hmm_without_ml_wheels() -> None:
    ds = _make_synthetic_trade_dataset(n_trades=650, seed=55, signal_strength=1.5)
    x = ds["X"]
    y = ds["y"]
    fnames = ds["feature_names"]

    # Pure-NumPy logit_l2
    m_logit = mcv.create_model_adapter("logit_l2", backend="numpy", l2_reg=2.0)
    m_logit.fit(x[:400], y[:400], feature_names=fnames)
    p_logit = m_logit.predict_proba(x[400:450])
    assert p_logit.shape == (50,) and bool(np.all((p_logit > 0.0) & (p_logit < 1.0)))
    exp_logit = mcv.LogitL2Adapter.explain_attributions(m_logit, x[400:450])
    assert exp_logit["method"] == "exact_linear_coefficients"
    recon = np.sum(exp_logit["contributions"], axis=1) + exp_logit["expected_value"]
    assert np.allclose(recon, np.log(p_logit / (1.0 - p_logit)), atol=1e-6)

    # Pure-NumPy Causal Forward-Only Jump-HMM (zero hmmlearn, zero future leakage!)
    m_hmm = mcv.create_model_adapter("regime_gmm_jump", backend="jump_hmm_numpy", n_regimes=3, jump_penalty=1.5)
    m_hmm.fit(x[:400], y[:400], feature_names=fnames)
    x_val = x[400:460].copy()
    p_hmm_orig = m_hmm.predict_proba(x_val)
    # Perturb second half of validation sequence by 10x -> first half MUST stay 0-bit identical (forward-only!)
    x_val_pert = x_val.copy()
    x_val_pert[30:] = x_val_pert[30:] * 10.0 + 50.0
    p_hmm_pert = m_hmm.predict_proba(x_val_pert)
    assert np.array_equal(p_hmm_orig[:30], p_hmm_pert[:30])
    exp_hmm = m_hmm.explain_attributions(x_val[:10])
    assert exp_hmm["method"] == "regime_margin_perturbation"
    assert exp_hmm["contributions"].shape == (10, 24)
    assert bool(np.all(np.isfinite(exp_hmm["contributions"])))

    # Pure-NumPy Calibrated Bet Sizing (both Platt and Isotonic PAVA)
    for cal_m in ("platt", "isotonic"):
        m_cal = mcv.create_model_adapter(
            "calibrated_bet_sizing",
            base_family="logit_l2",
            base_params={"backend": "numpy"},
            calibration_method=cal_m,
            size_floor=0.25,
            size_cap=1.25,
        )
        m_cal.fit(x[:400], y[:400], feature_names=fnames)
        p_cal = m_cal.predict_proba(x[400:450])
        s_cal = m_cal.predict_size(x[400:450], mode="afml_bet_sizing")
        assert p_cal.shape == (50,) and bool(np.all(np.isfinite(p_cal)))
        assert bool(np.all((s_cal >= 0.25 - 1e-9) & (s_cal <= 1.25 + 1e-9)))
        exp_cal = m_cal.explain_attributions(x[400:450])
        assert exp_cal["method"] == "calibrated_chain_rule"
        assert exp_cal["contributions"].shape == (50, 24)

    # End-to-end walk-forward CV with pure-NumPy adapter (no sklearn/lgb/cb/duckdb needed!)
    wf_res = mcv.run_purged_walkforward_cv(
        x,
        y,
        ds["entry_ts"],
        ds["exit_ts"],
        ds["net_r"],
        ds["engine_ids"],
        family_name="logit_l2",
        model_params={"backend": "numpy", "l2_reg": 2.0},
        feature_names=fnames,
        n_splits=4,
        purge_days=5,
        embargo_days=10,
        min_train_samples=250,
    )
    assert wf_res["oos_label"] == mcv.CONSUMED_CLB_TAG
    assert wf_res["holdout_rows_analysed"] == 0
    assert wf_res["order_send_count"] == 0
    assert len(wf_res["folds"]) == 4
    assert all(8 <= f["n_features_selected"] <= 12 for f in wf_res["folds"])
    assert wf_res["evaluation"]["brier_skill_score"] > 0.0
    assert wf_res["verdict"] in (mcv.VERDICT_PROMOTE, mcv.VERDICT_REJECT)


def test_all_5_model_families_fit_predict_and_native_shap(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    pytest.importorskip("sklearn")
    pytest.importorskip("lightgbm")
    pytest.importorskip("catboost")

    # Run inside tmp_path to prove CatBoost creates ZERO `catboost_info` directory!
    monkeypatch.chdir(tmp_path)

    ds = _make_synthetic_trade_dataset(n_trades=500, seed=88, signal_strength=1.5)
    x_tr, y_tr = ds["X"][:360], ds["y"][:360]
    x_va = ds["X"][360:420]
    fnames = ds["feature_names"]

    expected_methods = {
        "logit_l2": "exact_linear_coefficients",
        "lightgbm": "lightgbm_pred_contrib",
        "catboost": "catboost_shap_values",
        "regime_gmm_jump": "regime_margin_perturbation",
        "calibrated_bet_sizing": "calibrated_chain_rule",
    }

    for fam in mcv.MODEL_FAMILIES:
        kwargs: dict[str, Any] = {"random_state": 42}
        if fam == "lightgbm":
            kwargs.update({"n_estimators": 25, "max_depth": 3, "num_leaves": 7})
        elif fam == "catboost":
            kwargs.update({"iterations": 30, "depth": 3})
        elif fam == "regime_gmm_jump":
            kwargs.update({"backend": "gmm", "n_regimes": 3})
        elif fam == "calibrated_bet_sizing":
            kwargs.update({"base_family": "logit_l2", "calibration_method": "platt"})

        mdl = mcv.create_model_adapter(fam, **kwargs)
        mdl.fit(x_tr, y_tr, feature_names=fnames)
        probs = mdl.predict_proba(x_va)
        assert probs.shape == (60,)
        assert bool(np.all(np.isfinite(probs)))
        assert bool(np.all((probs > 0.0) & (probs < 1.0)))

        exp = mdl.explain_attributions(x_va, feature_names=fnames)
        assert exp["method"] == expected_methods[fam]
        assert exp["contributions"].shape == (60, 24)
        assert bool(np.all(np.isfinite(exp["contributions"])))
        assert len(exp["mean_abs_importance"]) == 24

        # Verify exact TreeSHAP / LinearSHAP margin additivity for logit_l2, lightgbm, and catboost
        if fam in ("logit_l2", "lightgbm", "catboost"):
            margin_recon = np.sum(exp["contributions"], axis=1) + exp["expected_value"]
            prob_recon = 1.0 / (1.0 + np.exp(-np.clip(margin_recon, -35.0, 35.0)))
            assert np.allclose(prob_recon, probs, atol=1e-4)

    # Confirm ZERO `shap` / `hmmlearn` imported and ZERO `catboost_info` dir written
    assert "shap" not in sys.modules
    assert "hmmlearn" not in sys.modules
    assert not (tmp_path / "catboost_info").exists()


def test_end_to_end_walkforward_cv_with_duckdb_ledger_all_families(tmp_path: Path) -> None:
    pytest.importorskip("duckdb")
    pytest.importorskip("sklearn")
    pytest.importorskip("lightgbm")
    pytest.importorskip("catboost")

    ds = _make_synthetic_trade_dataset(n_trades=700, seed=123, signal_strength=1.4)
    db_file = tmp_path / "wave4_ml_m48.duckdb"

    family_configs: list[tuple[str, dict[str, Any], str]] = [
        ("logit_l2", {"l2_reg": 2.0}, "toxic_filter"),
        ("lightgbm", {"n_estimators": 25, "max_depth": 3, "num_leaves": 7}, "toxic_filter"),
        ("catboost", {"iterations": 30, "depth": 3}, "toxic_filter"),
        ("regime_gmm_jump", {"backend": "gmm", "n_regimes": 3}, "toxic_filter"),
        ("calibrated_bet_sizing", {"base_family": "logit_l2", "calibration_method": "platt"}, "afml_bet_sizing"),
    ]

    with mcv.Wave4MlBudgetLedger(db_path=db_file, max_trials=48) as ledger:
        for idx, (fam, params, smode) in enumerate(family_configs, start=1):
            res = mcv.run_purged_walkforward_cv(
                ds["X"],
                ds["y"],
                ds["entry_ts"],
                ds["exit_ts"],
                ds["net_r"],
                ds["engine_ids"],
                family_name=fam,
                model_params=params,
                feature_names=ds["feature_names"],
                n_splits=4,
                purge_days=5,
                embargo_days=10,
                min_train_samples=250,
                sizing_mode=smode,
                ledger=ledger,
                trial_id=f"w4_cv_smoke_{idx:02d}_{fam}",
            )
            assert res["oos_label"] == mcv.CONSUMED_CLB_TAG
            assert "BLIND" not in json.dumps(res["evaluation"]).upper()
            assert res["holdout_rows_analysed"] == 0
            assert res["order_send_count"] == 0
            assert len(res["folds"]) == 4
            assert all(8 <= f["n_features_selected"] <= 12 for f in res["folds"])
            assert res["ledger_receipt"] is not None
            assert res["ledger_receipt"]["trial_seq"] == idx

        assert ledger.get_trial_count() == 5
        assert ledger.remaining_budget() == 43


# ---------------------------------------------------------------------------
# 7. Local Cache Real PORT_7E Dev Integration Proof (Skipped in Minimal CI)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_port7e_real_dev_cache_walkforward_cv_smoke(tmp_path: Path) -> None:
    pytest.importorskip("duckdb")
    bundle = mf.build_port7e_dev_feature_bundle(
        portfolio_key="PORT_7E_P28_CORE",
        cutoff_utc="2024-12-31",
        verify_sha=True,
        verify_causality=False,
    )
    entry_ts = np.array([int(t["entry_ts"]) for t in bundle["trades"]], dtype=np.int64)
    exit_ts = np.array([int(t["exit_ts"]) for t in bundle["trades"]], dtype=np.int64)
    engine_ids = [str(t["engine_id"]) for t in bundle["trades"]]

    db_file = tmp_path / "port7e_smoke_m48.duckdb"
    with mcv.Wave4MlBudgetLedger(db_path=db_file, max_trials=48) as ledger:
        res = mcv.run_purged_walkforward_cv(
            bundle["X"],
            bundle["y"],
            entry_ts,
            exit_ts,
            bundle["net_R"],
            engine_ids,
            family_name="logit_l2",
            model_params={"l2_reg": 2.0},
            feature_names=mf.FEATURE_NAMES_24,
            n_splits=5,
            purge_days=5,
            embargo_days=10,
            min_train_samples=300,
            oos_label=mcv.CONSUMED_CLB_TAG,
            ledger=ledger,
            trial_id="port7e_dev_smoke_logit_l2",
        )
        assert res["oos_label"] == mcv.CONSUMED_CLB_TAG
        assert res["holdout_rows_analysed"] == 0
        assert res["order_send_count"] == 0
        assert len(res["folds"]) == 5
        assert all(8 <= f["n_features_selected"] <= 12 for f in res["folds"])
        assert all(f["observed_gap_days"] >= 15.0 for f in res["folds"])
        assert res["evaluation"]["engine_balance"]["n_engines"] == 7
        assert ledger.get_trial_count() == 1
