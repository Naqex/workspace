"""Published sign agreement on sealed tick components, no new price simulation."""
from copy import deepcopy
from decimal import Decimal as D

from index_cash_close_tick_component import CANDIDATES as PARENTS, DELAYS
from index_rest_of_day_component import ROLES
from index_overnight_reversal_component import SCENARIOS

CANDIDATES = {
    'us500': 'us500-rod-firsthalf-consensus-tick-component-v1',
    'nasdaq': 'nasdaq-rod-firsthalf-consensus-tick-component-v1',
}


def select(parent, *, profile):
    if (profile not in CANDIDATES or parent['candidate'] != PARENTS[profile]
            or parent['year'] not in (2019, 2022) or type(parent['delay_ms']) is not int
            or parent['delay_ms'] not in DELAYS
            or any(type(parent[k]) is not bool for k in ('regular_session', 'predictor_valid', 'planned_trade'))
            or any(parent[k] is not False for k in ('execution_authorized', 'account_simulated', 'clean_oos', 'intrabar_equity_assessed'))
            or any(type(parent[k]) is not int or parent[k] != 0 for k in ('broker_calls', 'model_calls'))
            or parent['signal_side'] not in (None, 'BUY', 'SELL') or parent['first_half_side'] not in (None, 'BUY', 'SELL')):
        raise ValueError('registered_consensus_parent_scope')
    planned = parent['regular_session'] and parent['predictor_valid'] and parent['signal_side'] is not None
    if parent['planned_trade'] != planned or (parent['outcomes'] and not planned):
        raise ValueError('consensus_parent_signal_state')
    selected = planned and parent['signal_side'] == parent['first_half_side']
    row = deepcopy(parent)
    row.update(candidate=CANDIDATES[profile], parent_candidate=parent['candidate'],
               feature_source_candidate=parent['parent_candidate'], rod_side=parent['signal_side'],
               consensus_selected=selected, signal_side=parent['signal_side'] if selected else None,
               planned_trade=selected)
    if not selected:
        row.update(entry=None, exit=None, outcomes={}, status='consensus_no_exposure')
        row['no_exposure_reason'] = ('calendar_halfday' if not parent['regular_session'] else
            'predictor_unavailable' if not parent['predictor_valid'] else
            'rod_flat' if parent['signal_side'] is None else
            'first_half_flat' if parent['first_half_side'] is None else 'sign_disagreement')
    else:
        for scenario, values in row['outcomes'].items():
            if scenario not in SCENARIOS or set(values) != set(ROLES) or values['primary'] != values['first_half_control']:
                raise ValueError('consensus_first_half_must_equal_primary')
    return row


def summarize(rows, expected_sessions, *, profile):
    if profile not in CANDIDATES or set(expected_sessions) != {2019, 2022}:
        raise ValueError('consensus_summary_registered_scope')
    if any(not days or days != sorted(set(days)) for days in expected_sessions.values()):
        raise ValueError('ordered_unique_calendar_required')
    expected = [(delay, year, day) for delay in DELAYS for year in (2019, 2022) for day in expected_sessions[year]]
    if [(r['delay_ms'], r['year'], r['session']) for r in rows] != expected:
        raise ValueError('consensus_calendar_or_delay_census')
    for row in rows:
        if (row['candidate'] != CANDIDATES[profile] or row['parent_candidate'] != PARENTS[profile]
                or any(row[k] is not False for k in ('execution_authorized', 'account_simulated', 'clean_oos', 'intrabar_equity_assessed'))
                or any(type(row[k]) is not int or row[k] != 0 for k in ('broker_calls', 'model_calls'))
                or type(row['planned_trade']) is not bool or row['consensus_selected'] is not row['planned_trade']):
            raise ValueError('consensus_summary_identity_state_authority')
        if row['planned_trade'] and (not row['predictor_valid'] or not row['regular_session']
                or row['signal_side'] not in ('BUY', 'SELL') or row['signal_side'] != row['first_half_side']):
            raise ValueError('consensus_summary_signal_state')
        if row['outcomes']:
            if not row['planned_trade'] or set(row['outcomes']) != set(SCENARIOS):
                raise ValueError('consensus_unregistered_outcomes')
            for values in row['outcomes'].values():
                if set(values) != set(ROLES) or values['primary'] != values['first_half_control']:
                    raise ValueError('consensus_first_half_must_equal_primary')
        elif not row['planned_trade'] and (row['entry'] is not None or row['exit'] is not None):
            raise ValueError('no_exposure_cannot_have_fill')
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
                        raise ValueError('consensus_nonfinite_net')
                    nets[role] = sum(values, D(0))
                    summary.append(dict(delay_ms=delay, year=year, scenario=scenario, role=role,
                        cash_sessions=len(group), regular_sessions=len(regular), predictor_valid=valid,
                        planned=len(planned), resolved=len(resolved), unresolved=len(planned)-len(resolved),
                        no_exposure=len(group)-len(planned), known_net_usd_per_research_unit=str(nets[role]),
                        positive=sum(v > 0 for v in values), negative=sum(v < 0 for v in values),
                        intrabar_equity_assessed=False))
                if scenario == 'stress':
                    gates.append(dict(delay_ms=delay, year=year, retained=(len(planned) >= 100
                        and valid*100 >= len(regular)*98 and len(resolved)*100 >= len(planned)*98
                        and nets['primary'] > 0 and nets['primary'] > max(nets['always_long_control'], nets['always_short_control']))))
    return dict(candidate=CANDIDATES[profile], summary=summary, year_delay_gates=gates,
                retained_for_further_research=all(g['retained'] for g in gates),
                scope='price_component_not_account_policy', account_simulated=False,
                execution_authorized=False, clean_oos=False, broker_calls=0, model_calls=0)
