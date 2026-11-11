"""Two registered M15 signal policies over the existing modeled M1 index book."""
from collections import Counter
from decimal import Decimal as D
import index_m1_book as book
import index_noise_study as core

M = 60000
CANDIDATES = {
    'breakout': 'us500-m15-or15-firstbreak-width-stop-noon-v1',
    'failed_break': 'us500-m15-or15-failedbreak-width-stop-noon-v1',
}


def plans_for(sessions, pairs, policy):
    if policy not in CANDIDATES:
        raise ValueError('unregistered_m15_policy')
    plans, days = {}, []
    for day, stamps in sessions.items():
        plans[stamps[0]] = dict(side='EXIT', basis='cash_open_recovery')
        row = dict(session=day, status='calendar_short_session', signal=None)
        days.append(row)
        if len(stamps) != 390:
            continue
        plans[stamps[150]] = dict(side='EXIT', basis='noon_decision_1201_fill')
        prefix = [pairs.get(t) for t in stamps[:15]]
        if any(p is None for p in prefix):
            row['status'] = 'opening_range_unavailable'
            continue
        high = max(D(str(p[0]['high'])) for p in prefix)
        low = min(D(str(p[0]['low'])) for p in prefix)
        if high <= low:
            row['status'] = 'zero_opening_range'
            continue
        row.update(range_high=str(high), range_low=str(low), status='no_signal')
        first_side = None
        for elapsed in range(30, 91, 15):
            if any(t not in pairs for t in stamps[elapsed-15:elapsed]):
                row['status'] = 'causal_prefix_unavailable'
                break
            close = D(str(pairs[stamps[elapsed-1]][0]['close']))
            side = None
            if first_side is None:
                first_side = 'BUY' if close > high else 'SELL' if close < low else None
                if policy == 'breakout':
                    side = first_side
            elif policy == 'failed_break' and low <= close <= high:
                side = 'SELL' if first_side == 'BUY' else 'BUY'
            if side:
                at = stamps[elapsed-1] + M
                plans[at] = dict(side=side, distance=high-low,
                                 basis=f'{policy}_closed_M15_first_event')
                row.update(status='signal_ready', signal=dict(decision_msc=at,
                    side=side, distance=str(high-low), entry_msc=at+M))
                break
    return plans, days


def simulate(sessions, pairs, *, policy, slippage, null_control=False, progress=None, deadline=None):
    plans, days = plans_for(sessions, pairs, policy)
    result = book.simulate(pairs, plans, candidate=CANDIDATES[policy], slippage=slippage,
        funding_per_lot=D(1) if slippage == D('.25') else D(2),
        null_control=null_control, progress=progress, deadline=deadline,
        cost_scenario=core.FTMO_ZERO_COMMISSION)
    result.update(session_rows=days, policy=policy)
    return result


def metrics(result):
    trades = result['trades']
    nets = [D(t['net_usd']) for t in trades]
    unknown = bool(result['gap_events'] or result['open_position'] or result['pending_action'])
    wins, losses = [n for n in nets if n > 0], [n for n in nets if n < 0]
    equity = peak = D(10000)
    drawdown = D(0)
    streak = worst = 0
    for n in nets:
        equity += n
        peak = max(peak, equity)
        drawdown = max(drawdown, peak-equity)
        streak = streak+1 if n < 0 else 0
        worst = max(worst, streak)
    quote_gross = sum(((D(t['exit_fill'])-D(t['entry_fill']))
                       * (1 if t['side'] == 'BUY' else -1)*D(t['quantity']) for t in trades), D(0))
    slippage = sum((2*D(result['slippage_per_side'])*D(t['quantity']) for t in trades), D(0))
    funding = D(result['funding_total_usd'])
    # Quotes already embed spread; gross here is before explicit extra charges.
    return dict(entries=result['entries'], closed=len(trades),
        full_net_usd=None if unknown else result['net_equity_usd'],
        modeled_net_usd=result['net_equity_usd'], known_closed_net_usd=str(sum(nets, D(0))),
        unknown_path=unknown, gap_events=len(result['gap_events']),
        winrate_percent=str(D(len(wins))*100/len(nets)) if nets else None,
        average_win_usd=str(sum(wins)/len(wins)) if wins else None,
        average_loss_usd=str(sum(losses)/len(losses)) if losses else None,
        mean_planned_R=str(sum(nets)/len(nets)/25) if nets else None,
        closed_balance_dd_usd=str(drawdown), max_loss_streak=worst,
        top5_net_usd=str(sum(sorted(nets, reverse=True)[:5], D(0))),
        quote_gross_usd=str(quote_gross), extra_slippage_usd=str(slippage),
        commission_usd='0', funding_usd=str(funding),
        rounding_residual_usd=str(sum(nets,D(0))-(quote_gross-slippage-funding)),
        signal_census=dict(Counter(d['status'] for d in result['session_rows'])),
        rejections=dict(Counter(r['reason'] for r in result['rejected'])),
        prop_compliance='unknown', clean_oos=False, broker_spec_verified=False)
