"""Registered EURUSD local-session price component; no position/account simulator."""
import argparse
from datetime import date, datetime, timezone
from decimal import Decimal as D
import json
from pathlib import Path
import time
import traceback
from zoneinfo import ZoneInfo

from forex_study_batch import digest, read, save
from fixing_clock_probe import bind_core, dates, price_return, valid_at

YEARS = (2019, 2022)
VIEWS = {'primary_us_buy':('BUY','us_open','us_close'),
         'eu_sell_context':('SELL','eu_open','us_open'),
         'us_opposite_control':('SELL','us_open','us_close')}


def clocks(day):
    at = date.fromisoformat(day)
    if at.weekday() >= 5:
        raise ValueError('weekday_required')
    midnight = datetime.combine(at,datetime.min.time())
    answer = {name:int(midnight.replace(hour=hour,tzinfo=ZoneInfo(zone)).timestamp())*1000
        for name,zone,hour in (('eu_open','Europe/Dublin',7),
            ('us_open','America/New_York',8),('us_close','America/New_York',16))}
    if not answer['eu_open'] < answer['us_open'] < answer['us_close'] or any(t%3600000 for t in answer.values()):
        raise ValueError('invalid_session_clocks')
    return answer


def endpoint(index, target):
    if target%3600000:
        raise ValueError('whole_hour_target_required')
    hour = index.get(target)
    if hour is None:
        return None
    from trading_workspace_v2.replay_tick_execution import BrokerReplayTick
    q = BrokerReplayTick(time_msc=hour.first_time_msc,sequence=hour.first_sequence,
        bid=hour.bid[0],ask=hour.ask[0])
    if q.bid%D('.00001') or q.ask%D('.00001'):
        raise ValueError('endpoint_off_grid')
    if not target <= q.time_msc < target+3600000:
        raise ValueError('endpoint_outside_cache_hour')
    return q.model_dump(mode='json')


def event(day, quotes):
    bounds = clocks(day)
    result = dict(day=day,clocks=bounds,quotes=quotes,views={})
    for view,(side,start,end) in VIEWS.items():
        entry,exit_at = quotes.get(start),quotes.get(end)
        eligible = valid_at(entry,bounds[start])
        resolved = eligible and valid_at(exit_at,bounds[end])
        if resolved and not (entry['sequence'] < exit_at['sequence'] and entry['time_msc'] < exit_at['time_msc']):
            raise ValueError('endpoint_source_order')
        result['views'][view] = dict(entry_eligible=eligible,
            status='resolved' if resolved else 'missing_or_late_exit' if eligible else 'missing_or_late_entry',
            outcomes={s:price_return(side,entry,exit_at,s) for s in ('reference','stress')} if resolved else {})
    return result


def summarize(events,year):
    if [e['day'] for e in events] != dates(year):
        raise ValueError('weekday_denominator_or_order')
    rows=[]
    for view in VIEWS:
        selected=[e for e in events if e['views'][view]['status']=='resolved']
        eligible=sum(e['views'][view]['entry_eligible'] for e in events)
        for scenario in ('reference','stress'):
            values=[D(e['views'][view]['outcomes'][scenario]['net_pips']) for e in selected]
            positives=sorted((v for v in values if v>0),reverse=True)
            rows.append(dict(year=year,view=view,scenario=scenario,all_dates=len(events),
                entry_eligible=eligible,resolved=len(selected),unresolved=eligible-len(selected),
                unavailable_dates=[dict(day=e['day'],status=e['views'][view]['status']) for e in events
                    if e['views'][view]['status']!='resolved'],
                net_pips_sum=str(sum(values,D(0))) if values else None,
                net_pips_mean=str(sum(values,D(0))/len(values)) if values else None,
                net_pips_min=str(min(values)) if values else None,net_pips_max=str(max(values)) if values else None,
                positive_events=sum(v>0 for v in values),negative_events=sum(v<0 for v in values),
                top3_positive_share=str(sum(positives[:3],D(0))/sum(positives,D(0))) if positives else None,
                half_year_sums={str(half):str(sum((D(e['views'][view]['outcomes'][scenario]['net_pips'])
                    for e in selected if (int(e['day'][5:7])-1)//6+1==half),D(0))) for half in (1,2)}))
    return dict(year=year,all_dates=len(events),rows=rows,
        raw_review_sample_days=[e['day'] for e in events if e['views']['primary_us_buy']['status']=='resolved'][:4])


def retained(years):
    primary=[r for y in years for r in y['rows'] if r['view']=='primary_us_buy' and r['scenario']=='stress']
    if len(primary)!=2 or {r['year'] for r in primary}!=set(YEARS):
        raise ValueError('registered_years_required')
    return all(r['net_pips_sum'] is not None and D(r['net_pips_sum'])>0 and r['resolved']>=200 for r in primary)


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('parent-root','source-root','protocol','fixtures','output'):
        p.add_argument('--'+name,type=Path,required=True)
    args=p.parse_args(argv);args.output.mkdir(exist_ok=False)
    began,cpu=time.perf_counter(),time.process_time()
    def progress(phase,**more):
        if phase not in ('failed','completed_local_session_component'):
            if (args.output/'CANCEL').exists():raise InterruptedError('owner_cancelled')
            if time.perf_counter()-began>180:raise TimeoutError('numeric_deadline180s')
        state=dict(phase=phase,wall_seconds=time.perf_counter()-began,**more)
        save(args.output/'progress.json',state)
        with (args.output/'events.jsonl').open('a',encoding='utf-8') as stream:stream.write(json.dumps(state)+'\n')
        print(state,flush=True)
    try:
        test_path=Path(__file__).parent/'tests/test_local_session_probe.py'
        fixture=read(args.fixtures)
        if (fixture.get('status')!='passed' or fixture.get('tool_sha256')!=digest(Path(__file__))
                or fixture.get('tests_sha256')!=digest(test_path)):
            raise ValueError('fixtures_not_bound')
        bind_core(args.source_root)
        from trading_workspace_v2.forex_coarse_input import load_coarse_hours
        from trading_workspace_v2.forex_study_registration import runtime_binding
        files=[Path(__file__),test_path,args.protocol,args.fixtures,args.parent_root/'config.json']
        files += [Path(__file__).with_name(name) for name in ('forex_study_batch.py','fixing_clock_probe.py','weekend_gap_component.py')]
        files += [args.source_root/'trading_workspace_v2'/name for name in (
            'forex_coarse_input.py','forex_h4.py','replay_tick_execution.py','forex_study_registration.py',
            'retained.py','semantics/data_costs.py','semantics/data_contracts.py')]
        datasets=[]
        for year in YEARS:
            seal_path=args.parent_root/str(year)/'completed.json';seal=read(seal_path)
            result_path=Path(seal['result_path']);parent=read(result_path)
            if (seal['status']!='completed_verified' or digest(result_path)!=seal['result_sha256']
                    or seal['config_sha256']!=digest(args.parent_root/'config.json')
                    or parent['status']!='completed_observed_triage_only' or parent['dataset']!=str(year)
                    or parent['raw']['dates']!=[f'{year}0101',f'{year}1231']
                    or parent['raw']['config_sha256']!=seal['config_sha256']
                    or digest(Path(parent['hourly_cache']['path']))!=parent['hourly_cache']['sha256']):
                raise ValueError('parent_or_cache_binding')
            files += [seal_path,result_path,Path(parent['hourly_cache']['path'])]
            datasets.append(dict(year=year,raw=parent['raw'],cache=parent['hourly_cache']))
        pins={str(path):digest(path) for path in files}
        save(args.output/'manifest.json',dict(pins=pins,datasets=datasets,runtime=runtime_binding(),
            created_at_utc=datetime.now(timezone.utc).isoformat(),scope='exposed_price_component_no_account'))
        for name in pins:
            path=Path(name)
            if path.suffix=='.py':
                relative=path.relative_to(args.source_root) if path.is_relative_to(args.source_root) else Path(path.name)
                destination=args.output/'source-snapshot'/relative
                destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(path.read_bytes())
        years=[]
        for dataset in datasets:
            year,raw=dataset['year'],dataset['raw'];progress('load_verified_observed_cache',year=year)
            hours,proof=load_coarse_hours(Path(raw['path']),cache_dir=Path(dataset['cache']['path']).parent,
                sha256=raw['sha256'],first_day=raw['dates'][0],last_day=raw['dates'][1])
            if proof['sha256']!=dataset['cache']['sha256']:raise ValueError('loaded_cache_drift')
            index={h.mid.timestamp*1000:h for h in hours}
            events=[event(day,{name:endpoint(index,t) for name,t in clocks(day).items()}) for day in dates(year)]
            save(args.output/f'{year}-events.json',events)
            years.append(summarize(events,year));progress('year_completed',year=year,dates=len(events))
        if any(digest(Path(name))!=sha for name,sha in pins.items()):raise ValueError('source_or_input_drift')
        save(args.output/'result.json',dict(status='completed_local_session_component',years=years,
            priority_for_risk_wrapper_review=retained(years),account_backtest=False,clean_oos=False,
            challenge_qualified=False,promotion_authorized=False,simulation_calls=0,broker_calls=0,model_calls=0,
            wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,
            manifest_sha256=digest(args.output/'manifest.json')))
        progress('completed_local_session_component')
    except BaseException as error:
        save(args.output/'failure.json',dict(type=type(error).__name__,message=str(error),traceback=traceback.format_exc()))
        progress('failed');raise


if __name__=='__main__':main()
