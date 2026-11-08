from copy import deepcopy
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import nasdaq_intraday_momentum_component as study
import nasdaq_h4_study as market
from test_index_close_momentum import fixture

ROOT=Path(__file__).resolve().parents[3]


def setup_case():
    sessions,pairs=fixture();day=next(reversed(sessions));stamps=sessions[day]
    for at,price in [(stamps[-29],100),(stamps[-1],110)]:
        for row,offset in zip(pairs[at],[D(0),D('.2')]):
            row.update(open=D(price)+offset,high=D(price)+offset+D(1),low=D(price)+offset-D(1),close=D(price)+offset)
    start=stamps[0]//study.DAY*study.DAY
    return sessions,pairs,day,stamps,start,start+study.DAY


def run(sessions,pairs,start,end):
    return study.evaluate(sessions,pairs,start=start,end=end,market_function=market.market,cost_function=market.calculate_round_trip_cost)


class NasdaqMomentumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):market.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_overnight_sign_causal_delay_bidask_cost_and_no_account(self):
        sessions,pairs,day,stamps,start,end=setup_case()
        row=run(sessions,pairs,start,end)['rows'][0]
        self.assertEqual(row['signal_side'],'BUY')
        self.assertEqual(row['signal_known_at_ms'],stamps[29]+60000)
        self.assertEqual(row['decision_ms'],stamps[-30])
        self.assertEqual(row['entry_ms'],stamps[-29])
        self.assertEqual(row['exit_ms'],stamps[-1])
        self.assertEqual(row['entry']['quote_timestamp_interval_ms'],[stamps[-29],stamps[-29]+60000])
        self.assertEqual(D(row['outcomes']['reference']['primary']['net_usd_per_research_unit']),D('9.30'))
        self.assertEqual(D(row['outcomes']['stress']['primary']['net_usd_per_research_unit']),D('8.30'))
        self.assertEqual(row['path_expected_minutes'],28)
        self.assertFalse(row['account_simulated']);self.assertFalse(row['execution_authorized'])

    def test_sell_uses_bid_entry_ask_exit_and_control_keeps_same_mask(self):
        sessions,pairs,day,stamps,start,end=setup_case()
        for row,offset in zip(pairs[stamps[29]],[D(0),D('.2')]):
            row.update(open=D(99)+offset,high=D(100)+offset,low=D(98)+offset,close=D(99)+offset)
        row=run(sessions,pairs,start,end)['rows'][0]
        self.assertEqual(row['signal_side'],'SELL')
        self.assertEqual(D(row['outcomes']['reference']['primary']['net_usd_per_research_unit']),D('-10.70'))
        self.assertEqual(D(row['outcomes']['reference']['always_long_control']['net_usd_per_research_unit']),D('9.30'))

    def test_halfday_missing_firsthalf_and_missing_previous_close_cannot_enter(self):
        for mode in ['halfday','firsthalf','previousclose']:
            sessions,pairs,day,stamps,start,end=setup_case()
            if mode=='halfday':sessions[day]=stamps[:210]
            elif mode=='firsthalf':del pairs[stamps[29]]
            else:del pairs[list(sessions.values())[-2][-1]]
            row=run(sessions,pairs,start,end)['rows'][0]
            self.assertFalse(row['planned_trade']);self.assertFalse(row['outcomes'])

    def test_future_missing_or_mutated_prices_do_not_remove_entry(self):
        sessions,pairs,day,stamps,start,end=setup_case()
        before=study.prepare(sessions,pairs,start=start,end=end)
        changed=deepcopy(pairs);del changed[stamps[-1]]
        self.assertEqual(study.prepare(sessions,changed,start=start,end=end),before)
        row=run(sessions,changed,start,end)['rows'][0]
        self.assertTrue(row['planned_trade']);self.assertEqual(row['status'],'unresolved_endpoint')
        self.assertFalse(row['outcomes'])

    def test_endpoint_missing_crossed_and_clock_grid(self):
        for mode in ['missing','crossed','clock','grid']:
            sessions,pairs,day,stamps,start,end=setup_case();at=stamps[-29]
            if mode=='missing':del pairs[at]
            elif mode=='crossed':pairs[at][1]['open']=D(99)
            elif mode=='clock':pairs[at][1]['timestamp']+=1
            else:pairs[at][1]['open']+=D('.0001')
            if mode in ['clock','grid']:
                with self.subTest(mode=mode),self.assertRaises(ValueError):run(sessions,pairs,start,end)
            else:
                row=run(sessions,pairs,start,end)['rows'][0]
                self.assertTrue(row['planned_trade']);self.assertEqual(row['status'],'unresolved_endpoint')
                self.assertFalse(row['outcomes'])

    def test_nasdaq_identity_and_holdout_guard(self):
        from types import SimpleNamespace
        sessions,pairs,day,stamps,start,end=setup_case()
        _,model,rate=market.market('reference')
        with self.assertRaisesRegex(ValueError,'geometry'):
            study.evaluate(sessions,pairs,start=start,end=end,market_function=lambda s:(SimpleNamespace(instrument_id='US500',contract_size=1),model,rate),cost_function=market.calculate_round_trip_cost)
        with self.assertRaisesRegex(ValueError,'holdout'):
            study.prepare(sessions,pairs,start=start,end=1767225600000)

    def test_shared_observer_preserves_H1_default_and_rejects_unregistered_frame(self):
        from fomc_price_component import observation
        missing=observation(None,1000)
        self.assertEqual(missing['quote_timestamp_interval_ms'],[1000,1000+3600000])
        self.assertEqual(missing['basis'],'source_separate_side_H1_Open_proxy')
        self.assertEqual(missing['status'],'missing_exact_hour')
        with self.assertRaisesRegex(ValueError,'duration'):
            observation(None,0,duration_ms=300000)

    def test_dst_clock_is_from_calendar_not_fixed_utc_hour(self):
        from zoneinfo import ZoneInfo
        ny=ZoneInfo('America/New_York')
        for text,hour in [('2019-01-18',20),('2019-07-18',19)]:
            at=int(datetime.fromisoformat(text).replace(hour=9,minute=30,tzinfo=ny).timestamp()*1000)
            stamps=list(range(at,at+390*60000,60000))
            self.assertEqual(datetime.fromtimestamp(stamps[-29]/1000,timezone.utc).hour,hour)
            self.assertEqual(datetime.fromtimestamp(stamps[-29]/1000,timezone.utc).minute,31)

    def test_summary_gate_common_mask_and_denominators(self):
        sessions,pairs,day,stamps,start,end=setup_case();template=run(sessions,pairs,start,end)['rows'][0]
        expected={};rows=[]
        for year in [2019,2022]:
            expected[year]=[]
            for n in range(100):
                day=(datetime(year,1,1)+timedelta(days=n)).date().isoformat();expected[year].append(day)
                row=deepcopy(template);row.update(year=year,session=day)
                for scenario in study.SCENARIOS:
                    row['outcomes'][scenario]['primary']['net_usd_per_research_unit']='3'
                    row['outcomes'][scenario]['always_long_control']['net_usd_per_research_unit']='1'
                rows.append(row)
        self.assertTrue(study.summarize(rows,expected)['retained_for_further_research'])
        changed=deepcopy(rows)
        for i in range(3):changed[i]['outcomes']={};changed[i]['status']='unresolved_endpoint'
        result=study.summarize(changed,expected)
        self.assertFalse(result['retained_for_further_research'])
        primary=next(r for r in result['summary'] if r.get('year')==2019 and r.get('scenario')=='stress' and r['role']=='primary')
        control=next(r for r in result['summary'] if r.get('year')==2019 and r.get('scenario')=='stress' and r['role']=='always_long_control')
        self.assertEqual((primary['planned'],primary['resolved'],primary['unresolved']),(100,97,3))
        self.assertEqual(primary['resolved'],control['resolved'])
        for mode in ['missing','duplicate','authority']:
            changed=deepcopy(rows)
            if mode=='missing':changed.pop()
            elif mode=='duplicate':changed[-1]=deepcopy(changed[-2])
            else:changed[-1]['execution_authorized']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):study.summarize(changed,expected)


if __name__=='__main__':unittest.main()
