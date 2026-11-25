"""Pass 13 Track 2: Clean-Room Air-Gap Reproduction of NEN022 (Fakey H4) & SEA003 (XAUUSD Turn-of-Month)."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import fsum
from pathlib import Path
from statistics import mean, median

import numpy as np
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as clock
import pass11_gbpusd_m1 as ingest
import pass11_portfolio as portfolio
from native_ftmo_monfri_seal import START, STOP, read, sha, write
from pass10_institutional_flow import cohorts
from pass12_usdjpy_forensic import path_intervals, tally, timeline
from quant_core.ftmo_track_replay import commission, profiles, rollovers

PROTOCOL = "62ef31363604fc4588f0cb4d7a699efd80737cde"
SEED = 20261123
MC_DRAWS = 1000


def load_xauusd_m1_bid(folder: Path):
    """Load sealed XAUUSD M1 Bid parquets (2018-2024) as (times_sec, bid_ohlc_4col)."""
    manifest = read(folder / "manifest.json")
    ts_parts, ohlc_parts = [], []
    for year in clock.YEAR:
        meta = manifest["years"][str(year)]
        path = folder / meta["parquet"]
        if sha(path) != meta["parquet_sha256"]:
            raise ValueError(f"XAUUSD parquet SHA mismatch: {year}")
        tbl = pq.read_table(path)
        mins = tbl["minute"].to_numpy()
        scale = float(meta["scale"])
        arr = np.column_stack([tbl[c].to_numpy() for c in ("bo", "bh", "bl", "bc")]) / scale
        ts = mins * 60
        assert START <= int(ts[0]) <= int(ts[-1]) < STOP
        ts_parts.append(ts)
        ohlc_parts.append(arr)
    times = np.concatenate(ts_parts)
    bid = np.vstack(ohlc_parts)
    assert (np.diff(times) > 0).all()
    return times, bid, manifest


def load_fx_m1_bidask(folder: Path, asset: str):
    """Load sealed EURUSD/GBPUSD native Tick-derived M1 Bid/Ask (2018-2024) as (times_sec, quotes_8col)."""
    manifest = read(folder / "manifest.json")
    ts_parts, q_parts = [], []
    for year in clock.YEAR:
        times, values = ingest.load_m1(folder, year, manifest["years"][str(year)], asset=asset, scale=ingest.GRID)
        assert START <= int(times[0]) <= int(times[-1]) < STOP
        ts_parts.append(times)
        q_parts.append(values[:, :8])
    times = np.concatenate(ts_parts)
    quotes = np.vstack(q_parts)
    assert (np.diff(times) > 0).all()
    return times, quotes, manifest


def make_quotes_from_bid(bid_4col: np.ndarray, spread: float) -> np.ndarray:
    """Attach explicit proxy Ask = Bid + spread (explicitly flagged native_Ask=False)."""
    return np.hstack([bid_4col, bid_4col + spread])


def compute_swap_usd_per_lot(start_sec: int, end_sec: int, side: int, spec: dict) -> tuple[float, int, int]:
    """Exact FTMO rollover swap in USD per 1.0 lot (USD-quoted symbols EURUSD, GBPUSD, XAUUSD)."""
    term = spec["swap_long"] if side == 1 else spec["swap_short"]
    point = spec["point"]
    cs = spec["trade_contract_size"]
    total = 0.0
    n_normal = 0
    n_triple = 0
    for _at, mult in rollovers(start_sec * 1000, end_sec * 1000, spec["swap_rollover3days"]):
        total += term * point * cs * mult
        if mult == 3:
            n_triple += 1
        else:
            n_normal += 1
    return float(total), n_normal, n_triple


# ==============================================================================
# CANDIDATE 2A: NEN022 (Fakey H4 — 2-Sided Inside-Bar False Breakout)
# ==============================================================================

def resample_h4_utc(times: np.ndarray, bid_4col: np.ndarray, min_bars: int = 120):
    """Causally aggregate M1 Bid bars into UTC 4-hour blocks (00, 04, 08, 12, 16, 20 UTC)."""
    buckets = times // 14400
    uniq, first_idx, counts = np.unique(buckets, return_index=True, return_counts=True)
    bars = []
    for b_id, start_i, cnt in zip(uniq, first_idx, counts):
        if cnt < min_bars:
            continue
        sl = bid_4col[start_i:start_i + cnt]
        bars.append({
            "bucket": int(b_id),
            "start_sec": int(b_id * 14400),
            "end_sec": int((b_id + 1) * 14400),
            "o": float(sl[0, 0]),
            "h": float(sl[:, 1].max()),
            "l": float(sl[:, 2].min()),
            "c": float(sl[-1, 3]),
            "m1_count": int(cnt),
        })
    return bars


def detect_nen022_signals(h4_bars: list[dict]):
    """Detect NEN022 Fakey patterns on consecutive completed UTC H4 bars (100% causal)."""
    signals = []
    for k in range(2, len(h4_bars)):
        mother, inside, fakey = h4_bars[k - 2], h4_bars[k - 1], h4_bars[k]
        # Require contiguous or single-weekend-bridged H4 sequence (<= 72h gap between adjacent bars)
        if fakey["start_sec"] - inside["end_sec"] > 72 * 3600 or inside["start_sec"] - mother["end_sec"] > 72 * 3600:
            continue
        if not (inside["h"] <= mother["h"] + 1e-10 and inside["l"] >= mother["l"] - 1e-10):
            continue
        # Bullish Fakey (BUY): breaks below inside.l, does not break above mother.h, closes back > inside.l and bullish
        if (fakey["l"] < inside["l"] - 1e-10
                and fakey["h"] <= mother["h"] + 1e-10
                and fakey["c"] > inside["l"] + 1e-10
                and fakey["c"] > fakey["o"] + 1e-10):
            signals.append({"side": 1, "signal_close_sec": fakey["end_sec"], "fakey_low": fakey["l"], "fakey_high": fakey["h"]})
        # Bearish Fakey (SELL): symmetric
        elif (fakey["h"] > inside["h"] + 1e-10
                and fakey["l"] >= mother["l"] - 1e-10
                and fakey["c"] < inside["h"] - 1e-10
                and fakey["c"] < fakey["o"] - 1e-10):
            signals.append({"side": -1, "signal_close_sec": fakey["end_sec"], "fakey_low": fakey["l"], "fakey_high": fakey["h"]})
    return signals


def evaluate_nen022_asset(asset: str, times: np.ndarray, quotes_by_tier: dict, spec: dict, *, native_ask: bool):
    is_gold = asset == "XAUUSD"
    cs = float(spec["trade_contract_size"])
    buffer = 0.50 if is_gold else 0.0002
    slip_tiers = (
        {"Base": 0.10, "Stress_Mid": 0.25, "Stress_High": 0.50}
        if is_gold else
        {"Base": 0.00002, "Stress_Mid": 0.000045, "Stress_High": 0.00007}  # 0.2, 0.45 (0.2+0.25), 0.7 pip/side => RT 0.4, 0.9, 1.4 pip
    )
    # Match exact FX Stress_05 convention: Base 0.2/side, Stress_Mid = +0.5 pip RT (=0.45/side), Stress_High = +1.0 pip RT (=0.7/side)
    h4 = resample_h4_utc(times, quotes_by_tier["Stress_Mid"][:, :4])
    raw_signals = detect_nen022_signals(h4)

    # 1) Stage-0 raw horizons (12h, 24h, 48h) + Fade at Stress_Mid
    q_mid = quotes_by_tier["Stress_Mid"]
    slip_mid = slip_tiers["Stress_Mid"]
    stage0_rows = {h: [] for h in (12, 24, 48)}
    stage0_entries = []
    for sig in raw_signals:
        entry_i = int(times.searchsorted(sig["signal_close_sec"], side="left"))
        if entry_i >= len(times) or times[entry_i] - sig["signal_close_sec"] > 900:
            continue
        side = sig["side"]
        bid0, ask0 = float(q_mid[entry_i, 0]), float(q_mid[entry_i, 4])
        entry_p = ask0 if side == 1 else bid0
        opp_in = bid0 if side == 1 else ask0
        entry_ts = int(times[entry_i])
        stage0_entries.append((entry_i, entry_ts, side))

        for hrs in (12, 24, 48):
            target_ts = entry_ts + hrs * 3600
            if target_ts >= STOP:
                continue
            exit_i = int(times.searchsorted(target_ts, side="left"))
            if exit_i >= len(times) or times[exit_i] >= STOP:
                continue
            exit_ts = int(times[exit_i])
            bid_e, ask_e = float(q_mid[exit_i, 0]), float(q_mid[exit_i, 4])
            out_p = bid_e if side == 1 else ask_e
            opp_out = ask_e if side == 1 else bid_e
            comm_rt = commission(asset, spec, entry_p) + commission(asset, spec, out_p)
            swap_s, _, _ = compute_swap_usd_per_lot(entry_ts, exit_ts, side, spec)
            swap_f, _, _ = compute_swap_usd_per_lot(entry_ts, exit_ts, -side, spec)
            net_usd = side * (out_p - entry_p) * cs - 2.0 * slip_mid * cs - comm_rt + swap_s
            fade_usd = -side * (opp_out - opp_in) * cs - 2.0 * slip_mid * cs - comm_rt + swap_f
            stage0_rows[hrs].append({
                "year": datetime.fromtimestamp(entry_ts, timezone.utc).year,
                "side": "BUY" if side == 1 else "SELL",
                "net_usd": net_usd, "fade_usd": fade_usd, "swap_usd": swap_s,
            })

    stage0_summary = {}
    for hrs, rows in stage0_rows.items():
        yrs, cls = cohorts(rows)
        stage0_summary[f"{hrs}h"] = {
            "n": len(rows),
            "net_usd": fsum(r["net_usd"] for r in rows),
            "fade_usd": fsum(r["fade_usd"] for r in rows),
            "swap_usd": fsum(r["swap_usd"] for r in rows),
            "net_mean_usd": mean(r["net_usd"] for r in rows) if rows else None,
            "clusters": {k: fsum(r["net_usd"] for r in v) for k, v in cls.items()},
            "years": {k: fsum(r["net_usd"] for r in v) for k, v in yrs.items()},
        }

    # Monte Carlo Random-Entry Null Test (24h horizon, Stress_Mid, exact swap)
    mc_null = None
    if stage0_rows[24]:
        rng = np.random.default_rng(SEED)
        # Precompute eligible H4 close indices inside 2018-2024 with valid 24h exit
        valid_h4_idx = []
        h4_buy_pnl, h4_sell_pnl = [], []
        for bar in h4:
            ei = int(times.searchsorted(bar["end_sec"], side="left"))
            if ei >= len(times) or times[ei] - bar["end_sec"] > 900:
                continue
            ets = int(times[ei])
            tts = ets + 24 * 3600
            if tts >= STOP:
                continue
            xi = int(times.searchsorted(tts, side="left"))
            if xi >= len(times) or times[xi] >= STOP:
                continue
            xts = int(times[xi])
            b0, a0 = float(q_mid[ei, 0]), float(q_mid[ei, 4])
            be, ae = float(q_mid[xi, 0]), float(q_mid[xi, 4])
            c_b = commission(asset, spec, a0) + commission(asset, spec, be)
            c_s = commission(asset, spec, b0) + commission(asset, spec, ae)
            sw_b, _, _ = compute_swap_usd_per_lot(ets, xts, 1, spec)
            sw_s, _, _ = compute_swap_usd_per_lot(ets, xts, -1, spec)
            h4_buy_pnl.append((be - a0) * cs - 2.0 * slip_mid * cs - c_b + sw_b)
            h4_sell_pnl.append((b0 - ae) * cs - 2.0 * slip_mid * cs - c_s + sw_s)
            valid_h4_idx.append(ei)

        buy_pool = np.array(h4_buy_pnl, dtype=np.float64)
        sell_pool = np.array(h4_sell_pnl, dtype=np.float64)
        n_buy = sum(1 for r in stage0_rows[24] if r["side"] == "BUY")
        n_sell = sum(1 for r in stage0_rows[24] if r["side"] == "SELL")
        totals = np.zeros(MC_DRAWS, dtype=np.float64)
        for d in range(MC_DRAWS):
            b_sum = float(buy_pool[rng.integers(0, len(buy_pool), size=n_buy)].sum()) if n_buy else 0.0
            s_sum = float(sell_pool[rng.integers(0, len(sell_pool), size=n_sell)].sum()) if n_sell else 0.0
            totals[d] = b_sum + s_sum
        obs_24 = fsum(r["net_usd"] for r in stage0_rows[24])
        mc_null = {
            "horizon": "24h", "n_buy": n_buy, "n_sell": n_sell, "draws": MC_DRAWS, "seed": SEED,
            "observed_net_usd": float(obs_24),
            "null_mean_usd": float(totals.mean()),
            "null_p95_usd": float(np.percentile(totals, 95)),
            "p_value": float((np.sum(totals >= obs_24) + 1) / (MC_DRAWS + 1)),
        }

    # 2) Full M1 path SL/TP replay across Swing (weekend hold ok) & Standard (Friday flat) and TP multiples
    sl_tp_results = {}
    for weekend_mode in ("Swing_WeekendHold", "Standard_FriFlat"):
        mode_map = {}
        for tier_name, slip in slip_tiers.items():
            q = quotes_by_tier[tier_name]
            rr_grid = (2.0,) if tier_name != "Stress_Mid" else (1.5, 2.0, 3.0)
            for rr in rr_grid:
                trades = []
                next_free_sec = 0
                for sig in raw_signals:
                    if sig["signal_close_sec"] < next_free_sec:
                        continue
                    ei = int(times.searchsorted(sig["signal_close_sec"], side="left"))
                    if ei >= len(times) or times[ei] - sig["signal_close_sec"] > 900:
                        continue
                    entry_ts = int(times[ei])
                    side = sig["side"]
                    b0, a0 = float(q[ei, 0]), float(q[ei, 4])
                    entry_p = a0 if side == 1 else b0
                    stop = (sig["fakey_low"] - buffer) if side == 1 else (sig["fakey_high"] + buffer)
                    risk_p = side * (entry_p - stop)
                    if risk_p <= 0:
                        continue
                    tp = entry_p + side * rr * risk_p

                    # Max exit horizon: 5 trading days (120h) or Friday 20:55 UTC (if Standard) or STOP - 60
                    max_ts = min(entry_ts + 5 * 86400, STOP - 60)
                    if weekend_mode == "Standard_FriFlat":
                        dt0 = datetime.fromtimestamp(entry_ts, timezone.utc)
                        days_to_fri = (4 - dt0.weekday()) % 7
                        fri_flat = int(datetime(dt0.year, dt0.month, dt0.day, 20, 55, tzinfo=timezone.utc).timestamp()) + days_to_fri * 86400
                        if fri_flat <= entry_ts:
                            fri_flat += 7 * 86400
                        max_ts = min(max_ts, fri_flat)

                    hi_i = int(times.searchsorted(max_ts, side="right")) - 1
                    if hi_i <= ei:
                        continue
                    liq = q[ei:hi_i + 1, :4] if side == 1 else q[ei:hi_i + 1, 4:8]
                    exit_rel = len(liq) - 1
                    exit_p = float(liq[-1, 3])
                    reason = "TIME_FLAT"
                    # Vectorized fast scan for SL or TP touch
                    if side == 1:
                        sl_hits = np.flatnonzero(liq[:, 2] <= stop + 1e-10)
                        tp_hits = np.flatnonzero(liq[:, 1] >= tp - 1e-10)
                    else:
                        sl_hits = np.flatnonzero(liq[:, 1] >= stop - 1e-10)
                        tp_hits = np.flatnonzero(liq[:, 2] <= tp + 1e-10)
                    first_sl = int(sl_hits[0]) if len(sl_hits) else None
                    first_tp = int(tp_hits[0]) if len(tp_hits) else None
                    if first_sl is not None and (first_tp is None or first_sl <= first_tp):
                        exit_rel = first_sl
                        op_j = float(liq[exit_rel, 0])
                        gap = exit_rel > 0 and side * (op_j - stop) <= 1e-10
                        exit_p = op_j if gap else stop
                        reason = "SL_GAP" if gap else "SL_TOUCH"
                    elif first_tp is not None:
                        exit_rel = first_tp
                        op_j = float(liq[exit_rel, 0])
                        gap = exit_rel > 0 and side * (op_j - tp) >= -1e-10
                        exit_p = op_j if gap else tp
                        reason = "TP_GAP" if gap else "TP_TOUCH"

                    exit_i = ei + exit_rel
                    exit_ts = int(times[exit_i])
                    next_free_sec = exit_ts + 60

                    gross_usd = side * (exit_p - entry_p) * cs
                    comm_rt = commission(asset, spec, entry_p) + commission(asset, spec, exit_p)
                    slip_usd = 2.0 * slip * cs
                    swap_usd, n_norm, n_trip = compute_swap_usd_per_lot(entry_ts, exit_ts, side, spec)
                    net_usd = gross_usd - comm_rt - slip_usd + swap_usd
                    risk_usd = risk_p * cs + comm_rt + slip_usd
                    trades.append({
                        "year": datetime.fromtimestamp(entry_ts, timezone.utc).year,
                        "entry": entry_ts, "exit": exit_ts, "side": "BUY" if side == 1 else "SELL",
                        "reason": reason, "gross_usd": gross_usd, "comm_slip_usd": comm_rt + slip_usd,
                        "swap_usd": swap_usd, "n_swap_normal": n_norm, "n_swap_triple": n_trip,
                        "net_usd": net_usd, "risk_usd": risk_usd, "net_R": net_usd / risk_usd,
                    })

                yrs, cls = cohorts(trades)
                wins = [t for t in trades if t["net_R"] > 0]
                top10 = fsum(sorted((t["net_R"] for t in wins), reverse=True)[:10])
                net_r = fsum(t["net_R"] for t in trades)
                cl_r = {k: fsum(t["net_R"] for t in v) for k, v in cls.items()}
                yr_r = {k: fsum(t["net_R"] for t in v) for k, v in yrs.items()}
                # Closed-trade equity DD in R
                eq_curve = np.cumsum([0.0] + [t["net_R"] for t in trades])
                closed_dd_r = float((np.maximum.accumulate(eq_curve) - eq_curve).max()) if len(trades) else 0.0
                survives = (
                    len(trades) >= 30
                    and min(cl_r.values()) > 0
                    and sum(v > 0 for v in yr_r.values()) >= 5
                    and net_r > top10
                )
                mode_map[f"{tier_name}_RR{rr:.1f}"] = {
                    "n": len(trades),
                    "win_rate": len(wins) / len(trades) if trades else None,
                    "net_R": net_r,
                    "net_R_annual": net_r / 7.0,
                    "top10_R": top10,
                    "closed_dd_R": closed_dd_r,
                    "gross_usd_sum": fsum(t["gross_usd"] for t in trades),
                    "comm_slip_usd_sum": fsum(t["comm_slip_usd"] for t in trades),
                    "swap_usd_sum": fsum(t["swap_usd"] for t in trades),
                    "net_usd_sum": fsum(t["net_usd"] for t in trades),
                    "clusters_R": cl_r,
                    "years_R": yr_r,
                    "exit_counts": dict(Counter(t["reason"] for t in trades)),
                    "survives": survives,
                }
        sl_tp_results[weekend_mode] = mode_map

    primary = sl_tp_results["Swing_WeekendHold"]["Stress_Mid_RR2.0"]
    mc_ok = mc_null is not None and mc_null["p_value"] < 0.05
    if primary["survives"] and mc_ok:
        verdict = (f"NEN022_{asset}_PROVISIONAL_NEEDS_NATIVE_TICK_BIDASK" if not native_ask
                   else f"NEN022_{asset}_SURVIVED_M1")
    elif primary["survives"]:
        verdict = f"NEN022_{asset}_SL_POSITIVE_FAILED_MC_NULL"
    else:
        verdict = f"NEN022_{asset}_FAILED_M1_CHECK"

    return {
        "asset": asset,
        "native_Ask": native_ask,
        "spread_mode": "NATIVE_TICK_BIDASK" if native_ask else "M1_BID_PROXY_SPREAD",
        "h4_bars_total": len(h4),
        "raw_signals_detected": len(raw_signals),
        "stage0_stress_mid": stage0_summary,
        "monte_carlo_null_24h": mc_null,
        "sl_tp": sl_tp_results,
        "verdict": verdict,
    }


# ==============================================================================
# CANDIDATE 2B: SEA003 (XAUUSD Turn-of-Month, Long-Only + FTMO Swap 3x Pre-Mortem)
# ==============================================================================

def evaluate_sea003_xauusd(times: np.ndarray, bid_4col: np.ndarray, spec: dict):
    """Exact M1 audit of SEA003 on XAUUSD with FTMO Swap 3x pre-mortem & Monte Carlo Null."""
    cs = float(spec["trade_contract_size"])
    tiers = {
        "Base": {"spread": 0.35, "slip_side": 0.10},
        "Stress_Mid": {"spread": 0.50, "slip_side": 0.25},
        "Stress_High": {"spread": 0.75, "slip_side": 0.50},
    }

    # Group valid Mon-Fri UTC trading days (>= 720 M1 bars to avoid thin holiday stubs)
    day_buckets = times // 86400
    uniq_days, first_i, counts = np.unique(day_buckets, return_index=True, return_counts=True)
    trading_days = []  # list of (date_obj, day_start_sec, start_idx, end_idx, o, h, l, c)
    for d_int, fi, cnt in zip(uniq_days, first_i, counts):
        d_obj = date(1970, 1, 1) + timedelta(days=int(d_int))
        if d_obj.weekday() >= 5 or cnt < 720:
            continue
        sl = bid_4col[fi:fi + cnt]
        trading_days.append({
            "date": d_obj,
            "day_sec": int(d_int * 86400),
            "fi": int(fi),
            "ei": int(fi + cnt),
            "o": float(sl[0, 0]),
            "h": float(sl[:, 1].max()),
            "l": float(sl[:, 2].min()),
            "c": float(sl[-1, 3]),
        })

    # Causal Wilder ATR(14) on completed D1 bars (atr[i] uses bars 0..i-1 strictly!)
    tr = np.zeros(len(trading_days), dtype=np.float64)
    for i, d in enumerate(trading_days):
        if i == 0:
            tr[i] = d["h"] - d["l"]
        else:
            pc = trading_days[i - 1]["c"]
            tr[i] = max(d["h"] - d["l"], abs(d["h"] - pc), abs(d["l"] - pc))
    atr_prior = np.full(len(trading_days), np.nan, dtype=np.float64)
    if len(trading_days) > 14:
        val = float(tr[:14].mean())
        atr_prior[14] = val
        for i in range(15, len(trading_days)):
            val = (val * 13.0 + tr[i - 1]) / 14.0
            atr_prior[i] = val

    # Map (year, month) -> list of indices into trading_days
    by_month = defaultdict(list)
    for idx, d in enumerate(trading_days):
        by_month[(d["date"].year, d["date"].month)].append(idx)
    months_sorted = sorted(by_month.keys())

    # Build monthly cycles: entry = 2nd-to-last trading day of month M; exit = 3rd trading day of M+1
    # Excludes 2024-12 because M+1 is 2025-01 (LOCKED HOLDOUT!)
    cycles = []
    for m_pos in range(len(months_sorted) - 1):
        m_cur = months_sorted[m_pos]
        m_nxt = months_sorted[m_pos + 1]
        if len(by_month[m_cur]) < 2 or len(by_month[m_nxt]) < 3:
            continue
        ent_day_idx = by_month[m_cur][-2]
        ext_day_idx = by_month[m_nxt][2]
        assert trading_days[ext_day_idx]["date"] < date(2025, 1, 1)
        cycles.append((m_cur, ent_day_idx, ext_day_idx))

    def find_bar_at(day_rec, hour, minute):
        target = day_rec["day_sec"] + hour * 3600 + minute * 60
        sub_t = times[day_rec["fi"]:day_rec["ei"]]
        j = int(sub_t.searchsorted(target, side="left"))
        if j >= len(sub_t):
            j = len(sub_t) - 1
        return day_rec["fi"] + j

    def run_variant(entry_h, entry_m, spread, slip_side, *, sl_atr_mult=None):
        trades = []
        for m_cur, ent_d, ext_d in cycles:
            ei = find_bar_at(trading_days[ent_d], entry_h, entry_m)
            xi_target = find_bar_at(trading_days[ext_d], 20, 55)
            if xi_target <= ei:
                continue
            entry_ts = int(times[ei])
            entry_ask = float(bid_4col[ei, 0]) + spread  # Long buys at Ask = Bid + spread
            sl_price = None
            atr_val = float(atr_prior[ent_d]) if np.isfinite(atr_prior[ent_d]) else None
            if sl_atr_mult is not None:
                if atr_val is None or atr_val <= 0:
                    continue
                sl_price = entry_ask - sl_atr_mult * atr_val

            path_bid = bid_4col[ei:xi_target + 1]
            exit_rel = len(path_bid) - 1
            exit_bid = float(path_bid[-1, 3])
            reason = "TIME_EXIT"
            if sl_price is not None:
                hits = np.flatnonzero(path_bid[:, 2] <= sl_price + 1e-10)
                if len(hits):
                    exit_rel = int(hits[0])
                    op_j = float(path_bid[exit_rel, 0])
                    gap = exit_rel > 0 and op_j <= sl_price + 1e-10
                    exit_bid = op_j if gap else sl_price
                    reason = "SL_GAP" if gap else "SL_TOUCH"

            exit_i = ei + exit_rel
            exit_ts = int(times[exit_i])
            assert START <= entry_ts < exit_ts < STOP

            # Intra-trade worst adverse excursion (Bid low vs entry Ask)
            min_bid = float(path_bid[:exit_rel + 1, 2].min())
            mae_oz = min_bid - entry_ask
            mae_pct = 100.0 * mae_oz / entry_ask

            gross_price_usd = (exit_bid - float(bid_4col[ei, 0])) * cs  # pure Bid-to-Bid price change
            spread_usd = spread * cs
            slip_usd = 2.0 * slip_side * cs
            comm_usd = commission("XAUUSD", spec, entry_ask) + commission("XAUUSD", spec, exit_bid)
            swap_usd, n_norm, n_trip = compute_swap_usd_per_lot(entry_ts, exit_ts, 1, spec)
            net_usd = (exit_bid - entry_ask) * cs - slip_usd - comm_usd + swap_usd
            risk_usd = (sl_atr_mult * atr_val * cs + slip_usd + comm_usd) if sl_price is not None else (entry_ask * 0.02 * cs)
            trades.append({
                "month": f"{m_cur[0]}-{m_cur[1]:02d}", "year": m_cur[0],
                "entry_date": trading_days[ent_d]["date"].isoformat(),
                "exit_date": trading_days[ext_d]["date"].isoformat(),
                "entry_ask": entry_ask, "exit_bid": exit_bid, "reason": reason,
                "gross_price_usd_lot": gross_price_usd,
                "spread_slip_comm_usd_lot": spread_usd + slip_usd + comm_usd,
                "swap_usd_lot": swap_usd, "swap_nights_1x": n_norm, "swap_nights_3x": n_trip,
                "net_usd_lot": net_usd, "mae_oz": mae_oz, "mae_pct": mae_pct,
                "net_R": net_usd / risk_usd,
            })

        yrs, cls = cohorts(trades)
        wins = [t for t in trades if t["net_usd_lot"] > 0]
        cum_usd = np.cumsum([0.0] + [t["net_usd_lot"] for t in trades])
        dd_usd = float((np.maximum.accumulate(cum_usd) - cum_usd).max()) if trades else 0.0
        cl_net = {k: fsum(t["net_usd_lot"] for t in v) for k, v in cls.items()}
        yr_net = {k: fsum(t["net_usd_lot"] for t in v) for k, v in yrs.items()}
        net_sum = fsum(t["net_usd_lot"] for t in trades)
        gross_sum = fsum(t["gross_price_usd_lot"] for t in trades)
        swap_sum = fsum(t["swap_usd_lot"] for t in trades)
        exec_sum = fsum(t["spread_slip_comm_usd_lot"] for t in trades)
        return {
            "n": len(trades),
            "win_rate": len(wins) / len(trades) if trades else None,
            "gross_price_usd_lot_sum": gross_sum,
            "exec_cost_usd_lot_sum": exec_sum,
            "ftmo_swap_usd_lot_sum": swap_sum,
            "net_usd_lot_sum": net_sum,
            "mean_swap_per_trade_usd_lot": swap_sum / len(trades) if trades else None,
            "swap_drag_pct_of_gross": (100.0 * abs(swap_sum) / gross_sum) if gross_sum > 0 else None,
            "total_wed_3x_rollovers": sum(t["swap_nights_3x"] for t in trades),
            "worst_single_trade_mae_pct": min((t["mae_pct"] for t in trades), default=None),
            "closed_dd_usd_lot": dd_usd,
            "net_R_sum": fsum(t["net_R"] for t in trades),
            "clusters_usd_lot": cl_net,
            "years_usd_lot": yr_net,
            "exit_counts": dict(Counter(t["reason"] for t in trades)),
            "both_clusters_positive": min(cl_net.values()) > 0 if cl_net else False,
            "years_positive_count": sum(v > 0 for v in yr_net.values()),
        }

    variants = {}
    for tname, cfg in tiers.items():
        variants[f"Unhedged_NoSL_{tname}"] = run_variant(1, 0, cfg["spread"], cfg["slip_side"], sl_atr_mult=None)
        variants[f"ATR14_SL2x_{tname}"] = run_variant(1, 0, cfg["spread"], cfg["slip_side"], sl_atr_mult=2.0)

    # Entry hour sensitivity at Stress_Mid (00:05 UTC, 01:00 UTC, 08:00 UTC)
    hour_sens = {}
    mid_cfg = tiers["Stress_Mid"]
    for h, m in ((0, 5), (1, 0), (8, 0)):
        hour_sens[f"{h:02d}:{m:02d}_UTC"] = run_variant(h, m, mid_cfg["spread"], mid_cfg["slip_side"], sl_atr_mult=None)

    # Mandatory Monte Carlo Random-Entry Null Test (N=1000): random entry day each month, exact 4-step (=5 session) hold!
    rng = np.random.default_rng(SEED)
    month_pools_net = []
    month_pools_gross = []
    for m_cur, ent_d, ext_d in cycles:
        hold_steps = ext_d - ent_d
        m_days = by_month[m_cur]
        p_net, p_gross = [], []
        for cand_d in m_days:
            out_d = cand_d + hold_steps
            if out_d >= len(trading_days) or trading_days[out_d]["date"] >= date(2025, 1, 1):
                continue
            ei = find_bar_at(trading_days[cand_d], 1, 0)
            xi = find_bar_at(trading_days[out_d], 20, 55)
            if xi <= ei:
                continue
            ets, xts = int(times[ei]), int(times[xi])
            e_ask = float(bid_4col[ei, 0]) + mid_cfg["spread"]
            x_bid = float(bid_4col[xi, 3])
            gross = (x_bid - float(bid_4col[ei, 0])) * cs
            comm = commission("XAUUSD", spec, e_ask) + commission("XAUUSD", spec, x_bid)
            slip = 2.0 * mid_cfg["slip_side"] * cs
            sw, _, _ = compute_swap_usd_per_lot(ets, xts, 1, spec)
            p_gross.append(gross)
            p_net.append((x_bid - e_ask) * cs - slip - comm + sw)
        if p_net:
            month_pools_net.append(np.array(p_net, dtype=np.float64))
            month_pools_gross.append(np.array(p_gross, dtype=np.float64))

    null_net = np.zeros(MC_DRAWS, dtype=np.float64)
    null_gross = np.zeros(MC_DRAWS, dtype=np.float64)
    for pn, pg in zip(month_pools_net, month_pools_gross):
        idx = rng.integers(0, len(pn), size=MC_DRAWS)
        null_net += pn[idx]
        null_gross += pg[idx]

    obs_unhedged_mid = variants["Unhedged_NoSL_Stress_Mid"]
    obs_net = obs_unhedged_mid["net_usd_lot_sum"]
    obs_gross = obs_unhedged_mid["gross_price_usd_lot_sum"]
    mc_null = {
        "months_tested": len(month_pools_net),
        "draws": MC_DRAWS,
        "seed": SEED,
        "observed_gross_usd_lot": float(obs_gross),
        "null_gross_mean_usd_lot": float(null_gross.mean()),
        "null_gross_p95_usd_lot": float(np.percentile(null_gross, 95)),
        "gross_p_value": float((np.sum(null_gross >= obs_gross) + 1) / (MC_DRAWS + 1)),
        "observed_net_after_ftmo_swap_usd_lot": float(obs_net),
        "null_net_mean_usd_lot": float(null_net.mean()),
        "null_net_p95_usd_lot": float(np.percentile(null_net, 95)),
        "net_p_value": float((np.sum(null_net >= obs_net) + 1) / (MC_DRAWS + 1)),
    }

    atr_mid = variants["ATR14_SL2x_Stress_Mid"]
    survives_economics = (
        obs_unhedged_mid["net_usd_lot_sum"] > 0
        and obs_unhedged_mid["both_clusters_positive"]
        and atr_mid["net_usd_lot_sum"] > 0
        and atr_mid["both_clusters_positive"]
        and mc_null["net_p_value"] < 0.05
    )
    if survives_economics:
        verdict = "SEA003_PROVISIONAL_NEEDS_NATIVE_TICK_BIDASK"
    elif obs_unhedged_mid["gross_price_usd_lot_sum"] > 0 and obs_unhedged_mid["net_usd_lot_sum"] <= 0:
        verdict = "SEA003_KILLED_BY_FTMO_SWAP_AND_COSTS"
    elif mc_null["net_p_value"] >= 0.05:
        verdict = "SEA003_FAILED_RANDOM_ENTRY_NULL_DRIFT_ILLUSION"
    else:
        verdict = "SEA003_FAILED_M1_CHECK"

    return {
        "candidate": "SEA003_XAUUSD_TurnOfMonth",
        "native_Ask": False,
        "spread_mode": "M1_BID_PROXY_SPREAD",
        "ftmo_swap_long_pts_per_night": spec["swap_long"],
        "ftmo_triple_swap_weekday": spec["swap_rollover3days"],
        "cycles_2018_2024_excl_dec2024_holdout": len(cycles),
        "variants": variants,
        "entry_hour_sensitivity_stress_mid": hour_sens,
        "monte_carlo_random_entry_null_stress_mid": mc_null,
        "verdict": verdict,
    }


def run_track2(jobs_root: Path, pass13_job: Path, output_dir: Path):
    if sha(clock.ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load all 3 local M1 datasets
    xau_times, xau_bid, _ = load_xauusd_m1_bid(pass13_job / "data" / "xauusd-m1")
    eur_times, eur_q, _ = load_fx_m1_bidask(pass13_job / "data" / "eurusd-m1", "EURUSD")
    gbp_times, gbp_q, _ = load_fx_m1_bidask(jobs_root / "pass11-gbpusd-m1-20261120" / "development-m1", "GBPUSD")

    # Candidate 2A: NEN022 on EURUSD (native Bid/Ask), GBPUSD (native Bid/Ask), XAUUSD (Bid + proxy spread)
    nen022_out = {
        "EURUSD": evaluate_nen022_asset(
            "EURUSD", eur_times, {"Base": eur_q, "Stress_Mid": eur_q, "Stress_High": eur_q},
            swing_specs["EURUSD"], native_ask=True,
        ),
        "GBPUSD": evaluate_nen022_asset(
            "GBPUSD", gbp_times, {"Base": gbp_q, "Stress_Mid": gbp_q, "Stress_High": gbp_q},
            swing_specs["GBPUSD"], native_ask=True,
        ),
        "XAUUSD": evaluate_nen022_asset(
            "XAUUSD", xau_times, {
                "Base": make_quotes_from_bid(xau_bid, 0.35),
                "Stress_Mid": make_quotes_from_bid(xau_bid, 0.50),
                "Stress_High": make_quotes_from_bid(xau_bid, 0.75),
            },
            swing_specs["XAUUSD"], native_ask=False,
        ),
    }
    for sym, res in nen022_out.items():
        print(f"TRACK2_NEN022_{sym}_VERDICT={res['verdict']}", flush=True)

    # Candidate 2B: SEA003 on XAUUSD
    sea003_out = evaluate_sea003_xauusd(xau_times, xau_bid, swing_specs["XAUUSD"])
    print(f"TRACK2_SEA003_VERDICT={sea003_out['verdict']}", flush=True)

    result = {
        "track": "Track2_CleanRoom_Intel_Reproduction",
        "protocol_commit": PROTOCOL,
        "air_gap_compliant": True,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "spec": bindings,
        "NEN022": nen022_out,
        "SEA003": sea003_out,
    }
    write(output_dir / "track2-intel-cleanroom-result.json", result)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs"))
    parser.add_argument("--pass13-job", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_track2(args.jobs, args.pass13_job, args.output)
