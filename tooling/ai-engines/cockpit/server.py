"""Naqex Quant Pod Local Interactive Web Control Room Server (`127.0.0.1:8787`, stdlib-only).

Zero external dependencies, zero external CDNs, strictly localhost-bound (`127.0.0.1`),
100% read-only on workspace state (`ORDER_SEND_COUNT = 0`, Holdout 2025+ SEALED).

Live JSON API endpoints:
  - GET  /                    -> Flat-dark institutional Cockpit UI (`static/index.html`)
  - GET  /static/<asset>      -> Static CSS/JS (`styles.css`, `app.js`) with path-traversal guard
  - GET  /api/health          -> Lightweight readiness check
  - GET  /api/summary         -> Safety seal, registry, pod snapshot, FTMO specs, Red-Team stress curve
  - GET  /api/allocations     -> Multi-sleeve equity/underwater curves (4-6+ sleeves), N×N corr matrix & metrics
  - GET  /api/live-telemetry  -> Live MT5 heartbeat/spreads, Crypto shadow, Real-Tick TCA, Red-News countdown
  - GET|POST /api/vnd-calculator -> PROFILE.md-calibrated VND/USD absolute risk, stress & crossover calculator
  - GET  /api/rebalancer      -> Dry-run Sleeve #3B IBKR Macro ETF weights & order tickets (`OrderSend = 0`)
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import math
from pathlib import Path
import re
import sys
import threading
from typing import Any
from urllib.parse import parse_qs, urlparse

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
from quant_factory.treasury_ledger import DEFAULT_USD_VND_RATE, compute_prop_own_crossover

ORDER_SEND_COUNT = 0
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

_SLEEVE1_LOCK = threading.Lock()
_SLEEVE1_CACHE: tuple[dict[str, float], dict[str, Any]] | None = None

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
                    dt_str = datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
                    upcoming.append({
                        "utc_ts": int(ts),
                        "utc_iso": dt_str,
                        "hours_away": round((ts - now_ts) / 3600.0, 1),
                        "ccy": str(r.get("ccy", "")).strip(),
                        "event": str(r.get("event", "")).strip(),
                    })
    except Exception:
        return []
    upcoming.sort(key=lambda x: x["utc_ts"])
    return upcoming[:limit]


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

    # Default ERC-inspired cap weights (or equal weight if dynamic sleeve count != 4)
    default_w_map = {
        "S1_PROP_FX_IDX": 0.24,
        "S2_CRYPTO_SPOT": 0.166,
        "S3A_FUND_CARRY": 0.35,
        "S3B_MACRO_ETF": 0.244,
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
    crypto_shadow = _read_jsonl_tail(overnight_dir / "crypto_shadow_log.jsonl", limit=20)

    # Discover any heartbeat JSONs (runtime overnight or deployment kit)
    heartbeat_data = None
    heartbeat_src = None
    for cand in (
        overnight_dir / "naqex_heartbeat.json",
        root / ".runtime/naqex_heartbeat.json",
    ):
        obj = _safe_read_json(cand)
        if isinstance(obj, dict):
            heartbeat_data = obj
            heartbeat_src = cand.relative_to(root).as_posix()
            break

    # Check MT5 Real-Tick vs Python TCA summary if Lane A has produced it
    realtick_summary = None
    if realtick_dir.is_dir():
        for name in ("mt5_vs_python_reconcile.json", "realtick_summary.json", "summary.json"):
            obj = _safe_read_json(realtick_dir / name)
            if obj is not None:
                realtick_summary = obj
                break
        if realtick_summary is None:
            files = sorted([p.name for p in realtick_dir.iterdir()])[:25]
            if files:
                realtick_summary = {"files_detected": files}

    ftmo_specs = _safe_read_json(root / "planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json")
    upcoming_news = _load_upcoming_red_news(root, limit=10)

    return {
        "schema": "naqex-cockpit-live-telemetry-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "mt5_heartbeat": {
            "status": "LIVE_HEARTBEAT" if heartbeat_data else "STANDBY_DRYRUN",
            "source": heartbeat_src,
            "data": heartbeat_data,
        },
        "mt5_live_spreads": {
            "status": "ACTIVE" if mt5_spreads else "STANDBY_AWAITING_MONITOR",
            "count": len(mt5_spreads),
            "latest": mt5_spreads[-1] if mt5_spreads else None,
            "recent": mt5_spreads[-8:],
        },
        "crypto_shadow": {
            "status": "ACTIVE" if crypto_shadow else "STANDBY_AWAITING_SHADOW_RUNNER",
            "count": len(crypto_shadow),
            "latest": crypto_shadow[-1] if crypto_shadow else None,
            "recent": crypto_shadow[-8:],
        },
        "mt5_realtick_tca": {
            "status": "AVAILABLE" if realtick_summary else "STANDBY_PENDING_REALTICK",
            "data": realtick_summary,
        },
        "ftmo_live_specs_available": ftmo_specs is not None,
        "upcoming_red_news": upcoming_news,
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
            if path == "/api/allocations":
                self._send_json(HTTPStatus.OK, build_allocations_payload(root))
                return
            if path == "/api/live-telemetry":
                self._send_json(HTTPStatus.OK, build_live_telemetry_payload(root))
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
            if parsed.path != "/api/vnd-calculator":
                self._send_json(HTTPStatus.NOT_FOUND, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                raw = self.rfile.read(min(length, 65_536))
                body = json.loads(raw.decode("utf-8")) if raw else {}
            except Exception:
                self._send_json(HTTPStatus.BAD_REQUEST, {"error": "invalid_json"})
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
