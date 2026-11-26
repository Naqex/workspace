"""Development-only EURUSD Stage-0 screen using two lagged DGS2 observations."""
from bisect import bisect_left
from collections import Counter
import csv
from datetime import date
from decimal import Decimal
from io import StringIO
from pathlib import Path
from statistics import mean, median
import subprocess

import numpy as np

from prop_n1_screen import DEVELOPMENT_YEARS, WORKSPACE, classify, exact_hour, intervals, verify_commit
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, save
from prop_v26_common import DEV_END, FIRST, ROOT, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
from sealed_m1_review import cash_sessions
import prop_v21_common as evidence

PROTOCOL = WORKSPACE / 'planning/research/PROP-EURUSD-US-RATES-PROTOCOL-20261118.md'
BASE = ROOT / 'prop-eurusd-us-rates-20261118'
URL = 'https://fred.stlouisfed.org/graph/fredgraph.csv?id=DGS2&cosd=2018-01-01&coed=2023-12-31'
FRICTION_STEPS = 19


def parse_rates(raw):
    reader = csv.reader(StringIO(raw.decode('utf-8-sig')))
    if next(reader, None) not in (['observation_date', 'DGS2'], ['DATE', 'DGS2']):
        raise ValueError('DGS2_SCHEMA')
    previous, rates = '', {}
    for day, value in reader:
        stamp = date.fromisoformat(day)
        if stamp.year not in DEVELOPMENT_YEARS or day <= previous:
            raise ValueError('DGS2_DATE_SCOPE_OR_ORDER')
        previous = day
        if value not in ('', '.'):
            bp = Decimal(value) * 100
            if not bp.is_finite() or bp != bp.to_integral_value():
                raise ValueError('DGS2_RATE_GRID')
            rates[day] = int(bp)
    if {date.fromisoformat(day).year for day in rates} != set(DEVELOPMENT_YEARS):
        raise ValueError('DGS2_MISSING_YEAR')
    return rates


def rates_before(day, rates, dates):
    idx = bisect_left(dates, day)
    if idx < 2:
        return None
    old, new = dates[idx - 2:idx]
    if (date.fromisoformat(day) - date.fromisoformat(old)).days > 7:
        return None
    return old, new, rates[new] - rates[old]


def scan(bars, sessions, rates):
    dates = sorted(rates)
    result = []
    for day, minutes in sessions.items():
        if len(minutes) != 390:
            continue
        rate = rates_before(day, rates, dates)
        row = dict(day=day, signal='RATE_UNAVAILABLE', side=0, status='NO_INTENT')
        result.append(row)
        if rate is None:
            continue
        old, new, delta = rate
        row.update(rate_dates=[old, new], delta_bp=delta, signal='BELOW_THRESHOLD')
        if abs(delta) < 2:
            continue
        side = -1 if delta > 0 else 1
        start, end = minutes[60], minutes[300]
        row.update(signal='SIGNAL', side=side, entry_at=start, exit_at=end, net_steps=None,
                   natural_steps=None, status='ENDPOINT_MISSING')
        i, j = bars['t'].searchsorted([start, end])
        if j == len(bars) or bars['t'][i] != start or bars['t'][j] != end:
            continue
        if bars['ao'][i] - bars['bo'][i] != 10 or bars['ao'][j] - bars['bo'][j] != 10:
            raise ValueError('EURUSD_PROXY_SPREAD_MISMATCH')
        entry = int(bars['ao' if side == 1 else 'bo'][i])
        exit_ = int(bars['bo' if side == 1 else 'ao'][j])
        row.update(entry=entry, exit=exit_, net_steps=side * (exit_ - entry) - 9,
                   status='STOP_UNKNOWN_OR_INVALID')
        hour = exact_hour(bars, start)
        if hour is None:
            continue
        stop = int(hour['bl'].min()) - 1 if side == 1 else int(hour['ah'].max()) + 1
        natural = side * (entry - stop)
        row.update(stop=stop, natural_steps=natural)
        if natural > 0:
            row['status'] = 'COST_PASS' if FRICTION_STEPS * 100 <= natural * 12 else 'COST_REJECT'
    return result


def summarize(rows):
    result = []
    for year in DEVELOPMENT_YEARS:
        days = [r for r in rows if r['day'][:4] == str(year)]
        raw = [r for r in days if r['signal'] == 'SIGNAL']
        priced = [r for r in raw if r['net_steps'] is not None]
        geometry = [r['natural_steps'] for r in priced if (r['natural_steps'] or 0) > 0]
        fits = [r['net_steps'] for r in priced if r['status'] == 'COST_PASS']
        pnl = np.asarray([r['net_steps'] for r in priced], dtype=float) / 10
        result.append(dict(year=year, scheduled=len(days), stages=dict(Counter(r['signal'] for r in days)),
            funnel=dict(Counter(r['status'] for r in raw)), raw=len(raw), priced=len(priced),
            buy=sum(r['side'] == 1 for r in raw), sell=sum(r['side'] == -1 for r in raw),
            coverage=len(priced)/len(raw) if raw else None,
            median_natural=median(geometry)/10 if geometry else None,
            median_scale=FRICTION_STEPS/median(geometry) if geometry else None,
            retention=len(fits)/len(raw) if raw else None, mean_friction=FRICTION_STEPS/10,
            mean_net=float(pnl.mean()) if len(pnl) else None, mean_net_cost_pass=mean(fits)/10 if fits else None,
            markout_ci95=intervals(pnl, np.asarray([r['entry_at'] for r in priced], dtype='int64'))))
    return result


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE, WORKSPACE)
    output = runtime.activate()
    try:
        calendar = [Path(__file__).resolve().parent/'fixtures'/f'nyse-{y}.json' for y in DEVELOPMENT_YEARS]
        admission = ROOT/'evidence-and-lifecycle-v14-20261115/source-dev-admission.json'
        with bindings(evidence, JOB=output):
            save('registration.json', dict(source=URL, files={p.name: sha(p) for p in
                 [*calendar, admission, PROTOCOL, Path(__file__)]}, first=FIRST, cutoff_exclusive=DEV_END,
                 head=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip()))
            raw = subprocess.check_output(['curl.exe','-q','--fail','--silent','--show-error','--proto','=https',
                '--max-filesize','65536','--connect-timeout','8','--max-time','25','--retry','1',URL],timeout=60)
            rates = parse_rates(raw)
            path = output/'DGS2-2018-2023.csv'
            with path.open('xb') as stream:
                stream.write(raw)
            sessions = {d: stamps for p in calendar for d, stamps in cash_sessions(read(p)).items()}
            bars = bars_for('EURUSD', True)
            if bars['t'][-1] >= DEV_END:
                raise ValueError('EURUSD_HOLDOUT_FENCE')
            rows = scan(bars, sessions, rates)
            annual = summarize(rows)
            reasons = classify(annual)
            compressed('rates-session-rows', rows)
            save('stage0-results.json',dict(annual=annual, reasons=reasons, stage0_passed=not reasons,
                 rate_closes=len(rates), rates_sha256=sha(path), registration_sha256=sha(output/'registration.json')))
            print(output, [(r['year'],r['raw'],r['mean_net'],r['retention']) for r in annual], reasons, flush=True)
    finally:
        runtime.close()


if __name__ == '__main__':
    main()
