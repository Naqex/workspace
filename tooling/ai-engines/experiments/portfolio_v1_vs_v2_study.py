"""Pre-Registered Dev Architecture Study: Portfolio v1 vs v2 (`2018-2024`, Holdout 2025+ SEALED).

STRICT SAFETY & ANTI-OVERFIT INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity; `holdout_rows_analysed = 0`, `ORDER_SEND_CAPABLE = False`.
  - Evaluates ONLY `m_total = 6` pre-registered portfolio architectures on identical M1 Prague-reset
    floating-equity replay (`max_symbol_concurrent_risk = 1.0%`, `±5m` official red-news guard).
  - Applies exact per-trade friction stress (`1.0x`, `1.5x`, `2.0x`) on every minute mark and runs
    `N = 5,000` Numba block-bootstrap Prop Lifecycle MC across `FTMO Swing 10K` and `The5ers High Stakes 5K`
    comparing BOTH `P1_Balanced_Static` and `Dyn_ProfitLock_45x`.
  - Never modifies live running v1 EAs on `naqex-node1` or `PORTFOLIO-REGISTRY.json`.
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
from native_ftmo_monfri_seal import ROOT, STOP
from quant_core.ftmo_track_replay import profiles
from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates, enforce_pre_holdout_ts
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.lab10_v2_robust_prop_accelerator import (
    _simulate_dynamic_pacing_numba,
    build_lab10_catalog,
    build_local_m1_bundle,
    evaluate_lab10_spec,
)
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
SEED: int = 20261124
MAX_SYMBOL_CONCURRENT_RISK: float = 0.010  # 1.0% per-symbol concurrent risk cap (FTMO trade-idea bundle rule)

# Pre-registered Robustness Gate tiers from ROBUSTNESS-GATE-DEV-AUDIT-20261124.md (ZERO tuning!)
ROBUST_TIER_MULT: dict[str, float] = {
    "E1_USDJPY_TOKYO": 0.50,    # FAIL_FRAGILE -> 0.5x
    "E2_USDJPY_EXP80": 0.75,    # WARN_ASYMMETRY_OR_YEAR -> 0.75x
    "E3_GBPUSD_VH": 1.00,       # PASS_ROBUST (4/4) -> 1.0x
    "E4_US100_SESS40": 0.50,    # FAIL_FRAGILE -> 0.5x
    "E5_US100_RS1130": 1.00,    # PASS_ROBUST (4/4) -> 1.0x
    "E6_EURJPY_VOLCOMP": 1.00,  # PASS_ROBUST (4/4) -> 1.0x
    "E7_USDJPY_NY10ET": 1.00,   # PASS_ROBUST (4/4) -> 1.0x
    "S6_FX_USD_BSK": 0.75,      # WARN_ASYMMETRY_OR_YEAR -> 0.75x
    "L10_B2_EURUSD_VOLCOMP75": 1.00,  # Lab #10 PASS_ROBUST (4/4, r=+0.02) -> 1.0x
}


def estimate_base_friction_usd_per_lot(row: dict[str, Any]) -> float:
    """Estimate conservative per-lot round-trip friction USD from exact tape row fields."""
    stop_cost = float(row.get("stop_risk_with_cost_usd") or 0.0)
    if stop_cost <= 0.0:
        return 0.0

    # 1. Exact difference when initial_risk_usd is recorded (E1, E2, E3, L10_B2)
    init_r = row.get("initial_risk_usd")
    if init_r is not None and float(init_r) > 0.0:
        diff = max(0.0, stop_cost - float(init_r))
        if diff > 0.0:
            return diff

    # 2. Exact difference from sl_price & entry_price when available (E4..S7)
    ep = row.get("entry_price")
    slp = row.get("sl_price") or row.get("stop")
    asset = str(row.get("asset") or "")
    if ep is not None and slp is not None and float(ep) > 0.0 and float(slp) > 0.0:
        dist = abs(float(ep) - float(slp))
        if asset in ("EURUSD", "GBPUSD", "AUDUSD"):
            raw_sl = dist * 100_000.0
        elif asset in ("USDJPY", "EURJPY", "GBPJPY"):
            # For JPY crosses, approximate JPY/USD using entry_price on USDJPY or 150 fallback
            usd_jpy = float(ep) if asset == "USDJPY" else 135.0
            raw_sl = dist * 100_000.0 / max(80.0, usd_jpy)
        elif asset in ("US100", "US500", "GER40"):
            raw_sl = dist * 1.0
        elif asset == "XAUUSD":
            raw_sl = dist * 100.0
        else:
            raw_sl = stop_cost * 0.96
        if 0.50 * stop_cost <= raw_sl < stop_cost:
            return max(stop_cost - raw_sl, 0.03 * stop_cost)

    # 3. Conservative floor (3.5% of 1R stop risk = ~3.5 bps/stop friction baseline)
    return 0.035 * stop_cost


def apply_cost_stress_to_tapes(
    tapes: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]],
    cost_mult: float,
) -> dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]]:
    """Return a copy of M1 tapes shifted dollar-for-dollar by `(cost_mult - 1.0) * base_friction_usd_per_lot`."""
    if abs(cost_mult - 1.0) < 1e-9:
        return tapes
    delta_factor = float(cost_mult) - 1.0
    stressed: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
    for eng, dm in tapes.items():
        new_dm: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
        for dk, (row, stamps, marks) in dm.items():
            base_fric = estimate_base_friction_usd_per_lot(row)
            extra = delta_factor * base_fric
            new_row = {
                **row,
                "net_usd_per_lot": float(row["net_usd_per_lot"]) - extra,
                "stop_risk_with_cost_usd": float(row["stop_risk_with_cost_usd"]) + extra,
            }
            new_marks = np.asarray(marks, dtype=np.float64) - extra
            new_dm[dk] = (new_row, stamps, new_marks)
        stressed[eng] = new_dm
    return stressed


def build_l10_b2_eurusd_m1_tape(
    swing_specs: dict[str, dict],
    usdjpy_close_map: dict,
) -> dict[str, tuple[dict, np.ndarray, np.ndarray]]:
    """Build exact minute-by-minute M1 floating-equity tape for `L10_B2_EURUSD_VOLCOMP75` (`< 2025-01-01`)."""
    catalog = {c["id"]: c for c in build_lab10_catalog()}
    cfg = catalog["L10_B2_EURUSD_VOLCOMP75"]
    bundle = build_local_m1_bundle("EURUSD", swing_specs, usdjpy_close_map)
    trs, _ = evaluate_lab10_spec(bundle, cfg)

    times = bundle["times"]
    quotes = bundle["quotes"]
    spec = bundle["spec"]
    contract = float(spec["trade_contract_size"]) if spec else 100_000.0

    day_lookup = {d["day"]: d for d in bundle["days"]}
    tape: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
    for tr in trs:
        dk = str(tr["day"])
        if dk >= "2025-01-01":
            raise HoldoutLockError(f"HOLDOUT_CONTAMINATION_L10_B2:{dk}")
        dinfo = day_lookup.get(dk)
        if dinfo is None:
            continue
        fi, li = int(dinfo["fi"]), int(dinfo["flat_idx"])
        sub_t = times[fi:li + 1]
        sub_q = quotes[fi:li + 1]
        entry_ts = int(tr["entry"])
        exit_ts = int(tr["exit"])
        s_rel = int(sub_t.searchsorted(entry_ts, side="left"))
        e_rel = int(sub_t.searchsorted(exit_ts, side="right")) - 1
        s_rel = max(0, min(s_rel, len(sub_t) - 1))
        e_rel = max(s_rel, min(e_rel, len(sub_t) - 1))

        stamps = np.asarray(sub_t[s_rel:e_rel + 1], dtype=np.int64)
        sl_q = sub_q[s_rel:e_rel + 1]
        side = int(tr["side"])
        ep = float(sl_q[0, 4] if side == 1 else sl_q[0, 0])
        fric_usd = float(tr["ftmo_comm_slip"])
        net_usd = float(tr["ftmo_net"])
        ftmo_r = float(tr["ftmo_R"])
        if abs(ftmo_r) > 1e-6:
            stop_risk_with_cost_usd = abs(net_usd / ftmo_r)
        else:
            stop_risk_with_cost_usd = float(tr["sl_frac"]) * ep * contract + fric_usd
        init_risk_usd = max(1.0, stop_risk_with_cost_usd - fric_usd)

        # Floating mark-to-market per 1.0 lot in USD (EURUSD quote currency is USD)
        if side == 1:
            marks = (sl_q[:, 0:4] - ep) * contract - fric_usd
        else:
            marks = (ep - sl_q[:, 4:8]) * contract - fric_usd
        marks = np.asarray(marks, dtype=np.float64)
        marks = np.maximum(marks, -stop_risk_with_cost_usd)
        marks[-1, -1] = net_usd

        row = {
            "day": dk,
            "year": int(dk[:4]),
            "asset": "EURUSD",
            "entry": int(stamps[0]),
            "exit": int(stamps[-1]),
            "at_open": False,
            "reason": str(tr["reason"]),
            "side": side,
            "entry_price": ep,
            "sl_price": ep - side * (init_risk_usd / contract),
            "initial_risk_usd": init_risk_usd,
            "stop_risk_with_cost_usd": stop_risk_with_cost_usd,
            "net_usd_per_lot": net_usd,
            "net_R": ftmo_r,
        }
        tape[dk] = (row, stamps, marks)
    return tape


def build_preregistered_architectures(base_r: dict[str, float]) -> list[tuple[str, str, dict[str, float]]]:
    """Return the exact `m_total = 6` pre-registered portfolio architectures (ZERO post-hoc tuning)."""
    core7 = ["E1_USDJPY_TOKYO", "E2_USDJPY_EXP80", "E3_GBPUSD_VH", "E4_US100_SESS40",
             "E5_US100_RS1130", "E6_EURJPY_VOLCOMP", "E7_USDJPY_NY10ET"]
    live8 = [*core7, "S6_FX_USD_BSK"]
    prune6 = ["E2_USDJPY_EXP80", "E3_GBPUSD_VH", "E5_US100_RS1130", "E6_EURJPY_VOLCOMP", "E7_USDJPY_NY10ET", "S6_FX_USD_BSK"]
    pure4 = ["E3_GBPUSD_VH", "E5_US100_RS1130", "E6_EURJPY_VOLCOMP", "E7_USDJPY_NY10ET"]

    r_live8 = {k: base_r[k] for k in live8}
    sum_live8 = sum(r_live8.values())

    def _norm(raw: dict[str, float], target_sum: float) -> dict[str, float]:
        s = sum(raw.values())
        scale = (target_sum / s) if s > 1e-12 else 1.0
        return {k: round(v * scale, 6) for k, v in raw.items()}

    # Normalize v2 architectures to the exact same nominal risk sum as live8 so comparisons are risk-matched!
    r_tier8 = _norm({k: base_r[k] * ROBUST_TIER_MULT[k] for k in live8}, sum_live8)
    r_prune6 = _norm({k: base_r[k] * ROBUST_TIER_MULT[k] for k in prune6}, sum_live8)
    r_pure4 = _norm({k: base_r[k] for k in pure4}, sum_live8)
    r_tier_plus_eur = _norm(
        {**{k: base_r[k] * ROBUST_TIER_MULT[k] for k in live8}, "L10_B2_EURUSD_VOLCOMP75": 0.0050},
        sum_live8,
    )

    return [
        ("A0_V1_CORE7_INCUMBENT",   "Frozen PORT_7E (E1..E7)", {k: base_r[k] for k in core7}),
        ("A1_V1_LIVE8_INCUMBENT",   "Live 8 EA on naqex-node1 (E1..E7 + S6)", r_live8),
        ("A2_V2_ROBUST_TIER_8E",    "Live 8 EA tilted by Robustness Gate (PASS 1x / WARN 0.75x / FAIL 0.5x)", r_tier8),
        ("A3_V2_PRUNE_FRAGILE_6E",  "Drop FAIL_FRAGILE (E1, E4); keep 6 robust/warn engines", r_prune6),
        ("A4_V2_PURE_PASS_4E",      "Pure 4/4 PASS_ROBUST only (E3, E5, E6, E7)", r_pure4),
        ("A5_V2_ROBUST_TIER_9E_EUR","A2 Robust-Tier + L10_B2_EURUSD_VOLCOMP75 (r=+0.02)", r_tier_plus_eur),
    ]


def compute_yearly_stats(exits: list[dict], initial: float = 10000.0) -> dict[str, Any]:
    by_yr: dict[str, float] = defaultdict(float)
    for y in range(2018, 2025):
        by_yr[str(y)] = 0.0
    trades_total = 0
    for ex in exits:
        by_yr[str(ex["day"])[:4]] += float(ex["net_usd"])
        trades_total += sum(1 for o in ex.get("orders", []) if o.get("status") == "SIZED")
    yr_pct = {y: round(100.0 * v / initial, 2) for y, v in sorted(by_yr.items())}
    worst_yr = min(yr_pct.items(), key=lambda kv: kv[1])
    pos_yrs = sum(1 for v in yr_pct.values() if v > 0.0)
    return {
        "yearly_pct": yr_pct,
        "worst_year": worst_yr[0],
        "worst_year_pct": worst_yr[1],
        "positive_years": pos_yrs,
        "trades_total": trades_total,
        "trades_per_year": round(trades_total / 7.0, 1),
    }


def evaluate_prop_mc(
    nets: np.ndarray,
    dds: np.ndarray,
    flg: np.ndarray,
    idx_mat: np.ndarray,
    firms: list[dict],
) -> dict[str, dict[str, dict[str, Any]]]:
    policies = [
        ("P1_Balanced_Static", 4.00, 4.00, 4.00, 2.00, 2.00, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030),
        ("Dyn_ProfitLock_45x", 4.50, 3.00, 2.00, 2.50, 1.50, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030),
    ]
    n_paths = idx_mat.shape[0]
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for fcfg in firms:
        fid = fcfg["id"]
        out[fid] = {}
        for (pname, p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st) in policies:
            pd, py, cf, oop, br, wp, tx = _simulate_dynamic_pacing_numba(
                idx_mat, nets, dds, flg,
                int(fcfg["steps"]), float(fcfg["capital_usd"]), float(fcfg["fee_usd"]),
                float(fcfg.get("fee_refund_ratio", 1.0)),
                float(fcfg["p1_target_pct"]), float(fcfg["p2_target_pct"]),
                float(fcfg["daily_loss_pct"]), float(fcfg["static_loss_pct"]),
                bool(fcfg.get("daily_pause_non_breaching", False)),
                int(fcfg["min_days"]), float(fcfg.get("min_profitable_day_pct", 0.0)),
                float(fcfg["payout_split"]), int(fcfg["payout_cycle_days"]), 4,
                p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st,
            )
            passed = pd[pd > 0]
            paid = py[py > 0]
            out[fid][pname] = {
                "pass_24m_pct": round(100.0 * len(passed) / n_paths, 1),
                "med_days_pass": int(np.median(passed)) if len(passed) else -1,
                "med_days_pay1": int(np.median(paid)) if len(paid) else -1,
                "breach_pct": round(100.0 * float(np.mean(br)), 1),
                "wipeout_pct": round(100.0 * float(np.mean(wp)), 2),
                "oop95_usd": round(float(np.quantile(oop, 0.95)), 1),
                "ev_24m_usd": round(float(np.mean(cf)), 1),
                "ev_per_fee": round(float(np.mean(cf)) / max(1.0, float(fcfg["fee_usd"])), 2),
            }
    return out


def run_study(*, n_paths: int = 5000, write_report: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    red_news = load_red_news_calendar("red_news_official_2018_2024")
    tapes_1x = dict(warm["tapes"])
    ext_days = list(warm["ext_days"])
    enforce_pre_holdout_dates(ext_days, context="portfolio_v1_vs_v2.ext_days")

    # Build L10_B2_EURUSD_VOLCOMP75 exact M1 tape locally (0 holdout rows)
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, q_j, _ = hcache.load_asset("USDJPY", verify_sha=False)
    enforce_pre_holdout_ts(int(ts_j[-1]), stop_ts=STOP, context="portfolio_v1_vs_v2.usdjpy")
    day_j = (ts_j // 86400).astype(np.int64)
    chg_j = np.r_[True, day_j[1:] != day_j[:-1]]
    starts_j = np.flatnonzero(chg_j)
    ends_j = np.r_[starts_j[1:] - 1, len(day_j) - 1]
    usdjpy_close_map = {
        datetime.fromtimestamp(int(ts_j[ei]), timezone.utc).date(): float(q_j[ei, 3])
        for ei in ends_j
    }
    l10_tape = build_l10_b2_eurusd_m1_tape(swing_specs, usdjpy_close_map)
    tapes_1x["L10_B2_EURUSD_VOLCOMP75"] = l10_tape
    union_days = sorted(set(ext_days) | set(l10_tape.keys()))
    enforce_pre_holdout_dates(union_days, context="portfolio_v1_vs_v2.union_days")

    # Pre-build exact 1.5x and 2.0x cost-stressed M1 tapes
    tapes_15x = apply_cost_stress_to_tapes(tapes_1x, 1.5)
    tapes_20x = apply_cost_stress_to_tapes(tapes_1x, 2.0)

    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    archs = build_preregistered_architectures(base_r)
    firms = [load_firm_config(f) for f in ("ftmo_swing_10k", "the5ers_high_stakes_5k")]
    idx_mat = make_block_bootstrap_indices(len(union_days), horizon=504, n_paths=n_paths, block_len=5, seed=SEED)

    results: list[dict[str, Any]] = []
    for arch_id, desc, risks in archs:
        m1_1x, ex_1x = replay_portfolio_m1(
            union_days, tapes_1x, risks, 10000.0,
            profile_mode="Swing",
            max_symbol_concurrent_risk=MAX_SYMBOL_CONCURRENT_RISK,
            red_news_cal=red_news,
        )
        m1_15x, _ = replay_portfolio_m1(
            union_days, tapes_15x, risks, 10000.0,
            profile_mode="Swing",
            max_symbol_concurrent_risk=MAX_SYMBOL_CONCURRENT_RISK,
            red_news_cal=red_news,
        )
        m1_20x, _ = replay_portfolio_m1(
            union_days, tapes_20x, risks, 10000.0,
            profile_mode="Swing",
            max_symbol_concurrent_risk=MAX_SYMBOL_CONCURRENT_RISK,
            red_news_cal=red_news,
        )
        yr_stats = compute_yearly_stats(ex_1x, 10000.0)
        nets, dds, flg = exits_to_daily_arrays(union_days, ex_1x)
        prop_mc = evaluate_prop_mc(nets, dds, flg, idx_mat, firms)

        # Also run Prop MC under 1.5x cost stress for real-world slippage durability!
        _, ex_15x = replay_portfolio_m1(
            union_days, tapes_15x, risks, 10000.0,
            profile_mode="Swing",
            max_symbol_concurrent_risk=MAX_SYMBOL_CONCURRENT_RISK,
            red_news_cal=red_news,
        )
        nets15, dds15, flg15 = exits_to_daily_arrays(union_days, ex_15x)
        prop_mc_15x = evaluate_prop_mc(nets15, dds15, flg15, idx_mat, firms)

        results.append({
            "arch_id": arch_id,
            "description": desc,
            "n_engines": len(risks),
            "risk_weights_pct": {k: round(v * 100.0, 4) for k, v in risks.items()},
            "m1_1x": m1_1x,
            "m1_15x": m1_15x,
            "m1_20x": m1_20x,
            "yearly": yr_stats,
            "prop_mc_1x": prop_mc,
            "prop_mc_15x": prop_mc_15x,
        })

    # Apply pre-registered promotion gate vs incumbent A1_V1_LIVE8_INCUMBENT
    inc = next(r for r in results if r["arch_id"] == "A1_V1_LIVE8_INCUMBENT")
    for r in results:
        if r["arch_id"] in ("A0_V1_CORE7_INCUMBENT", "A1_V1_LIVE8_INCUMBENT"):
            r["verdict_vs_v1"] = "INCUMBENT_BASELINE"
            r["gates_won"] = 0
            continue
        g_calmar15 = r["m1_15x"]["calmar"] > inc["m1_15x"]["calmar"]
        g_worst_yr = r["yearly"]["worst_year_pct"] > inc["yearly"]["worst_year_pct"]
        g_cluster_b = r["m1_1x"]["ann_pct"]["B"] >= inc["m1_1x"]["ann_pct"]["B"] - 0.15
        ftmo_r = r["prop_mc_1x"]["FTMO_SWING_10K"]["P1_Balanced_Static"]
        ftmo_i = inc["prop_mc_1x"]["FTMO_SWING_10K"]["P1_Balanced_Static"]
        g_prop = (
            ftmo_r["wipeout_pct"] <= ftmo_i["wipeout_pct"]
            and ftmo_r["breach_pct"] <= ftmo_i["breach_pct"] + 0.5
            and (ftmo_r["ev_per_fee"] > ftmo_i["ev_per_fee"] or ftmo_r["med_days_pass"] < ftmo_i["med_days_pass"])
        )
        wins = int(g_calmar15) + int(g_worst_yr) + int(g_cluster_b) + int(g_prop)
        r["gates_detail"] = {
            "calmar_15x_beats_v1": g_calmar15,
            "worst_yr_beats_v1": g_worst_yr,
            "cluster_b_non_degraded": g_cluster_b,
            "prop_ev_or_speed_beats_v1": g_prop,
        }
        r["gates_won"] = wins
        if wins >= 3 and g_cluster_b and ftmo_r["wipeout_pct"] == 0.0:
            r["verdict_vs_v1"] = "PROMOTE_CANDIDATE_V2"
        elif wins >= 2:
            r["verdict_vs_v1"] = "MIXED_TRADEOFF_KEEP_V1_DEFAULT"
        else:
            r["verdict_vs_v1"] = "REJECT_INFERIOR_TO_V1"

    elapsed = round(time.perf_counter() - t0, 2)
    payload = {
        "schema": "naqex-portfolio-v1-vs-v2-architecture-study-v1",
        "generated_utc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "dev_window": f"{union_days[0]}..{union_days[-1]}",
        "m_total_architectures": len(results),
        "max_symbol_concurrent_risk_pct": round(MAX_SYMBOL_CONCURRENT_RISK * 100.0, 2),
        "red_news_guard": "FLATTEN_5M_OFFICIAL_2018_2024",
        "mc_paths": n_paths,
        "elapsed_sec": elapsed,
        "architectures": results,
    }

    if write_report:
        out_dir = ROOT / "planning/research"
        write_verified_receipt(out_dir / "PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.json", payload)
        md = render_markdown_report(payload)
        (out_dir / "PORTFOLIO-V1-VS-V2-ARCHITECTURE-STUDY-20261124.md").write_text(md, encoding="utf-8", newline="\n")

    return payload


def render_markdown_report(payload: dict[str, Any]) -> str:
    lines = [
        "# Nghiên Cứu Chốt Kiến Trúc Danh Mục: `Portfolio v1` vs `Portfolio v2` (Dev `2018–2024`, Holdout `2025+` Niêm Phong)",
        "",
        f"- **Phạm vi dữ liệu:** `{payload['dev_window']}` (`holdout_rows_analysed = 0`, `order_send_count = 0`, `m_total = {payload['m_total_architectures']}` cấu trúc đăng ký trước, thời gian chạy `{payload['elapsed_sec']}s`).",
        f"- **Chuẩn thực thi M1 giống nhau 100%:** Floating-equity Prague-reset, `max_symbol_concurrent_risk = {payload['max_symbol_concurrent_risk_pct']}%`, chặn tin đỏ chính thức `±5m`, cùng `seed = {SEED}` (`N = {payload['mc_paths']}` đường MC).",
        "",
        "## 1. Bảng So Sánh Hiệu Suất & Kháng Chi Phí (`1.0×` / `1.5×` / `2.0×` Friction)",
        "",
    ]
    t1_headers = ["Kiến trúc", "EAs", "Trd/Yr", "Ann 1x%", "Cl.A / Cl.B%", "Peak DD%", "Calmar 1x", "Calmar 1.5x", "Calmar 2.0x", "Năm tệ nhất", "+Yrs", "Kết luận"]
    t1_rows = []
    for r in payload["architectures"]:
        m1, m15, m20, yr = r["m1_1x"], r["m1_15x"], r["m1_20x"], r["yearly"]
        t1_rows.append([
            r["arch_id"],
            str(r["n_engines"]),
            f"{yr['trades_per_year']:.0f}",
            f"+{m1['ann_pct']['all']:.2f}%",
            f"{m1['ann_pct']['A']:+.1f}/{m1['ann_pct']['B']:+.1f}",
            f"{m1['peak_dd_pct']:.2f}%",
            f"{m1['calmar']:.2f}",
            f"{m15['calmar']:.2f}",
            f"{m20['calmar']:.2f}",
            f"{yr['worst_year']} ({yr['worst_year_pct']:+.2f}%)",
            f"{yr['positive_years']}/7",
            r["verdict_vs_v1"],
        ])
    lines.append(format_markdown_table(t1_headers, t1_rows))
    lines.extend([
        "",
        "## 2. Mô Phỏng Vòng Đời Prop Firm (`N = 5,000` Đường MC — `1.0×` & Stress `1.5×` Chi Phí)",
        "",
    ])
    t2_headers = ["Kiến trúc", "Quỹ / Policy", "Pass 24m% (1x / 1.5x)", "Med Days Pass", "Breach%", "Wipeout%", "OOP95 USD", "EV/Fee (1x / 1.5x)"]
    t2_rows = []
    for r in payload["architectures"]:
        for fid in ("FTMO_SWING_10K", "THE5ERS_HS_5K"):
            for pol in ("P1_Balanced_Static", "Dyn_ProfitLock_45x"):
                p1 = r["prop_mc_1x"][fid][pol]
                p15 = r["prop_mc_15x"][fid][pol]
                t2_rows.append([
                    r["arch_id"],
                    f"{fid} · {pol}",
                    f"{p1['pass_24m_pct']:.1f}% / {p15['pass_24m_pct']:.1f}%",
                    f"{p1['med_days_pass']}d / {p15['med_days_pass']}d",
                    f"{p1['breach_pct']:.1f}%",
                    f"{p1['wipeout_pct']:.2f}%",
                    f"{p1['oop95_usd']:.0f}",
                    f"+{p1['ev_per_fee']:.2f}x / +{p15['ev_per_fee']:.2f}x",
                ])
    lines.append(format_markdown_table(t2_headers, t2_rows))
    lines.extend([
        "",
        "## 3. Phân Tích Theo Từng Năm Dương Lịch (`2018–2024`, M1 `1.0×`)",
        "",
    ])
    t3_headers = ["Kiến trúc", "2018", "2019", "2020", "2021", "2022", "2023", "2024"]
    t3_rows = []
    for r in payload["architectures"]:
        yp = r["yearly"]["yearly_pct"]
        t3_rows.append([r["arch_id"]] + [f"{yp[str(y)]:+.2f}%" for y in range(2018, 2025)])
    lines.append(format_markdown_table(t3_headers, t3_rows))
    lines.append("")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Pre-Registered Portfolio v1 vs v2 Architecture Study (Dev 2018-2024)")
    ap.add_argument("--paths", type=int, default=5000)
    ap.add_argument("--no-write", action="store_true")
    args = ap.parse_args(argv)
    res = run_study(n_paths=args.paths, write_report=not args.no_write)
    for r in res["architectures"]:
        m1, m15, m20, yr = r["m1_1x"], r["m1_15x"], r["m1_20x"], r["yearly"]
        f_bal = r["prop_mc_1x"]["FTMO_SWING_10K"]["P1_Balanced_Static"]
        f_dyn = r["prop_mc_1x"]["FTMO_SWING_10K"]["Dyn_ProfitLock_45x"]
        t_bal = r["prop_mc_1x"]["THE5ERS_HS_5K"]["P1_Balanced_Static"]
        print(
            f"{r['arch_id']:26s} | Ann={m1['ann_pct']['all']:5.2f}% (A:{m1['ann_pct']['A']:+5.2f}/B:{m1['ann_pct']['B']:+5.2f}) "
            f"| DD={m1['peak_dd_pct']:4.2f}% | Cal={m1['calmar']:4.2f}/{m15['calmar']:4.2f}/{m20['calmar']:4.2f} "
            f"| WorstYr={yr['worst_year']}:{yr['worst_year_pct']:+5.2f}% | FTMO_Bal={f_bal['pass_24m_pct']:4.1f}%({f_bal['med_days_pass']}d,{f_bal['ev_per_fee']:+.2f}x) "
            f"| FTMO_Dyn={f_dyn['pass_24m_pct']:4.1f}%({f_dyn['med_days_pass']}d) | 5ers_Bal={t_bal['ev_per_fee']:+.2f}x | {r['verdict_vs_v1']}"
        )
    print(f"DONE elapsed={res['elapsed_sec']}s holdout_rows={res['holdout_rows_analysed']} order_send={res['order_send_count']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
