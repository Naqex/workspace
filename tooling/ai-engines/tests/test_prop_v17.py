from types import SimpleNamespace
import unittest
import numpy as np
from prop_campaign_source import stamp
from prop_v17_accounts import V17Account,bucket,bucket_cap,execution_bindings
from prop_v17_scan import session_measurement
import independent_ledger_auditor as oracle
from prop_v16_paths import CausalFlatSchedule

DAY=86400000


def trade(identity="core",*,swing=False):
    at=stamp("2018-01-02T10:00")
    return dict(id=identity,asset="XAUUSD",entry_msc=at,deadline_msc=at+(DAY if swing else 3600000),
        entry_price_units=100000,stop_units=90000)


def expected(tiers):
    return dict(closed=[],accepted=[],standalone_funded=False,rolling=True,start_msc=0,
        policy="V17_TIER_BUCKET_DAILY_RESERVE",V15_factor=1.5,cushion=True,tiers=tiers,
        total_stop_cap_usd=1000,swing_stop_cap_usd=400,intraday_reserved_stop_usd=600,
        daily_reserved_loss_usd=1200)


class V17PolicyTests(unittest.TestCase):
    def test_bucket_uses_deadline_not_48H_name_or_realized_profit(self):
        t=trade("XAUUSD|frozen|48H|P0")
        self.assertEqual(bucket(t),"INTRADAY")
        t["deadline_msc"]+=DAY
        self.assertEqual(bucket(t),"SWING")

    def test_swing_cannot_spend_reserved_intraday_capacity(self):
        tape=[trade(swing=True),trade("support")]
        self.assertEqual(bucket_cap(tape,{},0),400000)
        self.assertEqual(bucket_cap(tape,{1:(70,150)},0),1000000)
        # 700USD already borrowed intraday leaves only300USD, not another400USD.
        self.assertGreater(700000+400000,bucket_cap(tape,{1:(70,150)},0))

    def test_intraday_can_borrow_unused_swing_but_keeps_total_cap(self):
        tape=[trade(),trade("support",swing=True)]
        self.assertEqual(bucket_cap(tape,{},0),1000000)
        self.assertLessEqual(40*10000+600000,bucket_cap(tape,{1:(40,150)},0))
        self.assertGreater(40*10000+600001,bucket_cap(tape,{1:(40,150)},0))

    def test_tier_rounding_cushion_and_equity_throttle_match_separate_oracle(self):
        tiers={"core":1.,"support":.6};tape=[trade(),trade("support")]
        a=V17Account(0,DAY,"SYM_FLAT",rolling=True,tiers=tiers)
        o=oracle.V17LedgerOracle(expected(tiers),tape)
        a._tape=tape
        for i in (0,1):
            a._request=i;o.target=i
            for cash,equity in ((50000000,52000000),(51500010,51500010),
                    (50710010,50710010),(50000000,50000000),(47000000,47000000),(46500000,46500000)):
                a.balance=cash;a.observe_policy(1,equity)
                o.cash=cash;o.observe(1)
                self.assertEqual(a.risk_request(equity,"CORE",1),o.requested_risk(equity))
        a._request=1
        self.assertEqual(a.risk_request(46500000,"CORE",1),45)

    def test_bucket_and_daily_floor_match_independent_oracle(self):
        tiers={"core":1.,"support":.6};tape=[trade(swing=True),trade("support")]
        a=V17Account(0,DAY,"SYM_FLAT",rolling=True,tiers=tiers)
        o=oracle.V17LedgerOracle(expected(tiers),tape)
        a._tape=tape;a.active={1:(30,150)};o.open={1:30}
        for i in (0,1):
            a._request=i;o.target=i
            for anchor in (50000000,51000000,46500000):
                a.anchor=anchor;o.anchor=anchor
                self.assertEqual((a.open_cap_milli,a.internal_floor_milli),o.policy_limits())

    def test_unregistered_tier_and_relaxed_daily_contract_are_rejected(self):
        with self.assertRaises(ValueError):V17Account(0,DAY,"SYM_FLAT",rolling=True,tiers={"bad":.7})
        e=expected({"core":1.});e["daily_reserved_loss_usd"]=1250
        with self.assertRaises(ValueError):oracle.V17LedgerOracle(e,[trade()])

    def test_entry_clock_has_no_future_gap_quality_filter(self):
        at=np.array([stamp("2022-01-03T06:00"),stamp("2022-01-03T08:00")])
        fields=dict(at=at,entry_at=at,side=np.ones(2),entry_price=np.ones(2),stop=np.zeros(2),
            natural=np.ones(2),friction=np.zeros(2),ratio=np.zeros(2),years=np.array([2022,2022]),
            deadline=at+DAY,admitted=np.ones(2,dtype=bool))
        archive={"0:"+k:v for k,v in fields.items()}
        row=dict(source_cell=0,asset="XAUUSD",recipe="frozen",family="F1")
        m,skipped=session_measurement(archive,row,CausalFlatSchedule([]))
        self.assertEqual((len(m["at"]),skipped),(1,1))
        self.assertEqual(int(m["at"][0]),int(at[1]))
        self.assertTrue(m["admitted"][0])

    def test_daily_reservation_rejects_fourth_loss_in_real_replay_and_audit(self):
        from test_sl_active_kernel import fixture
        from prop_v14_paths import build
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        from quant_core.prop_lifecycle_and_parity import simulate,bindings
        import prop_v14_review as review
        b,_=fixture([(100,100,100,100),(90,90,89,89)]*4)
        at=b["t"][::2];p=b["ao"][::2].astype("int64");stop=np.full(4,90000,dtype="int64")
        identity="XAUUSD|F3:test|DAY|P0"
        m=dict(at=at,entry_at=at,side=np.ones(4,dtype="int8"),entry_price=p,stop=stop,
            natural=(p-stop)/1000,deadline=b["t"][1::2],admitted=np.ones(4,dtype=bool),asset="XAUUSD",
            _index=GapAwarePathIndex(b,asset="XAUUSD",schedule=SessionSchedule([])))
        trades,readers,missing=build({identity:m},"OPEN_LOW_HIGH_CLOSE",{"XAUUSD":b,"EURUSD":b})
        self.assertEqual(missing,[])
        first,end=int(b["t"][0]),int(b["t"][-1])+60000;cal=SimpleNamespace(events={})
        a=V17Account(first,end,"SYM_FLAT",rolling=True,tiers={identity:1.})
        with execution_bindings():rows=simulate(trades,readers,[a],first,end,cal)
        self.assertEqual(rows[0]["entries"],3)
        self.assertEqual(rows[0]["rejections"]["V17_STATIC_OR_DAILY_RESERVE"],1)
        with bindings(review,V14LedgerOracle=oracle.V17LedgerOracle):
            checked=review.audit_accounts(rows,trades,readers,cal,first,end)
        self.assertEqual(checked[0]["entries"],3)

    def test_US500_scalar_audit_uses_contract_one_and_001_price_grid(self):
        from test_sl_active_kernel import fixture
        from prop_v14_paths import build
        from quant_core.gap_aware_execution import GapAwarePathIndex
        from quant_core.ftmo_execution_and_calendar import SessionSchedule
        b,m=fixture([(100,101,99,100),(100,118,99,115),(115,118,110,113)])
        m.update(asset="US500",deadline=b["t"][-1:],
            _index=GapAwarePathIndex(b,asset="US500",schedule=SessionSchedule([])))
        for mode in ("P0","P1"):
            trades,_,missing=build({"US500|F3:test|DAY|"+mode:m},"OPEN_LOW_HIGH_CLOSE",{"US500":b})
            self.assertEqual(missing,[])
            t=trades[0];t["scale"]=1000
            r=oracle.audit_v14_path(t,b,{},int(b["t"][-1])+60000,scheduled_override=t["deadline_msc"])
            self.assertTrue(r["passed"],r)


if __name__=="__main__":unittest.main()
