from copy import deepcopy
from datetime import date, timedelta
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import intraday_shock_component as study
import fixing_clock_probe as costs
from test_abnormal_day_feature import observation

DAY = date(2022, 2, 1)


def fixture(sign=1):
    values = [4, -4, 3, -3, 3, -3, 2, -2]+[0]*12
    from decimal import Decimal as D
    obs = {d.isoformat(): observation(d, D(v)/1000) for d, v in zip(study.prior_day.calibration_days(DAY), values)}
    q = {}
    for h in range(21):
        mid = D(1) if h < 3 else D(1)+sign*D('.01') if h < 20 else D(1)+sign*D('.011')
        t = study.prior_day.utc_ms(DAY, h)
        q[t] = dict(time_msc=t, known_at_upper_bound_ms=t, bid=str(mid-D('.00001')), ask=str(mid+D('.00001')))
    return obs, q


class IntradayShockTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls): costs.bind_core(Path(__file__).resolve().parents[3]/'projects/trader/foundation_v2')

    def test_first_crossing_entry_lag_buy_sell_and_cost(self):
        for sign, side in ((1, 'BUY'), (-1, 'SELL')):
            obs, q = fixture(sign); r = study.evaluate_one(DAY, obs, q)
            self.assertEqual((r['signal_hour'], r['primary_side'], r['checked_hours']), (3, side, [1, 2, 3]))
            self.assertEqual(r['decision_ms'], study.prior_day.utc_ms(DAY, 3, 1))
            self.assertEqual(r['entry_ms'], study.prior_day.utc_ms(DAY, 4))
            self.assertEqual(r['outcomes']['reference']['primary']['net_usd_per_research_unit'], '93.0')
            self.assertEqual(r['outcomes']['stress']['primary']['net_usd_per_research_unit'], '89.0')
            self.assertEqual(r['outcomes']['stress']['opposite_control']['net_usd_per_research_unit'], '-111.0')
            self.assertEqual(r['outcomes']['stress']['null']['net_usd_per_research_unit'], '0')

    def test_future_close_and_missing_after_crossing_do_not_choose_signal(self):
        obs, q = fixture(); before = study.feature(DAY, obs, q)
        for h in range(4, 21): q.pop(study.prior_day.utc_ms(DAY, h))
        self.assertEqual(study.feature(DAY, obs, q), before)
        actual = study.evaluate_one(DAY, obs, q)
        self.assertTrue(actual['selected']); self.assertFalse(actual['outcomes']['stress']['primary']['resolved'])
        self.assertIsNone(actual['outcomes']['stress']['primary']['net_usd_per_research_unit'])

    def test_missing_prefix_cannot_skip_to_later_crossing(self):
        obs, q = fixture(); del q[study.prior_day.utc_ms(DAY, 2)]
        self.assertEqual(study.feature(DAY, obs, q)['status'], 'unavailable_prefix')
        obs, q = fixture(); del obs[study.prior_day.calibration_days(DAY)[0].isoformat()]
        self.assertEqual(study.feature(DAY, obs, q)['status'], 'unavailable_history')

    def test_strict_boundary_sign_and_known_at(self):
        obs, q = fixture()
        for h in range(1, 19):
            q[study.prior_day.utc_ms(DAY, h)].update(bid='1.00399', ask='1.00401')
        self.assertEqual(study.feature(DAY, obs, q)['status'], 'normal')
        t = study.prior_day.utc_ms(DAY, 1); q[t].update(bid='1.00400', ask='1.00402', known_at_upper_bound_ms=t+60000)
        self.assertEqual(study.feature(DAY, obs, q)['signal_hour'], 1)
        q[t]['known_at_upper_bound_ms'] += 1
        with self.assertRaises(ValueError): study.feature(DAY, obs, q)
        q[t].update(known_at_upper_bound_ms=t, bid='NaN')
        with self.assertRaises(ValueError): study.feature(DAY, obs, q)
        with self.assertRaises(ValueError): study.feature(date(2025, 2, 4), {}, {})

    def test_full_census_unknown_and_no_false_pass(self):
        rows = study.evaluate({}, {}); report = study.summarize(rows)
        self.assertEqual(len(report['books']), 12); self.assertEqual(report['financial_cases'], 3126)
        self.assertFalse(report['retained_for_temporal_review'])
        self.assertTrue(all(g['status'] == 'inconclusive' for g in report['year_gates']))
        with self.assertRaises(ValueError): study.summarize(rows[:-1])


if __name__ == '__main__': unittest.main()
