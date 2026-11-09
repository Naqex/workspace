from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import fixing_clock_probe as native
import round_level_component as r
from test_round_level_feature import quotes


class RoundComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        native.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_native_costs_buy_and_opposite_null(self):
        day = date(2019, 2, 5)
        slots, source = r.f.targets(day), quotes(day)
        source[slots[1]].update(bid='1.10010', ask='1.10020')
        source[slots[2]].update(bid='1.10010', ask='1.10020')
        source[slots[14]].update(bid='1.10120', ask='1.10130')
        row = r.evaluate_one(day, source, 'round')
        self.assertEqual(row['outcomes']['reference']['follow']['net'], '95.0')
        self.assertEqual(row['outcomes']['stress']['follow']['net'], '91.0')
        self.assertEqual(row['outcomes']['stress']['opposite']['net'], '-129.0')
        self.assertEqual(row['outcomes']['stress']['null']['net'], '0')
        self.assertEqual(row['outcomes']['stress']['follow']['costs']['financing_account'], 0)

    def test_missing_selected_endpoints_cannot_become_no_trade(self):
        day = date(2022, 2, 1)
        slots, source = r.f.targets(day), quotes(day)
        source[slots[1]].update(bid='1.10010', ask='1.10020')
        for target in (slots[2], slots[14]):
            changed = deepcopy(source)
            del changed[target]
            row = r.evaluate_one(day, changed, 'round')
            self.assertTrue(row['selected'])
            self.assertTrue(row['outcomes']['stress']['follow']['exposed'])
            self.assertFalse(row['outcomes']['stress']['follow']['resolved'])
            self.assertIsNone(row['outcomes']['stress']['follow']['net'])

    def test_full_census_and_no_false_pass(self):
        rows = r.evaluate({})
        result = r.summarize(rows)
        self.assertEqual(len(rows), 1042)
        self.assertEqual(len(result['books']), 24)
        self.assertEqual(result['financial_cases'], 6252)
        self.assertFalse(result['retained_for_temporal_review'])
        self.assertTrue(all(g['status'] == 'inconclusive' for g in result['year_gates']))
        with self.assertRaises(ValueError):
            r.summarize(rows[:-1])


if __name__ == '__main__':
    unittest.main()
