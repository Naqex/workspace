"""FTMO-MetriX-style Prop Account payload builder (buffers, rules, calendar, MAE/MFE)."""

from __future__ import annotations

import calendar
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from cockpit.modules.helpers import (
    _load_upcoming_red_news,
    _read_jsonl_tail,
    _safe_read_json,
    as_dict,
)
from cockpit.modules.prop_risk import (
    _build_prop_risk_attribution,
    _compute_positions_mae_mfe,
    _fetch_heroku_node1_cached,
)
from cockpit.modules.state import ORDER_SEND_COUNT, PROP_METRIX_PROGRAMS, ROOT


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
    snap_acct = as_dict(latest_snap.get("account"))
    cloud_eq = cloud_node.get("equity") if cloud_node is not None else None
    snap_eq = snap_acct.get("equity")
    if cloud_node is not None and cloud_eq is not None:
        source_label = f"{cloud_node.get('account_label') or 'NAQEX_NODE1'} · HEROKU LIVE"
        source_status = str(cloud_node.get("status") or "OK")
        cloud_bal = cloud_node.get("balance")
        balance = float(cloud_bal) if cloud_bal is not None else init_usd
        equity = float(cloud_eq)
        open_pos_cnt = int(cloud_node.get("open_positions") or 0)
        orphan_cnt = int(cloud_node.get("orphan_no_sl") or 0)
        regime = str(cloud_node.get("regime") or "NORMAL")
        kill_sw = bool(cloud_node.get("kill_switch") or False)
        age_raw = cloud_node.get("age_sec")
        age_sec: int | None = int(age_raw) if age_raw is not None else None
        daily_dd_pct_hb = float(cloud_node.get("daily_dd_pct") or 0.0)
    elif snap_acct and snap_eq is not None:
        source_label = "LOCAL MT5 TELEMETRY LOG"
        source_status = "CACHED"
        snap_bal = snap_acct.get("balance")
        balance = float(snap_bal) if snap_bal is not None else init_usd
        equity = float(snap_eq)
        open_pos_cnt = int(latest_snap.get("naqex_positions_count") or 0)
        orphan_cnt = int(latest_snap.get("orphan_no_sl") or 0)
        hb_s = as_dict(latest_snap.get("heartbeat"))
        regime = str(hb_s.get("regime") or local_hb.get("regime") or "NORMAL")
        kill_sw = bool(hb_s.get("kill_switch") or local_hb.get("kill_switch") or False)
        age_sec = None
        daily_dd_pct_hb = float(local_hb.get("daily_dd_pct") or 0.0)
    elif local_hb:
        source_label = "LOCAL HEARTBEAT JSON"
        source_status = "CACHED"
        hb_bal = local_hb.get("balance")
        hb_eq = local_hb.get("equity")
        balance = float(hb_bal) if hb_bal is not None else init_usd
        equity = float(hb_eq) if hb_eq is not None else balance
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
        ac = as_dict(s.get("account"))
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
            if (
                pos_c > 0
                or abs(eq_f - bal_f) > 1e-6
                or abs(eq_f - cur["start_eq"]) > 1e-6
                or abs(bal_f - cur["start_eq"]) > 1e-6
            ):
                cur["has_trade"] = True
        prev_day_end_eq = eq_f

    today_utc = datetime.now(UTC).strftime("%Y-%m-%d")
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

    target_progress_pct = (
        round(max(0.0, min(100.0, 100.0 * total_pnl_usd / float(target_usd))), 1) if target_usd else None
    )

    if min_prof_pct > 0.0:
        pct_vi = f"{min_prof_pct:g}".replace(".", ",")
        min_days_rule = {
            "id": "min_trading_days",
            "label": f"Ngày lãi tối thiểu >= +{pct_vi}% ({min_days} ngày)",
            "value_text": (
                f"{profitable_days_count} / {min_days} ngày lãi "
                f"(GD: {days_traded} ngày · >= +{min_prof_usd:,.2f} USD)"
            ),
            "status": "PASS" if profitable_days_count >= min_days else "PENDING",
            "profitable_days_count": profitable_days_count,
            "min_profitable_day_usd": min_prof_usd,
            "days_traded": days_traded,
        }
    else:
        min_days_rule = {
            "id": "min_trading_days",
            "label": (
                f"Ngày giao dịch tối thiểu ({min_days} ngày)"
                if min_days > 0
                else "Ngày giao dịch tối thiểu (Không yêu cầu)"
            ),
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
            "label": (
                f"Mục tiêu lợi nhuận (+{target_usd:,.0f} USD)"
                if target_usd
                else "Mục tiêu lợi nhuận (Tài khoản Funded)"
            ),
            "value_text": (
                f"{total_pnl_usd:+,.2f} USD ({total_pnl_usd / max(1.0, init_usd) * 100.0:+.2f}%)"
                if target_usd
                else f"{total_pnl_usd:+,.2f} USD"
            ),
            "status": (
                "FUNDED"
                if target_usd is None
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
    mt5_run_raw = cloud_node.get("mt5_running") if cloud_node is not None else None
    mt5_run: bool | None = bool(mt5_run_raw) if mt5_run_raw is not None else None
    risk_attribution = _build_prop_risk_attribution(
        kill_sw=kill_sw,
        orphan_cnt=orphan_cnt,
        age_sec=age_sec,
        mt5_running=mt5_run,
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
            cal_cells.append({
                "empty": False,
                "day_num": dnum,
                "day": dk,
                "has_trade": False,
                "pnl_usd": None,
                "state": "IDLE",
            })

    active_meta_src = (
        cloud_node if (cloud_node is not None and cloud_eq is not None) else (local_hb if local_hb else {})
    )
    return {
        "schema": "naqex-prop-metrix-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "program": prog,
        "available_programs": [{"id": k, "label": v["label"]} for k, v in PROP_METRIX_PROGRAMS.items()],
        "source": {
            "label": source_label,
            "status": source_status,
            "age_sec": age_sec,
            "mt5_running": mt5_run,
            "account_login": active_meta_src.get("account_login"),
            "account_server": active_meta_src.get("account_server"),
            "build_version": active_meta_src.get("build_version"),
            "positions_state": active_meta_src.get("positions_state")
            or ("CONFIRMED" if source_status == "OK" else "UNKNOWN"),
            "anchor_state": active_meta_src.get("anchor_state"),
            "manual_halt_ack": active_meta_src.get("manual_halt_ack"),
            "read_only_note": (
                "Read-only mirror; verify broker statement/terminal before treating positions as flat or closed."
            ),
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
