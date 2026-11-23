"""Unit tests for Pass 20 Positive-Swap Carry-Trend forensic & 3-Engine Prague-reset simulator."""

from datetime import date, datetime, timezone
import unittest

import numpy as np

import pass20_pos_swap_carry_3engine as p20
from quant_core.ftmo_track_replay import profiles


class TestPass20Carry3Engine(unittest.TestCase):
    def test_profit_and_margin_currency_conversions_for_eurgbp_and_jpy(self):
        """Verify EURGBP multiplies by GBPUSD for profit ccy and EURUSD for base margin."""
        d = date(2020, 6, 1)
        conv = {
            "USDJPY": {d: 110.0}, "USDCAD": {d: 1.35}, "USDCHF": {d: 0.96},
            "EURUSD": {d: 1.12}, "GBPUSD": {d: 1.25}, "AUDUSD": {d: 0.68},
        }
        self.assertAlmostEqual(p20.profit_ccy_to_usd_mult("GBP", d, conv, 0.89), 1.25)
        self.assertAlmostEqual(p20.profit_ccy_to_usd_mult("JPY", d, conv, 110.0), 1.0 / 110.0)
        self.assertAlmostEqual(p20.margin_quote_mult("EURGBP", d, conv), 1.12)
        self.assertAlmostEqual(p20.margin_quote_mult("GBPJPY", d, conv), 1.25)
        self.assertAlmostEqual(p20.margin_quote_mult("USDCAD", d, conv), 1.0)

    def test_jpy_concurrency_cap_enforces_max_one_jpy_carry_open(self):
        """Verify max_jpy_open=1 rejects overlapping JPY carry trades while allowing non-JPY trades."""
        fake = {
            "USDJPY": [{"sym": "USDJPY", "entry": 100, "exit": 500, "is_jpy": True}],
            "GBPJPY": [{"sym": "GBPJPY", "entry": 200, "exit": 600, "is_jpy": True}],
            "USDCAD": [{"sym": "USDCAD", "entry": 200, "exit": 600, "is_jpy": False}],
        }
        kept = p20.apply_sleeve_filters(fake, ("USDJPY", "GBPJPY", "USDCAD"), max_jpy_open=1)
        syms = [t["sym"] for t in kept]
        self.assertEqual(syms, ["USDJPY", "USDCAD"])

    def test_3engine_prague_simulator_tracks_floating_dd_and_daily_loss(self):
        """Verify unified Prague-reset simulator accurately records intrabar floating DD & daily loss."""
        specs, _ = profiles()
        t0 = int(datetime(2020, 1, 2, 10, 0, tzinfo=timezone.utc).timestamp())
        t1 = t0 + 4 * 3600
        # 1 carry trade on USDCAD risking $1000/lot; at 0.5% of $10,000 -> budget $50 -> 0.05 lots
        # Intrabar worst = -$1000/lot (-$50 = -0.50% DD & Daily Loss); terminal close = +$2000/lot (+$100 = +1.00%)
        carry = [{
            "sym": "USDCAD", "day": "2020-01-02", "exit_day": "2020-01-02", "year": 2020,
            "side": 1, "is_jpy": False, "entry": t0, "exit": t1,
            "entry_price": 1.30, "exit_price": 1.32, "margin_quote": 1.0,
            "stop_risk_with_cost_usd": 1000.0, "ftmo_net": 2000.0,
            "stamps": np.array([t0, t1], dtype=np.int64),
            "worst_usd": np.array([-1000.0, 2000.0], dtype=np.float64),
            "close_usd": np.array([0.0, 2000.0], dtype=np.float64),
        }]
        res = p20.replay_3engine_prague(set(), {}, {}, carry, 0.005, 10000.0, specs["Swing"])
        self.assertAlmostEqual(res["net_usd"], 100.0, places=2)
        self.assertAlmostEqual(res["peak_dd_pct"], 0.50, places=2)
        self.assertAlmostEqual(res["daily_loss_pct"], 0.50, places=2)
        self.assertEqual(res["margin_failures"], 0)
        self.assertEqual(res["sized_carry"], 1)


if __name__ == "__main__":
    unittest.main()
