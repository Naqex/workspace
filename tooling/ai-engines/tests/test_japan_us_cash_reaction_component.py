from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import japan_us_cash_reaction_component as study
from nasdaq_cash_calendar import calendar_for
from sealed_m1_review import cash_sessions


def setup(year=2019):
    closes = sorted(minutes[-1]+60000 for y in (year-1, year) for minutes in cash_sessions(calendar_for(y)).values())
    specs = study.schedules(year, [], closes)
    return specs, closes


def pair(at, price, field='open'):
    return tuple(dict(timestamp=at, open=str(D(price)+s), close=str(D(price)+s)) for s in (D(0), D('.5')))


def fixture(year=2019):
    specs, _ = setup(year); spec = next(s for s in specs if s['calendar_eligible'])
    us = {spec['prior_US_close_ms']-60000: pair(spec['prior_US_close_ms']-60000, '100'),
          spec['latest_US_close_ms']-60000: pair(spec['latest_US_close_ms']-60000, '101')}
    jp = {at: pair(at, '20000') for at in range(spec['entry_ms'], spec['exit_ms']+60000, 60000)}
    jp[spec['exit_ms']] = pair(spec['exit_ms'], '19990')
    return specs, spec, us, jp


class JapanCashTests(unittest.TestCase):
    def test_cross_zone_cash_clock_DST_stale_holiday_and_holdout(self):
        specs, closes = setup()
        jan = next(s for s in specs if s['session']=='2019-01-10')
        july = next(s for s in specs if s['session']=='2019-07-15')
        for spec in (jan, july):
            self.assertEqual(datetime.fromtimestamp(spec['decision_ms']/1000, timezone.utc).strftime('%H:%M'), '00:00')
            self.assertLess(spec['latest_US_close_ms'], spec['decision_ms'])
            self.assertEqual(spec['exit_ms']-spec['entry_ms'], 28*60000)
        self.assertEqual(datetime.fromtimestamp(jan['latest_US_close_ms']/1000, timezone.utc).hour, 21)
        self.assertEqual(datetime.fromtimestamp(july['latest_US_close_ms']/1000, timezone.utc).hour, 20)
        changed = study.schedules(2019, ['2019-01-10'], closes)
        self.assertNotIn('2019-01-10', [s['session'] for s in changed])
        stale = next(s for s in specs if s['session']=='2019-01-22')
        self.assertFalse(stale['calendar_eligible'])
        for y in (2023, 2025, True):
            with self.assertRaises(ValueError): study.schedules(y, [], closes)

    def test_close_not_open_feature_future_invariance_and_side_costs(self):
        specs, spec, us, jp = fixture()
        us[spec['latest_US_close_ms']-60000][0]['open']='1'
        rows = study.prepare([spec], us, jp)
        self.assertEqual(rows[0]['signal_side'], 'SELL')
        self.assertTrue(rows[0]['strict_roles_admitted'])
        out = study.evaluate(rows)[0]['outcomes']
        self.assertEqual(D(out['stress']['primary']['net_jpy_per_research_unit']), D('3.5'))
        self.assertEqual(D(out['stress']['always_long_control']['net_jpy_per_research_unit']), D('-16.5'))
        before = rows[0]['feature_mid_close_change']
        jp[spec['exit_ms']] = pair(spec['exit_ms'], '30000')
        self.assertEqual(study.prepare([spec], us, jp)[0]['feature_mid_close_change'], before)

    def test_missing_internal_crossed_feature_unknown_flat_null(self):
        _, spec, us, jp = fixture(); del jp[spec['entry_ms']+60000]
        row = study.evaluate(study.prepare([spec], us, jp))[0]
        self.assertFalse(row['outcomes']['stress']['primary']['resolved'])
        self.assertEqual(row['outcomes']['stress']['null']['net_jpy_per_research_unit'], '0')
        _, spec, us, jp = fixture()
        us[spec['latest_US_close_ms']-60000][1]['close']='1'
        row = study.evaluate(study.prepare([spec], us, jp))[0]
        self.assertFalse(row['signal_known']); self.assertFalse(row['outcomes']['stress']['primary']['resolved'])
        self.assertTrue(row['outcomes']['stress']['always_long_control']['resolved'])
        us[spec['latest_US_close_ms']-60000] = pair(spec['latest_US_close_ms']-60000, '100')
        row = study.evaluate(study.prepare([spec], us, jp))[0]
        self.assertEqual(row['feature_mid_close_change'], '0.0')
        self.assertIsNone(row['outcomes']['stress']['primary']['side'])
        self.assertEqual(row['outcomes']['stress']['primary']['net_jpy_per_research_unit'], '0')

    def test_stale_is_known_skip_and_summary_unknown_counts(self):
        rows=[]
        for year in (2019, 2022):
            specs, _ = setup(year)
            prepared = study.prepare(specs, {}, {})
            rows.extend(study.evaluate(prepared))
        report = study.summarize(rows)
        self.assertEqual(len(report['books']), 20); self.assertFalse(report['retained_for_gap_and_risk_review'])
        self.assertTrue(any(r['calendar_skip_reason'] for r in rows))
        for r in rows:
            if not r['calendar_eligible']:
                self.assertTrue(r['outcomes']['stress']['primary']['calendar_skipped'])
                self.assertTrue(r['outcomes']['stress']['primary']['resolved'])
        for book in report['books']:
            if book['rule']=='null': self.assertEqual(book['unknown'],0)
            else: self.assertIsNone(book['full_eligible_net'])
        with self.assertRaises(ValueError): study.summarize(rows+[deepcopy(rows[0])])


if __name__ == '__main__': unittest.main()
