from datetime import datetime,timezone
from decimal import Decimal as D
from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from monthly_trend_component import funding,allocation,money,previous_months,sides,SYMBOLS,run


class MonthlyComponentTests(unittest.TestCase):
    def points(self):
        result={}
        for symbol in SYMBOLS:
            result[(symbol,'2018-01','rebalance_observation')]=dict(bid='100',target_ms=100000)
            for i,month in enumerate(previous_months('2018-01')):
                price=(D(100)+i+D(i*i)/10) if symbol!='EURUSD' else D(100)-i-D(i*i)/10
                result[(symbol,month,'signal_close')]=dict(bid=str(price),known_at_ms=i,month=month)
        return result
    def test_known_history_inverse_vol_and_direction_with_gross_cap(self):
        points=self.points();weights,features=allocation(points,'2018-01')
        self.assertLess(weights['EURUSD'],0);self.assertGreater(weights['XAUUSD'],0)
        self.assertLessEqual(sum(map(abs,weights.values()),D(0)),D(1)+D('1e-25'))
        other,_=allocation(points,'2018-01',always_long=True)
        self.assertTrue(all(w>0 for w in other.values()))
        self.assertEqual(features['XAUUSD']['signs'],['1','1','1'])
    def test_missing_or_future_history_cannot_silently_become_flat(self):
        points=self.points();key=('XAUUSD',previous_months('2018-01')[-1],'signal_close')
        points[key]['known_at_ms']=100000
        with self.assertRaisesRegex(ValueError,'inconclusive'):allocation(points,'2018-01')
        points[key]['known_at_ms']=10;points[key]['bid']=None
        with self.assertRaisesRegex(ValueError,'inconclusive'):allocation(points,'2018-01')
    def test_future_execution_price_does_not_change_exante_weights(self):
        points=self.points();before=allocation(points,'2018-01')[0]
        for symbol in SYMBOLS:points[(symbol,'2018-01','rebalance_observation')]['bid']='999'
        self.assertEqual(allocation(points,'2018-01')[0],before)
    def test_funding_has_weekday_triple_and_inclusive_exit(self):
        stamp=lambda day:int(datetime.fromisoformat(day).replace(tzinfo=timezone.utc).timestamp()*1000)
        # Tuesday22:00 excluded, Wednesday22:00 included exactly once at triple.
        total,events=funding('EURUSD','BUY',D(1),stamp('2024-01-02T22:00'),stamp('2024-01-03T22:00'),'reference')
        self.assertEqual(total,D('27.90'));self.assertEqual(len(events),1)
        credit,_=funding('EURUSD','SELL',D(1),stamp('2024-01-02T22:00'),stamp('2024-01-03T22:00'),'reference')
        self.assertEqual(credit,D('-.93'))
        index,_=funding('US500','BUY',D(2),stamp('2024-01-05T23:00'),stamp('2024-01-07T22:00'),'stress')
        self.assertEqual(index,D(8))
    def test_Gold_Ask_is_declared_by_scenario_and_money_half_up(self):
        observation=dict(instrument='XAUUSD',bid='2000',ask=None,observed_ask=False)
        self.assertEqual(sides(observation,'reference'),(D(2000),D('2000.50')))
        self.assertEqual(sides(observation,'stress'),(D(2000),D(2001)))
        self.assertEqual(money(D('-.005')),D('-.01'))
    def test_continuous_NAV_and_final_open_mark_have_no_exit_fee(self):
        sys.path.insert(0,str(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2'))
        from trading_workspace_v2.semantics.data_costs import calculate_round_trip_cost
        observations=[]
        for year in range(2013,2025):
            for month in range(1,13):
                k=D((year-2013)*12+month)
                for symbol,base,step in [('EURUSD',D('1.1'),D('.0005')),('XAUUSD',D(1000),D(3)),('US500',D(2000),D(5))]:
                    bid=(base+step*k+step*k*k/100).quantize(D('.00001') if symbol=='EURUSD' else D('.001'))
                    ask=None if symbol=='XAUUSD' else str(bid+(D('.00010') if symbol=='EURUSD' else D('.25')))
                    for role,day,hour in [('rebalance_observation',1,15),('signal_close',28,21)]:
                        at=int(datetime(year,month,day,hour,tzinfo=timezone.utc).timestamp()*1000)
                        observations.append(dict(instrument=symbol,month=f'{year}-{month:02}',role=role,target_ms=at,
                            known_at_ms=at,bid=str(bid),ask=ask,observed_ask=ask is not None))
        result=run(observations,scenario='reference',always_long=True,cost_function=calculate_round_trip_cost)
        self.assertEqual(len(result['months']),84)
        self.assertEqual(D(result['net']),sum((D(r['net']) for r in result['months']),D(0)))
        self.assertEqual(D(result['cash'])+D(result['floating']),D(result['ending_nav']))
        for previous,current in zip(result['months'],result['months'][1:]):
            self.assertEqual(previous['nav_after'],current['nav_before'])
        for trade in result['months'][-1]['trades']:
            self.assertEqual(trade['status'],'open_mark')
            self.assertFalse(trade['costs']['exit_cost_charged'])
        self.assertFalse(result['final_positions_closed'])


if __name__=='__main__':unittest.main()
