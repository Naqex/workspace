from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from index_time_series_momentum import input_coverage, plans_for, prepare, simulate


def fixture(direction=1):
    sessions, pairs = {}, {}
    for month in range(14):
        year, number = 2013+month//12, month%12+1
        for day in [1, 2]:
            first = int(datetime(year, number, day, 14, 30, tzinfo=timezone.utc).timestamp()*1000)
            stamps = [first+i*60000 for i in range(3)]
            sessions[f'{year}-{number:02}-{day:02}'] = stamps
            for at in stamps:
                price = 100+direction*month
                bid = dict(timestamp=at, open=price, high=price+1, low=price-.5, close=price, volume=1)
                pairs[at] = (bid, {**bid, **{key: bid[key]+.2 for key in ['open', 'high', 'low', 'close']}})
    return sessions, pairs


class MonthlyTrendTests(unittest.TestCase):
    def test_thirteen_month_endpoints_and_past_atr_have_known_values(self):
        sessions, pairs = fixture()
        plans = plans_for(sessions, pairs)
        first = sessions['2014-02-01'][0]
        self.assertEqual(plans[first]['side'], 'BUY')
        # Seven month-opening TRs are 2 (including the gap); seven are 1.5.
        self.assertEqual(plans[first]['distance'], D('2.625'))
        self.assertTrue(all(plan['side'] == 'EXIT' for at, plan in plans.items() if at < first))

    def test_negative_momentum_and_long_benchmark_share_history_eligibility(self):
        sessions, pairs = fixture(-1)
        first = sessions['2014-02-01'][0]
        self.assertEqual(plans_for(sessions, pairs)[first]['side'], 'SELL')
        self.assertEqual(plans_for(sessions, pairs, always_long=True)[first]['side'], 'BUY')
        del pairs[sessions['2013-06-02'][-1]]
        for control in [False, True]:
            self.assertEqual(plans_for(sessions, pairs, always_long=control)[first]['side'], 'EXIT')

    def test_current_month_future_prices_and_gaps_cannot_change_open_decision(self):
        sessions, pairs = fixture()
        first = sessions['2014-02-01'][0]
        expected = plans_for(sessions, pairs)[first]
        changed = deepcopy(pairs)
        for day, stamps in sessions.items():
            if day.startswith('2014-02'):
                for stamp in stamps:
                    changed.pop(stamp)
        self.assertEqual(plans_for(sessions, changed)[first], expected)

    def test_skipped_calendar_month_is_not_a_twelve_month_return(self):
        sessions, pairs = fixture()
        for day in ['2013-06-01', '2013-06-02']:
            sessions.pop(day)
        self.assertEqual(plans_for(sessions, pairs)[sessions['2014-02-01'][0]]['side'], 'EXIT')

    def test_missing_prior_daily_range_stops_new_entries(self):
        sessions, pairs = fixture()
        del pairs[sessions['2014-01-01'][1]]
        self.assertEqual(plans_for(sessions, pairs)[sessions['2014-02-01'][0]]['side'], 'EXIT')

    def test_coverage_distinguishes_warmup_from_missing_evaluation_year(self):
        sessions, pairs = fixture()
        _, observations = prepare(sessions, pairs)
        self.assertTrue(input_coverage(observations)['admitted'])
        del pairs[sessions['2013-06-02'][-1]]
        _, observations = prepare(sessions, pairs)
        coverage = input_coverage(observations)
        self.assertEqual(coverage['unusable_evaluation_years'], ['2014'])
        self.assertIn('2013-06', observations[-1]['missing_month_closes'])
        with patch('index_time_series_momentum.book.simulate') as numerical:
            with self.assertRaisesRegex(ValueError, 'unusable_evaluation_year'):
                simulate(sessions, pairs, slippage=D('.25'))
            numerical.assert_not_called()

    def test_unavailable_future_fill_is_audit_only_and_cannot_change_signal(self):
        sessions, pairs = fixture()
        first = sessions['2014-02-01'][0]
        before = plans_for(sessions, pairs)[first]
        del pairs[first+60000]
        after, observations = prepare(sessions, pairs)
        self.assertEqual(after[first], before)
        self.assertTrue(observations[-1]['signal_input_eligible'])
        self.assertFalse(observations[-1]['historical_fill_minute_present'])
        self.assertEqual(input_coverage(observations)['unusable_evaluation_years'], ['2014'])


if __name__ == '__main__':
    unittest.main()
