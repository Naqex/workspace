"""Calendar and endpoint diagnostics, not a trading or portfolio simulator."""
from collections import defaultdict
from decimal import Decimal as D, localcontext

BPS = D(10000)


def turn_days(sessions):
    months = defaultdict(list)
    for day in sorted(sessions):
        months[day[:7]].append(day)
    return {day for days in months.values() for day in [*days[:3], days[-1]]}


def inspect_day(day, stamps, pairs, *, previous_close=None, previous_close_stamp=None):
    required = dict(cash_open=stamps[0], cash_close=stamps[-1],
                    entry=stamps[0]+120000, exit=stamps[-1])
    missing = [name for name, at in required.items() if at not in pairs]
    result = dict(day=day, required_timestamps=required, missing=missing,
                  previous_close_stamp=previous_close_stamp)
    opening = D(str(pairs[stamps[0]][0]['open'])) if stamps[0] in pairs else None
    closing = D(str(pairs[stamps[-1]][0]['close'])) if stamps[-1] in pairs else None
    if previous_close is not None and opening is not None and closing is not None:
        with localcontext() as context:
            context.prec = 40
            prior = D(str(previous_close))
            ctc, overnight, cash = ((closing/prior).ln()*BPS, (opening/prior).ln()*BPS,
                                    (closing/opening).ln()*BPS)
            if abs(ctc-overnight-cash) > D('1e-30'):
                raise ValueError('calendar_log_return_decomposition_mismatch')
        result.update(ctc_log_bps=ctc, overnight_log_bps=overnight, cash_log_bps=cash)
    else:
        result.update(ctc_log_bps=None, overnight_log_bps=None, cash_log_bps=None)
    if required['entry'] in pairs and required['exit'] in pairs:
        entry = pairs[required['entry']]
        exit_pair = pairs[required['exit']]
        ask, bid = D(str(entry[1]['open'])), D(str(exit_pair[0]['open']))
        result['tradable_net_bps'] = {label: (bid-ask-2*slip)/ask*BPS
            for label, slip in [('reference', D('.25')), ('stress', D('.75'))]}
        result['both_side_zero_volume_fill_minutes'] = [required[name] for name, pair in [('entry',entry),('exit',exit_pair)]
            if pair[0]['volume'] == 0 and pair[1]['volume'] == 0]
    else:
        result['tradable_net_bps'] = None
        result['both_side_zero_volume_fill_minutes'] = []
    return result


def inspect_sessions(sessions, pairs):
    selected, result = turn_days(sessions), []
    previous, previous_stamp = None, None
    for day, stamps in sorted(sessions.items()):
        row = inspect_day(day, stamps, pairs, previous_close=previous, previous_close_stamp=previous_stamp)
        row['group'] = 'TOM' if day in selected else 'REST'
        result.append(row)
        final = pairs.get(stamps[-1])
        # Never jump over a missing predecessor and call the longer gap a daily return.
        previous = D(str(final[0]['close'])) if final is not None else None
        previous_stamp = stamps[-1] if final is not None else None
    return result


def summarize(rows):
    summary = {}
    for group in ['TOM', 'REST']:
        current = [row for row in rows if row['group'] == group]
        metrics = {}
        for metric in ['ctc_log_bps', 'overnight_log_bps', 'cash_log_bps']:
            values = [row[metric] for row in current if row[metric] is not None]
            metrics[metric] = dict(observed=len(values), missing=len(current)-len(values),
                                   mean=str(sum(values,D(0))/len(values)) if values else None)
        for scenario in ['reference','stress']:
            values = [row['tradable_net_bps'][scenario] for row in current if row['tradable_net_bps'] is not None]
            metrics['tradable_'+scenario+'_bps'] = dict(observed=len(values), missing=len(current)-len(values),
                                                       mean=str(sum(values,D(0))/len(values)) if values else None)
        summary[group] = dict(planned=len(current), metrics=metrics,
            days_with_both_side_zero_volume_fill_minutes=sum(bool(row['both_side_zero_volume_fill_minutes']) for row in current))
    return summary
