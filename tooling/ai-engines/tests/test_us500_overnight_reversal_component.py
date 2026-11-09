from pathlib import Path
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_nasdaq_overnight_reversal_component import fixture
import index_overnight_reversal_component as study
import index_noise_study as market
import nasdaq_h4_study as nasdaq
from fomc_price_component import observation


def us_market(scenario):
    instrument,model=market.market(study.SCENARIOS[scenario][0],cost_scenario=market.FTMO_ZERO_COMMISSION)
    return instrument,model,D(0)


class US500OpeningComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root=Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2'
        market.bind_core(root);nasdaq.bind_core(root)

    def test_explicit_profile_binds_source_geometry_and_costs(self):
        for gap,direction in ((10,'SELL'),(-10,'BUY')):
            sessions,pairs,stamps,start,end=fixture(gap=gap)
            row=study.evaluate(sessions,pairs,start=start,end=end,profile='us500',
                market_function=us_market,cost_function=market.calculate_round_trip_cost)['rows'][0]
            self.assertEqual(row['candidate'],study.PROFILES['us500'][0])
            self.assertEqual(row['entry']['source_instrument'],'USA500.IDX/USD')
            self.assertEqual(row['signal_side'],direction)
            for scenario,net in (('reference','4.30'),('stress','3.30')):
                got=row['outcomes'][scenario]['primary'];self.assertEqual(D(got['net_usd_per_research_unit']),D(net))
                self.assertTrue(got['costs']['cost_model_version'].startswith(market.FTMO_ZERO_COMMISSION))
                self.assertEqual(got['costs']['commission_account'],0)
            self.assertFalse(row['account_simulated']);self.assertFalse(row['execution_authorized'])

    def test_profile_market_and_endpoint_source_cannot_silently_mix(self):
        sessions,pairs,stamps,start,end=fixture()
        with self.assertRaisesRegex(ValueError,'geometry'):
            study.evaluate(sessions,pairs,start=start,end=end,profile='us500',
                market_function=nasdaq.market,cost_function=nasdaq.calculate_round_trip_cost)
        for mode in ('US500',True,None):
            with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'profile'):
                study.prepare(sessions,pairs,start=start,end=end,profile=mode)
        with self.assertRaisesRegex(ValueError,'source_instrument'):
            observation(None,stamps[2],duration_ms=60000,source_instrument='EURUSD')

    def test_missing_endpoint_and_foreign_candidate_summary_stay_guarded(self):
        sessions,pairs,stamps,start,end=fixture();del pairs[stamps[2]]
        row=study.evaluate(sessions,pairs,start=start,end=end,profile='us500',
            market_function=us_market,cost_function=market.calculate_round_trip_cost)['rows'][0]
        self.assertTrue(row['planned_trade']);self.assertFalse(row['outcomes'])
        self.assertEqual(row['entry']['source_instrument'],'USA500.IDX/USD')
        row['candidate']=study.CANDIDATE
        expected={2019:[row['session']],2022:['2022-01-03']}
        other=dict(row,year=2022,session='2022-01-03')
        with self.assertRaisesRegex(ValueError,'identity'):
            study.summarize([row,other],expected,profile='us500')


if __name__=='__main__':unittest.main()
