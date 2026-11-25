"""Pass 15: FTMO-native Engine #2 screen — XAUUSD Intraday (swap=0) & FX Positive-Carry Trend (2018-2024)."""

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
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from pass10_institutional_flow import cohorts
from quant_core.ftmo_track_replay import commission, profiles

PROTOCOL = "b2e5803b0c7676bf1cbb516fa19db716aec7d16a"
SEED = 20261123
MC_DRAWS = 1000


def _fade_trade(ctx, entry_idx: int, side: int, stop_dist: float, flat_sec: int):
    """Exact opposite-direction Fade control at identical entry minute and symmetric stop distance."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    f_side = -side
    f_entry = float(quotes[entry_idx, 4] if f_side == 1 else quotes[entry_idx, 0])
    f_sl = f_entry - f_side * stop_dist
    return p14.replay_trade_m1(asset, times, quotes, entry_idx, f_side, f_entry, f_sl, None, flat_sec, spec, intraday_flat=True)


def _m1_portfolio_slice(ctx, entry_idx: int, side: int, entry_price: float, sl_price: float, flat_sec: int):
    """Build exact pass11_portfolio-compatible (row, stamps, marks) M1 envelope for XAUUSD intraday trades."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    entry_ts = int(times[entry_idx])
    risk_p = side * (entry_price - sl_price)
    if risk_p <= 0:
        return None
    hi_idx = int(times.searchsorted(min(flat_sec, STOP - 60), side="right")) - 1
    if hi_idx < entry_idx:
        return None
    liq = quotes[entry_idx:hi_idx + 1, :4] if side == 1 else quotes[entry_idx:hi_idx + 1, 4:8]
    if side == 1:
        hits = np.flatnonzero(liq[:, 2] <= sl_price + 1e-10)
    else:
        hits = np.flatnonzero(liq[:, 1] >= sl_price - 1e-10)
    if len(hits):
        rel = int(hits[0])
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_price) <= 1e-10
        exit_p = op if gap else sl_price
        at_open = bool(gap)
        reason = "SL_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        exit_p = float(liq[-1, 3])
        at_open = False
        reason = "HARD_FLAT"

    cs = float(spec["trade_contract_size"])
    f_cfg = p14.ftmo_stress_params(asset)
    comm_rt = commission(asset, spec, entry_price) + commission(asset, spec, exit_p)
    slip_rt = f_cfg["slip_rt"] * cs
    net_usd = side * (exit_p - entry_price) * cs - comm_rt - slip_rt
    stop_usd = risk_p * cs
    risk_with_cost = stop_usd + comm_rt + slip_rt

    sub = liq[:rel + 1]
    entry_drag = 0.5 * (comm_rt + slip_rt)
    marks = (side * (sub - entry_price) * cs - entry_drag)[:, [0, 1, 2, 3] if side == 1 else [0, 2, 1, 3]]
    spread_usd = float(quotes[entry_idx, 4] - quotes[entry_idx, 0]) * cs
    marks[0, 0] = -spread_usd - entry_drag
    marks[0, 1] = max(marks[0, 0], marks[0, 3])
    marks[0, 2] = min(marks[0, 0], marks[0, 2], marks[0, 3])
    if at_open or rel == 0:
        marks[-1] = net_usd
    else:
        op_m = marks[-1, 0]
        marks[-1] = [op_m, max(op_m, net_usd), min(op_m, net_usd), net_usd]

    stamps = times[entry_idx:entry_idx + rel + 1]
    dkey = datetime.fromtimestamp(entry_ts, timezone.utc).date().isoformat()
    row = {
        "day": dkey, "year": int(dkey[:4]), "entry": int(stamps[0]),
        "exit": int(stamps[-1]) + int(not at_open) * 60, "at_open": at_open, "reason": reason,
        "side": side, "entry_price": entry_price, "margin_quote": entry_price,
        "net_usd_per_lot": net_usd, "initial_risk_usd": stop_usd,
        "stop_risk_with_cost_usd": risk_with_cost, "net_R": net_usd / risk_with_cost,
        "winner_label": "UNCLASSIFIED_MISSING_EVIDENCE",
    }
    return row, stamps, marks


# ==============================================================================
# TRACK A: XAUUSD INTRADAY VOLATILITY & MOMENTUM (SWAP = 0, 2-SIDED)
# ==============================================================================

def run_xau_daily_open_atr(ctx, *, trig_atr: float = 0.50, sl_pad_atr: float = 0.25, collect_tape: bool = False):
    """A1: Daily Open ± trig_atr*ATR14_D1 OCO breakout (07:00-17:00 UTC), flat 20:55 UTC (swap=0)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades, tape = [], [], []
    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        fi, ei = day["fi"], day["ei"]
        open_0 = float(quotes[fi, 0])  # Bid open at 00:00 UTC
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day["day_sec"] + 17 * 3600, side="left"))
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + i0 + j
        entry_p = max(top, float(quotes[entry_i, 4])) if side == 1 else min(bot, float(quotes[entry_i, 0]))
        sl = (open_0 - sl_pad_atr * a_val) if side == 1 else (open_0 + sl_pad_atr * a_val)
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            ft = _fade_trade(ctx, entry_i, side, abs(entry_p - sl), flat_sec)
            if ft:
                fades.append(ft)
            if collect_tape:
                slc = _m1_portfolio_slice(ctx, entry_i, side, entry_p, sl, flat_sec)
                if slc:
                    tape.append(slc)
    return trades, fades, tape


def run_xau_london_ny_momentum(ctx, *, body_atr: float = 0.45, close_loc: float = 0.70, sl_atr: float = 0.60, collect_tape: bool = False):
    """A2: Strong directional London session (07:00-12:59 UTC) continuation into NY (13:00-20:55 UTC, swap=0)."""
    times, quotes, bid4, spec, asset = ctx["times"], ctx["quotes"], ctx["bid4"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades, tape = [], [], []
    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day["day_sec"] + 13 * 3600, side="left"))
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        if i1 <= i0 + 60 or (fi + i1) >= ei:
            continue
        lon = bid4[fi + i0:fi + i1]
        lo_o, lo_c = float(lon[0, 0]), float(lon[-1, 3])
        lo_h, lo_l = float(lon[:, 1].max()), float(lon[:, 2].min())
        rng = lo_h - lo_l
        if rng <= 0:
            continue
        body = lo_c - lo_o
        side = 0
        if body >= body_atr * a_val and (lo_c - lo_l) / rng >= close_loc:
            side = 1
        elif body <= -body_atr * a_val and (lo_h - lo_c) / rng >= close_loc:
            side = -1
        if not side:
            continue
        entry_i = fi + i1
        if times[entry_i] >= flat_sec:
            continue
        entry_p = float(quotes[entry_i, 4] if side == 1 else quotes[entry_i, 0])
        sl = entry_p - side * sl_atr * a_val
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            ft = _fade_trade(ctx, entry_i, side, abs(entry_p - sl), flat_sec)
            if ft:
                fades.append(ft)
            if collect_tape:
                slc = _m1_portfolio_slice(ctx, entry_i, side, entry_p, sl, flat_sec)
                if slc:
                    tape.append(slc)
    return trades, fades, tape


def run_xau_h1_donchian_intraday(ctx, *, don_n: int = 20, sl_atr: float = 1.5, collect_tape: bool = False):
    """A3: First H1 Donchian(20) breakout in London-NY (07:00-17:00 UTC), flat 20:55 UTC (swap=0)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, h, l, c, atr = ctx["h1"], ctx["h1_h"], ctx["h1_l"], ctx["h1_c"], ctx["h1_atr"]
    trades, fades, tape = [], [], []
    traded_days = set()
    for k in range(don_n + 1, len(h1)):
        bar = h1[k]
        dt = datetime.fromtimestamp(bar["end_sec"], timezone.utc)
        if dt.date() in traded_days or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        if not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        side = 0
        if c[k] > h[k - don_n:k].max():
            side = 1
        elif c[k] < l[k - don_n:k].min():
            side = -1
        if not side:
            continue
        entry_i = int(times.searchsorted(bar["end_sec"], side="left"))
        if entry_i >= len(times) or times[entry_i] - bar["end_sec"] > 900:
            continue
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if times[entry_i] >= flat_sec:
            continue
        entry_p = float(quotes[entry_i, 4] if side == 1 else quotes[entry_i, 0])
        sl = entry_p - side * sl_atr * atr[k]
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded_days.add(dt.date())
            ft = _fade_trade(ctx, entry_i, side, abs(entry_p - sl), flat_sec)
            if ft:
                fades.append(ft)
            if collect_tape:
                slc = _m1_portfolio_slice(ctx, entry_i, side, entry_p, sl, flat_sec)
                if slc:
                    tape.append(slc)
    return trades, fades, tape


def run_xau_asia_squeeze_break(ctx, *, max_asia_atr: float = 0.35, min_asia_atr: float = 0.10, collect_tape: bool = False):
    """A4: Tight Asia Volatility Squeeze (00:00-06:59 UTC) OCO breakout in London-NY (07:00-17:00 UTC), flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades, tape = [], [], []
    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day["day_sec"] + 17 * 3600, side="left"))
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        if i0 < 60 or i1 <= i0:
            continue
        asia = quotes[fi:fi + i0]
        top, bot = float(asia[:, 5].max()), float(asia[:, 2].min())
        rng = top - bot
        if not (min_asia_atr * a_val <= rng < max_asia_atr * a_val):
            continue
        scan = quotes[fi + i0:fi + i1]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + i0 + j
        entry_p = max(top, float(quotes[entry_i, 4])) if side == 1 else min(bot, float(quotes[entry_i, 0]))
        sl = bot if side == 1 else top
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            ft = _fade_trade(ctx, entry_i, side, abs(entry_p - sl), flat_sec)
            if ft:
                fades.append(ft)
            if collect_tape:
                slc = _m1_portfolio_slice(ctx, entry_i, side, entry_p, sl, flat_sec)
                if slc:
                    tape.append(slc)
    return trades, fades, tape


# ==============================================================================
# TRACK B: FX POSITIVE-CARRY TREND-FOLLOWING (FTMO POSITIVE SWAP ALIGNED)
# ==============================================================================

def run_carry_donchian_d1(ctx, *, side: int, entry_n: int = 20, exit_n: int = 10, sl_atr: float = 2.0):
    """B1/B3: Positive-carry D1 Donchian(20) breakout aligned with EMA50_D1, Donchian(10) trailing exit."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off = ctx["full_d1"], ctx["d1_offset"]
    h, l, c, atr = ctx["d1_h"], ctx["d1_l"], ctx["d1_c"], ctx["d1_atr"]
    ema50 = p14.ema(c, 50)
    trades = []
    next_free = 0
    for idx in range(off, len(d1) - 1):
        if d1[idx]["day_sec"] < next_free:
            continue
        p = idx - 1
        if not np.isfinite(ema50[p]) or not np.isfinite(atr[p]) or atr[p] <= 0:
            continue
        if side == 1:
            trig = c[p] > h[p - entry_n:p].max() and c[p] > ema50[p]
        else:
            trig = c[p] < l[p - entry_n:p].min() and c[p] < ema50[p]
        if not trig:
            continue
        entry_i = d1[idx]["fi"]
        entry_p = float(quotes[entry_i, 4] if side == 1 else quotes[entry_i, 0])
        sl = entry_p - side * sl_atr * atr[p]
        early_sec = None
        for fwd in range(idx, min(idx + 20, len(d1) - 1)):
            if side == 1 and c[fwd] < l[fwd - exit_n:fwd].min():
                early_sec = d1[fwd + 1]["day_sec"]
                break
            if side == -1 and c[fwd] > h[fwd - exit_n:fwd].max():
                early_sec = d1[fwd + 1]["day_sec"]
                break
        max_sec = d1[min(idx + 20, len(d1) - 1)]["day_sec"] + 20 * 3600 + 55 * 60
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, max_sec, spec, early_exit_sec=early_sec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_carry_usdjpy_pullback_h4(ctx, *, tp_r: float = 2.5):
    """B2: USDJPY Long-only H4 EMA20 pullback in D1 uptrend (C > EMA50_D1), enjoying +2.61 FTMO swap."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, h4_l, h4_c, h4_atr, h4_ema = ctx["h4"], ctx["h4_l"], ctx["h4_c"], ctx["h4_atr"], ctx["h4_ema20"]
    d1_map, d1_c = ctx["date_to_d1"], ctx["d1_c"]
    d1_ema50 = p14.ema(d1_c, 50)
    trades = []
    next_free = 0
    for k in range(25, len(h4)):
        bar = h4[k]
        if bar["end_sec"] < next_free:
            continue
        if not np.isfinite(h4_ema[k]) or not np.isfinite(h4_atr[k]) or h4_atr[k] <= 0:
            continue
        d_idx = d1_map.get(bar["date"])
        if d_idx is None or d_idx < 1:
            continue
        p = d_idx - 1
        if not (np.isfinite(d1_ema50[p]) and d1_c[p] > d1_ema50[p]):
            continue
        if not (h4_l[k] <= h4_ema[k] and h4_c[k] > h4_ema[k] and h4_c[k] > bar["o"]):
            continue
        ei = int(times.searchsorted(bar["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - bar["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4])
        sl = min(h4_l[k], h4_ema[k] - 1.5 * h4_atr[k])
        if sl >= entry_p:
            continue
        tp = entry_p + tp_r * (entry_p - sl)
        tr = p14.replay_trade_m1(asset, times, quotes, ei, 1, entry_p, sl, tp, int(times[ei]) + 10 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_portfolio_check(jobs_root: Path, xau_tape: list, specs: dict) -> dict:
    """Combine surviving XAUUSD intraday tape with frozen USDJPY Engine #1 on matched eligible days."""
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    xau_map = {r["day"]: (r, t, m) for r, t, m in xau_tape}
    # Match on frozen USDJPY strict & extended day calendars (all days have XAUUSD M1 available)
    tapes = {"USDJPY": ref_trades, "XAUUSD": xau_map}
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    dd = {}
    for sym in ("USDJPY", "XAUUSD"):
        dd[sym] = portfolio.replay(cluster_a, tapes, {sym: 0.003}, 10000, specs["Swing"])[0]["peak_dd_pct"]
    inv = {s: (1.0 / dd[s]) / fsum(1.0 / v for v in dd.values()) for s in dd} if all(v > 0 for v in dd.values()) else {"USDJPY": 0.5, "XAUUSD": 0.5}
    cases = {
        "SOLO_USDJPY_030": {"USDJPY": 0.003},
        "SOLO_XAUUSD_030": {"XAUUSD": 0.003},
        "PORT_EQUAL_030": {"USDJPY": 0.0015, "XAUUSD": 0.0015},
        "PORT_EQUAL_040": {"USDJPY": 0.0020, "XAUUSD": 0.0020},
        "PORT_INV_DD_030": {s: 0.003 * w for s, w in inv.items()},
        "PORT_INV_DD_040": {s: 0.004 * w for s, w in inv.items()},
    }
    books = {}
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        books[bkey] = {}
        for cov in ("strict", "extended"):
            books[bkey][cov] = {
                cname: portfolio.replay(ref_days[cov], tapes, risk, cap, specs[prof])[0]
                for cname, risk in cases.items()
            }
    return {"cluster_a_dd_pct": dd, "inverse_weights": inv, "books": books}


def run_pass15(jobs_root: Path, cache_dir: Path, output_dir: Path):
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    xau_ctx = p14.build_asset_context(jobs_root, "XAUUSD", cache_dir, swing_specs["XAUUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    eur_ctx = p14.build_asset_context(jobs_root, "EURUSD", cache_dir, swing_specs["EURUSD"])

    # Run all 7 preregistered hypotheses
    runs = []
    tapes_by_id = {}
    xau_defs = [
        ("XAU_DAILY_OPEN_ATR", run_xau_daily_open_atr),
        ("XAU_LONDON_NY_MOMENTUM", run_xau_london_ny_momentum),
        ("XAU_H1_DONCHIAN_INTRADAY", run_xau_h1_donchian_intraday),
        ("XAU_ASIA_SQUEEZE_BREAK", run_xau_asia_squeeze_break),
    ]
    for hid, fn in xau_defs:
        trs, fades, tape = fn(xau_ctx, collect_tape=True)
        mc = p14.mc_null_test(xau_ctx, trs)
        row = p14.summarize_pair(hid, "XAUUSD", False, trs, mc)
        row["fade_ftmo_R"] = fsum(t["ftmo_R"] for t in fades)
        row["beats_fade"] = row.get("ftmo_net_R", 0.0) > row["fade_ftmo_R"]
        row["branch"] = "TrackA_XAU_Intraday_ZeroSwap"
        runs.append(row)
        tapes_by_id[hid] = tape

    fx_defs = [
        ("CARRY_USDJPY_LONG_DONCHIAN20", jpy_ctx, lambda c: run_carry_donchian_d1(c, side=1)),
        ("CARRY_USDJPY_LONG_PULLBACK_H4", jpy_ctx, run_carry_usdjpy_pullback_h4),
        ("CARRY_EURUSD_SHORT_DONCHIAN20", eur_ctx, lambda c: run_carry_donchian_d1(c, side=-1)),
    ]
    for hid, ctx, fn in fx_defs:
        trs = fn(ctx)
        mc = p14.mc_null_test(ctx, trs)
        row = p14.summarize_pair(hid, ctx["asset"], True, trs, mc)
        row["branch"] = "TrackB_FX_PositiveCarry_Trend"
        runs.append(row)

    # Benjamini-Hochberg FDR across m = 7 hypotheses
    gross_qs = p14.benjamini_hochberg([r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0 for r in runs])
    ftmo_qs = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0 for r in runs])
    for r, qg, qf in zip(runs, gross_qs, ftmo_qs):
        r["fdr_gross_q"] = qg
        r["fdr_ftmo_q"] = qf
        pg = r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0
        pf = r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0
        print(
            f"  {r['strategy']:30s} | n={r['n']:4d} | FTMO_R={r.get('ftmo_net_R',0):+7.2f} "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+6.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+6.1f} "
            f"yr+={r.get('ftmo_pos_years',0)}/7 dd={r.get('ftmo_closed_dd_R',0):.1f} top10={r.get('ftmo_top10_R',0):.1f}) "
            f"| swap=${r.get('ftmo_swap_usd_sum',0):+,.0f} | p_g={pg:.3f}(q={qg:.3f}) p_f={pf:.3f}(q={qf:.3f}) | {r['tier']}",
            flush=True,
        )

    # Automatic ±30% stability & USDJPY portfolio checks for any Tier 1 / Tier 2 survivor
    stability = {}
    portfolios = {}
    for r in runs:
        if r["tier"].startswith("TIER_3"):
            continue
        hid = r["strategy"]
        grid = {}
        if hid == "XAU_DAILY_OPEN_ATR":
            for t_a in (0.35, 0.50, 0.65):
                trs, _, _ = run_xau_daily_open_atr(xau_ctx, trig_atr=t_a)
                grid[f"trig_{t_a:.2f}"] = p14.summarize_pair(hid, "XAUUSD", False, trs, None)
        elif hid == "XAU_LONDON_NY_MOMENTUM":
            for b_a in (0.35, 0.45, 0.60):
                trs, _, _ = run_xau_london_ny_momentum(xau_ctx, body_atr=b_a)
                grid[f"body_{b_a:.2f}"] = p14.summarize_pair(hid, "XAUUSD", False, trs, None)
        elif hid == "XAU_H1_DONCHIAN_INTRADAY":
            for dn in (14, 20, 26):
                trs, _, _ = run_xau_h1_donchian_intraday(xau_ctx, don_n=dn)
                grid[f"don_{dn}"] = p14.summarize_pair(hid, "XAUUSD", False, trs, None)
        elif hid == "XAU_ASIA_SQUEEZE_BREAK":
            for mx in (0.28, 0.35, 0.45):
                trs, _, _ = run_xau_asia_squeeze_break(xau_ctx, max_asia_atr=mx)
                grid[f"max_asia_{mx:.2f}"] = p14.summarize_pair(hid, "XAUUSD", False, trs, None)
        elif hid == "CARRY_USDJPY_LONG_DONCHIAN20":
            for en, ex in ((15, 8), (20, 10), (26, 13)):
                trs = run_carry_donchian_d1(jpy_ctx, side=1, entry_n=en, exit_n=ex)
                grid[f"don_{en}_{ex}"] = p14.summarize_pair(hid, "USDJPY", True, trs, None)
        elif hid == "CARRY_USDJPY_LONG_PULLBACK_H4":
            for tpr in (2.0, 2.5, 3.0):
                trs = run_carry_usdjpy_pullback_h4(jpy_ctx, tp_r=tpr)
                grid[f"tp_{tpr:.1f}R"] = p14.summarize_pair(hid, "USDJPY", True, trs, None)
        elif hid == "CARRY_EURUSD_SHORT_DONCHIAN20":
            for en, ex in ((15, 8), (20, 10), (26, 13)):
                trs = run_carry_donchian_d1(eur_ctx, side=-1, entry_n=en, exit_n=ex)
                grid[f"don_{en}_{ex}"] = p14.summarize_pair(hid, "EURUSD", True, trs, None)

        stability[hid] = {
            k: {
                "n": v["n"], "ftmo_R": round(v.get("ftmo_net_R", 0.0), 2),
                "A": round(v.get("ftmo_clusters_R", {}).get("A", 0.0), 2),
                "B": round(v.get("ftmo_clusters_R", {}).get("B", 0.0), 2),
                "dd_R": round(v.get("ftmo_closed_dd_R", 0.0), 2),
            }
            for k, v in grid.items()
        }
        print(f"  STABILITY {hid}: {stability[hid]}", flush=True)
        if hid in tapes_by_id and tapes_by_id[hid]:
            portfolios[hid] = run_portfolio_check(jobs_root, tapes_by_id[hid], specs)
            sw10 = portfolios[hid]["books"]["Swing_10000"]["extended"]
            print(
                f"  PORTFOLIO {hid} + USDJPY (Swing 10k ext): "
                f"SoloJPY={sw10['SOLO_USDJPY_030']['annual_pct']['all']:.2f}%/yr(DD {sw10['SOLO_USDJPY_030']['peak_dd_pct']:.2f}%, uw {sw10['SOLO_USDJPY_030']['underwater_months']:.1f}m) | "
                f"Eq030={sw10['PORT_EQUAL_030']['annual_pct']['all']:.2f}%/yr(DD {sw10['PORT_EQUAL_030']['peak_dd_pct']:.2f}%, uw {sw10['PORT_EQUAL_030']['underwater_months']:.1f}m) | "
                f"Eq040={sw10['PORT_EQUAL_040']['annual_pct']['all']:.2f}%/yr(DD {sw10['PORT_EQUAL_040']['peak_dd_pct']:.2f}%, uw {sw10['PORT_EQUAL_040']['underwater_months']:.1f}m)",
                flush=True,
            )

    tier_counts = dict(Counter(r["tier"] for r in runs))
    result = {
        "pass": "Pass 15",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "spec_bindings": bindings,
        "tier_counts": tier_counts,
        "hypotheses": runs,
        "stability_checks": stability,
        "portfolio_checks": portfolios,
    }
    write(output_dir / "pass15-result.json", result)
    print(f"PASS15_DONE in {result['elapsed_seconds']}s | TIER_COUNTS={tier_counts}", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_pass15(args.jobs, args.cache, args.output)
