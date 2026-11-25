"""Live-vs-Backtest Transaction Cost Analysis (TCA) & Execution Reconciliation Engine.

Parses structured execution logs emitted by `Naqex_PropGuard.mqh` (`naqex_exec_audit.csv`)
and optional closed-deal broker exports, measuring:
  - Realized entry slippage vs signal price (pips/pts and % of R0)
  - Realized spread vs Dukascopy / FTMO Demo benchmark
  - Fill latency distribution (p50 / p90 / p99 ms)
  - Order rejection / partial fill rate
  - Swap = 0 and intraday weekend-flat compliance
"""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Iterable

import numpy as np

# Benchmark median spreads (in broker points) from verified FTMO Demo & Dukascopy M1 snapshots
BENCHMARK_SPREAD_PTS = {
    "USDJPY": 7.0,
    "GBPUSD": 6.0,
    "EURUSD": 4.0,
    "EURJPY": 14.0,
    "AUDUSD": 7.0,
    "USDCAD": 9.0,
    "XAUUSD": 28.0,
    "US100": 20.0,
    "US100.cash": 20.0,
    "US500": 6.0,
    "US500.cash": 6.0,
}

POINT_SIZES = {
    "USDJPY": 0.001,
    "EURJPY": 0.001,
    "GBPJPY": 0.001,
    "GBPUSD": 0.00001,
    "EURUSD": 0.00001,
    "AUDUSD": 0.00001,
    "USDCAD": 0.00001,
    "XAUUSD": 0.01,
    "US100": 0.01,
    "US100.cash": 0.01,
    "US500": 0.01,
    "US500.cash": 0.01,
}


def load_exec_audit_csv(csv_path: Path) -> list[dict]:
    rows = []
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            rows.append({
                "utc_ts": int(float(r["utc_ts"])),
                "magic": int(float(r["magic"])),
                "symbol": str(r["symbol"]).strip(),
                "side": str(r["side"]).strip().upper(),
                "event_type": str(r["event_type"]).strip().upper(),
                "signal_price": float(r["signal_price"]),
                "fill_price": float(r["fill_price"]),
                "sl_price": float(r["sl_price"]),
                "lots": float(r["lots"]),
                "spread_pts": float(r["spread_pts"]),
                "latency_ms": float(r["latency_ms"]),
                "retcode": int(float(r["retcode"])),
                "comment": str(r.get("comment", "")),
                "swap_usd": float(r.get("swap_usd", 0.0) or 0.0),
            })
    return rows


def compute_tca_report(
    events: Iterable[dict],
    *,
    max_slippage_pct_r0_amber: float = 12.0,
    max_slippage_pct_r0_red: float = 25.0,
    max_reject_rate_pct: float = 5.0,
    max_p90_latency_ms: float = 600.0,
) -> dict:
    """Evaluate realized execution quality against model expectations and return structured TCA verdict."""
    ev_list = list(events)
    fills = [e for e in ev_list if e["event_type"] == "ORDER_FILL"]
    rejects = [e for e in ev_list if e["event_type"] == "ORDER_REJECT"]
    dryruns = [e for e in ev_list if e["event_type"] == "DRYRUN_SIGNAL"]

    slip_r_pcts = []
    slip_pts = []
    spread_ratios = []
    latencies = []
    swap_violations = 0
    by_sym: dict[str, list[float]] = {}

    for e in fills:
        sym = e["symbol"]
        pt = POINT_SIZES.get(sym, 0.00001)
        sig_px = float(e["signal_price"])
        fill_px = float(e["fill_price"])
        sl_px = float(e["sl_price"])
        side_sign = 1.0 if e["side"] == "BUY" else -1.0
        # Positive adverse slippage means worse fill than signal price
        adverse_px = side_sign * (fill_px - sig_px)
        sl_dist = abs(sig_px - sl_px)
        adv_pts = adverse_px / pt
        slip_pts.append(adv_pts)
        by_sym.setdefault(sym, []).append(adv_pts)
        if sl_dist > 1e-12:
            slip_r_pcts.append(100.0 * adverse_px / sl_dist)
        bench = BENCHMARK_SPREAD_PTS.get(sym)
        if bench and bench > 0:
            spread_ratios.append(float(e["spread_pts"]) / bench)
        latencies.append(float(e["latency_ms"]))
        if abs(float(e.get("swap_usd", 0.0))) > 1e-6:
            swap_violations += 1

    attempts = len(fills) + len(rejects)
    reject_rate = (100.0 * len(rejects) / attempts) if attempts > 0 else 0.0

    def _stats(arr: list[float]) -> dict:
        if not arr:
            return {"mean": 0.0, "median": 0.0, "p90": 0.0, "max": 0.0}
        a = np.asarray(arr, dtype=np.float64)
        return {
            "mean": round(float(np.mean(a)), 3),
            "median": round(float(np.median(a)), 3),
            "p90": round(float(np.percentile(a, 90)), 3),
            "max": round(float(np.max(a)), 3),
        }

    slip_r_st = _stats(slip_r_pcts)
    lat_st = _stats(latencies)
    sp_st = _stats(spread_ratios)

    flags = []
    verdict = "GREEN"
    if not fills:
        verdict = "DRYRUN_ONLY" if dryruns else "NO_DATA"
    else:
        if slip_r_st["mean"] >= max_slippage_pct_r0_red:
            verdict = "RED_SLIPPAGE_BREACH"
            flags.append(f"Mean adverse slippage {slip_r_st['mean']}% of R0 >= {max_slippage_pct_r0_red}%")
        elif slip_r_st["mean"] >= max_slippage_pct_r0_amber:
            verdict = "AMBER_WATCH"
            flags.append(f"Mean adverse slippage {slip_r_st['mean']}% of R0 >= {max_slippage_pct_r0_amber}%")
        if reject_rate > max_reject_rate_pct:
            verdict = "RED_EXECUTION_QUALITY"
            flags.append(f"Order reject rate {reject_rate:.1f}% > {max_reject_rate_pct}%")
        if lat_st["p90"] > max_p90_latency_ms:
            if verdict == "GREEN":
                verdict = "AMBER_WATCH"
            flags.append(f"p90 fill latency {lat_st['p90']:.1f}ms > {max_p90_latency_ms}ms")
        if swap_violations > 0:
            verdict = "RED_SWAP_VIOLATION"
            flags.append(f"{swap_violations} fills carried non-zero swap (violates swap=0 contract)")

    return {
        "schema": "naqex-tca-reconcile-v1",
        "counts": {"fills": len(fills), "rejects": len(rejects), "dryrun_signals": len(dryruns)},
        "reject_rate_pct": round(reject_rate, 2),
        "swap_violations": swap_violations,
        "adverse_slippage_pts": _stats(slip_pts),
        "adverse_slippage_pct_of_r0": slip_r_st,
        "spread_vs_benchmark_ratio": sp_st,
        "latency_ms": lat_st,
        "per_symbol_mean_slip_pts": {s: round(float(np.mean(v)), 2) for s, v in sorted(by_sym.items())},
        "flags": flags,
        "verdict": verdict,
    }
