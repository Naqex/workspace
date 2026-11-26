"""Live-vs-Backtest Transaction Cost Analysis (TCA) & Execution Reconciliation Engine.

Parses structured execution logs emitted by `Naqex_PropGuard.mqh` (`naqex_exec_audit.csv`)
and optional closed-deal broker exports, measuring:
  - Realized entry/exit slippage vs signal price (pips/pts and % of R0)
  - Realized spread vs Dukascopy / FTMO Demo benchmark
  - Fill latency distribution (p50 / p90 / p99 ms)
  - Order rejection / partial fill rate
  - Fail-closed Swap = 0, `FILL_UNRESOLVED`, and non-finite guards routed through `quant_core.tca`
  - Optional strictly causal `+1s/+10s/+60s/+5m` post-fill Markout Curve when quotes are supplied
"""

from __future__ import annotations

from collections.abc import Iterable, Mapping, Sequence
from typing import Any

import numpy as np
from quant_core.tca import (
    BENCHMARK_SPREAD_PTS,
    DEFAULT_MARKOUT_HORIZONS_SEC,
    POINT_SIZES,
    VALID_FILL_EVENT_TYPES,
    benchmark_spread_for_symbol,
    compute_markout_curve,
    load_exec_audit_csv,
    normalize_symbol_alias,
    parse_optional_finite_float,
    point_size_for_symbol,
    validate_tca_post_reconcile,
)


def compute_tca_report(
    events: Iterable[Mapping[str, Any]],
    *,
    max_slippage_pct_r0_amber: float = 12.0,
    max_slippage_pct_r0_red: float = 25.0,
    max_reject_rate_pct: float = 5.0,
    max_p90_latency_ms: float = 600.0,
    quote_series: Mapping[str, Sequence[Mapping[str, Any]]] | Iterable[Mapping[str, Any]] | None = None,
    markout_horizons_sec: Sequence[int] = DEFAULT_MARKOUT_HORIZONS_SEC,
    require_zero_swap_raise: bool = False,
    enforce_post_reconcile: bool = True,
) -> dict[str, Any]:
    """Evaluate realized execution quality against model expectations and return structured TCA verdict.

    Fail-closed post-reconciliation gate (`enforce_post_reconcile=True`, default):
      - Raises `ValueError` via `quant_core.tca.validate_tca_post_reconcile()` if ANY fill/closed
        trade still has `swap_usd is None` (e.g. un-enriched blank CSV cell), non-finite `NaN`/`Inf`,
        or `FILL_UNRESOLVED`.
      - Non-zero finite `swap_usd` sets `verdict = "RED_SWAP_VIOLATION"` (and also raises `ValueError`
        when `require_zero_swap_raise=True`).
    """
    ev_list = [dict(e) for e in events]

    post_reconcile_summary: dict[str, Any] | None = None
    if enforce_post_reconcile:
        post_reconcile_summary = validate_tca_post_reconcile(
            ev_list,
            require_zero_swap=require_zero_swap_raise,
            swap_tolerance_usd=0.0,
        )

    fills = [e for e in ev_list if str(e.get("event_type", "")).strip().upper() in VALID_FILL_EVENT_TYPES]
    rejects = [e for e in ev_list if str(e.get("event_type", "")).strip().upper() == "ORDER_REJECT"]
    dryruns = [e for e in ev_list if str(e.get("event_type", "")).strip().upper() == "DRYRUN_SIGNAL"]

    slip_r_pcts: list[float] = []
    slip_pts: list[float] = []
    spread_ratios: list[float] = []
    latencies: list[float] = []
    swap_violations = 0
    by_sym: dict[str, list[float]] = {}

    for e in fills:
        sym = str(e["symbol"])
        pt = point_size_for_symbol(sym)
        sig_px = float(e["signal_price"])
        fill_px = float(e["fill_price"])
        sl_px = float(e["sl_price"])
        side_sign = 1.0 if str(e["side"]).strip().upper() == "BUY" else -1.0
        # Positive adverse slippage means worse fill than signal price
        adverse_px = side_sign * (fill_px - sig_px)
        sl_dist = abs(sig_px - sl_px)
        adv_pts = adverse_px / pt
        slip_pts.append(adv_pts)
        by_sym.setdefault(sym, []).append(adv_pts)
        if sl_dist > 1e-12:
            slip_r_pcts.append(100.0 * adverse_px / sl_dist)
        bench = benchmark_spread_for_symbol(sym)
        if bench and bench > 0:
            spread_ratios.append(float(e["spread_pts"]) / bench)
        latencies.append(float(e["latency_ms"]))
        swap_val = parse_optional_finite_float(e.get("swap_usd"), field_name="swap_usd")
        if swap_val is not None and abs(swap_val) > 0.0:
            swap_violations += 1

    attempts = len(fills) + len(rejects)
    reject_rate = (100.0 * len(rejects) / attempts) if attempts > 0 else 0.0

    def _stats(arr: list[float]) -> dict[str, float]:
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

    markout_curve: dict[str, Any] | None = None
    if quote_series is not None and fills:
        markout_curve = compute_markout_curve(
            fills,
            quote_series,
            horizons_sec=markout_horizons_sec,
        )

    flags: list[str] = []
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
        if markout_curve is not None and markout_curve["adverse_selection_flagged"]:
            flags.append(
                f"Adverse selection detected: overall mean markout {markout_curve['overall_mean_markout_bps']} bps "
                f"(horizons={markout_curve['adverse_selection_horizons']})"
            )

    return {
        "schema": "naqex-tca-reconcile-v1",
        "counts": {"fills": len(fills), "rejects": len(rejects), "dryrun_signals": len(dryruns)},
        "reject_rate_pct": round(reject_rate, 2),
        "swap_violations": swap_violations,
        "unresolved_fills": 0,
        "post_reconcile_check": post_reconcile_summary,
        "adverse_slippage_pts": _stats(slip_pts),
        "adverse_slippage_pct_of_r0": slip_r_st,
        "spread_vs_benchmark_ratio": sp_st,
        "latency_ms": lat_st,
        "per_symbol_mean_slip_pts": {s: round(float(np.mean(v)), 2) for s, v in sorted(by_sym.items())},
        "markout_curve": markout_curve,
        "flags": flags,
        "verdict": verdict,
    }


__all__ = [
    "BENCHMARK_SPREAD_PTS",
    "POINT_SIZES",
    "benchmark_spread_for_symbol",
    "compute_markout_curve",
    "compute_tca_report",
    "load_exec_audit_csv",
    "normalize_symbol_alias",
    "point_size_for_symbol",
    "validate_tca_post_reconcile",
]
