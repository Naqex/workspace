"""V2 diagnostics and exactly two registered carry-aware A policies."""
from datetime import datetime,timezone
import numpy as np

from prop_campaign_source import (ROOT,JOB as V1,PARENT,START,END,FINAL,HOUR,DAY,
    Prices,read,write_json,stamp,digest)
from prop_campaign_exits import CELLS,net_per_oz,costs
from prop_campaign_accounts import Account,replay,annual,CAPITAL

JOB=ROOT/'prop-atlas-v2-20261114'


def event(stage,**fields):
    r=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**fields)
    write_json(JOB/'status.json',r)
    with (JOB/'events.jsonl').open('a',encoding='utf-8') as f:
        import json
        f.write(json.dumps(r)+'\n')
    print(r,flush=True)


class PeakDiagnostic(Account):
    def __init__(self,start,risk_map,cell):
        super().__init__(start,FINAL,cell)
        self.risk_map=risk_map;self.requested=150
        self.high_equity=self.high_balance=self.high_flat=CAPITAL
    def risk(self,equity):
        return self.requested
    def action(self,kind,at,i,trades,quote,mult=0):
        if kind=='entry':self.requested=self.risk_map[i]
        super().action(kind,at,i,trades,quote,mult)
    def metrics(self,low,high,dd=0):
        self.high_equity=max(self.high_equity,high)
        self.high_balance=max(self.high_balance,self.balance)
        if not self.active:self.high_flat=max(self.high_flat,self.balance)
        super().metrics(low,high,dd)


def phase0():
    alltrades=read(V1/'frozen-system-ASYM_FLAT-trades.json')
    cases=[c for c in read(V1/'lifecycle-ASYM_FLAT.json') if c['phase_passes']]
    if len(cases)!=13:raise ValueError('thirteen_parent_accounts')
    reader=Prices(read(PARENT/'attempt-2/binary-manifest.json'),FINAL)
    rows=[]
    for c in cases:
        accepted=[a for a in c['accepted'] if a['phase']==2]
        trades=[alltrades[a['trade']] for a in accepted]
        risk_map={i:a['risk_usd'] for i,a in enumerate(accepted)}
        d=PeakDiagnostic(c['phase_passes'][0]['at']+1,risk_map,'ASYM_FLAT')
        got=replay(trades,reader,[d])[0]
        rows.append(dict(start_msc=c['start_msc'],step1_pass=c['phase_passes'][0]['at'],
            phase2_entries=len(accepted),max_equity_profit_pct=(d.high_equity-CAPITAL)/500000,
            max_realized_profit_pct=(d.high_balance-CAPITAL)/500000,
            max_flat_profit_pct=(d.high_flat-CAPITAL)/500000,
            shortfall_from_best_equity_pct=5-(d.high_equity-CAPITAL)/500000,
            shortfall_from_best_flat_pct=5-(d.high_flat-CAPITAL)/500000,
            shortfall_from_best_flat_reference175_R=(52500000-d.high_flat)/175000,
            terminal_balance_usd=got['balance_usd'],first_breach=c['first_breach'],
            status='TIME_CENSORED_AT_DATASET_END' if c['first_breach'] is None else 'PROP_VIOLATED'))
        event('phase0_peak',completed=len(rows),total=13)
    side=[]
    for year in (2022,2023,2024):
        for direction in ('BUY','SELL'):
            ts=[t for t in alltrades if t['side']==direction and t['day'].startswith(str(year))]
            cs=[costs(t,'ASYM_FLAT') for t in ts]
            side.append(dict(year=year,side=direction,trades=len(ts),
                gross_R=sum(c['gross_usd'] for c in cs)/150,
                commission_R=sum(c['commission_usd'] for c in cs)/150,
                slippage_R=sum(c['slippage_usd'] for c in cs)/150,
                swap_R=sum(c['swap_usd'] for c in cs)/150,
                financing_free_net_R=sum(c['net_usd']-c['swap_usd'] for c in cs)/150,
                net_R=sum(c['net_usd'] for c in cs)/150))
    write_json(JOB/'phase0-diagnostic.json',dict(accounts=rows,annual_side=side,
        source_read='existing PR79 results/path only; explicitly includes2024',
        no_new_strategy_selection=True,prices2025_2026_read=False))


def carry_path(t,policy,cell,reader):
    """Only shorten a parent path; no changed entry/initial SL."""
    t=dict(t);buy=t['side']=='BUY'
    t['exit_policy']=policy
    if not buy:return t
    when=None
    if policy=='CA1':when=t['entry_msc']//DAY*DAY+20*HOUR+HOUR//2
    elif policy=='CA2':
        d=datetime.fromtimestamp(t['entry_msc']/1000,timezone.utc)
        days=(2-d.weekday())%7
        when=t['entry_msc']//DAY*DAY+days*DAY+20*HOUR+HOUR//2
    else:raise ValueError('unregistered_carry_policy')
    if not t['entry_msc']<when<t['exit_msc']:return t
    q=reader.endpoint(when)
    if q is None:
        t['exit_policy_unknown']='NO_FRESH_2030_QUOTE';return t
    if (q[0],q[3])>=(t['exit_msc'],t['exit_quote_index']):return t
    close=policy=='CA1'
    if policy=='CA2':
        a,_=reader.path(t['entry_msc'],q[0])
        value=float(net_per_oz(t,a,cell)[-1])
        close=value<1.5*t['natural_sl_usd_per_oz']
        t['carry_decision_net_price_R']=value/t['natural_sl_usd_per_oz']
    if close:
        t.update(exit_msc=q[0],exit_quote_index=q[3],exit_price_units=q[1],
            reason=policy+'_2030_FLAT',endpoint_wait_ms=0)
    t['costs']={cell:costs(t,cell)}
    return t


def phase1():
    reader=Prices(read(V1/'gold-dev-manifest-v2.json'))
    baseline=read(V1/'phase1-metrics.json');measurements={};decisions=[]
    for policy in ('CA1','CA2'):
        failures=[];gains=[];dds=[]
        for cell in CELLS:
            old=read(V1/f'paths-{cell}-A0.json')
            ts=[carry_path(t,policy,cell,reader) for t in old]
            write_json(JOB/f'core-{cell}-{policy}-dev.json',ts)
            unknown=[t['signal_id'] for t in ts if t.get('exit_policy_unknown')]
            if unknown:
                measurements[cell+':'+policy]=dict(annual=None,unknown=unknown)
                failures.append(cell+':DATA_PATH_UNKNOWN');continue
            rows=annual(ts,reader,cell)
            measurements[cell+':'+policy]=dict(annual=rows,unknown=[])
            for a,b in zip(baseline[cell+':A0']['annual'],rows):
                oldratio=a['net_R']/a['max_equity_R_DD']
                newratio=b['net_R']/b['max_equity_R_DD']
                gains.append(newratio/oldratio);dds.append(b['max_equity_R_DD'])
                if b['net_R']<=a['net_R']:failures.append(f"{cell}:{a['year']}:NET_NOT_IMPROVED")
                if newratio<=oldratio:failures.append(f"{cell}:{a['year']}:RATIO_NOT_IMPROVED")
            event('phase1_annual',policy=policy,cell=cell)
        decisions.append(dict(policy=policy,eligible=not failures,reasons=failures,
            worst_gain=min(gains) if gains else None,worst_dd=max(dds) if dds else None))
    eligible=sorted([d for d in decisions if d['eligible']],
        key=lambda r:(-r['worst_gain'],r['worst_dd'],r['policy']))
    chosen=eligible[0]['policy'] if eligible else 'A0'
    write_json(JOB/'core-decision.json',dict(selected=chosen,decisions=decisions,
        selection_cutoff=END,prices2024_for_selection=False,
        utc=datetime.now(timezone.utc).isoformat()))
    write_json(JOB/'core-comparison.json',measurements)
    for cell in CELLS:
        ts=read(V1/f'paths-{cell}-A0.json') if chosen=='A0' else read(JOB/f'core-{cell}-{chosen}-dev.json')
        write_json(JOB/f'core-{cell}-dev.json',ts)
    event('phase1_complete',selected=chosen)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('stage',choices=('phase0','phase1'))
    args=p.parse_args()
    globals()[args.stage]()
