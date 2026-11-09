from copy import deepcopy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from test_index_cash_close_tick_component import case, hour, evaluate
import test_index_cash_close_tick_component as parent_fixture
from nasdaq_cash_calendar import sessions_for
import index_consensus_component as study


def parent(profile='us500', *, side='BUY', agree=True):
    price = 110 if side == 'BUY' else 90
    data = case(profile, late=price, first=price if agree else 200-price)
    if side == 'SELL': data = (data[0], data[1], hour(data[0], profile, 'exit_hour', bid=107000))
    return evaluate(data, profile=profile)


class ConsensusTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): parent_fixture.CashCloseTickTests.setUpClass()

    def test_both_profiles_sides_exact_cost_reuse_and_input_immutable(self):
        for profile in ('us500', 'nasdaq'):
            for side in ('BUY', 'SELL'):
                p = parent(profile, side=side); original = deepcopy(p)
                got = study.select(p, profile=profile)
                self.assertTrue(got['planned_trade']); self.assertEqual(got['signal_side'], side)
                self.assertEqual(got['outcomes'], p['outcomes']); self.assertEqual(p, original)
                got['outcomes']['reference']['primary']['costs']['net_account'] = 999
                self.assertEqual(p, original)

    def test_disagreement_flat_and_missing_have_no_fake_fills(self):
        samples = [parent(agree=False), evaluate(case(late=100)), evaluate(case(first=100))]
        invalid = parent(); invalid.update(predictor_valid=False, planned_trade=False, outcomes={}); samples.append(invalid)
        for p in samples:
            got = study.select(p, profile='us500')
            self.assertFalse(got['planned_trade']); self.assertFalse(got['outcomes'])
            self.assertIsNone(got['entry']); self.assertIsNone(got['exit'])

    def test_selected_unknown_stays_planned_and_future_price_net_do_not_select(self):
        p = parent(); p['outcomes'] = {}; p['exit']['bid'] = None
        self.assertTrue(study.select(p, profile='us500')['planned_trade'])
        self.assertFalse(study.select(p, profile='us500')['outcomes'])
        p = parent(agree=False)
        for v in p['outcomes'].values(): v['primary']['net_usd_per_research_unit'] = '999999'
        p['exit']['bid'] = '999999'
        self.assertFalse(study.select(p, profile='us500')['planned_trade'])

    def test_scope_authority_and_first_half_identity_rejected(self):
        for key, value in [('candidate', 'foreign'), ('year', 2025), ('delay_ms', 200),
                           ('execution_authorized', True), ('broker_calls', True)]:
            p = parent(); p[key] = value
            with self.subTest(key=key), self.assertRaises(ValueError): study.select(p, profile='us500')
        p = parent(); p['outcomes']['reference']['first_half_control']['net_usd_per_research_unit'] = '1'
        with self.assertRaisesRegex(ValueError, 'first_half'): study.select(p, profile='us500')

    def test_equal_first_half_is_invariant_not_impossible_retention_gate(self):
        examples = [study.select(parent(side=side), profile='us500') for side in ('BUY', 'SELL')]
        expected = {y: list(sessions_for(f'development-{y}'))[:100] for y in (2019, 2022)}
        rows = []
        for delay in study.DELAYS:
            for year in (2019, 2022):
                for i, day in enumerate(expected[year]):
                    r = deepcopy(examples[i % 2]); r.update(delay_ms=delay, year=year, session=day); rows.append(r)
        result = study.summarize(rows, expected, profile='us500')
        self.assertTrue(result['retained_for_further_research'])
        for mode in ('unknown', 'cost_control'):
            bad = deepcopy(rows)
            if mode == 'unknown':
                for row in bad[-3:]: row['outcomes'] = {}
            else: bad[-1]['outcomes']['stress']['always_long_control']['net_usd_per_research_unit'] = '99999'
            self.assertFalse(study.summarize(bad, expected, profile='us500')['retained_for_further_research'])
        for bad in (rows[:-1], rows+[rows[-1]], rows[::-1]):
            with self.assertRaisesRegex(ValueError, 'census'): study.summarize(bad, expected, profile='us500')


if __name__ == '__main__': unittest.main()
