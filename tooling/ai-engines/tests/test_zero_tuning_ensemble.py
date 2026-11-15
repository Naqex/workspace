import sys
from pathlib import Path
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from quant_core.zero_tuning_ensemble import mechanical_composition, cumulative_drawdown


def row(name,series,events,asset="XAUUSD",family="F4"):
    return dict(id=name,daily=series,events=events,asset=asset,family=family)


class EnsembleTests(unittest.TestCase):
    def test_versioned_correlation_limit_preserves_default_and_supports_V12(self):
        a=np.array([1.,-1.,1.,-1.])
        noise=np.array([1.,1.,-1.,-1.])
        b=.27*a+np.sqrt(1-.27**2)*noise
        rows=[dict(id="a",asset="XAUUSD",family="F1",daily=a,events=[1]),
              dict(id="b",asset="US500",family="F5",daily=b,events=[2])]
        self.assertEqual(len(mechanical_composition(rows)["selected"]),2)
        self.assertEqual(len(mechanical_composition(rows,correlation_limit=.25)["selected"]),1)

    def test_component_can_be_low_frequency_without_four_positive_years(self):
        from prop_v11_campaign import component_reasons
        clusters=[dict(years=[y,y+1,y+2],retention=.8,scale_ratio=.1,
                       net=dict(SYM=dict(raw=1,admitted=2))) for y in (2018,2021)]
        row_=dict(clusters=clusters,annual=[dict(raw=5,priced=5,admitted=4,
                   economics=dict(SYM=dict(admitted_net_R=.4))) for _ in range(6)])
        self.assertEqual(component_reasons(row_),[])
        row_["annual"][0]["priced"]=4
        self.assertIn("ENDPOINT_INCOMPLETE",component_reasons(row_))

    def test_same_events_different_horizons_are_one_cluster_even_with_low_return_correlation(self):
        a=row("a",[1,-1,1,-1],[1,2])
        b=row("b",[1,1,-1,-1],[1,2])
        out=mechanical_composition([a,b])
        self.assertEqual(out["selected"],["a"])
        self.assertEqual(out["clusters"][0]["members"],["a","b"])
        self.assertFalse(out["subset_search"])

    def test_medoid_is_central_not_highest_profit_and_input_order_does_not_matter(self):
        a=row("a",[1,2,3,4],[1])
        b=row("b",[100,200,300,400],[2])
        c=row("c",[-1,1,1,-1],[3],asset="EURUSD",family="F1")
        first=mechanical_composition([a,b,c])
        second=mechanical_composition([c,b,a])
        self.assertEqual(first,second)
        self.assertNotIn("b",first["selected"])
        self.assertEqual(set(first["weights"].values()),{1})

    def test_correlated_cross_family_representative_is_blocked_without_subset_search(self):
        rows=[row("a",[1,2,3,4],[1],family="F1"),
              row("b",[10,20,30,40],[2],family="F3")]
        out=mechanical_composition(rows)
        self.assertEqual(out["selected"],["a"])
        self.assertEqual(out["blocked"][0]["reason"],"CORRELATION")

    def test_constant_vector_is_not_claimed_orthogonal_and_empty_is_explicit(self):
        out=mechanical_composition([row("a",[1,1,1],[1]),row("b",[1,2,1],[2],family="F3")])
        self.assertEqual(len(out["selected"]),1)
        self.assertEqual(mechanical_composition([])["selected"],[])

    def test_drawdown_includes_initial_losses_and_recovery(self):
        self.assertEqual(cumulative_drawdown([-2,1,-3,7]),4)
        self.assertEqual(cumulative_drawdown([1,2,3]),0)

    def test_duplicate_ids_and_nonfinite_values_are_rejected(self):
        with self.assertRaises(ValueError):
            mechanical_composition([row("a",[1,2],[1]),row("a",[3,4],[2])])
        with self.assertRaises(ValueError):
            mechanical_composition([row("a",[1,float("nan")],[1])])
