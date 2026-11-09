"""Frozen monthly-expiry calendar proxy; fixed-unit research, never orders."""
from datetime import date, timedelta
from decimal import Decimal as D

from index_overnight_reversal_component import cost_outcomes
from nasdaq_cash_calendar import calendar_for
from nasdaq_h4_study import SCENARIOS
from sealed_m1_review import cash_sessions
from us500_fomc_momentum_component import funding

CANDIDATE = 'us500-monthly-options-week-calendar-price-component-v1'
ROLES = ('expiry_week', 'previous_week_control')
MINUTE = 60000
HOUR = 3600000
GRID = D('.001')


def schedule(year):
    if type(year) is not int or year not in (2019, 2022):
        raise ValueError('options_registered_year_holdout_closed')
    sessions = cash_sessions(calendar_for(year))
    rows = []
    for month in range(1, 13):
        first = date(year, month, 1)
        friday = first + timedelta(days=(4-first.weekday()) % 7+14)
        monday = friday-timedelta(days=4)
        for role, shift in zip(ROLES, (0, 7)):
            begin, finish = monday-timedelta(days=shift), friday-timedelta(days=shift)
            days = [d for d in sessions if begin.isoformat() <= d <= finish.isoformat()]
            if not days:
                raise ValueError('options_calendar_empty_week')
            opening, closing = sessions[days[0]][0], sessions[days[-1]][-1]+MINUTE
            rows.append(dict(candidate=CANDIDATE, year=year, month=month, role=role,
                scheduled_third_friday=friday.isoformat(), entry_day=days[0], exit_day=days[-1],
                cash_days=len(days), entry_decision_ms=opening, entry_target_ms=opening+MINUTE,
                exit_decision_ms=closing-2*MINUTE, exit_target_ms=closing-MINUTE,
                exit_session_close_ms=closing, execution_authorized=False,
                account_simulated=False, clean_oos=False, broker_calls=0, model_calls=0))
    return rows


def hours():
    return sorted({r[k]//HOUR*HOUR for year in (2019, 2022) for r in schedule(year)
                   for k in ('entry_target_ms', 'exit_target_ms')})


def checked_quote(quote, target, upper):
    if quote is None:
        return None
    fields = ('timestamp', 'wait_ms', 'source_ordinal', 'bid_units', 'ask_units')
    if (any(type(quote.get(k)) is not int for k in fields)
            or not target <= quote['timestamp'] < upper
            or quote['wait_ms'] != quote['timestamp']-target
            or quote['source_ordinal'] < 0
            or not 0 < quote['bid_units'] <= quote['ask_units'] <= 2**53-1):
        raise ValueError('options_quote_clock_grid_or_geometry')
    if quote['wait_ms'] > MINUTE:
        return None
    return dict(bid=str(D(quote['bid_units'])*GRID), ask=str(D(quote['ask_units'])*GRID),
                timestamp=quote['timestamp'])


def evaluate(spec, entry_quote, exit_quote, *, market_function, cost_function):
    expected = next((r for r in schedule(spec['year'])
                     if r['month'] == spec['month'] and r['role'] == spec['role']), None)
    if expected is None or spec != expected or any(type(spec[k]) is not type(v) for k,v in expected.items()):
        raise ValueError('options_frozen_spec_or_authority')
    entry = checked_quote(entry_quote, spec['entry_target_ms'], spec['exit_decision_ms'])
    exit_at = checked_quote(exit_quote, spec['exit_target_ms'], spec['exit_session_close_ms'])
    row = dict(**spec, entry=entry, exit=exit_at, outcomes={}, status='unresolved_endpoint')
    if entry is None or exit_at is None:
        return row
    costs = cost_outcomes(entry, exit_at, {'long': 'BUY'}, instrument_id='US500',
                          market_function=market_function, cost_function=cost_function)
    midgross = (D(exit_at['bid'])+D(exit_at['ask'])-D(entry['bid'])-D(entry['ask']))/2
    spread = (D(entry['ask'])-D(entry['bid'])+D(exit_at['ask'])-D(exit_at['bid']))/2
    for scenario, (_, rate) in SCENARIOS.items():
        c = costs[scenario]['long']['costs']
        events = funding(entry['timestamp'], exit_at['timestamp'], entry['ask'], rate)
        debit = sum((D(e['debit_usd']) for e in events), D(0))
        net = D(str(c['net_account']))-debit
        residual = D(str(c['net_account']))-(midgross-spread-D(str(c['commission_account']))-D(str(c['slippage_account'])))
        row['outcomes'][scenario] = dict(costs=c, funding_events=events, funding_usd=str(debit),
            midpoint_gross_usd=str(midgross), embedded_spread_usd=str(spread), rounding_residual_usd=str(residual),
            net_usd_per_research_unit=str(net))
    row['status'] = 'resolved_price_component_not_account'
    return row


def summarize(rows):
    expected = schedule(2019)+schedule(2022)
    if len(rows) != len(expected) or any(any(r.get(k) != v for k, v in s.items()) for r, s in zip(rows, expected)):
        raise ValueError('options_full_calendar_census')
    books = []
    for year in (2019, 2022):
        for role in ROLES:
            current = [r for r in rows if r['year'] == year and r['role'] == role]
            for scenario in SCENARIOS:
                resolved = [r['outcomes'][scenario] for r in current if r['outcomes']]
                values = [D(v['net_usd_per_research_unit']) for v in resolved]
                if any(not v.is_finite() for v in values):
                    raise ValueError('options_nonfinite_net')
                total = sum(values, D(0))
                books.append(dict(year=year, role=role, scenario=scenario, planned=12,
                    resolved=len(resolved), strict_net_usd_per_research_unit=str(total) if len(resolved)==12 else None,
                    known_subset_net_usd_per_research_unit=str(total), positive=sum(v>0 for v in values),
                    negative=sum(v<0 for v in values), midpoint_gross_usd=str(sum((D(v['midpoint_gross_usd']) for v in resolved),D(0))),
                    embedded_spread_usd=str(sum((D(v['embedded_spread_usd']) for v in resolved),D(0))),
                    funding_usd=str(sum((D(v['funding_usd']) for v in resolved),D(0)))))
    gates = []
    for year in (2019, 2022):
        values = {b['role']:b['strict_net_usd_per_research_unit'] for b in books if b['year']==year and b['scenario']=='stress'}
        a, b = (D(values[k]) if values[k] is not None else None for k in ROLES)
        gates.append(dict(year=year, stress_net=str(a) if a is not None else None,
            stress_minus_control=str(a-b) if a is not None and b is not None else None,
            retained=a is not None and b is not None and a>0 and a>b))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates,
        retained_for_temporal_review=all(g['retained'] for g in gates), account_simulated=False,
        clean_oos=False, execution_authorized=False, broker_calls=0, model_calls=0)
