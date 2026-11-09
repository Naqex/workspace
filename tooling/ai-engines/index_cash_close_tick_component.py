"""Registered archived-quote rROD scenarios; not account or broker execution."""
from decimal import Decimal as D

from index_rest_of_day_component import CANDIDATES as PARENTS, ROLES
from index_overnight_reversal_component import cost_outcomes, profile_identity, SCENARIOS

CANDIDATES = {
    'us500': 'us500-restofday-cashclose-tick-component-v2',
    'nasdaq': 'nasdaq-restofday-cashclose-tick-component-v2',
}
DELAYS = (1000, 2000, 60000)
MAX_WAIT = 60000
GRID = D('.001')
FEATURES = ('session', 'year', 'regular_session', 'predictor_valid', 'signal_side',
            'first_half_side', 'planned_trade', 'previous_close_ms', 'previous_close_bid',
            'first_half_close_bid', 'late_close_bid', 'signal_known_at_ms', 'decision_ms')


def decimal_price(value):
    if type(value) is not str:
        raise ValueError('frozen_price_string_required')
    number = D(value)
    if not number.is_finite() or number <= 0 or number % GRID:
        raise ValueError('frozen_price_grid')
    return number


def direction(change):
    return 'BUY' if change > 0 else 'SELL' if change < 0 else None


def checked_hour(hour, spec, profile, role):
    source = profile_identity(profile)[2]
    instrument = 'usa500idxusd' if profile == 'us500' else 'usatechidxusd'
    if (type(hour) is not dict or hour['schema'] != 'index-source-hour-review-v1'
            or hour['instrument'] != instrument or hour['role'] != role
            or hour['session'] != spec['session'] or hour['year'] != spec['year']
            or hour['execution_authorized'] is not False or hour['exposure'] != 'consumed_development'
            or hour['price_grid'] != '0.001' or hour['price_unit'] != 'quoted_index_points'
            or hour['timestamp_unit'] != 'UTC_ms_archived_event_not_arrival'
            or type(hour['ticks']) is not int or hour['ticks'] < 0
            or len(hour['availability']) != 4
            or {x['scenario_delay_ms'] for x in hour['availability']} != {200, *DELAYS}):
        raise ValueError('registered_tick_hour_identity_units_or_scope')
    return source


def observation(hour, *, decision, delay):
    item = next(x for x in hour['availability'] if x['scenario_delay_ms'] == delay)
    if type(item['target_ms']) is not int or item['target_ms'] != decision + delay:
        raise ValueError('tick_target_causal_clock')
    quote = item['quote']
    result = dict(bid=None, ask=None, source_ordinal=None, tick_timestamp_ms=None,
                  target_ms=item['target_ms'], wait_ms=None, status='quote_unavailable',
                  basis='archived_joint_quote_timestamp_scenario', executable_tick_proven=False,
                  broker_spec_verified=False, execution_authorized=False)
    usable = False
    if quote is not None:
        keys = ('timestamp', 'source_ordinal', 'wait_ms', 'bid_units', 'ask_units')
        if any(type(quote[k]) is not int for k in keys):
            raise ValueError('tick_integer_quote_fields')
        hour_start = decision - 1800000 if hour['role'] == 'entry_hour' else decision
        if (not 0 <= quote['source_ordinal'] < hour['ticks']
                or not item['target_ms'] <= quote['timestamp'] < hour_start + 3600000
                or quote['wait_ms'] != quote['timestamp'] - item['target_ms']
                or not 0 < quote['bid_units'] <= quote['ask_units'] <= 2**53-1):
            raise ValueError('tick_quote_geometry_or_clock')
        usable = quote['wait_ms'] <= MAX_WAIT
        result.update(source_ordinal=quote['source_ordinal'], tick_timestamp_ms=quote['timestamp'],
                      wait_ms=quote['wait_ms'], status='observed_timestamp_scenario' if usable else 'quote_expired')
        if usable:
            result.update(bid=str(D(quote['bid_units'])*GRID), ask=str(D(quote['ask_units'])*GRID))
    if type(item['available_within_60s_after_target']) is not bool or item['available_within_60s_after_target'] != usable:
        raise ValueError('quote_availability_binding')
    return result


def evaluate_spec(spec, entry_hour, exit_hour, *, profile, delay_ms, market_function, cost_function):
    if profile not in CANDIDATES or type(delay_ms) is not int or delay_ms not in DELAYS:
        raise ValueError('registered_profile_and_delay')
    if (spec['candidate'] != PARENTS[profile] or spec['year'] not in (2019, 2022)
            or any(type(spec[k]) is not bool for k in ('regular_session', 'predictor_valid', 'planned_trade'))
            or any(spec[k] is not False for k in ('execution_authorized', 'account_simulated', 'clean_oos'))
            or any(type(spec[k]) is not int or spec[k] != 0 for k in ('broker_calls', 'model_calls'))):
        raise ValueError('frozen_spec_identity_scope_or_authority')
    row = {k: spec[k] for k in FEATURES}
    row.update(candidate=CANDIDATES[profile], parent_candidate=spec['candidate'], delay_ms=delay_ms,
               entry=None, exit=None, outcomes={}, exit_decision_ms=None,
               status='calendar_halfday_skipped' if not spec['regular_session'] else 'signal_unavailable',
               account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0, model_calls=0,
               intrabar_equity_assessed=False)
    if not spec['regular_session']:
        if spec['predictor_valid'] or spec['planned_trade']:
            raise ValueError('halfday_cannot_be_regular_signal')
        return row
    checked_hour(entry_hour, spec, profile, 'entry_hour')
    checked_hour(exit_hour, spec, profile, 'exit_hour')
    decision = spec['decision_ms']
    if (type(decision) is not int or spec['signal_known_at_ms'] != decision
            or decision >= 1735689600000):
        raise ValueError('signal_clock_or_holdout')
    row['exit_decision_ms'] = decision + 1800000
    if not spec['predictor_valid']:
        if spec['planned_trade']:
            raise ValueError('unavailable_predictor_cannot_trade')
        return row
    previous, first, late = map(decimal_price, (spec['previous_close_bid'], spec['first_half_close_bid'], spec['late_close_bid']))
    side, first_side = direction(late-previous), direction(first-previous)
    if (type(spec['previous_close_ms']) is not int or spec['previous_close_ms']+60000 >= decision
            or side != spec['signal_side'] or first_side != spec['first_half_side']
            or spec['planned_trade'] != (side is not None)):
        raise ValueError('frozen_predictor_direction_or_time')
    confirmation = entry_hour['late_predictor']
    if (confirmation is None or confirmation['canonical_present'] is not True
            or confirmation['ticks_present'] is not True or confirmation['close_exact'] is not True):
        row.update(predictor_valid=False, planned_trade=False, status='late_predictor_tick_confirmation_unavailable')
        return row
    if side is None:
        row['status'] = 'valid_flat_rod'
        return row
    entry = observation(entry_hour, decision=decision, delay=delay_ms)
    exit_at = observation(exit_hour, decision=row['exit_decision_ms'], delay=delay_ms)
    row.update(entry=entry, exit=exit_at, status='unresolved_endpoint')
    if entry['bid'] is None or exit_at['bid'] is None:
        return row
    if not decision < entry['tick_timestamp_ms'] < row['exit_decision_ms'] < exit_at['tick_timestamp_ms']:
        raise ValueError('cash_close_causal_execution_order')
    sides = dict(zip(ROLES, (side, 'SELL' if side == 'BUY' else 'BUY', 'BUY', 'SELL', first_side)))
    row.update(status='resolved_tick_timestamp_component_not_account', outcomes=cost_outcomes(
        entry, exit_at, sides, instrument_id=profile_identity(profile)[1],
        market_function=market_function, cost_function=cost_function))
    return row


def summarize(rows, expected_sessions, *, profile):
    if profile not in CANDIDATES or set(expected_sessions) != {2019, 2022}:
        raise ValueError('registered_summary_profile_years')
    for days in expected_sessions.values():
        if not days or days != sorted(set(days)):
            raise ValueError('ordered_unique_calendar_required')
    census = [(delay, year, day) for delay in DELAYS for year in (2019, 2022) for day in expected_sessions[year]]
    if [(r['delay_ms'], r['year'], r['session']) for r in rows] != census:
        raise ValueError('missing_duplicate_or_unregistered_scenario_day')
    for row in rows:
        if (row['candidate'] != CANDIDATES[profile] or any(row[k] is not False for k in ('clean_oos', 'account_simulated', 'execution_authorized'))
                or any(type(row[k]) is not int or row[k] != 0 for k in ('broker_calls', 'model_calls'))
                or any(type(row[k]) is not bool for k in ('regular_session', 'predictor_valid', 'planned_trade'))):
            raise ValueError('summary_identity_or_authority')
        if row['planned_trade'] and (not row['regular_session'] or not row['predictor_valid'] or row['signal_side'] not in ('BUY', 'SELL')):
            raise ValueError('summary_signal_state')
        if row['outcomes'] and (not row['planned_trade'] or set(row['outcomes']) != set(SCENARIOS)
                or any(set(values) != set(ROLES) for values in row['outcomes'].values())):
            raise ValueError('summary_cost_roles_or_exposure')
    summary, gates = [], []
    for delay in DELAYS:
        for year in (2019, 2022):
            group = [r for r in rows if r['delay_ms'] == delay and r['year'] == year]
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
                    positives = [v for v in values if v > 0]
                    nets[role] = sum(values, D(0))
                    summary.append(dict(delay_ms=delay, year=year, scenario=scenario, role=role,
                        cash_sessions=len(group), regular_sessions=len(regular), predictor_valid=valid,
                        signal_unavailable=len(regular)-valid, planned=len(planned), resolved=len(resolved),
                        unresolved=len(planned)-len(resolved), known_net_usd_per_research_unit=str(nets[role]),
                        positive=sum(v > 0 for v in values), negative=sum(v < 0 for v in values),
                        largest_positive_share=str(max(positives)/sum(positives)) if positives else None,
                        intrabar_equity_assessed=False))
                if scenario == 'stress':
                    gate = (len(planned) >= 100 and valid*100 >= len(regular)*98
                        and len(resolved)*100 >= len(planned)*98 and nets['primary'] > 0
                        and nets['primary'] > max(nets[role] for role in ('always_long_control', 'always_short_control', 'first_half_control')))
                    gates.append(dict(delay_ms=delay, year=year, retained=gate))
    return dict(candidate=CANDIDATES[profile], summary=summary, year_delay_gates=gates,
                retained_for_further_research=all(g['retained'] for g in gates),
                scope='price_component_not_account_policy', account_simulated=False, clean_oos=False,
                execution_authorized=False, broker_calls=0, model_calls=0)
