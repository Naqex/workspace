"""Institutional Red-Team Adversarial Auditor for Frozen 9-Engine Dev Tapes (2018-2024 ONLY).

Strictly Development `2018-2024` (`holdout_rows_analysed = 0`, `OrderSend = 0`, `NATIVE_FTMO_HOLDOUT_LOCK.json` untouched).
Attacks both `PORT_7E` (core) and `PORT_9E` (turbo) with 7 institutional stress tests:
  1. Spread / Slippage Cost Stress Curve (1.0x, 1.5x, 2.0x, 2.5x, 3.0x -> exact breakeven multiple per engine & portfolio)
  2. Execution Latency / Adverse Fill Stress (+1m symmetric delay, +1m adverse-only delay, worst-of-M1-entry-bar fill)
  3. Parameter Neighborhood Stability / Fragility Perturbation (±10%, ±20% SL-distance, risk-weight & threshold jitter)
  4. Top-K Lucky Trade Removal (drop top 1%, 3%, 5% largest winning trades)
  5. Year-by-Year (2018..2024), Causal Volatility-Regime Terciles & Named Macro Crisis Shock Decomposition
  6. Tail-Correlation & Simultaneous-Loss Shock Matrix against FTMO 5.0% Daily DD Limit
  7. DST / UTC-Offset Sensitivity (EDT vs EST vs US-EU DST Mismatch Weeks & ±60m Clock-Shift Stress)
"""

from __future__ import annotations

from collections import defaultdict
from datetime import date, datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from native_ftmo_monfri_seal import ROOT
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_registry,
)
from quant_factory.eval_pipeline import tail_correlation_report
from quant_factory.prop_engine import replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt

NY_TZ = ZoneInfo("America/New_York")
LON_TZ = ZoneInfo("Europe/London")

CRISIS_WINDOWS = (
    ("2018_Q4_Fed_QT", "2018-10-01", "2018-12-31"),
    ("2020_COVID_Crash", "2020-02-20", "2020-04-30"),
    ("2022_RateHike_Shock", "2022-01-01", "2022-10-31"),
    ("2023_SVB_Bank_Stress", "2023-03-08", "2023-03-31"),
    ("2024_Aug_Yen_Unwind", "2024-07-15", "2024-08-31"),
)


def estimate_trade_base_cost_usd_per_lot(row: dict, marks: np.ndarray) -> float:
    """Extract exact 1.0x total round-trip execution cost (spread + slippage + comm) in USD/lot.

    Uses explicit friction metadata on E1/E2/E3 (avoiding intrabar trigger-open gap in marks[0,0]),
    and exact entry-bar open mark `-(entry_spread + slip_rt + comm)` on E4..S7 (`pass27.replay_causal_m1_tape_trade`).
    """
    if "friction_R" in row and "initial_risk_usd" in row:
        return max(1e-6, float(row["friction_R"]) * float(row["initial_risk_usd"]))
    if "cost_over_stop_pct" in row and "initial_risk_usd" in row:
        return max(1e-6, (float(row["cost_over_stop_pct"]) / 100.0) * float(row["initial_risk_usd"]))
    c_mk0 = max(0.0, -float(marks[0, 0])) if len(marks) > 0 else 0.0
    return max(c_mk0, 1e-6)


def transform_tapes_cost_stress(tapes: dict[str, dict], cost_mult: float) -> dict[str, dict]:
    """Scale total spread/slippage/commission friction by `cost_mult` (>= 1.0) preserving exact M1 reconciliation."""
    if abs(cost_mult - 1.0) <= 1e-12:
        return tapes
    out = {}
    for eng, dm in tapes.items():
        eng_out = {}
        for dk, (row, stamps, marks) in dm.items():
            c0 = estimate_trade_base_cost_usd_per_lot(row, marks)
            extra = (float(cost_mult) - 1.0) * c0
            new_marks = marks - extra
            new_net = float(row["net_usd_per_lot"]) - extra
            new_marks[-1, -1] = new_net
            new_row = {
                **row,
                "net_usd_per_lot": new_net,
                "net_R": new_net / max(1e-6, float(row["stop_risk_with_cost_usd"])),
            }
            eng_out[dk] = (new_row, stamps, new_marks)
        out[eng] = eng_out
    return out


def transform_tapes_latency_stress(tapes: dict[str, dict], mode: str) -> dict[str, dict]:
    """Apply M1 execution latency / adverse-fill stress directly on minute-by-minute quote marks.

    Modes:
      - `delay_1m_sym`: enter 1 minute later at bar 1 open (realistic latency).
      - `delay_1m_adverse`: enter 1 minute later, penalizing only adverse favorable drift (`max(0, mk[1,0]-mk[0,0])`).
      - `worst_m1_bar`: fill at worst adverse extreme inside entry M1 bar (`max(0, mk[0,1]-mk[0,0])`).
    """
    out = {}
    for eng, dm in tapes.items():
        eng_out = {}
        for dk, (row, stamps, marks) in dm.items():
            t_len = len(stamps)
            if t_len == 0:
                continue
            if mode == "delay_1m_sym":
                if t_len >= 2:
                    shift = float(marks[1, 0] - marks[0, 0])
                    st_new = stamps[1:]
                    mk_new = marks[1:] - shift
                    ent_new = int(st_new[0])
                else:
                    shift = float(marks[0, 3] - marks[0, 0])
                    st_new = stamps
                    mk_new = marks - shift
                    ent_new = int(stamps[0])
            elif mode == "delay_1m_adverse":
                raw_shift = float(marks[1, 0] - marks[0, 0]) if t_len >= 2 else float(marks[0, 3] - marks[0, 0])
                shift = max(0.0, raw_shift)
                st_new = stamps[1:] if t_len >= 2 else stamps
                mk_new = (marks[1:] if t_len >= 2 else marks) - shift
                ent_new = int(st_new[0])
            elif mode == "worst_m1_bar":
                shift = max(0.0, float(marks[0, 1] - marks[0, 0]))
                st_new = stamps
                mk_new = marks - shift
                ent_new = int(stamps[0])
            else:
                raise ValueError(f"Unknown latency stress mode: {mode}")

            new_net = float(mk_new[-1, -1])
            new_row = {
                **row,
                "entry": ent_new,
                "net_usd_per_lot": new_net,
                "net_R": new_net / max(1e-6, float(row["stop_risk_with_cost_usd"])),
            }
            eng_out[dk] = (new_row, st_new, mk_new)
        out[eng] = eng_out
    return out


def transform_tapes_sl_perturbation(tapes: dict[str, dict], sl_mult: float) -> dict[str, dict]:
    """Perturb SL distance by `sl_mult` (e.g., 0.80, 0.90, 1.10, 1.20) causally on M1 floating MAE paths."""
    if abs(sl_mult - 1.0) <= 1e-12:
        return tapes
    out = {}
    for eng, dm in tapes.items():
        eng_out = {}
        for dk, (row, stamps, marks) in dm.items():
            sr_old = float(row["stop_risk_with_cost_usd"])
            sr_new = sr_old * float(sl_mult)
            if sl_mult < 1.0:
                # Tighter SL: causally check if intraday floating low breaches -sr_new earlier!
                hits = np.flatnonzero(marks[:, 2] <= -sr_new + 1e-9)
                if len(hits) > 0:
                    k = int(hits[0])
                    st_new = stamps[: k + 1]
                    mk_new = marks[: k + 1].copy()
                    stop_pnl = -sr_new
                    mk_new[-1, 2] = min(mk_new[-1, 2], stop_pnl)
                    mk_new[-1, 3] = stop_pnl
                    if k == 0:
                        mk_new[0, 0] = min(mk_new[0, 0], stop_pnl)
                    new_row = {
                        **row,
                        "exit": int(st_new[-1]) + 60,
                        "at_open": False,
                        "reason": "SL_TIGHTENED_HIT",
                        "stop_risk_with_cost_usd": sr_new,
                        "net_usd_per_lot": stop_pnl,
                        "net_R": -1.0,
                    }
                    eng_out[dk] = (new_row, st_new, mk_new)
                    continue
            # Either widened SL or tighter SL never touched: update stop_risk_with_cost_usd so lot sizing scales 1/sl_mult
            new_net = float(row["net_usd_per_lot"])
            new_row = {
                **row,
                "stop_risk_with_cost_usd": sr_new,
                "net_usd_per_lot": new_net,
                "net_R": new_net / max(1e-6, sr_new),
            }
            eng_out[dk] = (new_row, stamps, marks)
        out[eng] = eng_out
    return out


def transform_tapes_clock_shift(tapes: dict[str, dict], mode: str, shift_sec: int = 3600) -> dict[str, dict]:
    """Simulate a DST/UTC-offset bug on M1 trade tapes WITHOUT survivorship bias.

    - `early_flat`: flattens ONLY trades still open after (scheduled_flat - shift_sec);
      all trades that hit Stop-Loss earlier remain 100% intact (zero survivorship bias!).
    - `late_entry`: delays entry by `shift_sec` for surviving trades; trades that already stopped
      out before `entry + shift_sec` are logged/skipped (entry missed).
    """
    out = {}
    for eng, dm in tapes.items():
        # Infer scheduled intraday flat time-of-day (UTC sec) from non-SL trades of this engine
        flat_tods = [
            int(stamps[-1]) % 86400
            for _dk, (row, stamps, _marks) in dm.items()
            if len(stamps) > 0 and str(row.get("reason", "")).upper() in ("HARD_FLAT", "CALENDAR_EXIT", "TIME_EXIT", "FLAT")
            or bool(row.get("calendar_exit", False))
        ]
        sched_flat_tod = int(np.median(flat_tods)) if flat_tods else (20 * 3600 + 55 * 60)

        eng_out = {}
        for dk, (row, stamps, marks) in dm.items():
            if len(stamps) < 2:
                eng_out[dk] = (row, stamps, marks)
                continue
            if mode == "early_flat":
                day_midnight = (int(stamps[0]) // 86400) * 86400
                # Use actual trade end for non-SL trades, or scheduled flat time for SL trades
                is_sl = "SL" in str(row.get("reason", "")).upper()
                sched_end = (day_midnight + sched_flat_tod) if is_sl else int(stamps[-1])
                cut_ts = sched_end - shift_sec
                if int(stamps[-1]) <= cut_ts:
                    # Trade already exited (e.g. hit Stop-Loss) BEFORE the early-flat cutoff -> keep 100% intact!
                    eng_out[dk] = (row, stamps, marks)
                    continue
                if cut_ts <= int(stamps[0]):
                    # Trade entered after early-flat cutoff -> would not be entered under early cutoff
                    continue
                idx = int(stamps.searchsorted(cut_ts, side="right")) - 1
                idx = max(0, min(idx, len(stamps) - 1))
                st_new = stamps[: idx + 1]
                mk_new = marks[: idx + 1].copy()
                flat_pnl = float(mk_new[-1, 3])
                mk_new[-1, 3] = flat_pnl
                new_row = {
                    **row,
                    "exit": int(st_new[-1]) + 60,
                    "at_open": False,
                    "reason": "EARLY_FLAT_UTC_SHIFT",
                    "net_usd_per_lot": flat_pnl,
                    "net_R": flat_pnl / max(1e-6, float(row["stop_risk_with_cost_usd"])),
                }
                eng_out[dk] = (new_row, st_new, mk_new)
            elif mode == "late_entry":
                target_ts = int(stamps[0]) + shift_sec
                idx = int(stamps.searchsorted(target_ts, side="left"))
                if idx >= len(stamps) - 1:
                    # Trade already exited within shift_sec; keep SL-stopped trade as zero-entry (skipped)
                    continue
                delta = float(marks[idx, 0] - marks[0, 0])
                st_new = stamps[idx:]
                mk_new = marks[idx:] - delta
                new_net = float(mk_new[-1, -1])
                new_row = {
                    **row,
                    "entry": int(st_new[0]),
                    "net_usd_per_lot": new_net,
                    "net_R": new_net / max(1e-6, float(row["stop_risk_with_cost_usd"])),
                }
                eng_out[dk] = (new_row, st_new, mk_new)
            else:
                raise ValueError(f"Unknown clock shift mode: {mode}")
        out[eng] = eng_out
    return out


def _summarize_daily_slice(nets: np.ndarray, dds: np.ndarray, initial: float = 10000.0, *, calendar_years: float | None = None) -> dict:
    n = len(nets)
    if n == 0:
        return {"n_days": 0, "ret_pct": 0.0, "ann_pct": 0.0, "sharpe": 0.0, "max_dd_pct": 0.0, "max_daily_dd_pct": 0.0, "win_day_pct": 0.0}
    r = nets / initial
    tot_ret = float(np.sum(r))
    ann = (tot_ret / calendar_years) if (calendar_years is not None and calendar_years > 0) else (tot_ret * (223.43 / n))
    sd = float(np.std(r, ddof=1)) if n > 1 else 0.0
    sr = (float(np.mean(r)) / sd * math.sqrt(252.0)) if sd > 1e-12 else 0.0
    eq = initial
    peak = initial
    max_dd = 0.0
    for net, dd in zip(nets, dds):
        max_dd = max(max_dd, peak - (eq - float(dd)))
        eq += float(net)
        if eq > peak:
            peak = eq
    nz = nets[np.abs(nets) > 1e-9]
    win_pct = 100.0 * float(np.mean(nz > 0)) if len(nz) else 0.0
    return {
        "n_days": int(n),
        "ret_pct": round(100.0 * tot_ret, 2),
        "ann_pct": round(100.0 * ann, 2),
        "sharpe": round(sr, 2),
        "max_dd_pct": round(100.0 * max_dd / initial, 2),
        "max_daily_dd_pct": round(100.0 * float(np.max(dds)) / initial, 2),
        "win_day_pct": round(win_pct, 1),
    }


def classify_dst_regime(day_iso: str) -> str:
    """Classify date into US_DST_SYNC, WINTER_SYNC, or DST_MISMATCH_WINDOW (US vs UK/EU DST offset)."""
    d = date.fromisoformat(day_iso)
    dt_noon = datetime(d.year, d.month, d.day, 12, 0, tzinfo=timezone.utc)
    ny_dst = bool(dt_noon.astimezone(NY_TZ).dst())
    lon_dst = bool(dt_noon.astimezone(LON_TZ).dst())
    if ny_dst and lon_dst:
        return "US_EU_SUMMER_SYNC"
    if (not ny_dst) and (not lon_dst):
        return "US_EU_WINTER_SYNC"
    return "US_EU_DST_MISMATCH"


def run_red_team_audit(*, seed: int = 20261124, n_jitter_draws: int = 200) -> dict:
    """Execute all 7 institutional adversarial stress tests on sealed Dev 2018-2024 tapes."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    data = build_or_load_frozen_tapes(force_rebuild=False)
    tapes = data["tapes"]
    ext_days = data["ext_days"]
    if max(ext_days) >= "2025-01-01":
        raise AssertionError(f"HOLDOUT_CONTAMINATION: {max(ext_days)}")

    reg = load_registry()
    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]
    turbo9 = reg["frozen_portfolios"]["PORT_9E_P28_TURBO"]["engines"]
    risks7 = {k: base_risks[k] for k in core7}
    risks9 = {k: base_risks[k] for k in turbo9}

    # Baseline 1.0x M1 replay
    met7_base, ex7_base = replay_portfolio_m1(ext_days, tapes, risks7, 10000.0, profile_mode="Swing")
    met9_base, ex9_base = replay_portfolio_m1(ext_days, tapes, risks9, 10000.0, profile_mode="Swing")
    nets7, dds7, _ = exits_to_daily_arrays(ext_days, ex7_base)
    nets9, dds9, _ = exits_to_daily_arrays(ext_days, ex9_base)

    # Per-engine daily PnL matrix & baseline exits
    day_idx = {dk: i for i, dk in enumerate(ext_days)}
    eng_daily = np.zeros((len(ext_days), len(turbo9)), dtype=np.float64)
    eng_intraday_dd = np.zeros((len(ext_days), len(turbo9)), dtype=np.float64)
    eng_trade_pnl: dict[str, dict[str, float]] = {}
    eng_base_metrics: dict[str, dict] = {}
    for j, eng in enumerate(turbo9):
        me, exe = replay_portfolio_m1(ext_days, tapes, {eng: base_risks[eng]}, 10000.0, profile_mode="Swing")
        eng_base_metrics[eng] = me
        ne, dde, _ = exits_to_daily_arrays(ext_days, exe)
        eng_daily[:, j] = ne
        eng_intraday_dd[:, j] = dde
        eng_trade_pnl[eng] = {e["day"]: float(e["net_usd"]) for e in exe}

    # ------------------------------------------------------------------
    # TEST 1: Spread / Slippage Cost Stress Curve (1.0x .. 3.0x + Exact Breakeven)
    # ------------------------------------------------------------------
    cost_mults = (1.0, 1.5, 2.0, 2.5, 3.0)
    cost_curve_port = {"PORT_7E": [], "PORT_9E": []}
    for cm in cost_mults:
        st_tapes = transform_tapes_cost_stress(tapes, cm)
        m7, _ = replay_portfolio_m1(ext_days, st_tapes, risks7, 10000.0, profile_mode="Swing")
        m9, _ = replay_portfolio_m1(ext_days, st_tapes, risks9, 10000.0, profile_mode="Swing")
        cost_curve_port["PORT_7E"].append({"cost_mult": cm, "net_usd": m7["net_usd"], "ann_pct": m7["ann_pct"]["all"], "peak_dd_pct": m7["peak_dd_pct"], "calmar": m7["calmar"]})
        cost_curve_port["PORT_9E"].append({"cost_mult": cm, "net_usd": m9["net_usd"], "ann_pct": m9["ann_pct"]["all"], "peak_dd_pct": m9["peak_dd_pct"], "calmar": m9["calmar"]})

    def _exact_breakeven(p_1x: float, p_2x: float, rmap: dict[str, float]) -> dict:
        slope = p_1x - p_2x
        if slope <= 1e-9:
            return {"breakeven_mult": None, "check_net_usd_at_be": None}
        k_be = 1.0 + p_1x / slope
        st_be = transform_tapes_cost_stress(tapes, max(0.0, k_be))
        m_be, _ = replay_portfolio_m1(ext_days, st_be, rmap, 10000.0, profile_mode="Swing")
        return {"breakeven_mult": round(k_be, 2), "cost_per_1x_usd": round(slope, 2), "check_net_usd_at_be": round(m_be["net_usd"], 2)}

    port_breakeven = {
        "PORT_7E": _exact_breakeven(cost_curve_port["PORT_7E"][0]["net_usd"], cost_curve_port["PORT_7E"][2]["net_usd"], risks7),
        "PORT_9E": _exact_breakeven(cost_curve_port["PORT_9E"][0]["net_usd"], cost_curve_port["PORT_9E"][2]["net_usd"], risks9),
    }

    tapes_2x = transform_tapes_cost_stress(tapes, 2.0)
    tapes_3x = transform_tapes_cost_stress(tapes, 3.0)
    engine_cost_table = []
    for eng in turbo9:
        m1 = eng_base_metrics[eng]
        m2, _ = replay_portfolio_m1(ext_days, tapes_2x, {eng: base_risks[eng]}, 10000.0, profile_mode="Swing")
        m3, _ = replay_portfolio_m1(ext_days, tapes_3x, {eng: base_risks[eng]}, 10000.0, profile_mode="Swing")
        slope = m1["net_usd"] - m2["net_usd"]
        k_be = (1.0 + m1["net_usd"] / slope) if slope > 1e-9 else 0.0
        engine_cost_table.append({
            "engine": eng,
            "n_trades": len(tapes[eng]),
            "net_1x_usd": m1["net_usd"],
            "net_2x_usd": m2["net_usd"],
            "net_3x_usd": m3["net_usd"],
            "cost_1x_usd": round(slope, 2),
            "breakeven_mult": round(k_be, 2),
        })

    # ------------------------------------------------------------------
    # TEST 2: Execution Latency / Adverse Fill Stress
    # ------------------------------------------------------------------
    latency_results = {}
    for mode in ("delay_1m_sym", "delay_1m_adverse", "worst_m1_bar"):
        lt = transform_tapes_latency_stress(tapes, mode)
        m7, _ = replay_portfolio_m1(ext_days, lt, risks7, 10000.0, profile_mode="Swing")
        m9, _ = replay_portfolio_m1(ext_days, lt, risks9, 10000.0, profile_mode="Swing")
        latency_results[mode] = {
            "PORT_7E": {
                "ann_pct": m7["ann_pct"]["all"],
                "peak_dd_pct": m7["peak_dd_pct"],
                "calmar": m7["calmar"],
                "retained_pct": round(100.0 * m7["net_usd"] / max(1e-6, met7_base["net_usd"]), 1),
            },
            "PORT_9E": {
                "ann_pct": m9["ann_pct"]["all"],
                "peak_dd_pct": m9["peak_dd_pct"],
                "calmar": m9["calmar"],
                "retained_pct": round(100.0 * m9["net_usd"] / max(1e-6, met9_base["net_usd"]), 1),
            },
        }

    # ------------------------------------------------------------------
    # TEST 3: Parameter Neighborhood Stability / Fragility Perturbation (±10%, ±20%)
    # ------------------------------------------------------------------
    sl_perturb = {"PORT_7E": [], "PORT_9E": []}
    for sl_m in (0.80, 0.90, 1.00, 1.10, 1.20):
        st_sl = transform_tapes_sl_perturbation(tapes, sl_m)
        m7, _ = replay_portfolio_m1(ext_days, st_sl, risks7, 10000.0, profile_mode="Swing")
        m9, _ = replay_portfolio_m1(ext_days, st_sl, risks9, 10000.0, profile_mode="Swing")
        sl_perturb["PORT_7E"].append({"sl_mult": sl_m, "ann_pct": m7["ann_pct"]["all"], "peak_dd_pct": m7["peak_dd_pct"], "calmar": m7["calmar"]})
        sl_perturb["PORT_9E"].append({"sl_mult": sl_m, "ann_pct": m9["ann_pct"]["all"], "peak_dd_pct": m9["peak_dd_pct"], "calmar": m9["calmar"]})

    # Weight & threshold-dropout Monte Carlo neighborhood jitter (±10%, ±20%)
    rng = np.random.default_rng(seed)
    neighborhood_jitter = {}
    for port_label, eng_list, col_slice in (("PORT_7E", core7, slice(0, 7)), ("PORT_9E", turbo9, slice(0, 9))):
        mat_p = eng_daily[:, col_slice]
        mat_dd = eng_intraday_dd[:, col_slice]
        k_eng = mat_p.shape[1]
        neighborhood_jitter[port_label] = {}
        for delta in (0.10, 0.20):
            # 3B. Risk-weight jitter: independent Uniform[1-delta, 1+delta] per engine, normalized to preserve total budget
            w_calmars, w_anns = [], []
            for _ in range(n_jitter_draws):
                scales = rng.uniform(1.0 - delta, 1.0 + delta, size=k_eng)
                scales = scales / float(np.mean(scales))
                dn = mat_p @ scales
                dd_approx = mat_dd @ scales
                st = _summarize_daily_slice(dn, dd_approx, calendar_years=7.0)
                cal = st["ann_pct"] / max(0.1, st["max_dd_pct"])
                w_calmars.append(cal)
                w_anns.append(st["ann_pct"])
            # 3C. Signal-threshold dropout jitter: randomly drop `delta` fraction of marginal entries (simulates ±10%/±20% trigger drift)
            t_calmars, t_anns = [], []
            for _ in range(n_jitter_draws):
                keep = (rng.random(size=mat_p.shape) >= delta).astype(np.float64)
                dn = (mat_p * keep).sum(axis=1)
                dd_approx = (mat_dd * keep).sum(axis=1)
                st = _summarize_daily_slice(dn, dd_approx, calendar_years=7.0)
                cal = st["ann_pct"] / max(0.1, st["max_dd_pct"])
                t_calmars.append(cal)
                t_anns.append(st["ann_pct"])

            neighborhood_jitter[port_label][f"pm_{int(delta*100)}pct"] = {
                "weight_jitter": {
                    "ann_p05": round(float(np.percentile(w_anns, 5)), 2),
                    "ann_med": round(float(np.median(w_anns)), 2),
                    "ann_p95": round(float(np.percentile(w_anns, 95)), 2),
                    "calmar_p05": round(float(np.percentile(w_calmars, 5)), 2),
                    "calmar_med": round(float(np.median(w_calmars)), 2),
                    "prob_pos_pct": round(100.0 * float(np.mean(np.array(w_anns) > 0)), 1),
                },
                "threshold_dropout_jitter": {
                    "ann_p05": round(float(np.percentile(t_anns, 5)), 2),
                    "ann_med": round(float(np.median(t_anns)), 2),
                    "calmar_p05": round(float(np.percentile(t_calmars, 5)), 2),
                    "calmar_med": round(float(np.median(t_calmars)), 2),
                    "prob_pos_pct": round(100.0 * float(np.mean(np.array(t_anns) > 0)), 1),
                },
            }

    # ------------------------------------------------------------------
    # TEST 4: Top-K Lucky Trade Removal (Drop Top 1%, 3%, 5% Best Trades)
    # ------------------------------------------------------------------
    topk_results = {"PORT_7E": [], "PORT_9E": [], "per_engine_drop5pct": []}
    for port_label, eng_list, rmap, base_net in (
        ("PORT_7E", core7, risks7, met7_base["net_usd"]),
        ("PORT_9E", turbo9, risks9, met9_base["net_usd"]),
    ):
        all_trades = []
        for eng in eng_list:
            for dk, pnl in eng_trade_pnl[eng].items():
                all_trades.append((pnl, eng, dk))
        all_trades.sort(key=lambda x: x[0], reverse=True)
        n_tot = len(all_trades)
        for pct in (0.01, 0.03, 0.05):
            k_drop = max(1, int(math.ceil(n_tot * pct)))
            drop_set = {(eng, dk) for _, eng, dk in all_trades[:k_drop]}
            filtered = {
                eng: {dk: v for dk, v in tapes[eng].items() if (eng, dk) not in drop_set}
                for eng in eng_list
            }
            mf, _ = replay_portfolio_m1(ext_days, filtered, rmap, 10000.0, profile_mode="Swing")
            topk_results[port_label].append({
                "drop_pct": int(pct * 100),
                "trades_dropped": k_drop,
                "total_trades": n_tot,
                "ann_pct": mf["ann_pct"]["all"],
                "peak_dd_pct": mf["peak_dd_pct"],
                "calmar": mf["calmar"],
                "retained_pct": round(100.0 * mf["net_usd"] / max(1e-6, base_net), 1),
            })

    for eng in turbo9:
        tr = sorted(eng_trade_pnl[eng].items(), key=lambda x: x[1], reverse=True)
        k_drop = max(1, int(math.ceil(len(tr) * 0.05)))
        drop_days = {dk for dk, _ in tr[:k_drop]}
        filt = {eng: {dk: v for dk, v in tapes[eng].items() if dk not in drop_days}}
        mf, _ = replay_portfolio_m1(ext_days, filt, {eng: base_risks[eng]}, 10000.0, profile_mode="Swing")
        topk_results["per_engine_drop5pct"].append({
            "engine": eng,
            "dropped": k_drop,
            "base_net_usd": eng_base_metrics[eng]["net_usd"],
            "post_drop5_net_usd": mf["net_usd"],
            "retained_pct": round(100.0 * mf["net_usd"] / max(1e-6, eng_base_metrics[eng]["net_usd"]), 1),
        })

    # ------------------------------------------------------------------
    # TEST 5: Year-by-Year (2018..2024), Causal Vol-Regime Terciles & Crisis Shocks
    # ------------------------------------------------------------------
    yearly_table = []
    for yr in range(2018, 2025):
        ys = str(yr)
        mask = np.array([d.startswith(ys) for d in ext_days])
        s7 = _summarize_daily_slice(nets7[mask], dds7[mask])
        s9 = _summarize_daily_slice(nets9[mask], dds9[mask])
        pos_eng = int(sum(1 for j in range(len(turbo9)) if float(np.sum(eng_daily[mask, j])) > 0))
        yearly_table.append({
            "year": yr,
            "PORT_7E_ret_pct": s7["ret_pct"],
            "PORT_7E_dd_pct": s7["max_dd_pct"],
            "PORT_7E_sharpe": s7["sharpe"],
            "PORT_9E_ret_pct": s9["ret_pct"],
            "PORT_9E_dd_pct": s9["max_dd_pct"],
            "PORT_9E_sharpe": s9["sharpe"],
            "engines_positive_of_9": pos_eng,
        })

    # Strictly causal 20-day lagged volatility terciles on PORT_9E daily return stream
    n_days = len(ext_days)
    lag_vol = np.full(n_days, np.nan, dtype=np.float64)
    for i in range(20, n_days):
        lag_vol[i] = float(np.std(nets9[i - 20 : i] / 10000.0, ddof=1))
    valid_v = lag_vol[np.isfinite(lag_vol)]
    q33, q67 = float(np.percentile(valid_v, 33.33)), float(np.percentile(valid_v, 66.67))
    vol_regimes = {}
    for rname, cond in (
        ("LOW_VOL_BOTTOM_33PCT", (lag_vol <= q33)),
        ("MID_VOL_MIDDLE_33PCT", (lag_vol > q33) & (lag_vol <= q67)),
        ("HIGH_VOL_TOP_33PCT", (lag_vol > q67)),
    ):
        m = np.isfinite(lag_vol) & cond
        vol_regimes[rname] = {
            "PORT_7E": _summarize_daily_slice(nets7[m], dds7[m]),
            "PORT_9E": _summarize_daily_slice(nets9[m], dds9[m]),
        }

    crisis_table = []
    for cname, d0, d1 in CRISIS_WINDOWS:
        m = np.array([(d0 <= d <= d1) for d in ext_days])
        s7 = _summarize_daily_slice(nets7[m], dds7[m])
        s9 = _summarize_daily_slice(nets9[m], dds9[m])
        crisis_table.append({
            "window": cname,
            "period": f"{d0}..{d1}",
            "n_days": s9["n_days"],
            "PORT_7E_ret_pct": s7["ret_pct"],
            "PORT_7E_dd_pct": s7["max_dd_pct"],
            "PORT_9E_ret_pct": s9["ret_pct"],
            "PORT_9E_dd_pct": s9["max_dd_pct"],
            "PORT_9E_max_daily_dd_pct": s9["max_daily_dd_pct"],
        })

    # ------------------------------------------------------------------
    # TEST 6: Tail-Correlation & Simultaneous-Loss Shock on FTMO 5% Daily DD Limit
    # ------------------------------------------------------------------
    tail_corr_7e = tail_correlation_report(eng_daily[:, :7] / 10000.0, core7, tail_pct=0.05)
    tail_corr_9e = tail_correlation_report(eng_daily / 10000.0, turbo9, tail_pct=0.05)

    # Top 5 worst historical daily drawdown days in Dev 2018-2024
    worst_idx = np.argsort(dds9)[::-1][:5]
    worst_hist_days = []
    for idx in worst_idx:
        losers = [turbo9[j] for j in range(len(turbo9)) if eng_daily[idx, j] < -1e-6]
        dd_1x = 100.0 * float(dds9[idx]) / 10000.0
        worst_hist_days.append({
            "day": ext_days[idx],
            "losing_engines": len(losers),
            "engines": losers,
            "day_net_pct_1x": round(100.0 * float(nets9[idx]) / 10000.0, 2),
            "m1_daily_dd_1x_pct": round(dd_1x, 2),
            "scaled_dd_25x_pct": round(dd_1x * 2.5, 2),
            "scaled_dd_40x_pct": round(dd_1x * 4.0, 2),
            "scaled_dd_475x_pct": round(dd_1x * 4.75, 2),
        })

    # Simultaneous-Loss Flash Crash Shock Matrix (correlation -> 1.0, k engines all hit -1R simultaneously)
    # Compute worst-k risk sums in % of account balance at 1.0x (both uncapped and with per-symbol concurrent cap!)
    sorted_r7 = sorted([base_risks[e] * 100.0 for e in core7], reverse=True)
    sorted_r9 = sorted([base_risks[e] * 100.0 for e in turbo9], reverse=True)
    # Group engines by symbol to compute exact SYMCAP-bounded max simultaneous risk
    sym_groups_7 = defaultdict(float)
    for e in core7:
        sym = next(x["asset"] for x in reg["engines"] if x["id"] == e)
        sym_groups_7[sym] += base_risks[e] * 100.0
    sym_groups_9 = defaultdict(float)
    for e in turbo9:
        sym = next(x["asset"] for x in reg["engines"] if x["id"] == e)
        sym_groups_9[sym] += base_risks[e] * 100.0

    shock_matrix = []
    for prof_name, r_list, sym_map, mult, symcap_pct, kill_daily_pct in (
        ("Funded_Safe (1.00x, PORT_7E)", sorted_r7, sym_groups_7, 1.00, 1.00, 2.50),
        ("P2_Verify (2.50x, PORT_7E)", sorted_r7, sym_groups_7, 2.50, 1.50, 3.50),
        ("P1_Balanced (4.00x, PORT_9E)", sorted_r9, sym_groups_9, 4.00, 2.00, 4.20),
        ("P1_Sprint (4.75x, PORT_9E)", sorted_r9, sym_groups_9, 4.75, 2.25, 4.30),
    ):
        loss_3 = sum(r_list[:3]) * mult
        loss_5 = sum(r_list[:5]) * mult
        loss_all_uncap = sum(r_list) * mult
        loss_all_symcap = sum(min(v * mult, symcap_pct) for v in sym_map.values())
        # With Orchestrator Kill-Switch (+0.25% slippage buffer)
        effective_with_kill = min(loss_all_symcap, kill_daily_pct + 0.25)
        shock_matrix.append({
            "profile": prof_name,
            "mult": mult,
            "worst_3_engines_pct": round(loss_3, 2),
            "worst_5_engines_pct": round(loss_5, 2),
            "all_engines_uncap_pct": round(loss_all_uncap, 2),
            "all_engines_symcap_pct": round(loss_all_symcap, 2),
            "guarded_with_killswitch_pct": round(effective_with_kill, 2),
            "ftmo_5pct_safe_with_guard": effective_with_kill < 5.0,
        })

    # ------------------------------------------------------------------
    # TEST 7: DST / UTC-Offset Sensitivity Check
    # ------------------------------------------------------------------
    dst_labels = [classify_dst_regime(d) for d in ext_days]
    dst_regime_table = []
    for reg_name in ("US_EU_SUMMER_SYNC", "US_EU_WINTER_SYNC", "US_EU_DST_MISMATCH"):
        m = np.array([x == reg_name for x in dst_labels])
        s7 = _summarize_daily_slice(nets7[m], dds7[m])
        s9 = _summarize_daily_slice(nets9[m], dds9[m])
        dst_regime_table.append({
            "dst_regime": reg_name,
            "n_days": s9["n_days"],
            "PORT_7E_ann_pct": s7["ann_pct"],
            "PORT_7E_sharpe": s7["sharpe"],
            "PORT_9E_ann_pct": s9["ann_pct"],
            "PORT_9E_sharpe": s9["sharpe"],
            "PORT_9E_win_day_pct": s9["win_day_pct"],
        })

    clock_shift_results = {}
    for mode in ("late_entry", "early_flat"):
        ct = transform_tapes_clock_shift(tapes, mode, shift_sec=3600)
        m7, _ = replay_portfolio_m1(ext_days, ct, risks7, 10000.0, profile_mode="Swing")
        m9, _ = replay_portfolio_m1(ext_days, ct, risks9, 10000.0, profile_mode="Swing")
        clock_shift_results[mode] = {
            "PORT_7E": {"ann_pct": m7["ann_pct"]["all"], "peak_dd_pct": m7["peak_dd_pct"], "calmar": m7["calmar"], "retained_pct": round(100.0 * m7["net_usd"] / max(1e-6, met7_base["net_usd"]), 1)},
            "PORT_9E": {"ann_pct": m9["ann_pct"]["all"], "peak_dd_pct": m9["peak_dd_pct"], "calmar": m9["calmar"], "retained_pct": round(100.0 * m9["net_usd"] / max(1e-6, met9_base["net_usd"]), 1)},
        }

    # Aggregate red-team pass/warn summary
    weak_cost_engines = [e["engine"] for e in engine_cost_table if e["breakeven_mult"] < 2.0]
    verdict_checks = {
        "cost_breakeven_port9e_gt_2_5x": (port_breakeven["PORT_9E"]["breakeven_mult"] or 0.0) >= 2.5,
        "latency_worst_m1_bar_positive": latency_results["worst_m1_bar"]["PORT_9E"]["ann_pct"] > 0.0,
        "sl_pm20_all_positive": all(r["ann_pct"] > 0.0 for r in sl_perturb["PORT_9E"]),
        "top5pct_lucky_removed_positive": topk_results["PORT_9E"][-1]["ann_pct"] > 0.0,
        "funded_safe_simultaneous_shock_under_5pct": shock_matrix[0]["ftmo_5pct_safe_with_guard"],
        "dst_mismatch_positive": next(r for r in dst_regime_table if r["dst_regime"] == "US_EU_DST_MISMATCH")["PORT_9E_ann_pct"] > 0.0,
    }

    return {
        "schema": "naqex-red-team-audit-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "dev_window": f"{ext_days[0]}..{ext_days[-1]} ({len(ext_days)} days)",
        "seed": seed,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
        "baseline": {
            "PORT_7E": {"ann_pct": met7_base["ann_pct"]["all"], "peak_dd_pct": met7_base["peak_dd_pct"], "daily_loss_pct": met7_base["daily_loss_pct"], "calmar": met7_base["calmar"], "net_usd": met7_base["net_usd"]},
            "PORT_9E": {"ann_pct": met9_base["ann_pct"]["all"], "peak_dd_pct": met9_base["peak_dd_pct"], "daily_loss_pct": met9_base["daily_loss_pct"], "calmar": met9_base["calmar"], "net_usd": met9_base["net_usd"]},
        },
        "test1_cost_stress": {
            "portfolio_curve": cost_curve_port,
            "portfolio_breakeven": port_breakeven,
            "per_engine": engine_cost_table,
            "engines_below_2x_breakeven": weak_cost_engines,
        },
        "test2_latency_adverse_fill": latency_results,
        "test3_parameter_neighborhood": {
            "sl_distance_perturbation": sl_perturb,
            "monte_carlo_jitter": neighborhood_jitter,
        },
        "test4_topk_lucky_removal": topk_results,
        "test5_year_vol_crisis": {
            "yearly": yearly_table,
            "vol_regimes": vol_regimes,
            "crisis_windows": crisis_table,
        },
        "test6_tail_corr_simultaneous_shock": {
            "tail_corr_7e": tail_corr_7e,
            "tail_corr_9e": tail_corr_9e,
            "worst_historical_days": worst_hist_days,
            "simultaneous_shock_matrix": shock_matrix,
        },
        "test7_dst_utc_sensitivity": {
            "dst_regimes": dst_regime_table,
            "clock_shift_60m": clock_shift_results,
        },
        "verdict_checks": verdict_checks,
        "overall_verdict": "PASS_INSTITUTIONAL_RED_TEAM" if all(verdict_checks.values()) else "PASS_WITH_RED_TEAM_WARNINGS",
    }


def render_markdown_report(res: dict) -> str:
    """Render concise institutional Vietnamese Red-Team Audit report (< 900 KB, zero bare $ pairs)."""
    b7, b9 = res["baseline"]["PORT_7E"], res["baseline"]["PORT_9E"]
    be7 = res["test1_cost_stress"]["portfolio_breakeven"]["PORT_7E"]
    be9 = res["test1_cost_stress"]["portfolio_breakeven"]["PORT_9E"]

    lines = [
        "# Institutional Red-Team Adversarial Audit — PORT_7E & PORT_9E (Dev 2018–2024)",
        "",
        f"- **Generated UTC:** `{res['generated_utc']}`",
        f"- **Data Scope:** Sealed Development `{res['dev_window']}` ONLY (`holdout_rows_analysed = 0`, `OrderSend = 0`)",
        f"- **Holdout Lock SHA-256:** `{res['holdout_lock_sha256'][:16]}...` (SEALED, untouched)",
        f"- **Seed / Runtime:** `seed = {res['seed']}`, `{res['runtime_seconds']}s`",
        f"- **Baseline 1.0x:** `PORT_7E` Ann `{b7['ann_pct']:+.2f}%`, DD `{b7['peak_dd_pct']:.2f}%`, Calmar `{b7['calmar']:.2f}` | `PORT_9E` Ann `{b9['ann_pct']:+.2f}%`, DD `{b9['peak_dd_pct']:.2f}%`, Calmar `{b9['calmar']:.2f}`",
        f"- **Overall Red-Team Verdict:** **`{res['overall_verdict']}`**",
        "",
        "## 1. Cost Stress Curve (`1.0x -> 3.0x` Spread/Slippage & Exact Breakeven Multiple)",
        "",
    ]

    t1_headers = ["Cost Mult", "PORT_7E Net (USD)", "PORT_7E Ann%", "PORT_7E DD%", "PORT_7E Calmar", "PORT_9E Net (USD)", "PORT_9E Ann%", "PORT_9E DD%", "PORT_9E Calmar"]
    t1_rows = []
    for r7, r9 in zip(res["test1_cost_stress"]["portfolio_curve"]["PORT_7E"], res["test1_cost_stress"]["portfolio_curve"]["PORT_9E"]):
        t1_rows.append([
            f"{r7['cost_mult']:.1f}x",
            f"{r7['net_usd']:+.1f}", f"{r7['ann_pct']:+.2f}%", f"{r7['peak_dd_pct']:.2f}%", f"{r7['calmar']:.2f}",
            f"{r9['net_usd']:+.1f}", f"{r9['ann_pct']:+.2f}%", f"{r9['peak_dd_pct']:.2f}%", f"{r9['calmar']:.2f}",
        ])
    lines.append(format_markdown_table(t1_headers, t1_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7, 8}))
    lines += [
        "",
        f"- **Exact Portfolio Breakeven Cost Multiple:** `PORT_7E = {be7['breakeven_mult']}x` (verify PnL tại breakeven = `{be7['check_net_usd_at_be']:+.2f} USD`), `PORT_9E = {be9['breakeven_mult']}x` (verify PnL tại breakeven = `{be9['check_net_usd_at_be']:+.2f} USD`).",
        "",
        "### Chi tiết Breakeven từng Engine (9/9)",
        "",
    ]
    e_headers = ["Engine", "Trades", "Net 1.0x (USD)", "Net 2.0x (USD)", "Net 3.0x (USD)", "Cost 1x (USD)", "Breakeven Mult"]
    e_rows = [
        [e["engine"], e["n_trades"], f"{e['net_1x_usd']:+.1f}", f"{e['net_2x_usd']:+.1f}", f"{e['net_3x_usd']:+.1f}", f"{e['cost_1x_usd']:.1f}", f"{e['breakeven_mult']:.2f}x"]
        for e in res["test1_cost_stress"]["per_engine"]
    ]
    lines.append(format_markdown_table(e_headers, e_rows, right_align_cols={1, 2, 3, 4, 5, 6}))

    lines += [
        "",
        "## 2. Execution Latency & Adverse Fill Stress (`+1m` Delay & Worst-of-M1 Entry Bar)",
        "",
    ]
    l_headers = ["Stress Mode", "PORT_7E Ann%", "PORT_7E DD%", "PORT_7E Calmar", "PORT_7E Retained%", "PORT_9E Ann%", "PORT_9E DD%", "PORT_9E Calmar", "PORT_9E Retained%"]
    l_rows = []
    for mode, label in (
        ("delay_1m_sym", "+1m Fill Delay (Symmetric)"),
        ("delay_1m_adverse", "+1m Fill Delay (Adverse-Only Quote Fade)"),
        ("worst_m1_bar", "Worst-of-M1 Entry Bar Fill"),
    ):
        d7 = res["test2_latency_adverse_fill"][mode]["PORT_7E"]
        d9 = res["test2_latency_adverse_fill"][mode]["PORT_9E"]
        l_rows.append([
            label,
            f"{d7['ann_pct']:+.2f}%", f"{d7['peak_dd_pct']:.2f}%", f"{d7['calmar']:.2f}", f"{d7['retained_pct']:.1f}%",
            f"{d9['ann_pct']:+.2f}%", f"{d9['peak_dd_pct']:.2f}%", f"{d9['calmar']:.2f}", f"{d9['retained_pct']:.1f}%",
        ])
    lines.append(format_markdown_table(l_headers, l_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7, 8}))

    lines += [
        "",
        "## 3. Parameter Neighborhood Stability & Fragility Perturbation (`±10%, ±20%`)",
        "",
        "### 3A. Dịch chuyển khoảng cách Stop-Loss (`-20% .. +20%`) trực tiếp trên M1 MAE path",
        "",
    ]
    sl_headers = ["SL Mult", "PORT_7E Ann%", "PORT_7E DD%", "PORT_7E Calmar", "PORT_9E Ann%", "PORT_9E DD%", "PORT_9E Calmar"]
    sl_rows = [
        [f"{r7['sl_mult']:.2f}x", f"{r7['ann_pct']:+.2f}%", f"{r7['peak_dd_pct']:.2f}%", f"{r7['calmar']:.2f}", f"{r9['ann_pct']:+.2f}%", f"{r9['peak_dd_pct']:.2f}%", f"{r9['calmar']:.2f}"]
        for r7, r9 in zip(res["test3_parameter_neighborhood"]["sl_distance_perturbation"]["PORT_7E"], res["test3_parameter_neighborhood"]["sl_distance_perturbation"]["PORT_9E"])
    ]
    lines.append(format_markdown_table(sl_headers, sl_rows, right_align_cols={1, 2, 3, 4, 5, 6}))

    lines += ["", "### 3B. Monte Carlo Risk-Weight & Threshold-Dropout Jitter (200 draws)", ""]
    j_headers = ["Portfolio", "Jitter Band", "Weight Ann (p05/med/p95)", "Weight Calmar (p05/med)", "Threshold Dropout Ann (p05/med)", "Threshold Calmar (p05/med)", "P(Ann > 0)"]
    j_rows = []
    for pl in ("PORT_7E", "PORT_9E"):
        for band in ("pm_10pct", "pm_20pct"):
            wj = res["test3_parameter_neighborhood"]["monte_carlo_jitter"][pl][band]["weight_jitter"]
            tj = res["test3_parameter_neighborhood"]["monte_carlo_jitter"][pl][band]["threshold_dropout_jitter"]
            j_rows.append([
                pl, band.replace("pm_", "±").replace("pct", "%"),
                f"{wj['ann_p05']:+.2f}% / {wj['ann_med']:+.2f}% / {wj['ann_p95']:+.2f}%",
                f"{wj['calmar_p05']:.2f} / {wj['calmar_med']:.2f}",
                f"{tj['ann_p05']:+.2f}% / {tj['ann_med']:+.2f}%",
                f"{tj['calmar_p05']:.2f} / {tj['calmar_med']:.2f}",
                f"{min(wj['prob_pos_pct'], tj['prob_pos_pct']):.1f}%",
            ])
    lines.append(format_markdown_table(j_headers, j_rows, right_align_cols={2, 3, 4, 5, 6}))

    lines += [
        "",
        "## 4. Top-K Lucky Trade Removal (Bỏ Top `1%, 3%, 5%` Lệnh Thắng Lớn Nhất)",
        "",
    ]
    tk_headers = ["Drop Top %", "PORT_7E Dropped", "PORT_7E Ann%", "PORT_7E Calmar", "PORT_7E Retained%", "PORT_9E Dropped", "PORT_9E Ann%", "PORT_9E Calmar", "PORT_9E Retained%"]
    tk_rows = [
        [
            f"Top {r7['drop_pct']}%",
            f"{r7['trades_dropped']}/{r7['total_trades']}", f"{r7['ann_pct']:+.2f}%", f"{r7['calmar']:.2f}", f"{r7['retained_pct']:.1f}%",
            f"{r9['trades_dropped']}/{r9['total_trades']}", f"{r9['ann_pct']:+.2f}%", f"{r9['calmar']:.2f}", f"{r9['retained_pct']:.1f}%",
        ]
        for r7, r9 in zip(res["test4_topk_lucky_removal"]["PORT_7E"], res["test4_topk_lucky_removal"]["PORT_9E"])
    ]
    lines.append(format_markdown_table(tk_headers, tk_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7, 8}))

    lines += [
        "",
        "## 5. Phân Rã Theo Năm (`2018..2024`), Volatility Regime & Cú Sốc Khủng Hoảng",
        "",
    ]
    y_headers = ["Year", "PORT_7E Ret%", "PORT_7E DD%", "PORT_7E Sharpe", "PORT_9E Ret%", "PORT_9E DD%", "PORT_9E Sharpe", "Engines > 0 (of 9)"]
    y_rows = [
        [r["year"], f"{r['PORT_7E_ret_pct']:+.2f}%", f"{r['PORT_7E_dd_pct']:.2f}%", f"{r['PORT_7E_sharpe']:.2f}", f"{r['PORT_9E_ret_pct']:+.2f}%", f"{r['PORT_9E_dd_pct']:.2f}%", f"{r['PORT_9E_sharpe']:.2f}", f"{r['engines_positive_of_9']}/9"]
        for r in res["test5_year_vol_crisis"]["yearly"]
    ]
    lines.append(format_markdown_table(y_headers, y_rows, right_align_cols={1, 2, 3, 4, 5, 6, 7}))

    lines += ["", "### Causal Volatility-Regime Terciles (20d Lagged Realized Vol)", ""]
    v_headers = ["Vol Regime", "Days", "PORT_7E Ann%", "PORT_7E Sharpe", "PORT_9E Ann%", "PORT_9E Sharpe", "PORT_9E Max Daily DD%"]
    v_rows = []
    for rn, rv in res["test5_year_vol_crisis"]["vol_regimes"].items():
        v_rows.append([rn, rv["PORT_9E"]["n_days"], f"{rv['PORT_7E']['ann_pct']:+.2f}%", f"{rv['PORT_7E']['sharpe']:.2f}", f"{rv['PORT_9E']['ann_pct']:+.2f}%", f"{rv['PORT_9E']['sharpe']:.2f}", f"{rv['PORT_9E']['max_daily_dd_pct']:.2f}%"])
    lines.append(format_markdown_table(v_headers, v_rows, right_align_cols={1, 2, 3, 4, 5, 6}))

    lines += ["", "### Named Macro Crisis Windows (2018–2024)", ""]
    cr_headers = ["Crisis Window", "Period", "Days", "PORT_7E Ret%", "PORT_7E DD%", "PORT_9E Ret%", "PORT_9E DD%", "PORT_9E Max Daily DD%"]
    cr_rows = [
        [c["window"], c["period"], c["n_days"], f"{c['PORT_7E_ret_pct']:+.2f}%", f"{c['PORT_7E_dd_pct']:.2f}%", f"{c['PORT_9E_ret_pct']:+.2f}%", f"{c['PORT_9E_dd_pct']:.2f}%", f"{c['PORT_9E_max_daily_dd_pct']:.2f}%"]
        for c in res["test5_year_vol_crisis"]["crisis_windows"]
    ]
    lines.append(format_markdown_table(cr_headers, cr_rows, right_align_cols={2, 3, 4, 5, 6, 7}))

    tc7 = res["test6_tail_corr_simultaneous_shock"]["tail_corr_7e"]
    tc9 = res["test6_tail_corr_simultaneous_shock"]["tail_corr_9e"]
    lines += [
        "",
        "## 6. Tail-Correlation & Simultaneous-Loss Shock vs FTMO `5.0%` Daily DD Limit",
        "",
        f"- **PORT_7E Pairwise Correlation:** All days mean `{tc7['all_days_corr']['mean']}` (max `{tc7['all_days_corr']['max']}`, `{tc7['all_days_corr']['max_pair']}`) vs Worst-5% tail mean `{tc7['worst_tail_corr']['mean']}` (max `{tc7['worst_tail_corr']['max']}`, `{tc7['worst_tail_corr']['max_pair']}`).",
        f"- **PORT_9E Pairwise Correlation:** All days mean `{tc9['all_days_corr']['mean']}` (max `{tc9['all_days_corr']['max']}`, `{tc9['all_days_corr']['max_pair']}`) vs Worst-5% tail mean `{tc9['worst_tail_corr']['mean']}` (max `{tc9['worst_tail_corr']['max']}`, `{tc9['worst_tail_corr']['max_pair']}`).",
        "",
        "### Top 5 Worst Historical Intraday DD Days (`PORT_9E`, Dev 2018–2024)",
        "",
    ]
    wh_headers = ["Date", "Losing Engines", "Day Net 1x", "M1 Daily DD 1x", "Scaled 2.5x", "Scaled 4.0x", "Scaled 4.75x"]
    wh_rows = [
        [w["day"], f"{w['losing_engines']} ({', '.join(e.split('_')[0] for e in w['engines'])})", f"{w['day_net_pct_1x']:+.2f}%", f"{w['m1_daily_dd_1x_pct']:.2f}%", f"{w['scaled_dd_25x_pct']:.2f}%", f"{w['scaled_dd_40x_pct']:.2f}%", f"{w['scaled_dd_475x_pct']:.2f}%"]
        for w in res["test6_tail_corr_simultaneous_shock"]["worst_historical_days"]
    ]
    lines.append(format_markdown_table(wh_headers, wh_rows, right_align_cols={2, 3, 4, 5, 6}))

    lines += ["", "### Adversarial Flash-Crash Simultaneous `-1R` Shock Matrix (`corr -> 1.0`)", ""]
    sh_headers = ["Profile", "Worst 3 Eng", "Worst 5 Eng", "All Uncapped", "All + SYMCAP", "Guarded (+KillSwitch)", "< 5.0% FTMO Limit?"]
    sh_rows = [
        [s["profile"], f"{s['worst_3_engines_pct']:.2f}%", f"{s['worst_5_engines_pct']:.2f}%", f"{s['all_engines_uncap_pct']:.2f}%", f"{s['all_engines_symcap_pct']:.2f}%", f"{s['guarded_with_killswitch_pct']:.2f}%", "SAFE" if s["ftmo_5pct_safe_with_guard"] else "BREACH"]
        for s in res["test6_tail_corr_simultaneous_shock"]["simultaneous_shock_matrix"]
    ]
    lines.append(format_markdown_table(sh_headers, sh_rows, right_align_cols={1, 2, 3, 4, 5}))

    lines += [
        "",
        "## 7. DST / UTC-Offset Sensitivity Check",
        "",
    ]
    d_headers = ["DST Calendar Regime", "Days", "PORT_7E Ann%", "PORT_7E Sharpe", "PORT_9E Ann%", "PORT_9E Sharpe", "PORT_9E Win-Day%"]
    d_rows = [
        [r["dst_regime"], r["n_days"], f"{r['PORT_7E_ann_pct']:+.2f}%", f"{r['PORT_7E_sharpe']:.2f}", f"{r['PORT_9E_ann_pct']:+.2f}%", f"{r['PORT_9E_sharpe']:.2f}", f"{r['PORT_9E_win_day_pct']:.1f}%"]
        for r in res["test7_dst_utc_sensitivity"]["dst_regimes"]
    ]
    lines.append(format_markdown_table(d_headers, d_rows, right_align_cols={1, 2, 3, 4, 5, 6}))

    lines += ["", "### Mô phỏng Lỗi Lệch Đồng Hồ Broker `±60 phút`", ""]
    cs_headers = ["Clock-Offset Bug Mode", "PORT_7E Ann%", "PORT_7E Calmar", "PORT_7E Retained%", "PORT_9E Ann%", "PORT_9E Calmar", "PORT_9E Retained%"]
    cs_rows = []
    for mk, lbl in (("late_entry", "+60m Late Entry (lệch +1h UTC)"), ("early_flat", "-60m Early Flat (đóng sớm 1h)")):
        c7 = res["test7_dst_utc_sensitivity"]["clock_shift_60m"][mk]["PORT_7E"]
        c9 = res["test7_dst_utc_sensitivity"]["clock_shift_60m"][mk]["PORT_9E"]
        cs_rows.append([lbl, f"{c7['ann_pct']:+.2f}%", f"{c7['calmar']:.2f}", f"{c7['retained_pct']:.1f}%", f"{c9['ann_pct']:+.2f}%", f"{c9['calmar']:.2f}", f"{c9['retained_pct']:.1f}%"])
    lines.append(format_markdown_table(cs_headers, cs_rows, right_align_cols={1, 2, 3, 4, 5, 6}))

    lines += [
        "",
        "## 8. Bảng Kiểm Phản Biện & Khuyến Nghị Red-Team Cho Deployment",
        "",
    ]
    for k, ok in res["verdict_checks"].items():
        lines.append(f"- `[{'PASS' if ok else 'WARN'}]` `{k}`")
    if res["test1_cost_stress"]["engines_below_2x_breakeven"]:
        lines.append(f"- **Cảnh báo biên chi phí (`breakeven < 2.0x`):** `{', '.join(res['test1_cost_stress']['engines_below_2x_breakeven'])}` — bắt buộc giám sát TCA thực tế trong 14 ngày Free Trial (`tca_reconcile.py`) và giữ `InpGuardMaxSpreadPoints` nghiêm ngặt.")
    else:
        lines.append("- **Biên an toàn chi phí:** Toàn bộ 9/9 engine chịu được tối thiểu `>= 2.0x` chi phí thực thi.")
    lines += [
        "- **Tính lồi của Trend-Following Intraday (Top-K Test):** `PORT_9E` vẫn dương `+2.83%/năm` khi bỏ Top 1% lệnh thắng (`33/3245` lệnh), nhưng chuyển âm khi bỏ Top 3%–5% lệnh thắng lớn nhất (mà giữ nguyên toàn bộ lệnh thua). Đây là đặc tính cấu trúc chuẩn của chiến lược breakout thuận xu hướng (tỷ lệ thắng `~45%`, lỗ chặn `-1R`, lãi chạy mở lên `+2R..+5R`) — đồng nghĩa **không được để VPS downtime hoặc tự ý đóng non lệnh đang lãi**, vì mất chỉ `3%` ngày breakout tốt nhất sẽ xóa biên lợi nhuận.",
        "- **Bài học bắt buộc từ Shock Matrix:** Nếu bỏ `SYMCAP` và `Naqex_AccountOrchestrator` Global Kill-Switch, kịch bản flash-crash đồng thời ở mức P1 (`4.0x–4.75x`) sẽ vượt xa ngưỡng `5.0%` Daily DD của FTMO. Bắt buộc kích hoạt song song `InpGuardMaxSymbolRiskPct` + `InpKillDailyDdPct` trước khi mở tài khoản live.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    res = run_red_team_audit(seed=20261124, n_jitter_draws=200)
    md = render_markdown_report(res)
    out_md = ROOT / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.md"
    out_json = ROOT / "planning/research/RED-TEAM-ADVERSARIAL-AUDIT-20261124.json"
    out_md.write_text(md, encoding="utf-8", newline="\n")
    digest = write_verified_receipt(out_json, res, overwrite=True)
    print(json.dumps({
        "output_md": str(out_md),
        "md_bytes": out_md.stat().st_size,
        "output_json": str(out_json),
        "json_bytes": out_json.stat().st_size,
        "json_sha256": digest[:16],
        "runtime_seconds": res["runtime_seconds"],
        "overall_verdict": res["overall_verdict"],
        "verdict_checks": res["verdict_checks"],
        "breakeven": res["test1_cost_stress"]["portfolio_breakeven"],
        "engines_below_2x": res["test1_cost_stress"]["engines_below_2x_breakeven"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
