"""Quarantine admission and London ORB M1 replay for the frozen Pass 11."""

import argparse
from collections import Counter, defaultdict
from math import fsum
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as clock
import pass7b_qdm_m1 as qdm
import pass7b_usdjpy_equity as equity
from native_ftmo_monfri_seal import ROOT, START, STOP, read, sha, write
from pass10_institutional_flow import epoch
from pass8_usdjpy_gaps import touches_between
from quant_core.ftmo_track_replay import profiles

SYMBOL = "GBPUSD_PASS11_QUARANTINE"
PROTOCOL = "98068c8b7a6548889fd5c5b3794b10a5db91a76d"
QDM_SHA = "b58052d516422e3cf8e0d42a0883f6811807ecd730d867f8838efbcf6883f4a6"
PIP = .0001
GRID = 100000
STRESS = "M1_Real_Stress_05"
PROFILES = {"M1_Real_Base": 0., STRESS: .5 * PIP, "M1_Real_Stress_10": PIP}
CONTRACT = 100000.
COMMISSION = 5.
SLIP = .2 * PIP
WINDOW = 540


def bound_export(job, entry):
    year = entry["year"]
    qdm.year_limits(year)
    folder = (job / "export" / str(year)).resolve()
    args = ["-data", "action=export", f"symbols={SYMBOL}", "timeframe=TICK", "timezone=UTC",
            f"datefrom={year}.01.01", f"dateto={year}.12.31", f"outputdir={folder.as_posix()}",
            "format=Generic tick format (comma delimited)"]
    path = (job / entry["path"]).resolve()
    if entry["argv"] != args or path.parent != folder or path.suffix != ".csv":
        raise ValueError("QDM export is not a registered Development partition")
    if path.stat().st_size != entry["bytes"]:
        raise ValueError("QDM export size mismatch")
    return path


def grid(values):
    prices = values.to_numpy() * GRID
    rounded = np.rint(prices)
    if (not np.isfinite(prices).all() or (prices <= 0).any()
            or (rounded >= np.iinfo(np.int32).max // 2).any()
            or (np.abs(prices - rounded) > 1e-6).any()):
        raise ValueError("Invalid GBPUSD price or precision")
    return rounded.astype(np.int32)


def aggregate(path, year, admission):
    count, previous, blocks = 0, None, []
    carry = tuple(np.empty(0, dtype=np.int64) for _ in range(3))
    for batch in qdm.batches(path, prices=True):
        stamps = qdm.timestamp_ms(batch.column(0), year, previous)
        if not len(stamps):
            continue
        if not count and int(stamps[0]) != admission["first_ms"]:
            raise ValueError("QDM first clock changed after admission")
        previous = int(stamps[-1])
        count += len(stamps)
        bid, ask = grid(batch.column(1)), grid(batch.column(2))
        if (ask < bid).any():
            raise ValueError("Crossed QDM quote")
        minute, bid, ask = (np.concatenate((prev, new)) for prev, new in
                            zip(carry, (stamps // qdm.MINUTE_MS, bid, ask)))
        split = minute.searchsorted(minute[-1])
        if split:
            blocks.append(qdm.minute_rows(minute[:split], bid[:split], ask[:split]))
        carry = (minute[split:], bid[split:], ask[split:])
    blocks.append(qdm.minute_rows(*carry))
    result = np.concatenate(blocks)
    if (count != admission["rows"] or previous != admission["last_ms"]
            or int(result[:, 1].sum()) != count or (np.diff(result[:, 0]) <= 0).any()
            or sha(path) != admission["sha256"]):
        raise ValueError("QDM tick/minute reconciliation failed")
    return result


def prepare(job, out, only_year=None):
    receipt = job / "QDM_EXPORT_RECEIPT.json"
    meta = read(receipt)
    if (meta["status"], meta["protocol_commit"], meta["qdm_cli_version"],
            meta["qdm_cli_sha256"], meta["raw_symbol"]) != (
            "DEVELOPMENT_EXPORTS_READY", PROTOCOL, "125.2692", QDM_SHA, SYMBOL):
        raise ValueError("QDM receipt identity mismatch")
    if [e["year"] for e in meta["exported_development"]] != list(clock.YEAR):
        raise ValueError("QDM exports missing years")
    out.mkdir(exist_ok=True)
    for entry in meta["exported_development"]:
        year = entry["year"]
        if only_year is not None and only_year != year:
            continue
        receipt_path = out / f"{year}.json"
        if receipt_path.exists():
            continue
        path = bound_export(job, entry)
        scan = qdm.preflight(path, year)
        write(out / f"{year}-clock-admission.json", scan)
        rows = aggregate(path, year, scan)
        part = out / f"GBPUSD-M1-BIDASK-{year}.parquet"
        pq.write_table(pa.table({k: rows[:, i] for i, k in enumerate(qdm.COLUMNS)}), part,
                       compression="zstd")
        record = {**scan, "parquet": part.name, "parquet_sha256": sha(part),
                  "minutes": len(rows), "codec": "zstd",
                  "first_minute": int(rows[0, 0]), "last_minute": int(rows[-1, 0])}
        write(receipt_path, record)
        print(year, "ticks", scan["rows"], "minutes", len(rows), flush=True)
    if only_year is None:
        seal_source(job, out)


def seal_source(job, out):
    receipt = job / "QDM_EXPORT_RECEIPT.json"
    records = {str(y): read(out / f"{y}.json") for y in clock.YEAR}
    write(out / "manifest.json", {"source": SYMBOL, "protocol_commit": PROTOCOL,
                                  "export_receipt_sha256": sha(receipt), "years": records})


def load_m1(folder, year, binding):
    path = folder / f"GBPUSD-M1-BIDASK-{year}.parquet"
    if path.name != binding["parquet"] or sha(path) != binding["parquet_sha256"]:
        raise ValueError("GBPUSD M1 partition SHA mismatch")
    first, last = (n // qdm.MINUTE_MS for n in qdm.year_limits(year))
    stamps = pq.read_table(path, columns=["minute"])["minute"].to_numpy()
    if (not len(stamps) or len(stamps) != binding["minutes"] or stamps[0] < first
            or stamps[-1] >= last or (np.diff(stamps) <= 0).any()):
        raise ValueError("GBPUSD M1 clock outside year")
    values = pq.read_table(path, columns=qdm.COLUMNS[2:])
    return stamps * 60, np.column_stack([values[k].to_numpy() for k in values.column_names]) / GRID


def box_edges(offsets, values):
    box = values[offsets < 60]
    return float(box[:, 9].max() / 2), float(box[:, 10].min() / 2)


def execution(start, offsets, values):
    top, bottom = box_edges(offsets, values)
    if top <= bottom:
        return None
    prefix, bound = offsets.searchsorted([60, 300])
    candidates = values[prefix:bound]
    up, down = candidates[:, 5] >= top - 1e-10, candidates[:, 2] <= bottom + 1e-10
    touched = np.flatnonzero(up | down)
    if not len(touched):
        return None
    idx = int(prefix) + int(touched[0])
    quote = values[idx]
    side_candidates = []
    if up[touched[0]]:
        side_candidates.append((1, max(top, quote[4]), bottom))
    if down[touched[0]]:
        side_candidates.append((-1, min(bottom, quote[0]), top))
    dual = len(side_candidates) == 2
    possible = []
    for side, entry, edge in side_candidates:
        liq = values[:, :4] if side == 1 else values[:, 4:8]
        extrema = liq[:, 2 if side == 1 else 1]
        violations = np.flatnonzero(side * (extrema[idx:-1] - edge) <= 1e-10)
        if len(violations):
            stop = idx + int(violations[0])
            open_gap = stop != idx and side * (liq[stop, 0] - edge) <= 1e-10
            out = liq[stop, 0] if open_gap else edge
            end = equity.Exit(stop, float(out), bool(open_gap), "SL_GAP_OR_TOUCH")
        else:
            stop = len(liq) - 1
            end = equity.Exit(stop, float(liq[-1, 0]), True, "HARD_FLAT")
        margin_quote = float((quote[0] + quote[4]) / 2)
        risk = float(side * (entry - edge) * CONTRACT)
        if risk <= 0:
            raise ValueError("Nonpositive stop distance")
        possible.append((side, float(entry), edge, risk, end, margin_quote))
    side, entry, stop, risk, end, mid = min(
        possible, key=lambda r: (r[0] * (r[4].price - r[1]) * CONTRACT - 2 * SLIP * CONTRACT - COMMISSION) / r[3])
    return {"start": start, "entry_index": idx, "side": side, "entry_price": entry, "stop": stop, "risk": risk,
            "exit": end, "margin_quote": mid, "dual_entry_minute": dual, "entry_sl_same_minute": end.index == idx}


def gap_classification(offsets, values, trade):
    missing = np.setdiff1d(np.arange(WINDOW + 1), offsets, assume_unique=True)
    if not len(missing):
        return "strict", 0, None
    bounded = np.isin([0, 60, 300, WINDOW], offsets).all()
    if not bounded or len(missing) > 5 or (np.diff(missing) == 1).any():
        return ("empty_window" if not len(offsets) else "B"), len(missing), None
    indices = offsets.searchsorted(missing)
    jumps = np.abs(values[indices - 1][:, [3, 7]] - values[indices][:, [0, 4]])
    maximum = float(jumps.max()) / PIP
    if maximum > .2 + 1e-8:
        return "B", len(missing), maximum
    if trade is None:
        entry, finish = WINDOW + 1, WINDOW + 1
    else:
        entry, finish = offsets[[trade["entry_index"], trade["exit"].index]]
    top, bottom = box_edges(offsets, values)
    for index, at in zip(indices, missing):
        prev, nxt = values[index - 1], values[index]
        if min(abs(at - entry), abs(at - finish)) <= 1:
            return "A_unreplayable", len(missing), maximum
        if 60 <= at < 300 and at < entry:
            if touches_between(prev[7], nxt[4], top) or touches_between(prev[3], nxt[0], bottom):
                return "A_unreplayable", len(missing), maximum
        if trade is not None and entry < at < finish:
            liquid = (3, 0) if trade["side"] == 1 else (7, 4)
            if touches_between(prev[liquid[0]], nxt[liquid[1]], trade["stop"]):
                return "A_unreplayable", len(missing), maximum
    return "A_admitted", len(missing), maximum


def valued(trade, offsets, values, addon):
    i, exit_ = trade["entry_index"], trade["exit"]
    end = exit_.index
    side, entry, risk = trade["side"], trade["entry_price"], trade["risk"]
    net = (side * (exit_.price - entry) - 2 * SLIP - addon) * CONTRACT - COMMISSION
    slip = SLIP + addon
    observed = values[i:end+1]
    liquid = observed[:, :4] if side == 1 else observed[:, 4:8]
    pnl = (side * (liquid - entry) - slip) * CONTRACT - COMMISSION / 2
    marks = pnl[:, [0, 1, 2, 3] if side == 1 else [0, 2, 1, 3]]
    before = observed[0, 4] - observed[0, 0]
    marks[0, 0] = (-before - slip) * CONTRACT - COMMISSION / 2
    marks[0, 1] = max(marks[0, 0], marks[0, 3])
    marks[0, 2] = min(marks[0, 0], marks[0, 2], marks[0, 3])
    if exit_.at_open or end == i:
        marks[-1] = net
    else:
        at_open = marks[-1, 0]
        marks[-1] = [at_open, max(at_open, net), min(at_open, net), net]
    times = trade["start"] + offsets[i:end+1] * 60
    return {"day": clock.date(trade["start"]).date().isoformat(), "year": clock.date(trade["start"]).year,
            "entry": int(times[0]), "exit": int(times[-1]), "side": side, "reason": exit_.reason,
            "at_open": exit_.at_open, "entry_price": entry, "exit_price": exit_.price,
            "dual_entry_minute": trade["dual_entry_minute"], "entry_sl_same_minute": trade["entry_sl_same_minute"],
            "stop": trade["stop"], "initial_risk_usd": risk,
            "stop_risk_with_cost_usd": risk + (2 * SLIP + addon) * CONTRACT + COMMISSION,
            "net_R": net / risk, "net_usd_per_lot": net, "margin_quote": trade["margin_quote"]}, times, marks


def dual_touch_h1(jobs, lock):
    folder = jobs / "bottleneck2-monfri-20261119/development"
    hourly = clock.load_sealed(folder, "H1", lock["series"]["GBPUSD"]["H1"], asset="GBPUSD")
    from pass10_institutional_flow import london_day
    recipe = clock.Costs(.007, 5., CONTRACT)
    days = {clock.date(t).date().isoformat() for t in range(START, STOP, clock.DAY)
            if clock.date(t).weekday() < 5
            and london_day(clock.date(t).date(), hourly, recipe)[0] == "ambiguous_first_touch"}
    if len(days) != 173:
        raise ValueError("Pass 10 dual-touch universe drift")
    return days


def stats(trades, day_set, *, target_days=None):
    rows = [(row, times, marks) for row, times, marks in trades
            if row["day"] in day_set and (target_days is None or row["day"] in target_days)]
    trades_only = [r for r, _, _ in rows]
    outcomes = [r["net_R"] for r in trades_only]
    total = fsum(outcomes)
    winners = sorted((r for r in outcomes if r > 0), reverse=True)
    days = sorted(day_set if target_days is None else day_set & target_days)
    meter = equity.EquityMetrics(0., START, [int(np.datetime64(d, "D").astype(int)) for d in days])
    # Use a positive offset solely to avoid percentage denominators near zero.
    meter.peak = balance = 1_000_000.
    for row, times, marks in rows:
        values = balance + marks / row["initial_risk_usd"]
        meter.add(np.r_[times[0], np.repeat(times, 4)], np.r_[balance, values.ravel()], balance)
        balance += row["net_R"]
    if rows and balance < meter.peak:
        meter.update_age(np.array([meter.peak_at]), np.array([STOP - 1]))
    return {"days": len(days), "n": len(rows), "net_R": total, "positive": sum(r > 0 for r in outcomes),
            "top10_win_R": fsum(winners[:10]), "net_without_top10_R": total - fsum(winners[:10]),
            "top10_share_of_winners": fsum(winners[:10]) / fsum(winners) if winners else None,
            "exits": dict(Counter(r["reason"] for r in trades_only)),
            "dual_entry_minutes": sum(r["dual_entry_minute"] for r in trades_only),
            "entry_sl_same_minute": sum(r["entry_sl_same_minute"] for r in trades_only),
            "floating_dd_R": meter.dd if rows else None,
            "underwater_months": meter.max_age[0] / 86400 / (365.2425 / 12) if rows else None}


def trade_groups(valuations, eligible, dual):
    def section(rows, days):
        return {"total": stats(rows, days), "h1_dual": stats(rows, days, target_days=dual),
                "years": {str(y): stats([x for x in rows if x[0]["year"] == y],
                                        {d for d in days if d.startswith(str(y))})["net_R"] for y in clock.YEAR}}
    groups = {}
    for name, rows in valuations.items():
        result = section(rows, eligible)
        result["cl"] = {key: fsum(result["years"][str(y)] for y in years)
                        for key, years in clock.CLUSTERS.items()}
        result["positive_years"] = sum(v > 0 for v in result["years"].values())
        result["sides"] = {label: section([x for x in rows if x[0]["side"] == side], eligible)
                           for side, label in ((1, "BUY"), (-1, "SELL"))}
        groups[name] = result
    return groups


def compare_h1(jobs, m1, eligible):
    from pass11_portfolio import manifest_files

    sources = manifest_files(jobs, "pass10-engine2-institutional-flow-20261120",
                             ["final/london-GBPUSD-sl-active.json"])
    h1 = {r["day"]: r for r in read(sources["final/london-GBPUSD-sl-active.json"])}
    if len(h1) != 1605 or not all("2018-01-01" <= d < "2025-01-01" for d in h1):
        raise ValueError("Pass 10 H1 SL ledger differs from the registered scope")
    m1_by_day = {r["day"]: r for r, _, _ in m1}
    sections = {}
    for name, days in eligible.items():
        both = h1.keys() & m1_by_day.keys() & days
        h1_only = (h1.keys() - m1_by_day.keys()) & days
        m1_only = (m1_by_day.keys() - h1.keys()) & days
        sections[name] = {}
        for year in clock.YEAR:
            prefix = str(year)
            matched = sorted(d for d in both if d.startswith(prefix))
            sections[name][prefix] = {
                "matched_signals": len(matched),
                "side_disagrees": sum(h1[d]["side"] != m1_by_day[d]["side"] for d in matched),
                "h1_net_R_on_match": fsum(h1[d]["net_R"] for d in matched),
                "m1_net_R_on_match": fsum(m1_by_day[d]["net_R"] for d in matched),
                "h1_only_in_covered_days": sum(d.startswith(prefix) for d in h1_only),
                "m1_only_in_covered_days": sum(d.startswith(prefix) for d in m1_only),
                "h1_outside_m1_coverage": sum(d.startswith(prefix) and d not in days for d in h1),
            }
    return sections

def scan(jobs, folder, out):
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    if sha(lock_path) != clock.LOCK_SHA:
        raise ValueError("Holdout lock drift")
    specs, fees = profiles()
    if any(v["GBPUSD"]["trade_contract_size"] != CONTRACT for v in specs.values()):
        raise ValueError("GBPUSD contract drift")
    lock = read(lock_path)
    manifest = read(folder / "manifest.json")
    if manifest["source"] != SYMBOL or manifest["protocol_commit"] != PROTOCOL:
        raise ValueError("Unregistered M1 source")
    dual = dual_touch_h1(jobs, lock)
    cohort = {"strict": set(), "extended": set()}
    rows = {p: [] for p in PROFILES}
    gap_table = []
    coverage = defaultdict(Counter)
    out.mkdir(exist_ok=False)
    for year in clock.YEAR:
        times, values = load_m1(folder, year, manifest["years"][str(year)])
        first, last = [n // 1000 for n in qdm.year_limits(year)]
        for stamp in range(first, last, clock.DAY):
            day = clock.date(stamp).date()
            if day.weekday() >= 5:
                continue
            start = epoch(day, 8, clock.LONDON)
            lo, hi = times.searchsorted([start, start + (WINDOW + 1) * 60])
            offsets = (times[lo:hi] - start) // 60
            quotes = values[lo:hi]
            can_model = len(offsets) == WINDOW + 1 or np.isin([0, 60, 300, WINDOW], offsets).all()
            trade = execution(start, offsets, quotes) if can_model else None
            status, missing, jump = gap_classification(offsets, quotes, trade)
            day_key = day.isoformat()
            coverage[str(year)][status] += 1
            if status != "strict":
                gap_table.append({"day": day_key, "group": status, "missing_minutes": missing, "jump_pips": jump})
            if status in ("strict", "A_admitted"):
                cohort["extended"].add(day_key)
                if status == "strict":
                    cohort["strict"].add(day_key)
                if trade is not None:
                    for name, addon in PROFILES.items():
                        rows[name].append(valued(trade, offsets, quotes, addon))
        print(year, dict(coverage[str(year)]), flush=True)
    summaries = {}
    for name, days in cohort.items():
        summaries[name] = trade_groups(rows, days, dual)
        results = summaries[name][STRESS]
        summaries[name]["gate"] = (all(x > 0 for x in results["cl"].values()) and results["positive_years"] >= 5
                                    and results["total"]["net_without_top10_R"] > 0)
    verdict = "GBPUSD_SURVIVED_M1_CHECK" if all(v["gate"] for v in summaries.values()) else "GBPUSD_FAILED_M1_CHECK"
    for profile, all_trades in rows.items():
        write(out / f"{profile}-trades.json", [r for r, _, _ in all_trades])
    write(out / "eligibility.json", {k: sorted(v) for k, v in cohort.items()})
    write(out / "gap-days.json", gap_table)
    write(out / "m1-result.json", {"protocol_commit": PROTOCOL, "verdict": verdict, "fees": fees,
                                   "coverage": coverage, "results": summaries, "h1_dual_days": sorted(dual),
                                   "h1_m1_matched_signals": compare_h1(jobs, rows[STRESS], cohort),
                                   "source_manifest_sha256": sha(folder / "manifest.json"),
                                   "holdout_rows": 0, "order_send_count": 0,
                                   "track3_eligible": verdict == "GBPUSD_SURVIVED_M1_CHECK"})
    print(verdict, flush=True)
    return verdict, rows[STRESS], cohort


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=["prepare", "seal", "scan"])
    parser.add_argument("--jobs", type=Path, required=True)
    parser.add_argument("--job", type=Path, required=True)
    parser.add_argument("--year", type=int, choices=clock.YEAR)
    parser.add_argument("--output", type=Path, help="New scan destination for a separately recorded retry")
    options = parser.parse_args()
    source = options.job / "development-m1"
    if options.mode == "prepare":
        prepare(options.job, source, options.year)
    elif options.mode == "seal":
        seal_source(options.job, source)
    else:
        destination = options.output or options.job / "verified"
        verdict, rows, eligible = scan(options.jobs, source, destination)
        if verdict == "GBPUSD_SURVIVED_M1_CHECK":
            from pass11_portfolio import run
            result = run(options.jobs, destination, rows, eligible)
            print(result["verdict"], flush=True)
