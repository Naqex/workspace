"""Naqex Quant Pod Local Interactive Web Control Room Server (`127.0.0.1:8787`, stdlib-only).

Zero external dependencies, zero external CDNs, strictly localhost-bound (`127.0.0.1`),
100% read-only on workspace state (`ORDER_SEND_COUNT = 0`, Holdout 2025+ SEALED).

Live JSON API endpoints:
  - GET  /                    -> Flat-dark institutional Cockpit UI (`static/index.html`)
  - GET  /static/<asset>      -> Static CSS/JS (`styles.css`, `app.js`) with path-traversal guard
  - GET  /api/health          -> Lightweight readiness check
  - GET  /api/summary         -> Safety seal, registry, pod snapshot, FTMO specs, Red-Team stress curve
  - GET  /api/overview        -> Unified summary + live-telemetry + Black-Swan/Multi-Prop stress snapshot
  - GET  /api/allocations     -> Multi-sleeve equity/underwater curves (4-6+ sleeves), N×N corr matrix & metrics
  - GET  /api/live-telemetry  -> Live Crypto L2 shadow, Maker probe, MT5 demo/spreads, Real-Tick Matrix, Red-News
  - GET  /api/stress          -> Black-Swan VND/USD loss matrix (-30%/-50% CEX, Corr=0.85) & Multi-Prop budget audit
  - GET|POST /api/vnd-calculator -> PROFILE.md-calibrated VND/USD absolute risk, stress & crossover calculator
  - GET  /api/rebalancer      -> Dry-run Sleeve #3B IBKR Macro ETF weights & order tickets (`OrderSend = 0`)
"""

from __future__ import annotations

import argparse
import calendar
import csv
from datetime import datetime, timedelta, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import sys
import threading
import time
from typing import Any
from urllib.parse import parse_qs, urlparse
import urllib.request

import numpy as np

COCKPIT_DIR = Path(__file__).resolve().parent
STATIC_DIR = COCKPIT_DIR / "static"
AI_ENGINES = COCKPIT_DIR.parent
ROOT = AI_ENGINES.parents[1]

if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.ibkr_macro_rebalancer import VALID_MODES, generate_rebalance_plan
from quant_factory.portfolio_allocator import (
    align_sleeves_business_days,
    compute_series_metrics,
    load_external_sleeve_json,
)
from quant_factory.prop_terms_auditor import FIRM_BASELINES, audit_prop_terms_text
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE, compute_prop_own_crossover

ORDER_SEND_COUNT = 0
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

_SLEEVE1_LOCK = threading.Lock()
_SLEEVE1_CACHE: tuple[dict[str, float], dict[str, Any]] | None = None
_STRESS_CACHE_LOCK = threading.Lock()
_STRESS_MD_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_HEROKU_CACHE_LOCK = threading.Lock()
_HEROKU_STATUS_CACHE: tuple[float, dict[str, Any] | None] = (0.0, None)
VN_TZ = timezone(timedelta(hours=7))

PROP_METRIX_PROGRAMS: dict[str, dict[str, Any]] = {
    "ftmo_free_trial_10k": {
        "id": "ftmo_free_trial_10k",
        "label": "FTMO Free Trial 10K (Swing)",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 500.0,
        "min_trading_days": 2,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_10k_p1": {
        "id": "ftmo_swing_10k_p1",
        "label": "FTMO Swing 10K — Phase 1",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 1_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_25k_p1": {
        "id": "ftmo_swing_25k_p1",
        "label": "FTMO Swing 25K — Phase 1",
        "initial_usd": 25_000.0,
        "daily_loss_usd": 1_250.0,
        "max_loss_usd": 2_500.0,
        "profit_target_usd": 2_500.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_50k_p1": {
        "id": "ftmo_swing_50k_p1",
        "label": "FTMO Swing 50K — Phase 1",
        "initial_usd": 50_000.0,
        "daily_loss_usd": 2_500.0,
        "max_loss_usd": 5_000.0,
        "profit_target_usd": 5_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_100k_p1": {
        "id": "ftmo_swing_100k_p1",
        "label": "FTMO Swing 100K — Phase 1",
        "initial_usd": 100_000.0,
        "daily_loss_usd": 5_000.0,
        "max_loss_usd": 10_000.0,
        "profit_target_usd": 10_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_10k_p2": {
        "id": "ftmo_swing_10k_p2",
        "label": "FTMO Swing 10K — Phase 2",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 500.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_funded_10k": {
        "id": "ftmo_funded_10k",
        "label": "FTMO Funded 10K",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": None,
        "min_trading_days": 0,
        "min_profitable_day_pct": 0.0,
    },
    "the5ers_hs_5k_p1": {
        "id": "the5ers_hs_5k_p1",
        "label": "The5ers High Stakes 5K — Step 1",
        "initial_usd": 5_000.0,
        "daily_loss_usd": 250.0,
        "max_loss_usd": 500.0,
        "profit_target_usd": 400.0,
        "min_trading_days": 3,
        "min_profitable_day_pct": 0.5,
    },
    "the5ers_hs_20k_p1": {
        "id": "the5ers_hs_20k_p1",
        "label": "The5ers High Stakes 20K — Step 1",
        "initial_usd": 20_000.0,
        "daily_loss_usd": 1_000.0,
        "max_loss_usd": 2_000.0,
        "profit_target_usd": 1_600.0,
        "min_trading_days": 3,
        "min_profitable_day_pct": 0.5,
    },
}
PROP_PROGRAMS = PROP_METRIX_PROGRAMS

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}


def _safe_read_json(path: Path) -> dict[str, Any] | list[Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _read_jsonl_tail(path: Path, limit: int = 25) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        for ln in lines[-limit:]:
            s = ln.strip()
            if not s:
                continue
            try:
                obj = json.loads(s)
                if isinstance(obj, dict):
                    rows.append(obj)
            except json.JSONDecodeError:
                continue
    except OSError:
        return []
    return rows


def _parse_pod_snapshot_md(path: Path) -> dict[str, Any]:
    """Parse structured KPIs & sleeve table from `.runtime/pod_dashboard_snapshot.md`."""
    if not path.is_file():
        return {"available": False, "path": str(path)}
    txt = path.read_text(encoding="utf-8", errors="replace")
    meta: dict[str, str] = {}
    for key, pat in (
        ("generated_utc", r"\*\*Generated UTC:\*\*\s*`([^`]+)`"),
        ("active_policy", r"\*\*Active Allocation Policy:\*\*\s*`([^`]+)`"),
        ("mt5_heartbeat", r"\*\*MT5 Heartbeat:\*\*\s*`([^`]+)`"),
        ("next_red_news", r"\*\*Next Red-News:\*\*\s*`([^`]+)`"),
    ):
        m = re.search(pat, txt)
        if m:
            meta[key] = m.group(1)

    sleeves: list[dict[str, str]] = []
    in_sec1 = False
    for ln in txt.splitlines():
        if ln.startswith("## 1."):
            in_sec1 = True
            continue
        if in_sec1 and ln.startswith("## "):
            break
        if in_sec1 and ln.startswith("| S"):
            parts = [p.strip() for p in ln.strip("|").split("|")]
            if len(parts) >= 12:
                sleeves.append({
                    "sleeve": parts[0],
                    "strategy": parts[1],
                    "cagr": parts[2],
                    "vol": parts[3],
                    "sharpe": parts[4],
                    "max_dd": parts[5],
                    "cap_wt": parts[6],
                    "risk_wt": parts[7],
                    "traffic_light": parts[8],
                    "cusum_sigma": parts[9],
                    "sprt_state": parts[10],
                    "cone_pct": parts[11],
                })
    return {
        "available": True,
        "meta": meta,
        "sleeves": sleeves,
        "raw_chars": len(txt),
    }


def _format_countdown_vi(delta_sec: float) -> str:
    if abs(delta_sec) <= 300.0:
        return "CẤM ±5m"
    if delta_sec < 0:
        return f"Đã qua {int(abs(delta_sec) // 60)}m"
    mins = int(delta_sec // 60)
    if mins < 60:
        return f"+{mins}m"
    hrs, rem_m = divmod(mins, 60)
    if hrs < 24:
        return f"+{hrs}h {rem_m:02d}m" if rem_m else f"+{hrs}h"
    days, rem_h = divmod(hrs, 24)
    return f"+{days}d {rem_h}h"


def _load_upcoming_red_news(root: Path, limit: int = 10) -> list[dict[str, Any]]:
    csv_path = root / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"
    if not csv_path.is_file():
        return []
    now_ts = datetime.now(timezone.utc).timestamp()
    upcoming: list[dict[str, Any]] = []
    try:
        with csv_path.open("r", encoding="utf-8", newline="") as f:
            for r in csv.DictReader(f):
                ts = float(r.get("utc_ts") or 0.0)
                if ts >= now_ts - 3600.0:
                    dt_utc = datetime.fromtimestamp(ts, timezone.utc)
                    dt_vn = dt_utc.astimezone(VN_TZ)
                    delta_s = ts - now_ts
                    upcoming.append({
                        "utc_ts": int(ts),
                        "utc_iso": dt_utc.strftime("%Y-%m-%d %H:%M UTC"),
                        "vn_iso": dt_vn.strftime("%d/%m %H:%M ICT"),
                        "hours_away": round(delta_s / 3600.0, 1),
                        "countdown_vi": _format_countdown_vi(delta_s),
                        "in_blackout_window": abs(delta_s) <= 300.0,
                        "ccy": str(r.get("ccy", "")).strip(),
                        "event": str(r.get("event", "")).strip(),
                    })
    except Exception:
        return []
    upcoming.sort(key=lambda x: x["utc_ts"])
    return upcoming[:limit]


def _pip_size_for_symbol(symbol: str) -> float:
    s = str(symbol or "").upper()
    if "JPY" in s:
        return 0.01
    if any(tok in s for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "GER40", "DE40", "DAX", "UK100", "FTSE", "XAU", "GOLD", "BTC")):
        return 1.0
    return 0.0001


def _build_prop_risk_attribution(
    *,
    kill_sw: bool,
    orphan_cnt: int,
    age_sec: int | None,
    mt5_running: bool | None,
    source_status: str,
    regime: str,
    init_usd: float,
    daily_lim: float,
    max_lim: float,
    worst_daily_usd: float,
    worst_static_usd: float,
    today_pnl_usd: float,
    total_pnl_usd: float,
    latest_snap: dict[str, Any],
    upcoming_news: list[dict[str, Any]],
) -> dict[str, Any]:
    """Build 4-layer R4 -> R3 -> R2 -> R1 diagnostic attribution (plain Vietnamese, fail-closed)."""
    in_blackout = [ev for ev in upcoming_news if bool(ev.get("in_blackout_window"))]
    soon_news = [ev for ev in upcoming_news if (not ev.get("in_blackout_window")) and 0.0 <= float(ev.get("hours_away", 99.0)) <= 1.0]

    hard_daily = abs(worst_daily_usd) >= daily_lim - 1e-9
    hard_static = abs(worst_static_usd) >= max_lim - 1e-9
    daily_dd_ratio = abs(worst_daily_usd) / max(1.0, daily_lim)
    static_dd_ratio = abs(worst_static_usd) / max(1.0, max_lim)

    # Inspect latest snapshot quotes for spread spikes & open positions for swap/concentration
    quotes = latest_snap.get("quotes") if isinstance(latest_snap.get("quotes"), dict) else {}
    spread_alerts: list[str] = []
    spread_warns: list[str] = []
    for sym, q in quotes.items():
        if not isinstance(q, dict):
            continue
        bid = float(q.get("bid") or 0.0)
        ask = float(q.get("ask") or 0.0)
        if bid > 0.0 and ask >= bid:
            pip_sz = _pip_size_for_symbol(sym)
            sp_pips = (ask - bid) / pip_sz
            is_idx = any(tok in sym.upper() for tok in ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "GER40", "DE40", "DAX", "XAU", "BTC"))
            hi_lim = 6.0 if is_idx else 3.5
            warn_lim = 3.5 if is_idx else 2.2
            if sp_pips >= hi_lim:
                spread_alerts.append(f"{sym} ({sp_pips:.1f} pip)")
            elif sp_pips >= warn_lim:
                spread_warns.append(f"{sym} ({sp_pips:.1f} pip)")

    open_pos = latest_snap.get("naqex_positions") if isinstance(latest_snap.get("naqex_positions"), list) else []
    sym_counts: dict[str, int] = {}
    nonzero_swap_syms: list[str] = []
    for p in open_pos:
        if not isinstance(p, dict):
            continue
        sym_k = str(p.get("symbol") or "").upper().split(".")[0]
        if sym_k:
            sym_counts[sym_k] = sym_counts.get(sym_k, 0) + 1
        if abs(float(p.get("swap") or 0.0)) > 1e-6:
            nonzero_swap_syms.append(sym_k or "POS")
    max_sym_cnt = max(sym_counts.values(), default=0)
    top_sym = max(sym_counts, key=sym_counts.get) if sym_counts else ""

    # --- R4: Luật quỹ, Tin đỏ & Kill-Switch (kiểm đầu tiên) ---
    r4_alerts: list[str] = []
    r4_warns: list[str] = []
    if kill_sw:
        r4_alerts.append("Kill-Switch đang BẬT")
    if hard_daily:
        r4_alerts.append(f"Chạm ngưỡng lỗ ngày (-{daily_lim:,.0f} USD)")
    if hard_static:
        r4_alerts.append(f"Chạm ngưỡng lỗ tổng (-{max_lim:,.0f} USD)")
    if in_blackout:
        ev0 = in_blackout[0]
        r4_alerts.append(f"Đang trong vùng khóa tin đỏ ±5 phút ({ev0.get('ccy')} {ev0.get('event')})")
    elif soon_news:
        ev0 = soon_news[0]
        r4_warns.append(f"Sắp có tin đỏ trong < 60 phút ({ev0.get('ccy')} {ev0.get('event')} · {ev0.get('countdown_vi')})")

    if r4_alerts:
        r4 = {"code": "R4", "title": "Luật quỹ & Tin đỏ", "status": "ALERT", "detail": "; ".join(r4_alerts)}
    elif r4_warns:
        r4 = {"code": "R4", "title": "Luật quỹ & Tin đỏ", "status": "WARN", "detail": "; ".join(r4_warns)}
    else:
        r4 = {"code": "R4", "title": "Luật quỹ & Tin đỏ", "status": "OK", "detail": "An toàn — không vi phạm luật quỹ, ngoài vùng tin đỏ, Kill-Switch TẮT."}

    # --- R3: Khớp lệnh, Thiếu SL, Heartbeat & Spread ---
    r3_alerts: list[str] = []
    r3_warns: list[str] = []
    if orphan_cnt > 0:
        r3_alerts.append(f"Có {orphan_cnt} lệnh mở thiếu Stop Loss")
    if mt5_running is False:
        r3_alerts.append("Tiến trình MT5 trên node đang DỪNG")
    if age_sec is not None and age_sec > 180:
        r3_alerts.append(f"Heartbeat trễ {age_sec} giây (> 180s)")
    elif age_sec is not None and age_sec > 90:
        r3_warns.append(f"Heartbeat hơi chậm ({age_sec} giây)")
    if nonzero_swap_syms:
        r3_alerts.append(f"Phát hiện phí qua đêm swap != 0 ({', '.join(nonzero_swap_syms[:3])})")
    if spread_alerts:
        r3_alerts.append(f"Spread giãn mạnh: {', '.join(spread_alerts[:3])}")
    elif spread_warns:
        r3_warns.append(f"Spread hơi cao: {', '.join(spread_warns[:3])}")

    if r3_alerts:
        r3 = {"code": "R3", "title": "Khớp lệnh & Máy chủ", "status": "ALERT", "detail": "; ".join(r3_alerts)}
    elif r3_warns:
        r3 = {"code": "R3", "title": "Khớp lệnh & Máy chủ", "status": "WARN", "detail": "; ".join(r3_warns)}
    elif source_status == "PENDING":
        r3 = {"code": "R3", "title": "Khớp lệnh & Máy chủ", "status": "OK", "detail": "Chế độ chờ (chưa có dữ liệu live); chưa ghi nhận lỗi máy chủ hay thiếu SL."}
    else:
        r3 = {"code": "R3", "title": "Khớp lệnh & Máy chủ", "status": "OK", "detail": "Sạch — 0 lệnh thiếu SL, heartbeat ổn định, spread & swap trong ngưỡng."}

    # --- R2: Dồn lệnh cùng mã (SYMCAP) & Phanh danh mục ---
    r2_alerts: list[str] = []
    r2_warns: list[str] = []
    reg_u = str(regime or "NORMAL").upper()
    if daily_dd_ratio >= 0.70:
        r2_alerts.append(f"Lỗ ngày đạt {daily_dd_ratio * 100.0:.0f}% ngưỡng quỹ (chạm phanh Amber)")
    if static_dd_ratio >= 0.70:
        r2_alerts.append(f"Lỗ tổng đạt {static_dd_ratio * 100.0:.0f}% ngưỡng quỹ (chạm phanh Red)")
    if reg_u in ("RED", "HALT", "FLATTEN"):
        r2_alerts.append(f"Chế độ phanh danh mục đang là {reg_u}")
    elif reg_u == "AMBER":
        r2_warns.append("Chế độ phanh danh mục đang ở mức AMBER (giảm nửa cỡ lệnh)")
    if max_sym_cnt >= 3:
        r2_alerts.append(f"Dồn {max_sym_cnt} lệnh mở cùng mã {top_sym} (cần kiểm SYMCAP)")
    elif max_sym_cnt == 2:
        r2_warns.append(f"Đang mở song song 2 lệnh cùng mã {top_sym} (theo dõi SYMCAP)")

    if r2_alerts:
        r2 = {"code": "R2", "title": "Dồn lệnh & Danh mục", "status": "ALERT", "detail": "; ".join(r2_alerts)}
    elif r2_warns:
        r2 = {"code": "R2", "title": "Dồn lệnh & Danh mục", "status": "WARN", "detail": "; ".join(r2_warns)}
    else:
        r2 = {"code": "R2", "title": "Dồn lệnh & Danh mục", "status": "OK", "detail": "Cân bằng — không dồn lệnh cùng mã, chưa chạm phanh Amber/Red danh mục."}

    # --- R1: Lợi thế thật của chiến lược (chỉ soi khi R4/R3/R2 không ALERT) ---
    upstream_alert = any(layer["status"] == "ALERT" for layer in (r4, r3, r2))
    tot_dd_pct = -100.0 * total_pnl_usd / max(1.0, init_usd) if total_pnl_usd < 0.0 else 0.0
    day_dd_pct = -100.0 * today_pnl_usd / max(1.0, init_usd) if today_pnl_usd < 0.0 else 0.0
    if upstream_alert:
        r1 = {
            "code": "R1",
            "title": "Lợi thế chiến lược",
            "status": "OK",
            "detail": "Tạm giữ nguyên chiến lược — ưu tiên xử lý cảnh báo ở tầng R4/R3/R2 trước.",
        }
    elif tot_dd_pct >= 2.5:
        r1 = {
            "code": "R1",
            "title": "Lợi thế chiến lược",
            "status": "ALERT",
            "detail": f"Rút vốn thực tế -{tot_dd_pct:.2f}% khi R4/R3/R2 đều sạch — cần đối soát drift / CUSUM.",
        }
    elif tot_dd_pct >= 1.5 or day_dd_pct >= 1.5:
        r1 = {
            "code": "R1",
            "title": "Lợi thế chiến lược",
            "status": "WARN",
            "detail": f"Biến động âm nhẹ (tổng -{tot_dd_pct:.2f}%, hôm nay -{day_dd_pct:.2f}%) — trong biên độ bình thường.",
        }
    else:
        r1 = {
            "code": "R1",
            "title": "Lợi thế chiến lược",
            "status": "OK",
            "detail": "Bình thường — chưa ghi nhận suy giảm lợi thế chiến lược.",
        }

    layers = {"R4": r4, "R3": r3, "R2": r2, "R1": r1}
    order = ["R4", "R3", "R2", "R1"]
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
        headline_vi = "Tất cả 4 tầng R4 → R3 → R2 → R1 đều XANH — tài khoản vận hành sạch."
    else:
        act_obj = layers[active_label]
        sev_vi = "CẢNH BÁO ĐỎ" if act_obj["status"] == "ALERT" else "LƯU Ý"
        headline_vi = f"{sev_vi} tại {active_label} ({act_obj['title']}): {act_obj['detail']}"

    return {
        "active_label": active_label,
        "check_order": order,
        "headline_vi": headline_vi,
        "layers": layers,
    }


def _compute_positions_mae_mfe(snapshots: list[dict[str, Any]]) -> dict[int, dict[str, Any]]:
    """Compute observed MAE/MFE (pips & USD) per ticket from real telemetry snapshots (never fabricated)."""
    stats: dict[int, dict[str, Any]] = {}
    for snap in snapshots:
        quotes = snap.get("quotes") if isinstance(snap.get("quotes"), dict) else {}
        cap_utc = str(snap.get("captured_utc") or "")
        for p in snap.get("naqex_positions") or []:
            if not isinstance(p, dict) or p.get("ticket") is None:
                continue
            tid = int(p["ticket"])
            sym = str(p.get("symbol") or "")
            side = 1 if str(p.get("type", "")).upper() == "BUY" else -1
            ep = float(p.get("price_open") or 0.0)
            pnl = float(p.get("profit") or 0.0)
            q = quotes.get(sym) if isinstance(quotes.get(sym), dict) else None
            pip_sz = _pip_size_for_symbol(sym)
            pips: float | None = None
            if q and ep > 0.0:
                mkt_px = float(q.get("bid") or 0.0) if side == 1 else float(q.get("ask") or 0.0)
                if mkt_px > 0.0:
                    pips = (mkt_px - ep) * side / pip_sz

            rec = stats.get(tid)
            if rec is None:
                rec = {
                    "samples": 0,
                    "mae_usd": pnl,
                    "mfe_usd": pnl,
                    "mae_pips": pips,
                    "mfe_pips": pips,
                    "first_seen_utc": cap_utc,
                    "last_seen_utc": cap_utc,
                }
                stats[tid] = rec
            rec["samples"] += 1
            rec["last_seen_utc"] = cap_utc
            if pnl < rec["mae_usd"]:
                rec["mae_usd"] = pnl
            if pnl > rec["mfe_usd"]:
                rec["mfe_usd"] = pnl
            if pips is not None:
                if rec["mae_pips"] is None or pips < rec["mae_pips"]:
                    rec["mae_pips"] = pips
                if rec["mfe_pips"] is None or pips > rec["mfe_pips"]:
                    rec["mfe_pips"] = pips
    for rec in stats.values():
        rec["mae_usd"] = round(float(rec["mae_usd"]), 2)
        rec["mfe_usd"] = round(float(rec["mfe_usd"]), 2)
        if rec["mae_pips"] is not None:
            rec["mae_pips"] = round(float(rec["mae_pips"]), 1)
        if rec["mfe_pips"] is not None:
            rec["mfe_pips"] = round(float(rec["mfe_pips"]), 1)
    return stats


def _fetch_heroku_node1_cached(root: Path, *, ttl_sec: float = 8.0) -> dict[str, Any] | None:
    """Read live NAQEX_NODE1 telemetry from Heroku EU (read-only, cached, never leaks tokens)."""
    global _HEROKU_STATUS_CACHE
    cfg_path = root / ".runtime/ops-cloud/heroku_connection_local.json"
    if not cfg_path.is_file():
        return None
    now = time.monotonic()
    with _HEROKU_CACHE_LOCK:
        ts_c, val_c = _HEROKU_STATUS_CACHE
        if (now - ts_c) < ttl_sec:
            return val_c

    cfg = _safe_read_json(cfg_path)
    if not isinstance(cfg, dict):
        return None
    web_url = str(cfg.get("web_url") or "").rstrip("/")
    dash_url = str(cfg.get("mobile_dashboard_url") or "")
    if not web_url or "?" not in dash_url:
        return None
    q_part = dash_url.split("?", 1)[1]
    result: dict[str, Any] | None = None
    try:
        req = urllib.request.Request(f"{web_url}/api/status?{q_part}", headers={"User-Agent": "Naqex-Cockpit/1.0"})
        with urllib.request.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        nodes = data.get("nodes") or []
        preferred = next((n for n in nodes if n.get("account_label") == "NAQEX_NODE1"), None) or (nodes[0] if nodes else None)
        if isinstance(preferred, dict):
            result = {
                "source": "HEROKU_EU_LIVE",
                "account_label": preferred.get("account_label"),
                "status": preferred.get("status"),
                "age_sec": preferred.get("age_sec"),
                "mt5_running": preferred.get("mt5_running"),
                "balance": preferred.get("balance"),
                "equity": preferred.get("equity"),
                "daily_dd_pct": preferred.get("daily_dd_pct"),
                "static_dd_pct": preferred.get("static_dd_pct"),
                "open_positions": preferred.get("open_positions"),
                "orphan_no_sl": preferred.get("orphan_no_sl"),
                "regime": preferred.get("regime"),
                "kill_switch": preferred.get("kill_switch"),
                "last_seen_utc": preferred.get("last_seen_utc"),
            }
    except Exception:
        result = None

    with _HEROKU_CACHE_LOCK:
        _HEROKU_STATUS_CACHE = (now, result)
    return result


def build_prop_metrix_payload(
    root: Path = ROOT,
    *,
    program: str = "ftmo_free_trial_10k",
    allow_cloud_fetch: bool = True,
) -> dict[str, Any]:
    """Build FTMO-MetriX-style Prop Account buffers, rule checklist, MAE/MFE & daily calendar (OrderSend=0)."""
    prog = PROP_METRIX_PROGRAMS.get(program, PROP_METRIX_PROGRAMS["ftmo_free_trial_10k"])
    init_usd = float(prog["initial_usd"])
    daily_lim = float(prog["daily_loss_usd"])
    max_lim = float(prog["max_loss_usd"])
    target_usd = prog["profit_target_usd"]
    min_days = int(prog["min_trading_days"])

    live_dir = root / ".runtime/live-overnight"
    spread_rows = _read_jsonl_tail(live_dir / "mt5_live_spread_log.jsonl", limit=1500)
    mae_mfe_map = _compute_positions_mae_mfe(spread_rows)

    # Read local heartbeat fallback
    local_hb: dict[str, Any] = {}
    for cand in (
        root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_heartbeat.json",
        live_dir / "naqex_heartbeat.json",
    ):
        obj = _safe_read_json(cand)
        if isinstance(obj, dict) and float(obj.get("balance") or 0.0) > 0.0:
            local_hb = obj
            break

    cloud_node = _fetch_heroku_node1_cached(root) if (allow_cloud_fetch and root == ROOT) else None

    # Resolve live account numbers (Heroku EU live node1 preferred when healthy; local snapshots fallback)
    latest_snap = spread_rows[-1] if spread_rows else {}
    snap_acct = latest_snap.get("account") if isinstance(latest_snap.get("account"), dict) else {}
    if cloud_node and cloud_node.get("equity") is not None:
        source_label = f"{cloud_node.get('account_label') or 'NAQEX_NODE1'} · HEROKU LIVE"
        source_status = str(cloud_node.get("status") or "OK")
        balance = float(cloud_node["balance"]) if cloud_node.get("balance") is not None else init_usd
        equity = float(cloud_node["equity"])
        open_pos_cnt = int(cloud_node.get("open_positions") or 0)
        orphan_cnt = int(cloud_node.get("orphan_no_sl") or 0)
        regime = str(cloud_node.get("regime") or "NORMAL")
        kill_sw = bool(cloud_node.get("kill_switch") or False)
        age_sec = cloud_node.get("age_sec")
        daily_dd_pct_hb = float(cloud_node.get("daily_dd_pct") or 0.0)
    elif snap_acct and snap_acct.get("equity") is not None:
        source_label = "LOCAL MT5 TELEMETRY LOG"
        source_status = "CACHED"
        balance = float(snap_acct["balance"]) if snap_acct.get("balance") is not None else init_usd
        equity = float(snap_acct["equity"])
        open_pos_cnt = int(latest_snap.get("naqex_positions_count") or 0)
        orphan_cnt = int(latest_snap.get("orphan_no_sl") or 0)
        hb_s = latest_snap.get("heartbeat") if isinstance(latest_snap.get("heartbeat"), dict) else {}
        regime = str(hb_s.get("regime") or local_hb.get("regime") or "NORMAL")
        kill_sw = bool(hb_s.get("kill_switch") or local_hb.get("kill_switch") or False)
        age_sec = None
        daily_dd_pct_hb = float(local_hb.get("daily_dd_pct") or 0.0)
    elif local_hb:
        source_label = "LOCAL HEARTBEAT JSON"
        source_status = "CACHED"
        balance = float(local_hb["balance"]) if local_hb.get("balance") is not None else init_usd
        equity = float(local_hb["equity"]) if local_hb.get("equity") is not None else balance
        open_pos_cnt = int(local_hb.get("open_positions") or 0)
        orphan_cnt = int(local_hb.get("orphan_no_sl") or 0)
        regime = str(local_hb.get("regime") or "NORMAL")
        kill_sw = bool(local_hb.get("kill_switch") or False)
        age_sec = None
        daily_dd_pct_hb = float(local_hb.get("daily_dd_pct") or 0.0)
    else:
        source_label = "STANDBY (NO TELEMETRY)"
        source_status = "PENDING"
        balance = init_usd
        equity = init_usd
        open_pos_cnt = 0
        orphan_cnt = 0
        regime = "NORMAL"
        kill_sw = False
        age_sec = None
        daily_dd_pct_hb = 0.0

    # Aggregate daily equity & calendar cells from real telemetry snapshots
    daily_map: dict[str, dict[str, Any]] = {}
    prev_day_end_eq: float | None = None
    for s in spread_rows:
        utc_s = str(s.get("captured_utc") or "")
        if len(utc_s) < 10:
            continue
        dk = utc_s[:10]
        ac = s.get("account") if isinstance(s.get("account"), dict) else {}
        eq_s = ac.get("equity")
        bal_s = ac.get("balance")
        if eq_s is None:
            continue
        eq_f = float(eq_s)
        bal_f = float(bal_s) if bal_s is not None else eq_f
        pos_c = int(s.get("naqex_positions_count") or 0)
        cur = daily_map.get(dk)
        if cur is None:
            # Anchor start-of-day to prior day's EOD equity (or initial capital on day 1 when already closed flat)
            if pos_c == 0 and abs(eq_f - bal_f) <= 1e-6:
                if prev_day_end_eq is not None:
                    start_anchor = prev_day_end_eq
                elif len(daily_map) == 0 and abs(eq_f - init_usd) < init_usd * 0.5:
                    start_anchor = init_usd
                else:
                    start_anchor = bal_f
            else:
                start_anchor = bal_f if abs(bal_f - init_usd) < init_usd * 0.5 else eq_f
            daily_map[dk] = {
                "day": dk,
                "start_eq": start_anchor,
                "end_eq": eq_f,
                "min_eq": eq_f,
                "max_eq": eq_f,
                "max_open_pos": pos_c,
                "samples": 1,
                "has_trade": pos_c > 0 or abs(eq_f - bal_f) > 1e-6 or abs(eq_f - start_anchor) > 1e-6,
            }
        else:
            cur["end_eq"] = eq_f
            cur["min_eq"] = min(cur["min_eq"], eq_f)
            cur["max_eq"] = max(cur["max_eq"], eq_f)
            cur["max_open_pos"] = max(cur["max_open_pos"], pos_c)
            cur["samples"] += 1
            if pos_c > 0 or abs(eq_f - bal_f) > 1e-6 or abs(eq_f - cur["start_eq"]) > 1e-6 or abs(bal_f - cur["start_eq"]) > 1e-6:
                cur["has_trade"] = True
        prev_day_end_eq = eq_f

    today_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    if source_status != "PENDING":
        cur_today = daily_map.get(today_utc)
        if cur_today is None:
            daily_map[today_utc] = {
                "day": today_utc,
                "start_eq": init_usd if len(daily_map) == 0 else balance,
                "end_eq": equity,
                "min_eq": equity,
                "max_eq": equity,
                "max_open_pos": open_pos_cnt,
                "samples": 1,
                "has_trade": open_pos_cnt > 0 or abs(equity - init_usd) > 1e-6,
            }
        else:
            cur_today["end_eq"] = equity
            cur_today["min_eq"] = min(cur_today["min_eq"], equity)
            cur_today["max_eq"] = max(cur_today["max_eq"], equity)
            cur_today["max_open_pos"] = max(cur_today["max_open_pos"], open_pos_cnt)
            if open_pos_cnt > 0:
                cur_today["has_trade"] = True

    # Day anchor for FTMO daily buffer = start-of-day baseline (initial on day 1, or previous day end)
    sorted_days = sorted(daily_map.keys())
    if today_utc in daily_map:
        day_anchor_eq = float(daily_map[today_utc]["start_eq"])
    elif local_hb.get("day_anchor_eq"):
        day_anchor_eq = float(local_hb["day_anchor_eq"])
    else:
        day_anchor_eq = init_usd

    today_pnl_usd = round(equity - day_anchor_eq, 2)
    total_pnl_usd = round(equity - init_usd, 2)
    permitted_daily_loss_usd = round(max(0.0, daily_lim + today_pnl_usd), 2)
    permitted_max_loss_usd = round(max(0.0, max_lim + total_pnl_usd), 2)

    # Worst observed daily & static DD in USD
    obs_today_min = float(daily_map[today_utc]["min_eq"]) if today_utc in daily_map else equity
    worst_daily_usd = round(min(0.0, obs_today_min - day_anchor_eq, -(daily_dd_pct_hb / 100.0) * init_usd), 2)
    obs_all_min = min((float(v["min_eq"]) for v in daily_map.values()), default=equity)
    worst_static_usd = round(min(0.0, obs_all_min - init_usd, total_pnl_usd), 2)

    days_traded = sum(1 for v in daily_map.values() if v["has_trade"])
    min_prof_pct = float(prog.get("min_profitable_day_pct") or 0.0)
    min_prof_usd = round(init_usd * min_prof_pct / 100.0, 2)
    profitable_days_count = 0
    for v in daily_map.values():
        if not v["has_trade"]:
            continue
        dpnl = round(float(v["end_eq"]) - float(v["start_eq"]), 2)
        if min_prof_pct > 0.0:
            if dpnl >= min_prof_usd - 1e-9:
                profitable_days_count += 1
        elif dpnl > 0.0:
            profitable_days_count += 1

    target_progress_pct = round(max(0.0, min(100.0, 100.0 * total_pnl_usd / float(target_usd))), 1) if target_usd else None

    if min_prof_pct > 0.0:
        pct_vi = f"{min_prof_pct:g}".replace(".", ",")
        min_days_rule = {
            "id": "min_trading_days",
            "label": f"Ngày lãi tối thiểu >= +{pct_vi}% ({min_days} ngày)",
            "value_text": f"{profitable_days_count} / {min_days} ngày lãi (GD: {days_traded} ngày · >= +{min_prof_usd:,.2f} USD)",
            "status": "PASS" if profitable_days_count >= min_days else "PENDING",
            "profitable_days_count": profitable_days_count,
            "min_profitable_day_usd": min_prof_usd,
            "days_traded": days_traded,
        }
    else:
        min_days_rule = {
            "id": "min_trading_days",
            "label": f"Ngày giao dịch tối thiểu ({min_days} ngày)" if min_days > 0 else "Ngày giao dịch tối thiểu (Không yêu cầu)",
            "value_text": f"{days_traded} / {min_days} ngày" if min_days > 0 else f"{days_traded} ngày",
            "status": "PASS" if days_traded >= min_days else "PENDING",
            "profitable_days_count": profitable_days_count,
            "min_profitable_day_usd": min_prof_usd,
            "days_traded": days_traded,
        }

    rules = [
        min_days_rule,
        {
            "id": "max_daily_loss",
            "label": f"Mức lỗ tối đa hàng ngày (-{daily_lim:,.0f} USD)",
            "value_text": f"{worst_daily_usd:+,.2f} USD ({abs(worst_daily_usd) / max(1.0, init_usd) * 100.0:.2f}%)",
            "status": "BREACH" if abs(worst_daily_usd) >= daily_lim else "PASS",
        },
        {
            "id": "max_total_loss",
            "label": f"Mức lỗ tối đa tổng (-{max_lim:,.0f} USD)",
            "value_text": f"{worst_static_usd:+,.2f} USD ({abs(worst_static_usd) / max(1.0, init_usd) * 100.0:.2f}%)",
            "status": "BREACH" if abs(worst_static_usd) >= max_lim else "PASS",
        },
        {
            "id": "profit_target",
            "label": f"Mục tiêu lợi nhuận (+{target_usd:,.0f} USD)" if target_usd else "Mục tiêu lợi nhuận (Tài khoản Funded)",
            "value_text": (
                f"{total_pnl_usd:+,.2f} USD ({total_pnl_usd / max(1.0, init_usd) * 100.0:+.2f}%)"
                if target_usd else f"{total_pnl_usd:+,.2f} USD"
            ),
            "status": (
                "FUNDED" if target_usd is None
                else ("PASS" if total_pnl_usd >= float(target_usd) else "IN_PROGRESS")
            ),
            "progress_pct": target_progress_pct,
        },
        {
            "id": "safety_guard",
            "label": "Bảo vệ cứng SL & Kill-Switch",
            "value_text": f"Thiếu SL: {orphan_cnt} · Chế độ: {regime}",
            "status": "PASS" if (orphan_cnt == 0 and not kill_sw) else "BREACH",
        },
    ]

    upcoming_news = _load_upcoming_red_news(root, limit=6)
    risk_attribution = _build_prop_risk_attribution(
        kill_sw=kill_sw,
        orphan_cnt=orphan_cnt,
        age_sec=age_sec,
        mt5_running=cloud_node.get("mt5_running") if cloud_node else None,
        source_status=source_status,
        regime=regime,
        init_usd=init_usd,
        daily_lim=daily_lim,
        max_lim=max_lim,
        worst_daily_usd=worst_daily_usd,
        worst_static_usd=worst_static_usd,
        today_pnl_usd=today_pnl_usd,
        total_pnl_usd=total_pnl_usd,
        latest_snap=latest_snap,
        upcoming_news=upcoming_news,
    )

    # Build active month calendar matrix (Mon..Sun cells)
    ref_day = sorted_days[-1] if sorted_days else today_utc
    yr_i, mo_i = int(ref_day[:4]), int(ref_day[5:7])
    first_wd, n_days_mo = calendar.monthrange(yr_i, mo_i)
    cal_cells: list[dict[str, Any]] = []
    for _ in range(first_wd):
        cal_cells.append({"empty": True})
    for dnum in range(1, n_days_mo + 1):
        dk = f"{yr_i:04d}-{mo_i:02d}-{dnum:02d}"
        info = daily_map.get(dk)
        if info and info["has_trade"]:
            dpnl = round(float(info["end_eq"]) - float(info["start_eq"]), 2)
            state_lbl = "LIVE_OPEN" if (dk == today_utc and open_pos_cnt > 0) else "RECORDED"
            cal_cells.append({
                "empty": False,
                "day_num": dnum,
                "day": dk,
                "has_trade": True,
                "pnl_usd": dpnl,
                "max_open_pos": info["max_open_pos"],
                "state": state_lbl,
            })
        else:
            cal_cells.append({"empty": False, "day_num": dnum, "day": dk, "has_trade": False, "pnl_usd": None, "state": "IDLE"})

    return {
        "schema": "naqex-prop-metrix-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "program": prog,
        "available_programs": [{"id": k, "label": v["label"]} for k, v in PROP_METRIX_PROGRAMS.items()],
        "source": {
            "label": source_label,
            "status": source_status,
            "age_sec": age_sec,
            "mt5_running": cloud_node.get("mt5_running") if cloud_node else None,
        },
        "account": {
            "initial_usd": init_usd,
            "balance_usd": round(balance, 2),
            "equity_usd": round(equity, 2),
            "day_anchor_usd": round(day_anchor_eq, 2),
            "today_pnl_usd": today_pnl_usd,
            "today_pnl_pct": round(100.0 * today_pnl_usd / max(1.0, init_usd), 2),
            "total_pnl_usd": total_pnl_usd,
            "total_pnl_pct": round(100.0 * total_pnl_usd / max(1.0, init_usd), 2),
            "open_positions": open_pos_cnt,
            "orphan_no_sl": orphan_cnt,
            "regime": regime,
            "days_traded": days_traded,
            "profitable_days_count": profitable_days_count,
            "min_profitable_day_usd": min_prof_usd,
        },
        "profitable_days_count": profitable_days_count,
        "min_profitable_day_usd": min_prof_usd,
        "buffers": {
            "permitted_daily_loss_usd": permitted_daily_loss_usd,
            "daily_limit_usd": daily_lim,
            "permitted_max_loss_usd": permitted_max_loss_usd,
            "max_limit_usd": max_lim,
            "today_pnl_usd": today_pnl_usd,
        },
        "rules": rules,
        "risk_attribution": risk_attribution,
        "calendar": {
            "year": yr_i,
            "month": mo_i,
            "month_label": f"Tháng {mo_i:02d}/{yr_i}",
            "cells": cal_cells,
        },
        "positions_mae_mfe": {str(k): v for k, v in mae_mfe_map.items()},
    }


def _get_sleeve1_cached(root: Path) -> tuple[dict[str, float], dict[str, Any]] | None:
    global _SLEEVE1_CACHE
    if root != ROOT:
        return None
    with _SLEEVE1_LOCK:
        if _SLEEVE1_CACHE is not None:
            return _SLEEVE1_CACHE
        try:
            from quant_factory.portfolio_allocator import load_sleeve1_dev_daily_returns
            _SLEEVE1_CACHE = load_sleeve1_dev_daily_returns()
            return _SLEEVE1_CACHE
        except Exception:
            return None


def _downsample_series(dates: list[str], values_map: dict[str, list[float]], max_points: int = 260) -> tuple[list[str], dict[str, list[float]]]:
    n = len(dates)
    if n <= max_points:
        return dates, {k: [round(v, 4) for v in arr] for k, arr in values_map.items()}
    step = max(1, n // max_points)
    idxs = list(range(0, n, step))
    if idxs[-1] != n - 1:
        idxs.append(n - 1)
    ds_dates = [dates[i] for i in idxs]
    ds_vals = {k: [round(arr[i], 4) for i in idxs] for k, arr in values_map.items()}
    return ds_dates, ds_vals


def _interpolate_red_team_curve(curve: list[dict[str, Any]], mult: float) -> dict[str, float]:
    """Piecewise-linear interpolation on real Red-Team cost stress grid (1.0x..3.0x), extrapolating gently below 1.0x."""
    if not curve:
        return {"cost_mult": mult, "ann_pct": 0.0, "peak_dd_pct": 0.0, "calmar": 0.0, "net_usd": 0.0}
    pts = sorted(curve, key=lambda x: float(x["cost_mult"]))
    xs = [float(p["cost_mult"]) for p in pts]
    m = max(0.5, min(3.5, float(mult)))

    if m <= xs[0]:
        if len(xs) >= 2:
            t = (m - xs[0]) / max(1e-9, xs[1] - xs[0])
            p0, p1 = pts[0], pts[1]
            ann = float(p0["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = max(1.0, float(p0["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"])))
            net = float(p0["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {"cost_mult": round(m, 2), "ann_pct": round(ann, 2), "peak_dd_pct": round(dd, 2), "calmar": round(ann / dd, 2), "net_usd": round(net, 2)}
        p0 = pts[0]
        return {"cost_mult": round(m, 2), "ann_pct": float(p0["ann_pct"]), "peak_dd_pct": float(p0["peak_dd_pct"]), "calmar": float(p0["calmar"]), "net_usd": float(p0["net_usd"])}

    if m >= xs[-1]:
        if len(xs) >= 2:
            p0, p1 = pts[-2], pts[-1]
            t = (m - xs[-1]) / max(1e-9, xs[-1] - xs[-2])
            ann = float(p1["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = max(1.0, float(p1["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"])))
            net = float(p1["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {"cost_mult": round(m, 2), "ann_pct": round(ann, 2), "peak_dd_pct": round(dd, 2), "calmar": round(ann / dd, 2), "net_usd": round(net, 2)}
        p1 = pts[-1]
        return {"cost_mult": round(m, 2), "ann_pct": float(p1["ann_pct"]), "peak_dd_pct": float(p1["peak_dd_pct"]), "calmar": float(p1["calmar"]), "net_usd": float(p1["net_usd"])}

    for i in range(len(xs) - 1):
        if xs[i] <= m <= xs[i + 1]:
            t = (m - xs[i]) / max(1e-9, xs[i + 1] - xs[i])
            p0, p1 = pts[i], pts[i + 1]
            ann = float(p0["ann_pct"]) + t * (float(p1["ann_pct"]) - float(p0["ann_pct"]))
            dd = float(p0["peak_dd_pct"]) + t * (float(p1["peak_dd_pct"]) - float(p0["peak_dd_pct"]))
            net = float(p0["net_usd"]) + t * (float(p1["net_usd"]) - float(p0["net_usd"]))
            return {
                "cost_mult": round(m, 2),
                "ann_pct": round(ann, 2),
                "peak_dd_pct": round(dd, 2),
                "calmar": round(ann / max(0.01, dd), 2),
                "net_usd": round(net, 2),
            }
    return pts[0]


def build_summary_payload(root: Path = ROOT) -> dict[str, Any]:
    reg = _safe_read_json(root / "planning/research/PORTFOLIO-REGISTRY.json") or {}
    red_team = _safe_read_json(root / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json") or {}
    ftmo_live = _safe_read_json(root / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json")
    pod_snap = _parse_pod_snapshot_md(root / ".runtime/pod_dashboard_snapshot.md")
    holdout_lock = reg.get("holdout_lock", {})

    red_team_compact = {}
    if isinstance(red_team, dict) and red_team:
        t1 = red_team.get("test1_cost_stress", {})
        red_team_compact = {
            "available": True,
            "generated_utc": red_team.get("generated_utc"),
            "dev_window": red_team.get("dev_window"),
            "baseline": red_team.get("baseline", {}),
            "portfolio_curve": t1.get("portfolio_curve", {}),
            "portfolio_breakeven": t1.get("portfolio_breakeven", {}),
            "per_engine": t1.get("per_engine", []),
            "engines_below_2x_breakeven": t1.get("engines_below_2x_breakeven", []),
        }
    else:
        red_team_compact = {"available": False}

    return {
        "schema": "naqex-cockpit-summary-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "safety_seal": {
            "holdout_cutoff_utc": holdout_lock.get("cutoff_utc", "2025-01-01T00:00:00Z"),
            "holdout_lock_sha16": str(holdout_lock.get("lock_sha256", "UNKNOWN"))[:16],
            "holdout_rows_analysed": int(holdout_lock.get("holdout_rows_analysed", 0)),
            "order_send_count": ORDER_SEND_COUNT,
            "status": "HOLDOUT_2025_SEALED_DRYRUN",
        },
        "registry": {
            "status": reg.get("status", "UNKNOWN"),
            "engines_count": len(reg.get("engines", [])),
            "engines": reg.get("engines", []),
            "frozen_portfolios": reg.get("frozen_portfolios", {}),
            "one_time_holdout_2025_2026": reg.get("one_time_holdout_2025_2026", {}),
        },
        "pod_snapshot": pod_snap,
        "ftmo_live_specs": {
            "available": ftmo_live is not None,
            "status": "LIVE_DEMO_CAPTURED" if ftmo_live is not None else "PENDING_FTMO_LIVE_CAPTURE",
            "data": ftmo_live,
        },
        "red_team_stress": red_team_compact,
    }


def build_allocations_payload(root: Path = ROOT) -> dict[str, Any]:
    """Load 4-6+ orthogonal sleeves from `.runtime/quant-pod-returns/` + Dev Sleeve #1 and build equity, DD & corr."""
    ret_dir = root / ".runtime/quant-pod-returns"
    sleeve_maps: dict[str, dict[str, float]] = {}
    sleeve_meta: dict[str, dict[str, Any]] = {}

    s1 = _get_sleeve1_cached(root)
    if s1 is not None:
        sleeve_maps["S1_PROP_FX_IDX"] = s1[0]
        sleeve_meta["S1_PROP_FX_IDX"] = s1[1]

    if ret_dir.is_dir():
        for jf in sorted(ret_dir.glob("sleeve*.json")):
            try:
                rmap, meta = load_external_sleeve_json(jf)
            except Exception:
                continue
            if not rmap:
                continue
            sid = str(meta.get("sleeve_id") or jf.stem).upper()
            # Normalize well-known sleeve IDs cleanly
            if "sleeve2" in jf.name:
                sid = "S2_CRYPTO_SPOT"
            elif "sleeve3a" in jf.name:
                sid = "S3A_FUND_CARRY"
            elif "sleeve3b" in jf.name:
                sid = "S3B_MACRO_ETF"
            elif "sleeve4" in jf.name:
                sid = "S4_ETF40_MULTIFACTOR"
            elif "sleeve5" in jf.name:
                sid = "S5_CME_FUTURES_PROP"
            sleeve_maps[sid] = rmap
            sleeve_meta[sid] = meta

    if not sleeve_maps:
        return {
            "schema": "naqex-cockpit-allocations-v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "available": False,
            "sleeves": [],
            "dates": [],
            "equity_curves": {},
            "underwater_dd_pct": {},
            "correlation_matrix": {},
        }

    # Align on sealed Dev overlap (cap <= 2024-12-31 whenever S1_PROP_FX_IDX is present so Holdout stays sealed!)
    end_cap = "2024-12-31" if "S1_PROP_FX_IDX" in sleeve_maps else None
    biz_days, mat, names = align_sleeves_business_days(sleeve_maps, end_day=end_cap)

    # Default ERC/NCO-inspired weights across 4-6+ discovered sleeves
    default_w_map = {
        "S1_PROP_FX_IDX": 0.173,
        "S2_CRYPTO_SPOT": 0.065,
        "S3A_FUND_CARRY": 0.250,
        "S3B_MACRO_ETF": 0.141,
        "S4_ETF40_MULTIFACTOR": 0.120,
        "S5_CME_FUTURES_PROP": 0.251,
    }
    raw_w = np.array([default_w_map.get(nm, 1.0 / len(names)) for nm in names], dtype=np.float64)
    w_sum = float(np.sum(raw_w))
    weights = raw_w / w_sum if w_sum > 0 else np.full(len(names), 1.0 / len(names))

    pod_ret = mat @ weights

    eq_map: dict[str, list[float]] = {}
    dd_map: dict[str, list[float]] = {}
    sleeve_stats: list[dict[str, Any]] = []

    def _curve_and_dd(r_arr: np.ndarray) -> tuple[list[float], list[float]]:
        eq = 100.0 * np.cumprod(1.0 + r_arr)
        peaks = np.maximum.accumulate(np.maximum(100.0, eq))
        dd = -100.0 * (peaks - eq) / np.maximum(peaks, 1e-9)
        return eq.tolist(), dd.tolist()

    for idx, nm in enumerate(names):
        col = mat[:, idx]
        eq_l, dd_l = _curve_and_dd(col)
        eq_map[nm] = eq_l
        dd_map[nm] = dd_l
        m = compute_series_metrics(col, ann_days=252.0)
        sleeve_stats.append({
            "sleeve_id": nm,
            "strategy_name": sleeve_meta.get(nm, {}).get("strategy_name", nm),
            "default_weight_pct": round(float(weights[idx]) * 100.0, 2),
            **m,
        })

    pod_eq, pod_dd = _curve_and_dd(pod_ret)
    eq_map["POD_COMPOSITE"] = pod_eq
    dd_map["POD_COMPOSITE"] = pod_dd
    pod_metrics = compute_series_metrics(pod_ret, ann_days=252.0)

    # Synchronous N×N correlation matrix
    corr_np = np.corrcoef(mat, rowvar=False) if len(names) > 1 else np.array([[1.0]])
    corr_np = np.nan_to_num(corr_np, nan=0.0)
    corr_dict = {
        names[i]: {names[j]: round(float(corr_np[i, j]), 3) for j in range(len(names))}
        for i in range(len(names))
    }

    ds_dates, ds_eq = _downsample_series(biz_days, eq_map, max_points=260)
    _, ds_dd = _downsample_series(biz_days, dd_map, max_points=260)

    return {
        "schema": "naqex-cockpit-allocations-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "available": True,
        "window": {"start": biz_days[0], "end": biz_days[-1], "business_days": len(biz_days)},
        "holdout_sealed": end_cap == "2024-12-31",
        "sleeve_order": names,
        "sleeves": sleeve_stats,
        "pod_composite_metrics": pod_metrics,
        "dates": ds_dates,
        "equity_curves": ds_eq,
        "underwater_dd_pct": ds_dd,
        "correlation_matrix": corr_dict,
    }


def build_live_telemetry_payload(root: Path = ROOT) -> dict[str, Any]:
    overnight_dir = root / ".runtime/live-overnight"
    realtick_dir = root / ".runtime/mt5-realtick-results"

    mt5_spreads = _read_jsonl_tail(overnight_dir / "mt5_live_spread_log.jsonl", limit=20)
    crypto_shadow_rows = _read_jsonl_tail(overnight_dir / "crypto_shadow_log.jsonl", limit=20)
    crypto_shadow_latest = _safe_read_json(overnight_dir / "crypto_shadow_latest.json")
    crypto_maker_latest = _safe_read_json(overnight_dir / "crypto_maker_shadow_latest.json")
    crypto_maker_rows = _read_jsonl_tail(overnight_dir / "crypto_maker_shadow.jsonl", limit=20)

    # Parse structured Crypto Shadow L2 telemetry (BTC/ETH/SOL spreads, 10k slip vs 5bps budget, cycle count)
    cs_obj = crypto_shadow_latest if isinstance(crypto_shadow_latest, dict) else (crypto_shadow_rows[-1] if crypto_shadow_rows else None)
    if isinstance(cs_obj, dict):
        tca = cs_obj.get("tca_summary_top15") or {}
        depth = cs_obj.get("orderbook_depth_top15") or {}
        majors = {}
        for sym in ("BTCUSDT", "ETHUSDT", "SOLUSDT"):
            if sym in depth and isinstance(depth[sym], dict):
                majors[sym] = {
                    "mid": depth[sym].get("mid"),
                    "spread_bps": depth[sym].get("spread_bps"),
                    "slip_10k_bps": depth[sym].get("slip_10k_bps"),
                    "slip_50k_bps": depth[sym].get("slip_50k_bps"),
                    "depth_50k_ok": depth[sym].get("depth_50k_ok"),
                }
        s2_live = cs_obj.get("sleeve2_f4_4h_ema") or {}
        s3a_live = cs_obj.get("sleeve3a_carry_btc_eth") or {}
        crypto_shadow_block: dict[str, Any] = {
            "status": "ACTIVE",
            "source": ".runtime/live-overnight/crypto_shadow_latest.json" if isinstance(crypto_shadow_latest, dict) else ".runtime/live-overnight/crypto_shadow_log.jsonl",
            "cycle_num": cs_obj.get("cycle_num", len(crypto_shadow_rows)),
            "timestamp_utc": cs_obj.get("timestamp_utc"),
            "order_send_count": int(cs_obj.get("order_send_count", 0)),
            "count": max(len(crypto_shadow_rows), int(cs_obj.get("cycle_num") or 0)),
            "tca_summary": {
                "median_spread_bps": tca.get("median_spread_bps"),
                "median_slip_10k_bps": tca.get("median_slip_10k_bps"),
                "max_slip_10k_bps": tca.get("max_slip_10k_bps"),
                "median_slip_50k_bps": tca.get("median_slip_50k_bps"),
                "budget_10k_bps": tca.get("backtest_assumed_oneway_slip_bps", 5.0),
                "within_budget_10k": tca.get("tca_within_budget_10k"),
            },
            "majors_l2": majors,
            "sleeve2_regime_bull": s2_live.get("btc_regime_bull"),
            "sleeve2_active_count": s2_live.get("active_count"),
            "sleeve3a_funding_btc_ann_pct": ((s3a_live.get("perp_live_basis") or {}).get("BTCUSDT") or {}).get("next_funding_ann_pct"),
            "sleeve3a_funding_eth_ann_pct": ((s3a_live.get("perp_live_basis") or {}).get("ETHUSDT") or {}).get("next_funding_ann_pct"),
            "latest": cs_obj,
            "recent": crypto_shadow_rows[-8:],
        }
    else:
        crypto_shadow_block = {
            "status": "pending",
            "source": None,
            "cycle_num": 0,
            "timestamp_utc": None,
            "order_send_count": 0,
            "count": 0,
            "tca_summary": None,
            "majors_l2": {},
            "latest": None,
            "recent": [],
        }

    # Parse Crypto Maker Shadow Probe (`.runtime/live-overnight/crypto_maker_shadow_latest.json`)
    cm_obj = crypto_maker_latest if isinstance(crypto_maker_latest, dict) else (crypto_maker_rows[-1] if crypto_maker_rows else None)
    if isinstance(cm_obj, dict):
        crypto_maker_block: dict[str, Any] = {
            "status": "ACTIVE",
            "source": ".runtime/live-overnight/crypto_maker_shadow_latest.json" if isinstance(crypto_maker_latest, dict) else ".runtime/live-overnight/crypto_maker_shadow.jsonl",
            "cycle_num": cm_obj.get("cycle_num", len(crypto_maker_rows)),
            "timestamp_utc": cm_obj.get("timestamp_utc") or cm_obj.get("generated_utc"),
            "count": max(len(crypto_maker_rows), int(cm_obj.get("cycle_num") or 1)),
            "latest": cm_obj,
        }
    else:
        crypto_maker_block = {
            "status": "pending",
            "source": None,
            "cycle_num": 0,
            "timestamp_utc": None,
            "count": 0,
            "latest": None,
        }

    # Discover MT5 Real-Tick `Model=4` Matrix & Python Reconciliation (prioritize realtick_matrix_summary.json!)
    realtick_summary = None
    realtick_source = None
    if realtick_dir.is_dir():
        for name in ("realtick_matrix_summary.json", "mt5_vs_python_reconcile.json", "realtick_summary.json", "summary.json"):
            obj = _safe_read_json(realtick_dir / name)
            if isinstance(obj, dict):
                realtick_summary = obj
                realtick_source = f".runtime/mt5-realtick-results/{name}"
                break

    if isinstance(realtick_summary, dict):
        rec_map = realtick_summary.get("reconciliation") if isinstance(realtick_summary.get("reconciliation"), dict) else {}
        engines_compact = []
        for eng_id, rec in rec_map.items():
            if not isinstance(rec, dict):
                continue
            lc = rec.get("latency_curve") if isinstance(rec.get("latency_curve"), dict) else {}
            lat_rows = {
                lat_k: {
                    "ok": v.get("ok"),
                    "trades": v.get("trades"),
                    "net_profit": v.get("net_profit"),
                    "profit_factor": v.get("profit_factor"),
                    "swap_zero_ok": v.get("swap_zero_ok"),
                }
                for lat_k, v in lc.items()
                if isinstance(v, dict)
            }
            engines_compact.append({
                "engine_id": eng_id,
                "verdict": rec.get("verdict", "UNKNOWN"),
                "latency_drag_50_to_250ms_usd": rec.get("latency_drag_50_to_250ms_usd"),
                "latency_curve": lat_rows,
                "python_ref_trades": (rec.get("python_dev_reference") or {}).get("trades"),
                "python_ref_net_usd": (rec.get("python_dev_reference") or {}).get("net_profit_usd"),
            })
        realtick_block: dict[str, Any] = {
            "status": "AVAILABLE",
            "source": realtick_source,
            "generated_utc": realtick_summary.get("generated_utc"),
            "model": realtick_summary.get("model"),
            "window": realtick_summary.get("window"),
            "latencies_ms": realtick_summary.get("latencies_ms", []),
            "engines_run": realtick_summary.get("engines_run", len(engines_compact)),
            "account": realtick_summary.get("account"),
            "engines": engines_compact,
            "data": realtick_summary,
        }
    else:
        realtick_block = {
            "status": "pending",
            "source": None,
            "generated_utc": None,
            "model": None,
            "window": None,
            "latencies_ms": [],
            "engines_run": 0,
            "account": None,
            "engines": [],
            "data": None,
        }

    # Discover MT5 heartbeat JSON (prioritize live sandbox heartbeat -> latest telemetry -> fallback)
    heartbeat_data = None
    heartbeat_src = None
    for cand in (
        root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_heartbeat.json",
        overnight_dir / "naqex_heartbeat.json",
        root / ".runtime/naqex_heartbeat.json",
    ):
        obj = _safe_read_json(cand)
        if isinstance(obj, dict):
            heartbeat_data = obj
            heartbeat_src = cand.relative_to(root).as_posix()
            break

    # Extract MT5 live spread tail + FTMO-Demo live account, open positions & recent execution audit CSV
    mt5_latest = mt5_spreads[-1] if mt5_spreads else None
    mt5_acct_live = mt5_latest.get("account") if (isinstance(mt5_latest, dict) and isinstance(mt5_latest.get("account"), dict)) else {}
    if heartbeat_data is None and isinstance(mt5_latest, dict) and isinstance(mt5_latest.get("heartbeat"), dict):
        hb_pay = mt5_latest["heartbeat"].get("payload")
        if isinstance(hb_pay, dict):
            heartbeat_data = hb_pay
            heartbeat_src = ".runtime/live-overnight/mt5_live_spread_log.jsonl"

    raw_positions = list(mt5_latest.get("naqex_positions") or []) if isinstance(mt5_latest, dict) else []
    mae_mfe_lookup = _compute_positions_mae_mfe(_read_jsonl_tail(overnight_dir / "mt5_live_spread_log.jsonl", limit=1500)) if raw_positions else {}
    live_positions = []
    for p in raw_positions:
        if not isinstance(p, dict):
            continue
        mm = mae_mfe_lookup.get(int(p["ticket"])) if p.get("ticket") is not None else None
        live_positions.append({
            **p,
            "mae_pips": mm.get("mae_pips") if mm else None,
            "mfe_pips": mm.get("mfe_pips") if mm else None,
            "mae_usd": mm.get("mae_usd") if mm else None,
            "mfe_usd": mm.get("mfe_usd") if mm else None,
        })
    exec_audit_recent: list[dict[str, str]] = []
    exec_csv = root / ".runtime/ftmo-demo-portable-1515343166/MQL5/Files/naqex_exec_audit.csv"
    if exec_csv.is_file():
        try:
            with exec_csv.open("r", encoding="utf-8", errors="replace", newline="") as f:
                exec_audit_recent = list(csv.DictReader(f))[-15:]
        except OSError:
            exec_audit_recent = []

    demo_acct = realtick_block.get("account") if isinstance(realtick_block.get("account"), dict) else None
    mt5_spread_block: dict[str, Any] = {
        "status": "ACTIVE" if mt5_latest else "pending",
        "count": len(mt5_spreads),
        "latest": mt5_latest,
        "recent": mt5_spreads[-8:],
        "open_positions": live_positions,
        "exec_audit_recent": exec_audit_recent,
        "demo_account": {
            "login": mt5_acct_live.get("login") or (mt5_latest or {}).get("login") or (demo_acct or {}).get("login"),
            "server": mt5_acct_live.get("server") or (mt5_latest or {}).get("server") or (demo_acct or {}).get("server"),
            "balance": mt5_acct_live.get("balance") if "balance" in mt5_acct_live else ((mt5_latest or {}).get("balance") if (mt5_latest and "balance" in mt5_latest) else (demo_acct or {}).get("balance")),
            "equity": mt5_acct_live.get("equity") if "equity" in mt5_acct_live else ((mt5_latest or {}).get("equity") if (mt5_latest and "equity" in mt5_latest) else (demo_acct or {}).get("equity")),
            "profit": mt5_acct_live.get("profit"),
            "leverage": mt5_acct_live.get("leverage") or (demo_acct or {}).get("leverage"),
            "terminal_connected": (mt5_latest or {}).get("terminal_connected") if (mt5_latest and "terminal_connected" in mt5_latest) else (demo_acct or {}).get("terminal_connected"),
        } if (mt5_latest or demo_acct) else None,
    }

    emergency_state = read_emergency_cover_state(root)
    ftmo_specs = _safe_read_json(root / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json")
    upcoming_news = _load_upcoming_red_news(root, limit=10)

    return {
        "schema": "naqex-cockpit-live-telemetry-v2",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "mt5_heartbeat": {
            "status": "LIVE_HEARTBEAT" if heartbeat_data else ("DEMO_VERIFIED" if demo_acct else "pending"),
            "source": heartbeat_src or (realtick_source if demo_acct else None),
            "data": heartbeat_data or demo_acct,
        },
        "mt5_live_spreads": mt5_spread_block,
        "emergency_cover": emergency_state,
        "crypto_shadow": crypto_shadow_block,
        "crypto_maker_shadow": crypto_maker_block,
        "mt5_realtick_tca": realtick_block,
        "ftmo_live_specs_available": ftmo_specs is not None,
        "upcoming_red_news": upcoming_news,
    }


EMERGENCY_CONFIRM_CODES = {
    "HALT_NEW_ENTRIES": "HALT",
    "FLATTEN_ALL": "FLATTEN",
    "RESET_NORMAL": "RESET",
}


def read_emergency_cover_state(root: Path = ROOT) -> dict[str, Any]:
    state_path = root / ".runtime/live-overnight/naqex_emergency_cover_state.json"
    obj = _safe_read_json(state_path)
    if isinstance(obj, dict):
        return obj
    return {
        "schema": "naqex-emergency-cover-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "state": "NORMAL_COVER_CLOSED",
        "action": "NONE",
        "updated_utc": None,
        "reason": "Safety cover closed; zero emergency flags active.",
    }


def apply_emergency_cover_action(
    root: Path,
    body: dict[str, Any],
    *,
    bridge_dir: Path | None = None,
) -> tuple[HTTPStatus, dict[str, Any]]:
    """Fail-closed 2-step safety-covered emergency flag handler (OrderSend=0)."""
    cover_opened = bool(body.get("cover_opened", False))
    action = str(body.get("action", "")).strip().upper()
    confirm_code = str(body.get("confirm_code", "")).strip().upper()
    reason = str(body.get("reason", "")).strip()[:240] or "operator_triggered"

    if not cover_opened:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": "SAFETY_COVER_CLOSED: must flip safety cover first (cover_opened=true).",
        }
    expected_code = EMERGENCY_CONFIRM_CODES.get(action)
    if expected_code is None:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"INVALID_ACTION: allowed={sorted(EMERGENCY_CONFIRM_CODES.keys())}",
        }
    if confirm_code != expected_code:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"CONFIRM_CODE_MISMATCH: expected '{expected_code}' for action '{action}'.",
        }

    now_iso = datetime.now(timezone.utc).isoformat()
    new_state = "NORMAL_COVER_CLOSED" if action == "RESET_NORMAL" else f"ARMED_{action}"
    bridge_written = False
    if bridge_dir is not None:
        flag_path = bridge_dir / "naqex_manual_halt.flag"
        bridge_dir.mkdir(parents=True, exist_ok=True)
        if action == "RESET_NORMAL":
            if flag_path.exists():
                flag_path.unlink()
        else:
            flag_path.write_text(f"{action}|{now_iso}|{reason}\n", encoding="utf-8", newline="\n")
        bridge_written = True

    delivery_status = (
        "WRITTEN_TO_MT5_BRIDGE_AWAITING_ORCH_ACK"
        if bridge_written
        else "LOCAL_AUDIT_ONLY_NOT_DELIVERED_TO_MT5"
    )
    record = {
        "schema": "naqex-emergency-cover-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "state": new_state,
        "action": action,
        "reason": reason,
        "updated_utc": now_iso,
        "mt5_bridge_written": bridge_written,
        "delivery_status": delivery_status,
        "note": (
            "Bridge flag written to MT5 MQL5/Files; requires InpAllowManualHaltFile=true on Orchestrator for live effect."
            if bridge_written
            else "LOCAL AUDIT ONLY: NOT delivered to remote MT5/VPS! Open RDP/MT5 directly to halt or flatten live positions."
        ),
    }

    state_path = root / ".runtime/live-overnight/naqex_emergency_cover_state.json"
    state_path.parent.mkdir(parents=True, exist_ok=True)
    state_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    return HTTPStatus.OK, {"ok": True, **record}


def handle_prop_terms_audit_request(body: dict[str, Any]) -> tuple[HTTPStatus, dict[str, Any]]:
    """Offline baseline preview by default; opt-in TypeSafe jev-1.14.0 drift audit when requested."""
    firm = str(body.get("firm", "the5ers_high_stakes")).strip()
    terms_text = str(body.get("terms_text", "")).strip()
    use_typesafe = bool(body.get("use_typesafe", False))

    if firm not in FIRM_BASELINES:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": f"Unknown firm '{firm}'. Allowed: {sorted(FIRM_BASELINES.keys())}",
        }

    baseline = FIRM_BASELINES[firm]
    if not use_typesafe:
        return HTTPStatus.OK, {
            "ok": True,
            "order_send_count": ORDER_SEND_COUNT,
            "mode": "offline_baseline_preview",
            "firm": firm,
            "baseline": baseline,
            "verdict": "BASELINE_PREVIEW_ONLY",
            "note": "Tích chọn 'Bật AI TypeSafe (jev-1.14.0)' và dán văn bản điều khoản để kiểm toán drift trực tiếp.",
        }

    if len(terms_text) < 20:
        return HTTPStatus.BAD_REQUEST, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "error": "Văn bản điều khoản quá ngắn (< 20 ký tự) để kiểm toán.",
        }

    try:
        res = audit_prop_terms_text(terms_text, firm_id=firm)
        return HTTPStatus.OK, {"ok": True, "order_send_count": ORDER_SEND_COUNT, "mode": "typesafe_jev114", **res}
    except Exception as exc:
        return HTTPStatus.SERVICE_UNAVAILABLE, {
            "ok": False,
            "order_send_count": ORDER_SEND_COUNT,
            "mode": "typesafe_jev114_fail_closed",
            "error": f"Fail-closed TypeSafe error: {exc}",
        }


def _parse_float_token(tok: str) -> float | None:
    m = re.search(r"[-+]?\d+(?:,\d{3})*(?:\.\d+)?", tok or "")
    if not m:
        return None
    try:
        return float(m.group(0).replace(",", ""))
    except ValueError:
        return None


def _parse_stress_and_multiprop_md(md_path: Path) -> dict[str, Any] | None:
    """Parse verified Wave-2 Cycle 3B Black-Swan & Multi-Prop report tables (cached by mtime)."""
    if not md_path.is_file():
        return None
    mtime = md_path.stat().st_mtime
    cache_key = str(md_path.resolve())
    with _STRESS_CACHE_LOCK:
        cached = _STRESS_MD_CACHE.get(cache_key)
        if cached is not None and cached[0] == mtime:
            return cached[1]

    txt = md_path.read_text(encoding="utf-8", errors="replace")
    gen_m = re.search(r"\*\*Generated UTC:\*\*\s*`([^`]+)`", txt)
    generated_utc = gen_m.group(1) if gen_m else None

    # Parse 1A/1B/1C Multi-Prop budget tables (500 / 1,500 / 3,000 USD)
    budgets: dict[int, list[dict[str, Any]]] = {500: [], 1500: [], 3000: []}
    alloc_stress: dict[str, dict[str, Any]] = {}
    section = ""

    for raw_ln in txt.splitlines():
        ln = raw_ln.strip()
        if ln.startswith("### 1A."):
            section = "b500"
            continue
        if ln.startswith("### 1B."):
            section = "b1500"
            continue
        if ln.startswith("### 1C."):
            section = "b3000"
            continue
        if ln.startswith("### 1D."):
            section = "b1d"
            continue
        if ln.startswith("### 2A."):
            section = "s2a"
            continue
        if ln.startswith("### 2B."):
            section = "s2b"
            continue
        if ln.startswith("## 3."):
            section = "done"
            continue

        if not ln.startswith("|") or ln.startswith("|---") or ln.startswith("| Architecture") or ln.startswith("| Allocator"):
            continue
        cols = [c.strip() for c in ln.strip("|").split("|")]

        if section in ("b500", "b1500", "b3000") and len(cols) >= 10:
            bkey = {"b500": 500, "b1500": 1500, "b3000": 3000}[section]
            budgets[bkey].append({
                "architecture": cols[0],
                "profile": cols[1],
                "wipeout_pct": _parse_float_token(cols[2]) or 0.0,
                "sustain_pct": _parse_float_token(cols[3]) or 0.0,
                "double_fail_pct": _parse_float_token(cols[4]) or 0.0,
                "p95_corr_dd_pct": _parse_float_token(cols[5]) or 0.0,
                "fees_24m_usd": _parse_float_token(cols[6]) or 0.0,
                "wealth_24m_med_usd": _parse_float_token(cols[7]) or 0.0,
                "ev_per_fee": _parse_float_token(cols[8]) or 0.0,
                "ob_60m_raw": cols[9],
            })
        elif section == "s2a" and len(cols) >= 8:
            aname = cols[0]
            h30_50 = [x.strip() for x in cols[4].split("/")]
            c95_99 = [x.strip() for x in cols[5].split("/")]
            w20_60 = [x.strip() for x in cols[1].split("/")]
            alloc_stress[aname] = {
                "allocator": aname,
                "hist_20d_dd_pct": _parse_float_token(w20_60[0]) or 0.0,
                "hist_60d_dd_pct": _parse_float_token(w20_60[1]) if len(w20_60) > 1 else 0.0,
                "rate2022_ftx_dd_pct": _parse_float_token(cols[2]) or 0.0,
                "cex_weight_pct": _parse_float_token(cols[3]) or 0.0,
                "cex_haircut_30_pct": _parse_float_token(h30_50[0]) or 0.0,
                "cex_haircut_50_pct": _parse_float_token(h30_50[1]) if len(h30_50) > 1 else 0.0,
                "corr085_p95_dd_pct": _parse_float_token(c95_99[0]) or 0.0,
                "corr085_p99_dd_pct": _parse_float_token(c95_99[1]) if len(c95_99) > 1 else 0.0,
                "worst_1d_p99_pct": _parse_float_token(cols[6]) or 0.0,
                "slip_3x_cagr_raw": cols[7],
            }
        elif section == "s2b" and len(cols) >= 3:
            aname = cols[0]
            if aname in alloc_stress:
                alloc_stress[aname]["worst_case_dd_pct"] = _parse_float_token(cols[1]) or 0.0
                alloc_stress[aname]["dominant_shock"] = cols[2]

    if not alloc_stress and not any(budgets.values()):
        return None

    parsed = {
        "source": "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md",
        "generated_utc": generated_utc,
        "multi_prop_budgets": budgets,
        "black_swan_allocators": list(alloc_stress.values()),
    }
    with _STRESS_CACHE_LOCK:
        _STRESS_MD_CACHE[cache_key] = (mtime, parsed)
    return parsed


def build_stress_payload(
    root: Path = ROOT,
    *,
    capital_usd: float = 50_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Build Black-Swan VND/USD loss matrix & Multi-Prop budget wipeout comparison scaled to any capital tier."""
    cap_usd = max(1_000.0, float(capital_usd))
    fx = max(1_000.0, float(usd_vnd_rate))
    cap_vnd = cap_usd * fx

    md_path = root / "planning/research/MULTI-PROP-SCALING-AND-BLACKSWAN-STRESS-20261124.md"
    parsed = _parse_stress_and_multiprop_md(md_path)
    if parsed is None:
        return {
            "schema": "naqex-cockpit-stress-v1",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "status": "pending",
            "available": False,
            "capital_usd": round(cap_usd, 2),
            "capital_vnd": round(cap_vnd, 0),
            "usd_vnd_rate": fx,
            "black_swan_matrix": [],
            "multi_prop_budgets": {},
        }

    # Owner PROFILE.md comfort thresholds by VND tier
    if cap_vnd >= 1_000_000_000.0:
        green_cap, amber_cap = 5.5, 10.0
    elif cap_vnd >= 100_000_000.0:
        green_cap, amber_cap = 10.0, 15.0
    else:
        green_cap, amber_cap = 15.0, 20.0

    def _scaled_loss(pct: float) -> dict[str, float]:
        usd = cap_usd * (pct / 100.0)
        return {
            "pct": round(pct, 2),
            "usd": round(usd, 2),
            "vnd_m": round((usd * fx) / 1_000_000.0, 1),
        }

    matrix: list[dict[str, Any]] = []
    for row in parsed["black_swan_allocators"]:
        wc_pct = float(row.get("worst_case_dd_pct") or max(row["cex_haircut_50_pct"], row["corr085_p99_dd_pct"]))
        if wc_pct <= green_cap:
            verdict = "COMFORT_GREEN"
        elif wc_pct <= amber_cap:
            verdict = "CAUTION_AMBER"
        else:
            verdict = "BREACH_RED"
        matrix.append({
            "allocator": row["allocator"],
            "cex_weight_pct": row["cex_weight_pct"],
            "dominant_shock": row.get("dominant_shock", "CEX_-50%_Haircut"),
            "verdict": verdict,
            "cex_30": _scaled_loss(row["cex_haircut_30_pct"]),
            "cex_50": _scaled_loss(row["cex_haircut_50_pct"]),
            "corr085_p99": _scaled_loss(row["corr085_p99_dd_pct"]),
            "rate2022_ftx": _scaled_loss(row["rate2022_ftx_dd_pct"]),
            "worst_case": _scaled_loss(wc_pct),
            "worst_1d_p99_pct": row["worst_1d_p99_pct"],
            "slip_3x_cagr_raw": row["slip_3x_cagr_raw"],
        })

    # Compact headline highlights for 500 / 1,500 / 3,000 USD Multi-Prop comparison
    mp_highlights: list[dict[str, Any]] = []
    for b_usd in (500, 1500, 3000):
        rows_b = parsed["multi_prop_budgets"].get(b_usd, [])
        for r in rows_b:
            if (r["architecture"] in ("DUAL_2FIRM_STAGGER_42D", "DUAL_2FIRM_SYNC", "LADDER_STAGGER_SCALE")) and (
                (r["architecture"] == "DUAL_2FIRM_STAGGER_42D" and r["profile"] == "Balanced")
                or (r["architecture"] == "DUAL_2FIRM_SYNC" and r["profile"] == "Sprint")
                or (r["architecture"] == "LADDER_STAGGER_SCALE" and r["profile"] == "Balanced")
            ):
                mp_highlights.append({"budget_usd": b_usd, **r})

    return {
        "schema": "naqex-cockpit-stress-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "report_generated_utc": parsed["generated_utc"],
        "source": parsed["source"],
        "order_send_count": ORDER_SEND_COUNT,
        "status": "AVAILABLE",
        "available": True,
        "capital_usd": round(cap_usd, 2),
        "capital_vnd": round(cap_vnd, 0),
        "capital_vnd_m": round(cap_vnd / 1_000_000.0, 1),
        "usd_vnd_rate": fx,
        "cex_group_cap_recommendation": {
            "max_combined_cex_pct": 25.0,
            "capped_cex50_loss": _scaled_loss(12.5),
            "capped_cex30_loss": _scaled_loss(7.5),
        },
        "black_swan_matrix": matrix,
        "multi_prop_highlights": mp_highlights,
        "multi_prop_budgets": {str(k): v for k, v in parsed["multi_prop_budgets"].items()},
    }


def build_overview_payload(
    root: Path = ROOT,
    *,
    capital_usd: float = 50_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Unified Control Room overview aggregating summary, live overnight telemetry & Black-Swan stress."""
    return {
        "schema": "naqex-cockpit-overview-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "summary": build_summary_payload(root),
        "live_telemetry": build_live_telemetry_payload(root),
        "stress": build_stress_payload(root, capital_usd=capital_usd, usd_vnd_rate=usd_vnd_rate),
    }


def compute_vnd_risk_calculator(
    *,
    capital_vnd: float = 250_000_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    prop_nominal_usd: float = 10_000.0,
    risk_profile: str = "balanced",
    cost_mult: float = 1.0,
    root: Path = ROOT,
) -> dict[str, Any]:
    """VND/USD Absolute Risk, Red-Team Stress & Prop->Own-Book Calculator calibrated to `knowledge/owner/PROFILE.md`."""
    cap_vnd = max(0.0, float(capital_vnd))
    fx = max(1_000.0, float(usd_vnd_rate))
    cap_usd = cap_vnd / fx
    prop_nom = max(0.0, float(prop_nominal_usd))
    cm = max(0.5, min(3.5, float(cost_mult)))

    # Profile risk multipliers (synced with M2.2 & Holdout Funded Safe)
    profiles = {
        "conservative": {"label": "Funded Safe (1.0x)", "mult": 1.0, "exp_cagr_pct": 10.5, "exp_peak_dd_pct": 6.5, "daily_dd_pct": 1.5, "risk_per_trade_pct": 0.50},
        "balanced": {"label": "Quant Pod Balanced (4-Sleeve)", "mult": 1.0, "exp_cagr_pct": 18.0, "exp_peak_dd_pct": 8.0, "daily_dd_pct": 1.8, "risk_per_trade_pct": 0.50},
        "p1_balanced": {"label": "Prop P1 Balanced (4.0x)", "mult": 4.0, "exp_cagr_pct": 30.0, "exp_peak_dd_pct": 9.2, "daily_dd_pct": 4.2, "risk_per_trade_pct": 1.50},
        "p1_sprint": {"label": "Prop P1 Sprint (4.75x)", "mult": 4.75, "exp_cagr_pct": 36.0, "exp_peak_dd_pct": 9.5, "daily_dd_pct": 4.3, "risk_per_trade_pct": 1.75},
    }
    prof = profiles.get(risk_profile.lower(), profiles["balanced"])

    # Pull real Red-Team stress curve if available
    red_team = _safe_read_json(root / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json") or {}
    t1 = red_team.get("test1_cost_stress", {}) if isinstance(red_team, dict) else {}
    p7_curve = t1.get("portfolio_curve", {}).get("PORT_7E", [])
    p9_curve = t1.get("portfolio_curve", {}).get("PORT_9E", [])
    p7_interp = _interpolate_red_team_curve(p7_curve, cm)
    p9_interp = _interpolate_red_team_curve(p9_curve, cm)
    p7_be = float(t1.get("portfolio_breakeven", {}).get("PORT_7E", {}).get("breakeven_mult", 2.26))
    p9_be = float(t1.get("portfolio_breakeven", {}).get("PORT_9E", {}).get("breakeven_mult", 2.23))

    # Calibrate comfort band directly from knowledge/owner/PROFILE.md §3:
    # - Small test capital (< 100M VND): tolerates up to 15-20% DD
    # - Medium-large capital (100M - 1B VND): treats 15%-20% DD as too high (target <= 10%)
    # - Very large capital (>= 1B VND): treats 5% DD as significant (target <= 5-7%)
    eff_dd_pct = prof["exp_peak_dd_pct"] if cm <= 1.0 else max(prof["exp_peak_dd_pct"], p7_interp.get("peak_dd_pct", prof["exp_peak_dd_pct"]))
    if cap_vnd >= 1_000_000_000.0:
        tier_label = "Vốn rất lớn (>= 1 tỷ VND — PROFILE.md: 5% DD đã đáng kể)"
        green_cap, amber_cap = 5.5, 8.0
    elif cap_vnd >= 100_000_000.0:
        tier_label = "Vốn trung–lớn (100 triệu – 1 tỷ VND — PROFILE.md: 15%–20% DD là quá cao)"
        green_cap, amber_cap = 10.0, 14.5
    else:
        tier_label = "Vốn thử nghiệm nhỏ (< 100 triệu VND — chịu được DD cao hơn)"
        green_cap, amber_cap = 15.0, 20.0

    if eff_dd_pct <= green_cap:
        comfort_verdict = "COMFORT_GREEN"
    elif eff_dd_pct <= amber_cap:
        comfort_verdict = "CAUTION_AMBER"
    else:
        comfort_verdict = "OVER_TOLERANCE_RED"

    one_r_usd = cap_usd * (prof["risk_per_trade_pct"] / 100.0)
    daily_dd_usd = cap_usd * (prof["daily_dd_pct"] / 100.0)
    peak_dd_usd = cap_usd * (eff_dd_pct / 100.0)
    giveback_2r_usd = one_r_usd * 2.0  # Behavioral check for profit-giveback discomfort!
    exp_annual_own_usd = cap_usd * (prof["exp_cagr_pct"] / 100.0)

    crossover = compute_prop_own_crossover(
        own_book_equity_usd=cap_usd,
        active_prop_nominal_usd=prop_nom,
        prop_expected_ann_ret=max(0.0, p7_interp.get("ann_pct", 7.73) / 100.0) if p7_curve else 0.10,
        own_pod_expected_ann_ret=prof["exp_cagr_pct"] / 100.0,
        avg_prop_split=0.80,
        firm_counterparty_haircut=0.10,
        annual_prop_fees_usd=210.0 if prop_nom > 0 else 0.0,
        usd_vnd_rate=fx,
    )

    # 4-sleeve own-book allocation breakdown (ERC_Capped35 baseline)
    sleeve_weights = [
        {"sleeve": "S1_PROP_FX_IDX", "label": "FX/Idx Intraday (PORT_7E)", "weight_pct": 24.0},
        {"sleeve": "S2_CRYPTO_SPOT", "label": "Crypto Spot Top-15 (F4_4H_EMA)", "weight_pct": 16.6},
        {"sleeve": "S3A_FUND_CARRY", "label": "Funding Carry 2xBuf (Cap <=20% live)", "weight_pct": 20.0},
        {"sleeve": "S3B_MACRO_ETF", "label": "18-Yr Macro ETF (M5_VOL_PARITY)", "weight_pct": 39.4},
    ]
    for sw in sleeve_weights:
        u = cap_usd * sw["weight_pct"] / 100.0
        sw["usd"] = round(u, 2)
        sw["vnd"] = round(u * fx, 0)

    per_engine_stress = []
    for eng in t1.get("per_engine", []):
        c1 = float(eng.get("cost_1x_usd", 0.0))
        n1 = float(eng.get("net_1x_usd", 0.0))
        est_net = n1 - (cm - 1.0) * c1
        per_engine_stress.append({
            "engine": eng["engine"],
            "n_trades": eng["n_trades"],
            "breakeven_mult": eng["breakeven_mult"],
            "est_net_usd": round(est_net, 2),
            "survives": est_net > 0.0,
        })

    return {
        "schema": "naqex-vnd-risk-calculator-v1",
        "order_send_count": ORDER_SEND_COUNT,
        "inputs": {
            "capital_vnd": round(cap_vnd, 0),
            "capital_usd": round(cap_usd, 2),
            "usd_vnd_rate": fx,
            "prop_nominal_usd": round(prop_nom, 2),
            "risk_profile": risk_profile,
            "profile_label": prof["label"],
            "cost_mult": round(cm, 2),
        },
        "absolute_pain_table": {
            "one_r_stop_usd": round(one_r_usd, 2),
            "one_r_stop_vnd": round(one_r_usd * fx, 0),
            "profit_giveback_2r_usd": round(giveback_2r_usd, 2),
            "profit_giveback_2r_vnd": round(giveback_2r_usd * fx, 0),
            "daily_dd_usd": round(daily_dd_usd, 2),
            "daily_dd_vnd": round(daily_dd_usd * fx, 0),
            "expected_peak_dd_pct": round(eff_dd_pct, 2),
            "expected_peak_dd_usd": round(peak_dd_usd, 2),
            "expected_peak_dd_vnd": round(peak_dd_usd * fx, 0),
            "expected_annual_return_usd": round(exp_annual_own_usd, 2),
            "expected_annual_return_vnd": round(exp_annual_own_usd * fx, 0),
        },
        "owner_profile_assessment": {
            "capital_tier": tier_label,
            "green_dd_cap_pct": green_cap,
            "amber_dd_cap_pct": amber_cap,
            "verdict": comfort_verdict,
        },
        "red_team_stress": {
            "cost_mult": round(cm, 2),
            "PORT_7E": {**p7_interp, "breakeven_mult": p7_be, "headroom_mult": round(p7_be - cm, 2)},
            "PORT_9E": {**p9_interp, "breakeven_mult": p9_be, "headroom_mult": round(p9_be - cm, 2)},
            "per_engine": per_engine_stress,
        },
        "crossover": crossover,
        "own_book_sleeve_allocation": sleeve_weights,
    }


def make_handler(root: Path = ROOT, static_dir: Path = STATIC_DIR):
    class CockpitHandler(BaseHTTPRequestHandler):
        def log_message(self, format: str, *args: Any) -> None:
            # Keep stdout/stderr quiet during automated smoke tests
            return

        def _send_bytes(self, code: int, body: bytes, content_type: str) -> None:
            self.send_response(code)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.end_headers()
            self.wfile.write(body)

        def _send_json(self, code: int, payload: Any) -> None:
            raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self._send_bytes(code, raw, "application/json; charset=utf-8")

        def _serve_static(self, rel_name: str) -> None:
            try:
                target = (static_dir / rel_name).resolve()
                base = static_dir.resolve()
                target.relative_to(base)
            except Exception:
                self._send_json(HTTPStatus.FORBIDDEN, {"error": "forbidden"})
                return
            if not target.is_file():
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            mime = MIME_TYPES.get(target.suffix.lower(), "application/octet-stream")
            self._send_bytes(HTTPStatus.OK, target.read_bytes(), mime)

        def do_GET(self) -> None:
            parsed = urlparse(self.path)
            path = parsed.path
            qs = parse_qs(parsed.query)

            if path in ("/", "/index.html"):
                self._serve_static("index.html")
                return
            if path.startswith("/static/"):
                self._serve_static(path[len("/static/"):])
                return
            if path == "/api/health":
                self._send_json(HTTPStatus.OK, {
                    "ok": True,
                    "service": "naqex-cockpit",
                    "order_send_count": ORDER_SEND_COUNT,
                    "utc": datetime.now(timezone.utc).isoformat(),
                })
                return
            if path == "/api/summary":
                self._send_json(HTTPStatus.OK, build_summary_payload(root))
                return
            if path == "/api/overview":
                try:
                    cap_u = float(qs.get("capital_usd", [50_000.0])[0])
                except (ValueError, TypeError):
                    cap_u = 50_000.0
                try:
                    fx_r = float(qs.get("usd_vnd", [DEFAULT_USD_VND_RATE])[0])
                except (ValueError, TypeError):
                    fx_r = DEFAULT_USD_VND_RATE
                self._send_json(HTTPStatus.OK, build_overview_payload(root, capital_usd=cap_u, usd_vnd_rate=fx_r))
                return
            if path == "/api/allocations":
                self._send_json(HTTPStatus.OK, build_allocations_payload(root))
                return
            if path == "/api/live-telemetry":
                self._send_json(HTTPStatus.OK, build_live_telemetry_payload(root))
                return
            if path == "/api/prop-metrix":
                prog = str(qs.get("program", ["ftmo_free_trial_10k"])[0])
                offline = str(qs.get("offline", ["0"])[0]) in ("1", "true", "yes")
                self._send_json(HTTPStatus.OK, build_prop_metrix_payload(root, program=prog, allow_cloud_fetch=not offline))
                return
            if path == "/api/emergency-cover":
                self._send_json(HTTPStatus.OK, read_emergency_cover_state(root))
                return
            if path == "/api/stress":
                try:
                    cap_u = float(qs.get("capital_usd", [50_000.0])[0])
                except (ValueError, TypeError):
                    cap_u = 50_000.0
                try:
                    fx_r = float(qs.get("usd_vnd", [DEFAULT_USD_VND_RATE])[0])
                except (ValueError, TypeError):
                    fx_r = DEFAULT_USD_VND_RATE
                self._send_json(HTTPStatus.OK, build_stress_payload(root, capital_usd=cap_u, usd_vnd_rate=fx_r))
                return
            if path == "/api/vnd-calculator":
                def _qfloat(k: str, default: float) -> float:
                    try:
                        return float(qs.get(k, [default])[0])
                    except (ValueError, TypeError):
                        return default

                res = compute_vnd_risk_calculator(
                    capital_vnd=_qfloat("capital_vnd", 250_000_000.0),
                    usd_vnd_rate=_qfloat("usd_vnd", DEFAULT_USD_VND_RATE),
                    prop_nominal_usd=_qfloat("prop_nominal_usd", 10_000.0),
                    risk_profile=str(qs.get("risk_profile", ["balanced"])[0]),
                    cost_mult=_qfloat("cost_mult", 1.0),
                    root=root,
                )
                self._send_json(HTTPStatus.OK, res)
                return
            if path == "/api/rebalancer":
                mode = str(qs.get("mode", ["M5_VOL_PARITY_TREND_GUARD"])[0])
                if mode not in VALID_MODES:
                    mode = "M5_VOL_PARITY_TREND_GUARD"
                try:
                    eq = float(qs.get("equity_usd", [25_000.0])[0])
                except (ValueError, TypeError):
                    eq = 25_000.0
                try:
                    plan = generate_rebalance_plan(
                        mode=mode,
                        equity_usd=max(100.0, eq),
                        cache_dir=root / ".runtime/macro-etf-cache",
                    )
                    self._send_json(HTTPStatus.OK, plan)
                except Exception as exc:
                    self._send_json(HTTPStatus.OK, {
                        "schema": "naqex-ibkr-macro-rebalance-v1",
                        "order_send_count": ORDER_SEND_COUNT,
                        "dry_run_only": True,
                        "available": False,
                        "reason": str(exc),
                    })
                return

            self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found", "path": path})

        def do_POST(self) -> None:
            parsed = urlparse(self.path)
            if parsed.path not in ("/api/vnd-calculator", "/api/emergency-cover", "/api/prop-terms-audit"):
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(min(length, 65_536))
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
                return
            if parsed.path == "/api/emergency-cover":
                status_c, payload = apply_emergency_cover_action(root, body)
                self._send_json(status_c, payload)
                return
            if parsed.path == "/api/prop-terms-audit":
                status_c, payload = handle_prop_terms_audit_request(body)
                self._send_json(status_c, payload)
                return
            res = compute_vnd_risk_calculator(
                capital_vnd=float(body.get("capital_vnd", 250_000_000.0)),
                usd_vnd_rate=float(body.get("usd_vnd", DEFAULT_USD_VND_RATE)),
                prop_nominal_usd=float(body.get("prop_nominal_usd", 10_000.0)),
                risk_profile=str(body.get("risk_profile", "balanced")),
                cost_mult=float(body.get("cost_mult", 1.0)),
                root=root,
            )
            self._send_json(HTTPStatus.OK, res)

    return CockpitHandler


def create_server(
    host: str = DEFAULT_HOST,
    port: int = DEFAULT_PORT,
    *,
    root: Path = ROOT,
    static_dir: Path = STATIC_DIR,
) -> ThreadingHTTPServer:
    if host not in ("127.0.0.1", "localhost"):
        raise ValueError(f"Cockpit server MUST bind strictly to localhost/127.0.0.1, refused '{host}'")
    return ThreadingHTTPServer((host, port), make_handler(root=root, static_dir=static_dir))


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Quant Pod Local Web Control Room (127.0.0.1)")
    ap.add_argument("--host", default=DEFAULT_HOST)
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    args = ap.parse_args()

    srv = create_server(host=args.host, port=args.port)
    actual_port = srv.server_address[1]
    print(f"Naqex Quant Pod Cockpit listening at http://{args.host}:{actual_port} (OrderSend=0, Read-Only)", flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
