"""Frozen A signal reuse and calendar/source admission, with 2025 price fence."""
from bisect import bisect_left,bisect_right
from datetime import datetime,timedelta,timezone
from functools import lru_cache
import json
from pathlib import Path
import struct
from eurusd_b0_source import digest,write_json
from xau_intraday_source import source_views
from xau_h1_stage0_source import START,HOUR,DAY,signal_features,mechanisms

END=1735689600000
REC=struct.Struct('<qii')


class Calendar:
    def __init__(self,path):
        self.data=json.loads(Path(path).read_bytes());self.events={r['day']:r for r in self.data['events']}
        self.flats=[]
        day=datetime(2022,1,1,tzinfo=timezone.utc)
        while day<datetime(2025,1,1,tzinfo=timezone.utc):
            text=day.date().isoformat();r=self.events.get(text)
            clock=r.get('flat_utc') if r else None
            if clock:self.flats.append((int((day+timedelta(hours=int(clock[:2]),minutes=int(clock[3:]))).timestamp()*1000),'HOLIDAY_FLAT'))
            if day.weekday()==4:self.flats.append((int((day+timedelta(hours=20,minutes=30)).timestamp()*1000),'FRIDAY_CLOSE'))
            day+=timedelta(days=1)
        self.flats.sort();self.times=[r[0] for r in self.flats]
    def allowed(self,at):
        d=datetime.fromtimestamp(at/1000,timezone.utc);r=self.events.get(d.date().isoformat())
        if d.weekday()>=5 or r and r['kind']=='CLOSED':return False
        if r and r.get('flat_utc') and d.strftime('%H:%M')>=r['flat_utc']:return False
        return True
    def deadline(self,at):
        if not START<=at<END or not self.allowed(at):raise ValueError('entry_outside_session')
        i=bisect_right(self.times,at)
        if i==len(self.flats):raise ValueError('missing_future_calendar_flat')
        flat,reason=self.flats[i];end=at+48*HOUR
        return (flat,reason) if flat<end else (end,'TIME_48H')


class Quotes:
    def __init__(self,manifest):self.files={int(k):v for k,v in manifest.items()}
    @lru_cache(maxsize=64)
    def hour(self,at):
        if not START<=at<END or at%HOUR:raise ValueError('2025_2026_prices_closed')
        r=self.files.get(at)
        if r is None:return [],[]
        rows=list(REC.iter_unpack(Path(r['path']).read_bytes()))
        return rows,[x[0] for x in rows]
    def endpoint(self,at):
        rows,times=self.hour(at//HOUR*HOUR);i=bisect_left(times,at)
        return (rows[i],i) if i<len(rows) and rows[i][0]-at<=60000 else (None,None)
    def interval(self,start,end):
        for hour in range(start//HOUR*HOUR,end//HOUR*HOUR+1,HOUR):
            if hour not in self.files:raise ValueError('unrequested_path_hour')
            rows,times=self.hour(hour)
            for i in range(bisect_left(times,start),bisect_right(times,end)):yield rows[i],i


def prepare(cfg_path):
    cfg=json.loads(Path(cfg_path).read_bytes());root=Path(cfg['output']);root.mkdir(exist_ok=False)
    freeze=json.loads(Path(cfg['calendar_freeze']).read_bytes())
    if digest(cfg['calendar'])!=freeze['calendar_sha256'] or digest(cfg['protocol'])!=freeze['protocol_sha256']:
        raise ValueError('calendar_must_be_frozen_before_2024')
    cal=Calendar(cfg['calendar']);patches={}
    for path in cfg['corrections']:
        p=json.loads(Path(path).read_bytes())
        for row in p['patches']:
            if not START<=row['at']<END:raise ValueError('correction_holdout')
            if row['at'] in patches and patches[row['at']]['corrected']!=row['corrected']:raise ValueError('conflicting_corrections')
            patches[row['at']]=row
    correction=dict(schema='XAU-A0-observed-tick-M1-corrections-v1',patches=list(patches.values()))
    write_json(root/'corrections.json',correction)
    _,views=source_views(cfg['cache'],root/'corrections.json',end_msc=END)
    hours=views['h1'];hour_map={r[0]:r for r in hours if r[5]==60};seen=set();signals=[]
    for f in signal_features(hours):
        at=f['at'];d=datetime.fromtimestamp(at/1000,timezone.utc);day=d.date().isoformat()
        if not START<=at<END or d.weekday()>=5 or not 8<=d.hour<=15:continue
        asia=[hour_map.get(at//DAY*DAY+i*HOUR) for i in range(6)]
        if any(r is None for r in asia):continue
        region=(max(r[2] for r in asia),min(r[3] for r in asia))
        for row in mechanisms(f,region):
            if row['recipe']=='H1A_ASIA' and day not in seen:signals.append(row);seen.add(day)
    parent=[r for r in json.loads(Path(cfg['parent_signals']).read_bytes()) if r['recipe']=='H1A_ASIA']
    if [r for r in signals if r['decision_msc']<1704067200000]!=parent:raise ValueError('frozen_210_A_signals_changed')
    write_json(root/'signals.json',signals)
    needed=set();closed=[]
    for row in signals:
        at=row['decision_msc']
        if not cal.allowed(at):closed.append(row);continue
        end,_=cal.deadline(at)
        if end+60000>=END:raise ValueError('holdout_deadline')
        needed.update(range(at//HOUR*HOUR,end//HOUR*HOUR+1,HOUR))
    old=Path(cfg['parent_attempt']);proof=json.loads((old/'source-review.json').read_bytes());binaries={}
    for r in proof['hours']:
        if r['at'] in needed:
            p=old/'ticks'/f"{r['at']}.ticks"
            if digest(p)!=r['binary_sha256']:raise ValueError('old_binary_changed')
            binaries[r['at']]=dict(path=str(p),sha256=r['binary_sha256'],records=r['records'])
    write_json(root/'inherited-binaries.json',binaries)
    missing=needed-binaries.keys();raw={}
    for path in cfg['raw_manifests']:
        for r in json.loads(Path(path).read_bytes())['hours']:
            if r['at'] in missing:raw[r['at']]=r
    census=dict(schema='XAU-H1-A-validation-census-v1',scope_start=START,scope_end_exclusive=END,
        holdout_start=END,hours=sorted(missing),reused_hours=list(raw.values()),
        signal_sha256=digest(root/'signals.json'),calendar_sha256=digest(cfg['calendar']),
        prices2025_2026_read=False)
    write_json(root/'census.json',census)
    write_json(root/'preparation.json',dict(config_sha256=digest(cfg_path),yearly={str(y):sum(r['day'].startswith(str(y)) for r in signals) for y in (2022,2023,2024)},
        parent_signal_parity=True,parent_signals=210,raw_signals=len(signals),session_rejections=closed,
        requested_hours=len(needed),inherited_binary_hours=len(binaries),raw_hours_reused=len(raw),
        new_raw_hours=len(missing)-len(raw),prices2025_2026_read=False))
    print((root/'preparation.json').read_text())


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();prepare(a.config)
