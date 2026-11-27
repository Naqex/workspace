"""Prop risk attribution (R4->R1), observed MAE/MFE calculator, and Heroku EU live probe."""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, urlparse

from cockpit.modules.helpers import _pip_size_for_symbol, _safe_read_json, as_dict, as_list
from cockpit.modules.state import (
    _HEROKU_CACHE_LOCK,
    get_heroku_status_cache,
    get_urllib_request,
    set_heroku_status_cache,
)

_INDEX_SPREAD_TOKENS = (
    "US100",
    "NAS100",
    "NDX",
    "USTEC",
    "US500",
    "SPX",
    "US30",
    "GER40",
    "DE40",
    "DAX",
    "XAU",
    "BTC",
)


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
    soon_news = [
        ev
        for ev in upcoming_news
        if (not ev.get("in_blackout_window")) and 0.0 <= float(ev.get("hours_away", 99.0)) <= 1.0
    ]

    hard_daily = abs(worst_daily_usd) >= daily_lim - 1e-9
    hard_static = abs(worst_static_usd) >= max_lim - 1e-9
    daily_dd_ratio = abs(worst_daily_usd) / max(1.0, daily_lim)
    static_dd_ratio = abs(worst_static_usd) / max(1.0, max_lim)

    # Inspect latest snapshot quotes for spread spikes & open positions for swap/concentration
    quotes = as_dict(latest_snap.get("quotes"))
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
            is_idx = any(tok in sym.upper() for tok in _INDEX_SPREAD_TOKENS)
            hi_lim = 6.0 if is_idx else 3.5
            warn_lim = 3.5 if is_idx else 2.2
            if sp_pips >= hi_lim:
                spread_alerts.append(f"{sym} ({sp_pips:.1f} pip)")
            elif sp_pips >= warn_lim:
                spread_warns.append(f"{sym} ({sp_pips:.1f} pip)")

    open_pos = as_list(latest_snap.get("naqex_positions"))
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
    top_sym = max(sym_counts, key=lambda k: sym_counts[k]) if sym_counts else ""

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
        r4_warns.append(
            f"Sắp có tin đỏ trong < 60 phút ({ev0.get('ccy')} {ev0.get('event')} · {ev0.get('countdown_vi')})"
        )

    if r4_alerts:
        r4 = {"code": "R4", "title": "Luật quỹ & Tin đỏ", "status": "ALERT", "detail": "; ".join(r4_alerts)}
    elif r4_warns:
        r4 = {"code": "R4", "title": "Luật quỹ & Tin đỏ", "status": "WARN", "detail": "; ".join(r4_warns)}
    else:
        r4 = {
            "code": "R4",
            "title": "Luật quỹ & Tin đỏ",
            "status": "OK",
            "detail": "An toàn — không vi phạm luật quỹ, ngoài vùng tin đỏ, Kill-Switch TẮT.",
        }

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
        r3 = {
            "code": "R3",
            "title": "Khớp lệnh & Máy chủ",
            "status": "OK",
            "detail": "Chế độ chờ (chưa có dữ liệu live); chưa ghi nhận lỗi máy chủ hay thiếu SL.",
        }
    else:
        r3 = {
            "code": "R3",
            "title": "Khớp lệnh & Máy chủ",
            "status": "OK",
            "detail": "Sạch — 0 lệnh thiếu SL, heartbeat ổn định, spread & swap trong ngưỡng.",
        }

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
        r2 = {
            "code": "R2",
            "title": "Dồn lệnh & Danh mục",
            "status": "OK",
            "detail": "Cân bằng — không dồn lệnh cùng mã, chưa chạm phanh Amber/Red danh mục.",
        }

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
            "detail": (
                f"Biến động âm nhẹ (tổng -{tot_dd_pct:.2f}%, hôm nay -{day_dd_pct:.2f}%) "
                "— trong biên độ bình thường."
            ),
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
        quotes = as_dict(snap.get("quotes"))
        cap_utc = str(snap.get("captured_utc") or "")
        for p in as_list(snap.get("naqex_positions")):
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
                rec_init: dict[str, Any] = {
                    "samples": 0,
                    "mae_usd": pnl,
                    "mfe_usd": pnl,
                    "mae_pips": pips,
                    "mfe_pips": pips,
                    "first_seen_utc": cap_utc,
                    "last_seen_utc": cap_utc,
                }
                stats[tid] = rec_init
                rec = rec_init
            rec["samples"] = int(rec["samples"]) + 1
            rec["last_seen_utc"] = cap_utc
            if pnl < float(rec["mae_usd"]):
                rec["mae_usd"] = pnl
            if pnl > float(rec["mfe_usd"]):
                rec["mfe_usd"] = pnl
            if pips is not None:
                cur_mae_pips = rec["mae_pips"]
                cur_mfe_pips = rec["mfe_pips"]
                if cur_mae_pips is None or pips < float(cur_mae_pips):
                    rec["mae_pips"] = pips
                if cur_mfe_pips is None or pips > float(cur_mfe_pips):
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
    cfg_path = root / ".runtime/ops-cloud/heroku_connection_local.json"
    if not cfg_path.is_file():
        return None
    now = time.monotonic()
    with _HEROKU_CACHE_LOCK:
        ts_c, val_c = get_heroku_status_cache()
        if (now - ts_c) < ttl_sec:
            return val_c

    cfg = _safe_read_json(cfg_path)
    if not isinstance(cfg, dict):
        return None
    raw_web_url = str(cfg.get("web_url") or "").strip()
    dash_url = str(cfg.get("mobile_dashboard_url") or "").strip()
    view_token = str(cfg.get("view_token") or "").strip()
    if not view_token and dash_url:
        view_token = (parse_qs(urlparse(dash_url).query).get("token") or [""])[0].strip()
    if not view_token and raw_web_url:
        view_token = (parse_qs(urlparse(raw_web_url).query).get("token") or [""])[0].strip()
    parsed_web = urlparse(raw_web_url)
    web_base = (
        f"{parsed_web.scheme}://{parsed_web.netloc}{parsed_web.path}".rstrip("/")
        if (parsed_web.scheme and parsed_web.netloc)
        else ""
    )
    if not web_base or not view_token:
        return None
    result: dict[str, Any] | None = None
    url_req = get_urllib_request()
    try:
        req = url_req.Request(
            f"{web_base}/api/status",
            headers={"User-Agent": "Naqex-Cockpit/1.0", "X-Naqex-View-Token": view_token},
        )
        with url_req.urlopen(req, timeout=2.5) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        nodes = data.get("nodes") or []
        preferred = next((n for n in nodes if n.get("account_label") == "NAQEX_NODE1"), None) or (
            nodes[0] if nodes else None
        )
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
        set_heroku_status_cache((now, result))
    return result
