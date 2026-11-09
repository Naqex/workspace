"""R091 fixed-unit economics; not SL/account/prop or broker execution."""
from collections import Counter
from decimal import Decimal as D

import round_level_feature as f
from fixing_clock_probe import price_return

RULES = ('follow', 'opposite', 'null')
SCENARIOS = ('reference', 'stress')
CANDIDATE = 'eurusd-first-M5-round50-cross-follow60-NY-v1'


def evaluate_one(day, quotes, geometry):
    row = f.feature(day, quotes, geometry)
    entry = f.endpoint(quotes.get(row['entry_ms']), row['entry_ms']) if row['selected'] else None
    exit_at = f.endpoint(quotes.get(row['exit_ms']), row['exit_ms']) if row['selected'] else None
    if entry is not None and exit_at is not None:
        if not row['decision_ms'] < entry['time_msc'] < exit_at['time_msc'] or not entry['sequence'] < exit_at['sequence']:
            raise ValueError('R091_entry_exit_order')
    row.update(candidate=CANDIDATE, entry_quote=entry, exit_quote=exit_at, outcomes={})
    for scenario in SCENARIOS:
        row['outcomes'][scenario] = {}
        for rule in RULES:
            side = row['side'] if row['selected'] and rule != 'null' else None
            if side is not None and rule == 'opposite':
                side = 'SELL' if side == 'BUY' else 'BUY'
            if side is None:
                value = dict(side=None, exposed=False, resolved=True, net='0', costs=None)
            elif entry is None or exit_at is None:
                value = dict(side=side, exposed=True, resolved=False, net=None, costs=None)
            else:
                cost = price_return(side, entry, exit_at, scenario)
                value = dict(side=side, exposed=True, resolved=True, net=cost['net_usd_per_standard_lot'], costs=cost['costs'])
            row['outcomes'][scenario][rule] = value
    return row


def evaluate(quotes):
    return [evaluate_one(day, quotes, geometry) for day in f.days() for geometry in f.OFFSETS]


def summarize(rows):
    expected = [(d.isoformat(), g) for d in f.days() for g in f.OFFSETS]
    if len(rows) != len(expected) or [(r['day'], r['geometry']) for r in rows] != expected:
        raise ValueError('R091_calendar_geometry_census')
    books, gates = [], []
    for year in f.YEARS:
        adequacy = []
        for geometry in f.OFFSETS:
            cohort = [r for r in rows if r['year'] == year and r['geometry'] == geometry]
            counts = dict(Counter(r['status'] for r in cohort))
            selected = sum(r['selected'] for r in cohort)
            known = counts.get('no_cross', 0)+counts.get('cross', 0)
            for rule in RULES:
                for scenario in SCENARIOS:
                    values = [r['outcomes'][scenario][rule] for r in cohort]
                    exposed = [v for v in values if v['exposed']]
                    resolved = [v for v in exposed if v['resolved']]
                    net = sum((D(v['net']) for v in resolved), D(0))
                    books.append(dict(year=year, geometry=geometry, rule=rule, scenario=scenario,
                        days=len(cohort), feature_status_counts=counts, selected=selected, exposed=len(exposed),
                        resolved=len(resolved), unknown=len(exposed)-len(resolved), known_net=str(net),
                        strict_net=str(net) if len(exposed) == len(resolved) else None,
                        known_mean=str(net/len(resolved)) if resolved else None))
            primary = next(b for b in books if b['year'] == year and b['geometry'] == geometry
                           and b['rule'] == 'follow' and b['scenario'] == 'stress')
            adequacy.append(selected >= 20 and known*100 >= len(cohort)*98 and primary['unknown'] == 0)
        real = next(b for b in books if b['year'] == year and b['geometry'] == 'round'
                    and b['rule'] == 'follow' and b['scenario'] == 'stress')
        placebo = next(b for b in books if b['year'] == year and b['geometry'] == 'placebo'
                       and b['rule'] == 'follow' and b['scenario'] == 'stress')
        economic_positive = real['strict_net'] is not None and D(real['strict_net']) > 0
        increment_positive = (real['known_mean'] is not None and placebo['known_mean'] is not None
                              and D(real['known_mean']) > D(placebo['known_mean']))
        adequate = all(adequacy)
        retained = adequate and economic_positive and increment_positive
        gates.append(dict(year=year, adequate=adequate, economic_positive=economic_positive,
                          increment_positive=increment_positive, retained=retained,
                          status='inconclusive' if not adequate else 'retained' if retained else 'not_retained'))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates, financial_cases=len(rows)*6,
                retained_for_temporal_review=all(g['retained'] for g in gates),
                unit='USD_per_100000EUR_research_notional', account_simulated=False,
                clean_oos=False, execution_authorized=False, broker_calls=0)
