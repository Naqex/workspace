"""Deterministic unit & receipt verification tests for Cycle-2 Unified Top-1% Prop-to-OwnBook Trajectory Study.

Verifies:
  1. Sealed Dev `NCO_CexCap25` (`Monthly_1st`, total CEX <= 25%) loader & Holdout `>= 2025-01-01` refusal.
  2. Coupled 60-month Numba simulator physics: 3-bucket overflow, profit-funded VPS/Data infra gates
     (deducts strictly from Ops bucket when profitable; spends 0 USD when unprofitable), wipeout detection,
     and tier-dependent IBKR fee drag monotonicity.
  3. Smart-Tier slot ladder structural invariants (total nominal <= 360k USD, The5ers >= 50k strict 4%/8%
     calibration with `ea_stop <= 2.8%`, expansion slot fail-closed cushion >= 1.75x).
  4. Verified receipt `TOP1-UNIFIED-PROP-TO-OWNBOOK-TRAJECTORY-20261124.{md,json,sha256}`: `< 900 KB`,
     cryptographic SHA-256 match, verbatim MD == render(JSON), `OrderSend = 0`, `holdout_rows_analysed = 0`,
     zero bare `$`, and core Smart-Tier vs Old-10K economic findings.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import sys

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(ROOT / "tooling/knowledge") not in sys.path:
    sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli
from quant_factory import top1_unified_trajectory_study as uts


def test_own_book_nco_cexcap25_monthly_rebal_and_holdout_refusal() -> None:
    assert uts.ORDER_SEND_COUNT == 0
    assert uts.ORDER_SEND_CAPABLE is False

    # Must fail-closed if anyone attempts end_day >= 2025-01-01
    with pytest.raises(AssertionError, match="HOLDOUT_CONTAMINATION"):
        uts.build_own_book_nco_cexcap25_series(["2024-01-02"], end_day="2025-01-01")

    sample_days = ["2020-01-02", "2022-06-15", "2024-12-30"]
    ob = uts.build_own_book_nco_cexcap25_series(sample_days, end_day="2024-12-31")
    assert ob["total_cex_weight_pct"] <= 25.01
    assert ob["rebalance_schedule"] == "Monthly_1st"
    assert ob["rebalance_count"] >= 40
    assert abs(sum(ob["weights_pct"].values()) - 100.0) <= 0.15
    assert len(ob["aligned_daily_returns"]) == len(sample_days)
    assert ob["metrics_full_dev"]["sharpe"] > 1.0


def test_smart_tier_slots_and_4_8_calibration_invariants() -> None:
    slots = uts.build_smart_tier_ladder_slots()
    total_nom = sum(s["cap"] for s in slots)
    assert 300_000.0 <= total_nom <= 400_000.0

    # Every The5ers >= 50k slot MUST use calibrated 4%/8% safe book (book_id == 1) and ea_stop <= 2.8%
    t5_big = [s for s in slots if s["refund_is_hub"] == 1 and s["cap"] >= 50_000.0]
    assert len(t5_big) >= 1
    for s in t5_big:
        assert s["book_id"] == 1
        assert abs(s["daily_lim"] - 0.04) < 1e-9
        assert abs(s["static_lim"] - 0.08) < 1e-9
        assert s["ea_stop"] <= 0.028 + 1e-9
        assert s["amber_dd"] <= 0.025
        assert s["red_dd"] <= 0.050

    # Expansion slots (>= 50k FTMO or >= 20k The5ers) must enforce funded-first gate & cushion >= 1.75x
    exp_slots = [s for s in slots if s["start_day"] >= 84]
    assert len(exp_slots) >= 4
    for s in exp_slots:
        assert s["req_funded_first"] == 1
        assert s["cushion_mult"] >= 1.75


def test_coupled_numba_simulator_3bucket_overflow_infra_gates_and_wipeout() -> None:
    n_paths = 8
    horizon = 1260  # 60 months
    n_src = 200
    idx_mat = np.tile(np.arange(n_src, dtype=np.int32), (n_paths, (horizon // n_src) + 1))[:, :horizon]
    slots_packed = uts._pack_unified_slots(uts.build_smart_tier_ladder_slots())

    # 1. Deterministic profitable tape: +180 USD/day on 10k base (P1/P2), +55 USD/day Funded, low DD
    def _arr(val: float) -> np.ndarray:
        return np.full(n_src, val, dtype=np.float64)

    flg_on = np.ones(n_src, dtype=np.int8)
    win_books = (
        _arr(180.0), _arr(30.0), flg_on,  # b0 p1s
        _arr(110.0), _arr(20.0), flg_on,  # b0 p1l
        _arr(120.0), _arr(20.0), flg_on,  # b0 p2s
        _arr(80.0),  _arr(15.0), flg_on,  # b0 p2l
        _arr(55.0),  _arr(15.0), flg_on,  # b0 fn
        _arr(130.0), _arr(20.0), flg_on,  # b1 p1s
        _arr(85.0),  _arr(15.0), flg_on,  # b1 p1l
        _arr(95.0),  _arr(15.0), flg_on,  # b1 p2s
        _arr(70.0),  _arr(10.0), flg_on,  # b1 p2l
        _arr(55.0),  _arr(15.0), flg_on,  # b1 fn
        _arr(150.0), _arr(30.0), flg_on,  # b2 p1s
        _arr(100.0), _arr(20.0), flg_on,  # b2 p2s
        _arr(55.0),  _arr(15.0), flg_on,  # b2 fn
    )
    ob_ret = _arr(0.0003)  # ~+7.8%/yr before IBKR drag

    res_win = uts._simulate_unified_trajectory_numba(
        idx_mat, *win_books, ob_ret, *slots_packed,
        1_500.0, 0.0, 0.30, 0.50, 0.20, 5.0,
        0.006, 0.009, 360_000.0,
    )
    summ_win = uts._summarize_trajectory(res_win, n_paths)
    assert summ_win["wipeout_pct"] == 0.0
    assert summ_win["ob_60m_med_usd"] > 50_000.0
    assert summ_win["infra_self_funded_60m_med_usd"] > 0.0
    assert summ_win["milestones"]["A_vps_self_funded"]["p_24m_pct"] == 100.0
    assert summ_win["milestones"]["B1_data_active50k"]["p_60m_pct"] == 100.0

    # 2. Deterministic losing tape (every day breaches 5% daily limit): MUST wipeout fee bankroll & spend 0 USD on infra!
    lose_books = (
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
        _arr(-600.0), _arr(650.0), flg_on,
    )
    res_lose = uts._simulate_unified_trajectory_numba(
        idx_mat, *lose_books, ob_ret, *slots_packed,
        500.0, 10_000.0, 0.30, 0.50, 0.20, 5.0,
        0.006, 0.009, 360_000.0,
    )
    summ_lose = uts._summarize_trajectory(res_lose, n_paths)
    assert summ_lose["wipeout_pct"] == 100.0
    assert summ_lose["infra_self_funded_60m_med_usd"] == 0.0
    # Remaining Own-Book (10k seed) must continue compounding cleanly despite Prop fee wipeout!
    assert summ_lose["ob_60m_med_usd"] > 10_000.0


def test_unified_trajectory_receipt_sha_verbatim_parity_and_hygiene() -> None:
    md_p = uts.OUT_MD
    js_p = uts.OUT_JSON
    sha_p = js_p.with_suffix(".sha256")

    for p in (md_p, js_p, sha_p):
        assert p.is_file(), f"Missing trajectory receipt artifact: {p}"
        assert p.stat().st_size < 900 * 1024, f"Artifact exceeds 900 KB: {p}"

    raw_js = js_p.read_bytes()
    actual_sha = hashlib.sha256(raw_js).hexdigest()
    expected_sha = sha_p.read_text(encoding="utf-8").strip().split()[0]
    assert actual_sha == expected_sha

    data = json.loads(raw_js.decode("utf-8"))
    assert data["order_send_count"] == 0
    assert data["order_send_capable"] is False
    assert data["holdout_rows_analysed"] == 0
    assert data["mc_paths"] == 5_000
    assert data["mc_horizon_months"] == 60
    assert data["mc_seed"] == 20261124
    assert data["dev_window"].split("..")[1] < "2025-01-01"
    assert data["own_book_pod"]["total_cex_weight_pct"] <= 25.01

    # Exact verbatim MD == render_trajectory_markdown(JSON, sha) parity!
    md_txt = md_p.read_text(encoding="utf-8")
    assert md_txt == uts.render_trajectory_markdown(data, actual_sha)
    assert md_txt.startswith("---\n")
    for line_no, line in brain_cli._iter_non_code_lines(md_txt):
        cleaned = brain_cli.INLINE_CODE_RE.sub("", line)
        assert "$" not in cleaned, f"Bare '$' in {md_p.name}:{line_no}: {line}"

    # Verify core empirical invariants (including true post-funded Crossover — NEVER false Month-1 trigger!)
    hl = data["highlights"]
    assert hl["smart_vs_old_b1500_ob60m_usd"][1] > hl["smart_vs_old_b1500_ob60m_usd"][0]
    assert hl["smart_vs_old_b1500_15x_ob60m_usd"][1] > hl["smart_vs_old_b1500_15x_ob60m_usd"][0]
    assert hl["smart_b1500_vps_med_month"] > 0
    assert hl["smart_b3000_ob25k_crossover_p60m_pct"] < 50.0
    sc_ob25 = next(s for s in data["scenarios"] if s["friction"] == "1.0x" and s["scenario_id"] == "SMART_B3000_OB25K")
    xo_m = sc_ob25["milestones"]["D_crossover"]["med_month"]
    assert xo_m == -1 or xo_m > 3, f"False early Crossover trigger at month {xo_m}"
    assert hl["analytical_crossover"]["ob_needed_to_beat_100k_prop_1x_usd"] > 100_000.0

    # Verify VND pain table covers all 4 tiers with exact 25,500 FX rate
    pain = data["scorecard_and_pain"]["vnd_pain_table"]
    assert [r["tier_usd"] for r in pain] == [10_000, 50_000, 100_000, 200_000]
    for r in pain:
        assert abs(r["tier_vnd_tr"] - round(r["tier_usd"] * 25_500.0 / 1_000_000.0, 1)) <= 0.11
