"""Bounded 544-cell discovery, persisted raw arrays and pre-validation decision."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import subprocess
import time
import numpy as np

from prop_campaign_source import read, write_json
from prop_v10_source import JOB, FIRST, END, sources, sha
from prop_v10_signals import recipes
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_stage0_scanner import measure, summaries

PROTOCOL = Path("planning/research/ENTERPRISE-ALPHA-V10-PROTOCOL-20261115.md")


def scan(asset_sources):
    calendar = gold_calendar(FIRST, END)
    measurements, signal_cache, timings = [], {}, {}
    for asset, bars in asset_sources.items():
        start = time.perf_counter()
        raw = recipes(bars, asset, FIRST, END, calendar)
        signal_cache[asset] = raw
        timings[asset] = dict(signal_seconds=time.perf_counter()-start, recipes=len(raw))
        start = time.perf_counter()
        for r in raw:
            measurements.extend(measure(asset, r, bars, calendar, FIRST, END))
        timings[asset]["markout_seconds"] = time.perf_counter()-start
        print(dict(stage="V10_array_scan", asset=asset, **timings[asset]), flush=True)
    if len(measurements) != 544:
        raise ValueError("registered_matrix_budget_changed")
    start = time.perf_counter()
    stats, daily = summaries(measurements, FIRST, END, 544)
    timings["statistics_seconds"] = time.perf_counter()-start
    return measurements, signal_cache, stats, daily, timings


def run():
    if (JOB / "discovery.json").exists():
        raise ValueError("preserve_V10_existing_attempt")
    files = [PROTOCOL, Path(__file__), Path(__file__).with_name("prop_v10_signals.py"),
             Path(__file__).with_name("quant_core") / "vectorized_stage0_scanner.py"]
    write_json(JOB / "discovery-registration.json", dict(
        commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        pins={str(p): sha(p) for p in files}, trials=544, dev_years=list(range(2018, 2024)),
        source_admission_sha256=sha(JOB / "source-admission.json"), historical_exposure=True,
        validation_status="CLOSED_UNTIL_COMMITTED_ELIGIBLE_COMPOSITION"))
    start = time.perf_counter()
    data = sources()
    io_seconds = time.perf_counter()-start
    start = time.perf_counter()
    measurements, raw, stats, daily, timings = scan(data)
    scan_seconds = time.perf_counter()-start
    eligible = [s for s in stats if s["eligible"]]
    ranked = sorted(stats, key=lambda s: (s["score"], sum(c["net"]["SYM"]["raw"] for c in s["clusters"])), reverse=True)
    packed = {}
    for j, m in enumerate(measurements):
        for field in ("at", "entry_at", "exit_at", "deadline", "side", "entry_price", "exit_price",
                      "stop", "natural", "friction", "ratio", "ok", "admitted", "years"):
            packed[f"{j}:{field}"] = m[field]
        for model in ("SYM", "ASYM"):
            for field in ("gross", "commission", "funding", "funding_multipliers", "net", "net_R"):
                packed[f"{j}:{model}:{field}"] = m["model"][model][field]
    np.savez_compressed(JOB / "raw-matrix.npz", **packed)
    np.savez_compressed(JOB / "daily-R.npz", daily=daily)
    write_json(JOB / "raw-signals.json", {asset: [dict(r, at=r["at"].tolist(),
        side=r["side"].tolist(), stop=r["stop"].tolist()) for r in rows] for asset, rows in raw.items()})
    write_json(JOB / "discovery.json", dict(rows=stats, top15=ranked[:15],
        eligible=[dict(asset=r["asset"], recipe=r["recipe"], horizon=r["horizon"]) for r in eligible],
        economics_pass=sum(r["economic_gate"] for r in stats), trials=544,
        io_seconds=io_seconds, scan_seconds=scan_seconds, timings=timings,
        config_years_per_second=544*6/scan_seconds,
        first=FIRST, end=END, costs_conditional=True, no_stop_or_account=True,
        matrix_sha256=sha(JOB / "raw-matrix.npz"), source_sha256=sha(JOB / "source-admission.json")))
    decision = dict(stage="STAGE0", trials=544, eligible=[dict(asset=r["asset"],
        recipe=r["recipe"], horizon=r["horizon"]) for r in eligible],
        economics_pass=sum(r["economic_gate"] for r in stats),
        composition=None, validation="NEEDS_STAGE1_AND_COMMITTED_FREEZE" if eligible else "CANCELED_FAILED_STAGE0",
        lifecycle="NOT_RUN", clean_OOS=False, source_conditional=True)
    write_json(JOB / "decision.json", decision)
    print(completion_event(decision, scan_seconds), flush=True)


def completion_event(decision, seconds):
    return dict(decision, event="V10_Discovery_complete", scan_seconds=seconds)


if __name__ == "__main__":
    run()
