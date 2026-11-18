from copy import deepcopy
from pathlib import Path
import json
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solo_validation_source as source


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding='utf-8')
    return source.pin(path)


def raw_hour(at):
    return dict(timestamp=at, multiplier=.00001, bid=1.2, ask=1.2001,
                times=[1, 0, 1000], bids=[0, 2, -1], asks=[0, 2, -1],
                bidVolumes=[1, 2, 3], askVolumes=[1, 2, 3])


def signal(at):
    return dict(id=source.CELL, asset='GBPUSD', side='BUY',
                day=source.datetime.fromtimestamp(at / 1000, source.timezone.utc).date().isoformat(),
                decision_msc=at, stop_units=119000, deadline_msc=at + 2 * source.HOUR,
                deadline_kind='DAY')


class SourcePureTests(unittest.TestCase):
    def test_real_generator_carries_ATR_and_future_append_keeps_Dev(self):
        begin = source.stamp('2023-12-27')
        finish = source.stamp('2024-01-04')
        sweep = {source.stamp('2023-12-29T07:00:00'), source.stamp('2024-01-02T07:00:00')}
        wide = source.stamp('2023-12-31')
        hours = []
        for at in range(begin, finish, source.HOUR):
            width = 300 if wide <= at < source.END else 20
            bar = [at, 120000, 120000 + width, 120000 - width, 120000, 60]
            if at in sweep:
                bar = [at, 120000, 120020, 119900, 120010, 60]
            hours.append(bar)
        with patch.object(source.Path, 'cwd', return_value=source.WORKSPACE):
            dev, _, _ = source.generated_signals([r for r in hours if r[0] < source.END], source.START, source.END)
            dev_appended, _, _ = source.generated_signals(hours, source.START, source.END)
            full, _, _ = source.generated_signals(hours, source.END, source.FINAL)
            restarted, _, _ = source.generated_signals([r for r in hours if r[0] >= source.END], source.END, source.FINAL)
        self.assertEqual(dev, dev_appended)
        self.assertEqual(len(full), 1)
        self.assertEqual(len(restarted), 1)
        self.assertNotEqual(full[0]['stop_units'], restarted[0]['stop_units'])
        self.assertEqual(full[0]['decision_msc'], source.stamp('2024-01-02T08:00:00'))
        self.assertEqual(full[0]['deadline_msc'], source.stamp('2024-01-02T20:30:00'))
        self.assertEqual(full[0]['id'], source.CELL)

    def test_raw_census_keeps_rejects_and_refuses_closed_years(self):
        at = source.stamp('2024-01-03T08:00:00')
        row = dict(signal(at), pass15=False, future_exit=123)
        signals, hours = source.signal_census([row])
        self.assertEqual(signals, [signal(at)])
        self.assertEqual(hours, [at, at + source.HOUR, at + 2 * source.HOUR])
        for bad in (signal(source.FINAL), dict(row, deadline_msc=source.FINAL - 60000),
                    dict(row, asset='EURUSD'), dict(row, stop_units=True)):
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                source.signal_census([bad])
        with self.assertRaisesRegex(ValueError, 'duplicate'):
            source.signal_census([row, row])

    def test_decoder_preserves_same_ms_and_denies_later_hour(self):
        at = source.stamp('2024-01-03T08:00:00')
        rows = source.decode_hour(raw_hour(at), at)
        self.assertEqual(rows['t'].tolist(), [at + 1, at + 1, at + 1001])
        self.assertEqual(rows['b'].tolist(), [120000, 120002, 120001])
        raw = raw_hour(at)
        raw['times'][-1] = source.HOUR
        with self.assertRaisesRegex(ValueError, 'not_dropped'):
            source.decode_hour(raw, at)
        with self.assertRaisesRegex(ValueError, 'outside_validation'):
            source.decode_hour(raw_hour(source.FINAL), source.FINAL)
        overflow = raw_hour(at)
        overflow.update(bid=30000.0, ask=30000.0001)
        with self.assertRaisesRegex(ValueError, 'int32_price_grid'):
            source.decode_hour(overflow, at)

    def test_registration_denied_before_H1_or_tick_read(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / 'job'
            with patch.object(source, 'JOB', job), patch.object(source, 'SOURCE_JOB', job / 'gbp-source'), \
                 patch.object(source, 'load_books', side_effect=AssertionError('price reader called')):
                with self.assertRaisesRegex(ValueError, 'release_missing'):
                    source.register_source()
                with self.assertRaisesRegex(ValueError, 'source_registration_path'):
                    source.verify_source_registration(job / 'other.json')

    def test_H1_denies_2025_metadata_before_file_read(self):
        with patch.object(source, 'digest', side_effect=AssertionError('price bytes opened')):
            with self.assertRaisesRegex(ValueError, 'H1_year_closed'):
                source.book_rows(dict(year=2025, side='bid'))

    def test_opaque_inherited_identity_does_not_parse_json(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'opaque.json'
            path.write_bytes(b'opaque bytes are not valid json')
            with patch('solo_validation_replay.inherited_validation_paths', return_value={'gold': path}), \
                 patch.object(source, 'read', side_effect=AssertionError('parsed outcome')):
                self.assertEqual(source.inherited_metadata()['gold']['sha256'], source.digest(path))

    def test_output_links_and_outside_roots_fail(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / 'job'
            with patch.object(source, 'JOB', job):
                with self.assertRaisesRegex(ValueError, 'outside_owned'):
                    source.write_new(Path(directory) / 'not-owned.json', {})
                source.write_new(job / 'new.json', {'ok': True})
                with self.assertRaises(FileExistsError):
                    source.write_new(job / 'new.json', {'ok': False})


class BookProofTests(unittest.TestCase):
    def fixture(self, folder, year=2024):
        at = source.stamp(f'{year}-11-01T08:00:00')
        book = folder / f'{year}-gbpusd-bid.json'
        save(book, [dict(timestamp=at, open=1.2, high=1.20002, low=1.2, close=1.20001)])
        proof = folder / f'{year}-gbpusd-bid-source-proof.json'
        save(proof, dict(observedTickTimestamps=False, sourcePolicy='explicit_source_H1_only',
                         selectedRows=1, unavailableSources=[]))
        return dict(year=year, side='bid', path=str(book), sha256=source.digest(book),
                    proof_path=str(proof), proof_sha256=source.digest(proof), rows=1,
                    source_policy='explicit_source_H1_only')

    def test_explicit_book_positive_and_timestamp_or_price_mismatch(self):
        with tempfile.TemporaryDirectory() as directory:
            detail = self.fixture(Path(directory))
            self.assertEqual(next(iter(source.book_rows(detail).values())), [120000, 120002, 120000, 120001])
            path = Path(detail['path'])
            rows = source.read(path)
            rows[0]['timestamp'] = source.FINAL
            save(path, rows)
            detail['sha256'] = source.digest(path)
            with self.assertRaisesRegex(ValueError, 'H1_clock_or_year'):
                source.book_rows(detail)

    def test_corrected_2022_proof_positive_and_lineage_tamper(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            detail = self.fixture(folder, 2022)
            original_book = save(folder / 'original-book.json', [{'metadata': 'fixture'}])
            original_proof = save(folder / 'original-proof.json', dict(observedTickTimestamps=False,
                sourcePolicy='explicit_source_H1_only', selectedRows=1, unavailableSources=[]))
            card = save(folder / 'card.json', dict(schema='S01-source-correction-v2',
                changes={'bid': [{'at': h} for h in source.CORRECTED_HOURS]},
                cohort_and_natural_stops_unchanged=True, financial_outcomes_computed=False))
            lineage = dict(original_book=original_book, original_proof=original_proof, correction_card=card)
            proof = dict(**lineage, corrected_hours=source.CORRECTED_HOURS,
                changed_fields=['open', 'high', 'low', 'close'],
                sourcePolicy='explicit_H1_plus_registered_two_hour_tick_OHLC', observedTickTimestamps=False,
                tick_timestamps_observed_only_at=source.CORRECTED_HOURS,
                original_volume_retained_not_tick_volume=True, independent_feed_verified=False)
            save(Path(detail['proof_path']), proof)
            detail.update(proof_sha256=source.digest(detail['proof_path']),
                source_policy=proof['sourcePolicy'], correction_lineage=lineage)
            self.assertEqual(len(source.book_rows(detail)), 1)
            changed = deepcopy(proof)
            changed['corrected_hours'] = source.CORRECTED_HOURS[:1]
            save(Path(detail['proof_path']), changed)
            detail['proof_sha256'] = source.digest(detail['proof_path'])
            with self.assertRaisesRegex(ValueError, 'corrected_H1_proof_lineage'):
                source.book_rows(detail)
            save(Path(detail['proof_path']), proof)
            detail['proof_sha256'] = source.digest(detail['proof_path'])
            Path(card['path']).write_text('{}')
            with self.assertRaisesRegex(ValueError, 'bound_input_changed'):
                source.book_rows(detail)


class AdmissionTests(unittest.TestCase):
    def fixture(self, folder):
        at = source.stamp('2024-01-03T08:00:00')
        job, child = folder / 'job', folder / 'job/gbp-source'
        raw = raw_hour(at)
        # Minute observations cover the complete registered holding period.
        raw.update(times=[0] + [60000] * 59, bids=[0] * 60, asks=[0] * 60,
                   bidVolumes=[1] * 60, askVolumes=[1] * 60)
        raw_pin = save(child / 'source/cache/hour.json', raw)
        save(child / 'source/sealed-hours.json', [dict(at=at, raw_path=raw_pin['path'],
             raw_sha256=raw_pin['sha256'], records=60)])
        row = dict(signal(at), deadline_msc=at + 30 * 60000)
        registration = dict(hours=[at], signals=[row])
        save(child / 'registration.json', registration)
        expected = {(at, 'bid'): [120000] * 4, (at, 'ask'): [120010] * 4}
        return job, child, registration, expected

    def test_full_admission_positive_and_H1_mismatch_remains_review(self):
        for mismatch in (False, True):
            with self.subTest(mismatch=mismatch), tempfile.TemporaryDirectory() as directory:
                job, child, registration, expected = self.fixture(Path(directory))
                if mismatch:
                    expected[next(iter(expected))][-1] += 1
                with patch.object(source, 'JOB', job), patch.object(source, 'SOURCE_JOB', child), \
                     patch.object(source, 'verify_source_registration', return_value=registration), \
                     patch.object(source, 'verify_release', return_value={}), \
                     patch.object(source, 'load_books', return_value=([], expected)):
                    self.assertEqual(source.admit_source(), not mismatch)
                    proof = source.read(child / 'source-proof.json')
                    self.assertEqual(proof['status'], 'SOURCE_REVIEW_REQUIRED' if mismatch else 'SOURCE_RECONCILED')
                    self.assertFalse(proof['financial_results_computed'])
                    self.assertEqual(proof['manifest_sha256'], source.digest(child / 'manifest.json'))
                    with self.assertRaisesRegex(ValueError, 'receipt_already_exists'):
                        source.admit_source()

    def test_missing_endpoint_and_held_gap_are_not_interpolated(self):
        at = source.stamp('2024-01-03T08:00:00')
        with tempfile.TemporaryDirectory() as directory:
            rows = source.decode_hour(raw_hour(at), at)
            rows['t'] = [at, at + 20 * 60000, at + 30 * 60000]
            binary = Path(directory) / 'hour.ticks'
            binary.write_bytes(rows.tobytes())
            manifest = {str(at): dict(path=str(binary), records=3, sha256=source.digest(binary))}
            row = dict(signal(at), deadline_msc=at + 30 * 60000)
            issues = source.held_quality([row], manifest)
            self.assertEqual(issues[0]['reason'], 'HELD_GAP_GT15_MINUTES')
            row['deadline_msc'] = at + 40 * 60000
            self.assertEqual(source.held_quality([row], manifest)[0]['reason'],
                             'ENTRY_OR_DEADLINE_QUOTE_UNKNOWN')


class ReleaseTests(unittest.TestCase):
    def test_positive_committed_release_and_mutations(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            workspace = root / 'workspace'
            workspace.mkdir()
            subprocess.run(['git', 'init', '-q', str(workspace)], check=True)
            producer = workspace / 'source.py'
            producer.write_text('# committed fixture\n')
            subprocess.run(['git', '-C', str(workspace), 'add', 'source.py'], check=True)
            subprocess.run(['git', '-C', str(workspace), '-c', 'user.name=fixture', '-c',
                            'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
            job = root / 'job'
            result = save(root / 'result.json', {'status': 'fixture'})
            review = root / 'review.json'
            save(review, dict(schema='solo-validation-pre-release-review-v1', status='PASS',
                source_only=True, prices2024_2026_read=False,
                price_access_claim_scope='independent_reviewer_only',
                reviewed_producer_sha256={str(producer.resolve()): source.digest(producer)}))
            metadata = save(root / 'metadata.json', {'books': []})
            incident = root / 'incident.json'
            save(incident, {'synthetic': True})
            with patch.object(source, 'WORKSPACE', workspace), patch.object(source, 'JOB', job), \
                 patch.object(source, 'INCIDENT', incident), \
                 patch.object(source, 'producer_paths', return_value=[producer]), \
                 patch.object(source, 'canonical_pins', return_value={'result': result}), \
                 patch.object(source, 'h1_metadata', return_value=([], metadata)), \
                 patch.object(source, 'inherited_metadata', return_value={}), \
                 patch.object(source, 'load_books', side_effect=AssertionError('release parsed prices')):
                packet = source.release(review)
                self.assertTrue(packet['source_only'])
                self.assertFalse(packet['financial_results_computed'])
                self.assertEqual(source.verify_release(), packet)
                producer.write_text('# uncommitted change\n')
                with self.assertRaisesRegex(ValueError, 'commit_before_release'):
                    source.verify_release()

    def test_resigned_raw_cohort_cannot_change_side_stop_or_count(self):
        with tempfile.TemporaryDirectory() as directory:
            job = Path(directory) / 'job'
            child = job / 'gbp-source'
            at = source.stamp('2024-01-03T08:00:00')
            signals, hours = source.signal_census([signal(at), signal(at + 24 * source.HOUR)])
            release = dict(producer_pins=[], h1_books=[])
            release_pin = save(job / 'source-release.json', release)
            dev = [dict(signal(source.START + i * source.HOUR)) for i in range(300)]
            original_pin = save(job / 'original.json', dict(signals=dev, hours=[]))
            packet = dict(schema='solo-validation-gbp-source-v1', cell=source.CELL,
                job_root=str(child.resolve()), window=source.WINDOW, source_only=True,
                financial_results_computed=False, prices2025_2026_read=False,
                source_budget=source.BUDGET, release_pin=release_pin, producer_pins=[],
                h1_source_books=[], input_pins=[], signals=signals, hours=hours, missing_hours=hours,
                reused={}, development_prefix_verified=True, development_prefix_signals=300, abstentions={})
            path = child / 'registration.json'
            save(path, source.sealed(packet, 'registration_sha256'))
            def generated(bars, first, end):
                return (dev, [], {}) if first == source.START else (signals, hours, {})
            with patch.object(source, 'JOB', job), patch.object(source, 'SOURCE_JOB', child), \
                 patch.object(source, 'verify_release', return_value=release), \
                 patch.object(source, 'load_books', return_value=([], {})), \
                 patch.object(source, 'generated_signals', side_effect=generated), \
                 patch.dict(source.CANONICAL, {'s01_registration': (Path(original_pin['path']), original_pin['sha256'])}):
                self.assertEqual(source.verify_source_registration()['signals'], signals)
                for mode in ('stop', 'side', 'remove'):
                    changed = deepcopy(packet)
                    if mode == 'stop':
                        changed['signals'][0]['stop_units'] -= 1
                    elif mode == 'side':
                        changed['signals'][0]['side'] = 'SELL'
                    else:
                        changed['signals'] = changed['signals'][:1]
                    _, changed['hours'] = source.signal_census(changed['signals'])
                    changed['missing_hours'] = changed['hours']
                    save(path, source.sealed(changed, 'registration_sha256'))
                    with self.subTest(mode=mode), self.assertRaisesRegex(ValueError, 'registered_raw_recipe_changed'):
                        source.verify_source_registration()


if __name__ == '__main__':
    unittest.main()
