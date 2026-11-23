from unittest import TestCase

import numpy as np

import pass12_us500_ny_orb as index
import pass12_usdjpy_forensic as jpy


def quotes():
    return np.tile([100.,100.,100.,100.,100.5,100.5,100.5,100.5],(386,1))


class Us500Tests(TestCase):
    def test_nyse_calendar_respects_dst_and_skips_half_day(self):
        days, _ = index.calendar(2024)
        self.assertEqual(days["2024-03-11"]-days["2024-03-08"],3*86400-3600)
        self.assertNotIn("2024-11-29",days)

    def test_quote_sides_fade_and_horizons(self):
        offsets=np.arange(386)
        values=quotes()
        values[0,5], values[0,2] = 102.,98.
        values[90,[0,1,2,3]]=102.
        values[90,[4,5,6,7]]=102.5
        values[-1,[0,4]]=106.,106.5
        status,event=index.first_signal(offsets,values)
        self.assertEqual(status,"first_touch")
        self.assertEqual((event["entry_price"],event["stop"]),(102.5,98.))
        rows=index.raw_marks("2024-01-02",0,offsets,values,event)
        clean=next(r for r in rows if r["horizon"]=="hard_flat" and r["fee"]==index.HIGH)
        self.assertEqual((clean["net"],clean["fade"]),(2.,-6.))
        self.assertTrue(all(r["exit"]<=385*60 for r in rows))

    def test_same_bar_dual_and_opposite_stop(self):
        offsets=np.arange(386)
        values=quotes()
        values[0,5],values[0,2]=102.,98.
        values[60,[5,2]]=102.,98.
        self.assertEqual(index.first_signal(offsets,values),("dual_touch",None))
        values[60,2]=99.
        _, fill=index.first_signal(offsets,values)
        values[61,[0,2]]=97.
        self.assertEqual(index.stop_event(values,fill),(61,97.,True,"SL_GAP_OR_TOUCH"))

    def test_near_entry_gap_remains_unavailable(self):
        values=quotes()
        values[0,5], values[0,2]=102.,98.
        values[62,5]=102.
        offsets=np.delete(np.arange(386),61)
        self.assertEqual(index.classify(offsets,values[offsets])[0],"A_unreplayable")


class UsdJpyTests(TestCase):
    def test_friction_uses_entry_spread_and_conversion(self):
        self.assertAlmostEqual(jpy.estimated_cost(150.,150.004,.2),
                               100*(.004+5*150.002/100000+.009)/.2)
        self.assertEqual(jpy.entry_bucket(7),"07:00–09:59")

    def test_longest_episode_is_distinct_from_deepest(self):
        times=np.array([1,2,4,5,6,7,20,21])
        points=np.array([0,10,0,10,18,17,17,19])
        reports=jpy.path_intervals(times,points)
        self.assertEqual((reports["peak_dd"]["start"],reports["peak_dd"]["end"]),(2,4))
        self.assertEqual((reports["underwater"]["start"],reports["underwater"]["end"]),(6,21))
        censored=jpy.path_intervals(times[:-1],points[:-1])
        self.assertTrue(censored["underwater"]["censored"])
