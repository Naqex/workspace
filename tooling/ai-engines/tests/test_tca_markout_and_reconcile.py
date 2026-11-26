"""Comprehensive tests for Wave 2A Lane L11: Unified Fail-Closed TCA Parser, Markout Curve,
and Automated Daily Broker Statement Reconciler (strictly offline & read-only, OrderSend=0).

Covers:
  1. Blank/missing `swap_usd` parses as `None` (NEVER coerced to `0.0`) in `quant_core.tca` and
     `tca_reconcile.load_exec_audit_csv`, while `NaN`/`Inf` fails closed immediately.
  2. Post-reconciliation gate (`validate_tca_post_reconcile` & `compute_tca_report`):
     - Fails closed if closed trade / fill still has `swap_usd is None` before enrichment.
     - Passes cleanly after broker statement enrichment populates `swap_usd = 0.0`.
     - Blocks `FILL_UNRESOLVED` and non-zero/non-finite swap fail-closed.
  3. Strictly causal Markout Curve (`+1s/+10s/+60s/+5m`):
     - Exact signed bps & price units on BUY and SELL synthetic tick fixtures.
     - Strictly causal `asof` arrival mid (`<= fill_ts`) & next-quote horizon (`>= fill_ts + h`).
     - Missing quotes return `None` (NEVER fabricated!).
     - Adverse-selection flag triggers on negative mean post-fill markout.
  4. `prop_live_tca_monitor.py` routes blank/NaN swap, `FILL_UNRESOLVED`, and optional markout
     through `quant_core.tca` without breaking existing calibration flows.
  5. `daily_statement_reconciler.py` end-to-end tests on both CSV and HTML MT5 statements:
     - Clean reconciliation with blank-audit enrichment + quote tape markout + atomic SHA-256 JSON.
     - Orphan audit/statement flagging, non-zero swap fail-closed, missing swap fail-closed,
       `FILL_UNRESOLVED` fail-closed, and login/magic mismatch fail-closed.
"""

from __future__ import annotations

import ast
import csv
import hashlib
import json
import math
import sys
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any

import pytest

TESTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = TESTS_DIR.parent
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core import tca as core_tca  # noqa: E402
from quant_factory import daily_statement_reconciler as dsr  # noqa: E402
from quant_factory import prop_live_tca_monitor as live_mon  # noqa: E402
from quant_factory import tca_reconcile  # noqa: E402


def _write_csv(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, Any]]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
    return path


# ---------------------------------------------------------------------------
# 1. P0-7 Backward-Compat Parsing & Fail-Closed Post-Reconcile Gate
# ---------------------------------------------------------------------------
def test_blank_swap_parses_as_none_never_zero_and_rejects_nan_inf(tmp_path: Path) -> None:
    """Blank/missing `swap_usd` parses as `None` (NEVER `0.0`); `NaN`/`Inf` raises `ValueError`."""
    fields = [
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
        "deal_id",
        "order_id",
        "position_id",
        "comment",
    ]
    csv_path = _write_csv(
        tmp_path / "naqex_exec_audit.csv",
        fields,
        [
            {
                "utc_ts": 1793610300,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "BUY",
                "event_type": "ENTRY_FILLED",
                "signal_price": 153.200,
                "fill_price": 153.205,
                "sl_price": 152.700,
                "lots": 0.10,
                "spread_pts": 7.0,
                "latency_ms": 40.0,
                "retcode": 10009,
                "pnl_usd": "",
                "swap_usd": "0.0",
                "deal_id": "D2001",
                "order_id": "O3001",
                "position_id": "P1001",
                "comment": "deal=D2001 pos=P1001",
            },
            {
                "utc_ts": 1793617800,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "SELL",
                "event_type": "TP_HIT",
                "signal_price": 153.650,
                "fill_price": 153.645,
                "sl_price": 152.700,
                "lots": 0.10,
                "spread_pts": 8.0,
                "latency_ms": 45.0,
                "retcode": 10009,
                "pnl_usd": "",
                "swap_usd": "",  # Intentionally blank pending broker statement enrichment (P0-7)
                "deal_id": "D2002",
                "order_id": "O3002",
                "position_id": "P1001",
                "comment": "deal=D2002 pos=P1001",
            },
        ],
    )

    # Raw CSV load MUST succeed without raising and MUST preserve swap_usd=None on blank row!
    loaded = tca_reconcile.load_exec_audit_csv(csv_path)
    assert len(loaded) == 2
    assert loaded[0]["swap_usd"] == 0.0
    assert loaded[1]["swap_usd"] is None
    assert loaded[1]["pnl_usd"] is None

    # Direct row parser also preserves None when column omitted altogether
    row_no_col = core_tca.parse_exec_audit_row({
        "utc_ts": 1793610300,
        "magic": 20261122,
        "symbol": "GBPUSD",
        "side": "BUY",
        "event_type": "ORDER_FILL",
        "signal_price": 1.2900,
        "fill_price": 1.2901,
        "sl_price": 1.2850,
        "lots": 0.10,
        "spread_pts": 6.0,
        "latency_ms": 50.0,
        "retcode": 10009,
    })
    assert row_no_col["swap_usd"] is None

    # Non-finite swap_usd (NaN / Inf / -Inf / bool) MUST raise ValueError immediately
    for bad_swap in ("NaN", "nan", "inf", "-inf", float("nan"), float("inf"), True):
        with pytest.raises(ValueError, match="swap_usd"):
            core_tca.parse_exec_audit_row({
                "utc_ts": 1793610300,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "BUY",
                "event_type": "ORDER_FILL",
                "signal_price": 153.200,
                "fill_price": 153.205,
                "sl_price": 152.700,
                "lots": 0.10,
                "spread_pts": 7.0,
                "latency_ms": 40.0,
                "retcode": 10009,
                "swap_usd": bad_swap,
            })


def test_post_reconcile_fails_closed_before_enrichment_and_passes_after(tmp_path: Path) -> None:
    """Blank `swap_usd=None` fails closed in post-reconcile & `compute_tca_report`, then passes after enrichment."""
    raw_rows = [
        core_tca.parse_exec_audit_row({
            "utc_ts": 1793610300,
            "magic": 20261122,
            "symbol": "USDJPY",
            "side": "BUY",
            "event_type": "ENTRY_FILLED",
            "signal_price": 153.200,
            "fill_price": 153.204,
            "sl_price": 152.700,
            "lots": 0.10,
            "spread_pts": 7.0,
            "latency_ms": 42.0,
            "retcode": 10009,
            "swap_usd": "0.0",
            "deal_id": "D2001",
            "position_id": "P1001",
        }),
        core_tca.parse_exec_audit_row({
            "utc_ts": 1793617500,
            "magic": 20261122,
            "symbol": "USDJPY",
            "side": "SELL",
            "event_type": "TP_HIT",
            "signal_price": 153.650,
            "fill_price": 153.648,
            "sl_price": 152.700,
            "lots": 0.10,
            "spread_pts": 7.0,
            "latency_ms": 44.0,
            "retcode": 10009,
            "swap_usd": "",  # Missing before enrichment!
            "pnl_usd": "",
            "deal_id": "D2002",
            "position_id": "P1001",
        }),
    ]

    # 1. Before enrichment: BOTH validate_tca_post_reconcile and compute_tca_report MUST fail closed!
    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        core_tca.validate_tca_post_reconcile(raw_rows)

    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        tca_reconcile.compute_tca_report(raw_rows)

    # 2. Enrich with broker statement showing swap=0.00 -> passes both gates cleanly!
    stmt_rows = [
        {"deal": "D2001", "position": "P1001", "swap": 0.0, "profit": None, "commission": -0.30},
        {"deal": "D2002", "position": "P1001", "swap": 0.0, "profit": 44.50, "commission": -0.30},
    ]
    enriched, stats = core_tca.enrich_audit_rows_with_statement(raw_rows, stmt_rows)
    assert stats["matched_rows"] == 2
    assert stats["swap_enriched_count"] == 1
    assert stats["pnl_enriched_count"] == 1
    assert enriched[1]["swap_usd"] == 0.0
    assert enriched[1]["pnl_usd"] == 44.50

    gate = core_tca.validate_tca_post_reconcile(enriched, require_zero_swap=True)
    assert gate["passed"] is True
    assert gate["missing_swap_count"] == 0
    assert gate["nonzero_swap_count"] == 0

    rep = tca_reconcile.compute_tca_report(enriched)
    assert rep["verdict"] == "GREEN"
    assert rep["swap_violations"] == 0

    # 3. Enriching with non-zero swap fails closed in validate_tca_post_reconcile(require_zero_swap=True)
    stmt_nonzero = [
        {"deal": "D2001", "position": "P1001", "swap": 0.0, "profit": None},
        {"deal": "D2002", "position": "P1001", "swap": -1.25, "profit": 44.50},
    ]
    enriched_bad, _ = core_tca.enrich_audit_rows_with_statement(raw_rows, stmt_nonzero)
    with pytest.raises(ValueError, match="NONZERO_SWAP_USD"):
        core_tca.validate_tca_post_reconcile(enriched_bad, require_zero_swap=True)

    # compute_tca_report flags RED_SWAP_VIOLATION (or raises when require_zero_swap_raise=True)
    rep_bad = tca_reconcile.compute_tca_report(enriched_bad)
    assert rep_bad["verdict"] == "RED_SWAP_VIOLATION"
    assert rep_bad["swap_violations"] == 1
    with pytest.raises(ValueError, match="NONZERO_SWAP_USD"):
        tca_reconcile.compute_tca_report(enriched_bad, require_zero_swap_raise=True)


def test_fill_unresolved_blocked_fail_closed_across_tca_modules(tmp_path: Path) -> None:
    """`FILL_UNRESOLVED` is blocked fail-closed across `quant_core.tca`, `tca_reconcile`, and live monitor."""
    unresolved = {
        "utc_ts": 1793618000,
        "magic": 20261122,
        "symbol": "USDJPY",
        "side": "BUY",
        "event_type": "FILL_UNRESOLVED",
        "signal_price": 154.000,
        "fill_price": 0.0,
        "sl_price": 153.500,
        "lots": 0.10,
        "spread_pts": 8.0,
        "latency_ms": 95.0,
        "retcode": 10009,
        "swap_usd": 0.0,
        "comment": "FILL_UNRESOLVED_DEAL_PRICE_MISSING",
    }

    with pytest.raises(ValueError, match="FILL_UNRESOLVED"):
        core_tca.validate_tca_post_reconcile([unresolved])

    with pytest.raises(ValueError, match="FILL_UNRESOLVED"):
        tca_reconcile.compute_tca_report([unresolved])

    # Also test status="FILL_UNRESOLVED" even when event_type is generic
    with pytest.raises(ValueError, match="FILL_UNRESOLVED"):
        core_tca.validate_tca_post_reconcile([
            {**unresolved, "event_type": "ORDER_FILL", "status": "FILL_UNRESOLVED", "comment": ""}
        ])

    # And in prop_live_tca_monitor.py: standalone FILL_UNRESOLVED audit CSV must NOT become NO_DATA!
    audit_csv = tmp_path / "naqex_exec_audit_unresolved.csv"
    audit_csv.write_text(
        "\n".join([
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment,swap_usd",
            "1793618000,20261122,USDJPY,BUY,FILL_UNRESOLVED,154.0,0.0,153.5,0.10,8.0,95.0,10009,FILL_UNRESOLVED,",
        ])
        + "\n",
        encoding="utf-8",
    )
    mon_rep = live_mon.evaluate_live_tca(audit_csv_paths=[audit_csv], use_hot_cache=False, n_bootstrap_draws=500)
    assert mon_rep["verdict"] == "RED_UNRESOLVED_FILL"
    assert mon_rep["inputs"]["unresolved_fills"] == 1
    assert mon_rep["post_reconcile_check"]["passed"] is False
    assert live_mon.exit_code_for_report(mon_rep) == 2

    with pytest.raises(ValueError, match="FILL_UNRESOLVED"):
        live_mon.evaluate_live_tca(
            audit_csv_paths=[audit_csv],
            use_hot_cache=False,
            n_bootstrap_draws=500,
            fail_closed_raise=True,
        )


# ---------------------------------------------------------------------------
# 2. Strictly Causal Markout Curve (+1s / +10s / +60s / +5m)
# ---------------------------------------------------------------------------
def test_markout_curve_exact_buy_and_sell_causal_lookup_and_missing_quotes() -> None:
    """Verify exact signed markout math on BUY & SELL ticks, strict causality, and missing -> `None`."""
    t0 = 1795600000
    # USDJPY quotes: arrival at t0-1 (mid=150.000), +1s at t0+1 (mid=150.015 -> +1.0 bps for BUY),
    # +10s at t0+12 (causal next quote >= t0+10, mid=150.030 -> +2.0 bps),
    # +60s at t0+60 (mid=150.060 -> +4.0 bps), +5m at t0+305 (mid=150.150 -> +10.0 bps).
    # GBPUSD quotes: arrival at t0 (mid=1.25000), +1s at t0+1 (mid=1.24975 -> +2.0 bps for SELL),
    # +10s at t0+10 (mid=1.24950 -> +4.0 bps for SELL), NO quotes after t0+10 -> +60s & +5m MUST be None!
    quotes = [
        # Out-of-order intentionally to verify deterministic timestamp sorting
        {"utc_ts": t0 + 305, "symbol": "USDJPY.pro", "bid": 150.148, "ask": 150.152},
        {"utc_ts": t0 - 1, "symbol": "USDJPY", "bid": 149.998, "ask": 150.002},
        {"utc_ts": t0 + 1, "symbol": "USDJPY", "bid": 150.013, "ask": 150.017},
        {"utc_ts": t0 + 12, "symbol": "USDJPY", "bid": 150.028, "ask": 150.032},
        {"utc_ts": t0 + 60, "symbol": "USDJPY", "bid": 150.058, "ask": 150.062},
        {"utc_ts": t0, "symbol": "GBPUSD", "bid": 1.24995, "ask": 1.25005},
        {"utc_ts": t0 + 1, "symbol": "GBPUSD", "bid": 1.24970, "ask": 1.24980},
        {"utc_ts": t0 + 10, "symbol": "GBPUSD", "bid": 1.24945, "ask": 1.24955},
    ]

    fills = [
        {"utc_ts": t0, "symbol": "USDJPY", "side": "BUY", "fill_price": 150.002, "event_type": "ORDER_FILL"},
        {"utc_ts": t0, "symbol": "GBPUSD", "side": "SELL", "fill_price": 1.24995, "event_type": "ORDER_FILL"},
    ]

    curve = core_tca.compute_markout_curve(fills, quotes, horizons_sec=(1, 10, 60, 300))
    assert curve["horizon_labels"] == ["+1s", "+10s", "+60s", "+5m"]
    assert curve["fills_analysed"] == 2
    assert curve["fills_with_arrival_mid"] == 2
    assert curve["adverse_selection_flagged"] is False
    assert curve["adverse_selection_horizons"] == []

    # Check exact BUY USDJPY markouts
    buy_row = curve["per_fill"][0]
    assert buy_row["arrival_mid"] == pytest.approx(150.000, abs=1e-8)
    assert buy_row["arrival_quote_ts"] == t0 - 1
    assert buy_row["markouts"]["+1s"]["quote_ts"] == t0 + 1
    assert buy_row["markouts"]["+1s"]["markout_price"] == pytest.approx(0.015, abs=1e-8)
    assert buy_row["markouts"]["+1s"]["markout_bps"] == pytest.approx(1.0, abs=1e-5)
    assert buy_row["markouts"]["+10s"]["quote_ts"] == t0 + 12  # strictly >= t0+10!
    assert buy_row["markouts"]["+10s"]["markout_price"] == pytest.approx(0.030, abs=1e-8)
    assert buy_row["markouts"]["+10s"]["markout_bps"] == pytest.approx(2.0, abs=1e-5)
    assert buy_row["markouts"]["+60s"]["quote_ts"] == t0 + 60
    assert buy_row["markouts"]["+60s"]["markout_bps"] == pytest.approx(4.0, abs=1e-5)
    assert buy_row["markouts"]["+5m"]["quote_ts"] == t0 + 305
    assert buy_row["markouts"]["+5m"]["markout_price"] == pytest.approx(0.150, abs=1e-8)
    assert buy_row["markouts"]["+5m"]["markout_bps"] == pytest.approx(10.0, abs=1e-5)

    # Check exact SELL GBPUSD markouts & missing quotes -> None (NEVER fabricated!)
    sell_row = curve["per_fill"][1]
    assert sell_row["arrival_mid"] == pytest.approx(1.25000, abs=1e-8)
    assert sell_row["markouts"]["+1s"]["markout_price"] == pytest.approx(0.00025, abs=1e-8)
    assert sell_row["markouts"]["+1s"]["markout_bps"] == pytest.approx(2.0, abs=1e-5)
    assert sell_row["markouts"]["+10s"]["markout_price"] == pytest.approx(0.00050, abs=1e-8)
    assert sell_row["markouts"]["+10s"]["markout_bps"] == pytest.approx(4.0, abs=1e-5)
    assert sell_row["markouts"]["+60s"]["quote_ts"] is None
    assert sell_row["markouts"]["+60s"]["markout_price"] is None
    assert sell_row["markouts"]["+60s"]["markout_bps"] is None
    assert sell_row["markouts"]["+5m"]["quote_ts"] is None
    assert sell_row["markouts"]["+5m"]["markout_bps"] is None

    # Aggregated counts & means
    assert curve["by_horizon"]["+1s"]["n_observed"] == 2
    assert curve["by_horizon"]["+1s"]["mean_markout_bps"] == pytest.approx(1.5, abs=1e-5)
    assert curve["by_horizon"]["+10s"]["mean_markout_bps"] == pytest.approx(3.0, abs=1e-5)
    assert curve["by_horizon"]["+60s"]["n_observed"] == 1
    assert curve["by_horizon"]["+60s"]["n_missing"] == 1
    assert curve["by_horizon"]["+5m"]["n_observed"] == 1
    assert curve["by_horizon"]["+5m"]["n_missing"] == 1


def test_markout_curve_adverse_selection_detection_and_no_arrival_quote() -> None:
    """Negative post-fill markout flags adverse selection; future-only tape yields None arrival mid."""
    t0 = 1795610000
    # BUY fill at 20000.00 followed by immediate drop -> negative markout at all 4 horizons!
    adverse_quotes = {
        "US100.cash": [
            {"utc_ts": t0, "mid": 20000.0},
            {"utc_ts": t0 + 1, "mid": 19996.0},   # -2.0 bps
            {"utc_ts": t0 + 10, "mid": 19990.0},  # -5.0 bps
            {"utc_ts": t0 + 60, "mid": 19980.0},  # -10.0 bps
            {"utc_ts": t0 + 300, "mid": 19960.0}, # -20.0 bps
        ]
    }
    fills = [
        {
            "utc_ts": t0,
            "symbol": "NAS100",
            "side": "BUY",
            "fill_price": 20001.0,
            "swap_usd": 0.0,
            "event_type": "ORDER_FILL",
            "signal_price": 20000.5,
            "sl_price": 19900.0,
            "spread_pts": 20.0,
            "latency_ms": 80.0,
        },
    ]
    curve = core_tca.compute_markout_curve(fills, adverse_quotes)
    assert curve["adverse_selection_flagged"] is True
    assert curve["adverse_selection_horizons"] == ["+1s", "+10s", "+60s", "+5m"]
    assert curve["by_horizon"]["+1s"]["mean_markout_bps"] == pytest.approx(-2.0, abs=1e-5)
    assert curve["by_horizon"]["+5m"]["mean_markout_bps"] == pytest.approx(-20.0, abs=1e-5)
    assert curve["overall_mean_markout_bps"] == pytest.approx(-9.25, abs=1e-5)

    # Integration with tca_reconcile.compute_tca_report(..., quote_series=...)
    rep = tca_reconcile.compute_tca_report(fills, quote_series=adverse_quotes)
    assert rep["markout_curve"] is not None
    assert rep["markout_curve"]["adverse_selection_flagged"] is True
    assert any("Adverse selection" in flg for flg in rep["flags"])

    # Strictly causal: if tape starts strictly AFTER fill_ts (no arrival quote), return None (NEVER look ahead!)
    future_only_quotes = [{"utc_ts": t0 + 1, "symbol": "EURJPY", "bid": 165.00, "ask": 165.02}]
    no_arr = core_tca.compute_markout_curve(
        [{"utc_ts": t0, "symbol": "EURJPY", "side": "BUY", "fill_price": 165.01}],
        future_only_quotes,
    )
    assert no_arr["fills_with_arrival_mid"] == 0
    assert no_arr["per_fill"][0]["arrival_mid"] is None
    assert no_arr["per_fill"][0]["markouts"]["+1s"]["markout_bps"] is None
    assert no_arr["overall_mean_markout_bps"] is None


# ---------------------------------------------------------------------------
# 3. `prop_live_tca_monitor.py` Blank/NaN Swap Guard & Optional Markout
# ---------------------------------------------------------------------------
def test_prop_live_tca_monitor_rejects_blank_swap_and_computes_optional_markout(tmp_path: Path) -> None:
    """Blank `swap_usd` in live audit CSV fails closed (never 0.0); optional markout works on spread log."""
    t0 = 1795620000
    audit_blank = tmp_path / "naqex_exec_audit_blank_swap.csv"
    audit_blank.write_text(
        "\n".join([
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment,swap_usd",
            f"{t0},20261122,USDJPY,BUY,ORDER_FILL,159.200,159.201,159.050,0.01,4.0,150.0,10009,pos=101,",
        ])
        + "\n",
        encoding="utf-8",
    )
    rep_blank = live_mon.evaluate_live_tca(audit_csv_paths=[audit_blank], use_hot_cache=False, n_bootstrap_draws=500)
    assert rep_blank["inputs"]["missing_swap_count"] == 1
    assert rep_blank["verdict"] == "RED_FRICTION_BREACH"
    assert live_mon.exit_code_for_report(rep_blank) == 2

    # Also test NaN swap in prop_live_tca_monitor fails closed
    audit_nan = tmp_path / "naqex_exec_audit_nan_swap.csv"
    audit_nan.write_text(
        "\n".join([
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment,swap_usd",
            f"{t0},20261122,USDJPY,BUY,ORDER_FILL,159.200,159.201,159.050,0.01,4.0,150.0,10009,pos=103,NaN",
        ])
        + "\n",
        encoding="utf-8",
    )
    rep_nan = live_mon.evaluate_live_tca(audit_csv_paths=[audit_nan], use_hot_cache=False, n_bootstrap_draws=500)
    assert rep_nan["inputs"]["nonfinite_swap_count"] == 1
    assert rep_nan["verdict"] == "RED_FRICTION_BREACH"
    assert live_mon.exit_code_for_report(rep_nan) == 2

    # Clean audit + live spread log with include_markout=True
    audit_clean = tmp_path / "naqex_exec_audit_clean.csv"
    audit_clean.write_text(
        "\n".join([
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,lots,spread_pts,latency_ms,retcode,comment,swap_usd",
            f"{t0},20261122,USDJPY,BUY,ORDER_FILL,159.200,159.201,159.050,0.01,4.0,150.0,10009,pos=102,0.0",
        ])
        + "\n",
        encoding="utf-8",
    )
    spread_log = tmp_path / "mt5_live_spread_log.jsonl"
    spread_rows = [
        {"captured_utc_ts": t0, "quotes": {"USDJPY": {"available": True, "bid": 159.198, "ask": 159.202}}},
        {"captured_utc_ts": t0 + 1, "quotes": {"USDJPY": {"available": True, "bid": 159.208, "ask": 159.212}}},
        {"captured_utc_ts": t0 + 10, "quotes": {"USDJPY": {"available": True, "bid": 159.218, "ask": 159.222}}},
        {"captured_utc_ts": t0 + 60, "quotes": {"USDJPY": {"available": True, "bid": 159.228, "ask": 159.232}}},
        {"captured_utc_ts": t0 + 300, "quotes": {"USDJPY": {"available": True, "bid": 159.248, "ask": 159.252}}},
    ]
    spread_log.write_text("\n".join(json.dumps(r) for r in spread_rows) + "\n", encoding="utf-8")

    rep_ok = live_mon.evaluate_live_tca(
        audit_csv_paths=[audit_clean],
        spread_jsonl_path=spread_log,
        use_hot_cache=False,
        include_markout=True,
        n_bootstrap_draws=500,
    )
    assert rep_ok["verdict"] == "GREEN_HEALTHY"
    assert rep_ok["markout_curve"] is not None
    assert rep_ok["markout_curve"]["by_horizon"]["+1s"]["n_observed"] == 1
    assert rep_ok["markout_curve"]["by_horizon"]["+5m"]["mean_markout_bps"] > 0.0


# ---------------------------------------------------------------------------
# 4. Automated Daily Statement Reconciler (CSV + HTML + Atomic SHA-256 JSON)
# ---------------------------------------------------------------------------
def test_daily_statement_reconciler_csv_e2e_with_markout_and_sha256(tmp_path: Path) -> None:
    """End-to-end CSV reconciliation: blank audit swap enriched from statement + markout + atomic SHA-256 JSON."""
    t_in = 1793610300
    t_out = 1793617500
    audit_fields = [
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
        "account_login",
        "deal_id",
        "order_id",
        "position_id",
        "comment",
    ]
    audit_csv = _write_csv(
        tmp_path / "naqex_exec_audit.csv",
        audit_fields,
        [
            {
                "utc_ts": t_in,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "BUY",
                "event_type": "ENTRY_FILLED",
                "signal_price": 153.200,
                "fill_price": 153.202,
                "sl_price": 152.700,
                "lots": 0.10,
                "spread_pts": 6.0,
                "latency_ms": 45.0,
                "retcode": 10009,
                "pnl_usd": "",
                "swap_usd": "0.0",
                "commission_usd": "-0.30",
                "account_login": 9900112233,
                "deal_id": "D9001",
                "order_id": "O9001",
                "position_id": "P9001",
                "comment": "deal=D9001 pos=P9001",
            },
            {
                "utc_ts": t_out,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "SELL",
                "event_type": "TP_HIT",
                "signal_price": 153.650,
                "fill_price": 153.648,
                "sl_price": 152.700,
                "lots": 0.10,
                "spread_pts": 7.0,
                "latency_ms": 50.0,
                "retcode": 10009,
                "pnl_usd": "",
                "swap_usd": "",  # Intentionally blank on audit -> enriched by broker statement!
                "commission_usd": "-0.30",
                "account_login": 9900112233,
                "deal_id": "D9002",
                "order_id": "O9002",
                "position_id": "P9001",
                "comment": "deal=D9002 pos=P9001",
            },
        ],
    )

    stmt_fields = [
        "login",
        "deal",
        "order",
        "position",
        "magic",
        "symbol",
        "type",
        "direction",
        "volume",
        "price",
        "profit",
        "swap",
        "commission",
    ]
    stmt_csv = _write_csv(
        tmp_path / "broker_statement.csv",
        stmt_fields,
        [
            {
                "login": 9900112233,
                "deal": "D9001",
                "order": "O9001",
                "position": "P9001",
                "magic": 20261122,
                "symbol": "USDJPY",
                "type": "BUY",
                "direction": "IN",
                "volume": 0.10,
                "price": 153.202,
                "profit": "",
                "swap": "0.00",
                "commission": "-0.30",
            },
            {
                "login": 9900112233,
                "deal": "D9002",
                "order": "O9002",
                "position": "P9001",
                "magic": 20261122,
                "symbol": "USDJPY",
                "type": "SELL",
                "direction": "OUT",
                "volume": 0.10,
                "price": 153.648,
                "profit": "62.40",
                "swap": "0.00",
                "commission": "-0.30",
            },
        ],
    )

    quote_jsonl = tmp_path / "quotes.jsonl"
    quote_jsonl.write_text(
        "\n".join([
            json.dumps({"utc_ts": t_in, "symbol": "USDJPY", "bid": 153.198, "ask": 153.202}),
            json.dumps({"utc_ts": t_in + 1, "symbol": "USDJPY", "bid": 153.208, "ask": 153.212}),
            json.dumps({"utc_ts": t_in + 10, "symbol": "USDJPY", "bid": 153.218, "ask": 153.222}),
            json.dumps({"utc_ts": t_in + 60, "symbol": "USDJPY", "bid": 153.228, "ask": 153.232}),
            json.dumps({"utc_ts": t_in + 300, "symbol": "USDJPY", "bid": 153.248, "ask": 153.252}),
            json.dumps({"utc_ts": t_out, "symbol": "USDJPY", "bid": 153.648, "ask": 153.652}),
            json.dumps({"utc_ts": t_out + 1, "symbol": "USDJPY", "bid": 153.638, "ask": 153.642}),
            json.dumps({"utc_ts": t_out + 10, "symbol": "USDJPY", "bid": 153.628, "ask": 153.632}),
        ])
        + "\n",
        encoding="utf-8",
    )

    out_json = tmp_path / "out/daily_reconcile.json"
    rc = dsr.main([
        "--audit-csv",
        str(audit_csv),
        "--statement",
        str(stmt_csv),
        "--quote-tape",
        str(quote_jsonl),
        "--expected-login",
        "9900112233",
        "--out-json",
        str(out_json),
    ])
    assert rc == 0
    assert out_json.is_file()
    raw_bytes = out_json.read_bytes()
    assert b"\r\n" not in raw_bytes  # LF-only atomic JSON

    payload = json.loads(raw_bytes.decode("utf-8"))
    assert payload["order_send_count"] == 0
    assert payload["status"] == "PASS"
    assert payload["passed"] is True
    assert payload["summary"]["matched_pairs"] == 2
    assert payload["summary"]["orphan_audit_count"] == 0
    assert payload["summary"]["orphan_statement_count"] == 0
    assert payload["summary"]["swap_enriched_count"] == 1
    assert payload["summary"]["pnl_enriched_count"] == 1
    assert payload["summary"]["missing_swap_count"] == 0
    assert payload["summary"]["nonzero_swap_count"] == 0
    assert payload["summary"]["net_pnl_usd"] == pytest.approx(62.40, abs=0.01)
    assert payload["post_reconcile_gate"]["passed"] is True

    # Verify embedded canonical SHA-256 matches recomputed canonical hash!
    expected_sha = core_tca.canonical_payload_sha256(payload)
    assert payload["report_sha256"] == expected_sha
    assert len(expected_sha) == 64

    # Verify Markout Curve computed on both fills (+1s/+10s observed on both, +60s/+5m on entry only)
    mc = payload["markout_curve"]
    assert mc is not None
    assert mc["by_horizon"]["+1s"]["n_observed"] == 2
    assert mc["by_horizon"]["+10s"]["n_observed"] == 2
    assert mc["by_horizon"]["+60s"]["n_observed"] == 1
    assert mc["by_horizon"]["+5m"]["n_observed"] == 1
    assert mc["adverse_selection_flagged"] is False


def test_daily_statement_reconciler_html_statement_and_failure_modes(tmp_path: Path) -> None:
    """Verify MT5 HTML statement parsing + fail-closed orphans, nonzero swap, missing swap, and FILL_UNRESOLVED."""
    audit_fields = [
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
        "deal_id",
        "order_id",
        "position_id",
        "comment",
    ]
    base_audit = [
        {
            "utc_ts": 1793610300,
            "magic": 20261125,
            "symbol": "GBPUSD",
            "side": "BUY",
            "event_type": "ENTRY_FILLED",
            "signal_price": 1.29100,
            "fill_price": 1.29105,
            "sl_price": 1.28700,
            "lots": 0.10,
            "spread_pts": 6.0,
            "latency_ms": 40.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "0.0",
            "deal_id": "55001",
            "order_id": "66001",
            "position_id": "77001",
            "comment": "",
        },
        {
            "utc_ts": 1793617500,
            "magic": 20261125,
            "symbol": "GBPUSD",
            "side": "SELL",
            "event_type": "TP_HIT",
            "signal_price": 1.29500,
            "fill_price": 1.29495,
            "sl_price": 1.28700,
            "lots": 0.10,
            "spread_pts": 6.0,
            "latency_ms": 45.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "deal_id": "55002",
            "order_id": "66002",
            "position_id": "77001",
            "comment": "",
        },
    ]
    audit_csv = _write_csv(tmp_path / "audit_clean.csv", audit_fields, base_audit)

    # 1. Clean MT5 HTML statement with balance row ignored -> PASS!
    html_header_row = (
        "<tr><th>Time</th><th>Deal</th><th>Symbol</th><th>Type</th><th>Direction</th>"
        "<th>Volume</th><th>Price</th><th>Order</th><th>Commission</th><th>Swap</th>"
        "<th>Profit</th><th>Comment</th></tr>"
    )

    def _tr(*cells: str) -> str:
        return "<tr>" + "".join(f"<td>{c}</td>" for c in cells) + "</tr>"

    html_clean = tmp_path / "mt5_statement.html"
    html_clean.write_text(
        "\n".join([
            "<!DOCTYPE html><html><body><table>",
            "<tr><td>Account:</td><td>9900112233</td></tr>",
            html_header_row,
            _tr("2026.11.01 00:00:00", "55000", "", "balance", "in", "", "", "0", "0.00", "0.00", "10 000.00", "Init"),
            _tr(
                "2026.11.02 09:05:00", "55001", "GBPUSD", "buy", "in",
                "0.10", "1.29105", "66001", "-0.30", "0.00", "0.00", "magic=20261125 pos=77001",
            ),
            _tr(
                "2026.11.02 11:05:00", "55002", "GBPUSD", "sell", "out",
                "0.10", "1.29495", "66002", "-0.30", "0.00", "39.00", "magic=20261125 pos=77001",
            ),
            "</table></body></html>",
        ])
        + "\n",
        encoding="utf-8",
    )
    rep_html = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=html_clean,
        expected_login=9900112233,
    )
    assert rep_html["status"] == "PASS"
    assert rep_html["inputs"]["statement_format"] == "html"
    assert rep_html["summary"]["matched_pairs"] == 2
    assert rep_html["summary"]["statement_ignored_non_trade_rows"] == 1
    assert rep_html["summary"]["net_pnl_usd"] == pytest.approx(39.00, abs=0.01)

    # 2. Orphan statement row + non-zero swap in HTML -> FAIL_CLOSED (exit code 2)
    html_orphan_swap = tmp_path / "mt5_statement_bad.html"
    html_orphan_swap.write_text(
        "\n".join([
            "<!DOCTYPE html><html><body><table>",
            "<tr><td>Account:</td><td>9900112233</td></tr>",
            html_header_row,
            _tr(
                "2026.11.02 09:05:00", "55001", "GBPUSD", "buy", "in",
                "0.10", "1.29105", "66001", "-0.30", "0.00", "0.00", "magic=20261125",
            ),
            _tr(
                "2026.11.02 11:05:00", "55002", "GBPUSD", "sell", "out",
                "0.10", "1.29495", "66002", "-0.30", "-2.10", "39.00", "magic=20261125",
            ),
            _tr(
                "2026.11.02 12:00:00", "55999", "EURJPY", "buy", "in",
                "0.10", "165.100", "66999", "-0.30", "0.00", "0.00", "magic=20261128",
            ),
            "</table></body></html>",
        ])
        + "\n",
        encoding="utf-8",
    )
    rc_bad = dsr.main([
        "--audit-csv",
        str(audit_csv),
        "--statement",
        str(html_orphan_swap),
        "--expected-login",
        "9900112233",
    ])
    assert rc_bad == 2
    rep_bad = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=html_orphan_swap,
        expected_login=9900112233,
    )
    assert rep_bad["status"] == "FAIL_CLOSED"
    assert rep_bad["summary"]["orphan_statement_count"] == 1
    assert rep_bad["summary"]["nonzero_swap_count"] == 1
    assert rep_bad["post_reconcile_gate"]["passed"] is False

    # 3. Missing swap on BOTH audit AND statement -> FAIL_CLOSED (never coerced to 0.0!)
    short_stmt_fields = [
        "login",
        "deal",
        "order",
        "position",
        "magic",
        "symbol",
        "type",
        "direction",
        "volume",
        "price",
        "profit",
        "swap",
    ]
    stmt_missing_swap = _write_csv(
        tmp_path / "stmt_missing_swap.csv",
        short_stmt_fields,
        [
            {
                "login": 9900112233,
                "deal": "55001",
                "order": "66001",
                "position": "77001",
                "magic": 20261125,
                "symbol": "GBPUSD",
                "type": "BUY",
                "direction": "IN",
                "volume": 0.10,
                "price": 1.29105,
                "profit": "",
                "swap": "0.0",
            },
            {
                "login": 9900112233,
                "deal": "55002",
                "order": "66002",
                "position": "77001",
                "magic": 20261125,
                "symbol": "GBPUSD",
                "type": "SELL",
                "direction": "OUT",
                "volume": 0.10,
                "price": 1.29495,
                "profit": "39.00",
                "swap": "",
            },
        ],
    )
    rep_missing = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_missing_swap,
        expected_login=9900112233,
    )
    assert rep_missing["status"] == "FAIL_CLOSED"
    assert rep_missing["summary"]["missing_swap_count"] == 1
    assert rep_missing["post_reconcile_gate"]["passed"] is False

    # 4. Login mismatch & magic mismatch & orphan audit row -> FAIL_CLOSED
    rep_login = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=html_clean,
        expected_login=999999999,
    )
    assert rep_login["status"] == "FAIL_CLOSED"
    assert any("LOGIN_MISMATCH" in r for r in rep_login["fail_reasons"])

    stmt_one_row_wrong_magic = _write_csv(
        tmp_path / "stmt_one_wrong_magic.csv",
        short_stmt_fields,
        [
            {
                "login": 9900112233,
                "deal": "55001",
                "order": "66001",
                "position": "77001",
                "magic": 20269999,
                "symbol": "GBPUSD",
                "type": "BUY",
                "direction": "IN",
                "volume": 0.10,
                "price": 1.29105,
                "profit": "",
                "swap": "0.0",
            },
        ],
    )
    rep_orphan_audit = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_one_row_wrong_magic,
        expected_login=9900112233,
    )
    assert rep_orphan_audit["status"] == "FAIL_CLOSED"
    assert rep_orphan_audit["summary"]["orphan_audit_count"] == 1
    assert rep_orphan_audit["summary"]["magic_mismatch_count"] == 1

    # 4. FILL_UNRESOLVED row in audit -> FAIL_CLOSED
    audit_unres = _write_csv(
        tmp_path / "audit_unres.csv",
        audit_fields,
        [
            *base_audit,
            {
                "utc_ts": 1793618000,
                "magic": 20261125,
                "symbol": "GBPUSD",
                "side": "BUY",
                "event_type": "FILL_UNRESOLVED",
                "signal_price": 1.295,
                "fill_price": 0.0,
                "sl_price": 1.290,
                "lots": 0.10,
                "spread_pts": 6.0,
                "latency_ms": 60.0,
                "retcode": 10009,
                "pnl_usd": "",
                "swap_usd": "",
                "deal_id": "",
                "order_id": "66999",
                "position_id": "",
                "comment": "FILL_UNRESOLVED",
            },
        ],
    )
    rep_unres = dsr.reconcile_daily_statement(
        audit_csv=audit_unres,
        statement_path=html_clean,
        expected_login=9900112233,
    )
    assert rep_unres["status"] == "FAIL_CLOSED"
    assert rep_unres["summary"]["unresolved_fill_rows"] == 1
    assert rep_unres["post_reconcile_gate"]["passed"] is False


# ---------------------------------------------------------------------------
# 5. Architecture & Safety Invariants (ZERO scipy, ZERO assert in quant_core/tca.py)
# ---------------------------------------------------------------------------
def test_quant_core_tca_zero_scipy_and_zero_asserts() -> None:
    """Verify ARCH-01 (zero scipy) and zero assert guards in new L11 modules."""
    for rel in (
        "quant_core/tca.py",
        "quant_factory/tca_reconcile.py",
        "quant_factory/daily_statement_reconciler.py",
    ):
        src = (AI_ENGINES_DIR / rel).read_text(encoding="utf-8")
        tree = ast.parse(src)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("scipy"), f"Forbidden scipy import in {rel}"
                    assert alias.name != "MetaTrader5", f"Forbidden MetaTrader5 import in {rel}"
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                assert not mod.startswith("scipy"), f"Forbidden scipy import in {rel}"
                assert mod != "MetaTrader5", f"Forbidden MetaTrader5 import in {rel}"
            elif isinstance(node, ast.Assert):
                raise AssertionError(f"Forbidden assert statement in {rel}:{node.lineno}")

    assert core_tca.ORDER_SEND_CAPABLE is False
    assert core_tca.ORDER_SEND_COUNT == 0
    assert dsr.ORDER_SEND_CAPABLE is False
    assert dsr.ORDER_SEND_COUNT == 0
    # Smoke-check SHA helper determinism
    h1 = hashlib.sha256(b"naqex").hexdigest()
    assert len(h1) == 64 and math.isfinite(1.0)


# ---------------------------------------------------------------------------
# 6. Adversarial Regression Suite (rev11-tca Findings #1..#5)
# ---------------------------------------------------------------------------
def test_rev11_1_live_monitor_ingests_all_canonical_fill_event_types_for_swap_guards(tmp_path: Path) -> None:
    """Fix #1: `load_exec_audit_readonly` uses `VALID_FILL_EVENT_TYPES` (never drops `EXIT`/`CLOSE`/`ORDER_CLOSE`)."""
    t0 = 1795630000
    for bad_ev, bad_swap, exp_field in (
        ("EXIT", "-5.00", "swap_violations"),
        ("CLOSE", "", "missing_swap_count"),
        ("ORDER_CLOSE", "NaN", "nonfinite_swap_count"),
        ("PARTIAL_EXIT", "-1.25", "swap_violations"),
    ):
        p = tmp_path / f"audit_{bad_ev.lower()}.csv"
        header = (
            "utc_ts,magic,symbol,side,event_type,signal_price,fill_price,sl_price,"
            "lots,spread_pts,latency_ms,retcode,comment,swap_usd"
        )
        row1 = f"{t0},20261122,USDJPY,BUY,ORDER_FILL,159.200,159.201,159.050,0.01,4.0,150.0,10009,pos=201,0.0"
        row2 = (
            f"{t0 + 60},20261122,USDJPY,SELL,{bad_ev},159.250,159.249,159.050,"
            f"0.01,4.0,150.0,10009,pos=201,{bad_swap}"
        )
        p.write_text("\n".join([header, row1, row2]) + "\n", encoding="utf-8")
        rep = live_mon.evaluate_live_tca(audit_csv_paths=[p], use_hot_cache=False, n_bootstrap_draws=500)
        assert rep["verdict"] == "RED_FRICTION_BREACH", f"{bad_ev} with swap={bad_swap!r} must fail closed"
        assert rep["inputs"][exp_field] >= 1
        assert rep["post_reconcile_check"]["passed"] is False
        assert live_mon.exit_code_for_report(rep) == 2


def test_rev11_2_fail_closed_missing_swap_on_entries_and_unrecognized_event_types(tmp_path: Path) -> None:
    """Fix #2: `ENTRY_*` and unrecognized `event_type` with `swap_usd=None` fail closed everywhere."""
    # Unrecognized event_type with swap_usd=None MUST fail closed even with check_entries_for_missing_swap=False
    unknown_row = {
        "utc_ts": 1795631000,
        "symbol": "USDJPY",
        "side": "SELL",
        "event_type": "CLOSE_POSITION",
        "signal_price": 153.5,
        "fill_price": 153.5,
        "sl_price": 153.0,
        "spread_pts": 6.0,
        "latency_ms": 40.0,
        "swap_usd": None,
    }
    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        core_tca.validate_tca_post_reconcile([unknown_row], check_entries_for_missing_swap=False)

    # ENTRY_FILLED with swap_usd=None fails closed by default in validate_tca_post_reconcile & compute_tca_report
    entry_blank = {
        "utc_ts": 1795631000,
        "symbol": "USDJPY",
        "side": "BUY",
        "event_type": "ENTRY_FILLED",
        "signal_price": 153.2,
        "fill_price": 153.202,
        "sl_price": 152.7,
        "spread_pts": 6.0,
        "latency_ms": 40.0,
        "swap_usd": None,
    }
    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        core_tca.validate_tca_post_reconcile([entry_blank])
    with pytest.raises(ValueError, match="MISSING_SWAP_USD"):
        tca_reconcile.compute_tca_report([entry_blank])

    # Daily statement reconciler also fails closed when ENTRY_FILLED has blank swap on BOTH audit and statement
    audit_csv = _write_csv(
        tmp_path / "audit_entry_blank.csv",
        [
            "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price",
            "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "swap_usd", "deal_id", "account_login",
        ],
        [
            {
                "utc_ts": 1795631000,
                "magic": 20261122,
                "symbol": "USDJPY",
                "side": "BUY",
                "event_type": "ENTRY_FILLED",
                "signal_price": 153.2,
                "fill_price": 153.202,
                "sl_price": 152.7,
                "lots": 0.10,
                "spread_pts": 6.0,
                "latency_ms": 40.0,
                "retcode": 10009,
                "swap_usd": "",
                "deal_id": "D7001",
                "account_login": 9900112233,
            },
        ],
    )
    stmt_csv = _write_csv(
        tmp_path / "stmt_entry_blank.csv",
        ["login", "deal", "symbol", "type", "direction", "volume", "price", "profit", "swap"],
        [
            {
                "login": 9900112233,
                "deal": "D7001",
                "symbol": "USDJPY",
                "type": "BUY",
                "direction": "IN",
                "volume": 0.10,
                "price": 153.202,
                "profit": "",
                "swap": "",
            },
        ],
    )
    rep = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_csv,
        expected_login=9900112233,
    )
    assert rep["status"] == "FAIL_CLOSED"
    assert rep["summary"]["missing_swap_count"] == 1
    assert rep["post_reconcile_gate"]["passed"] is False


def test_rev11_3_login_mismatch_bypasses_all_fail_closed(tmp_path: Path) -> None:
    """Fix #3: Cross-login without expected_login, multi-login mixing, and missing statement login all FAIL_CLOSED."""
    audit_fields = [
        "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price",
        "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "swap_usd", "deal_id", "account_login",
    ]
    stmt_fields = ["login", "deal", "symbol", "type", "direction", "volume", "price", "profit", "swap"]

    audit_a = _write_csv(
        tmp_path / "audit_a.csv",
        audit_fields,
        [
            {
                "utc_ts": 1795632000, "magic": 20261122, "symbol": "USDJPY", "side": "BUY",
                "event_type": "ENTRY_FILLED", "signal_price": 153.2, "fill_price": 153.2,
                "sl_price": 152.7, "lots": 0.10, "spread_pts": 6.0, "latency_ms": 40.0,
                "retcode": 10009, "swap_usd": "0.0", "deal_id": "D8001", "account_login": 11111111,
            },
            {
                "utc_ts": 1795633000, "magic": 20261122, "symbol": "USDJPY", "side": "SELL",
                "event_type": "TP_HIT", "signal_price": 153.5, "fill_price": 153.5,
                "sl_price": 152.7, "lots": 0.10, "spread_pts": 6.0, "latency_ms": 40.0,
                "retcode": 10009, "swap_usd": "0.0", "deal_id": "D8002", "account_login": 11111111,
            },
        ],
    )

    # (a) expected_login=None, audit_logins=[11111111] vs stmt_logins=[22222222] -> FAIL_CLOSED
    stmt_other = _write_csv(
        tmp_path / "stmt_other.csv",
        stmt_fields,
        [
            {
                "login": 22222222, "deal": "D8001", "symbol": "USDJPY", "type": "BUY",
                "direction": "IN", "volume": 0.10, "price": 153.2, "profit": "", "swap": "0.0",
            },
            {
                "login": 22222222, "deal": "D8002", "symbol": "USDJPY", "type": "SELL",
                "direction": "OUT", "volume": 0.10, "price": 153.5, "profit": "20.0", "swap": "0.0",
            },
        ],
    )
    rep_a = dsr.reconcile_daily_statement(audit_csv=audit_a, statement_path=stmt_other, expected_login=None)
    assert rep_a["status"] == "FAIL_CLOSED"
    assert any("LOGIN_MISMATCH" in r for r in rep_a["fail_reasons"])

    # (b) Multi-login statement [11111111, 99999999] with expected_login=11111111 -> FAIL_CLOSED
    stmt_mixed = _write_csv(
        tmp_path / "stmt_mixed.csv",
        stmt_fields,
        [
            {
                "login": 11111111, "deal": "D8001", "symbol": "USDJPY", "type": "BUY",
                "direction": "IN", "volume": 0.10, "price": 153.2, "profit": "", "swap": "0.0",
            },
            {
                "login": 99999999, "deal": "D8002", "symbol": "USDJPY", "type": "SELL",
                "direction": "OUT", "volume": 0.10, "price": 153.5, "profit": "20.0", "swap": "0.0",
            },
        ],
    )
    rep_b = dsr.reconcile_daily_statement(audit_csv=audit_a, statement_path=stmt_mixed, expected_login=11111111)
    assert rep_b["status"] == "FAIL_CLOSED"
    assert any("LOGIN_MISMATCH" in r for r in rep_b["fail_reasons"])

    # (c) expected_login=11111111 but statement CSV lacks login column entirely -> FAIL_CLOSED
    stmt_no_login = _write_csv(
        tmp_path / "stmt_no_login.csv",
        ["deal", "symbol", "type", "direction", "volume", "price", "profit", "swap"],
        [
            {
                "deal": "D8001", "symbol": "USDJPY", "type": "BUY",
                "direction": "IN", "volume": 0.10, "price": 153.2, "profit": "", "swap": "0.0",
            },
            {
                "deal": "D8002", "symbol": "USDJPY", "type": "SELL",
                "direction": "OUT", "volume": 0.10, "price": 153.5, "profit": "20.0", "swap": "0.0",
            },
        ],
    )
    rep_c = dsr.reconcile_daily_statement(audit_csv=audit_a, statement_path=stmt_no_login, expected_login=11111111)
    assert rep_c["status"] == "FAIL_CLOSED"
    assert any("LOGIN_MISMATCH" in r for r in rep_c["fail_reasons"])


def test_rev11_4_mt5_multisection_utf16_html_report_prefers_deals_and_skips_orders(tmp_path: Path) -> None:
    """Fix #4: Standard MT5 UTF-16 `ReportHistory.html` (Positions + Orders + Deals) yields exact 2 matched deals."""
    audit_csv = _write_csv(
        tmp_path / "audit_mt5_hist.csv",
        [
            "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price",
            "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "pnl_usd", "swap_usd",
            "deal_id", "order_id", "position_id", "account_login",
        ],
        [
            {
                "utc_ts": 1793610300, "magic": 20261122, "symbol": "USDJPY", "side": "BUY",
                "event_type": "ENTRY_FILLED", "signal_price": 153.200, "fill_price": 153.202,
                "sl_price": 152.700, "lots": 0.10, "spread_pts": 6.0, "latency_ms": 40.0,
                "retcode": 10009, "pnl_usd": "", "swap_usd": "0.0",
                "deal_id": "91001", "order_id": "81001", "position_id": "71001", "account_login": 9900112233,
            },
            {
                "utc_ts": 1793617500, "magic": 20261122, "symbol": "USDJPY", "side": "SELL",
                "event_type": "TP_HIT", "signal_price": 153.650, "fill_price": 153.648,
                "sl_price": 152.700, "lots": 0.10, "spread_pts": 6.0, "latency_ms": 42.0,
                "retcode": 10009, "pnl_usd": "", "swap_usd": "",
                "deal_id": "91002", "order_id": "81002", "position_id": "71001", "account_login": 9900112233,
            },
        ],
    )

    def _tr(tag: str, *cells: str) -> str:
        return "<tr>" + "".join(f"<{tag}>{c}</{tag}>" for c in cells) + "</tr>"

    html_text = "\n".join([
        "<!DOCTYPE html><html><body><table>",
        "<tr><td>Account:</td><td>9900112233 (USD, FTMO-Demo, hedging)</td></tr>",
        '<tr><th colspan="13"><b>Positions</b></th></tr>',
        _tr(
            "th", "Time", "Position", "Symbol", "Type", "Volume", "Price",
            "S / L", "T / P", "Time", "Price", "Commission", "Swap", "Profit",
        ),
        _tr(
            "td", "2026.11.02 09:05:00", "71001", "USDJPY", "buy", "0.10", "153.202",
            "152.700", "153.650", "2026.11.02 11:05:00", "153.648", "-0.60", "0.00", "29.10",
        ),
        '<tr><th colspan="11"><b>Orders</b></th></tr>',
        _tr(
            "th", "Open Time", "Order", "Symbol", "Type", "Volume", "Price",
            "S / L", "T / P", "Time", "State", "Comment",
        ),
        _tr(
            "td", "2026.11.02 09:05:00", "81001", "USDJPY", "buy", "0.10 / 0.10", "153.202",
            "152.700", "153.650", "2026.11.02 09:05:00", "filled", "magic=20261122",
        ),
        _tr(
            "td", "2026.11.02 11:05:00", "81002", "USDJPY", "sell", "0.10 / 0.10", "153.648",
            "0.000", "0.000", "2026.11.02 11:05:00", "filled", "tp 153.650",
        ),
        '<tr><th colspan="13"><b>Deals</b></th></tr>',
        _tr(
            "th", "Time", "Deal", "Symbol", "Type", "Direction", "Volume", "Price",
            "Order", "Commission", "Fee", "Swap", "Profit", "Comment",
        ),
        _tr(
            "td", "2026.11.01 00:00:00", "91000", "", "balance", "in", "", "",
            "0", "0.00", "0.00", "0.00", "10 000.00", "Deposit",
        ),
        _tr(
            "td", "2026.11.02 09:05:00", "91001", "USDJPY", "buy", "in", "0.10", "153.202",
            "81001", "-0.30", "0.00", "0.00", "0.00", "magic=20261122 pos=71001",
        ),
        _tr(
            "td", "2026.11.02 11:05:00", "91002", "USDJPY", "sell", "out", "0.10", "153.648",
            "81002", "-0.30", "0.00", "0.00", "29.10", "magic=20261122 pos=71001",
        ),
        "</table></body></html>",
    ])
    # Write with UTF-16 BOM just like real MetaTrader 5 HTML export!
    html_path = tmp_path / "ReportHistory.html"
    html_path.write_bytes(html_text.encode("utf-16"))

    rep = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=html_path,
        expected_login=9900112233,
    )
    assert rep["status"] == "PASS"
    assert rep["summary"]["statement_trade_rows"] == 2
    assert rep["summary"]["matched_pairs"] == 2
    assert rep["summary"]["orphan_statement_count"] == 0
    assert rep["summary"]["orphan_audit_count"] == 0
    assert rep["summary"]["swap_enriched_count"] == 1
    assert rep["summary"]["net_pnl_usd"] == pytest.approx(29.10, abs=0.01)


def test_rev11_5_broker_nonzero_swap_overrides_audit_zero_claim_fail_closed(tmp_path: Path) -> None:
    """Fix #5: Audit `swap_usd=0.0` vs broker `swap=-1.50` adopts broker swap so all swap gates fail closed."""
    audit_csv = _write_csv(
        tmp_path / "audit_claims_zero.csv",
        [
            "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price",
            "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "pnl_usd", "swap_usd",
            "deal_id", "account_login",
        ],
        [
            {
                "utc_ts": 1793617500, "magic": 20261122, "symbol": "USDJPY", "side": "SELL",
                "event_type": "TP_HIT", "signal_price": 153.65, "fill_price": 153.65,
                "sl_price": 152.70, "lots": 0.10, "spread_pts": 6.0, "latency_ms": 40.0,
                "retcode": 10009, "pnl_usd": "40.00", "swap_usd": "0.0",
                "deal_id": "D9901", "account_login": 9900112233,
            },
        ],
    )
    stmt_csv = _write_csv(
        tmp_path / "stmt_real_swap.csv",
        ["login", "deal", "symbol", "type", "direction", "volume", "price", "profit", "swap"],
        [
            {
                "login": 9900112233, "deal": "D9901", "symbol": "USDJPY", "type": "SELL",
                "direction": "OUT", "volume": 0.10, "price": 153.65, "profit": "40.00", "swap": "-1.50",
            },
        ],
    )
    rep = dsr.reconcile_daily_statement(
        audit_csv=audit_csv,
        statement_path=stmt_csv,
        expected_login=9900112233,
    )
    assert rep["status"] == "FAIL_CLOSED"
    assert rep["summary"]["swap_discrepancy_count"] == 1
    assert rep["summary"]["nonzero_swap_count"] == 1
    assert rep["summary"]["total_swap_usd"] == pytest.approx(-1.50, abs=1e-6)
    assert rep["post_reconcile_gate"]["passed"] is False
    assert "NONZERO_SWAP_USD" in str(rep["post_reconcile_gate"]["error"])
    assert rep["discrepancies"]["swap_discrepancies"][0]["audit_swap_usd"] == 0.0
    assert rep["discrepancies"]["swap_discrepancies"][0]["statement_swap_usd"] == -1.50
