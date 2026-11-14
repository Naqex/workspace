"""Separate cash-posted-swap oracle and Fraction cost bridges.

This is computational parity by the same implementer, not a second reviewer.
The production engine accrues open funding in floating; this oracle posts it
to cash and independently reconstructs realized-balance daily anchors.
"""
from collections import defaultdict
from datetime import date,datetime,timedelta,timezone
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

from prop_campaign_source import JOB,PARENT,START,FINAL,HOUR,Prices,read,write_json,digest
from xau_h1_execution_review import money_parts,funding
from xau_a_validation import native_terminal

CAP=50000000
PRAGUE=ZoneInfo('Europe/Prague')


def oracle(trades,accepted,passes,payouts,reader,start,end,cell):
    actions=defaultdict(list);parts={};sizes={};funding_open={}
    for a in accepted:
        i=a['trade'];t=trades[i];q=a['ounces']
        sizes[i]=q;parts[i]=money_parts(dict(t,ounces=q),cell)
        actions[(t['entry_msc'],t['entry_quote_index'])].append(('entry',i,0))
        actions[(t['exit_msc'],t['exit_quote_index'])].append(('exit',i,0))
        for at,m in funding(t['entry_msc'],t['exit_msc']):
            actions[(at,-1)].append(('swap',i,m))
    for p in passes:
        i=next(i for i in sizes if trades[i]['exit_msc']==p['at'])
        actions[(p['at'],trades[i]['exit_quote_index'])].append(('pass',None,0))
    for p in payouts:
        exact=[i for i in sizes if trades[i]['exit_msc']==p['at']]
        ordinal=trades[exact[0]]['exit_quote_index'] if exact else -1
        actions[(p['at'],ordinal)].append(('reward',None,int(round(p['gross_removed_usd']*1000))))
    d=date(2022,1,1)
    while d<date(2025,1,1):
        at=int(datetime(d.year,d.month,d.day,tzinfo=PRAGUE).timestamp()*1000)
        if start<=at<end:actions[(at,-1)].append(('reset',None,0))
        d+=timedelta(days=1)
    keys=sorted(k for k in actions if start<=k[0]<end);cursor=0;open_ids=set()
    cash=anchor=peak=CAP;dd=daily=static=0;last=None;breach=None;marks=0
    max_equity=max_balance=max_flat=CAP
    bridge=[];qbuy=qsell=basis=0
    def measure(values,times):
        nonlocal peak,dd,daily,static,breach,marks,max_equity
        if len(values)==0 or breach:return
        eq=values+cash
        bad=np.flatnonzero(eq<max(anchor-2500000,45000000))
        if len(bad):
            n=int(bad[0]);breach=dict(at=int(times[n]),equity=int(eq[n]))
            eq=eq[:n+1]
        running=np.maximum.accumulate(np.r_[peak,eq])
        max_equity=max(max_equity,int(eq.max()))
        dd=max(dd,int((running[1:]-eq).max()));peak=int(running[-1])
        daily=max(daily,anchor-int(eq.min()));static=max(static,CAP-int(eq.min()))
        marks+=len(eq)
    def point(clock=None):
        nonlocal max_balance,max_flat
        realized=cash+sum(sizes[k]*200-funding_open[k] for k in open_ids)
        max_balance=max(max_balance,realized)
        if not open_ids:max_flat=max(max_flat,cash)
        if last is not None:
            v=qbuy*last[1]-qsell*last[2]-basis
            measure(np.array([v],dtype='int64'),np.array([last[0] if clock is None else clock],dtype='int64'))
    for hour in range(start//HOUR*HOUR,end,HOUR):
        if breach:break
        a=reader.hour(hour) if hour in reader.files else np.empty(0,dtype=[('t','<i8'),('b','<i4'),('a','<i4')])
        j=0
        def segment(lo,hi):
            nonlocal last
            if hi<=lo:return
            b=a[lo:hi]
            if open_ids:
                v=qbuy*b['b'].astype('int64')-qsell*b['a'].astype('int64')-basis
                measure(v,b['t'])
            last=[int(b['t'][-1]),int(b['b'][-1]),int(b['a'][-1])]
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            at,ordinal=keys[cursor];cut=int(a['t'].searchsorted(at)) if ordinal<0 else ordinal
            segment(j,cut)
            if breach:break
            if ordinal>=0:
                if cut>=len(a) or a['t'][cut]!=at:raise ValueError('oracle_quote_ordinal')
                last=[int(a['t'][cut]),int(a['b'][cut]),int(a['a'][cut])];point()
            for kind,i,m in sorted(actions[keys[cursor]],key=lambda r:
                    {'reset':0,'swap':1,'exit':2,'pass':3,'reward':4,'entry':5}[r[0]]):
                if kind=='reset':
                    anchor=cash+sum(sizes[k]*200-funding_open[k] for k in open_ids)
                elif kind=='pass':
                    if open_ids:raise ValueError('oracle_pass_with_open_position')
                    bridge.append(dict(at=at,kind='phase_reset',removed=cash-CAP))
                    cash=anchor=peak=CAP
                elif kind=='reward':
                    if open_ids or m<20000 or cash-CAP!=m:raise ValueError('oracle_invalid_reward')
                    cash-=m;anchor=peak=CAP
                else:
                    t=trades[i];q=sizes[i];p=parts[i];s=1 if t['side']=='BUY' else -1
                    if kind=='entry':
                        qbuy+=q if s==1 else 0;qsell+=q if s==-1 else 0
                        basis+=s*q*t['entry_price_units'];open_ids.add(i);funding_open[i]=0
                        cash-=(p['commission'][0]+p['slip'][0])*10
                    elif kind=='exit':
                        qbuy-=q if s==1 else 0;qsell-=q if s==-1 else 0
                        basis-=s*q*t['entry_price_units'];open_ids.remove(i);funding_open.pop(i)
                        cash+=(p['gross']-p['commission'][1]-p['slip'][1])*10
                    else:
                        charge=dict(p['swaps'])[at]*10;cash+=charge;funding_open[i]+=charge
                point(at)
                if breach:break
            j=cut;cursor+=1
            if breach:break
        if breach:break
        segment(j,len(a))
    return dict(dd=dd,daily=daily,static=static,breach=breach,cash=cash,
        marks=marks,phase_bridges=bridge,open_ids=sorted(open_ids),
        max_equity=max_equity,max_realized_balance=max_balance,max_flat_balance=max_flat)


def run():
    freeze=read(JOB/'composition-freeze.json')
    if freeze['selected_exit']!='A0' or freeze['selected_sleeves']:
        raise ValueError('review_scope_requires_selected_A0')
    original=read(PARENT/'attempt-2/trades.json')
    native_checks=bridges=0;results=[];start=datetime.now(timezone.utc)
    p=Prices(read(PARENT/'attempt-2/binary-manifest.json'),FINAL)
    for cell in ('SYM_FLAT','ASYM_FLAT'):
        trades=read(JOB/f'frozen-system-{cell}-trades.json')
        for t,old in zip(trades,original):
            for k in ('entry_msc','exit_msc','entry_price_units','exit_price_units','stop_units',
                      'entry_quote_index','exit_quote_index','deadline_msc','reason'):
                if t[k]!=old[k]:raise ValueError('parent_308_path_parity:'+k)
            for risk in (125,150,175,250):
                from prop_campaign_exits import costs
                q=risk*1000//abs(t['entry_price_units']-t['stop_units'])
                v=money_parts(dict(t,ounces=q),cell);got=costs(t,cell,risk)
                for key,value in (('net_usd',v['net']),('gross_usd',v['gross']),
                    ('commission_usd',sum(v['commission'])),('slippage_usd',sum(v['slip'])),
                    ('swap_usd',sum(n for _,n in v['swaps']))):
                    if int(round(got[key]*100))!=value:raise ValueError('Fraction_cost_bridge')
                bridges+=1
        cases=read(JOB/f'lifecycle-{cell}.json')
        for n,c in enumerate(cases):
            # Independent cost ledger: every accepted lot must match its frozen
            # initial monetary budget; never infer quantity by scaling $150 PnL.
            for a in c['accepted']:
                t=trades[a['trade']]
                if a['ounces']!=a['risk_usd']*1000//abs(t['entry_price_units']-t['stop_units']):
                    raise ValueError('oracle_quantity')
            for event in c['phase_passes']:
                days={datetime.fromtimestamp(a['at']/1000,timezone.utc).astimezone(PRAGUE).date().isoformat()
                      for a in c['accepted'] if a['phase']==event['phase'] and a['at']<=event['at']}
                native_terminal(event['phase'],int(round(event['balance_usd']*1000)),0,CAP,
                    days,event['at'],c['start_msc'],0,
                    'phase_pass' if event['phase']==1 else 'complete_pass')
                native_checks+=1
            v=oracle(trades,c['accepted'],c['phase_passes'],c['payouts'],p,
                c['start_msc'],c['end_msc'],cell)
            for k,field in (('dd','peak_dd_pct'),('daily','worst_daily_loss_pct'),('static','static_loss_pct')):
                if abs(v[k]-c[field]*500000)>1e-6:
                    raise ValueError('independent_equity_parity:'+str((cell,n,k,v[k],c[field]*500000)))
            if bool(v['breach'])!=bool(c['first_breach']):raise ValueError('oracle_breach')
            if not v['breach'] and abs(v['cash']/1000-c['balance_usd'])>1e-6:
                raise ValueError('oracle_cash')
            if v['breach'] and v['breach']['at']!=c['first_breach']['at']:
                raise ValueError('oracle_first_breach_time')
            results.append(dict(cell=cell,start_msc=c['start_msc'],oracle=v,
                production_balance_usd=c['balance_usd'],passed=True))
            if n%6==0:print('independent account oracle',cell,n,flush=True)
    write_json(JOB/'computational-parity.json',dict(status='PASSED_SAME_IMPLEMENTER_SEPARATE_FORMULATION',
        rational_cost_bridges=bridges,parent_paths_checked=len(original)*2,
        lifecycle_accounts=len(results),native_terminal_checks=native_checks,accounts=results,
        source_price_end_exclusive=FINAL,prices2025_2026_read=False,
        elapsed_seconds=(datetime.now(timezone.utc)-start).total_seconds(),
        reviewer_sha256=digest(__file__)))


if __name__=='__main__':run()
