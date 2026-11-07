"""Conditional block bootstrap of verified, exposed coarse closed-trade panels."""
import argparse
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import math
from pathlib import Path
import random

WEEK_MS=7*86400*1000


def quantile(values,p):
    ordered=sorted(values)
    at=(len(ordered)-1)*p
    a,b=math.floor(at),math.ceil(at)
    return ordered[a]+(ordered[b]-ordered[a])*(at-a)


def binned_trades(row,year):
    start=int(datetime(year,1,1,tzinfo=timezone.utc).timestamp())*1000
    end=int(datetime(year+1,1,1,tzinfo=timezone.utc).timestamp())*1000
    n=math.ceil((end-start)/WEEK_MS)
    if row['open_position'] is not None or Decimal(row['floating_usd'])!=0 or row['pending_entry']:
        raise ValueError('uncertainty panel requires flat annual books')
    trades=row['trades']
    if len(trades)!=row['closed_trades'] or len({t['position_id'] for t in trades})!=len(trades):
        raise ValueError('trade counts/identity mismatch')
    net=[Decimal(0) for _ in range(n)];counts=[0]*n
    for trade in trades:
        amount=Decimal(trade['net_usd'])
        if not amount.is_finite():raise ValueError('nonfinite closed net')
        bounds=trade['exit_interval_msc']
        if (len(bounds)!=2 or any(type(t)is not int for t in bounds)
                or not start<=bounds[0]<=bounds[1]<end):
            raise ValueError('trade outside annual book')
        first,last=[(t-start)//WEEK_MS for t in bounds]
        if first!=last:raise ValueError('unknown stop instant spans statistical bins')
        net[first]+=amount;counts[first]+=1
    if sum(net)!=Decimal(row['net_equity_usd']):
        raise ValueError('closed net differs from flat annual equity')
    return dict(net=[float(v) for v in net],counts=counts)


def bootstrap(panel,*,draws=10000,block=4,seed=42):
    if type(draws)is not int or draws<10 or type(block)is not int or block<1:
        raise ValueError('invalid bootstrap design')
    years=sorted(panel);keys=sorted(panel[years[0]])
    for year in years:
        series=panel[year]
        if sorted(series)!=keys:raise ValueError('missing paired cost/candidate series')
        n=len(series[keys[0]]['net'])
        if n<block:raise ValueError('shorter panel than block')
        for row in series.values():
            if len(row['net'])!=n or len(row['counts'])!=n:
                raise ValueError('unaligned series')
            if (any(not math.isfinite(v) for v in row['net'])
                    or any(type(v)is not int or v<0 for v in row['counts'])):
                raise ValueError('invalid statistical panel')
    rng=random.Random(seed);samples={key:[] for key in keys};empty={key:0 for key in keys}
    for _ in range(draws):
        profits={key:0. for key in keys};counts={key:0 for key in keys}
        for year in years:
            series=panel[year];n=len(series[keys[0]]['net']);indices=[]
            while len(indices)<n:
                at=rng.randrange(n)
                indices.extend((at+i)%n for i in range(block))
            indices=indices[:n]
            for key in keys:
                profits[key]+=sum(series[key]['net'][i] for i in indices)
                counts[key]+=sum(series[key]['counts'][i] for i in indices)
        for key in keys:
            if counts[key]:samples[key].append(profits[key]/25/counts[key])
            else:empty[key]+=1
    rows=[]
    for key in keys:
        net=sum(sum(panel[y][key]['net']) for y in years)
        count=sum(sum(panel[y][key]['counts']) for y in years)
        values=samples[key]
        rows.append(dict(series=key,closed_trades=count,mean_closed_r=net/25/count if count else None,
            conditional_bootstrap_95pct_interval_r=[quantile(values,.025),quantile(values,.975)] if values else None,
            usable_draws=len(values),zero_trade_draws=empty[key]))
    return dict(schema='forex-conditional-uncertainty-v1',rows=rows,draws=draws,block_bins=block,bin_days=7,
        seed=seed,years=years,joint_sampled_indices=True,selection_adjusted=False,
        interval_is_future_edge_or_pass_probability=False,clean_oos=False,promotion_authorized=False,
        assumptions=['closed net only, annual flat books; not a continuous portfolio',
            'circular28day blocks within each exposed year; final short bin kept',
            'long regimes/tails/simulation error and multiple-trial selection not corrected'])


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--config',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    args=p.parse_args();config=json.loads(args.config.read_bytes());panel={};pins={}
    for item in config['reports']:
        path=Path(item['path']);raw=path.read_bytes();sha=hashlib.sha256(raw).hexdigest()
        if sha!=item['sha256']:raise ValueError('statistical report pin mismatch')
        report=json.loads(raw)
        if report['schema']!='forex-coarse-screen-report-v1' or report['status']!='completed_triage_only':
            raise ValueError('unsupported coarse packet')
        year=int(report['inputs']['development']['first_day'][:4])
        if (year not in (2023,2024) or report['inputs']['development']['first_day']!=str(year)+'0101'
                or report['inputs']['development']['last_day']!=str(year)+'1231'):
            raise ValueError('scope excludes nonregistered years/holdout')
        for row in report['rows']:
            if row['candidate'] not in config['candidates']:continue
            key=row['candidate']+'::'+row['scenario']
            group=panel.setdefault(str(year),{})
            if key in group:raise ValueError('duplicate annual series')
            group[key]=binned_trades(row,year)
        pins[str(path)]=sha
    expected={candidate+'::'+cost for candidate in config['candidates'] for cost in ('reference','cost-stress')}
    if set(panel)!={'2023','2024'} or any(set(series)!=expected for series in panel.values()):
        raise ValueError('missing annual/scenario panel')
    result=bootstrap(panel)
    result.update(input_report_pins=pins,source_sha256=hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        config_sha256=hashlib.sha256(args.config.read_bytes()).hexdigest())
    with args.output.open('x',encoding='utf-8') as file:json.dump(result,file,indent=2,allow_nan=False)
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
