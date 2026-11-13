"""Bounded B0 views from sealed QDM Bid/Ask ticks; no provider or broker IO."""
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import struct
import time
from zoneinfo import ZoneInfo

MINUTE = 60_000
HOLDOUT = 1_735_689_600_000
RECORD = struct.Struct('<qqii')  # UTC ms, original source ordinal, Bid/Ask grid units
LONDON = ZoneInfo('Europe/London')
PRICE = re.compile(r'[0-9]+\.[0-9]{5}\Z')
STAMP = re.compile(r'[0-9]{8} [0-9]{2}:[0-9]{2}:[0-9]{2}\.[0-9]{3}\Z')


def digest(path):
    with Path(path).open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def write_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def bounds(first, last):
    a = datetime.strptime(first, '%Y%m%d').replace(tzinfo=timezone.utc)
    b = datetime.strptime(last, '%Y%m%d').replace(tzinfo=timezone.utc) + timedelta(days=1)
    if a < datetime(2021, 11, 1, tzinfo=timezone.utc) or b.timestamp()*1000 > HOLDOUT or a >= b:
        raise ValueError('B0_source_window_not_authorized')
    return int(a.timestamp()*1000), int(b.timestamp()*1000)


def units(text):
    if not PRICE.fullmatch(text):
        raise ValueError('QDM_exact_five_decimal_grid_required')
    return int(text.replace('.', ''))


def seek_day(stream, first):
    """Locate the first admitted date without parsing prices outside the warmup."""
    stream.seek(0, 2)
    lo, hi = 0, stream.tell()
    target = first.encode('ascii')
    while hi-lo > 4096:
        mid = (lo+hi)//2
        stream.seek(mid)
        stream.readline()
        offset = stream.tell()
        line = stream.readline()
        if not line or line[:8] >= target:
            hi = mid
        else:
            lo = offset
    stream.seek(lo)
    while True:
        offset = stream.tell()
        line = stream.readline()
        if not line or line[:8] >= target:
            stream.seek(offset)
            return offset


def csv_rows(source):
    first, last = source['first_day'], source['last_day']
    start, end = bounds(first, last)
    count = 0
    previous = -1
    second_key = None
    with Path(source['path']).open('rb') as stream:
        if stream.readline().decode('utf-8-sig').strip() != 'DateTime,Bid,Ask,Volume':
            raise ValueError('QDM_header')
        if source.get('slice_from_annual'):
            seek_day(stream, first)
        for line in stream:
            row = line.decode('ascii').strip().split(',')
            if len(row) != 4 or not STAMP.fullmatch(row[0]):
                raise ValueError('QDM_row_schema')
            stamp, bid, ask, _ = row
            # Reject instead of reading forbidden next-year prices into a view.
            if not first <= stamp[:8] <= last:
                if source.get('slice_from_annual') and stamp[:8] > last:
                    break
                raise ValueError('QDM_date_outside_registration')
            if stamp[:17] != second_key:
                second_key = stamp[:17]
                second = int(datetime.fromisoformat(stamp[:8]+'T'+stamp[9:17]+'+00:00').timestamp())*1000
            at = second + int(stamp[18:])
            b, a = units(bid), units(ask)
            count += 1
            if not start <= at < end or at < previous or not 0 < b <= a:
                raise ValueError('QDM_time_order_or_quote')
            previous = at
            yield at, count, b, a


def prepared_rows(source):
    import pyarrow as pa
    import pyarrow.parquet as pq
    metadata = Path(source['prepared_metadata'])
    envelope = json.loads(metadata.read_bytes())
    p = envelope['payload']
    canonical = json.dumps(p, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode()
    # Native serialization uses sort_keys, UTF-8 and compact separators.
    if hashlib.sha256(canonical).hexdigest() != envelope['payload_sha256']:
        raise ValueError('prepared_payload_checksum')
    binding = p['binding']['input']
    if any(binding[k] != source[k] for k in ('sha256', 'first_day', 'last_day')):
        raise ValueError('prepared_source_binding')
    path = metadata.with_suffix('.parquet')
    if path.stat().st_size != p['bytes'] or digest(path) != p['sha256']:
        raise ValueError('prepared_content_checksum')
    start, end = bounds(source['first_day'], source['last_day'])
    count, previous, first = 0, -1, None
    with path.open('rb') as stream:
        table = pq.ParquetFile(stream, read_dictionary=['bid', 'ask'])
        schema = table.schema_arrow
        if (schema.names != ['time_msc', 'sequence', 'bid', 'ask']
                or schema.field('time_msc').type != pa.int64()
                or schema.field('sequence').type != pa.int64()
                or table.metadata.num_rows != p['ticks']):
            raise ValueError('prepared_schema_or_count')
        for batch in table.iter_batches(batch_size=65536, use_threads=False):
            if any(c.null_count for c in batch.columns):
                raise ValueError('prepared_null')
            bcol, acol = batch.column(2), batch.column(3)
            bids = [units(v) for v in bcol.dictionary.to_pylist()]
            asks = [units(v) for v in acol.dictionary.to_pylist()]
            for at, seq, bi, ai in zip(batch.column(0).to_pylist(), batch.column(1).to_pylist(),
                    bcol.indices.to_pylist(), acol.indices.to_pylist()):
                b, a = bids[bi], asks[ai]
                count += 1
                if seq != count or not start <= at < end or at < previous or not 0 < b <= a:
                    raise ValueError('prepared_order_grid_or_window')
                first = at if first is None else first
                previous = at
                yield at, seq, b, a
    if (count, first, previous) != (p['ticks'], p['first_time_msc'], p['last_time_msc']):
        raise ValueError('prepared_terminal_census')


def session(day):
    local = datetime.fromisoformat(day).replace(tzinfo=LONDON)
    return {h: int(local.replace(hour=h).timestamp()*1000) for h in (7, 8, 11, 12)}


def add_bar(views, at, bid, width):
    stamp = at//width*width
    bar = views.get(stamp)
    bit = 1 << ((at-stamp)//MINUTE)
    if bar is None:
        views[stamp] = [stamp, bid, bid, bid, bid, bit]
    else:
        if bid > bar[2]:
            bar[2] = bid
        if bid < bar[3]:
            bar[3] = bid
        bar[4] = bid
        bar[5] |= bit


def prepare(source, destination, event):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    binding = dict(source=source, decoder_sha256=digest(__file__))
    seal_path = destination/'seal.json'
    if seal_path.exists():
        seal = json.loads(seal_path.read_bytes())
        if seal['binding'] != binding:
            raise ValueError('B0_prepared_binding_changed')
        for row in seal['files']:
            if digest(destination/row['name']) != row['sha256']:
                raise ValueError('B0_prepared_tamper')
        event(stage='prepared_reused', partition=source['first_day'])
        return seal
    began, cpu = time.monotonic(), time.process_time()
    if digest(source['path']) != source['sha256']:
        raise ValueError('raw_source_hash_changed')
    m15, h1, current_day, output = {}, {}, None, None
    clocks = None
    files, days = [], []
    count = selected = 0
    previous = None
    max_gap = 0
    def finish_day():
        if output is not None:
            output.close()
            path = destination/(current_day+'.ticks')
            files.append(dict(name=path.name, sha256=digest(path), bytes=path.stat().st_size))
            days.append(current_day)
    try:
        reader = prepared_rows(source) if source.get('prepared_metadata') else csv_rows(source)
        for at, seq, bid, ask in reader:
            day = datetime.fromtimestamp(at//86_400_000*86400, timezone.utc).date().isoformat() if previous is None or at//86_400_000 != previous//86_400_000 else current_day
            if day != current_day:
                finish_day()
                current_day = day
                clocks = session(day)
                output = (destination/(day+'.ticks')).open('xb')
            add_bar(m15, at, bid, 15*MINUTE)
            add_bar(h1, at, bid, 60*MINUTE)
            if clocks[7] <= at < clocks[12]+5*MINUTE:
                output.write(RECORD.pack(at, seq, bid, ask))
                selected += 1
            if previous is not None:
                max_gap = max(max_gap, at-previous)
            previous = at
            count += 1
            if count % 1_000_000 == 0:
                event(stage='prepare_ticks', partition=source['first_day'], ticks=count,
                      wall_seconds=round(time.monotonic()-began, 2))
        finish_day()
        output = None
        bars = {label: [row[:5]+[row[5].bit_count()] for _, row in sorted(view.items())]
                for label, view in (('m15', m15), ('h1', h1))}
        write_json(destination/'bars.json', bars)
        files.append(dict(name='bars.json', sha256=digest(destination/'bars.json')))
        if digest(source['path']) != source['sha256']:
            raise ValueError('raw_source_changed_during_prepare')
        seal = dict(binding=binding, ticks=count, session_ticks=selected, days=days, files=files,
                    max_source_gap_ms=max_gap, wall_seconds=time.monotonic()-began,
                    cpu_seconds=time.process_time()-cpu, source_order_preserved=True)
        write_json(seal_path, seal)
        return seal
    finally:
        if output is not None and not output.closed:
            output.close()


def read_session(path):
    raw = Path(path).read_bytes()
    if len(raw) % RECORD.size:
        raise ValueError('B0_tick_record_truncated')
    rows = list(RECORD.iter_unpack(raw))
    if any(b[0] < a[0] or b[1] <= a[1] for a, b in zip(rows, rows[1:])):
        raise ValueError('B0_session_order')
    return rows
