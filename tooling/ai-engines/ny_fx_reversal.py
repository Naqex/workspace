"""Frozen NY-session EURUSD MA4 reversal, with H1 execution proxies and no broker."""
from datetime import date, datetime, timedelta
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
from zoneinfo import ZoneInfo

from forex_study_batch import configure_source_root

HOUR=3600000
GRID=D('.00001')
CANDIDATES=('eurusd-ny-ma4-reversal-tr14x1p5-r025-h1-v1',
            'eurusd-ny-ma4-momentum-control-tr14x1p5-r025-h1-v1')


def bind_core(root):
    configure_source_root(root)
    global InstrumentSpec, CostModel, calculate_round_trip_cost, size_for_market_stop
    global protective_exit_for_bar
    from trading_workspace_v2.retained import InstrumentSpec, CostModel, calculate_round_trip_cost
    from trading_workspace_v2.research_market import size_for_market_stop
    from trading_workspace_v2.execution_semantics import protective_exit_for_bar


def dates(year):
    if type(year) is not int or year not in (2019,2022):raise ValueError('unregistered_NY_FX_year')
    day=date(year,1,1);out=[]
    while day.year==year:
        if day.weekday()<5:out.append(day.isoformat())
        day+=timedelta(days=1)
    return out


def clocks(day):
    d=datetime.fromisoformat(day).replace(tzinfo=ZoneInfo('America/New_York'))
    return {hour:int(d.replace(hour=hour).timestamp()*1000) for hour in range(10,16)}


def paired(bid,ask):
    return {t:(bid.get(t),ask.get(t)) for t in sorted(bid.keys()|ask.keys())}


def available(pair,fields=('open',)):
    return (pair is not None and all(r is not None for r in pair)
            and all(D(str(pair[1][k]))>=D(str(pair[0][k]))>0 for k in fields))


def decision(pairs,at,*,opposite=False):
    past=[pairs.get(t) for t in range(at-15*HOUR,at,HOUR)]
    result=dict(decision_msc=at,action_msc=at+HOUR,status='feature_unavailable',side=None,distance=None)
    if any(p is None or p[0] is None for p in past) or any(not available(p,('close',)) for p in past[-4:]):return result
    bids=[{k:D(str(p[0][k])) for k in ('open','high','low','close')} for p in past]
    mids=[(D(str(p[0]['close']))+D(str(p[1]['close'])))/2 for p in past[-4:]]
    mean=sum(mids,D(0))/4
    tr=sum((max(b['high']-b['low'],abs(b['high']-prev['close']),abs(b['low']-prev['close']))
            for prev,b in zip(bids,bids[1:])),D(0))/14
    side='BUY' if mids[-1]<mean else 'SELL' if mids[-1]>mean else None
    if opposite and side:side='SELL' if side=='BUY' else 'BUY'
    if tr<=0:return result
    result.update(status='ready',side=side,distance=tr*D('1.5'),midpoint=mids[-1],ma4=mean,tr14=tr)
    return result


def market(scenario):
    if scenario not in ('reference','stress'):raise ValueError('unregistered_NY_FX_cost')
    instrument=InstrumentSpec.from_mapping(dict(instrument_id='EURUSD',asset_class='fx',base_ccy='EUR',
        quote_ccy='USD',account_ccy='USD',contract_size='100000',tick_size=str(GRID),pip_size='.0001',
        quantity_min='.01',quantity_step='.01',effective_from_utc='2019-01-01T00:00:00Z'))
    model=CostModel.from_mapping(dict(version='NY-FX-declared-'+scenario+'-v1',spread_basis='bid_ask_embedded',
        commission_per_side_account='0',commission_per_side_per_quantity_account='2.5',minimum_fee_account='0',
        slippage_price_per_side='0' if scenario=='reference' else '.00002',financing_account='0',
        quote_to_account_rate='1',account_ccy='USD',rounding_decimals=2))
    return instrument,model


def open_position(intent,pair,at,cash,instrument,model):
    bid,ask=(D(str(r['open'])) for r in pair);side=intent['side'];entry=ask if side=='BUY' else bid
    distance=intent['distance'];q=size_for_market_stop(distance,instrument=instrument,model=model,budget=D(25))
    if q is None:return None,'quantity_rejected'
    stop=((entry-distance if side=='BUY' else entry+distance)/GRID).to_integral_value(
        rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING)*GRID
    if stop<=0:return None,'invalid_stop'
    risk=(abs(entry-stop)*100000+2*model.slippage_price_per_side*100000+5)*q
    margin=entry*q*100000/30
    if risk>25:raise ValueError('planned_risk_exceeded')
    if q>50 or cash<25 or margin>cash:return None,'quantity_or_margin_rejected'
    return dict(side=side,quantity=q,entry_msc=at,decision_msc=intent['decision_msc'],
        entry_bid=bid,entry_ask=ask,entry_quote=entry,stop=stop,distance=distance,
        planned_risk_usd=risk,margin_usd=margin),'opened'


def run(pairs,year,scenario,*,opposite=False,null=False,day_list=None,progress=None):
    days=dates(year) if day_list is None else day_list
    if not days or len(set(days))!=len(days) or any(d not in dates(year) for d in days):
        raise ValueError('registered_weekday_subset_required')
    instrument,model=market(scenario);cash=D(10000);position=None;unknown=None
    decisions=[];events=[];trades=[];census=[]

    def close(at,price,reason,at_open):
        nonlocal position,cash
        cost=calculate_round_trip_cost(model,position['side'],position['quantity'],D(100000),
            position['entry_bid'],position['entry_ask'],price,price)
        cash+=D(str(cost['net_account']))
        trades.append(dict(**position,exit_bar_msc=at,exit_interval_msc=[at,at+HOUR],exit_quote=price,
            exit_at_open=at_open,reason=reason,costs=cost,cash_after=cash))
        position=None

    for day in days:
        if unknown:break
        times=clocks(day)
        intents={}
        for hour in range(10,14):
            r=decision(pairs,times[hour],opposite=opposite);intents[r['action_msc']]=r;decisions.append(r)
        for hour in range(11,16):
            at=times[hour];pair=pairs.get(at);intent=intents.get(at)
            row=dict(day=day,hour=hour,at_msc=at,intent_status=intent['status'] if intent else 'scheduled_exit',
                action='no_action',position_before=position['side'] if position else None)
            if position and not available(pair,('open','close')):
                unknown=dict(at_msc=at,reason='missing_or_crossed_held_hour',position=position);census.append(row);break
            if position:
                bar={k:D(str(pair[0 if position['side']=='BUY' else 1]['open'])) for k in ('open','high','low','close')}
                hit=protective_exit_for_bar(side=position['side'],bar=bar,stop_loss=position['stop'],
                    take_profit=None,spread_price=0,tick_size=GRID,allow_open_gap=True)
                if hit:close(at,hit['exit_price'],hit['reason'],True);row['action']='gap_stop'
            if hour==15:
                if position:
                    price=D(str(pair[0 if position['side']=='BUY' else 1]['open']))
                    close(at,price,'scheduled_exit',True);row['action']='scheduled_exit'
            elif intent['status']=='ready' and not null:
                target=intent['side']
                if position and position['side']!=target:
                    price=D(str(pair[0 if position['side']=='BUY' else 1]['open']))
                    close(at,price,'target_change',True);row['action']='target_change'
                if position is None and target:
                    if available(pair):
                        position,status=open_position(intent,pair,at,cash,instrument,model)
                        row['action']=status
                        if position:events.append(dict(type='opened',**position))
                    else:row['action']='missing_or_crossed_entry_Open'
            if position:
                if not available(pair,('open','close')):
                    unknown=dict(at_msc=at,reason='missing_or_crossed_held_hour',position=position);census.append(row);break
                bar={k:D(str(pair[0 if position['side']=='BUY' else 1][k])) for k in ('open','high','low','close')}
                hit=protective_exit_for_bar(side=position['side'],bar=bar,stop_loss=position['stop'],
                    take_profit=None,spread_price=0,tick_size=GRID,allow_open_gap=True)
                if hit:close(at,hit['exit_price'],hit['reason'],hit['at_open'])
            row.update(position_after=position['side'] if position else None,cash_usd=cash);census.append(row)
        if progress:progress(day=day,closed=len(trades),cash=str(cash),unknown=bool(unknown))
    return dict(candidate=CANDIDATES[int(opposite)],year=year,scenario=scenario,null_control=null,
        expected_days=len(days),expected_decisions=4*len(days),decisions=decisions,census=census,
        events=events,trades=trades,closed_trades=len(trades),cash_usd=cash,
        net_equity_usd=cash-10000 if unknown is None and position is None else None,
        unknown=unknown,position=position,account_state='unknown_exposure' if unknown else 'modeled_flat',
        clean_oos=False,prop_evaluated=False,execution_authorized=False,holdout_read=False,broker_calls=0)
