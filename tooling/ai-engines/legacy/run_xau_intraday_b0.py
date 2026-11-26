"""Registered A0 only, common stress sizing and separate per-leg cost ledgers."""
from collections import Counter,defaultdict
from datetime import datetime,timezone
import json
from pathlib import Path
import time
import os
import platform
import sys

from eurusd_b0_source import digest,write_json
from prepare_xau_intraday_views import RECORD
import xau_intraday_b0 as b0

REASONS=('TP_2R','SL','TIME_STOP_2H','SESSION_CLOSE_1800')


def breakdown(trades,scenario):
    records=[]
    for reason in REASONS:
        ts=[t for t in trades if t['exit_reason']==reason]
        net=sum(round(t['results'][scenario]['conditional_net_usd']*100) for t in ts)
        records.append(dict(reason=reason,trades=len(ts),wins=sum(t['results'][scenario]['conditional_net_usd']>0 for t in ts),
            net_winrate=sum(t['results'][scenario]['conditional_net_usd']>0 for t in ts)/len(ts) if ts else None,
            net_usd=net/100,total_net_r0=net/b0.R0,mean_net_r0=net/b0.R0/len(ts) if ts else None))
    return records


def summarize(year,scenario,days,account,source_counts,censored):
    trades=[t for d in days for t in d['trades']]
    counts=Counter()
    for d in days:counts.update(d['counters'])
    gross=sum(round(t['results'][scenario]['gross_after_spread_usd']*100) for t in trades)
    comm=sum(round(t['results'][scenario]['commission_usd']*100) for t in trades)
    slip=sum(round(t['results'][scenario]['slippage_usd']*100) for t in trades)
    net=sum(round(t['results'][scenario]['conditional_net_usd']*100) for t in trades)
    if gross-comm-slip!=net:raise ValueError('XAU_year_PnL_bridge')
    if not censored and account.cash!=b0.INITIAL+net:raise ValueError('XAU_year_cash_reconciliation')
    from statistics import median
    intents=[i for d in days for i in d['intents']]
    rejected=[i['natural_sl_usd_per_oz'] for i in intents if i['status']=='friction_cap_rejected']
    cost_pass=[i['natural_sl_usd_per_oz'] for i in intents if i['status'] in
               ('accepted','daily_cap_rejected','position_active_rejected','wait_new_bar_rejected','margin_rejected')]
    actual=[t['natural_sl_usd_per_oz'] for t in trades]
    sides=[]
    for side in ('BUY','SELL'):
        ts=[t for t in trades if t['side']==side]
        def total(key):return sum(round(t['results'][scenario][key]*100) for t in ts)/100
        sides.append(dict(side=side,trades=len(ts),gross_after_spread_usd=total('gross_after_spread_usd'),
            commission_usd=total('commission_usd'),slippage_usd=total('slippage_usd'),
            net_usd=total('conditional_net_usd'),total_net_r0=total('conditional_net_usd')/150))
    return dict(year=year,scenario=scenario,role='development' if year<2024 else 'historical_validation_previously_exposed',
        source_counts=source_counts,counters=dict(counts),filled_trades=len(trades),
        closed_cohort_net_usd=net/100,conditional_net_usd=None if censored else net/100,
        mean_net_r0=None if censored or not trades else net/b0.R0/len(trades),
        annual_net_r0=None if censored else net/b0.R0,
        gross_after_spread_usd=gross/100,commission_usd=comm/100,slippage_usd=slip/100,
        sum_lots=sum(t['lot_steps'] for t in trades)/100,
        gross_after_spread_usd_per_lot=gross/sum(t['lot_steps'] for t in trades) if trades else None,
        rejected_SL_median_usd_per_oz=median(rejected) if rejected else None,
        accepted_SL_median_usd_per_oz=median(actual) if actual else None,
        cost_pass_SL_median_usd_per_oz=median(cost_pass) if cost_pass else None,
        exit_breakdown=breakdown(trades,scenario),side_breakdown=sides,
        observed_equity_max_dd_usd=account.max_dd/100,observed_cumulative_r_dd=account.max_dd/b0.R0,
        observed_worst_daily_loss_usd=account.worst_daily_loss/100,
        observed_worst_daily_loss_pct=account.worst_daily_loss/b0.INITIAL*100,
        daily_witness=account.worst_daily_witness,dd_witness=account.max_dd_witness,
        planned_friction_r0_median=median(t['planned_stress_friction_r0'] for t in trades) if trades else None,
        max_realized_loss_r0=max((-t['results'][scenario]['net_r0'] for t in trades),default=0),
        max_daily_fills=max((d['counters'].get('filled_entries',0) for d in days),default=0),
        static_initial_loss_usd=max(0,b0.INITIAL-account.min_equity)/100,
        minimum_equity_usd=account.min_equity/100,peak_equity_usd=account.peak/100,
        monthly_fills={f'{m:02d}':sum(t['day'][5:7]==f'{m:02d}' for t in trades) for m in range(1,13)},
        path_flagged_trades=sum(t['path_gap_gt60s'] for t in trades),censored=censored,
        news_checked=False,target_calendar_verified=False,strict_B0_net=None,prop_status='PROP_UNMEASURED')


def execute(config_path):
    cfg=json.loads(Path(config_path).read_bytes());study=Path(cfg['study']);root=Path(cfg['workspace'])
    out=Path(cfg['output']);out.mkdir(parents=True,exist_ok=False)
    began=time.monotonic();cpu=time.process_time();events=[]
    def event(stage,**fields):
        if (out/'CANCEL').exists():raise InterruptedError('XAU_cancelled')
        if time.monotonic()-began>cfg['deadline_seconds']:raise TimeoutError('XAU_financial_deadline')
        row=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),sequence=len(events)+1,**fields)
        events.append(row);write_json(out/'status.json',row)
        with (out/'events.jsonl').open('a') as f:f.write(json.dumps(row)+'\n')
        print(json.dumps(row),flush=True)
    try:
        if cfg['candidate']!='XAUUSD-Intraday-B0-A0-v1' or cfg['years']!=[2022,2023,2024]:raise ValueError('unregistered_XAU_candidate_or_years')
        import pydantic
        runtime=dict(python=platform.python_version(),executable=sys.executable,pydantic=pydantic.__version__)
        if runtime!=cfg['runtime']:raise ValueError('XAU_frozen_runtime_changed')
        for path,sha in cfg['pins'].items():
            if digest(root/path)!=sha:raise ValueError('XAU_frozen_source_changed:'+path)
        b0.bind_native(root/'projects/trader/foundation_v2')
        tick_view=study/cfg['tick_view'];signals=study/cfg['signal_view']
        seal=json.loads((tick_view/'seal.json').read_bytes())
        if digest(tick_view/'seal.json')!=cfg['tick_seal_sha256']:raise ValueError('tick_source_seal_changed')
        census=json.loads((signals/'census.json').read_bytes())
        candidates=json.loads((signals/'candidates.json').read_bytes())
        if digest(signals/'candidates.json')!=census['signals_sha256']:raise ValueError('candidate_trace_changed')
        if digest(signals/'census.json')!=seal['signal_census_sha256']:raise ValueError('sealed_census_changed')
        event('preflight_passed',pid=os.getpid(),runtime=runtime)
        hours={r['at']:r for r in seal['hours']};byday=defaultdict(list)
        for candidate in candidates:
            if not '2022-01-01'<=candidate['day']<='2024-12-31':raise ValueError('XAU_closed_holdout')
            byday[candidate['day']].append(candidate)
        rows=[];all_trades=[]
        for year in cfg['years']:
            accounts={s:b0.Account() for s in ('reference','stress')};days=[];censored=None
            for day,cs in sorted(byday.items()):
                if int(day[:4])!=year:continue
                quotes=[]
                needed=sorted({c['decision_msc']//b0.HOUR*b0.HOUR+i*b0.HOUR for c in cs for i in range(3)})
                for hour in needed:
                    path=tick_view/(str(hour)+'.ticks')
                    if digest(path)!=hours[hour]['binary_sha256']:raise ValueError('tick_binary_content_changed')
                    raw=path.read_bytes()
                    if len(raw)%RECORD.size:raise ValueError('tick_binary_truncated')
                    quotes.extend(RECORD.iter_unpack(raw))
                if any(b[0]<a[0] for a,b in zip(quotes,quotes[1:])):raise ValueError('tick_day_order')
                d=b0.run_day(day,cs,quotes,accounts);days.append(d)
                if d['unresolved_position'] is not None:
                    censored=dict(day=day,reason='exit_not_confirmed_no_fabricated_flat_or_next_day_reset')
                    event('year_censored',year=year,day=day);break
                if len(days)%25==0:event('year_replay',year=year,candidate_days=len(days),through=day)
            write_json(out/(str(year)+'-details.json'),dict(year=year,days=days,censored=censored))
            all_trades.extend(t for d in days for t in d['trades'])
            for scenario,account in accounts.items():
                row=summarize(year,scenario,days,account,census['yearly'][str(year)],censored)
                rows.append(row)
            event('year_complete',year=year,censored=bool(censored))
        pooled=[]
        for scenario in ('reference','stress'):
            rs=[r for r in rows if r['scenario']==scenario]
            offset=sum(round(r['closed_cohort_net_usd']*100) for r in rs)
            pooled.append(dict(scenario=scenario,exit_breakdown=breakdown(all_trades,scenario),
                closed_cohort_net_usd=offset/100,
                worst_annual_equity_r_dd=max(r['observed_cumulative_r_dd'] for r in rs),
                annual_capital_reset=True,continuous_account_replay=False,
                censored=any(r['censored'] for r in rs)))
        result=dict(schema='XAU-A0-B0-result-v1',rows=rows,pooled=pooled,config_sha256=digest(config_path),
            strict_status='BLOCKED_BY_CALENDAR_AND_TARGET_SPEC',prices2025_2026_read=False,
            B1_used=False,other_alpha_versions_run=False,broker_calls=0,
            runtime=runtime,pid=os.getpid(),
            wall_seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        write_json(out/'result.json',result);event('completed_conditional',result_sha256=digest(out/'result.json'))
        return result
    except BaseException as e:
        import traceback
        write_json(out/'failure.json',dict(type=type(e).__name__,stage=events[-1]['stage'] if events else 'preflight',
            locations=[dict(file=f.filename,line=f.lineno) for f in traceback.extract_tb(e.__traceback__)]))
        raise


if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--config',required=True);a=p.parse_args();execute(a.config)
