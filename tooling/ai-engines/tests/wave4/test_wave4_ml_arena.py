"""Tests for Wave 4 5-Family ML Arena Runner (`run_ml_arena_5families.py`, `W4-G04`).

Covers:
  1. Lazy-import purity & zero bare `assert`s under clean `python -O` subprocess (`-m "not local_cache"`).
  2. Pre-registered 5-family grid validation (`36 <= 48`, all 5 families covered, fail-closed budget cap).
  3. Holdout `2025+` seal & Law 13 honesty (`CONSUMED_DEV_CLB_TEMPORAL_OOS`, zero forbidden tags) under `-O`.
  4. Offline pure-NumPy arena execution on BOTH noise-only data (honest `REJECT_ML_KEEP_V103` +
     `RESEARCH_PROTOTYPE_NOT_LIVE_APPROVED`) AND strong-signal synthetic data (honest `PROMOTE_V104_ML`).
  5. Full 5-family arena smoke test with `sklearn`/`lightgbm`/`catboost`/`duckdb` (via `pytest.importorskip`),
     verifying zero `catboost_info/`, zero `shap`/`hmmlearn`, DuckDB `<= 48`, and `500` golden `float32`
     parity vectors matching model `predict_proba` to `< 1e-6`.
  6. `@pytest.mark.local_cache` production artifact verification (READ-ONLY DuckDB inspection,
     `wave4_ml_arena_summary.json`, `report_sha256`, `holdout_rows_analysed == 0`, zero forbidden label,
     and `wave4_ml_parity_500.npz` / `wave4_ml_best_prototype.npz` shape `(500, k)` finite `float32`).
"""

from __future__ import annotations

import ast
import json
import pickle
import subprocess
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_factory.wave4 import ml_features_24 as mf
from quant_factory.wave4 import ml_walkforward_cv as mcv
from quant_factory.wave4 import run_ml_arena_5families as arena

ROOT = Path(__file__).resolve().parents[4]
FORBIDDEN_BLIND_TOKEN = "BL" + "IND"


# ---------------------------------------------------------------------------
# Deterministic Synthetic Dataset Generators (Offline, Zero Local Cache)
# ---------------------------------------------------------------------------


def _make_synthetic_arena_dataset(
    *,
    n_trades: int = 900,
    seed: int = 42,
    signal_strength: float = 0.0,
    base_edge_r: float = 0.05,
) -> dict[str, Any]:
    """Generate deterministic multi-engine Dev dataset strictly inside 2018-2024."""
    rng = np.random.default_rng(seed)
    n_features = len(mf.FEATURE_NAMES_24)
    x = rng.normal(0.0, 1.0, size=(n_trades, n_features)).astype(np.float32)

    # Spread trades chronologically from 2018-02-01 through 2024-11-15 (~2.5 days apart)
    start_ts = 1_517_443_200  # 2018-02-01T00:00:00Z
    end_ts = 1_731_628_800  # 2024-11-15T00:00:00Z
    entry_ts = np.linspace(start_ts, end_ts, n_trades, dtype=np.int64)
    exit_ts = entry_ts + 21_600  # 6-hour intraday holding window

    engines = [
        "E1_USDJPY_TOKYO",
        "E2_USDJPY_EXP80",
        "E3_GBPUSD_VH",
        "E4_US100_SESS40",
        "E5_US100_RS1130",
        "E6_EURJPY_VOLCOMP",
        "E7_USDJPY_NY10ET",
    ]
    engine_ids = [engines[i % len(engines)] for i in range(n_trades)]

    if signal_strength > 0.0:
        latent = (
            signal_strength * (0.9 * x[:, 0] - 0.8 * x[:, 6] + 0.7 * x[:, 11] - 0.6 * x[:, 12])
            + rng.normal(0.0, 0.35, size=n_trades)
        )
        probs_true = 1.0 / (1.0 + np.exp(-np.clip(latent, -15.0, 15.0)))
        y = (rng.uniform(0.0, 1.0, size=n_trades) < probs_true).astype(np.float64)
        # Losses are slightly sharper when latent is negative so toxic filtering lifts 24m breakeven >= 1.75x
        net_r = np.where(y > 0.5, 1.15 + base_edge_r, -1.00).astype(np.float64)
    else:
        # Pure i.i.d. noise independent of X -> honest ML must fail Brier Skill > 0!
        y = (rng.uniform(0.0, 1.0, size=n_trades) < 0.49).astype(np.float64)
        net_r = np.where(y > 0.5, 1.09, -0.95).astype(np.float64)

    return {
        "X": x,
        "y": y,
        "entry_ts": entry_ts,
        "exit_ts": exit_ts,
        "net_r": net_r,
        "engine_ids": engine_ids,
        "feature_names": mf.FEATURE_NAMES_24,
    }


# ---------------------------------------------------------------------------
# 1. Lazy Import Purity, Zero Bare `assert`, and Grid Budget Validation
# ---------------------------------------------------------------------------


def test_lazy_imports_zero_bare_asserts_and_clean_python_O_import() -> None:
    module_path = ROOT / "tooling" / "ai-engines" / "quant_factory" / "wave4" / "run_ml_arena_5families.py"
    src = module_path.read_text(encoding="utf-8")
    tree = ast.parse(src, filename=str(module_path))

    # Zero bare Python `assert` statements (100% active under python -O / -OO)
    assert_nodes = [node for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert assert_nodes == [], f"Found bare assert statements on lines {[n.lineno for n in assert_nodes]}"

    # Clean `python -O` subprocess must NOT eagerly import optional ML or DB wheels
    code = (
        "import sys; "
        "from quant_factory.wave4 import run_ml_arena_5families as a; "
        "forbidden = ['sklearn', 'lightgbm', 'catboost', 'duckdb', 'scipy', 'pandas', 'shap', 'hmmlearn', 'onnx']; "
        "loaded = [m for m in forbidden if m in sys.modules]; "
        "assert not loaded, f'Eagerly imported: {loaded}'; "
        "assert a.ORDER_SEND_CAPABLE is False and a.ORDER_SEND_COUNT == 0; "
        "assert a.HOLDOUT_CUTOFF_DATE == '2024-12-31'; "
        "print('CLEAN_IMPORT_OK')"
    )
    proc = subprocess.run(
        [sys.executable, "-O", "-c", code],
        cwd=str(ROOT / "tooling" / "ai-engines"),
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr}\nstdout={proc.stdout}"
    assert "CLEAN_IMPORT_OK" in proc.stdout


def test_preregistered_grid_bounds_and_fail_closed_validation() -> None:
    grid = arena.build_preregistered_arena_grid(random_state=42)
    validated = arena.validate_arena_grid(grid, max_trials=48, require_all_five_families=True)
    assert 30 <= len(validated) <= 48
    by_family = {fam: sum(1 for g in validated if g["family_name"] == fam) for fam in mcv.MODEL_FAMILIES}
    assert all(cnt >= 6 for cnt in by_family.values()), f"Unbalanced grid: {by_family}"

    # Oversized grid (> 48) MUST fail closed
    too_big = [
        {
            "trial_id": f"t_{i:02d}",
            "family_name": mcv.MODEL_FAMILIES[i % len(mcv.MODEL_FAMILIES)],
            "model_params": {},
            "sizing_mode": "afml_bet_sizing"
            if mcv.MODEL_FAMILIES[i % len(mcv.MODEL_FAMILIES)] == "calibrated_bet_sizing"
            else "toxic_filter",
        }
        for i in range(49)
    ]
    with pytest.raises(ValueError, match="ARENA_GRID_EXCEEDS_BUDGET"):
        arena.validate_arena_grid(too_big, max_trials=48, require_all_five_families=True)

    # Missing family MUST fail closed when require_all_five_families=True
    with pytest.raises(ValueError, match="INCOMPLETE_5FAMILY_GRID"):
        arena.validate_arena_grid(arena.build_numpy_smoke_grid(), max_trials=48, require_all_five_families=True)


# ---------------------------------------------------------------------------
# 2. Holdout 2025+ Seal & Law 13 Honesty Fail-Closed Guards
# ---------------------------------------------------------------------------


def test_holdout_2025_and_law13_honesty_rejected_fail_closed(tmp_path: Path) -> None:
    ds = _make_synthetic_arena_dataset(n_trades=450, seed=7, signal_strength=0.0)

    # Law 13: forbidden label MUST fail closed
    with pytest.raises(mcv.Law13HonestyError, match="LAW13_HONESTY_VIOLATION"):
        arena.run_5family_ml_arena(
            ds["X"],
            ds["y"],
            ds["entry_ts"],
            ds["exit_ts"],
            ds["net_r"],
            ds["engine_ids"],
            trial_grid=arena.build_numpy_smoke_grid(),
            require_all_five_families=False,
            out_dir=tmp_path / "law13",
            n_splits=3,
            min_train_samples=150,
            oos_label=f"DEV_{FORBIDDEN_BLIND_TOKEN}_OOS",
            use_duckdb_ledger=False,
        )

    # Holdout 2025-01-01 timestamp MUST fail closed
    ent_bad = ds["entry_ts"].copy()
    ext_bad = ds["exit_ts"].copy()
    ent_bad[-1] = mcv.DEV_CUTOFF_SEC
    ext_bad[-1] = mcv.DEV_CUTOFF_SEC + 3600
    with pytest.raises(mcv.HoldoutCutoffBreachError, match="HOLDOUT_TIMESTAMP_BREACH"):
        arena.run_5family_ml_arena(
            ds["X"],
            ds["y"],
            ent_bad,
            ext_bad,
            ds["net_r"],
            ds["engine_ids"],
            trial_grid=arena.build_numpy_smoke_grid(),
            require_all_five_families=False,
            out_dir=tmp_path / "holdout_ts",
            n_splits=3,
            min_train_samples=150,
            use_duckdb_ledger=False,
        )


# ---------------------------------------------------------------------------
# 3. Offline Pure-NumPy Arena: Honest REJECT vs Honest PROMOTE + Parity Export
# ---------------------------------------------------------------------------


def test_offline_noise_dataset_emits_honest_reject_and_research_prototype(tmp_path: Path) -> None:
    ds = _make_synthetic_arena_dataset(n_trades=850, seed=101, signal_strength=0.0)
    out_dir = tmp_path / "ml_reject"
    summary = arena.run_5family_ml_arena(
        ds["X"],
        ds["y"],
        ds["entry_ts"],
        ds["exit_ts"],
        ds["net_r"],
        ds["engine_ids"],
        trial_grid=arena.build_numpy_smoke_grid(random_state=42),
        require_all_five_families=False,
        out_dir=out_dir,
        n_splits=4,
        min_train_samples=200,
        n_parity_samples=500,
        use_duckdb_ledger=False,
    )

    assert summary["w4_g04_status"] == "PASS"
    assert summary["verdict"] == arena.VERDICT_REJECT
    assert summary["prototype_approval_tag"] == arena.TAG_RESEARCH_PROTOTYPE
    assert summary["hard_invariants"]["holdout_rows_analysed"] == 0
    assert summary["hard_invariants"]["order_send_count"] == 0
    assert summary["hard_invariants"]["oos_label"] == mcv.CONSUMED_CLB_TAG
    assert summary["report_sha256"] == arena.compute_report_sha256(
        json.loads((out_dir / arena.SUMMARY_FILENAME).read_text(encoding="utf-8"))
    )
    assert FORBIDDEN_BLIND_TOKEN not in json.dumps(summary).upper()

    # Verify serialized 500 golden parity vectors + white-box JSON + pickle model
    for npz_name in (arena.PARITY_NPZ_FILENAME, arena.BEST_PROTOTYPE_NPZ_FILENAME):
        npz_path = out_dir / npz_name
        assert npz_path.is_file()
        with np.load(npz_path, allow_pickle=False) as z:
            x_p = z["X"]
            p_p = z["pred_proba"]
            sel = z["selected_feature_indices"]
            assert x_p.ndim == 2 and x_p.shape[0] == 500
            assert 8 <= x_p.shape[1] <= 12
            assert x_p.dtype == np.float32
            assert p_p.dtype == np.float32 and p_p.shape == (500,)
            assert bool(np.all(np.isfinite(x_p)))
            assert bool(np.all(np.isfinite(p_p)))
            assert sel.shape == (x_p.shape[1],)

    proto_json = json.loads((out_dir / arena.PROTOTYPE_MODEL_JSON_FILENAME).read_text(encoding="utf-8"))
    assert proto_json["approval_tag"] == arena.TAG_RESEARCH_PROTOTYPE
    assert proto_json["holdout_rows_analysed"] == 0
    assert FORBIDDEN_BLIND_TOKEN not in json.dumps(proto_json).upper()

    # Verify white-box linear coefficients reproduce NPZ probabilities to float32 precision
    wb = proto_json["model_whitebox"]
    with np.load(out_dir / arena.PARITY_NPZ_FILENAME, allow_pickle=False) as z:
        x_std = z["X_standardized"].astype(np.float64)
        w = np.asarray(wb["coefficients_std"], dtype=np.float64)
        b = float(wb["intercept_std"])
        p_recon = 1.0 / (1.0 + np.exp(-np.clip(x_std @ w + b, -35.0, 35.0)))
        assert np.allclose(p_recon, z["pred_proba"].astype(np.float64), atol=1e-5)

    # Verify receipt writer produces LF / 0 BOM JSON without forbidden tags
    receipt_p = tmp_path / "audits" / "w4_m1_arena_receipt.json"
    dropbox_p = tmp_path / "dropbox" / "w4-m1-arena.json"
    arena.write_arena_receipt(summary, receipt_path=receipt_p, dropbox_path=dropbox_p)
    for rp in (receipt_p, dropbox_p):
        raw = rp.read_bytes()
        assert not raw.startswith(b"\xef\xbb\xbf")
        assert b"\r\n" not in raw
        assert FORBIDDEN_BLIND_TOKEN not in raw.decode("utf-8").upper()


def test_offline_strong_signal_dataset_emits_honest_promote(tmp_path: Path) -> None:
    ds = _make_synthetic_arena_dataset(n_trades=1000, seed=202, signal_strength=2.2, base_edge_r=0.05)
    out_dir = tmp_path / "ml_promote"
    summary = arena.run_5family_ml_arena(
        ds["X"],
        ds["y"],
        ds["entry_ts"],
        ds["exit_ts"],
        ds["net_r"],
        ds["engine_ids"],
        trial_grid=arena.build_numpy_smoke_grid(random_state=42),
        require_all_five_families=False,
        out_dir=out_dir,
        n_splits=4,
        min_train_samples=220,
        n_parity_samples=500,
        use_duckdb_ledger=False,
    )
    assert summary["verdict"] == arena.VERDICT_PROMOTE
    assert summary["prototype_approval_tag"] == arena.TAG_PROMOTE_CANDIDATE
    assert summary["best_overall_trial"]["brier_skill_score"] > 0.0
    assert summary["best_overall_trial"]["roc_auc"] > 0.50
    assert summary["best_overall_trial"]["slippage_breakeven_24m"] >= 1.75


# ---------------------------------------------------------------------------
# 4. Full 5-Family + DuckDB Integration Smoke Test (Lazy ML Wheels)
# ---------------------------------------------------------------------------


def test_all_5_families_arena_with_duckdb_and_zero_catboost_info(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pytest.importorskip("duckdb")
    pytest.importorskip("sklearn")
    pytest.importorskip("lightgbm")
    pytest.importorskip("catboost")

    monkeypatch.chdir(tmp_path)
    ds = _make_synthetic_arena_dataset(n_trades=900, seed=303, signal_strength=1.4)
    db_file = tmp_path / "wave4_ml_m48.duckdb"
    out_dir = tmp_path / "ml_5fam"

    five_fam_grid = [
        {
            "trial_id": "t5_01_logit",
            "family_name": "logit_l2",
            "model_params": {"l2_reg": 2.0, "random_state": 42},
            "sizing_mode": "toxic_filter",
            "label": "5fam Logit-L2",
        },
        {
            "trial_id": "t5_02_lgbm",
            "family_name": "lightgbm",
            "model_params": {"n_estimators": 25, "max_depth": 2, "num_leaves": 4, "random_state": 42},
            "sizing_mode": "toxic_filter",
            "label": "5fam LightGBM",
        },
        {
            "trial_id": "t5_03_catboost",
            "family_name": "catboost",
            "model_params": {"iterations": 30, "depth": 3, "l2_leaf_reg": 10.0, "random_state": 42},
            "sizing_mode": "toxic_filter",
            "label": "5fam CatBoost",
        },
        {
            "trial_id": "t5_04_gmm",
            "family_name": "regime_gmm_jump",
            "model_params": {"n_regimes": 3, "shrinkage_alpha": 15.0, "backend": "gmm", "random_state": 42},
            "sizing_mode": "toxic_filter",
            "label": "5fam Regime-GMM",
        },
        {
            "trial_id": "t5_05_cal",
            "family_name": "calibrated_bet_sizing",
            "model_params": {
                "base_family": "logit_l2",
                "base_params": {"l2_reg": 2.0},
                "calibration_method": "platt",
                "calibration_frac": 0.25,
                "size_floor": 0.25,
                "size_cap": 1.25,
                "random_state": 42,
            },
            "sizing_mode": "afml_bet_sizing",
            "label": "5fam Calibrated Bet Sizing",
        },
    ]

    summary = arena.run_5family_ml_arena(
        ds["X"],
        ds["y"],
        ds["entry_ts"],
        ds["exit_ts"],
        ds["net_r"],
        ds["engine_ids"],
        trial_grid=five_fam_grid,
        require_all_five_families=True,
        db_path=db_file,
        max_trials=48,
        out_dir=out_dir,
        n_splits=4,
        min_train_samples=200,
        n_parity_samples=500,
        use_duckdb_ledger=True,
    )

    assert set(summary["family_leaderboard"].keys()) == set(mcv.MODEL_FAMILIES)
    assert summary["budget"]["recorded_trials"] == 5
    assert summary["budget"]["remaining_trials"] == 43
    assert not (tmp_path / "catboost_info").exists()
    assert "shap" not in sys.modules
    assert "hmmlearn" not in sys.modules
    assert FORBIDDEN_BLIND_TOKEN not in json.dumps(summary).upper()

    # Reload pickled prototype and verify exact parity against parity_500.npz
    with (out_dir / arena.PROTOTYPE_MODEL_PKL_FILENAME).open("rb") as fh:
        pkl = pickle.load(fh)
    with np.load(out_dir / arena.PARITY_NPZ_FILENAME, allow_pickle=False) as z:
        x_p = z["X"]
        p_saved = z["pred_proba"]
        p_live = pkl["adapter"].predict_proba(x_p.astype(np.float64)).astype(np.float32)
        assert np.allclose(p_live, p_saved, atol=1e-6)


# ---------------------------------------------------------------------------
# 5. Production Local-Cache Artifact Verification (READ-ONLY DuckDB Check)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_production_port7e_arena_artifacts_and_duckdb_read_only() -> None:
    duckdb = pytest.importorskip("duckdb")

    ml_dir = ROOT / ".runtime" / "offensive4" / "ml"
    summary_path = ml_dir / arena.SUMMARY_FILENAME
    db_path = ml_dir / "wave4_ml_m48.duckdb"
    parity_path = ml_dir / arena.PARITY_NPZ_FILENAME
    best_proto_path = ml_dir / arena.BEST_PROTOTYPE_NPZ_FILENAME
    proto_json_path = ml_dir / arena.PROTOTYPE_MODEL_JSON_FILENAME
    proto_pkl_path = ml_dir / arena.PROTOTYPE_MODEL_PKL_FILENAME

    for req in (summary_path, db_path, parity_path, best_proto_path, proto_json_path, proto_pkl_path):
        assert req.is_file(), f"Missing Wave 4 ML arena artifact: {req}"

    summary_raw = summary_path.read_text(encoding="utf-8")
    assert FORBIDDEN_BLIND_TOKEN not in summary_raw.upper()
    summary = json.loads(summary_raw)

    assert summary["w4_g04_status"] == "PASS"
    assert summary["verdict"] in (arena.VERDICT_PROMOTE, arena.VERDICT_REJECT)
    assert summary["hard_invariants"]["order_send_count"] == 0
    assert summary["hard_invariants"]["holdout_rows_analysed"] == 0
    assert summary["hard_invariants"]["holdout_cutoff_date"] == "2024-12-31"
    assert summary["hard_invariants"]["oos_label"] == mcv.CONSUMED_CLB_TAG
    assert summary["dataset"]["n_trades"] == 3122
    assert summary["dataset"]["n_engines"] == 7
    assert summary["dataset"]["max_entry_ts"] < mcv.DEV_CUTOFF_SEC
    assert summary["dataset"]["max_exit_ts"] < mcv.DEV_CUTOFF_SEC
    assert summary["report_sha256"] == arena.compute_report_sha256(summary)
    assert set(summary["family_leaderboard"].keys()) == set(mcv.MODEL_FAMILIES)

    if summary["verdict"] == arena.VERDICT_REJECT:
        assert summary["prototype_approval_tag"] == arena.TAG_RESEARCH_PROTOTYPE
    else:
        assert summary["best_overall_trial"]["brier_skill_score"] > 0.0
        assert summary["best_overall_trial"]["slippage_breakeven_24m"] >= 1.75

    # Verify DuckDB wave4_ml_m48 in READ-ONLY mode (never mutates production budget!)
    con = duckdb.connect(str(db_path), read_only=True)
    try:
        cnt = int(con.execute("SELECT COUNT(*) FROM wave4_ml_m48").fetchone()[0])
        ho = int(con.execute("SELECT MAX(holdout_rows_analysed) FROM wave4_ml_m48").fetchone()[0])
        os_cnt = int(con.execute("SELECT MAX(order_send_count) FROM wave4_ml_m48").fetchone()[0])
        fams = {str(r[0]) for r in con.execute("SELECT DISTINCT family_name FROM wave4_ml_m48").fetchall()}
        oos_labels = {str(r[0]) for r in con.execute("SELECT DISTINCT oos_label FROM wave4_ml_m48").fetchall()}
    finally:
        con.close()

    assert 1 <= cnt <= 48
    assert cnt == int(summary["budget"]["recorded_trials"])
    assert ho == 0
    assert os_cnt == 0
    assert fams == set(mcv.MODEL_FAMILIES)
    assert oos_labels == {mcv.CONSUMED_CLB_TAG}

    # Verify 500 golden parity vectors shape (500, k), finite float32, strict pre-2025 cutoff
    for npz_file in (parity_path, best_proto_path):
        with np.load(npz_file, allow_pickle=False) as z:
            x_p = z["X"]
            p_p = z["pred_proba"]
            ets = z["entry_ts"]
            sel = z["selected_feature_indices"]
            assert x_p.ndim == 2 and x_p.shape[0] == 500
            assert 8 <= x_p.shape[1] <= 12
            assert x_p.dtype == np.float32
            assert bool(np.all(np.isfinite(x_p)))
            assert p_p.shape == (500,) and p_p.dtype == np.float32
            assert bool(np.all(np.isfinite(p_p)))
            assert bool(np.all((p_p > 0.0) & (p_p < 1.0)))
            assert int(np.max(ets)) < mcv.DEV_CUTOFF_SEC
            assert sel.shape == (x_p.shape[1],)

    # Zero catboost_info directory anywhere in workspace root
    assert not (ROOT / "catboost_info").exists()
