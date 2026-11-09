"""R087 own CFD hypothesis at Japan cash open; fixed JPY research geometry."""
from bisect import bisect_left
from datetime import date, datetime, timedelta, time
from decimal import Decimal as D
from zoneinfo import ZoneInfo

from fomc_price_component import observation

CANDIDATE = 'jpn-cash-open-US-close-contrarian-component-v1'
RULES = ('primary', 'opposite_control', 'always_long_control', 'always_short_control', 'null')
SCENARIOS = {'reference': D(1), 'stress': D(3)}
MINUTE = 60000
NY = ZoneInfo('America/New_York')
TOKYO = ZoneInfo('Asia/Tokyo')


def instant(day, hour, minute, zone):
    return int(datetime.combine(date.fromisoformat(day), time(hour, minute), zone).timestamp()*1000)


def schedules(year, holidays, us_closes):
    if type(year) is not int or year not in (2019, 2022):
        raise ValueError('R087_registered_year_holdout_closed')
    if not us_closes or list(us_closes) != sorted(set(us_closes)):
        raise ValueError('ordered_US_close_clock_required')
    if any(type(t) is not int or t % MINUTE for t in us_closes):
        raise ValueError('US_close_minute_clock')
    holidays = {date.fromisoformat(d) for d in holidays}
    rows = []; day = date(year, 1, 1)
    while day.year == year:
        if day.weekday() < 5 and day not in holidays and (day.month, day.day) not in ((1, 1), (1, 2), (1, 3), (12, 31)):
            label = day.isoformat(); decision = instant(label, 9, 0, TOKYO)
            i = bisect_left(us_closes, decision)-1
            if i < 1:
                raise ValueError('US_calendar_warmup_missing')
            earlier, latest = us_closes[i-1:i+1]
            if not earlier < latest < decision:
                raise ValueError('US_close_not_before_Japan_decision')
            rows.append(dict(candidate=CANDIDATE, year=year, session=label, decision_ms=decision,
                entry_ms=decision+MINUTE, exit_decision_ms=decision+28*MINUTE, exit_ms=decision+29*MINUTE,
                prior_US_close_ms=earlier, latest_US_close_ms=latest,
                calendar_eligible=decision-latest <= 72*3600000,
                calendar_skip_reason=None if decision-latest <= 72*3600000 else 'latest_US_close_older_than_72h'))
        day += timedelta(days=1)
    return rows


def prepare(specs, us_pairs, jpn_pairs):
    rows = []
    for spec in specs:
        features = {}
        for key in ('prior_US_close_ms', 'latest_US_close_ms'):
            at = spec[key]-MINUTE; pair = us_pairs.get(at)
            close_pair = tuple(dict(r, open=r['close']) for r in pair) if pair is not None else None
            q = observation(close_pair, at, duration_ms=MINUTE, source_instrument='USA500.IDX/USD')
            q.update(field='close', basis='source_separate_side_M1_Close_proxy')
            features[key] = q
        known = all(q['bid'] is not None for q in features.values())
        a, b = (features[k] for k in ('prior_US_close_ms', 'latest_US_close_ms'))
        change = (D(b['bid'])+D(b['ask'])-D(a['bid'])-D(a['ask']))/2 if known else None
        side = ('SELL' if change > 0 else 'BUY' if change < 0 else None) if known else None
        quotes = {k: observation(jpn_pairs.get(spec[k]), spec[k], duration_ms=MINUTE,
            source_instrument='JPN.IDX/JPY') for k in ('entry_ms', 'exit_ms')}
        path = range(spec['entry_ms'], spec['exit_ms']+MINUTE, MINUTE)
        missing = []; crossed = []
        for at in path:
            q = observation(jpn_pairs.get(at), at, duration_ms=MINUTE, source_instrument='JPN.IDX/JPY')
            if q['status'] == 'crossed_endpoint': crossed.append(at)
            elif q['bid'] is None: missing.append(at)
        rows.append(dict(**spec, features=features, quotes=quotes, signal_known=known,
            signal_side=side, feature_mid_close_change=str(change) if known else None,
            source_role_minutes=len(path), missing_role_minutes=missing, crossed_role_minutes=crossed,
            strict_roles_admitted=not missing and not crossed, outcomes={}, unit='JPY_per_research_unit',
            account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0))
    return rows


def evaluate(prepared):
    rows = []
    for prepared_row in prepared:
        row = dict(prepared_row, outcomes={})
        side = row['signal_side']
        directions = (side, 'SELL' if side == 'BUY' else 'BUY' if side == 'SELL' else None, 'BUY', 'SELL', None)
        for scenario, slip in SCENARIOS.items():
            row['outcomes'][scenario] = {}
            for rule, direction in zip(RULES, directions):
                known = row['signal_known'] if rule in ('primary', 'opposite_control') else True
                skip = not row['calendar_eligible']
                resolved = rule == 'null' or skip or (known and (direction is None or row['strict_roles_admitted']))
                outcome = dict(side=None if skip else direction, calendar_skipped=skip, resolved=resolved,
                    mid_price_pnl=None, embedded_spread=None, slippage=None, commission=None,
                    funding=None, net_jpy_per_research_unit=None)
                if resolved:
                    mid = spread = extra = D(0)
                    if not skip and direction is not None:
                        entry, exit_at = (row['quotes'][k] for k in ('entry_ms', 'exit_ms'))
                        be, ae, bx, ax = (D(q[k]) for q in (entry, exit_at) for k in ('bid', 'ask'))
                        mid = (1 if direction == 'BUY' else -1)*(bx+ax-be-ae)/2
                        spread = (ae-be+ax-bx)/2; extra = 2*slip
                    outcome.update(mid_price_pnl=str(mid), embedded_spread=str(spread), slippage=str(extra),
                        commission='0', funding='0', net_jpy_per_research_unit=str(mid-spread-extra))
                row['outcomes'][scenario][rule] = outcome
        rows.append(row)
    return rows


def summarize(rows):
    if not rows or len({r['session'] for r in rows}) != len(rows):
        raise ValueError('registered_session_rows_required')
    books = []; gates = []
    for year in (2019, 2022):
        group = [r for r in rows if r['year'] == year]
        eligible = [r for r in group if r['calendar_eligible']]
        if not eligible: raise ValueError('no_eligible_registered_year')
        for scenario in SCENARIOS:
            for rule in RULES:
                values = [r['outcomes'][scenario][rule] for r in eligible]
                known = [v for v in values if v['resolved']]
                totals = {k: str(sum((D(v[k]) for v in known), D(0))) for k in (
                    'mid_price_pnl', 'embedded_spread', 'slippage', 'commission', 'funding', 'net_jpy_per_research_unit')}
                books.append(dict(year=year, rule=rule, scenario=scenario, planned_calendar_sessions=len(group),
                    calendar_eligible=len(eligible), calendar_skipped=len(group)-len(eligible), resolved=len(known),
                    unknown=len(values)-len(known), trades=sum(v['side'] is not None for v in known),
                    known_subset_totals=totals, full_eligible_net=totals['net_jpy_per_research_unit'] if len(known) == len(values) else None))
        common = [r for r in eligible if all(r['outcomes']['stress'][rule]['resolved'] for rule in ('primary', 'always_long_control'))]
        primary = sum((D(r['outcomes']['stress']['primary']['net_jpy_per_research_unit']) for r in common), D(0))
        control = sum((D(r['outcomes']['stress']['always_long_control']['net_jpy_per_research_unit']) for r in common), D(0))
        resolved = sum(r['outcomes']['stress']['primary']['resolved'] for r in eligible)
        gates.append(dict(year=year, eligible=len(eligible), resolved=resolved,
            common_resolved=len(common), paired_stress_net=str(primary), paired_stress_minus_BUY=str(primary-control),
            retained=resolved*100 >= 95*len(eligible) and primary > 0 and primary-control > 0))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates, retained_for_gap_and_risk_review=all(g['retained'] for g in gates),
        unit='JPY_per_research_unit', account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0)
