from pathlib import Path
import ast
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import independent_ledger_auditor as oracle
from test_sl_active_kernel import fixture
from quant_core.vectorized_sl_active_kernel import PathIndex, replay
from prop_campaign_source import stamp
from quant_core.vectorized_stage0_scanner import HOUR, DAY


class IndependentAuditorTests(unittest.TestCase):
    def test_oracle_imports_no_producer_or_quant_core_accounting(self):
        tree = ast.parse(Path(oracle.__file__).read_text())
        names = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
        self.assertFalse(any(n and ("quant_core" in n or n.startswith("prop_")) for n in names))

    def test_wednesday_triple_funding_and_asymmetric_short_are_independently_rounded(self):
        t = dict(symbol="XAUUSD", direction="SELL", entry_price="1900", exit_price="1890",
                 lots="0.13", entry_time=stamp("2023-03-08T21:00"), exit_time=stamp("2023-03-08T23:00"),
                 reason="HORIZON")
        value = oracle.cash_legs(t, "ASYM", dict(contract=100))
        self.assertEqual(str(value["swap"]), "-1.95")
        self.assertEqual(str(value["gross"]), "130.00")
        self.assertEqual(value["net"], value["gross"]-value["commission"]-value["slippage"]+value["swap"])

    def test_Prague_midnight_anchors_balance_not_floating_equity(self):
        entry, midnight = stamp("2023-03-27T21:00"), stamp("2023-03-27T22:00")
        trade = dict(symbol="XAUUSD", direction="BUY", entry_price="1900", exit_price="1880",
                     lots="1", entry_time=entry, exit_time=midnight+120000, reason="SL")
        points = [dict(at=entry, quotes={"XAUUSD": ("1900", "1900.1")}),
                  dict(at=midnight, quotes={"XAUUSD": ("1920", "1920.1")}),
                  dict(at=midnight+60000, quotes={"XAUUSD": ("1880", "1880.1")})]
        r = oracle.audit_equity([trade], points, {"XAUUSD": dict(contract=100)}, model="ASYM")
        self.assertEqual(r["worst_daily_usd"], "2045.00")
        self.assertFalse(r["daily_breach"])
        with self.assertRaisesRegex(ValueError, "midnight"):
            oracle.audit_equity([trade], [points[0], points[2]], {"XAUUSD": dict(contract=100)})

    def test_winter_reset_uses_23UTC_and_static_floor_does_not_reset(self):
        at, reset = stamp("2023-01-09T22:00"), stamp("2023-01-09T23:00")
        trade = dict(symbol="US500", direction="BUY", entry_price="4000", exit_price="3900",
                     lots="50", entry_time=at, exit_time=reset+120000, reason="SL")
        points = [dict(at=at, quotes={"US500": ("4000", "4001")}),
                  dict(at=reset, quotes={"US500": ("3940", "3941")}),
                  dict(at=reset+60000, quotes={"US500": ("3900", "3901")})]
        r = oracle.audit_equity([trade], points, {"US500": dict(contract=1)})
        self.assertTrue(r["daily_breach"]);self.assertTrue(r["static_breach"])

    def test_scalar_first_hit_detects_tampered_exit_and_matches_P1(self):
        b, m = fixture([(100, 120, 99, 118), (118, 119, 101, 102), (102, 103, 101, 102)])
        r = replay(PathIndex(b, asset="XAUUSD"), m, "P1")
        row = dict(symbol="XAUUSD", direction="BUY", entry_time=int(m["entry_at"][0]),
                   exit_time=int(r["exit_at"][0]), entry_price="100.1", exit_price=str(r["exit_price"][0]/1000),
                   sl_price="90", lots="1", reason=str(r["reason"][0]), mode="P1", horizon="24H",
                   protection_time=int(b["t"][r["activation_index"][0]])+60000)
        # Use the registered horizon and an observed protection exit before it.
        flats = [m["entry_at"][0]+4*DAY]
        spec = dict(contract=100, scale=1000, step=60000)
        self.assertTrue(oracle.audit_trade(row, (b["t"], b), spec, flats)["passed"])
        row["exit_price"] = "119"
        self.assertIn("MISSED_OR_WRONG_FIRST_HIT", oracle.audit_trade(row, (b["t"], b), spec, flats)["errors"])

    def test_Friday_and_US500_session_deadlines_are_calculated_without_core(self):
        at = stamp("2023-03-24T15:00");flat = stamp("2023-03-24T20:30")
        t = dict(symbol="US500", entry_time=at, horizon="FRIDAY")
        self.assertEqual(oracle.expected_deadline(t, [flat]), stamp("2023-03-24T20:00"))
