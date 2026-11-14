"""A-only validation and lossless segment replay; no broker or 2025 prices."""
from bisect import bisect_left,bisect_right
from collections import defaultdict,Counter
from datetime import date,datetime,timedelta,timezone
from decimal import Decimal as D
from itertools import combinations
import json
from pathlib import Path
import time

from eurusd_b0_source import digest,write_json
from index_tick_review import decode,minute_ohlc
from xau_intraday_source import source_views
from xau_h1_execution import path_for,economics,commission,cents,funding_events
from xau_a_validation_source import START,END,HOUR,REC,Calendar,Quotes
from gold_continuous_ledger import StreamSummary
from gold_continuous_b1 import phase_spec
from trading_workspace_v2.prop_session import (money_oracle,MoneyOracleInput,calendar_oracle,
    PropProfileSnapshot,PropSessionSnapshot,ChallengeAttemptSnapshot,PhaseStateSnapshot,
    PropLifecycleEvent,evaluate_prop_lifecycle_event,TransitionIntent,apply_prop_lifecycle_command)
from zoneinfo import ZoneInfo

PRAGUE=ZoneInfo('Europe/Prague');CELLS=('SYM_FLAT','ASYM_FLAT');CAPITAL=50000000


def ms(text):return int(datetime.fromisoformat(text).replace(tzinfo=timezone.utc).timestamp()*1000)
def utc(at):return datetime.fromtimestamp(at/1000,timezone.utc)
def masks(ids):return [c for n in range(1,len(ids)+1) for c in combinations(sorted(ids),n)]
def keymask(ids):return ','.join(map(str,sorted(ids)))
def qsize(t,risk):return risk*1000//abs(t['entry_price_units']-t['stop_units'])
def fee(t,risk,entry=True):return cents(commission(t['entry_price_units'] if entry else t['exit_price_units'],qsize(t,risk)))*10
def swap(t,risk,cell,mult):return qsize(t,risk)*(-400 if cell.startswith('SYM') else -450 if t['side']=='BUY' else -50)*mult


class Events:
    def __init__(self,out):self.out=Path(out);self.start=time.monotonic();self.n=0
    def __call__(self,stage,**fields):
        if (self.out/'CANCEL').exists():raise InterruptedError('cancelled')
        if time.monotonic()-self.start>3600:raise TimeoutError('validation_deadline')
        self.n+=1;r=dict(sequence=self.n,stage=stage,elapsed_seconds=time.monotonic()-self.start,utc=datetime.now(timezone.utc).isoformat(),**fields)
        write_json(self.out/'status.json',r)
        with (self.out/'events.jsonl').open('a') as f:f.write(json.dumps(r)+'\n')
        print(json.dumps(r),flush=True)


def admit(cfg,out,event):
    source_dir=Path(cfg['source_dir']);manifest=json.loads((source_dir/'inherited-binaries.json').read_bytes())
    for r in manifest.values():
        if digest(r['path'])!=r['sha256']:raise ValueError('parent_binary_changed')
    minutes,_=source_views(cfg['cache'],source_dir/'corrections.json',end_msc=END)
    packet=json.loads(Path(cfg['tick_source']).read_bytes());new=out/'ticks';new.mkdir()
    census=json.loads((source_dir/'census.json').read_bytes())
    requested=sorted(census['hours']);received=sorted(r['at'] for r in packet['hours'])
    if received!=requested or len(set(received))!=len(received):raise ValueError('tick_census_changed')
    counts=Counter();bad=[];proof=[];expected=defaultdict(set)
    for stamp in minutes:
        if START<=stamp<END:expected[stamp//HOUR*HOUR].add(stamp)
    for i,r in enumerate(packet['hours'],1):
        at=r['at']
        if not START<=at<END:raise ValueError('2025_2026_tick_prices_closed')
        if digest(r['rawPath'])!=r['sha256']:raise ValueError('raw_tick_changed')
        ticks=decode(json.loads(Path(r['rawPath']).read_bytes()),start_msc=at,end_msc=at+HOUR)
        if len(ticks)!=r['records']:raise ValueError('tick_record_census')
        observed_minutes=minute_ohlc(ticks)
        absent=sorted(expected[at]-observed_minutes.keys());counts['M1_without_ticks']+=len(absent)
        for stamp,pair in observed_minutes.items():
            observed=[pair['bid'][k] for k in ('open','high','low','close')]
            if stamp in minutes:
                counts['M1_compared']+=1
                if observed!=minutes[stamp]:bad.append(dict(at=stamp,source=minutes[stamp],observed=observed,raw=r))
            else:counts['tick_minutes_without_M1']+=1
        path=new/f'{at}.ticks'
        with path.open('xb') as f:
            for q in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units):f.write(REC.pack(*q))
        record=dict(path=str(path),sha256=digest(path),records=len(ticks));manifest[str(at)]=record
        proof.append(dict(at=at,raw=r,binary=record,missing_M1_minutes=absent));counts['ticks']+=len(ticks)
        if i%100==0:event('source_review',hours=i,total=len(packet['hours']))
    write_json(out/'source-review.json',dict(counts=dict(counts),mismatches=bad,hours=proof))
    if bad:raise ValueError('new_source_OHLC_mismatch_before_PnL')
    if counts['M1_without_ticks']:raise ValueError('new_source_path_incomplete_before_PnL')
    write_json(out/'binary-manifest.json',manifest)
    return Quotes(manifest),dict(counts)


def make_paths(cfg,out,quotes,event):
    source=Path(cfg['source_dir']);signals=json.loads((source/'signals.json').read_bytes());cal=Calendar(cfg['calendar'])
    trades=[];rejected=[]
    for i,row in enumerate(signals):
        at=row['decision_msc']
        if not cal.allowed(at):rejected.append(dict(signal=row,reason='TARGET_SESSION_CLOSED'));continue
        quote,index=quotes.endpoint(at)
        if quote is None:raise ValueError('entry_quote_missing')
        r=path_for(dict(row,entry_quote=list(quote)),quotes,False,deadline_rule=cal.deadline)
        r['decision_msc']=at;r['entry_quote_index']=index
        if r['exit_msc'] is None:raise ValueError('calendar_path_still_unresolved:'+r['signal_id'])
        if r['endpoint_wait_ms']>60000 or r['exit_msc']>=END:raise ValueError('exit_outside_frozen_price_window')
        r['sizing_costs']={}
        for risk in (150,200):
            t=dict(r,risk_usd=risk,ounces=qsize(r,risk))
            r['sizing_costs'][str(risk)]={c:economics(t,c) for c in CELLS}
        trades.append(r)
        if i%25==0:event('path_measurement',signals=i,total=len(signals))
    write_json(out/'trades.json',trades);write_json(out/'session-rejections.json',rejected)
    return trades


def build_ledger(trades,quotes,out,event):
    actions=defaultdict(list)
    for i,t in enumerate(trades):
        actions[(t['entry_msc'],t['entry_quote_index'])].append(('entry',i,0))
        actions[(t['exit_msc'],t['exit_quote_index'])].append(('exit',i,0))
        for e in funding_events(t['entry_msc'],t['exit_msc']):actions[(e['at'],-1)].append(('swap',i,e['multiplier']))
    d=date(2022,1,1)
    while d<date(2025,1,1):
        at=int(datetime(d.year,d.month,d.day,tzinfo=PRAGUE).timestamp()*1000)
        if START<=at<END:actions[(at,-1)].append(('reset',None,0))
        d+=timedelta(days=1)
    keys=sorted(actions);cursor=0;active=set();last=None;ledger=[];total_ticks=0;long_gaps=[];resets=[]
    def segment(rows,start_index):
        nonlocal last,total_ticks
        if not rows:return
        if active:
            summaries={}
            for mask in masks(active):
                summaries[keymask(mask)]={}
                for risk in (150,200):
                    qb=qs=basis=0
                    for i in mask:
                        t=trades[i];q=qsize(t,risk);sign=1 if t['side']=='BUY' else -1
                        qb+=q if sign==1 else 0;qs+=q if sign==-1 else 0;basis+=sign*q*t['entry_price_units']
                    s=StreamSummary()
                    for offset,(at,bid,ask) in enumerate(rows):s.add(qb*bid-qs*ask-basis,[at,start_index+offset])
                    summaries[keymask(mask)][str(risk)]=s.dump()
            ledger.append(dict(kind='segment',at=[rows[-1][0],start_index+len(rows)-1],start=[rows[0][0],start_index],summaries=summaries))
            if last is not None and rows[0][0]-last[0]>7200000:long_gaps.append(dict(previous=last,current=rows[0],active=sorted(active)))
            for a,b in zip(rows,rows[1:]):
                if b[0]-a[0]>7200000:long_gaps.append(dict(previous=a,current=b,active=sorted(active)))
            total_ticks+=len(rows)
        last=rows[-1]
    first=trades[0]['entry_msc']//HOUR*HOUR;final=trades[-1]['exit_msc']//HOUR*HOUR
    # Last signal need not have the latest exit if an older position survives.
    final=max(t['exit_msc'] for t in trades)//HOUR*HOUR
    for n,hour in enumerate(range(first,final+HOUR,HOUR)):
        rows,times=quotes.hour(hour);j=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            k=keys[cursor];at,index=k;cut=bisect_left(times,at) if index<0 else index
            if index>=0 and (cut>=len(rows) or rows[cut][0]!=at):raise ValueError('ledger_quote_ordinal')
            segment(rows[j:cut],j)
            if index>=0:
                if active and last is not None and rows[cut][0]-last[0]>7200000:
                    long_gaps.append(dict(previous=last,current=rows[cut],active=sorted(active)))
                last=rows[cut]
                ledger.append(dict(kind='point',at=list(k),quote=last))
            for kind,i,m in sorted(actions[k],key=lambda x:{'reset':0,'swap':1,'exit':2,'entry':3}[x[0]]):
                if kind=='reset' and active:
                    resets.append(dict(at=at,active=sorted(active),last_quote_msc=last[0] if last else None,
                        mark_age_ms=at-last[0] if last else None))
                ledger.append(dict(kind=kind,at=list(k),trade=i,mult=m,quote=last))
                if kind=='entry':active.add(i)
                if kind=='exit':active.remove(i)
            j=cut;cursor+=1
        segment(rows[j:],j)
        if n%500==0:event('segment_ledger',hours=n,segments=len(ledger),active=len(active))
    if active:raise ValueError('ledger_not_flat_at_cutoff')
    write_json(out/'ledger.json',dict(events=ledger,source_tick_marks=total_ticks,
        open_position_midnight_marks=resets,long_quote_gaps_while_held=long_gaps))
    return ledger,long_gaps


def native_terminal(index,balance,floating,anchor,days,at,start,positions,expected):
    profile=PropProfileSnapshot(profile_id='XAU-A-2step-declared',terms_version='20261114',profile_hash='sha256:XAU-A-20261114',effective_from=date(2026,11,14),source_kind='custom',phases=[phase_spec(1),phase_spec(2)])
    session=PropSessionSnapshot(workspace_id='offline',session_id='A',profile=profile,status='running')
    attempt=ChallengeAttemptSnapshot(workspace_id='offline',session_id='A',attempt_id='A',profile_id=profile.profile_id,terms_version=profile.terms_version,profile_hash=profile.profile_hash,data_version='2022-2024-frozen',cost_version='paired',engine_version='A-segments-v1',status='running',virtual_start_utc=utc(start),virtual_cutoff_utc=utc(END))
    b,f,a=(D(v)/1000 for v in (balance,floating,anchor))
    phase=PhaseStateSnapshot(workspace_id='offline',session_id='A',attempt_id='A',profile_hash=profile.profile_hash,phase_index=min(index,2),initial_balance='50000',balance=b,equity=b+f,floating_pl=f,high_water_mark=max(D(50000),b+f),daily_anchor=a,virtual_time_utc=utc(at),evaluation_quality='full_for_declared_model')
    e=PropLifecycleEvent(workspace_id='offline',session_id='A',attempt_id='A',profile_hash=profile.profile_hash,operation_id='terminal',expected_revision=attempt.revision,event_sequence=1,virtual_time_utc=utc(at),balance_before_separate_costs=b,floating_pl=f,open_positions=positions,evaluation_quality='full_for_declared_model')
    r=evaluate_prop_lifecycle_event(session,attempt,phase,e,resume_state={'prop_lifecycle':{'qualifying_local_dates':sorted(days)}})
    if r['objectives']['terminal_action']!=expected:raise ValueError('native_terminal_disagreement')
    if expected=='phase_pass':
        for action in ('next_phase','start'):
            intent=TransitionIntent(workspace_id='offline',session_id='A',attempt_id='A',profile_hash=profile.profile_hash,intent_id=action,expected_revision=r['attempt'].revision,event_sequence=r['phase'].last_event_sequence,action=action)
            r=apply_prop_lifecycle_command(session,r['attempt'],r['phase'],intent,resume_state=r['resume_state'])
        if r['phase'].balance!=50000 or r['phase'].phase_index!=2:raise ValueError('native_phase_reset_failed')
    return expected


class Case:
    def __init__(self,start,end,risk,cell,*,rolling=True):
        self.start=start;self.end=end;self.risk=risk;self.cell=cell;self.rolling=rolling
        self.balance=self.anchor=CAPITAL;self.active=set();self.swaps={};self.days=set();self.phase=1;self.gate=start-1
        self.passes=[];self.breach=None;self.entries=0;self.rejections=0;self.last=None;self.float=0
        self.peak=CAPITAL;self.dd=0;self.daily=0;self.static=0;self.funded_start=None;self.native_checks=0
        self.phase_dd=0;self.phase_daily=0;self.max_concurrency=0
        rules={i:money_oracle(phase_spec(i),MoneyOracleInput(initial_capital=50000,daily_anchor=50000,balance_before_separate_costs=50000,high_water_mark=50000)) for i in (1,2)}
        self.daily_allowance=int((rules[1]['daily_loss']['reference']-rules[1]['daily_loss']['floor'])*1000)
        self.overall_floor=int(rules[1]['overall_drawdown']['floor']*1000)
        self.targets={i:int(rules[i]['profit_target']['target']*1000) for i in (1,2)}
        self.min_days={i:phase_spec(i).min_qualifying_days for i in (1,2)}
    def floating(self,trades,quote):
        if not self.active:return 0
        if quote is None:raise ValueError('open_position_without_mark')
        value=0
        for i in self.active:
            t=trades[i];q=qsize(t,self.risk);sign=1 if t['side']=='BUY' else -1
            price=quote[1] if sign==1 else quote[2]
            value+=sign*q*(price-t['entry_price_units'])-q*200+self.swaps[i]
        return value
    def point(self,trades,at,quote):
        self.last=quote;v=self.floating(trades,quote);self.float=v
        self.metrics(self.balance+v,self.balance+v,0)
        if not self.rolling or self.breach:return
        if self.balance+v<max(self.anchor-self.daily_allowance,self.overall_floor):
            self.fail(at,v);return
        if self.phase<3 and not self.active and self.balance>=self.targets[self.phase] and len(self.days)>=self.min_days[self.phase]:
            expected='phase_pass' if self.phase==1 else 'complete_pass'
            native_terminal(self.phase,self.balance,v,self.anchor,self.days,at[0],self.start,0,expected);self.native_checks+=1
            self.passes.append(dict(phase=self.phase,at=at[0],balance_usd=self.balance/1000,days=len(self.days),max_R_DD=self.phase_dd/(self.risk*1000),worst_daily_loss_pct=self.phase_daily/500000))
            self.phase+=1;self.balance=self.anchor=CAPITAL;self.days=set();self.gate=at[0];self.float=0
            self.peak=CAPITAL;self.phase_dd=self.phase_daily=0
            if self.phase==3:self.funded_start=at[0]
    def metrics(self,low,high,internal):
        dd=max(self.peak-low,internal);self.dd=max(self.dd,dd);self.phase_dd=max(self.phase_dd,dd)
        self.peak=max(self.peak,high);loss=self.anchor-low
        self.daily=max(self.daily,loss);self.phase_daily=max(self.phase_daily,loss);self.static=max(self.static,CAPITAL-low)
    def fail(self,at,floating):
        oracle=money_oracle(phase_spec(min(self.phase,2)),MoneyOracleInput(initial_capital=50000,daily_anchor=D(self.anchor)/1000,balance_before_separate_costs=D(self.balance)/1000,floating_pl=D(floating)/1000,high_water_mark=max(D(50000),D(self.balance+floating)/1000)))
        if oracle['terminal_precedence']!='failed_breach':raise ValueError('native_breach_disagreement')
        native_terminal(self.phase,self.balance,floating,self.anchor,self.days,at[0],self.start,len(self.active),'breach');self.native_checks+=1
        self.breach=dict(at=at,phase=self.phase,daily=oracle['daily_loss']['breached'],overall=oracle['overall_drawdown']['breached'],equity_usd=(self.balance+floating)/1000)
    def consume(self,e,trades):
        at=e['at']
        if at[0]<self.start or at[0]>=self.end or self.breach:return
        kind=e['kind']
        if kind=='segment':
            if not self.active:return
            s=e['summaries'][keymask(self.active)][str(self.risk)]
            offset=self.balance-sum(qsize(trades[i],self.risk)*200 for i in self.active)+sum(self.swaps.values())
            floor=max(self.anchor-self.daily_allowance,self.overall_floor)-offset
            hit=next((low for low in s['lows'] if low[0]<floor),None) if self.rolling else None
            if hit:
                value,when,peak,dd=hit;self.metrics(offset+value,offset+peak,dd);self.float=offset+value-self.balance
                self.fail(when,self.float);return
            self.metrics(offset+s['min'],offset+s['max'],s['dd']);self.float=offset+s['last']-self.balance
            return
        i=e.get('trade');t=trades[i] if i is not None else None
        if kind=='reset':self.anchor=self.balance
        elif kind=='entry':
            if t['decision_msc']<self.start or t['decision_msc']<=self.gate:self.rejections+=1;return
            self.active.add(i);self.swaps[i]=0;self.balance-=fee(t,self.risk);self.entries+=1
            self.days.add(utc(t['entry_msc']).astimezone(PRAGUE).date().isoformat());self.max_concurrency=max(self.max_concurrency,len(self.active))
        elif kind=='swap':
            if i not in self.active:return
            self.swaps[i]+=swap(t,self.risk,self.cell,e['mult'])
        elif kind=='exit':
            if i not in self.active:return
            net=cents(t['sizing_costs'][str(self.risk)][self.cell]['net_usd'])*10
            self.balance+=net+fee(t,self.risk);self.active.remove(i);self.swaps.pop(i)
        self.point(trades,at,e['quote'])
    def dump(self):
        return dict(start_msc=self.start,end_msc=self.end,risk_usd=self.risk,risk_pct=self.risk/500,cell=self.cell,
            rolling=self.rolling,status='FAILED_MODEL_BREACH' if self.breach else 'FUNDED_MONITOR_CENSORED' if len(self.passes)==2 else 'RIGHT_CENSORED',
            entries=self.entries,rejected_prepass_or_prestart=self.rejections,phase_passes=self.passes,first_breach=self.breach,
            native_terminal_checks=self.native_checks,terminal_phase=self.phase,balance_usd=self.balance/1000,floating_usd=self.float/1000,
            net_R=(self.balance+self.float-CAPITAL)/(self.risk*1000),max_R_DD=self.dd/(self.risk*1000),peak_to_valley_pct=self.dd/500000,
            static_loss_pct=self.static/500000,worst_daily_loss_pct=self.daily/500000,max_concurrent_positions=self.max_concurrency,
            funded_start=self.funded_start,funded_net_usd=(self.balance+self.float-CAPITAL)/1000 if self.funded_start else None,
            daily_limit_touched=self.daily>=self.daily_allowance,overall_limit_touched=self.static>=CAPITAL-self.overall_floor,
            prop_qualified=False)


def evaluate(ledger,trades,start,end,risk,cell,rolling):
    c=Case(start,end,risk,cell,rolling=rolling)
    for e in ledger:
        if e['at'][0]>=end:break
        c.consume(e,trades)
        if c.breach:break
    return c.dump()


def execute(cfg_path):
    cfg=json.loads(Path(cfg_path).read_bytes());out=Path(cfg['output']);out.mkdir(exist_ok=False);event=Events(out)
    try:
        for path,sha in cfg['pins'].items():
            if digest(path)!=sha:raise ValueError('frozen_source_changed:'+path)
        write_json(out/'execution-binding.json',dict(config_sha256=digest(cfg_path),pins=cfg['pins'],
            utc=datetime.now(timezone.utc).isoformat(),before_financial_outcomes=True))
        quotes,source_counts=admit(cfg,out,event)
        trades=make_paths(cfg,out,quotes,event)
        ledger,gaps=build_ledger(trades,quotes,out,event)
        if gaps:raise ValueError('calendar_still_holds_through_quote_break_over2h')
        annual=[];rolling=[];continuous=[]
        for risk in (150,200):
            for cell in CELLS:
                for year in (2022,2023,2024):
                    event('annual',year=year,risk=risk,cell=cell)
                    a=evaluate(ledger,trades,ms(f'{year}-01-01'),ms(f'{year+1}-01-01'),risk,cell,False)
                    subset=[t for t in trades if t['day'].startswith(str(year))]
                    a.update(year=year,trades=len(subset),buy=sum(t['side']=='BUY' for t in subset),sell=sum(t['side']=='SELL' for t in subset),
                        annual_net_R=sum(t['sizing_costs'][str(risk)][cell]['net_R'] for t in subset),
                        mean_net_R=sum(t['sizing_costs'][str(risk)][cell]['net_R'] for t in subset)/len(subset))
                    if abs(a['annual_net_R']-a['net_R'])>1e-8:raise ValueError('annual_cash_bridge')
                    annual.append(a)
                continuous.append(evaluate(ledger,trades,START,END,risk,cell,False))
                for year in (2022,2023,2024):
                    for month in range(1,13):
                        event('rolling_case',year=year,month=month,risk=risk,cell=cell)
                        a=evaluate(ledger,trades,ms(f'{year}-{month:02d}-01'),END,risk,cell,True)
                        a.update(start_year=year,start_month=month,quarterly_subset=month in (1,4,7,10));rolling.append(a)
        result=dict(schema='XAU-A-validation-result-v1',annual=annual,rolling=rolling,continuous=continuous,
            source_counts=source_counts,raw_signals=len(trades),path_coverage_complete=True,long_quote_gaps_while_held=gaps,
            config_sha256=digest(cfg_path),trades_sha256=digest(out/'trades.json'),ledger_sha256=digest(out/'ledger.json'),
            binary_manifest_sha256=digest(out/'binary-manifest.json'),prices2025_2026_read=False,broker_calls=0,
            prop_qualified=False,wall_seconds=time.monotonic()-event.start)
        write_json(out/'result.json',result);event('completed',sha256=digest(out/'result.json'))
    except BaseException as exc:
        import traceback
        write_json(out/'failure.json',dict(type=type(exc).__name__,code=str(exc),locations=[dict(file=f.filename,line=f.lineno) for f in traceback.extract_tb(exc.__traceback__)]))
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();execute(a.config)
