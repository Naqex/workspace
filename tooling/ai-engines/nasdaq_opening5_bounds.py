"""Conditional outer bounds, never a repair of missing executable quotes.

The frozen exact model remains authoritative for its own unknown verdict.
Coarse envelopes below are retrospective uncertainty assumptions, not signals.
"""
from decimal import Decimal as D
import time

import nasdaq_opening5_orb as parent

MINUTE = parent.MINUTE
HOUR = 3600000


def exit_envelope(position, pairs, hours, *, scheduled_exit, deadline=None):
    from trading_workspace_v2.execution_semantics import IntrabarAmbiguityError

    side = position['side']
    index = 0 if side == 'BUY' else 1
    stop, target = position['stop'], position['take_profit']
    possibilities, uncertainties, checked_hours = [], [], set()
    for stamp in range(position['entry_time_msc'], scheduled_exit+MINUTE, MINUTE):
        if deadline is not None and time.perf_counter() > deadline:
            raise TimeoutError('bounds_deadline')
        pair = pairs.get(stamp)
        if pair is not None and not parent.valid_pair(pair):
            raise ValueError('crossed_source_not_a_missing_minute')
        if pair is None:
            if stamp == scheduled_exit:
                raise ValueError('missing_scheduled_exit_no_terminal_bound')
            hour = stamp//HOUR*HOUR
            coarse_pair = hours.get(hour)
            if coarse_pair is None or not parent.valid_pair(coarse_pair):
                raise ValueError('missing_or_crossed_H1_envelope')
            coarse = coarse_pair[index]
            low, high = D(str(coarse['low'])), D(str(coarse['high']))
            if (coarse['timestamp'] != hour or not low.is_finite() or not high.is_finite()
                    or low <= 0 or high < low or low % D('.001') or high % D('.001')):
                raise ValueError('invalid_H1_envelope')
            if hour not in checked_hours:
                for at in range(hour, hour+HOUR, MINUTE):
                    observed = pairs.get(at)
                    if observed is not None:
                        if not parent.valid_pair(observed):
                            raise ValueError('crossed_source_in_envelope_hour')
                        row = observed[index]
                        if any(not low <= D(str(row[k])) <= high for k in ('open','high','low','close')):
                            raise ValueError('H1_excludes_observed_M1')
                checked_hours.add(hour)
            if side == 'BUY':
                if low <= stop: possibilities.append((low, stop))
                if high >= target: possibilities.append((target, high))
            else:
                if high >= stop: possibilities.append((stop, high))
                if low <= target: possibilities.append((low, target))
            uncertainties.append(dict(at_msc=stamp, reason='missing_M1_conditional_H1_envelope',
                                      H1_open_msc=hour, side='bid' if index == 0 else 'ask',
                                      low=low, high=high))
            # Retain a surviving branch, including the possibility of no quote.
            continue
        bar = {k:D(str(pair[index][k])) for k in ('open','high','low','close')}
        opened = {k:bar['open'] for k in bar}
        hit = parent.core.protective_exit_for_bar(side=side, bar=opened, stop_loss=stop,
                take_profit=target, spread_price=0, tick_size=D('.001'), allow_open_gap=True)
        if hit is None and stamp == scheduled_exit:
            hit = dict(exit_price=bar['open'], reason='scheduled_cash_exit')
        if hit is None:
            try:
                hit = parent.core.protective_exit_for_bar(side=side, bar=bar, stop_loss=stop,
                        take_profit=target, spread_price=0, tick_size=D('.001'), allow_open_gap=True)
            except IntrabarAmbiguityError:
                possibilities.append((min(stop,target), max(stop,target)))
                uncertainties.append(dict(at_msc=stamp, reason='same_M1_both_barriers'))
                return dict(exit_price_lower=min(x[0] for x in possibilities),
                            exit_price_upper=max(x[1] for x in possibilities),
                            latest_terminal_msc=stamp+MINUTE, terminal_reason='both_barriers_order_unknown',
                            uncertainties=uncertainties)
        if hit is not None:
            price = hit['exit_price']
            possibilities.append((price,price))
            return dict(exit_price_lower=min(x[0] for x in possibilities),
                        exit_price_upper=max(x[1] for x in possibilities),
                        latest_terminal_msc=stamp+MINUTE, terminal_reason=hit['reason'],
                        uncertainties=uncertainties)
    raise ValueError('no_terminal_bound')


def simulate(sessions, pairs, hours, *, start, end, scenario, null_control=False,
             progress=None, deadline=None):
    began = time.perf_counter()
    parent.validate_inputs(sessions, pairs, start=start, end=end)
    if scenario not in parent.core.SCENARIOS:
        raise ValueError('unregistered_bounds_cost')
    instrument, model, _ = parent.core.market(scenario)
    cash_low = cash_high = D(10000)
    trades, rows = [], []
    for i,(day,stamps) in enumerate(sessions.items()):
        if i % 32 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('bounds_deadline')
            if progress: progress(i, len(sessions))
        plan = parent.opening_plan(stamps, pairs)
        row = dict(session=day, status=plan['status'])
        rows.append(row)
        if null_control:
            row['status'] = 'null_no_action'
            continue
        if plan['side'] is None:
            continue
        pair = pairs.get(plan['entry_time_msc'])
        if not parent.valid_pair(pair):
            row['status'] = 'missing_or_crossed_exact_entry'
            continue
        bid, ask = (D(str(pair[k]['open'])) for k in (0,1))
        side, stop = plan['side'], plan['stop']
        entry = ask if side == 'BUY' else bid
        distance = entry-stop if side == 'BUY' else stop-entry
        target = entry+10*distance if side == 'BUY' else entry-10*distance
        if distance <= 0 or min(stop,target) <= 0:
            row['status'] = 'invalid_protection_bracket'
            continue
        quantity = parent.core.size_for_market_stop(distance, instrument=instrument, model=model, budget=D(25))
        if quantity is None or quantity > 50:
            row['status'] = 'min_max_quantity_margin_or_cash'
            continue
        margin = entry*quantity*instrument.contract_size/10
        eligible_low, eligible_high = (balance >= max(D(25),margin) for balance in (cash_low,cash_high))
        if eligible_low != eligible_high:
            raise ValueError('cash_interval_changes_entry_eligibility')
        if not eligible_low:
            row['status'] = 'min_max_quantity_margin_or_cash'
            continue
        risk = (distance+2*model.slippage_price_per_side)*quantity*instrument.contract_size
        if risk > 25:
            raise ValueError('planned_budget_exceeded')
        position = dict(session=day, side=side, quantity=quantity, entry_bid=bid, entry_ask=ask,
                        entry_quote=entry, entry_time_msc=plan['entry_time_msc'],
                        decision_time_msc=plan['known_at_msc'], stop=stop, take_profit=target,
                        planned_stop_risk_usd=risk, margin_usd=margin)
        exits = exit_envelope(position, pairs, hours, scheduled_exit=plan['scheduled_exit_msc'], deadline=deadline)
        costs = [parent.core.calculate_round_trip_cost(model, side, quantity, instrument.contract_size,
                 bid, ask, p, p) for p in (exits['exit_price_lower'],exits['exit_price_upper'])]
        nets = [D(str(c['net_account'])) for c in costs]
        low, high = min(nets), max(nets)
        trades.append(dict(**position, **exits, net_lower_usd=low, net_upper_usd=high))
        cash_low += low
        cash_high += high
        row['status'] = 'conditionally_bounded_trade' if exits['uncertainties'] else 'exact_model_trade'
    if (cash_low != 10000+sum((t['net_lower_usd'] for t in trades),D(0))
            or cash_high != 10000+sum((t['net_upper_usd'] for t in trades),D(0))):
        raise ValueError('interval_cash_reconciliation')
    return dict(candidate=parent.CANDIDATE, scenario=scenario, null_control=null_control,
                year=int(next(iter(sessions))[:4]), trades=trades, session_rows=rows,
                entries=len(trades), uncertain_trades=sum(bool(t['uncertainties']) for t in trades),
                net_lower_usd=cash_low-10000, net_upper_usd=cash_high-10000,
                account_state='conditional_model_terminal', actual_account_state_verified=False,
                parent_unknown_cleared=False, conditional_on_H1_envelope_and_parent_execution=True,
                starting_balance_usd=D(10000), wall_seconds=time.perf_counter()-began,
                clean_oos=False, prop_evaluated=False, execution_authorized=False,
                holdout_read=False, broker_calls=0, model_calls=0)
