"""Reconcile the sealed Bot Lab example inputs without running strategy rules."""

from collections import Counter, defaultdict
from dataclasses import replace
from hashlib import sha256
import json
from pathlib import Path
import sys

import pyarrow.parquet as pq

from bot_live_auditor import audit, cash_attribution, leakage
from quant_core.ftmo_track_replay import STOP, check_lock
from quant_core.live_trade_log import normalize
from quant_core.native_paths import read_bounded

ROOT=Path(__file__).resolve().parents[2]
SWING_PIN='0d9d87ef808613b6b8f35b0412ef4dde428ed7379cad532f881884c28fc41e41'
PARENT_PIN='be77daf84d9d73671e8423804e711f30d348917740b041c7968acc1d508ebf52'
START=1514764800
VIEWS=('EQUAL_RISK','SWING_TREND_D1','SWING_CARRY_TREND_D1','SWING_INDEX_DIP_D1')
BASE_END=1704067200


def digest(path):
    with path.open('rb') as stream:
        from hashlib import file_digest
        return file_digest(stream,'sha256').hexdigest()


def bound(folder, name, pin):
    manifest=folder/'manifest.json'
    if digest(manifest)!=pin:
        raise ValueError('SEALED_JOB_MANIFEST_DRIFT')
    record=json.loads(manifest.read_bytes())['files'][name]
    file=folder/name
    if file.stat().st_size!=record['bytes'] or digest(file)!=record['sha256']:
        raise ValueError('SEALED_JOB_FILE_DRIFT')
    return file


def raw_summary(by_year, gate):
    parts=defaultdict(float)
    sample=0
    net_positive=0
    for row in by_year.values():
        contributions=row['pnl_R'] if 'pnl_R' in row else row['totals_R']
        sample+=row['n'] if 'n' in row else row['count']
        net_positive+=contributions['net']>0
        for k,val in contributions.items():
            parts[k]+=val
    return dict(gate=gate, net_positive_years=net_positive, observed_fixed_endpoints=sample,
                gross_R=parts['gross'], net_R=parts['net'],
                execution_R=sum(parts[x] for x in ('spread','commission','slippage')),swap_R=parts['swap'],
                per_year_net_R={y:(r['pnl_R'] if 'pnl_R' in r else r['totals_R'])['net'] for y,r in by_year.items()})


def attribution(ledger):
    net={k:ledger[k] for k in ('gross','swap')}
    net.update({k:-ledger[k] for k in ('spread','commission','slippage')})
    if abs(sum(net.values())-ledger['net'])>1e-8:
        raise ValueError('SEALED_COST_ATTRIBUTION_DRIFT')
    return cash_attribution(net)


def sealed_report(private):
    check_lock()
    swing=private/'swing-10k-20261120'
    parent=private/'bottleneck2-asymmetric-pivot-20261119'
    tape=bound(swing,'WIN_DIAGNOSIS.parquet',SWING_PIN)
    wins=json.loads(bound(swing,'WIN_DIAGNOSIS.json',SWING_PIN).read_bytes())
    screen=json.loads(bound(swing,'SWING_SCREEN.json',SWING_PIN).read_bytes())
    pivot=json.loads(bound(parent,'SCREEN.json',PARENT_PIN).read_bytes())
    keys={view:f'{view}|10000|SWING' for view in VIEWS}
    keys.update(USDJPY_ASYM_B='USDJPY_de62a92', BASE_GUARD='BASE_GUARD_DEV_2018_2023')
    rows=pq.read_table(tape,filters=[('cohort','in',list(keys.values()))]).to_pylist()
    groups=defaultdict(list)
    for r in rows:
        limit=BASE_END if r['cohort']==keys['BASE_GUARD'] else STOP//1000
        if not START<=r['decision']<=r['known_at_entry']['known_at']<=r['entry']<=r['exit']<limit:
            raise ValueError('SEALED_TAPE_TIME_FENCE')
        groups[r['cohort']].append(r)
    output={}
    p=pivot['cases']['ASYM_B']['Stress-Real']['views']['USDJPY']
    for title,key in keys.items():
        all_rows=groups[key]
        reference=wins['tables'][key]['ALL']
        if len(all_rows)!=reference['trades'] or abs(sum(r['contribution_R'] for r in all_rows)-reference['net_R'])>1e-7:
            raise ValueError('SEALED_TAPE_COUNT_OR_NET_DRIFT')
        raw,paired,components,net_rate=None,None,None,None
        if title in VIEWS:
            v=screen['views'][title]
            b=v['books']['10000']
            m=b['SWING']['metrics']['ALL']
            raw=raw_summary(v['raw']['by_year'],v['raw']['pass_gate'])
            paired=b['paired']['ALL'] | {'comparison_net_R_per_year':b['FRIDAY_OPEN']['metrics']['ALL']['net_R_per_year'],
                                        'basis':'SAME_INTENT_SAME_LOT_SWING_MINUS_FRIDAY_D1_OPEN'}
            components=m['pnl_R']
            net_rate=m['net_R_per_year']
        elif title=='USDJPY_ASYM_B':
            m=p['book']['10000']['metrics']['ALL']
            raw=raw_summary(p['stage0']['by_year'],p['stage0']['gate'])
            components=m['attribution_R']
            net_rate=m['net_R_per_year']
        else:
            net_rate=reference['net_R']/6
        records=[r['post_entry'] for r in all_rows]
        breakdown=leakage(records,raw=raw,paired=paired)
        breakdown.update(total_portfolio_contribution_R=reference['net_R'],contribution_R_per_year=net_rate,
                         outcome_basis='TRADE_NATIVE_R_FOR_EXCURSIONS_VS_SIZED_R_FOR_CONTRIBUTION',
                         path_quality=dict(sorted((k,sum(r['path_quality']==k for r in records)) for k in
                                                  {r['path_quality'] for r in records})),
                         label_distribution=reference['distribution'], cost_components_R=components,
                         loss_attribution=attribution(components) if components else None)
        output[title]=breakdown
    return dict(swing_manifest_sha256=SWING_PIN,parent_manifest_sha256=PARENT_PIN,
                winner_parquet_sha256=digest(tape),cohorts=output,records=len(rows),new_strategy_runs=0)


def example_report():
    directory=ROOT/'education/real-example/For those who ever need'
    files=sorted(directory.glob('*Performance*.csv'))
    unsuffixed=[p for p in files if not p.stem.endswith('_all')]
    if len(files)!=2 or len(unsuffixed)!=1:
        raise ValueError('PERFORMANCE_SOURCE_SET_CHANGED')
    source=unsuffixed[0]
    raw=read_bounded(source,16*1024*1024)
    audit_result=audit(raw,'.csv')
    rows,_=normalize(raw,'.csv')
    other=next(p for p in files if p!=source)
    other_raw=read_bounded(other,16*1024*1024)
    other_rows,_=normalize(other_raw,'.csv')
    if Counter(replace(t,row=0) for t in rows)!=Counter(replace(t,row=0) for t in other_rows) or len(rows)!=len(other_rows):
        raise ValueError('PERFORMANCE_EXPORTS_DIFFER')
    declared={'WIN':1,'LOSS':-1,'BE':0}
    checks=[t for t in rows if t.outcome in declared and t.reported_r is not None]
    audit_result['observed']['journal_outcome_vs_R_disagreements']=sum(
        (int(t.reported_r>0)-int(t.reported_r<0))!=declared[t.outcome] for t in checks)
    return dict(audit=audit_result,canonical_input=source.relative_to(ROOT).as_posix(),
                duplicate_input=other.relative_to(ROOT).as_posix(),duplicate_sha256=sha256(other_raw).hexdigest(),
                deduplication='TWO_EXPORTS_SAME_NORMALIZED_MULTISET_ONE_COUNT')


def run(private,output):
    output.parent.mkdir(parents=True,exist_ok=True)
    result=dict(schema='BotLabDevelopmentAuditEvidence-v1',sealed_development=sealed_report(private),
                recorded_journal=example_report(),holdout_market_prices_opened=False,order_send_count=0)
    with output.open('x',encoding='utf-8',newline='\n') as stream:
        json.dump(result,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')
    print(f"Sealed rows={result['sealed_development']['records']}; journal rows={result['recorded_journal']['audit']['normalization']['accepted']}")


if __name__=='__main__':
    run(*map(Path,sys.argv[1:]))
