"""Frozen R010 monthly allocation proxy, not an account or execution engine."""
from datetime import datetime,timedelta,timezone
from decimal import Decimal as D, ROUND_HALF_UP

SYMBOLS=('EURUSD','XAUUSD','US500')
CONTRACTS={'EURUSD':D(100000),'XAUUSD':D(100),'US500':D(1)}
COMMISSIONS={'EURUSD':D('2.5'),'XAUUSD':D('2.5'),'US500':D(0)}
SLIPPAGE={'reference':{'EURUSD':D(0),'XAUUSD':D('.10'),'US500':D('.25')},
          'stress':{'EURUSD':D('.00002'),'XAUUSD':D('.20'),'US500':D('.75')}}


def money(value):
    return D(value).quantize(D('.01'),rounding=ROUND_HALF_UP)


def previous_months(month):
    year,index=map(int,month.split('-'));ordinal=year*12+index-1
    return [f'{i//12}-{i%12+1:02}' for i in range(ordinal-13,ordinal)]


def allocation(observations,month,*,always_long=False):
    history=previous_months(month);features={};inverse={}
    for symbol in SYMBOLS:
        entry=observations[(symbol,month,'rebalance_observation')]
        points=[observations[(symbol,m,'signal_close')] for m in history]
        if (entry['bid'] is None or any(p['bid'] is None for p in points)
                or any(p.get('known_at_ms',p.get('known_at_upper_bound_ms'))>=entry['target_ms'] for p in points)):
            raise ValueError('inconclusive_monthly_inputs')
        prices=[D(p['bid']) for p in points]
        if any(not p.is_finite() or p<=0 for p in prices):raise ValueError('invalid_signal_price')
        returns=[b/a-1 for a,b in zip(prices,prices[1:])]
        mean=sum(returns,D(0))/12
        sigma=(sum(((r-mean)**2 for r in returns),D(0))/11).sqrt()
        if sigma<=0:raise ValueError('inconclusive_zero_volatility')
        signs=[D(1) if prices[-1]>prices[-1-h] else D(-1) if prices[-1]<prices[-1-h] else D(0) for h in (1,3,12)]
        trend=D(1) if always_long else sum(signs,D(0))/3
        inverse[symbol]=1/sigma
        features[symbol]=dict(history_months=history,prices=list(map(str,prices)),monthly_returns=list(map(str,returns)),
            sample_vol=str(sigma),signs=list(map(str,signs)),trend=str(trend))
    denominator=sum(inverse.values(),D(0));weights={s:inverse[s]/denominator*D(features[s]['trend']) for s in SYMBOLS}
    if sum(map(abs,weights.values()),D(0))>1+D('1e-24'):raise ValueError('gross_exposure_cap')
    return weights,features


def sides(observation,scenario):
    if observation['bid'] is None:raise ValueError('missing_future_execution_or_mark')
    bid=D(observation['bid']);symbol=observation['instrument']
    if symbol=='XAUUSD':
        if observation['ask'] is not None or observation['observed_ask'] is not False:raise ValueError('Gold_observed_Ask_claim')
        ask=bid+(D('.50') if scenario=='reference' else D('1.00'))
    else:
        if observation['ask'] is None:raise ValueError('missing_observed_Ask')
        ask=D(observation['ask'])
    if ask<bid or bid<=0:raise ValueError('invalid_endpoint_prices')
    return bid,ask


def funding(symbol,side,quantity,start_ms,stop_ms,scenario):
    if stop_ms<=start_ms or quantity<0:raise ValueError('funding_interval')
    day=datetime.fromtimestamp(start_ms/1000,timezone.utc).replace(hour=22,minute=0,second=0,microsecond=0)
    if int(day.timestamp()*1000)<=start_ms:day+=timedelta(days=1)
    events=[]
    rate=(D('9.30') if side=='BUY' else D('-.31')) if symbol=='EURUSD' and scenario=='reference' else (
        D(20) if symbol=='EURUSD' else D(20) if symbol=='XAUUSD' and scenario=='reference' else
        D(40) if symbol=='XAUUSD' else D(1) if scenario=='reference' else D(2))
    while int(day.timestamp()*1000)<=stop_ms:
        if symbol=='US500' or day.weekday()<5:
            multiplier=3 if symbol!='US500' and day.weekday()==2 else 1
            debit=rate*quantity*multiplier
            events.append(dict(time_ms=int(day.timestamp()*1000),rate_per_lot=str(rate),multiplier=multiplier,debit=str(debit)))
        day+=timedelta(days=1)
    return sum((D(e['debit']) for e in events),D(0)),events


def model_cost(symbol,scenario,financing):
    return dict(version='monthly-allocation-declared-'+symbol+'-'+scenario,spread_basis='bid_ask_embedded',
        commission_per_side_account='0',commission_per_side_per_quantity_account=str(COMMISSIONS[symbol]),
        minimum_fee_account='0',slippage_price_per_side=str(SLIPPAGE[scenario][symbol]),financing_account=str(financing),
        quote_to_account_rate='1',account_ccy='USD',rounding_decimals=2)


def run(observations,*,scenario,always_long,cost_function,progress=None):
    if scenario not in SLIPPAGE:raise ValueError('unknown_cost_scenario')
    keyed={(r['instrument'],r['month'],r['role']):r for r in observations}
    nav=D(10000);cash=nav;rows=[]
    months=[f'{y}-{m:02}' for y in range(2018,2025) for m in range(1,13)]
    for index,month in enumerate(months):
        if progress:progress(month)
        weights,features=allocation(keyed,month,always_long=always_long)
        before=nav;trades=[];endmark=index==len(months)-1;net=D(0);float_total=D(0);cashflow=D(0)
        for symbol in SYMBOLS:
            weight=weights[symbol]
            if weight==0:
                trades.append(dict(symbol=symbol,weight='0',status='flat',net='0'));continue
            side='BUY' if weight>0 else 'SELL'
            entry=keyed[(symbol,month,'rebalance_observation')]
            exit_at=keyed[(symbol,month,'signal_close')] if endmark else keyed[(symbol,months[index+1],'rebalance_observation')]
            eb,ea=sides(entry,scenario);xb,xa=sides(exit_at,scenario)
            units=before*abs(weight)/((eb+ea)/2);quantity=units/CONTRACTS[symbol]
            start=entry.get('quote_time_ms',entry['target_ms']);stop=exit_at['target_ms'] if endmark else exit_at.get('quote_time_ms',exit_at['target_ms'])
            finance,events=funding(symbol,side,quantity,start,stop,scenario)
            if endmark:
                gross=money(((xb-ea) if side=='BUY' else (eb-xa))*units)
                commission=money(quantity*COMMISSIONS[symbol]);slip=money(units*SLIPPAGE[scenario][symbol]);fin=money(finance)
                component_cash=-commission-slip-fin;component_net=component_cash+gross
                costs=dict(gross_account=str(gross),commission_account=str(commission),slippage_account=str(slip),financing_account=str(fin),net_account=str(component_net),exit_cost_charged=False)
                float_total+=gross;cashflow+=component_cash
            else:
                costs=cost_function(model_cost(symbol,scenario,finance),side,quantity,CONTRACTS[symbol],eb,ea,xb,xa)
                component_net=D(str(costs['net_account']));cashflow+=component_net
            net+=component_net
            trades.append(dict(symbol=symbol,weight=str(weight),status='open_mark' if endmark else 'closed',side=side,
                units=str(units),quantity_lots=str(quantity),entry=entry,exit_or_mark=exit_at,
                entry_prices=dict(bid=str(eb),ask=str(ea)),exit_prices=dict(bid=str(xb),ask=str(xa)),
                start_ms=start,stop_ms=stop,funding_events=events,costs=costs,net=str(component_net)))
        cash+=cashflow;nav=before+net
        if nav<=0:raise ValueError('allocation_proxy_exhausted')
        if cash+float_total!=nav:raise ValueError('continuous_proxy_cash_equity')
        rows.append(dict(month=month,nav_before=str(before),nav_after=str(nav),net=str(net),cash_after=str(cash),
            floating_after=str(float_total),gross_exposure=str(sum(map(abs,weights.values()),D(0))),features=features,trades=trades,
            end_state='open_mark_not_closed' if endmark else 'monthly_full_roll_closed'))
    years=[]
    for year in range(2018,2025):
        group=[r for r in rows if r['month'].startswith(str(year))];start=D(group[0]['nav_before']);ending=D(group[-1]['nav_after'])
        years.append(dict(allocation_cohort_year=year,months=len(group),starting_nav=str(start),ending_nav=str(ending),
            net=str(ending-start),return_percent=str((ending/start-1)*100)))
    peak=D(10000);endpoint_dd=D(0)
    for row in rows:
        at=D(row['nav_after']);peak=max(peak,at);endpoint_dd=max(endpoint_dd,(peak-at)/peak)
    return dict(status='completed_monthly_allocation_proxy_not_account',scenario=scenario,
        candidate='always_long_inverse_vol_benchmark' if always_long else 'mixed_1_3_12_inverse_vol_primary',
        starting_nav='10000',ending_nav=str(nav),net=str(nav-10000),cash=str(cash),floating=str(nav-cash),
        years=years,months=rows,monthly_endpoint_drawdown_fraction=str(endpoint_dd),
        financing_rounding='sum_unrounded_events_then_money_round2',final_positions_closed=False,
        account_simulated=False,prop_evaluated=False,challenge_qualified=False,execution_authorized=False)
