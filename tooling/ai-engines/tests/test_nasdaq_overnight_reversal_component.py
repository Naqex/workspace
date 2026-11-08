from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import nasdaq_overnight_reversal_component as study
import nasdaq_h4_study as market
from nasdaq_cash_calendar import sessions_for

ROOT = Path(__file__).resolve().parents[3]


def fixture(day='2019-01-02', gap=10):
    year = int(day[:4])
    calendar = {**sessions_for(f'warmup-{year}'), **sessions_for(f'development-{year}')}
    days = list(calendar); ix = days.index(day); previous = days[ix-1]
    sessions = {d: calendar[d] for d in (previous, day)}
    pairs = {}
    for stamps in sessions.values():
        for at in stamps:
            pairs[at] = tuple(dict(timestamp=at, open=str(D(100)+offset), high=str(D(101)+offset),
                low=str(D(99)+offset), close=str(D(100)+offset)) for offset in (D(0), D('.2')))
    stamps = sessions[day]
    for at, price in ((stamps[0], 100+gap), (stamps[2], 100+gap), (stamps[29], 100+gap/2)):
        for row, offset in zip(pairs[at], (D(0), D('.2'))):
            row.update(open=str(D(str(price))+offset))
    start = stamps[0] // study.DAY * study.DAY
    return sessions, pairs, stamps, start, start+study.DAY


def evaluate(case):
    sessions, pairs, _, start, end = case
    return study.evaluate(sessions, pairs, start=start, end=end,
        market_function=market.market, cost_function=market.calculate_round_trip_cost)['rows'][0]


class OvernightReversalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        market.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_sell_buy_exact_delay_bidask_and_controls(self):
        for gap, side in ((10, 'SELL'), (-10, 'BUY')):
            row = evaluate(fixture(gap=gap))
            self.assertEqual(row['signal_side'], side)
            self.assertEqual(row['decision_ms'], row['signal_known_at_ms'])
            self.assertEqual(row['entry_ms']-row['decision_ms'], 60000)
            self.assertEqual(row['exit_ms']-row['entry_ms'], 27*60000)
            for scenario, net in (('reference', '4.30'), ('stress', '3.30')):
                self.assertEqual(D(row['outcomes'][scenario]['primary']['net_usd_per_research_unit']), D(net))
                self.assertEqual(set(row['outcomes'][scenario]), set(study.ROLES))
                self.assertEqual(row['outcomes'][scenario]['primary']['side'], side)
            self.assertFalse(row['execution_authorized']); self.assertFalse(row['account_simulated'])

    def test_flat_missing_and_crossed_predictor_are_distinct(self):
        row = evaluate(fixture(gap=0)); self.assertEqual(row['status'], 'valid_flat_gap')
        self.assertTrue(row['predictor_valid']); self.assertFalse(row['planned_trade'])
        for target in ('current', 'previous'):
            for mode in ('missing', 'crossed'):
                case = fixture(); sessions, pairs, stamps, _, _ = case
                at = stamps[0] if target == 'current' else next(iter(sessions.values()))[-1]
                if mode == 'missing': del pairs[at]
                else: pairs[at][1]['open' if target == 'current' else 'close'] = '1'
                row = evaluate(case)
                self.assertEqual(row['status'], 'signal_unavailable'); self.assertFalse(row['outcomes'])

    def test_previous_halfday_holiday_and_dst(self):
        for day, utc_hour in (('2019-01-02', 14), ('2019-07-05', 13), ('2022-11-28', 14)):
            case = fixture(day); sessions, _, stamps, _, _ = case
            if day != '2019-01-02': self.assertEqual(len(next(iter(sessions.values()))), 210)
            row = evaluate(case)
            self.assertTrue(row['planned_trade'])
            dt = datetime.fromtimestamp(row['entry_ms']/1000, timezone.utc)
            self.assertEqual((dt.hour, dt.minute), (utc_hour, 32))
            self.assertEqual(row['previous_close_ms'], next(iter(sessions.values()))[-1])
        self.assertEqual(evaluate(fixture('2019-11-29'))['status'], 'calendar_halfday_skipped')

    def test_endpoint_missing_crossed_remains_planned_unresolved(self):
        for offset in (2, 29):
            for mode in ('missing', 'crossed'):
                case = fixture(); pairs, stamps = case[1:3]
                if mode == 'missing': del pairs[stamps[offset]]
                else: pairs[stamps[offset]][1]['open'] = '1'
                row = evaluate(case)
                self.assertTrue(row['planned_trade']); self.assertFalse(row['outcomes'])
                self.assertEqual(row['status'], 'unresolved_endpoint')

    def test_future_prices_and_missing_future_do_not_change_signal(self):
        case = fixture(); baseline = evaluate(case)
        for at in list(case[1]):
            if at >= baseline['entry_ms']: del case[1][at]
        changed = evaluate(case)
        for key in ('signal_side', 'planned_trade', 'gap_bid_price_units', 'decision_ms', 'entry_ms'):
            self.assertEqual(changed[key], baseline[key])
        self.assertFalse(changed['outcomes'])

    def test_bad_clock_grid_calendar_identity_and_holdout(self):
        for offset in (0, 2, 29):
            for mode in ('clock', 'grid'):
                case = fixture(); row = case[1][case[2][offset]][0]
                row['timestamp' if mode == 'clock' else 'open'] = 1 if mode == 'clock' else '100.0001'
                with self.subTest(offset=offset, mode=mode), self.assertRaises(ValueError): evaluate(case)
        case = fixture(); case[0][next(reversed(case[0]))][0] += 60000
        with self.assertRaises(ValueError): evaluate(case)
        case = fixture(); sessions, pairs, _, start, end = case
        with self.assertRaisesRegex(ValueError, 'holdout'):
            study.prepare(sessions, pairs, start=start, end=1767225600000)
        with self.assertRaisesRegex(ValueError, 'window'):
            study.prepare(sessions, pairs, start=True, end=end)
        from types import SimpleNamespace
        with self.assertRaisesRegex(ValueError, 'geometry'):
            study.evaluate(sessions, pairs, start=start, end=end, cost_function=market.calculate_round_trip_cost,
                market_function=lambda s: (SimpleNamespace(instrument_id='US500', contract_size=1), None, None))

    def test_census_control_gate_and_authority_guards(self):
        template = evaluate(fixture()); expected = {}; rows = []
        for year in (2019, 2022):
            expected[year] = list(sessions_for(f'development-{year}'))[:100]
            for day in expected[year]:
                row = deepcopy(template); row.update(year=year, session=day)
                for scenario in study.SCENARIOS:
                    for role in study.ROLES:
                        row['outcomes'][scenario][role]['net_usd_per_research_unit'] = '3' if role == 'primary' else '1'
                rows.append(row)
        self.assertTrue(study.summarize(rows, expected)['retained_for_further_research'])
        for mode in ('predictor', 'endpoint', 'control'):
            changed = deepcopy(rows)
            if mode == 'predictor':
                for row in changed[:3]: row['predictor_valid'] = False
            elif mode == 'endpoint':
                for row in changed[:3]: row['outcomes'] = {}
            else: changed[0]['outcomes']['stress']['always_short_control']['net_usd_per_research_unit'] = '1000'
            self.assertFalse(study.summarize(changed, expected)['retained_for_further_research'])
        for mode in ('missing', 'authority', 'nan'):
            changed = deepcopy(rows)
            if mode == 'missing': changed.pop()
            elif mode == 'authority': changed[0]['execution_authorized'] = True
            else: changed[0]['outcomes']['stress']['primary']['net_usd_per_research_unit'] = 'NaN'
            with self.subTest(mode=mode), self.assertRaises(ValueError): study.summarize(changed, expected)


if __name__ == '__main__':
    unittest.main()
