"""Registered US500 Stage-0 markout using lagged daily VIX closes."""
from collections import Counter
import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
import subprocess

import numpy as np

from prop_n1_screen import DEVELOPMENT_YEARS, WORKSPACE, classify, exact_hour, intervals, verify_commit
from prop_v21_common import compressed, save
from prop_v26_common import DEV_END, FIRST, ROOT, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.native_hourly_source import IndexedUs500Store
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_sl_active_kernel import money
from quant_core.vectorized_stage0_scanner import DAY, HOUR, endpoint_indices
from sealed_m1_review import cash_sessions
import prop_v21_common as evidence

ASSET = "US500"
CANDIDATE = "US500-VIX-DIVERGENCE-B0"
PROTOCOL = WORKSPACE / "planning/research/PROP-US500-VIX-DIVERGENCE-PROTOCOL-20261118.md"
FIXTURES = Path(__file__).resolve().parent / "fixtures"
BASE = ROOT / "prop-us500-vix-stage0-20261118"
SOURCE = "https://fred.stlouisfed.org/graph/fredgraph.csv?id=VIXCLS&cosd=2018-01-01&coed=2023-12-31"


def vix_values(raw):
    reader = csv.reader(StringIO(raw.decode("utf-8-sig")))
    header = next(reader, None)
    if header not in (["observation_date", "VIXCLS"], ["DATE", "VIXCLS"]):
        raise ValueError("VIXCLS_CSV_SCHEMA")
    values = {}
    previous = ""
    for key, value in reader:
        day = date.fromisoformat(key)
        if day.year not in DEVELOPMENT_YEARS or key <= previous:
            raise ValueError("VIXCLS_TIMESTAMP_SCOPE_OR_ORDER")
        previous = key
        if value in ("", "."):
            continue
        amount = Decimal(value)
        if not amount.is_finite() or amount <= 0:
            raise ValueError("VIXCLS_INVALID_CLOSE")
        values[key] = amount
    if {date.fromisoformat(key).year for key in values} != set(DEVELOPMENT_YEARS):
        raise ValueError("VIXCLS_INCOMPLETE_YEAR_SET")
    return values


def signal(vix_change, price_change):
    if vix_change > 0 and price_change > 0:
        return -1
    if vix_change < 0 and price_change < 0:
        return 1
    return 0


def opportunities(bars, sessions, volatility):
    days = list(sessions)
    closes = {}
    observations = []
    for index, (day, minutes) in enumerate(sessions.items()):
        last = bars["t"].searchsorted(minutes[-1])
        if last < len(bars) and bars["t"][last] == minutes[-1]:
            closes[day] = int(bars["bc"][last])
        row = dict(day=day, state="HALF_DAY", side=0)
        observations.append(row)
        if len(minutes) != 390:
            continue
        if index < 2:
            row.update(state="WARMUP")
            continue
        start, end = days[index - 2:index]
        row.update(prior_dates=[start, end], state="PREDICTOR_UNKNOWN")
        if not all(key in closes and key in volatility for key in (start, end)):
            continue
        vix_change = volatility[end] - volatility[start]
        price_change = closes[end] - closes[start]
        side = signal(vix_change, price_change)
        row.update(state="SIGNAL" if side else "NO_SIGNAL", side=side,
                   vix_change=str(vix_change), prior_price_change_units=price_change)
        if side:
            at = minutes[60]
            opening = exact_hour(bars, at)
            stop = None
            if opening is not None:
                stop = int(opening["bl"].min()) - 1 if side == 1 else int(opening["ah"].max()) + 1
            row.update(decision=at, cash_close=minutes[-1] + 60000, stop=stop)
    return observations


def markout(bars, rows):
    at = np.array([r["decision"] for r in rows], dtype="int64")
    sides = np.array([r["side"] for r in rows], dtype="int64")
    entry, has_entry = endpoint_indices(bars, at, DEV_END)
    starts = bars["t"][entry]
    exit_, has_exit = endpoint_indices(bars, starts + 4 * HOUR, DEV_END)
    ends = bars["t"][exit_]
    cutoff = np.array([r["cash_close"] for r in rows], dtype="int64")
    valid = has_entry & has_exit & (starts // DAY == ends // DAY) & (ends < cutoff) & (ends < DEV_END)
    price = np.where(sides == 1, bars["ao"][entry], bars["bo"][entry])
    close = np.where(sides == 1, bars["bo"][exit_], bars["ao"][exit_])
    net = money(ASSET, "SYM", sides, price, close, starts, np.maximum(starts, ends), "MARKET")["net"]
    friction = bars["ao"][entry] - bars["bo"][entry] + 2500
    for i, row in enumerate(rows):
        if not valid[i]:
            row.update(entry_at=None, exit_at=None, natural_units=None, net=None, friction_units=None, pass_cost=False)
            continue
        natural = None if row["stop"] is None else int(sides[i] * (price[i] - row["stop"]))
        row.update(entry_at=int(starts[i]), exit_at=int(ends[i]), natural_units=natural,
                   entry_units=int(price[i]), exit_units=int(close[i]), net=round(float(net[i]), 2),
                   friction_units=int(friction[i]),
                   pass_cost=natural is not None and 100 * int(friction[i]) <= 12 * natural)


def summarize(observations, baseline_days):
    annual = []
    for year in DEVELOPMENT_YEARS:
        sessions = [r for r in observations if r["day"][:4] == str(year)]
        states = Counter(r["state"] for r in sessions)
        calendar = len(sessions) - states["WARMUP"] - states["HALF_DAY"]
        raw = [r for r in sessions if r["state"] == "SIGNAL"]
        priced = [r for r in raw if r["net"] is not None]
        geometry = [r for r in priced if (r["natural_units"] or 0) > 0]
        net = np.array([r["net"] for r in priced])
        basis = np.array([r["decision"] for r in priced], dtype="int64")
        natural = np.array([r["natural_units"] / 1000 for r in geometry])
        geometry_friction = np.array([r["friction_units"] / 1000 for r in geometry])
        annual.append(dict(
            year=year, calendar_counts=dict(states), predictor_coverage=(calendar - states["PREDICTOR_UNKNOWN"]) / calendar,
            raw=len(raw), buy=sum(r["side"] == 1 for r in raw), sell=sum(r["side"] == -1 for r in raw),
            empty_months=12 - len({r["day"][:7] for r in raw}),
            days_without_baseline=sum(r["decision"] // DAY not in baseline_days for r in raw),
            priced=len(priced), coverage=len(priced) / len(raw) if raw else None,
            missing_or_invalid_stop=len(priced) - len(geometry),
            median_natural=float(np.median(natural)) if geometry else None,
            median_scale=float(np.median(geometry_friction) / np.median(natural)) if geometry else None,
            retention=sum(r["pass_cost"] for r in raw) / len(raw) if raw else None,
            mean_friction=sum(r["friction_units"] for r in priced) / (1000 * len(priced)) if priced else None,
            mean_net=float(net.mean()) if priced else None,
            net_quantiles=np.quantile(net, [.1, .5, .9]).tolist() if priced else None,
            mean_net_week_bootstrap_95=intervals(net, basis)))
    return annual


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE, WORKSPACE)
    output = runtime.activate()
    try:
        admission = ROOT / "ensemble-and-storage-v11-20261115/source-admission-v11.json"
        baseline = V19 / "Dev-OLHC-PRIMARY-trades.json"
        calendars = [FIXTURES / f"nyse-{year}.json" for year in DEVELOPMENT_YEARS]
        with bindings(evidence, JOB=output):
            save("registration.json", dict(candidate=CANDIDATE, protocol_sha256=sha(PROTOCOL), code_sha256=sha(__file__),
                 head=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
                 first=FIRST, end_exclusive=DEV_END, vix_url=SOURCE,
                 pins={p.name: sha(p) for p in (admission, baseline, *calendars)}))
            raw = subprocess.check_output(["curl.exe", "-q", "--fail", "--silent", "--show-error",
                                            "--connect-timeout", "8", "--max-time", "25", "--retry", "1",
                                            "--max-filesize", "65536", "--proto", "=https", SOURCE], timeout=60)
            volatility = vix_values(raw)
            with (output / "VIXCLS-2018-2023.csv").open("xb") as stream:
                stream.write(raw)
            print(f"Scoped VIX series admitted with {len(volatility)} daily closes", flush=True)
            source = read(admission)["minute_indices"][ASSET]
            source = dict(source, years=[book for book in source["years"] if book["year"] in DEVELOPMENT_YEARS])
            if {book["year"] for book in source["years"]} != set(DEVELOPMENT_YEARS):
                raise ValueError("US500_VIX_SOURCE_YEAR_SET")
            bars = IndexedUs500Store(source, FIRST, DEV_END).bars()
            sessions = {day: minutes for file in calendars for day, minutes in cash_sessions(read(file)).items()}
            observations = opportunities(bars, sessions, volatility)
            markout(bars, [r for r in observations if r["state"] == "SIGNAL"])
            base_days = {r["entry_msc"] // DAY for r in read(baseline)}
            annual = summarize(observations, base_days)
            reasons = classify(annual)
            for row in annual:
                if row["predictor_coverage"] < .99:
                    reasons.setdefault("DATA_PATH_INCOMPLETE", []).append(f"{row['year']}:LT99PCT_PREDICTOR")
            compressed("session-observations", observations)
            save("stage0-results.json", dict(candidate=CANDIDATE, years=annual, reasons=reasons, stage0_passed=not reasons,
                 vix_sha256=sha(output / "VIXCLS-2018-2023.csv"), registration=sha(output / "registration.json")))
            print([(row["year"], row["raw"], row["mean_net"]) for row in annual], reasons, flush=True)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
