"""Separate scalar accounting and grid/source admission reconciliation."""
from decimal import Decimal
import hashlib
import json
import numpy as np
from prop_v22_common import *


def run():
    from prop_v15_accounts import exact_quantity
    from independent_ledger_auditor import v14_parts
    frozen=read(JOB/'Development-decision.json')
    for p,digest in frozen['code_pins'].items():assert sha(p)==digest
    for p,digest in frozen['bindings'].items():assert sha(JOB/p)==digest
    anatomy=unpack('Full-entry-anatomy');lookup={r['trade_key']:r for r in anatomy}
    dev=unpack('Dev-entry-snapshots');d={r['trade_key']:r for r in dev}
    for key,r in d.items():assert r['day_range_ATR']==lookup[key]['day_range_ATR']
    parent=unpack('Dev-OLHC-forensics',V21);top=sorted(parent,key=lambda r:-r['net_R'])[:10]
    checks=[]
    for g in read(JOB/'Dev-gate-results.json')['cases']:
        for case in g['cases']:
            records=read(V19/f"Dev-{case['order']}-PRIMARY-trades.json")
            retained=[];net=Decimal(0);removed_win=Decimal(0);removed_loss=Decimal(0)
            for t in records:
                key=f"{t['id']}@{t['entry_msc']}";r=d[key]
                limit=.9 if g['gate']=='G_L3_A' else frozen['thresholds'].get(t['id'])
                keep=r['family']=='F5' or r['day_range_ATR'] is not None and limit is not None and r['day_range_ATR']<=limit
                cash=Decimal(v14_parts(t,exact_quantity(t,150),'SYM_FLAT')['net'])/150000
                if keep:retained.append(key);net+=cash
                elif cash>0:removed_win+=cash
                else:removed_loss+=cash
            assert len(retained)==case['trades'] and abs(float(net)-case['candidate']['net_R'])<1e-10
            assert abs(float(removed_win)-case['rejected_winner_R'])<1e-10
            assert abs(float(removed_loss)-case['rejected_loser_R'])<1e-10
            assert sum(r['trade_key'] in retained for r in top)==case['top10_retained']==10
            assert not case['passed']
            checks.append(dict(gate=g['gate'],order=case['order'],retained=len(retained),net_R=float(net),passed=True))
    # Check each H1 quote endpoint and money leg without using money()/screen().
    from prop_v12_campaign import load_bars
    index=read(ROOT/'ensemble-and-storage-v11-20261115/source-admission-v11.json')
    h1checks=[];missing=[]
    b=read(JOB/'H1-behavioral-results.json')
    for asset in ('GBPUSD','AUDUSD'):
        bars=load_bars(asset,index)
        for r in [r for r in b['rows'] if r['asset']==asset]:
            name=asset+'-'+r['recipe'].replace(':','_')+'-H1-raw';m=unpack(name)
            assert all(int(t)%3600000==0 for t in m['deadline'])
            assert all(t%86400000<=20*3600000 for t in m['deadline'])
            if asset=='GBPUSD':
                name0=asset+'-'+r['recipe'].replace(':','_')+'-raw'
                old=unpack(name0,V21/'behavioral-corrected-v2')
                for field in ('at','side','stop','natural','entry_price'):assert m[field]==old[field]
            n=0
            for i,ok in enumerate(m['ok']):
                if not ok:
                    missing.append(dict(asset=asset,recipe=r['recipe'],decision=m['at'][i],deadline=m['deadline'][i],next_observed=m['exit_at'][i]));continue
                assert m['entry_at'][i]==m['at'][i] and m['exit_at'][i]==m['deadline'][i]
                assert m['entry_at'][i]//86400000==m['exit_at'][i]//86400000
                j=int(bars['t'].searchsorted(m['deadline'][i]));assert int(bars['t'][j])==m['deadline'][i]
                px=int(bars['bo' if m['side'][i]==1 else 'ao'][j]);assert px==m['exit_price'][i]
                expected=Decimal(m['side'][i])*(Decimal(px)-Decimal(m['entry_price'][i]))/100000-Decimal('.00009')
                assert abs(float(expected)-m['net'][i])<1e-12;n+=1
            assert n==r['priced'];h1checks.append(dict(asset=asset,recipe=r['recipe'],priced=n,raw=r['raw'],same_signals=asset=='GBPUSD'))
    # These22 cells must be byte-equivalent JSON values apart from provenance flag.
    parent={ (r['asset'],r['recipe']):r for r in read('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json')['behavioral']['rows']}
    reused=0
    for r in b['rows']:
        if r['reused_from_V21']:
            assert {k:v for k,v in r.items() if k!='reused_from_V21'}==parent[r['asset'],r['recipe']];reused+=1
    assert reused==22
    import zstandard as zstd
    manifests=[]
    for p in JOB.rglob('*-manifest.json'):
        m=read(p);raw=zstd.ZstdDecompressor().decompress((p.parent/m['file']).read_bytes())
        assert hashlib.sha256(raw).hexdigest()==m['original_sha256'] and sha(p.parent/m['file'])==m['compressed_sha256']
        assert len(raw)==m['original_bytes'];manifests.append(p.name)
    save('independent-audit.json',dict(passed=True,gates=checks,H1=h1checks,H1_missing=missing,
        reused_M1_cells=reused,compressed_tables=len(manifests),anatomy_rows=len(anatomy),Dev_snapshot_parity=len(dev),
        baseline_report_sha256=sha('planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json'),
        inherited_behavioral_sha256=sha('planning/research/TRADE-FORENSICS-BEHAVIORAL-V21-RESULTS-20261117.json'),
        same_author_and_feed=True,independent_human_review=False))
    event('V22_audit_complete',H1_cases=len(h1checks),H1_missing=len(missing),tables=len(manifests))


if __name__=='__main__':run()
