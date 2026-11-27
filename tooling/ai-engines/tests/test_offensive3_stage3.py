"""Synthetic offline unit tests for Offensive #3 Stage 3 Blind Cluster B Pipeline & Swing-Safe RobustnessGate.

Strictly tests ONLY synthetic pre-2025 fixtures (ZERO live Cluster B execution, ZERO Holdout 2025+ rows):
  1. Swing-safe multi-day Random-Entry MC (`allow_weekend_gaps=True` + `swap_drag_per_day_r`)
     plus `matched_hold_timing_permutation_p` (`p < 0.05` check) and `evaluate_crisis_stress_windows`
     (3 historical stress windows on `2018-2024`, fail-closed on `>= 2025-01-01`).
  2. Dual-Ledger DuckDB writes (`offensive3_primary_m200` + `offensive3_exploratory_m1200`, unique PKs,
     100% pass+fail logged, SQLite hash-chain parity verified).
  3. Mandatory `G7_pbo_cscv` execution via explicit `pbo_returns_matrix` (NEVER silently skipped — `B4`),
     exact `G08` `KillCriteria`, and strict rejection of `CONDITIONAL_RETEST`.
  4. `sign_flip_p_numba` with `draws=50_000` + Student-t / Newey-West HAC cross-check &
     effective independent trials `N_eff = (sum(lam))^2 / sum(lam^2)`.
  5. 3-Tier Funnel Classifier (`TIER_1_FTMO_READY` with `M1_NATIVE_VERIFIED` vs
     `PROVISIONAL_AWAITING_OWNER_M1_EXPORT`, `TIER_2_PERSONAL_VAULT`, `TIER_3_DEAD_NO_EDGE`).
  6. Campaign cap guards (`<= 200` primary, `<= 1200` exploratory, `discovery_years == [2018, 2019, 2020]`)
     and `< 300 KB` compact tracked funnel serialization enforcement.
"""

from __future__ import annotations

import json
import sys
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES.parents[1]
for _p in (AI_ENGINES, REPO_ROOT):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_factory.experiment_ledger import ExperimentLedger  # noqa: E402
from quant_factory.offensive3.common_contract import (  # noqa: E402
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    RES_D1_YAHOO_SANCTIONED,
    RES_NATIVE_M1_BIDASK,
    TIER_12OLD,
    TIER_NEW7,
    _build_weekday_calendar,
    save_family_candidates,
)
from quant_factory.offensive3.stage3_pipeline import (  # noqa: E402
    CAMPAIGN_EXPLORATORY_FAMILY_ID,
    CAMPAIGN_PRIMARY_FAMILY_ID,
    MAX_TRACKED_FUNNEL_BYTES,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    SIGN_FLIP_DRAWS,
    TAG_M1_NATIVE_VERIFIED,
    TAG_PROVISIONAL_AWAITING_M1,
    TIER_1_FTMO_READY,
    TIER_2_PERSONAL_VAULT,
    TIER_3_DEAD_NO_EDGE,
    build_g08_kill_criteria,
    classify_candidate_tier,
    compute_effective_independent_trials,
    compute_sign_flip_p_50k,
    compute_student_t_and_newey_west_p,
    load_all_family_checkpoints,
    run_stage3_blind_clb,
    student_t_one_sided_p,
    write_compact_funnel_json,
)
from quant_factory.robustness_gate import (  # noqa: E402
    CRISIS_STRESS_WINDOWS,
    evaluate_crisis_stress_windows,
    matched_hold_timing_permutation_p,
    random_entry_mc_on_bars,
    random_entry_mc_on_closes,
)


def _make_synthetic_d1_asset(
    symbol: str,
    *,
    years: tuple[int, ...] = ALL_DEV_YEARS,
    drift_per_day: float = 0.0001,
    vol_per_day: float = 0.006,
    base_price: float = 100.0,
    resolution: str = RES_D1_YAHOO_SANCTIONED,
    blindness_tier: str = TIER_NEW7,
    seed: int = 42,
) -> dict[str, Any]:
    dates = _build_weekday_calendar(years)
    n = len(dates)
    rng = np.random.default_rng(seed)
    ts = np.array(
        [int(datetime.fromisoformat(f"{d}T00:00:00+00:00").timestamp()) for d in dates],
        dtype=np.int64,
    )
    rets = drift_per_day + rng.normal(0.0, vol_per_day, size=n)
    o = base_price * np.exp(np.cumsum(rets))
    c = o * (1.0 + rng.normal(0.0, vol_per_day * 0.5, size=n))
    h = np.maximum(o, c) * (1.0 + abs(vol_per_day) * 0.6)
    lo = np.minimum(o, c) * (1.0 - abs(vol_per_day) * 0.6)
    wds = np.array([date.fromisoformat(d).weekday() for d in dates], dtype=np.int32)
    yrs = np.array([int(d[:4]) for d in dates], dtype=np.int32)
    return {
        "symbol": symbol,
        "data_resolution": resolution,
        "blindness_tier": blindness_tier,
        "m1": None,
        "d1": {
            "times_sec": ts,
            "dates": dates,
            "years": yrs,
            "weekdays": wds,
            "open": o,
            "high": h,
            "low": lo,
            "close": c,
        },
    }


def _make_synthetic_trades_and_daily(
    *,
    symbol: str,
    years: tuple[int, ...],
    r_values: np.ndarray,
    sides: np.ndarray,
    hold_bars: int = 3,
    cost_drag_1x_r: float = 0.04,
    swap_real_r: float = -0.02,
    swap_zero_pos_r: float = -0.02,
    resolution: str = RES_NATIVE_M1_BIDASK,
    blindness_tier: str = TIER_12OLD,
    fade_shift_r: float = -0.60,
    margin_util_frac: float = 0.15,
) -> dict[str, Any]:
    cal = _build_weekday_calendar(years)
    n_trades = len(r_values)
    step = max(1, (len(cal) - hold_bars - 2) // max(1, n_trades))
    trades: list[dict[str, Any]] = []
    d1x: dict[str, float] = {d: 0.0 for d in cal}
    d15x: dict[str, float] = {d: 0.0 for d in cal}
    d2x: dict[str, float] = {d: 0.0 for d in cal}
    dzpos: dict[str, float] = {d: 0.0 for d in cal}
    dfade: dict[str, float] = {d: 0.0 for d in cal}

    for i in range(n_trades):
        ei = min(i * step, len(cal) - hold_bars - 1)
        xi = ei + hold_bars
        ed = cal[ei]
        xd = cal[xi]
        ets = int(datetime.fromisoformat(f"{ed}T00:00:00+00:00").timestamp())
        xts = int(datetime.fromisoformat(f"{xd}T00:00:00+00:00").timestamp())
        r1 = float(r_values[i])
        r15 = r1 - 0.5 * cost_drag_1x_r
        r2 = r1 - 1.0 * cost_drag_1x_r
        rz = r1 - swap_real_r + swap_zero_pos_r
        rf = -r1 + fade_shift_r if r1 > 0.0 else (-r1 - 0.10)
        d1x[xd] += r1
        d15x[xd] += r15
        d2x[xd] += r2
        dzpos[xd] += rz
        dfade[xd] += rf
        trades.append(
            {
                "symbol": symbol,
                "data_resolution": resolution,
                "blindness_tier": blindness_tier,
                "side": int(sides[i]),
                "entry_date": ed,
                "exit_date": xd,
                "entry_ts": ets,
                "exit_ts": xts,
                "entry_price": 100.0,
                "sl_price": 98.5 if int(sides[i]) > 0 else 101.5,
                "sl_dist": 1.5,
                "hold_bars": hold_bars,
                "swap_real_R": swap_real_r,
                "swap_zero_pos_R": swap_zero_pos_r,
                "net_R": r1,
                "net_R_1x": r1,
                "net_R_15x": r15,
                "net_R_2x": r2,
                "net_R_zero_pos_1x": rz,
                "friction_over_sl_1x": cost_drag_1x_r,
                "friction_over_sl": 2.0 * cost_drag_1x_r,
                "margin_util_frac": margin_util_frac,
            }
        )

    return {
        "trades": trades,
        "daily_pnl_1x": d1x,
        "daily_pnl_15x": d15x,
        "daily_pnl_2x": d2x,
        "daily_pnl_zero_pos_swap": dzpos,
        "fade_daily_pnl_1x": dfade,
        "data_resolution": resolution,
        "blindness_tier": blindness_tier,
    }


def test_01_swing_safe_mc_timing_permutation_and_3_crisis_windows() -> None:
    assert ORDER_SEND_CAPABLE is False
    assert ORDER_SEND_COUNT == 0

    asset = _make_synthetic_d1_asset("EURGBP", years=CLUSTER_B_YEARS, drift_per_day=0.0, vol_per_day=0.005, seed=7)
    d1 = asset["d1"]
    n_trades = 80
    sides = np.array([1 if i % 2 == 0 else -1 for i in range(n_trades)], dtype=np.int64)
    durs = np.full(n_trades, 5, dtype=np.int64)  # 5 trading days -> ALWAYS spans a weekend!
    sl_fracs = np.full(n_trades, 0.015, dtype=np.float64)
    frics = np.full(n_trades, 0.02, dtype=np.float64)
    good_r = np.array([1.3 if i % 2 == 0 else -0.4 for i in range(n_trades)], dtype=np.float64)

    # 1A. Swing-safe MC with allow_weekend_gaps=True & swap_drag_per_day_r deducted into null
    mc_no_swap = random_entry_mc_on_bars(
        ts=d1["times_sec"],
        bar_o=d1["open"],
        bar_h=d1["high"],
        bar_l=d1["low"],
        bar_c=d1["close"],
        bar_sec=86400,
        trade_r=good_r,
        trade_sides=sides,
        trade_durs=durs,
        trade_sl_fracs=sl_fracs,
        trade_frics=frics,
        draws=300,
        seed=20261127,
        allow_weekend_gaps=True,
        swap_drag_per_day_r=0.0,
    )
    mc_with_swap = random_entry_mc_on_bars(
        ts=d1["times_sec"],
        bar_o=d1["open"],
        bar_h=d1["high"],
        bar_l=d1["low"],
        bar_c=d1["close"],
        bar_sec=86400,
        trade_r=good_r,
        trade_sides=sides,
        trade_durs=durs,
        trade_sl_fracs=sl_fracs,
        trade_frics=frics,
        draws=300,
        seed=20261127,
        allow_weekend_gaps=True,
        swap_drag_per_day_r=0.04,
    )
    assert mc_no_swap["mc_mode"] == "real_market_bars_swing"
    assert mc_no_swap["allow_weekend_gaps"] is True
    assert mc_no_swap["beat_rate_unbiased"] >= 0.90
    assert mc_no_swap["beat_rate_same_side"] >= 0.90
    # Deducting swap_drag_per_day_r=0.04 over 5d holds MUST shift random-entry null median strictly downward!
    assert mc_with_swap["null_unbiased_median_r"] < mc_no_swap["null_unbiased_median_r"] - 5.0
    assert mc_with_swap["swap_drag_per_day_r"] == 0.04

    mc_close_drag = random_entry_mc_on_closes(
        closes=d1["close"],
        trade_r=good_r,
        trade_sides=sides,
        trade_durs=durs,
        trade_sl_fracs=sl_fracs,
        trade_frics=frics,
        draws=200,
        seed=11,
        swap_drag_per_day_r=0.03,
    )
    assert mc_close_drag["mc_mode"] == "close_series_swing"
    assert mc_close_drag["beat_rate_unbiased"] >= 0.90

    # 1B. Matched-Hold Timing Permutation (`p < 0.05` passes strong edge, fails pure noise & passive drift)
    closes = d1["close"]
    mkt_rets = np.diff(closes) / closes[:-1]
    t_days = d1["dates"][10 : 10 + n_trades]
    perm_good = matched_hold_timing_permutation_p(
        mkt_rets, t_days, good_r, draws=2000, seed=20261127, hold_bars=5, trade_sides=sides
    )
    assert perm_good["passed"] is True
    assert perm_good["p_value"] < 0.05
    assert perm_good["null_mode"] == "matched_hold_market_timing"

    rng = np.random.default_rng(99)
    noise_r = rng.normal(0.0, 1.0, size=n_trades)
    perm_noise = matched_hold_timing_permutation_p(
        mkt_rets, t_days, noise_r, draws=2000, seed=20261127, hold_bars=5, trade_sides=sides
    )
    assert perm_noise["passed"] is False
    assert perm_noise["p_value"] >= 0.05

    # Holdout date guard on timing permutation
    with pytest.raises(HoldoutLockError):
        matched_hold_timing_permutation_p(mkt_rets, ["2024-12-30", "2025-01-02"], [1.0, 1.0], draws=100)

    # 1C. Crisis stress windows (3 windows strictly on 2018-2024)
    all_days = _build_weekday_calendar(ALL_DEV_YEARS)
    calm_dev = {d: 0.02 for d in all_days}
    cr_ok = evaluate_crisis_stress_windows(calm_dev)
    assert cr_ok["passed"] is True
    assert cr_ok["survived_count"] == 3
    assert set(cr_ok["windows"].keys()) == set(CRISIS_STRESS_WINDOWS.keys())

    blowup_dev = dict(calm_dev)
    blowup_dev["2024-08-05"] = -8.5  # Yen carry unwind blowup (> 6R 1-day limit)
    cr_fail = evaluate_crisis_stress_windows(blowup_dev)
    assert cr_fail["passed"] is False
    assert "2024_YEN_UNWIND" in cr_fail["failed_windows"]

    # Holdout leak in crisis stress fails closed!
    leak_dev = dict(calm_dev)
    leak_dev["2025-01-02"] = 0.1
    with pytest.raises(HoldoutLockError):
        evaluate_crisis_stress_windows(leak_dev)


def test_02_sign_flip_50k_analytical_p_and_effective_trials_n_eff() -> None:
    rng = np.random.default_rng(2026)
    # 1. Exact Student-t critical value verification (~0.025 one-sided at t=1.984, df=100)
    p_crit = student_t_one_sided_p(1.98397, 100)
    assert abs(p_crit - 0.025) < 5e-4
    assert abs(student_t_one_sided_p(0.0, 50) - 0.5) < 1e-12

    # 2. sign_flip_p_numba with draws=50_000 (minimum achievable p = 1/50001 ≈ 2e-5)
    n_days = 1000
    strong_daily = np.zeros(n_days, dtype=np.float64)
    fade_daily = np.zeros(n_days, dtype=np.float64)
    active_idx = np.arange(0, n_days, 10)
    strong_daily[active_idx] = rng.normal(0.55, 0.70, size=len(active_idx))
    fade_daily[active_idx] = -strong_daily[active_idx] - 0.05

    sf = compute_sign_flip_p_50k(strong_daily, fade_daily, draws=SIGN_FLIP_DRAWS, seed=20261127)
    assert sf["draws"] == 50_000
    assert sf["n_active_days"] == len(active_idx)
    assert sf["p_value"] < 0.0005

    an = compute_student_t_and_newey_west_p(strong_daily)
    assert an["p_student_t"] < 0.001
    assert an["p_newey_west"] < 0.01

    # 3. Effective independent trials N_eff participation ratio
    # 3A: 10 identical copies -> N_eff == 1.0
    base = rng.normal(0.0, 1.0, size=400)
    mat_dup = np.column_stack([base for _ in range(10)])
    neff_dup = compute_effective_independent_trials(mat_dup)
    assert abs(neff_dup["n_eff"] - 1.0) < 1e-6

    # 3B: 12 independent orthogonal columns -> N_eff close to 12.0
    mat_indep = rng.normal(0.0, 1.0, size=4000 * 12).reshape(4000, 12)
    neff_indep = compute_effective_independent_trials(mat_indep)
    assert 11.0 < neff_indep["n_eff"] <= 12.0


def test_03_stage3_e2e_dual_ledger_mandatory_g7_pbo_3tier_and_compact_funnel(tmp_path: Path) -> None:
    """End-to-end synthetic Stage 3 pipeline verifying ALL G3 gates, Dual-Ledger, G7 PBO, 3-Tier & <300KB."""
    cal_clb = _build_weekday_calendar(CLUSTER_B_YEARS)
    cal_cla = _build_weekday_calendar(CLUSTER_A_YEARS)

    # Synthetic 2-symbol universe: EURUSD (NATIVE_M1_BIDASK) + EURGBP (D1_YAHOO_SANCTIONED / TRUE_BLIND_7)
    universe = {
        "assets": {
            "EURUSD": _make_synthetic_d1_asset(
                "EURUSD",
                years=ALL_DEV_YEARS,
                drift_per_day=0.0,
                vol_per_day=0.0045,
                base_price=1.10,
                resolution=RES_NATIVE_M1_BIDASK,
                blindness_tier=TIER_12OLD,
                seed=11,
            ),
            "EURGBP": _make_synthetic_d1_asset(
                "EURGBP",
                years=ALL_DEV_YEARS,
                drift_per_day=0.0,
                vol_per_day=0.0045,
                base_price=0.86,
                resolution=RES_D1_YAHOO_SANCTIONED,
                blindness_tier=TIER_NEW7,
                seed=22,
            ),
        }
    }

    # Synthetic PORT_7E incumbent daily returns (strictly pre-2025)
    rng_inc = np.random.default_rng(777)
    inc_vals = rng_inc.normal(0.0005, 0.0045, size=len(cal_clb))
    inc_daily = {d: float(v) for d, v in zip(cal_clb, inc_vals, strict=True)}

    # Build a synthetic family module implementing `evaluate_candidate(spec, universe, years)`
    call_counter: dict[tuple[str, tuple[int, ...]], int] = {}

    class _SyntheticFamilyModule:
        FAMILY_ID = "F10_TRUE_BLIND_CROSS7"

        @staticmethod
        def evaluate_candidate(spec: dict[str, Any], _univ: Any, years: tuple[int, ...]) -> dict[str, Any]:
            cid = str(spec["candidate_id"])
            key = (cid, tuple(years))
            call_counter[key] = call_counter.get(key, 0) + 1
            mode = str(spec["synth_mode"])
            sym = str(spec["symbol"])
            res = str(spec["data_resolution"])
            tier = str(spec["blindness_tier"])

            n_tr = 90 if tuple(years) == CLUSTER_B_YEARS else 60
            sides = np.array([1 if (i % 4 < 2) else -1 for i in range(n_tr)], dtype=np.int64)
            rng_c = np.random.default_rng(int(spec["seed"]))

            if mode == "tier1_strong":
                r_vals = np.array([1.25 if i % 2 == 0 else -0.35 for i in range(n_tr)], dtype=np.float64)
                r_vals += rng_c.normal(0.0, 0.05, size=n_tr)
                out = _make_synthetic_trades_and_daily(
                    symbol=sym,
                    years=tuple(years),
                    r_values=r_vals,
                    sides=sides,
                    hold_bars=3,
                    cost_drag_1x_r=0.03,
                    resolution=res,
                    blindness_tier=tier,
                )
            elif mode == "tier2_high_corr_port7e":
                # Genuine standalone edge (beats BH-FDR + MC + 2x + Fade + Trim),
                # but deliberately correlated with PORT_7E (`|r| > 0.50 > 0.15`!) -> MUST land in TIER_2!
                r_vals = np.array([1.20 if i % 2 == 0 else -0.30 for i in range(n_tr)], dtype=np.float64)
                out = _make_synthetic_trades_and_daily(
                    symbol=sym,
                    years=tuple(years),
                    r_values=r_vals,
                    sides=sides,
                    hold_bars=3,
                    cost_drag_1x_r=0.03,
                    resolution=res,
                    blindness_tier=tier,
                )
                if tuple(years) == CLUSTER_B_YEARS:
                    # Inject strong correlation with PORT_7E onto daily curve while preserving net positive edge
                    for dk in cal_clb:
                        out["daily_pnl_1x"][dk] += 180.0 * inc_daily[dk]
                        out["daily_pnl_15x"][dk] += 180.0 * inc_daily[dk]
                        out["daily_pnl_2x"][dk] += 180.0 * inc_daily[dk]
                        out["daily_pnl_zero_pos_swap"][dk] += 180.0 * inc_daily[dk]
            elif mode == "conditional_retest_soft_fail":
                # Strong edge EXCEPT fails 1 soft gate (low Cluster B Sharpe or asymmetric side warning)
                # Wait: force unidirectional with allow_unidirectional=False -> R2 WARN_ASYMMETRY_OR_YEAR (1 soft gate!)
                sides_uni = np.ones(n_tr, dtype=np.int64)
                r_vals = np.array([1.25 if i % 2 == 0 else -0.35 for i in range(n_tr)], dtype=np.float64)
                out = _make_synthetic_trades_and_daily(
                    symbol=sym,
                    years=tuple(years),
                    r_values=r_vals,
                    sides=sides_uni,
                    hold_bars=3,
                    cost_drag_1x_r=0.03,
                    resolution=res,
                    blindness_tier=tier,
                )
            else:
                # Dead noise / negative edge -> MUST land in TIER_3_DEAD_NO_EDGE!
                r_vals = rng_c.normal(-0.08, 0.90, size=n_tr)
                out = _make_synthetic_trades_and_daily(
                    symbol=sym,
                    years=tuple(years),
                    r_values=r_vals,
                    sides=sides,
                    hold_bars=3,
                    cost_drag_1x_r=0.05,
                    resolution=res,
                    blindness_tier=tier,
                    fade_shift_r=0.10,
                )

            return {
                "spec": spec,
                "metrics": {"n_trades": len(out["trades"])},
                "allow_unidirectional": bool(spec.get("allow_unidirectional", False)),
                **out,
            }

    # Save valid Cluster A checkpoint via common_contract.save_family_candidates (`2018-2020` ONLY!)
    cdir = tmp_path / "candidates"
    rationale = "Institutional cross-border liquidity imbalance creates persistent multi-day risk transfer edge."
    prim_cands = [
        {
            "candidate_id": "C_TIER1_M1",
            "tier": "PRIMARY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURUSD",
            "data_resolution": RES_NATIVE_M1_BIDASK,
            "blindness_tier": TIER_12OLD,
            "synth_mode": "tier1_strong",
            "seed": 101,
            "economic_rationale": rationale,
            "counterparty_mechanism": "Dealer inventory rebalancing across FX majors",
        },
        {
            "candidate_id": "C_TIER1_D1_BLIND7",
            "tier": "PRIMARY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURGBP",
            "data_resolution": RES_D1_YAHOO_SANCTIONED,
            "blindness_tier": TIER_NEW7,
            "synth_mode": "tier1_strong",
            "seed": 102,
            "economic_rationale": rationale,
            "counterparty_mechanism": "Corporate cross-currency hedging flow on EURGBP",
        },
        {
            "candidate_id": "C_TIER2_CORR",
            "tier": "PRIMARY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURUSD",
            "data_resolution": RES_NATIVE_M1_BIDASK,
            "blindness_tier": TIER_12OLD,
            "synth_mode": "tier2_high_corr_port7e",
            "seed": 103,
            "economic_rationale": rationale,
            "counterparty_mechanism": "Shared macro risk-on factor correlated with PORT_7E",
        },
        {
            "candidate_id": "C_COND_RETEST",
            "tier": "PRIMARY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURUSD",
            "data_resolution": RES_NATIVE_M1_BIDASK,
            "blindness_tier": TIER_12OLD,
            "synth_mode": "conditional_retest_soft_fail",
            "allow_unidirectional": False,
            "seed": 104,
            "economic_rationale": rationale,
            "counterparty_mechanism": "Unidirectional drift not explicitly authorized",
        },
        {
            "candidate_id": "C_TIER3_DEAD_1",
            "tier": "PRIMARY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURGBP",
            "data_resolution": RES_D1_YAHOO_SANCTIONED,
            "blindness_tier": TIER_NEW7,
            "synth_mode": "dead_noise",
            "seed": 105,
            "economic_rationale": rationale,
            "counterparty_mechanism": "Noise control trial 1",
        },
    ]
    expl_cands = [
        {
            "candidate_id": f"C_EXPL_DEAD_{i}",
            "tier": "EXPLORATORY",
            "prop_track": "FTMO_SWING",
            "symbol": "EURGBP",
            "data_resolution": RES_D1_YAHOO_SANCTIONED,
            "blindness_tier": TIER_NEW7,
            "synth_mode": "dead_noise",
            "seed": 200 + i,
            "economic_rationale": rationale,
            "counterparty_mechanism": f"Exploratory noise control {i}",
        }
        for i in range(4)
    ]

    save_family_candidates(
        "F10_TRUE_BLIND_CROSS7",
        {"primary": prim_cands, "exploratory": expl_cands},
        {"discovery_years": list(CLUSTER_A_YEARS), "primary_cap": 10},
        candidates_dir=cdir,
    )

    duck_path = tmp_path / "exp.duckdb"
    reg_path = tmp_path / "reg.sqlite3"
    full_out = tmp_path / "blind_clb_full_results.json"
    funnel_out = tmp_path / "OFFENSIVE3-ALPHA-FUNNEL-20261127.json"

    res = run_stage3_blind_clb(
        candidates_dir=cdir,
        family_modules={"F10_TRUE_BLIND_CROSS7": _SyntheticFamilyModule},
        universe=universe,
        incumbent_daily_returns=inc_daily,
        duckdb_path=duck_path,
        registry_path=reg_path,
        full_results_path=full_out,
        tracked_funnel_path=funnel_out,
        campaign_run_id="test-off3-run-01",
        sign_flip_draws=SIGN_FLIP_DRAWS,
        timing_perm_draws=2000,
        mc_draws=250,
        pbo_n_slices=8,
        seed=20261127,
    )

    # 1. Hard safety invariants + single blind Cl.B pass verification
    assert res["order_send_capable"] is False
    assert res["order_send_count"] == 0
    assert res["holdout_rows_analysed"] == 0
    for cand in [*prim_cands, *expl_cands]:
        assert call_counter[(cand["candidate_id"], CLUSTER_B_YEARS)] == 1

    # 2. Dual-Ledger DuckDB verification (`offensive3_primary_m200` + `offensive3_exploratory_m1200`)
    led = ExperimentLedger(duckdb_path=duck_path, registry_path=reg_path)
    try:
        assert led.verify_integrity()["verified"] is True
        assert led.get_cumulative_trial_count(CAMPAIGN_PRIMARY_FAMILY_ID) == 5
        assert led.get_cumulative_trial_count(CAMPAIGN_EXPLORATORY_FAMILY_ID) == 9
    finally:
        led.close()

    assert res["duckdb_ledger_summary"]["primary_cumulative_m"] == 5
    assert res["duckdb_ledger_summary"]["exploratory_cumulative_m"] == 9
    assert res["statistical_config"]["sign_flip_draws"] == 50_000
    assert res["effective_trials_n_eff"]["primary_m200"]["n_eff"] >= 1.0
    assert res["effective_trials_n_eff"]["exploratory_m1200"]["n_eff"] >= 1.0

    # 3. Mandatory G7_pbo_cscv execution (`B4` — NEVER silently skipped on ANY candidate!)
    assert res["funnel_counts"]["g7_pbo_executed_count"] == 9
    by_cid = {c["candidate_id"]: c for c in res["candidates"]}
    for cid, crec in by_cid.items():
        gates = crec["research_council"]["gates"]
        assert "G7_pbo_cscv" in gates, f"G7_pbo_cscv missing for {cid}!"
        assert crec["sign_flip"]["draws"] == 50_000

    # 4. Exact 3-Tier Funnel classification & sub-tags & CONDITIONAL_RETEST rejection
    c_t1_m1 = by_cid["C_TIER1_M1"]
    assert c_t1_m1["classification"]["tier"] == TIER_1_FTMO_READY
    assert c_t1_m1["classification"]["tier1_resolution_tag"] == TAG_M1_NATIVE_VERIFIED
    assert c_t1_m1["research_council"]["verdict"] == "APPROVE_FOR_INCUBATION"

    c_t1_d1 = by_cid["C_TIER1_D1_BLIND7"]
    assert c_t1_d1["classification"]["tier"] == TIER_1_FTMO_READY
    assert c_t1_d1["classification"]["tier1_resolution_tag"] == TAG_PROVISIONAL_AWAITING_M1

    c_t2 = by_cid["C_TIER2_CORR"]
    assert c_t2["classification"]["tier"] == TIER_2_PERSONAL_VAULT
    assert "PROP_PORT7E_ORTHOGONALITY" in c_t2["classification"]["failed_prop_gates"]

    # CONDITIONAL_RETEST MUST be strictly rejected from Tier 1!
    c_cond = by_cid["C_COND_RETEST"]
    assert c_cond["research_council"]["verdict"] == "CONDITIONAL_RETEST"
    assert c_cond["classification"]["council_conditional_rejected"] is True
    assert c_cond["classification"]["tier"] != TIER_1_FTMO_READY
    assert "PROP_COUNCIL_CONDITIONAL_RETEST_REJECTED" in c_cond["classification"]["failed_prop_gates"]

    c_dead = by_cid["C_TIER3_DEAD_1"]
    assert c_dead["classification"]["tier"] == TIER_3_DEAD_NO_EDGE
    assert len(c_dead["classification"]["failed_core_gates"]) >= 1

    # 5. Tracked compact funnel JSON exists and is strictly < 300 KB
    assert full_out.is_file()
    assert funnel_out.is_file()
    assert funnel_out.stat().st_size < MAX_TRACKED_FUNNEL_BYTES
    funnel_doc = json.loads(funnel_out.read_text(encoding="utf-8"))
    assert funnel_doc["holdout_rows_analysed"] == 0
    assert funnel_doc["order_send_count"] == 0
    assert funnel_doc["funnel_counts"]["tier1_ftmo_ready"] == 2
    assert funnel_doc["funnel_counts"]["tier1_m1_native_verified"] == 1
    assert funnel_doc["funnel_counts"]["tier1_provisional_awaiting_m1"] == 1
    assert len(funnel_doc["tier1_ftmo_ready"]) == 2
    assert len(cal_cla) > 0


def test_04_g08_kill_criteria_cap_guards_and_300kb_funnel_enforcement(tmp_path: Path) -> None:
    # 1. Exact G08 KillCriteria thresholds (30 Swing vs 50 Intraday)
    kc_swing = build_g08_kill_criteria(is_intraday=False)
    kc_intra = build_g08_kill_criteria(is_intraday=True)
    assert kc_swing.max_bh_q == 0.10
    assert kc_swing.min_dsr == 0.50
    assert kc_swing.min_cluster_b_sharpe == 0.40
    assert kc_swing.min_cost_breakeven_mult == 2.0
    assert kc_swing.max_corr_vs_incumbent == 0.15
    assert kc_swing.max_tail_corr_vs_incumbent == 0.35
    assert kc_swing.min_trades_cluster_b == 30
    assert kc_intra.min_trades_cluster_b == 50
    assert kc_swing.max_pbo == 0.50
    assert kc_swing.require_incumbent is True
    assert kc_swing.require_robustness_gate is True

    # 2. Campaign primary cap guard (> 200 primary fails closed!)
    cdir = tmp_path / "over_cap"
    for f_idx in range(1, 13):
        fid = f"SYNTH_{f_idx:02d}"
        cands = [{"candidate_id": f"P_{f_idx}_{j}", "tier": "PRIMARY"} for j in range(18)]
        save_family_candidates(
            fid,
            {"primary": cands, "exploratory": []},
            {"discovery_years": list(CLUSTER_A_YEARS), "primary_cap": 18},
            candidates_dir=cdir,
        )
    # 12 * 18 = 216 > 200 -> MUST raise ValueError fail-closed!
    with pytest.raises(ValueError, match="CAMPAIGN_PRIMARY_CAP_EXCEEDED"):
        load_all_family_checkpoints(candidates_dir=cdir)

    # 3. Direct classifier unit test: Swing zero_pos_swap failure kills candidate to Tier 3!
    fake_base = {
        "is_primary": True,
        "is_swing": True,
        "min_trades_cluster_b": 30,
        "data_resolution": RES_D1_YAHOO_SANCTIONED,
        "bh_q_primary": 0.02,
        "bh_q_exploratory": 0.05,
        "robustness_gate": {
            "verdict": "PASS_ROBUST",
            "pillars": {
                "R1_random_entry_mc": {"beat_rate_unbiased": 0.96, "beat_rate_same_side": 0.94},
                "R3_top5_outlier_trim": {"trimmed_winners_pf": 1.35, "trimmed_winners_sum_r": 12.0},
            },
        },
        "net_r_1x": 20.0,
        "net_r_2x": 14.0,
        "net_r_zero_pos_swap": -2.5,  # Failed zero_pos_swap floor!
        "fade_net_r_1x": -10.0,
        "cost_breakeven_mult": 3.3,
        "n_trades_clb": 60,
        "research_council": {
            "verdict": "APPROVE_FOR_INCUBATION",
            "gates": {
                "G2_dsr_and_sharpe": {"passed": True},
                "G4_orthogonality": {"passed": True, "corr_all": 0.05, "corr_tail_5pct": 0.12},
                "G7_pbo_cscv": {"passed": True, "pbo": 0.25},
            },
        },
        "timing_permutation": {"passed": True, "p_value": 0.01},
        "prop_max_dd_pct_at_risk": 3.5,
        "prop_worst_1d_pct_at_risk": 1.2,
        "peak_margin_util_frac": 0.25,
        "margin_breached": False,
        "crisis_stress_2018_2024": {"passed": True},
    }
    cls_zpos_fail = classify_candidate_tier(fake_base)
    assert cls_zpos_fail["tier"] == TIER_3_DEAD_NO_EDGE
    assert "CORE_ZERO_POS_SWAP_FAIL" in cls_zpos_fail["failed_core_gates"]

    # 4. Funnel `< 300 KB` programmatic compaction & hard fail-closed limit
    huge_tier2 = [
        {
            "strategy_id": f"F01::CAND_{i:04d}",
            "alpha_family_id": "F01",
            "pool_tier": "EXPLORATORY",
            "is_primary": False,
            "is_swing": True,
            "symbols": ["EURGBP"],
            "data_resolution": RES_D1_YAHOO_SANCTIONED,
            "blindness_tier": TIER_NEW7,
            "n_trades_clb": 50,
            "net_r_1x": 15.0,
            "net_r_15x": 13.0,
            "net_r_2x": 11.0,
            "net_r_zero_pos_swap": 10.0,
            "fade_net_r_1x": -5.0,
            "sharpe_clb": 0.9,
            "dsr_council": 0.8,
            "dsr_empirical": 0.75,
            "p_sign_flip_50k": 0.001,
            "analytical_p": {"p_newey_west": 0.002},
            "bh_q_primary": None,
            "bh_q_exploratory": 0.04,
            "robustness_gate": {
                "pillars": {
                    "R1_random_entry_mc": {"beat_rate_unbiased": 0.95, "beat_rate_same_side": 0.93},
                    "R3_top5_outlier_trim": {"trimmed_winners_pf": 1.25},
                }
            },
            "timing_permutation": {"p_value": 0.01},
            "crisis_stress_2018_2024": {"passed": True, "worst_crisis_dd_r": 2.0},
            "research_council": {
                "verdict": "REJECT_KILLED",
                "gates": {
                    "G4_orthogonality": {"corr_all": 0.45, "corr_tail_5pct": 0.55},
                    "G7_pbo_cscv": {"pbo": 0.30},
                },
            },
            "classification": {
                "tier": TIER_2_PERSONAL_VAULT,
                "tier1_resolution_tag": None,
                "failed_core_gates": [],
                "failed_prop_gates": ["PROP_PORT7E_ORTHOGONALITY"],
            },
        }
        for i in range(450)
    ]
    synthetic_full = {
        "generated_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "campaign_run_id": "size-test",
        "git_sha": "abc123",
        "data_sha": "a" * 64,
        "holdout_lock_sha256": "b" * 64,
        "statistical_config": {},
        "duckdb_ledger_summary": {},
        "effective_trials_n_eff": {},
        "campaign_pbo": {},
        "funnel_counts": {"total_evaluated": len(huge_tier2)},
        "family_summaries": {},
        "candidates": huge_tier2,
    }
    compact_out = tmp_path / "compact_funnel.json"
    receipt = write_compact_funnel_json(synthetic_full, compact_out, max_bytes=MAX_TRACKED_FUNNEL_BYTES)
    assert receipt["bytes"] < MAX_TRACKED_FUNNEL_BYTES
    assert compact_out.stat().st_size == receipt["bytes"]

    # Tight budget impossible even after compaction -> raises ValueError fail-closed!
    with pytest.raises(ValueError, match="FUNNEL_SIZE_LIMIT_EXCEEDED"):
        write_compact_funnel_json(synthetic_full, tmp_path / "too_small.json", max_bytes=4096)


def test_05_zero_bare_asserts_in_stage3_and_robustness_gate() -> None:
    """Verify [ARCH-02] ZERO bare `assert` statements in both `stage3_pipeline.py` and `robustness_gate.py`."""
    import ast

    for rel in (
        "tooling/ai-engines/quant_factory/robustness_gate.py",
        "tooling/ai-engines/quant_factory/offensive3/stage3_pipeline.py",
    ):
        path = REPO_ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        assert asserts == [], f"Bare assert found in {rel} at lines {asserts}"
