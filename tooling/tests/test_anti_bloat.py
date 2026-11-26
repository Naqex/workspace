import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_anti_bloat import LIMIT, evaluate, parse_raw_diff_paths


class AntiBloatTests(unittest.TestCase):
    def test_large_raw_payload_fails_but_compressed_or_code_does_not(self):
        self.assertFalse(evaluate([dict(path="new.csv", bytes=LIMIT + 1)])["passed"])
        self.assertTrue(
            evaluate([dict(path="archive.csv.gz", bytes=LIMIT + 1), dict(path="code.py", bytes=LIMIT + 1)])["passed"]
        )

    def test_many_small_files_and_aggregate_budget_fail(self):
        self.assertFalse(evaluate([dict(path=f"{k}.json", bytes=1) for k in range(101)])["passed"])
        self.assertFalse(evaluate([dict(path=f"{k}.json", bytes=LIMIT) for k in range(9)])["passed"])

    def test_exact_r100_rename_is_grandfathered_but_modified_rename_and_copy_fail(self):
        sha_a = "a" * 40
        sha_b = "b" * 40
        raw = (
            f":100644 100644 {sha_a} {sha_a} R100\0old/hist.json\0archive/hist.json\0"
            f":100644 100644 {sha_a} {sha_b} R095\0old/edit.json\0archive/edit.json\0"
            f":100644 100644 {sha_a} {sha_a} C100\0old/hist.json\0dup/hist.json\0"
            f":000000 100644 {'0' * 40} {sha_b} A\0new/raw.csv\0"
        ).encode()
        self.assertEqual(
            parse_raw_diff_paths(raw),
            ["archive/edit.json", "dup/hist.json", "new/raw.csv"],
        )
