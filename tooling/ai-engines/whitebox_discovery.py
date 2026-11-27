"""Prop-First White-Box Strategy Discovery Engine (Strict Cluster A Discovery -> Blind Cluster B OOS Validation, swap=0)."""

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import json
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles
from quant_core.holdout_guard import enforce_pre_holdout_ts

PROTOCOL = "9bbf69c83241d2b1084d21bd3a23f057414a5677"
SEED = 20261123
MC_DRAWS = 1000


def _fx_cost_params(asset: str) -> dict:
    if asset == "XAUUSD":
        return {"spread_proxy": 0.50, "slip_rt": 0.50}
    if asset.endswith("JPY"):
        return {"spread_proxy": None, "slip_rt": 0.009}  # 0.2/side base + 0.5 stress = 0.9 pip RT
    return {"spread_proxy": None, "slip_rt": 0.00009}


def replay_fx_intraday_fast(ctx: dict, entry_idx: int, side: int, entry_p: float, sl_p: float, max_exit_sec: int, *, slip_rt: float | None = None):
    """Unified M1 Bid/Ask intraday replay (swap=0) supporting both JPY crosses (GBPJPY) & majors/XAUUSD."""
    asset = ctx["asset"]
    times, quotes, spec = ctx["times"], ctx["quotes"], ctx["spec"]
    risk_p = side * (entry_p - sl_p)
    if risk_p <= 0 or entry_idx < 0:
        return None
    entry_ts = int(times[entry_idx])
    enforce_pre_holdout_ts((entry_ts, int(times[-1])), START, STOP, context=f"whitebox_discovery:{asset}")
    cap_sec = min(max_exit_sec, STOP - 60)
    hi_idx = int(times.searchsorted(cap_sec, side="right")) - 1
    if hi_idx < entry_idx:
        return None
    liq = quotes[entry_idx:hi_idx + 1, :4] if side == 1 else quotes[entry_idx:hi_idx + 1, 4:8]
    if side == 1:
        hits = np.flatnonzero(liq[:, 2] <= sl_p + 1e-10)
    else:
        hits = np.flatnonzero(liq[:, 1] >= sl_p - 1e-10)
    if len(hits):
        rel = int(hits[0])
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        reason = "SL_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        ex_p = float(liq[-1, 3])
        reason = "TIME_FLAT"

    ex_idx = entry_idx + rel
    ex_ts = int(times[ex_idx])
    enforce_pre_holdout_ts((entry_ts, ex_ts), START, STOP, context=f"whitebox_discovery:{asset}")

    cfg = _fx_cost_params(asset)
    s_rt = cfg["slip_rt"] if slip_rt is None else slip_rt
    # Separate strictly causal entry_conv_rate (lot/risk sizing) from exit_conv_rate (realized exit PnL)
    cs = float(spec["trade_contract_size"])
    d_entry = datetime.fromtimestamp(entry_ts, timezone.utc).date()
    d_ex = datetime.fromtimestamp(ex_ts, timezone.utc).date()
    usdjpy_map = ctx.get("usdjpy_close_map")

    def _prior_day_rate(rmap: dict | None, ref_d) -> float | None:
        if not rmap:
            return None
        for lag in range(1, 15):
            val = rmap.get(ref_d - timedelta(days=lag))
            if val is not None and float(val) > 0.0:
                return float(val)
        earlier = [k for k in rmap if k < ref_d]
        return float(rmap[max(earlier)]) if earlier else None

    if spec["currency_profit"] == "USD":
        entry_conv_rate = 1.0
        exit_conv_rate = 1.0
    elif spec["currency_profit"] == "JPY":
        if asset == "USDJPY":
            entry_conv_rate = 1.0 / entry_p
            exit_conv_rate = 1.0 / ex_p
        else:
            usdjpy_ent = _prior_day_rate(usdjpy_map, d_entry)
            entry_conv_rate = 1.0 / (usdjpy_ent if usdjpy_ent is not None else entry_p)
            usdjpy_ex = (
                (usdjpy_map.get(d_ex) or _prior_day_rate(usdjpy_map, d_ex) or usdjpy_ent)
                if usdjpy_map
                else ex_p
            )
            exit_conv_rate = 1.0 / (float(usdjpy_ex) if usdjpy_ex is not None else ex_p)
    elif spec["currency_profit"] in ("CAD", "CHF"):
        entry_conv_rate = 1.0 / entry_p
        exit_conv_rate = 1.0 / ex_p
    else:
        entry_conv_rate = 1.0
        exit_conv_rate = 1.0

    entry_scale = cs * entry_conv_rate
    exit_scale = cs * exit_conv_rate
    gross_usd = side * (ex_p - entry_p) * exit_scale
    comm_usd = 5.0 if asset != "XAUUSD" else 0.0
    exit_slip_usd = s_rt * exit_scale
    entry_slip_usd = s_rt * entry_scale
    ftmo_net = gross_usd - comm_usd - exit_slip_usd
    ftmo_risk = risk_p * entry_scale + comm_usd + entry_slip_usd
    if ftmo_risk <= 0:
        return None
    addon_p = 0.20 if asset == "XAUUSD" else (0.005 if asset.endswith("JPY") else 0.00005)
    addon_exit_usd = addon_p * exit_scale
    addon_entry_usd = addon_p * entry_scale
    base_net = ftmo_net + addon_exit_usd
    base_risk = max(1e-9, ftmo_risk - addon_entry_usd)
    return {
        "day": d_entry.isoformat(),
        "year": d_entry.year,
        "entry": entry_ts, "exit": ex_ts, "side": side, "reason": reason,
        "entry_conv_rate": float(entry_conv_rate),
        "exit_conv_rate": float(exit_conv_rate),
        "gross_usd": gross_usd, "ftmo_comm_slip": comm_usd + exit_slip_usd, "ftmo_swap": 0.0,
        "ftmo_net": ftmo_net, "ftmo_risk": ftmo_risk, "ftmo_R": ftmo_net / ftmo_risk,
        "base_R": base_net / base_risk,
        "ex_R_normal": base_net / base_risk, "ex_R_swapfree": base_net / base_risk,
    }


def _regime_allows(ctx: dict, d_idx: int, regime: str) -> tuple[bool, bool]:
    if regime == "NONE":
        return True, True
    if regime == "EMA50_TREND":
        ev = ctx["d1_ema50"][d_idx - 1]
        if not np.isfinite(ev):
            return False, False
        c = ctx["d1_c"][d_idx - 1]
        return c > ev, c < ev
    rng_prev = ctx["d1_h"][d_idx - 1] - ctx["d1_l"][d_idx - 1]
    atr_prev = ctx["d1_atr"][d_idx - 1]
    if not np.isfinite(atr_prev) or atr_prev <= 0:
        return False, False
    if regime == "VOL_HIGH":
        ok = rng_prev >= 1.10 * atr_prev
        return ok, ok
    if regime == "VOL_LOW":
        ok = rng_prev <= 0.80 * atr_prev
        return ok, ok
    raise ValueError(f"Unknown regime: {regime}")


# ==============================================================================
# 4 ORTHOGONAL PROP-FIRST WHITE-BOX ARCHETYPES (swap=0, zero-grid, hard-SL)
# ==============================================================================

def eval_open_expansion(ctx: dict, *, trig_atr: float, sl_atr: float, regime: str, reverse: bool = False) -> tuple[list[dict], list[dict]]:
    """Archetype 2 (WB_OPEN_EXPANSION) & Archetype 3 (WB_OVEREXT_FADE when reverse=True)."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades = [], []

    for idx in range(off, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        ok_b, ok_s = _regime_allows(ctx, idx, regime)
        if not (ok_b or ok_s):
            continue
        day = d1[idx]
        fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
        sub_t = times[fi:ei]
        open_0 = float(quotes[fi, 0])
        top = open_0 + trig_atr * a_val
        bot = open_0 - trig_atr * a_val
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
        side = -raw_side if reverse else raw_side
        e_idx = fi + i0 + j
        if not reverse:
            ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
            fep = float(quotes[e_idx, 4] if side == -1 else quotes[e_idx, 0])
        else:
            ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
            fep = max(top, float(quotes[e_idx, 4])) if raw_side == 1 else min(bot, float(quotes[e_idx, 0]))
        t_flat = dsec + 20 * 3600 + 55 * 60
        tr = replay_fx_intraday_fast(ctx, e_idx, side, ep, ep - side * sl_atr * a_val, t_flat)
        fd = replay_fx_intraday_fast(ctx, e_idx, -side, fep, fep + side * sl_atr * a_val, t_flat)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def eval_session_box(ctx: dict, *, box_start_h: int, box_end_h: int, max_box_atr: float, sl_atr: float) -> tuple[list[dict], list[dict]]:
    """Archetype 1 (WB_SESSION_BOX): Breakout of causal session box [box_start_h, box_end_h) UTC with box/ATR filter."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades = [], []
    for idx in range(off, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        day = d1[idx]
        fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
        sub_t = times[fi:ei]
        b0 = int(sub_t.searchsorted(dsec + box_start_h * 3600, side="left"))
        b1 = int(sub_t.searchsorted(dsec + box_end_h * 3600, side="left"))
        e_end = int(sub_t.searchsorted(dsec + 17 * 3600, side="left"))
        if b1 - b0 < 30 or e_end <= b1:
            continue
        box_q = quotes[fi + b0:fi + b1]
        hi_b = float(box_q[:, 1].max())
        lo_b = float(box_q[:, 2].min())
        width = hi_b - lo_b
        if width < 0.15 * a_val or width > max_box_atr * a_val:
            continue
        scan = quotes[fi + b1:fi + e_end]
        up = scan[:, 5] >= hi_b + 1e-10
        dn = scan[:, 2] <= lo_b - 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        e_idx = fi + b1 + j
        ep = max(hi_b, float(quotes[e_idx, 4])) if side == 1 else min(lo_b, float(quotes[e_idx, 0]))
        fep = float(quotes[e_idx, 4] if side == -1 else quotes[e_idx, 0])
        t_flat = dsec + 20 * 3600 + 55 * 60
        tr = replay_fx_intraday_fast(ctx, e_idx, side, ep, ep - side * sl_atr * a_val, t_flat)
        fd = replay_fx_intraday_fast(ctx, e_idx, -side, fep, fep + side * sl_atr * a_val, t_flat)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def eval_impulse_pullback(ctx: dict, *, imp_atr: float, retrace_frac: float, sl_atr: float) -> tuple[list[dict], list[dict]]:
    """Archetype 4 (WB_IMPULSE_PULLBACK): Early London impulse 07:00->10:00 UTC >= imp_atr -> causal pullback entry 10:00->16:00 UTC."""
    times, quotes = ctx["times"], ctx["quotes"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades, fades = [], []
    for idx in range(off, len(d1)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        day = d1[idx]
        fi, ei, dsec = day["fi"], day["ei"], day["day_sec"]
        sub_t = times[fi:ei]
        i0 = int(sub_t.searchsorted(dsec + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(dsec + 10 * 3600, side="left"))
        i2 = int(sub_t.searchsorted(dsec + 16 * 3600, side="left"))
        if i1 - i0 < 60 or i2 <= i1:
            continue
        p0 = float(quotes[fi + i0, 0])
        p1 = float(quotes[fi + i1 - 1, 3])
        move = p1 - p0
        if abs(move) < imp_atr * a_val:
            continue
        side = 1 if move > 0 else -1
        target = p1 - side * retrace_frac * abs(move)
        scan = quotes[fi + i1:fi + i2]
        # Limit pullback touch: BUY touches ask_low <= target; SELL touches bid_high >= target
        hits = np.flatnonzero(scan[:, 6] <= target + 1e-10) if side == 1 else np.flatnonzero(scan[:, 1] >= target - 1e-10)
        if not len(hits):
            continue
        e_idx = fi + i1 + int(hits[0])
        ep = min(target, float(quotes[e_idx, 4])) if side == 1 else max(target, float(quotes[e_idx, 0]))
        fep = float(quotes[e_idx, 4] if side == -1 else quotes[e_idx, 0])
        t_flat = dsec + 20 * 3600 + 55 * 60
        tr = replay_fx_intraday_fast(ctx, e_idx, side, ep, ep - side * sl_atr * a_val, t_flat)
        fd = replay_fx_intraday_fast(ctx, e_idx, -side, fep, fep + side * sl_atr * a_val, t_flat)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def eval_us500_grammar(times: np.ndarray, quotes: np.ndarray, sessions: list[dict], atr: np.ndarray, ema50: np.ndarray, spec_cfg: dict) -> tuple[list[dict], list[dict]]:
    """Run prop-first intraday grammar (Open Expansion / Fade / Impulse Pullback / Session Box) on Native Bid/Ask US500."""
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
            if reg == "EMA50_TREND":
                if not np.isfinite(ema50[idx - 1]):
                    continue
                ok_b = sessions[idx - 1]["c"] > ema50[idx - 1]
                ok_s = sessions[idx - 1]["c"] < ema50[idx - 1]
            elif reg == "VOL_HIGH":
                ok_b = ok_s = (sessions[idx - 1]["h"] - sessions[idx - 1]["l"]) >= 1.10 * a_val
            elif reg == "VOL_LOW":
                ok_b = ok_s = (sessions[idx - 1]["h"] - sessions[idx - 1]["l"]) <= 0.80 * a_val
            if not (ok_b or ok_s):
                continue
            a_i, b_i = int(offs.searchsorted(30)), int(offs.searchsorted(300))
            if b_i <= a_i:
                continue
            top = s["o"] + spec_cfg["trig_atr"] * a_val
            bot = s["o"] - spec_cfg["trig_atr"] * a_val
            scan = q[a_i:b_i]
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
            rel_i = a_i + j
            spr_i = max(0.0, float(q[rel_i, 4] - q[rel_i, 0]))
            if not rev:
                ep = max(top, float(q[rel_i, 4])) if side == 1 else min(bot, float(q[rel_i, 0]))
                fep = (ep - spr_i) if side == 1 else (ep + spr_i)
            else:
                ep = max(top, float(q[rel_i, 0])) if side == -1 else min(bot, float(q[rel_i, 4]))
                fep = (ep + spr_i) if side == -1 else (ep - spr_i)
        elif arch == "WB_IMPULSE_PULLBACK":
            i0, i1, i2 = int(offs.searchsorted(0)), int(offs.searchsorted(60)), int(offs.searchsorted(300))
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

        # Causal stop/limit fill via exact entry price adjustment
        q_orig = q[rel_i].copy()
        tr = p18.sim_us500_trade(times, quotes, s, rel_i, side, sl_pts, slip_side=0.75)
        fd = p18.sim_us500_trade(times, quotes, s, rel_i, -side, sl_pts, slip_side=0.75)
        if tr and fd:
            # Adjust gross/net for causal trigger price vs bar open (removes intraminute lookahead)
            def _rebase(rec, sdir, true_ep):
                open_ep = float(q_orig[4] if sdir == 1 else q_orig[0])
                diff = sdir * (open_ep - true_ep)
                if abs(diff) > 1e-12:
                    r_str = sl_pts + 1.50
                    r_bas = sl_pts + 0.50
                    rec["gross_usd"] += diff
                    rec["ftmo_net"] += diff
                    rec["ftmo_R"] = rec["ftmo_net"] / r_str
                    rec["base_R"] = (rec["gross_usd"] - 0.50) / r_bas
            _rebase(tr, side, ep)
            _rebase(fd, -side, fep)
            trades.append(tr)
            fades.append(fd)
    return trades, fades


def build_grammar_catalog() -> list[dict]:
    """Fixed, pre-registered Prop-First White-Box Grammar (30 clean specs per asset, swap=0, max 2-3 primitives)."""
    specs = []
    # Archetype 1: Session Box Breakout (6 specs)
    for bs, be, mb in ((0, 7, 0.70), (0, 7, 1.00), (2, 8, 0.75), (2, 8, 1.00), (7, 11, 0.75), (7, 11, 1.00)):
        specs.append({
            "id": f"WB_BOX_{bs:02d}{be:02d}_M{int(mb*100)}", "arch": "WB_SESSION_BOX",
            "box_start_h": bs, "box_end_h": be, "max_box_atr": mb, "sl_atr": 0.75,
        })
    # Archetype 2: Open Expansion (12 specs: 3 trig x 4 causal regimes)
    for ta in (0.65, 0.80, 1.00):
        for reg in ("NONE", "EMA50_TREND", "VOL_HIGH", "VOL_LOW"):
            specs.append({
                "id": f"WB_EXP_{int(ta*100)}_{reg}", "arch": "WB_OPEN_EXPANSION",
                "trig_atr": ta, "sl_atr": 0.75, "regime": reg,
            })
    # Archetype 3: Overextension Mean-Reversion Fade (6 specs: 3 trig x 2 regimes)
    for ta in (0.80, 1.00, 1.20):
        for reg in ("NONE", "VOL_HIGH"):
            specs.append({
                "id": f"WB_FADE_{int(ta*100)}_{reg}", "arch": "WB_OVEREXT_FADE",
                "trig_atr": ta, "sl_atr": 0.75, "regime": reg,
            })
    # Archetype 4: Early Impulse + Pullback Continuation (6 specs: 3 imp x 2 retrace)
    for imp in (0.35, 0.50, 0.65):
        for ret in (0.35, 0.50):
            specs.append({
                "id": f"WB_IMP_{int(imp*100)}_R{int(ret*100)}", "arch": "WB_IMPULSE_PULLBACK",
                "imp_atr": imp, "retrace_frac": ret, "sl_atr": 0.75,
            })
    return specs


def build_asset_ctx_extended(jobs_root: Path, asset: str, cache_dir: Path, spec: dict, usdjpy_close_map: dict) -> dict:
    ctx = p14.build_asset_context(jobs_root, asset, cache_dir, spec)
    ctx["d1_ema50"] = p14.ema(ctx["d1_c"], 50)
    ctx["usdjpy_close_map"] = usdjpy_close_map
    return ctx


def split_metrics(trades: list[dict], years: tuple[int, ...]) -> dict:
    sub = [t for t in trades if t["year"] in years]
    if not sub:
        return {"n": 0, "net_R": 0.0, "pf": 0.0, "dd_R": 0.0}
    pos = fsum(t["ftmo_R"] for t in sub if t["ftmo_R"] > 0)
    neg = -fsum(t["ftmo_R"] for t in sub if t["ftmo_R"] < 0)
    eq = np.cumsum([0.0] + [t["ftmo_R"] for t in sub])
    return {
        "n": len(sub),
        "net_R": round(pos - neg, 2),
        "pf": round(pos / neg, 3) if neg > 1e-9 else (9.99 if pos > 0 else 0.0),
        "dd_R": round(float((np.maximum.accumulate(eq) - eq).max()), 2),
    }


def run_whitebox_discovery(jobs_root: Path, cache_dir: Path, assets: list[str] | None = None) -> dict:
    """Run strict Cluster A Discovery -> Blind Cluster B OOS Validation across all cached assets."""
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    hot_m = json.loads((cache_dir / "manifest.json").read_text(encoding="utf-8"))
    avail_assets = list(hot_m["assets"].keys())
    target_assets = [a for a in (assets or avail_assets) if a in avail_assets]

    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    core_daily = p18.build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)

    # USDJPY D1 close map for exact JPY-cross USD conversion (GBPJPY)
    jpy_d_ts, _, _, _, jpy_d_c = p14.load_pre2018_d1(jobs_root, "USDJPY"), None, None, None, None
    import pass19_us500_supertrend_yencross as p19
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    grammar = build_grammar_catalog()
    all_evals = []

    for asset in target_assets:
        if asset == "US500":
            us_t, us_q, _ = hcache.load_asset("US500", cache_dir, verify_sha=True)
            us_s, us_atr = p18.build_us500_sessions(us_t, us_q)
            us_ema50 = p14.ema(np.array([s["c"] for s in us_s], dtype=np.float64), 50)
            for cfg in grammar:
                if cfg["arch"] == "WB_SESSION_BOX":
                    continue
                trs, fds = eval_us500_grammar(us_t, us_q, us_s, us_atr, us_ema50, cfg)
                all_evals.append((asset, True, cfg, trs, fds))
        else:
            ctx = build_asset_ctx_extended(jobs_root, asset, cache_dir, swing_specs[asset], usdjpy_close_map)
            nat_ask = bool(ctx["meta"]["native_Ask"])
            for cfg in grammar:
                arch = cfg["arch"]
                if arch == "WB_SESSION_BOX":
                    trs, fds = eval_session_box(ctx, box_start_h=cfg["box_start_h"], box_end_h=cfg["box_end_h"], max_box_atr=cfg["max_box_atr"], sl_atr=cfg["sl_atr"])
                elif arch == "WB_OPEN_EXPANSION":
                    trs, fds = eval_open_expansion(ctx, trig_atr=cfg["trig_atr"], sl_atr=cfg["sl_atr"], regime=cfg["regime"], reverse=False)
                elif arch == "WB_OVEREXT_FADE":
                    trs, fds = eval_open_expansion(ctx, trig_atr=cfg["trig_atr"], sl_atr=cfg["sl_atr"], regime=cfg["regime"], reverse=True)
                elif arch == "WB_IMPULSE_PULLBACK":
                    trs, fds = eval_impulse_pullback(ctx, imp_atr=cfg["imp_atr"], retrace_frac=cfg["retrace_frac"], sl_atr=cfg["sl_atr"])
                else:
                    continue
                all_evals.append((asset, nat_ask, cfg, trs, fds))

    m_total = len(all_evals)
    # STAGE 1: STRICT CLUSTER A DISCOVERY ONLY (2018-2020) — blind to 2021-2024!
    # Also compute p_sf on ALL m_total pairs so BH FDR penalizes the ENTIRE search space honestly!
    p_all_net = []
    stage1_records = []
    for asset, nat_ask, cfg, trs, fds in all_evals:
        mA = split_metrics(trs, clock.CLUSTERS["A"])
        passed_A = (mA["n"] >= 60 and mA["net_R"] > 0 and mA["pf"] >= 1.05)
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if (passed_A and trs) else {"gross_p": 1.0, "ftmo_net_p": 1.0}
        p_all_net.append(sf["ftmo_net_p"])
        stage1_records.append((asset, nat_ask, cfg, trs, fds, mA, passed_A, sf))

    q_all = p14.benjamini_hochberg(p_all_net)

    # STAGE 2: BLIND CLUSTER B OOS EVALUATION (2021-2024) + PROP-FIRST 3-TIER CLASSIFICATION
    survivors = []
    for (asset, nat_ask, cfg, trs, fds, mA, passed_A, sf), q_full in zip(stage1_records, q_all):
        if not passed_A:
            continue
        mB = split_metrics(trs, clock.CLUSTERS["B"])
        tot_R = round(fsum(t["ftmo_R"] for t in trs), 2)
        base_R = round(fsum(t.get("base_R", t["ftmo_R"]) for t in trs), 2)
        fade_R = round(fsum(f["ftmo_R"] for f in fds), 2)
        yr_map = {y: round(fsum(t["ftmo_R"] for t in trs if t["year"] == y), 2) for y in clock.YEAR}
        pos_yrs = sum(v > 0 for v in yr_map.values())
        eq = np.cumsum([0.0] + [t["ftmo_R"] for t in trs])
        dd_R = round(float((np.maximum.accumulate(eq) - eq).max()), 2)
        wins = sorted((t["ftmo_R"] for t in trs if t["ftmo_R"] > 0), reverse=True)
        top10 = round(fsum(wins[:10]), 2)
        corr = p18.daily_correlation(trs, core_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)

        tier1_core = (
            len(trs) >= 150
            and mB["net_R"] > 0
            and tot_R > top10
            and tot_R > fade_R
            and pos_yrs >= 5
            and dd_R <= 15.0
            and sf["ftmo_net_p"] < 0.05
            and q_full <= 0.10
        )
        if tier1_core:
            tier = "TIER_1_FTMO_READY" if nat_ask else "TIER_1_FTMO_READY_PROVISIONAL_XAU"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT" if nat_ask else "TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "arch": cfg["arch"], "asset": asset, "native_Ask": nat_ask,
            "n_total": len(trs), "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R, "top10_R": top10,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_usdjpy_core": corr, "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    tier_counts = dict(Counter(r["tier"] for r in survivors))
    tier_counts["STAGE1_FILTERED_OUT_ON_CLUSTER_A"] = m_total - len(survivors)

    print(f"\n=== WHITE-BOX PROP-FIRST DISCOVERY (m_total={m_total} across {len(target_assets)} assets, Cluster A -> Blind Cluster B) ===", flush=True)
    print(f"  Passed Cluster A Discovery Gate (n_A>=60, Net_A>0, PF_A>=1.05): {len(survivors)} / {m_total}", flush=True)
    print(f"  Tier Distribution: {tier_counts}", flush=True)
    for r in survivors[:20]:
        print(
            f"  {r['strategy']:24s} {r['asset']:6s} | n={r['n_total']:4d} | A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (Base={r['ftmo_base_R']:+6.2f}R, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q_all={r['fdr_q_full_space']:.3f} | rJPY={r['corr_usdjpy_core']} | {r['tier']}",
            flush=True,
        )

    return {
        "engine": "whitebox_prop_discovery_v1",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "assets": target_assets,
        "m_total_search_space": m_total,
        "cluster_a_survivors": len(survivors),
        "tier_counts": tier_counts,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "survivors": survivors,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--assets", nargs="*", default=None)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_whitebox_discovery(args.jobs, args.cache, args.assets)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "whitebox-discovery-result.json", res)
    print("\nWHITEBOX_DISCOVERY_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
