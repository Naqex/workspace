from pathlib import Path
import sys
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_v7_accounts import AuditAccount
from prop_v7_paths import reprice
from prop_v6_signals import Calendar
from prop_v7_common import START, END, HOUR, stamp, read, CALENDAR
from prop_campaign_source import DTYPE
from test_prop_v5 import trade, quote


class Reader:
    def __init__(self, rows):
        self.rows = np.array(rows, dtype=DTYPE)

    def endpoint(self, at):
        j = int(self.rows["t"].searchsorted(at))
        if j == len(self.rows) or self.rows["t"][j] - at > 60000:
            return None
        a = self.rows[j]
        return [int(a["t"]), int(a["b"]), int(a["a"]), j]

    def path(self, first, last):
        indices = np.flatnonzero((self.rows["t"] >= first) & (self.rows["t"] <= last))
        return self.rows[indices], indices


class V7Tests(unittest.TestCase):
    def test_independence_observed_closes_before_known17UTC_boundary(self):
        c = Calendar(read(CALENDAR), END)
        end, kind = c.deadline(stamp("2026-07-02T10:00"))
        self.assertEqual(end, stamp("2026-07-03T16:58"))
        self.assertEqual(kind, "HOLIDAY_FLAT")
        self.assertFalse(c.allowed(stamp("2026-07-03T16:59")))

    def test_historical_calendar_keeps_old_deadline(self):
        c = Calendar(read(CALENDAR), END)
        self.assertEqual(c.deadline(stamp("2023-11-24T10:00"))[0], stamp("2023-11-24T17:00"))

    def test_both_registered_risk_policies_and_throttles(self):
        for policy, risks in (("GOLD_V4", (200, 175, 125)), ("GOLD_SCALED", (250, 200, 150))):
            a = AuditAccount(START, END, "SYM_FLAT", rolling=True, policy=policy)
            for phase, risk in enumerate(risks, 1):
                a.phase = phase
                self.assertEqual(a.risk_request(50000000, "CORE", 1), risk)
                self.assertEqual(a.risk_request(47000000, "CORE", 1), 90)
                self.assertEqual(a.risk_request(48000000, "CORE", 1), min(risk, 150))
            self.assertEqual(a.internal_floor_milli, 46000000)
            self.assertEqual(a.open_cap_milli, 800000)

    def test_decommission_is_account_admission_not_erased_historical_data(self):
        at = START + 8 * HOUR
        t = trade(at, "EURUSD")
        a = AuditAccount(START, END, "SYM_FLAT", rolling=True, policy="GOLD_V4")
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at, 1))
        self.assertFalse(a.accepted)
        self.assertEqual(a.rejected["EURUSD_DECOMMISSIONED"], 1)
        self.assertEqual(t["asset"], "EURUSD")

    def test_counterfactual_retains_EUR(self):
        at = START + 8 * HOUR
        t = trade(at, "EURUSD")
        a = AuditAccount(START, END, "SYM_FLAT", rolling=True, policy="COCORE_FIXED")
        a._trades = [t]
        a.action("entry", at, 0, [t], quote(at, 1))
        self.assertEqual(len(a.accepted), 1)

    def test_no_ratchet_appears_in_enhanced_policy(self):
        a = AuditAccount(START, END, "SYM_FLAT", rolling=True, policy="GOLD_SCALED")
        a.observe_policy(START, 55000000)
        self.assertFalse(a.ratchet)
        self.assertEqual(a.risk_request(55000000, "CORE", 1), 250)

    def test_calendar_fix_does_not_move_entry_or_stop(self):
        at = stamp("2026-07-02T10:00")
        end = stamp("2026-07-03T16:58")
        t = dict(trade(at), asset="XAUUSD", day="2026-07-02", reason="ENDPOINT_UNKNOWN_OPEN",
                 entry_quote_index=0, exit_quote_index=-1, exit_price_units=2100000)
        r = Reader([(at, 2000000, 2000100), (end, 2010000, 2010100)])
        out, changed = reprice([t], {"XAUUSD": r}, Calendar(read(CALENDAR), END))
        self.assertEqual(out[0]["exit_msc"], end)
        self.assertEqual(out[0]["entry_msc"], t["entry_msc"])
        self.assertEqual(out[0]["stop_units"], t["stop_units"])
        self.assertEqual(len(changed), 1)

    def test_missing_nonholiday_quote_stays_error(self):
        at = stamp("2026-07-02T10:00")
        t = dict(trade(at), asset="XAUUSD", day="2026-07-02", reason="ENDPOINT_UNKNOWN_OPEN",
                 exit_quote_index=-1, exit_price_units=2100000)
        with self.assertRaisesRegex(ValueError, "unresolved_registered_deadline"):
            reprice([t], {"XAUUSD": Reader([(at, 2000000, 2000100)])}, Calendar(read(CALENDAR), END))

    def test_stop_before_calendar_flat_remains_first_exit(self):
        at = stamp("2026-07-02T10:00")
        end = stamp("2026-07-03T16:58")
        t = dict(trade(at), asset="XAUUSD", day="2026-07-02", reason="ENDPOINT_UNKNOWN_OPEN",
                 entry_quote_index=0, exit_quote_index=-1, exit_price_units=2100000)
        r = Reader([(at, 2000000, 2000100), (at + HOUR, 1980000, 1980100),
                    (end, 2010000, 2010100)])
        out, _ = reprice([t], {"XAUUSD": r}, Calendar(read(CALENDAR), END))
        self.assertEqual(out[0]["reason"], "SL")
        self.assertEqual(out[0]["exit_msc"], at + HOUR)


if __name__ == "__main__":
    unittest.main()
