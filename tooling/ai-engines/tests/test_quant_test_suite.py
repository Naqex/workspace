"""Regression tests for quant_test_suite LPT sharding and stdlib-safe RepoModuleFinder."""
import importlib.machinery
from pathlib import Path
import unittest

import quant_test_suite as qts


class QuantTestSuiteTests(unittest.TestCase):
    def test_assign_shards_balances_heavy_modules_deterministically(self):
        selected = qts.modules("complete", "all")
        batches_a = qts.assign_shards(selected, 4)
        batches_b = qts.assign_shards(selected, 4)
        self.assertEqual(batches_a, batches_b)
        flat = [m for b in batches_a for m in b]
        self.assertEqual(sorted(flat), sorted(selected))
        # The two heaviest modules must not land in the same shard when workers=4.
        shard_of = {m: i for i, b in enumerate(batches_a) for m in b}
        self.assertNotEqual(shard_of["test_shadow_reconcile"], shard_of["test_forex_study_batch"])

    def test_repo_module_finder_indexes_pass_modules_and_never_shadows_stdlib(self):
        finder = qts.RepoModuleFinder()
        for name in ("pass12_usdjpy_forensic", "pass12_us500_ny_orb", "test_pass12_forensics", "quant_core.market_data_store"):
            spec = finder.find_spec(name)
            self.assertIsNotNone(spec, f"Expected local spec for {name}")
            self.assertIsInstance(spec.loader, importlib.machinery.SourceFileLoader)
            self.assertTrue(Path(spec.origin).is_file())
        for external in ("json", "sys", "os", "numpy", "pyarrow"):
            self.assertIsNone(finder.find_spec(external))


if __name__ == "__main__":
    unittest.main()
