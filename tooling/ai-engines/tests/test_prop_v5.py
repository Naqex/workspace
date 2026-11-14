from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from prop_v5_account import ColdState,V5Account
from prop_v5_data import timestamp_file
from prop_v5_replay import TAGGED
from prop_campaign_source import stamp,DAY,HOUR


def trade(at,asset="XAUUSD"):
    return dict(asset=asset,role="CORE" if asset=="XAUUSD" else "SATELLITE",side="BUY",
                decision_msc=at-1,entry_msc=at,entry_price_units=2000000 if asset=="XAUUSD" else 110000,
                stop_units=1990000 if asset=="XAUUSD" else 109000,
                deadline_msc=at+48*HOUR,exit_msc=at+HOUR,
                exit_price_units=1990000 if asset=="XAUUSD" else 109000,d1_gate=True)


def quote(at,source=0,gold=2000000,eur=110000):
    a=np.zeros(1,dtype=TAGGED);a["t"]=at;a["src"]=source
    a["b0"]=gold;a["a0"]=gold+100;a["b1"]=eur;a["a1"]=eur+10
    return a[0]


class V5Tests(unittest.TestCase):
    def account(self,**kw):
        return V5Account(stamp("2022-01-01"),stamp("2024-01-01"),"ASYM_FLAT",rolling=True,**kw)

    def test_cold_streak_boundary_and_recovery(self):
        s=ColdState();s.observe(-7.99);self.assertEqual(s.factor,1)
        s.observe(-.01);self.assertEqual(s.factor,.5)
        s.observe(-2);s.observe(3.99);self.assertEqual(s.factor,.5)
        s.observe(.01);self.assertEqual(s.factor,1)

    def test_sleeve_controls_are_independent(self):
        a=self.account(mechanism="D2");a.cold["EURUSD"].observe(-8)
        a.current_asset="XAUUSD";self.assertEqual(a.risk_request(50000000,"CORE",1),200)
        a.current_asset="EURUSD";self.assertEqual(a.risk_request(50000000,"SATELLITE",1),100)

    def test_ratchet_does_not_arm_before_threshold(self):
        a=self.account();a.observe_policy(a.start,53499999);self.assertFalse(a.ratchet)
        a.observe_policy(a.start,53500000);self.assertTrue(a.ratchet)
        self.assertEqual(a.risk_request(53500000,"CORE",1),125)

    def test_protected_floor_latches_reduction_and_liquidation(self):
        a=self.account();a.ratchet=True;a.active={0:(10,200)}
        a.observe_policy(a.start,52500000)
        self.assertTrue(a.floor_touched);self.assertIn(0,a.pending)
        self.assertEqual(a.risk_request(52500000,"CORE",1),90)

    def test_phase2_ratchet_has_no_invented_phase1_floor(self):
        a=self.account();a.phase=2;a.observe_policy(a.start,51750000)
        self.assertEqual(a.risk_request(51750000,"CORE",1),100)
        a.observe_policy(a.start,50000000);self.assertFalse(a.floor_touched)

    def test_harvest_freeze_requires_closed_profit_and_due_proximity(self):
        a=self.account();a.phase=3;a.funded_first=a.start;a.balance=50500000
        a.observe_policy(a.start+12*DAY-1,52000000);self.assertEqual(a.harvest_state,"NORMAL")
        a.observe_policy(a.start+12*DAY,52000000);self.assertEqual(a.harvest_state,"PRE_PAYOUT_FREEZE")

    def test_floating_profit_alone_never_arms_harvester(self):
        a=self.account();a.phase=3;a.funded_first=a.start
        a.observe_policy(a.start+13*DAY,51500000)
        self.assertEqual(a.harvest_state,"NORMAL")

    def test_profit_lock_is_immediate_and_requests_flat(self):
        a=self.account();a.phase=3;a.funded_first=a.start;a.balance=51000000
        a.active={0:(1,125)};a.observe_policy(a.start+DAY,51000000)
        self.assertEqual(a.harvest_state,"PROFIT_LOCK_IDLE");self.assertIn(0,a.pending)

    def test_same_timestamp_and_other_asset_quotes_cannot_fill_forced_order(self):
        a=self.account();at=a.start+8*HOUR;t=trade(at);a._trades=[t]
        a.action("entry",at,0,[t],quote(at));a.request_flat(at,"TEST")
        rows=np.array([quote(at,0),quote(at+1,1)],dtype=TAGGED)
        a.segment(rows,[t],{})
        self.assertFalse(a.closed);self.assertIn(0,a.pending)
        a.segment(np.array([quote(at+2,0)],dtype=TAGGED),[t],{})
        self.assertEqual(len(a.closed),1);self.assertEqual(a.closed[0]["at"],at+2)

    def test_d1_uses_registered_gate_and_does_not_widen_stop(self):
        a=self.account(mechanism="D1");at=a.start+8*HOUR;t=trade(at,"EURUSD");t["d1_gate"]=False
        a.action("entry",at,0,[t],quote(at,1))
        self.assertFalse(a.accepted);self.assertEqual(a.rejected["D1_ASIA_RANGE_ATR"],1)
        self.assertEqual(t["stop_units"],109000)

    def test_full_profit_debit_and_unlock_after_reward(self):
        a=self.account();a.phase=3;a.funded_first=a.start;a.balance=51000000
        a.harvest_state="PROFIT_LOCK_IDLE";a.reward(a.start+14*DAY)
        self.assertEqual(a.balance,50000000);self.assertEqual(a.payouts[0]["trader_usd"],800)
        self.assertEqual(a.harvest_state,"NORMAL")

    def test_forced_close_costs_can_erase_harvest_profit_no_guarantee(self):
        a=self.account();a.phase=3;a.funded_first=a.start;a.balance=49999999
        a.harvest_state="PRE_PAYOUT_FREEZE";a.reward(a.start+14*DAY)
        self.assertFalse(a.payouts)

    def test_timestamp_export_rejects_any_price_column(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.csv";p.write_text("DateTime,Bid\n2025.01.02 07:00:00,1.2\n")
            with self.assertRaises(ValueError):timestamp_file(p)
            p.write_text("DateTime\n2025.01.02 07:00:00\n")
            self.assertEqual(len(timestamp_file(p)),1)

    def test_timestamp_export_date_fence(self):
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"x.csv";p.write_text("DateTime\n2024.12.31 23:00:00\n")
            with self.assertRaises(ValueError):timestamp_file(p)

    def test_shadow_d2_observes_only_at_original_exit(self):
        a=self.account(mechanism="D2");at=a.start+8*HOUR;t=trade(at);a._trades=[t]
        a.action("entry",at,0,[t],quote(at))
        self.assertEqual(a.cold["XAUUSD"].total,0)
        a.request_flat(at,"TEST")
        a.segment(np.array([quote(at+1,0)],dtype=TAGGED),[t],{})
        self.assertEqual(a.cold["XAUUSD"].total,0)
        a.action("exit",t["exit_msc"],0,[t],quote(t["exit_msc"],0))
        self.assertLess(a.cold["XAUUSD"].total,0)

    def test_reference_R_is_cash_weighted_not_sum_of_differently_sized_trade_R(self):
        a=V5Account(0,10**15,"ASYM_FLAT",fixed_risk=150,controller=False)
        a._trades=[]
        with patch("prop_cocore_v4.MeasuredAccount.dump",return_value={"net_R":5,"net_usd":375}):
            row=a.dump()
        self.assertEqual(row["net_R"],2.5)


if __name__=="__main__":unittest.main()
