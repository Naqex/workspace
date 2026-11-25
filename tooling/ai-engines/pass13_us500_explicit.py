"""Pass 13 Track 3: US500 NY ORB on sealed direct-Dukascopy Explicit M1 Bid/Ask (2018-2024)."""

import argparse
from collections import Counter, defaultdict
from math import fsum
from pathlib import Path
from statistics import mean, median

import numpy as np

import pass5_usdjpy_tokyo as clock
import pass11_portfolio as portfolio
import pass12_us500_ny_orb as orb
from native_ftmo_monfri_seal import START, STOP, read, sha, write
from quant_core.ftmo_track_replay import commission, profiles

PROTOCOL = "62ef31363604fc4588f0cb4d7a699efd80737cde"
SEED = 20261123
MC_DRAWS = 1000


def year_root(jobs_root: Path, year: int) -> Path:
    base = jobs_root / "challenge-discovery4-20261108" / "execution-v1"
    folder = "us500-long-explicit-source-v1" if year <= 2021 else "us500-explicit-source-v1"
    return base / folder / str(year)


def load_explicit_year(jobs_root: Path, year: int):
    """Load and SHA-verify paired Explicit M1 Bid/Ask JSONs for a single Development year."""
    if year not in clock.YEAR:
        raise ValueError(f"Holdout or unregistered year blocked: {year}")
    root = year_root(jobs_root, year)
    seals = []
    ts_parts, q_parts = [], []
    lo_ms = int(clock.datetime(year, 1, 1, tzinfo=clock.timezone.utc).timestamp() * 1000)
    hi_ms = int(clock.datetime(year + 1, 1, 1, tzinfo=clock.timezone.utc).timestamp() * 1000)
    assert lo_ms >= START * 1000 and hi_ms <= STOP * 1000

    for q in range(1, 5):
        bid_path = root / f"q{q}-bid.json"
        ask_path = root / f"q{q}-ask.json"
        bid_seal = read(root / f"q{q}-bid-seal.json")
        ask_seal = read(root / f"q{q}-ask-seal.json")
        if sha(bid_path) != bid_seal["sha256"] or sha(ask_path) != ask_seal["sha256"]:
            raise ValueError(f"US500 explicit seal SHA mismatch: {year} Q{q}")
        bids = read(bid_path)
        asks = read(ask_path)
        if len(bids) != bid_seal["rows"] or len(asks) != ask_seal["rows"] or len(bids) != len(asks):
            raise ValueError(f"US500 explicit row count mismatch: {year} Q{q}")
        if not bids:
            continue
        b_ts = np.fromiter((int(r["timestamp"]) for r in bids), dtype=np.int64, count=len(bids))
        a_ts = np.fromiter((int(r["timestamp"]) for r in asks), dtype=np.int64, count=len(asks))
        if not np.array_equal(b_ts, a_ts):
            raise ValueError(f"US500 bid/ask timestamps unpaired: {year} Q{q}")
        if int(b_ts[0]) < lo_ms or int(b_ts[-1]) >= hi_ms or (b_ts % 60000 != 0).any():
            raise ValueError(f"US500 timestamps outside Development year {year}")
        mat = np.empty((len(bids), 8), dtype=np.float64)
        for idx, key in enumerate(("open", "high", "low", "close")):
            mat[:, idx] = [float(r[key]) for r in bids]
            mat[:, idx + 4] = [float(r[key]) for r in asks]
        if (mat[:, 4] < mat[:, 0] - 1e-9).any():
            raise ValueError(f"Crossed explicit Bid/Ask open in {year} Q{q}")
        ts_parts.append(b_ts // 1000)
        q_parts.append(mat)
        seals.append({"quarter": q, "rows": len(bids), "bid_sha256": bid_seal["sha256"], "ask_sha256": ask_seal["sha256"]})

    times = np.concatenate(ts_parts)
    quotes = np.vstack(q_parts)
    if (np.diff(times) <= 0).any():
        raise ValueError(f"US500 explicit timestamps not strictly increasing in {year}")
    assert START <= int(times[0]) <= int(times[-1]) < STOP
    return times, quotes, {"year": year, "source_dir": root.parent.name, "minutes": int(len(times)),
                           "first_second": int(times[0]), "last_second": int(times[-1]), "quarters": seals}


def mc_random_entry_null(events, slip: float, *, draws: int = MC_DRAWS, seed: int = SEED):
    """Random-entry null test on exact same eligible trading days, random minute in [60, CANCEL), random side."""
    if not events:
        return None
    rng = np.random.default_rng(seed)
    day_pools = []
    obs_breakout = 0.0
    obs_fade = 0.0
    for day, start, offsets, quotes, signal in events:
        idx = signal["entry_idx"]
        side = signal["side"]
        entry = signal["entry_price"]
        spread = signal["entry_spread"]
        flat_j = int(offsets.searchsorted(orb.FLAT))
        if flat_j >= len(offsets) or offsets[flat_j] != orb.FLAT:
            continue
        out_bid, out_ask = float(quotes[flat_j, 0]), float(quotes[flat_j, 4])
        obs_breakout += side * ((out_bid if side == 1 else out_ask) - entry) - 2.0 * slip
        obs_fade += -side * ((out_ask if side == 1 else out_bid) - (entry - side * spread)) - 2.0 * slip

        a, b = offsets.searchsorted([60, orb.CANCEL])
        if b <= a:
            continue
        sub = quotes[a:b]
        # Precompute BUY and SELL net PnL to hard_flat from every minute in [60, CANCEL)
        buy_pnl = (out_bid - sub[:, 4]) - 2.0 * slip
        sell_pnl = (sub[:, 0] - out_ask) - 2.0 * slip
        day_pools.append(np.concatenate([buy_pnl, sell_pnl]))

    if not day_pools:
        return None
    totals = np.zeros(draws, dtype=np.float64)
    for pool in day_pools:
        picks = rng.integers(0, len(pool), size=draws)
        totals += pool[picks]

    return {
        "n_days": len(day_pools),
        "draws": draws,
        "seed": seed,
        "slip_per_side": slip,
        "observed_breakout_net_pts": float(obs_breakout),
        "observed_fade_net_pts": float(obs_fade),
        "null_mean_pts": float(totals.mean()),
        "null_std_pts": float(totals.std(ddof=1)),
        "null_p50_pts": float(np.percentile(totals, 50)),
        "null_p95_pts": float(np.percentile(totals, 95)),
        "breakout_p_value": float((np.sum(totals >= obs_breakout) + 1) / (draws + 1)),
        "fade_p_value": float((np.sum(totals >= obs_fade) + 1) / (draws + 1)),
    }


def fade_sl_slice(day, start, offsets, quotes, signal, slip):
    """Diagnostic opposite-direction Fade with symmetric stop distance = signal['risk'] (non-binding control)."""
    i = signal["entry_idx"]
    side = -signal["side"]
    bid0, ask0 = float(quotes[i, 0]), float(quotes[i, 4])
    entry = ask0 if side == 1 else bid0
    risk = signal["risk"]
    stop = entry - side * risk
    fade_sig = {**signal, "side": side, "entry_price": entry, "stop": stop, "risk": risk}
    return orb.sl_slice(day, start, offsets, quotes, fade_sig, slip)


def run_track3(jobs_root: Path, output_dir: Path):
    if sha(clock.ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json") != clock.LOCK_SHA:
        raise ValueError("Holdout lock SHA mismatch")
    specs, bindings = profiles()
    for spec in (s[orb.TARGET] for s in specs.values()):
        if spec["trade_contract_size"] != 1 or spec["currency_profit"] != "USD" or commission(orb.TARGET, spec, 1.0) != 0:
            raise ValueError("Unexpected target US500 execution units")

    output_dir.mkdir(parents=True, exist_ok=True)
    coverage = defaultdict(Counter)
    raw = []
    events = []
    gaps = []
    eligible = {"strict": set(), "extended": set()}
    source_years = {}
    open_spreads = []

    for year in clock.YEAR:
        times, values, ymeta = load_explicit_year(jobs_root, year)
        sessions, cal_sha = orb.calendar(year)
        ymeta["calendar_sha256"] = cal_sha
        source_years[str(year)] = ymeta

        for day, start in sessions.items():
            lo, hi = times.searchsorted([start, start + (orb.FLAT + 1) * 60])
            offsets = (times[lo:hi] - start) // 60
            quotes = values[lo:hi]
            box_mask = offsets < 60
            if box_mask.any():
                open_spreads.extend((quotes[box_mask, 4] - quotes[box_mask, 0]).tolist())

            group, status, signal, missing = orb.classify(offsets, quotes)
            c = coverage[str(year)]
            c[group] += 1
            if group != "strict":
                gaps.append({"day": day, "group": group, "missing_minutes": int(missing)})
            if group not in ("strict", "A_admitted"):
                continue
            eligible["extended"].add(day)
            if group == "strict":
                eligible["strict"].add(day)
            c[status] += 1
            if signal:
                raw.extend(orb.raw_marks(day, start, offsets, quotes, signal))
                events.append((day, start, offsets, quotes, signal))
        print(f"Track3 US500 {year}: {dict(coverage[str(year)])}", flush=True)

    sp_arr = np.array(open_spreads, dtype=np.float64)
    cash_open_spread = {
        "n_minutes": int(len(sp_arr)),
        "mean": float(sp_arr.mean()),
        "p50": float(np.percentile(sp_arr, 50)),
        "p90": float(np.percentile(sp_arr, 90)),
        "p95": float(np.percentile(sp_arr, 95)),
    }

    stage0 = {}
    for k, days in eligible.items():
        stage0[k] = {
            fee: {
                h: orb.raw_summary([r for r in raw if r["fee"] == fee and r["horizon"] == h and r["day"] in days])
                for h in ("2h", "4h", "hard_flat")
            }
            for fee in orb.COSTS
        }

    # Always compute Monte Carlo Null and full SL diagnostics (for complete forensic transparency)
    mc_null = {
        k: mc_random_entry_null([ev for ev in events if ev[0] in days], orb.COSTS[orb.HIGH])
        for k, days in eligible.items()
    }

    sl_results = {}
    fade_sl_diag = {}
    high_tape = []
    for fee, slip in orb.COSTS.items():
        tape = [orb.sl_slice(*ev, slip) for ev in events]
        summaries = {}
        for k, days in eligible.items():
            applicable = [item for item in tape if item[0]["day"] in days]
            summaries[k] = orb.summary_sl(applicable)
            sized, _ = portfolio.replay(
                days,
                {orb.TARGET: {r["day"]: (r, t, m) for r, t, m in applicable}},
                {orb.TARGET: 0.003},
                10000,
                specs["Swing"],
            )
            summaries[k]["swing_10k_030"] = sized
        sl_results[fee] = summaries
        if fee == orb.HIGH:
            high_tape = tape
            ftape = [fade_sl_slice(*ev, slip) for ev in events]
            for k, days in eligible.items():
                fapp = [item for item in ftape if item[0]["day"] in days]
                fade_sl_diag[k] = orb.summary_sl(fapp)

    main_gates = [stage0[k][orb.HIGH]["hard_flat"]["gate"] for k in eligible]
    stage0_pass = all(g["pass"] for g in main_gates)
    sl_pass = all(v["survives"] for v in sl_results[orb.HIGH].values())
    mc_pass = all(mc_null[k]["breakout_p_value"] < 0.05 for k in eligible)

    portfolio_out = None
    if stage0_pass and sl_pass and mc_pass:
        verdict = "US500_SURVIVED_EXPLICIT_M1"
        portfolio_out = orb.combine(jobs_root, eligible, high_tape, specs)
    elif sl_pass and not stage0_pass:
        verdict = "US500_SL_POSITIVE_BUT_FAILED_STAGE0_GATE"
        portfolio_out = orb.combine(jobs_root, eligible, high_tape, specs)
    else:
        verdict = "US500_FAILED_EXPLICIT_M1_CHECK"

    result = {
        "track": "Track3_US500_NY_ORB_Explicit_M1",
        "protocol_commit": PROTOCOL,
        "source_policy": "paired-explicit-source-M1-v1",
        "native_Ask": True,
        "holdout_rows": 0,
        "order_send_count": 0,
        "network_calls": 0,
        "spec": bindings,
        "source_years": source_years,
        "cash_open_spread_points": cash_open_spread,
        "coverage": {k: dict(v) for k, v in coverage.items()},
        "eligible_days": {k: len(v) for k, v in eligible.items()},
        "stage0": stage0,
        "monte_carlo_null_high": mc_null,
        "sl": sl_results,
        "diagnostic_fade_sl_high": fade_sl_diag,
        "gates": {"stage0_pass": stage0_pass, "sl_pass": sl_pass, "mc_null_p05_pass": mc_pass},
        "portfolio": portfolio_out,
        "verdict": verdict,
    }
    write(output_dir / "track3-us500-result.json", result)
    write(output_dir / "track3-us500-gap-days.json", gaps)
    print(f"TRACK3_VERDICT={verdict}", flush=True)
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, default=Path(r"E:\BACKUP-TRADINGWORKSPACE\ai-engine-jobs"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run_track3(args.jobs, args.output)
