"""Frozen rROD price components with first-half control; no gamma/account claims."""
from decimal import Decimal as D
import time

from fomc_price_component import observation
from index_overnight_reversal_component import (
    DAY, MINUTE, SCENARIOS, cost_outcomes, predictor_bid, profile_identity,
    summarize_rows, validate_calendar_window,
)

CANDIDATES = {
    'us500': 'us500-restofday-last30-price-component-v1',
    'nasdaq': 'nasdaq-restofday-last30-price-component-v1',
}
ROLES = ('primary', 'opposite_rod_control', 'always_long_control', 'always_short_control', 'first_half_control')


def identity(profile):
    _, market, source = profile_identity(profile)
    return CANDIDATES[profile], market, source


def prepare(sessions, pairs, *, start, end, profile):
    candidate, _, _ = identity(profile)
    year = validate_calendar_window(sessions, start=start, end=end)
    previous = previous_at = None
    specs = []
    for day, stamps in sessions.items():
        regular = len(stamps) == 390
        first = predictor_bid(pairs.get(stamps[29]), stamps[29], 'close') if regular else None
        late = predictor_bid(pairs.get(stamps[-31]), stamps[-31], 'close') if regular else None
        valid = regular and previous is not None and first is not None and late is not None
        rod = late-previous if valid else None
        first_change = first-previous if valid else None
        side = 'BUY' if valid and rod > 0 else 'SELL' if valid and rod < 0 else None
        first_side = 'BUY' if valid and first_change > 0 else 'SELL' if valid and first_change < 0 else None
        if start <= stamps[0] < end:
            specs.append(dict(candidate=candidate, session=day, year=year, regular_session=regular,
                predictor_valid=valid, signal_side=side, first_half_side=first_side,
                planned_trade=side is not None, rod_bid_price_units=str(rod) if valid else None,
                first_half_bid_price_units=str(first_change) if valid else None,
                previous_close_ms=previous_at, previous_close_bid=str(previous) if previous is not None else None,
                first_half_close_bid=str(first) if first is not None else None,
                late_close_bid=str(late) if late is not None else None,
                signal_known_at_ms=stamps[-30] if regular else None, decision_ms=stamps[-30] if regular else None,
                entry_ms=stamps[-29] if regular else None, exit_decision_ms=stamps[-2] if regular else None,
                exit_ms=stamps[-1] if regular else None,
                status='planned_price_component' if side else 'calendar_halfday_skipped' if not regular
                else 'valid_flat_rod' if valid else 'signal_unavailable'))
        previous_at = stamps[-1]
        previous = predictor_bid(pairs.get(previous_at), previous_at, 'close')
    return specs


def evaluate(sessions, pairs, *, start, end, profile, market_function, cost_function, progress=None, deadline=None):
    _, instrument, source = identity(profile)
    began, cpu = time.perf_counter(), time.process_time()
    specs = prepare(sessions, pairs, start=start, end=end, profile=profile)
    rows = []
    for i, spec in enumerate(specs):
        if i % 32 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('restofday_component_deadline')
            if progress:
                progress(i, len(specs))
        row = dict(**spec, entry=None, exit=None, outcomes={}, path_expected_minutes=None,
            path_observed_minutes=None, clean_oos=False, account_simulated=False,
            execution_authorized=False, broker_calls=0, model_calls=0)
        if spec['planned_trade']:
            if not spec['previous_close_ms']+MINUTE < spec['signal_known_at_ms'] == spec['decision_ms'] < spec['entry_ms'] < spec['exit_decision_ms'] < spec['exit_ms']:
                raise ValueError('restofday_causal_clock')
            entry = observation(pairs.get(spec['entry_ms']), spec['entry_ms'], duration_ms=MINUTE, source_instrument=source)
            exit_at = observation(pairs.get(spec['exit_ms']), spec['exit_ms'], duration_ms=MINUTE, source_instrument=source)
            path = range(spec['entry_ms'], spec['exit_ms'], MINUTE)
            row.update(entry=entry, exit=exit_at, path_expected_minutes=len(path),
                path_observed_minutes=sum(t in pairs for t in path), status='unresolved_endpoint')
            if entry['bid'] is not None and exit_at['bid'] is not None:
                row['status'] = 'resolved_price_component_not_account'
                opposite = 'SELL' if spec['signal_side'] == 'BUY' else 'BUY'
                sides = dict(zip(ROLES, (spec['signal_side'], opposite, 'BUY', 'SELL', spec['first_half_side'])))
                row['outcomes'] = cost_outcomes(entry, exit_at, sides, instrument_id=instrument,
                    market_function=market_function, cost_function=cost_function)
        rows.append(row)
    return dict(rows=rows, wall_seconds=time.perf_counter()-began, cpu_seconds=time.process_time()-cpu)


def summarize(rows, expected_sessions, *, profile):
    candidate, _, _ = identity(profile)
    result = summarize_rows(rows, expected_sessions, candidate=candidate, roles=ROLES,
        benchmark_roles=('always_long_control', 'always_short_control', 'first_half_control'))
    for summary in result['summary']:
        if summary['role'] == 'first_half_control':
            group = [r for r in rows if r['year'] == summary['year'] and r['outcomes']]
            summary['no_exposure_days'] = sum(r['first_half_side'] is None for r in group)
    for year in (2019, 2022):
        for scenario in SCENARIOS:
            selected = [s for s in result['summary'] if s.get('year') == year and s.get('scenario') == scenario]
            primary = next(s for s in selected if s['role'] == 'primary')
            first = next(s for s in selected if s['role'] == 'first_half_control')
            result['summary'].append(dict(year=year, scenario=scenario, role='primary_minus_first_half',
                planned=primary['planned'], resolved=primary['resolved'], unresolved=primary['unresolved'],
                known_net_usd_per_research_unit=str(D(primary['known_net_usd_per_research_unit'])-D(first['known_net_usd_per_research_unit']))))
    return result
