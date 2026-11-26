"""Pass 27: Bound FTMO Demo US100 Spec Parity, Exact M1 Floating-Equity 5/6/7-Engine Prague-Reset Audit
& Empirical Benchmark of Phase-Based Prop Portfolio Profiles (FTMO Swing 10k + The5ers High Stakes 5k).

Strictly causal Development 2018-2024 (holdout_rows = 0, OrderSend = 0).
"""

import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from math import fsum, isclose
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as jpy_eq
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass19_us500_supertrend_yencross as p19
import pass22_gbpusd_volhigh_3engine as p22
import pass23_ftmo_lifecycle_sim as p23l
import pass23_xau_indices_discovery as p23d
import pass24_mtf_new_archetypes as p24
import pass26_cross_asset_rs as p26
import whitebox_discovery as wbd
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from quant_core.ftmo_track_replay import commission, profiles
from quant_core.holdout_guard import enforce_pre_holdout_ts

PROTOCOL = "262d0e221e847065df531146b84fc584909a81e2"
DEMO_SPEC_ARTIFACT = Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs\ftmo-demo-indices-spec-20261123\ftmo_indices_spec_snapshot.json")
SEED = 20261123
BOOTSTRAP_PATHS = 2000
BLOCK_DAYS = 5


# ==============================================================================
# 1. EXACT MINUTE-BY-MINUTE M1 FLOATING-EQUITY TAPE BUILDER (ALL ASSET CLASSES)
# ==============================================================================

def replay_causal_m1_tape_trade(
    asset: str,
    times: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    flat_idx: int,
    side: int,
    entry_p: float,
    sl_p: float,
    *,
    spec: dict | None = None,
    usdjpy_close_map: dict | None = None,
    cost_tier: str = "stress",
) -> tuple[dict, np.ndarray, np.ndarray] | None:
    """Build exact minute-by-minute (row, stamps, marks) tuple reconciled to terminal cash USD per 1.00 lot."""
    risk_p = side * (entry_p - sl_p)
    if risk_p <= 0 or entry_idx < 0 or flat_idx <= entry_idx:
        return None
    liq = quotes[entry_idx:flat_idx + 1, :4] if side == 1 else quotes[entry_idx:flat_idx + 1, 4:8]
    if side == 1:
        sl_hits = np.flatnonzero(liq[:-1, 2] <= sl_p + 1e-10)
    else:
        sl_hits = np.flatnonzero(liq[:-1, 1] >= sl_p - 1e-10)

    if len(sl_hits):
        rel = int(sl_hits[0])
        op = float(liq[rel, 0])
        gap = rel > 0 and side * (op - sl_p) <= 1e-10
        ex_p = op if gap else sl_p
        at_open = bool(gap)
        reason = "SL_GAP_OR_TOUCH"
    else:
        rel = len(liq) - 1
        ex_p = float(liq[-1, 0])
        at_open = True
        reason = "HARD_FLAT"

    stamps = times[entry_idx:entry_idx + rel + 1].astype(np.int64)
    enforce_pre_holdout_ts(stamps, START, STOP, context=f"pass27.replay_causal_m1_tape_trade:{asset}")

    c = p24.asset_cost_tiers(asset)
    slip_rt = float(c[cost_tier])
    comm = float(c["comm_usd"])
    sub_liq = liq[:rel + 1]

    d_entry = datetime.fromtimestamp(int(stamps[0]), timezone.utc).date()
    d_ex = datetime.fromtimestamp(int(stamps[-1]), timezone.utc).date()

    def _prior_day_rate(rmap: dict | None, ref_d) -> float | None:
        if not rmap:
            return None
        for lag in range(1, 15):
            val = rmap.get(ref_d - timedelta(days=lag))
            if val is not None and float(val) > 0.0:
                return float(val)
        earlier = [k for k in rmap if k < ref_d]
        return float(rmap[max(earlier)]) if earlier else None

    if c["is_index"]:
        # FTMO Demo bound spec for US100.cash / US500.cash: 1.0 pt x 1.0 lot = $1.00 USD, commission = $0.00
        cs = 1.0
        entry_conv_rate = 1.0
        exit_conv_rate = 1.0
    else:
        if spec is None:
            raise ValueError(f"Missing broker spec for non-index asset: {asset}")
        cs = float(spec["trade_contract_size"])
        cp = spec.get("currency_profit", "USD")
        if cp == "USD":
            entry_conv_rate = 1.0
            exit_conv_rate = 1.0
        elif cp == "JPY":
            if asset == "USDJPY":
                entry_conv_rate = 1.0 / entry_p
                exit_conv_rate = 1.0 / ex_p
            else:
                # Strictly causal entry conversion: prior-day USDJPY close (< d_entry), NEVER d_ex or ex_p!
                usdjpy_ent = _prior_day_rate(usdjpy_close_map, d_entry)
                entry_conv_rate = 1.0 / (usdjpy_ent if usdjpy_ent is not None else entry_p)
                usdjpy_ex = (
                    (usdjpy_close_map.get(d_ex) or _prior_day_rate(usdjpy_close_map, d_ex) or usdjpy_ent)
                    if usdjpy_close_map
                    else ex_p
                )
                exit_conv_rate = 1.0 / (float(usdjpy_ex) if usdjpy_ex is not None else ex_p)
        elif cp in ("CAD", "CHF"):
            entry_conv_rate = 1.0 / entry_p
            exit_conv_rate = 1.0 / ex_p
        else:
            entry_conv_rate = 1.0
            exit_conv_rate = 1.0

    # Strictly causal entry-time sizing scale & drag (zero future exit price / exit FX leak!)
    entry_scale = cs * entry_conv_rate
    entry_drag_usd = comm + slip_rt * entry_scale
    exit_scale = cs * exit_conv_rate
    exit_drag_usd = comm + slip_rt * exit_scale

    # Minute-by-minute causal floating PnL in USD per 1.00 lot
    hi_px = sub_liq[:, 1] if side == 1 else sub_liq[:, 2]
    lo_px = sub_liq[:, 2] if side == 1 else sub_liq[:, 1]
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        s_op = cs / sub_liq[:, 0]
        s_hi = cs / hi_px
        s_lo = cs / lo_px
        s_cl = cs / sub_liq[:, 3]
        cur_pnl = side * (sub_liq[:, 0] - entry_p) * s_op - (comm + slip_rt * s_op)
        hi_pnl = side * (hi_px - entry_p) * s_hi - (comm + slip_rt * s_hi)
        lo_pnl = side * (lo_px - entry_p) * s_lo - (comm + slip_rt * s_lo)
        cls_pnl = side * (sub_liq[:, 3] - entry_p) * s_cl - (comm + slip_rt * s_cl)
    else:
        cur_pnl = side * (sub_liq[:, 0] - entry_p) * entry_scale - entry_drag_usd
        hi_pnl = side * (hi_px - entry_p) * entry_scale - entry_drag_usd
        lo_pnl = side * (lo_px - entry_p) * entry_scale - entry_drag_usd
        cls_pnl = side * (sub_liq[:, 3] - entry_p) * entry_scale - entry_drag_usd

    # Entry bar: opening quote may predate stop trigger; anchor open mark at entry spread
    spr0 = max(0.0, float(quotes[entry_idx, 4] - quotes[entry_idx, 0]))
    cur_pnl[0] = -spr0 * entry_scale - entry_drag_usd
    hi_pnl[0] = max(cur_pnl[0], cls_pnl[0])
    lo_pnl[0] = min(cur_pnl[0], lo_pnl[0], cls_pnl[0])

    # Realized exit cash strictly uses exit_conv_rate
    net_usd = side * (ex_p - entry_p) * exit_scale - exit_drag_usd
    if rel == 0 or at_open:
        cur_pnl[-1] = hi_pnl[-1] = lo_pnl[-1] = cls_pnl[-1] = net_usd
    else:
        hi_pnl[-1] = max(cur_pnl[-1], net_usd)
        lo_pnl[-1] = min(cur_pnl[-1], net_usd)
        cls_pnl[-1] = net_usd

    marks = np.column_stack((cur_pnl, hi_pnl, lo_pnl, cls_pnl)).astype(np.float64)
    stop_risk_usd = risk_p * entry_scale + entry_drag_usd
    d_iso = d_entry.isoformat()
    row = {
        "day": d_iso,
        "year": int(d_iso[:4]),
        "asset": asset,
        "entry": int(stamps[0]),
        "exit": int(stamps[-1]) + (0 if at_open else 60),
        "at_open": at_open,
        "reason": reason,
        "side": side,
        "entry_price": float(entry_p),
        "sl_price": float(sl_p),
        "entry_conv_rate": float(entry_conv_rate),
        "exit_conv_rate": float(exit_conv_rate),
        "net_usd_per_lot": float(net_usd),
        "stop_risk_with_cost_usd": float(stop_risk_usd),
        "net_R": float(net_usd / stop_risk_usd),
    }
    return row, stamps, marks


def build_us100_e4_tape(bundle: dict) -> dict[str, tuple]:
    """Exact M1 tape for Engine #4: US100 SESS_CONT_BRK_40 (min_move=0.40, close_pct=0.70, sl=0.65)."""
    times, quotes = bundle["times"], bundle["quotes"]
    out = {}
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
        if mrng <= 1e-9 or abs(mc - mo) < 0.40 * a_val:
            continue
        pos = (mc - ml) / mrng
        if mc > mo and pos >= 0.70:
            side = 1
        elif mc < mo and pos <= 0.30:
            side = -1
        else:
            continue

        fi, flat_idx = d["fi"], d["flat_idx"]
        sub_t = times[fi:flat_idx + 1]
        i0 = int(sub_t.searchsorted(me, side="left"))
        i1 = int(sub_t.searchsorted(max(we, me + 5 * 3600), side="left"))
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        if side == 1:
            hits = np.flatnonzero(scan[:, 5] >= mh - 1e-10)
        else:
            hits = np.flatnonzero(scan[:, 2] <= ml + 1e-10)
        if not len(hits):
            continue
        e_idx = fi + i0 + int(hits[0])
        ep = max(mh, float(quotes[e_idx, 4])) if side == 1 else min(ml, float(quotes[e_idx, 0]))
        item = replay_causal_m1_tape_trade("US100", times, quotes, e_idx, flat_idx, side, ep, ep - side * 0.65 * a_val)
        if item is not None:
            out[item[0]["day"]] = item
    return out


def build_us100_e5_tape(bundles: dict, day_maps: dict, all_days: list[str]) -> dict[str, tuple]:
    """Exact M1 tape for Engine #5: IDX_RS_US100_LEAD_1130 (thr=0.25, sl=0.75, exact Pass 26 parity n=261)."""
    out = {}
    b100 = bundles["US100"]
    times, quotes = b100["times"], b100["quotes"]
    for dk in all_days:
        if dk not in day_maps["US100"] or dk not in day_maps["US500"]:
            continue
        d100, d500 = day_maps["US100"][dk], day_maps["US500"][dk]
        ts_s, ts_e = d100["day_sec"], d100["day_sec"] + 120 * 60
        z100 = p26.causal_z_return(b100, ts_s, ts_e, d100["atr"])
        z500 = p26.causal_z_return(bundles["US500"], ts_s, ts_e, d500["atr"])
        if z100 is None or z500 is None:
            continue
        diff = z100 - z500
        if abs(diff) < 0.25 or (z100 * diff <= 0):
            continue
        side = 1 if diff > 0 else -1
        fi, flat_idx = d100["fi"], d100["flat_idx"]
        rel = int(times[fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        e_idx = fi + rel
        if e_idx >= flat_idx or int(times[e_idx]) - ts_e > 600:
            continue
        ep = float(quotes[e_idx, 4] if side == 1 else quotes[e_idx, 0])
        item = replay_causal_m1_tape_trade("US100", times, quotes, e_idx, flat_idx, side, ep, ep - side * 0.75 * d100["atr"])
        if item is not None:
            out[item[0]["day"]] = item
    return out


def build_fx_usd_basket_s6_tape(bundles: dict, day_maps: dict, all_days: list[str]) -> dict[str, tuple]:
    """Exact M1 tape for Satellite #6: FX_USD_BASKET_12U_Z35 (entry=12 UTC, lb=5h, min_z=0.35, sl=0.75)."""
    out = {}
    for dk in all_days:
        if not all(dk in day_maps[a] for a in p26.FX7):
            continue
        dsec = day_maps["USDJPY"][dk]["day_sec"]
        ts_e = dsec + 12 * 3600
        ts_s = ts_e - 5 * 3600
        z_map = {}
        for a in p26.FX7:
            z = p26.causal_z_return(bundles[a], ts_s, ts_e, day_maps[a][dk]["atr"])
            if z is not None:
                z_map[a] = z
        if len(z_map) < len(p26.FX7):
            continue
        usd_s = p26.compute_g6_factors(z_map)["USD"]
        if abs(usd_s) < 0.35:
            continue
        usd_dir = 1 if usd_s > 0 else -1
        best_a, best_sc, best_side = None, -1e9, 0
        for a in p26.USD_MAJORS_NOJPY:
            base, _ = p26.PAIR_CCY[a]
            side = usd_dir if base == "USD" else -usd_dir
            sc = side * z_map[a]
            if sc > best_sc:
                best_a, best_sc, best_side = a, sc, side
        if best_a is None or best_sc <= 0:
            continue
        b = bundles[best_a]
        dr = day_maps[best_a][dk]
        fi, flat_idx = dr["fi"], dr["flat_idx"]
        rel = int(b["times"][fi:flat_idx + 1].searchsorted(ts_e, side="left"))
        e_idx = fi + rel
        if e_idx >= flat_idx or int(b["times"][e_idx]) - ts_e > 600:
            continue
        ep = float(b["quotes"][e_idx, 4] if best_side == 1 else b["quotes"][e_idx, 0])
        item = replay_causal_m1_tape_trade(
            best_a, b["times"], b["quotes"], e_idx, flat_idx, best_side, ep,
            ep - best_side * 0.75 * dr["atr"], spec=b["spec"], usdjpy_close_map=b["usdjpy_close_map"],
        )
        if item is not None:
            out[item[0]["day"]] = item
    return out


def build_xau_exp120_s7_tape(xau_bundle: dict) -> dict[str, tuple]:
    """Exact M1 tape for Satellite #7: XAU_EXP_DAILY_OPEN_120 (trig=1.20 ATR, sl=0.75 ATR, swap=0, Native M1 Bid/Ask)."""
    out = {}
    times, quotes = xau_bundle["times"], xau_bundle["quotes"]
    for d in xau_bundle["days"]:
        fi, flat_idx = d["fi"], d["flat_idx"]
        a_val = d["atr"]
        open_0 = float(quotes[fi, 0])
        top, bot = open_0 + 1.20 * a_val, open_0 - 1.20 * a_val
        sub_t = times[fi:flat_idx + 1]
        i0 = int(sub_t.searchsorted(d["day_sec"] + 7 * 3600, side="left"))
        i1 = int(sub_t.searchsorted(d["day_sec"] + 17 * 3600, side="left"))
        if i1 <= i0:
            continue
        scan = quotes[fi + i0:fi + i1]
        up = scan[:, 5] >= top - 1e-10
        dn = scan[:, 2] <= bot + 1e-10
        hits = np.flatnonzero(up | dn)
        if not len(hits):
            continue
        j = int(hits[0])
        if up[j] and dn[j]:
            continue
        side = 1 if up[j] else -1
        e_idx = fi + i0 + j
        ep = max(top, float(quotes[e_idx, 4])) if side == 1 else min(bot, float(quotes[e_idx, 0]))
        item = replay_causal_m1_tape_trade(
            "XAUUSD", times, quotes, e_idx, flat_idx, side, ep,
            ep - side * 0.75 * a_val, spec=xau_bundle["spec"], usdjpy_close_map=xau_bundle["usdjpy_close_map"],
        )
        if item is not None:
            out[item[0]["day"]] = item
    return out


# ==============================================================================
# 2. EXACT M1 MULTI-ENGINE PRAGUE-RESET PORTFOLIO REPLAY WITH OVERLAP CAP
# ==============================================================================

def margin_per_lot_usd(asset: str, entry_price: float, profile_mode: str = "Swing") -> tuple[float, float, float, float, float]:
    """Return (margin_per_lot_usd, vol_min, vol_step, vol_max, comm_usd_per_lot) using FTMO Demo bound specs."""
    # FTMO Demo bound leverage ratios:
    # Standard: FX 1:100, US100.cash 1:50 (2.0% measured 517.05 / 25852.68), XAUUSD 1:50 (2.0% measured 7240.82 / 362041)
    # Swing: FX 1:30 (3.333%), US100.cash conservative 1:15 (6.67%), XAUUSD 1:10 (10.0%)
    is_std = (profile_mode == "Standard")
    if asset in ("US100", "US100.cash", "US500", "US500.cash"):
        mgn = entry_price * (0.02 if is_std else (1.0 / 15.0))
        return mgn, 0.01, 0.01, 1000.0, 0.0
    if asset == "XAUUSD":
        mgn = entry_price * 100.0 * (0.02 if is_std else 0.10)
        return mgn, 0.01, 0.01, 100.0, 5.20
    # FX pairs (100,000 contract size; margin in USD = 100k * base_to_usd / lev)
    lev = 100.0 if is_std else 30.0
    if asset in ("USDJPY", "USDCAD", "USDCHF"):
        notional_usd = 100000.0
    elif asset.startswith("EUR") and not asset.endswith("USD"):
        notional_usd = 100000.0 * 1.15  # conservative EUR/USD upper bound for EUR crosses
    elif asset.startswith("GBP") and not asset.endswith("USD"):
        notional_usd = 100000.0 * 1.35  # conservative GBP/USD upper bound for GBP crosses
    else:
        # GBPUSD, EURUSD, AUDUSD: entry_price is base/USD
        notional_usd = 100000.0 * entry_price
    return notional_usd / lev, 0.01, 0.01, 50.0, 5.0


def replay_multi_engine_m1(
    days: list[str],
    tapes: dict[str, dict],
    risks: dict[str, float],
    initial: float = 10000.0,
    *,
    profile_mode: str = "Swing",
    us100_same_dir_cap: float | None = None,
    cutoff: int = STOP,
) -> tuple[dict, list[dict]]:
    """Exact minute-by-minute M1 floating-equity Prague-reset portfolio audit across arbitrary multi-asset engines."""
    balance = float(initial)
    sorted_days = sorted(days)
    meter = jpy_eq.EquityMetrics(initial, START, [int(np.datetime64(d, "D").astype(int)) for d in sorted_days])
    exits, totals, rejects = [], defaultdict(list), Counter()
    peak_margin = peak_simultaneous = 0.0
    max_concurrent = 0
    us100_cap_activations = 0

    for dk in sorted_days:
        day_candidates = [(eng, tapes[eng][dk]) for eng in risks if dk in tapes[eng]]
        if not day_candidates:
            continue
        # Strictly causal chronological entry order
        day_candidates.sort(key=lambda kv: (kv[1][0]["entry"], kv[0]))

        sized = []
        orders = []
        us100_dir_risk_used = {1: 0.0, -1: 0.0}

        for eng, (row, stamps, marks) in day_candidates:
            eff_risk = float(risks[eng])
            asset = row.get("asset") or ("USDJPY" if "USDJPY" in eng else ("GBPUSD" if "GBPUSD" in eng else eng))
            if us100_same_dir_cap is not None and asset == "US100":
                side = int(row["side"])
                rem = max(0.0, us100_same_dir_cap - us100_dir_risk_used[side])
                if rem < eff_risk - 1e-12:
                    us100_cap_activations += 1
                    eff_risk = rem
                if eff_risk <= 1e-9:
                    orders.append({"engine": eng, "status": "US100_OVERLAP_SKIP", "lots": 0.0})
                    rejects["US100_OVERLAP_SKIP"] += 1
                    continue

            budget = initial * eff_risk
            mgn_1lot, vmin, vstep, vmax, comm_1lot = margin_per_lot_usd(asset, float(row["entry_price"]), profile_mode)
            acct = jpy_eq.Account(eng, initial, mgn_1lot, vmin, vstep, vmax)
            lot = jpy_eq.floor_lot(budget, float(row["stop_risk_with_cost_usd"]), acct)
            stamp = int(stamps[0])
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
                sized.append(portfolio.SizedTrade(row, stamps, marks, lot, lot * mgn_1lot, lot * float(row["net_usd_per_lot"])))
                if asset == "US100":
                    us100_dir_risk_used[int(row["side"])] += eff_risk

        if not sized:
            continue

        tl, comb_marks, mgn_arr, conc_arr, _stale = portfolio.combined_marks(sized)
        # Verify Prague day consistency (all engines flat <= 20:55 UTC <= 22:55 Prague)
        assert jpy_eq.prague_day(int(tl[0])) == jpy_eq.prague_day(int(tl[-1])), f"Prague midnight crossed on {dk}"
        points = np.r_[balance, (balance + comb_marks).ravel()]
        meter.add(np.r_[tl[0], np.repeat(tl, 4)], points, balance)

        peak_margin = max(peak_margin, float(mgn_arr.max()))
        cmax = int(conc_arr.max())
        max_concurrent = max(max_concurrent, cmax)
        if np.any(conc_arr >= 2):
            peak_simultaneous = max(peak_simultaneous, float(mgn_arr[conc_arr >= 2].max()))

        net = fsum(t.net for t in sized)
        assert isclose(float(comb_marks[-1, -1]), net, abs_tol=1e-5), f"Terminal reconciliation mismatch on {dk}"
        balance += net
        totals[dk[:4]].append(net)
        exits.append({
            "day": dk,
            "net_usd": net,
            "cash": balance,
            "orders": orders,
            "day_equity_minimum": float(points.min()),
            "day_equity_maximum": float(points.max()),
        })

    if balance < meter.peak:
        meter.update_age(np.array([meter.peak_at]), np.array([cutoff - 1]))

    ann_A = fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["A"]) / 3.0
    ann_B = fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["B"]) / 4.0
    ann_all = (balance - initial) / 7.0
    peak_dd_pct = 100.0 * meter.dd / initial
    ann_pct_all = 100.0 * ann_all / initial
    calmar = (ann_pct_all / peak_dd_pct) if peak_dd_pct > 1e-9 else 0.0

    metrics = {
        "profile_mode": profile_mode,
        "net_usd": round(balance - initial, 2),
        "ann_pct": {"all": round(ann_pct_all, 2), "A": round(100.0 * ann_A / initial, 2), "B": round(100.0 * ann_B / initial, 2)},
        "daily_loss_pct": round(100.0 * meter.daily / initial, 2),
        "peak_dd_pct": round(peak_dd_pct, 2),
        "static_loss_pct": round(100.0 * max(0.0, initial - min(initial, meter.minimum)) / initial, 2),
        "calmar": round(calmar, 2),
        "underwater_months": round(meter.max_age[0] / clock.DAY / (365.2425 / 12.0), 2),
        "peak_margin_pct": round(100.0 * peak_margin / initial, 2),
        "peak_simultaneous_margin_pct": round(100.0 * peak_simultaneous / initial, 2),
        "max_concurrent_positions": max_concurrent,
        "sized_trades": int(rejects["SIZED"]),
        "margin_failures": int(rejects["MARGIN"]),
        "min_lot_rejections": int(rejects["MIN_LOT"]),
        "us100_cap_activations": us100_cap_activations,
        "years_pct": {str(y): round(100.0 * fsum(totals[str(y)]) / initial, 2) for y in clock.YEAR},
    }
    return metrics, exits


def analyze_us100_overlap(e4_tape: dict, e5_tape: dict) -> dict:
    """Detailed overlap forensics between Engine #4 (SESS_CONT_BRK_40) and Engine #5 (IDX_RS_US100_LEAD_1130)."""
    d4, d5 = set(e4_tape.keys()), set(e5_tape.keys())
    both = sorted(d4 & d5)
    same_dir = [d for d in both if e4_tape[d][0]["side"] == e5_tape[d][0]["side"]]
    opp_dir = [d for d in both if e4_tape[d][0]["side"] != e5_tape[d][0]["side"]]
    same_both_sl = [d for d in same_dir if e4_tape[d][0]["reason"] == "SL_GAP_OR_TOUCH" and e5_tape[d][0]["reason"] == "SL_GAP_OR_TOUCH"]
    same_sum_R = round(fsum(e4_tape[d][0]["net_R"] + e5_tape[d][0]["net_R"] for d in same_dir), 2)
    opp_sum_R = round(fsum(e4_tape[d][0]["net_R"] + e5_tape[d][0]["net_R"] for d in opp_dir), 2)
    return {
        "e4_days": len(d4),
        "e5_days": len(d5),
        "overlap_days": len(both),
        "overlap_pct_of_e5": round(100.0 * len(both) / max(1, len(d5)), 1),
        "same_dir_days": len(same_dir),
        "opp_dir_days": len(opp_dir),
        "same_dir_both_sl_days": len(same_both_sl),
        "same_dir_combined_R": same_sum_R,
        "opp_dir_combined_R": opp_sum_R,
    }


# ==============================================================================
# 3. PHASE-BASED PROP PROFILE ARCHITECTURE SIMULATOR (4-STATE MACHINE + LADDER)
# ==============================================================================

def _draw_bootstrap_indices(n_days: int, horizon: int = 504, n_paths: int = BOOTSTRAP_PATHS, seed: int = SEED) -> np.ndarray:
    rng = np.random.default_rng(seed)
    n_blocks = (horizon + BLOCK_DAYS - 1) // BLOCK_DAYS
    max_start = n_days - BLOCK_DAYS
    out = np.empty((n_paths, horizon), dtype=np.int32)
    for b in range(n_paths):
        starts = rng.integers(0, max_start + 1, size=n_blocks)
        seq = np.concatenate([np.arange(s, s + BLOCK_DAYS, dtype=np.int32) for s in starts])[:horizon]
        out[b] = seq
    return out


def compute_phase_state_and_mult(
    stage: str,
    bal: float,
    initial: float,
    policy: dict,
    refunded: bool,
) -> tuple[str, float, str]:
    """Deterministic causal state machine mapping (stage, equity_pct, policy) -> (state_name, risk_mult, portfolio_key).

    Zero lookahead: depends solely on start-of-day account balance & current prop stage.
    """
    eq_pct = (bal - initial) / initial  # e.g. +0.075 = +7.5%, -0.04 = -4.0%
    core_key = policy["core_key"]
    p1_key = policy.get("p1_key", core_key)

    if stage == "P1":
        m = float(policy["p1_mult"])
        pkey = p1_key
        state = "P1_GREEN"
        # Target Lock-In Glidepath
        if policy.get("glidepath"):
            if eq_pct >= 0.085:
                return "P1_LOCKIN_FINAL", min(m, 0.50), core_key
            if eq_pct >= 0.070:
                return "P1_LOCKIN", min(m, 1.00), core_key
        # Drawdown state machine (AMBER / RED)
        if policy.get("dynamic_dd", True):
            if eq_pct <= -0.060:
                return "RED_SURVIVAL", min(m, 0.40), core_key
            if eq_pct <= -0.035:
                return "AMBER_THROTTLE", min(m, 0.65), core_key
        return state, m, pkey

    if stage == "P2":
        m = float(policy["p2_mult"])
        if policy.get("glidepath") and eq_pct >= 0.032:
            return "P2_LOCKIN", min(m, 0.60), core_key
        if policy.get("dynamic_dd", True):
            if eq_pct <= -0.060:
                return "RED_SURVIVAL", min(m, 0.40), core_key
            if eq_pct <= -0.035:
                return "AMBER_THROTTLE", min(m, 0.65), core_key
        return "P2_CRUISE", m, core_key

    # FUNDED stage
    m = float(policy["funded_mult"])
    if policy.get("funded_survival") and (not refunded) and eq_pct < 0.025:
        m = min(m, 0.80)
        state = "FUNDED_SURVIVAL"
    else:
        state = "FUNDED_HARVEST"
    if policy.get("dynamic_dd", True):
        if eq_pct <= -0.060:
            return "RED_SURVIVAL", min(m, 0.40), core_key
        if eq_pct <= -0.035:
            return "AMBER_THROTTLE", min(m, 0.65), core_key
    return state, m, core_key


def run_single_firm_path(
    idx_seq: np.ndarray,
    series_map: dict[str, tuple[np.ndarray, np.ndarray, np.ndarray]],
    *,
    firm: str,
    cap: float,
    fee: float,
    policy: dict,
) -> dict:
    """Run one 24-month (504 trading-day) path under exact firm rules and phase-based profile policy."""
    scale = cap / 10000.0
    p1_goal = cap * 1.10
    p2_goal = cap * 1.05
    daily_cap = cap * 0.05
    static_floor = cap * 0.90
    is_5ers = ("5ERS" in firm.upper())
    min_d = 3 if is_5ers else 4
    leave_buf = float(policy.get("funded_keep_buffer_pct", 0.0)) * cap

    stage = "P1"
    bal = cap
    tdays = 0
    attempts = 1
    fees_spent = fee
    refunded = False
    payouts = 0.0
    breaches_p1 = 0
    breaches_p2 = 0
    breaches_funded = 0
    first_pass_day = None
    first_payout_day = None
    cycle_d = 0
    cf12 = None
    max_oop = fee  # Max cumulative out-of-pocket cash negative peak

    for day_num, src_i in enumerate(idx_seq, start=1):
        _st, mult, pkey = compute_phase_state_and_mult(stage, bal, cap, policy, refunded)
        nets, dds, flags = series_map[pkey]
        net = float(nets[src_i]) * scale * mult
        dd = float(dds[src_i]) * scale * mult
        flg = int(flags[src_i])

        # Conservative breach ordering BEFORE target check
        if dd >= daily_cap - 1e-9 or (bal - dd) <= static_floor + 1e-9:
            if stage == "P1":
                breaches_p1 += 1
            elif stage == "P2":
                breaches_p2 += 1
            else:
                breaches_funded += 1

            if attempts <= 3:
                attempts += 1
                if is_5ers:
                    disc = 0.90 if attempts == 2 else 0.80
                    fees_spent += fee * disc
                else:
                    fees_spent += fee
                stage = "P1"
                bal = cap
                tdays = 0
                refunded = False
                cycle_d = 0
            else:
                # Out of tickets (max 4 tickets = 1 initial + 3 retries)
                pass
        else:
            bal += net
            if is_5ers:
                if net >= cap * 0.005:
                    tdays += 1
            elif flg:
                tdays += 1

            if stage == "P1" and bal >= p1_goal - 1e-9 and tdays >= min_d:
                stage = "P2"
                bal = cap
                tdays = 0
            elif stage == "P2" and bal >= p2_goal - 1e-9 and tdays >= min_d:
                stage = "FUNDED"
                bal = cap
                tdays = 0
                cycle_d = 0
                if first_pass_day is None:
                    first_pass_day = day_num
            elif stage == "FUNDED":
                cycle_d += 1
                if cycle_d >= 10:  # bi-weekly payout window
                    if not refunded:
                        # First payout: withdraw any profit above 0 + fee refund
                        if bal > cap + 1e-6:
                            payouts += (bal - cap) * 0.80 + (fee * 0.70 if is_5ers else fee)
                            refunded = True
                            if first_payout_day is None:
                                first_payout_day = day_num
                            bal = cap
                    else:
                        # Subsequent payouts: optionally keep `leave_buf` cushion inside account
                        withdraw_floor = cap + leave_buf
                        if bal > withdraw_floor + 1e-6:
                            payouts += (bal - withdraw_floor) * 0.80
                            bal = withdraw_floor
                    cycle_d = 0

        max_oop = max(max_oop, fees_spent - payouts)
        if day_num == 252:
            cf12 = payouts - fees_spent

    cf24 = payouts - fees_spent
    return {
        "first_pass_day": first_pass_day,
        "first_payout_day": first_payout_day,
        "breaches_p1": breaches_p1,
        "breaches_p2": breaches_p2,
        "breaches_funded": breaches_funded,
        "attempts": attempts,
        "cf12": float(cf12 if cf12 is not None else cf24),
        "cf24": float(cf24),
        "max_oop": float(max_oop),
    }


def evaluate_policy_mc(
    idx_matrix: np.ndarray,
    series_map: dict,
    *,
    firm: str,
    cap: float,
    fee: float,
    policy: dict,
) -> tuple[dict, list[dict]]:
    paths = [run_single_firm_path(idx_matrix[b], series_map, firm=firm, cap=cap, fee=fee, policy=policy) for b in range(len(idx_matrix))]
    n = len(paths)
    pass_days = [p["first_pass_day"] for p in paths if p["first_pass_day"] is not None]
    pay_days = [p["first_payout_day"] for p in paths if p["first_payout_day"] is not None]
    cf12 = np.array([p["cf12"] for p in paths])
    cf24 = np.array([p["cf24"] for p in paths])
    oop = np.array([p["max_oop"] for p in paths])

    pass_pct = {f"{m}m": round(100.0 * sum(1 for p in paths if p["first_pass_day"] is not None and p["first_pass_day"] <= m * 21) / n, 1) for m in (3, 6, 9, 12, 24)}
    funded_breach_rate = round(100.0 * sum(1 for p in paths if p["breaches_funded"] > 0) / max(1, len(pass_days)), 1)
    summary = {
        "pass_pct": pass_pct,
        "br1_pct": round(100.0 * sum(1 for p in paths if p["breaches_p1"] > 0) / n, 1),
        "br_funded_given_pass_pct": funded_breach_rate,
        "avg_tickets": round(float(np.mean([p["attempts"] for p in paths])), 2),
        "med_pass_m": round(float(np.median(pass_days)) / 21.0, 1) if pass_days else None,
        "med_first_payout_m": round(float(np.median(pay_days)) / 21.0, 1) if pay_days else None,
        "cf12_mean": round(float(cf12.mean()), 1),
        "cf24_mean": round(float(cf24.mean()), 1),
        "cf24_p05": round(float(np.percentile(cf24, 5)), 1),
        "cf24_med": round(float(np.median(cf24)), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24 > 0)), 1),
        "max_oop_p95": round(float(np.percentile(oop, 95)), 1),
    }
    return summary, paths


def simulate_self_funded_ladder(idx_matrix: np.ndarray, series_map: dict, policy: dict) -> dict:
    """Start ONLY with The5ers 5k ($39). Once cumulative The5ers payouts >= $168, launch FTMO 10k from profits!"""
    n = len(idx_matrix)
    cf12_arr, cf24_arr, oop_arr, f_launch_m = [], [], [], []
    for b in range(n):
        seq = idx_matrix[b]
        # Track day-by-day The5ers 5k; trigger FTMO 10k when net profit >= 168
        p5 = run_single_firm_path(seq, series_map, firm="THE5ERS_HS_5K", cap=5000.0, fee=39.0, policy=policy)
        # Approximate exact launch day by scanning first payout day + buffer if profitable
        launch_day = p5["first_payout_day"]
        if launch_day is not None and launch_day < 460:
            sub_seq = seq[launch_day:]
            # Pad to evaluate remaining horizon cleanly
            p_ftmo = run_single_firm_path(sub_seq, series_map, firm="FTMO_SWING_10K", cap=10000.0, fee=168.0, policy=policy)
            rem_days = len(sub_seq)
            ftmo_cf12 = p_ftmo["cf12"] if launch_day <= 252 else 0.0
            # Re-run exact truncation to 252-launch_day for cf12 accuracy
            if launch_day < 252:
                p_ftmo_12 = run_single_firm_path(seq[launch_day:252], series_map, firm="FTMO_SWING_10K", cap=10000.0, fee=168.0, policy=policy)
                ftmo_cf12 = p_ftmo_12["cf24"]
            else:
                ftmo_cf12 = 0.0
            cf12_arr.append(p5["cf12"] + ftmo_cf12)
            cf24_arr.append(p5["cf24"] + p_ftmo["cf24"])
            oop_arr.append(p5["max_oop"] + max(0.0, p_ftmo["max_oop"] - 168.0))
            f_launch_m.append(launch_day / 21.0)
        else:
            cf12_arr.append(p5["cf12"])
            cf24_arr.append(p5["cf24"])
            oop_arr.append(p5["max_oop"])
    cf12_np, cf24_np, oop_np = np.array(cf12_arr), np.array(cf24_arr), np.array(oop_arr)
    return {
        "ftmo_launched_pct": round(100.0 * len(f_launch_m) / n, 1),
        "med_ftmo_launch_m": round(float(np.median(f_launch_m)), 1) if f_launch_m else None,
        "cf12_mean": round(float(cf12_np.mean()), 1),
        "cf24_mean": round(float(cf24_np.mean()), 1),
        "cf24_p05": round(float(np.percentile(cf24_np, 5)), 1),
        "cf24_pos_pct": round(100.0 * float(np.mean(cf24_np > 0)), 1),
        "max_oop_p95": round(float(np.percentile(oop_np, 95)), 1),
    }


# ==============================================================================
# 4. MAIN ORCHESTRATOR
# ==============================================================================

def run_pass27(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, _ = profiles()
    swing_specs = specs["Swing"]
    ts_j, _, _, _, c_j = p19.load_sealed_bars(jobs_root, "USDJPY", "D1")
    usdjpy_close_map = {datetime.fromtimestamp(int(t), timezone.utc).date(): float(cv) for t, cv in zip(ts_j, c_j)}

    # Load sealed Native M1 Bid/Ask bundles for all 11 cross-asset instruments
    assets11 = ("USDJPY", "GBPUSD", "EURUSD", "GBPJPY", "AUDUSD", "USDCAD", "EURJPY", "XAUUSD", "US500", "US100", "GER40")
    bundles = {a: p24.build_unified_asset(a, jobs_root, cache_dir, swing_specs, usdjpy_close_map) for a in assets11}
    day_maps = {a: {d["day"]: d for d in bundles[a]["days"]} for a in assets11}
    all_days = sorted({d for dm in day_maps.values() for d in dm})

    # Build exact M1 minute-by-minute tapes for ALL 7 engines (E1..E5 Core + S6 + S7)
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    cluster_a_days = sorted(d for d in ref_days["strict"] if d < "2021-01-01")

    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, swing_specs["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, swing_specs["USDJPY"])
    exp_usd_05 = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)}
    gbp_vh_05_raw, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)
    gbp_vh_05 = {r["day"]: (r, t, m) for r, t, m in gbp_vh_05_raw}

    # Tag asset names on E1..E3 cleanly
    for eng_d, a_name in ((ref_trades, "USDJPY"), (exp_usd_05, "USDJPY"), (gbp_vh_05, "GBPUSD")):
        for _dk, (r, _t, _m) in eng_d.items():
            r["asset"] = a_name

    e4_us100 = build_us100_e4_tape(bundles["US100"])
    e5_us100 = build_us100_e5_tape(bundles, day_maps, all_days)
    assert len(e4_us100) == 414, f"E4 parity drift: {len(e4_us100)}"
    assert len(e5_us100) == 261, f"E5 parity drift: {len(e5_us100)}"
    s6_usdbsk = build_fx_usd_basket_s6_tape(bundles, day_maps, all_days)
    assert len(s6_usdbsk) == 195, f"S6 parity drift: {len(s6_usdbsk)}"
    s7_xau120 = build_xau_exp120_s7_tape(bundles["XAUUSD"])

    tapes = {
        "E1_USDJPY_TOKYO": ref_trades,
        "E2_USDJPY_EXP80": exp_usd_05,
        "E3_GBPUSD_VH": gbp_vh_05,
        "E4_US100_SESS40": e4_us100,
        "E5_US100_RS1130": e5_us100,
        "S6_FX_USD_BSK": s6_usdbsk,
        "S7_XAU_EXP120": s7_xau120,
    }

    # 1. US100 Overlap Forensics (E4 vs E5)
    us100_overlap = analyze_us100_overlap(e4_us100, e5_us100)
    print("\n=== TRACK A1: US100 ENGINE #4 vs ENGINE #5 OVERLAP FORENSICS ===", flush=True)
    print(f"  {us100_overlap}", flush=True)

    # 2. Cluster-A-only inverse-DD weights (zero lookahead!)
    a_dd_3 = {e: replay_multi_engine_m1(cluster_a_days, tapes, {e: 0.003}, 10000.0)[0]["peak_dd_pct"] for e in ("E1_USDJPY_TOKYO", "E2_USDJPY_EXP80")}
    inv2 = {e: (1.0 / a_dd_3[e]) / fsum(1.0 / v for v in a_dd_3.values()) for e in a_dd_3}
    base_3e = {**{e: 0.0075 * w for e, w in inv2.items()}, "E3_GBPUSD_VH": 0.0075}

    a_dd_5 = {e: max(0.25, replay_multi_engine_m1(cluster_a_days, tapes, {e: 0.005}, 10000.0)[0]["peak_dd_pct"]) for e in ("E1_USDJPY_TOKYO", "E2_USDJPY_EXP80", "E3_GBPUSD_VH", "E4_US100_SESS40", "E5_US100_RS1130")}
    inv5 = {e: (1.0 / a_dd_5[e]) / fsum(1.0 / v for v in a_dd_5.values()) for e in a_dd_5}
    # Match total risk sum (~2.50%) of PORT_5E_RAW
    tot_r5 = fsum(base_3e.values()) + 0.005 + 0.005
    weights_5e_invdd = {e: round(tot_r5 * w, 5) for e, w in inv5.items()}

    port_configs = {
        "PORT_3E_FROZEN": (base_3e, None),
        "PORT_4E": ({**base_3e, "E4_US100_SESS40": 0.0050}, None),
        "PORT_5E_RAW": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050}, None),
        "PORT_5E_US100_CAP75": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050}, 0.0075),
        "PORT_5E_US100_CAP50": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050}, 0.0050),
        "PORT_5E_INVDD_A": (weights_5e_invdd, 0.0075),
        "PORT_6E_SAT25": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050, "S6_FX_USD_BSK": 0.0025}, 0.0075),
        "PORT_6E_SAT50": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050, "S6_FX_USD_BSK": 0.0050}, 0.0075),
        "PORT_7E_P1_TURBO": ({**base_3e, "E4_US100_SESS40": 0.0050, "E5_US100_RS1130": 0.0050, "S6_FX_USD_BSK": 0.0050, "S7_XAU_EXP120": 0.0050}, 0.0075),
    }

    print("\n=== TRACK A2: EXACT MINUTE-BY-MINUTE M1 FLOATING-EQUITY PRAGUE-RESET PORTFOLIO AUDIT (SWING 10K, 2018-2024) ===", flush=True)
    m1_audit = {}
    daily_series = {}
    for pname, (rk, ucap) in port_configs.items():
        met_sw, led_sw = replay_multi_engine_m1(ext_days, tapes, rk, 10000.0, profile_mode="Swing", us100_same_dir_cap=ucap)
        met_st, _ = replay_multi_engine_m1(ext_days, tapes, rk, 10000.0, profile_mode="Standard", us100_same_dir_cap=ucap)
        m1_audit[pname] = {"swing_10k": met_sw, "standard_10k_margin_pct": met_st["peak_margin_pct"], "risks": rk, "us100_cap": ucap}
        _, n_arr, d_arr, f_arr = p23l.build_full_daily_series(ext_days, led_sw, 10000.0)
        daily_series[pname] = (n_arr, d_arr, f_arr)
        print(
            f"  {pname:21s} | Ann={met_sw['ann_pct']['all']:+5.2f}% (A={met_sw['ann_pct']['A']:+5.2f}%, B={met_sw['ann_pct']['B']:+5.2f}%) "
            f"| DailyDD={met_sw['daily_loss_pct']:4.2f}% | FloatPeakDD={met_sw['peak_dd_pct']:4.2f}% | Calmar={met_sw['calmar']:4.2f} "
            f"| UW={met_sw['underwater_months']:4.1f}m | MaxConc={met_sw['max_concurrent_positions']} | MgnSw={met_sw['peak_margin_pct']:4.1f}%/Std={met_st['peak_margin_pct']:4.1f}% "
            f"| CapHit={met_sw['us100_cap_activations']} | MgnFail={met_sw['margin_failures']}",
            flush=True,
        )

    # 3. TRACK B: EMPIRICAL PHASE-BASED PROP PROFILE ARCHITECTURE BENCHMARK (N=2,000 BOOTSTRAP)
    idx_matrix = _draw_bootstrap_indices(len(ext_days), horizon=504, n_paths=BOOTSTRAP_PATHS, seed=SEED)
    policies = {
        "A_FLAT_CORE5": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_5E_US100_CAP75",
            "p1_mult": 1.0, "p2_mult": 1.0, "funded_mult": 1.0, "dynamic_dd": False, "glidepath": False, "funded_survival": False,
        },
        "B_2REGIME_PURE_SCALE_2X": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_5E_US100_CAP75",
            "p1_mult": 2.0, "p2_mult": 1.25, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": False, "funded_survival": False,
        },
        "B2_2REGIME_FAST_25X": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_5E_US100_CAP75",
            "p1_mult": 2.5, "p2_mult": 1.40, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": False, "funded_survival": False,
        },
        "C_2PROF_P1_6E_2X_THEN_5E": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_6E_SAT50",
            "p1_mult": 2.0, "p2_mult": 1.25, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": False, "funded_survival": False,
        },
        "D_2PROF_P1_7E_2X_THEN_5E": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_7E_P1_TURBO",
            "p1_mult": 2.0, "p2_mult": 1.25, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": False, "funded_survival": False,
        },
        "E_GLIDEPATH_FAST_25X_5E": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_5E_US100_CAP75",
            "p1_mult": 2.5, "p2_mult": 1.40, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": True, "funded_survival": False,
        },
        "F_4STATE_7E_2X_TO_5E": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_7E_P1_TURBO",
            "p1_mult": 2.0, "p2_mult": 1.25, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": True, "funded_survival": True,
        },
        "G_4STATE_FUNDED_2PCT_BUF": {
            "core_key": "PORT_5E_US100_CAP75", "p1_key": "PORT_7E_P1_TURBO",
            "p1_mult": 2.0, "p2_mult": 1.25, "funded_mult": 1.0, "dynamic_dd": True, "glidepath": True, "funded_survival": True,
            "funded_keep_buffer_pct": 0.02,
        },
    }

    print("\n=== TRACK B: PHASE-BASED PROP PROFILE ARCHITECTURE BENCHMARK (EXACT M1 LEDGERS, N=2,000) ===", flush=True)
    phase_results = {}
    cached_paths = {}
    for pol_name, pol in policies.items():
        phase_results[pol_name] = {}
        print(f"\n  [{pol_name}]", flush=True)
        for firm, cap, fee in (("FTMO_SWING_10K", 10000.0, 168.0), ("THE5ERS_HS_5K", 5000.0, 39.0)):
            summ, paths = evaluate_policy_mc(idx_matrix, daily_series, firm=firm, cap=cap, fee=fee, policy=pol)
            phase_results[pol_name][firm] = summ
            cached_paths[(pol_name, firm)] = paths
            pp = summ["pass_pct"]
            print(
                f"    {firm:14s} | 3/6/9/12/24m={pp['3m']:4.1f}/{pp['6m']:4.1f}/{pp['9m']:4.1f}/{pp['12m']:4.1f}/{pp['24m']:4.1f}% "
                f"| Br1={summ['br1_pct']:4.1f}% BrF={summ['br_funded_given_pass_pct']:4.1f}% Tix={summ['avg_tickets']:.2f} "
                f"| MedPass={str(summ['med_pass_m']):>4s}m Pay1={str(summ['med_first_payout_m']):>4s}m "
                f"| CF12=${summ['cf12_mean']:+5.0f} CF24=${summ['cf24_mean']:+6.0f} (P05=${summ['cf24_p05']:+5.0f}, P>0={summ['cf24_pos_pct']:4.1f}%) OOP95=${summ['max_oop_p95']:.0f}",
                flush=True,
            )

    # H. Synchronized Dual-Firm Parallel Ladder vs Self-Funded Ladder (on identical market paths!)
    dual_firm_parallel = {}
    for pol_key in ("B2_2REGIME_FAST_25X", "D_2PROF_P1_7E_2X_THEN_5E", "F_4STATE_7E_2X_TO_5E"):
        ftmo_f = cached_paths[(pol_key, "FTMO_SWING_10K")]
        t5_f = cached_paths[(pol_key, "THE5ERS_HS_5K")]
        par_cf12 = np.array([a["cf12"] + b["cf12"] for a, b in zip(ftmo_f, t5_f)])
        par_cf24 = np.array([a["cf24"] + b["cf24"] for a, b in zip(ftmo_f, t5_f)])
        par_oop = np.array([a["max_oop"] + b["max_oop"] for a, b in zip(ftmo_f, t5_f)])
        either_pay = [min(x for x in (a["first_payout_day"], b["first_payout_day"]) if x is not None)
                      for a, b in zip(ftmo_f, t5_f) if (a["first_payout_day"] is not None or b["first_payout_day"] is not None)]
        dual_firm_parallel[pol_key] = {
            "cf12_mean": round(float(par_cf12.mean()), 1),
            "cf24_mean": round(float(par_cf24.mean()), 1),
            "cf24_p05": round(float(np.percentile(par_cf24, 5)), 1),
            "cf24_pos_pct": round(100.0 * float(np.mean(par_cf24 > 0)), 1),
            "max_oop_p95": round(float(np.percentile(par_oop, 95)), 1),
            "either_first_payout_med_m": round(float(np.median(either_pay)) / 21.0, 1) if either_pay else None,
            "either_payout_24m_pct": round(100.0 * len(either_pay) / len(ftmo_f), 1),
        }
    parallel_dual = dual_firm_parallel
    self_funded = simulate_self_funded_ladder(idx_matrix, daily_series, policies["D_2PROF_P1_7E_2X_THEN_5E"])
    print("\n=== TRACK B2: DUAL-FIRM MULTI-ACCOUNT ARCHITECTURE (SYNCHRONIZED REAL TIMELINE) ===", flush=True)
    for k, v in parallel_dual.items():
        print(f"  H_PARALLEL[{k:24s}]: {v}", flush=True)
    print(f"  I_5ERS5K_FIRST_SELF_FUND_FTMO      : {self_funded}", flush=True)

    demo_sha = sha(DEMO_SPEC_ARTIFACT) if DEMO_SPEC_ARTIFACT.exists() else "UNAVAILABLE"
    return {
        "pass": "Pass 27 (Bound FTMO Demo Specs, Exact M1 Floating-Equity Audit & Phase-Based Prop Profiles)",
        "protocol_commit": PROTOCOL,
        "demo_spec_sha256": demo_sha,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "us100_overlap": us100_overlap,
        "cluster_a_invdd_5e_weights": weights_5e_invdd,
        "m1_floating_audit": m1_audit,
        "phase_profile_benchmark": phase_results,
        "dual_firm_parallel": parallel_dual,
        "dual_firm_self_funded_ladder": self_funded,
        "elapsed_seconds": round(time.monotonic() - t0, 2),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass27(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass27-result.json", res)
    print("\nPASS27_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
