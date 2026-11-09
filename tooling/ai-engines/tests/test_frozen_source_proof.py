from pathlib import Path
import json
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from test_explicit_m1_view import fixture, CALENDAR, write
from explicit_m1_view import prepare
from sealed_m1_review import digest, verify_source_proof


def check(root, **kwargs):
    return verify_source_proof(root,json.loads((root/'manifest.json').read_text()),
        json.loads((root/'result.json').read_text()),CALENDAR,**kwargs)


class FrozenSourceProofTests(unittest.TestCase):
    def setup_view(self, base):
        parent,protocol=fixture(base);out=base/'explicit';prepare(parent,CALENDAR,protocol,out)
        return out,protocol

    def test_default_keeps_strict_binding_but_explicit_snapshot_can_reuse_protocol(self):
        with tempfile.TemporaryDirectory() as temp:
            out,protocol=self.setup_view(Path(temp));old_hash=digest(out/'source-observation-proof.json')
            protocol.write_text('New protocol, old frozen record remains historical.')
            with self.assertRaisesRegex(ValueError,'input_or_code_changed'):check(out)
            result=check(out,frozen_source=True)
            self.assertTrue(result['source_presence_verified'])
            self.assertEqual(len(result['historical_source_snapshots']),1)
            self.assertIn('not_current_producer_validation',result['source_validation_scope'])
            self.assertEqual(digest(out/'source-observation-proof.json'),old_hash)

    def test_missing_corrupt_and_ambiguous_snapshot_rejected(self):
        for mode in ('missing','corrupt','ambiguous'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                out,protocol=self.setup_view(Path(temp));protocol.write_text('Changed protocol.')
                snap=next((out/'source-snapshot').glob('*-'+protocol.name))
                if mode=='missing':snap.unlink()
                elif mode=='corrupt':snap.write_text('Corrupt historical bytes.')
                else:(snap.parent/('999-'+protocol.name)).write_bytes(snap.read_bytes())
                with self.assertRaisesRegex(ValueError,'snapshot_missing_or_ambiguous'):check(out,frozen_source=True)

    def test_frozen_code_does_not_allow_changed_raw_or_calendar(self):
        for mode in ('raw','calendar'):
            with self.subTest(mode=mode),tempfile.TemporaryDirectory() as temp:
                out,protocol=self.setup_view(Path(temp));proof=json.loads((out/'source-observation-proof.json').read_text())
                if mode=='raw':
                    raw=Path(proof['quarters'][0]['sides'][0]['responses'][0]['path'])
                    (out/'source-snapshot'/('999-'+raw.name)).write_bytes(raw.read_bytes())
                    raw.write_bytes(raw.read_bytes()+b' ')
                    with self.assertRaisesRegex(ValueError,'input_or_code_changed'):check(out,frozen_source=True)
                else:
                    # A source-pin calendar is data even when an authentic old
                    # copy exists. Do not redirect it as code/protocol.
                    custom=Path(temp)/'calendar.json';custom.write_bytes(CALENDAR.read_bytes())
                    proof['source_pins'][str(custom.resolve())]=digest(custom)
                    (out/'source-snapshot'/'999-calendar.json').write_bytes(custom.read_bytes())
                    custom.write_text('{}')
                    write(out/'source-observation-proof.json',proof)
                    result=json.loads((out/'result.json').read_text());result['sourceObservationProofSha256']=digest(out/'source-observation-proof.json');write(out/'result.json',result)
                    with self.assertRaisesRegex(ValueError,'cannot_redirect_data'):check(out,frozen_source=True)

    def test_forged_validator_hash_still_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out,_=self.setup_view(Path(temp));proof=json.loads((out/'source-observation-proof.json').read_text());proof['validator_sha256']='0'*64
            write(out/'source-observation-proof.json',proof)
            result=json.loads((out/'result.json').read_text());result['sourceObservationProofSha256']=digest(out/'source-observation-proof.json');write(out/'result.json',result)
            with self.assertRaisesRegex(ValueError,'proof_contract'):check(out,frozen_source=True)

    def test_opt_in_is_boolean_and_default_missing_source_remains_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            out,protocol=self.setup_view(Path(temp))
            for mode in ('false',1,None):
                with self.subTest(mode=mode),self.assertRaisesRegex(ValueError,'explicit_boolean'):
                    check(out,frozen_source=mode)
            protocol.unlink()
            with self.assertRaisesRegex(ValueError,'input_or_code_changed'):check(out)
            self.assertTrue(check(out,frozen_source=True)['source_presence_verified'])

    def test_missing_input_with_forged_null_hash_is_never_a_matching_binding(self):
        with tempfile.TemporaryDirectory() as temp:
            out,_=self.setup_view(Path(temp));proof=json.loads((out/'source-observation-proof.json').read_text())
            parent_manifest=Path(temp)/'parent/manifest.json'
            self.assertIn(str(parent_manifest.resolve()),proof['input_bindings'])
            parent_manifest.unlink();proof['input_bindings'][str(parent_manifest.resolve())]=None
            write(out/'source-observation-proof.json',proof)
            result=json.loads((out/'result.json').read_text());result['sourceObservationProofSha256']=digest(out/'source-observation-proof.json');write(out/'result.json',result)
            with self.assertRaisesRegex(ValueError,'input_or_code_changed'):check(out,frozen_source=True)


if __name__=='__main__':unittest.main()
