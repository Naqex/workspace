from pathlib import Path
import sys
import tempfile
import unittest
sys.path[:0]=[str(Path(__file__).resolve().parents[1]),str(Path(__file__).resolve().parents[2])]
from prop_v13_campaign import ensemble_gate
from deep_storage import merkle_tree


class V13ProtocolTests(unittest.TestCase):
    def decision(self, values, counts=None):
        annual=[dict(year=2018+i,trades=(counts or [50]*6)[i],
                     models={m:dict(net_R=v) for m in ("SYM","ASYM")}) for i,v in enumerate(values)]
        return ensemble_gate([dict(asset="XAUUSD",family="F3"),dict(asset="EURUSD",family="F5")],annual)

    def test_V13_stability_OR_accepts_two_positive_clusters_with_positive_exbest(self):
        d=self.decision([-1,2,3,-1,2,3])
        self.assertTrue(d["passed"],d)
        self.assertEqual(d["metrics"]["SYM"]["positive_years"],4)

    def test_five_positive_years_is_the_other_registered_stability_route(self):
        d=self.decision([1,1,1,1,1,-6])
        self.assertTrue(d["passed"],d)
        self.assertLess(d["metrics"]["SYM"]["ex_best_R"],0)

    def test_cadence_cannot_use_multi_year_average_to_hide_a_sparse_year(self):
        d=self.decision([1]*6,[49,100,100,100,100,100])
        self.assertIn("CADENCE_BELOW50_IN_A_YEAR",d["reasons"])

    def test_one_positive_cluster_and_four_positive_years_does_not_pass(self):
        self.assertFalse(self.decision([-4,1,1,-1,1,1])["passed"])

    def test_Merkle_requires_all_relative_paths_not_a_filename_sample(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/"a",Path(temp)/"b";a.mkdir();b.mkdir()
            for p in (a,b):(p/"same.py").write_text("same")
            self.assertEqual(merkle_tree(a)["merkle_sha256"],merkle_tree(b)["merkle_sha256"])
            (b/"unique.txt").write_text("keep")
            self.assertNotEqual(merkle_tree(a)["merkle_sha256"],merkle_tree(b)["merkle_sha256"])

    def test_Merkle_includes_empty_directories(self):
        with tempfile.TemporaryDirectory() as temp:
            a,b=Path(temp)/"a",Path(temp)/"b";a.mkdir();b.mkdir()
            (a/"empty").mkdir()
            self.assertNotEqual(merkle_tree(a)["merkle_sha256"],merkle_tree(b)["merkle_sha256"])

    def test_Merkle_detects_content_change_with_same_length(self):
        with tempfile.TemporaryDirectory() as temp:
            a=Path(temp);(a/"x").write_bytes(b"1234")
            before=merkle_tree(a)
            (a/"x").write_bytes(b"4321")
            after=merkle_tree(a)
            self.assertNotEqual(before["merkle_sha256"],after["merkle_sha256"])


if __name__=="__main__":
    unittest.main()
