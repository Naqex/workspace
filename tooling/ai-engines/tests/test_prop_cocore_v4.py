from pathlib import Path
import sys
import unittest
from unittest.mock import patch
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_campaign_source import DAY, HOUR, stamp
from prop_portfolio_accounts import PortfolioAccount, JOINT
from prop_cocore_v4 import CoCoreAccount, MeasuredAccount
from prop_cocore_audit import third_gate
from prop_portfolio_review import CashOracle


class CoCoreTests(unittest.TestCase):
    def account(self, **kw):
        return CoCoreAccount(stamp("2022-01-01"), stamp("2024-01-01"),
                             "ASYM_FLAT", rolling=True, **kw)

    def test_equal_phase_risk_and_causal_throttle_boundaries(self):
        a = self.account()
        for phase, risk in ((1, 200), (2, 175), (3, 125)):
            a.phase = phase
            for role in ("CORE", "SATELLITE"):
                self.assertEqual(a.risk_request(48000001, role, 1), risk)
                self.assertEqual(a.risk_request(48000000, role, 1), min(risk, 150))
                self.assertEqual(a.risk_request(47000000, role, 1), 90)

    def test_standalone_reference_book_does_not_use_challenge_risk(self):
        a = CoCoreAccount(0, 10**15, "SYM_FLAT", fixed_risk=150)
        self.assertEqual(a.risk_request(50000000, "SATELLITE", 1), 150)

    def test_default_v3_policy_unchanged(self):
        a = PortfolioAccount(0, 10**15, "SYM_FLAT", rolling=True)
        self.assertEqual(a.reward_interval_days, 30)
        self.assertEqual(a.open_cap_milli, 500000)
        self.assertEqual(a.internal_floor_milli, 46500000)
        self.assertEqual(a.risk_request(50000000, "SATELLITE", 1), 100)
        self.assertEqual(a.risk_request(47000000, "CORE", 1), 90)

    def test_reward_day14_is_earliest_eligibility_full_debit(self):
        a = self.account()
        a.phase = 3
        a.funded_first = a.start
        a.balance += 100000
        a.reward(a.start + 14 * DAY - 1)
        self.assertFalse(a.payouts)
        a.reward(a.start + 14 * DAY)
        self.assertEqual(a.balance, 50000000)
        self.assertEqual(a.payouts[0]["trader_usd"], 80)
        self.assertEqual(a.payouts[0]["firm_usd"], 20)
        self.assertEqual(a.payouts[0]["gross_removed_usd"], 100)

    def test_positive_equity_while_position_open_is_not_withdrawable(self):
        a = self.account()
        a.phase = 3
        a.funded_first = a.start
        a.balance += 100000
        a.active = {0: (1, 125)}
        a.reward(a.start + 30 * DAY)
        self.assertFalse(a.payouts)

    def test_reward_repeat_clock_is_explicit_proxy_not_fixed_calendar(self):
        a = self.account()
        a.phase = 3
        a.funded_first = a.start
        a.balance += 20000
        a.reward(a.start + 20 * DAY)
        a.balance += 20000
        a.reward(a.start + 33 * DAY)
        self.assertEqual(len(a.payouts), 1)
        a.reward(a.start + 34 * DAY)
        self.assertEqual(len(a.payouts), 2)

    def test_30day_reward_control_and_unknown_schedule_rejected(self):
        a = self.account(reward_days=30)
        a.phase = 3
        a.funded_first = a.start
        a.balance += 20000
        a.reward(a.start + 14 * DAY)
        self.assertFalse(a.payouts)
        a.reward(a.start + 30 * DAY)
        self.assertEqual(len(a.payouts), 1)
        with self.assertRaises(ValueError):
            self.account(reward_days=7)

    def test_cash_posted_oracle_checks_day14_and_full_reward_debit(self):
        start = stamp("2022-01-01")
        expected = dict(start_msc=start, end_msc=start+40*DAY, accepted=[], closed=[])
        oracle = CashOracle(expected, [], "ASYM_FLAT", cocore=True, reward_days=14)
        oracle.phase = 3
        oracle.first_funded = start
        oracle.cash += 100000
        reward = dict(gross_removed_usd=100, trader_usd=80, firm_usd=20)
        with self.assertRaises(ValueError):
            oracle.action("reward", None, start+14*DAY-1, None, reward)
        oracle.action("reward", None, start+14*DAY, None, reward)
        self.assertEqual(oracle.cash, 50000000)
        self.assertEqual(oracle.reward_checks, 1)

    def test_new_cap_admits_three_200dollar_positions_without_hedge_netting(self):
        a = self.account()
        at = a.start + 8 * HOUR
        quote = np.zeros(1, dtype=JOINT)[0]
        quote["t"] = at
        quote["b0"] = 2000000
        quote["a0"] = 2000100
        quote["b1"] = 110000
        quote["a1"] = 110010
        trades = []
        for i in range(5):
            trades.append(dict(
                asset="XAUUSD", role="CORE", side="BUY",
                decision_msc=at + i * HOUR - 1, entry_msc=at + i * HOUR,
                entry_price_units=2000100, stop_units=1990100,
                deadline_msc=at + 48 * HOUR, exit_msc=at + 24 * HOUR,
                exit_price_units=2010000))
        for i in range(4):
            a.action("entry", at + i * HOUR, i, trades, quote)
        self.assertEqual(len(a.accepted), 4)
        a.action("entry", at + 4 * HOUR, 4, trades, quote)
        self.assertEqual(a.rejected["OPEN_STOP_RISK_1P6PCT_CAP"], 1)
        self.assertEqual(a.maximum_stop_exposure, 800000)

    def test_internal_floor_rejects_before_broker_static_limit(self):
        a = self.account()
        at = a.start + 8 * HOUR
        t = dict(asset="XAUUSD", role="CORE", side="BUY", decision_msc=at-1,
                 entry_msc=at, entry_price_units=2000000, stop_units=1990000,
                 deadline_msc=at + HOUR)
        q = np.zeros(1, dtype=JOINT)[0]
        q["t"] = at; q["b0"] = 2000000; q["a0"] = 2000100
        with patch.object(a, "reserve_floor", return_value=46000000):
            a.action("entry", at, 0, [t], q)
        self.assertEqual(a.rejected["INTERNAL_STATIC_8PCT_RESERVE"], 1)
        self.assertFalse(a.accepted)

    def test_third_sleeve_cannot_pass_with_h1_only_or_low_retention(self):
        c = dict(source_path_complete=False, cell=dict(asset="GBPUSD", horizon="DAY"),
                 funnel={y: dict(friction_pass_rate=.9, scale_ratio=.1)
                         for y in ("2022", "2023")},
                 models={"SYM_FLAT": dict(net_R={"2022": 2., "2023": 10.},
                                         correlation=dict(pooled=.1))})
        self.assertIn("SOURCE_PATH_INCOMPLETE_OR_H1_ONLY", third_gate(c, "SYM_FLAT", .1))
        c["source_path_complete"] = True
        c["funnel"]["2022"]["friction_pass_rate"] = .49
        self.assertIn("2022:FRICTION_RETENTION_LT50", third_gate(c, "SYM_FLAT", .1))

    def test_third_sleeve_must_be_uncorrelated_with_both_cores(self):
        c = dict(source_path_complete=True, cell=dict(asset="EURUSD", horizon="DAY"),
                 funnel={y: dict(friction_pass_rate=.9, scale_ratio=.1)
                         for y in ("2022", "2023")},
                 models={"SYM_FLAT": dict(net_R={"2022": 2., "2023": 10.},
                                         correlation=dict(pooled=.1))})
        self.assertIn("DUAL_CORRELATION_GATE", third_gate(c, "SYM_FLAT", .25))
        self.assertEqual(third_gate(c, "SYM_FLAT", .24), [])


if __name__ == "__main__":
    unittest.main()
