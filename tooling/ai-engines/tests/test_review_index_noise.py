from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from review_index_noise import inspect_funded_scenario, inspect_scenario


def known_trade():
    start = int(datetime(2022, 1, 3, 14, 30, tzinfo=timezone.utc).timestamp()*1000)
    stamps = list(range(start, start+390*60000, 60000))
    entry, exit = stamps[31], stamps[-1]
    trade = dict(position_id='index-1', side='BUY', quantity='1', entry_time_msc=entry,
        entry_fill='101.01', stop='100', exit_fill='102', exit_interval_msc=[exit, exit],
        reason='scheduled_cash_flat', net_usd='-0.51', costs={'net_account': -.51}, path_unresolved=False)
    result = dict(slippage_per_side='.25', decisions=[dict(time_msc=entry-60000, side='BUY', lower='100', upper='100')],
        trades=[trade], balance_usd='9999.49', open_position=None, net_equity_usd='-0.51', closed_trades=1, entries=1)
    pairs = {entry: ({'open': 100.99}, {'open': 101.01}), exit: ({'open': 102}, {'open': 102.02})}
    return result, pairs, {'2022-01-03': stamps}


def known_funded_trade():
    start = int(datetime(2022, 1, 3, 14, 30, tzinfo=timezone.utc).timestamp()*1000)
    entry, exit_at = start+60000, start+180000
    trade = dict(position_id='index-1', side='BUY', quantity='1', entry_time_msc=entry,
        entry_fill='100.2', stop='95.2', exit_fill='102', exit_interval_msc=[exit_at, exit_at],
        reason='strategy_exit', price_net_usd='0.30', funding_usd='0', net_usd='0.30',
        costs={'net_account': .30}, path_unresolved=False)
    result = dict(slippage_per_side='.25', funding_per_lot_per_day='1',
        decisions=[dict(time_msc=start, side='BUY', stop_distance='5'),
                   dict(time_msc=exit_at-60000, side='EXIT', stop_distance='None')],
        trades=[trade], funding_events=[], funding_total_usd='0', balance_usd='10000.30',
        open_position=None, net_equity_usd='0.30', floating_usd='0', closed_trades=1, entries=1)
    pairs = {entry: ({'open': 100, 'close': 100}, {'open': 100.2, 'close': 100.2}),
             exit_at: ({'open': 102, 'close': 102}, {'open': 102.2, 'close': 102.2})}
    return result, pairs


class IndependentArithmeticTests(unittest.TestCase):
    def test_hand_calculated_loss_reconciles(self):
        result, pairs, sessions = known_trade()
        review = inspect_scenario(result, pairs, sessions)
        self.assertEqual(review['net_usd'], '-0.51')
        self.assertEqual(review['losses'], 1)

    def test_changed_net_quote_risk_or_cash_is_rejected(self):
        result, pairs, sessions = known_trade()
        for change in [dict(net_usd='0.51'), dict(entry_fill='100.99'), dict(quantity='20'), dict(stop='99')]:
            altered = deepcopy(result)
            altered['trades'][0].update(change)
            with self.subTest(change=change), self.assertRaises(ValueError):
                inspect_scenario(altered, pairs, sessions)
        result['balance_usd'] = '10000'
        with self.assertRaisesRegex(ValueError, 'cash_reconcile'):
            inspect_scenario(result, pairs, sessions)

    def test_wrong_fill_delay_has_no_matching_decision(self):
        result, pairs, sessions = known_trade()
        result['decisions'][0]['time_msc'] += 60000
        with self.assertRaises(KeyError):
            inspect_scenario(result, pairs, sessions)

    def test_unreviewed_open_or_pending_book_cannot_receive_closed_book_verdict(self):
        for changes in [dict(open_position={'id': 'open'}), dict(pending_action={'side': 'BUY'})]:
            result, pairs, sessions = known_trade()
            result.update(changes)
            with self.subTest(changes=changes), self.assertRaisesRegex(ValueError, 'separate_mark_review'):
                inspect_scenario(result, pairs, sessions)

    def test_unfunded_cross_day_carry_requires_separate_funding_review(self):
        result, pairs, sessions = known_trade()
        trade = result['trades'][0]
        previous = trade['exit_interval_msc'][0]
        exit_at = previous+86400000
        pairs[exit_at] = pairs.pop(previous)
        trade.update(exit_interval_msc=[exit_at, exit_at], reason='delayed_cash_flat')
        with self.assertRaisesRegex(ValueError, 'carry_requires_funded_review'):
            inspect_scenario(result, pairs, sessions)


class FundedBindingTests(unittest.TestCase):
    def test_hand_calculated_funded_trade_reconciles(self):
        result, pairs = known_funded_trade()
        self.assertEqual(inspect_funded_scenario(result, pairs, {})['net_usd'], '0.30')

    def test_recorded_entry_must_match_quote_even_when_pnl_is_unchanged(self):
        result, pairs = known_funded_trade()
        result['trades'][0]['entry_fill'] = '99'
        with self.assertRaisesRegex(ValueError, 'entry_quote_binding'):
            inspect_funded_scenario(result, pairs, {})

    def test_duplicate_position_ids_cannot_be_hidden_by_dictionary_projection(self):
        result, pairs = known_funded_trade()
        result['trades'].append(deepcopy(result['trades'][0]))
        result['entries'] = result['closed_trades'] = 2
        with self.assertRaisesRegex(ValueError, 'duplicate_position_id'):
            inspect_funded_scenario(result, pairs, {})

    def test_closed_trade_counter_must_match_records(self):
        result, pairs = known_funded_trade()
        result['closed_trades'] = 2
        with self.assertRaisesRegex(ValueError, 'position_count'):
            inspect_funded_scenario(result, pairs, {})

    def test_open_position_preserves_both_recorded_entry_sides(self):
        result, pairs = known_funded_trade()
        entry = result['trades'][0]['entry_time_msc']
        result.update(trades=[], closed_trades=0, balance_usd='10000', floating_usd='0.30',
            open_position=dict(id='index-1', time=entry, side='BUY', quantity='1',
                bid='100', ask='100.2', stop='95.2', funding='0', path_unresolved=False))
        self.assertEqual(inspect_funded_scenario(result, pairs, {})['net_usd'], '0.30')
        result['open_position']['bid'] = '99'
        with self.assertRaisesRegex(ValueError, 'entry_quote_binding'):
            inspect_funded_scenario(result, pairs, {})


if __name__ == '__main__':
    unittest.main()
