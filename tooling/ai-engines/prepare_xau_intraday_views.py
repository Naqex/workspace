"""Bind observed XAU Bid/Ask hour rows to the admitted signal M1 before PnL."""
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import struct
import time

from index_tick_review import decode
from xau_intraday_source import source_views
from eurusd_b0_source import digest, write_json

RECORD=struct.Struct('<qii')


def prepare(study,cache,*,signals='signal-source-v2',view='tick-view-v1',corrections=None):
    study,cache=Path(study),Path(cache)
    out=study/view;out.mkdir(exist_ok=False)
    began=time.monotonic()
    minutes,_=source_views(cache,corrections)
    source=json.loads((study/'tick-source-v1/result.json').read_bytes())
    census=json.loads((study/signals/'census.json').read_bytes())
    if sorted(r['at'] for r in source['hours'])!=census['hours']:
        raise ValueError('tick_hour_census_incomplete')
    proofs=[];counts=Counter();mismatch=[];missing=set();bar_mismatch=[]
    for n,row in enumerate(sorted(source['hours'],key=lambda r:r['at']),1):
        path=Path(row['rawPath'])
        if digest(path)!=row['sha256']:raise ValueError('tick_source_changed')
        ticks=decode(json.loads(path.read_bytes()),start_msc=row['at'],end_msc=row['at']+3600000)
        if len(ticks)!=row['records']:raise ValueError('native_tick_raw_record_census')
        binary=out/(str(row['at'])+'.ticks')
        observed={}
        with binary.open('xb') as f:
            for at,bid,ask in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units):
                minute=at//60000*60000
                if minute not in observed:observed[minute]=[bid,bid,bid,bid]
                else:
                    v=observed[minute];v[1]=max(v[1],bid);v[2]=min(v[2],bid);v[3]=bid
                bar=minutes.get(at//60000*60000)
                if bar is None:missing.add(at//60000*60000)
                elif not bar[2]<=bid<=bar[1]:
                    counts['range_mismatch_ticks']+=1
                    if len(mismatch)<20:mismatch.append(dict(at=at,bid_units=bid,bar_units=bar))
                f.write(RECORD.pack(at,bid,ask))
        for at,bar in observed.items():
            if at in minutes:
                counts['M1_OHLC_compared']+=1
                if bar==minutes[at]:counts['M1_OHLC_exact']+=1
                else:
                    counts['M1_OHLC_mismatch']+=1
                    if len(bar_mismatch)<20:bar_mismatch.append(dict(at=at,observed=bar,source=minutes[at]))
        counts['ticks']+=len(ticks)
        proofs.append(dict(at=row['at'],ticks=len(ticks),binary_sha256=digest(binary),raw_sha256=row['sha256']))
        if n%100==0:
            value=dict(stage='tick_view_prepare',hours=n,total=len(source['hours']),ticks=counts['ticks'],
                       wall_seconds=time.monotonic()-began)
            write_json(out/'status.json',value);print(json.dumps(value),flush=True)
    packet=dict(schema='XAU-A0-observed-tick-view-v1',hours=proofs,counts=dict(counts),
        source_minutes_absent_but_ticks_observed=sorted(missing),mismatch_samples=mismatch,
        M1_OHLC_mismatch_samples=bar_mismatch,
        source_result_sha256=digest(study/'tick-source-v1/result.json'),
        signal_census_sha256=digest(study/signals/'census.json'),code_sha256=digest(__file__),
        corrections_sha256=digest(corrections) if corrections else None,
        wall_seconds=time.monotonic()-began)
    write_json(out/'review.json',packet)
    if mismatch or bar_mismatch:raise ValueError('QDM_vs_observed_tick_OHLC_mismatch_requires_review_no_financial_dispatch')
    write_json(out/'seal.json',packet)
    return packet


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--study',required=True);p.add_argument('--cache',required=True)
    p.add_argument('--signals',default='signal-source-v2');p.add_argument('--view',default='tick-view-v1');p.add_argument('--corrections')
    a=p.parse_args();prepare(a.study,a.cache,signals=a.signals,view=a.view,corrections=a.corrections)
