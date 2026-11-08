from copy import deepcopy
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
from pathlib import Path
import json
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'tooling/ai-engines'))
import index_noise_study as core
import index_m1_book as book
import index_daily_reversion as policy
from review_index_noise import inspect_funded_scenario


def quote(stamp,bid,ask=None):
    ask=bid+D('.2') if ask is None else ask
    return tuple(dict(timestamp=stamp,open=float(p),high=float(p),low=float(p),close=float(p),volume=0)
                 for p in (bid,ask))


class DailyBookTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_weekend_funding_reconciles_known_dollars_and_null_is_flat(self):
        start=int(datetime(2022,1,7,23,57,tzinfo=timezone.utc).timestamp()*1000)
        monday=int(datetime(2022,1,10,0,0,tzinfo=timezone.utc).timestamp()*1000)
        pairs={t:quote(t,D(100)) for t in [start,start+60000,start+120000]}
        pairs.update({t:quote(t,D(105)) for t in [monday,monday+60000]})
        plans={start+60000:dict(side='BUY',distance=D(5)),monday:dict(side='EXIT')}
        result=book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertEqual(result['entries'],1)
        trade=result['trades'][0]
        self.assertEqual(trade['entry_time_msc'],start+120000)
        self.assertEqual(trade['quantity'],'3.84')
        self.assertEqual(trade['funding_usd'],'11.52')
        self.assertEqual(trade['net_usd'],'1.15')
        self.assertEqual(result['balance_usd'],'10001.15')
        self.assertEqual(len(result['funding_events']),3)
        self.assertTrue(trade['path_unresolved'])
        packet=json.loads(json.dumps(result,default=str))
        self.assertEqual(inspect_funded_scenario(packet,pairs,{})['net_usd'],'1.15')
        omitted=deepcopy(packet)
        omitted['funding_events']=[]
        omitted['funding_total_usd']='0'
        omitted['trades'][0]['funding_usd']='0'
        omitted['trades'][0]['net_usd']=omitted['trades'][0]['price_net_usd']
        omitted['balance_usd']='10012.67'
        omitted['net_equity_usd']='12.67'
        with self.assertRaisesRegex(ValueError,'calendar_funding'):
            inspect_funded_scenario(omitted,pairs,{})
        null=book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1),null_control=True)
        self.assertEqual((null['entries'],null['net_equity_usd']),(0,'0'))

    def test_missing_fill_expires_without_later_entry_and_open_end_is_marked(self):
        start=1640995200000
        plans={start:dict(side='BUY',distance=D(5))}
        pairs={start:quote(start,D(100)),start+120000:quote(start+120000,D(101))}
        expired=book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertEqual(expired['entries'],0)
        self.assertEqual(expired['rejected'][0]['reason'],'missing_fill_minute')
        pairs[start+60000]=quote(start+60000,D(100))
        with self.assertRaisesRegex(ValueError,'unordered'):
            book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        opened=book.simulate(dict(sorted(pairs.items())),plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertIsNotNone(opened['open_position'])
        self.assertEqual(opened['closed_trades'],0)
        self.assertEqual(opened['balance_usd'],'10000')
        self.assertGreater(D(opened['floating_usd']),-D(25))

    def test_scheduled_safety_exit_does_not_require_a_quote_at_decision_minute(self):
        start=1640995200000
        pairs={t:quote(t,D(100)) for t in [start,start+60000,start+240000]}
        plans={start:dict(side='BUY',distance=D(5)),start+180000:dict(side='EXIT')}
        result=book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertEqual(result['closed_trades'],1)
        self.assertEqual(result['trades'][0]['exit_time_msc'],start+240000)

    def test_gap_stop_does_not_cap_loss_at_planned_risk(self):
        start=1640995200000
        pairs={start:quote(start,D(100)),start+60000:quote(start+60000,D(100)),
               start+120000:quote(start+120000,D(90))}
        result=book.simulate(pairs,{start:dict(side='BUY',distance=D(5))},candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertEqual(result['trades'][0]['reason'],'stop_loss_gap')
        self.assertLess(D(result['trades'][0]['net_usd']),-D(25))

    def test_short_book_closes_on_ask_and_reconciles_hand_calculated_profit(self):
        start=1640995200000
        pairs={t:quote(t,D(100)if t<start+180000 else D(95))
               for t in [start,start+60000,start+120000,start+180000]}
        plans={start:dict(side='SELL',distance=D(5)),start+120000:dict(side='EXIT')}
        result=book.simulate(pairs,plans,candidate='fixture',slippage=D('.25'),funding_per_lot=D(1))
        self.assertEqual(result['trades'][0]['entry_fill'],'100.0')
        self.assertEqual(result['trades'][0]['exit_fill'],'95.2')
        self.assertEqual(result['trades'][0]['net_usd'],'12.67')

    def test_open_end_keeps_mark_and_accrues_weekend_funding_until_exclusive_horizon(self):
        start=int(datetime(2022,1,7,23,57,tzinfo=timezone.utc).timestamp()*1000)
        end=int(datetime(2022,1,10,0,0,tzinfo=timezone.utc).timestamp()*1000)
        pairs={t:quote(t,D(100)) for t in [start,start+60000,start+120000]}
        result=book.simulate(pairs,{start+60000:dict(side='BUY',distance=D(5))},
            candidate='fixture',slippage=D('.25'),funding_per_lot=D(1),end_time_msc=end)
        self.assertEqual(result['funding_total_usd'],'7.68')
        self.assertEqual(result['balance_usd'],'9992.32')
        self.assertEqual(result['floating_usd'],'-6.53')
        self.assertEqual(result['closed_trades'],0)
        self.assertIsNotNone(result['open_position'])
        self.assertEqual(result['last_mark_time_msc'],start+180000)


class DailySignalTests(unittest.TestCase):
    def test_oracle_disagreement_blocks_before_numerical_execution(self):
        with patch.object(policy.signal_oracle,'oracle_plans',return_value={1:dict(side='BUY',distance=1)}),\
                patch.object(book,'simulate')as execution:
            with self.assertRaisesRegex(ValueError,'independent_signal_oracle_mismatch'):
                policy.simulator(policy.RSI)({}, {}, slippage=D('.25'))
            execution.assert_not_called()

    def test_ibs_safety_exit_survives_unavailable_rsi_after_missing_history(self):
        start=1641218400000
        sessions={'2022-01-03':[start,start+60000],'2022-01-04':[start+86400000,start+86460000]}
        pairs={}
        for at in sessions['2022-01-04']:
            b,a=quote(at,D(109));b.update(high=110,low=100,close=109);pairs[at]=(b,a)
        plans=policy.plans_for(sessions,pairs,policy.RSI)
        self.assertEqual(plans[sessions['2022-01-04'][-1]+60000]['side'],'EXIT')

    def test_rsi_exit_survives_undefined_ibs_flat_range(self):
        sessions={};pairs={};start=1641218400000
        for day in range(4):
            at=start+day*86400000;sessions[f'2022-01-{day+3:02}']=[at]
            pairs[at]=quote(at,D(100+day))
        plans=policy.plans_for(sessions,pairs,policy.RSI)
        self.assertEqual(plans[start+3*86400000+60000]['side'],'EXIT')

    def test_cutler_rsi_has_known_values(self):
        self.assertEqual(policy.rsi3(list(map(D,[100,99,98,97]))),D(0))
        self.assertEqual(policy.rsi3(list(map(D,[1,2,3,4]))),D(100))
        self.assertEqual(policy.rsi3(list(map(D,[100,99,101,100]))),D(50))
        self.assertIsNone(policy.rsi3([D(1),None,D(2),D(3)]))

    def test_past_only_atr_warmup_gap_and_future_prefix(self):
        start=int(datetime(2022,1,3,14,30,tzinfo=timezone.utc).timestamp()*1000)
        sessions,pairs={},{}
        for day in range(20):
            stamps=[start+day*86400000+i*60000 for i in range(3)]
            sessions[str(day)]=stamps
            close=D(100-day)
            for stamp in stamps:
                b,a=quote(stamp,close)
                b.update(high=float(close+1),low=float(close-D('.1')))
                pairs[stamp]=(b,a)
        plans=policy.plans_for(sessions,pairs,policy.RSI)
        first=list(sessions.values())[14][-1]+60000
        self.assertEqual(min(plans),first)
        self.assertEqual(plans[first]['distance'],D('1.65'))
        changed=deepcopy(pairs)
        later=list(sessions.values())[-1]
        del changed[later[1]]
        altered=policy.plans_for(sessions,changed,policy.RSI)
        self.assertEqual({t:p for t,p in plans.items() if t<later[0]},
                         {t:p for t,p in altered.items() if t<later[0]})
        self.assertEqual(altered[later[-1]+60000]['side'],'EXIT')


if __name__=='__main__':
    unittest.main()
