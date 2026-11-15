from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workspace_maintenance import inventory
from deep_storage import disjoint_partitions, cold_zip, generated_dependencies, backup_plan


class DeepStorageTests(unittest.TestCase):
    def test_disjoint_accounts_for_root_files_and_all_depths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for rel in ("root.bin", "a/direct.bin", "a/b/deep.bin"):
                p = root / rel
                p.parent.mkdir(parents=True, exist_ok=True)
                p.write_bytes(b"123")
            census = inventory(root)
            parts = disjoint_partitions(census)
            self.assertEqual(sum(r["bytes"] for r in parts.values()), 9)
            self.assertEqual(sum(r["files"] for r in parts.values()), 3)
            self.assertIn("a/b", parts)

    def test_zip_roundtrip_has_sha_manifest_before_source_removal(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            cold = root / ".artifacts/closed-derived"
            cold.mkdir(parents=True)
            (cold / "series.json").write_text('{"preserve":true}')
            result = cold_zip(root, cold, root / "cold.zip", remove=True)
            self.assertFalse(cold.exists())
            self.assertIn("series.json", result["files"])
            self.assertTrue((root / "cold.MANIFEST.json").exists())
            with self.assertRaises(ValueError):
                cold_zip(root, root, root / "bad.zip")

    def test_dependency_purge_refuses_active_and_vi_paths(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for p in (root/"projects/vi-dubber/node_modules", root/"app/node_modules"):
                p.mkdir(parents=True)
                with self.assertRaises(ValueError):
                    generated_dependencies(root, p)
            p = root/"tooling/ui-qa/artifacts/old/node_modules"
            p.mkdir(parents=True)
            (p/"fixture.js").write_text("generated")
            self.assertEqual(generated_dependencies(root, p)["files"], 1)

    def test_backup_plan_keeps_research_and_backup_source_untouched(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for rel in ("ai-engine-jobs/cargo-target", "old/cargo-target", "workspace/rust-target"):
                p = root/rel
                p.mkdir(parents=True)
                (p/"fixture.bin").write_bytes(b"keep")
            census=inventory(root)
            result=backup_plan(census, root/"dry-run.json")
            self.assertEqual(result["potential_files"], 1)
            self.assertFalse(result["executed"])
            self.assertTrue((root/"old/cargo-target/fixture.bin").exists())
