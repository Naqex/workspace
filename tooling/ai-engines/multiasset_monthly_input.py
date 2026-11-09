"""Small source observations for registered multiasset research, never order authority."""
from datetime import datetime, timezone
from decimal import Decimal as D
import hashlib
from pathlib import Path
from zoneinfo import ZoneInfo

GRIDS = {'EURUSD': D('.00001'), 'XAUUSD': D('.001'), 'US500': D('.001')}
UNITS = {'EURUSD': 'USD_per_EUR', 'XAUUSD': 'USD_per_troy_ounce', 'US500': 'USD_per_index_point'}


def schedules(sessions):
    grouped = {}
    for day, stamps in sorted(sessions.items()):
        year = int(day[:4])
        if not 2013 <= year <= 2024:
            raise ValueError('monthly_input_holdout_scope')
        grouped.setdefault(day[:7], []).append((day, stamps))
    result = []
    for month, days in sorted(grouped.items()):
        first, last = days[0], days[-1]
        opened = datetime.fromisoformat(first[0]).replace(hour=10, tzinfo=ZoneInfo('America/New_York'))
        result.extend([dict(month=month, role='rebalance_observation', target_ms=int(opened.timestamp()*1000)),
                       dict(month=month, role='signal_close', target_ms=last[1][-1]+60000)])
    return result


def number(value, grid):
    if isinstance(value, bool):
        raise ValueError('price_boolean')
    result = D(str(value))
    if not result.is_finite() or result <= 0 or result % grid:
        raise ValueError('price_positive_grid')
    return result


def record(instrument, spec, point, *, basis):
    if instrument not in GRIDS or spec['role'] not in ('signal_close', 'rebalance_observation'):
        raise ValueError('monthly_input_kind')
    target = spec['target_ms']
    if type(target) is not int or basis not in ('observed_tick','source_M1_bid_ask','source_M1_bid_only'):
        raise ValueError('monthly_input_time_or_basis')
    value = dict(schema='multiasset-monthly-observation-v1', instrument=instrument, **spec,
                 quote_currency='USD', price_unit=UNITS[instrument], data_role='historical_source_observation',
                 exposure='previously_consumed', clean_oos=False, observation_basis=basis,
                 status='missing_or_stale', bid=None, ask=None, observed_ask=False,
                 execution_authorized=False, executable_tick_proven=False)
    if point is None:
        return value
    if type(target) is not int or type(point['time_ms']) is not int:
        raise ValueError('integer_timestamp_required')
    signal = spec['role']=='signal_close'
    if basis=='observed_tick':
        at = point['time_ms']
        valid = 0 < target-at <= 60000 if signal else 0 <= at-target <= 60000
        value.update(known_at_ms=target if signal else at, quote_time_ms=at,
                     observation_age_or_lag_ms=target-at if signal else at-target)
    elif basis=='source_M1_bid_ask' or basis=='source_M1_bid_only':
        at = point['time_ms']
        valid = at == target-60000 if signal else at == target
        value.update(source_bar_open_ms=at, known_at_upper_bound_ms=at+60000,
                     quote_timestamp_interval_ms=[at,at+60000], observation_age_or_lag_ms=target-at if signal else None)
    else:
        raise ValueError('unregistered_price_basis')
    bid = number(point['bid'], GRIDS[instrument])
    ask = number(point['ask'], GRIDS[instrument]) if point.get('ask') is not None else None
    if ask is not None and ask < bid:
        raise ValueError('negative_spread')
    if (instrument=='XAUUSD' and ask is not None) or (instrument!='XAUUSD' and ask is None):
        raise ValueError('observed_side_contract')
    if not valid:
        value['rejected_observation'] = dict(time_ms=at, bid=str(bid), ask=str(ask) if ask is not None else None)
        return value
    value.update(status='observed_bid_only' if ask is None else 'observed_bid_ask',
                 bid=str(bid), ask=str(ask) if ask is not None else None, observed_ask=ask is not None)
    return value


def tick_quote(line, sequence):
    stamp, bid, ask, _ = line.decode('utf8').strip().split(',')
    at = datetime.strptime(stamp, '%Y%m%d %H:%M:%S.%f').replace(tzinfo=timezone.utc)
    return dict(time_ms=int(at.timestamp())*1000+at.microsecond//1000, bid=bid, ask=ask, sequence=sequence)


def sparse_ticks(path, expected_sha, specs, *, first_day, last_day, expected_count, progress=None):
    if not ('20130101' <= first_day <= last_day <= '20241231'):
        raise ValueError('raw_tick_holdout_scope')
    targets = sorted((datetime.fromtimestamp(s['target_ms']/1000, timezone.utc).strftime('%Y%m%d %H:%M:%S.%f')[:-3].encode(), i, s)
                     for i,s in enumerate(specs))
    if len({t for t,_,_ in targets}) != len(targets):
        raise ValueError('duplicate_targets')
    result, proofs = {}, []
    count = cursor = 0
    previous = previous_stamp = None
    checksum = hashlib.sha256()
    with Path(path).open('rb') as stream:
        header = stream.readline(); checksum.update(header)
        if header.decode('utf-8-sig').strip()!='DateTime,Bid,Ask,Volume':
            raise ValueError('tick_header')
        for line in stream:
            checksum.update(line)
            if not line.strip():
                continue
            stamp=line[:21];count+=1
            if (len(stamp)!=21 or not first_day.encode()<=stamp[:8]<=last_day.encode()
                    or previous_stamp is not None and stamp<previous_stamp):
                raise ValueError('raw_tick_scope_or_order')
            while cursor<len(targets) and stamp>=targets[cursor][0]:
                _, index, spec=targets[cursor]
                selected=previous if spec['role']=='signal_close' else line
                sequence=count-1 if spec['role']=='signal_close' else count
                point=tick_quote(selected,sequence) if selected is not None else None
                result[index]=record('EURUSD',spec,point,basis='observed_tick')
                result[index]['source_sequence']=sequence if point else None
                proofs.append(dict(index=index,selected_sequence=sequence if point else None,
                    previous_time_ms=tick_quote(previous,count-1)['time_ms'] if previous else None,
                    next_time_ms=tick_quote(line,count)['time_ms']))
                cursor+=1
            previous,previous_stamp=line,stamp
            if progress and count%1000000==0:
                progress(count)
    for _,index,spec in targets[cursor:]:
        point=tick_quote(previous,count) if previous is not None and spec['role']=='signal_close' else None
        result[index]=record('EURUSD',spec,point,basis='observed_tick')
        result[index]['source_sequence']=count if point else None
        proofs.append(dict(index=index,selected_sequence=count if point else None,at_eof=True))
    if checksum.hexdigest()!=expected_sha or count!=expected_count:
        raise ValueError('raw_tick_hash_or_census')
    return [result[i] for i in range(len(specs))], dict(raw_sha256=expected_sha,raw_rows=count,selection_proofs=proofs)
