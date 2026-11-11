"""Read sealed native intraday annual books; no simulation or parameter selection."""
from collections import Counter
from datetime import datetime,timezone
from decimal import Decimal as D
import json
from pathlib import Path
import time
from zoneinfo import ZoneInfo

from forex_screen_diagnostics import decimal,digest
from sealed_m1_review import cash_sessions


def maximum_zero_run(values):
    longest=current=0
    for n in values:
        current=current+1 if not n else 0
        longest=max(longest,current)
    return longest


def book_fit(book, *, year, calendar_days, starting_balance):
    """Percentages need an explicit source-book capital; invalid capital stays unknown."""
    zone=ZoneInfo('America/New_York')
    vn=ZoneInfo('Asia/Ho_Chi_Minh')
    try:
        capital=decimal(starting_balance)
        if capital<=0:capital=None
    except (ValueError,TypeError):
        capital=None
    if not calendar_days or len(calendar_days)!=len(set(calendar_days)) or calendar_days!=sorted(calendar_days):
        raise ValueError('fit_calendar_order_duplicates')
    if any(datetime.fromisoformat(day).year!=year for day in calendar_days):
        raise ValueError('fit_calendar_year_scope')
    trades=book['trades']
    days=Counter({day:0 for day in calendar_days})
    weeks=Counter({datetime.fromisoformat(day).date().isocalendar()[:2]:0 for day in calendar_days})
    months={m:dict(month=f'{year}-{m:02}',trades=0,net=D(0)) for m in range(1,13)}
    nets=[]
    risks=[]
    holding=[]
    local_entry=[]
    streak=longest_streak=0
    cumulative=peak=dd=D(0)
    dd_pct=D(0) if capital else None
    prior=-1
    intraday=True
    for trade in trades:
        entry=trade['entry_time']
        if type(entry) is not int or entry<=prior:
            raise ValueError('fit_trade_order_duplicate')
        prior=entry
        at=datetime.fromtimestamp(entry//1000,zone)
        end=datetime.fromtimestamp(trade['exit_ns']//1000000000,zone)
        if at.year!=year or at.date().isoformat() not in days or trade['exit_ns']<=entry*1000000:
            raise ValueError('fit_trade_clock_scope')
        intraday=intraday and at.date()==end.date()
        # Annual book consumers cannot silently book a next-year exit into December.
        if end.year!=year:
            raise ValueError('fit_cross_year_close_not_supported')
        day=at.date().isoformat()
        days[day]+=1
        weeks[at.date().isocalendar()[:2]]+=1
        value=decimal(trade['cash_net'])
        nets.append(value)
        months[end.month]['trades']+=1
        months[end.month]['net']+=value
        risk=trade.get('planned_risk')
        try:
            risk=decimal(risk)
            if risk<=0:risk=None
        except (ValueError,TypeError):risk=None
        risks.append(risk)
        holding.append(D(trade['exit_ns']-entry*1000000-1)/D(60000000000))
        local=datetime.fromtimestamp(entry//1000,vn)
        local_entry.append(((local.date()-at.date()).days,local.strftime('%H:%M')))
        streak=streak+1 if value<0 else 0
        longest_streak=max(longest_streak,streak)
        cumulative+=value
        peak=max(peak,cumulative)
        drop=peak-cumulative
        dd=max(dd,drop)
        if capital:dd_pct=max(dd_pct,drop/(capital+peak)*100)
    unresolved=sum(bool(t['unresolved']) for t in trades)+int(book['position'] is not None)
    full_known=unresolved==0
    balance=capital
    monthly=[]
    for m in range(1,13):
        row=months[m]
        rate=row['net']/balance*100 if balance and balance>0 else None
        monthly.append(dict(row,starting_balance=balance,modeled_closed_balance_return_pct=rate,
                            full_intraday_month_return_pct=rate if full_known and intraday else None))
        if balance is not None:balance+=row['net']
    if capital and balance!=decimal(book['decimal_cash']):
        raise ValueError('fit_closed_balance_reconciliation')
    endpoint=book.get('endpoint_equity_dd')
    endpoint=None if endpoint is None else decimal(endpoint)
    if endpoint is not None and endpoint+D('.01')<dd:
        raise ValueError('fit_endpoint_dd_smaller_than_closed_dd')
    winners=[x for x in nets if x>0]
    losers=[x for x in nets if x<0]
    gain=sum(winners,D(0))
    loss=-sum(losers,D(0))
    avg_win=gain/len(winners) if winners else None
    avg_loss=loss/len(losers) if losers else None
    risk_known=bool(risks) and all(r is not None for r in risks)
    return dict(year=year,trades=len(trades),scheduled_sessions=len(days),scheduled_iso_weeks=len(weeks),
        days_with_trade=sum(x>0 for x in days.values()),days_without_trade=sum(x==0 for x in days.values()),
        max_trades_per_day=max(days.values(),default=0),max_no_trade_scheduled_session_run=maximum_zero_run(days.values()),
        weekly_distribution=dict(sorted(Counter(weeks.values()).items())),weeks_in_proposed_3_to_8_band=sum(3<=x<=8 for x in weeks.values()),
        weekly_mean=D(len(trades))/len(weeks) if weeks else None,monthly=monthly,
        net_usd=cumulative,full_net_usd=cumulative if full_known else None,
        return_on_source_initial_pct=cumulative/capital*100 if capital and full_known else None,
        modeled_closed_balance_dd_usd=dd,modeled_closed_balance_dd_peak_pct=dd_pct,
        recorded_endpoint_equity_dd_usd=endpoint,
        endpoint_dd_amount_as_pct_initial=endpoint/capital*100 if endpoint is not None and capital else None,
        full_intraminute_equity_dd_pct=None,full_prop_breach_validation=False,
        winrate_pct=D(len(winners))/len(trades)*100 if trades else None,wins=len(winners),losses=len(losers),
        winning_net_pool_usd=gain,losing_net_pool_usd=loss,net_profit_factor=gain/loss if loss else None,
        average_win_usd=avg_win,average_loss_usd=avg_loss,realized_average_win_loss_ratio=avg_win/avg_loss if avg_win and avg_loss else None,
        mean_net_usd_per_trade=cumulative/len(trades) if trades else None,longest_closed_loss_streak=longest_streak,
        mean_net_R_per_trade=sum((n/r for n,r in zip(nets,risks)),D(0))/len(nets) if risk_known else None,
        max_planned_risk_usd=max(risks) if risk_known else None,
        max_planned_risk_pct_initial=max(risks)/capital*100 if risk_known and capital else None,
        mean_modeled_hold_minutes=sum(holding,D(0))/len(holding) if holding else None,
        max_modeled_hold_minutes=max(holding) if holding else None,intraday_all_closed=intraday,
        entry_vn_session_relative_first=dict(zip(('day_offset_from_NY_session','clock'),min(local_entry))) if local_entry else None,
        entry_vn_session_relative_last=dict(zip(('day_offset_from_NY_session','clock'),max(local_entry))) if local_entry else None,
        clock_scope='historical_DST_conversion_not_future_schedule',unresolved=unresolved,
        return_scope='annual_reset_books_no_external_flows;zero_trade_months_retained')


def main():
    import argparse
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--run',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--starting-balance',required=True)
    args=p.parse_args()
    if decimal(args.starting_balance)!=10000:
        raise ValueError('fit_registered_R123_capital_is_10000')
    if (args.run/'controller.lock').exists():raise ValueError('fit_run_still_owned')
    began=time.perf_counter()
    result=json.loads((args.run/'result.json').read_text(encoding='utf-8'))
    if result['status']!='completed_exploratory_cost_screen_not_qualified' or len(result['rows'])!=9:
        raise ValueError('fit_expected_completed_R123_screen')
    expected={(y,s) for y in (2022,2023,2024) for s in ('reference','stress','null')}
    if {(r['year'],r['scenario']) for r in result['rows']}!=expected or any(r['candidate']!='R123' for r in result['rows']):
        raise ValueError('fit_unique_year_scenario_census')
    paths=(Path(__file__),Path(__file__).with_name('forex_screen_diagnostics.py'),Path(__file__).with_name('sealed_m1_review.py'),
           args.run/'result.json',args.run/'manifest.json')
    bindings={str(path.resolve()):digest(path) for path in paths}
    reports=[]
    for row in result['rows']:
        year,scenario=row['year'],row['scenario']
        if year not in (2022,2023,2024):raise ValueError('fit_development_year_only')
        name=f'{year}-R123-{scenario}'
        book_path=args.run/(name+'.json')
        review_path=args.run/(name+'-review.json')
        seal_path=args.run/(name+'-seal.json')
        seal=json.loads(seal_path.read_text(encoding='utf-8'))
        if digest(book_path)!=seal['result_sha256'] or digest(review_path)!=seal['review_sha256'] or digest(args.run/'manifest.json')!=seal['manifest_sha256']:
            raise ValueError('fit_durable_seal_binding')
        review=json.loads(review_path.read_text(encoding='utf-8'))
        if review['status']!='verified_execution_cash_only':raise ValueError('fit_prior_execution_review_missing')
        book=json.loads(book_path.read_text(encoding='utf-8'))
        admission_path=args.run/f'input-{year}.json'
        admission=json.loads(admission_path.read_text(encoding='utf-8'))
        matches=[Path(name) for name,sha in admission['bindings'].items() if Path(name).name.endswith(f'-nyse-{year}.json') and 'source-snapshot' in name and digest(name)==sha]
        if len(matches)!=1:raise ValueError('fit_frozen_calendar_binding')
        calendar_path=matches[0]
        days=list(cash_sessions(json.loads(calendar_path.read_text(encoding='utf-8'))))
        for path in (book_path,review_path,seal_path,admission_path,calendar_path):bindings[str(path.resolve())]=digest(path)
        report=book_fit(book,year=year,calendar_days=days,starting_balance=args.starting_balance)
        if report['net_usd']!=decimal(row['sides']['combined']['modeled_closed_net_usd']):raise ValueError('fit_saved_metrics_reconciliation')
        reports.append(dict(candidate='R123',scenario=scenario,**report))
    if any(digest(name)!=sha for name,sha in bindings.items()):raise ValueError('fit_binding_drift')
    args.output.mkdir(exist_ok=False)
    out=dict(status='completed_descriptive_fit_review_not_qualification',reports=reports,bindings=bindings,
        scope='saved_ledgers_and_frozen_calendars_only_no_financial_replay_or_new_trial',wall_seconds=time.perf_counter()-began)
    snapshots=args.output/'source-snapshot'
    snapshots.mkdir()
    for i,path in enumerate((Path(__file__),Path(__file__).with_name('forex_screen_diagnostics.py'),Path(__file__).with_name('sealed_m1_review.py'))):
        (snapshots/f'{i:02}-{path.name}').write_bytes(path.read_bytes())
    (args.output/'result.json').write_text(json.dumps(out,ensure_ascii=False,default=str,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(dict(status=out['status'],reviewed_books=len(reports),wall_seconds=out['wall_seconds'])))


if __name__=='__main__':main()
