"""Frozen cash-opening bracket research with explicit unknown-exposure accounting."""
from datetime import datetime,timezone
from decimal import Decimal as D
import time
from zoneinfo import ZoneInfo

import nasdaq_h4_study as core
from sealed_m1_review import validate_rows

MINUTE=60000
CANDIDATE='nasdaq-cash-opening5-direction-10R-r025-m1-v1'
NY=ZoneInfo('America/New_York')


def valid_pair(pair):
    return pair is not None and all(D(str(pair[1][k]))>=D(str(pair[0][k])) for k in ('open','close'))


def opening_plan(stamps,pairs):
    times=stamps[:5]
    known=times[-1]+MINUTE
    plan=dict(known_at_msc=known,entry_time_msc=known+MINUTE,exit_decision_msc=stamps[-1]-MINUTE,
              scheduled_exit_msc=stamps[-1],side=None,stop=None,status='incomplete_opening_range')
    if not all(valid_pair(pairs.get(t)) for t in times):return plan
    rows=[pairs[t][0] for t in times]
    first,last=D(str(rows[0]['open'])),D(str(rows[-1]['close']))
    side='BUY' if last>first else 'SELL' if last<first else None
    plan.update(side=side,status='signal_ready' if side else 'doji_no_entry',
        stop=min(D(str(r['low'])) for r in rows) if side=='BUY' else max(D(str(r['high'])) for r in rows) if side else None)
    return plan


def validate_inputs(sessions,pairs,*,start,end):
    if (type(start) is not int or type(end) is not int or start%core.DAY or end%core.DAY
            or end<=start or end>1735689600000 or not pairs or not sessions):
        raise ValueError('opening5_window_or_holdout_closed')
    keys=list(pairs)
    if keys!=sorted(set(keys)) or list(sessions)!=sorted(set(sessions)):
        raise ValueError('unordered_opening5_inputs')
    for side in [0,1]:
        if any(len(pair)!=2 for pair in pairs.values()):raise ValueError('missing_source_side')
        validate_rows([pair[side] for pair in pairs.values()],start,end,.001)
        if any(pair[side]['timestamp']!=at for at,pair in pairs.items()):raise ValueError('source_side_clock_mismatch')
    for day,stamps in sessions.items():
        if len(stamps) not in (210,390) or stamps!=list(range(stamps[0],stamps[0]+len(stamps)*MINUTE,MINUTE)):
            raise ValueError('cash_session_shape')
        begin=datetime.fromtimestamp(stamps[0]/1000,NY);finish=datetime.fromtimestamp((stamps[-1]+MINUTE)/1000,NY)
        if (begin.date().isoformat()!=day or (begin.hour,begin.minute)!=(9,30)
                or (finish.hour,finish.minute)!=((13,0) if len(stamps)==210 else (16,0))
                or not start<=stamps[0]<stamps[-1]<end):raise ValueError('registered_cash_clock')


def simulate(sessions,pairs,*,start,end,scenario,null_control=False,progress=None,deadline=None):
    began,cpu=time.perf_counter(),time.process_time()
    if scenario not in core.SCENARIOS:raise ValueError('unregistered_opening5_cost')
    validate_inputs(sessions,pairs,start=start,end=end)
    result=_book(sessions,pairs,start=start,end=end,scenario=scenario,null_control=null_control,
                 progress=progress,deadline=deadline)
    result.update(wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu)
    return result


def simulate_batch(sessions,pairs,*,start,end,progress=None,deadline=None):
    began,cpu=time.perf_counter(),time.process_time()
    validate_inputs(sessions,pairs,start=start,end=end)
    validation=time.perf_counter()-began
    results=[]
    for scenario in ('reference','stress'):
        for null in (False,True):
            at,used=time.perf_counter(),time.process_time()
            callback=(lambda i,n:progress(scenario,null,i,n)) if progress else None
            result=_book(sessions,pairs,start=start,end=end,scenario=scenario,null_control=null,progress=callback,deadline=deadline)
            result.update(wall_seconds=time.perf_counter()-at,cpu_seconds=time.process_time()-used);results.append(result)
    return dict(results=results,validation_seconds=validation,wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu)


def _book(sessions,pairs,*,start,end,scenario,null_control,progress,deadline):
    from trading_workspace_v2.execution_semantics import IntrabarAmbiguityError
    instrument,model,_=core.market(scenario)
    balance,peak,drawdown=D(10000),D(10000),D(0)
    trades,rows=[],[]
    unknown=None
    for i,(day,stamps) in enumerate(sessions.items()):
        if i%16==0:
            if deadline is not None and time.perf_counter()>deadline:raise TimeoutError('opening5_deadline')
            if progress:progress(i,len(sessions))
        plan=opening_plan(stamps,pairs)
        row=dict(session=day,plan=plan,status=plan['status'],position_id=None)
        if null_control:
            row['status']='null_no_action';rows.append(row);continue
        if unknown is not None:
            row['status']='blocked_unknown_exposure';rows.append(row);continue
        if plan['side'] is None:rows.append(row);continue
        pair=pairs.get(plan['entry_time_msc'])
        if not valid_pair(pair):
            row['status']='missing_or_crossed_exact_entry';rows.append(row);continue
        bid,ask=D(str(pair[0]['open'])),D(str(pair[1]['open']))
        side=plan['side'];entry=ask if side=='BUY' else bid;stop=plan['stop']
        distance=entry-stop if side=='BUY' else stop-entry
        target=entry+10*distance if side=='BUY' else entry-10*distance
        if distance<=0 or stop<=0 or target<=0:
            row['status']='invalid_protection_bracket';rows.append(row);continue
        quantity=core.size_for_market_stop(distance,instrument=instrument,model=model,budget=D(25))
        margin=entry*quantity*instrument.contract_size/10 if quantity else D(0)
        if quantity is None or quantity>50 or margin>balance or balance<25:
            row['status']='min_max_quantity_margin_or_cash';rows.append(row);continue
        planned_risk=(distance+2*model.slippage_price_per_side)*quantity*instrument.contract_size
        if planned_risk>25:raise ValueError('opening5_planned_budget_exceeded')
        position=dict(id=f'opening5-{day}',session=day,side=side,quantity=quantity,entry_bid=bid,entry_ask=ask,
            entry_quote=entry,entry_time_msc=plan['entry_time_msc'],decision_time_msc=plan['known_at_msc'],
            entry_interval_msc=[plan['entry_time_msc'],plan['entry_time_msc']+MINUTE],
            stop=stop,take_profit=target,planned_stop_risk_usd=planned_risk,margin_usd=margin)
        row['position_id']=position['id'];last_mark=None;closed=False
        for stamp in range(plan['entry_time_msc'],plan['scheduled_exit_msc']+MINUTE,MINUTE):
            observed=pairs.get(stamp)
            if not valid_pair(observed):
                unknown=dict(position=position,reason='missing_or_crossed_held_minute',at_msc=stamp,last_known_mark=last_mark)
                break
            prices=observed[0 if side=='BUY' else 1]
            bar={k:D(str(prices[k])) for k in ('open','high','low','close')}
            last_mark=dict(source_bar_open_msc=stamp,known_at_upper_bound_msc=stamp+MINUTE,basis='M1_Open_interval_proxy',
                bid=D(str(observed[0]['open'])),ask=D(str(observed[1]['open'])))
            opening={k:bar['open'] for k in bar}
            hit=core.protective_exit_for_bar(side=side,bar=opening,stop_loss=stop,take_profit=target,
                spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
            if hit is None and stamp==plan['scheduled_exit_msc']:
                hit=dict(exit_price=bar['open'],reason='scheduled_cash_exit',at_open=True)
            if hit is None:
                try:
                    hit=core.protective_exit_for_bar(side=side,bar=bar,stop_loss=stop,take_profit=target,
                        spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
                except IntrabarAmbiguityError:
                    unknown=dict(position=position,reason='ambiguous_SL_TP_same_M1',at_msc=stamp,last_known_mark=last_mark)
                    break
            if hit is not None:
                price=hit['exit_price']
                costs=core.calculate_round_trip_cost(model,side,quantity,instrument.contract_size,bid,ask,price,price)
                net=D(str(costs['net_account']));balance+=net
                trades.append(dict(**position,exit_bar_open_msc=stamp,exit_time_msc=stamp if hit['at_open'] else None,
                    exit_interval_msc=[stamp,stamp+MINUTE],exit_at_open=hit['at_open'],exit_quote=price,
                    reason=hit['reason'],net_usd=net,costs=costs))
                peak=max(peak,balance);drawdown=max(drawdown,peak-balance);closed=True
                row['status']='trade_closed';break
            last_mark=dict(source_bar_open_msc=stamp,known_at_upper_bound_msc=stamp+MINUTE,basis='M1_Close',
                bid=D(str(observed[0]['close'])),ask=D(str(observed[1]['close'])))
        if unknown is not None:row['status']='unknown_exposure'
        elif not closed:raise ValueError('position_without_terminal_or_unknown_state')
        rows.append(row)
    if balance!=D(10000)+sum((t['net_usd'] for t in trades),D(0)):raise ValueError('opening5_cash_reconciliation')
    return dict(candidate=CANDIDATE,year=datetime.fromtimestamp(start/1000,timezone.utc).year,scenario=scenario,
        null_control=null_control,source_instrument='USATECH.IDX/USD',source_basis='separate_side_M1_OHLC_interval_proxy',
        starting_balance_usd=D(10000),balance_usd=balance,known_closed_net_usd=balance-10000,
        net_equity_usd=None if unknown else balance-10000,funding_total_usd=None if unknown else D(0),
        account_state='unknown_exposure' if unknown else 'known_flat',unknown_position=unknown,
        entries=len(trades)+(unknown is not None),closed_trades=len(trades),trades=trades,session_rows=rows,
        max_closed_balance_drawdown_usd=drawdown,start_time_msc=start,end_time_msc=end,
        qualification='development_modeled_M1_research_not_native_execution',prop_evaluated=False,
        clean_oos=False,broker_spec_verified=False,execution_authorized=False,broker_calls=0,model_calls=0)


def summarize(results):
    identities={(r['year'],r['scenario'],r['null_control']) for r in results}
    if len(results)!=8 or identities!={(y,s,n) for y in [2019,2022] for s in ['reference','stress'] for n in [False,True]}:
        raise ValueError('registered_eight_opening5_books')
    for r in results:
        if (r['candidate']!=CANDIDATE or r['execution_authorized'] is not False or r['prop_evaluated'] is not False
                or r['broker_calls']!=0 or r['model_calls']!=0):raise ValueError('opening5_identity_or_authority')
        if r['null_control'] and (r['entries'] or r['balance_usd']!=10000 or r['net_equity_usd']!=0):raise ValueError('null_opening5_action')
    stress=[r for r in results if r['scenario']=='stress' and not r['null_control']]
    gates=[dict(year=r['year'],verdict='inconclusive_unknown_exposure' if r['account_state']!='known_flat'
        else 'retained_for_further_research' if r['closed_trades']>=100 and r['net_equity_usd']>0 else 'not_retained') for r in sorted(stress,key=lambda x:x['year'])]
    return dict(candidate=CANDIDATE,year_gates=gates,retained_for_further_research=all(g['verdict']=='retained_for_further_research' for g in gates),
        clean_oos=False,prop_evaluated=False,execution_authorized=False,broker_calls=0,model_calls=0)
