"""Separate rational cost and integer equity oracle; no broker/network/holdout."""
from collections import defaultdict
from datetime import datetime,timedelta,timezone
from fractions import Fraction as F
from functools import lru_cache
import json
from pathlib import Path
import struct
from zoneinfo import ZoneInfo

from eurusd_b0_source import digest,write_json

HOUR=3600000
REC=struct.Struct('<qii')
CELLS=('SYM_FLAT','SYM_ORDER','ASYM_FLAT','ASYM_ORDER')


def rounded_cents(value):
    x=F(value)*100;sign=1 if x>=0 else -1;x=abs(x)
    return sign*((2*x.numerator+x.denominator)//(2*x.denominator))


def funding(at,end):
    d=datetime.fromtimestamp(at/1000,timezone.utc).replace(hour=22,minute=0,second=0,microsecond=0)
    result=[]
    while d.timestamp()*1000<=end:
        stamp=int(d.timestamp()*1000)
        if at<stamp and d.weekday()<5:result.append((stamp,3 if d.weekday()==2 else 1))
        d+=timedelta(days=1)
    return result


def money_parts(t,c):
    q=t['ounces'];p0=t['entry_price_units'];p1=t['exit_price_units'];sign=1 if t['side']=='BUY' else -1
    commission=[rounded_cents(F(p*q*7,10**9)) for p in (p0,p1)]
    slip=[q*20,0 if t['reason']=='TP2R' and c.endswith('ORDER') else q*20]
    swaprate=-40 if c.startswith('SYM') else -45 if sign==1 else -5
    swaps=[(at,q*swaprate*m) for at,m in funding(t['entry_msc'],t['exit_msc'])]
    gross=rounded_cents(F(sign*(p1-p0)*q,1000))
    return dict(commission=commission,slip=slip,swaps=swaps,gross=gross,
        net=gross-sum(commission)-sum(slip)+sum(v for _,v in swaps))


class Reader:
    def __init__(self,path):self.path=Path(path)
    @lru_cache(maxsize=64)
    def hour(self,at):
        if not 1640995200000<=at<1704067200000:raise AssertionError('holdout')
        p=self.path/f'{at}.ticks'
        return list(REC.iter_unpack(p.read_bytes())) if p.exists() else []


def oracle_book(trades,reader,year,cells=('SYM_FLAT','ASYM_ORDER')):
    actions=defaultdict(list);cash={c:0 for c in cells};parts={}
    for i,t in enumerate(trades):
        parts[i]={c:money_parts(t,c) for c in cells}
        actions[t['entry_msc']].append(('entry',i,0))
        actions[t['exit_msc']].append(('exit',i,0))
        for at,m in funding(t['entry_msc'],t['exit_msc']):actions[at].append(('swap',i,m))
    d=datetime(year,1,1).date()
    while d.year<=year:
        at=int(datetime(d.year,d.month,d.day,tzinfo=ZoneInfo('Europe/Prague')).timestamp()*1000)
        actions[at].append(('reset',None,0));d+=timedelta(days=1)
    start=min(t['entry_msc'] for t in trades);end=max(t['exit_msc'] for t in trades)
    stamps=sorted(at for at in actions if start<=at<=end);ai=0
    qtyb=qtys=basis=0;last=None
    state={c:dict(peak=0,dd=0,daily=0,anchor=0,minimum=0) for c in cells}
    def mark():
        floating=qtyb*last[1]-qtys*last[2]-basis if last else 0
        for c in cells:
            value=cash[c]*10+floating;s=state[c]
            s['dd']=max(s['dd'],s['peak']-value);s['peak']=max(s['peak'],value)
            s['daily']=max(s['daily'],s['anchor']*10-value);s['minimum']=min(s['minimum'],value)
    def act(at,quote=None):
        nonlocal qtyb,qtys,basis,last
        if any(a[0]=='reset' for a in actions[at]):
            for c in cells:state[c]['anchor']=cash[c]
        if quote is not None:last=quote;mark()
        for kind,i,m in sorted(actions[at],key=lambda a:{'reset':0,'swap':1,'exit':2,'entry':3}[a[0]]):
            if kind=='reset':continue
            t=trades[i];q=t['ounces'];sign=1 if t['side']=='BUY' else -1
            if kind=='entry':
                qtyb+=q if sign==1 else 0;qtys+=q if sign==-1 else 0;basis+=sign*q*t['entry_price_units']
                for c in cells:cash[c]-=parts[i][c]['commission'][0]+parts[i][c]['slip'][0]
            elif kind=='exit':
                qtyb-=q if sign==1 else 0;qtys-=q if sign==-1 else 0;basis-=sign*q*t['entry_price_units']
                for c in cells:cash[c]+=parts[i][c]['gross']-parts[i][c]['commission'][1]-parts[i][c]['slip'][1]
            else:
                for c in cells:cash[c]+=dict(parts[i][c]['swaps'])[at]
            mark()
    tick_marks=0
    for hour in range(start//HOUR*HOUR,end//HOUR*HOUR+1,HOUR):
        for row in reader.hour(hour):
            at=row[0]
            if at<start or at>end:continue
            while ai<len(stamps) and stamps[ai]<=at:
                s=stamps[ai];act(s,row if s==at else None);ai+=1
            last=row
            if qtyb or qtys:mark();tick_marks+=1
        # Missing source hours are legal only while flat; still apply resets.
        while ai<len(stamps) and stamps[ai]<hour+HOUR:
            act(stamps[ai]);ai+=1
    assert qtyb==qtys==basis==0
    return {c:dict(dd_usd=s['dd']/1000,daily_usd=s['daily']/1000,cash_usd=cash[c]/100)
        for c,s in state.items()},tick_marks


def review(root):
    root=Path(root);result=json.loads((root/'result.json').read_bytes());trades=json.loads((root/'trades.json').read_bytes())
    reader=Reader(root/'ticks');count=0;books=[];ticks=0
    for t in trades:
        if t['costs'] is None:continue
        for c in CELLS:
            p=money_parts(t,c);e=t['costs'][c]
            assert rounded_cents(str(e['net_usd']))==p['net']
            assert rounded_cents(str(e['gross_usd']))==p['gross']
            assert rounded_cents(str(e['commission_usd']))==sum(p['commission'])
            assert rounded_cents(str(e['slippage_usd']))==sum(p['slip'])
            assert rounded_cents(str(e['swap_usd']))==sum(v for _,v in p['swaps'])
            count+=1
    for summary in result['summaries']:
        b=summary['book']
        subcohort=b['status']=='UNRESOLVED_PATH_BOOK_NOT_MEASURED'
        if subcohort:b=b.get('resolved_subcohort_only')
        if not b or b['status']!='OBSERVED_TICK_BOOK_CONDITIONAL':continue
        subset=[t for t in trades if t['recipe']==summary['recipe'] and t['exit_policy']==summary['policy']
            and t['day'].startswith(str(summary['year'])) and (summary['view']=='BOTH' or t['side']==summary['view'])
            and t['exit_msc'] is not None]
        observed,n=oracle_book(subset,reader,summary['year']);ticks+=n
        for c,r in observed.items():
            expected_book=b['costs'][c]
            for actual,expected in [(r['dd_usd'],expected_book['max_equity_drawdown_usd']),
                (r['daily_usd'],expected_book['worst_daily_loss_usd']),(r['cash_usd'],expected_book['realized_net_usd'])]:
                assert abs(actual-expected)<1e-6,(summary['recipe'],summary['policy'],summary['year'],c,actual,expected)
        books.append(dict(recipe=summary['recipe'],view=summary['view'],policy=summary['policy'],year=summary['year'],
            resolved_subcohort_only=subcohort,oracle=observed,tick_marks=n))
        print(json.dumps(dict(stage='integer_oracle',books=len(books),tick_marks=ticks)),flush=True)
    packet=dict(status='SELF_AUDIT_PASSED_NOT_INDEPENDENT_REVIEW',cost_bridges=count,books=books,
        observed_tick_marks=ticks,result_sha256=digest(root/'result.json'),trades_sha256=digest(root/'trades.json'),
        reviewer_source_sha256=digest(__file__),prices2024_2026_read=False)
    write_json(root/'arithmetic-review.json',packet)


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('root');a=p.parse_args();review(a.root)
