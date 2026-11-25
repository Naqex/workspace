"""Unit & Safety Tests for Wave-2 Cycle 0 MT5 Real-Tick Runner, Reconciler, Profile Builder & Live Monitor."""

from __future__ import annotations

import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest

AI_ENGINES = Path(__file__).resolve().parents[1]
EXPORTS_DIR = AI_ENGINES / "exports"

for p in (AI_ENGINES, EXPORTS_DIR):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

import build_ftmo_profile as prof  # noqa: E402
import mt5_live_monitor as mon  # noqa: E402
import mt5_realtick_runner as runner  # noqa: E402
import mt5_vs_python_reconciler as recon  # noqa: E402
from quant_factory.data_store import assert_holdout_locked  # noqa: E402


SAMPLE_MT5_HTML = """<!DOCTYPE html>
<html><body>
<table>
<tr><td>Expert:</td><td>Naqex\\Naqex_WB_EXP080_USDJPY</td><td>Symbol:</td><td>USDJPY</td></tr>
<tr><td>Period:</td><td>M15 (2024.09.01 - 2024.12.31)</td><td>History Quality:</td><td>100%</td></tr>
<tr><td>Bars:</td><td>8 420</td><td>Ticks:</td><td>6 540 120</td></tr>
<tr><td>Initial Deposit:</td><td>10 000.00</td><td>Total Net Profit:</td><td>342.50</td></tr>
<tr><td>Gross Profit:</td><td>780.00</td><td>Gross Loss:</td><td>-437.50</td></tr>
<tr><td>Profit Factor:</td><td>1.78</td><td>Expected Payoff:</td><td>17.13</td></tr>
<tr><td>Recovery Factor:</td><td>2.45</td><td>Sharpe Ratio:</td><td>1.92</td></tr>
<tr><td>Balance Drawdown Maximal:</td><td>140.00 (1.38%)</td><td>Equity Drawdown Maximal:</td><td>165.00 (1.62%)</td></tr>
<tr><td>Total Trades:</td><td>20</td><td>Total Deals:</td><td>40</td></tr>
<tr><td>Profit Trades (% of total):</td><td>11 (55.00%)</td><td>Loss Trades (% of total):</td><td>9 (45.00%)</td></tr>
</table>
<table>
<tr><th>Time</th><th>Deal</th><th>Symbol</th><th>Type</th><th>Direction</th><th>Volume</th><th>Price</th><th>Order</th><th>Commission</th><th>Swap</th><th>Profit</th><th>Balance</th><th>Comment</th></tr>
<tr><td>2024.09.05 08:12:00</td><td>2</td><td>USDJPY</td><td>buy</td><td>in</td><td>0.10</td><td>143.500</td><td>2</td><td>-0.25</td><td>0.00</td><td>0.00</td><td>9999.75</td><td>Naqex_WB_EXP_BUY</td></tr>
<tr><td>2024.09.05 20:55:00</td><td>3</td><td>USDJPY</td><td>sell</td><td>out</td><td>0.10</td><td>144.200</td><td>3</td><td>-0.25</td><td>0.00</td><td>48.50</td><td>10048.00</td><td>HARD_FLAT_SWAP0</td></tr>
<tr><td>2024.09.12 10:05:00</td><td>4</td><td>USDJPY</td><td>sell</td><td>in</td><td>0.10</td><td>142.100</td><td>4</td><td>-0.25</td><td>0.00</td><td>0.00</td><td>10047.75</td><td>Naqex_WB_EXP_SELL</td></tr>
<tr><td>2024.09.12 13:20:00</td><td>5</td><td>USDJPY</td><td>buy</td><td>out</td><td>0.10</td><td>142.850</td><td>5</td><td>-0.25</td><td>0.00</td><td>-52.50</td><td>9995.00</td><td>[sl 142.850]</td></tr>
</table>
</body></html>
"""


class Wave2Mt5RealTickTests(unittest.TestCase):
    def test_forbidden_non_ftmo_paths_are_rejected_fail_closed(self):
        bad_term = Path(r"C:\Program Files\MetaTrader 5\terminal64.exe")
        bad_data = Path(r"C:\Users\MIIKEY\AppData\Roaming\MetaQuotes\Terminal\D0E8209F77C8CF37AD8BF550E51FF075")
        with self.assertRaises(ValueError):
            mon.assert_safe_terminal_path(bad_term)
        with self.assertRaises(ValueError):
            runner.assert_safe_portable_root(bad_term.parent)
        with self.assertRaises(ValueError):
            prof.assert_safe_mt5_data_dir(bad_data)

    def test_demo_account_guard_rejects_real_and_wrong_server(self):
        good = SimpleNamespace(
            login=1515343166, server="FTMO-Demo", trade_mode=0, currency="USD",
            balance=10000.0, equity=10010.0, profit=10.0, margin=0.0, margin_free=10010.0,
            leverage=100, trade_allowed=True, trade_expert=True,
        )
        res = mon.validate_demo_account(good, demo_trade_mode=0)
        self.assertEqual(res["trade_mode"], "ACCOUNT_TRADE_MODE_DEMO")
        self.assertEqual(res["login"], 1515343166)

        real_acc = SimpleNamespace(**{**good.__dict__, "trade_mode": 2})
        with self.assertRaises(RuntimeError):
            mon.validate_demo_account(real_acc, demo_trade_mode=0)

        exness_acc = SimpleNamespace(**{**good.__dict__, "server": "Exness-MT5Real9"})
        with self.assertRaises(RuntimeError):
            mon.validate_demo_account(exness_acc, demo_trade_mode=0)

    def test_tester_ini_contains_no_password_and_model4_real_ticks(self):
        ini = runner.render_tester_ini(
            expert_rel=r"Naqex\Naqex_WB_EXP080_USDJPY",
            set_filename="naqex_rt_E2.set",
            symbol="USDJPY",
            period="M15",
            from_date="2024.09.01",
            to_date="2024.12.31",
            report_stem="naqex_rt_E2_50ms",
            execution_mode_ms=150,
            model=4,
            leverage=30,
        )
        self.assertIn("Model=4", ini)
        self.assertIn("ExecutionMode=150", ini)
        self.assertIn("Leverage=1:30", ini)
        self.assertIn("KeepPrivate=0", ini)
        self.assertIn("ShutdownTerminal=1", ini)
        self.assertNotIn("Password=", ini)
        self.assertNotIn("Login=", ini)

    def test_html_report_parser_and_reconciler_holdout_guard(self):
        with tempfile.TemporaryDirectory() as td:
            htm = Path(td) / "sample_report.htm"
            htm.write_bytes(SAMPLE_MT5_HTML.encode("utf-16"))
            rep = recon.parse_mt5_html_report(htm)
            self.assertTrue(rep["ok"])
            self.assertEqual(rep["total_trades"], 20)
            self.assertAlmostEqual(rep["total_net_profit"], 342.50, places=2)
            self.assertAlmostEqual(rep["profit_factor"], 1.78, places=2)
            self.assertAlmostEqual(rep["equity_dd_pct"], 1.62, places=2)
            self.assertTrue(rep["swap_zero_ok"])
            self.assertAlmostEqual(rep["commission_total_usd"], -1.00, places=2)
            self.assertEqual(rep["sl_exits_count"], 1)
            self.assertEqual(rep["entry_days"], ["2024-09-05", "2024-09-12"])

            # Verify reconciler refuses Python comparison on Holdout >= 2025-01-01
            runs = {
                50: {"report": rep, "logs": {"clean": True, "issues": []}},
                250: {"report": {**rep, "total_net_profit": 310.0}, "logs": {"clean": True, "issues": []}},
            }
            rec = recon.reconcile_engine_runs(
                "E2_USDJPY_EXP80",
                runs,
                window_start_iso="2025-01-02",
                window_end_iso="2025-06-30",
            )
            self.assertFalse(rec["python_dev_reference"]["available"])
            self.assertIn("HOLDOUT_SEALED_SKIPPED", rec["python_dev_reference"]["reason"])
            self.assertAlmostEqual(rec["latency_drag_50_to_250ms_usd"], -32.50, places=2)
            self.assertEqual(rec["verdict"], "PASS")

    def test_build_ftmo_profile_generates_9_utf16_charts_with_algo_only(self):
        with tempfile.TemporaryDirectory() as td:
            data_dir = Path(td) / "ftmo_portable"
            res = prof.build_mt5_chart_profile(
                data_dir=data_dir,
                preset_profile="FTMO_FreeTrial_Demo",
                mt5_profile_name="Naqex_FreeTrial",
            )
            self.assertTrue(res["ok"])
            self.assertEqual(res["charts_count"], 9)
            pdir = Path(res["profile_dir"])
            self.assertTrue((pdir / "order.wnd").exists())
            chrs = sorted(pdir.glob("chart*.chr"))
            self.assertEqual(len(chrs), 9)

            # Check chart05 (US100.cash E4) has UTF-16 BOM, expertmode=1 (no DLL), MaxSpreadPoints=450
            c5_bytes = (pdir / "chart05.chr").read_bytes()
            self.assertTrue(c5_bytes.startswith(b"\xff\xfe"))
            c5 = c5_bytes.decode("utf-16")
            self.assertIn("symbol=US100.cash", c5)
            self.assertIn("path=Experts\\Naqex\\Naqex_WB_SESS_CONT_BRK40_US100.ex5", c5)
            self.assertIn("expertmode=1", c5)
            self.assertIn("InpGuardMaxSpreadPoints=450.00", c5)
            self.assertIn("InpDryRunLogOnly=false", c5)

    def test_live_monitor_snapshot_read_only_and_heartbeat_telemetry(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td) / "ftmo-demo-portable-1515343166"
            (root / "MQL5/Files").mkdir(parents=True)
            hb_path = root / "MQL5/Files/naqex_heartbeat.json"
            hb_path.write_text(
                json.dumps(
                    {
                        "utc_ts": 9_999_999_999,
                        "balance": 10000.0,
                        "equity": 10020.0,
                        "regime": "NORMAL",
                        "risk_mult": 1.0,
                        "kill_switch": False,
                        "orphan_no_sl": 0,
                    }
                ),
                encoding="utf-8",
            )

            class FakeMT5:
                ACCOUNT_TRADE_MODE_DEMO = 0

                def initialize(self, **kwargs):
                    return True

                def shutdown(self):
                    return None

                def last_error(self):
                    return (0, "OK")

                def account_info(self):
                    return SimpleNamespace(
                        login=1515343166, server="FTMO-Demo", trade_mode=0, currency="USD",
                        balance=10000.0, equity=10020.0, profit=20.0, margin=50.0, margin_free=9970.0,
                        leverage=100, trade_allowed=True, trade_expert=True,
                    )

                def terminal_info(self):
                    return SimpleNamespace(connected=True, trade_allowed=True, build=6230, data_path=str(root))

                def symbol_select(self, sym, enable):
                    return True

                def symbol_info(self, sym):
                    if sym == "US100.cash":
                        return SimpleNamespace(bid=25850.0, ask=25851.95, point=0.01, spread=195, digits=2)
                    return SimpleNamespace(bid=155.000, ask=155.006, point=0.001, spread=6, digits=3)

                def symbol_info_tick(self, sym):
                    si = self.symbol_info(sym)
                    return SimpleNamespace(bid=si.bid, ask=si.ask, time=1795450000)

                def positions_get(self):
                    return [
                        SimpleNamespace(
                            ticket=101, symbol="USDJPY", magic=20261123, type=0,
                            volume=0.10, price_open=155.0, sl=154.2, tp=0.0, profit=20.0, swap=0.0,
                        )
                    ]

            snap = mon.collect_snapshot(
                terminal_path=root / "terminal64.exe",
                symbols=("USDJPY", "US100.cash"),
                mt5_mod=FakeMT5(),
            )
            self.assertEqual(snap["order_send_count"], 0)
            self.assertEqual(snap["account"]["server"], "FTMO-Demo")
            self.assertEqual(snap["naqex_positions_count"], 1)
            self.assertEqual(snap["orphan_no_sl"], 0)
            self.assertAlmostEqual(snap["quotes"]["US100.cash"]["spread_pts"], 195.0, places=1)
            self.assertEqual(snap["heartbeat"]["status"], "OK")

    def test_holdout_lock_remains_untouched(self):
        self.assertEqual(len(assert_holdout_locked()), 64)

    def test_us_equity_half_day_swap0_and_dst_guards_baked_into_mq5(self):
        mqh = (EXPORTS_DIR / "Include/Naqex_PropGuard.mqh").read_text(encoding="utf-8")
        self.assertIn("IsUsEquityHalfDayNY", mqh)
        self.assertIn("IsUsDstUtc", mqh)
        self.assertIn("InpGuardDryRunLogOnly     = true;", mqh)

        for fname in ("Naqex_WB_SESS_CONT_BRK40_US100.mq5", "Naqex_WB_IDX_RS_US100_LEAD_1130.mq5"):
            src = (EXPORTS_DIR / fname).read_text(encoding="utf-8")
            self.assertIn("IsUsEquityHalfDayNY(ny)", src)
            self.assertIn("HARD_FLAT_US_HALF_DAY_SWAP0", src)
            self.assertIn("OVERNIGHT_FAILSAFE_SWAP0", src)
            self.assertIn("InpDryRunLogOnly     = true;", src)

    def test_realtick_matrix_summary_and_reconciliation_doc_hygiene(self):
        doc = Path(__file__).resolve().parents[3] / "planning/research/MT5-REALTICK-RECONCILIATION-20261124.md"
        self.assertTrue(doc.exists())
        txt = doc.read_text(encoding="utf-8")
        self.assertLess(doc.stat().st_size, 900 * 1024)
        self.assertNotIn("Password=", txt)
        self.assertNotRegex(txt, r"\$\d+")

        summary_path = Path(__file__).resolve().parents[3] / ".runtime/mt5-realtick-results/realtick_matrix_summary.json"
        if summary_path.exists():
            data = json.loads(summary_path.read_text(encoding="utf-8"))
            self.assertEqual(data["engines_run"], 8)
            for eid, item in data["reconciliation"].items():
                self.assertEqual(item["verdict"], "PASS", f"{eid} not PASS: {item['diagnostics']}")
                for lat_k, metrics in item["latency_curve"].items():
                    self.assertTrue(metrics["ok"], f"{eid} {lat_k} not ok")
                    self.assertTrue(metrics["swap_zero_ok"], f"{eid} {lat_k} swap != 0")
                    self.assertTrue(metrics["log_clean"], f"{eid} {lat_k} logs not clean")


if __name__ == "__main__":
    unittest.main()
