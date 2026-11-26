"""Portfolio summary, multi-sleeve allocations, and unified Control Room overview payloads."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
from cockpit.modules.helpers import _downsample_series, _parse_pod_snapshot_md, _safe_read_json, as_dict
from cockpit.modules.state import (
    _SLEEVE1_LOCK,
    ORDER_SEND_COUNT,
    ROOT,
    get_sleeve1_cache,
    set_sleeve1_cache,
)
from cockpit.modules.stress import build_stress_payload
from cockpit.modules.telemetry import build_live_telemetry_payload
from quant_factory.portfolio_allocator import (
    align_sleeves_business_days,
    compute_series_metrics,
    load_external_sleeve_json,
)
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE


def _get_sleeve1_cached(root: Path) -> tuple[dict[str, float], dict[str, Any]] | None:
    if root != ROOT:
        return None
    with _SLEEVE1_LOCK:
        cached = get_sleeve1_cache()
        if cached is not None:
            return cached
        try:
            from quant_factory.portfolio_allocator import load_sleeve1_dev_daily_returns

            loaded = load_sleeve1_dev_daily_returns()
            set_sleeve1_cache(loaded)
            return loaded
        except Exception:
            return None


def build_summary_payload(root: Path = ROOT) -> dict[str, Any]:
    reg = as_dict(_safe_read_json(root / "planning/research/PORTFOLIO-REGISTRY.json"))
    red_team = as_dict(_safe_read_json(root / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json"))
    ftmo_live = _safe_read_json(root / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json")
    pod_snap = _parse_pod_snapshot_md(root / ".runtime/pod_dashboard_snapshot.md")
    holdout_lock = as_dict(reg.get("holdout_lock"))

    red_team_compact: dict[str, Any] = {}
    if red_team:
        t1 = as_dict(red_team.get("test1_cost_stress"))
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
        "generated_utc": datetime.now(UTC).isoformat(),
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
            "generated_utc": datetime.now(UTC).isoformat(),
            "order_send_count": ORDER_SEND_COUNT,
            "available": False,
            "window": {},
            "holdout_sealed": True,
            "sleeve_order": [],
            "sleeves": [],
            "pod_composite_metrics": {},
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
        "generated_utc": datetime.now(UTC).isoformat(),
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


def build_overview_payload(
    root: Path = ROOT,
    *,
    capital_usd: float = 50_000.0,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Unified Control Room overview aggregating summary, live overnight telemetry & Black-Swan stress."""
    return {
        "schema": "naqex-cockpit-overview-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "summary": build_summary_payload(root),
        "live_telemetry": build_live_telemetry_payload(root),
        "stress": build_stress_payload(root, capital_usd=capital_usd, usd_vnd_rate=usd_vnd_rate),
    }
