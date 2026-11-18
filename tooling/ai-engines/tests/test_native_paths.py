from pathlib import Path
import os
import subprocess
import tempfile
import unittest
from quant_core.native_paths import io_path, logical_path, PathGuard, read_bounded


class NativePathTests(unittest.TestCase):
    def test_prefix_roundtrip_and_already_extended_path(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "sample.py"
            self.assertEqual(logical_path(io_path(p)), p)
            self.assertEqual(io_path(io_path(p)), io_path(p))

    def test_real_deep_path_has_no_max_path_read_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / ("segment" * 12) / ("layer" * 16) / ("deep" * 20) / "bot.py"
            self.assertGreater(len(str(p)), 260)
            io_path(p.parent).mkdir(parents=True)
            try:
                io_path(p).write_bytes(b"source-data-only")
                self.assertEqual(read_bounded(p, 100), b"source-data-only")
            finally:
                io_path(p).unlink()
                for parent in (p.parent, *list(p.parent.parents)[:2]):
                    io_path(parent).rmdir()

    def test_size_missing_and_parent_paths_fail_without_partial_read(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / "bot.py"
            p.write_bytes(b"12345")
            with self.assertRaisesRegex(ValueError, "SIZE_LIMIT"):
                read_bounded(p, 4)
            with self.assertRaises(FileNotFoundError):
                read_bounded(p.with_name("missing"), 100)
            with self.assertRaisesRegex(ValueError, "PARENT_PATH"):
                read_bounded(p.parent / "nested" / ".." / p.name, 100)

    def test_junction_or_symlink_ancestor_is_never_followed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            target = root / "target"
            target.mkdir()
            (target / "secret.py").write_bytes(b"never-read")
            alias = root / "alias"
            if os.name == "nt":
                result = subprocess.run(["cmd", "/c", "mklink", "/J", str(alias), str(target)],
                                        capture_output=True)
                self.assertEqual(result.returncode, 0)
            else:
                alias.symlink_to(target, target_is_directory=True)
            with self.assertRaisesRegex(ValueError, "REPARSE"):
                read_bounded(alias / "secret.py", 100)
            with self.assertRaisesRegex(ValueError, "REPARSE"):
                read_bounded(alias, 100)
            self.assertEqual((target / "secret.py").read_bytes(), b"never-read")

    def test_unc_is_not_probed(self):
        with self.assertRaisesRegex(ValueError, "NONLOCAL"):
            PathGuard().admit("\\\\untrusted-server\\share\\file.py")
