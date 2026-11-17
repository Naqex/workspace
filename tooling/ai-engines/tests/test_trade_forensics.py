from copy import deepcopy
from datetime import datetime,timezone
import unittest
import numpy as np
from quant_core.trade_forensics_classifier import classify,excursions,summarize,concentration
from quant_core.behavioral_signals import london_hour,closed_atr,recipes


def row(**kw):
    r=dict(net_R=1.,MFE_R=1.2,MAE_R=.2,reason="HORIZON",family="F3",post_path_unknown=False,
           open_path_unknown=False,day_range_ATR=.5,trade_key="fixture")
    r.update(kw);return r


class ForensicTests(unittest.TestCase):
    def test_favorable_geometry_is_description_not_skill_certificate(self):
        r=classify(row());self.assertEqual(r["label"],"W1");self.assertFalse(r["causal_skill_or_manipulation_identified"])

    def test_near_death_boundary_precedes_good_reward_adverse_ratio(self):
        self.assertEqual(classify(row(MAE_R=.8,MFE_R=5))["label"],"W2")

    def test_unverified_positive_path_never_becomes_structural_win(self):
        r=classify(row(open_path_unknown=True));self.assertEqual(r["label"],"W2");self.assertTrue(r["provisional"])

    def test_late_burst_requires_both_late_share_and_mostly_unprofitable_path(self):
        self.assertEqual(classify(row(late_jump_share=.8,profitable_fraction=.2))["label"],"W2")
        self.assertEqual(classify(row(late_jump_share=.8,profitable_fraction=.21))["label"],"W1")

    def test_positive_residual_is_explicit_fragile_geometry(self):
        self.assertEqual(classify(row(MAE_R=.7,MFE_R=.1))["label"],"W2")

    def test_stop_recovery_requires_stop_and_one_R_recovery(self):
        self.assertEqual(classify(row(net_R=-1,reason="SL",post_MFE_R=1,MFE_R=.1))["label"],"L1")
        self.assertEqual(classify(row(net_R=-.1,post_MFE_R=2,MFE_R=.1))["label"],"L4")

    def test_giveback_overlap_is_not_lost_to_exclusive_priority(self):
        r=classify(row(net_R=-1,reason="SL",post_MFE_R=2,MFE_R=1.2))
        self.assertEqual(r["label"],"L1");self.assertTrue(r["flags"]["L2"])

    def test_giveback_boundary_and_pre_protection_bucket(self):
        r=classify(row(net_R=0,MFE_R=.8));self.assertEqual(r["label"],"L2");self.assertEqual(r["giveback_bucket"],"0.80–<1.00")

    def test_exhaustion_is_not_assigned_to_FX_range_rejection(self):
        self.assertEqual(classify(row(net_R=-1,MFE_R=.2,day_range_ATR=.91))["label"],"L3")
        self.assertEqual(classify(row(net_R=-1,MFE_R=.2,day_range_ATR=.91,family="F5"))["label"],"L4")

    def test_unknown_loss_is_provisional_not_certified_clean(self):
        self.assertTrue(classify(row(net_R=-1,MFE_R=.1,reason="SL",post_path_unknown=True))["provisional"])

    def test_nonfinite_and_negative_magnitudes_rejected(self):
        for r in (row(net_R=float("nan")),row(MAE_R=-1)):
            with self.assertRaises(ValueError):classify(r)

    def test_excursion_truncates_exit_bar_and_tracks_strictly_later_recovery(self):
        r=excursions([0,20000,40000,60000],[100,90,125,120],entry=0,exit_at=10000,
            entry_price=100,natural_units=10,side=1,exit_price=90,cutoff=60000,stop_reason="SL")
        self.assertEqual(r["MFE_R"],0);self.assertEqual(r["MAE_R"],1)
        self.assertEqual(r["post_1R_at"],40000);self.assertEqual(r["post_2R_at"],40000)

    def test_short_excursion_uses_ask_direction(self):
        r=excursions([0,20000,40000],[100,95,105],entry=0,exit_at=40000,entry_price=100,
            natural_units=10,side=-1,exit_price=105,cutoff=40000,stop_reason="SL")
        self.assertEqual(r["MFE_R"],.5);self.assertEqual(r["MAE_R"],.5)

    def test_concentration_retains_losing_trades_and_denominator(self):
        rows=[dict(row(net_R=v,trade_key=str(i)),**classify(row(net_R=v))) for i,v in enumerate([5,3,-2])]
        self.assertEqual(concentration(rows)["without_top5"],-2)
        s=summarize(rows);self.assertEqual(sum(r["count"] for r in s["groups"]),3);self.assertEqual(s["net_R"],6)

    def test_london_clock_has_winter_and_summer_mapping(self):
        stamp=lambda s:int(datetime.fromisoformat(s).replace(tzinfo=timezone.utc).timestamp()*1000)
        self.assertEqual(london_hour(stamp("2023-01-03T15:00")),15)
        self.assertEqual(london_hour(stamp("2023-07-03T14:00")),15)

    def test_closed_atr_wilder_includes_last_closed_day(self):
        f=dict(h=np.arange(16.)+2,l=np.arange(16.),c=np.arange(16.)+1)
        a=closed_atr(f);self.assertTrue(np.isnan(a[12]));self.assertEqual(a[13],2);self.assertEqual(a[15],2)

    def test_future_prices_cannot_change_prior_registered_signal_prefix(self):
        from quant_core.market_data_store import BAR
        t=np.arange(0,45*24)*3600000;bars=np.zeros(len(t),dtype=BAR);bars["t"]=t
        for n,v in (("o",10000),("h",10030),("l",9970),("c",10000)):
            bars["b"+n]=v;bars["a"+n]=v+10
        cut=35*24*3600000
        before=recipes(bars,"EURUSD",0,cut,hourly=True)
        changed=bars.copy()
        for n in ("o","h","l","c"):changed["b"+n][t>=cut]+=1000
        after=recipes(changed,"EURUSD",0,cut,hourly=True)
        self.assertEqual(len(before),6)
        for a,b in zip(before,after):
            for k in ("at","side","stop"):np.testing.assert_array_equal(a[k],b[k])
