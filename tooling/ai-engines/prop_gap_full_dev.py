"""Expand the frozen cross-feed sensitivity to every ranked Development gap."""
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from statistics import median
import subprocess

from prop_gap_source_sensitivity import EST, MINUTE, N1, assess, fetch, observed_ticks
from prop_replay_regression import BASE as REPLAY, WORKSPACE, net, verify_commit
from prop_v15_accounts import exact_quantity
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, save, unpack
from prop_v26_common import DEV_END, FIRST, ROOT, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import DAY
import prop_v21_common as evidence

PROTOCOL = WORKSPACE / 'planning/research/PROP-GAP-FULL-DEV-PROTOCOL-20261118.md'
BASE = ROOT / 'prop-gap-full-dev-20261118'
SCALE = {'EURUSD': 100000, 'XAUUSD': 1000}
PIP = {'EURUSD': 10000, 'XAUUSD': 1}  # XAU output is USD/oz, not pips.


def month_at(when):
    return datetime.fromtimestamp(when / 1000, EST).strftime('%Y%m')


def archived_months():
    receipt = next(REPLAY.glob('histdata-gaps/*/tick-sensitivity-manifest.json'))
    with bindings(evidence, JOB=receipt.parent):
        source = unpack('tick-sensitivity')
    return {('EURUSD', row['month']): (receipt.parent / f"HistData-EURUSD-{row['month']}.zip", row['sha256'])
            for row in source['results']}


def get_source(key, folder, cached):
    if key in cached:
        path, expected = cached[key]
        if sha(path) != expected:
            raise ValueError('HISTDATA_CACHED_SOURCE_HASH')
        return path, expected, True
    asset, month = key
    path, _ = fetch(month, folder, asset)
    return path, sha(path), False


def compare_month(key, gaps, path, base, strict, stops, bars):
    asset, month = key
    minute_ids = {at for g in gaps for at in range(g['before'], g['after'] + MINUTE, MINUTE)}
    grouped = defaultdict(list)
    for g in gaps:
        for row in g['trades']:
            grouped[asset, row['entry']].append(g)
    for index in grouped:
        t = base[index]
        first, end = t['entry_msc'], t['deadline_msc']
        if t['mode'] == 'P0' and month_at(first) == month_at(end + MINUTE) == month:
            minute_ids.update(range(first // MINUTE * MINUTE, end + 2 * MINUTE, MINUTE))
    ticks = observed_ticks(path, month, min(minute_ids), max(minute_ids) + MINUTE,
                           wanted_minutes=minute_ids, asset=asset)
    minutes = defaultdict(list)
    for tick in ticks:
        minutes[tick[0] // MINUTE * MINUTE].append(tick)
    path_results, gap_results, differences = [], [], {}
    for g in gaps:
        inside = [tick for at in range(g['first_unknown'], g['after'], MINUTE) for tick in minutes[at]]
        matches = []
        for row in g['trades']:
            t = base[asset, row['entry']]
            level = stops[(asset, g['before'], g['after'], t['id'], row['entry'])]
            value = Decimal(level['level']) / SCALE[asset]
            crosses = sum(tick[1] <= value if t['side'] == 'BUY' else tick[2] >= value for tick in inside)
            matches.append(dict(entry=row['entry'], id=t['id'], stop=str(value),
                                protection_active=level['protected'], crossings=crosses))
        gap_results.append(dict(asset=asset, first_unknown=g['first_unknown'], after=g['after'],
                                count=len(inside), before_count=len(minutes[g['before']]),
                                after_count=len(minutes[g['after']]), matches=matches))
        for at in (g['before'], g['after']):
            i = int(bars['t'].searchsorted(at))
            if not minutes[at] or i == len(bars) or bars['t'][i] != at:
                continue
            differences[at] = [float(abs(Decimal(int(bars[field][i])) / SCALE[asset] - row[1]) * PIP[asset])
                               for field, row in (('bo', minutes[at][0]), ('bc', minutes[at][-1]))]
    for index, relevant in grouped.items():
        t = base[index]
        entry, deadline = t['entry_msc'], t['deadline_msc']
        label = dict(asset=asset, id=t['id'], entry=entry)
        if t['mode'] != 'P0':
            path_results.append(dict(label, status='P1_GAP_ONLY', net_cents=None))
        elif (month_at(entry) != month or month_at(deadline + MINUTE) != month
              or deadline // DAY != entry // DAY or deadline % DAY >= 21 * 60 * MINUTE):
            path_results.append(dict(label, status='SOURCE_SPAN_OR_FUNDING_OUTSIDE_SCOPE', net_cents=None))
        else:
            path_results.append(dict(assess(t, ticks, relevant, strict[index]), **label))
    return dict(gaps=gap_results, paths=path_results, diffs=differences, ticks=len(ticks))


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    verify_commit(WORKSPACE / 'tooling/ai-engines/prop_gap_source_sensitivity.py')
    rank = next(N1.glob('gaps/*/gap-ranking-manifest.json'))
    with bindings(evidence, JOB=rank.parent):
        ranked = unpack('gap-ranking')['gaps']
    groups = defaultdict(list)
    for gap in ranked:
        if not FIRST <= gap['before'] < gap['after'] < DEV_END:
            raise ValueError('HISTDATA_RANGE_OUTSIDE_DEVELOPMENT')
        groups[gap['asset'], month_at(gap['first_unknown'])].append(gap)
    if len(ranked) != 43 or len(groups) != 19:
        raise ValueError('HISTDATA_RANGE_CHANGED')
    primary_path, strict_path, stop_path = [V19 / name for name in (
        'Dev-OLHC-PRIMARY-trades.json', 'Dev-OLHC-STRICT-trades.json', 'gap-identities.json')]
    base, strict = ({(t['asset'], t['entry_msc']): t for t in read(p)} for p in (primary_path, strict_path))
    stops = {(r['asset'], r['before'], r['after'], r['id'], r['entry']): r for r in read(stop_path)['rows']
             if FIRST <= r['first_unknown'] < DEV_END}
    cached = archived_months()
    bars = {asset: bars_for(asset, True) for asset in SCALE}
    runtime = JobWorkspace(BASE, WORKSPACE)
    output = runtime.activate()
    try:
        with bindings(evidence, JOB=output):
            save('registration.json', dict(inputs={p.name: sha(p) for p in (rank, primary_path, strict_path, stop_path, PROTOCOL, Path(__file__))},
                head=subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
                first=FIRST, end_exclusive=DEV_END, scope=[list(k) for k in sorted(groups)]))
        attempts, path_results, gaps = [], {}, []
        differences = defaultdict(dict)
        def job(key):
            try:
                path, digest, reused = get_source(key, output, cached)
                observation = compare_month(key, groups[key], path, base, strict, stops, bars[key[0]])
                return dict(asset=key[0], month=key[1], status='OBSERVED', bytes=path.stat().st_size,
                            sha256=digest, reused=reused), observation
            except (subprocess.SubprocessError, OSError, KeyError, ValueError) as error:
                return dict(asset=key[0], month=key[1], status='SOURCE_UNAVAILABLE',
                            error=type(error).__name__, detail=str(error)[:160]), None
        with ThreadPoolExecutor(max_workers=3) as pool:
            for attempt, observation in pool.map(job, sorted(groups)):
                attempts.append(attempt)
                print(attempt['asset'], attempt['month'], attempt['status'], flush=True)
                if observation is None:
                    continue
                gaps.extend(observation['gaps'])
                differences[attempt['asset']].update(observation['diffs'])
                for r in observation['paths']:
                    key = (r['asset'], r['entry'])
                    if key not in path_results or r['net_cents'] is not None:
                        path_results[key] = r
        actual = {key: r['net_cents'] for key, r in path_results.items() if r['net_cents'] is not None}
        fiscal = {}
        for name, book in (('PRIMARY', base), ('STRICT', strict)):
            starting = {key: net(row, exact_quantity(base[key], 150)) for key, row in book.items()}
            value = sum(starting.values())
            delta = sum(amount - starting[key] for key, amount in actual.items())
            fiscal[name] = dict(original_cents=value, delta_cents=delta, alternate_cash_sum_cents=value+delta)
        parity = {}
        for asset, by_minute in differences.items():
            flat = [v for pair in by_minute.values() for v in pair]
            parity[asset] = dict(minutes=len(by_minute), exact=sum(v == 0 for v in flat),
                                 median_abs=median(flat), max_abs=max(flat))
        with bindings(evidence, JOB=output):
            compressed('full-sensitivity', dict(attempts=attempts, gaps=gaps, paths=list(path_results.values()),
                       paired_bid_parity=parity, replaced_p0=len(actual), cash_sensitivity=fiscal,
                       registration=sha(output / 'registration.json')))
        print(dict(gaps=len(gaps), with_ticks=sum(g['count'] > 0 for g in gaps), matched=len(actual)), flush=True)
    finally:
        runtime.close()


if __name__ == '__main__':
    main()
