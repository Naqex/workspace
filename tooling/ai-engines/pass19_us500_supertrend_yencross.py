"""Pass 19: US500 Overnight/Short-Swing (exact FTMO swap), Clean-Room SuperTrend(10,3), and Stage-0 Yen-Cross/Carry Scout."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np
import pyarrow.parquet as pq

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass14_intel_top15_batch as p14
import pass18_opensource_non_usdjpy as p18
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import commission, profiles, rollovers

PROTOCOL = "87c5a3fef7303c0b4cc84f4eefdb085970a92273"
SEED = 20261123
MC_DRAWS = 1000


# ==============================================================================
# INDICATORS (100% CAUSAL)
# ==============================================================================

def wilder_rsi(closes: np.ndarray, n: int = 2) -> np.ndarray:
    out = np.full(len(closes), np.nan, dtype=np.float64)
    if len(closes) <= n:
        return out
    diff = np.diff(closes)
    gains = np.where(diff > 0, diff, 0.0)
    losses = np.where(diff < 0, -diff, 0.0)
    ag = float(gains[:n].mean())
    al = float(losses[:n].mean())
    out[n] = 100.0 if al == 0 else (100.0 - 100.0 / (1.0 + ag / al))
    for i in range(n, len(diff)):
        ag = (ag * (n - 1) + gains[i]) / n
        al = (al * (n - 1) + losses[i]) / n
        out[i + 1] = 100.0 if al == 0 else (100.0 - 100.0 / (1.0 + ag / al))
    return out


def supertrend(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, period: int = 10, mult: float = 3.0):
    """Standard causal SuperTrend(period, mult). Returns (direction: int8[N] in {-1,0,1}, band: float64[N], atr: float64[N])."""
    n = len(closes)
    atr = p14.wilder_atr(highs, lows, closes, period)
    direction = np.zeros(n, dtype=np.int8)
    band = np.full(n, np.nan, dtype=np.float64)
    upper = np.full(n, np.nan, dtype=np.float64)
    lower = np.full(n, np.nan, dtype=np.float64)

    for i in range(period - 1, n):
        if not np.isfinite(atr[i]):
            continue
        hl2 = 0.5 * (highs[i] + lows[i])
        b_up = hl2 + mult * atr[i]
        b_dn = hl2 - mult * atr[i]
        if i == period - 1 or not np.isfinite(upper[i - 1]):
            upper[i] = b_up
            lower[i] = b_dn
            direction[i] = 1 if closes[i] >= hl2 else -1
        else:
            upper[i] = b_up if (b_up < upper[i - 1] or closes[i - 1] > upper[i - 1]) else upper[i - 1]
            lower[i] = b_dn if (b_dn > lower[i - 1] or closes[i - 1] < lower[i - 1]) else lower[i - 1]
            if direction[i - 1] == 1:
                direction[i] = -1 if closes[i] < lower[i] else 1
            else:
                direction[i] = 1 if closes[i] > upper[i] else -1
        band[i] = lower[i] if direction[i] == 1 else upper[i]
    return direction, band, atr


# ==============================================================================
# TRACK 1: US500 OVERNIGHT & SHORT-SWING ON NATIVE M1 BID/ASK (EXACT FTMO SWAP)
# ==============================================================================

def sim_us500_multiday_m1(
    times: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    exit_cap_idx: int,
    side: int,
    sl_pts: float,
    us_spec: dict,
    *,
    day_key: str,
    year: int,
    slip_side: float = 0.75,
) -> dict | None:
    """Exact multi-day M1 Bid/Ask replay on US500 with real FTMO Swing swap (swapL=-138.03, swapS=-36.37, 3day=Fri)."""
    if entry_idx < 0 or exit_cap_idx <= entry_idx or sl_pts <= 0:
        return None
    entry_ts = int(times[entry_idx])
    if entry_ts >= STOP - 60:
        return None
    entry_p = float(quotes[entry_idx, 4] if side == 1 else quotes[entry_idx, 0])
    sl_p = entry_p - side * sl_pts

    liq = quotes[entry_idx:exit_cap_idx + 1, :4] if side == 1 else quotes[entry_idx:exit_cap_idx + 1, 4:8]
    adverse = liq[:-1, 2 if side == 1 else 1]
    hits = np.flatnonzero(side * (adverse - sl_p) <= 1e-10)
    if len(hits):
        k = int(hits[0])
        op = float(liq[k, 0])
        gap = k > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        reason = "SL_GAP_OR_TOUCH"
        exit_idx = entry_idx + k
    else:
        ex_p = float(liq[-1, 0])
        reason = "TIME_EXIT"
        exit_idx = exit_cap_idx

    exit_ts = int(times[exit_idx])
    assert START <= entry_ts <= exit_ts < STOP

    gross = side * (ex_p - entry_p)  # US500.cash cs=1.0 -> $1/point
    ftmo_swap, n1, n3 = p14.swap_usd_per_lot("US500.cash", entry_ts, exit_ts, side, us_spec, ex_p)
    net_stress = gross - 2.0 * slip_side + ftmo_swap
    risk_stress = sl_pts + 2.0 * slip_side
    net_base = gross - 0.50 + ftmo_swap
    risk_base = sl_pts + 0.50
    net_swapfree = gross - 0.50  # Exness Swap-Free diagnostic
    return {
        "day": day_key, "year": year, "side": side, "reason": reason,
        "entry": entry_ts, "exit": exit_ts, "hold_hours": max(0.5, (exit_ts - entry_ts) / 3600.0),
        "gross_usd": gross, "ftmo_comm_slip": 2.0 * slip_side, "ftmo_swap": ftmo_swap,
        "ftmo_n1": n1, "ftmo_n3": n3,
        "ftmo_net": net_stress, "ftmo_R": net_stress / risk_stress,
        "base_R": net_base / risk_base,
        "ex_R_normal": net_base / risk_base,
        "ex_R_swapfree": net_swapfree / risk_base,
    }


def timing_permutation_p(all_day_nets: list[float], selected_mask: list[bool], *, draws: int = MC_DRAWS) -> float:
    """Does picking the signal days beat picking the exact same number of random days LONG (eliminates S&P drift illusion)?"""
    arr = np.array(all_day_nets, dtype=np.float64)
    mask = np.array(selected_mask, dtype=bool)
    k = int(mask.sum())
    if k == 0 or k >= len(arr):
        return 1.0
    obs = float(arr[mask].sum())
    rng = np.random.default_rng(SEED + 190)
    ge = 0
    for _ in range(draws):
        idx = rng.choice(len(arr), size=k, replace=False)
        if float(arr[idx].sum()) >= obs:
            ge += 1
    return float((ge + 1) / (draws + 1))


def run_track1_us500_overnight(cache_dir: Path, us_spec: dict, core_daily: dict[str, float]) -> dict:
    t0 = time.monotonic()
    times, quotes, _ = hcache.load_asset("US500", cache_dir, verify_sha=True)
    sessions, atr = p18.build_us500_sessions(times, quotes)
    closes = np.array([s["c"] for s in sessions], dtype=np.float64)
    highs = np.array([s["h"] for s in sessions], dtype=np.float64)
    lows = np.array([s["l"] for s in sessions], dtype=np.float64)
    sma200 = p14.sma(closes, 200)
    rsi2 = wilder_rsi(closes, 2)

    # Pre-locate exact M1 index for 09:35 ET (off=5) and 15:50 ET (off=380) of each session
    idx_0935, idx_1550 = [], []
    for s in sessions:
        lo, hi = s["lo"], s["hi"]
        offs = (times[lo:hi] - s["start"]) // 60
        j_open = int(offs.searchsorted(5, side="left"))
        j_close = int(offs.searchsorted(380, side="left"))
        idx_0935.append(lo + min(j_open, len(offs) - 1))
        idx_1550.append(lo + min(j_close, len(offs) - 1))

    strats = {
        k: ([], []) for k in (
            "US500_IBS_OVERNIGHT_LONG", "US500_IBS_NEXT_OPEN_LONG", "US500_IBS_TWO_SIDED",
            "US500_RSI2_PULLBACK_LONG", "US500_OVERNIGHT_DRIFT_MON_THU", "US500_DOWN_DAY_OVERNIGHT_LONG",
        )
    }
    # For drift-adjusted timing permutation test: record unconditional 1-night & 1-day LONG net on every eligible day
    pool_next_open_net, mask_ibs_open, mask_down_open, mask_monthu_open = [], [], [], []
    pool_next_close_net, mask_ibs_close = [], []

    for i in range(15, len(sessions) - 1):
        s = sessions[i]
        a_val = atr[i]  # Known at 15:50 ET (session i OHLC completed up to 15:50; use prior-bar atr[i-1] to stay 100% strictly prior-day causal!)
        a_val = atr[i - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        ent_i = idx_1550[i]
        # Compute session i IBS / body strictly up to ent_i (15:50 ET, zero future info!)
        sub_q = quotes[s["lo"]:ent_i + 1]
        cur_o = float(sub_q[0, 0])
        cur_h = float(sub_q[:, 1].max())
        cur_l = float(sub_q[:, 2].min())
        cur_c = float(sub_q[-1, 0])
        rng = cur_h - cur_l
        ibs = (cur_c - cur_l) / rng if rng > 1e-9 else 0.5
        wd = datetime.strptime(s["day"], "%Y-%m-%d").weekday()  # 0=Mon..4=Fri

        ex_open = idx_0935[i + 1]
        ex_close = idx_1550[i + 1]

        # Benchmark trades for timing permutation null
        bm_open = sim_us500_multiday_m1(times, quotes, ent_i, ex_open, 1, 1.00 * a_val, us_spec, day_key=s["day"], year=s["year"])
        bm_close = sim_us500_multiday_m1(times, quotes, ent_i, ex_close, 1, 1.25 * a_val, us_spec, day_key=s["day"], year=s["year"])
        if bm_open is not None:
            pool_next_open_net.append(bm_open["ftmo_net"])
            is_ibs = ibs <= 0.20
            is_down = (cur_c - cur_o) <= -0.50 * a_val
            is_mt = wd <= 3
            mask_ibs_open.append(is_ibs)
            mask_down_open.append(is_down)
            mask_monthu_open.append(is_mt)
            fd_open = sim_us500_multiday_m1(times, quotes, ent_i, ex_open, -1, 1.00 * a_val, us_spec, day_key=s["day"], year=s["year"])
            if fd_open is not None:
                if is_ibs:
                    strats["US500_IBS_NEXT_OPEN_LONG"][0].append(bm_open)
                    strats["US500_IBS_NEXT_OPEN_LONG"][1].append(fd_open)
                if is_mt:
                    strats["US500_OVERNIGHT_DRIFT_MON_THU"][0].append(bm_open)
                    strats["US500_OVERNIGHT_DRIFT_MON_THU"][1].append(fd_open)
                if is_down:
                    strats["US500_DOWN_DAY_OVERNIGHT_LONG"][0].append(bm_open)
                    strats["US500_DOWN_DAY_OVERNIGHT_LONG"][1].append(fd_open)

        if bm_close is not None:
            pool_next_close_net.append(bm_close["ftmo_net"])
            is_ibs = ibs <= 0.20
            mask_ibs_close.append(is_ibs)
            fd_close = sim_us500_multiday_m1(times, quotes, ent_i, ex_close, -1, 1.25 * a_val, us_spec, day_key=s["day"], year=s["year"])
            if fd_close is not None:
                if is_ibs:
                    strats["US500_IBS_OVERNIGHT_LONG"][0].append(bm_close)
                    strats["US500_IBS_OVERNIGHT_LONG"][1].append(fd_close)
                    strats["US500_IBS_TWO_SIDED"][0].append(bm_close)
                    strats["US500_IBS_TWO_SIDED"][1].append(fd_close)
                elif ibs >= 0.80:
                    strats["US500_IBS_TWO_SIDED"][0].append(fd_close)
                    strats["US500_IBS_TWO_SIDED"][1].append(bm_close)

        # 4. US500_RSI2_PULLBACK_LONG (strictly causal: uses closes[i-1]/sma200[i-1]/rsi2[i-1] or close up to 15:50 ET)
        if i >= 200 and np.isfinite(sma200[i - 1]) and cur_c > sma200[i - 1]:
            # Compute causal 2-bar RSI using cur_c as bar i close
            # (Approximated cleanly via precomputed rsi2[i] since 15:50 vs 15:55 differs by 5 min; use strictly rsi2[i-1] on prior bar + red day check? Better: exact causal RSI2 up to cur_c!)
            prev_c1, prev_c2 = closes[i - 1], closes[i - 2]
            d1, d2 = prev_c1 - prev_c2, cur_c - prev_c1
            g1, l1 = max(d1, 0.0), max(-d1, 0.0)
            g2, l2 = max(d2, 0.0), max(-d2, 0.0)
            ag = 0.5 * g1 + 0.5 * g2
            al = 0.5 * l1 + 0.5 * l2
            cur_rsi2 = 100.0 if al == 0 else (100.0 - 100.0 / (1.0 + ag / al))
            if cur_rsi2 <= 15.0:
                # Find exit: first subsequent day d in {i+1, i+2, i+3} where Close_15:50 > High_{d-1}, else i+3
                ex_i = min(i + 3, len(sessions) - 1)
                for step in range(1, 4):
                    if i + step >= len(sessions):
                        break
                    chk_idx = idx_1550[i + step]
                    if float(quotes[chk_idx, 0]) > highs[i + step - 1]:
                        ex_i = i + step
                        break
                tr_r = sim_us500_multiday_m1(times, quotes, ent_i, idx_1550[ex_i], 1, 1.50 * a_val, us_spec, day_key=s["day"], year=s["year"])
                fd_r = sim_us500_multiday_m1(times, quotes, ent_i, idx_1550[ex_i], -1, 1.50 * a_val, us_spec, day_key=s["day"], year=s["year"])
                if tr_r and fd_r:
                    strats["US500_RSI2_PULLBACK_LONG"][0].append(tr_r)
                    strats["US500_RSI2_PULLBACK_LONG"][1].append(fd_r)

    timing_p_map = {
        "US500_IBS_OVERNIGHT_LONG": timing_permutation_p(pool_next_close_net, mask_ibs_close),
        "US500_IBS_NEXT_OPEN_LONG": timing_permutation_p(pool_next_open_net, mask_ibs_open),
        "US500_IBS_TWO_SIDED": None,
        "US500_RSI2_PULLBACK_LONG": None,
        "US500_OVERNIGHT_DRIFT_MON_THU": timing_permutation_p(pool_next_open_net, mask_monthu_open),
        "US500_DOWN_DAY_OVERNIGHT_LONG": timing_permutation_p(pool_next_open_net, mask_down_open),
    }

    rows = []
    for sid, (trs, fds) in strats.items():
        sf = p18.sign_flip_null_p(trs, fds)
        mc_eff = {
            "gross_p_value": sf["gross_p"], "ftmo_net_p_value": sf["ftmo_net_p"],
            "timing_perm_p": timing_p_map[sid],
        }
        r = p14.summarize_pair(sid, "US500", True, trs, mc_eff)
        r["ftmo_base_R"] = round(fsum(t["base_R"] for t in trs), 2)
        r["ftmo_swap_total_usd"] = round(fsum(t["ftmo_swap"] for t in trs), 2)
        r["ftmo_gross_total_usd"] = round(fsum(t["gross_usd"] for t in trs), 2)
        r["fade_ftmo_R"] = round(fsum(t["ftmo_R"] for t in fds), 2)
        r["direction"] = p18.direction_breakdown(trs)
        r["corr_usdjpy_core"] = p18.daily_correlation(trs, core_daily)
        rows.append(r)

    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] for r in rows])
    print("\n=== TRACK 1: US500 OVERNIGHT & SHORT-SWING (EXACT FTMO SWAP, m=6 BH FDR) ===", flush=True)
    for r, qf in zip(rows, q_f):
        r["fdr_ftmo_q"] = qf
        if r["tier"] == "TIER_1_FTMO_READY" and (qf > 0.10 or r["ftmo_net_R"] <= r["fade_ftmo_R"]):
            r["tier"] = "TIER_2_PERSONAL_VAULT"
        pf = r["mc_null"]["ftmo_net_p_value"]
        tp = r["mc_null"]["timing_perm_p"]
        tp_s = f"{tp:.3f}" if tp is not None else "n/a  "
        print(
            f"  {r['strategy']:30s} | n={r['n']:4d} | FTMO={r.get('ftmo_net_R',0):+6.2f}R Base={r['ftmo_base_R']:+6.2f}R ExSF={r.get('exness_swapfree_R',0):+6.2f}R "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7 DD={r.get('ftmo_closed_dd_R',0):.1f}R) "
            f"| Swap=${r['ftmo_swap_total_usd']:+.0f} | Fade={r['fade_ftmo_R']:+6.1f} | p_sf={pf:.3f}(q={qf:.3f}) p_tm={tp_s} | rJPY={r['corr_usdjpy_core']['union_corr']} | {r['tier']}",
            flush=True,
        )
    return {
        "track": "Track1_US500_Overnight_ShortSwing",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows,
    }


# ==============================================================================
# TRACK 2: CLEAN-ROOM SUPERTREND(10,3.0) RETRACEMENT + STEP-TRAILING (5 M1 ASSETS)
# ==============================================================================

def replay_step_trailing_m1(
    asset: str, times: np.ndarray, quotes: np.ndarray, entry_idx: int, side: int,
    entry_p: float, init_sl: float, max_exit_sec: int, spec: dict, *, is_us500: bool = False,
) -> dict | None:
    """Exact M1 replay with step-trailing stop (+1.0R -> lock +0.5R, +1.5R -> +1.0R, ...), SL-first conservative, swap=0."""
    risk_p = side * (entry_p - init_sl)
    if risk_p <= 0:
        return None
    entry_ts = int(times[entry_idx])
    cap_sec = min(max_exit_sec, STOP - 60)
    hi_idx = int(times.searchsorted(cap_sec, side="right")) - 1
    if hi_idx <= entry_idx:
        return None
    liq = quotes[entry_idx:hi_idx + 1, :4] if side == 1 else quotes[entry_idx:hi_idx + 1, 4:8]
    cur_sl = init_sl
    best_step = 0
    ex_rel = len(liq) - 1
    ex_p = float(liq[-1, 3])
    reason = "TIME_FLAT"

    for k in range(len(liq)):
        op, hi_b, lo_b = float(liq[k, 0]), float(liq[k, 1]), float(liq[k, 2])
        # 1. Conservative SL-first check BEFORE updating trailing SL on bar k
        if side == 1 and lo_b <= cur_sl + 1e-10:
            ex_p = op if (k > 0 and op <= cur_sl + 1e-10) else cur_sl
            ex_rel = k
            reason = "TRAIL_SL" if cur_sl > init_sl + 1e-10 else "SL_GAP_OR_TOUCH"
            break
        if side == -1 and hi_b >= cur_sl - 1e-10:
            ex_p = op if (k > 0 and op >= cur_sl - 1e-10) else cur_sl
            ex_rel = k
            reason = "TRAIL_SL" if cur_sl < init_sl - 1e-10 else "SL_GAP_OR_TOUCH"
            break
        # 2. Update step-trailing SL at bar end (activates at +1.0R, trails 0.5R in 0.5R steps)
        fav = (hi_b - entry_p) / risk_p if side == 1 else (entry_p - lo_b) / risk_p
        if fav >= 1.0:
            step = int((fav - 1.0) // 0.5) + 1  # step=1 at 1.0R -> lock +0.5R
            if step > best_step:
                best_step = step
                cur_sl = entry_p + side * (0.5 * best_step) * risk_p

    exit_idx = entry_idx + ex_rel
    exit_ts = int(times[exit_idx])
    assert START <= entry_ts <= exit_ts < STOP
    dkey = datetime.fromtimestamp(entry_ts, timezone.utc).date().isoformat()
    yr = datetime.fromtimestamp(entry_ts, timezone.utc).year

    if is_us500:
        gross = side * (ex_p - entry_p)
        net_s = gross - 1.50
        risk_s = risk_p + 1.50
        net_b = gross - 0.50
        risk_b = risk_p + 0.50
        return {
            "day": dkey, "year": yr, "side": side, "reason": reason,
            "entry": entry_ts, "exit": exit_ts, "hold_hours": max(0.25, (exit_ts - entry_ts) / 3600.0),
            "gross_usd": gross, "ftmo_comm_slip": 1.50, "ftmo_swap": 0.0,
            "ftmo_net": net_s, "ftmo_R": net_s / risk_s, "base_R": net_b / risk_b,
            "ex_R_normal": net_b / risk_b, "ex_R_swapfree": net_b / risk_b,
        }

    f_cfg = p14.ftmo_stress_params(asset)
    gross_usd = p14.price_to_usd_per_lot(asset, side * (ex_p - entry_p), ex_p, spec)
    ftmo_comm = commission(asset, spec, entry_p) + commission(asset, spec, ex_p)
    ftmo_slip = p14.price_to_usd_per_lot(asset, f_cfg["slip_rt"], ex_p, spec)
    ftmo_net = gross_usd - ftmo_comm - ftmo_slip
    ftmo_risk = p14.price_to_usd_per_lot(asset, risk_p, entry_p, spec) + ftmo_comm + ftmo_slip
    if ftmo_risk <= 0:
        return None
    addon_p = 0.20 if asset == "XAUUSD" else (0.005 if asset == "USDJPY" else 0.00005)
    addon_usd = p14.price_to_usd_per_lot(asset, addon_p, ex_p, spec)
    e_cfg = p14.exness_ref_params(asset)
    spread_adj = (f_cfg["spread_proxy"] - e_cfg["spread_proxy"]) * float(spec["trade_contract_size"]) if asset == "XAUUSD" else 0.0
    ex_slip = p14.price_to_usd_per_lot(asset, e_cfg["slip_rt"], ex_p, spec)
    ex_net = gross_usd + spread_adj - e_cfg["comm_rt"] - ex_slip
    ex_risk = p14.price_to_usd_per_lot(asset, risk_p, entry_p, spec) + e_cfg["comm_rt"] + ex_slip
    return {
        "day": dkey, "year": yr, "side": side, "reason": reason,
        "entry": entry_ts, "exit": exit_ts, "hold_hours": max(0.25, (exit_ts - entry_ts) / 3600.0),
        "gross_usd": gross_usd, "ftmo_comm_slip": ftmo_comm + ftmo_slip, "ftmo_swap": 0.0,
        "ftmo_net": ftmo_net, "ftmo_R": ftmo_net / ftmo_risk,
        "base_R": (ftmo_net + addon_usd) / max(1e-9, ftmo_risk - addon_usd),
        "ex_R_normal": ex_net / ex_risk, "ex_R_swapfree": ex_net / ex_risk,
    }


def run_supertrend_asset(asset: str, jobs_root: Path, cache_dir: Path, spec: dict):
    is_us = (asset == "US500")
    if is_us:
        times, quotes, meta = hcache.load_asset("US500", cache_dir, verify_sha=True)
        bid4 = quotes[:, :4]
        h1 = p14.resample_bars(times, bid4, 3600, min_bars=25)
        sessions, d1_atr = p18.build_us500_sessions(times, quotes)
        day_atr_map = {sessions[i]["day"]: float(d1_atr[i - 1]) for i in range(15, len(sessions)) if np.isfinite(d1_atr[i - 1])}
        day_end_map = {s["day"]: int(times[s["hi"] - 1]) for s in sessions}
        ctx = None
    else:
        ctx = p14.build_asset_context(jobs_root, asset, cache_dir, spec)
        times, quotes, meta, h1 = ctx["times"], ctx["quotes"], ctx["meta"], ctx["h1"]
        day_atr_map = {
            ctx["full_d1"][i]["date"].isoformat(): float(ctx["d1_atr"][i - 1])
            for i in range(ctx["d1_offset"], len(ctx["full_d1"])) if np.isfinite(ctx["d1_atr"][i - 1])
        }
        day_end_map = {}

    h1_h = np.array([b["h"] for b in h1], dtype=np.float64)
    h1_l = np.array([b["l"] for b in h1], dtype=np.float64)
    h1_c = np.array([b["c"] for b in h1], dtype=np.float64)
    st_dir, st_band, st_atr = supertrend(h1_h, h1_l, h1_c, period=10, mult=3.0)
    h1_ema20 = p14.ema(h1_c, 20)

    trades, fades = [], []
    traded_days = set()
    for i in range(30, len(h1) - 1):
        d = int(st_dir[i])
        if d == 0 or not np.isfinite(st_atr[i]) or not np.isfinite(h1_ema20[i]) or st_atr[i] <= 0:
            continue
        # Next bar start (strictly causal: decision made after H1 bar i closes)
        nxt = h1[i + 1]
        dt_nxt = datetime.fromtimestamp(nxt["start_sec"], timezone.utc)
        dkey = dt_nxt.date().isoformat()
        if dkey in traded_days or dkey not in day_atr_map:
            continue
        if is_us:
            if not (14 <= dt_nxt.hour <= 19) or dkey not in day_end_map:
                continue
            t_flat = day_end_map[dkey]
        else:
            if not (7 <= dt_nxt.hour <= 16):
                continue
            t_flat = int(datetime(dt_nxt.year, dt_nxt.month, dt_nxt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if nxt["start_sec"] >= t_flat:
            continue

        # Causal retracement condition on completed H1 bar i
        if d == 1:
            retraced = (h1_l[i] <= st_band[i] + 0.50 * st_atr[i]) or (h1_c[i] < h1_ema20[i] and h1_c[i] > st_band[i])
            trig = h1_h[i]
        else:
            retraced = (h1_h[i] >= st_band[i] - 0.50 * st_atr[i]) or (h1_c[i] > h1_ema20[i] and h1_c[i] < st_band[i])
            trig = h1_l[i]
        if not retraced:
            continue

        # Scan next 60 M1 bars for stop-order breakout of bar i high/low
        fi, ei = nxt["fi"], nxt["ei"]
        scan = quotes[fi:ei]
        hits = np.flatnonzero(scan[:, 5] >= trig - 1e-10) if d == 1 else np.flatnonzero(scan[:, 2] <= trig + 1e-10)
        if not len(hits):
            continue
        e_idx = fi + int(hits[0])
        ep = max(trig, float(quotes[e_idx, 4])) if d == 1 else min(trig, float(quotes[e_idx, 0]))
        fep = float(quotes[e_idx, 4] if d == -1 else quotes[e_idx, 0])
        sl_dist = max(1.00 * float(st_atr[i]), 0.35 * day_atr_map[dkey])

        tr = replay_step_trailing_m1(asset, times, quotes, e_idx, d, ep, ep - d * sl_dist, t_flat, spec, is_us500=is_us)
        fd = replay_step_trailing_m1(asset, times, quotes, e_idx, -d, fep, fep + d * sl_dist, t_flat, spec, is_us500=is_us)
        if tr and fd:
            trades.append(tr)
            fades.append(fd)
            traded_days.add(dkey)
    return trades, fades, bool(meta["native_Ask"]), ctx


def run_track2_supertrend(jobs_root: Path, cache_dir: Path, specs: dict, core_daily: dict[str, float]) -> dict:
    t0 = time.monotonic()
    rows = []
    for asset in ("USDJPY", "EURUSD", "GBPUSD", "US500", "XAUUSD"):
        sp = specs["Swing"]["US500.cash" if asset == "US500" else asset]
        trs, fds, native_ask, ctx = run_supertrend_asset(asset, jobs_root, cache_dir, sp)
        sf = p18.sign_flip_null_p(trs, fds)
        mc_eff = {"gross_p_value": sf["gross_p"], "ftmo_net_p_value": sf["ftmo_net_p"]}
        r = p14.summarize_pair("CLEAN_SUPERTREND_10_3", asset, native_ask, trs, mc_eff)
        r["ftmo_base_R"] = round(fsum(t["base_R"] for t in trs), 2)
        r["fade_ftmo_R"] = round(fsum(t["ftmo_R"] for t in fds), 2)
        r["direction"] = p18.direction_breakdown(trs)
        r["corr_usdjpy_core"] = p18.daily_correlation(trs, core_daily)
        rows.append(r)

    q_f = p14.benjamini_hochberg([r["mc_null"]["ftmo_net_p_value"] for r in rows])
    print("\n=== TRACK 2: CLEAN-ROOM SUPERTREND(10,3.0) RETRACEMENT + STEP-TRAILING (m=5, swap=0) ===", flush=True)
    for r, qf in zip(rows, q_f):
        r["fdr_ftmo_q"] = qf
        if r["tier"] == "TIER_1_FTMO_READY" and (qf > 0.10 or r["ftmo_net_R"] <= r["fade_ftmo_R"]):
            r["tier"] = "TIER_2_PERSONAL_VAULT"
        pf = r["mc_null"]["ftmo_net_p_value"]
        print(
            f"  CLEAN_ST10_3 {r['asset']:6s} | n={r['n']:4d} | FTMO={r.get('ftmo_net_R',0):+6.2f}R Base={r['ftmo_base_R']:+6.2f}R "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7) "
            f"| Fade={r['fade_ftmo_R']:+6.1f} | p_sf={pf:.3f}(q={qf:.3f}) | rJPY={r['corr_usdjpy_core']['union_corr']} | {r['tier']}",
            flush=True,
        )
    return {
        "track": "Track2_CleanRoom_SuperTrend_10_3",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "tier_counts": dict(Counter(r["tier"] for r in rows)),
        "rows": rows,
    }


# ==============================================================================
# TRACK 3: STAGE-0 H4/D1 SCOUT ON SEALED POSITIVE-SWAP FX PAIRS (ZERO-NETWORK)
# ==============================================================================

def load_sealed_bars(jobs_root: Path, sym: str, tf: str) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    p = jobs_root / "swing-10k-20261120" / "development" / f"{sym}-{tf}.parquet"
    tbl = pq.read_table(p)
    ts = tbl["bar_open_server_seconds"].to_numpy().astype(np.int64)
    assert int(ts[-1]) < STOP, f"Holdout leak detected in {p}"
    return (
        ts,
        tbl["open"].to_numpy().astype(np.float64),
        tbl["high"].to_numpy().astype(np.float64),
        tbl["low"].to_numpy().astype(np.float64),
        tbl["close"].to_numpy().astype(np.float64),
    )


def run_track3_stage0_scout(jobs_root: Path, specs: dict, core_daily: dict[str, float]) -> dict:
    t0 = time.monotonic()
    pairs = ("EURJPY", "GBPJPY", "AUDJPY", "USDCAD", "USDCHF", "USDJPY")
    # Load USDJPY / USDCAD / USDCHF D1 close map for exact USD conversion of swap & commission
    conv_d1 = {}
    for base_sym in ("USDJPY", "USDCAD", "USDCHF"):
        ts, _, _, _, c = load_sealed_bars(jobs_root, base_sym, "D1")
        conv_d1[base_sym] = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts, c)}

    def quote_to_usd_div(ccy: str, d_obj, fallback_px: float) -> float:
        if ccy == "USD":
            return 1.0
        key = f"USD{ccy}"
        return conv_d1.get(key, {}).get(d_obj, fallback_px)

    rows_3a, rows_3b = [], []
    for sym in pairs:
        sp = specs["Swing"][sym]
        is_jpy = sym.endswith("JPY")
        pip = 0.01 if is_jpy else 0.0001
        cost_pips_rt = 1.8 if is_jpy else 1.5  # Conservative H4/D1 Stress RT spread + slippage + comm proxy
        cost_px = cost_pips_rt * pip

        # Load D1 (2000-2024) for causal ATR14 & EMA50 & Donchian20
        d_ts, d_o, d_h, d_l, d_c = load_sealed_bars(jobs_root, sym, "D1")
        d_dates = [datetime.fromtimestamp(int(t), timezone.utc).date() for t in d_ts]
        d_atr = p14.wilder_atr(d_h, d_l, d_c, 14)
        d_ema50 = p14.ema(d_c, 50)
        d_map = {dt: i for i, dt in enumerate(d_dates)}

        # --- 3A: EXP_DAILY_OPEN_080 H4 Stage-0 Scout (swap=0) ---
        h_ts, h_o, h_h, h_l, h_c = load_sealed_bars(jobs_root, sym, "H4")
        by_day = defaultdict(list)
        for k in range(len(h_ts)):
            if START <= int(h_ts[k]) < STOP:
                dt = datetime.fromtimestamp(int(h_ts[k]), timezone.utc)
                if dt.weekday() < 5:
                    by_day[dt.date()].append((dt.hour, float(h_o[k]), float(h_h[k]), float(h_l[k]), float(h_c[k])))

        trs_a, fds_a = [], []
        for dt in sorted(by_day.keys()):
            d_i = d_map.get(dt)
            if d_i is None or d_i < 20 or not np.isfinite(d_atr[d_i - 1]) or d_atr[d_i - 1] <= 0:
                continue
            bars = by_day[dt]
            if len(bars) < 4:
                continue
            a_val = float(d_atr[d_i - 1])
            open_0 = bars[0][1]
            top = open_0 + 0.80 * a_val
            bot = open_0 - 0.80 * a_val
            sl_dist = 0.75 * a_val

            hit_idx = None
            side = 0
            for bi, (hr, bo, bh, bl, bc) in enumerate(bars):
                if hr < 4 or hr > 16:
                    continue
                up = bh >= top - 1e-10
                dn = bl <= bot + 1e-10
                if up and dn:
                    hit_idx = None
                    break
                if up or dn:
                    hit_idx = bi
                    side = 1 if up else -1
                    break
            if hit_idx is None:
                continue

            ep = max(top, bars[hit_idx][1]) if side == 1 else min(bot, bars[hit_idx][1])
            def sim_h4(s_dir: int, e_px: float):
                sl_p = e_px - s_dir * sl_dist
                ex_px = bars[-1][4]
                # On H4 entry bar, bar low/high before trigger can lie below Open < sl_p;
                # check SL strictly on subsequent completed H4 bars (calibrated against M1 USDJPY control!)
                # plus entry-bar close if bar reversed sharply after triggering.
                if (s_dir == 1 and bars[hit_idx][4] <= sl_p + 1e-10) or (s_dir == -1 and bars[hit_idx][4] >= sl_p - 1e-10):
                    ex_px = sl_p
                else:
                    for _, bo, bh, bl, bc in bars[hit_idx + 1:]:
                        if s_dir == 1 and bl <= sl_p + 1e-10:
                            ex_px = min(bo, sl_p)
                            break
                        if s_dir == -1 and bh >= sl_p - 1e-10:
                            ex_px = max(bo, sl_p)
                            break
                gross_px = s_dir * (ex_px - e_px)
                net_px = gross_px - cost_px
                r_val = net_px / (sl_dist + cost_px)
                return {
                    "day": dt.isoformat(), "year": dt.year, "side": s_dir, "reason": "SL_OR_FLAT",
                    "gross_usd": gross_px / pip, "ftmo_comm_slip": cost_px / pip, "ftmo_swap": 0.0,
                    "ftmo_net": net_px / pip, "ftmo_R": r_val,
                    "ex_R_normal": r_val, "ex_R_swapfree": r_val,
                }
            trs_a.append(sim_h4(side, ep))
            fds_a.append(sim_h4(-side, ep))

        sf_a = p18.sign_flip_null_p(trs_a, fds_a)
        ra = p14.summarize_pair("STAGE0_EXP080_H4", sym, False, trs_a, {"gross_p_value": sf_a["gross_p"], "ftmo_net_p_value": sf_a["ftmo_net_p"]})
        ra["stage0_tag"] = "CONTROL_USDJPY" if sym == "USDJPY" else "STAGE0_H4_D1_PRE_M1_SCOUT"
        ra["fade_ftmo_R"] = round(fsum(t["ftmo_R"] for t in fds_a), 2)
        ra["direction"] = p18.direction_breakdown(trs_a)
        ra["corr_usdjpy_core"] = p18.daily_correlation(trs_a, core_daily)
        rows_3a.append(ra)

        # --- 3B: POS_SWAP_DONCHIAN20_D1_SCOUT (BUY ONLY in FTMO Positive-Swap Direction) ---
        trs_b, fds_b = [], []
        i = 60
        while i < len(d_ts) - 1:
            if int(d_ts[i]) < START:
                i += 1
                continue
            if not np.isfinite(d_atr[i - 1]) or not np.isfinite(d_ema50[i - 1]):
                i += 1
                continue
            don20_hi = float(np.max(d_h[i - 21:i - 1]))
            if d_c[i - 1] > d_ema50[i - 1] and d_c[i - 1] > don20_hi:
                a_val = float(d_atr[i - 1])
                ep = float(d_o[i])
                sl_dist = 2.0 * a_val
                sl_p = ep - sl_dist
                ex_i = i
                ex_px = float(d_c[i])
                for j in range(i, len(d_ts)):
                    if d_l[j] <= sl_p + 1e-10:
                        ex_i = j
                        ex_px = min(float(d_o[j]), sl_p) if j > i else sl_p
                        break
                    if j > i and d_c[j - 1] < float(np.min(d_l[j - 11:j - 1])):
                        ex_i = j
                        ex_px = float(d_o[j])
                        break
                    ex_i = j
                    ex_px = float(d_c[j])

                dt_in = d_dates[i]
                dt_out = d_dates[ex_i]
                div = quote_to_usd_div(sp["currency_profit"], dt_out, ex_px)
                cs = float(sp["trade_contract_size"])
                pt = float(sp["point"])
                gross_usd = (ex_px - ep) * cs / div
                cost_usd = cost_px * cs / div
                # Exact FTMO positive swap earned over hold!
                swap_usd = 0.0
                for _at, mult in rollovers(int(d_ts[i]) * 1000, int(d_ts[ex_i]) * 1000, sp["swap_rollover3days"]):
                    swap_usd += float(sp["swap_long"]) * pt * cs / div * mult
                risk_usd = sl_dist * cs / div + cost_usd
                net_usd = gross_usd - cost_usd + swap_usd
                # Symmetric SHORT fade (paying negative swap_short!)
                swap_sh = 0.0
                for _at, mult in rollovers(int(d_ts[i]) * 1000, int(d_ts[ex_i]) * 1000, sp["swap_rollover3days"]):
                    swap_sh += float(sp["swap_short"]) * pt * cs / div * mult
                net_sh = -gross_usd - cost_usd + swap_sh
                trs_b.append({
                    "day": dt_in.isoformat(), "year": dt_in.year, "side": 1, "reason": "DON_EXIT_OR_SL",
                    "gross_usd": gross_usd, "ftmo_comm_slip": cost_usd, "ftmo_swap": swap_usd, "ftmo_net": net_usd,
                    "ftmo_R": net_usd / risk_usd, "ex_R_normal": net_usd / risk_usd, "ex_R_swapfree": (gross_usd - cost_usd) / risk_usd,
                })
                fds_b.append({
                    "day": dt_in.isoformat(), "year": dt_in.year, "side": -1, "reason": "DON_EXIT_OR_SL",
                    "gross_usd": -gross_usd, "ftmo_comm_slip": cost_usd, "ftmo_swap": swap_sh, "ftmo_net": net_sh,
                    "ftmo_R": net_sh / risk_usd, "ex_R_normal": net_sh / risk_usd, "ex_R_swapfree": (-gross_usd - cost_usd) / risk_usd,
                })
                i = ex_i + 1
            else:
                i += 1

        sf_b = p18.sign_flip_null_p(trs_b, fds_b)
        rb = p14.summarize_pair("STAGE0_POS_SWAP_DON20", sym, False, trs_b, {"gross_p_value": sf_b["gross_p"], "ftmo_net_p_value": sf_b["ftmo_net_p"]})
        rb["stage0_tag"] = "CONTROL_USDJPY" if sym == "USDJPY" else "STAGE0_H4_D1_PRE_M1_SCOUT"
        rb["ftmo_swap_total_usd"] = round(fsum(t["ftmo_swap"] for t in trs_b), 2)
        rb["fade_ftmo_R"] = round(fsum(t["ftmo_R"] for t in fds_b), 2)
        rb["corr_usdjpy_core"] = p18.daily_correlation(trs_b, core_daily)
        rows_3b.append(rb)

    print("\n=== TRACK 3A: STAGE-0 H4 EXP_DAILY_OPEN_080 ACROSS YEN CROSSES & USD PAIRS (swap=0) ===", flush=True)
    for r in rows_3a:
        b_r, s_r = r["direction"]["BUY"]["ftmo_R"], r["direction"]["SELL"]["ftmo_R"]
        print(
            f"  EXP080_H4 {r['asset']:6s} | n={r['n']:4d} | Net={r.get('ftmo_net_R',0):+6.2f}R "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7 DD={r.get('ftmo_closed_dd_R',0):.1f}R) "
            f"| B/S={b_r:+.1f}/{s_r:+.1f} | Fade={r['fade_ftmo_R']:+6.1f} | p_sf={r['mc_null']['ftmo_net_p_value']:.3f} | rJPY={r['corr_usdjpy_core']['union_corr']} | {r['stage0_tag']}",
            flush=True,
        )

    print("\n=== TRACK 3B: STAGE-0 D1 POSITIVE-SWAP DONCHIAN-20 LONG ONLY (EXACT FTMO +SWAP) ===", flush=True)
    for r in rows_3b:
        print(
            f"  DON20_POS {r['asset']:6s} | n={r['n']:4d} | Net={r.get('ftmo_net_R',0):+6.2f}R "
            f"(A={r.get('ftmo_clusters_R',{}).get('A',0):+5.1f} B={r.get('ftmo_clusters_R',{}).get('B',0):+5.1f} yr+={r.get('ftmo_pos_years',0)}/7 DD={r.get('ftmo_closed_dd_R',0):.1f}R) "
            f"| Swap=+${r['ftmo_swap_total_usd']:.0f} | p_g={r['mc_null']['gross_p_value']:.3f} p_f={r['mc_null']['ftmo_net_p_value']:.3f} | rJPY={r['corr_usdjpy_core']['union_corr']} | {r['stage0_tag']}",
            flush=True,
        )

    return {
        "track": "Track3_Stage0_H4_D1_YenCross_And_PositiveSwap_Scout",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "exp080_h4": rows_3a,
        "pos_swap_donchian20_d1": rows_3b,
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
    core_daily = p18.build_usdjpy_core_daily_series(args.jobs, args.cache, specs)

    t1 = run_track1_us500_overnight(args.cache, specs["Swing"]["US500.cash"], core_daily)
    t2 = run_track2_supertrend(args.jobs, args.cache, specs, core_daily)
    t3 = run_track3_stage0_scout(args.jobs, specs, core_daily)

    out = {
        "pass": "Pass 19", "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA, "holdout_rows": 0,
        "order_send_count": 0, "network_calls": 0, "spec_bindings": bindings,
        "track1_us500_overnight": t1,
        "track2_clean_supertrend": t2,
        "track3_stage0_yencross_carry": t3,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass19-result.json", out)
    print("\nPASS19_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
