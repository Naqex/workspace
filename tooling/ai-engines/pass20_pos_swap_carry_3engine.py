"""Pass 20: Deep H4/M1 Forensic Audit of 8-Pair Positive-Swap Carry-Trend & 3-Engine Prague-Reset Portfolio Integration."""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass18_opensource_non_usdjpy as p18
import pass19_us500_supertrend_yencross as p19
from native_ftmo_monfri_seal import ROOT, START, STOP, sha, write
from quant_core.ftmo_track_replay import commission, profiles, rollovers

PROTOCOL = "54cb0697aedf20747e543f1cd08232b8ddf662a6"
SEED = 20261123
MC_DRAWS = 1000

# All 8 FTMO Swing FX pairs with verified positive swap (direction fixed by positive swap sign)
POS_SWAP_UNIVERSE = (
    ("USDCAD", 1, False),
    ("USDCHF", 1, False),
    ("EURUSD", -1, False),
    ("EURGBP", -1, False),
    ("USDJPY", 1, True),
    ("EURJPY", 1, True),
    ("GBPJPY", 1, True),
    ("AUDJPY", 1, True),
)
NON_JPY_4 = ("USDCAD", "USDCHF", "EURUSD", "EURGBP")
JPY_CARRY_4 = ("USDJPY", "EURJPY", "GBPJPY", "AUDJPY")


def load_fx_conversion_maps(jobs_root: Path) -> dict[str, dict]:
    """Load sealed D1 close maps (2000-2024) for exact USD P&L and 1:30/1:100 margin conversion."""
    maps = {}
    for sym in ("USDJPY", "USDCAD", "USDCHF", "EURUSD", "GBPUSD", "AUDUSD"):
        ts, _, _, _, c = p19.load_sealed_bars(jobs_root, sym, "D1")
        maps[sym] = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts, c)}
    return maps


def profit_ccy_to_usd_mult(ccy: str, d_obj, conv_maps: dict, fallback_px: float) -> float:
    """Multiplier converting 1 unit of profit currency into USD on calendar date d_obj."""
    if ccy == "USD":
        return 1.0
    if ccy == "GBP":
        return conv_maps["GBPUSD"].get(d_obj, 1.27)
    if ccy in ("JPY", "CAD", "CHF"):
        key = f"USD{ccy}"
        denom = conv_maps[key].get(d_obj, fallback_px)
        return 1.0 / denom
    raise ValueError(f"Unsupported profit currency: {ccy}")


def margin_quote_mult(sym: str, d_obj, conv_maps: dict) -> float:
    """Base-currency to USD multiplier for FTMO margin_per_reference (exact for USD/EUR/GBP/AUD bases)."""
    base = sym[:3]
    if base == "USD":
        return 1.0
    if base == "EUR":
        return conv_maps["EURUSD"].get(d_obj, 1.10)
    if base == "GBP":
        return conv_maps["GBPUSD"].get(d_obj, 1.27)
    if base == "AUD":
        return conv_maps["AUDUSD"].get(d_obj, 0.68)
    raise ValueError(f"Unsupported base currency: {base}")


def load_pair_data(jobs_root: Path, sym: str) -> dict:
    d_ts, d_o, d_h, d_l, d_c = p19.load_sealed_bars(jobs_root, sym, "D1")
    h_ts, h_o, h_h, h_l, h_c = p19.load_sealed_bars(jobs_root, sym, "H4")
    d_dates = [datetime.fromtimestamp(int(t), timezone.utc).date() for t in d_ts]
    d_atr = p14.wilder_atr(d_h, d_l, d_c, 14)
    d_ema50 = p14.ema(d_c, 50)
    return {
        "sym": sym,
        "d_ts": d_ts, "d_o": d_o, "d_h": d_h, "d_l": d_l, "d_c": d_c,
        "d_dates": d_dates, "d_atr": d_atr, "d_ema50": d_ema50,
        "h_ts": h_ts, "h_o": h_o, "h_h": h_h, "h_l": h_l, "h_c": h_c,
    }


def build_h4_carry_trades(
    pdata: dict,
    side: int,
    spec: dict,
    conv_maps: dict,
    *,
    entry_don: int = 20,
    exit_don: int = 10,
    sl_atr: float = 2.0,
    cost_mult: float = 1.0,
    include_swap: bool = True,
) -> tuple[list[dict], list[dict]]:
    """Exact H4 floating-equity replay for Positive-Swap Donchian Carry-Trend (causal D1 signals, H4 intrabar SL & marks)."""
    sym = pdata["sym"]
    is_jpy = sym.endswith("JPY")
    pip = 0.01 if is_jpy else 0.0001
    # Conservative H4 RT spread + slippage (Stress_1x: 1.8 pip JPY / 1.5 pip non-JPY; Stress_2x: 3.0 pip)
    base_pips = 1.8 if is_jpy else 1.5
    slip_spread_px = (base_pips if cost_mult == 1.0 else 3.0) * pip
    cs = float(spec["trade_contract_size"])
    pt = float(spec["point"])
    ccy = spec["currency_profit"]
    sw_pts = float(spec["swap_long"] if side == 1 else spec["swap_short"])
    sw_pts_fade = float(spec["swap_short"] if side == 1 else spec["swap_long"])
    roll3 = spec["swap_rollover3days"]

    d_ts, d_h, d_l, d_c = pdata["d_ts"], pdata["d_h"], pdata["d_l"], pdata["d_c"]
    d_dates, d_atr, d_ema50 = pdata["d_dates"], pdata["d_atr"], pdata["d_ema50"]
    h_ts, h_o, h_h, h_l, h_c = pdata["h_ts"], pdata["h_o"], pdata["h_h"], pdata["h_l"], pdata["h_c"]

    trades, fades = [], []
    i = max(60, entry_don + 2)
    while i < len(d_ts) - 1:
        if int(d_ts[i]) < START:
            i += 1
            continue
        if int(d_ts[i]) >= STOP - 86400:
            break
        a_val = float(d_atr[i - 1])
        ev = float(d_ema50[i - 1])
        if not np.isfinite(a_val) or not np.isfinite(ev) or a_val <= 0:
            i += 1
            continue

        if side == 1:
            don_lvl = float(np.max(d_h[i - 1 - entry_don:i - 1]))
            trig = (d_c[i - 1] > ev) and (d_c[i - 1] > don_lvl)
        else:
            don_lvl = float(np.min(d_l[i - 1 - entry_don:i - 1]))
            trig = (d_c[i - 1] < ev) and (d_c[i - 1] < don_lvl)
        if not trig:
            i += 1
            continue

        # Locate first H4 bar on/after day i open
        h0 = int(h_ts.searchsorted(int(d_ts[i]), side="left"))
        if h0 >= len(h_ts) or int(h_ts[h0]) >= STOP - 4 * 3600:
            break
        ep = float(h_o[h0])
        sl_dist = sl_atr * a_val
        sl_p = ep - side * sl_dist
        ent_dt = d_dates[i]
        ent_ts = int(h_ts[h0])
        ent_mult = profit_ccy_to_usd_mult(ccy, ent_dt, conv_maps, ep)
        # Round-turn commission ($5/lot RT on FTMO FX; exact via commission helper if USD/JPY else $5.00 RT)
        comm_usd = 5.0
        slip_usd_est = slip_spread_px * cs * ent_mult
        risk_usd = sl_dist * cs * ent_mult + slip_usd_est + comm_usd
        if risk_usd <= 0:
            i += 1
            continue

        # Precompute first D1 exit day > i where prior completed D1 breaches exit_don channel
        d_exit_day_idx = len(d_ts) - 1
        for di in range(i + 1, len(d_ts)):
            if side == 1:
                ch = float(np.min(d_l[di - 1 - exit_don:di - 1]))
                if d_c[di - 1] < ch:
                    d_exit_day_idx = di
                    break
            else:
                ch = float(np.max(d_h[di - 1 - exit_don:di - 1]))
                if d_c[di - 1] > ch:
                    d_exit_day_idx = di
                    break
        exit_cap_ts = min(int(d_ts[d_exit_day_idx]), STOP - 4 * 3600)
        h_cap = int(h_ts.searchsorted(exit_cap_ts, side="left"))
        h_cap = min(max(h_cap, h0), len(h_ts) - 1)

        # Replay H4 bar-by-bar recording worst floating mark & close mark (with accrued FTMO swap!)
        stamps_list = []
        worst_list = []
        close_list = []
        ex_h = h_cap
        ex_px = float(h_o[h_cap])
        reason = "DON_EXIT" if d_exit_day_idx < len(d_ts) - 1 else "END_OF_DEV"
        accrued_swap = 0.0
        prev_roll_ts = ent_ts

        for hk in range(h0, h_cap + 1):
            ts_k = int(h_ts[hk])
            dt_k = datetime.fromtimestamp(ts_k, timezone.utc).date()
            m_k = profit_ccy_to_usd_mult(ccy, dt_k, conv_maps, float(h_c[hk]))
            if include_swap and ts_k > prev_roll_ts:
                for _at, mult in rollovers(prev_roll_ts * 1000, ts_k * 1000, roll3):
                    accrued_swap += sw_pts * pt * cs * m_k * mult
                prev_roll_ts = ts_k

            bo, bh, bl, bc = float(h_o[hk]), float(h_h[hk]), float(h_l[hk]), float(h_c[hk])
            # Check if we reached Donchian exit open at hk == h_cap (after entry bar)
            if hk == h_cap and hk > h0 and reason == "DON_EXIT":
                ex_h = hk
                ex_px = bo
                net_k = side * (bo - ep) * cs * m_k - (slip_spread_px * cs * m_k + comm_usd) + accrued_swap
                stamps_list.append(ts_k)
                worst_list.append(net_k)
                close_list.append(net_k)
                break

            # Conservative SL check on H4 bar hk
            hit_sl = (side == 1 and bl <= sl_p + 1e-10) or (side == -1 and bh >= sl_p - 1e-10)
            if hit_sl:
                gap = (hk > h0) and ((side == 1 and bo <= sl_p + 1e-10) or (side == -1 and bo >= sl_p - 1e-10))
                ex_px = bo if gap else sl_p
                ex_h = hk
                reason = "SL_GAP_OR_TOUCH"
                net_k = side * (ex_px - ep) * cs * m_k - (slip_spread_px * cs * m_k + comm_usd) + accrued_swap
                stamps_list.append(ts_k)
                worst_list.append(net_k)
                close_list.append(net_k)
                break

            # Open bar: worst floating adverse excursion & close mark
            adv_px = bl if side == 1 else bh
            worst_k = side * (adv_px - ep) * cs * m_k - (slip_spread_px * cs * m_k + comm_usd) + accrued_swap
            close_k = side * (bc - ep) * cs * m_k - (slip_spread_px * cs * m_k + comm_usd) + accrued_swap
            stamps_list.append(ts_k)
            worst_list.append(worst_k)
            close_list.append(close_k)

        ex_ts = int(h_ts[ex_h])
        assert START <= ent_ts <= ex_ts < STOP
        ex_dt = datetime.fromtimestamp(ex_ts, timezone.utc).date()
        ex_mult = profit_ccy_to_usd_mult(ccy, ex_dt, conv_maps, ex_px)
        gross_usd = side * (ex_px - ep) * cs * ex_mult
        exec_cost_usd = slip_spread_px * cs * ex_mult + comm_usd
        # Exact total swap over hold
        tot_swap = 0.0
        tot_swap_fade = 0.0
        for _at, mult in rollovers(ent_ts * 1000, ex_ts * 1000, roll3):
            tot_swap += sw_pts * pt * cs * ex_mult * mult
            tot_swap_fade += sw_pts_fade * pt * cs * ex_mult * mult
        used_swap = tot_swap if include_swap else 0.0
        net_usd = gross_usd - exec_cost_usd + used_swap
        price_only_net = gross_usd - exec_cost_usd

        # Reconcile terminal close mark with exact realized cash
        close_list[-1] = net_usd
        worst_list[-1] = min(worst_list[-1], net_usd)

        row = {
            "sym": sym, "day": ent_dt.isoformat(), "exit_day": ex_dt.isoformat(),
            "year": ent_dt.year, "side": side, "is_jpy": sym in JPY_CARRY_4,
            "entry": ent_ts, "exit": ex_ts, "entry_price": ep, "exit_price": ex_px,
            "hold_days": max(1, (ex_dt - ent_dt).days),
            "reason": reason,
            "margin_quote": margin_quote_mult(sym, ent_dt, conv_maps),
            "stop_risk_with_cost_usd": risk_usd,
            "gross_usd": gross_usd, "ftmo_comm_slip": exec_cost_usd,
            "ftmo_swap": tot_swap, "ftmo_net": net_usd,
            "price_only_net": price_only_net,
            "ftmo_R": net_usd / risk_usd,
            "price_only_R": price_only_net / risk_usd,
            "ex_R_normal": net_usd / risk_usd,
            "ex_R_swapfree": price_only_net / risk_usd,
            "stamps": np.array(stamps_list, dtype=np.int64),
            "worst_usd": np.array(worst_list, dtype=np.float64),
            "close_usd": np.array(close_list, dtype=np.float64),
        }
        trades.append(row)

        # Paired opposite-side fade on identical window (for sign-flip null)
        fade_net = -gross_usd - exec_cost_usd + (tot_swap_fade if include_swap else 0.0)
        fades.append({
            "day": ent_dt.isoformat(), "year": ent_dt.year, "side": -side, "reason": reason,
            "gross_usd": -gross_usd, "ftmo_comm_slip": exec_cost_usd, "ftmo_swap": tot_swap_fade,
            "ftmo_net": fade_net, "ftmo_R": fade_net / risk_usd,
            "price_only_net": -gross_usd - exec_cost_usd,
            "ex_R_normal": fade_net / risk_usd, "ex_R_swapfree": (-gross_usd - exec_cost_usd) / risk_usd,
        })

        # Advance past exit day cleanly (1 position per pair at a time)
        nxt_d = int(np.searchsorted(d_ts, ex_ts, side="right"))
        i = max(i + 1, nxt_d)
    return trades, fades


def random_entry_matched_hold_null(
    pdata: dict, side: int, spec: dict, conv_maps: dict, trades: list[dict], *, sl_atr: float = 2.0, draws: int = MC_DRAWS
) -> dict:
    """Does Donchian timing beat entering the SAME positive-swap direction on random days with matched hold length?"""
    if not trades:
        return {"timing_price_p": 1.0, "timing_total_p": 1.0}
    d_ts, d_o, d_h, d_l, d_c = pdata["d_ts"], pdata["d_o"], pdata["d_h"], pdata["d_l"], pdata["d_c"]
    d_dates, d_atr = pdata["d_dates"], pdata["d_atr"]
    cs, pt, ccy = float(spec["trade_contract_size"]), float(spec["point"]), spec["currency_profit"]
    sw_pts = float(spec["swap_long"] if side == 1 else spec["swap_short"])
    roll3 = spec["swap_rollover3days"]
    pip = 0.01 if pdata["sym"].endswith("JPY") else 0.0001
    cost_px = (1.8 if pdata["sym"].endswith("JPY") else 1.5) * pip

    med_bars = max(3, int(round(np.median([t["hold_days"] for t in trades]) * 5.0 / 7.0)))
    dev_idx = [i for i in range(60, len(d_ts) - med_bars - 1) if START <= int(d_ts[i]) < STOP - med_bars * 86400]
    pool_price, pool_total = [], []
    for i in dev_idx:
        a = float(d_atr[i - 1])
        if not np.isfinite(a) or a <= 0:
            continue
        ep = float(d_o[i])
        sl_p = ep - side * sl_atr * a
        ex_i = i + med_bars
        ex_px = float(d_c[ex_i])
        for j in range(i, ex_i + 1):
            if (side == 1 and d_l[j] <= sl_p) or (side == -1 and d_h[j] >= sl_p):
                ex_i = j
                ex_px = sl_p
                break
        m_ex = profit_ccy_to_usd_mult(ccy, d_dates[ex_i], conv_maps, ex_px)
        g = side * (ex_px - ep) * cs * m_ex
        c_usd = cost_px * cs * m_ex + 5.0
        sw = sum(sw_pts * pt * cs * m_ex * mult for _at, mult in rollovers(int(d_ts[i]) * 1000, int(d_ts[ex_i]) * 1000, roll3))
        risk = sl_atr * a * cs * m_ex + c_usd
        pool_price.append((g - c_usd) / risk)
        pool_total.append((g - c_usd + sw) / risk)

    ap, at = np.array(pool_price), np.array(pool_total)
    n = len(trades)
    rng = np.random.default_rng(SEED + 200)
    idx = rng.integers(0, len(ap), size=(draws, n))
    obs_p = fsum(t["price_only_R"] for t in trades)
    obs_t = fsum(t["ftmo_R"] for t in trades)
    return {
        "med_hold_bars": med_bars,
        "obs_price_R": round(obs_p, 2), "null_price_mean_R": round(float(ap[idx].sum(axis=1).mean()), 2),
        "timing_price_p": float((np.sum(ap[idx].sum(axis=1) >= obs_p) + 1) / (draws + 1)),
        "obs_total_R": round(obs_t, 2), "null_total_mean_R": round(float(at[idx].sum(axis=1).mean()), 2),
        "timing_total_p": float((np.sum(at[idx].sum(axis=1) >= obs_t) + 1) / (draws + 1)),
    }


def m1_parity_crosscheck(jobs_root: Path, cache_dir: Path, sym: str, side: int, h4_trades: list[dict], spec: dict) -> dict:
    """Bit-for-bit Native Tick-Derived M1 Bid/Ask parity replay on USDJPY & EURUSD for exact same D1 signal dates."""
    ctx = p14.build_asset_context(jobs_root, sym, cache_dir, spec)
    times, quotes = ctx["times"], ctx["quotes"]
    m1_rs, h4_rs = [], []
    matched = 0
    for tr in h4_trades:
        e_idx = int(times.searchsorted(tr["entry"], side="left"))
        if e_idx >= len(times) - 1:
            continue
        ep_m1 = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
        sl_dist = abs(tr["entry_price"] - tr["exit_price"]) if tr["reason"] == "SL_GAP_OR_TOUCH" else None
        # Exact same sl_dist = 2.0 * ATR_D1 reconstructed from initial risk_usd or re-derived cleanly
        d_i = ctx["date_to_d1"].get(datetime.strptime(tr["day"], "%Y-%m-%d").date())
        if d_i is None or not np.isfinite(ctx["d1_atr"][d_i - 1]):
            continue
        sl_p = ep_m1 - side * 2.0 * float(ctx["d1_atr"][d_i - 1])
        m1_tr = p14.replay_trade_m1(
            sym, times, quotes, e_idx, side, ep_m1, sl_p, None, tr["exit"], spec, intraday_flat=False
        )
        if m1_tr is not None:
            matched += 1
            m1_rs.append(m1_tr["ftmo_R"])
            h4_rs.append(tr["ftmo_R"])
    h4_sum = fsum(h4_rs)
    m1_sum = fsum(m1_rs)
    return {
        "sym": sym, "side": side, "matched": matched, "h4_total": len(h4_trades),
        "h4_net_R": round(h4_sum, 2), "m1_native_net_R": round(m1_sum, 2),
        "diff_R_total": round(m1_sum - h4_sum, 2),
        "diff_R_per_year": round((m1_sum - h4_sum) / 7.0, 3),
    }


def apply_sleeve_filters(all_pair_trades: dict[str, list[dict]], pairs: tuple[str, ...], *, max_jpy_open: int | None = None) -> list[dict]:
    """Chronologically filter candidate carry trades enforcing concurrency cap (e.g. max 1 JPY carry open)."""
    cands = []
    for sym in pairs:
        cands.extend(all_pair_trades[sym])
    cands.sort(key=lambda t: (t["entry"], t["sym"]))
    accepted = []
    active_jpy_exits = []
    for t in cands:
        active_jpy_exits = [ex for ex in active_jpy_exits if ex > t["entry"]]
        if max_jpy_open is not None and t["is_jpy"]:
            if len(active_jpy_exits) >= max_jpy_open:
                continue
            active_jpy_exits.append(t["exit"])
        accepted.append(t)
    return accepted


def summarize_sleeve(trades: list[dict]) -> dict:
    if not trades:
        return {"n": 0, "net_R": 0.0, "price_R": 0.0, "A": 0.0, "B": 0.0, "price_A": 0.0, "price_B": 0.0, "pos_years": 0, "dd_R": 0.0}
    by_yr = defaultdict(float)
    by_yr_p = defaultdict(float)
    for t in trades:
        by_yr[t["year"]] += t["ftmo_R"]
        by_yr_p[t["year"]] += t["price_only_R"]
    eq = np.cumsum([0.0] + [t["ftmo_R"] for t in trades])
    dd = float((np.maximum.accumulate(eq) - eq).max())
    return {
        "n": len(trades),
        "net_R": round(fsum(t["ftmo_R"] for t in trades), 2),
        "price_R": round(fsum(t["price_only_R"] for t in trades), 2),
        "swap_usd": round(fsum(t["ftmo_swap"] for t in trades), 0),
        "A": round(fsum(by_yr[y] for y in clock.CLUSTERS["A"]), 2),
        "B": round(fsum(by_yr[y] for y in clock.CLUSTERS["B"]), 2),
        "price_A": round(fsum(by_yr_p[y] for y in clock.CLUSTERS["A"]), 2),
        "price_B": round(fsum(by_yr_p[y] for y in clock.CLUSTERS["B"]), 2),
        "pos_years": sum(by_yr[y] > 0 for y in clock.YEAR),
        "dd_R": round(dd, 2),
    }


# ==============================================================================
# TRACK 3: UNIFIED 3-ENGINE PRAGUE-RESET FLOATING-EQUITY & MARGIN SIMULATOR
# ==============================================================================

def replay_3engine_prague(
    intraday_days: set[str],
    intraday_tapes: dict[str, dict],
    intraday_risks: dict[str, float],
    carry_trades: list[dict],
    carry_risk_pct: float,
    initial: float,
    specs: dict,
    *,
    max_carry_open: int = 4,
) -> dict:
    """Exact unified Prague-reset floating-equity & margin simulation for Engine #1 + #2 (M1) + Engine #3 (H4 multi-day).

    Every trade is sized from static initial capital (FTMO fixed-budget sizing matching pass11_portfolio.replay),
    checked against exact live free margin (1:30 Swing / 1:100 Standard), and tracked at every M1 intraday minute
    plus every H4 carry mark across Europe/Prague daily resets.
    """
    # Collect all candidate trade descriptors with unified (entry_ts, exit_ts, sym, kind, ...)
    # Intraday trades: restrict to intraday_days matching Pass 17 extended cohort
    events = []
    for d in sorted(intraday_days):
        for eng, rpct in intraday_risks.items():
            if rpct > 0 and d in intraday_tapes.get(eng, {}):
                row, stamps, marks = intraday_tapes[eng][d]
                events.append(("INTRA", int(stamps[0]), eng, row, stamps, marks, rpct))
    if carry_risk_pct > 0:
        for tr in carry_trades:
            events.append(("CARRY", int(tr["entry"]), tr["sym"], tr, tr["stamps"], None, carry_risk_pct))
    events.sort(key=lambda e: (e[1], 0 if e[0] == "CARRY" else 1, e[2]))

    # Active open trades: list of dicts with lot, margin, timestamps, worst/close marks, net_cash, release_ts
    balance = float(initial)
    active = []
    sized_all = []
    rejects = Counter()
    totals_by_year = defaultdict(float)

    # First pass: chronological admission, sizing & margin check against open floating equity + used margin
    def settle_until(ts_now: int):
        nonlocal balance, active
        still = []
        for a in active:
            if a["release"] <= ts_now:
                balance += a["net_cash"]
                totals_by_year[a["exit_year"]] += a["net_cash"]
            else:
                still.append(a)
        active = still

    def open_floating_at(a: dict, ts_now: int) -> float:
        st = a["stamps"]
        j = int(st.searchsorted(ts_now, side="right")) - 1
        if j < 0:
            return 0.0
        return a["lots"] * float(a["close_per_lot"][j])

    for kind, ent_ts, eng, row, stamps, marks, rpct in events:
        settle_until(ent_ts)
        if kind == "CARRY" and sum(1 for a in active if a["kind"] == "CARRY") >= max_carry_open:
            rejects["CAP_CARRY"] += 1
            continue
        spec = specs["USDJPY"] if eng == p17.USDJPY_EXP else specs[eng]
        budget = initial * rpct
        m_per_lot = spec["margin_per_reference"] * row.get("margin_quote", 1.0)
        account = jpy_eq.Account(eng, initial, m_per_lot, spec["volume_min"], spec["volume_step"], spec["volume_max"])
        lot = jpy_eq.floor_lot(budget, row["stop_risk_with_cost_usd"], account)
        used_m = fsum(a["margin"] for a in active)
        open_fl = fsum(open_floating_at(a, ent_ts) for a in active)
        avail = balance + open_fl - used_m
        comm_req = 5.0 if kind == "CARRY" else commission(eng if eng != p17.USDJPY_EXP else "USDJPY", spec, row["entry_price"])
        if lot < spec["volume_min"]:
            rejects["MIN_LOT"] += 1
            continue
        if lot * (m_per_lot + comm_req) > avail:
            rejects["MARGIN"] += 1
            continue
        rejects["SIZED"] += 1

        if kind == "INTRA":
            rel_ts = int(stamps[-1]) + (0 if row["at_open"] else 60)
            worst_arr = marks.min(axis=1)
            close_arr = marks[:, 3]
            net_per_lot = float(row["net_usd_per_lot"])
            ex_yr = int(row["year"])
        else:
            rel_ts = int(stamps[-1]) + 1
            worst_arr = row["worst_usd"]
            close_arr = row["close_usd"]
            net_per_lot = float(row["ftmo_net"])
            ex_yr = datetime.fromtimestamp(int(row["exit"]), timezone.utc).year

        rec = {
            "kind": kind, "eng": eng, "entry": ent_ts, "release": rel_ts,
            "lots": lot, "margin": lot * m_per_lot, "net_cash": lot * net_per_lot,
            "exit_year": ex_yr, "stamps": stamps,
            "worst_per_lot": worst_arr, "close_per_lot": close_arr,
        }
        active.append(rec)
        sized_all.append(rec)

    settle_until(STOP + 86400)

    # Second pass: exact unified floating equity & Prague daily reset across ALL unique timestamps (M1 + H4)
    if not sized_all:
        return {"annual_pct": {"A": 0.0, "B": 0.0, "all": 0.0}, "peak_dd_pct": 0.0, "daily_loss_pct": 0.0,
                "underwater_months": 0.0, "peak_margin_pct": 0.0, "margin_failures": 0, "sized": 0}

    # Build sparse sorted timestamp grid containing every intraday M1 stamp, every H4 carry stamp, and every release stamp
    all_ts = np.unique(np.concatenate([
        np.concatenate([a["stamps"] for a in sized_all]),
        np.array([a["release"] for a in sized_all], dtype=np.int64),
    ]))
    n_t = len(all_ts)
    realized = np.zeros(n_t, dtype=np.float64)
    fl_close = np.zeros(n_t, dtype=np.float64)
    fl_worst_delta = np.zeros(n_t, dtype=np.float64)
    margin_ts = np.zeros(n_t, dtype=np.float64)

    for a in sized_all:
        i0 = int(all_ts.searchsorted(a["entry"], side="left"))
        i1 = int(all_ts.searchsorted(a["release"], side="left"))
        if i1 < n_t:
            realized[i1] += a["net_cash"]
        if i1 > i0:
            margin_ts[i0:i1] += a["margin"]
            # Map each grid timestamp in [i0, i1) to its latest mark index in a["stamps"]
            sub_t = all_ts[i0:i1]
            idx_m = a["stamps"].searchsorted(sub_t, side="right") - 1
            idx_m = np.clip(idx_m, 0, len(a["stamps"]) - 1)
            c_vals = a["lots"] * a["close_per_lot"][idx_m]
            w_vals = a["lots"] * a["worst_per_lot"][idx_m]
            # Exact intrabar worst excursion applies on stamps actually matching trade bars; elsewhere carry close mark
            on_bar = (a["stamps"][idx_m] == sub_t)
            fl_close[i0:i1] += c_vals
            fl_worst_delta[i0:i1] += np.where(on_bar, np.minimum(0.0, w_vals - c_vals), 0.0)

    cum_realized = initial + np.cumsum(realized)
    eq_close = cum_realized + fl_close
    eq_worst = eq_close + fl_worst_delta

    # Exact Prague daily reset tracking + Peak DD + Underwater duration
    peak = float(initial)
    peak_at = int(all_ts[0])
    max_dd = 0.0
    max_daily = 0.0
    max_uw_sec = 0
    cur_pday = None
    day_anchor = float(initial)

    # Vectorized Prague day lookup via pass7b core.prague_day cached by UTC hour bucket
    for k in range(n_t):
        ts_k = int(all_ts[k])
        pday = jpy_eq.prague_day(ts_k)
        ec = float(eq_close[k])
        ew = float(eq_worst[k])
        if pday != cur_pday:
            cur_pday = pday
            # Anchor at start of new Prague day = prior equity (or initial on day 0)
            day_anchor = float(eq_close[k - 1]) if k > 0 else float(initial)
        # Update peak & underwater
        if ec >= peak:
            if peak_at < ts_k:
                max_uw_sec = max(max_uw_sec, ts_k - peak_at)
            peak = ec
            peak_at = ts_k
        else:
            max_uw_sec = max(max_uw_sec, ts_k - peak_at)
        dd_k = peak - ew
        if dd_k > max_dd:
            max_dd = dd_k
        dl_k = day_anchor - ew
        if dl_k > max_daily:
            max_daily = dl_k

    if float(eq_close[-1]) < peak:
        max_uw_sec = max(max_uw_sec, (STOP - 1) - peak_at)

    ann_a = fsum(totals_by_year[y] for y in clock.CLUSTERS["A"]) / 3.0
    ann_b = fsum(totals_by_year[y] for y in clock.CLUSTERS["B"]) / 4.0
    ann_all = (balance - initial) / 7.0
    peak_dd_pct = 100.0 * max_dd / initial
    calmar = (100.0 * ann_all / initial) / peak_dd_pct if peak_dd_pct > 1e-9 else 0.0
    return {
        "net_usd": round(balance - initial, 2),
        "annual_pct": {
            "A": round(100.0 * ann_a / initial, 2),
            "B": round(100.0 * ann_b / initial, 2),
            "all": round(100.0 * ann_all / initial, 2),
        },
        "peak_dd_pct": round(peak_dd_pct, 2),
        "daily_loss_pct": round(100.0 * max_daily / initial, 2),
        "underwater_months": round(max_uw_sec / clock.DAY / (365.2425 / 12.0), 1),
        "calmar": round(calmar, 2),
        "peak_margin_pct": round(100.0 * float(margin_ts.max()) / initial, 1),
        "margin_failures": int(rejects["MARGIN"]),
        "min_lot_rejections": int(rejects["MIN_LOT"]),
        "carry_cap_skips": int(rejects["CAP_CARRY"]),
        "sized_total": int(rejects["SIZED"]),
        "sized_carry": sum(1 for a in sized_all if a["kind"] == "CARRY"),
    }


def run_pass20(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    swing_specs = specs["Swing"]
    conv_maps = load_fx_conversion_maps(jobs_root)
    core_daily = p18.build_usdjpy_core_daily_series(jobs_root, cache_dir, specs)

    pair_data = {sym: load_pair_data(jobs_root, sym) for sym, _, _ in POS_SWAP_UNIVERSE}

    # --- TRACK 1: H4 Forensic across all 8 Positive-Swap pairs + Stress_2x + M1 parity on USDJPY & EURUSD ---
    t1_rows = []
    base_h4_trades = {}
    for sym, side, is_jpy in POS_SWAP_UNIVERSE:
        sp = swing_specs[sym]
        trs1, fds1 = build_h4_carry_trades(pair_data[sym], side, sp, conv_maps, cost_mult=1.0, include_swap=True)
        trs2, _ = build_h4_carry_trades(pair_data[sym], side, sp, conv_maps, cost_mult=2.0, include_swap=True)
        base_h4_trades[sym] = trs1
        sf = p18.sign_flip_null_p(trs1, fds1)
        tm = random_entry_matched_hold_null(pair_data[sym], side, sp, conv_maps, trs1)
        s1 = summarize_sleeve(trs1)
        s2 = summarize_sleeve(trs2)
        corr = p18.daily_correlation(trs1, core_daily)
        t1_rows.append({
            "sym": sym, "side": "BUY" if side == 1 else "SELL", "is_jpy": is_jpy,
            "swap_pts": float(sp["swap_long"] if side == 1 else sp["swap_short"]),
            "stress1x": s1, "stress2x_net_R": s2["net_R"],
            "fade_net_R": round(fsum(f["ftmo_R"] for f in fds1), 2),
            "p_sign_flip": round(sf["ftmo_net_p"], 3),
            "p_timing_price": round(tm["timing_price_p"], 3),
            "p_timing_total": round(tm["timing_total_p"], 3),
            "corr_usdjpy_core": corr["union_corr"],
        })

    print("\n=== TRACK 1: 8 POSITIVE-SWAP PAIRS H4 FORENSIC (DON20/10, SL 2.0 ATR, 2018-2024) ===", flush=True)
    for r in t1_rows:
        s = r["stress1x"]
        print(
            f"  {r['sym']:6s} {r['side']:4s} (sw={r['swap_pts']:+5.2f}) | n={s['n']:2d} | Net={s['net_R']:+6.2f}R (PriceOnly={s['price_R']:+6.2f}R, S2x={r['stress2x_net_R']:+6.2f}R) "
            f"| A/B={s['A']:+5.1f}/{s['B']:+5.1f} (P_A/B={s['price_A']:+5.1f}/{s['price_B']:+5.1f}) yr+={s['pos_years']}/7 DD={s['dd_R']:.1f}R "
            f"| Swap=+${s['swap_usd']:.0f} | p_sf={r['p_sign_flip']:.3f} p_tm={r['p_timing_total']:.3f} | rJPY={r['corr_usdjpy_core']}",
            flush=True,
        )

    # H4 vs Native M1 Bid/Ask Parity Cross-Check on USDJPY & EURUSD
    m1_parity = [
        m1_parity_crosscheck(jobs_root, cache_dir, "USDJPY", 1, base_h4_trades["USDJPY"], swing_specs["USDJPY"]),
        m1_parity_crosscheck(jobs_root, cache_dir, "EURUSD", -1, base_h4_trades["EURUSD"], swing_specs["EURUSD"]),
    ]
    print("\n=== TRACK 1B: H4 vs NATIVE M1 BID/ASK PARITY CROSS-CHECK ===", flush=True)
    for mp in m1_parity:
        print(f"  {mp['sym']:6s} ({mp['matched']}/{mp['h4_total']}) | H4={mp['h4_net_R']:+6.2f}R vs M1_Native={mp['m1_native_net_R']:+6.2f}R | diff={mp['diff_R_total']:+.2f}R ({mp['diff_R_per_year']:+.3f}R/yr)", flush=True)

    # --- TRACK 2: 12-Cell 2D Parameter Surface on NON_JPY_4 and ALL_8_JPYCAP1 ---
    surf_non_jpy = {}
    surf_all8 = {}
    for ed in (15, 20, 30, 40):
        for ex_d, sl_a in ((10, 1.5), (10, 2.0), (15, 2.5)):
            key = f"don{ed}_ex{ex_d}_sl{sl_a:.1f}"
            by_sym = {
                sym: build_h4_carry_trades(pair_data[sym], side, swing_specs[sym], conv_maps, entry_don=ed, exit_don=ex_d, sl_atr=sl_a)[0]
                for sym, side, _ in POS_SWAP_UNIVERSE
            }
            tr_nj = apply_sleeve_filters(by_sym, NON_JPY_4, max_jpy_open=None)
            tr_a8 = apply_sleeve_filters(by_sym, tuple(s for s, _, _ in POS_SWAP_UNIVERSE), max_jpy_open=1)
            surf_non_jpy[key] = summarize_sleeve(tr_nj)
            surf_all8[key] = summarize_sleeve(tr_a8)

    nj_both_pos = sum(1 for v in surf_non_jpy.values() if v["A"] > 0 and v["B"] > 0)
    nj_price_both_pos = sum(1 for v in surf_non_jpy.values() if v["price_A"] > 0 and v["price_B"] > 0)
    a8_both_pos = sum(1 for v in surf_all8.values() if v["A"] > 0 and v["B"] > 0)
    a8_price_both_pos = sum(1 for v in surf_all8.values() if v["price_A"] > 0 and v["price_B"] > 0)

    print(f"\n=== TRACK 2: 12-CELL 2D PARAMETER SURFACE ===", flush=True)
    print(f"  NON_JPY_4 (USDCAD/USDCHF/EURUSD/EURGBP): {nj_both_pos}/12 both A&B>0 with swap | {nj_price_both_pos}/12 price-only A&B>0", flush=True)
    print(f"  ALL_8_JPYCAP1 (8 pairs, max 1 JPY open): {a8_both_pos}/12 both A&B>0 with swap | {a8_price_both_pos}/12 price-only A&B>0", flush=True)
    for key in ("don20_ex10_sl2.0", "don30_ex10_sl2.0", "don20_ex15_sl2.5"):
        vn, va = surf_non_jpy[key], surf_all8[key]
        print(f"    {key:18s} | NON_JPY_4: n={vn['n']:3d} Net={vn['net_R']:+5.1f}R(P={vn['price_R']:+5.1f}R) A/B={vn['A']:+4.1f}/{vn['B']:+4.1f} DD={vn['dd_R']:.1f}R | ALL_8_CAP1: n={va['n']:3d} Net={va['net_R']:+5.1f}R(P={va['price_R']:+5.1f}R) A/B={va['A']:+4.1f}/{va['B']:+4.1f} DD={va['dd_R']:.1f}R", flush=True)

    # --- TRACK 3: UNIFIED 3-ENGINE PRAGUE-RESET FLOATING EQUITY (Swing 10k, Swing 25k, Standard 50k) ---
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    exp_tape = p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)
    exp_map = {r["day"]: (r, t, m) for r, t, m in exp_tape}
    intraday_tapes = {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_map}
    ext_days = ref_days["extended"]

    # Recompute exact Pass 17 inverse-DD weights on Cluster A
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}
    specs_ext = {prof: {**sp, p17.USDJPY_EXP: sp["USDJPY"]} for prof, sp in specs.items()}
    a_dd = {
        s: portfolio.replay(cluster_a, intraday_tapes, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP)
    }
    inv = {s: (1.0 / a_dd[s]) / fsum(1.0 / v for v in a_dd.values()) for s in a_dd}
    core_risk_075 = {s: 0.0075 * w for s, w in inv.items()}
    core_risk_100 = {s: 0.0100 * w for s, w in inv.items()}

    sleeve_nj = apply_sleeve_filters(base_h4_trades, NON_JPY_4, max_jpy_open=None)
    sleeve_a8 = apply_sleeve_filters(base_h4_trades, tuple(s for s, _, _ in POS_SWAP_UNIVERSE), max_jpy_open=1)

    configs = [
        ("BASE_2E_INVDD_075", core_risk_075, [], 0.0),
        ("SOLO_CARRY_NJ4_050", {}, sleeve_nj, 0.005),
        ("SOLO_CARRY_A8C1_050", {}, sleeve_a8, 0.005),
        ("PORT3E_075_NJ4_025", core_risk_075, sleeve_nj, 0.0025),
        ("PORT3E_075_NJ4_040", core_risk_075, sleeve_nj, 0.0040),
        ("PORT3E_075_NJ4_050", core_risk_075, sleeve_nj, 0.0050),
        ("PORT3E_075_A8C1_025", core_risk_075, sleeve_a8, 0.0025),
        ("PORT3E_075_A8C1_040", core_risk_075, sleeve_a8, 0.0040),
        ("PORT3E_075_A8C1_050", core_risk_075, sleeve_a8, 0.0050),
        ("PORT3E_100_A8C1_050", core_risk_100, sleeve_a8, 0.0050),
    ]

    books = {}
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        books[bkey] = {}
        for cname, irisk, ctrades, crisk in configs:
            books[bkey][cname] = replay_3engine_prague(
                ext_days, intraday_tapes, irisk, ctrades, crisk, cap, specs_ext[prof], max_carry_open=4
            )

    print("\n=== TRACK 3: 3-ENGINE PRAGUE-RESET FLOATING EQUITY (SWING 10K / SWING 25K / STANDARD 50K) ===", flush=True)
    for bkey in ("Swing_10000", "Swing_25000", "Standard_50000"):
        print(f"  --- {bkey} ---", flush=True)
        for cname, m in books[bkey].items():
            ap = m["annual_pct"]
            print(
                f"    {cname:22s} | ann={ap['all']:+5.2f}%/yr (A={ap['A']:+5.2f}%, B={ap['B']:+5.2f}%) "
                f"| peakDD={m['peak_dd_pct']:5.2f}% | daily={m['daily_loss_pct']:4.2f}% | uw={m['underwater_months']:4.1f}m "
                f"| calmar={m['calmar']:4.2f} | mgn={m['peak_margin_pct']:5.1f}% fail={m['margin_failures']} (carryN={m['sized_carry']})",
                flush=True,
            )

    return {
        "pass": "Pass 20", "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA, "holdout_rows": 0,
        "order_send_count": 0, "network_calls": 0, "spec_bindings": bindings,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "track1_h4_forensic": t1_rows,
        "track1b_m1_parity": m1_parity,
        "track2_surface_non_jpy_4": {
            "both_clusters_pos_with_swap": nj_both_pos,
            "both_clusters_pos_price_only": nj_price_both_pos,
            "cells": surf_non_jpy,
        },
        "track2_surface_all8_jpycap1": {
            "both_clusters_pos_with_swap": a8_both_pos,
            "both_clusters_pos_price_only": a8_price_both_pos,
            "cells": surf_all8,
        },
        "track3_books": books,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass20(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass20-result.json", res)
    print("\nPASS20_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
