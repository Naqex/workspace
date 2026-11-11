"""Separate signal reconstruction plus existing financial and first-stop checks."""
from decimal import Decimal as D
from review_index_noise import inspect_funded_scenario

M = 60000


def expected_signals(sessions, pairs, policy):
    if policy not in ('breakout', 'failed_break'):
        raise ValueError('review_policy')
    expected = {}
    for stamps in sessions.values():
        if len(stamps) != 390:
            continue
        seen, direction = [], 0
        for index in range(90):
            point = pairs.get(stamps[index])
            if point is None:
                break
            seen.append(point[0])
            if index == 14:
                ceiling = max(D(str(r['high'])) for r in seen)
                floor = min(D(str(r['low'])) for r in seen)
                if ceiling <= floor:
                    break
            if index < 29 or (index+1) % 15:
                continue
            close = D(str(point[0]['close']))
            prior = direction
            if not direction:
                direction = int(close > ceiling)-int(close < floor)
            chosen = (direction if policy == 'breakout' else
                      -prior if prior and floor <= close <= ceiling else 0)
            if chosen:
                expected[stamps[index]+M] = ('BUY' if chosen > 0 else 'SELL', ceiling-floor)
                break
    return expected


def inspect(result, sessions, pairs):
    expected = expected_signals(sessions, pairs, result['policy'])
    actual = {d['time_msc']: (d['side'], D(d['stop_distance']))
              for d in result['decisions'] if d['side'] in ('BUY', 'SELL')}
    if actual != ({} if result['null_control'] else expected):
        raise ValueError('m15_signal_or_causal_clock_mismatch')
    allowed_exit = {s[0]+151*M for s in sessions.values() if len(s) == 390}
    allowed_exit.update(s[0]+M for s in sessions.values())
    for trade in result['trades']:
        entered, exited = trade['entry_time_msc'], trade['exit_interval_msc'][0]
        side, stop = trade['side'], D(trade['stop'])
        # Earliest barrier must precede scheduled exit; no cherry-picked late stop.
        if not trade['path_unresolved']:
            for at in range(entered, exited, M):
                point = pairs.get(at)
                if point is None:
                    raise ValueError('hidden_missing_held_minute')
                prices = point[0 if side == 'BUY' else 1]
                crossed = (D(str(prices['low'])) <= stop if side == 'BUY'
                           else D(str(prices['high'])) >= stop)
                if crossed:
                    raise ValueError('earlier_stop_was_ignored')
        if trade['reason'] == 'strategy_exit' and exited not in allowed_exit:
            raise ValueError('unregistered_m15_exit_clock')
    financial = inspect_funded_scenario(result, pairs, sessions)
    if result['null_control'] and (result['entries'] or D(result['net_equity_usd'])):
        raise ValueError('m15_null_not_flat')
    return dict(status='signals_and_financial_bindings_verified', financial=financial,
                signal_opportunities=len(expected), reviewer='separate_code_path_same_agent')
