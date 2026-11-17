from pathlib import Path
import hashlib
import json
import tempfile
import unittest
from evidence_compaction import EvidenceStore, prepare, apply, digest


class EvidenceCompactionTests(unittest.TestCase):
    def fixture(self, root):
        (root/"rows.json").write_bytes(b'{"a":123}\n'*100)
        (root/"journal.jsonl").write_bytes(b'{"failed":true}\n'*100)
        (root/"small.md").write_text("keep",encoding="utf-8")

    def test_compression_preserves_exact_bytes_failures_and_restorable_paths(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root)
            before={p.name:p.read_bytes() for p in root.iterdir()}
            manifest=prepare(root,min_bytes=100)
            self.assertEqual(len(manifest["entries"]),2)
            store=EvidenceStore(root)
            result=apply(root,digest(store.manifest_path))
            self.assertEqual(len(result["removed"]),2)
            self.assertTrue((root/"small.md").exists())
            for name,data in before.items():
                self.assertEqual(store.read_bytes(name),data)
                self.assertEqual(store.canonical_sha(name),hashlib.sha256(data).hexdigest())
            self.assertEqual(store.restore(),2)
            self.assertEqual({p.name:p.read_bytes() for p in root.iterdir() if p.is_file()},before)

    def test_all_originals_preflight_before_any_delete_on_drift(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);prepare(root,min_bytes=100);store=EvidenceStore(root)
            (root/"rows.json").write_bytes(b'changed')
            with self.assertRaisesRegex(ValueError,"drift_preflight"):
                apply(root,digest(store.manifest_path))
            self.assertTrue((root/"journal.jsonl").exists())

    def test_corrupt_archive_prevents_unlink_and_cannot_be_read_after_loss(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);prepare(root,min_bytes=100);store=EvidenceStore(root)
            row=next(iter(store.entries.values()));p=root/row["compressed_relative"]
            p.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError,"compressed_checksum"):
                apply(root,digest(store.manifest_path))
            self.assertTrue((root/row["relative"]).exists())

    def test_manifest_escape_and_wrong_root_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);prepare(root,min_bytes=100);store=EvidenceStore(root)
            m=store.manifest;m["entries"][0]["relative"]="../outside"
            store.manifest_path.write_text(json.dumps(m),encoding="utf-8")
            with self.assertRaisesRegex(ValueError,"relative_path"):EvidenceStore(root)

    def test_wrong_manifest_digest_and_repeat_attempt_do_not_delete(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);prepare(root,min_bytes=100)
            with self.assertRaisesRegex(ValueError,"hash_mismatch"):apply(root,"0"*64)
            with self.assertRaisesRegex(ValueError,"already_exists"):prepare(root,min_bytes=100)
            self.assertTrue((root/"rows.json").exists())

    def test_numpy_archive_is_array_equivalent_without_pickle_or_padding(self):
        import numpy as np
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);a=np.array([(1,2),(3,4)],dtype=[("t","<i8"),("price","<i8")])
            np.save(root/"quotes.npy",a);prepare(root,min_bytes=1);store=EvidenceStore(root)
            apply(root,digest(store.manifest_path))
            np.testing.assert_array_equal(store.numpy("quotes.npy"),a)
            self.assertEqual(store.numpy("quotes.npy").dtype,a.dtype)

    def test_existing_restore_collision_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);self.fixture(root);prepare(root,min_bytes=100);store=EvidenceStore(root)
            apply(root,digest(store.manifest_path));(root/"rows.json").write_bytes(b"new owner data")
            with self.assertRaisesRegex(ValueError,"collision"):store.restore()
            self.assertEqual((root/"rows.json").read_bytes(),b"new owner data")


if __name__ == "__main__":unittest.main()
