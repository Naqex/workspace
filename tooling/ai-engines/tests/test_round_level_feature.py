from copy import deepcopy
from datetime import date, datetime
from decimal import Decimal as D
from pathlib import Path
import sys
import unittest
from zoneinfo import ZoneInfo

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import round_level_feature as r


def q(bid, ask):
    return dict(bid=str(bid), ask=str(ask))


def quotes(day):
    return {at: dict(time_msc=at+10, sequence=i+1, bid='1.09980', ask='1.09990')
            for i, at in enumerate(r.targets(day))}


class RoundLevelTests(unittest.TestCase):
    def test_direction_and_current_previous_equality(self):
        self.assertEqual(r.crossing(q('1.0998', '1.0999'), q('1.1001', '1.1002'), 'round')['side'], 'BUY')
        self.assertEqual(r.crossing(q('1.1001', '1.1002'), q('1.0998', '1.0999'), 'round')['side'], 'SELL')
        self.assertEqual(r.crossing(q('1.0998', '1.0999'), q('1.0999', '1.1000'), 'round')['status'], 'no_cross')
        self.assertEqual(r.crossing(q('1.0999', '1.1000'), q('1.1000', '1.1001'), 'round')['side'], 'BUY')
        self.assertEqual(r.crossing(q('1.1000', '1.1001'), q('1.0999', '1.1000'), 'round')['side'], 'SELL')

    def test_placebo_multilevel_and_simultaneous_cross(self):
        a, b = q('1.1023', '1.1024'), q('1.1026', '1.1027')
        self.assertEqual(r.crossing(a, b, 'placebo')['side'], 'BUY')
        self.assertEqual(r.crossing(a, b, 'round')['status'], 'no_cross')
        self.assertEqual(r.crossing(q('1.0998', '1.0999'), q('1.1101', '1.1102'), 'round')['status'], 'ambiguous')
        self.assertEqual(r.crossing(q('1.1000', '1.1000'), q('1.0999', '1.1001'), 'round')['status'], 'ambiguous')

    def test_first_cross_delay_and_future_invariance(self):
        day = date(2019, 2, 5)
        slots, source = r.targets(day), quotes(day)
        source[slots[1]].update(bid='1.10010', ask='1.10020')
        signal = r.feature(day, source, 'round')
        self.assertTrue(signal['selected'])
        self.assertEqual((signal['crossing_ms'], signal['decision_ms'], signal['entry_ms'], signal['exit_ms']),
                         (slots[1], slots[1]+60000, slots[2], slots[14]))
        self.assertLess(signal['decision_ms'], signal['entry_ms'])
        changed = {at: row for at, row in source.items() if at <= slots[1]}
        self.assertEqual(signal, r.feature(day, changed, 'round'))

    def test_prefix_missing_does_not_select_later_but_later_missing_keeps_selection(self):
        day = date(2022, 2, 1)
        slots, source = r.targets(day), quotes(day)
        source[slots[2]].update(bid='1.10010', ask='1.10020')
        missing = deepcopy(source)
        del missing[slots[1]]
        self.assertEqual(r.feature(day, missing, 'round')['status'], 'unavailableprefix')
        source[slots[2]]['time_msc'] += 60001
        self.assertEqual(r.feature(day, source, 'round')['status'], 'unavailableprefix')

    def test_last_cross_exit_clock_dst_calendar_and_scope(self):
        self.assertEqual(len(r.days()), 521)
        self.assertEqual(len(r.targets(date(2019, 2, 5))), 84)
        for day, hour in [(date(2019, 2, 5), 14), (date(2022, 7, 5), 13)]:
            slots, source = r.targets(day), quotes(day)
            self.assertEqual(datetime.fromtimestamp(slots[0]/1000, ZoneInfo('UTC')).hour, hour)
            source[slots[70]].update(bid='1.10010', ask='1.10020')
            signal = r.feature(day, source, 'round')
            self.assertEqual(signal['exit_ms'], slots[83])
            self.assertEqual(datetime.fromtimestamp(signal['exit_ms']/1000, r.NY).strftime('%H:%M'), '15:55')
        for day in [date(2025, 1, 1), date(2019, 2, 2)]:
            with self.assertRaises(ValueError):
                r.targets(day)

    def test_invalid_quote_and_sequence_fail_instead_of_no_signal(self):
        day, source = date(2019, 2, 5), quotes(date(2019, 2, 5))
        at = r.targets(day)[1]
        source[at]['bid'] = '1.2'
        with self.assertRaises(ValueError):
            r.feature(day, source, 'round')
        source = quotes(day)
        source[at]['sequence'] = 1
        with self.assertRaises(ValueError):
            r.feature(day, source, 'round')


if __name__ == '__main__':
    unittest.main()
