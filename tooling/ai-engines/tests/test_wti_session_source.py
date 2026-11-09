from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import wti_session_source as source


def fixture(label):
    return {side: {at: dict(open='70.000' if side == 'bid' else '70.010',
                           close='70.000' if side == 'bid' else '70.010') for at in source.slots(label)}
            for side in ('bid', 'ask')}


class WtiSessionSourceTests(unittest.TestCase):
    def test_calendar_census_and_sunday_winter_summer(self):
        self.assertEqual(sum(len(source.slots(label)) for label in source.LABELS), 1656)
        self.assertEqual(source.utc_dates(), ['2019-02-03','2019-02-04','2019-02-05','2019-07-01','2019-07-02',
                                              '2022-02-06','2022-02-07','2022-02-08','2022-07-04','2022-07-05'])
        winter = datetime.fromtimestamp(source.slots('2019-02-04')[0]/1000, timezone.utc)
        summer = datetime.fromtimestamp(source.slots('2022-07-05')[0]/1000, timezone.utc)
        self.assertEqual((winter.isoformat(), winter.weekday()), ('2019-02-03T23:00:00+00:00', 6))
        self.assertEqual(summer.isoformat(), '2022-07-04T22:00:00+00:00')
        with self.assertRaises(ValueError):
            source.slots('2025-02-03')

    def test_exact_endpoints_cannot_be_substituted(self):
        label = source.LABELS[0]
        for side in ('bid','ask'):
            for at in (source.slots(label)[0], source.slots(label)[-1]):
                values = fixture(label)
                del values[side][at]
                result = source.coverage(label, values)
                self.assertEqual(result['paired'], 275)
                self.assertEqual(result['missing_endpoints'], [at])
                self.assertFalse(result['admitted'])

    def test_fixed_coverage_boundary_and_missing_side(self):
        label = source.LABELS[0]
        values = fixture(label)
        for at in source.slots(label)[1:6]:
            del values['bid'][at]
        self.assertTrue(source.coverage(label, values)['admitted'])
        del values['bid'][source.slots(label)[6]]
        self.assertFalse(source.coverage(label, values)['admitted'])
        with self.assertRaises(ValueError):
            source.coverage(label, {'bid': values['bid']})

    def test_crossed_or_bad_grid_rejects_instead_of_missing(self):
        label = source.LABELS[0]
        for bad in ('71', '70.0001', 'NaN'):
            values = fixture(label)
            values['bid'][source.slots(label)[0]]['open'] = bad
            with self.assertRaises(ValueError):
                source.coverage(label, values)


if __name__ == '__main__':
    unittest.main()
