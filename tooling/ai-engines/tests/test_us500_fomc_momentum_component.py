from datetime import datetime, timezone
from decimal import Decimal as D
from fractions import Fraction as F
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_us500_overnight_reversal_component import us_market
import index_noise_study as market
import us500_fomc_momentum_component as study


def pair(at, bid):
    return tuple(dict(timestamp=at, open=str(D(bid)+d)) for d in (D(0), D('.2')))


def fixture():
    pairs = {}
    for year in (2019, 2022):
        for s in study.schedule(year):
            for key, price in (('feature_start_ms', '100'), ('feature_end_ms', '101'), ('entry_ms', '103'), ('exit_ms', '110')):
                pairs[s[key]] = pair(s[key], price)
    return pairs


def evaluate(pairs, year=2019, progress=None):
    return study.evaluate(year, pairs, market_function=us_market,
        cost_function=market.calculate_round_trip_cost, progress=progress)


class FomcMomentumTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        market.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_registered_calendar_crossyear_dst_offsets_and_holdout(self):
        rows = study.schedule(2019)+study.schedule(2022)
        self.assertEqual(len(rows), 32)
        self.assertEqual(datetime.fromtimestamp(rows[14]['exit_ms']/1000, study.NY).isoformat(), '2020-01-03T12:01:00-05:00')
        self.assertEqual(datetime.fromtimestamp(rows[30]['exit_ms']/1000, study.NY).isoformat(), '2023-01-06T12:01:00-05:00')
        for s in rows:
            self.assertTrue(s['calendar_endpoints_valid'])
            days = list(study.sessions(s['year']))
            local = lambda k: datetime.fromtimestamp(s[k]/1000, study.NY).date().isoformat()
            self.assertEqual(days.index(local('feature_end_ms'))-days.index(local('feature_start_ms')), 25)
            self.assertLess(s['feature_end_ms']+60000, s['decision_ms'])
        january, july = rows[0], rows[8]
        self.assertEqual(datetime.fromtimestamp(january['entry_ms']/1000, timezone.utc).hour, 19)
        self.assertEqual(datetime.fromtimestamp(july['entry_ms']/1000, timezone.utc).hour, 18)
        for year in (2020, 2023, 2025, True):
            with self.assertRaises(ValueError): study.schedule(year)

    def test_future_exit_never_changes_signal_and_census_precedes_costs(self):
        p = fixture(); base = study.prepare(2019, p)[0]
        p[base['exit_ms']] = pair(base['exit_ms'], '1')
        changed = study.prepare(2019, p)[0]
        for k in ('signal_side', 'signal_known', 'feature_midpoint_change', 'entry_ms'):
            self.assertEqual(base[k], changed[k])
        phases = []; evaluate(p, progress=lambda phase, _: phases.append(phase))
        self.assertEqual(phases, ['source_feature_endpoint_census_before_costs'])

    def test_missing_feature_is_unknown_not_flat_and_buy_null_remain_separate(self):
        p = fixture(); s = study.schedule(2019)[0]; del p[s['feature_end_ms']]
        r = evaluate(p)[0]['outcomes']['stress']
        self.assertFalse(r['primary']['resolved']); self.assertIsNone(r['primary']['net_usd_per_research_unit'])
        self.assertTrue(r['always_long_control']['resolved']); self.assertEqual(r['null']['net_usd_per_research_unit'], '0')

    def test_flat_missing_and_crossed_entry_exit(self):
        for key in ('entry_ms', 'exit_ms'):
            for bad in ('missing', 'crossed'):
                p = fixture(); s = study.schedule(2019)[0]
                if bad == 'missing': del p[s[key]]
                else: p[s[key]][1]['open'] = '1'
                r = evaluate(p)[0]['outcomes']['reference']
                self.assertFalse(r['primary']['resolved']); self.assertTrue(r['null']['resolved'])
        p = fixture(); s = study.schedule(2019)[0]
        p[s['feature_end_ms']] = pair(s['feature_end_ms'], '100')
        r = evaluate(p)[0]['outcomes']['stress']['primary']
        self.assertTrue(r['resolved']); self.assertIsNone(r['side']); self.assertEqual(r['funding_events'], [])
        self.assertEqual(r['net_usd_per_research_unit'], '0')

    def test_buy_sell_costs_funding_with_fraction_oracle(self):
        r = evaluate(fixture())[0]
        for scenario, slip, annual in (('reference', F(1, 4), F(8, 100)), ('stress', F(3, 4), F(16, 100))):
            events = r['outcomes'][scenario]['primary']['funding_events']
            count = sum(r['entry_ms'] < at <= r['exit_ms'] for at in range(
                r['entry_ms']//86400000*86400000, r['exit_ms']+86400000, 86400000) for at in [at+22*3600000])
            debit = F('103.2')*annual/365
            cents = (debit*100+F(1, 2)).numerator//(debit*100+F(1, 2)).denominator
            funding = F(cents, 100)*count
            self.assertEqual(len(events), count)
            for rule, price in (('primary', F(110)-F('103.2')), ('opposite_control', F(103)-F('110.2'))):
                out = r['outcomes'][scenario][rule]
                self.assertEqual(F(out['net_usd_per_research_unit']), price-2*slip-funding)
        boundary = 22*3600000
        self.assertEqual(len(study.funding(boundary, boundary+86400000, '100', D('.08'))), 1)
        self.assertEqual(len(study.funding(boundary-1, boundary, '100', D('.08'))), 1)
        self.assertEqual(len(study.funding(boundary-1, boundary-1, '100', D('.08'))), 0)

    def test_summary_census_unknown_gate_and_authority(self):
        p = fixture(); rows = evaluate(p)+evaluate(p, 2022)
        summary = study.summarize(rows)
        self.assertEqual(len(summary['books']), 32)
        self.assertEqual(sum(b['planned'] for b in summary['books']), 256)
        self.assertFalse(summary['execution_authorized']); self.assertFalse(summary['account_simulated'])
        for changed in (rows[:-1], rows[::-1]):
            with self.assertRaises(ValueError): study.summarize(changed)
        del p[study.schedule(2019)[0]['feature_end_ms']]
        summary = study.summarize(evaluate(p)+evaluate(p, 2022))
        self.assertFalse(summary['retained_for_further_research'])
        self.assertIsNone(summary['year_gates'][0]['primary_stress_net'])


if __name__ == '__main__': unittest.main()
