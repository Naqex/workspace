from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from nasdaq_cash_calendar import sessions_for
from test_us500_overnight_reversal_component import us_market
import index_noise_study as market
import nasdaq_h4_study as nasdaq
import us500_euopen_component as study


def pair(at, bid):
    return tuple(dict(timestamp=at, open=str(D(bid)+offset), high=str(D(bid)+offset+1),
        low=str(D(bid)+offset-1), close=str(D(bid)+offset), volume=0) for offset in (D(0), D('.2')))


def fixture(year=2019, all_days=False):
    sessions = sessions_for(f'development-{year}'); specs = study.schedule(year, sessions)
    selected = [s for s in specs if s['planned_trade']]
    if not all_days: selected = selected[:1]
    pairs = {}
    for s in selected:
        for at in range(s['entry_ms'], s['exit_ms'], 60000): pairs[at] = pair(at, '111.003')
        pairs[s['exit_ms']] = pair(s['exit_ms'], '115')
    return sessions, pairs


def evaluate(year=2019, all_days=False):
    sessions, pairs = fixture(year, all_days)
    return study.evaluate(year, sessions, pairs, market_function=us_market, cost_function=market.calculate_round_trip_cost)


class EUOpenTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        root = Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2'
        market.bind_core(root); nasdaq.bind_core(root)

    def test_cross_midnight_dst_monday_and_halfday_calendar(self):
        specs = study.schedule(2019, sessions_for('development-2019')); by_day = {s['session']: s for s in specs}
        for day, hour in [('2019-01-02', 4), ('2019-03-08', 4), ('2019-03-11', 3), ('2019-07-05', 3)]:
            s = by_day[day]
            utc = datetime.fromtimestamp(s['entry_ms']/1000, timezone.utc)
            self.assertEqual((utc.hour, utc.minute), (hour, 31))
            self.assertEqual(s['exit_ms']-s['entry_ms'], 14400000)
        monday = by_day['2019-03-11']; local = datetime.fromtimestamp(monday['entry_ms']/1000, study.NY)
        self.assertEqual((local.date().isoformat(), local.weekday()), ('2019-03-10', 6))
        self.assertFalse(by_day['2019-11-29']['planned_trade'])
        self.assertEqual(len(specs), 252); self.assertEqual(sum(s['planned_trade'] for s in specs), 249)

    def test_exact_bidask_subcent_costs_null_and_declared_no_rollover(self):
        row = evaluate()['rows'][0]
        self.assertEqual(row['status'], 'resolved_price_component_not_account')
        self.assertEqual((row['path_expected_minutes'], row['path_observed_minutes']), (240, 240))
        self.assertEqual(row['funding_events'], [])
        for scenario, primary, opposite in [('reference', '3.30', '-4.70'), ('stress', '2.30', '-5.70')]:
            values = row['outcomes'][scenario]
            self.assertEqual(D(values['primary']['net_usd_per_research_unit']), D(primary))
            self.assertEqual(D(values['opposite_control']['net_usd_per_research_unit']), D(opposite))
            self.assertEqual(D(str(values['primary']['costs']['gross_quote'])), D('3.797'))
            self.assertIsNone(values['null_no_exposure']['costs']); self.assertTrue(values['null_no_exposure']['no_exposure'])
        self.assertFalse(row['account_simulated']); self.assertFalse(row['execution_authorized'])

    def test_missing_crossed_and_internal_gap_preserve_planned_calendar(self):
        for mode in ('entry', 'exit', 'crossed', 'internal'):
            sessions, pairs = fixture(); s = study.schedule(2019, sessions)[0]
            at = s['entry_ms'] if mode in ('entry', 'crossed') else s['exit_ms'] if mode == 'exit' else s['entry_ms']+60000
            if mode == 'crossed': pairs[at][1]['open'] = '1'
            else: del pairs[at]
            row = study.evaluate(2019, sessions, pairs, market_function=us_market, cost_function=market.calculate_round_trip_cost)['rows'][0]
            self.assertTrue(row['planned_trade']); self.assertEqual(bool(row['outcomes']), mode == 'internal')
            if mode == 'internal': self.assertEqual(row['path_observed_minutes'], 239)

    def test_future_exit_mutation_changes_no_entry_schedule_and_prepares_before_costs(self):
        sessions, pairs = fixture(); original = study.prepare(2019, sessions, pairs)
        first = original['rows'][0]; del pairs[first['exit_ms']]
        changed = study.prepare(2019, sessions, pairs)['rows'][0]
        for key in ('planned_trade', 'decision_ms', 'entry_ms', 'exit_ms', 'entry'): self.assertEqual(first[key], changed[key])
        phases = []; calls = []
        def cost(*args):
            self.assertEqual(phases[0], 'source_prepared_before_costs'); calls.append(1)
            return market.calculate_round_trip_cost(*args)
        sessions, pairs = fixture()
        study.evaluate(2019, sessions, pairs, market_function=us_market, cost_function=cost, progress=lambda phase, _: phases.append(phase))
        self.assertEqual(len(calls), 4)

    def test_calendar_scope_grid_clock_and_market_identity_guards(self):
        sessions, pairs = fixture()
        for year in (True, 2025):
            with self.assertRaises(ValueError): study.schedule(year, sessions)
        bad = dict(sessions); bad.pop(next(iter(bad)))
        with self.assertRaisesRegex(ValueError, 'census'): study.schedule(2019, bad)
        first = study.schedule(2019, sessions)[0]
        for key, value in [('open', '111.0001'), ('timestamp', 1)]:
            changed = deepcopy(pairs); changed[first['entry_ms']][0][key] = value
            with self.assertRaises(ValueError): study.prepare(2019, sessions, changed)
        with self.assertRaisesRegex(ValueError, 'geometry'):
            study.evaluate(2019, sessions, pairs, market_function=nasdaq.market, cost_function=market.calculate_round_trip_cost)

    def test_summary_census_unknowns_quarters_and_authority(self):
        rows = [r for year in (2019, 2022) for r in evaluate(year, True)['rows']]
        original = deepcopy(rows); result = study.summarize(rows)
        self.assertTrue(result['retained_for_further_research']); self.assertEqual(rows, original)
        self.assertTrue(all(s['resolved_exposure_cases']==0 for s in result['summary'] if s['role']=='null_no_exposure'))
        primary = next(s for s in result['summary'] if s['year']==2019 and s['scenario']=='stress' and s['role']=='primary')
        self.assertEqual(sum(D(q['known_net_usd_per_research_unit']) for q in primary['quarters']), D(primary['known_net_usd_per_research_unit']))
        bad = deepcopy(rows)
        for row in [r for r in bad if r['year']==2019 and r['planned_trade']][:6]: row['outcomes'] = {}
        self.assertFalse(study.summarize(bad)['retained_for_further_research'])
        for mode in ('duplicate', 'authority', 'funding'):
            bad = deepcopy(rows)
            if mode == 'duplicate': bad[-1] = deepcopy(bad[-2])
            elif mode == 'authority': bad[0]['execution_authorized'] = True
            else: bad[0]['funding_events'] = [dict(time_msc=1)]
            with self.assertRaises(ValueError): study.summarize(bad)


if __name__ == '__main__': unittest.main()
