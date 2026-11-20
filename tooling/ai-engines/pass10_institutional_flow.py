"""Preregistered London opening-range and US500 month-turn screens on sealed Development prices."""

import argparse
from collections import Counter, defaultdict
from datetime import date, datetime, time, timedelta, timezone
from math import floor, fsum, isfinite
from pathlib import Path
from statistics import correlation, median

import numpy as np
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as tokyo
from native_ftmo_monfri_seal import CLOCK, ROOT, START, STOP, read, sha, write
from pass7_fx_scout import quote_cash
from quant_core.ftmo_track_replay import commission, profiles, rollovers
from sealed_m1_review import cash_sessions

PROTOCOL = "99b30515d6dee84f5572cbfc93ac7f238fcb2784"
PROTOCOL_FILE = "PASS10-ENGINE2-INSTITUTIONAL-FLOW-STAGE0-PROTOCOL-20261120.md"
PARENT = "d004497"
FX = ("EURUSD", "GBPUSD")
INDEX = "US500.cash"
PIP = 0.0001
SLIP_INDEX = 0.75
NY_GAP = "US500_INTRADAY_DATA_GAP_2018_2020"


def epoch(day, hour, zone, minute=0):
    return int(datetime.combine(day, time(hour, minute), zone).timestamp())


def london_day(day, hourly, costs):
    start = epoch(day, 8, tokyo.LONDON)
    box = hourly.get(start)
    if box is None or box.h == box.l:
        return "missing_or_flat_box", None
    top, bottom = (edge + costs.spread / 2 for edge in (box.h, box.l))
    stamps = list(range(start + tokyo.HOUR, start + 5 * tokyo.HOUR, tokyo.HOUR))
    path = []
    for stamp in stamps:
        if stamp not in hourly:
            break
        path.append((stamp, hourly[stamp]))
    verdict, first = tokyo.first_touch(path, top, bottom, costs)
    if first is None:
        if verdict == "no_touch" and len(path) < len(stamps):
            verdict = "missing_activation"
        return verdict, None
    stamp, side, mid = first
    entry = stamp + tokyo.HOUR
    edge = bottom if side == 1 else top
    risk = abs(mid + side * costs.spread / 2 - edge)
    stamps = {"4h": entry + 4 * tokyo.HOUR, "8h": entry + 8 * tokyo.HOUR,
              "hard_flat": epoch(day, 17, tokyo.LONDON)}
    marks, missing = {}, {}
    for name, at in stamps.items():
        if at >= STOP or at >= epoch(day, 17, tokyo.NEW_YORK):
            missing[name] = "rollover_or_cutoff"
        elif any(t not in hourly for t in range(start, at + tokyo.HOUR, tokyo.HOUR)):
            missing[name] = "missing_path_or_endpoint"
        else:
            out = hourly[at].o + costs.spread / 2
            marks[name] = {
                "exit_at": at, "Breakout": quote_cash(mid, out, side, cost=costs, pip=PIP),
                "Fade": quote_cash(mid, out, -side, cost=costs, pip=PIP),
            }
    return "first_touch", {
        "day": day.isoformat(), "year": day.year, "side": side, "trigger": stamp,
        "entry_proxy": entry, "entry_mid": mid, "stop": edge, "risk": risk,
        "width": top - bottom, "marks": marks, "missing": missing,
    }


def cohorts(rows):
    groups = {str(year): [] for year in tokyo.YEAR}
    for row in rows:
        groups[str(row["year"])].append(row)
    clusters = {k: [r for y in years for r in groups[str(y)]] for k, years in tokyo.CLUSTERS.items()}
    return groups, clusters


def friction_scale(rows, friction_key):
    costs = [r[friction_key] for r in rows]
    risks = [r["risk"] for r in rows if r["risk"] is not None and r["risk"] > 0]
    if not costs or len(risks) != len(costs):
        return None
    return {"median_friction": median(costs), "median_natural_stop": median(risks),
            "median_ratio_pct": 100 * median(costs) / median(risks),
            "share_at_12pct": sum(f <= 0.12 * s for f, s in zip(costs, risks)) / len(costs)}


def mean(values):
    values = list(values)
    return fsum(values) / len(values) if values else None


def gate(summary, scale, *, control_fields):
    yearly = list(summary["years"].values())
    by_year = [row["net"] for row in yearly]
    total = summary["total"]
    metric, control, friction = control_fields
    tests = {
        "all_years_observed": len(yearly) == 7 and all(row["n"] for row in yearly),
        "positive_both_clusters": all(v["net"] > 0 for v in summary["clusters"].values()),
        "at_least_five_positive_years": sum(value > 0 for value in by_year) >= 5,
        "positive_ex_best_two_years": fsum(sorted(by_year, reverse=True)[2:]) > 0,
        "mean_net_covers_mean_friction": bool(total["n"] and total["net"] >= total["friction"]),
        "beats_control_by_friction_both_clusters": all(
            v[metric] is not None and v[control] is not None and v[friction] is not None
            and v[metric] - v[control] >= v[friction] for v in summary["clusters"].values()
        ),
        "natural_stop_scale": scale is not None and scale["median_ratio_pct"] <= 12
        and scale["share_at_12pct"] >= .5,
    }
    return {"tests": tests, "positive_years": sum(value > 0 for value in by_year),
            "net_ex_best_two_years": fsum(sorted(by_year, reverse=True)[2:]),
            "pass": all(tests.values())}


def orb_metrics(rows):
    counts = len(rows)
    return {
        "n": counts, "buy": sum(r["side"] == 1 for r in rows), "sell": sum(r["side"] == -1 for r in rows),
        "net": fsum(r["Breakout"]["net"] for r in rows),
        "gross": fsum(r["Breakout"]["gross"] for r in rows),
        "friction": fsum(r["friction"] for r in rows),
        "fade": fsum(r["Fade"]["net"] for r in rows),
        "net_mean": mean(r["Breakout"]["net"] for r in rows),
        "fade_mean": mean(r["Fade"]["net"] for r in rows),
        "friction_mean": mean(r["friction"] for r in rows),
    }


def orb_summary(events, horizon):
    rows = [{"year": r["year"], "side": r["side"], "risk": r["risk"], "width": r["width"],
             "friction": r["marks"][horizon]["Breakout"]["cost"],
             "friction_price": r["marks"][horizon]["Breakout"]["cost_pips"] * PIP,
             **r["marks"][horizon]}
            for r in events if horizon in r["marks"]]
    years, clusters = cohorts(rows)
    result = {"total": orb_metrics(rows), "years": {k: orb_metrics(v) for k, v in years.items()},
              "clusters": {k: orb_metrics(v) for k, v in clusters.items()}}
    scale = friction_scale(rows, "friction_price")
    if scale:
        width = median(r["width"] for r in rows)
        scale["median_box_width_pips"] = width / PIP
        scale["friction_over_box_pct"] = 100 * scale["median_friction"] / width
    result["scale"] = scale
    result["gate"] = gate(result, scale, control_fields=("net_mean", "fade_mean", "friction_mean"))
    return result


def london_scan(asset, hourly, spec):
    costs = tokyo.Costs(spec["spread_price_proxy"] / tokyo.PIP,
                        2 * commission(asset, spec, 1.0), spec["trade_contract_size"])
    coverage, events, eligible = defaultdict(Counter), [], set()
    for t in range(START, STOP, tokyo.DAY):
        day = tokyo.date(t).date()
        if day.weekday() >= 5:
            continue
        status, event = london_day(day, hourly, costs)
        counts = coverage[day.year]
        counts[status] += 1
        if status in ("no_touch", "ambiguous_first_touch") or (event and "hard_flat" in event["marks"]):
            eligible.add(day.isoformat())
        if event is not None:
            events.append(event)
            for horizon, reason in event["missing"].items():
                counts[f"{horizon}:{reason}"] += 1
    horizons = {name: orb_summary(events, name) for name in ("4h", "8h", "hard_flat")}
    return {"decision": decision(horizons["hard_flat"]), "coverage": coverage,
            "horizons": horizons}, events, costs, eligible


def daily_source(folder, binding):
    path = folder / binding["development_file"]
    if path.name != f"{INDEX}-D1.parquet":
        raise ValueError("Wrong native D1 partition")
    clocks = pq.read_table(path, columns=[CLOCK])[CLOCK].to_numpy()
    if (not len(clocks) or len(clocks) != binding["development_rows"] or clocks[-1] >= STOP
            or (np.diff(clocks) <= 0).any() or (clocks % tokyo.DAY).any()
            or sha(path) != binding["development_sha256"]):
        raise ValueError("Native D1 clock or SHA invalid")
    data = pq.read_table(path, columns=[CLOCK, "open", "high", "low", "close"],
                         filters=[(CLOCK, ">=", START), (CLOCK, "<", STOP)])
    daily = {}
    for stamp, op, hi, lo, cl in zip(*(data[k].to_numpy() for k in data.column_names)):
        day = tokyo.date(stamp).date()
        if (not START <= stamp < STOP or epoch(day, 16, tokyo.NEW_YORK, 59) >= STOP
                or not all(isfinite(v) for v in (op, hi, lo, cl))
                or not 0 < lo <= min(op, cl) <= max(op, cl) <= hi):
            raise ValueError("Invalid native D1 Development bar")
        daily[day] = tokyo.Bar(float(op), float(hi), float(lo), float(cl))
    return daily


def calendars():
    paths = [Path(__file__).with_name("fixtures") / f"nyse-{y}.json" for y in tokyo.YEAR]
    days = [date.fromisoformat(d) for path in paths for d in cash_sessions(read(path))]
    if days != sorted(set(days)):
        raise ValueError("Invalid NYSE cash calendar")
    return days, {p.name: sha(p) for p in paths}


def month_windows(days):
    months = defaultdict(list)
    for day in days:
        months[(day.year, day.month)].append(day)
    batches = list(months.values())
    if any(len(month) < 4 for month in batches):
        raise ValueError("Invalid month in the NYSE calendar")
    tom_days = {d for m in batches for d in [*m[:3], m[-1]]}
    tom = [[left[-1], *right[:3]] for left, right in zip(batches, batches[1:])]
    rest = [window for i in range(len(days) - 3)
            if tom_days.isdisjoint(window := days[i:i+4])]
    return tom, rest


def known_atr(daily):
    dates = list(daily)
    bars = list(daily.values())
    prev = [bars[0].o, *(b.c for b in bars[:-1])]
    values = tokyo.wilder(np.array([max(b.h - b.l, abs(b.h - c), abs(b.l - c))
                                  for b, c in zip(bars, prev)]))
    return {d: float(values[i-1]) for i, d in enumerate(dates) if i >= 14 and isfinite(values[i-1])}


def index_mark(start, stop, bid_in, bid_out, spec):
    if not START <= start < stop < STOP:
        raise ValueError("TOM execution clock outside Development")
    if spec["swap_mode"] != 1 or spec["trade_contract_size"] != 1:
        raise ValueError("Unexpected sealed index contract")
    spread = spec["spread_price_proxy"]
    marks = list(rollovers(start * 1000, stop * 1000, spec["swap_rollover3days"]))
    swap = fsum(mult * spec["swap_long"] * spec["point"] for _, mult in marks)
    gross = bid_out - bid_in
    friction = spread + 2 * SLIP_INDEX - swap
    return {"gross": gross, "spread": spread, "slippage": 2 * SLIP_INDEX,
            "swap": swap, "friction": friction, "net": gross - friction,
            "rollovers": len(marks), "triple_rollovers": sum(mult == 3 for _, mult in marks)}


def tom_event(window, daily, atr, spec, standard):
    if any(day not in daily for day in window):
        return None
    begin = window[0]
    idx = len(window) - 1
    if standard:
        # A Friday holiday leaves Thursday as the last cash session before the weekend.
        idx = next((i for i, (left, right) in enumerate(zip(window, window[1:]))
                    if left.isocalendar()[:2] != right.isocalendar()[:2]), idx)
    end = window[idx]
    start = epoch(begin - timedelta(days=1), 17, tokyo.NEW_YORK)
    stop = epoch(end, 16, tokyo.NEW_YORK, 59)
    if start < START:
        return None
    bid_in, bid_out = daily[begin].o, daily[end].c
    result = index_mark(start, stop, bid_in, bid_out, spec)
    exposure = idx + 1
    return {**result, "day": begin.isoformat(), "exit_day": end.isoformat(), "year": begin.year,
            "start": start, "stop": stop, "entry_bid": bid_in, "held_sessions": exposure,
            "friday_clamped": idx < len(window)-1, "risk": 2 * atr[begin] if begin in atr else None,
            "net_bps_session": 10000 * result["net"] / (bid_in * exposure),
            "friction_bps_session": 10000 * result["friction"] / (bid_in * exposure)}


def tom_metrics(rows, control):
    return {
        "n": len(rows), "control_n": len(control), "net": fsum(r["net"] for r in rows),
        "gross": fsum(r["gross"] for r in rows), "friction": fsum(r["friction"] for r in rows),
        "swap": fsum(r["swap"] for r in rows), "triple_rollovers": sum(r["triple_rollovers"] for r in rows),
        "friday_clamped": sum(r["friday_clamped"] for r in rows),
        "net_bps_session": mean(r["net_bps_session"] for r in rows),
        "rest_bps_session": mean(r["net_bps_session"] for r in control),
        "friction_bps_session": mean(r["friction_bps_session"] for r in rows),
    }


def tom_scan(daily, days, spec, standard):
    windows, rest_windows = month_windows(days)
    atr = known_atr(daily)
    events, control = (
        [event for window in configured if (event := tom_event(window, daily, atr, spec, standard)) is not None]
        for configured in (windows, rest_windows)
    )
    years, clusters = cohorts(events)
    cy, cc = cohorts(control)
    result = {"planned_tom": len(windows), "planned_rest": len(rest_windows), "boundary_tom_windows": 2,
              "native_d1_rows": len(daily), "cash_sessions": len(days),
              "cash_d1_present": sum(day in daily for day in days),
              "total": tom_metrics(events, control),
              "years": {k: tom_metrics(v, cy[k]) for k, v in years.items()},
              "clusters": {k: tom_metrics(v, cc[k]) for k, v in clusters.items()},
              "scale": friction_scale(events, "friction")}
    result["gate"] = gate(result, result["scale"],
                          control_fields=("net_bps_session", "rest_bps_session", "friction_bps_session"))
    result["decision"] = decision(result) if not standard else "CONTROL_ONLY"
    return result, events


def decision(result):
    return "PROMOTE_TO_SL_SLICE" if result["gate"]["pass"] else "REJECTED_AT_STAGE0"


def account_trade(net_per_lot, stop_per_lot, margin_per_lot, min_lot, step, max_lot, balance):
    budget = balance * .003
    lots = round(floor(min(budget / stop_per_lot, max_lot) / step + 1e-10) * step, 8)
    if lots < min_lot:
        return {"status": "MIN_LOT", "lots": 0., "net": 0., "margin": 0.}
    if margin_per_lot * lots > balance:
        return {"status": "MARGIN", "lots": 0., "net": 0., "margin": 0.}
    return {"status": "SIZED", "lots": lots, "net": net_per_lot * lots,
            "planned_risk": stop_per_lot * lots, "margin": margin_per_lot * lots}


def london_slice(events, hourly, costs, spec):
    rows = []
    for row in events:
        if "hard_flat" not in row["marks"]:
            continue
        risk = row["risk"] * costs.contract
        flat = row["marks"]["hard_flat"]["exit_at"]
        event = {"day": row["day"], "year": row["year"], "side": row["side"],
                 "entry_proxy_utc": tokyo.date(row["entry_proxy"]).isoformat(),
                 "entry_mid_proxy": row["entry_mid"], "stop_opposite_edge": row["stop"],
                 "markouts": {"hard_flat": {"exit_at": tokyo.date(flat).isoformat()}}}
        priced = tokyo.sl_trade(event, hourly, costs, stop_risk_usd=lambda *_: risk,
                                value_at=lambda _, a, b, side: quote_cash(a, b, side, cost=costs, pip=PIP))
        net = priced["net_R"] * risk
        stop = risk + costs.commission_usd + 2 * costs.slip_pips_per_side * PIP * costs.contract
        margin = spec["margin_per_reference"] * row["entry_mid"]
        lots = {str(balance): account_trade(net, stop, margin, spec["volume_min"], spec["volume_step"],
                                             spec["volume_max"], balance) for balance in (10000, 25000)}
        rows.append({**priced, "net_usd_per_lot": net, "stop_with_friction_usd_per_lot": stop, "sizing": lots})
    return rows


def bound_reference(jobs):
    root = jobs / "pass7b-usdjpy-qdm-equity-20261120"
    catalogue = read(ROOT / "planning/research/STRATEGY-CATALOGUE-20261107.json")
    binding = next(r for r in catalogue["evidence_inventory"]["broker_observations"] if r["id"] == root.name)
    manifest_path = root / "manifest.json"
    if sha(manifest_path) != binding["private_manifest_sha256"]:
        raise ValueError("Pass 7B manifest drift")
    manifest = read(manifest_path)
    if manifest["holdout_lock_sha256"] != tokyo.LOCK_SHA or manifest["holdout_price_rows_analysed"]:
        raise ValueError("Unbound Pass 7B source scope")
    hashes = {}

    def private_file(rel):
        path = root / rel
        actual = sha(path)
        if actual != manifest["files"][rel]["sha256"]:
            raise ValueError(f"Pass 7B file hash drift: {rel}")
        hashes[rel] = actual
        return path

    costs = read(private_file("verified/M1_Real_Stress_05-trades.json"))
    original = read(private_file("verified/M1_Real_Stress_05-account-lots.json"))["Swing 10k/0.0030"]
    receipt = read(private_file("verified/result.json"))
    complete = set()
    for year in tokyo.YEAR:
        path = private_file(f"development-m1/USDJPY-M1-BIDASK-{year}.parquet")
        clock = pq.read_table(path, columns=["minute"])["minute"].to_numpy() * 60
        low = epoch(date(year, 1, 1), 0, timezone.utc)
        high = epoch(date(year + 1, 1, 1), 0, timezone.utc)
        if not len(clock) or clock[0] < low or clock[-1] >= min(high, STOP) or (np.diff(clock) <= 0).any():
            raise ValueError("Pass 7B clock outside allowed window")
        for stamp in range(low, high, tokyo.DAY):
            utc = tokyo.date(stamp)
            if utc.weekday() >= 5:
                continue
            end = tokyo.hard_flat(utc)
            lo, hi = clock.searchsorted([stamp, end + 60])
            if np.array_equal(clock[lo:hi], np.arange(stamp, end + 60, 60)):
                complete.add(utc.date().isoformat())

    if any(sum(d.startswith(str(y)) for d in complete) != receipt["coverage"][str(y)]["complete_path"]
           for y in tokyo.YEAR):
        raise ValueError("Reconstructed Pass 7B covered days failed reconciliation")
    if {r["day"] for r in costs} != {r["day"] for r in original}:
        raise ValueError("Pass 7B Stress_05 cash/lot ledger mismatch")
    for row in costs:
        if (row["day"] not in complete or not START <= row["entry"] <= row["exit"] < STOP
                or tokyo.date(row["exit"]).date().isoformat() != row["day"]):
            raise ValueError("Pass 7B trade outside reconstructed same-day coverage")
    anchor, = [r for r in receipt["account_equity"]["M1_Real_Stress_05"]
               if r["account"] == "Swing 10k" and r["risk_pct"] == .30]
    return costs, original, complete, hashes, anchor["max_underwater_months"]


def curve(rows, key):
    equity = peak = dd = age = 0.
    peak_day = None
    underwater = False
    for row in rows:
        day = date.fromisoformat(row["day"])
        if peak_day is None:
            peak_day = day
        equity += row[key]
        below_peak = equity < peak - 1e-8
        if below_peak or underwater:
            age = max(age, (day - peak_day).days)
        underwater = below_peak
        if below_peak:
            dd = max(dd, peak - equity)
        else:
            peak_day = day
            peak = max(peak, equity)
    return {"net_usd": equity, "max_dd_usd": dd, "net_over_dd": equity / dd if dd else None,
            "max_underwater_days": age, "max_underwater_months": age / (365.2425 / 12)}


def paired_metrics(rows):
    result = {}
    for frequency in ("daily", "weekly"):
        groups = defaultdict(lambda: [0., 0.])
        for row in rows:
            day = date.fromisoformat(row["day"])
            key = day if frequency == "daily" else day.isocalendar()[:2]
            groups[key][0] += row["usdjpy"]
            groups[key][1] += row["gbpusd"]
        result[frequency] = {}
        for name, values in (("all", list(groups.values())),
                             ("usdjpy_losing", [v for v in groups.values() if v[0] < 0])):
            x, y = zip(*values) if values else ((), ())
            result[frequency][name] = {"n": len(values),
                "pearson": correlation(x, y) if min(len(set(x)), len(set(y))) > 1 else None,
                "double_loss": sum(a < 0 and b < 0 for a, b in values),
                "gbpusd_positive": sum(b > 0 for b in y),
                "gbpusd_net_usd": fsum(y)}
    return result


def compare_portfolio(jobs, london_rows, london_eligible, usd_spec):
    usdjpy, original, reference_eligible, hashes, original_floating_age = bound_reference(jobs)
    jpy_amounts = {
        r["day"]: account_trade(r["net_usd_per_lot"], r["stop_risk_with_cost_usd"],
                                usd_spec["margin_per_reference"], usd_spec["volume_min"],
                                usd_spec["volume_step"], usd_spec["volume_max"], 10000)["net"]
        for r in usdjpy
    }
    gbp_amounts = {r["day"]: r["sizing"]["10000"]["net"] for r in london_rows}
    paired_days = sorted(london_eligible & reference_eligible)
    rows = [{"day": day, "usdjpy": jpy_amounts.get(day, 0.), "gbpusd": gbp_amounts.get(day, 0.)}
            for day in paired_days]
    for row in rows:
        row["combined"] = row["usdjpy"] + row["gbpusd"]
    original_by_day = {r["day"]: r["net_usd"] for r in original}
    baseline = [{"day": day, "usdjpy": original_by_day.get(day, 0.)} for day in sorted(reference_eligible)]
    summary = {"pairing_basis": "same eligible UTC day and fixed $30 per sleeve, closed cash only",
               "reference_eligible_days": len(reference_eligible), "gbpusd_eligible_days": len(london_eligible),
               "paired_days": len(rows), "excluded_usdjpy_signals": len(jpy_amounts.keys() - set(paired_days)),
               "excluded_gbpusd_signals": len(gbp_amounts.keys() - set(paired_days)),
               "original_usdjpy_full_closed_cash": curve(baseline, "usdjpy"),
               "original_usdjpy_full_floating_underwater_months": original_floating_age,
               "correlation": paired_metrics(rows),
               "matched_cash": {k: curve(rows, k) for k in ("usdjpy", "gbpusd", "combined")},
               "reference_manifest_files": hashes}
    return summary, rows

def run(jobs, out):
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    if sha(lock_path) != tokyo.LOCK_SHA:
        raise ValueError("Holdout lock changed")
    lock = read(lock_path)
    specs, bindings = profiles()
    folder = jobs / "bottleneck2-monfri-20261119/development"
    out.mkdir(exist_ok=False)
    result = {"schema": "pass10-institutional-flow-v1", "parent": PARENT, "protocol_commit": PROTOCOL,
              "holdout_lock_sha256": tokyo.LOCK_SHA, "holdout_price_files_read": 0,
              "order_send_count": 0, "profiles": bindings, "input_hashes": {},
              "cohort": [2018, 2024], "london": {}, "ny_orb": {"decision": NY_GAP, "executed": False}}
    for asset in FX:
        binding = lock["series"][asset]["H1"]
        hourly = tokyo.load_sealed(folder, "H1", binding, asset=asset)
        assert min(hourly) >= START and max(hourly) < STOP
        result["input_hashes"][asset] = binding["development_sha256"]
        result["london"][asset], ledger, costs, eligible = london_scan(asset, hourly, specs["Swing"][asset])
        if result["london"][asset]["decision"] == "PROMOTE_TO_SL_SLICE":
            sl = london_slice(ledger, hourly, costs, specs["Swing"][asset])
            yr, cl = cohorts(sl)
            def sl_stats(rows):
                return {"n": len(rows), "net_R": fsum(r["net_R"] for r in rows),
                        "net_usd_per_lot": fsum(r["net_usd_per_lot"] for r in rows),
                        "exits": dict(Counter(r["reason"] for r in rows))}
            result["london"][asset]["sl_slice"] = {
                "total": sl_stats(sl), "years": {k: sl_stats(v) for k, v in yr.items()},
                "clusters": {k: sl_stats(v) for k, v in cl.items()},
                "sizing": {k: {"statuses": dict(Counter(r["sizing"][k]["status"] for r in sl)),
                               "net_usd": fsum(r["sizing"][k]["net"] for r in sl),
                               "peak_margin_usd": max(r["sizing"][k]["margin"] for r in sl)}
                           for k in ("10000", "25000")}}
            write(out / f"london-{asset}-sl-active.json", sl)
            if asset == "GBPUSD":
                result["pairing"], aligned = compare_portfolio(jobs, sl, eligible, specs["Swing"]["USDJPY"])
                write(out / "paired-daily-cash.json", aligned)
        write(out / f"london-{asset}-events.json", ledger)
        print(asset, result["london"][asset]["decision"], flush=True)
    binding = lock["series"][INDEX]["D1"]
    daily = daily_source(folder, binding)
    days, result["calendars"] = calendars()
    result["input_hashes"][INDEX] = binding["development_sha256"]
    result["tom"] = {}
    for profile in ("Swing", "Standard"):
        result["tom"][profile], ledger = tom_scan(daily, days, specs[profile][INDEX], profile == "Standard")
        write(out / f"tom-{profile.lower()}-events.json", ledger)
        print(profile, result["tom"][profile]["decision"], flush=True)
    write(out / "stage0.json", result)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    run(args.jobs, args.output)
