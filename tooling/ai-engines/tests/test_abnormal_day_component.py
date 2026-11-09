from copy import deepcopy
from datetime import date
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import abnormal_day_component as study
import fixing_clock_probe as costs
from test_abnormal_day_feature import fixture, ENTRY


def quotes():
    s = study.signal.schedule(ENTRY)
    return {s['entry_ms']: dict(time_msc=s['entry_ms'], bid='1.10000', ask='1.10010'),
        s['exit_ms']: dict(time_msc=s['exit_ms'], bid='1.09900', ask='1.09910')}


class AbnormalComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        costs.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_buy_sell_spread_commission_slip_null_and_unit(self):
        row = study.evaluate_one(ENTRY, fixture(), quotes())
        self.assertEqual(row['outcomes']['reference']['primary']['net_usd_per_research_unit'], '85.0')
        self.assertEqual(row['outcomes']['stress']['primary']['net_usd_per_research_unit'], '81.0')
        self.assertEqual(row['outcomes']['stress']['opposite_control']['net_usd_per_research_unit'], '-119.0')
        self.assertEqual(row['outcomes']['stress']['null']['net_usd_per_research_unit'], '0')
        neg = study.evaluate_one(ENTRY, fixture('-.01000'), quotes())
        self.assertEqual(neg['outcomes']['stress']['primary']['side'], 'BUY')
        self.assertEqual(neg['outcomes']['stress']['primary']['net_usd_per_research_unit'], '-119.0')
        self.assertFalse(row['execution_authorized']); self.assertFalse(row['account_simulated'])

    def test_selected_unknown_is_not_zero_or_entry_filter(self):
        q = quotes(); del q[study.signal.schedule(ENTRY)['exit_ms']]
        row = study.evaluate_one(ENTRY, fixture(), q)
        self.assertTrue(row['selected'])
        self.assertFalse(row['outcomes']['stress']['primary']['resolved'])
        self.assertIsNone(row['outcomes']['stress']['primary']['net_usd_per_research_unit'])
        self.assertTrue(row['outcomes']['stress']['null']['resolved'])
        late = quotes(); late[study.signal.schedule(ENTRY)['entry_ms']]['time_msc'] += 60001
        self.assertFalse(study.evaluate_one(ENTRY, fixture(), late)['outcomes']['reference']['primary']['resolved'])
        for price in ('1.100001', 'NaN'):
            bad = quotes(); bad[study.signal.schedule(ENTRY)['entry_ms']]['bid'] = price
            with self.assertRaises(ValueError): study.evaluate_one(ENTRY, fixture(), bad)

    def test_census_known_at_skips_and_inconclusive_gate(self):
        rows = study.evaluate({}, {})
        result = study.summarize(rows)
        self.assertEqual(len(rows), 521); self.assertEqual(result['financial_cases'], 3126)
        self.assertEqual(len(result['books']), 12)
        self.assertTrue(all(b['strict_net'] == '0' and b['selected_shocks'] == 0 for b in result['books']))
        self.assertFalse(result['retained_for_risk_review'])
        self.assertTrue(all(g['status'] == 'inconclusive' for g in result['year_gates']))
        with self.assertRaises(ValueError): study.summarize(rows[:-1])
        with self.assertRaises(ValueError): study.summarize(list(reversed(rows)))

    def test_future_exit_changes_outcome_not_feature_or_schedule(self):
        before = study.evaluate_one(ENTRY, fixture(), quotes())
        q = quotes(); q[study.signal.schedule(ENTRY)['exit_ms']].update(bid='1.20000', ask='1.20010')
        after = study.evaluate_one(ENTRY, fixture(), q)
        for key in ('primary_side', 'selected', 'shock_return', 'calibration_mean', 'calibration_sample_variance',
                    'decision_ms', 'entry_ms', 'exit_ms', 'feature_version'):
            self.assertEqual(before[key], after[key])
        self.assertNotEqual(before['outcomes'], after['outcomes'])


if __name__ == '__main__':
    unittest.main()
