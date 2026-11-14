"""Finite registered structural atlas. Phase2 owns Development only."""
from collections import defaultdict,deque,Counter
from datetime import datetime,timezone
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING
from statistics import mean,median
import numpy as np

from prop_campaign_source import START,END,FINAL,HOUR,DAY,Calendar,CALENDAR,read,write_json,digest
from prop_campaign_exits import funding_rate
from xau_h1_stage0_scan import funding_events
from xau_h1_stage0_source import signal_features
from prop_atlas_source import inputs
from prop_atlas_core import JOB,event

ASSETS=('XAUUSD','EURUSD','US500','GBPUSD','AUDUSD')


def catalog():
    out=[]
    for asset in ASSETS:
        for mechanism in ('SWEEP',) if asset=='XAUUSD' else ('SWEEP','CONT'):
            for region in ('ASIA','PREVDAY'):
                for window in ('LONDON','NY'):
                    for horizon in ('DAY','24H','48H'):
                        out.append(dict(id=f'{asset}.{mechanism}.{region}.{window}.{horizon}',
                            asset=asset,mechanism=mechanism,region=region,window=window,horizon=horizon))
    for mechanism in ('IMPULSE','TWOBAR'):
        for window in ('LONDON','NY'):
            out.append(dict(id=f'XAUUSD.{mechanism}.D1H4.{window}.DAY',asset='XAUUSD',
                mechanism=mechanism,region='D1H4',window=window,horizon='DAY'))
    if len(out)!=112:raise ValueError('catalog_budget')
    return out


def daily_context(hours):
    days=defaultdict(list)
    for r in hours:
        if r[5]==60:days[r[0]//DAY*DAY].append(r)
    regions={};trends={};closes=deque(maxlen=20);mas=deque(maxlen=4)
    last=None;last_d1=None
    for day,rs in sorted(days.items()):
        if last is not None and day-last[0]<=4*DAY:
            regions[day]=last[1]
        trends[day]=(len(mas)==4 and last_d1 is not None and
            day-last_d1[0]<=4*DAY and last_d1[1]>mas[-1] and mas[-1]>mas[0])
        if len(rs)>=12:
            last=(day,(max(r[2] for r in rs),min(r[3] for r in rs)),rs[-1][4])
        if len(rs)>=20:
            closes.append(D(rs[-1][4]))
            if len(closes)==20:mas.append(sum(closes)/20)
            last_d1=(day,rs[-1][4])
    return regions,trends


def candidates(hours,asset,*,first=START,end=END,only_cells=None):
    if (first,end) not in ((START,END),(END,FINAL)):
        raise ValueError('registered_atlas_window_required')
    if end==FINAL and not only_cells:
        raise ValueError('validation_requires_frozen_cell_whitelist')
    cells=[r for r in catalog() if r['asset']==asset]
    if only_cells is not None:
        if not set(only_cells)<=set(r['id'] for r in cells):
            raise ValueError('unregistered_atlas_cell')
        cells=[r for r in cells if r['id'] in only_cells]
    history,up=daily_context(hours)
    hm={r[0]:r for r in hours if r[5]==60}
    cal=Calendar(CALENDAR);seen=set();signals=[];abstentions=Counter()
    for f in signal_features(hours):
        at=f['at'];dt=datetime.fromtimestamp(at/1000,timezone.utc)
        if not first<=at<end or dt.weekday()>=5 or f['atr_before'] is None:
            continue
        window='LONDON' if 8<=dt.hour<=11 else 'NY' if 13<=dt.hour<=16 else None
        if window is None:continue
        if not cal.allowed(at):
            abstentions['CALENDAR_DECISION']+=1;continue
        day=at//DAY*DAY;b=f['bar'];prev=f['previous'];atr=f['atr_before'];ma=f['ma_before']
        asia=[hm.get(day+i*HOUR) for i in range(6)]
        zones={'ASIA':(max(r[2] for r in asia),min(r[3] for r in asia)) if all(r is not None for r in asia) else None,
               'PREVDAY':history.get(day)}
        for cell in cells:
            key=(cell['id'],day)
            if cell['window']!=window or key in seen:continue
            side=None;extreme=None;mech=cell['mechanism']
            zone=zones.get(cell['region'])
            if mech=='SWEEP' and zone:
                upper,lower=zone
                buy=b[3]<lower<b[4] and b[4]>b[1]
                sell=b[2]>upper>b[4] and b[4]<b[1]
                if buy and sell:abstentions['AMBIGUOUS_SWEEP']+=1;continue
                if buy:side='BUY';extreme=b[3]
                elif sell:side='SELL';extreme=b[2]
            elif mech=='CONT' and zone and prev is not None:
                upper,lower=zone
                if prev[4]<=upper<b[4] and f['bias']=='BUY':side='BUY';extreme=lower
                elif prev[4]>=lower>b[4] and f['bias']=='SELL':side='SELL';extreme=upper
            elif mech in ('IMPULSE','TWOBAR') and prev is not None:
                if not (up.get(day,False) and f['bias']=='BUY' and ma is not None and b[4]>ma):
                    continue
                if mech=='IMPULSE' and b[4]-b[1]>=atr*D('.75') and b[4]>prev[2]:
                    side='BUY';extreme=b[3]
                if mech=='TWOBAR' and prev[4]>prev[1] and b[4]>b[1] and b[3]>prev[3] and b[4]>prev[2]:
                    side='BUY';extreme=min(b[3],prev[3])
            if side is None:continue
            stop=D(extreme)+(-atr/10 if side=='BUY' else atr/10)
            stop=int(stop.to_integral_value(rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING))
            seen.add(key);signals.append(dict(cell,recipe=cell['id'],side=side,decision_msc=at,
                day=dt.date().isoformat(),stop_units=stop,known_h4_at=f['bias_at']))
    return signals,dict(abstentions)


def exit_deadline(row,entry):
    end,why=Calendar(CALENDAR).deadline(entry)
    target=entry//DAY*DAY+20*HOUR+HOUR//2 if row['horizon']=='DAY' else entry+(24 if row['horizon']=='24H' else 48)*HOUR
    return (target,row['horizon']) if target<end else (end,why)


def money(row,ent,out,scale,cell):
    buy=row['side']=='BUY';s=1 if buy else -1
    p0=(ent[2] if buy else ent[1])/scale;p1=(out[1] if buy else out[2])/scale
    spread=(ent[2]-ent[1]+out[2]-out[1])/(2*scale)
    if row['asset']=='XAUUSD':
        commission=(p0+p1)*.000007;slip=.4
        carry=funding_rate(row['side'],cell)*sum(e['multiplier'] for e in funding_events(ent[0],out[0]))
    elif row['asset']=='US500':
        commission=1.;slip=1.5;carry=-2*(out[0]//DAY-ent[0]//DAY)
    else:
        commission=.00005;slip=.00004
        carry=-.0004*sum(e['multiplier'] for e in funding_events(ent[0],out[0]))
    gross=s*(p1-p0);friction=spread+commission+slip
    return dict(gross=gross,commission=commission,slippage=slip,swap=carry,
        net=gross-commission-slip+carry,execution_friction=friction)


def score(cell,signals,reader,scale,kind):
    rows=[];source_unknown=False
    for r in signals:
        try:
            entry=reader.endpoint(r['decision_msc'])
            if entry is None:rows.append(dict(r,missing='ENTRY'));continue
            end,why=exit_deadline(r,entry[0]);exit=reader.endpoint(end)
            if exit is None:rows.append(dict(r,missing='ENDPOINT'));continue
        except ValueError as e:
            if str(e).startswith('unadmitted_tick_hour:'):raise
            rows.append(dict(r,missing='SCOPE_OR_ENDPOINT'));continue
        buy=r['side']=='BUY';price=entry[2] if buy else entry[1]
        stop=(price-r['stop_units'] if buy else r['stop_units']-price)/scale
        valid=stop>0 and (entry[1]>r['stop_units'] if buy else entry[2]<r['stop_units'])
        m={c:money(r,entry,exit,scale,c) for c in ('SYM_FLAT','ASYM_FLAT')}
        if r['asset']=='XAUUSD':exante=(entry[2]-entry[1])/scale+2*price/scale*.000007+.4
        elif r['asset']=='US500':exante=(entry[2]-entry[1])/scale+2.5
        else:exante=(entry[2]-entry[1])/scale+.00009
        rows.append(dict(r,entry_quote=entry,exit_quote=exit,deadline_msc=end,
            deadline_kind=why,natural_sl=stop,valid_geometry=valid,friction=exante,
            pass15=bool(valid and exante/stop<=.15),money=m,source_kind=kind))
    annual=[]
    for year in (2022,2023):
        allrows=[r for r in rows if r['day'].startswith(str(year))]
        ok=[r for r in allrows if 'money' in r]
        reasons=[]
        if len(allrows)<40:reasons.append('CADENCE_LT40')
        if len(ok)!=len(allrows):reasons.append('DATA_ENDPOINT_INCOMPLETE')
        if any(not r['valid_geometry'] for r in ok):reasons.append('INVALID_GEOMETRY')
        ratio=median(r['friction'] for r in ok)/median(r['natural_sl'] for r in ok) if ok else None
        keep=sum(r['pass15'] for r in ok)/len(allrows) if allrows else 0
        if ratio is None or ratio>.15:reasons.append('MEDIAN_SCALE_GT15')
        if keep<.6:reasons.append('SCALE_RETENTION_LT60')
        nets={c:mean(r['money'][c]['net'] for r in ok) if ok else None for c in ('SYM_FLAT','ASYM_FLAT')}
        friction=mean(r['money']['SYM_FLAT']['execution_friction'] for r in ok) if ok else None
        for c,n in nets.items():
            if n is None or n<=0:reasons.append('NET_NONPOSITIVE_'+c)
            elif n<friction:reasons.append('NET_LT_FRICTION_'+c)
        if cell['asset']=='US500' and cell['horizon']!='DAY':
            reasons.append('DIVIDEND_CARRY_TARGET_UNVERIFIED')
        annual.append(dict(year=year,raw=len(allrows),priced=len(ok),
            natural_sl_median=median(r['natural_sl'] for r in ok) if ok else None,
            scale_ratio=ratio,pass15_fraction=keep,net_mean=nets,
            mean_execution_friction=friction,reasons=reasons))
    return dict(cell=cell,annual=annual,stage0_pass=all(not r['reasons'] for r in annual),
        preliminary_component=kind in ('H1_OPEN_PROXY','PAIRED_M1_OPEN_MODEL'),rows=rows)


def prepare():
    data=inputs();allrows={};abstentions={}
    for asset,(hours,reader,scale,kind) in data.items():
        r,a=candidates(hours,asset);allrows[asset]=r;abstentions[asset]=a
        write_json(JOB/f'atlas-{asset}-signals.json',r)
        event('atlas_signal_census',asset=asset,signals=len(r),cells=len([c for c in catalog() if c['asset']==asset]))
    needed=set()
    for r in allrows['XAUUSD']:
        at=r['decision_msc'];end,_=exit_deadline(r,at)
        needed.update((at//HOUR*HOUR,end//HOUR*HOUR))
    manifest=data['XAUUSD'][1].files
    missing=sorted(needed-set(manifest))
    write_json(JOB/'gold-endpoint-census.json',dict(schema='XAU-H1-execution-census-v1',
        scope_start=START,scope_end_exclusive=END,hours=missing,reused_hours=[],
        needed=sorted(needed),registered_before_PnL=True))
    write_json(JOB/'atlas-census.json',dict(cells=catalog(),counts={k:len(v) for k,v in allrows.items()},
        abstentions=abstentions,missing_gold_hours=len(missing),selection_cutoff=END,
        source_inventory_sha256=digest(JOB/'source-inventory.json'),PnL_computed=False))
    event('atlas_census_complete',missing_gold_hours=len(missing))


def run():
    data=inputs();result=[]
    census=read(JOB/'atlas-census.json')
    if census['cells']!=catalog():raise ValueError('registered_catalog_changed')
    for asset,(hours,reader,scale,kind) in data.items():
        signals=read(JOB/f'atlas-{asset}-signals.json')
        for c in [c for c in catalog() if c['asset']==asset]:
            r=score(c,[s for s in signals if s['id']==c['id']],reader,scale,kind)
            write_json(JOB/f"stage0-{c['id']}.json",r)
            result.append({k:v for k,v in r.items() if k!='rows'})
            event('stage0_cell',cell=c['id'],pass_gate=r['stage0_pass'])
    write_json(JOB/'atlas-stage0.json',dict(cells=result,trials=len(result),
        survivors=[r['cell']['id'] for r in result if r['stage0_pass']],
        consumed_data='2022-2023 only',prices2024_2026_read=False))


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('prepare','run'))
    args=p.parse_args();globals()[args.stage]()
