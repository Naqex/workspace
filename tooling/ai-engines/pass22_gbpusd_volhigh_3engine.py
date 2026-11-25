"""Pass 22: Deep M1 Floating-Equity Forensic Audit of GBPUSD WB_EXP_80_VOL_HIGH & 3-Engine Prague-Reset Portfolio."""

import argparse
from collections import Counter
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
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "d9b70d6b6e362062e105db4722d37f941751f00a"
GBPUSD_VH = "GBPUSD_VH"
PIP = 0.0001
CONTRACT = 100000.0
BASE_SLIP_SIDE = 0.2 * PIP
COMM_RT = 5.0


def build_gbpusd_volhigh_tape(
    ctx: dict,
    *,
    trig_atr: float = 0.80,
    sl_atr: float = 0.75,
    vol_mult: float = 1.10,
    addon_pips: float = 0.50,
) -> tuple[list, list]:
    """Exact M1 Bid/Ask floating path & Prague-reset marks for GBPUSD WB_EXP_80_VOL_HIGH (swap=0)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    d1_h, d1_l = ctx["d1_h"], ctx["d1_l"]
    addon = addon_pips * PIP
    cost_px_total = 2.0 * BASE_SLIP_SIDE + addon

    tape, fades = [], []
    for idx in range(off, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        # Strictly causal prior completed D1 range expansion regime filter
        prev_rng = float(d1_h[idx - 1] - d1_l[idx - 1])
        if prev_rng < vol_mult * a_val:
            continue

        day = d1[idx]
        d_obj = day["date"]
        fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
        sub_t = times[fi:ei]
        open_0 = float(quotes[fi, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
        i0 = int(sub_t.searchsorted(dsec + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(dsec + 17 * 3600, side="left"))
        i_flat = int(sub_t.searchsorted(dsec + 20 * 3600 + 55 * 60, side="left"))
        if i_flat >= (ei - fi):
            i_flat = ei - fi - 1
        if i1 <= i0 or i_flat <= i0:
            continue

        day_q = quotes[fi:fi + i_flat + 1]
        day_t = times[fi:fi + i_flat + 1]
        scan = day_q[i0:min(i1, len(day_q))]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        at = i0 + j
        ep = max(top, float(day_q[at, 4])) if side == 1 else min(bot, float(day_q[at, 0]))
        fep = float(day_q[at, 4] if side == -1 else day_q[at, 0])

        def sim_side(s_dir: int, e_px: float):
            sl_p = e_px - s_dir * sl_atr * a_val
            liq = day_q[:, :4] if s_dir == 1 else day_q[:, 4:8]
            if (s_dir == 1 and liq[at, 2] <= sl_p + 1e-10) or (s_dir == -1 and liq[at, 1] >= sl_p - 1e-10):
                ex_i, ex_px, at_open, reason = at, float(sl_p), False, "SL_GAP_OR_TOUCH"
            else:
                tail = liq[at + 1:-1, 2 if s_dir == 1 else 1]
                fl = np.flatnonzero(tail <= sl_p + 1e-10 if s_dir == 1 else tail >= sl_p - 1e-10)
                if len(fl):
                    k = at + 1 + int(fl[0])
                    op = float(liq[k, 0])
                    fill = min(op, sl_p) if s_dir == 1 else max(op, sl_p)
                    ex_i, ex_px, at_open, reason = k, float(fill), (fill == op), "SL_GAP_OR_TOUCH"
                else:
                    ex_i, ex_px, at_open, reason = len(day_q) - 1, float(liq[-1, 0]), True, "HARD_FLAT"

            stamps = day_t[at:ex_i + 1].astype(np.int64)
            assert START <= int(stamps[0]) <= int(stamps[-1]) < STOP
            sub_liq = liq[at:ex_i + 1]
            drag_usd = cost_px_total * CONTRACT + COMM_RT
            if s_dir == 1:
                marks = (sub_liq - e_px) * CONTRACT - drag_usd
            else:
                marks = (e_px - sub_liq) * CONTRACT - drag_usd
            gross_usd = s_dir * (ex_px - e_px) * CONTRACT
            net_usd = gross_usd - drag_usd
            marks[-1, 3] = net_usd
            if at_open:
                marks[-1, :] = net_usd
            risk_usd = abs(e_px - sl_p) * CONTRACT
            stop_with_cost = risk_usd + drag_usd
            half = float((day_q[at, 4] - day_q[at, 0]) / 2.0)
            ent_hr = datetime.fromtimestamp(int(stamps[0]), timezone.utc).hour
            est_cost_pct = 100.0 * ((2.0 * half + cost_px_total) * CONTRACT + COMM_RT) / risk_usd
            row = {
                "day": d_obj.isoformat(), "year": d_obj.year,
                "entry": int(stamps[0]), "exit": int(stamps[-1]) + (0 if at_open else 60),
                "at_open": at_open, "reason": reason,
                "side": s_dir, "direction": "BUY" if s_dir == 1 else "SELL",
                "entry_window": "07:00–11:59_London" if ent_hr < 12 else "12:00–16:59_NY",
                "entry_price": float(e_px), "margin_quote": float(e_px),
                "gross_usd": float(gross_usd), "ftmo_net": float(net_usd),
                "net_usd_per_lot": float(net_usd),
                "initial_risk_usd": float(risk_usd),
                "stop_risk_with_cost_usd": float(stop_with_cost),
                "net_R": float(net_usd / stop_with_cost),
                "ftmo_R": float(net_usd / stop_with_cost),
                "cost_over_stop_pct": float(est_cost_pct),
                "cost_bucket": "<4%" if est_cost_pct < 4 else ("4–8%" if est_cost_pct <= 8 else ">8%"),
                "winner_label": "UNCLASSIFIED_MISSING_EVIDENCE",
            }
            return row, stamps, marks

        tape.append(sim_side(side, ep))
        fades.append(sim_side(-side, fep))
    return tape, fades


def outlier_stress_report(tape: list) -> dict:
    """Honest outlier stress: drop Top-3/Top-5 wins, exclude Mar-2020 COVID, exclude Sep-Oct 2022 UK Gilt crisis."""
    rs = [r["net_R"] for r, *_ in tape]
    tot = fsum(rs)
    top_desc = sorted([x for x in rs if x > 0], reverse=True)
    no_covid = [r["net_R"] for r, *_ in tape if not r["day"].startswith("2020-03")]
    no_gilt = [r["net_R"] for r, *_ in tape if not (r["day"].startswith("2022-09") or r["day"].startswith("2022-10"))]
    no_both = [
        r["net_R"] for r, *_ in tape
        if not (r["day"].startswith("2020-03") or r["day"].startswith("2022-09") or r["day"].startswith("2022-10"))
    ]
    return {
        "total_R": round(tot, 2),
        "drop_top3_R": round(tot - fsum(top_desc[:3]), 2),
        "drop_top5_R": round(tot - fsum(top_desc[:5]), 2),
        "drop_top10_R": round(tot - fsum(top_desc[:10]), 2),
        "excl_covid_2020_03_R": round(fsum(no_covid), 2),
        "excl_gilt_2022_0910_R": round(fsum(no_gilt), 2),
        "excl_both_crises_R": round(fsum(no_both), 2),
        "excl_both_n": len(no_both),
        "top5_trades": [
            {"day": r["day"], "dir": r["direction"], "net_R": round(r["net_R"], 2)}
            for r, *_ in sorted(tape, key=lambda it: it[0]["net_R"], reverse=True)[:5]
        ],
    }


def run_pass22(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, specs["Swing"]["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    all_dev_days = {d["date"].isoformat() for d in gbp_ctx["full_d1"][gbp_ctx["d1_offset"]:]}
    cohorts_map = {"strict": ref_days["strict"], "extended": ref_days["extended"], "all_dev": all_dev_days}

    # --- TRACK 1A: 3 Cost Tiers across strict / extended / all_dev ---
    cost_matrix = {}
    stress05_tape = stress05_fade = None
    for cname, ap in (("M1_Real_Base", 0.0), ("M1_Real_Stress_05", 0.50), ("M1_Real_Stress_10", 1.00)):
        tp, fd = build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=ap)
        if cname == "M1_Real_Stress_05":
            stress05_tape, stress05_fade = tp, fd
        cost_matrix[cname] = {
            k: p17.summarize_tape([it for it in tp if it[0]["day"] in days])
            for k, days in cohorts_map.items()
        }
        s_str, s_ext, s_all = cost_matrix[cname]["strict"], cost_matrix[cname]["extended"], cost_matrix[cname]["all_dev"]
        print(
            f"T1A COST {cname:17s} | strict: n={s_str['n']} net={s_str['net_R']:+5.2f}R dd={s_str['floating_dd_R']:.1f}R | "
            f"ext: n={s_ext['n']} net={s_ext['net_R']:+5.2f}R dd={s_ext['floating_dd_R']:.1f}R uw={s_ext['underwater_months']:.1f}m | "
            f"all: n={s_all['n']} net={s_all['net_R']:+5.2f}R yr+={s_all['pos_years']}/7 dd={s_all['floating_dd_R']:.1f}R uw={s_all['underwater_months']:.1f}m",
            flush=True,
        )

    # --- TRACK 1B: Two Parameter Stability Surfaces (12 trig x vol_mult + 9 trig x sl_atr = 21 cells) ---
    surf_tv = {}
    for ta in (0.65, 0.80, 0.95, 1.10):
        for vm in (0.95, 1.10, 1.25):
            tp, _ = build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=ta, sl_atr=0.75, vol_mult=vm, addon_pips=0.50)
            st = p17.summarize_tape(tp)
            surf_tv[f"trig{ta:.2f}_vol{vm:.2f}"] = {
                "n": st["n"], "net_R": round(st["net_R"], 2),
                "A": st["clusters"]["A"], "B": st["clusters"]["B"],
                "pos_years": st["pos_years"], "dd_R": round(st["floating_dd_R"], 2),
            }
    tv_both_pos = sum(1 for v in surf_tv.values() if v["A"] > 0 and v["B"] > 0)

    surf_ts = {}
    for ta in (0.70, 0.80, 0.90):
        for sa in (0.55, 0.75, 0.95):
            tp, _ = build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=ta, sl_atr=sa, vol_mult=1.10, addon_pips=0.50)
            st = p17.summarize_tape(tp)
            surf_ts[f"trig{ta:.2f}_sl{sa:.2f}"] = {
                "n": st["n"], "net_R": round(st["net_R"], 2),
                "A": st["clusters"]["A"], "B": st["clusters"]["B"],
                "pos_years": st["pos_years"], "dd_R": round(st["floating_dd_R"], 2),
            }
    ts_both_pos = sum(1 for v in surf_ts.values() if v["A"] > 0 and v["B"] > 0)
    print(f"T1B SURFACES (Stress +0.50 pip): trig×vol_mult = {tv_both_pos}/12 A&B>0 | trig×sl_atr = {ts_both_pos}/9 A&B>0", flush=True)

    # --- TRACK 1C: 4-Axis Decomposition + Outlier Stress + MC Null ---
    decomp_all = p17.decompose_axes(stress05_tape)
    outlier = outlier_stress_report(stress05_tape)
    sf = p18.sign_flip_null_p([r for r, *_ in stress05_tape], [r for r, *_ in stress05_fade])
    core_daily = p18.build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)
    corr_jpy = p18.daily_correlation([r for r, *_ in stress05_tape], core_daily)
    print(
        f"T1C OUTLIER STRESS: Total={outlier['total_R']:+.2f}R | -Top3={outlier['drop_top3_R']:+.2f}R | -Top5={outlier['drop_top5_R']:+.2f}R "
        f"| ExclCOVID={outlier['excl_covid_2020_03_R']:+.2f}R | ExclGilt={outlier['excl_gilt_2022_0910_R']:+.2f}R | ExclBoth={outlier['excl_both_crises_R']:+.2f}R (n={outlier['excl_both_n']})",
        flush=True,
    )
    print(f"T1C DIRECTION: {decomp_all['direction']} | p_sf={sf['ftmo_net_p']:.4f} | rJPY={corr_jpy}", flush=True)

    # --- TRACK 2: EXACT PRAGUE-RESET M1 FLOATING EQUITY FOR 3-ENGINE PORTFOLIO ---
    exp_usd_tape = p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    exp_usd_map = {r["day"]: (r, t, m) for r, t, m in exp_usd_tape}
    gbp_vh_map = {r["day"]: (r, t, m) for r, t, m in stress05_tape}
    tapes_3e = {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_usd_map, GBPUSD_VH: gbp_vh_map}
    ext_days = ref_days["extended"]
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    specs_ext = {prof: {**sp, p17.USDJPY_EXP: sp["USDJPY"], GBPUSD_VH: sp["GBPUSD"]} for prof, sp in specs.items()}

    # 2-engine Cluster A inverse-DD weights (exact Pass 17 baseline)
    a_dd_2 = {
        s: portfolio.replay(cluster_a, tapes_3e, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP)
    }
    inv2 = {s: (1.0 / a_dd_2[s]) / fsum(1.0 / v for v in a_dd_2.values()) for s in a_dd_2}
    core_075 = {s: 0.0075 * w for s, w in inv2.items()}

    # 3-engine Cluster A inverse-DD weights (strictly Cluster A 2018-2020 ONLY — zero Cluster B peeking!)
    a_dd_3 = {
        s: portfolio.replay(cluster_a, tapes_3e, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP, GBPUSD_VH)
    }
    inv3 = {s: (1.0 / a_dd_3[s]) / fsum(1.0 / v for v in a_dd_3.values()) for s in a_dd_3}

    port_configs = {
        "BASE_2E_USDJPY_075": core_075,
        "SOLO_GBP_VH_050": {GBPUSD_VH: 0.0050},
        "SOLO_GBP_VH_075": {GBPUSD_VH: 0.0075},
        "SOLO_GBP_VH_100": {GBPUSD_VH: 0.0100},
        "PORT3E_075_GBP025": {**core_075, GBPUSD_VH: 0.0025},
        "PORT3E_075_GBP050": {**core_075, GBPUSD_VH: 0.0050},
        "PORT3E_075_GBP075": {**core_075, GBPUSD_VH: 0.0075},
        "PORT3E_075_GBP100": {**core_075, GBPUSD_VH: 0.0100},
        "PORT3E_INVDD_075": {s: 0.0075 * w for s, w in inv3.items()},
        "PORT3E_INVDD_100": {s: 0.0100 * w for s, w in inv3.items()},
        "PORT3E_INVDD_125": {s: 0.0125 * w for s, w in inv3.items()},
    }

    books = {}
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        books[bkey] = {}
        for cname, rmap in port_configs.items():
            m = portfolio.replay(ext_days, tapes_3e, rmap, cap, specs_ext[prof])[0]
            m["calmar"] = round(m["annual_pct"]["all"] / m["peak_dd_pct"], 2) if m["peak_dd_pct"] > 1e-9 else 0.0
            books[bkey][cname] = m

    print("\n=== TRACK 2: PRAGUE-RESET M1 FLOATING EQUITY (3-ENGINE PORTFOLIO: USDJPY TOKYO + USDJPY EXP080 + GBPUSD VOL_HIGH) ===", flush=True)
    for bkey in ("Swing_10000", "Swing_25000", "Standard_50000"):
        print(f"  --- {bkey} ---", flush=True)
        for cname, m in books[bkey].items():
            ap = m["annual_pct"]
            print(
                f"    {cname:20s} | ann={ap['all']:+5.2f}%/yr (A={ap['A']:+5.2f}%, B={ap['B']:+5.2f}%) "
                f"| peakDD={m['peak_dd_pct']:5.2f}% | daily={m['daily_loss_pct']:4.2f}% | uw={m['underwater_months']:4.1f}m "
                f"| calmar={m['calmar']:4.2f} | mgn={m['peak_margin_pct']:5.1f}% fail={m['margin_failures']}",
                flush=True,
            )

    # Pre-registered Promotion Check
    sw10 = books["Swing_10000"]
    sw25 = books["Swing_25000"]
    st50 = books["Standard_50000"]
    cost_ok = all(cost_matrix[c]["all_dev"]["net_R"] > 0 for c in ("M1_Real_Base", "M1_Real_Stress_05", "M1_Real_Stress_10"))
    surf_ok = (tv_both_pos >= 9) or (ts_both_pos >= 7)
    upgraded_configs = [
        cn for cn in port_configs if cn.startswith("PORT3E_")
        and all(
            b[cn]["annual_pct"]["all"] > b["BASE_2E_USDJPY_075"]["annual_pct"]["all"]
            and b[cn]["calmar"] > b["BASE_2E_USDJPY_075"]["calmar"]
            and b[cn]["peak_dd_pct"] <= 7.0
            and b[cn]["daily_loss_pct"] <= 2.5
            and b[cn]["margin_failures"] == 0
            and b[cn]["annual_pct"]["A"] > 0 and b[cn]["annual_pct"]["B"] > 0
            for b in (sw10, sw25, st50)
        )
    ]
    promoted = bool(cost_ok and surf_ok and len(upgraded_configs) > 0)
    verdict = (
        "GBPUSD_VOLHIGH_PROMOTED_AS_ORTHOGONAL_ENGINE3" if promoted
        else ("GBPUSD_VOLHIGH_PORTFOLIO_IMPROVER_WITH_SURFACE_OR_CONCENTRATION_CAVEAT" if upgraded_configs else "GBPUSD_VOLHIGH_NOT_PROMOTED_KEEP_2ENGINE_CORE")
    )
    print(f"\nPASS22_VERDICT: {verdict} | cost_ok={cost_ok} surf_ok={surf_ok} upgraded_3e={upgraded_configs}", flush=True)

    return {
        "pass": "Pass 22", "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA, "holdout_rows": 0,
        "order_send_count": 0, "network_calls": 0, "spec_bindings": bindings,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "verdict": verdict,
        "promotion_checks": {"cost_ok": cost_ok, "surf_ok": surf_ok, "upgraded_configs": upgraded_configs},
        "cost_matrix": cost_matrix,
        "surface_trig_vol": {"both_pos": tv_both_pos, "total": 12, "cells": surf_tv},
        "surface_trig_sl": {"both_pos": ts_both_pos, "total": 9, "cells": surf_ts},
        "decomposition_all_dev": decomp_all,
        "outlier_stress": outlier,
        "sign_flip_null": sf,
        "corr_usdjpy_core": corr_jpy,
        "cluster_a_dd_3e": a_dd_3,
        "inverse_dd_weights_3e": inv3,
        "books": books,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass22(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass22-result.json", res)
    print("PASS22_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
