from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from check_anti_bloat import evaluate, LIMIT


class AntiBloatTests(unittest.TestCase):
    def test_large_raw_payload_fails_but_compressed_or_code_does_not(self):
        self.assertFalse(evaluate([dict(path="new.csv", bytes=LIMIT + 1)])["passed"])
        self.assertTrue(evaluate([dict(path="archive.csv.gz", bytes=LIMIT + 1),
                                  dict(path="code.py", bytes=LIMIT + 1)])["passed"])

    def test_many_small_files_and_aggregate_budget_fail(self):
        self.assertFalse(evaluate([dict(path=f"{k}.json", bytes=1) for k in range(101)])["passed"])
        self.assertFalse(evaluate([dict(path=f"{k}.json", bytes=LIMIT) for k in range(9)])["passed"])
