"""Pass 12 USDJPY forensic audit on frozen Stress_05 trades and M1 equity."""

import argparse
from collections import defaultdict
from math import fsum, isclose
from pathlib import Path

import numpy as np

import pass5_usdjpy_tokyo as clock
import pass7b_usdjpy_equity as eq
from native_ftmo_monfri_seal import START, STOP, read, sha, write
from pass11_portfolio import frozen_usdjpy, manifest_files
from pass7b_usdjpy_research import accounts
from selective_win_diagnosis import UNKNOWN

PROTOCOL = "fdef13d5a30dd1299ff47a1edf1126919303191b"
MONTH = 86400 * 365.2425 / 12


def estimated_cost(bid, ask, width):
    if not 0 < bid <= ask or width <= 0:
        raise ValueError("Invalid USDJPY entry quote or box")
    midpoint = (bid + ask) / 2
    cost = ask - bid + eq.COMMISSION * midpoint / eq.CONTRACT
    cost += 2 * eq.BASE_SIDE_SLIPPAGE + eq.PROFILE["M1_Real_Stress_05"]
    return 100 * cost / width


def entry_bucket(hour):
    if 3 <= hour < 7:
        return "03:00–06:59"
    if 7 <= hour < 10:
        return "07:00–09:59"
    raise ValueError("USDJPY fill outside frozen OCO")


def attach_features(atr_times, atr):
    def feature(day, offsets, prices, trade):
        top, bottom = eq.box_edges(prices[offsets < 180])
        width = top - bottom
        entry = trade.entry_second
        bid, ask = map(float, prices[trade.entry, [0, 4]])
        cost = estimated_cost(bid, ask, width)
        i = atr_times.searchsorted(day + 3 * clock.HOUR, side="right") - 1
        vol = float(atr[i]) if i >= 0 and np.isfinite(atr[i]) and atr[i] > 0 else None
        relative = width / vol if vol else None
        return {
            "box_width_pip": width / clock.PIP, "estimated_friction_over_box_pct": cost,
            "cost_bucket": ">12%" if cost > 12 else "6–12%" if cost >= 6 else "<6%",
            "atr_d1_pip": vol / clock.PIP if vol else None,
            "atr_visible_utc": int(atr_times[i]) if vol else None,
            "box_over_atr": relative,
            "atr_bucket": "unknown" if relative is None else
                          "<0.25" if relative < .25 else "0.25–<0.50" if relative < .5 else "≥0.50",
            "direction": "BUY" if trade.side == 1 else "SELL",
            "entry_window": entry_bucket(clock.date(entry).hour),
        }
    return feature


def path_intervals(times, values):
    """Find an actual peak/trough pair and longest unrecovered excursion on ordered marks."""
    peaks = np.maximum.accumulate(values)
    drops = peaks - values
    bottom = int(drops.argmax())
    peak_hits = np.flatnonzero(values >= peaks)
    peak_at = int(peak_hits[peak_hits.searchsorted(bottom, side="right") - 1])
    intervals = [(a, b, False) for a, b in zip(peak_hits, peak_hits[1:]) if b > a + 1]
    if peak_hits[-1] < len(times) - 1:
        intervals.append((peak_hits[-1], len(times) - 1, True))
    age_a, age_b, censored = max(intervals, key=lambda w: times[w[1]] - times[w[0]],
                                  default=(0, 0, False))
    def episode(a, b):
        return {"start": int(times[a]), "end": int(times[b]),
                "start_equity": float(values[a]), "end_equity": float(values[b])}
    return {"peak_dd": episode(peak_at, bottom) | {"drawdown": float(drops[bottom])},
            "underwater": episode(age_a, age_b) | {
                "censored": censored, "months": float((times[age_b] - times[age_a]) / MONTH)}}


def timeline(tape, cash=None, initial=0.):
    """Rebuild ordered minute envelopes on the same ledger used by the parent engine."""
    stamps, values = [np.array([START])], [np.array([initial])]
    balance = initial
    cash = {r["day"]: r for r in cash} if cash is not None else None
    for row, ts, marks in tape:
        if cash is not None and row["day"] not in cash:
            continue
        lot = cash[row["day"]]["lots"] if cash is not None else 1. / row["initial_risk_usd"]
        end = row["exit"]
        after = balance + lot * row["net_usd_per_lot"]
        stamps.append(np.r_[ts[0], np.repeat(ts, 4), end])
        values.append(np.r_[balance, balance + lot * marks.ravel(), after])
        balance = after
    stamps.append(np.array([STOP]))
    values.append(np.array([balance]))
    return np.concatenate(stamps), np.concatenate(values)


def tally(tape, *, floating=True):
    rows = [item[0] for item in tape]
    winners = [r for r in rows if r["net_R"] > 0]
    losses = [r for r in rows if r["net_R"] < 0]
    known_labels = sum(r["winner_label"] != UNKNOWN for r in winners)
    top = fsum(sorted((r["net_R"] for r in winners), reverse=True)[:10])
    result = {"n": len(rows), "net_R": fsum(r["net_R"] for r in rows),
              "win_rate": len(winners) / len(rows) if rows else None,
              "losing_R": -fsum(r["net_R"] for r in losses),
              "winning_R": fsum(r["net_R"] for r in winners),
              "top10_R": top,
              "winner_label_coverage": known_labels / len(winners) if winners else None}
    if floating:
        result["floating_dd_R"] = path_intervals(*timeline(tape))["peak_dd"]["drawdown"]
    return result


def partitions(tape, axis):
    by = defaultdict(list)
    for item in tape:
        row = item[0]
        key = row[axis]
        by[key].append(item)
    return {key: tally(value) for key, value in by.items()}


def episode_breakdown(tape, episode, *, cash=None):
    section = [item for item in tape if item[0]["exit"] >= episode["start"]
               and episode["end"] >= item[0]["entry"]]
    marks = {r["day"]: r for r in cash} if cash is not None else {}
    cash_data = [marks[r["day"]] for r, *_ in section if r["day"] in marks
                 and episode["start"] < r["exit"] <= episode["end"]]
    quarters = defaultdict(list)
    for item in section:
        day = clock.date(item[0]["entry"])
        quarters[f"{day.year}-Q{(day.month - 1)//3+1}"].append(item)
    return {
        **episode, "trades_overlapping": len(section),
        "realized_cash_usd_inside": fsum(r["net_usd"] for r in cash_data),
        "quarters": {k: tally(v, floating=False) for k, v in quarters.items()},
        "years": {str(y): tally([x for x in section if x[0]["year"] == y], floating=False)
                  for y in sorted({x[0]["year"] for x in section})},
        "axes": {axis: partitions(section, axis) for axis in
                 ("cost_bucket", "atr_bucket", "direction", "entry_window")},
    }


def replay(book, risk, tape, days):
    rows, times, marks = zip(*tape, strict=True)
    return eq.account_replay(book, risk, rows, marks,
                             [int(np.datetime64(d, "D").astype(int)) for d in sorted(days)],
                             observed_times=times)


def audit(jobs, destination):
    lp = clock.ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    if sha(lp) != clock.LOCK_SHA:
        raise ValueError("Holdout lock drift")
    lock = read(lp)
    if sha(clock.AUDIT) != lock["audit_sha256"]:
        raise ValueError("Target profile drift")
    daily = clock.load_sealed(jobs / "bottleneck2-monfri-20261119/development", "D1",
                              lock["series"]["USDJPY"]["D1"])
    tape, eligibility = frozen_usdjpy(jobs, entry_features=attach_features(*clock.atr_checkpoints(daily)))
    if (len(tape), len(eligibility["strict"]), len(eligibility["extended"])) != (1437,1334,1564):
        raise ValueError("USDJPY parent sample identity")
    books, bindings = accounts(jobs, read(clock.AUDIT))
    p7_path, = manifest_files(jobs,"pass7b-usdjpy-qdm-equity-20261120",["verified/result.json"]).values()
    p8_path, = manifest_files(jobs,"pass8-engine2-and-m1-gaps-20261120",["usdjpy/gap-summary.json"]).values()
    p7, p8 = read(p7_path), read(p8_path)
    destination.mkdir(exist_ok=False)
    results = {}
    parent_hashes = {"pass7b_result":sha(p7_path), "pass8_gap_summary":sha(p8_path),
                     "usd_d1":lock["series"]["USDJPY"]["D1"]["development_sha256"]}
    for name, days in eligibility.items():
        all_rows = [tape[d] for d in sorted(days) if d in tape]
        kept = [item for item in all_rows if item[0]["estimated_friction_over_box_pct"] <= 12.]
        stats = {}
        for label, sample in (("baseline",all_rows),("cost12",kept)):
            rows = [item[0] for item in sample]
            years, clusters, annual = eq.years_and_clusters(rows,"net_R")
            stats[label] = {"trades": len(sample), "net_R_years": years, "net_R_clusters": clusters,
                            "net_R_annual": annual, "total": tally(sample), "accounts": {},
                            "cluster_trades": {k:sum(r["year"] in group for r in rows)
                                               for k, group in clock.CLUSTERS.items()}}
        axes = {}
        for k, years in clock.CLUSTERS.items():
            slice_ = [item for item in all_rows if item[0]["year"] in years]
            axes[k] = {axis: partitions(slice_,axis) for axis in
                       ("cost_bucket","atr_bucket","direction","entry_window")}
        episodes, baseline_paths = {}, {}
        for book in books:
            stats["baseline"]["accounts"][book.label] = {}
            stats["cost12"]["accounts"][book.label] = {}
            for risk in (.003,.004):
                before, cash = replay(book,risk,all_rows,days)
                after, _ = replay(book,risk,kept,days)
                key = f"{risk*100:.2f}%"
                stats["baseline"]["accounts"][book.label][key] = before
                stats["cost12"]["accounts"][book.label][key] = after
                if name == "strict":
                    expected = next(x for x in p7["account_equity"]["M1_Real_Stress_05"]
                                    if x["account"] == book.label and x["risk_pct"] == risk*100)
                elif risk == .003:
                    expected = next(x["sensitivity"] for x in p8["books"]
                                    if x["sensitivity"]["account"] == book.label)
                else:
                    expected = None
                if expected and any(not isclose(before[f],expected[f],abs_tol=1e-8) for f in
                                    ("net_usd","peak_floating_dd_pct","worst_daily_loss_pct",
                                     "max_underwater_months")):
                    raise ValueError(f"Parent account replay drift: {name} {book.label} {key}")
                episode = path_intervals(*timeline(all_rows,cash,book.initial))
                dd = episode["peak_dd"]["drawdown"] * 100 / book.initial
                if not isclose(dd,before["peak_floating_dd_pct"],abs_tol=1e-8):
                    raise ValueError("Forensic peak/trough does not reconcile with replay")
                baseline_paths[f"{book.label} {key}"] = episode
                if book.label == "Swing 10k" and risk == .004:
                    episodes = {k:episode_breakdown(all_rows,e,cash=cash) for k,e in episode.items()}
        swing_before = stats["baseline"]["accounts"]["Swing 10k"]
        swing_after = stats["cost12"]["accounts"]["Swing 10k"]
        ok = all(swing_after[r]["net_usd"] > swing_before[r]["net_usd"]
                 and swing_after[r]["peak_floating_dd_pct"] < swing_before[r]["peak_floating_dd_pct"]
                 and swing_after[r]["max_underwater_months"] <= swing_before[r]["max_underwater_months"]
                 for r in swing_before) and min(stats["cost12"]["net_R_clusters"].values()) > 0
        results[name] = {"days":len(days), "comparisons":stats, "baseline_axes":axes,
                         "baseline_episodes":episodes, "baseline_paths":baseline_paths, "retain":ok}
    write(destination / "usd-trades.json", [r for r,*_ in tape.values()])
    result = {"protocol_commit":PROTOCOL,"baseline":"67d1a42","holdout_rows":0,"order_send_count":0,
              "sample_results":results,"swing_spec_bindings":bindings,"parent_hashes":parent_hashes,
              "verdict":"USDJPY_COST_HYGIENE_RETAIN_FOR_RESEARCH" if all(x["retain"] for x in results.values())
                        else "USDJPY_COST_HYGIENE_NOT_RETAINED"}
    write(destination / "usd-result.json",result)
    print(result["verdict"],flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--jobs",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    audit(args.jobs,args.output)
