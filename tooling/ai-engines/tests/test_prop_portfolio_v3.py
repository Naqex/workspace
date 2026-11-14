from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_campaign_accounts import Account
from prop_campaign_source import HOUR, stamp
from prop_campaign_source import DAY
from prop_portfolio_regime import states, weight_at
from prop_portfolio_sources import deadline, merge_bars, BAR
import numpy as np


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

class DailyRegimeTests(unittest.TestCase):
    def test_future_daily_closes_do_not_change_earlier_weight(self):
        start = stamp("2021-01-01")
        rows = [dict(day=start+i*DAY,minutes=1440,close=2000000+i*100)
                for i in range(70)]
        at = start+60*DAY+8*HOUR
        old = weight_at(states(rows[:60]),at,"SELL")
        later = weight_at(states(rows),at,"SELL")
        self.assertEqual(old,later)
        self.assertEqual(old[0],0.5)
        self.assertLess(old[1]["known_at"],at)

    def test_partial_day_cannot_become_a_full_d1_close(self):
        start = stamp("2021-01-01")
        rows = [dict(day=start+i*DAY,minutes=1440,close=2000000+i*100)
                for i in range(60)]
        baseline=states(rows)
        rows.append(dict(day=start+60*DAY,minutes=720,close=9999999))
        self.assertEqual(states(rows),baseline)
        self.assertEqual(weight_at(baseline,start+70*DAY,"SELL"),(None,None))

class SourceClockTests(unittest.TestCase):
    def test_friday_exit_avoids_us500_summer_source_break(self):
        row=dict(asset="US500",horizon="48H")
        end,why=deadline(row,stamp("2022-07-29T12:00:00"))
        self.assertEqual(end,stamp("2022-07-29T20:00:00"))
        self.assertEqual(why,"SOURCE_BREAK_PRE_FLAT_1600_NY")
        end,_=deadline(row,stamp("2022-12-16T12:00:00"))
        self.assertEqual(end,stamp("2022-12-16T20:30:00"))

    def test_chunk_boundary_merges_same_minute_without_new_bar(self):
        one=np.array([(1000,10,12,9,11,11,13,10,12)],dtype=BAR)
        two=np.array([(1000,11,15,8,13,12,16,9,14)],dtype=BAR)
        rows=merge_bars([one,two])
        self.assertEqual(len(rows),1)
        self.assertEqual(tuple(rows[0]),(1000,10,15,8,13,11,16,9,14))


if __name__ == "__main__":
    unittest.main()
