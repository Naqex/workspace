from copy import deepcopy
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tooling/ai-engines'))
import nasdaq_h4_study as study

HOUR, H4, DAY = study.HOUR, study.H4, study.DAY
START = 100*DAY


def fixture(values=(210,)*12):
    prices = [200]*80+list(values)
    begin = START-80*H4
    result = {}
    for index, price in enumerate(prices):
        for hour in range(4):
            stamp = begin+index*H4+hour*HOUR
            result[stamp] = tuple(dict(timestamp=stamp, open=D(price)+offset,
                high=D(price)+offset+D('.1'), low=D(price)+offset-D('.1'),
                close=D(price)+offset, volume=0) for offset in [D(0), D('.2')])
    return result


def run(pairs, scenario='reference', days=2):
    return study.simulate(pairs, start=START, end=START+days*DAY, scenario=scenario)


class NasdaqH4Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        study.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_complete_bid_h4_and_explicit_volume_zero(self):
        pairs = fixture()
        study.validate_pairs(pairs)
        bars = study.completed_h4(pairs)
        bar = bars[START+H4]
        self.assertEqual((bar.open, bar.high, bar.low, bar.close), (D(210),D('210.1'),D('209.9'),D(210)))
        del pairs[START+HOUR]
        self.assertNotIn(START+H4, study.completed_h4(pairs))

    def test_indicator_matches_parent_math_without_instrument_relabelling(self):
        from trading_workspace_v2.forex_h4_candidates import ResearchH4Candidate, SMA
        own, oracle = study.BidSmaSignal(), ResearchH4Candidate(SMA)
        candles = study.completed_h4(fixture([210,190,210,190,220,180]*2))
        for i, bar in enumerate(candles.values()):
            side = [None, 'BUY', 'SELL'][i%3]
            expected = oracle.observe(bar, side=side, position_id='p'+str(i) if side else None)
            got = own.observe(bar, side=side)
            self.assertEqual((got['side'],got['distance']), expected)

    def test_cross_after_warmup_then_exact_one_hour_delay_and_no_warmup_trades(self):
        r = run(fixture())
        self.assertEqual(r['entries'],1)
        p = r['open_position']
        self.assertEqual(p['side'],'BUY')
        self.assertEqual(p['decision_time_msc'],START+H4)
        self.assertEqual(p['entry_time_msc'],START+H4+HOUR)
        self.assertEqual(p['entry_quote'],D('210.2'))
        self.assertTrue(all(d['time_msc']>START for d in r['decisions']))
        self.assertFalse(r['prop_evaluated'])
        self.assertEqual(r['broker_calls'],0)

    def test_missing_fill_hour_cancels_without_later_retry(self):
        pairs=fixture();del pairs[START+H4+HOUR]
        r=run(pairs)
        self.assertEqual(r['entries'],0)
        self.assertIsNone(r['pending_action'])
        self.assertEqual(r['rejected'][0]['reason'],'missing_exact_fill_hour')

    def test_long_stop_gap_fills_worse_price_and_flags_missing_path(self):
        pairs=fixture();del pairs[START+6*HOUR]
        for row in pairs[START+7*HOUR]:
            row.update(open=D(170),high=D('170.1'),low=D('169.9'),close=D(170))
        r=run(pairs);t=r['trades'][0]
        self.assertEqual(t['reason'],'stop_loss_gap')
        self.assertEqual(t['exit_quote'],D(170))
        self.assertTrue(t['path_unresolved'])
        self.assertLess(t['net_usd'],-25)

    def test_short_stop_uses_ask_and_intrabar_interval(self):
        pairs=fixture([190]*12)
        reference=run(pairs);stop=reference['open_position']['stop']
        # Bid high stays below stop, Ask alone reaches it.
        pairs[START+6*HOUR][1]['high']=stop
        r=run(pairs);t=r['trades'][0]
        self.assertEqual(t['side'],'SELL')
        self.assertEqual(t['reason'],'stop_loss')
        self.assertIsNone(t['exit_time_msc'])
        self.assertEqual(t['exit_interval_msc'],[START+6*HOUR,START+7*HOUR])
        self.assertGreaterEqual(t['net_usd'],D('-25'))

    def test_cost_reserve_sizing_and_margin_are_explicit_research_units(self):
        for scenario in ['reference','stress']:
            r=run(fixture(),scenario);p=r['open_position'];slip=study.SCENARIOS[scenario][0]
            planned=(abs(p['entry_quote']-p['stop'])+2*slip)*p['quantity']
            self.assertLessEqual(planned,25)
            self.assertEqual(p['quantity']%D('.01'),0)
            self.assertLessEqual(p['entry_quote']*p['quantity']/10,10000)
        self.assertLess(run(fixture(),'stress')['net_equity_usd'],run(fixture())['net_equity_usd'])
        with self.assertRaisesRegex(ValueError,'unregistered'):
            run(fixture(),'free')

    def test_funding_exact_22utc_on_each_calendar_day_and_final_open_mark(self):
        r=run(fixture());p=r['open_position']
        self.assertEqual([f['time_msc'] for f in r['funding_events']], [START+22*HOUR,START+46*HOUR])
        debit=(p['entry_quote']*p['quantity']*D('.08')/365).quantize(D('.01'),rounding=ROUND_HALF_UP)
        self.assertEqual(r['funding_total_usd'],2*debit)
        self.assertEqual(r['balance_usd'],10000-2*debit)
        expected=(-(D('.2')+D('.5'))*p['quantity']).quantize(D('.01'),rounding=ROUND_HALF_UP)
        self.assertEqual(r['floating_usd'],expected)
        self.assertEqual(r['net_equity_usd'],expected-2*debit)
        self.assertEqual(r['closed_trades'],0)
        self.assertEqual(r['last_mark_time_msc'],START+2*DAY)

    def test_missing_final_tail_remains_open_unresolved_not_forceclosed(self):
        r=run(fixture([210]*7))
        self.assertIsNotNone(r['open_position'])
        self.assertTrue(r['open_position']['path_unresolved'])
        self.assertEqual(r['gap_events'][-1]['reason'],'unobserved_final_tail')
        self.assertEqual(r['closed_trades'],0)

    def test_strategy_exit_requires_later_fill_and_retains_cash_identity(self):
        r=run(fixture([210]*6+[180]*6))
        self.assertEqual(r['trades'][0]['reason'],'stop_loss_gap')
        self.assertEqual(r['balance_usd'],D(10000)+sum((t['price_net_usd'] for t in r['trades']),D(0))-r['funding_total_usd'])
        # Force a scheduled exit to isolate its fill ordering from the indicator oracle above.
        from unittest.mock import patch
        original=study.BidSmaSignal.observe
        def exits_at_second_bar(obj,candle,side=None):
            result=original(obj,candle,side)
            if candle.timestamp*1000==START+H4 and side=='BUY':result['side']='EXIT'
            return result
        with patch.object(study.BidSmaSignal,'observe',exits_at_second_bar):
            r=run(fixture())
        t=r['trades'][0]
        self.assertEqual(t['reason'],'strategy_exit')
        self.assertEqual(t['exit_time_msc'],START+2*H4+HOUR)
        self.assertEqual(r['entries'],1)

    def test_calendar_weekend_debits_are_not_skipped_and_margin_rejects(self):
        # START is day100 after epoch (Saturday); the calendar contract has no weekday exemption.
        self.assertEqual(len(run(fixture())['funding_events']),2)
        pairs=fixture([201]*12)
        for pair in pairs.values():
            for row in pair:
                for key in ['open','high','low','close']:row[key]+=D(19800)
        r=run(pairs)
        self.assertEqual(r['entries'],0)
        self.assertEqual(r['rejected'][0]['reason'],'invalid_stop_min_max_unit_or_margin')

    def test_prefix_and_future_mutation_cannot_change_earlier_decisions(self):
        pairs=fixture();r=run(pairs)
        changed=deepcopy(pairs)
        for at,pair in changed.items():
            if at>=START+DAY:
                for row in pair:
                    for key in ['open','high','low','close']:row[key]+=D(50)
        other=run(changed)
        self.assertEqual([d for d in r['decisions'] if d['time_msc']<=START+DAY],
                         [d for d in other['decisions'] if d['time_msc']<=START+DAY])
        prefix=study.simulate({t:p for t,p in pairs.items() if t<START+DAY},start=START,end=START+DAY,scenario='reference')
        self.assertEqual(prefix['decisions'],[d for d in r['decisions'] if d['time_msc']<=START+DAY])

    def test_source_clock_crossed_grid_and_evaluation_bounds(self):
        for mutation,error in [('clock','clock'),('cross','crossed'),('grid','grid')]:
            pairs=fixture()
            if mutation=='clock':pairs[START][1]['timestamp']+=HOUR
            if mutation=='cross':
                for key in ['open','high','low','close']:pairs[START][1][key]-=D(1)
            if mutation=='grid':pairs[START][1]['high']+=D('.0001')
            with self.subTest(mutation=mutation),self.assertRaisesRegex(ValueError,error):run(pairs)
        with self.assertRaisesRegex(ValueError,'evaluation_interval'):
            study.simulate(fixture(),start=START,end=START+DAY,scenario='reference')


if __name__=='__main__':unittest.main()
