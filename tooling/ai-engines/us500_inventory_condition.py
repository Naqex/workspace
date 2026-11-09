"""One registered pre-entry price proxy; no order-flow or account authority."""
from copy import deepcopy
from decimal import Decimal as D

import us500_euopen_component as parent
from nasdaq_cash_calendar import sessions_for

CANDIDATE = 'us500-prior-close-negative-euopen-price-component-v1'


def endpoint(pair, at, field):
    result = dict(timestamp=at, field=field, known_at_ms=at+60000,
                  bid=None, ask=None, status='missing_exact_minute')
    if pair is None:
        return result
    if len(pair) != 2 or field not in ('open', 'close') or any(
            type(r['timestamp']) is not int or r['timestamp'] != at for r in pair):
        raise ValueError('inventory_predictor_clock_field')
    bid, ask = (D(str(r[field])) for r in pair)
    if any(not v.is_finite() or v <= 0 or v % D('.001') for v in (bid, ask)):
        raise ValueError('inventory_predictor_price_grid')
    if ask < bid:
        result['status'] = 'crossed_endpoint'
    else:
        result.update(bid=str(bid), ask=str(ask), status='observed_separate_side_M1_proxy')
    return result


def prepare(year, pairs):
    sessions = sessions_for(f'development-{year}')
    specs = parent.schedule(year, sessions)
    result = []
    for i, spec in enumerate(specs):
        item = dict(session=spec['session'], year=year, previous_session=None,
                    eligible=False, predictor_valid=False, selected=False,
                    start=None, end=None, delta_mid=None, status='first_session_out_of_scope')
        if not spec['regular_session']:
            item['status'] = 'current_halfday'
        elif i:
            previous = specs[i-1]['session']; stamps = sessions[previous]
            item['previous_session'] = previous
            item['status'] = 'previous_halfday_abstain'
            if len(stamps) == 390:
                begin = endpoint(pairs.get(stamps[-30]), stamps[-30], 'open')
                end = endpoint(pairs.get(stamps[-1]), stamps[-1], 'close')
                if not begin['known_at_ms'] <= end['known_at_ms'] <= spec['decision_ms']:
                    raise ValueError('inventory_predictor_not_known_before_decision')
                valid = begin['bid'] is not None and end['bid'] is not None
                delta = ((D(end['bid'])+D(end['ask'])-D(begin['bid'])-D(begin['ask']))/2) if valid else None
                item.update(eligible=True, start=begin, end=end, predictor_valid=valid,
                            delta_mid=str(delta) if valid else None, selected=valid and delta < 0,
                            status='negative' if valid and delta < 0 else 'nonnegative' if valid else 'predictor_unknown')
        result.append(item)
    return result


def select(parents, predictors):
    specs = [s for year in (2019, 2022) for s in parent.schedule(year, sessions_for(f'development-{year}'))]
    if len(parents) != len(predictors) or len(parents) != len(specs):
        raise ValueError('inventory_full_calendar_census')
    result = []
    for old, pred, spec in zip(parents, predictors, specs):
        if (any(old[k] != v for k, v in spec.items())
                or (pred['year'], pred['session']) != (spec['year'], spec['session'])
                or any(old[k] is not False for k in ('clean_oos', 'account_simulated', 'execution_authorized', 'intrabar_equity_assessed'))
                or old['broker_calls'] != 0 or old['model_calls'] != 0 or old['funding_events']):
            raise ValueError('inventory_parent_identity_scope')
        if (type(pred['predictor_valid']) is not bool or type(pred['selected']) is not bool
                or pred['selected'] != (pred['predictor_valid'] and D(pred['delta_mid']) < 0)
                or (pred['predictor_valid'] and (not pred['eligible'] or pred['end']['known_at_ms'] > spec['decision_ms']))):
            raise ValueError('inventory_condition_or_known_at')
        row = deepcopy(old)
        row.update(candidate=CANDIDATE, parent_candidate=parent.CANDIDATE,
                   predictor=deepcopy(pred), planned_trade=pred['selected'],
                   signal_side='BUY' if pred['selected'] else None)
        if not pred['selected']:
            row.update(entry=None, exit=None, outcomes={}, status='conditional_no_exposure')
        result.append(row)
    return result


def decompose(rows, scenario):
    resolved = [r for r in rows if r['outcomes']]
    totals = {k:D(0) for k in ('mid_gross', 'embedded_spread', 'bidask_gross', 'slippage', 'commission', 'funding', 'net', 'rounding_residual')}
    for row in resolved:
        entry, exit_at = row['entry'], row['exit']; cost = row['outcomes'][scenario]['primary']['costs']
        mid = (D(exit_at['bid'])+D(exit_at['ask'])-D(entry['bid'])-D(entry['ask']))/2
        gross = D(exit_at['bid'])-D(entry['ask'])
        slip, commission, funding = (D(str(cost[k])) for k in ('slippage_account', 'commission_account', 'financing_account'))
        net = D(row['outcomes'][scenario]['primary']['net_usd_per_research_unit'])
        for k,v in dict(mid_gross=mid, embedded_spread=mid-gross, bidask_gross=gross,
                        slippage=slip, commission=commission, funding=funding, net=net,
                        rounding_residual=net-(gross-slip-commission-funding)).items():
            totals[k] += v
    return dict(resolved=len(resolved), **{k:str(v) for k,v in totals.items()})


def summarize(rows, parents):
    groups, gates = [], []
    for year in (2019, 2022):
        group = [r for r in rows if r['year'] == year]
        old = [r for r in parents if r['year'] == year]
        eligible = sum(r['predictor']['eligible'] for r in group)
        valid = sum(r['predictor']['predictor_valid'] for r in group)
        selected = [r for r in group if r['planned_trade']]
        resolved = [r for r in selected if r['outcomes']]
        for scenario in ('reference', 'stress'):
            nets = {role:sum((D(r['outcomes'][scenario][role]['net_usd_per_research_unit']) for r in resolved), D(0)) for role in parent.ROLES}
            groups.append(dict(year=year, scenario=scenario, rows=len(group), eligible_predictors=eligible,
                valid_predictors=valid, selected=len(selected), resolved=len(resolved), unknown=len(selected)-len(resolved),
                no_exposure=len(group)-len(selected), nets={k:str(v) for k,v in nets.items()},
                selected_decomposition=decompose(selected, scenario), parent_decomposition=decompose(old, scenario)))
            if scenario == 'stress':
                gates.append(dict(year=year, retained=(len(selected) >= 50 and eligible > 0 and valid*100 >= eligible*98
                    and len(resolved)*100 >= len(selected)*98 and nets['primary'] > max(D(0), nets['opposite_control']))))
    return dict(candidate=CANDIDATE, groups=groups, year_gates=gates, retained_for_further_research=all(g['retained'] for g in gates),
                clean_oos=False, account_simulated=False, execution_authorized=False, broker_calls=0, model_calls=0)
