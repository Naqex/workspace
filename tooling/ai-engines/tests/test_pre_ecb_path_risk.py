from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
from types import SimpleNamespace as NS
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from fixing_clock_probe import clocks
from pre_ecb_path_risk import common_rows, distribution, excursions, observed_path, HOUR


def fixture():
    event = dict(clocks=dict(entry=HOUR,exit_1400=3*HOUR),quotes=dict(
        entry=dict(time_msc=HOUR+1,sequence=1,bid='1.10000',ask='1.10010'),
        exit_1400=dict(time_msc=3*HOUR+1,sequence=5,bid='1.09890',ask='1.09900')))
    hours = {HOUR:NS(first_time_msc=HOUR+1,first_sequence=1,last_sequence=2,
                    bid=(D('1.10000'),),ask=tuple(map(D,('1.10010','1.10100','1.09900','1.1')))),
        2*HOUR:NS(first_sequence=3,last_sequence=4,ask=tuple(map(D,('1.1','1.10200','1.09800','1.1')))),
        3*HOUR:NS(first_time_msc=3*HOUR+1,first_sequence=5,last_sequence=6,
                    bid=(D('1.09890'),),ask=tuple(map(D,('1.09900','2.00000','.50000','1.1'))))}
    return event,hours


class PathRiskTests(unittest.TestCase):
    def test_sell_hand_example_costs_and_risk(self):
        got=excursions('1.1','1.098','1.102','.1')
        self.assertEqual(got,dict(mae_pips='20',mfe_pips='20',worst_reference_loss_usd='41/2',
            worst_stress_loss_usd='209/10',worst_reference_loss_R='41/50',worst_stress_loss_R='209/250'))

    def test_sell_uses_ask_and_excludes_future_in_endpoint_hour(self):
        event,hours=fixture();got=observed_path(event,hours,'.1')
        self.assertEqual((got['mae_pips'],got['mfe_pips']),('20','20'))
        self.assertEqual(got['observed_ticks'],5)
        # Spread gives immediate loss even when Bid does not change.
        self.assertEqual(excursions('1.1','1.1001','1.1001','.1')['mae_pips'],'1')

    def test_endpoint_quote_is_included(self):
        event,hours=fixture()
        event['quotes']['exit_1400']['ask']='1.103'
        hours[3*HOUR].ask=(D('1.103'),)*4
        self.assertEqual(observed_path(event,hours,'.1')['mae_pips'],'30')

    def test_missing_hour_is_unresolved_not_zero(self):
        event,hours=fixture();del hours[2*HOUR]
        got=observed_path(event,hours,'.1')
        self.assertEqual(got['status'],'unresolved_missing_observed_hour')
        self.assertNotIn('mae_pips',got)

    def test_source_quote_sequence_and_partial_window_rejected(self):
        for mutation in ('bid','sequence','late','partial'):
            event,hours=fixture()
            if mutation=='bid': event['quotes']['entry']['bid']='1.10001'
            if mutation=='sequence': hours[2*HOUR].first_sequence=4
            if mutation=='late': event['quotes']['entry']['time_msc']+=60001
            if mutation=='partial': event['clocks']['entry']+=1
            with self.subTest(mutation=mutation),self.assertRaises(ValueError):observed_path(event,hours,'.1')

    def test_dst_mismatch_weeks_are_whole_utc_hours(self):
        for day in ('2019-01-04','2019-03-15','2019-04-01','2022-10-31','2022-11-07'):
            got=clocks(day)
            self.assertEqual(got['entry']%HOUR,0);self.assertEqual(got['exit_1400']%HOUR,0)
            self.assertGreater(got['exit_1400'],got['entry'])
        self.assertNotEqual(clocks('2019-03-15')['exit_1400']-clocks('2019-03-15')['entry'],
                            clocks('2019-04-01')['exit_1400']-clocks('2019-04-01')['entry'])

    def test_invalid_price_quantity_and_nearest_rank(self):
        for q in ('0','-.1','.015','NaN'):
            with self.assertRaises(ValueError):excursions('1.1','1.09','1.11',q)
        with self.assertRaises(ValueError):excursions('1.1','1.12','1.11','.1')
        self.assertEqual(distribution([4,1,3,2]),dict(count=4,p50='2',p90='4',p95='4',max='4'))
        self.assertEqual(distribution([]),dict(count=0))

    def test_common_mask_costs_do_not_double_count(self):
        r=dict(day='2019-01-04',quantity='.1',entry_time_msc=1,entry_fill='1.1',endpoint_time_msc=2)
        books=[dict(year=2019,scenario=s,matched=[deepcopy(r)],excluded=[])
               for s in ('reference','cost-stress')]
        self.assertEqual(len(common_rows(dict(rows=books),2019)[0]),1)
        books[1]['matched'][0]['quantity']='.2'
        merged=common_rows(dict(rows=books),2019)[0]
        self.assertEqual(merged[0]['stress_quantity'],'.2')
        self.assertEqual(excursions('1.1','1.098','1.102','.1','.2')['worst_stress_loss_usd'],'209/5')
        books[1]['matched'][0]['day']='2019-01-07'
        with self.assertRaises(ValueError):common_rows(dict(rows=books),2019)


if __name__=='__main__':unittest.main()
