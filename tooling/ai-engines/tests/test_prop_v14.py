from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest.mock import patch
import unittest
import numpy as np
from test_sl_active_kernel import fixture
from prop_campaign_source import stamp
from prop_v14_source import csv_window
from prop_v14_paths import M1ScenarioQuotes,crossing,realize,build
from prop_v14_accounts import V14Account,trade_money,entry_charge,cost_bindings,monthly_starts
from prop_v14_review import audit_accounts
from independent_ledger_auditor import v14_parts,audit_v14_path
from quant_core.market_data_store import BAR
from quant_core.gap_aware_execution import GapAwarePathIndex,replay_gap_aware
from quant_core.ftmo_execution_and_calendar import SessionSchedule
from quant_core.prop_lifecycle_and_parity import simulate


class V14Tests(unittest.TestCase):
    def realized(self,values,mode="P0",*,short=False,gap=False,cutoff=None):
        b,m=fixture(values)
        if gap:b["t"][1:]+=60000
        m["deadline"]=b["t"][-1:]
        if short:m.update(side=np.array([-1]),entry_price=np.array([100000]),stop=np.array([110000]),natural=np.array([10.]))
        m["asset"]="XAUUSD"
        ix=GapAwarePathIndex(b,asset="XAUUSD",schedule=SessionSchedule([]))
        r=replay_gap_aware(ix,m,mode)
        reader=M1ScenarioQuotes(b,"OPEN_LOW_HIGH_CLOSE",int(b["t"][0]),cutoff or int(b["t"][-1])+60000)
        t=realize(m,r,0,reader,ix,"XAUUSD|F3:test|DAY|"+mode,mode)
        return b,m,t,reader

    def test_csv_seek_has_exact_lower_bound_and_excludes_high(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"raw.csv"
            p.write_text("DateTime,Bid,Ask,Volume\n"+"".join(f"{i:07},1,2,1\n" for i in range(5000)))
            for lo,hi in ((0,1),(101,1000),(4090,4093),(4999,5001)):
                _,r=csv_window(p,f"{lo:07}".encode(),f"{hi:07}".encode())
                self.assertEqual([int(x[0]) for x in r],list(range(lo,min(hi,5000))))

    def test_split_date_seek_compares_time_inside_same_day(self):
        with TemporaryDirectory() as d:
            p=Path(d)/"raw.csv";p.write_text("Date,Time,Open\n2020.01.01,10:00:00,1\n2020.01.01,10:01:00,2\n")
            h,r=csv_window(p,b"2020.01.01 10:01:00",b"2020.01.01 10:02:00")
            self.assertEqual(r,[["2020.01.01","10:01:00","2"]])

    def test_opening_gap_long_fills_open_not_interpolated_stop(self):
        b,m,t,r=self.realized([(100,101,99,100),(87,91,85,88),(88,89,87,88)],gap=True)
        self.assertEqual((t["exit_msc"],t["exit_price_units"]),(int(b["t"][1]),87000))
        self.assertTrue(t["source_uncertain"])

    def test_opening_gap_short_uses_actual_ask(self):
        b,m,t,r=self.realized([(100,101,99,100),(115,118,112,116),(116,117,115,116)],short=True,gap=True)
        self.assertEqual(t["exit_price_units"],115100)

    def test_continuous_stop_crossing_is_inside_minute(self):
        b,m,t,r=self.realized([(100,102,80,100),(100,101,99,100)])
        self.assertEqual(t["exit_price_units"],90000)
        self.assertTrue(int(b["t"][0])<t["exit_msc"]<int(b["t"][0])+20000)

    def test_endpoint_high_low_is_not_consumed(self):
        b,m,t,r=self.realized([(100,101,99,100),(102,180,50,120)])
        self.assertEqual(t["reason"],"HORIZON")
        self.assertEqual(t["exit_price_units"],102000)

    def test_true_sample_boundary_remains_open(self):
        b,_=fixture([(100,101,99,100)]*3)
        _,_,t,r=self.realized([(100,101,99,100)]*3,cutoff=int(b["t"][1]))
        self.assertEqual(t["reason"],"RIGHT_CENSORED")
        self.assertEqual(t["exit_msc"],r.cutoff)

    def test_P1_arms_only_on_next_bar(self):
        b,m,t,r=self.realized([(100,120,99,118),(118,119,101,102),(102,103,101,102)],"P1")
        self.assertEqual(t["activation_time"],int(b["t"][1]))
        self.assertEqual(t["reason"],"PROTECT")
        self.assertGreaterEqual(t["exit_msc"],t["activation_time"])

    def test_independent_path_oracle_detects_exit_tampering(self):
        b,m,t,r=self.realized([(100,102,80,100),(100,101,99,100)])
        events={"2023-03-06":dict(day="2023-03-06",flat_utc="10:01")}
        self.assertTrue(audit_v14_path(t,b,events,r.cutoff)["passed"])
        t["exit_price_units"]+=1
        self.assertIn("FIRST_PASSAGE",audit_v14_path(t,b,events,r.cutoff)["errors"])

    def test_protection_price_is_independently_recomputed(self):
        b,m,t,r=self.realized([(100,120,99,118),(118,119,101,102),(102,103,101,102)],"P1")
        events={"2023-03-06":dict(day="2023-03-06",flat_utc="10:02")}
        out=audit_v14_path(t,b,events,r.cutoff)
        self.assertTrue(out["passed"],out)

    def test_price_reader_fence_and_cache_invalidation(self):
        b,m,t,r=self.realized([(100,101,99,100)]*3)
        q=r.hour(int(b["t"][0])//3600000*3600000)
        r.add(int(b["t"][0])+1000,100000,100100)
        self.assertEqual(len(r.hour(int(b["t"][0])//3600000*3600000)),len(q)+1)
        with self.assertRaises(ValueError):r.add(r.cutoff,1,2)
        with self.assertRaises(ValueError):r.hour(r.cutoff+3600000)

    def test_actual_lot_decimal_costs_and_directional_swap(self):
        for asset,p0,px,stop in (("XAUUSD",1900000,1905000,1890000),("EURUSD",110000,110100,109000)):
            for side in ("BUY","SELL"):
                t=dict(asset=asset,side=side,entry_price_units=p0,exit_price_units=px,stop_units=stop,
                    entry_msc=stamp("2023-03-08T21:00"),exit_msc=stamp("2023-03-08T23:00"),reason="HORIZON")
                for q in (1,3,17):
                    for model in ("SYM_FLAT","ASYM_FLAT"):
                        actual=trade_money(t,q,model,150);own=v14_parts(t,q,model)
                        self.assertAlmostEqual(actual["net_usd"],own["net"]/1000)
                        self.assertAlmostEqual(entry_charge(t,p0,q),-own["entry_charge"])

    def test_limit_tp_removes_only_exit_slippage_in_asymmetric_scenario(self):
        t=dict(asset="XAUUSD",side="BUY",entry_price_units=1900000,exit_price_units=1920000,
            entry_msc=stamp("2023-03-06T10:00"),exit_msc=stamp("2023-03-06T11:00"),reason="TP")
        self.assertEqual(trade_money(t,3,"SYM_FLAT",150)["slippage_usd"],1.2)
        self.assertEqual(trade_money(t,3,"ASYM_FLAT",150)["slippage_usd"],.6)

    def test_bindings_restore_legacy_costs_and_progress_writer(self):
        import prop_portfolio_accounts as old
        import prop_v6_replay as replay
        fee,event=old.entry_exit_fee,replay.event
        with cost_bindings():
            self.assertIs(old.entry_exit_fee,entry_charge)
            self.assertIsNot(replay.event,event)
        self.assertIs(old.entry_exit_fee,fee);self.assertIs(replay.event,event)

    def test_105_monthly_starts_excludes_partial_october(self):
        values=monthly_starts(stamp("2018-01-01"),stamp("2026-10-14"))
        self.assertEqual(len(values),105)
        self.assertEqual(values[-1],stamp("2026-09-01"))

    def test_equality_touch_is_a_breach(self):
        a=V14Account(0,10000,"SYM_FLAT",rolling=True)
        a.check(1,-2500000)
        self.assertTrue(a.breach["daily"])

    def test_reference_book_skips_stop_larger_than_risk_at_minimum_lot(self):
        t=dict(asset="XAUUSD",entry_price_units=2000000,stop_units=1800000)
        a=V14Account(0,10000,"SYM_FLAT",rolling=False)
        a.action("entry",1,0,[t],None)
        self.assertFalse(a.accepted)
        self.assertEqual(a.rejected["LOT_GRID_MIN_MAX"],1)

    def test_small_account_replay_and_independent_cash_equity_oracle(self):
        b,m=fixture([(100,101,99,100),(100,104,99,103),(103,105,102,104)])
        m["asset"]="XAUUSD"
        ix=GapAwarePathIndex(b,asset="XAUUSD",schedule=SessionSchedule([]))
        m["_index"]=ix
        trades,readers,missing=build({"XAUUSD|F3:test|DAY|P0":m},"OPEN_LOW_HIGH_CLOSE",{"XAUUSD":b,"EURUSD":b})
        first,end=int(b["t"][0]),int(b["t"][-1])+60000
        cal=SimpleNamespace(events={})
        a=V14Account(first,end,"SYM_FLAT",rolling=True,standalone=True)
        with cost_bindings():rows=simulate(trades,readers,[a],first,end,cal)
        result=audit_accounts(rows,trades,readers,cal,first,end)
        self.assertEqual(result[0]["entries"],1)
        self.assertEqual(result[0]["exits"],1)
        rows[0]["balance_usd"]+=.01
        with self.assertRaisesRegex(ValueError,"terminal"):audit_accounts(rows,trades,readers,cal,first,end)

    def test_two_phase_resets_and_funded_harvest_reconcile(self):
        dates=["2023-03-06","2023-03-07","2023-03-08","2023-03-09",
            "2023-03-10","2023-03-13","2023-03-14","2023-03-15",
            "2023-03-16","2023-04-03"]
        trades=[];records=[]
        for day in dates:
            at=stamp(day+"T09:00");exit_at=at+3600000
            records.extend([(at,2000000),(exit_at,2800000)])
            trades.append(dict(asset="XAUUSD",side="BUY",role="CORE",decision_msc=at,
                entry_msc=at,exit_msc=exit_at,entry_price_units=2000000,exit_price_units=2800000,
                stop_units=1900000,deadline_msc=exit_at,reason="HORIZON",entry_quote_index=0,exit_quote_index=0))
        b=np.zeros(len(records),dtype=BAR)
        for j,(at,px) in enumerate(records):
            b["t"][j]=at
            for n in "ohlc":b["b"+n][j]=px;b["a"+n][j]=px+100
        first,end=stamp(dates[0]),stamp("2023-04-05")
        readers={a:M1ScenarioQuotes(b,"OPEN_LOW_HIGH_CLOSE",first,end) for a in ("XAUUSD","EURUSD")}
        # BUY entries use Ask, matching the true paired source quote.
        for t in trades:
            t["entry_price_units"]+=100
            t["stop_units"]+=100
        a=V14Account(first,end,"ASYM_FLAT",rolling=True)
        cal=SimpleNamespace(events={})
        with cost_bindings():rows=simulate(trades,readers,[a],first,end,cal)
        self.assertEqual(len(rows[0]["phase_passes"]),2)
        self.assertGreater(len(rows[0]["payouts"]),0)
        result=audit_accounts(rows,trades,readers,cal,first,end)
        self.assertEqual(result[0]["passes"],2)
