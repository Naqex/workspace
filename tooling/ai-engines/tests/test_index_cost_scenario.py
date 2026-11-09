from contextlib import redirect_stderr
from datetime import datetime, timezone
from decimal import Decimal as D
from io import StringIO
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tooling/ai-engines'))
import index_noise_study as core
import index_m1_book as book
import index_close_momentum as close_policy
from review_index_noise import commission_for_result, inspect_funded_scenario, inspect_scenario
from test_index_daily_reversion import quote
from test_index_close_momentum import fixture as close_fixture
from test_review_index_noise import known_trade


def packet(value):
    return json.loads(json.dumps(value, default=str))


class IndexCostScenarioTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        core.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_default_legacy_retains_known_buy_and_sell_outcomes(self):
        start = 1640995200000
        for side in ['BUY', 'SELL']:
            last = D(105) if side == 'BUY' else D(95)
            pairs = {t: quote(t, D(100) if t < start+180000 else last)
                     for t in [start, start+60000, start+120000, start+180000]}
            plans = {start: dict(side=side, distance=D(5)), start+120000: dict(side='EXIT')}
            kwargs = dict(candidate='fixture', slippage=D('.25'), funding_per_lot=D(1))
            result = book.simulate(pairs, plans, **kwargs)
            explicit = book.simulate(pairs, plans, cost_scenario=core.LEGACY_COST_SCENARIO, **kwargs)
            self.assertEqual(result['trades'], explicit['trades'])
            self.assertEqual(result['trades'][0]['quantity'], '3.84')
            self.assertEqual(result['net_equity_usd'], '12.67')
            inspect_funded_scenario(packet(result), pairs, {})

    def test_zero_commission_resizes_and_reconciles_known_buy_and_sell_profit(self):
        start = 1640995200000
        for side in ['BUY', 'SELL']:
            last = D(105) if side == 'BUY' else D(95)
            pairs = {t: quote(t, D(100) if t < start+180000 else last)
                     for t in [start, start+60000, start+120000, start+180000]}
            plans = {start: dict(side=side, distance=D(5)), start+120000: dict(side='EXIT')}
            result = book.simulate(pairs, plans, candidate='fixture', slippage=D('.25'), funding_per_lot=D(1),
                cost_scenario=core.FTMO_ZERO_COMMISSION)
            # 25/(5 distance + .5 round-trip slippage + .001 grid allowance), floored to .01.
            self.assertEqual(result['trades'][0]['quantity'], '4.54')
            # (4.8 price gain - .5 slippage) * 4.54 = 19.522, rounded to cents.
            self.assertEqual(result['net_equity_usd'], '19.52')
            self.assertEqual(result['commission_per_lot_per_side_usd'], '0')
            self.assertEqual(inspect_funded_scenario(packet(result), pairs, {})['net_usd'], '19.52')

    def test_zero_commission_keeps_spread_slippage_and_weekend_funding(self):
        start = int(datetime(2022, 1, 7, 23, 57, tzinfo=timezone.utc).timestamp()*1000)
        end = int(datetime(2022, 1, 10, tzinfo=timezone.utc).timestamp()*1000)
        pairs = {t: quote(t, D(100)) for t in [start, start+60000, start+120000]}
        result = book.simulate(pairs, {start+60000: dict(side='BUY', distance=D(5))}, candidate='fixture',
            slippage=D('.25'), funding_per_lot=D(1), end_time_msc=end, cost_scenario=core.FTMO_ZERO_COMMISSION)
        self.assertEqual(result['funding_total_usd'], '9.08')
        self.assertEqual(result['floating_usd'], '-3.18')
        self.assertEqual(result['net_equity_usd'], '-12.26')
        inspect_funded_scenario(packet(result), pairs, {})

    def test_unfunded_checker_recomputes_zero_commission_for_both_sides(self):
        for side, expected in [('BUY', '.49'), ('SELL', '2.49')]:
            result, pairs, sessions = known_trade()
            result.update(cost_scenario=core.FTMO_ZERO_COMMISSION, commission_per_lot_per_side_usd='0',
                balance_usd=str(D(10000)+D(expected)), net_equity_usd=expected)
            trade = result['trades'][0]
            trade.update(net_usd=expected, costs={'net_account': expected})
            if side == 'SELL':
                trade.update(side='SELL', entry_fill='100.99', stop='102', exit_fill='98')
                result['decisions'][0].update(side='SELL', upper='102')
                pairs[trade['exit_interval_msc'][0]] = ({'open': 97.98}, {'open': 98})
            self.assertEqual(D(inspect_scenario(result, pairs, sessions)['net_usd']), D(expected))

    def test_result_and_manifest_cost_mismatches_are_rejected(self):
        legacy = dict(slippage_per_side='.25')
        self.assertEqual(commission_for_result(legacy, {}), D('.5'))
        zero = dict(cost_scenario=core.FTMO_ZERO_COMMISSION, commission_per_lot_per_side_usd='0')
        self.assertEqual(commission_for_result(zero, zero), D(0))
        for wrong in [dict(cost_scenario='unknown', commission_per_lot_per_side_usd='0'),
                      dict(cost_scenario=core.FTMO_ZERO_COMMISSION),
                      dict(cost_scenario=core.FTMO_ZERO_COMMISSION, commission_per_lot_per_side_usd='NaN')]:
            with self.subTest(wrong=wrong), self.assertRaisesRegex(ValueError, 'scenario_binding'):
                commission_for_result(wrong)
        with self.assertRaisesRegex(ValueError, 'manifest_result_commission_binding'):
            commission_for_result(zero, {})

    def test_changed_cost_label_cannot_preserve_old_fee_arithmetic(self):
        result, pairs, sessions = known_trade()
        result.update(cost_scenario=core.FTMO_ZERO_COMMISSION, commission_per_lot_per_side_usd='0')
        with self.assertRaisesRegex(ValueError, 'trade_arithmetic'):
            inspect_scenario(result, pairs, sessions)

    def test_unknown_scenario_stops_before_reading_inputs_or_creating_output(self):
        for unknown in ['free-everything', None, []]:
            with self.assertRaisesRegex(ValueError, 'unknown_index_cost_scenario'):
                core.market(D('.25'), cost_scenario=unknown)
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)/'never-created'
            args = ['study', '--source-root', directory, '--data-root', directory, '--calendar', directory,
                    '--protocol', directory, '--output', str(output), '--cost-scenario', 'free-everything']
            with patch.object(sys, 'argv', args), redirect_stderr(StringIO()), self.assertRaises(SystemExit):
                core.main()
            self.assertFalse(output.exists())

    def test_close_policy_propagates_cost_into_sizing_and_stop_loss(self):
        sessions, pairs = close_fixture()
        result = close_policy.simulate(sessions, pairs, slippage=D('.25'), cost_scenario=core.FTMO_ZERO_COMMISSION)
        self.assertEqual(result['cost_scenario'], core.FTMO_ZERO_COMMISSION)
        self.assertEqual(result['entries'], 1)
        self.assertEqual(result['trades'][0]['quantity'], '24.97')
        self.assertEqual(result['net_equity_usd'], '-24.97')
        inspect_funded_scenario(packet(result), pairs, sessions)


if __name__ == '__main__':
    unittest.main()
