import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workspace_maintenance import inventory, purge, compact_environment, purge_incremental, snapshot_view, maintain


class MaintenanceTests(unittest.TestCase):
    def test_purge_preserves_canonical_and_vi_wip_and_rejects_outside(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name in ("src/__pycache__", "projects/vi-dubber/__pycache__", "source-cache"):
                p = root / name
                p.mkdir(parents=True)
                (p / "keep.bin").write_bytes(b"fixture")
            d = inventory(root)
            self.assertEqual(len(d["cache_candidates"]), 1)
            r = purge(root, d["cache_candidates"])
            self.assertEqual(r["files"], 1)
            self.assertTrue((root / "source-cache/keep.bin").exists())
            self.assertTrue((root / "projects/vi-dubber/__pycache__/keep.bin").exists())
            with self.assertRaisesRegex(ValueError, "not_disposable"):
                purge(root, [root / "source-cache"])
            with self.assertRaises(ValueError):
                purge(root, [root.parent / "__pycache__"])

    def test_all_targets_preflight_before_first_delete(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "__pycache__").mkdir()
            with self.assertRaises(ValueError):
                purge(root, [root / "__pycache__", root / "source-cache"])
            self.assertTrue((root / "__pycache__").exists())

    def test_cold_environment_archive_keeps_manifest_and_refuses_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            env = root / ".artifacts/old/.venv"
            env.mkdir(parents=True)
            (env / "fixture.bin").write_bytes(b"restore me")
            dest = root / "archive.tar.gz"
            r = compact_environment(root, env, dest)
            self.assertFalse(env.exists())
            self.assertEqual(r["files"]["fixture.bin"], hashlib.sha256(b"restore me").hexdigest())
            self.assertTrue(dest.with_suffix(".gz.MANIFEST.json").exists())
            with self.assertRaisesRegex(ValueError, "not_cold"):
                compact_environment(root, root / "source-cache", root / "other.tar.gz")

    def test_rust_cleanup_does_not_accept_general_target_or_source(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "app/target/debug/incremental"
            path.mkdir(parents=True)
            (path / "cache.bin").write_bytes(b"cache")
            (path.parent / "api.exe").write_bytes(b"binary")
            self.assertEqual(purge_incremental(root, path)["files"], 1)
            self.assertTrue((path.parent / "api.exe").exists())
            with self.assertRaises(ValueError):
                purge_incremental(root, path.parent)

    def test_absolute_input_never_overrides_snapshot_destination(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            source = root / "immutable.json"
            source.write_bytes(b'{"fixture":1}\r\n')
            before = source.stat().st_mtime_ns
            expected = hashlib.sha256(b'{"fixture":1}\n').hexdigest()
            out = snapshot_view([dict(path=str(source.resolve()), sha256=expected)], root / "view")
            self.assertTrue(Path(out[0]["snapshot"]).is_relative_to(root / "view"))
            self.assertEqual(source.stat().st_mtime_ns, before)
            self.assertEqual(source.read_bytes(), b'{"fixture":1}\r\n')
            self.assertEqual(Path(out[0]["snapshot"]).read_bytes(), b'{"fixture":1}\n')
            with self.assertRaisesRegex(ValueError, "content_changed"):
                snapshot_view([dict(path=str(source), sha256="0"*64)], root / "other")

    def test_one_command_health_cleanup_and_backup_preview_keeps_backup_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder) / "workspace"
            cache = root / "__pycache__"
            cache.mkdir(parents=True)
            (cache / "fixture.pyc").write_bytes(b"cache")
            backup = Path(folder) / "backup"
            preview = maintain(root, destination=backup)
            self.assertTrue(cache.exists())
            self.assertIn("/L", preview["backup"]["command"])
            applied = maintain(root, destination=backup, apply_caches=True)
            self.assertFalse(cache.exists())
            self.assertFalse(backup.exists())
            self.assertEqual(applied["cache_purge"]["files"], 1)
            self.assertEqual(applied["after"]["groups"]["/"]["files"], 0)
            self.assertFalse(applied["backup_copied"])
