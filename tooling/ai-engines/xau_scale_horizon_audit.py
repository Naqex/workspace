"""Development-only, frozen-cohort path diagnostics; never a B1/account replay."""
from bisect import bisect_left
from collections import Counter,defaultdict
from datetime import datetime,timezone
from decimal import Decimal as D,ROUND_HALF_UP
import json
from pathlib import Path
import random
from statistics import mean,median
import struct
import sys
import time

from eurusd_b0_source import digest,write_json
from index_tick_review import decode

HOUR=3_600_000
DAY=24*HOUR
START=1_640_995_200_000
END=1_704_067_200_000
RECORD=struct.Struct('<qii')


def describe(values):
    values=sorted(values)
    if not values:return dict(n=0,mean=None,median=None,p10=None,p90=None,min=None,max=None)
    return dict(n=len(values),mean=mean(values),median=median(values),
        p10=values[int(.1*(len(values)-1))],p90=values[int(.9*(len(values)-1))],min=values[0],max=values[-1])


def money(value):
    return int(value.quantize(D('.01'),rounding=ROUND_HALF_UP)*100)


def first_passage(quotes,entry_index,entry_units,side,distance_units,cutoff):
    """Two competing price barriers; preserve censoring and unknown observed paths."""
    sign=1 if side=='BUY' else -1
    start=quotes[entry_index][0];previous=start;maxgap=0
    if cutoff<start or distance_units<=0:raise ValueError('invalid_passage_geometry')
    for index in range(entry_index,len(quotes)):
        at,bid,ask=quotes[index]
        if at>cutoff+60_000:break
        maxgap=max(maxgap,at-previous);previous=at
        liquid=bid if sign==1 else ask
        move=sign*(liquid-entry_units)
        hit='SL' if move<=-distance_units else 'TP_2R' if move>=2*distance_units else None
        if hit is not None or at>=cutoff:
            price=entry_units+sign*2*distance_units if hit=='TP_2R' else liquid
            return dict(status=hit or 'RIGHT_CENSORED',at=at,index=index,price_units=price,
                observed_hours=(at-start)/HOUR,cutoff_hours=(cutoff-start)/HOUR,
                path_incomplete=maxgap>60_000,max_quote_gap_ms=maxgap)
    return dict(status='MISSING_CUTOFF_QUOTE',at=None,index=None,price_units=None,
        observed_hours=None,cutoff_hours=(cutoff-start)/HOUR,path_incomplete=True,max_quote_gap_ms=maxgap)


def markout(quotes,times,entry_index,side,cutoff):
    entry=quotes[entry_index];index=bisect_left(times,cutoff)
    if index==len(quotes) or times[index]-cutoff>60_000:return None
    quote=quotes[index];sign=1 if side=='BUY' else -1
    p0=entry[2] if sign==1 else entry[1];p1=quote[1] if sign==1 else quote[2]
    gross=sign*(p1-p0)/1000
    commission=(p0+p1)/1000*.000007
    return dict(at=quote[0],gross_usd_per_oz=gross,commission_usd_per_oz=commission,
        reference_net_usd_per_oz=gross-commission,stress_net_usd_per_oz=gross-commission-.4)


def friction_record(trade):
    ounces=trade['lot_steps']
    entry_spread=(trade['entry_ask_units']-trade['entry_bid_units'])/1000
    exit_spread=(trade['exit_ask_units']-trade['exit_bid_units'])/1000
    spread=(entry_spread+exit_spread)/2
    commission=trade['results']['reference']['commission_usd']/ounces
    sign=1 if trade['side']=='BUY' else -1
    liquid=trade['exit_bid_units'] if sign==1 else trade['exit_ask_units']
    clipping=sign*(liquid-trade['exit_units'])/1000
    # Decimal oracle: actual Bid/Ask PnL == signed mid move minus two half-spreads
    # and the explicitly conservative TP limit fill, rounded once to cents.
    midmove=D(sign*(trade['exit_bid_units']+trade['exit_ask_units']-trade['entry_bid_units']-trade['entry_ask_units']))/2000
    spread_d=D(trade['entry_ask_units']-trade['entry_bid_units']+trade['exit_ask_units']-trade['exit_bid_units'])/2000
    clip_d=D(sign*(liquid-trade['exit_units']))/1000
    assert money((midmove-spread_d-clip_d)*ounces)==round(trade['results']['reference']['gross_after_spread_usd']*100)
    return dict(day=trade['day'],year=int(trade['day'][:4]),ounces=ounces,
        entry_spread_usd_per_oz=entry_spread,exit_spread_usd_per_oz=exit_spread,
        roundtrip_mid_spread_usd_per_oz=spread,commission_usd_per_oz=commission,
        reference_friction_usd_per_oz=spread+commission,
        stress_friction_usd_per_oz=spread+commission+.4,
        stress_slippage_share=.4/(spread+commission+.4),
        tp_no_improvement_usd_per_oz=clipping)


def stop_record(intent):
    side=intent['side'];sign=1 if side=='BUY' else -1
    _,high,low,close=intent['bar_units'];atr=D(intent['atr_units'])
    extreme=low if side=='BUY' else high
    before=sign*(D(close)-D(extreme))/1000
    drift=sign*(D(intent['entry_units'])-D(close))/1000
    buffer=atr/10000
    rounded=sign*(D(extreme)-D(intent['stop_units']))/1000-buffer
    distance=sign*(D(intent['entry_units'])-D(intent['stop_units']))/1000
    assert distance==before+drift+buffer+rounded
    assert 0<=rounded<D('.001')
    spread=(intent['entry_ask_units']-intent['entry_bid_units'])/1000
    bound=max(intent['entry_units'],intent['stop_units'],intent.get('take_units',intent['entry_units']))/1000
    fee=2*bound*.000007+.4
    return dict(day=intent['day'],year=int(intent['day'][:4]),status=intent['status'],
        sl_usd_per_oz=float(distance),close_to_bar_extreme_usd_per_oz=float(before),
        entry_drift_usd_per_oz=float(drift),atr_buffer_usd_per_oz=float(buffer),
        outward_rounding_usd_per_oz=float(rounded),atr_m15_usd_per_oz=float(atr/1000),
        bar_range_usd_per_oz=(high-low)/1000,bar_range_to_atr=float(D(high-low)/atr),
        sl_to_atr=float(distance/(atr/1000)),entry_spread_usd_per_oz=spread,
        continuous_cost_floor_usd_per_oz=(spread+.88*fee)/.12)


def bootstrapped_day_ci(records,key,seed=20261113,repetitions=2000):
    groups=defaultdict(list)
    for row in records:groups[row['day']].append(row[key])
    if len(groups)<2:return None
    units=[(sum(v),len(v)) for v in groups.values()];rng=random.Random(seed);sample=[]
    for _ in range(repetitions):
        selected=[units[rng.randrange(len(units))] for _ in units]
        sample.append(sum(a for a,n in selected)/sum(n for a,n in selected))
    sample.sort()
    return dict(lower=sample[int(.025*repetitions)],upper=sample[int(.975*repetitions)],
        day_clusters=len(units),repetitions=repetitions,seed=seed,
        scope='conditional_within_day_dependence_only_not_trial_adjusted_or_future_edge_proof')


def summarize_passage(records):
    complete=[r for r in records if not r['path_incomplete']]
    events=[r for r in complete if r['status'] in ('SL','TP_2R')]
    observed=describe([r['observed_hours'] for r in events])
    # Observed medians excluding right-censored rows are conditional, not the
    # cohort median or a Kaplan-Meier estimate with untested censoring assumptions.
    lower=[r['observed_hours'] if not r['path_incomplete'] and r['status'] in ('SL','TP_2R')
           else r['cutoff_hours'] if not r['path_incomplete'] else 0 for r in records]
    upper=[r['observed_hours'] if not r['path_incomplete'] and r['status'] in ('SL','TP_2R') else float('inf') for r in records]
    lo=median(lower) if lower else None;hi=median(upper) if upper else None
    identified=bool(records) and lo==hi
    return dict(n=len(records),counts=dict(Counter(r['status'] for r in records)),
        complete_paths=len(complete),path_unknown=len(records)-len(complete),
        event_times_hours_conditional_on_observed_boundary=observed,
        median_all_cohort_hours=lo if identified else None,
        median_all_cohort_bounds=dict(lower=lo,upper=hi if hi is not None and hi!=float('inf') else None),
        median_all_cohort_reason='identified_by_observed_time_intervals' if identified else 'not_point_identified_with_censoring_no_KM_assumption',
        terminal_gross_usd_per_oz=describe([r['terminal_gross_usd_per_oz'] for r in complete]),
        terminal_stress_net_usd_per_oz=describe([r['terminal_stress_net_usd_per_oz'] for r in complete]))


def execute(config_path):
    if sys.flags.optimize:raise ValueError('scale_audit_requires_assertions_enabled')
    cfg=json.loads(Path(config_path).read_bytes());study=Path(cfg['study']);parent=Path(cfg['parent'])
    out=Path(cfg['output']);out.mkdir(exist_ok=False)
    began=time.monotonic();cpu=time.process_time();sequence=0
    def event(stage,**fields):
        nonlocal sequence
        if (out/'CANCEL').exists():raise InterruptedError('scale_audit_cancelled')
        if time.monotonic()-began>1800:raise TimeoutError('scale_audit_deadline')
        sequence+=1;row=dict(sequence=sequence,stage=stage,utc=datetime.now(timezone.utc).isoformat(),**fields)
        write_json(out/'status.json',row)
        with (out/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(row),flush=True)
    try:
        if cfg['candidate']!='XAU-A0-scale-horizon-diagnostic-v1':raise ValueError('unregistered_diagnostic')
        for name,sha in cfg['pins'].items():
            if digest(Path(cfg['workspace'])/name)!=sha:raise ValueError('frozen_diagnostic_code_changed')
        census=json.loads((study/'census.json').read_bytes())
        assert digest(study/'census.json')==cfg['census_sha256']
        assert digest(study/'development-cohorts.json')==census['cohorts_sha256']
        for path,sha in census['parent_detail_pins'].items():assert digest(path)==sha
        assert digest(study/'tick-source-v1/result.json')==cfg['tick_source_sha256']
        source=json.loads((study/'tick-source-v1/result.json').read_bytes())
        if sorted(r['at'] for r in source['hours'])!=census['hours']:raise ValueError('source_hours_incomplete')
        parent_proofs=json.loads((parent/'tick-view-v2/seal.json').read_bytes())
        parent_hours={r['at']:r for r in parent_proofs['hours'] if START<=r['at']<END}
        view=out/'tick-view';view.mkdir();proofs={};counts=Counter()
        for n,row in enumerate(source['hours'],1):
            at=row['at']
            if not START<=at<END or at%HOUR:raise ValueError('non_development_tick_access_rejected')
            if digest(row['rawPath'])!=row['sha256']:raise ValueError('raw_hash_changed')
            if row.get('inherited_parent'):
                proof=parent_hours[at];path=parent/'tick-view-v2'/f'{at}.ticks'
                assert proof['raw_sha256']==row['sha256'] and digest(path)==proof['binary_sha256']
                count=proof['ticks'];counts['inherited_hours']+=1
            else:
                ticks=decode(json.loads(Path(row['rawPath']).read_bytes()),start_msc=at,end_msc=at+HOUR)
                assert len(ticks)==row['records'];path=view/f'{at}.ticks'
                with path.open('xb') as f:
                    for q in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units):f.write(RECORD.pack(*q))
                count=len(ticks);counts['new_hours']+=1
            counts['ticks']+=count;proofs[at]=dict(path=str(path),sha256=digest(path),ticks=count,raw_sha256=row['sha256'])
            if n%100==0:event('source_review',hours=n,total=len(source['hours']))
        write_json(out/'tick-view-seal.json',dict(hours=proofs,counts=dict(counts),source_sha256=cfg['tick_source_sha256']))
        preparation_seconds=time.monotonic()-began
        cohorts=json.loads((study/'development-cohorts.json').read_bytes())
        stop_rows=[];frictions=[];marks=[];passages=[];checks=Counter()
        for number,day in enumerate(cohorts,1):
            if not '2022-01-01'<=day['day']<='2023-12-31':raise ValueError('non_development_cohort')
            cs=day['intents'];midnight=cs[0]['decision_msc']//DAY*DAY
            needed={c['decision_msc']//HOUR*HOUR+i*HOUR for c in cs for i in range(3)}
            needed.update(midnight+h*HOUR for h in (18,20))
            for t in day['trades']:needed.update(range(t['entry_msc']//HOUR*HOUR,midnight+21*HOUR,HOUR))
            quotes=[]
            for hour in sorted(needed):
                proof=proofs[hour];path=Path(proof['path']);assert digest(path)==proof['sha256']
                quotes.extend(RECORD.iter_unpack(path.read_bytes()))
            assert all(a[0]<=b[0] for a,b in zip(quotes,quotes[1:]))
            times=[q[0] for q in quotes]
            trade_by_at={t['decision_msc']:t for t in day['trades']}
            for c in cs:
                assert START<=c['decision_msc']<END
                index=bisect_left(times,c['decision_msc']);q=quotes[index]
                assert q==(c['entry_msc'],c['entry_bid_units'],c['entry_ask_units'])
                assert q[0]-c['decision_msc']<=60_000
                stop_rows.append(stop_record(c));checks['raw_entry_prefix_parity']+=1
                groups=['raw']
                if c['status']=='friction_cap_rejected':groups.append('friction_rejected')
                if c['status'] in ('accepted','position_active_rejected'):groups.append('cost_pass')
                trade=trade_by_at.get(c['decision_msc'])
                if trade:groups.append('fills')
                narrow=bool(trade and 6.5<=trade['natural_sl_usd_per_oz']<=8)
                if narrow:groups.append('fills_SL6.5_8')
                cutoffs={'2h':q[0]+2*HOUR,'1800':midnight+18*HOUR,'2030':midnight+20*HOUR+HOUR//2}
                for name,cutoff in cutoffs.items():
                    m=markout(quotes,times,index,c['side'],cutoff)
                    marks.append(dict(day=day['day'],year=int(day['day'][:4]),decision_msc=c['decision_msc'],
                        side=c['side'],groups=groups,horizon=name,measurement=m))
                if trade:
                    frictions.append(friction_record(trade))
                    geometries=[('natural_fills',abs(trade['entry_units']-trade['stop_units']))]
                    if narrow:geometries.append(('fixed7.5_fills_SL6.5_8',7500))
                    for geometry,distance in geometries:
                        for name,cutoff in cutoffs.items():
                            event_row=first_passage(quotes,index,trade['entry_units'],trade['side'],distance,cutoff)
                            p1=event_row['price_units'];p0=trade['entry_units'];sign=1 if trade['side']=='BUY' else -1
                            if p1 is not None:
                                gross=sign*(p1-p0)/1000;comm=(p0+p1)/1000*.000007
                                terminal_net=gross-comm-.4
                            else:gross=terminal_net=None
                            event_row.update(day=day['day'],year=int(day['day'][:4]),geometry=geometry,
                                horizon=name,narrow=narrow,decision_msc=c['decision_msc'],side=trade['side'],
                                distance_usd_per_oz=distance/1000,terminal_gross_usd_per_oz=gross,
                                terminal_stress_net_usd_per_oz=terminal_net)
                            passages.append(event_row)
                            if geometry=='natural_fills' and name=='2h':
                                reason={'SL':'SL','TP_2R':'TP_2R','RIGHT_CENSORED':'TIME_STOP_2H'}[event_row['status']]
                                assert (reason,event_row['at'],p1)==(trade['exit_reason'],trade['exit_msc'],trade['exit_units'])
                                for scenario in ('reference','stress'):
                                    oz=D(trade['lot_steps']);g=money(D(sign*(p1-p0))/1000*oz)
                                    fees=money(D(p0)/1000*oz*D('.000007'))+money(D(p1)/1000*oz*D('.000007'))
                                    net=g-fees-(40*trade['lot_steps'] if scenario=='stress' else 0)
                                    assert net==round(trade['results'][scenario]['conditional_net_usd']*100)
                                    checks['parent_scenario_trade_net_parity']+=1
            if number%30==0:event('diagnostic_days',days=number,total=len(cohorts))
        tables=dict(friction=[],stops=[],markouts=[],passages=[])
        for year in (2022,2023,'development'):
            choose=lambda rows:[r for r in rows if year=='development' or r['year']==year]
            fs=choose(frictions)
            tables['friction'].append(dict(year=year,trades=len(fs),
                components={key:describe([r[key] for r in fs]) for key in (
                    'entry_spread_usd_per_oz','exit_spread_usd_per_oz','roundtrip_mid_spread_usd_per_oz',
                    'commission_usd_per_oz','reference_friction_usd_per_oz','stress_friction_usd_per_oz',
                    'stress_slippage_share','tp_no_improvement_usd_per_oz')},
                stress_slippage_dollar_share=sum(.4*r['ounces'] for r in fs)/sum(r['stress_friction_usd_per_oz']*r['ounces'] for r in fs)))
            for group in ('raw','friction_rejected','cost_pass','fills'):
                ss=[r for r in choose(stop_rows) if group=='raw' or (group=='friction_rejected' and r['status']=='friction_cap_rejected')
                    or (group=='cost_pass' and r['status'] in ('accepted','position_active_rejected')) or (group=='fills' and r['status']=='accepted')]
                tables['stops'].append(dict(year=year,group=group,signals=len(ss),
                    components={key:describe([r[key] for r in ss]) for key in (
                        'sl_usd_per_oz','close_to_bar_extreme_usd_per_oz','entry_drift_usd_per_oz','atr_buffer_usd_per_oz',
                        'atr_m15_usd_per_oz','bar_range_usd_per_oz','bar_range_to_atr','sl_to_atr','continuous_cost_floor_usd_per_oz')}))
                for horizon in ('2h','1800','2030'):
                    ms=[r for r in choose(marks) if group in r['groups'] and r['horizon']==horizon]
                    valid=[dict(day=r['day'],**r['measurement']) for r in ms if r['measurement'] is not None]
                    tables['markouts'].append(dict(year=year,group=group,horizon=horizon,signals=len(ms),
                        observed=len(valid),missing=len(ms)-len(valid),unique_days=len({r['day'] for r in valid}),
                        gross=describe([r['gross_usd_per_oz'] for r in valid]),
                        reference_net=describe([r['reference_net_usd_per_oz'] for r in valid]),
                        stress_net=describe([r['stress_net_usd_per_oz'] for r in valid]),
                        stress_positive_fraction=mean(r['stress_net_usd_per_oz']>0 for r in valid) if valid else None,
                        day_cluster_bootstrap_ci=bootstrapped_day_ci(valid,'stress_net_usd_per_oz') if group=='raw' else None))
            for geometry in ('natural_fills','natural_fills_SL6.5_8','fixed7.5_fills_SL6.5_8'):
                for horizon in ('2h','1800','2030'):
                    ps=[r for r in choose(passages) if r['horizon']==horizon and
                        (r['geometry']==geometry or geometry=='natural_fills_SL6.5_8' and r['geometry']=='natural_fills' and r['narrow'])]
                    tables['passages'].append(dict(year=year,geometry=geometry,horizon=horizon,**summarize_passage(ps)))
        write_json(out/'details.json',dict(friction=frictions,stops=stop_rows,markouts=marks,passages=passages))
        result=dict(schema='XAU-A0-scale-horizon-audit-v1',tables=tables,parent_checks=dict(checks),
            source_counts=dict(counts),config_sha256=digest(config_path),details_sha256=digest(out/'details.json'),
            B1_run=False,prices_2024_2026_used=False,broker_calls=0,portfolio_simulation=False,
            preparation_seconds=preparation_seconds,wall_seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        write_json(out/'result.json',result);event('completed',result_sha256=digest(out/'result.json'))
        return result
    except BaseException as exc:
        import traceback
        write_json(out/'failure.json',dict(type=type(exc).__name__,locations=[dict(file=f.filename,line=f.lineno) for f in traceback.extract_tb(exc.__traceback__)]))
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();execute(a.config)
