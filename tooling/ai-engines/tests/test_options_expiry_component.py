from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import copy
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import index_noise_study as market
from nasdaq_h4_study import SCENARIOS
import options_expiry_component as study


def us_market(scenario):
    instrument,model=market.market(SCENARIOS[scenario][0],cost_scenario=market.FTMO_ZERO_COMMISSION)
    return instrument,model,SCENARIOS[scenario][1]


def quote(at,bid=100000):
    return dict(timestamp=at,wait_ms=0,source_ordinal=0,bid_units=bid,ask_units=bid+200)


def evaluate(s,entry=None,exit_at=None):
    return study.evaluate(s,entry,exit_at,market_function=us_market,cost_function=market.calculate_round_trip_cost)


class OptionsExpiryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        market.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_calendar_holiday_dst_and_registered_census(self):
        specs=study.schedule(2019)+study.schedule(2022)
        self.assertEqual((len(specs),len(study.hours())),(48,96))
        cases={(s['year'],s['month'],s['role']):s for s in specs}
        self.assertEqual(cases[2019,4,'expiry_week']['exit_day'],'2019-04-18')
        self.assertEqual(cases[2022,4,'expiry_week']['exit_day'],'2022-04-14')
        self.assertEqual(cases[2022,1,'expiry_week']['entry_day'],'2022-01-18')
        self.assertEqual(cases[2019,2,'expiry_week']['entry_day'],'2019-02-11')
        utc=lambda t:datetime.fromtimestamp(t/1000,timezone.utc).strftime('%H:%M')
        self.assertEqual(utc(cases[2019,1,'expiry_week']['entry_target_ms']),'14:31')
        self.assertEqual(utc(cases[2022,4,'expiry_week']['exit_target_ms']),'19:59')
        for year in (2025,2023,True):
            with self.assertRaises(ValueError):study.schedule(year)

    def test_quotes_wait_boundary_unknown_and_no_close_boundary_fill(self):
        s=study.schedule(2019)[0];at=s['entry_target_ms']
        q=quote(at+60000);q['wait_ms']=60000
        self.assertIsNotNone(study.checked_quote(q,at,s['exit_decision_ms']))
        q.update(timestamp=at+60001,wait_ms=60001)
        self.assertIsNone(study.checked_quote(q,at,s['exit_decision_ms']))
        for q in (quote(at-1),dict(quote(at),bid_units=True),dict(quote(at),ask_units=1)):
            with self.assertRaises(ValueError):study.checked_quote(q,at,s['exit_decision_ms'])
        q=quote(s['exit_session_close_ms']);q['wait_ms']=60000
        with self.assertRaises(ValueError):study.checked_quote(q,s['exit_target_ms'],s['exit_session_close_ms'])
        self.assertEqual(evaluate(s)['outcomes'],{})

    def test_cost_waterfall_with_funding_is_not_zero_commission_free_trade(self):
        s=study.schedule(2019)[0]
        r=evaluate(s,quote(s['entry_target_ms']),quote(s['exit_target_ms'],110000))
        v=r['outcomes']['stress'];c=v['costs']
        self.assertEqual(v['midpoint_gross_usd'],'10.000')
        self.assertEqual(v['embedded_spread_usd'],'0.200')
        self.assertEqual((D(str(c['commission_account'])),D(str(c['slippage_account']))),(D(0),D('1.50')))
        self.assertEqual((len(v['funding_events']),D(v['funding_usd'])),(4,D('.16')))
        self.assertEqual(D(v['net_usd_per_research_unit']),D('8.14'))
        self.assertEqual(D(v['midpoint_gross_usd'])-D(v['embedded_spread_usd'])-D(str(c['commission_account']))-D(str(c['slippage_account']))-D(v['funding_usd'])+D(v['rounding_residual_usd']),D(v['net_usd_per_research_unit']))

    def test_future_prices_do_not_change_calendar_or_scope(self):
        s=study.schedule(2022)[0];frozen=copy.deepcopy(s)
        evaluate(s,quote(s['entry_target_ms']),quote(s['exit_target_ms'],90000))
        self.assertEqual(s,frozen)
        for key,value in (('execution_authorized',True),('execution_authorized',0),('entry_target_ms',s['entry_target_ms']-60000),('role','chosen_after_outcome')):
            with self.assertRaises(ValueError):evaluate(dict(s,**{key:value}))

    def test_full_calendar_keeps_unknown_and_rejects_dropped_control(self):
        rows=[evaluate(s) for year in (2019,2022) for s in study.schedule(year)]
        summary=study.summarize(rows)
        self.assertFalse(summary['retained_for_temporal_review'])
        self.assertTrue(all(b['strict_net_usd_per_research_unit'] is None for b in summary['books']))
        self.assertTrue(all(b['resolved']==0 for b in summary['books']))
        with self.assertRaises(ValueError):study.summarize(rows[:-1])


if __name__=='__main__':unittest.main()
