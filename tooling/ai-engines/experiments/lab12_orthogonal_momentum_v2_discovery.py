"""Wave-3 Cycle 2 — Lab #12: Orthogonal Structural Momentum, Vol-Expansion & Cross-Session Catalysts
on 7 Under-Used M1 Bid/Ask Assets (`2018-2024` Dev ONLY).

Complementary Study to Lab #11 (`LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124.md`):
  Lab #11 demonstrated that short-target intraday mean-reversion fades hit the CFD Bid/Ask spread wall
  (`0/20` passed; `BTCUSD` CFD spread+slip = 12% of SL). Lab #12 tests the complementary physical
  hypothesis: fat right-tail directional momentum, volatility-compression breakouts, and cross-market
  session transmission (`tp = None`, holding winners to session flat `swap = 0` so `1.5R-4R` tails clear
  CFD friction!) across the 7 under-used M1 assets (`GER40, XAUUSD, AUDUSD, GBPJPY, USDCAD, EURUSD, US500`).

STRICT SAFETY & ANTI-BIAS INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 integrity on startup (`holdout_rows_analysed = 0`).
  - Reads ONLY local D: SSD `.runtime/hot-m1-cache/` verified `< 2025-01-01T00:00:00Z`.
  - `ORDER_SEND_CAPABLE = False` (`OrderSend = 0`), ZERO network/API calls.
  - Strictly causal `shift = 1` daily indicators (`ATR14`, `ATR5/ATR20 vol_ratio`, `prev_o/h/l/c`),
    strict `< entry_ts` intraday features, realistic stop-order entry fills (`max(top, AskOpen)` /
    `min(bot, BidOpen)`), conservative SL-before-TP tie-break, hard same-UTC-day flat before `20:50 UTC`
    (`swap = 0`), and official `2018-2024` red-news `±5m` guard (`FLATTEN_5M`) applied to EVERY tape!
  - Pre-registered `m_total = 16` hypotheses (4 families x 4 specs), Cluster A (`2018-2020`) -> Blind
    Cluster B (`2021-2024`), tracking `Sign-Flip Null`, `Bonferroni`, `BH-FDR`, and `DSR (n_trials=16)`.
  - Hard 6-Gate Red-Team Filter + 10,000-path Block Bootstrap MC (`seed=20261124`, `SYMCAP 1.75%` +
    `Dyn_ProfitLock`) across `FTMO Swing 10K`, `FTMO Swing 25K`, and `The5ers High Stakes 5K`.
  - Retains ALL negative/failed candidates honestly (zero peeking or cherry-picking!).
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
import math
from math import fsum
from pathlib import Path
import sys
import time
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass24_mtf_new_archetypes as p24
import pass28_final_discovery_rednews_frontier as p28
from native_ftmo_monfri_seal import START, STOP
from quant_core.ftmo_track_replay import profiles
from quant_core.holdout_guard import HoldoutLockError, enforce_pre_holdout_dates, enforce_pre_holdout_ts
from quant_factory.data_store import (
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_firm_config,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio, sign_flip_p_numba
from quant_factory.lab11_orthogonal_prop_v2_discovery import (
    ALL_DEV_YEARS,
    CLUSTER_A_YEARS,
    CLUSTER_B_YEARS,
    FUNDED_SYMCAP,
    INCUMBENT_LIVE8,
    N_MC_PATHS,
    P1_SYMCAP_TIGHT,
    SEED,
    SIGN_FLIP_DRAWS,
    _apply_cost_stress_existing_tapes,
    _causal_window_stats,
    _lot_scale_and_cost,
    _resolve_ts,
    _safe_corr,
    _tape_split_metrics,
    apply_red_news_and_15x_stress,
    evaluate_prop_accretion_mc,
    replay_lab11_portfolio_m1,
)
from quant_factory.prop_engine import make_block_bootstrap_indices
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")
BERLIN_TZ = ZoneInfo("Europe/Berlin")

REPORT_DIR = ROOT / "planning/research"
REPORT_STEM = "LAB12-ORTHOGONAL-MOMENTUM-V2-DISCOVERY-20261124"


# ==============================================================================
# 1. STRICTLY CAUSAL M1 BUNDLE WITH SHIFT=1 ATR14 + VOL_RATIO (ATR5/ATR20)
# ==============================================================================

def build_causal_m1_bundle_v2(
    asset: str,
    swing_specs: dict[str, dict],
    usdjpy_close_map: dict[date, float],
    *,
    cache_dir: Path = hcache.DEFAULT_CACHE,
) -> dict[str, Any]:
    """Load sealed local M1 Bid/Ask bars (`< 2025-01-01`) with strict `shift=1` ATR14, ATR5/ATR20 vol_ratio & prev OHLC."""
    times, quotes, am = hcache.load_asset(asset, cache_dir=cache_dir, verify_sha=False)
    enforce_pre_holdout_ts(int(times[-1]), stop_ts=STOP, context=f"lab12:{asset}")
    if quotes.shape[1] < 8:
        quotes = np.hstack([quotes, quotes])

    day_ids = (times // 86400).astype(np.int64)
    change = np.empty(len(day_ids), dtype=np.bool_)
    change[0] = True
    change[1:] = day_ids[1:] != day_ids[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = len(day_ids) - 1

    raw_days: list[dict[str, Any]] = []
    for s_i, e_i in zip(starts, ends):
        ts0 = int(times[s_i])
        dt0 = datetime.fromtimestamp(ts0, timezone.utc)
        if dt0.weekday() >= 5:
            continue
        if (e_i - s_i + 1) < 120:
            continue
        d_iso = dt0.date().isoformat()
        if d_iso >= "2025-01-01":
            raise HoldoutLockError(f"HOLDOUT_CONTAMINATION_DAY:{asset}:{d_iso}")
        dsec = int(datetime(dt0.year, dt0.month, dt0.day, tzinfo=timezone.utc).timestamp())
        flat_target = dsec + 20 * 3600 + 50 * 60
        sub_t = times[s_i:e_i + 1]
        rel_flat = int(sub_t.searchsorted(flat_target, side="right")) - 1
        flat_idx = int(s_i + max(0, rel_flat))
        bo = float(quotes[s_i, 0])
        bh = float(quotes[s_i:e_i + 1, 1].max())
        bl = float(quotes[s_i:e_i + 1, 2].min())
        bc = float(quotes[e_i, 3])
        raw_days.append({
            "day": d_iso,
            "year": dt0.year,
            "weekday": dt0.weekday(),
            "dsec": dsec,
            "fi": int(s_i),
            "li": int(e_i),
            "flat_idx": flat_idx,
            "o": bo, "h": bh, "l": bl, "c": bc,
        })

    # Strictly causal shift=1 daily ATR14, ATR5, ATR20, vol_ratio (computed ONLY from closed days <= t-1!)
    days_out: list[dict[str, Any]] = []
    trs: list[float] = []
    for i, d in enumerate(raw_days):
        if i == 0:
            trs.append(max(1e-9, d["h"] - d["l"]))
            continue
        prev = raw_days[i - 1]
        prev2_c = raw_days[i - 2]["c"] if i >= 2 else prev["o"]
        tr_prev = max(prev["h"] - prev["l"], abs(prev["h"] - prev2_c), abs(prev["l"] - prev2_c))
        if i >= 2:
            trs.append(max(1e-9, tr_prev))
        if len(trs) >= 20:
            atr14 = float(np.mean(trs[-14:]))
            atr5 = float(np.mean(trs[-5:]))
            atr20 = float(np.mean(trs[-20:]))
            days_out.append({
                **d,
                "prev_o": prev["o"],
                "prev_h": prev["h"],
                "prev_l": prev["l"],
                "prev_c": prev["c"],
                "prev_rng": max(1e-9, prev["h"] - prev["l"]),
                "prev_day": prev["day"],
                "atr": max(1e-9, atr14),
                "vol_ratio": atr5 / max(1e-9, atr20),
            })

    spec_key = asset if asset in swing_specs else ("US500.cash" if asset == "US500" else None)
    spec = swing_specs[spec_key] if spec_key and spec_key in swing_specs else None
    return {
        "asset": asset,
        "times": times,
        "quotes": quotes,
        "spec": spec,
        "usdjpy_close_map": usdjpy_close_map,
        "days": days_out,
        "day_map": {d["day"]: d for d in days_out},
        "meta": am,
    }


# ==============================================================================
# 2. REALISTIC STOP-BREAKOUT & MARKET M1 TRADE REPLAY (SL-BEFORE-TP, SWAP = 0)
# ==============================================================================

def replay_lab12_trade(
    bundle: dict[str, Any],
    e_idx: int,
    flat_idx: int,
    side: int,
    sl_dist: float,
    *,
    entry_price_override: float | None = None,
    tp_dist: float | None = None,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, float] | None:
    """Replay single causal M1 Bid/Ask trade (`swap = 0`, SL-before-TP, realistic stop-trigger fill)."""
    times, quotes = bundle["times"], bundle["quotes"]
    asset = bundle["asset"]
    if sl_dist <= 1e-9 or e_idx < 0 or flat_idx <= e_idx:
        return None

    mkt_ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
    ep = float(entry_price_override) if entry_price_override is not None else mkt_ep
    sl_p = ep - side * sl_dist
    tp_p = (ep + side * tp_dist) if (tp_dist is not None and tp_dist > 1e-9) else None

    liq = quotes[e_idx:flat_idx + 1, :4] if side == 1 else quotes[e_idx:flat_idx + 1, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 1] >= tp_p - 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)
        tp_hits = np.flatnonzero(liq[:-1, 2] <= tp_p + 1e-10) if tp_p is not None else np.empty(0, dtype=np.int64)

    f_sl = int(sl_hits[0]) if len(sl_hits) else None
    f_tp = int(tp_hits[0]) if len(tp_hits) else None

    # Conservative SL-before-TP on same M1 bar tie-break!
    if f_sl is not None and (f_tp is None or f_sl <= f_tp):
        rel = f_sl
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        at_open = bool(gap)
        reason = "SL_GAP_OR_TOUCH"
    elif f_tp is not None:
        rel = f_tp
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - tp_p) >= -1e-10
        ex_p = op if gap else tp_p
        at_open = bool(gap)
        reason = "TP_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        ex_p = float(liq[-1, 0])
        at_open = True
        reason = "HARD_FLAT"

    stamps = times[e_idx:e_idx + rel + 1].astype(np.int64)
    enforce_pre_holdout_ts(stamps, START, STOP, context=f"lab12.trade:{asset}")

    # Hard swap = 0 invariant (same UTC day & closed before 20:55 UTC)
    dt_e = datetime.fromtimestamp(int(stamps[0]), timezone.utc)
    dt_x = datetime.fromtimestamp(int(stamps[-1]), timezone.utc)
    assert dt_e.date() == dt_x.date(), f"OVERNIGHT_HOLD_DETECTED:{asset}:{dt_e.date()}->{dt_x.date()}"
    assert (dt_x.hour * 60 + dt_x.minute) <= 20 * 60 + 55, f"ROLLOVER_BREACH:{asset}:{dt_x}"

    scale, drag_1x, _ = _lot_scale_and_cost(
        asset, ep, ex_p, int(stamps[-1]), bundle["spec"], bundle["usdjpy_close_map"]
    )
    sub_liq = liq[:rel + 1]
    cur_pnl = side * (sub_liq[:, 0] - ep) * scale - drag_1x
    hi_px = sub_liq[:, 1] if side == 1 else sub_liq[:, 2]
    lo_px = sub_liq[:, 2] if side == 1 else sub_liq[:, 1]
    hi_pnl = side * (hi_px - ep) * scale - drag_1x
    lo_pnl = side * (lo_px - ep) * scale - drag_1x
    cls_pnl = side * (sub_liq[:, 3] - ep) * scale - drag_1x

    spr0 = max(0.0, float(quotes[e_idx, 4] - quotes[e_idx, 0]))
    cur_pnl[0] = -spr0 * scale - drag_1x
    hi_pnl[0] = max(cur_pnl[0], cls_pnl[0])
    lo_pnl[0] = min(cur_pnl[0], lo_pnl[0], cls_pnl[0])

    net_1x = side * (ex_p - ep) * scale - drag_1x
    if rel == 0 or at_open:
        cur_pnl[-1] = hi_pnl[-1] = lo_pnl[-1] = cls_pnl[-1] = net_1x
    else:
        hi_pnl[-1] = max(cur_pnl[-1], net_1x)
        lo_pnl[-1] = min(cur_pnl[-1], net_1x)
        cls_pnl[-1] = net_1x

    marks = np.column_stack((cur_pnl, hi_pnl, lo_pnl, cls_pnl)).astype(np.float64)
    init_risk_usd = sl_dist * scale
    stop_risk_1x = init_risk_usd + drag_1x
    marks = np.maximum(marks, -stop_risk_1x)
    marks[-1, -1] = net_1x

    # Opposite-side control trade at identical timestamp for exact sign-flip permutation null
    fep = (ep - side * spr0) if entry_price_override is not None else float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
    ftp = (fep - side * tp_dist) if (tp_dist is not None and tp_dist > 1e-9) else None
    fd = p24.replay_causal_intraday(
        asset, times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_dist,
        tp_p=ftp, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
    )
    fade_r_1x = float(fd["ftmo_R"]) if fd is not None else -float(net_1x / stop_risk_1x)

    d_iso = dt_e.date().isoformat()
    row = {
        "day": d_iso,
        "year": int(dt_e.year),
        "asset": asset,
        "entry": int(stamps[0]),
        "exit": int(stamps[-1]) + (0 if at_open else 60),
        "at_open": at_open,
        "reason": reason,
        "side": int(side),
        "entry_price": float(ep),
        "sl_price": float(sl_p),
        "tp_price": float(tp_p) if tp_p is not None else None,
        "initial_risk_usd": float(init_risk_usd),
        "base_friction_usd": float(drag_1x),
        "stop_risk_with_cost_usd": float(stop_risk_1x),
        "net_usd_per_lot": float(net_1x),
        "net_R": float(net_1x / stop_risk_1x),
        "swap_usd": 0.0,
    }
    return row, stamps, marks, fade_r_1x


def _scan_stop_breakout(
    bundle: dict[str, Any],
    d: dict[str, Any],
    ts_scan_start: int,
    ts_scan_end: int,
    ts_flat: int,
    top: float,
    bot: float,
    sl_dist: float,
    *,
    allow_long: bool = True,
    allow_short: bool = True,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, float] | None:
    """Scan M1 Bid/Ask bars inside `[ts_scan_start, ts_scan_end)` for first stop-order breakout (zero lookahead)."""
    times, quotes = bundle["times"], bundle["quotes"]
    fi, day_flat = int(d["fi"]), int(d["flat_idx"])
    sub_t = times[fi:day_flat + 1]
    i0 = int(sub_t.searchsorted(ts_scan_start, side="left"))
    i1 = int(sub_t.searchsorted(ts_scan_end, side="left"))
    rel_f = int(sub_t.searchsorted(ts_flat, side="right")) - 1
    f_idx = min(day_flat, fi + max(0, rel_f))
    if i1 <= i0 or (fi + i0) >= f_idx:
        return None
    scan = quotes[fi + i0:fi + i1]
    up = (scan[:, 5] >= top - 1e-10) if allow_long else np.zeros(len(scan), dtype=bool)
    dn = (scan[:, 2] <= bot + 1e-10) if allow_short else np.zeros(len(scan), dtype=bool)
    hits = np.flatnonzero(up | dn)
    if not len(hits):
        return None
    j = int(hits[0])
    if up[j] and dn[j]:
        return None  # Ambiguous same-minute dual touch -> skip conservatively!
    side = 1 if up[j] else -1
    e_idx = fi + i0 + j
    if e_idx >= f_idx:
        return None
    ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
    return replay_lab12_trade(bundle, e_idx, f_idx, side, sl_dist, entry_price_override=ep, tp_dist=None)


# ==============================================================================
# 3. PRE-REGISTERED M = 16 ORTHOGONAL MOMENTUM / VOL-EXPANSION CATALOG
# ==============================================================================

def build_lab12_catalog() -> list[dict[str, Any]]:
    """Pre-registered `m_total = 16` white-box directional momentum & vol-expansion hypotheses (4 families x 4)."""
    return [
        # ---- FAMILY A: European Cash Session GER40 (DAX) Momentum & ORB (flat 16:20 UTC, 1:15 margin) ----
        {
            "id": "L12_A1_GER40_FFM08_ORB30_BRK",
            "family": "A_GER40_EU_ORB",
            "asset": "GER40",
            "kind": "BOX_STOP_BRK",
            "box_start": (8, 0, "BERLIN"), "box_end": (8, 30, "BERLIN"),
            "scan_end": (12, 30, "BERLIN"), "flat_hm": (16, 20, "UTC"),
            "max_box_atr": 0.55, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "Frankfurt 08:00-08:30 CET compressed opening range breakout rides institutional DAX flow into Xetra close.",
        },
        {
            "id": "L12_A2_GER40_FFM08_ORB60_BRK",
            "family": "A_GER40_EU_ORB",
            "asset": "GER40",
            "kind": "BOX_STOP_BRK",
            "box_start": (8, 0, "BERLIN"), "box_end": (9, 0, "BERLIN"),
            "scan_end": (13, 0, "BERLIN"), "flat_hm": (16, 20, "UTC"),
            "max_box_atr": 0.70, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.80,
            "rationale": "Frankfurt 08:00-09:00 CET pre-cash auction box breakout captures Xetra opening institutional expansion.",
        },
        {
            "id": "L12_A3_GER40_VOLCOMP_EXP",
            "family": "A_GER40_EU_ORB",
            "asset": "GER40",
            "kind": "BOX_STOP_BRK",
            "box_start": (0, 0, "UTC"), "box_end": (8, 0, "BERLIN"),
            "scan_end": (13, 0, "BERLIN"), "flat_hm": (16, 20, "UTC"),
            "max_box_atr": 0.85, "vol_ratio_max": 0.85, "buf_atr": 0.15, "sl_atr": 0.75,
            "rationale": "Multi-day DAX volatility compression (ATR5/ATR20 <= 0.85) releases into directional Frankfurt session expansion.",
        },
        {
            "id": "L12_A4_GER40_MORN_TO_AFT_CONT",
            "family": "A_GER40_EU_ORB",
            "asset": "GER40",
            "kind": "SESSION_IMPULSE_STOP_CONT",
            "box_start": (8, 0, "BERLIN"), "box_end": (11, 30, "BERLIN"),
            "scan_end": (14, 30, "BERLIN"), "flat_hm": (16, 20, "UTC"),
            "min_move_atr": 0.35, "close_pos_thr": 0.70, "sl_atr": 0.75,
            "rationale": "Strong DAX morning directional close near extreme breaks into afternoon continuation before Xetra close.",
        },

        # ---- FAMILY B: Gold (XAUUSD) Directional Vol-Expansion & Session Breakout (EOD fat tail, swap=0) ----
        {
            "id": "L12_B1_XAU_ASIA_BOX_LDN_BRK",
            "family": "B_XAU_VOL_EXP",
            "asset": "XAUUSD",
            "kind": "BOX_STOP_BRK",
            "box_start": (0, 0, "UTC"), "box_end": (7, 0, "UTC"),
            "scan_end": (14, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.50, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "Tight Gold Asian consolidation box (<= 0.50 ATR) breaks into London/NY directional trend held to EOD.",
        },
        {
            "id": "L12_B2_XAU_COMEX0820_ORB30",
            "family": "B_XAU_VOL_EXP",
            "asset": "XAUUSD",
            "kind": "BOX_STOP_BRK",
            "box_start": (8, 20, "NY"), "box_end": (8, 50, "NY"),
            "scan_end": (12, 30, "NY"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.65, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "COMEX Gold pit open (08:20-08:50 ET) opening-range breakout captures US rate/futures momentum through EOD.",
        },
        {
            "id": "L12_B3_XAU_LDN_NY_VOLCOMP_BRK",
            "family": "B_XAU_VOL_EXP",
            "asset": "XAUUSD",
            "kind": "BOX_STOP_BRK",
            "box_start": (7, 0, "UTC"), "box_end": (12, 0, "UTC"),
            "scan_end": (16, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.75, "vol_ratio_max": 0.88, "buf_atr": 0.05, "sl_atr": 0.75,
            "rationale": "Gold volatility compression (ATR5/ATR20 <= 0.88) triggers London-box breakout into NY macro liquidity.",
        },
        {
            "id": "L12_B4_XAU_PRIOR_DAY_EXP_BRK",
            "family": "B_XAU_VOL_EXP",
            "asset": "XAUUSD",
            "kind": "PRIOR_DAY_RANGE_EXP",
            "scan_start": (7, 0, "UTC"), "scan_end": (16, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_prev_rng_atr": 0.85, "sl_atr": 0.75,
            "rationale": "Compressed prior-day Gold bar (<= 0.85 ATR) expanding beyond prior high/low rides trend release to EOD.",
        },

        # ---- FAMILY C: Non-JPY FX Cross/Commodity Pairs (AUDUSD, GBPJPY, USDCAD, EURUSD) ----
        {
            "id": "L12_C1_AUDUSD_ASIA_LDN_VOLCOMP",
            "family": "C_FX_NONJPY_MOM",
            "asset": "AUDUSD",
            "kind": "BOX_STOP_BRK",
            "box_start": (0, 0, "UTC"), "box_end": (7, 0, "UTC"),
            "scan_end": (14, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.55, "vol_ratio_max": 0.90, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "AUDUSD compressed Sydney/Tokyo range under low 5d/20d vol breaks into London-NY risk-sentiment trend.",
        },
        {
            "id": "L12_C2_GBPJPY_ASIA_LDN_VOLCOMP",
            "family": "C_FX_NONJPY_MOM",
            "asset": "GBPJPY",
            "kind": "BOX_STOP_BRK",
            "box_start": (0, 0, "UTC"), "box_end": (7, 0, "UTC"),
            "scan_end": (13, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.55, "vol_ratio_max": 0.92, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "GBPJPY tight Asian box under vol compression triggers high-velocity London breakout held to EOD.",
        },
        {
            "id": "L12_C3_USDCAD_NY_OIL_EXP_BRK",
            "family": "C_FX_NONJPY_MOM",
            "asset": "USDCAD",
            "kind": "BOX_STOP_BRK",
            "box_start": (7, 0, "UTC"), "box_end": (12, 30, "UTC"),
            "scan_end": (16, 30, "UTC"), "flat_hm": (20, 50, "UTC"),
            "max_box_atr": 0.60, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "USDCAD pre-NY London range breaks out on North American oil/CAD institutional flow through 20:50 UTC.",
        },
        {
            "id": "L12_C4_EURUSD_LDN_MORN_CONT",
            "family": "C_FX_NONJPY_MOM",
            "asset": "EURUSD",
            "kind": "SESSION_IMPULSE_STOP_CONT",
            "box_start": (7, 0, "UTC"), "box_end": (10, 0, "UTC"),
            "scan_end": (14, 30, "UTC"), "flat_hm": (20, 50, "UTC"),
            "min_move_atr": 0.35, "close_pos_thr": 0.75, "sl_atr": 0.75,
            "rationale": "EURUSD clean London morning directional drive closing near extreme continues into NY overlap (swap=0).",
        },

        # ---- FAMILY D: US500 Cash-Session & Cross-Asset Lead-Lag (distinct from US100 E4/E5!) ----
        {
            "id": "L12_D1_US500_CASH_ORB30_EOD",
            "family": "D_US500_CROSS_LEADLAG",
            "asset": "US500",
            "kind": "BOX_STOP_BRK",
            "box_start": (9, 30, "NY"), "box_end": (10, 0, "NY"),
            "scan_end": (13, 30, "NY"), "flat_hm": (15, 50, "NY"),
            "max_box_atr": 0.65, "vol_ratio_max": 9.9, "buf_atr": 0.0, "sl_atr": 0.75,
            "rationale": "S&P 500 09:30-10:00 ET cash opening-range breakout captures broad institutional equity trend to 15:50 ET.",
        },
        {
            "id": "L12_D2_GER40_TO_US500_TRANSMIT",
            "family": "D_US500_CROSS_LEADLAG",
            "asset": "US500",
            "kind": "CROSS_TRANSMIT_MKT",
            "lead_asset": "GER40",
            "lead_start": (8, 0, "BERLIN"), "lead_end": (9, 25, "NY"),
            "entry_hm": (9, 30, "NY"), "flat_hm": (15, 50, "NY"),
            "thr": 0.45, "sl_atr": 0.75,
            "rationale": "Strong European risk-on/off drive in GER40 (08:00 CET -> 09:25 ET) transmits into US500 cash session.",
        },
        {
            "id": "L12_D3_XAU_USD_SAFEHAVEN_NY",
            "family": "D_US500_CROSS_LEADLAG",
            "asset": "XAUUSD",
            "kind": "CROSS_CONFLUENCE_MKT",
            "confirm_asset": "EURUSD", "confirm_sign": 1,
            "win_start": (0, 0, "UTC"), "win_end": (9, 25, "NY"),
            "entry_hm": (9, 30, "NY"), "flat_hm": (15, 50, "NY"),
            "thr": 0.30, "sl_atr": 0.75,
            "rationale": "Synchronized Gold + EURUSD pre-NY dollar trend confirms macro safe-haven/USD flow into NY afternoon.",
        },
        {
            "id": "L12_D4_COMMOD_FX_BASKET_MOM",
            "family": "D_US500_CROSS_LEADLAG",
            "asset": "AUDUSD",
            "kind": "CROSS_CONFLUENCE_MKT",
            "confirm_asset": "USDCAD", "confirm_sign": -1,
            "win_start": (0, 0, "UTC"), "win_end": (12, 0, "UTC"),
            "entry_hm": (12, 0, "UTC"), "flat_hm": (20, 50, "UTC"),
            "thr": 0.30, "sl_atr": 0.75,
            "rationale": "Agreement between AUDUSD up and USDCAD down (or vice versa) confirms broad commodity-FX macro momentum.",
        },
    ]


def evaluate_lab12_spec(
    bundles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> tuple[dict[str, tuple[dict, np.ndarray, np.ndarray]], dict[str, float]]:
    """Generate exact causal M1 trade tape + opposite-side fade_R map for one Lab #12 hypothesis."""
    asset = cfg["asset"]
    kind = cfg["kind"]
    sl_atr = float(cfg["sl_atr"])
    b = bundles[asset]
    times = b["times"]

    raw_tape: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
    fade_r_by_day: dict[str, float] = {}

    for d in b["days"]:
        dk = d["day"]
        atr = float(d["atr"])
        if atr <= 1e-9:
            continue
        res = None

        if kind == "BOX_STOP_BRK":
            if float(d["vol_ratio"]) > float(cfg["vol_ratio_max"]):
                continue
            ts_bs = _resolve_ts(dk, cfg["box_start"])
            ts_be = _resolve_ts(dk, cfg["box_end"])
            ts_se = _resolve_ts(dk, cfg["scan_end"])
            ts_fl = _resolve_ts(dk, cfg["flat_hm"])
            if ts_bs >= ts_be or ts_be >= ts_se or ts_be >= ts_fl:
                continue
            st = _causal_window_stats(b, ts_bs, ts_be)
            if st is None or st["range"] > float(cfg["max_box_atr"]) * atr:
                continue
            buf = float(cfg["buf_atr"]) * atr
            # Trigger on Ask high >= top (Buy) or Bid low <= bot (Sell) using exact box extremes
            i0 = int(times.searchsorted(ts_bs, side="left"))
            i1 = int(times.searchsorted(ts_be, side="left"))
            if i1 - i0 < 15:
                continue
            box_hi = float(np.max(b["quotes"][i0:i1, 5])) + buf  # Ask high of completed box
            box_lo = float(np.min(b["quotes"][i0:i1, 2])) - buf  # Bid low of completed box
            res = _scan_stop_breakout(b, d, ts_be, ts_se, ts_fl, box_hi, box_lo, sl_atr * atr)

        elif kind == "SESSION_IMPULSE_STOP_CONT":
            ts_bs = _resolve_ts(dk, cfg["box_start"])
            ts_be = _resolve_ts(dk, cfg["box_end"])
            ts_se = _resolve_ts(dk, cfg["scan_end"])
            ts_fl = _resolve_ts(dk, cfg["flat_hm"])
            if ts_bs >= ts_be or ts_be >= ts_se or ts_be >= ts_fl:
                continue
            st = _causal_window_stats(b, ts_bs, ts_be)
            if st is None:
                continue
            z = st["ret"] / atr
            cpos = st["close_pos"]
            thr_m = float(cfg["min_move_atr"])
            c_thr = float(cfg["close_pos_thr"])
            allow_l = (z >= thr_m) and (cpos >= c_thr)
            allow_s = (z <= -thr_m) and (cpos <= 1.0 - c_thr)
            if not (allow_l or allow_s):
                continue
            i0 = int(times.searchsorted(ts_bs, side="left"))
            i1 = int(times.searchsorted(ts_be, side="left"))
            if i1 - i0 < 15:
                continue
            box_hi = float(np.max(b["quotes"][i0:i1, 5]))
            box_lo = float(np.min(b["quotes"][i0:i1, 2]))
            res = _scan_stop_breakout(
                b, d, ts_be, ts_se, ts_fl, box_hi, box_lo, sl_atr * atr,
                allow_long=allow_l, allow_short=allow_s,
            )

        elif kind == "PRIOR_DAY_RANGE_EXP":
            if float(d["prev_rng"]) > float(cfg["max_prev_rng_atr"]) * atr:
                continue
            ts_ss = _resolve_ts(dk, cfg["scan_start"])
            ts_se = _resolve_ts(dk, cfg["scan_end"])
            ts_fl = _resolve_ts(dk, cfg["flat_hm"])
            if ts_ss >= ts_se or ts_ss >= ts_fl:
                continue
            res = _scan_stop_breakout(
                b, d, ts_ss, ts_se, ts_fl, float(d["prev_h"]), float(d["prev_l"]), sl_atr * atr
            )

        elif kind == "CROSS_TRANSMIT_MKT":
            b_lead = bundles[cfg["lead_asset"]]
            d_lead = b_lead["day_map"].get(dk)
            if d_lead is None or float(d_lead["atr"]) <= 1e-9:
                continue
            ts_ls = _resolve_ts(dk, cfg["lead_start"])
            ts_le = _resolve_ts(dk, cfg["lead_end"])
            ts_e = _resolve_ts(dk, cfg["entry_hm"])
            ts_fl = _resolve_ts(dk, cfg["flat_hm"])
            if ts_le > ts_e or ts_e >= ts_fl:
                continue
            st_l = _causal_window_stats(b_lead, ts_ls, ts_le)
            if st_l is None:
                continue
            z_l = st_l["ret"] / float(d_lead["atr"])
            if abs(z_l) < float(cfg["thr"]):
                continue
            side = 1 if z_l > 0.0 else -1
            fi, day_flat = int(d["fi"]), int(d["flat_idx"])
            sub_t = times[fi:day_flat + 1]
            e_idx = fi + int(sub_t.searchsorted(ts_e, side="left"))
            f_idx = min(day_flat, fi + max(0, int(sub_t.searchsorted(ts_fl, side="right")) - 1))
            if e_idx < f_idx and e_idx <= day_flat and (int(times[e_idx]) - ts_e) <= 900:
                res = replay_lab12_trade(b, e_idx, f_idx, side, sl_atr * atr)

        elif kind == "CROSS_CONFLUENCE_MKT":
            b_cf = bundles[cfg["confirm_asset"]]
            d_cf = b_cf["day_map"].get(dk)
            if d_cf is None or float(d_cf["atr"]) <= 1e-9:
                continue
            ts_ws = _resolve_ts(dk, cfg["win_start"])
            ts_we = _resolve_ts(dk, cfg["win_end"])
            ts_e = _resolve_ts(dk, cfg["entry_hm"])
            ts_fl = _resolve_ts(dk, cfg["flat_hm"])
            if ts_we > ts_e or ts_e >= ts_fl:
                continue
            st_a = _causal_window_stats(b, ts_ws, ts_we)
            st_c = _causal_window_stats(b_cf, ts_ws, ts_we)
            if st_a is None or st_c is None:
                continue
            z_a = st_a["ret"] / atr
            z_c = (st_c["ret"] / float(d_cf["atr"])) * float(cfg["confirm_sign"])
            thr = float(cfg["thr"])
            if z_a >= thr and z_c >= thr:
                side = 1
            elif z_a <= -thr and z_c <= -thr:
                side = -1
            else:
                continue
            fi, day_flat = int(d["fi"]), int(d["flat_idx"])
            sub_t = times[fi:day_flat + 1]
            e_idx = fi + int(sub_t.searchsorted(ts_e, side="left"))
            f_idx = min(day_flat, fi + max(0, int(sub_t.searchsorted(ts_fl, side="right")) - 1))
            if e_idx < f_idx and e_idx <= day_flat and (int(times[e_idx]) - ts_e) <= 900:
                res = replay_lab12_trade(b, e_idx, f_idx, side, sl_atr * atr)

        if res is not None:
            row, stamps, marks, fade_r = res
            raw_tape[dk] = (row, stamps, marks)
            fade_r_by_day[dk] = fade_r

    return raw_tape, fade_r_by_day


# ==============================================================================
# 4. FULL LAB #12 PIPELINE (6-GATE RED-TEAM + 10K MC ON FTMO 10K/25K + THE5ERS 5K)
# ==============================================================================

def _build_lab12_firms() -> list[dict[str, Any]]:
    """Load FTMO Swing 10K, calibrated FTMO Swing 25K (270 USD fee), and The5ers High Stakes 5K."""
    f10 = load_firm_config("ftmo_swing_10k")
    f25 = {**f10, "id": "FTMO_SWING_25K", "capital_usd": 25000.0, "fee_usd": 270.0}
    f5 = load_firm_config("the5ers_high_stakes_5k")
    return [f10, f25, f5]


def run_lab12(*, n_mc_paths: int = N_MC_PATHS, write_report: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    red_news = load_red_news_calendar("red_news_official_2018_2024")
    inc_tapes_1x = dict(warm["tapes"])
    ext_days = list(warm["ext_days"])
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    live8_risks = {k: base_r[k] for k in INCUMBENT_LIVE8}

    canonical_inc_days = sorted(
        set(ext_days) | {dk for eng in INCUMBENT_LIVE8 for dk in inc_tapes_1x[eng]}
    )
    enforce_pre_holdout_dates(canonical_inc_days, context="lab12.canonical_inc_days")

    _, inc_ex_1x = replay_lab11_portfolio_m1(
        canonical_inc_days, inc_tapes_1x, live8_risks, 10000.0,
        profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
    )
    inc_day_ret = {e["day"]: float(e["net_usd"]) / 10000.0 for e in inc_ex_1x}
    inc_vec_all = np.array([inc_day_ret.get(d, 0.0) for d in canonical_inc_days], dtype=np.float64)

    single_inc_vecs: dict[str, np.ndarray] = {}
    for eng in INCUMBENT_LIVE8:
        gt, _ = p28.apply_red_news_guard_to_tape(inc_tapes_1x[eng], red_news, mode="FLATTEN_5M", pad_sec=300)
        single_inc_vecs[eng] = np.array([float(gt[d][0]["net_R"]) if d in gt else 0.0 for d in canonical_inc_days], dtype=np.float64)

    # Load all 7 target M1 Bid/Ask assets locally from sealed hot-m1-cache (< 2025-01-01)
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, q_j, _ = hcache.load_asset("USDJPY", verify_sha=False)
    enforce_pre_holdout_ts(int(ts_j[-1]), stop_ts=STOP, context="lab12.usdjpy")
    day_j = (ts_j // 86400).astype(np.int64)
    chg_j = np.r_[True, day_j[1:] != day_j[:-1]]
    starts_j = np.flatnonzero(chg_j)
    ends_j = np.r_[starts_j[1:] - 1, len(day_j) - 1]
    usdjpy_close_map = {
        datetime.fromtimestamp(int(ts_j[ei]), timezone.utc).date(): float(q_j[ei, 3])
        for ei in ends_j
    }

    catalog = build_lab12_catalog()
    m_total = len(catalog)
    needed_assets = ("AUDUSD", "EURUSD", "GBPJPY", "GER40", "US500", "USDCAD", "XAUUSD")
    bundles = {a: build_causal_m1_bundle_v2(a, swing_specs, usdjpy_close_map) for a in needed_assets}

    cand_records: list[dict[str, Any]] = []
    cand_tapes_1x: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
    cand_tapes_15x: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
    p_raw_b_list: list[float] = []

    for idx, cfg in enumerate(catalog):
        cid = cfg["id"]
        raw_tape, fade_map = evaluate_lab12_spec(bundles, cfg)
        tape_1x, tape_15x, news_st = apply_red_news_and_15x_stress(raw_tape, red_news)
        cand_tapes_1x[cid] = tape_1x
        cand_tapes_15x[cid] = tape_15x

        st_a1 = _tape_split_metrics(tape_1x, CLUSTER_A_YEARS)
        st_b1 = _tape_split_metrics(tape_1x, CLUSTER_B_YEARS)
        st_b15 = _tape_split_metrics(tape_15x, CLUSTER_B_YEARS)
        st_all1 = _tape_split_metrics(tape_1x, set(ALL_DEV_YEARS))
        st_all15 = _tape_split_metrics(tape_15x, set(ALL_DEV_YEARS))

        yr_r = {str(y): 0.0 for y in ALL_DEV_YEARS}
        for dk, (row, _st, _mk) in tape_1x.items():
            yr_r[str(row["year"])] += float(row["net_R"])
        yr_r = {y: round(v, 2) for y, v in yr_r.items()}
        pos_years = sum(1 for v in yr_r.values() if v > 0.0)
        tot_r = float(fsum(yr_r.values()))
        max_yr_r = max(yr_r.values())
        max_yr_share_pct = round(100.0 * max_yr_r / tot_r, 1) if tot_r > 1e-6 else 100.0

        cand_vec_all = np.array([float(tape_1x[d][0]["net_R"]) if d in tape_1x else 0.0 for d in canonical_inc_days], dtype=np.float64)
        corr_live8 = _safe_corr(cand_vec_all, inc_vec_all)
        single_corrs = {eng: _safe_corr(cand_vec_all, vec) for eng, vec in single_inc_vecs.items()}
        max_single_eng, max_single_corr = max(single_corrs.items(), key=lambda kv: abs(kv[1]))

        b_days = [d for d in canonical_inc_days if int(d[:4]) in CLUSTER_B_YEARS]
        r_b_daily = np.array([float(tape_1x[d][0]["net_R"]) * 0.005 if d in tape_1x else 0.0 for d in b_days], dtype=np.float64)
        dsr_b = deflated_sharpe_ratio(r_b_daily, n_trials=m_total, annualization=252.0)

        b_trade_days = sorted(dk for dk in tape_1x if int(dk[:4]) in CLUSTER_B_YEARS)
        if len(b_trade_days) >= 10:
            obs_arr = np.array([float(tape_1x[dk][0]["net_R"]) for dk in b_trade_days], dtype=np.float64)
            fade_arr = np.array([float(fade_map.get(dk, -tape_1x[dk][0]["net_R"])) for dk in b_trade_days], dtype=np.float64)
            p_sf_b = float(sign_flip_p_numba(obs_arr, fade_arr, draws=SIGN_FLIP_DRAWS, seed=SEED + 100 + idx))
        else:
            p_sf_b = 1.0
        p_raw_b_list.append(p_sf_b)

        g1_pass = (st_b1["pf"] >= 1.15) and (st_b1["net_R"] > 0.0) and (st_b1["n"] >= 60)
        g2_pass = st_b15["ann_R"] > 0.0
        g3_pass = (abs(corr_live8) < 0.25) and (abs(max_single_corr) < 0.35)
        g4_pass = (pos_years >= 5) and (tot_r > 0.0) and (max_yr_share_pct <= 60.0)

        failed_gates = []
        if not g1_pass:
            failed_gates.append("G1_CLB_PF_OR_N")
        if not g2_pass:
            failed_gates.append("G2_STRESS_15X")
        if not g3_pass:
            failed_gates.append("G3_ORTHOGONALITY")
        if not g4_pass:
            failed_gates.append("G4_YEAR_STABILITY")

        cand_records.append({
            "id": cid,
            "family": cfg["family"],
            "asset": cfg["asset"],
            "kind": cfg["kind"],
            "rationale": cfg["rationale"],
            "swap_usd_total": 0.0,
            "news_guard_stats": news_st,
            "cluster_a_1x": st_a1,
            "cluster_b_1x": st_b1,
            "cluster_b_15x": st_b15,
            "full_1x": st_all1,
            "full_15x": st_all15,
            "yearly_R": yr_r,
            "pos_years": pos_years,
            "max_yr_share_pct": max_yr_share_pct,
            "corr_vs_live8": corr_live8,
            "max_single_inc_engine": max_single_eng,
            "max_single_inc_corr": max_single_corr,
            "p_signflip_b": round(p_sf_b, 5),
            "p_bonf_b": round(min(1.0, m_total * p_sf_b), 5),
            "dsr_b": dsr_b,
            "gates": {
                "G1_clb_pf_n": g1_pass,
                "G2_stress_15x": g2_pass,
                "G3_orthogonality": g3_pass,
                "G4_year_stability": g4_pass,
            },
            "failed_gates": failed_gates,
        })

    bh_qs = benjamini_hochberg(p_raw_b_list)
    approved_ids: list[str] = []
    for rec, qv in zip(cand_records, bh_qs):
        rec["bh_q_b"] = round(float(qv), 5)
        if not rec["failed_gates"]:
            rec["verdict"] = "APPROVE_FOR_INCUBATION"
            approved_ids.append(rec["id"])
        elif len(rec["failed_gates"]) == 1 and rec["gates"]["G1_clb_pf_n"] and rec["gates"]["G2_stress_15x"]:
            rec["verdict"] = "NEAR_MISS_REJECTED"
        else:
            rec["verdict"] = "REJECT_KILLED"

    # Gate 5: 10,000-Path Prop Portfolio Accretion across FTMO 10K, FTMO 25K, The5ers 5K
    all_tapes_1x = dict(inc_tapes_1x)
    all_tapes_15x = _apply_cost_stress_existing_tapes(inc_tapes_1x, 1.5)
    for cid in cand_tapes_1x:
        all_tapes_1x[cid] = cand_tapes_1x[cid]
        all_tapes_15x[cid] = cand_tapes_15x[cid]

    port_configs: list[tuple[str, str, dict[str, float]]] = [
        ("A1_V1_LIVE8_BASE", "Incumbent 8 live engines (E1..E7 + S6)", dict(live8_risks)),
    ]
    if approved_ids:
        add_risks = {**live8_risks, **{cid: 0.0045 for cid in approved_ids}}
        port_configs.append((
            "V2_LIVE8_PLUS_LAB12_ADD",
            f"A1_V1_LIVE8 + {len(approved_ids)} Approved Lab #12 (+0.45% each, additive breadth)",
            add_risks,
        ))
        sum_base = sum(live8_risks.values())
        s_add = sum(add_risks.values())
        norm_risks = {k: round(v * (sum_base / s_add), 6) for k, v in add_risks.items()}
        port_configs.append((
            "V2_LIVE8_PLUS_LAB12_RISKMATCH",
            f"A1_V1_LIVE8 + {len(approved_ids)} Approved Lab #12 (risk-budget matched to live8)",
            norm_risks,
        ))
    else:
        ranked_cf = sorted(cand_records, key=lambda r: (r["cluster_b_15x"]["ann_R"], r["cluster_b_1x"]["pf"]), reverse=True)
        top1_cf = ranked_cf[0]
        port_configs.append((
            "DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED",
            f"Diagnostic ONLY (NOT promoted): live8 + top non-approved {top1_cf['id']}",
            {**live8_risks, top1_cf["id"]: 0.0045},
        ))

    union_days = sorted(
        set(canonical_inc_days)
        | {dk for _pid, _desc, rmap in port_configs for eng in rmap for dk in all_tapes_1x[eng]}
    )
    enforce_pre_holdout_dates(union_days, context="lab12.union_days")

    firms = _build_lab12_firms()
    idx_mat = make_block_bootstrap_indices(len(union_days), horizon=504, n_paths=n_mc_paths, block_len=5, seed=SEED)

    accretion_results: list[dict[str, Any]] = []
    for pid, desc, rmap in port_configs:
        m1_1x, ex_1x = replay_lab11_portfolio_m1(
            union_days, all_tapes_1x, rmap, 10000.0,
            profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
        )
        m1_15x, _ = replay_lab11_portfolio_m1(
            union_days, all_tapes_15x, rmap, 10000.0,
            profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
        )
        rmap_p1 = {k: v * 4.0 for k, v in rmap.items()}
        m1_p1, ex_p1 = replay_lab11_portfolio_m1(
            union_days, all_tapes_1x, rmap_p1, 10000.0,
            profile_mode="Swing", max_symbol_concurrent_risk=P1_SYMCAP_TIGHT, red_news_cal=red_news,
        )
        nets_core, dds_core, flg_core = exits_to_daily_arrays(union_days, ex_1x, 10000.0)
        nets_p1, dds_p1, flg_p1 = exits_to_daily_arrays(union_days, ex_p1, 10000.0)
        mc_10k = evaluate_prop_accretion_mc(
            nets_p1, dds_p1, flg_p1,
            nets_core, dds_core, flg_core,
            idx_mat, firms,
        )
        accretion_results.append({
            "portfolio_id": pid,
            "description": desc,
            "n_engines": len(rmap),
            "risk_weights_pct": {k: round(v * 100.0, 4) for k, v in rmap.items()},
            "m1_1x": m1_1x,
            "m1_15x": m1_15x,
            "p1_symcap175_hits": m1_p1["sym_cap_hits"],
            "prop_mc_10k": mc_10k,
        })

    fam_summary: dict[str, dict[str, int]] = {}
    for rec in cand_records:
        f = rec["family"]
        fam_summary.setdefault(f, {"tested": 0, "approved": 0, "g1_pass": 0, "g2_pass": 0, "g3_pass": 0, "g4_pass": 0})
        fam_summary[f]["tested"] += 1
        fam_summary[f]["approved"] += int(rec["verdict"] == "APPROVE_FOR_INCUBATION")
        fam_summary[f]["g1_pass"] += int(rec["gates"]["G1_clb_pf_n"])
        fam_summary[f]["g2_pass"] += int(rec["gates"]["G2_stress_15x"])
        fam_summary[f]["g3_pass"] += int(rec["gates"]["G3_orthogonality"])
        fam_summary[f]["g4_pass"] += int(rec["gates"]["G4_year_stability"])

    decision = (
        f"APPROVE_{len(approved_ids)}_INCUBATION_CANDIDATES"
        if approved_ids
        else "ZERO_APPROVED_36_TOTAL_PARETO_FRONTIER_A1_V1_LIVE8"
    )

    payload: dict[str, Any] = {
        "schema": "naqex-lab12-orthogonal-momentum-v2-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "holdout_rows_analysed": 0,
        "holdout_lock_sha256": lock_sha,
        "dev_window": ["2018-01-02", "2024-12-31"],
        "cluster_a_years": sorted(CLUSTER_A_YEARS),
        "cluster_b_years": sorted(CLUSTER_B_YEARS),
        "m_total": m_total,
        "cumulative_lab11_plus_lab12_tested": 20 + m_total,
        "mc_paths": int(n_mc_paths),
        "mc_seed": int(SEED),
        "funded_symcap_pct": round(FUNDED_SYMCAP * 100.0, 2),
        "p1_symcap_tight_pct": round(P1_SYMCAP_TIGHT * 100.0, 2),
        "red_news_filter": "red_news_official_2018_2024 FLATTEN_5M (+-300s)",
        "n_approved": len(approved_ids),
        "approved_ids": approved_ids,
        "executive_decision": decision,
        "family_summary": fam_summary,
        "candidates": cand_records,
        "accretion_comparison": accretion_results,
    }

    if write_report:
        json_path = REPORT_DIR / f"{REPORT_STEM}.json"
        write_verified_receipt(json_path, payload, overwrite=True)

    return payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Lab #12 Orthogonal Structural Momentum & Vol-Expansion Discovery")
    parser.add_argument("--mc-paths", type=int, default=N_MC_PATHS)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    out = run_lab12(n_mc_paths=args.mc_paths, write_report=not args.no_write)
    print(f"Lab #12 finished in {out['runtime_seconds']}s | Holdout rows={out['holdout_rows_analysed']} | Decision={out['executive_decision']}")
    print(f"Approved ({out['n_approved']}/{out['m_total']}): {out['approved_ids']}")
    print("-" * 138)
    print(f"{'ID':<32} {'Ast':<7} {'A1_n':>4} {'A1_PF':>5} {'B1_n':>4} {'B1_PF':>5} {'B1_R':>6} {'B15_aR':>6} {'PosY':>4} {'MaxY%':>6} {'rL8':>6} {'MaxE':>6} {'pSF_B':>7} {'qBH':>7} {'DSR':>5} {'Verdict'}")
    for c in out["candidates"]:
        a1, b1, b15 = c["cluster_a_1x"], c["cluster_b_1x"], c["cluster_b_15x"]
        print(
            f"{c['id']:<32} {c['asset']:<7} {a1['n']:>4} {a1['pf']:>5.2f} {b1['n']:>4} {b1['pf']:>5.2f} "
            f"{b1['net_R']:>6.1f} {b15['ann_R']:>6.2f} {c['pos_years']:>2}/7 {c['max_yr_share_pct']:>5.1f}% "
            f"{c['corr_vs_live8']:>6.3f} {c['max_single_inc_corr']:>6.3f} {c['p_signflip_b']:>7.4f} {c['bh_q_b']:>7.4f} "
            f"{c['dsr_b']['dsr']:>5.3f} {c['verdict']} {c['failed_gates']}"
        )
    print("-" * 138)
    for acc in out["accretion_comparison"]:
        m1, m15 = acc["m1_1x"], acc["m1_15x"]
        print(f"PORT {acc['portfolio_id']}: Ann1x={m1['ann_pct']['all']}% Sh1x={m1['sharpe_1x']} DD1x={m1['peak_dd_pct']}% Cal1x={m1['calmar']} Cal15x={m15['calmar']} P1SymCapHits={acc['p1_symcap175_hits']}")
        for fid, pmap in acc["prop_mc_10k"].items():
            for pname, st in pmap.items():
                print(
                    f"   {fid:<14} {pname:<25} Pass3m/6m/12m={st['pass_3m_pct']}%/{st['pass_6m_pct']}%/{st['pass_12m_pct']}% "
                    f"MedPass={st['med_days_pass']}d Br={st['breach_pct']}% Wp={st['wipeout_pct']}% EV24m={st['ev_24m_usd']} ({st['ev_per_fee']}x fee)"
                )


if __name__ == "__main__":
    main()
