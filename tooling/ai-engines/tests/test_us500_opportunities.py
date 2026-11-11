from copy import deepcopy
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import us500_opportunities as s
from test_us500_multiframe import event


def prepared(events):
    return dict(snapshots={e['t']: e for e in events})


def channel_events():
    es = [event(slot, 100, day='2022-01-03') for slot in range(15, 301, 15)]
    es += [event(15, 100), event(30, 102), event(45, 103), event(60, 100), event(75, 104)]
    for e in es:
        e['m15']['high'] = max(D(101), e['m15']['close'])
    return es


class OpportunityTests(unittest.TestCase):
    def test_reclaim_retry_after_expiry_only_on_later_bar_and_stops_after_confirm(self):
        es = [event(30, 100), event(90, 100), event(105, 100), event(120, 102),
              event(135, 100), event(150, 102)]
        baseline = s.reclaim(prepared(es))
        retried = s.reclaim(prepared(es), retry=True)
        self.assertEqual(baseline['terminal_counts'].get('confirm', 0), 0)
        self.assertEqual(retried['terminal_counts']['arm'], 2)
        self.assertEqual(retried['terminal_counts']['confirm'], 1)
        self.assertEqual([e['t'] for e in retried['events'] if e['kind'] == 'arm'], [es[0]['t'], es[2]['t']])

    def test_reclaim_buy_sell_and_trend_cancel_then_new_setup(self):
        for side, price in (('BUY', 102), ('SELL', 98)):
            es = [event(30, 100, side=side), event(45, price, side=side)]
            self.assertEqual(s.reclaim(prepared(es), retry=True)['terminal_counts']['confirm'], 1)
        es = [event(30, 100), event(45, 100, side='SELL'), event(60, 100), event(75, 102)]
        r = s.reclaim(prepared(es), retry=True)
        self.assertEqual(r['terminal_counts']['cancel_trend'], 1)
        self.assertEqual(r['terminal_counts']['confirm'], 1)

    def test_channel_excludes_current_bar_and_deduplicates_episode(self):
        es = channel_events()
        r = s.triggers(prepared(es), 'FP07')
        self.assertEqual([e['t'] for e in r['events']], [es[-4]['t'], es[-1]['t']])
        self.assertEqual(r['counts']['same_breakout_episode'], 1)

    def test_channel_equality_is_not_breakout_and_sell_is_symmetric(self):
        es = channel_events()[:-4]
        equal = event(30, '101.1')
        equal['m15']['high'] = D('101.1')
        self.assertEqual(s.triggers(prepared(es + [equal]), 'FP07')['events'], [])
        down = event(30, 98, side='SELL')
        down['m15']['low'] = D(98)
        self.assertEqual(s.triggers(prepared(es + [down]), 'FP07')['events'][0]['side'], 'SELL')

    def test_channel_missing_bar_resets_history_not_overnight(self):
        es = channel_events()
        es[-5]['m15'] = None
        self.assertEqual(s.triggers(prepared(es), 'FP07')['events'], [])

    def test_cross_uses_two_closed_means_and_same_session(self):
        for old, new, side in ((99, 101, 'BUY'), (101, 99, 'SELL')):
            e = event(30, 100)
            e['m15']['means'] = {20: D(new), 80: D(100)}
            e['m15']['previous']['means'] = {20: D(old), 80: D(100)}
            self.assertEqual(s.triggers(prepared([e]), 'FP08')['events'][0]['side'], side)
            e['m15']['previous']['day'] = '2022-01-03'
            self.assertEqual(s.triggers(prepared([e]), 'FP08')['events'], [])
        e['m15']['previous']['day'] = e['day']
        e['m15']['means'][20] = D(100)
        self.assertEqual(s.triggers(prepared([e]), 'FP08')['events'], [])

    def test_gap_short_session_and_outside_clock_block_signals(self):
        for mode in ('FP07', 'FP08'):
            for key, value in (('blocked', True), ('full_session', False), ('slot', 345)):
                e = event(30, 104)
                e['m15']['means'] = {20: D(101), 80: D(100)}
                e['m15']['previous']['means'] = {20: D(99), 80: D(100)}
                e[key] = value
                prefix = channel_events()[:-4] if mode == 'FP07' else []
                self.assertEqual(s.triggers(prepared(prefix + [e]), mode)['events'], [])

    def test_future_change_does_not_remove_earlier_events(self):
        es = channel_events()
        for mode in ('FP07', 'FP08'):
            old = s.triggers(prepared(es), mode)['events']
            changed = deepcopy(es)
            changed[-1]['blocked'] = True
            changed[-1]['m15']['close'] = D(-999)
            new = s.triggers(prepared(changed), mode)['events']
            self.assertEqual([e for e in old if e['t'] < es[-1]['t']], [e for e in new if e['t'] < es[-1]['t']])

    def test_first_signal_selection_precedes_quote_check_and_preserves_zero_periods(self):
        es = [dict(kind='confirm', t=event(slot, 100)['t'], side='BUY') for slot in (30, 45)]
        sessions = {'2022-01-03': [], '2022-01-04': [], '2022-01-10': []}
        pairs = {es[1]['t']: True, es[1]['t'] + 60000: True}
        r = s.cadence(sessions, es, pairs)
        self.assertEqual(r['raw_exact_quote_available'], 1)
        self.assertEqual(r['first_signal_exact_quote_available'], 0)
        self.assertEqual(r['zero_weeks'], 2)
        self.assertEqual(r['max_no_signal_sessions'], 3)
        self.assertEqual(len(r['monthly']), 12)
        with self.assertRaises(ValueError): s.cadence(sessions, es + [es[0]], pairs)


if __name__ == '__main__':
    unittest.main()
