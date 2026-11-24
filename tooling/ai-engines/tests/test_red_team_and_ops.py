"""Comprehensive deterministic tests for Lane B (M2.1-M2.3 + M5.1-M5.3):
  - Red-Team Adversarial Auditor (cost breakeven linearity, latency, SL, DST, zero survivorship bias)
  - Multi-Firm Dual-P1 Prop EV Frontier (Monte Carlo seed determinism, EV/USD-fee math, PropGuard bounds)
  - Blameless Weekly Postmortem Engine (TCA Bug vs Alpha Decay vs Regime Shift vs Normal Variance)
  - Institutional 2-Role Research Council (Proposer -> Skeptical Critic fail-closed gates)
  - Official Red-News Calendar CSV through 2027 (3-col MQL5 schema, exact DST UTC timestamps)
  - 4-Sleeve Portfolio Allocator (weekend compounding, ERC parity, HRP, 35% counterparty cap)
  - Unified Pod Command Center Dashboard (< 2s generation, HTML + Markdown snapshot integrity)
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys
import tempfile
import time
import unittest

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.data_store import assert_holdout_locked
from quant_factory.pod_dashboard import generate_pod_dashboard, load_upcoming_red_news
from quant_factory.portfolio_allocator import (
    ALLOCATORS,
    align_sleeves_business_days,
    compute_risk_contributions,
    weights_erc,
    weights_erc_capped35,
    weights_hrp_capped35,
)
from quant_factory.postmortem_gen import generate_weekly_postmortem, run_weekly_postmortem
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import (
    decompose_mt5_multiplier,
    evaluate_ev_profile,
    geometric_p95_consec_fails,
    load_firm_variants,
)
from quant_factory.red_team_auditor import (
    classify_dst_regime,
    estimate_trade_base_cost_usd_per_lot,
    transform_tapes_clock_shift,
    transform_tapes_cost_stress,
    transform_tapes_latency_stress,
    transform_tapes_sl_perturbation,
)
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)


def _make_synthetic_tape() -> dict[str, dict]:
    ts0 = 1704200400  # 2024-01-02 13:00 UTC
    stamps = np.array([ts0 + 60 * i for i in range(120)], dtype=np.int64)
    # Opens with -20 USD/lot spread+cost, moves up +30 on bar 1, dips to -85 on bar 40, finishes +180 USD/lot
    marks = np.zeros((120, 4), dtype=np.float64)
    marks[0] = [-20.0, 15.0, -30.0, 10.0]
    marks[1] = [10.0, 25.0, 5.0, 20.0]
    for i in range(2, 120):
        val = 20.0 + (i - 1) * (160.0 / 118.0)
        marks[i] = [val - 2.0, val + 5.0, val - 5.0, val]
    marks[40, 2] = -85.0  # Intraday MAE dip that hits 0.80x SL (-80) but NOT 1.0x SL (-100)
    marks[-1] = [180.0, 180.0, 180.0, 180.0]
    row_win = {
        "day": "2024-01-02",
        "asset": "US100",
        "entry": ts0,
        "exit": ts0 + 119 * 60,
        "at_open": True,
        "reason": "HARD_FLAT",
        "entry_price": 17000.0,
        "stop_risk_with_cost_usd": 100.0,
        "net_usd_per_lot": 180.0,
        "net_R": 1.80,
    }
    # Second trade: fast SL hit after 25 minutes on next day (tests zero survivorship bias in early_flat!)
    ts1 = ts0 + 86400
    stamps_sl = np.array([ts1 + 60 * i for i in range(25)], dtype=np.int64)
    marks_sl = np.zeros((25, 4), dtype=np.float64)
    marks_sl[0] = [-20.0, -5.0, -35.0, -25.0]
    for i in range(1, 24):
        marks_sl[i] = [-30.0, -20.0, -70.0, -50.0]
    marks_sl[-1] = [-80.0, -80.0, -100.0, -100.0]
    row_sl = {
        "day": "2024-01-03",
        "asset": "US100",
        "entry": ts1,
        "exit": ts1 + 25 * 60,
        "at_open": False,
        "reason": "SL_GAP_OR_TOUCH",
        "entry_price": 17050.0,
        "stop_risk_with_cost_usd": 100.0,
        "net_usd_per_lot": -100.0,
        "net_R": -1.0,
    }
    return {"E_SYN": {"2024-01-02": (row_win, stamps, marks), "2024-01-03": (row_sl, stamps_sl, marks_sl)}}


class TestRedTeamAndOps(unittest.TestCase):
    def test_01_holdout_lock_and_report_hygiene(self):
        sha_hex = assert_holdout_locked()
        self.assertEqual(len(sha_hex), 64)
        bare_dollar_re = re.compile(r"\$[0-9]")
        for rel in (
            "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.md",
            "planning/research/PROP-EV-FRONTIER-BALANCED-VS-SPRINT-20261124.md",
            "planning/research/QUANT-POD-4SLEEVE-ALLOCATION-20261124.md",
        ):
            p = ROOT / rel
            self.assertTrue(p.exists(), f"Missing report: {rel}")
            self.assertLess(p.stat().st_size, 900_000, f"Anti-bloat violation (>900KB): {rel}")
            txt = p.read_text(encoding="utf-8")
            self.assertIsNone(bare_dollar_re.search(txt), f"Bare $ found in Markdown prose: {rel}")

        rt_json = ROOT / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json"
        self.assertTrue(rt_json.exists())
        self.assertLess(rt_json.stat().st_size, 200_000)
        payload = json.loads(rt_json.read_text(encoding="utf-8"))
        self.assertEqual(payload["holdout_rows_analysed"], 0)
        self.assertEqual(payload["order_send_count"], 0)
        self.assertAlmostEqual(payload["test1_cost_stress"]["portfolio_breakeven"]["PORT_7E"]["check_net_usd_at_be"], 0.0, delta=1.0)
        self.assertAlmostEqual(payload["test1_cost_stress"]["portfolio_breakeven"]["PORT_9E"]["check_net_usd_at_be"], 0.0, delta=1.0)
        sha_sidecar = rt_json.with_suffix(".sha256")
        self.assertTrue(sha_sidecar.exists())
        expected_sha = sha_sidecar.read_text(encoding="utf-8").strip().split()[0]
        self.assertEqual(hashlib.sha256(rt_json.read_bytes()).hexdigest(), expected_sha)

    def test_02_red_team_cost_breakeven_latency_sl_clock_dst(self):
        tapes = _make_synthetic_tape()
        days = ["2024-01-02", "2024-01-03"]
        risks = {"E_SYN": 0.005}

        # Cost stress strict monotonicity + exact breakeven formula
        nets = []
        for mult in (1.0, 1.5, 2.0, 2.5, 3.0):
            m, _ = replay_portfolio_m1(days, transform_tapes_cost_stress(tapes, mult), risks, 10000.0)
            nets.append(m["net_usd"])
        for a, b in zip(nets, nets[1:]):
            self.assertGreater(a, b, f"Cost stress must decrease net PnL monotonically: {nets}")

        slope = nets[0] - nets[2]
        k_be = 1.0 + nets[0] / slope
        m_be, _ = replay_portfolio_m1(days, transform_tapes_cost_stress(tapes, k_be), risks, 10000.0)
        self.assertAlmostEqual(m_be["net_usd"], 0.0, delta=1e-4)

        # Explicit friction precedence avoids intrabar gap distortion
        row_e3 = {"cost_over_stop_pct": 3.0, "initial_risk_usd": 800.0, "stop_risk_with_cost_usd": 824.0}
        c_e3 = estimate_trade_base_cost_usd_per_lot(row_e3, np.array([[-65.0, 0.0, -70.0, -10.0]]))
        self.assertAlmostEqual(c_e3, 24.0, places=6)

        # Latency & adverse fill stress strictly <= baseline
        for mode in ("delay_1m_sym", "delay_1m_adverse", "worst_m1_bar"):
            ml, _ = replay_portfolio_m1(days, transform_tapes_latency_stress(tapes, mode), risks, 10000.0)
            self.assertLessEqual(ml["net_usd"], nets[0] + 1e-6)

        # Tightened SL 0.80x causally triggers on bar 40 (-85 <= -80)
        t_sl80 = transform_tapes_sl_perturbation(tapes, 0.80)
        row_hit, st_hit, _ = t_sl80["E_SYN"]["2024-01-02"]
        self.assertEqual(row_hit["reason"], "SL_TIGHTENED_HIT")
        self.assertEqual(len(st_hit), 41)
        self.assertAlmostEqual(row_hit["net_R"], -1.0, places=6)

        # Early-flat clock shift MUST preserve the fast SL hit on 2024-01-03 (zero survivorship bias!)
        t_ef = transform_tapes_clock_shift(tapes, "early_flat", shift_sec=3600)
        self.assertIn("2024-01-03", t_ef["E_SYN"])
        self.assertEqual(t_ef["E_SYN"]["2024-01-03"][0]["reason"], "SL_GAP_OR_TOUCH")
        self.assertAlmostEqual(t_ef["E_SYN"]["2024-01-03"][0]["net_usd_per_lot"], -100.0, places=6)

        # DST regime classifier
        self.assertEqual(classify_dst_regime("2024-07-15"), "US_EU_SUMMER_SYNC")
        self.assertEqual(classify_dst_regime("2024-01-15"), "US_EU_WINTER_SYNC")
        self.assertEqual(classify_dst_regime("2024-03-18"), "US_EU_DST_MISMATCH")
        self.assertEqual(classify_dst_regime("2024-10-30"), "US_EU_DST_MISMATCH")

    def test_03_prop_ev_frontier_determinism_and_ev_math(self):
        rng = np.random.default_rng(123)
        n_obs = 500
        nets = rng.normal(loc=22.0, scale=75.0, size=n_obs)
        dds = np.abs(rng.normal(loc=45.0, scale=35.0, size=n_obs))
        flg = np.ones(n_obs, dtype=np.int8)

        idx1 = make_block_bootstrap_indices(n_obs, horizon=504, n_paths=1000, block_len=5, seed=20261124)
        idx2 = make_block_bootstrap_indices(n_obs, horizon=504, n_paths=1000, block_len=5, seed=20261124)
        np.testing.assert_array_equal(idx1, idx2)

        variants = load_firm_variants()
        fids = [v[0]["id"] for v in variants]
        self.assertEqual(
            fids,
            ["FTMO_SWING_10K", "FTMO_STANDARD_10K", "FTMO_STANDARD_10K_BF25", "THE5ERS_HS_5K_8P5", "THE5ERS_HG_5K"],
        )
        bf_cfg = next(v[0] for v in variants if v[0]["id"] == "FTMO_STANDARD_10K_BF25")
        std_cfg = next(v[0] for v in variants if v[0]["id"] == "FTMO_STANDARD_10K")
        hs_cfg = next(v[0] for v in variants if v[0]["id"] == "THE5ERS_HS_5K_8P5")
        self.assertAlmostEqual(bf_cfg["fee_usd"], 126.0, places=2)
        self.assertAlmostEqual(hs_cfg["p1_target_pct"], 0.08, places=4)

        prof = {"id": "TEST_P1", "p1_mult": 3.0, "p2_mult": 2.0, "funded_mult": 1.0}
        r1 = evaluate_ev_profile(idx1, (nets, dds, flg), (nets, dds, flg), (nets, dds, flg), std_cfg, prof)
        r2 = evaluate_ev_profile(idx2, (nets, dds, flg), (nets, dds, flg), (nets, dds, flg), std_cfg, prof)
        self.assertEqual(r1, r2, "Monte Carlo output must be bit-identical for same seed")

        # Exact EV-per-USD-fee mathematical identity
        self.assertAlmostEqual(r1["ev_per_usd_fee_24m"], round(r1["cf24_mean_usd"] / r1["mean_fees_24m_usd"], 3), places=3)
        self.assertAlmostEqual(r1["ev_per_init_fee_24m"], round(r1["cf24_mean_usd"] / std_cfg["fee_usd"], 3), places=3)

        # Black Friday -25% fee strictly raises EV per USD fee on identical paths
        r_bf = evaluate_ev_profile(idx1, (nets, dds, flg), (nets, dds, flg), (nets, dds, flg), bf_cfg, prof)
        self.assertGreater(r_bf["ev_per_usd_fee_24m"], r1["ev_per_usd_fee_24m"])

        # Geometric P95 consecutive fails sanity
        self.assertEqual(geometric_p95_consec_fails(0.0), 0)
        self.assertEqual(geometric_p95_consec_fails(0.20), 1)
        self.assertEqual(geometric_p95_consec_fails(0.33), 2)
        self.assertEqual(geometric_p95_consec_fails(0.50), 4)

        # MT5 multiplier decomposition always respects PropGuard <= 3.50
        for eff in (1.0, 2.5, 3.5, 4.0, 4.75, 5.5):
            dc = decompose_mt5_multiplier(eff)
            self.assertLessEqual(dc["orch_base_phase_mult"], 3.50)
            self.assertAlmostEqual(dc["ea_risk_scale"] * dc["orch_base_phase_mult"], eff, delta=0.02)

    def test_04_postmortem_gen_classifications_and_markdown(self):
        rng = np.random.default_rng(42)
        dev = rng.normal(loc=0.04, scale=0.35, size=600)
        live_ok = rng.normal(loc=0.04, scale=0.35, size=60)
        live_dead = rng.normal(loc=-0.18, scale=0.35, size=100)
        live_vol_shift = rng.normal(loc=-0.02, scale=0.80, size=40)

        clean_tca = [
            {"symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.00, "fill_price": 150.01, "sl_price": 149.20, "spread_pts": 7.0, "latency_ms": 90.0, "swap_usd": 0.0},
        ]
        bad_tca = [{**clean_tca[0], "fill_price": 150.30, "swap_usd": -5.0}]
        ok_hb = {"status": "OK", "age_seconds": 15, "alerts": [], "payload": {"regime": "NORMAL"}}

        # 1. Execution TCA Bug takes priority
        pm_tca = run_weekly_postmortem(dev, live_ok, tca_events=bad_tca, heartbeat_report=ok_hb)
        self.assertEqual(pm_tca["diagnosis"]["classification"], "Execution TCA Bug")
        self.assertEqual(pm_tca["diagnosis"]["severity"], "RED")

        # 2. Structural Alpha Decay
        pm_dec = run_weekly_postmortem(dev, live_dead, tca_events=clean_tca, heartbeat_report=ok_hb)
        self.assertEqual(pm_dec["diagnosis"]["classification"], "Alpha Decay")
        self.assertEqual(pm_dec["diagnosis"]["severity"], "RED")

        # 3. Volatility Regime Shift
        pm_reg = run_weekly_postmortem(dev, live_vol_shift, tca_events=clean_tca, heartbeat_report=ok_hb)
        self.assertEqual(pm_reg["diagnosis"]["classification"], "Regime Shift")
        self.assertEqual(pm_reg["diagnosis"]["severity"], "AMBER")

        # 4. Normal Variance + Markdown persistence
        with tempfile.TemporaryDirectory() as td:
            md_path = Path(td) / "pm.md"
            pm_ok, md_txt = generate_weekly_postmortem(dev, live_ok, tca_events=clean_tca, heartbeat_report=ok_hb, output_md=md_path)
            self.assertEqual(pm_ok["diagnosis"]["classification"], "Normal Variance")
            self.assertTrue(md_path.exists())
            self.assertIn("Blameless Weekly Postmortem", md_txt)
            self.assertIn("Telemetry Evidence Matrix", md_txt)

    def test_05_research_council_proposer_and_skeptical_critic(self):
        rng = np.random.default_rng(77)
        card = propose_hypothesis(
            hypothesis_id="H_2026_TEST_01",
            title="London Fix Volatility Expansion",
            asset_universe=["EURJPY", "GBPUSD"],
            timeframe="M1_INTRADAY",
            counterparty_mechanism="SESSION_REBALANCING",
            economic_rationale="Institutional pension and corporate FX hedging flows concentrate into the London 16:00 fix, creating forced directional liquidity demand.",
            causal_invariants=["prior_d1_atr_only", "swap_zero_intraday_flat", "t_to_t_plus_1_exec"],
            n_trials_cumulative=20,
            kill_criteria=KillCriteria(max_bh_q=0.10, min_dsr=0.50, min_cluster_b_sharpe=0.50, min_cost_breakeven_mult=2.0),
        )
        inc = rng.normal(loc=0.0003, scale=0.004, size=600)
        good_a = rng.normal(loc=0.0009, scale=0.004, size=600)
        good_b = rng.normal(loc=0.0008, scale=0.004, size=600)

        ev_good = EvidenceBundle(
            cluster_a_returns=good_a,
            cluster_b_returns=good_b,
            p_value_raw=0.002,
            family_p_values=(0.002, 0.25, 0.50, 0.70),
            candidate_index_in_family=0,
            cost_1x_net=1200.0,
            cost_2x_net=700.0,
            n_trades_cluster_b=120,
            incumbent_daily_returns=inc,
            holdout_rows_analysed=0,
        )
        v_good = critique_proposal(card, ev_good)
        self.assertEqual(v_good["verdict"], "APPROVE_FOR_INCUBATION")
        self.assertEqual(v_good["failed_gates"], [])

        # Fail-closed on Holdout contamination
        ev_leak = EvidenceBundle(**{**ev_good.__dict__, "holdout_rows_analysed": 12})
        v_leak = critique_proposal(card, ev_leak)
        self.assertEqual(v_leak["verdict"], "REJECT_KILLED")
        self.assertIn("G0_seal_and_card", v_leak["failed_gates"])

        # Fail-closed on cost fragility & high correlation redundancy
        ev_bad = EvidenceBundle(**{**ev_good.__dict__, "cost_2x_net": -50.0, "cluster_b_returns": inc * 0.95 + rng.normal(0, 0.0005, size=600)})
        v_bad = critique_proposal(card, ev_bad)
        self.assertEqual(v_bad["verdict"], "REJECT_KILLED")
        self.assertIn("G3_cost_stress", v_bad["failed_gates"])
        self.assertIn("G4_orthogonality", v_bad["failed_gates"])

    def test_06_red_news_csv_extended_through_2027(self):
        from quant_factory.build_red_news_calendar import build_or_verify_calendar, merge_and_deduplicate_events

        csv_path = AI_ENGINES / "exports/Files/naqex_red_news_utc.csv"
        raw_lines = csv_path.read_text(encoding="utf-8").splitlines()
        self.assertEqual(raw_lines[0], "utc_ts,ccy,event")
        self.assertLess(csv_path.stat().st_size, 200_000, "Red-news CSV must remain well under 200 KB")

        rows = []
        for idx, line in enumerate(raw_lines[1:], start=2):
            parts = line.split(",")
            self.assertEqual(len(parts), 3, f"MQL5 3-col contract broken on line {idx}: {line}")
            rows.append((int(parts[0]), parts[1], parts[2]))

        # Strictly sorted non-decreasing, zero duplicate (utc_ts, ccy) pairs
        tss = [r[0] for r in rows]
        self.assertEqual(tss, sorted(tss), "CSV timestamps must be sorted ascending")
        ts_ccy_keys = [(r[0], r[1]) for r in rows]
        self.assertEqual(len(ts_ccy_keys), len(set(ts_ccy_keys)), "Duplicate (utc_ts, ccy) pairs found")

        t2025_start = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())
        t2026_start = int(datetime(2026, 1, 1, tzinfo=timezone.utc).timestamp())
        t2027_start = int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp())
        t2028_start = int(datetime(2028, 1, 1, tzinfo=timezone.utc).timestamp())
        in_1824 = [r for r in rows if r[0] < t2025_start]
        in_2025 = [r for r in rows if t2025_start <= r[0] < t2026_start]
        in_2026 = [r for r in rows if t2026_start <= r[0] < t2027_start]
        in_2027 = [r for r in rows if t2027_start <= r[0] < t2028_start]

        # Frozen 2018-2024 Dev (224) and 2025 (31) rows must remain 100% untouched
        self.assertEqual(len(in_1824), 224, "Frozen 2018-2024 Dev rows must remain untouched")
        self.assertEqual(len(in_2025), 31, "Frozen 2025 rows must remain untouched")
        # Expanded late-2026 & full-2027 must cover all 4 currencies (USD, EUR, GBP, JPY)
        self.assertGreaterEqual(len(in_2026), 46, "2026 must include 32 USD + expanded late-2026 4-ccy events")
        self.assertEqual({r[1] for r in in_2026}, {"USD", "EUR", "GBP", "JPY"})
        self.assertGreaterEqual(len(in_2027), 115, "2027 must include all 56 original anchors + expanded multi-ccy macro/CB events")
        self.assertEqual({r[1] for r in in_2027}, {"USD", "EUR", "GBP", "JPY"})

        ev_counts = {}
        for _, ccy, ev in in_2027:
            ev_counts[ev] = ev_counts.get(ev, 0) + 1
            self.assertIn(ccy, {"USD", "EUR", "GBP", "JPY"})
        # All 56 original 2027 anchor events preserved verbatim
        self.assertEqual(ev_counts["US_NFP_BLS2027"], 12)
        self.assertEqual(ev_counts["US_CPI_BLS2027"], 12)
        self.assertEqual(ev_counts["FOMC_FED2027_TENTATIVE"] + ev_counts["FOMC_STRATEGY_FED2027_TENTATIVE"], 8)
        self.assertEqual(ev_counts["ECB_RATE_ECB2027"], 8)
        self.assertEqual(ev_counts["BOE_RATE_BOE2027"], 8)
        self.assertEqual(ev_counts["BOJ_RATE_BOJ2027_EST03UTC"], 8)
        # Newly added 2027 multi-ccy red folders (PPI, Retail Sales, Core PCE/GDP, UK CPI, ECB Press Conf, FOMC Press Conf)
        self.assertEqual(ev_counts["UK_CPI_ONS2027"], 12)
        self.assertEqual(ev_counts["ECB_PRESS_CONF_ECB2027"], 8)
        self.assertEqual(ev_counts["FOMC_PRESS_CONF_FED2027_TENTATIVE"], 7)
        self.assertEqual(ev_counts["US_GDP_ADV_AND_CORE_PCE_BEA2027"] + ev_counts["US_GDP_AND_CORE_PCE_BEA2027"], 12)
        self.assertEqual(sum(n for ev, n in ev_counts.items() if "US_PPI_BLS2027" in ev), 12)
        self.assertEqual(sum(n for ev, n in ev_counts.items() if "US_RETAIL_SALES_CENSUS2027" in ev), 12)

        # Spot-check exact DST UTC timestamps (EST/EDT, CET/CEST, GMT/BST, JST) across 2026 & 2027
        by_triple = {(t, c, e) for t, c, e in (in_2026 + in_2027)}
        expected_checks = [
            (datetime(2026, 11, 25, 13, 30, tzinfo=timezone.utc), "USD", "US_GDP_AND_CORE_PCE_BEA2026"),
            (datetime(2026, 12, 16, 7, 0, tzinfo=timezone.utc), "GBP", "UK_CPI_ONS2026"),
            (datetime(2026, 12, 17, 12, 0, tzinfo=timezone.utc), "GBP", "BOE_RATE_BOE2026"),
            (datetime(2026, 12, 17, 13, 15, tzinfo=timezone.utc), "EUR", "ECB_RATE_ECB2026"),
            (datetime(2026, 12, 17, 13, 45, tzinfo=timezone.utc), "EUR", "ECB_PRESS_CONF_ECB2026"),
            (datetime(2026, 12, 18, 3, 0, tzinfo=timezone.utc), "JPY", "BOJ_RATE_BOJ2026_EST03UTC"),
            (datetime(2027, 1, 8, 13, 30, tzinfo=timezone.utc), "USD", "US_NFP_BLS2027"),           # EST UTC-5
            (datetime(2027, 6, 4, 12, 30, tzinfo=timezone.utc), "USD", "US_NFP_BLS2027"),           # EDT UTC-4
            (datetime(2027, 1, 27, 19, 0, tzinfo=timezone.utc), "USD", "FOMC_FED2027_TENTATIVE"),   # EST 14:00 -> 19:00 UTC
            (datetime(2027, 6, 9, 18, 0, tzinfo=timezone.utc), "USD", "FOMC_FED2027_TENTATIVE"),    # EDT 14:00 -> 18:00 UTC
            (datetime(2027, 2, 4, 13, 15, tzinfo=timezone.utc), "EUR", "ECB_RATE_ECB2027"),         # CET 14:15 -> 13:15 UTC
            (datetime(2027, 6, 10, 12, 15, tzinfo=timezone.utc), "EUR", "ECB_RATE_ECB2027"),        # CEST 14:15 -> 12:15 UTC
            (datetime(2027, 6, 10, 12, 45, tzinfo=timezone.utc), "EUR", "ECB_PRESS_CONF_ECB2027"),  # CEST 14:45 -> 12:45 UTC
            (datetime(2027, 2, 4, 12, 0, tzinfo=timezone.utc), "GBP", "BOE_RATE_BOE2027"),          # GMT 12:00 -> 12:00 UTC
            (datetime(2027, 6, 17, 11, 0, tzinfo=timezone.utc), "GBP", "BOE_RATE_BOE2027"),         # BST 12:00 -> 11:00 UTC
            (datetime(2027, 6, 16, 6, 0, tzinfo=timezone.utc), "GBP", "UK_CPI_ONS2027"),            # BST 07:00 -> 06:00 UTC
            (datetime(2027, 1, 22, 3, 0, tzinfo=timezone.utc), "JPY", "BOJ_RATE_BOJ2027_EST03UTC"), # JST 12:00 -> 03:00 UTC
            (datetime(2027, 10, 15, 12, 30, tzinfo=timezone.utc), "USD", "US_PPI_BLS2027+US_RETAIL_SALES_CENSUS2027"),
        ]
        for dt_utc, ccy, ev in expected_checks:
            self.assertIn((int(dt_utc.timestamp()), ccy, ev), by_triple, f"Missing/wrong UTC timestamp for {dt_utc} {ccy} {ev}")

        # Deterministic builder verification & deduplication check
        rep = build_or_verify_calendar(write=False)
        self.assertTrue(rep["ok"], f"build_red_news_calendar verification failed: {rep['errors']}")
        self.assertTrue(rep["disk_matches_deterministic_build"])
        self.assertTrue(rep["parity_check"]["ok"])
        dedup_rows, merges = merge_and_deduplicate_events(
            [(1700000000, "USD", "EV_A")],
            [(1700000000, "USD", "EV_A"), (1700000000, "USD", "EV_B")],
            [(1700000000, "GBP", "EV_C")],
        )
        self.assertEqual(dedup_rows, [(1700000000, "GBP", "EV_C"), (1700000000, "USD", "EV_A+EV_B")])
        self.assertEqual(len(merges), 1)

        upcoming = load_upcoming_red_news(csv_path, now_utc_ts=int(datetime(2027, 1, 1, tzinfo=timezone.utc).timestamp()), limit=5)
        self.assertEqual(len(upcoming), 5)
        self.assertEqual(upcoming[0]["event"], "US_NFP_BLS2027")

    def test_07_four_sleeve_allocator_and_fast_pod_dashboard(self):
        # 1. Weekend compounding preserves 100% of crypto cumulative return
        s_fx = {"2024-01-05": 0.01, "2024-01-08": 0.02}
        s_cr = {"2024-01-05": 0.01, "2024-01-06": 0.03, "2024-01-07": -0.02, "2024-01-08": 0.01}
        days, mat, names = align_sleeves_business_days({"FX": s_fx, "CR": s_cr})
        self.assertEqual(days, ["2024-01-05", "2024-01-08"])
        raw_cr_cum = np.prod([1.0 + v for v in s_cr.values()])
        aligned_cr_cum = np.prod(1.0 + mat[:, 1])
        self.assertAlmostEqual(aligned_cr_cum, raw_cr_cum, places=10)

        # 2. All 7 allocators valid, ERC equalizes risk contributions, Capped35 <= 0.35
        rng = np.random.default_rng(99)
        mat4 = np.column_stack([
            rng.normal(0.0003, 0.004, 400),
            rng.normal(0.0006, 0.008, 400),
            rng.normal(0.0002, 0.0007, 400),
            rng.normal(0.0002, 0.005, 400),
        ])
        for mname, fn in ALLOCATORS.items():
            w = fn(mat4)
            self.assertAlmostEqual(float(np.sum(w)), 1.0, places=6, msg=mname)
            self.assertTrue(np.all(w >= -1e-9), msg=mname)

        w_erc = weights_erc(mat4)
        rc_erc = compute_risk_contributions(np.cov(mat4, rowvar=False), w_erc)
        self.assertLess(float(np.max(np.abs(rc_erc - 0.25))), 0.01)

        self.assertLessEqual(float(np.max(weights_erc_capped35(mat4))), 0.35 + 1e-6)
        self.assertLessEqual(float(np.max(weights_hrp_capped35(mat4))), 0.35 + 1e-6)

        # 3. Single-command Pod Dashboard runs in < 2.0s and outputs complete HTML + MD
        with tempfile.TemporaryDirectory() as td:
            h_out = Path(td) / "dash.html"
            m_out = Path(td) / "dash.md"
            t0 = time.perf_counter()
            snap = generate_pod_dashboard(html_out=h_out, md_out=m_out)
            elapsed = time.perf_counter() - t0
            self.assertLess(elapsed, 2.0, f"Dashboard generation exceeded 2s budget: {elapsed:.3f}s")
            self.assertEqual(snap["holdout_rows_analysed"], 0)
            self.assertEqual(snap["order_send_count"], 0)
            self.assertEqual(len(snap["sleeve_names"]), 4)
            h_txt = h_out.read_text(encoding="utf-8")
            m_txt = m_out.read_text(encoding="utf-8")
            self.assertIn("NAQEX QUANT POD — UNIFIED CONTROL ROOM", h_txt)
            self.assertIn("S3B_MACRO_ETF", h_txt)
            self.assertIn("CUSUM", h_txt)
            self.assertIn("ERC_Capped35", m_txt)
            self.assertGreaterEqual(len(snap["upcoming_red_news"]), 1)


if __name__ == "__main__":
    unittest.main()
