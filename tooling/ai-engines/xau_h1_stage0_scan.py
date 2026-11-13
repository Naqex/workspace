"""Raw H1 markout scanner, no orders/position exits/sizing/account simulation."""
from bisect import bisect_left
from collections import Counter,defaultdict
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D
import json
from pathlib import Path
from statistics import mean,median
import struct
import sys
import time

from eurusd_b0_source import digest,write_json
from index_tick_review import decode,minute_ohlc
from xau_intraday_source import source_views
from xau_h1_stage0_source import START,END,HOUR,DAY,HORIZONS,PRIMARY
from xau_scale_horizon_audit import describe,bootstrapped_day_ci

RECORD=struct.Struct('<qii')
RATE=D('.000007')


def funding_events(entry,exit):
    if exit<entry:raise ValueError('negative_horizon')
    date=datetime.fromtimestamp(entry/1000,timezone.utc).replace(hour=22,minute=0,second=0,microsecond=0)
    if int(date.timestamp()*1000)<=entry:date+=timedelta(days=1)
    events=[]
    while int(date.timestamp()*1000)<=exit:
        if date.weekday()<5:events.append(dict(at=int(date.timestamp()*1000),multiplier=3 if date.weekday()==2 else 1))
        date+=timedelta(days=1)
    return events


def economics(entry,exit,side):
    at,bid,ask=entry;end,ebid,eask=exit;sign=1 if side=='BUY' else -1
    p0=D(ask if sign==1 else bid)/1000;p1=D(ebid if sign==1 else eask)/1000
    mid=D(sign*(ebid+eask-bid-ask))/2000
    spread=D(ask-bid+eask-ebid)/2000
    gross=sign*(p1-p0)
    if mid-spread!=gross:raise ValueError('raw_mid_spread_bridge')
    commission=(p0+p1)*RATE
    units=sum(r['multiplier'] for r in funding_events(at,end))
    ref_funding=D('.20')*units;stress_funding=D('.40')*units
    return dict(signed_mid_move_usd_per_oz=float(mid),spread_usd_per_oz=float(spread),
        gross_after_spread_usd_per_oz=float(gross),commission_usd_per_oz=float(commission),
        stress_slippage_usd_per_oz=.4,rollover_units=units,
        reference_financing_usd_per_oz=float(ref_funding),stress_financing_usd_per_oz=float(stress_funding),
        reference_net_usd_per_oz=float(gross-commission-ref_funding),
        stress_net_usd_per_oz=float(gross-commission-D('.4')-stress_funding),
        stress_execution_friction_usd_per_oz=float(spread+commission+D('.4')))


def entry_geometry(signal,quote):
    at,bid,ask=quote;buy=signal['side']=='BUY';p0=ask if buy else bid
    distance=D(p0-signal['stop_units'] if buy else signal['stop_units']-p0)/1000
    valid=distance>0 and (bid>signal['stop_units'] if buy else ask<signal['stop_units'])
    friction=D(ask-bid)/1000+2*D(p0)/1000*RATE+D('.4')
    ratio=friction/distance if valid else None
    return dict(valid_stop=valid,natural_sl_usd_per_oz=float(distance),
        ex_ante_stress_friction_usd_per_oz=float(friction),friction_over_sl=float(ratio) if ratio is not None else None,
        pass12=bool(valid and ratio<=D('.12')),pass15=bool(valid and ratio<=D('.15')))


def quote_at(prefix,hour,target):
    if not START<=target<END:return None,'outside_development'
    rows=prefix.get(hour,[]);times=[q[0] for q in rows];index=bisect_left(times,target)
    if index==len(rows) or times[index]-target>60_000:return None,'no_fresh_quote'
    return rows[index],None


def verdict(yearly,primary):
    reasons=[]
    for y in yearly:
        if y['raw_signals']<40:reasons.append('CADENCE_'+str(y['year']))
        if y['entry_quote_missing'] or y['invalid_stops']:reasons.append('ENTRY_OR_GEOMETRY_UNKNOWN_'+str(y['year']))
        if y['scale_ratio_of_medians'] is None or y['scale_ratio_of_medians']>.12:reasons.append('SCALE_'+str(y['year']))
        if y['fraction_pass12']<.5:reasons.append('COST_REJECTION_GT50_'+str(y['year']))
        m=next(r for r in y['markouts'] if r['hours']==primary)
        if m['missing']:reasons.append('PRIMARY_ENDPOINTS_MISSING_'+str(y['year']))
        if m['stress_net']['mean'] is None or m['stress_net']['mean']<=0:reasons.append('ECONOMIC_'+str(y['year']))
        elif m['stress_net']['mean']<m['execution_friction']['mean']:reasons.append('NET_SMALLER_THAN_FRICTION_'+str(y['year']))
    return dict(status='STAGE0_MODEL_SCREEN_PASS_NOT_EDGE' if not reasons else 'NOT_ELIGIBLE_FOR_PACKAGING',
        reasons=reasons,primary_horizon_hours=primary,clean_OOS_verified=False,prop_qualified=False)


def execute(config_path):
    if sys.flags.optimize:raise ValueError('stage0_requires_assertions')
    cfg=json.loads(Path(config_path).read_bytes());study=Path(cfg['study']);root=Path(cfg['workspace'])
    out=Path(cfg['output']);out.mkdir(exist_ok=False)
    start=time.monotonic();cpu=time.process_time();seq=0
    def event(stage,**fields):
        nonlocal seq
        if (out/'CANCEL').exists():raise InterruptedError('stage0_cancelled')
        if time.monotonic()-start>1800:raise TimeoutError('stage0_deadline')
        seq+=1;row=dict(sequence=seq,stage=stage,utc=datetime.now(timezone.utc).isoformat(),**fields)
        write_json(out/'status.json',row)
        with (out/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(row),flush=True)
    try:
        if cfg['candidate']!='XAU-H1-stage0-discovery-v1':raise ValueError('unregistered_stage0')
        for name,sha in cfg['pins'].items():
            if digest(root/name)!=sha:raise ValueError('stage0_frozen_code_changed:'+name)
        census=json.loads((study/'census.json').read_bytes());signals=json.loads((study/'signals.json').read_bytes())
        assert digest(study/'signals.json')==census['signals_sha256']
        assert digest(study/'census.json')==cfg['census_sha256']
        assert digest(study/'tick-source-v1/result.json')==cfg['tick_source_sha256']
        source=json.loads((study/'tick-source-v1/result.json').read_bytes())
        assert sorted(r['at'] for r in source['hours'])==census['hours']
        correction=cfg.get('source_correction')
        if correction:
            assert digest(correction)==cfg['source_correction_sha256']
            assert digest(cfg['correction_parity'])==cfg['correction_parity_sha256']
            parity=json.loads(Path(cfg['correction_parity']).read_bytes())
            assert parity['H1_OHLC_bitwise_equal'] and parity['H4_OHLC_bitwise_equal']
            assert parity['source_signals_sha256']==census['signals_sha256']
        minutes,_=source_views(cfg['cache'],correction,end_msc=END)
        prefixes={};proofs=[];counts=Counter();mismatches=[];missing=set()
        view=out/'prefix';view.mkdir()
        for n,row in enumerate(source['hours'],1):
            at=row['at']
            if not START<=at<END:raise ValueError('stage0_non_development_source')
            if digest(row['rawPath'])!=row['sha256']:raise ValueError('stage0_raw_source_changed')
            ticks=decode(json.loads(Path(row['rawPath']).read_bytes()),start_msc=at,end_msc=at+HOUR)
            if len(ticks)!=row['records']:raise ValueError('tick_record_census')
            for minute,pair in minute_ohlc(ticks).items():
                bar=minutes.get(minute)
                if bar is None:missing.add(minute);continue
                actual=[pair['bid'][key] for key in ('open','high','low','close')]
                counts['M1_compared']+=1
                if actual!=bar:
                    counts['M1_mismatched']+=1
                    if len(mismatches)<30:mismatches.append(dict(at=minute,source=bar,observed=actual))
            rows=[q for q in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units) if q[0]<=at+120_000]
            prefixes[at]=rows;path=view/f'{at}.ticks'
            with path.open('xb') as f:
                for q in rows:f.write(RECORD.pack(*q))
            proofs.append(dict(at=at,raw_sha256=row['sha256'],prefix_sha256=digest(path),source_records=len(ticks),prefix_records=len(rows)))
            counts['ticks']+=len(ticks)
            if n%100==0:event('source_review',hours=n,total=len(source['hours']))
        source_review=dict(counts=dict(counts),mismatch_samples=mismatches,source_missing_minutes_with_ticks=sorted(missing),hours=proofs)
        write_json(out/'source-review.json',source_review)
        if mismatches:raise ValueError('stage0_source_OHLC_mismatch_before_markout')
        preparation=time.monotonic()-start;measurements=[]
        for signal in signals:
            at=signal['decision_msc'];assert START<=at<END
            entry,reason=quote_at(prefixes,at,at)
            row=dict(signal,entry_quote=list(entry) if entry else None,entry_missing_reason=reason,geometry=None,markouts=[])
            if entry:
                row['geometry']=entry_geometry(signal,entry)
                for hours in HORIZONS:
                    target=entry[0]+hours*HOUR;hour=target//HOUR*HOUR
                    quote,missing_reason=quote_at(prefixes,hour,target)
                    row['markouts'].append(dict(hours=hours,target_msc=target,exit_quote=list(quote) if quote else None,
                        missing_reason=missing_reason,economics=economics(entry,quote,signal['side']) if quote else None))
            else:
                row['markouts']=[dict(hours=h,missing_reason='entry_missing',economics=None) for h in HORIZONS]
            measurements.append(row)
        yearly=[];decisions=[]
        for recipe in PRIMARY:
            for view_name in ('BUY','BOTH'):
                ys=[]
                for year in (2022,2023):
                    rows=[r for r in measurements if r['recipe']==recipe and r['day'].startswith(str(year)) and (view_name=='BOTH' or r['side']=='BUY')]
                    geometry=[r['geometry'] for r in rows if r['geometry'] is not None]
                    valid=[g for g in geometry if g['valid_stop']]
                    sf=median(g['ex_ante_stress_friction_usd_per_oz'] for g in valid) if valid else None
                    ss=median(g['natural_sl_usd_per_oz'] for g in valid) if valid else None
                    record=dict(recipe=recipe,view=view_name,year=year,raw_signals=len(rows),buy_signals=sum(r['side']=='BUY' for r in rows),
                        sell_signals=sum(r['side']=='SELL' for r in rows),unique_days=len({r['day'] for r in rows}),
                        entry_quote_missing=len(rows)-len(geometry),invalid_stops=len(geometry)-len(valid),
                        natural_SL=describe([g['natural_sl_usd_per_oz'] for g in valid]),
                        ex_ante_friction=describe([g['ex_ante_stress_friction_usd_per_oz'] for g in valid]),
                        scale_ratio_of_medians=sf/ss if ss and ss>0 else None,
                        fraction_pass12=sum(g['pass12'] for g in geometry)/len(rows) if rows else 0,
                        fraction_pass15=sum(g['pass15'] for g in geometry)/len(rows) if rows else 0,
                        no_cost_filter_applied_to_markout=True,markouts=[])
                    for horizon in HORIZONS:
                        pairs=[(r,next(m for m in r['markouts'] if m['hours']==horizon)) for r in rows]
                        observed=[dict(day=r['day'],**m['economics']) for r,m in pairs if m['economics'] is not None]
                        def stats(key):return describe([r[key] for r in observed])
                        record['markouts'].append(dict(hours=horizon,observed=len(observed),missing=len(rows)-len(observed),
                            missing_reasons=dict(Counter(m['missing_reason'] for r,m in pairs if m['economics'] is None)),
                            gross_after_spread=stats('gross_after_spread_usd_per_oz'),
                            reference_net=stats('reference_net_usd_per_oz'),stress_net=stats('stress_net_usd_per_oz'),
                            execution_friction=stats('stress_execution_friction_usd_per_oz'),
                            stress_financing=stats('stress_financing_usd_per_oz'),
                            day_cluster_ci=bootstrapped_day_ci(observed,'stress_net_usd_per_oz') if observed else None))
                    yearly.append(record);ys.append(record)
                decisions.append(dict(recipe=recipe,view=view_name,**verdict(ys,PRIMARY[recipe])))
        write_json(out/'measurements.json',measurements)
        result=dict(schema='XAU-H1-stage0-result-v1',yearly=yearly,decisions=decisions,
            config_sha256=digest(config_path),measurements_sha256=digest(out/'measurements.json'),
            source_review_sha256=digest(out/'source-review.json'),source_counts=dict(counts),
            primary_horizons=PRIMARY,signal_recipes=3,direction_views_are_dependent=True,
            no_SLTP_or_account_simulation=True,prices2024_2026_read=False,broker_calls=0,
            funding_model='DECLARED_SYMMETRIC_22UTC_WEEKDAYS_WED3_NOT_TARGET_VERIFIED',
            preparation_seconds=preparation,wall_seconds=time.monotonic()-start,cpu_seconds=time.process_time()-cpu)
        write_json(out/'result.json',result);event('completed',result_sha256=digest(out/'result.json'))
        return result
    except BaseException as exc:
        import traceback
        write_json(out/'failure.json',dict(type=type(exc).__name__,locations=[dict(file=f.filename,line=f.lineno) for f in traceback.extract_tb(exc.__traceback__)]))
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();execute(a.config)
