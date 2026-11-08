from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import fomc_price_component as study
import nasdaq_h4_study as market

ROOT=Path(__file__).resolve().parents[3]

def fixture():
    specs=study.schedules([2019,2022]);pairs={}
    for spec in specs:
        for t in [spec['entry_ms'],spec['exit_ms']]:
            price=1000 if t==spec['entry_ms'] else 1010 if spec['role']=='primary' else 1005
            pairs[t]=tuple(dict(timestamp=t,open=D(price)+offset,high=D(price)+offset,low=D(price)+offset,close=D(price)+offset) for offset in [D(0),D('.2')])
    return specs,pairs

def run(specs,pairs):return study.evaluate(specs,pairs,market_function=market.market,cost_function=market.calculate_round_trip_cost)


class FomcComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):market.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_calendar_winter_summer_and_control_recomputes_DST(self):
        specs=study.schedules([2019,2022]);self.assertEqual(len(specs),32)
        get=lambda event,role:next(s for s in specs if s['event']==event and s['role']==role)
        from datetime import datetime,timezone
        winter=get('2019-01-30','primary');summer=get('2019-06-19','primary')
        self.assertEqual(datetime.fromtimestamp(winter['entry_ms']/1000,timezone.utc).hour,19)
        self.assertEqual(datetime.fromtimestamp(summer['entry_ms']/1000,timezone.utc).hour,18)
        a,b=get('2022-03-16','primary'),get('2022-03-16','matched_week_control')
        self.assertEqual(a['entry_ms']-b['entry_ms'],(7*24-1)*study.HOUR)
        self.assertTrue(all(s['exit_ms']-s['entry_ms']==23*study.HOUR for s in specs))
        for years in [[2025],[2019,2019],[]]:
            with self.subTest(years=years),self.assertRaises(ValueError):study.schedules(years)

    def test_fixed_calendar_future_publication_and_recipe_change_reject(self):
        specs,pairs=fixture()
        for field,value in [('calendar_publication_ms',specs[0]['entry_ms']+1),('exit_ms',specs[0]['exit_ms']+study.HOUR),('event','2019-10-04')]:
            changed=deepcopy(specs);changed[0][field]=value
            with self.subTest(field=field),self.assertRaisesRegex(ValueError,'unregistered'):run(changed,pairs)
        with self.assertRaises(ValueError):run(specs[:-1],pairs)

    def test_entryask_exitbid_funding_cent_and_no_account_claim(self):
        specs,pairs=fixture();rows=run(specs,pairs);row=rows[0]
        # 1010-1000.2-2*.25=9.30, one22UTC debit1000.2*.08/365 ->.22.
        self.assertEqual(row['outcomes']['reference']['net_usd_per_research_unit'],'9.08')
        self.assertEqual(row['outcomes']['stress']['net_usd_per_research_unit'],'7.86')
        self.assertEqual(len(row['outcomes']['reference']['funding_events']),1)
        at=row['outcomes']['reference']['funding_events'][0]['time_msc']
        self.assertEqual(at%study.DAY,22*study.HOUR)
        self.assertFalse(row['account_simulated']);self.assertFalse(row['execution_authorized'])
        self.assertTrue(row['missing_path_hours'])

    def test_missing_and_crossed_endpoints_stay_in_denominator(self):
        specs,pairs=fixture();del pairs[specs[0]['entry_ms']]
        rows=run(specs,pairs);summary=study.summarize(rows,[2019,2022])
        self.assertFalse(rows[0]['outcomes'])
        pair=next(r for r in summary['summary'] if r['year']==2019 and r['role']=='paired_difference' and r['scenario']=='stress')
        self.assertEqual((pair['planned'],pair['resolved'],pair['unresolved']),(8,7,1))
        with self.assertRaises(ValueError):study.summarize(rows[:-1],[2019,2022])
        specs,pairs=fixture();pairs[specs[0]['entry_ms']][1]['open']=D(999)
        self.assertEqual(run(specs,pairs)[0]['entry']['status'],'crossed_endpoint')

    def test_endpoint_clocks_grid_and_geometry_are_guarded(self):
        specs,pairs=fixture()
        for mode in ['clock','grid']:
            changed=deepcopy(pairs);row=changed[specs[0]['entry_ms']][0]
            if mode=='clock':row['timestamp']+=1
            else:row['open']+=D('.0001')
            with self.subTest(mode=mode),self.assertRaises(ValueError):run(specs,changed)
        from types import SimpleNamespace
        _,model,rate=market.market('reference')
        wrong=lambda scenario:(SimpleNamespace(instrument_id='US500',contract_size=D(1)),model,rate)
        with self.assertRaisesRegex(ValueError,'geometry_identity'):
            study.evaluate(specs,pairs,market_function=wrong,cost_function=market.calculate_round_trip_cost)

    def test_summary_common_mask_costs_and_no_hidden_parameter_search(self):
        specs,pairs=fixture();rows=run(specs,pairs);result=study.summarize(rows,[2019,2022])
        self.assertTrue(result['retained_for_risk_wrapper_review'])
        self.assertEqual(len(result['summary']),12)
        pair=next(r for r in result['summary'] if r['role']=='paired_difference')
        self.assertEqual(D(pair['net_usd_per_research_unit']),D(40))
        self.assertEqual(result['broker_calls'],0)
        changed=deepcopy(rows);changed[0]['side']='SELL'
        with self.assertRaises(ValueError):study.summarize(changed,[2019,2022])


if __name__=='__main__':unittest.main()
