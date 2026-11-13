"""Three preregistered H1 signal mechanisms, bounded Development source, no PnL."""
from bisect import bisect_right
from collections import Counter,deque
from datetime import datetime,timezone
from decimal import Decimal as D,ROUND_FLOOR,ROUND_CEILING
import json
from pathlib import Path

from eurusd_b0_source import digest,write_json
from xau_intraday_source import source_views

HOUR=3_600_000
DAY=24*HOUR
START=1_640_995_200_000
END=1_704_067_200_000
HORIZONS=(4,8,24,48)
PRIMARY={'H1A_ASIA':8,'H1B_RECLAIM':24,'H1C_MOMENTUM':8}


def aggregate_h4(hours):
    groups={}
    for row in hours:
        if row[5]!=60:continue
        groups.setdefault(row[0]//(4*HOUR)*(4*HOUR),[]).append(row)
    result=[]
    for at,rows in sorted(groups.items()):
        if [r[0] for r in rows]!=[at+i*HOUR for i in range(4)]:continue
        result.append([at,rows[0][1],max(r[2] for r in rows),min(r[3] for r in rows),rows[-1][4]])
    return result


def h4_bias(hours):
    closes=deque(maxlen=20);means=deque(maxlen=4);result={}
    for at,op,high,low,close in aggregate_h4(hours):
        closes.append(D(close))
        if len(closes)!=20:continue
        ma=sum(closes)/20;means.append(ma)
        if len(means)!=4:continue
        side='BUY' if close>ma and ma>means[0] else 'SELL' if close<ma and ma<means[0] else None
        result[at+4*HOUR]=dict(side=side,close=close,sma20=str(ma),sma20_lag3=str(means[0]))
    return result


def signal_features(hours):
    bias=h4_bias(hours);known=sorted(bias);closes=deque(maxlen=20)
    atr=None;seed=[];previous=None;recent=deque(maxlen=3);result=[]
    for row in hours:
        if row[5]!=60:continue
        at,op,high,low,close,_=row;decision=at+HOUR
        index=bisect_right(known,decision)-1
        b_at=known[index] if index>=0 else None
        b=bias[b_at] if b_at is not None and decision-b_at<=8*HOUR else None
        adjacent=previous is not None and previous[0]+HOUR==at
        if not adjacent:recent.clear()
        recent.append(row)
        result.append(dict(bar=row,at=decision,ma_before=sum(closes)/20 if len(closes)==20 else None,
            atr_before=atr,bias=b['side'] if b else None,bias_at=b_at,
            previous=previous if adjacent else None,recent=list(recent)))
        tr=D(high-low) if previous is None else D(max(high-low,abs(high-previous[4]),abs(low-previous[4])))
        if atr is None:
            seed.append(tr)
            if len(seed)==14:atr=sum(seed)/14
        else:atr=(13*atr+tr)/14
        closes.append(D(close));previous=row
    return result


def mechanisms(feature,asia):
    at=feature['at'];bar=feature['bar'];_,op,high,low,close,_=bar
    prev=feature['previous'];atr=feature['atr_before'];ma=feature['ma_before'];side=feature['bias']
    if side is None or prev is None or atr is None or ma is None:return []
    buy=side=='BUY';result=[]
    def add(recipe,extreme):
        stop=(D(extreme)-atr/10).to_integral_value(rounding=ROUND_FLOOR) if buy else (D(extreme)+atr/10).to_integral_value(rounding=ROUND_CEILING)
        result.append(dict(recipe=recipe,side=side,decision_msc=at,day=datetime.fromtimestamp(at/1000,timezone.utc).date().isoformat(),
            stop_units=int(stop),atr_h1_before_units=str(atr),sma_h1_before_units=str(ma),
            structure_extreme_units=extreme,bar_units=bar[1:5],bias_h4_known_at=feature['bias_at']))
    if asia is not None:
        asia_high,asia_low=asia
        if (close>asia_high and prev[4]<=asia_high if buy else close<asia_low and prev[4]>=asia_low):
            add('H1A_ASIA',asia_low if buy else asia_high)
    if (prev[4]<=ma<close and close>op if buy else prev[4]>=ma>close and close<op):
        add('H1B_RECLAIM',min(low,prev[3]) if buy else max(high,prev[2]))
    recent=feature['recent']
    if len(recent)==3:
        one,two,three=recent
        if (D(close-prev[4])>=atr and close>op and one[3]<two[3]<three[3] if buy else
            D(prev[4]-close)>=atr and close<op and one[2]>two[2]>three[2]):
            add('H1C_MOMENTUM',min(r[3] for r in recent) if buy else max(r[2] for r in recent))
    return result


def prepare(cache,study,parents):
    study=Path(study);study.mkdir(exist_ok=False)
    _,views=source_views(cache,end_msc=END)
    hours=views['h1'];hour_map={r[0]:r for r in hours if r[5]==60}
    signals=[];counts={str(y):Counter() for y in (2022,2023)};days={str(y):set() for y in (2022,2023)}
    asia_days={str(y):set() for y in (2022,2023)};seen_asia=set();needed=set()
    for feature in signal_features(hours):
        at=feature['at'];dt=datetime.fromtimestamp(at/1000,timezone.utc)
        if not START<=at<END or dt.weekday()>=5 or not 8<=dt.hour<=15:continue
        year=str(dt.year);day=dt.date().isoformat();midnight=at//DAY*DAY
        days[year].add(day);counts[year]['source_H1_decisions']+=1
        if feature['bias'] is not None:counts[year]['directional_H4_decisions']+=1
        asian=[hour_map.get(midnight+i*HOUR) for i in range(6)]
        asia=None
        if all(r is not None for r in asian):
            asia_days[year].add(day);asia=(max(r[2] for r in asian),min(r[3] for r in asian))
        for signal in mechanisms(feature,asia):
            if signal['recipe']=='H1A_ASIA':
                if day in seen_asia:continue
                seen_asia.add(day)
            signals.append(signal);counts[year][signal['recipe']+'_'+signal['side']]+=1
            needed.add(at)
            for horizon in HORIZONS:
                target=at+horizon*HOUR
                if START<=target<END:needed.add(target)
    inherited={}
    for parent in parents:
        raw=json.loads(Path(parent).read_bytes())
        for row in raw['hours']:
            if not START<=row['at']<END or row['at'] not in needed:continue
            if row['at'] in inherited and inherited[row['at']]['sha256']!=row['sha256']:raise ValueError('parent_source_conflict')
            inherited[row['at']]=row
    write_json(study/'signals.json',signals)
    census=dict(schema='XAU-H1-stage0-census-v1',scope_start=START,scope_end_exclusive=END,hours=sorted(needed),
        reused_hours=[inherited[at] for at in sorted(inherited)],signals_sha256=digest(study/'signals.json'),
        yearly={year:dict(counts[year],source_days=len(days[year]),valid_asian_days=len(asia_days[year])) for year in counts},
        cache_manifest_sha256=digest(Path(cache)/'manifest.json'),parent_source_pins={str(p):digest(p) for p in parents},
        protocol_sha256=digest('planning/research/XAUUSD-H1-STAGE0-PROTOCOL-20261113.md'),PnL_computed=False,prices2024_2026_read=False)
    write_json(study/'census.json',census)
    print(json.dumps(dict(yearly=census['yearly'],raw_signals=len(signals),tick_hours=len(needed),reused=len(inherited),new_hours=len(needed)-len(inherited))))
    return census


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--study',required=True);p.add_argument('--parent',action='append',required=True)
    a=p.parse_args();prepare(a.cache,a.study,a.parent)
