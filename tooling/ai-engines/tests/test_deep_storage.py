from pathlib import Path
import sys
import tempfile
import unittest
import hashlib

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from workspace_maintenance import inventory
from deep_storage import disjoint_partitions, cold_zip, generated_dependencies, backup_plan, apply_backup_plan


class DeepStorageTests(unittest.TestCase):
    def cache_plan(self, root):
        for owner in ("old-a","old-b"):
            p=root/owner/"cargo-target"
            p.mkdir(parents=True)
            (p/"compiled.o").write_bytes(b"generated")
        plan=root/"plan.json"
        backup_plan(inventory(root),plan)
        return plan,hashlib.sha256(plan.read_bytes()).hexdigest()

    def test_hash_bound_cache_apply_keeps_unlisted_research(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            plan,digest=self.cache_plan(root)
            keep=root/"ai-engine-jobs/raw.csv";keep.parent.mkdir();keep.write_bytes(b"market")
            out=apply_backup_plan(plan,digest,root,root/"applied.json")
            self.assertEqual(out["files"],2)
            self.assertEqual(out["folders"],2)
            self.assertTrue(keep.exists())
            self.assertFalse((root/"old-a/cargo-target").exists())

    def test_preflight_all_targets_before_any_delete_on_drift(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan,digest=self.cache_plan(root)
            (root/"old-b/cargo-target/new.o").write_bytes(b"not authorized")
            with self.assertRaisesRegex(ValueError,"manifest_drift"):
                apply_backup_plan(plan,digest,root,root/"applied.json")
            self.assertTrue((root/"old-a/cargo-target/compiled.o").exists())

    def test_active_reference_and_manifest_hash_block_purge(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);plan,digest=self.cache_plan(root)
            for hashed,refs in (("0"*64,()),(digest,[(root/"old-a/cargo-target").as_posix()+"/app.exe"])):
                with self.assertRaises(ValueError):
                    apply_backup_plan(plan,hashed,root,root/"applied.json",active_references=refs)
            self.assertTrue((root/"old-a/cargo-target/compiled.o").exists())

    def test_market_data_extension_in_cache_is_never_deleted(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);cache=root/"old/cargo-target";cache.mkdir(parents=True)
            (cache/"XAUUSD.csv").write_bytes(b"market")
            plan=root/"plan.json";backup_plan(inventory(root),plan)
            with self.assertRaisesRegex(ValueError,"protected_data"):
                apply_backup_plan(plan,hashlib.sha256(plan.read_bytes()).hexdigest(),root,root/"applied.json")
            self.assertTrue((cache/"XAUUSD.csv").exists())

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
