"""Wave-2 Cycle 4H Tests: Prop-Challenge & 14-Day Free-Trial Tracker CLI + FTMO/The5ers Launch SOP.

Covers:
  1. Empty / pre-trade graceful handling (`PRE_TRADE_READY`, `EXTEND_SHADOW`, CLI `--out-md`/`--out-json`).
  2. Exact FTMO 4-trading-day vs The5ers High Stakes 3x`+0.50%` profitable-day gate math (`PASS_TO_PAID` vs `EXTEND_SHADOW`).
  3. Red-News `+-300s` guard / `+-120s` firm window violation detection, nonzero `swap_usd` & overnight hold -> `HALT_AND_FIX`.
  4. Per-engine `1.5x` backtest M1 slippage breach flag & Daily/Total DD Amber/Red/Hard brake transitions.
  5. `knowledge/playbooks/ftmo-the5ers-live-launch-sop.md`: `< 16 KB`, YAML frontmatter, `0` bare `$`,
     `0` broken local links, and clean `brain_cli` vault audit.
"""

from __future__ import annotations

import csv
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))
if str(ROOT / "tooling/knowledge") not in sys.path:
    sys.path.insert(0, str(ROOT / "tooling/knowledge"))

import brain_cli
from quant_factory import prop_challenge_tracker as pct

SOP_PATH = ROOT / "knowledge/playbooks/ftmo-the5ers-live-launch-sop.md"
HEADER = [
    "utc_ts", "magic", "symbol", "side", "event_type", "signal_price", "fill_price",
    "sl_price", "lots", "spread_pts", "latency_ms", "retcode", "pnl_usd", "swap_usd", "comment",
]


def _write_audit(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        for r in rows:
            base = {k: "" for k in HEADER}
            base.update(r)
            w.writerow(base)


def _write_news(path: Path, events: list[tuple[int, str, str]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["utc_ts", "ccy", "event"])
        for ts, ccy, ev in events:
            w.writerow([ts, ccy, ev])


def test_empty_pre_trade_graceful_standby_and_cli(tmp_path: Path) -> None:
    assert pct.ORDER_SEND_COUNT == 0
    out_md = tmp_path / "prop_score.md"
    out_json = tmp_path / "prop_score.json"

    rc = pct.main([
        "--profile", "ftmo_swing_10k",
        "--exec-audit-csv", str(tmp_path / "missing_audit.csv"),
        "--spread-log-jsonl", str(tmp_path / "missing_spreads.jsonl"),
        "--heartbeat-json", str(tmp_path / "missing_hb.json"),
        "--out-md", str(out_md),
        "--out-json", str(out_json),
    ])
    assert rc == 0
    assert out_md.is_file() and out_json.is_file()

    data = json.loads(out_json.read_text(encoding="utf-8"))
    assert data["schema"] == "naqex-prop-challenge-tracker-v1"
    assert data["order_send_count"] == 0
    assert data["status"] == "PRE_TRADE_READY"
    assert data["gate_decision"] == "EXTEND_SHADOW"
    assert data["summary"]["deals_total"] == 0
    assert data["summary"]["news_events_loaded"] > 100  # Loads real workspace Red-News CSV

    md = out_md.read_text(encoding="utf-8")
    assert md.startswith("---\n")
    assert "$" not in md
    assert "EXTEND_SHADOW" in md


def test_ftmo_4_day_and_the5ers_3x_profitable_day_math(tmp_path: Path) -> None:
    news_csv = tmp_path / "news.csv"
    _write_news(news_csv, [(1_795_000_000, "USD", "NFP")])  # Far away from test deals
    audit_csv = tmp_path / "audit.csv"

    # Build 3 clean intraday trading days (10:00 UTC -> 14:00 UTC) with low 0.5 bps slip & 0 swap
    base_ts = 1_795_500_000  # Away from news & away from 21:55-22:15 UTC rollover
    # Align cleanly to 2026-11-24 10:00 UTC (exact)
    d0 = 1_795_428_000  # 2026-11-24 10:00:00 UTC
    rows_3d = []
    for i, pnl in enumerate((30.0, 30.0, 20.0)):
        t_in = d0 + i * 86_400
        t_out = t_in + 3600
        rows_3d.append({"utc_ts": t_in, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "signal_price": 150.000, "fill_price": 150.008, "sl_price": 149.2, "lots": 0.10, "pnl_usd": 0.0, "swap_usd": 0.0})
        rows_3d.append({"utc_ts": t_out, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.300, "fill_price": 150.295, "sl_price": 149.2, "lots": 0.10, "pnl_usd": pnl, "swap_usd": 0.0})
    _write_audit(audit_csv, rows_3d)

    # FTMO 10k: 3 days < 4 required -> EXTEND_SHADOW
    res_ftmo_3 = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_ftmo_3["rules"]["R3_min_days"]["status"] == "IN_PROGRESS"
    assert res_ftmo_3["gate_decision"] == "EXTEND_SHADOW"

    # The5ers 5k (+0.50% = 25 USD): Day 3 earned +20 USD < 25 USD -> only 2/3 profitable days -> EXTEND_SHADOW!
    res_t5_2p = pct.evaluate_prop_challenge(profile_id="the5ers_hs_5k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_t5_2p["rules"]["R3_min_days"]["trading_days"] == 3
    assert res_t5_2p["rules"]["R3_min_days"]["profitable_days"] == 2
    assert res_t5_2p["gate_decision"] == "EXTEND_SHADOW"

    # Bump Day 3 pnl to +26.0 USD (>= 25.0 USD) -> The5ers 5k PASS_TO_PAID!
    rows_3d[-1]["pnl_usd"] = 26.0
    _write_audit(audit_csv, rows_3d)
    res_t5_ok = pct.evaluate_prop_challenge(profile_id="the5ers_hs_5k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_t5_ok["rules"]["R3_min_days"]["profitable_days"] == 3
    assert res_t5_ok["gate_decision"] == "PASS_TO_PAID"

    # Add 4th clean trading day -> FTMO 10k PASS_TO_PAID!
    t4 = d0 + 3 * 86_400
    rows_4d = list(rows_3d) + [
        {"utc_ts": t4, "magic": 20261123, "symbol": "USDJPY", "side": "SELL", "event_type": "ENTRY", "signal_price": 150.000, "fill_price": 149.992, "sl_price": 150.8, "lots": 0.10, "pnl_usd": 0.0, "swap_usd": 0.0},
        {"utc_ts": t4 + 3600, "magic": 20261123, "symbol": "USDJPY", "side": "SELL", "event_type": "EXIT", "signal_price": 149.700, "fill_price": 149.706, "sl_price": 150.8, "lots": 0.10, "pnl_usd": 35.0, "swap_usd": 0.0},
    ]
    _write_audit(audit_csv, rows_4d)
    res_ftmo_4 = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_ftmo_4["rules"]["R3_min_days"]["trading_days"] == 4
    assert res_ftmo_4["gate_decision"] == "PASS_TO_PAID"


def test_red_news_nonzero_swap_and_overnight_halt_and_fix(tmp_path: Path) -> None:
    d0 = 1_795_428_000  # 2026-11-24 10:00:00 UTC
    news_csv = tmp_path / "news.csv"
    _write_news(news_csv, [(d0 + 180, "USD", "US_CPI")])
    audit_csv = tmp_path / "audit.csv"

    # Case 1: Deal 180s before USD CPI -> violates +-300s guard (outside +-120s firm) -> HALT_AND_FIX
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "signal_price": 150.0, "fill_price": 150.005, "pnl_usd": 10.0, "swap_usd": 0.0},
    ])
    res_rn = pct.evaluate_prop_challenge(profile_id="ftmo_std_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_rn["rules"]["R4_zero_swap_and_red_news"]["red_news_guard_violations"] == 1
    assert res_rn["rules"]["R4_zero_swap_and_red_news"]["red_news_firm_violations"] == 0
    assert res_rn["gate_decision"] == "HALT_AND_FIX"

    # Case 2: Deal 60s before USD CPI -> violates BOTH +-300s guard AND +-120s firm window
    _write_audit(audit_csv, [
        {"utc_ts": d0 + 120, "magic": 20261124, "symbol": "US100.cash", "side": "BUY", "event_type": "ENTRY", "signal_price": 20000.0, "fill_price": 20001.0, "pnl_usd": 10.0, "swap_usd": 0.0},
    ])
    res_rn2 = pct.evaluate_prop_challenge(profile_id="ftmo_std_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_rn2["rules"]["R4_zero_swap_and_red_news"]["red_news_firm_violations"] == 1
    assert res_rn2["gate_decision"] == "HALT_AND_FIX"

    # Case 3: Nonzero overnight swap -> HALT_AND_FIX
    _write_news(news_csv, [(1_700_000_000, "USD", "OLD")])
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": 20.0, "swap_usd": -1.45},
    ])
    res_sw = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_sw["rules"]["R4_zero_swap_and_red_news"]["nonzero_swap_count"] == 1
    assert res_sw["gate_decision"] == "HALT_AND_FIX"

    # Case 4: Overnight hold across server midnight (ENTRY Day 0 -> EXIT Day 1) -> HALT_AND_FIX
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": 0.0, "swap_usd": 0.0},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.1, "fill_price": 150.1, "pnl_usd": 20.0, "swap_usd": 0.0},
    ])
    res_ov = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_ov["rules"]["R4_zero_swap_and_red_news"]["overnight_hold_count"] == 1
    assert res_ov["gate_decision"] == "HALT_AND_FIX"


def test_per_engine_1_5x_slippage_breach_and_dd_brake_flags(tmp_path: Path) -> None:
    d0 = 1_795_428_000
    news_csv = tmp_path / "news.csv"
    _write_news(news_csv, [(1_700_000_000, "USD", "OLD")])
    audit_csv = tmp_path / "audit.csv"

    # E1_USDJPY_TOKYO budget = 1.30 bps -> 1.5x limit = 1.95 bps.
    # Fill at 150.060 vs signal 150.000 = +4.00 bps adverse slip -> MUST flag E1 & HALT_AND_FIX!
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "signal_price": 150.000, "fill_price": 150.060, "pnl_usd": 10.0, "swap_usd": 0.0},
    ])
    res_slip = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert "E1_USDJPY_TOKYO" in res_slip["rules"]["R5_engine_slippage_tca"]["flagged_engines"]
    assert res_slip["rules"]["R5_engine_slippage_tca"]["status"] == "FAIL"
    assert res_slip["gate_decision"] == "HALT_AND_FIX"

    # Amber Daily DD (3.8% on 10k = -380 USD) with clean slip -> R1 WARN & EXTEND_SHADOW
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.000, "fill_price": 150.000, "pnl_usd": -380.0, "swap_usd": 0.0},
    ])
    res_amb = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_amb["rules"]["R1_daily_loss"]["status"] == "WARN"
    assert res_amb["gate_decision"] == "EXTEND_SHADOW"

    # Hard Daily DD (5.2% = -520 USD) -> R1 FAIL & HALT_AND_FIX
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.000, "fill_price": 150.000, "pnl_usd": -520.0, "swap_usd": 0.0},
    ])
    res_hard = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_hard["rules"]["R1_daily_loss"]["status"] == "FAIL"
    assert res_hard["gate_decision"] == "HALT_AND_FIX"


def test_propguard_order_fill_dryrun_and_reject_contract(tmp_path: Path) -> None:
    """Verify exact live `Naqex_PropGuard.mqh` event types (`ORDER_FILL`, `DRYRUN_SIGNAL`, `ORDER_REJECT`)."""
    d0 = 1_795_428_000
    news_csv = tmp_path / "news.csv"
    _write_news(news_csv, [(1_700_000_000, "USD", "OLD")])
    audit_csv = tmp_path / "audit.csv"

    # Case 1: Only DRYRUN_SIGNAL & ORDER_REJECT rows -> MUST stay PRE_TRADE_READY (0 live trading days!)
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "DRYRUN_SIGNAL", "signal_price": 150.000, "fill_price": 150.000, "lots": 0.10, "retcode": 0},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_REJECT", "signal_price": 150.000, "fill_price": 150.500, "lots": 0.10, "retcode": 10018},
    ])
    res_pre = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_pre["status"] == "PRE_TRADE_READY"
    assert res_pre["summary"]["deals_total"] == 0
    assert res_pre["summary"]["trading_days"] == 0
    assert res_pre["summary"]["dryrun_signals"] == 1
    assert res_pre["summary"]["rejected_orders"] == 1

    # Case 2: Live BUY ORDER_FILL with +4.00 bps adverse fill (150.060 > 150.000) MUST NOT invert sign -> MUST flag E1 & HALT_AND_FIX!
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 150.060, "lots": 0.10, "retcode": 10009},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "DRYRUN_SIGNAL", "signal_price": 150.000, "fill_price": 150.000, "lots": 0.10, "retcode": 0},
        {"utc_ts": d0 + 2 * 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "SELL", "event_type": "ORDER_REJECT", "signal_price": 150.000, "fill_price": 149.500, "lots": 0.10, "retcode": 10019},
    ])
    res_fill = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_fill["summary"]["deals_total"] == 1
    assert res_fill["summary"]["trading_days"] == 1
    assert res_fill["summary"]["dryrun_signals"] == 1
    assert res_fill["summary"]["rejected_orders"] == 1
    e1_tca = res_fill["rules"]["R5_engine_slippage_tca"]["per_engine"]["E1_USDJPY_TOKYO"]
    assert e1_tca["entries"] == 1
    assert e1_tca["mean_adverse_slip_bps"] > 3.9
    assert e1_tca["breached"] is True
    assert "E1_USDJPY_TOKYO" in res_fill["rules"]["R5_engine_slippage_tca"]["flagged_engines"]
    assert res_fill["gate_decision"] == "HALT_AND_FIX"


def test_launch_sop_playbook_hygiene_links_and_vault_audit() -> None:
    assert SOP_PATH.is_file(), f"Missing {SOP_PATH}"
    raw = SOP_PATH.read_text(encoding="utf-8")
    assert SOP_PATH.stat().st_size < 16 * 1024, "SOP exceeds 16 KB cap"
    assert raw.startswith("---\n") and raw.count("\n---\n") >= 1
    assert "$" not in raw, "Bare '$' detected in Launch SOP — use USD!"

    for required_tok in (
        "1515343166",
        "Naqex_FreeTrial",
        "DUAL_2FIRM_STAGGER_42D",
        "Terms §11",
        "naqex_red_news_utc.csv",
        "orphan_no_sl",
        "PASS_TO_PAID",
        "HALT_AND_FIX",
    ):
        assert required_tok in raw, f"Missing required SOP anchor: {required_tok}"

    link_re = re.compile(r"\[[^\]]+\]\(([^)#]+)(?:#[^)]*)?\)")
    links = link_re.findall(raw)
    assert len(links) >= 8
    for target in links:
        if target.startswith(("http://", "https://", "mailto:", "file://")):
            continue
        resolved = (SOP_PATH.parent / target).resolve()
        assert resolved.exists(), f"Broken relative link '{target}' in {SOP_PATH.name}"

    assert brain_cli.find_broken_knowledge_links(ROOT) == []
    assert brain_cli.find_near_duplicate_topic_headings(ROOT) == []


def test_symbol_aliases_red_news_and_r4_r1_triage_tagging(tmp_path: Path) -> None:
    """Verify NAS100/NDX/USTEC/SPX aliases, R4->R3->R2->R1 triage labels, and The5ers 50K 4%/8% DD."""
    # 1. Symbol alias normalization & currency mapping
    for alias in ("NAS100", "NDX", "USTEC", "US100.cash"):
        assert pct._normalize_symbol(alias) == "US100"
        assert pct._symbol_currencies(alias) == {"USD"}
    for alias in ("SPX", "SPX500", "US500.pro"):
        assert pct._normalize_symbol(alias) == "US500"
        assert pct._symbol_currencies(alias) == {"USD"}
    assert pct._symbol_currencies("DE40.cash") == {"EUR"}
    assert pct._symbol_currencies("UK100") == {"GBP"}
    assert pct._symbol_currencies("BTCUSD") == {"USD"}

    d0 = 1_795_428_000  # 2026-11-24 10:00:00 UTC
    news_csv = tmp_path / "news.csv"
    audit_csv = tmp_path / "audit.csv"
    _write_news(news_csv, [(d0 + 90, "USD", "US_CPI")])

    # 2. NAS100 / NDX / USTEC inside USD red-news window -> R4 alert!
    for sym in ("NAS100", "NDX", "USTEC", "SPX"):
        _write_audit(audit_csv, [
            {"utc_ts": d0, "magic": 20261124, "symbol": sym, "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 20000.0, "fill_price": 20000.5, "pnl_usd": 15.0, "swap_usd": 0.0},
        ])
        res = pct.evaluate_prop_challenge(profile_id="the5ers_hs_5k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
        assert res["rules"]["R4_zero_swap_and_red_news"]["red_news_guard_violations"] == 1
        assert res["rules"]["R4_zero_swap_and_red_news"]["red_news_firm_violations"] == 1
        assert res["rules"]["R4_zero_swap_and_red_news"]["risk_label"] == "R4"
        assert res["risk_attribution"]["active_label"] == "R4"
        assert any(a["risk_label"] == "R4" and a["severity"] == "FAIL" for a in res["alerts"])

    # 3. Slippage breach (> 1.5x M1 budget) with clean news/swap -> R3 alert!
    _write_news(news_csv, [(1_700_000_000, "USD", "OLD")])
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 150.060, "pnl_usd": 30.0, "swap_usd": 0.0},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 150.060, "pnl_usd": 30.0, "swap_usd": 0.0},
        {"utc_ts": d0 + 2 * 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 150.060, "pnl_usd": 30.0, "swap_usd": 0.0},
    ])
    res_slip = pct.evaluate_prop_challenge(profile_id="the5ers_hs_5k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_slip["rules"]["R5_engine_slippage_tca"]["risk_label"] == "R3"
    assert res_slip["risk_attribution"]["active_label"] == "R3"

    # 4. Nonzero swap (without red news) -> R3 alert!
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": 30.0, "swap_usd": -2.0},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": 30.0, "swap_usd": 0.0},
        {"utc_ts": d0 + 2 * 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": 30.0, "swap_usd": 0.0},
    ])
    res_sw = pct.evaluate_prop_challenge(profile_id="the5ers_hs_5k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_sw["rules"]["R4_zero_swap_and_red_news"]["risk_label"] == "R3"
    assert res_sw["risk_attribution"]["active_label"] == "R3"

    # 5. Pure R2 Amber daily DD brake across 4 clean trading days -> active_label == "R2"
    _write_audit(audit_csv, [
        {"utc_ts": d0 + i * 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": pnl, "swap_usd": 0.0}
        for i, pnl in enumerate((-380.0, 50.0, 50.0, 50.0))
    ])
    res_r2 = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_r2["rules"]["R1_daily_loss"]["risk_label"] == "R2"
    assert res_r2["risk_attribution"]["active_label"] == "R2"

    # 6. Pure R1 strategy edge decay (-3.2% spread across 4 losing days < Amber daily limit, clean R4/R3/R2) -> active_label == "R1"
    _write_audit(audit_csv, [
        {"utc_ts": d0 + i * 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": -80.0, "swap_usd": 0.0}
        for i in range(4)
    ])
    res_r1 = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_r1["risk_attribution"]["active_label"] == "R1"
    assert res_r1["risk_attribution"]["layers"]["R1"]["status"] == "ALERT"

    # 7. The5ers 50K strict 4%/8% DD boundary: -4.2% daily loss (-2100 USD) MUST FAIL (R4), while -4.2% on 5K (-210 USD) is WARN (R2)
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.0, "fill_price": 150.0, "pnl_usd": -2100.0, "swap_usd": 0.0},
    ])
    res_50k = pct.evaluate_prop_challenge(profile_id="the5ers_hs_50k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_50k["rules"]["R1_daily_loss"]["status"] == "FAIL"
    assert res_50k["rules"]["R1_daily_loss"]["risk_label"] == "R4"
    assert res_50k["gate_decision"] == "HALT_AND_FIX"

    md_out = pct.render_prop_tracker_md(res_50k)
    assert "R4 -> R3 -> R2 -> R1" in md_out
    assert "$" not in md_out


def test_astra_f13_unresolved_fill_adverse_masking_and_missing_swap_fail_closed(tmp_path: Path) -> None:
    """Astra F13: unresolved fills, missing swap on EXIT, and signed-slippage masking must NOT pass silently."""
    d0 = 1_795_428_000
    news_csv = tmp_path / "news.csv"
    _write_news(news_csv, [(1_700_000_000, "USD", "OLD")])
    audit_csv = tmp_path / "audit.csv"

    # 1. Unresolved fill (fill_price=-1.0 / FILL_UNRESOLVED) blocks PASS_TO_PAID even with 4 clean trading days!
    rows_unres = []
    for i in range(4):
        t_in = d0 + i * 86_400
        rows_unres.append({"utc_ts": t_in, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.0, "fill_price": -1.0 if i == 0 else 150.005, "pnl_usd": 0.0, "swap_usd": 0.0, "comment": "FILL_UNRESOLVED" if i == 0 else ""})
        rows_unres.append({"utc_ts": t_in + 3600, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.2, "fill_price": 150.2, "pnl_usd": 30.0, "swap_usd": 0.0})
    _write_audit(audit_csv, rows_unres)
    res_u = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_u["rules"]["R5_engine_slippage_tca"]["unresolved_fill_count"] == 1
    assert res_u["gate_decision"] == "EXTEND_SHADOW"

    # 2. Signed slippage masking: one -5.0 bps lucky fill CANNOT hide one +5.0 bps adverse fill (budget 1.30 bps)!
    _write_audit(audit_csv, [
        {"utc_ts": d0, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 149.925, "pnl_usd": 0.0, "swap_usd": 0.0},
        {"utc_ts": d0 + 86_400, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ORDER_FILL", "signal_price": 150.000, "fill_price": 150.075, "pnl_usd": 0.0, "swap_usd": 0.0},
    ])
    res_mask = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    e1 = res_mask["rules"]["R5_engine_slippage_tca"]["per_engine"]["E1_USDJPY_TOKYO"]
    assert abs(e1["mean_adverse_slip_bps"]) < 0.05
    assert e1["mean_positive_adverse_slip_bps"] >= 2.4
    assert e1["breached"] is True
    assert res_mask["gate_decision"] == "HALT_AND_FIX"

    # 3. Missing swap_usd on EXIT row blocks PASS_TO_PAID
    rows_msw = []
    for i in range(4):
        t_in = d0 + i * 86_400
        rows_msw.append({"utc_ts": t_in, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "ENTRY", "signal_price": 150.0, "fill_price": 150.005, "pnl_usd": 0.0, "swap_usd": 0.0})
        rows_msw.append({"utc_ts": t_in + 3600, "magic": 20261122, "symbol": "USDJPY", "side": "BUY", "event_type": "EXIT", "signal_price": 150.2, "fill_price": 150.2, "pnl_usd": 30.0, "swap_usd": ""})
    _write_audit(audit_csv, rows_msw)
    res_msw = pct.evaluate_prop_challenge(profile_id="ftmo_swing_10k", exec_audit_csv=audit_csv, news_csv=news_csv, spread_log_jsonl=None, heartbeat_json=None)
    assert res_msw["rules"]["R4_zero_swap_and_red_news"]["missing_swap_count"] == 4
    assert res_msw["gate_decision"] == "EXTEND_SHADOW"

