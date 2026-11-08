from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nasdaq_cash_reversion_component as study

M, H, DAY = study.MINUTE, study.HOUR, study.DAY
START = 100*DAY


def pair(at, bid=100, spread='.2'):
    return tuple(dict(timestamp=at, open=D(bid)+offset, high=D(bid)+offset+D('.1'),
        low=D(bid)+offset-D('.1'), close=D(bid)+offset, volume=0) for offset in [D(0), D(spread)])


def case():
    a, b = START+20*H, START+DAY+20*H
    pairs = {a:pair(a), a+M:pair(a+M), b:pair(b,102), b+M:pair(b+M,102)}
    plans = {a:dict(side='BUY'), b:dict(side='EXIT')}
    return pairs, plans


def run(pairs, plans, **kw):
    return study.simulate(pairs, plans, start=START, end=START+2*DAY, scenario='reference', **kw)


class CashReversionTests(unittest.TestCase):
    def test_delay_sides_spread_slip_funding_and_arithmetic(self):
        pairs, plans = case()
        result = run(pairs, plans)
        trade = result['trades'][0]
        self.assertEqual(trade['entry_time_msc'], START+20*H+M)
        self.assertEqual(trade['entry_ask'], D('100.2'))
        self.assertEqual(trade['exit_bid'], D(102))
        self.assertEqual(trade['price_net_usd'], D('1.30'))
        self.assertEqual(trade['funding_usd'], D('.02'))
        self.assertEqual(result['net_component_usd'], D('1.28'))
        self.assertEqual(result['funding_events'][0]['time_msc'], START+22*H)
        self.assertFalse(result['execution_authorized'])

    def test_missing_fill_never_uses_next_quote_or_warmup_trade(self):
        pairs, plans = case()
        del pairs[START+20*H+M]
        pairs[START+20*H+2*M] = pair(START+20*H+2*M)
        pairs = dict(sorted(pairs.items()))
        plans[START-DAY] = dict(side='BUY')
        result = run(pairs, plans)
        self.assertEqual(result['entries'], 0)
        self.assertEqual(result['rejected'][0]['reason'], 'missing_exact_fill_minute')
        self.assertEqual(len(result['decisions']), 2)

    def test_new_decision_reports_superseded_pending_during_long_quote_gap(self):
        pairs, plans = case()
        del pairs[START+20*H+M]
        result = run(pairs, plans)
        self.assertEqual(result['entries'], 0)
        self.assertEqual(result['rejected'][0]['reason'], 'unfilled_before_next_decision')

    def test_decision_without_preceding_minute_is_not_lost(self):
        pairs, plans = case()
        del pairs[START+20*H]
        self.assertEqual(run(pairs, plans)['entries'], 1)

    def test_final_position_pending_and_missing_path_are_not_forceclosed(self):
        pairs, plans = case()
        plans.pop(START+DAY+20*H)
        plans[START+2*DAY-M] = dict(side='EXIT')
        result = run(pairs, plans)
        self.assertEqual(result['closed_trades'], 0)
        self.assertIsNotNone(result['open_position'])
        self.assertTrue(result['open_position']['path_unresolved'])
        self.assertEqual(result['pending_action']['fill_time_msc'], START+2*DAY)
        self.assertEqual(len(result['funding_events']), 2)

    def test_boundary_charge_before_exit_but_not_before_same_time_entry(self):
        at = START+22*H
        pairs = {at:pair(at),at+DAY:pair(at+DAY,102)}
        plans = {at-M:dict(side='BUY'),at+DAY-M:dict(side='EXIT')}
        result = run(pairs, plans)
        self.assertEqual([x['time_msc'] for x in result['funding_events']], [at+DAY])
        self.assertEqual(result['trades'][0]['funding_usd'], D('.02'))

    def test_null_and_stress_and_future_mutation(self):
        pairs, plans = case()
        result = run(pairs, plans)
        null = run(pairs, plans, null_control=True)
        self.assertEqual(null['net_component_usd'], 0)
        self.assertEqual(null['entries'], 0)
        stress = study.simulate(pairs, plans, start=START,end=START+2*DAY,scenario='stress')
        self.assertLess(stress['net_component_usd'],result['net_component_usd'])
        changed = deepcopy(pairs)
        for at in changed:
            if at >= START+DAY:
                changed[at] = pair(at,120)
        other = run(changed,plans)
        self.assertEqual(other['decisions'],result['decisions'])
        self.assertEqual(other['trades'][0]['entry_ask'],result['trades'][0]['entry_ask'])

    def test_incomplete_cash_session_safety_exit_and_oracle_readiness(self):
        pairs, sessions = {}, {}
        # Fifteen declining complete sessions seed ATR14, RSI3 and IBS<=.5.
        for n in range(15):
            at = START+n*DAY
            sessions[str(n)] = [at]
            pairs[at] = pair(at,100-n)
            pairs[at][0].update(high=D(102-n),low=D(99-n),close=D(99-n))
        missing = START+15*DAY
        sessions['missing'] = [missing]
        plans = study.prepare(sessions,pairs)
        self.assertEqual(plans[START+14*DAY+M]['side'],'BUY')
        self.assertEqual(plans[missing+M]['side'],'EXIT')
        self.assertTrue(all(v['side']!='BUY' for t,v in plans.items() if t<START+14*DAY))

    def test_crossed_and_wrong_grid_fail_before_numeric(self):
        for kind in ['cross','clock','grid']:
            pairs, plans = case()
            at = next(iter(pairs))
            if kind=='cross':pairs[at] = pair(at,100,'-.2')
            elif kind=='clock':pairs[at][1]['timestamp'] += M
            else:pairs[at][1]['high'] += D('.0001')
            with self.subTest(kind=kind), self.assertRaises(ValueError):run(pairs,plans)

    def test_retention_needs_both_stress_years_closed_and_no_rejections(self):
        base=dict(scenario='stress',null_control=False,net_component_usd=D(10),
                  closed_trades=10,rejected=[],open_position=None,pending_action=None)
        self.assertTrue(study.retained([dict(base),dict(base)]))
        for change in [dict(net_component_usd=D(0)),dict(closed_trades=9),
                       dict(rejected=[{'reason':'missing_exact_fill_minute'}]),
                       dict(open_position={'id':'open'}),dict(pending_action={'side':'EXIT'})]:
            with self.subTest(change=change):
                self.assertFalse(study.retained([dict(base),dict(base,**change)]))
        self.assertFalse(study.retained([dict(base)]))


if __name__ == '__main__':unittest.main()
