"""M4.2 — Pass 30: Extended FX Intraday Discovery (AUDUSD, USDCAD, EURJPY, GBPJPY — DEV < 2025-01-01 ONLY!).

STRICT SEALED DEVELOPMENT BOUNDARY (< 2025-01-01 ONLY):
  - Asserts NATIVE_FTMO_HOLDOUT_LOCK.json SHA integrity on startup.
  - Reads ONLY .runtime/hot-m1-cache/ (verified max_ts < 2025-01-01T00:00:00Z, holdout_rows = 0).
  - Cluster A (Discovery): 2018-2021; Blind Cluster B (Validation): 2022-2024.
  - Intraday swap = 0, hard server SL on every trade, Native M1 Bid/Ask (Base / Stress / Double).
  - 3 pre-registered economic families (m_total = 24 across AUDUSD, USDCAD, EURJPY, GBPJPY):
      F1: Overnight Gap Fade (Asian/overnight dislocation reversion at London open)
      F2: London Open Range Breakout + Causal Volatility Filter (compression & expansion)
      F3: Cross-Currency Relative-Strength Intraday (causal G6 factor spread at 10:00 UTC & 13:00 UTC)
  - Full statistical audit: BH-FDR over m_total = 24, Sign-Flip Null (N=1,000), Matched-Hold Timing Null (N=500),
    daily correlation vs PORT_7E, and exact impact on PORT_7E Cluster B Calmar & FTMO P1 pass time!
  - Retains ALL negative/failed results honestly.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from math import fsum
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
import pass27_portfolio_m1_phase_audit as p27
import pass28_final_discovery_rednews_frontier as p28
from native_ftmo_monfri_seal import STOP
from quant_core.ftmo_track_replay import profiles
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_registry,
)
from quant_factory.eval_pipeline import benjamini_hochberg, sign_flip_p_numba
from quant_factory.pass29_gold_index_dev import (
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    MATCHED_HOLD_DRAWS,
    SEED,
    SIGN_FLIP_DRAWS,
    _market_entry_window,
    _stop_breakout_window,
    compute_matched_hold_p,
    split_stats,
)
from quant_factory.prop_engine import evaluate_firm_profile, make_block_bootstrap_indices, replay_portfolio_m1

TARGET_FX4: tuple[str, ...] = ("AUDUSD", "USDCAD", "EURJPY", "GBPJPY")
FX7_ALL: tuple[str, ...] = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY")


def build_pass30_catalog() -> list[dict[str, Any]]:
    """Pre-registered 24-spec catalog across 3 economic families on AUDUSD, USDCAD, EURJPY, GBPJPY."""
    specs: list[dict[str, Any]] = []
    # Family 1: Overnight Gap Fade (8 specs)
    for asset in TARGET_FX4:
        specs.append({
            "id": f"P30_F1_{asset}_ON_GAP_FADE_35_TP",
            "fam": "F1_OVERNIGHT_GAP_FADE",
            "asset": asset,
            "kind": "ON_FADE_TP",
            "thr": 0.35,
            "sl_atr": 0.70,
        })
        specs.append({
            "id": f"P30_F1_{asset}_ON_GAP_FADE_50_RAW",
            "fam": "F1_OVERNIGHT_GAP_FADE",
            "asset": asset,
            "kind": "ON_FADE_RAW",
            "thr": 0.50,
            "sl_atr": 0.75,
        })
    # Family 2: London Open Range Breakout + Causal Vol Filter (8 specs)
    for asset in TARGET_FX4:
        specs.append({
            "id": f"P30_F2_{asset}_LDN_ORB90_VOLCOMP",
            "fam": "F2_LONDON_ORB_VOL_FILTER",
            "asset": asset,
            "kind": "ORB90_COMP",
            "thr": 0.90,  # max causal vol_ratio_5_20
            "sl_atr": 0.75,
        })
        specs.append({
            "id": f"P30_F2_{asset}_LDN_ORB120_VOLEXP",
            "fam": "F2_LONDON_ORB_VOL_FILTER",
            "asset": asset,
            "kind": "ORB120_EXP",
            "thr": 1.05,  # min prior-day range / ATR
            "sl_atr": 0.75,
        })
    # Family 3: Cross-Currency Relative-Strength Intraday (8 specs)
    for asset in TARGET_FX4:
        specs.append({
            "id": f"P30_F3_{asset}_CCY_RS_10UTC",
            "fam": "F3_CROSS_CCY_RS_INTRADAY",
            "asset": asset,
            "kind": "CCY_RS_10U",
            "thr": 0.30,
            "sl_atr": 0.75,
        })
        specs.append({
            "id": f"P30_F3_{asset}_CCY_RS_13UTC",
            "fam": "F3_CROSS_CCY_RS_INTRADAY",
            "asset": asset,
            "kind": "CCY_RS_13U",
            "thr": 0.30,
            "sl_atr": 0.75,
        })
    return specs


def _compute_prev_range_ratio_map(bundle: dict[str, Any]) -> dict[str, float]:
    """Strictly causal prior-day (H-L)/ATR ratio per day_iso (using completed day t-1)."""
    days = bundle["days"]
    quotes = bundle["quotes"]
    out: dict[str, float] = {}
    for i in range(1, len(days)):
        prev_d = days[i - 1]
        q = quotes[prev_d["fi"]:prev_d["flat_idx"] + 1]
        if len(q) > 0 and days[i]["atr"] > 1e-9:
            rng = float(q[:, 1].max() - q[:, 2].min())
            out[days[i]["day"]] = rng / float(days[i]["atr"])
    return out


def eval_pass30_spec(
    bundles: dict[str, Any],
    day_maps: dict[str, dict[str, Any]],
    all_days: list[str],
    vol_ratios: dict[str, dict[str, float]],
    prev_rng_ratios: dict[str, dict[str, float]],
    cfg: dict[str, Any],
    *,
    build_m1_tape: bool = False,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, tuple]]:
    asset = cfg["asset"]
    kind = cfg["kind"]
    thr = float(cfg["thr"])
    sl_atr = float(cfg["sl_atr"])
    b = bundles[asset]
    times, quotes = b["times"], b["quotes"]
    trs, fds = [], []
    tape_out: dict[str, tuple] = {}

    for dk in all_days:
        if dk not in day_maps[asset]:
            continue
        d = day_maps[asset][dk]
        dsec = d["day_sec"]
        atr = float(d["atr"])
        tr = fd = None
        tape_args: tuple[int, int, int, float, float] | None = None

        if kind in ("ON_FADE_TP", "ON_FADE_RAW"):
            ts_e = dsec + 7 * 3600
            ts_f = dsec + (14 * 3600 if kind == "ON_FADE_TP" else 16 * 3600)
            p_ldn = p26.causal_completed_bid(times, quotes, ts_e)
            if p_ldn is not None:
                mv = p_ldn - float(d["prev_c"])
                if abs(mv) / atr >= thr:
                    side = -1 if mv > 0 else 1
                    tp_d = 0.50 * abs(mv) if kind == "ON_FADE_TP" else None
                    tr, fd = _market_entry_window(b, d, ts_e, ts_f, side, sl_atr, tp_dist=tp_d, win_start_ts=dsec + 6 * 3600)
                    if build_m1_tape and tr is not None:
                        m = tr["_meta"]
                        ep = float(quotes[m["e_idx"], 4] if side == 1 else quotes[m["e_idx"], 0])
                        tape_args = (m["e_idx"], m["flat_idx"], side, ep, ep - side * sl_atr * atr)

        elif kind in ("ORB90_COMP", "ORB120_EXP"):
            if kind == "ORB90_COMP":
                vr = vol_ratios[asset].get(dk)
                if vr is None or vr >= thr:
                    continue
                ts_o0, ts_o1, ts_we = dsec + 7 * 3600, dsec + 8 * 3600 + 30 * 60, dsec + 17 * 3600
                max_box_atr = 0.65
            else:
                pr = prev_rng_ratios[asset].get(dk)
                if pr is None or pr < thr:
                    continue
                ts_o0, ts_o1, ts_we = dsec + 7 * 3600, dsec + 9 * 3600, dsec + 17 * 3600
                max_box_atr = 0.55
            m0 = int(times.searchsorted(ts_o0, side="left"))
            m1 = int(times.searchsorted(ts_o1, side="left"))
            if m1 - m0 >= 30:
                box = quotes[m0:m1]
                bh, bl = float(box[:, 1].max()), float(box[:, 2].min())
                brng = bh - bl
                if 1e-9 < brng <= max_box_atr * atr:
                    tr, fd = _stop_breakout_window(b, d, ts_o1, ts_we, bh, bl, sl_atr)
                    if build_m1_tape and tr is not None:
                        m = tr["_meta"]
                        side = m["side"]
                        ep = max(bh, float(quotes[m["e_idx"], 4])) if side == 1 else min(bl, float(quotes[m["e_idx"], 0]))
                        tape_args = (m["e_idx"], d["flat_idx"], side, ep, ep - side * sl_atr * atr)

        elif kind in ("CCY_RS_10U", "CCY_RS_13U"):
            if not all(dk in day_maps[a] for a in FX7_ALL):
                continue
            ts_e = dsec + (10 * 3600 if kind == "CCY_RS_10U" else 13 * 3600)
            ts_s = ts_e - (4 * 3600 if kind == "CCY_RS_10U" else 5 * 3600)
            z_map = {a: p26.causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"]) for a in FX7_ALL}
            if any(v is None for v in z_map.values()):
                continue
            fac = p26.compute_g6_factors(z_map)
            base_c, quote_c = p26.PAIR_CCY[asset]
            diff = fac[base_c] - fac[quote_c]
            z_self = float(z_map[asset])
            if abs(diff) >= thr and diff * z_self > 0.0 and abs(z_self) >= 0.20:
                side = 1 if diff > 0 else -1
                tr, fd = _market_entry_window(b, d, ts_e, dsec + 20 * 3600 + 55 * 60, side, sl_atr, win_start_ts=dsec + 7 * 3600)
                if build_m1_tape and tr is not None:
                    m = tr["_meta"]
                    ep = float(quotes[m["e_idx"], 4] if side == 1 else quotes[m["e_idx"], 0])
                    tape_args = (m["e_idx"], m["flat_idx"], side, ep, ep - side * sl_atr * atr)

        if tr is not None and fd is not None:
            trs.append(tr)
            fds.append(fd)
            if build_m1_tape and tape_args is not None:
                e_i, f_i, sd, ep_v, sl_v = tape_args
                item = p27.replay_causal_m1_tape_trade(
                    asset, times, quotes, e_i, f_i, sd, ep_v, sl_v,
                    spec=b["spec"], usdjpy_close_map=b["usdjpy_close_map"],
                )
                if item is not None:
                    tape_out[item[0]["day"]] = item

    return trs, fds, tape_out


def _extract_lifecycle_arrays(days_sorted: list[str], exits: list[dict[str, Any]], initial: float = 10000.0) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    by_day = {e["day"]: e for e in exits}
    n = len(days_sorted)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    flgs = np.zeros(n, dtype=np.int8)
    prev_cash = float(initial)
    for i, dk in enumerate(days_sorted):
        e = by_day.get(dk)
        if e is not None:
            nets[i] = float(e["net_usd"])
            dds[i] = max(0.0, prev_cash - float(e["day_equity_minimum"]))
            flgs[i] = 1
            prev_cash = float(e["cash"])
    return nets, dds, flgs


def evaluate_portfolio_impact(
    warm: dict[str, Any],
    reg: dict[str, Any],
    cand_id: str,
    cand_tape: dict[str, tuple],
    *,
    cand_risk: float = 0.005,
) -> dict[str, Any]:
    """Quantify exact impact on PORT_7E Cluster B (2022-2024) Calmar & FTMO Swing 10k P1 pass time."""
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    ext_days = warm["ext_days"]
    cl_b_days = [d for d in ext_days if d[:4] in ("2022", "2023", "2024")]

    tapes_plus = {**warm["tapes"], cand_id: cand_tape}
    risks_plus = {**risks7, cand_id: cand_risk}

    m7_all, ex7_all = replay_portfolio_m1(ext_days, warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    mp_all, exp_all = replay_portfolio_m1(ext_days, tapes_plus, risks_plus, 10000.0, profile_mode="Swing")

    m7_b, _ = replay_portfolio_m1(cl_b_days, warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    mp_b, _ = replay_portfolio_m1(cl_b_days, tapes_plus, risks_plus, 10000.0, profile_mode="Swing")

    firm_swing = load_firm_config("ftmo_swing_10k")
    prof_bal = {
        "id": "P1_BALANCED_REF",
        "p1_mult": 3.5, "p2_mult": 2.0, "funded_mult": 1.0,
        "amber_dd_pct": 0.050, "amber_mult": 0.65,
        "red_dd_pct": 0.075, "red_mult": 0.40,
        "ea_daily_stop_pct": 0.035,
    }
    s7 = _extract_lifecycle_arrays(ext_days, ex7_all, 10000.0)
    sp = _extract_lifecycle_arrays(ext_days, exp_all, 10000.0)
    idx_mat = make_block_bootstrap_indices(len(ext_days), horizon=504, n_paths=2000, block_len=5, seed=SEED)
    mc7 = evaluate_firm_profile(idx_mat, s7, s7, firm_swing, prof_bal)
    mcp = evaluate_firm_profile(idx_mat, sp, sp, firm_swing, prof_bal)

    return {
        "candidate_id": cand_id,
        "cand_risk_pct": round(cand_risk * 100.0, 2),
        "cand_tape_trades": len(cand_tape),
        "port7e_dev_all": {"ann_pct": m7_all["ann_pct"]["all"], "peak_dd_pct": m7_all["peak_dd_pct"], "calmar": m7_all["calmar"]},
        "port7e_plus_dev_all": {"ann_pct": mp_all["ann_pct"]["all"], "peak_dd_pct": mp_all["peak_dd_pct"], "calmar": mp_all["calmar"]},
        "port7e_cluster_b_2022_2024": {"ann_pct": m7_b["ann_pct"]["all"], "peak_dd_pct": m7_b["peak_dd_pct"], "calmar": m7_b["calmar"]},
        "port7e_plus_cluster_b_2022_2024": {"ann_pct": mp_b["ann_pct"]["all"], "peak_dd_pct": mp_b["peak_dd_pct"], "calmar": mp_b["calmar"]},
        "delta_cluster_b_calmar": round(mp_b["calmar"] - m7_b["calmar"], 3),
        "mc_ftmo_swing_port7e": {"pass_3m": mc7["pass_3m"], "pass_6m": mc7["pass_6m"], "med_pass_m": mc7["med_pass_m"], "br1_pct": mc7["br1_pct"], "cf24_mean": mc7["cf24_mean"]},
        "mc_ftmo_swing_port7e_plus": {"pass_3m": mcp["pass_3m"], "pass_6m": mcp["pass_6m"], "med_pass_m": mcp["med_pass_m"], "br1_pct": mcp["br1_pct"], "cf24_mean": mcp["cf24_mean"]},
    }


def run_pass30(*, cache_dir: Path = hcache.DEFAULT_CACHE, jobs_root: Path = hcache.DEFAULT_JOBS) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=cache_dir, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    _, dev_ex7 = replay_portfolio_m1(warm["ext_days"], warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_daily = {e["day"]: float(e["net_usd"]) / 100.0 for e in dev_ex7}

    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    bundles = {}
    asset_audit = {}
    for a in FX7_ALL:
        b = p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map)
        assert int(b["times"].max()) < STOP, f"HOLDOUT_CONTAMINATION_DETECTED:{a}"
        bundles[a] = b
        if a in TARGET_FX4:
            asset_audit[a] = {"m1_rows": int(len(b["times"])), "days": len(b["days"]), "max_ts_lt_2025": True}

    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in FX7_ALL}
    all_days = sorted({d for dm in day_maps.values() for d in dm})
    vol_ratios = {a: p28._compute_vol_ratio_map(bundles[a]) for a in TARGET_FX4}
    prev_rng_ratios = {a: _compute_prev_range_ratio_map(bundles[a]) for a in TARGET_FX4}

    catalog = build_pass30_catalog()
    m_total = len(catalog)
    rows: list[dict[str, Any]] = []
    cfg_by_id = {c["id"]: c for c in catalog}
    p_sf_all_list: list[float] = []
    p_sf_b_list: list[float] = []

    for idx_c, cfg in enumerate(catalog):
        trs, fds, _ = eval_pass30_spec(bundles, day_maps, all_days, vol_ratios, prev_rng_ratios, cfg, build_m1_tape=False)
        mA = split_stats(trs, CLUSTER_A_YEARS)
        mB = split_stats(trs, CLUSTER_B_YEARS)
        mAll = split_stats(trs, set(ALL_DEV_YEARS))
        yr_map = {str(y): round(fsum(float(t["ftmo_R"]) for t in trs if t["year"] == y), 2) for y in ALL_DEV_YEARS}

        vals_all = [float(t["ftmo_R"]) for t in trs]
        fade_all = [float(f["ftmo_R"]) for f in fds]
        p_sf_all = sign_flip_p_numba(vals_all, fade_all, draws=SIGN_FLIP_DRAWS, seed=SEED + 500 + idx_c) if vals_all else 1.0

        vals_b = [float(t["ftmo_R"]) for t in trs if t["year"] in CLUSTER_B_YEARS]
        fade_b = [float(f["ftmo_R"]) for f in fds if f["year"] in CLUSTER_B_YEARS]
        p_sf_b = sign_flip_p_numba(vals_b, fade_b, draws=SIGN_FLIP_DRAWS, seed=SEED + 600 + idx_c) if vals_b else 1.0

        p_mh_all = compute_matched_hold_p(trs, bundles, years_filter=set(ALL_DEV_YEARS), draws=MATCHED_HOLD_DRAWS, seed=SEED + 700 + idx_c) if trs else 1.0
        trs_b = [t for t in trs if t["year"] in CLUSTER_B_YEARS]
        p_mh_b = compute_matched_hold_p(trs_b, bundles, years_filter=CLUSTER_B_YEARS, draws=MATCHED_HOLD_DRAWS, seed=SEED + 800 + idx_c) if trs_b else 1.0

        corr_7e = round(float(p18.daily_correlation(trs, port7_daily)["union_corr"]), 4) if trs else 0.0
        p_sf_all_list.append(p_sf_all)
        p_sf_b_list.append(p_sf_b)
        rows.append({
            "id": cfg["id"],
            "fam": cfg["fam"],
            "asset": cfg["asset"],
            "cluster_a_2018_2021": mA,
            "cluster_b_2022_2024": mB,
            "dev_all_2018_2024": mAll,
            "years_R": yr_map,
            "sign_flip_p_all": round(p_sf_all, 4),
            "sign_flip_p_b": round(p_sf_b, 4),
            "matched_hold_p_all": round(p_mh_all, 4),
            "matched_hold_p_b": round(p_mh_b, 4),
            "corr_vs_port7e": corr_7e,
        })

    q_all = benjamini_hochberg(p_sf_all_list)
    q_b = benjamini_hochberg(p_sf_b_list)
    qualifiers: list[str] = []

    for r, qa_v, qb_v in zip(rows, q_all, q_b):
        r["bh_q_all"] = round(qa_v, 4)
        r["bh_q_b"] = round(qb_v, 4)
        mA = r["cluster_a_2018_2021"]
        mB = r["cluster_b_2022_2024"]
        mAll = r["dev_all_2018_2024"]

        fail_reasons = []
        if not (mA["n"] >= 40 and mA["net_R"] > 0 and mA["pf"] >= 1.05):
            fail_reasons.append("FAIL_CLUSTER_A")
        if not (mB["n"] >= 25 and mB["net_R"] > 0 and mB["pf"] >= 1.05):
            fail_reasons.append("FAIL_CLUSTER_B")
        if mAll["double_R"] <= 0:
            fail_reasons.append("FAIL_DOUBLE_COST")
        if qa_v >= 0.10:
            fail_reasons.append("FAIL_BH_FDR_ALL")
        if r["matched_hold_p_all"] >= 0.05:
            fail_reasons.append("FAIL_MATCHED_HOLD_NULL")
        if abs(r["corr_vs_port7e"]) >= 0.15:
            fail_reasons.append("FAIL_CORR_GT_015")

        r["verdict"] = "PASS_CANDIDATE" if not fail_reasons else "REJECTED"
        r["fail_reasons"] = fail_reasons
        if not fail_reasons:
            qualifiers.append(r["id"])

    # Quantify PORT_7E impact for every passing candidate (or best Cluster-A spec as counterfactual diagnostic if 0 pass)
    impact_targets = list(qualifiers)
    impact_is_counterfactual = False
    if not impact_targets:
        impact_is_counterfactual = True
        best_a = max(rows, key=lambda x: x["cluster_a_2018_2021"]["net_R"])
        impact_targets = [best_a["id"]]

    portfolio_impacts = {}
    for cid in impact_targets:
        _, _, tape_c = eval_pass30_spec(bundles, day_maps, all_days, vol_ratios, prev_rng_ratios, cfg_by_id[cid], build_m1_tape=True)
        imp = evaluate_portfolio_impact(warm, reg, cid, tape_c, cand_risk=0.005)
        imp["counterfactual_only_do_not_promote"] = impact_is_counterfactual
        portfolio_impacts[cid] = imp

    summary = {
        "schema": "naqex-pass30-fx-extended-dev-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "cluster_split": {"A": "2018-2021", "B": "2022-2024"},
        "assets_audited": asset_audit,
        "m_total": m_total,
        "passed_count": len(qualifiers),
        "passed_ids": qualifiers,
        "portfolio_impacts": portfolio_impacts,
        "results": rows,
    }
    out_cache = ROOT / ".runtime" / "quant-pod-returns" / "pass30_fx_extended_summary.json"
    out_cache.parent.mkdir(parents=True, exist_ok=True)
    out_cache.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M4.2 Pass 30 Extended FX Intraday Discovery (Dev < 2025 ONLY)")
    ap.parse_args()
    s = run_pass30()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "holdout_rows_analysed": s["holdout_rows_analysed"],
        "m_total": s["m_total"],
        "passed_count": s["passed_count"],
        "passed_ids": s["passed_ids"],
        "portfolio_impacts": s["portfolio_impacts"],
        "top_by_dev_R": sorted(
            [(r["id"], r["cluster_a_2018_2021"]["net_R"], r["cluster_b_2022_2024"]["net_R"], r["bh_q_all"], r["matched_hold_p_all"], r["corr_vs_port7e"], r["verdict"]) for r in s["results"]],
            key=lambda x: x[1] + x[2],
            reverse=True,
        )[:10],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
