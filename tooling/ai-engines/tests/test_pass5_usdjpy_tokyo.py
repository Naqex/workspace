from datetime import datetime, timezone
import unittest
from pathlib import Path
from unittest.mock import patch

import numpy as np
import pyarrow as pa

from pass5_usdjpy_tokyo import Bar, CLOCK, Costs, HOUR, PIP, STOP, first_touch, hard_flat, load_sealed, pnl, run_day, sl_trade, wall_to_utc


def ts(stamp):
    return int(datetime.fromisoformat(stamp).replace(tzinfo=timezone.utc).timestamp())


class TokyoBoxTests(unittest.TestCase):
    def setUp(self):
        self.costs = Costs(.30, 5., 100000.)

    def test_us_server_and_european_cutoff_differ_in_march_gap(self):
        stamp = ts('2024-03-12T03:00:00')
        self.assertEqual(int(wall_to_utc(stamp).timestamp()), ts('2024-03-12T00:00:00'))
        self.assertEqual(hard_flat(wall_to_utc(stamp)), ts('2024-03-12T16:00:00'))
        self.assertEqual(hard_flat(datetime(2024,4,2)), ts('2024-04-02T15:00:00'))

    def test_dual_touch_first_and_open_gap(self):
        both = Bar(150.,150.2,149.8,150.)
        up_gap = Bar(150.20,150.21,150.15,150.17)
        self.assertEqual(first_touch([(20,both)],150.10,149.90,self.costs),
                         ('ambiguous_first_touch',None))
        status, (at,side,mid) = first_touch([(20,up_gap),(21,both)],150.10,149.90,self.costs)
        self.assertEqual((status,at,side),('event',20,1))
        self.assertAlmostEqual(mid,150.2015)

    def test_paired_money_oracle_spread_paid_once(self):
        buy = pnl(150.,150.2,1,self.costs)
        sell = pnl(150.,150.2,-1,self.costs)
        self.assertAlmostEqual(buy['gross'],20000/150.2)
        self.assertAlmostEqual(buy['cost'],700/150.2+5)
        self.assertAlmostEqual(buy['net']+sell['net'],-2*buy['cost'])
        self.assertAlmostEqual(buy['gross']+sell['gross'],0.)

    def test_box_excludes_trigger_bar_and_common_cohort_rejects_one_endpoint_gap(self):
        day = ts('2024-03-12T00:00:00')
        neutral = Bar(150.,150.10,149.90,150.)
        after = Bar(150.01,150.04,149.96,150.02)
        bars = {day+i*HOUR:(neutral if i<3 else after) for i in range(17)}
        bars[day+3*HOUR]=Bar(150.01,150.40,149.97,150.02)
        empty = np.array([])
        status,dual,event = run_day(day,bars,empty,empty,self.costs)
        self.assertEqual((status,dual,event['side']),('valued',False,1))
        self.assertAlmostEqual(event['width_pips'],.20/PIP)
        self.assertEqual(event['entry_proxy_utc'],'2024-03-12T04:00:00+00:00')
        self.assertEqual(event['markouts']['8h']['exit_at'],'2024-03-12T12:00:00+00:00')
        del bars[day+12*HOUR]
        self.assertEqual(run_day(day,bars,empty,empty,self.costs),('missing_markout_path',False,None))

    def test_only_last_completed_daily_atr_is_visible(self):
        day = ts('2024-04-02T00:00:00')
        base = Bar(150.,150.10,149.90,150.)
        refs = {day+i*HOUR:base for i in range(17)}
        refs[day+3*HOUR]=Bar(150.01,150.15,149.97,150.02)
        at = np.array([day-2*HOUR,day+4*HOUR])
        atr = np.array([.5,999.])
        event = run_day(day,refs,at,atr,self.costs)[2]
        self.assertAlmostEqual(event['width_over_atr'],.4)


    def test_sl_is_activated_on_opposite_edge_and_gap_uses_first_quote(self):
        day = ts('2024-04-02T00:00:00')
        bars = {day+i*HOUR:Bar(150.,150.10,149.90,150.) for i in range(19)}
        bars[day+3*HOUR]=Bar(150.01,150.30,149.97,150.02)
        event = run_day(day,bars,np.array([]),np.array([]),self.costs)[2]
        bars[day+4*HOUR]=Bar(149.75,149.82,149.59,149.70)
        row = sl_trade(event,bars,self.costs)
        self.assertEqual(row['reason'],'SL_GAP_OR_TOUCH')
        self.assertEqual(row['exit_proxy'],'2024-04-02T04:00:00+00:00')
        self.assertLess(row['net_R'],-1.)
        self.assertIsNone(row['winner_label'])

    def test_rejects_holdout_clock_before_requesting_ohlc(self):
        binding = dict(development_file='USDJPY-H1.parquet',
                       development_sha256='expected',development_rows=2)
        clock_payload = pa.table({CLOCK: [STOP-HOUR,STOP]})
        with (patch('pass5_usdjpy_tokyo.sha',return_value='expected'),
              patch('pass5_usdjpy_tokyo.pq.read_table',return_value=clock_payload) as source):
            with self.assertRaisesRegex(ValueError,'Invalid sealed clock'):
                load_sealed(Path('development'),'H1',binding)
            source.assert_called_once_with(Path('development/USDJPY-H1.parquet'),columns=[CLOCK])
