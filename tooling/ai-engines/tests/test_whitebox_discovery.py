"""Unit tests for White-Box Prop-First Discovery Engine & FTMO-safe .mq5 exporter/intake auditor."""

from pathlib import Path
import tempfile
import unittest

import inbox_intake_scanner as intake
import mq5_whitebox_exporter as mq5
import whitebox_discovery as wb


class TestWhiteBoxDiscoveryAndExporter(unittest.TestCase):
    def test_open_source_mq5_auditor_flags_martingale_dll_and_accepts_clean_ea(self):
        """Verify static open-source .mq5 auditor catches DLL/Martingale red flags and accepts clean hard-SL EA."""
        toxic = """
        #import "evil_helper.dll"
        input double MartingaleMultiplier = 1.8;
        input int GridStep = 200;
        void OnTick() { WebRequest("GET", "https://example.com", "", 1000, NULL, NULL, NULL); }
        """
        r_bad = mq5.audit_open_source_mq5(toxic, filename="toxic_sample.mq5")
        self.assertEqual(r_bad["intake_verdict"], "REJECT_PROP_RED_FLAGS")
        self.assertIn("DLL_IMPORT", r_bad["red_flags"])
        self.assertIn("MARTINGALE_HINT", r_bad["red_flags"])
        self.assertIn("GRID_HINT", r_bad["red_flags"])
        self.assertIn("WEB_REQUEST", r_bad["red_flags"])
        self.assertIn("NO_EXPLICIT_SL_TOKEN", r_bad["red_flags"])

        clean_code = mq5.export_exp_daily_open_mq5({
            "strategy": "EXP_DAILY_OPEN_080", "asset": "USDJPY",
            "trig_atr": 0.80, "sl_atr": 0.75, "risk_pct": 0.50,
            "protocol_commit": "9bbf69c83241d2b1084d21bd3a23f057414a5677",
            "tier": "TIER_1_FTMO_READY",
        })
        r_clean = mq5.audit_open_source_mq5(clean_code, filename="naqex_exp080_usdjpy.mq5")
        self.assertEqual(r_clean["intake_verdict"], "CLEAN_FOR_PYTHON_REPLICATION")
        self.assertEqual(r_clean["red_flags"], [])
        self.assertIn("InpDryRunLogOnly     = true;", clean_code)
        self.assertIn("HARD_FLAT_SWAP0", clean_code)

    def test_grammar_catalog_covers_all_four_orthogonal_prop_archetypes(self):
        cat = wb.build_grammar_catalog()
        arches = {c["arch"] for c in cat}
        self.assertEqual(arches, {"WB_SESSION_BOX", "WB_OPEN_EXPANSION", "WB_OVEREXT_FADE", "WB_IMPULSE_PULLBACK"})
        self.assertEqual(len(cat), 30)

    def test_strict_cluster_split_metrics_isolates_cluster_a_from_cluster_b(self):
        trades = [
            {"year": 2019, "ftmo_R": 2.0},
            {"year": 2020, "ftmo_R": -1.0},
            {"year": 2022, "ftmo_R": -5.0},
        ]
        mA = wb.split_metrics(trades, (2018, 2019, 2020))
        mB = wb.split_metrics(trades, (2021, 2022, 2023, 2024))
        self.assertEqual(mA["n"], 2)
        self.assertAlmostEqual(mA["net_R"], 1.0)
        self.assertAlmostEqual(mA["pf"], 2.0)
        self.assertEqual(mB["n"], 1)
        self.assertAlmostEqual(mB["net_R"], -5.0)

    def test_inbox_scanner_quarantines_binaries_and_flags_utf16_martingale_set(self):
        """Verify read-only inbox scanner quarantines .ex5/.rar and detects Martingale/Rollover in UTF-16 .set."""
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "bot.ex5").write_bytes(b"FAKE_EX5")
            (root / "crack.rar").write_bytes(b"Rar!")
            (root / "mart.set").write_bytes("MartingaleMultiplier=1.8\r\nST_Period=10\r\n".encode("utf-16"))
            (root / "clean.mq5").write_text("input double InpSlAtr = 0.75;\nvoid OnTick(){}\n", encoding="utf-8")
            rep = intake.scan_inbox(root, run_defender=False)
            self.assertEqual(rep["summary"]["quarantined_binaries_no_exec"], 2)
            self.assertEqual(rep["summary"]["set_flagged_anti_prop"], 1)
            self.assertEqual(rep["summary"]["open_source_clean"], 1)
            self.assertIn("MARTINGALE_SET", rep["set_and_text"][0]["red_flags"])
            self.assertIn("SuperTrend", rep["set_and_text"][0]["public_indicator_hints"])


if __name__ == "__main__":
    unittest.main()
