"""End-to-end tests for FTMO MetriX / MT5 broker statement CSV reconciliation in `prop_challenge_tracker.py`.

Strictly offline & read-only (`ORDER_SEND_COUNT = 0`, zero MT5 launches, zero Holdout access).
Covers:
  1. Clean winning + SL closed trades reconciled against realistic FTMO statement CSV -> PASS_TO_PAID (exit 0).
  2. Non-zero swap surfaced via statement CSV join -> fail-closed HALT_AND_FIX (exit 3).
  3. FILL_UNRESOLVED rows (both alongside valid trades and standalone) & unmatched/wrong-login statement -> fail-closed.
  4. Missing/pre-trade files graceful handling -> PRE_TRADE_READY + EXTEND_SHADOW (exit 2).
"""

from __future__ import annotations

import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import quant_factory.prop_challenge_tracker as pct  # noqa: E402


AUDIT_FIELDS = [
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
    "comment",
]

STATEMENT_FIELDS = [
    "login",
    "deal",
    "order",
    "position",
    "symbol",
    "type",
    "direction",
    "volume",
    "price",
    "profit",
    "swap",
    "commission",
]


def _ts(year: int, month: int, day: int, hour: int, minute: int = 0) -> int:
    return int(datetime(year, month, day, hour, minute, tzinfo=timezone.utc).timestamp())


def _write_csv(path: Path, fieldnames: list[str], rows: list[dict]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow(r)
    return path


def _build_clean_ftmo_book(
    tmp_path: Path,
    *,
    account_login: int = 1515343166,
    statement_login: int | None = None,
    swap_override_exit_idx: tuple[int, float] | None = None,
    drop_last_statement_row: bool = False,
    append_unresolved_row: bool = False,
) -> dict[str, Path]:
    """Generate 10 realistic intraday round-trips (wins + SL losses) across 5 trading days & 4 engines."""
    stmt_login = account_login if statement_login is None else statement_login
    # Quiet midday UTC timestamps in Nov 2026 far from any US/UK/EU/JP red-news release
    trade_specs = [
        # (day, hour, magic, engine, symbol, pos_side, sig_in, fill_in, sl, sig_out, fill_out, exit_type, pnl_usd)
        (2, 9, 20261122, "E1_USDJPY_TOKYO", "USDJPY", "BUY", 153.200, 153.210, 152.700, 153.650, 153.642, "TP_HIT", 68.50),
        (2, 14, 20261125, "E3_GBPUSD_VH", "GBPUSD", "SELL", 1.29500, 1.29492, 1.29950, 1.29880, 1.29888, "SL_HIT", -42.00),
        (3, 9, 20261128, "E6_EURJPY_VOLCOMP", "EURJPY", "BUY", 165.400, 165.412, 164.900, 165.920, 165.910, "TIME_EXIT", 54.20),
        (3, 15, 20261124, "E4_US100_SESS40", "US100.cash", "BUY", 20450.0, 20451.8, 20370.0, 20545.0, 20543.5, "TP_HIT", 81.00),
        (4, 10, 20261122, "E1_USDJPY_TOKYO", "USDJPY", "SELL", 153.800, 153.790, 154.250, 153.400, 153.408, "TIME_EXIT", 49.00),
        (4, 15, 20261124, "E4_US100_SESS40", "US100.cash", "SELL", 20510.0, 20508.2, 20595.0, 20588.0, 20590.0, "SL_HIT", -51.50),
        (5, 10, 20261125, "E3_GBPUSD_VH", "GBPUSD", "BUY", 1.29100, 1.29109, 1.28700, 1.29520, 1.29512, "TP_HIT", 63.40),
        (5, 14, 20261128, "E6_EURJPY_VOLCOMP", "EURJPY", "SELL", 165.100, 165.088, 165.600, 165.540, 165.552, "SL_HIT", -38.80),
        (6, 9, 20261122, "E1_USDJPY_TOKYO", "USDJPY", "BUY", 154.000, 154.010, 153.500, 154.480, 154.472, "TIME_EXIT", 58.10),
        (6, 15, 20261124, "E4_US100_SESS40", "US100.cash", "BUY", 20600.0, 20601.5, 20520.0, 20695.0, 20693.8, "TP_HIT", 76.20),
    ]

    audit_rows: list[dict] = []
    stmt_rows: list[dict] = []
    for idx, (day, hr, magic, eng, sym, pos_side, sig_in, fill_in, sl, sig_out, fill_out, exit_type, pnl_usd) in enumerate(trade_specs, start=1):
        pos_id = f"P{1000 + idx}"
        deal_in = f"D{2000 + 2 * idx - 1}"
        deal_out = f"D{2000 + 2 * idx}"
        ord_in = f"O{3000 + 2 * idx - 1}"
        ord_out = f"O{3000 + 2 * idx}"
        exit_side = "SELL" if pos_side == "BUY" else "BUY"
        ts_in = _ts(2026, 11, day, hr, 5)
        ts_out = _ts(2026, 11, day, hr + 2, 10)

        # Entry row in exec_audit + broker statement
        audit_rows.append({
            "utc_ts": ts_in,
            "magic": magic,
            "engine_id": eng,
            "symbol": sym,
            "side": pos_side,
            "position_side": pos_side,
            "event_type": "ENTRY_FILLED",
            "signal_price": sig_in,
            "fill_price": fill_in,
            "sl_price": sl,
            "lots": 0.10,
            "spread_pts": 8.0,
            "latency_ms": 42.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "0.0",
            "commission_usd": "-0.30",
            "account_login": account_login,
            "deal_id": deal_in,
            "order_id": ord_in,
            "position_id": pos_id,
            "comment": f"deal={deal_in} pos={pos_id}",
        })
        stmt_rows.append({
            "login": stmt_login,
            "deal": deal_in,
            "order": ord_in,
            "position": pos_id,
            "symbol": sym,
            "type": pos_side,
            "direction": "IN",
            "volume": 0.10,
            "price": fill_in,
            "profit": "",
            "swap": 0.0,
            "commission": -0.30,
        })

        # Exit row: intentionally omit pnl_usd & swap_usd on even exits to prove statement join enrichment!
        omit_on_audit = (idx % 2 == 0)
        stmt_swap = 0.0
        if swap_override_exit_idx is not None and idx == swap_override_exit_idx[0]:
            stmt_swap = swap_override_exit_idx[1]
            omit_on_audit = True  # Force swap detection strictly through broker statement CSV join!

        audit_rows.append({
            "utc_ts": ts_out,
            "magic": magic,
            "engine_id": eng,
            "symbol": sym,
            "side": exit_side,
            "position_side": pos_side,
            "event_type": exit_type,
            "signal_price": sig_out,
            "fill_price": fill_out,
            "sl_price": sl,
            "lots": 0.10,
            "spread_pts": 9.0,
            "latency_ms": 48.0,
            "retcode": 10009,
            "pnl_usd": "" if omit_on_audit else f"{pnl_usd:.2f}",
            "swap_usd": "" if omit_on_audit else "0.0",
            "commission_usd": "-0.30",
            "account_login": account_login,
            "deal_id": deal_out,
            "order_id": ord_out,
            "position_id": pos_id,
            "comment": f"deal={deal_out} pos={pos_id}",
        })
        stmt_rows.append({
            "login": stmt_login,
            "deal": deal_out,
            "order": ord_out,
            "position": pos_id,
            "symbol": sym,
            "type": exit_side,
            "direction": "OUT",
            "volume": 0.10,
            "price": fill_out,
            "profit": f"{pnl_usd:.2f}",
            "swap": f"{stmt_swap:.2f}",
            "commission": -0.30,
        })

    if drop_last_statement_row:
        stmt_rows.pop()

    if append_unresolved_row:
        audit_rows.append({
            "utc_ts": _ts(2026, 11, 6, 17, 30),
            "magic": 20261122,
            "engine_id": "E1_USDJPY_TOKYO",
            "symbol": "USDJPY",
            "side": "BUY",
            "position_side": "BUY",
            "event_type": "FILL_UNRESOLVED",
            "signal_price": 154.500,
            "fill_price": 0.0,
            "sl_price": 154.000,
            "lots": 0.10,
            "spread_pts": 10.0,
            "latency_ms": 120.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": "",
            "account_login": account_login,
            "deal_id": "",
            "order_id": "O9999",
            "position_id": "",
            "comment": "FILL_UNRESOLVED_DEAL_PRICE_MISSING",
        })

    audit_csv = _write_csv(tmp_path / "naqex_exec_audit.csv", AUDIT_FIELDS, audit_rows)
    stmt_csv = _write_csv(tmp_path / "ftmo_statement.csv", STATEMENT_FIELDS, stmt_rows)
    news_csv = _write_csv(
        tmp_path / "naqex_red_news_utc.csv",
        ["utc_ts", "ccy", "event"],
        [{"utc_ts": _ts(2026, 11, 6, 13, 30), "ccy": "USD", "event": "US_NFP"}],
    )
    hb_json = tmp_path / "naqex_heartbeat.json"
    hb_json.write_text(
        json.dumps({
            "utc_ts": _ts(2026, 11, 6, 18, 0),
            "account_login": account_login,
            "terminal_connected": True,
            "positions_state": "CONFIRMED",
            "open_positions": 0,
            "orphan_no_sl": 0,
            "kill_switch": False,
            "balance": 10318.10,
            "equity": 10318.10,
            "daily_dd_pct": 0.42,
            "static_dd_pct": 0.52,
        }),
        encoding="utf-8",
    )
    spread_jsonl = tmp_path / "mt5_live_spread_log.jsonl"
    spread_jsonl.write_text(
        json.dumps({"utc_ts": _ts(2026, 11, 6, 12, 0), "symbol": "USDJPY", "bid": 154.10, "ask": 154.11, "spread_pts": 10}) + "\n",
        encoding="utf-8",
    )
    return {
        "audit_csv": audit_csv,
        "stmt_csv": stmt_csv,
        "news_csv": news_csv,
        "hb_json": hb_json,
        "spread_jsonl": spread_jsonl,
    }


def test_e2e_clean_winning_and_sl_statement_reconcile_passes_strict_exit(tmp_path: Path):
    paths = _build_clean_ftmo_book(tmp_path)
    out_json = tmp_path / "out/tracker.json"
    out_md = tmp_path / "out/tracker.md"

    rc = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(paths["audit_csv"]),
        "--spread-log-jsonl", str(paths["spread_jsonl"]),
        "--news-csv", str(paths["news_csv"]),
        "--heartbeat-json", str(paths["hb_json"]),
        "--statement-csv", str(paths["stmt_csv"]),
        "--expected-login", "1515343166",
        "--strict-exit",
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])
    assert rc == 0
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["order_send_count"] == 0
    assert payload["gate_decision"] == "PASS_TO_PAID"
    assert payload["status"] == "COMPLIANT_READY_TO_PROMOTE"
    assert payload["risk_attribution"]["active_label"] == "OK"
    assert payload["summary"]["deals_total"] == 20
    assert payload["summary"]["closed_deals"] == 10
    assert payload["summary"]["reconciled_closed_trades"] == 10
    assert payload["summary"]["statement_matched_deals"] == 20
    assert payload["summary"]["statement_unmatched_deals"] == 0
    assert payload["summary"]["trading_days"] == 5
    # Verify statement-enriched PnL sums exact wins + SL losses (+318.10 USD)
    assert abs(payload["summary"]["net_pnl_usd"] - 318.10) < 0.01
    for rk in (
        "R1_daily_loss",
        "R2_max_total_loss",
        "R3_min_days",
        "R4_zero_swap_and_red_news",
        "R5_engine_slippage_tca",
        "R6_reconciliation_and_coverage",
    ):
        assert payload["rules"][rk]["status"] == "PASS", f"{rk} failed: {payload['rules'][rk]}"
    assert payload["rules"]["R6_reconciliation_and_coverage"]["statement_reconciled"] is True
    md_text = out_md.read_text(encoding="utf-8")
    assert "PASS_TO_PAID" in md_text
    assert "$" not in md_text


def test_e2e_nonzero_swap_from_statement_triggers_halt_and_fix_exit_3(tmp_path: Path):
    paths = _build_clean_ftmo_book(tmp_path, swap_override_exit_idx=(4, -3.45))
    out_json = tmp_path / "out/swap_halt.json"

    rc = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(paths["audit_csv"]),
        "--spread-log-jsonl", str(paths["spread_jsonl"]),
        "--news-csv", str(paths["news_csv"]),
        "--heartbeat-json", str(paths["hb_json"]),
        "--statement-csv", str(paths["stmt_csv"]),
        "--expected-login", "1515343166",
        "--strict-exit",
        "--out-json", str(out_json),
    ])
    assert rc == 3
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["gate_decision"] == "HALT_AND_FIX"
    assert payload["status"] == "COMPLIANCE_VIOLATION"
    assert payload["rules"]["R4_zero_swap_and_red_news"]["status"] == "FAIL"
    assert payload["rules"]["R4_zero_swap_and_red_news"]["nonzero_swap_count"] == 1
    assert payload["risk_attribution"]["active_label"] == "R3"


def test_e2e_fill_unresolved_and_statement_mismatch_fail_closed(tmp_path: Path):
    # Case A: FILL_UNRESOLVED row appended alongside 10 clean closed trades -> blocks PASS_TO_PAID (exit 2)
    paths_a = _build_clean_ftmo_book(tmp_path / "case_a", append_unresolved_row=True)
    out_a = tmp_path / "case_a/out.json"
    rc_a = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(paths_a["audit_csv"]),
        "--spread-log-jsonl", str(paths_a["spread_jsonl"]),
        "--news-csv", str(paths_a["news_csv"]),
        "--heartbeat-json", str(paths_a["hb_json"]),
        "--statement-csv", str(paths_a["stmt_csv"]),
        "--expected-login", "1515343166",
        "--strict-exit",
        "--out-json", str(out_a),
    ])
    assert rc_a == 2
    pay_a = json.loads(out_a.read_text(encoding="utf-8"))
    assert pay_a["gate_decision"] == "EXTEND_SHADOW"
    assert pay_a["rules"]["R5_engine_slippage_tca"]["status"] == "WARN"
    assert pay_a["rules"]["R5_engine_slippage_tca"]["unresolved_fill_count"] == 1

    # Case B: Standalone FILL_UNRESOLVED with zero executed deals must NOT silently become PRE_TRADE_READY
    only_unres = _write_csv(
        tmp_path / "case_b/audit.csv",
        AUDIT_FIELDS,
        [{
            "utc_ts": _ts(2026, 11, 6, 10, 0),
            "magic": 20261122,
            "engine_id": "E1_USDJPY_TOKYO",
            "symbol": "USDJPY",
            "side": "BUY",
            "position_side": "BUY",
            "event_type": "FILL_UNRESOLVED",
            "signal_price": 154.0,
            "fill_price": 0.0,
            "sl_price": 153.5,
            "lots": 0.10,
            "spread_pts": 8.0,
            "latency_ms": 50.0,
            "retcode": 10009,
            "pnl_usd": "",
            "swap_usd": "",
            "commission_usd": "",
            "account_login": 1515343166,
            "deal_id": "",
            "order_id": "O5001",
            "position_id": "",
            "comment": "FILL_UNRESOLVED",
        }],
    )
    pay_b = pct.evaluate_prop_challenge(
        profile_id="ftmo_std_10k",
        exec_audit_csv=only_unres,
        spread_log_jsonl=paths_a["spread_jsonl"],
        news_csv=paths_a["news_csv"],
        heartbeat_json=paths_a["hb_json"],
        statement_csv=paths_a["stmt_csv"],
    )
    assert pay_b["status"] != "PRE_TRADE_READY"
    assert pay_b["gate_decision"] == "EXTEND_SHADOW"
    assert pay_b["rules"]["R5_engine_slippage_tca"]["unresolved_fill_count"] == 1

    # Case C: Missing deal in broker statement -> R6 WARN -> EXTEND_SHADOW (exit 2)
    paths_c = _build_clean_ftmo_book(tmp_path / "case_c", drop_last_statement_row=True)
    rc_c = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(paths_c["audit_csv"]),
        "--spread-log-jsonl", str(paths_c["spread_jsonl"]),
        "--news-csv", str(paths_c["news_csv"]),
        "--heartbeat-json", str(paths_c["hb_json"]),
        "--statement-csv", str(paths_c["stmt_csv"]),
        "--strict-exit",
    ])
    assert rc_c == 2

    # Case D: Broker statement login != expected login -> R6 hard FAIL -> HALT_AND_FIX (exit 3)
    paths_d = _build_clean_ftmo_book(tmp_path / "case_d", statement_login=1515343318)
    rc_d = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(paths_d["audit_csv"]),
        "--spread-log-jsonl", str(paths_d["spread_jsonl"]),
        "--news-csv", str(paths_d["news_csv"]),
        "--heartbeat-json", str(paths_d["hb_json"]),
        "--statement-csv", str(paths_d["stmt_csv"]),
        "--expected-login", "1515343166",
        "--strict-exit",
    ])
    assert rc_d == 3


def test_e2e_missing_and_pretrade_files_handled_gracefully(tmp_path: Path):
    hb_json = tmp_path / "naqex_heartbeat.json"
    hb_json.write_text(
        json.dumps({
            "utc_ts": _ts(2026, 11, 25, 9, 45),
            "account_login": 1515343166,
            "terminal_connected": True,
            "positions_state": "CONFIRMED",
            "open_positions": 0,
            "orphan_no_sl": 0,
            "kill_switch": False,
            "balance": 9998.88,
            "equity": 9998.88,
            "daily_dd_pct": 0.0,
            "static_dd_pct": 0.011,
        }),
        encoding="utf-8",
    )
    out_json = tmp_path / "pretrade.json"
    out_md = tmp_path / "pretrade.md"
    rc = pct.main([
        "--profile", "ftmo_std_10k",
        "--exec-audit-csv", str(tmp_path / "missing_audit.csv"),
        "--spread-log-jsonl", str(tmp_path / "missing_spread.jsonl"),
        "--news-csv", str(pct.DEFAULT_NEWS_CSV),
        "--heartbeat-json", str(hb_json),
        "--statement-csv", str(tmp_path / "missing_statement.csv"),
        "--strict-exit",
        "--out-json", str(out_json),
        "--out-md", str(out_md),
    ])
    assert rc == 2
    payload = json.loads(out_json.read_text(encoding="utf-8"))
    assert payload["order_send_count"] == 0
    assert payload["status"] == "PRE_TRADE_READY"
    assert payload["gate_decision"] == "EXTEND_SHADOW"
    assert payload["summary"]["deals_total"] == 0
    assert payload["summary"]["statement_rows_loaded"] == 0
    assert payload["summary"]["news_events_loaded"] >= 400
    assert "$" not in out_md.read_text(encoding="utf-8")
