"""Read completed/sealed native cohorts; no simulation, tuning or broker calls."""
import argparse
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path

import review_us500_multiframe as reviewer


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def summarize(base,prefix='us500-multiframe-native-v3-review'):
    roots=[base/f'{prefix}-{y}' for y in (2022,2023,2024)]
    rows,timings,receipts=[],[],[]
    pins=None
    for year,root in zip((2022,2023,2024),roots):
        if (root/'controller.lock').exists():
            raise ValueError('cohort_still_owned')
        result=json.loads((root/'result.json').read_text(encoding='utf-8'))
        manifest=json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        if result['status']!='completed_development_screen_not_qualified' or len(result['rows'])!=57 or manifest['years']!=[year] or result['manifest_sha256']!=digest(root/'manifest.json'):
            raise ValueError('cohort_terminal_contract')
        if pins is None:
            pins=manifest['source_pins']
        elif pins!=manifest['source_pins']:
            raise ValueError('cohort_source_mismatch')
        for row in result['rows']:
            name=f'{year}-{row["candidate"]}-{row["scenario"]}'
            seal=json.loads((root/(name+'-seal.json')).read_text(encoding='utf-8'))
            if seal['result_sha256']!=digest(root/(name+'.json')) or seal['review_sha256']!=digest(root/(name+'-review.json')) or seal['manifest_sha256']!=result['manifest_sha256']:
                raise ValueError('book_durable_seal')
            book=json.loads((root/(name+'.json')).read_text(encoding='utf-8'))
            review=json.loads((root/(name+'-review.json')).read_text(encoding='utf-8'))
            if review['status']!='verified_execution_cash_only' or reviewer.metrics(book)!={k:v for k,v in row.items() if k not in ('year','candidate','config','scenario')}:
                raise ValueError('book_summary_review_binding')
            if row['year']!=year or book['config']!=row['config']:
                raise ValueError('book_identity')
            rows.append(row)
        timings+=result['timings']
        receipts.append(dict(year=year,path=str(root),result_sha256=digest(root/'result.json'),wall_seconds=result['wall_seconds'],cpu_seconds=result['cpu_seconds']))
    if len(rows)!=171 or len({(r['year'],r['candidate'],r['scenario']) for r in rows})!=171:
        raise ValueError('union_census')
    candidates=[]
    for cid in sorted({r['candidate'] for r in rows}):
        subset=[r for r in rows if r['candidate']==cid and r['scenario']!='null']
        if len(subset)!=6:
            raise ValueError('candidate_book_census')
        result=dict(id=cid,config=subset[0]['config'],scenarios={})
        for scenario in ('reference','stress'):
            books=sorted((r for r in subset if r['scenario']==scenario),key=lambda r:r['year'])
            data={}
            for side in ('BUY','SELL','combined'):
                groups=[r['sides'][side] for r in books]
                unresolved=sum(g['unresolved'] for g in groups)
                data[side]=dict(trades=sum(g['trades'] for g in groups),unresolved=unresolved,
                    net_usd=None if unresolved else str(sum((D(g['net_usd']) for g in groups),D(0))),
                    modeled_closed_net_usd=str(sum((D(g['modeled_closed_net_usd']) for g in groups),D(0))),
                    known_trades=sum(g['known_trades'] for g in groups),wins=sum(g['wins'] for g in groups),
                    years=[dict(year=b['year'],**b['sides'][side]) for b in books])
            result['scenarios'][scenario]=data
        candidates.append(result)
    nulls=[r for r in rows if r['scenario']=='null']
    if len(nulls)!=9 or any(r['sides']['combined']['trades'] or D(r['sides']['combined']['net_usd']) for r in nulls):
        raise ValueError('null_control')
    return dict(status='completed_development_screen_not_qualified',candidates=candidates,cohorts=receipts,timings=timings,
                financial_books=162,null_books=9,source_pins=pins,qualified_candidates=0,
                semantics='Annual books cold reset10000USD; sums are descriptive, not continuous account returns')


def number(value):
    return 'N/A' if value is None else f'{D(value):+.2f}'


def markdown(summary):
    lines=['# US500 M15 A/B/C — bảng đầy đủ','',
           '162 books +9 null controls. Mỗi sổ năm bắt đầu10.000USD; plannedrisk25USD/lệnh.',
           'Commission0, spread trong Bid/Ask; slip0,25/0,75point mỗi chiều. Dữ liệu proxy development, chưa challenge-qualified.',
           'Dấu* là modeledclosed khi có path unresolved; fullnet N/A. Không dùng dấu* để chứng minh lợi thế.','',
           '|ID|Lane|MA|k|2022 chuẩn|2023 chuẩn|2024 chuẩn|2022 cao|2023 cao|2024 cao|Lệnh chuẩn/cao|',
           '|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for c in summary['candidates']:
        config=c['config']
        values=[]
        for scenario in ('reference','stress'):
            for row in c['scenarios'][scenario]['combined']['years']:
                values.append(number(row['modeled_closed_net_usd'])+('*' if row['unresolved'] else ''))
        a,b=(c['scenarios'][s]['combined']['trades'] for s in ('reference','stress'))
        lines.append(f'|{c["id"]}|{config["lane"]}|{config["fast"]}/{config["slow"]}|{config["k"]}|'+ '|'.join(values)+f'|{a}/{b}|')
    lines+=['','## Tách BUY/SELL, tổng mô tả ba sổ năm','',
            '|ID|BUY chuẩn|SELL chuẩn|BUY cao|SELL cao|Unresolved chuẩn/cao|',
            '|---|---:|---:|---:|---:|---:|']
    for c in summary['candidates']:
        values=[number(c['scenarios'][s][side]['net_usd']) for s in ('reference','stress') for side in ('BUY','SELL')]
        counts=[c['scenarios'][s]['combined']['unresolved'] for s in ('reference','stress')]
        lines.append(f'|{c["id"]}|'+ '|'.join(values)+f'|{counts[0]}/{counts[1]}|')
    return '\n'.join(lines)+'\n'


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--base',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args()
    result=summarize(a.base)
    a.output.mkdir(exist_ok=False)
    (a.output/'summary.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (a.output/'TABLE.md').write_text(markdown(result),encoding='utf-8')
    print(json.dumps(dict(financial_books=162,null_books=9,candidates=len(result['candidates']),output=str(a.output))))
