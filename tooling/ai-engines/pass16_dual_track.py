"""Pass 16: Track 1 (Wide-Expansion Low-Freq Intraday swap=0) & Track 2 (8 remaining H1 context leads, swap=0)."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass14_intel_top15_batch as p14
import pass15_ftmo_native_engine2 as p15
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "8e590ca2090f2fb20d132839901403bf0d1adc38"
TRACK_ASSETS = ("XAUUSD", "USDJPY", "EURUSD")


def cci(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, n: int = 20) -> np.ndarray:
    tp = (highs + lows + closes) / 3.0
    out = np.full(len(tp), np.nan, dtype=np.float64)
    for i in range(n - 1, len(tp)):
        win = tp[i - n + 1:i + 1]
        m = float(win.mean())
        md = float(np.abs(win - m).mean())
        out[i] = 0.0 if md <= 1e-12 else (tp[i] - m) / (0.015 * md)
    return out


# ==============================================================================
# TRACK 1: WIDE-EXPANSION LOW-FREQUENCY DAILY-OPEN ATR BREAKOUT (SWAP = 0)
# ==============================================================================

def run_wide_expansion(ctx, *, trig_atr: float, sl_atr: float = 0.75, use_ema50: bool = False, collect_tape: bool = False):
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, atr, c_d1 = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"], ctx["d1_c"]
    ema50 = p14.ema(c_d1, 50)
    trades, fades, tape = [], [], []
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
        open_0 = float(quotes[fi, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day["day_sec"] + 17 * 3600, side="left"))
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        up = (scan[:, 5] >= top - 1e-10) if allow_buy else np.zeros(len(scan), dtype=bool)
        dn = (scan[:, 2] <= bot + 1e-10) if allow_sell else np.zeros(len(scan), dtype=bool)
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + i0 + j
        entry_p = max(top, float(quotes[entry_i, 4])) if side == 1 else min(bot, float(quotes[entry_i, 0]))
        sl = entry_p - side * sl_atr * a_val
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            ft = p15._fade_trade(ctx, entry_i, side, abs(entry_p - sl), flat_sec)
            if ft:
                fades.append(ft)
            if collect_tape and asset == "XAUUSD":
                slc = p15._m1_portfolio_slice(ctx, entry_i, side, entry_p, sl, flat_sec)
                if slc:
                    tape.append(slc)
    return trades, fades, tape


# ==============================================================================
# TRACK 2: 8 REMAINING H1 INTRADAY STRATEGIES FROM 39 TÌNH HUỐNG (SWAP = 0)
# ==============================================================================

def run_brk011_camarilla(ctx):
    """BRK011: Camarilla R4/S4 breakout from prior completed D1, intraday flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off = ctx["full_d1"], ctx["d1_offset"]
    trades = []
    for idx in range(off, len(d1)):
        day, prev = d1[idx], d1[idx - 1]
        rng = prev["h"] - prev["l"]
        if rng <= 0:
            continue
        r4 = prev["c"] + rng * 0.55
        s4 = prev["c"] - rng * 0.55
        r3 = prev["c"] + rng * 0.275
        s3 = prev["c"] - rng * 0.275
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day["day_sec"] + 17 * 3600, side="left"))
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        up = scan[:, 5] >= r4 - 1e-10
        dn = scan[:, 2] <= s4 + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + i0 + j
        entry_p = max(r4, float(quotes[entry_i, 4])) if side == 1 else min(s4, float(quotes[entry_i, 0]))
        sl = r3 if side == 1 else s3
        tr = p14.replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
    return trades


def run_brk037_2bar_break(ctx):
    """BRK037: 2 consecutive H1 closes outside prior 20h Donchian channel, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, h, l, c, atr = ctx["h1"], ctx["h1_h"], ctx["h1_l"], ctx["h1_c"], ctx["h1_atr"]
    trades, traded = [], set()
    for k in range(22, len(h1)):
        dt = datetime.fromtimestamp(h1[k]["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        if not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        hi20 = h[k - 21:k - 1].max()
        lo20 = l[k - 21:k - 1].min()
        side = 0
        if c[k - 1] > hi20 and c[k] > hi20:
            side = 1
        elif c[k - 1] < lo20 and c[k] < lo20:
            side = -1
        if not side:
            continue
        ei = int(times.searchsorted(h1[k]["end_sec"], side="left"))
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if ei >= len(times) or times[ei] - h1[k]["end_sec"] > 900 or times[ei] >= flat_sec:
            continue
        ep = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = ep - side * 1.5 * atr[k]
        tr = p14.replay_trade_m1(asset, times, quotes, ei, side, ep, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded.add(dt.date())
    return trades


def run_ind017_cci100(ctx):
    """IND017: H1 CCI(20) crossing ±100 in 07:00-17:00 UTC, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, h, l, c, atr = ctx["h1"], ctx["h1_h"], ctx["h1_l"], ctx["h1_c"], ctx["h1_atr"]
    cv = cci(h, l, c, 20)
    trades, traded = [], set()
    for k in range(21, len(h1)):
        dt = datetime.fromtimestamp(h1[k]["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        if not (np.isfinite(cv[k]) and np.isfinite(cv[k - 1]) and np.isfinite(atr[k]) and atr[k] > 0):
            continue
        side = 1 if (cv[k] > 100.0 and cv[k - 1] <= 100.0) else (-1 if (cv[k] < -100.0 and cv[k - 1] >= -100.0) else 0)
        if not side:
            continue
        ei = int(times.searchsorted(h1[k]["end_sec"], side="left"))
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if ei >= len(times) or times[ei] - h1[k]["end_sec"] > 900 or times[ei] >= flat_sec:
            continue
        ep = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = ep - side * 1.5 * atr[k]
        tr = p14.replay_trade_m1(asset, times, quotes, ei, side, ep, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded.add(dt.date())
    return trades


def run_ind027_ema9_21(ctx):
    """IND027: H1 EMA(9)/EMA(21) cross in 07:00-17:00 UTC, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, c, atr = ctx["h1"], ctx["h1_c"], ctx["h1_atr"]
    e9, e21 = p14.ema(c, 9), p14.ema(c, 21)
    trades, traded = [], set()
    for k in range(22, len(h1)):
        dt = datetime.fromtimestamp(h1[k]["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        if not (np.isfinite(e9[k]) and np.isfinite(e21[k]) and np.isfinite(e9[k - 1]) and np.isfinite(e21[k - 1]) and np.isfinite(atr[k]) and atr[k] > 0):
            continue
        side = 1 if (e9[k] > e21[k] and e9[k - 1] <= e21[k - 1]) else (-1 if (e9[k] < e21[k] and e9[k - 1] >= e21[k - 1]) else 0)
        if not side:
            continue
        ei = int(times.searchsorted(h1[k]["end_sec"], side="left"))
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if ei >= len(times) or times[ei] - h1[k]["end_sec"] > 900 or times[ei] >= flat_sec:
            continue
        ep = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = ep - side * 1.5 * atr[k]
        tr = p14.replay_trade_m1(asset, times, quotes, ei, side, ep, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded.add(dt.date())
    return trades


def run_mtf005_weekly_reject(ctx):
    """MTF005: Prior completed week High/Low + H1 rejection wick reversal, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, h1 = ctx["full_d1"], ctx["h1"]
    buf = 0.50 if asset == "XAUUSD" else (0.02 if asset == "USDJPY" else 0.0002)
    # Build causal ISO-week high/low table from completed D1 bars
    wk_hi, wk_lo = defaultdict(lambda: -1e18), defaultdict(lambda: 1e18)
    for b in d1:
        yw = b["date"].isocalendar()[:2]
        wk_hi[yw] = max(wk_hi[yw], b["h"])
        wk_lo[yw] = min(wk_lo[yw], b["l"])
    weeks_sorted = sorted(wk_hi.keys())
    prev_wk_map = {weeks_sorted[i]: weeks_sorted[i - 1] for i in range(1, len(weeks_sorted))}

    trades, traded = [], set()
    for k in range(1, len(h1)):
        bar = h1[k]
        dt = datetime.fromtimestamp(bar["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        pw = prev_wk_map.get(dt.date().isocalendar()[:2])
        if pw is None:
            continue
        wh, wl = wk_hi[pw], wk_lo[pw]
        side = 0
        sl = 0.0
        if bar["h"] >= wh and bar["c"] < wh and bar["c"] < bar["o"]:
            side = -1
            sl = bar["h"] + buf
        elif bar["l"] <= wl and bar["c"] > wl and bar["c"] > bar["o"]:
            side = 1
            sl = bar["l"] - buf
        if not side:
            continue
        ei = int(times.searchsorted(bar["end_sec"], side="left"))
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if ei >= len(times) or times[ei] - bar["end_sec"] > 900 or times[ei] >= flat_sec:
            continue
        ep = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        if side * (ep - sl) <= 0:
            continue
        tr = p14.replay_trade_m1(asset, times, quotes, ei, side, ep, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded.add(dt.date())
    return trades


def run_nen024_vbottom(ctx):
    """NEN024: V-bottom H1 — bear bar <= -2 ATR followed immediately by bull bar >= +2 ATR -> BUY, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, atr = ctx["h1"], ctx["h1_atr"]
    buf = 0.50 if asset == "XAUUSD" else (0.02 if asset == "USDJPY" else 0.0002)
    trades, traded = [], set()
    for k in range(15, len(h1)):
        b0, b1 = h1[k - 1], h1[k]
        dt = datetime.fromtimestamp(b1["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (1 <= dt.hour <= 17):
            continue
        if not np.isfinite(atr[k - 1]) or atr[k - 1] <= 0 or (b1["start_sec"] - b0["end_sec"]) > 3600:
            continue
        if (b0["c"] - b0["o"]) <= -2.0 * atr[k - 1] and (b1["c"] - b1["o"]) >= 2.0 * atr[k - 1]:
            ei = int(times.searchsorted(b1["end_sec"], side="left"))
            flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
            if ei >= len(times) or times[ei] - b1["end_sec"] > 900 or times[ei] >= flat_sec:
                continue
            ep = float(quotes[ei, 4])
            sl = min(b0["l"], b1["l"]) - buf
            if sl >= ep:
                continue
            tr = p14.replay_trade_m1(asset, times, quotes, ei, 1, ep, sl, None, flat_sec, spec, intraday_flat=True)
            if tr:
                trades.append(tr)
                traded.add(dt.date())
    return trades


def run_nen029_mon_gap(ctx):
    """NEN029: Monday open gap >= 1.0*ATR_H1 -> follow gap direction intraday, flat 20:55 UTC."""
    times, quotes, bid4, spec, asset = ctx["times"], ctx["quotes"], ctx["bid4"], ctx["spec"], ctx["asset"]
    d1, off, h1, h1_atr = ctx["full_d1"], ctx["d1_offset"], ctx["h1"], ctx["h1_atr"]
    h1_end = np.array([b["end_sec"] for b in h1], dtype=np.int64)
    trades = []
    for idx in range(off, len(d1)):
        mon, fri = d1[idx], d1[idx - 1]
        if mon["date"].weekday() != 0 or fri["date"].weekday() != 4 or (mon["date"] - fri["date"]).days != 3:
            continue
        k_atr = int(h1_end.searchsorted(mon["day_sec"], side="right")) - 1
        if k_atr < 14 or not np.isfinite(h1_atr[k_atr]) or h1_atr[k_atr] <= 0:
            continue
        gap = mon["o"] - fri["c"]
        if abs(gap) < 1.0 * h1_atr[k_atr]:
            continue
        side = 1 if gap > 0 else -1
        ei = p14.find_m1_at(times, mon["fi"], mon["ei"], mon["day_sec"] + 3600)
        flat_sec = mon["day_sec"] + 20 * 3600 + 55 * 60
        ep = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = ep - side * 1.5 * h1_atr[k_atr]
        tr = p14.replay_trade_m1(asset, times, quotes, ei, side, ep, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
    return trades


def run_vir024_3line_strike(ctx):
    """VIR024: 3 consecutive bearish H1 bars + 1 bullish bar closing > bar1 open -> BUY, flat 20:55 UTC."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1 = ctx["h1"]
    buf = 0.50 if asset == "XAUUSD" else (0.02 if asset == "USDJPY" else 0.0002)
    trades, traded = [], set()
    for k in range(3, len(h1)):
        b1, b2, b3, b4 = h1[k - 3], h1[k - 2], h1[k - 1], h1[k]
        dt = datetime.fromtimestamp(b4["end_sec"], timezone.utc)
        if dt.date() in traded or dt.weekday() >= 5 or not (7 <= dt.hour <= 17):
            continue
        if (b4["start_sec"] - b1["start_sec"]) > 6 * 3600:
            continue
        if (b1["c"] < b1["o"] and b2["c"] < b2["o"] and b3["c"] < b3["o"]
                and b2["l"] < b1["l"] and b3["l"] < b2["l"]
                and b4["c"] > b1["o"]):
            ei = int(times.searchsorted(b4["end_sec"], side="left"))
            flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
            if ei >= len(times) or times[ei] - b4["end_sec"] > 900 or times[ei] >= flat_sec:
                continue
            ep = float(quotes[ei, 4])
            sl = min(b1["l"], b2["l"], b3["l"], b4["l"]) - buf
            if sl >= ep:
                continue
            tr = p14.replay_trade_m1(asset, times, quotes, ei, 1, ep, sl, None, flat_sec, spec, intraday_flat=True)
            if tr:
                trades.append(tr)
                traded.add(dt.date())
    return trades


TRACK2_STRATS = {
    "BRK011": run_brk011_camarilla,
    "BRK037": run_brk037_2bar_break,
    "IND017": run_ind017_cci100,
    "IND027": run_ind027_ema9_21,
    "MTF005": run_mtf005_weekly_reject,
    "NEN024": run_nen024_vbottom,
    "NEN029": run_nen029_mon_gap,
    "VIR024": run_vir024_3line_strike,
}


def run_track1(jobs_root: Path, cache_dir: Path, output_dir: Path):
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    defs = [
        ("EXP_DAILY_OPEN_080", dict(trig_atr=0.80, use_ema50=False)),
        ("EXP_DAILY_OPEN_100", dict(trig_atr=1.00, use_ema50=False)),
        ("EXP_DAILY_OPEN_120", dict(trig_atr=1.20, use_ema50=False)),
        ("EXP_DAILY_OPEN_080_TREND", dict(trig_atr=0.80, use_ema50=True)),
    ]
    rows = []
    portfolios = {}
    for asset in TRACK_ASSETS:
        ctx = p14.build_asset_context(jobs_root, asset, cache_dir, swing_specs[asset])
        for sid, kwargs in defs:
            trs, fades, tape = run_wide_expansion(ctx, collect_tape=True, **kwargs)
            mc = p14.mc_null_test(ctx, trs)
            r = p14.summarize_pair(sid, asset, ctx["meta"]["native_Ask"], trs, mc)
            r["fade_ftmo_R"] = fsum(t["ftmo_R"] for t in fades)
            rows.append(r)
            if not r["tier"].startswith("TIER_3") and asset == "XAUUSD" and tape:
                portfolios[f"{sid}_{asset}"] = p15.run_portfolio_check(jobs_root, tape, specs)

    q_g = p14.benjamini_hochberg([r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    for r, qg, qf in zip(rows, q_g, q_f):
        r["fdr_gross_q"], r["fdr_ftmo_q"] = qg, qf
        pg = r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0
        pf = r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0
        print(
            f"T1 {r['strategy']:25s} {r['asset']:6s} | n={r['n']:4d} | FTMO_R={r.get('ftmo_net_R',0):+7.2f} "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7) "
            f"| Fade={r['fade_ftmo_R']:+7.1f} | p_g={pg:.3f}(q={qg:.3f}) p_f={pf:.3f} | {r['tier']}",
            flush=True,
        )

    out = {
        "track": "Track1_Wide_Expansion_LowFreq_Intraday",
        "protocol_commit": PROTOCOL, "holdout_rows": 0, "order_send_count": 0, "network_calls": 0,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows, "portfolios": portfolios,
    }
    write(output_dir / "track1-result.json", out)
    print(f"TRACK1_DONE in {out['elapsed_seconds']}s | {out['tier_counts']}", flush=True)


def run_track2(jobs_root: Path, cache_dir: Path, output_dir: Path):
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    rows = []
    for asset in TRACK_ASSETS:
        ctx = p14.build_asset_context(jobs_root, asset, cache_dir, swing_specs[asset])
        for sid, fn in TRACK2_STRATS.items():
            trs = fn(ctx)
            mc = p14.mc_null_test(ctx, trs)
            rows.append(p14.summarize_pair(sid, asset, ctx["meta"]["native_Ask"], trs, mc))

    q_g = p14.benjamini_hochberg([r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0 for r in rows])
    for r, qg, qf in zip(rows, q_g, q_f):
        r["fdr_gross_q"], r["fdr_ftmo_q"] = qg, qf
        pg = r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0
        pf = r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0
        print(
            f"T2 {r['strategy']:6s} {r['asset']:6s} | n={r['n']:4d} | FTMO_R={r.get('ftmo_net_R',0):+7.2f} "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7) "
            f"| p_g={pg:.3f}(q={qg:.3f}) p_f={pf:.3f} | {r['tier']}",
            flush=True,
        )

    out = {
        "track": "Track2_Intel_8_Remaining_H1_Context_Intraday",
        "protocol_commit": PROTOCOL, "holdout_rows": 0, "order_send_count": 0, "network_calls": 0,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows,
    }
    write(output_dir / "track2-result.json", out)
    print(f"TRACK2_DONE in {out['elapsed_seconds']}s | {out['tier_counts']}", flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--track", choices=("track1", "track2"), required=True)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.track == "track1":
        run_track1(args.jobs, args.cache, args.output)
    else:
        run_track2(args.jobs, args.cache, args.output)
