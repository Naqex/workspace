"""Pass 17: Deep M1 floating equity forensic audit of EXP_DAILY_OPEN_080 USDJPY & cross-asset GBPUSD/US500 check."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
from statistics import mean, median
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass12_us500_ny_orb as us500_orb
import pass14_intel_top15_batch as p14
import pass15_ftmo_native_engine2 as p15
import pass16_dual_track as p16
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from pass10_institutional_flow import cohorts
from pass12_usdjpy_forensic import path_intervals, tally, timeline
from quant_core.ftmo_track_replay import commission, profiles

PROTOCOL = "92808a44b785b82f900318906b99529dbbec8654"
USDJPY_EXP = "USDJPY_EXP"
SEED = 20261123
MC_DRAWS = 1000


def build_usdjpy_exp_tape(ctx, *, trig_atr: float = 0.80, sl_atr: float = 0.75, addon: float = 0.005, use_ema50: bool = False):
    """Exact bit-for-bit pass7b_usdjpy_equity M1 path & cash envelope for EXP_DAILY_OPEN on USDJPY."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr, c_d1 = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"], ctx["d1_c"]
    ema50 = p14.ema(c_d1, 50)
    tape = []

    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        allow_buy = allow_sell = True
        if use_ema50:
            ev = ema50[idx - 1]
            if not np.isfinite(ev):
                continue
            allow_buy = c_d1[idx - 1] > ev
            allow_sell = c_d1[idx - 1] < ev

        fi, ei = day["fi"], day["ei"]
        day_sec = day["day_sec"]
        open_0 = float(quotes[fi, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day_sec + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day_sec + 17 * 3600, side="left"))
        i_flat = int(sub_t.searchsorted(day_sec + 20 * 3600 + 55 * 60, side="left"))
        if i_flat >= (ei - fi):
            i_flat = ei - fi - 1
        if i1 <= i0 or i_flat <= i0:
            continue

        day_q = quotes[fi:fi + i_flat + 1]
        day_off = (times[fi:fi + i_flat + 1] - day_sec) // 60
        scan = day_q[i0:min(i1, len(day_q))]
        up = (scan[:, 5] >= top - 1e-10) if allow_buy else np.zeros(len(scan), dtype=bool)
        dn = (scan[:, 2] <= bot + 1e-10) if allow_sell else np.zeros(len(scan), dtype=bool)
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        at = i0 + j
        entry_p = max(top, float(day_q[at, 4])) if side == 1 else min(bot, float(day_q[at, 0]))
        sl = entry_p - side * sl_atr * a_val

        liq = day_q[:, :4] if side == 1 else day_q[:, 4:8]
        # Same-minute SL-first conservative check
        if side == 1 and liq[at, 2] <= sl + 1e-10:
            close = jpy_eq.Exit(at, float(sl), False, "SL_GAP_OR_TOUCH")
        elif side == -1 and liq[at, 1] >= sl - 1e-10:
            close = jpy_eq.Exit(at, float(sl), False, "SL_GAP_OR_TOUCH")
        else:
            tail = liq[at + 1:-1, 2 if side == 1 else 1]
            flags = np.flatnonzero(tail <= sl + 1e-10 if side == 1 else tail >= sl - 1e-10)
            if len(flags):
                k = at + 1 + int(flags[0])
                op = float(liq[k, 0])
                fill = min(op, sl) if side == 1 else max(op, sl)
                close = jpy_eq.Exit(k, float(fill), fill == op, "SL_GAP_OR_TOUCH")
            else:
                close = jpy_eq.Exit(len(day_q) - 1, float(liq[-1, 0]), True, "HARD_FLAT")

        half = float((day_q[at, 4] - day_q[at, 0]) / 2.0)
        risk_usd = abs(entry_p - sl) * jpy_eq.CONTRACT / (entry_p - side * half)
        if risk_usd <= 0:
            continue
        tr_obj = jpy_eq.Trade(
            day_sec, at, side, float(entry_p), half, float(sl), risk_usd,
            close, day_q[at:close.index + 1], False, day_off,
        )
        val = jpy_eq.closed(tr_obj, addon)
        marks = jpy_eq.path(tr_obj, addon)
        stamps = np.array([tr_obj.second_at(i) for i in range(at, close.index + 1)], dtype=np.int64)
        assert START <= int(stamps[0]) <= int(stamps[-1]) < STOP

        mid0 = float(entry_p - side * half)
        est_cost_usd = (2.0 * half + 2.0 * jpy_eq.BASE_SIDE_SLIPPAGE + addon) * jpy_eq.CONTRACT / mid0 + jpy_eq.COMMISSION
        stop_with_cost = risk_usd + (2.0 * jpy_eq.BASE_SIDE_SLIPPAGE + addon) * jpy_eq.CONTRACT / mid0 + jpy_eq.COMMISSION
        dkey = day["date"].isoformat()
        ent_hr = datetime.fromtimestamp(int(stamps[0]), timezone.utc).hour
        row = {
            "day": dkey, "year": day["date"].year,
            "entry": int(stamps[0]),
            "exit": int(stamps[-1]) + (0 if close.at_open else 60),
            "at_open": close.at_open, "reason": close.reason,
            "side": side, "direction": "BUY" if side == 1 else "SELL",
            "entry_window": "07:00–11:59_London" if ent_hr < 12 else "12:00–16:59_NY",
            "entry_price": float(entry_p), "margin_quote": 1.0,
            "net_usd_per_lot": float(val["net"]),
            "initial_risk_usd": float(risk_usd),
            "stop_risk_with_cost_usd": float(stop_with_cost),
            "net_R": float(val["net"] / stop_with_cost),
            "cost_over_stop_pct": float(100.0 * est_cost_usd / risk_usd),
            "cost_bucket": "<4%" if (100.0 * est_cost_usd / risk_usd) < 4 else ("4–8%" if (100.0 * est_cost_usd / risk_usd) <= 8 else ">8%"),
            "winner_label": "UNCLASSIFIED_MISSING_EVIDENCE",
        }
        tape.append((row, stamps, marks))
    return tape


def summarize_tape(tape: list) -> dict:
    if not tape:
        return {"n": 0, "net_R": 0.0}
    groups, clusters = cohorts([r for r, *_ in tape])
    st = tally(tape)
    pi = path_intervals(*timeline(tape))
    st.update({
        "net_R_annual": st["net_R"] / 7.0,
        "years": {k: round(fsum(r["net_R"] for r in v), 3) for k, v in groups.items()},
        "clusters": {k: round(fsum(r["net_R"] for r in v), 3) for k, v in clusters.items()},
        "pos_years": sum(fsum(r["net_R"] for r in v) > 0 for v in groups.values()),
        "underwater_months": round(pi["underwater"]["months"], 2),
        "underwater_censored": pi["underwater"]["censored"],
        "exit_counts": dict(Counter(r["reason"] for r, *_ in tape)),
        "median_cost_over_stop_pct": round(median(r["cost_over_stop_pct"] for r, *_ in tape), 2),
    })
    return st


def decompose_axes(tape: list) -> dict:
    out = {}
    for axis in ("direction", "entry_window", "cost_bucket"):
        buckets = defaultdict(list)
        for item in tape:
            buckets[item[0][axis]].append(item)
        out[axis] = {
            k: {
                "n": len(v),
                "win_rate": round(sum(r["net_R"] > 0 for r, *_ in v) / len(v), 3),
                "net_R": round(fsum(r["net_R"] for r, *_ in v), 2),
                "floating_dd_R": round(path_intervals(*timeline(v))["peak_dd"]["drawdown"], 2),
            }
            for k, v in sorted(buckets.items())
        }
    return out


def run_track1_usdjpy_forensic(jobs_root: Path, cache_dir: Path, specs: dict) -> dict:
    t0 = time.monotonic()
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    all_dev_days = {d["date"].isoformat() for d in jpy_ctx["full_d1"][jpy_ctx["d1_offset"]:]}
    cohorts_map = {"strict": ref_days["strict"], "extended": ref_days["extended"], "all_dev": all_dev_days}

    # 1. 3 Cost Tiers across strict / extended / all_dev
    cost_matrix = {}
    stress05_tape = None
    for cname, addon in jpy_eq.PROFILE.items():
        tape = build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=addon)
        if cname == "M1_Real_Stress_05":
            stress05_tape = tape
        cost_matrix[cname] = {
            k: summarize_tape([item for item in tape if item[0]["day"] in days])
            for k, days in cohorts_map.items()
        }
        s_all = cost_matrix[cname]["all_dev"]
        s_ext = cost_matrix[cname]["extended"]
        s_str = cost_matrix[cname]["strict"]
        print(
            f"T1 COST {cname:17s} | strict: n={s_str['n']} net={s_str['net_R']:+6.2f}R dd={s_str['floating_dd_R']:.1f}R uw={s_str['underwater_months']:.1f}m | "
            f"ext: n={s_ext['n']} net={s_ext['net_R']:+6.2f}R dd={s_ext['floating_dd_R']:.1f}R uw={s_ext['underwater_months']:.1f}m | "
            f"all: n={s_all['n']} net={s_all['net_R']:+6.2f}R dd={s_all['floating_dd_R']:.1f}R uw={s_all['underwater_months']:.1f}m",
            flush=True,
        )

    # 2. 2D Parameter Stability Surface (4 trig x 3 sl = 12 cells) at Stress_05 on extended & all_dev
    surface = {}
    for ta in (0.65, 0.80, 0.95, 1.10):
        for sa in (0.55, 0.75, 0.95):
            key = f"trig{ta:.2f}_sl{sa:.2f}"
            tp = build_usdjpy_exp_tape(jpy_ctx, trig_atr=ta, sl_atr=sa, addon=0.005)
            sa_all = summarize_tape(tp)
            sa_ext = summarize_tape([item for item in tp if item[0]["day"] in ref_days["extended"]])
            surface[key] = {
                "all_dev": {"n": sa_all["n"], "net_R": round(sa_all["net_R"], 2), "A": sa_all["clusters"]["A"],
                            "B": sa_all["clusters"]["B"], "pos_years": sa_all["pos_years"], "dd_R": round(sa_all["floating_dd_R"], 2)},
                "extended": {"n": sa_ext["n"], "net_R": round(sa_ext["net_R"], 2), "A": sa_ext["clusters"]["A"],
                             "B": sa_ext["clusters"]["B"], "pos_years": sa_ext["pos_years"], "dd_R": round(sa_ext["floating_dd_R"], 2)},
            }
    pos_cells_both = sum(1 for v in surface.values() if v["all_dev"]["A"] > 0 and v["all_dev"]["B"] > 0)
    print(f"T1 2D SURFACE (12 cells at Stress_05): {pos_cells_both}/12 cells positive in BOTH Cluster A & B!", flush=True)

    # 3. 4-Axis Forensic Decomposition at Stress_05 (all_dev & extended)
    decomp = {
        "all_dev": decompose_axes(stress05_tape),
        "extended": decompose_axes([item for item in stress05_tape if item[0]["day"] in ref_days["extended"]]),
    }

    # 4. Exact M1 Floating Equity & Prague Daily Reset Audit (Solo + Combined with Engine #1 USDJPY Tokyo-Box)
    exp_map = {r["day"]: (r, t, m) for r, t, m in stress05_tape}
    tapes = {"USDJPY": ref_trades, USDJPY_EXP: exp_map}
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    specs_ext = {prof: {**sp, USDJPY_EXP: sp["USDJPY"]} for prof, sp in specs.items()}
    a_dd = {
        s: portfolio.replay(cluster_a, tapes, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", USDJPY_EXP)
    }
    inv = {s: (1.0 / a_dd[s]) / fsum(1.0 / v for v in a_dd.values()) for s in a_dd}

    # Also build MUTEX tape (never hold both USDJPY engines on same day: if Tokyo triggers first, skip Exp; else Exp)
    # Wait: Tokyo enters 03:00-09:59 UTC; Exp enters 07:00-16:59 UTC. Let's test MUTEX_NO_DOUBLE_USDJPY!
    mutex_exp_map = {}
    for d, item in exp_map.items():
        if d not in ref_trades or item[0]["entry"] < ref_trades[d][0]["entry"]:
            mutex_exp_map[d] = item
    mutex_ref_map = {d: item for d, item in ref_trades.items() if d not in mutex_exp_map}
    tapes_mutex = {"USDJPY": mutex_ref_map, USDJPY_EXP: mutex_exp_map}

    solo_cases = {
        "SOLO_EXP080_030": {USDJPY_EXP: 0.003},
        "SOLO_EXP080_040": {USDJPY_EXP: 0.004},
        "SOLO_EXP080_050": {USDJPY_EXP: 0.005},
        "SOLO_EXP080_075": {USDJPY_EXP: 0.0075},
        "SOLO_EXP080_100": {USDJPY_EXP: 0.010},
        "SOLO_TOKYO_030": {"USDJPY": 0.003},
    }
    port_cases = {
        "PORT_EQUAL_030": {"USDJPY": 0.0015, USDJPY_EXP: 0.0015},
        "PORT_EQUAL_040": {"USDJPY": 0.0020, USDJPY_EXP: 0.0020},
        "PORT_EQUAL_050": {"USDJPY": 0.0025, USDJPY_EXP: 0.0025},
        "PORT_INV_DD_040": {s: 0.004 * w for s, w in inv.items()},
        "PORT_INV_DD_050": {s: 0.005 * w for s, w in inv.items()},
        "PORT_INV_DD_075": {s: 0.0075 * w for s, w in inv.items()},
    }

    books = {}
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        books[bkey] = {}
        for cov, days in cohorts_map.items():
            res_cov = {}
            for cname, risk in solo_cases.items():
                if cname == "SOLO_TOKYO_030" and cov == "all_dev":
                    continue
                res_cov[cname] = portfolio.replay(days, tapes, risk, cap, specs_ext[prof])[0]
            if cov in ("strict", "extended"):
                for cname, risk in port_cases.items():
                    res_cov[cname] = portfolio.replay(days, tapes, risk, cap, specs_ext[prof])[0]
                res_cov["MUTEX_EQUAL_050"] = portfolio.replay(
                    days, tapes_mutex, {"USDJPY": 0.0025, USDJPY_EXP: 0.0025}, cap, specs_ext[prof]
                )[0]
                res_cov["MUTEX_INV_DD_075"] = portfolio.replay(
                    days, tapes_mutex, {s: 0.0075 * w for s, w in inv.items()}, cap, specs_ext[prof]
                )[0]
            books[bkey][cov] = res_cov

    sw10 = books["Swing_10000"]["extended"]
    print("\n=== SWING 10K EXTENDED M1 FLOATING EQUITY (PRAGUE RESET, STRESS +0.50 PIP) ===")
    for cname, m in sw10.items():
        ap = m["annual_pct"]
        print(
            f"  {cname:18s} | ann={ap['all']:+5.2f}%/yr (A={ap['A']:+5.2f}%, B={ap['B']:+5.2f}%) "
            f"| peakDD={m['peak_dd_pct']:5.2f}% | dailyLoss={m['daily_loss_pct']:4.2f}% | uw={m['underwater_months']:4.1f}m "
            f"| dblSL={m['double_sl_days']:2d} | mgnFail={m['margin_failures']} | maxMgn={m['peak_margin_pct']:5.1f}%"
        )

    return {
        "track": "Track1_USDJPY_EXP080_M1_Forensic",
        "protocol_commit": PROTOCOL,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "cost_matrix": cost_matrix,
        "surface_2d_stress05": surface,
        "surface_both_clusters_positive_count": pos_cells_both,
        "decomposition_stress05": decomp,
        "cluster_a_dd_pct": a_dd,
        "inverse_dd_weights": inv,
        "books": books,
    }


# ==============================================================================
# TRACK 2: CROSS-ASSET EXP_DAILY_OPEN ON GBPUSD & US500 (NATIVE BID/ASK M1)
# ==============================================================================

def run_us500_wide_expansion(times, quotes, spec, *, trig_atr: float, sl_atr: float = 0.75, slip_side: float = 0.75, use_ema50: bool = False):
    """NYSE cash-session Daily-Open ± trig_atr*ATR14_D1 on sealed US500 Explicit M1 Bid/Ask (swap=0)."""
    # Build completed NYSE cash-session daily OHLC for causal ATR14 & EMA50
    all_sessions = []
    for y in clock.YEAR:
        sess, _ = us500_orb.calendar(y)
        for dkey, start in sorted(sess.items()):
            lo, hi = times.searchsorted([start, start + 386 * 60])
            if hi - lo < 300:
                continue
            q = quotes[lo:hi]
            all_sessions.append({
                "day": dkey, "year": y, "start": start, "lo": int(lo), "hi": int(hi),
                "o": float(q[0, 0]), "h": float(q[:, 1].max()), "l": float(q[:, 2].min()), "c": float(q[-1, 3]),
            })
    hs = np.array([s["h"] for s in all_sessions], dtype=np.float64)
    ls = np.array([s["l"] for s in all_sessions], dtype=np.float64)
    cs = np.array([s["c"] for s in all_sessions], dtype=np.float64)
    atr = p14.wilder_atr(hs, ls, cs, 14)
    ema50 = p14.ema(cs, 50)

    trades, fades = [], []
    for idx in range(15, len(all_sessions)):
        s = all_sessions[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        allow_buy = allow_sell = True
        if use_ema50:
            ev = ema50[idx - 1]
            if not np.isfinite(ev):
                continue
            allow_buy = cs[idx - 1] > ev
            allow_sell = cs[idx - 1] < ev

        lo, hi = s["lo"], s["hi"]
        offs = (times[lo:hi] - s["start"]) // 60
        q = quotes[lo:hi]
        open_0 = float(q[0, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val

        a_i, b_i = int(offs.searchsorted(30)), int(offs.searchsorted(300))  # 10:00..14:30 NY
        if b_i <= a_i:
            continue
        scan = q[a_i:b_i]
        up = (scan[:, 5] >= top - 1e-10) if allow_buy else np.zeros(len(scan), dtype=bool)
        dn = (scan[:, 2] <= bot + 1e-10) if allow_sell else np.zeros(len(scan), dtype=bool)
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        rel_i = a_i + j
        entry_p = max(top, float(q[rel_i, 4])) if side == 1 else min(bot, float(q[rel_i, 0]))
        sl = entry_p - side * sl_atr * a_val

        def sim(s_dir, e_p, stop_p):
            liq = q[rel_i:, :4] if s_dir == 1 else q[rel_i:, 4:8]
            adverse = liq[:-1, 2 if s_dir == 1 else 1]
            h_sl = np.flatnonzero(s_dir * (adverse - stop_p) <= 1e-10)
            if len(h_sl):
                k = int(h_sl[0])
                op = float(liq[k, 0])
                gap = k > 0 and s_dir * (op - stop_p) <= 1e-10
                ex_p = op if gap else stop_p
                reason = "SL_GAP_OR_TOUCH"
                ex_rel = rel_i + k
            else:
                ex_p = float(liq[-1, 0])
                reason = "HARD_FLAT"
                ex_rel = len(q) - 1
            gross = s_dir * (ex_p - e_p)
            net = gross - 2.0 * slip_side
            risk = abs(e_p - stop_p) + 2.0 * slip_side
            return {
                "day": s["day"], "year": s["year"], "side": s_dir, "reason": reason,
                "entry": int(times[lo + rel_i]), "exit": int(times[lo + ex_rel]),
                "hold_hours": max(1.0, (times[lo + ex_rel] - times[lo + rel_i]) / 3600.0),
                "gross_usd": gross, "ftmo_comm_slip": 2.0 * slip_side, "ftmo_swap": 0.0,
                "ftmo_net": net, "ftmo_R": net / risk,
                "ex_R_normal": (gross - 1.0) / (abs(e_p - stop_p) + 1.0),
                "ex_R_swapfree": (gross - 1.0) / (abs(e_p - stop_p) + 1.0),
            }

        trades.append(sim(side, entry_p, sl))
        f_side = -side
        f_ep = float(q[rel_i, 4] if f_side == 1 else q[rel_i, 0])
        fades.append(sim(f_side, f_ep, f_ep - f_side * sl_atr * a_val))
    return trades, fades, all_sessions


def mc_us500_null(times, quotes, trades, all_sessions, slip_side: float = 0.75):
    if not trades:
        return None
    sess_map = {s["day"]: s for s in all_sessions}
    pools_g, pools_n = [], []
    for tr in trades:
        s = sess_map[tr["day"]]
        lo, hi = s["lo"], s["hi"]
        offs = (times[lo:hi] - s["start"]) // 60
        q = quotes[lo:hi]
        a, b = int(offs.searchsorted(30)), int(offs.searchsorted(300))
        if b <= a:
            continue
        out_bid, out_ask = float(q[-1, 0]), float(q[-1, 4])
        sub = q[a:b]
        pg = np.concatenate([out_bid - sub[:, 4], sub[:, 0] - out_ask])
        pools_g.append(pg)
        pools_n.append(pg - 2.0 * slip_side)
    rng = np.random.default_rng(SEED)
    ng = np.zeros(MC_DRAWS)
    nn = np.zeros(MC_DRAWS)
    for pg, pn in zip(pools_g, pools_n):
        idx = rng.integers(0, len(pg), size=MC_DRAWS)
        ng += pg[idx]
        nn += pn[idx]
    obs_g = fsum(t["gross_usd"] for t in trades)
    obs_n = fsum(t["ftmo_net"] for t in trades)
    return {
        "n_days": len(pools_g), "draws": MC_DRAWS, "seed": SEED,
        "obs_gross_usd": float(obs_g), "null_gross_mean": float(ng.mean()), "null_gross_p95": float(np.percentile(ng, 95)),
        "gross_p_value": float((np.sum(ng >= obs_g) + 1) / (MC_DRAWS + 1)),
        "obs_ftmo_net_usd": float(obs_n), "null_net_mean": float(nn.mean()), "null_net_p95": float(np.percentile(nn, 95)),
        "ftmo_net_p_value": float((np.sum(nn >= obs_n) + 1) / (MC_DRAWS + 1)),
    }


def run_track2_cross_asset(jobs_root: Path, cache_dir: Path, specs: dict) -> dict:
    t0 = time.monotonic()
    rows = []
    defs = [
        ("EXP_DAILY_OPEN_080", dict(trig_atr=0.80, use_ema50=False)),
        ("EXP_DAILY_OPEN_100", dict(trig_atr=1.00, use_ema50=False)),
        ("EXP_DAILY_OPEN_120", dict(trig_atr=1.20, use_ema50=False)),
        ("EXP_DAILY_OPEN_080_TREND", dict(trig_atr=0.80, use_ema50=True)),
    ]
    # 1. GBPUSD native Tick M1 Bid/Ask
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, specs["Swing"]["GBPUSD"])
    for sid, kw in defs:
        trs, fades, _ = p16.run_wide_expansion(gbp_ctx, **kw)
        mc = p14.mc_null_test(gbp_ctx, trs)
        r = p14.summarize_pair(sid, "GBPUSD", True, trs, mc)
        r["fade_ftmo_R"] = fsum(t["ftmo_R"] for t in fades)
        rows.append(r)

    # 2. US500 Explicit M1 Bid/Ask (from D: SSD Hot Cache!)
    us_times, us_quotes, _ = hcache.load_asset("US500", cache_dir, verify_sha=True)
    for sid, kw in defs:
        trs, fades, all_s = run_us500_wide_expansion(us_times, us_quotes, specs["Swing"]["US500.cash"], slip_side=0.75, **kw)
        mc = mc_us500_null(us_times, us_quotes, trs, all_s, slip_side=0.75)
        r = p14.summarize_pair(sid, "US500", True, trs, mc)
        r["fade_ftmo_R"] = fsum(t["ftmo_R"] for t in fades)
        # Also report M1_Base (0.25) and M1_Stress_Mid (0.50) net R for full transparency
        t_mid, _, _ = run_us500_wide_expansion(us_times, us_quotes, specs["Swing"]["US500.cash"], slip_side=0.50, **kw)
        t_base, _, _ = run_us500_wide_expansion(us_times, us_quotes, specs["Swing"]["US500.cash"], slip_side=0.25, **kw)
        r["us500_stress_mid_R"] = round(fsum(t["ftmo_R"] for t in t_mid), 2)
        r["us500_base_R"] = round(fsum(t["ftmo_R"] for t in t_base), 2)
        rows.append(r)

    q_g = p14.benjamini_hochberg([r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    print("\n=== TRACK 2: CROSS-ASSET EXP_DAILY_OPEN ON GBPUSD & US500 (BH FDR m=8) ===")
    for r, qg, qf in zip(rows, q_g, q_f):
        r["fdr_gross_q"], r["fdr_ftmo_q"] = qg, qf
        pg = r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0
        pf = r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0
        extra = f" (Mid={r['us500_stress_mid_R']:+.1f}R Base={r['us500_base_R']:+.1f}R)" if r["asset"] == "US500" else ""
        print(
            f"  {r['strategy']:25s} {r['asset']:6s} | n={r['n']:4d} | FTMO_R={r.get('ftmo_net_R',0):+7.2f}{extra} "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7) "
            f"| Fade={r['fade_ftmo_R']:+7.1f} | p_f={pf:.3f}(q={qf:.3f}) | {r['tier']}",
            flush=True,
        )

    return {
        "track": "Track2_CrossAsset_GBPUSD_US500_Expansion",
        "protocol_commit": PROTOCOL,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    args.output.mkdir(parents=True, exist_ok=True)

    t1 = run_track1_usdjpy_forensic(args.jobs, args.cache, specs)
    t2 = run_track2_cross_asset(args.jobs, args.cache, specs)
    out = {
        "pass": "Pass 17", "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA, "holdout_rows": 0,
        "order_send_count": 0, "network_calls": 0, "spec_bindings": bindings,
        "track1": t1, "track2": t2,
    }
    write(args.output / "pass17-result.json", out)
    print("\nPASS17_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
