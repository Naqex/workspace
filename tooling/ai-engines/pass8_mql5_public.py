"""Guest-only, throttled MQL5 public statistics census for Pass 8."""

import argparse
from collections import Counter
from datetime import datetime, timezone
from hashlib import sha256
import html
import json
from math import isfinite
from pathlib import Path
import re
import time


BASE='https://www.mql5.com/en/signals/'
EXCLUDED={'2308133','2266387','2229611','2201028','2237614','2311977','1919885','2283078'}
FIELD=re.compile(r'<div class="s-(?:data-columns|list-info)__label"[^>]*>(.*?)</div>\s*'
                 r'<div class="s-(?:data-columns|list-info)__value"[^>]*>(.*?)</div>',re.S)
PERCENT=re.compile(r'([-+]?\d+(?:\.\d+)?)\s*%')


def clean(s):
    return ' '.join(html.unescape(re.sub(r'<[^>]+>','',s)).split())


def number(value):
    m=re.search(r'[-+]?\d+(?:\.\d+)?',value.replace(',','').replace(' ',''))
    return float(m[0]) if m and isfinite(float(m[0])) else None


def percent(value):
    m=PERCENT.search(value)
    return float(m[1]) if m else None


def list_rows(raw, platform):
    for row in raw.split('class="row signal">')[1:]:
        signal=re.search(r'class="signal-avatar"\s+href="https://www\.mql5\.com/en/signals/(\d+)"',row)
        if not signal:
            continue
        def cls(label,tag='div'):
            m=re.search(rf'<{tag} class="{label}(?: [^"]*)?"[^>]*>(.*?)</{tag}>',row,re.S)
            return clean(m[1]) if m else ''
        sid=signal[1]
        yield dict(signal_id=sid,name=cls('name','span'),url=BASE+sid,platform=platform,
                   real='title="Real Account"' in row.partition('</a>')[0],
                   weeks=number(cls('col-weeks')),trades=number(cls('col-trades')),
                   algo=percent(cls('col-experts')),dd=percent(cls('col-drawdown')),
                   win=percent(cls('col-plus')),pf=number(cls('col-pf')))


def recency(text, stamp):
    match=re.search(r'(\d+)\s+(seconds?|minutes?|hours?|days?|weeks?|months?|years?)\s+ago',text,re.I)
    if match:
        unit=match[2].lower().rstrip('s')
        return int(match[1])*{'second':1/86400,'minute':1/1440,'hour':1/24,
                             'day':1,'week':7,'month':30,'year':365}[unit]
    try:
        latest=datetime.fromisoformat(text.replace('.','-',2)).replace(tzinfo=timezone.utc)
        return (stamp-latest).total_seconds()/86400
    except ValueError:
        return 0. if text.lower() in ('just now','today') else None


def description_risk(text):
    text=text.lower()
    pattern=r'grid|martingale|averaging down|dollar.cost averaging|recovery basket|\bdca\b'
    for sentence in re.split(r'[.!\n;]',text):
        if not re.search(pattern,sentence):
            continue
        if re.search(r'\b(?:uses?|using|implements?|employs?|combines?|based on)\s+(?:a |an |the )?(?:'
                     +pattern+r')\b|\b(?:grid|martingale|dca)\s+(?:system|strategy|trading|lot multiplier)\b',sentence):
            if not re.search(r'\b(?:no|without|avoids?|never|not|non[- ])\b',sentence):
                return True
    return False


def detail(raw, row, stamp):
    if 'signal is disabled and unavailable' in raw:
        return row|{'access':'disabled'}
    fields={clean(k).rstrip(':'):clean(v) for k,v in FIELD.findall(raw)}
    content=raw.partition('id="signal-content"')[2].partition('id="tab_history"')[0]
    monitors=re.search(r'total Signal monitoring period \(([^)]*)\)',raw)
    monitor=monitors[1] if monitors else ''
    days=re.search(r'(\d[\d ,]*)\s+days?\b',monitor)
    age=number(days[1]) if days else None
    desc=raw.partition('id="description"')[2].partition('</div>')[0]
    summary_win=percent(fields.get('Profit Trades',''))
    avg_profit=number(fields.get('Average Profit',''))
    avg_loss=number(fields.get('Average Loss',''))
    dd={k:percent(fields.get(field,'')) for k,field in
        [('balance_relative_dd','By Balance'),('equity_relative_dd','By Equity'),
         ('maximal_cash_dd_pct','Maximal')]}
    dist={clean(s):int(re.sub(r'\D','',n)) for s,n in re.findall(
        r'<td class="col-symbol">([^<]+)</td>\s*<td class="col-buy-sell col-right">([\d ,\u00a0]+)</td>',raw)}
    h=raw.partition('id="tab_content_history"')[2].partition('id="tab_content_statistics"')[0]
    guest_csv=('export to csv' in h.lower() and 'class="need-auth"' not in h and '<table' in h)
    return dict(row,access='public_statistics' if fields else 'statistics_missing',monitor_days=age,
                real_detail='title="Real Account"' in content,
                detail_weeks=number(fields.get('Weeks','')),detail_trades=number(fields.get('Trades','')),
                detail_algo=percent(fields.get('Algo trading','')),detail_win=summary_win,
                last_trade=fields.get('Latest trade'),last_trade_days=recency(fields.get('Latest trade',''),stamp),
                trades_per_week_displayed=number(fields.get('Trades per week','')),
                holding=fields.get('Avg holding time'),deposit_load=percent(fields.get('Max deposit load','')),
                avg_profit=avg_profit,avg_loss=avg_loss,distribution=dist,guest_csv=guest_csv,
                history_gate='login' if 'class="need-auth"' in h else 'not_verified',
                disclosed_grid=description_risk(clean(desc)),**dd)


def evaluate(d):
    if d['access']!='public_statistics':
        return ['statistics_unverified'],[]
    missing={'monitor_days','detail_trades','detail_algo','last_trade_days',
             'balance_relative_dd','equity_relative_dd'}
    t1=sorted(f'unverified_{key}' for key in missing if d[key] is None)
    if not d['real_detail']:
        t1.append('real_not_verified')
    for field,minimum in [('monitor_days',364),('detail_trades',150),('detail_algo',80)]:
        if d[field] is not None and d[field]<minimum:
            t1.append(field+'_below_floor')
    if d['last_trade_days'] is not None and not 0<=d['last_trade_days']<=30:
        t1.append('inactive')
    observed=[d[f] for f in ('balance_relative_dd','equity_relative_dd','maximal_cash_dd_pct') if d[f] is not None]
    d['max_dd']=max(observed) if observed else None
    if d['max_dd'] is not None and d['max_dd']>20:
        t1.append('dd_above_20')
    if t1:
        return t1,[]
    win,loss=d['avg_profit'],d['avg_loss']
    ratio=win/abs(loss) if win is not None and loss not in (None,0) else None
    d['reward_loss_ratio']=ratio
    observed=d['trades_per_week_displayed']
    life=d['detail_trades']/d['detail_weeks'] if d['detail_weeks'] else None
    d['trades_per_week_gate']=max(observed,life) if observed is not None and life is not None else observed
    t2=[]
    if ratio is None or ratio<.85-1e-12:
        t2.append('reward_loss_below_0_85_or_missing')
    if d['detail_win'] is None:
        t2.append('winrate_unverified')
    elif d['detail_win']>72 and (ratio is None or ratio<1):
        t2.append('high_winrate_and_small_wins')
    if d['trades_per_week_gate'] is None or d['trades_per_week_gate']>20:
        t2.append('cadence_above_20_or_missing')
    if d['deposit_load'] is not None and d['deposit_load']>20:
        t2.append('deposit_load_above_20')
    if d['equity_relative_dd']>1.5*d['balance_relative_dd']+1e-12:
        t2.append('equity_balance_dd_ratio')
    if d['disclosed_grid']:
        t2.append('disclosed_grid_or_recovery')
    return t1,t2


def list_gate(d):
    return (d['signal_id'] not in EXCLUDED and d['real'] and (d['weeks'] or 0)>=52
            and (d['trades'] or 0)>=150 and (d['algo'] or 0)>=80
            and d['dd'] is not None and d['dd']<=20)


def save(path, data):
    path.write_text(json.dumps(data,ensure_ascii=False,indent=2,allow_nan=False)+'\n',
                    encoding='utf-8',newline='\n')


def scan(folder):
    import requests

    cache=folder/'public'
    cache.mkdir(exist_ok=True)
    events=[]
    last=0.
    blocked=False
    def fetch(url,name):
        nonlocal last,blocked
        if blocked:
            return None
        path=cache/name
        if path.is_file():
            raw=path.read_text(encoding='utf-8')
            stamp=datetime.fromtimestamp(path.stat().st_mtime,timezone.utc)
            events.append(dict(url=url,file=name,status=200,reused=True,sha256=sha256(path.read_bytes()).hexdigest()))
            return raw,stamp
        time.sleep(max(0.,2-(time.monotonic()-last)))
        last=time.monotonic()
        stamp=datetime.now(timezone.utc)
        try:
            rsp=requests.get(url,timeout=20,allow_redirects=False)
        except requests.RequestException as e:
            events.append(dict(url=url,file=None,status=type(e).__name__))
            return None
        challenge=rsp.headers.get('cf-mitigated')=='challenge' or '<title>Just a moment' in rsp.text
        if challenge or rsp.status_code in (401,403,429):
            blocked=True
        events.append(dict(url=url,file=None,status=rsp.status_code,challenge=challenge))
        if rsp.status_code!=200 or challenge:
            return None
        path.write_bytes(rsp.content)
        events[-1].update(file=name,sha256=sha256(rsp.content).hexdigest())
        return rsp.text,stamp
    all_rows={}
    pages={}
    for platform in ('MT5','MT4'):
        p=platform.lower()
        # The page and sort links are from the public catalogue.
        for ordering,total in [('dd',14),('rank',4)]:
            for page in range(1,total+1):
                name=f'{p}-{ordering}-{page}.html'
                endpoint=p+'/list'+(f'/page{page}' if page>1 else '')
                suffix='?orderby=drawdown&dir=up' if ordering=='dd' else ''
                data=fetch(BASE+endpoint+suffix,name)
                if data is None:
                    if blocked:
                        break
                    continue
                rows=list(list_rows(data[0],platform))
                pages[name]=len(rows)
                if not rows:
                    break
                for d in rows:
                    all_rows.setdefault(d['signal_id'],d)
            if blocked:
                break
        if blocked:
            break
    leads=[d for d in all_rows.values() if list_gate(d)]
    leads.sort(key=lambda d:(d['platform']!='MT5',d['dd'],-d['weeks']))
    save(folder/'lists.json',dict(pages=pages,rows=list(all_rows.values()),leads=len(leads)))
    print('Public rows',sum(pages.values()),'unique',len(all_rows),'detail leads',len(leads),flush=True)
    details=[]
    for i,row in enumerate(leads,1):
        item=fetch(row['url'],'detail-'+row['signal_id']+'.html')
        if item is None:
            if blocked:
                break
            continue
        result=detail(item[0],row,item[1])
        result['layer1_reasons'],result['layer2_reasons']=evaluate(result)
        result['observed_at_utc']=item[1].isoformat()
        details.append(result)
        if i%10==0:
            print(i,'/',len(leads),'details',flush=True)
    tier1=[d for d in details if not d['layer1_reasons']]
    passed=[d for d in tier1 if not d['layer2_reasons']]
    save(folder/'public-scan.json',dict(pages=pages,counts=dict(list_pages=len(pages),listed_rows=sum(pages.values()),
         distinct_ids=len(all_rows),excluded_ids_seen=len(EXCLUDED&all_rows.keys()),eligible_after_id_exclusions=len(all_rows.keys()-EXCLUDED),
         list_prefilter=len(leads),detail_pages=len(details),layer1=len(tier1),layer2=len(passed)),
         excluded_ids=sorted(EXCLUDED),details=details,passed=passed,events=events,stopped_for_access_block=blocked,
         rejection_counts=dict(Counter(x for d in details for x in (d['layer1_reasons']+d['layer2_reasons'])))))
    print('Complete',len(details),len(tier1),len(passed),'blocked',blocked,flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('folder',type=Path)
    scan(parser.parse_args().folder)
