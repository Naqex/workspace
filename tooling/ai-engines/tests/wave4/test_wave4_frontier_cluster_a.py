"""Unit, causality, anti-leakage, budget-cap, and local-cache tests for Wave 4 Frontier Cluster A."""

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
from quant_factory.wave4 import frontier_sleeves as fs

MODULE_PATH = Path(fs.__file__).resolve()


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
    start_iso: str = "2014-01-02",
    end_iso: str = "2018-12-31",
    late_symbols: dict[str, int] | None = None,
    seed: int = 101,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    dates = _make_business_days(start_iso, end_iso)
    n_t = len(dates)
    n_k = len(symbols)
    adjclose = np.empty((n_t, n_k), dtype=np.float64)

    # Common market factor + regime volatility burst in the middle
    regime_vol = np.full(n_t, 0.008, dtype=np.float64)
    mid_lo = n_t // 3
    mid_hi = mid_lo + max(40, n_t // 10)
    regime_vol[mid_lo:mid_hi] = 0.022
    mkt_shock = rng.normal(0.0003, 1.0, size=n_t) * regime_vol

    for j, sym in enumerate(symbols):
        if sym == "IDX_VIX":
            base_vix = 15.0 + 18.0 * (regime_vol > 0.015).astype(np.float64)
            noise = rng.normal(0.0, 1.2, size=n_t)
            adjclose[:, j] = np.clip(base_vix + noise, 10.0, 60.0)
        elif sym == "IDX_VIX3M":
            base_3m = 17.5 + 11.0 * (regime_vol > 0.015).astype(np.float64)
            noise = rng.normal(0.0, 0.8, size=n_t)
            adjclose[:, j] = np.clip(base_3m + noise, 11.0, 50.0)
        elif sym in ("BIL", "SHY"):
            r = rng.normal(0.00005, 0.0004, size=n_t)
            adjclose[:, j] = 90.0 * np.exp(np.cumsum(r))
        else:
            beta = 0.7 if sym in ("SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV", "EFA", "EEM") else -0.15
            idio = rng.normal(0.0002, 0.007, size=n_t)
            r = beta * mkt_shock + idio
            adjclose[:, j] = (50.0 + 5.0 * j) * np.exp(np.cumsum(r))

    if late_symbols:
        for sym, start_idx in late_symbols.items():
            if sym in symbols:
                adjclose[:start_idx, symbols.index(sym)] = np.nan

    return {
        "kind": "etf",
        "dates": dates,
        "symbols": list(symbols),
        "adjclose": adjclose,
        "max_loaded_date": dates[-1],
        "holdout_rows_analysed": 0,
        "data_sha256": f"synthetic-etf-{seed}",
    }


def _make_synthetic_crypto_panel(
    symbols: list[str] | None = None,
    *,
    start_iso: str = "2020-01-01",
    end_iso: str = "2022-12-31",
    late_symbols: dict[str, int] | None = None,
    seed: int = 202,
) -> dict[str, Any]:
    rng = np.random.default_rng(seed)
    syms = symbols or ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT", "ADAUSDT", "LINKUSDT", "LTCUSDT"]
    dates = _make_calendar_days(start_iso, end_iso)
    n_t = len(dates)
    n_k = len(syms)

    btc_r = rng.normal(0.001, 0.025, size=n_t)
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
        r = 0.7 * btc_r + rng.normal(0.0005, 0.02, size=n_t)
        px = (100.0 + 25.0 * j) * np.exp(np.cumsum(r))
        basis = rng.normal(0.0008, 0.0015, size=n_t)
        spot_c[:, j] = px
        perp_c[:, j] = px * np.exp(basis)
        spot_h[:, j] = spot_c[:, j] * (1.0 + np.abs(rng.normal(0.015, 0.01, size=n_t)))
        perp_h[:, j] = perp_c[:, j] * (1.0 + np.abs(rng.normal(0.016, 0.01, size=n_t)))
        f_base = 0.00035 + 0.0001 * (j % 3) + rng.normal(0.0, 0.00025, size=n_t)
        funding_daily[:, j] = f_base
        pos_8h_cnt[:, j] = np.where(f_base > 0.0001, 3, np.where(f_base > 0.0, 2, 0)).astype(np.int32)
        perp_qv[:, j] = (5e8 / (j + 1)) * rng.uniform(0.6, 1.5, size=n_t)
        h4_trend[:, j] = np.clip(np.tanh(20.0 * r), -1.0, 1.0)

    if late_symbols:
        for sym, start_idx in late_symbols.items():
            if sym in syms:
                j = syms.index(sym)
                spot_c[:start_idx, j] = np.nan
                perp_c[:start_idx, j] = np.nan
                spot_h[:start_idx, j] = np.nan
                perp_h[:start_idx, j] = np.nan
                funding_daily[:start_idx, j] = np.nan
                pos_8h_cnt[:start_idx, j] = 0
                tot_8h_cnt[:start_idx, j] = 0
                perp_qv[:start_idx, j] = np.nan
                h4_trend[:start_idx, j] = np.nan

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
        "data_sha256": f"synthetic-crypto-{seed}",
    }


def _slice_panel(panel: dict[str, Any], stop_exclusive: int) -> dict[str, Any]:
    out = dict(panel)
    out["dates"] = list(panel["dates"][:stop_exclusive])
    out["max_loaded_date"] = out["dates"][-1]
    for k, v in panel.items():
        if isinstance(v, np.ndarray) and v.ndim >= 1 and v.shape[0] == len(panel["dates"]):
            out[k] = v[:stop_exclusive].copy()
    return out


# ---------------------------------------------------------------------------
# 1. AST & Structural Safety Tests (Offline CI-Safe)
# ---------------------------------------------------------------------------


def test_ast_zero_bare_asserts_lazy_imports_and_order_send_zero() -> None:
    """Verify ZERO bare `assert`s, ZERO banned libs, lazy ML imports, and `OrderSend=0`."""
    source = MODULE_PATH.read_text(encoding="utf-8")
    tree = ast.parse(source, filename=str(MODULE_PATH))

    assert_nodes = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
    assert assert_nodes == [], f"Found bare assert statements stripped under python -O at lines: {assert_nodes}"

    banned_roots = {"hmmlearn", "MetaTrader5", "backtesting", "backtrader", "vectorbt"}
    heavy_top_level = {"scipy", "pandas", "pyarrow", "sklearn", "duckdb", "httpx"}

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

    # Every subprocess.run call must pass creationflags (no visible terminal popups on Windows)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == "run":
            kw_names = {kw.arg for kw in node.keywords if kw.arg is not None}
            assert "creationflags" in kw_names, f"subprocess.run at line {node.lineno} missing creationflags"

    assert fs.ORDER_SEND_CAPABLE is False
    assert fs.ORDER_SEND_COUNT == 0
    assert fs.HOLDOUT_CUTOFF_DATE == "2024-12-31"
    assert fs.WAVE4_FRONTIER_BUDGET_CAP == 36


# ---------------------------------------------------------------------------
# 2. Causality (Prefix Truncation + Non-Monotonic Future Perturbation) Tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("allocator", ["nco", "hrp"])
def test_frontier_01_causality_and_zero_prelisting(allocator: str) -> None:
    """Prove FRONTIER_01 SJM+NCO/HRP weights at `<= split` are bit-for-bit invariant to future prices."""
    syms = ["SPY", "QQQ", "IWM", "TLT", "IEF", "GLD", "DBC", "HYG", "BIL", "SHY"]
    panel = _make_synthetic_etf_panel(
        syms,
        start_iso="2014-01-02",
        end_iso="2018-12-31",
        late_symbols={"HYG": 320, "DBC": 200},
        seed=111,
    )
    params = {
        "allocator": allocator,
        "jump_lambda": 40.0,
        "rebal_freq": "monthly",
        "sjm_window": 180,
        "cov_window": 90,
        "bear_scale": 0.0,
        "target_vol": 0.10,
        "deadband": 0.05,
        "safe_harbor": "bil_cash",
        "max_single_weight": 0.30,
    }
    split_idx = 620

    w_full = fs.build_sleeve_weights(fs.FRONTIER_01_ID, panel, params)["target_w"]
    w_trunc = fs.build_sleeve_weights(fs.FRONTIER_01_ID, _slice_panel(panel, split_idx + 1), params)["target_w"]

    perturbed = copy.deepcopy(panel)
    rng = np.random.default_rng(999)
    tail_len = len(panel["dates"]) - (split_idx + 1)
    perturbed["adjclose"][split_idx + 1 :] = (
        perturbed["adjclose"][split_idx : split_idx + 1]
        * np.exp(rng.uniform(-0.8, 0.8, size=(tail_len, len(syms))))
    )
    w_pert = fs.build_sleeve_weights(fs.FRONTIER_01_ID, perturbed, params)["target_w"]

    np.testing.assert_allclose(w_full[: split_idx + 1], w_trunc, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(w_full[: split_idx + 1], w_pert[: split_idx + 1], rtol=0.0, atol=0.0)

    # Zero pre-listing allocation for late-listed ETFs
    assert float(np.max(np.abs(w_full[:320, syms.index("HYG")]))) == 0.0
    assert float(np.max(np.abs(w_full[:200, syms.index("DBC")]))) == 0.0

    # End-to-end evaluation on Cluster A succeeds with zero holdout/Cluster-B contamination
    res = fs.evaluate_sleeve(fs.FRONTIER_01_ID, params, split="cluster_a", panel=panel)
    assert res["holdout_rows_analysed"] == 0
    assert res["cluster_b_touched"] is False
    assert res["diagnostics"]["pre_listing_weight_violations"] == 0


@pytest.mark.parametrize("scaling", ["inv_var", "inv_vol", "cov_mfm"])
def test_frontier_02_causality_and_zero_signal_only_weights(scaling: str) -> None:
    """Prove FRONTIER_02 VRP+Vol-Managed causality, zero signal-only weights, and zero backfill."""
    syms = ["IDX_VIX", "IDX_VIX3M", "SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV", "BIL", "SHY", "GLD", "TIP"]
    panel = _make_synthetic_etf_panel(
        syms,
        start_iso="2014-01-02",
        end_iso="2018-12-31",
        late_symbols={"MTUM": 280, "QUAL": 350},
        seed=222,
    )
    params = {
        "scaling": scaling,
        "r_enter": 0.95,
        "r_exit": 1.02,
        "vix_smooth": 5,
        "vol_lookback": 21,
        "target_vol": 0.10,
        "deadband": 0.12,
        "rebal_days": 5,
        "safe_harbor": "bil_shy",
        "def_gld_cap": 0.15,
    }
    split_idx = 580

    w_full = fs.build_sleeve_weights(fs.FRONTIER_02_ID, panel, params)["target_w"]
    w_trunc = fs.build_sleeve_weights(fs.FRONTIER_02_ID, _slice_panel(panel, split_idx + 1), params)["target_w"]

    perturbed = copy.deepcopy(panel)
    rng = np.random.default_rng(777)
    tail_len = len(panel["dates"]) - (split_idx + 1)
    perturbed["adjclose"][split_idx + 1 :] *= rng.uniform(0.4, 2.2, size=(tail_len, len(syms)))
    w_pert = fs.build_sleeve_weights(fs.FRONTIER_02_ID, perturbed, params)["target_w"]

    np.testing.assert_allclose(w_full[: split_idx + 1], w_trunc, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(w_full[: split_idx + 1], w_pert[: split_idx + 1], rtol=0.0, atol=0.0)

    # Hard zero weight on IDX_VIX and IDX_VIX3M + zero pre-listing allocation
    assert float(np.max(np.abs(w_full[:, syms.index("IDX_VIX")]))) == 0.0
    assert float(np.max(np.abs(w_full[:, syms.index("IDX_VIX3M")]))) == 0.0
    assert float(np.max(np.abs(w_full[:280, syms.index("MTUM")]))) == 0.0
    assert float(np.max(np.abs(w_full[:350, syms.index("QUAL")]))) == 0.0

    res = fs.evaluate_sleeve(fs.FRONTIER_02_ID, params, split="cluster_a", panel=panel)
    assert res["holdout_rows_analysed"] == 0
    assert res["cluster_b_touched"] is False
    assert res["diagnostics"]["signal_only_max_abs_weight"] == 0.0
    assert res["diagnostics"]["pre_listing_weight_violations"] == 0


def test_frontier_03_crypto_causality_and_zero_prelisting() -> None:
    """Prove FRONTIER_03 Crypto Carry+Basis+SlowMom weights are bit-for-bit causal & zero-backfill."""
    panel = _make_synthetic_crypto_panel(
        start_iso="2020-01-01",
        end_iso="2022-12-31",
        late_symbols={"SOLUSDT": 220},
        seed=333,
    )
    params = {
        "k_max": 4,
        "keep_rank": 6,
        "enter_ann": 0.06,
        "exit_ann": 0.01,
        "rebal_days": 7,
        "w_fund": 0.55,
        "w_basis": 0.20,
        "w_mom": 0.25,
        "mom_lb": 21,
        "equity_buffer": 2.0,
        "max_single": 0.25,
        "deadband": 0.06,
        "mom_gate": True,
        "use_4h_confirm": True,
        "neg_med_brake": False,
        "min_persist14": 0.50,
        "bear_scale": 0.75,
    }
    split_idx = 500

    w_full = fs.build_sleeve_weights(fs.FRONTIER_03_ID, panel, params)["target_w"]
    w_trunc = fs.build_sleeve_weights(fs.FRONTIER_03_ID, _slice_panel(panel, split_idx + 1), params)["target_w"]

    perturbed = copy.deepcopy(panel)
    rng = np.random.default_rng(555)
    tail_len = len(panel["dates"]) - (split_idx + 1)
    n_k = len(panel["symbols"])
    perturbed["spot_close"][split_idx + 1 :] *= rng.uniform(0.3, 3.0, size=(tail_len, n_k))
    perturbed["perp_close"][split_idx + 1 :] *= rng.uniform(0.3, 3.0, size=(tail_len, n_k))
    perturbed["funding_daily"][split_idx + 1 :] = rng.normal(-0.002, 0.003, size=(tail_len, n_k))
    perturbed["h4_trend"][split_idx + 1 :] = rng.uniform(-1.0, 1.0, size=(tail_len, n_k))
    w_pert = fs.build_sleeve_weights(fs.FRONTIER_03_ID, perturbed, params)["target_w"]

    np.testing.assert_allclose(w_full[: split_idx + 1], w_trunc, rtol=0.0, atol=0.0)
    np.testing.assert_allclose(w_full[: split_idx + 1], w_pert[: split_idx + 1], rtol=0.0, atol=0.0)
    assert float(np.max(np.abs(w_full[:220, panel["symbols"].index("SOLUSDT")]))) == 0.0

    res = fs.evaluate_sleeve(fs.FRONTIER_03_ID, params, split="cluster_a", panel=panel)
    assert res["holdout_rows_analysed"] == 0
    assert res["cluster_b_touched"] is False
    assert res["diagnostics"]["pre_listing_weight_violations"] == 0
    assert res["diagnostics"]["cross_liq_events"] == 0


# ---------------------------------------------------------------------------
# 3. Hard `< 2025-01-01` Holdout Lock & Cluster A Boundary Guard (`-O` Safe)
# ---------------------------------------------------------------------------


def test_hard_holdout_2025_rejection_across_all_guards() -> None:
    """Prove `< 2025-01-01` Holdout rejection is fail-closed under both `python` and `python -O`."""
    etf_syms = ["SPY", "QQQ", "TLT", "IEF", "GLD", "BIL", "SHY"]
    etf_params = fs.PRE_REGISTERED_CLUSTER_A_GRIDS[fs.FRONTIER_01_ID][0][1]

    # 1. Poisoned cutoff_utc values
    for bad_cutoff in ("2025-01-01", "2025-06-15", "2026-11-20", "2024/12/31", "", None, True):
        with pytest.raises((HoldoutLockError, ValueError)):
            fs.enforce_split_bounds(
                ["2018-12-28", "2018-12-31"],
                sleeve_id=fs.FRONTIER_01_ID,
                split="cluster_a",
                cutoff_utc=bad_cutoff,  # type: ignore[arg-type]
            )

    # 2. Panel containing 2025-01-02 rejected on BOTH cluster_a AND cluster_b_blind
    panel_2025 = _make_synthetic_etf_panel(etf_syms, start_iso="2018-06-01", end_iso="2025-01-10", seed=41)
    for split in ("cluster_a", "cluster_b_blind"):
        with pytest.raises(HoldoutLockError):
            fs.evaluate_sleeve(fs.FRONTIER_01_ID, etf_params, split=split, panel=panel_2025)

    # 3. Incumbent return maps containing 2025+ date rejected fail-closed
    clean_panel = _make_synthetic_etf_panel(etf_syms, start_iso="2017-01-03", end_iso="2018-12-31", seed=42)
    with pytest.raises(HoldoutLockError):
        fs.evaluate_sleeve(
            fs.FRONTIER_01_ID,
            etf_params,
            split="cluster_a",
            panel=clean_panel,
            s1_dev_returns={"2018-12-31": 0.001, "2025-01-02": 0.002},
        )


def test_cluster_a_guard_rejects_cluster_b_dates_for_all_sleeves() -> None:
    """Prove `split='cluster_a'` rejects ANY Cluster B date fail-closed while `cluster_b_blind` accepts <= 2024."""
    # FRONTIER_01: Cluster A ends 2018-12-31 -> 2019-01-03 MUST raise CLUSTER_B_LEAKAGE_VIOLATION
    f01_syms = ["SPY", "QQQ", "TLT", "IEF", "GLD", "BIL", "SHY"]
    f01_leak = _make_synthetic_etf_panel(f01_syms, start_iso="2017-01-03", end_iso="2019-03-01", seed=51)
    f01_params = fs.PRE_REGISTERED_CLUSTER_A_GRIDS[fs.FRONTIER_01_ID][0][1]
    with pytest.raises(ValueError, match="CLUSTER_B_LEAKAGE_VIOLATION"):
        fs.evaluate_sleeve(fs.FRONTIER_01_ID, f01_params, split="cluster_a", panel=f01_leak)

    # Shared harness works cleanly when explicitly called on cluster_b_blind (<= 2024-12-31)
    f01_b = fs.evaluate_sleeve(fs.FRONTIER_01_ID, f01_params, split="cluster_b_blind", panel=f01_leak)
    assert f01_b["cluster_b_touched"] is True
    assert f01_b["holdout_rows_analysed"] == 0
    assert f01_b["eval_start_date"] >= "2019-01-03"
    assert f01_b["eval_end_date"] <= "2024-12-31"

    # FRONTIER_02: Cluster A ends 2018-12-31 -> 2019-01-03 MUST raise CLUSTER_B_LEAKAGE_VIOLATION
    f02_syms = ["IDX_VIX", "IDX_VIX3M", "SPY", "QQQ", "IWM", "VTV", "BIL", "SHY", "GLD", "TIP"]
    f02_leak = _make_synthetic_etf_panel(f02_syms, start_iso="2017-01-03", end_iso="2019-03-01", seed=52)
    f02_params = fs.PRE_REGISTERED_CLUSTER_A_GRIDS[fs.FRONTIER_02_ID][0][1]
    with pytest.raises(ValueError, match="CLUSTER_B_LEAKAGE_VIOLATION"):
        fs.evaluate_sleeve(fs.FRONTIER_02_ID, f02_params, split="cluster_a", panel=f02_leak)

    # FRONTIER_03: Cluster A ends 2022-12-31 -> 2023-01-01 MUST raise CLUSTER_B_LEAKAGE_VIOLATION
    f03_leak = _make_synthetic_crypto_panel(start_iso="2022-01-01", end_iso="2023-03-01", seed=53)
    f03_params = fs.PRE_REGISTERED_CLUSTER_A_GRIDS[fs.FRONTIER_03_ID][0][1]
    with pytest.raises(ValueError, match="CLUSTER_B_LEAKAGE_VIOLATION"):
        fs.evaluate_sleeve(fs.FRONTIER_03_ID, f03_params, split="cluster_a", panel=f03_leak)

    # Shared harness on cluster_b_blind evaluates strictly >= 2023-01-01
    f03_b = fs.evaluate_sleeve(fs.FRONTIER_03_ID, f03_params, split="cluster_b_blind", panel=f03_leak)
    assert f03_b["cluster_b_touched"] is True
    assert f03_b["holdout_rows_analysed"] == 0
    assert f03_b["eval_start_date"] >= "2023-01-01"


# ---------------------------------------------------------------------------
# 4. DuckDB Experiment Budget Cap `<= 36` & Per-Sleeve `<= 8` Enforcement
# ---------------------------------------------------------------------------


def test_duckdb_budget_cap_36_and_per_sleeve_8_fail_closed(tmp_path: Path) -> None:
    """Verify hard DuckDB budget cap `<= 36`, per-sleeve Cluster A cap `<= 8`, and hash-chain parity."""
    db_path = tmp_path / "wave4_frontier_m36.duckdb"
    reg_path = tmp_path / "wave4_frontier_m36_registry.sqlite3"

    with fs.FrontierExperimentLedger(duckdb_path=db_path, registry_path=reg_path) as ledger:
        # 1. Non-zero holdout_rows_analysed MUST fail closed
        with pytest.raises(HoldoutLockError):
            ledger.record_trial(
                trial_id="BAD_HO",
                sleeve_id=fs.FRONTIER_01_ID,
                split="cluster_a",
                params={"k": 1},
                cluster_a_sharpe=1.0,
                cluster_a_calmar=1.0,
                cluster_a_dd=5.0,
                corr_vs_7e=0.01,
                cost_2x_net=10.0,
                holdout_rows_analysed=1,
            )

        # 2. Fill 8 Cluster A trials per sleeve = 24 trials
        for s_idx, sid in enumerate(fs.FRONTIER_SLEEVE_IDS):
            for t_i in range(8):
                ledger.record_trial(
                    trial_id=f"S{s_idx}_A_{t_i}",
                    sleeve_id=sid,
                    split="cluster_a",
                    params={"trial": t_i, "s": s_idx},
                    cluster_a_sharpe=1.1 + 0.05 * t_i,
                    cluster_a_calmar=1.4,
                    cluster_a_dd=6.5,
                    corr_vs_7e=0.02,
                    cost_2x_net=12.5,
                    holdout_rows_analysed=0,
                    cluster_b_touched=False,
                    p_value=0.02,
                )
            # 9th Cluster A trial for same sleeve MUST raise SLEEVE_CLUSTER_A_BUDGET_EXCEEDED
            with pytest.raises(ValueError, match="SLEEVE_CLUSTER_A_BUDGET_EXCEEDED"):
                ledger.record_trial(
                    trial_id=f"S{s_idx}_A_OVERFLOW",
                    sleeve_id=sid,
                    split="cluster_a",
                    params={"trial": 99},
                    cluster_a_sharpe=2.0,
                    cluster_a_calmar=2.0,
                    cluster_a_dd=3.0,
                    corr_vs_7e=0.0,
                    cost_2x_net=20.0,
                    holdout_rows_analysed=0,
                    cluster_b_touched=False,
                )

        assert ledger.get_total_trial_count() == 24

        # 3. Fill remaining 12 slots up to exact 36 cap
        for extra_i in range(12):
            sid = fs.FRONTIER_SLEEVE_IDS[extra_i % 3]
            ledger.record_trial(
                trial_id=f"BLIND_FILL_{extra_i}",
                sleeve_id=sid,
                split="cluster_b_blind",
                params={"extra": extra_i},
                cluster_a_sharpe=0.9,
                cluster_a_calmar=1.1,
                cluster_a_dd=7.0,
                corr_vs_7e=0.03,
                cost_2x_net=8.0,
                holdout_rows_analysed=0,
                cluster_b_touched=True,
                p_value=0.04,
            )

        assert ledger.get_total_trial_count() == 36

        # 4. 37th trial MUST fail closed with WAVE4_FRONTIER_BUDGET_EXCEEDED
        with pytest.raises(ValueError, match="WAVE4_FRONTIER_BUDGET_EXCEEDED"):
            ledger.record_trial(
                trial_id="TRIAL_37_MUST_FAIL",
                sleeve_id=fs.FRONTIER_01_ID,
                split="cluster_b_blind",
                params={"extra": 37},
                cluster_a_sharpe=3.0,
                cluster_a_calmar=5.0,
                cluster_a_dd=1.0,
                corr_vs_7e=0.0,
                cost_2x_net=50.0,
                holdout_rows_analysed=0,
                cluster_b_touched=True,
            )

        integrity = ledger.verify_integrity()
        assert integrity["verified"] is True
        assert integrity["wave4_frontier_trials_count"] == 36
        assert integrity["budget_headroom"] == 0
        assert integrity["holdout_rows_analysed"] == 0


# ---------------------------------------------------------------------------
# 5. Adversarial Self-Audit: Poisoned Inputs & Deliberate Negative Mutations
# ---------------------------------------------------------------------------


def test_poisoned_inputs_and_negative_mutations_fail_closed(tmp_path: Path) -> None:
    """Adversarial vectors V1 & V7: poisoned values and deliberate mutations MUST flip PASS -> FAIL."""
    etf_syms = ["IDX_VIX", "IDX_VIX3M", "SPY", "QQQ", "BIL", "SHY"]
    etf_panel = _make_synthetic_etf_panel(etf_syms, start_iso="2016-01-04", end_iso="2018-12-31", seed=88)

    # Poisoned numeric params (NaN, Inf, bool disguised as numeric, out of bounds)
    for bad_lam in (float("nan"), float("inf"), float("-inf"), -1.0, True):
        with pytest.raises(ValueError):
            fs.build_sleeve_weights(fs.FRONTIER_01_ID, etf_panel, {"jump_lambda": bad_lam})

    for bad_r in (float("nan"), float("inf"), True, 1.50):
        with pytest.raises(ValueError):
            fs.build_sleeve_weights(fs.FRONTIER_02_ID, etf_panel, {"r_enter": bad_r})

    # Poisoned negative price in ETF panel
    bad_px_panel = copy.deepcopy(etf_panel)
    bad_px_panel["adjclose"][10, 2] = -5.0
    with pytest.raises(ValueError, match="non-positive or infinite"):
        fs.build_sleeve_weights(fs.FRONTIER_01_ID, bad_px_panel, {})

    # Deliberate Negative Mutation #1: Non-zero weight injected onto IDX_VIX
    bad_w = np.zeros_like(etf_panel["adjclose"])
    bad_w[50, 0] = 0.25  # IDX_VIX
    with pytest.raises(ValueError, match="SIGNAL_ONLY_WEIGHT_VIOLATION"):
        fs._simulate_etf_causal(etf_panel["adjclose"], bad_w, etf_syms)

    # Deliberate Negative Mutation #2: Non-zero weight on pre-listing NaN price row
    late_panel = copy.deepcopy(etf_panel)
    late_panel["adjclose"][:40, 3] = np.nan
    bad_late_w = np.zeros_like(late_panel["adjclose"])
    bad_late_w[20, 3] = 0.50
    with pytest.raises(ValueError, match="PRE_LISTING_BACKFILL_VIOLATION"):
        fs._simulate_etf_causal(late_panel["adjclose"], bad_late_w, etf_syms)

    # Deliberate Negative Mutation #3: +150% single-day perp mark squeeze triggers Cross-Margin liquidation audit
    c_panel = _make_synthetic_crypto_panel(start_iso="2021-01-01", end_iso="2021-06-30", seed=99)
    n_t, n_k = c_panel["funding_daily"].shape
    tw = np.zeros((n_t, n_k), dtype=np.float64)
    tw[:, 0] = 1.0  # 100% notional on BTCUSDT at 2.0x buffer => 0.50 spot, 0.50 margin
    c_panel["perp_high"][40, 0] = c_panel["perp_close"][39, 0] * 2.50
    c_panel["spot_high"][40, 0] = c_panel["perp_close"][39, 0] * 2.50
    sim_liq = fs._simulate_crypto_carry_causal(c_panel, tw, equity_buffer_mult=2.0)
    assert sim_liq["isolated_liq_events"] >= 1
    assert sim_liq["cross_liq_events"] >= 1

    # Deliberate Negative Mutation #4: Tampering frozen JSON SHA-256 or cluster_b_touched flips verify_frozen_artifact
    fake_frozen = {
        "schema_version": fs.FROZEN_SCHEMA_VERSION,
        "generated_utc": "2026-11-27T18:35:00Z",
        "cluster_a_trials_total": 3,
        "budget_cap": 36,
        "holdout_rows_analysed": 0,
        "cluster_b_touched": False,
        "order_send_capable": False,
        "order_send_count": 0,
        "frozen_candidates": {},
    }
    for sid in fs.FRONTIER_SLEEVE_IDS:
        spec = fs.get_sleeve_spec(sid)
        fp = {
            "sleeve_id": sid,
            "frozen_trial_id": f"{sid}_T1",
            "params": {"x": 1},
            "params_sha256": fs.sha256_json_canonical({"x": 1}),
            "dev_cluster_a": spec["gate"]["dev_cluster_a"],
            "dev_cluster_b_blind_pending": spec["gate"]["dev_cluster_b_blind"],
            "dev_cutoff_utc": "2024-12-31",
        }
        fake_frozen["frozen_candidates"][sid] = {
            **fp,
            "candidate_sha256": fs.sha256_json_canonical(fp),
            "cluster_a_metrics": {"max_loaded_date": spec["cluster_a_end"]},
            "holdout_rows_analysed": 0,
            "cluster_b_touched": False,
        }
    fake_frozen["manifest_sha256"] = fs.sha256_json_canonical(fake_frozen)
    p = tmp_path / "frozen.json"
    p.write_text(json.dumps(fake_frozen), encoding="utf-8")
    assert fs.verify_frozen_artifact(p)["verified"] is True

    # Tamper params without updating hash -> MUST fail
    tampered = copy.deepcopy(fake_frozen)
    tampered["frozen_candidates"][fs.FRONTIER_01_ID]["params"]["x"] = 999
    p_bad = tmp_path / "frozen_tampered.json"
    p_bad.write_text(json.dumps(tampered), encoding="utf-8")
    with pytest.raises(ValueError, match="SHA256_MISMATCH"):
        fs.verify_frozen_artifact(p_bad)

    # Tamper cluster_b_touched=True (even with recomputed manifest hash) -> MUST fail
    tampered_cb = copy.deepcopy(fake_frozen)
    tampered_cb["cluster_b_touched"] = True
    tampered_cb.pop("manifest_sha256")
    tampered_cb["manifest_sha256"] = fs.sha256_json_canonical(tampered_cb)
    p_cb = tmp_path / "frozen_cb.json"
    p_cb.write_text(json.dumps(tampered_cb), encoding="utf-8")
    with pytest.raises(ValueError, match="CLUSTER_B_LEAKAGE_VIOLATION"):
        fs.verify_frozen_artifact(p_cb)


# ---------------------------------------------------------------------------
# 6. Local Cache Artifact & Reproducibility Verification (`local_cache`)
# ---------------------------------------------------------------------------


@pytest.mark.local_cache
def test_local_cache_frozen_cluster_a_artifact_and_duckdb_integrity() -> None:
    """Validate real Cluster A frozen JSON, DuckDB `wave4_frontier_m36`, and zero-leakage invariants."""
    ver = fs.verify_frozen_artifact(fs.DEFAULT_FROZEN_JSON_PATH)
    assert ver["verified"] is True
    assert ver["holdout_rows_analysed"] == 0
    assert ver["cluster_b_touched"] is False
    assert ver["cluster_a_trials_total"] <= fs.MAX_CLUSTER_A_TOTAL_TRIALS
    assert ver["budget_cap"] == fs.WAVE4_FRONTIER_BUDGET_CAP

    doc = json.loads(fs.DEFAULT_FROZEN_JSON_PATH.read_text(encoding="utf-8"))
    assert doc["order_send_count"] == 0
    assert doc["order_send_capable"] is False
    assert doc["dev_cutoff_utc"] == "2024-12-31"
    assert doc["budget_headroom_remaining"] >= 12

    for sid in fs.FRONTIER_SLEEVE_IDS:
        cand = doc["frozen_candidates"][sid]
        assert cand["holdout_rows_analysed"] == 0
        assert cand["cluster_b_touched"] is False
        assert 1 <= cand["cluster_a_trials_run"] <= fs.MAX_CLUSTER_A_TRIALS_PER_SLEEVE
        diag = cand["cluster_a_metrics"]["diagnostics"]
        assert diag["pre_listing_weight_violations"] == 0
        assert diag["signal_only_max_abs_weight"] == 0.0
        if sid == fs.FRONTIER_03_ID:
            assert diag["cross_liq_events"] == 0

    with fs.FrontierExperimentLedger(
        duckdb_path=fs.DEFAULT_DUCKDB_PATH,
        registry_path=fs.DEFAULT_REGISTRY_PATH,
    ) as ledger:
        integrity = ledger.verify_integrity()
        assert integrity["verified"] is True
        assert integrity["holdout_rows_analysed"] == 0
        trials = ledger.list_trials()
        cluster_a_rows = [row for row in trials if row["split"] == "cluster_a"]
        cluster_b_blind_rows = [row for row in trials if row["split"] == "cluster_b_blind"]
        unknown_split_rows = [
            row for row in trials if row["split"] not in ("cluster_a", "cluster_b_blind")
        ]
        assert unknown_split_rows == []
        assert len(cluster_a_rows) == 24
        assert len(cluster_a_rows) == doc["cluster_a_trials_total"]
        assert len(cluster_b_blind_rows) in (0, 3)
        total_trials = len(trials)
        assert total_trials == len(cluster_a_rows) + len(cluster_b_blind_rows)
        assert total_trials == integrity["wave4_frontier_trials_count"]
        assert total_trials <= fs.WAVE4_FRONTIER_BUDGET_CAP
        for row in cluster_a_rows:
            assert row["holdout_rows_analysed"] == 0
            assert row["cluster_b_touched"] is False
        for row in cluster_b_blind_rows:
            assert row["holdout_rows_analysed"] == 0
            assert row["cluster_b_touched"] is True

    # Replay frozen FRONTIER_02 winner on Cluster A and confirm bit-for-bit reproducibility
    f02_frozen = doc["frozen_candidates"][fs.FRONTIER_02_ID]
    replay = fs.evaluate_sleeve(
        fs.FRONTIER_02_ID,
        f02_frozen["params"],
        split="cluster_a",
        cutoff_utc="2024-12-31",
    )
    assert replay["holdout_rows_analysed"] == 0
    assert replay["cluster_b_touched"] is False
    assert replay["sharpe"] == f02_frozen["cluster_a_metrics"]["sharpe"]
    assert replay["max_dd_pct"] == f02_frozen["cluster_a_metrics"]["max_dd_pct"]
    assert replay["cost_2x_net"] == f02_frozen["cluster_a_metrics"]["cost_2x_net_pct"]
