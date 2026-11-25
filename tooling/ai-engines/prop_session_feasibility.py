"""Measure cost-to-stop geometry and endpoint headroom without trading signals."""
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

from prop_n1_screen import DEVELOPMENT_YEARS, WORKSPACE, exact_hour, verify_commit
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, save
from prop_v26_common import DEV_END, FIRST, ROOT, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.native_hourly_source import IndexedUs500Store
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_sl_active_kernel import money
from sealed_m1_review import cash_sessions
import prop_v21_common as evidence

PROTOCOL = WORKSPACE / 'planning/research/PROP-SESSION-FEASIBILITY-20261118.md'
BASE = ROOT / 'prop-session-feasibility-20261118' / 'attempt-2'


def inspect(asset, bars, sessions):
    scale = 100000 if asset == 'EURUSD' else 1000
    rows = []
    for day, minutes in sessions.items():
        if len(minutes) != 390:
            continue
        start, end = minutes[60], minutes[300]
        opening = exact_hour(bars, start)
        e, x = bars['t'].searchsorted([start, end])
        if (opening is None or x == len(bars) or bars['t'][e] != start or bars['t'][x] != end):
            rows.append(dict(day=day, known=False))
            continue
        entry = np.array([bars['ao'][e], bars['bo'][e]])
        close = np.array([bars['bo'][x], bars['ao'][x]])
        side = np.array([1, -1])
        stop = np.array([opening['bl'].min()-1, opening['ah'].max()+1])
        natural = side*(entry-stop)
        entry_at = np.full(2, start, dtype='int64')
        exit_at = np.full(2, end, dtype='int64')
        friction = float((entry[0]-entry[1])/scale)-money(asset, 'SYM', side, entry, entry, entry_at, entry_at, 'MARKET')['net']
        net = money(asset, 'SYM', side, entry, close, entry_at, exit_at, 'MARKET')['net']
        multiple = 10 if asset == 'XAUUSD' else 1  # Gold per-ounce commission has 4 decimal places.
        costs = np.rint(friction * scale * multiple).astype('int64')
        fits = (natural > 0) & (100 * costs <= 12 * natural * multiple)
        room = fits & (net + 1e-12 >= friction)
        rows.append(dict(day=day, known=True, natural=(natural/scale).tolist(),
                         friction=friction.tolist(), fits=fits.tolist(), net=net.tolist(), room=room.tolist()))
    return rows


def summarize(rows):
    annual = defaultdict(Counter)
    for row in rows:
        values = annual[row['day'][:4]]
        values['scheduled'] += 1
        if not row['known']:
            continue
        values['priced'] += 1
        values['either_side_fits'] += any(row['fits'])
        values['both_sides_fit'] += all(row['fits'])
        values['ex_post_room'] += any(row['room'])
    return {year: dict(counts) for year, counts in sorted(annual.items())}


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    fixtures = Path(__file__).resolve().parent/'fixtures'
    calendars = [fixtures/f'nyse-{y}.json' for y in DEVELOPMENT_YEARS]
    admission = ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json'
    dev_m1 = ROOT/'evidence-and-lifecycle-v14-20261115/source-dev-admission.json'
    runtime = JobWorkspace(BASE, WORKSPACE)
    output = runtime.activate()
    try:
        with bindings(evidence, JOB=output):
            save('registration.json',dict(inputs={p.name:sha(p) for p in (admission,dev_m1,*calendars,PROTOCOL,Path(__file__))},
                 first=FIRST, cutoff_exclusive=DEV_END))
            sessions = {day: stamp for path in calendars for day, stamp in cash_sessions(read(path)).items()}
            source = read(admission)['minute_indices']['US500']
            source = dict(source, years=[book for book in source['years'] if book['year'] in DEVELOPMENT_YEARS])
            result = {}
            for asset in ('EURUSD','XAUUSD','US500'):
                bars = IndexedUs500Store(source,FIRST,DEV_END).bars() if asset=='US500' else bars_for(asset,True)
                if bars['t'][-1] >= DEV_END:
                    raise ValueError('SESSION_FEASIBILITY_DEVELOPMENT_FENCE')
                rows = inspect(asset,bars,sessions)
                result[asset] = summarize(rows)
                compressed(asset+'-room',rows)
                print(asset,result[asset],flush=True)
            save('session-feasibility.json',dict(assets=result, registration=sha(output/'registration.json')))
    finally:
        runtime.close()


if __name__ == '__main__':
    main()
