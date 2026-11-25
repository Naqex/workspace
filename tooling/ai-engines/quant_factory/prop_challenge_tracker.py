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
import re
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
    reset_tz: str = "Europe/Prague"  # Europe/Prague (FTMO DST-aware) | NY_CLOSE_SERVER (The5ers US DST) | UTC


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
        reset_tz="Europe/Prague",
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
        reset_tz="Europe/Prague",
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
        reset_tz="NY_CLOSE_SERVER",
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
        reset_tz="NY_CLOSE_SERVER",
    ),
    "ftmo_swing_25k": PropProfileSpec(
        profile_id="ftmo_swing_25k",
        firm_name="FTMO Swing 25K",
        initial_balance_usd=25_000.0,
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
        reset_tz="Europe/Prague",
    ),
    "ftmo_swing_50k": PropProfileSpec(
        profile_id="ftmo_swing_50k",
        firm_name="FTMO Swing 50K",
        initial_balance_usd=50_000.0,
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
        reset_tz="Europe/Prague",
    ),
    "ftmo_swing_100k": PropProfileSpec(
        profile_id="ftmo_swing_100k",
        firm_name="FTMO Swing 100K",
        initial_balance_usd=100_000.0,
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
        reset_tz="Europe/Prague",
    ),
    "the5ers_hs_50k": PropProfileSpec(
        profile_id="the5ers_hs_50k",
        firm_name="The5ers High Stakes 50K/60K (Strict 4%/8% DD)",
        initial_balance_usd=50_000.0,
        profit_target_pct=8.0,
        hard_daily_loss_pct=4.0,
        amber_daily_brake_pct=2.8,
        hard_max_loss_pct=8.0,
        red_total_brake_pct=5.6,
        min_trading_days=3,
        min_profitable_days=3,
        profitable_day_threshold_pct=0.50,
        red_news_firm_sec=120,
        red_news_guard_sec=300,
        reset_tz="NY_CLOSE_SERVER",
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
CORE7_ENGINES: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
)
DEFAULT_ENGINE_BUDGET_BPS = 1.60
SLIPPAGE_BREACH_MULT = 1.50
NEWS_HARD_BAN_SEC = 135
BOJ_ESTIMATED_PAD_SEC = 3600
ENTRY_EVENT_TYPES: frozenset[str] = frozenset({"ENTRY", "ORDER_FILL", "ENTRY_FILLED", "PARTIAL_ENTRY"})
EXIT_EVENT_TYPES: frozenset[str] = frozenset({
    "EXIT", "ORDER_CLOSE", "CLOSE", "EXIT_FILLED", "PARTIAL_EXIT",
    "SL_HIT", "TP_HIT", "TIME_EXIT", "PRE_FLATTEN_EXIT",
})
VALID_FILL_EVENT_TYPES: frozenset[str] = ENTRY_EVENT_TYPES | EXIT_EVENT_TYPES
NON_FILL_EVENT_TYPES: frozenset[str] = frozenset({
    "DRYRUN_SIGNAL", "ORDER_REJECT", "ORDER_BLOCKED_SYMCAP",
    "ORDER_BLOCKED_FACTOR", "ORDER_BLOCKED_RISK", "CLOSE_REJECT",
    "FILL_UNRESOLVED", "SHADOW_INTENT",
})


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


def _nth_sunday_day(year: int, month: int, nth: int) -> int:
    first_wd = datetime(year, month, 1, tzinfo=timezone.utc).weekday()  # Mon=0..Sun=6
    first_sun = 1 + (6 - first_wd) % 7
    return first_sun + 7 * (nth - 1)


def _last_sunday_day(year: int, month: int) -> int:
    next_m = datetime(year + 1, 1, 1, tzinfo=timezone.utc) if month == 12 else datetime(year, month + 1, 1, tzinfo=timezone.utc)
    last_d = next_m.timestamp() - 86_400
    dt = datetime.fromtimestamp(last_d, timezone.utc)
    return dt.day - ((dt.weekday() - 6) % 7)


def _prague_utc_offset_h(utc_dt: datetime) -> int:
    """Exact EU DST offset for Europe/Prague (FTMO): CEST +2h last Sun Mar 01:00 UTC -> last Sun Oct 01:00 UTC, else CET +1h."""
    y, m, d, h = utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour
    if m < 3 or m > 10:
        return 1
    if 3 < m < 10:
        return 2
    ls = _last_sunday_day(y, m)
    if m == 3:
        return 2 if (d > ls or (d == ls and h >= 1)) else 1
    return 2 if (d < ls or (d == ls and h < 1)) else 1


def _ny_close_server_offset_h(utc_dt: datetime) -> int:
    """Exact NY+7 server offset (The5ers / FTMO server time): UTC+3 during US EDT, UTC+2 during US EST."""
    y, m, d, h = utc_dt.year, utc_dt.month, utc_dt.day, utc_dt.hour
    if m < 3 or m > 11:
        return 2
    if 3 < m < 11:
        return 3
    if m == 3:
        s2 = _nth_sunday_day(y, 3, 2)
        return 3 if (d > s2 or (d == s2 and h >= 7)) else 2
    s1 = _nth_sunday_day(y, 11, 1)
    return 3 if (d < s1 or (d == s1 and h < 6)) else 2


def _firm_reset_day(utc_ts: int, reset_tz: str = "Europe/Prague", fallback_offset_h: int = 2) -> str:
    utc_dt = datetime.fromtimestamp(utc_ts, timezone.utc)
    if reset_tz == "Europe/Prague":
        off_h = _prague_utc_offset_h(utc_dt)
    elif reset_tz == "NY_CLOSE_SERVER":
        off_h = _ny_close_server_offset_h(utc_dt)
    elif reset_tz == "UTC":
        off_h = 0
    else:
        off_h = fallback_offset_h
    return datetime.fromtimestamp(utc_ts + off_h * 3600, timezone.utc).strftime("%Y-%m-%d")


def _server_day(utc_ts: int, offset_h: int = 2) -> str:
    return datetime.fromtimestamp(utc_ts + offset_h * 3600, timezone.utc).strftime("%Y-%m-%d")


def _in_rollover_blackout(utc_ts: int) -> bool:
    """True when UTC timestamp sits inside the 21:55..22:15 UTC broker rollover spread-widening window."""
    dt = datetime.fromtimestamp(utc_ts, timezone.utc)
    mins = dt.hour * 60 + dt.minute
    return (21 * 60 + 55) <= mins <= (22 * 60 + 15)


_SYMBOL_SUFFIX_RE = re.compile(r"(?:\.(?:CASH|PRO|RAW|ECN|STD|MINI|MICRO|M|I|C)|[-_](?:CASH|PRO|RAW|C))$")


def _normalize_symbol(symbol: str) -> str:
    """Normalize broker alias symbols (NAS100/NDX/USTEC -> US100, SPX -> US500, DE40/DAX -> GER40, etc.)."""
    s = _SYMBOL_SUFFIX_RE.sub("", (symbol or "").strip().upper())
    if any(k in s for k in ("US100", "NAS100", "USTEC", "NDX", "NAS")):
        return "US100"
    if any(k in s for k in ("US500", "SPX500", "SPX", "SP500")):
        return "US500"
    if any(k in s for k in ("US30", "DJ30", "WS30")):
        return "US30"
    if any(k in s for k in ("GER40", "DE40", "GER30", "DAX")):
        return "GER40"
    if any(k in s for k in ("UK100", "FTSE")):
        return "UK100"
    if "XAU" in s or "GOLD" in s:
        return "XAUUSD"
    if "BTC" in s:
        return "BTCUSD"
    return s


def _symbol_currencies(symbol: str) -> set[str]:
    """Map FX pairs, US/EU/UK equity indices (NAS100/NDX/USTEC/SPX/US30/DE40/DAX/UK100), gold & BTC to news currencies."""
    s = _SYMBOL_SUFFIX_RE.sub("", (symbol or "").strip().upper())
    if any(k in s for k in ("US100", "NAS100", "USTEC", "NDX", "NAS", "US500", "SPX", "SP500", "US30", "DJ30", "WS30")):
        return {"USD"}
    if any(k in s for k in ("GER40", "DE40", "GER30", "DAX")):
        return {"EUR"}
    if any(k in s for k in ("UK100", "FTSE")):
        return {"GBP"}
    if "XAU" in s or "GOLD" in s or "BTC" in s:
        return {"USD"}
    ccys: set[str] = set()
    for c in ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD"):
        if c in s:
            ccys.add(c)
    return ccys or {"USD"}


def _build_tracker_risk_attribution(
    *,
    alerts: list[dict[str, Any]],
    net_pnl_pct: float,
    losing_days: int,
    total_trading_days: int,
) -> dict[str, Any]:
    """Aggregate structured R4 -> R3 -> R2 -> R1 triage from rule alerts (fail-closed priority)."""
    order = ["R4", "R3", "R2", "R1"]
    titles = {
        "R4": "Luật quỹ, Tin đỏ & Kill-Switch",
        "R3": "Khớp lệnh, Trượt giá, Swap & Thiếu SL",
        "R2": "Tập trung mã (SYMCAP) & Phanh danh mục",
        "R1": "Lợi thế thật của chiến lược",
    }
    by_layer: dict[str, list[dict[str, Any]]] = {k: [] for k in order}
    for a in alerts:
        lbl = str(a.get("risk_label") or "R4")
        if lbl in by_layer:
            by_layer[lbl].append(a)

    layers: dict[str, dict[str, Any]] = {}
    for code in ("R4", "R3", "R2"):
        items = by_layer[code]
        has_fail = any(x.get("severity") == "FAIL" for x in items)
        has_warn = any(x.get("severity") in ("WARN", "IN_PROGRESS") for x in items)
        if has_fail:
            st = "ALERT"
            detail = "; ".join(str(x["message"]) for x in items if x.get("severity") == "FAIL")
        elif has_warn:
            st = "WARN"
            detail = "; ".join(str(x["message"]) for x in items)
        else:
            st = "OK"
            detail = "Sạch — không có vi phạm ở tầng này."
        layers[code] = {"code": code, "title": titles[code], "status": st, "detail": detail, "count": len(items)}

    upstream_alert = any(layers[c]["status"] == "ALERT" for c in ("R4", "R3", "R2"))
    if by_layer["R1"]:
        has_fail = any(x.get("severity") == "FAIL" for x in by_layer["R1"])
        layers["R1"] = {
            "code": "R1",
            "title": titles["R1"],
            "status": "ALERT" if has_fail else "WARN",
            "detail": "; ".join(str(x["message"]) for x in by_layer["R1"]),
            "count": len(by_layer["R1"]),
        }
    elif upstream_alert:
        layers["R1"] = {
            "code": "R1",
            "title": titles["R1"],
            "status": "OK",
            "detail": "Tạm chưa quy lỗi cho chiến lược — xử lý tầng R4/R3/R2 trước.",
            "count": 0,
        }
    elif net_pnl_pct <= -2.5 or (total_trading_days >= 4 and losing_days >= 4 and net_pnl_pct < -1.0):
        layers["R1"] = {
            "code": "R1",
            "title": titles["R1"],
            "status": "ALERT",
            "detail": f"Lỗ ròng {net_pnl_pct:+.2f}% ({losing_days}/{total_trading_days} ngày âm) khi R4/R3/R2 đều sạch — cần kiểm tra suy giảm lợi thế.",
            "count": 1,
        }
    else:
        layers["R1"] = {
            "code": "R1",
            "title": titles["R1"],
            "status": "OK",
            "detail": "Bình thường — chưa có dấu hiệu suy giảm lợi thế chiến lược.",
            "count": 0,
        }

    active_label = "OK"
    for code in order:
        if layers[code]["status"] == "ALERT":
            active_label = code
            break
    if active_label == "OK":
        for code in order:
            if layers[code]["status"] == "WARN":
                active_label = code
                break

    if active_label == "OK":
        headline_vi = "Cả 4 tầng R4 → R3 → R2 → R1 đều XANH."
    else:
        act = layers[active_label]
        headline_vi = f"{active_label} ({act['title']}) [{act['status']}]: {act['detail']}"

    return {
        "active_label": active_label,
        "check_order": order,
        "headline_vi": headline_vi,
        "layers": layers,
    }


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


_TAG_ID_RE = re.compile(r"\b(deal|ord|tk|pos|intent)=([A-Za-z0-9_-]+)")


def _extract_comment_ids(comment: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in _TAG_ID_RE.findall(comment or ""):
        out[k] = v
    return out


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
            has_swap = ("swap_usd" in r and str(r.get("swap_usd") or "").strip() != "")
            has_comm = ("commission_usd" in r and str(r.get("commission_usd") or "").strip() != "")
            comment = str(r.get("comment") or "").strip()
            tag_ids = _extract_comment_ids(comment)
            exec_side = str(r.get("deal_side") or r.get("exec_side") or r.get("side") or "").strip().upper()
            pos_side = str(r.get("position_side") or "").strip().upper()
            rows.append({
                "utc_ts": ts,
                "magic": magic,
                "engine_id": eng,
                "symbol": str(r.get("symbol") or "").strip(),
                "side": exec_side,
                "position_side": pos_side,
                "event_type": str(r.get("event_type") or "").strip().upper(),
                "signal_price": _to_float(r.get("signal_price"), 0.0),
                "fill_price": _to_float(r.get("fill_price"), -1.0),
                "sl_price": _to_float(r.get("sl_price"), 0.0),
                "lots": _to_float(r.get("lots"), 0.0),
                "spread_pts": _to_float(r.get("spread_pts"), 0.0),
                "latency_ms": _to_float(r.get("latency_ms"), 0.0),
                "retcode": _to_int(r.get("retcode"), 0),
                "pnl_usd": _to_float(r.get("pnl_usd"), 0.0) if "pnl_usd" in r and str(r.get("pnl_usd") or "").strip() != "" else None,
                "swap_usd": _to_float(r.get("swap_usd"), 0.0) if has_swap else None,
                "commission_usd": _to_float(r.get("commission_usd"), 0.0) if has_comm else None,
                "account_login": _to_int(r.get("account_login"), 0),
                "deal_id": str(r.get("deal_id") or tag_ids.get("deal") or "").strip(),
                "order_id": str(r.get("order_id") or tag_ids.get("ord") or "").strip(),
                "position_id": str(r.get("position_id") or tag_ids.get("pos") or tag_ids.get("tk") or "").strip(),
                "intent_id": str(r.get("intent_id") or tag_ids.get("intent") or "").strip(),
                "comment": comment,
            })
    rows.sort(key=lambda x: x["utc_ts"])
    return rows


def load_broker_statement_rows(statement_csv: Path | None) -> list[dict[str, Any]]:
    """Load broker statement deal rows for deterministic reconciliation by account + deal/order/position ID."""
    if statement_csv is None or not statement_csv.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with statement_csv.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            deal_id = str(r.get("deal_id") or r.get("deal") or r.get("ticket") or "").strip()
            order_id = str(r.get("order_id") or r.get("order") or "").strip()
            pos_id = str(r.get("position_id") or r.get("position") or "").strip()
            if not (deal_id or order_id or pos_id):
                continue
            rows.append({
                "account_login": _to_int(r.get("account_login") or r.get("login"), 0),
                "deal_id": deal_id,
                "order_id": order_id,
                "position_id": pos_id,
                "symbol": str(r.get("symbol") or "").strip(),
                "side": str(r.get("side") or r.get("type") or "").strip().upper(),
                "entry_flag": str(r.get("entry") or r.get("direction") or "").strip().upper(),
                "volume": _to_float(r.get("volume") or r.get("lots"), 0.0),
                "price": _to_float(r.get("price") or r.get("fill_price"), 0.0),
                "pnl_usd": _to_float(r.get("pnl_usd") or r.get("profit"), 0.0)
                if any(str(r.get(k) or "").strip() != "" for k in ("pnl_usd", "profit"))
                else None,
                "swap_usd": _to_float(r.get("swap_usd") or r.get("swap"), 0.0)
                if any(str(r.get(k) or "").strip() != "" for k in ("swap_usd", "swap"))
                else None,
                "commission_usd": _to_float(r.get("commission_usd") or r.get("commission"), 0.0)
                if any(str(r.get(k) or "").strip() != "" for k in ("commission_usd", "commission"))
                else 0.0,
            })
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
    statement_csv: Path | None = None,
    now_utc: datetime | None = None,
    require_statement: bool = True,
    require_heartbeat: bool = True,
    require_news_calendar: bool = True,
    min_closed_trades: int = 10,
    min_distinct_engines: int = 2,
    min_trial_calendar_days: int = 4,
    expected_account_login: int | None = None,
) -> dict[str, Any]:
    """Evaluate all 6 broker-aligned compliance, reconciliation & TCA rules (fail-closed Gate Decision)."""
    if profile_id not in PROP_PROFILES:
        raise ValueError(f"Unknown profile '{profile_id}'. Expected one of {sorted(PROP_PROFILES.keys())}")
    spec = PROP_PROFILES[profile_id]
    ts_now = now_utc or datetime.now(timezone.utc)

    all_rows = load_exec_audit_rows(exec_audit_csv)
    dryrun_signals = sum(1 for r in all_rows if r["event_type"] == "DRYRUN_SIGNAL")
    rejected_orders = sum(1 for r in all_rows if r["event_type"] == "ORDER_REJECT")
    close_rejects = sum(1 for r in all_rows if r["event_type"] == "CLOSE_REJECT")
    blocked_orders = sum(1 for r in all_rows if r["event_type"].startswith("ORDER_BLOCKED"))
    ignored_unknown_events = sum(
        1 for r in all_rows
        if r["event_type"] not in VALID_FILL_EVENT_TYPES and r["event_type"] not in NON_FILL_EVENT_TYPES
    )
    # R2-01 STRICT ALLOWLIST: only actual executed fills enter `deals` and count toward trading days!
    deals = [r for r in all_rows if r["event_type"] in VALID_FILL_EVENT_TYPES]
    explicit_unresolved_rows = sum(1 for r in all_rows if r["event_type"] == "FILL_UNRESOLVED")
    spreads = load_spread_log_rows(spread_log_jsonl)
    news_events = load_red_news_events(news_csv)
    hb = load_heartbeat_json(heartbeat_json)
    stmt_rows = load_broker_statement_rows(statement_csv)

    init_bal = spec.initial_balance_usd

    # Detect pre-trade empty state gracefully (zero live executed deals AND no PnL movement)
    orphan_no_sl = int((hb or {}).get("orphan_no_sl", 0)) if isinstance(hb, dict) else 0
    kill_switch = bool((hb or {}).get("kill_switch", False)) if isinstance(hb, dict) else False

    if not deals and orphan_no_sl == 0 and not kill_switch and explicit_unresolved_rows == 0:
        hb_daily_dd = float((hb or {}).get("daily_dd_pct", 0.0)) if isinstance(hb, dict) else 0.0
        hb_static_dd = float((hb or {}).get("static_dd_pct", 0.0)) if isinstance(hb, dict) else 0.0
        pre_alerts = [
            {
                "rule_id": "R3_min_days",
                "severity": "IN_PROGRESS",
                "risk_label": "R4",
                "message": "Zero executed deals recorded yet (pre-trade standby); keep Free Trial / Shadow running.",
            }
        ]
        return {
            "schema": "naqex-prop-challenge-tracker-v1",
            "generated_utc": ts_now.isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "profile": asdict(spec),
            "status": "PRE_TRADE_READY",
            "gate_decision": "EXTEND_SHADOW",
            "gate_reasons": ["Zero executed deals recorded yet (pre-trade standby); keep Free Trial / Shadow running."],
            "alerts": pre_alerts,
            "risk_attribution": _build_tracker_risk_attribution(
                alerts=pre_alerts, net_pnl_pct=0.0, losing_days=0, total_trading_days=0,
            ),
            "summary": {
                "deals_total": 0,
                "entry_deals": 0,
                "closed_deals": 0,
                "reconciled_closed_trades": 0,
                "dryrun_signals": dryrun_signals,
                "rejected_orders": rejected_orders,
                "close_rejects": close_rejects,
                "blocked_orders": blocked_orders,
                "ignored_unknown_events": ignored_unknown_events,
                "trading_days": 0,
                "profitable_days": 0,
                "trial_calendar_days": 0,
                "net_pnl_usd": 0.0,
                "net_pnl_pct": 0.0,
                "worst_daily_dd_pct": round(hb_daily_dd, 3),
                "max_total_dd_pct": round(hb_static_dd, 3),
                "orphan_no_sl": orphan_no_sl,
                "kill_switch": kill_switch,
                "spread_log_rows": len(spreads),
                "news_events_loaded": len(news_events),
                "statement_rows_loaded": len(stmt_rows),
                "engines_observed": [],
                "core7_missing_engines": list(CORE7_ENGINES),
                "symbol_concentration": {},
            },
            "rules": {
                "R1_daily_loss": {"status": "PASS", "risk_label": "OK", "worst_daily_dd_pct": round(hb_daily_dd, 3), "amber_buffer_pct": round(spec.amber_daily_brake_pct - hb_daily_dd, 3), "hard_buffer_pct": round(spec.hard_daily_loss_pct - hb_daily_dd, 3)},
                "R2_max_total_loss": {"status": "PASS", "risk_label": "OK", "max_total_dd_pct": round(hb_static_dd, 3), "red_buffer_pct": round(spec.red_total_brake_pct - hb_static_dd, 3), "hard_buffer_pct": round(spec.hard_max_loss_pct - hb_static_dd, 3)},
                "R3_min_days": {"status": "IN_PROGRESS", "risk_label": "R4", "trading_days": 0, "required_trading_days": spec.min_trading_days, "profitable_days": 0, "required_profitable_days": spec.min_profitable_days, "profitable_day_threshold_usd": round(init_bal * spec.profitable_day_threshold_pct / 100.0, 2)},
                "R4_zero_swap_and_red_news": {"status": "PASS", "risk_label": "OK", "nonzero_swap_count": 0, "missing_swap_count": 0, "overnight_hold_count": 0, "rollover_blackout_count": 0, "valid_pre_flatten_exits": 0, "red_news_guard_violations": 0, "red_news_firm_violations": 0, "violations": []},
                "R5_engine_slippage_tca": {"status": "PASS", "risk_label": "OK", "flagged_engines": [], "unresolved_fill_count": 0, "unmeasured_engines": [], "per_engine": {}},
                "R6_reconciliation_and_coverage": {"status": "IN_PROGRESS", "risk_label": "R3", "closed_deals": 0, "min_closed_trades": min_closed_trades, "reconciled_closed_trades": 0, "unclosed_entries": 0, "engines_observed": [], "core7_missing_engines": list(CORE7_ENGINES), "statement_reconciled": False, "heartbeat_present": hb is not None},
            },
        }

    # --- Index optional broker statement rows for deterministic join (account + deal/order/position ID) ---
    stmt_by_deal: dict[str, dict[str, Any]] = {}
    stmt_by_order: dict[str, dict[str, Any]] = {}
    stmt_by_pos: dict[str, list[dict[str, Any]]] = {}
    stmt_logins: set[int] = set()
    for sr in stmt_rows:
        if sr["account_login"] > 0:
            stmt_logins.add(sr["account_login"])
        if sr["deal_id"]:
            stmt_by_deal[sr["deal_id"]] = sr
        if sr["order_id"]:
            stmt_by_order[sr["order_id"]] = sr
        if sr["position_id"]:
            stmt_by_pos.setdefault(sr["position_id"], []).append(sr)

    # --- Aggregate daily PnL, watermark DD, trading days & profitable days ---
    daily_pnl_usd: dict[str, float] = {}
    trading_days_set: set[str] = set()
    equity_curve = [init_bal]
    running_eq = init_bal

    nonzero_swap_count = 0
    missing_swap_count = 0
    missing_pnl_exits_count = 0
    unresolved_fill_count = explicit_unresolved_rows
    overnight_hold_count = 0
    rollover_blackout_count = 0
    valid_pre_flatten_exits = 0
    news_guard_violations: list[dict[str, Any]] = []
    news_firm_violations: list[dict[str, Any]] = []
    open_entry_day: dict[tuple[Any, ...], list[str]] = {}
    entry_count = 0
    closed_deals_count = 0
    reconciled_closed_trades = 0
    statement_matched_deals = 0
    statement_unmatched_deals = 0

    per_engine_slips: dict[str, list[float]] = {}
    per_engine_trades: dict[str, int] = {}
    engines_observed_set: set[str] = set()
    symbol_pnl_usd: dict[str, float] = {}
    symbol_day_entries: dict[tuple[str, str], int] = {}

    for d in deals:
        dk = _firm_reset_day(d["utc_ts"], spec.reset_tz, spec.server_utc_offset_h)
        trading_days_set.add(dk)
        ev = d["event_type"]
        is_entry = ev in ENTRY_EVENT_TYPES
        is_exit = ev in EXIT_EVENT_TYPES
        is_pre_flatten = (ev == "PRE_FLATTEN_EXIT") or ("NEWS_PRE_FLATTEN" in d["comment"].upper())
        eng = d["engine_id"]
        engines_observed_set.add(eng)
        norm_sym = _normalize_symbol(d["symbol"])
        if is_entry:
            entry_count += 1
        if is_exit:
            closed_deals_count += 1
        per_engine_trades[eng] = per_engine_trades.get(eng, 0) + (1 if is_entry else 0)
        if is_entry and norm_sym:
            symbol_day_entries[(dk, norm_sym)] = symbol_day_entries.get((dk, norm_sym), 0) + 1

        # Enrich / reconcile against optional broker statement (by deal_id -> order_id -> position_id)
        matched_sr: dict[str, Any] | None = None
        if stmt_rows:
            if d["deal_id"] and d["deal_id"] in stmt_by_deal:
                matched_sr = stmt_by_deal[d["deal_id"]]
            elif d["order_id"] and d["order_id"] in stmt_by_order:
                matched_sr = stmt_by_order[d["order_id"]]
            elif d["position_id"] and d["position_id"] in stmt_by_pos:
                cands = stmt_by_pos[d["position_id"]]
                matched_sr = cands[-1] if is_exit else cands[0]
            if matched_sr is not None:
                statement_matched_deals += 1
            else:
                statement_unmatched_deals += 1

        eff_swap = d["swap_usd"]
        if eff_swap is None and matched_sr is not None and matched_sr["swap_usd"] is not None:
            eff_swap = matched_sr["swap_usd"]
        eff_pnl = d["pnl_usd"]
        if eff_pnl is None and matched_sr is not None and matched_sr["pnl_usd"] is not None:
            eff_pnl = matched_sr["pnl_usd"]
        if is_exit and eff_pnl is None:
            missing_pnl_exits_count += 1

        # Rule 4a: Swap == 0.0 & Rollover flat audit (fail-closed if EXIT row lacks swap_usd!)
        if eff_swap is None:
            if is_exit:
                missing_swap_count += 1
        elif abs(eff_swap) > 1e-6:
            nonzero_swap_count += 1
        if _in_rollover_blackout(d["utc_ts"]):
            rollover_blackout_count += 1

        pos_key = ("POS", d["position_id"]) if d["position_id"] else ("MS", d["magic"], d["symbol"])
        if is_entry:
            open_entry_day.setdefault(pos_key, []).append(dk)
        elif is_exit:
            stack = open_entry_day.get(pos_key)
            if stack:
                ent_day = stack.pop(0)
                if not stack:
                    open_entry_day.pop(pos_key, None)
                reconciled_closed_trades += 1
                if ent_day != dk:
                    overnight_hold_count += 1

        # Rule 4b: Red-News window check (respects defensive PRE_FLATTEN outside +-135s & BoJ estimated window!)
        sym_ccys = _symbol_currencies(d["symbol"])
        for ne in news_events:
            if ne["ccy"] not in sym_ccys:
                continue
            pad_sec = BOJ_ESTIMATED_PAD_SEC if "EST03UTC" in ne["event"].upper() else spec.red_news_guard_sec
            signed_before_sec = ne["utc_ts"] - d["utc_ts"]  # >0 means BEFORE news release
            dt_sec = abs(signed_before_sec)
            if dt_sec <= pad_sec:
                # Defensive pre-flatten strictly BEFORE hard +-135s no-execution zone is compliant, NOT a violation!
                if is_exit and is_pre_flatten and signed_before_sec > NEWS_HARD_BAN_SEC:
                    valid_pre_flatten_exits += 1
                    break
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

        # Rule 5: Realized adverse slippage (bps) vs signal_price — EXECUTION/DEAL SIDE CONVENTION!
        # BUY deal (opening LONG or closing SHORT) pays Ask -> adverse when fill > signal.
        # SELL deal (opening SHORT or closing LONG) hits Bid -> adverse when fill < signal.
        sig_px = d["signal_price"]
        fill_px = d["fill_price"]
        if ev == "FILL_UNRESOLVED" or "FILL_UNRESOLVED" in d["comment"].upper() or fill_px <= 0.0:
            unresolved_fill_count += 1
        elif sig_px > 0.0 and fill_px > 0.0:
            deal_side = d["side"]
            if not deal_side and d["position_side"]:
                # Fallback ONLY when CSV omits execution `side` and supplies `position_side`
                if is_exit:
                    deal_side = "SELL" if d["position_side"] == "BUY" else "BUY"
                else:
                    deal_side = d["position_side"]
            if deal_side == "BUY":
                adv_bps = ((fill_px - sig_px) / sig_px) * 10_000.0
            elif deal_side == "SELL":
                adv_bps = ((sig_px - fill_px) / sig_px) * 10_000.0
            else:
                # Unknown side -> fail-closed treat absolute price deviation as adverse!
                adv_bps = (abs(fill_px - sig_px) / sig_px) * 10_000.0
            per_engine_slips.setdefault(eng, []).append(adv_bps)

        # Daily PnL & cumulative equity
        if eff_pnl is not None:
            daily_pnl_usd[dk] = daily_pnl_usd.get(dk, 0.0) + eff_pnl
            if norm_sym:
                symbol_pnl_usd[norm_sym] = symbol_pnl_usd.get(norm_sym, 0.0) + eff_pnl
            running_eq += eff_pnl
            equity_curve.append(running_eq)

    unclosed_entries_count = sum(len(v) for v in open_entry_day.values())
    engines_observed = sorted(engines_observed_set)
    core7_missing = [e for e in CORE7_ENGINES if e not in engines_observed_set]
    trial_calendar_days = 0
    if deals:
        first_d = datetime.fromtimestamp(deals[0]["utc_ts"], timezone.utc).date()
        last_d = datetime.fromtimestamp(deals[-1]["utc_ts"], timezone.utc).date()
        trial_calendar_days = (last_d - first_d).days + 1

    # Include live heartbeat DD & spread log snapshots into Rules 1 & 2
    worst_daily_dd_pct = 0.0
    for dk, pnl in daily_pnl_usd.items():
        if pnl < 0.0:
            worst_daily_dd_pct = max(worst_daily_dd_pct, (-pnl / init_bal) * 100.0)
    if isinstance(hb, dict) and hb.get("daily_dd_pct") is not None:
        worst_daily_dd_pct = max(worst_daily_dd_pct, float(hb["daily_dd_pct"]))

    min_eq = min(equity_curve)
    if isinstance(hb, dict) and hb.get("equity") is not None and hb.get("terminal_connected") is not False:
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

    # Rule 5: Per-engine realized slippage vs 1.5x backtest M1 budget (adverse-only + P50/P90, no masking!)
    per_engine_tca: dict[str, dict[str, Any]] = {}
    flagged_engines: list[str] = []
    for eng, slips in sorted(per_engine_slips.items()):
        budget = ENGINE_BACKTEST_SLIP_BUDGET_BPS.get(eng, DEFAULT_ENGINE_BUDGET_BPS)
        limit = round(budget * SLIPPAGE_BREACH_MULT, 3)
        pos_slips = sorted(max(0.0, s) for s in slips)
        n_s = len(pos_slips)
        mean_bps = round(sum(slips) / n_s, 3)
        mean_pos_bps = round(sum(pos_slips) / n_s, 3)
        p50_bps = round(pos_slips[min(n_s - 1, int(0.50 * (n_s - 1)))], 3)
        p90_bps = round(pos_slips[min(n_s - 1, int(0.90 * (n_s - 1)))], 3)
        max_bps = round(max(pos_slips), 3)
        breached = (mean_bps > limit) or (mean_pos_bps > limit) or (p90_bps > round(budget * 2.5, 3))
        if breached:
            flagged_engines.append(eng)
        per_engine_tca[eng] = {
            "fills_measured": n_s,
            "entries": per_engine_trades.get(eng, 0),
            "mean_adverse_slip_bps": mean_bps,
            "mean_positive_adverse_slip_bps": mean_pos_bps,
            "p50_adverse_slip_bps": p50_bps,
            "p90_adverse_slip_bps": p90_bps,
            "max_adverse_slip_bps": max_bps,
            "backtest_budget_bps": budget,
            "limit_1_5x_bps": limit,
            "ratio_vs_budget": round(mean_pos_bps / max(1e-6, budget), 2),
            "breached": breached,
        }
    unmeasured_engines = sorted(e for e, cnt in per_engine_trades.items() if cnt > 0 and e not in per_engine_tca)
    if flagged_engines:
        r5_status = "FAIL"
    elif unresolved_fill_count > 0 or unmeasured_engines:
        r5_status = "WARN"
    else:
        r5_status = "PASS"

    # Rule 6 (Astra R2-01 CRITICAL): Reconciliation, Closed Deals, Statement Join, Heartbeat & Fleet Coverage
    r6_hard_issues: list[str] = []
    r6_warn_issues: list[str] = []

    if hb is not None and hb.get("terminal_connected") is False:
        r6_hard_issues.append("Heartbeat reports terminal_connected=false (broker disconnected)")
    if expected_account_login is not None:
        if hb is not None and int(hb.get("account_login") or 0) not in (0, expected_account_login):
            r6_hard_issues.append(f"Heartbeat account_login={hb.get('account_login')} != expected {expected_account_login}")
        if stmt_logins and expected_account_login not in stmt_logins:
            r6_hard_issues.append(f"Broker statement logins {sorted(stmt_logins)} do not match expected {expected_account_login}")

    if closed_deals_count <= 0:
        r6_warn_issues.append("Zero closed deals recorded (entries without reconciled exits cannot pass gate)")
    elif closed_deals_count < max(1, min_closed_trades):
        r6_warn_issues.append(f"Insufficient closed deals: {closed_deals_count}/{min_closed_trades} required by SOP")
    if missing_pnl_exits_count > 0:
        r6_warn_issues.append(f"Missing realized pnl_usd on {missing_pnl_exits_count} closed deal(s)")
    if close_rejects > 0:
        r6_warn_issues.append(f"Observed {close_rejects} CLOSE_REJECT event(s) — verify position closure")
    if unclosed_entries_count > 0:
        hb_open = int(hb.get("open_positions", -1)) if isinstance(hb, dict) else -1
        if hb is None or hb_open == 0:
            r6_warn_issues.append(f"{unclosed_entries_count} entry deal(s) have no matching exit row (reconcile against statement)")
    if require_heartbeat and hb is None:
        r6_warn_issues.append("Missing naqex_heartbeat.json — cannot verify live broker connectivity or open_positions")
    elif isinstance(hb, dict) and (str(hb.get("positions_state") or "").upper() == "UNKNOWN" or int(hb.get("open_positions") or 0) < 0):
        r6_warn_issues.append("Heartbeat positions_state is UNKNOWN (offline/unsynced)")
    if require_statement and not stmt_rows:
        r6_warn_issues.append("Missing broker statement reconciliation CSV (statement_csv required for PASS_TO_PAID)")
    elif stmt_rows and statement_unmatched_deals > 0:
        r6_warn_issues.append(f"{statement_unmatched_deals} executed fill(s) not matched in broker statement")
    if require_news_calendar and spec.red_news_guard_sec > 0 and not news_events:
        r6_warn_issues.append("Missing/empty red-news calendar CSV — cannot certify news compliance")
    if len(engines_observed) < max(1, min_distinct_engines):
        r6_warn_issues.append(f"Insufficient fleet coverage: only {len(engines_observed)} engine(s) observed ({', '.join(engines_observed)}), need >= {min_distinct_engines}")
    if trial_calendar_days < max(1, min_trial_calendar_days):
        r6_warn_issues.append(f"Trial span too short: {trial_calendar_days} calendar day(s) < {min_trial_calendar_days}")

    if r6_hard_issues:
        r6_status = "FAIL"
    elif r6_warn_issues:
        r6_status = "WARN"
    else:
        r6_status = "PASS"

    # Fail-closed Gate Decision + Structured R4 -> R3 -> R2 -> R1 triage tagging
    hard_reasons: list[str] = []
    warn_reasons: list[str] = []
    alerts: list[dict[str, Any]] = []

    if r1_status == "FAIL":
        msg = f"Rule 1 Daily Loss breach: {worst_daily_dd_pct:.2f}% >= {spec.hard_daily_loss_pct:.1f}%"
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R1_daily_loss", "severity": "FAIL", "risk_label": "R4", "message": msg})
        r1_risk_label = "R4"
    elif r1_status == "WARN":
        msg = f"Rule 1 Naqex Amber brake touched: {worst_daily_dd_pct:.2f}% >= {spec.amber_daily_brake_pct:.1f}%"
        warn_reasons.append(msg)
        alerts.append({"rule_id": "R1_daily_loss", "severity": "WARN", "risk_label": "R2", "message": msg})
        r1_risk_label = "R2"
    else:
        r1_risk_label = "OK"

    if r2_status == "FAIL":
        r2_labels: list[str] = []
        if orphan_no_sl > 0:
            msg = f"Rule 2 Orphan position without SL detected: orphan_no_sl={orphan_no_sl}"
            hard_reasons.append(msg)
            alerts.append({"rule_id": "R2_max_total_loss", "severity": "FAIL", "risk_label": "R3", "message": msg})
            r2_labels.append("R3")
        if kill_switch:
            msg = "Rule 2 Orchestrator global kill_switch active"
            hard_reasons.append(msg)
            alerts.append({"rule_id": "R2_max_total_loss", "severity": "FAIL", "risk_label": "R4", "message": msg})
            r2_labels.append("R4")
        if max_total_dd_pct >= spec.hard_max_loss_pct:
            msg = f"Rule 2 Max Total Loss breach: {max_total_dd_pct:.2f}% >= {spec.hard_max_loss_pct:.1f}%"
            hard_reasons.append(msg)
            alerts.append({"rule_id": "R2_max_total_loss", "severity": "FAIL", "risk_label": "R4", "message": msg})
            r2_labels.append("R4")
        r2_risk_label = "R4" if "R4" in r2_labels else (r2_labels[0] if r2_labels else "R4")
    elif r2_status == "WARN":
        msg = f"Rule 2 Naqex Red brake touched: {max_total_dd_pct:.2f}% >= {spec.red_total_brake_pct:.1f}%"
        warn_reasons.append(msg)
        alerts.append({"rule_id": "R2_max_total_loss", "severity": "WARN", "risk_label": "R2", "message": msg})
        r2_risk_label = "R2"
    else:
        r2_risk_label = "OK"

    r4_labels: list[str] = []
    if nonzero_swap_count > 0:
        msg = f"Rule 4 Nonzero overnight swap detected on {nonzero_swap_count} deal(s)"
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R4_zero_swap_and_red_news", "severity": "FAIL", "risk_label": "R3", "message": msg})
        r4_labels.append("R3")
    if overnight_hold_count > 0:
        msg = f"Rule 4 Overnight hold across server midnight detected on {overnight_hold_count} trade(s)"
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R4_zero_swap_and_red_news", "severity": "FAIL", "risk_label": "R3", "message": msg})
        r4_labels.append("R3")
    if rollover_blackout_count > 0:
        msg = f"Rule 4 Deal executed inside 21:55-22:15 UTC rollover window ({rollover_blackout_count})"
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R4_zero_swap_and_red_news", "severity": "FAIL", "risk_label": "R3", "message": msg})
        r4_labels.append("R3")
    if news_guard_violations:
        msg = (
            f"Rule 4 Red-News violation: {len(news_guard_violations)} deal(s) inside +-{spec.red_news_guard_sec}s "
            f"(firm window +-{spec.red_news_firm_sec}s: {len(news_firm_violations)})"
        )
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R4_zero_swap_and_red_news", "severity": "FAIL", "risk_label": "R4", "message": msg})
        r4_labels.append("R4")
    r4_risk_label = "R4" if "R4" in r4_labels else ("R3" if r4_labels else "OK")

    if flagged_engines:
        msg = f"Rule 5 Realized slippage > 1.5x backtest M1 budget (or P90 > 2.5x) on: {', '.join(flagged_engines)}"
        hard_reasons.append(msg)
        alerts.append({"rule_id": "R5_engine_slippage_tca", "severity": "FAIL", "risk_label": "R3", "message": msg})
        r5_risk_label = "R3"
    elif unresolved_fill_count > 0 or unmeasured_engines:
        parts = []
        if unresolved_fill_count > 0:
            parts.append(f"unresolved_fill_count={unresolved_fill_count}")
        if unmeasured_engines:
            parts.append(f"unmeasured_engines={','.join(unmeasured_engines)}")
        msg = f"Rule 5 Incomplete TCA telemetry ({'; '.join(parts)}) — cannot mark PASS_TO_PAID"
        warn_reasons.append(msg)
        alerts.append({"rule_id": "R5_engine_slippage_tca", "severity": "WARN", "risk_label": "R3", "message": msg})
        r5_risk_label = "R3"
    else:
        r5_risk_label = "OK"

    if missing_swap_count > 0:
        msg = f"Rule 4 Missing swap_usd column/value on {missing_swap_count} closed deal(s) — verify swap=0 before paid"
        warn_reasons.append(msg)
        alerts.append({"rule_id": "R4_zero_swap_and_red_news", "severity": "WARN", "risk_label": "R3", "message": msg})
        if r4_risk_label == "OK":
            r4_risk_label = "R3"

    if not r3_ok:
        msg = (
            f"Rule 3 Min days incomplete: trading={n_tdays}/{spec.min_trading_days}, "
            f"profitable(>={spec.profitable_day_threshold_pct:.2f}%)={n_pdays}/{spec.min_profitable_days}"
        )
        warn_reasons.append(msg)
        alerts.append({"rule_id": "R3_min_days", "severity": "IN_PROGRESS", "risk_label": "R4", "message": msg})
        r3_risk_label = "R4"
    else:
        r3_risk_label = "OK"

    for r6h in r6_hard_issues:
        hard_reasons.append(f"Rule 6 Reconciliation FAIL: {r6h}")
        alerts.append({"rule_id": "R6_reconciliation_and_coverage", "severity": "FAIL", "risk_label": "R3", "message": r6h})
    for r6w in r6_warn_issues:
        warn_reasons.append(f"Rule 6 Reconciliation incomplete: {r6w}")
        alerts.append({"rule_id": "R6_reconciliation_and_coverage", "severity": "WARN", "risk_label": "R3", "message": r6w})
    r6_risk_label = "R3" if (r6_hard_issues or r6_warn_issues) else "OK"

    # R2 Symbol Concentration diagnostic (non-blocking informational alert if >= 3 entries on same canonical symbol in 1 day)
    symbol_concentration: dict[str, dict[str, Any]] = {}
    for sym_k, pnl_v in sorted(symbol_pnl_usd.items()):
        max_day_e = max((cnt for (dk, sk), cnt in symbol_day_entries.items() if sk == sym_k), default=0)
        symbol_concentration[sym_k] = {
            "net_pnl_usd": round(pnl_v, 2),
            "max_same_day_entries": max_day_e,
        }
        if max_day_e >= 3 and pnl_v < 0.0:
            alerts.append({
                "rule_id": "R2_symbol_concentration",
                "severity": "WARN",
                "risk_label": "R2",
                "message": f"Symbol concentration on {sym_k}: {max_day_e} entries in 1 day (PnL {pnl_v:+.2f} USD) — verify SYMCAP.",
            })

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
        reasons = ["All 6 compliance, reconciliation, coverage & realized TCA rules PASSED with zero violations."]

    net_pnl_usd = round(sum(daily_pnl_usd.values()), 2)
    net_pnl_pct = round((net_pnl_usd / init_bal) * 100.0, 2)
    losing_days = sum(1 for v in daily_pnl_usd.values() if v < 0.0)
    risk_attribution = _build_tracker_risk_attribution(
        alerts=alerts,
        net_pnl_pct=net_pnl_pct,
        losing_days=losing_days,
        total_trading_days=n_tdays,
    )

    return {
        "schema": "naqex-prop-challenge-tracker-v1",
        "generated_utc": ts_now.isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "profile": asdict(spec),
        "status": overall_status,
        "gate_decision": gate_decision,
        "gate_reasons": reasons,
        "alerts": alerts,
        "risk_attribution": risk_attribution,
        "summary": {
            "deals_total": len(deals),
            "entry_deals": entry_count,
            "closed_deals": closed_deals_count,
            "reconciled_closed_trades": reconciled_closed_trades,
            "unclosed_entries": unclosed_entries_count,
            "dryrun_signals": dryrun_signals,
            "rejected_orders": rejected_orders,
            "close_rejects": close_rejects,
            "blocked_orders": blocked_orders,
            "ignored_unknown_events": ignored_unknown_events,
            "trading_days": n_tdays,
            "profitable_days": n_pdays,
            "trial_calendar_days": trial_calendar_days,
            "net_pnl_usd": net_pnl_usd,
            "net_pnl_pct": net_pnl_pct,
            "worst_daily_dd_pct": round(worst_daily_dd_pct, 3),
            "max_total_dd_pct": round(max_total_dd_pct, 3),
            "orphan_no_sl": orphan_no_sl,
            "kill_switch": kill_switch,
            "spread_log_rows": len(spreads),
            "news_events_loaded": len(news_events),
            "statement_rows_loaded": len(stmt_rows),
            "statement_matched_deals": statement_matched_deals,
            "statement_unmatched_deals": statement_unmatched_deals,
            "engines_observed": engines_observed,
            "core7_missing_engines": core7_missing,
            "symbol_concentration": symbol_concentration,
        },
        "rules": {
            "R1_daily_loss": {
                "status": r1_status,
                "risk_label": r1_risk_label,
                "worst_daily_dd_pct": round(worst_daily_dd_pct, 3),
                "amber_buffer_pct": round(spec.amber_daily_brake_pct - worst_daily_dd_pct, 3),
                "hard_buffer_pct": round(spec.hard_daily_loss_pct - worst_daily_dd_pct, 3),
            },
            "R2_max_total_loss": {
                "status": r2_status,
                "risk_label": r2_risk_label,
                "max_total_dd_pct": round(max_total_dd_pct, 3),
                "red_buffer_pct": round(spec.red_total_brake_pct - max_total_dd_pct, 3),
                "hard_buffer_pct": round(spec.hard_max_loss_pct - max_total_dd_pct, 3),
            },
            "R3_min_days": {
                "status": r3_status,
                "risk_label": r3_risk_label,
                "trading_days": n_tdays,
                "required_trading_days": spec.min_trading_days,
                "profitable_days": n_pdays,
                "required_profitable_days": spec.min_profitable_days,
                "profitable_day_threshold_usd": round(prof_thresh_usd, 2),
                "profitable_day_dates": profitable_days,
            },
            "R4_zero_swap_and_red_news": {
                "status": r4_status,
                "risk_label": r4_risk_label,
                "nonzero_swap_count": nonzero_swap_count,
                "missing_swap_count": missing_swap_count,
                "overnight_hold_count": overnight_hold_count,
                "rollover_blackout_count": rollover_blackout_count,
                "valid_pre_flatten_exits": valid_pre_flatten_exits,
                "red_news_guard_violations": len(news_guard_violations),
                "red_news_firm_violations": len(news_firm_violations),
                "violations": news_guard_violations[:20],
            },
            "R5_engine_slippage_tca": {
                "status": r5_status,
                "risk_label": r5_risk_label,
                "flagged_engines": flagged_engines,
                "unresolved_fill_count": unresolved_fill_count,
                "unmeasured_engines": unmeasured_engines,
                "tca_statistical_note": (
                    "14-day Free Trial validates technical execution pipeline and flags gross adverse slippage (>1.5x M1 budget or P90 >2.5x), "
                    "not full tail slippage distribution; keep live TCA monitoring active across first 100+ paid trades."
                ),
                "per_engine": per_engine_tca,
            },
            "R6_reconciliation_and_coverage": {
                "status": r6_status,
                "risk_label": r6_risk_label,
                "closed_deals": closed_deals_count,
                "min_closed_trades": min_closed_trades,
                "reconciled_closed_trades": reconciled_closed_trades,
                "unclosed_entries": unclosed_entries_count,
                "missing_pnl_exits": missing_pnl_exits_count,
                "engines_observed": engines_observed,
                "core7_missing_engines": core7_missing,
                "trial_calendar_days": trial_calendar_days,
                "statement_reconciled": bool(stmt_rows and statement_unmatched_deals == 0),
                "heartbeat_present": hb is not None,
                "hard_issues": r6_hard_issues,
                "warn_issues": r6_warn_issues,
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
    r6 = rules.get("R6_reconciliation_and_coverage") or {}

    ra = payload.get("risk_attribution") or {}
    ra_active = ra.get("active_label", "OK")
    ra_headline = ra.get("headline_vi", "")

    lines = [
        "---",
        "doc_type: prop-compliance-scoreboard",
        f"generated_utc: {payload['generated_utc']}",
        f"profile_id: {prof['profile_id']}",
        f"gate_decision: {payload['gate_decision']}",
        f"risk_triage_active: {ra_active}",
        f"order_send_count: {payload['order_send_count']}",
        "---",
        "",
        f"# Bảng Điểm Tuân Thủ Prop Challenge & Free Trial — `{prof['firm_name']}`",
        "",
        f"- **Thời điểm UTC:** `{payload['generated_utc']}` · **Trạng thái:** `{payload['status']}`",
        f"- **Phán quyết Cổng Chuyển (Fail-Closed Gate):** **`{payload['gate_decision']}`**",
        f"- **Phân Tầng Lỗi 4 Lớp (`R4 -> R3 -> R2 -> R1`):** **`{ra_active}`** — {ra_headline}",
        f"- **Số dư khởi điểm:** `{prof['initial_balance_usd']:,.0f} USD` · **Lãi ròng:** `{summ['net_pnl_usd']:+,.2f} USD` (`{summ['net_pnl_pct']:+.2f}%`) · **Tổng khớp / Đã đóng:** `{summ['deals_total']} / {summ.get('closed_deals', 0)}`",
        "",
        "## 1. Kiểm Toán 6 Quy Tắc Bắt Buộc",
        "",
        "| Quy tắc | Trạng thái | Tầng lỗi | Giá trị thực đo | Ngưỡng cứng / Đệm an toàn |",
        "| --- | :---: | :---: | --- | --- |",
        f"| **R1 — Daily Loss & Amber Brake** | `{r1['status']}` | `{r1.get('risk_label', 'OK')}` | Worst Daily DD `{r1['worst_daily_dd_pct']:.2f}%` | Amber `{prof['amber_daily_brake_pct']:.1f}%` (đệm `{r1['amber_buffer_pct']:+.2f}%`) · Hard `{prof['hard_daily_loss_pct']:.1f}%` |",
        f"| **R2 — Max Total Loss & Red Brake** | `{r2['status']}` | `{r2.get('risk_label', 'OK')}` | Max Total DD `{r2['max_total_dd_pct']:.2f}%` · Orphan `{summ['orphan_no_sl']}` | Red `{prof['red_total_brake_pct']:.1f}%` (đệm `{r2['red_buffer_pct']:+.2f}%`) · Hard `{prof['hard_max_loss_pct']:.1f}%` |",
        f"| **R3 — Số Ngày Giao Dịch / Ngày Lãi** | `{r3['status']}` | `{r3.get('risk_label', 'OK')}` | Trading `{r3['trading_days']}/{r3['required_trading_days']}` · Profitable `{r3['profitable_days']}/{r3['required_profitable_days']}` | Ngưỡng ngày lãi `>= +{prof['profitable_day_threshold_pct']:.2f}%` (`>= {r3['profitable_day_threshold_usd']:,.2f} USD`) |",
        f"| **R4 — Zero Swap & Khóa Tin Đỏ** | `{r4['status']}` | `{r4.get('risk_label', 'OK')}` | Swap!=0: `{r4['nonzero_swap_count']}` · Overnight: `{r4['overnight_hold_count']}` · Pre-flatten hợp lệ: `{r4.get('valid_pre_flatten_exits', 0)}` | Vi phạm Tin Đỏ (`+-{prof['red_news_guard_sec']}s`): `{r4['red_news_guard_violations']}` (Hãng `+-{prof['red_news_firm_sec']}s`: `{r4['red_news_firm_violations']}`) |",
        f"| **R5 — Trượt Giá Thực Tế (`<= 1.5x` M1)** | `{r5['status']}` | `{r5.get('risk_label', 'OK')}` | Động cơ vượt ngưỡng: `{len(r5['flagged_engines'])}` | Danh sách cờ đỏ: `{', '.join(r5['flagged_engines']) if r5['flagged_engines'] else 'NONE'}` |",
        f"| **R6 — Đối Soát Statement & Độ Phủ Đội Hình** | `{r6.get('status', 'PASS')}` | `{r6.get('risk_label', 'OK')}` | Đóng `{r6.get('closed_deals', 0)}/{r6.get('min_closed_trades', 10)}` · EA phủ `{len(r6.get('engines_observed', []))}/7` | Statement `{r6.get('statement_reconciled', False)}` · Heartbeat `{r6.get('heartbeat_present', False)}` |",
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
    ap.add_argument("--statement-csv", type=Path, default=None)
    ap.add_argument("--expected-login", type=int, default=None)
    ap.add_argument("--strict-exit", action="store_true", help="Exit 0 only on PASS_TO_PAID, 2 on EXTEND_SHADOW, 3 on HALT_AND_FIX.")
    ap.add_argument("--out-md", type=Path, default=None)
    ap.add_argument("--out-json", type=Path, default=None)
    args = ap.parse_args(argv)

    payload = evaluate_prop_challenge(
        profile_id=args.profile,
        exec_audit_csv=args.exec_audit_csv,
        spread_log_jsonl=args.spread_log_jsonl,
        news_csv=args.news_csv,
        heartbeat_json=args.heartbeat_json,
        statement_csv=args.statement_csv,
        expected_account_login=args.expected_login,
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
        "closed_deals": payload["summary"].get("closed_deals", 0),
        "out_md": str(args.out_md) if args.out_md else None,
        "out_json": str(args.out_json) if args.out_json else None,
    }, indent=2, ensure_ascii=False))
    if args.strict_exit:
        if payload["gate_decision"] == "PASS_TO_PAID":
            return 0
        if payload["gate_decision"] == "EXTEND_SHADOW":
            return 2
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
