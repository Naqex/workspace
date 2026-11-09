"""Own R090 hourly shock continuation, not tick-first-crossing or account orders."""
from collections import Counter
from datetime import date, timedelta
from decimal import Decimal as D
from fractions import Fraction

import abnormal_day_feature as prior_day
from abnormal_day_component import days, endpoint, RULES, SCENARIOS
from fixing_clock_probe import price_return

CANDIDATE = 'eurusd-first-hourly-shock-continuation-utc-v1'


def prefix_mid(q, target, decision):
    if q is None:
        return None
    at, known = q['time_msc'], q['known_at_upper_bound_ms']
    if type(at) is not int or type(known) is not int or known < at:
        raise ValueError('R090_invalid_source_clock')
    bid, ask = (D(str(q[k])) for k in ('bid', 'ask'))
    if any(not p.is_finite() or p <= 0 or p % prior_day.GRID for p in (bid, ask)) or bid > ask:
        raise ValueError('R090_invalid_source_price')
    if not 0 <= at-target <= 60000:
        return None
    if known > decision:
        raise ValueError('R090_future_signal_quote')
    return (Fraction(bid)+Fraction(ask))/2


def feature(day, observations, quotes):
    if day.year not in (2019, 2022) or day.weekday() >= 5:
        raise ValueError('R090_registered_day_required')
    early = prior_day.utc_ms(day, 1, 1)
    required = prior_day.calibration_days(day)
    returns = [prior_day._return(observations.get(d.isoformat()), d, early) for d in required]
    row = dict(candidate=CANDIDATE, day=day.isoformat(), year=day.year,
        calibration_days=[d.isoformat() for d in required],
        missing_days=[d.isoformat() for d, v in zip(required, returns) if v is None],
        status='unavailable_history', primary_side=None, signal_hour=None, current_return=None,
        decision_ms=None, entry_ms=None, exit_decision_ms=prior_day.utc_ms(day, 19, 59),
        exit_ms=prior_day.utc_ms(day, 20), checked_hours=[], selected=False,
        account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0)
    if row['missing_days']:
        return row
    mean = sum(returns, Fraction(0))/20
    variance = sum(((r-mean)**2 for r in returns), Fraction(0))/19
    row.update(calibration_mean=prior_day.rational(mean), calibration_sample_variance=prior_day.rational(variance))
    if variance == 0:
        row['status'] = 'unavailable_zero_variance'
        return row
    base = prefix_mid(quotes.get(prior_day.utc_ms(day, 0)), prior_day.utc_ms(day, 0), early)
    row['status'] = 'unavailable_prefix'
    if base is None:
        return row
    for hour in range(1, 19):
        target, decision = prior_day.utc_ms(day, hour), prior_day.utc_ms(day, hour, 1)
        current = prefix_mid(quotes.get(target), target, decision)
        row['checked_hours'].append(hour)
        if current is None:
            return row
        change = current/base-1
        delta = change-mean
        if delta*delta > 4*variance and ((change > 0 and delta > 0) or (change < 0 and delta < 0)):
            row.update(status='shock', selected=True, primary_side='BUY' if change > 0 else 'SELL',
                signal_hour=hour, current_return=prior_day.rational(change), decision_ms=decision,
                entry_ms=prior_day.utc_ms(day, hour+1))
            return row
    row['status'] = 'normal'
    return row


def evaluate_one(day, observations, quotes):
    row = feature(day, observations, quotes)
    entry = endpoint(quotes.get(row['entry_ms']), row['entry_ms']) if row['selected'] else None
    exit_at = endpoint(quotes.get(row['exit_ms']), row['exit_ms']) if row['selected'] else None
    if entry is not None and exit_at is not None and not row['decision_ms'] < entry['time_msc'] < exit_at['time_msc']:
        raise ValueError('R090_entry_exit_order')
    row.update(entry_quote=entry, exit_quote=exit_at, outcomes={})
    for scenario in SCENARIOS:
        row['outcomes'][scenario] = {}
        for rule in RULES:
            side = row['primary_side'] if row['selected'] and rule != 'null' else None
            if side and rule == 'opposite_control':
                side = 'SELL' if side == 'BUY' else 'BUY'
            if side is None:
                value = dict(side=None, exposed=False, resolved=True, net_usd_per_research_unit='0', costs=None)
            elif entry is None or exit_at is None:
                value = dict(side=side, exposed=True, resolved=False, net_usd_per_research_unit=None, costs=None)
            else:
                cost = price_return(side, entry, exit_at, scenario)
                value = dict(side=side, exposed=True, resolved=True,
                    net_usd_per_research_unit=cost['net_usd_per_standard_lot'], costs=cost['costs'])
            row['outcomes'][scenario][rule] = value
    return row


def evaluate(observations, quotes):
    return [evaluate_one(day, observations, quotes) for day in days()]


def summarize(rows):
    if len(rows) != 521 or any(r['day'] != day.isoformat() for r, day in zip(rows, days())):
        raise ValueError('R090_weekday_census')
    books, gates = [], []
    for year in (2019, 2022):
        cohort = [r for r in rows if r['year'] == year]
        counts = dict(Counter(r['status'] for r in cohort))
        selected = sum(r['selected'] for r in cohort)
        for rule in RULES:
            for scenario in SCENARIOS:
                exposed = [r['outcomes'][scenario][rule] for r in cohort if r['outcomes'][scenario][rule]['exposed']]
                resolved = [v for v in exposed if v['resolved']]
                net = sum((D(v['net_usd_per_research_unit']) for v in resolved), D(0))
                books.append(dict(year=year, rule=rule, scenario=scenario, planned_weekdays=len(cohort),
                    feature_status_counts=counts, selected_shocks=selected, exposed=len(exposed),
                    resolved_exposed=len(resolved), unresolved_exposed=len(exposed)-len(resolved),
                    known_subset_net=str(net), strict_net=str(net) if len(resolved) == len(exposed) else None))
        primary = next(b for b in books if b['year'] == year and b['rule'] == 'primary' and b['scenario'] == 'stress')
        available = counts.get('normal', 0)+counts.get('shock', 0)
        adequate = selected >= 8 and available*100 >= len(cohort)*80 and primary['unresolved_exposed'] == 0
        retained = adequate and D(primary['strict_net']) > 0
        gates.append(dict(year=year, available_features=available, planned_weekdays=len(cohort),
            status='inconclusive' if not adequate else 'positive' if retained else 'nonpositive', retained=retained))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates, financial_cases=len(rows)*6,
        retained_for_temporal_review=all(g['retained'] for g in gates), unit='USD_per_100000EUR_research_notional',
        account_simulated=False, clean_oos=False, execution_authorized=False, broker_calls=0)
