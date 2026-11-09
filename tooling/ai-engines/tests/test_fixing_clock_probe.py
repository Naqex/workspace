import contextlib
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT/'tooling/ai-engines'))
import fixing_clock_probe as probe


def q(at, bid='1.10000', ask='1.10010', sequence=1):
    return dict(time_msc=at, bid=bid, ask=ask, sequence=sequence)


def packet(day='2019-03-11'):
    bounds = probe.clocks(day)
    return dict(entry=q(bounds['entry'], sequence=1),
                exit_1400=q(bounds['exit_1400'], '1.09900', '1.09910', 2),
                exit_1415=q(bounds['exit_1415'], '1.09800', '1.09810', 3))


def lines(rows):
    return b'DateTime,Bid,Ask,Volume\n'+b''.join((
        datetime.fromtimestamp(row['time_msc']/1000, timezone.utc).strftime('%Y%m%d %H:%M:%S.%f')[:-3]
        +','+row['bid']+','+row['ask']+',0\n').encode() for row in rows)


class FixingProbeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        probe.bind_core(ROOT/'projects/trader/foundation_v2')

    def test_fixed_costs_both_directions_and_endpoint_difference(self):
        result = probe.event('2019-03-11', packet())
        primary = result['views']['primary_1415']['outcomes']
        # SELL: 19pip net of embedded spread, .5pip fee, .4pip extra stress.
        self.assertEqual(primary['reference']['net_pips'], '18.5')
        self.assertEqual(primary['stress']['net_pips'], '18.1')
        self.assertEqual(result['paired_delta_pips'], dict(reference='10.0', stress='10.0'))
        other = result['views']['opposite_control']['outcomes']['reference']['net_pips']
        self.assertEqual(other, '-21.5')

    def test_dst_uses_local_frankfurt_clock_not_fixed_ny_offset(self):
        for day, entry_hour, exit_hour in [('2019-03-08', 7, 13), ('2019-03-11', 6, 13),
                                          ('2019-04-01', 6, 12), ('2019-10-28', 6, 13),
                                          ('2019-11-04', 7, 13)]:
            times = probe.clocks(day)
            self.assertEqual(datetime.fromtimestamp(times['entry']/1000, timezone.utc).hour, entry_hour)
            self.assertEqual(datetime.fromtimestamp(times['exit_1400']/1000, timezone.utc).hour, exit_hour)
            self.assertEqual(times['exit_1415']-times['exit_1400'], 900000)
        with self.assertRaises(ValueError):probe.clocks('2019-03-10')

    def test_missing_exit_does_not_change_entry_eligibility_or_fill_missing_with_zero(self):
        original = probe.event('2019-03-11', packet())
        values = packet();del values['exit_1415']
        missing = probe.event('2019-03-11', values)
        self.assertEqual(missing['entry_eligible'], original['entry_eligible'])
        self.assertFalse(missing['paired_delta_pips'])
        self.assertEqual(missing['views']['primary_1415']['status'], 'missing_or_late_exit')
        row = probe.summarize([missing], 2019)['rows'][0]
        self.assertEqual(row['unresolved'], 1)
        self.assertIsNone(row['net_pips_sum'])
        changed = packet();changed['exit_1415']['bid'] = '1.50000';changed['exit_1415']['ask'] = '1.50010'
        self.assertEqual(probe.event('2019-03-11', changed)['entry_eligible'], original['entry_eligible'])

    def test_deadline_inclusive_and_invalid_entry_not_rescued_by_good_future(self):
        for key in ('entry', 'exit_1415'):
            values = packet();values[key]['time_msc'] += 60000
            self.assertEqual(probe.event('2019-03-11', values)['views']['primary_1415']['status'], 'resolved')
            values[key]['time_msc'] += 1
            self.assertNotEqual(probe.event('2019-03-11', values)['views']['primary_1415']['status'], 'resolved')
        values = packet();values['entry']['time_msc'] -= 1
        self.assertFalse(probe.event('2019-03-11', values)['entry_eligible'])

    def test_paired_delta_uses_only_common_mask(self):
        complete = probe.event('2019-03-11', packet())
        values = packet('2019-03-12');del values['exit_1400']
        partial = probe.event('2019-03-12', values)
        summary = probe.summarize([complete, partial], 2019)
        self.assertEqual(summary['paired']['stress']['events'], 1)
        self.assertEqual(summary['paired']['stress']['sum_pips'], '10.0')
        self.assertEqual(summary['rows'][0]['resolved'], 2)
        self.assertEqual(summary['rows'][2]['resolved'], 1)
        self.assertFalse(summary['challenge_qualified'])

    def test_selector_first_quote_at_target_preserves_predecessor_and_rejects_hash(self):
        targets = probe.clocks('2019-03-11')
        rows = []
        for i, stamp in enumerate(targets.values()):
            rows.extend([q(stamp-1, sequence=2*i+1), q(stamp, sequence=2*i+2)])
        raw = lines(rows)
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'raw.csv';path.write_bytes(raw)
            selected, proof = probe.scan_targets(path, ['2019-03-11'], hashlib.sha256(raw).hexdigest(), 6, lambda n:None)
            self.assertEqual(selected['2019-03-11']['entry']['sequence'], 2)
            self.assertEqual(proof['quote_proofs'][0]['predecessor']['sequence'], 1)
            self.assertFalse(proof['late'])
            with self.assertRaises(ValueError):probe.scan_targets(path, ['2019-03-11'], '0'*64, 6, lambda n:None)
            with self.assertRaises(ValueError):probe.scan_targets(path, ['2019-03-11'], hashlib.sha256(raw).hexdigest(), 5, lambda n:None)

    def test_bad_quote_sequence_rejected(self):
        values = packet();values['exit_1415']['sequence'] = 1
        with self.assertRaises(ValueError):probe.event('2019-03-11', values)

    def test_actual_cli_binds_two_sealed_synthetic_years_and_refuses_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory);parent = root/'parent';parent.mkdir()
            write = lambda p, value:p.write_text(json.dumps(value), encoding='utf-8')
            sha = lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
            write(parent/'config.json', dict(purpose='synthetic transport fixture, not market history'))
            for year in probe.YEARS:
                folder = parent/str(year);folder.mkdir()
                raw = folder/'raw.csv'
                data = []
                for day in probe.dates(year):data.extend(packet(day).values())
                raw.write_bytes(lines(data))
                source = dict(dataset=str(year), status='completed_observed_triage_only',
                    raw=dict(path=str(raw), sha256=sha(raw), dates=[f'{year}0101', f'{year}1231'], config_sha256=sha(parent/'config.json')),
                    hourly_cache=dict(ticks=len(data)))
                write(folder/'result.json', source)
                write(folder/'completed.json', dict(status='completed_verified', result_path=str(folder/'result.json'),
                    result_sha256=sha(folder/'result.json'), config_sha256=sha(parent/'config.json')))
            protocol = root/'protocol.md';protocol.write_text('synthetic CLI fixture')
            fixtures = root/'fixtures.json';write(fixtures, dict(status='passed', tool_sha256=sha(Path(probe.__file__))))
            args = ['--source-root',str(ROOT/'projects/trader/foundation_v2'), '--parent-root',str(parent),
                '--protocol',str(protocol),'--fixtures',str(fixtures),'--output',str(root/'output')]
            with contextlib.redirect_stdout(io.StringIO()):probe.main(args)
            result = json.loads((root/'output/result.json').read_bytes())
            self.assertEqual(sum(y['all_dates'] for y in result['years']), 521)
            self.assertTrue(result['priority_for_wrapper_review'])
            self.assertFalse(result['challenge_qualified'])
            with self.assertRaises(FileExistsError):probe.main(args)
            write(fixtures, dict(status='passed', tool_sha256='0'*64))
            with contextlib.redirect_stdout(io.StringIO()), self.assertRaises(ValueError):probe.main(args[:-1]+[str(root/'bad')])
            self.assertEqual(json.loads((root/'bad/progress.json').read_bytes())['phase'], 'failed')


if __name__ == '__main__':
    unittest.main()
