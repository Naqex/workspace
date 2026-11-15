from pathlib import Path
import unittest
import numpy as np
import independent_ledger_auditor as oracle
from prop_v15_evidence import classify_bridge,duration_group
from prop_v15_accounts import V15Account,exact_quantity,execution_bindings
from prop_v15_paths import insert_excursions,patch_plan
from quant_core.market_data_store import BAR


class V15BridgeTests(unittest.TestCase):
    def classify(self,side=1,level=90,before=100,after=101,minutes=2,sigma=1,adjacent=1,envelope=None):
        args=(side,level,before,after,minutes,sigma,adjacent,envelope or {})
        got=classify_bridge(*args,first=60,end=180)
        check=oracle.bridge_screen(*args,first=60,end=180)
        self.assertEqual(got["status"],check["status"])
        self.assertEqual(got["signed_distances"],check["signed_distances"])
        return got

    def test_three_sigma_is_a_model_with_nonzero_tail_not_a_certificate(self):
        r=self.classify()
        self.assertEqual(r["status"],"MODEL_LOW_RISK")
        self.assertGreater(r["model_hit_probability"],0)
        self.assertFalse(r["market_certificate"])
        self.assertFalse(r["deterministic_bound"])

    def test_absolute_distance_cannot_hide_an_endpoint_beyond_stop(self):
        r=self.classify(before=1000,after=80)
        self.assertEqual(r["status"],"ENDPOINT_TOUCH_OR_BEYOND_STOP")
        self.assertLess(r["minimum_distance"],0)

    def test_short_uses_ask_upper_extreme_not_bid_low(self):
        env=dict(available=True,complete_export_assumption=True,derived_from_gappy_M1=False,
            origin="PROVIDER_NATIVE_HTF",first=0,end=240,bid_low=80,ask_high=111)
        r=self.classify(side=-1,level=110,envelope=env)
        self.assertFalse(r["conditional_source_exclusion"])
        env["ask_high"]=109
        self.assertTrue(self.classify(side=-1,level=110,envelope=env)["conditional_source_exclusion"])

    def test_gappy_M1_aggregation_is_never_new_envelope_evidence(self):
        env=dict(available=True,complete_export_assumption=True,derived_from_gappy_M1=True,
            origin="PROVIDER_NATIVE_HTF",first=0,end=240,bid_low=95,ask_high=105)
        self.assertFalse(self.classify(envelope=env)["conditional_source_exclusion"])

    def test_native_envelope_requires_full_interval_and_strict_stop_exclusion(self):
        env=dict(available=True,complete_export_assumption=True,derived_from_gappy_M1=False,
            origin="RECORDED_NATIVE_TICK_ENVELOPE",first=0,end=240,bid_low=90)
        self.assertFalse(self.classify(envelope=env)["conditional_source_exclusion"])
        env["bid_low"]=91
        self.assertTrue(self.classify(envelope=env)["conditional_source_exclusion"])
        env["end"]=179
        self.assertFalse(self.classify(envelope=env)["conditional_source_exclusion"])

    def test_zero_or_unknown_volatility_does_not_certify_a_flat_feed(self):
        self.assertEqual(self.classify(sigma=0)["status"],"AMBIGUOUS")
        self.assertEqual(self.classify(sigma=None)["status"],"AMBIGUOUS")

    def test_bridge_probability_retains_log_for_numerical_underflow(self):
        r=self.classify(before=10000,after=10000)
        self.assertLess(r["model_log_hit_probability"],-745)
        self.assertGreater(r["model_hit_probability"],0)

    def test_duration_auditor_counts_losers_in_omitted_group(self):
        def trade(hours,gap,pnl):
            return dict(entry_msc=0,exit_msc=hours*3600000,source_uncertain=gap,
                reason="SL" if pnl<0 else "HORIZON",reference={"SYM":{"net_R":pnl}})
        rows=[trade(1,False,-1),trade(10,False,2),trade(24,True,4),trade(30,True,-1)]
        claimed={label:duration_group([t for t in rows if t["source_uncertain"]==flag])
            for label,flag in (("NO_UNKNOWN_GAP",False),("UNKNOWN_GAP",True))}
        r=oracle.audit_duration_censorship(rows,claimed)
        self.assertEqual(r["groups"]["UNKNOWN_GAP"]["losses"],1)
        self.assertFalse(r["causal_proof"])
        claimed["UNKNOWN_GAP"]["median_hours"]=99
        with self.assertRaises(ValueError):oracle.audit_duration_censorship(rows,claimed)


class V15RiskAndPathTests(unittest.TestCase):
    def account(self,**kwargs):
        return V15Account(0,10000,"SYM_FLAT",rolling=True,**kwargs)

    def test_registered_phase_schedule_and_drawdown_throttles(self):
        a=self.account(factor=2.5)
        for phase,risk in ((1,500),(2,437.5),(3,312.5)):
            a.phase=phase
            self.assertEqual(a.risk_request(50000000,"CORE",1),risk)
            self.assertEqual(a.risk_request(47500000,"CORE",1),150)
            self.assertEqual(a.risk_request(46500000,"CORE",1),75)
        with self.assertRaises(ValueError):self.account(factor=4)

    def test_cushion_needs_realized_profit_and_disarms_at_initial_balance(self):
        a=self.account(factor=1.5,cushion=True)
        a.observe_policy(1,52000000)
        self.assertEqual(a.risk_request(52000000,"CORE",1),300)
        a.balance=51500000;a.observe_policy(2,51500000)
        self.assertEqual(a.risk_request(51500000,"CORE",1),550)
        a.balance=50700000;a.observe_policy(3,50700000)
        self.assertEqual(a.risk_request(50700000,"CORE",1),440)
        self.assertEqual(a.risk_request(49900000,"CORE",1),300)
        a.balance=50000000;a.observe_policy(4,50000000)
        self.assertFalse(a.cushion_armed)

    def test_cushion_is_reset_at_phase_change(self):
        a=self.account(cushion=True);a.balance=51600000;a.observe_policy(1,51600000)
        a.phase=2;a.balance=50000000;a.observe_policy(2,50000000)
        self.assertFalse(a.cushion_armed)
        self.assertEqual(a.risk_request(52000000,"CORE",1),175)

    def test_fractional_budget_lot_floor_and_binding_restore(self):
        import prop_v5_account as v5
        t=dict(asset="XAUUSD",entry_price_units=2000000,stop_units=1991000)
        self.assertEqual(exact_quantity(t,218.75),24)
        old=v5.quantity_steps
        with execution_bindings():self.assertIs(v5.quantity_steps,exact_quantity)
        self.assertIs(v5.quantity_steps,old)
        with self.assertRaises(ValueError):exact_quantity(t,.1)

    def test_shared_opposite_side_excursion_preserves_every_observed_bar(self):
        first=1514764800000
        bars=np.zeros(2,dtype=BAR);bars["t"]=[first,first+180000]
        for n in "ohlc":bars["b"+n]=100000;bars["a"+n]=100338
        patch=dict(asset="XAUUSD",at=first+60000,targets=[
            dict(side=1,level=90000),dict(side=-1,level=110000)])
        actual,count=insert_excursions(bars,[patch],"XAUUSD",first+240000)
        self.assertEqual(count,1)
        self.assertTrue(np.array_equal(actual[[0,2]],bars))
        self.assertLess(actual["bl"][1],90000)
        self.assertGreater(actual["ah"][1],110000)
        self.assertTrue(np.all(actual["ao"]-actual["bo"]==338))
        patch["at"]=first
        with self.assertRaises(ValueError):insert_excursions(bars,[patch],"XAUUSD",first+240000)

    def test_primary_no_patch_keeps_model_risk_distinct_from_certification(self):
        row=dict(asset="XAUUSD",id="frozen",entry=1,exit=3,side=1,level=90,before=100,
            after=100,source_uncertain=True,first_unknown=2,screen=dict(status="MODEL_LOW_RISK"))
        self.assertEqual(patch_plan([row],"PRIMARY"),[])
        self.assertEqual(len(patch_plan([row],"ALL_UNCERTIFIED")),1)

    def test_policy_oracle_independently_matches_fractional_risk_and_cushion(self):
        a=self.account(factor=1.25,cushion=True)
        expected=dict(closed=[],accepted=[],standalone_funded=False,rolling=True,start_msc=0,
            policy="V15_DD_CUSHION",V15_factor=1.25,cushion=True)
        o=oracle.V15LedgerOracle(expected,[])
        for cash,equity in ((50000000,52000000),(51500010,51500010),(50710010,50710010),
                            (50000000,50000000),(47000000,47000000),(46500000,46500000)):
            a.balance=cash;a.observe_policy(1,equity)
            o.cash=cash;o.observe(1)
            self.assertEqual(a.risk_request(equity,"CORE",1),o.requested_risk(equity))

    def test_small_replay_and_separate_ledger_cover_new_risk_policy(self):
        from test_prop_v14 import V14Tests
        from types import SimpleNamespace
        from prop_v14_paths import build
        from quant_core.prop_lifecycle_and_parity import simulate,bindings
        import prop_v14_review as review
        b,m,_,_=V14Tests().realized([(100,101,99,100),(100,104,99,103),(103,105,102,104)])
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        m["_index"]=GapAwarePathIndex(b,asset="XAUUSD",schedule=SessionSchedule([]))
        trades,readers,missing=build({"XAUUSD|F3:test|DAY|P0":m},"OPEN_LOW_HIGH_CLOSE",
            {"XAUUSD":b,"EURUSD":b})
        first,end=int(b["t"][0]),int(b["t"][-1])+60000;cal=SimpleNamespace(events={})
        a=V15Account(first,end,"SYM_FLAT",rolling=True,factor=1.25,cushion=True)
        with execution_bindings():rows=simulate(trades,readers,[a],first,end,cal)
        with bindings(review,V14LedgerOracle=oracle.V15LedgerOracle):
            result=review.audit_accounts(rows,trades,readers,cal,first,end)
        self.assertEqual((result[0]["entries"],result[0]["exits"]),(1,1))

