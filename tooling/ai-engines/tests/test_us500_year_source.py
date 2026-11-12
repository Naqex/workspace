from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from us500_year_source import load_year_side


def write(path, value):
    path.write_text(json.dumps(value)+'\n', encoding='utf-8')
    return hashlib.sha256(path.read_bytes()).hexdigest()


def fixture(root, year=2019):
    seals = []
    for q in range(1, 5):
        at = int(datetime(year, 3*q-2, 2, tzinfo=timezone.utc).timestamp()*1000)
        for side in ('bid', 'ask'):
            p = root/f'q{q}-{side}.json'; digest = write(p, [dict(timestamp=at, close=100)])
            seals.append(dict(request=f'q{q}-{side}', rows=1, first=at, last=at, sha256=digest))
    proof = dict(schema='explicit-source-M1-proof-v1', status='source_explicit_prices_and_pairing_verified',
        policy='paired-explicit-source-M1-v1', instrument='usa500idxusd', year=year, holdout_read=False,
        quarters=[dict(quarter=q) for q in range(1, 5)], output_seals=seals)
    return proof, write(root/'source-observation-proof.json', proof)


class US500YearSourceTests(unittest.TestCase):
    def test_explicit_historical_scope_preserves_default_and_proof_checks(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, sha = fixture(root, 2013)
            with self.assertRaisesRegex(ValueError, 'explicit_registered_year'):
                load_year_side(root, year=2013, side='bid', proof_sha256=sha)
            loaded = load_year_side(root, year=2013, side='bid', proof_sha256=sha, registered_years=(2013,))
            self.assertEqual(len(loaded['rows']), 4)
            with self.assertRaisesRegex(ValueError, 'accepted_source_proof_binding'):
                load_year_side(root, year=2013, side='bid', proof_sha256='0'*64, registered_years=(2013,))

    def test_explicit_scope_never_opens_reserved_or_unregistered_years(self):
        for years in ((2025,), (2012,), (), (2014, 2013), (2013, 2013), [2013], (True,)):
            with self.assertRaisesRegex(ValueError, 'explicit_registered_year'):
                load_year_side(Path('not_read').resolve(), year=2013, side='bid', proof_sha256='0'*64, registered_years=years)
        with self.assertRaisesRegex(ValueError, 'explicit_registered_year'):
            load_year_side(Path('not_read').resolve(), year=2014, side='bid', proof_sha256='0'*64, registered_years=(2013,))

    def test_recent_accepted_years_and_reserved_holdout_boundary(self):
        for year in (2023,2024):
            with tempfile.TemporaryDirectory() as temp:
                root=Path(temp);_,sha=fixture(root,year)
                self.assertEqual(len(load_year_side(root,year=year,side='bid',proof_sha256=sha)['rows']),4)
        with self.assertRaisesRegex(ValueError,'explicit_registered_year'):
            load_year_side(Path('not_read').resolve(),year=2025,side='bid',proof_sha256='0'*64)

    def test_all_quarters_are_loaded_and_bound_for_each_side(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); _, digest = fixture(root)
            for side in ('bid', 'ask'):
                result = load_year_side(root, year=2019, side=side, proof_sha256=digest)
                self.assertEqual(result['quarter_rows'], {1: 1, 2: 1, 3: 1, 4: 1})
                self.assertEqual(len(result['rows']), 4); self.assertEqual(len(result['bindings']), 5)

    def test_pilot_only_quarters_or_missing_side_cannot_be_a_year(self):
        for mode in ('pilot', 'missing', 'duplicate'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); proof, _ = fixture(root)
                if mode == 'pilot': proof['quarters'] = [dict(quarter=1), dict(quarter=3)]
                elif mode == 'missing': proof['output_seals'].pop(2)
                else: proof['output_seals'][2] = proof['output_seals'][0]
                digest = write(root/'source-observation-proof.json', proof)
                with self.assertRaisesRegex(ValueError, 'four_quarter'): load_year_side(root, year=2019, side='bid', proof_sha256=digest)

    def test_changed_proof_or_canonical_file_rejected(self):
        for mode in ('proof', 'quarter'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); _, digest = fixture(root)
                p = root/('source-observation-proof.json' if mode == 'proof' else 'q2-bid.json')
                p.write_bytes(p.read_bytes()+b' ')
                with self.assertRaises(ValueError): load_year_side(root, year=2019, side='bid', proof_sha256=digest)

    def test_wrong_year_clock_or_census_cannot_be_hidden_by_resealing(self):
        for mode in ('year', 'clock', 'census'):
            with self.subTest(mode=mode), tempfile.TemporaryDirectory() as temp:
                root = Path(temp); proof, _ = fixture(root)
                if mode == 'year': proof['year'] = 2022
                elif mode == 'census': proof['output_seals'][2]['rows'] = 0
                else:
                    p = root/'q2-bid.json'; digest = write(p, [dict(timestamp=0, close=100)])
                    proof['output_seals'][2].update(sha256=digest, first=0, last=0)
                digest = write(root/'source-observation-proof.json', proof)
                with self.assertRaises(ValueError): load_year_side(root, year=2019, side='bid', proof_sha256=digest)


if __name__ == '__main__': unittest.main()
