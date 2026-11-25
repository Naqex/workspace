"""Pass 25: 4 New Native M1 Bid/Ask Assets (AUDUSD, USDCAD, EURJPY, BTCUSD) & Engine #5/#6 Discovery (m_total=136)."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
import pass22_gbpusd_volhigh_3engine as p22
import pass23_ftmo_lifecycle_sim as p23l
import pass23_xau_indices_discovery as p23d
import pass24_mtf_new_archetypes as p24
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "504232d819e82064bc273ddba96762bb760c0115"
SEED = 20261123
MC_DRAWS = 1000


def build_btcusd_bundle(cache_dir: Path) -> dict:
    """Build causal daily frame for 24/7 BTCUSD from Native M1 Bid/Ask Parquets (55-day causal warmup in early 2018)."""
    times, quotes, meta = hcache.load_asset("BTCUSD", cache_dir, verify_sha=True)
    assert meta["native_Ask"] is True
    bid4 = quotes[:, :4]
    # Resample UTC calendar days (allow 7 days/week for 24/7 crypto, min 600 M1 bars/day)
    buckets = times // 86400
    uniq, fi_arr, cnts = np.unique(buckets, return_index=True, return_counts=True)
    d1 = []
    for b, f, cnt in zip(uniq, fi_arr, cnts):
        if cnt < 600:
            continue
        sl = bid4[f:f + cnt]
        s_sec = int(b * 86400)
        d_obj = datetime.fromtimestamp(s_sec, timezone.utc).date()
        d1.append({
            "date": d_obj, "day_sec": s_sec, "fi": int(f), "ei": int(f + cnt),
            "o": float(sl[0, 0]), "h": float(sl[:, 1].max()),
            "l": float(sl[:, 2].min()), "c": float(sl[-1, 3]),
        })
    hs = np.array([b["h"] for b in d1], dtype=np.float64)
    ls = np.array([b["l"] for b in d1], dtype=np.float64)
    cs = np.array([b["c"] for b in d1], dtype=np.float64)
    atr = p14.wilder_atr(hs, ls, cs, 14)
    ema50 = p14.ema(cs, 50)

    days = []
    for idx in range(55, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        d = d1[idx]
        fi, ei, dsec = d["fi"], d["ei"], d["day_sec"]
        sub_t = times[fi:ei]
        i_flat = int(sub_t.searchsorted(dsec + 20 * 3600 + 55 * 60, side="left"))
        if i_flat >= ei - fi:
            i_flat = ei - fi - 1
        if i_flat < 60:
            continue
        days.append({
            "day": d["date"].isoformat(), "year": d["date"].year, "day_sec": dsec,
            "fi": fi, "ei": ei, "flat_idx": fi + i_flat,
            "atr": a_val, "ema50": float(ema50[idx - 1]),
            "prev_c": float(cs[idx - 1]), "pdh": float(hs[idx - 1]), "pdl": float(ls[idx - 1]),
            "win_start_sec": dsec + 7 * 3600, "win_end_sec": dsec + 16 * 3600,
            "morn_start_sec": dsec + 7 * 3600, "morn_end_sec": dsec + 12 * 3600,
            "twap_check_sec": dsec + 10 * 3600,
            "sqz_specs": [
                ("SQZ_LDN_4H_045", dsec + 3 * 3600, dsec + 7 * 3600, dsec + 15 * 3600, 0.45),
                ("SQZ_NY_4H_045", dsec + 8 * 3600, dsec + 12 * 3600, dsec + 17 * 3600, 0.45),
                ("SQZ_NY_6H_055", dsec + 6 * 3600, dsec + 12 * 3600, dsec + 17 * 3600, 0.55),
            ],
        })
    return {"asset": "BTCUSD", "is_index": False, "is_crypto": True, "times": times, "quotes": quotes, "days": days, "spec": None, "usdjpy_close_map": {}}


def eval_wb_open_expansion_unified(bundle: dict, *, trig_atr: float, sl_atr: float, regime: str, vol_mult_override: float | None = None):
    """Causal WB_OPEN_EXPANSION routed through unified 3-tier p24.replay_causal_intraday."""
    quotes = bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        a_val = d["atr"]
        ok_b = ok_s = True
        prev_rng = d["pdh"] - d["pdl"]
        if regime == "EMA50_TREND":
            if not np.isfinite(d["ema50"]):
                continue
            ok_b = d["prev_c"] > d["ema50"]
            ok_s = d["prev_c"] < d["ema50"]
        elif regime == "VOL_HIGH":
            vm = 1.10 if vol_mult_override is None else vol_mult_override
            ok_b = ok_s = prev_rng >= vm * a_val
        elif regime == "VOL_LOW":
            vm = 0.80 if vol_mult_override is None else vol_mult_override
            ok_b = ok_s = prev_rng <= vm * a_val
        if not (ok_b or ok_s):
            continue
        open_0 = float(quotes[d["fi"], 0])
        top, bot = open_0 + trig_atr * a_val, open_0 - trig_atr * a_val
        tr, fd = p24._scan_stop_breakout(bundle, d, d["day_sec"] + 7 * 3600, d["day_sec"] + 17 * 3600, top, bot, sl_atr * a_val, ok_b=ok_b, ok_s=ok_s)
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_wb_session_box_unified(bundle: dict, *, box_start_h: int, box_end_h: int, max_box_atr: float, sl_atr: float = 0.75):
    """Causal WB_SESSION_BOX routed through unified 3-tier p24.replay_causal_intraday."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        a_val, dsec = d["atr"], d["day_sec"]
        b0 = int(times.searchsorted(dsec + box_start_h * 3600, side="left"))
        b1 = int(times.searchsorted(dsec + box_end_h * 3600, side="left"))
        if b1 - b0 < 30:
            continue
        hi_b = float(quotes[b0:b1, 1].max())
        lo_b = float(quotes[b0:b1, 2].min())
        width = hi_b - lo_b
        if width < 0.15 * a_val or width > max_box_atr * a_val:
            continue
        tr, fd = p24._scan_stop_breakout(bundle, d, dsec + box_end_h * 3600, dsec + 17 * 3600, hi_b, lo_b, sl_atr * a_val)
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def build_pass25_catalog() -> list[dict]:
    """Fixed 34-spec catalog per asset: 12 WB_OPEN_EXPANSION + 6 WB_SESSION_BOX + 16 Pass 24 MTF specs."""
    specs = []
    for ta in (0.65, 0.80, 1.00):
        for reg in ("NONE", "EMA50_TREND", "VOL_HIGH", "VOL_LOW"):
            specs.append({"id": f"WB_EXP_{int(ta*100)}_{reg}", "fam": "WB_OPEN_EXPANSION", "trig_atr": ta, "sl_atr": 0.75, "regime": reg})
    for bs, be, mb in ((0, 7, 0.70), (0, 7, 1.00), (2, 8, 0.75), (2, 8, 1.00), (7, 11, 0.75), (7, 11, 1.00)):
        specs.append({"id": f"WB_BOX_{bs:02d}{be:02d}_M{int(mb*100)}", "fam": "WB_SESSION_BOX", "box_start_h": bs, "box_end_h": be, "max_box_atr": mb, "sl_atr": 0.75})
    specs.extend(p24.build_pass24_catalog())
    return specs


def eval_p25_spec(bundle: dict, cfg: dict):
    fam = cfg["fam"]
    if fam == "WB_OPEN_EXPANSION":
        return eval_wb_open_expansion_unified(bundle, trig_atr=cfg["trig_atr"], sl_atr=cfg["sl_atr"], regime=cfg["regime"], vol_mult_override=cfg.get("vol_mult_override"))
    if fam == "WB_SESSION_BOX":
        return eval_wb_session_box_unified(bundle, box_start_h=cfg["box_start_h"], box_end_h=cfg["box_end_h"], max_box_atr=cfg["max_box_atr"], sl_atr=cfg["sl_atr"])
    return p24.eval_spec(bundle, cfg)


def forensic_p25_survivor(bundle: dict, cfg: dict, core4_daily: dict[str, float]) -> dict:
    fam = cfg["fam"]
    if fam not in ("WB_OPEN_EXPANSION", "WB_SESSION_BOX"):
        return p24.run_forensic_for_survivor(bundle, cfg, core4_daily)

    trs, fds = eval_p25_spec(bundle, cfg)
    res = {
        "asset": bundle["asset"], "strategy": cfg["id"], "family": fam, "n": len(trs),
        "cost_tiers": {
            "Base": round(fsum(t["base_R"] for t in trs), 2),
            "Stress": round(fsum(t["ftmo_R"] for t in trs), 2),
            "Double": round(fsum(t["double_R"] for t in trs), 2),
        },
        "fade_R": round(fsum(f["ftmo_R"] for f in fds), 2),
        "outlier": p23d.outlier_stress_trades(trs),
        "direction": p18.direction_breakdown(trs),
        "corr_4e": p18.daily_correlation(trs, core4_daily)["union_corr"],
    }
    s1, s2 = {}, {}
    if fam == "WB_OPEN_EXPANSION":
        for ta in (round(cfg["trig_atr"] - 0.15, 2), cfg["trig_atr"], round(cfg["trig_atr"] + 0.15, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p25_spec(bundle, {**cfg, "trig_atr": ta, "sl_atr": sa})
                s1[f"t{ta:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
            if cfg["regime"] in ("VOL_HIGH", "VOL_LOW"):
                vms = (0.95, 1.10, 1.25) if cfg["regime"] == "VOL_HIGH" else (0.65, 0.80, 0.95)
                for vm in vms:
                    tt, _ = eval_p25_spec(bundle, {**cfg, "trig_atr": ta, "vol_mult_override": vm})
                    s2[f"t{ta:.2f}_v{vm:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    else:
        for mb in (0.60, 0.75, 0.90, 1.10):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p25_spec(bundle, {**cfg, "max_box_atr": mb, "sl_atr": sa})
                s1[f"m{mb:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    res["surface_1"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
    if s2:
        res["surface_2"] = {"both_pos": sum(1 for v in s2.values() if v["A"] > 0 and v["B"] > 0), "total": len(s2), "cells": s2}
    res["trades"] = trs
    return res


def run_pass25(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, _bindings = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    # Build 4-Engine Core (Pass 24 baseline: USDJPY Tokyo + USDJPY EXP080 + GBPUSD VOL_HIGH + US100 SESS_CONT_BRK_40)
    core3_daily = p23d.build_3engine_daily_series(jobs_root, cache_dir, specs)
    u100_bundle = p24.build_unified_asset("US100", jobs_root, cache_dir, swing_specs, usdjpy_close_map)
    u100_tr, _ = p24.eval_sess_continuation(u100_bundle, min_move_atr=0.40, mode="BRK", sl_atr=0.65)
    core4_daily = defaultdict(float, core3_daily)
    for t in u100_tr:
        core4_daily[t["day"]] += float(t["ftmo_R"]) * 0.50
    core4_daily = dict(core4_daily)

    new_assets = ("AUDUSD", "USDCAD", "EURJPY", "BTCUSD")
    bundles = {}
    for a in new_assets:
        bundles[a] = build_btcusd_bundle(cache_dir) if a == "BTCUSD" else p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map)

    catalog = build_pass25_catalog()
    all_evals = []
    for a in new_assets:
        prov_spec = (a == "BTCUSD")
        for cfg in catalog:
            trs, fds = eval_p25_spec(bundles[a], cfg)
            all_evals.append((a, prov_spec, cfg, trs, fds))

    m_total = len(all_evals)
    p_all, stage1 = [], []
    for asset, prov_spec, cfg, trs, fds in all_evals:
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        passed_A = (mA["n"] >= 50 and mA["net_R"] > 0 and mA["pf"] >= 1.05)
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if (passed_A and trs) else {"gross_p": 1.0, "ftmo_net_p": 1.0}
        p_all.append(sf["ftmo_net_p"])
        stage1.append((asset, prov_spec, cfg, trs, fds, mA, passed_A, sf))

    q_all = p14.benjamini_hochberg(p_all)
    survivors = []
    for (asset, prov_spec, cfg, trs, fds, mA, passed_A, sf), q_full in zip(stage1, q_all):
        if not passed_A:
            continue
        mB = wbd.split_metrics(trs, clock.CLUSTERS["B"])
        tot_R = round(fsum(t["ftmo_R"] for t in trs), 2)
        base_R = round(fsum(t["base_R"] for t in trs), 2)
        dbl_R = round(fsum(t["double_R"] for t in trs), 2)
        fade_R = round(fsum(f["ftmo_R"] for f in fds), 2)
        yr_map = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        pos_yrs = sum(v > 0 for v in yr_map.values())
        eq = np.cumsum([0.0] + [t["ftmo_R"] for t in trs])
        dd_R = round(float((np.maximum.accumulate(eq) - eq).max()), 2)
        wins = sorted((t["ftmo_R"] for t in trs if t["ftmo_R"] > 0), reverse=True)
        top10 = round(fsum(wins[:10]), 2)
        corr_4e = p18.daily_correlation(trs, core4_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)

        tier1_core = (
            len(trs) >= 150 and mB["net_R"] > 0 and tot_R > top10 and tot_R > fade_R
            and pos_yrs >= 5 and dd_R <= 15.0 and sf["ftmo_net_p"] < 0.05 and q_full <= 0.10
            and abs(corr_4e) <= 0.25
        )
        if tier1_core:
            tier = "TIER_1_FTMO_READY_PROVISIONAL_CRYPTO" if prov_spec else "TIER_1_FTMO_READY"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT_PROVISIONAL_CRYPTO" if prov_spec else "TIER_2_PERSONAL_VAULT"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "family": cfg["fam"], "asset": asset,
            "provisional_crypto": prov_spec, "n_total": len(trs),
            "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "ftmo_double_R": dbl_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R, "top10_R": top10,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_4e": corr_4e, "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    tier_counts = dict(Counter(r["tier"] for r in survivors))
    tier_counts["STAGE1_FILTERED_OUT_ON_CLUSTER_A"] = m_total - len(survivors)

    print(f"\n=== PASS 25: 4 NEW ASSETS DISCOVERY (m_total={m_total} across AUDUSD/USDCAD/EURJPY/BTCUSD, Cluster A -> Blind Cluster B) ===", flush=True)
    print(f"  Passed Cluster A Gate: {len(survivors)} / {m_total} | Tiers: {tier_counts}", flush=True)
    for r in survivors[:25]:
        print(
            f"  {r['strategy']:22s} {r['asset']:6s} ({r['family']:17s}) | n={r['n_total']:4d} "
            f"| A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (B={r['ftmo_base_R']:+5.1f}, D={r['ftmo_double_R']:+5.1f}, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:4.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q={r['fdr_q_full_space']:.3f} | r4E={r['corr_4e']:+.3f} | {r['tier']}",
            flush=True,
        )

    # --- STAGE 3: DEEP FORENSIC ON ALL TIER_1 + TOP ORTHOGONAL TIER_2 (p < 0.02, |r4E| <= 0.25) ---
    targets = [r for r in survivors if "TIER_1" in r["tier"]]
    for r in survivors:
        if "TIER_2" in r["tier"] and r["p_sign_flip"] < 0.02 and abs(r["corr_4e"]) <= 0.25 and r not in targets:
            targets.append(r)

    forensic_reports = []
    qualified_engines = []
    if targets:
        print(f"\n=== STAGE 3: DEEP FORENSIC AUDIT ({len(targets)} target(s)) ===", flush=True)
        for cand in targets[:8]:
            frep = forensic_p25_survivor(bundles[cand["asset"]], cand["spec"], core4_daily)
            tr_list = frep.pop("trades")
            s1 = frep["surface_1"]
            s2 = frep.get("surface_2")
            s1_ok = (s1["both_pos"] / max(1, s1["total"])) >= 0.50
            cost_ok = (frep["cost_tiers"]["Base"] > 0 and frep["cost_tiers"]["Stress"] > 0 and frep["cost_tiers"]["Double"] > 0)
            out_ok = (frep["outlier"]["drop_top3_R"] > 0 and frep["outlier"]["excl_both_crises_R"] > 0)
            frep["forensic_pass"] = bool(cost_ok and s1_ok and out_ok)
            forensic_reports.append(frep)
            r_val = frep.get("corr_4e", frep.get("corr_3e", 0.0))
            print(
                f"  FORENSIC {cand['asset']:6s} {cand['strategy']:22s} | tiers={frep['cost_tiers']} "
                f"| out(-T3={frep['outlier']['drop_top3_R']:+.1f}, -T5={frep['outlier']['drop_top5_R']:+.1f}, exCr={frep['outlier']['excl_both_crises_R']:+.1f}) "
                f"| s1={s1['both_pos']}/{s1['total']}" + (f" s2={s2['both_pos']}/{s2['total']}" if s2 else "") +
                f" | r4E={r_val:+.3f} | dir=B:{frep['direction']['BUY']['ftmo_R']:+.1f}/S:{frep['direction']['SELL']['ftmo_R']:+.1f} | PASS={frep['forensic_pass']}",
                flush=True,
            )
            if frep["forensic_pass"]:
                qualified_engines.append((cand, tr_list))

    # --- STAGE 4: DUAL-FIRM 2-LAYER UPGRADE CHECK (PORT_4E -> PORT_5E / PORT_6E) ---
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, swing_specs["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    exp_usd_05 = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)}
    gbp_vh_05_raw, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)
    gbp_vh_05 = {r["day"]: (r, t, m) for r, t, m in gbp_vh_05_raw}
    tapes_05 = {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_usd_05, p22.GBPUSD_VH: gbp_vh_05}
    specs_ext = {prof: {**sp, p17.USDJPY_EXP: sp["USDJPY"], p22.GBPUSD_VH: sp["GBPUSD"]} for prof, sp in specs.items()}

    a_dd_2 = {s: portfolio.replay(cluster_a, tapes_05, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"] for s in ("USDJPY", p17.USDJPY_EXP)}
    inv2 = {s: (1.0 / a_dd_2[s]) / fsum(1.0 / v for v in a_dd_2.values()) for s in a_dd_2}
    p3_bal = {**{s: 0.0075 * w for s, w in inv2.items()}, p22.GBPUSD_VH: 0.0075}
    _, ledger3 = portfolio.replay(ext_days, tapes_05, p3_bal, 10000, specs_ext["Swing"])
    d_list, nets3_10k, dds3_10k, flags3 = p23l.build_full_daily_series(ext_days, ledger3, 10000.0)

    def _overlay(base_n, base_d, base_f, extra_list, risk_pct=0.0050):
        n_arr, d_arr, f_arr = base_n.copy(), base_d.copy(), base_f.copy()
        r_usd = 10000.0 * risk_pct
        for trs in extra_list:
            by_d = defaultdict(list)
            for t in trs:
                by_d[t["day"]].append(t)
            for i, dk in enumerate(d_list):
                if dk in by_d:
                    n_arr[i] += fsum(t["ftmo_R"] * r_usd for t in by_d[dk])
                    d_arr[i] += fsum(t["mae_R"] * r_usd for t in by_d[dk])
                    f_arr[i] = 1
        return n_arr, d_arr, f_arr

    nets4_10k, dds4_10k, flags4 = _overlay(nets3_10k, dds3_10k, flags3, [u100_tr], 0.0050)
    port_series = {"PORT_4E_BASE": (nets4_10k, dds4_10k, flags4)}

    picked_assets = set()
    picked = []
    for cand, tr_list in qualified_engines:
        if cand["asset"] not in picked_assets:
            picked_assets.add(cand["asset"])
            picked.append((cand, tr_list))

    for cand, tr_list in picked[:4]:
        port_series[f"PORT5E_PLUS_{cand['asset']}_{cand['strategy']}"] = _overlay(nets4_10k, dds4_10k, flags4, [tr_list], 0.0050)
    if len(picked) >= 2:
        port_series[f"PORT{4+len(picked)}E_ALL_QUALIFIED_R50"] = _overlay(nets4_10k, dds4_10k, flags4, [tl for _, tl in picked], 0.0050)
        port_series[f"PORT{4+len(picked)}E_ALL_QUALIFIED_R60"] = _overlay(nets4_10k, dds4_10k, flags4, [tl for _, tl in picked], 0.0060)

    dual_firm_eval = {}
    print("\n=== STAGE 4: DUAL-FIRM 2-LAYER UPGRADE CHECK (PORT_4E -> PORT_5E/6E · FTMO 10K vs THE5ERS 5K) ===", flush=True)
    for pname, (n10, d10, flg) in port_series.items():
        eq = np.cumsum(np.insert(n10, 0, 10000.0))
        peak_dd = float(np.max((np.maximum.accumulate(eq[:-1]) - (eq[:-1] - d10)) / 10000.0) * 100.0)
        ann = float((eq[-1] - 10000.0) / 10000.0 / 7.0 * 100.0)
        ann_A = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk < "2021-01-01") / 10000.0 / 3.0 * 100.0)
        ann_B = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk >= "2021-01-01") / 10000.0 / 4.0 * 100.0)
        cal = round(ann / peak_dd, 2) if peak_dd > 1e-9 else 0.0
        print(f"\n  [{pname}] 7y Ann={ann:+.2f}% (A={ann_A:+.2f}%, B={ann_B:+.2f}%) | PeakDD={peak_dd:.2f}% | Calmar={cal:.2f}", flush=True)
        dual_firm_eval[pname] = {"ann_pct": round(ann, 2), "ann_A": round(ann_A, 2), "ann_B": round(ann_B, 2), "peak_dd_pct": round(peak_dd, 2), "calmar": cal, "firms": {}}
        for firm, cap, fee, scale in (("FTMO_SWING_10K", 10000.0, 168.0, 1.0), ("THE5ERS_HS_5K", 5000.0, 39.0, 0.5)):
            dual_firm_eval[pname]["firms"][firm] = {}
            for pol_name, p1m, p2m, fm, dyn in (
                ("Flat_Safe_1.0", 1.0, 1.0, 1.0, False),
                ("2Layer_Cap1Pct_Dyn", 1.33, 1.0, 1.0, True),
                ("2Layer_Mod_2.0_Dyn", 2.0, 1.25, 1.0, True),
            ):
                r = p24.simulate_dual_firm_2layer(n10 * scale, d10 * scale, flg, firm=firm, cap=cap, fee=fee, p1_m=p1m, p2_m=p2m, fund_m=fm, dynamic=dyn)
                dual_firm_eval[pname]["firms"][firm][pol_name] = r
                pp = r["pass_pct"]
                print(
                    f"    {firm:14s} | {pol_name:18s} | 3/6/9/12/24m={pp['3m']:4.1f}/{pp['6m']:4.1f}/{pp['9m']:4.1f}/{pp['12m']:4.1f}/{pp['24m']:4.1f}% "
                    f"| Br1={r['br1_pct']:4.1f}% Tix={r['avg_tickets']:.2f} Med={str(r['med_pass_m']):>4s}m "
                    f"| CF12=${r['cf12_mean']:+5.0f} CF24=${r['cf24_mean']:+6.0f} (P>0={r['cf24_pos_pct']:4.1f}%)",
                    flush=True,
                )

    return {
        "pass": "Pass 25 (4 New Assets AUDUSD/USDCAD/EURJPY/BTCUSD & Engine #5/#6 Discovery)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "m_total_search_space": m_total,
        "cluster_a_survivors": len(survivors),
        "tier_counts": tier_counts,
        "survivors": survivors,
        "forensic_reports": forensic_reports,
        "qualified_engines": [f"{c['asset']}_{c['strategy']}" for c, _ in picked],
        "dual_firm_eval": dual_firm_eval,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass25(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass25-result.json", res)
    print("\nPASS25_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
