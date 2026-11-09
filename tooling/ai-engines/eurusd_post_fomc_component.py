"""R088 calendar-only EURUSD component; separate-side M1, never account orders."""
from datetime import date, datetime, timedelta, time
from decimal import Decimal as D
from zoneinfo import ZoneInfo

from fomc_price_component import DATES, PUBLICATIONS
from fixing_clock_probe import price_return

CANDIDATE = 'eurusd-post-fomc-12to24h-SELL-component-v1'
RULES = ('primary', 'opposite_control', 'null')
NY = ZoneInfo('America/New_York'); MINUTE = 60000


def schedules():
    rows = []
    for year in (2019, 2022):
        for event in DATES[year]:
            for role, shift in (('primary', 0), ('matched_week_control', 7)):
                day = date.fromisoformat(event)-timedelta(days=shift)
                anchor = datetime.combine(day, time(14), NY)
                decision = anchor+timedelta(hours=12)
                entry = decision+timedelta(minutes=1)
                exit_at = anchor+timedelta(hours=24, minutes=-1)
                rollover = datetime.combine(entry.date(), time(17), NY)
                if not decision < entry < exit_at < rollover or entry.date() != exit_at.date():
                    raise ValueError('R088_declared_no_rollover_window')
                publication = int(datetime.fromisoformat(PUBLICATIONS[year]).timestamp()*1000)
                if publication >= int(decision.timestamp()*1000):
                    raise ValueError('R088_calendar_not_known')
                rows.append(dict(candidate=CANDIDATE, year=year, event=event, role=role,
                    anchor_ms=int(anchor.timestamp()*1000), calendar_publication_ms=publication,
                    decision_ms=int(decision.timestamp()*1000), entry_ms=int(entry.timestamp()*1000),
                    exit_decision_ms=int(exit_at.timestamp()*1000)-MINUTE, exit_ms=int(exit_at.timestamp()*1000)))
    return rows


def observe(pair, at):
    result = dict(source_bar_open_ms=at, quote_timestamp_interval_ms=[at, at+MINUTE],
        known_at_upper_bound_ms=at+MINUTE, basis='EURUSD_separate_side_source_M1_Open',
        bid=None, ask=None, executable_tick_proven=False, broker_spec_verified=False)
    if pair is None: return result
    if len(pair) != 2 or any(r['timestamp'] != at for r in pair):
        raise ValueError('R088_source_side_clock')
    bid, ask = (D(str(r['open'])) for r in pair)
    if any(not p.is_finite() or p <= 0 or p % D('.00001') for p in (bid, ask)):
        raise ValueError('R088_source_price_grid')
    if bid <= ask: result.update(bid=str(bid), ask=str(ask))
    return result


def prepare(pairs):
    rows = []
    for spec in schedules():
        entry, exit_at = (observe(pairs.get(spec[k]), spec[k]) for k in ('entry_ms', 'exit_ms'))
        path = range(spec['entry_ms'], spec['exit_ms']+MINUTE, MINUTE)
        rows.append(dict(**spec, entry=entry, exit=exit_at,
            holding_role_expected_minutes=len(path), holding_paired_source_minutes=sum(t in pairs for t in path),
            endpoints_resolved=entry['bid'] is not None and exit_at['bid'] is not None, outcomes={},
            clean_oos=False, account_simulated=False, execution_authorized=False, broker_calls=0))
    return rows


def evaluate(prepared):
    rows = []
    expected = schedules()
    if len(prepared) != 32 or any(any(r[k] != v for k, v in s.items()) for r, s in zip(prepared, expected)):
        raise ValueError('R088_registered_calendar_census')
    for r in prepared:
        row = dict(r, outcomes={})
        for scenario in ('reference', 'stress'):
            row['outcomes'][scenario] = {}
            for rule, side in zip(RULES, ('SELL', 'BUY', None)):
                if side is None:
                    result = dict(side=None, resolved=True, net_usd_per_research_unit='0', costs=None)
                elif not r['endpoints_resolved']:
                    result = dict(side=side, resolved=False, net_usd_per_research_unit=None, costs=None)
                else:
                    cost = price_return(side, r['entry'], r['exit'], scenario)
                    result = dict(side=side, resolved=True, net_usd_per_research_unit=cost['net_usd_per_standard_lot'], costs=cost['costs'])
                row['outcomes'][scenario][rule] = result
        rows.append(row)
    return rows


def summarize(rows):
    if len(rows) != 32 or any(any(r[k] != v for k, v in s.items()) for r, s in zip(rows, schedules())):
        raise ValueError('R088_registered_result_rows')
    books = []; gates = []
    for year in (2019, 2022):
        for anchor in ('primary', 'matched_week_control'):
            for rule in RULES:
                for scenario in ('reference', 'stress'):
                    vs = [r['outcomes'][scenario][rule] for r in rows if r['year'] == year and r['role'] == anchor]
                    known = [v for v in vs if v['resolved']]
                    net = sum((D(v['net_usd_per_research_unit']) for v in known), D(0))
                    books.append(dict(year=year, anchor=anchor, rule=rule, scenario=scenario, planned=8,
                        resolved=len(known), known_subset_net=str(net), strict_net=str(net) if len(known) == 8 else None))
        primary, matched = [v['strict_net'] for v in books if v['year'] == year and v['rule'] == 'primary' and v['scenario'] == 'stress']
        gates.append(dict(year=year, retained=primary is not None and matched is not None and D(primary)>0 and D(primary)-D(matched)>0))
    return dict(candidate=CANDIDATE, books=books, year_gates=gates,
        retained_for_risk_review=all(g['retained'] for g in gates), unit='USD_per_100000EUR_research_notional',
        clean_oos=False, account_simulated=False, execution_authorized=False, broker_calls=0)
