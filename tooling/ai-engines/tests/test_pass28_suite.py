"""Regression tests for Pass 28: Official Red-News Calendar & ±5m Guard, Catalog=40, and 1-Step Hyper Growth Daily Pause."""

import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import pass28_final_discovery_rednews_frontier as p28


class Pass28SuiteTests(unittest.TestCase):
    def test_catalog_has_exact_40_unique_specs_across_5_families(self):
        cat = p28.build_pass28_catalog()
        self.assertEqual(len(cat), 40)
        self.assertEqual(len({c["id"] for c in cat}), 40)
        self.assertEqual(len({c["fam"] for c in cat}), 5)

    def test_official_red_news_calendar_counts_and_flatten_guard(self):
        cal = p28.build_official_red_news_calendar(include_uk_proxy=False)
        # 56 FOMC + 84 CPI + 84 NFP = 224 exact US events across 2018-2024
        self.assertEqual(sum(len(v) for v in cal.values()), 224)

        # Synthetic trade entered before 2024-01-31 FOMC (14:00 ET = 19:00 UTC) and held past it -> must flatten at 18:55 UTC!
        fomc_ts = p28._local_ts("2024-01-31", 14, 0, p28.NY_TZ)
        stamps = np.array([fomc_ts - 600 + i * 60 for i in range(15)], dtype=np.int64)  # 18:50 .. 19:04 UTC
        marks = np.zeros((15, 4), dtype=np.float64)
        for i in range(15):
            marks[i] = [i * 10.0, i * 10.0 + 2.0, i * 10.0 - 2.0, i * 10.0 + 5.0]
        row = {
            "day": "2024-01-31", "asset": "US100", "entry": int(stamps[0]), "exit": int(stamps[-1]) + 60,
            "at_open": False, "reason": "HARD_FLAT", "net_usd_per_lot": float(marks[-1, 3]),
            "stop_risk_with_cost_usd": 100.0, "net_R": float(marks[-1, 3]) / 100.0,
        }
        guarded, stats = p28.apply_red_news_guard_to_tape({"2024-01-31": (row, stamps, marks)}, cal, mode="FLATTEN_5M", pad_sec=300)
        self.assertEqual(stats["flattened_pre_news"], 1)
        new_row, new_stamps, new_marks = guarded["2024-01-31"]
        self.assertEqual(new_row["reason"], "NEWS_PRE_FLATTEN")
        self.assertLessEqual(int(new_stamps[-1]), fomc_ts - 300)
        self.assertAlmostEqual(new_row["net_usd_per_lot"], float(new_marks[-1, 3]), places=6)

        # Trade entering inside ±5 min window must be completely blocked
        row_blk = {**row, "entry": fomc_ts - 120}
        stamps_blk = np.array([fomc_ts - 120 + i * 60 for i in range(5)], dtype=np.int64)
        g2, st2 = p28.apply_red_news_guard_to_tape({"2024-01-31": (row_blk, stamps_blk, marks[:5])}, cal, mode="FLATTEN_5M", pad_sec=300)
        self.assertEqual(st2["blocked_entry"], 1)
        self.assertEqual(len(g2), 0)

    def test_hyper_growth_1step_3pct_daily_pause_does_not_breach_account(self):
        # Day 1 hits -4% raw DD (capped by 3% non-breaching pause -> -3% net); Day 2-12 rally +1.5%/day -> PASSES with 0 breach!
        nets = np.array([-400.0] + [150.0] * 15, dtype=np.float64)  # on 10k base -> scaled 0.5 for 5k
        dds = np.array([400.0] + [20.0] * 15, dtype=np.float64)
        idx = np.array([np.arange(16, dtype=np.int32)])
        res = p28.run_frontier_hyper_growth_1step(idx, nets, dds, cap=5000.0, fee=260.0, p1_mult=1.0)
        self.assertEqual(res["br1_pct"], 0.0)
        self.assertEqual(res["pass_3m"], 100.0)

    def test_exported_e6_and_e7_mq5_have_zero_red_flags_and_dryrun_default(self):
        import mq5_whitebox_exporter as exp
        exp_dir = Path(__file__).resolve().parents[1] / "exports"
        for fname, token in (
            ("Naqex_WB_VOLCOMP_EXP75_EURJPY.mq5", "InpMaxVolRatio5_20   = 0.85;"),
            ("Naqex_WB_NY_RISK_FLOW_10ET_USDJPY.mq5", "InpMinEquityMoveAtr  = 0.25;"),
        ):
            src = (exp_dir / fname).read_text(encoding="utf-8")
            audit = exp.audit_open_source_mq5(src, filename=fname)
            self.assertEqual(audit["red_flags"], [])
            self.assertEqual(audit["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")
            self.assertIn("InpDryRunLogOnly     = true;", src)
            self.assertIn(token, src)


if __name__ == "__main__":
    unittest.main()
