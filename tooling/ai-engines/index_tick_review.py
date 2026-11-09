"""Exact 0.001-grid archived index ticks; compact derived columns, never fills."""
from array import array
from bisect import bisect_left
from dataclasses import dataclass
from decimal import Decimal as D
import math

from candle_source_provenance import base_units, number

HOUR=3600000
MINUTE=60000
GRID=D('.001')
MAX_SAFE=2**53-1
HOLDOUT_START=1735689600000


@dataclass(frozen=True)
class TickColumns:
    start_msc: int
    end_msc: int
    timestamps: array
    bid_units: array
    ask_units: array
    bid_volumes_millions: array
    ask_volumes_millions: array

    def __len__(self):
        return len(self.timestamps)


def _safe_integer(value):
    if type(value) is not int or abs(value)>MAX_SAFE:
        raise ValueError('tick_safe_integer_required')
    return value


def _volume(value):
    if type(value) not in (int,float):
        raise ValueError('tick_numeric_volume_required')
    try:
        value=float(value)
    except OverflowError as exc:
        raise ValueError('tick_volume_overflow') from exc
    if not math.isfinite(value) or value<0:
        raise ValueError('tick_nonfinite_or_negative_volume')
    return value


def _observed_units(value):
    units=number(value)/GRID
    if units!=units.to_integral_value() or not 0<units<=MAX_SAFE:
        raise ValueError('native_tick_exact_grid_required')
    return int(units)


def decode(raw, *, start_msc, end_msc):
    if (type(start_msc) is not int or type(end_msc) is not int or start_msc<0
            or start_msc%HOUR or end_msc-start_msc!=HOUR or end_msc>HOLDOUT_START):
        raise ValueError('registered_index_tick_hour_holdout_closed')
    names=('times','bids','asks','bidVolumes','askVolumes')
    if type(raw) is not dict or not set((*names,'timestamp','multiplier','bid','ask'))<=raw.keys():
        raise ValueError('raw_tick_schema')
    columns=[raw[n] for n in names]
    if any(type(c) is not list for c in columns) or len({len(c) for c in columns})!=1:
        raise ValueError('raw_tick_column_shape')
    if (type(raw['timestamp']) is not int or raw['timestamp']!=start_msc
            or number(raw['multiplier'])!=GRID):
        raise ValueError('raw_tick_hour_or_grid')
    result=TickColumns(start_msc,end_msc,array('q'),array('q'),array('q'),array('d'),array('d'))
    if not columns[0]:
        return result
    bid,ask=(base_units(raw[n],GRID) for n in ('bid','ask'))
    _safe_integer(bid);_safe_integer(ask)
    stamp=start_msc
    for dt,db,da,bv,av in zip(*columns):
        dt,db,da=map(_safe_integer,(dt,db,da))
        if dt<0:
            raise ValueError('raw_tick_negative_time_delta')
        stamp+=dt;bid+=db;ask+=da
        _safe_integer(stamp);_safe_integer(bid);_safe_integer(ask)
        if not 0<bid<=ask:
            raise ValueError('raw_tick_crossed_or_nonpositive')
        # Match the pinned native Number division, including its float output.
        bv=_volume(bv)/1_000_000;av=_volume(av)/1_000_000
        if start_msc<=stamp<end_msc:
            result.timestamps.append(stamp);result.bid_units.append(bid);result.ask_units.append(ask)
            result.bid_volumes_millions.append(bv);result.ask_volumes_millions.append(av)
    return result


def inspect(native_rows, raw, *, start_msc, end_msc):
    result=decode(raw,start_msc=start_msc,end_msc=end_msc)
    if type(native_rows) is not list:
        raise ValueError('native_tick_rows_required')
    if len(native_rows)!=len(result):
        raise ValueError('native_tick_census')
    for i,row in enumerate(native_rows):
        if type(row) is not dict or not {'timestamp','bidPrice','askPrice','bidVolume','askVolume'}<=row.keys():
            raise ValueError('native_tick_schema')
        if type(row['timestamp']) is not int or row['timestamp']!=result.timestamps[i]:
            raise ValueError('native_tick_clock_or_order')
        if (_observed_units(row['bidPrice'])!=result.bid_units[i]
                or _observed_units(row['askPrice'])!=result.ask_units[i]):
            raise ValueError('native_tick_price_binding')
        if (_volume(row['bidVolume'])!=result.bid_volumes_millions[i]
                or _volume(row['askVolume'])!=result.ask_volumes_millions[i]):
            raise ValueError('native_tick_volume_binding')
    return result


def minute_ohlc(ticks):
    """Independent side OHLC in integer price units; absent minutes stay absent."""
    result={}
    for at,bid,ask in zip(ticks.timestamps,ticks.bid_units,ticks.ask_units):
        minute=at//MINUTE*MINUTE
        if minute not in result:
            result[minute]={'bid':[bid,bid,bid,bid],'ask':[ask,ask,ask,ask]}
            continue
        for side,price in (('bid',bid),('ask',ask)):
            bar=result[minute][side]
            if price>bar[1]:bar[1]=price
            if price<bar[2]:bar[2]=price
            bar[3]=price
    return {at:{side:dict(zip(('open','high','low','close'),values)) for side,values in pair.items()}
            for at,pair in result.items()}


def first_quote(ticks, target_msc):
    if type(target_msc) is not int or not ticks.start_msc<=target_msc<ticks.end_msc:
        raise ValueError('quote_locator_outside_source_hour')
    index=bisect_left(ticks.timestamps,target_msc)
    if index==len(ticks):
        return None
    return dict(source_ordinal=index,timestamp=ticks.timestamps[index],wait_ms=ticks.timestamps[index]-target_msc,
        bid_units=ticks.bid_units[index],ask_units=ticks.ask_units[index],
        bid_volume_millions=ticks.bid_volumes_millions[index],ask_volume_millions=ticks.ask_volumes_millions[index])
