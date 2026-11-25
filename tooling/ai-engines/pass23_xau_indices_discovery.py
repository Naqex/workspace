"""Pass 23 Lane D: True Native M1 Bid/Ask Discovery on XAUUSD, US100, GER40 + Provisional XAU Re-Audit + Engine #4 Forensic."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from math import fsum
from pathlib import Path
import time
from zoneinfo import ZoneInfo

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
import pass22_gbpusd_volhigh_3engine as p22
import pass23_ftmo_lifecycle_sim as p23_life
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "5eb0506089d12ffbd047a8eab1871cc618f4850c"
SEED = 20261123
MC_DRAWS = 1000
BERLIN = ZoneInfo("Europe/Berlin")


def build_ger40_sessions(times: np.ndarray, quotes: np.ndarray) -> tuple[list[dict], np.ndarray]:
    """Build causal Xetra cash sessions (08:00..16:30 Europe/Berlin, exact CET/CEST DST, 510 mins) + Wilder ATR14."""
    sessions = []
    d_cur = date(2018, 1, 1)
    d_end = date(2024, 12, 31)
    while d_cur <= d_end:
        if d_cur.weekday() < 5:
            start_dt = datetime(d_cur.year, d_cur.month, d_cur.day, 8, 0, tzinfo=BERLIN)
            end_dt = datetime(d_cur.year, d_cur.month, d_cur.day, 16, 30, tzinfo=BERLIN)
            s_sec = int(start_dt.timestamp())
            e_sec = int(end_dt.timestamp())
            lo, hi = times.searchsorted([s_sec, e_sec + 60])
            if hi - lo >= 360:
                q = quotes[lo:hi]
                sessions.append({
                    "day": d_cur.isoformat(), "year": d_cur.year,
                    "start": s_sec, "end": e_sec, "lo": int(lo), "hi": int(hi),
                    "o": float(q[0, 0]), "h": float(q[:, 1].max()),
                    "l": float(q[:, 2].min()), "c": float(q[-1, 3]),
                })
        d_cur += timedelta(days=1)
    hs = np.array([s["h"] for s in sessions], dtype=np.float64)
    ls = np.array([s["l"] for s in sessions], dtype=np.float64)
    cs = np.array([s["c"] for s in sessions], dtype=np.float64)
    atr = p14.wilder_atr(hs, ls, cs, 14)
    return sessions, atr


def sim_index_trade(
    times: np.ndarray,
    quotes: np.ndarray,
    sess: dict,
    rel_entry: int,
    side: int,
    sl_pts: float,
    *,
    entry_price_override: float | None = None,
    slip_side_base: float = 1.0,
    slip_side_stress: float = 2.0,
    slip_side_double: float = 3.0,
) -> dict | None:
    """Exact Native Bid/Ask M1 intraday simulation for US100/GER40 (swap=0, $0 comm, conservative SL-first, causal stop/limit fill)."""
    lo, hi = sess["lo"], sess["hi"]
    q = quotes[lo:hi]
    if rel_entry < 0 or rel_entry >= len(q) - 1 or sl_pts <= 0:
        return None
    entry_p = float(entry_price_override) if entry_price_override is not None else float(q[rel_entry, 4] if side == 1 else q[rel_entry, 0])
    sl_p = entry_p - side * sl_pts
    liq = q[rel_entry:, :4] if side == 1 else q[rel_entry:, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)

    if len(sl_hits):
        k = int(sl_hits[0])
        op = float(liq[k, 0])
        gap = k > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        reason = "SL_GAP_OR_TOUCH"
        ex_rel = rel_entry + k
    else:
        ex_p = float(liq[-1, 0])
        reason = "HARD_FLAT"
        ex_rel = len(q) - 1

    e_ts = int(times[lo + rel_entry])
    x_ts = int(times[lo + ex_rel])
    assert START <= e_ts <= x_ts < STOP
    gross = side * (ex_p - entry_p)

    def r_at(s_side: float) -> tuple[float, float]:
        net = gross - 2.0 * s_side
        rsk = sl_pts + 2.0 * s_side
        return net, net / rsk

    net_b, r_b = r_at(slip_side_base)
    net_s, r_s = r_at(slip_side_stress)
    net_d, r_d = r_at(slip_side_double)
    # Track intraday M1 worst adverse excursion (in R under Stress) for floating DD & daily breach fidelity
    if side == 1:
        worst_px = float(liq[:ex_rel - rel_entry + 1, 2].min())
        mae_pts = max(0.0, entry_p - worst_px)
    else:
        worst_px = float(liq[:ex_rel - rel_entry + 1, 1].max())
        mae_pts = max(0.0, worst_px - entry_p)
    mae_r = min(1.5, (mae_pts + 2.0 * slip_side_stress) / (sl_pts + 2.0 * slip_side_stress))
    return {
        "day": sess["day"], "year": sess["year"], "side": side, "reason": reason,
        "entry": e_ts, "exit": x_ts,
        "gross_usd": gross, "ftmo_comm_slip": 2.0 * slip_side_stress, "ftmo_swap": 0.0,
        "ftmo_net": net_s, "ftmo_R": r_s,
        "base_R": r_b, "double_R": r_d,
        "mae_R": mae_r,
        "ex_R_normal": r_b, "ex_R_swapfree": r_b,
    }


def eval_index_grammar(
    times: np.ndarray,
    quotes: np.ndarray,
    sessions: list[dict],
    atr: np.ndarray,
    ema50: np.ndarray,
    spec_cfg: dict,
    *,
    entry_start_min: int = 30,
    entry_end_min: int = 300,
    imp_min: int = 60,
    vol_mult_override: float | None = None,
) -> tuple[list[dict], list[dict]]:
    """Run causal intraday grammar (Open Expansion / Fade / Impulse Pullback) on US100 or GER40 Native Bid/Ask."""
    arch = spec_cfg["arch"]
    trades, fades = [], []
    for idx in range(55, len(sessions)):
        s = sessions[idx]
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        lo, hi = s["lo"], s["hi"]
        offs = (times[lo:hi] - s["start"]) // 60
        q = quotes[lo:hi]
        sl_pts = spec_cfg["sl_atr"] * a_val

        if arch in ("WB_OPEN_EXPANSION", "WB_OVEREXT_FADE"):
            rev = (arch == "WB_OVEREXT_FADE")
            reg = spec_cfg["regime"]
            ok_b = ok_s = True
            prev_rng = sessions[idx - 1]["h"] - sessions[idx - 1]["l"]
            if reg == "EMA50_TREND":
                if not np.isfinite(ema50[idx - 1]):
                    continue
                ok_b = sessions[idx - 1]["c"] > ema50[idx - 1]
                ok_s = sessions[idx - 1]["c"] < ema50[idx - 1]
            elif reg == "VOL_HIGH":
                vm = 1.10 if vol_mult_override is None else vol_mult_override
                ok_b = ok_s = prev_rng >= vm * a_val
            elif reg == "VOL_LOW":
                vm = 0.80 if vol_mult_override is None else vol_mult_override
                ok_b = ok_s = prev_rng <= vm * a_val
            if not (ok_b or ok_s):
                continue
            a_i, b_i = int(offs.searchsorted(entry_start_min)), int(offs.searchsorted(entry_end_min))
            if b_i <= a_i:
                continue
            top = s["o"] + spec_cfg["trig_atr"] * a_val
            bot = s["o"] - spec_cfg["trig_atr"] * a_val
            scan = q[a_i:b_i]
            if not rev:
                # Stop breakout: BUY triggers when ask_high >= top, SELL triggers when bid_low <= bot
                up = (scan[:, 5] >= top - 1e-10) if ok_b else np.zeros(len(scan), dtype=bool)
                dn = (scan[:, 2] <= bot + 1e-10) if ok_s else np.zeros(len(scan), dtype=bool)
            else:
                # Limit overextension fade: SELL limit at top fills when bid_high >= top; BUY limit at bot fills when ask_low <= bot
                up = (scan[:, 1] >= top - 1e-10) if ok_b else np.zeros(len(scan), dtype=bool)
                dn = (scan[:, 6] <= bot + 1e-10) if ok_s else np.zeros(len(scan), dtype=bool)
            hits = np.flatnonzero(up | dn)
            if not len(hits):
                continue
            j = int(hits[0])
            if up[j] and dn[j]:
                continue
            raw_side = 1 if up[j] else -1
            side = -raw_side if rev else raw_side
            rel_i = a_i + j
            spr_i = max(0.0, float(q[rel_i, 4] - q[rel_i, 0]))
            if not rev:
                # Causal stop fill: NEVER better than trigger level
                ep = max(top, float(q[rel_i, 4])) if side == 1 else min(bot, float(q[rel_i, 0]))
                # Instantaneous opposite quote at the trigger touch for honest Fade null
                fep = (ep - spr_i) if side == 1 else (ep + spr_i)
            else:
                # Causal limit fade fill: SELL limit at >= top (bid), BUY limit at <= bot (ask)
                ep = max(top, float(q[rel_i, 0])) if side == -1 else min(bot, float(q[rel_i, 4]))
                fep = (ep + spr_i) if side == -1 else (ep - spr_i)
        elif arch == "WB_IMPULSE_PULLBACK":
            i0, i1, i2 = int(offs.searchsorted(0)), int(offs.searchsorted(imp_min)), int(offs.searchsorted(entry_end_min))
            if i1 <= i0 + 30 or i2 <= i1:
                continue
            p0, p1 = float(q[i0, 0]), float(q[i1 - 1, 3])
            move = p1 - p0
            if abs(move) < spec_cfg["imp_atr"] * a_val:
                continue
            side = 1 if move > 0 else -1
            target = p1 - side * spec_cfg["retrace_frac"] * abs(move)
            scan = q[i1:i2]
            hits = np.flatnonzero(scan[:, 6] <= target + 1e-10) if side == 1 else np.flatnonzero(scan[:, 1] >= target - 1e-10)
            if not len(hits):
                continue
            rel_i = i1 + int(hits[0])
            spr_i = max(0.0, float(q[rel_i, 4] - q[rel_i, 0]))
            ep = min(target, float(q[rel_i, 4])) if side == 1 else max(target, float(q[rel_i, 0]))
            fep = (ep - spr_i) if side == 1 else (ep + spr_i)
        else:
            continue

        tr = sim_index_trade(times, quotes, s, rel_i, side, sl_pts, entry_price_override=ep)
        fd = sim_index_trade(times, quotes, s, rel_i, -side, sl_pts, entry_price_override=fep)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def outlier_stress_trades(trades: list[dict]) -> dict:
    rs = [t["ftmo_R"] for t in trades]
    tot = fsum(rs)
    top_desc = sorted([x for x in rs if x > 0], reverse=True)
    no_covid = [t["ftmo_R"] for t in trades if not t["day"].startswith("2020-03")]
    no_shock22 = [t["ftmo_R"] for t in trades if not (t["day"].startswith("2022-09") or t["day"].startswith("2022-10"))]
    no_both = [
        t["ftmo_R"] for t in trades
        if not (t["day"].startswith("2020-03") or t["day"].startswith("2022-09") or t["day"].startswith("2022-10"))
    ]
    return {
        "total_R": round(tot, 2),
        "drop_top3_R": round(tot - fsum(top_desc[:3]), 2),
        "drop_top5_R": round(tot - fsum(top_desc[:5]), 2),
        "drop_top10_R": round(tot - fsum(top_desc[:10]), 2),
        "excl_covid_2020_03_R": round(fsum(no_covid), 2),
        "excl_shock_2022_0910_R": round(fsum(no_shock22), 2),
        "excl_both_crises_R": round(fsum(no_both), 2),
        "excl_both_n": len(no_both),
    }


def build_3engine_daily_series(jobs_root: Path, cache_dir: Path, specs: dict) -> dict[str, float]:
    """Daily combined R/USD series of the frozen 3-Engine Core (USDJPY Tokyo + USDJPY EXP080 + GBPUSD VOL_HIGH)."""
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, specs["Swing"]["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    ref_trades, _ = portfolio.frozen_usdjpy(jobs_root)
    exp_usd = p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    gbp_vh, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)
    daily = defaultdict(float)
    for d, (row, *_rest) in ref_trades.items():
        daily[d] += float(row["net_R"]) * 0.30
    for row, *_rest in exp_usd:
        daily[row["day"]] += float(row["net_R"]) * 0.45
    for row, *_rest in gbp_vh:
        daily[row["day"]] += float(row["net_R"]) * 0.75
    return dict(daily)


def reaudit_xau_provisional_leads(xau_ctx: dict, core3_daily: dict[str, float]) -> dict:
    """Re-audit Pass 14-16 provisional XAUUSD leads on TRUE Native M1 Bid/Ask (no spread proxy!)."""
    assert xau_ctx["meta"]["native_Ask"] is True, "XAUUSD must be upgraded to native_Ask=True before re-audit!"
    out = {}

    # 1. XAUUSD EXP_DAILY_OPEN_120 (intraday swap=0, Pass 15/16) across 3 cost tiers ($0.20, $0.50, $1.00 slip RT)
    exp_tiers = {}
    for tname, s_rt in (("Base_slip020", 0.20), ("Stress_slip050", 0.50), ("Double_slip100", 1.00)):
        # Evaluate using native Bid/Ask with exact slip_rt override
        times, quotes = xau_ctx["times"], xau_ctx["quotes"]
        d1, off, atr = xau_ctx["full_d1"], xau_ctx["d1_offset"], xau_ctx["d1_atr"]
        trs, fds = [], []
        for idx in range(off, len(d1)):
            a_val = float(atr[idx - 1])
            if not np.isfinite(a_val) or a_val <= 0:
                continue
            day = d1[idx]
            fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
            sub_t = times[fi:ei]
            open_0 = float(quotes[fi, 0])
            top, bot = open_0 + 1.20 * a_val, open_0 - 1.20 * a_val
            i0 = int(sub_t.searchsorted(dsec + 7 * 3600, side="left"))
            i1 = int(sub_t.searchsorted(dsec + 17 * 3600, side="left"))
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
            e_idx = fi + i0 + j
            ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
            fep = float(quotes[e_idx, 4] if side == -1 else quotes[e_idx, 0])
            t_flat = dsec + 20 * 3600 + 55 * 60
            tr = wbd.replay_fx_intraday_fast(xau_ctx, e_idx, side, ep, ep - side * 0.75 * a_val, t_flat, slip_rt=s_rt)
            fd = wbd.replay_fx_intraday_fast(xau_ctx, e_idx, -side, fep, fep + side * 0.75 * a_val, t_flat, slip_rt=s_rt)
            if tr and fd:
                trs.append(tr)
                fds.append(fd)
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        mB = wbd.split_metrics(trs, clock.CLUSTERS["B"])
        yr = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if trs else {"ftmo_net_p": 1.0}
        exp_tiers[tname] = {
            "n": len(trs), "net_R": round(fsum(t["ftmo_R"] for t in trs), 2),
            "fade_R": round(fsum(f["ftmo_R"] for f in fds), 2),
            "A": mA["net_R"], "B": mB["net_R"],
            "pos_years": sum(v > 0 for v in yr.values()), "years_R": yr,
            "p_sf": round(sf["ftmo_net_p"], 4),
            "outlier": outlier_stress_trades(trs),
            "corr_3e": p18.daily_correlation(trs, core3_daily)["union_corr"],
        }
    out["XAU_EXP_DAILY_OPEN_120_NATIVE_ASK"] = exp_tiers

    # 2. NEN006 & IND026 (Pass 14 D1 leads) re-run on TRUE Native Bid/Ask
    for sname, fn in (("NEN006_INSIDE_BAR_EMA200_D1", p14.STRATEGIES["NEN006"]), ("IND026_ICHIMOKU_CHIKOU_D1", p14.STRATEGIES["IND026"])):
        trs = fn(xau_ctx)
        # Ensure day field exists for outlier/corr
        for t in trs:
            t["day"] = datetime.fromtimestamp(t["entry"], timezone.utc).date().isoformat()
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        mB = wbd.split_metrics(trs, clock.CLUSTERS["B"])
        tot_ftmo = round(fsum(t["ftmo_R"] for t in trs), 2)
        tot_swap = round(fsum(t["ftmo_swap"] for t in trs), 2)
        # Honest Exness Swap-Free using REAL Native Bid/Ask (remove artificial spread_adj credit!)
        ex_sf_r = []
        for t in trs:
            net_noswap = t["gross_usd"] - 7.0 - 30.0  # $7 comm + $0.30/oz slip * 100 oz
            rsk = max(1e-9, t["ftmo_risk"] - t["ftmo_comm_slip"] + 37.0)
            ex_sf_r.append(net_noswap / rsk)
        yr = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        out[sname] = {
            "native_Ask": True,
            "n": len(trs), "ftmo_net_R": tot_ftmo, "ftmo_swap_usd_per_lot": tot_swap,
            "A": mA["net_R"], "B": mB["net_R"],
            "pos_years": sum(v > 0 for v in yr.values()), "years_R": yr,
            "dd_R": wbd.split_metrics(trs, clock.YEAR)["dd_R"],
            "honest_exness_swapfree_R": round(fsum(ex_sf_r), 2),
            "outlier": outlier_stress_trades(trs),
            "corr_3e": p18.daily_correlation(trs, core3_daily)["union_corr"],
        }
    return out


def forensic_candidate(asset: str, cfg: dict, data_bundle: dict, core3_daily: dict[str, float]) -> dict:
    """Deep forensic check for any discovered Engine #4 candidate (3 cost tiers, Dual 2D surfaces, Outlier Stress)."""
    arch = cfg["arch"]
    res = {"asset": asset, "strategy": cfg["id"], "arch": arch}

    if asset == "XAUUSD":
        ctx = data_bundle["XAUUSD"]
        def run_one(ta, sa, reg, slip_rt=0.50):
            times, quotes = ctx["times"], ctx["quotes"]
            d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
            trs, fds = [], []
            rev = (arch == "WB_OVEREXT_FADE")
            for idx in range(off, len(d1)):
                a_val = float(atr[idx - 1])
                if not np.isfinite(a_val) or a_val <= 0:
                    continue
                ok_b, ok_s = wbd._regime_allows(ctx, idx, reg)
                if not (ok_b or ok_s):
                    continue
                day = d1[idx]
                fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
                sub_t = times[fi:ei]
                open_0 = float(quotes[fi, 0])
                top, bot = open_0 + ta * a_val, open_0 - ta * a_val
                i0 = int(sub_t.searchsorted(dsec + 7 * 3600, side="left"))
                i1 = int(sub_t.searchsorted(dsec + 17 * 3600, side="left"))
                if i1 <= i0:
                    continue
                scan = quotes[fi + i0:fi + i1]
                up = (scan[:, 5] >= top - 1e-10) if ok_b else np.zeros(len(scan), dtype=bool)
                dn = (scan[:, 2] <= bot + 1e-10) if ok_s else np.zeros(len(scan), dtype=bool)
                hits = np.flatnonzero(up | dn)
                if not len(hits):
                    continue
                j = int(hits[0])
                if up[j] and dn[j]:
                    continue
                raw_side = 1 if up[j] else -1
                side = -raw_side if rev else raw_side
                e_idx = fi + i0 + j
                ep = (max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))) if not rev else float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
                fep = float(quotes[e_idx, 4] if side == -1 else quotes[e_idx, 0]) if not rev else (max(top, float(quotes[e_idx, 4])) if raw_side == 1 else min(bot, float(quotes[e_idx, 0])))
                t_flat = dsec + 20 * 3600 + 55 * 60
                tr = wbd.replay_fx_intraday_fast(ctx, e_idx, side, ep, ep - side * sa * a_val, t_flat, slip_rt=slip_rt)
                fd = wbd.replay_fx_intraday_fast(ctx, e_idx, -side, fep, fep + side * sa * a_val, t_flat, slip_rt=slip_rt)
                if tr and fd:
                    trs.append(tr)
                    fds.append(fd)
            return trs, fds

        if arch in ("WB_OPEN_EXPANSION", "WB_OVEREXT_FADE"):
            t_base, _ = run_one(cfg["trig_atr"], cfg["sl_atr"], cfg["regime"], 0.20)
            t_str, f_str = run_one(cfg["trig_atr"], cfg["sl_atr"], cfg["regime"], 0.50)
            t_dbl, _ = run_one(cfg["trig_atr"], cfg["sl_atr"], cfg["regime"], 1.00)
            res["cost_tiers"] = {
                "Base_020": round(fsum(t["ftmo_R"] for t in t_base), 2),
                "Stress_050": round(fsum(t["ftmo_R"] for t in t_str), 2),
                "Double_100": round(fsum(t["ftmo_R"] for t in t_dbl), 2),
            }
            res["outlier"] = outlier_stress_trades(t_str)
            res["direction"] = p18.direction_breakdown(t_str)
            res["corr_3e"] = p18.daily_correlation(t_str, core3_daily)["union_corr"]
            # Dual 2D Surface 1: trig x sl_atr (9 cells)
            s_ts = {}
            for ta in (round(cfg["trig_atr"] - 0.15, 2), cfg["trig_atr"], round(cfg["trig_atr"] + 0.15, 2)):
                for sa in (0.55, 0.75, 0.95):
                    tt, _ = run_one(ta, sa, cfg["regime"], 0.50)
                    s_ts[f"t{ta:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
            res["surface_1_trig_sl"] = {"both_pos": sum(1 for v in s_ts.values() if v["A"] > 0 and v["B"] > 0), "total": len(s_ts), "cells": s_ts}
            res["trades_stress"] = t_str
        else:
            # Session Box or Impulse Pullback
            if arch == "WB_SESSION_BOX":
                t_str, _ = wbd.eval_session_box(ctx, box_start_h=cfg["box_start_h"], box_end_h=cfg["box_end_h"], max_box_atr=cfg["max_box_atr"], sl_atr=cfg["sl_atr"])
            else:
                t_str, _ = wbd.eval_impulse_pullback(ctx, imp_atr=cfg["imp_atr"], retrace_frac=cfg["retrace_frac"], sl_atr=cfg["sl_atr"])
            res["cost_tiers"] = {
                "Base": round(fsum(t.get("base_R", t["ftmo_R"]) for t in t_str), 2),
                "Stress": round(fsum(t["ftmo_R"] for t in t_str), 2),
            }
            res["outlier"] = outlier_stress_trades(t_str)
            res["direction"] = p18.direction_breakdown(t_str)
            res["corr_3e"] = p18.daily_correlation(t_str, core3_daily)["union_corr"]
            res["trades_stress"] = t_str
        return res

    # Index assets (US100 / GER40)
    times, quotes, sess, atr, ema50, e_end = data_bundle[asset]
    t_str, _ = eval_index_grammar(times, quotes, sess, atr, ema50, cfg, entry_end_min=e_end)
    res["cost_tiers"] = {
        "Base_1pt": round(fsum(t["base_R"] for t in t_str), 2),
        "Stress_2pt": round(fsum(t["ftmo_R"] for t in t_str), 2),
        "Double_3pt": round(fsum(t["double_R"] for t in t_str), 2),
    }
    res["outlier"] = outlier_stress_trades(t_str)
    res["direction"] = p18.direction_breakdown(t_str)
    res["corr_3e"] = p18.daily_correlation(t_str, core3_daily)["union_corr"]

    # Dual 2D Stability Surfaces
    if arch in ("WB_OPEN_EXPANSION", "WB_OVEREXT_FADE"):
        s1, s2 = {}, {}
        for ta in (round(cfg["trig_atr"] - 0.15, 2), cfg["trig_atr"], round(cfg["trig_atr"] + 0.15, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_index_grammar(times, quotes, sess, atr, ema50, {**cfg, "trig_atr": ta, "sl_atr": sa}, entry_end_min=e_end)
                s1[f"t{ta:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
            for vm in ((0.95, 1.10, 1.25) if cfg["regime"] == "VOL_HIGH" else ((0.65, 0.80, 0.95) if cfg["regime"] == "VOL_LOW" else (0.0,))):
                tt, _ = eval_index_grammar(times, quotes, sess, atr, ema50, {**cfg, "trig_atr": ta}, entry_end_min=e_end, vol_mult_override=(vm if vm > 0 else None))
                s2[f"t{ta:.2f}_f{vm:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
        res["surface_1_trig_sl"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
        res["surface_2_trig_flt"] = {"both_pos": sum(1 for v in s2.values() if v["A"] > 0 and v["B"] > 0), "total": len(s2), "cells": s2}
    elif arch == "WB_IMPULSE_PULLBACK":
        s1, s2 = {}, {}
        for imp in (round(cfg["imp_atr"] - 0.10, 2), cfg["imp_atr"], round(cfg["imp_atr"] + 0.10, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_index_grammar(times, quotes, sess, atr, ema50, {**cfg, "imp_atr": imp, "sl_atr": sa}, entry_end_min=e_end)
                s1[f"i{imp:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
            for ret in (0.25, 0.35, 0.50, 0.60):
                tt, _ = eval_index_grammar(times, quotes, sess, atr, ema50, {**cfg, "imp_atr": imp, "retrace_frac": ret}, entry_end_min=e_end)
                s2[f"i{imp:.2f}_r{ret:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
        res["surface_1_imp_sl"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
        res["surface_2_imp_ret"] = {"both_pos": sum(1 for v in s2.values() if v["A"] > 0 and v["B"] > 0), "total": len(s2), "cells": s2}
    res["trades_stress"] = t_str
    return res


def simulate_4engine_upgrade(jobs_root: Path, cache_dir: Path, specs: dict, eng4_trades: list[dict], eng4_label: str) -> dict:
    """Test adding Engine #4 (fixed-risk 0.50% & 0.75%) onto frozen 3-Engine Core in Nhịp 3 FTMO 2-Step Lifecycle."""
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, specs["Swing"]["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
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
    core_075 = {s: 0.0075 * w for s, w in inv2.items()}
    p3_bal = {**core_075, p22.GBPUSD_VH: 0.0075}

    m3, ledger3 = portfolio.replay(ext_days, tapes_05, p3_bal, 10000, specs_ext["Swing"])
    d_list, nets3, dds3, flags3 = p23_life.build_full_daily_series(ext_days, ledger3, 10000.0)

    e4_by_day = defaultdict(list)
    for t in eng4_trades:
        e4_by_day[t["day"]].append(t)

    upgrades = {}
    for r_pct in (0.0050, 0.0075, 0.0100):
        r_usd = 10000.0 * r_pct
        nets4 = nets3.copy()
        dds4 = dds3.copy()
        flags4 = flags3.copy()
        for i, d in enumerate(d_list):
            if d in e4_by_day:
                day_net = fsum(t["ftmo_R"] * r_usd for t in e4_by_day[d])
                day_mae = fsum(t.get("mae_R", max(1.0, -t["ftmo_R"])) * r_usd for t in e4_by_day[d])
                nets4[i] += day_net
                # Conservative additive intraday worst-case stacking
                dds4[i] += day_mae
                flags4[i] = 1
        eq = np.cumsum(np.insert(nets4, 0, 10000.0))
        eq_lows = eq[:-1] - dds4
        peak_so_far = np.maximum.accumulate(eq[:-1])
        peak_dd_pct = float(np.max((peak_so_far - eq_lows) / 10000.0) * 100.0)
        max_daily_pct = float(np.max(dds4) / 10000.0 * 100.0)
        ann_pct = float((eq[-1] - 10000.0) / 10000.0 / 7.0 * 100.0)
        ann_A = float(fsum(nets4[i] for i, d in enumerate(d_list) if d < "2021-01-01") / 10000.0 / 3.0 * 100.0)
        ann_B = float(fsum(nets4[i] for i, d in enumerate(d_list) if d >= "2021-01-01") / 10000.0 / 4.0 * 100.0)
        calmar = round(ann_pct / peak_dd_pct, 2) if peak_dd_pct > 1e-9 else 0.0
        roll = p23_life.rolling_historical_windows(d_list, nets4, dds4, flags4, 10000.0)
        boot = p23_life.block_bootstrap_lifecycle(nets4, dds4, flags4, 10000.0, 168.0)
        key = f"PORT4E_3E_PLUS_{eng4_label}_R{int(r_pct*10000)}"
        upgrades[key] = {
            "ann_pct": round(ann_pct, 2), "ann_A": round(ann_A, 2), "ann_B": round(ann_B, 2),
            "peak_dd_pct": round(peak_dd_pct, 2), "daily_loss_pct": round(max_daily_pct, 2),
            "calmar": calmar, "rolling_windows": roll, "bootstrap_2000": boot,
        }
        h12, h24 = boot["horizons"]["12m"], boot["horizons"]["24m"]
        cf = boot["cashflow_24m_with_retries"]
        print(
            f"  4E UPGRADE {key:38s} | ann={ann_pct:+5.2f}% (A={ann_A:+5.2f}%, B={ann_B:+5.2f}%) "
            f"| peakDD={peak_dd_pct:5.2f}% dly={max_daily_pct:4.2f}% cal={calmar:4.2f} "
            f"| Boot12={h12['two_step_pass_pct']:4.1f}% Boot24={h24['two_step_pass_pct']:4.1f}% Br24={h24['breach_total_pct']:4.1f}% "
            f"| 24mCF med=${cf['median_net_usd']:+6.0f} (P>0={cf['net_profitable_pct']:4.1f}%)",
            flush=True,
        )
    return upgrades


def run_pass23_lane_d(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, bindings = profiles()
    core_jpy = p18.build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)
    core3_daily = build_3engine_daily_series(jobs_root, cache_dir, specs)

    import pass19_us500_supertrend_yencross as p19
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    # Load all 3 newly sealed Native M1 Bid/Ask assets
    xau_ctx = wbd.build_asset_ctx_extended(jobs_root, "XAUUSD", cache_dir, specs["Swing"]["XAUUSD"], usdjpy_close_map)
    assert xau_ctx["meta"]["native_Ask"] is True, "XAUUSD still missing native_Ask!"

    u100_t, u100_q, u100_m = hcache.load_asset("US100", cache_dir, verify_sha=True)
    u100_s, u100_atr = p18.build_us500_sessions(u100_t, u100_q)
    u100_ema50 = p14.ema(np.array([s["c"] for s in u100_s], dtype=np.float64), 50)

    g40_t, g40_q, g40_m = hcache.load_asset("GER40", cache_dir, verify_sha=True)
    g40_s, g40_atr = build_ger40_sessions(g40_t, g40_q)
    g40_ema50 = p14.ema(np.array([s["c"] for s in g40_s], dtype=np.float64), 50)

    data_bundle = {
        "XAUUSD": xau_ctx,
        "US100": (u100_t, u100_q, u100_s, u100_atr, u100_ema50, 300),
        "GER40": (g40_t, g40_q, g40_s, g40_atr, g40_ema50, 420),
    }

    # --- PART 1: TRUE NATIVE BID/ASK RE-AUDIT OF PASS 14-16 XAUUSD PROVISIONAL LEADS ---
    print("\n=== PASS 23 LANE D1: TRUE NATIVE BID/ASK RE-AUDIT OF XAUUSD PROVISIONAL LEADS ===", flush=True)
    xau_reaudit = reaudit_xau_provisional_leads(xau_ctx, core3_daily)
    for k, v in xau_reaudit.items():
        print(f"  {k}: {v}", flush=True)

    # --- PART 2: STRICT CLUSTER A -> BLIND CLUSTER B WHITE-BOX DISCOVERY (m_total = 78) ---
    grammar = wbd.build_grammar_catalog()
    all_evals = []
    # XAUUSD (30 specs)
    for cfg in grammar:
        arch = cfg["arch"]
        if arch == "WB_SESSION_BOX":
            trs, fds = wbd.eval_session_box(xau_ctx, box_start_h=cfg["box_start_h"], box_end_h=cfg["box_end_h"], max_box_atr=cfg["max_box_atr"], sl_atr=cfg["sl_atr"])
        elif arch == "WB_OPEN_EXPANSION":
            trs, fds = wbd.eval_open_expansion(xau_ctx, trig_atr=cfg["trig_atr"], sl_atr=cfg["sl_atr"], regime=cfg["regime"], reverse=False)
        elif arch == "WB_OVEREXT_FADE":
            trs, fds = wbd.eval_open_expansion(xau_ctx, trig_atr=cfg["trig_atr"], sl_atr=cfg["sl_atr"], regime=cfg["regime"], reverse=True)
        else:
            trs, fds = wbd.eval_impulse_pullback(xau_ctx, imp_atr=cfg["imp_atr"], retrace_frac=cfg["retrace_frac"], sl_atr=cfg["sl_atr"])
        all_evals.append(("XAUUSD", False, cfg, trs, fds))

    # US100 (24 specs) & GER40 (24 specs)
    for sym, (ts, qs, sess, atr, ema50, e_end) in (("US100", data_bundle["US100"]), ("GER40", data_bundle["GER40"])):
        for cfg in grammar:
            if cfg["arch"] == "WB_SESSION_BOX":
                continue
            trs, fds = eval_index_grammar(ts, qs, sess, atr, ema50, cfg, entry_end_min=e_end)
            all_evals.append((sym, True, cfg, trs, fds))

    m_total = len(all_evals)
    p_all, stage1 = [], []
    for asset, provisional_spec, cfg, trs, fds in all_evals:
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        passed_A = (mA["n"] >= 60 and mA["net_R"] > 0 and mA["pf"] >= 1.05)
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if (passed_A and trs) else {"gross_p": 1.0, "ftmo_net_p": 1.0}
        p_all.append(sf["ftmo_net_p"])
        stage1.append((asset, provisional_spec, cfg, trs, fds, mA, passed_A, sf))

    q_all = p14.benjamini_hochberg(p_all)
    survivors = []
    for (asset, prov_spec, cfg, trs, fds, mA, passed_A, sf), q_full in zip(stage1, q_all):
        if not passed_A:
            continue
        mB = wbd.split_metrics(trs, clock.CLUSTERS["B"])
        tot_R = round(fsum(t["ftmo_R"] for t in trs), 2)
        base_R = round(fsum(t.get("base_R", t["ftmo_R"]) for t in trs), 2)
        fade_R = round(fsum(f["ftmo_R"] for f in fds), 2)
        yr_map = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        pos_yrs = sum(v > 0 for v in yr_map.values())
        eq = np.cumsum([0.0] + [t["ftmo_R"] for t in trs])
        dd_R = round(float((np.maximum.accumulate(eq) - eq).max()), 2)
        wins = sorted((t["ftmo_R"] for t in trs if t["ftmo_R"] > 0), reverse=True)
        top10 = round(fsum(wins[:10]), 2)
        corr_jpy = p18.daily_correlation(trs, core_jpy)["union_corr"]
        corr_3e = p18.daily_correlation(trs, core3_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)

        tier1_core = (
            len(trs) >= 150 and mB["net_R"] > 0 and tot_R > top10 and tot_R > fade_R
            and pos_yrs >= 5 and dd_R <= 15.0 and sf["ftmo_net_p"] < 0.05 and q_full <= 0.10
        )
        if tier1_core:
            tier = "TIER_1_FTMO_READY_PROVISIONAL_SPEC_UNMEASURED_DEMO" if prov_spec else "TIER_1_FTMO_READY"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT_PROVISIONAL_SPEC" if prov_spec else "TIER_2_PERSONAL_VAULT"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "arch": cfg["arch"], "asset": asset,
            "native_Ask": True, "provisional_spec_unmeasured_demo": prov_spec,
            "n_total": len(trs), "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R, "top10_R": top10,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_usdjpy_core": corr_jpy, "corr_3engine_core": corr_3e,
            "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    tier_counts = dict(Counter(r["tier"] for r in survivors))
    tier_counts["STAGE1_FILTERED_OUT_ON_CLUSTER_A"] = m_total - len(survivors)

    print(f"\n=== PASS 23 LANE D2: WHITE-BOX ENGINE #4 DISCOVERY (m_total={m_total} across XAUUSD/US100/GER40, Native Bid/Ask) ===", flush=True)
    print(f"  Passed Cluster A Gate: {len(survivors)} / {m_total} | Tiers: {tier_counts}", flush=True)
    for r in survivors[:15]:
        print(
            f"  {r['strategy']:24s} {r['asset']:6s} | n={r['n_total']:4d} | A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (Base={r['ftmo_base_R']:+6.2f}R, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q_all={r['fdr_q_full_space']:.3f} | r3E={r['corr_3engine_core']} | {r['tier']}",
            flush=True,
        )

    # --- PART 3: AUTOMATIC FORENSIC + 4-ENGINE PORTFOLIO UPGRADE CHECK FOR TOP SURVIVORS ---
    forensic_reports = []
    upgrade_4e = {}
    targets = [r for r in survivors if "TIER_1" in r["tier"]]
    if not targets:
        targets = [r for r in survivors if "TIER_2" in r["tier"]][:2]

    if targets:
        print(f"\n=== PASS 23 LANE D3: DEEP FORENSIC & 4-ENGINE UPGRADE CHECK ({len(targets)} candidate(s)) ===", flush=True)
        for cand in targets[:3]:
            frep = forensic_candidate(cand["asset"], cand["spec"], data_bundle, core3_daily)
            tr_stress = frep.pop("trades_stress")
            forensic_reports.append(frep)
            print(
                f"  FORENSIC {cand['asset']} {cand['strategy']} | tiers={frep['cost_tiers']} "
                f"| outlier={frep['outlier']} | r3E={frep['corr_3e']} "
                f"| s1={frep.get('surface_1_trig_sl', frep.get('surface_1_imp_sl', {})).get('both_pos')}/{frep.get('surface_1_trig_sl', frep.get('surface_1_imp_sl', {})).get('total')}",
                flush=True,
            )
            if "TIER_1" in cand["tier"] or (frep["outlier"]["excl_both_crises_R"] > 0 and frep["outlier"]["drop_top3_R"] > 0):
                lbl = f"{cand['asset']}_{cand['strategy']}"
                upgrade_4e[lbl] = simulate_4engine_upgrade(jobs_root, cache_dir, specs, tr_stress, lbl)

    return {
        "pass": "Pass 23 Lane D (Native Ask XAUUSD + US100 + GER40 Discovery & Engine #4 Forensic)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "m_total_search_space": m_total,
        "cluster_a_survivors": len(survivors),
        "tier_counts": tier_counts,
        "xau_provisional_reaudit": xau_reaudit,
        "survivors": survivors,
        "forensic_reports": forensic_reports,
        "upgrade_4e_lifecycle": upgrade_4e,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass23_lane_d(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass23-lane-d-result.json", res)
    print("\nPASS23_LANE_D_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
