"""Bounded stdlib decoder for a registered historical BI5 tick-hour fixture."""
import hashlib
import lzma
import math
import struct

HOUR=3_600_000


def decode_ticks(raw,*,hour_start,price_factor,compressed_cap=8*1024*1024,
                 uncompressed_cap=32*1024*1024,memory_cap=64*1024*1024):
    if (type(hour_start) is not int or hour_start<0 or hour_start%HOUR
            or hour_start+HOUR>1735689600000):
        raise ValueError('BI5_hour_or_holdout_closed')
    if type(price_factor) is not int or price_factor<=0:
        raise ValueError('explicit_BI5_price_factor_required')
    if any(type(x) is not int or x<=0 for x in [compressed_cap,uncompressed_cap,memory_cap]):
        raise ValueError('invalid_BI5_resource_cap')
    if not isinstance(raw,bytes) or not raw or len(raw)>compressed_cap:
        raise ValueError('empty_or_oversize_BI5_response')
    try:
        decoder=lzma.LZMADecompressor(format=lzma.FORMAT_ALONE,memlimit=memory_cap)
        plain=decoder.decompress(raw,max_length=uncompressed_cap+1)
    except lzma.LZMAError as error:
        raise ValueError('invalid_BI5_LZMA_or_memory_limit') from error
    if len(plain)>uncompressed_cap:
        raise ValueError('BI5_decompressed_size_cap')
    if not decoder.eof or decoder.unused_data:
        raise ValueError('BI5_truncated_or_trailing_stream')
    if len(plain)%20:
        raise ValueError('BI5_record_size')
    rows=[];previous=-1
    for offset,ask,bid,ask_volume,bid_volume in struct.iter_unpack('>iiiff',plain):
        if offset<0 or offset>=HOUR or offset<previous:
            raise ValueError('BI5_tick_offset_scope_or_order')
        if bid<=0 or ask<bid:
            raise ValueError('BI5_tick_price_or_spread')
        if any(not math.isfinite(v) or v<0 for v in [ask_volume,bid_volume]):
            raise ValueError('BI5_tick_volume')
        previous=offset
        rows.append(dict(timestamp=hour_start+offset,askPrice=ask/price_factor,bidPrice=bid/price_factor,
                         askVolume=ask_volume,bidVolume=bid_volume))
    return dict(rows=rows,record_count=len(rows),raw_sha256=hashlib.sha256(raw).hexdigest(),
        decompressed_sha256=hashlib.sha256(plain).hexdigest(),decompressed_bytes=len(plain),
        price_factor=price_factor,volume_units='provider_quote_millions_IEEE754_float32',
        layout='big_endian_3signed_int32_2float32',same_ms_ordinal_preserved=True)
