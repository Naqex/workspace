"""Preregistered 15/60-minute latency comparison on the same source-only M1 path."""
from collections import defaultdict
from decimal import Decimal as D
import ny_fx_reversal as parent

MINUTE=60000


def aggregate_hours(pairs):
    """Only a complete, source-listed minute grid may supply an hourly feature."""
    buckets=[defaultdict(dict),defaultdict(dict)]
    for t,pair in pairs.items():
        if type(t) is not int or t%MINUTE:raise ValueError('exact_source_minute_clock_required')
        for i,row in enumerate(pair):
            if row is not None:
                if row['timestamp']!=t:raise ValueError('source_side_clock')
                buckets[i][t//parent.HOUR*parent.HOUR][t]=row
    sides=[]
    for groups in buckets:
        out={}
        for at,minute_rows in groups.items():
            expected=list(range(at,at+parent.HOUR,MINUTE))
            if sorted(minute_rows)!=expected:continue
            rows=[minute_rows[t] for t in expected]
            out[at]=dict(timestamp=at,open=rows[0]['open'],close=rows[-1]['close'],
                high=max(D(str(r['high'])) for r in rows),low=min(D(str(r['low'])) for r in rows),volume=0)
        sides.append(out)
    return parent.paired(*sides)


def run(pairs,hourly,year,scenario,*,lag_minutes,opposite=False,null=False,day_list=None,progress=None,gap_model=None):
    if type(lag_minutes) is not int or lag_minutes not in (15,60):raise ValueError('unregistered_latency')
    days=parent.dates(year) if day_list is None else day_list
    if not days or days!=sorted(set(days)) or any(d not in parent.dates(year) for d in days):raise ValueError('registered_day_subset')
    if gap_model is not None:
        from ny_fx_gap_scenarios import GapScenario
        if not isinstance(gap_model,GapScenario):raise ValueError('typed_gap_scenario_required')
    instrument,model=parent.market(scenario);cash=D(10000);position=None;unknown=None
    decisions=[];census=[];events=[];trades=[]

    def close(at,price,reason,at_open,*,conditional_exit=False):
        nonlocal position,cash
        costs=parent.calculate_round_trip_cost(model,position['side'],position['quantity'],D(100000),
            position['entry_bid'],position['entry_ask'],price,price)
        cash+=D(str(costs['net_account']))
        trades.append(dict(**position,exit_bar_msc=at,exit_interval_msc=[at,at+MINUTE],exit_quote=price,
            exit_at_open=at_open,reason=reason,costs=costs,cash_after=cash));position=None
        if conditional_exit:
            trades[-1].update(exit_price_basis='conditional_same_side_H1_extreme',observed_exit=False)

    for day in days:
        if unknown:break
        clock=parent.clocks(day);intents={}
        for hour in range(10,14):
            r=parent.decision(hourly,clock[hour],opposite=opposite)
            r['action_msc']=r['decision_msc']+lag_minutes*MINUTE
            decisions.append(r);intents[r['action_msc']]=r
        for at in range(clock[10],clock[15]+MINUTE,MINUTE):
            pair=pairs.get(at);intent=intents.get(at);scheduled=at==clock[15]
            row=dict(day=day,at_msc=at,intent_status=intent['status'] if intent else 'scheduled_exit' if scheduled else 'none',
                action='no_action',position_before=position['side'] if position else None)
            if position and not parent.available(pair,('open','close')):
                gap_action=gap_model.action(at,pair,position,intent=intent,scheduled=scheduled) if gap_model else None
                if gap_action is not None:
                    if gap_action['price'] is not None:
                        close(at,gap_action['price'],gap_action['action'],False,conditional_exit=True)
                    row.update(action=gap_action['action'],position_after=position['side'] if position else None,
                        cash_usd=cash,valuation_status='unobserved_no_mark',conditional_gap=True)
                    census.append(row)
                    continue
                unknown=dict(at_msc=at,reason='missing_or_crossed_held_minute',position=position);census.append(row);break
            if position:
                p=D(str(pair[0 if position['side']=='BUY' else 1]['open']));bar={k:p for k in ('open','high','low','close')}
                hit=parent.protective_exit_for_bar(side=position['side'],bar=bar,stop_loss=position['stop'],
                    take_profit=None,spread_price=0,tick_size=parent.GRID,allow_open_gap=True)
                if hit:close(at,hit['exit_price'],hit['reason'],True);row['action']='gap_stop'
            if scheduled:
                if position:close(at,D(str(pair[0 if position['side']=='BUY' else 1]['open'])),'scheduled_exit',True);row['action']='scheduled_exit'
            elif intent and intent['status']=='ready' and not null:
                target=intent['side']
                if position and position['side']!=target:
                    close(at,D(str(pair[0 if position['side']=='BUY' else 1]['open'])),'target_change',True);row['action']='target_change'
                if position is None and target:
                    if parent.available(pair):
                        position,status=parent.open_position(intent,pair,at,cash,instrument,model);row['action']=status
                        if position:events.append(dict(type='opened',**position))
                    else:row['action']='missing_or_crossed_entry_Open'
            if position:
                if not parent.available(pair,('open','close')):
                    unknown=dict(at_msc=at,reason='missing_or_crossed_held_minute',position=position);census.append(row);break
                bar={k:D(str(pair[0 if position['side']=='BUY' else 1][k])) for k in ('open','high','low','close')}
                hit=parent.protective_exit_for_bar(side=position['side'],bar=bar,stop_loss=position['stop'],
                    take_profit=None,spread_price=0,tick_size=parent.GRID,allow_open_gap=True)
                if hit:close(at,hit['exit_price'],hit['reason'],hit['at_open'])
            # Minute heartbeats belong in process telemetry; retain trading decisions/state changes here.
            if intent or scheduled or row['action']!='no_action' or row['position_before']!=(position['side'] if position else None):
                row.update(position_after=position['side'] if position else None,cash_usd=cash);census.append(row)
        if progress:progress(day=day,closed=len(trades),cash=str(cash),unknown=bool(unknown))
    result=dict(candidate=parent.CANDIDATES[int(opposite)].replace('-h1-v1',f'-m1-lag{lag_minutes}-v1'),
        year=year,scenario=scenario,lag_minutes=lag_minutes,null_control=null,expected_days=len(days),
        expected_decisions=4*len(days),decisions=decisions,census=census,events=events,trades=trades,
        closed_trades=len(trades),cash_usd=cash,net_equity_usd=cash-10000 if position is None and unknown is None else None,
        position=position,unknown=unknown,account_state='unknown_exposure' if unknown else 'modeled_flat',
        clean_oos=False,prop_evaluated=False,execution_authorized=False,holdout_read=False,broker_calls=0)
    if gap_model is not None:
        result.update(candidate=result['candidate'].removesuffix('-v1')+'-conditional-gap-v1',
            gap_scenario=gap_model.mode,conditional_model=True,original_unknown_preserved=True,
            account_state='unknown_exposure' if unknown else 'conditional_flat',
            model_assumptions='observed_feed_events_only' if gap_model.mode=='observed_events' else
                'hidden_gap_path_within_same_side_H1_envelope_adverse_stop_scenario_not_global_bound')
    return result
