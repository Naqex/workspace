from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import sys,unittest
WS=Path(__file__).resolve().parents[3]
sys.path[:0]=[str(WS/'tooling/ai-engines/tests'),str(WS/'tooling/ai-engines'),str(WS/'projects/trader/foundation_v2')]
from test_ny_fx_latency import series
import ny_fx_latency as m
from ny_fx_gap_scenarios import GapMinute,GapScenario
m.parent.bind_core(WS/'projects/trader/foundation_v2')

DAY='2019-01-02'


def model(at,mode='observed_events'):
    return GapScenario(mode,(GapMinute(at,D('1.098'),D('1.102'),D('1.0981'),D('1.1021')),))


class GapScenarioTests(unittest.TestCase):
    def run_gap(self,*,mode='observed_events',opposite=False,scenario='reference',gap_offset=16):
        pairs=series();hourly=m.aggregate_hours(pairs);t=m.parent.clocks(DAY)[10]+gap_offset*m.MINUTE
        pairs.pop(t)
        book=m.run(pairs,hourly,2019,scenario,lag_minutes=15,opposite=opposite,day_list=[DAY],gap_model=model(t,mode))
        return book,pairs,hourly,t

    def test_observed_silence_creates_no_fill_or_mark_and_preserves_position(self):
        b,_,_,t=self.run_gap()
        gap=next(r for r in b['census'] if r['at_msc']==t)
        self.assertEqual(gap['action'],'conditional_no_observed_event')
        self.assertEqual(gap['valuation_status'],'unobserved_no_mark')
        self.assertEqual(gap['cash_usd'],10000)
        self.assertEqual(gap['position_before'],gap['position_after'])
        self.assertFalse(any(r['exit_bar_msc']==t for r in b['trades']))
        self.assertEqual(b['account_state'],'conditional_flat')
        self.assertTrue(b['original_unknown_preserved']);self.assertFalse(b['execution_authorized'])

    def test_adverse_both_sides_and_costs_match_manual_fraction(self):
        for opposite in (False,True):
            for scenario in ('reference','stress'):
                b,_,_,t=self.run_gap(mode='adverse_envelope',opposite=opposite,scenario=scenario)
                trade=b['trades'][0];self.assertEqual(trade['exit_bar_msc'],t)
                self.assertFalse(trade['observed_exit'])
                price=F('1.098') if opposite else F('1.1021')
                self.assertEqual(F(trade['exit_quote']),price)
                gross=(price-F(trade['entry_quote']))*(1 if opposite else -1)*F(trade['quantity'])*100000
                slip=F(0) if scenario=='reference' else F('.00002')
                net=gross-(5+2*slip*100000)*F(trade['quantity'])
                self.assertEqual(F(str(trade['costs']['net_account'])),round(net,2))

    def test_first_quote_after_silence_checks_gap_stop(self):
        pairs=series();hourly=m.aggregate_hours(pairs);t=m.parent.clocks(DAY)[10]+16*m.MINUTE;pairs.pop(t)
        for row in pairs[t+m.MINUTE]:row.update(open=D('1.11'),high=D('1.12'),low=D('1.10'),close=D('1.11'))
        b=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(t))
        self.assertEqual(b['trades'][0]['exit_bar_msc'],t+m.MINUTE)
        self.assertEqual(b['trades'][0]['exit_quote'],D('1.11'))

    def test_unregistered_crossed_and_exit_gaps_still_unknown(self):
        b,pairs,hourly,t=self.run_gap()
        strict=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=[DAY])
        self.assertEqual(strict['account_state'],'unknown_exposure');self.assertIsNone(strict['net_equity_usd'])
        unregistered=m.run(pairs,hourly,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(t+m.MINUTE))
        self.assertEqual(unregistered['account_state'],'unknown_exposure')
        p=series();h=m.aggregate_hours(p);p[t][1]['close']=D('1.09')
        crossed=m.run(p,h,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(t))
        self.assertEqual(crossed['account_state'],'unknown_exposure')
        p=series();h=m.aggregate_hours(p);end=m.parent.clocks(DAY)[15];p.pop(end)
        last=m.run(p,h,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(end))
        self.assertEqual(last['account_state'],'unknown_exposure')

    def test_envelope_not_used_for_decision_or_sizing_and_null_cash_zero(self):
        observed,p,h,t=self.run_gap()
        adverse=m.run(p,h,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(t,'adverse_envelope'))
        self.assertEqual(observed['decisions'],adverse['decisions'])
        self.assertEqual(observed['events'][0],adverse['events'][0])
        null=m.run(p,h,2019,'reference',lag_minutes=15,day_list=[DAY],gap_model=model(t),null=True)
        self.assertEqual(null['net_equity_usd'],0);self.assertEqual(null['closed_trades'],0)

    def test_invalid_or_untyped_scenario_rejected(self):
        t=m.parent.clocks(DAY)[10]+16*m.MINUTE
        with self.assertRaises(ValueError):GapScenario('ignore_missing',model(t).minutes)
        with self.assertRaises(ValueError):GapScenario('observed_events',model(t).minutes*2)
        with self.assertRaises(ValueError):GapMinute(t,D('1.101'),D('1.1'),D('1.1'),D('1.1'))
        with self.assertRaises(ValueError):m.run(series(),m.aggregate_hours(series()),2019,'reference',lag_minutes=15,gap_model=True)

if __name__=='__main__':unittest.main()
