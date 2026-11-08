from datetime import datetime,timezone
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nasdaq_cash_calendar as calendar


class CashCalendarTests(unittest.TestCase):
    def test_registered_role_census_regular_and_halfdays(self):
        for role,count,early in [('warmup-2019',40,2),('development-2019',252,3),('warmup-2022',43,1),('development-2022',251,1)]:
            sessions=calendar.sessions_for(role)
            with self.subTest(role=role):
                self.assertEqual(len(sessions),count)
                self.assertEqual(sum(len(v)==210 for v in sessions.values()),early)
                self.assertTrue(all(len(v) in (210,390) for v in sessions.values()))
                self.assertEqual(list(sessions),sorted(sessions))

    def test_mourning_and_juneteenth_not_misclassified_as_feed_loss(self):
        self.assertNotIn('2018-12-05',calendar.sessions_for('warmup-2019'))
        self.assertNotIn('2022-06-20',calendar.sessions_for('development-2022'))
        # Saturday Jan1/2022 was not observed on Friday Dec31/2021 by this cash-calendar proxy.
        self.assertEqual(len(calendar.sessions_for('warmup-2022')['2021-12-31']),390)

    def test_halfday_and_DST_UTC_boundaries(self):
        sessions=calendar.sessions_for('development-2019')
        utc=lambda t:datetime.fromtimestamp(t/1000,timezone.utc)
        self.assertEqual((utc(sessions['2019-01-02'][0]).hour,utc(sessions['2019-01-02'][0]).minute),(14,30))
        self.assertEqual((utc(sessions['2019-07-03'][0]).hour,utc(sessions['2019-07-03'][-1]+60000).hour),(13,17))
        self.assertEqual(utc(sessions['2019-12-24'][-1]+60000).hour,18)

    def test_calendar_returns_independent_data_and_has_no_authority(self):
        c=calendar.calendar_for(2022);c['holidays'].append('2022-01-03')
        self.assertNotIn('2022-01-03',calendar.calendar_for(2022)['holidays'])
        self.assertFalse(c['broker_verified'])
        with self.assertRaises(ValueError):calendar.calendar_for(2025)
        with self.assertRaises(ValueError):calendar.sessions_for('development-2025')


if __name__=='__main__':unittest.main()
