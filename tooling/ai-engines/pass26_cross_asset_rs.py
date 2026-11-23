"""Pass 26: Cross-Asset Relative Strength, Currency-Basket Momentum & Intermarket Lead-Lag (m_total=34, 12 Native M1 Assets)."""

import argparse
from collections import Counter, defaultdict
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
import pass19_us500_supertrend_yencross as p19
import pass22_gbpusd_volhigh_3engine as p22
import pass23_ftmo_lifecycle_sim as p23l
import pass23_xau_indices_discovery as p23d
import pass24_mtf_new_archetypes as p24
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "6b5938e7f087b2016777dd930c4657dbc0f230e0"
SEED = 20261123
MC_DRAWS = 1000
FX7 = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY")
USD_MAJORS_NOJPY = ("GBPUSD", "EURUSD", "AUDUSD", "USDCAD")
PAIR_CCY = {
    "USDJPY": ("USD", "JPY"), "GBPUSD": ("GBP", "USD"), "EURUSD": ("EUR", "USD"),
    "GBPJPY": ("GBP", "JPY"), "AUDUSD": ("AUD", "USD"), "USDCAD": ("USD", "CAD"),
    "EURJPY": ("EUR", "JPY"),
}


def causal_completed_bid(times: np.ndarray, quotes: np.ndarray, ts_sec: int, *, max_stale_sec: int = 7200) -> float | None:
    """Return close bid of the last M1 bar strictly BEFORE ts_sec (zero contemporaneous or future lookahead)."""
    j = int(times.searchsorted(ts_sec, side="left")) - 1
    if j < 0:
        return None
    if ts_sec - int(times[j]) > max_stale_sec:
        return None
    return float(quotes[j, 3])


def causal_z_return(bundle: dict, ts_start: int, ts_end: int, atr_val: float) -> float | None:
    """Strictly causal ATR-normalized return over completed M1 bars strictly prior to [ts_start, ts_end)."""
    if atr_val <= 0:
        return None
    p0 = causal_completed_bid(bundle["times"], bundle["quotes"], ts_start)
    p1 = causal_completed_bid(bundle["times"], bundle["quotes"], ts_end)
    if p0 is None or p1 is None:
        return None
    return (p1 - p0) / atr_val


def market_entry_at(bundle: dict, day_rec: dict, ts_entry: int, side: int, sl_atr: float):
    """Causal market entry on first M1 bar >= ts_entry with hard server SL & swap=0 flat."""
    times, quotes = bundle["times"], bundle["quotes"]
    fi, flat_idx = day_rec["fi"], day_rec["flat_idx"]
    sub_t = times[fi:flat_idx + 1]
    rel = int(sub_t.searchsorted(ts_entry, side="left"))
    e_idx = fi + rel
    if e_idx >= flat_idx or int(times[e_idx]) - ts_entry > 600:
        return None, None
    ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
    fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
    sl_d = sl_atr * day_rec["atr"]
    tr = p24.replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, ep - side * sl_d, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
    fd = p24.replay_causal_intraday(bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_d, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"])
    return tr, fd


def compute_g6_factors(z_map: dict[str, float]) -> dict[str, float]:
    """Decompose 7 FX pair ATR-normalized returns into causal G6 currency strength factors."""
    if not all(k in z_map for k in FX7):
        return {}
    return {
        "USD": float(np.mean([z_map["USDJPY"], z_map["USDCAD"], -z_map["EURUSD"], -z_map["GBPUSD"], -z_map["AUDUSD"]])),
        "JPY": float(np.mean([-z_map["USDJPY"], -z_map["EURJPY"], -z_map["GBPJPY"]])),
        "EUR": float(np.mean([z_map["EURUSD"], z_map["EURJPY"]])),
        "GBP": float(np.mean([z_map["GBPUSD"], z_map["GBPJPY"]])),
        "AUD": float(z_map["AUDUSD"]),
        "CAD": float(-z_map["USDCAD"]),
    }


# ==============================================================================
# 5 CROSS-ASSET / INTERMARKET CAUSAL FAMILIES (34 SPECS, ZERO LOOKAHEAD)
# ==============================================================================

def eval_fx_cs_momentum(bundles: dict, day_maps: dict, all_days: list[str], *, entry_h: int, lb_h: int, min_z: float, reverse: bool = False, usd_basket_only: bool = False, sl_atr: float = 0.75):
    """Family 1: Cross-Sectional FX Strongest/Weakest Pair Selection (or Macro USD Basket Factor)."""
    trs, fds = [], []
    for dk in all_days:
        if not all(dk in day_maps[a] for a in FX7):
            continue
        dsec = day_maps["USDJPY"][dk]["day_sec"]
        ts_e = dsec + entry_h * 3600
        ts_s = ts_e - lb_h * 3600
        z_map = {}
        for a in FX7:
            z = causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"])
            if z is not None:
                z_map[a] = z
        if len(z_map) < len(FX7):
            continue

        if usd_basket_only:
            fac = compute_g6_factors(z_map)
            usd_s = fac["USD"]
            if abs(usd_s) < min_z:
                continue
            # Pick strongest aligned non-JPY USD major!
            usd_dir = 1 if usd_s > 0 else -1
            best_a, best_score, best_side = None, -1e9, 0
            for a in USD_MAJORS_NOJPY:
                base, quote = PAIR_CCY[a]
                side = usd_dir if base == "USD" else -usd_dir
                aligned_z = side * z_map[a]
                if aligned_z > best_score:
                    best_a, best_score, best_side = a, aligned_z, side
            if best_a is None or best_score <= 0:
                continue
            chosen_a, side = best_a, best_side
        else:
            # Pick single pair with largest absolute ATR-normalized cross-sectional return
            chosen_a = max(z_map.keys(), key=lambda a: abs(z_map[a]))
            z_best = z_map[chosen_a]
            if abs(z_best) < min_z:
                continue
            raw_side = 1 if z_best > 0 else -1
            side = -raw_side if reverse else raw_side

        tr, fd = market_entry_at(bundles[chosen_a], day_maps[chosen_a][dk], ts_e, side, sl_atr)
        if tr and fd:
            tr["chosen_asset"] = chosen_a
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_ccy_matrix(bundles: dict, day_maps: dict, all_days: list[str], *, entry_h: int, lb_h: int, min_spread: float, exclude_usdjpy: bool = False, sl_atr: float = 0.75):
    """Family 2: Decomposed G6 Currency Strength Matrix (Strongest Currency vs Weakest Currency)."""
    trs, fds = [], []
    pool = [a for a in FX7 if not (exclude_usdjpy and a == "USDJPY")]
    for dk in all_days:
        if not all(dk in day_maps[a] for a in FX7):
            continue
        dsec = day_maps["USDJPY"][dk]["day_sec"]
        ts_e = dsec + entry_h * 3600
        ts_s = ts_e - lb_h * 3600
        z_map = {}
        for a in FX7:
            z = causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"])
            if z is not None:
                z_map[a] = z
        fac = compute_g6_factors(z_map)
        if not fac:
            continue
        scores = {a: fac[PAIR_CCY[a][0]] - fac[PAIR_CCY[a][1]] for a in pool}
        best_a = max(scores.keys(), key=lambda a: abs(scores[a]))
        sc = scores[best_a]
        if abs(sc) < min_spread:
            continue
        side = 1 if sc > 0 else -1
        tr, fd = market_entry_at(bundles[best_a], day_maps[best_a][dk], ts_e, side, sl_atr)
        if tr and fd:
            tr["chosen_asset"] = best_a
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def eval_idx_cross_leadlag(bundles: dict, day_maps: dict, all_days: list[str], *, kind: str, thr: float = 0.40, sl_atr: float = 0.75):
    """Family 3: Europe->US Lead-Lag (GER40 -> US100/US500) & US100 vs US500 Intraday Relative Strength."""
    trs, fds = [], []
    for dk in all_days:
        if kind.startswith("EU_LEAD_"):
            target = "US100" if "US100" in kind else "US500"
            if dk not in day_maps["GER40"] or dk not in day_maps[target]:
                continue
            gd, td = day_maps["GER40"][dk], day_maps[target][dk]
            # Strictly causal GER40 return from Berlin open to NYSE open (td["day_sec"] = 09:30 ET)
            z_ger = causal_z_return(bundles["GER40"], gd["day_sec"], td["day_sec"], gd["atr"])
            if z_ger is None or abs(z_ger) < thr:
                continue
            raw_side = 1 if z_ger > 0 else -1
            side = -raw_side if "FADE" in kind else raw_side
            tr, fd = market_entry_at(bundles[target], td, td["day_sec"] + 5 * 60, side, sl_atr)
            if tr and fd:
                trs.append(tr); fds.append(fd)

        elif kind in ("IDX_RS_US100_LEAD_1130", "IDX_RS_US500_CATCHUP_1130", "IDX_RS_BOTH_AGREE_US500_1130"):
            if dk not in day_maps["US100"] or dk not in day_maps["US500"]:
                continue
            d100, d500 = day_maps["US100"][dk], day_maps["US500"][dk]
            ts_s, ts_e = d100["day_sec"], d100["day_sec"] + 120 * 60  # 09:30 -> 11:30 ET
            z100 = causal_z_return(bundles["US100"], ts_s, ts_e, d100["atr"])
            z500 = causal_z_return(bundles["US500"], ts_s, ts_e, d500["atr"])
            if z100 is None or z500 is None:
                continue
            if kind == "IDX_RS_US100_LEAD_1130":
                diff = z100 - z500
                if abs(diff) < thr or (z100 * diff <= 0):
                    continue
                side = 1 if diff > 0 else -1
                tr, fd = market_entry_at(bundles["US100"], d100, ts_e, side, sl_atr)
            elif kind == "IDX_RS_US500_CATCHUP_1130":
                diff = z100 - z500
                if abs(diff) < thr or abs(z100) < 0.35:
                    continue
                side = 1 if z100 > 0 else -1
                tr, fd = market_entry_at(bundles["US500"], d500, ts_e, side, sl_atr)
            else:
                if abs(z100) < thr or abs(z500) < thr or (z100 * z500 <= 0):
                    continue
                side = 1 if z500 > 0 else -1
                # Breakout of morning high/low on US500 when BOTH US100 & US500 strongly agree!
                mq = bundles["US500"]["quotes"][d500["fi"]:int(bundles["US500"]["times"].searchsorted(ts_e, side="left"))]
                if len(mq) < 30:
                    continue
                mh, ml = float(mq[:, 1].max()), float(mq[:, 2].min())
                tr, fd = p24._scan_stop_breakout(bundles["US500"], d500, ts_e, d500["day_sec"] + 360 * 60, mh, ml, sl_atr * d500["atr"], ok_b=(side == 1), ok_s=(side == -1))
            if tr and fd:
                trs.append(tr); fds.append(fd)

        elif kind == "IDX_RS_GER40_NY_OPEN":
            if dk not in day_maps["US100"] or dk not in day_maps["GER40"]:
                continue
            d100, gd = day_maps["US100"][dk], day_maps["GER40"][dk]
            ts_s, ts_e = d100["day_sec"], d100["day_sec"] + 15 * 60  # First 15m of NYSE
            if ts_e >= int(bundles["GER40"]["times"][gd["flat_idx"]]) - 1800:
                continue
            z100 = causal_z_return(bundles["US100"], ts_s, ts_e, d100["atr"])
            if z100 is None or abs(z100) < thr:
                continue
            side = 1 if z100 > 0 else -1
            tr, fd = market_entry_at(bundles["GER40"], gd, ts_e, side, sl_atr)
            if tr and fd:
                trs.append(tr); fds.append(fd)
    return trs, fds


def eval_macro_gold_cross(bundles: dict, day_maps: dict, all_days: list[str], *, kind: str, thr: float = 0.35, sl_atr: float = 0.75):
    """Family 4: Intermarket Macro Signals for XAUUSD driven by real-time USD Basket & Risk-Off Peers."""
    trs, fds = [], []
    xb = bundles["XAUUSD"]
    for dk in all_days:
        if dk not in day_maps["XAUUSD"] or not all(dk in day_maps[a] for a in FX7):
            continue
        xd = day_maps["XAUUSD"][dk]
        dsec = xd["day_sec"]

        if kind == "XAU_EXP80_USD_CONF":
            # Daily-open 0.80 ATR breakout on XAUUSD ONLY if causal -USD basket agrees at trigger minute!
            open_0 = float(xb["quotes"][xd["fi"], 0])
            top, bot = open_0 + 0.80 * xd["atr"], open_0 - 0.80 * xd["atr"]
            sub_t = xb["times"][xd["fi"]:xd["flat_idx"] + 1]
            i0 = int(sub_t.searchsorted(dsec + 7 * 3600, side="left"))
            i1 = int(sub_t.searchsorted(dsec + 17 * 3600, side="left"))
            if i1 <= i0:
                continue
            scan = xb["quotes"][xd["fi"] + i0:xd["fi"] + i1]
            up = scan[:, 5] >= top - 1e-10
            dn = scan[:, 2] <= bot + 1e-10
            hits = np.flatnonzero(up | dn)
            if not len(hits):
                continue
            j = int(hits[0])
            if up[j] and dn[j]:
                continue
            side = 1 if up[j] else -1
            e_idx = xd["fi"] + i0 + j
            trig_ts = int(xb["times"][e_idx])
            # Strictly causal USD factor BEFORE trig_ts
            z_map = {a: causal_z_return(bundles[a], dsec, trig_ts, day_maps[a][dk]["atr"]) for a in FX7}
            if any(v is None for v in z_map.values()):
                continue
            usd_s = compute_g6_factors(z_map)["USD"]
            # BUY Gold requires USD weak (usd_s <= -thr); SELL Gold requires USD strong (usd_s >= +thr)
            if (side == 1 and usd_s > -thr) or (side == -1 and usd_s < thr):
                continue
            spr = max(0.0, float(xb["quotes"][e_idx, 4] - xb["quotes"][e_idx, 0]))
            ep = max(top, float(xb["quotes"][e_idx, 4])) if side == 1 else min(bot, float(xb["quotes"][e_idx, 0]))
            fep = (ep - spr) if side == 1 else (ep + spr)
            tr = p24.replay_causal_intraday("XAUUSD", xb["times"], xb["quotes"], e_idx, xd["flat_idx"], side, ep, ep - side * sl_atr * xd["atr"], spec=xb["spec"], usdjpy_close_map=xb["usdjpy_close_map"])
            fd = p24.replay_causal_intraday("XAUUSD", xb["times"], xb["quotes"], e_idx, xd["flat_idx"], -side, fep, fep + side * sl_atr * xd["atr"], spec=xb["spec"], usdjpy_close_map=xb["usdjpy_close_map"])
            if tr and fd:
                trs.append(tr); fds.append(fd)
            continue

        entry_h = 7 if "07U" in kind else 12
        lb_h = 7 if entry_h == 7 else 5
        ts_e = dsec + entry_h * 3600
        ts_s = ts_e - lb_h * 3600
        z_xau = causal_z_return(xb, ts_s, ts_e, xd["atr"])
        z_map = {a: causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"]) for a in FX7}
        if z_xau is None or any(v is None for v in z_map.values()):
            continue
        fac = compute_g6_factors(z_map)
        usd_s, jpy_s = fac["USD"], fac["JPY"]

        if kind.startswith("XAU_MACRO_CONF"):
            # Gold AND -USD basket strongly aligned
            if abs(z_xau) < thr or abs(usd_s) < 0.25 or (z_xau * (-usd_s) <= 0):
                continue
            side = 1 if z_xau > 0 else -1
        elif kind == "XAU_USD_LEADLAG_12U_40":
            # USD moved strongly while Gold lagged -> catch-up in -sign(USD)
            if abs(usd_s) < thr or abs(z_xau) > 0.30:
                continue
            side = -1 if usd_s > 0 else 1
        elif kind == "XAU_RISKOFF_CONF_12U":
            if dk not in day_maps["GER40"]:
                continue
            gd = day_maps["GER40"][dk]
            z_ger = causal_z_return(bundles["GER40"], gd["day_sec"], ts_e, gd["atr"])
            if z_ger is None:
                continue
            # Risk-off (Gold up + JPY up + GER40 down) or Risk-on symmetric
            if z_xau >= thr and jpy_s >= 0.20 and z_ger <= -0.25:
                side = 1
            elif z_xau <= -thr and jpy_s <= -0.20 and z_ger >= 0.25:
                side = -1
            else:
                continue
        else:
            continue

        tr, fd = market_entry_at(xb, xd, ts_e, side, sl_atr)
        if tr and fd:
            trs.append(tr); fds.append(fd)
    return trs, fds


def eval_peer_confirmed_breakout(bundles: dict, day_maps: dict, all_days: list[str], *, target: str, peer: str, peer_sign: int, trig_atr: float, peer_min_z: float = 0.25, sl_atr: float = 0.75):
    """Family 5: Daily-Open Expansion Breakout on `target` confirmed causally by `peer` asset before trigger minute."""
    trs, fds = [], []
    tb, pb = bundles[target], bundles[peer]
    for dk in all_days:
        if dk not in day_maps[target] or dk not in day_maps[peer]:
            continue
        td, pd = day_maps[target][dk], day_maps[peer][dk]
        dsec = td["day_sec"]
        open_0 = float(tb["quotes"][td["fi"], 0])
        top, bot = open_0 + trig_atr * td["atr"], open_0 - trig_atr * td["atr"]
        sub_t = tb["times"][td["fi"]:td["flat_idx"] + 1]
        ws = td["win_start_sec"]
        we = td["win_end_sec"]
        i0 = int(sub_t.searchsorted(ws, side="left"))
        i1 = int(sub_t.searchsorted(we, side="left"))
        if i1 <= i0:
            continue
        scan = tb["quotes"][td["fi"] + i0:td["fi"] + i1]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        e_idx = td["fi"] + i0 + j
        trig_ts = int(tb["times"][e_idx])
        # Strictly causal peer move from peer day_sec to strictly BEFORE trig_ts
        p_z = causal_z_return(pb, pd["day_sec"], trig_ts, pd["atr"])
        if p_z is None or (side * peer_sign * p_z) < peer_min_z:
            continue
        spr = max(0.0, float(tb["quotes"][e_idx, 4] - tb["quotes"][e_idx, 0]))
        ep = max(top, float(tb["quotes"][e_idx, 4])) if side == 1 else min(bot, float(tb["quotes"][e_idx, 0]))
        fep = (ep - spr) if side == 1 else (ep + spr)
        tr = p24.replay_causal_intraday(target, tb["times"], tb["quotes"], e_idx, td["flat_idx"], side, ep, ep - side * sl_atr * td["atr"], spec=tb["spec"], usdjpy_close_map=tb["usdjpy_close_map"])
        fd = p24.replay_causal_intraday(target, tb["times"], tb["quotes"], e_idx, td["flat_idx"], -side, fep, fep + side * sl_atr * td["atr"], spec=tb["spec"], usdjpy_close_map=tb["usdjpy_close_map"])
        if tr and fd:
            trs.append(tr); fds.append(fd)
    return trs, fds


def build_pass26_catalog() -> list[dict]:
    """Fixed preregistered 34-spec Cross-Asset / Intermarket catalog (5 orthogonal families, swap=0)."""
    return [
        # Family 1: FX_CS_MOMENTUM (8)
        {"id": "FX_TOP1_07U_LB6_Z30", "fam": "FX_CS_MOMENTUM", "entry_h": 7, "lb_h": 6, "min_z": 0.30, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_TOP1_07U_LB12_Z40", "fam": "FX_CS_MOMENTUM", "entry_h": 7, "lb_h": 12, "min_z": 0.40, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_TOP1_09U_LB6_Z30", "fam": "FX_CS_MOMENTUM", "entry_h": 9, "lb_h": 6, "min_z": 0.30, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_TOP1_12U_LB5_Z35", "fam": "FX_CS_MOMENTUM", "entry_h": 12, "lb_h": 5, "min_z": 0.35, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_TOP1_12U_LB5_Z50", "fam": "FX_CS_MOMENTUM", "entry_h": 12, "lb_h": 5, "min_z": 0.50, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_TOP1_12U_LB12_Z40", "fam": "FX_CS_MOMENTUM", "entry_h": 12, "lb_h": 12, "min_z": 0.40, "rev": False, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_REV1_12U_LB5_Z70", "fam": "FX_CS_MOMENTUM", "entry_h": 12, "lb_h": 5, "min_z": 0.70, "rev": True, "usd_only": False, "sl_atr": 0.75},
        {"id": "FX_USD_BASKET_12U_Z35", "fam": "FX_CS_MOMENTUM", "entry_h": 12, "lb_h": 5, "min_z": 0.35, "rev": False, "usd_only": True, "sl_atr": 0.75},
        # Family 2: CURRENCY_FACTOR_PAIRING (6)
        {"id": "CCY_MAT_07U_ALL_S40", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 7, "lb_h": 7, "min_s": 0.40, "no_jpy": False, "sl_atr": 0.75},
        {"id": "CCY_MAT_07U_NOJPY_S40", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 7, "lb_h": 7, "min_s": 0.40, "no_jpy": True, "sl_atr": 0.75},
        {"id": "CCY_MAT_12U_ALL_S40", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 12, "lb_h": 5, "min_s": 0.40, "no_jpy": False, "sl_atr": 0.75},
        {"id": "CCY_MAT_12U_ALL_S60", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 12, "lb_h": 5, "min_s": 0.60, "no_jpy": False, "sl_atr": 0.75},
        {"id": "CCY_MAT_12U_NOJPY_S40", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 12, "lb_h": 5, "min_s": 0.40, "no_jpy": True, "sl_atr": 0.75},
        {"id": "CCY_MAT_12U_NOJPY_S60", "fam": "CURRENCY_FACTOR_PAIRING", "entry_h": 12, "lb_h": 5, "min_s": 0.60, "no_jpy": True, "sl_atr": 0.75},
        # Family 3: IDX_CROSS_LEADLAG (8)
        {"id": "EU_LEAD_US100_MOM_40", "fam": "IDX_CROSS_LEADLAG", "kind": "EU_LEAD_US100_MOM", "thr": 0.40, "sl_atr": 0.75, "prov": True},
        {"id": "EU_LEAD_US100_MOM_60", "fam": "IDX_CROSS_LEADLAG", "kind": "EU_LEAD_US100_MOM", "thr": 0.60, "sl_atr": 0.75, "prov": True},
        {"id": "EU_LEAD_US500_MOM_40", "fam": "IDX_CROSS_LEADLAG", "kind": "EU_LEAD_US500_MOM", "thr": 0.40, "sl_atr": 0.75, "prov": False},
        {"id": "EU_LEAD_US100_FADE_60", "fam": "IDX_CROSS_LEADLAG", "kind": "EU_LEAD_US100_FADE", "thr": 0.60, "sl_atr": 0.75, "prov": True},
        {"id": "IDX_RS_US100_LEAD_1130", "fam": "IDX_CROSS_LEADLAG", "kind": "IDX_RS_US100_LEAD_1130", "thr": 0.25, "sl_atr": 0.75, "prov": True},
        {"id": "IDX_RS_US500_CATCHUP_1130", "fam": "IDX_CROSS_LEADLAG", "kind": "IDX_RS_US500_CATCHUP_1130", "thr": 0.25, "sl_atr": 0.75, "prov": False},
        {"id": "IDX_RS_BOTH_AGREE_US500_1130", "fam": "IDX_CROSS_LEADLAG", "kind": "IDX_RS_BOTH_AGREE_US500_1130", "thr": 0.35, "sl_atr": 0.65, "prov": False},
        {"id": "IDX_RS_GER40_NY_OPEN", "fam": "IDX_CROSS_LEADLAG", "kind": "IDX_RS_GER40_NY_OPEN", "thr": 0.25, "sl_atr": 0.65, "prov": True},
        # Family 4: MACRO_GOLD_CROSS (6)
        {"id": "XAU_MACRO_CONF_07U_35", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_MACRO_CONF_07U_35", "thr": 0.35, "sl_atr": 0.75},
        {"id": "XAU_MACRO_CONF_12U_35", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_MACRO_CONF_12U_35", "thr": 0.35, "sl_atr": 0.75},
        {"id": "XAU_MACRO_CONF_12U_50", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_MACRO_CONF_12U_50", "thr": 0.50, "sl_atr": 0.75},
        {"id": "XAU_USD_LEADLAG_12U_40", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_USD_LEADLAG_12U_40", "thr": 0.40, "sl_atr": 0.75},
        {"id": "XAU_EXP80_USD_CONF", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_EXP80_USD_CONF", "thr": 0.20, "sl_atr": 0.75},
        {"id": "XAU_RISKOFF_CONF_12U", "fam": "MACRO_GOLD_CROSS", "kind": "XAU_RISKOFF_CONF_12U", "thr": 0.30, "sl_atr": 0.75},
        # Family 5: INTERMARKET_CONFIRM_BREAKOUT (6)
        {"id": "EUR_CONF_GBP_EXP65", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "EURUSD", "peer": "GBPUSD", "ps": 1, "trig": 0.65, "pz": 0.25, "sl_atr": 0.75},
        {"id": "EUR_CONF_GBP_EXP80", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "EURUSD", "peer": "GBPUSD", "ps": 1, "trig": 0.80, "pz": 0.25, "sl_atr": 0.75},
        {"id": "AUD_CONF_XAU_USD_EXP65", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "AUDUSD", "peer": "XAUUSD", "ps": 1, "trig": 0.65, "pz": 0.25, "sl_atr": 0.75},
        {"id": "CAD_CONF_USD_EXP65", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "USDCAD", "peer": "EURUSD", "ps": -1, "trig": 0.65, "pz": 0.25, "sl_atr": 0.75},
        {"id": "GER40_CONF_EURJPY_EXP65", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "GER40", "peer": "EURJPY", "ps": 1, "trig": 0.65, "pz": 0.25, "sl_atr": 0.75, "prov": True},
        {"id": "GBP_CONF_EUR_EXP80", "fam": "INTERMARKET_CONFIRM_BREAKOUT", "target": "GBPUSD", "peer": "EURUSD", "ps": 1, "trig": 0.80, "pz": 0.25, "sl_atr": 0.75},
    ]


def eval_p26_spec(bundles: dict, day_maps: dict, all_days: list[str], cfg: dict):
    fam = cfg["fam"]
    if fam == "FX_CS_MOMENTUM":
        return eval_fx_cs_momentum(bundles, day_maps, all_days, entry_h=cfg["entry_h"], lb_h=cfg["lb_h"], min_z=cfg["min_z"], reverse=cfg["rev"], usd_basket_only=cfg["usd_only"], sl_atr=cfg["sl_atr"])
    if fam == "CURRENCY_FACTOR_PAIRING":
        return eval_ccy_matrix(bundles, day_maps, all_days, entry_h=cfg["entry_h"], lb_h=cfg["lb_h"], min_spread=cfg["min_s"], exclude_usdjpy=cfg["no_jpy"], sl_atr=cfg["sl_atr"])
    if fam == "IDX_CROSS_LEADLAG":
        return eval_idx_cross_leadlag(bundles, day_maps, all_days, kind=cfg["kind"], thr=cfg["thr"], sl_atr=cfg["sl_atr"])
    if fam == "MACRO_GOLD_CROSS":
        return eval_macro_gold_cross(bundles, day_maps, all_days, kind=cfg["kind"], thr=cfg["thr"], sl_atr=cfg["sl_atr"])
    if fam == "INTERMARKET_CONFIRM_BREAKOUT":
        return eval_peer_confirmed_breakout(bundles, day_maps, all_days, target=cfg["target"], peer=cfg["peer"], peer_sign=cfg["ps"], trig_atr=cfg["trig"], peer_min_z=cfg["pz"], sl_atr=cfg["sl_atr"])
    raise ValueError(f"Unknown family: {fam}")


def forensic_p26_survivor(bundles: dict, day_maps: dict, all_days: list[str], cfg: dict, core4_daily: dict[str, float]) -> dict:
    trs, fds = eval_p26_spec(bundles, day_maps, all_days, cfg)
    res = {
        "strategy": cfg["id"], "family": cfg["fam"], "n": len(trs),
        "cost_tiers": {
            "Base": round(fsum(t["base_R"] for t in trs), 2),
            "Stress": round(fsum(t["ftmo_R"] for t in trs), 2),
            "Double": round(fsum(t["double_R"] for t in trs), 2),
        },
        "fade_R": round(fsum(f["ftmo_R"] for f in fds), 2),
        "outlier": p23d.outlier_stress_trades(trs),
        "direction": p18.direction_breakdown(trs),
        "corr_4e": p18.daily_correlation(trs, core4_daily)["union_corr"],
    }
    fam = cfg["fam"]
    s1 = {}
    if fam == "FX_CS_MOMENTUM":
        for mz in (round(max(0.15, cfg["min_z"] - 0.10), 2), cfg["min_z"], round(cfg["min_z"] + 0.10, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p26_spec(bundles, day_maps, all_days, {**cfg, "min_z": mz, "sl_atr": sa})
                s1[f"z{mz:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "CURRENCY_FACTOR_PAIRING":
        for ms in (round(max(0.20, cfg["min_s"] - 0.15), 2), cfg["min_s"], round(cfg["min_s"] + 0.15, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p26_spec(bundles, day_maps, all_days, {**cfg, "min_s": ms, "sl_atr": sa})
                s1[f"s{ms:.2f}_sl{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam in ("IDX_CROSS_LEADLAG", "MACRO_GOLD_CROSS"):
        for th in (round(max(0.10, cfg["thr"] - 0.10), 2), cfg["thr"], round(cfg["thr"] + 0.10, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p26_spec(bundles, day_maps, all_days, {**cfg, "thr": th, "sl_atr": sa})
                s1[f"t{th:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    elif fam == "INTERMARKET_CONFIRM_BREAKOUT":
        for tr_v in (round(cfg["trig"] - 0.10, 2), cfg["trig"], round(cfg["trig"] + 0.10, 2)):
            for sa in (0.55, 0.75, 0.95):
                tt, _ = eval_p26_spec(bundles, day_maps, all_days, {**cfg, "trig": tr_v, "sl_atr": sa})
                s1[f"tr{tr_v:.2f}_s{sa:.2f}"] = {"A": wbd.split_metrics(tt, clock.CLUSTERS["A"])["net_R"], "B": wbd.split_metrics(tt, clock.CLUSTERS["B"])["net_R"]}
    res["surface_1"] = {"both_pos": sum(1 for v in s1.values() if v["A"] > 0 and v["B"] > 0), "total": len(s1), "cells": s1}
    res["trades"] = trs
    return res


def run_pass26(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, _bindings = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    all_assets = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY", "XAUUSD", "US500", "US100", "GER40")
    bundles = {a: p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map) for a in all_assets}
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in all_assets}
    all_days = sorted(day_maps["USDJPY"].keys())

    # 4-Engine Core Baseline (Pass 24: Calmar 1.08)
    core3_daily = p23d.build_3engine_daily_series(jobs_root, cache_dir, specs)
    u100_tr, _ = p24.eval_sess_continuation(bundles["US100"], min_move_atr=0.40, mode="BRK", sl_atr=0.65)
    core4_daily = defaultdict(float, core3_daily)
    for t in u100_tr:
        core4_daily[t["day"]] += float(t["ftmo_R"]) * 0.50
    core4_daily = dict(core4_daily)

    catalog = build_pass26_catalog()
    all_evals = []
    for cfg in catalog:
        trs, fds = eval_p26_spec(bundles, day_maps, all_days, cfg)
        all_evals.append((cfg, trs, fds))

    m_total = len(all_evals)
    p_all, stage1 = [], []
    for cfg, trs, fds in all_evals:
        mA = wbd.split_metrics(trs, clock.CLUSTERS["A"])
        passed_A = (mA["n"] >= 40 and mA["net_R"] > 0 and mA["pf"] >= 1.05)
        sf = p18.sign_flip_null_p(trs, fds, draws=MC_DRAWS) if (passed_A and trs) else {"gross_p": 1.0, "ftmo_net_p": 1.0}
        p_all.append(sf["ftmo_net_p"])
        stage1.append((cfg, trs, fds, mA, passed_A, sf))

    q_all = p14.benjamini_hochberg(p_all)
    survivors = []
    for (cfg, trs, fds, mA, passed_A, sf), q_full in zip(stage1, q_all):
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
        corr_4e = p18.daily_correlation(trs, core4_daily)["union_corr"]
        b_dir = p18.direction_breakdown(trs)
        prov = bool(cfg.get("prov", False))

        tier1_core = (
            len(trs) >= 120 and mB["net_R"] > 0 and tot_R > top10 and tot_R > fade_R
            and pos_yrs >= 5 and dd_R <= 15.0 and sf["ftmo_net_p"] < 0.05 and q_full <= 0.10
            and abs(corr_4e) <= 0.25
        )
        if tier1_core:
            tier = "TIER_1_FTMO_READY_PROVISIONAL_SPEC" if prov else "TIER_1_FTMO_READY"
        elif mB["net_R"] > 0 and tot_R > 0 and tot_R > fade_R and pos_yrs >= 4 and sf["ftmo_net_p"] < 0.10:
            tier = "TIER_2_PERSONAL_VAULT_PROVISIONAL_SPEC" if prov else "TIER_2_PERSONAL_VAULT"
        else:
            tier = "TIER_3_DEAD_NO_EDGE"

        survivors.append({
            "strategy": cfg["id"], "family": cfg["fam"], "provisional_spec": prov,
            "n_total": len(trs), "cluster_A": mA, "cluster_B_blind": mB,
            "ftmo_net_R": tot_R, "ftmo_base_R": base_R, "ftmo_double_R": dbl_R, "fade_ftmo_R": fade_R,
            "pos_years": pos_yrs, "years_R": yr_map, "closed_dd_R": dd_R, "top10_R": top10,
            "p_sign_flip": round(sf["ftmo_net_p"], 4), "fdr_q_full_space": round(q_full, 4),
            "corr_4e": corr_4e, "direction": b_dir, "tier": tier, "spec": cfg,
        })

    survivors.sort(key=lambda r: (0 if "TIER_1" in r["tier"] else (1 if "TIER_2" in r["tier"] else 2), -r["ftmo_net_R"]))
    tier_counts = dict(Counter(r["tier"] for r in survivors))
    tier_counts["STAGE1_FILTERED_OUT_ON_CLUSTER_A"] = m_total - len(survivors)

    print(f"\n=== PASS 26: CROSS-ASSET RS & INTERMARKET LEAD-LAG (m_total={m_total} across 11 synchronized M1 Bid/Ask assets) ===", flush=True)
    print(f"  Passed Cluster A Gate: {len(survivors)} / {m_total} | Tiers: {tier_counts}", flush=True)
    for r in survivors:
        print(
            f"  {r['strategy']:28s} ({r['family']:24s}) | n={r['n_total']:4d} "
            f"| A={r['cluster_A']['net_R']:+5.1f}R -> BLIND_B={r['cluster_B_blind']['net_R']:+5.1f}R "
            f"| Tot={r['ftmo_net_R']:+6.2f}R (B={r['ftmo_base_R']:+5.1f}, D={r['ftmo_double_R']:+5.1f}, yr+={r['pos_years']}/7, DD={r['closed_dd_R']:4.1f}R) "
            f"| p={r['p_sign_flip']:.3f} q={r['fdr_q_full_space']:.3f} | r4E={r['corr_4e']:+.3f} | {r['tier']}",
            flush=True,
        )

    # --- STAGE 3: DEEP FORENSIC ON ALL TIER_1 + TOP ORTHOGONAL TIER_2 (p < 0.03, |r4E| <= 0.25) ---
    targets = [r for r in survivors if "TIER_1" in r["tier"]]
    for r in survivors:
        if "TIER_2" in r["tier"] and r["p_sign_flip"] < 0.03 and abs(r["corr_4e"]) <= 0.25 and r not in targets:
            targets.append(r)

    forensic_reports = []
    qualified_engines = []
    if targets:
        print(f"\n=== STAGE 3: DEEP FORENSIC AUDIT ({len(targets)} target(s)) ===", flush=True)
        for cand in targets[:8]:
            frep = forensic_p26_survivor(bundles, day_maps, all_days, cand["spec"], core4_daily)
            tr_list = frep.pop("trades")
            s1 = frep["surface_1"]
            s1_ok = (s1["both_pos"] / max(1, s1["total"])) >= 0.50
            cost_ok = (frep["cost_tiers"]["Base"] > 0 and frep["cost_tiers"]["Stress"] > 0 and frep["cost_tiers"]["Double"] > 0)
            out_ok = (frep["outlier"]["drop_top3_R"] > 0 and frep["outlier"]["excl_both_crises_R"] > 0)
            frep["forensic_pass"] = bool(cost_ok and s1_ok and out_ok)
            forensic_reports.append(frep)
            print(
                f"  FORENSIC {cand['strategy']:28s} | tiers={frep['cost_tiers']} "
                f"| out(-T3={frep['outlier']['drop_top3_R']:+.1f}, -T5={frep['outlier']['drop_top5_R']:+.1f}, exCr={frep['outlier']['excl_both_crises_R']:+.1f}) "
                f"| s1={s1['both_pos']}/{s1['total']} | r4E={frep['corr_4e']:+.3f} "
                f"| dir=B:{frep['direction']['BUY']['ftmo_R']:+.1f}/S:{frep['direction']['SELL']['ftmo_R']:+.1f} | PASS={frep['forensic_pass']}",
                flush=True,
            )
            if frep["forensic_pass"]:
                qualified_engines.append((cand, tr_list))

    # --- STAGE 4: DUAL-FIRM 2-LAYER UPGRADE CHECK (PORT_4E -> PORT_5E / PORT_6E) ---
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

    def _overlay(base_n, base_d, base_f, extra_list, risk_pct=0.0050):
        n_arr, d_arr, f_arr = base_n.copy(), base_d.copy(), base_f.copy()
        r_usd = 10000.0 * risk_pct
        for trs in extra_list:
            by_d = defaultdict(list)
            for t in trs:
                by_d[t["day"]].append(t)
            for i, dk in enumerate(d_list):
                if dk in by_d:
                    n_arr[i] += fsum(t["ftmo_R"] * r_usd for t in by_d[dk])
                    d_arr[i] += fsum(t["mae_R"] * r_usd for t in by_d[dk])
                    f_arr[i] = 1
        return n_arr, d_arr, f_arr

    nets4_10k, dds4_10k, flags4 = _overlay(nets3_10k, dds3_10k, flags3, [u100_tr], 0.0050)
    port_series = {"PORT_4E_BASE": (nets4_10k, dds4_10k, flags4)}

    picked_fams = set()
    picked = []
    for cand, tr_list in qualified_engines:
        if cand["family"] not in picked_fams:
            picked_fams.add(cand["family"])
            picked.append((cand, tr_list))

    for cand, tr_list in picked[:4]:
        port_series[f"PORT5E_PLUS_{cand['strategy']}"] = _overlay(nets4_10k, dds4_10k, flags4, [tr_list], 0.0050)
    if len(picked) >= 2:
        port_series[f"PORT{4+len(picked)}E_ALL_QUALIFIED_R50"] = _overlay(nets4_10k, dds4_10k, flags4, [tl for _, tl in picked], 0.0050)

    dual_firm_eval = {}
    print("\n=== STAGE 4: DUAL-FIRM 2-LAYER UPGRADE CHECK (PORT_4E -> PORT_5E/6E · FTMO 10K vs THE5ERS 5K) ===", flush=True)
    for pname, (n10, d10, flg) in port_series.items():
        eq = np.cumsum(np.insert(n10, 0, 10000.0))
        peak_dd = float(np.max((np.maximum.accumulate(eq[:-1]) - (eq[:-1] - d10)) / 10000.0) * 100.0)
        ann = float((eq[-1] - 10000.0) / 10000.0 / 7.0 * 100.0)
        ann_A = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk < "2021-01-01") / 10000.0 / 3.0 * 100.0)
        ann_B = float(fsum(n10[i] for i, dk in enumerate(d_list) if dk >= "2021-01-01") / 10000.0 / 4.0 * 100.0)
        cal = round(ann / peak_dd, 2) if peak_dd > 1e-9 else 0.0
        print(f"\n  [{pname}] 7y Ann={ann:+.2f}% (A={ann_A:+.2f}%, B={ann_B:+.2f}%) | PeakDD={peak_dd:.2f}% | Calmar={cal:.2f}", flush=True)
        dual_firm_eval[pname] = {"ann_pct": round(ann, 2), "ann_A": round(ann_A, 2), "ann_B": round(ann_B, 2), "peak_dd_pct": round(peak_dd, 2), "calmar": cal, "firms": {}}
        for firm, cap, fee, scale in (("FTMO_SWING_10K", 10000.0, 168.0, 1.0), ("THE5ERS_HS_5K", 5000.0, 39.0, 0.5)):
            dual_firm_eval[pname]["firms"][firm] = {}
            for pol_name, p1m, p2m, fm, dyn in (
                ("Flat_Safe_1.0", 1.0, 1.0, 1.0, False),
                ("2Layer_Cap1Pct_Dyn", 1.33, 1.0, 1.0, True),
                ("2Layer_Mod_2.0_Dyn", 2.0, 1.25, 1.0, True),
            ):
                r = p24.simulate_dual_firm_2layer(n10 * scale, d10 * scale, flg, firm=firm, cap=cap, fee=fee, p1_m=p1m, p2_m=p2m, fund_m=fm, dynamic=dyn)
                dual_firm_eval[pname]["firms"][firm][pol_name] = r
                pp = r["pass_pct"]
                print(
                    f"    {firm:14s} | {pol_name:18s} | 3/6/9/12/24m={pp['3m']:4.1f}/{pp['6m']:4.1f}/{pp['9m']:4.1f}/{pp['12m']:4.1f}/{pp['24m']:4.1f}% "
                    f"| Br1={r['br1_pct']:4.1f}% Tix={r['avg_tickets']:.2f} Med={str(r['med_pass_m']):>4s}m "
                    f"| CF12=${r['cf12_mean']:+5.0f} CF24=${r['cf24_mean']:+6.0f} (P>0={r['cf24_pos_pct']:4.1f}%)",
                    flush=True,
                )

    return {
        "pass": "Pass 26 (Cross-Asset Relative Strength & Intermarket Lead-Lag)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "m_total_search_space": m_total,
        "cluster_a_survivors": len(survivors),
        "tier_counts": tier_counts,
        "survivors": survivors,
        "forensic_reports": forensic_reports,
        "qualified_engines": [c["strategy"] for c, _ in picked],
        "dual_firm_eval": dual_firm_eval,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass26(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass26-result.json", res)
    print("\nPASS26_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
