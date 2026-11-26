"""Property-based invariant tests (`hypothesis`) across ALL `quant_core` SSOT modules.

Covers:
  1. `quant_core.schemas` — reject NaN/Inf, raw int `0`, future `2099` `verified_utc`, extra fields; valid models pass.
  2. `quant_core.metrics` — finite Sharpe/Calmar/PF/MaxDD/DSR/PBO/SPA invariants and zero `scipy` imports.
  3. `quant_core.prop_sim` vs `quant_core.decimal_oracle` — penny-exact parity across randomized paths,
     raw DD breach checked before EA cut, and zero Infinite Mulligan (`STAGE_DEAD` + `cf12` at day 252).
  4. `quant_core.tca` — blank/None/NaN/nonzero `swap_usd` fail-closed, BUY/SELL markout sign symmetry,
     and strict markout causality (future quote invariance + missing quote -> None).
  5. `quant_core.causality` — causal transforms pass; lookahead transforms raise `CausalityViolationError`.
  6. `quant_core.red_news` — valid windows sorted/monotonic/bounded; poisoned inputs rejected fail-closed.
  7. `quant_core.holdout_guard` — pre-2025 passes; `>= 2025-01-01` & tz-shifted UTC `>= 2025-01-01` raise
     `HoldoutLockError` unconditionally (even under `python -O`).

Profile:
  Reads `HYPOTHESIS_MAX_EXAMPLES` env var (default `50` for fast local pytest, `1000` for deep `<X13_WORKER>` fuzzing).
"""

from __future__ import annotations

import ast
import json
import math
import os
import sys
import tempfile
from datetime import UTC, date, datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.causality import (  # noqa: E402
    CausalityViolationError,
    assert_prefix_invariance_numpy,
    assert_prefix_invariance_series,
)
from quant_core.decimal_oracle import (  # noqa: E402
    DailyObservation,
    DecimalOracleParams,
    assert_penny_parity,
    replay_prop_lifecycle_decimal,
)
from quant_core.holdout_guard import (  # noqa: E402
    DEV_START_UTC_TS,
    HOLDOUT_START_UTC_TS,
    HoldoutLockError,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)
from quant_core.metrics import (  # noqa: E402
    compute_drawdowns,
    compute_pbo_cscv,
    compute_sharpe,
    deflated_sharpe_ratio_empirical,
    hansen_spa_test,
)
from quant_core.prop_sim import (  # noqa: E402
    STAGE_DEAD,
    PropSimParams,
    simulate_single_path,
)
from quant_core.red_news import (  # noqa: E402
    ALLOWED_CURRENCIES,
    MAX_BLACKOUT_SEC,
    load_calendar_events,
    summarize_calendar_events,
    validate_blackout_sec,
)
from quant_core.schemas import (  # noqa: E402
    EngineBaseRiskSpec,
    FxRatesConfig,
)
from quant_core.tca import (  # noqa: E402
    compute_markout_curve,
    parse_exec_audit_row,
    validate_tca_post_reconcile,
)

# Register configurable Hypothesis profile (`50` default local, `1000` on <X13_WORKER> deep fuzz)
_RAW_MAX_EXAMPLES = os.environ.get("HYPOTHESIS_MAX_EXAMPLES", "50").strip()
HYPOTHESIS_MAX_EXAMPLES = max(1, int(_RAW_MAX_EXAMPLES)) if _RAW_MAX_EXAMPLES.isdigit() else 50

settings.register_profile(
    "naqex_fuzz",
    max_examples=HYPOTHESIS_MAX_EXAMPLES,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.filter_too_much],
)
settings.load_profile("naqex_fuzz")


def _check(cond: bool, msg: str) -> None:
    """Assertion helper immune to `python -O` bytecode stripping."""
    if not cond:
        raise AssertionError(msg)


# ==============================================================================
# 1. quant_core.schemas
# ==============================================================================


@given(
    usd_vnd=st.floats(min_value=15000.0, max_value=35000.0, allow_nan=False, allow_infinity=False),
    eur_usd=st.floats(min_value=0.80, max_value=1.50, allow_nan=False, allow_infinity=False),
    days_ago=st.integers(min_value=1, max_value=365),
)
def test_schemas_fx_rates_valid_roundtrip_and_fingerprint(
    usd_vnd: float,
    eur_usd: float,
    days_ago: int,
) -> None:
    eur_vnd = usd_vnd * eur_usd
    verified = (datetime.now(UTC) - timedelta(days=days_ago)).replace(microsecond=0)
    cfg = FxRatesConfig(
        usd_vnd=usd_vnd,
        eur_usd=eur_usd,
        eur_vnd=eur_vnd,
        usd_eur=1.0 / eur_usd,
        verified_utc=verified,
        source="hypothesis-test",
    )
    fp1 = cfg.fingerprint()
    fp2 = cfg.fingerprint()
    _check(len(fp1) == 64 and fp1 == fp2, "Fingerprint must be deterministic 64-char SHA-256")
    _check(math.isfinite(cfg.usd_vnd) and cfg.usd_vnd > 0.0, "usd_vnd must stay finite positive")


@given(
    bad_num=st.sampled_from([float("nan"), float("inf"), float("-inf")]),
    bad_ts=st.sampled_from([0, 1700000000, True, "2099-01-01T00:00:00Z", "2099-12-31T23:59:59+00:00"]),
    extra_key=st.text(min_size=1, max_size=12, alphabet=st.characters(min_codepoint=97, max_codepoint=122)).filter(
        lambda k: k not in FxRatesConfig.model_fields
    ),
)
def test_schemas_reject_nan_inf_raw_int_zero_future_2099_and_extra_fields(
    bad_num: float,
    bad_ts: Any,
    extra_key: str,
) -> None:
    now_iso = (datetime.now(UTC) - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")
    valid_base: dict[str, Any] = {
        "usd_vnd": 25500.0,
        "eur_usd": 1.10,
        "eur_vnd": 28050.0,
        "verified_utc": now_iso,
        "source": "unit-test",
    }

    # 1. NaN / Inf rejected
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid_base, "usd_vnd": bad_num})

    # 2. Raw int 0 / Unix timestamp / bool / future 2099 verified_utc rejected
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid_base, "verified_utc": bad_ts})

    # 3. Unknown extra fields rejected (extra="forbid")
    with pytest.raises(ValidationError):
        FxRatesConfig.model_validate({**valid_base, extra_key: "injected"})


@given(
    bad_frac=st.one_of(
        st.floats(min_value=-10.0, max_value=-1e-6, allow_nan=False, allow_infinity=False),
        st.floats(min_value=1.0 + 1e-6, max_value=100.0, allow_nan=False, allow_infinity=False),
    ),
)
def test_schemas_unit_suffix_bounds_rejected_out_of_range(bad_frac: float) -> None:
    with pytest.raises(ValidationError):
        EngineBaseRiskSpec(
            engine_id="E1_TEST",
            symbol="USDJPY",
            magic=20261122,
            base_risk_pct=bad_frac * 100.0,
            base_risk_frac=bad_frac,
            signals_array_index=0,
        )


# ==============================================================================
# 2. quant_core.metrics (ZERO scipy)
# ==============================================================================


def test_metrics_module_has_zero_scipy_imports() -> None:
    metrics_path = AI_ENGINES / "quant_core" / "metrics.py"
    tree = ast.parse(metrics_path.read_text(encoding="utf-8"), filename=str(metrics_path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                _check(
                    not (alias.name == "scipy" or alias.name.startswith("scipy.")),
                    f"Forbidden scipy import in metrics.py: {alias.name}",
                )
        elif isinstance(node, ast.ImportFrom):
            mod = node.module or ""
            _check(
                not (mod == "scipy" or mod.startswith("scipy.")),
                f"Forbidden from-scipy import in metrics.py: {mod}",
            )


@given(
    returns=st.lists(
        st.floats(min_value=-0.05, max_value=0.05, allow_nan=False, allow_infinity=False),
        min_size=12,
        max_size=60,
    ),
    initial_cap=st.floats(min_value=1000.0, max_value=200000.0, allow_nan=False, allow_infinity=False),
    intraday_dip=st.floats(min_value=0.0, max_value=0.02, allow_nan=False, allow_infinity=False),
)
def test_metrics_sharpe_calmar_pf_maxdd_and_dsr_invariants(
    returns: list[float],
    initial_cap: float,
    intraday_dip: float,
) -> None:
    arr = np.asarray(returns, dtype=np.float64)
    sh = compute_sharpe(arr, annualization_days=252, calendar_aligned=True)
    _check(math.isfinite(sh.sharpe_annualized), "sharpe_annualized must be finite")
    _check(math.isfinite(sh.sharpe_per_period), "sharpe_per_period must be finite")
    _check(sh.std_return >= 0.0, "std_return must be >= 0")
    _check(0 <= sh.active_days <= sh.calendar_days == len(returns), "active_days bounds violated")
    if sh.std_return > 1e-15:
        if sh.mean_return > 0.0:
            _check(sh.sharpe_annualized > 0.0, "positive mean must yield positive Sharpe")
        elif sh.mean_return < 0.0:
            _check(sh.sharpe_annualized < 0.0, "negative mean must yield negative Sharpe")

    # Profit Factor & Calmar finite invariants on trade-return series
    gross_win = float(np.sum(arr[arr > 0.0]))
    gross_loss = float(-np.sum(arr[arr < 0.0]))
    if gross_loss > 1e-12:
        pf = gross_win / gross_loss
        _check(math.isfinite(pf) and pf >= 0.0, f"PF must be finite >= 0, got {pf}")

    # Equity curve & drawdown invariants (close-only vs intraday lows)
    eq = initial_cap * np.cumprod(1.0 + arr)
    lows = eq * (1.0 - intraday_dip)
    dd_close = compute_drawdowns(eq, initial_cap)
    dd_intra = compute_drawdowns(eq, initial_cap, intraday_lows=lows)
    for dd in (dd_close, dd_intra):
        _check(math.isfinite(dd.dd_of_peak_frac) and 0.0 <= dd.dd_of_peak_frac <= 1.0 + 1e-12, "dd_of_peak bounds")
        _check(math.isfinite(dd.dd_of_initial_frac) and dd.dd_of_initial_frac >= 0.0, "dd_of_initial >= 0")
        _check(dd.max_peak_to_trough_usd >= 0.0, "max_peak_to_trough_usd >= 0")
    _check(
        dd_intra.dd_of_peak_frac + 1e-12 >= dd_close.dd_of_peak_frac,
        "intraday lows must never reduce peak drawdown",
    )
    if dd_intra.dd_of_peak_frac > 1e-9:
        ann_ret = float(np.mean(arr)) * 252.0
        calmar = ann_ret / dd_intra.dd_of_peak_frac
        _check(math.isfinite(calmar), "Calmar must be finite when max DD > 0")

    # Empirical DSR bounds & monotonicity in n_trials when variance > 0
    if float(np.std(arr, ddof=1)) > 1e-9:
        dsr_1 = deflated_sharpe_ratio_empirical(arr, sr_trials_var=0.04, n_trials=1)
        dsr_20 = deflated_sharpe_ratio_empirical(arr, sr_trials_var=0.04, n_trials=20)
        dsr_200 = deflated_sharpe_ratio_empirical(arr, sr_trials_var=0.04, n_trials=200)
        for res in (dsr_1, dsr_20, dsr_200):
            _check(math.isfinite(res.dsr) and 0.0 <= res.dsr <= 1.0, f"DSR out of [0,1]: {res.dsr}")
            _check(math.isfinite(res.z_stat), "z_stat must be finite")
            _check(res.expected_max_sr >= 0.0, "expected_max_sr must be >= 0")
        _check(
            dsr_200.expected_max_sr + 1e-12 >= dsr_20.expected_max_sr >= dsr_1.expected_max_sr,
            "expected_max_sr must grow with n_trials",
        )
        _check(dsr_200.dsr <= dsr_20.dsr + 1e-12, "more trials cannot inflate DSR")


@given(
    seed=st.integers(min_value=1, max_value=100_000),
    n_obs=st.integers(min_value=16, max_value=48),
    n_models=st.integers(min_value=2, max_value=6),
    drift=st.floats(min_value=-0.01, max_value=0.01, allow_nan=False, allow_infinity=False),
)
def test_metrics_pbo_cscv_and_hansen_spa_invariants(
    seed: int,
    n_obs: int,
    n_models: int,
    drift: float,
) -> None:
    rng = np.random.default_rng(seed)
    mat = rng.normal(drift, 0.015, size=(n_obs, n_models))

    pbo = compute_pbo_cscv(mat, n_slices=4)
    _check(math.isfinite(pbo.pbo) and 0.0 <= pbo.pbo <= 1.0, f"PBO out of [0,1]: {pbo.pbo}")
    _check(
        math.isfinite(pbo.prob_oos_nonpositive_sr) and 0.0 <= pbo.prob_oos_nonpositive_sr <= 1.0,
        "prob_oos_nonpositive_sr out of [0,1]",
    )
    _check(pbo.is_overfit == (pbo.pbo > 0.50), "is_overfit flag mismatch")
    _check(pbo.n_combinations == 6, "C(4,2) must be 6")

    spa = hansen_spa_test(mat, n_boot=40, block_len=3, seed=seed)
    _check(math.isfinite(spa.t_stat) and spa.t_stat >= 0.0, "SPA t_stat must be finite >= 0")
    _check(
        0.0 <= spa.spa_p_lower <= spa.spa_p_consistent + 1e-12 <= spa.spa_p_upper + 2e-12 <= 1.0 + 2e-12,
        f"Hansen SPA ordering violated: {spa.spa_p_lower} <= {spa.spa_p_consistent} <= {spa.spa_p_upper}",
    )


# ==============================================================================
# 3. quant_core.prop_sim vs quant_core.decimal_oracle
# ==============================================================================


@given(
    daily_rows=st.lists(
        st.tuples(
            st.integers(min_value=-450, max_value=450),
            st.integers(min_value=0, max_value=480),
            st.sampled_from([0, 1]),
            st.sampled_from([0, 0, 0, 1]),
        ),
        min_size=12,
        max_size=45,
    ),
    steps=st.sampled_from([1, 2]),
    daily_pause_only=st.booleans(),
    max_retries=st.sampled_from([0, 1, 2]),
    require_flat=st.booleans(),
    ea_stop_bp=st.sampled_from([0, 350, 400]),
)
def test_prop_sim_vs_decimal_oracle_penny_parity_randomized(
    daily_rows: list[tuple[int, int, int, int]],
    steps: int,
    daily_pause_only: bool,
    max_retries: int,
    require_flat: bool,
    ea_stop_bp: int,
) -> None:
    # Use clean binary-exact multipliers so float64 & Decimal never diverge on an exact boundary epsilon
    nets = [float(r[0]) for r in daily_rows]
    dds = [float(r[1]) for r in daily_rows]
    flgs = [int(r[2]) for r in daily_rows]
    opens = [int(r[3]) for r in daily_rows]
    ea_stop_frac = ea_stop_bp / 10000.0

    params_sim = PropSimParams(
        steps=steps,
        capital_usd=10000.0,
        fee_usd=100.0,
        fee_refund_ratio=1.0,
        p1_target_frac=0.10,
        p2_target_frac=0.05,
        daily_loss_limit_frac=0.05,
        static_loss_limit_frac=0.10,
        daily_pause_only=daily_pause_only,
        min_days=2,
        payout_split_frac=0.80,
        payout_cycle_days=5,
        max_retries=max_retries,
        retry_discounts=(1.0,),
        p1_mult=2.0,
        p2_mult=1.5,
        funded_mult=1.0,
        amber_dd_frac=0.035,
        amber_mult=0.5,
        red_dd_frac=0.060,
        red_mult=0.25,
        ea_daily_stop_frac=ea_stop_frac,
        p1_profit_lock_trigger_frac=0.07,
        p1_profit_lock_mult=1.5,
        p2_profit_lock_trigger_frac=0.035,
        p2_profit_lock_mult=1.0,
        funded_profit_lock_trigger_frac=0.0,
        funded_profit_lock_mult=1.0,
        require_flat_for_pass=require_flat,
    )
    params_dec = DecimalOracleParams(
        steps=steps,
        capital_usd=Decimal("10000"),
        fee_usd=Decimal("100"),
        fee_refund_ratio=Decimal("1"),
        p1_target_frac=Decimal("0.10"),
        p2_target_frac=Decimal("0.05"),
        daily_loss_limit_frac=Decimal("0.05"),
        static_loss_limit_frac=Decimal("0.10"),
        daily_pause_only=daily_pause_only,
        min_days=2,
        payout_split_frac=Decimal("0.80"),
        payout_cycle_days=5,
        max_retries=max_retries,
        retry_discounts=(Decimal("1"),),
        p1_mult=Decimal("2.0"),
        p2_mult=Decimal("1.5"),
        funded_mult=Decimal("1.0"),
        amber_dd_frac=Decimal("0.035"),
        amber_mult=Decimal("0.5"),
        red_dd_frac=Decimal("0.060"),
        red_mult=Decimal("0.25"),
        ea_daily_stop_frac=Decimal(ea_stop_bp) / Decimal("10000"),
        p1_profit_lock_trigger_frac=Decimal("0.07"),
        p1_profit_lock_mult=Decimal("1.5"),
        p2_profit_lock_trigger_frac=Decimal("0.035"),
        p2_profit_lock_mult=Decimal("1.0"),
        funded_profit_lock_trigger_frac=Decimal("0"),
        funded_profit_lock_mult=Decimal("1.0"),
        require_flat_for_pass=require_flat,
    )

    obs = [DailyObservation(net=Decimal(r[0]), dd=Decimal(r[1]), flg=r[2], open_positions=r[3]) for r in daily_rows]
    oracle = replay_prop_lifecycle_decimal(obs, params_dec)
    sim_py = simulate_single_path(nets, dds, flgs, params_sim, open_positions=opens, backend="python")
    sim_nb = simulate_single_path(nets, dds, flgs, params_sim, open_positions=opens, backend="numba")

    assert_penny_parity(oracle, sim_py)
    assert_penny_parity(oracle, sim_nb)


@given(
    raw_dd_usd=st.integers(min_value=505, max_value=1500),
    ea_cut_frac=st.floats(min_value=0.01, max_value=0.045, allow_nan=False, allow_infinity=False),
)
def test_prop_sim_raw_dd_breaches_before_ea_cut_invariant(raw_dd_usd: int, ea_cut_frac: float) -> None:
    params = PropSimParams(
        steps=2,
        capital_usd=10000.0,
        fee_usd=100.0,
        daily_loss_limit_frac=0.05,
        static_loss_limit_frac=0.10,
        daily_pause_only=False,
        max_retries=0,
        p1_mult=1.0,
        p2_mult=1.0,
        funded_mult=1.0,
        ea_daily_stop_frac=ea_cut_frac,
        amber_dd_frac=0.08,
        red_dd_frac=0.09,
    )
    res = simulate_single_path([-float(raw_dd_usd), 500.0, 500.0], [float(raw_dd_usd), 0.0, 0.0], [1, 1, 1], params)
    _check(res["breached_p1"] is True, "Raw daily breach >= 5% MUST breach despite tighter ea_daily_stop_frac")
    _check(res["final_stage"] == STAGE_DEAD, "Zero retries after raw breach must enter STAGE_DEAD")
    _check(res["pass_day"] == -1, "Dead path cannot pass")


@given(
    blowup_day=st.integers(min_value=0, max_value=20),
    post_profit=st.integers(min_value=100, max_value=600),
    max_retries=st.integers(min_value=0, max_value=2),
)
def test_prop_sim_zero_infinite_mulligan_stays_dead_through_day_252(
    blowup_day: int,
    post_profit: int,
    max_retries: int,
) -> None:
    horizon = 260
    nets = [float(post_profit)] * horizon
    dds = [10.0] * horizon
    flgs = [1] * horizon
    # Force (max_retries + 1) consecutive blowups starting at blowup_day
    for k in range(max_retries + 1):
        idx = blowup_day + k
        nets[idx] = -600.0
        dds[idx] = 600.0

    fee_usd = 98.5
    params = PropSimParams(
        steps=2,
        capital_usd=10000.0,
        fee_usd=fee_usd,
        daily_loss_limit_frac=0.05,
        static_loss_limit_frac=0.10,
        min_days=30,  # prevent accidental pass before blowup_day
        max_retries=max_retries,
        retry_discounts=(1.0,),
        p1_mult=1.0,
        p2_mult=1.0,
        funded_mult=1.0,
        ea_daily_stop_frac=0.035,
    )
    res = simulate_single_path(nets, dds, flgs, params, backend="numba")
    expected_fees = fee_usd * (max_retries + 1)
    _check(res["final_stage"] == STAGE_DEAD, "Must remain STAGE_DEAD through day 260")
    _check(res["pass_day"] == -1 and res["first_payout_day"] == -1, "Dead account must never pass or pay out")
    _check(res["total_payouts_usd"] == 0.0, "Dead account must have 0 payouts")
    _check(abs(float(res["cf12_usd"]) - (-expected_fees)) < 1e-6, "cf12 at day 252 must equal -total_fees")
    _check(abs(float(res["cf_terminal_usd"]) - (-expected_fees)) < 1e-6, "cf_terminal must equal -total_fees")


# ==============================================================================
# 4. quant_core.tca
# ==============================================================================


@given(
    bad_swap=st.sampled_from(["", "   ", None, "NaN", "nan", "Inf", "-Inf", float("nan"), float("inf"), True]),
    nonzero_swap=st.one_of(
        st.floats(min_value=-500.0, max_value=-0.01, allow_nan=False, allow_infinity=False),
        st.floats(min_value=0.01, max_value=500.0, allow_nan=False, allow_infinity=False),
    ),
)
def test_tca_blank_nan_and_nonzero_swap_fail_closed(bad_swap: Any, nonzero_swap: float) -> None:
    base_row: dict[str, Any] = {
        "utc_ts": 1700000000,
        "magic": 20261122,
        "symbol": "USDJPY",
        "side": "BUY",
        "event_type": "EXIT",
        "signal_price": 150.0,
        "fill_price": 150.01,
        "swap_usd": "0.0",
    }

    if bad_swap in ("", "   ", None):
        parsed = parse_exec_audit_row({**base_row, "swap_usd": bad_swap})
        _check(parsed["swap_usd"] is None, "Blank/None swap_usd must preserve None (never coerce to 0.0)")
        with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
            validate_tca_post_reconcile([parsed], require_zero_swap=True)
    else:
        with pytest.raises(ValueError):
            parse_exec_audit_row({**base_row, "swap_usd": bad_swap})
        with pytest.raises(ValueError):
            validate_tca_post_reconcile([{**base_row, "swap_usd": bad_swap}], require_zero_swap=True)

    # Non-zero finite swap fails closed when require_zero_swap=True
    parsed_nz = parse_exec_audit_row({**base_row, "swap_usd": nonzero_swap})
    with pytest.raises(ValueError, match="NONZERO_SWAP_USD"):
        validate_tca_post_reconcile([parsed_nz], require_zero_swap=True)


@given(
    base_mid=st.floats(min_value=50.0, max_value=250.0, allow_nan=False, allow_infinity=False),
    d1=st.floats(min_value=-2.0, max_value=2.0, allow_nan=False, allow_infinity=False),
    d10=st.floats(min_value=-4.0, max_value=4.0, allow_nan=False, allow_infinity=False),
    future_shock=st.floats(min_value=10.0, max_value=80.0, allow_nan=False, allow_infinity=False),
)
def test_tca_markout_buy_sell_symmetry_and_strict_causality(
    base_mid: float,
    d1: float,
    d10: float,
    future_shock: float,
) -> None:
    t0 = 1_700_000_000
    quotes_a = {
        "USDJPY": [
            {"utc_ts": t0 - 5, "mid": base_mid},
            {"utc_ts": t0 + 1, "mid": max(1.0, base_mid + d1)},
            {"utc_ts": t0 + 10, "mid": max(1.0, base_mid + d10)},
            {"utc_ts": t0 + 60, "mid": max(1.0, base_mid + d10 + 1.0)},
        ]
    }
    # Perturb quote strictly AFTER +10s horizon -> +1s and +10s markouts MUST stay bit-for-bit identical!
    quotes_b = {
        "USDJPY": [
            {"utc_ts": t0 - 5, "mid": base_mid},
            {"utc_ts": t0 + 1, "mid": max(1.0, base_mid + d1)},
            {"utc_ts": t0 + 10, "mid": max(1.0, base_mid + d10)},
            {"utc_ts": t0 + 60, "mid": max(1.0, base_mid + future_shock)},
        ]
    }
    buy_fill = {"utc_ts": t0, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "fill_price": base_mid}
    sell_fill = {"utc_ts": t0, "symbol": "USDJPY", "side": "SELL", "event_type": "ENTRY", "fill_price": base_mid}

    mc_buy_a = compute_markout_curve([buy_fill], quotes_a, horizons_sec=(1, 10, 60, 300))
    mc_sell_a = compute_markout_curve([sell_fill], quotes_a, horizons_sec=(1, 10, 60, 300))
    mc_buy_b = compute_markout_curve([buy_fill], quotes_b, horizons_sec=(1, 10, 60, 300))

    for lbl in ("+1s", "+10s"):
        b_bps = mc_buy_a["by_horizon"][lbl]["mean_markout_bps"]
        s_bps = mc_sell_a["by_horizon"][lbl]["mean_markout_bps"]
        b_px = mc_buy_a["by_horizon"][lbl]["mean_markout_price"]
        s_px = mc_sell_a["by_horizon"][lbl]["mean_markout_price"]
        _check(b_bps is not None and s_bps is not None, f"Expected observed markout at {lbl}")
        _check(abs(b_bps + s_bps) <= 1e-6, f"BUY/SELL markout_bps asymmetry at {lbl}: {b_bps} vs {s_bps}")
        _check(abs(b_px + s_px) <= 1e-8, f"BUY/SELL markout_price asymmetry at {lbl}: {b_px} vs {s_px}")
        # Strict causality: mutating t0+60 quote cannot touch +1s or +10s!
        _check(
            mc_buy_a["by_horizon"][lbl]["mean_markout_bps"] == mc_buy_b["by_horizon"][lbl]["mean_markout_bps"],
            f"Causality leak into {lbl} from t0+60 quote mutation",
        )

    # Missing horizon (+5m = t0+300 > max quote t0+60) MUST return None (never fabricate)
    _check(mc_buy_a["by_horizon"]["+5m"]["mean_markout_bps"] is None, "Missing +5m quote must return None")
    _check(mc_buy_a["by_horizon"]["+5m"]["n_missing"] == 1, "Missing +5m count must be 1")


# ==============================================================================
# 5. quant_core.causality
# ==============================================================================


@given(
    seed=st.integers(min_value=1, max_value=50_000),
    window=st.integers(min_value=3, max_value=8),
)
def test_causality_causal_passes_and_lookahead_caught(seed: int, window: int) -> None:
    rng = np.random.default_rng(seed)
    n_bars = 36
    t0 = 1_700_000_000
    times = np.array([t0 + i * 60 for i in range(n_bars)], dtype=np.int64)
    bo = 150.0 + np.cumsum(rng.normal(0.0, 0.2, size=n_bars))
    bc = bo + rng.normal(0.0, 0.1, size=n_bars)
    bh = np.maximum(bo, bc) + 0.05
    bl = np.minimum(bo, bc) - 0.05
    quotes = np.column_stack([bo, bh, bl, bc, bo + 0.02, bh + 0.02, bl + 0.02, bc + 0.02]).astype(np.float64)

    def causal_sma(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        c = q[:, 3]
        out = np.full(len(c), np.nan, dtype=np.float64)
        for i in range(window, len(c)):
            out[i] = float(np.mean(c[i - window : i]))
        return out

    def leaky_shift_m1(_ts: np.ndarray, q: np.ndarray) -> np.ndarray:
        out = np.empty(q.shape[0], dtype=np.float64)
        out[:-1] = q[1:, 3]
        out[-1] = q[-1, 3]
        return out

    res = assert_prefix_invariance_numpy(causal_sma, times, quotes, [12, 24], seed=seed)
    _check(res["passed"] is True, "Strictly causal rolling SMA must pass")

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_numpy(leaky_shift_m1, times, quotes, [12, 24], seed=seed)

    series = rng.normal(0.0, 1.0, size=36)
    res_1d = assert_prefix_invariance_series(lambda v: np.cumsum(v), series, [12, 24], seed=seed)
    _check(res_1d["passed"] is True, "Causal cumsum must pass")

    with pytest.raises(CausalityViolationError):
        assert_prefix_invariance_series(lambda v: v - float(np.mean(v)), series, [12, 24], seed=seed)


# ==============================================================================
# 6. quant_core.red_news
# ==============================================================================


@given(
    events_spec=st.lists(
        st.tuples(
            st.integers(min_value=1_514_764_800, max_value=1_735_603_200),  # 2018-01-01 .. 2024-12-31
            st.sampled_from(sorted(ALLOWED_CURRENCIES)),
            st.integers(min_value=1, max_value=MAX_BLACKOUT_SEC),
        ),
        min_size=1,
        max_size=8,
        unique_by=lambda item: (item[0], item[1]),
    ),
)
def test_red_news_valid_windows_monotonic_and_bounded(events_spec: list[tuple[int, str, int]]) -> None:
    payload = {
        "events": [
            {
                "utc_ts": ts,
                "utc_iso": datetime.fromtimestamp(ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ccy": ccy,
                "event": f"{ccy}_MACRO_{i}",
                "blackout_sec": bsec,
            }
            for i, (ts, ccy, bsec) in enumerate(events_spec)
        ]
    }
    with tempfile.TemporaryDirectory() as td:
        p = Path(td) / "cal.json"
        p.write_text(json.dumps(payload), encoding="utf-8")
        loaded = load_calendar_events(p)

    _check(len(loaded) == len(events_spec), "Event count mismatch")
    ts_list = [e.utc_ts for e in loaded]
    _check(ts_list == sorted(ts_list), "Loaded events must be monotonically sorted by utc_ts")
    for ev in loaded:
        _check(1 <= ev.blackout_sec <= MAX_BLACKOUT_SEC, f"blackout_sec out of bounds: {ev.blackout_sec}")
        _check(ev.ccy in ALLOWED_CURRENCIES, f"Unexpected currency: {ev.ccy}")
    summary = summarize_calendar_events(loaded)
    _check(summary["total_events"] == len(loaded), "Summary total_events mismatch")


@given(
    bad_blackout=st.one_of(
        st.integers(min_value=-1000, max_value=0),
        st.integers(min_value=MAX_BLACKOUT_SEC + 1, max_value=MAX_BLACKOUT_SEC + 100_000),
        st.sampled_from([float("nan"), float("inf"), True, False, 300.5]),
    ),
    bad_ccy=st.sampled_from(["BTC", "CNY", "VND", "", "XAU"]),
)
def test_red_news_poisoned_inputs_rejected(bad_blackout: Any, bad_ccy: str) -> None:
    with pytest.raises(ValueError):
        validate_blackout_sec(bad_blackout)

    with tempfile.TemporaryDirectory() as td:
        p_ccy = Path(td) / "bad_ccy.json"
        p_ccy.write_text(
            json.dumps({"events": [{"utc_ts": 1700000000, "ccy": bad_ccy, "event": "CPI"}]}),
            encoding="utf-8",
        )
        with pytest.raises(ValueError):
            load_calendar_events(p_ccy)


# ==============================================================================
# 7. quant_core.holdout_guard
# ==============================================================================


@given(
    dev_offset_days=st.integers(min_value=0, max_value=(date(2024, 12, 31) - date(2018, 1, 1)).days),
    dev_ts=st.integers(min_value=DEV_START_UTC_TS, max_value=HOLDOUT_START_UTC_TS - 1),
)
def test_holdout_guard_pre_2025_passes(dev_offset_days: int, dev_ts: int) -> None:
    d = date(2018, 1, 1) + timedelta(days=dev_offset_days)
    enforce_pre_holdout_dates([d.isoformat()], context="hyp_dev_ok")
    enforce_pre_holdout_ts(dev_ts, start_ts=DEV_START_UTC_TS, stop_ts=HOLDOUT_START_UTC_TS, context="hyp_dev_ts_ok")


@given(
    holdout_offset_days=st.integers(min_value=0, max_value=730),
    neg_tz_hours=st.integers(min_value=1, max_value=12),
    holdout_ts=st.integers(min_value=HOLDOUT_START_UTC_TS, max_value=HOLDOUT_START_UTC_TS + 100_000_000),
)
def test_holdout_guard_post_2025_and_tz_shifted_always_raise(
    holdout_offset_days: int,
    neg_tz_hours: int,
    holdout_ts: int,
) -> None:
    # 1. Direct >= 2025-01-01 ISO date
    d_bad = date(2025, 1, 1) + timedelta(days=holdout_offset_days)
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_dates([d_bad.isoformat()], context="hyp_ho_date")

    # 2. TZ-shifted string showing local date 2024-12-31 whose UTC instant is >= 2025-01-01T00:00:00Z!
    tz_neg = timezone(timedelta(hours=-neg_tz_hours))
    local_dt = datetime(2024, 12, 31, 24 - neg_tz_hours, 0, 1, tzinfo=tz_neg)
    _check(local_dt.date() == date(2024, 12, 31), "Local calendar date must look like 2024-12-31")
    _check(local_dt.astimezone(UTC).date() >= date(2025, 1, 1), "UTC date must cross into 2025+")
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_dates([local_dt.isoformat()], context="hyp_ho_tz_shift")

    # 3. Direct >= HOLDOUT_START_UTC_TS epoch seconds
    with pytest.raises(HoldoutLockError):
        enforce_pre_holdout_ts(holdout_ts, start_ts=DEV_START_UTC_TS, stop_ts=HOLDOUT_START_UTC_TS, context="hyp_ho_ts")
