"""Offline Bot Lab intake and FTMO scorecard. No terminal or order API."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict
from dataclasses import asdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
from math import isclose, isfinite
from statistics import mean, median

from forex_screen_diagnostics import adverse_budget
from quant_core.ftmo_track_replay import (BALANCES, STOP, Market, calendar_warnings, observe_path,
                                         position, profiles, read_json_file, replay, sessions)
from quant_core.live_trade_log import SUFFIXES, normalize
from quant_core.native_paths import read_bounded
from selective_win_diagnosis import LABELS, UNKNOWN, classify

ROOT=Path(__file__).resolve().parents[2]
INBOX=ROOT/'research/bot_reverse_lab/inbox/live_signals'
LIMIT=16*1024*1024


def outcomes(trades):
    sources={}
    for basis, pick in (('net_money',lambda t:t.net_profit),('reported_R',lambda t:t.reported_r),
                        ('reported_profit',lambda t:t.profit)):
        groups=defaultdict(list)
        for t in trades:
            val=pick(t)
            if val is not None:
                if basis=='reported_R':
                    unit='R'
                else:
                    unit=t.profit_currency or 'UNKNOWN_ACCOUNT_CURRENCY'
                groups[unit].append((t,val))
        sources[basis]=groups
    return sources


def metrics(rows):
    a=[v for _,v in rows]
    if not a:
        return None
    wins=sorted((x for x in a if x>0),reverse=True)
    losses=[-x for x in a if x<0]
    pool=sum(wins)
    months=Counter()
    for t,v in rows:
        observed = t.open_date if t.time_basis=='journal_timestamp' else t.close_date
        if observed:
            months.setdefault(observed[:7],0.)
            months[observed[:7]]+=max(0.,v)
    return dict(n=len(a), wins=len(wins), losses=len(losses), breakeven=sum(x==0 for x in a),
                winrate=len(wins)/len(a), sum=sum(a), mean=mean(a), median=median(a),
                avg_win=mean(wins) if wins else None, avg_loss=mean(losses) if losses else None,
                avg_loss_over_avg_win=mean(losses)/mean(wins) if wins and losses else None,
                top2_profit_share=sum(wins[:2])/pool if pool else None,
                top5_profit_share=sum(wins[:5])/pool if pool else None,
                top10_profit_share=sum(wins[:10])/pool if pool else None,
                ex_top2=sum(a)-sum(wins[:2]), ex_top5=sum(a)-sum(wins[:5]),
                largest_month_profit_share=max(months.values())/pool if pool and len(months)>=2 else None,
                monthly_time_basis='JOURNAL_DATE_OR_REPORTED_CLOSE_DATE', months_observed=len(months))


def behavior(trades, sources, market, specs):
    dated=sorted((t for t in trades if t.time_basis=='reported_fill' and t.open_time is not None),
                 key=lambda t:(t.open_time,t.row))
    sleeves=defaultdict(list)
    for t in dated:
        sleeves[t.symbol].append(t)
    escalations=[]
    streak_checks=0
    grid=[]
    grid_unknown=0
    overlap_checks=0
    for symbol,rows in sleeves.items():
        closed=sorted((t for t in rows if t.has_execution_clock and t.open_time<t.close_time),
                      key=lambda t:(t.close_time,t.row))
        exits=[t.close_time for t in closed]
        active=[]
        for t in rows:
            last=bisect_left(exits,t.open_time)
            if last>=2 and t.lots is not None and t.open_time>exits[last-1]>exits[last-2]:
                a,b=closed[last-2:last]
                def value(x):
                    return x.net_profit if x.net_profit is not None else x.reported_r
                x,y=value(a),value(b)
                if x is not None and y is not None and b.lots is not None:
                    streak_checks+=1
                    if x<0 and y<0 and t.lots>=1.5*b.lots:
                        escalations.append(dict(row=t.row,previous=b.row,lot_multiple=t.lots/b.lots))
            active=[x for x in active if x.close_time is None or x.close_time>t.open_time]
            for p in active:
                if t.direction is None or p.direction!=t.direction or p.open_time==t.open_time:
                    continue
                if p.close_time is None or p.open_price is None or symbol not in specs or t.open_time%60000:
                    grid_unknown+=1
                    continue
                mark=market.bid(symbol,t.open_time)
                if mark is None:
                    grid_unknown+=1
                    continue
                overlap_checks+=1
                exit_mark=mark if p.direction=='BUY' else mark+specs[symbol]['spread_price_proxy']
                if (exit_mark-p.open_price)*(1 if p.direction=='BUY' else -1)<0:
                    grid.append(dict(row=t.row,prior_open_row=p.row,estimated_liquidation_price=exit_mark))
            active.append(t)
    stops=[t.sl for t in trades if t.sl is not None]
    explicit_zero=sum(x==0 for x in stops)
    rows=next((v for k in ('net_money','reported_R','reported_profit') for v in sources[k].values()
               if len(v)==len(trades)),[])
    series=metrics(rows)
    ratio=series['avg_loss_over_avg_win'] if series else None
    fl=bool(series and series['n']>=10 and (
        (series['top2_profit_share'] or 0)>.50 or (series['top5_profit_share'] or 0)>.70 or
        (series['largest_month_profit_share'] or 0)>.80))
    no_sl=explicit_zero>0 or (ratio is not None and ratio>=3 and len(rows)>=10)
    return {
        'HIDDEN_MARTINGALE_LOT_ESCALATION': dict(status='FLAG' if escalations else
            'NO_FLAG_IN_OBSERVED_CONTEXT' if streak_checks else 'UNKNOWN',evidence=escalations,assessed=streak_checks,
            rule='Two strictly settled losses in same symbol and current lot >=1.5x last loss lot'),
        'HIDDEN_GRID_AVERAGING_DOWN':dict(status='FLAG_AT_BID_PROXY' if grid else
            'NO_FLAG_IN_OBSERVED_CONTEXT' if overlap_checks and not grid_unknown else 'UNKNOWN',
            evidence=grid,assessed=overlap_checks,overlaps_without_mark_or_clock=grid_unknown),
        'NO_HARD_SL_OR_WIDE_STOP_GAMBLING':dict(status='FLAG' if no_sl else
            'NO_FLAG_IN_OBSERVED_CONTEXT' if stops and len(stops)==len(trades) and ratio is not None else 'UNKNOWN',
            observed_sl=len(stops),missing_sl=len(trades)-len(stops),explicit_no_sl=explicit_zero,
            explicit_no_sl_share=explicit_zero/len(stops) if stops else None,
            avg_loss_over_avg_win=ratio,loss_size_flag_min_ratio=3.,
            wide_stop_geometry='REQUIRES_INITIAL_STOP_AND_ADMITTED_PATH'),
        'CONCENTRATED_LOTTERY_PROFILE':dict(status='FLAG' if fl else
            'NO_FLAG_IN_OBSERVED_CONTEXT' if series and series['n']>=10 and series['wins'] else 'UNKNOWN',
            metrics=series, min_trades=10, top2_limit=.50,top5_limit=.70, top_month_limit=.80),
    }


def cash_attribution(parts):
    vals={k:Decimal(str(v)) for k,v in parts.items()}
    return adverse_budget({k:max(-v,0) for k,v in vals.items()},
                          {k+'_credit':max(v,0) for k,v in vals.items()},net=sum(vals.values()))


def loss_diagnosis(trades, prepared):
    losses=[]; sum_components=defaultdict(float)
    for t in trades:
        p,path=prepared[t.row]
        if p is None or p['net']>=0 or t.lots is None:
            continue
        losses.append(t.row)
        for k,v in (('fill_gross',p['gross']),('commission',-p['open_commission']-p['close_commission']),
                    ('swap',p['swap'])):
            sum_components[k]+=t.lots*v
    return dict(status='VALUED_LOSS_SUBSET' if losses else 'UNKNOWN_NO_VALUED_LOSERS',loss_rows=losses,
                components_usd=dict(sum_components), attribution=cash_attribution(sum_components) if losses else None)


def excursion_summary(rows):
    """Use net MFE after round-trip costs. Include losers and keep coverage visible."""
    def part(rows):
        marks=[r for r in rows if r['mfe_R'] is not None and r['mae_R'] is not None]
        winners=[r for r in marks if r['net_R']>0 and r['mfe_R']>0]
        outcome=[r['net_R'] for r in rows]
        def med(field):
            return median(r[field] for r in marks) if marks else None
        ideal=sum(r['mfe_R'] for r in marks)
        return dict(n=len(rows),path_n=len(marks), path_coverage=len(marks)/len(rows) if rows else None,
                    net_R=sum(outcome) if outcome else None, mae_median_R=med('mae_R'),mfe_median_R=med('mfe_R'),
                    n_net_mfe_le_zero=sum(r['mfe_R']<=1e-12 for r in marks),
                    net_mfe_le_zero_share=sum(r['mfe_R']<=1e-12 for r in marks)/len(marks) if marks else None,
                    median_capture_positive_peak=median(r['net_R']/r['mfe_R'] for r in marks if r['mfe_R']>0)
                    if any(r['mfe_R']>0 for r in marks) else None,
                    realised_over_net_peak_pool=sum(r['net_R'] for r in marks)/ideal if ideal>0 else None,
                    median_winner_capture=median(r['net_R']/r['mfe_R'] for r in winners) if winners else None,
                    median_giveback_R=median(r['mfe_R']-r['net_R'] for r in marks) if marks else None,
                    favourable_peak_then_loss=sum(r['mfe_R']>1e-12 and r['net_R']<0 for r in marks))
    return {k:part([r for r in rows if pred(r['net_R'])]) for k,pred in (
        ('all',lambda _:True),('win',lambda n:n>0),('loss',lambda n:n<0),('flat',lambda n:n==0))}


def leakage(cases, *, raw=None, paired=None):
    stats=excursion_summary(cases)
    marked=stats['all']['path_n']
    if raw is not None and paired is not None and paired['delta_R']['gross']<0 and not raw['gate']:
        verdict='ENTRY_OR_HOLD_HORIZON_DEFICIT_AND_MEASURED_GIVEBACK'
    elif raw is not None and not raw['gate']:
        verdict='RAW_EDGE_NOT_ESTABLISHED_WITH_OBSERVED_GIVEBACK' if marked else 'RAW_EDGE_NOT_ESTABLISHED'
    elif marked:
        verdict='EXIT_GIVEBACK_DESCRIPTIVE_ENTRY_EDGE_UNIDENTIFIED'
    else:
        verdict='UNKNOWN_PATH_AND_ENTRY_BENCHMARK'
    return dict(verdict=verdict,cohorts=stats,raw_fixed_horizon=raw,paired_exit=paired,
                optimal_exit_profit_is_hindsight=True, raw_proof_requires_controlled_same_entry_exit_comparison=True)


def profile_report(trades,specs,market,name,calendar,pairs=None):
    prepared={}
    rows=[]
    winners=Counter({k:0 for k in (*LABELS,UNKNOWN)})
    winner_profit=Counter({k:0. for k in (*LABELS,UNKNOWN)})
    original=defaultdict(float)
    original_count=0
    for t in trades:
        sp=specs.get(t.symbol)
        p=position(t,sp,market)
        path=observe_path(t,sp,market,p) if p else None
        prepared[t.row]=(p,path)
        if p is not None and t.lots is not None:
            original_count+=1
            for k in ('gross','swap','net'):
                original[k]+=p[k]*t.lots
            original['commission']+=(p['open_commission']+p['close_commission'])*t.lots
        label=None
        realized_R=None
        if p is not None and p['risk'] is not None:
            risk=p['risk']
            realized_R=p['net']/risk
            calendar_exit=t.exit_reason=='CALENDAR_CUTOFF'
            alternative=(pairs or {}).get(str(t.row),{})
            matched=calendar_exit and alternative.get('entry_utc_msc')==t.open_time and (
                alternative.get('exit_utc_msc',0)>t.close_time) and isclose(
                alternative.get('risk_per_lot_usd',0.),risk,rel_tol=1e-9)
            alternative_R=alternative.get('net_R') if matched else None
            item={'net_R':realized_R,'swap_R':p['swap']/risk,
                  'mfe_R':path['mfe']/risk if path else None,'mae_R':path['mae']/risk if path else None,
                  'holding_hours':(t.close_time-t.open_time)/3600000,'calendar_exit':calendar_exit,
                  'paired_net_R':alternative_R}
            # Incomplete marks are useful for the coverage inventory. Only full
            # interior-M1 paths can certify a path-dependent winner label.
            if not path or not path['complete']:
                item['mfe_R']=item['mae_R']=None
            label=classify(item)
            rows.append(dict(row=t.row,**item,peak_hours=path['peak_hours'] if path else None,
                             capture_efficiency=item['net_R']/item['mfe_R'] if item['net_R']>0 and item['mfe_R'] else None,
                             winner_label=label, path_basis='POST_ENTRY_PROXY_M1_DEV'))
        elif (t.net_profit is not None and t.net_profit>0) or (t.reported_r is not None and t.reported_r>0) or (
                t.outcome=='WIN' and t.net_profit is None and t.reported_r is None):
            label=UNKNOWN
            rows.append(dict(row=t.row,winner_label=label,path_basis='UNKNOWN_REALIZED_TRADE_RISK_OR_PATH'))
        if label:
            winners[label]+=1
            if realized_R is not None:
                winner_profit[label]+=realized_R
    valued=[x for x in rows if 'net_R' in x]
    overall=leakage(valued)
    mfes=[x['mae_R'] for x in valued if x['mae_R'] is not None]
    wins=[x['net_R'] for x in valued if x['net_R']>0]
    tail_ratio=max(mfes)/mean(wins) if mfes and wins else None
    report=dict(spec_symbols=len(specs),supported_trades=sum(t.symbol in specs for t in trades),
            target_reprice=dict(status='REPRICED_FILL_SUBSET' if original_count else 'UNKNOWN_MISSING_FILLS_LOTS_OR_CONVERSION',
                trades=original_count,totals_usd=dict(original) if original_count else None,
                basis='fill-to-fill price PnL with embedded spread; apply target commission and snapshot swap once'),
            winner_diagnosis=dict(counts=dict(winners),valued_positive_R=dict(winner_profit),rows=rows),
            loss_diagnosis=loss_diagnosis(trades,prepared),entry_exit_decomposition=overall,
            adverse_excursion=dict(valued_paths=len(mfes),max_MAE_over_mean_net_winner_R=tail_ratio,
                flag=tail_ratio>=5 if tail_ratio is not None and len(mfes)>=10 and len(wins)>=3 else None),
            ftmo_rule_breach_sim=[replay(trades,prepared,specs,b,f) for b in BALANCES[name] for f in (.005,.01)])
    report['calendar']=calendar_warnings(trades,calendar,specs) if name=='Standard' else dict(
        status='LONG_BREAK_RULE_EXCEPTION_FOR_SWING', applies_to='SWING')
    return report


def load_pairs(payload, input_sha, bindings):
    if payload is None:
        return {}
    if (payload.get('input_sha256')!=input_sha or not payload.get('source') or
            payload.get('basis')!='SAME_ENTRY_INITIAL_RISK_AND_TARGET_COSTS' or
            payload.get('profile_sha256_lf')!={k:v['sha256_lf'] for k,v in bindings.items()}):
        raise ValueError('PAIRED_CONTINUATION_BINDING_MISMATCH')
    cases=payload['profiles']
    for cases_by_row in cases.values():
        for item in cases_by_row.values():
            a,b=item['entry_utc_msc'],item['exit_utc_msc']
            if (not isinstance(a,int) or not isinstance(b,int) or not 0<=a<b<STOP or
                    not isfinite(item['risk_per_lot_usd']) or item['risk_per_lot_usd']<=0 or not isfinite(item['net_R'])):
                raise ValueError('PAIRED_CONTINUATION_OUTSIDE_DEV_OR_INVALID')
    return cases


def audit(raw,suffix,*,market=None,calendar=None,pair_payload=None,include_rows=False,**normalizer):
    trades,meta=normalize(raw,suffix,**normalizer)
    market=market or Market()
    specs,bindings=profiles()
    input_sha=sha256(raw).hexdigest()
    pairs=load_pairs(pair_payload,input_sha,bindings)
    sources=outcomes(trades)
    derived={k:{unit:metrics(v) for unit,v in group.items()} for k,group in sources.items()}
    by_asset=defaultdict(list)
    for t,v in sources['reported_R'].get('R',[]):
        by_asset[t.symbol].append((t,v))
    report=dict(schema='BotLabLiveTrackAudit-v1',input_sha256=input_sha,normalization=meta,order_send_count=0,
            observed=dict(assets=dict(Counter(t.symbol for t in trades)),direction=dict(Counter(t.direction or 'UNKNOWN' for t in trades)),
                journal_labels=dict(Counter(t.outcome or 'UNKNOWN' for t in trades)),metrics=derived,
                reported_R_by_asset={k:metrics(v) for k,v in by_asset.items()},
                observed_date_min=min((t.open_date for t in trades if t.open_date),default=None),
                observed_date_max=max((t.open_date for t in trades if t.open_date),default=None)),
            behavioral_toxicity=behavior(trades,sources,market,specs['Swing']),allocation={'Swing':80,'Standard':20},
            profile_bindings=bindings,profiles={k:profile_report(trades,v,market,k,calendar,pairs.get(k)) for k,v in specs.items()},
            data_policy='Observed log rows are descriptive; only explicitly bound pre-2025 market stores can be read.',
            threshold_policy='2-Step 5% Prague balance-based daily and 10% static, strict below floor. No payout qualification.')
    scenarios=[v for k in report['profiles'].values() for v in k['ftmo_rule_breach_sim']]
    observed=[v['status'] for v in scenarios if v['daily_breach_observed'] or v['overall_breach_observed']]
    standard_calendar=report['profiles']['Standard']['calendar']['status']
    status=('BREACH_INDICATION' if observed or standard_calendar=='FUNDED_STANDARD_LONG_BREAK_OBSERVED' else
            'NO_BREACH_AT_SAMPLED_MARKS' if all(v['status']=='NO_BREACH_AT_SAMPLED_MARKS' for v in scenarios)
            else 'UNKNOWN')
    report['behavioral_toxicity']['FTMO_RULE_BREACH_SIM']=dict(status=status,
        scenarios=len(scenarios), scenarios_with_observed_breach=len(observed),
        standard_funded_session=standard_calendar)
    if any(v['adverse_excursion']['flag'] for v in report['profiles'].values()):
        report['behavioral_toxicity']['NO_HARD_SL_OR_WIDE_STOP_GAMBLING']['status']='FLAG'
    if include_rows:
        report['normalized_trades']=[asdict(t) for t in trades]
    return report


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('source',type=Path,nargs='?',default=INBOX,help='CSV/HTML/XML or an inbox directory')
    p.add_argument('--output',type=Path)
    p.add_argument('--timezone')
    p.add_argument('--date-order',choices=('dmy','mdy'))
    p.add_argument('--decimal-mark',choices=('.',','),default='.')
    p.add_argument('--volume-lots',action='store_true')
    p.add_argument('--stop-is-initial',action='store_true')
    p.add_argument('--profit-basis',choices=('reported','net','gross'),default='reported')
    p.add_argument('--currency')
    p.add_argument('--market-store',type=Path)
    p.add_argument('--calendar',type=Path)
    p.add_argument('--paired-continuation',type=Path)
    p.add_argument('--include-rows',action='store_true',help='Only for private JSON output')
    a=p.parse_args()
    if a.include_rows and a.output is None:
        p.error('Use private --output for --include-rows')
    if a.output is not None and a.output.suffix.lower()!='.json':
        p.error('--output requires a JSON destination')
    try:
        if a.timezone:
            from zoneinfo import ZoneInfo
            ZoneInfo(a.timezone)
        paths=sorted(q for q in a.source.iterdir() if q.suffix.lower() in SUFFIXES and q.is_file()) if a.source.is_dir() else [a.source]
        market=Market(a.market_store)
        calendar=sessions(a.calendar)
        pair=read_json_file(a.paired_continuation) if a.paired_continuation else None
        reports=[];errors=[]
        for path in paths:
            try:
                if path.suffix.lower() not in SUFFIXES:
                    raise ValueError('CSV_HTML_XML_INPUT_REQUIRED')
                raw=read_bounded(path,LIMIT)
                r=audit(raw,path.suffix.lower(),market=market,calendar=calendar,pair_payload=pair,timezone_name=a.timezone,
                        date_order=a.date_order,decimal_mark=a.decimal_mark,volume_lots=a.volume_lots,
                        stop_is_initial=a.stop_is_initial,profit_basis=a.profit_basis,currency=a.currency,include_rows=a.include_rows)
                reports.append({'file':path.name,'audit':r})
            except (ValueError,OSError,KeyError) as exc:
                # Provider text, credentials and arbitrary paths do not enter error receipts.
                reason=str(exc) if isinstance(exc,ValueError) and str(exc).replace('_','').isupper() else type(exc).__name__
                errors.append({'file':path.name,'error':reason})
        payload={'schema':'BotLabAuditBatch-v1','reports':reports,'errors':errors,'order_send_count':0,
                 'input_count':len(paths)}
        if a.output:
            a.output.parent.mkdir(parents=True,exist_ok=True)
            with a.output.open('x',encoding='utf-8',newline='\n') as stream:
                json.dump(payload,stream,ensure_ascii=False,indent=2,allow_nan=False)
                stream.write('\n')
            print(json.dumps({'reports':len(reports),'errors':len(errors),'order_send_count':0}))
        else:
            print(json.dumps(payload,ensure_ascii=False,allow_nan=False))
        return 2 if errors else 0
    except (ValueError,OSError,KeyError) as exc:
        print(json.dumps({'status':'AUDIT_INCOMPLETE','error':type(exc).__name__,'order_send_count':0}))
        return 2


if __name__=='__main__':
    raise SystemExit(main())
