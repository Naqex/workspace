"""Own R089 causal day-proxy feature; no fills, account model or orders.

Economic motivation and differences from Caporale & Plastun (2020/2021):
planning/research/FX-ABNORMAL-DAY-METHOD-ADMISSION-20261109.md.
"""
from datetime import date, datetime, time, timedelta, timezone
from decimal import Decimal
from fractions import Fraction

LOOKBACK = 20
K_SQUARED = 4
MINUTE = 60_000
GRID = Decimal('0.00001')
DAY_PROXY_END_HOUR = 20
FEATURE_VERSION = 'R089-prior-UTC20h-abnormal-day-v2'


def utc_ms(day, hour, minute=0):
    return int(datetime.combine(day, time(hour, minute), timezone.utc).timestamp()) * 1000


def calibration_days(shock_day):
    days = []
    cursor = shock_day - timedelta(days=1)
    while len(days) < LOOKBACK:
        if cursor.weekday() < 5:
            days.append(cursor)
        cursor -= timedelta(days=1)
    return list(reversed(days))


def schedule(entry_day):
    if entry_day.year not in (2019, 2022) or entry_day.weekday() >= 5:
        raise ValueError('R089_registered_entry_day_required')
    previous = entry_day - timedelta(days=1)
    return dict(day=entry_day.isoformat(), shock_day=previous.isoformat(),
        calendar_eligible=entry_day.weekday() in (1, 2, 3, 4),
        decision_ms=utc_ms(entry_day, 0, 59), entry_ms=utc_ms(entry_day, 1),
        exit_decision_ms=utc_ms(entry_day, 7, 59), exit_ms=utc_ms(entry_day, 8))


def _mid(quote, target, decision):
    if quote is None:
        return None
    at = quote['time_msc']
    known = quote['known_at_upper_bound_ms']
    if type(at) is not int or type(known) is not int or not at <= known < decision:
        raise ValueError('R089_future_or_invalid_source_clock')
    prices = [Decimal(str(quote[key])) for key in ('bid', 'ask')]
    if any(not p.is_finite() or p <= 0 or p % GRID for p in prices) or prices[0] > prices[1]:
        raise ValueError('R089_invalid_source_price')
    if not 0 <= at - target <= MINUTE:
        return None
    return sum((Fraction(p) for p in prices), Fraction(0)) / 2


def _return(observation, day, decision):
    if observation is None:
        return None
    if observation['day'] != day.isoformat():
        raise ValueError('R089_wrong_observation_day')
    a = _mid(observation['start'], utc_ms(day, 0), decision)
    b = _mid(observation['end'], utc_ms(day, DAY_PROXY_END_HOUR), decision)
    return b / a - 1 if a is not None and b is not None else None


def rational(value):
    return dict(numerator=value.numerator, denominator=value.denominator)


def feature(entry_day, observations):
    """Read only prior registered weekdays; current/future outcome prices are irrelevant."""
    row = dict(**schedule(entry_day), status='calendar_skip', primary_side=None,
        shock_tail=None, feature_version=FEATURE_VERSION,
        scope='feature_only_not_account', execution_authorized=False)
    if not row['calendar_eligible']:
        return row
    shock_day = date.fromisoformat(row['shock_day'])
    prior = calibration_days(shock_day)
    required = prior + [shock_day]
    values = [_return(observations.get(d.isoformat()), d, row['decision_ms']) for d in required]
    row['calibration_days'] = [d.isoformat() for d in prior]
    row['missing_days'] = [d.isoformat() for d, r in zip(required, values) if r is None]
    if row['missing_days']:
        row['status'] = 'unavailable_history'
        return row
    history, change = values[:-1], values[-1]
    mean = sum(history, Fraction(0)) / LOOKBACK
    variance = sum(((r - mean) ** 2 for r in history), Fraction(0)) / (LOOKBACK - 1)
    row.update(shock_return=rational(change), calibration_mean=rational(mean),
        calibration_sample_variance=rational(variance))
    if variance == 0:
        row['status'] = 'unavailable_zero_variance'
        return row
    row['status'] = 'normal'
    delta = change - mean
    # Exact inequality keeps equality outside the tails without rounding a square root.
    if delta * delta > K_SQUARED * variance:
        if change > 0 and delta > 0:
            row.update(status='shock', shock_tail='positive', primary_side='SELL')
        elif change < 0 and delta < 0:
            row.update(status='shock', shock_tail='negative', primary_side='BUY')
    return row
