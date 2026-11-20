"""Batch admission and descriptive blueprints for Bot Lab trade logs."""

from collections import Counter, defaultdict
from pathlib import Path
from hashlib import sha256
from zoneinfo import ZoneInfo
import json

import numpy as np

from bot_live_auditor import LIMIT, audit
from quant_core.ftmo_track_replay import Market, read_json_file, sessions, utc_time
from quant_core.native_paths import read_bounded

FORMATS = {'.csv','.html','.htm'}
REJECTED = 'REJECTED_TOXIC_OR_FTMO_BREACH'
UNKNOWN = 'INSUFFICIENT_DATA_UNKNOWN'
SWING = 'PASS_SWING_CANDIDATE'
BOTH = 'PASS_SWING_AND_STANDARD'
BASE_FIELDS = ('open_time','close_time','direction','lots','open_price','close_price','initial_sl')
TOKYO, LONDON, NEW_YORK = (ZoneInfo(t) for t in ('Asia/Tokyo','Europe/London','America/New_York'))

def news_file(path):
    if path is None:
        return None
    p=read_json_file(path)
    start,end=p['valid_from_utc_msc'],p['valid_to_utc_msc']
    if not p.get('source') or not isinstance(start,int) or not isinstance(end,int) or start>=end:
        raise ValueError('RESTRICTED_NEWS_BINDING_INVALID')
    if any(not isinstance(t,int) or not start<=t<end for events in p['restricted_news_by_symbol'].values() for t in events):
        raise ValueError('RESTRICTED_NEWS_OUTSIDE_COVERAGE')
    return p


def news_gate(rows, news):
    flagged=[]
    assessed=0
    bins=news['restricted_news_by_symbol'] if news else {}
    for t in rows:
        a,b=t['open_time'],t['close_time']
        if (t['time_basis']=='reported_fill' and a is not None and b is not None and t['symbol'] in bins and
                news['valid_from_utc_msc']<=a-120000 and b+120000<news['valid_to_utc_msc']):
            assessed+=1
            for at in (a,b):
                if any(abs(at-e)<=120000 for e in bins[t['symbol']]):
                    flagged.append(t['row'])
                    break
    return dict(status='RESTRICTED_WINDOW_HIT' if flagged else
                'CLEAR_ON_PROVIDED_CALENDAR' if rows and assessed==len(rows) else 'UNKNOWN_RESTRICTED_NEWS_COVERAGE',
                assessed=assessed,flagged_rows=flagged)


def screen(book, count):
    checks=book['ftmo_rule_breach_sim']
    confirmed=[]
    uncertain=[]
    for s in checks:
        tag=f"{s['capital_usd']}@{s['risk_per_trade_pct']:g}%"
        if s['daily_breach_observed'] or s['overall_breach_observed']:
            confirmed.append(dict(code='FTMO_RULE_BREACH_SIM',scenario=tag,
                                  daily_loss_pct=s['daily_loss_pct'],maximum_loss_pct=s['maximum_loss_pct'],
                                  scope=s['status']))
        if s['margin_100pct_exceeded_at_equity_mark']:
            confirmed.append(dict(code='FTMO_MARGIN_AT_EQUITY_MARK',scenario=tag,
                                  margin_pct=s['margin_peak_pct_available_equity']))
        if s['normalized_trades']==count and s['net_usd'] is not None and s['net_usd']<=0:
            confirmed.append(dict(code='NONPOSITIVE_TARGET_NET',scenario=tag,net_usd=s['net_usd']))
        if (s['status']!='NO_BREACH_AT_SAMPLED_MARKS' or s['normalized_trades']!=count or
                s['known_entry_margin_trades']!=count or s['margin_peak_pct_available_equity'] is None):
            uncertain.append(dict(code='EQUITY_MARGIN_OR_RISK_EVIDENCE_INCOMPLETE',scenario=tag,
                                  covered=s['normalized_trades'],margin_covered=s['known_entry_margin_trades']))
    costs=book['target_reprice']
    if costs['trades']==count and costs['totals_usd'] is not None and costs['totals_usd']['net']<=0:
        confirmed.append(dict(code='NONPOSITIVE_TARGET_NET_AT_LOGGED_SIZES',net_usd=costs['totals_usd']['net']))
    if costs['trades']!=count or not count:
        uncertain.append(dict(code='TARGET_COST_COVERAGE_INCOMPLETE',covered=costs['trades']))
    return confirmed,uncertain


def decision(report, news=None):
    rows=report['normalized_trades']
    n=len(rows)
    flags=report['behavioral_toxicity']
    fatal=[]
    missing=[]
    for key in ('HIDDEN_MARTINGALE_LOT_ESCALATION','HIDDEN_GRID_AVERAGING_DOWN',
                'NO_HARD_SL_OR_WIDE_STOP_GAMBLING','CONCENTRATED_LOTTERY_PROFILE'):
        item=flags[key]
        if item['status'].startswith('FLAG'):
            fatal.append(dict(code=key,evidence=item.get('evidence'),
                              explicit_no_sl=item.get('explicit_no_sl'),
                              avg_loss_over_avg_win=item.get('avg_loss_over_avg_win'),
                              concentration=item.get('metrics') if key=='CONCENTRATED_LOTTERY_PROFILE' else None))
    overlap=flags['HIDDEN_GRID_AVERAGING_DOWN']['overlaps_without_mark_or_clock']
    if overlap:
        missing.append(dict(code='GRID_PRICE_OR_POSITION_OVERLAP_UNRESOLVED',overlap_checks=overlap))
    norm=report['normalization']
    expected_exclusions = {'NON_TRADE_OR_CASH_FLOW', 'NON_TRADE_PENDING_ORDER'}
    if not n or norm['warnings'] or norm['rejected'].keys() - expected_exclusions:
        missing.append(dict(code='PARTIAL_OR_UNRECONCILED_LOG',warnings=norm['warnings'],rejected=norm['rejected']))
    gaps={k:norm['unknown_counts'][k] for k in BASE_FIELDS if norm['unknown_counts'][k]}
    if gaps:
        missing.append(dict(code='MINIMUM_TRADE_FIELDS_MISSING',fields=gaps))
    if any(t['time_basis']!='reported_fill' for t in rows):
        missing.append(dict(code='BROKER_FILL_CLOCK_REQUIRED'))
    if report['path_scope_counts'].get('bar_path_skipped_holdout_lock'):
        missing.append(dict(code='BAR_PATH_SKIPPED_HOLDOUT_LOCK',
                           trades=report['path_scope_counts']['bar_path_skipped_holdout_lock']))

    swing_fit=report['profiles']['Swing']
    standard_fit=report['profiles']['Standard']
    breaches,unresolved=screen(swing_fit,n)
    fatal+=breaches
    missing+=unresolved
    std_breaches,std_unresolved=screen(standard_fit,n)
    market_breaks=standard_fit['calendar']
    if market_breaks['breaches']:
        std_breaches.append(dict(code='STANDARD_LONG_MARKET_BREAK',evidence=market_breaks['breaches']))
    elif market_breaks['status']!='NO_LONG_BREAK_OBSERVED':
        std_unresolved.append(dict(code='STANDARD_MARKET_BREAK_COVERAGE_UNKNOWN',
                                   weekend_proxy_rows=market_breaks['weekend_proxy_rows']))
    ng=news_gate(rows,news)
    if ng['flagged_rows']:
        std_breaches.append(dict(code='STANDARD_RESTRICTED_NEWS_WINDOW',rows=ng['flagged_rows']))
    elif ng['status']!='CLEAR_ON_PROVIDED_CALENDAR':
        std_unresolved.append(dict(code=ng['status']))
    standard_pass=not std_breaches and not std_unresolved
    status=REJECTED if fatal else UNKNOWN if missing else BOTH if standard_pass else SWING

    def conservative_pct(book):
        base=[100*s['net_usd']/s['capital_usd'] for s in book['ftmo_rule_breach_sim'] if s['risk_per_trade_pct']==.5]
        return min(base)
    score=None
    if status in (BOTH,SWING):
        months=log_geometry(rows)['calendar_months']
        score=(.8*conservative_pct(swing_fit)+.2*(conservative_pct(standard_fit) if standard_pass else 0.))/months
    return dict(status=status,score=score,confirmed_rejections=fatal,evidence_gaps=missing,
                standard=dict(passed=standard_pass,failed=std_breaches,unknown=std_unresolved,news=ng))


def session(at):
    at=utc_time(at)
    tokyo=9<=at.astimezone(TOKYO).hour<18
    london=8<=at.astimezone(LONDON).hour<17
    ny=8<=at.astimezone(NEW_YORK).hour<17
    if london and ny:
        return 'London_NY_overlap'
    if tokyo and london:
        return 'Asia_London_overlap'
    if tokyo:
        return 'Asia'
    if london:
        return 'London'
    if ny:
        return 'NY'
    return 'Other'


def spans_weekend(t):
    from datetime import timedelta
    a,b=(utc_time(t[k]) for k in ('open_time','close_time'))
    saturday=(a+timedelta(days=(5-a.weekday())%7)).replace(hour=0,minute=0,second=0,microsecond=0)
    sunday=saturday+timedelta(days=1)
    return a<sunday and b>saturday or a.weekday()==6 and b>a


def quantiles(values):
    return {k:float(np.quantile(values,q)) if values else None for k,q in (('p25',.25),('median',.50),('p75',.75),('p90',.9))}


def log_geometry(rows):
    closes=[t for t in rows if t['time_basis']=='reported_fill' and t['open_time'] is not None and
            t['close_time'] is not None and t['open_time']<t['close_time']]
    holding=[(t['close_time']-t['open_time'])/3_600_000 for t in closes]
    buckets=Counter('weekend_utc' if spans_weekend(t) else 'overnight_utc' if
                    utc_time(t['open_time']).date()!=utc_time(t['close_time']).date() else 'intraday_utc' for t in closes)
    valid=[utc_time(t['open_time']) for t in closes]
    months=0
    if valid:
        lo,hi=min(valid),max(valid)
        months=(hi.year-lo.year)*12+hi.month-lo.month+1
    r=[t['reported_r'] for t in rows if t['reported_r'] is not None]
    return dict(trades=len(rows),exact_clock_trades=len(closes),calendar_months=months,
        holding_share={k:buckets[k]/len(closes) if closes else None
                      for k in ('intraday_utc','overnight_utc','weekend_utc')},
        hold_hours=quantiles(holding), trades_per_calendar_month=len(closes)/months if months else None,
        lot_quantiles=quantiles([t['lots'] for t in rows if t['lots'] is not None]),
        reported_R={'n':len(r),'total':sum(r) if r else None,'quantiles':quantiles(r)},
        session_dna={name:dict(hour_utc=dict(Counter(utc_time(t[name]).hour for t in closes)),
                               bucket=dict(Counter(session(t[name]) for t in closes)))
                     for name in ('open_time','close_time')})


def blueprint(report):
    rows=report['normalized_trades']
    n=len(rows)
    by_asset=Counter(t['symbol'] for t in rows)
    p=[[],[]]
    for t in rows:
        for i,point in enumerate((t['initial_sl'],t['tp'])):
            if point and point>0:
                p[i].append(abs(point-t['open_price'])/t['open_price']*100)
    profile=report['profiles']['Swing']
    price_net=profile['target_reprice']
    by_symbol=price_net['by_symbol']
    gross=sum(x['positive_price_pnl_usd'] for x in by_symbol.values())
    total=price_net['totals_usd']
    net=total['net']
    report_profit=profile.get('target_trade_expectancy',{})
    return dict(assets={s:dict(trades=c,trade_share=c/n,target_net_usd=by_symbol[s]['net_usd'],
                               net_contribution_share=by_symbol[s]['net_usd']/net if net else None,
                               positive_price_pnl_share=by_symbol[s]['positive_price_pnl_usd']/gross if gross else None)
                        for s,c in by_asset.items()},
                audited_ftmo_symbol_trade_share=profile['supported_trades']/n,
                **log_geometry(rows),winrate=report_profit.get('winrate'),
                avg_win_over_avg_loss=report_profit.get('avg_win_over_avg_loss'),
                initial_sl_distance_pct=quantiles(p[0]),tp_distance_pct=quantiles(p[1]),
                target_cost_usd={'commission':total['commission'],'net_swap':total['swap'],
                                 'positive_price_pnl_usd':gross},
                target_execution_cost_share=total['commission']/gross if gross else None,
                target_cost_including_swap_share=(total['commission']-total['swap'])/gross if gross else None,
                winner_taxonomy=profile['winner_diagnosis']['counts'],
                bar_path_status=report['path_scope_counts'],
                basis='SWING_TARGET_AT_LOGGED_LOTS; CLOSED_TRADE_COHORT; FIXED_SNAPSHOT_COSTS')


def audit_batch(files, market, calendar=None, news=None, **options):
    leaders=[]
    blueprints=[]
    seen={}
    pair_payload=options.pop('pair_payload',None)
    for file in files:
        try:
            raw=read_bounded(file,LIMIT)
            digest=sha256(raw).hexdigest()
            if digest in seen:
                leaders.append(dict(file=file.name,status=UNKNOWN,score=None,duplicate_of=seen[digest],
                    evidence_gaps=[{'code':'EXACT_DUPLICATE_EXPORT'}],confirmed_rejections=[]))
                continue
            pair=pair_payload if pair_payload and pair_payload.get('input_sha256')==digest else None
            r=audit(raw,file.suffix.lower(),market=market,calendar=calendar,include_rows=True,pair_payload=pair,**options)
            seen[digest]=file.name
            d=decision(r,news)
            leaders.append(dict(file=file.name,sha256=digest,**d,
                trades=r['normalization']['accepted'],source=r['normalization']['layout'],
                normalization=r['normalization'], out_of_ftmo_13_universe=r['out_of_ftmo_13_universe'],
                path_scope=r['path_scope_counts'], log_geometry=log_geometry(r['normalized_trades']),
                log_only_after_lock=log_geometry([t for t in r['normalized_trades']
                    if t['bar_path_status']=='bar_path_skipped_holdout_lock']),
                bar_path_skipped_rows=[t['row'] for t in r['normalized_trades']
                    if t['bar_path_status']=='bar_path_skipped_holdout_lock'],
                profile_sim={k:v['ftmo_rule_breach_sim'] for k,v in r['profiles'].items()},
                toxicity=r['behavioral_toxicity']))
            if d['status'] in (SWING,BOTH):
                blueprints.append(dict(file=file.name,sha256=digest,**blueprint(r)))
        except (ValueError,OSError,KeyError,TypeError) as exc:
            reason=str(exc) if type(exc) is ValueError and str(exc).replace('_','').isupper() else type(exc).__name__
            leaders.append(dict(file=file.name,status=UNKNOWN,score=None,
                                evidence_gaps=[{'code':reason}],confirmed_rejections=[]))
    p={BOTH:0,SWING:0,UNKNOWN:1,REJECTED:2}
    ranked=sorted(leaders,key=lambda x:(p[x['status']],-(x['score'] or 0),x['file']))
    rank=0
    for row in ranked:
        if row['score'] is not None:
            rank+=1
            row['rank']=rank
        else:
            row['rank']=None
    blueprints.sort(key=lambda item:next(r['rank'] for r in ranked if r['file']==item['file']))
    return ranked,blueprints


def write_results(out, leaders, blueprints):
    out.mkdir(parents=True,exist_ok=False)
    payloads={
        'FTMO_LIVE_CANDIDATE_LEADERBOARD':{'records':leaders,'allocation':{'Swing':80,'Standard':20},
            'score_basis':'0.8*worst Swing base return pct/month + 0.2*worst eligible Standard base return pct/month; no Standard credit if unresolved',
            'scope':'SAMPLED HISTORICAL MODEL ON PROVIDED TRADES; CANDIDATE FOR RESEARCH'},
        'BEHAVIORAL_BLUEPRINT':{'records':blueprints,'scope':'DESCRIPTIVE; NO STRATEGY RECONSTRUCTION'}
    }
    for stem,pack in payloads.items():
        text=json.dumps(pack|{'order_send_count':0},indent=2,ensure_ascii=False,allow_nan=False)+'\n'
        (out/(stem+'.json')).write_text(text,encoding='utf-8',newline='\n')
    head=['# FTMO live candidate leaderboard','',
          '| Rank | Log | Status | Score | Reasons |','| --- | --- | --- | --- | --- |']
    def safe(s):
        return str(s).replace('|','/').replace('<','&lt;').replace('>','&gt;').replace('\n',' ')
    for x in leaders:
        why=[r['code'] for r in x['confirmed_rejections']+x['evidence_gaps']]
        head.append(f"| {x['rank'] or '—'} | {safe(x['file'])} | {x['status']} | "
                    f"{format(x['score'],'.3f') if x['score'] is not None else '—'} | {', '.join(dict.fromkeys(why))} |")
    if not leaders:
        head+=['','Inbox has no eligible CSV/HTML/HTM inputs.']
    head+=['','See JSON for Standard calendar/news findings, coverage and scenario details.']
    (out/'FTMO_LIVE_CANDIDATE_LEADERBOARD.md').write_text('\n'.join(head)+'\n',encoding='utf-8',newline='\n')
    md=['# Behavioral blueprints','']
    for x in blueprints:
        md.extend([f"## {safe(x['file'])}",'',
                   f"- Audited FTMO symbol coverage: {x['audited_ftmo_symbol_trade_share']:.1%}.",
                   f"- Holding time median: {x['hold_hours']['median']:.2f}h.",
                   f"- Cadence: {x['trades_per_calendar_month']:.2f} trades per calendar month.",
                   '- Top instruments: '+', '.join(f"{s} {t['trade_share']:.1%}" for s,t in sorted(
                         x['assets'].items(),key=lambda p:-p[1]['trade_share'])[:5])+'.',''])
    if not blueprints:
        md.append('No candidate passed the evidence and risk checks.')
    md.extend(['','See JSON for the symbol attribution, UTC sessions, holding quantiles, stop/target geometry and winner taxonomy.'])
    (out/'BEHAVIORAL_BLUEPRINT.md').write_text('\n'.join(md)+'\n',encoding='utf-8',newline='\n')


def run_batch(args):
    if not args.source.is_dir():
        raise ValueError('LEADERBOARD_INPUT_DIRECTORY_REQUIRED')
    files=sorted(p for p in args.source.iterdir() if p.is_file() and p.suffix.lower() in FORMATS
                 and not p.name.lower().startswith(('readme','template')))
    market=Market(args.market_store)
    news=news_file(args.news_calendar)
    calendar=sessions(args.calendar)
    pair_payload=read_json_file(args.paired_continuation) if args.paired_continuation else None
    try:
        r,b=audit_batch(files,market,calendar,news,timezone_name=args.timezone,date_order=args.date_order,
                        decimal_mark=args.decimal_mark,volume_lots=args.volume_lots,stop_is_initial=args.stop_is_initial,
                        profit_basis=args.profit_basis,currency=args.currency,pair_payload=pair_payload)
    finally:
        market.close()
    write_results(args.leaderboard_dir,r,b)
    print(json.dumps({'reports':len(r),'passed':len(b),'order_send_count':0}))
    return 0
