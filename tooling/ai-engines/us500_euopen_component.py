"""Registered EU-open fixed long price component; M1 proxies, no account path."""
from datetime import date, datetime, time as wall_time, timedelta
from decimal import Decimal as D
import time
from zoneinfo import ZoneInfo

from fomc_price_component import observation
from index_overnight_reversal_component import cost_outcomes, MINUTE, SCENARIOS
from nasdaq_cash_calendar import sessions_for

CANDIDATE = 'us500-euopen-2330-0330-price-component-v1'
ROLES = ('primary', 'opposite_control', 'null_no_exposure')
NY = ZoneInfo('America/New_York')


def schedule(year, sessions):
    if type(year) is not int or year not in (2019, 2022):
        raise ValueError('registered_EUopen_year_holdout_closed')
    expected = sessions_for(f'development-{year}')
    if list(sessions.items()) != list(expected.items()):
        raise ValueError('full_registered_calendar_census_clock_required')
    result = []
    for label, stamps in sessions.items():
        day = date.fromisoformat(label)
        start = datetime.combine(day-timedelta(days=1), wall_time(23, 30), NY)
        end = datetime.combine(day, wall_time(3, 30), NY)
        decision, exit_decision = int(start.timestamp()*1000), int(end.timestamp()*1000)
        if exit_decision-decision != 240*MINUTE:
            raise ValueError('registered_EUopen_four_hour_clock')
        regular = len(stamps) == 390
        result.append(dict(candidate=CANDIDATE, session=label, year=year,
            regular_session=regular, planned_trade=regular, signal_side='BUY' if regular else None,
            decision_ms=decision, entry_ms=decision+MINUTE,
            exit_decision_ms=exit_decision, exit_ms=exit_decision+MINUTE,
            funding_rollover_model='NY17_declared_not_target_broker_verified'))
    return result


def prepare(year, sessions, pairs):
    rows = []
    for spec in schedule(year, sessions):
        row = dict(**spec, entry=None, exit=None, outcomes={}, path_expected_minutes=None,
            path_observed_minutes=None, status='calendar_halfday_skipped', funding_events=[],
            clean_oos=False, account_simulated=False, execution_authorized=False,
            intrabar_equity_assessed=False, broker_calls=0, model_calls=0)
        if spec['planned_trade']:
            entry_at, exit_at = spec['entry_ms'], spec['exit_ms']
            entry = observation(pairs.get(entry_at), entry_at, duration_ms=MINUTE, source_instrument='USA500.IDX/USD')
            exit_quote = observation(pairs.get(exit_at), exit_at, duration_ms=MINUTE, source_instrument='USA500.IDX/USD')
            start = datetime.fromtimestamp(entry_at/1000, NY)
            for day in (start.date(), start.date()+timedelta(days=1)):
                rollover = int(datetime.combine(day, wall_time(17), NY).timestamp()*1000)
                if entry_at < rollover <= exit_at:
                    raise ValueError('registered_zero_funding_window_crossed_rollover')
            row.update(entry=entry, exit=exit_quote, path_expected_minutes=240,
                path_observed_minutes=sum(at in pairs for at in range(entry_at, exit_at, MINUTE)),
                status='unresolved_endpoint')
        rows.append(row)
    planned = [r for r in rows if r['planned_trade']]
    resolved = sum(r['entry']['bid'] is not None and r['exit']['bid'] is not None for r in planned)
    return dict(rows=rows, source_scope=dict(cash_sessions=len(rows), planned=len(planned),
        expected_endpoints=len(planned)*2, usable_endpoints=sum(r[role]['bid'] is not None for r in planned for role in ('entry', 'exit')),
        resolved_pairs=resolved, unresolved_pairs=len(planned)-resolved,
        coverage98_passed=resolved*100 >= len(planned)*98))


def evaluate(year, sessions, pairs, *, market_function, cost_function, progress=None, deadline=None):
    began = time.perf_counter(); prepared = prepare(year, sessions, pairs)
    prep_seconds = time.perf_counter()-began
    if progress: progress('source_prepared_before_costs', prepared['source_scope'])
    began = time.perf_counter()
    for index, row in enumerate(prepared['rows']):
        if index % 32 == 0 and deadline is not None and time.perf_counter() >= deadline:
            raise TimeoutError('EUopen_component_deadline')
        if not row['planned_trade'] or row['entry']['bid'] is None or row['exit']['bid'] is None:
            continue
        row['outcomes'] = cost_outcomes(row['entry'], row['exit'], dict(zip(ROLES, ('BUY', 'SELL', None))),
            instrument_id='US500', market_function=market_function, cost_function=cost_function)
        row['status'] = 'resolved_price_component_not_account'
    return dict(**prepared, prepare_seconds=prep_seconds, compute_seconds=time.perf_counter()-began)


def summarize(rows):
    expected = [s for year in (2019, 2022) for s in schedule(year, sessions_for(f'development-{year}'))]
    if len(rows) != len(expected):
        raise ValueError('EUopen_missing_calendar_rows')
    for row, spec in zip(rows, expected):
        if any(row.get(k) != v for k, v in spec.items()):
            raise ValueError('EUopen_changed_schedule_or_identity')
        if (any(row[k] is not False for k in ('clean_oos', 'account_simulated', 'execution_authorized', 'intrabar_equity_assessed'))
                or any(type(row[k]) is not int or row[k] != 0 for k in ('broker_calls', 'model_calls'))
                or row['funding_events']):
            raise ValueError('EUopen_authority_funding_or_scope')
        if row['outcomes'] and (not row['planned_trade'] or set(row['outcomes']) != set(SCENARIOS)
                or any(set(v) != set(ROLES) for v in row['outcomes'].values())):
            raise ValueError('EUopen_unregistered_cost_roles')
    summary, gates = [], []
    for year in (2019, 2022):
        group = [r for r in rows if r['year'] == year]
        planned = [r for r in group if r['planned_trade']]
        resolved = [r for r in planned if r['outcomes']]
        for scenario in SCENARIOS:
            nets = {}
            for role in ROLES:
                values = [D(r['outcomes'][scenario][role]['net_usd_per_research_unit']) for r in resolved]
                if any(not value.is_finite() for value in values):
                    raise ValueError('EUopen_nonfinite_net')
                nets[role] = sum(values, D(0)); positive = [v for v in values if v > 0]
                quarters = []
                for q in range(1, 5):
                    cohort = [r for r in planned if (int(r['session'][5:7])-1)//3+1 == q]
                    known = [r for r in cohort if r['outcomes']]
                    quarters.append(dict(quarter=q, planned=len(cohort), resolved=len(known),
                        known_net_usd_per_research_unit=str(sum((D(r['outcomes'][scenario][role]['net_usd_per_research_unit']) for r in known), D(0)))))
                summary.append(dict(year=year, scenario=scenario, role=role, cash_sessions=len(group),
                    planned=len(planned), resolved=len(resolved), unresolved=len(planned)-len(resolved),
                    known_net_usd_per_research_unit=str(nets[role]), positive=sum(v > 0 for v in values), negative=sum(v < 0 for v in values),
                    worst=str(min(values)) if values else None, best=str(max(values)) if values else None,
                    top_positive_share=str(max(positive)/sum(positive)) if positive else None,
                    quarters=quarters, resolved_exposure_cases=0 if role == 'null_no_exposure' else len(resolved),
                    missing_path_windows=sum(r['path_observed_minutes'] != r['path_expected_minutes'] for r in resolved)))
            if scenario == 'stress':
                gates.append(dict(year=year, retained=(len(planned) >= 150 and len(resolved)*100 >= len(planned)*98
                    and nets['primary'] > 0 and nets['primary'] > nets['opposite_control'] and nets['primary'] > nets['null_no_exposure'])))
    return dict(candidate=CANDIDATE, summary=summary, year_gates=gates,
        retained_for_further_research=all(g['retained'] for g in gates), scope='price_component_not_account_policy',
        clean_oos=False, account_simulated=False, execution_authorized=False, broker_calls=0, model_calls=0)
