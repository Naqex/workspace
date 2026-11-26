"""Wave 2 Cycle 3B Tests — Multi-Account Simultaneous Prop Scaling Optimizer & Black-Swan Crisis Stress Replay.

Verifies:
  - Holdout 2025+ SEALED (`holdout_rows_analysed = 0`, `OrderSend = 0`), report `< 900 KB`, zero bare `$`.
  - Multi-prop Numba simulator determinism, budget monotonicity, stagger double-fail reduction,
    and exact 3-bucket `5x`-ticket reserve-cap overflow into Own-Book.
  - Crisis stress replay across all 6 scenarios (Hist 20d/60d, 2022+FTX, CEX -30%/-50% haircut,
    Corr=0.85 Crunch, 3x Slippage, and exact %, USD, VND currency matrix aligned to `PROFILE.md`).
"""

from __future__ import annotations

from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crisis_stress_replay import (
    FOCUS_ALLOCATORS,
    _profile_comfort_tag,
    run_crisis_stress_replay,
)
from quant_factory.data_store import assert_holdout_locked
from quant_factory.multi_prop_portfolio_sim import (
    USD_VND_RATE,
    _pack_slots,
    _simulate_multi_slot_prop_numba,
    run_multi_prop_scaling_study,
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


def test_cycle3b_report_exists_holdout_sealed_and_clean_prose():
    lock_sha = assert_holdout_locked()
    assert len(lock_sha) == 64

    rp = ROOT / "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
    assert rp.exists(), f"Missing Cycle 3B report: {rp}"
    assert rp.stat().st_size < 900_000
    txt = rp.read_text(encoding="utf-8")
    assert "holdout_rows_analysed: 0" in txt
    assert "order_send_count: 0" in txt
    assert _count_bare_dollar_pairs(txt) == 0
    for token in ("25,500 VND", "10k USD", "50k USD", "200k USD", "NCO_Capped35", "ERC_LW_Capped35"):
        assert token in txt, f"Missing expected section/token in report: {token}"


@pytest.mark.local_cache
def test_multi_prop_sim_determinism_stagger_and_budget_invariants():
    r1 = run_multi_prop_scaling_study(n_paths=400, horizon_days=504, seed=42)
    r2 = run_multi_prop_scaling_study(n_paths=400, horizon_days=504, seed=42)
    assert r1["holdout_rows_analysed"] == 0
    assert r1["order_send_count"] == 0
    assert r1["budget_matrix"] == r2["budget_matrix"]
    assert r1["crossover_matrix"] == r2["crossover_matrix"]

    def _find(bgt: float, arch: str, prof: str) -> dict:
        return next(
            row for row in r1["budget_matrix"]
            if row["budget_usd"] == bgt and row["architecture"] == arch and row["profile"] == prof
        )

    # Single-slot architectures MUST have 0.0% simultaneous double-fail
    for bgt in (500.0, 1500.0, 3000.0):
        assert _find(bgt, "SINGLE_FTMO_SWING", "P1_Balanced_3to6m")["simultaneous_dbl_fail_pct"] == 0.0
        assert _find(bgt, "SINGLE_THE5ERS_HS", "P1_Sprint_1to3m")["simultaneous_dbl_fail_pct"] == 0.0

    # Higher fee budget cannot increase wipeout probability on identical architecture
    w_500 = _find(500.0, "DUAL_2FIRM_SYNC", "P1_Sprint_1to3m")["wipeout_prob_pct"]
    w_3000 = _find(3000.0, "DUAL_2FIRM_SYNC", "P1_Sprint_1to3m")["wipeout_prob_pct"]
    assert w_3000 <= w_500

    # Staggered entry (+42d) reduces simultaneous double-fail vs synchronized t=0 start
    dbl_sync = _find(1500.0, "DUAL_2FIRM_SYNC", "P1_Sprint_1to3m")["simultaneous_dbl_fail_pct"]
    dbl_stag = _find(1500.0, "DUAL_2FIRM_STAGGER_42D", "P1_Sprint_1to3m")["simultaneous_dbl_fail_pct"]
    assert dbl_stag < dbl_sync

    # P1_Sprint under tight 500 USD budget carries >= wipeout risk than P1_Balanced
    w_500_bal = _find(500.0, "DUAL_2FIRM_SYNC", "P1_Balanced_3to6m")["wipeout_prob_pct"]
    assert w_500 >= w_500_bal

    # Non-raiding reserve-cap invariant: idle initial fee budget above 5x cap MUST NOT leak into Own-Book!
    t5_1500 = _find(1500.0, "SINGLE_THE5ERS_HS", "P1_Balanced_3to6m")
    t5_3000 = _find(3000.0, "SINGLE_THE5ERS_HS", "P1_Balanced_3to6m")
    assert abs(t5_1500["med_own_book_60m_usd"] - t5_3000["med_own_book_60m_usd"]) < 1e-3
    assert abs(t5_1500["ev_per_usd_fee_24m"] - t5_3000["ev_per_usd_fee_24m"]) < 1e-3


def test_three_bucket_reserve_cap_overflow_exact_math():
    """Verify exact 30/50/20 payout split + 100% overflow into Own-Book once Reserve hits 5x-ticket cap."""
    n_days = 120
    idx = np.arange(n_days, dtype=np.int32).reshape(1, n_days)
    # Deterministic +150 USD/day on 10k nominal (+1.5%/day), zero intraday DD
    nets = np.full(n_days, 150.0, dtype=np.float64)
    dds = np.zeros(n_days, dtype=np.float64)
    flg = np.ones(n_days, dtype=np.int8)
    ob_zero = np.zeros(n_days, dtype=np.float64)

    slot = [{
        "book_id": 0,
        "cap": 10000.0,
        "fee": 168.0,
        "refund_ratio": 1.0,
        "refund_is_hub": 0,
        "p1_target": 0.10,
        "p2_target": 0.05,
        "daily_lim": 0.05,
        "static_lim": 0.10,
        "min_days": 4,
        "min_prof_day": 0.0,
        "split": 0.80,
        "payout_cycle": 10,
        "start_day": 0,
        "retry_disc": 1.0,
        "can_scale_up": 0,
    }]
    packed = _pack_slots(slot)
    reserve_cap = 5.0 * 168.0  # 840 USD cap; start at 1008 -> after paying 168 fee, reserve == 840 (AT CAP!)

    (
        wiped, sustain, dbl_fail, _w24, ob24, ob60, pay24, fee24, *_rest
    ) = _simulate_multi_slot_prop_numba(
        idx,
        nets, dds, flg, nets, dds, flg, nets, dds, flg,
        nets, dds, flg, nets, dds, flg, nets, dds, flg,
        ob_zero,
        *packed,
        1.0, 1.0, 1.0,
        0.08, 1.0, 0.09, 1.0, 0.04,
        0.08, 1.0, 0.09, 1.0, 0.04,
        1008.0,  # 1008 - 168 = 840 == reserve_cap -> EVERY payout's 30% reserve share must overflow into Own-Book!
        0.0,
        0.30,
        0.50,
        0.20,
        reserve_cap,
        False,
    )
    assert int(wiped[0]) == 0
    assert int(sustain[0]) == 1
    assert int(dbl_fail[0]) == 0
    assert abs(float(fee24[0]) - 168.0) < 1e-6
    assert float(pay24[0]) > 5000.0
    # Because reserve is already at cap (840 USD), Own-Book MUST receive 50% + 30% overflow = EXACTLY 80% of all net payouts!
    assert abs(float(ob60[0]) - 0.80 * float(pay24[0])) < 1e-4


@pytest.mark.local_cache
def test_crisis_stress_replay_all_6_scenarios_and_currency_math():
    c1 = run_crisis_stress_replay(n_crunch_paths=400, seed=77)
    c2 = run_crisis_stress_replay(n_crunch_paths=400, seed=77)
    assert c1["holdout_rows_analysed"] == 0
    assert c1["order_send_count"] == 0
    assert 4 <= c1["n_sleeves"] <= 8
    assert c1["scenario4_corr085_crunch"] == c2["scenario4_corr085_crunch"]
    assert c1["scenario6_currency_impact"] == c2["scenario6_currency_impact"]

    for aname in FOCUS_ALLOCATORS:
        s1 = c1["scenario1_historical_windows"][aname]
        assert s1["w60"]["max_dd_pct"] >= s1["w20"]["max_dd_pct"] >= 0.0

        s2 = c1["scenario2_2022_rate_ftx"][aname]
        assert s2["max_dd_pct"] > 0.0

        s3 = c1["scenario3_cex_haircut"][aname]
        assert abs(s3["haircut_50_instant_loss_pct"] - 0.50 * s3["cex_exposed_weight_pct"]) <= 0.15
        assert s3["haircut_50_instant_loss_pct"] >= s3["haircut_30_instant_loss_pct"]

        s4 = c1["scenario4_corr085_crunch"][aname]
        assert s4["stress_dd_p99_pct"] >= s4["stress_dd_p95_pct"] >= 0.0
        assert s4["worst_1d_p99_pct"] > 0.0

        s5 = c1["scenario5_slippage_3x"][aname]
        assert s5["stress3x_cagr_pct"] <= s5["base_cagr_pct"] + 0.05

    # Counterparty cap effectiveness: capped allocators suffer strictly less CEX default shock than uncapped HRP
    hrp_hit = c1["scenario3_cex_haircut"]["HRP"]["haircut_50_instant_loss_pct"]
    nco_hit = c1["scenario3_cex_haircut"]["NCO_Capped35"]["haircut_50_instant_loss_pct"]
    assert nco_hit < hrp_hit

    # Exact USD & VND arithmetic + PROFILE.md traffic lights
    for row in c1["scenario6_currency_impact"]:
        dd = row["worst_case_dd_pct"]
        for tier in (10_000, 50_000, 200_000):
            t_obj = row["tiers"][tier]
            expected_usd = round(tier * (dd / 100.0), 0)
            expected_vnd_m = round(expected_usd * USD_VND_RATE / 1e6, 1)
            assert abs(t_obj["loss_usd"] - expected_usd) <= 1.0
            assert abs(t_obj["loss_vnd_m"] - expected_vnd_m) <= 0.11
            assert t_obj["profile_status"] == _profile_comfort_tag(dd, float(tier))
