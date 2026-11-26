"""Offline `--summarize`: live vs Dev M1 spread ratios and Realized Friction Multiplier."""

from __future__ import annotations

import csv
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from exports.calibration_probe.baselines import compute_dev_m1_spread_baselines
from exports.calibration_probe.constants import (
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    CORE_SYMBOLS,
    DEFAULT_FILLS_CSV,
    DEFAULT_HOLDOUT_LOCK_JSON,
    DEFAULT_HOT_M1_CACHE,
    DEFAULT_SPREAD_LOG,
    DEFAULT_SUMMARY_JSON,
    SESSION_ORDER,
    SYMBOL_META,
)
from exports.calibration_probe.models import SafetyLockError
from exports.calibration_probe.validators import is_past_flatten_cutoff, tag_session_utc
from quant_core.io_utils import atomic_write_json
from quant_factory import prop_challenge_tracker as pct


def _percentile(vals: list[float], pct_val: float) -> float:
    if not vals:
        return 0.0
    return float(np.percentile(np.asarray(vals, dtype=np.float64), pct_val))


def _aggregate_live_spread_comparison(
    spread_rows: list[dict[str, Any]],
    dev_base: dict[str, Any],
) -> tuple[dict[str, dict[str, Any]], set[int]]:
    live_spreads: dict[str, dict[str, dict[str, list[float]]]] = {
        sym: {s: {"pts": [], "bps": [], "px": []} for s in (*SESSION_ORDER, "OVERALL")} for sym in CORE_SYMBOLS
    }
    logins_in_spread_log: set[int] = set()

    for row in spread_rows:
        acct = row.get("account")
        if isinstance(acct, dict) and acct.get("login"):
            logins_in_spread_log.add(int(acct["login"]))
        ts_val = int(row.get("captured_utc_ts") or 0)
        sess = str(row.get("session") or "").strip().upper()
        if sess not in SESSION_ORDER:
            sess = tag_session_utc(datetime.fromtimestamp(ts_val, UTC)) if ts_val > 0 else "ASIA"
        quotes = row.get("quotes")
        if not isinstance(quotes, dict):
            continue
        for sym in CORE_SYMBOLS:
            q = quotes.get(sym)
            if not isinstance(q, dict) or not q.get("available"):
                continue
            bid = float(q.get("bid") or 0.0)
            ask = float(q.get("ask") or 0.0)
            if bid <= 0.0 or ask <= 0.0 or ask < bid:
                continue
            pt = float(q.get("point") or SYMBOL_META[sym]["point"])
            sp_px = ask - bid
            mid = 0.5 * (ask + bid)
            raw_pts = q.get("spread_pts")
            raw_bps = q.get("spread_bps")
            sp_pts = float(raw_pts) if raw_pts is not None else (sp_px / pt)
            sp_bps = float(raw_bps) if raw_bps is not None else ((sp_px / mid) * 10_000.0)
            for bucket in (sess, "OVERALL"):
                live_spreads[sym][bucket]["pts"].append(sp_pts)
                live_spreads[sym][bucket]["bps"].append(sp_bps)
                live_spreads[sym][bucket]["px"].append(sp_px)

    spread_comparison: dict[str, dict[str, Any]] = {}
    for sym in CORE_SYMBOLS:
        dev_sym = dev_base["by_symbol"][sym]
        sym_out: dict[str, Any] = {}
        for sess in (*SESSION_ORDER, "OVERALL"):
            pts_arr = live_spreads[sym][sess]["pts"]
            bps_arr = live_spreads[sym][sess]["bps"]
            dev_s = dev_sym["sessions"][sess]
            if not pts_arr:
                sym_out[sess] = {
                    "live_samples": 0,
                    "live_median_spread_pts": None,
                    "live_p90_spread_pts": None,
                    "live_median_spread_bps": None,
                    "live_p90_spread_bps": None,
                    "dev_m1_median_spread_pts": dev_s["median_spread_pts"],
                    "dev_m1_median_spread_bps": dev_s["median_spread_bps"],
                    "live_to_dev_spread_ratio_pts": None,
                    "live_to_dev_spread_ratio_bps": None,
                }
                continue
            l_med_pts = _percentile(pts_arr, 50)
            l_p90_pts = _percentile(pts_arr, 90)
            l_med_bps = _percentile(bps_arr, 50)
            l_p90_bps = _percentile(bps_arr, 90)
            d_med_pts = float(dev_s["median_spread_pts"])
            d_med_bps = float(dev_s["median_spread_bps"])
            sym_out[sess] = {
                "live_samples": len(pts_arr),
                "live_median_spread_pts": round(l_med_pts, 3),
                "live_p90_spread_pts": round(l_p90_pts, 3),
                "live_median_spread_bps": round(l_med_bps, 4),
                "live_p90_spread_bps": round(l_p90_bps, 4),
                "dev_m1_median_spread_pts": round(d_med_pts, 3),
                "dev_m1_median_spread_bps": round(d_med_bps, 4),
                "live_to_dev_spread_ratio_pts": round(l_med_pts / d_med_pts, 3) if d_med_pts > 0 else None,
                "live_to_dev_spread_ratio_bps": round(l_med_bps / d_med_bps, 3) if d_med_bps > 0 else None,
            }
        spread_comparison[sym] = sym_out
    return spread_comparison, logins_in_spread_log


def _parse_live_fills_csv(fills_csv_path: Path) -> tuple[list[dict[str, Any]], int, int, int, int]:
    live_fills: list[dict[str, Any]] = []
    dryrun_rows_ignored = 0
    reject_rows = 0
    swap_nonzero_count = 0
    after_cutoff_count = 0

    if not fills_csv_path.is_file():
        return live_fills, dryrun_rows_ignored, reject_rows, swap_nonzero_count, after_cutoff_count

    with fills_csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            if str(r.get("dry_run", "")).strip().lower() in ("true", "1", "yes"):
                dryrun_rows_ignored += 1
                continue
            leg = str(r.get("leg", "")).strip().upper()
            if leg == "ENTRY_REJECT" or int(float(r.get("retcode") or 0)) != 10009:
                reject_rows += 1
                continue
            if leg not in ("ENTRY", "EXIT"):
                continue
            ts_val = int(float(r.get("utc_ts") or 0))
            if ts_val > 0 and is_past_flatten_cutoff(datetime.fromtimestamp(ts_val, UTC)):
                after_cutoff_count += 1
            sw = float(r.get("swap_usd") or 0.0)
            if abs(sw) > 1e-6:
                swap_nonzero_count += 1
            live_fills.append(
                {
                    "utc_ts": ts_val,
                    "session": str(r.get("session") or ""),
                    "trade_seq": int(float(r.get("trade_seq") or 0)),
                    "position_id": str(r.get("position_id") or ""),
                    "symbol": str(r.get("symbol") or "").strip(),
                    "leg": leg,
                    "side": str(r.get("side") or "").strip().upper(),
                    "exit_reason": str(r.get("exit_reason") or "").strip().upper(),
                    "pre_spread_bps": float(r.get("pre_spread_bps") or 0.0),
                    "adverse_slip_pts": float(r.get("adverse_slip_pts") or 0.0),
                    "adverse_slip_bps": float(r.get("adverse_slip_bps") or 0.0),
                    "latency_ms": float(r.get("latency_ms") or 0.0),
                    "commission_usd": float(r.get("commission_usd") or 0.0),
                    "commission_bps": float(r.get("commission_bps") or 0.0),
                    "swap_usd": sw,
                    "pnl_usd": float(r.get("pnl_usd") or 0.0),
                }
            )
    return live_fills, dryrun_rows_ignored, reject_rows, swap_nonzero_count, after_cutoff_count


def _compute_symbol_realized_friction(
    sym_fills: list[dict[str, Any]],
    *,
    dev_budget: dict[str, Any],
    ov_sp: dict[str, Any],
) -> tuple[dict[str, Any], float | None, float | None, list[float]]:
    entries = [x for x in sym_fills if x["leg"] == "ENTRY"]
    exits = [x for x in sym_fills if x["leg"] == "EXIT"]
    sl_exits = [x for x in exits if x["exit_reason"] == "SL_HIT"]
    dev_1x_rt_bps = float(dev_budget["total_1x_rt_bps"])

    # Pair round-trips by position_id (falling back to trade_seq)
    ent_by_key = {(x["position_id"] or str(x["trade_seq"])): x for x in entries}
    rt_slips_signed: list[float] = []
    rt_slips_pos: list[float] = []
    rt_comm_bps: list[float] = []
    rt_spreads_bps: list[float] = []
    for ex in exits:
        k = ex["position_id"] or str(ex["trade_seq"])
        en = ent_by_key.get(k)
        if en is not None:
            rt_slips_signed.append(en["adverse_slip_bps"] + ex["adverse_slip_bps"])
            rt_slips_pos.append(max(0.0, en["adverse_slip_bps"]) + max(0.0, ex["adverse_slip_bps"]))
            rt_comm_bps.append(en["commission_bps"] + ex["commission_bps"])
            rt_spreads_bps.append(0.5 * (en["pre_spread_bps"] + ex["pre_spread_bps"]))

    # Fallback if entries exist without paired exits yet
    if not rt_slips_signed and sym_fills:
        rt_slips_signed = [2.0 * x["adverse_slip_bps"] for x in sym_fills]
        rt_slips_pos = [2.0 * max(0.0, x["adverse_slip_bps"]) for x in sym_fills]
        rt_comm_bps = [2.0 * x["commission_bps"] for x in sym_fills]
        rt_spreads_bps = [x["pre_spread_bps"] for x in sym_fills]

    # Live spread (prefer continuous 5s spread recorder OVERALL; fallback to fill pre-trade spreads)
    live_sp_p50 = (
        float(ov_sp["live_median_spread_bps"])
        if ov_sp["live_median_spread_bps"] is not None
        else (_percentile(rt_spreads_bps, 50) if rt_spreads_bps else 0.0)
    )
    live_sp_p90 = (
        float(ov_sp["live_p90_spread_bps"])
        if ov_sp["live_p90_spread_bps"] is not None
        else (_percentile(rt_spreads_bps, 90) if rt_spreads_bps else 0.0)
    )
    lat_list = [x["latency_ms"] for x in sym_fills if x["latency_ms"] > 0.0]

    if not sym_fills:
        return (
            {
                "entries": 0,
                "exits": 0,
                "sl_exits": 0,
                "live_spread_p50_bps": round(live_sp_p50, 4) if ov_sp["live_samples"] > 0 else None,
                "live_spread_p90_bps": round(live_sp_p90, 4) if ov_sp["live_samples"] > 0 else None,
                "dev_1x_budget_rt_bps": round(dev_1x_rt_bps, 4),
                "realized_friction_multiplier_p50": None,
                "realized_friction_multiplier_p90": None,
                "status": "NO_LIVE_FILLS_YET",
            },
            None,
            None,
            lat_list,
        )

    slip_p50_pos = _percentile(rt_slips_pos, 50)
    slip_p90_pos = _percentile(rt_slips_pos, 90)
    slip_p50_signed = _percentile(rt_slips_signed, 50)
    slip_p90_signed = _percentile(rt_slips_signed, 90)
    comm_p50 = _percentile(rt_comm_bps, 50)

    # Conservative positive-adverse friction AND signed net friction
    realized_rt_p50_bps = live_sp_p50 + comm_p50 + slip_p50_pos
    realized_rt_p90_bps = live_sp_p90 + comm_p50 + slip_p90_pos
    realized_rt_p50_signed_bps = live_sp_p50 + comm_p50 + slip_p50_signed

    mult_p50 = realized_rt_p50_bps / max(1e-6, dev_1x_rt_bps)
    mult_p90 = realized_rt_p90_bps / max(1e-6, dev_1x_rt_bps)

    sl_slips = [x["adverse_slip_bps"] for x in sl_exits]
    ent_slips = [x["adverse_slip_bps"] for x in entries]
    exit_slips = [x["adverse_slip_bps"] for x in exits]

    status = (
        "BREACH_ABOVE_2_0X"
        if mult_p50 > 2.0
        else ("WARN_ELEVATED_1_5X_TO_2_0X" if mult_p50 > 1.5 else "PASS_WITHIN_1_5X")
    )
    record = {
        "entries": len(entries),
        "exits": len(exits),
        "paired_roundtrips": len(rt_slips_pos),
        "sl_exits": len(sl_exits),
        "sl_adverse_slip_p50_bps": round(_percentile(sl_slips, 50), 4) if sl_slips else None,
        "sl_adverse_slip_p90_bps": round(_percentile(sl_slips, 90), 4) if sl_slips else None,
        "entry_adverse_slip_p50_bps": round(_percentile(ent_slips, 50), 4) if ent_slips else None,
        "exit_adverse_slip_p50_bps": round(_percentile(exit_slips, 50), 4) if exit_slips else None,
        "rt_adverse_slip_p50_pos_bps": round(slip_p50_pos, 4),
        "rt_adverse_slip_p90_pos_bps": round(slip_p90_pos, 4),
        "rt_adverse_slip_p50_signed_bps": round(slip_p50_signed, 4),
        "rt_adverse_slip_p90_signed_bps": round(slip_p90_signed, 4),
        "live_spread_p50_bps": round(live_sp_p50, 4),
        "live_spread_p90_bps": round(live_sp_p90, 4),
        "commission_rt_p50_bps": round(comm_p50, 4),
        "realized_rt_friction_p50_bps": round(realized_rt_p50_bps, 4),
        "realized_rt_friction_p90_bps": round(realized_rt_p90_bps, 4),
        "realized_rt_friction_p50_signed_bps": round(realized_rt_p50_signed_bps, 4),
        "dev_1x_budget_rt_bps": round(dev_1x_rt_bps, 4),
        "tracker_budget_rt_bps": round(float(dev_budget["tracker_budget_rt_bps"]), 4),
        "realized_friction_multiplier_p50": round(mult_p50, 3),
        "realized_friction_multiplier_p90": round(mult_p90, 3),
        "latency_p50_ms": round(_percentile(lat_list, 50), 2) if lat_list else None,
        "latency_p90_ms": round(_percentile(lat_list, 90), 2) if lat_list else None,
        "net_pnl_usd": round(sum(x["pnl_usd"] for x in exits), 4),
        "total_commission_usd": round(sum(x["commission_usd"] for x in sym_fills), 4),
        "total_swap_usd": round(sum(x["swap_usd"] for x in sym_fills), 4),
        "status": status,
    }
    return record, mult_p50, mult_p90, lat_list


def summarize_calibration_and_spreads(
    *,
    spread_log_path: Path = DEFAULT_SPREAD_LOG,
    fills_csv_path: Path = DEFAULT_FILLS_CSV,
    summary_json_path: Path | None = DEFAULT_SUMMARY_JSON,
    hot_cache_dir: Path = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    dev_m1_baselines: dict[str, Any] | None = None,
    verify_dev_sha: bool = False,
) -> dict[str, Any]:
    """Compute FTMO Live Spread / Dev M1 Spread ratios & Realized Friction Multiplier (OrderSend=0, holdout=0)."""
    dev_base = (
        dev_m1_baselines
        if dev_m1_baselines is not None
        else compute_dev_m1_spread_baselines(
            hot_cache_dir=hot_cache_dir,
            holdout_lock_path=holdout_lock_path,
            verify_sha=verify_dev_sha,
        )
    )
    if int(dev_base.get("holdout_rows_analysed", -1)) != 0:
        raise SafetyLockError("HOLDOUT_CONTAMINATION_DETECTED_IN_SUMMARY")

    spread_rows = pct.load_spread_log_rows(spread_log_path)
    spread_comparison, logins_in_spread_log = _aggregate_live_spread_comparison(spread_rows, dev_base)
    live_fills, dryrun_rows_ignored, reject_rows, swap_nonzero_count, after_cutoff_count = _parse_live_fills_csv(
        fills_csv_path
    )

    realized_friction: dict[str, dict[str, Any]] = {}
    all_mult_p50: list[float] = []
    all_mult_p90: list[float] = []
    all_latencies: list[float] = []

    for sym in CORE_SYMBOLS:
        sym_fills = [x for x in live_fills if x["symbol"] == sym]
        rec, mult_p50, mult_p90, lat_list = _compute_symbol_realized_friction(
            sym_fills,
            dev_budget=dev_base["by_symbol"][sym]["dev_1x_budget"],
            ov_sp=spread_comparison[sym]["OVERALL"],
        )
        realized_friction[sym] = rec
        all_latencies.extend(lat_list)
        if mult_p50 is not None and mult_p90 is not None:
            all_mult_p50.append(mult_p50)
            all_mult_p90.append(mult_p90)

    port_mult_p50 = round(float(np.mean(all_mult_p50)), 3) if all_mult_p50 else None
    port_mult_p90 = round(float(np.mean(all_mult_p90)), 3) if all_mult_p90 else None

    if not live_fills:
        overall_verdict = "PRE_TRADE_SPREAD_ONLY"
    elif swap_nonzero_count > 0 or after_cutoff_count > 0:
        overall_verdict = "COMPLIANCE_VIOLATION"
    elif port_mult_p50 is not None and port_mult_p50 > 2.0:
        overall_verdict = "BREACH_ABOVE_2_0X"
    elif port_mult_p50 is not None and port_mult_p50 > 1.5:
        overall_verdict = "WARN_ELEVATED_1_5X_TO_2_0X"
    else:
        overall_verdict = "PASS_WITHIN_1_5X"

    payload = {
        "schema": "naqex-ftmo-realized-friction-summary-v1",
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "order_send_count": 0,
        "calibration_account_login": ALLOWED_DEMO_LOGIN,
        "server": ALLOWED_SERVER,
        "holdout_lock_sha256": dev_base["holdout_lock_sha256"],
        "holdout_rows_analysed": int(dev_base["holdout_rows_analysed"]),
        "dev_m1_max_utc": dev_base.get("dev_m1_max_utc"),
        "verdict": overall_verdict,
        "inputs": {
            "spread_log_path": str(spread_log_path),
            "spread_log_rows_total": len(spread_rows),
            "spread_log_logins_observed": sorted(logins_in_spread_log),
            "fills_csv_path": str(fills_csv_path),
            "live_fill_legs_total": len(live_fills),
            "dryrun_rows_ignored": dryrun_rows_ignored,
            "rejected_orders": reject_rows,
        },
        "compliance": {
            "swap_nonzero_count": swap_nonzero_count,
            "after_2055_utc_count": after_cutoff_count,
            "zero_swap_ok": swap_nonzero_count == 0,
            "cutoff_ok": after_cutoff_count == 0,
        },
        "portfolio_core4": {
            "symbols_with_live_fills": len(all_mult_p50),
            "realized_friction_multiplier_p50": port_mult_p50,
            "realized_friction_multiplier_p90": port_mult_p90,
            "latency_p50_ms": round(_percentile(all_latencies, 50), 2) if all_latencies else None,
            "latency_p90_ms": round(_percentile(all_latencies, 90), 2) if all_latencies else None,
            "net_pnl_usd": round(sum(x["pnl_usd"] for x in live_fills if x["leg"] == "EXIT"), 4),
            "total_commission_usd": round(sum(x["commission_usd"] for x in live_fills), 4),
            "total_swap_usd": round(sum(x["swap_usd"] for x in live_fills), 4),
        },
        "spread_vs_dev_m1": spread_comparison,
        "realized_friction_by_symbol": realized_friction,
    }

    if summary_json_path is not None:
        atomic_write_json(summary_json_path, payload, indent=2, ensure_ascii=False)
    return payload
