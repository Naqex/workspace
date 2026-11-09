from copy import deepcopy
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_index_rest_of_day_component import fixture, evaluate as parent_evaluate
from test_us500_overnight_reversal_component import us_market
from nasdaq_cash_calendar import sessions_for
import index_cash_close_tick_component as study
import index_noise_study as market
import nasdaq_h4_study as nasdaq


def hour(spec, profile, role, *, bid=111003, wait=17):
    decision = spec['decision_ms'] + (1800000 if role == 'exit_hour' else 0)
    return dict(schema='index-source-hour-review-v1', instrument='usa500idxusd' if profile == 'us500' else 'usatechidxusd',
        role=role, session=spec['session'], year=spec['year'], execution_authorized=False,
        exposure='consumed_development', price_grid='0.001', price_unit='quoted_index_points',
        timestamp_unit='UTC_ms_archived_event_not_arrival', ticks=100,
        late_predictor=dict(canonical_present=True, ticks_present=True, close_exact=True) if role == 'entry_hour' else None,
        availability=[dict(scenario_delay_ms=delay, target_ms=decision+delay,
            quote=dict(timestamp=decision+delay+wait, source_ordinal=3, wait_ms=wait, bid_units=bid, ask_units=bid+200),
            available_within_60s_after_target=wait<=60000) for delay in [200, *study.DELAYS]])


def case(profile='us500', *, late=110, first=90):
    spec = parent_evaluate(fixture(late=late, first=first), profile)
    return spec, hour(spec, profile, 'entry_hour'), hour(spec, profile, 'exit_hour', bid=115000)


def evaluate(data, *, profile='us500', delay=1000):
    return study.evaluate_spec(*data, profile=profile, delay_ms=delay,
        market_function=us_market if profile == 'us500' else nasdaq.market,
        cost_function=market.calculate_round_trip_cost)


def cents(value):
    sign = 1 if value >= 0 else -1
    v = abs(value)*100+F(1, 2)
    return sign*F(v.numerator//v.denominator, 100)


class CashCloseTickTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2'
        market.bind_core(root); nasdaq.bind_core(root)

    def test_both_profiles_sides_delays_and_costs_match_fraction(self):
        count = 0
        for profile in ('us500', 'nasdaq'):
            for late in (90, 110):
                data = case(profile, late=late)
                for delay in study.DELAYS:
                    row = evaluate(data, profile=profile, delay=delay)
                    self.assertEqual(row['exit_decision_ms']-row['decision_ms'], 1800000)
                    self.assertEqual(row['entry']['tick_timestamp_ms']-row['decision_ms'], delay+17)
                    self.assertFalse(row['execution_authorized']); self.assertFalse(row['account_simulated'])
                    self.assertFalse(row['entry']['executable_tick_proven'])
                    for scenario, slip in [('reference', F(1, 4)), ('stress', F(3, 4))]:
                        for role, got in row['outcomes'][scenario].items():
                            gross = F(115000-111203, 1000) if got['side'] == 'BUY' else F(111003-115200, 1000)
                            costs = got['costs']
                            self.assertEqual(F(str(costs['gross_quote'])), gross)
                            self.assertEqual(F(str(costs['gross_account'])), cents(gross))
                            self.assertEqual(F(got['net_usd_per_research_unit']), cents(gross-2*slip))
                            self.assertEqual(F(str(costs['slippage_account'])), 2*slip)
                            self.assertEqual(costs['commission_account'], 0)
                            count += 1
        self.assertEqual(count, 120)

    def test_expiry_inclusive_missing_quotes_preserve_planned_unknown(self):
        for role in (1, 2):
            for wait in (60000, 60001, None):
                data = case()
                for item in data[role]['availability']:
                    if wait is None: item['quote'] = None
                    else: item['quote'].update(wait_ms=wait, timestamp=item['target_ms']+wait)
                    item['available_within_60s_after_target'] = wait is not None and wait <= 60000
                row = evaluate(data)
                self.assertTrue(row['planned_trade'])
                self.assertEqual(bool(row['outcomes']), wait == 60000)
                if wait != 60000: self.assertEqual(row['status'], 'unresolved_endpoint')

    def test_future_exit_change_cannot_change_signal_or_entry(self):
        data = case(); before = evaluate(data)
        for item in data[2]['availability']:
            item['quote'] = None; item['available_within_60s_after_target'] = False
        after = evaluate(data)
        for key in ('signal_side', 'planned_trade', 'predictor_valid', 'decision_ms', 'entry'):
            self.assertEqual(before[key], after[key])
        self.assertTrue(before['outcomes']); self.assertFalse(after['outcomes'])

    def test_preentry_confirmation_flat_signal_and_flat_control(self):
        for confirmation in (None, dict(canonical_present=False, ticks_present=True, close_exact=None),
                             dict(canonical_present=True, ticks_present=True, close_exact=False)):
            data = case(); data[1]['late_predictor'] = confirmation; row = evaluate(data)
            self.assertFalse(row['planned_trade']); self.assertFalse(row['predictor_valid'])
        row = evaluate(case(late=100)); self.assertEqual(row['status'], 'valid_flat_rod')
        self.assertFalse(row['planned_trade']); self.assertFalse(row['outcomes'])
        row = evaluate(case(first=100))
        for values in row['outcomes'].values():
            self.assertIsNone(values['first_half_control']['costs'])
            self.assertEqual(values['first_half_control']['net_usd_per_research_unit'], '0')

    def test_bad_quote_clock_units_census_and_scope_rejected(self):
        for mode in ('target', 'clock', 'ordinal', 'crossed', 'bool', 'availability', 'role', 'market', 'units', 'authority', 'parent'):
            data = case(); item = data[1]['availability'][1]
            if mode == 'target': item['target_ms'] += 1
            elif mode == 'clock': item['quote']['timestamp'] -= 1
            elif mode == 'ordinal': item['quote']['source_ordinal'] = 100
            elif mode == 'crossed': item['quote']['ask_units'] = 1
            elif mode == 'bool': item['quote']['bid_units'] = True
            elif mode == 'availability': item['available_within_60s_after_target'] = False
            elif mode == 'role': data[1]['role'] = 'exit_hour'
            elif mode == 'market': data[1]['instrument'] = 'usatechidxusd'
            elif mode == 'units': data[1]['price_grid'] = '0.01'
            elif mode == 'authority': data[0]['execution_authorized'] = True
            elif mode == 'parent': data[0]['candidate'] = 'other'
            with self.subTest(mode=mode), self.assertRaises(ValueError): evaluate(data)
        for profile, delay in [(True, 1000), ('us500', True), ('us500', 200), ('us500', 1000.0)]:
            with self.assertRaises(ValueError): evaluate(case(), profile=profile, delay=delay)
        with self.assertRaisesRegex(ValueError, 'geometry'):
            study.evaluate_spec(*case(), profile='us500', delay_ms=1000,
                market_function=nasdaq.market, cost_function=market.calculate_round_trip_cost)

    def test_summary_requires_all_scenarios_years_and_retains_unknown_census(self):
        template = evaluate(case()); expected = {y: list(sessions_for(f'development-{y}'))[:100] for y in (2019, 2022)}
        # Synthetic outcomes over calendar labels, not a historical market result.
        rows = []
        for delay in study.DELAYS:
            for year in (2019, 2022):
                for day in expected[year]:
                    row = deepcopy(template); row.update(delay_ms=delay, year=year, session=day)
                    for values in row['outcomes'].values():
                        for role in study.ROLES: values[role]['net_usd_per_research_unit'] = '3' if role == 'primary' else '1'
                    rows.append(row)
        self.assertTrue(study.summarize(rows, expected, profile='us500')['retained_for_further_research'])
        for mode in ('control', 'unknown', 'coverage'):
            bad = deepcopy(rows)
            if mode == 'control': bad[-1]['outcomes']['stress']['first_half_control']['net_usd_per_research_unit'] = '1000'
            elif mode == 'unknown':
                for row in bad[-3:]: row['outcomes'] = {}
            else:
                for row in bad[-3:]: row.update(predictor_valid=False, planned_trade=False, outcomes={})
            self.assertFalse(study.summarize(bad, expected, profile='us500')['retained_for_further_research'])
        for bad in (rows[:-1], rows+[rows[-1]], rows[::-1]):
            with self.assertRaisesRegex(ValueError, 'scenario_day'): study.summarize(bad, expected, profile='us500')
        bad = deepcopy(rows); bad[0]['predictor_valid'] = False
        with self.assertRaisesRegex(ValueError, 'signal_state'): study.summarize(bad, expected, profile='us500')


if __name__ == '__main__': unittest.main()
