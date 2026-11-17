from pathlib import Path
from unittest.mock import patch
import ast
import json
import tempfile
import unittest
import ftmo_trial_runner as runner


class ObserverRunnerTests(unittest.TestCase):
    def reader(self,bundle):
        from ftmo_free_trial_adapter import FileBridge
        obj=object.__new__(FileBridge);obj.bundle=bundle;return obj

    def test_account_snapshot_is_sanitized_and_captures_unknown_sessions(self):
        b,p=runner.builtin_fixture();s=runner.snapshot(self.reader(b),p["from_msc"],replay=True)
        self.assertEqual(set(s["specs"]),set(runner.ASSETS))
        self.assertNotIn("login",s["account"])
        self.assertIsNone(s["specs"]["EURUSD"]["sessions_trade"])
        self.assertEqual(s["account"]["trade_mode"],0)

    def test_real_or_unrelated_account_does_not_become_an_ftmo_probe(self):
        for mode,server in ((2,"FTMO"),(0,"OTHER-BROKER")):
            b,p=runner.builtin_fixture();b["account"].update(trade_mode=mode,server=server,company=server)
            with self.assertRaises(runner.adapter.AdapterError):runner.snapshot(self.reader(b),p["from_msc"])

    def test_native_shadow_refuses_missing_session_export_before_any_paper_entry(self):
        b,p=runner.builtin_fixture()
        class Reader:
            def account(self):return b["account"]
            def spec(self,asset):return b["specs"][asset]
            def close(self):pass
        with tempfile.TemporaryDirectory() as d:
            root=Path(d);manifest=root/"manifest.json";manifest.write_text(json.dumps(p),encoding="utf-8")
            with patch.object(runner,"terminal_inventory",return_value=[dict(ExecutablePath="already-running.exe")]), \
                 patch.object(runner.adapter,"NativeMT5Reader",return_value=Reader()):
                with self.assertRaisesRegex(runner.adapter.AdapterError,"SESSION_EXPORT"):
                    runner.run("shadow-paper",root/"capture",manifest=manifest)
            self.assertFalse((root/"capture/shadow_paper_ledger.json").exists())
            self.assertTrue((root/"capture/TARGET_ACCOUNT_SPEC_SNAPSHOT.json").exists())

    def test_changed_lot_step_is_a_diff_not_a_silent_repair(self):
        b,p=runner.builtin_fixture();b["specs"]["XAUUSD"]["volume_step"]=.1
        s=runner.snapshot(self.reader(b),p["from_msc"],replay=True);diff=runner.parity(s)
        self.assertTrue(any(r["field"]=="volume_step" and r["status"]=="DIFFERENT" for r in diff["rows"]))
        self.assertFalse(diff["exact_session_parity"])

    def test_supplied_weekly_sessions_detect_an_early_close_before_registered_cutoff(self):
        b,p=runner.builtin_fixture();s=runner.snapshot(self.reader(b),p["from_msc"],replay=True)
        for asset in runner.adapter.ASSETS:
            s["specs"][asset].update(session_timezone="UTC",sessions_trade=[
                dict(weekday=1,from_server_seconds=0,to_server_seconds=22*3600)])
        self.assertTrue(runner.parity(s,p["holidays"])["exact_session_parity"])
        s["specs"]["XAUUSD"]["sessions_trade"][0]["to_server_seconds"]=19*3600
        diff=runner.parity(s,p["holidays"])
        self.assertFalse(diff["exact_session_parity"])
        self.assertTrue(any(r["asset"]=="XAUUSD" and r["field"]=="sessions_trade" and r["status"]=="DIFFERENT" for r in diff["rows"]))

    def test_session_timezone_dst_mapping_and_unknown_holiday_cannot_imply_parity(self):
        b,p=runner.builtin_fixture();s=runner.snapshot(self.reader(b),p["from_msc"],replay=True)
        # Prague in May is UTC+2: 20:30 UTC is22:30 server-local.
        for asset in runner.adapter.ASSETS:
            s["specs"][asset].update(session_timezone="Europe/Prague",sessions_trade=[
                dict(weekday=1,from_server_seconds=0,to_server_seconds=23*3600)])
        self.assertTrue(runner.parity(s,p["holidays"])["exact_session_parity"])
        s["specs"]["XAUUSD"]["sessions_trade"][0]["to_server_seconds"]=22*3600
        self.assertFalse(runner.parity(s,p["holidays"])["exact_session_parity"])
        self.assertFalse(runner.parity(s)["exact_session_parity"])

    def test_paced_replay_keeps_quotes_ledger_and_observed_excursions(self):
        import pyarrow.parquet as pq
        b,p=runner.builtin_fixture();waits=[]
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);recorder=runner.QuoteParquet(out/"quotes.parquet")
            result=runner.stream(b["events"],runner.ObserverPaper(p,p["from_msc"],p["to_msc"]),recorder,out,sleeper=waits.append)
            receipt=recorder.close();rows=pq.read_table(out/"quotes.parquet").to_pylist()
            self.assertEqual(receipt["rows"],4);self.assertEqual(len(rows),4)
            self.assertEqual(result["account"]["entries"],1);self.assertEqual(result["account"]["closed_trades"],1)
            self.assertEqual(result["broker_orders_sent"],0)
            self.assertEqual(sum(waits),3.)
            self.assertGreater(result["excursions"]["synthetic-demo"]["MFE_price"],0)
            self.assertLess(result["excursions"]["synthetic-demo"]["MAE_price"],-10)

    def test_replay_unknown_news_blocks_entry_and_does_not_fake_slippage(self):
        b,p=runner.builtin_fixture();p["news"]=dict(p["news"],coverage_complete=False)
        with tempfile.TemporaryDirectory() as d:
            out=Path(d);recorder=runner.QuoteParquet(out/"quotes.parquet")
            result=runner.stream(b["events"],runner.ObserverPaper(p,p["from_msc"],p["to_msc"]),recorder,out,sleeper=lambda x:None)
            recorder.close()
            self.assertEqual(result["account"]["entries"],0);self.assertFalse(result["slippage_measured"])

    def test_future_quote_and_mutated_event_order_fail_closed(self):
        with tempfile.TemporaryDirectory() as d:
            recorder=runner.QuoteParquet(Path(d)/"quotes.parquet")
            with self.assertRaisesRegex(ValueError,"future_quote"):
                recorder.accept(dict(kind="quote",asset="XAUUSD",bid=1.,ask=2.,time_msc=100,known_at_msc=99))
            recorder.close()

    def test_no_submission_api_and_module_namespace_resolves_existing_implementation(self):
        tree=ast.parse(Path(runner.__file__).read_text(encoding="utf-8"))
        self.assertFalse(any(isinstance(n,ast.Attribute) and n.attr in ("order_send","order_check","login") for n in ast.walk(tree)))
        self.assertFalse(runner.ALLOW_LIVE_ORDER_SEND)
        import tooling.ai_engines.ftmo_trial_runner as module
        self.assertEqual(Path(module.__file__).resolve(),Path(runner.__file__).resolve())

    def test_one_command_readonly_and_shadow_replay_leave_zero_orders(self):
        with tempfile.TemporaryDirectory() as d,patch.object(runner,"terminal_inventory",return_value=[]):
            for mode in ("read-only","shadow-paper"):
                out=Path(d)/mode
                runner.run(mode,out,speed=10000)
                report=json.loads((out/"report.json").read_text(encoding="utf-8"))
                self.assertEqual(report["source"],"TIMESTAMP_PACED_REPLAY")
                self.assertFalse(report["native_terminal_verified"])
                self.assertTrue((out/"quotes.parquet").exists())
                self.assertTrue((out/"TARGET_ACCOUNT_SPEC_SNAPSHOT.json").exists())


if __name__=="__main__":unittest.main()
