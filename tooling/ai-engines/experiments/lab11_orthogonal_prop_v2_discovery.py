"""Wave-3 Cycle 1 — Lab #11: Orthogonal Non-Breakout & New-Asset Prop v2 Discovery (2018-2024 Dev ONLY).

Strategic Goal (TOP1-SOLO-QUANT-MASTER-PLAN.md):
  All 8 incumbent engines (`A1_V1_LIVE8`: E1..E7 + S6) are intraday trend/breakout on
  USDJPY/GBPUSD/EURJPY/US100/USD-basket. Lab #11 systematically tests `m_total = 20` clean,
  white-box, zero-grid, hard-SL, `swap = 0` intraday hypotheses across 4 genuinely non-breakout /
  new-asset families strictly on sealed Development M1 Bid/Ask data (`2018-01-02..2024-12-31`):
    - Family A: Intraday Mean-Reversion / Overextension Fade (EURUSD, AUDUSD, USDCAD, US500, GER40)
    - Family B: Gold (`XAUUSD`) Structural Intraday Mechanics (Asia-London, AM/PM Fix, COMEX)
    - Family C: European Index (`GER40` DAX) Cash-Session & Cross-Index Lead-Lag (`GER40` vs `US500`)
    - Family D: `BTCUSD` Intraday / Weekend Session Mechanics & `GBPJPY` Non-Breakout Fade

STRICT SAFETY & ANTI-BIAS INVARIANTS:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 integrity on startup (`holdout_rows_analysed = 0`).
  - Reads ONLY local D: SSD `.runtime/hot-m1-cache/` verified `< 2025-01-01T00:00:00Z`.
  - `ORDER_SEND_CAPABLE = False` (`OrderSend = 0`), ZERO network/API calls.
  - Strict `shift = 1` daily indicators (ATR14, prev OHLC), strict `< entry_ts` intraday features,
    conservative M1 SL-before-TP tie-break (`f_sl <= f_tp`), hard intraday flat before `20:50 UTC`
    (`swap = 0`), and official `2018-2024` red-news `±5m` guard (`FLATTEN_5M`) applied to EVERY tape!
  - Pre-registered split: Cluster A (`2018-2020`, 3y) -> Blind Cluster B (`2021-2024`, 4y), with exact
    `m_total = 20` multiple-testing tracking (Bonferroni, BH-FDR, Deflated Sharpe Ratio, Sign-Flip Null).
  - Hard 6-Gate Red-Team Filter + 10,000-path Block Bootstrap Prop Portfolio Accretion MC (`seed=20261124`)
    across `FTMO Swing 10K` and `The5ers High Stakes 5K` (`P1_Balanced` w/ tightened `SYMCAP 1.75%`
    & `Dyn_ProfitLock_45x`).
  - Retains ALL negative/failed candidates honestly (zero cherry-picking!).
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timezone
import json
import math
from math import fsum, isclose
from pathlib import Path
import sys
import time
from typing import Any
from zoneinfo import ZoneInfo

from numba import njit
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass24_mtf_new_archetypes as p24
import pass27_portfolio_m1_phase_audit as p27
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
from quant_factory.prop_engine import make_block_bootstrap_indices, replay_portfolio_m1
from quant_factory.prop_ev_frontier import exits_to_daily_arrays
from quant_factory.report_gen import format_markdown_table, write_verified_receipt

ORDER_SEND_CAPABLE: bool = False
SEED: int = 20261124
N_MC_PATHS: int = 10_000
SIGN_FLIP_DRAWS: int = 1000

NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")
BERLIN_TZ = ZoneInfo("Europe/Berlin")

CLUSTER_A_YEARS = frozenset({2018, 2019, 2020})
CLUSTER_B_YEARS = frozenset({2021, 2022, 2023, 2024})
ALL_DEV_YEARS = tuple(range(2018, 2025))

FUNDED_SYMCAP: float = 0.0100   # 1.00% per-symbol concurrent risk cap on Funded_Safe (1.0x)
P1_SYMCAP_TIGHT: float = 0.0175 # 1.75% tightened per-symbol concurrent risk cap on P1 (Top-1% Master Plan Patch #3)

INCUMBENT_LIVE8: tuple[str, ...] = (
    "E1_USDJPY_TOKYO",
    "E2_USDJPY_EXP80",
    "E3_GBPUSD_VH",
    "E4_US100_SESS40",
    "E5_US100_RS1130",
    "E6_EURJPY_VOLCOMP",
    "E7_USDJPY_NY10ET",
    "S6_FX_USD_BSK",
)

REPORT_DIR = ROOT / "planning/research"
REPORT_STEM = "LAB11-ORTHOGONAL-PROP-V2-DISCOVERY-20261124"


def local_ts(day_iso: str, hour: int, minute: int, tz: ZoneInfo) -> int:
    d = date.fromisoformat(day_iso)
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz).timestamp())


# ==============================================================================
# 1. LOCAL M1 BID/ASK BUNDLE BUILDER (STRICTLY < 2025-01-01, SHIFT=1 INDICATORS)
# ==============================================================================

def build_causal_m1_bundle(
    asset: str,
    swing_specs: dict[str, dict],
    usdjpy_close_map: dict[date, float],
    *,
    include_weekends: bool = False,
    cache_dir: Path = hcache.DEFAULT_CACHE,
) -> dict[str, Any]:
    """Load sealed local M1 Bid/Ask bars (`< 2025-01-01`) and compute strictly causal `shift=1` D1 ATR14."""
    times, quotes, am = hcache.load_asset(asset, cache_dir=cache_dir, verify_sha=False)
    enforce_pre_holdout_ts(int(times[-1]), stop_ts=STOP, context=f"lab11:{asset}")
    if int(times[0]) < START - 86400 * 60:
        raise HoldoutLockError(f"UNEXPECTED_START:{asset}")
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
        if (not include_weekends) and dt0.weekday() >= 5:
            continue
        if (e_i - s_i + 1) < 120:
            continue
        d_iso = dt0.date().isoformat()
        if d_iso >= "2025-01-01":
            raise HoldoutLockError(f"HOLDOUT_CONTAMINATION_DAY:{asset}:{d_iso}")
        dsec = int(datetime(dt0.year, dt0.month, dt0.day, tzinfo=timezone.utc).timestamp())
        # Hard flat strictly before 20:50 UTC (zero overnight rollover / swap = 0 invariant!)
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

    # Strictly causal shift=1 daily ATR14 & prior-day OHLC (computed ONLY from days <= t-1!)
    days_out: list[dict[str, Any]] = []
    trs: list[float] = []
    for i, d in enumerate(raw_days):
        if i == 0:
            trs.append(max(1e-9, d["h"] - d["l"]))
            continue
        prev = raw_days[i - 1]
        prev2_c = raw_days[i - 2]["c"] if i >= 2 else prev["o"]
        tr_prev = max(
            prev["h"] - prev["l"],
            abs(prev["h"] - prev2_c),
            abs(prev["l"] - prev2_c),
        )
        if i >= 2:
            trs.append(max(1e-9, tr_prev))
        if len(trs) >= 14:
            atr14 = float(np.mean(trs[-14:]))
            days_out.append({
                **d,
                "prev_o": prev["o"],
                "prev_h": prev["h"],
                "prev_l": prev["l"],
                "prev_c": prev["c"],
                "prev_day": prev["day"],
                "atr": max(1e-9, atr14),
            })

    spec_key = asset if asset in swing_specs else ("US500.cash" if asset == "US500" else None)
    spec = swing_specs[spec_key] if spec_key and spec_key in swing_specs else None
    day_map = {d["day"]: d for d in days_out}
    return {
        "asset": asset,
        "times": times,
        "quotes": quotes,
        "spec": spec,
        "usdjpy_close_map": usdjpy_close_map,
        "days": days_out,
        "day_map": day_map,
        "meta": am,
    }


def _causal_window_stats(bundle: dict[str, Any], ts_start: int, ts_end: int) -> dict[str, float] | None:
    """Compute strictly causal intraday window stats over bars with `ts_start <= t < ts_end` (ZERO lookahead)."""
    times, quotes = bundle["times"], bundle["quotes"]
    i0 = int(times.searchsorted(ts_start, side="left"))
    i1 = int(times.searchsorted(ts_end, side="left"))
    if i1 - i0 < 15:
        return None
    sub = quotes[i0:i1]
    # Mid-price open/high/low/close and equal-time TWAP/VWAP proxy across M1 bars
    mid_o = 0.5 * (float(sub[0, 0]) + float(sub[0, 4]))
    mid_c = 0.5 * (float(sub[-1, 3]) + float(sub[-1, 7]))
    mid_h = float(np.max(0.5 * (sub[:, 1] + sub[:, 5])))
    mid_l = float(np.min(0.5 * (sub[:, 2] + sub[:, 6])))
    typical = 0.5 * ((sub[:, 1] + sub[:, 2] + sub[:, 3]) / 3.0 + (sub[:, 5] + sub[:, 6] + sub[:, 7]) / 3.0)
    vwap = float(np.mean(typical))
    rng = max(1e-9, mid_h - mid_l)
    return {
        "open": mid_o,
        "close": mid_c,
        "high": mid_h,
        "low": mid_l,
        "vwap": vwap,
        "ret": mid_c - mid_o,
        "range": rng,
        "close_pos": (mid_c - mid_l) / rng,
        "n_bars": float(i1 - i0),
    }


# ==============================================================================
# 2. EXACT M1 BID/ASK TAPE REPLAY (SL-BEFORE-TP, SWAP=0, 1.0x & 1.5x STRESS)
# ==============================================================================

def _lot_scale_and_cost(
    asset: str,
    entry_p: float,
    ex_p: float,
    x_ts: int,
    spec: dict | None,
    usdjpy_close_map: dict[date, float],
) -> tuple[float, float, float]:
    """Return `(scale_usd_per_pt, drag_1x_usd, drag_15x_usd)` per 1.00 lot."""
    c = p24.asset_cost_tiers(asset)
    if c.get("is_crypto"):
        scale = 1.0
        drag_1x = entry_p * float(c["stress_pct"])
        drag_15x = 1.5 * drag_1x
        return scale, drag_1x, drag_15x
    if c["is_index"]:
        # FTMO CFD index contract: US100/US500 = 1 USD/pt, GER40 = 1 EUR/pt (~1.10 USD/pt conservative)
        conv = 1.10 if asset == "GER40" else 1.0
        scale = 1.0 * conv
        drag_1x = float(c["stress"]) * scale
        drag_15x = 1.5 * drag_1x
        return scale, drag_1x, drag_15x
    assert spec is not None, f"Missing swing spec for {asset}"
    cs = float(spec["trade_contract_size"])
    cp = spec.get("currency_profit", "USD")
    if cp == "USD":
        conv = 1.0
    elif cp == "JPY":
        d_ex = datetime.fromtimestamp(x_ts, timezone.utc).date()
        conv = 1.0 / max(50.0, float(usdjpy_close_map.get(d_ex, ex_p) if asset != "USDJPY" else ex_p))
    elif cp in ("CAD", "CHF"):
        conv = 1.0 / max(0.2, ex_p)
    else:
        conv = 1.0
    scale = cs * conv
    drag_1x = float(c["comm_usd"]) + float(c["stress"]) * scale
    drag_15x = 1.5 * drag_1x
    return scale, drag_1x, drag_15x


def replay_intraday_tape_trade(
    bundle: dict[str, Any],
    e_idx: int,
    flat_idx: int,
    side: int,
    sl_dist: float,
    *,
    tp_dist: float | None = None,
) -> tuple[dict[str, Any], np.ndarray, np.ndarray, float] | None:
    """Replay single causal M1 Bid/Ask trade (`swap = 0`, conservative SL-before-TP tie-break).

    Returns `(row, stamps, marks_1x, fade_r_1x)` where `marks_1x` is exact minute-by-minute
    floating PnL in USD per 1.00 lot reconciled to terminal `net_usd_per_lot`, and `fade_r_1x`
    is the opposite-side control trade R for exact sign-flip permutation testing.
    """
    times, quotes = bundle["times"], bundle["quotes"]
    asset = bundle["asset"]
    if sl_dist <= 1e-9 or e_idx < 0 or flat_idx <= e_idx:
        return None

    ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
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

    # Conservative M1 tie-break: SL ALWAYS fills before TP if both touch on the same M1 bar!
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
    enforce_pre_holdout_ts(stamps, START, STOP, context=f"lab11.trade:{asset}")

    # Verify swap = 0 (strictly closed same UTC day before 20:55 UTC)
    dt_e = datetime.fromtimestamp(int(stamps[0]), timezone.utc)
    dt_x = datetime.fromtimestamp(int(stamps[-1]), timezone.utc)
    assert dt_e.date() == dt_x.date(), f"OVERNIGHT_HOLD_DETECTED:{asset}:{dt_e.date()}->{dt_x.date()}"
    assert (dt_x.hour * 60 + dt_x.minute) <= 20 * 60 + 55, f"ROLLOVER_BREACH:{asset}:{dt_x}"

    scale, drag_1x, drag_15x = _lot_scale_and_cost(
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

    # Opposite-side trade R for exact sign-flip permutation null
    fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
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


def apply_red_news_and_15x_stress(
    raw_tape: dict[str, tuple[dict, np.ndarray, np.ndarray]],
    red_news_cal: dict[str, list[tuple[int, str]]],
) -> tuple[dict[str, tuple[dict, np.ndarray, np.ndarray]], dict[str, tuple[dict, np.ndarray, np.ndarray]], dict]:
    """Apply official 2018-2024 ±5m red-news guard and produce exact 1.0x and 1.5x stressed M1 tapes."""
    tape_1x, news_stats = p28.apply_red_news_guard_to_tape(raw_tape, red_news_cal, mode="FLATTEN_5M", pad_sec=300)
    tape_15x: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
    for dk, (row, stamps, marks) in tape_1x.items():
        base_f = float(row.get("base_friction_usd") or max(0.0, float(row["stop_risk_with_cost_usd"]) - float(row.get("initial_risk_usd", 0.0))))
        extra = 0.5 * base_f
        new_stop = float(row["stop_risk_with_cost_usd"]) + extra
        new_net = float(row["net_usd_per_lot"]) - extra
        new_marks = np.maximum(np.asarray(marks, dtype=np.float64) - extra, -new_stop)
        new_marks[-1, -1] = new_net
        new_row = {
            **row,
            "stop_risk_with_cost_usd": new_stop,
            "net_usd_per_lot": new_net,
            "net_R": float(new_net / max(1e-9, new_stop)),
        }
        tape_15x[dk] = (new_row, stamps, new_marks)
    return tape_1x, tape_15x, news_stats


# ==============================================================================
# 3. PRE-REGISTERED M = 20 ORTHOGONAL NON-BREAKOUT / NEW-ASSET CATALOG
# ==============================================================================

def build_lab11_catalog() -> list[dict[str, Any]]:
    """Pre-registered `m_total = 20` white-box non-breakout & new-asset hypotheses (4 families x 5 specs)."""
    return [
        # ---- FAMILY A: Intraday Mean-Reversion / Overextension Fade (FX & Equity Indices) ----
        {
            "id": "L11_A1_EURUSD_LDN_STRETCH_FADE",
            "family": "A_INTRADAY_MR_FADE",
            "asset": "EURUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.70, "sl_atr": 0.65, "tp_atr": 0.85,
            "win_start": (7, 0, "UTC"), "entry_hm": (12, 0, "UTC"), "flat_hm": (19, 30, "UTC"),
            "rationale": "EURUSD London morning spikes >= 0.70 ATR exhaust dealer flow and revert toward open into NY afternoon.",
        },
        {
            "id": "L11_A2_AUDUSD_ASIA_LDN_FADE",
            "family": "A_INTRADAY_MR_FADE",
            "asset": "AUDUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.60, "sl_atr": 0.65, "tp_atr": 0.80,
            "win_start": (0, 0, "UTC"), "entry_hm": (7, 0, "UTC"), "flat_hm": (15, 0, "UTC"),
            "rationale": "AUDUSD thin-liquidity Asian extension >= 0.60 ATR mean-reverts as London liquidity absorbs retail chase.",
        },
        {
            "id": "L11_A3_USDCAD_NY_VWAP_FADE",
            "family": "A_INTRADAY_MR_FADE",
            "asset": "USDCAD",
            "kind": "VWAP_STRETCH_FADE",
            "thr": 0.45, "sl_atr": 0.65, "tp_atr": 0.80,
            "win_start": (7, 0, "UTC"), "entry_hm": (13, 30, "UTC"), "flat_hm": (19, 30, "UTC"),
            "rationale": "USDCAD pre-NY deviation >= 0.45 ATR from intraday VWAP reverts during North American liquidity balance.",
        },
        {
            "id": "L11_A4_US500_OPEN_STRETCH_FADE",
            "family": "A_INTRADAY_MR_FADE",
            "asset": "US500",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.55, "sl_atr": 0.70, "tp_atr": 0.90,
            "win_start": (9, 30, "NY"), "entry_hm": (10, 30, "NY"), "flat_hm": (15, 45, "NY"),
            "rationale": "S&P 500 first-hour cash impulse >= 0.55 ATR overshoots fair value and mean-reverts through NY midday.",
        },
        {
            "id": "L11_A5_GER40_MIDDAY_VWAP_FADE",
            "family": "A_INTRADAY_MR_FADE",
            "asset": "GER40",
            "kind": "VWAP_STRETCH_FADE",
            "thr": 0.50, "sl_atr": 0.70, "tp_atr": 0.85,
            "win_start": (8, 0, "BERLIN"), "entry_hm": (11, 30, "BERLIN"), "flat_hm": (17, 15, "BERLIN"),
            "rationale": "DAX morning stretch >= 0.50 ATR from Frankfurt-session VWAP reverts into midday European consolidation.",
        },

        # ---- FAMILY B: Gold (XAUUSD) Structural Intraday Mechanics ----
        {
            "id": "L11_B1_XAU_ASIA_SWEEP_LDN_REV",
            "family": "B_GOLD_STRUCTURAL",
            "asset": "XAUUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.55, "sl_atr": 0.70, "tp_atr": 0.90,
            "win_start": (0, 0, "UTC"), "entry_hm": (7, 0, "UTC"), "flat_hm": (13, 0, "UTC"),
            "rationale": "Gold Asian-session liquidity sweep >= 0.55 ATR fades as London bullion desks re-anchor spot price.",
        },
        {
            "id": "L11_B2_XAU_LDN_AM_FIX_DRIFT",
            "family": "B_GOLD_STRUCTURAL",
            "asset": "XAUUSD",
            "kind": "FIX_DRIFT_MOM",
            "thr": 0.25, "sl_atr": 0.70, "tp_atr": 1.40,
            "win_start": (8, 0, "LONDON"), "entry_hm": (10, 35, "LONDON"), "flat_hm": (15, 0, "LONDON"),
            "rationale": "LBMA 10:30 AM London Gold Fix institutional order imbalance persists into COMEX liquidity overlap.",
        },
        {
            "id": "L11_B3_XAU_COMEX_OPEN_MR",
            "family": "B_GOLD_STRUCTURAL",
            "asset": "XAUUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.45, "sl_atr": 0.65, "tp_atr": 0.85,
            "win_start": (8, 20, "NY"), "entry_hm": (9, 20, "NY"), "flat_hm": (13, 30, "NY"),
            "rationale": "COMEX Gold open (08:20-09:20 ET) initial volatility burst >= 0.45 ATR fades into settlement window.",
        },
        {
            "id": "L11_B4_XAU_COMEX_CLOSE_MOM",
            "family": "B_GOLD_STRUCTURAL",
            "asset": "XAUUSD",
            "kind": "COMEX_TREND_ALIGN",
            "thr": 0.30, "sl_atr": 0.70, "tp_atr": 1.30,
            "win_start": (8, 20, "NY"), "entry_hm": (10, 30, "NY"), "flat_hm": (13, 30, "NY"),
            "rationale": "COMEX morning drift aligned with prior-day gold trend persists into 13:30 ET futures settlement.",
        },
        {
            "id": "L11_B5_XAU_PM_FIX_REVERT",
            "family": "B_GOLD_STRUCTURAL",
            "asset": "XAUUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.40, "sl_atr": 0.65, "tp_atr": 0.85,
            "win_start": (13, 0, "LONDON"), "entry_hm": (15, 5, "LONDON"), "flat_hm": (19, 30, "UTC"),
            "rationale": "LBMA 15:00 PM London Fix hedging spike >= 0.40 ATR mean-reverts once benchmark execution clears.",
        },

        # ---- FAMILY C: European Index (GER40 DAX) Cash-Session & Cross-Index Lead-Lag ----
        {
            "id": "L11_C1_GER40_CASH_OR30_MOM",
            "family": "C_GER40_AND_LEADLAG",
            "asset": "GER40",
            "kind": "GER40_OR30_MOM",
            "thr": 0.20, "sl_atr": 0.70, "tp_atr": 1.40,
            "win_start": (9, 0, "BERLIN"), "entry_hm": (9, 30, "BERLIN"), "flat_hm": (17, 20, "BERLIN"),
            "rationale": "Frankfurt Xetra cash open (09:00-09:30 CET) strong directional auction persists through European session.",
        },
        {
            "id": "L11_C2_GER40_CASH_OR30_FADE",
            "family": "C_GER40_AND_LEADLAG",
            "asset": "GER40",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.40, "sl_atr": 0.65, "tp_atr": 0.85,
            "win_start": (9, 0, "BERLIN"), "entry_hm": (9, 30, "BERLIN"), "flat_hm": (15, 0, "BERLIN"),
            "rationale": "Extreme >= 0.40 ATR Frankfurt cash-open auction gap overshoots institutional liquidity and reverts intraday.",
        },
        {
            "id": "L11_C3_GER40_VS_US500_REL_MR",
            "family": "C_GER40_AND_LEADLAG",
            "asset": "GER40",
            "kind": "CROSS_INDEX_REL_MR",
            "thr": 0.65, "sl_atr": 0.65, "tp_atr": 0.90,
            "win_start": (8, 0, "UTC"), "entry_hm": (14, 30, "UTC"), "flat_hm": (17, 25, "BERLIN"),
            "rationale": "Intraday GER40 vs US500 ATR-normalized divergence >= 0.65 reverts as US cash open re-prices global beta.",
        },
        {
            "id": "L11_C4_GER40_VS_US500_LEADLAG",
            "family": "C_GER40_AND_LEADLAG",
            "asset": "GER40",
            "kind": "US500_TO_GER40_LEAD",
            "thr": 0.30, "sl_atr": 0.70, "tp_atr": 1.20,
            "win_start": (0, 0, "UTC"), "entry_hm": (9, 0, "BERLIN"), "flat_hm": (13, 30, "BERLIN"),
            "rationale": "Overnight US500 futures impulse from prior NY close to EU open leads Xetra cash catch-up at 09:00 CET.",
        },
        {
            "id": "L11_C5_GER40_PRE_US_DRIFT",
            "family": "C_GER40_AND_LEADLAG",
            "asset": "GER40",
            "kind": "GER40_AFTERNOON_CONT",
            "thr": 0.35, "sl_atr": 0.70, "tp_atr": 1.30,
            "win_start": (9, 0, "BERLIN"), "entry_hm": (13, 30, "BERLIN"), "flat_hm": (17, 25, "BERLIN"),
            "rationale": "DAX strong morning trend closing near session extreme continues through European cash closing auction.",
        },

        # ---- FAMILY D: BTCUSD Intraday/Weekend Mechanics & GBPJPY Non-Breakout Fade ----
        {
            "id": "L11_D1_BTC_WEEKEND_MR_FADE",
            "family": "D_BTC_AND_GBPJPY_MR",
            "asset": "BTCUSD",
            "kind": "BTC_WEEKEND_FADE",
            "thr": 0.55, "sl_atr": 0.75, "tp_atr": 1.00,
            "win_start": (0, 0, "UTC"), "entry_hm": (8, 0, "UTC"), "flat_hm": (20, 30, "UTC"),
            "rationale": "Weekend BTCUSD low-depth retail stop-runs >= 0.55 ATR revert intraday before UTC close (0% FX overlap!).",
        },
        {
            "id": "L11_D2_BTC_US_OPEN_MOM",
            "family": "D_BTC_AND_GBPJPY_MR",
            "asset": "BTCUSD",
            "kind": "BTC_US_TREND_MOM",
            "thr": 0.35, "sl_atr": 0.75, "tp_atr": 1.50,
            "win_start": (13, 30, "UTC"), "entry_hm": (15, 0, "UTC"), "flat_hm": (20, 30, "UTC"),
            "rationale": "Weekday BTCUSD US institutional cash/CME open impulse aligned with prior-day trend persists into NY close.",
        },
        {
            "id": "L11_D3_BTC_ASIA_STRETCH_FADE",
            "family": "D_BTC_AND_GBPJPY_MR",
            "asset": "BTCUSD",
            "kind": "SESSION_STRETCH_FADE",
            "thr": 0.65, "sl_atr": 0.75, "tp_atr": 1.00,
            "win_start": (0, 0, "UTC"), "entry_hm": (7, 0, "UTC"), "flat_hm": (20, 30, "UTC"),
            "rationale": "BTCUSD Asian leverage spike >= 0.65 ATR mean-reverts during European/US institutional trading hours.",
        },
        {
            "id": "L11_D4_GBPJPY_LDN_OVEREXT_FADE",
            "family": "D_BTC_AND_GBPJPY_MR",
            "asset": "GBPJPY",
            "kind": "VWAP_STRETCH_FADE",
            "thr": 0.55, "sl_atr": 0.70, "tp_atr": 0.90,
            "win_start": (7, 0, "UTC"), "entry_hm": (11, 30, "UTC"), "flat_hm": (19, 30, "UTC"),
            "rationale": "GBPJPY non-breakout fade of extreme London morning deviation >= 0.55 ATR from session VWAP.",
        },
        {
            "id": "L11_D5_GBPJPY_PRIOR_DAY_REV",
            "family": "D_BTC_AND_GBPJPY_MR",
            "asset": "GBPJPY",
            "kind": "PRIOR_DAY_EXHAUST_FADE",
            "thr": 1.10, "sl_atr": 0.70, "tp_atr": 1.00,
            "win_start": (0, 0, "UTC"), "entry_hm": (7, 30, "UTC"), "flat_hm": (19, 30, "UTC"),
            "rationale": "After an extreme prior-day GBPJPY move >= 1.10 ATR without Asian continuation, fade into London liquidity.",
        },
    ]


def _resolve_ts(day_iso: str, hm_tz: tuple[int, int, str]) -> int:
    h, m, tz_name = hm_tz
    if tz_name == "UTC":
        d = date.fromisoformat(day_iso)
        return int(datetime(d.year, d.month, d.day, h, m, tzinfo=timezone.utc).timestamp())
    tz = {"NY": NY_TZ, "LONDON": LONDON_TZ, "BERLIN": BERLIN_TZ}[tz_name]
    return local_ts(day_iso, h, m, tz)


def evaluate_lab11_spec(
    bundles: dict[str, dict[str, Any]],
    cfg: dict[str, Any],
) -> tuple[dict[str, tuple[dict, np.ndarray, np.ndarray]], dict[str, float]]:
    """Generate exact causal M1 trade tape + opposite-side fade_R map for one pre-registered Lab #11 spec."""
    asset = cfg["asset"]
    kind = cfg["kind"]
    thr = float(cfg["thr"])
    sl_atr = float(cfg["sl_atr"])
    tp_atr = float(cfg["tp_atr"]) if cfg.get("tp_atr") is not None else None
    b = bundles[asset]
    times = b["times"]

    raw_tape: dict[str, tuple[dict, np.ndarray, np.ndarray]] = {}
    fade_r_by_day: dict[str, float] = {}

    for d in b["days"]:
        dk = d["day"]
        atr = float(d["atr"])
        if atr <= 1e-9:
            continue

        # Weekend filter for BTC_WEEKEND_FADE / BTC_US_TREND_MOM
        if kind == "BTC_WEEKEND_FADE" and d["weekday"] < 5:
            continue
        if kind == "BTC_US_TREND_MOM" and d["weekday"] >= 5:
            continue

        ts_ws = _resolve_ts(dk, cfg["win_start"])
        ts_e = _resolve_ts(dk, cfg["entry_hm"])
        ts_f = _resolve_ts(dk, cfg["flat_hm"])
        if ts_e >= ts_f:
            continue

        side = 0
        if kind in ("SESSION_STRETCH_FADE", "BTC_WEEKEND_FADE"):
            st = _causal_window_stats(b, ts_ws, ts_e)
            if st is not None:
                z = st["ret"] / atr
                if abs(z) >= thr:
                    side = -1 if z > 0.0 else 1

        elif kind == "VWAP_STRETCH_FADE":
            st = _causal_window_stats(b, ts_ws, ts_e)
            if st is not None:
                z = (st["close"] - st["vwap"]) / atr
                if abs(z) >= thr:
                    side = -1 if z > 0.0 else 1

        elif kind == "FIX_DRIFT_MOM":
            st = _causal_window_stats(b, ts_ws, ts_e)
            if st is not None:
                z = st["ret"] / atr
                if abs(z) >= thr:
                    side = 1 if z > 0.0 else -1

        elif kind in ("COMEX_TREND_ALIGN", "BTC_US_TREND_MOM"):
            st = _causal_window_stats(b, ts_ws, ts_e)
            prev_dir = 1 if (d["prev_c"] > d["prev_o"]) else (-1 if d["prev_c"] < d["prev_o"] else 0)
            if st is not None and prev_dir != 0:
                z = st["ret"] / atr
                if abs(z) >= thr and (1 if z > 0.0 else -1) == prev_dir:
                    side = prev_dir

        elif kind == "GER40_OR30_MOM":
            st = _causal_window_stats(b, ts_ws, ts_e)
            if st is not None:
                z = st["ret"] / atr
                if z >= thr and st["close_pos"] >= 0.75:
                    side = 1
                elif z <= -thr and st["close_pos"] <= 0.25:
                    side = -1

        elif kind == "GER40_AFTERNOON_CONT":
            st = _causal_window_stats(b, ts_ws, ts_e)
            if st is not None:
                z = st["ret"] / atr
                if z >= thr and st["close_pos"] >= 0.70:
                    side = 1
                elif z <= -thr and st["close_pos"] <= 0.30:
                    side = -1

        elif kind == "CROSS_INDEX_REL_MR":
            b_us = bundles["US500"]
            d_us = b_us["day_map"].get(dk)
            if d_us is not None:
                st_g = _causal_window_stats(b, ts_ws, ts_e)
                st_u = _causal_window_stats(b_us, ts_ws, ts_e)
                if st_g is not None and st_u is not None and d_us["atr"] > 1e-9:
                    rel_z = (st_g["ret"] / atr) - (st_u["ret"] / float(d_us["atr"]))
                    if abs(rel_z) >= thr:
                        side = -1 if rel_z > 0.0 else 1

        elif kind == "US500_TO_GER40_LEAD":
            b_us = bundles["US500"]
            d_us = b_us["day_map"].get(dk)
            if d_us is not None and d_us["atr"] > 1e-9:
                # Strictly causal overnight US500 futures return: prior US500 close (t-1) -> 08:00 UTC(t)
                ts_8u = _resolve_ts(dk, (8, 0, "UTC"))
                i_us = int(b_us["times"].searchsorted(ts_8u, side="left")) - 1
                if i_us >= 0 and int(b_us["times"][i_us]) < ts_e and (ts_8u - int(b_us["times"][i_us])) <= 3600:
                    us_now = 0.5 * (float(b_us["quotes"][i_us, 3]) + float(b_us["quotes"][i_us, 7]))
                    us_z = (us_now - float(d_us["prev_c"])) / float(d_us["atr"])
                    if abs(us_z) >= thr:
                        side = 1 if us_z > 0.0 else -1

        elif kind == "PRIOR_DAY_EXHAUST_FADE":
            prev_z = (float(d["prev_c"]) - float(d["prev_o"])) / atr
            if abs(prev_z) >= thr:
                prev_dir = 1 if prev_z > 0.0 else -1
                st = _causal_window_stats(b, ts_ws, ts_e)
                if st is not None:
                    early_z = (st["ret"] / atr) * prev_dir
                    if early_z < 0.20:
                        side = -prev_dir

        if side == 0:
            continue

        fi, day_flat = int(d["fi"]), int(d["flat_idx"])
        sub_t = times[fi:day_flat + 1]
        rel_e = int(sub_t.searchsorted(ts_e, side="left"))
        rel_f = int(sub_t.searchsorted(ts_f, side="right")) - 1
        e_idx = fi + rel_e
        f_idx = min(day_flat, fi + max(0, rel_f))
        if e_idx >= f_idx or e_idx > day_flat or (int(times[e_idx]) - ts_e) > 900:
            continue

        res = replay_intraday_tape_trade(
            b, e_idx, f_idx, side, sl_atr * atr,
            tp_dist=(tp_atr * atr) if tp_atr is not None else None,
        )
        if res is None:
            continue
        row, stamps, marks, fade_r = res
        raw_tape[dk] = (row, stamps, marks)
        fade_r_by_day[dk] = fade_r

    return raw_tape, fade_r_by_day


# ==============================================================================
# 4. PORTFOLIO REPLAY WITH EXACT GER40/BTCUSD CONTRACT MARGIN & 10,000-PATH MC
# ==============================================================================

def lab11_margin_per_lot_usd(asset: str, entry_price: float, profile_mode: str = "Swing") -> tuple[float, float, float, float, float]:
    """Exact margin/lot/comm specs extending `p27.margin_per_lot_usd` cleanly for GER40 & BTCUSD."""
    if asset == "GER40":
        lev = 15.0 if profile_mode == "Swing" else 50.0
        return (entry_price * 1.10 / lev, 0.01, 0.01, 1000.0, 0.0)
    if asset == "BTCUSD":
        lev = 1.0 if profile_mode == "Swing" else 3.3
        return (entry_price / lev, 0.01, 0.01, 50.0, 0.0)
    return p27.margin_per_lot_usd(asset, entry_price, profile_mode)


def replay_lab11_portfolio_m1(
    days: list[str],
    tapes: dict[str, dict],
    risks: dict[str, float],
    initial: float = 10000.0,
    *,
    profile_mode: str = "Swing",
    max_symbol_concurrent_risk: float | None = None,
    red_news_cal: dict | None = None,
    news_pad_sec: int = 300,
    cutoff: int = STOP,
) -> tuple[dict, list[dict]]:
    """Exact minute-by-minute M1 floating-equity Prague-reset portfolio replay supporting all 12 assets."""
    active_tapes = {}
    news_stats = {}
    for eng in risks:
        if red_news_cal is not None:
            gt, st = p28.apply_red_news_guard_to_tape(tapes[eng], red_news_cal, mode="FLATTEN_5M", pad_sec=news_pad_sec)
            active_tapes[eng] = gt
            news_stats[eng] = st
        else:
            active_tapes[eng] = tapes[eng]

    balance = float(initial)
    sorted_days = sorted(days)
    meter = jpy_eq.EquityMetrics(initial, START, [int(np.datetime64(d, "D").astype(int)) for d in sorted_days])
    exits, totals, rejects = [], defaultdict(list), Counter()
    peak_margin = 0.0
    max_concurrent = sym_cap_hits = 0

    for dk in sorted_days:
        day_candidates = [(eng, active_tapes[eng][dk]) for eng in risks if dk in active_tapes[eng]]
        if not day_candidates:
            continue
        day_candidates.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))

        sized = []
        orders = []
        for eng, (row, stamps, marks) in day_candidates:
            eff_risk = float(risks[eng])
            asset = row.get("asset") or ("USDJPY" if "USDJPY" in eng else ("GBPUSD" if "GBPUSD" in eng else eng))
            stamp = int(stamps[0])

            if max_symbol_concurrent_risk is not None:
                open_sym_r = fsum(t.row.get("_eff_risk", 0.0) for t in sized if t.row.get("asset") == asset and stamp < t.release)
                rem = max(0.0, max_symbol_concurrent_risk - open_sym_r)
                if rem < eff_risk - 1e-12:
                    sym_cap_hits += 1
                    eff_risk = rem
                if eff_risk <= 1e-9:
                    rejects["SYM_RISK_CAP_SKIP"] += 1
                    orders.append({"engine": eng, "asset": asset, "status": "SYM_RISK_CAP_SKIP", "lots": 0.0})
                    continue

            budget = initial * eff_risk
            mgn_1lot, vmin, vstep, vmax, comm_1lot = lab11_margin_per_lot_usd(asset, float(row["entry_price"]), profile_mode)
            acct = jpy_eq.Account(eng, initial, mgn_1lot, vmin, vstep, vmax)
            lot = jpy_eq.floor_lot(budget, float(row["stop_risk_with_cost_usd"]), acct)
            used_m = fsum(t.margin for t in sized if stamp < t.release)
            avail = balance + fsum(t.open_floating(stamp) for t in sized) - used_m

            status = "SIZED"
            if lot < vmin:
                status = "MIN_LOT"
            elif lot * (mgn_1lot + comm_1lot) > avail:
                status = "MARGIN"
            rejects[status] += 1
            orders.append({"engine": eng, "asset": asset, "entry": stamp, "lots": lot if status == "SIZED" else 0.0, "status": status, "eff_risk": eff_risk})
            if status == "SIZED":
                row_copy = {**row, "asset": asset, "at_open": bool(row.get("at_open", False)), "_eff_risk": eff_risk}
                sized.append(portfolio.SizedTrade(row_copy, stamps, marks, lot, lot * mgn_1lot, lot * float(row["net_usd_per_lot"])))

        if not sized:
            continue

        tl, comb_marks, mgn_arr, conc_arr, _ = portfolio.combined_marks(sized)
        points = np.r_[balance, (balance + comb_marks).ravel()]
        meter.add(np.r_[tl[0], np.repeat(tl, 4)], points, balance)

        peak_margin = max(peak_margin, float(mgn_arr.max()))
        max_concurrent = max(max_concurrent, int(conc_arr.max()))
        net = fsum(t.net for t in sized)
        assert isclose(float(comb_marks[-1, -1]), net, abs_tol=1e-4)
        balance += net
        totals[dk[:4]].append(net)
        exits.append({
            "day": dk, "net_usd": net, "cash": balance, "orders": orders,
            "day_equity_minimum": float(points.min()), "day_equity_maximum": float(points.max()),
        })

    if balance < meter.peak:
        meter.update_age(np.array([meter.peak_at]), np.array([cutoff - 1]))

    yrs_span = max(1.0, len({d[:4] for d in sorted_days}))
    ann_all = (balance - initial) / yrs_span
    ann_A = fsum(fsum(totals[str(y)]) for y in (2018, 2019, 2020)) / 3.0
    ann_B = fsum(fsum(totals[str(y)]) for y in (2021, 2022, 2023, 2024)) / 4.0
    peak_dd_pct = 100.0 * meter.dd / initial
    ann_pct_all = 100.0 * ann_all / initial
    calmar = (ann_pct_all / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0

    # Daily return Sharpe (annualized 252 trading days over sorted_days)
    by_day = {e["day"]: float(e["net_usd"]) / initial for e in exits}
    r_arr = np.array([by_day.get(dk, 0.0) for dk in sorted_days], dtype=np.float64)
    sd = float(np.std(r_arr, ddof=1)) if len(r_arr) > 5 else 0.0
    sharpe = (float(np.mean(r_arr)) / sd * math.sqrt(252.0)) if sd > 1e-12 else 0.0

    return {
        "net_usd": round(balance - initial, 2),
        "ann_pct": {"all": round(ann_pct_all, 2), "A": round(100.0 * ann_A / initial, 2), "B": round(100.0 * ann_B / initial, 2)},
        "sharpe_1x": round(sharpe, 2),
        "daily_loss_pct": round(100.0 * meter.daily / initial, 2),
        "peak_dd_pct": round(peak_dd_pct, 2),
        "calmar": round(calmar, 2),
        "peak_margin_pct": round(100.0 * peak_margin / initial, 2),
        "max_concurrent_positions": max_concurrent,
        "sym_cap_hits": sym_cap_hits,
        "margin_failures": int(rejects["MARGIN"]),
        "years_pct": {str(y): round(100.0 * fsum(totals[str(y)]) / initial, 2) for y in ALL_DEV_YEARS},
        "news_stats": news_stats,
    }, exits


@njit(cache=True)
def _simulate_prop_tight_symcap_numba(
    idx_matrix: np.ndarray,
    nets_p1: np.ndarray, dds_p1: np.ndarray, flg_p1: np.ndarray,
    nets_core: np.ndarray, dds_core: np.ndarray, flg_core: np.ndarray,
    steps: int, cap: float, fee: float, fee_refund_ratio: float,
    p1_target: float, p2_target: float, daily_lim: float, static_lim: float,
    daily_pause_only: bool, min_days: int, min_prof_day: float,
    split: float, payout_cycle: int, max_retries: int,
    p1_start_scale: float, p1_lock50_scale: float, p1_lock75_scale: float,
    p2_start_mult: float, p2_lock60_mult: float, funded_mult: float,
    amber_dd: float, amber_mult: float, red_dd: float, red_mult: float,
    ea_daily_stop: float,
):
    """10,000-path Block Bootstrap MC supporting separate tightened-SYMCAP P1 arrays + Dyn_ProfitLock!

    `nets_p1 / dds_p1` are already pre-replayed at exact P1 `4.0x` risk with tightened `SYMCAP = 1.75%`,
    so `p1_start_scale = 1.00` uses exact 4.0x/1.75%-SYMCAP, `1.125` scales to 4.5x start, and profit-lock
    steps smoothly down (`0.75` -> 3.0x, `0.50` -> 2.0x) while P2 & Funded use `nets_core` (`SYMCAP 1.0%`).
    """
    n_paths, horizon = idx_matrix.shape
    scale = cap / 10000.0
    p1_goal = cap * (1.0 + p1_target)
    p2_goal = cap * (1.0 + p2_target)

    pass_days = np.full(n_paths, -1, dtype=np.int32)
    pay1_days = np.full(n_paths, -1, dtype=np.int32)
    cf24 = np.zeros(n_paths, dtype=np.float64)
    oop = np.zeros(n_paths, dtype=np.float64)
    br_any = np.zeros(n_paths, dtype=np.int8)
    wiped = np.zeros(n_paths, dtype=np.int8)
    tix = np.ones(n_paths, dtype=np.int32)

    for b in range(n_paths):
        stage = 1
        bal = cap
        tdays = 0
        attempts = 1
        fees = fee
        refunded = False
        payouts = 0.0
        cycle_d = 0
        max_oop = fee
        f_pass = -1
        f_pay = -1
        had_br = 0
        is_dead = 0

        for d in range(horizon):
            if is_dead == 1:
                break
            src = idx_matrix[b, d]
            eq_pct = (bal - cap) / cap

            if stage == 1:
                prog = eq_pct / max(1e-6, p1_target)
                if eq_pct <= -red_dd:
                    net = nets_core[src] * scale * red_mult
                    dd = dds_core[src] * scale * red_mult
                    flg = flg_core[src]
                elif eq_pct <= -amber_dd:
                    net = nets_core[src] * scale * amber_mult
                    dd = dds_core[src] * scale * amber_mult
                    flg = flg_core[src]
                else:
                    s_p1 = p1_lock75_scale if prog >= 0.75 else (p1_lock50_scale if prog >= 0.50 else p1_start_scale)
                    net = nets_p1[src] * scale * s_p1
                    dd = dds_p1[src] * scale * s_p1
                    flg = flg_p1[src]
            elif stage == 2:
                prog = eq_pct / max(1e-6, p2_target)
                m = p2_lock60_mult if prog >= 0.60 else p2_start_mult
                if eq_pct <= -red_dd:
                    m = min(m, red_mult)
                elif eq_pct <= -amber_dd:
                    m = min(m, amber_mult)
                net = nets_core[src] * scale * m
                dd = dds_core[src] * scale * m
                flg = flg_core[src]
            else:
                m = funded_mult
                if eq_pct <= -red_dd:
                    m = min(m, red_mult)
                elif eq_pct <= -amber_dd:
                    m = min(m, amber_mult)
                net = nets_core[src] * scale * m
                dd = dds_core[src] * scale * m
                flg = flg_core[src]

            cur_daily_cap = cap * daily_lim
            cur_static_floor = cap * (1.0 - static_lim)
            cur_ea_cut = cap * ea_daily_stop if ea_daily_stop > 0.0 else 1e18

            if daily_pause_only:
                if dd >= cur_daily_cap:
                    dd = min(dd, cur_daily_cap + cap * 0.001)
                    net = min(net, -cur_daily_cap)
                breached = (bal - dd) <= cur_static_floor + 1e-9
            else:
                if dd > cur_ea_cut:
                    dd = min(dd, cur_ea_cut + cap * 0.0025)
                    net = min(net, -cur_ea_cut)
                breached = (dd >= cur_daily_cap - 1e-9) or ((bal - dd) <= cur_static_floor + 1e-9)

            if breached:
                had_br = 1
                if attempts <= max_retries:
                    attempts += 1
                    fees += fee
                    stage = 1
                    bal = cap
                    tdays = 0
                    refunded = False
                    cycle_d = 0
                else:
                    is_dead = 1
            else:
                bal += net
                if min_prof_day > 0.0:
                    if net >= cap * min_prof_day:
                        tdays += 1
                elif flg != 0:
                    tdays += 1

                if stage == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
                    stage = 2 if steps == 2 else 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if steps == 1 and f_pass < 0:
                        f_pass = d + 1
                elif stage == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
                    stage = 3
                    bal = cap
                    tdays = 0
                    cycle_d = 0
                    if f_pass < 0:
                        f_pass = d + 1
                elif stage == 3:
                    cycle_d += 1
                    if cycle_d >= payout_cycle:
                        if bal > cap + 1e-6:
                            pay = (bal - cap) * split
                            if not refunded:
                                pay += fee * fee_refund_ratio
                                refunded = True
                            payouts += pay
                            if f_pay < 0:
                                f_pay = d + 1
                            bal = cap
                        cycle_d = 0

            cur_oop = fees - payouts
            if cur_oop > max_oop:
                max_oop = cur_oop

        pass_days[b] = f_pass
        pay1_days[b] = f_pay
        cf24[b] = payouts - fees
        oop[b] = max_oop
        br_any[b] = had_br
        wiped[b] = is_dead
        tix[b] = attempts

    return pass_days, pay1_days, cf24, oop, br_any, wiped, tix


def evaluate_prop_accretion_mc(
    nets_p1: np.ndarray, dds_p1: np.ndarray, flg_p1: np.ndarray,
    nets_core: np.ndarray, dds_core: np.ndarray, flg_core: np.ndarray,
    idx_mat: np.ndarray,
    firms: list[dict[str, Any]],
) -> dict[str, dict[str, dict[str, Any]]]:
    """Run 10,000-path Block Bootstrap MC across FTMO Swing & The5ers HS (`P1_Balanced` & `Dyn_ProfitLock`)."""
    # P1 tape is already replayed at 4.0x w/ tightened SYMCAP 1.75%!
    policies = [
        ("P1_Balanced_SymCap175",  1.000, 1.000, 1.000, 2.00, 2.00, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030),
        ("Dyn_ProfitLock_SymCap175", 1.125, 0.750, 0.500, 2.50, 1.50, 1.00, 0.035, 0.65, 0.060, 0.40, 0.030),
    ]
    n_paths = idx_mat.shape[0]
    out: dict[str, dict[str, dict[str, Any]]] = {}
    for fcfg in firms:
        fid = fcfg["id"]
        out[fid] = {}
        for (pname, p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st) in policies:
            pd, py, cf, oop, br, wp, tx = _simulate_prop_tight_symcap_numba(
                idx_mat,
                nets_p1, dds_p1, flg_p1,
                nets_core, dds_core, flg_core,
                int(fcfg["steps"]), float(fcfg["capital_usd"]), float(fcfg["fee_usd"]),
                float(fcfg.get("fee_refund_ratio", 1.0)),
                float(fcfg["p1_target_pct"]), float(fcfg["p2_target_pct"]),
                float(fcfg["daily_loss_pct"]), float(fcfg["static_loss_pct"]),
                bool(fcfg.get("daily_pause_non_breaching", False)),
                int(fcfg["min_days"]), float(fcfg.get("min_profitable_day_pct", 0.0)),
                float(fcfg["payout_split"]), int(fcfg["payout_cycle_days"]), 4,
                p1s, p1_50, p1_75, p2s, p2_60, fmult, amb_d, amb_m, red_d, red_m, ea_st,
            )
            passed = pd[pd > 0]
            paid = py[py > 0]
            out[fid][pname] = {
                "pass_3m_pct": round(100.0 * float(np.mean((pd > 0) & (pd <= 63))), 1),
                "pass_6m_pct": round(100.0 * float(np.mean((pd > 0) & (pd <= 126))), 1),
                "pass_12m_pct": round(100.0 * float(np.mean((pd > 0) & (pd <= 252))), 1),
                "pass_24m_pct": round(100.0 * len(passed) / n_paths, 1),
                "med_days_pass": int(np.median(passed)) if len(passed) else -1,
                "med_days_pay1": int(np.median(paid)) if len(paid) else -1,
                "breach_pct": round(100.0 * float(np.mean(br)), 1),
                "wipeout_pct": round(100.0 * float(np.mean(wp)), 2),
                "oop95_usd": round(float(np.quantile(oop, 0.95)), 1),
                "ev_24m_usd": round(float(np.mean(cf)), 1),
                "ev_per_fee": round(float(np.mean(cf)) / max(1.0, float(fcfg["fee_usd"])), 2),
                "avg_tickets": round(float(np.mean(tx)), 2),
            }
    return out


# ==============================================================================
# 5. SINGLE-CANDIDATE METRICS, 6-GATE RED-TEAM AUDIT & REPORT BUILDER
# ==============================================================================

def _tape_split_metrics(tape: dict[str, tuple[dict, np.ndarray, np.ndarray]], years: frozenset[int] | set[int]) -> dict[str, Any]:
    rs = [float(row["net_R"]) for dk, (row, _st, _mk) in sorted(tape.items()) if int(row["year"]) in years]
    n = len(rs)
    if n == 0:
        return {"n": 0, "net_R": 0.0, "ann_R": 0.0, "pf": 0.0, "win_pct": 0.0, "dd_R": 0.0, "mean_R": 0.0}
    gp = fsum(x for x in rs if x > 0.0)
    gl = -fsum(x for x in rs if x < 0.0)
    pf = gp / gl if gl > 1e-9 else (9.99 if gp > 0.0 else 0.0)
    eq = np.cumsum([0.0] + rs)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    n_yrs = max(1.0, float(len(years)))
    net_r = float(fsum(rs))
    return {
        "n": int(n),
        "net_R": round(net_r, 2),
        "ann_R": round(net_r / n_yrs, 2),
        "pf": round(pf, 3),
        "win_pct": round(100.0 * sum(x > 0.0 for x in rs) / n, 1),
        "dd_R": round(dd, 2),
        "mean_R": round(net_r / n, 4),
    }


def _safe_corr(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) < 20 or len(a) != len(b):
        return 0.0
    if float(np.std(a)) <= 1e-12 or float(np.std(b)) <= 1e-12:
        return 0.0
    c = float(np.corrcoef(a, b)[0, 1])
    return round(c, 4) if math.isfinite(c) else 0.0


def _apply_cost_stress_existing_tapes(tapes: dict[str, dict], cost_mult: float) -> dict[str, dict]:
    """Shift existing frozen tapes cleanly by `(cost_mult - 1.0) * base_friction_usd_per_lot`."""
    from quant_factory.portfolio_v1_vs_v2_study import apply_cost_stress_to_tapes
    return apply_cost_stress_to_tapes(tapes, cost_mult)


def run_lab11(*, n_mc_paths: int = N_MC_PATHS, write_report: bool = True) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    # 1. Load frozen incumbent A1_V1_LIVE8 M1 tapes & official 2018-2024 Red News calendar
    reg = load_registry()
    warm = build_or_load_frozen_tapes(force_rebuild=False)
    red_news = load_red_news_calendar("red_news_official_2018_2024")
    inc_tapes_1x = dict(warm["tapes"])
    ext_days = list(warm["ext_days"])
    enforce_pre_holdout_dates(ext_days, context="lab11.ext_days")

    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    live8_risks = {k: base_r[k] for k in INCUMBENT_LIVE8}

    # Build complete canonical Mon-Fri incumbent Dev calendar (includes all non-Tokyo FX/Index days <= 2024-12-31!)
    canonical_inc_days = sorted(
        set(ext_days) | {dk for eng in INCUMBENT_LIVE8 for dk in inc_tapes_1x[eng]}
    )
    enforce_pre_holdout_dates(canonical_inc_days, context="lab11.canonical_inc_days")

    # Replay incumbent A1_V1_LIVE8 & each individual incumbent engine (for exact Gate 3 orthogonality!)
    inc_m1_1x, inc_ex_1x = replay_lab11_portfolio_m1(
        canonical_inc_days, inc_tapes_1x, live8_risks, 10000.0,
        profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
    )
    inc_day_ret = {e["day"]: float(e["net_usd"]) / 10000.0 for e in inc_ex_1x}
    inc_vec_all = np.array([inc_day_ret.get(d, 0.0) for d in canonical_inc_days], dtype=np.float64)

    single_inc_vecs: dict[str, np.ndarray] = {}
    for eng in INCUMBENT_LIVE8:
        gt, _ = p28.apply_red_news_guard_to_tape(inc_tapes_1x[eng], red_news, mode="FLATTEN_5M", pad_sec=300)
        single_inc_vecs[eng] = np.array([float(gt[d][0]["net_R"]) if d in gt else 0.0 for d in canonical_inc_days], dtype=np.float64)

    # 2. Load local sealed M1 Bid/Ask bundles for all required Lab #11 assets
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, q_j, _ = hcache.load_asset("USDJPY", verify_sha=False)
    enforce_pre_holdout_ts(int(ts_j[-1]), stop_ts=STOP, context="lab11.usdjpy")
    day_j = (ts_j // 86400).astype(np.int64)
    chg_j = np.r_[True, day_j[1:] != day_j[:-1]]
    starts_j = np.flatnonzero(chg_j)
    ends_j = np.r_[starts_j[1:] - 1, len(day_j) - 1]
    usdjpy_close_map = {
        datetime.fromtimestamp(int(ts_j[ei]), timezone.utc).date(): float(q_j[ei, 3])
        for ei in ends_j
    }

    catalog = build_lab11_catalog()
    m_total = len(catalog)
    needed_assets = sorted({c["asset"] for c in catalog} | {"US500"})
    bundles: dict[str, dict[str, Any]] = {}
    for a in needed_assets:
        bundles[a] = build_causal_m1_bundle(
            a, swing_specs, usdjpy_close_map,
            include_weekends=(a == "BTCUSD"),
        )

    # 3. Evaluate all M = 20 pre-registered hypotheses strictly Cl.A (2018-2020) -> Blind Cl.B (2021-2024)
    cand_records: list[dict[str, Any]] = []
    cand_tapes_1x: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
    cand_tapes_15x: dict[str, dict[str, tuple[dict, np.ndarray, np.ndarray]]] = {}
    p_raw_b_list: list[float] = []

    for idx, cfg in enumerate(catalog):
        cid = cfg["id"]
        raw_tape, fade_map = evaluate_lab11_spec(bundles, cfg)
        tape_1x, tape_15x, news_st = apply_red_news_and_15x_stress(raw_tape, red_news)
        cand_tapes_1x[cid] = tape_1x
        cand_tapes_15x[cid] = tape_15x

        st_a1 = _tape_split_metrics(tape_1x, CLUSTER_A_YEARS)
        st_b1 = _tape_split_metrics(tape_1x, CLUSTER_B_YEARS)
        st_b15 = _tape_split_metrics(tape_15x, CLUSTER_B_YEARS)
        st_all1 = _tape_split_metrics(tape_1x, set(ALL_DEV_YEARS))
        st_all15 = _tape_split_metrics(tape_15x, set(ALL_DEV_YEARS))

        # Exact year-by-year R (2018..2024) & single-year profit concentration share
        yr_r = {str(y): 0.0 for y in ALL_DEV_YEARS}
        for dk, (row, _st, _mk) in tape_1x.items():
            yr_r[str(row["year"])] += float(row["net_R"])
        yr_r = {y: round(v, 2) for y, v in yr_r.items()}
        pos_years = sum(1 for v in yr_r.values() if v > 0.0)
        tot_r = float(fsum(yr_r.values()))
        max_yr_r = max(yr_r.values())
        max_yr_share_pct = round(100.0 * max_yr_r / tot_r, 1) if tot_r > 1e-6 else 100.0

        # Exact daily alignment on canonical_inc_days for Orthogonality (Gate 3) & Cl.B DSR
        cand_vec_all = np.array([float(tape_1x[d][0]["net_R"]) if d in tape_1x else 0.0 for d in canonical_inc_days], dtype=np.float64)
        corr_live8 = _safe_corr(cand_vec_all, inc_vec_all)
        single_corrs = {eng: _safe_corr(cand_vec_all, vec) for eng, vec in single_inc_vecs.items()}
        max_single_eng, max_single_corr = max(single_corrs.items(), key=lambda kv: abs(kv[1]))

        # Daily series on Blind Cluster B (2021-2024) for DSR & Sign-Flip Null
        b_days = [d for d in canonical_inc_days if int(d[:4]) in CLUSTER_B_YEARS]
        # Include BTC weekend days in DSR series if asset is BTCUSD
        if cfg["asset"] == "BTCUSD":
            b_days = sorted(set(b_days) | {dk for dk in tape_1x if int(dk[:4]) in CLUSTER_B_YEARS})
        r_b_daily = np.array([float(tape_1x[d][0]["net_R"]) * 0.005 if d in tape_1x else 0.0 for d in b_days], dtype=np.float64)
        dsr_b = deflated_sharpe_ratio(r_b_daily, n_trials=m_total, annualization=252.0)

        # Sign-Flip Permutation Null on Blind Cluster B (using exact paired trade & fade R!)
        b_trade_days = sorted(dk for dk in tape_1x if int(dk[:4]) in CLUSTER_B_YEARS)
        if len(b_trade_days) >= 10:
            obs_arr = np.array([float(tape_1x[dk][0]["net_R"]) for dk in b_trade_days], dtype=np.float64)
            fade_arr = np.array([float(fade_map.get(dk, -tape_1x[dk][0]["net_R"])) for dk in b_trade_days], dtype=np.float64)
            p_sf_b = float(sign_flip_p_numba(obs_arr, fade_arr, draws=SIGN_FLIP_DRAWS, seed=SEED + idx))
        else:
            p_sf_b = 1.0
        p_raw_b_list.append(p_sf_b)

        # Hard Red-Team Gates 1..4
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

    # Attach exact BH-FDR q-values across m_total = 20 and finalize verdicts
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

    # 4. Gate 5: Prop Portfolio Accretion Test (10,000-path Block Bootstrap MC, seed=20261124)
    # Build combined tapes (incumbent + any approved Lab #11 engines, plus top counterfactual if 0 approved)
    all_tapes_1x = dict(inc_tapes_1x)
    all_tapes_15x = _apply_cost_stress_existing_tapes(inc_tapes_1x, 1.5)
    for cid in cand_tapes_1x:
        all_tapes_1x[cid] = cand_tapes_1x[cid]
        all_tapes_15x[cid] = cand_tapes_15x[cid]

    # Build portfolio variants to compare head-to-head on identical 10,000 bootstrap paths
    port_configs: list[tuple[str, str, dict[str, float]]] = [
        ("A1_V1_LIVE8_BASE", "Incumbent 8 live engines (E1..E7 + S6)", dict(live8_risks)),
    ]

    if approved_ids:
        # Add each approved Lab #11 engine at conservative 0.45% base risk (funded 1x -> 1.80% before SYMCAP at 4x!)
        # Keep existing live8 intact (pure additive breadth test!) AND risk-matched normalized version
        add_risks = {**live8_risks, **{cid: 0.0045 for cid in approved_ids}}
        port_configs.append((
            "V2_LIVE8_PLUS_LAB11_ADD",
            f"A1_V1_LIVE8 + {len(approved_ids)} Approved Lab #11 (+0.45% each, additive breadth)",
            add_risks,
        ))
        sum_base = sum(live8_risks.values())
        s_add = sum(add_risks.values())
        norm_risks = {k: round(v * (sum_base / s_add), 6) for k, v in add_risks.items()}
        port_configs.append((
            "V2_LIVE8_PLUS_LAB11_RISKMATCH",
            f"A1_V1_LIVE8 + {len(approved_ids)} Approved Lab #11 (risk-budget normalized to live8)",
            norm_risks,
        ))
    else:
        # Honest counterfactual diagnostic if 0 passed: test top 2 Blind-Cl.B non-approved candidates (clearly labeled NOT promoted!)
        ranked_cf = sorted(cand_records, key=lambda r: (r["cluster_b_15x"]["ann_R"], r["cluster_b_1x"]["pf"]), reverse=True)
        top1_cf = ranked_cf[0]
        top2_cf = ranked_cf[1]
        port_configs.append((
            "DIAG_COUNTERFACTUAL_TOP1_UNAPPROVED",
            f"Diagnostic ONLY (NOT promoted): live8 + top non-approved {top1_cf['id']}",
            {**live8_risks, top1_cf["id"]: 0.0045},
        ))
        port_configs.append((
            "DIAG_COUNTERFACTUAL_TOP2_UNAPPROVED",
            f"Diagnostic ONLY (NOT promoted): live8 + top-2 non-approved ({top1_cf['id']} + {top2_cf['id']})",
            {**live8_risks, top1_cf["id"]: 0.0045, top2_cf["id"]: 0.0045},
        ))

    union_days = sorted(
        set(canonical_inc_days)
        | {dk for _pid, _desc, rmap in port_configs for eng in rmap for dk in all_tapes_1x[eng]}
    )
    enforce_pre_holdout_dates(union_days, context="lab11.union_days")

    firms = [load_firm_config(f) for f in ("ftmo_swing_10k", "the5ers_high_stakes_5k")]
    idx_mat = make_block_bootstrap_indices(len(union_days), horizon=504, n_paths=n_mc_paths, block_len=5, seed=SEED)

    accretion_results: list[dict[str, Any]] = []
    for pid, desc, rmap in port_configs:
        # Funded_Safe 1x (SYMCAP 1.00%) at 1.0x & 1.5x friction
        m1_1x, ex_1x = replay_lab11_portfolio_m1(
            union_days, all_tapes_1x, rmap, 10000.0,
            profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
        )
        m1_15x, _ = replay_lab11_portfolio_m1(
            union_days, all_tapes_15x, rmap, 10000.0,
            profile_mode="Swing", max_symbol_concurrent_risk=FUNDED_SYMCAP, red_news_cal=red_news,
        )
        # P1_Balanced 4.0x tape with tightened SYMCAP = 1.75% (Master Plan Patch #3!)
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

    # Family summary counts
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
        else "ZERO_APPROVED_KEEP_A1_V1_LIVE8"
    )

    payload: dict[str, Any] = {
        "schema": "naqex-lab11-orthogonal-prop-v2-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "runtime_seconds": round(time.perf_counter() - t0, 2),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "holdout_rows_analysed": 0,
        "holdout_lock_sha256": lock_sha,
        "dev_window": ["2018-01-02", "2024-12-31"],
        "cluster_a_years": sorted(CLUSTER_A_YEARS),
        "cluster_b_years": sorted(CLUSTER_B_YEARS),
        "m_total": m_total,
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
    parser = argparse.ArgumentParser(description="Lab #11 Orthogonal Non-Breakout & New-Asset Prop v2 Discovery")
    parser.add_argument("--mc-paths", type=int, default=N_MC_PATHS)
    parser.add_argument("--no-write", action="store_true")
    args = parser.parse_args()
    out = run_lab11(n_mc_paths=args.mc_paths, write_report=not args.no_write)
    print(f"Lab #11 finished in {out['runtime_seconds']}s | Holdout rows={out['holdout_rows_analysed']} | Decision={out['executive_decision']}")
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
