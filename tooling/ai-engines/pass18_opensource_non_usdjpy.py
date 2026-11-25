"""Pass 18: Open-Source Academic & MQL5 CodeBase Non-USDJPY Engine #3 Screen (14 causal swap=0 hypotheses)."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass12_us500_ny_orb as us500_orb
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "467a0286d53f7ae5743bb3241cf2c458c7c8d137"
SEED = 20261123
MC_DRAWS = 1000


def last_sunday_of_month(year: int, month: int) -> date:
    """Return the last Sunday of (year, month) for exact UK BST / London DST transitions."""
    d = date(year, month, 31)
    offset = (d.weekday() + 1) % 7  # Sunday -> 0, Monday -> 1, ..., Saturday -> 6
    return date(year, month, 31 - offset)


def london_utc_offset_hours(d: date) -> int:
    """Exact Europe/London UTC offset (1 during BST: last Sun Mar -> last Sun Oct, else 0)."""
    bst_start = last_sunday_of_month(d.year, 3)
    bst_end = last_sunday_of_month(d.year, 10)
    return 1 if bst_start <= d < bst_end else 0


def london_to_utc_sec(d: date, hour: int, minute: int = 0) -> int:
    """Convert Europe/London local wall-clock (hour, minute) on date d to UTC epoch seconds."""
    off = london_utc_offset_hours(d)
    dt_utc = datetime(d.year, d.month, d.day, 0, 0, tzinfo=timezone.utc)
    return int(dt_utc.timestamp()) + (hour - off) * 3600 + minute * 60


def build_us500_sessions(times: np.ndarray, quotes: np.ndarray) -> tuple[list[dict], np.ndarray]:
    """Build causal completed NYSE cash-session daily bars (09:30..15:55 ET) + Wilder ATR14."""
    all_sessions = []
    for y in clock.YEAR:
        sess, _ = us500_orb.calendar(y)
        for dkey, start in sorted(sess.items()):
            lo, hi = times.searchsorted([start, start + 386 * 60])
            if hi - lo < 300:
                continue
            q = quotes[lo:hi]
            all_sessions.append({
                "day": dkey, "year": y, "start": int(start), "lo": int(lo), "hi": int(hi),
                "o": float(q[0, 0]), "h": float(q[:, 1].max()),
                "l": float(q[:, 2].min()), "c": float(q[-1, 3]),
            })
    hs = np.array([s["h"] for s in all_sessions], dtype=np.float64)
    ls = np.array([s["l"] for s in all_sessions], dtype=np.float64)
    cs = np.array([s["c"] for s in all_sessions], dtype=np.float64)
    atr = p14.wilder_atr(hs, ls, cs, 14)
    return all_sessions, atr


def sim_us500_trade(
    times: np.ndarray,
    quotes: np.ndarray,
    sess: dict,
    rel_entry: int,
    side: int,
    sl_pts: float,
    tp_pts: float | None = None,
    *,
    slip_side: float = 0.75,
) -> dict | None:
    """Exact Native Bid/Ask M1 simulation on US500 NYSE session with SL-first conservative check (swap=0)."""
    lo, hi = sess["lo"], sess["hi"]
    q = quotes[lo:hi]
    if rel_entry < 0 or rel_entry >= len(q) - 1 or sl_pts <= 0:
        return None
    entry_p = float(q[rel_entry, 4] if side == 1 else q[rel_entry, 0])
    sl_p = entry_p - side * sl_pts
    tp_p = (entry_p + side * tp_pts) if (tp_pts is not None and tp_pts > 0) else None

    liq = q[rel_entry:, :4] if side == 1 else q[rel_entry:, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 1] >= tp_p - 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 2] <= tp_p + 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)

    f_sl = int(sl_hits[0]) if len(sl_hits) else None
    f_tp = int(tp_hits[0]) if len(tp_hits) else None

    if f_sl is not None and (f_tp is None or f_sl <= f_tp):
        k = f_sl
        op = float(liq[k, 0])
        gap = k > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        reason = "SL_GAP_OR_TOUCH"
        ex_rel = rel_entry + k
    elif f_tp is not None:
        k = f_tp
        op = float(liq[k, 0])
        gap = k > 0 and side * (op - tp_p) >= -1e-10
        ex_p = op if gap else tp_p
        reason = "TP_GAP_OR_TOUCH"
        ex_rel = rel_entry + k
    else:
        ex_p = float(liq[-1, 0])
        reason = "HARD_FLAT"
        ex_rel = len(q) - 1

    e_ts = int(times[lo + rel_entry])
    x_ts = int(times[lo + ex_rel])
    assert START <= e_ts <= x_ts < STOP
    gross = side * (ex_p - entry_p)
    net_stress = gross - 2.0 * slip_side
    risk_stress = sl_pts + 2.0 * slip_side
    net_mid = gross - 1.00
    risk_mid = sl_pts + 1.00
    net_base = gross - 0.50
    risk_base = sl_pts + 0.50
    return {
        "day": sess["day"], "year": sess["year"], "side": side, "reason": reason,
        "entry": e_ts, "exit": x_ts, "hold_hours": max(0.25, (x_ts - e_ts) / 3600.0),
        "gross_usd": gross, "ftmo_comm_slip": 2.0 * slip_side, "ftmo_swap": 0.0,
        "ftmo_net": net_stress, "ftmo_R": net_stress / risk_stress,
        "base_R": net_base / risk_base, "mid_R": net_mid / risk_mid,
        "ex_R_normal": net_base / risk_base, "ex_R_swapfree": net_base / risk_base,
    }


def run_us500_strategies(times: np.ndarray, quotes: np.ndarray) -> dict[str, tuple[list[dict], list[dict], list[dict]]]:
    """Run all 4 pre-registered academic US500 intraday strategies (swap=0)."""
    sessions, atr = build_us500_sessions(times, quotes)
    out = {k: ([], []) for k in ("US500_GHLZ_LAST30", "US500_GHLZ_AFTERNOON", "US500_GAP_FADE_NY", "US500_IBS_INTRADAY")}

    for idx in range(15, len(sessions)):
        prev_s = sessions[idx - 1]
        s = sessions[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        lo, hi = s["lo"], s["hi"]
        offs = (times[lo:hi] - s["start"]) // 60
        q = quotes[lo:hi]
        sl_pts = 0.75 * a_val

        # Helper to find first bar at/after target minute offset
        def idx_at(m_off: int) -> int | None:
            j = int(offs.searchsorted(m_off, side="left"))
            if j >= len(offs) - 1 or int(offs[j]) > m_off + 10:
                return None
            return j

        # 1. US500_GHLZ_LAST30: Gao-Han-Li-Zhou (2018 JFE) first half-hour -> last half-hour (15:30..15:55 ET)
        j_1000 = idx_at(30)
        j_1530 = idx_at(360)
        if j_1000 is not None and j_1530 is not None:
            r1 = (float(q[j_1000, 0]) - prev_s["c"]) / a_val
            if abs(r1) >= 0.25:
                side = 1 if r1 > 0 else -1
                tr = sim_us500_trade(times, quotes, s, j_1530, side, sl_pts)
                fd = sim_us500_trade(times, quotes, s, j_1530, -side, sl_pts)
                if tr and fd:
                    out["US500_GHLZ_LAST30"][0].append(tr)
                    out["US500_GHLZ_LAST30"][1].append(fd)

        # 2. US500_GHLZ_AFTERNOON: First-hour NY return (09:30->10:30 ET) -> afternoon (13:30..15:55 ET)
        j_1030 = idx_at(60)
        j_1330 = idx_at(240)
        if j_1030 is not None and j_1330 is not None:
            r1h = (float(q[j_1030, 0]) - s["o"]) / a_val
            if abs(r1h) >= 0.35:
                side = 1 if r1h > 0 else -1
                tr = sim_us500_trade(times, quotes, s, j_1330, side, sl_pts)
                fd = sim_us500_trade(times, quotes, s, j_1330, -side, sl_pts)
                if tr and fd:
                    out["US500_GHLZ_AFTERNOON"][0].append(tr)
                    out["US500_GHLZ_AFTERNOON"][1].append(fd)

        # 3. US500_GAP_FADE_NY: Lou-Polk-Skouras (2019 JFE) fade overnight gap >= 0.35 ATR at 09:35 ET
        j_0935 = idx_at(5)
        if j_0935 is not None:
            gap_pts = s["o"] - prev_s["c"]
            if abs(gap_pts) / a_val >= 0.35:
                side = -1 if gap_pts > 0 else 1
                tp_pts = 0.60 * abs(gap_pts)
                tr = sim_us500_trade(times, quotes, s, j_0935, side, sl_pts, tp_pts=tp_pts)
                fd = sim_us500_trade(times, quotes, s, j_0935, -side, sl_pts, tp_pts=tp_pts)
                if tr and fd:
                    out["US500_GAP_FADE_NY"][0].append(tr)
                    out["US500_GAP_FADE_NY"][1].append(fd)

        # 4. US500_IBS_INTRADAY: Quantpedia IBS <= 0.20 BUY / >= 0.80 SELL at 09:35 ET
        prev_rng = prev_s["h"] - prev_s["l"]
        if j_0935 is not None and prev_rng > 1e-9:
            ibs = (prev_s["c"] - prev_s["l"]) / prev_rng
            side = 1 if ibs <= 0.20 else (-1 if ibs >= 0.80 else 0)
            if side != 0:
                tr = sim_us500_trade(times, quotes, s, j_0935, side, sl_pts)
                fd = sim_us500_trade(times, quotes, s, j_0935, -side, sl_pts)
                if tr and fd:
                    out["US500_IBS_INTRADAY"][0].append(tr)
                    out["US500_IBS_INTRADAY"][1].append(fd)

    return {k: (v[0], v[1], sessions) for k, v in out.items()}


def sim_fx_base_and_stress(ctx: dict, entry_idx: int, side: int, entry_p: float, sl_p: float, max_exit_sec: int) -> dict | None:
    """Replay M1 FX/XAU intraday trade (swap=0) with FTMO Stress + FTMO Base + Exness reference."""
    tr = p14.replay_trade_m1(
        ctx["asset"], ctx["times"], ctx["quotes"],
        entry_idx, side, entry_p, sl_p, None, max_exit_sec, ctx["spec"],
        intraday_flat=True,
    )
    if tr is None:
        return None
    tr["day"] = datetime.fromtimestamp(tr["entry"], timezone.utc).date().isoformat()
    # Add FTMO Base (zero extra +0.5 pip stress addon on FX; $0.20 slip on XAU)
    asset = ctx["asset"]
    spec = ctx["spec"]
    exit_p = float(ctx["quotes"][int(ctx["times"].searchsorted(tr["exit"], side="left")), 3 if side == 1 else 7])
    addon_p = 0.20 if asset == "XAUUSD" else (0.005 if asset == "USDJPY" else 0.00005)
    addon_usd = p14.price_to_usd_per_lot(asset, addon_p, exit_p, spec)
    base_net = tr["ftmo_net"] + addon_usd
    base_risk = max(1e-9, tr["ftmo_risk"] - addon_usd)
    tr["base_R"] = base_net / base_risk
    return tr


def run_fx_wmr_strategies(ctx: dict) -> dict[str, tuple[list[dict], list[dict]]]:
    """Run Krohn-Mueller-Whelan (2024 JoF) London 16:00 WMR Fix strategies on EURUSD/GBPUSD (swap=0)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    out = {k: ([], []) for k in ("FX_WMR_PRE_FIX", "FX_WMR_POST_FIX", "FX_WMR_MORNING_FADE")}

    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        d_obj = day["date"]
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]

        def find_exact(h_lon: int, m_lon: int) -> int | None:
            target = london_to_utc_sec(d_obj, h_lon, m_lon)
            j = int(sub_t.searchsorted(target, side="left"))
            if j >= len(sub_t) or int(sub_t[j]) - target > 600:
                return None
            return fi + j

        sl_dist = 0.75 * a_val

        # 5/6. FX_WMR_PRE_FIX: SELL at 13:00 London -> flat 15:55 London
        i_1300 = find_exact(13, 0)
        t_1555 = london_to_utc_sec(d_obj, 15, 55)
        if i_1300 is not None and int(times[i_1300]) < t_1555:
            ep_s = float(quotes[i_1300, 0])
            ep_b = float(quotes[i_1300, 4])
            tr = sim_fx_base_and_stress(ctx, i_1300, -1, ep_s, ep_s + sl_dist, t_1555)
            fd = sim_fx_base_and_stress(ctx, i_1300, 1, ep_b, ep_b - sl_dist, t_1555)
            if tr and fd:
                out["FX_WMR_PRE_FIX"][0].append(tr)
                out["FX_WMR_PRE_FIX"][1].append(fd)

        # 7/8. FX_WMR_POST_FIX: BUY at 16:05 London -> flat 20:55 London
        i_1605 = find_exact(16, 5)
        t_2055 = london_to_utc_sec(d_obj, 20, 55)
        if i_1605 is not None and int(times[i_1605]) < t_2055:
            ep_b = float(quotes[i_1605, 4])
            ep_s = float(quotes[i_1605, 0])
            tr = sim_fx_base_and_stress(ctx, i_1605, 1, ep_b, ep_b - sl_dist, t_2055)
            fd = sim_fx_base_and_stress(ctx, i_1605, -1, ep_s, ep_s + sl_dist, t_2055)
            if tr and fd:
                out["FX_WMR_POST_FIX"][0].append(tr)
                out["FX_WMR_POST_FIX"][1].append(fd)

        # 9/10. FX_WMR_MORNING_FADE: if 07:00->15:55 London move >= 0.50 ATR, fade at 16:05 -> 20:55 London
        i_0700 = find_exact(7, 0)
        i_1555 = find_exact(15, 55)
        if i_0700 is not None and i_1555 is not None and i_1605 is not None and int(times[i_1605]) < t_2055:
            move = float(quotes[i_1555, 0] - quotes[i_0700, 0])
            if abs(move) >= 0.50 * a_val:
                side = -1 if move > 0 else 1
                ep = float(quotes[i_1605, 4] if side == 1 else quotes[i_1605, 0])
                fep = float(quotes[i_1605, 4] if side == -1 else quotes[i_1605, 0])
                tr = sim_fx_base_and_stress(ctx, i_1605, side, ep, ep - side * sl_dist, t_2055)
                fd = sim_fx_base_and_stress(ctx, i_1605, -side, fep, fep + side * sl_dist, t_2055)
                if tr and fd:
                    out["FX_WMR_MORNING_FADE"][0].append(tr)
                    out["FX_WMR_MORNING_FADE"][1].append(fd)

    return out


def run_nr4_expansion(ctx: dict, trig_atr: float = 0.65, sl_atr: float = 0.75) -> tuple[list[dict], list[dict]]:
    """Toby Crabel (1990) / MQL5 CodeBase NR4 Volatility Compression Breakout (07:00-17:00 UTC, flat 20:55 UTC, swap=0)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    ranges = ctx["d1_h"] - ctx["d1_l"]
    trades, fades = [], []

    for idx in range(max(off, 4), len(d1)):
        # Causal NR4: completed day idx-1 has strictly narrowest range of {idx-1, idx-2, idx-3, idx-4}
        if not (ranges[idx - 1] < min(ranges[idx - 2], ranges[idx - 3], ranges[idx - 4])):
            continue
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        day = d1[idx]
        fi, ei = day["fi"], day["ei"]
        day_sec = day["day_sec"]
        open_0 = float(quotes[fi, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(day_sec + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(day_sec + 17 * 3600, side="left"))
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
        entry_idx = fi + i0 + j
        ep = max(top, float(quotes[entry_idx, 4])) if side == 1 else min(bot, float(quotes[entry_idx, 0]))
        fep = float(quotes[entry_idx, 4] if side == -1 else quotes[entry_idx, 0])
        t_flat = day_sec + 20 * 3600 + 55 * 60
        tr = sim_fx_base_and_stress(ctx, entry_idx, side, ep, ep - side * sl_atr * a_val, t_flat)
        fd = sim_fx_base_and_stress(ctx, entry_idx, -side, fep, fep + side * sl_atr * a_val, t_flat)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def run_xau_lbma_pm_drift(ctx: dict) -> tuple[list[dict], list[dict]]:
    """Caminschi & Heaney (2014 JFM) London AM -> COMEX/PM Fix momentum drift on XAUUSD (swap=0)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades = [], []

    for idx in range(off, len(d1)):
        day = d1[idx]
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        d_obj = day["date"]
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]

        def find_exact(h_lon: int, m_lon: int) -> int | None:
            target = london_to_utc_sec(d_obj, h_lon, m_lon)
            j = int(sub_t.searchsorted(target, side="left"))
            if j >= len(sub_t) or int(sub_t[j]) - target > 600:
                return None
            return fi + j

        i_0700 = find_exact(7, 0)
        i_1300 = find_exact(13, 0)
        i_1305 = find_exact(13, 5)
        t_flat = day["day_sec"] + 20 * 3600 + 55 * 60
        if i_0700 is None or i_1300 is None or i_1305 is None or int(times[i_1305]) >= t_flat:
            continue
        move = float(quotes[i_1300, 0] - quotes[i_0700, 0])
        if abs(move) < 0.40 * a_val:
            continue
        side = 1 if move > 0 else -1
        ep = float(quotes[i_1305, 4] if side == 1 else quotes[i_1305, 0])
        fep = float(quotes[i_1305, 4] if side == -1 else quotes[i_1305, 0])
        sl_dist = 0.75 * a_val
        tr = sim_fx_base_and_stress(ctx, i_1305, side, ep, ep - side * sl_dist, t_flat)
        fd = sim_fx_base_and_stress(ctx, i_1305, -side, fep, fep + side * sl_dist, t_flat)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def sign_flip_null_p(trades: list[dict], fades: list[dict], *, draws: int = MC_DRAWS) -> dict:
    """Exact paired Rademacher sign-flip null on identical entry/exit windows (eliminates duration distortion)."""
    if not trades or len(trades) != len(fades):
        return {"gross_p": 1.0, "ftmo_net_p": 1.0}
    rng = np.random.default_rng(SEED + 18)
    g_pos = np.array([t["gross_usd"] for t in trades], dtype=np.float64)
    g_neg = np.array([f["gross_usd"] for f in fades], dtype=np.float64)
    n_pos = np.array([t["ftmo_net"] for t in trades], dtype=np.float64)
    n_neg = np.array([f["ftmo_net"] for f in fades], dtype=np.float64)
    n = len(trades)
    flips = rng.integers(0, 2, size=(draws, n), dtype=np.int8)
    null_g = (flips * g_pos + (1 - flips) * g_neg).sum(axis=1)
    null_n = (flips * n_pos + (1 - flips) * n_neg).sum(axis=1)
    obs_g = float(g_pos.sum())
    obs_n = float(n_pos.sum())
    return {
        "gross_p": float((np.sum(null_g >= obs_g) + 1) / (draws + 1)),
        "ftmo_net_p": float((np.sum(null_n >= obs_n) + 1) / (draws + 1)),
    }


def direction_breakdown(trades: list[dict]) -> dict:
    out = {}
    for label, s in (("BUY", 1), ("SELL", -1)):
        sub = [t for t in trades if t["side"] == s]
        out[label] = {
            "n": len(sub),
            "ftmo_R": round(fsum(t["ftmo_R"] for t in sub), 2),
            "base_R": round(fsum(t.get("base_R", t["ftmo_R"]) for t in sub), 2),
        }
    return out


def daily_correlation(trades: list[dict], core_daily: dict[str, float]) -> dict:
    """Pearson correlation of daily net R vs Pass 17 frozen USDJPY 2-engine core (PORT_INV_DD_075)."""
    cand = defaultdict(float)
    for t in trades:
        cand[t["day"]] += t["ftmo_R"]
    union_days = sorted(set(cand.keys()) | set(core_daily.keys()))
    overlap_days = sorted(set(cand.keys()) & set(core_daily.keys()))
    def corr(days):
        if len(days) < 20:
            return None
        x = np.array([cand.get(d, 0.0) for d in days], dtype=np.float64)
        y = np.array([core_daily.get(d, 0.0) for d in days], dtype=np.float64)
        if np.std(x) < 1e-12 or np.std(y) < 1e-12:
            return 0.0
        return round(float(np.corrcoef(x, y)[0, 1]), 4)
    return {"union_corr": corr(union_days), "overlap_corr": corr(overlap_days), "overlap_days": len(overlap_days)}


def build_usdjpy_core_daily_series(jobs_root: Path, cache_dir: Path, specs: dict) -> dict[str, float]:
    """Daily net-R proxy for Pass 17 frozen USDJPY 2-engine core (0.35 Tokyo-box + 0.65 EXP_DAILY_OPEN_080)."""
    core = defaultdict(float)
    ref_trades, _ = portfolio.frozen_usdjpy(jobs_root)
    for dkey, (row, *_) in ref_trades.items():
        core[dkey] += 0.35 * row["net_R"]
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    exp_tape = p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    for row, _, _ in exp_tape:
        core[row["day"]] += 0.65 * row["net_R"]
    return dict(core)


def run_pass18(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    core_daily = build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)

    rows = []

    def package_row(sid: str, asset: str, source: str, native_ask: bool, trs: list[dict], fds: list[dict], mc_rand: dict | None):
        sf = sign_flip_null_p(trs, fds)
        # Conservative effective p-value = max(random_entry_null, paired_sign_flip_null)
        mc_eff = dict(mc_rand) if mc_rand else {"gross_p_value": 1.0, "ftmo_net_p_value": 1.0}
        mc_eff["random_entry_gross_p"] = mc_eff["gross_p_value"]
        mc_eff["random_entry_ftmo_p"] = mc_eff["ftmo_net_p_value"]
        mc_eff["sign_flip_gross_p"] = sf["gross_p"]
        mc_eff["sign_flip_ftmo_p"] = sf["ftmo_net_p"]
        mc_eff["gross_p_value"] = max(mc_eff["gross_p_value"], sf["gross_p"])
        mc_eff["ftmo_net_p_value"] = max(mc_eff["ftmo_net_p_value"], sf["ftmo_net_p"])

        r = p14.summarize_pair(sid, asset, native_ask, trs, mc_eff)
        r["source"] = source
        r["fade_ftmo_R"] = round(fsum(t["ftmo_R"] for t in fds), 2)
        r["ftmo_base_R"] = round(fsum(t.get("base_R", t["ftmo_R"]) for t in trs), 2)
        if asset == "US500":
            r["us500_mid_R"] = round(fsum(t.get("mid_R", t["ftmo_R"]) for t in trs), 2)
        r["direction"] = direction_breakdown(trs)
        r["corr_usdjpy_core"] = daily_correlation(trs, core_daily)
        rows.append(r)

    # 1. US500 (4 academic strategies, Native Bid/Ask M1)
    us_times, us_quotes, _ = hcache.load_asset("US500", cache_dir, verify_sha=True)
    us_res = run_us500_strategies(us_times, us_quotes)
    us_sources = {
        "US500_GHLZ_LAST30": "Gao-Han-Li-Zhou (2018 JFE) Intraday Momentum Last30",
        "US500_GHLZ_AFTERNOON": "Gao-Han-Li-Zhou (2018 JFE) First-Hour->Afternoon",
        "US500_GAP_FADE_NY": "Lou-Polk-Skouras (2019 JFE) Overnight Gap Fade",
        "US500_IBS_INTRADAY": "Quantpedia / Connors IBS Intraday",
    }
    for sid, src in us_sources.items():
        trs, fds, all_s = us_res[sid]
        mc = p17.mc_us500_null(us_times, us_quotes, trs, all_s, slip_side=0.75)
        package_row(sid, "US500", src, True, trs, fds, mc)

    # 2. EURUSD & GBPUSD (Krohn-Mueller-Whelan 2024 JoF WMR Fix + Crabel NR4, Native Bid/Ask M1)
    wmr_sources = {
        "FX_WMR_PRE_FIX": "Krohn-Mueller-Whelan (2024 JoF) Pre-16:00 London Fix SELL",
        "FX_WMR_POST_FIX": "Krohn-Mueller-Whelan (2024 JoF) Post-16:00 London Fix BUY",
        "FX_WMR_MORNING_FADE": "Krohn-Mueller-Whelan (2024 JoF) Post-Fix Inventory Reversal",
    }
    for sym in ("EURUSD", "GBPUSD"):
        ctx = p14.build_asset_context(jobs_root, sym, cache_dir, specs["Swing"][sym])
        wmr_res = run_fx_wmr_strategies(ctx)
        for sid, src in wmr_sources.items():
            trs, fds = wmr_res[sid]
            mc = p14.mc_null_test(ctx, trs)
            package_row(sid, sym, src, True, trs, fds, mc)
        trs_nr, fds_nr = run_nr4_expansion(ctx)
        mc_nr = p14.mc_null_test(ctx, trs_nr)
        package_row(f"{sym}_NR4_EXPANSION", sym, "Toby Crabel (1990) / MQL5 CodeBase NR4 Breakout", True, trs_nr, fds_nr, mc_nr)

    # 3. XAUUSD (Crabel NR4 + Caminschi-Heaney 2014 JFM LBMA PM Drift, PROVISIONAL_XAU)
    xau_ctx = p14.build_asset_context(jobs_root, "XAUUSD", cache_dir, specs["Swing"]["XAUUSD"])
    trs_xnr, fds_xnr = run_nr4_expansion(xau_ctx)
    package_row("XAU_NR4_EXPANSION", "XAUUSD", "Toby Crabel (1990) / MQL5 CodeBase NR4 Breakout", False, trs_xnr, fds_xnr, p14.mc_null_test(xau_ctx, trs_xnr))
    trs_xlb, fds_xlb = run_xau_lbma_pm_drift(xau_ctx)
    package_row("XAU_LBMA_PM_DRIFT", "XAUUSD", "Caminschi-Heaney (2014 JFM) London/COMEX PM Drift", False, trs_xlb, fds_xlb, p14.mc_null_test(xau_ctx, trs_xlb))

    # Family-wise Benjamini-Hochberg FDR across all m = 14 hypotheses
    q_g = p14.benjamini_hochberg([r["mc_null"]["gross_p_value"] for r in rows])
    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] for r in rows])

    print(f"\n=== PASS 18: OPEN-SOURCE NON-USDJPY SCREEN (m={len(rows)} BH FDR, swap=0) ===", flush=True)
    for r, qg, qf in zip(rows, q_g, q_f):
        r["fdr_gross_q"] = qg
        r["fdr_ftmo_q"] = qf
        # Re-enforce FDR q <= 0.10 + Fade superiority + orthogonality for Tier 1 promotion
        corr_u = r["corr_usdjpy_core"]["union_corr"]
        if r["tier"] == "TIER_1_FTMO_READY":
            if qf > 0.10 or r.get("ftmo_net_R", 0) <= r["fade_ftmo_R"] or (corr_u is not None and abs(corr_u) >= 0.35):
                r["tier"] = "TIER_2_PERSONAL_VAULT"
        pf = r["mc_null"]["ftmo_net_p_value"]
        pg = r["mc_null"]["gross_p_value"]
        b_r = r["direction"]["BUY"]["ftmo_R"]
        s_r = r["direction"]["SELL"]["ftmo_R"]
        print(
            f"  {r['strategy']:22s} {r['asset']:6s} | n={r['n']:4d} | Stress={r.get('ftmo_net_R',0):+7.2f}R Base={r['ftmo_base_R']:+7.2f}R "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7) "
            f"| B/S={b_r:+.1f}/{s_r:+.1f} | Fade={r['fade_ftmo_R']:+6.1f} | p_f={pf:.3f}(q={qf:.3f}) p_g={pg:.3f} | rJPY={corr_u} | {r['tier']}",
            flush=True,
        )

    return {
        "pass": "Pass 18",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "spec_bindings": bindings,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "m_hypotheses": len(rows),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass18(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass18-result.json", res)
    print("\nPASS18_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
