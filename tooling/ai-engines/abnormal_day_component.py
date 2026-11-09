"""R089 fixed-notional price component; account/risk qualification is separate."""
from collections import Counter
from datetime import date, datetime, time, timedelta
from decimal import Decimal as D
from zoneinfo import ZoneInfo

import abnormal_day_feature as signal
from fixing_clock_probe import price_return

CANDIDATE = 'eurusd-prior-abnormal-20h-day-reversal-utc-v2'
RULES = ('primary', 'opposite_control', 'null')
SCENARIOS = ('reference', 'stress')


def days(*, years=(2019, 2022)):
    result = []
    for year in signal.registered_years(years):
        cursor = date(year, 1, 1)
        while cursor.year == year:
            if cursor.weekday() < 5:
                result.append(cursor)
            cursor += timedelta(days=1)
    return result


def endpoint(q, target):
    if q is None:
        return None
    if type(q['time_msc']) is not int:
        raise ValueError('R089_invalid_endpoint_clock')
    bid, ask = (D(str(q[key])) for key in ('bid', 'ask'))
    if any(not p.is_finite() or p <= 0 or p % signal.GRID for p in (bid, ask)) or bid > ask:
        raise ValueError('R089_invalid_endpoint_price')
    return q if 0 <= q['time_msc']-target <= 60000 else None


def evaluate_one(day, observations, quotes, *, years=(2019, 2022)):
    feature = signal.feature(day, observations, years=years)
    row = dict(**feature, candidate=CANDIDATE, year=day.year, outcomes={},
        account_simulated=False, clean_oos=False, broker_calls=0)
    ny = ZoneInfo('America/New_York')
    start = datetime.fromtimestamp(row['entry_ms']/1000, ny)
    end = datetime.fromtimestamp(row['exit_ms']/1000, ny)
    for roll_day in (start.date(), end.date()):
        rollover = datetime.combine(roll_day, time(17), ny)
        if start < rollover <= end:
            raise ValueError('R089_unregistered_rollover')
    selected = row['status'] == 'shock'
    entry = endpoint(quotes.get(row['entry_ms']), row['entry_ms']) if selected else None
    exit_at = endpoint(quotes.get(row['exit_ms']), row['exit_ms']) if selected else None
    if entry is not None and exit_at is not None and not (row['decision_ms'] < entry['time_msc'] < exit_at['time_msc']):
        raise ValueError('R089_endpoint_order')
    row.update(selected=selected, entry_quote=entry, exit_quote=exit_at)
    for scenario in SCENARIOS:
        row['outcomes'][scenario] = {}
        for rule in RULES:
            side = row['primary_side'] if selected and rule != 'null' else None
            if side is not None and rule == 'opposite_control':
                side = 'SELL' if side == 'BUY' else 'BUY'
            if side is None:
                value = dict(side=None, exposed=False, resolved=True, net_usd_per_research_unit='0', costs=None)
            elif entry is None or exit_at is None:
                value = dict(side=side, exposed=True, resolved=False, net_usd_per_research_unit=None, costs=None)
            else:
                costs = price_return(side, entry, exit_at, scenario)
                value = dict(side=side, exposed=True, resolved=True,
                    net_usd_per_research_unit=costs['net_usd_per_standard_lot'], costs=costs['costs'])
            row['outcomes'][scenario][rule] = value
    return row


def evaluate(observations, quotes, *, years=(2019, 2022)):
    years = signal.registered_years(years)
    return [evaluate_one(day, observations, quotes, years=years) for day in days(years=years)]


def summarize(rows, *, years=(2019, 2022)):
    years = signal.registered_years(years)
    expected = days(years=years)
    if len(rows) != len(expected) or any(r['day'] != d.isoformat() for r, d in zip(rows, expected)):
        raise ValueError('R089_weekday_census')
    books, gates = [], []
    for year in years:
        cohort = [r for r in rows if r['year'] == year]
        statuses = dict(Counter(r['status'] for r in cohort))
        selected = sum(r['selected'] for r in cohort)
        for rule in RULES:
            for scenario in SCENARIOS:
                values = [r['outcomes'][scenario][rule] for r in cohort]
                exposed = [v for v in values if v['exposed']]
                resolved = [v for v in exposed if v['resolved']]
                net = sum((D(v['net_usd_per_research_unit']) for v in resolved), D(0))
                books.append(dict(year=year, rule=rule, scenario=scenario, planned_weekdays=len(cohort),
                    feature_status_counts=statuses, selected_shocks=selected, exposed=len(exposed),
                    resolved_exposed=len(resolved), unresolved_exposed=len(exposed)-len(resolved),
                    known_subset_net=str(net), strict_net=str(net) if len(resolved) == len(exposed) else None))
        primary = next(b for b in books if b['year'] == year and b['rule'] == 'primary' and b['scenario'] == 'stress')
        incomplete = selected < 8 or primary['unresolved_exposed'] > 0
        retained = not incomplete and D(primary['strict_net']) > 0
        gates.append(dict(year=year, status='inconclusive' if incomplete else 'positive' if retained else 'nonpositive',
            retained=retained))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates,
        retained_for_risk_review=all(g['retained'] for g in gates),
        unit='USD_per_100000EUR_research_notional', financial_cases=len(rows)*6,
        account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0)


def temporal_gate(books):
    years = tuple(range(2010, 2025))
    expected = {(year, rule, scenario) for year in years for rule in RULES for scenario in SCENARIOS}
    indexed = {(b['year'], b['rule'], b['scenario']): b for b in books}
    if len(books) != 90 or set(indexed) != expected:
        raise ValueError('R089_temporal_book_census')
    extension = [indexed[(year, 'primary', 'stress')] for year in years if year not in (2019, 2022)]
    coverage = []
    for book in extension:
        counts = book['feature_status_counts']
        eligible = book['planned_weekdays'] - counts.get('calendar_skip', 0)
        available = counts.get('normal', 0) + counts.get('shock', 0)
        if eligible <= 0 or not 0 <= available <= eligible:
            raise ValueError('R089_temporal_feature_counts')
        coverage.append(dict(year=book['year'], available=available, eligible=eligible,
            meets_80_percent=available * 100 >= eligible * 80))
    complete = all(b['strict_net'] is not None and b['unresolved_exposed'] == 0 for b in extension)
    resolved = sum(b['resolved_exposed'] for b in extension)
    block_years = ((2010, 2011, 2012), (2013, 2014, 2015), (2016, 2017, 2018), (2020, 2021), (2023, 2024))
    blocks = []
    for group in block_years:
        selected = [b for b in extension if b['year'] in group]
        values = [D(b['strict_net']) for b in selected if b['strict_net'] is not None]
        blocks.append(dict(years=list(group), strict_net=str(sum(values, D(0))) if len(values) == len(group) else None))
    total = str(sum((D(b['strict_net']) for b in extension), D(0))) if complete else None
    positive = sum(b['strict_net'] is not None and D(b['strict_net']) > 0 for b in extension)
    adequate = complete and all(c['meets_80_percent'] for c in coverage) and resolved >= 100
    retained = adequate and D(total) > 0 and positive >= 9 and all(b['strict_net'] is not None and D(b['strict_net']) > 0 for b in blocks)
    return dict(scope='13_extension_years_excluding_2019_2022', coverage=coverage, resolved_selected=resolved,
        complete_selected_endpoints=complete, extension_strict_net=total, positive_extension_years=positive,
        extension_blocks=blocks, status='inconclusive' if not adequate else 'retained' if retained else 'not_retained',
        retained_for_risk_review=bool(retained), account_simulated=False, execution_authorized=False)
