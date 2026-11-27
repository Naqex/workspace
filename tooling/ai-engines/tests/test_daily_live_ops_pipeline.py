"""Tests for OPS-4 Daily/Weekly End-to-End Live-Ops Pipeline & Objective Traffic-Light Decision Matrix.

Covers:
  1. Static safety, immutability, LF-only, `[ARCH-02]` zero bare asserts, zero MetaTrader5 imports,
     and `G12` zero FTMO-support-contact wording.
  2. Full `GREEN` end-to-end fixture (statement reconciler + TCA + parity forensics + blackbox guard
     block + live decay + postmortem + calendar TTL > 14d + feed health + fresh heartbeat +
     compliance + offline pre-checkout network + atomic SHA-256 JSON receipt + Telegram digest).
  3. `AMBER` fixtures (`THROTTLE_TO_0_5X_WATCH`):
       - Calendar TTL = 10d (`<= 14d` and `> 3d`)
       - Market `Regime Shift` (vol shift / `AMBER_WATCH_REDUCE_SIZE`, NO bot bug, NO SPRT reject)
       - Inactivity `>= 21d` (`< 27d`)
       - Elevated slippage/friction `1.5x-2.0x`
  4. `RED` fixtures (`HALT_BOT_ENABLE_DRYRUN_INVESTIGATE`):
       - (a) `BOT_BUG_GHOST_TRADE` -> immediate `RED` halt REGARDLESS of profitable PnL!
       - (b) `Alpha Decay` Wald SPRT rejection -> immediate `RED` halt!
       - (c) Expired / `<= 3d` red-news calendar -> immediate `RED` halt!
       - (d) Statement orphan / Standard `swap != 0` violation -> immediate `RED` halt!
       - (e) Stale heartbeat / `kill_switch` -> immediate `RED` halt!
       - (f) Execution TCA Bug RED (`> 2.0x` friction breach) -> immediate `RED` halt!
  5. Strict OPSEC redaction check (`0` raw logins, tickets, IPv4/IPv6, Windows user paths, or bare `$`)
     and single-command CLI execution (`GREEN -> 0`, `AMBER -> 1`, `RED -> 2`).
"""

from __future__ import annotations

import ast
import csv
import json
import sys
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.red_news import RedNewsEvent  # noqa: E402
from quant_core.tca import canonical_payload_sha256  # noqa: E402
from quant_factory.live_ops import daily_live_ops_pipeline as pipeline  # noqa: E402

ORDER_SEND_COUNT = 0

NOW_UTC = datetime(2026, 11, 27, 12, 0, 0, tzinfo=UTC)
NOW_TS = int(NOW_UTC.timestamp())


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _make_dev_returns(n: int = 120, *, mean: float = 0.25, std: float = 0.80, seed: int = 42) -> np.ndarray:
    rng = np.random.default_rng(seed)
    return rng.normal(loc=mean, scale=std, size=n)


def _make_calendar_events(now_dt: datetime, days_ahead: float) -> list[RedNewsEvent]:
    """Build multi-currency red-news events ending at `now_dt + days_ahead`."""
    target_dt = now_dt + timedelta(days=days_ahead)
    # Keep event on a weekday (shift Friday/Monday if needed)
    if target_dt.weekday() == 5:
        target_dt = target_dt - timedelta(days=1)
    elif target_dt.weekday() == 6:
        target_dt = target_dt + timedelta(days=1)
    ts = int(target_dt.timestamp())
    iso = target_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    day = target_dt.strftime("%Y-%m-%d")
    return [
        RedNewsEvent(utc_ts=ts, utc_iso=iso, utc_day=day, ccy=ccy, event=f"{ccy} CPI Release")
        for ccy in ("USD", "GBP", "EUR", "JPY")
    ]


def _build_clean_workspace_fixture(
    root: Path,
    *,
    login: int = 1515987654,
    swap_usd: float = 0.0,
    extra_statement_orphan: bool = False,
    heartbeat_age_sec: int = 12,
    heartbeat_kill_switch: bool = False,
) -> dict[str, Any]:
    """Create a complete clean set of read-only files for an end-to-end daily live-ops run."""
    entry_ts = NOW_TS - 7200
    exit_ts = NOW_TS - 3600

    audit_fields = [
        "utc_ts",
        "account_login",
        "magic",
        "symbol",
        "side",
        "event_type",
        "signal_price",
        "fill_price",
        "sl_price",
        "lots",
        "spread_pts",
        "latency_ms",
        "retcode",
        "pnl_usd",
        "swap_usd",
        "commission_usd",
        "deal_id",
        "order_id",
        "position_id",
        "comment",
    ]
    audit_rows = [
        {
            "utc_ts": entry_ts,
            "account_login": login,
            "magic": 7101,
            "symbol": "USDJPY",
            "side": "BUY",
            "event_type": "ENTRY_FILLED",
            "signal_price": 155.000,
            "fill_price": 155.001,
            "sl_price": 154.500,
            "lots": 0.10,
            "spread_pts": 4.0,
            "latency_ms": 140.0,
            "retcode": 10009,
            "pnl_usd": 0.0,
            "swap_usd": 0.0,
            "commission_usd": -0.25,
            "deal_id": "2001001",
            "order_id": "3001001",
            "position_id": "4001001",
            "comment": "pos=4001001 intent=SIG_001",
        },
        {
            "utc_ts": exit_ts,
            "account_login": login,
            "magic": 7101,
            "symbol": "USDJPY",
            "side": "SELL",
            "event_type": "EXIT_FILLED",
            "signal_price": 155.750,
            "fill_price": 155.749,
            "sl_price": 154.500,
            "lots": 0.10,
            "spread_pts": 4.0,
            "latency_ms": 135.0,
            "retcode": 10009,
            "pnl_usd": 48.20,
            "swap_usd": swap_usd,
            "commission_usd": -0.25,
            "deal_id": "2001002",
            "order_id": "3001002",
            "position_id": "4001001",
            "comment": "pos=4001001 intent=SIG_001 TP_HIT",
        },
    ]
    audit_csv = root / f"naqex_exec_audit_{login}.csv"
    _write_csv(audit_csv, audit_fields, audit_rows)

    stmt_fields = [
        "time",
        "login",
        "deal_id",
        "order_id",
        "position_id",
        "magic",
        "symbol",
        "type",
        "direction",
        "volume",
        "price",
        "commission",
        "swap",
        "profit",
        "comment",
    ]
    stmt_rows: list[dict[str, Any]] = [
        {
            "time": datetime.fromtimestamp(entry_ts, tz=UTC).strftime("%Y.%m.%d %H:%M:%S"),
            "login": login,
            "deal_id": "2001001",
            "order_id": "3001001",
            "position_id": "4001001",
            "magic": 7101,
            "symbol": "USDJPY",
            "type": "BUY",
            "direction": "IN",
            "volume": 0.10,
            "price": 155.001,
            "commission": -0.25,
            "swap": 0.0,
            "profit": 0.0,
            "comment": "pos=4001001",
        },
        {
            "time": datetime.fromtimestamp(exit_ts, tz=UTC).strftime("%Y.%m.%d %H:%M:%S"),
            "login": login,
            "deal_id": "2001002",
            "order_id": "3001002",
            "position_id": "4001001",
            "magic": 7101,
            "symbol": "USDJPY",
            "type": "SELL",
            "direction": "OUT",
            "volume": 0.10,
            "price": 155.749,
            "commission": -0.25,
            "swap": swap_usd,
            "profit": 48.20,
            "comment": "pos=4001001",
        },
    ]
    if extra_statement_orphan:
        stmt_rows.append(
            {
                "time": datetime.fromtimestamp(exit_ts + 60, tz=UTC).strftime("%Y.%m.%d %H:%M:%S"),
                "login": login,
                "deal_id": "2009999",
                "order_id": "3009999",
                "position_id": "4009999",
                "magic": 7101,
                "symbol": "GBPUSD",
                "type": "BUY",
                "direction": "OUT",
                "volume": 0.10,
                "price": 1.30500,
                "commission": -0.25,
                "swap": 0.0,
                "profit": 15.00,
                "comment": "orphan_stmt_trade",
            }
        )
    stmt_csv = root / f"broker_statement_{login}.csv"
    _write_csv(stmt_csv, stmt_fields, stmt_rows)

    # Decision blackbox logging 1 legitimate guard block (must NOT count as missed trade!)
    blackbox_path = root / "naqex_decision_blackbox_20261127.jsonl"
    bb_line = {
        "signal_id": "SIG_BLOCKED_SPREAD",
        "magic": 7101,
        "position_id": "0",
        "symbol": "GBPUSD",
        "side": "BUY",
        "utc_ts": entry_ts + 600,
        "bid": 1.30100,
        "ask": 1.30145,
        "spread_pts": 45.0,
        "expected_entry": 1.30145,
        "expected_sl": 1.29845,
        "expected_lot": 0.10,
        "decision": "BLOCKED_BY_SPREAD",
        "block_reason": "spread_45pts_exceeds_cap",
        "indicators": {"atr14": 0.0020},
    }
    blackbox_path.write_text(json.dumps(bb_line) + "\n", encoding="utf-8", newline="\n")

    expected_python_trades = [
        {
            "signal_id": "SIG_001",
            "magic": 7101,
            "symbol": "USDJPY",
            "side": "BUY",
            "utc_ts": entry_ts,
            "entry_price": 155.000,
            "sl_price": 154.500,
            "lots": 0.10,
            "gross_R": 1.50,
        },
        {
            "signal_id": "SIG_BLOCKED_SPREAD",
            "magic": 7101,
            "symbol": "GBPUSD",
            "side": "BUY",
            "utc_ts": entry_ts + 600,
            "entry_price": 1.30145,
            "sl_price": 1.29845,
            "lots": 0.10,
            "gross_R": 0.80,
        },
    ]

    hb_path = root / "naqex_heartbeat.json"
    hb_payload = {
        "utc_ts": NOW_TS - heartbeat_age_sec,
        "account_login": login,
        "equity": 10048.20,
        "balance": 10048.20,
        "daily_dd_pct": 0.15,
        "static_dd_pct": 0.20,
        "risk_mult": 1.0,
        "regime": "NORMAL",
        "dry_run": False,
        "kill_switch": heartbeat_kill_switch,
        "orphan_no_sl": 0,
    }
    hb_path.write_text(json.dumps(hb_payload) + "\n", encoding="utf-8", newline="\n")

    feed_snapshots = {
        "USDJPY": {
            "symbol": "USDJPY",
            "last_tick_utc": (NOW_UTC - timedelta(seconds=3)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "bid": 155.100,
            "ask": 155.104,
            "point_size": 0.001,
            "median_spread_points": 4.0,
            "is_market_open": True,
        }
    }

    dev_returns = _make_dev_returns(150, mean=0.25, std=0.80, seed=101)
    live_returns = _make_dev_returns(20, mean=0.30, std=0.75, seed=202)

    return {
        "audit_csv": audit_csv,
        "statement_path": stmt_csv,
        "decision_blackbox_path": blackbox_path,
        "expected_python_trades": expected_python_trades,
        "heartbeat_path": hb_path,
        "feed_snapshots": feed_snapshots,
        "dev_returns": dev_returns,
        "live_returns": live_returns,
        "calendar_events": _make_calendar_events(NOW_UTC, days_ahead=30.0),
        "expected_login": login,
    }


class Ops4StaticSafetyTests(unittest.TestCase):
    def test_zero_bare_asserts_zero_mt5_imports_lf_only_and_g12_clean(self) -> None:
        self.assertFalse(pipeline.ORDER_SEND_CAPABLE)
        self.assertEqual(pipeline.ORDER_SEND_COUNT, 0)
        self.assertEqual(ORDER_SEND_COUNT, 0)

        mod_path = AI_ENGINES_DIR / "quant_factory" / "live_ops" / "daily_live_ops_pipeline.py"
        raw = mod_path.read_bytes()
        self.assertNotIn(b"\r\n", raw, "CRLF line endings forbidden in daily_live_ops_pipeline.py")
        text = raw.decode("utf-8")

        # G12: zero suggestions to contact/email FTMO support
        low = text.lower()
        for forbidden in ("contact ftmo", "email ftmo", "ftmo support", "ho tro ftmo", "lien he ftmo"):
            self.assertNotIn(forbidden, low, f"G12 violation: {forbidden!r} found in {mod_path.name}")

        tree = ast.parse(text, filename=str(mod_path))
        for node in ast.walk(tree):
            self.assertNotIsInstance(node, ast.Assert, "[ARCH-02] bare assert forbidden inside quant_factory/")
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "MetaTrader5")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "MetaTrader5")


class Ops4DailyLiveOpsPipelineTests(unittest.TestCase):
    def test_full_green_end_to_end_fixture(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_green_") as tmp:
            root = Path(tmp)
            fx = _build_clean_workspace_fixture(root)
            out_json = root / "receipts" / "daily_ops_green.json"
            out_txt = root / "receipts" / "daily_ops_green.txt"

            report = pipeline.run_daily_live_ops_pipeline(
                account_alias="FTMO_DEMO_CORE",
                firm_profile="FTMO_STANDARD",
                period_label="2026-11-27 Daily",
                now_utc=NOW_UTC,
                expected_login=fx["expected_login"],
                symbols=("USDJPY", "GBPUSD"),
                audit_csv=fx["audit_csv"],
                statement_path=fx["statement_path"],
                expected_python_trades=fx["expected_python_trades"],
                decision_blackbox_path=fx["decision_blackbox_path"],
                dev_returns=fx["dev_returns"],
                live_returns=fx["live_returns"],
                calendar_events=fx["calendar_events"],
                feed_snapshots=fx["feed_snapshots"],
                heartbeat_path=fx["heartbeat_path"],
                days_since_last_trade=4,
                pre_checkout_network={"country_code": "VN", "geo_lookup_ok": True, "is_cgnat": False},
                n_bootstrap_draws=1000,
                out_json=out_json,
                out_digest_txt=out_txt,
            )

            self.assertEqual(report["traffic_light"], pipeline.TRAFFIC_GREEN)
            self.assertEqual(report["action"], pipeline.ACTION_KEEP_1_0X)
            self.assertEqual(report["risk_multiplier"], 1.0)
            self.assertFalse(report["decision"]["dry_run_required"])
            self.assertEqual(report["order_send_count"], 0)
            self.assertFalse(report["order_send_capable"])
            self.assertEqual(pipeline.exit_code_for_report(report), 0)

            # Verify every evaluated subsystem is GREEN
            subs = report["subsystems"]
            self.assertEqual(subs["reconciler"]["status"], "GREEN")
            self.assertEqual(subs["reconciler"]["matched_pairs"], 2)
            self.assertEqual(subs["tca"]["status"], "GREEN")
            self.assertEqual(subs["tca"]["holdout_rows_analysed"], 0)
            self.assertEqual(subs["parity_forensics"]["status"], "GREEN")
            self.assertEqual(subs["parity_forensics"]["counts"]["MATCH_CLEAN"], 1)
            self.assertEqual(subs["parity_forensics"]["counts"]["LEGITIMATE_GUARD_BLOCK"], 1)
            self.assertEqual(subs["decay"]["status"], "GREEN")
            self.assertEqual(subs["postmortem"]["classification"], "Normal Variance")
            self.assertEqual(subs["feed_dst_ttl"]["status"], "GREEN")
            self.assertEqual(subs["heartbeat"]["status"], "GREEN")
            self.assertEqual(subs["preflight_compliance"]["status"], "GREEN")
            self.assertEqual(subs["ops_cloud"]["status"], "GREEN")

            # Verify atomic SHA-256 JSON receipt and zero bare dollar signs
            self.assertTrue(out_json.is_file())
            self.assertTrue(out_txt.is_file())
            loaded = json.loads(out_json.read_text(encoding="utf-8"))
            self.assertEqual(loaded["order_send_count"], 0)
            self.assertEqual(loaded["report_sha256"], canonical_payload_sha256(loaded))
            self.assertNotIn("$", report["digest_text"])
            self.assertNotIn(str(fx["expected_login"]), report["digest_text"])
            self.assertNotIn(str(fx["expected_login"]), out_json.read_text(encoding="utf-8"))

    def test_amber_calendar_ttl_10d_throttles_to_0_5x(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_amber_ttl_") as tmp:
            fx = _build_clean_workspace_fixture(Path(tmp))
            report = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                expected_login=fx["expected_login"],
                symbols=("USDJPY",),
                audit_csv=fx["audit_csv"],
                statement_path=fx["statement_path"],
                expected_python_trades=fx["expected_python_trades"],
                decision_blackbox_path=fx["decision_blackbox_path"],
                dev_returns=fx["dev_returns"],
                live_returns=fx["live_returns"],
                calendar_events=_make_calendar_events(NOW_UTC, days_ahead=10.0),
                feed_snapshots=fx["feed_snapshots"],
                heartbeat_path=fx["heartbeat_path"],
                days_since_last_trade=3,
                n_bootstrap_draws=1000,
            )

            self.assertEqual(report["traffic_light"], pipeline.TRAFFIC_AMBER)
            self.assertEqual(report["action"], pipeline.ACTION_THROTTLE_0_5X)
            self.assertEqual(report["risk_multiplier"], 0.5)
            self.assertFalse(report["decision"]["dry_run_required"])
            self.assertEqual(report["decision"]["red_codes"], [])
            self.assertIn("CALENDAR_TTL_AMBER", report["decision"]["amber_codes"])
            self.assertEqual(pipeline.exit_code_for_report(report), 1)

    def test_amber_regime_shift_inactivity_and_elevated_slippage(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_amber_multi_") as tmp:
            fx = _build_clean_workspace_fixture(Path(tmp))

            # 1. Regime Shift (vol_ratio=1.95x, clean parity, no SPRT reject)
            rep_regime = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                expected_login=fx["expected_login"],
                audit_csv=fx["audit_csv"],
                statement_path=fx["statement_path"],
                expected_python_trades=fx["expected_python_trades"],
                decision_blackbox_path=fx["decision_blackbox_path"],
                dev_returns=fx["dev_returns"],
                live_returns=fx["live_returns"],
                vol_ratio=1.95,
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
                n_bootstrap_draws=500,
            )
            self.assertEqual(rep_regime["traffic_light"], pipeline.TRAFFIC_AMBER)
            self.assertEqual(rep_regime["action"], pipeline.ACTION_THROTTLE_0_5X)
            self.assertEqual(rep_regime["subsystems"]["postmortem"]["classification"], "Regime Shift")
            self.assertIn("POSTMORTEM_REGIME_SHIFT_AMBER", rep_regime["decision"]["amber_codes"])

            # 2. Inactivity >= 21d (22 days) -> AMBER throttle
            rep_inact = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
                days_since_last_trade=22,
            )
            self.assertEqual(rep_inact["traffic_light"], pipeline.TRAFFIC_AMBER)
            self.assertEqual(rep_inact["action"], pipeline.ACTION_THROTTLE_0_5X)
            self.assertIn("INACTIVITY_AMBER_WARNING", rep_inact["decision"]["amber_codes"])

            # 3. Elevated slippage 1.75x (in 1.5x..2.0x band, no bot bug, no SPRT reject) -> AMBER
            rep_slip = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                tca_report={
                    "verdict": "AMBER_FRICTION_WATCH",
                    "portfolio": {
                        "stratified_friction_multiplier_95ci": {
                            "ci_lo": 1.40,
                            "median": 1.72,
                            "mean": 1.75,
                            "ci_hi": 1.92,
                        }
                    },
                    "inputs": {"swap_violations": 0, "missing_swap_count": 0, "unresolved_fills": 0},
                    "cusum_overall": {"alert": False, "max_stat": 1.2},
                    "alerts": ["ELEVATED_SLIPPAGE_1_75X"],
                },
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
            )
            self.assertEqual(rep_slip["traffic_light"], pipeline.TRAFFIC_AMBER)
            self.assertEqual(rep_slip["action"], pipeline.ACTION_THROTTLE_0_5X)
            self.assertIn("TCA_ELEVATED_SLIPPAGE_AMBER", rep_slip["decision"]["amber_codes"])

    def test_red_a_ghost_trade_halts_immediately_regardless_of_profitable_pnl(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_red_ghost_") as tmp:
            fx = _build_clean_workspace_fixture(Path(tmp))
            # Inject an extra wildly profitable MT5 ghost trade (+500 USD / +4.5R) with NO Python signal
            profitable_actual_trades = [
                {
                    "signal_id": "SIG_001",
                    "magic": 7101,
                    "symbol": "USDJPY",
                    "side": "BUY",
                    "utc_ts": NOW_TS - 7200,
                    "entry_price": 155.001,
                    "sl_price": 154.500,
                    "lots": 0.10,
                    "exit_price": 155.749,
                    "exit_utc_ts": NOW_TS - 3600,
                    "gross_R": 1.50,
                    "net_R": 1.49,
                    "net_pnl_usd": 48.20,
                    "swap_usd": 0.0,
                },
                {
                    "signal_id": "",
                    "position_id": "999888777",
                    "magic": 7101,
                    "symbol": "EURJPY",
                    "side": "BUY",
                    "utc_ts": NOW_TS - 1800,
                    "entry_price": 162.000,
                    "sl_price": 161.500,
                    "lots": 0.50,
                    "exit_price": 164.250,
                    "exit_utc_ts": NOW_TS - 900,
                    "gross_R": 4.50,
                    "net_R": 4.48,
                    "net_pnl_usd": 500.00,
                    "swap_usd": 0.0,
                },
            ]

            report = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                expected_login=fx["expected_login"],
                audit_csv=fx["audit_csv"],
                statement_path=fx["statement_path"],
                expected_python_trades=fx["expected_python_trades"],
                actual_mt5_trades=profitable_actual_trades,
                decision_blackbox_path=fx["decision_blackbox_path"],
                dev_returns=fx["dev_returns"],
                live_returns=fx["live_returns"],
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
                n_bootstrap_draws=500,
            )

            self.assertEqual(report["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertEqual(report["action"], pipeline.ACTION_HALT_DRYRUN)
            self.assertEqual(report["risk_multiplier"], 0.0)
            self.assertTrue(report["decision"]["dry_run_required"])
            self.assertIn("PARITY_BOT_BUG_GHOST_TRADE", report["decision"]["red_codes"])
            self.assertEqual(report["subsystems"]["parity_forensics"]["counts"]["BOT_BUG_GHOST_TRADE"], 1)
            self.assertEqual(pipeline.exit_code_for_report(report), 2)

    def test_red_b_alpha_decay_sprt_rejection_halts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_red_decay_") as tmp:
            fx = _build_clean_workspace_fixture(Path(tmp))
            dev_pos = _make_dev_returns(200, mean=0.45, std=0.60, seed=7)
            # Persistent negative live stream triggering CUSUM breach + Wald SPRT REJECT_EDGE_DECAYED
            live_decayed = np.full(35, -0.55, dtype=np.float64) + np.linspace(-0.05, 0.05, 35)

            report = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                dev_returns=dev_pos,
                live_returns=live_decayed,
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
            )

            self.assertEqual(report["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertEqual(report["action"], pipeline.ACTION_HALT_DRYRUN)
            self.assertEqual(report["subsystems"]["decay"]["sprt_state"], "REJECT_EDGE_DECAYED")
            self.assertEqual(report["subsystems"]["decay"]["verdict"], "RED_HALT_ALPHA_DECAY")
            self.assertEqual(report["subsystems"]["postmortem"]["classification"], "Alpha Decay")
            self.assertIn("ALPHA_DECAY_SPRT_REJECT", report["decision"]["red_codes"])
            self.assertEqual(pipeline.exit_code_for_report(report), 2)

    def test_red_c_expired_red_news_calendar_halts(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_red_cal_") as tmp:
            fx = _build_clean_workspace_fixture(Path(tmp))
            expired_events = _make_calendar_events(NOW_UTC, days_ahead=-2.0)

            report = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                symbols=("USDJPY", "GBPUSD"),
                calendar_events=expired_events,
                heartbeat_path=fx["heartbeat_path"],
            )

            self.assertEqual(report["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertEqual(report["action"], pipeline.ACTION_HALT_DRYRUN)
            self.assertEqual(report["subsystems"]["feed_dst_ttl"]["calendar_ttl"]["status"], "RED")
            self.assertFalse(report["subsystems"]["feed_dst_ttl"]["calendar_ttl"]["allow_new_entries"])
            self.assertIn("CALENDAR_TTL_RED_OR_EXPIRED", report["decision"]["red_codes"])

            # Empty calendar list also fails closed RED and remains JSON-serializable (no -inf crash!)
            out_json = Path(tmp) / "empty_cal_receipt.json"
            rep_empty = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                symbols=("USDJPY",),
                calendar_events=[],
                out_json=out_json,
            )
            self.assertEqual(rep_empty["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertTrue(out_json.is_file())
            self.assertIsNone(rep_empty["subsystems"]["feed_dst_ttl"]["calendar_ttl"]["min_remaining_days"])

    def test_red_d_e_f_reconciler_orphan_swap_stale_heartbeat_and_tca_red(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_red_other_") as tmp:
            root = Path(tmp)
            # (d) Statement orphan + non-zero swap on Standard -> RED
            fx_bad_rec = _build_clean_workspace_fixture(
                root / "rec",
                swap_usd=-2.35,
                extra_statement_orphan=True,
            )
            rep_rec = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                expected_login=fx_bad_rec["expected_login"],
                audit_csv=fx_bad_rec["audit_csv"],
                statement_path=fx_bad_rec["statement_path"],
                calendar_events=fx_bad_rec["calendar_events"],
                heartbeat_path=fx_bad_rec["heartbeat_path"],
                require_zero_swap=True,
                n_bootstrap_draws=500,
            )
            self.assertEqual(rep_rec["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertIn("RECONCILE_ORPHAN_STATEMENT", rep_rec["decision"]["red_codes"])
            self.assertIn("RECONCILE_SWAP_VIOLATION", rep_rec["decision"]["red_codes"])

            # (e) Stale heartbeat (> 180s) -> RED
            fx_stale = _build_clean_workspace_fixture(root / "hb", heartbeat_age_sec=420)
            rep_hb = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                calendar_events=fx_stale["calendar_events"],
                heartbeat_path=fx_stale["heartbeat_path"],
            )
            self.assertEqual(rep_hb["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertIn("HEARTBEAT_CRITICAL", rep_hb["decision"]["red_codes"])

            # (f) Execution TCA Bug RED (> 2.0x friction breach) -> RED
            rep_tca = pipeline.run_daily_live_ops_pipeline(
                now_utc=NOW_UTC,
                tca_report={
                    "verdict": "RED_FRICTION_BREACH",
                    "portfolio": {
                        "stratified_friction_multiplier_95ci": {
                            "ci_lo": 2.10,
                            "median": 2.45,
                            "mean": 2.50,
                            "ci_hi": 2.90,
                        }
                    },
                    "inputs": {"swap_violations": 0, "missing_swap_count": 0, "unresolved_fills": 0},
                    "cusum_overall": {"alert": True, "max_stat": 5.8},
                    "alerts": ["FRICTION_BREACH_2_50X"],
                },
                calendar_events=fx_stale["calendar_events"],
            )
            self.assertEqual(rep_tca["traffic_light"], pipeline.TRAFFIC_RED)
            self.assertIn("TCA_FRICTION_BREACH_RED", rep_tca["decision"]["red_codes"])
            self.assertIn("POSTMORTEM_EXECUTION_TCA_BUG_RED", rep_tca["decision"]["red_codes"])

    def test_opsec_redaction_and_cli_execution(self) -> None:
        with tempfile.TemporaryDirectory(prefix="naqex_ops4_opsec_") as tmp:
            root = Path(tmp)
            secret_login = 1515887766
            fx = _build_clean_workspace_fixture(root, login=secret_login)

            # Inject synthetic sensitive tokens (RFC 5737 TEST-NET IPv4, RFC 3849 IPv6, Windows user path, bare $)
            test_ipv4 = "203.0.113.42"
            test_ipv6 = "2001:db8::cafe"
            test_ticket = "88997766"
            test_win_path = "C:" + "\\Users\\" + "TestOperator\\Desktop\\secret.csv"
            cgnat_hop = "100." + "65.1.1"

            out_json = root / "opsec_receipt.json"
            out_txt = root / "opsec_digest.txt"
            report = pipeline.run_daily_live_ops_pipeline(
                account_alias=f"ACCT_{secret_login}_{test_ipv4}",
                period_label=f"Daily $250.00 ticket={test_ticket} path={test_win_path} ip={test_ipv6}",
                now_utc=NOW_UTC,
                expected_login=secret_login,
                audit_csv=fx["audit_csv"],
                statement_path=fx["statement_path"],
                calendar_events=fx["calendar_events"],
                heartbeat_path=fx["heartbeat_path"],
                pre_checkout_network={
                    "country_code": "VN",
                    "geo_lookup_ok": True,
                    "hop_ips": ["10.0.0.1", cgnat_hop],
                },
                n_bootstrap_draws=500,
                out_json=out_json,
                out_digest_txt=out_txt,
            )

            digest_text = report["digest_text"]
            raw_json_text = out_json.read_text(encoding="utf-8")

            for blob_name, blob in (("digest_text", digest_text), ("json_receipt", raw_json_text)):
                self.assertNotIn(str(secret_login), blob, f"Raw login leaked into {blob_name}")
                self.assertNotIn(test_ipv4, blob, f"Raw IPv4 leaked into {blob_name}")
                self.assertNotIn(test_ipv6, blob, f"Raw IPv6 leaked into {blob_name}")
                self.assertNotIn(test_ticket, blob, f"Raw ticket leaked into {blob_name}")
                self.assertNotIn("TestOperator", blob, f"Windows user path leaked into {blob_name}")
                self.assertNotIn("$", blob, f"Bare dollar sign leaked into {blob_name}")
                self.assertNotIn("email ftmo", blob.lower(), f"G12 violation leaked into {blob_name}")
                self.assertNotIn("contact ftmo", blob.lower(), f"G12 violation leaked into {blob_name}")

            # Verify single-command CLI works end-to-end with --config-json
            cfg_path = root / "pipeline_cfg.json"
            exp_path = root / "expected_trades.json"
            exp_path.write_text(json.dumps(fx["expected_python_trades"]), encoding="utf-8")
            cal_csv = root / "red_news_future.csv"
            _write_csv(
                cal_csv,
                ["utc_ts", "ccy", "event"],
                [
                    {"utc_ts": ev.utc_ts, "ccy": ev.ccy, "event": ev.event}
                    for ev in fx["calendar_events"]
                ],
            )
            cfg_path.write_text(
                json.dumps(
                    {
                        "account_alias": "CLI_DEMO",
                        "now_utc": NOW_UTC.strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "expected_login": secret_login,
                        "audit_csv": str(fx["audit_csv"]),
                        "statement_path": str(fx["statement_path"]),
                        "expected_python_trades": str(exp_path),
                        "decision_blackbox_path": str(fx["decision_blackbox_path"]),
                        "calendar_path": str(cal_csv),
                        "heartbeat_path": str(fx["heartbeat_path"]),
                        "days_since_last_trade": 2,
                        "n_bootstrap_draws": 500,
                    }
                ),
                encoding="utf-8",
            )
            cli_out = root / "cli_receipt.json"
            rc = pipeline.main(
                [
                    "--config-json",
                    str(cfg_path),
                    "--out-json",
                    str(cli_out),
                    "--json",
                ]
            )
            self.assertEqual(rc, 0)
            self.assertTrue(cli_out.is_file())
            cli_doc = json.loads(cli_out.read_text(encoding="utf-8"))
            self.assertEqual(cli_doc["traffic_light"], pipeline.TRAFFIC_GREEN)
            self.assertEqual(cli_doc["action"], pipeline.ACTION_KEEP_1_0X)
            self.assertEqual(cli_doc["order_send_count"], 0)
            self.assertEqual(cli_doc["report_sha256"], canonical_payload_sha256(cli_doc))


if __name__ == "__main__":
    unittest.main()
