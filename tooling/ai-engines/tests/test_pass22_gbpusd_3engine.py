"""Unit tests for Pass 22 GBPUSD WB_EXP_80_VOL_HIGH forensic & 3-engine Prague audit."""

import unittest

import pass22_gbpusd_volhigh_3engine as p22
from quant_core.ftmo_track_replay import profiles


class TestPass22Gbpusd3Engine(unittest.TestCase):
    def test_outlier_stress_report_excludes_covid_and_gilt_cleanly(self):
        fake_tape = [
            ({"day": "2020-03-18", "direction": "SELL", "net_R": 4.0}, None, None),
            ({"day": "2022-09-23", "direction": "SELL", "net_R": 3.5}, None, None),
            ({"day": "2021-05-10", "direction": "BUY", "net_R": 2.0}, None, None),
            ({"day": "2023-02-02", "direction": "BUY", "net_R": 1.5}, None, None),
            ({"day": "2024-04-12", "direction": "SELL", "net_R": -1.0}, None, None),
        ]
        rep = p22.outlier_stress_report(fake_tape)
        self.assertAlmostEqual(rep["total_R"], 10.0, places=2)
        self.assertAlmostEqual(rep["excl_covid_2020_03_R"], 6.0, places=2)
        self.assertAlmostEqual(rep["excl_gilt_2022_0910_R"], 6.5, places=2)
        self.assertAlmostEqual(rep["excl_both_crises_R"], 2.5, places=2)
        self.assertEqual(rep["excl_both_n"], 3)
        self.assertAlmostEqual(rep["drop_top3_R"], 0.5, places=2)

    def test_gbpusd_ftmo_swing_margin_spec_consistency(self):
        specs, _ = profiles()
        gbp = specs["Swing"]["GBPUSD"]
        self.assertEqual(gbp["currency_profit"], "USD")
        self.assertAlmostEqual(gbp["trade_contract_size"], 100000.0)
        self.assertAlmostEqual(gbp["margin_per_reference"], 100000.0 / 30.0, places=1)


if __name__ == "__main__":
    unittest.main()
