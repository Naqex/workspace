"""Shared modeled M1 book for frozen offline index policies; not native execution."""
from decimal import Decimal as D, ROUND_HALF_UP
import time

import index_noise_study as core

DAY = 86400000
MINUTE = 60000


def simulate(pairs, plans, *, candidate, slippage, funding_per_lot, null_control=False,
             progress=None, deadline=None, end_time_msc=None, cost_scenario=core.LEGACY_COST_SCENARIO):
    began, cpu = time.perf_counter(), time.process_time()
    instrument, model = core.market(slippage, cost_scenario=cost_scenario)
    balance = D(10000)
    position = pending = None
    trades, decisions, funding, gaps, rejected = [], [], [], [], []
    entries = 0
    previous = None
    day_charge = None
    plan_times = sorted(plans)
    plan_index = 0

    def post_funding(boundary):
        nonlocal day_charge, balance
        while day_charge is not None and day_charge<=boundary:
            if position:
                debit = (position['quantity']*funding_per_lot).quantize(D('.01'), rounding=ROUND_HALF_UP)
                position['funding'] += debit
                balance -= debit
                funding.append(dict(time_msc=day_charge, position_id=position['id'], debit_usd=str(debit)))
            day_charge += DAY

    def queue_due(boundary):
        nonlocal pending, plan_index
        while plan_index<len(plan_times) and plan_times[plan_index]<=boundary:
            at = plan_times[plan_index]
            plan = plans[at]
            plan_index += 1
            side = None if null_control else plan['side']
            decisions.append(dict(time_msc=at,side=side,stop_distance=str(plan.get('distance')),
                                  signal_basis=plan.get('basis')))
            if side:
                if pending:
                    rejected.append(dict(time_msc=pending['fill_time'],reason='unfilled_before_next_decision'))
                pending = dict(side=side,distance=plan.get('distance'),fill_time=at+MINUTE)

    def close(stamp, price, reason):
        nonlocal balance, position
        costs = core.calculate_round_trip_cost(model, position['side'], position['quantity'], instrument.contract_size,
                                               position['bid'], position['ask'], price, price)
        price_net = D(str(costs['net_account']))
        balance += price_net
        trades.append(dict(position_id=position['id'], side=position['side'], quantity=str(position['quantity']),
            entry_time_msc=position['time'], entry_fill=str(position['ask'] if position['side']=='BUY' else position['bid']),
            exit_time_msc=stamp if reason!='stop_loss' else None,
            exit_interval_msc=[stamp, stamp+MINUTE] if reason=='stop_loss' else [stamp, stamp],
            exit_fill=str(price), reason=reason, stop=str(position['stop']),
            price_net_usd=str(price_net), funding_usd=str(position['funding']),
            net_usd=str(price_net-position['funding']), costs=costs, path_unresolved=position['path_unresolved']))
        position = None

    ordered = list(pairs)
    if not ordered or any(b<=a for a,b in zip(ordered,ordered[1:])):
        raise ValueError('empty_or_unordered_M1_book_input')
    if end_time_msc is not None and (type(end_time_msc) is not int or end_time_msc<=ordered[-1]):
        raise ValueError('evaluation_end_not_after_last_quote')
    for index, stamp in enumerate(ordered):
        if index%25000 == 0:
            if deadline is not None and time.perf_counter()>deadline:
                raise TimeoutError('index_book_deadline')
            if progress:
                progress(index, len(ordered))
        pair = pairs[stamp]
        queue_due(stamp)
        if previous is not None and stamp>previous+MINUTE and position:
            position['path_unresolved'] = True
            gaps.append(dict(after_time_msc=previous, before_time_msc=stamp, position_id=position['id']))
        # Charges are calendar boundaries crossed while holding, including weekends.
        if day_charge is not None:
            post_funding(stamp)
        else:
            day_charge = (stamp//DAY+1)*DAY
        bid, ask = D(str(pair[0]['open'])), D(str(pair[1]['open']))
        if position:
            opening = bid if position['side']=='BUY' else ask
            protection = core.protective_exit_for_bar(side=position['side'],
                bar=dict(open=opening,high=opening,low=opening,close=opening),stop_loss=position['stop'],
                take_profit=None,spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
            if protection:
                close(stamp, protection['exit_price'], protection['reason'])
        action = None
        if pending and pending['fill_time']<=stamp:
            action, pending = pending, None
            if action['fill_time'] != stamp:
                rejected.append(dict(time_msc=action['fill_time'], reason='missing_fill_minute'))
                action = None
        if action:
            if position and (action['side']=='EXIT' or position['side']!=action['side']):
                close(stamp, bid if position['side']=='BUY' else ask, 'strategy_exit')
            if not position and action['side']!='EXIT':
                side = action['side']
                distance = action['distance']
                quantity = core.size_for_market_stop(distance,instrument=instrument,model=model)
                entry = ask if side=='BUY' else bid
                if quantity is None or quantity>50 or entry*quantity/10>balance:
                    rejected.append(dict(time_msc=stamp,reason='minlot_maxlot_or_margin'))
                else:
                    from decimal import ROUND_FLOOR, ROUND_CEILING
                    stop = entry-distance if side=='BUY' else entry+distance
                    stop = (stop/instrument.tick_size).to_integral_value(rounding=ROUND_FLOOR if side=='BUY' else ROUND_CEILING)*instrument.tick_size
                    entries += 1
                    position = dict(id=f'index-{entries}',side=side,quantity=quantity,bid=bid,ask=ask,
                        stop=stop,time=stamp,funding=D(0),path_unresolved=False)
        if position:
            prices = pair[0 if position['side']=='BUY' else 1]
            protection = core.protective_exit_for_bar(side=position['side'],
                bar={k:prices[k] for k in ('open','high','low','close')},stop_loss=position['stop'],
                take_profit=None,spread_price=0,tick_size=instrument.tick_size,allow_open_gap=True)
            if protection:
                close(stamp,protection['exit_price'],protection['reason'])
        previous = stamp
    # The final observed candle closes without inventing a future fill.
    queue_due(ordered[-1]+MINUTE)
    if end_time_msc is not None:
        post_funding(end_time_msc-1)
    finance_total = sum((D(f['debit_usd']) for f in funding),D(0))
    expected = D(10000)+sum((D(t['price_net_usd']) for t in trades),D(0))-finance_total
    if balance != expected:
        raise ValueError('index_book_cash_reconcile')
    floating = D(0)
    if position:
        last = pairs[ordered[-1]]
        floating = D(str(core.calculate_round_trip_cost(model,position['side'],position['quantity'],instrument.contract_size,
            position['bid'],position['ask'],D(str(last[0]['close'])),D(str(last[1]['close'])))['net_account']))
    return dict(candidate=candidate,slippage_per_side=str(slippage),funding_per_lot_per_day=str(funding_per_lot),
        cost_scenario=cost_scenario,commission_per_lot_per_side_usd=str(core.commission_for_scenario(cost_scenario)),
        null_control=null_control,balance_usd=str(balance),floating_usd=str(floating),
        net_equity_usd=str(balance+floating-10000),entries=entries,closed_trades=len(trades),
        open_position=position,pending_action=pending,trades=trades,decisions=decisions,
        funding_events=funding,funding_total_usd=str(finance_total),gap_events=gaps,rejected=rejected,
        evaluation_end_msc=end_time_msc,last_mark_time_msc=ordered[-1]+MINUTE,
        wall_seconds=time.perf_counter()-began,cpu_seconds=time.process_time()-cpu,
        qualification='development_modeled_M1_only',broker_spec_verified=False,prop_evaluated=False,
        broker_calls=0,model_calls=0)
