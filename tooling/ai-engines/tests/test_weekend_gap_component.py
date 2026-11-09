from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tooling/ai-engines'))
import weekend_gap_component as component


def q(at, bid, ask, sequence):
    return dict(time_msc=at, bid=bid, ask=ask, sequence=sequence)


def fixture():
    row = dict(friday='2019-03-08', sunday='2019-03-10')
    t = component.clocks(row['friday'])
    quotes = dict(close=q(t['friday_reference']-1000, '1.10000', '1.10010', 1),
                  open=q(t['sunday_reference']+1000, '1.10100', '1.10110', 2),
                  entry=q(t['entry'], '1.10090', '1.10100', 3),
                  exit=q(t['exit'], '1.10000', '1.10010', 4))
    return row, quotes


class WeekendComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        component.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_buy_sell_costs_match_independent_money_examples(self):
        for side, entry, exit_at in (
                ('BUY', q(1, '1.10000', '1.10020', 1), q(2, '1.10100', '1.10110', 2)),
                ('SELL', q(1, '1.10100', '1.10120', 1), q(2, '1.10000', '1.10020', 2))):
            # Closeable-side gross0.00080*100000=80USD, commission5USD,
            # stress slippage2*0.00002*100000=4USD.
            self.assertEqual(component.net_component(side, entry, exit_at, 'reference')['net_usd_per_standard_lot'], '75.0')
            self.assertEqual(component.net_component(side, entry, exit_at, 'stress')['net_usd_per_standard_lot'], '71.0')

    def test_entry_filter_direction_zero_and_threshold_inclusive(self):
        row, quotes = fixture(); t = component.clocks(row['friday'])
        decide = lambda opened: component.entry_signal(quotes['close'], opened, quotes['entry'], t)
        self.assertEqual(decide(quotes['open'])['side'], 'SELL')
        below = dict(quotes['open'], bid='1.09900', ask='1.09910')
        self.assertEqual(decide(below)['side'], 'BUY')
        zero = dict(quotes['open'], bid='1.10000', ask='1.10010')
        self.assertEqual(decide(zero)['status'], 'zero_gap')
        exact = dict(quotes['open'], bid='1.10057', ask='1.10067')
        self.assertTrue(decide(exact)['primary_eligible'])
        smaller = dict(quotes['open'], bid='1.10056', ask='1.10066')
        self.assertFalse(decide(smaller)['primary_eligible'])

    def test_future_quote_and_missing_exit_never_change_eligibility(self):
        row, quotes = fixture()
        old = component.event_result(row, quotes)
        changed = deepcopy(quotes); changed['exit'].update(bid='1.50000', ask='1.60000')
        self.assertEqual(old['signal'], component.event_result(row, changed)['signal'])
        missing = deepcopy(quotes); del missing['exit']
        event = component.event_result(row, missing)
        self.assertEqual(old['signal'], event['signal'])
        self.assertEqual(event['outcome_status'], 'missing_or_late_exit')
        summary = component.summarize([event], 2019)[0]
        self.assertEqual(summary['eligible_events'], 1)
        self.assertEqual(summary['unresolved_events'], 1)
        self.assertIsNone(summary['net_pips_mean'])

    def test_quality_deadlines_and_source_order(self):
        row, quotes = fixture(); t = component.clocks(row['friday'])
        for key, stamp in [('open', t['sunday_reference']+300001), ('entry', t['entry']-1), ('entry', t['entry']+60001)]:
            changed = deepcopy(quotes); changed[key]['time_msc'] = stamp
            self.assertFalse(component.event_result(row, changed)['signal']['primary_eligible'])
        changed = deepcopy(quotes); changed['exit']['sequence'] = changed['entry']['sequence']
        with self.assertRaisesRegex(ValueError, 'quote_order'):
            component.event_result(row, changed)

    def test_clocks_cover_spring_and_autumn_ny_dst(self):
        spring = component.clocks('2019-03-08'); autumn = component.clocks('2019-11-01')
        self.assertEqual(spring['sunday_reference']-spring['friday_reference'], 47*3600000)
        self.assertEqual(autumn['sunday_reference']-autumn['friday_reference'], 49*3600000)
        self.assertEqual(spring['exit']-spring['entry'], 12*3600000)
        with self.assertRaisesRegex(ValueError, 'not_friday'):
            component.clocks('2019-03-09')

    def test_raw_selector_uses_first_at_or_after_and_preserves_endpoints(self):
        row, quotes = fixture(); t = component.clocks(row['friday'])
        at = [quotes['close']['time_msc'], quotes['open']['time_msc'], t['entry']-1,
              t['entry'], t['exit']-1, t['exit']+60000]
        lines = [b'DateTime,Bid,Ask,Volume\n']
        for timestamp in at:
            text = datetime.fromtimestamp(timestamp/1000, timezone.utc).strftime('%Y%m%d %H:%M:%S.%f')[:-3]
            lines.append((text+',1.10000,1.10010,1\n').encode())
        raw = b''.join(lines)
        row.update(close=dict(sequence=1, time_msc=at[0]), open=dict(sequence=2, time_msc=at[1]))
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'ticks.csv'; path.write_bytes(raw)
            selected, rejected = component.collect_quotes(path, [row], hashlib.sha256(raw).hexdigest(), 6, lambda n: None)
            self.assertEqual(selected[row['friday']]['entry']['sequence'], 4)
            self.assertEqual(selected[row['friday']]['exit']['sequence'], 6)
            self.assertFalse(rejected)
            late = b''.join(lines[:-1]+[lines[-1].replace(b'.000,', b'.001,')])
            path.write_bytes(late)
            selected, rejected = component.collect_quotes(path, [row], hashlib.sha256(late).hexdigest(), 6, lambda n: None)
            self.assertNotIn('exit', selected[row['friday']])
            self.assertEqual(len(rejected), 1)
            with self.assertRaisesRegex(ValueError, 'hash_or_count'):
                component.collect_quotes(path, [row], '0'*64, 6, lambda n: None)

    def test_empty_primary_is_unknown_instead_of_zero_edge(self):
        row, quotes = fixture(); quotes['open'].update(bid='1.10000', ask='1.10010')
        event = component.event_result(row, quotes)
        for summary in component.summarize([event], 2019):
            self.assertEqual(summary['eligible_events'], 0)
            self.assertIsNone(summary['net_pips_sum'])

    def test_failure_receipt_is_visible_even_when_cancellation_is_pending(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp)/'run'
            argv = ['weekend_gap_component.py', '--source-root', str(ROOT/'projects/trader/foundation_v2')]
            for name in ('admission-root', 'parent-root', 'protocol', 'fixtures'):
                argv.extend(['--'+name, str(Path(temp)/name)])
            argv.extend(['--output', str(output)])
            def invalid_fixture(path):
                (output/'CANCEL').touch()
                return dict(status='failed')
            with patch.object(sys, 'argv', argv), patch.object(component, 'read', side_effect=invalid_fixture):
                with self.assertRaisesRegex(ValueError, 'fixtures_not_bound'):
                    component.main()
            self.assertEqual(json.loads((output/'progress.json').read_text())['phase'], 'failed')
            self.assertEqual(json.loads((output/'failure.json').read_text())['type'], 'ValueError')


if __name__ == '__main__':
    unittest.main()
