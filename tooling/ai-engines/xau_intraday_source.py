"""Admitted Gold views and frozen A0 signals; no pricing outside 2021seed/2022-24."""
from array import array
from bisect import bisect_left
from collections import deque, Counter
from datetime import datetime, timezone
from decimal import Decimal as D
import json
from pathlib import Path
import sys

from eurusd_b0 import features, natural_stop
from eurusd_b0_source import digest, write_json, MINUTE

RAW_SHA = 'd209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9'
START = 1635724800000
END = 1735689600000
HOUR = 3600000


def source_views(cache, corrections=None, *, end_msc=END):
    if type(end_msc) is not int or not START<end_msc<=END:
        raise ValueError('XAU_source_scope_or_holdout')
    cache = Path(cache)
    manifest = json.loads((cache/'manifest.json').read_bytes())
    if manifest['raw_sha256'] != RAW_SHA or manifest['scope_end_exclusive'] != END//1000:
        raise ValueError('XAU_unadmitted_source_or_holdout')
    patches={}
    if corrections is not None:
        from index_tick_review import decode,minute_ohlc
        packet=json.loads(Path(corrections).read_bytes())
        if packet['schema']!='XAU-A0-observed-tick-M1-corrections-v1':raise ValueError('unregistered_M1_corrections')
        for patch in packet['patches']:
            at=patch['at'];hour=at//HOUR*HOUR
            if not START<=at<end_msc or at%MINUTE or at in patches:raise ValueError('correction_clock_or_holdout')
            if digest(patch['raw_path'])!=patch['raw_sha256']:raise ValueError('correction_raw_binding')
            observed=minute_ohlc(decode(json.loads(Path(patch['raw_path']).read_bytes()),start_msc=hour,end_msc=hour+HOUR))
            if [observed[at]['bid'][key] for key in ('open','high','low','close')]!=patch['corrected']:
                raise ValueError('correction_not_native_observed_ohlc')
            patches[at]=patch
    times = array('q')
    if digest(cache/'times.bin') != manifest['files']['times.bin']:
        raise ValueError('XAU_timestamp_hash')
    with (cache/'times.bin').open('rb') as f:
        times.fromfile(f, manifest['rows'])
    if sys.byteorder != manifest['byteorder']:
        times.byteswap()
    lo, hi = bisect_left(times, START//1000), bisect_left(times, end_msc//1000)
    prices = []
    for name in ('o', 'h', 'l', 'c'):
        if digest(cache/(name+'.bin')) != manifest['files'][name+'.bin']:
            raise ValueError('XAU_price_hash')
        values = array('i')
        with (cache/(name+'.bin')).open('rb') as f:
            f.seek(lo*4)
            values.fromfile(f, hi-lo)
        if sys.byteorder != manifest['byteorder']:
            values.byteswap()
        prices.append(values)
    minutes, m15, h1 = {}, {}, {}
    previous = -1;applied=set()
    for at, o, h, l, c in zip(times[lo:hi], *prices):
        at *= 1000
        if at in patches:
            p=patches[at]
            if [o,h,l,c]!=p['original']:raise ValueError('correction_original_not_equal')
            o,h,l,c=p['corrected']
            applied.add(at)
        if not START <= at < end_msc or at <= previous or at % MINUTE or not 0 < l <= min(o,c) <= max(o,c) <= h:
            raise ValueError('XAU_M1_schema')
        previous = at
        minutes[at] = [o,h,l,c]
        for view, width in ((m15, 15*MINUTE), (h1, HOUR)):
            stamp = at//width*width
            bit = 1 << ((at-stamp)//MINUTE)
            if stamp not in view:
                view[stamp] = [stamp,o,h,l,c,bit]
            else:
                r = view[stamp]
                r[2], r[3], r[4], r[5] = max(r[2],h), min(r[3],l), c, r[5]|bit
    if applied!=set(patches):raise ValueError('unapplied_M1_correction')
    views = {name:[r[:5]+[r[5].bit_count()] for _,r in sorted(v.items())] for name,v in (('m15',m15),('h1',h1))}
    return minutes, views


def signal_features(views):
    f = features(views['m15'], views['h1'])
    closes = deque(maxlen=20)
    previous = None
    for row in views['m15']:
        if row[5] != 15:
            continue
        at = row[0]+15*MINUTE
        f[at]['ma_before'] = sum(closes)/20 if len(closes) == 20 else None
        f[at]['previous_close'] = previous[4] if previous is not None and previous[0]+15*MINUTE == row[0] else None
        closes.append(D(row[4]))
        previous = row
    return f


def signal(f, at):
    stamp, o, h, l, c, _ = f['bar']
    if (f['bias'] is None or f['atr_before'] is None or f['ma_before'] is None
            or f['previous_close'] is None or not 9*HOUR < at % 86400000 < 16*HOUR or stamp % 86400000 < 9*HOUR):
        return None
    ma, atr = f['ma_before'], f['atr_before']
    lower, upper = ma-atr/D(5), ma+atr/D(5)
    touch = D(l) <= upper and D(h) >= lower
    side = f['bias']
    confirm = (f['previous_close'] > upper and D(c) > upper if side == 'BUY'
               else f['previous_close'] < lower and D(c) < lower)
    if not touch or not confirm:
        return None
    return dict(decision_msc=at, side=side, stop_units=natural_stop(side,l,h,atr/D(10)),
                atr_units=str(atr), ma_units=str(ma), bar_units=[o,h,l,c],
                day=datetime.fromtimestamp(at/1000,timezone.utc).date().isoformat())


def prepare(cache, output, corrections=None):
    output = Path(output)
    output.mkdir(parents=True,exist_ok=False)
    minutes, views = source_views(cache,corrections)
    f = signal_features(views)
    candidates, yearly, hours = [], {}, set()
    for year in (2022,2023,2024):
        counts = Counter()
        days, full, directional_hours = set(), Counter(), set()
        for at, feature in f.items():
            day = datetime.fromtimestamp(at/1000,timezone.utc)
            if day.year != year or day.weekday() >= 5 or feature['bar'][0]%86400000 < 9*HOUR or not 9*HOUR < at%86400000 < 16*HOUR:
                continue
            days.add(day.date().isoformat())
            full[day.date().isoformat()] += 1
            counts['admitted_m15_bars'] += 1
            if feature['bias'] is not None:
                counts['directional_m15_bars'] += 1
                directional_hours.add(at//HOUR*HOUR)
            result = signal(feature,at)
            if result:
                candidates.append(result)
                counts['raw_signals'] += 1
                start = at//HOUR*HOUR
                hours.update(start+i*HOUR for i in range(3))
        yearly[year] = dict(counts, source_valid_days=len(days), full_27bar_days=sum(n==27 for n in full.values()),
                            directional_h1_hours=len(directional_hours))
    write_json(output/'views.json',views)
    write_json(output/'candidates.json',candidates)
    packet=dict(schema='XAU-A0-signal-census-v1',yearly=yearly,hours=sorted(hours),
                source_manifest_sha256=digest(Path(cache)/'manifest.json'),signals_sha256=digest(output/'candidates.json'),
                views_sha256=digest(output/'views.json'),source_code_sha256=digest(__file__),
                source_cache=str(cache),corrections_sha256=digest(corrections) if corrections else None,
                PnL_computed=False,prices2025_2026_opened=False)
    write_json(output/'census.json',packet)
    print(json.dumps(dict(yearly=yearly,tick_hours=len(hours))),flush=True)
    return packet


if __name__ == '__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--cache',required=True);p.add_argument('--output',required=True)
    p.add_argument('--corrections');a=p.parse_args();prepare(a.cache,a.output,a.corrections)
