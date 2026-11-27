"""Wave 0C (`W4-G12`) Field Milestone Toolkit Tests (`01/12` -> `10/12`).

Verifies strictly offline & deterministically (zero SSH writes, zero OrderSend, zero Holdout v1 reads):
  1. `01/12` Holdout v2 Preregistration: `preregister_holdout_v2.py --verify` returns `exit 0`,
     `VERIFIED_PASS`, `8/8` frozen artifacts verified, `order_send_count == 0`, `holdout_rows_analysed == 0`.
  2. `04/12` NFP & `10/12` CPI Quote Collector: `nfp_cpi_quote_collector.py --event SMOKE_PREFLIGHT
     --preflight-offline-only` confirms `PREFLIGHT_OK`, `record_tier == "QUOTE_ONLY"`, `order_send_count == 0`,
     `csv_columns_count == 23`, both Dec-2026 BLS events in red-news CSV, AND fail-closed NTP rejection.
  3. `08/12` Free-Trial Read-Only Harvester (`harvest_free_trial_forensics.py`):
     - End-to-end synthetic `--offline-fixture` pipeline -> isolated `live-vault` broker M1 ingestion +
       SHA-256 manifest + `OPS-6` parity/geometry report + slippage tail `P50/P90/P95/P99` +
       `US100.cash` SL slippage vs `1.50x/1.75x` + `12-13/12` `GO_READY` / `CONDITIONAL_REVIEW` / `NO_GO`.
     - Fail-closed rejection on: SSH write attempts (`deploy-scripts`, `mkdir`, `rm`, `>`, `Set-Content`,
       SCP push to VPS, raw IPv4 host), NTP `>= 1000 ms` (`1000.0`, `1500.0`, `"-1.2s"`, missing),
       `NaN`/`Inf` slippage, missing/mismatched `expected_login`/`expected_server`, `trade_allowed != False`,
       and `2025+` Holdout contamination in Dev mode (plus sealed Holdout v1 `[2025-01-01, 2026-12-01)`
       rejection in `prospective_trial` mode).
     - Mocked read-only SSH pull (`naqex-node1-lan` -> `naqex-node1-ts` fallback) proving `creationflags`
       propagation and `0` SSH writes.
  4. AST Guards:
     - `0` `subprocess` spawn calls missing `creationflags` across `harvest_free_trial_forensics.py`,
       `nfp_cpi_quote_collector.py`, `node_ctl.py`, and `preregister_holdout_v2.py`.
     - `0` bare `assert` statements and `0` `MetaTrader5` imports in `harvest_free_trial_forensics.py`.

All checks use `_check(...)` so tests remain 100% active under BOTH `python` AND `python -O`.
"""

from __future__ import annotations

import ast
import csv
import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

AI_ENGINES = Path(__file__).resolve().parents[2]
REPO_ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from ops_cloud import nfp_cpi_quote_collector as nfp_mod  # noqa: E402
from ops_cloud import node_ctl  # noqa: E402
from quant_core.holdout_guard import HoldoutLockError  # noqa: E402
from quant_core.tca import canonical_payload_sha256  # noqa: E402
from quant_factory import preregister_holdout_v2 as prereg_mod  # noqa: E402
from quant_factory.wave4 import harvest_free_trial_forensics as hft  # noqa: E402

_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
_SUBPROCESS_CALL_ATTRS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})

SYNTHETIC_LOGIN = 990001
SYNTHETIC_SERVER = "FTMO-Demo-Synthetic"


def _check(cond: bool, msg: str) -> None:
    """Explicit assertion immune to `python -O` optimization stripping."""
    if not cond:
        raise AssertionError(msg)


@pytest.fixture
def safe_tmp_dir() -> Iterator[Path]:
    """OS-temp directory outside drive E: so isolated live-vault ingestion never collides with E: backup guard."""
    with tempfile.TemporaryDirectory(prefix="naqex_w4t0mil_") as d:
        yield Path(d)


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)


def _build_offline_fixture(
    fixture_dir: Path,
    *,
    base_ts: int = int(datetime(2024, 10, 15, 13, 30, 0, tzinfo=UTC).timestamp()),
    ntp_offset: str = "+0.045s",
    trade_allowed: bool | None = False,
    status_login: int | None = SYNTHETIC_LOGIN,
    status_server: str | None = SYNTHETIC_SERVER,
    us100_sl_exit_px: float = 19949.10,  # SL=19950.00 -> 90 pts adverse = 0.90x (<= 1.50x PASS)
    swap_usd: float = 0.0,
    inject_nan_slip: bool = False,
    inject_ghost_trade: bool = False,
    audit_row_login: int = SYNTHETIC_LOGIN,
) -> Path:
    """Create a complete deterministic offline Free-Trial fixture directory."""
    fixture_dir.mkdir(parents=True, exist_ok=True)

    # 1. node_status.json (telemetry + read-only posture)
    heartbeat: dict[str, Any] = {"connected": True, "order_send_count": 0}
    if status_login is not None:
        heartbeat["login"] = status_login
    if status_server is not None:
        heartbeat["server"] = status_server
    if trade_allowed is not None:
        heartbeat["trade_allowed"] = trade_allowed

    node_status = {
        "checked_utc": datetime.fromtimestamp(base_ts + 3600, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_count": 0,
        "ntp_offset": ntp_offset,
        "heartbeat": heartbeat,
    }
    (fixture_dir / "node_status.json").write_text(json.dumps(node_status, indent=2) + "\n", encoding="utf-8")

    # 2. naqex_exec_audit.csv (3 clean entry fills + 1 legitimate spread block)
    audit_cols = [
        "utc_ts",
        "magic",
        "engine_id",
        "symbol",
        "side",
        "position_side",
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
        "intent_id",
        "comment",
        "adverse_slip_pts",
    ]
    audit_rows: list[dict[str, Any]] = [
        {
            "utc_ts": base_ts,
            "magic": 701,
            "engine_id": "E1_US100",
            "symbol": "US100.cash",
            "side": "BUY",
            "position_side": "BUY",
            "event_type": "ORDER_FILL",
            "signal_price": 20000.00,
            "fill_price": 20000.25,
            "sl_price": 19950.00,
            "lots": 0.20,
            "spread_pts": 18.0,
            "latency_ms": 95.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": 0.0,
            "account_login": audit_row_login,
            "deal_id": "D101",
            "order_id": "O101",
            "position_id": "P101",
            "intent_id": "SIG_US100_1",
            "comment": "pos=P101 intent=SIG_US100_1",
            "adverse_slip_pts": "NaN" if inject_nan_slip else 25.0,
        },
        {
            "utc_ts": base_ts + 300,
            "magic": 702,
            "engine_id": "E2_USDJPY",
            "symbol": "USDJPY",
            "side": "BUY",
            "position_side": "BUY",
            "event_type": "ORDER_FILL",
            "signal_price": 149.500,
            "fill_price": 149.503,
            "sl_price": 149.200,
            "lots": 0.50,
            "spread_pts": 6.0,
            "latency_ms": 82.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": -1.5,
            "account_login": audit_row_login,
            "deal_id": "D102",
            "order_id": "O102",
            "position_id": "P102",
            "intent_id": "SIG_USDJPY_1",
            "comment": "pos=P102 intent=SIG_USDJPY_1",
            "adverse_slip_pts": 3.0,
        },
        {
            "utc_ts": base_ts + 600,
            "magic": 703,
            "engine_id": "E3_GBPUSD",
            "symbol": "GBPUSD",
            "side": "SELL",
            "position_side": "SELL",
            "event_type": "ORDER_FILL",
            "signal_price": 1.30500,
            "fill_price": 1.30498,
            "sl_price": 1.30800,
            "lots": 0.40,
            "spread_pts": 5.5,
            "latency_ms": 74.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": -1.2,
            "account_login": audit_row_login,
            "deal_id": "D103",
            "order_id": "O103",
            "position_id": "P103",
            "intent_id": "SIG_GBPUSD_1",
            "comment": "pos=P103 intent=SIG_GBPUSD_1",
            "adverse_slip_pts": 2.0,
        },
        {
            "utc_ts": base_ts + 900,
            "magic": 704,
            "engine_id": "E4_EURJPY",
            "symbol": "EURJPY",
            "side": "BUY",
            "position_side": "BUY",
            "event_type": "ORDER_BLOCKED_SPREAD",
            "signal_price": 162.500,
            "fill_price": 0.0,
            "sl_price": 162.200,
            "lots": 0.30,
            "spread_pts": 45.0,
            "latency_ms": 5.0,
            "retcode": 0,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": "",
            "account_login": audit_row_login,
            "deal_id": "",
            "order_id": "",
            "position_id": "",
            "intent_id": "SIG_EURJPY_BLOCKED",
            "comment": "BLOCKED_BY_SPREAD",
            "adverse_slip_pts": "",
        },
    ]
    if inject_ghost_trade:
        audit_rows.append(
            {
                "utc_ts": base_ts + 1200,
                "magic": 702,
                "engine_id": "E2_USDJPY",
                "symbol": "USDJPY",
                "side": "SELL",
                "position_side": "SELL",
                "event_type": "ORDER_FILL",
                "signal_price": 149.600,
                "fill_price": 149.598,
                "sl_price": 149.900,
                "lots": 0.50,
                "spread_pts": 6.0,
                "latency_ms": 80.0,
                "retcode": 10009,
                "pnl_usd": 20.0,
                "swap_usd": 0.0,
                "commission_usd": -1.5,
                "account_login": audit_row_login,
                "deal_id": "D999",
                "order_id": "O999",
                "position_id": "P999",
                "intent_id": "GHOST_SIG",
                "comment": "pos=P999 intent=GHOST_SIG",
                "adverse_slip_pts": 2.0,
            }
        )
    _write_csv(fixture_dir / "naqex_exec_audit.csv", audit_cols, audit_rows)

    # 3. mt5_deals_export.csv (enriches entry swap_usd + supplies SL/TP exit legs!)
    deal_cols = [
        "utc_ts",
        "position_id",
        "deal_id",
        "order_id",
        "leg",
        "event_type",
        "symbol",
        "side",
        "position_side",
        "lots",
        "signal_price",
        "fill_price",
        "sl_price",
        "spread_pts",
        "latency_ms",
        "pnl_usd",
        "swap_usd",
        "commission_usd",
        "exit_reason",
        "account_login",
    ]
    deal_rows: list[dict[str, Any]] = [
        # Entry deal enrichments (matching D101..D103 so swap_usd=0.0 is enriched cleanly)
        {
            "utc_ts": base_ts,
            "position_id": "P101",
            "deal_id": "D101",
            "order_id": "O101",
            "leg": "ENTRY",
            "event_type": "ORDER_FILL",
            "symbol": "US100.cash",
            "side": "BUY",
            "position_side": "BUY",
            "lots": 0.20,
            "signal_price": 20000.00,
            "fill_price": 20000.25,
            "sl_price": 19950.00,
            "spread_pts": 18.0,
            "latency_ms": 95.0,
            "pnl_usd": 0.0,
            "swap_usd": swap_usd,
            "commission_usd": 0.0,
            "exit_reason": "",
            "account_login": audit_row_login,
        },
        {
            "utc_ts": base_ts + 240,
            "position_id": "P101",
            "deal_id": "D101_EXIT",
            "order_id": "O101_EXIT",
            "leg": "EXIT",
            "event_type": "SL_HIT",
            "symbol": "US100.cash",
            "side": "SELL",  # MT5 closing deal side is opposite to BUY position_side!
            "position_side": "BUY",
            "lots": 0.20,
            "signal_price": 19950.00,
            "fill_price": us100_sl_exit_px,
            "sl_price": 19950.00,
            "spread_pts": 20.0,
            "latency_ms": 40.0,
            "pnl_usd": -102.30,
            "swap_usd": swap_usd,
            "commission_usd": 0.0,
            "exit_reason": "SL",
            "account_login": audit_row_login,
        },
        {
            "utc_ts": base_ts + 300,
            "position_id": "P102",
            "deal_id": "D102",
            "order_id": "O102",
            "leg": "ENTRY",
            "event_type": "ORDER_FILL",
            "symbol": "USDJPY",
            "side": "BUY",
            "position_side": "BUY",
            "lots": 0.50,
            "signal_price": 149.500,
            "fill_price": 149.503,
            "sl_price": 149.200,
            "spread_pts": 6.0,
            "latency_ms": 82.0,
            "pnl_usd": 0.0,
            "swap_usd": 0.0,
            "commission_usd": -1.5,
            "exit_reason": "",
            "account_login": audit_row_login,
        },
        {
            "utc_ts": base_ts + 540,
            "position_id": "P102",
            "deal_id": "D102_EXIT",
            "order_id": "O102_EXIT",
            "leg": "EXIT",
            "event_type": "TP_HIT",
            "symbol": "USDJPY",
            "side": "SELL",
            "position_side": "BUY",
            "lots": 0.50,
            "signal_price": 149.950,
            "fill_price": 149.950,
            "sl_price": 149.200,
            "spread_pts": 6.0,
            "latency_ms": 35.0,
            "pnl_usd": 149.50,
            "swap_usd": 0.0,
            "commission_usd": -1.5,
            "exit_reason": "TP",
            "account_login": audit_row_login,
        },
        {
            "utc_ts": base_ts + 600,
            "position_id": "P103",
            "deal_id": "D103",
            "order_id": "O103",
            "leg": "ENTRY",
            "event_type": "ORDER_FILL",
            "symbol": "GBPUSD",
            "side": "SELL",
            "position_side": "SELL",
            "lots": 0.40,
            "signal_price": 1.30500,
            "fill_price": 1.30498,
            "sl_price": 1.30800,
            "spread_pts": 5.5,
            "latency_ms": 74.0,
            "pnl_usd": 0.0,
            "swap_usd": 0.0,
            "commission_usd": -1.2,
            "exit_reason": "",
            "account_login": audit_row_login,
        },
        {
            "utc_ts": base_ts + 840,
            "position_id": "P103",
            "deal_id": "D103_EXIT",
            "order_id": "O103_EXIT",
            "leg": "EXIT",
            "event_type": "TP_HIT",
            "symbol": "GBPUSD",
            "side": "BUY",
            "position_side": "SELL",
            "lots": 0.40,
            "signal_price": 1.30050,
            "fill_price": 1.30050,
            "sl_price": 1.30800,
            "spread_pts": 5.5,
            "latency_ms": 30.0,
            "pnl_usd": 179.20,
            "swap_usd": 0.0,
            "commission_usd": -1.2,
            "exit_reason": "TP",
            "account_login": audit_row_login,
        },
    ]
    _write_csv(fixture_dir / "mt5_deals_export.csv", deal_cols, deal_rows)

    # 4. naqex_decision_blackbox_20241015.jsonl (legitimate guard block for EURJPY)
    bb_line = {
        "utc_ts": base_ts + 900,
        "symbol": "EURJPY",
        "side": "BUY",
        "magic": 704,
        "signal_id": "SIG_EURJPY_BLOCKED",
        "decision": "BLOCKED_BY_SPREAD",
        "block_reason": "spread_45pts_gt_max",
        "spread_pts": 45.0,
    }
    (fixture_dir / "naqex_decision_blackbox_20241015.jsonl").write_text(
        json.dumps(bb_line) + "\n", encoding="utf-8"
    )

    # 5. expected_python_trades.json (3 matched fills + 1 legitimately guard-blocked signal)
    expected_trades = [
        {
            "symbol": "US100.cash",
            "side": "BUY",
            "utc_ts": base_ts,
            "magic": 701,
            "signal_id": "SIG_US100_1",
            "entry_price": 20000.00,
            "sl_price": 19950.00,
            "lots": 0.20,
            "slippage_budget_pts": 150.0,
            "gross_R": -1.0,
        },
        {
            "symbol": "USDJPY",
            "side": "BUY",
            "utc_ts": base_ts + 300,
            "magic": 702,
            "signal_id": "SIG_USDJPY_1",
            "entry_price": 149.500,
            "sl_price": 149.200,
            "lots": 0.50,
            "gross_R": 1.5,
        },
        {
            "symbol": "GBPUSD",
            "side": "SELL",
            "utc_ts": base_ts + 600,
            "magic": 703,
            "signal_id": "SIG_GBPUSD_1",
            "entry_price": 1.30500,
            "sl_price": 1.30800,
            "lots": 0.40,
            "gross_R": 1.5,
        },
        {
            "symbol": "EURJPY",
            "side": "BUY",
            "utc_ts": base_ts + 900,
            "magic": 704,
            "signal_id": "SIG_EURJPY_BLOCKED",
            "entry_price": 162.500,
            "sl_price": 162.200,
            "lots": 0.30,
            "gross_R": 1.0,
        },
    ]
    (fixture_dir / "expected_python_trades.json").write_text(
        json.dumps({"trades": expected_trades}, indent=2) + "\n", encoding="utf-8"
    )

    # 6. broker_quote_tape.csv (causal Bid/Ask quotes for isolated live-vault M1 ingestion + markout)
    quote_cols = ["utc_ts", "symbol", "bid", "ask", "point", "order_send_count"]
    quote_rows: list[dict[str, Any]] = []
    for offset in (-10, 0, 1, 10, 60, 120, 240, 300, 600):
        quote_rows.append(
            {
                "utc_ts": base_ts + offset,
                "symbol": "US100.cash",
                "bid": 19999.90 - (offset * 0.15 if offset <= 240 else 20.0),
                "ask": 20000.10 - (offset * 0.15 if offset <= 240 else 20.0),
                "point": 0.01,
                "order_send_count": 0,
            }
        )
        quote_rows.append(
            {
                "utc_ts": base_ts + 300 + offset,
                "symbol": "USDJPY",
                "bid": 149.497 + (0.001 * max(0, offset // 30)),
                "ask": 149.503 + (0.001 * max(0, offset // 30)),
                "point": 0.001,
                "order_send_count": 0,
            }
        )
        quote_rows.append(
            {
                "utc_ts": base_ts + 600 + offset,
                "symbol": "GBPUSD",
                "bid": 1.30495 - (0.00002 * max(0, offset // 30)),
                "ask": 1.30501 - (0.00002 * max(0, offset // 30)),
                "point": 0.00001,
                "order_send_count": 0,
            }
        )
    _write_csv(fixture_dir / "broker_quote_tape.csv", quote_cols, quote_rows)

    return fixture_dir


# ---------------------------------------------------------------------------
# 1. End-to-End 08/12 Free-Trial Harvester on Offline Fixture -> OPS-6 Bundle
# ---------------------------------------------------------------------------
def test_harvest_free_trial_end_to_end_offline_fixture_and_cli(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    fixture_dir = _build_offline_fixture(tmp_path / "fixture_clean")
    vault_root = tmp_path / "live-vault"
    out_json = tmp_path / "bundle" / "free_trial_forensics.json"
    out_md = tmp_path / "bundle" / "free_trial_forensics.md"

    bundle = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=fixture_dir,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="FTMO_TRIAL_SMOKE",
        run_mode="dev",
        vault_root=vault_root,
        output_json=out_json,
        output_md=out_md,
    )

    _check(bundle["schema"] == hft.SCHEMA_VERSION, f"Unexpected schema: {bundle['schema']}")
    _check(bundle["hard_invariants"]["order_send_count"] == 0, "order_send_count must be 0")
    _check(bundle["hard_invariants"]["ssh_write_count"] == 0, "ssh_write_count must be 0")
    _check(bundle["hard_invariants"]["holdout_v1_rows_analysed"] == 0, "holdout_v1_rows_analysed must be 0")
    _check(bundle["telemetry_posture"]["ntp_ok"] is True, "NTP should pass")
    _check(bundle["telemetry_posture"]["trade_allowed"] is False, "trade_allowed must be False")
    _check(bundle["telemetry_posture"]["login_verified"] is True, "login must verify")
    _check(str(SYNTHETIC_LOGIN) not in json.dumps(bundle), "Raw login must NEVER leak into emitted bundle")

    # Isolated live-vault ingestion verified
    vault_info = bundle["live_broker_tape_vault"]
    _check(vault_info is not None and vault_info["manifest_verified"] is True, "Live vault manifest must verify")
    _check(vault_info["zero_cache_contamination"] is True, "Zero cache contamination required")
    _check(set(vault_info["symbols_ingested"]) == {"GBPUSD", "US100", "USDJPY"}, f"Unexpected symbols: {vault_info}")

    # Slippage tail P50/P90/P95/P99
    tail = bundle["slippage_tail"]["overall_adverse_slip_pts"]
    _check(tail["count"] == 3, f"Expected 3 positions in slippage tail, got {tail}")
    for key in ("p50", "p90", "p95", "p99"):
        _check(tail[key] is not None, f"Missing slippage percentile {key}")

    # US100.cash SL slippage vs 1.50x / 1.75x (90 pts / 100 pts = 0.90x -> PASS_WITHIN_1_50X)
    us100 = bundle["us100_sl_slippage_gate"]
    _check(us100["sl_sample_count"] == 1, f"Expected 1 US100 SL sample, got {us100}")
    _check(abs(us100["multipliers"]["effective_mult"] - 0.90) < 1e-3, f"Expected 0.90x, got {us100}")
    _check(us100["verdict"] == "PASS_WITHIN_1_50X", f"Unexpected US100 verdict: {us100}")
    _check(us100["within_1_50x"] is True and us100["breaches_1_75x_kill"] is False, "US100 flags mismatch")

    # OPS-6 parity & GO/NO-GO decision
    go = bundle["go_nogo_decision"]
    _check(go["decision"] == "GO_READY", f"Expected GO_READY, got {go}")
    _check(go["trade_match_rate"] == 1.0, f"Expected 100% actionable match rate, got {go}")
    _check(go["ghost_trades"] == 0, f"Expected 0 ghost trades, got {go}")
    _check(go["legitimate_guard_blocks"] == 1, f"Expected 1 guard block, got {go}")
    _check(go["swap_violations"] == 0, f"Expected 0 swap violations, got {go}")

    # Atomic SHA-256 disk integrity matches memory bundle
    _check(out_json.is_file() and out_md.is_file(), "Output JSON and MD must exist")
    disk_doc = json.loads(out_json.read_text(encoding="utf-8"))
    _check(disk_doc["report_sha256"] == canonical_payload_sha256(disk_doc), "Disk SHA-256 mismatch")
    _check(disk_doc["report_sha256"] == bundle["report_sha256"], "Memory vs disk SHA-256 mismatch")

    # CLI --offline-fixture smoke execution
    cli_out = tmp_path / "bundle_cli" / "cli_forensics.json"
    proc = subprocess.run(
        [
            sys.executable,
            str(AI_ENGINES / "quant_factory" / "wave4" / "harvest_free_trial_forensics.py"),
            "--offline-fixture",
            str(fixture_dir),
            "--expected-login",
            str(SYNTHETIC_LOGIN),
            "--expected-server",
            SYNTHETIC_SERVER,
            "--account-alias",
            "FTMO_TRIAL_CLI",
            "--run-mode",
            "dev",
            "--vault-root",
            str(tmp_path / "cli_run" / "live-vault"),
            "--output-json",
            str(cli_out),
        ],
        capture_output=True,
        text=True,
        timeout=30,
        creationflags=_NO_WINDOW_FLAGS,
    )
    _check(proc.returncode == 0, f"CLI offline fixture failed rc={proc.returncode}: {proc.stderr}")
    cli_payload = json.loads(proc.stdout)
    _check(cli_payload["go_nogo_decision"]["decision"] == "GO_READY", "CLI should emit GO_READY")
    _check(cli_out.is_file(), "CLI output JSON missing")


def test_harvest_us100_slippage_amber_kill_and_ghost_no_go(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    # 1. US100 SL slippage = 160 pts = 1.60x -> AMBER (CONDITIONAL_REVIEW)
    f_amber = _build_offline_fixture(tmp_path / "f_amber", us100_sl_exit_px=19948.40)
    b_amber = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=f_amber,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="TRIAL_AMBER",
        vault_root=tmp_path / "live-vault",
    )
    amber_gate = b_amber["us100_sl_slippage_gate"]
    _check(amber_gate["verdict"] == "AMBER_BETWEEN_1_50X_AND_1_75X", f"Got {amber_gate}")
    _check(b_amber["go_nogo_decision"]["decision"] == "CONDITIONAL_REVIEW", f"Got {b_amber['go_nogo_decision']}")

    # 2. US100 SL slippage = 190 pts = 1.90x -> KILL (> 1.75x) -> NO_GO
    f_kill = _build_offline_fixture(tmp_path / "f_kill", us100_sl_exit_px=19948.10)
    b_kill = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=f_kill,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="TRIAL_KILL",
        vault_root=tmp_path / "live-vault",
    )
    kill_gate = b_kill["us100_sl_slippage_gate"]
    _check(kill_gate["verdict"] == "KILL_EXCEEDS_1_75X", f"Got {kill_gate}")
    _check(b_kill["go_nogo_decision"]["decision"] == "NO_GO", f"Got {b_kill['go_nogo_decision']}")

    # 3. Ghost trade -> NO_GO
    f_ghost = _build_offline_fixture(tmp_path / "f_ghost", inject_ghost_trade=True)
    b_ghost = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=f_ghost,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="TRIAL_GHOST",
        vault_root=tmp_path / "live-vault",
    )
    _check(b_ghost["go_nogo_decision"]["ghost_trades"] == 1, "Ghost trade must be detected")
    _check(b_ghost["go_nogo_decision"]["decision"] == "NO_GO", "Ghost trade must force NO_GO")

    # 4. Non-zero swap -> NO_GO
    f_swap = _build_offline_fixture(tmp_path / "f_swap", swap_usd=-2.50)
    b_swap = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=f_swap,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="TRIAL_SWAP",
        vault_root=tmp_path / "live-vault",
    )
    _check(b_swap["go_nogo_decision"]["swap_violations"] >= 1, "Swap violation must be flagged")
    _check(b_swap["go_nogo_decision"]["decision"] == "NO_GO", "Non-zero swap must force NO_GO")


# ---------------------------------------------------------------------------
# 2. Fail-Closed Guards: SSH Writes, NTP >= 1000ms, NaN Slippage, Login/Posture, Holdout 2025+
# ---------------------------------------------------------------------------
def test_fail_closed_ssh_write_and_raw_ip_rejection(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    # Block deploy-scripts & any unlisted node_ctl write action
    for bad_action in ("deploy-scripts", "deploy", "rm", "exec"):
        with pytest.raises(hft.ReadOnlyViolationError):
            hft.run_readonly_node_probe(bad_action, host="naqex-node1-lan")

    # Block raw IPv4 / user@host / unlisted host aliases (using RFC 5737 doc IP only)
    for bad_host in ("203.0.113.10", "admin@naqex-node1-lan", "evil-box", "naqex-node1-lan;whoami", ""):
        with pytest.raises(hft.ReadOnlyViolationError):
            hft.validate_ssh_host_alias(bad_host)

    # Allow ONLY approved SSH host aliases
    for good_host in ("naqex-node1-lan", "naqex-node1-ts", "naqex-node1"):
        _check(hft.validate_ssh_host_alias(good_host) == good_host, f"Valid alias rejected: {good_host}")

    # Block ALL mutating/redirection SSH commands
    for bad_cmd in (
        'mkdir "C:\\Naqex\\pwn"',
        'del "C:\\Naqex\\mt5\\MQL5\\Files\\naqex_exec_audit.csv"',
        'dir /b "C:\\Naqex\\mt5\\MQL5\\Files" > C:\\Naqex\\out.txt',
        'dir /b "C:\\Naqex\\mt5\\MQL5\\Files" && echo hi',
        'powershell -Command "Set-Content C:\\Naqex\\x.txt hi"',
        'dir /b "C:\\Windows\\System32"',
        'dir /b "C:\\Naqex\\..\\Windows"',
    ):
        with pytest.raises(hft.ReadOnlyViolationError):
            hft.validate_readonly_ssh_command(bad_cmd)

    # Block SCP push/upload (local -> remote) and forbidden local cache destinations
    local_file = tmp_path / "dummy.csv"
    local_file.write_text("a,b\n1,2\n", encoding="utf-8")
    with pytest.raises(hft.ReadOnlyViolationError):
        hft.validate_readonly_scp_pull(str(local_file), "naqex-node1-lan:C:/Naqex/mt5/MQL5/Files/dummy.csv")
    with pytest.raises(hft.ReadOnlyViolationError):
        hft.run_readonly_scp_pull("naqex-node1-lan:C:/Naqex/mt5/MQL5/Files/a.csv", "naqex-node1-ts:C:/Naqex/a.csv")
    with pytest.raises(hft.ReadOnlyViolationError):
        hft.validate_readonly_scp_pull(
            "naqex-node1-lan:C:/Naqex/mt5/MQL5/Files/naqex_exec_audit.csv",
            tmp_path / "hot-m1-cache" / "leak.csv",
        )
    with pytest.raises(hft.ReadOnlyViolationError):
        hft.validate_readonly_scp_pull(
            "naqex-node1-lan:C:/Naqex/mt5/MQL5/Files/payload.ex5",
            tmp_path / "staging" / "payload.ex5",
        )
    with pytest.raises(hft.ReadOnlyViolationError):
        hft.validate_readonly_scp_pull(
            "naqex-node1-lan:C:/Naqex/mt5/MQL5/Files/naqex_exec_audit.csv",
            "E:\\live-vault\\leak.csv",
        )


def test_fail_closed_ntp_login_server_trade_allowed_and_nan_slippage(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    # 1. NTP >= 1000 ms (exact boundary 1000.0 ms, +1.500s, -1.050s, and "unknown")
    for bad_ntp in ("+1.000s", "+1.500s", "-1.050s", "unknown"):
        f_ntp = _build_offline_fixture(tmp_path / f"f_ntp_{abs(hash(bad_ntp))}", ntp_offset=bad_ntp)
        with pytest.raises(hft.TelemetryPreflightError):
            hft.harvest_free_trial_forensics(
                source_dir_or_manifest=f_ntp,
                expected_login=SYNTHETIC_LOGIN,
                expected_server=SYNTHETIC_SERVER,
                vault_root=tmp_path / "live-vault",
            )

    # 2. Missing expected_login / missing observed login / login mismatch
    f_ok = _build_offline_fixture(tmp_path / "f_base_ok")
    for bad_login in (None, 0, -5, True):
        with pytest.raises(hft.TelemetryPreflightError):
            hft.harvest_free_trial_forensics(
                source_dir_or_manifest=f_ok,
                expected_login=bad_login,  # type: ignore[arg-type]
                expected_server=SYNTHETIC_SERVER,
                vault_root=tmp_path / "live-vault",
            )

    f_no_login = _build_offline_fixture(tmp_path / "f_no_login", status_login=None)
    with pytest.raises(hft.TelemetryPreflightError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_no_login,
            expected_login=SYNTHETIC_LOGIN,
            expected_server=SYNTHETIC_SERVER,
            vault_root=tmp_path / "live-vault",
        )

    f_wrong_row_login = _build_offline_fixture(tmp_path / "f_wrong_row", audit_row_login=990999)
    with pytest.raises(hft.TelemetryPreflightError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_wrong_row_login,
            expected_login=SYNTHETIC_LOGIN,
            expected_server=SYNTHETIC_SERVER,
            vault_root=tmp_path / "live-vault",
        )

    # 3. Missing / mismatched expected_server
    with pytest.raises(hft.TelemetryPreflightError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_ok,
            expected_login=SYNTHETIC_LOGIN,
            expected_server="Wrong-Broker-Server",
            vault_root=tmp_path / "live-vault",
        )

    # 4. trade_allowed == True or missing trade_allowed -> FAIL CLOSED
    for bad_ta in (True, None):
        f_ta = _build_offline_fixture(tmp_path / f"f_ta_{bad_ta}", trade_allowed=bad_ta)
        with pytest.raises(hft.TelemetryPreflightError):
            hft.harvest_free_trial_forensics(
                source_dir_or_manifest=f_ta,
                expected_login=SYNTHETIC_LOGIN,
                expected_server=SYNTHETIC_SERVER,
                vault_root=tmp_path / "live-vault",
            )

    # 5. NaN / Inf slippage -> FAIL CLOSED
    f_nan = _build_offline_fixture(tmp_path / "f_nan", inject_nan_slip=True)
    with pytest.raises(hft.NonFiniteTelemetryError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_nan,
            expected_login=SYNTHETIC_LOGIN,
            expected_server=SYNTHETIC_SERVER,
            vault_root=tmp_path / "live-vault",
        )
    with pytest.raises(hft.NonFiniteTelemetryError):
        hft.compute_slippage_tail_stats([1.0, float("nan"), 2.0])
    with pytest.raises(hft.NonFiniteTelemetryError):
        hft.compute_slippage_tail_stats([1.0, float("inf")])


def test_fail_closed_holdout_2025_plus_in_dev_mode_and_v1_seal_in_prospective_mode(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    # Dev mode MUST reject 2025-01-01T00:00:00Z+ timestamps with HoldoutLockError
    ts_2025 = int(datetime(2025, 1, 1, 0, 0, 0, tzinfo=UTC).timestamp())
    f_2025 = _build_offline_fixture(tmp_path / "f_2025", base_ts=ts_2025)
    with pytest.raises(HoldoutLockError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_2025,
            expected_login=SYNTHETIC_LOGIN,
            expected_server=SYNTHETIC_SERVER,
            run_mode="dev",
            vault_root=tmp_path / "live-vault",
        )

    # Prospective trial mode MUST STILL reject sealed Holdout v1 [2025-01-01, 2026-12-01)
    ts_2026_nov = int(datetime(2026, 11, 15, 13, 30, 0, tzinfo=UTC).timestamp())
    f_v1 = _build_offline_fixture(tmp_path / "f_v1_sealed", base_ts=ts_2026_nov)
    with pytest.raises(HoldoutLockError):
        hft.harvest_free_trial_forensics(
            source_dir_or_manifest=f_v1,
            expected_login=SYNTHETIC_LOGIN,
            expected_server=SYNTHETIC_SERVER,
            run_mode="prospective_trial",
            vault_root=tmp_path / "live-vault",
        )

    # Prospective trial mode ACCEPTS >= 2026-12-01T00:00:00Z (e.g. 08/12/2026 Free Trial!)
    ts_dec08 = int(datetime(2026, 12, 8, 13, 30, 0, tzinfo=UTC).timestamp())
    f_dec08 = _build_offline_fixture(tmp_path / "f_dec08_trial", base_ts=ts_dec08)
    b_dec08 = hft.harvest_free_trial_forensics(
        source_dir_or_manifest=f_dec08,
        expected_login=SYNTHETIC_LOGIN,
        expected_server=SYNTHETIC_SERVER,
        account_alias="FTMO_TRIAL_DEC08",
        run_mode="prospective_trial",
        vault_root=tmp_path / "live-vault",
    )
    _check(b_dec08["temporal_guard"]["run_mode"] == "prospective_trial", "Expected prospective_trial mode")
    _check(b_dec08["hard_invariants"]["holdout_v1_rows_analysed"] == 0, "Holdout v1 rows must be 0")
    go_dec08 = b_dec08["go_nogo_decision"]
    _check(go_dec08["decision"] == "GO_READY", f"Expected GO_READY, got {go_dec08}")


def test_mocked_readonly_remote_pull_lan_to_ts_fallback_and_creationflags(safe_tmp_dir: Path) -> None:
    tmp_path = safe_tmp_dir
    calls: list[tuple[list[str], int]] = []

    def _fake_probe(
        action: str,
        extra_args: Any = None,
        *,
        host: str | None = None,
        timeout: int = 20,
    ) -> dict[str, Any]:
        if host == "naqex-node1-lan":
            raise RuntimeError("Remote probe failed on naqex-node1-lan (rc=255): Connection timed out")
        if action == "status":
            return {
                "order_send_count": 0,
                "ntp_offset": "+0.032s",
                "heartbeat": {
                    "login": SYNTHETIC_LOGIN,
                    "server": SYNTHETIC_SERVER,
                    "trade_allowed": False,
                },
            }
        return {"order_send_count": 0, "audit_files": ["naqex_exec_audit.csv"]}

    def _fake_subproc_run(cmd: list[str], **kwargs: Any) -> subprocess.CompletedProcess[str]:
        _check("creationflags" in kwargs, f"subprocess.run missing creationflags for cmd={cmd}")
        _check(kwargs["creationflags"] == _NO_WINDOW_FLAGS, f"Unexpected creationflags={kwargs['creationflags']}")
        calls.append((list(cmd), int(kwargs["creationflags"])))
        if cmd[0] == "ssh":
            return subprocess.CompletedProcess(cmd, 0, stdout="naqex_exec_audit.csv\nrandom_unrelated.ex5\n", stderr="")
        if cmd[0] == "scp":
            dst = Path(cmd[-1])
            dst.write_text("utc_ts,symbol,event_type\n", encoding="utf-8")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        raise AssertionError(f"Unexpected binary invoked: {cmd}")

    with (
        patch.object(node_ctl, "run_remote_probe", side_effect=_fake_probe),
        patch.object(hft.subprocess, "run", side_effect=_fake_subproc_run),
    ):
        meta = hft.pull_readonly_trial_artifacts(tmp_path / "staging_mock")

    _check(meta["ssh_alias"] == "naqex-node1-ts", f"Expected fallback to naqex-node1-ts, got {meta}")
    _check(meta["ssh_write_count"] == 0 and meta["order_send_count"] == 0, "Must be strictly read-only")
    _check(meta["pulled_files"] == ["naqex_exec_audit.csv"], f"Must ignore .ex5 and pull only CSV: {meta}")
    _check(len(calls) == 2, f"Expected 1 ssh list + 1 scp pull, got {calls}")
    _check((tmp_path / "staging_mock" / "node_status.json").is_file(), "node_status.json not staged")


# ---------------------------------------------------------------------------
# 3. AST Zero-Popup (`creationflags`), Zero-Assert & Zero-MT5-Import Audit
# ---------------------------------------------------------------------------
def test_ast_zero_missing_creationflags_and_safety_invariants() -> None:
    targets = (
        AI_ENGINES / "quant_factory" / "wave4" / "harvest_free_trial_forensics.py",
        AI_ENGINES / "ops_cloud" / "nfp_cpi_quote_collector.py",
        AI_ENGINES / "ops_cloud" / "node_ctl.py",
        AI_ENGINES / "quant_factory" / "preregister_holdout_v2.py",
    )
    missing_cf: list[str] = []
    checked_calls = 0

    for py_path in targets:
        _check(py_path.is_file(), f"Missing target file: {py_path}")
        tree = ast.parse(py_path.read_text(encoding="utf-8"), filename=str(py_path))
        subproc_aliases = {"subprocess"}
        direct_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        subproc_aliases.add(alias.asname or "subprocess")
            elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                for alias in node.names:
                    if alias.name in _SUBPROCESS_CALL_ATTRS:
                        direct_names.add(alias.asname or alias.name)

        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            call_name: str | None = None
            if (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id in subproc_aliases
                and fn.attr in _SUBPROCESS_CALL_ATTRS
            ):
                call_name = f"{fn.value.id}.{fn.attr}"
            elif isinstance(fn, ast.Name) and fn.id in direct_names:
                call_name = fn.id
            if call_name is not None:
                checked_calls += 1
                if not any(kw.arg == "creationflags" for kw in node.keywords):
                    rel = py_path.relative_to(REPO_ROOT).as_posix()
                    missing_cf.append(f"{rel}:{node.lineno} ({call_name})")

    _check(checked_calls >= 6, f"Expected >= 6 subprocess calls checked across milestone toolkit, got {checked_calls}")
    _check(missing_cf == [], f"subprocess calls missing creationflags: {missing_cf}")

    # Verify harvest_free_trial_forensics.py has ZERO bare assert statements and ZERO MetaTrader5 imports
    hft_path = AI_ENGINES / "quant_factory" / "wave4" / "harvest_free_trial_forensics.py"
    hft_tree = ast.parse(hft_path.read_text(encoding="utf-8"), filename=str(hft_path))
    assert_lines = [n.lineno for n in ast.walk(hft_tree) if isinstance(n, ast.Assert)]
    _check(assert_lines == [], f"Bare assert statements forbidden in harvest_free_trial_forensics.py: {assert_lines}")
    mt5_imports: list[int] = []
    for node in ast.walk(hft_tree):
        if isinstance(node, ast.Import) and any(a.name == "MetaTrader5" for a in node.names):
            mt5_imports.append(node.lineno)
        elif isinstance(node, ast.ImportFrom) and (node.module or "").startswith("MetaTrader5"):
            mt5_imports.append(node.lineno)
    _check(mt5_imports == [], f"MetaTrader5 import forbidden in harvest_free_trial_forensics.py: {mt5_imports}")


# ---------------------------------------------------------------------------
# 4. Verify 01/12 Preregistration & 04/12-10/12 NFP/CPI Collector Preflight
# ---------------------------------------------------------------------------
def test_01_12_preregister_holdout_v2_verify_passes() -> None:
    # Direct API verification
    res = prereg_mod.verify_preregistration(
        repo_root=REPO_ROOT,
        out_dir=REPO_ROOT / prereg_mod.DEFAULT_OUT_SUBDIR,
    )
    _check(res["status"] == "VERIFIED_PASS", f"Unexpected prereg status: {res}")
    _check(res["verified_artifacts"] == 8, f"Expected 8/8 verified artifacts, got {res}")
    _check(res["order_send_count"] == 0 and res["holdout_rows_analysed"] == 0, "Safety counters must be 0")

    # CLI subprocess verification
    proc = subprocess.run(
        [sys.executable, str(AI_ENGINES / "quant_factory" / "preregister_holdout_v2.py"), "--verify"],
        capture_output=True,
        text=True,
        timeout=20,
        creationflags=_NO_WINDOW_FLAGS,
    )
    _check(proc.returncode == 0, f"preregister_holdout_v2 --verify failed rc={proc.returncode}: {proc.stderr}")
    payload = json.loads(proc.stdout)
    _check(payload["status"] == "VERIFIED_PASS" and payload["verified_artifacts"] == 8, f"Bad CLI verify: {payload}")
    _check(payload["file_sha256"] == res["file_sha256"], "CLI vs API file_sha256 mismatch")


def test_04_12_and_10_12_nfp_cpi_quote_collector_preflight_offline_only(capsys: pytest.CaptureFixture[str]) -> None:
    # Deterministic offline check (works even in isolated/Linux CI without w32tm)
    fake_ntp_ok = {
        "ok": True,
        "ntp_host": "time.cloudflare.com",
        "offset_ms": 42.5,
        "samples_ms": [42.1, 42.5, 43.0],
        "threshold_ms": 1000.0,
    }
    with patch.object(nfp_mod, "measure_ntp_offset_ms", return_value=fake_ntp_ok):
        rc = nfp_mod.main(["--event", "SMOKE_PREFLIGHT", "--preflight-offline-only"])
    _check(rc == 0, f"Expected exit 0 for SMOKE_PREFLIGHT --preflight-offline-only, got {rc}")
    out_ok = json.loads(capsys.readouterr().out)
    _check(out_ok["status"] == "PREFLIGHT_OK" and out_ok["preflight_ok"] is True, f"Bad preflight output: {out_ok}")
    _check(out_ok["record_tier"] == "QUOTE_ONLY" and out_ok["order_send_count"] == 0, "Must be QUOTE_ONLY/OrderSend=0")
    _check(out_ok["csv_columns_count"] == 23, f"Expected 23 CSV columns, got {out_ok['csv_columns_count']}")
    _check(out_ok["red_news_calendar_check"]["ok"] is True, f"Calendar check failed: {out_ok}")
    _check(out_ok["red_news_calendar_check"]["found"]["US_NFP_20261204"] is True, "Missing US_NFP_20261204")
    _check(out_ok["red_news_calendar_check"]["found"]["US_CPI_20261210"] is True, "Missing US_CPI_20261210")

    # Fail-closed check when NTP >= 1000 ms
    fake_ntp_bad = {
        "ok": False,
        "ntp_host": "time.cloudflare.com",
        "offset_ms": 1250.0,
        "samples_ms": [1250.0],
        "threshold_ms": 1000.0,
    }
    with patch.object(nfp_mod, "measure_ntp_offset_ms", return_value=fake_ntp_bad):
        rc_bad = nfp_mod.main(["--event", "SMOKE_PREFLIGHT", "--preflight-offline-only"])
    _check(rc_bad == 2, f"Expected exit 2 on NTP drift >= 1000 ms, got {rc_bad}")
    out_bad = json.loads(capsys.readouterr().out)
    _check(out_bad["status"] == "PREFLIGHT_FAILED" and out_bad["preflight_ok"] is False, f"Should fail: {out_bad}")

    # Real CLI subprocess execution check (strictly offline-preflight, zero MT5)
    proc = subprocess.run(
        [
            sys.executable,
            str(AI_ENGINES / "ops_cloud" / "nfp_cpi_quote_collector.py"),
            "--event",
            "SMOKE_PREFLIGHT",
            "--preflight-offline-only",
        ],
        capture_output=True,
        text=True,
        timeout=25,
        creationflags=_NO_WINDOW_FLAGS,
    )
    cli_doc = json.loads(proc.stdout)
    _check(cli_doc["record_tier"] == "QUOTE_ONLY" and cli_doc["order_send_count"] == 0, "CLI must be QUOTE_ONLY")
    _check(cli_doc["red_news_calendar_check"]["ok"] is True, "CLI red-news calendar check must pass")
    if os.name == "nt":
        _check(proc.returncode == 0 and cli_doc["preflight_ok"] is True, f"Windows CLI preflight failed: {cli_doc}")
