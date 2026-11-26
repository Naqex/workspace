"""One registered 1.30/.70/.70 Dev-only lot-sized SL-active quote-path screen."""
import json,subprocess,time
import numpy as np
from prop_v24_common import *
from prop_v15_accounts import exact_quantity
from prop_v14_accounts import trade_money,VALUE
from quant_core.research_fast_fail import development_gate,content_hash

WEIGHTS={'F5':1.30,'F3':.70,'F4':.70}

def prepare(trades,readers):
    times=[];prices=[];indices=[];starts=[];ends=[];cursor=0
    for i,t in enumerate(trades):
        q=readers[t['asset']].points(t['entry_msc'],t['exit_msc'])
        times.append(np.r_[q['t'],t['exit_msc']]);prices.append(np.r_[q['b' if t['side']=='BUY' else 'a'],t['exit_price_units']])
        n=len(times[-1]);indices.append(np.full(n,i,dtype='int32'));starts.append(cursor);cursor+=n;ends.append(cursor-1)
    at=np.concatenate(times);order=np.argsort(at,kind='stable');unique,groups=np.unique(at[order],return_index=True)
    return dict(t=at,price=np.concatenate(prices).astype(float),i=np.concatenate(indices),starts=np.array(starts),
        ends=np.array(ends),order=order,unique=unique,groups=groups)

def measure(trades,p,weights):
    q=np.array([exact_quantity(t,150*weights.get(t['id'].split('|')[1][:2],1)) for t in trades]);i=p['i'];quant=q[i]
    entry=np.array([t['entry_price_units'] for t in trades]);sign=np.array([1 if t['side']=='BUY' else -1 for t in trades])
    gold=np.array([t['asset']=='XAUUSD' for t in trades])[i];value=np.array([VALUE[t['asset']] for t in trades])[i]
    raw=sign[i]*(p['price']-entry[i])*quant*value
    gross=np.sign(raw)*((abs(raw)+5)//10*10)/1000
    en_fee=np.where(gold,np.floor(entry[i]*quant*.0000007+.5+1e-9)/100,np.floor(quant*.035*100+.5+1e-9)/100)
    ex_fee=np.where(gold,np.floor(p['price']*quant*.0000007+.5+1e-9)/100,np.floor(quant*.035*100+.5+1e-9)/100)
    vals=(gross-en_fee-ex_fee-np.where(gold,quant*.4,quant*.02))/150
    final=np.array([trade_money(t,int(size),'SYM_FLAT',150)['net_R'] for t,size in zip(trades,q)])
    vals[p['ends']]=final;delta=np.diff(np.r_[0.,vals]);delta[p['starts']]=vals[p['starts']]
    eq=np.cumsum(np.add.reduceat(delta[p['order']],p['groups']))
    if abs(eq[-1]-final.sum())>1e-7:raise ValueError('WEIGHTED_PATH_CASH_CONSERVATION')
    peaks=np.maximum.accumulate(np.r_[0.,eq])[1:];days,ix=np.unique(p['unique']//86400000,return_index=True)
    anchors=np.r_[0.,eq[ix[1:]-1]];daily=float(np.max(anchors-np.minimum.reduceat(eq,ix)))
    risk=np.array([-trade_money(dict(t,exit_msc=t['entry_msc'],exit_price_units=t['stop_units'],reason='SL'),int(n),'SYM_FLAT',150)['net_usd'] for t,n in zip(trades,q)])
    rt=np.array([t['entry_msc'] for t in trades]+[t['exit_msc'] for t in trades]);rd=np.r_[risk,-risk]
    ro=np.argsort(rt,kind='stable');_,ri=np.unique(rt[ro],return_index=True)
    maxrisk=float(np.cumsum(np.add.reduceat(rd[ro],ri)).max())
    years=np.array([int(np.datetime64(t['entry_msc'],'ms').astype('datetime64[Y]').astype(int))+1970 for t in trades])
    return dict(net_R=float(final.sum()),equity_R_DD=float((peaks-eq).max()),static_R_loss=max(0.,float(-eq.min())),
        worst_daily_R=daily,max_open_risk_USD=maxrisk,cluster_R=[float(final[(years>=lo)&(years<=hi)].sum()) for lo,hi in ((2018,2020),(2021,2023))],
        development_years=[2018,2023],trades=len(trades),SL_active_validated=True,signal_contract_status='CAUSAL_FROZEN')

def run():
    pins={str(p):sha(p) for p in (PROTOCOL,Path(__file__),Path('tooling/ai-engines/quant_core/research_fast_fail.py'))}
    save('P80-registration.json',dict(weights=WEIGHTS,commit=subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        code_pins=pins,Development=[FIRST,DEV_END],trials=1,no_later_prices_for_selection=True))
    from prop_v21_forensics import Context
    from prop_v15_evidence import bars_for
    from prop_v14_paths import M1ScenarioQuotes
    started=time.perf_counter();bars={a:bars_for(a,True) for a in ('XAUUSD','EURUSD')};results=[]
    for tag,names in (('OLHC','OPEN_LOW_HIGH_CLOSE'),('OHLC','OPEN_HIGH_LOW_CLOSE')):
        path=V19/f'Dev-{tag}-PRIMARY-trades.json';trades=read(path)
        assert all(FIRST<=t['entry_msc']<=t['exit_msc']<DEV_END for t in trades)
        readers={a:M1ScenarioQuotes(b,names,FIRST,DEV_END) for a,b in bars.items()};p=prepare(trades,readers)
        ready=time.perf_counter();base=measure(trades,p,{});candidate=measure(trades,p,WEIGHTS)
        if abs(base['net_R']-23.8524)>1e-7 or abs(base['equity_R_DD']-12.206533333333333)>1e-7:raise ValueError('BASELINE_M1_PARITY_REQUIRED')
        decision=development_gate(candidate,base,inputs_sha256=sha(path),recipe_sha256=content_hash(WEIGHTS))
        results.append(dict(order=tag,decision=decision,prepared_gate_seconds=time.perf_counter()-ready,
            max_account_open_risk_cap_USD=1000,account_reserve_unchanged=True))
    passing=all(r['decision']['passed'] for r in results)
    save('P80-Development-decision.json',dict(passed=passing,cases=results,weights=WEIGHTS,trials=1,
        end_to_end_seconds=time.perf_counter()-started,prices_2024_2026_opened=False,
        new_historical_children=0,new_bootstrap_children=0,incumbent='V16/V19 BASE_GUARD',prop_qualified=False))
    print(json.dumps(dict(passed=passing,cases=results)))

if __name__=='__main__':run()
