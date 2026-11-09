"""Registered quote-sampled round-level crossing; never broker execution."""
from datetime import date, datetime, timedelta
from decimal import Decimal as D, ROUND_CEILING, ROUND_FLOOR
from zoneinfo import ZoneInfo

NY = ZoneInfo('America/New_York')
YEARS = (2019, 2022)
OFFSETS = {'round': D(0), 'placebo': D('.0025')}
STEP = D('.0050')


def days():
    return [date.fromordinal(at) for y in YEARS
            for at in range(date(y, 1, 1).toordinal(), date(y+1, 1, 1).toordinal())
            if date.fromordinal(at).weekday() < 5]


def targets(day):
    if day.year not in YEARS or day.weekday() >= 5:
        raise ValueError('R091_unregistered_day')
    start = datetime(day.year, day.month, day.day, 9, tzinfo=NY)
    return [int((start+timedelta(minutes=5*i)).timestamp())*1000 for i in range(84)]


def endpoint(q, target):
    if q is None:
        return None
    if type(q['time_msc']) is not int or type(q['sequence']) is not int or q['sequence'] < 1:
        raise ValueError('R091_quote_identity')
    bid, ask = (D(str(q[k])) for k in ('bid', 'ask'))
    if any(not p.is_finite() or p <= 0 or p % D('.00001') for p in (bid, ask)) or bid > ask:
        raise ValueError('R091_quote_price')
    return q if 0 <= q['time_msc']-target <= 60000 else None


def crossing(previous, current, geometry):
    if geometry not in OFFSETS:
        raise ValueError('R091_unknown_geometry')
    offset = OFFSETS[geometry]
    hits = []
    pa, ca = D(str(previous['ask'])), D(str(current['ask']))
    pb, cb = D(str(previous['bid'])), D(str(current['bid']))
    if ca > pa:
        level = offset+((pa-offset)/STEP).to_integral_value(rounding=ROUND_CEILING)*STEP
        if level < ca:
            if level+STEP < ca:
                return dict(status='ambiguous', side=None, level=None)
            hits.append(('BUY', level))
    if cb < pb:
        level = offset+((pb-offset)/STEP).to_integral_value(rounding=ROUND_FLOOR)*STEP
        if level > cb:
            if level-STEP > cb:
                return dict(status='ambiguous', side=None, level=None)
            hits.append(('SELL', level))
    if len(hits) > 1:
        return dict(status='ambiguous', side=None, level=None)
    return dict(status='cross' if hits else 'no_cross', side=hits[0][0] if hits else None,
                level=str(hits[0][1]) if hits else None)


def feature(day, quotes, geometry):
    slots = targets(day)
    result = dict(day=day.isoformat(), year=day.year, geometry=geometry,
                  status='no_cross', selected=False, side=None, level=None,
                  crossing_ms=None, decision_ms=None, entry_ms=None, exit_ms=None)
    previous = endpoint(quotes.get(slots[0]), slots[0])
    if previous is None:
        return {**result, 'status': 'unavailableprefix'}
    for i in range(1, 71):
        target = slots[i]
        current = endpoint(quotes.get(target), target)
        if current is None:
            return {**result, 'status': 'unavailableprefix'}
        if not previous['time_msc'] < current['time_msc'] or not previous['sequence'] < current['sequence']:
            raise ValueError('R091_feature_quote_order')
        hit = crossing(previous, current, geometry)
        if hit['status'] == 'ambiguous':
            return {**result, 'status': 'ambiguous'}
        if hit['status'] == 'cross':
            return {**result, **hit, 'selected': True, 'crossing_ms': target,
                    'decision_ms': target+60000, 'entry_ms': slots[i+1], 'exit_ms': slots[i+13]}
        previous = current
    return result
