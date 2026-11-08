"""Observed SELL excursions to a registered endpoint, not an account backtest."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal as D
import math
from pathlib import Path
import time
import traceback

from forex_study_batch import configure_source_root, digest, read, save
from forex_wrapper_attribution import CANDIDATE, fraction

HOUR = 3600000
YEARS = (2019, 2022)
ATTRIBUTION_SHA = '022207cb47559cb2f7f99f84c166321218e68f7a1f0c343ee01a286d38a7bb8d'
COMPONENT_SHA = '98414710bdf3d73e39033c2b5b12ec8866d7a13d315302d13661022c4243be34'


def excursions(entry_bid, minimum_ask, maximum_ask, quantity):
    bid, low, high, q = map(fraction, (entry_bid, minimum_ask, maximum_ask, quantity))
    if not 0 < low <= high or bid <= 0 or q <= 0 or (q*100).denominator != 1:
        raise ValueError('invalid_price_or_quantity')
    adverse, favorable = max(0, high-bid), max(0, bid-low)
    return dict(mae_pips=str(adverse*10000), mfe_pips=str(favorable*10000),
        worst_reference_loss_usd=str(adverse*q*100000+5*q),
        worst_stress_loss_usd=str(adverse*q*100000+9*q),
        worst_reference_loss_R=str((adverse*q*100000+5*q)/25),
        worst_stress_loss_R=str((adverse*q*100000+9*q)/25))


def observed_path(event, hours, quantity):
    entry, end = event['quotes']['entry'], event['quotes']['exit_1400']
    start, finish = event['clocks']['entry'], event['clocks']['exit_1400']
    if start % HOUR or finish % HOUR or finish <= start:
        raise ValueError('whole_hour_order_required')
    required = list(range(start, finish+HOUR, HOUR))
    missing = [t for t in required if t not in hours]
    if missing:
        return dict(status='unresolved_missing_observed_hour', missing_hours=missing)
    for q, at in ((entry, start), (end, finish)):
        h = hours[at]
        if (not 0 <= q['time_msc']-at <= 60000
                or h.first_time_msc != q['time_msc'] or h.first_sequence != q['sequence']
                or h.bid[0] != D(q['bid']) or h.ask[0] != D(q['ask'])):
            raise ValueError('endpoint_cache_quote_mismatch')
    selected = [hours[t] for t in required]
    if any(b.first_sequence != a.last_sequence+1 for a,b in zip(selected, selected[1:])):
        raise ValueError('observed_sequence_discontinuity')
    # The rest of the endpoint hour is outside the registered trade window.
    low = min([h.ask[2] for h in selected[:-1]]+[D(end['ask'])])
    high = max([h.ask[1] for h in selected[:-1]]+[D(end['ask'])])
    return dict(status='resolved_observed_extrema', minimum_ask=str(low), maximum_ask=str(high),
        entry_time_msc=entry['time_msc'], endpoint_time_msc=end['time_msc'],
        entry_sequence=entry['sequence'], endpoint_sequence=end['sequence'],
        observed_ticks=end['sequence']-entry['sequence']+1, hours=len(selected)-1,
        **excursions(entry['bid'], low, high, quantity))


def distribution(values):
    ordered = sorted(map(fraction, values))
    if not ordered:
        return dict(count=0)
    return dict(count=len(ordered), **{name:str(ordered[max(0, math.ceil(p*len(ordered))-1)])
        for name,p in (('p50',.5),('p90',.9),('p95',.95),('max',1))})


def common_rows(attribution, year):
    books = [r for r in attribution['rows'] if r['year'] == year]
    if len(books) != 2 or {r['scenario'] for r in books} != {'reference','cost-stress'}:
        raise ValueError('cost_books_required')
    reference = next(r for r in books if r['scenario'] == 'reference')
    stress = next(r for r in books if r['scenario'] == 'cost-stress')
    fields = ('day','quantity','entry_time_msc','entry_fill','endpoint_time_msc')
    a, b = [[tuple(r[k] for k in fields) for r in book['matched']] for book in (reference,stress)]
    if a != b or len({r['day'] for r in reference['matched']}) != len(a):
        raise ValueError('cost_common_mask_mismatch')
    return reference['matched'], reference['excluded']


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('root','source-root','protocol','fixtures','output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args(argv)
    args.output.mkdir(exist_ok=False)
    began, cpu = time.perf_counter(), time.process_time()
    def progress(phase, **more):
        if phase not in ('failed','completed_observed_path_diagnostic'):
            if (args.output/'CANCEL').exists(): raise InterruptedError('owner_cancelled')
            if time.perf_counter()-began > 180: raise TimeoutError('path_deadline')
        state = dict(phase=phase, wall_seconds=time.perf_counter()-began, **more)
        save(args.output/'progress.json',state)
        import json
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(state)+'\n')
        print(state,flush=True)
    try:
        fixture = read(args.fixtures)
        test_path = Path(__file__).parent/'tests/test_pre_ecb_path_risk.py'
        if (fixture.get('status') != 'passed' or fixture.get('tool_sha256') != digest(Path(__file__))
                or fixture.get('tests_sha256') != digest(test_path)):
            raise ValueError('fixtures_not_bound')
        configure_source_root(args.source_root)
        from trading_workspace_v2.forex_coarse_input import load_coarse_hours
        attribution_dir = args.root/'pre-ecb-wrapper-attribution-v1'
        attribution_path = attribution_dir/'result.json'
        attribution = read(attribution_path)
        if (digest(attribution_path) != ATTRIBUTION_SHA
                or attribution['status'] != 'completed_matched_attribution'
                or digest(attribution_dir/'manifest.json') != attribution['manifest_sha256']):
            raise ValueError('attribution_binding')
        paths = [Path(__file__), Path(__file__).with_name('forex_wrapper_attribution.py'),
            Path(__file__).with_name('forex_study_batch.py'), args.protocol, args.fixtures,
            attribution_path, attribution_dir/'manifest.json', test_path]
        component = args.root/'fixing-clock-transfer-v1'
        for name in ('result.json','manifest.json','review-result.json','linkage-review.json'):
            paths.append(component/name)
        component_sha = digest(component/'result.json')
        if component_sha != COMPONENT_SHA: raise ValueError('unexpected_component_version')
        for year in YEARS:
            paths.append(component/f'{year}-events.json')
        for name in ('review-result.json','linkage-review.json'):
            if read(component/name)['numerical_result_sha256'] != component_sha:
                raise ValueError('component_review_binding')
        # Reuse sealed inputs; source changes must be handled by loader, not by editing old pins.
        for manifest in (read(attribution_dir/'manifest.json'), read(component/'linkage-review.json')):
            for name, sha in manifest['pins'].items():
                if digest(Path(name)) != sha: raise ValueError('upstream_input_drift')
        pins = {str(path):digest(path) for path in paths}
        datasets = []
        for year in YEARS:
            seal_path = args.root/'eurusd-observed-history-v2'/str(year)/'completed.json'
            seal = read(seal_path); parent_path = Path(seal['result_path'])
            if digest(parent_path) != seal['result_sha256']: raise ValueError('parent_result_seal')
            parent = read(parent_path)
            raw, cache = parent['raw'], parent['hourly_cache']
            if digest(Path(cache['path'])) != cache['sha256']: raise ValueError('cache_seal')
            for path in (seal_path,parent_path,Path(cache['path'])):
                pins[str(path)] = digest(path)
            datasets.append(dict(year=year, raw=raw, cache=cache))
        for name in ('forex_coarse_input.py','forex_h4.py','replay_tick_execution.py','forex_study_registration.py'):
            path = args.source_root/'trading_workspace_v2'/name
            pins[str(path)] = digest(path)
        save(args.output/'manifest.json',dict(pins=pins,datasets=datasets,
            created_at_utc=datetime.now(timezone.utc).isoformat(),scope='observed_counterfactual_paths_only'))
        for name in pins:
            path = Path(name)
            if path.suffix == '.py':
                destination = args.output/'source-snapshot'/path.name
                destination.parent.mkdir(exist_ok=True)
                destination.write_bytes(path.read_bytes())
        results = []
        for dataset in datasets:
            year, raw = dataset['year'], dataset['raw']
            progress('load_verified_observed_cache',year=year)
            hours, proof = load_coarse_hours(Path(raw['path']), cache_dir=Path(dataset['cache']['path']).parent,
                sha256=raw['sha256'],first_day=raw['dates'][0],last_day=raw['dates'][1])
            if proof['sha256'] != dataset['cache']['sha256']: raise ValueError('loaded_cache_drift')
            index = {h.mid.timestamp*1000:h for h in hours}
            events_path = component/f'{year}-events.json'
            if str(events_path) not in read(component/'linkage-review.json')['pins']:
                raise ValueError('events_not_source_bound')
            events = {e['day']:e for e in read(events_path)}
            matched, excluded = common_rows(attribution,year)
            rows = []
            for r in matched:
                e = events[r['day']]
                if (e['views']['baseline_1400']['status'] != 'resolved'
                        or r['entry_time_msc'] != e['quotes']['entry']['time_msc']
                        or fraction(r['entry_fill']) != fraction(e['quotes']['entry']['bid'])
                        or r['endpoint_time_msc'] != e['quotes']['exit_1400']['time_msc']):
                    raise ValueError('matched_event_binding')
                rows.append(dict(day=r['day'],quantity=r['quantity'],entry_bid=e['quotes']['entry']['bid'],
                    endpoint_reference_net_unit_usd=e['views']['baseline_1400']['outcomes']['reference']['net_usd_per_standard_lot'],
                    **observed_path(e,index,r['quantity'])))
            resolved = [r for r in rows if r['status'] == 'resolved_observed_extrema']
            metrics = ('mae_pips','mfe_pips','worst_reference_loss_usd','worst_stress_loss_usd',
                       'worst_reference_loss_R','worst_stress_loss_R')
            results.append(dict(year=year,matched_dates=len(rows),resolved=len(resolved),excluded=excluded,
                unresolved=[r for r in rows if r not in resolved],rows=rows,
                distributions={k:distribution(r[k] for r in resolved) for k in metrics},
                reference_positive_endpoint_mae=distribution(r['mae_pips'] for r in resolved
                    if fraction(r['endpoint_reference_net_unit_usd']) > 0),
                worst_reference_above_25usd=sum(fraction(r['worst_reference_loss_usd'])>25 for r in resolved),
                worst_stress_above_25usd=sum(fraction(r['worst_stress_loss_usd'])>25 for r in resolved),
                raw_review_sample_days=[r['day'] for r in sorted(resolved,key=lambda r:r['entry_time_msc'])[:4]]))
            progress('year_completed',year=year,resolved=len(resolved))
        if any(digest(Path(name)) != sha for name,sha in pins.items()): raise ValueError('source_or_input_drift')
        save(args.output/'result.json',dict(status='completed_observed_path_diagnostic',years=results,
            manifest_sha256=digest(args.output/'manifest.json'), wall_seconds=time.perf_counter()-began,
            cpu_seconds=time.process_time()-cpu,simulation_calls=0,broker_calls=0,model_calls=0,
            account_backtest=False,clean_oos=False,challenge_qualified=False,promotion_authorized=False))
        progress('completed_observed_path_diagnostic',years=len(results))
    except BaseException as error:
        save(args.output/'failure.json',dict(error_type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        progress('failed')
        raise


if __name__ == '__main__': main()
