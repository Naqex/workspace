"""Identify explicit candles versus padding in pinned Dukascopy JSON responses.

The native decoder expands omitted minutes with carried-close/zero-volume rows.
Keep those historical exports intact; only an explicitly bound source bar may
be treated as a price observation in a new source-only view.
"""
from decimal import Decimal as D, ROUND_HALF_UP
from bisect import bisect_right


PRICE_KEYS=('open','high','low','close')


def number(value):
    if type(value) not in (int,float):
        raise ValueError('source_number_type')
    result=D(str(value))
    if not result.is_finite():
        raise ValueError('source_number_nonfinite')
    return result


def integer(value):
    result=number(value)
    if result!=result.to_integral_value():
        raise ValueError('source_integer_required')
    return int(result)


def base_units(value,grid):
    units=number(value)/grid
    nearest=units.to_integral_value(rounding=ROUND_HALF_UP)
    # Raw JSON can contain 384.43600000000004 for the 384.436 base price.
    # Match native integer-unit normalization only within floating-point noise.
    if nearest<=0 or abs(units-nearest)>D('1e-7'):
        raise ValueError('source_base_price_grid')
    return int(nearest)


def explicit_candles(payload, *, duration_ms=60000):
    """Decode source-listed candles; H1 is explicit opt-in, M1 remains default."""
    if type(duration_ms) is not int or duration_ms not in (60000,3600000):
        raise ValueError('source_registered_duration_required')
    if not isinstance(payload,dict):
        raise ValueError('source_object_required')
    stamp,shift=integer(payload['timestamp']),integer(payload['shift'])
    grid=number(payload['multiplier'])
    if stamp<0 or stamp%duration_ms or shift!=duration_ms or grid<=0:
        raise ValueError('source_M1_clock_or_grid')
    columns=[payload[name] for name in ['times','opens','highs','lows','closes','volumes']]
    if any(not isinstance(column,list) for column in columns) or len({len(c) for c in columns})!=1:
        raise ValueError('source_column_shape')
    if not columns[0]:
        return {}
    units={}
    for key in PRICE_KEYS:
        units[key]=base_units(payload[key],grid)
    result={}
    for index,step in enumerate(payload['times']):
        delta=integer(step)
        if delta<0 or (index>0 and delta==0):
            raise ValueError('source_timestamp_order')
        stamp+=delta*shift
        row=dict(timestamp=stamp)
        for key in PRICE_KEYS:
            units[key]+=integer(payload[key+'s'][index])
            row[key]=D(units[key])*grid
        row['volume']=number(payload['volumes'][index])
        if (min(row[k] for k in PRICE_KEYS)<=0 or row['volume']<0
                or row['low']>min(row['open'],row['close'])
                or row['high']<max(row['open'],row['close'])):
            raise ValueError('source_candle_bounds')
        result[stamp]=row
    return result


def inspect_expansion(payload,native_rows, *, require_complete=True):
    """Bind the full unfiltered native view, returning original explicit rows.

    Input volumes are in the provider's native millions unit. Unknown/missing
    source or an already filtered export is an error, not permission to guess
    provenance from flat price or zero volume.
    """
    if type(require_complete) is not bool:
        raise ValueError('source_complete_mode_must_be_boolean')
    explicit=explicit_candles(payload)
    if not explicit:
        if native_rows:
            raise ValueError('native_rows_without_explicit_source')
        return dict(explicit_rows=[],padding_stamps=[],native_rows=0,unrepresented_explicit_rows=0)
    first,last=integer(payload['timestamp']),max(explicit)
    if require_complete and len(native_rows)!=(last-first)//60000+1:
        raise ValueError('full_unfiltered_native_expansion_required')
    grid=number(payload['multiplier'])
    base_close=D(base_units(payload['close'],grid))*grid
    source_stamps=sorted(explicit)
    kept,padding=[],[]
    previous_stamp=first-60000
    for index,row in enumerate(native_rows):
        stamp=integer(row['timestamp'])
        if (not first<=stamp<=last or stamp%60000 or stamp<=previous_stamp
                or (require_complete and stamp!=first+index*60000)):
            raise ValueError('native_expansion_clock')
        previous_stamp=stamp
        source=explicit.get(stamp)
        if source is None:
            at=bisect_right(source_stamps,stamp)-1
            previous=explicit[source_stamps[at]]['close'] if at>=0 else base_close
            if number(row['volume'])!=0 or any(number(row[k])!=previous for k in PRICE_KEYS):
                raise ValueError('padding_price_or_volume_binding')
            padding.append(stamp)
        else:
            if any(number(row[k])!=source[k] for k in [*PRICE_KEYS,'volume']):
                raise ValueError('explicit_source_price_or_volume_binding')
            kept.append(row)
    if require_complete and len(kept)!=len(explicit):
        raise ValueError('explicit_source_count')
    return dict(explicit_rows=kept,padding_stamps=padding,native_rows=len(native_rows),
                unrepresented_explicit_rows=len(explicit)-len(kept))
