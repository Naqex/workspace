"""One fixed EURUSD reversal of a two-hour return relative to two FX peers."""
from datetime import datetime, timezone
from fractions import Fraction
from pathlib import Path
import subprocess

from prop_eurusd_us_rates import FRICTION_STEPS, summarize
from prop_n1_screen import WORKSPACE, classify, exact_hour, verify_commit
from prop_v15_evidence import bars_for
from prop_v16_paths import CausalFlatSchedule
from prop_v21_common import compressed, save
from prop_v26_common import DEV_END, FIRST, ROOT, read, sha
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.job_workspace import JobWorkspace
from quant_core.native_hourly_source import PairedHourlyStore
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import DAY, HOUR
import prop_v21_common as evidence

PROTOCOL = WORKSPACE / 'planning/research/PROP-OIL-CAD-AND-FX-RESIDUAL-PROTOCOL-20261118.md'
BASE = ROOT / 'prop-fx-residual-stage0-20261118'
THRESHOLD = Fraction(1, 1000)


def bid_return(open_, close):
    return Fraction(int(close) - int(open_), int(open_))


def choose(residual):
    if abs(residual) < THRESHOLD:
        return 0
    return -1 if residual > 0 else 1


def scan(eur, gbp, aud, schedule):
    peers = [{int(row['t']): row for row in bars} for bars in (gbp, aud)]
    rows = []
    for day in range(FIRST, DEV_END, DAY):
        calendar_day = datetime.fromtimestamp(day / 1000, timezone.utc)
        start, at, end = (day + hour * HOUR for hour in (12, 14, 18))
        if (calendar_day.weekday() > 4 or schedule.off_kind(at, 'EURUSD')
                or schedule.off_kind(end, 'EURUSD') or schedule.cutoff(at, 'EURUSD') < end):
            continue
        row = dict(day=calendar_day.date().isoformat(), signal='PREDICTOR_MISSING', side=0, status='NO_INTENT')
        rows.append(row)
        first, last = exact_hour(eur, at - HOUR), exact_hour(eur, at)
        if first is None or last is None or any(start not in p or start + HOUR not in p for p in peers):
            continue
        changes = [bid_return(p[start]['bo'], p[start + HOUR]['bc']) for p in peers]
        residual = bid_return(first[0]['bo'], last[-1]['bc']) - sum(changes) / 2
        side = choose(residual)
        row.update(signal='SIGNAL' if side else 'BELOW_THRESHOLD', side=side,
                   residual_numerator=residual.numerator, residual_denominator=residual.denominator)
        if not side:
            continue
        lo, hi = ('bl', 'ah')
        stop = (int(min(first[lo].min(), last[lo].min())) - 1 if side == 1
                else int(max(first[hi].max(), last[hi].max())) + 1)
        row.update(entry_at=at, exit_at=end, stop=stop, net_steps=None,
                   natural_steps=None, status='ENDPOINT_MISSING')
        i, j = eur['t'].searchsorted([at, end])
        if j == len(eur) or eur['t'][i] != at or eur['t'][j] != end:
            continue
        if eur['ao'][i] - eur['bo'][i] != 10 or eur['ao'][j] - eur['bo'][j] != 10:
            raise ValueError('EURUSD_PROXY_SPREAD_MISMATCH')
        entry = int(eur['ao' if side == 1 else 'bo'][i])
        exit_ = int(eur['bo' if side == 1 else 'ao'][j])
        natural = side * (entry - stop)
        row.update(entry=entry, exit=exit_, natural_steps=natural,
                   net_steps=side * (exit_ - entry) - 9, status='STOP_UNKNOWN_OR_INVALID')
        if natural > 0:
            row['status'] = 'COST_PASS' if FRICTION_STEPS * 100 <= 12 * natural else 'COST_REJECT'
    return rows


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE, WORKSPACE)
    output = runtime.activate()
    try:
        v11 = ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json'
        v14 = ROOT/'evidence-and-lifecycle-v14-20261115/source-dev-admission.json'
        with bindings(evidence, JOB=output):
            save('registration.json', dict(files={p.name: sha(p) for p in (v11, v14, PROTOCOL, Path(__file__))},
                 first=FIRST, cutoff_exclusive=DEV_END,
                 head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                 order=['OIL_CAD_SOURCE_BLOCKED', 'EURUSD_FX_RESIDUAL']))
            eur = bars_for('EURUSD', True)
            indexes = read(v11)['hourly_indices']
            peers = []
            for asset in ('GBPUSD', 'AUDUSD'):
                source = indexes[asset]
                allowed = [book for book in source['books'] if book['last'] < DEV_END]
                peers.append(PairedHourlyStore(dict(source, books=allowed), FIRST, DEV_END).bars())
            if any(bar['t'][-1] >= DEV_END for bar in (eur, *peers)):
                raise ValueError('FX_RESIDUAL_HOLDOUT_FENCE')
            schedule = CausalFlatSchedule(gold_calendar(FIRST, DEV_END).events.values())
            rows = scan(eur, *peers, schedule)
            annual = summarize(rows)
            reasons = classify(annual)
            compressed('residual-session-rows', rows)
            save('stage0-results.json', dict(annual=annual, reasons=reasons, stage0_passed=not reasons,
                 registration_sha256=sha(output/'registration.json'), hypotheses=2, executed=1,
                 negatives=['OIL_CAD_SOURCE_BLOCKED'] + (['FX_RESIDUAL_STAGE0_FAIL'] if reasons else [])))
            print(output, [(r['year'], r['raw'], r['mean_net'], r['retention']) for r in annual], reasons, flush=True)
    finally:
        runtime.close()


if __name__ == '__main__':
    main()
