"""Unit & adversarial regression tests for Wave 2A Lane L7:
  - HoldoutLockError(ValueError) & python -O immunity + SQLiteRunRegistry override audit
  - NumPy prefix-invariance (true truncation + non-monotonic 8-column Bid/Ask perturbation)
  - All 6 lookahead fixes (pass27, pass24, whitebox_discovery, holdout_eval, prop_engine, red_team_auditor)
  - Both prop_engine._simulate_lifecycle_numba fixes (raw breach before ea_cut; dead stage=0 + cf12@252)
  - Honest simultaneous gap-through shock matrix in red_team_auditor (zero <5% tautology)
  - Unified ExperimentLedger (SQLiteRunRegistry hash chain + local DuckDB <0.1s queries + tamper check)
  - Research Council ledger enforcement, strict Gate 4 date alignment, fail-closed G4/G6 skips & PBO <= 0.50 gate
"""

from __future__ import annotations

import json
import subprocess
import sys
import time
from dataclasses import replace
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import pass24_mtf_new_archetypes as p24  # noqa: E402
import pass27_portfolio_m1_phase_audit as p27  # noqa: E402
import whitebox_discovery as wbd  # noqa: E402
from native_ftmo_monfri_seal import START, STOP  # noqa: E402
from quant_core.causality import (  # noqa: E402
    CausalityViolationError,
    assert_prefix_invariance_numpy,
    assert_prefix_invariance_series,
)
from quant_core.holdout_guard import (  # noqa: E402
    HoldoutLockError,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
    record_holdout_override_event,
)
from quant_factory import holdout_eval_2025_2026 as heval  # noqa: E402
from quant_factory import prop_engine, red_team_auditor  # noqa: E402
from quant_factory.experiment_ledger import ExperimentLedger  # noqa: E402
from quant_factory.research_council import (  # noqa: E402
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)
from quant_factory.robustness_gate import RobustnessThresholds, evaluate_robustness_gate  # noqa: E402

from tooling.run_registry.store import JournalCorruptionError, SQLiteRunRegistry  # noqa: E402


def _make_synthetic_fx_bundle(
    n_bars: int = 90,
    *,
    base_px: float = 150.0,
    spread: float = 0.015,
    start_ts: int | None = None,
    seed: int = 101,
) -> tuple[np.ndarray, np.ndarray]:
    t0 = start_ts or int(datetime(2024, 6, 3, 8, 0, tzinfo=UTC).timestamp())
    times = np.array([t0 + i * 60 for i in range(n_bars)], dtype=np.int64)
    rng = np.random.default_rng(seed)
    steps = rng.normal(0.0, base_px * 0.0005, size=n_bars)
    bo = base_px + np.cumsum(steps)
    bc = bo + rng.normal(0.0, base_px * 0.0003, size=n_bars)
    bh = np.maximum(bo, bc) + base_px * 0.0004
    bl = np.minimum(bo, bc) - base_px * 0.0004
    quotes = np.column_stack([bo, bh, bl, bc, bo + spread, bh + spread, bl + spread, bc + spread]).astype(np.float64)
    return times, quotes


def test_holdout_lock_error_inherits_value_error_and_survives_python_o() -> None:
    assert issubclass(HoldoutLockError, ValueError)

    enforce_pre_holdout_dates(["2024-12-30", "2024-12-31"], context="ok_dev")
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_dates(["2024-12-31", "2025-01-01"], context="bad_iso")
    with pytest.raises(ValueError):
        enforce_pre_holdout_dates("2025.01.02", context="bad_dotted")

    enforce_pre_holdout_ts(np.array([START, STOP - 60], dtype=np.int64), START, STOP, context="ok_ts")
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_ts(STOP, START, STOP, context="at_stop")
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_ts(START - 60, START, STOP, context="before_start")
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_ts(True, START, STOP, context="bool_ts")

    # Verify enforcement survives `python -O` (asserts stripped!) across holdout_guard + core engines
    probe_code = """
import sys
import numpy as np
sys.path.insert(0, r'tooling/ai-engines')
from native_ftmo_monfri_seal import START, STOP
from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates, enforce_pre_holdout_ts
import pass24_mtf_new_archetypes as p24
import pass27_portfolio_m1_phase_audit as p27
import whitebox_discovery as wbd
from quant_factory import prop_engine

assert False  # MUST be stripped under python -O!

for fn in (
    lambda: enforce_pre_holdout_dates(['2025-01-01']),
    lambda: enforce_pre_holdout_ts(STOP, START, STOP),
    lambda: prop_engine.replay_portfolio_m1(['2025-01-01'], {'E1': {}}, {'E1': 0.005}),
):
    try:
        fn()
    except HoldoutLockError:
        pass
    else:
        raise SystemExit('FAILED_TO_RAISE_UNDER_PYTHON_O')

ts = np.array([STOP - 60, STOP, STOP + 60], dtype=np.int64)
q = np.tile(np.array([[150.0, 150.1, 149.9, 150.0, 150.01, 150.11, 149.91, 150.01]]), (3, 1))
spec = {'trade_contract_size': 100000.0, 'currency_profit': 'JPY'}
for call in (
    lambda: p27.replay_causal_m1_tape_trade('USDJPY', ts, q, 0, 2, 1, 150.01, 149.01, spec=spec),
    lambda: p24.replay_causal_intraday('USDJPY', ts, q, 0, 2, 1, 150.01, 149.01, spec=spec),
    lambda: wbd.replay_fx_intraday_fast(
        {'asset': 'USDJPY', 'times': ts, 'quotes': q, 'spec': spec}, 0, 1, 150.01, 149.01, STOP + 60
    ),
):
    try:
        call()
    except HoldoutLockError:
        pass
    else:
        raise SystemExit('REPLAYER_FAILED_UNDER_PYTHON_O')
print('PYTHON_O_GUARDS_OK')
"""
    proc = subprocess.run(
        [sys.executable, "-O", "-c", probe_code],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
        timeout=30,
    )
    assert proc.returncode == 0, f"stderr={proc.stderr} stdout={proc.stdout}"
    assert "PYTHON_O_GUARDS_OK" in proc.stdout


def test_record_holdout_override_event_logs_tamper_evident_run_event(tmp_path: Path) -> None:
    reg_path = tmp_path / "holdout_overrides.sqlite3"
    ev = record_holdout_override_event(
        caller="test_holdout_override",
        context="one_time_unlock_unit_test",
        reason="unit_test_verification",
        details={"window": "2025-01-01..2025-01-05"},
        registry_path=reg_path,
    )
    assert ev.event_type == "holdout.override"
    assert ev.sequence == 1
    assert ev.event_hash is not None and len(ev.event_hash) == 64

    reg = SQLiteRunRegistry(reg_path)
    reg.verify()
    events = reg.replay()
    assert len(events) == 1
    assert events[0].payload["allow_holdout"] is True
    assert events[0].payload["caller"] == "test_holdout_override"


def test_causality_helper_catches_scale_invariant_and_ask_column_leaks() -> None:
    times, quotes = _make_synthetic_fx_bundle(n_bars=80, base_px=150.0)

    # 1. Scale-invariant lookahead (immune to naive quotes * 100, caught by non-monotonic perturbation + truncation!)
    def leaky_scale_invariant(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        ratio = q[:, 0] / np.maximum(np.max(q[:, 0]), 1e-9)
        return ratio

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_numpy(leaky_scale_invariant, times, quotes, [20, 40, 60])

    # 2. Ask-high (column 5) lookahead caught by 8-column non-monotonic perturbation
    def leaky_ask_future(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        out = q[:, 0].copy()
        out[:-1] += 0.01 * q[1:, 5]
        return out

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_numpy(leaky_ask_future, times, quotes, [25, 50])

    # 3. Clean strictly causal rolling mean passes both truncation & non-monotonic perturbation
    def clean_causal(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        mids = 0.5 * (q[:, 0] + q[:, 4])
        out = np.full(len(mids), np.nan, dtype=np.float64)
        for i in range(5, len(mids)):
            out[i] = float(np.mean(mids[i - 5 : i]))
        return out

    res = assert_prefix_invariance_numpy(clean_causal, times, quotes, [15, 40, 65])
    assert res["passed"] is True

    # 4. 1D full-sample quantile leak caught by assert_prefix_invariance_series
    rng = np.random.default_rng(7)
    vals = rng.normal(0.0, 1.0, size=100)

    def leaky_full_quantile(v: np.ndarray) -> np.ndarray:
        q50 = float(np.percentile(v, 50.0))
        return (v > q50).astype(np.int8)

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_series(leaky_full_quantile, vals, [30, 60])


def test_fixed_entry_conv_rate_zero_lookahead_across_all_4_fx_replayers() -> None:
    times, quotes = _make_synthetic_fx_bundle(n_bars=40, base_px=150.0, spread=0.01)
    # Create a dramatic price move at exit bar (150 -> 175) while keeping SL unhit
    quotes[20:, 0:4] += 25.0
    quotes[20:, 4:8] += 25.0

    jpy_spec = {"trade_contract_size": 100000.0, "currency_profit": "JPY"}
    cad_spec = {"trade_contract_size": 100000.0, "currency_profit": "CAD"}
    d_entry = datetime.fromtimestamp(int(times[0]), UTC).date()
    d_prev = d_entry - timedelta(days=3)  # Monday entry -> Friday prior close!

    # Direct USDJPY: perturb exit price wildly and verify stop_risk_with_cost_usd / ftmo_risk stays IDENTICAL
    quotes_alt = quotes.copy()
    quotes_alt[20:, 0:4] += 15.0  # exit now 190 instead of 175
    quotes_alt[20:, 4:8] += 15.0

    ep = float(quotes[0, 4])
    sl = ep - 1.5

    item1 = p27.replay_causal_m1_tape_trade("USDJPY", times, quotes, 0, 39, 1, ep, sl, spec=jpy_spec)
    item2 = p27.replay_causal_m1_tape_trade("USDJPY", times, quotes_alt, 0, 39, 1, ep, sl, spec=jpy_spec)
    assert item1 is not None and item2 is not None
    r1, _, m1 = item1
    r2, _, m2 = item2
    assert abs(r1["entry_conv_rate"] - 1.0 / ep) < 1e-12
    assert abs(r1["stop_risk_with_cost_usd"] - r2["stop_risk_with_cost_usd"]) < 1e-12
    # Floating marks before bar 20 MUST also be invariant to future exit move!
    np.testing.assert_allclose(m1[:20], m2[:20], atol=1e-12, rtol=0.0)
    # Realized exit PnL uses exit_conv_rate (different exit price -> different realized USD)
    assert r1["exit_conv_rate"] != r2["exit_conv_rate"]
    assert abs(float(m1[-1, -1]) - r1["net_usd_per_lot"]) < 1e-9

    # Cross-JPY (EURJPY): entry sizing uses STRICT prior-day USDJPY (d_prev=145.0), NEVER future d_entry/d_ex close!
    map_a = {d_prev: 145.0, d_entry: 162.0}
    map_b = {d_prev: 145.0, d_entry: 120.0}
    e_item1 = p27.replay_causal_m1_tape_trade(
        "EURJPY", times, quotes, 0, 39, 1, ep, sl, spec=jpy_spec, usdjpy_close_map=map_a
    )
    e_item2 = p27.replay_causal_m1_tape_trade(
        "EURJPY", times, quotes, 0, 39, 1, ep, sl, spec=jpy_spec, usdjpy_close_map=map_b
    )
    assert e_item1 is not None and e_item2 is not None
    er1, _, em1 = e_item1
    er2, _, em2 = e_item2
    assert abs(er1["entry_conv_rate"] - 1.0 / 145.0) < 1e-12
    assert abs(er1["stop_risk_with_cost_usd"] - er2["stop_risk_with_cost_usd"]) < 1e-12
    np.testing.assert_allclose(em1[:-1], em2[:-1], atol=1e-12, rtol=0.0)
    assert abs(er1["exit_conv_rate"] - 1.0 / 162.0) < 1e-12
    assert abs(er2["exit_conv_rate"] - 1.0 / 120.0) < 1e-12

    # Verify pass24, whitebox_discovery, and holdout_eval_2025_2026 identically!
    p24_a = p24.replay_causal_intraday("EURJPY", times, quotes, 0, 39, 1, ep, sl, spec=jpy_spec, usdjpy_close_map=map_a)
    p24_b = p24.replay_causal_intraday("EURJPY", times, quotes, 0, 39, 1, ep, sl, spec=jpy_spec, usdjpy_close_map=map_b)
    assert p24_a is not None and p24_b is not None
    # Net USD differs with exit FX, while entry risk implied by net/R is identical
    rsk_a = p24_a["ftmo_net"] / p24_a["ftmo_R"]
    rsk_b = p24_b["ftmo_net"] / p24_b["ftmo_R"]
    assert abs(rsk_a - rsk_b) < 1e-9

    wb_a = wbd.replay_fx_intraday_fast(
        {"asset": "EURJPY", "times": times, "quotes": quotes, "spec": jpy_spec, "usdjpy_close_map": map_a},
        0, 1, ep, sl, int(times[-1]),
    )
    wb_b = wbd.replay_fx_intraday_fast(
        {"asset": "EURJPY", "times": times, "quotes": quotes, "spec": jpy_spec, "usdjpy_close_map": map_b},
        0, 1, ep, sl, int(times[-1]),
    )
    assert wb_a is not None and wb_b is not None
    assert abs(wb_a["ftmo_risk"] - wb_b["ftmo_risk"]) < 1e-12
    assert abs(wb_a["entry_conv_rate"] - 1.0 / 145.0) < 1e-12

    he_item_a = heval.replay_m1_tape_unbounded(
        "USDCAD", times, quotes / 110.0, 0, 39, 1, ep / 110.0, (ep - 1.5) / 110.0, spec=cad_spec
    )
    he_item_b = heval.replay_m1_tape_unbounded(
        "USDCAD", times, quotes_alt / 110.0, 0, 39, 1, ep / 110.0, (ep - 1.5) / 110.0, spec=cad_spec
    )
    assert he_item_a is not None and he_item_b is not None
    he_a, _, _ = he_item_a
    he_b, _, _ = he_item_b
    assert abs(he_a["stop_risk_with_cost_usd"] - he_b["stop_risk_with_cost_usd"]) < 1e-12
    assert abs(he_a["entry_conv_rate"] - 1.0 / (ep / 110.0)) < 1e-12

    # Full assert_prefix_invariance_numpy on USDJPY & EURJPY stop-risk + entry-mark stream!
    times_pi, quotes_pi = _make_synthetic_fx_bundle(n_bars=60, base_px=150.0, spread=0.015, seed=77)

    def _entry_risk_stream(ts_arr: np.ndarray, q_arr: np.ndarray) -> np.ndarray:
        n = len(ts_arr)
        out = np.full(n, np.nan, dtype=np.float64)
        for i in range(n - 1):
            e_p = float(q_arr[i, 4])
            item = p27.replay_causal_m1_tape_trade(
                "USDJPY", ts_arr, q_arr, i, n - 1, 1, e_p, e_p - 1.0, spec=jpy_spec
            )
            if item is not None:
                out[i] = float(item[0]["stop_risk_with_cost_usd"])
        return out

    # The last bar i == t has no flat_idx > i in truncated prefix; evaluate completed entry indices < t
    def _prefix_safe_risk_stream(ts_arr: np.ndarray, q_arr: np.ndarray) -> np.ndarray:
        n = len(ts_arr)
        out = np.full(n, np.nan, dtype=np.float64)
        for i in range(1, n):
            e_p = float(q_arr[i - 1, 4])
            item = p27.replay_causal_m1_tape_trade(
                "USDJPY", ts_arr, q_arr, i - 1, i, 1, e_p, e_p - 1.0, spec=jpy_spec
            )
            if item is not None:
                out[i] = float(item[0]["stop_risk_with_cost_usd"])
        return out

    pi_res = assert_prefix_invariance_numpy(_prefix_safe_risk_stream, times_pi, quotes_pi, [15, 30, 45])
    assert pi_res["passed"] is True
    # Also ensure entry_risk_stream at i=0 is identical under non-monotonic perturbation of bars > 10
    full_s = _entry_risk_stream(times_pi, quotes_pi)
    assert np.isfinite(full_s[0])


def test_prop_engine_causal_vol_targeting_and_both_simulator_bug_fixes() -> None:
    # 1. apply_vol_targeting_causal fails closed when < 30 bars without frozen_train_vol
    short_days = [f"2022-01-{i:02d}" for i in range(1, 21)]
    short_nets = np.ones(20, dtype=np.float64)
    with pytest.raises(ValueError, match="Insufficient history"):
        prop_engine.apply_vol_targeting_causal(short_days, short_nets, np.abs(short_nets))

    # 2. Works with explicit frozen_train_vol even on short OOS slices and passes prefix invariance
    rng = np.random.default_rng(42)
    n_obs = 120
    days_ab = [(date(2020, 11, 1) + timedelta(days=i)).isoformat() for i in range(n_obs)]
    nets_ab = rng.normal(15.0, 50.0, size=n_obs)

    res_vt_exp = assert_prefix_invariance_series(
        lambda v: prop_engine.apply_vol_targeting_causal(days_ab[: len(v)], v, np.abs(v), window=10)[0],
        nets_ab,
        [45, 70, 95],
    )
    assert res_vt_exp["passed"] is True

    res_vt_frozen = assert_prefix_invariance_series(
        lambda v: prop_engine.apply_vol_targeting_causal(
            days_ab[: len(v)], v, np.abs(v), window=10, frozen_train_vol=45.0
        )[0],
        nets_ab,
        [25, 60, 90],
    )
    assert res_vt_frozen["passed"] is True

    # 3. Simulator Bug #1: Raw daily/static breach checked BEFORE ea_daily_stop cut!
    # Counterexample A: Raw daily DD = 600 (> 500 daily_cap) with ea_daily_stop = 350 MUST breach!
    nets_br = np.array([-600.0, 200.0, 200.0, 200.0, 200.0], dtype=np.float64)
    dds_br = np.array([600.0, 10.0, 10.0, 10.0, 10.0], dtype=np.float64)
    flg_br = np.ones(5, dtype=np.int8)
    idx_br = np.array([[0, 1, 2, 3, 4]], dtype=np.int32)
    pdays, _, _, _, _, br1, _, _ = prop_engine._simulate_lifecycle_numba(
        idx_br,
        nets_br, dds_br, flg_br,
        nets_br, dds_br, flg_br,
        2, 10000.0, 168.0, 1.0,
        0.10, 0.05, 0.05, 0.10,
        False, 4, 0.0,
        1.0, 0.80, 10, 0,
        np.array([1.0], dtype=np.float64),
        1.0, 1.0, 1.0,
        0.99, 1.0, 0.99, 1.0,
        0.035,
    )
    assert int(br1[0]) == 1, "ea_daily_stop must NEVER mask raw daily breach!"
    assert int(pdays[0]) == -1

    # Counterexample B (Astra F09 static floor): Day 0 bal->9420, Day 1 raw dd=450 (<500 daily_cap, >380 ea_cut)
    # bal - dd = 8970 <= 9000 static floor -> MUST breach immediately!
    nets_st = np.array([-350.0, -230.0, -450.0, 1500.0], dtype=np.float64)
    dds_st = np.array([350.0, 230.0, 450.0, 10.0], dtype=np.float64)
    flg_st = np.ones(4, dtype=np.int8)
    idx_st = np.array([[0, 1, 2, 3]], dtype=np.int32)
    _, _, _, _, _, br1_st, _, _ = prop_engine._simulate_lifecycle_numba(
        idx_st,
        nets_st, dds_st, flg_st,
        nets_st, dds_st, flg_st,
        2, 10000.0, 168.0, 1.0,
        0.10, 0.05, 0.05, 0.10,
        False, 4, 0.0,
        1.0, 0.80, 10, 0,
        np.array([1.0], dtype=np.float64),
        1.0, 1.0, 1.0,
        0.99, 1.0, 0.99, 1.0,
        0.038,
    )
    assert int(br1_st[0]) == 1, "ea_daily_stop must NEVER mask raw static-floor breach!"

    # 4. Simulator Bug #2: Exhausting max_retries sets stage=0 (dead) AND still records cf12 at day 252!
    horizon = 300
    nets_dead = np.full(horizon, 400.0, dtype=np.float64)
    dds_dead = np.full(horizon, 10.0, dtype=np.float64)
    nets_dead[0] = -650.0
    dds_dead[0] = 650.0
    nets_dead[1] = -650.0
    dds_dead[1] = 650.0
    flg_dead = np.ones(horizon, dtype=np.int8)
    idx_dead = np.arange(horizon, dtype=np.int32).reshape(1, horizon)
    pdays_d, pay1_d, cf12_d, cf24_d, _, br1_d, _, tix_d = prop_engine._simulate_lifecycle_numba(
        idx_dead,
        nets_dead, dds_dead, flg_dead,
        nets_dead, dds_dead, flg_dead,
        2, 10000.0, 168.0, 1.0,
        0.10, 0.05, 0.05, 0.10,
        False, 4, 0.0,
        1.0, 0.80, 10, 1,  # 1 retry = 2 tickets total; both breach on days 0 & 1!
        np.array([1.0], dtype=np.float64),
        1.0, 1.0, 1.0,
        0.99, 1.0, 0.99, 1.0,
        0.035,
    )
    assert int(br1_d[0]) == 1
    assert int(tix_d[0]) == 2
    assert int(pdays_d[0]) == -1, "Dead account must NEVER pass after exhausting retries!"
    assert int(pay1_d[0]) == -1, "Dead account must NEVER earn payouts!"
    assert abs(float(cf12_d[0]) - (-336.0)) < 1e-9, "cf12 must still record -fees at day 252 when stage==0!"
    assert abs(float(cf24_d[0]) - (-336.0)) < 1e-9


def test_red_team_causal_vol_regimes_and_honest_shock_matrix() -> None:
    rng = np.random.default_rng(123)
    nets = rng.normal(5.0, 65.0, size=180)
    pi_vol = assert_prefix_invariance_series(
        lambda v: red_team_auditor.classify_causal_vol_regimes(v, vol_window=20, min_history=30, scale=10000.0)[1],
        nets,
        [65, 110, 150],
    )
    assert pi_vol["passed"] is True

    # Honest simultaneous gap-through shock matrix: NEVER clamp high SYMCAP risk under 5%!
    sym_map_7 = {"USDJPY": 0.95, "US100": 0.65, "GBPUSD": 0.35, "EURJPY": 0.35}
    r_list_7 = [0.40, 0.35, 0.35, 0.35, 0.35, 0.30, 0.20]
    safe_row = red_team_auditor.compute_simultaneous_shock_row(
        "Funded_Safe (1.00x)", r_list_7, sym_map_7, 1.00, 1.00, 2.50
    )
    assert safe_row["ftmo_5pct_safe_with_guard"] is True
    assert safe_row["simultaneous_gap_through_pct"] < 5.0

    sprint_row = red_team_auditor.compute_simultaneous_shock_row(
        "P1_Sprint (4.75x)", r_list_7, sym_map_7, 4.75, 2.25, 4.30
    )
    assert sprint_row["all_engines_symcap_pct"] > 5.0
    assert sprint_row["guarded_with_killswitch_pct"] > sprint_row["all_engines_symcap_pct"]
    assert sprint_row["ftmo_5pct_safe_with_guard"] is False


def test_experiment_ledger_roundtrip_sql_latency_and_tamper_detection(tmp_path: Path) -> None:
    db_path = tmp_path / "experiments.duckdb"
    reg_path = tmp_path / "run_registry.sqlite3"
    ledger = ExperimentLedger(duckdb_path=db_path, registry_path=reg_path)

    for i in range(25):
        fam = "FAM_BREAKOUT" if i < 20 else "FAM_MEANREV"
        rec = ledger.record_experiment(
            run_id=f"run-{i:03d}",
            git_sha="abc1234",
            data_sha="a" * 64,
            strategy_id=f"STRAT_{i:02d}",
            family_id=fam,
            sharpe=0.4 + 0.05 * i,
            dsr=min(0.99, 0.3 + 0.02 * i),
            pbo=0.25,
            spa_p=0.04,
            npv_usd=1200.0 + 50.0 * i,
            p_le_zero=0.18,
            p_value=round(0.01 + 0.03 * (i % 10), 4),
        )
        assert rec["registry_sequence"] == i + 1
        assert len(str(rec["registry_event_hash"])) == 64

    t0 = time.perf_counter()
    m_brk = ledger.get_cumulative_trial_count("FAM_BREAKOUT")
    pvals_brk = ledger.get_family_p_values("FAM_BREAKOUT")
    elapsed = time.perf_counter() - t0
    assert m_brk == 20
    assert len(pvals_brk) == 20
    assert elapsed < 0.1, f"DuckDB ledger query exceeded 0.1s SLA: {elapsed:.4f}s"
    assert ledger.get_cumulative_trial_count("FAM_MEANREV") == 5
    assert ledger.has_strategy("FAM_BREAKOUT", "STRAT_05") is True
    assert ledger.has_strategy("FAM_BREAKOUT", "NONEXISTENT") is False

    integrity = ledger.verify_integrity()
    assert integrity["verified"] is True
    assert integrity["experiments_count"] == 25

    # Reject NaN / invalid p_value fail-closed
    with pytest.raises(ValueError):
        ledger.record_experiment(
            run_id="bad-nan",
            git_sha="abc",
            data_sha="def",
            strategy_id="BAD",
            family_id="FAM_BREAKOUT",
            p_value=float("nan"),
        )

    # Tamper test: silently deleting a failed trial from DuckDB MUST fail verify_integrity()!
    con = duckdb.connect(str(db_path))
    try:
        con.execute("DELETE FROM experiments WHERE run_id = 'run-000'")
    finally:
        con.close()
    with pytest.raises(JournalCorruptionError, match="LEDGER_PARITY_MISMATCH"):
        ledger.verify_integrity()


def test_research_council_ledger_date_alignment_strict_gates_and_pbo(tmp_path: Path) -> None:
    rng = np.random.default_rng(2026)
    ledger = ExperimentLedger(duckdb_path=tmp_path / "exp.duckdb", registry_path=tmp_path / "reg.sqlite3")
    # Populate 19 prior high p-value trials in FAM_ALPHA
    for i in range(19):
        ledger.record_experiment(
            run_id=f"hist-{i:02d}",
            git_sha="deadbeef",
            data_sha="b" * 64,
            strategy_id=f"OLD_{i:02d}",
            family_id="FAM_ALPHA",
            p_value=0.65,
            sharpe=0.1,
        )

    card = propose_hypothesis(
        hypothesis_id="CAND_20",
        title="Ledger-Audited Candidate",
        asset_universe=["USDJPY"],
        timeframe="M15",
        counterparty_mechanism="FAM_ALPHA",
        economic_rationale="Session opening liquidity imbalance creates bounded stop-loss breakout edge.",
        causal_invariants=["prior_day_atr_only", "swap_zero_intraday"],
        n_trials_cumulative=1,  # Attempted self-report M=1!
        kill_criteria=KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.40, max_pbo=0.50),
    )

    dates_200 = [(date(2022, 1, 3) + timedelta(days=i)).isoformat() for i in range(200)]
    ret_a = rng.normal(0.0012, 0.004, size=200)
    ret_b = rng.normal(0.0012, 0.004, size=200)
    inc = rng.normal(0.0002, 0.004, size=200)

    good_days = [(date(2018, 1, 5) + timedelta(days=i * 20)).isoformat() for i in range(100)]
    closes = 100.0 + np.cumsum(rng.normal(0.0, 0.3, size=1000))
    good_rb = evaluate_robustness_gate(
        strategy_id="CAND_20",
        trade_r=np.array([1.2 if (i % 2 == 0) else -0.4 for i in range(100)], dtype=np.float64),
        trade_sides=np.array([1 if (i % 4 < 2) else -1 for i in range(100)], dtype=np.int64),
        trade_days=good_days,
        closes=closes,
        thresholds=RobustnessThresholds(mc_draws=200),
    )

    # 1. Ledger overrides self-reported M=1 -> M=20 -> BH q = 0.02 * 20 = 0.40 > 0.10 -> REJECT_KILLED!
    ev_sneaky = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.02,
        family_p_values=(0.02,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=good_rb,
    )
    v_ledger = critique_proposal(card, ev_sneaky, ledger=ledger, family_id="FAM_ALPHA")
    assert v_ledger["ledger_enforced"] is True
    assert v_ledger["effective_n_trials"] == 20
    assert v_ledger["gates"]["G1_bh_fdr"]["m_family"] == 20
    assert v_ledger["verdict"] == "REJECT_KILLED"
    assert "G1_bh_fdr" in v_ledger["failed_gates"]

    # 2. Strict Gate 4 date alignment: mismatched lengths without dates MUST fail closed (never slice a[:n], b[:n]!)
    ev_mismatch = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.001,
        family_p_values=(0.001,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=rng.normal(0.0, 0.004, size=150),  # length 150 != 200!
        robustness_report=good_rb,
    )
    v_mis = critique_proposal(card, ev_mismatch)
    assert v_mis["verdict"] == "REJECT_KILLED"
    assert "G4_orthogonality" in v_mis["failed_gates"]
    assert "UNALIGNED_LENGTH_MISMATCH" in v_mis["gates"]["G4_orthogonality"]["detail"]

    # 3. Strict Gate 4 & Gate 6 fail-closed when skipped (incumbent=None or robustness_report=None)
    ev_skip_g4 = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0005,
        family_p_values=(0.0005,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=None,
        robustness_report=good_rb,
    )
    v_skip_g4 = critique_proposal(card, ev_skip_g4, strict_gates=True)
    assert v_skip_g4["verdict"] == "REJECT_KILLED"
    assert "G4_orthogonality" in v_skip_g4["failed_gates"]

    ev_skip_g6 = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0005,
        family_p_values=(0.0005,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=None,
    )
    v_skip_g6 = critique_proposal(card, ev_skip_g6, strict_gates=True)
    assert v_skip_g6["verdict"] == "REJECT_KILLED"
    assert "G6_robustness_gate" in v_skip_g6["failed_gates"]

    # 4. Gate 7 PBO <= 0.50 via quant_core.metrics.compute_pbo_cscv
    # Construct matrix with 1 genuine strong signal + 5 noise columns -> low PBO (PASS)
    mat_good = rng.normal(0.0, 0.01, size=(160, 6))
    mat_good[:, 0] = rng.normal(0.004, 0.005, size=160)
    ev_pbo_pass = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0005,
        family_p_values=(0.0005,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=good_rb,
        pbo_returns_matrix=mat_good,
        pbo_n_slices=8,
    )
    v_pbo_ok = critique_proposal(card, ev_pbo_pass, strict_gates=True)
    assert v_pbo_ok["verdict"] == "APPROVE_FOR_INCUBATION"
    assert v_pbo_ok["gates"]["G7_pbo_cscv"]["passed"] is True
    assert v_pbo_ok["gates"]["G7_pbo_cscv"]["pbo"] <= 0.50

    # Overfit PBO > 0.50 -> REJECT_KILLED
    ev_pbo_fail = replace(ev_pbo_pass, pbo_returns_matrix=None, pbo_value=0.72)
    v_pbo_kill = critique_proposal(card, ev_pbo_fail, strict_gates=True)
    assert v_pbo_kill["verdict"] == "REJECT_KILLED"
    assert "G7_pbo_cscv" in v_pbo_kill["failed_gates"]


def test_rev7_adversarial_bypasses_all_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Regression suite covering every adversarial bypass reported in rev7-lookahead (#501)."""
    import hot_m1_cache as hcache
    import pass5_usdjpy_tokyo as clock
    import quant_factory.prop_engine as prop_engine
    import quant_factory.robustness_gate as rg
    from quant_factory.experiment_ledger import ExperimentLedger
    from quant_factory.research_council import EvidenceBundle, critique_proposal, propose_hypothesis

    from tooling.run_registry.store import JournalCorruptionError

    # 1A. enforce_pre_holdout_dates: UTC tz-aware holdout, non-ISO, malformed, numeric, NaN -> HoldoutLockError
    bad_date_inputs: list[Any] = [
        "2024-12-31T23:59:59-05:00",  # = 2025-01-01T04:59:59Z -> HOLDOUT!
        "2025-01-01T00:00:00Z",
        "01-01-2025",
        "01/01/2025",
        "!bad",
        "-1",
        "0000-00-00",
        "2024-13-45",
        [1735689600],
        [float("-inf")],
        float("nan"),
        1735689600,
        None,
    ]
    for bad in bad_date_inputs:
        with pytest.raises(HoldoutLockError):
            enforce_pre_holdout_dates(bad, context="rev7_bad_date")

    # Valid UTC-pre-holdout timestamps MUST still pass
    enforce_pre_holdout_dates(
        ["2024-12-31", "2024.12.31", "2024-12-31T23:59:59Z", "2024-12-31T22:00:00+02:00"],
        context="rev7_ok_dates",
    )

    # 1B. enforce_pre_holdout_ts: int64 overflow (1e20, uint64), scalar floats, None -> HoldoutLockError
    bad_ts_inputs: list[Any] = [
        np.array([1e20], dtype=np.float64),
        np.array([-1e20], dtype=np.float64),
        np.array([2**63 + 10], dtype=np.uint64),
        float("nan"),
        float("inf"),
        np.float64(np.nan),
        float(STOP),
        None,
    ]
    for bad_ts in bad_ts_inputs:
        with pytest.raises(HoldoutLockError):
            enforce_pre_holdout_ts(bad_ts, stop_ts=STOP, context="rev7_bad_ts")

    # 1C. hot_m1_cache & robustness_gate wrap corrupt/tampered manifest, SHA drift, lock JSON -> HoldoutLockError
    bad_cache = tmp_path / "corrupt-cache"
    bad_cache.mkdir()
    (bad_cache / "manifest.json").write_text("{corrupt json", encoding="utf-8")
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache)

    (bad_cache / "manifest.json").write_text(
        json.dumps({"holdout_rows": 0, "holdout_lock_sha256": "deadbeef" * 8, "assets": {}}),
        encoding="utf-8",
    )
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache)

    # Parquet SHA drift with valid lock SHA -> MUST raise HoldoutLockError
    (bad_cache / "usdjpy").mkdir()
    (bad_cache / "usdjpy" / "USDJPY-2018.parquet").write_bytes(b"corrupt-bytes")
    (bad_cache / "manifest.json").write_text(
        json.dumps(
            {
                "holdout_rows": 0,
                "holdout_lock_sha256": clock.LOCK_SHA,
                "assets": {
                    "USDJPY": {
                        "dir": "usdjpy",
                        "native_Ask": True,
                        "scale": 1000,
                        "years": {
                            str(y): {"parquet": "USDJPY-2018.parquet", "parquet_sha256": "0" * 64}
                            for y in clock.YEAR
                        },
                    }
                },
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(HoldoutLockError):
        hcache.load_asset("USDJPY", cache_dir=bad_cache, verify_sha=True)

    monkeypatch.setattr(rg, "assert_holdout_locked", lambda: (_ for _ in ()).throw(ValueError("tampered lock")))
    with pytest.raises(HoldoutLockError):
        rg._enforce_holdout_lock_sealed()

    # 2. In-place DuckDB column tamper MUST be detected by verify_integrity() AND block research_council!
    led = ExperimentLedger(
        duckdb_path=tmp_path / "tamper.duckdb",
        registry_path=tmp_path / "tamper.sqlite3",
    )
    led.record_experiment(
        run_id="r-001",
        git_sha="abc1234",
        data_sha="a" * 64,
        strategy_id="S_00",
        family_id="FAM_TAMPER",
        p_value=0.0001,
        sharpe=2.1,
    )
    led.record_experiment(
        run_id="r-002",
        git_sha="abc1234",
        data_sha="a" * 64,
        strategy_id="S_BAD",
        family_id="FAM_TAMPER",
        p_value=0.80,
        sharpe=0.2,
    )
    assert led.verify_integrity()["verified"] is True

    # 3A. P-value hijack attack: S_BAD (logged p=0.80) claims p_value_raw=0.0001 -> MUST NOT steal S_00's 0.0001!
    rng = np.random.default_rng(77)
    ret_a = rng.normal(0.0020, 0.004, size=200)
    ret_b = rng.normal(0.0020, 0.004, size=200)
    inc = rng.normal(0.0004, 0.004, size=200)
    d0 = date(2022, 1, 3)
    dates_200 = [(d0 + timedelta(days=i)).isoformat() for i in range(200)]
    good_rb = {"verdict": "PASS_ROBUST", "passed": True, "failed_pillars": [], "ranking_score_worst_year_p10_r": 2.0}

    card_bad = propose_hypothesis(
        hypothesis_id="S_BAD",
        title="Sneaky Hijack Candidate",
        asset_universe=["USDJPY"],
        timeframe="M15",
        counterparty_mechanism="FAM_TAMPER",
        economic_rationale="Testing authoritative ledger p-value lookup against cross-strategy hijack.",
        causal_invariants=["Strictly causal"],
        n_trials_cumulative=1,
    )
    ev_hijack = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0001,  # trying to steal S_00's p=0.0001!
        family_p_values=(0.0001,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=inc,
        cluster_b_dates=dates_200,
        incumbent_dates=dates_200,
        robustness_report=good_rb,
    )
    v_hijack = critique_proposal(card_bad, ev_hijack, ledger=led, family_id="FAM_TAMPER")
    assert v_hijack["verdict"] == "REJECT_KILLED"
    assert "G1_bh_fdr" in v_hijack["failed_gates"]
    assert v_hijack["gates"]["G1_bh_fdr"]["p_raw"] == pytest.approx(0.80, abs=1e-4)

    # 3B. Holdout date bypass with incumbent_daily_returns=None and strict_gates=False -> MUST raise HoldoutLockError!
    ev_holdout_bypass = EvidenceBundle(
        cluster_a_returns=ret_a,
        cluster_b_returns=ret_b,
        p_value_raw=0.0005,
        family_p_values=(0.0005,),
        candidate_index_in_family=0,
        cost_1x_net=1500.0,
        cost_2x_net=1000.0,
        n_trades_cluster_b=120,
        incumbent_daily_returns=None,
        cluster_b_dates=["2025-01-01"] * 200,
        robustness_report=good_rb,
    )
    with pytest.raises(HoldoutLockError):
        critique_proposal(card_bad, ev_holdout_bypass, strict_gates=False)

    # 3C. Mutate DuckDB row in-place -> BOTH verify_integrity() AND critique_proposal(..., ledger=led) fail closed!
    con = duckdb.connect(str(tmp_path / "tamper.duckdb"))
    try:
        con.execute("UPDATE experiments SET p_value = 0.0001, family_id = 'HIDDEN' WHERE run_id = 'r-002'")
    finally:
        con.close()

    with pytest.raises(JournalCorruptionError):
        led.verify_integrity()
    with pytest.raises(JournalCorruptionError):
        critique_proposal(card_bad, ev_hijack, ledger=led, family_id="FAM_TAMPER")

    # 4. Monotonic days_sorted guard in prop_engine.apply_vol_targeting_causal
    tail_days = [(date(2020, 1, 4) + timedelta(days=i)).isoformat() for i in range(35)]
    unsorted_days = ["2020-01-03", "2020-01-02", *tail_days]
    arr_37 = np.ones(37, dtype=np.float64) * 5.0
    with pytest.raises(ValueError, match="monotonically"):
        prop_engine.apply_vol_targeting_causal(unsorted_days, arr_37, np.abs(arr_37))
