from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_nasdaq_overnight_reversal_component import fixture as opening_fixture
from test_us500_overnight_reversal_component import us_market
from nasdaq_cash_calendar import sessions_for
import index_rest_of_day_component as study
import index_noise_study as market
import nasdaq_h4_study as nasdaq


def quote(pair, price):
    for row, offset in zip(pair, (D(0), D('.2'))):
        p=D(str(price))+offset
        row.update(open=str(p), high=str(p+1), low=str(p-1), close=str(p))


def fixture(day='2019-01-02', *, late=110, first=90):
    case=opening_fixture(day);sessions,pairs,stamps,start,end=case
    quote(pairs[stamps[29]],first)
    quote(pairs[stamps[-31]],late)
    quote(pairs[stamps[-29]],111)
    quote(pairs[stamps[-1]],115 if late>=100 else 107)
    return case


def evaluate(case, profile='us500'):
    sessions,pairs,_,start,end=case
    return study.evaluate(sessions,pairs,start=start,end=end,profile=profile,
        market_function=us_market if profile=='us500' else nasdaq.market,
        cost_function=market.calculate_round_trip_cost)['rows'][0]


class RestOfDayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2'
        market.bind_core(root);nasdaq.bind_core(root)

    def test_late_sign_not_first_half_and_exact_delayed_bidask_cost(self):
        for profile in ('us500','nasdaq'):
            row=evaluate(fixture(),profile)
            self.assertEqual((row['signal_side'],row['first_half_side']),('BUY','SELL'))
            self.assertEqual(row['signal_known_at_ms'],row['decision_ms'])
            self.assertEqual(row['entry_ms']-row['decision_ms'],60000)
            self.assertEqual(row['path_expected_minutes'],28)
            for scenario,primary,control in [('reference','3.30','-4.70'),('stress','2.30','-5.70')]:
                self.assertEqual(D(row['outcomes'][scenario]['primary']['net_usd_per_research_unit']),D(primary))
                self.assertEqual(D(row['outcomes'][scenario]['first_half_control']['net_usd_per_research_unit']),D(control))
            self.assertEqual(row['candidate'],study.CANDIDATES[profile])
            self.assertFalse(row['account_simulated']);self.assertFalse(row['execution_authorized'])
        row=evaluate(fixture(late=90,first=110))
        self.assertEqual((row['signal_side'],row['first_half_side']),('SELL','BUY'))
        self.assertEqual(D(row['outcomes']['reference']['primary']['net_usd_per_research_unit']),D('3.30'))

    def test_all_predictors_required_and_no_dependency_on_0930_open(self):
        for feature in ('previous','first','late'):
            for mode in ('missing','crossed'):
                case=fixture();sessions,pairs,stamps,_,_=case
                at=next(iter(sessions.values()))[-1] if feature=='previous' else stamps[29] if feature=='first' else stamps[-31]
                if mode=='missing':del pairs[at]
                else:pairs[at][1]['close']='1'
                row=evaluate(case)
                self.assertFalse(row['planned_trade']);self.assertEqual(row['status'],'signal_unavailable')
        case=fixture();del case[1][case[2][0]]
        self.assertTrue(evaluate(case)['planned_trade'])

    def test_missing_crossed_endpoint_and_internal_gap_do_not_erase_planned_day(self):
        for target in ('entry','exit','internal'):
            case=fixture();pairs,stamps=case[1:3]
            at=stamps[-29] if target=='entry' else stamps[-1] if target=='exit' else stamps[-10]
            del pairs[at];row=evaluate(case);self.assertTrue(row['planned_trade'])
            self.assertEqual(bool(row['outcomes']),target=='internal')
            if target=='internal':self.assertEqual(row['path_observed_minutes'],27)
        case=fixture();case[1][case[2][-29]][1]['open']='1'
        self.assertEqual(evaluate(case)['status'],'unresolved_endpoint')

    def test_flat_primary_and_control_have_distinct_no_exposure_states(self):
        row=evaluate(fixture(late=100));self.assertEqual(row['status'],'valid_flat_rod')
        self.assertFalse(row['planned_trade']);self.assertFalse(row['outcomes'])
        row=evaluate(fixture(first=100))
        for scenario in study.SCENARIOS:
            control=row['outcomes'][scenario]['first_half_control']
            self.assertIsNone(control['side']);self.assertIsNone(control['costs'])
            self.assertEqual(control['net_usd_per_research_unit'],'0');self.assertTrue(control['no_exposure'])

    def test_future_mutation_changes_neither_signal_nor_sizing_claim(self):
        case=fixture();base=evaluate(case)
        for at in list(case[1]):
            if at>=base['entry_ms']:del case[1][at]
        got=evaluate(case)
        for name in ('signal_side','first_half_side','planned_trade','decision_ms','entry_ms'):
            self.assertEqual(got[name],base[name])
        case=fixture();quote(case[1][case[2][29]],120)
        got=evaluate(case)
        self.assertEqual(got['signal_side'],base['signal_side']);self.assertNotEqual(got['first_half_side'],base['first_half_side'])

    def test_holiday_prior_halfday_and_dst(self):
        for day,hour in [('2019-01-02',20),('2019-07-05',19),('2022-11-28',20)]:
            case=fixture(day);row=evaluate(case)
            self.assertEqual(row['previous_close_ms'],next(iter(case[0].values()))[-1])
            dt=datetime.fromtimestamp(row['entry_ms']/1000,timezone.utc)
            self.assertEqual((dt.hour,dt.minute),(hour,31))
        self.assertEqual(evaluate(fixture('2019-11-29'))['status'],'calendar_halfday_skipped')

    def test_feature_grid_clock_holdout_profile_and_market_identity(self):
        for offset in (29,-31):
            for mode in ('grid','clock'):
                case=fixture();row=case[1][case[2][offset]][0]
                row['close' if mode=='grid' else 'timestamp']='100.0001' if mode=='grid' else 1
                with self.subTest(offset=offset,mode=mode),self.assertRaises(ValueError):evaluate(case)
        sessions,pairs,_,start,end=fixture()
        with self.assertRaisesRegex(ValueError,'holdout'):
            study.prepare(sessions,pairs,start=start,end=1767225600000,profile='us500')
        with self.assertRaisesRegex(ValueError,'profile'):
            study.prepare(sessions,pairs,start=start,end=end,profile=True)
        with self.assertRaisesRegex(ValueError,'geometry'):
            study.evaluate(sessions,pairs,start=start,end=end,profile='us500',market_function=nasdaq.market,cost_function=market.calculate_round_trip_cost)

    def test_summary_first_half_comparison_coverage_and_identity_guards(self):
        template=evaluate(fixture());expected={};rows=[]
        for year in (2019,2022):
            expected[year]=list(sessions_for(f'development-{year}'))[:100]
            for day in expected[year]:
                row=deepcopy(template);row.update(year=year,session=day)
                for scenario in study.SCENARIOS:
                    for role in study.ROLES:
                        row['outcomes'][scenario][role]['net_usd_per_research_unit']='3' if role=='primary' else '1'
                rows.append(row)
        self.assertTrue(study.summarize(rows,expected,profile='us500')['retained_for_further_research'])
        for mode in ('firsthalf','missing','coverage'):
            bad=deepcopy(rows)
            if mode=='firsthalf':bad[0]['outcomes']['stress']['first_half_control']['net_usd_per_research_unit']='1000'
            elif mode=='missing':
                for row in bad[:3]:row['outcomes']={}
            else:
                for row in bad[:3]:row['predictor_valid']=False
            self.assertFalse(study.summarize(bad,expected,profile='us500')['retained_for_further_research'])
        for mode in ('duplicate','foreign','authority'):
            bad=deepcopy(rows)
            if mode=='duplicate':bad[-1]=deepcopy(bad[-2])
            elif mode=='foreign':bad[0]['candidate']=study.CANDIDATES['nasdaq']
            else:bad[0]['execution_authorized']=True
            with self.subTest(mode=mode),self.assertRaises(ValueError):study.summarize(bad,expected,profile='us500')


if __name__=='__main__':unittest.main()
