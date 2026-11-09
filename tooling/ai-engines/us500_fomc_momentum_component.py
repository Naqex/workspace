"""Frozen R086 price-only event component; no portfolio or broker authority."""
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from zoneinfo import ZoneInfo

from fomc_price_component import DATES, PUBLICATIONS, observation
from index_overnight_reversal_component import cost_outcomes
from nasdaq_cash_calendar import sessions_for
from nasdaq_h4_study import DAY, HOUR, SCENARIOS

CANDIDATE = 'us500-fomc-past25-price-momentum-component-v1'
RULES = ('primary', 'opposite_control', 'always_long_control', 'null')
NY = ZoneInfo('America/New_York')
MINUTE = 60000


def stamp(day, hour, minute=0):
    return int(datetime.combine(date.fromisoformat(day), time(hour, minute), NY).timestamp()*1000)


def sessions(year):
    if type(year) is not int or year not in (2019, 2022):
        raise ValueError('R086_registered_year_holdout_closed')
    result = {**sessions_for(f'warmup-{year}'), **sessions_for(f'development-{year}')}
    # This is a bounded tail, not a newly admitted full-year exchange calendar.
    holiday = '2020-01-01' if year == 2019 else '2023-01-02'
    for n in range(1, 16):
        day = date(year+1, 1, n)
        if day.weekday() < 5 and day.isoformat() != holiday:
            result[day.isoformat()] = list(range(stamp(day.isoformat(), 9, 30), stamp(day.isoformat(), 16), MINUTE))
    return result


def schedule(year):
    cash = sessions(year); days = list(cash); rows = []
    publication = int(datetime.fromisoformat(PUBLICATIONS[year]).timestamp()*1000)
    for event in DATES[year]:
        for role, shift in (('primary', 0), ('matched_week_control', 7)):
            anchor = (date.fromisoformat(event)-timedelta(days=shift)).isoformat()
            if anchor not in cash:
                raise ValueError('R086_anchor_not_cash_session')
            i = days.index(anchor)
            if i < 27 or i+15 >= len(days):
                raise ValueError('R086_calendar_coverage')
            early, late, entry, exit_day = days[i-27], days[i-2], days[i-1], days[i+15]
            decision, exit_decision = stamp(entry, 14), stamp(exit_day, 12)
            row = dict(candidate=CANDIDATE, year=year, event=event, role=role, anchor=anchor,
                calendar_publication_ms=publication, feature_start_ms=stamp(early, 12),
                feature_end_ms=stamp(late, 12), decision_ms=decision, entry_ms=decision+MINUTE,
                exit_decision_ms=exit_decision, exit_ms=exit_decision+MINUTE)
            row['calendar_endpoints_valid'] = all(at in cash[d] for at, d in (
                (row['feature_start_ms'], early), (row['feature_end_ms'], late),
                (row['entry_ms'], entry), (row['exit_ms'], exit_day)))
            if not publication < row['feature_end_ms']+MINUTE < decision < row['entry_ms'] < exit_decision < row['exit_ms']:
                raise ValueError('R086_causal_clock')
            rows.append(row)
    return rows


def prepare(year, pairs):
    rows = []
    for spec in schedule(year):
        quotes = {k: observation(pairs.get(spec[k]), spec[k], duration_ms=MINUTE,
            source_instrument='USA500.IDX/USD') for k in ('feature_start_ms', 'feature_end_ms', 'entry_ms', 'exit_ms')}
        start, finish = (quotes[k] for k in ('feature_start_ms', 'feature_end_ms'))
        known = start['bid'] is not None and finish['bid'] is not None
        change = (D(finish['bid'])+D(finish['ask'])-D(start['bid'])-D(start['ask']))/2 if known else None
        side = ('BUY' if change > 0 else 'SELL' if change < 0 else None) if known else None
        rows.append(dict(**spec, quotes=quotes, signal_known=known, signal_side=side,
            feature_midpoint_change=str(change) if known else None, outcomes={},
            account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0))
    return rows


def funding(entry_ms, exit_ms, entry_ask, rate):
    at = entry_ms//DAY*DAY+22*HOUR
    if at <= entry_ms:
        at += DAY
    debit = (D(entry_ask)*rate/365).quantize(D('.01'), rounding=ROUND_HALF_UP)
    events = []
    while at <= exit_ms:
        events.append(dict(time_msc=at, debit_usd=str(debit))); at += DAY
    return events


def evaluate(year, pairs, *, market_function, cost_function, progress=None):
    rows = prepare(year, pairs)
    if progress:
        progress('source_feature_endpoint_census_before_costs', rows)
    for row in rows:
        entry, exit_at = (row['quotes'][k] for k in ('entry_ms', 'exit_ms'))
        endpoints = row['calendar_endpoints_valid'] and entry['bid'] is not None and exit_at['bid'] is not None
        sides = dict(zip(RULES, (row['signal_side'],
            'SELL' if row['signal_side'] == 'BUY' else 'BUY' if row['signal_side'] == 'SELL' else None, 'BUY', None)))
        # Null needs neither feature nor quotes; unknown feature must never mean flat.
        for scenario, (_, rate) in SCENARIOS.items():
            row['outcomes'][scenario] = {}
            for rule, side in sides.items():
                known = rule not in ('primary', 'opposite_control') or row['signal_known']
                resolved = known and (side is None or endpoints)
                result = dict(side=side, resolved=resolved, net_usd_per_research_unit=None,
                    funding_events=[], funding_usd=None, costs=None)
                if resolved:
                    if side is None:
                        result.update(net_usd_per_research_unit='0', funding_usd='0')
                    else:
                        costs = cost_outcomes(entry, exit_at, {rule: side}, instrument_id='US500',
                            market_function=market_function, cost_function=cost_function)[scenario][rule]['costs']
                        events = funding(row['entry_ms'], row['exit_ms'], entry['ask'], rate)
                        total = sum((D(e['debit_usd']) for e in events), D(0))
                        result.update(costs=costs, funding_events=events, funding_usd=str(total),
                            net_usd_per_research_unit=str(D(str(costs['net_account']))-total))
                row['outcomes'][scenario][rule] = result
    return rows


def summarize(rows):
    expected = schedule(2019)+schedule(2022)
    if len(rows) != 32 or any(any(row.get(k) != v for k, v in spec.items()) for row, spec in zip(rows, expected)):
        raise ValueError('R086_registered_row_census')
    books = []
    for year in (2019, 2022):
        for anchor in ('primary', 'matched_week_control'):
            current = [r for r in rows if r['year'] == year and r['role'] == anchor]
            for rule in RULES:
                for scenario in SCENARIOS:
                    values = [r['outcomes'][scenario][rule] for r in current]
                    resolved = [v for v in values if v['resolved']]
                    net = sum((D(v['net_usd_per_research_unit']) for v in resolved), D(0))
                    books.append(dict(year=year, anchor=anchor, rule=rule, scenario=scenario,
                        planned=8, resolved=len(resolved), trades=sum(v['side'] is not None for v in resolved),
                        strict_net_usd_per_research_unit=str(net) if len(resolved) == 8 else None,
                        known_subset_net_usd_per_research_unit=str(net)))
    gates = []
    for year in (2019, 2022):
        selected = [b for b in books if b['year'] == year and b['rule'] == 'primary' and b['scenario'] == 'stress']
        a, b = (None if v['strict_net_usd_per_research_unit'] is None else D(v['strict_net_usd_per_research_unit']) for v in selected)
        gates.append(dict(year=year, primary_stress_net=str(a) if a is not None else None,
            primary_minus_matched_stress=str(a-b) if a is not None and b is not None else None,
            retained=a is not None and b is not None and a > 0 and a-b > 0))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates,
        retained_for_further_research=all(g['retained'] for g in gates),
        scope='price_component_not_account_policy', account_simulated=False, clean_oos=False,
        execution_authorized=False, broker_calls=0)
