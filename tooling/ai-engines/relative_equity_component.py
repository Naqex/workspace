"""Registered bilateral price-proxy signal; no broker, position or prop engine."""
from datetime import date, datetime
from decimal import Decimal as D
from zoneinfo import ZoneInfo

INSTRUMENTS = ('ezuususd', 'spyususd', 'eurusd')
VIEWS = ('primary', 'opposite_control', 'always_buy', 'always_sell')


def positive(value):
    if isinstance(value, bool) or not isinstance(value, (str, int, float, D)):
        raise ValueError('numeric_price_required')
    result = D(str(value))
    if not result.is_finite() or result <= 0:
        raise ValueError('finite_positive_price_required')
    return result


def month_schedule(calendar_sessions, year, month):
    if type(year) is not int or type(month) is not int or not 1 <= month <= 12 or not 2018 <= year <= 2024:
        raise ValueError('registered_historical_month_required')
    days = sorted(day for day in calendar_sessions if day.startswith(f'{year}-{month:02}-'))
    if len(days) < 3:
        raise ValueError('cash_calendar_month_required')
    first, penultimate, last = days[0], days[-2], days[-1]
    local = datetime.fromisoformat(last).replace(tzinfo=ZoneInfo('Europe/London'))
    stamp = lambda hour, minute: int(local.replace(hour=hour, minute=minute).timestamp()*1000)
    return dict(year=year, month=month, first=first, penultimate=penultimate, last=last,
                equity_stamps={day: calendar_sessions[day][-1] for day in (first, penultimate)},
                decision_ms=stamp(15, 0), entry_ms=stamp(15, 1), exit_ms=stamp(16, 3),
                calendar_basis='last_NYSE_session_proxy_not_verified_WMR_calendar')


def relative_signal(first, penultimate, schedule):
    for points, day in ((first, schedule['first']), (penultimate, schedule['penultimate'])):
        expected = schedule['equity_stamps'][day]
        for instrument in INSTRUMENTS:
            point = points[instrument]
            if (type(point['stamp']) is not int or point['stamp'] != expected
                    or point['known_at'] != expected+60000
                    or not point['known_at'] < schedule['decision_ms']):
                raise ValueError('noncausal_or_asynchronous_equity_signal')
            positive(point['bid']); positive(point['ask'])
            if positive(point['ask']) < positive(point['bid']):
                raise ValueError('negative_signal_spread')
    e0, e1 = (positive(p['ezuususd']['bid'])/positive(p['eurusd']['bid']) for p in (first, penultimate))
    us0, us1 = (positive(p['spyususd']['bid']) for p in (first, penultimate))
    eur_factor, us_factor = e1/e0, us1/us0
    # Compare products before division: decimal rounding must not invent a sign at equality.
    left = positive(penultimate['ezuususd']['bid'])*positive(first['eurusd']['bid'])*us0
    right = positive(first['ezuususd']['bid'])*positive(penultimate['eurusd']['bid'])*us1
    side = 'SELL' if left > right else 'BUY' if left < right else None
    return dict(side=side, euro_local_price_factor=str(eur_factor), US_price_factor=str(us_factor),
                adjustment_basis='unknown_ETF_price_proxy_not_total_return',
                first=first, penultimate=penultimate)


def costed_views(signal, entry, exit_at, schedule, price_return):
    for point, expected in ((entry, schedule['entry_ms']), (exit_at, schedule['exit_ms'])):
        if type(point['stamp']) is not int or point['stamp'] != expected:
            raise ValueError('FX_endpoint_not_exact')
        if positive(point['ask']) < positive(point['bid']):
            raise ValueError('negative_FX_endpoint_spread')
    if not schedule['decision_ms'] < entry['stamp'] < exit_at['stamp']:
        raise ValueError('FX_causal_order')
    primary = signal['side']
    directions = dict(primary=primary, opposite_control=('SELL' if primary=='BUY' else 'BUY') if primary else None,
                      always_buy='BUY', always_sell='SELL')
    return {view: dict(side=side, outcomes={scenario:price_return(side, entry, exit_at, scenario) for scenario in
                ('reference','stress')} if side else {}) for view,side in directions.items()}


def registered_priority(summary, *, years, minimum_resolved, minimum_positive_years):
    """Apply explicit study thresholds; never infer them from observed returns."""
    if (not years or len(set(years)) != len(years)
            or any(type(y) is not int or not 2018 <= y <= 2024 for y in years)
            or type(minimum_resolved) is not int or not 1 <= minimum_resolved <= 12
            or type(minimum_positive_years) is not int or not 1 <= minimum_positive_years <= len(years)):
        raise ValueError('registered_priority_configuration')
    rows = [r for r in summary if r['view']=='primary' and r['scenario']=='stress']
    if len(rows) != len(years) or {r['year'] for r in rows} != set(years):
        raise ValueError('primary_stress_year_census')
    values = []
    for row in rows:
        if (type(row['resolved']) is not int or not 0 <= row['resolved'] <= 12
                or isinstance(row['net_pips_sum'], bool)):
            raise ValueError('priority_summary_numeric')
        value = D(str(row['net_pips_sum']))
        if not value.is_finite():
            raise ValueError('priority_summary_numeric')
        values.append(value)
    return (all(r['resolved'] >= minimum_resolved for r in rows)
            and sum(v > 0 for v in values) >= minimum_positive_years
            and sum(values, D(0)) > 0)
