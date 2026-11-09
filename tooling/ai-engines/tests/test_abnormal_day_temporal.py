from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abnormal_day_component as study


def books():
    return [dict(year=y, rule=r, scenario=s, planned_weekdays=261,
        feature_status_counts=dict(calendar_skip=52, normal=199, shock=10), selected_shocks=10,
        exposed=10 if r != 'null' else 0, resolved_exposed=10 if r != 'null' else 0,
        unresolved_exposed=0, strict_net='10' if r != 'null' else '0')
        for y in range(2010, 2025) for r in study.RULES for s in study.SCENARIOS]


class TemporalTests(unittest.TestCase):
    def test_explicit_scope_keeps_default_and_blocks_holdout(self):
        self.assertEqual(len(study.days()), 521)
        self.assertEqual(len(study.days(years=range(2010, 2025))), 3913)
        with self.assertRaises(ValueError): study.signal.schedule(date(2010, 2, 1))
        self.assertEqual(study.signal.schedule(date(2010, 2, 1), years=(2010,))['day'], '2010-02-01')
        for scope in ((2025,), (), (2022, 2019), (2019, 2019), (True,), ('2022',)):
            with self.assertRaises(ValueError): study.days(years=scope)

    def test_discovery_cannot_rescue_extension_block(self):
        data = books()
        self.assertTrue(study.temporal_gate(data)['retained_for_risk_review'])
        for b in data:
            if b['year'] in (2019, 2022): b['strict_net'] = '999999'
            if b['year'] == 2024 and b['rule'] == 'primary' and b['scenario'] == 'stress': b['strict_net'] = '-100'
        result = study.temporal_gate(data)
        self.assertEqual(result['extension_strict_net'], '20')
        self.assertEqual(result['extension_blocks'][-1]['strict_net'], '-90')
        self.assertEqual(result['status'], 'not_retained')

    def test_unknown_coverage_and_small_sample_are_inconclusive(self):
        for kind in ('unknown', 'coverage', 'sample'):
            data = books()
            for b in data:
                if b['rule'] != 'primary' or b['scenario'] != 'stress': continue
                if kind == 'unknown' and b['year'] == 2010: b.update(strict_net=None, unresolved_exposed=1, resolved_exposed=9)
                if kind == 'coverage' and b['year'] == 2010: b['feature_status_counts'] = dict(calendar_skip=52, normal=99, shock=10, unavailable_history=100)
                if kind == 'sample': b['resolved_exposed'] = 6
            self.assertEqual(study.temporal_gate(data)['status'], 'inconclusive')

    def test_duplicate_or_missing_books_fail(self):
        data = books()
        with self.assertRaises(ValueError): study.temporal_gate(data[:-1])
        data[-1] = deepcopy(data[0])
        with self.assertRaises(ValueError): study.temporal_gate(data)


if __name__ == '__main__':
    unittest.main()
