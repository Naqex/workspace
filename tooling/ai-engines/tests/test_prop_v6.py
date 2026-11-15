from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_v6_account import HarvestAccount
from prop_v6_signals import Calendar
from prop_v6_paths import scenario, realize
from prop_v6_replay import clocks
from prop_v6_campaign import ReferenceAccount
from prop_v6_measurement import MeasuredHarvest
from prop_campaign_source import stamp, HOUR, DAY
from prop_portfolio_sources import BAR
from test_prop_v5 import trade, quote


class V6Tests(unittest.TestCase):
    def account(self, **kw):
        return HarvestAccount(stamp("2022-01-01"), stamp("2027-01-01"),
                              "ASYM_FLAT", rolling=True, **kw)

    def test_phase1_and_phase2_never_ratchet(self):
        a = self.account()
        for phase in (1, 2):
            a.phase = phase
            a.observe_policy(a.start, 55000000)
            self.assertFalse(a.ratchet)
            self.assertFalse(a.pending)
            self.assertEqual(a.risk_request(55000000, "CORE", 1), 200 if phase == 1 else 175)

    def test_standalone_begins_funded_without_challenge_targets(self):
        a = self.account(standalone=True)
        self.assertEqual(a.phase, 3)
        self.assertEqual(a.passes, [])
        self.assertEqual(a.risk_request(50000000, "SATELLITE", 1), 125)

    def test_original_equity_throttles_and_caps_retained(self):
        a = self.account()
        self.assertEqual(a.risk_request(48000000, "CORE", 1), 150)
        self.assertEqual(a.risk_request(47000000, "CORE", 1), 90)
        self.assertEqual(a.open_cap_milli, 800000)
        self.assertEqual(a.internal_floor_milli, 46000000)

    def test_harvester_remains_active_only_in_funded(self):
        a = self.account(standalone=True)
        a.funded_first = a.start
        a.balance = 51000000
        a.observe_policy(a.start, a.balance)
        self.assertEqual(a.harvest_state, "PROFIT_LOCK_IDLE")
        a.reward(a.start + 14 * DAY)
        self.assertEqual(a.balance, 50000000)
        self.assertEqual(a.payouts[0]["trader_usd"], 800)

    def test_censored_open_position_is_not_liquidated_or_counted_closed(self):
        a = self.account(standalone=True)
        at = a.start + 8 * HOUR
        t = trade(at, "EURUSD")
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at, 1))
        r = a.dump()
        self.assertEqual(r["closed_trades"], 0)
        self.assertEqual(len(r["open_positions"]), 1)
        self.assertTrue(r["cash_bridge_verified"])

    def test_scope_calendar_carries_into_2026_and_clamps_holiday(self):
        c = Calendar(dict(events=[dict(day="2025-11-28", kind="EARLY", flat_utc="17:00")]),
                     stamp("2026-10-14"))
        self.assertEqual(c.deadline(stamp("2025-11-28T09:00"))[0], stamp("2025-11-28T17:00"))
        self.assertEqual(c.deadline(stamp("2026-10-09T09:00"))[0], stamp("2026-10-09T20:30"))
        self.assertTrue(c.allowed(stamp("2026-10-13T09:00")))

    def test_m1_scenarios_are_labeled_different_orders_without_ask_zero(self):
        b = np.array([(stamp("2025-01-02"), 2000, 2020, 1980, 2005, 0, 0, 0, 0)], dtype=BAR)
        a = scenario(b, spread=3)
        other = scenario(b, "OPEN_HIGH_LOW_CLOSE", spread=3)
        self.assertEqual(a["b"].tolist(), [2000, 1980, 2020, 2005])
        self.assertEqual(other["b"].tolist(), [2000, 2020, 1980, 2005])
        self.assertTrue(np.all(a["a"] - a["b"] == 3))
        self.assertTrue(np.all(np.diff(a["t"]) > 0))

    def test_prague_reset_retains_dst_in_2025(self):
        c = Calendar(dict(events=[]), stamp("2026-10-14"))
        events = dict((at, kind) for at, kind in clocks(
            stamp("2025-03-30"), stamp("2025-04-01"), c) if kind == "reset")
        self.assertIn(stamp("2025-03-30T22:00"), events)
        self.assertIn(stamp("2025-03-31T22:00"), events)

    def test_reference_rejects_below_minimum_lot_without_changing_stop_or_risk(self):
        a = ReferenceAccount(stamp("2025-01-01"), stamp("2027-01-01"), "SYM_FLAT", fixed_risk=125)
        at = a.start + 8 * HOUR
        t = trade(at)
        t["stop_units"] = t["entry_price_units"] - 251617
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at))
        self.assertFalse(a.accepted)
        self.assertEqual(a.rejected["LOT_GRID_MIN_MAX"], 1)
        self.assertEqual(t["stop_units"], t["entry_price_units"] - 251617)

    def test_missing_scheduled_exit_censors_before_future_gain_is_counted(self):
        a = MeasuredHarvest(stamp("2025-01-01"), stamp("2027-01-01"), "SYM_FLAT",
                            rolling=True, standalone=True)
        at = a.start + 8 * HOUR
        t = dict(trade(at), reason="ENDPOINT_UNKNOWN_OPEN", deadline_msc=at + HOUR)
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at))
        before = a.balance
        a.check(at + HOUR, 999999999)
        a.action("session_flat", at + 2 * HOUR, None, [t], quote(at + 2 * HOUR, gold=4000000))
        self.assertEqual(a.balance, before)
        self.assertFalse(a.payouts)
        self.assertEqual(a.dump()["status"], "DATA_PATH_CENSORED")
        self.assertLess(a.peak, 51000000)

    def test_unknown_exit_that_was_liquidated_earlier_does_not_censor(self):
        a = MeasuredHarvest(stamp("2025-01-01"), stamp("2027-01-01"), "SYM_FLAT",
                            rolling=True, standalone=True)
        at = a.start + 8 * HOUR
        t = dict(trade(at), reason="ENDPOINT_UNKNOWN_OPEN", deadline_msc=at + HOUR)
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at))
        a.liquidate(at + 1, 0, [t], quote(at + 1), "TEST_EARLY")
        self.assertFalse(a.censor(at + 2 * HOUR))


if __name__ == "__main__":
    unittest.main()
