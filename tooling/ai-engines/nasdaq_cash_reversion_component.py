"""Frozen NASDAQ cash reversion price component; no sizing or broker authority."""
from decimal import Decimal as D, ROUND_HALF_UP
import time

from index_daily_reversion import plans_for, RSI
from cash_rsi_signal_oracle import oracle_plans

MINUTE, HOUR, DAY = 60_000, 3_600_000, 86_400_000
CANDIDATE = 'nasdaq-cash-cutler3-10-40-ibs05-component-v1'
SCENARIOS = {'reference': (D('.25'), D('.08')), 'stress': (D('.75'), D('.16'))}


def prepare(sessions, pairs):
    # Only the parent's cash-indicator math is reused, never its US500 market/book.
    plans = plans_for(sessions, pairs, RSI)
    expected = oracle_plans(sessions, pairs)
    if set(plans) != set(expected) or any(
            plans[t]['side'] != expected[t]['side'] or
            (plans[t]['side'] == 'BUY' and
             abs(plans[t]['distance']-D(expected[t]['distance'].numerator)/D(expected[t]['distance'].denominator)) > D('1e-10'))
            for t in plans):
        raise ValueError('independent_cash_signal_mismatch')
    return plans


def simulate(pairs, plans, *, start, end, scenario, null_control=False,
             progress=None, deadline=None):
    began, cpu = time.perf_counter(), time.process_time()
    if scenario not in SCENARIOS:
        raise ValueError('unregistered_component_cost')
    stamps = list(pairs)
    if (type(start) is not int or type(end) is not int or start % DAY or end % DAY or end <= start
            or not stamps or stamps != sorted(set(stamps)) or stamps[-1] >= end):
        raise ValueError('invalid_component_interval_or_order')
    for at, pair in pairs.items():
        if type(at) is not int or at % MINUTE or len(pair) != 2:
            raise ValueError('component_pair_clock')
        for row in pair:
            prices = [D(str(row[k])) for k in ('open', 'high', 'low', 'close')]
            if row['timestamp'] != at or any(not x.is_finite() or x <= 0 or x % D('.001') for x in prices):
                raise ValueError('component_price_clock_grid')
            o, h, l, c = prices
            if not l <= min(o, c) <= max(o, c) <= h:
                raise ValueError('component_OHLC')
        if any(D(str(pair[1][k])) < D(str(pair[0][k])) for k in ('open', 'close')):
            raise ValueError('component_crossed_endpoints')
    events = sorted(t for t in plans if start <= t < end)
    if any(type(t) is not int or t % MINUTE or plans[t]['side'] not in ('BUY', 'EXIT') for t in events):
        raise ValueError('component_decision_contract')
    times = [t for t in stamps if t >= start]
    if not times:
        raise ValueError('empty_component_evaluation')
    slip, annual = SCENARIOS[scenario]
    position = pending = None
    cursor = entries = 0
    realized = D(0)
    trades, decisions, funding, rejected, gaps = [], [], [], [], []
    charge_time = start+22*HOUR
    previous = None

    def queue(boundary):
        nonlocal cursor, pending
        while cursor < len(events) and events[cursor] <= boundary:
            at = events[cursor]
            cursor += 1
            plan = plans[at]
            decisions.append(dict(time_msc=at, side=plan['side'], basis=plan.get('basis'),
                                  action_enabled=not null_control))
            if not null_control:
                if pending:
                    rejected.append(dict(**pending, reason='unfilled_before_next_decision'))
                pending = dict(side=plan['side'], decision_time_msc=at, fill_time_msc=at+MINUTE)

    def finance(boundary):
        nonlocal charge_time
        while charge_time <= boundary:
            if position is not None and position['entry_time_msc'] < charge_time:
                debit = (position['entry_ask']*annual/365).quantize(D('.01'), rounding=ROUND_HALF_UP)
                position['funding_usd'] += debit
                funding.append(dict(time_msc=charge_time, position_id=position['id'], debit_usd=debit))
            charge_time += DAY

    for i, at in enumerate(times):
        if i % 25000 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('cash_component_deadline')
            if progress:
                progress(i, len(times))
        queue(at)
        finance(at)
        if position and previous is not None and at > previous+MINUTE:
            position['path_unresolved'] = True
            gaps.append(dict(after_time_msc=previous, before_time_msc=at, position_id=position['id']))
        if pending and pending['fill_time_msc'] <= at:
            action, pending = pending, None
            if action['fill_time_msc'] != at:
                rejected.append(dict(**action, reason='missing_exact_fill_minute'))
            elif action['side'] == 'BUY' and position is None:
                entries += 1
                position = dict(id=f'cash-component-{entries}', entry_time_msc=at,
                    decision_time_msc=action['decision_time_msc'], entry_ask=D(str(pairs[at][1]['open'])),
                    funding_usd=D(0), path_unresolved=False)
            elif action['side'] == 'EXIT' and position is not None:
                bid = D(str(pairs[at][0]['open']))
                price_net = (bid-position['entry_ask']-2*slip).quantize(D('.01'), rounding=ROUND_HALF_UP)
                realized += price_net
                trades.append(dict(**position, exit_time_msc=at, exit_decision_time_msc=action['decision_time_msc'],
                    exit_bid=bid, price_net_usd=price_net, net_usd=price_net-position['funding_usd']))
                position = None
        previous = at
    queue(end-1)
    finance(end-1)
    total_funding = sum((f['debit_usd'] for f in funding), D(0))
    floating = D(0)
    if position:
        floating = (D(str(pairs[times[-1]][0]['close']))-position['entry_ask']-2*slip).quantize(D('.01'), rounding=ROUND_HALF_UP)
        if times[-1]+MINUTE < end:
            position['path_unresolved'] = True
            gaps.append(dict(after_time_msc=times[-1], before_time_msc=end, position_id=position['id'], reason='unobserved_final_tail'))
    if realized != sum((t['price_net_usd'] for t in trades), D(0)):
        raise ValueError('component_realized_reconciliation')
    return dict(candidate=CANDIDATE, scenario=scenario, source_instrument='USATECH.IDX/USD',
        qualification='development_price_component_per_one_hypothetical_unit_not_account',
        null_control=null_control, entries=entries, closed_trades=len(trades),
        realized_price_net_usd=realized, floating_price_net_usd=floating,
        funding_total_usd=total_funding, net_component_usd=realized+floating-total_funding,
        trades=trades, funding_events=funding, decisions=decisions, open_position=position,
        pending_action=pending, rejected=rejected, gap_events=gaps,
        start_time_msc=start, end_time_msc=end, last_mark_time_msc=times[-1]+MINUTE,
        broker_calls=0, model_calls=0, strategy_account_simulated=False,
        execution_authorized=False, prop_evaluated=False, clean_oos=False,
        wall_seconds=time.perf_counter()-began, cpu_seconds=time.process_time()-cpu)


def retained(results):
    stress = [r for r in results if r['scenario'] == 'stress' and not r['null_control']]
    windows = {(r['start_time_msc'], r['end_time_msc']) for r in stress}
    return len(stress) == len(windows) == 2 and all(r['net_component_usd'] > 0 and r['closed_trades'] >= 10
        and not r['rejected'] and r['open_position'] is None and r['pending_action'] is None for r in stress)
