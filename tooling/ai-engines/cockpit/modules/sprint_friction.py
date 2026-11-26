"""Black Friday Sprint Mũi 1-2 live calibration CSV progress and realized friction/spreads loaders."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import numpy as np
from cockpit.modules.helpers import (
    _coerce_opt_float,
    _coerce_opt_int,
    _extract_first_float,
    _extract_first_int,
    _read_jsonl_tail,
    _safe_read_json,
    _sanitize_short_token,
    as_dict,
)
from cockpit.modules.state import CORE_DEV_SPREAD_BASELINE_BPS


def _load_live_calibration_progress(root: Path, *, target_round_trips: int = 28) -> dict[str, Any]:
    """Read-only parser for `.runtime/live-overnight/ftmo_calibration_fills_1515343318.csv` with partial-line safety."""
    csv_path = root / ".runtime/live-overnight/ftmo_calibration_fills_1515343318.csv"
    per_sym_default: dict[str, dict[str, Any]] = {
        sym: {"completed": 0, "open": 0, "target": 7, "legs": 0, "mean_slip_bps": None}
        for sym in CORE_DEV_SPREAD_BASELINE_BPS
    }
    empty_payload: dict[str, Any] = {
        "status": "pending",
        "available": False,
        "completed_round_trips": 0,
        "target_round_trips": target_round_trips,
        "progress_pct": 0.0,
        "open_in_progress_count": 0,
        "valid_legs_count": 0,
        "rejected_count": 0,
        "skipped_partial_rows": 0,
        "mean_adverse_slip_pts": None,
        "max_adverse_slip_pts": None,
        "mean_adverse_slip_bps": None,
        "max_adverse_slip_bps": None,
        "median_latency_ms": None,
        "p90_latency_ms": None,
        "swap_total_usd": 0.0,
        "swap_zero_ok": True,
        "latest_fill_utc": None,
        "per_symbol_fills": per_sym_default,
    }
    if not csv_path.is_file():
        return empty_payload

    try:
        raw_text = csv_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return empty_payload

    lines = [ln for ln in raw_text.splitlines() if ln.strip()]
    if len(lines) < 2:
        return empty_payload

    try:
        header = [h.strip() for h in next(csv.reader([lines[0]]))]
    except Exception:
        return empty_payload
    if "symbol" not in header or "leg" not in header:
        return empty_payload

    expected_cols = len(header)
    skipped_partial = 0
    rejected_count = 0
    valid_legs = 0
    slip_pts_vals: list[float] = []
    slip_bps_vals: list[float] = []
    lat_vals: list[float] = []
    swap_vals: list[float] = []
    latest_fill_utc: str | None = None

    trades_by_key: dict[str, dict[str, Any]] = {}
    sym_slip_bps: dict[str, list[float]] = {sym: [] for sym in CORE_DEV_SPREAD_BASELINE_BPS}
    sym_legs: dict[str, int] = {sym: 0 for sym in CORE_DEV_SPREAD_BASELINE_BPS}

    for idx, raw_ln in enumerate(lines[1:], start=1):
        try:
            fields = next(csv.reader([raw_ln]))
        except Exception:
            skipped_partial += 1
            continue
        if len(fields) != expected_cols:
            skipped_partial += 1
            continue
        r = dict(zip(header, fields, strict=False))
        if str(r.get("dry_run") or "").strip().lower() in ("true", "1", "yes"):
            continue
        sym = _sanitize_short_token(r.get("symbol"), "", 24)
        leg = str(r.get("leg") or "").strip().upper()
        utc_ts = _coerce_opt_int(r.get("utc_ts"))
        if not sym or leg not in ("ENTRY", "EXIT", "ENTRY_REJECT", "EXIT_REJECT") or utc_ts is None or utc_ts <= 0:
            skipped_partial += 1
            continue

        retcode = _coerce_opt_int(r.get("retcode"))
        if leg.endswith("_REJECT") or (retcode is not None and retcode != 10009):
            rejected_count += 1
            continue

        valid_legs += 1
        sym_legs[sym] = sym_legs.get(sym, 0) + 1
        utc_iso = _sanitize_short_token(r.get("utc_iso"), "", 40)
        if utc_iso:
            latest_fill_utc = utc_iso

        s_pts = _coerce_opt_float(r.get("adverse_slip_pts"), 4)
        s_bps = _coerce_opt_float(r.get("adverse_slip_bps"), 4)
        lat_ms = _coerce_opt_float(r.get("latency_ms"), 2)
        swap_u = _coerce_opt_float(r.get("swap_usd"), 4)
        if s_pts is not None:
            slip_pts_vals.append(s_pts)
        if s_bps is not None:
            slip_bps_vals.append(s_bps)
            sym_slip_bps.setdefault(sym, []).append(s_bps)
        if lat_ms is not None and lat_ms > 0.0:
            lat_vals.append(lat_ms)
        if swap_u is not None:
            swap_vals.append(swap_u)

        tseq = str(r.get("trade_seq") or "").strip()
        pos_id = str(r.get("position_id") or "").strip()
        tkey = f"{sym}|seq:{tseq}|pos:{pos_id}" if (tseq or pos_id) else f"{sym}|row:{idx}"
        rec = trades_by_key.setdefault(tkey, {"symbol": sym, "has_entry": False, "has_exit": False})
        if leg == "ENTRY":
            rec["has_entry"] = True
        elif leg == "EXIT":
            rec["has_exit"] = True

    completed_rt = sum(1 for tr in trades_by_key.values() if tr["has_exit"])
    open_in_prog = sum(1 for tr in trades_by_key.values() if tr["has_entry"] and not tr["has_exit"])

    per_sym_out: dict[str, dict[str, Any]] = {}
    all_syms = list(CORE_DEV_SPREAD_BASELINE_BPS.keys()) + sorted(
        s
        for s in (set(sym_legs.keys()) | {str(tr["symbol"]) for tr in trades_by_key.values()})
        if s not in CORE_DEV_SPREAD_BASELINE_BPS
    )
    for sym in all_syms:
        comp_s = sum(1 for tr in trades_by_key.values() if tr["symbol"] == sym and tr["has_exit"])
        open_s = sum(
            1 for tr in trades_by_key.values() if tr["symbol"] == sym and tr["has_entry"] and not tr["has_exit"]
        )
        sb_arr = sym_slip_bps.get(sym, [])
        per_sym_out[sym] = {
            "completed": comp_s,
            "open": open_s,
            "target": 7,
            "legs": sym_legs.get(sym, 0),
            "mean_slip_bps": round(float(np.mean(sb_arr)), 2) if sb_arr else None,
        }

    swap_total = round(float(sum(swap_vals)), 4) if swap_vals else 0.0
    swap_zero_ok = all(abs(x) <= 1e-6 for x in swap_vals) if swap_vals else True

    if completed_rt >= target_round_trips:
        status_str = "COMPLETED"
    elif completed_rt > 0 or open_in_prog > 0 or valid_legs > 0:
        status_str = "IN_PROGRESS"
    else:
        status_str = "pending"

    return {
        "status": status_str,
        "available": valid_legs > 0,
        "completed_round_trips": completed_rt,
        "target_round_trips": target_round_trips,
        "progress_pct": round(min(100.0, 100.0 * completed_rt / max(1, target_round_trips)), 1),
        "open_in_progress_count": open_in_prog,
        "valid_legs_count": valid_legs,
        "rejected_count": rejected_count,
        "skipped_partial_rows": skipped_partial,
        "mean_adverse_slip_pts": round(float(np.mean(slip_pts_vals)), 2) if slip_pts_vals else None,
        "max_adverse_slip_pts": round(float(np.max(slip_pts_vals)), 2) if slip_pts_vals else None,
        "mean_adverse_slip_bps": round(float(np.mean(slip_bps_vals)), 2) if slip_bps_vals else None,
        "max_adverse_slip_bps": round(float(np.max(slip_bps_vals)), 2) if slip_bps_vals else None,
        "median_latency_ms": round(float(np.median(lat_vals)), 1) if lat_vals else None,
        "p90_latency_ms": round(float(np.percentile(lat_vals, 90)), 1) if lat_vals else None,
        "swap_total_usd": swap_total,
        "swap_zero_ok": swap_zero_ok,
        "latest_fill_utc": latest_fill_utc,
        "per_symbol_fills": per_sym_out,
    }


def _load_mui1_mui2_friction_and_spreads(root: Path) -> dict[str, Any]:
    live_dir = root / ".runtime/live-overnight"
    friction_path = live_dir / "ftmo_realized_friction_summary_20261125.json"
    spread_path = live_dir / "mt5_live_spread_log.jsonl"

    calibration_progress = _load_live_calibration_progress(root)
    friction_raw = _safe_read_json(friction_path)
    friction_by_sym: dict[str, dict[str, Any]] = {}
    friction_block: dict[str, Any]
    if isinstance(friction_raw, dict):
        overall = as_dict(friction_raw.get("overall"))
        rf_sub = as_dict(friction_raw.get("realized_friction"))
        port_c4 = as_dict(friction_raw.get("portfolio_core4"))
        inputs_sub = as_dict(friction_raw.get("inputs"))
        merged_top = {**rf_sub, **overall, **port_c4, **friction_raw}

        fills_count = _extract_first_int(
            merged_top, ("fills_count", "total_fills", "n_fills", "trades_count", "closed_trades")
        )
        rf_by_sym_raw = friction_raw.get("realized_friction_by_symbol")
        if fills_count is None and isinstance(rf_by_sym_raw, dict):
            paired_sum = sum(
                int(v.get("paired_roundtrips") or v.get("exits") or 0)
                for v in rf_by_sym_raw.values()
                if isinstance(v, dict)
            )
            if paired_sum > 0:
                fills_count = paired_sum
        if fills_count is None:
            fills_count = _extract_first_int(inputs_sub, ("live_fill_legs_total",))
        if fills_count is None:
            fills_count = int(calibration_progress["completed_round_trips"])

        p50_mult = _extract_first_float(
            merged_top,
            (
                "realized_friction_multiplier_p50",
                "realized_friction_mult_p50",
                "friction_multiplier_p50",
                "p50_friction_multiplier",
                "friction_mult_p50",
                "p50_mult",
            ),
            2,
        )
        p90_mult = _extract_first_float(
            merged_top,
            (
                "realized_friction_multiplier_p90",
                "realized_friction_mult_p90",
                "friction_multiplier_p90",
                "p90_friction_multiplier",
                "friction_mult_p90",
                "p90_mult",
            ),
            2,
        )
        p50_slip_bps = _extract_first_float(
            merged_top,
            ("adverse_slippage_p50_bps", "slippage_p50_bps", "p50_slippage_bps", "median_slippage_bps"),
            2,
        )
        p90_slip_bps = _extract_first_float(
            merged_top, ("adverse_slippage_p90_bps", "slippage_p90_bps", "p90_slippage_bps"), 2
        )

        # Native ftmo_demo_calibration_probe.py schema (`spread_vs_dev_m1` + `realized_friction_by_symbol`)
        sp_vs_dev = as_dict(friction_raw.get("spread_vs_dev_m1"))
        rf_by_sym = as_dict(rf_by_sym_raw)
        raw_by_sym = as_dict(
            friction_raw.get("by_symbol")
            or friction_raw.get("symbols")
            or friction_raw.get("spread_ratios_by_symbol")
        )
        sym_keys_union: list[str] = []
        for src_d in (rf_by_sym, sp_vs_dev, raw_by_sym):
            for k in src_d:
                if k not in sym_keys_union:
                    sym_keys_union.append(k)

        for sym_k in sym_keys_union:
            rec_flat = as_dict(raw_by_sym.get(sym_k))
            rec_rf = as_dict(rf_by_sym.get(sym_k))
            rec_sp_ov = as_dict(as_dict(sp_vs_dev.get(sym_k)).get("OVERALL"))
            merged_sym = {**rec_sp_ov, **rec_rf, **rec_flat}
            sym_clean = _sanitize_short_token(sym_k, "SYM", 24)
            friction_by_sym[sym_clean] = {
                "fills_count": _extract_first_int(
                    merged_sym, ("paired_roundtrips", "fills_count", "exits", "n_fills", "trades", "count")
                ),
                "live_median_spread_bps": _extract_first_float(
                    merged_sym,
                    (
                        "live_median_spread_bps",
                        "live_spread_p50_bps",
                        "median_spread_bps",
                        "live_spread_bps",
                        "spread_p50_bps",
                    ),
                    2,
                ),
                "live_p90_spread_bps": _extract_first_float(
                    merged_sym, ("live_p90_spread_bps", "live_spread_p90_bps", "p90_spread_bps", "spread_p90_bps"), 2
                ),
                "dev_median_spread_bps": _extract_first_float(
                    merged_sym,
                    (
                        "dev_m1_median_spread_bps",
                        "dev_median_spread_bps",
                        "dev_m1_spread_bps",
                        "dev_baseline_bps",
                        "budget_bps",
                    ),
                    2,
                ),
                "spread_ratio_vs_dev": _extract_first_float(
                    merged_sym,
                    (
                        "live_to_dev_spread_ratio_bps",
                        "spread_ratio_vs_dev",
                        "live_to_dev_spread_ratio",
                        "spread_ratio",
                        "ratio_vs_dev_1x",
                    ),
                    2,
                ),
                "friction_mult_p50": _extract_first_float(
                    merged_sym,
                    ("realized_friction_multiplier_p50", "realized_friction_mult_p50", "friction_mult_p50", "p50_mult"),
                    2,
                ),
                "friction_mult_p90": _extract_first_float(
                    merged_sym,
                    ("realized_friction_multiplier_p90", "realized_friction_mult_p90", "friction_mult_p90", "p90_mult"),
                    2,
                ),
            }

        raw_by_sess = friction_raw.get("by_session")
        by_session_clean: dict[str, dict[str, Any]] = {}
        if isinstance(raw_by_sess, dict):
            for sess_k, rec in raw_by_sess.items():
                if not isinstance(rec, dict):
                    continue
                sk = _sanitize_short_token(sess_k, "SESSION", 24)
                by_session_clean[sk] = {
                    "samples": _extract_first_int(rec, ("samples", "count", "n_samples")),
                    "median_spread_bps": _extract_first_float(rec, ("median_spread_bps", "live_median_spread_bps"), 2),
                    "spread_ratio_vs_dev": _extract_first_float(rec, ("spread_ratio_vs_dev", "ratio_vs_dev_1x"), 2),
                }

        friction_block = {
            "status": "AVAILABLE",
            "available": True,
            "generated_utc": _sanitize_short_token(friction_raw.get("generated_utc"), "", 40) or None,
            "verdict": _sanitize_short_token(merged_top.get("verdict") or merged_top.get("status"), "RECORDED", 32),
            "fills_count": fills_count,
            "p50_friction_mult": p50_mult,
            "p90_friction_mult": p90_mult,
            "p50_slippage_bps": p50_slip_bps,
            "p90_slippage_bps": p90_slip_bps,
            "latency_p50_ms": _extract_first_float(merged_top, ("latency_p50_ms",), 1),
            "by_session": by_session_clean,
        }
    else:
        friction_block = {
            "status": "pending",
            "available": False,
            "generated_utc": None,
            "verdict": "PENDING",
            "fills_count": 0,
            "p50_friction_mult": None,
            "p90_friction_mult": None,
            "p50_slippage_bps": None,
            "p90_slippage_bps": None,
            "latency_p50_ms": None,
            "by_session": {},
        }

    # Aggregate live spreads from mt5_live_spread_log.jsonl (last 2000 samples)
    spread_rows = _read_jsonl_tail(spread_path, limit=2000)
    sym_bps: dict[str, list[float]] = {}
    latest_cap_utc: str | None = None
    for row in spread_rows:
        cap = row.get("captured_utc") or row.get("timestamp_utc")
        if isinstance(cap, str) and cap.strip():
            latest_cap_utc = _sanitize_short_token(cap, "", 40)
        quotes = row.get("quotes")
        if isinstance(quotes, dict):
            for sym, q in quotes.items():
                if not isinstance(q, dict):
                    continue
                sp_bps = _coerce_opt_float(q.get("spread_bps"), 4)
                if sp_bps is None:
                    bid = _coerce_opt_float(q.get("bid"), 8)
                    ask = _coerce_opt_float(q.get("ask"), 8)
                    if bid is not None and ask is not None and bid > 0.0 and ask >= bid:
                        mid = 0.5 * (bid + ask)
                        sp_bps = ((ask - bid) / mid) * 10_000.0
                if sp_bps is not None and sp_bps >= 0.0:
                    sym_bps.setdefault(str(sym), []).append(float(sp_bps))
        elif row.get("symbol"):
            sym = str(row["symbol"])
            sp_bps = _coerce_opt_float(row.get("spread_bps"), 4)
            if sp_bps is None:
                bid = _coerce_opt_float(row.get("bid"), 8)
                ask = _coerce_opt_float(row.get("ask"), 8)
                if bid is not None and ask is not None and bid > 0.0 and ask >= bid:
                    sp_bps = ((ask - bid) / (0.5 * (bid + ask))) * 10_000.0
            if sp_bps is not None and sp_bps >= 0.0:
                sym_bps.setdefault(sym, []).append(float(sp_bps))

    ordered_syms: list[str] = list(CORE_DEV_SPREAD_BASELINE_BPS.keys())
    for extra in sorted(set(friction_by_sym.keys()) | set(sym_bps.keys())):
        if extra not in ordered_syms and extra in friction_by_sym:
            ordered_syms.append(extra)

    calib_by_sym = as_dict(calibration_progress.get("per_symbol_fills"))
    symbol_rows: list[dict[str, Any]] = []
    for sym in ordered_syms:
        arr = sym_bps.get(sym, [])
        frec = friction_by_sym.get(sym, {})
        crec = as_dict(calib_by_sym.get(sym))
        med_bps = frec.get("live_median_spread_bps")
        p90_bps = frec.get("live_p90_spread_bps")
        if med_bps is None and arr:
            med_bps = round(float(np.median(arr)), 2)
        if p90_bps is None and arr:
            p90_bps = round(float(np.percentile(arr, 90)), 2)
        dev_base = frec.get("dev_median_spread_bps") or CORE_DEV_SPREAD_BASELINE_BPS.get(sym)
        ratio = frec.get("spread_ratio_vs_dev")
        if ratio is None and med_bps is not None and dev_base and dev_base > 0.0:
            ratio = round(float(med_bps) / float(dev_base), 2)
        fills_sym = frec.get("fills_count")
        crec_comp = int(crec.get("completed", 0))
        crec_open = int(crec.get("open", 0))
        if fills_sym is None and crec and (crec_comp > 0 or crec_open > 0):
            fills_sym = crec_comp
        if not arr and not frec and not (crec and (crec_comp > 0 or crec_open > 0)):
            continue
        symbol_rows.append({
            "symbol": sym,
            "samples": len(arr),
            "fills_count": fills_sym,
            "live_median_spread_bps": med_bps,
            "live_p90_spread_bps": p90_bps,
            "dev_baseline_bps": dev_base,
            "ratio_vs_dev_1x": ratio,
            "friction_mult_p50": frec.get("friction_mult_p50"),
            "friction_mult_p90": frec.get("friction_mult_p90"),
        })

    return {
        "realized_friction": friction_block,
        "calibration_progress": calibration_progress,
        "live_spreads": {
            "status": "ACTIVE" if spread_rows else "pending",
            "available": bool(spread_rows),
            "samples_count": len(spread_rows),
            "latest_captured_utc": latest_cap_utc,
        },
        "symbol_table": symbol_rows,
    }
