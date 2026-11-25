"""Pass 23 Lane B (Nhip 3): FTMO 2-Step Challenge Lifecycle, Block Bootstrap & Reward Cashflow Simulator.

Built strictly on exact Prague-reset M1 floating-equity daily ledgers (Development 2018-2024, holdout_rows = 0).
"""

import argparse
from collections import Counter
from datetime import date, datetime, timezone
from math import fsum
from pathlib import Path
import time

import numpy as np

import hot_m1_cache as hcache
import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as core
import pass11_portfolio as portfolio
import pass14_intel_top15_batch as p14
import pass17_usdjpy_forensic_cross as p17
import pass22_gbpusd_volhigh_3engine as p22
from pass7b_usdjpy_research import load_m1
from pass8_usdjpy_gaps import replayable, shape
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from quant_core.ftmo_track_replay import profiles

PROTOCOL = "5eb0506089d12ffbd047a8eab1871cc618f4850c"
SEED = 20261123
BOOTSTRAP_PATHS = 2000
BLOCK_DAYS = 5
TRADING_DAYS_PER_MONTH = 21.0
TRADING_DAYS_PER_PAYOUT = 10  # 14 calendar days ~= 10 trading days

# Declared FTMO public fee table (EUR converted conservatively at 1.08 USD/EUR; marked FTMO_PUBLIC_FEE_DECLARED)
FTMO_FEES_USD = {
    ("Swing", 10000): 168.0,
    ("Swing", 25000): 270.0,
    ("Standard", 50000): 373.0,
}


def build_usdjpy_tokyo_with_addon(jobs: Path, addon: float) -> dict:
    """Re-replay frozen USDJPY Tokyo-box exact M1 trades with an arbitrary slippage addon (e.g. 0.01 = +1.0 pip)."""
    parent = "pass7b-usdjpy-qdm-equity-20261120"
    relatives = ["development-m1/manifest.json", "verified/result.json", "verified/m1-coverage-gaps.json"]
    paths = portfolio.manifest_files(jobs, parent, relatives)
    manifest, _report, gaps = (read(paths[name]) for name in relatives)
    known = {r["day"]: r for r in gaps["native_h1_missing_m1_days"]}
    trades = {}
    for year in clock.YEAR:
        times, values = load_m1(paths[relatives[0]].parent, manifest["years"][str(year)], year)
        for day in range(START, STOP, clock.DAY):
            utc = clock.date(day)
            if utc.year != year or utc.weekday() >= 5:
                continue
            day_key = utc.date().isoformat()
            flat = (clock.hard_flat(utc) - day) // 60
            lo, hi = times.searchsorted([day, day + (flat + 1) * 60])
            offsets = (times[lo:hi] - day) // 60
            prices = values[lo:hi, :8]
            strict = np.array_equal(offsets, np.arange(flat + 1))
            if strict:
                trade, _ = core.select(day, prices)
            elif day_key in known:
                missing, gap = shape(day, offsets, prices, flat)
                if not gap["compatible"]:
                    continue
                trade, _ = core.select(day, prices, offsets=offsets)
                if not replayable(missing, offsets, prices, trade):
                    continue
            else:
                continue
            if trade is None:
                continue
            row = core.record(trade, addon)
            stamps = np.array([trade.second_at(i) for i in range(trade.entry, trade.execution.index + 1)])
            assert START <= stamps[0] <= stamps[-1] < STOP
            trades[day_key] = ({**row, "at_open": trade.execution.at_open}, stamps, core.path(trade, addon))
    return trades


def build_full_daily_series(all_days_sorted: list[str], ledger: list[dict], initial: float) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Convert sparse trade-day ledger into complete trading-day arrays: (days, net_usd, worst_dd_usd, traded_flag)."""
    by_day = {}
    prev_cash = float(initial)
    for row in ledger:
        d = row["day"]
        net = float(row["net_usd"])
        dd_from_open = max(0.0, prev_cash - float(row["day_equity_minimum"]))
        traded = 1 if any(o["status"] == "SIZED" for o in row["orders"]) else 0
        by_day[d] = (net, dd_from_open, traded)
        prev_cash = float(row["cash"])
    n = len(all_days_sorted)
    nets = np.zeros(n, dtype=np.float64)
    dds = np.zeros(n, dtype=np.float64)
    flags = np.zeros(n, dtype=np.int8)
    for i, d in enumerate(all_days_sorted):
        if d in by_day:
            nets[i], dds[i], flags[i] = by_day[d]
    return all_days_sorted, nets, dds, flags


def simulate_two_step_path(
    nets: np.ndarray,
    dds: np.ndarray,
    flags: np.ndarray,
    initial: float,
    *,
    p1_target_pct: float = 0.10,
    p2_target_pct: float = 0.05,
    daily_limit_pct: float = 0.05,
    static_limit_pct: float = 0.10,
    min_days: int = 4,
) -> dict:
    """Simulate a single FTMO 2-Step attempt (Phase 1 -> Phase 2) with exact daily & static breach checks."""
    p1_goal = initial * (1.0 + p1_target_pct)
    p2_goal = initial * (1.0 + p2_target_pct)
    daily_cap = initial * daily_limit_pct
    static_floor = initial * (1.0 - static_limit_pct)

    phase = 1
    bal = float(initial)
    tdays = 0
    p1_pass_day = None

    for idx in range(len(nets)):
        eq_low = bal - dds[idx]
        # Conservative breach ordering: daily and static losses checked BEFORE end-of-day profit target
        if dds[idx] >= daily_cap - 1e-9:
            return {"outcome": f"BREACH_DAILY_P{phase}", "breached": True, "p1_passed": phase == 2, "p2_passed": False, "pass_day": None, "p1_day": p1_pass_day}
        if eq_low <= static_floor + 1e-9:
            return {"outcome": f"BREACH_STATIC_P{phase}", "breached": True, "p1_passed": phase == 2, "p2_passed": False, "pass_day": None, "p1_day": p1_pass_day}
        bal += nets[idx]
        if flags[idx]:
            tdays += 1
        if phase == 1 and bal >= p1_goal - 1e-9 and tdays >= min_days:
            phase = 2
            p1_pass_day = idx + 1
            bal = float(initial)
            tdays = 0
        elif phase == 2 and bal >= p2_goal - 1e-9 and tdays >= min_days:
            return {"outcome": "PASSED_2STEP", "breached": False, "p1_passed": True, "p2_passed": True, "pass_day": idx + 1, "p1_day": p1_pass_day}

    return {
        "outcome": "CENSORED_P2" if phase == 2 else "CENSORED_P1",
        "breached": False, "p1_passed": phase == 2, "p2_passed": False,
        "pass_day": None, "p1_day": p1_pass_day,
    }


def simulate_continuous_lifecycle(
    nets: np.ndarray,
    dds: np.ndarray,
    flags: np.ndarray,
    initial: float,
    fee_usd: float,
    *,
    horizon_days: int = 504,  # 24 months
    max_retries: int = 3,
    profit_split: float = 0.80,
) -> dict:
    """Simulate a solo operator over `horizon_days` (Phase 1 -> Phase 2 -> Funded bi-weekly payouts, retries on breach)."""
    p1_goal = initial * 1.10
    p2_goal = initial * 1.05
    daily_cap = initial * 0.05
    static_floor = initial * 0.90

    stage = "P1"
    bal = float(initial)
    tdays = 0
    attempts = 1
    fees_spent = float(fee_usd)
    refunded = False
    payouts_total = 0.0
    payout_cycles = 0
    zero_payout_cycles = 0
    funded_days = 0
    breaches = 0
    cycle_days = 0
    first_payout_day = None
    stopped_out = False

    n = min(len(nets), horizon_days)
    for idx in range(n):
        if stopped_out:
            break
        eq_low = bal - dds[idx]
        if dds[idx] >= daily_cap - 1e-9 or eq_low <= static_floor + 1e-9:
            breaches += 1
            if attempts <= max_retries:
                attempts += 1
                fees_spent += fee_usd
                stage = "P1"
                bal = float(initial)
                tdays = 0
                refunded = False
                cycle_days = 0
            else:
                stopped_out = True
            continue

        bal += nets[idx]
        if flags[idx]:
            tdays += 1

        if stage == "P1":
            if bal >= p1_goal - 1e-9 and tdays >= 4:
                stage = "P2"
                bal = float(initial)
                tdays = 0
        elif stage == "P2":
            if bal >= p2_goal - 1e-9 and tdays >= 4:
                stage = "FUNDED"
                bal = float(initial)
                tdays = 0
                cycle_days = 0
        else:
            funded_days += 1
            cycle_days += 1
            if cycle_days >= TRADING_DAYS_PER_PAYOUT:
                payout_cycles += 1
                if bal > initial + 1e-6:
                    profit = bal - initial
                    pay = profit * profit_split
                    if not refunded:
                        pay += fee_usd
                        refunded = True
                    payouts_total += pay
                    if first_payout_day is None:
                        first_payout_day = idx + 1
                    bal = float(initial)
                else:
                    zero_payout_cycles += 1
                cycle_days = 0

    net_cashflow = payouts_total - fees_spent
    return {
        "net_cashflow_usd": net_cashflow,
        "payouts_total_usd": payouts_total,
        "fees_spent_usd": fees_spent,
        "attempts": attempts,
        "breaches": breaches,
        "funded_days": funded_days,
        "payout_cycles": payout_cycles,
        "zero_payout_cycles": zero_payout_cycles,
        "first_payout_months": (first_payout_day / TRADING_DAYS_PER_MONTH) if first_payout_day is not None else None,
        "reached_funded": funded_days > 0,
        "stopped_out": stopped_out,
    }


def rolling_historical_windows(days: list[str], nets: np.ndarray, dds: np.ndarray, flags: np.ndarray, initial: float) -> dict:
    """Evaluate every monthly historical start date across 6/12/18/24/36-month horizons (keeping censored windows)."""
    # Find first trading index of each YYYY-MM
    month_starts = []
    seen = set()
    for i, d in enumerate(days):
        ym = d[:7]
        if ym not in seen:
            seen.add(ym)
            month_starts.append((ym, i))

    out = {}
    for months in (6, 12, 18, 24, 36):
        h_days = int(round(months * TRADING_DAYS_PER_MONTH))
        eligible_starts = [(ym, i) for ym, i in month_starts if i + h_days <= len(nets)]
        if not eligible_starts:
            out[f"{months}m"] = {"windows": 0}
            continue
        passed = p1_ok = breached = 0
        pass_months = []
        for _ym, i in eligible_starts:
            r = simulate_two_step_path(nets[i:i + h_days], dds[i:i + h_days], flags[i:i + h_days], initial)
            if r["p2_passed"]:
                passed += 1
                pass_months.append(r["pass_day"] / TRADING_DAYS_PER_MONTH)
            if r["p1_passed"]:
                p1_ok += 1
            if r["breached"]:
                breached += 1
        w = len(eligible_starts)
        out[f"{months}m"] = {
            "windows": w,
            "p1_pass_pct": round(100.0 * p1_ok / w, 1),
            "two_step_pass_pct": round(100.0 * passed / w, 1),
            "breach_pct": round(100.0 * breached / w, 1),
            "censored_pct": round(100.0 * (w - passed - breached) / w, 1),
            "median_pass_months_cond": round(float(np.median(pass_months)), 1) if pass_months else None,
        }
    return out


def block_bootstrap_lifecycle(
    nets: np.ndarray,
    dds: np.ndarray,
    flags: np.ndarray,
    initial: float,
    fee_usd: float,
    *,
    n_paths: int = BOOTSTRAP_PATHS,
    block_len: int = BLOCK_DAYS,
    seed: int = SEED,
) -> dict:
    """Circular 5-day block bootstrap for 2-Step pass probabilities (6/12/18/24m) and 24m solo-operator cashflow."""
    rng = np.random.default_rng(seed)
    n_obs = len(nets)
    max_h = int(round(24 * TRADING_DAYS_PER_MONTH))  # 504 trading days
    n_blocks = (max_h + block_len - 1) // block_len

    horizons = {6: 126, 12: 252, 18: 378, 24: 504}
    pass_counts = {m: 0 for m in horizons}
    p1_counts = {m: 0 for m in horizons}
    breach_daily = {m: 0 for m in horizons}
    breach_static = {m: 0 for m in horizons}
    pass_days_24 = []

    cf_list, fees_list, zero_ratios, first_pay_m = [], [], [], []
    funded_cnt = profit_cnt = stopped_cnt = 0

    for _ in range(n_paths):
        starts = rng.integers(0, n_obs, size=n_blocks)
        idxs = (starts[:, None] + np.arange(block_len)[None, :]).ravel()[:max_h] % n_obs
        sn, sd, sf = nets[idxs], dds[idxs], flags[idxs]

        # Single-attempt 2-Step over full 24m path, then score at 6/12/18/24m checkpoints
        r24 = simulate_two_step_path(sn, sd, sf, initial)
        if r24["p2_passed"]:
            pass_days_24.append(r24["pass_day"] / TRADING_DAYS_PER_MONTH)
        for m, h in horizons.items():
            rm = simulate_two_step_path(sn[:h], sd[:h], sf[:h], initial)
            if rm["p2_passed"]:
                pass_counts[m] += 1
            if rm["p1_passed"]:
                p1_counts[m] += 1
            if rm["outcome"].startswith("BREACH_DAILY"):
                breach_daily[m] += 1
            elif rm["outcome"].startswith("BREACH_STATIC"):
                breach_static[m] += 1

        # 24m continuous operator cashflow
        cf = simulate_continuous_lifecycle(sn, sd, sf, initial, fee_usd, horizon_days=max_h, max_retries=3)
        cf_list.append(cf["net_cashflow_usd"])
        fees_list.append(cf["fees_spent_usd"])
        if cf["reached_funded"]:
            funded_cnt += 1
        if cf["net_cashflow_usd"] > 0:
            profit_cnt += 1
        if cf["stopped_out"]:
            stopped_cnt += 1
        if cf["payout_cycles"] > 0:
            zero_ratios.append(100.0 * cf["zero_payout_cycles"] / cf["payout_cycles"])
        if cf["first_payout_months"] is not None:
            first_pay_m.append(cf["first_payout_months"])

    cf_arr = np.array(cf_list, dtype=np.float64)
    return {
        "paths": n_paths,
        "block_days": block_len,
        "horizons": {
            f"{m}m": {
                "p1_pass_pct": round(100.0 * p1_counts[m] / n_paths, 1),
                "two_step_pass_pct": round(100.0 * pass_counts[m] / n_paths, 1),
                "breach_daily_pct": round(100.0 * breach_daily[m] / n_paths, 1),
                "breach_static_pct": round(100.0 * breach_static[m] / n_paths, 1),
                "breach_total_pct": round(100.0 * (breach_daily[m] + breach_static[m]) / n_paths, 1),
            }
            for m in horizons
        },
        "pass_time_months_cond_24m": {
            "median": round(float(np.median(pass_days_24)), 1) if pass_days_24 else None,
            "p75": round(float(np.percentile(pass_days_24, 75)), 1) if pass_days_24 else None,
        },
        "cashflow_24m_with_retries": {
            "fee_usd_declared": fee_usd,
            "reached_funded_pct": round(100.0 * funded_cnt / n_paths, 1),
            "net_profitable_pct": round(100.0 * profit_cnt / n_paths, 1),
            "stopped_out_3retries_pct": round(100.0 * stopped_cnt / n_paths, 1),
            "mean_net_usd": round(float(cf_arr.mean()), 1),
            "p25_net_usd": round(float(np.percentile(cf_arr, 25)), 1),
            "median_net_usd": round(float(np.median(cf_arr)), 1),
            "p75_net_usd": round(float(np.percentile(cf_arr, 75)), 1),
            "mean_fees_spent_usd": round(float(np.mean(fees_list)), 1),
            "mean_zero_payout_cycle_pct": round(float(np.mean(zero_ratios)), 1) if zero_ratios else 100.0,
            "median_first_payout_months": round(float(np.median(first_pay_m)), 1) if first_pay_m else None,
        },
    }


def run_pass23_lifecycle(jobs_root: Path, cache_dir: Path) -> dict:
    t0 = time.monotonic()
    if sha(ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")

    specs, bindings = profiles()
    gbp_ctx = p14.build_asset_context(jobs_root, "GBPUSD", cache_dir, specs["Swing"]["GBPUSD"])
    jpy_ctx = p14.build_asset_context(jobs_root, "USDJPY", cache_dir, specs["Swing"]["USDJPY"])
    ref_trades, ref_days = portfolio.frozen_usdjpy(jobs_root)
    ext_days = sorted(ref_days["extended"])
    cluster_a = {d for d in ref_days["strict"] if d < "2021-01-01"}

    # Build exact Stress +0.50 pip tapes (baseline Pass 22)
    exp_usd_05 = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.005)}
    gbp_vh_05_raw, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=0.50)
    gbp_vh_05 = {r["day"]: (r, t, m) for r, t, m in gbp_vh_05_raw}
    tapes_05 = {"USDJPY": ref_trades, p17.USDJPY_EXP: exp_usd_05, p22.GBPUSD_VH: gbp_vh_05}

    # Build exact Stress +1.00 pip tapes (all 3 engines stressed simultaneously!)
    ref_trades_10 = build_usdjpy_tokyo_with_addon(jobs_root, 0.01)
    exp_usd_10 = {r["day"]: (r, t, m) for r, t, m in p17.build_usdjpy_exp_tape(jpy_ctx, trig_atr=0.80, sl_atr=0.75, addon=0.010)}
    gbp_vh_10_raw, _ = p22.build_gbpusd_volhigh_tape(gbp_ctx, trig_atr=0.80, sl_atr=0.75, vol_mult=1.10, addon_pips=1.00)
    gbp_vh_10 = {r["day"]: (r, t, m) for r, t, m in gbp_vh_10_raw}
    tapes_10 = {"USDJPY": ref_trades_10, p17.USDJPY_EXP: exp_usd_10, p22.GBPUSD_VH: gbp_vh_10}

    specs_ext = {prof: {**sp, p17.USDJPY_EXP: sp["USDJPY"], p22.GBPUSD_VH: sp["GBPUSD"]} for prof, sp in specs.items()}

    # Exact Cluster-A inverse-DD weights (identical to Pass 22)
    a_dd_2 = {
        s: portfolio.replay(cluster_a, tapes_05, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP)
    }
    inv2 = {s: (1.0 / a_dd_2[s]) / fsum(1.0 / v for v in a_dd_2.values()) for s in a_dd_2}
    core_075 = {s: 0.0075 * w for s, w in inv2.items()}

    a_dd_3 = {
        s: portfolio.replay(cluster_a, tapes_05, {s: 0.003}, 10000, specs_ext["Swing"])[0]["peak_dd_pct"]
        for s in ("USDJPY", p17.USDJPY_EXP, p22.GBPUSD_VH)
    }
    inv3 = {s: (1.0 / a_dd_3[s]) / fsum(1.0 / v for v in a_dd_3.values()) for s in a_dd_3}

    p3_bal = {**core_075, p22.GBPUSD_VH: 0.0075}
    configs = [
        ("SOLO_USDJPY_030", {"USDJPY": 0.0030}, tapes_05),
        ("BASE_2E_USDJPY_075", core_075, tapes_05),
        ("PORT3E_INVDD_125", {s: 0.0125 * w for s, w in inv3.items()}, tapes_05),
        ("PORT3E_075_GBP075", p3_bal, tapes_05),
        ("PORT3E_075_GBP075_X125", {s: v * 1.25 for s, v in p3_bal.items()}, tapes_05),
        ("PORT3E_075_GBP075_X150", {s: v * 1.50 for s, v in p3_bal.items()}, tapes_05),
        ("PORT3E_075_GBP075_STRESS10", p3_bal, tapes_10),
    ]

    results = {}
    print("\n=== PASS 23 LANE B (NHIP 3): FTMO 2-STEP LIFECYCLE & REWARD CASHFLOW (N=2,000 BLOCK BOOTSTRAP + ROLLING WINDOWS) ===", flush=True)
    for prof, cap in (("Swing", 10000), ("Swing", 25000), ("Standard", 50000)):
        bkey = f"{prof}_{cap}"
        fee = FTMO_FEES_USD[(prof, cap)]
        results[bkey] = {}
        print(f"\n--- {bkey} (Declared Fee: ${fee:.0f}) ---", flush=True)
        for cname, rmap, t_use in configs:
            m, ledger = portfolio.replay(ext_days, t_use, rmap, cap, specs_ext[prof])
            m["calmar"] = round(m["annual_pct"]["all"] / m["peak_dd_pct"], 2) if m["peak_dd_pct"] > 1e-9 else 0.0
            d_list, nets, dds, flags = build_full_daily_series(ext_days, ledger, cap)
            roll = rolling_historical_windows(d_list, nets, dds, flags, cap)
            boot = block_bootstrap_lifecycle(nets, dds, flags, cap, fee)
            results[bkey][cname] = {"replay_7y": m, "rolling_windows": roll, "bootstrap_2000": boot}

            h12, h24 = boot["horizons"]["12m"], boot["horizons"]["24m"]
            r12, r24 = roll["12m"], roll["24m"]
            cf = boot["cashflow_24m_with_retries"]
            print(
                f"  {cname:26s} | ann={m['annual_pct']['all']:+5.2f}% peakDD={m['peak_dd_pct']:5.2f}% dly={m['daily_loss_pct']:4.2f}% cal={m['calmar']:4.2f} "
                f"| Roll12={r12['two_step_pass_pct']:4.1f}% Roll24={r24['two_step_pass_pct']:4.1f}% "
                f"| Boot12={h12['two_step_pass_pct']:4.1f}% Boot24={h24['two_step_pass_pct']:4.1f}% Br24={h24['breach_total_pct']:4.1f}% "
                f"| 24mCF med=${cf['median_net_usd']:+6.0f} (P>0={cf['net_profitable_pct']:4.1f}%, 0pay={cf['mean_zero_payout_cycle_pct']:4.1f}%)",
                flush=True,
            )

    return {
        "pass": "Pass 23 Lane B (Nhip 3 FTMO 2-Step Lifecycle)",
        "protocol_commit": PROTOCOL,
        "holdout_lock_sha256": clock.LOCK_SHA,
        "holdout_rows": 0,
        "order_send_count": 0,
        "spec_bindings": bindings,
        "fee_source": "FTMO_PUBLIC_FEE_DECLARED",
        "elapsed_seconds": round(time.monotonic() - t0, 2),
        "books": results,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=hcache.DEFAULT_JOBS)
    parser.add_argument("--cache", type=Path, default=hcache.DEFAULT_CACHE)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    res = run_pass23_lifecycle(args.jobs, args.cache)
    args.output.mkdir(parents=True, exist_ok=True)
    write(args.output / "pass23-lifecycle-result.json", res)
    print("\nPASS23_LANE_B_LIFECYCLE_COMPLETE", flush=True)


if __name__ == "__main__":
    main()
