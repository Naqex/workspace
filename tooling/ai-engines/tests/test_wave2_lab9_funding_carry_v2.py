"""Wave-2 Cycle 4F Tests — Lab #9 Multi-Coin Diversified Perpetual Funding Carry v2 & EVT Tail Audit.

Verifies:
  1. Bit-for-bit future-mutation zero-lookahead proof across ALL 8 Lab #9 weight builders.
  2. Exact 2.0x (<= 50% equity) & 2.5x (<= 40% equity) CEX margin-buffer leverage caps and
     <= 20% / <= 25% single-coin concentration caps.
  3. Zero pre-listing NaN allocation invariant across all 8 builders.
  4. Hysteresis state-retention & 2x friction / Maker-vs-Taker monotonicity.
  5. Incumbent `sleeve3a_funding_carry.json` untouched SHA-256, exact Cycle-3 EVT xi parity
     (0.0718), and Holdout 2025+ FX seal (`holdout_rows_analysed == 0`).
  6. Report hygiene (YAML frontmatter, < 14 KB, 0 bare `$`, 0 broken links) and 100% verbatim
     8-of-8 JSON-to-Markdown table parity.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import sys

import numpy as np
import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.funding_rate_carry import SLEEVE3A_RETURNS_PATH
from quant_factory.lab9_multicoin_funding_carry_v2 import (
    BASIS_CROSS_SLIP_1X_BPS,
    BASIS_CROSS_SLIP_2X_BPS,
    LAB9_SPEC_ORDER,
    LAB9_SUMMARY_PATH,
    MAKER_PAIR_1X_BPS,
    TAKER_10_LEG_PAIR_1X_BPS,
    TAKER_10_LEG_PAIR_2X_BPS,
    TAKER_15_LEG_PAIR_1X_BPS,
    build_lab9_strategies,
    load_lab9_funding_panel,
    simulate_lab9_carry,
)

LAB9_MD_PATH = ROOT / "planning/research/LAB9-MULTICOIN-FUNDING-CARRY-V2-20261124.md"
HOLDOUT_LOCK_PATH = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"


def _make_synthetic_panel(n_t: int = 240, n_k: int = 12, seed: int = 20261124) -> dict:
    """Create deterministic synthetic 20-perp-like funding/price panel with staggered listings."""
    rng = np.random.default_rng(seed)
    dates = [f"2023-{(i // 28) % 12 + 1:02d}-{(i % 28) + 1:02d}" for i in range(n_t)]
    syms = ["BTCUSDT", "ETHUSDT"] + [f"ALT{i}USDT" for i in range(2, n_k)]

    fund = rng.normal(0.00035, 0.00025, size=(n_t, n_k))
    # Inject a brief negative funding shock around t=140..146 to exercise hysteresis & regime brake
    fund[140:147, :] = -0.00040
    spot = np.zeros((n_t, n_k), dtype=np.float64)
    perp = np.zeros((n_t, n_k), dtype=np.float64)
    spot[0, :] = 100.0
    perp[0, :] = 100.05
    for t in range(1, n_t):
        ret = rng.normal(0.0005, 0.03, size=n_k)
        spot[t] = spot[t - 1] * np.exp(ret)
        basis_noise = rng.normal(0.0, 0.0008, size=n_k)
        perp[t] = spot[t] * (1.0 + basis_noise)
    # Inject a BTC bear phase in second half so BTC < EMA300 triggers F9_TOP5_BEAR_GUARD
    spot[160:, 0] *= 0.65
    perp[160:, 0] *= 0.65
    spot_h = spot * 1.04
    perp_h = perp * 1.045
    pos_8h = np.where(fund > 0.0, 3, 0).astype(np.int32)
    tot_8h = np.full((n_t, n_k), 3, dtype=np.int32)
    qv = rng.uniform(5e7, 5e8, size=(n_t, n_k))

    # Staggered listing: last 2 coins do NOT exist before day 80 (NaN + tot_8h=0)
    for j in (n_k - 2, n_k - 1):
        fund[:80, j] = np.nan
        spot[:80, j] = np.nan
        perp[:80, j] = np.nan
        spot_h[:80, j] = np.nan
        perp_h[:80, j] = np.nan
        qv[:80, j] = np.nan
        pos_8h[:80, j] = 0
        tot_8h[:80, j] = 0

    return {
        "dates": dates,
        "symbols": syms,
        "funding_daily": fund,
        "spot_close": spot,
        "perp_close": perp,
        "spot_high": spot_h,
        "perp_high": perp_h,
        "pos_8h_cnt": pos_8h,
        "tot_8h_cnt": tot_8h,
        "perp_quote_vol": qv,
    }


def test_lab9_zero_lookahead_future_mutation_all_8_specs():
    """Bit-for-bit proof: mutating ALL market inputs after `cut` produces identical weights on `0..cut`."""
    base_panel = _make_synthetic_panel(n_t=220, n_k=12, seed=42)
    cut = 130

    mut_panel = {
        k: (v.copy() if isinstance(v, np.ndarray) else list(v))
        for k, v in base_panel.items()
    }
    # Aggressively scramble ALL future arrays strictly after `cut`
    mut_panel["funding_daily"][cut + 1 :, :] = -0.025
    mut_panel["spot_close"][cut + 1 :, :] *= 4.7
    mut_panel["perp_close"][cut + 1 :, :] *= 0.25
    mut_panel["spot_high"][cut + 1 :, :] *= 6.0
    mut_panel["perp_high"][cut + 1 :, :] *= 5.0
    mut_panel["pos_8h_cnt"][cut + 1 :, :] = 0
    mut_panel["tot_8h_cnt"][cut + 1 :, :] = 1
    mut_panel["perp_quote_vol"][cut + 1 :, :] = 1.0

    s_base = build_lab9_strategies(base_panel)
    s_mut = build_lab9_strategies(mut_panel)

    assert tuple(s_base.keys()) == LAB9_SPEC_ORDER
    for sid in LAB9_SPEC_ORDER:
        w0 = s_base[sid]["weights"][: cut + 1]
        w1 = s_mut[sid]["weights"][: cut + 1]
        assert np.array_equal(w0, w1), f"LOOKAHEAD_DETECTED in {sid}: prefix weights changed after future mutation!"


def test_lab9_margin_buffer_leverage_caps_and_zero_prelisting():
    """Verify exact 2.0x/2.5x equity caps, single-coin caps, and zero pre-listing allocation."""
    panel = _make_synthetic_panel(n_t=220, n_k=12, seed=99)
    strats = build_lab9_strategies(panel)

    for sid in LAB9_SPEC_ORDER:
        cfg = strats[sid]
        w = cfg["weights"]
        buf = float(cfg["equity_buffer_mult"])
        max_single = float(cfg["max_single_notional_cap"])

        # Zero pre-listing allocation (coins 10 & 11 unlisted on days 0..79)
        assert float(np.max(np.abs(w[:80, 10:]))) == 0.0, f"Pre-listing allocation leak in {sid}"

        # Carry notional budget sum <= 1.0 and single-coin cap respected on every day
        assert float(np.max(w)) <= max_single + 1e-12, f"{sid} breached single-coin cap {max_single}"
        assert float(np.max(w.sum(axis=1))) <= 1.0 + 1e-12, f"{sid} breached 1.0 carry budget"
        assert float(np.min(w)) >= 0.0, f"{sid} produced negative carry weight"

        # Simulator enforces exact equity buffer notional cap (2.0x => <= 0.50, 2.5x => <= 0.40)
        sim = simulate_lab9_carry(panel, w, equity_buffer_mult=buf)
        held = sim["held_notional"]
        expected_cap = 1.0 / buf
        assert sim["notional_cap"] == pytest.approx(expected_cap, abs=1e-12)
        assert float(np.max(held.sum(axis=1))) <= expected_cap + 1e-12, f"{sid} breached {buf}x buffer equity cap"
        assert float(np.max(held)) <= max_single * expected_cap + 1e-12, f"{sid} breached single-coin equity cap"
        # Day 0 held is strictly 0 (causal t -> t+1)
        assert float(np.max(np.abs(held[0]))) == 0.0

    # Specific 2.5x conservative check on F9_TOP10_TIER1_CAP20 (<= 40% gross equity, <= 8% per coin!)
    cfg10 = strats["F9_TOP10_TIER1_CAP20"]
    assert cfg10["equity_buffer_mult"] == 2.5
    assert cfg10["max_single_notional_cap"] == 0.20
    sim10 = simulate_lab9_carry(panel, cfg10["weights"], equity_buffer_mult=2.5)
    assert sim10["perp_margin_ratio"] == pytest.approx(1.5, abs=1e-12)
    assert float(np.max(sim10["held_notional"].sum(axis=1))) <= 0.40 + 1e-12
    assert float(np.max(sim10["held_notional"])) <= 0.08 + 1e-12


def test_lab9_hysteresis_retention_and_friction_monotonicity():
    """Verify hysteresis retains held coins inside deadband & 2x / Taker costs monotonically reduce PnL."""
    # Construct clean 2-coin panel to test BTC+ETH hysteresis deadband (+3% enter / <=0% exit)
    n_t, n_k = 60, 2
    fund = np.zeros((n_t, n_k), dtype=np.float64)
    # Days 0..19: +1.5% ann (inside deadband 0..3% -> must NOT enter from flat!)
    fund[:20, :] = 0.015 / 365.0
    # Days 20..34: +15% ann (above +3% -> MUST enter!)
    fund[20:35, :] = 0.15 / 365.0
    # Days 35..49: +1.5% ann (back inside deadband -> MUST STAY HELD due to hysteresis!)
    fund[35:50, :] = 0.015 / 365.0
    # Days 50..59: -5% ann (below 0% -> MUST exit!)
    fund[50:, :] = -0.05 / 365.0

    spot = np.full((n_t, n_k), 100.0, dtype=np.float64)
    perp = np.full((n_t, n_k), 100.0, dtype=np.float64)
    panel = {
        "dates": [f"2024-01-{i+1:02d}" for i in range(n_t)],
        "symbols": ["BTCUSDT", "ETHUSDT"],
        "funding_daily": fund,
        "spot_close": spot,
        "perp_close": perp,
        "spot_high": spot * 1.01,
        "perp_high": perp * 1.01,
        "pos_8h_cnt": np.where(fund > 0, 3, 0).astype(np.int32),
        "tot_8h_cnt": np.full((n_t, n_k), 3, dtype=np.int32),
        "perp_quote_vol": np.full((n_t, n_k), 1e8, dtype=np.float64),
    }

    strats = build_lab9_strategies(panel)
    w_v1 = strats["F9_V1_BTC_ETH_BASE"]["weights"]
    # Before t=20: inside deadband from flat -> strictly 0.0
    assert float(np.max(w_v1[:20])) == 0.0
    # After 7d rolling rises above +3% (by day 27): entered at 0.50 each
    assert w_v1[27, 0] == pytest.approx(0.50)
    # Days 36..49: back at +1.5% ann (deadband) -> RETAINED at 0.50 due to hysteresis!
    assert float(np.min(w_v1[36:50, 0])) == pytest.approx(0.50)
    # By day 57: rolling 7d turns negative -> EXITED to 0.0!
    assert w_v1[57, 0] == pytest.approx(0.0)

    # Friction monotonicity on synthetic multi-coin panel: Maker (6.15/leg) > Taker10 > Taker15 > 2x Taker10
    p2 = _make_synthetic_panel(n_t=180, n_k=10, seed=7)
    w6 = build_lab9_strategies(p2)["F9_TOP6_MAKER_ENTRY"]["weights"]
    s_maker = simulate_lab9_carry(
        p2, w6, equity_buffer_mult=2.0,
        oneway_pair_cost_bps=MAKER_PAIR_1X_BPS, basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS, exit_shock_mult=1.0,
    )
    s_t10 = simulate_lab9_carry(
        p2, w6, equity_buffer_mult=2.0,
        oneway_pair_cost_bps=TAKER_10_LEG_PAIR_1X_BPS, basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS, exit_shock_mult=1.0,
    )
    s_t15 = simulate_lab9_carry(
        p2, w6, equity_buffer_mult=2.0,
        oneway_pair_cost_bps=TAKER_15_LEG_PAIR_1X_BPS, basis_cross_slip_bps=BASIS_CROSS_SLIP_1X_BPS, exit_shock_mult=1.0,
    )
    s_t10_2x = simulate_lab9_carry(
        p2, w6, equity_buffer_mult=2.0,
        oneway_pair_cost_bps=TAKER_10_LEG_PAIR_2X_BPS, basis_cross_slip_bps=BASIS_CROSS_SLIP_2X_BPS, exit_shock_mult=2.0,
    )
    assert float(np.sum(s_maker["net_returns"])) > float(np.sum(s_t10["net_returns"]))
    assert float(np.sum(s_t10["net_returns"])) > float(np.sum(s_t15["net_returns"]))
    assert float(np.sum(s_t10["net_returns"])) > float(np.sum(s_t10_2x["net_returns"]))


def test_lab9_summary_artifacts_evt_parity_and_md_hygiene():
    """Verify summary JSON integrity, untouched S3A v1, Cycle-3 EVT xi=0.0718, and 8-of-8 MD parity."""
    assert LAB9_SUMMARY_PATH.exists(), f"Missing Lab #9 summary JSON: {LAB9_SUMMARY_PATH}"
    assert LAB9_MD_PATH.exists(), f"Missing Lab #9 report MD: {LAB9_MD_PATH}"
    assert HOLDOUT_LOCK_PATH.exists()

    summary = json.loads(LAB9_SUMMARY_PATH.read_text(encoding="utf-8"))
    md_text = LAB9_MD_PATH.read_text(encoding="utf-8")

    # 1. Holdout seal & incumbent sleeve3a_funding_carry.json 100% untouched
    lock_sha = hashlib.sha256(HOLDOUT_LOCK_PATH.read_bytes()).hexdigest()
    assert summary["holdout_rows_analysed"] == 0
    assert summary["holdout_lock_sha256"] == lock_sha
    assert summary["data_source"]["s1_dev_overlap_window"][1] <= "2024-12-31"
    assert summary["incumbent_sleeve3a_json_untouched"] is True
    assert SLEEVE3A_RETURNS_PATH.exists()
    actual_s3a_sha = hashlib.sha256(SLEEVE3A_RETURNS_PATH.read_bytes()).hexdigest()
    assert summary["incumbent_sleeve3a_json_sha256"] == actual_s3a_sha

    # 2. Exact Cycle-3 EVT xi parity on unmodified S3A v1 file (2020-2024 Mon-Fri)
    assert summary["incumbent_s3a_file_evt_monfri_2020_2024"]["evt_xi"] == pytest.approx(0.0718, abs=1e-4)
    assert summary["m_family"] == 8
    assert summary["data_source"]["n_symbols"] == 20

    # 3. Markdown hygiene: YAML frontmatter, < 14 KB, 0 bare `$`, 0 broken relative links
    assert md_text.startswith("---\n"), "Missing YAML frontmatter"
    assert LAB9_MD_PATH.stat().st_size < 14 * 1024, f"Report exceeds 14 KB: {LAB9_MD_PATH.stat().st_size}"
    assert "$" not in md_text, "Bare `$` found in Markdown prose/tables!"

    for _label, target in re.findall(r"\[([^\]]+)\]\(([^)]+)\)", md_text):
        if target.startswith(("http://", "https://", "#")):
            continue
        resolved = (LAB9_MD_PATH.parent / target.split("#")[0]).resolve()
        assert resolved.exists(), f"Broken relative Markdown link: {target} -> {resolved}"

    # 4. Exact 8-of-8 verbatim JSON-to-Markdown table parity
    for sid in LAB9_SPEC_ORDER:
        v = summary["variants"][sid]
        a1 = v["cluster_a_1x"]
        b1 = v["cluster_b_1x"]
        b2 = v["cluster_b_2x"]
        em = v["evt_monfri_2020_2024"]
        ef = v["evt_full_24_7"]
        ms = v["margin_stress"]
        expected_row = (
            f"| `{sid}` | {v['equity_buffer_mult']:.1f}x | {a1['sharpe']:.2f} | "
            f"{b1['cagr_pct']:.2f}% | {b1['sharpe']:.2f} | {b1['max_dd_pct']:.2f}% | "
            f"{b1['calmar']:.2f} | {b1['annual_turnover_x']:.2f}x | {b2['cagr_pct']:.2f}% | "
            f"{b2['sharpe']:.2f} | {v['council_breakeven_mult']:.2f}x | {v['bh_q_b']:.5f} | "
            f"{v['dsr_b']['dsr']:.3f} | {v['corr_vs_s1_cal_b_dev']:.3f} / {v['corr_vs_s1_monfri_b_dev']:.3f} | "
            f"{em['evt_xi']:.4f} | {ef['evt_xi']:.4f} | {em['p99_stress_dd_252d_pct']:.2f}% | "
            f"{ms['isolated_liq_events']} / {ms['cross_liq_events']} | `{v['council_verdict']}` |"
        )
        assert expected_row in md_text, f"Table 1 MD-vs-JSON parity mismatch for {sid}:\nExpected: {expected_row}"

        # Also verify Crisis Stress row verbatim
        cs = v["crisis_stress"]
        expected_cs = (
            f"| `{sid}` | {cs['may2021_crash']['total_ret_pct']:+.2f}% / {cs['may2021_crash']['max_dd_pct']:.2f}% | "
            f"{cs['ftx2022_collapse']['total_ret_pct']:+.2f}% / {cs['ftx2022_collapse']['max_dd_pct']:.2f}% | "
            f"{cs['bear2022_full']['total_ret_pct']:+.2f}% / {cs['bear2022_full']['max_dd_pct']:.2f}% | "
            f"{cs['aug2024_yen_shock']['total_ret_pct']:+.2f}% / {cs['aug2024_yen_shock']['max_dd_pct']:.2f}% | "
            f"{em['worst_day_pct']:.3f}% | {ms['max_single_coin_mark_jump_pct']:.2f}% | "
            f"{ms['max_cross_margin_draw_pct']:.2f}% |"
        )
        assert expected_cs in md_text, f"Crisis Stress MD-vs-JSON mismatch for {sid}:\nExpected: {expected_cs}"


def test_lab9_real_cached_panel_zero_lookahead_and_20_symbols():
    """Verify real 20-perp offline cache loads cleanly with zero pre-listing allocation on real data."""
    panel = load_lab9_funding_panel()
    assert len(panel["symbols"]) == 20
    assert panel["dates"][0] == "2020-01-01"
    assert panel["pos_8h_cnt"].shape == panel["funding_daily"].shape
    assert panel["tot_8h_cnt"].shape == panel["funding_daily"].shape
    assert np.all(panel["pos_8h_cnt"] <= panel["tot_8h_cnt"])

    # Verify zero allocation whenever funding is NaN on real 20-coin panel across ALL 8 strategies
    strats = build_lab9_strategies(panel)
    nan_mask = ~np.isfinite(panel["funding_daily"])
    for sid in LAB9_SPEC_ORDER:
        w = strats[sid]["weights"]
        assert float(np.max(np.abs(w[nan_mask]))) == 0.0, f"Allocated to NaN/unlisted coin in {sid}"
