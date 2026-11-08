"""Registered opening reversal price component; no account policy or broker calls."""
from datetime import datetime, timezone
from decimal import Decimal as D
import time

from fomc_price_component import observation
from nasdaq_cash_calendar import sessions_for
from nasdaq_h4_study import DAY, GRID, SCENARIOS

MINUTE = 60000
CANDIDATE = 'nasdaq-overnight-first30-reversal-price-component-v1'
ROLES = ('primary', 'opposite_gap_control', 'always_long_control', 'always_short_control')


def _predictor(pair, at, field):
    if pair is None:
        return None
    if len(pair) != 2 or any(type(r['timestamp']) is not int or r['timestamp'] != at for r in pair):
        raise ValueError('predictor_side_clock')
    bid, ask = (D(str(r[field])) for r in pair)
    if any(not p.is_finite() or p <= 0 or p % GRID for p in (bid, ask)):
        raise ValueError('predictor_price_grid')
    return bid if bid <= ask else None


def prepare(sessions, pairs, *, start, end):
    if (type(start) is not int or type(end) is not int or start % DAY or end % DAY
            or end <= start):
        raise ValueError('component_window')
    year = datetime.fromtimestamp(start / 1000, timezone.utc).year
    if year not in (2019, 2022) or end > int(datetime(year + 1, 1, 1, tzinfo=timezone.utc).timestamp() * 1000):
        raise ValueError('registered_development_only_holdout_closed')
    expected = {**sessions_for(f'warmup-{year}'), **sessions_for(f'development-{year}')}
    if not sessions or list(sessions) != sorted(set(sessions)):
        raise ValueError('ordered_cash_calendar_required')
    selected = {d: s for d, s in expected.items() if next(iter(sessions)) <= d <= next(reversed(sessions))}
    if list(sessions.items()) != list(selected.items()):
        raise ValueError('cash_calendar_day_clock_or_missing_session')
    specs, previous, previous_at = [], None, None
    for day, stamps in sessions.items():
        regular = len(stamps) == 390
        current = _predictor(pairs.get(stamps[0]), stamps[0], 'open') if regular else None
        valid = regular and previous is not None and current is not None
        gap = current - previous if valid else None
        side = 'SELL' if valid and gap > 0 else 'BUY' if valid and gap < 0 else None
        if start <= stamps[0] < end:
            specs.append(dict(candidate=CANDIDATE, session=day, year=year,
                regular_session=regular, predictor_valid=valid, signal_side=side,
                planned_trade=side is not None, gap_bid_price_units=str(gap) if valid else None,
                previous_close_ms=previous_at, previous_close_bid=str(previous) if previous is not None else None,
                current_open_bid=str(current) if current is not None else None,
                signal_known_at_ms=stamps[0] + MINUTE if regular else None,
                decision_ms=stamps[1] if regular else None, entry_ms=stamps[2] if regular else None,
                exit_decision_ms=stamps[28] if regular else None, exit_ms=stamps[29] if regular else None,
                status='planned_price_component' if side else 'calendar_halfday_skipped' if not regular
                else 'valid_flat_gap' if valid else 'signal_unavailable'))
        previous_at = stamps[-1]
        previous = _predictor(pairs.get(previous_at), previous_at, 'close')
    return specs


def evaluate(sessions, pairs, *, start, end, market_function, cost_function, progress=None, deadline=None):
    began, cpu = time.perf_counter(), time.process_time()
    specs = prepare(sessions, pairs, start=start, end=end)
    rows = []
    for i, spec in enumerate(specs):
        if i % 32 == 0:
            if deadline is not None and time.perf_counter() > deadline:
                raise TimeoutError('overnight_component_deadline')
            if progress:
                progress(i, len(specs))
        row = dict(**spec, entry=None, exit=None, outcomes={}, path_expected_minutes=None,
            path_observed_minutes=None, clean_oos=False, account_simulated=False,
            execution_authorized=False, broker_calls=0, model_calls=0)
        if spec['planned_trade']:
            if not spec['previous_close_ms'] + MINUTE < spec['signal_known_at_ms'] == spec['decision_ms'] < spec['entry_ms'] < spec['exit_decision_ms'] < spec['exit_ms']:
                raise ValueError('opening_reversal_causal_clock')
            entry = observation(pairs.get(spec['entry_ms']), spec['entry_ms'], duration_ms=MINUTE)
            exit_at = observation(pairs.get(spec['exit_ms']), spec['exit_ms'], duration_ms=MINUTE)
            path = range(spec['entry_ms'], spec['exit_ms'], MINUTE)
            row.update(entry=entry, exit=exit_at, path_expected_minutes=len(path),
                path_observed_minutes=sum(t in pairs for t in path), status='unresolved_endpoint')
            if entry['bid'] is not None and exit_at['bid'] is not None:
                row['status'] = 'resolved_price_component_not_account'
                for scenario in SCENARIOS:
                    instrument, model, _ = market_function(scenario)
                    if instrument.instrument_id != 'USATECH.IDX/USD' or instrument.contract_size != 1:
                        raise ValueError('opening_reversal_geometry_identity')
                    opposite = 'SELL' if spec['signal_side'] == 'BUY' else 'BUY'
                    sides = (spec['signal_side'], opposite, 'BUY', 'SELL')
                    row['outcomes'][scenario] = {}
                    for role, side in zip(ROLES, sides):
                        costs = cost_function(model, side, D(1), instrument.contract_size,
                            D(entry['bid']), D(entry['ask']), D(exit_at['bid']), D(exit_at['ask']))
                        row['outcomes'][scenario][role] = dict(side=side, costs=costs,
                            net_usd_per_research_unit=str(costs['net_account']), planned_funding_usd='0')
        rows.append(row)
    return dict(rows=rows, wall_seconds=time.perf_counter() - began, cpu_seconds=time.process_time() - cpu)


def summarize(rows, expected_sessions):
    if set(expected_sessions) != {2019, 2022} or any(not v or list(v) != sorted(set(v)) for v in expected_sessions.values()):
        raise ValueError('registered_two_year_census')
    expected = [(year, day) for year in (2019, 2022) for day in expected_sessions[year]]
    if [(r['year'], r['session']) for r in rows] != expected:
        raise ValueError('missing_or_repeated_session_rows')
    for r in rows:
        if (r['candidate'] != CANDIDATE or any(r[k] is not False for k in ('clean_oos', 'account_simulated', 'execution_authorized'))
                or any(type(r[k]) is not int or r[k] != 0 for k in ('broker_calls', 'model_calls'))):
            raise ValueError('component_identity_or_authority')
        if r['outcomes'] and (not r['planned_trade'] or set(r['outcomes']) != set(SCENARIOS)
                or any(set(v) != set(ROLES) for v in r['outcomes'].values())):
            raise ValueError('unregistered_outcomes')
    summary, gates = [], []
    for year in (2019, 2022):
        group = [r for r in rows if r['year'] == year]
        regular = [r for r in group if r['regular_session']]
        valid = sum(r['predictor_valid'] for r in regular)
        planned = [r for r in group if r['planned_trade']]
        resolved = [r for r in planned if r['outcomes']]
        for scenario in SCENARIOS:
            nets = {}
            for role in ROLES:
                values = [D(r['outcomes'][scenario][role]['net_usd_per_research_unit']) for r in resolved]
                if any(not v.is_finite() for v in values):
                    raise ValueError('nonfinite_component_net')
                positive = [v for v in values if v > 0]
                nets[role] = sum(values, D(0))
                summary.append(dict(year=year, scenario=scenario, role=role, cash_sessions=len(group),
                    regular_sessions=len(regular), predictor_valid=valid, signal_unavailable=len(regular)-valid,
                    planned=len(planned), resolved=len(resolved), unresolved=len(planned)-len(resolved),
                    known_net_usd_per_research_unit=str(nets[role]), positive=sum(v > 0 for v in values),
                    negative=sum(v < 0 for v in values),
                    largest_positive_share=str(max(positive)/sum(positive)) if positive else None,
                    missing_path_windows=sum(r['path_observed_minutes'] != r['path_expected_minutes'] for r in resolved)))
            if scenario == 'stress':
                gates.append(dict(year=year, retained=len(planned) >= 100 and valid*100 >= len(regular)*98
                    and len(resolved)*100 >= len(planned)*98 and nets['primary'] > 0
                    and nets['primary'] > max(nets['always_long_control'], nets['always_short_control'])))
        summary.append(dict(year=year, role='null_no_exposure', entries=0, known_net_usd_per_research_unit='0'))
    return dict(candidate=CANDIDATE, summary=summary, year_gates=gates,
        retained_for_further_research=all(g['retained'] for g in gates), scope='price_component_not_account_policy',
        clean_oos=False, account_simulated=False, execution_authorized=False, broker_calls=0, model_calls=0)
