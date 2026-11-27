"""Pass 21 Lane A: Deep M1 Bid/Ask Forensic Audit of GBPJPY EXP_DAILY_OPEN & 3-Engine Prague-Reset Portfolio Integration."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
import pass20_pos_swap_carry_3engine as p20
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "9bbf69c83241d2b1084d21bd3a23f057414a5677"
GBPJPY_EXP = "GBPJPY_EXP"
SEED = 20261123
MC_DRAWS = 1000


def build_gbpjpy_exp_tape(
    ctx: dict,
    conv_maps: dict,
    *,
    trig_atr: float = 0.80,
    sl_atr: float = 0.75,
    addon_pips: float = 0.50,
    use_ema50: bool = False,
) -> tuple[list, list]:
    """Exact M1 Bid/Ask floating path & Prague-reset marks for GBPJPY EXP_DAILY_OPEN (swap=0)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr, c_d1 = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"], ctx["d1_c"]
    ema50 = p14.ema(c_d1, 50)
    addon = addon_pips * 0.01  # 1 pip = 0.01 JPY
    base_slip_side = 0.002     # 0.2 pip/side base
    comm_rt = 5.0              # $5/lot RT FTMO FX
    cs = 100000.0

    tape, fades = [], []
    for idx in range(off, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        allow_b = allow_s = True
        if use_ema50:
            ev = float(ema50[idx - 1])
            if not np.isfinite(ev):
                continue
            allow_b = c_d1[idx - 1] > ev
            allow_s = c_d1[idx - 1] < ev

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
        up = (scan[:, 5] >= top - 1e-10) if allow_b else np.zeros(len(scan), dtype=bool)
        dn = (scan[:, 2] <= bot + 1e-10) if allow_s else np.zeros(len(scan), dtype=bool)
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

        # Exact USD conversion for JPY quote currency via USDJPY D1 close & GBP base margin via GBPUSD
        jpy_div = conv_maps["USDJPY"].get(d_obj, 130.0)
        gbp_mgn = conv_maps["GBPUSD"].get(d_obj, 1.27)
        conv = cs / jpy_div  # USD per 1.0 JPY price move per lot
        cost_px_total = 2.0 * base_slip_side + addon

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
            # Exact M1 floating marks (open, high, low, close) in USD/lot after slippage & comm
            drag_usd = cost_px_total * conv + comm_rt
            if s_dir == 1:
                marks = (sub_liq - e_px) * conv - drag_usd
            else:
                marks = (e_px - sub_liq) * conv - drag_usd
            gross_usd = s_dir * (ex_px - e_px) * conv
            net_usd = gross_usd - drag_usd
            # Clamp terminal close & worst mark cleanly
            marks[-1, 3] = net_usd
            if at_open:
                marks[-1, :] = net_usd
            risk_usd = abs(e_px - sl_p) * conv
            stop_with_cost = risk_usd + drag_usd
            half = float((day_q[at, 4] - day_q[at, 0]) / 2.0)
            ent_hr = datetime.fromtimestamp(int(stamps[0]), timezone.utc).hour
            est_cost_pct = 100.0 * ((2.0 * half + cost_px_total) * conv + comm_rt) / risk_usd
            row = {
                "day": d_obj.isoformat(), "year": d_obj.year,
                "entry": int(stamps[0]), "exit": int(stamps[-1]) + (0 if at_open else 60),
                "at_open": at_open, "reason": reason,
                "side": s_dir, "direction": "BUY" if s_dir == 1 else "SELL",
                "entry_window": "07:00–11:59_London" if ent_hr < 12 else "12:00–16:59_NY",
                "entry_price": float(e_px), "margin_quote": gbp_mgn,
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


def run_pass21_gbpjpy(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    conv_maps = p20.load_fx_conversion_maps(jobs_root)
    core_daily = p18.build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPJPY", cache_dir, specs["Swing"]["GBPJPY"])

    # 1. Screen all 4 pre-registered variants (0.80, 1.00, 1.20, 0.80_TREND) across 3 cost tiers + BH FDR m=4
    variant_defs = [
        ("EXP_DAILY_OPEN_080", 0.80, False),
        ("EXP_DAILY_OPEN_100", 1.00, False),
        ("EXP_DAILY_OPEN_120", 1.20, False),
        ("EXP_DAILY_OPEN_080_TREND", 0.80, True),
    ]
    screen_rows = []
    stress05_tapes = {}
    for vid, ta, use_ema in variant_defs:
        tp_base, _ = build_gbpjpy_exp_tape(gbp_ctx, conv_maps, trig_atr=ta, sl_atr=0.75, addon_pips=0.0, use_ema50=use_ema)
        tp_s05, fd_s05 = build_gbpjpy_exp_tape(gbp_ctx, conv_maps, trig_atr=ta, sl_atr=0.75, addon_pips=0.50, use_ema50=use_ema)
        tp_s10, _ = build_gbpjpy_exp_tape(gbp_ctx, conv_maps, trig_atr=ta, sl_atr=0.75, addon_pips=1.00, use_ema50=use_ema)
        stress05_tapes[vid] = tp_s05
        s_base = p17.summarize_tape(tp_base)
        s_s05 = p17.summarize_tape(tp_s05)
        s_s10 = p17.summarize_tape(tp_s10)
        sf = p18.sign_flip_null_p([r for r, *_ in tp_s05], [r for r, *_ in fd_s05])
        fade_R = round(fsum(r["net_R"] for r, *_ in fd_s05), 2)
        corr = p18.daily_correlation([r for r, *_ in tp_s05], core_daily)
        decomp = p17.decompose_axes(tp_s05)
        screen_rows.append({
            "strategy": vid, "asset": "GBPJPY", "n": s_s05["n"],
            "base_R": round(s_base["net_R"], 2), "stress05_R": round(s_s05["net_R"], 2), "stress10_R": round(s_s10["net_R"], 2),
            "clusters_s05": s_s05["clusters"], "years_s05": s_s05["years"], "pos_years_s05": s_s05["pos_years"],
            "floating_dd_R_s05": round(s_s05["floating_dd_R"], 2), "underwater_m_s05": s_s05["underwater_months"],
            "fade_R_s05": fade_R, "p_sign_flip": round(sf["ftmo_net_p"], 4), "p_gross": round(sf["gross_p"], 4),
            "corr_usdjpy_core": corr, "decomp": decomp,
        })

    q_vals = p14.benjamini_hochberg([r["p_sign_flip"] for r in screen_rows])
    print("\n=== PASS 21 LANE A: GBPJPY NATIVE M1 BID/ASK EXP_DAILY_OPEN (3 COST TIERS, BH FDR m=4) ===", flush=True)
    for r, q in zip(screen_rows, q_vals):
        r["fdr_q"] = round(q, 4)
        cA, cB = r["clusters_s05"]["A"], r["clusters_s05"]["B"]
        ok_t1 = (r["n"] >= 150 and r["stress05_R"] > 0 and cA > 0 and cB > 0 and r["pos_years_s05"] >= 5 and r["p_sign_flip"] < 0.05 and q <= 0.10 and r["stress05_R"] > r["fade_R_s05"])
        ok_t2 = (not ok_t1 and r["stress05_R"] > 0 and cA > 0 and cB > 0 and r["stress05_R"] > r["fade_R_s05"] and r["p_sign_flip"] < 0.10)
        r["tier"] = "TIER_1_FTMO_READY" if ok_t1 else ("TIER_2_PERSONAL_VAULT" if ok_t2 else "TIER_3_DEAD_NO_EDGE")
        b_r = r["decomp"]["direction"].get("BUY", {}).get("net_R", 0.0)
        s_r = r["decomp"]["direction"].get("SELL", {}).get("net_R", 0.0)
        print(
            f"  {r['strategy']:24s} | n={r['n']:4d} | Base={r['base_R']:+6.2f}R S05={r['stress05_R']:+6.2f}R S10={r['stress10_R']:+6.2f}R "
            f"(A={cA:+5.1f} B={cB:+5.1f} yr+={r['pos_years_s05']}/7 DD={r['floating_dd_R_s05']:.1f}R UW={r['underwater_m_s05']:.1f}m) "
            f"| B/S={b_r:+.1f}/{s_r:+.1f} | Fade={r['fade_R_s05']:+6.1f} | p={r['p_sign_flip']:.3f}(q={q:.3f}) | rJPY={r['corr_usdjpy_core']['union_corr']} | {r['tier']}",
            flush=True,
        )

    # 2. 12-Cell 2D Parameter Stability Surface at Stress_05 on GBPJPY
    surface = {}
    for ta in (0.65, 0.80, 0.95, 1.10):
        for sa in (0.55, 0.75, 0.95):
            tp, _ = build_gbpjpy_exp_tape(gbp_ctx, conv_maps, trig_atr=ta, sl_atr=sa, addon_pips=0.50)
            st = p17.summarize_tape(tp)
            surface[f"trig{ta:.2f}_sl{sa:.2f}"] = {
                "n": st["n"], "net_R": round(st["net_R"], 2),
                "A": st["clusters"]["A"], "B": st["clusters"]["B"],
                "pos_years": st["pos_years"], "dd_R": round(st["floating_dd_R"], 2),
            }
    pos_both = sum(1 for v in surface.values() if v["A"] > 0 and v["B"] > 0)
    print(f"  GBPJPY 2D SURFACE (12 cells at Stress +0.50 pip): {pos_both}/12 positive in BOTH Cluster A & B!", flush=True)

    # 3. Exact Prague-Reset M1 Floating Equity Audit: Solo GBPJPY + 3-Engine Portfolio with Pass 17 USDJPY Core!
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    exp_usd_tape = p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    exp_usd_map = {r["day"]: (r, t, m) for r, t, m in exp_usd_tape}
    exp_gbp_map = {r["day"]: (r, t, m) for r, t, m in stress05_tapes["EXP_DAILY_OPEN_080"]}

    tapes_3e = {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_usd_map, GBPJPY_EXP: exp_gbp_map}
    ext_days = ref_days["extended"]
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    specs_ext = {prof: {**sp, p17.USDJPY_EXP: sp["USDJPY"], GBPJPY_EXP: sp["GBPJPY"]} for prof, sp in specs.items()}
    a_dd = {
        s: portfolio.replay(cluster_a, {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_usd_map}, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP)
    }
    inv = {s: (1.0 / a_dd[s]) / fsum(1.0 / v for v in a_dd.values()) for s in a_dd}
    core_075 = {s: 0.0075 * w for s, w in inv.items()}
    core_100 = {s: 0.0100 * w for s, w in inv.items()}

    port_configs = {
        "BASE_2E_USDJPY_075": core_075,
        "SOLO_GBPJPY_050": {GBPJPY_EXP: 0.005},
        "SOLO_GBPJPY_075": {GBPJPY_EXP: 0.0075},
        "PORT3E_075_GBP025": {**core_075, GBPJPY_EXP: 0.0025},
        "PORT3E_075_GBP040": {**core_075, GBPJPY_EXP: 0.0040},
        "PORT3E_075_GBP050": {**core_075, GBPJPY_EXP: 0.0050},
        "PORT3E_100_GBP050": {**core_100, GBPJPY_EXP: 0.0050},
    }
    books = {}
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        books[bkey] = {}
        for cname, rmap in port_configs.items():
            m = portfolio.replay(ext_days, tapes_3e, rmap, cap, specs_ext[prof])[0]
            m["calmar"] = round(m["annual_pct"]["all"] / m["peak_dd_pct"], 2) if m["peak_dd_pct"] > 1e-9 else 0.0
            books[bkey][cname] = m

    print("\n=== PASS 21 LANE A: PRAGUE-RESET M1 FLOATING EQUITY (GBPJPY SOLO & 3-ENGINE PORTFOLIO) ===", flush=True)
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

    return {
        "pass": "Pass 21 Lane A", "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA, "holdout_rows": 0,
        "order_send_count": 0, "elapsed_seconds": round(time.monotonic() - t0, 2),
        "screen_rows": screen_rows,
        "surface_2d_stress05": surface,
        "surface_both_clusters_positive_count": pos_both,
        "books": books,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass21_gbpjpy(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass21-gbpjpy-result.json", res)
    print("\nPASS21_GBPJPY_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
