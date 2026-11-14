from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_campaign_accounts import Account
from prop_campaign_source import HOUR, stamp


def trade():
    at = stamp("2023-06-20T08:00:00")
    return dict(
        entry_msc=at, deadline_msc=at + 48 * HOUR,
        entry_price_units=2000000, stop_units=1990000,
        side="BUY", exit_msc=at + HOUR, exit_price_units=1990000,
    )


class FundingReserveTests(unittest.TestCase):
    def test_reserve_does_not_read_future_exit_time_or_price(self):
        row = trade()
        account = Account(0, 10**15, "ASYM_FLAT")
        expected = account.reserve_floor([row], 0, 10, 0)
        changed = dict(row, exit_msc=row["entry_msc"] + 900 * HOUR,
                       exit_price_units=9999999)
        self.assertEqual(account.reserve_floor([changed], 0, 10, 0), expected)
        del changed["exit_msc"]
        del changed["exit_price_units"]
        self.assertEqual(account.reserve_floor([changed], 0, 10, 0), expected)

    def test_known_deadline_includes_wednesday_triple_funding(self):
        row = trade()
        early = dict(row, deadline_msc=row["entry_msc"] + 12 * HOUR)
        account = Account(0, 10**15, "SYM_FLAT")
        difference = (
            account.reserve_floor([early], 0, 10, 0)
            - account.reserve_floor([row], 0, 10, 0)
        )
        self.assertEqual(difference, 16000)  # $0.40/oz * 10oz * (1 + 3)

    def test_missing_or_invalid_known_deadline_fails_closed(self):
        row = trade()
        account = Account(0, 10**15, "SYM_FLAT")
        for deadline in (None, row["entry_msc"] - 1, "tomorrow"):
            with self.assertRaisesRegex(ValueError, "prelocked_funding_horizon"):
                account.reserve_floor([dict(row, deadline_msc=deadline)], 0, 10, 0)


if __name__ == "__main__":
    unittest.main()
