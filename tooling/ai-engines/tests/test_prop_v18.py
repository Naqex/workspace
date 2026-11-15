from types import SimpleNamespace
import unittest
from unittest.mock import patch
import numpy as np
from prop_v18_costs import surcharge, independent_surcharge, FrictionAccount, FrictionOracle, cost_bindings
from prop_v18_blocks import BlockTape, STRIDE
from quant_core.prop_lifecycle_and_parity import simulate, bindings
from prop_v14_paths import build
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import SessionSchedule
import prop_v14_review as review


class V18Tests(unittest.TestCase):
    def test_actual_quantity_surcharge_matches_separate_Decimal_and_never_rounds_down(self):
        for asset, spread in (("XAUUSD", 300), ("EURUSD", 4)):
            t = dict(asset=asset, spread_units=spread)
            for q in (1, 3, 29, 107):
                for pct in (100, 125, 150):
                    a = surcharge(t, q, pct)
                    self.assertEqual(a, independent_surcharge(t, q, pct))
                    self.assertEqual(a % 10, 0)
            self.assertLess(surcharge(t, 29, 125), surcharge(t, 29, 150))
        with self.assertRaises(ValueError):
            surcharge(t, 1, 110)

    def test_live_fee_reserve_floating_and_cash_match_own_oracle(self):
        from test_sl_active_kernel import fixture
        b, m = fixture([(100, 101, 99, 100), (100, 104, 99, 103), (103, 108, 101, 107)])
        m.update(asset="XAUUSD", _index=GapAwarePathIndex(b, asset="XAUUSD", schedule=SessionSchedule([])))
        trades, readers, missing = build({"XAUUSD|F3:test|DAY|P0": m}, "OPEN_LOW_HIGH_CLOSE",
                                         {"XAUUSD": b, "EURUSD": b})
        self.assertEqual(missing, [])
        t = trades[0]
        t["spread_units"] = int(b["ao"][0]) - int(b["bo"][0])
        first, end = int(b["t"][0]), int(b["t"][-1]) + 60000
        results = []
        for pct in (100, 125, 150):
            a = FrictionAccount(first, end, "SYM_FLAT", rolling=True, friction_pct=pct)
            with cost_bindings(pct):
                rows = simulate(trades, readers, [a], first, end, SimpleNamespace(events={}))
                with bindings(review, V14LedgerOracle=FrictionOracle):
                    checked = review.audit_accounts(rows, trades, readers, SimpleNamespace(events={}), first, end)
            self.assertEqual(checked[0]["entries"], 1)
            results.append(rows[0]["net_usd"])
        self.assertGreater(results[0], results[1])
        self.assertGreater(results[1], results[2])

    def test_block_timestamp_shift_repeated_trade_ids_are_disjoint(self):
        t = dict(decision_msc=10, entry_msc=11, exit_msc=20, deadline_msc=25, activation_time=None)
        tape = BlockTape.__new__(BlockTape)
        tape.blocks = [dict(trades=[t])]
        first = tape.prepared(0, 100, 0)
        second = tape.prepared(0, 200, 1)
        self.assertEqual(first[0]["entry_msc"], 111)
        self.assertEqual(second[STRIDE]["entry_msc"], 211)
        self.assertEqual(first[0]["deadline_msc"], 125)
        self.assertIsNone(second[STRIDE]["activation_time"])
        self.assertEqual(t["entry_msc"], 11)

    def test_copied_prague_reset_clock_is_not_replaced_by_UTC_midnight(self):
        tape = BlockTape.__new__(BlockTape)
        tape.blocks = [dict(first=0, end=86400000, trades=[], operations=[
            dict(kind="action", at=22 * 3600000, precheck=False,
                 quote={"t": 21 * 3600000}, actions=[["reset", None]])])]
        calls = []
        class Account:
            breach = None
            active = {}
            end = 2 * 86400000
            def action(self, kind, at, i, trades, quote):
                calls.append((kind, at, quote["t"]))
        tape.walk(0, 86400000, 0, [Account()])
        self.assertEqual(calls, [("reset", 46 * 3600000, 45 * 3600000)])

    def test_same_quote_multi_exit_settles_reward_before_new_entry(self):
        from prop_v18_audit import audit_path
        tape = BlockTape.__new__(BlockTape)
        trades = [dict(asset="XAUUSD", exit_quote_index=7, entry_msc=10, exit_msc=20)
                  for _ in range(3)]
        quote = dict(t=10, src=0, ordinal=7)
        tape.blocks = [dict(first=0, end=100, trades=trades, operations=[
            dict(kind="action", at=10, precheck=True, quote=quote, actions=[["entry", 0], ["entry", 1]]),
            dict(kind="action", at=20, precheck=True, quote=dict(quote, t=20),
                 actions=[["exit", 0], ["exit", 1], ["entry", 2]])])]
        expected = dict(start_msc=0, end_msc=100, phase_passes=[], payouts=[dict(at=20)],
                        closed=[dict(trade=0, at=20), dict(trade=1, at=20)])
        calls = []
        class OrderingOracle:
            breach = None
            def __init__(self, *args):
                self.open = {}
            def point(self, *args):
                pass
            def action(self, kind, i, at, quote, extra=None):
                if kind == "entry":
                    self.open[i] = 1
                elif kind == "exit":
                    self.open.pop(i)
                elif kind == "reward" and self.open:
                    raise AssertionError("reward_before_all_exits")
                calls.append((kind, i))
            def finish(self):
                return dict(passed=True)
        with patch("prop_v18_audit.FrictionOracle", OrderingOracle):
            self.assertTrue(audit_path(tape, [(0, 0)], expected)["passed"])
        self.assertEqual(calls[-4:], [("exit", 0), ("exit", 1), ("reward", None), ("entry", 2)])


if __name__ == "__main__":
    unittest.main()
