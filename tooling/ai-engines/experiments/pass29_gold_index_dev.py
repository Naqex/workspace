"""M4.1 — Pass 29: Gold (XAUUSD) & Global Indices (US500, US100, GER40) Orthogonal Intraday Discovery.

STRICT SEALED DEVELOPMENT BOUNDARY (< 2025-01-01 ONLY):
  - Asserts NATIVE_FTMO_HOLDOUT_LOCK.json SHA integrity on startup.
  - Reads ONLY .runtime/hot-m1-cache/ (verified max_ts < 2025-01-01T00:00:00Z, holdout_rows = 0).
  - Cluster A (Discovery): 2018-2021; Blind Cluster B (Validation): 2022-2024.
  - Intraday swap = 0, hard server SL on every order, max 1 trade/day/spec, Native M1 Bid/Ask.
  - 4 pre-registered economic hypotheses (m_total = 24):
      H1: London/NY Fix Drift
      H2: Opening-Range Volatility Squeeze
      H3: Gold Asian -> London Mean Reversion (+ Continuation control)
      H4: Index Opening-Auction Momentum (+ Fade control)
  - Full statistical audit:
      1. Sign-Flip Permutation Null (N = 1,000, Numba JIT)
      2. Matched-Hold Random-Timing Null (N = 500, same asset/day/side/SL/hold-bars -> kills passive drift!)
      3. Benjamini-Hochberg FDR across ALL m_total = 24 specs (Cluster B & Full Dev)
      4. Daily correlation r vs frozen PORT_7E (target |r| < 0.15)
  - Retains ALL negative/failed results honestly (0 passes reported transparently if none qualify!).
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import json
from math import fsum
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
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
from native_ftmo_monfri_seal import START, STOP
from quant_core.ftmo_track_replay import profiles
from quant_core.holdout_guard import enforce_pre_holdout_ts
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.eval_pipeline import benjamini_hochberg, sign_flip_p_numba
from quant_factory.prop_engine import replay_portfolio_m1

NY_TZ = ZoneInfo("America/New_York")
LONDON_TZ = ZoneInfo("Europe/London")
BERLIN_TZ = ZoneInfo("Europe/Berlin")

CLUSTER_A_YEARS = frozenset({2018, 2019, 2020, 2021})
CLUSTER_B_YEARS = frozenset({2022, 2023, 2024})
ALL_DEV_YEARS = tuple(range(2018, 2025))

SEED = 20261124
SIGN_FLIP_DRAWS = 1000
MATCHED_HOLD_DRAWS = 500


def local_ts(day_iso: str, hour: int, minute: int, tz: ZoneInfo) -> int:
    d = date.fromisoformat(day_iso)
    return int(datetime(d.year, d.month, d.day, hour, minute, tzinfo=tz).timestamp())


def _replay_with_meta(
    bundle: dict[str, Any],
    day_rec: dict[str, Any],
    e_idx: int,
    flat_idx: int,
    side: int,
    ep: float,
    sl_p: float,
    *,
    tp_p: float | None = None,
    win_start_idx: int | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = bundle["times"], bundle["quotes"]
    sl_d = abs(ep - sl_p)
    if sl_d <= 1e-10 or e_idx < 0 or flat_idx <= e_idx:
        return None, None
    tr = p24.replay_causal_intraday(
        bundle["asset"], times, quotes, e_idx, flat_idx, side, ep, sl_p,
        tp_p=tp_p, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
    )
    if tr is None:
        return None, None
    # Opposite-side fade at identical timestamp for exact sign-flip permutation null
    fep = float(quotes[e_idx, 0] if side == 1 else quotes[e_idx, 4])
    ftp = (fep - side * abs(tp_p - ep)) if tp_p is not None else None
    fd = p24.replay_causal_intraday(
        bundle["asset"], times, quotes, e_idx, flat_idx, -side, fep, fep + side * sl_d,
        tp_p=ftp, spec=bundle["spec"], usdjpy_close_map=bundle["usdjpy_close_map"],
    )
    if fd is None:
        return None, None
    # Attach exact indices for Matched-Hold Timing Null
    ex_idx = int(times.searchsorted(tr["exit"], side="left"))
    hold_bars = max(1, min(flat_idx - e_idx, ex_idx - e_idx))
    ws_idx = day_rec["fi"] if win_start_idx is None else max(day_rec["fi"], win_start_idx)
    tr["_meta"] = {
        "asset": bundle["asset"],
        "year": int(day_rec["year"]),
        "e_idx": int(e_idx),
        "flat_idx": int(flat_idx),
        "win_start_idx": int(ws_idx),
        "hold_bars": int(hold_bars),
        "sl_dist": float(sl_d),
        "sl_atr": float(sl_d / max(1e-9, float(day_rec["atr"]))),
        "side": int(side),
    }
    return tr, fd


def _market_entry_window(
    bundle: dict[str, Any],
    day_rec: dict[str, Any],
    ts_entry: int,
    ts_flat: int,
    side: int,
    sl_atr: float,
    *,
    tp_dist: float | None = None,
    win_start_ts: int | None = None,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = bundle["times"], bundle["quotes"]
    fi, day_flat = day_rec["fi"], day_rec["flat_idx"]
    sub_t = times[fi:day_flat + 1]
    rel_e = int(sub_t.searchsorted(ts_entry, side="left"))
    rel_f = int(sub_t.searchsorted(ts_flat, side="left"))
    e_idx = fi + rel_e
    f_idx = min(day_flat, fi + rel_f)
    if e_idx >= f_idx or int(times[e_idx]) - ts_entry > 600:
        return None, None
    ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
    sl_d = sl_atr * day_rec["atr"]
    tp_p = (ep + side * tp_dist) if tp_dist is not None else None
    ws_idx = fi + int(sub_t.searchsorted(win_start_ts, side="left")) if win_start_ts is not None else fi
    return _replay_with_meta(bundle, day_rec, e_idx, f_idx, side, ep, ep - side * sl_d, tp_p=tp_p, win_start_idx=ws_idx)


def _stop_breakout_window(
    bundle: dict[str, Any],
    day_rec: dict[str, Any],
    ts_scan_start: int,
    ts_scan_end: int,
    top: float,
    bot: float,
    sl_atr: float,
    *,
    ok_b: bool = True,
    ok_s: bool = True,
) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    times, quotes = bundle["times"], bundle["quotes"]
    fi, flat_idx = day_rec["fi"], day_rec["flat_idx"]
    sub_t = times[fi:flat_idx + 1]
    i0 = int(sub_t.searchsorted(ts_scan_start, side="left"))
    i1 = int(sub_t.searchsorted(ts_scan_end, side="left"))
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
    ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
    sl_d = sl_atr * day_rec["atr"]
    return _replay_with_meta(bundle, day_rec, e_idx, flat_idx, side, ep, ep - side * sl_d, win_start_idx=fi + i0)


@njit(cache=True)
def _matched_hold_null_numba(
    quotes: np.ndarray,
    pool_ws: np.ndarray,
    pool_flat: np.ndarray,
    pool_atr: np.ndarray,
    hold_arr: np.ndarray,
    side_arr: np.ndarray,
    sl_atr_arr: np.ndarray,
    slip_px_arr: np.ndarray,
    obs_total_r: float,
    draws: int,
    seed: int,
) -> float:
    """Zero-leakage Numba Matched-Hold Random-Timing Null on Native M1 Bid/Ask quotes.

    For each observed trade i (preserving exact trade count N, exact side sequence, exact hold_bars,
    and exact sl_atr), draws a random eligible trading day from the asset's pool within the same split
    and a random entry minute inside [day_ws, day_flat - hold_bars], then replays on real Bid/Ask
    with identical hard SL and stress friction. Kills passive drift without leaking the signal window!
    """
    n_tr = len(hold_arr)
    n_pool = len(pool_ws)
    if n_tr == 0 or n_pool == 0:
        return 1.0
    np.random.seed(seed)
    ge = 0
    for _ in range(draws):
        acc_r = 0.0
        for i in range(n_tr):
            p_i = np.random.randint(0, n_pool)
            ws = pool_ws[p_i]
            fl = pool_flat[p_i]
            hb = hold_arr[i]
            sd = side_arr[i]
            sld = sl_atr_arr[i] * pool_atr[p_i]
            slp = slip_px_arr[i]
            if sld <= 1e-10 or fl <= ws:
                continue
            hi_start = fl - hb
            if hi_start <= ws:
                r_idx = ws
            else:
                r_idx = ws + np.random.randint(0, hi_start - ws + 1)
            end_idx = r_idx + hb
            if end_idx > fl:
                end_idx = fl
            if end_idx <= r_idx:
                continue
            ep = quotes[r_idx, 4] if sd == 1 else quotes[r_idx, 0]
            sl_p = ep - sd * sld
            ex_p = quotes[end_idx, 0] if sd == 1 else quotes[end_idx, 4]
            for k in range(r_idx, end_idx):
                if sd == 1:
                    if quotes[k, 2] <= sl_p + 1e-10:
                        ex_p = quotes[k, 0] if (k > r_idx and quotes[k, 0] <= sl_p + 1e-10) else sl_p
                        break
                else:
                    if quotes[k, 5] >= sl_p - 1e-10:
                        ex_p = quotes[k, 4] if (k > r_idx and quotes[k, 4] >= sl_p - 1e-10) else sl_p
                        break
            gross = sd * (ex_p - ep)
            acc_r += (gross - slp) / (sld + slp)
        if acc_r >= obs_total_r - 1e-12:
            ge += 1
    return (ge + 1.0) / (draws + 1.0)


def compute_matched_hold_p(
    trades: list[dict[str, Any]],
    bundles: dict[str, Any],
    *,
    years_filter: frozenset[int] | set[int] | None = None,
    draws: int = MATCHED_HOLD_DRAWS,
    seed: int = SEED,
) -> float:
    """Compute zero-leakage Matched-Hold Random-Timing Null p-value on the same asset & split."""
    if not trades:
        return 1.0
    a = trades[0]["_meta"]["asset"]
    b = bundles[a]
    c = p24.asset_cost_tiers(a)
    pool_days = [d for d in b["days"] if years_filter is None or d["year"] in years_filter]
    if not pool_days:
        return 1.0

    pool_ws = np.array([int(d["fi"]) for d in pool_days], dtype=np.int64)
    pool_fl = np.array([int(d["flat_idx"]) for d in pool_days], dtype=np.int64)
    pool_atr = np.array([float(d["atr"]) for d in pool_days], dtype=np.float64)

    n = len(trades)
    hb = np.empty(n, dtype=np.int64)
    sd = np.empty(n, dtype=np.int64)
    sl_atr = np.empty(n, dtype=np.float64)
    slp = np.empty(n, dtype=np.float64)
    for i, t in enumerate(trades):
        m = t["_meta"]
        hb[i] = m["hold_bars"]
        sd[i] = m["side"]
        sl_atr[i] = m["sl_atr"]
        if c["is_index"]:
            slp[i] = float(c["stress"])
        else:
            cs = float(b["spec"]["trade_contract_size"])
            if b["spec"]["currency_profit"] == "USD":
                conv = 1.0
            elif b["spec"]["currency_profit"] == "JPY":
                d_ex = datetime.fromtimestamp(int(t["exit"]), timezone.utc).date()
                conv = 1.0 / (b["usdjpy_close_map"].get(d_ex, float(b["quotes"][m["e_idx"], 0])) if a != "USDJPY" else float(b["quotes"][m["e_idx"], 0]))
            elif b["spec"]["currency_profit"] in ("CAD", "CHF"):
                conv = 1.0 / max(1e-6, float(b["quotes"][m["e_idx"], 0]))
            else:
                conv = 1.0
            slp[i] = float(c["stress"]) + float(c["comm_usd"]) / max(1e-6, cs * conv)

    obs = float(fsum(t["ftmo_R"] for t in trades))
    return float(_matched_hold_null_numba(b["quotes"], pool_ws, pool_fl, pool_atr, hb, sd, sl_atr, slp, obs, int(draws), int(seed)))


def split_stats(trades: list[dict[str, Any]], years: frozenset[int] | set[int]) -> dict[str, Any]:
    sub = [t for t in trades if t["year"] in years]
    n = len(sub)
    if n == 0:
        return {"n": 0, "net_R": 0.0, "base_R": 0.0, "double_R": 0.0, "pf": 0.0, "win_pct": 0.0, "dd_R": 0.0}
    rs = [float(t["ftmo_R"]) for t in sub]
    gp = fsum(x for x in rs if x > 0)
    gl = -fsum(x for x in rs if x < 0)
    pf = gp / gl if gl > 1e-9 else (9.99 if gp > 0 else 0.0)
    eq = np.cumsum([0.0] + rs)
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return {
        "n": n,
        "net_R": round(fsum(rs), 2),
        "base_R": round(fsum(float(t["base_R"]) for t in sub), 2),
        "double_R": round(fsum(float(t["double_R"]) for t in sub), 2),
        "pf": round(pf, 3),
        "win_pct": round(100.0 * sum(x > 0 for x in rs) / n, 1),
        "dd_R": round(dd, 2),
    }


def build_pass29_catalog() -> list[dict[str, Any]]:
    """Pre-registered 24-spec catalog across 4 economic hypotheses on Gold & Global Indices (Dev < 2025 ONLY)."""
    return [
        # H1: London/NY Fix Drift (8)
        {"id": "P29_H1_XAU_PRE_LON_PMFIX_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "XAUUSD", "kind": "XAU_PRE_PMFIX", "thr": 0.30, "sl_atr": 0.60},
        {"id": "P29_H1_XAU_POST_AMFIX_NY", "hyp": "H1_FIX_DRIFT", "asset": "XAUUSD", "kind": "XAU_POST_AMFIX", "thr": 0.35, "sl_atr": 0.75},
        {"id": "P29_H1_XAU_NY_CLOSE_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "XAUUSD", "kind": "XAU_NY_EOD", "thr": 0.35, "sl_atr": 0.70},
        {"id": "P29_H1_GER40_LON4PM_FIX", "hyp": "H1_FIX_DRIFT", "asset": "GER40", "kind": "GER40_FIX16L", "thr": 0.30, "sl_atr": 0.60},
        {"id": "P29_H1_US500_NY_EOD_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "US500", "kind": "US_NY_EOD", "thr": 0.30, "sl_atr": 0.60},
        {"id": "P29_H1_US100_NY_EOD_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "US100", "kind": "US_NY_EOD", "thr": 0.35, "sl_atr": 0.65},
        {"id": "P29_H1_US500_LON4PM_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "US500", "kind": "US_LON4PM", "thr": 0.30, "sl_atr": 0.65},
        {"id": "P29_H1_US100_LON4PM_DRIFT", "hyp": "H1_FIX_DRIFT", "asset": "US100", "kind": "US_LON4PM", "thr": 0.35, "sl_atr": 0.65},
        # H2: Opening-Range Vol Squeeze (6)
        {"id": "P29_H2_XAU_LDN_OR60_SQZ35", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "XAUUSD", "kind": "XAU_LDN_OR60", "thr": 0.35, "sl_atr": 0.70},
        {"id": "P29_H2_XAU_NY_OR30_SQZ30", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "XAUUSD", "kind": "XAU_NY_OR30", "thr": 0.30, "sl_atr": 0.70},
        {"id": "P29_H2_US500_OR30_SQZ35", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "US500", "kind": "US_OR30_SQZ", "thr": 0.35, "sl_atr": 0.65},
        {"id": "P29_H2_US100_OR30_SQZ35", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "US100", "kind": "US_OR30_SQZ", "thr": 0.35, "sl_atr": 0.65},
        {"id": "P29_H2_GER40_OR30_SQZ35", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "GER40", "kind": "GER_OR30_SQZ", "thr": 0.35, "sl_atr": 0.65},
        {"id": "P29_H2_GER40_OR60_SQZ45", "hyp": "H2_OR_VOL_SQUEEZE", "asset": "GER40", "kind": "GER_OR60_SQZ", "thr": 0.45, "sl_atr": 0.65},
        # H3: Gold Asian -> London Mean Reversion (+ Continuation control) (4)
        {"id": "P29_H3_XAU_ASIA_LDN_REV_30", "hyp": "H3_GOLD_ASIA_LDN_REV", "asset": "XAUUSD", "kind": "XAU_ASIA_REV_TP", "thr": 0.30, "sl_atr": 0.70},
        {"id": "P29_H3_XAU_ASIA_LDN_REV_50", "hyp": "H3_GOLD_ASIA_LDN_REV", "asset": "XAUUSD", "kind": "XAU_ASIA_REV_RAW", "thr": 0.50, "sl_atr": 0.75},
        {"id": "P29_H3_XAU_ASIA_LDN_REV_40_08U", "hyp": "H3_GOLD_ASIA_LDN_REV", "asset": "XAUUSD", "kind": "XAU_ASIA_REV_08U", "thr": 0.40, "sl_atr": 0.70},
        {"id": "P29_H3_XAU_ASIA_LDN_CONT_40", "hyp": "H3_GOLD_ASIA_LDN_REV", "asset": "XAUUSD", "kind": "XAU_ASIA_CONT", "thr": 0.40, "sl_atr": 0.75},
        # H4: Index Auction Momentum (+ Fade control) (6)
        {"id": "P29_H4_US500_AUCT15_MOM_25", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "US500", "kind": "IDX_AUCT15_GAP", "thr": 0.25, "sl_atr": 0.65},
        {"id": "P29_H4_US100_AUCT15_MOM_25", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "US100", "kind": "IDX_AUCT15_GAP", "thr": 0.25, "sl_atr": 0.65},
        {"id": "P29_H4_GER40_AUCT15_MOM_25", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "GER40", "kind": "GER_AUCT15_GAP", "thr": 0.25, "sl_atr": 0.65},
        {"id": "P29_H4_US500_AUCT15_FADE_30", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "US500", "kind": "IDX_AUCT15_FADE", "thr": 0.30, "sl_atr": 0.65},
        {"id": "P29_H4_US100_AUCT30_CONT_40", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "US100", "kind": "US_AUCT30_CONT", "thr": 0.40, "sl_atr": 0.65},
        {"id": "P29_H4_GER40_AUCT30_CONT_40", "hyp": "H4_INDEX_AUCTION_MOM", "asset": "GER40", "kind": "GER_AUCT30_CONT", "thr": 0.40, "sl_atr": 0.65},
    ]


def eval_pass29_spec(bundles: dict[str, Any], cfg: dict[str, Any]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    asset = cfg["asset"]
    kind = cfg["kind"]
    thr = float(cfg["thr"])
    sl_atr = float(cfg["sl_atr"])
    b = bundles[asset]
    times, quotes = b["times"], b["quotes"]
    trs, fds = [], []

    for d in b["days"]:
        dk = d["day"]
        dsec = d["day_sec"]
        atr = float(d["atr"])
        tr = fd = None

        if kind == "XAU_PRE_PMFIX":
            ts_s, ts_e, ts_f = local_ts(dk, 12, 0, LONDON_TZ), local_ts(dk, 14, 0, LONDON_TZ), local_ts(dk, 15, 15, LONDON_TZ)
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=dsec + 7 * 3600)
        elif kind == "XAU_POST_AMFIX":
            ts_s, ts_e, ts_f = local_ts(dk, 8, 0, LONDON_TZ), local_ts(dk, 10, 35, LONDON_TZ), local_ts(dk, 15, 0, LONDON_TZ)
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=dsec + 7 * 3600)
        elif kind == "XAU_NY_EOD":
            ts_s, ts_e, ts_f = local_ts(dk, 10, 0, NY_TZ), local_ts(dk, 13, 30, NY_TZ), local_ts(dk, 16, 45, NY_TZ)
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=local_ts(dk, 8, 20, NY_TZ))
        elif kind == "GER40_FIX16L":
            ts_s, ts_e, ts_f = local_ts(dk, 14, 0, BERLIN_TZ), local_ts(dk, 15, 30, BERLIN_TZ), local_ts(dk, 17, 25, BERLIN_TZ)
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=local_ts(dk, 9, 0, BERLIN_TZ))
        elif kind == "US_NY_EOD":
            ts_s, ts_e, ts_f = dsec + 120 * 60, dsec + 270 * 60, dsec + 385 * 60  # 11:30 -> 14:00 ET, flat 15:55 ET
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=dsec)
        elif kind == "US_LON4PM":
            ts_s, ts_e, ts_f = dsec, dsec + 90 * 60, dsec + 240 * 60  # 09:30 -> 11:00 ET (16:00 LDN), flat 13:30 ET
            z = p26.causal_z_return(b, ts_s, ts_e, atr)
            if z is not None and abs(z) >= thr:
                tr, fd = _market_entry_window(b, d, ts_e, ts_f, 1 if z > 0 else -1, sl_atr, win_start_ts=dsec)

        elif kind in ("XAU_LDN_OR60", "XAU_NY_OR30", "US_OR30_SQZ", "GER_OR30_SQZ", "GER_OR60_SQZ"):
            if kind == "XAU_LDN_OR60":
                ts_o0, ts_o1, ts_we = dsec + 7 * 3600, dsec + 8 * 3600, dsec + 16 * 3600
            elif kind == "XAU_NY_OR30":
                ts_o0, ts_o1, ts_we = local_ts(dk, 8, 20, NY_TZ), local_ts(dk, 8, 50, NY_TZ), local_ts(dk, 15, 30, NY_TZ)
            elif kind == "US_OR30_SQZ":
                ts_o0, ts_o1, ts_we = dsec, dsec + 30 * 60, dsec + 330 * 60
            elif kind == "GER_OR30_SQZ":
                ts_o0, ts_o1, ts_we = local_ts(dk, 9, 0, BERLIN_TZ), local_ts(dk, 9, 30, BERLIN_TZ), local_ts(dk, 16, 30, BERLIN_TZ)
            else:
                ts_o0, ts_o1, ts_we = local_ts(dk, 9, 0, BERLIN_TZ), local_ts(dk, 10, 0, BERLIN_TZ), local_ts(dk, 16, 30, BERLIN_TZ)
            m0 = int(times.searchsorted(ts_o0, side="left"))
            m1 = int(times.searchsorted(ts_o1, side="left"))
            if m1 - m0 >= 15:
                box = quotes[m0:m1]
                bh, bl = float(box[:, 1].max()), float(box[:, 2].min())
                rng = bh - bl
                if 1e-9 < rng <= thr * atr:
                    tr, fd = _stop_breakout_window(b, d, ts_o1, ts_we, bh, bl, sl_atr)

        elif kind in ("XAU_ASIA_REV_TP", "XAU_ASIA_REV_RAW", "XAU_ASIA_REV_08U", "XAU_ASIA_CONT"):
            ts_a0 = dsec
            ts_a1 = dsec + (8 * 3600 if kind == "XAU_ASIA_REV_08U" else 7 * 3600)
            ts_fl = dsec + (12 * 3600 if kind == "XAU_ASIA_REV_TP" else (14 * 3600 if kind in ("XAU_ASIA_REV_08U", "XAU_ASIA_CONT") else 13 * 3600))
            p0 = p26.causal_completed_bid(times, quotes, ts_a0 + 1800)  # First active Asia print <= 00:30 UTC
            p1 = p26.causal_completed_bid(times, quotes, ts_a1)
            if p0 is not None and p1 is not None:
                mv = p1 - p0
                z = mv / atr
                if abs(z) >= thr:
                    side = (1 if mv > 0 else -1) if kind == "XAU_ASIA_CONT" else (-1 if mv > 0 else 1)
                    tp_d = 0.50 * abs(mv) if kind == "XAU_ASIA_REV_TP" else None
                    tr, fd = _market_entry_window(b, d, ts_a1, ts_fl, side, sl_atr, tp_dist=tp_d, win_start_ts=dsec + 6 * 3600)

        elif kind in ("IDX_AUCT15_GAP", "GER_AUCT15_GAP", "IDX_AUCT15_FADE"):
            ts_o0 = local_ts(dk, 9, 0, BERLIN_TZ) if kind == "GER_AUCT15_GAP" else dsec
            ts_o1 = ts_o0 + 15 * 60
            ts_fl = ts_o0 + 180 * 60
            m0 = int(times.searchsorted(ts_o0, side="left"))
            m1 = int(times.searchsorted(ts_o1, side="left"))
            if m1 - m0 >= 10:
                op = float(quotes[m0, 0])
                cl = float(quotes[m1 - 1, 3])
                gap = op - float(d["prev_c"])
                r15 = (cl - op) / atr
                if kind == "IDX_AUCT15_FADE":
                    if abs(r15) >= thr:
                        tr, fd = _market_entry_window(b, d, ts_o1, ts_fl, -1 if r15 > 0 else 1, sl_atr, win_start_ts=ts_o0)
                else:
                    if abs(r15) >= thr and gap * r15 > 0.0:
                        tr, fd = _market_entry_window(b, d, ts_o1, ts_fl, 1 if r15 > 0 else -1, sl_atr, win_start_ts=ts_o0)

        elif kind in ("US_AUCT30_CONT", "GER_AUCT30_CONT"):
            ts_o0 = local_ts(dk, 9, 0, BERLIN_TZ) if kind == "GER_AUCT30_CONT" else dsec
            ts_o1 = ts_o0 + 30 * 60
            ts_fl = ts_o0 + (270 * 60 if kind == "GER_AUCT30_CONT" else 210 * 60)
            m0 = int(times.searchsorted(ts_o0, side="left"))
            m1 = int(times.searchsorted(ts_o1, side="left"))
            if m1 - m0 >= 20:
                aq = quotes[m0:m1]
                ao, ac = float(aq[0, 0]), float(aq[-1, 3])
                ah, al = float(aq[:, 1].max()), float(aq[:, 2].min())
                arng = ah - al
                if arng > 1e-9 and abs(ac - ao) >= thr * atr:
                    pos = (ac - al) / arng
                    if ac > ao and pos >= 0.75:
                        tr, fd = _market_entry_window(b, d, ts_o1, ts_fl, 1, sl_atr, win_start_ts=ts_o0)
                    elif ac < ao and pos <= 0.25:
                        tr, fd = _market_entry_window(b, d, ts_o1, ts_fl, -1, sl_atr, win_start_ts=ts_o0)

        if tr is not None and fd is not None:
            trs.append(tr)
            fds.append(fd)
    return trs, fds


def run_pass29(*, cache_dir: Path = hcache.DEFAULT_CACHE, jobs_root: Path = hcache.DEFAULT_JOBS) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    # Load frozen PORT_7E daily PnL series for orthogonality correlation audit
    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=cache_dir, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    _, dev_ex7 = replay_portfolio_m1(warm["ext_days"], warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_daily = {e["day"]: float(e["net_usd"]) / 100.0 for e in dev_ex7}

    # Build strictly Dev (< 2025-01-01) unified M1 Bid/Ask bundles for XAUUSD, US500, US100, GER40
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    assets4 = ("XAUUSD", "US500", "US100", "GER40")
    bundles = {}
    asset_audit = {}
    for a in assets4:
        b = p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map)
        enforce_pre_holdout_ts(int(b["times"].max()), stop_ts=STOP, context=f"pass29:{a}")
        bundles[a] = b
        asset_audit[a] = {"m1_rows": int(len(b["times"])), "days": len(b["days"]), "max_ts_lt_2025": True}

    catalog = build_pass29_catalog()
    m_total = len(catalog)
    rows: list[dict[str, Any]] = []
    p_sf_all_list: list[float] = []
    p_sf_b_list: list[float] = []

    for idx_c, cfg in enumerate(catalog):
        trs, fds = eval_pass29_spec(bundles, cfg)
        mA = split_stats(trs, CLUSTER_A_YEARS)
        mB = split_stats(trs, CLUSTER_B_YEARS)
        mAll = split_stats(trs, set(ALL_DEV_YEARS))
        yr_map = {str(y): round(fsum(float(t["ftmo_R"]) for t in trs if t["year"] == y), 2) for y in ALL_DEV_YEARS}

        # Sign-flip permutation p-values (Full Dev & Blind Cluster B)
        vals_all = [float(t["ftmo_R"]) for t in trs]
        fade_all = [float(f["ftmo_R"]) for f in fds]
        p_sf_all = sign_flip_p_numba(vals_all, fade_all, draws=SIGN_FLIP_DRAWS, seed=SEED + idx_c) if vals_all else 1.0

        vals_b = [float(t["ftmo_R"]) for t in trs if t["year"] in CLUSTER_B_YEARS]
        fade_b = [float(f["ftmo_R"]) for f in fds if f["year"] in CLUSTER_B_YEARS]
        p_sf_b = sign_flip_p_numba(vals_b, fade_b, draws=SIGN_FLIP_DRAWS, seed=SEED + 100 + idx_c) if vals_b else 1.0

        # Matched-Hold Random-Timing Null (Full Dev & Blind Cluster B, zero-leakage random-day pool)
        p_mh_all = compute_matched_hold_p(trs, bundles, years_filter=set(ALL_DEV_YEARS), draws=MATCHED_HOLD_DRAWS, seed=SEED + 200 + idx_c) if trs else 1.0
        trs_b = [t for t in trs if t["year"] in CLUSTER_B_YEARS]
        p_mh_b = compute_matched_hold_p(trs_b, bundles, years_filter=CLUSTER_B_YEARS, draws=MATCHED_HOLD_DRAWS, seed=SEED + 300 + idx_c) if trs_b else 1.0

        # Daily correlation vs frozen PORT_7E
        corr_7e = round(float(p18.daily_correlation(trs, port7_daily)["union_corr"]), 4) if trs else 0.0

        p_sf_all_list.append(p_sf_all)
        p_sf_b_list.append(p_sf_b)
        rows.append({
            "id": cfg["id"],
            "hyp": cfg["hyp"],
            "asset": cfg["asset"],
            "cluster_a_2018_2021": mA,
            "cluster_b_2022_2024": mB,
            "dev_all_2018_2024": mAll,
            "years_R": yr_map,
            "sign_flip_p_all": round(p_sf_all, 4),
            "sign_flip_p_b": round(p_sf_b, 4),
            "matched_hold_p_all": round(p_mh_all, 4),
            "matched_hold_p_b": round(p_mh_b, 4),
            "corr_vs_port7e": corr_7e,
        })

    q_all = benjamini_hochberg(p_sf_all_list)
    q_b = benjamini_hochberg(p_sf_b_list)
    qualifiers = []

    for r, qa_v, qb_v in zip(rows, q_all, q_b):
        r["bh_q_all"] = round(qa_v, 4)
        r["bh_q_b"] = round(qb_v, 4)
        mA = r["cluster_a_2018_2021"]
        mB = r["cluster_b_2022_2024"]
        mAll = r["dev_all_2018_2024"]

        fail_reasons = []
        if not (mA["n"] >= 40 and mA["net_R"] > 0 and mA["pf"] >= 1.05):
            fail_reasons.append("FAIL_CLUSTER_A")
        if not (mB["n"] >= 25 and mB["net_R"] > 0 and mB["pf"] >= 1.05):
            fail_reasons.append("FAIL_CLUSTER_B")
        if mAll["double_R"] <= 0:
            fail_reasons.append("FAIL_DOUBLE_COST")
        if qa_v >= 0.10:
            fail_reasons.append("FAIL_BH_FDR_ALL")
        if r["matched_hold_p_all"] >= 0.05:
            fail_reasons.append("FAIL_MATCHED_HOLD_NULL")
        if abs(r["corr_vs_port7e"]) >= 0.15:
            fail_reasons.append("FAIL_CORR_GT_015")

        r["verdict"] = "PASS_CANDIDATE" if not fail_reasons else "REJECTED"
        r["fail_reasons"] = fail_reasons
        if not fail_reasons:
            qualifiers.append(r["id"])

    summary = {
        "schema": "naqex-pass29-gold-index-dev-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_count": 0,
        "cluster_split": {"A": "2018-2021", "B": "2022-2024"},
        "assets_audited": asset_audit,
        "m_total": m_total,
        "passed_count": len(qualifiers),
        "passed_ids": qualifiers,
        "results": rows,
    }
    out_cache = ROOT / ".runtime" / "quant-pod-returns" / "pass29_gold_index_summary.json"
    out_cache.parent.mkdir(parents=True, exist_ok=True)
    out_cache.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M4.1 Pass 29 Gold & Indices Orthogonal Intraday Discovery (Dev < 2025 ONLY)")
    ap.parse_args()
    s = run_pass29()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "holdout_rows_analysed": s["holdout_rows_analysed"],
        "m_total": s["m_total"],
        "passed_count": s["passed_count"],
        "passed_ids": s["passed_ids"],
        "top_by_dev_R": sorted(
            [(r["id"], r["cluster_a_2018_2021"]["net_R"], r["cluster_b_2022_2024"]["net_R"], r["bh_q_all"], r["matched_hold_p_all"], r["corr_vs_port7e"], r["verdict"]) for r in s["results"]],
            key=lambda x: x[1] + x[2],
            reverse=True,
        )[:10],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
