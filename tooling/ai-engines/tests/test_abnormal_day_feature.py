from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abnormal_day_feature as study

ENTRY = date(2022, 2, 1)


def observation(day, change):
    def point(hour, mid):
        return dict(time_msc=study.utc_ms(day, hour), known_at_upper_bound_ms=study.utc_ms(day, hour)+60000,
            bid=str(mid - Decimal('.00001')), ask=str(mid + Decimal('.00001')))
    return dict(day=day.isoformat(), start=point(0, Decimal(1)), end=point(20, Decimal(1)+change))


def fixture(shock='.01000', shift='0'):
    day = ENTRY - timedelta(days=1)
    # Sum=0, sum of squared integer units=76, sample variance=76/19=4.
    changes = [4, -4, 3, -3, 3, -3, 2, -2] + [0] * 12
    obs = {d.isoformat(): observation(d, Decimal(n)/1000 + Decimal(shift))
        for d, n in zip(study.calibration_days(day), changes)}
    obs[day.isoformat()] = observation(day, Decimal(shock))
    return obs


class AbnormalDayFeatureTests(unittest.TestCase):
    def test_positive_negative_and_strict_boundary(self):
        for change, expected in [('.01000', 'SELL'), ('-.01000', 'BUY'), ('.00400', None),
                                 ('-.00400', None), ('.00401', 'SELL'), ('-.00401', 'BUY')]:
            row = study.feature(ENTRY, fixture(change))
            self.assertEqual(row['primary_side'], expected)
            self.assertEqual(row['calibration_mean'], dict(numerator=0, denominator=1))
            self.assertEqual(row['calibration_sample_variance'], dict(numerator=1, denominator=250000))
            self.assertFalse(row['execution_authorized'])

    def test_calibration_excludes_shock_and_future_outcomes(self):
        obs = fixture()
        baseline = study.feature(ENTRY, obs)
        self.assertNotIn(baseline['shock_day'], baseline['calibration_days'])
        obs[ENTRY.isoformat()] = {'not_a_valid_source': 'future quote must not be consumed'}
        obs[(ENTRY+timedelta(days=1)).isoformat()] = None
        self.assertEqual(study.feature(ENTRY, obs), baseline)
        changed = fixture('-.01000')
        row = study.feature(ENTRY, changed)
        self.assertEqual(row['calibration_mean'], baseline['calibration_mean'])
        self.assertEqual(row['calibration_sample_variance'], baseline['calibration_sample_variance'])

    def test_missing_is_not_backfilled_and_zero_variance_is_unavailable(self):
        obs = fixture()
        removed = study.calibration_days(ENTRY-timedelta(days=1))[0]
        del obs[removed.isoformat()]
        older = removed-timedelta(days=1)
        obs[older.isoformat()] = observation(older, Decimal('.01000'))
        row = study.feature(ENTRY, obs)
        self.assertEqual(row['status'], 'unavailable_history')
        self.assertEqual(row['missing_days'], [removed.isoformat()])
        flat = {key: observation(date.fromisoformat(key), Decimal(0)) for key in fixture()}
        self.assertEqual(study.feature(ENTRY, flat)['status'], 'unavailable_zero_variance')

    def test_source_clock_grid_sign_and_calendar(self):
        key = (ENTRY-timedelta(days=1)).isoformat()
        for kind in ('future', 'offgrid', 'crossed', 'wrong_day'):
            obs = deepcopy(fixture())
            if kind == 'future': obs[key]['end']['known_at_upper_bound_ms'] = study.schedule(ENTRY)['decision_ms']
            if kind == 'offgrid': obs[key]['start']['bid'] = '0.999991'
            if kind == 'crossed': obs[key]['start']['ask'] = '0.9'
            if kind == 'wrong_day': obs[key]['day'] = '2022-01-30'
            with self.assertRaises(ValueError): study.feature(ENTRY, obs)
        obs = fixture(); obs[key]['end']['time_msc'] += 60001; obs[key]['end']['known_at_upper_bound_ms'] += 60001
        self.assertEqual(study.feature(ENTRY, obs)['status'], 'unavailable_history')
        self.assertIsNone(study.feature(ENTRY, fixture('-.09000', shift='-.10000'))['primary_side'])
        self.assertEqual(study.feature(date(2022, 2, 7), {})['status'], 'calendar_skip')
        with self.assertRaises(ValueError): study.schedule(date(2025, 2, 4))
        with self.assertRaises(ValueError): study.schedule(date(2022, 2, 5))

    def test_friday_calibration_ends_before_weekly_close(self):
        obs = fixture()
        friday = date(2022, 1, 28)
        self.assertEqual(study.feature(ENTRY, obs)['status'], 'shock')
        obs[friday.isoformat()]['end']['time_msc'] = study.utc_ms(friday, 23)
        obs[friday.isoformat()]['end']['known_at_upper_bound_ms'] = study.utc_ms(friday, 23)+60000
        row = study.feature(ENTRY, obs)
        self.assertEqual(row['status'], 'unavailable_history')
        self.assertEqual(row['missing_days'], [friday.isoformat()])


if __name__ == '__main__':
    unittest.main()
