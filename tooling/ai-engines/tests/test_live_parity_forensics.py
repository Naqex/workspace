"""Tests for OPS-6 Live Broker Tape Ingestor, Parity Forensics, Trade Geometry & Anti-Overfit Loop.

Covers:
  1. Static safety & immutability invariants (zero bare `assert` in quant_factory modules,
     `ORDER_SEND_CAPABLE=False`, `ORDER_SEND_COUNT=0`, zero `MetaTrader5` imports, LF-only).
  2. Live Broker Tape Ingestor: CSV (nfp_cpi 23-col) & JSONL (nested spread log) ingestion,
     broker symbol specs JSON, SHA-256 manifest verification + tamper detection, strict
     live-vault isolation against `.runtime/hot-m1-cache/` and sealed Holdout `2025+`.
  3. True Broker M1 Bid/Ask bar construction & executable price path extraction.
  4. Legacy `v1.01`/`v1.03` adapter (`naqex_exec_audit.csv`, `naqex_master_v103_shadow.csv`)
     and `naqex_decision_blackbox_YYYYMMDD.jsonl` (strict FILE_ANSI, rejects UTF-16 BOM).
  5. Split-deal & partial-fill aggregation by `POSITION_IDENTIFIER` (combining entry/exit
     commission, swap, fee, and realized PnL while preserving P0-7 `None` semantics).
  6. All 5 parity classes (`MATCH_CLEAN`, `BOT_BUG_GHOST_TRADE`, `BOT_BUG_MISSED_TRADE`,
     `LOT_OR_SL_DRIFT`, `EXECUTION_FRICTION_DRIFT`) + legitimate `BLOCKED_BY_*` / `v1.03`
     `ORDER_BLOCKED_*` NOT misclassified as missed!
  7. Exact `v3.5` MT5 Strategy Tester Parity Gate (`evaluate_tester_parity_gate`) pass & fail modes.
  8. Real broker-tape `W1..L4` excursions (`provisional=False`) + Weekly Forensics Postmortem
     + Anti-Overfit Feedback lock (`N_live < 30` locked vs `N_live >= 30` `HypothesisCard` emission).
"""

from __future__ import annotations

import ast
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path
from typing import Any

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_factory.live_ops import live_broker_tape_ingestor as ingestor  # noqa: E402
from quant_factory.live_ops import live_parity_forensics as forensics  # noqa: E402
from quant_factory.research_council import HypothesisCard, KillCriteria  # noqa: E402

ORDER_SEND_COUNT = 0


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)


def _make_broker_ticks_for_trade(
    symbol: str,
    entry_ts: int,
    *,
    points: list[tuple[int, float, float]],
) -> list[dict[str, Any]]:
    """Build flat broker Bid/Ask tick dicts offset in seconds from `entry_ts`."""
    return [
        {
            "utc_ts_ms": (entry_ts + offset_s) * 1000,
            "symbol": symbol,
            "bid": bid,
            "ask": ask,
            "record_tier": "QUOTE_ONLY",
            "order_send_count": 0,
        }
        for offset_s, bid, ask in points
    ]


class Ops6StaticSafetyAndBlackboxContractTests(unittest.TestCase):
    def test_zero_bare_asserts_and_zero_mt5_imports_in_ops6_modules(self) -> None:
        self.assertFalse(ingestor.ORDER_SEND_CAPABLE)
        self.assertEqual(ingestor.ORDER_SEND_COUNT, 0)
        self.assertFalse(forensics.ORDER_SEND_CAPABLE)
        self.assertEqual(forensics.ORDER_SEND_COUNT, 0)

        for mod_path in (
            AI_ENGINES_DIR / "quant_factory" / "live_ops" / "live_broker_tape_ingestor.py",
            AI_ENGINES_DIR / "quant_factory" / "live_ops" / "live_parity_forensics.py",
        ):
            raw = mod_path.read_bytes()
            self.assertNotIn(b"\r\n", raw, f"CRLF forbidden in {mod_path.name}")
            tree = ast.parse(raw.decode("utf-8"), filename=str(mod_path))
            for node in ast.walk(tree):
                self.assertNotIsInstance(node, ast.Assert, f"[ARCH-02] bare assert forbidden in {mod_path.name}")
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        self.assertNotEqual(alias.name, "MetaTrader5")
                elif isinstance(node, ast.ImportFrom):
                    self.assertNotEqual(node.module, "MetaTrader5")

    def test_decision_blackbox_mqh_contract_if_present(self) -> None:
        mqh_path = WORKSPACE_ROOT / "private_vault" / "strategies" / "offensive3_v3" / "Naqex_DecisionBlackbox.mqh"
        if not mqh_path.is_file():
            self.skipTest("Layer-2 private_vault MQH not present in CI")
        text = mqh_path.read_text(encoding="utf-8")
        self.assertIn("FILE_ANSI", text)
        self.assertIn("FILE_COMMON", text)
        self.assertIn("InpBlackboxEnableInTester = true", text)
        self.assertIn("EscapeJsonString", text)
        self.assertIn("BuildDailyFileName", text)
        self.assertIn("signal_id", text)
        self.assertIn("position_id", text)
        self.assertIn("strategy_sha", text)
        self.assertIn("preset_sha", text)
        self.assertNotIn("OrderSend(", text)


class Ops6LiveBrokerTapeIngestorTests(unittest.TestCase):
    def test_ingest_csv_and_jsonl_with_specs_manifest_and_m1_bars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hot_cache = root / ".runtime" / "hot-m1-cache"
            hot_cache.mkdir(parents=True)
            hot_manifest = hot_cache / "manifest.json"
            hot_manifest.write_text('{"dev":"2018-2024"}\n', encoding="utf-8")
            holdout_dir = root / ".runtime" / "native_ftmo_holdout"
            holdout_dir.mkdir(parents=True)

            vault_root = root / ".runtime" / "live-vault"
            src_dir = root / "incoming"
            src_dir.mkdir(parents=True)

            # 1) NFP/CPI 23-col CSV tape (including 2 distinct same-ms ticks + 1 exact dup)
            csv_path = src_dir / "nfp_cpi_20261127.csv"
            base_ms = 1795700040_000  # 2026-11-27 exact minute boundary
            _write_csv(
                csv_path,
                [
                    "record_tier",
                    "event_id",
                    "utc_ts_ms",
                    "symbol",
                    "bid",
                    "ask",
                    "point",
                    "spread_pts",
                    "order_send_count",
                ],
                [
                    {
                        "record_tier": "QUOTE_ONLY",
                        "event_id": "DEMO",
                        "utc_ts_ms": base_ms + 1_000,
                        "symbol": "US100.cash",
                        "bid": 20500.00,
                        "ask": 20500.20,
                        "point": 0.01,
                        "spread_pts": 20.0,
                        "order_send_count": 0,
                    },
                    # Exact duplicate -> deduplicated
                    {
                        "record_tier": "QUOTE_ONLY",
                        "event_id": "DEMO",
                        "utc_ts_ms": base_ms + 1_000,
                        "symbol": "US100.cash",
                        "bid": 20500.00,
                        "ask": 20500.20,
                        "point": 0.01,
                        "spread_pts": 20.0,
                        "order_send_count": 0,
                    },
                    # Distinct same-ms tick -> preserved!
                    {
                        "record_tier": "QUOTE_ONLY",
                        "event_id": "DEMO",
                        "utc_ts_ms": base_ms + 1_000,
                        "symbol": "US100.cash",
                        "bid": 20502.50,
                        "ask": 20502.75,
                        "point": 0.01,
                        "spread_pts": 25.0,
                        "order_send_count": 0,
                    },
                    {
                        "record_tier": "QUOTE_ONLY",
                        "event_id": "DEMO",
                        "utc_ts_ms": base_ms + 40_000,
                        "symbol": "US100.cash",
                        "bid": 20498.00,
                        "ask": 20498.20,
                        "point": 0.01,
                        "spread_pts": 20.0,
                        "order_send_count": 0,
                    },
                ],
            )

            # 2) Nested JSONL live spread tape (mt5_live_spread_log style)
            jsonl_path = src_dir / "mt5_live_spread_log.jsonl"
            jsonl_lines = [
                json.dumps(
                    {
                        "captured_utc_ts": (base_ms // 1000) + 5,
                        "quotes": {
                            "USDJPY": {"available": True, "bid": 152.100, "ask": 152.108},
                            "UNAVAIL": {"available": False, "bid": 0.0, "ask": 0.0},
                        },
                    }
                ),
                json.dumps(
                    {
                        "captured_utc_ts": (base_ms // 1000) + 35,
                        "quotes": {
                            "USDJPY": {"available": True, "bid": 152.140, "ask": 152.147},
                        },
                    }
                ),
            ]
            jsonl_path.write_text("\n".join(jsonl_lines) + "\n", encoding="utf-8")

            # 3) Broker symbol specs JSON
            specs_path = src_dir / "ftmo_specs.json"
            specs_path.write_text(
                json.dumps(
                    {
                        "symbols": {
                            "US100.cash": {"digits": 2, "point": 0.01, "contract_size": 1.0, "stops_level": 0},
                            "USDJPY": {"digits": 3, "point": 0.001, "contract_size": 100000.0, "stops_level": 0},
                        }
                    }
                ),
                encoding="utf-8",
            )

            res = ingestor.ingest_live_broker_tape(
                account_alias="FTMO_DEMO_PRIMARY",
                quote_tape_paths=[csv_path, jsonl_path],
                symbol_specs_path=specs_path,
                vault_root=vault_root,
                hot_m1_cache_dir=hot_cache,
                holdout_dir=holdout_dir,
            )

            manifest = res["manifest"]
            self.assertEqual(manifest["order_send_count"], 0)
            self.assertFalse(manifest["order_send_capable"])
            self.assertTrue(manifest["isolation"]["verified"])
            self.assertFalse(manifest["isolation"]["hot_m1_cache_contaminated"])
            self.assertFalse(manifest["isolation"]["holdout_contaminated"])
            self.assertEqual(manifest["symbols_ingested"], ["US100", "USDJPY"])
            self.assertEqual(res["ticks_count"], 5)  # 3 unique US100 + 2 USDJPY

            # Check M1 Bid/Ask bar OHLC accuracy
            us100_bars = res["m1_bars_by_symbol"]["US100"]
            self.assertEqual(len(us100_bars), 1)
            b0 = us100_bars[0]
            self.assertEqual(b0["tick_count"], 3)
            self.assertAlmostEqual(b0["bid_open"], 20500.00)
            self.assertAlmostEqual(b0["bid_high"], 20502.50)
            self.assertAlmostEqual(b0["bid_low"], 20498.00)
            self.assertAlmostEqual(b0["bid_close"], 20498.00)
            self.assertAlmostEqual(b0["ask_high"], 20502.75)
            self.assertAlmostEqual(b0["spread_pts_median"], 20.0)

            # Reload from NPZ & verify SHA-256 manifest
            reloaded = ingestor.load_ingested_broker_m1_bars(res["account_vault_dir"], "US100.cash")
            self.assertEqual(len(reloaded), 1)
            self.assertAlmostEqual(reloaded[0]["bid_high"], 20502.50)

            check = ingestor.verify_live_vault_manifest(res["account_vault_dir"])
            self.assertTrue(check["valid"])
            self.assertEqual(check["mismatches"], [])

            # Tamper with an ingested M1 bar file -> verify_live_vault_manifest MUST fail closed
            npz_file = Path(res["account_vault_dir"]) / "m1_bars" / "US100_m1_bidask.npz"
            npz_file.write_bytes(npz_file.read_bytes() + b"TAMPER")
            tampered = ingestor.verify_live_vault_manifest(res["account_vault_dir"])
            self.assertFalse(tampered["valid"])
            self.assertTrue(any("M1_BAR_SHA_MISMATCH" in m for m in tampered["mismatches"]))

    def test_live_vault_isolation_rejects_dev_cache_holdout_and_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            hot_cache = root / ".runtime" / "hot-m1-cache"
            holdout_dir = root / ".runtime" / "holdout_2025"

            bad_roots = [
                hot_cache,
                root / ".runtime" / "hot-m1-cache" / "live-vault",
                holdout_dir,
                root / ".runtime" / "holdout" / "live-vault",
                root / "dev_cache" / "live-vault",
                root / "private_vault" / "live-vault",
                root / "not_isolated_dir",
                Path("E:/live-vault"),
                root / ".runtime" / "live-vault" / ".." / "hot-m1-cache",
            ]
            for bad in bad_roots:
                with self.assertRaises(ingestor.LiveVaultIsolationError, msg=f"Should reject {bad}"):
                    ingestor.validate_live_vault_target(
                        bad,
                        "DEMO_A",
                        hot_m1_cache_dir=hot_cache,
                        holdout_dir=holdout_dir,
                    )

            for bad_alias in ("", "../escape", "hot-m1-cache", "holdout", "bad alias!"):
                with self.assertRaises(ingestor.LiveVaultIsolationError, msg=f"Should reject alias {bad_alias!r}"):
                    ingestor.validate_live_vault_target(
                        root / ".runtime" / "live-vault",
                        bad_alias,
                        hot_m1_cache_dir=hot_cache,
                        holdout_dir=holdout_dir,
                    )

    def test_nonzero_order_send_in_quote_tape_fails_closed(self) -> None:
        with self.assertRaises(ValueError):
            ingestor.parse_broker_quote_records(
                [
                    {
                        "utc_ts_ms": 1795700040_000,
                        "symbol": "EURUSD",
                        "bid": 1.0800,
                        "ask": 1.0801,
                        "order_send_count": 1,
                    }
                ]
            )


class Ops6LegacyAdapterAndPositionAggregationTests(unittest.TestCase):
    def test_v103_legacy_adapter_blackbox_and_split_deal_position_grouping(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            # 1) Native v1.03 naqex_exec_audit.csv with partial entry + 2 partial exits (pos=77001)
            audit_csv = root / "naqex_exec_audit.csv"
            _write_csv(
                audit_csv,
                [
                    "utc_ts",
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
                    "comment",
                ],
                [
                    {
                        "utc_ts": 1795700100,
                        "magic": 260101,
                        "symbol": "USDJPY",
                        "side": "BUY",
                        "event_type": "PARTIAL_ENTRY",
                        "signal_price": 152.000,
                        "fill_price": 152.002,
                        "sl_price": 151.500,
                        "lots": 0.60,
                        "spread_pts": 7.0,
                        "latency_ms": 85.0,
                        "retcode": 10010,
                        "pnl_usd": 0.0,
                        "swap_usd": 0.0,
                        "commission_usd": -2.10,
                        "comment": "E1|v103|intent=SIG01|deal=9001|ord=8001|pos=77001",
                    },
                    {
                        "utc_ts": 1795700101,
                        "magic": 260101,
                        "symbol": "USDJPY",
                        "side": "BUY",
                        "event_type": "PARTIAL_ENTRY",
                        "signal_price": 152.000,
                        "fill_price": 152.007,
                        "sl_price": 151.500,
                        "lots": 0.40,
                        "spread_pts": 8.0,
                        "latency_ms": 95.0,
                        "retcode": 10009,
                        "pnl_usd": 0.0,
                        "swap_usd": 0.0,
                        "commission_usd": -1.40,
                        "comment": "E1|v103|intent=SIG01|deal=9002|ord=8001|pos=77001",
                    },
                    {
                        "utc_ts": 1795703600,
                        "magic": 260101,
                        "symbol": "USDJPY",
                        "side": "SELL",
                        "event_type": "PARTIAL_EXIT",
                        "signal_price": 152.500,
                        "fill_price": 152.500,
                        "sl_price": 151.500,
                        "lots": 0.50,
                        "spread_pts": 7.0,
                        "latency_ms": 60.0,
                        "retcode": 10009,
                        "pnl_usd": 164.0,
                        "swap_usd": 0.0,
                        "commission_usd": -1.75,
                        "comment": "TP_PART1|deal=9003|pos=77001",
                    },
                    {
                        "utc_ts": 1795705400,
                        "magic": 260101,
                        "symbol": "USDJPY",
                        "side": "SELL",
                        "event_type": "TP_HIT",
                        "signal_price": 152.700,
                        "fill_price": 152.700,
                        "sl_price": 151.500,
                        "lots": 0.50,
                        "spread_pts": 7.0,
                        "latency_ms": 55.0,
                        "retcode": 10009,
                        "pnl_usd": 229.0,
                        "swap_usd": 0.0,
                        "commission_usd": -1.75,
                        "comment": "TP_FINAL|deal=9004|pos=77001",
                    },
                ],
            )
            audit_rows = forensics.load_exec_audit_records(audit_csv)
            self.assertEqual(len(audit_rows), 4)

            positions = forensics.aggregate_mt5_deals_by_position(audit_rows)
            self.assertEqual(len(positions), 1)
            pos = positions[0]
            self.assertEqual(pos["position_id"], "77001")
            self.assertEqual(pos["signal_id"], "SIG01")
            self.assertAlmostEqual(pos["lots"], 1.0, places=6)
            self.assertAlmostEqual(pos["closed_lots"], 1.0, places=6)
            self.assertAlmostEqual(pos["entry_price"], 152.004, places=6)  # 0.6*152.002 + 0.4*152.007
            self.assertAlmostEqual(pos["exit_price"], 152.600, places=6)  # 0.5*152.5 + 0.5*152.7
            self.assertAlmostEqual(pos["commission_usd"], -7.0, places=6)
            self.assertAlmostEqual(pos["swap_usd"], 0.0, places=6)
            self.assertAlmostEqual(pos["gross_pnl_usd"], 393.0, places=6)
            self.assertAlmostEqual(pos["net_pnl_usd"], 386.0, places=6)
            self.assertEqual(pos["exit_reason"], "TP")
            self.assertEqual(pos["entry_deal_count"], 2)
            self.assertEqual(pos["exit_deal_count"], 2)
            self.assertFalse(pos["incomplete_close"])

            # 2) Native v1.03 naqex_master_v103_shadow.csv
            shadow_csv = root / "naqex_master_v103_shadow.csv"
            _write_csv(
                shadow_csv,
                [
                    "utc_ts",
                    "account_login",
                    "intent_id",
                    "engine_id",
                    "magic",
                    "symbol",
                    "deal_side",
                    "event_type",
                    "signal_price",
                    "sl_price",
                    "risk_pct",
                    "lots",
                    "tick_lag_ms",
                    "shadow_only",
                    "reason",
                ],
                [
                    {
                        "utc_ts": 1795701000,
                        "account_login": 1515343166,
                        "intent_id": "SIG02",
                        "engine_id": "E1_USDJPY",
                        "magic": 260101,
                        "symbol": "USDJPY",
                        "deal_side": "BUY",
                        "event_type": "ORDER_BLOCKED_SPREAD",
                        "signal_price": 152.100,
                        "sl_price": 151.600,
                        "risk_pct": 0.0,
                        "lots": 0.0,
                        "tick_lag_ms": 120,
                        "shadow_only": "false",
                        "reason": "SPREAD_45>25",
                    }
                ],
            )
            shadow_recs = forensics.load_v103_shadow_csv(shadow_csv)
            self.assertEqual(len(shadow_recs), 1)
            self.assertEqual(shadow_recs[0]["decision"], "BLOCKED_BY_SPREAD")
            self.assertTrue(forensics.is_legitimate_guard_block(shadow_recs[0]["decision"]))

            # 3) New naqex_decision_blackbox_20261127.jsonl (strict FILE_ANSI)
            bb_file = root / "naqex_decision_blackbox_20261127.jsonl"
            bb_file.write_text(
                json.dumps(
                    {
                        "schema": "naqex-decision-blackbox-v1",
                        "signal_id": "SIG03",
                        "magic": 260102,
                        "position_id": 0,
                        "symbol": "US100.cash",
                        "side": "SELL",
                        "server_time": "2026-11-27 15:00:00",
                        "utc_time": "2026-11-27T13:00:00Z",
                        "utc_ts": 1795698000,
                        "bid": 20500.0,
                        "ask": 20500.8,
                        "spread_pts": 80.0,
                        "indicators": {"atr14": 42.5, "zscore": -2.1},
                        "expected_entry": 20500.0,
                        "expected_sl": 20585.0,
                        "expected_lot": 0.25,
                        "decision": "BLOCKED_BY_SPREAD",
                        "block_reason": "SPREAD_80>40",
                        "strategy_sha": "abc123",
                        "preset_sha": "def456",
                    }
                )
                + "\n",
                encoding="utf-8",
            )
            bb_recs = forensics.load_decision_blackbox_jsonl(bb_file)
            self.assertEqual(len(bb_recs), 1)
            self.assertEqual(bb_recs[0]["canonical_symbol"], "US100")
            self.assertEqual(bb_recs[0]["indicators"]["atr14"], 42.5)
            self.assertEqual(bb_recs[0]["decision"], "BLOCKED_BY_SPREAD")

            # 4) UTF-16 BOM in blackbox MUST fail closed!
            bad_bom = root / "naqex_decision_blackbox_20261128.jsonl"
            bad_bom.write_bytes(b"\xff\xfe" + '{"symbol":"EURUSD"}\n'.encode("utf-16-le"))
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(bad_bom)


class Ops6ParityClassifierAndTesterGateTests(unittest.TestCase):
    def test_all_five_parity_classes_plus_legitimate_guard_block(self) -> None:
        t0 = 1795700000
        expected = [
            # 1. MATCH_CLEAN (US100 canonical alias matches US100.cash!)
            {
                "signal_id": "S_CLEAN",
                "symbol": "US100",
                "side": "BUY",
                "magic": 101,
                "utc_ts": t0,
                "entry_price": 20000.0,
                "sl_price": 19900.0,
                "lots": 0.50,
                "spread_pts": 20.0,
                "gross_R": 1.5,
            },
            # 2. BOT_BUG_MISSED_TRADE (no MT5 fill AND no guard block logged!)
            {
                "signal_id": "S_MISSED",
                "symbol": "GBPUSD",
                "side": "SELL",
                "magic": 102,
                "utc_ts": t0 + 300,
                "entry_price": 1.27000,
                "sl_price": 1.27500,
                "lots": 0.40,
                "gross_R": 1.0,
            },
            # 3. LEGITIMATE_GUARD_BLOCK (BLOCKED_BY_SPREAD logged -> MUST NOT be MISSED!)
            {
                "signal_id": "S_GUARD_SPREAD",
                "symbol": "EURJPY",
                "side": "BUY",
                "magic": 103,
                "utc_ts": t0 + 600,
                "entry_price": 164.000,
                "sl_price": 163.500,
                "lots": 0.30,
                "gross_R": 0.5,
            },
            # 4. LOT_OR_SL_DRIFT (15% lot drift -> catches TICK_VALUE_LOSS bug!)
            {
                "signal_id": "S_LOT_DRIFT",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 104,
                "utc_ts": t0 + 900,
                "entry_price": 152.000,
                "sl_price": 151.500,
                "lots": 1.00,
                "spread_pts": 7.0,
                "gross_R": 1.0,
            },
            # 5. EXECUTION_FRICTION_DRIFT (signal/lot/SL match, but spread & slippage exceed budget -> TCA)
            {
                "signal_id": "S_FRICTION",
                "symbol": "EURUSD",
                "side": "BUY",
                "magic": 105,
                "utc_ts": t0 + 1200,
                "entry_price": 1.08000,
                "sl_price": 1.07500,
                "lots": 0.50,
                "spread_pts": 4.0,
                "spread_budget_pts": 8.0,
                "slippage_budget_pts": 5.0,
                "gross_R": 1.0,
            },
        ]
        actual = [
            # Matches S_CLEAN within 12s, 2% lot drift (<= 5%), normal spread
            {
                "signal_id": "S_CLEAN",
                "position_id": "P1",
                "symbol": "US100.cash",
                "side": "BUY",
                "magic": 101,
                "utc_ts": t0 + 12,
                "entry_price": 20000.05,
                "sl_price": 19900.05,
                "lots": 0.51,
                "spread_pts": 22.0,
                "swap_usd": 0.0,
                "gross_R": 1.49,
            },
            # Matches S_LOT_DRIFT with +20% lot bug (1.20 vs 1.00)
            {
                "signal_id": "S_LOT_DRIFT",
                "position_id": "P2",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 104,
                "utc_ts": t0 + 905,
                "entry_price": 152.001,
                "sl_price": 151.501,
                "lots": 1.20,
                "spread_pts": 7.0,
                "swap_usd": 0.0,
                "gross_R": 1.0,
            },
            # Matches S_FRICTION (lot/SL exact, but spread=28pts > 8pts & adverse slip=20pts > 5pts)
            {
                "signal_id": "S_FRICTION",
                "position_id": "P3",
                "symbol": "EURUSD",
                "side": "BUY",
                "magic": 105,
                "utc_ts": t0 + 1203,
                "entry_price": 1.08020,
                "sl_price": 1.07520,
                "lots": 0.50,
                "spread_pts": 28.0,
                "swap_usd": 0.0,
                "gross_R": 0.96,
            },
            # Unmatched MT5 execution -> BOT_BUG_GHOST_TRADE!
            {
                "signal_id": "GHOST_99",
                "position_id": "P4",
                "symbol": "AUDUSD",
                "side": "SELL",
                "magic": 109,
                "utc_ts": t0 + 1800,
                "entry_price": 0.65000,
                "sl_price": 0.65500,
                "lots": 0.30,
                "spread_pts": 7.0,
                "swap_usd": 0.0,
                "gross_R": -1.0,
            },
        ]
        blackbox = [
            {
                "signal_id": "S_GUARD_SPREAD",
                "symbol": "EURJPY",
                "side": "BUY",
                "magic": 103,
                "utc_ts": t0 + 601,
                "decision": "BLOCKED_BY_SPREAD",
                "block_reason": "SPREAD_42>25",
            }
        ]

        rep = forensics.classify_parity_events(expected, actual, blackbox)
        self.assertEqual(rep["verdict"], "RED_BOT_BUG_ESCALATION")
        self.assertEqual(rep["counts"][forensics.PARITY_MATCH_CLEAN], 1)
        self.assertEqual(rep["counts"][forensics.PARITY_BOT_BUG_GHOST_TRADE], 1)
        self.assertEqual(rep["counts"][forensics.PARITY_BOT_BUG_MISSED_TRADE], 1)
        self.assertEqual(rep["counts"][forensics.PARITY_LOT_OR_SL_DRIFT], 1)
        self.assertEqual(rep["counts"][forensics.PARITY_EXECUTION_FRICTION_DRIFT], 1)
        self.assertEqual(rep["counts"][forensics.PARITY_LEGITIMATE_GUARD_BLOCK], 1)
        self.assertEqual(rep["technical_bug_count"], 3)

        by_sig = {e["signal_id"]: e for e in rep["events"]}
        self.assertEqual(by_sig["S_CLEAN"]["parity_class"], forensics.PARITY_MATCH_CLEAN)
        self.assertEqual(by_sig["S_MISSED"]["parity_class"], forensics.PARITY_BOT_BUG_MISSED_TRADE)
        self.assertEqual(by_sig["S_MISSED"]["escalation"], "IMMEDIATE_FIX_REQUIRED")
        self.assertEqual(by_sig["S_GUARD_SPREAD"]["parity_class"], forensics.PARITY_LEGITIMATE_GUARD_BLOCK)
        self.assertFalse(by_sig["S_GUARD_SPREAD"]["is_technical_bug"])
        self.assertEqual(by_sig["S_LOT_DRIFT"]["parity_class"], forensics.PARITY_LOT_OR_SL_DRIFT)
        self.assertEqual(by_sig["S_LOT_DRIFT"]["escalation"], "IMMEDIATE_FIX_REQUIRED")
        self.assertEqual(by_sig["S_FRICTION"]["parity_class"], forensics.PARITY_EXECUTION_FRICTION_DRIFT)
        self.assertEqual(by_sig["S_FRICTION"]["escalation"], "ROUTE_TO_TCA")
        self.assertEqual(by_sig["GHOST_99"]["parity_class"], forensics.PARITY_BOT_BUG_GHOST_TRADE)
        self.assertEqual(by_sig["GHOST_99"]["escalation"], "IMMEDIATE_FIX_REQUIRED")

    def test_tester_parity_gate_v35_pass_and_all_fail_conditions(self) -> None:
        base_ts = 1795700000
        expected = [
            {
                "signal_id": f"T{i}",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 201,
                "utc_ts": base_ts + i * 3600,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "lots": 1.00,
                "gross_R": 1.50 if i % 2 == 0 else -1.00,
            }
            for i in range(50)
        ]
        # Clean pass: 50/50 matched within 30s (<= 1 bar), 0 ghost, 1% lot drift (<= 2%), ~1% gross_R drift (<= 5%)
        actual_pass = [
            {
                "signal_id": f"T{i}",
                "position_id": f"P{i}",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 201,
                "utc_ts": base_ts + i * 3600 + 30,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "lots": 1.01,
                "gross_R": (1.50 if i % 2 == 0 else -1.00) - 0.01,
            }
            for i in range(50)
        ]
        gate_pass = forensics.evaluate_tester_parity_gate(expected, actual_pass, bar_seconds=60.0)
        self.assertTrue(gate_pass["passed"])
        self.assertEqual(gate_pass["verdict"], "PASS")
        self.assertEqual(gate_pass["metrics"]["trade_match_rate"], 1.0)
        self.assertEqual(gate_pass["metrics"]["ghost_trades"], 0)
        self.assertLessEqual(gate_pass["metrics"]["max_lot_sl_drift"], 0.02)
        self.assertLessEqual(gate_pass["metrics"]["gross_r_drift"], 0.05)

        # Fail 1: ghost trade present
        actual_ghost = list(actual_pass) + [
            {
                "signal_id": "GHOST",
                "position_id": "PG",
                "symbol": "USDJPY",
                "side": "SELL",
                "magic": 201,
                "utc_ts": base_ts + 999_999,
                "entry_price": 150.0,
                "sl_price": 150.5,
                "lots": 1.0,
                "gross_R": -1.0,
            }
        ]
        gate_ghost = forensics.evaluate_tester_parity_gate(expected, actual_ghost, bar_seconds=60.0)
        self.assertFalse(gate_ghost["passed"])
        self.assertFalse(gate_ghost["checks"]["ghost_trades_ok"])

        # Fail 2: trade_match_rate = 48/50 = 0.96 < 0.98
        gate_missed = forensics.evaluate_tester_parity_gate(expected, actual_pass[:48], bar_seconds=60.0)
        self.assertFalse(gate_missed["passed"])
        self.assertFalse(gate_missed["checks"]["trade_match_rate_ok"])

        # Fail 3: max_lot_sl_drift = 0.03 > 0.02
        actual_drift = [dict(r) for r in actual_pass]
        actual_drift[0]["lots"] = 1.03
        gate_drift = forensics.evaluate_tester_parity_gate(expected, actual_drift, bar_seconds=60.0)
        self.assertFalse(gate_drift["passed"])
        self.assertFalse(gate_drift["checks"]["max_lot_sl_drift_ok"])

        # Fail 4: gross_r_drift > 0.05
        actual_r_drift = [dict(r, gross_R=r["gross_R"] - 0.12) for r in actual_pass]
        gate_r = forensics.evaluate_tester_parity_gate(expected, actual_r_drift, bar_seconds=60.0)
        self.assertFalse(gate_r["passed"])
        self.assertFalse(gate_r["checks"]["gross_r_drift_ok"])


class Ops6TradeGeometryAndAntiOverfitFeedbackTests(unittest.TestCase):
    def test_w1_to_l4_real_broker_tape_excursions_not_provisional(self) -> None:
        t0 = 1795700000
        # Build 6 closed trades on USDJPY (SL dist = 0.500): W1, W2, L1, L2, L3, L4
        trades: list[dict[str, Any]] = []
        ticks: list[dict[str, Any]] = []

        # 1) W1: clean BUY win (+1.5R, low MAE=0.1R)
        t_w1 = t0
        trades.append(
            {
                "position_id": "T_W1",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_w1,
                "exit_utc_ts": t_w1 + 1800,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 150.750,
                "lots": 1.0,
                "exit_reason": "TP",
                "net_R": 1.50,
                "family": "F1",
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_w1,
                points=[
                    (0, 150.000, 150.007),
                    (300, 149.950, 149.957),  # MAE = 0.10R
                    (900, 150.550, 150.557),  # Early gain > 0.7R
                    (1800, 150.750, 150.757),  # Exit +1.5R
                    (2400, 150.800, 150.807),
                ],
            )
        )

        # 2) W2: near-death BUY win (+1.0R after MAE=0.90R)
        t_w2 = t0 + 10_000
        trades.append(
            {
                "position_id": "T_W2",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_w2,
                "exit_utc_ts": t_w2 + 1800,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 150.500,
                "lots": 1.0,
                "exit_reason": "TP",
                "net_R": 1.00,
                "family": "F1",
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_w2,
                points=[
                    (0, 150.000, 150.007),
                    (300, 149.550, 149.557),  # MAE = 0.90R -> near_death -> W2
                    (1800, 150.500, 150.507),
                    (2400, 150.520, 150.527),
                ],
            )
        )

        # 3) L1: STOP_HUNTED_RIGHT_DIRECTION (SL hit at -1.0R, then post-exit broker Bid reaches +1.4R!)
        t_l1 = t0 + 20_000
        trades.append(
            {
                "position_id": "T_L1",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_l1,
                "exit_utc_ts": t_l1 + 600,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 149.500,
                "lots": 1.0,
                "exit_reason": "SL",
                "net_R": -1.00,
                "family": "F1",
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_l1,
                points=[
                    (0, 150.000, 150.007),
                    (300, 149.700, 149.707),
                    (600, 149.500, 149.507),  # SL hit
                    (1800, 150.700, 150.707),  # Post-exit rally -> post_MFE_R = 1.40R -> L1!
                ],
            )
        )

        # 4) L2: ROUND_TRIP_GIVEBACK (reached MFE = 1.1R, then reversed to SL -1.0R; no post-exit rally)
        t_l2 = t0 + 40_000
        trades.append(
            {
                "position_id": "T_L2",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_l2,
                "exit_utc_ts": t_l2 + 1800,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 149.500,
                "lots": 1.0,
                "exit_reason": "SL",
                "net_R": -1.00,
                "family": "F1",
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_l2,
                points=[
                    (0, 150.000, 150.007),
                    (600, 150.550, 150.557),  # MFE = 1.10R >= 0.80R -> L2!
                    (1800, 149.500, 149.507),  # Reversed to SL
                    (3600, 149.400, 149.407),  # Stayed below entry (post_MFE_R = 0.0)
                ],
            )
        )

        # 5) L3: EXHAUSTION_OR_CHASING_TRAP (family=F3, MFE < 0.25R, day_range_ATR=1.15 > 0.9)
        t_l3 = t0 + 60_000
        trades.append(
            {
                "position_id": "T_L3",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_l3,
                "exit_utc_ts": t_l3 + 900,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 149.500,
                "lots": 1.0,
                "exit_reason": "SL",
                "net_R": -1.00,
                "family": "F3",
                "day_range_ATR": 1.15,
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_l3,
                points=[
                    (0, 150.000, 150.007),
                    (300, 150.050, 150.057),  # MFE = 0.10R < 0.25R
                    (900, 149.500, 149.507),
                    (2400, 149.300, 149.307),
                ],
            )
        )

        # 6) L4: CLEAN_EXPECTED_LOSS
        t_l4 = t0 + 80_000
        trades.append(
            {
                "position_id": "T_L4",
                "symbol": "USDJPY",
                "side": "BUY",
                "entry_utc_ts": t_l4,
                "exit_utc_ts": t_l4 + 900,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "exit_price": 149.500,
                "lots": 1.0,
                "exit_reason": "SL",
                "net_R": -1.00,
                "family": "F1",
            }
        )
        ticks.extend(
            _make_broker_ticks_for_trade(
                "USDJPY",
                t_l4,
                points=[
                    (0, 150.000, 150.007),
                    (300, 149.800, 149.807),
                    (900, 149.500, 149.507),
                    (2400, 149.400, 149.407),
                ],
            )
        )

        m1_bars = ingestor.build_broker_m1_bars_from_quotes(ticks)
        geom = forensics.analyze_trade_geometry_on_broker_tape(trades, broker_tape_by_symbol=m1_bars)

        self.assertEqual(geom["closed_trades_analysed"], 6)
        self.assertEqual(geom["summary"]["provisional"], 0, "Real broker M1 tape MUST produce provisional=False!")

        by_key = {r["trade_key"]: r for r in geom["trades"]}
        self.assertEqual(by_key["T_W1"]["label"], "W1")
        self.assertEqual(by_key["T_W2"]["label"], "W2")
        self.assertEqual(by_key["T_L1"]["label"], "L1")
        self.assertGreaterEqual(by_key["T_L1"]["post_MFE_R"], 1.0)
        self.assertEqual(by_key["T_L2"]["label"], "L2")
        self.assertGreaterEqual(by_key["T_L2"]["MFE_R"], 0.8)
        self.assertEqual(by_key["T_L3"]["label"], "L3")
        self.assertEqual(by_key["T_L4"]["label"], "L4")

    def test_anti_overfit_hard_lock_below_30_and_hypothesis_card_emission_at_30_plus(self) -> None:
        base_ts = 1795700000

        def _build_trades_and_tape(n_total: int) -> tuple[list[dict[str, Any]], dict[str, list[dict[str, Any]]]]:
            trades_out: list[dict[str, Any]] = []
            ticks_out: list[dict[str, Any]] = []
            for i in range(n_total):
                ts = base_ts + i * 25_000
                # Mix L1 (post rally), L2 (round-trip giveback), and W1 wins
                mode = i % 3
                if mode == 0:  # L1
                    trades_out.append(
                        {
                            "signal_id": f"SIG_{i}",
                            "position_id": f"POS_{i}",
                            "symbol": "USDJPY",
                            "side": "BUY",
                            "magic": 301,
                            "entry_utc_ts": ts,
                            "exit_utc_ts": ts + 600,
                            "entry_price": 150.000,
                            "sl_price": 149.500,
                            "exit_price": 149.500,
                            "lots": 0.50,
                            "spread_pts": 7.0,
                            "swap_usd": 0.0,
                            "exit_reason": "SL",
                            "net_R": -1.0,
                            "family": "F1",
                        }
                    )
                    ticks_out.extend(
                        _make_broker_ticks_for_trade(
                            "USDJPY",
                            ts,
                            points=[(0, 150.0, 150.007), (600, 149.5, 149.507), (1800, 150.65, 150.657)],
                        )
                    )
                elif mode == 1:  # L2
                    trades_out.append(
                        {
                            "signal_id": f"SIG_{i}",
                            "position_id": f"POS_{i}",
                            "symbol": "USDJPY",
                            "side": "BUY",
                            "magic": 301,
                            "entry_utc_ts": ts,
                            "exit_utc_ts": ts + 1200,
                            "entry_price": 150.000,
                            "sl_price": 149.500,
                            "exit_price": 149.500,
                            "lots": 0.50,
                            "spread_pts": 7.0,
                            "swap_usd": 0.0,
                            "exit_reason": "SL",
                            "net_R": -1.0,
                            "family": "F1",
                        }
                    )
                    ticks_out.extend(
                        _make_broker_ticks_for_trade(
                            "USDJPY",
                            ts,
                            points=[
                                (0, 150.0, 150.007),
                                (600, 150.55, 150.557),
                                (1200, 149.5, 149.507),
                                (2400, 149.4, 149.407),
                            ],
                        )
                    )
                else:  # W1
                    trades_out.append(
                        {
                            "signal_id": f"SIG_{i}",
                            "position_id": f"POS_{i}",
                            "symbol": "USDJPY",
                            "side": "BUY",
                            "magic": 301,
                            "entry_utc_ts": ts,
                            "exit_utc_ts": ts + 1200,
                            "entry_price": 150.000,
                            "sl_price": 149.500,
                            "exit_price": 150.800,
                            "lots": 0.50,
                            "spread_pts": 7.0,
                            "swap_usd": 0.0,
                            "exit_reason": "TP",
                            "net_R": 1.6,
                            "family": "F1",
                        }
                    )
                    ticks_out.extend(
                        _make_broker_ticks_for_trade(
                            "USDJPY",
                            ts,
                            points=[
                                (0, 150.0, 150.007),
                                (300, 150.4, 150.407),
                                (1200, 150.8, 150.807),
                                (1800, 150.85, 150.857),
                            ],
                        )
                    )
            return trades_out, ingestor.build_broker_m1_bars_from_quotes(ticks_out)

        # Case A: N_live = 29 (< 30) -> HARD-LOCKED, 0 HypothesisCards, while a ghost bug STILL escalates!
        trades_29, tape_29 = _build_trades_and_tape(29)
        expected_28 = [dict(t) for t in trades_29[:28]]  # Leave trade #28 as a GHOST bug
        rep_locked = forensics.build_weekly_forensics_report(
            expected_python_trades=expected_28,
            actual_mt5_trades=trades_29,
            broker_tape_by_symbol=tape_29,
            account_alias="FTMO_DEMO_A",
            period_label="Week-1",
        )
        fb_locked = rep_locked["feedback_protocol"]
        self.assertTrue(fb_locked["parameter_change_locked"])
        self.assertFalse(fb_locked["auto_tune_permitted"])
        self.assertEqual(fb_locked["lock_status"], "HARD_LOCKED_INSUFFICIENT_LIVE_SAMPLE")
        self.assertEqual(fb_locked["remaining_trades_to_unlock"], 1)
        self.assertEqual(fb_locked["draft_hypothesis_cards"], [])
        self.assertEqual(fb_locked["technical_bug_status"], "IMMEDIATE_FIX_REQUIRED")
        self.assertEqual(rep_locked["discrepancy_diagnosis"]["classification"], "Execution TCA Bug")

        # Case B: N_live = 36 (>= 30) -> UNLOCKED for draft HypothesisCard emission
        trades_36, tape_36 = _build_trades_and_tape(36)
        with tempfile.TemporaryDirectory() as tmp:
            out_json = Path(tmp) / "weekly_forensics.json"
            rep_unlocked = forensics.build_weekly_forensics_report(
                expected_python_trades=trades_36,
                actual_mt5_trades=trades_36,
                broker_tape_by_symbol=tape_36,
                account_alias="FTMO_DEMO_A",
                period_label="Week-4",
                output_json=out_json,
            )
            self.assertTrue(out_json.is_file())
            self.assertIn("report_sha256", rep_unlocked)

        fb_open = rep_unlocked["feedback_protocol"]
        self.assertFalse(fb_open["parameter_change_locked"])
        self.assertFalse(fb_open["auto_tune_permitted"])
        self.assertEqual(fb_open["lock_status"], "UNLOCKED_DRAFT_HYPOTHESIS_ONLY")
        self.assertEqual(fb_open["sample_confidence_tier"], "MINIMUM_N30_CAUTIOUS")
        self.assertEqual(fb_open["technical_bug_status"], "CLEAN")
        self.assertEqual(rep_unlocked["discrepancy_diagnosis"]["classification"], "Normal Variance")

        cards = fb_open["draft_hypothesis_cards"]
        self.assertGreaterEqual(len(cards), 2)
        emitted_classes = {c["source_geometry_class"] for c in cards}
        self.assertIn("L1", emitted_classes)
        self.assertIn("L2", emitted_classes)
        for wrap in cards:
            self.assertEqual(wrap["validation_tag"], forensics.MUST_VALIDATE_TAG)
            self.assertTrue(wrap["live_auto_tune_forbidden"])
            self.assertTrue(wrap["holdout_untouched_required"])
            hc_dict = wrap["hypothesis_card"]
            kc_dict = hc_dict["kill_criteria"]
            rebuilt = HypothesisCard(
                hypothesis_id=hc_dict["hypothesis_id"],
                title=hc_dict["title"],
                asset_universe=tuple(hc_dict["asset_universe"]),
                timeframe=hc_dict["timeframe"],
                counterparty_mechanism=hc_dict["counterparty_mechanism"],
                economic_rationale=hc_dict["economic_rationale"],
                causal_invariants=tuple(hc_dict["causal_invariants"]),
                n_trials_cumulative=hc_dict["n_trials_cumulative"],
                kill_criteria=KillCriteria(**kc_dict),
            )
            self.assertEqual(rebuilt.validate(), [])

        # Markdown rendering check (LF-only, no bare $)
        md = forensics.render_weekly_forensics_markdown(rep_unlocked)
        self.assertNotIn("\r\n", md)
        self.assertNotIn("$", md)
        self.assertIn("MUST_VALIDATE_ON_7YR_DEV_BEFORE_CHANGE", md)

    def test_short_trade_ask_excursion_v103_blocks_sl_drift_swap_and_n50_tier(self) -> None:
        # 1) Blank swap_usd preserved as None + incomplete partial close flagged
        positions = forensics.aggregate_mt5_deals_by_position(
            [
                {
                    "utc_ts": 1795700000,
                    "symbol": "GBPUSD",
                    "side": "SELL",
                    "event_type": "ENTRY",
                    "signal_price": 1.27000,
                    "fill_price": 1.27000,
                    "sl_price": 1.27500,
                    "lots": 1.00,
                    "swap_usd": "",
                    "comment": "pos=88001",
                },
                {
                    "utc_ts": 1795701200,
                    "symbol": "GBPUSD",
                    "side": "BUY",
                    "event_type": "PARTIAL_EXIT",
                    "signal_price": 1.26500,
                    "fill_price": 1.26500,
                    "sl_price": 1.27500,
                    "lots": 0.40,
                    "swap_usd": "",
                    "comment": "pos=88001",
                },
            ]
        )
        self.assertEqual(len(positions), 1)
        self.assertIsNone(positions[0]["swap_usd"])
        self.assertTrue(positions[0]["incomplete_close"])

        # 2) SHORT trade uses executable ASK path for L1 post-SL excursion
        t0 = 1795700000
        short_trade = [
            {
                "position_id": "S_SHORT_L1",
                "symbol": "EURUSD",
                "side": "SELL",
                "entry_utc_ts": t0,
                "exit_utc_ts": t0 + 600,
                "entry_price": 1.10000,
                "sl_price": 1.10500,  # SL dist = 0.00500
                "exit_price": 1.10500,
                "lots": 0.50,
                "exit_reason": "SL",
                "net_R": -1.0,
                "family": "F1",
            }
        ]
        short_ticks = _make_broker_ticks_for_trade(
            "EURUSD",
            t0,
            points=[
                (0, 1.09996, 1.10000),
                (600, 1.10496, 1.10500),  # SL hit on Ask
                (1800, 1.09390, 1.09400),  # Ask drops +1.2R in favor of SHORT -> L1!
            ],
        )
        short_bars = ingestor.build_broker_m1_bars_from_quotes(short_ticks)
        s_geom = forensics.analyze_trade_geometry_on_broker_tape(short_trade, broker_tape_by_symbol=short_bars)
        self.assertEqual(s_geom["trades"][0]["label"], "L1")
        self.assertFalse(s_geom["trades"][0]["provisional"])
        self.assertGreaterEqual(s_geom["trades"][0]["post_MFE_R"], 1.19)

        # 3) SL distance drift > 5%, nonzero swap friction, and legacy v1.03 ORDER_BLOCKED_NEWS/SYMCAP/HEADROOM
        exp = [
            {
                "signal_id": "SL_DRIFT_1",
                "symbol": "EURUSD",
                "side": "BUY",
                "magic": 101,
                "utc_ts": t0,
                "entry_price": 1.10000,
                "sl_price": 1.09500,  # 500 pts
                "lots": 0.50,
            },
            {
                "signal_id": "SWAP_VIOL_1",
                "symbol": "GBPUSD",
                "side": "BUY",
                "magic": 102,
                "utc_ts": t0 + 300,
                "entry_price": 1.27000,
                "sl_price": 1.26500,
                "lots": 0.50,
            },
            {
                "signal_id": "V103_NEWS_1",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 103,
                "utc_ts": t0 + 600,
                "entry_price": 150.000,
                "sl_price": 149.500,
                "lots": 0.50,
            },
        ]
        act = [
            {
                "signal_id": "SL_DRIFT_1",
                "position_id": "P_SL",
                "symbol": "EURUSD",
                "side": "BUY",
                "magic": 101,
                "utc_ts": t0 + 5,
                "entry_price": 1.10000,
                "sl_price": 1.09400,  # 600 pts -> 20% SL drift > 5%!
                "lots": 0.50,
                "spread_pts": 4.0,
                "swap_usd": 0.0,
            },
            {
                "signal_id": "SWAP_VIOL_1",
                "position_id": "P_SW",
                "symbol": "GBPUSD",
                "side": "BUY",
                "magic": 102,
                "utc_ts": t0 + 302,
                "entry_price": 1.27000,
                "sl_price": 1.26500,
                "lots": 0.50,
                "spread_pts": 6.0,
                "swap_usd": -2.50,
            },
        ]
        legacy_blocks = [
            {
                "signal_id": "V103_NEWS_1",
                "symbol": "USDJPY",
                "side": "BUY",
                "magic": 103,
                "utc_ts": t0 + 601,
                "event_type": "ORDER_BLOCKED_NEWS",
                "block_reason": "US_NFP",
            }
        ]
        p_rep = forensics.classify_parity_events(exp, act, legacy_blocks)
        by_s = {e["signal_id"]: e for e in p_rep["events"]}
        self.assertEqual(by_s["SL_DRIFT_1"]["parity_class"], forensics.PARITY_LOT_OR_SL_DRIFT)
        self.assertEqual(by_s["SWAP_VIOL_1"]["parity_class"], forensics.PARITY_EXECUTION_FRICTION_DRIFT)
        self.assertEqual(by_s["SWAP_VIOL_1"]["severity"], "RED")
        self.assertEqual(by_s["V103_NEWS_1"]["parity_class"], forensics.PARITY_LEGITIMATE_GUARD_BLOCK)
        self.assertEqual(p_rep["counts"][forensics.PARITY_BOT_BUG_MISSED_TRADE], 0)

        # 4) Anti-overfit hard floor rejection (< 30 forbidden) and N >= 50 RECOMMENDED tier
        with self.assertRaises(ValueError):
            forensics.evaluate_anti_overfit_feedback(p_rep, s_geom, min_live_trades=15)
        fake_geom_52 = {
            "summary": {
                "trades": 52,
                "overlapping_loss_flags": {
                    "L1": {"count": 5, "loss_R": 5.0},
                    "L2": {"count": 0, "loss_R": 0.0},
                    "L3": {"count": 3, "loss_R": 3.0},
                },
            },
            "trades": [{"canonical_symbol": "US100"}],
        }
        fb52 = forensics.evaluate_anti_overfit_feedback(
            {"counts": {}}, fake_geom_52, account_alias="FTMO_DEMO", period_label="Month-1"
        )
        self.assertEqual(fb52["sample_confidence_tier"], "RECOMMENDED_N50_PLUS")
        self.assertEqual({c["source_geometry_class"] for c in fb52["draft_hypothesis_cards"]}, {"L1", "L3"})

    def test_info_01_corrupt_blackbox_jsonl_and_info_02_strict_int_min_live_trades(self) -> None:
        # INFO-01: Corrupt 1-line or trailing JSONL line MUST raise ValueError (NEVER silently drop to [])
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            corrupt_single = root / "naqex_decision_blackbox_20261127.jsonl"
            corrupt_single.write_text("NOT_JSON_CORRUPT_PAYLOAD\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(corrupt_single)

            truncated_single = root / "naqex_decision_blackbox_20261128.jsonl"
            truncated_single.write_text('{"symbol":"EURUSD","decision":"FIRE"', encoding="utf-8")
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(truncated_single)

            valid_line = json.dumps(
                {
                    "signal_id": "SIG_OK",
                    "symbol": "EURUSD",
                    "side": "BUY",
                    "utc_ts": 1795700000,
                    "decision": "FIRE",
                }
            )
            corrupt_tail = root / "naqex_decision_blackbox_20261129.jsonl"
            corrupt_tail.write_text(valid_line + "\nCORRUPT_LINE\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(corrupt_tail)
            # Even with allow_truncated_tail=True, non-JSON garbage still raises ValueError
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(corrupt_tail, allow_truncated_tail=True)

            # Opt-in allow_truncated_tail=True tolerates ONLY an unterminated trailing '{...' line
            mid_write = root / "naqex_decision_blackbox_20261130.jsonl"
            mid_write.write_text(valid_line + '\n{"signal_id":"PARTIAL', encoding="utf-8")
            with self.assertRaises(ValueError):
                forensics.load_decision_blackbox_jsonl(mid_write)
            tolerated = forensics.load_decision_blackbox_jsonl(mid_write, allow_truncated_tail=True)
            self.assertEqual(len(tolerated), 1)
            self.assertEqual(tolerated[0]["signal_id"], "SIG_OK")

        # INFO-02: min_live_trades & int gates MUST be strict positive int (reject NaN, Inf, bool, float, str)
        fake_geom_35 = {
            "summary": {"trades": 35, "overlapping_loss_flags": {"L1": {"count": 5, "loss_R": 5.0}}},
            "trades": [{"canonical_symbol": "USDJPY"}],
        }
        for bad_min in (float("nan"), float("inf"), float("-inf"), True, False, 30.0, "30", None, -1, 0, 29):
            with self.assertRaises(ValueError, msg=f"min_live_trades={bad_min!r} must raise ValueError"):
                forensics.evaluate_anti_overfit_feedback(
                    {"counts": {}},
                    fake_geom_35,
                    min_live_trades=bad_min,  # type: ignore[arg-type]
                )
        for bad_rec in (float("nan"), True, False, 50.0, 10):
            with self.assertRaises(ValueError, msg=f"recommended_live_trades={bad_rec!r} must raise ValueError"):
                forensics.evaluate_anti_overfit_feedback(
                    {"counts": {}},
                    fake_geom_35,
                    recommended_live_trades=bad_rec,  # type: ignore[arg-type]
                )
        for bad_pat in (True, False, 0, -2, 2.0):
            with self.assertRaises(ValueError, msg=f"min_pattern_count={bad_pat!r} must raise ValueError"):
                forensics.evaluate_anti_overfit_feedback(
                    {"counts": {}},
                    fake_geom_35,
                    min_pattern_count=bad_pat,  # type: ignore[arg-type]
                )
        for bad_trials in (True, False, 0, -1, 1.5):
            with self.assertRaises(ValueError, msg=f"n_trials_cumulative={bad_trials!r} must raise ValueError"):
                forensics.evaluate_anti_overfit_feedback(
                    {"counts": {}},
                    fake_geom_35,
                    n_trials_cumulative=bad_trials,  # type: ignore[arg-type]
                )


if __name__ == "__main__":
    unittest.main()
