from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from local_session_probe import bind_core, clocks, endpoint, event, retained, summarize
from fixing_clock_probe import dates

bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')


def quote(t,n,bid='1.10000',ask='1.10010'):
    return dict(time_msc=t+1,sequence=n,bid=bid,ask=ask)


def fixture(day='2019-03-15'):
    c=clocks(day)
    return event(day,dict(eu_open=quote(c['eu_open'],1),us_open=quote(c['us_open'],10),
        us_close=quote(c['us_close'],20,'1.10100','1.10110')))


class SessionProbeTests(unittest.TestCase):
    def test_buy_sell_costs_match_hand_calculation(self):
        got=fixture()['views']
        self.assertEqual(D(got['primary_us_buy']['outcomes']['reference']['net_usd_per_standard_lot']),D('85.00'))
        self.assertEqual(D(got['primary_us_buy']['outcomes']['stress']['net_usd_per_standard_lot']),D('81.00'))
        self.assertEqual(D(got['us_opposite_control']['outcomes']['reference']['net_usd_per_standard_lot']),D('-115.00'))
        self.assertEqual(D(got['us_opposite_control']['outcomes']['stress']['net_usd_per_standard_lot']),D('-119.00'))

    def test_unchanged_bid_ask_still_pays_spread_and_fees(self):
        c=clocks('2019-01-04');got=event('2019-01-04',{k:quote(t,n) for n,(k,t) in enumerate(c.items(),1)})
        for name in ('primary_us_buy','us_opposite_control'):
            self.assertEqual(D(got['views'][name]['outcomes']['reference']['net_pips']),D('-1.50'))

    def test_dst_changes_europe_us_overlap_but_not_eight_hour_us_leg(self):
        normal,unequal=clocks('2019-04-01'),clocks('2019-03-15')
        self.assertEqual(normal['us_open']-normal['eu_open'],6*3600000)
        self.assertEqual(unequal['us_open']-unequal['eu_open'],5*3600000)
        for c in (normal,unequal,clocks('2022-10-31')):
            self.assertEqual(c['us_close']-c['us_open'],8*3600000)
        with self.assertRaises(ValueError):clocks('2019-03-16')

    def test_missing_late_endpoints_preserved_not_zero_filled(self):
        c=clocks('2019-01-04')
        for end in (None,quote(c['us_close']+60000,20)):
            got=event('2019-01-04',dict(eu_open=None,us_open=quote(c['us_open'],10),us_close=end))
            self.assertEqual(got['views']['primary_us_buy']['status'],'missing_or_late_exit')
            self.assertEqual(got['views']['primary_us_buy']['outcomes'],{})
            self.assertEqual(got['views']['eu_sell_context']['status'],'missing_or_late_entry')

    def test_reversed_source_sequence_rejected(self):
        got=fixture();bad=deepcopy(got['quotes']);bad['us_close']['sequence']=9
        with self.assertRaises(ValueError):event(got['day'],bad)

    def test_endpoint_checks_grid_hour_and_whole_target(self):
        h=3600000;index={h:NS(first_time_msc=h+1,first_sequence=1,bid=(D('1.1'),),ask=(D('1.1001'),))}
        self.assertEqual(endpoint(index,h)['sequence'],1)
        self.assertIsNone(endpoint({},h))
        with self.assertRaises(ValueError):endpoint(index,h+1)
        index[h].ask=(D('1.100101'),)
        with self.assertRaises(ValueError):endpoint(index,h)
        index[h].ask=(D('1.1001'),);index[h].first_time_msc=h-1
        with self.assertRaises(ValueError):endpoint(index,h)

    def test_summary_requires_full_denominator_and_preserves_all_missing(self):
        events=[event(day,{}) for day in dates(2019)]
        summary=summarize(events,2019)
        row=summary['rows'][0]
        self.assertEqual((row['all_dates'],row['resolved'],len(row['unavailable_dates'])),(261,0,261))
        self.assertIsNone(row['net_pips_sum'])
        with self.assertRaises(ValueError):summarize(events+[events[0]],2019)

    def test_context_cannot_rescue_negative_primary_or_missing_registered_year(self):
        years=[dict(rows=[dict(year=y,view='primary_us_buy',scenario='stress',net_pips_sum='1',resolved=250),
                         dict(year=y,view='eu_sell_context',scenario='stress',net_pips_sum='999',resolved=250)])
               for y in (2019,2022)]
        self.assertTrue(retained(years))
        years[1]['rows'][0]['net_pips_sum']='-1';self.assertFalse(retained(years))
        with self.assertRaises(ValueError):retained(years[:1])


if __name__=='__main__':unittest.main()
