from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import run_us500_channel_history as h


class ChannelHistoryTests(unittest.TestCase):
    def test_only_source_newlines_can_differ_from_verified_snapshot(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); snapshots = root/'snapshots'; snapshots.mkdir()
            prior = snapshots/'01-rule.py'; prior.write_bytes(b'x = 1\n')
            current = root/'rule.py'; current.write_bytes(b'x = 1\r\n')
            manifest = dict(source_pins={str(current.resolve()): h.source.digest(prior)})
            checks = h.rule_identity([current], manifest, snapshots)
            self.assertEqual(checks[0]['difference'], 'CRLF_LF_only_python_source')
            current.write_bytes(b'x = 2\r\n')
            with self.assertRaisesRegex(ValueError, 'rule_or_environment_changed'):
                h.rule_identity([current], manifest, snapshots)
            current.write_bytes(b'x = 1\r\n'); prior.write_bytes(b'x = 3\n')
            with self.assertRaisesRegex(ValueError, 'rule_or_environment_changed'):
                h.rule_identity([current], manifest, snapshots)

    def test_data_and_lock_files_never_receive_newline_exception(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); snapshots = root/'snapshots'; snapshots.mkdir()
            for name in ('quotes.json', 'uv.lock'):
                prior = snapshots/('01-'+name); prior.write_bytes(b'1\n')
                current = root/name; current.write_bytes(b'1\r\n')
                manifest = dict(source_pins={str(current.resolve()): h.source.digest(prior)})
                with self.assertRaisesRegex(ValueError, 'rule_or_environment_changed'):
                    h.rule_identity([current], manifest, snapshots)

    def test_registered_window_stops_before_any_reserved_data_io(self):
        with patch.object(h.source, 'digest', side_effect=AssertionError('must not read')):
            for year in (2012, 2022, 2025):
                with self.assertRaisesRegex(ValueError, 'registered_year'):
                    h.historical_year(Path('not_read'), dict(year=year), lambda *a, **k: None)

    def test_coverage_is_diagnostic_and_keeps_short_and_gap_days_separate(self):
        sessions = {'a': list(range(390)), 'b': list(range(390, 780)), 'short': [1000]}
        pairs = {t: True for ts in sessions.values() for t in ts if t != 400}
        events = [dict(day=day, slot=slot, blocked=day == 'b', m15=True)
                  for day in ('a', 'b') for slot in range(30, 331, 15)]
        c = h.coverage(sessions, pairs, dict(snapshots=dict(enumerate(events))))
        self.assertEqual(c['normal_sessions'], 2)
        self.assertEqual(c['short_sessions'], 1)
        self.assertEqual(c['complete_cash_normal_sessions'], 1)
        self.assertEqual(c['unblocked_complete_decision_window_normal_sessions'], 1)
        self.assertEqual(c['normal_days_blocked_or_missing_in_decision_window'], 1)
        self.assertAlmostEqual(c['paired_cash_minute_coverage_pct'], 780/781*100)


if __name__ == '__main__': unittest.main()
