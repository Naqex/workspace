"""Frozen, stop-aligned XAU research labels and causal annual forest inference."""
from bisect import bisect_right
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
from pathlib import Path
import time

from forex_study_batch import configure_source_root
from nasdaq_cash_calendar import calendar_for
from sealed_m1_review import cash_sessions,validate_rows

HOUR=3600000
CANDIDATES=('xauusd-h1-forest-sl-time3-r025-v1','xauusd-h1-forest-sl-time3-shuffled-r025-v1')


def bind_core(root:Path):
    configure_source_root(root)
    global Candle,features,FEATURE_NAMES,predict,validate_model
    global InstrumentSpec,CostModel,calculate_round_trip_cost,MetalStudyMarket
    global protective_exit_for_bar,size_for_market_stop
    from trading_workspace_v2.forex_h4 import Candle
    from trading_workspace_v2.forex_ml_candidate import features,FEATURE_NAMES,predict,validate_model
    from trading_workspace_v2.retained import InstrumentSpec,CostModel,calculate_round_trip_cost
    from trading_workspace_v2.research_market import MetalStudyMarket,size_for_market_stop
    from trading_workspace_v2.execution_semantics import protective_exit_for_bar


def paired_inputs(bid,ask,*,start,end):
    if start>=end or end>1735689600000 or start%HOUR or end%HOUR:
        raise ValueError('gold_ML_source_scope_holdout_closed')
    for rows in (bid,ask):
        validate_rows(rows,start,end,.001)
        if any(r['timestamp']%HOUR for r in rows):raise ValueError('gold_ML_H1_required')
    sides=[{r['timestamp']:r for r in rows} for rows in (bid,ask)]
    return {t:(sides[0].get(t),sides[1].get(t)) for t in sorted(sides[0].keys()|sides[1].keys())}


def valid_pair(pair):
    return pair is not None and all(r is not None for r in pair) and all(D(str(pair[1][k]))>=D(str(pair[0][k])) for k in ('open','close'))


def opportunities(pairs,year):
    if type(year) is not int or year not in (2018,2019,2021,2022):raise ValueError('unregistered_gold_ML_year')
    from datetime import datetime,timezone
    dates={d:ss for d,ss in cash_sessions(calendar_for(year)).items() if len(ss)==390}
    bids=[(t,p[0]) for t,p in pairs.items() if p[0] is not None]
    stamps=[t for t,_ in bids]
    if stamps!=sorted(set(stamps)):raise ValueError('gold_ML_ordered_source_required')
    candles=[Candle(timestamp=t//1000,**{k:D(str(r[k])) for k in ('open','high','low','close')}) for t,r in bids]
    result=[]
    for day in dates:
        for hour in (8,12,16):
            at=int(datetime.fromisoformat(day).replace(hour=hour,tzinfo=timezone.utc).timestamp()*1000)
            row=dict(id=f'{day}-{hour:02}',day=day,decision_msc=at,entry_msc=at+HOUR,exit_msc=at+4*HOUR,
                     status='feature_unavailable',x=None,distance=None)
            current=pairs.get(at-HOUR)
            if valid_pair(current):
                i=bisect_right(stamps,at-HOUR)
                if i>=100:
                    x,distance=features(candles[i-100:i],D(str(current[1]['close']))-D(str(current[0]['close'])))
                    if x is not None:row.update(x=x,distance=distance,status='feature_ready')
            result.append(row)
    return result


def market(scenario):
    if scenario not in ('reference','stress'):raise ValueError('unregistered_gold_ML_cost')
    geometry=MetalStudyMarket()
    instrument=InstrumentSpec.from_mapping(geometry.instrument(1514764800000))
    model=CostModel.from_mapping(dict(version='gold-observed-H1-'+scenario+'-v1',spread_basis='bid_ask_embedded',
        commission_per_side_account='0',commission_per_side_per_quantity_account='2.5',minimum_fee_account='0',
        slippage_price_per_side='.1' if scenario=='reference' else '.2',financing_account='0',
        quote_to_account_rate='1',account_ccy='USD',rounding_decimals=2))
    return instrument,model


def trade_path(op,side,pairs,*,scenario='reference',balance=D(10000)):
    if side not in ('BUY','SELL'):raise ValueError('gold_ML_side')
    if op['x'] is None or op['distance'] is None:return dict(status='feature_unavailable')
    pair=pairs.get(op['entry_msc'])
    if not valid_pair(pair):return dict(status='missing_or_crossed_entry')
    instrument,model=market(scenario)
    bid,ask=(D(str(pair[i]['open'])) for i in (0,1));entry=ask if side=='BUY' else bid
    distance=D(str(op['distance']))
    raw=entry-distance if side=='BUY' else entry+distance
    stop=(raw/instrument.tick_size).to_integral_value(rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING)*instrument.tick_size
    if distance<=0 or stop<=0:return dict(status='invalid_stop')
    quantity=size_for_market_stop(distance,instrument=instrument,model=model,budget=D(25))
    margin=entry*quantity*instrument.contract_size/10 if quantity else D(0)
    if quantity is None or quantity>50 or margin>balance or balance<25:return dict(status='quantity_or_margin_rejected')
    actual=entry-stop if side=='BUY' else stop-entry
    risk=((actual+2*model.slippage_price_per_side)*instrument.contract_size+2*model.commission_per_side_per_quantity_account)*quantity
    if risk>25:raise ValueError('gold_ML_planned_risk_exceeded')
    position=dict(opportunity_id=op['id'],day=op['day'],side=side,quantity=quantity,decision_msc=op['decision_msc'],
                  entry_msc=op['entry_msc'],entry_bid=bid,entry_ask=ask,entry_quote=entry,stop=stop,
                  distance=distance,margin_usd=margin,planned_stop_risk_usd=risk)
    mark=None
    for at in range(op['entry_msc'],op['exit_msc']+HOUR,HOUR):
        pair=pairs.get(at)
        if not valid_pair(pair):return dict(status='unknown_exposure',position=position,at_msc=at,last_mark=mark)
        bar={k:D(str(pair[0 if side=='BUY' else 1][k])) for k in ('open','high','low','close')}
        opened={k:bar['open'] for k in bar}
        hit=protective_exit_for_bar(side=side,bar=opened,stop_loss=stop,take_profit=None,
                                   spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
        if hit is None and at==op['exit_msc']:hit=dict(exit_price=bar['open'],reason='scheduled_exit',at_open=True)
        if hit is None:
            hit=protective_exit_for_bar(side=side,bar=bar,stop_loss=stop,take_profit=None,
                                       spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
        if hit:
            price=hit['exit_price'];costs=calculate_round_trip_cost(model,side,quantity,instrument.contract_size,bid,ask,price,price)
            return dict(status='closed',**position,exit_bar_msc=at,exit_interval_msc=[at,at+HOUR],
                        endpoint_msc=at+HOUR,exit_quote=price,reason=hit['reason'],exit_at_open=hit['at_open'],
                        costs=costs,net_usd=D(str(costs['net_account'])))
        mark=dict(bar_open_msc=at,bid=D(str(pair[0]['close'])),ask=D(str(pair[1]['close'])))
    raise ValueError('gold_ML_missing_terminal')


def training_labels(ops,pairs):
    result=[]
    for op in ops:
        row=dict(opportunity_id=op['id'],decision_msc=op['decision_msc'],x=op['x'],usable=False,y=None,endpoint_msc=None,sides={})
        if op['x'] is not None:
            row['sides']={s:trade_path(op,s,pairs) for s in ('BUY','SELL')}
            if all(r['status']=='closed' for r in row['sides'].values()):
                row.update(usable=True,y=[float(row['sides'][s]['net_usd']/25) for s in ('BUY','SELL')],
                           endpoint_msc=max(r['endpoint_msc'] for r in row['sides'].values()))
        result.append(row)
    return result


def purged_training(labels,*,start,cutoff):
    return [r for r in labels if r['usable'] and start<=r['decision_msc']<cutoff and r['endpoint_msc']<cutoff]


def fit_pack(labels,*,start,cutoff,bindings,shuffled=False,fold_index=0):
    import numpy as np
    from sklearn.ensemble import RandomForestRegressor
    from forex_ml_study import export_model
    if (set(bindings)!={'protocol_sha256','input_manifest_sha256','implementation_sha256'}
            or any(not isinstance(v,str) or len(v)!=64 or set(v)-set('0123456789abcdef') for v in bindings.values())):
        raise ValueError('gold_ML_pack_bindings_required')
    chosen=purged_training(labels,start=start,cutoff=cutoff)
    if len(chosen)<100:raise ValueError('gold_ML_insufficient_complete_training_labels')
    x=np.asarray([r['x'] for r in chosen]);y=np.asarray([r['y'] for r in chosen])
    if shuffled:y=y[np.random.default_rng(42+fold_index).permutation(len(y))]
    estimator=RandomForestRegressor(n_estimators=80,max_depth=4,min_samples_leaf=100,random_state=42,n_jobs=1).fit(x,y)
    model=export_model(estimator);validate_model(model)
    expected=estimator.predict(x);observed=np.asarray([predict(model,row.tolist()) for row in x])
    delta=float(np.max(np.abs(expected-observed)))
    if delta>1e-10:raise ValueError('gold_ML_safe_export_mismatch')
    return dict(schema='gold-stop-aligned-forest-pack-v1',candidate=CANDIDATES[int(shuffled)],shuffled=shuffled,
                cutoff_msc=cutoff,available_from_msc=cutoff+HOUR,train_start_msc=start,train_rows=len(chosen),
                last_label_endpoint_msc=max(r['endpoint_msc'] for r in chosen),feature_names=list(FEATURE_NAMES),
                bindings=dict(bindings),model=model,max_abs_export_delta=delta)


def predicted_side(pack,op):
    if pack['feature_names']!=list(FEATURE_NAMES) or pack['candidate'] not in CANDIDATES:raise ValueError('gold_ML_pack_identity')
    if op['x'] is None or op['decision_msc']<pack['available_from_msc']:return None,None
    scores=predict(pack['model'],op['x'])
    side='BUY' if scores[0]>scores[1] and scores[0]>.10 else 'SELL' if scores[1]>scores[0] and scores[1]>.10 else None
    return side,scores


def simulate(ops,pairs,pack,*,scenario,null_control=False,deadline=None,progress=None):
    began=time.perf_counter();balance=D(10000);trades=[];decisions=[];unknown=None
    for i,op in enumerate(ops):
        if i%96==0:
            if deadline is not None and time.perf_counter()>deadline:raise TimeoutError('gold_ML_deadline')
            if progress:progress(i,len(ops))
        row=dict(opportunity_id=op['id'],decision_msc=op['decision_msc'],side=None,scores=None,status='no_signal')
        decisions.append(row)
        if unknown is not None:row['status']='blocked_unknown_exposure';continue
        side,scores=predicted_side(pack,op);row['scores']=scores
        if null_control:row['status']='null_no_action';continue
        row['side']=side
        if side is None:continue
        trade=trade_path(op,side,pairs,scenario=scenario,balance=balance);row['status']=trade['status']
        if trade['status']=='unknown_exposure':unknown=trade;continue
        if trade['status']=='closed':
            if trades and trade['entry_msc']<trades[-1]['endpoint_msc']:raise ValueError('gold_ML_position_overlap')
            trades.append(trade);balance+=trade['net_usd']
    if balance!=10000+sum((t['net_usd'] for t in trades),D(0)):raise ValueError('gold_ML_cash_reconciliation')
    return dict(candidate=pack['candidate'],scenario=scenario,null_control=null_control,trades=trades,decisions=decisions,
                closed_trades=len(trades),entries=len(trades)+int(unknown is not None),unknown=unknown,
                known_closed_net_usd=balance-10000,net_equity_usd=None if unknown else balance-10000,
                account_state='unknown_exposure' if unknown else 'modeled_flat',starting_balance_usd=D(10000),
                source_basis='observed_side_H1_OHLC_interval_proxy_not_ticks',wall_seconds=time.perf_counter()-began,
                clean_oos=False,prop_evaluated=False,broker_spec_verified=False,execution_authorized=False,
                holdout_read=False,broker_calls=0,model_calls=0)
