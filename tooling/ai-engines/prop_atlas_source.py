"""Atlas input census: explicit bounded reads, no 2024 selection prices."""
from collections import defaultdict
from decimal import Decimal as D
from pathlib import Path
import json

from prop_campaign_source import (ROOT,JOB as V1,PARENT,START,END,FINAL,HOUR,DAY,
    Prices,Calendar,CALENDAR,read,write_json,digest,gold_views,stamp)
from prop_atlas_core import JOB,event
from us500_year_source import load_year_side

PROOFS={2022:'7a41f021c86a04345ce2591b90efa72112792ef5479c16ff6d1167f7064dc840',
        2023:'61d46d061a870e98a97b696b95d8efab2d28abe190d94f2fc04c1b2255b1909c'}


class ComponentQuotes:
    def __init__(self,rows,scale,kind):
        self.rows=rows;self.scale=scale;self.kind=kind
    def endpoint(self,at):
        if not START<=at<END:raise ValueError('atlas_development_price_fence')
        width=HOUR if self.kind=='H1_OPEN_PROXY' else 60000
        if at%width:return None
        r=self.rows.get(at)
        if r is None:return None
        b,a=r
        return [at,b[0],a[0],0] if 0<b[0]<=a[0] else None


def aggregate_minutes(rows):
    groups=defaultdict(list)
    for at,(bid,ask) in rows.items():groups[at//HOUR*HOUR].append((at,bid))
    out=[]
    for at,rs in sorted(groups.items()):
        rs.sort()
        out.append([at,rs[0][1][0],max(r[1][1] for r in rs),
                    min(r[1][2] for r in rs),rs[-1][1][3],len(rs)])
    return out


def load_eur():
    proofs=read(V1/'eur-dev-source-review.json')
    quotes={};hours=[];pins=[]
    cfg=read(ROOT/'eurusd-b0-20261113/config-attempt-1.json')
    for p in proofs:
        year=p['year']
        if year not in (2021,2022,2023):raise ValueError('EUR_year_not_development')
        path=p['coarse_path']
        if digest(path)!=p['sha256']:raise ValueError('EUR_parent_coarse_changed')
        payload=read(path)['payload']
        if payload['binding']['sha256']!=p['raw_sha256']:raise ValueError('EUR_raw_binding')
        source=next(s for s in cfg['sources'] if s['first_day'].startswith(str(year)))
        hpath=ROOT/f"eurusd-b0-20261113/prepared-v1/{source['first_day']}/bars.json"
        bars=read(hpath)['h1'];hours.extend(bars)
        for r in payload['hours']:
            at=r['mid']['timestamp']*1000
            if START<=at<END:
                b=int(D(r['bid'][0])*100000);a=int(D(r['ask'][0])*100000)
                quotes[at]=[r['first_time_msc'],b,a,r['first_sequence']]
        pins.append(dict(coarse_path=path,sha256=p['sha256'],bars_path=str(hpath),bars_sha256=digest(hpath)))
    # Existing full raw CSV, timestamp-seek endpoint resolver; redirect evidence
    # to this job via a wrapper rather than overwriting the PR79 artifacts.
    q=EURExact(quotes,[s for s in cfg['sources'] if s['last_day']<='20231231'])
    return hours,q,pins


class EURExact:
    def __init__(self,rows,sources):
        self.rows=rows;self.sources=sources;self.cache={}
    def endpoint(self,at):
        if not START<=at<END:raise ValueError('EUR_development_price_fence')
        if at in self.cache:return self.cache[at]
        row=self.rows.get(at//HOUR*HOUR)
        if row and 0<=row[0]-at<=60000:return row
        from eurusd_b0_source import seek_day,units
        from datetime import datetime,timezone
        d=datetime.fromtimestamp(at/1000,timezone.utc);day=d.strftime('%Y%m%d')
        source=next(s for s in self.sources if s['first_day']<=day<=s['last_day'])
        target=d.strftime('%Y%m%d %H:%M:%S.')+f'{at%1000:03d}'
        result=None
        with Path(source['path']).open('rb') as f:
            f.readline();seek_day(f,day)
            for line in f:
                ts=line[:21].decode('ascii')
                if ts<target:continue
                if ts[:8]>'20231231':break
                actual=int(datetime.strptime(ts,'%Y%m%d %H:%M:%S.%f').replace(tzinfo=timezone.utc).timestamp()*1000)
                if actual-at>60000:break
                row=line.decode('ascii').split(',')
                result=[actual,units(row[1]),units(row[2]),None];break
        self.cache[at]=result
        return result


def load_us500():
    rows={};pins=[]
    for year in (2022,2023):
        root=ROOT/f'us500-explicit-source-v1/{year}'
        sides={s:load_year_side(root,year=year,side=s,proof_sha256=PROOFS[year],
                               registered_years=(2022,2023)) for s in ('bid','ask')}
        if set(sides['bid']['rows'])!=set(sides['ask']['rows']):
            raise ValueError('US500_pairing_changed')
        for at in sides['bid']['rows']:
            pair=[]
            for s in ('bid','ask'):
                r=sides[s]['rows'][at]
                pair.append([int(D(str(r[k]))*1000) for k in ('open','high','low','close')])
            rows[at]=pair
        pins.extend(dict(path=p,sha256=h) for p,h in sides['bid']['bindings'].items())
        pins.extend(dict(path=p,sha256=h) for p,h in sides['ask']['bindings'].items())
    return aggregate_minutes(rows),ComponentQuotes(rows,1000,'PAIRED_M1_OPEN_MODEL'),pins


def load_extra_fx(asset):
    root=ROOT/'fx-h1-history-v3'
    seals=read(root/'sealed-books.json')
    if isinstance(seals,dict):
        seals=seals.get('books',seals.get('seals',[]))
    hours=[];rows={};pins=[]
    for year in (2021,2022,2023):
        sides={}
        for side in ('bid','ask'):
            path=root/f'{year}-{asset.lower()}-{side}.json'
            if not path.exists():continue
            # Immutable input and producer provenance are saved before signals.
            proof=path.with_name(path.stem+'-source-proof.json')
            if not proof.exists():raise ValueError('FX_side_source_proof_missing')
            seal=next(s for s in seals if s['book']==path.stem)
            if digest(path)!=seal['sha256'] or digest(proof)!=seal['sourceProofSha256']:
                raise ValueError('FX_accepted_side_seal_changed')
            data=read(path)
            if isinstance(data,dict):data=data.get('rows',data.get('data',[]))
            if len(data)!=seal['rows'] or data[0]['timestamp']!=seal['first'] or data[-1]['timestamp']!=seal['last']:
                raise ValueError('FX_accepted_side_census_changed')
            sides[side]={r['timestamp']:[int(D(str(r[k]))*100000)
                for k in ('open','high','low','close')] for r in data
                if stamp('2021-11-01')<=r['timestamp']<END}
            pins.append(dict(path=str(path),sha256=digest(path),
                proof_path=str(proof),proof_sha256=digest(proof)))
        if set(sides)!= {'bid','ask'}:continue
        for at,b in sorted(sides['bid'].items()):
            hours.append([at,*b,60])
            if START<=at<END and at in sides['ask']:rows[at]=(b,sides['ask'][at])
    return hours,ComponentQuotes(rows,100000,'H1_OPEN_PROXY'),pins


def inputs():
    correction=JOB/'gold-source-corrections.json'
    if correction.exists():
        from xau_intraday_source import source_views
        _,v=source_views(ROOT/'gold-continuous-B2-20261113-v1/source-cache',correction,end_msc=END)
        h=v['h1']
    else:h=gold_views()
    manifest=read(V1/'gold-dev-manifest-v2.json')
    extra=JOB/'gold-atlas-manifest.json'
    if extra.exists():manifest=read(extra)
    data={'XAUUSD':(h,Prices(manifest),1000,'OBSERVED_TICKS')}
    proofs={'XAUUSD':dict(source='PR79 admitted QDM/tick source',hours=len(h),
                         cutoff=END,manifest_sha256=digest(V1/'gold-dev-manifest-v2.json'))}
    for asset,loader in (('EURUSD',load_eur),('US500',load_us500),
                         ('GBPUSD',lambda:load_extra_fx('GBPUSD')),
                         ('AUDUSD',lambda:load_extra_fx('AUDUSD'))):
        bars,q,pins=loader()
        data[asset]=(bars,q,1000 if asset=='US500' else 100000,
                     'OBSERVED_PAIRED_OPEN' if asset=='EURUSD' else q.kind)
        proofs[asset]=dict(pins=pins,hours=len(bars),cutoff=END)
        event('source_admission',asset=asset,hours=len(bars))
    proofs['USDJPY']=dict(status='NOT_CONTINUOUS_ADMITTED_SOURCE',
        reason='Selected fixing-day M1 history cannot generate full-year H1 session catalog')
    write_json(JOB/'source-inventory.json',proofs)
    return data


def admit_gold():
    import numpy as np
    from xau_intraday_source import source_views
    from index_tick_review import decode,minute_ohlc
    from prop_campaign_source import DTYPE
    packet=read(JOB/'gold-endpoint-source/result.json')
    census=read(JOB/'gold-endpoint-census.json')
    if sorted(r['at'] for r in packet['hours'])!=sorted(census['hours']):
        raise ValueError('gold_endpoint_census_changed')
    old=ROOT/'xauusd-h1-stage0-20261113/source-correction-v1.json'
    minutes,_=source_views(ROOT/'gold-continuous-B2-20261113-v1/source-cache',old,end_msc=END)
    manifest=read(V1/'gold-dev-manifest-v2.json')
    target=JOB/'gold-endpoint-binaries';target.mkdir(exist_ok=False)
    proof=[];patches=[];missing=[]
    for n,r in enumerate(packet['hours']):
        at=r['at']
        if not START<=at<END or digest(r['rawPath'])!=r['sha256']:raise ValueError('gold_raw_binding')
        ticks=decode(read(r['rawPath']),start_msc=at,end_msc=at+HOUR)
        bars=minute_ohlc(ticks)
        for m in range(at,at+HOUR,60000):
            if m in minutes and m not in bars:missing.append(m)
        for m,pair in bars.items():
            values=[pair['bid'][k] for k in ('open','high','low','close')]
            if m in minutes and values!=minutes[m]:
                patches.append(dict(at=m,original=minutes[m],corrected=values,
                    raw_path=r['rawPath'],raw_sha256=r['sha256']))
        a=np.empty(len(ticks),dtype=DTYPE)
        a['t']=ticks.timestamps;a['b']=ticks.bid_units;a['a']=ticks.ask_units
        path=target/f'{at}.ticks';a.tofile(path)
        manifest[str(at)]=dict(path=str(path),sha256=digest(path),records=len(a))
        proof.append(dict(at=at,raw_sha256=r['sha256'],binary_sha256=digest(path),
                          records=len(a),minutes=len(bars)))
        if n%100==0:event('gold_source_review',hours=n,total=len(packet['hours']))
    write_json(JOB/'gold-source-review.json',dict(hours=proof,patches=patches,
        M1_without_ticks=missing,prices2024_2026_read=False))
    if missing:raise ValueError('gold_new_tick_path_incomplete')
    if patches:
        allpatches=read(old);allpatches['patches']+=patches
        write_json(JOB/'gold-source-corrections.json',allpatches)
        event('gold_working_corrections_before_PnL',patches=len(patches))
    write_json(JOB/'gold-atlas-manifest.json',manifest)
    event('gold_source_admitted',new_hours=len(packet['hours']),corrections=len(patches))
