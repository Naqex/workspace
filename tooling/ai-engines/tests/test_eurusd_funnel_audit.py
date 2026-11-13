from pathlib import Path
import sys
import unittest
from decimal import Decimal as D

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from eurusd_funnel_audit import minimum_distance_units, fate, audit_days
from eurusd_b0_source import MINUTE, session


class FunnelTests(unittest.TestCase):
    def test_exact_native_lotfloor_threshold(self):
        for spread in range(100):
            minimum = minimum_distance_units(spread)
            self.assertLessEqual((15000//(minimum+10))*(spread+9), 1800)
            if minimum > 1:
                self.assertGreater((15000//(minimum-1+10))*(spread+9), 1800)
        self.assertEqual(minimum_distance_units(1), 73)
        self.assertEqual(minimum_distance_units(2), 82)
        self.assertIsNone(minimum_distance_units(1800))

    def test_two_signals_remain_one_confirmed_zone(self):
        day = '2022-06-01'
        clocks = session(day)
        f = {}
        for at in range(clocks[7]+15*MINUTE, clocks[8]+1, 15*MINUTE):
            f[at] = dict(bar=[at-15*MINUTE, 99990, 100000, 99900, 99999, 15], bias='BUY', atr_before=D(20))
        events, intents = [], []
        for minute in (15, 75):
            at = clocks[8]+minute*MINUTE
            events.append(dict(kind='setup', at=at, side='BUY', buffer_units='2'))
            f[at+15*MINUTE] = dict(bar=[at, 100003, 100040, 99999, 100020, 15], bias='BUY', atr_before=D(20))
            intents.append(dict(breakout_msc=at, decision_msc=at+15*MINUTE, side='BUY', status='friction_cap_rejected',
                entry_bid_units=100020, entry_ask_units=100022, distance_units=25, lot_steps=428, natural_sl_pips=2.5))
        d = dict(day=day, events=events, intents=intents,
                 counters=dict(valid_zones=1, bias_breakouts=2, first_touches=2, pre_cost_confirmed_signals=2,
                               friction_cap_rejected=2, filled_entries=0))
        result = audit_days([d], f, 2022)['summary']
        self.assertEqual(result['confirmed_signal_events'], 2)
        self.assertEqual(result['confirmed_unique_zones'], 1)
        self.assertEqual(result['zones_without_confirmation'], 0)

    def test_bias_cancellation_precedes_touch(self):
        at = 1654066800000
        setup = dict(at=at, side='BUY', buffer_units='2')
        f = {at+15*MINUTE:dict(bias='SELL', bar=[at, 100003, 100040, 99999, 100020, 15])}
        self.assertEqual(fate(setup, f, 100000, 99900, at+3*60*MINUTE)['reason'], 'setup_bias_cancelled')

    def test_validation_not_allowed(self):
        with self.assertRaisesRegex(ValueError, '2024_closed'):
            audit_days([], {}, 2024)


if __name__ == '__main__':
    unittest.main()
