"""Winner diagnosis on bound Development ledgers. Entry features stay separate."""
from collections import Counter, defaultdict
from math import isfinite
from pathlib import Path
from statistics import median
import json
import sys

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

from evidence_compaction import EvidenceStore
from native_ftmo_asym_forensics import LOCK_PIN, PARENT_PIN
from native_ftmo_asym_pivot import BASE_END, BASE_PIN, macro_signals, wall_to_utc
from native_ftmo_monfri_screen import Market, bars, date, simulate
from native_ftmo_monfri_seal import AUDIT, FRAMES, ROOT, START, STOP, read, sha, write
from native_ftmo_swing import CLUSTERS, WIN_STANDARD

LABELS = ('CUTOFF_TRUNCATED_WIN', 'CARRY_ASSISTED_WIN', 'TAIL_TREND_RUNNER',
          'CLEAN_STRUCTURAL_WIN', 'LUCKY_NOISE_WIN')
UNKNOWN = 'UNCLASSIFIED_MISSING_EVIDENCE'
ENTRY_FIELDS = frozenset(('known_at','trend','volatility','distance','session','carry_historical',
                          'carry_snapshot_proxy','weekday'))
BASE_FILES = {
    'Dev-pack/OLHC-PRIMARY-blocks.json':'a107e20704617154483e72e7c649dc251c199c96228946d55b63606ffa1d1c83',
    'Dev-pack/OLHC-PRIMARY-quotes.npy':'af1235474e401319bcf0c306609af36c6078c48da9a4fd3d16f7005c23a91e57',
}


def classify(post):
    net = post['net_R']
    if net <= 0:
        return None
    if post['calendar_exit']:
        alt = post['paired_net_R']
        if alt is None:
            return UNKNOWN
        if alt-net>=.50 and alt>=1.25*net:
            return LABELS[0]
    swap = post['swap_R']
    if swap is None:
        return UNKNOWN
    if swap>=.10 and (swap>=.25*net or net-swap<=0):
        return LABELS[1]
    mfe,mae,held = (post[k] for k in ('mfe_R','mae_R','holding_hours'))
    if mfe is None or mae is None or held is None:
        return UNKNOWN
    capture = net/mfe if mfe>0 else 0.
    if mfe>=3 and net>=2 and held>=72 and capture>=.40:
        return LABELS[2]
    if mfe>=1 and net>=.50 and mae<=.75 and capture>=.50:
        return LABELS[3]
    return LABELS[4]


def dev_scope(decision, entry, exit, max_time=STOP):
    if not START <= decision <= entry <= exit < max_time:
        raise ValueError('trade outside Development')


def classify_trade(key, decision, entry, exit, asset, features, net, swap, mfe, mae, peak,
                   pnl_pool_R, *, source, calendar_exit=False, pair_net=None, nominal_pair_extra=None,
                   quality='MODELED'):
    dev_scope(decision,entry,exit)
    known = features.get('known_at')
    if not isinstance(known,int) or not decision <= known <= entry:
        raise ValueError('entry feature not known at entry')
    if features.keys() - ENTRY_FIELDS:
        raise ValueError('post-entry field in entry features')
    if any(x is not None and not isfinite(x) for x in (net,swap,mfe,mae,peak,pair_net)):
        raise ValueError('non-finite path input')
    if peak is not None and not 0<=peak<=(exit-entry)/3600:
        raise ValueError('peak outside held path')
    post = dict(net_R=net,swap_R=swap,mfe_R=mfe,mae_R=mae,time_to_peak_hours=peak,
                capture_efficiency=net/mfe if net>0 and mfe and mfe>0 else None,
                swap_share=swap/net if swap is not None and net>0 else None,
                holding_hours=(exit-entry)/3600,calendar_exit=calendar_exit,paired_net_R=pair_net,
                path_quality=quality)
    return dict(key=key,asset=asset,decision=decision,entry=entry,exit=exit,year=date(entry).year,
                source=source,known_at_entry=features,post_entry=post,contribution_R=pnl_pool_R,
                paired_extra_contribution_R=nominal_pair_extra,label=classify(post))


def trade_swing(trade):
    if not trade['closed']:
        return None
    decision,entry,exit_ = (int(wall_to_utc(trade[k]).timestamp()) for k in ('decision','entry','exit'))
    risk = trade['risk_per_lot']
    net = trade['net']/risk
    nominal = trade['budget']*.005
    pool_R = trade['net']*trade['lots']/nominal
    extra = trade['paired_extra_net_R']
    pair_net = net+extra*nominal/(risk*trade['lots']) if extra is not None else None
    features = trade['features'] | {'known_at':decision}
    return classify_trade(trade['key'],decision,entry,exit_,trade['asset'],features,
        net,trade['swap']/risk,trade['mfe_R_actual_risk'],trade['mae_R_actual_risk'],trade['time_to_peak_hours'],pool_R,
        source='D1_MODELED_OPEN_CLOSE_STOP',calendar_exit=trade['reason']=='FRIDAY_CUTOFF',
        pair_net=pair_net,nominal_pair_extra=extra,quality='D1_MODELED_WIDE_GAP' if trade['held_bar_open_gap_flags'] else 'D1_MODELED')


def verify_parent(private, raw_rows):
    asset = 'USDJPY'
    sealed = private/'bottleneck2-monfri-20261119'
    if sha(sealed/'manifest.json')!=PARENT_PIN or sha(sealed/'NATIVE_FTMO_HOLDOUT_LOCK.json')!=LOCK_PIN:
        raise ValueError('parent seal drift')
    lock=read(sealed/'NATIVE_FTMO_HOLDOUT_LOCK.json')
    if sha(AUDIT)!=lock['audit_sha256']:
        raise ValueError('parent cost drift')
    feed={}
    for f in FRAMES:
        p=sealed/'development'/f'{asset}-{f}.parquet'
        if sha(p)!=lock['series'][asset][f]['development_sha256']:
            raise ValueError('parent USDJPY partition drift')
        feed[f]=bars(p,FRAMES[f])
    m=Market(asset,feed['H1'],read(AUDIT)['symbols'][asset],feed['H1'])
    plans,levels=macro_signals(asset,feed,m)
    intents={(i.frame,i.at,i.side):i for i,c in plans if c}
    for t in raw_rows:
        decision,entry,end=(int(wall_to_utc(t[k]).timestamp()) for k in ('decision','entry','exit'))
        dev_scope(decision,entry,end)
        intent=intents[(t['frame'],t['decision'],t['side'])]
        replay,_=simulate(m,intent,levels,'Stress-Real','Mon-Fri')
        if replay is None or any(replay[k]!=t[k] for k in ('entry','exit','reason','net','swap','initial_risk')):
            raise ValueError('parent USDJPY path replay drift')
        risk=t['initial_risk']
        marks=replay['path']
        when,top=max(marks,key=lambda p:(p[1],-p[0]))
        mfe=max(0.,top)/risk
        mae=max(0.,-min(pnl for _,pnl in marks))/risk
        yield classify_trade(f"USDJPY|{t['frame']}|{decision}|{t['side']}",decision,entry,end,asset,
            {'weekday':date(entry).strftime('%a'),'session':t['frame'],'carry_historical':'UNKNOWN','known_at':decision},
            t['net']/risk,t['swap']/risk,mfe,mae,(when-t['entry'])/3600 if mfe>0 else None,
            t['net']*t['lots']/50,source='PARENT_ASYM_B_H1_MARKS',calendar_exit=t['reason']=='CUTOFF',
            quality='H1_MODELED')


def base_guard(private):
    path=private/'challenge-discovery4-20261108/execution-v1/asymmetric-recovery-and-mt5-v19-20261116'
    tape=path/'Dev-OLHC-PRIMARY-trades.json'
    if sha(tape)!=BASE_PIN:
        raise ValueError('BASE_GUARD tape drift')
    store=EvidenceStore(path)
    for item,pin in BASE_FILES.items():
        if store.entries[item]['sha256']!=pin:
            raise ValueError('BASE_GUARD Development path pin drift')
    block_file,quote_file=(Path(k) for k in BASE_FILES)
    pack=json.loads(store.read_bytes(block_file))
    prices=store.numpy(quote_file)
    if pack['quote_sha256']!=BASE_FILES[str(quote_file.as_posix())] or not pack['no_swap']:
        raise ValueError('BASE_GUARD block contract mismatch')
    times=prices['t']
    if np.min(times)<START*1000 or np.max(times)>=BASE_END*1000 or np.any(np.diff(times)<0):
        raise ValueError('BASE_GUARD quotes outside Development or unsorted')
    ids={(t['id'],t['source_event'],t['entry_msc'],t['exit_msc']) for b in pack['blocks'] for t in b['trades']}
    for t in read(tape):
        a,b,c=(t[k] for k in ('decision_msc','entry_msc','exit_msc'))
        if not START*1000<=a<=b<=c<BASE_END*1000:
            raise ValueError('BASE_GUARD trade outside Development')
        if t['censored']:
            continue
        if (t['id'],t['source_event'],b,c) not in ids:
            raise ValueError('BASE_GUARD missing source block')
        side=1 if t['side']=='BUY' else -1
        field=('b' if side==1 else 'a')+('0' if t['asset']=='XAUUSD' else '1')
        left=int(times.searchsorted(b,side='right'))
        right=int(times.searchsorted(c,side='left'))
        ref=t['reference']['SYM']
        risk=t['natural']
        if abs(side*(t['exit_price_units']-t['entry_price_units'])/t['scale']-ref['gross'])>1e-7:
            raise ValueError('BASE_GUARD exit cannot reconcile')
        mfe,mae,peak=None,None,None
        if not t['source_uncertain'] and t['exit_price_units']>0:
            # This existing synthetic quote pack uses a fixed fee proxy. Use the original
            # settled fee on all post-entry marks and append exact recorded exit PnL.
            fees=ref['commission']+ref['slippage']
            marks=(side*(prices[field][left:right].astype('float64')-t['entry_price_units'])/t['scale']-fees)/risk
            values=np.r_[-fees/risk,marks,ref['net_R']]
            j=int(np.argmax(values))
            times_in_trade=np.r_[b,times[left:right],c]
            mfe=max(0.,float(values[j]))
            mae=max(0.,float(-min(values)))
            peak=(int(times_in_trade[j])-b)//1000/3600 if mfe>0 else None
        yield classify_trade(f"{t['id']}|{t['source_event']}",a//1000,b//1000,c//1000,t['asset'],
            {'weekday':date(b//1000).strftime('%a'),'session':'UTC_HOUR_'+date(b//1000).strftime('%H'),
             'known_at':a//1000,'carry_historical':'UNKNOWN'},ref['net_R'],ref['funding']/risk,mfe,mae,peak,
            ref['net_R'],source='V19_OLHC_PRIMARY_SYM_DEV',quality='SOURCE_UNCERTAIN' if t['source_uncertain'] else 'M1_SCENARIO_PROXY')


def breakdown(records):
    winners = [r for r in records if r['label']]
    pnl = sum(r['contribution_R'] for r in records)
    pool = sum(r['contribution_R'] for r in winners)
    dist={}
    for label in (*LABELS,UNKNOWN):
        group=[r for r in winners if r['label']==label]
        gain=sum(r['contribution_R'] for r in group)
        def med(field):
            values=[r['post_entry'][field] for r in group if r['post_entry'][field] is not None]
            return median(values) if values else None
        dist[label]={'count':len(group),'contribution_R':gain,'profit_share':gain/pool if pool else None,
                     'median_MAE_R':med('mae_R'),'median_MFE_R':med('mfe_R'),'median_capture':med('capture_efficiency'),
                     'median_time_to_peak_hours':med('time_to_peak_hours'),'median_swap_share':med('swap_share')}
    pairing=[r for r in winners if r['post_entry']['calendar_exit'] and r['post_entry']['paired_net_R'] is not None]
    truncated=[r for r in pairing if r['label']==LABELS[0]]
    missed=sum(r['paired_extra_contribution_R'] for r in truncated)
    alt_pool=sum(max(0.,r['contribution_R']+r['paired_extra_contribution_R']) for r in pairing)
    order=sorted((r['contribution_R'] for r in winners),reverse=True)
    tops={f'top{n}':{'profit_share':sum(order[:n])/pool if pool else None,'net_R_excluding':pnl-sum(order[:n])}
          for n in (2,5,10)}
    rates={}
    entry=defaultdict(lambda:defaultdict(list))
    for t in records:
        for k,v in t['known_at_entry'].items():
            if k!='known_at':
                entry[k][v].append(t)
    for k,groups in entry.items():
        rates[k]={v:{'n':len(g),'winrate':sum(r['contribution_R']>0 for r in g)/len(g),
                     'lossrate':sum(r['contribution_R']<0 for r in g)/len(g),
                     'mean_net_R':sum(r['contribution_R'] for r in g)/len(g)} for v,g in groups.items()}
    coverage=1-dist[UNKNOWN]['count']/len(winners) if winners else None
    return dict(trades=len(records),winner_count=len(winners),loss_count=sum(r['contribution_R']<0 for r in records),
                positive_R_pool=pool,coverage=coverage,net_R=pnl,distribution=dist,top=tops,entry_base_rates=rates,
                cutoff=dict(clamped_winners=sum(r['post_entry']['calendar_exit'] for r in winners),pairs=len(pairing),
                            truncated_win_count=len(truncated),missed_R=missed,paired_counterfactual_positive_R=alt_pool,
                            lost_share=missed/alt_pool if alt_pool else None),
                fragility=dict(lucky_share_gt_30=bool((dist[LABELS[4]]['profit_share'] or 0)>.30),
                               coverage_lt_90=bool(coverage is not None and coverage<.90),
                               top2_gt_50=bool((tops['top2']['profit_share'] or 0)>.50),
                               ex_top5_nonpositive=tops['top5']['net_R_excluding']<=0))


def run(private, job):
    if sha(ROOT/'planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json')!=LOCK_PIN:
        raise ValueError('holdout pin drift')
    analysis=read(job/'SWING_SCREEN.json')
    if analysis['holdout_prices_opened'] or analysis['input_sha256'][WIN_STANDARD.name]!=sha(WIN_STANDARD):
        raise ValueError('screen/label binding mismatch')
    ledger=job/'SWING_TRADE_LEDGER.parquet'
    rows=defaultdict(list)
    for t in pq.read_table(ledger).to_pylist():
        o=trade_swing(t)
        if o:
            # Preserve the server-wall entry year used by the screen.
            o['year']=t['year']
            rows[f"{t['view']}|{t['budget']}|{t['policy']}"].append(o)
    prior=private/'bottleneck2-asymmetric-pivot-20261119'
    manifest=read(prior/'manifest.json')
    parent_ledger=prior/'PIVOT_TRADES.parquet'
    if manifest['holdout_lock_sha256']!=LOCK_PIN or sha(parent_ledger)!=manifest['files'][parent_ledger.name]['sha256']:
        raise ValueError('USDJPY ledger drift')
    parent_rows=pq.read_table(parent_ledger,filters=[('family','=','ASYM_B'),('asset','=','USDJPY'),
        ('scenario','=','Stress-Real'),('book','=',10000)]).to_pylist()
    rows['USDJPY_de62a92']=list(verify_parent(private,parent_rows))
    rows['BASE_GUARD_DEV_2018_2023']=list(base_guard(private))
    tables={}
    flat=[]
    for k,v in rows.items():
        tables[k]={p:breakdown([t for t in v if t['year'] in y]) for p,y in CLUSTERS.items()}
        flat.extend(t | {'cohort':k} for t in v)
    pq.write_table(pa.Table.from_pylist(flat),job/'WIN_DIAGNOSIS.parquet',compression='zstd')
    write(job/'WIN_DIAGNOSIS.json',dict(schema='selective-win-dev-v1',holdout_sha256=LOCK_PIN,
          swing_ledger_sha256=sha(ledger),parent_ledger_sha256=sha(parent_ledger),base_guard_tape_sha256=BASE_PIN,
          base_guard_path_sha256=BASE_FILES,standard_sha256=sha(WIN_STANDARD),tables=tables))
    print(f'Winner diagnosis: {len(flat)} closed records across {len(tables)} cohorts')


if __name__ == '__main__':
    run(*map(Path,sys.argv[1:]))
