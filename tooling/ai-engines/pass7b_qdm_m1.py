"""Admit bounded QDM tick exports and build lossless-per-minute quote envelopes."""

from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pyarrow as pa
import pyarrow.compute as pc
import pyarrow.csv as csv
import pyarrow.parquet as pq

import pass5_usdjpy_tokyo as base

PROTOCOL = 'f2bbf3b3c41a0e960b8778bbf91e7f42670d1af1'
SYMBOL = 'USDJPY_PASS7B_QUARANTINE'
HEADER = ['DateTime', 'Bid', 'Ask', 'Volume']
MINUTE_MS = 60_000
DAY_MINUTES = 1440
COLUMNS = ['minute', 'number_ticks', 'bo', 'bh', 'bl', 'bc', 'ao', 'ah', 'al', 'ac',
           'mo2', 'mh2', 'ml2', 'mc2']


def year_limits(year):
    if year not in base.YEAR:
        raise ValueError('Year outside registered Development')
    return tuple(int(datetime(y,1,1,tzinfo=timezone.utc).timestamp())*1000 for y in (year,year+1))


def batches(path, prices=False):
    types = {'DateTime': pa.string(), 'Bid':pa.float64(), 'Ask':pa.float64()}
    with path.open('rb') as stream:
        if stream.readline().strip().decode('utf-8-sig').split(',') != HEADER:
            raise ValueError('Unexpected QDM tick header')
    return csv.open_csv(path, read_options=csv.ReadOptions(block_size=16*1024*1024),
                        convert_options=csv.ConvertOptions(
                            include_columns=list(types) if prices else ['DateTime'],column_types=types))


def timestamp_ms(column, year, previous=None):
    lower, upper = year_limits(year)
    valid = pc.match_substring_regex(column,r'^[0-9]{8} [0-9]{2}:[0-9]{2}:[0-9]{2}(\.[0-9]{3})?$')
    if valid.null_count or not pc.all(valid).as_py():
        raise ValueError('Unregistered QDM tick clock layout')
    clock = pc.utf8_slice_codeunits(column,0,17)
    seconds = pc.cast(pc.strptime(clock,format='%Y%m%d %H:%M:%S',unit='s'),pa.int64()).to_numpy()
    tail = pc.utf8_slice_codeunits(column,18)
    fraction = pc.cast(pc.if_else(pc.equal(tail,''),'0',tail),pa.int64()).to_numpy()
    ms = seconds*1000 + fraction
    if len(ms) and (ms[0] < lower or ms[-1] >= upper or
                    (previous is not None and ms[0] < previous) or np.any(np.diff(ms) < 0)):
        raise ValueError('QDM tick clock outside UTC year or rows out of order')
    return ms


def preflight(path, year):
    count=0
    first=last=None
    for batch in batches(path):
        clock=timestamp_ms(batch.column(0),year,last)
        if len(clock):
            first = int(clock[0]) if first is None else first
            last = int(clock[-1])
            count += len(clock)
    if count==0:
        raise ValueError('No observations in emitted QDM CSV')
    if last >= base.STOP*1000:
        raise ValueError('QDM source crossed locked holdout')
    return dict(year=year,rows=count,first_ms=first,last_ms=last,
                sha256=base.sha(path),bytes=path.stat().st_size,rows_at_or_after_holdout=0)


def grid(array):
    raw=array.to_numpy()*1000
    values=np.rint(raw)
    if (not np.isfinite(raw).all() or np.any(raw<=0) or np.any(abs(raw-values)>1e-6)
            or np.any(values>=1_000_000)):
        raise ValueError('Unexpected USDJPY price grid')
    return values.astype(np.int32)


def minute_rows(minutes, bid, ask):
    if not len(minutes):
        return np.empty((0,len(COLUMNS)),dtype=np.int64)
    starts=np.r_[0,np.flatnonzero(minutes[1:]!=minutes[:-1])+1]
    ends=np.r_[starts[1:],len(minutes)]-1
    out=[minutes[starts],ends-starts+1]
    for stream in (bid,ask,bid+ask):
        out.extend((stream[starts],np.maximum.reduceat(stream,starts),
                    np.minimum.reduceat(stream,starts),stream[ends]))
    return np.column_stack(out)


def spread_stats(counts):
    items=sorted(counts.items())
    n=sum(counts.values())
    if not n:
        return dict(n=0,median_pips=None,p95_pips=None)
    cumulative=np.cumsum([v for _,v in items])
    quantile=lambda p:items[int(np.searchsorted(cumulative,int(np.ceil(p*n))))][0]/10
    return dict(n=n,median_pips=quantile(.5),p95_pips=quantile(.95))


def london_minutes(year):
    lo,hi=year_limits(year)
    days=range(lo//1000,hi//1000,base.DAY)
    return np.array([(int(datetime(d.year,d.month,d.day,8,tzinfo=base.LONDON).timestamp())-at)//60
        for at in days for d in [base.date(at)]],dtype=np.int16)


def aggregate(path, year, admission):
    if base.sha(path)!=admission['sha256']:
        raise ValueError('QDM CSV drift after clock-only admission')
    previous=None
    count=0
    result=[]
    hist={s:Counter() for s in ('Tokyo','London')}
    carry=(np.empty(0,dtype=np.int64),np.empty(0,dtype=np.int32),np.empty(0,dtype=np.int32))
    london=london_minutes(year)
    start_day=year_limits(year)[0]//(MINUTE_MS*DAY_MINUTES)
    for batch in batches(path,prices=True):
        clock=timestamp_ms(batch.column(0),year,previous)
        if not len(clock):
            continue
        previous=int(clock[-1])
        minute=clock//MINUTE_MS
        bid,ask=(grid(batch.column(i)) for i in (1,2))
        if np.any(ask<bid):
            raise ValueError('Crossed Bid/Ask in QDM CSV')
        count+=len(clock)
        minute_local=minute%DAY_MINUTES
        london_open=london[minute//DAY_MINUTES-start_day]
        for name, mask in [('Tokyo',minute_local<180),
                           ('London',(minute_local>=london_open)&(minute_local<london_open+240))]:
            price,count_by=np.unique((ask-bid)[mask],return_counts=True)
            hist[name].update({int(k):int(v) for k,v in zip(price,count_by)})
        minute,bid,ask=(np.concatenate((old,new)) for old,new in zip(carry,(minute,bid,ask)))
        split=minute.searchsorted(minute[-1])
        if split:
            result.append(minute_rows(minute[:split],bid[:split],ask[:split]))
        carry=(minute[split:],bid[split:],ask[split:])
    result.append(minute_rows(*carry))
    rows=np.concatenate(result)
    if (count!=admission['rows'] or previous!=admission['last_ms']
            or int(rows[:,1].sum())!=count or np.any(np.diff(rows[:,0])<=0)):
        raise ValueError('M1 aggregation reconciliation failed')
    return rows, hist


def native_export_path(job, receipt):
    year=receipt['year']
    year_limits(year)
    path=(job/receipt['path']).resolve()
    folder=(job/'export'/str(year)).resolve()
    argv=receipt['argv']
    required = {'-data','action=export',f'symbols={SYMBOL}','timeframe=TICK','timezone=UTC',
                f'datefrom={year}.01.01',f'dateto={year}.12.31',
                f'outputdir={folder.as_posix()}','format=Generic tick format (comma delimited)'}
    if len(argv)!=len(required) or set(argv)!=required or path.parent!=folder or path.suffix!='.csv':
        raise ValueError('Unbound or unbounded QDM export')
    if path.stat().st_size!=receipt['bytes']:
        raise ValueError('QDM export bytes drift')
    return path


def build(job, out):
    receipt_path=job/'QDM_EXPORT_RECEIPT.json'
    src=base.read(receipt_path)
    if (src['status'],src['protocol_commit'],src['qdm_cli_version'],src['raw_symbol']) != (
            'DEVELOPMENT_EXPORTS_READY',PROTOCOL,'125.2692',SYMBOL):
        raise ValueError('QDM export receipt has wrong source binding')
    if [r['year'] for r in src['exported_development']]!=list(base.YEAR):
        raise ValueError('Missing or duplicate QDM exports')
    out.mkdir(exist_ok=False)
    manifest=dict(schema='pass7b-qdm-usdjpy-m1-v1',protocol_commit=PROTOCOL,
                  export_receipt_sha256=base.sha(receipt_path), raw_quarantine=SYMBOL,
                  holdout_exclusive_ms=base.STOP*1000, years={})
    total_hist={s:Counter() for s in ('Tokyo','London')}
    for r in src['exported_development']:
        year=r['year']
        path=native_export_path(job,r)
        admitted=preflight(path,year)
        base.write(out/f'{year}-clock-admission.json',admitted)
        bars,hist=aggregate(path,year,admitted)
        for name,c in hist.items():
            total_hist[name].update(c)
        parquet=out/f'USDJPY-M1-BIDASK-{year}.parquet'
        table=pa.table({k:bars[:,i] for i,k in enumerate(COLUMNS)})
        pq.write_table(table,parquet,compression='zstd')
        manifest['years'][str(year)]={**admitted,'parquet':parquet.name,
            'parquet_sha256':base.sha(parquet),'minutes':len(bars),
            'first_minute':int(bars[0,0]),'last_minute':int(bars[-1,0]),
            'spread':{k:spread_stats(v) for k,v in hist.items()}}
        print(year,'ticks',admitted['rows'],'minutes',len(bars),flush=True)
    manifest['spread']={k:spread_stats(v) for k,v in total_hist.items()}
    base.write(out/'manifest.json',manifest)
    return manifest
