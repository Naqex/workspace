"""Pass 24: Multi-Timeframe (M15/H1/D1) 6 New Structural Families Discovery (m_total=128) & Dual-Firm 2-Layer Evaluation."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
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
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles
from quant_core.holdout_guard import enforce_pre_holdout_ts

PROTOCOL = "52a53cb785a63998a281aab06cf449cd061f140a"
SEED = 20261123
MC_DRAWS = 1000


def asset_cost_tiers(asset: str) -> dict:
    """Exact 3-tier round-turn slippage + commission schedule on top of Native M1 Bid/Ask spreads."""
    if asset in ("USDJPY", "GBPJPY", "EURJPY"):
        return {"comm_usd": 5.0, "base": 0.004, "stress": 0.009, "double": 0.014, "is_index": False, "is_crypto": False}
    if asset in ("GBPUSD", "EURUSD", "AUDUSD", "USDCAD", "USDCHF"):
        return {"comm_usd": 5.0, "base": 0.00004, "stress": 0.00009, "double": 0.00014, "is_index": False, "is_crypto": False}
    if asset == "XAUUSD":
        return {"comm_usd": 0.0, "base": 0.20, "stress": 0.50, "double": 1.00, "is_index": False, "is_crypto": False}
    if asset == "US500":
        return {"comm_usd": 0.0, "base": 0.50, "stress": 1.50, "double": 2.50, "is_index": True, "is_crypto": False}
    if asset in ("US100", "GER40"):
        return {"comm_usd": 0.0, "base": 2.00, "stress": 4.00, "double": 6.00, "is_index": True, "is_crypto": False}
    if asset == "BTCUSD":
        # Conservative % RT slippage on top of real M1 Bid/Ask spread (0.05% Base, 0.15% Stress, 0.30% Double)
        return {"comm_usd": 0.0, "base_pct": 0.0005, "stress_pct": 0.0015, "double_pct": 0.0030, "is_index": False, "is_crypto": True}
    raise ValueError(f"Unsupported asset: {asset}")


def replay_causal_intraday(
    asset: str,
    times: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    flat_idx: int,
    side: int,
    entry_p: float,
    sl_p: float,
    *,
    tp_p: float | None = None,
    spec: dict | None = None,
    usdjpy_close_map: dict | None = None,
) -> dict | None:
    """Unified zero-lookahead M1 Bid/Ask intraday trade replay (swap=0, conservative SL-first on entry bar)."""
    risk_p = side * (entry_p - sl_p)
    if risk_p <= 0 or entry_idx < 0 or flat_idx <= entry_idx:
        return None
    liq = quotes[entry_idx:flat_idx + 1, :4] if side == 1 else quotes[entry_idx:flat_idx + 1, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 1] >= tp_p - 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 2] <= tp_p + 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)

    f_sl = int(sl_hits[0]) if len(sl_hits) else None
    f_tp = int(tp_hits[0]) if len(tp_hits) else None

    if f_sl is not None and (f_tp is None or f_sl <= f_tp):
        rel = f_sl
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        reason = "SL_GAP_OR_TOUCH"
    elif f_tp is not None:
        rel = f_tp
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - tp_p) >= -1e-10
        ex_p = op if gap else tp_p
        reason = "TP_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        ex_p = float(liq[-1, 0])
        reason = "HARD_FLAT"

    e_ts = int(times[entry_idx])
    x_ts = int(times[entry_idx + rel])
    enforce_pre_holdout_ts((e_ts, x_ts), START, STOP, context=f"pass24.replay_causal_intraday:{asset}")

    c = asset_cost_tiers(asset)
    if c.get("is_crypto"):
        gross = side * (ex_p - entry_p)
        def _cry_r(pct_rt: float) -> tuple[float, float]:
            slip_px = entry_p * pct_rt
            net = gross - slip_px
            rsk = risk_p + slip_px
            return net, net / rsk
        net_b, r_b = _cry_r(c["base_pct"])
        net_s, r_s = _cry_r(c["stress_pct"])
        net_d, r_d = _cry_r(c["double_pct"])
        worst_px = float(liq[:rel + 1, 2].min()) if side == 1 else float(liq[:rel + 1, 1].max())
        mae_p = max(0.0, side * (entry_p - worst_px))
        s_px = entry_p * c["stress_pct"]
        mae_r = min(1.5, (mae_p + s_px) / (risk_p + s_px))
        gross_usd = gross
        ftmo_cs = s_px
    elif c["is_index"]:
        gross = side * (ex_p - entry_p)
        def _idx_r(slip_rt: float) -> tuple[float, float]:
            net = gross - slip_rt
            rsk = risk_p + slip_rt
            return net, net / rsk
        net_b, r_b = _idx_r(c["base"])
        net_s, r_s = _idx_r(c["stress"])
        net_d, r_d = _idx_r(c["double"])
        worst_px = float(liq[:rel + 1, 2].min()) if side == 1 else float(liq[:rel + 1, 1].max())
        mae_p = max(0.0, side * (entry_p - worst_px))
        mae_r = min(1.5, (mae_p + c["stress"]) / (risk_p + c["stress"]))
        gross_usd = gross
        ftmo_cs = c["stress"]
    else:
        if spec is None:
            raise ValueError(f"Missing broker spec for non-index asset: {asset}")
        cs = float(spec["trade_contract_size"])
        d_entry = datetime.fromtimestamp(e_ts, timezone.utc).date()
        d_ex = datetime.fromtimestamp(x_ts, timezone.utc).date()

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
                usdjpy_ent = _prior_day_rate(usdjpy_close_map, d_entry)
                entry_conv_rate = 1.0 / (usdjpy_ent if usdjpy_ent is not None else entry_p)
                usdjpy_ex = (
                    (usdjpy_close_map.get(d_ex) or _prior_day_rate(usdjpy_close_map, d_ex) or usdjpy_ent)
                    if usdjpy_close_map
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
        comm = c["comm_usd"]
        def _fx_r(slip_rt: float) -> tuple[float, float]:
            exit_drag = comm + slip_rt * exit_scale
            entry_drag = comm + slip_rt * entry_scale
            net = gross_usd - exit_drag
            rsk = risk_p * entry_scale + entry_drag
            return net, net / rsk
        net_b, r_b = _fx_r(c["base"])
        net_s, r_s = _fx_r(c["stress"])
        net_d, r_d = _fx_r(c["double"])
        worst_px = float(liq[:rel + 1, 2].min()) if side == 1 else float(liq[:rel + 1, 1].max())
        mae_p = max(0.0, side * (entry_p - worst_px))
        mae_scale = (cs / worst_px) if asset in ("USDJPY", "USDCAD", "USDCHF") else entry_scale
        drag_s_entry = comm + c["stress"] * entry_scale
        mae_r = min(1.5, (mae_p * mae_scale + drag_s_entry) / (risk_p * entry_scale + drag_s_entry))
        ftmo_cs = comm + c["stress"] * exit_scale

    d_iso = datetime.fromtimestamp(e_ts, timezone.utc).date().isoformat()
    return {
        "day": d_iso, "year": int(d_iso[:4]), "entry": e_ts, "exit": x_ts,
        "side": side, "reason": reason,
        "gross_usd": gross_usd, "ftmo_comm_slip": ftmo_cs, "ftmo_swap": 0.0,
        "ftmo_net": net_s, "ftmo_R": r_s,
        "base_R": r_b, "double_R": r_d, "mae_R": mae_r,
        "ex_R_normal": r_b, "ex_R_swapfree": r_b,
    }


def build_unified_asset(asset: str, jobs_root: Path, cache_dir: Path, swing_specs: dict, usdjpy_close_map: dict) -> dict:
    """Build unified causal daily/session frame for any of the 8 Native M1 Bid/Ask assets."""
    is_idx = asset in ("US500", "US100", "GER40")
    if not is_idx:
        ctx = wbd.build_asset_ctx_extended(jobs_root, asset, cache_dir, swing_specs[asset], usdjpy_close_map)
        assert ctx["meta"]["native_Ask"] is True
        times, quotes = ctx["times"], ctx["quotes"]
        d1, off = ctx["full_d1"], ctx["d1_offset"]
        days = []
        for idx in range(off, len(d1)):
            a_val = float(ctx["d1_atr"][idx - 1])
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
                "atr": a_val, "ema50": float(ctx["d1_ema50"][idx - 1]),
                "prev_c": float(ctx["d1_c"][idx - 1]),
                "pdh": float(ctx["d1_h"][idx - 1]), "pdl": float(ctx["d1_l"][idx - 1]),
                "win_start_sec": dsec + 7 * 3600, "win_end_sec": dsec + 16 * 3600,
                "morn_start_sec": dsec + 7 * 3600, "morn_end_sec": dsec + 12 * 3600,
                "twap_check_sec": dsec + 10 * 3600,
                "sqz_specs": [
                    ("SQZ_LDN_4H_045", dsec + 3 * 3600, dsec + 7 * 3600, dsec + 15 * 3600, 0.45),
                    ("SQZ_NY_4H_045", dsec + 8 * 3600, dsec + 12 * 3600, dsec + 17 * 3600, 0.45),
                    ("SQZ_NY_6H_055", dsec + 6 * 3600, dsec + 12 * 3600, dsec + 17 * 3600, 0.55),
                ],
            })
        return {"asset": asset, "is_index": False, "times": times, "quotes": quotes, "days": days, "spec": swing_specs[asset], "usdjpy_close_map": usdjpy_close_map}

    # Index assets (US500, US100, GER40)
    times, quotes, meta = hcache.load_asset(asset, cache_dir, verify_sha=True)
    assert meta["native_Ask"] is True
    sess, atr = p23d.build_ger40_sessions(times, quotes) if asset == "GER40" else p18.build_us500_sessions(times, quotes)
    ema50 = p14.ema(np.array([s["c"] for s in sess], dtype=np.float64), 50)
    morn_len = 240 if asset == "GER40" else 120
    win_end_min = 420 if asset == "GER40" else 300
    days = []
    for idx in range(55, len(sess)):
        a_val = float(atr[idx - 1])
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        s, prev_s = sess[idx], sess[idx - 1]
        s0 = s["start"]
        days.append({
            "day": s["day"], "year": s["year"], "day_sec": s0,
            "fi": s["lo"], "ei": s["hi"], "flat_idx": s["hi"] - 1,
            "atr": a_val, "ema50": float(ema50[idx - 1]),
            "prev_c": float(prev_s["c"]), "pdh": float(prev_s["h"]), "pdl": float(prev_s["l"]),
            "win_start_sec": s0 + 30 * 60, "win_end_sec": s0 + win_end_min * 60,
            "morn_start_sec": s0, "morn_end_sec": s0 + morn_len * 60,
            "twap_check_sec": s0 + 90 * 60,
            "sqz_specs": [
                ("SQZ_LDN_4H_045", s0, s0 + 60 * 60, s0 + win_end_min * 60, 0.45),
                ("SQZ_NY_4H_045", s0, s0 + 90 * 60, s0 + win_end_min * 60, 0.55),
                ("SQZ_NY_6H_055", s0, s0 + 120 * 60, s0 + win_end_min * 60, 0.65),
            ],
        })
    return {"asset": asset, "is_index": True, "times": times, "quotes": quotes, "days": days, "spec": None, "usdjpy_close_map": usdjpy_close_map}


# ==============================================================================
# 6 NEW CAUSAL MTF STRUCTURAL FAMILIES (16 SPECS PER ASSET, ZERO LOOKAHEAD)
# ==============================================================================

def _scan_stop_breakout(bundle: dict, d: dict, win_s: int, win_e: int, top: float, bot: float, sl_dist: float, *, ok_b: bool = True, ok_s: bool = True):
    times, quotes = bundle["times"], bundle["quotes"]
    fi, flat_idx = d["fi"], d["flat_idx"]
    sub_t = times[fi:flat_idx + 1]
    i0 = int(sub_t.searchsorted(win_s, side="left"))
    i1 = int(sub_t.searchsorted(win_e, side="left"))
    if i1 <= i0:
        return None, None
    scan = quotes[fi + i0:fi + i1]
    up = (scan[:, 5] >= top - 1e-10) if ok_b else np.zeros(len(scan), dtype=bool)
    dn = (scan[:, 2] <= bot + 1e-10) if ok_s else np.zeros(len(scan), dtype=bool)
    hits = np.flatnonzero(up | dn)
    if not len(hits):
        return None, None
    j = int(hits[0])
    if up[j] and dn[j]:
        return None, None
    side = 1 if up[j] else -1
    e_idx = fi + i0 + j
    spr = max(0.0, float(quotes[e_idx, 4] - quotes[e_idx, 0]))
    ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
    fep = (ep - spr) if side == 1 else (ep + spr)
    tr = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_dist, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
    fd = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_dist, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
    return tr, fd


def eval_h1_channel(bundle: dict, *, lookback_h: int, sl_atr: float = 0.75, trend_filter: bool = False):
    """Family 1: Causal rolling prior K-hour H1 channel breakout inside active liquidity window."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    lb_sec = lookback_h * 3600
    for d in bundle["days"]:
        ws, we, a_val = d["win_start_sec"], d["win_end_sec"], d["atr"]
        c0 = int(times.searchsorted(ws - lb_sec, side="left"))
        c1 = int(times.searchsorted(ws, side="left"))
        if c1 - c0 < 60:
            continue
        ch_hi = float(quotes[c0:c1, 1].max())
        ch_lo = float(quotes[c0:c1, 2].min())
        if ch_hi <= ch_lo:
            continue
        ok_b = ok_s = True
        if trend_filter:
            if not np.isfinite(d["ema50"]):
                continue
            ok_b = d["prev_c"] > d["ema50"]
            ok_s = d["prev_c"] < d["ema50"]
        tr, fd = _scan_stop_breakout(bundle, d, ws, we, ch_hi, ch_lo, sl_atr * a_val, ok_b=ok_b, ok_s=ok_s)
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_vol_squeeze(bundle: dict, *, sqz_idx: int, sl_atr: float = 0.65, max_ratio_override: float | None = None):
    """Family 2: Pre-session tight volatility compression breakout."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        _name, bs, be, we, max_r = d["sqz_specs"][sqz_idx]
        if max_ratio_override is not None:
            max_r = max_ratio_override
        a_val = d["atr"]
        b0 = int(times.searchsorted(bs, side="left"))
        b1 = int(times.searchsorted(be, side="left"))
        if b1 - b0 < 30:
            continue
        hi_b = float(quotes[b0:b1, 1].max())
        lo_b = float(quotes[b0:b1, 2].min())
        width = hi_b - lo_b
        if width < 0.10 * a_val or width > max_r * a_val:
            continue
        tr, fd = _scan_stop_breakout(bundle, d, be, we, hi_b, lo_b, sl_atr * a_val)
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_sess_continuation(bundle: dict, *, min_move_atr: float, mode: str = "BRK", sl_atr: float = 0.65, close_pct: float = 0.70):
    """Family 3: Strong morning directional close -> afternoon breakout or market continuation."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        ms, me, we, a_val = d["morn_start_sec"], d["morn_end_sec"], d["win_end_sec"], d["atr"]
        m0 = int(times.searchsorted(ms, side="left"))
        m1 = int(times.searchsorted(me, side="left"))
        if m1 - m0 < 60:
            continue
        mq = quotes[m0:m1]
        mo, mc = float(mq[0, 0]), float(mq[-1, 3])
        mh, ml = float(mq[:, 1].max()), float(mq[:, 2].min())
        mrng = mh - ml
        if mrng <= 1e-9 or abs(mc - mo) < min_move_atr * a_val:
            continue
        pos_in_rng = (mc - ml) / mrng
        if mc > mo and pos_in_rng >= close_pct:
            side = 1
        elif mc < mo and pos_in_rng <= (1.0 - close_pct):
            side = -1
        else:
            continue

        if mode == "BRK":
            tr, fd = _scan_stop_breakout(bundle, d, me, max(we, me + 5 * 3600), mh, ml, sl_atr * a_val, ok_b=(side == 1), ok_s=(side == -1))
        else:
            # Causal market entry on FIRST M1 bar >= me (strictly after morning closes!)
            fi, flat_idx = d["fi"], d["flat_idx"]
            sub_t = times[fi:flat_idx + 1]
            j = int(sub_t.searchsorted(me, side="left"))
            e_idx = fi + j
            if e_idx >= flat_idx:
                continue
            ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
            fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
            tr = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_atr * a_val, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
            fd = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_atr * a_val, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_m15_pdhl_sweep(bundle: dict, *, tp_r: float | None = None, trend_filter: bool = False, sl_pad_atr: float = 0.15):
    """Family 4: Causal M15 failed sweep beyond Prior-Day High/Low closing back inside -> next-M1 reversal entry."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        fi, flat_idx = d["fi"], d["flat_idx"]
        ws, we, a_val = d["win_start_sec"], d["win_end_sec"], d["atr"]
        pdh, pdl = d["pdh"], d["pdl"]
        if pdh <= pdl:
            continue
        ok_b = ok_s = True
        if trend_filter:
            if not np.isfinite(d["ema50"]):
                continue
            ok_b = d["prev_c"] > d["ema50"]
            ok_s = d["prev_c"] < d["ema50"]

        sub_t = times[fi:flat_idx + 1]
        sub_q = quotes[fi:flat_idx + 1]
        i0 = int(sub_t.searchsorted(ws, side="left"))
        i1 = int(sub_t.searchsorted(we, side="left"))
        if i1 - i0 < 30:
            continue
        # Group into causal 15-minute buckets
        b_ids = (sub_t[i0:i1] - d["day_sec"]) // 900
        uniq, starts, cnts = np.unique(b_ids, return_index=True, return_counts=True)
        swept_hi = False; hi_ext = pdh
        swept_lo = False; lo_ext = pdl
        chosen = None
        for b, st, cnt in zip(uniq, starts, cnts):
            if cnt < 5:
                continue
            sl_q = sub_q[i0 + st:i0 + st + cnt]
            bh = float(sl_q[:, 1].max())
            bl = float(sl_q[:, 2].min())
            bc = float(sl_q[-1, 3])
            m15_end_sec = d["day_sec"] + int(b + 1) * 900
            if bh > pdh:
                swept_hi = True
                hi_ext = max(hi_ext, bh)
            if bl < pdl:
                swept_lo = True
                lo_ext = min(lo_ext, bl)
            # Reclaim confirmation strictly at M15 bar close -> next M1 bar >= m15_end_sec
            if swept_hi and ok_s and bc < pdh and bc > pdl:
                chosen = (-1, hi_ext, m15_end_sec)
                break
            if swept_lo and ok_b and bc > pdl and bc < pdh:
                chosen = (1, lo_ext, m15_end_sec)
                break
        if chosen is None:
            continue
        side, ext_px, after_sec = chosen
        j_ent = int(sub_t.searchsorted(after_sec, side="left"))
        e_idx = fi + j_ent
        if e_idx >= flat_idx:
            continue
        ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
        fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
        raw_sl_d = abs(ep - ext_px) + sl_pad_atr * a_val
        sl_d = min(max(raw_sl_d, 0.35 * a_val), 1.00 * a_val)
        tp_p = (ep + side * tp_r * sl_d) if tp_r is not None else None
        ftp_p = (fep - side * tp_r * sl_d) if tp_r is not None else None
        tr = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_d, tp_p=tp_p, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
        fd = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_d, tp_p=ftp_p, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_m15_twap_pullback(bundle: dict, *, drive_atr: float, sl_atr: float = 0.60):
    """Family 5: Early directional drive -> causal M15 pullback bounce off session cumulative TWAP -> next-M1 entry."""
    times, quotes = bundle["times"], bundle["quotes"]
    trs, fds = [], []
    for d in bundle["days"]:
        fi, flat_idx = d["fi"], d["flat_idx"]
        ws, t_chk, we, a_val = d["win_start_sec"], d["twap_check_sec"], d["win_end_sec"], d["atr"]
        sub_t = times[fi:flat_idx + 1]
        sub_q = quotes[fi:flat_idx + 1]
        s0_i = int(sub_t.searchsorted(d["morn_start_sec"], side="left"))
        chk_i = int(sub_t.searchsorted(t_chk, side="left"))
        we_i = int(sub_t.searchsorted(we, side="left"))
        if chk_i - s0_i < 45 or we_i <= chk_i + 15:
            continue
        open_p = float(sub_q[s0_i, 0])
        chk_p = float(sub_q[chk_i - 1, 3])
        move = chk_p - open_p
        if abs(move) < drive_atr * a_val:
            continue
        side = 1 if move > 0 else -1

        # Strictly causal cumulative session TWAP from s0_i onward
        mids = 0.5 * (sub_q[s0_i:we_i, 3] + sub_q[s0_i:we_i, 7])
        twap_all = np.cumsum(mids) / np.arange(1, len(mids) + 1, dtype=np.float64)

        b_ids = (sub_t[chk_i:we_i] - d["day_sec"]) // 900
        uniq, starts, cnts = np.unique(b_ids, return_index=True, return_counts=True)
        chosen_sec = None
        for b, st, cnt in zip(uniq, starts, cnts):
            if cnt < 5:
                continue
            g0 = chk_i + st
            g1 = g0 + cnt
            sl_q = sub_q[g0:g1]
            bo, bh, bl, bc = float(sl_q[0, 0]), float(sl_q[:, 1].max()), float(sl_q[:, 2].min()), float(sl_q[-1, 3])
            tw_end = float(twap_all[(g1 - 1) - s0_i])
            if side == 1 and bl <= tw_end and bc > tw_end and bc > bo:
                chosen_sec = d["day_sec"] + int(b + 1) * 900
                break
            if side == -1 and bh >= tw_end and bc < tw_end and bc < bo:
                chosen_sec = d["day_sec"] + int(b + 1) * 900
                break
        if chosen_sec is None:
            continue
        e_idx = fi + int(sub_t.searchsorted(chosen_sec, side="left"))
        if e_idx >= flat_idx:
            continue
        ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
        fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
        tr = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_atr * a_val, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
        fd = replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_atr * a_val, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_pdhl_breakout(bundle: dict, *, narrow_max_atr: float | None = None, sl_atr: float = 0.75):
    """Family 6: Causal breakout beyond exact Prior-Day High/Low (optionally after Narrow-Range prior day)."""
    trs, fds = [], []
    for d in bundle["days"]:
        pdh, pdl, a_val = d["pdh"], d["pdl"], d["atr"]
        if pdh <= pdl:
            continue
        if narrow_max_atr is not None and (pdh - pdl) > narrow_max_atr * a_val:
            continue
        tr, fd = _scan_stop_breakout(bundle, d, d["win_start_sec"], d["win_end_sec"], pdh, pdl, sl_atr * a_val)
        if tr and fd:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def build_pass24_catalog() -> list[dict]:
    """Fixed preregistered 16-spec MTF catalog (6 orthogonal new families, swap=0)."""
    return [
        # Family 1: H1 Channel Breakout (3)
        {"id": "H1_CH12_SL75", "fam": "H1_CHANNEL_BRK", "lookback_h": 12, "sl_atr": 0.75, "trend": False},
        {"id": "H1_CH24_SL75", "fam": "H1_CHANNEL_BRK", "lookback_h": 24, "sl_atr": 0.75, "trend": False},
        {"id": "H1_CH24_TREND_SL75", "fam": "H1_CHANNEL_BRK", "lookback_h": 24, "sl_atr": 0.75, "trend": True},
        # Family 2: Pre-Session Volatility Squeeze Breakout (3)
        {"id": "SQZ_LDN_4H_045", "fam": "H1_VOL_SQUEEZE", "sqz_idx": 0, "sl_atr": 0.65},
        {"id": "SQZ_NY_4H_045", "fam": "H1_VOL_SQUEEZE", "sqz_idx": 1, "sl_atr": 0.65},
        {"id": "SQZ_NY_6H_055", "fam": "H1_VOL_SQUEEZE", "sqz_idx": 2, "sl_atr": 0.65},
        # Family 3: Cross-Session Morning -> Afternoon Continuation (3)
        {"id": "SESS_CONT_BRK_40", "fam": "SESS_CONTINUATION", "min_move_atr": 0.40, "mode": "BRK", "sl_atr": 0.65},
        {"id": "SESS_CONT_BRK_55", "fam": "SESS_CONTINUATION", "min_move_atr": 0.55, "mode": "BRK", "sl_atr": 0.65},
        {"id": "SESS_CONT_MKT_50", "fam": "SESS_CONTINUATION", "min_move_atr": 0.50, "mode": "MKT", "sl_atr": 0.65},
        # Family 4: Causal M15 Failed Prior-Day High/Low Sweep Reversal (3)
        {"id": "PDHL_SWEEP_FLAT", "fam": "M15_PDHL_SWEEP", "tp_r": None, "trend": False},
        {"id": "PDHL_SWEEP_TP2R", "fam": "M15_PDHL_SWEEP", "tp_r": 2.0, "trend": False},
        {"id": "PDHL_SWEEP_TREND", "fam": "M15_PDHL_SWEEP", "tp_r": None, "trend": True},
        # Family 5: Causal M15 Session TWAP Pullback Continuation (2)
        {"id": "TWAP_PB_40", "fam": "M15_TWAP_PULLBACK", "drive_atr": 0.40, "sl_atr": 0.60},
        {"id": "TWAP_PB_55", "fam": "M15_TWAP_PULLBACK", "drive_atr": 0.55, "sl_atr": 0.60},
        # Family 6: Causal Prior-Day Range Breakout (2)
        {"id": "PDHL_BRK_ALL", "fam": "D1_PDHL_BREAKOUT", "narrow_max_atr": None, "sl_atr": 0.75},
        {"id": "PDHL_BRK_NR", "fam": "D1_PDHL_BREAKOUT", "narrow_max_atr": 0.80, "sl_atr": 0.75},
    ]


def eval_spec(bundle: dict, cfg: dict):
    fam = cfg["fam"]
    if fam == "H1_CHANNEL_BRK":
        return eval_h1_channel(bundle, lookback_h=cfg["lookback_h"], sl_atr=cfg["sl_atr"], trend_filter=cfg["trend"])
    if fam == "H1_VOL_SQUEEZE":
        return eval_vol_squeeze(bundle, sqz_idx=cfg["sqz_idx"], sl_atr=cfg["sl_atr"], max_ratio_override=cfg.get("max_ratio_override"))
    if fam == "SESS_CONTINUATION":
        return eval_sess_continuation(bundle, min_move_atr=cfg["min_move_atr"], mode=cfg["mode"], sl_atr=cfg["sl_atr"], close_pct=cfg.get("close_pct", 0.70))
    if fam == "M15_PDHL_SWEEP":
        return eval_m15_pdhl_sweep(bundle, tp_r=cfg["tp_r"], trend_filter=cfg["trend"], sl_pad_atr=cfg.get("sl_pad_atr", 0.15))
    if fam == "M15_TWAP_PULLBACK":
        return eval_m15_twap_pullback(bundle, drive_atr=cfg["drive_atr"], sl_atr=cfg["sl_atr"])
    if fam == "D1_PDHL_BREAKOUT":
        return eval_pdhl_breakout(bundle, narrow_max_atr=cfg["narrow_max_atr"], sl_atr=cfg["sl_atr"])
    raise ValueError(f"Unknown family: {fam}")


# ==============================================================================
# DUAL-FIRM 2-LAYER CHALLENGE EVALUATOR (FTMO SWING 10K + THE5ERS HIGH STAKES 5K)
# ==============================================================================

def simulate_dual_firm_2layer(
    nets_base: np.ndarray,
    dds_base: np.ndarray,
    flags_base: np.ndarray,
    *,
    firm: str,
    cap: float,
    fee: float,
    p1_m: float = 1.0,
    p2_m: float = 1.0,
    fund_m: float = 1.0,
    dynamic: bool = False,
    n_paths: int = 2000,
    seed: int = SEED,
) -> dict:
    """2-Layer Challenge Policy Evaluator for FTMO Swing 10k & The5ers High Stakes 5k (3 profitable days >= 0.5% + Hub Credits)."""
    rng = np.random.default_rng(seed)
    n_obs = len(nets_base)
    max_h = 504  # 24 months
    blk = 5
    nb = (max_h + blk - 1) // blk
    horizons = (63, 126, 189, 252, 504)
    pass_h = {h: 0 for h in horizons}
    pass_m_list = []
    br1 = 0
    tix_list, cf12, cf24 = [], [], []
    is_5ers = (firm == "THE5ERS_HS_5K")

    for _ in range(n_paths):
        starts = rng.integers(0, n_obs, size=nb)
        idxs = (starts[:, None] + np.arange(blk)[None, :]).ravel()[:max_h] % n_obs
        sn, sd, sf = nets_base[idxs], dds_base[idxs], flags_base[idxs]

        stage = "P1"; bal = cap; qdays = 0; att = 1; cash_fees = fee; hub_credit = 0.0
        refunded = False; pay_tot = 0.0; cyc = 0
        passed_once = False; passed_day = None; first_breached = False; snap12 = None

        for di in range(max_h):
            if di == 252:
                snap12 = pay_tot - cash_fees
            if stage == "DEAD":
                continue
            if stage == "P1":
                mult = p1_m
                if dynamic:
                    pnl_p = (bal - cap) / cap
                    if pnl_p >= 0.075:
                        mult = p1_m * 0.65  # Bellman target-proximity taper
                    elif pnl_p >= 0.03:
                        mult = p1_m * 1.20  # House-money cushion boost
                    elif pnl_p <= -0.03:
                        mult = p1_m * 0.60  # Drawdown throttle
            elif stage == "P2":
                mult = p2_m
                if dynamic and (bal - cap) / cap <= -0.025:
                    mult = p2_m * 0.60
            else:
                mult = fund_m

            day_dd = sd[di] * mult
            day_net = sn[di] * mult
            if (day_dd >= cap * 0.05 - 1e-9) or ((bal - day_dd) <= cap * 0.90 + 1e-9):
                if att == 1 and not passed_once:
                    first_breached = True
                if att < 6:
                    att += 1
                    use_hc = min(hub_credit, fee) if is_5ers else 0.0
                    hub_credit -= use_hc
                    cash_fees += (fee - use_hc)
                    stage = "P1"; bal = cap; qdays = 0; refunded = False; cyc = 0
                else:
                    stage = "DEAD"
                continue

            bal += day_net
            if is_5ers:
                # High Stakes Profitable Day: >= +0.5% of initial balance (conservative EOD closed net)
                if day_net >= cap * 0.005 - 1e-9:
                    qdays += 1
            else:
                if sf[di]:
                    qdays += 1

            min_d = 3 if is_5ers else 4
            if stage == "P1" and bal >= cap * 1.10 - 1e-9 and qdays >= min_d:
                if is_5ers:
                    hub_credit += 0.10 * fee
                stage = "P2"; bal = cap; qdays = 0
            elif stage == "P2" and bal >= cap * 1.05 - 1e-9 and qdays >= min_d:
                if is_5ers:
                    hub_credit += 0.20 * fee
                stage = "FUNDED"; bal = cap; qdays = 0; cyc = 0
                if not passed_once:
                    passed_once = True; passed_day = di + 1
            elif stage == "FUNDED":
                cyc += 1
                if cyc >= 10:
                    if bal > cap + 1e-6:
                        raw_pay = (bal - cap) * 0.80
                        min_pay = 150.0 if is_5ers else 0.0
                        ref_amt = (0.70 * fee if is_5ers else fee) if not refunded else 0.0
                        if raw_pay + ref_amt >= min_pay:
                            pay_tot += raw_pay + ref_amt
                            refunded = True
                            bal = cap
                    cyc = 0

        if passed_once:
            pass_m_list.append(passed_day / 21.0)
            for h in horizons:
                if passed_day <= h:
                    pass_h[h] += 1
        if first_breached:
            br1 += 1
        tix_list.append(att)
        cf12.append(snap12 if snap12 is not None else (pay_tot - cash_fees))
        cf24.append(pay_tot - cash_fees)

    return {
        "firm": firm, "cap": cap, "fee": fee,
        "pass_pct": {f"{h//21}m": round(100.0 * pass_h[h] / n_paths, 1) for h in horizons},
        "br1_pct": round(100.0 * br1 / n_paths, 1),
        "avg_tickets": round(float(np.mean(tix_list)), 2),
        "med_pass_m": round(float(np.median(pass_m_list)), 1) if pass_m_list else None,
        "cf12_mean": round(float(np.mean(cf12)), 1),
        "cf24_mean": round(float(np.mean(cf24)), 1),
        "cf24_med": round(float(np.median(cf24)), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(np.array(cf24) > 0)), 1),
    }


def run_forensic_for_survivor(bundle: dict, cfg: dict, core3_daily: dict[str, float]) -> dict:
    """Deep forensic gate: 3 cost tiers, Dual 2D parameter surfaces, Outlier/Crisis Stress, BUY/SELL."""
    trs, fds = eval_spec(bundle, cfg)
    res = {
        "asset": bundle["asset"], "strategy": cfg["id"], "family": cfg["fam"],
        "n": len(trs),
        "cost_tiers": {
            "Base": round(fsum(t["base_R"] for t in trs), 2),
            "Stress": round(fsum(t["ftmo_R"] for t in trs), 2),
            "Double": round(fsum(t["double_R"] for t in trs), 2),
        },
        "fade_R": round(fsum(f["ftmo_R"] for f in fds), 2),
        "outlier": p23d.outlier_stress_trades(trs),
        "direction": p18.direction_breakdown(trs),
        "corr_3e": p18.daily_correlation(trs, core3_daily)["union_corr"],
    }
    # Dual 2D parameter stability surface per family
    fam = cfg["fam"]
    s1, s2 = {}, {}
    if fam == "H1_CHANNEL_BRK":
        for lb in (8, 12, 18, 24, 30):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_spec(bundle, {**cfg, "lookback_h": lb, "sl_atr": sa})
                s1[f"lb{lb}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "H1_VOL_SQUEEZE":
        for mr in (0.35, 0.45, 0.55, 0.65):
            for sa in (0.50, 0.65, 0.85):
                tt, _ = eval_spec(bundle, {**cfg, "max_ratio_override": mr, "sl_atr": sa})
                s1[f"mr{mr:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "SESS_CONTINUATION":
        for mm in (0.30, 0.40, 0.50, 0.60):
            for sa in (0.50, 0.65, 0.85):
                tt, _ = eval_spec(bundle, {**cfg, "min_move_atr": mm, "sl_atr": sa})
                s1[f"mm{mm:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
            for cp in (0.60, 0.70, 0.80):
                tt, _ = eval_spec(bundle, {**cfg, "min_move_atr": mm, "close_pct": cp})
                s2[f"mm{mm:.2f}_cp{cp:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "M15_PDHL_SWEEP":
        for pad in (0.05, 0.15, 0.25):
            for trp in (None, 1.5, 2.0, 2.5):
                tt, _ = eval_spec(bundle, {**cfg, "sl_pad_atr": pad, "tp_r": trp})
                s1[f"p{pad:.2f}_tp{trp}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "M15_TWAP_PULLBACK":
        for dr in (0.30, 0.40, 0.55, 0.70):
            for sa in (0.45, 0.60, 0.80):
                tt, _ = eval_spec(bundle, {**cfg, "drive_atr": dr, "sl_atr": sa})
                s1[f"dr{dr:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "D1_PDHL_BREAKOUT":
        for nm in (None, 0.70, 0.80, 0.95):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_spec(bundle, {**cfg, "narrow_max_atr": nm, "sl_atr": sa})
                s1[f"nm{nm}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    res["surface_1"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
    if s2:
        res["surface_2"] = {"both_pos": sum(1 for v in s2.values() if v["A"] > 0 and v["B"] > 0), "total": len(s2), "cells": s2}
    res["trades"] = trs
    return res


def run_pass24(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    core3_daily = p23d.build_3engine_daily_series(jobs_root, cache_dir, specs)
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    assets = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "XAUUSD", "US500", "US100", "GER40")
    bundles = {a: build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map) for a in assets}
    catalog = build_pass24_catalog()

    all_evals = []
    for a in assets:
        prov_spec = a in ("US100", "GER40")
        b = bundles[a]
        for cfg in catalog:
            trs, fds = eval_spec(b, cfg)
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
        corr_3e = p18.daily_correlation(trs, core3_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)

        tier1_core = (
            len(trs) >= 150 and mB["net_R"] > 0 and tot_R > top10 and tot_R > fade_R
            and pos_yrs >= 5 and dd_R <= 15.0 and sf["ftmo_net_p"] < 0.05 and q_full <= 0.10
            and abs(corr_3e) <= 0.25
        )
        if tier1_core:
            tier = "TIER_1_FTMO_READY_PROVISIONAL_SPEC" if prov_spec else "TIER_1_FTMO_READY"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT_PROVISIONAL_SPEC" if prov_spec else "TIER_2_PERSONAL_VAULT"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "family": cfg["fam"], "asset": asset,
            "provisional_spec": prov_spec, "n_total": len(trs),
            "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "ftmo_double_R": dbl_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R, "top10_R": top10,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_3e": corr_3e, "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    tier_counts = dict(Counter(r["tier"] for r in survivors))
    tier_counts["STAGE1_FILTERED_OUT_ON_CLUSTER_A"] = m_total - len(survivors)

    print(f"\n=== PASS 24: MTF 6 NEW FAMILIES DISCOVERY (m_total={m_total} across 8 Native Bid/Ask assets, Cluster A -> Blind Cluster B) ===", flush=True)
    print(f"  Passed Cluster A Gate: {len(survivors)} / {m_total} | Tiers: {tier_counts}", flush=True)
    for r in survivors[:25]:
        print(
            f"  {r['strategy']:20s} {r['asset']:6s} ({r['family']:17s}) | n={r['n_total']:4d} "
            f"| A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (B={r['ftmo_base_R']:+5.1f}, D={r['ftmo_double_R']:+5.1f}, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:4.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q={r['fdr_q_full_space']:.3f} | r3E={r['corr_3e']:+.3f} | {r['tier']}",
            flush=True,
        )

    # --- STAGE 3: DEEP FORENSIC ON ALL TIER_1 + TOP ORTHOGONAL TIER_2 (p < 0.02, |r3E| <= 0.25) ---
    targets = [r for r in survivors if "TIER_1" in r["tier"]]
    for r in survivors:
        if "TIER_2" in r["tier"] and r["p_sign_flip"] < 0.02 and abs(r["corr_3e"]) <= 0.25 and r not in targets:
            targets.append(r)

    forensic_reports = []
    qualified_engines = []
    if targets:
        print(f"\n=== STAGE 3: DEEP FORENSIC AUDIT ({len(targets)} target(s)) ===", flush=True)
        for cand in targets[:6]:
            frep = run_forensic_for_survivor(bundles[cand["asset"]], cand["spec"], core3_daily)
            tr_list = frep.pop("trades")
            s1 = frep["surface_1"]
            s2 = frep.get("surface_2")
            s1_ok = (s1["both_pos"] / max(1, s1["total"])) >= 0.50
            cost_ok = (frep["cost_tiers"]["Base"] > 0 and frep["cost_tiers"]["Stress"] > 0 and frep["cost_tiers"]["Double"] > 0)
            out_ok = (frep["outlier"]["drop_top3_R"] > 0 and frep["outlier"]["excl_both_crises_R"] > 0)
            frep["forensic_pass"] = bool(cost_ok and s1_ok and out_ok)
            forensic_reports.append(frep)
            print(
                f"  FORENSIC {cand['asset']:6s} {cand['strategy']:20s} | tiers={frep['cost_tiers']} "
                f"| out(-T3={frep['outlier']['drop_top3_R']:+.1f}, -T5={frep['outlier']['drop_top5_R']:+.1f}, exCr={frep['outlier']['excl_both_crises_R']:+.1f}) "
                f"| s1={s1['both_pos']}/{s1['total']}" + (f" s2={s2['both_pos']}/{s2['total']}" if s2 else "") +
                f" | r3E={frep['corr_3e']:+.3f} | PASS={frep['forensic_pass']}",
                flush=True,
            )
            if frep["forensic_pass"]:
                qualified_engines.append((cand, tr_list))

    # --- STAGE 4: DUAL-FIRM 2-LAYER EVALUATION (FTMO SWING 10K + THE5ERS HIGH STAKES 5K) ---
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

    # Portfolio variants: Base 3E + each qualified Engine #4 + combined multi-engine (if >= 2 independent assets pass!)
    port_series = {"CORE_3E": (nets3_10k, dds3_10k, flags3)}
    # Pick best non-duplicate qualified engine per asset
    picked_assets = set()
    picked_engines = []
    for cand, tr_list in qualified_engines:
        if cand["asset"] not in picked_assets:
            picked_assets.add(cand["asset"])
            picked_engines.append((cand, tr_list))

    def _add_engines(eng_list, risk_pct_each=0.0050):
        n_arr, d_arr, f_arr = nets3_10k.copy(), dds3_10k.copy(), flags3.copy()
        r_usd = 10000.0 * risk_pct_each
        for _c, trs in eng_list:
            by_d = defaultdict(list)
            for t in trs:
                by_d[t["day"]].append(t)
            for i, d_k in enumerate(d_list):
                if d_k in by_d:
                    n_arr[i] += fsum(t["ftmo_R"] * r_usd for t in by_d[d_k])
                    d_arr[i] += fsum(t["mae_R"] * r_usd for t in by_d[d_k])
                    f_arr[i] = 1
        return n_arr, d_arr, f_arr

    for cand, tr_list in picked_engines[:3]:
        lbl = f"PLUS_{cand['asset']}_{cand['strategy']}"
        port_series[lbl] = _add_engines([(cand, tr_list)], 0.0050)
    if len(picked_engines) >= 2:
        port_series[f"COMBINED_{3 + len(picked_engines)}E_R50"] = _add_engines(picked_engines, 0.0050)

    dual_firm_eval = {}
    print("\n=== STAGE 4: DUAL-FIRM 2-LAYER EVALUATION (FTMO SWING 10K vs THE5ERS HIGH STAKES 5K · <=1% RISK CAP) ===", flush=True)
    for pname, (n10, d10, flg) in port_series.items():
        eq = np.cumsum(np.insert(n10, 0, 10000.0))
        peak_dd = float(np.max((np.maximum.accumulate(eq[:-1]) - (eq[:-1] - d10)) / 10000.0) * 100.0)
        ann = float((eq[-1] - 10000.0) / 10000.0 / 7.0 * 100.0)
        ann_A = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk < "2021-01-01") / 10000.0 / 3.0 * 100.0)
        ann_B = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk >= "2021-01-01") / 10000.0 / 4.0 * 100.0)
        cal = round(ann / peak_dd, 2) if peak_dd > 1e-9 else 0.0
        print(f"\n  [{pname}] 7y Ann={ann:+.2f}% (A={ann_A:+.2f}%, B={ann_B:+.2f}%) | PeakDD={peak_dd:.2f}% | Calmar={cal:.2f}", flush=True)
        dual_firm_eval[pname] = {"ann_pct": round(ann, 2), "ann_A": round(ann_A, 2), "ann_B": round(ann_B, 2), "peak_dd_pct": round(peak_dd, 2), "calmar": cal, "firms": {}}
        # Scale strictly inside <=1.0% single-trade cap: 1.0x safe & 1.33x dynamic cushion (max 0.75% * 1.33 = 1.0%!)
        for firm, cap, fee, scale in (("FTMO_SWING_10K", 10000.0, 168.0, 1.0), ("THE5ERS_HS_5K", 5000.0, 39.0, 0.5)):
            dual_firm_eval[pname]["firms"][firm] = {}
            for pol_name, p1m, p2m, fm, dyn in (
                ("Flat_Safe_1.0", 1.0, 1.0, 1.0, False),
                ("2Layer_Cap1Pct_Dyn", 1.33, 1.0, 1.0, True),
                ("2Layer_Mod_2.0_Dyn", 2.0, 1.25, 1.0, True),
            ):
                r = simulate_dual_firm_2layer(n10 * scale, d10 * scale, flg, firm=firm, cap=cap, fee=fee, p1_m=p1m, p2_m=p2m, fund_m=fm, dynamic=dyn)
                dual_firm_eval[pname]["firms"][firm][pol_name] = r
                pp = r["pass_pct"]
                print(
                    f"    {firm:14s} | {pol_name:18s} | 3/6/9/12/24m={pp['3m']:4.1f}/{pp['6m']:4.1f}/{pp['9m']:4.1f}/{pp['12m']:4.1f}/{pp['24m']:4.1f}% "
                    f"| Br1={r['br1_pct']:4.1f}% Tix={r['avg_tickets']:.2f} Med={str(r['med_pass_m']):>4s}m "
                    f"| CF12=${r['cf12_mean']:+5.0f} CF24=${r['cf24_mean']:+6.0f} (P>0={r['cf24_pos_pct']:4.1f}%)",
                    flush=True,
                )

    return {
        "pass": "Pass 24 (MTF 6 New Structural Families + Dual-Firm 2-Layer Evaluation)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "m_total_search_space": m_total,
        "cluster_a_survivors": len(survivors),
        "tier_counts": tier_counts,
        "survivors": survivors,
        "forensic_reports": forensic_reports,
        "qualified_engines": [f"{c['asset']}_{c['strategy']}" for c, _ in picked_engines],
        "dual_firm_eval": dual_firm_eval,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass24(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass24-result.json", res)
    print("\nPASS24_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
