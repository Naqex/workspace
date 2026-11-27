"""Unit, negative-mutation, anti-leakage, one-shot budget, and local-cache tests for Wave 2A Blind Cluster B."""

from __future__ import annotations

import ast
import copy
import json
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from quant_core.holdout_guard import HoldoutLockError
from quant_core.io_utils import sha256_json_canonical
from quant_factory.eval_pipeline import benjamini_hochberg
from quant_factory.wave4 import frontier_sleeves as fs
from quant_factory.wave4 import run_frontier_blind_cluster_b as blind

MODULE_PATH = Path(blind.__file__).resolve()


# ---------------------------------------------------------------------------
# Deterministic Synthetic Offline Fixtures (100% CI-Safe, Zero Local Cache)
# ---------------------------------------------------------------------------


def _make_business_days(start_iso: str, end_iso: str) -> list[str]:
    d = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    out: list[str] = []
    while d <= end:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _make_calendar_days(start_iso: str, end_iso: str) -> list[str]:
    d = date.fromisoformat(start_iso)
    end = date.fromisoformat(end_iso)
    out: list[str] = []
    while d <= end:
        out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def _make_synthetic_etf_panel(
    symbols: list[str],
    *,
    start_iso: str = "2016-01-04",
    end_iso: str = "2024-12-31",
    seed: int = 301,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    dates = _make_business_days(start_iso, end_iso)
    n_t, n_k = len(dates), len(symbols)
    adjclose = np.empty((n_t, n_k), dtype=np.float64)

    regime_vol = np.full(n_t, 0.008, dtype=np.float64)
    for i, dk in enumerate(dates):
        if dk.startswith("2022-"):
            regime_vol[i] = 0.019
    mkt = rng.normal(0.00035, 1.0, size=n_t) * regime_vol

    for j, sym in enumerate(symbols):
        if sym == "IDX_VIX":
            adjclose[:, j] = np.clip(15.0 + 16.0 * (regime_vol > 0.014) + rng.normal(0.0, 1.0, size=n_t), 10.0, 60.0)
        elif sym == "IDX_VIX3M":
            adjclose[:, j] = np.clip(18.0 + 10.0 * (regime_vol > 0.014) + rng.normal(0.0, 0.7, size=n_t), 11.0, 50.0)
        elif sym in ("BIL", "SHY"):
            adjclose[:, j] = 90.0 * np.exp(np.cumsum(rng.normal(0.00008, 0.0003, size=n_t)))
        else:
            beta = 0.65 if sym in ("SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV", "EFA", "EEM") else -0.10
            adjclose[:, j] = (50.0 + 4.0 * j) * np.exp(np.cumsum(beta * mkt + rng.normal(0.0002, 0.006, size=n_t)))

    return {
        "kind": "etf",
        "dates": dates,
        "symbols": list(symbols),
        "adjclose": adjclose,
        "max_loaded_date": dates[-1],
        "holdout_rows_analysed": 0,
        "data_sha256": f"synth-etf-{seed}",
    }


def _make_synthetic_crypto_panel(
    symbols: list[str] | None = None,
    *,
    start_iso: str = "2020-01-01",
    end_iso: str = "2024-12-31",
    seed: int = 404,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    syms = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT"]
    dates = _make_calendar_days(start_iso, end_iso)
    n_t, n_k = len(dates), len(syms)

    btc_r = rng.normal(0.0008, 0.022, size=n_t)
    spot_c = np.empty((n_t, n_k), dtype=np.float64)
    perp_c = np.empty((n_t, n_k), dtype=np.float64)
    spot_h = np.empty((n_t, n_k), dtype=np.float64)
    perp_h = np.empty((n_t, n_k), dtype=np.float64)
    funding_daily = np.empty((n_t, n_k), dtype=np.float64)
    pos_8h_cnt = np.full((n_t, n_k), 3, dtype=np.int32)
    tot_8h_cnt = np.full((n_t, n_k), 3, dtype=np.int32)
    perp_qv = np.empty((n_t, n_k), dtype=np.float64)
    h4_trend = np.empty((n_t, n_k), dtype=np.float64)

    for j in range(n_k):
        r = 0.7 * btc_r + rng.normal(0.0003, 0.018, size=n_t)
        px = (100.0 + 20.0 * j) * np.exp(np.cumsum(r))
        basis = rng.normal(0.0006, 0.0012, size=n_t)
        spot_c[:, j] = px
        perp_c[:, j] = px * np.exp(basis)
        spot_h[:, j] = spot_c[:, j] * (1.0 + np.abs(rng.normal(0.015, 0.008, size=n_t)))
        perp_h[:, j] = perp_c[:, j] * (1.0 + np.abs(rng.normal(0.016, 0.008, size=n_t)))
        f_base = 0.00040 + 0.00008 * (j % 3) + rng.normal(0.0, 0.0002, size=n_t)
        funding_daily[:, j] = f_base
        pos_8h_cnt[:, j] = np.where(f_base > 0.0001, 3, np.where(f_base > 0.0, 2, 0)).astype(np.int32)
        perp_qv[:, j] = (4e8 / (j + 1)) * rng.uniform(0.7, 1.4, size=n_t)
        h4_trend[:, j] = np.clip(np.tanh(15.0 * r), -1.0, 1.0)

    return {
        "kind": "crypto",
        "dates": dates,
        "symbols": list(syms),
        "funding_daily": funding_daily,
        "pos_8h_cnt": pos_8h_cnt,
        "tot_8h_cnt": tot_8h_cnt,
        "perp_close": perp_c,
        "perp_high": perp_h,
        "perp_quote_vol": perp_qv,
        "spot_close": spot_c,
        "spot_high": spot_h,
        "h4_trend": h4_trend,
        "max_loaded_date": dates[-1],
        "holdout_rows_analysed": 0,
        "data_sha256": f"synth-crypto-{seed}",
    }


def _slice_panel_max_date(panel: dict[str, Any], max_iso: str) -> dict[str, Any]:
    dates = list(panel["dates"])
    keep_idx = [i for i, d in enumerate(dates) if d <= max_iso]
    out = dict(panel)
    out["dates"] = [dates[i] for i in keep_idx]
    out["max_loaded_date"] = out["dates"][-1]
    for k, v in panel.items():
        if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(dates):
            out[k] = v[keep_idx].copy()
    return out


def _make_passing_metrics(sleeve_id: str) -> dict[str, Any]:
    base: dict[str, Any] = {
        "holdout_rows_analysed": 0,
        "eval_end_date": "2024-12-31",
        "max_loaded_date": "2024-12-31",
        "order_send_count": 0,
        "sharpe": 1.35,
        "calmar": 1.40,
        "pbo_cscv": 0.18,
        "dsr_empirical": 0.88,
        "bh_fdr_q": 0.015,
        "hansen_spa_p": 0.02,
        "cost_2x_net_pct": 25.0,
        "cost_breakeven_mult": 5.5,
        "annual_turnover": 4.2,
        "corr_vs_7e": 0.04,
        "tail_corr_vs_7e": 0.08,
        "corr_vs_s4_etf": 0.35,
        "pre_listing_weight_violations": 0,
        "signal_only_max_abs_weight": 0.0,
        "cpcv_purge_embargo_verified": True,
        "max_dd_2022_pct": 6.5,
    }
    if sleeve_id == fs.FRONTIER_02_ID:
        base["hansen_spa_vs_spy_vt_p"] = 0.03
    if sleeve_id == fs.FRONTIER_03_ID:
        base["cross_liq_events"] = 0
        base["isolated_liq_events"] = 0
        base["max_dd_2022_pct"] = None
    return base


def _make_fake_frozen_file(tmp_path: Path, cfg: dict[str, Any]) -> tuple[Path, dict[str, Any]]:
    frozen: dict[str, Any] = {
        "schema_version": fs.FROZEN_SCHEMA_VERSION,
        "generated_utc": "2026-11-27T18:46:49Z",
        "worker": "w4-m2b-frontier",
        "family_budget_id": fs.WAVE4_FRONTIER_FAMILY_ID,
        "budget_cap": fs.WAVE4_FRONTIER_BUDGET_CAP,
        "cluster_a_trials_total": 6,
        "budget_headroom_remaining": 30,
        "dev_cutoff_utc": "2024-12-31",
        "holdout_rows_analysed": 0,
        "cluster_b_touched": False,
        "order_send_capable": False,
        "order_send_count": 0,
        "spend_vnd": 0,
        "frozen_candidates": {},
        "all_cluster_a_trials": {},
    }
    for sid in fs.FRONTIER_SLEEVE_IDS:
        spec = fs.get_sleeve_spec(sid, config=cfg)
        tid, raw_params = fs.PRE_REGISTERED_CLUSTER_A_GRIDS[sid][0]
        params = dict(sorted(raw_params.items()))
        p_sha = sha256_json_canonical(params)
        fp = {
            "sleeve_id": sid,
            "frozen_trial_id": tid,
            "params": params,
            "params_sha256": p_sha,
            "dev_cluster_a": spec["gate"]["dev_cluster_a"],
            "dev_cluster_b_blind_pending": spec["gate"]["dev_cluster_b_blind"],
            "dev_cutoff_utc": "2024-12-31",
        }
        frozen["frozen_candidates"][sid] = {
            **fp,
            "candidate_sha256": sha256_json_canonical(fp),
            "cluster_a_trials_run": 2,
            "cluster_a_metrics": {"max_loaded_date": spec["cluster_a_end"], "sharpe": 1.1},
            "pre_registered_falsification_gate": copy.deepcopy(spec["gate"]),
            "holdout_rows_analysed": 0,
            "cluster_b_touched": False,
        }
        frozen["all_cluster_a_trials"][sid] = [
            {"trial_id": tid, "params_sha256": p_sha},
        ]
    frozen["manifest_sha256"] = sha256_json_canonical(frozen)
    p = tmp_path / "frontier_cluster_a_frozen.json"
    p.write_text(json.dumps(frozen, indent=2), encoding="utf-8")
    return p, frozen


# ---------------------------------------------------------------------------
# 1. AST & Structural Safety Tests (Offline CI-Safe)
# ---------------------------------------------------------------------------


def test_ast_zero_bare_asserts_lazy_imports_and_order_send_zero() -> None:
    """Verify ZERO bare `assert`s, ZERO banned libs, lazy heavy imports, and `OrderSend=0`."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert_nodes = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert assert_nodes == [], f"Found bare assert statements stripped under python -O at lines: {assert_nodes}"

    banned_roots = {"hmmlearn", "MetaTrader5", "backtesting", "backtrader", "vectorbt"}
    heavy_top_level = {"scipy", "pandas", "pyarrow", "sklearn", "duckdb", "httpx", "numba"}

    all_imports: set[str] = set()
    top_level_imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                all_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            all_imports.add(node.module.split(".")[0])

    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                top_level_imports.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.module:
            top_level_imports.add(node.module.split(".")[0])

    assert banned_roots.isdisjoint(all_imports), f"Banned import found: {banned_roots & all_imports}"
    assert heavy_top_level.isdisjoint(top_level_imports), (
        f"Heavy/optional library imported at top-level instead of lazily: {heavy_top_level & top_level_imports}"
    )

    assert blind.ORDER_SEND_CAPABLE is False
    assert blind.ORDER_SEND_COUNT == 0
    assert blind.SPEND_VND == 0
    assert blind.HOLDOUT_CUTOFF_DATE == "2024-12-31"


# ---------------------------------------------------------------------------
# 2. Tampered `candidate_sha256`, `params`, & Gate Weakening Fail-Closed
# ---------------------------------------------------------------------------


def test_tampered_candidate_sha256_and_gate_weakening_fail_closed(tmp_path: Path) -> None:
    """Prove tampered `candidate_sha256`, tampered params, or weakened gate raises fail-closed."""
    cfg = fs.load_frontier_config()
    valid_path, valid_doc = _make_fake_frozen_file(tmp_path, cfg)

    ver = blind.verify_frozen_bundle_for_blind_eval(valid_path)
    assert ver["verified"] is True
    assert set(ver["candidates"].keys()) == set(fs.FRONTIER_SLEEVE_IDS)

    # Mutation 1: Tamper candidate_sha256 (even if manifest_sha256 is recomputed!)
    bad_cand_sha = copy.deepcopy(valid_doc)
    bad_cand_sha["frozen_candidates"][fs.FRONTIER_01_ID]["candidate_sha256"] = "0" * 64
    bad_cand_sha.pop("manifest_sha256")
    bad_cand_sha["manifest_sha256"] = sha256_json_canonical(bad_cand_sha)
    p1 = tmp_path / "tampered_cand_sha.json"
    p1.write_text(json.dumps(bad_cand_sha), encoding="utf-8")
    with pytest.raises(ValueError, match="CANDIDATE_SHA256_MISMATCH"):
        blind.verify_frozen_bundle_for_blind_eval(p1)

    # Mutation 2: Re-tune a parameter and recompute candidate_sha256 + manifest_sha256
    #             without updating params_sha256 -> MUST fail PARAMS_SHA256_MISMATCH
    bad_params = copy.deepcopy(valid_doc)
    c1 = bad_params["frozen_candidates"][fs.FRONTIER_01_ID]
    c1["params"]["jump_lambda"] = 999.0
    fp_new = {
        "sleeve_id": c1["sleeve_id"],
        "frozen_trial_id": c1["frozen_trial_id"],
        "params": c1["params"],
        "params_sha256": c1["params_sha256"],
        "dev_cluster_a": c1["dev_cluster_a"],
        "dev_cluster_b_blind_pending": c1["dev_cluster_b_blind_pending"],
        "dev_cutoff_utc": c1["dev_cutoff_utc"],
    }
    c1["candidate_sha256"] = sha256_json_canonical(fp_new)
    bad_params.pop("manifest_sha256")
    bad_params["manifest_sha256"] = sha256_json_canonical(bad_params)
    p2 = tmp_path / "tampered_params.json"
    p2.write_text(json.dumps(bad_params), encoding="utf-8")
    with pytest.raises(ValueError, match="PARAMS_SHA256_MISMATCH"):
        blind.verify_frozen_bundle_for_blind_eval(p2)

    # Mutation 3: Attempt to weaken a pre-registered gate threshold in frozen JSON -> GATE_TAMPER_MISMATCH
    weak_gate = copy.deepcopy(valid_doc)
    weak_gate["frozen_candidates"][fs.FRONTIER_02_ID]["pre_registered_falsification_gate"]["min_cluster_b_sharpe"] = 0.2
    weak_gate.pop("manifest_sha256")
    weak_gate["manifest_sha256"] = sha256_json_canonical(weak_gate)
    p3 = tmp_path / "weakened_gate.json"
    p3.write_text(json.dumps(weak_gate), encoding="utf-8")
    with pytest.raises(ValueError, match="GATE_TAMPER_MISMATCH"):
        blind.verify_frozen_bundle_for_blind_eval(p3)


# ---------------------------------------------------------------------------
# 3. Hard `< 2025-01-01` Holdout Lock Fail-Closed (`-O` Safe)
# ---------------------------------------------------------------------------


def test_holdout_2025_date_fails_closed_across_all_blind_guards(tmp_path: Path) -> None:
    """Prove `2025-01-01` date fails closed across cutoff, gate evaluator, 2022 DD, and Pod blend under `python -O`."""
    cfg = fs.load_frontier_config()
    f01_gate = fs.get_sleeve_spec(fs.FRONTIER_01_ID, config=cfg)["gate"]
    valid_path, _ = _make_fake_frozen_file(tmp_path, cfg)

    # 1. Poisoned cutoff_utc = "2025-01-01" rejected BEFORE opening frozen file
    for bad_cut in ("2025-01-01", "2025-06-30", "2026-01-01", "", None, True):
        with pytest.raises((HoldoutLockError, ValueError)):
            blind.verify_frozen_bundle_for_blind_eval(valid_path, cutoff_utc=bad_cut)  # type: ignore[arg-type]

    # 2. Blind metrics with eval_end_date = "2025-01-01" or holdout_rows_analysed = 1 MUST raise HoldoutLockError
    m_2025 = _make_passing_metrics(fs.FRONTIER_01_ID)
    m_2025["eval_end_date"] = "2025-01-01"
    with pytest.raises(HoldoutLockError):
        blind.evaluate_sleeve_falsification_gates(fs.FRONTIER_01_ID, m_2025, f01_gate)

    m_rows = _make_passing_metrics(fs.FRONTIER_01_ID)
    m_rows["holdout_rows_analysed"] = 1
    with pytest.raises(HoldoutLockError):
        blind.evaluate_sleeve_falsification_gates(fs.FRONTIER_01_ID, m_rows, f01_gate)

    # 3. Calendar-year DD helper rejects 2025-01-01 key
    with pytest.raises(HoldoutLockError):
        blind.compute_calendar_year_drawdown({"2022-05-02": -0.01, "2025-01-01": 0.01}, year=2022)

    # 4. Starved-month helper & Pod blend reject 2025-01-01 date
    with pytest.raises(HoldoutLockError):
        blind.compute_starved_month_metrics(["2024-12-31", "2025-01-01"], [0.001, 0.002])

    with pytest.raises(HoldoutLockError):
        blind.evaluate_pod_blend_impact(
            {"2024-12-31": 0.001},
            {fs.FRONTIER_01_ID: {"2024-12-31": 0.001, "2025-01-01": 0.002}},
            [fs.FRONTIER_01_ID],
        )


# ---------------------------------------------------------------------------
# 4. Negative Mutations on Pre-Registered Kill Rules (`KILLED_ON_BLIND_CLUSTER_B`)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("sleeve_id", "field", "bad_value", "expected_failed_gate"),
    [
        (fs.FRONTIER_01_ID, "pbo_cscv", 0.51, "max_pbo_cscv"),
        (fs.FRONTIER_01_ID, "bh_fdr_q", 0.11, "max_bh_fdr_q"),
        (fs.FRONTIER_01_ID, "corr_vs_7e", 0.15, "max_abs_corr_vs_7e"),
        (fs.FRONTIER_01_ID, "corr_vs_7e", -0.16, "max_abs_corr_vs_7e"),
        (fs.FRONTIER_01_ID, "dsr_empirical", 0.49, "min_dsr_empirical"),
        (fs.FRONTIER_01_ID, "hansen_spa_p", 0.12, "max_hansen_spa_p"),
        (fs.FRONTIER_01_ID, "sharpe", 0.74, "min_cluster_b_sharpe"),
        (fs.FRONTIER_01_ID, "cost_2x_net_pct", -0.5, "cost_stress_2x_net_positive"),
        (fs.FRONTIER_01_ID, "cost_breakeven_mult", 2.4, "min_cost_breakeven_mult"),
        (fs.FRONTIER_01_ID, "annual_turnover", 10.1, "max_annual_turnover"),
        (fs.FRONTIER_01_ID, "tail_corr_vs_7e", 0.26, "max_worst5pct_tail_corr_vs_7e"),
        (fs.FRONTIER_01_ID, "corr_vs_s4_etf", 0.65, "max_corr_vs_existing_s4_etf"),
        (fs.FRONTIER_01_ID, "max_dd_2022_pct", 15.0, "inflation_2022_dd_check"),
        (fs.FRONTIER_02_ID, "sharpe", 0.84, "min_cluster_b_sharpe"),
        (fs.FRONTIER_02_ID, "max_dd_2022_pct", 10.5, "inflation_2022_dd_check"),
        (fs.FRONTIER_02_ID, "hansen_spa_vs_spy_vt_p", 0.15, "hansen_spa_vs_spy_voltarget"),
        (fs.FRONTIER_02_ID, "signal_only_max_abs_weight", 0.01, "zero_signal_only_weights"),
        (fs.FRONTIER_03_ID, "cross_liq_events", 1, "zero_cross_margin_liquidations"),
        (fs.FRONTIER_03_ID, "isolated_liq_events", 1, "zero_isolated_liquidations"),
        (fs.FRONTIER_03_ID, "annual_turnover", 6.1, "max_annual_turnover"),
        (fs.FRONTIER_03_ID, "cpcv_purge_embargo_verified", False, "cpcv_purge_embargo_required"),
    ],
)
def test_kill_rule_negative_mutations_trigger_killed_verdict(
    sleeve_id: str,
    field: str,
    bad_value: Any,
    expected_failed_gate: str,
) -> None:
    """Deliberate negative mutations MUST flip verdict from PASS_BLIND_CLUSTER_B -> KILLED_ON_BLIND_CLUSTER_B."""
    cfg = fs.load_frontier_config()
    gate = fs.get_sleeve_spec(sleeve_id, config=cfg)["gate"]

    # Baseline clean metrics pass unconditionally
    clean = _make_passing_metrics(sleeve_id)
    if sleeve_id == fs.FRONTIER_01_ID and field == "max_dd_2022_pct":
        # Ensure it does NOT dominate incumbent Sharpe/Calmar when testing the 2022 DD kill rule
        clean["sharpe"] = 0.85
        clean["calmar"] = 0.60
    res_pass = blind.evaluate_sleeve_falsification_gates(sleeve_id, clean, gate)
    assert res_pass["verdict"] == blind.VERDICT_PASS
    assert res_pass["failed_gates"] == []

    # Inject single negative mutation -> MUST flip to KILLED_ON_BLIND_CLUSTER_B with exact failing gate
    mutated = dict(clean)
    mutated[field] = bad_value
    res_fail = blind.evaluate_sleeve_falsification_gates(sleeve_id, mutated, gate)
    assert res_fail["verdict"] == blind.VERDICT_KILLED
    assert res_fail["all_gates_passed"] is False
    assert expected_failed_gate in res_fail["failed_gates"]


def test_poisoned_numeric_metrics_fail_closed() -> None:
    """NaN, Inf, and bool-disguised metrics MUST raise ValueError instead of silently passing."""
    cfg = fs.load_frontier_config()
    gate = fs.get_sleeve_spec(fs.FRONTIER_01_ID, config=cfg)["gate"]

    for field, bad_val in (
        ("sharpe", float("nan")),
        ("pbo_cscv", float("inf")),
        ("dsr_empirical", True),
        ("bh_fdr_q", -0.05),
        ("order_send_count", 1),
    ):
        m = _make_passing_metrics(fs.FRONTIER_01_ID)
        m[field] = bad_val
        with pytest.raises(ValueError):
            blind.evaluate_sleeve_falsification_gates(fs.FRONTIER_01_ID, m, gate)


# ---------------------------------------------------------------------------
# 5. End-to-End Synthetic Offline Pipeline (`24 -> 27 <= 36` + One-Shot Lock)
# ---------------------------------------------------------------------------


def test_synthetic_end_to_end_cluster_a_to_blind_b_and_oneshot_lock(tmp_path: Path) -> None:
    """Run synthetic Cluster A (6 trials) -> Blind Cluster B (+3 = 9 <= 36), verify SHA-256 & one-shot lock."""
    cfg = fs.load_frontier_config()
    f01_syms = ["SPY", "QQQ", "IWM", "TLT", "IEF", "GLD", "DBC", "HYG", "BIL", "SHY"]
    f02_syms = ["IDX_VIX", "IDX_VIX3M", "SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV", "BIL", "SHY", "GLD", "TIP"]

    etf01_full = _make_synthetic_etf_panel(f01_syms, start_iso="2016-01-04", end_iso="2024-12-31", seed=61)
    etf02_full = _make_synthetic_etf_panel(f02_syms, start_iso="2016-01-04", end_iso="2024-12-31", seed=62)
    crypto_full = _make_synthetic_crypto_panel(start_iso="2020-01-01", end_iso="2024-12-31", seed=63)

    etf01_a = _slice_panel_max_date(etf01_full, "2018-12-31")
    etf02_a = _slice_panel_max_date(etf02_full, "2018-12-31")
    crypto_a = _slice_panel_max_date(crypto_full, "2022-12-31")

    # Small synthetic 2-trial-per-sleeve grid (2 * 3 = 6 Cluster A trials -> +3 blind = 9 <= 36)
    mini_grids = {
        sid: fs.PRE_REGISTERED_CLUSTER_A_GRIDS[sid][:2]
        for sid in fs.FRONTIER_SLEEVE_IDS
    }

    # Build synthetic PORT_7E and S4 daily returns <= 2024-12-31
    rng = np.random.default_rng(707)
    biz_all = _make_business_days("2018-01-02", "2024-12-31")
    s1_synth = {d: float(rng.normal(0.0002, 0.006)) for d in biz_all}
    s4_synth = {d: float(rng.normal(0.00025, 0.005)) for d in biz_all}

    db_path = tmp_path / "wave4_frontier_m36.duckdb"
    reg_path = tmp_path / "wave4_frontier_m36_registry.sqlite3"
    frozen_path = tmp_path / "frontier_cluster_a_frozen.json"
    verdict_path = tmp_path / "frontier_cluster_b_blind_verdict.json"

    # Populate synthetic Cluster A ledger + frozen JSON without reading local disk caches
    frozen_doc: dict[str, Any] = {
        "schema_version": fs.FROZEN_SCHEMA_VERSION,
        "generated_utc": "2026-11-27T18:46:49Z",
        "worker": "w4-m2b-frontier",
        "family_budget_id": fs.WAVE4_FRONTIER_FAMILY_ID,
        "budget_cap": fs.WAVE4_FRONTIER_BUDGET_CAP,
        "cluster_a_trials_total": 6,
        "budget_headroom_remaining": 30,
        "dev_cutoff_utc": "2024-12-31",
        "holdout_rows_analysed": 0,
        "cluster_b_touched": False,
        "order_send_capable": False,
        "order_send_count": 0,
        "spend_vnd": 0,
        "frozen_candidates": {},
        "all_cluster_a_trials": {},
    }
    panels_a = {fs.FRONTIER_01_ID: etf01_a, fs.FRONTIER_02_ID: etf02_a, fs.FRONTIER_03_ID: crypto_a}
    panels_b = {fs.FRONTIER_01_ID: etf01_full, fs.FRONTIER_02_ID: etf02_full, fs.FRONTIER_03_ID: crypto_full}

    with fs.FrontierExperimentLedger(duckdb_path=db_path, registry_path=reg_path) as ledger:
        for sid in fs.FRONTIER_SLEEVE_IDS:
            spec = fs.get_sleeve_spec(sid, config=cfg)
            rows_a = []
            for tid, params in mini_grids[sid]:
                res_a = fs.evaluate_sleeve(
                    sid,
                    params,
                    split="cluster_a",
                    panel=panels_a[sid],
                    s1_dev_returns=s1_synth,
                    s4_dev_returns=s4_synth,
                    config=cfg,
                )
                ledger.record_trial(
                    trial_id=tid,
                    sleeve_id=sid,
                    split="cluster_a",
                    params=res_a["params"],
                    cluster_a_sharpe=res_a["sharpe"],
                    cluster_a_calmar=res_a["calmar"],
                    cluster_a_dd=res_a["max_dd_pct"],
                    cluster_a_cagr=res_a["cagr_pct"],
                    cluster_a_turnover=res_a["annual_turnover"],
                    corr_vs_7e=res_a["corr_vs_7e"],
                    tail_corr_vs_7e=res_a["tail_corr_vs_7e"],
                    cost_2x_net=res_a["cost_2x_net"],
                    cost_breakeven_mult=res_a["cost_breakeven_mult"],
                    holdout_rows_analysed=0,
                    cluster_b_touched=False,
                    p_value=res_a["p_value"],
                )
                rows_a.append({"trial_id": tid, "params": res_a["params"], "params_sha256": res_a["params_sha256"]})

            w_row = rows_a[0]
            fp = {
                "sleeve_id": sid,
                "frozen_trial_id": w_row["trial_id"],
                "params": w_row["params"],
                "params_sha256": w_row["params_sha256"],
                "dev_cluster_a": spec["gate"]["dev_cluster_a"],
                "dev_cluster_b_blind_pending": spec["gate"]["dev_cluster_b_blind"],
                "dev_cutoff_utc": "2024-12-31",
            }
            frozen_doc["frozen_candidates"][sid] = {
                **fp,
                "candidate_sha256": sha256_json_canonical(fp),
                "cluster_a_trials_run": len(rows_a),
                "cluster_a_metrics": {"max_loaded_date": spec["cluster_a_end"]},
                "pre_registered_falsification_gate": spec["gate"],
                "holdout_rows_analysed": 0,
                "cluster_b_touched": False,
            }
            frozen_doc["all_cluster_a_trials"][sid] = rows_a

    frozen_doc["manifest_sha256"] = sha256_json_canonical(frozen_doc)
    frozen_path.write_text(json.dumps(frozen_doc, indent=2), encoding="utf-8")

    # Execute ONE-SHOT blind Cluster B evaluation
    verdict = blind.run_blind_cluster_b_evaluation(
        frozen_json_path=frozen_path,
        duckdb_path=db_path,
        registry_path=reg_path,
        verdict_json_path=verdict_path,
        cutoff_utc="2024-12-31",
        s1_dev_returns=s1_synth,
        s4_dev_returns=s4_synth,
        panels_by_sleeve=panels_b,
        cluster_a_panels_by_sleeve=panels_a,
        grids=mini_grids,
        spa_n_boot=200,
        pbo_n_slices=8,
    )
    assert verdict["holdout_rows_analysed"] == 0
    assert verdict["order_send_count"] == 0
    assert verdict["pre_blind_trials_total"] == 6
    assert verdict["blind_trials_logged"] == 3
    assert verdict["total_trials_logged"] == 9
    assert verdict["bh_fdr_all_trials_m_total"] == 9

    # Verify verdict artifact + DuckDB parity
    ver_out = blind.verify_blind_verdict_artifact(verdict_path, duckdb_path=db_path, registry_path=reg_path)
    assert ver_out["verified"] is True
    assert ver_out["total_trials_logged"] == 9
    assert ver_out["holdout_rows_analysed"] == 0

    # Tampering a KILLED/PASS verdict in JSON MUST fail verify_blind_verdict_artifact!
    tampered_v = copy.deepcopy(verdict)
    first_sid = fs.FRONTIER_01_ID
    tampered_v["sleeves"][first_sid]["verdict"] = (
        blind.VERDICT_PASS
        if tampered_v["sleeves"][first_sid]["verdict"] == blind.VERDICT_KILLED
        else blind.VERDICT_KILLED
    )
    tampered_v.pop("report_sha256")
    tampered_v["report_sha256"] = sha256_json_canonical(tampered_v)
    bad_vp = tmp_path / "tampered_verdict.json"
    bad_vp.write_text(json.dumps(tampered_v), encoding="utf-8")
    with pytest.raises(ValueError, match="VERDICT_RECOMPUTATION_MISMATCH"):
        blind.verify_blind_verdict_artifact(bad_vp)

    # Attempting a SECOND blind run on the same DuckDB MUST fail closed (one-shot immutability!)
    with pytest.raises(ValueError, match="DUPLICATE_BLIND_EVAL_BLOCKED"):
        blind.run_blind_cluster_b_evaluation(
            frozen_json_path=frozen_path,
            duckdb_path=db_path,
            registry_path=reg_path,
            verdict_json_path=verdict_path,
            cutoff_utc="2024-12-31",
            s1_dev_returns=s1_synth,
            s4_dev_returns=s4_synth,
            panels_by_sleeve=panels_b,
            cluster_a_panels_by_sleeve=panels_a,
            grids=mini_grids,
            spa_n_boot=200,
            pbo_n_slices=8,
        )


def test_starved_month_and_pod_blend_math_offline() -> None:
    """Verify exact starved-month compounding and Pod blend starved-month reduction math."""
    # 4 calendar months: Jan (+2%), Feb (-1% starved), Mar (+0.2% < 0.5% low), Apr (-0.5% starved)
    dates = ["2024-01-10", "2024-02-10", "2024-03-10", "2024-04-10"]
    p7e = [0.02, -0.01, 0.002, -0.005]
    st = blind.compute_starved_month_metrics(dates, p7e)
    assert st["n_months"] == 4
    assert st["starved_months_le_0"] == 2
    assert st["starved_month_rate_le_0_pct"] == 50.0
    assert st["starved_months_lt_0p5pct"] == 3
    assert st["starved_month_rate_lt_0p5_pct"] == 75.0
    assert st["max_consec_starved_le_0"] == 1
    assert st["max_consec_starved_lt_0p5"] == 3

    # Adding an uncorrelated positive sleeve (+3% in every month) reduces starved months to 0%
    biz = _make_business_days("2023-01-02", "2024-12-31")
    p7e_map = {d: (-0.001 if int(d[5:7]) % 2 == 0 else 0.002) for d in biz}
    f03_map = {d: 0.0025 for d in biz}
    blend_res = blind.evaluate_pod_blend_impact(
        p7e_map,
        {fs.FRONTIER_03_ID: f03_map},
        [fs.FRONTIER_03_ID],
    )
    assert blend_res["status"] == "SURVIVING_FRONTIER_SLEEVES_BLENDED"
    assert blend_res["holdout_rows_analysed"] == 0
    eq_delta = blend_res["combined_blends"]["EQUAL_WEIGHT"]["delta_vs_port7e"]
    assert eq_delta["starved_le_0_reduction_pp"] > 0.0


# ---------------------------------------------------------------------------
# 6. Local Cache Artifact & DuckDB `27/36` Integrity Verification (`local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_local_cache_blind_verdict_and_duckdb_27_of_36_integrity() -> None:
    """Verify real `.runtime/offensive4/frontier/frontier_cluster_b_blind_verdict.json` & DuckDB `27/36`."""
    ver = blind.verify_blind_verdict_artifact(
        blind.DEFAULT_VERDICT_JSON_PATH,
        duckdb_path=fs.DEFAULT_DUCKDB_PATH,
        registry_path=fs.DEFAULT_REGISTRY_PATH,
    )
    assert ver["verified"] is True
    assert ver["holdout_rows_analysed"] == 0
    assert ver["total_trials_logged"] == 27
    assert ver["budget_cap"] == 36

    doc = json.loads(blind.DEFAULT_VERDICT_JSON_PATH.read_text(encoding="utf-8"))
    assert doc["order_send_count"] == 0
    assert doc["order_send_capable"] is False
    assert doc["dev_cutoff_utc"] == "2024-12-31"
    assert doc["pre_blind_trials_total"] == 24
    assert doc["blind_trials_logged"] == 3
    assert doc["total_trials_logged"] == 27
    assert doc["budget_headroom_remaining"] == 9
    assert doc["bh_fdr_all_trials_m_total"] == 27

    with fs.FrontierExperimentLedger(
        duckdb_path=fs.DEFAULT_DUCKDB_PATH,
        registry_path=fs.DEFAULT_REGISTRY_PATH,
    ) as ledger:
        integrity = ledger.verify_integrity()
        assert integrity["verified"] is True
        assert integrity["wave4_frontier_trials_count"] == 27
        assert integrity["holdout_rows_analysed"] == 0

        trials = ledger.list_trials()
        assert len(trials) == 27
        cl_a = [r for r in trials if r["split"] == "cluster_a"]
        cl_b = [r for r in trials if r["split"] == "cluster_b_blind"]
        assert len(cl_a) == 24
        assert len(cl_b) == 3
        for row in trials:
            assert row["holdout_rows_analysed"] == 0

        # Independently recompute BH-FDR q across all 27 raw DuckDB rows & verify exact match!
        recomputed_q = benjamini_hochberg([float(r["p_value"]) for r in trials])
        q_map = {str(r["trial_id"]): round(float(q), 6) for r, q in zip(trials, recomputed_q, strict=True)}
        for sid in fs.FRONTIER_SLEEVE_IDS:
            sv = doc["sleeves"][sid]
            assert sv["holdout_rows_analysed"] == 0
            assert sv["eval_end_date"] <= "2024-12-31"
            assert sv["max_loaded_date"] <= "2024-12-31"
            assert sv["verdict"] in (blind.VERDICT_PASS, blind.VERDICT_KILLED)
            assert sv["blind_metrics"]["bh_fdr_q"] == q_map[sv["blind_trial_id"]]
