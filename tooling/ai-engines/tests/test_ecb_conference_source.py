from datetime import datetime,timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import ecb_conference_source as source


class EcbSourceTests(unittest.TestCase):
    def test_winter_summer_and_historical_clock_change(self):
        expected={'2019-01-24':('13:30','14:50'),'2019-09-12':('12:30','13:50'),
                  '2022-02-03':('13:30','14:50'),'2022-09-08':('12:45','14:05')}
        fmt=lambda t:datetime.fromtimestamp(t/1000,timezone.utc).strftime('%H:%M')
        for day,(start,decision) in expected.items():
            r=source.roles(day)
            self.assertEqual((fmt(r['conference_ms']),fmt(r['decision_ms'])),(start,decision))
        self.assertEqual(len(source.hours()),9)
        with self.assertRaises(ValueError):source.roles('2025-01-30')

    def test_halfopen_windows_same_ms_and_entry_expiry_inclusive(self):
        r=source.roles('2022-09-08');stamps=[]
        for lo,hi in (r['pre'],r['post']):
            stamps.extend(range(lo,hi,60000))
        stamps.extend((r['post'][1],r['entry_expiry_ms'],r['entry_expiry_ms']))
        v=source.availability(r['day'],sorted(stamps))
        self.assertEqual(v['post']['quotes'],10)
        self.assertTrue(v['admitted'])
        self.assertEqual(v['entry_locator_ms'],r['entry_expiry_ms'])
        v=source.availability(r['day'],[t+1 if t==r['entry_expiry_ms'] else t for t in sorted(stamps)])
        self.assertIsNone(v['entry_locator_ms'])

    def test_one_hole_allowed_two_holes_missing_boundary_reject(self):
        lo=0;stamps=list(range(0,600000,60000))
        self.assertTrue(source.window_coverage([t for t in stamps if t!=300000],lo,600000)['admitted'])
        self.assertFalse(source.window_coverage([t for t in stamps if t not in (300000,360000)],lo,600000)['admitted'])
        for boundary in (0,540000):
            self.assertFalse(source.window_coverage([t for t in stamps if t!=boundary],lo,600000)['admitted'])
        self.assertFalse(source.window_coverage([],lo,600000)['admitted'])

    def test_timestamps_are_ordered_and_do_not_substitute_next_window(self):
        for stamps in ([2,1],[-1],[True],[float('nan')]):
            with self.assertRaises(ValueError):source.window_coverage(stamps,0,600000)
        self.assertEqual(source.window_coverage([600000],0,600000)['quotes'],0)
        with self.assertRaises(ValueError):source.window_coverage([],0,600001)


if __name__=='__main__':unittest.main()
