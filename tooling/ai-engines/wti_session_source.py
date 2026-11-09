"""Bounded WTI session source roles; no return/signal/order calculations."""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal as D
from zoneinfo import ZoneInfo

LABELS = ('2019-02-04', '2019-02-05', '2019-07-02',
          '2022-02-07', '2022-02-08', '2022-07-05')
NY = ZoneInfo('America/New_York')


def slots(label):
    if label not in LABELS:
        raise ValueError('unregistered_source_session')
    day = date.fromisoformat(label)
    start = datetime.combine(day-timedelta(days=1), datetime.min.time(), NY).replace(hour=18)
    end = datetime.combine(day, datetime.min.time(), NY).replace(hour=16, minute=55)
    result = list(range(int(start.timestamp())*1000, int(end.timestamp())*1000+1, 300000))
    if len(result) != 276:
        raise ValueError('session_role_census')
    return result


def utc_dates():
    return sorted({datetime.fromtimestamp(at/1000, timezone.utc).date().isoformat()
                   for label in LABELS for at in slots(label)})


def coverage(label, sides):
    wanted = slots(label)
    if set(sides) != {'bid', 'ask'}:
        raise ValueError('both_source_sides_required')
    paired = set(sides['bid']) & set(sides['ask'])
    available = sorted(set(wanted) & paired)
    for at in available:
        for key in ('open', 'close'):
            bid, ask = (D(str(sides[side][at][key])) for side in ('bid', 'ask'))
            if any(not p.is_finite() or p <= 0 or p % D('.001') for p in (bid, ask)) or bid > ask:
                raise ValueError('invalid_or_crossed_role_price')
    missing = sorted(set(wanted)-paired)
    endpoints = [at for at in (wanted[0], wanted[-1]) if at not in paired]
    return dict(label=label, expected=len(wanted), paired=len(available), missing=missing,
                missing_endpoints=endpoints, first_paired_ms=available[0] if available else None,
                last_paired_ms=available[-1] if available else None,
                admitted=not endpoints and len(available)*100 >= len(wanted)*98)
