"""Regression tests for Pass 27: M1 floating-equity Prague replay, US100 overlap cap, 4-state phase machine & .mq5 exports."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import mq5_whitebox_exporter as exp
import pass27_portfolio_m1_phase_audit as p27


class Pass27AuditAndPhaseTests(unittest.TestCase):
    def test_4state_phase_machine_transitions_and_satellite_gating(self):
        pol = {
            "core_key": "PORT_5E",
            "p1_key": "PORT_6E",
            "p1_mult": 1.85,
            "p2_mult": 1.20,
            "funded_mult": 1.0,
            "dynamic_dd": True,
            "glidepath": True,
            "funded_survival": True,
        }
        # P1 Green uses satellite P1_KEY at full P1 mult
        self.assertEqual(p27.compute_phase_state_and_mult("P1", 10000.0, 10000.0, pol, False), ("P1_GREEN", 1.85, "PORT_6E"))
        # P1 Lock-In (>= +7.0% and >= +8.5%) drops satellites & throttles down cleanly
        self.assertEqual(p27.compute_phase_state_and_mult("P1", 10750.0, 10000.0, pol, False), ("P1_LOCKIN", 1.0, "PORT_5E"))
        self.assertEqual(p27.compute_phase_state_and_mult("P1", 10880.0, 10000.0, pol, False), ("P1_LOCKIN_FINAL", 0.5, "PORT_5E"))
        # Amber (-3.5%..-6.0%) and Red (<= -6.0%) auto-drop satellites to pure core
        self.assertEqual(p27.compute_phase_state_and_mult("P1", 9600.0, 10000.0, pol, False), ("AMBER_THROTTLE", 0.65, "PORT_5E"))
        self.assertEqual(p27.compute_phase_state_and_mult("P1", 9350.0, 10000.0, pol, False), ("RED_SURVIVAL", 0.40, "PORT_5E"))
        # P2 Cruise & Lock-In strictly core-only
        self.assertEqual(p27.compute_phase_state_and_mult("P2", 10000.0, 10000.0, pol, False), ("P2_CRUISE", 1.20, "PORT_5E"))
        self.assertEqual(p27.compute_phase_state_and_mult("P2", 10350.0, 10000.0, pol, False), ("P2_LOCKIN", 0.60, "PORT_5E"))
        # Funded survival before refund vs Funded harvest after refund
        self.assertEqual(p27.compute_phase_state_and_mult("FUNDED", 10050.0, 10000.0, pol, False), ("FUNDED_SURVIVAL", 0.80, "PORT_5E"))
        self.assertEqual(p27.compute_phase_state_and_mult("FUNDED", 10050.0, 10000.0, pol, True), ("FUNDED_HARVEST", 1.0, "PORT_5E"))

    def test_m1_tape_reconciles_terminal_cash_and_us100_overlap_cap(self):
        # Synthetic 5-minute M1 US100 BUY trade (entry at 15:00 UTC -> hard flat at 15:04 UTC)
        t0 = 1704207600  # 2024-01-02 15:00:00 UTC (Prague 16:00 CET)
        times = np.array([t0 + i * 60 for i in range(5)], dtype=np.int64)
        # Bid O,H,L,C and Ask O,H,L,C (spread = 2.0 pts, steady rally +100 pts)
        quotes = np.array([
            [16800, 16810, 16790, 16805, 16802, 16812, 16792, 16807],
            [16805, 16830, 16800, 16825, 16807, 16832, 16802, 16827],
            [16825, 16860, 16820, 16855, 16827, 16862, 16822, 16857],
            [16855, 16890, 16850, 16885, 16857, 16892, 16852, 16887],
            [16902, 16905, 16900, 16902, 16904, 16907, 16902, 16904],
        ], dtype=np.float64)
        item = p27.replay_causal_m1_tape_trade("US100", times, quotes, 0, 4, 1, 16802.0, 16702.0, cost_tier="stress")
        self.assertIsNotNone(item)
        row, stamps, marks = item
        # Gross +100.0 pts - 4.0 pts stress slip = +96.0 USD/lot
        self.assertAlmostEqual(row["net_usd_per_lot"], 96.0, places=6)
        self.assertAlmostEqual(float(marks[-1, -1]), row["net_usd_per_lot"], places=6)

        # Feed two same-day same-direction US100 engines with 0.50% each under a 0.75% US100 overlap cap
        dk = row["day"]
        tapes = {"E4": {dk: item}, "E5": {dk: item}}
        met_raw, _ = p27.replay_multi_engine_m1([dk], tapes, {"E4": 0.005, "E5": 0.005}, 10000.0, us100_same_dir_cap=None)
        met_cap, _ = p27.replay_multi_engine_m1([dk], tapes, {"E4": 0.005, "E5": 0.005}, 10000.0, us100_same_dir_cap=0.0075)
        self.assertEqual(met_raw["us100_cap_activations"], 0)
        self.assertEqual(met_cap["us100_cap_activations"], 1)
        self.assertLess(met_cap["net_usd"], met_raw["net_usd"])

    def test_exported_e5_and_s6_mq5_have_zero_red_flags_and_dryrun_default(self):
        exp_dir = Path(__file__).resolve().parents[1] / "exports"
        for fname, token in (
            ("Naqex_WB_IDX_RS_US100_LEAD_1130.mq5", "InpMinRsDiffAtr      = 0.25;"),
            ("Naqex_WB_FX_USD_BASKET_12U_Z35.mq5", "InpMinUsdBasketZ     = 0.35;"),
        ):
            src = (exp_dir / fname).read_text(encoding="utf-8")
            audit = exp.audit_open_source_mq5(src, filename=fname)
            self.assertEqual(audit["red_flags"], [])
            self.assertEqual(audit["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")
            self.assertIn("InpDryRunLogOnly     = true;", src)
            self.assertIn(token, src)


if __name__ == "__main__":
    unittest.main()
