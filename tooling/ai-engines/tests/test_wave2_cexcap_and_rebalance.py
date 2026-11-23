"""Wave-2 Cycle 4B Tests — Group CEX Counterparty Cap (<= 25%), Rebalance Cadence & Causal Macro-Vol Overlay.

Verifies:
  - Holdout 2025+ SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`), report `< 14 KB`, zero bare `$`.
  - Exact projected-simplex `apply_group_weight_cap`: `w_i >= 0`, `sum(w) == 1.0`, `w_i <= 0.35 + 1e-9`,
    AND `sum(w[CEX]) <= 0.25 + 1e-9`, plus strict infeasibility error check.
  - `NCO_CexCap25` & `ERC_LW_CexCap25` cut `-50%` CEX instant shock to `<= 12.5%` (vs `> 20%` Capped35 & `> 40%` HRP).
  - Rebalance schedule exact cost monotonicity, drift-band monotonicity, and zero-cost daily frictionless parity.
  - Bit-for-bit future-mutation anti-lookahead proof for `simulate_causal_macro_vol_overlay`.
"""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crisis_stress_replay import run_crisis_stress_replay
from quant_factory.data_store import assert_holdout_locked
from quant_factory.portfolio_allocator import (
    ALLOCATORS,
    DEFAULT_CEX_GROUP_CAPS,
    apply_group_weight_cap,
    run_allocation_study,
    weights_erc_lw_cexcap25,
    weights_nco_cexcap25,
)
from quant_factory.regime_allocation_optimizer import (
    get_sleeve_cost_vector,
    simulate_causal_macro_vol_overlay,
    simulate_rebalance_schedule,
)


def _count_bare_dollar_pairs(md_text: str) -> int:
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


def test_cycle4b_report_exists_holdout_sealed_and_under_14kb():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    rp = ROOT / "planning/research/QUANT-POD-V2-NCO-CEXCAP-AND-REBALANCE-20261124.md"
    assert rp.exists(), f"Missing Cycle 4B report: {rp}"
    assert rp.stat().st_size < 14_336, f"Report {rp.stat().st_size} B exceeds 14 KB target!"
    txt = rp.read_text(encoding="utf-8")
    assert "holdout_rows_analysed: 0" in txt
    assert "order_send_count: 0" in txt
    assert _count_bare_dollar_pairs(txt) == 0
    for tok in ("NCO_CexCap25", "ERC_LW_CexCap25", "Monthly_1st", "DriftBand_3pct", "VND"):
        assert tok in txt, f"Missing expected token: {tok}"


def test_group_weight_cap_exact_simplex_single_and_cex_caps():
    assert {"ERC_LW_CexCap25", "NCO_CexCap25"}.issubset(set(ALLOCATORS.keys()))

    sids6 = [
        "S1_PROP_FX_IDX",
        "S2_CRYPTO_SPOT",
        "S3A_FUND_CARRY",
        "S3B_MACRO_ETF",
        "S4_ETF40_MULTIFACTOR",
        "S5_CME_FUTURES_PROP",
    ]
    rng = np.random.default_rng(20261124)
    # Test adversarial corner cases (100% in CEX, 95% in single sleeve, and 25 random Dirichlet vectors)
    test_vectors = [
        np.array([0.0, 0.45, 0.55, 0.0, 0.0, 0.0]),
        np.array([0.01, 0.10, 0.85, 0.02, 0.01, 0.01]),
        np.array([0.90, 0.02, 0.02, 0.02, 0.02, 0.02]),
        *[rng.dirichlet(np.ones(6)) for _ in range(25)],
    ]
    for raw_w in test_vectors:
        w = apply_group_weight_cap(raw_w, sids6, group_caps=DEFAULT_CEX_GROUP_CAPS, single_cap=0.35, strict=True)
        assert np.all(np.isfinite(w))
        assert float(np.min(w)) >= -1e-12
        assert abs(float(np.sum(w)) - 1.0) <= 1e-9
        assert float(np.max(w)) <= 0.35 + 1e-9
        cex_sum = float(w[1] + w[2])
        assert cex_sum <= 0.25 + 1e-9

    # Strict infeasibility check on 4 sleeves (2 CEX capped at 0.25 + 2 free capped at 0.35 = 0.95 < 1.0)
    sids4 = sids6[:4]
    with pytest.raises(ValueError, match="Infeasible"):
        apply_group_weight_cap(np.array([0.1, 0.4, 0.4, 0.1]), sids4, single_cap=0.35, strict=True)
    # Non-strict mode keeps hard CEX <= 0.25 while minimally relaxing non-CEX single cap to stay on simplex
    w4 = apply_group_weight_cap(np.array([0.1, 0.4, 0.4, 0.1]), sids4, single_cap=0.35, strict=False)
    assert abs(float(np.sum(w4)) - 1.0) <= 1e-9
    assert float(w4[1] + w4[2]) <= 0.25 + 1e-9

    # Verify allocator wrappers on synthetic 6-sleeve returns
    mat6 = rng.normal(0.0003, 0.006, size=(500, 6))
    mat6[:, 2] *= 0.20  # low-vol carry sleeve that unconstrained NCO/ERC overweights heavily
    for fn in (weights_nco_cexcap25, weights_erc_lw_cexcap25):
        w = fn(mat6, sleeve_ids=sids6)
        assert abs(float(np.sum(w)) - 1.0) <= 1e-9
        assert float(np.max(w)) <= 0.35 + 1e-9
        assert float(w[1] + w[2]) <= 0.25 + 1e-9


def test_cexcap25_cuts_cex_default_shock_and_runs_in_allocation_study():
    study = run_allocation_study(n_stress_paths=300, seed=77)
    assert study["holdout_rows_analysed"] == 0
    assert {"NCO_CexCap25", "ERC_LW_CexCap25"}.issubset(set(study["methods"].keys()))

    cr = run_crisis_stress_replay(n_crunch_paths=300, seed=77)
    for aname in ("NCO_CexCap25", "ERC_LW_CexCap25"):
        s3 = cr["scenario3_cex_haircut"][aname]
        assert s3["cex_exposed_weight_pct"] <= 25.01
        assert s3["haircut_50_instant_loss_pct"] <= 12.51
        assert s3["haircut_50_plus_p99_day_pct"] < cr["scenario3_cex_haircut"]["NCO_Capped35"]["haircut_50_plus_p99_day_pct"]
        assert s3["haircut_50_plus_p99_day_pct"] < cr["scenario3_cex_haircut"]["HRP"]["haircut_50_plus_p99_day_pct"]


def _make_biz_dates(n: int) -> list[str]:
    out = []
    d = date(2020, 1, 2)
    while len(out) < n:
        if d.weekday() < 5:
            out.append(d.isoformat())
        d += timedelta(days=1)
    return out


def test_rebalance_schedule_cost_monotonicity_and_zero_cost_parity():
    rng = np.random.default_rng(101)
    n = 500
    dates = _make_biz_dates(n)
    sids = ["S1_PROP_FX_IDX", "S2_CRYPTO_SPOT", "S3A_FUND_CARRY", "S3B_MACRO_ETF", "S4_ETF40_MULTIFACTOR", "S5_CME_FUTURES_PROP"]
    mat = rng.normal(0.0003, 0.012, size=(n, 6))
    w_tgt = np.array([0.22, 0.08, 0.17, 0.16, 0.12, 0.25], dtype=np.float64)
    c0 = np.zeros(6, dtype=np.float64)
    c1 = get_sleeve_cost_vector(sids, cost_mult=1.0)
    c2 = get_sleeve_cost_vector(sids, cost_mult=2.0)

    # Zero-cost Daily MUST match frictionless `mat @ w_tgt` bit-for-bit
    d0 = simulate_rebalance_schedule(mat, dates, w_tgt, c0, schedule="Daily")
    assert float(np.max(np.abs(d0["net_returns"] - (mat @ w_tgt)))) < 1e-12
    assert d0["cost_drag_bps_yr"] == 0.0

    # Strict cost monotonicity: Daily > Weekly > Monthly > Quarterly in rebalance count & cost drag
    d1 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="Daily")
    d2 = simulate_rebalance_schedule(mat, dates, w_tgt, c2, schedule="Daily")
    w1 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="Weekly_Mon")
    m1 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="Monthly_1st")
    q1 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="Quarterly")
    b3 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="DriftBand_3pct", drift_band=0.03)
    b5 = simulate_rebalance_schedule(mat, dates, w_tgt, c1, schedule="DriftBand_5pct", drift_band=0.05)

    assert d1["rebalance_count"] > w1["rebalance_count"] > m1["rebalance_count"] > q1["rebalance_count"] > 0
    assert d1["cost_drag_bps_yr"] > w1["cost_drag_bps_yr"] > m1["cost_drag_bps_yr"] > q1["cost_drag_bps_yr"] >= 0.0
    assert abs(d2["cost_drag_bps_yr"] - 2.0 * d1["cost_drag_bps_yr"]) < 0.05
    assert float(np.sum(d2["net_returns"])) < float(np.sum(d1["net_returns"])) < float(np.sum(d0["net_returns"]))
    assert b5["rebalance_count"] <= b3["rebalance_count"]


def test_causal_macro_vol_overlay_strict_future_mutation_zero_lookahead():
    """Mutating `mat[cut:]` MUST produce EXACT 0.0 change in all earlier overlay returns and risk-off flags."""
    rng = np.random.default_rng(2026)
    n = 450
    dates = _make_biz_dates(n)
    sids = ["S1_PROP_FX_IDX", "S2_CRYPTO_SPOT", "S3A_FUND_CARRY", "S3B_MACRO_ETF", "S4_ETF40_MULTIFACTOR", "S5_CME_FUTURES_PROP"]
    mat = rng.normal(0.0003, 0.008, size=(n, 6))
    # Inject a pre-cut drawdown shock around days 120..145 so risk-off genuinely triggers before `cut`!
    mat[120:145, :] -= 0.008
    w_tgt = np.array([0.22, 0.08, 0.17, 0.16, 0.12, 0.25], dtype=np.float64)
    c1 = get_sleeve_cost_vector(sids, cost_mult=1.0)

    cut = 300
    mat_mut = mat.copy()
    mat_mut[cut:, :] = -0.15  # catastrophic future crash

    for mode in ("TBILL_CASH_0PCT", "TBILL50_S3B50"):
        ov_clean = simulate_causal_macro_vol_overlay(mat, dates, sids, w_tgt, c1, defensive_mode=mode)
        ov_mut = simulate_causal_macro_vol_overlay(mat_mut, dates, sids, w_tgt, c1, defensive_mode=mode)
        assert int(np.sum(ov_clean["risk_off_flags"][:cut])) > 0, f"Expected pre-cut risk-off trigger for {mode}"
        assert ov_clean["avg_cash_pct"] > 0.0
        assert np.array_equal(ov_clean["risk_off_flags"][:cut], ov_mut["risk_off_flags"][:cut]), f"Look-ahead flag leak in {mode}!"
        assert np.array_equal(ov_clean["net_returns"][:cut], ov_mut["net_returns"][:cut]), f"Look-ahead return leak in {mode}!"
