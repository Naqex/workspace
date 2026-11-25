"""Break down the immutable Mon–Fri Development ledger without loading prices."""

from collections import defaultdict
from pathlib import Path
import sys

import pyarrow.parquet as pq

from native_ftmo_monfri_screen import FAMILIES, PARTS, POLICIES, key
from native_ftmo_monfri_seal import ASSETS, START, STOP, read, sha, write


PARENT_PIN = 'ea4a22aa4af11131e266b785a7f9dd820f12f8b1d7f1b56cfa30f8c496fd6275'
LOCK_PIN = 'f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486'


def totals(rows):
    values = {k: sum(t[k]*t['lots']/50 for t in rows) for k in PARTS}
    values['friction_R'] = sum(values[x] for x in ('spread', 'commission', 'slippage'))
    return {'trades':len(rows), **values}


def run(parent, out):
    manifest = parent/'manifest.json'
    if sha(manifest) != PARENT_PIN or sha(parent/'NATIVE_FTMO_HOLDOUT_LOCK.json') != LOCK_PIN:
        raise ValueError('parent seal changed')
    p = read(manifest)['files']
    for name in ('PORTFOLIO_TRADES.parquet','RESULTS.json'):
        if sha(parent/name) != p[name]['sha256']:
            raise ValueError('parent payload changed')
    table = pq.read_table(parent/'PORTFOLIO_TRADES.parquet', filters=[('book','=',10000),('scenario','=','Stress-Real')])
    ledger = table.to_pylist()
    if any(not START <= t['decision'] <= t['entry'] <= t['exit'] < STOP for t in ledger):
        raise ValueError('Development time fence')
    old = read(parent/'RESULTS.json')['families']
    grouped, paired, dual, standalone = {}, {}, [], {}
    for family in FAMILIES:
        sample = [t for t in ledger if t['family']==family]
        consolidated = old[family]['Stress-Real']['books']['10000']
        book = consolidated['PORTFOLIO']
        grouped[family], paired[family], standalone[family] = {}, {}, {}
        all_by_policy = {p: [t for t in sample if t['policy']==p] for p in POLICIES}
        for p, rows in all_by_policy.items():
            prior = book[p]['metrics']['ALL']
            if len(rows)!=prior['trades'] or any(abs(totals(rows)[k]-prior['attribution_R'][k])>1e-7 for k in PARTS):
                raise ValueError('parent portfolio attribution mismatch')
        for asset in ASSETS:
            by_policy = {p:[t for t in rows if t['asset']==asset] for p,rows in all_by_policy.items()}
            standalone[family][asset] = {p:consolidated[asset][p]['metrics'] for p in POLICIES}
            group = grouped[family][asset] = {}
            direction_delta = paired[family][asset] = {}
            for side in (1,-1):
                direction = 'BUY' if side==1 else 'SELL'
                slices = {p:[t for t in rows if t['side']==side] for p,rows in by_policy.items()}
                group[direction] = {p:{'ALL':totals(rows),'A':totals([t for t in rows if t['year']<=2020]),
                                       'B':totals([t for t in rows if t['year']>=2021])} for p,rows in slices.items()}
                by_key = {p:{key(t):t for t in rows} for p,rows in slices.items()}
                if any(len(by_key[p])!=len(slices[p]) for p in POLICIES):
                    raise ValueError('duplicate canonical ledger intent')
                overnight, daily = by_key['Mon-Fri'],by_key['20:30-UTC']
                common = sorted(overnight.keys() & daily.keys())
                diff = {k:sum((overnight[i][k]*overnight[i]['lots']-daily[i][k]*daily[i]['lots'])/50 for i in common) for k in PARTS}
                direction_delta[direction] = {'paired_intents':len(common), **diff}
            m = standalone[family][asset]['20:30-UTC']
            if min(m[c]['net_R_per_year'] for c in ('A','B'))>0:
                dual.append(dict(family=family,asset=asset,A_R_per_year=m['A']['net_R_per_year'],B_R_per_year=m['B']['net_R_per_year'],
                                 ALL_R_per_year=m['ALL']['net_R_per_year'],swap_R=m['ALL']['attribution_R']['swap']))
        expected = book['hold_overnight_delta']['paired_delta_R']
        for field in PARTS:
            if abs(sum(t[field] for a in paired[family].values() for t in a.values())-expected[field])>1e-7:
                raise ValueError('paired attribution does not match parent')
    write(out,dict(schema='ftmo-monfri-pivot-forensics-v1',basis='parent portfolio selected lots at 10k Stress-Real',
                   parent_manifest_sha256=PARENT_PIN, holdout_lock_sha256=LOCK_PIN, rows=len(ledger),
                   total_by_symbol_direction_exit=grouped,paired_monfri_minus_daily=paired,
                   standalone_metrics=standalone,dual_cluster_daily=dual))


if __name__=='__main__':
    run(*map(Path,sys.argv[1:]))
