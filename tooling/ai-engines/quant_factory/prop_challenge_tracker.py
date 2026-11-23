"""Naqex Quant Pod — Live Prop-Challenge & 14-Day Free-Trial Pass/Kill Compliance Tracker CLI.

Pure stdlib, deterministic, fail-closed (`ORDER_SEND_COUNT = 0`, zero API keys, zero network calls).
Evaluates broker-aligned compliance & realized TCA across 5 hard rules for:
  - `ftmo_swing_10k`  (10k USD, >= 4 trading days, 5% daily / 10% max DD, swap=0, +-300s Naqex news guard)
  - `ftmo_std_10k`    (10k USD, >= 4 trading days, 5% daily / 10% max DD, swap=0, +-120s firm / +-300s guard)
  - `the5ers_hs_5k`   (5k USD,  >= 3 profitable days >= +0.50%, 5% daily / 10% max DD, swap=0, +-120s firm / +-300s guard)
  - `the5ers_hs_20k`  (20k USD, >= 3 profitable days >= +0.50%, 5% daily / 10% max DD, swap=0, +-120s firm / +-300s guard)

Emits an unambiguous fail-closed Gate Decision (`PASS_TO_PAID` / `EXTEND_SHADOW` / `HALT_AND_FIX`),
handles empty/pre-trade Free-Trial files cleanly (`status: "PRE_TRADE_READY"`, `EXTEND_SHADOW`), and
writes both a structured JSON receipt and a concise Vietnamese Markdown scoreboard (zero bare `$`).
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import json
from pathlib import Path
from typing import Any

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]

ORDER_SEND_COUNT = 0
DEFAULT_NEWS_CSV = ROOT / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"
DEFAULT_EXEC_AUDIT_CSV = ROOT / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_exec_audit.csv"
DEFAULT_HEARTBEAT_JSON = ROOT / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_heartbeat.json"
DEFAULT_SPREAD_LOG_JSONL = ROOT / ".runtime/live-overnight/mt5_live_spread_log.jsonl"


@dataclass(frozen=True)
class PropProfileSpec:
    profile_id: str
    firm_name: str
    initial_balance_usd: float
    profit_target_pct: float
    hard_daily_loss_pct: float
    amber_daily_brake_pct: float
    hard_max_loss_pct: float
    red_total_brake_pct: float
    min_trading_days: int
    min_profitable_days: int
    profitable_day_threshold_pct: float
    red_news_firm_sec: int
    red_news_guard_sec: int
    server_utc_offset_h: int = 2


PROP_PROFILES: dict[str, PropProfileSpec] = {
    "ftmo_swing_10k": PropProfileSpec(
        profile_id="ftmo_swing_10k",
        firm_name="FTMO Swing 10K",
        initial_balance_usd=10_000.0,
        profit_target_pct=10.0,
        hard_daily_loss_pct=5.0,
        amber_daily_brake_pct=3.5,
        hard_max_loss_pct=10.0,
        red_total_brake_pct=7.0,
        min_trading_days=4,
        min_profitable_days=0,
        profitable_day_threshold_pct=0.0,
        red_news_firm_sec=0,
        red_news_guard_sec=300,
    ),
    "ftmo_std_10k": PropProfileSpec(
        profile_id="ftmo_std_10k",
        firm_name="FTMO Standard 10K",
        initial_balance_usd=10_000.0,
        profit_target_pct=10.0,
        hard_daily_loss_pct=5.0,
        amber_daily_brake_pct=3.5,
        hard_max_loss_pct=10.0,
        red_total_brake_pct=7.0,
        min_trading_days=4,
        min_profitable_days=0,
        profitable_day_threshold_pct=0.0,
        red_news_firm_sec=120,
        red_news_guard_sec=300,
    ),
    "the5ers_hs_5k": PropProfileSpec(
        profile_id="the5ers_hs_5k",
        firm_name="The5ers High Stakes 5K",
        initial_balance_usd=5_000.0,
        profit_target_pct=8.0,
        hard_daily_loss_pct=5.0,
        amber_daily_brake_pct=3.5,
        hard_max_loss_pct=10.0,
        red_total_brake_pct=7.0,
        min_trading_days=3,
        min_profitable_days=3,
        profitable_day_threshold_pct=0.50,
        red_news_firm_sec=120,
        red_news_guard_sec=300,
    ),
    "the5ers_hs_20k": PropProfileSpec(
        profile_id="the5ers_hs_20k",
        firm_name="The5ers High Stakes 20K",
        initial_balance_usd=20_000.0,
        profit_target_pct=8.0,
        hard_daily_loss_pct=5.0,
        amber_daily_brake_pct=3.5,
        hard_max_loss_pct=10.0,
        red_total_brake_pct=7.0,
        min_trading_days=3,
        min_profitable_days=3,
        profitable_day_threshold_pct=0.50,
        red_news_firm_sec=120,
        red_news_guard_sec=300,
    ),
}

# Verified MQL5 export magic numbers (`tooling/ai-engines/exports/Naqex_WB_*.mq5`)
MAGIC_TO_ENGINE: dict[int, str] = {
    20261122: "E1_USDJPY_TOKYO",
    20261123: "E2_USDJPY_EXP80",
    20261124: "E4_US100_SESS40",
    20261125: "E3_GBPUSD_VH",
    20261126: "E5_US100_RS1130",
    20261127: "S6_FX_USD_BSK",
    20261128: "E6_EURJPY_VOLCOMP",
    20261129: "E7_USDJPY_NY10ET",
    20261130: "S7_XAU_EXP120",
}

# Empirical M1 backtest one-way spread/slippage budgets (bps, synced with Lab #3A & Red-Team audit)
ENGINE_BACKTEST_SLIP_BUDGET_BPS: dict[str, float] = {
    "E1_USDJPY_TOKYO": 1.30,
    "E2_USDJPY_EXP80": 1.30,
    "E3_GBPUSD_VH": 1.50,
    "E4_US100_SESS40": 2.25,
    "E5_US100_RS1130": 2.25,
    "E6_EURJPY_VOLCOMP": 1.50,
    "E7_USDJPY_NY10ET": 1.30,
    "S6_FX_USD_BSK": 1.50,
    "S7_XAU_EXP120": 2.05,
}
DEFAULT_ENGINE_BUDGET_BPS = 1.60
SLIPPAGE_BREACH_MULT = 1.50
ENTRY_EVENT_TYPES: frozenset[str] = frozenset({"ENTRY", "ORDER_FILL"})
EXIT_EVENT_TYPES: frozenset[str] = frozenset({"EXIT", "ORDER_CLOSE", "CLOSE"})
NON_FILL_EVENT_TYPES: frozenset[str] = frozenset({"DRYRUN_SIGNAL", "ORDER_REJECT"})


def _to_float(val: Any, default: float = 0.0) -> float:
    try:
        if val is None or val == "":
            return default
        return float(val)
    except (ValueError, TypeError):
        return default


def _to_int(val: Any, default: int = 0) -> int:
    try:
        if val is None or val == "":
            return default
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _server_day(utc_ts: int, offset_h: int = 2) -> str:
    return datetime.fromtimestamp(utc_ts + offset_h * 3600, timezone.utc).strftime("%Y-%m-%d")


def _in_rollover_blackout(utc_ts: int) -> bool:
    """True when UTC timestamp sits inside the 21:55..22:15 UTC broker rollover spread-widening window."""
    dt = datetime.fromtimestamp(utc_ts, timezone.utc)
    mins = dt.hour * 60 + dt.minute
    return (21 * 60 + 55) <= mins <= (22 * 60 + 15)


def _symbol_currencies(symbol: str) -> set[str]:
    s = (symbol or "").upper().replace(".CASH", "").replace(".PRO", "")
    if any(k in s for k in ("US100", "US500", "US30", "NAS", "SPX")):
        return {"USD"}
    if any(k in s for k in ("GER40", "DE40", "DAX")):
        return {"EUR"}
    if "XAU" in s or "GOLD" in s:
        return {"USD"}
    ccys: set[str] = set()
    for c in ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"):
        if c in s:
            ccys.add(c)
    return ccys or {"USD"}


def load_red_news_events(news_csv: Path | None) -> list[dict[str, Any]]:
    if news_csv is None or not news_csv.is_file():
        return []
    events: list[dict[str, Any]] = []
    with news_csv.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            ts = _to_int(r.get("utc_ts"), 0)
            if ts > 0:
                events.append({
                    "utc_ts": ts,
                    "ccy": str(r.get("ccy") or "USD").strip().upper(),
                    "event": str(r.get("event") or "MACRO").strip(),
                })
    events.sort(key=lambda x: x["utc_ts"])
    return events


def load_exec_audit_rows(audit_csv: Path | None) -> list[dict[str, Any]]:
    if audit_csv is None or not audit_csv.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with audit_csv.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            ts = _to_int(r.get("utc_ts"), 0)
            if ts <= 0:
                continue
            magic = _to_int(r.get("magic"), 0)
            eng = str(r.get("engine_id") or "").strip() or MAGIC_TO_ENGINE.get(magic, f"MAGIC_{magic}")
            rows.append({
                "utc_ts": ts,
                "magic": magic,
                "engine_id": eng,
                "symbol": str(r.get("symbol") or "").strip(),
                "side": str(r.get("side") or "").strip().upper(),
                "event_type": str(r.get("event_type") or "ENTRY").strip().upper(),
                "signal_price": _to_float(r.get("signal_price"), 0.0),
                "fill_price": _to_float(r.get("fill_price"), 0.0),
                "sl_price": _to_float(r.get("sl_price"), 0.0),
                "lots": _to_float(r.get("lots"), 0.0),
                "spread_pts": _to_float(r.get("spread_pts"), 0.0),
                "latency_ms": _to_float(r.get("latency_ms"), 0.0),
                "retcode": _to_int(r.get("retcode"), 0),
                "pnl_usd": _to_float(r.get("pnl_usd"), 0.0) if "pnl_usd" in r and r.get("pnl_usd") != "" else None,
                "swap_usd": _to_float(r.get("swap_usd"), 0.0) if "swap_usd" in r and r.get("swap_usd") != "" else 0.0,
                "comment": str(r.get("comment") or "").strip(),
            })
    rows.sort(key=lambda x: x["utc_ts"])
    return rows


def load_spread_log_rows(spread_jsonl: Path | None) -> list[dict[str, Any]]:
    if spread_jsonl is None or not spread_jsonl.is_file():
        return []
    rows: list[dict[str, Any]] = []
    for raw in spread_jsonl.read_text(encoding="utf-8", errors="replace").splitlines():
        s = raw.strip()
        if not s:
            continue
        try:
            obj = json.loads(s)
            if isinstance(obj, dict):
                rows.append(obj)
        except json.JSONDecodeError:
            continue
    return rows


def load_heartbeat_json(hb_path: Path | None) -> dict[str, Any] | None:
    if hb_path is None or not hb_path.is_file():
        return None
    try:
        obj = json.loads(hb_path.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else None
    except Exception:
        return None


def evaluate_prop_challenge(
    *,
    profile_id: str = "ftmo_swing_10k",
    exec_audit_csv: Path | None = DEFAULT_EXEC_AUDIT_CSV,
    spread_log_jsonl: Path | None = DEFAULT_SPREAD_LOG_JSONL,
    news_csv: Path | None = DEFAULT_NEWS_CSV,
    heartbeat_json: Path | None = DEFAULT_HEARTBEAT_JSON,
    now_utc: datetime | None = None,
) -> dict[str, Any]:
    """Evaluate all 5 broker-aligned compliance & TCA rules and return a fail-closed Gate Decision."""
    if profile_id not in PROP_PROFILES:
        raise ValueError(f"Unknown profile '{profile_id}'. Expected one of {sorted(PROP_PROFILES.keys())}")
    spec = PROP_PROFILES[profile_id]
    ts_now = now_utc or datetime.now(timezone.utc)

    all_rows = load_exec_audit_rows(exec_audit_csv)
    dryrun_signals = sum(1 for r in all_rows if r["event_type"] == "DRYRUN_SIGNAL")
    rejected_orders = sum(1 for r in all_rows if r["event_type"] == "ORDER_REJECT")
    deals = [r for r in all_rows if r["event_type"] not in NON_FILL_EVENT_TYPES]
    spreads = load_spread_log_rows(spread_log_jsonl)
    news_events = load_red_news_events(news_csv)
    hb = load_heartbeat_json(heartbeat_json)

    init_bal = spec.initial_balance_usd

    # Detect pre-trade empty state gracefully (zero live executed deals AND no PnL movement)
    orphan_no_sl = int((hb or {}).get("orphan_no_sl", 0)) if isinstance(hb, dict) else 0
    kill_switch = bool((hb or {}).get("kill_switch", False)) if isinstance(hb, dict) else False

    if not deals and orphan_no_sl == 0 and not kill_switch:
        hb_daily_dd = float((hb or {}).get("daily_dd_pct", 0.0)) if isinstance(hb, dict) else 0.0
        hb_static_dd = float((hb or {}).get("static_dd_pct", 0.0)) if isinstance(hb, dict) else 0.0
        return {
            "schema": "naqex-prop-challenge-tracker-v1",
            "generated_utc": ts_now.isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "profile": asdict(spec),
            "status": "PRE_TRADE_READY",
            "gate_decision": "EXTEND_SHADOW",
            "gate_reasons": ["Zero executed deals recorded yet (pre-trade standby); keep Free Trial / Shadow running."],
            "summary": {
                "deals_total": 0,
                "dryrun_signals": dryrun_signals,
                "rejected_orders": rejected_orders,
                "trading_days": 0,
                "profitable_days": 0,
                "net_pnl_usd": 0.0,
                "net_pnl_pct": 0.0,
                "worst_daily_dd_pct": round(hb_daily_dd, 3),
                "max_total_dd_pct": round(hb_static_dd, 3),
                "orphan_no_sl": orphan_no_sl,
                "kill_switch": kill_switch,
                "spread_log_rows": len(spreads),
                "news_events_loaded": len(news_events),
            },
            "rules": {
                "R1_daily_loss": {"status": "PASS", "worst_daily_dd_pct": round(hb_daily_dd, 3), "amber_buffer_pct": round(spec.amber_daily_brake_pct - hb_daily_dd, 3), "hard_buffer_pct": round(spec.hard_daily_loss_pct - hb_daily_dd, 3)},
                "R2_max_total_loss": {"status": "PASS", "max_total_dd_pct": round(hb_static_dd, 3), "red_buffer_pct": round(spec.red_total_brake_pct - hb_static_dd, 3), "hard_buffer_pct": round(spec.hard_max_loss_pct - hb_static_dd, 3)},
                "R3_min_days": {"status": "IN_PROGRESS", "trading_days": 0, "required_trading_days": spec.min_trading_days, "profitable_days": 0, "required_profitable_days": spec.min_profitable_days, "profitable_day_threshold_usd": round(init_bal * spec.profitable_day_threshold_pct / 100.0, 2)},
                "R4_zero_swap_and_red_news": {"status": "PASS", "nonzero_swap_count": 0, "overnight_hold_count": 0, "rollover_blackout_count": 0, "red_news_guard_violations": 0, "red_news_firm_violations": 0, "violations": []},
                "R5_engine_slippage_tca": {"status": "PASS", "flagged_engines": [], "per_engine": {}},
            },
        }

    # --- Aggregate daily PnL, watermark DD, trading days & profitable days ---
    daily_pnl_usd: dict[str, float] = {}
    trading_days_set: set[str] = set()
    equity_curve = [init_bal]
    running_eq = init_bal

    nonzero_swap_count = 0
    overnight_hold_count = 0
    rollover_blackout_count = 0
    news_guard_violations: list[dict[str, Any]] = []
    news_firm_violations: list[dict[str, Any]] = []
    open_entry_day: dict[tuple[int, str], str] = {}

    per_engine_slips: dict[str, list[float]] = {}
    per_engine_trades: dict[str, int] = {}

    for d in deals:
        dk = _server_day(d["utc_ts"], spec.server_utc_offset_h)
        trading_days_set.add(dk)
        ev = d["event_type"]
        is_entry = ev in ENTRY_EVENT_TYPES
        is_exit = ev in EXIT_EVENT_TYPES
        eng = d["engine_id"]
        per_engine_trades[eng] = per_engine_trades.get(eng, 0) + (1 if is_entry else 0)

        # Rule 4a: Swap == 0.0 & Rollover flat audit
        if abs(d["swap_usd"]) > 1e-6:
            nonzero_swap_count += 1
        if _in_rollover_blackout(d["utc_ts"]):
            rollover_blackout_count += 1
        pos_key = (d["magic"], d["symbol"])
        if is_entry:
            open_entry_day[pos_key] = dk
        elif is_exit:
            ent_day = open_entry_day.pop(pos_key, None)
            if ent_day is not None and ent_day != dk:
                overnight_hold_count += 1

        # Rule 4b: Red-News window check (matching symbol currency within +-guard_sec / +-firm_sec)
        sym_ccys = _symbol_currencies(d["symbol"])
        for ne in news_events:
            if ne["ccy"] not in sym_ccys:
                continue
            dt_sec = abs(d["utc_ts"] - ne["utc_ts"])
            if dt_sec <= spec.red_news_guard_sec:
                rec_v = {
                    "utc_ts": d["utc_ts"],
                    "engine_id": eng,
                    "symbol": d["symbol"],
                    "event_type": ev,
                    "news_ccy": ne["ccy"],
                    "news_event": ne["event"],
                    "delta_sec": int(dt_sec),
                }
                news_guard_violations.append(rec_v)
                if spec.red_news_firm_sec > 0 and dt_sec <= spec.red_news_firm_sec:
                    news_firm_violations.append(rec_v)
                break

        # Rule 5: Realized adverse slippage (bps) vs signal_price
        sig_px = d["signal_price"]
        fill_px = d["fill_price"]
        if sig_px > 0.0 and fill_px > 0.0:
            side = d["side"]
            # BUY entry (ENTRY/ORDER_FILL) or SELL exit (EXIT/CLOSE) pays Ask -> adverse when fill > signal
            if (is_entry and side == "BUY") or (is_exit and side == "SELL"):
                adv_bps = ((fill_px - sig_px) / sig_px) * 10_000.0
            else:
                adv_bps = ((sig_px - fill_px) / sig_px) * 10_000.0
            per_engine_slips.setdefault(eng, []).append(adv_bps)

        # Daily PnL & cumulative equity
        if d["pnl_usd"] is not None:
            daily_pnl_usd[dk] = daily_pnl_usd.get(dk, 0.0) + d["pnl_usd"]
            running_eq += d["pnl_usd"]
            equity_curve.append(running_eq)

    # Include live heartbeat DD & spread log snapshots into Rules 1 & 2
    worst_daily_dd_pct = 0.0
    for dk, pnl in daily_pnl_usd.items():
        if pnl < 0.0:
            worst_daily_dd_pct = max(worst_daily_dd_pct, (-pnl / init_bal) * 100.0)
    if isinstance(hb, dict) and hb.get("daily_dd_pct") is not None:
        worst_daily_dd_pct = max(worst_daily_dd_pct, float(hb["daily_dd_pct"]))

    min_eq = min(equity_curve)
    if isinstance(hb, dict) and hb.get("equity") is not None:
        min_eq = min(min_eq, float(hb["equity"]))
    max_total_dd_pct = max(0.0, ((init_bal - min_eq) / init_bal) * 100.0)
    if isinstance(hb, dict) and hb.get("static_dd_pct") is not None:
        max_total_dd_pct = max(max_total_dd_pct, float(hb["static_dd_pct"]))

    # Rule 1 status
    if worst_daily_dd_pct >= spec.hard_daily_loss_pct:
        r1_status = "FAIL"
    elif worst_daily_dd_pct >= spec.amber_daily_brake_pct:
        r1_status = "WARN"
    else:
        r1_status = "PASS"

    # Rule 2 status
    if max_total_dd_pct >= spec.hard_max_loss_pct or orphan_no_sl > 0 or kill_switch:
        r2_status = "FAIL"
    elif max_total_dd_pct >= spec.red_total_brake_pct:
        r2_status = "WARN"
    else:
        r2_status = "PASS"

    # Rule 3: Minimum trading days & The5ers profitable days (>= +0.50% of initial balance!)
    prof_thresh_usd = init_bal * (spec.profitable_day_threshold_pct / 100.0)
    profitable_days = [
        dk for dk, pnl in sorted(daily_pnl_usd.items())
        if spec.min_profitable_days > 0 and pnl >= prof_thresh_usd - 1e-9
    ]
    n_tdays = len(trading_days_set)
    n_pdays = len(profitable_days)
    r3_ok = (n_tdays >= spec.min_trading_days) and (n_pdays >= spec.min_profitable_days)
    r3_status = "PASS" if r3_ok else "IN_PROGRESS"

    # Rule 4: Zero Swap + Zero Overnight + Zero Red-News Violations
    r4_fail = (
        nonzero_swap_count > 0
        or overnight_hold_count > 0
        or rollover_blackout_count > 0
        or len(news_guard_violations) > 0
    )
    r4_status = "FAIL" if r4_fail else "PASS"

    # Rule 5: Per-engine realized slippage vs 1.5x backtest M1 budget
    per_engine_tca: dict[str, dict[str, Any]] = {}
    flagged_engines: list[str] = []
    for eng, slips in sorted(per_engine_slips.items()):
        budget = ENGINE_BACKTEST_SLIP_BUDGET_BPS.get(eng, DEFAULT_ENGINE_BUDGET_BPS)
        limit = round(budget * SLIPPAGE_BREACH_MULT, 3)
        mean_bps = round(sum(slips) / len(slips), 3)
        max_bps = round(max(slips), 3)
        breached = mean_bps > limit
        if breached:
            flagged_engines.append(eng)
        per_engine_tca[eng] = {
            "fills_measured": len(slips),
            "entries": per_engine_trades.get(eng, 0),
            "mean_adverse_slip_bps": mean_bps,
            "max_adverse_slip_bps": max_bps,
            "backtest_budget_bps": budget,
            "limit_1_5x_bps": limit,
            "ratio_vs_budget": round(mean_bps / max(1e-6, budget), 2),
            "breached": breached,
        }
    r5_status = "FAIL" if flagged_engines else "PASS"

    # Fail-closed Gate Decision
    hard_reasons: list[str] = []
    warn_reasons: list[str] = []
    if r1_status == "FAIL":
        hard_reasons.append(f"Rule 1 Daily Loss breach: {worst_daily_dd_pct:.2f}% >= {spec.hard_daily_loss_pct:.1f}%")
    elif r1_status == "WARN":
        warn_reasons.append(f"Rule 1 Naqex Amber brake touched: {worst_daily_dd_pct:.2f}% >= {spec.amber_daily_brake_pct:.1f}%")

    if r2_status == "FAIL":
        if orphan_no_sl > 0:
            hard_reasons.append(f"Rule 2 Orphan position without SL detected: orphan_no_sl={orphan_no_sl}")
        if kill_switch:
            hard_reasons.append("Rule 2 Orchestrator global kill_switch active")
        if max_total_dd_pct >= spec.hard_max_loss_pct:
            hard_reasons.append(f"Rule 2 Max Total Loss breach: {max_total_dd_pct:.2f}% >= {spec.hard_max_loss_pct:.1f}%")
    elif r2_status == "WARN":
        warn_reasons.append(f"Rule 2 Naqex Red brake touched: {max_total_dd_pct:.2f}% >= {spec.red_total_brake_pct:.1f}%")

    if nonzero_swap_count > 0:
        hard_reasons.append(f"Rule 4 Nonzero overnight swap detected on {nonzero_swap_count} deal(s)")
    if overnight_hold_count > 0:
        hard_reasons.append(f"Rule 4 Overnight hold across server midnight detected on {overnight_hold_count} trade(s)")
    if rollover_blackout_count > 0:
        hard_reasons.append(f"Rule 4 Deal executed inside 21:55-22:15 UTC rollover window ({rollover_blackout_count})")
    if news_guard_violations:
        hard_reasons.append(
            f"Rule 4 Red-News violation: {len(news_guard_violations)} deal(s) inside +-{spec.red_news_guard_sec}s "
            f"(firm window +-{spec.red_news_firm_sec}s: {len(news_firm_violations)})"
        )
    if flagged_engines:
        hard_reasons.append(f"Rule 5 Realized slippage > 1.5x backtest M1 budget on: {', '.join(flagged_engines)}")

    if not r3_ok:
        warn_reasons.append(
            f"Rule 3 Min days incomplete: trading={n_tdays}/{spec.min_trading_days}, "
            f"profitable(>={spec.profitable_day_threshold_pct:.2f}%)={n_pdays}/{spec.min_profitable_days}"
        )

    if hard_reasons:
        gate_decision = "HALT_AND_FIX"
        overall_status = "COMPLIANCE_VIOLATION"
        reasons = hard_reasons + warn_reasons
    elif warn_reasons:
        gate_decision = "EXTEND_SHADOW"
        overall_status = "IN_PROGRESS_MONITORING"
        reasons = warn_reasons
    else:
        gate_decision = "PASS_TO_PAID"
        overall_status = "COMPLIANT_READY_TO_PROMOTE"
        reasons = ["All 5 compliance & realized TCA rules PASSED with zero violations."]

    net_pnl_usd = round(sum(daily_pnl_usd.values()), 2)
    return {
        "schema": "naqex-prop-challenge-tracker-v1",
        "generated_utc": ts_now.isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "profile": asdict(spec),
        "status": overall_status,
        "gate_decision": gate_decision,
        "gate_reasons": reasons,
        "summary": {
            "deals_total": len(deals),
            "dryrun_signals": dryrun_signals,
            "rejected_orders": rejected_orders,
            "trading_days": n_tdays,
            "profitable_days": n_pdays,
            "net_pnl_usd": net_pnl_usd,
            "net_pnl_pct": round((net_pnl_usd / init_bal) * 100.0, 2),
            "worst_daily_dd_pct": round(worst_daily_dd_pct, 3),
            "max_total_dd_pct": round(max_total_dd_pct, 3),
            "orphan_no_sl": orphan_no_sl,
            "kill_switch": kill_switch,
            "spread_log_rows": len(spreads),
            "news_events_loaded": len(news_events),
        },
        "rules": {
            "R1_daily_loss": {
                "status": r1_status,
                "worst_daily_dd_pct": round(worst_daily_dd_pct, 3),
                "amber_buffer_pct": round(spec.amber_daily_brake_pct - worst_daily_dd_pct, 3),
                "hard_buffer_pct": round(spec.hard_daily_loss_pct - worst_daily_dd_pct, 3),
            },
            "R2_max_total_loss": {
                "status": r2_status,
                "max_total_dd_pct": round(max_total_dd_pct, 3),
                "red_buffer_pct": round(spec.red_total_brake_pct - max_total_dd_pct, 3),
                "hard_buffer_pct": round(spec.hard_max_loss_pct - max_total_dd_pct, 3),
            },
            "R3_min_days": {
                "status": r3_status,
                "trading_days": n_tdays,
                "required_trading_days": spec.min_trading_days,
                "profitable_days": n_pdays,
                "required_profitable_days": spec.min_profitable_days,
                "profitable_day_threshold_usd": round(prof_thresh_usd, 2),
                "profitable_day_dates": profitable_days,
            },
            "R4_zero_swap_and_red_news": {
                "status": r4_status,
                "nonzero_swap_count": nonzero_swap_count,
                "overnight_hold_count": overnight_hold_count,
                "rollover_blackout_count": rollover_blackout_count,
                "red_news_guard_violations": len(news_guard_violations),
                "red_news_firm_violations": len(news_firm_violations),
                "violations": news_guard_violations[:20],
            },
            "R5_engine_slippage_tca": {
                "status": r5_status,
                "flagged_engines": flagged_engines,
                "per_engine": per_engine_tca,
            },
        },
    }


def render_prop_tracker_md(payload: dict[str, Any]) -> str:
    """Render concise Vietnamese compliance & TCA scoreboard (strictly zero bare `$`)."""
    prof = payload["profile"]
    summ = payload["summary"]
    rules = payload["rules"]
    r1, r2, r3, r4, r5 = (
        rules["R1_daily_loss"],
        rules["R2_max_total_loss"],
        rules["R3_min_days"],
        rules["R4_zero_swap_and_red_news"],
        rules["R5_engine_slippage_tca"],
    )

    lines = [
        "---",
        "doc_type: prop-compliance-scoreboard",
        f"generated_utc: {payload['generated_utc']}",
        f"profile_id: {prof['profile_id']}",
        f"gate_decision: {payload['gate_decision']}",
        f"order_send_count: {payload['order_send_count']}",
        "---",
        "",
        f"# Bảng Điểm Tuân Thủ Prop Challenge & Free Trial — `{prof['firm_name']}`",
        "",
        f"- **Thời điểm UTC:** `{payload['generated_utc']}` · **Trạng thái:** `{payload['status']}`",
        f"- **Phán quyết Cổng Chuyển (Fail-Closed Gate):** **`{payload['gate_decision']}`**",
        f"- **Số dư khởi điểm:** `{prof['initial_balance_usd']:,.0f} USD` · **Lãi ròng:** `{summ['net_pnl_usd']:+,.2f} USD` (`{summ['net_pnl_pct']:+.2f}%`) · **Tổng lệnh:** `{summ['deals_total']}`",
        "",
        "## 1. Kiểm Toán 5 Quy Tắc Bắt Buộc",
        "",
        "| Quy tắc | Trạng thái | Giá trị thực đo | Ngưỡng cứng / Đệm an toàn |",
        "| --- | :---: | --- | --- |",
        f"| **R1 — Daily Loss & Amber Brake** | `{r1['status']}` | Worst Daily DD `{r1['worst_daily_dd_pct']:.2f}%` | Amber `{prof['amber_daily_brake_pct']:.1f}%` (đệm `{r1['amber_buffer_pct']:+.2f}%`) · Hard `{prof['hard_daily_loss_pct']:.1f}%` |",
        f"| **R2 — Max Total Loss & Red Brake** | `{r2['status']}` | Max Total DD `{r2['max_total_dd_pct']:.2f}%` · Orphan `{summ['orphan_no_sl']}` | Red `{prof['red_total_brake_pct']:.1f}%` (đệm `{r2['red_buffer_pct']:+.2f}%`) · Hard `{prof['hard_max_loss_pct']:.1f}%` |",
        f"| **R3 — Số Ngày Giao Dịch / Ngày Lãi** | `{r3['status']}` | Trading `{r3['trading_days']}/{r3['required_trading_days']}` · Profitable `{r3['profitable_days']}/{r3['required_profitable_days']}` | Ngưỡng ngày lãi `>= +{prof['profitable_day_threshold_pct']:.2f}%` (`>= {r3['profitable_day_threshold_usd']:,.2f} USD`) |",
        f"| **R4 — Zero Swap & Khóa Tin Đỏ** | `{r4['status']}` | Swap!=0: `{r4['nonzero_swap_count']}` · Overnight: `{r4['overnight_hold_count']}` · Rollover: `{r4['rollover_blackout_count']}` | Vi phạm Tin Đỏ (`+-{prof['red_news_guard_sec']}s`): `{r4['red_news_guard_violations']}` (Hãng `+-{prof['red_news_firm_sec']}s`: `{r4['red_news_firm_violations']}`) |",
        f"| **R5 — Trượt Giá Thực Tế (`<= 1.5x` M1)** | `{r5['status']}` | Động cơ vượt ngưỡng: `{len(r5['flagged_engines'])}` | Danh sách cờ đỏ: `{', '.join(r5['flagged_engines']) if r5['flagged_engines'] else 'NONE'}` |",
        "",
    ]

    if r5["per_engine"]:
        lines += [
            "## 2. Đối Soát Trượt Giá Thực Tế Theo Động Cơ (`bps` so với ngân sách M1)",
            "",
            "| Động cơ | Số khớp | Trượt giá TB (bps) | Max (bps) | Ngân sách M1 (bps) | Giới hạn 1.5x (bps) | Kết luận |",
            "| --- | ---: | ---: | ---: | ---: | ---: | :---: |",
        ]
        for eng, st in r5["per_engine"].items():
            ver = "FLAG_BREACH" if st["breached"] else "OK"
            lines.append(
                f"| `{eng}` | `{st['fills_measured']}` | `{st['mean_adverse_slip_bps']:.3f}` | `{st['max_adverse_slip_bps']:.3f}` "
                f"| `{st['backtest_budget_bps']:.2f}` | `{st['limit_1_5x_bps']:.3f}` | `{ver}` |"
            )
        lines.append("")

    lines += ["## 3. Lý Do Phán Quyết Cổng", ""]
    for reason in payload["gate_reasons"]:
        lines.append(f"- {reason}")
    lines.append("")

    md_txt = "\n".join(lines)
    assert "$" not in md_txt, "Bare '$' detected in prop challenge tracker Markdown!"
    return md_txt


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Naqex Prop-Challenge & 14-Day Free-Trial Compliance Tracker (OrderSend=0)")
    ap.add_argument("--profile", choices=sorted(PROP_PROFILES.keys()), default="ftmo_swing_10k")
    ap.add_argument("--exec-audit-csv", type=Path, default=DEFAULT_EXEC_AUDIT_CSV)
    ap.add_argument("--spread-log-jsonl", type=Path, default=DEFAULT_SPREAD_LOG_JSONL)
    ap.add_argument("--news-csv", type=Path, default=DEFAULT_NEWS_CSV)
    ap.add_argument("--heartbeat-json", type=Path, default=DEFAULT_HEARTBEAT_JSON)
    ap.add_argument("--out-md", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args(argv)

    payload = evaluate_prop_challenge(
        profile_id=args.profile,
        exec_audit_csv=args.exec_audit_csv,
        spread_log_jsonl=args.spread_log_jsonl,
        news_csv=args.news_csv,
        heartbeat_json=args.heartbeat_json,
    )
    md = render_prop_tracker_md(payload)

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    if args.out_md is not None:
        args.out_md.parent.mkdir(parents=True, exist_ok=True)
        args.out_md.write_text(md, encoding="utf-8", newline="\n")

    print(json.dumps({
        "schema": payload["schema"],
        "profile_id": payload["profile"]["profile_id"],
        "status": payload["status"],
        "gate_decision": payload["gate_decision"],
        "deals_total": payload["summary"]["deals_total"],
        "out_md": str(args.out_md) if args.out_md else None,
        "out_json": str(args.out_json) if args.out_json else None,
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
