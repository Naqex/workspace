from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from gold_intraday_quality import missing_runs


class QualityTests(unittest.TestCase):
    def test_fifteen_missing_minutes_is_not_more_than_fifteen(self):
        self.assertEqual(missing_runs(set(range(840))-set(range(20, 35))), [])

    def test_sixteen_missing_minutes_is_an_interior_gap(self):
        rows = missing_runs(set(range(840))-set(range(20, 36)))
        self.assertEqual(rows, [dict(start_offset_minute=20, end_offset_exclusive_minute=36,
                                     missing_minutes=16, kind='interior')])

    def test_empty_and_boundary_windows_remain_in_census(self):
        self.assertEqual(missing_runs(set())[0]['kind'], 'whole_day')
        self.assertEqual(missing_runs(set())[0]['missing_minutes'], 840)
        rows = missing_runs(set(range(16, 820)))
        self.assertEqual([r['missing_minutes'] for r in rows], [16, 20])
        self.assertTrue(all(r['kind'] == 'boundary' for r in rows))

    def test_no_gap_and_invalid_minute(self):
        self.assertEqual(missing_runs(set(range(840))), [])
        with self.assertRaises(ValueError):
            missing_runs({840})


if __name__ == '__main__':
    unittest.main()
