"""Pass 13 Track 1: GBPUSD & EURUSD Intraday Liquidity Sweep & Reversal on native M1 Bid/Ask (2018-2024)."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timezone
from math import fsum
from pathlib import Path
from statistics import mean, median

import numpy as np

import pass5_usdjpy_tokyo as clock
import pass11_gbpusd_m1 as ingest
import pass11_portfolio as portfolio
from native_ftmo_monfri_seal import START, STOP, read, sha, write
from pass10_institutional_flow import cohorts, epoch
from pass12_usdjpy_forensic import path_intervals, tally, timeline
from pass8_usdjpy_gaps import touches_between
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "62ef31363604fc4588f0cb4d7a699efd80737cde"
PIP = 0.0001
GRID = 100000
CONTRACT = 100000.0
COMMISSION = 5.0
BASE_SLIP = 0.2 * PIP
STRESS = "M1_Real_Stress_05"
PROFILES = {"M1_Real_Base": 0.0, STRESS: 0.5 * PIP, "M1_Real_Stress_10": 1.0 * PIP}
SIGNAL_END = 13 * 60   # 13:00 London
FLAT = 17 * 60         # 17:00 London (strictly before 17:00 NY -> swap = 0)
SEED = 20261123
MC_DRAWS = 1000


def detect_sweep(offsets, quotes, *, box_end=480, buffer_pips=2.0):
    """Causal sweep-and-reclaim detection on London [00:00..box_end) liquidity box."""
    box = quotes[offsets < box_end]
    if not len(box):
        return "empty_box", None
    box_high = float(box[:, 5].max())  # max Ask high
    box_low = float(box[:, 2].min())   # min Bid low
    if box_high <= box_low:
        return "flat_box", None

    a = int(offsets.searchsorted(box_end))
    b = int(offsets.searchsorted(SIGNAL_END))
    swept_high = False
    swept_low = False
    hi_ext = -1e18
    lo_ext = 1e18
    buf = buffer_pips * PIP

    for i in range(a, b):
        if quotes[i, 5] >= box_high - 1e-10:
            swept_high = True
            if quotes[i, 5] > hi_ext:
                hi_ext = float(quotes[i, 5])
        if quotes[i, 2] <= box_low + 1e-10:
            swept_low = True
            if quotes[i, 2] < lo_ext:
                lo_ext = float(quotes[i, 2])
        if swept_high and swept_low:
            return "dual_sweep_skip", None

        # Causal reclaim check on CLOSED M1 bar i -> enter on NEXT minute i+1 open
        if swept_high and quotes[i, 3] < box_high - 1e-10:
            nxt = i + 1
            if nxt >= len(offsets) or offsets[nxt] != offsets[i] + 1 or offsets[nxt] >= FLAT:
                return "no_next_minute", None
            bid0, ask0 = float(quotes[nxt, 0]), float(quotes[nxt, 4])
            stop = hi_ext + buf
            if bid0 >= stop - 1e-10:
                return "gap_past_stop", None
            return "sweep_reclaim", {
                "side": -1,
                "trigger_idx": i,
                "entry_idx": nxt,
                "entry_price": bid0,
                "entry_spread": ask0 - bid0,
                "stop": stop,
                "opp_edge": box_low,
                "box_high": box_high,
                "box_low": box_low,
                "sweep_extreme": hi_ext,
                "risk_price": stop - bid0,
                "margin_quote": 0.5 * (bid0 + ask0),
            }

        if swept_low and quotes[i, 7] > box_low + 1e-10:
            nxt = i + 1
            if nxt >= len(offsets) or offsets[nxt] != offsets[i] + 1 or offsets[nxt] >= FLAT:
                return "no_next_minute", None
            bid0, ask0 = float(quotes[nxt, 0]), float(quotes[nxt, 4])
            stop = lo_ext - buf
            if ask0 <= stop + 1e-10:
                return "gap_past_stop", None
            return "sweep_reclaim", {
                "side": 1,
                "trigger_idx": i,
                "entry_idx": nxt,
                "entry_price": ask0,
                "entry_spread": ask0 - bid0,
                "stop": stop,
                "opp_edge": box_high,
                "box_high": box_high,
                "box_low": box_low,
                "sweep_extreme": lo_ext,
                "risk_price": ask0 - stop,
                "margin_quote": 0.5 * (bid0 + ask0),
            }

    if swept_high or swept_low:
        return "swept_no_reclaim", None
    return "no_sweep", None


def simulate_exit(quotes, signal, *, use_opp_tp=False):
    """M1 path replay from entry_idx to SL, optional opposite-edge TP, or hard flat (worst-case SL-first)."""
    i = signal["entry_idx"]
    side = signal["side"]
    stop = signal["stop"]
    tp = signal["opp_edge"] if use_opp_tp else None
    liq = quotes[:, :4] if side == 1 else quotes[:, 4:8]  # BUY closes on Bid; SELL closes on Ask

    for j in range(i, len(quotes) - 1):
        op, hi, lo, cl = float(liq[j, 0]), float(liq[j, 1]), float(liq[j, 2]), float(liq[j, 3])
        # Check open gap first (SL-first if j > i)
        if j != i and side * (op - stop) <= 1e-10:
            return j, op, True, "SL_GAP_OR_TOUCH"
        if tp is not None and j != i and side * (op - tp) >= -1e-10:
            return j, op, True, "TP_GAP_OR_TOUCH"
        # Intra-minute check (SL strictly checked BEFORE TP -> conservative worst-case)
        adverse = lo if side == 1 else hi
        favorable = hi if side == 1 else lo
        if side * (adverse - stop) <= 1e-10:
            return j, float(stop), False, "SL_GAP_OR_TOUCH"
        if tp is not None and side * (favorable - tp) >= -1e-10:
            return j, float(tp), False, "TP_GAP_OR_TOUCH"

    return len(quotes) - 1, float(liq[-1, 0]), True, "HARD_FLAT"


def classify_day(offsets, quotes, *, box_end=480, buffer_pips=2.0):
    missing = np.setdiff1d(np.arange(FLAT + 1), offsets, assume_unique=True)
    if not len(missing):
        status, sig = detect_sweep(offsets, quotes, box_end=box_end, buffer_pips=buffer_pips)
        return "strict", status, sig, 0
    required = [0, box_end, SIGNAL_END, FLAT]
    if (len(missing) > 5 or (np.diff(missing) == 1).any()
            or not np.isin(required, offsets).all()):
        return ("empty" if not len(offsets) else "B"), "unavailable", None, int(len(missing))
    nearest = offsets.searchsorted(missing)
    max_jump_pip = float(np.abs(quotes[nearest - 1][:, [3, 7]] - quotes[nearest][:, [0, 4]]).max()) / PIP
    if max_jump_pip > 0.2 + 1e-8:
        return "B", "unavailable", None, int(len(missing))

    status, sig = detect_sweep(offsets, quotes, box_end=box_end, buffer_pips=buffer_pips)
    box = quotes[offsets < box_end]
    box_high, box_low = float(box[:, 5].max()), float(box[:, 2].min())
    trig_off = int(offsets[sig["trigger_idx"]]) if sig else SIGNAL_END
    entry_off = int(offsets[sig["entry_idx"]]) if sig else SIGNAL_END
    exit_idx = simulate_exit(quotes, sig, use_opp_tp=False)[0] if sig else None
    exit_off = int(offsets[exit_idx]) if sig else FLAT

    for idx, pt in zip(nearest, missing):
        prev, nxt = quotes[idx - 1], quotes[idx]
        if sig and min(abs(pt - trig_off), abs(pt - entry_off), abs(pt - exit_off), abs(pt - FLAT)) <= 1:
            return "A_unreplayable", status, None, int(len(missing))
        if box_end <= pt < SIGNAL_END and pt < entry_off:
            if touches_between(prev[7], nxt[4], box_high) or touches_between(prev[3], nxt[0], box_low):
                return "A_unreplayable", status, None, int(len(missing))
        if sig and entry_off < pt < exit_off:
            c_prev, c_nxt = (3, 0) if sig["side"] == 1 else (7, 4)
            if touches_between(prev[c_prev], nxt[c_nxt], sig["stop"]):
                return "A_unreplayable", status, None, int(len(missing))
    return "A_admitted", status, sig, int(len(missing))


def raw_marks(day, start, offsets, quotes, sig):
    idx = sig["entry_idx"]
    side = sig["side"]
    entry = sig["entry_price"]
    spread = sig["entry_spread"]
    at = int(offsets[idx])
    out_rows = []
    for horizon, end_off in (("2h", at + 120), ("4h", at + 240), ("hard_flat", FLAT)):
        j = int(offsets.searchsorted(end_off))
        if end_off > FLAT or j >= len(offsets) or offsets[j] != end_off:
            continue
        bid_e, ask_e = float(quotes[j, 0]), float(quotes[j, 4])
        out_p = bid_e if side == 1 else ask_e
        opp_out = ask_e if side == 1 else bid_e
        opp_in = entry - side * spread
        for fee, addon in PROFILES.items():
            slip_usd = (2.0 * BASE_SLIP + addon) * CONTRACT
            net_usd = side * (out_p - entry) * CONTRACT - slip_usd - COMMISSION
            fade_usd = -side * (opp_out - opp_in) * CONTRACT - slip_usd - COMMISSION
            friction_usd = 0.5 * (spread + (ask_e - bid_e)) * CONTRACT + slip_usd + COMMISSION
            out_rows.append({
                "day": day, "year": int(day[:4]), "side": "BUY" if side == 1 else "SELL",
                "horizon": horizon, "fee": fee, "entry": start + at * 60, "exit": start + end_off * 60,
                "net_usd": net_usd, "fade_usd": fade_usd, "friction_usd": friction_usd,
                "risk_usd": sig["risk_price"] * CONTRACT,
            })
    return out_rows


def summarize_raw(rows):
    def stats(subset):
        return {
            "n": len(subset),
            "net_usd": fsum(r["net_usd"] for r in subset),
            "fade_usd": fsum(r["fade_usd"] for r in subset),
            "friction_usd": fsum(r["friction_usd"] for r in subset),
            "net_mean_usd": mean(r["net_usd"] for r in subset) if subset else None,
            "fade_mean_usd": mean(r["fade_usd"] for r in subset) if subset else None,
            "friction_mean_usd": mean(r["friction_usd"] for r in subset) if subset else None,
        }

    years, clusters = cohorts(rows)
    res = {
        "total": stats(rows),
        "years": {k: stats(v) for k, v in years.items()},
        "clusters": {k: stats(v) for k, v in clusters.items()},
        "direction": {
            s: {"total": stats([r for r in rows if r["side"] == s]),
                "clusters": {k: stats([r for r in v if r["side"] == s]) for k, v in clusters.items()}}
            for s in ("BUY", "SELL")
        },
    }
    if rows:
        ratios = [100.0 * r["friction_usd"] / r["risk_usd"] for r in rows if r["risk_usd"] > 0]
        res["scale"] = {
            "median_friction_over_stop_pct": median(ratios) if ratios else None,
            "share_at_12pct": sum(x <= 12.0 for x in ratios) / len(ratios) if ratios else None,
        }
        yr_nets = sorted(v["net_usd"] for v in res["years"].values())
        c_a = res["clusters"]["A"]
        c_b = res["clusters"]["B"]
        res["gate"] = {
            "all_years_observed": all(v["n"] > 0 for v in res["years"].values()),
            "clusters_positive": c_a["net_usd"] > 0 and c_b["net_usd"] > 0,
            "years_positive_ge5": sum(v["net_usd"] > 0 for v in res["years"].values()) >= 5,
            "ex_top2_years_positive": fsum(yr_nets[:-2]) > 0 if len(yr_nets) >= 3 else False,
            "beats_fade_both_clusters": (
                c_a["net_mean_usd"] > c_a["fade_mean_usd"]
                and c_b["net_mean_usd"] > c_b["fade_mean_usd"]
            ),
            "pass": (
                all(v["n"] > 0 for v in res["years"].values())
                and c_a["net_usd"] > 0 and c_b["net_usd"] > 0
                and sum(v["net_usd"] > 0 for v in res["years"].values()) >= 5
                and fsum(yr_nets[:-2]) > 0
                and c_a["net_mean_usd"] > c_a["fade_mean_usd"]
                and c_b["net_mean_usd"] > c_b["fade_mean_usd"]
            ),
        }
    else:
        res["scale"] = None
        res["gate"] = {"pass": False}
    return res


def sl_trade_slice(day, start, offsets, quotes, sig, addon, *, use_opp_tp=False):
    i = sig["entry_idx"]
    side = sig["side"]
    entry = sig["entry_price"]
    end, exit_price, at_open, reason = simulate_exit(quotes, sig, use_opp_tp=use_opp_tp)
    slip_usd = (2.0 * BASE_SLIP + addon) * CONTRACT
    net_usd = side * (exit_price - entry) * CONTRACT - slip_usd - COMMISSION
    stop_usd = sig["risk_price"] * CONTRACT
    risk_with_cost = stop_usd + slip_usd + COMMISSION

    liq = quotes[i:end + 1, :4] if side == 1 else quotes[i:end + 1, 4:8]
    entry_drag = BASE_SLIP * CONTRACT + COMMISSION / 2.0 + addon * CONTRACT
    marks = (side * (liq - entry) * CONTRACT - entry_drag)[:, [0, 1, 2, 3] if side == 1 else [0, 2, 1, 3]]
    marks[0, 0] = -sig["entry_spread"] * CONTRACT - entry_drag
    marks[0, 1] = max(marks[0, 0], marks[0, 3])
    marks[0, 2] = min(marks[0, 0], marks[0, 2], marks[0, 3])
    if at_open or i == end:
        marks[-1] = net_usd
    else:
        op_m = marks[-1, 0]
        marks[-1] = [op_m, max(op_m, net_usd), min(op_m, net_usd), net_usd]

    stamps = start + offsets[i:end + 1] * 60
    friction_usd = 0.5 * (sig["entry_spread"] + float(quotes[end, 4] - quotes[end, 0])) * CONTRACT + slip_usd + COMMISSION
    row = {
        "day": day, "year": int(day[:4]), "entry": int(stamps[0]),
        "exit": int(stamps[-1]) + int(not at_open) * 60, "at_open": at_open, "reason": reason,
        "side": side, "entry_price": entry, "margin_quote": sig["margin_quote"],
        "net_usd_per_lot": net_usd, "initial_risk_usd": stop_usd,
        "stop_risk_with_cost_usd": risk_with_cost, "net_R": net_usd / risk_with_cost,
        "estimated_friction_over_stop_pct": 100.0 * friction_usd / stop_usd,
        "winner_label": "UNCLASSIFIED_MISSING_EVIDENCE",
        "entry_sl_same_minute": end == i,
    }
    return row, stamps, marks


def summarize_sl(tape):
    if not tape:
        return {"n": 0, "net_R": 0.0, "survives": False}
    groups, clusters = cohorts([r for r, *_ in tape])
    stats = tally(tape)
    stats.update({
        "years": {k: fsum(r["net_R"] for r in v) for k, v in groups.items()},
        "clusters": {k: fsum(r["net_R"] for r in v) for k, v in clusters.items()},
        "net_R_annual": stats["net_R"] / 7.0,
        "underwater_months": path_intervals(*timeline(tape))["underwater"]["months"],
        "stop_cost_share_12pct": mean(r["estimated_friction_over_stop_pct"] <= 12.0 for r, *_ in tape),
        "same_minute": sum(r["entry_sl_same_minute"] for r, *_ in tape),
        "exit_counts": dict(Counter(r["reason"] for r, *_ in tape)),
        "direction_R": {
            "BUY": fsum(r["net_R"] for r, *_ in tape if r["side"] == 1),
            "SELL": fsum(r["net_R"] for r, *_ in tape if r["side"] == -1),
        },
    })
    stats["survives"] = (
        min(stats["clusters"].values()) > 0
        and sum(p > 0 for p in stats["years"].values()) >= 5
        and stats["net_R"] > stats["top10_R"]
    )
    return stats


def mc_random_null(events, addon, *, box_end=480, draws=MC_DRAWS, seed=SEED):
    if not events:
        return None
    rng = np.random.default_rng(seed)
    slip_usd = (2.0 * BASE_SLIP + addon) * CONTRACT
    pools = []
    obs_sweep = 0.0
    obs_fade = 0.0
    for day, start, offsets, quotes, sig in events:
        flat_j = int(offsets.searchsorted(FLAT))
        if flat_j >= len(offsets) or offsets[flat_j] != FLAT:
            continue
        out_bid, out_ask = float(quotes[flat_j, 0]), float(quotes[flat_j, 4])
        side = sig["side"]
        entry = sig["entry_price"]
        spread = sig["entry_spread"]
        obs_sweep += side * ((out_bid if side == 1 else out_ask) - entry) * CONTRACT - slip_usd - COMMISSION
        obs_fade += -side * ((out_ask if side == 1 else out_bid) - (entry - side * spread)) * CONTRACT - slip_usd - COMMISSION

        a, b = offsets.searchsorted([box_end, SIGNAL_END])
        if b <= a:
            continue
        sub = quotes[a:b]
        buy_pnl = (out_bid - sub[:, 4]) * CONTRACT - slip_usd - COMMISSION
        sell_pnl = (sub[:, 0] - out_ask) * CONTRACT - slip_usd - COMMISSION
        pools.append(np.concatenate([buy_pnl, sell_pnl]))

    if not pools:
        return None
    totals = np.zeros(draws, dtype=np.float64)
    for pool in pools:
        totals += pool[rng.integers(0, len(pool), size=draws)]

    return {
        "n_days": len(pools),
        "draws": draws,
        "seed": seed,
        "observed_sweep_usd": float(obs_sweep),
        "observed_fade_usd": float(obs_fade),
        "null_mean_usd": float(totals.mean()),
        "null_std_usd": float(totals.std(ddof=1)),
        "null_p95_usd": float(np.percentile(totals, 95)),
        "sweep_p_value": float((np.sum(totals >= obs_sweep) + 1) / (draws + 1)),
        "fade_p_value": float((np.sum(totals >= obs_fade) + 1) / (draws + 1)),
    }


def evaluate_asset(asset: str, m1_folder: Path, specs: dict, jobs_root: Path):
    manifest = read(m1_folder / "manifest.json")
    coverage = defaultdict(Counter)
    raw = []
    events = []
    eligible = {"strict": set(), "extended": set()}

    # Preload yearly arrays once so sensitivity grid is super fast
    year_data = {}
    for year in clock.YEAR:
        times, values = ingest.load_m1(m1_folder, year, manifest["years"][str(year)], asset=asset, scale=GRID)
        assert START <= int(times[0]) <= int(times[-1]) < STOP
        year_data[year] = (times, values[:, :8])

    for year in clock.YEAR:
        times, values = year_data[year]
        day = date(year, 1, 1)
        while day.year == year:
            if day.weekday() < 5:
                start = epoch(day, 0, clock.LONDON)
                lo, hi = times.searchsorted([start, start + (FLAT + 1) * 60])
                offsets = (times[lo:hi] - start) // 60
                quotes = values[lo:hi]
                group, status, sig, _ = classify_day(offsets, quotes, box_end=480, buffer_pips=2.0)
                c = coverage[str(year)]
                c[group] += 1
                if group in ("strict", "A_admitted"):
                    dkey = day.isoformat()
                    eligible["extended"].add(dkey)
                    if group == "strict":
                        eligible["strict"].add(dkey)
                    c[status] += 1
                    if sig is not None:
                        raw.extend(raw_marks(dkey, start, offsets, quotes, sig))
                        events.append((dkey, start, offsets, quotes, sig))
            day = date.fromordinal(day.toordinal() + 1)
        print(f"Track1 {asset} {year}: {dict(coverage[str(year)])}", flush=True)

    stage0 = {
        k: {
            fee: {
                h: summarize_raw([r for r in raw if r["fee"] == fee and r["horizon"] == h and r["day"] in days])
                for h in ("2h", "4h", "hard_flat")
            }
            for fee in PROFILES
        }
        for k, days in eligible.items()
    }
    mc_null = {k: mc_random_null([ev for ev in events if ev[0] in days], PROFILES[STRESS]) for k, days in eligible.items()}

    sl_modes = {}
    best_tape = None
    best_mode_name = None
    for mode_name, use_opp_tp in (("Sweep_SL_Flat", False), ("Sweep_SL_OppEdge", True)):
        mode_res = {}
        for fee, addon in PROFILES.items():
            tape = [sl_trade_slice(*ev, addon, use_opp_tp=use_opp_tp) for ev in events]
            per_cov = {}
            for k, days in eligible.items():
                app = [item for item in tape if item[0]["day"] in days]
                s = summarize_sl(app)
                if app:
                    sized, _ = portfolio.replay(
                        days, {asset: {r["day"]: (r, t, m) for r, t, m in app}},
                        {asset: 0.003}, 10000, specs["Swing"],
                    )
                    s["swing_10k_030"] = sized
                per_cov[k] = s
            mode_res[fee] = per_cov
            if fee == STRESS and all(per_cov[k]["survives"] for k in ("strict", "extended")):
                if best_tape is None:
                    best_tape = tape
                    best_mode_name = mode_name
        sl_modes[mode_name] = mode_res

    # Parameter stability neighborhood at STRESS (buffer in {1, 2, 3} pips, box_end in {7, 8} London)
    stability = {}
    for box_h in (7, 8):
        for buf_p in (1.0, 2.0, 3.0):
            key = f"box00_{box_h:02d}_buf{buf_p:.0f}p"
            sub_events = []
            for year in clock.YEAR:
                times, values = year_data[year]
                day = date(year, 1, 1)
                while day.year == year:
                    if day.weekday() < 5:
                        dkey = day.isoformat()
                        if dkey in eligible["extended"]:
                            start = epoch(day, 0, clock.LONDON)
                            lo, hi = times.searchsorted([start, start + (FLAT + 1) * 60])
                            offsets = (times[lo:hi] - start) // 60
                            quotes = values[lo:hi]
                            _, sig = detect_sweep(offsets, quotes, box_end=box_h * 60, buffer_pips=buf_p)
                            if sig is not None:
                                sub_events.append((dkey, start, offsets, quotes, sig))
                    day = date.fromordinal(day.toordinal() + 1)
            t_flat = [sl_trade_slice(*ev, PROFILES[STRESS], use_opp_tp=False) for ev in sub_events]
            t_opp = [sl_trade_slice(*ev, PROFILES[STRESS], use_opp_tp=True) for ev in sub_events]
            stability[key] = {
                "Sweep_SL_Flat": {
                    "n": len(t_flat),
                    "net_R": fsum(r["net_R"] for r, *_ in t_flat),
                    "clusters": summarize_sl(t_flat)["clusters"],
                    "survives": summarize_sl(t_flat)["survives"],
                },
                "Sweep_SL_OppEdge": {
                    "n": len(t_opp),
                    "net_R": fsum(r["net_R"] for r, *_ in t_opp),
                    "clusters": summarize_sl(t_opp)["clusters"],
                    "survives": summarize_sl(t_opp)["survives"],
                },
            }

    # Conditional portfolio combine with frozen USDJPY if either SL mode survived
    port_out = None
    if best_tape is not None:
        ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
        tapes = {"USDJPY": ref_trades, asset: {r["day"]: (r, t, m) for r, t, m in best_tape}}
        shared = {k: eligible[k] & ref_days[k] for k in ("strict", "extended")}
        cluster_a = {d for d in shared["strict"] if d < "2021-01-01"}
        dd = {s: portfolio.replay(cluster_a, tapes, {s: 0.003}, 10000, specs["Swing"])[0]["peak_dd_pct"] for s in tapes}
        inv = {s: 0.003 / dd[s] / fsum(1.0 / v for v in dd.values()) for s in dd}
        cases = {"solo": {"USDJPY": 0.003}, "equal": {"USDJPY": 0.0015, asset: 0.0015}, "inverse": inv}
        books = {
            f"{prof}_{cap}": {
                k: {cname: portfolio.replay(days, tapes, risk, cap, specs[prof])[0] for cname, risk in cases.items()}
                for k, days in shared.items()
            }
            for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000))
        }
        port_out = {"mode": best_mode_name, "matched_days": {k: len(v) for k, v in shared.items()},
                    "inverse_dd_cluster_A": dd, "books": books}

    any_sl_survives = best_tape is not None
    mc_ok = all(mc_null[k]["sweep_p_value"] < 0.05 for k in ("strict", "extended"))
    if any_sl_survives and mc_ok:
        verdict = f"{asset}_SWEEP_SURVIVED_M1"
    elif any_sl_survives:
        verdict = f"{asset}_SWEEP_SL_SURVIVED_FAILED_MC_NULL"
    else:
        verdict = f"{asset}_SWEEP_FAILED_M1_CHECK"

    return {
        "asset": asset,
        "native_Ask": True,
        "source_manifest_sha256": sha(m1_folder / "manifest.json"),
        "coverage": {k: dict(v) for k, v in coverage.items()},
        "eligible_days": {k: len(v) for k, v in eligible.items()},
        "stage0": stage0,
        "monte_carlo_null_stress05": mc_null,
        "sl_modes": sl_modes,
        "parameter_stability_stress05": stability,
        "portfolio": port_out,
        "verdict": verdict,
    }


def run_track1(jobs_root: Path, pass13_job: Path, output_dir: Path):
    if sha(clock.ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    output_dir.mkdir(parents=True, exist_ok=True)

    sources = {
        "GBPUSD": jobs_root / "pass11-gbpusd-m1-20261120" / "development-m1",
        "EURUSD": pass13_job / "data" / "eurusd-m1",
    }
    assets_out = {}
    for asset, folder in sources.items():
        if not (folder / "manifest.json").exists():
            raise FileNotFoundError(f"Missing M1 manifest for {asset}: {folder}")
        assets_out[asset] = evaluate_asset(asset, folder, specs, jobs_root)
        print(f"TRACK1_{asset}_VERDICT={assets_out[asset]['verdict']}", flush=True)

    result = {
        "track": "Track1_FX_Intraday_Liquidity_Sweep_Reversal",
        "protocol_commit": PROTOCOL,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "spec": bindings,
        "assets": assets_out,
    }
    write(output_dir / "track1-fx-sweep-result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs"))
    parser.add_argument("--pass13-job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_track1(args.jobs, args.pass13_job, args.output)
