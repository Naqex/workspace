"""Offline contract & negative-mutation tests for Wave 5 DP (W5-G13) & Closed-Loop Factory (W5-G16/G17).

Hard invariants enforced:
  - ZERO bare Python `assert` statements (`python -O` safe — verified via AST check on all new files).
  - ZERO mutations to production `.runtime/offensive5/` artifacts (uses `tmp_path` or `write_output_path=None`).
  - Lazy-import portability: zero top-level `quant_trading` import in AST; stdlib fallback parity tested.
  - Holdout 2025+ strictly sealed (`holdout_rows_analysed == 0`, any `2025-*` date raises `ValueError`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `AUTO_DEPLOY_PERMITTED = False`.
  - Negative mutation tests:
      1. Martingale / Dubins-Savage bold-play violation (`mult(dd_deeper) > mult(dd_shallower)`) -> `ValueError`
      2. Shield A open-risk cap breach (`> 3.00%`) -> `ValueError`
      3. P1-6 poisoned inputs (`NaN`, `Inf`, `bool`, non-numeric, empty array, bad thresholds) -> `ValueError`
      4. Empty-bench fail-closed on RED decay (unverified/killed candidates NEVER promoted)
      5. Tampered ledger hash / modified ledger field -> `ValueError("LEDGER_TAMPER_DETECTED")`
      6. Illegal FSM jump (`DISCOVERED -> ACTIVE_1X`) -> `ValueError`
"""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path
from typing import Any

import numpy as np
import pytest

REPO_ROOT = Path(__file__).resolve().parents[4]
AI_ENGINES_DIR = REPO_ROOT / "tooling" / "ai-engines"
for _p in (REPO_ROOT, AI_ENGINES_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory.wave5 import alpha_factory_closed_loop as af  # noqa: E402
from quant_factory.wave5 import bellman_dp_challenge_control as bdp  # noqa: E402


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion helper immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


def _make_synthetic_causal_matrices(
    *,
    n_ca: int = 120,
    n_cb: int = 120,
    seed: int = 20261128,
) -> dict[str, Any]:
    """Deterministic Cluster A (<= 2020-12-31) + Cluster B (2021..2024) synthetic daily matrices."""
    rng = np.random.default_rng(seed)
    action_grid = np.asarray(bdp.DEFAULT_ACTION_GRID, dtype=np.float64)
    days_ca = [f"2020-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n_ca)]
    days_cb = [f"2023-{(i // 28) + 1:02d}-{(i % 28) + 1:02d}" for i in range(n_cb)]
    days = days_ca + days_cb
    n_tot = len(days)

    # Underlying 1.0x daily return with realistic fat-tailed downside shock
    base_net = rng.normal(loc=0.045, scale=0.28, size=n_tot)
    base_dd = np.maximum(0.0, -base_net) + np.abs(rng.normal(loc=0.14, scale=0.12, size=n_tot))
    base_up = np.maximum(0.0, base_net) + np.abs(rng.normal(loc=0.12, scale=0.10, size=n_tot))

    n_act = len(action_grid)
    nets = np.zeros((n_act, n_tot), dtype=np.float64)
    dds = np.zeros((n_act, n_tot), dtype=np.float64)
    ups = np.zeros((n_act, n_tot), dtype=np.float64)
    for idx, m in enumerate(action_grid):
        # Sublinear saturation above 3.0x simulating Shield A 3.00% total open cap
        eff_scale = min(float(m), 3.0 + 0.55 * max(0.0, float(m) - 3.0))
        nets[idx, :] = base_net * eff_scale
        dds[idx, :] = np.minimum(4.8, base_dd * eff_scale)
        ups[idx, :] = base_up * eff_scale

    return {
        "action_grid": action_grid,
        "days": days,
        "nets": nets,
        "dds": dds,
        "ups": ups,
    }


def _make_candidate_spec(
    *,
    engine_id: str,
    symbol: str,
    magic: int,
    series: np.ndarray,
    ca_sh: float = 1.20,
    cb_sh: float = 1.15,
    pbo: float = 0.20,
    dsr: float = 0.92,
    cost2x: float = 15.0,
    cb_end: str = "2024-12-31",
) -> af.AlphaCandidateSpec:
    return af.AlphaCandidateSpec(
        engine_id=engine_id,
        family_id="TEST_FAM",
        symbol=symbol,
        magic=magic,
        base_risk_pct=0.50,
        cluster_a_end_date="2020-12-31",
        cluster_b_end_date=cb_end,
        cluster_a_sharpe=ca_sh,
        cluster_a_pf=1.30,
        cluster_b_sharpe=cb_sh,
        cluster_b_pf=1.25,
        pbo_cscv=pbo,
        dsr_empirical=dsr,
        cost_stress_2x_net_pct=cost2x,
        daily_returns_dev=tuple(float(x) for x in series),
    )


# ---------------------------------------------------------------------------
# 1. Static Hygiene, Zero Bare Asserts, Lazy-Import & Safety Constants
# ---------------------------------------------------------------------------


def test_zero_bare_asserts_zero_crlf_zero_bom_and_lazy_quant_trading() -> None:
    files = [
        AI_ENGINES_DIR / "quant_factory" / "wave5" / "bellman_dp_challenge_control.py",
        AI_ENGINES_DIR / "quant_factory" / "wave5" / "alpha_factory_closed_loop.py",
        Path(__file__),
    ]
    for path in files:
        raw_bytes = path.read_bytes()
        _check(not raw_bytes.startswith(b"\xef\xbb\xbf"), f"BOM detected in {path.name}")
        _check(b"\r\n" not in raw_bytes, f"CRLF detected in {path.name}")
        tree = ast.parse(raw_bytes.decode("utf-8"), filename=str(path))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(len(bare_asserts) == 0, f"Bare assert in {path.name} at lines {bare_asserts}")

        # Verify ZERO top-level import of quant_trading or live_decay_monitor for minimal CI portability
        for node in tree.body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    _check(
                        "quant_trading" not in alias.name and "live_decay_monitor" not in alias.name,
                        f"Top-level non-lazy import {alias.name!r} in {path.name}",
                    )
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                _check(
                    "quant_trading" not in mod and "live_decay_monitor" not in mod,
                    f"Top-level non-lazy import-from {mod!r} in {path.name}",
                )

    _check(bdp.ORDER_SEND_CAPABLE is False, "DP ORDER_SEND_CAPABLE must be False")
    _check(bdp.ORDER_SEND_COUNT == 0, "DP ORDER_SEND_COUNT must be 0")
    _check(af.ORDER_SEND_CAPABLE is False, "Factory ORDER_SEND_CAPABLE must be False")
    _check(af.ORDER_SEND_COUNT == 0, "Factory ORDER_SEND_COUNT must be 0")
    _check(af.AUTO_DEPLOY_PERMITTED is False, "AUTO_DEPLOY_PERMITTED must be False")
    _check(bdp.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Holdout cutoff must be 2024-12-31")
    _check(af.HOLDOUT_CUTOFF_DATE == "2024-12-31", "Factory Holdout cutoff must be 2024-12-31")


# ---------------------------------------------------------------------------
# 2. Gate W5-G13: Anti-Martingale Bellman DP & Cluster B Ablation Tests
# ---------------------------------------------------------------------------


def test_bellman_dp_causal_split_distillation_and_ablation(tmp_path: Path) -> None:
    synth = _make_synthetic_causal_matrices(n_ca=110, n_cb=110, seed=77)
    out_file = tmp_path / "bellman_dp_schedule.json"
    res = bdp.run_bellman_dp_causal_ablation_from_matrices(
        action_grid=synth["action_grid"],
        days=synth["days"],
        nets_pct_175=synth["nets"],
        dds_pct_175=synth["dds"],
        ups_pct_175=synth["ups"],
        n_paths=200,
        horizon_days=42,
        seed=1234,
        write_output_path=out_file,
    )

    _check(out_file.is_file(), "Schedule JSON must be written to tmp_path")
    _check(b"\r\n" not in out_file.read_bytes(), "Schedule JSON must be LF-only")
    _check(res["hard_invariants"]["holdout_rows_analysed"] == 0, "holdout_rows_analysed must be 0")
    _check(res["hard_invariants"]["order_send_count"] == 0, "order_send_count must be 0")
    _check(res["causal_split"]["train_cluster_a"]["max_day"] <= "2020-12-31", "Train max day must be <= 2020-12-31")
    _check(res["causal_split"]["eval_cluster_b_oos"]["min_day"] >= "2021-01-01", "Eval min day must be >= 2021-01-01")

    for phase in ("P1", "P2"):
        sched = res["mql5_loadable_schedule"][phase]
        tiers = sched["tiers"]
        _check(1 <= len(tiers) <= 6, f"{phase} distilled tiers must be in [1..6], got {len(tiers)}")
        _check(
            sched["full_dp_anti_martingale_check"]["anti_martingale_verified"] is True,
            f"{phase} full DP anti-martingale failed",
        )
        _check(
            sched["distilled_schedule_check"]["anti_martingale_verified"] is True,
            f"{phase} 6-tier anti-martingale failed",
        )
        for t in tiers:
            _check(t["effective_total_open_risk_cap_pct"] <= 3.00 + 1e-12, f"{phase} tier exceeds Shield A 3.00%")

    # Every evaluated policy must satisfy Pass + Fail + Pending == 100.0%
    expected_policies = {
        "BELLMAN_DP_POLICY",
        "BELLMAN_DP_6TIER_SCHEDULE",
        "BARRIER_TAPER",
        "V103_SPRINT_STATIC_LOCK",
        "C10_NEWS_ON",
    }
    _check(set(res["cluster_b_ablation"]["combined_P1_P2"].keys()) == expected_policies, "Missing ablation policies")
    for pname in expected_policies:
        p1_m = res["cluster_b_ablation"]["P1"][pname]
        p2_m = res["cluster_b_ablation"]["P2"][pname]
        cb_m = res["cluster_b_ablation"]["combined_P1_P2"][pname]
        _check(abs(p1_m["outcome_sum_pct"] - 100.0) < 1e-6, f"P1 sum != 100 for {pname}")
        _check(abs(p2_m["outcome_sum_pct"] - 100.0) < 1e-6, f"P2 sum != 100 for {pname}")
        _check(abs(cb_m["outcome_sum_pct"] - 100.0) < 1e-6, f"Combined sum != 100 for {pname}")


def test_negative_mutation_martingale_bold_play_and_shield_a_rejected() -> None:
    p1_spec = bdp.build_p1_spec(horizon_days=30)
    eq_grid, dd_grid = bdp.build_state_grids(p1_spec)

    # Construct valid flat anti-martingale grid first
    valid_pol = np.full((len(eq_grid), len(dd_grid)), 2.5, dtype=np.float64)
    ok = bdp.validate_anti_martingale_policy(valid_pol, eq_grid, dd_grid, max_mult=4.5)
    _check(ok["anti_martingale_verified"] is True, "Flat policy must pass anti-martingale check")

    # Negative Mutation 1: Dubins-Savage bold play (higher risk at deeper dd_from_peak)
    martingale_dd = valid_pol.copy()
    martingale_dd[10, 4] = 4.0  # deeper dd > shallower dd (2.5)
    with pytest.raises(ValueError, match="ANTI_MARTINGALE_VIOLATION"):
        bdp.validate_anti_martingale_policy(martingale_dd, eq_grid, dd_grid, max_mult=4.5)

    # Negative Mutation 2: Higher risk at deeper static equity loss (eq=-6% > eq=-4%)
    martingale_eq = valid_pol.copy()
    zero_i = int(np.argmin(np.abs(eq_grid - 0.0)))
    martingale_eq[zero_i - 4, :] = 3.5
    with pytest.raises(ValueError, match="ANTI_MARTINGALE_STATIC_LOSS_VIOLATION"):
        bdp.validate_anti_martingale_policy(martingale_eq, eq_grid, dd_grid, max_mult=4.5)

    # Negative Mutation 3: Shield A cap > 3.00%
    with pytest.raises(ValueError, match="SHIELD_A_CAP_VIOLATION"):
        bdp.validate_shield_a_cap(3.05)

    # Negative Mutation 4: Holdout 2025 date injected into causal split
    with pytest.raises(ValueError, match="HOLDOUT_LOCK_VIOLATION"):
        bdp.validate_strict_pre_holdout_days(["2020-12-31", "2024-12-31", "2025-01-02"])


def test_barrier_taper_matches_v104_mq5_formula() -> None:
    # Check exact MQL5 `Naqex_Master_Prop7E_v104_ML.mq5:675-690` scaling
    # Case 1: Profit near target (eq=+8.0% of 10% target => frac_rem=0.20 < 0.35 => ddScale=0.20/0.35)
    m_near_target = bdp.compute_barrier_taper_mult(
        base_phase_mult=4.0,
        eq_pct=8.0,
        target_profit_pct=10.0,
        amber_dd_pct=3.5,
        amber_mult=0.65,
        red_dd_pct=6.0,
        red_mult=0.40,
        profit_lock_pct=7.0,
        profit_lock_mult=2.5,
        kill_static_dd_pct=8.0,
        sizing_mode=1,
    )
    expected = min(2.5, 4.0 * (0.20 / 0.35))
    _check(abs(m_near_target - expected) < 1e-9, f"BARRIER_TAPER near-target mismatch: {m_near_target} != {expected}")

    # Case 2: Static headroom < 3.5% (eq=-6.0%, kill_static=8.0% => headroom=2.0 => ddScale=2.0/3.5, red brake=1.6)
    m_deep_dd = bdp.compute_barrier_taper_mult(
        base_phase_mult=4.0,
        eq_pct=-6.0,
        target_profit_pct=10.0,
        amber_dd_pct=3.5,
        amber_mult=0.65,
        red_dd_pct=6.0,
        red_mult=0.40,
        profit_lock_pct=7.0,
        profit_lock_mult=2.5,
        kill_static_dd_pct=8.0,
        sizing_mode=1,
    )
    expected_dd = min(4.0 * 0.40, 4.0 * (2.0 / 3.5))
    _check(abs(m_deep_dd - expected_dd) < 1e-9, f"BARRIER_TAPER deep-dd mismatch: {m_deep_dd} != {expected_dd}")


# ---------------------------------------------------------------------------
# 3. Gates W5-G16 & W5-G17: Closed-Loop Alpha Factory, P1-6 Guardrail & Drills
# ---------------------------------------------------------------------------


def test_p1_6_fail_closed_guardrail_rejects_all_poisoned_inputs() -> None:
    rng = np.random.default_rng(42)
    good_dev = rng.normal(0.08, 0.50, size=60)
    good_live = rng.normal(0.10, 0.40, size=20)

    # Sanity check: valid inputs succeed on BOTH primary backend and stdlib fallback
    res_primary = af.evaluate_decay_fail_closed(good_dev, good_live, force_stdlib_fallback=False)
    res_fallback = af.evaluate_decay_fail_closed(good_dev, good_live, force_stdlib_fallback=True)
    _check(res_primary["verdict"] == res_fallback["verdict"], "Primary & stdlib fallback verdict mismatch")
    _check(
        abs(res_primary["cusum"]["current_negative_sigma"] - res_fallback["cusum"]["current_negative_sigma"]) < 1e-6,
        "Primary & stdlib fallback CUSUM mismatch",
    )
    _check(
        abs(res_primary["sprt"]["llr"] - res_fallback["sprt"]["llr"]) < 1e-6,
        "Primary & stdlib fallback SPRT mismatch",
    )

    poisoned_calls = [
        ("nan_in_dev", lambda: af.evaluate_decay_fail_closed(np.append(good_dev, np.nan), good_live)),
        ("inf_in_dev", lambda: af.evaluate_decay_fail_closed(np.append(good_dev, np.inf), good_live)),
        ("neg_inf_in_live", lambda: af.evaluate_decay_fail_closed(good_dev, np.append(good_live, -np.inf))),
        ("nan_in_live", lambda: af.evaluate_decay_fail_closed(good_dev, [0.1, float("nan"), 0.2])),
        ("bool_in_live", lambda: af.evaluate_decay_fail_closed(good_dev, [0.1, True, 0.2])),
        ("bool_ndarray_live", lambda: af.evaluate_decay_fail_closed(good_dev, np.array([True, False, True]))),
        ("bool_in_dev", lambda: af.evaluate_decay_fail_closed([True] * 35, good_live)),
        ("str_in_live", lambda: af.evaluate_decay_fail_closed(good_dev, [0.1, "0.2"])),
        ("empty_live", lambda: af.evaluate_decay_fail_closed(good_dev, [])),
        ("empty_dev", lambda: af.evaluate_decay_fail_closed([], good_live)),
        ("bool_cusum_k", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, cusum_k_sigma=False)),
        ("nan_cusum_h", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, cusum_h_sigma=float("nan"))),
        ("neg_cusum_h", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, cusum_h_sigma=0.0)),
        ("bool_sprt_alpha", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, sprt_alpha=True)),
        ("inf_sprt_beta", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, sprt_beta=float("inf"))),
        ("oob_sprt_alpha", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, sprt_alpha=0.6)),
        ("holdout_2025_date", lambda: af.evaluate_decay_fail_closed(good_dev, good_live, dev_max_date="2025-01-01")),
    ]
    for _label, fn in poisoned_calls:
        with pytest.raises(ValueError):
            fn()


def test_negative_mutation_empty_bench_fail_closed_and_tampered_ledger(tmp_path: Path) -> None:
    rng = np.random.default_rng(99)
    dev_map = {
        e["engine_id"]: rng.normal(loc=0.10, scale=0.45, size=120)
        for e in af.CANONICAL_PORT_7E_ENGINES
    }
    ctrl = af._seed_factory_with_port7e("test_empty_bench", dev_map)

    # Put UNVERIFIED (DISCOVERED) and KILLED candidates in registry — ZERO BENCH_READY!
    unv = _make_candidate_spec(
        engine_id="UNVERIFIED_X",
        symbol="AUDJPY",
        magic=20261161,
        series=rng.normal(0.15, 0.40, size=120),
    )
    ctrl.enqueue_discovery_candidate(unv)  # stays DISCOVERED

    bad = _make_candidate_spec(
        engine_id="KILLED_Y",
        symbol="NZDJPY",
        magic=20261162,
        series=rng.normal(-0.05, 0.45, size=120),
        cb_sh=0.10,
        pbo=0.80,
        dsr=0.15,
        cost2x=-5.0,
    )
    ctrl.enqueue_discovery_candidate(bad)
    gate_bad = ctrl.run_blind_validation_gate(bad.engine_id)
    _check(gate_bad["final_state"] == "KILLED", "Bad candidate must be KILLED")

    # Illegal FSM jump from DISCOVERED -> ACTIVE_1X must fail closed
    with pytest.raises(ValueError, match="ILLEGAL_LIFECYCLE_TRANSITION"):
        ctrl._transition_state(
            "UNVERIFIED_X",
            af.EngineLifecycleState.ACTIVE_1X,
            stage="TEST",
            reason="Illegal jump",
        )

    # Trigger RED decay on E1_USDJPY_TOKYO
    live = af._make_healthy_live_streams(dev_map, n_live=40, seed=55)
    live["E1_USDJPY_TOKYO"] = np.full(25, -0.55, dtype=np.float64)
    cycle = ctrl.run_decay_and_governance_cycle(live, force_stdlib_fallback=True)
    _check(len(cycle["proposals"]) == 1, "Expected exactly 1 HALT proposal")
    prop = cycle["proposals"][0]
    _check(prop["action_type"] == "HALT_ONLY_EMPTY_BENCH", f"Expected HALT_ONLY_EMPTY_BENCH, got {prop['action_type']}")
    _check(prop["replacement_engine_id"] is None, "Empty bench MUST NOT promote any candidate")
    _check(
        ctrl.registry["UNVERIFIED_X"].state == af.EngineLifecycleState.DISCOVERED,
        "Unverified candidate state mutated!",
    )
    _check(ctrl.registry["KILLED_Y"].state == af.EngineLifecycleState.KILLED, "Killed candidate state mutated!")

    # Persist ledger to tmp_path and verify tamper detection
    ledger_path = tmp_path / "alpha_factory_ledger.json"
    exported = ctrl.export_ledger(write_output_path=ledger_path)
    _check(ledger_path.is_file(), "Ledger file must be written to tmp_path")
    _check(af.verify_ledger_integrity(exported)["integrity_verified"] is True, "Fresh ledger must verify clean")

    # Negative Mutation A: modify entry details
    tampered_a = json.loads(ledger_path.read_text(encoding="utf-8"))
    tampered_a["entries"][0]["details"]["factory_id"] = "TAMPERED_ID"
    with pytest.raises(ValueError, match="LEDGER_TAMPER_DETECTED"):
        af.verify_ledger_integrity(tampered_a)

    # Negative Mutation B: corrupt ledger_root_sha256
    tampered_b = json.loads(ledger_path.read_text(encoding="utf-8"))
    tampered_b["ledger_root_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="LEDGER_TAMPER_DETECTED"):
        af.verify_ledger_integrity(tampered_b)


def test_all_5_e2e_drills_pass_in_tmp_path_without_mutating_prod(tmp_path: Path) -> None:
    ledger_p = tmp_path / "ledger.json"
    drills_p = tmp_path / "drills.json"
    report = af.run_all_e2e_drills(
        write_ledger_path=ledger_p,
        write_drills_path=drills_p,
        force_stdlib_fallback=True,
    )
    _check(report["all_5_drills_passed"] is True, f"Expected all 5 drills PASS, got {report['verdict']}")
    _check(report["drills_passed"] == 5, f"Expected 5/5 passed, got {report['drills_passed']}")
    _check(report["hard_invariants"]["holdout_rows_analysed"] == 0, "Holdout rows must be 0")
    _check(report["hard_invariants"]["order_send_count"] == 0, "OrderSend count must be 0")
    _check(report["hard_invariants"]["auto_deploy_permitted"] is False, "Auto-deploy must be False")
    _check(ledger_p.is_file() and drills_p.is_file(), "Drill outputs must be written to tmp_path")

    # Check DRILL 3 chose the orthogonal high-score BENCH_READY candidate & locked dry-run in .set diff
    d3 = report["drills"]["DRILL_3_RED_WITH_BENCH_SWAP"]
    _check(d3["selected_replacement"] == "B1_XAGUSD_ORTH_VOL", f"Wrong replacement: {d3['selected_replacement']}")
    diff_text = d3["proposal"]["draft_set_diff"]["unified_diff"]
    _check("InpDryRunLogOnly=true" in diff_text, "Missing dry-run lock in .set diff")
    _check("InpGuardDryRunLogOnly=true" in diff_text, "Missing guard dry-run lock")

    # Check DRILL 5 rejected 100% of poisoned vectors
    d5 = report["drills"]["DRILL_5_POISONED_INPUT_AND_TAMPERED_LEDGER"]
    _check(d5["cases_tested"] == d5["cases_rejected_fail_closed"] == 8, "All 8 poison vectors must be rejected")

    # Verify persisted ledger integrity from disk
    loaded_ledger = json.loads(ledger_p.read_text(encoding="utf-8"))
    _check(af.verify_ledger_integrity(loaded_ledger)["integrity_verified"] is True, "Persisted ledger invalid")
