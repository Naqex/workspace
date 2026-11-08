"""Frozen R024 price component; no positions, sizing, risk or broker execution."""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from decimal import Decimal as D
import hashlib
import json
from pathlib import Path
import sys
import time
from zoneinfo import ZoneInfo

from forex_study_batch import configure_source_root, digest, read, save

NY = ZoneInfo('America/New_York')
YEARS = (2019, 2022)
SLIPPAGE = {'reference': D(0), 'stress': D('.00002')}
CONTRACT = D(100000)
PIP = D('.0001')


def bind_core(path):
    configure_source_root(path)
    global CostModel, calculate_round_trip_cost
    from trading_workspace_v2.retained import CostModel, calculate_round_trip_cost


def stamp_ms(text):
    dt = datetime.strptime(text, '%Y%m%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
    return int(dt.timestamp())*1000 + dt.microsecond//1000


def quote(line, sequence):
    from trading_workspace_v2.replay_tick_execution import BrokerReplayTick
    stamp, bid, ask, _ = line.decode('utf-8').strip().split(',')
    q = BrokerReplayTick(time_msc=stamp_ms(stamp), sequence=sequence, bid=bid, ask=ask)
    if q.bid % D('.00001') or q.ask % D('.00001'):
        raise ValueError('selected_quote_grid')
    return q.model_dump(mode='json')


def clocks(friday):
    day = datetime.fromisoformat(friday).replace(tzinfo=NY)
    if day.weekday() != 4:
        raise ValueError('not_friday')
    sunday = day + timedelta(days=2)
    entry = sunday.replace(hour=17, minute=10)
    exit_at = entry + timedelta(hours=12)
    return {k: int(v.timestamp())*1000 for k, v in (
        ('friday_reference', day.replace(hour=17)),
        ('sunday_reference', sunday.replace(hour=17)), ('entry', entry), ('exit', exit_at))}


def mid(q):
    return (D(q['bid']) + D(q['ask']))/2


def entry_signal(friday_quote, sunday_quote, entry_quote, boundaries):
    """Eligibility deliberately has no exit quote or future-return argument."""
    if friday_quote is None or sunday_quote is None or entry_quote is None:
        return dict(status='missing_entry_inputs', primary_eligible=False, side=None)
    close_age = boundaries['friday_reference'] - friday_quote['time_msc']
    open_lag = sunday_quote['time_msc'] - boundaries['sunday_reference']
    entry_lag = entry_quote['time_msc'] - boundaries['entry']
    if not (0 <= close_age <= 300000 and 0 <= open_lag <= 300000 and 0 <= entry_lag <= 60000):
        return dict(status='late_or_outside_entry_quality', primary_eligible=False, side=None)
    gap = mid(sunday_quote) - mid(friday_quote)
    threshold = 3*(D(entry_quote['ask'])-D(entry_quote['bid']) + D(5)/CONTRACT + 2*SLIPPAGE['stress'])
    side = 'SELL' if gap > 0 else 'BUY' if gap < 0 else None
    return dict(status='eligible' if side and abs(gap) >= threshold else 'zero_gap' if side is None else 'cost_filtered',
                primary_eligible=bool(side and abs(gap) >= threshold), side=side,
                gap_price=str(gap), exante_threshold_price=str(threshold))


def net_component(side, entry_quote, exit_quote, scenario):
    if side not in ('BUY', 'SELL') or scenario not in SLIPPAGE:
        raise ValueError('invalid_component_direction_or_cost')
    model = CostModel.from_mapping(dict(version='r024-declared-'+scenario, spread_basis='bid_ask_embedded',
        commission_per_side_account='0', commission_per_side_per_quantity_account='2.5', minimum_fee_account='0',
        slippage_price_per_side=SLIPPAGE[scenario], financing_account='0', quote_to_account_rate='1',
        account_ccy='USD', rounding_decimals=2))
    costs = calculate_round_trip_cost(model, side, D(1), CONTRACT,
        D(entry_quote['bid']), D(entry_quote['ask']), D(exit_quote['bid']), D(exit_quote['ask']))
    net = D(str(costs['net_account']))
    return dict(side=side, net_usd_per_standard_lot=str(net),
                net_pips=str(net/CONTRACT/PIP),
                net_bps_on_entry_notional=str(net/CONTRACT/mid(entry_quote)*10000), costs=costs)


def event_result(row, quotes):
    boundaries = clocks(row['friday'])
    before, opened, entry, exit_at = (quotes.get(k) for k in ('close', 'open', 'entry', 'exit'))
    signal = entry_signal(before, opened, entry, boundaries)
    result = dict(friday=row['friday'], sunday=row['sunday'], clocks=boundaries, quotes=quotes,
                  signal=signal, outcome_status='not_applicable', outcomes={})
    if signal['side'] is None:
        return result
    # An unresolved future quote must not change ex-ante eligibility.
    if exit_at is None or not 0 <= exit_at['time_msc']-boundaries['exit'] <= 60000:
        result['outcome_status'] = 'missing_or_late_exit'
        return result
    if not before['sequence'] < opened['sequence'] <= entry['sequence'] < exit_at['sequence']:
        raise ValueError('component_source_quote_order')
    result['outcome_status'] = 'resolved'
    opposite = 'BUY' if signal['side'] == 'SELL' else 'SELL'
    for scenario in SLIPPAGE:
        result['outcomes'][scenario] = dict(fade=net_component(signal['side'], entry, exit_at, scenario),
                                            follow=net_component(opposite, entry, exit_at, scenario))
    return result


def collect_quotes(raw, endpoint_rows, expected_sha, expected_count, progress):
    """One source scan; decode only fixed endpoints and first quotes after targets."""
    selected = {row['friday']: {} for row in endpoint_rows}
    endpoints, pending = {}, []
    for row in endpoint_rows:
        for name in ('close', 'open'):
            e = row[name]
            if e is not None:
                endpoints[e['sequence']] = (row['friday'], name, e['time_msc'])
        for name in ('entry', 'exit'):
            when = clocks(row['friday'])[name]
            text = datetime.fromtimestamp(when/1000, timezone.utc).strftime('%Y%m%d %H:%M:%S.')+'000'
            pending.append((text.encode(), when, row['friday'], name))
    pending.sort()
    cursor, count, previous = 0, 0, None
    h = hashlib.sha256()
    rejected = []
    with Path(raw).open('rb') as stream:
        header = stream.readline(); h.update(header)
        if header.decode('utf-8-sig').strip() != 'DateTime,Bid,Ask,Volume':
            raise ValueError('raw_tick_header')
        for line in stream:
            h.update(line)
            if not line.strip():
                continue
            count += 1
            stamp = line[:21]
            if previous is not None and stamp < previous:
                raise ValueError('raw_timestamp_order')
            previous = stamp
            decoded = None
            if count in endpoints:
                day, name, when = endpoints[count]
                decoded = quote(line, count)
                if decoded['time_msc'] != when:
                    raise ValueError('admitted_endpoint_time_mismatch')
                selected[day][name] = decoded
            while cursor < len(pending) and stamp >= pending[cursor][0]:
                _, when, day, name = pending[cursor]
                if decoded is None:
                    decoded = quote(line, count)
                if decoded['time_msc']-when <= 60000:
                    selected[day][name] = decoded
                else:
                    rejected.append(dict(friday=day, event=name, first_later_quote=decoded))
                cursor += 1
            if count % 1000000 == 0:
                progress(count)
    if h.hexdigest() != expected_sha or count != expected_count:
        raise ValueError('raw_hash_or_count_mismatch')
    for row in endpoint_rows:
        for name in ('close', 'open'):
            if row[name] is not None and name not in selected[row['friday']]:
                raise ValueError('admitted_endpoint_missing')
    return selected, rejected


def summarize(events, year):
    result = []
    statuses = {}
    for e in events:
        key = e['signal']['status']
        statuses[key] = statuses.get(key, 0)+1
    for view, direction in (('primary_fade', 'fade'), ('primary_follow_control', 'follow'), ('secondary_ungated_fade', 'fade')):
        eligible = [e for e in events if e['signal']['side'] is not None and
                    (view.startswith('secondary') or e['signal']['primary_eligible'])]
        resolved = [e for e in eligible if e['outcome_status'] == 'resolved']
        for scenario in SLIPPAGE:
            values = [D(e['outcomes'][scenario][direction]['net_pips']) for e in resolved]
            bps = [D(e['outcomes'][scenario][direction]['net_bps_on_entry_notional']) for e in resolved]
            positive = sum((x for x in values if x > 0), D(0))
            result.append(dict(year=year, view=view, scenario=scenario, total_weekends=len(events),
                eligible_events=len(eligible), resolved_events=len(resolved), unresolved_events=len(eligible)-len(resolved),
                net_pips_sum=str(sum(values, D(0))) if values else None,
                net_pips_mean=str(sum(values, D(0))/len(values)) if values else None,
                net_bps_mean=str(sum(bps, D(0))/len(bps)) if bps else None,
                positive_events=sum(x > 0 for x in values), negative_events=sum(x < 0 for x in values),
                net_pips_min=str(min(values)) if values else None, net_pips_max=str(max(values)) if values else None,
                top3_positive_contribution_share=str(sum(sorted([x for x in values if x > 0], reverse=True)[:3], D(0))/positive) if positive else None,
                entry_statuses=statuses, expectancy_evidence='exposed_component_not_edge_or_account_PnL'))
    return result


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('source-root', 'admission-root', 'parent-root', 'protocol', 'fixtures', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    args = p.parse_args()
    bind_core(args.source_root)
    args.output.mkdir(exist_ok=False)
    began = time.perf_counter()
    def progress(phase, **more):
        if (args.output/'CANCEL').exists(): raise RuntimeError('cancelled')
        if time.perf_counter()-began > 300: raise TimeoutError('component deadline300s')
        packet = dict(phase=phase, wall_seconds=time.perf_counter()-began, **more)
        save(args.output/'progress.json', packet)
        with (args.output/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(packet)+'\n')
        print(json.dumps(packet), flush=True)
    try:
        fixtures = read(args.fixtures)
        if fixtures.get('status') != 'passed' or fixtures.get('component_sha256') != digest(Path(__file__)):
            raise ValueError('fixtures_not_bound_to_current_component')
        admission = read(args.admission_root/'result.json')
        oracle = read(args.admission_root/'oracle-result.json')
        oracle_manifest = read(args.admission_root/'oracle-manifest.json')
        if (admission['status'] != 'completed_endpoint_metadata_only'
                or oracle['status'] != '206raw_endpoints_and103adjacent_pairs_verified'
                or oracle_manifest['parent_result_sha256'] != digest(args.admission_root/'result.json')
                or [y['year'] for y in admission['years']] != list(YEARS)):
            raise ValueError('admission_scope_or_oracle_binding')
        pins = {str(path): digest(path) for path in [Path(__file__), Path(__file__).with_name('forex_study_batch.py'), args.protocol, args.fixtures,
            args.admission_root/'result.json', args.admission_root/'manifest.json',
            args.admission_root/'oracle-result.json', args.admission_root/'oracle-manifest.json']}
        for path, old_sha in read(args.admission_root/'manifest.json')['pins'].items():
            if digest(Path(path)) != old_sha:
                raise ValueError('admission_input_drift')
            pins[path] = old_sha
        for rel in ('trading_workspace_v2/semantics/data_costs.py', 'trading_workspace_v2/semantics/data_contracts.py',
                    'trading_workspace_v2/semantics/__init__.py', 'trading_workspace_v2/retained.py',
                    'trading_workspace_v2/replay_tick_execution.py', 'scripts/forex_h4_pilot.py'):
            path = args.source_root/rel; pins[str(path)] = digest(path)
        save(args.output/'manifest.json', dict(protocol_sha256=digest(args.protocol), source_root=str(args.source_root),
             pins=pins, years=list(YEARS), source_kind='consumed_QDM_ticks_not_target_broker',
             holdout_opened=False, broker_calls=0, model_calls=0, promotion_authorized=False))
        packets = []
        for year_info in admission['years']:
            year = year_info['year']
            seal = read(args.parent_root/str(year)/'raw-seal.json')
            if seal['dates'] != [f'{year}0101', f'{year}1231'] or seal['sha256'] != year_info['source_raw_sha256']:
                raise ValueError('parent_raw_scope')
            progress('collect_quotes', year=year)
            quotes, rejected = collect_quotes(seal['path'], year_info['endpoints'], seal['sha256'], year_info['ticks'],
                lambda n: progress('collect_quotes', year=year, rows=n))
            packet = dict(year=year, quotes=quotes, rejected_first_later_quotes=rejected)
            save(args.output/f'quotes-{year}.json', packet)
            packets.append((year_info, packet))
        events, summaries = [], []
        for info, packet in packets:
            progress('component_arithmetic', year=info['year'])
            rows = [event_result(r, packet['quotes'][r['friday']]) for r in info['endpoints']]
            events.append(dict(year=info['year'], events=rows))
            summaries.extend(summarize(rows, info['year']))
        if any(digest(Path(path)) != sha for path, sha in pins.items()):
            raise ValueError('pinned_source_or_input_drift')
        primary = [s for s in summaries if s['view'] == 'primary_fade']
        prioritized = all(s['resolved_events'] > 0 and not s['unresolved_events'] and D(s['net_pips_sum']) > 0 for s in primary)
        save(args.output/'result.json', dict(status='completed_price_component_only', years=events, summaries=summaries,
            original_priority_criterion=prioritized, wall_seconds=time.perf_counter()-began,
            flat_cash_baseline=dict(net_pips='0', costs='0', is_trading_strategy=False),
            equity_risk_and_prop_evaluated=False, broker_spec_verified=False, broker_calls=0, model_calls=0,
            holdout_opened=False, policy_implemented=False, promotion_authorized=False))
        progress('completed_price_component_only', prioritized=prioritized)
    except BaseException as error:
        save(args.output/'failure.json', dict(type=type(error).__name__, message=str(error)))
        progress('failed', error=str(error))
        raise


if __name__ == '__main__':
    main()
