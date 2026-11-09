"""Registered first noise-band break: one attempt per cash session, offline only."""
from collections import deque
from decimal import Decimal as D, ROUND_FLOOR, ROUND_CEILING
import time

from index_noise_study import bands
import nasdaq_opening5_orb as source

CANDIDATE = 'nasdaq-noise14-first-break-opposite-stop-r025-m1-v1'
MINUTE = 60000
HOUR = 3600000


def prepare_plans(sessions, pairs, *, evaluation_start):
    history = deque(maxlen=14)
    previous_close = None
    plans = {}
    for day, stamps in sessions.items():
        opening = pairs.get(stamps[0])
        current_open = D(str(opening[0]['open'])) if source.valid_pair(opening) else None
        closes = {i:D(str(pairs[t][0]['close'])) for i,t in enumerate(stamps)
                  if source.valid_pair(pairs.get(t))}
        decisions = []
        for slot in range(29, len(stamps)-1, 30):
            stamp = stamps[slot]
            boundary = bands(history, current_open, previous_close, slot)
            close = closes.get(slot)
            side = None
            if boundary is not None and close is not None:
                lower, upper = boundary
                side = 'BUY' if close > upper else 'SELL' if close < lower else None
            decisions.append(dict(slot=slot, known_at_msc=stamp+MINUTE,
                                  fill_at_msc=stamp+2*MINUTE, side=side,
                                  close=close, lower=boundary[0] if boundary else None,
                                  upper=boundary[1] if boundary else None,
                                  available=boundary is not None and close is not None))
        if stamps[0] >= evaluation_start:
            first = next((d for d in decisions if d['side'] is not None), None)
            end, reason, exit_decision = stamps[-1], 'scheduled_cash_exit', None
            if first is not None:
                opposite = next((d for d in decisions if d['known_at_msc'] > first['known_at_msc']
                                 and d['side'] is not None and d['side'] != first['side']), None)
                if opposite is not None and opposite['fill_at_msc'] < end:
                    end, reason, exit_decision = opposite['fill_at_msc'], 'opposite_band', opposite['known_at_msc']
            plans[day] = dict(session=day, first_signal=first, terminal_msc=end,
                              terminal_reason=reason, exit_decision_msc=exit_decision,
                              decisions=decisions, previous_sessions=len(history))
        history.append(dict(open=current_open, closes=closes))
        previous_close = closes.get(len(stamps)-1)
    return plans


def exit_bounds(position, pairs, hours, plan, *, conditional, deadline=None):
    side = position['side']
    idx = 0 if side == 'BUY' else 1
    stop = position['stop']
    possible, uncertainties, checked = [], [], set()
    mark = None
    for at in range(position['entry_time_msc'], plan['terminal_msc']+MINUTE, MINUTE):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError('noise14_deadline')
        pair = pairs.get(at)
        if not source.valid_pair(pair):
            if pair is not None or not conditional or at == plan['terminal_msc']:
                return dict(unknown=True, at_msc=at, reason='missing_or_crossed_held_or_terminal_minute', last_mark=mark)
            hour = at//HOUR*HOUR
            hp = hours.get(hour)
            if not source.valid_pair(hp):
                return dict(unknown=True, at_msc=at, reason='missing_or_crossed_H1_envelope', last_mark=mark)
            row = hp[idx]
            lo, hi = D(str(row['low'])), D(str(row['high']))
            if (row['timestamp'] != hour or not lo.is_finite() or not hi.is_finite()
                    or lo <= 0 or hi < lo or lo % D('.001') or hi % D('.001')):
                raise ValueError('invalid_noise14_H1_envelope')
            if hour not in checked:
                for t in range(hour, hour+HOUR, MINUTE):
                    observed = pairs.get(t)
                    if observed is not None and (not source.valid_pair(observed)
                            or any(not lo <= D(str(observed[idx][k])) <= hi for k in ('open','high','low','close'))):
                        raise ValueError('noise14_H1_excludes_or_crosses_observed_M1')
                checked.add(hour)
            if idx == 0 and lo <= stop: possible.extend([lo, stop])
            if idx == 1 and hi >= stop: possible.extend([stop, hi])
            uncertainties.append(dict(at_msc=at, hour_msc=hour, side='bid' if idx == 0 else 'ask', low=lo, high=hi))
            continue
        bar = {k:D(str(pair[idx][k])) for k in ('open','high','low','close')}
        opened = {k:bar['open'] for k in bar}
        hit = source.core.protective_exit_for_bar(side=side, bar=opened, stop_loss=stop,
                 take_profit=None, spread_price=0, tick_size=D('.001'), allow_open_gap=True)
        if hit is None and at == plan['terminal_msc']:
            hit = dict(exit_price=bar['open'], reason=plan['terminal_reason'])
        if hit is None:
            hit = source.core.protective_exit_for_bar(side=side, bar=bar, stop_loss=stop,
                     take_profit=None, spread_price=0, tick_size=D('.001'), allow_open_gap=True)
        if hit is not None:
            possible.append(hit['exit_price'])
            return dict(unknown=False, lower=min(possible), upper=max(possible),
                        terminal_msc=at+MINUTE, reason=hit['reason'], uncertainties=uncertainties)
        mark = dict(source_minute_msc=at, bid=D(str(pair[0]['close'])), ask=D(str(pair[1]['close'])))
    raise ValueError('noise14_position_without_terminal')


def simulate(plans, pairs, hours, *, scenario, conditional=False, null_control=False,
             deadline=None, progress=None):
    began = time.perf_counter()
    instrument, model, _ = source.core.market(scenario)
    low = high = D(10000)
    trades, rows, unknown = [], [], None
    for number,(day,plan) in enumerate(plans.items()):
        if number % 32 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('noise14_deadline')
            if progress: progress(number,len(plans))
        row = dict(session=day, status='no_signal')
        rows.append(row)
        if null_control:
            row['status'] = 'null_no_action'
            continue
        if unknown is not None:
            row['status'] = 'blocked_unknown_exposure'
            continue
        first = plan['first_signal']
        if first is None:
            continue
        side = first['side']
        at = first['fill_at_msc']
        pair = pairs.get(at)
        if not source.valid_pair(pair):
            row['status'] = 'missing_or_crossed_exact_entry'
            continue
        bid, ask = (D(str(pair[i]['open'])) for i in (0,1))
        entry = ask if side == 'BUY' else bid
        raw_stop = first['lower'] if side == 'BUY' else first['upper']
        stop = (raw_stop/instrument.tick_size).to_integral_value(rounding=ROUND_FLOOR if side == 'BUY' else ROUND_CEILING)*instrument.tick_size
        distance = entry-stop if side == 'BUY' else stop-entry
        if distance <= 0 or stop <= 0:
            row['status'] = 'invalid_stop_after_delay'
            continue
        quantity = source.core.size_for_market_stop(distance, instrument=instrument, model=model, budget=D(25))
        if quantity is None or quantity > 50:
            row['status'] = 'min_max_quantity_or_margin'
            continue
        margin = entry*quantity*instrument.contract_size/10
        a, b = (balance >= max(margin,D(25)) for balance in (low,high))
        if a != b:
            unknown = dict(reason='cash_interval_changes_entry_eligibility', session=day, at_msc=at,
                           cash_lower_usd=low,cash_upper_usd=high)
            row['status'] = 'unknown_entry_eligibility'
            continue
        if not a:
            row['status'] = 'min_max_quantity_or_margin'
            continue
        risk = (distance+2*model.slippage_price_per_side)*quantity*instrument.contract_size
        if risk > 25:
            raise ValueError('noise14_planned_risk_exceeded')
        position = dict(session=day,side=side,quantity=quantity,entry_bid=bid,entry_ask=ask,entry_quote=entry,
                        decision_time_msc=first['known_at_msc'],entry_time_msc=at,stop=stop,
                        planned_stop_risk_usd=risk,margin_usd=margin)
        terminal = exit_bounds(position,pairs,hours,plan,conditional=conditional,deadline=deadline)
        if terminal['unknown']:
            unknown = dict(position=position,**terminal)
            row['status'] = 'unknown_exposure'
            continue
        values = [D(str(source.core.calculate_round_trip_cost(model,side,quantity,instrument.contract_size,
                  bid,ask,price,price)['net_account'])) for price in (terminal['lower'],terminal['upper'])]
        lo, hi = min(values), max(values)
        trades.append(dict(**position,exit_lower=terminal['lower'],exit_upper=terminal['upper'],
                           terminal_msc=terminal['terminal_msc'],reason=terminal['reason'],
                           uncertainties=terminal['uncertainties'],net_lower_usd=lo,net_upper_usd=hi))
        low += lo
        high += hi
        row['status'] = 'conditionally_bounded' if terminal['uncertainties'] else 'exact_model_closed'
    if (low != 10000+sum((t['net_lower_usd'] for t in trades),D(0))
            or high != 10000+sum((t['net_upper_usd'] for t in trades),D(0))):
        raise ValueError('noise14_cash_reconciliation')
    return dict(candidate=CANDIDATE,scenario=scenario,conditional=conditional,null_control=null_control,
                trades=trades,session_rows=rows,unknown=unknown,closed_trades=len(trades),
                entries=len(trades)+bool(unknown is not None and 'position' in unknown),
                uncertain_trades=sum(bool(t['uncertainties']) for t in trades),
                known_closed_lower_usd=low-10000,known_closed_upper_usd=high-10000,
                net_lower_usd=None if unknown else low-10000,net_upper_usd=None if unknown else high-10000,
                account_state='unknown' if unknown else 'conditional_model_terminal' if conditional else 'exact_model_flat',
                starting_balance_usd=D(10000),wall_seconds=time.perf_counter()-began,
                actual_account_state_verified=False,clean_oos=False,prop_evaluated=False,
                holdout_read=False,execution_authorized=False,broker_calls=0,model_calls=0)
