"""Matched-coverage M1 equity audit, conditional on the frozen GBPUSD gate."""

from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from math import fsum, isclose

import numpy as np

import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as core
from pass7b_usdjpy_research import load_m1
from pass8_usdjpy_gaps import replayable, shape
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from quant_core.ftmo_track_replay import profiles

PROTECTED_DD = 8.
STRESS = "M1_Real_Stress_05"
USDJPY = "USDJPY"
GBPUSD = "GBPUSD"


@dataclass(frozen=True)
class SizedTrade:
    row: dict
    clock: np.ndarray
    marks: np.ndarray
    lots: float
    margin: float
    net: float

    @property
    def entry(self):
        return int(self.clock[0])

    @property
    def release(self):
        return int(self.clock[-1]) + (0 if self.row["at_open"] else 60)

    def open_floating(self, stamp):
        if stamp >= self.release:
            return self.net
        i = int(self.clock.searchsorted(stamp))
        point = self.marks[i, 0] if i < len(self.clock) and self.clock[i] == stamp else self.marks[i - 1, 3]
        return self.lots * point


def manifest_files(jobs, key, relatives):
    root = jobs / key
    catalogue = read(ROOT / "planning/research/STRATEGY-CATALOGUE-20261107.json")
    entry, = [r for r in catalogue["evidence_inventory"]["broker_observations"] if r["id"] == key]
    manifest = root / "manifest.json"
    if sha(manifest) != entry["private_manifest_sha256"]:
        raise ValueError(f"Parent manifest drift: {key}")
    objects = read(manifest)["files"]
    paths = {name: root / name for name in relatives}
    if any(sha(path) != objects[name]["sha256"] for name, path in paths.items()):
        raise ValueError(f"Parent file drift: {key}")
    return paths


def frozen_usdjpy(jobs):
    parent = "pass7b-usdjpy-qdm-equity-20261120"
    relatives = ["development-m1/manifest.json", "verified/result.json",
                 "verified/m1-coverage-gaps.json"]
    paths = manifest_files(jobs, parent, relatives)
    manifest, report, gaps = (read(paths[name]) for name in relatives)
    if (manifest["holdout_exclusive_ms"] != STOP * 1000 or report["holdout_price_rows_analysed"]
            or report["holdout_lock_sha256"] != clock.LOCK_SHA):
        raise ValueError("USDJPY parent outside scope")
    known = {r["day"]: r for r in gaps["native_h1_missing_m1_days"]}
    cohort = {"strict": set(), "extended": set()}
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
            offsets = (times[lo:hi]-day)//60
            prices = values[lo:hi, :8]
            strict = np.array_equal(offsets, np.arange(flat + 1))
            if strict:
                cohort["strict"].add(day_key)
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
            cohort["extended"].add(day_key)
            if trade is None:
                continue
            addon = core.PROFILE[STRESS]
            row = core.record(trade, addon)
            stamps = np.array([trade.second_at(i) for i in range(trade.entry, trade.execution.index + 1)])
            assert START <= stamps[0] <= stamps[-1] < STOP
            trades[day_key] = ({**row, "at_open": trade.execution.at_open}, stamps, core.path(trade, addon))
    old = report["profiles"][STRESS]
    base_trades = [row for d, (row, *_rest) in trades.items() if d in cohort["strict"]]
    if len(cohort["strict"]) != 1334 or len(base_trades) != old["n"] or not isclose(
            fsum(r["net_R"] for r in base_trades), old["net_R"], abs_tol=1e-8):
        raise ValueError("Pass 7B Stress_05 replay changed")
    gap_receipt, = manifest_files(jobs, "pass8-engine2-and-m1-gaps-20261120", ["usdjpy/gap-summary.json"]).values()
    check = read(gap_receipt)
    if (len(cohort["extended"]) != check["coverage"]["sensitivity"]
            or not isclose(fsum(row["net_R"] for row, *_ in trades.values()),
                           check["sensitivity_R"]["net_R"], abs_tol=1e-8)):
        raise ValueError("Pass 8 extended Stress_05 replay changed")
    return trades, cohort


def size_day(day_trades, risks, initial, balance, specs):
    sized, ledger = [], []
    for symbol, (row, stamps, marks) in sorted(day_trades.items(), key=lambda kv: (kv[1][0]["entry"], kv[0])):
        if symbol not in risks:
            continue
        spec = specs[symbol]
        budget = initial * risks[symbol]
        margin = spec["margin_per_reference"] * (row["margin_quote"] if symbol == GBPUSD else 1.)
        account = core.Account(symbol, initial, margin, spec["volume_min"], spec["volume_step"], spec["volume_max"])
        lot = core.floor_lot(budget, row["stop_risk_with_cost_usd"], account)
        stamp = int(stamps[0])
        used = fsum(t.margin for t in sized if stamp < t.release)
        available = balance + fsum(t.open_floating(stamp) for t in sized) - used
        status = "SIZED"
        if lot < spec["volume_min"]:
            status = "MIN_LOT"
        elif lot * (margin + 2.5) > available:
            status = "MARGIN"
        ledger.append({"engine": symbol, "entry": stamp, "lots": lot if status == "SIZED" else 0.,
                       "entry_free_margin": available, "status": status,
                       "planned_risk_usd": budget, "reason": row["reason"]})
        if status == "SIZED":
            sized.append(SizedTrade(row, stamps, marks, lot, lot * margin, lot * row["net_usd_per_lot"]))
    return sized, ledger


def combined_marks(trades):
    timeline = np.arange(min(t.entry for t in trades), max(t.clock[-1] for t in trades) + 60, 60)
    combined = np.zeros((len(timeline), 4))
    margin = np.zeros(len(timeline))
    concurrent = np.zeros(len(timeline), dtype=np.int8)
    missing = 0
    for trade in trades:
        offsets = (trade.clock - timeline[0]) // 60
        start, end = int(offsets[0]), int(offsets[-1])
        combined[offsets] += trade.marks * trade.lots
        pos = np.arange(start, end + 1)
        gaps = np.setdiff1d(pos, offsets, assume_unique=True)
        if len(gaps):
            # No simulated quote/fill. Carry the most recent observed mark for accounting.
            past = offsets.searchsorted(gaps) - 1
            combined[gaps] += (trade.marks[past, 3] * trade.lots)[:, None]
            missing += len(gaps)
        combined[end+1:] += trade.net
        held = (timeline >= trade.entry) & (timeline < trade.release)
        margin[held] += trade.margin
        concurrent[held] += 1
    return timeline, combined, margin, concurrent, missing


def replay(days, tapes, risks, initial, specs, *, cutoff=STOP):
    balance = float(initial)
    meter = core.EquityMetrics(initial, START, [int(np.datetime64(d, "D").astype(int)) for d in sorted(days)])
    exits, totals, rejects = [], defaultdict(list), Counter()
    double_sl = stale = margin_open_days = 0
    peak_margin = peak_simultaneous = peak_overlap_utc = 0.
    for day in sorted(days):
        selected = {s: tapes[s][day] for s in risks if day in tapes[s]}
        if not selected:
            continue
        trades, orders = size_day(selected, risks, initial, balance, specs)
        rejects.update(x["status"] for x in orders)
        if not trades:
            continue
        timeline, marks, margin, overlap, count = combined_marks(trades)
        if core.prague_day(int(timeline[0])) != core.prague_day(int(timeline[-1])):
            raise ValueError("Unexpected Prague reset within day")
        # All orders start after prior-day flattening, so current balance is Prague reset anchor.
        points = np.r_[balance, (balance + marks).ravel()]
        meter.add(np.r_[timeline[0], np.repeat(timeline, 4)], points, balance)
        stale += count
        peak_margin = max(peak_margin, float(margin.max()), max(t.margin for t in trades))
        if np.any(overlap == 2):
            margin_open_days += 1
            peak_simultaneous = max(peak_simultaneous, float(margin[overlap == 2].max()))
            minute_utc = (timeline % clock.DAY) // 60
            selected_hours = (overlap == 2) & (minute_utc >= 9 * 60) & (minute_utc < 16 * 60)
            if selected_hours.any():
                peak_overlap_utc = max(peak_overlap_utc, float(margin[selected_hours].max()))
        net = fsum(t.net for t in trades)
        if not isclose(float(marks[-1, -1]), net, abs_tol=1e-8):
            raise ValueError("Terminal floating marks do not reconcile with cash")
        balance += net
        totals[day[:4]].append(net)
        double_sl += int(len(trades) == 2 and all(t.row["reason"] == "SL_GAP_OR_TOUCH" for t in trades))
        exits.append({"day": day, "net_usd": net, "cash": balance, "orders": orders,
                      "day_equity_minimum": float(points.min()), "day_equity_maximum": float(points.max())})
    if balance < meter.peak:
        meter.update_age(np.array([meter.peak_at]), np.array([cutoff - 1]))
    annual = {"A": fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["A"]) / 3,
              "B": fsum(fsum(totals[str(y)]) for y in clock.CLUSTERS["B"]) / 4, "all": (balance - initial) / 7}
    return {"risk": risks, "net_usd": balance-initial, "annual_usd": annual,
            "annual_pct": {k: 100*v/initial for k,v in annual.items()},
            "daily_loss_pct": 100 * meter.daily/initial, "peak_dd_pct": 100 * meter.dd/initial,
            "static_loss_pct": 100 * max(0., initial - min(initial, meter.minimum))/initial,
            "net_over_dd": (balance-initial)/meter.dd if meter.dd else None,
            "underwater_months": meter.max_age[0]/clock.DAY/(365.2425/12),
            "double_sl_days": double_sl, "peak_margin_pct": 100*peak_margin/initial,
            "simultaneous_margin_pct": 100*peak_simultaneous/initial,
            "simultaneous_margin_09_16_utc_pct": 100*peak_overlap_utc/initial,
            "overlap_days": margin_open_days, "margin_failures": rejects["MARGIN"],
            "min_lot_rejections": rejects["MIN_LOT"], "sized": rejects["SIZED"],
            "stale_marks_group_a": stale}, exits


def run(jobs, output, gbp, eligible):
    reference, ref_days = frozen_usdjpy(jobs)
    tapes = {USDJPY: reference, GBPUSD: {r["day"]: (r, clocks, m) for r, clocks, m in gbp}}
    matched = {k: ref_days[k] & eligible[k] for k in eligible}
    specs, bindings = profiles()
    a_days = {d for d in matched["strict"] if d < "2021-01-01"}
    a_dd = {s: replay(a_days, tapes, {s: .003}, 10000, specs["Swing"],
                      cutoff=int(datetime(2021, 1, 1, tzinfo=timezone.utc).timestamp()))[0]["peak_dd_pct"] for s in tapes}
    if any(v <= 0 for v in a_dd.values()):
        raise ValueError("Invalid Cluster A inverse DD denominator")
    inv = {s: (1 / dd) / fsum(1 / v for v in a_dd.values()) for s, dd in a_dd.items()}
    cases = {
        "SOLO_USDJPY_REF_025": {USDJPY: .0025},
        "SOLO_USDJPY_REF_030": {USDJPY: .003},
        "PORT_EQUAL_CONSERVATIVE": {USDJPY: .0015, GBPUSD: .0015},
        "PORT_EQUAL_BALANCED": {USDJPY: .002, GBPUSD: .002},
        "PORT_INVERSE_DD_040": {s: .004 * w for s, w in inv.items()},
        "PORT_INVERSE_DD_050": {s: .005 * w for s, w in inv.items()},
    }
    results = {}
    gate_passed = []
    for profile, balances in (("Swing", (10000, 25000)), ("Standard", (50000,))):
        for balance in balances:
            name = f"{profile}_{balance}"
            results[name] = {}
            for cohort, days in matched.items():
                results[name][cohort] = {}
                for key, risks in cases.items():
                    metrics, ledger = replay(days, tapes, risks, balance, specs[profile])
                    results[name][cohort][key] = metrics
                    write(output / f"{name}-{cohort}-{key}-daily.json", ledger)
                solo = results[name][cohort]["SOLO_USDJPY_REF_030"]
                for key, m in results[name][cohort].items():
                    if key.startswith("PORT"):
                        m["advance_gate"] = (
                            min(m["annual_pct"]["A"], m["annual_pct"]["B"]) > 0 and m["annual_pct"]["all"] >= 8.
                            and m["daily_loss_pct"] <= 3. and m["peak_dd_pct"] <= PROTECTED_DD
                            and m["static_loss_pct"] < 10. and not m["margin_failures"]
                            and m["underwater_months"] < solo["underwater_months"])
            if profile == "Swing":
                for key in cases:
                    if (key.startswith("PORT") and all(results[name][k][key]["advance_gate"] for k in matched)
                            and all(not results["Swing_10000"][k][key]["margin_failures"] for k in matched)):
                        gate_passed.append([name, key])
    result = {"cases": cases, "inverse_dd_cluster_A": a_dd, "matched_days": {k: len(d) for k, d in matched.items()},
              "profiles": bindings, "books": results, "qualifying_cases": gate_passed,
              "verdict": "ADVANCE_TO_PASS12_CHALLENGE_SIM" if gate_passed else "PORTFOLIO_STILL_TOO_SLOW_NEEDS_ENGINE3"}
    write(output / "portfolio-result.json", result)
    return result
