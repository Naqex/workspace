"""Registered endpoint/fee diagnostic, not a position simulator or strategy."""
import argparse
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys
import time
import traceback
from zoneinfo import ZoneInfo

from forex_study_batch import configure_source_root, digest, read, save
from weekend_gap_component import quote

YEARS = (2019, 2022)
SLIPPAGE = {'reference': D(0), 'stress': D('.00002')}
VIEWS = {'primary_1415': ('SELL', 'exit_1415'), 'baseline_1400': ('SELL', 'exit_1400'),
         'opposite_control': ('BUY', 'exit_1415')}


def bind_core(path):
    configure_source_root(path)
    global CostModel, calculate_round_trip_cost
    from trading_workspace_v2.retained import CostModel, calculate_round_trip_cost


def clocks(day):
    at = date.fromisoformat(day)
    if at.weekday() >= 5:
        raise ValueError('weekday_required')
    local = datetime.combine(at, datetime.min.time())
    times = dict(entry=local.replace(hour=2, tzinfo=ZoneInfo('America/New_York')),
                 exit_1400=local.replace(hour=14, tzinfo=ZoneInfo('Europe/Berlin')),
                 exit_1415=local.replace(hour=14, minute=15, tzinfo=ZoneInfo('Europe/Berlin')))
    result = {key: int(value.timestamp())*1000 for key, value in times.items()}
    if not result['entry'] < result['exit_1400'] < result['exit_1415']:
        raise ValueError('clock_order')
    return result


def dates(year):
    current, end = date(year, 1, 1), date(year+1, 1, 1)
    result = []
    while current < end:
        if current.weekday() < 5:
            result.append(current.isoformat())
        current += timedelta(days=1)
    return result


def valid_at(q, target):
    return q is not None and 0 <= q['time_msc']-target <= 60000


def price_return(side, entry, exit_at, scenario):
    model = CostModel.from_mapping(dict(version='fixing-clock-component-'+scenario,
        spread_basis='bid_ask_embedded', commission_per_side_account='0',
        commission_per_side_per_quantity_account='2.5', minimum_fee_account='0',
        slippage_price_per_side=str(SLIPPAGE[scenario]), financing_account='0',
        quote_to_account_rate='1', account_ccy='USD', rounding_decimals=2))
    costs = calculate_round_trip_cost(model, side, D(1), D(100000),
        D(entry['bid']), D(entry['ask']), D(exit_at['bid']), D(exit_at['ask']))
    return dict(net_usd_per_standard_lot=str(costs['net_account']),
                net_pips=str(D(str(costs['net_account']))/10), costs=costs)


def event(day, quotes):
    bounds = clocks(day)
    entry = quotes.get('entry')
    eligible = valid_at(entry, bounds['entry'])
    result = dict(day=day, clocks=bounds, quotes=quotes, entry_eligible=eligible,
                  views={}, paired_delta_pips={})
    for view, (side, exit_key) in VIEWS.items():
        exit_at = quotes.get(exit_key)
        resolved = eligible and valid_at(exit_at, bounds[exit_key])
        if resolved and not (entry['sequence'] < exit_at['sequence'] and entry['time_msc'] < exit_at['time_msc']):
            raise ValueError('source_quote_order')
        result['views'][view] = dict(status='resolved' if resolved else
            'missing_or_late_exit' if eligible else 'missing_or_late_entry', outcomes={
                scenario: price_return(side, entry, exit_at, scenario) for scenario in SLIPPAGE} if resolved else {})
    a, b = result['views']['primary_1415'], result['views']['baseline_1400']
    if a['status'] == b['status'] == 'resolved':
        result['paired_delta_pips'] = {s: str(D(a['outcomes'][s]['net_pips'])-D(b['outcomes'][s]['net_pips']))
                                       for s in SLIPPAGE}
    return result


def scan_targets(path, days, expected_sha, expected_count, progress):
    selected = {day: {} for day in days}
    targets = sorted((datetime.fromtimestamp(ms/1000, timezone.utc).strftime('%Y%m%d %H:%M:%S.000').encode(),
                      ms, day, name) for day in days for name, ms in clocks(day).items())
    cursor, count = 0, 0
    previous_stamp = previous_line = None
    proofs, late = [], []
    h = hashlib.sha256()
    with Path(path).open('rb') as stream:
        header = stream.readline(); h.update(header)
        if header.decode('utf-8-sig').strip() != 'DateTime,Bid,Ask,Volume':
            raise ValueError('raw_header')
        for line in stream:
            h.update(line)
            if not line.strip():
                continue
            count += 1
            stamp = line[:21]
            if len(stamp) != 21 or (previous_stamp is not None and stamp < previous_stamp):
                raise ValueError('raw_order')
            decoded = None
            while cursor < len(targets) and stamp >= targets[cursor][0]:
                _, target, day, name = targets[cursor]
                if decoded is None:
                    decoded = quote(line, count)
                predecessor = quote(previous_line, count-1) if previous_line is not None else None
                if predecessor is not None and predecessor['time_msc'] >= target:
                    raise ValueError('not_first_after_target')
                proofs.append(dict(day=day, event=name, target=target, first_later=decoded, predecessor=predecessor))
                if valid_at(decoded, target):
                    selected[day][name] = decoded
                else:
                    late.append(dict(day=day, event=name, first_later_time_msc=decoded['time_msc']))
                cursor += 1
            previous_stamp, previous_line = stamp, line
            if count % 1000000 == 0:
                progress(count)
    if h.hexdigest() != expected_sha or count != expected_count:
        raise ValueError('raw_hash_or_count')
    missing = [dict(day=day, event=name, target=target) for _, target, day, name in targets[cursor:]]
    return selected, dict(quote_proofs=proofs, late=late, missing_after_eof=missing,
                          raw_sha256=h.hexdigest(), raw_ticks=count)


def summarize(events, year):
    rows = []
    eligible = sum(e['entry_eligible'] for e in events)
    for view in VIEWS:
        resolved = [e for e in events if e['views'][view]['status'] == 'resolved']
        for scenario in SLIPPAGE:
            values = [D(e['views'][view]['outcomes'][scenario]['net_pips']) for e in resolved]
            positive = sum((x for x in values if x > 0), D(0))
            rows.append(dict(year=year, view=view, scenario=scenario, all_dates=len(events),
                entry_eligible=eligible, resolved=len(resolved), unresolved=eligible-len(resolved),
                net_pips_sum=str(sum(values, D(0))) if values else None,
                net_pips_mean=str(sum(values, D(0))/len(values)) if values else None,
                net_pips_min=str(min(values)) if values else None, net_pips_max=str(max(values)) if values else None,
                positive_events=sum(x > 0 for x in values), negative_events=sum(x < 0 for x in values),
                top3_positive_share=str(sum(sorted([x for x in values if x > 0], reverse=True)[:3], D(0))/positive) if positive else None))
    paired = [e for e in events if e['paired_delta_pips']]
    delta = {s: dict(events=len(paired), sum_pips=str(sum((D(e['paired_delta_pips'][s]) for e in paired), D(0)))
                    if paired else None,
                    mean_pips=str(sum((D(e['paired_delta_pips'][s]) for e in paired), D(0))/len(paired))
                    if paired else None) for s in SLIPPAGE}
    return dict(year=year, all_dates=len(events), entry_eligible=eligible, rows=rows, paired=delta,
                challenge_qualified=False, promotion_authorized=False)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'parent-root', 'protocol', 'fixtures', 'output'):
        parser.add_argument('--'+name, required=True, type=Path)
    args = parser.parse_args(argv)
    bind_core(args.source_root)
    args.output.mkdir(exist_ok=False)
    began = time.perf_counter()
    cpu = time.process_time()
    def progress(phase, **more):
        if phase not in ('failed', 'completed_exposed_component'):
            if (args.output/'CANCEL').exists(): raise InterruptedError('owner_cancelled')
            if time.perf_counter()-began > 300: raise TimeoutError('component_deadline300s')
        packet = dict(phase=phase, wall_seconds=time.perf_counter()-began,
                      cpu_seconds=time.process_time()-cpu, **more)
        save(args.output/'progress.json', packet)
        with (args.output/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(packet)+'\n')
        if phase != 'raw_scan': print(json.dumps(packet), flush=True)
    try:
        fixtures = read(args.fixtures)
        if fixtures.get('status') != 'passed' or fixtures.get('tool_sha256') != digest(Path(__file__)):
            raise ValueError('fixtures_not_bound')
        pins = {str(p): digest(p) for p in (Path(__file__), Path(__file__).with_name('forex_study_batch.py'),
                Path(__file__).with_name('weekend_gap_component.py'), args.protocol, args.fixtures, args.parent_root/'config.json')}
        for name in ('trading_workspace_v2/retained.py', 'trading_workspace_v2/forex_study_registration.py',
                     'trading_workspace_v2/semantics/data_costs.py',
                     'trading_workspace_v2/semantics/data_contracts.py', 'trading_workspace_v2/replay_tick_execution.py'):
            path = args.source_root/name; pins[str(path)] = digest(path)
        datasets = []
        for year in YEARS:
            seal_path = args.parent_root/str(year)/'completed.json'
            seal = read(seal_path); path = Path(seal['result_path']); source = read(path)
            if (seal['status'] != 'completed_verified' or seal['result_sha256'] != digest(path)
                    or seal['config_sha256'] != digest(args.parent_root/'config.json')
                    or source['dataset'] != str(year) or source['status'] != 'completed_observed_triage_only'
                    or source['raw']['dates'] != [f'{year}0101', f'{year}1231']
                    or source['raw']['config_sha256'] != seal['config_sha256']):
                raise ValueError('parent_binding_or_scope')
            pins[str(seal_path)], pins[str(path)] = digest(seal_path), digest(path)
            datasets.append(dict(year=year, raw=source['raw'], expected_ticks=source['hourly_cache']['ticks']))
        from trading_workspace_v2.forex_study_registration import runtime_binding
        save(args.output/'manifest.json', dict(pins=pins, datasets=datasets, runtime=runtime_binding(), pid=__import__('os').getpid(),
            created_at_utc=datetime.now(timezone.utc).isoformat(), protocol=str(args.protocol),
            scope='exposed_endpoint_component_no_account_simulation'))
        for name in pins:
            source = Path(name)
            relative = (str(source.relative_to(args.source_root)) if source.is_relative_to(args.source_root)
                        else source.name)
            target = args.output/'source-snapshot'/relative
            # Parent result/seal files share basenames; their bytes stay at pinned originals.
            if source == Path(__file__) or source.suffix == '.py':
                target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(source.read_bytes())
        years = []
        for dataset in datasets:
            year = dataset['year']; progress('collect_endpoints', year=year)
            days = dates(year)
            chosen, proof = scan_targets(dataset['raw']['path'], days, dataset['raw']['sha256'],
                dataset['expected_ticks'], lambda count: progress('raw_scan', year=year, ticks=count))
            events = [event(day, chosen[day]) for day in days]
            summary = summarize(events, year)
            save(args.output/f'{year}-events.json', events)
            save(args.output/f'{year}-source-proof.json', proof)
            years.append(summary)
            progress('year_completed', year=year, dates=len(days))
        if sum(y['all_dates'] for y in years) != 521 or any(digest(Path(p)) != sha for p, sha in pins.items()):
            raise ValueError('final_scope_or_source_drift')
        primary = [r for y in years for r in y['rows'] if r['view'] == 'primary_1415']
        incomplete = any(r['unresolved'] or not r['entry_eligible'] for y in years for r in y['rows']
                         if r['view'] != 'opposite_control')
        priority = (all(r['net_pips_sum'] is not None and D(r['net_pips_sum']) > 0 and r['unresolved'] == 0 for r in primary)
                    and not incomplete
                    and all(y['paired']['stress']['sum_pips'] is not None and D(y['paired']['stress']['sum_pips']) > 0 for y in years))
        save(args.output/'result.json', dict(status='completed_exposed_component', years=years,
            priority_for_wrapper_review=priority, promotion_authorized=False, challenge_qualified=False,
            selection_status='inconclusive_quote_coverage' if incomplete else
                'eligible_for_wrapper_review' if priority else 'no_priority_under_registered_heuristic',
            broker_calls=0, model_calls=0, clean_oos=False, simulation_calls=0,
            wall_seconds=time.perf_counter()-began, cpu_seconds=time.process_time()-cpu,
            manifest_sha256=digest(args.output/'manifest.json')))
        progress('completed_exposed_component')
    except BaseException as error:
        save(args.output/'failure.json', dict(error_type=type(error).__name__, message=str(error),
            traceback=traceback.format_exc(), wall_seconds=time.perf_counter()-began))
        progress('failed')
        raise


if __name__ == '__main__':
    main()
