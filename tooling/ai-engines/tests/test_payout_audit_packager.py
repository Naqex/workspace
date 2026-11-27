"""Tests for OPS-5 Immutable Payout Audit Trail Packager & Go-Live Master Runbook.

Covers:
  1. Clean bundle certification & independent SHA-256 hash-chain verification.
  2. Tamper detection (artifact byte edit, manifest edit, extra unindexed file) & immutability.
  3. Fail-closed rejection on:
     - Missing or wrong-side hard SL (`hard_sl_attached_pct < 100%`)
     - Concurrent same-symbol/magic grid stacking (`zero_grid_verified == False`)
     - Loss-conditioned martingale lot doubling (`zero_martingale_verified == False`)
     - Sub-threshold HFT / tick scalping duration (`zero_hft_tick_scalping == False`)
     - Red-news `+-120s` hard-ban breach (`red_news_ban_clean == False`)
     - Reconciliation orphan trade or mismatched audit CSV SHA-256
  4. Strict Layer-1 OPSEC redaction (`redact_for_layer1=True`) hiding logins, tickets, IPs,
     and Windows user paths while keeping hash-chain verification 100% valid.
  5. Architecture safety invariants (`ORDER_SEND_CAPABLE=False`, `ORDER_SEND_COUNT=0`,
     zero `MetaTrader5` imports, zero bare `assert` statements in `payout_audit_packager.py`).
  6. Markdown compliance audit on `GO-LIVE-END-TO-END-RUNBOOK.md` (LF-only, 0 bare `$`,
     0 forbidden G12 FTMO/The5ers support-contact strings, 0 real IPs, all required tools/gates).
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import re
import sys
import tempfile
import unittest
from pathlib import Path

TESTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = TESTS_DIR.parent
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.red_news import RedNewsEvent  # noqa: E402
from quant_factory.daily_statement_reconciler import reconcile_daily_statement  # noqa: E402
from quant_factory.live_ops import payout_audit_packager as packager  # noqa: E402

PACKAGER_PATH = AI_ENGINES_DIR / "quant_factory" / "live_ops" / "payout_audit_packager.py"
RUNBOOK_PATH = AI_ENGINES_DIR / "exports" / "deployment_kit" / "GO-LIVE-END-TO-END-RUNBOOK.md"

_AUDIT_COLUMNS = [
    "utc_ts",
    "magic",
    "engine_id",
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
    "account_login",
    "deal_id",
    "order_id",
    "position_id",
    "ticket",
    "comment",
]

_STMT_COLUMNS = [
    "time",
    "deal_id",
    "ticket",
    "order_id",
    "position_id",
    "magic",
    "account_login",
    "symbol",
    "side",
    "direction",
    "volume",
    "price",
    "profit",
    "swap",
    "commission",
    "comment",
]


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_clean_cycle_fixture(
    tmp: Path,
    *,
    login: int = 55112233,
    extra_comment: str = "",
) -> dict[str, Path]:
    """Create a realistic clean 2-trade cycle + matching statement receipt + blackbox + preset + fake ex5."""
    t0 = 1794042000  # 2026-11-06T09:00:00Z
    audit_rows: list[dict[str, object]] = [
        # Trade 1: EURUSD BUY, losing trade (-50 USD), held 900s, valid SL below entry
        {
            "utc_ts": t0,
            "magic": 20261122,
            "engine_id": "E1",
            "symbol": "EURUSD",
            "side": "BUY",
            "event_type": "ENTRY",
            "signal_price": 1.08500,
            "fill_price": 1.08502,
            "sl_price": 1.08300,
            "lots": 0.25,
            "spread_pts": 4.0,
            "latency_ms": 22.0,
            "retcode": 10009,
            "pnl_usd": 0.0,
            "swap_usd": 0.0,
            "commission_usd": -1.25,
            "account_login": login,
            "deal_id": "9001001",
            "order_id": "8001001",
            "position_id": "7001001",
            "ticket": "9001001",
            "comment": f"deal=9001001 pos=7001001 {extra_comment}".strip(),
        },
        {
            "utc_ts": t0 + 900,
            "magic": 20261122,
            "engine_id": "E1",
            "symbol": "EURUSD",
            "side": "SELL",
            "event_type": "SL_HIT",
            "signal_price": 1.08300,
            "fill_price": 1.08300,
            "sl_price": 1.08300,
            "lots": 0.25,
            "spread_pts": 4.0,
            "latency_ms": 18.0,
            "retcode": 10009,
            "pnl_usd": -50.0,
            "swap_usd": 0.0,
            "commission_usd": -1.25,
            "account_login": login,
            "deal_id": "9001002",
            "order_id": "8001002",
            "position_id": "7001001",
            "ticket": "9001002",
            "comment": "deal=9001002 pos=7001001",
        },
        # Trade 2: EURUSD SELL after Trade 1 closed, same 0.25 lots (no martingale!), held 1200s, valid SL above entry
        {
            "utc_ts": t0 + 3600,
            "magic": 20261122,
            "engine_id": "E1",
            "symbol": "EURUSD",
            "side": "SELL",
            "event_type": "ENTRY",
            "signal_price": 1.08400,
            "fill_price": 1.08398,
            "sl_price": 1.08600,
            "lots": 0.25,
            "spread_pts": 4.0,
            "latency_ms": 20.0,
            "retcode": 10009,
            "pnl_usd": 0.0,
            "swap_usd": 0.0,
            "commission_usd": -1.25,
            "account_login": login,
            "deal_id": "9001003",
            "order_id": "8001003",
            "position_id": "7001002",
            "ticket": "9001003",
            "comment": "deal=9001003 pos=7001002",
        },
        {
            "utc_ts": t0 + 4800,
            "magic": 20261122,
            "engine_id": "E1",
            "symbol": "EURUSD",
            "side": "BUY",
            "event_type": "TP_HIT",
            "signal_price": 1.08000,
            "fill_price": 1.08000,
            "sl_price": 1.08600,
            "lots": 0.25,
            "spread_pts": 4.0,
            "latency_ms": 19.0,
            "retcode": 10009,
            "pnl_usd": 100.0,
            "swap_usd": 0.0,
            "commission_usd": -1.25,
            "account_login": login,
            "deal_id": "9001004",
            "order_id": "8001004",
            "position_id": "7001002",
            "ticket": "9001004",
            "comment": "deal=9001004 pos=7001002",
        },
    ]

    stmt_rows: list[dict[str, object]] = []
    for r in audit_rows:
        direction = "IN" if r["event_type"] == "ENTRY" else "OUT"
        stmt_rows.append(
            {
                "time": r["utc_ts"],
                "deal_id": r["deal_id"],
                "ticket": r["ticket"],
                "order_id": r["order_id"],
                "position_id": r["position_id"],
                "magic": r["magic"],
                "account_login": login,
                "symbol": r["symbol"],
                "side": r["side"],
                "direction": direction,
                "volume": r["lots"],
                "price": r["fill_price"],
                "profit": r["pnl_usd"],
                "swap": r["swap_usd"],
                "commission": r["commission_usd"],
                "comment": r["comment"],
            }
        )

    audit_csv = tmp / "naqex_exec_audit.csv"
    stmt_csv = tmp / "statement.csv"
    receipt_json = tmp / "reconcile_receipt.json"
    _write_csv(audit_csv, _AUDIT_COLUMNS, audit_rows)
    _write_csv(stmt_csv, _STMT_COLUMNS, stmt_rows)

    reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_csv,
        expected_login=login,
        out_json=receipt_json,
    )

    blackbox_dir = tmp / "blackbox"
    blackbox_dir.mkdir(parents=True, exist_ok=True)
    bb_file = blackbox_dir / "naqex_decision_blackbox_20261106.jsonl"
    bb_lines = [
        json.dumps(
            {
                "signal_id": "SIG-001",
                "magic": 20261122,
                "position_id": "7001001",
                "symbol": "EURUSD",
                "decision": "FIRE",
                "strategy_sha": "a" * 64,
                "preset_sha": "b" * 64,
            }
        ),
        json.dumps(
            {
                "signal_id": "SIG-002",
                "magic": 20261122,
                "position_id": "",
                "symbol": "EURUSD",
                "decision": "BLOCKED_BY_SPREAD",
                "strategy_sha": "a" * 64,
                "preset_sha": "b" * 64,
            }
        ),
    ]
    bb_file.write_text("\n".join(bb_lines) + "\n", encoding="utf-8", newline="\n")

    preset_file = tmp / "FTMO_Funded_1x.set"
    preset_file.write_text(
        "; Clean Funded Preset\n"
        "InpContractSku=FTMO_STD_10K_FUNDED_SAFE_1X\n"
        "InpBasePhaseMult=1.00\n"
        "InpAllowManualHaltFile=true\n"
        "InpGuardEnableRedNews=true\n"
        "InpGuardNewsHardBanSec=135\n",
        encoding="utf-8",
        newline="\n",
    )

    ex5_file = tmp / "Naqex_Master_Prop7E.ex5"
    ex5_file.write_bytes(b"FAKE-EX5-BINARY-CONTENT-FOR-SHA256-TEST-ONLY")

    return {
        "audit_csv": audit_csv,
        "stmt_csv": stmt_csv,
        "receipt_json": receipt_json,
        "blackbox_dir": blackbox_dir,
        "preset_file": preset_file,
        "ex5_file": ex5_file,
    }


def _reconcile_modified_audit(
    tmp: Path,
    audit_rows: list[dict[str, object]],
    *,
    login: int = 55112233,
) -> tuple[Path, Path]:
    audit_csv = tmp / "naqex_exec_audit.csv"
    stmt_csv = tmp / "statement.csv"
    receipt_json = tmp / "reconcile_receipt.json"
    _write_csv(audit_csv, _AUDIT_COLUMNS, audit_rows)
    stmt_rows = [
        {
            "time": r["utc_ts"],
            "deal_id": r["deal_id"],
            "ticket": r["ticket"],
            "order_id": r["order_id"],
            "position_id": r["position_id"],
            "magic": r["magic"],
            "account_login": login,
            "symbol": r["symbol"],
            "side": r["side"],
            "direction": "IN" if r["event_type"] == "ENTRY" else "OUT",
            "volume": r["lots"],
            "price": r["fill_price"],
            "profit": r["pnl_usd"],
            "swap": r["swap_usd"],
            "commission": r["commission_usd"],
            "comment": r["comment"],
        }
        for r in audit_rows
    ]
    _write_csv(stmt_csv, _STMT_COLUMNS, stmt_rows)
    reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_csv,
        expected_login=login,
        out_json=receipt_json,
    )
    return audit_csv, receipt_json


class PayoutAuditPackagerTests(unittest.TestCase):
    def test_clean_bundle_certification_and_hash_chain_verification(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = _build_clean_cycle_fixture(tmp)
            # Distant red news event (not overlapping trades)
            far_news = [
                RedNewsEvent(
                    utc_ts=1794060000,
                    utc_iso="2026-11-06T14:00:00Z",
                    utc_day="2026-11-06",
                    ccy="USD",
                    event="NFP",
                )
            ]
            bundle_dir = tmp / "bundle_clean"
            manifest = packager.package_payout_audit_bundle(
                output_dir=bundle_dir,
                cycle_id="cycle_2026_11_p1",
                audit_csv=fx["audit_csv"],
                reconcile_receipt_json=fx["receipt_json"],
                decision_blackbox_path=fx["blackbox_dir"],
                set_preset_path=fx["preset_file"],
                ex5_path=fx["ex5_file"],
                red_news_events=far_news,
                firm_profile="FTMO_STANDARD",
                account_phase="FUNDED",
                account_alias="FTMO_FUNDED_10K",
                redact_for_layer1=True,
                created_utc="2026-11-07T00:00:00Z",
            )

            self.assertTrue(manifest["certified"])
            self.assertTrue(manifest["payout_ready"])
            self.assertEqual(manifest["verdict"], "CERTIFIED")
            self.assertEqual(manifest["fail_reasons"], [])
            self.assertEqual(manifest["order_send_count"], 0)
            self.assertFalse(manifest["order_send_capable"])

            ca = manifest["compliance_assertions"]
            self.assertEqual(ca["hard_sl_attached_pct"], 100.0)
            self.assertTrue(ca["hard_sl_verified"])
            self.assertTrue(ca["zero_grid_verified"])
            self.assertTrue(ca["zero_martingale_verified"])
            self.assertTrue(ca["zero_hft_tick_scalping"])
            self.assertTrue(ca["red_news_ban_clean"])
            self.assertEqual(ca["reconciliation_orphan_count"], 0)
            self.assertTrue(ca["reconciliation_verified"])

            # Verify ex5 & preset SHA-256 recorded accurately
            self.assertEqual(
                manifest["provenance"]["ex5_sha256"],
                hashlib.sha256(fx["ex5_file"].read_bytes()).hexdigest(),
            )
            self.assertEqual(
                manifest["provenance"]["preset_sha256"],
                hashlib.sha256(fx["preset_file"].read_bytes()).hexdigest(),
            )
            self.assertEqual(manifest["hash_chain_spec"]["artifact_count"], 6)

            # Independent hash-chain verification passes
            ver = packager.verify_payout_audit_bundle(bundle_dir)
            self.assertTrue(ver["verified"])
            self.assertTrue(ver["integrity_ok"])
            self.assertTrue(ver["manifest_sha_valid"])
            self.assertTrue(ver["hash_chain_valid"])
            self.assertTrue(ver["certified"])
            self.assertEqual(ver["errors"], [])

            # Immutability: refusing to overwrite an existing bundle directory
            with self.assertRaises(FileExistsError):
                packager.package_payout_audit_bundle(
                    output_dir=bundle_dir,
                    cycle_id="cycle_2026_11_p1",
                    audit_csv=fx["audit_csv"],
                    reconcile_receipt_json=fx["receipt_json"],
                    red_news_events=far_news,
                )

            # Tamper test 1: modify 1 byte in an artifact -> fails closed!
            cert_art = bundle_dir / "artifacts" / "compliance_certification.json"
            orig_bytes = cert_art.read_bytes()
            cert_art.write_bytes(orig_bytes + b" ")
            tampered = packager.verify_payout_audit_bundle(bundle_dir)
            self.assertFalse(tampered["verified"])
            self.assertFalse(tampered["hash_chain_valid"])
            self.assertTrue(any("ARTIFACT_SHA256_MISMATCH" in e for e in tampered["errors"]))

            # Restore and Tamper test 2: inject extra unindexed file
            cert_art.write_bytes(orig_bytes)
            extra = bundle_dir / "artifacts" / "injected.txt"
            extra.write_text("tamper\n", encoding="utf-8")
            tampered_extra = packager.verify_payout_audit_bundle(bundle_dir)
            self.assertFalse(tampered_extra["verified"])
            self.assertTrue(any("UNEXPECTED_EXTRA_ARTIFACT" in e for e in tampered_extra["errors"]))

    def test_fail_closed_missing_sl_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            t0 = 1794042000
            rows: list[dict[str, object]] = [
                {
                    "utc_ts": t0,
                    "magic": 20261122,
                    "engine_id": "E1",
                    "symbol": "EURUSD",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 1.08500,
                    "fill_price": 1.08500,
                    "sl_price": 0.0,  # MISSING HARD SL!
                    "lots": 0.25,
                    "spread_pts": 4.0,
                    "latency_ms": 20.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -1.25,
                    "account_login": 55112233,
                    "deal_id": "101",
                    "order_id": "201",
                    "position_id": "301",
                    "ticket": "101",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 600,
                    "magic": 20261122,
                    "engine_id": "E1",
                    "symbol": "EURUSD",
                    "side": "SELL",
                    "event_type": "EXIT",
                    "signal_price": 1.08600,
                    "fill_price": 1.08600,
                    "sl_price": 0.0,
                    "lots": 0.25,
                    "spread_pts": 4.0,
                    "latency_ms": 20.0,
                    "retcode": 10009,
                    "pnl_usd": 25.0,
                    "swap_usd": 0.0,
                    "commission_usd": -1.25,
                    "account_login": 55112233,
                    "deal_id": "102",
                    "order_id": "202",
                    "position_id": "301",
                    "ticket": "102",
                    "comment": "",
                },
            ]
            audit_csv, receipt_json = _reconcile_modified_audit(tmp, rows)
            manifest = packager.package_payout_audit_bundle(
                output_dir=tmp / "bundle_no_sl",
                cycle_id="cycle_no_sl",
                audit_csv=audit_csv,
                reconcile_receipt_json=receipt_json,
                red_news_events=[],
            )
            self.assertFalse(manifest["certified"])
            self.assertEqual(manifest["verdict"], "REJECTED_FAIL_CLOSED")
            self.assertEqual(manifest["compliance_assertions"]["hard_sl_attached_pct"], 0.0)
            self.assertFalse(manifest["compliance_assertions"]["hard_sl_verified"])
            self.assertTrue(any("MISSING_OR_INVALID_HARD_SL" in r for r in manifest["fail_reasons"]))

            # Strict verifier rejects uncertified bundle by default, while integrity_only still validates chain
            ver_strict = packager.verify_payout_audit_bundle(tmp / "bundle_no_sl", require_certified=True)
            self.assertFalse(ver_strict["verified"])
            self.assertIn("BUNDLE_NOT_CERTIFIED", ver_strict["errors"])
            ver_int = packager.verify_payout_audit_bundle(tmp / "bundle_no_sl", require_certified=False)
            self.assertTrue(ver_int["verified"])
            self.assertTrue(ver_int["integrity_ok"])

    def test_fail_closed_martingale_lot_jump_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            t0 = 1794042000
            rows: list[dict[str, object]] = [
                # Trade 1: 0.10 lot loss
                {
                    "utc_ts": t0,
                    "magic": 20261123,
                    "engine_id": "E2",
                    "symbol": "USDJPY",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 150.000,
                    "fill_price": 150.000,
                    "sl_price": 149.500,
                    "lots": 0.10,
                    "spread_pts": 7.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "401",
                    "order_id": "501",
                    "position_id": "601",
                    "ticket": "401",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 900,
                    "magic": 20261123,
                    "engine_id": "E2",
                    "symbol": "USDJPY",
                    "side": "SELL",
                    "event_type": "SL_HIT",
                    "signal_price": 149.500,
                    "fill_price": 149.500,
                    "sl_price": 149.500,
                    "lots": 0.10,
                    "spread_pts": 7.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": -33.3,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "402",
                    "order_id": "502",
                    "position_id": "601",
                    "ticket": "402",
                    "comment": "",
                },
                # Trade 2: immediately doubles lots to 0.20 after loss -> MARTINGALE!
                {
                    "utc_ts": t0 + 1800,
                    "magic": 20261123,
                    "engine_id": "E2",
                    "symbol": "USDJPY",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 149.600,
                    "fill_price": 149.600,
                    "sl_price": 149.100,
                    "lots": 0.20,
                    "spread_pts": 7.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -1.0,
                    "account_login": 55112233,
                    "deal_id": "403",
                    "order_id": "503",
                    "position_id": "602",
                    "ticket": "403",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 2700,
                    "magic": 20261123,
                    "engine_id": "E2",
                    "symbol": "USDJPY",
                    "side": "SELL",
                    "event_type": "TP_HIT",
                    "signal_price": 150.200,
                    "fill_price": 150.200,
                    "sl_price": 149.100,
                    "lots": 0.20,
                    "spread_pts": 7.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 80.0,
                    "swap_usd": 0.0,
                    "commission_usd": -1.0,
                    "account_login": 55112233,
                    "deal_id": "404",
                    "order_id": "504",
                    "position_id": "602",
                    "ticket": "404",
                    "comment": "",
                },
            ]
            audit_csv, receipt_json = _reconcile_modified_audit(tmp, rows)
            with self.assertRaises(packager.PayoutComplianceError):
                packager.package_payout_audit_bundle(
                    output_dir=tmp / "bundle_martingale",
                    cycle_id="cycle_martingale",
                    audit_csv=audit_csv,
                    reconcile_receipt_json=receipt_json,
                    red_news_events=[],
                    raise_on_failure=True,
                )
            manifest_path = tmp / "bundle_martingale" / "payout_audit_manifest.json"
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            self.assertFalse(manifest["certified"])
            self.assertFalse(manifest["compliance_assertions"]["zero_martingale_verified"])
            self.assertTrue(any("MARTINGALE_LOT_JUMP_DETECTED" in r for r in manifest["fail_reasons"]))

    def test_fail_closed_grid_hft_red_news_and_orphan_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            t0 = 1794042000
            # Two overlapping positions on same symbol/magic (GRID) + 20s duration (HFT) + fill 30s after USD NFP!
            rows: list[dict[str, object]] = [
                {
                    "utc_ts": t0,
                    "magic": 20261125,
                    "engine_id": "E3",
                    "symbol": "GBPUSD",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 1.27000,
                    "fill_price": 1.27000,
                    "sl_price": 1.26800,
                    "lots": 0.10,
                    "spread_pts": 6.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "701",
                    "order_id": "801",
                    "position_id": "901",
                    "ticket": "701",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 10,  # Second simultaneous position -> GRID!
                    "magic": 20261125,
                    "engine_id": "E3",
                    "symbol": "GBPUSD",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 1.26950,
                    "fill_price": 1.26950,
                    "sl_price": 1.26750,
                    "lots": 0.10,
                    "spread_pts": 6.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "702",
                    "order_id": "802",
                    "position_id": "902",
                    "ticket": "702",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 20,  # Closed after 20s (< 60s) -> HFT TICK SCALP!
                    "magic": 20261125,
                    "engine_id": "E3",
                    "symbol": "GBPUSD",
                    "side": "SELL",
                    "event_type": "EXIT",
                    "signal_price": 1.27050,
                    "fill_price": 1.27050,
                    "sl_price": 1.26800,
                    "lots": 0.10,
                    "spread_pts": 6.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 5.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "703",
                    "order_id": "803",
                    "position_id": "901",
                    "ticket": "703",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 120,
                    "magic": 20261125,
                    "engine_id": "E3",
                    "symbol": "GBPUSD",
                    "side": "SELL",
                    "event_type": "EXIT",
                    "signal_price": 1.27020,
                    "fill_price": 1.27020,
                    "sl_price": 1.26750,
                    "lots": 0.10,
                    "spread_pts": 6.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 7.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "704",
                    "order_id": "804",
                    "position_id": "902",
                    "ticket": "704",
                    "comment": "",
                },
            ]
            audit_csv = tmp / "naqex_exec_audit.csv"
            stmt_csv = tmp / "statement.csv"
            receipt_json = tmp / "reconcile_receipt.json"
            _write_csv(audit_csv, _AUDIT_COLUMNS, rows)
            # Drop last row from statement so reconciliation has 1 ORPHAN audit trade!
            stmt_rows = [
                {
                    "time": r["utc_ts"],
                    "deal_id": r["deal_id"],
                    "ticket": r["ticket"],
                    "order_id": r["order_id"],
                    "position_id": r["position_id"],
                    "magic": r["magic"],
                    "account_login": 55112233,
                    "symbol": r["symbol"],
                    "side": r["side"],
                    "direction": "IN" if r["event_type"] == "ENTRY" else "OUT",
                    "volume": r["lots"],
                    "price": r["fill_price"],
                    "profit": r["pnl_usd"],
                    "swap": r["swap_usd"],
                    "commission": r["commission_usd"],
                    "comment": r["comment"],
                }
                for r in rows[:-1]
            ]
            _write_csv(stmt_csv, _STMT_COLUMNS, stmt_rows)
            reconcile_daily_statement(
                audit_csv=audit_csv,
                statement_path=stmt_csv,
                expected_login=55112233,
                out_json=receipt_json,
            )

            close_news = [
                RedNewsEvent(
                    utc_ts=t0 + 30,  # Within +-120s of GBPUSD fills!
                    utc_iso="2026-11-06T09:00:30Z",
                    utc_day="2026-11-06",
                    ccy="USD",
                    event="US_CPI",
                )
            ]

            manifest = packager.package_payout_audit_bundle(
                output_dir=tmp / "bundle_multi_fail",
                cycle_id="cycle_multi_fail",
                audit_csv=audit_csv,
                reconcile_receipt_json=receipt_json,
                red_news_events=close_news,
            )
            self.assertFalse(manifest["certified"])
            ca = manifest["compliance_assertions"]
            self.assertFalse(ca["zero_grid_verified"])
            self.assertFalse(ca["zero_hft_tick_scalping"])
            self.assertFalse(ca["red_news_ban_clean"])
            self.assertGreaterEqual(ca["reconciliation_orphan_count"], 1)
            self.assertFalse(ca["reconciliation_verified"])

    def test_opsec_redaction_strips_logins_tickets_ips_and_user_paths(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            synthetic_ip = "203.0." + "113.42"
            synthetic_user_path = "C:" + "\\Users\\" + "Alice\\Desktop\\notes.txt"
            fx = _build_clean_cycle_fixture(
                tmp,
                login=55112233,
                extra_comment=f"host={synthetic_ip} path={synthetic_user_path}",
            )
            bundle_dir = tmp / "bundle_redacted"
            manifest = packager.package_payout_audit_bundle(
                output_dir=bundle_dir,
                cycle_id="cycle_redacted_01",
                audit_csv=fx["audit_csv"],
                reconcile_receipt_json=fx["receipt_json"],
                decision_blackbox_path=fx["blackbox_dir"],
                set_preset_path=fx["preset_file"],
                ex5_path=fx["ex5_file"],
                red_news_events=[],
                account_alias=f"Node-{synthetic_ip}",
                redact_for_layer1=True,
            )
            self.assertTrue(manifest["certified"])
            self.assertTrue(manifest["redacted_for_layer1"])

            # Scan EVERY file in the packaged bundle for zero raw login/ticket/IP/user path leaks
            for file_path in sorted(bundle_dir.rglob("*")):
                if not file_path.is_file():
                    continue
                content = file_path.read_text(encoding="utf-8")
                self.assertNotIn("55112233", content, f"Raw login leaked in {file_path.name}")
                self.assertNotIn("9001001", content, f"Raw deal_id leaked in {file_path.name}")
                self.assertNotIn("7001001", content, f"Raw position_id leaked in {file_path.name}")
                self.assertNotIn(synthetic_ip, content, f"Raw IP leaked in {file_path.name}")
                self.assertNotIn("Alice", content, f"Windows user path leaked in {file_path.name}")

            # Verification still passes 100% on redacted bundle
            ver = packager.verify_payout_audit_bundle(bundle_dir)
            self.assertTrue(ver["verified"])

    def test_cli_package_and_verify_exit_codes(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = _build_clean_cycle_fixture(tmp)
            bundle_dir = tmp / "bundle_cli"

            rc_pkg = packager.main(
                [
                    "package",
                    "--output-dir",
                    str(bundle_dir),
                    "--cycle-id",
                    "cycle_cli_01",
                    "--audit-csv",
                    str(fx["audit_csv"]),
                    "--reconcile-receipt",
                    str(fx["receipt_json"]),
                    "--set-preset",
                    str(fx["preset_file"]),
                    "--ex5-path",
                    str(fx["ex5_file"]),
                ]
            )
            self.assertEqual(rc_pkg, 0)

            rc_ver = packager.main(["verify", "--bundle-dir", str(bundle_dir)])
            self.assertEqual(rc_ver, 0)

    def test_architecture_invariants_zero_asserts_and_readonly(self) -> None:
        self.assertFalse(packager.ORDER_SEND_CAPABLE)
        self.assertEqual(packager.ORDER_SEND_COUNT, 0)

        source = PACKAGER_PATH.read_text(encoding="utf-8")
        self.assertNotIn("\r", source, "payout_audit_packager.py must be LF-only")

        tree = ast.parse(source)
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        self.assertEqual(bare_asserts, [], f"Bare assert forbidden in quant_factory/: lines {bare_asserts}")

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom) and node.module:
                imported_names.add(node.module)
        self.assertFalse(
            any("metatrader5" in name.lower() for name in imported_names),
            f"MetaTrader5 import strictly forbidden: {imported_names}",
        )

    def test_go_live_master_runbook_markdown_opsec_and_g12_compliance(self) -> None:
        self.assertTrue(RUNBOOK_PATH.is_file(), f"Missing Master Runbook: {RUNBOOK_PATH}")
        raw = RUNBOOK_PATH.read_bytes()
        self.assertNotIn(b"\r", raw, "GO-LIVE-END-TO-END-RUNBOOK.md MUST be LF-only (0 CRLF)")

        text = raw.decode("utf-8")
        self.assertNotIn("$", text, "GO-LIVE-END-TO-END-RUNBOOK.md MUST contain 0 bare '$' signs")

        # G12 PERMANENT OWNER RULE: zero mentions of emailing/contacting/Live-Chatting FTMO / The5ers / prop support
        g12_forbidden_patterns = (
            re.compile(r"live[\s-]*chat", re.IGNORECASE),
            re.compile(
                r"(?:email|contact|message|write|nhắn|liên hệ|gửi\s*mail|gửi\s*email)"
                r".{0,40}(?:ftmo|the5ers|support|hỗ\s*trợ)",
                re.IGNORECASE,
            ),
            re.compile(r"(?:ftmo|the5ers|prop\s*firm).{0,30}(?:support|email|live[\s-]*chat|clearance)", re.IGNORECASE),
            re.compile(r"support\s+ticket|written\s+clearance|ea\s+clearance", re.IGNORECASE),
        )
        for rx in g12_forbidden_patterns:
            match = rx.search(text)
            self.assertIsNone(match, f"G12 violation in runbook: {match.group(0) if match else ''!r}")

        # Zero real private LAN or Tailscale IPs (only RFC 6598 CIDR literal 100.64.0.0/10 allowed)
        self.assertIsNone(re.search(r"\b192\.168\.\d{1,3}\.\d{1,3}\b", text))
        for m_ts in re.finditer(r"\b100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}\b", text):
            self.assertEqual(text[m_ts.start() : m_ts.end() + 3], "100.64.0.0/10")

        # Zero `uv run` in root commands
        self.assertNotIn("uv run", text)

        # Required tool references & operational gates present
        for required_token in (
            "ftmo_pre_checkout_guard.py",
            "node_ctl.py",
            "node_cutover_dryrun.py",
            "node_weekly_digest.py",
            "hardening_v3/",
            "account_phase_preflight.py",
            "daily_live_ops_pipeline.py",
            "live_parity_forensics.py",
            "payout_audit_packager.py",
            "prop_terms_auditor.py",
            "InpAllowManualHaltFile=true",
            "98%",
            "10–14",
            "4–5",
            "45%",
            "120s",
            "20 GB",
            "MATCH_CLEAN",
            "W1..L4",
        ):
            self.assertIn(required_token, text, f"Runbook missing required token: {required_token}")

    def test_fail_closed_wrong_side_sl_and_receipt_sha_mismatch(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            t0 = 1794042000
            rows: list[dict[str, object]] = [
                {
                    "utc_ts": t0,
                    "magic": 20261122,
                    "engine_id": "E1",
                    "symbol": "EURUSD",
                    "side": "BUY",
                    "event_type": "ENTRY",
                    "signal_price": 1.08500,
                    "fill_price": 1.08500,
                    "sl_price": 1.08700,  # WRONG SIDE: BUY SL above entry!
                    "lots": 0.10,
                    "spread_pts": 4.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 0.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "1101",
                    "order_id": "1201",
                    "position_id": "1301",
                    "ticket": "1101",
                    "comment": "",
                },
                {
                    "utc_ts": t0 + 600,
                    "magic": 20261122,
                    "engine_id": "E1",
                    "symbol": "EURUSD",
                    "side": "SELL",
                    "event_type": "EXIT",
                    "signal_price": 1.08600,
                    "fill_price": 1.08600,
                    "sl_price": 1.08700,
                    "lots": 0.10,
                    "spread_pts": 4.0,
                    "latency_ms": 15.0,
                    "retcode": 10009,
                    "pnl_usd": 10.0,
                    "swap_usd": 0.0,
                    "commission_usd": -0.5,
                    "account_login": 55112233,
                    "deal_id": "1102",
                    "order_id": "1202",
                    "position_id": "1301",
                    "ticket": "1102",
                    "comment": "",
                },
            ]
            audit_csv, receipt_json = _reconcile_modified_audit(tmp, rows)
            # Tamper receipt audit_csv_sha256 to simulate pairing mismatched audit & receipt
            rec_doc = json.loads(receipt_json.read_text(encoding="utf-8"))
            rec_doc["inputs"]["audit_csv_sha256"] = "0" * 64
            receipt_json.write_text(json.dumps(rec_doc, indent=2) + "\n", encoding="utf-8", newline="\n")

            manifest = packager.package_payout_audit_bundle(
                output_dir=tmp / "bundle_bad_sl_sha",
                cycle_id="cycle_bad_sl_sha",
                audit_csv=audit_csv,
                reconcile_receipt_json=receipt_json,
                red_news_events=[],
            )
            self.assertFalse(manifest["certified"])
            self.assertFalse(manifest["compliance_assertions"]["hard_sl_verified"])
            self.assertFalse(manifest["compliance_assertions"]["reconciliation_verified"])
            self.assertIn("AUDIT_CSV_RECEIPT_SHA_MISMATCH", manifest["fail_reasons"])

    def test_p1_04_missing_or_blank_receipt_audit_sha256_fails_closed(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            fx = _build_clean_cycle_fixture(tmp)
            base_doc = json.loads(fx["receipt_json"].read_text(encoding="utf-8"))

            # 1. Receipt omitting 'inputs' key entirely MUST fail closed (audit_sha_matched=False)
            doc_no_inputs = dict(base_doc)
            doc_no_inputs.pop("inputs", None)
            rec_no_inputs = tmp / "receipt_no_inputs.json"
            rec_no_inputs.write_text(json.dumps(doc_no_inputs, indent=2) + "\n", encoding="utf-8", newline="\n")
            cert_no_inputs = packager.evaluate_whitebox_compliance(
                audit_csv=fx["audit_csv"],
                reconcile_receipt_json=rec_no_inputs,
                red_news_events=[],
            )
            self.assertFalse(cert_no_inputs["certified"])
            self.assertEqual(cert_no_inputs["verdict"], "REJECTED_FAIL_CLOSED")
            self.assertFalse(cert_no_inputs["details"]["reconciliation"]["audit_sha_matched"])
            self.assertIn("AUDIT_CSV_RECEIPT_SHA_MISSING", cert_no_inputs["fail_reasons"])

            # 2. Receipt with blank / None audit_csv_sha256 MUST fail closed
            for bad_sha in ("", "   ", None):
                doc_bad = json.loads(json.dumps(base_doc))
                doc_bad["inputs"]["audit_csv_sha256"] = bad_sha
                rec_bad = tmp / f"receipt_blank_{type(bad_sha).__name__}_{len(str(bad_sha))}.json"
                rec_bad.write_text(json.dumps(doc_bad, indent=2) + "\n", encoding="utf-8", newline="\n")
                cert_bad = packager.evaluate_whitebox_compliance(
                    audit_csv=fx["audit_csv"],
                    reconcile_receipt_json=rec_bad,
                    red_news_events=[],
                )
                self.assertFalse(cert_bad["certified"], f"bad_sha={bad_sha!r} must fail certification")
                self.assertFalse(cert_bad["details"]["reconciliation"]["audit_sha_matched"])
                self.assertIn("AUDIT_CSV_RECEIPT_SHA_MISSING", cert_bad["fail_reasons"])

            # 3. Receipt with malformed non-64-hex audit_csv_sha256 MUST fail closed
            doc_malformed = json.loads(json.dumps(base_doc))
            doc_malformed["inputs"]["audit_csv_sha256"] = "not-a-valid-sha256"
            rec_malformed = tmp / "receipt_malformed_sha.json"
            rec_malformed.write_text(json.dumps(doc_malformed, indent=2) + "\n", encoding="utf-8", newline="\n")
            cert_mal = packager.evaluate_whitebox_compliance(
                audit_csv=fx["audit_csv"],
                reconcile_receipt_json=rec_malformed,
                red_news_events=[],
            )
            self.assertFalse(cert_mal["certified"])
            self.assertFalse(cert_mal["details"]["reconciliation"]["audit_sha_matched"])
            self.assertIn("AUDIT_CSV_RECEIPT_SHA_INVALID", cert_mal["fail_reasons"])

            # 4. Bundling with missing audit_csv_sha256 fails certification and strict verify
            bundle_dir = tmp / "bundle_missing_sha"
            manifest = packager.package_payout_audit_bundle(
                output_dir=bundle_dir,
                cycle_id="cycle_missing_sha",
                audit_csv=fx["audit_csv"],
                reconcile_receipt_json=rec_no_inputs,
                red_news_events=[],
            )
            self.assertFalse(manifest["certified"])
            self.assertIn("AUDIT_CSV_RECEIPT_SHA_MISSING", manifest["fail_reasons"])
            ver = packager.verify_payout_audit_bundle(bundle_dir, require_certified=True)
            self.assertFalse(ver["verified"])

    def test_manifest_tamper_and_consecutive_soft_martingale_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            t0 = 1794042000
            # Soft martingale over 2 consecutive losses: 0.10 -> 0.14 -> 0.20 (2.0x cumulative)
            rows: list[dict[str, object]] = []
            lots_seq = [0.10, 0.14, 0.20]
            pnl_seq = [-20.0, -28.0, 60.0]
            for idx, (lot, pnl) in enumerate(zip(lots_seq, pnl_seq, strict=True), start=1):
                base_t = t0 + idx * 3600
                rows.append(
                    {
                        "utc_ts": base_t,
                        "magic": 20261124,
                        "engine_id": "E4",
                        "symbol": "US100.cash",
                        "side": "BUY",
                        "event_type": "ENTRY",
                        "signal_price": 20000.0,
                        "fill_price": 20000.0,
                        "sl_price": 19950.0,
                        "lots": lot,
                        "spread_pts": 20.0,
                        "latency_ms": 15.0,
                        "retcode": 10009,
                        "pnl_usd": 0.0,
                        "swap_usd": 0.0,
                        "commission_usd": 0.0,
                        "account_login": 55112233,
                        "deal_id": f"200{idx}1",
                        "order_id": f"210{idx}1",
                        "position_id": f"220{idx}",
                        "ticket": f"200{idx}1",
                        "comment": "",
                    }
                )
                rows.append(
                    {
                        "utc_ts": base_t + 600,
                        "magic": 20261124,
                        "engine_id": "E4",
                        "symbol": "US100.cash",
                        "side": "SELL",
                        "event_type": "SL_HIT" if pnl < 0 else "TP_HIT",
                        "signal_price": 19950.0 if pnl < 0 else 20100.0,
                        "fill_price": 19950.0 if pnl < 0 else 20100.0,
                        "sl_price": 19950.0,
                        "lots": lot,
                        "spread_pts": 20.0,
                        "latency_ms": 15.0,
                        "retcode": 10009,
                        "pnl_usd": pnl,
                        "swap_usd": 0.0,
                        "commission_usd": 0.0,
                        "account_login": 55112233,
                        "deal_id": f"200{idx}2",
                        "order_id": f"210{idx}2",
                        "position_id": f"220{idx}",
                        "ticket": f"200{idx}2",
                        "comment": "",
                    }
                )
            audit_csv, receipt_json = _reconcile_modified_audit(tmp, rows)
            bdir = tmp / "bundle_soft_mart"
            manifest = packager.package_payout_audit_bundle(
                output_dir=bdir,
                cycle_id="cycle_soft_mart",
                audit_csv=audit_csv,
                reconcile_receipt_json=receipt_json,
                red_news_events=[],
            )
            self.assertFalse(manifest["certified"])
            self.assertFalse(manifest["compliance_assertions"]["zero_martingale_verified"])

            # Mutate manifest JSON directly -> verify_payout_audit_bundle catches MANIFEST_SHA256_MISMATCH
            mp = bdir / "payout_audit_manifest.json"
            doc = json.loads(mp.read_text(encoding="utf-8"))
            doc["certified"] = True
            doc["verdict"] = "CERTIFIED"
            mp.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8", newline="\n")
            ver = packager.verify_payout_audit_bundle(bdir)
            self.assertFalse(ver["verified"])
            self.assertFalse(ver["manifest_sha_valid"])
            self.assertIn("MANIFEST_SHA256_MISMATCH", ver["errors"])

    def test_layer1_opsec_direct_scan_on_all_ops5_deliverables(self) -> None:
        from tests import test_layer1_opsec_guard as opsec

        targets = (
            (PACKAGER_PATH, False),
            (RUNBOOK_PATH, False),
            (Path(__file__).resolve(), True),
        )
        for path, is_test in targets:
            raw = path.read_bytes()
            self.assertNotIn(b"\r", raw, f"Non-LF line ending in {path.name}")
            text = raw.decode("utf-8")
            self.assertIsNone(opsec._REAL_LAN_HOST_RE.search(text), f"Real LAN IP in {path.name}")
            self.assertIsNone(opsec._REAL_TAILSCALE_RE.search(text), f"Real Tailscale IP in {path.name}")
            self.assertIsNone(opsec._HEROKU_APP_RE.search(text), f"Real Heroku app in {path.name}")
            self.assertIsNone(opsec._TG_BOT_HANDLE_RE.search(text), f"Real TG bot in {path.name}")
            if not is_test:
                self.assertIsNone(opsec._ANY_LAN_IP_RE.search(text), f"LAN IP in {path.name}")
                for m_ts in opsec._ANY_CGNAT_TS_RE.finditer(text):
                    self.assertEqual(text[m_ts.start() : m_ts.end() + 3], "100.64.0.0/10")
                self.assertIsNone(opsec._WIN_USER_PATH_RE.search(text), f"Windows user path in {path.name}")
            for tag, rx in opsec._REAL_SECRET_PATTERNS:
                self.assertIsNone(rx.search(text), f"Secret {tag} in {path.name}")


if __name__ == "__main__":
    unittest.main()
