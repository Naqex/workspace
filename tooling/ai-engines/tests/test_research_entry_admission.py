from datetime import datetime, timezone
import unittest
from zoneinfo import ZoneInfo

from quant_core.research_entry_admission import hard_flat_entry_rejection


def utc(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp() * 1000)


class HardFlatEntryTests(unittest.TestCase):
    def test_cutoff_and_reopen_are_half_open(self):
        flat = utc("2019-12-27T20:30:00")
        reopen = utc("2019-12-29T22:00:00")
        windows = [(flat, reopen)]
        self.assertIsNone(hard_flat_entry_rejection(flat - 2, flat - 1, windows))
        self.assertEqual(hard_flat_entry_rejection(flat, flat, windows), "DECISION_IN_HARD_FLAT_WINDOW")
        self.assertEqual(hard_flat_entry_rejection(flat + 1, None, windows), "DECISION_IN_HARD_FLAT_WINDOW")
        self.assertEqual(hard_flat_entry_rejection(flat - 1, flat, windows), "ENTRY_QUOTE_CROSSES_HARD_FLAT")
        self.assertEqual(hard_flat_entry_rejection(flat - 1, reopen, windows), "ENTRY_QUOTE_CROSSES_HARD_FLAT")
        self.assertEqual(hard_flat_entry_rejection(reopen - 1, reopen, windows), "DECISION_IN_HARD_FLAT_WINDOW")
        self.assertIsNone(hard_flat_entry_rejection(reopen, reopen + 1, windows))

    def test_dst_and_asset_specific_reopen(self):
        ny = ZoneInfo("America/New_York")
        for sunday, fx_utc in (("2019-12-29", "22:00:00"), ("2019-08-25", "21:00:00")):
            fx_local = datetime.fromisoformat(sunday + "T17:00:00").replace(tzinfo=ny)
            fx = int(fx_local.timestamp() * 1000)
            futures = int(fx_local.replace(hour=18).timestamp() * 1000)
            flat = fx - 48 * 3600000
            self.assertEqual(fx, utc(sunday + "T" + fx_utc))
            self.assertIsNone(hard_flat_entry_rejection(fx, fx, [(flat, fx)]))
            self.assertEqual(hard_flat_entry_rejection(fx, fx, [(flat, futures)]), "DECISION_IN_HARD_FLAT_WINDOW")

    def test_holiday_requires_a_configured_reopen_and_swing_stays_opt_in(self):
        early = utc("2019-12-24T16:58:00")
        resume = utc("2019-12-26T00:00:00")
        self.assertIsNone(hard_flat_entry_rejection(early, early, []))
        self.assertEqual(hard_flat_entry_rejection(early, early, [(early, None)]), "HARD_FLAT_REOPEN_UNKNOWN")
        self.assertEqual(hard_flat_entry_rejection(resume, resume, [(early, None)]), "HARD_FLAT_REOPEN_UNKNOWN")
        self.assertIsNone(hard_flat_entry_rejection(resume, resume, [(early, resume)]))

    def test_invalid_clock_or_window_is_rejected(self):
        with self.assertRaisesRegex(ValueError, "entry_quote_precedes_decision"):
            hard_flat_entry_rejection(10, 9, [])
        with self.assertRaisesRegex(ValueError, "invalid_hard_flat_window"):
            hard_flat_entry_rejection(10, 10, [(10, 10)])
