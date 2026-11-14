"""Bounded, source-bound inputs for the registered November prop campaign."""
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path
import json
import numpy as np

from eurusd_b0_source import digest, write_json
from xau_intraday_source import source_views
from xau_h1_stage0_source import signal_features, mechanisms, START, END, HOUR, DAY
from xau_a_validation_source import Calendar

FINAL = 1735689600000
ROOT = Path('E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1')
PARENT = ROOT/'xauusd-a-validation-20261114'
JOB = ROOT/'prop-qualification-campaign-20261114'
DTYPE = np.dtype([('t','<i8'),('b','<i4'),('a','<i4')])
CALENDAR = Path('planning/research/XAUUSD-A-SESSION-CALENDAR-20261114.json')


def read(path):
    return json.loads(Path(path).read_bytes())


def stamp(text):
    return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()*1000)


class Prices:
    def __init__(self, manifest, cutoff=END):
        if cutoff not in (END, FINAL):
            raise ValueError('unapproved_price_cutoff')
        self.cutoff = cutoff
        self.files = {int(k):v for k,v in manifest.items() if START<=int(k)<cutoff}
        self.accessed = set()

    @lru_cache(maxsize=48)
    def hour(self, at):
        if not START<=at<self.cutoff or at%HOUR:
            raise ValueError('closed_price_window')
        if at not in self.files:
            raise ValueError('unadmitted_tick_hour:'+str(at))
        r = self.files[at]
        if digest(r['path']) != r['sha256']:
            raise ValueError('tick_binary_checksum')
        rows = np.fromfile(r['path'], dtype=DTYPE)
        if (len(rows)!=r['records'] or len(rows) and
                (rows['t'][0]<at or rows['t'][-1]>=at+HOUR or
                 np.any(np.diff(rows['t'])<0) or np.any(rows['a']<rows['b']))):
            raise ValueError('tick_binary_schema')
        self.accessed.add(at)
        return rows

    def endpoint(self, at):
        a=self.hour(at//HOUR*HOUR);i=int(a['t'].searchsorted(at))
        if i==len(a) or a['t'][i]-at>60000:
            return None
        return [int(a['t'][i]),int(a['b'][i]),int(a['a'][i]),i]

    def path(self, start, end):
        if not START<=start<=end<self.cutoff:
            raise ValueError('path_crosses_closed_window')
        parts=[];ordinals=[]
        for h in range(start//HOUR*HOUR,end//HOUR*HOUR+1,HOUR):
            a=self.hour(h);lo=int(a['t'].searchsorted(start));hi=int(a['t'].searchsorted(end,side='right'))
            if hi>lo:
                parts.append(a[lo:hi]);ordinals.append(np.arange(lo,hi,dtype='int64'))
        if not parts:
            raise ValueError('empty_price_path')
        return np.concatenate(parts),np.concatenate(ordinals)


def gold_views(validation=False):
    correction = (PARENT/'source-v2/corrections.json' if validation else
                  ROOT/'xauusd-h1-stage0-20261113/source-correction-v1.json')
    _,views=source_views(ROOT/'gold-continuous-B2-20261113-v1/source-cache',
                         correction,end_msc=FINAL if validation else END)
    return views['h1']


def signals(hours, first=START, end=END, eur=False):
    """Closed Bid bars; no markout or trading-cost selection here."""
    result=[];seen=set();hourmap={r[0]:r for r in hours if r[5]==60}
    for f in signal_features(hours):
        at=f['at'];d=datetime.fromtimestamp(at/1000,timezone.utc)
        if not first<=at<end or d.weekday()>=5:
            continue
        b=f['bar'];prev=f['previous'];bias=f['bias'];atr=f['atr_before']
        if bias is None or prev is None or atr is None:
            continue
        day=d.date().isoformat();buy=bias=='BUY';candidates=[]
        if 8<=d.hour<=15:
            asia=[hourmap.get(at//DAY*DAY+i*HOUR) for i in range(6)]
            if all(r is not None for r in asia):
                region=(max(r[2] for r in asia),min(r[3] for r in asia))
                for r in mechanisms(f,region):
                    if r['recipe']=='H1A_ASIA':
                        candidates.append(dict(r,recipe='S3' if eur else 'A'))
        if not eur:
            if (12<=d.hour<=16 and
                    (prev[4]<prev[1] and b[4]>prev[2] if buy else
                     prev[4]>prev[1] and b[4]<prev[3])):
                candidates.append(dict(recipe='S1',extreme=min(b[3],prev[3]) if buy else max(b[2],prev[2])))
            recent=f['recent']
            if len(recent)==3 and 8<=d.hour<=16:
                one,two,three=recent
                if two[2]<=one[2] and two[3]>=one[3] and (b[4]>one[2] if buy else b[4]<one[3]):
                    candidates.append(dict(recipe='S2',extreme=one[3] if buy else one[2]))
        for r in candidates:
            key=(r['recipe'],day)
            if key in seen:
                continue
            seen.add(key)
            if 'stop_units' not in r:
                from decimal import Decimal,ROUND_FLOOR,ROUND_CEILING
                stop=Decimal(r['extreme'])+(-atr/10 if buy else atr/10)
                r.update(side=bias,decision_msc=at,day=day,
                    stop_units=int(stop.to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING)),
                    bias_h4_known_at=f['bias_at'],atr_h1_before_units=str(atr))
            result.append(r)
    return sorted(result,key=lambda r:(r['decision_msc'],r['recipe']))


def deadline(row, calendar, entry_msc=None):
    at=row['decision_msc'] if entry_msc is None else entry_msc
    end,reason=calendar.deadline(at)
    if row['recipe']=='S1':
        target=at//DAY*DAY+20*HOUR+HOUR//2;kind='SESSION_2030'
    elif row['recipe']=='S3':
        target=at+24*HOUR;kind='TIME_24H'
    else:
        return end,reason
    return (target,kind) if target<end else (end,reason)


def prepare_dev():
    JOB.mkdir(exist_ok=False)
    protocol=Path('planning/research/PROP-QUALIFICATION-CAMPAIGN-PROTOCOL-20261114.md')
    write_json(JOB/'registration.json',dict(protocol_sha256=digest(protocol),
        frozen_commit='95e3709',registered_utc=datetime.now(timezone.utc).isoformat(),
        anchor_result_sha256=digest(PARENT/'attempt-2/result.json'),
        calendar_sha256=digest(CALENDAR),price_cutoff=END,prices2025_2026_read=False))
    h=gold_views();write_json(JOB/'gold-dev-hours.json',h)
    s=signals(h);write_json(JOB/'gold-dev-signals.json',s)
    old=read(ROOT/'xauusd-h1-stage0-20261113/signals.json')
    parent=[dict(r,recipe='A') for r in old if r['recipe']=='H1A_ASIA']
    if [r for r in s if r['recipe']=='A']!=parent:
        raise ValueError('anchor_210_signal_parity')
    manifest=read(PARENT/'attempt-2/binary-manifest.json')
    cal=Calendar(CALENDAR);needed=set();endpoints=set();blocked=[]
    for r in s:
        at=r['decision_msc']
        if not cal.allowed(at):
            blocked.append(r);continue
        end,_=deadline(r,cal)
        if end+60000>=END:
            raise ValueError('dev_endpoint_in_validation')
        if r['recipe']=='A':
            needed.update(range(at//HOUR*HOUR,end//HOUR*HOUR+1,HOUR))
        else:
            endpoints.update((at//HOUR*HOUR,end//HOUR*HOUR))
    inherited={k:v for k,v in manifest.items() if int(k) in needed|endpoints}
    missing=sorted((needed|endpoints)-set(map(int,inherited)))
    write_json(JOB/'gold-dev-manifest.json',inherited)
    write_json(JOB/'gold-dev-census.json',dict(needed=sorted(needed|endpoints),
        missing=missing,session_blocked=blocked,signals_sha256=digest(JOB/'gold-dev-signals.json'),
        counts={name:sum(r['recipe']==name for r in s) for name in ('A','S1','S2')},
        PnL_computed=False,cutoff=END))
    print('Development source census:',read(JOB/'gold-dev-census.json')['counts'],
          'missing endpoint hours',len(missing),flush=True)


def admit_endpoints():
    from index_tick_review import decode,minute_ohlc
    packet=read(JOB/'gold-endpoint-source/result.json')
    if sorted(r['at'] for r in packet['hours'])!=read(JOB/'gold-dev-census.json')['missing']:
        raise ValueError('endpoint_census_changed')
    minutes,_=source_views(ROOT/'gold-continuous-B2-20261113-v1/source-cache',
        ROOT/'xauusd-h1-stage0-20261113/source-correction-v1.json',end_msc=END)
    manifest=read(JOB/'gold-dev-manifest.json');proof=[];bad=[]
    target=JOB/'endpoint-binaries';target.mkdir(exist_ok=False)
    for r in packet['hours']:
        at=r['at']
        if not START<=at<END or digest(r['rawPath'])!=r['sha256']:
            raise ValueError('endpoint_raw_binding')
        ticks=decode(read(r['rawPath']),start_msc=at,end_msc=at+HOUR)
        bars=minute_ohlc(ticks);compared=0;missing=[]
        for m,pair in bars.items():
            actual=[pair['bid'][k] for k in ('open','high','low','close')]
            if m in minutes:
                compared+=1
                if actual!=minutes[m]:bad.append(dict(at=m,original=minutes[m],observed=actual))
        for m in range(at,at+HOUR,60000):
            if m in minutes and m not in bars:missing.append(m)
        if missing:raise ValueError('new_endpoint_tick_path_incomplete')
        a=np.empty(len(ticks),dtype=DTYPE)
        a['t']=ticks.timestamps;a['b']=ticks.bid_units;a['a']=ticks.ask_units
        p=target/f'{at}.ticks';a.tofile(p)
        manifest[str(at)]=dict(path=str(p),sha256=digest(p),records=len(a))
        proof.append(dict(at=at,raw_sha256=r['sha256'],binary_sha256=digest(p),compared=compared))
    write_json(JOB/'endpoint-source-review.json',dict(hours=proof,mismatches=bad))
    if bad:raise ValueError('endpoint_M1_mismatch_before_PnL')
    write_json(JOB/'gold-dev-manifest-v2.json',manifest)


class EURHours:
    """Only actual paired hourly opening quotes, never intrabar execution."""
    def __init__(self,quotes,sources):
        self.quotes=quotes;self.sources=sources;self.requests=[];self.resolved={}
    def endpoint(self,at):
        if not START<=at<END:raise ValueError('EUR_development_only')
        r=self.quotes.get(at//HOUR*HOUR)
        if r and 0<=r[0]-at<=60000:return r
        if at in self.resolved:return self.resolved[at]
        # The hour cache cannot price half-hour holiday/Friday exits. Seek the
        # admitted raw year by date, read timestamps only until the requested
        # quote; never substitute an hour opening or a post-break quote.
        from eurusd_b0_source import seek_day,units
        d=datetime.fromtimestamp(at/1000,timezone.utc)
        source=next(s for s in self.sources if s['first_day']<=d.strftime('%Y%m%d')<=s['last_day'])
        target=d.strftime('%Y%m%d %H:%M:%S.')+f'{at%1000:03d}'
        self.requests.append(dict(at=at,source_sha256=source['sha256']))
        write_json(JOB/'eur-endpoint-census.json',dict(requests=self.requests,
            purpose='missing paired quote at frozen endpoint',no_new_hypothesis=True,cutoff=END))
        result=None
        with Path(source['path']).open('rb') as f:
            f.readline();seek_day(f,d.strftime('%Y%m%d'))
            for line in f:
                timepart=line[:21].decode('ascii')
                if timepart<target:continue
                if timepart[:8]>'20231231':break
                sec=datetime.strptime(timepart,'%Y%m%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
                actual=int(sec.timestamp()*1000)
                if actual-at>60000:break
                parts=line.decode('ascii').strip().split(',')
                result=[actual,units(parts[1]),units(parts[2]),None];break
        self.resolved[at]=result
        write_json(JOB/'eur-exact-endpoints.json',self.resolved)
        return result


def eur_dev():
    import hashlib
    from decimal import Decimal
    from trading_workspace_v2.forex_coarse_input import CoarseHour
    cfg=read(ROOT/'eurusd-b0-20261113/config-attempt-1.json')
    hours=[];quotes={};proof=[]
    for year in (2021,2022,2023):
        src=next(s for s in cfg['sources'] if s['first_day'].startswith(str(year)))
        if year<2023:
            metadata=read(ROOT/f'eurusd-observed-history-v2/{year}/attempt-1/result.json')['hourly_cache']
            path=Path(metadata['path'])
            if digest(path)!=metadata['sha256']:raise ValueError('coarse_parent_changed')
        else:
            path=ROOT/'historical-hours/coarse-hours-f281d454fd4040fa5a3a3cf92c447720db19d78c7c7c9b26da94e2e111c53ab3.json'
        p=read(path);payload=p['payload'];binding=payload['binding']
        canonical=json.dumps(payload,sort_keys=True,separators=(',',':'),ensure_ascii=False).encode()
        if hashlib.sha256(canonical).hexdigest()!=p['payload_sha256']:
            raise ValueError('coarse_payload_checksum')
        if binding['sha256']!=src['sha256'] or not binding['last_day']<='20231231':
            raise ValueError('EUR_coarse_scope')
        if digest(src['path'])!=src['sha256']:raise ValueError('EUR_raw_changed')
        native=[CoarseHour.model_validate(r) for r in payload['hours']]
        # Existing full-session Bid bar minute counts enforce completeness.
        bars=read(ROOT/f"eurusd-b0-20261113/prepared-v1/{src['first_day']}/bars.json")['h1']
        admitted={r[0]:r for r in bars}
        mismatches=[]
        for h in native:
            at=h.mid.timestamp*1000
            if at<stamp('2021-11-01'):continue
            b=[int(v*100000) for v in h.bid]
            if at in admitted and admitted[at][1:5]!=b:mismatches.append(at)
            if at in admitted:hours.append(admitted[at])
            if START<=at<END:
                quotes[at]=[h.first_time_msc,b[0],int(h.ask[0]*100000),h.first_sequence]
        if mismatches:raise ValueError('EUR_Bid_H1_raw_parity')
        proof.append(dict(year=year,coarse_path=str(path),sha256=digest(path),raw_sha256=src['sha256'],
            historical_binding=binding,rows=len(native),bid_bar_mismatches=mismatches))
    write_json(JOB/'eur-dev-source-review.json',proof)
    s=signals(hours,eur=True);write_json(JOB/'eur-dev-signals.json',s)
    return s,EURHours(quotes,[s for s in cfg['sources'] if s['last_day']<='20231231'])


if __name__=='__main__':
    prepare_dev()
