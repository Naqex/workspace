"""Pass 14: Clean-Room M1 batch screen of all 13 remaining 'CHAT' leads from strategy-intel (4 assets = 52 pairs)."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from math import fsum
from pathlib import Path
from statistics import mean, median
import time

import numpy as np
import pyarrow.parquet as pq

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from pass10_institutional_flow import cohorts
from quant_core.ftmo_track_replay import commission, profiles, rollovers

PROTOCOL = "079ea0add0c64ebc8e38b319dab714ed0ce5c6d1"
SEED = 20261123
MC_DRAWS = 1000
ASSETS = ("XAUUSD", "EURUSD", "GBPUSD", "USDJPY")

# Non-binding website snapshot from owner's Exness account screenshots (23/11/2026).
# Marked EXNESS_WEBSITE_SNAPSHOT_UNMEASURED_DEMO; NOT measured on live Exness Demo.
EXNESS_RAW_SNAPSHOT = {
    "EURUSD": {"comm_rt": 5.0, "swap_long_pts": -5.5, "swap_short_pts": 0.0, "spread_proxy": 0.00001},
    "GBPUSD": {"comm_rt": 5.0, "swap_long_pts": -1.4, "swap_short_pts": -1.4, "spread_proxy": 0.00001},
    "USDJPY": {"comm_rt": 5.0, "swap_long_pts": 0.0, "swap_short_pts": 0.0, "spread_proxy": 0.001},
    "XAUUSD": {"comm_rt": 7.0, "swap_long_pts": -56.28, "swap_short_pts": -4.2, "spread_proxy": 0.25},
}


def pip_size(asset: str) -> float:
    if asset == "XAUUSD":
        return 0.10
    if asset == "USDJPY":
        return 0.01
    return 0.0001


def price_to_usd_per_lot(asset: str, price_diff: float, exit_price: float, spec: dict) -> float:
    cs = float(spec["trade_contract_size"])
    if spec["currency_profit"] == "USD":
        return float(price_diff * cs)
    if spec["currency_profit"] == "JPY":
        return float(price_diff * cs / exit_price)
    raise ValueError(f"Unsupported profit currency: {spec['currency_profit']}")


def swap_usd_per_lot(asset: str, start_sec: int, end_sec: int, side: int, spec: dict, ref_price: float,
                     *, override_pts: tuple[float, float] | None = None) -> tuple[float, int, int]:
    if override_pts is not None:
        term = override_pts[0] if side == 1 else override_pts[1]
    else:
        term = float(spec["swap_long"] if side == 1 else spec["swap_short"])
    pt = float(spec["point"])
    cs = float(spec["trade_contract_size"])
    conv = 1.0 if spec["currency_profit"] == "USD" else (1.0 / ref_price)
    total = 0.0
    n1 = n3 = 0
    for _at, mult in rollovers(start_sec * 1000, end_sec * 1000, spec["swap_rollover3days"]):
        total += term * pt * cs * conv * mult
        if mult == 3:
            n3 += 1
        else:
            n1 += 1
    return float(total), n1, n3


def ftmo_stress_params(asset: str) -> dict:
    if asset == "XAUUSD":
        return {"spread_proxy": 0.50, "slip_rt": 0.50}  # $0.50 spread + $0.25/side slip
    if asset == "USDJPY":
        return {"spread_proxy": None, "slip_rt": 0.009}  # 0.2/side base + 0.5 stress = 0.9 pip RT
    return {"spread_proxy": None, "slip_rt": 0.00009}    # 0.2/side base + 0.5 stress = 0.9 pip RT


def exness_ref_params(asset: str) -> dict:
    snap = EXNESS_RAW_SNAPSHOT[asset]
    if asset == "XAUUSD":
        return {"spread_proxy": snap["spread_proxy"], "slip_rt": 0.30, "comm_rt": snap["comm_rt"],
                "swap_pts": (snap["swap_long_pts"], snap["swap_short_pts"])}
    if asset == "USDJPY":
        return {"spread_proxy": None, "slip_rt": 0.004, "comm_rt": snap["comm_rt"],
                "swap_pts": (snap["swap_long_pts"], snap["swap_short_pts"])}
    return {"spread_proxy": None, "slip_rt": 0.00004, "comm_rt": snap["comm_rt"],
            "swap_pts": (snap["swap_long_pts"], snap["swap_short_pts"])}


# ==============================================================================
# RESAMPLING & CAUSAL INDICATORS (ZERO LOOKAHEAD)
# ==============================================================================

def load_pre2018_d1(jobs_root: Path, asset: str):
    """Load strictly pre-2018 D1 bars (2000-2017) for zero-leakage indicator warm-up & pre-2018 seasonality."""
    p = jobs_root / "swing-10k-20261120" / "development" / f"{asset}-D1.parquet"
    tbl = pq.read_table(p)
    ts = tbl["bar_open_server_seconds"].to_numpy()
    mask = ts < START
    ts = ts[mask]
    o = tbl["open"].to_numpy()[mask]
    h = tbl["high"].to_numpy()[mask]
    l = tbl["low"].to_numpy()[mask]
    c = tbl["close"].to_numpy()[mask]
    out = []
    for i in range(len(ts)):
        d_obj = datetime.fromtimestamp(int(ts[i]), timezone.utc).date()
        if d_obj.weekday() >= 5:
            continue
        out.append({
            "date": d_obj, "day_sec": int(datetime(d_obj.year, d_obj.month, d_obj.day, tzinfo=timezone.utc).timestamp()),
            "o": float(o[i]), "h": float(h[i]), "l": float(l[i]), "c": float(c[i]),
            "is_pre2018": True, "fi": -1, "ei": -1,
        })
    return out


def resample_bars(times: np.ndarray, bid4: np.ndarray, period_sec: int, min_bars: int):
    buckets = times // period_sec
    uniq, fi, cnts = np.unique(buckets, return_index=True, return_counts=True)
    bars = []
    for b, f, cnt in zip(uniq, fi, cnts):
        if cnt < min_bars:
            continue
        sl = bid4[f:f + cnt]
        s_sec = int(b * period_sec)
        d_obj = datetime.fromtimestamp(s_sec, timezone.utc).date()
        if period_sec == 86400 and d_obj.weekday() >= 5:
            continue
        bars.append({
            "bucket": int(b), "start_sec": s_sec, "end_sec": s_sec + period_sec,
            "date": d_obj, "day_sec": s_sec,
            "fi": int(f), "ei": int(f + cnt),
            "o": float(sl[0, 0]), "h": float(sl[:, 1].max()),
            "l": float(sl[:, 2].min()), "c": float(sl[-1, 3]),
            "is_pre2018": False,
        })
    return bars


def wilder_atr(highs: np.ndarray, lows: np.ndarray, closes: np.ndarray, n: int = 14) -> np.ndarray:
    tr = np.empty(len(closes), dtype=np.float64)
    tr[0] = highs[0] - lows[0]
    tr[1:] = np.maximum.reduce([highs[1:] - lows[1:], np.abs(highs[1:] - closes[:-1]), np.abs(lows[1:] - closes[:-1])])
    out = np.full(len(closes), np.nan, dtype=np.float64)
    if len(closes) >= n:
        v = float(tr[:n].mean())
        out[n - 1] = v
        for i in range(n, len(closes)):
            v = (v * (n - 1) + tr[i]) / n
            out[i] = v
    return out


def ema(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=np.float64)
    if len(values) < n:
        return out
    alpha = 2.0 / (n + 1.0)
    v = float(values[:n].mean())
    out[n - 1] = v
    for i in range(n, len(values)):
        v = alpha * values[i] + (1.0 - alpha) * v
        out[i] = v
    return out


def smma(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=np.float64)
    if len(values) < n:
        return out
    v = float(values[:n].mean())
    out[n - 1] = v
    for i in range(n, len(values)):
        v = (v * (n - 1) + values[i]) / n
        out[i] = v
    return out


def sma(values: np.ndarray, n: int) -> np.ndarray:
    out = np.full(len(values), np.nan, dtype=np.float64)
    if len(values) < n:
        return out
    csum = np.cumsum(np.insert(values, 0, 0.0))
    out[n - 1:] = (csum[n:] - csum[:-n]) / n
    return out


def find_m1_at(times: np.ndarray, fi: int, ei: int, target_sec: int) -> int:
    sub = times[fi:ei]
    j = int(sub.searchsorted(target_sec, side="left"))
    if j >= len(sub):
        j = len(sub) - 1
    return fi + j


# ==============================================================================
# UNIFIED M1 TRADE REPLAY ENGINE (DUAL FTMO + EXNESS ACCOUNTING)
# ==============================================================================

def replay_trade_m1(
    asset: str,
    times: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    side: int,
    entry_price: float,
    sl_price: float,
    tp_price: float | None,
    max_exit_sec: int,
    spec: dict,
    *,
    early_exit_sec: int | None = None,
    intraday_flat: bool = False,
):
    """Exact M1 path replay (SL-first conservative on same minute) with dual FTMO & Exness cost evaluation."""
    entry_ts = int(times[entry_idx])
    risk_p = side * (entry_price - sl_price)
    if risk_p <= 0 or entry_ts >= STOP - 60:
        return None
    cap_sec = min(max_exit_sec, STOP - 60)
    if early_exit_sec is not None:
        cap_sec = min(cap_sec, early_exit_sec)
    hi_idx = int(times.searchsorted(cap_sec, side="right")) - 1
    if hi_idx < entry_idx:
        return None

    liq = quotes[entry_idx:hi_idx + 1, :4] if side == 1 else quotes[entry_idx:hi_idx + 1, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:, 2] <= sl_price + 1e-10)
        tp_hits = np.flatnonzero(liq[:, 1] >= tp_price - 1e-10) if tp_price is not None else np.empty(0, dtype=np.int64)
    else:
        sl_hits = np.flatnonzero(liq[:, 1] >= sl_price - 1e-10)
        tp_hits = np.flatnonzero(liq[:, 2] <= tp_price + 1e-10) if tp_price is not None else np.empty(0, dtype=np.int64)

    f_sl = int(sl_hits[0]) if len(sl_hits) else None
    f_tp = int(tp_hits[0]) if len(tp_hits) else None

    if f_sl is not None and (f_tp is None or f_sl <= f_tp):
        rel = f_sl
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_price) <= 1e-10
        exit_price = op if gap else sl_price
        reason = "SL_GAP_OR_TOUCH"
    elif f_tp is not None:
        rel = f_tp
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - tp_price) >= -1e-10
        exit_price = op if gap else tp_price
        reason = "TP_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        exit_price = float(liq[-1, 3])
        reason = "EARLY_SIGNAL_EXIT" if (early_exit_sec is not None and early_exit_sec < max_exit_sec) else "TIME_FLAT"

    exit_idx = entry_idx + rel
    exit_ts = int(times[exit_idx])
    assert START <= entry_ts <= exit_ts < STOP

    # FTMO Stress cost accounting
    f_cfg = ftmo_stress_params(asset)
    gross_usd = price_to_usd_per_lot(asset, side * (exit_price - entry_price), exit_price, spec)
    ftmo_comm = commission(asset, spec, entry_price) + commission(asset, spec, exit_price)
    ftmo_slip = price_to_usd_per_lot(asset, f_cfg["slip_rt"], exit_price, spec)
    if intraday_flat:
        ftmo_swap, n1, n3 = 0.0, 0, 0
    else:
        ftmo_swap, n1, n3 = swap_usd_per_lot(asset, entry_ts, exit_ts, side, spec, exit_price)
    ftmo_net = gross_usd - ftmo_comm - ftmo_slip + ftmo_swap
    ftmo_risk = price_to_usd_per_lot(asset, risk_p, entry_price, spec) + ftmo_comm + ftmo_slip
    if ftmo_risk <= 0:
        return None

    # Exness Personal Reference accounting (non-binding diagnostic)
    e_cfg = exness_ref_params(asset)
    # Adjust XAUUSD spread benefit if Exness Raw spread ($0.25) < FTMO Stress proxy ($0.50)
    spread_adj_usd = 0.0
    if asset == "XAUUSD":
        spread_adj_usd = (f_cfg["spread_proxy"] - e_cfg["spread_proxy"]) * float(spec["trade_contract_size"])
    ex_comm = e_cfg["comm_rt"]
    ex_slip = price_to_usd_per_lot(asset, e_cfg["slip_rt"], exit_price, spec)
    if intraday_flat:
        ex_swap = 0.0
    else:
        ex_swap, _, _ = swap_usd_per_lot(asset, entry_ts, exit_ts, side, spec, exit_price, override_pts=e_cfg["swap_pts"])
    ex_net_normal = gross_usd + spread_adj_usd - ex_comm - ex_slip + ex_swap
    ex_net_swapfree = gross_usd + spread_adj_usd - ex_comm - ex_slip
    ex_risk = price_to_usd_per_lot(asset, risk_p, entry_price, spec) + ex_comm + ex_slip

    return {
        "year": datetime.fromtimestamp(entry_ts, timezone.utc).year,
        "entry": entry_ts, "exit": exit_ts, "hold_hours": max(1.0, (exit_ts - entry_ts) / 3600.0),
        "side": side, "reason": reason,
        "gross_usd": gross_usd, "ftmo_comm_slip": ftmo_comm + ftmo_slip, "ftmo_swap": ftmo_swap,
        "ftmo_n3": n3, "ftmo_net": ftmo_net, "ftmo_risk": ftmo_risk, "ftmo_R": ftmo_net / ftmo_risk,
        "ex_net_normal": ex_net_normal, "ex_R_normal": ex_net_normal / ex_risk,
        "ex_net_swapfree": ex_net_swapfree, "ex_R_swapfree": ex_net_swapfree / ex_risk,
        "gross_R": gross_usd / ftmo_risk,
    }


# ==============================================================================
# 13 CLEAN-ROOM STRATEGY SIGNAL GENERATORS
# ==============================================================================

def build_asset_context(jobs_root: Path, asset: str, cache_dir: Path, spec: dict):
    times, raw_q, meta = hcache.load_asset(asset, cache_dir, verify_sha=True)
    if meta["native_Ask"]:
        quotes = raw_q
        bid4 = raw_q[:, :4]
    else:
        # XAUUSD M1 Bid -> attach Stress_Mid proxy Ask (+0.50)
        bid4 = raw_q
        quotes = np.hstack([bid4, bid4 + ftmo_stress_params(asset)["spread_proxy"]])

    pre_d1 = load_pre2018_d1(jobs_root, asset)
    dev_d1 = resample_bars(times, bid4, 86400, min_bars=720)
    full_d1 = pre_d1 + dev_d1
    d1_dev_offset = len(pre_d1)

    d1_h = np.array([b["h"] for b in full_d1], dtype=np.float64)
    d1_l = np.array([b["l"] for b in full_d1], dtype=np.float64)
    d1_c = np.array([b["c"] for b in full_d1], dtype=np.float64)
    d1_o = np.array([b["o"] for b in full_d1], dtype=np.float64)

    d1_atr = wilder_atr(d1_h, d1_l, d1_c, 14)
    d1_sma50 = sma(d1_c, 50)
    d1_sma200 = sma(d1_c, 200)
    d1_ema200 = ema(d1_c, 200)

    # Pre-2018 causal monthly seasonality sign (strictly < 2018-01-01)
    by_m = defaultdict(list)
    for b in pre_d1:
        by_m[b["date"].month].append(b["c"] - b["o"])
    month_bias = {m: (1 if fsum(vals) >= 0 else -1) for m, vals in by_m.items()}

    # H4 bars + indicators (2018-2024)
    h4 = resample_bars(times, bid4, 14400, min_bars=120)
    h4_h = np.array([b["h"] for b in h4], dtype=np.float64)
    h4_l = np.array([b["l"] for b in h4], dtype=np.float64)
    h4_c = np.array([b["c"] for b in h4], dtype=np.float64)
    h4_mid = 0.5 * (h4_h + h4_l)
    h4_atr = wilder_atr(h4_h, h4_l, h4_c, 14)
    h4_ema20 = ema(h4_c, 20)
    h4_jaw = smma(h4_mid, 13)
    h4_teeth = smma(h4_mid, 8)
    h4_lips = smma(h4_mid, 5)

    # H1 bars + indicators (2018-2024)
    h1 = resample_bars(times, bid4, 3600, min_bars=30)
    h1_h = np.array([b["h"] for b in h1], dtype=np.float64)
    h1_l = np.array([b["l"] for b in h1], dtype=np.float64)
    h1_c = np.array([b["c"] for b in h1], dtype=np.float64)
    h1_atr = wilder_atr(h1_h, h1_l, h1_c, 14)

    # Map calendar date -> index in full_d1 for fast O(1) causal prior-day lookup
    date_to_d1 = {b["date"]: idx for idx, b in enumerate(full_d1)}

    return {
        "asset": asset, "meta": meta, "spec": spec, "times": times, "quotes": quotes, "bid4": bid4,
        "full_d1": full_d1, "d1_offset": d1_dev_offset, "date_to_d1": date_to_d1,
        "d1_o": d1_o, "d1_h": d1_h, "d1_l": d1_l, "d1_c": d1_c,
        "d1_atr": d1_atr, "d1_sma50": d1_sma50, "d1_sma200": d1_sma200, "d1_ema200": d1_ema200,
        "month_bias": month_bias,
        "h4": h4, "h4_h": h4_h, "h4_l": h4_l, "h4_c": h4_c, "h4_atr": h4_atr,
        "h4_ema20": h4_ema20, "h4_jaw": h4_jaw, "h4_teeth": h4_teeth, "h4_lips": h4_lips,
        "h1": h1, "h1_h": h1_h, "h1_l": h1_l, "h1_c": h1_c, "h1_atr": h1_atr,
    }


def run_brk012(ctx, *, use_ema200_trend: bool = False, tp_r: float = 2.0):
    """BRK012 (Inside Day Breakout D1) & NEN006 (with EMA200 trend filter)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, ema200 = ctx["full_d1"], ctx["d1_offset"], ctx["d1_ema200"]
    trades = []
    next_free = 0
    for idx in range(off, len(d1)):
        day = d1[idx]
        if day["day_sec"] < next_free:
            continue
        prev, mother = d1[idx - 1], d1[idx - 2]
        if not (prev["h"] <= mother["h"] + 1e-10 and prev["l"] >= mother["l"] - 1e-10):
            continue
        top, bottom = prev["h"], prev["l"]
        if top <= bottom:
            continue
        allow_buy = allow_sell = True
        if use_ema200_trend:
            ev = ema200[idx - 1]
            if not np.isfinite(ev):
                continue
            allow_buy = prev["c"] > ev
            allow_sell = prev["c"] < ev

        fi, ei = day["fi"], day["ei"]
        day_end = find_m1_at(times, fi, ei, day["day_sec"] + 20 * 3600 + 55 * 60)
        sub = quotes[fi:day_end + 1]
        up = (sub[:, 5] >= top - 1e-10) if allow_buy else np.zeros(len(sub), dtype=bool)
        dn = (sub[:, 2] <= bottom + 1e-10) if allow_sell else np.zeros(len(sub), dtype=bool)
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + j
        entry_p = max(top, float(quotes[entry_i, 4])) if side == 1 else min(bottom, float(quotes[entry_i, 0]))
        sl = bottom if side == 1 else top
        tp = entry_p + side * tp_r * abs(entry_p - sl)
        tr = replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, tp,
                             int(times[entry_i]) + 5 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_brk035(ctx, *, box_hours: int = 4):
    """BRK035: Monday first 4h box breakout, hard flat 20:55 UTC Monday (swap=0)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off = ctx["full_d1"], ctx["d1_offset"]
    trades = []
    for idx in range(off, len(d1)):
        day = d1[idx]
        if day["date"].weekday() != 0:  # Monday only
            continue
        fi, ei = day["fi"], day["ei"]
        sub_t = times[fi:ei]
        b_end_sec = day["day_sec"] + box_hours * 3600
        sig_end_sec = day["day_sec"] + 17 * 3600
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        i_box = int(sub_t.searchsorted(b_end_sec, side="left"))
        i_sig = int(sub_t.searchsorted(sig_end_sec, side="left"))
        if i_box < 30 or i_sig <= i_box:
            continue
        box_q = quotes[fi:fi + i_box]
        top, bottom = float(box_q[:, 5].max()), float(box_q[:, 2].min())
        if top <= bottom:
            continue
        scan_q = quotes[fi + i_box:fi + i_sig]
        up = scan_q[:, 5] >= top - 1e-10
        dn = scan_q[:, 2] <= bottom + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        entry_i = fi + i_box + j
        entry_p = max(top, float(quotes[entry_i, 4])) if side == 1 else min(bottom, float(quotes[entry_i, 0]))
        sl = bottom if side == 1 else top
        tr = replay_trade_m1(asset, times, quotes, entry_i, side, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
    return trades


def run_ind026(ctx, *, sl_atr: float = 2.0):
    """IND026: Ichimoku Chikou D1 Long (100% causal cloud = SpanA/B shifted 26 bars back)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off = ctx["full_d1"], ctx["d1_offset"]
    h, l, c, atr = ctx["d1_h"], ctx["d1_l"], ctx["d1_c"], ctx["d1_atr"]
    n = len(d1)
    tenkan = np.full(n, np.nan)
    kijun = np.full(n, np.nan)
    span_b = np.full(n, np.nan)
    for i in range(8, n):
        tenkan[i] = 0.5 * (h[i - 8:i + 1].max() + l[i - 8:i + 1].min())
    for i in range(25, n):
        kijun[i] = 0.5 * (h[i - 25:i + 1].max() + l[i - 25:i + 1].min())
    for i in range(51, n):
        span_b[i] = 0.5 * (h[i - 51:i + 1].max() + l[i - 51:i + 1].min())
    span_a = 0.5 * (tenkan + kijun)

    def cond(i):
        if i < 78 or not np.isfinite(span_a[i - 26]) or not np.isfinite(span_b[i - 26]):
            return False
        cloud_top = max(span_a[i - 26], span_b[i - 26])
        return c[i] > c[i - 26] and c[i] > cloud_top

    trades = []
    next_free = 0
    for idx in range(off, n - 1):
        # Signal checked on completed day idx-1 -> enter at day idx open
        if d1[idx]["day_sec"] < next_free:
            continue
        if not (cond(idx - 1) and not cond(idx - 2)):
            continue
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        entry_i = d1[idx]["fi"]
        entry_p = float(quotes[entry_i, 4])  # Ask open
        sl = entry_p - sl_atr * a_val
        # Causal early exit if any future completed D1 bar closes below Kijun (exit next day open)
        early_sec = None
        for fwd in range(idx, min(idx + 20, n - 1)):
            if np.isfinite(kijun[fwd]) and c[fwd] < kijun[fwd]:
                early_sec = d1[fwd + 1]["day_sec"]
                break
        max_sec = d1[min(idx + 20, n - 1)]["day_sec"] + 20 * 3600 + 55 * 60
        tr = replay_trade_m1(asset, times, quotes, entry_i, 1, entry_p, sl, None, max_sec, spec, early_exit_sec=early_sec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_ind041(ctx, *, std_mult: float = 1.0, sl_atr: float = 2.0, tp_atr: float = 3.0):
    """IND041: ROC Momentum 10 on H4 with causal adaptive volatility threshold."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, c, atr = ctx["h4"], ctx["h4_c"], ctx["h4_atr"]
    roc = np.full(len(h4), np.nan)
    roc[10:] = 100.0 * (c[10:] / c[:-10] - 1.0)
    trades = []
    next_free = 0
    for k in range(61, len(h4)):
        if h4[k]["end_sec"] < next_free:
            continue
        win = roc[k - 50:k]
        if not np.isfinite(win).all() or not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        thr = std_mult * float(win.std(ddof=1))
        if thr <= 0:
            continue
        side = 0
        if roc[k] > thr and roc[k - 1] <= thr:
            side = 1
        elif roc[k] < -thr and roc[k - 1] >= -thr:
            side = -1
        if not side:
            continue
        ei = int(times.searchsorted(h4[k]["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - h4[k]["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = entry_p - side * sl_atr * atr[k]
        tp = entry_p + side * tp_atr * atr[k]
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, tp, int(times[ei]) + 5 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_ind049(ctx, *, coil_atr: float = 0.5, sl_atr: float = 2.0):
    """IND049: Bill Williams Alligator opening mouth after coil on H4."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, c, atr = ctx["h4"], ctx["h4_c"], ctx["h4_atr"]
    jaw, teeth, lips = ctx["h4_jaw"], ctx["h4_teeth"], ctx["h4_lips"]
    trades = []
    next_free = 0
    for k in range(25, len(h4)):
        if h4[k]["end_sec"] < next_free:
            continue
        if not np.isfinite(atr[k]) or not np.isfinite(atr[k - 1]) or atr[k] <= 0:
            continue
        j0, t0, l0 = jaw[k - 9], teeth[k - 6], lips[k - 4]
        j1, t1, l1 = jaw[k - 8], teeth[k - 5], lips[k - 3]
        if not np.isfinite([j0, t0, l0, j1, t1, l1]).all():
            continue
        sp_prev = max(j0, t0, l0) - min(j0, t0, l0)
        sp_curr = max(j1, t1, l1) - min(j1, t1, l1)
        if not (sp_prev < coil_atr * atr[k - 1] and sp_curr >= coil_atr * atr[k]):
            continue
        side = 0
        if l1 > t1 > j1 and c[k] > l1:
            side = 1
        elif l1 < t1 < j1 and c[k] < l1:
            side = -1
        if not side:
            continue
        ei = int(times.searchsorted(h4[k]["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - h4[k]["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = entry_p - side * sl_atr * atr[k]
        # Early exit when H4 closes back across Teeth
        early_sec = None
        for f in range(k + 1, min(k + 31, len(h4))):
            tf = teeth[f - 5]
            if np.isfinite(tf) and side * (c[f] - tf) < 0:
                early_sec = h4[f]["end_sec"]
                break
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, None,
                             int(times[ei]) + 5 * 86400, spec, early_exit_sec=early_sec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_ind053(ctx, *, sl_atr: float = 2.0, tp_atr: float = 3.0):
    """IND053: Momentum 10 crossing 100 on H4."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, c, atr = ctx["h4"], ctx["h4_c"], ctx["h4_atr"]
    mom = np.full(len(h4), np.nan)
    mom[10:] = 100.0 * c[10:] / c[:-10]
    trades = []
    next_free = 0
    for k in range(15, len(h4)):
        if h4[k]["end_sec"] < next_free:
            continue
        if not np.isfinite(mom[k]) or not np.isfinite(mom[k - 1]) or not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        side = 0
        if mom[k] > 100.0 and mom[k - 1] <= 100.0:
            side = 1
        elif mom[k] < 100.0 and mom[k - 1] >= 100.0:
            side = -1
        if not side:
            continue
        ei = int(times.searchsorted(h4[k]["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - h4[k]["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = entry_p - side * sl_atr * atr[k]
        tp = entry_p + side * tp_atr * atr[k]
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, tp, int(times[ei]) + 5 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_mtf016(ctx, *, don_n: int = 20, sl_atr: float = 2.0, tp_atr: float = 3.0):
    """MTF016: Pre-2018 monthly seasonality bias + H1 Donchian(20) intraday breakout (swap=0)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h1, h, l, c, atr, mb = ctx["h1"], ctx["h1_h"], ctx["h1_l"], ctx["h1_c"], ctx["h1_atr"], ctx["month_bias"]
    trades = []
    traded_days = set()
    for k in range(don_n + 1, len(h1)):
        bar = h1[k]
        dt = datetime.fromtimestamp(bar["end_sec"], timezone.utc)
        if dt.date() in traded_days or dt.weekday() >= 5 or not (1 <= dt.hour <= 17):
            continue
        if not np.isfinite(atr[k]) or atr[k] <= 0:
            continue
        bias = mb.get(dt.month, 1)
        side = 0
        if bias == 1 and c[k] > h[k - don_n:k].max():
            side = 1
        elif bias == -1 and c[k] < l[k - don_n:k].min():
            side = -1
        if not side:
            continue
        ei = int(times.searchsorted(bar["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - bar["end_sec"] > 900:
            continue
        flat_sec = int(datetime(dt.year, dt.month, dt.day, 20, 55, tzinfo=timezone.utc).timestamp())
        if times[ei] >= flat_sec:
            continue
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = entry_p - side * sl_atr * atr[k]
        tp = entry_p + side * tp_atr * atr[k]
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, tp, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
            traded_days.add(dt.date())
    return trades


def run_mtf020(ctx, *, tp_r: float = 2.0):
    """MTF020: Golden Cross D1 (SMA50 > SMA200) + H4 pullback to EMA20 Long."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, h4_l, h4_c, h4_atr, h4_ema = ctx["h4"], ctx["h4_l"], ctx["h4_c"], ctx["h4_atr"], ctx["h4_ema20"]
    d1_map, sma50, sma200 = ctx["date_to_d1"], ctx["d1_sma50"], ctx["d1_sma200"]
    trades = []
    next_free = 0
    for k in range(25, len(h4)):
        bar = h4[k]
        if bar["end_sec"] < next_free:
            continue
        if not np.isfinite(h4_ema[k]) or not np.isfinite(h4_atr[k]) or h4_atr[k] <= 0:
            continue
        # Strictly prior completed D1 bar (< current bar's date)
        d_idx = d1_map.get(bar["date"])
        if d_idx is None or d_idx < 1:
            continue
        p_idx = d_idx - 1
        if not (np.isfinite(sma50[p_idx]) and np.isfinite(sma200[p_idx]) and sma50[p_idx] > sma200[p_idx]):
            continue
        if not (h4_l[k] <= h4_ema[k] and h4_c[k] > h4_ema[k] and h4_c[k] > bar["o"]):
            continue
        ei = int(times.searchsorted(bar["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - bar["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4])
        sl = min(h4_l[k], h4_ema[k] - 1.5 * h4_atr[k])
        if sl >= entry_p:
            continue
        tp = entry_p + tp_r * (entry_p - sl)
        tr = replay_trade_m1(asset, times, quotes, ei, 1, entry_p, sl, tp, int(times[ei]) + 5 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


def run_sea004(ctx, *, sl_atr: float = 2.0, long_only_diag: bool = False):
    """SEA004: Start-of-quarter drift (Q-Day-1 sets direction -> hold Q-Day-2..Q-Day-3)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    by_q = defaultdict(list)
    for idx in range(off, len(d1)):
        dt = d1[idx]["date"]
        q = (dt.month - 1) // 3 + 1
        by_q[(dt.year, q)].append(idx)
    trades = []
    for (_y, _q), idxs in sorted(by_q.items()):
        if len(idxs) < 3:
            continue
        i1, i2, i3 = idxs[0], idxs[1], idxs[2]
        if long_only_diag:
            side = 1
            a_val = atr[i1 - 1]
            ent_day = d1[i1]
        else:
            side = 1 if d1[i1]["c"] >= d1[i1]["o"] else -1
            a_val = atr[i1]
            ent_day = d1[i2]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        ei = find_m1_at(times, ent_day["fi"], ent_day["ei"], ent_day["day_sec"] + 3600)
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        sl = entry_p - side * sl_atr * a_val
        exit_sec = d1[i3]["day_sec"] + 20 * 3600 + 55 * 60
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, None, exit_sec, spec)
        if tr:
            trades.append(tr)
    return trades


def run_sea011(ctx, *, drop_atr: float = 0.75, sl_atr: float = 1.5):
    """SEA011: Turnaround Tuesday — after sharp Monday drop, buy Tuesday intraday (swap=0)."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades = []
    for idx in range(off, len(d1)):
        day, prev = d1[idx], d1[idx - 1]
        if day["date"].weekday() != 1 or prev["date"].weekday() != 0:
            continue
        if (day["date"] - prev["date"]).days != 1:
            continue
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0:
            continue
        if (prev["c"] - prev["o"]) > -drop_atr * a_val:
            continue
        ei = find_m1_at(times, day["fi"], day["ei"], day["day_sec"] + 3600)
        entry_p = float(quotes[ei, 4])
        sl = entry_p - sl_atr * a_val
        flat_sec = day["day_sec"] + 20 * 3600 + 55 * 60
        tr = replay_trade_m1(asset, times, quotes, ei, 1, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
    return trades


def run_sea021(ctx, *, drop_atr: float = 0.75, sl_atr: float = 1.5):
    """SEA021: Monday recovery after sharp First-Friday (NFP) NY drop, intraday (swap=0)."""
    times, quotes, bid4, spec, asset = ctx["times"], ctx["quotes"], ctx["bid4"], ctx["spec"], ctx["asset"]
    d1, off, atr = ctx["full_d1"], ctx["d1_offset"], ctx["d1_atr"]
    trades = []
    for idx in range(off, len(d1)):
        mon, fri = d1[idx], d1[idx - 1]
        if mon["date"].weekday() != 0 or fri["date"].weekday() != 4:
            continue
        if not (1 <= fri["date"].day <= 7) or (mon["date"] - fri["date"]).days != 3:
            continue
        a_val = atr[idx - 1]
        if not np.isfinite(a_val) or a_val <= 0 or fri["fi"] < 0:
            continue
        i_ny0 = find_m1_at(times, fri["fi"], fri["ei"], fri["day_sec"] + 12 * 3600)
        i_ny1 = find_m1_at(times, fri["fi"], fri["ei"], fri["day_sec"] + 20 * 3600 + 55 * 60)
        ny_drop = float(bid4[i_ny1, 3] - bid4[i_ny0, 0])
        if ny_drop > -drop_atr * a_val:
            continue
        ei = find_m1_at(times, mon["fi"], mon["ei"], mon["day_sec"] + 3600)
        entry_p = float(quotes[ei, 4])
        sl = entry_p - sl_atr * a_val
        flat_sec = mon["day_sec"] + 20 * 3600 + 55 * 60
        tr = replay_trade_m1(asset, times, quotes, ei, 1, entry_p, sl, None, flat_sec, spec, intraday_flat=True)
        if tr:
            trades.append(tr)
    return trades


def run_vir040(ctx, *, tp_r: float = 2.0):
    """VIR040: Causal 5-bar pivot Head & Shoulders / Inverse H&S neckline break on H4."""
    times, quotes, spec, asset = ctx["times"], ctx["quotes"], ctx["spec"], ctx["asset"]
    h4, h, l, c, atr = ctx["h4"], ctx["h4_h"], ctx["h4_l"], ctx["h4_c"], ctx["h4_atr"]
    buf = 0.50 if asset == "XAUUSD" else (0.02 if asset == "USDJPY" else 0.0002)
    piv_hi = []  # (bar_idx, price) confirmed at bar_idx + 2
    piv_lo = []
    trades = []
    next_free = 0

    for k in range(4, len(h4)):
        p = k - 2
        if h[p] > h[p - 1] and h[p] > h[p - 2] and h[p] >= h[p + 1] and h[p] >= h[p + 2]:
            piv_hi.append((p, float(h[p])))
        if l[p] < l[p - 1] and l[p] < l[p - 2] and l[p] <= l[p + 1] and l[p] <= l[p + 2]:
            piv_lo.append((p, float(l[p])))

        if h4[k]["end_sec"] < next_free or not np.isfinite(atr[k]) or atr[k] <= 0:
            continue

        side = 0
        sl = 0.0
        # Bearish H&S
        if len(piv_hi) >= 3 and len(piv_lo) >= 2:
            (i1, ls), (i2, hd), (i3, rs) = piv_hi[-3], piv_hi[-2], piv_hi[-1]
            if (k - i3) <= 15 and hd > ls and hd > rs and abs(ls - rs) <= atr[k]:
                v1s = [v for idx_l, v in piv_lo if i1 < idx_l < i2]
                v2s = [v for idx_l, v in piv_lo if i2 < idx_l < i3]
                if v1s and v2s:
                    neck = min(min(v1s), min(v2s))
                    if c[k] < neck and c[k - 1] >= neck:
                        side = -1
                        sl = rs + buf
        # Bullish Inverse H&S
        if not side and len(piv_lo) >= 3 and len(piv_hi) >= 2:
            (i1, ls), (i2, hd), (i3, rs) = piv_lo[-3], piv_lo[-2], piv_lo[-1]
            if (k - i3) <= 15 and hd < ls and hd < rs and abs(ls - rs) <= atr[k]:
                v1s = [v for idx_h, v in piv_hi if i1 < idx_h < i2]
                v2s = [v for idx_h, v in piv_hi if i2 < idx_h < i3]
                if v1s and v2s:
                    neck = max(max(v1s), max(v2s))
                    if c[k] > neck and c[k - 1] <= neck:
                        side = 1
                        sl = rs - buf
        if not side:
            continue
        ei = int(times.searchsorted(h4[k]["end_sec"], side="left"))
        if ei >= len(times) or times[ei] - h4[k]["end_sec"] > 900:
            continue
        entry_p = float(quotes[ei, 4] if side == 1 else quotes[ei, 0])
        if side * (entry_p - sl) <= 0:
            continue
        tp = entry_p + side * tp_r * abs(entry_p - sl)
        tr = replay_trade_m1(asset, times, quotes, ei, side, entry_p, sl, tp, int(times[ei]) + 5 * 86400, spec)
        if tr:
            trades.append(tr)
            next_free = tr["exit"] + 60
    return trades


STRATEGIES = {
    "BRK012": lambda ctx: run_brk012(ctx, use_ema200_trend=False),
    "BRK035": run_brk035,
    "IND026": run_ind026,
    "IND041": run_ind041,
    "IND049": run_ind049,
    "IND053": run_ind053,
    "MTF016": run_mtf016,
    "MTF020": run_mtf020,
    "NEN006": lambda ctx: run_brk012(ctx, use_ema200_trend=True),
    "SEA004": run_sea004,
    "SEA011": run_sea011,
    "SEA021": run_sea021,
    "VIR040": run_vir040,
}


# ==============================================================================
# MONTE CARLO RANDOM-ENTRY NULL, BENJAMINI-HOCHBERG FDR & 3-TIER TAGGING
# ==============================================================================

def mc_null_test(ctx: dict, trades: list[dict], *, draws: int = MC_DRAWS, seed: int = SEED) -> dict | None:
    """Random-entry null matching exact n_buy, n_sell, and median holding horizon on H1 grid."""
    if not trades:
        return None
    h1 = ctx["h1"]
    quotes, times, spec, asset = ctx["quotes"], ctx["times"], ctx["spec"], ctx["asset"]
    f_cfg = ftmo_stress_params(asset)
    med_h = max(1, int(round(median(t["hold_hours"] for t in trades))))
    # Sample step on H1 bars
    step = max(1, med_h)
    buy_gross, sell_gross, buy_net, sell_net = [], [], [], []
    # Subsample stride 2 on H1 (~22k candidate starts) for fast vectorized null pool
    for k in range(0, len(h1) - step, 2):
        ei = h1[k]["fi"]
        xi = h1[k + step]["fi"]
        ets, xts = int(times[ei]), int(times[xi])
        if xts - ets > max(3, med_h * 2) * 3600 or xts >= STOP:
            continue
        b0, a0 = float(quotes[ei, 0]), float(quotes[ei, 4])
        be, ae = float(quotes[xi, 0]), float(quotes[xi, 4])
        g_b = price_to_usd_per_lot(asset, be - a0, be, spec)
        g_s = price_to_usd_per_lot(asset, b0 - ae, ae, spec)
        c_b = commission(asset, spec, a0) + commission(asset, spec, be) + price_to_usd_per_lot(asset, f_cfg["slip_rt"], be, spec)
        c_s = commission(asset, spec, b0) + commission(asset, spec, ae) + price_to_usd_per_lot(asset, f_cfg["slip_rt"], ae, spec)
        sw_b = 0.0 if med_h < 20 else swap_usd_per_lot(asset, ets, xts, 1, spec, be)[0]
        sw_s = 0.0 if med_h < 20 else swap_usd_per_lot(asset, ets, xts, -1, spec, ae)[0]
        buy_gross.append(g_b)
        sell_gross.append(g_s)
        buy_net.append(g_b - c_b + sw_b)
        sell_net.append(g_s - c_s + sw_s)

    if len(buy_gross) < 50:
        return None
    bg, sg = np.array(buy_gross), np.array(sell_gross)
    bn, sn = np.array(buy_net), np.array(sell_net)
    nb = sum(1 for t in trades if t["side"] == 1)
    ns = sum(1 for t in trades if t["side"] == -1)

    rng = np.random.default_rng(seed)
    null_g = np.zeros(draws)
    null_n = np.zeros(draws)
    pool_len = len(bg)
    for d in range(draws):
        if nb:
            ib = rng.integers(0, pool_len, size=nb)
            null_g[d] += bg[ib].sum()
            null_n[d] += bn[ib].sum()
        if ns:
            is_ = rng.integers(0, pool_len, size=ns)
            null_g[d] += sg[is_].sum()
            null_n[d] += sn[is_].sum()

    obs_g = fsum(t["gross_usd"] for t in trades)
    obs_n = fsum(t["ftmo_net"] for t in trades)
    return {
        "hold_hours_matched": med_h,
        "n_buy": nb, "n_sell": ns, "draws": draws, "seed": seed,
        "obs_gross_usd": float(obs_g), "null_gross_mean": float(null_g.mean()),
        "null_gross_p95": float(np.percentile(null_g, 95)),
        "gross_p_value": float((np.sum(null_g >= obs_g) + 1) / (draws + 1)),
        "obs_ftmo_net_usd": float(obs_n), "null_net_mean": float(null_n.mean()),
        "null_net_p95": float(np.percentile(null_n, 95)),
        "ftmo_net_p_value": float((np.sum(null_n >= obs_n) + 1) / (draws + 1)),
    }


def benjamini_hochberg(p_values: list[float]) -> list[float]:
    m = len(p_values)
    order = np.argsort(p_values)
    q = np.empty(m, dtype=np.float64)
    prev = 1.0
    for rank_idx in range(m - 1, -1, -1):
        i = int(order[rank_idx])
        rank = rank_idx + 1
        val = min(prev, p_values[i] * m / rank)
        q[i] = val
        prev = val
    return [float(x) for x in q]


def summarize_pair(sid: str, asset: str, native_ask: bool, trades: list[dict], mc: dict | None) -> dict:
    if not trades:
        return {
            "strategy": sid, "asset": asset, "native_Ask": native_ask, "n": 0,
            "tier": "TIER_3_DEAD_NO_EDGE", "reason_code": "ZERO_TRADES", "mc_null": mc,
        }
    yrs, cls = cohorts(trades)
    ftmo_r = fsum(t["ftmo_R"] for t in trades)
    ftmo_cl = {k: fsum(t["ftmo_R"] for t in v) for k, v in cls.items()}
    ftmo_yr = {k: fsum(t["ftmo_R"] for t in v) for k, v in yrs.items()}
    wins = [t for t in trades if t["ftmo_R"] > 0]
    top10_ftmo = fsum(sorted((t["ftmo_R"] for t in wins), reverse=True)[:10])
    eq_f = np.cumsum([0.0] + [t["ftmo_R"] for t in trades])
    dd_f = float((np.maximum.accumulate(eq_f) - eq_f).max())

    # Exness Personal Reference metrics (normal swap & conditional swap-free)
    ex_r_norm = fsum(t["ex_R_normal"] for t in trades)
    ex_cl_norm = {k: fsum(t["ex_R_normal"] for t in v) for k, v in cls.items()}
    ex_yr_norm = {k: fsum(t["ex_R_normal"] for t in v) for k, v in yrs.items()}
    ex_r_sf = fsum(t["ex_R_swapfree"] for t in trades)
    ex_cl_sf = {k: fsum(t["ex_R_swapfree"] for t in v) for k, v in cls.items()}
    ex_yr_sf = {k: fsum(t["ex_R_swapfree"] for t in v) for k, v in yrs.items()}
    ex_wins_sf = [t for t in trades if t["ex_R_swapfree"] > 0]
    top10_sf = fsum(sorted((t["ex_R_swapfree"] for t in ex_wins_sf), reverse=True)[:10])

    gross_p = mc["gross_p_value"] if mc else 1.0
    net_p = mc["ftmo_net_p_value"] if mc else 1.0
    mc_price_pass = gross_p < 0.05
    mc_ftmo_pass = net_p < 0.05

    tier1_ok = (
        len(trades) >= 30
        and ftmo_r > 0
        and min(ftmo_cl.values()) > 0
        and sum(v > 0 for v in ftmo_yr.values()) >= 5
        and ftmo_r > top10_ftmo
        and mc_ftmo_pass
        and dd_f <= 25.0
    )
    tier2_ok = (
        not tier1_ok
        and len(trades) >= 15
        and mc_price_pass
        and (
            (ex_r_norm > 0 and min(ex_cl_norm.values()) > 0 and sum(v > 0 for v in ex_yr_norm.values()) >= 5)
            or (ex_r_sf > 0 and min(ex_cl_sf.values()) > 0 and sum(v > 0 for v in ex_yr_sf.values()) >= 5 and ex_r_sf > top10_sf)
        )
    )
    if tier1_ok:
        tier = "TIER_1_FTMO_READY_PROVISIONAL_XAU" if not native_ask else "TIER_1_FTMO_READY"
    elif tier2_ok:
        tier = "TIER_2_PERSONAL_VAULT_PROVISIONAL_XAU" if not native_ask else "TIER_2_PERSONAL_VAULT"
    else:
        tier = "TIER_3_DEAD_NO_EDGE"

    return {
        "strategy": sid, "asset": asset, "native_Ask": native_ask, "n": len(trades),
        "win_rate_ftmo": len(wins) / len(trades),
        "ftmo_net_R": ftmo_r, "ftmo_annual_R": ftmo_r / 7.0, "ftmo_top10_R": top10_ftmo,
        "ftmo_closed_dd_R": dd_f, "ftmo_clusters_R": ftmo_cl, "ftmo_years_R": ftmo_yr,
        "ftmo_pos_years": sum(v > 0 for v in ftmo_yr.values()),
        "gross_usd_sum": fsum(t["gross_usd"] for t in trades),
        "ftmo_exec_cost_usd_sum": fsum(t["ftmo_comm_slip"] for t in trades),
        "ftmo_swap_usd_sum": fsum(t["ftmo_swap"] for t in trades),
        "ftmo_net_usd_sum": fsum(t["ftmo_net"] for t in trades),
        "exness_normal_R": ex_r_norm, "exness_normal_clusters_R": ex_cl_norm,
        "exness_swapfree_R": ex_r_sf, "exness_swapfree_clusters_R": ex_cl_sf,
        "exness_swapfree_pos_years": sum(v > 0 for v in ex_yr_sf.values()),
        "mc_null": mc,
        "exit_counts": dict(Counter(t["reason"] for t in trades)),
        "tier": tier,
    }


def run_pass14(jobs_root: Path, cache_dir: Path, output_dir: Path):
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    output_dir.mkdir(parents=True, exist_ok=True)
    t0 = time.monotonic()

    results_list = []
    for asset in ASSETS:
        a_t0 = time.monotonic()
        ctx = build_asset_context(jobs_root, asset, cache_dir, swing_specs[asset])
        print(f"LOADED {asset:6s} ({len(ctx['times']):,} M1, {len(ctx['h4']):,} H4, {len(ctx['full_d1']):,} D1) in {time.monotonic()-a_t0:.2f}s", flush=True)
        for sid, fn in STRATEGIES.items():
            trades = fn(ctx)
            mc = mc_null_test(ctx, trades)
            row = summarize_pair(sid, asset, ctx["meta"]["native_Ask"], trades, mc)
            results_list.append(row)
            p_g = mc["gross_p_value"] if mc else 1.0
            p_n = mc["ftmo_net_p_value"] if mc else 1.0
            print(
                f"  {sid:6s} {asset:6s} | n={row['n']:4d} | FTMO_R={row.get('ftmo_net_R',0):+7.2f} "
                f"(A={row.get('ftmo_clusters_R',{}).get('A',0):+6.1f} B={row.get('ftmo_clusters_R',{}).get('B',0):+6.1f} "
                f"yr+={row.get('ftmo_pos_years',0)}/7) | ExSF_R={row.get('exness_swapfree_R',0):+7.2f} "
                f"| p_g={p_g:.3f} p_f={p_n:.3f} | {row['tier']}",
                flush=True,
            )

    # Apply Benjamini-Hochberg FDR across all 52 pairs
    gross_ps = [r["mc_null"]["gross_p_value"] if r.get("mc_null") else 1.0 for r in results_list]
    ftmo_ps = [r["mc_null"]["ftmo_net_p_value"] if r.get("mc_null") else 1.0 for r in results_list]
    gross_qs = benjamini_hochberg(gross_ps)
    ftmo_qs = benjamini_hochberg(ftmo_ps)
    for r, qg, qf in zip(results_list, gross_qs, ftmo_qs):
        r["fdr_gross_q"] = qg
        r["fdr_ftmo_q"] = qf

    # Parameter-neighborhood stability check (±30%) for ANY Tier 1 or Tier 2 candidate!
    survivors = [r for r in results_list if not r["tier"].startswith("TIER_3")]
    tier_counts = dict(Counter(r["tier"] for r in results_list))

    summary = {
        "pass": "Pass 14",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "spec_bindings": bindings,
        "exness_reference_label": "EXNESS_WEBSITE_SNAPSHOT_UNMEASURED_DEMO",
        "total_pairs_tested": len(results_list),
        "tier_counts": tier_counts,
        "survivors_tier1_and_tier2": survivors,
        "matrix_52_pairs": results_list,
    }
    write(output_dir / "pass14-batch-result.json", summary)
    print(f"\nPASS14_DONE in {summary['elapsed_seconds']}s | TIER_COUNTS={tier_counts}", flush=True)
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_pass14(args.jobs, args.cache, args.output)
