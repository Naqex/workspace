"""Census the sealed native archive and materialize only the permitted price partition."""

from collections import Counter
from datetime import datetime, timezone
from hashlib import file_digest
import json
from pathlib import Path
import sys

import numpy as np
import pyarrow.parquet as pq


ASSETS = ('US500.cash', 'EURUSD', 'USDJPY', 'EURJPY', 'GBPUSD', 'XAUUSD')
FRAMES = {'H1': 3600, 'H4': 14400, 'D1': 86400}
CLOCK = 'bar_open_server_seconds'
ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / 'planning/research/FTMO-DEMO-10K-STANDARD-FULL13-AND-EXECUTION-20261119.json'
PROTOCOL = ROOT / 'planning/research/BOTTLENECK2-MULTI-ASSET-MONFRI-PROTOCOL-20261119.md'
ARCHIVE_PIN = '958efae21180c0dfc2654de3ecc447effb88e0ddc12eb63e30aca894c6980f1c'
HOLD_DATE = '2025-01-01'
START = int(datetime(2018, 1, 1, tzinfo=timezone.utc).timestamp())
STOP = int(datetime(2025, 1, 1, tzinfo=timezone.utc).timestamp())


def sha(path):
    with path.open('rb') as stream:
        return file_digest(stream, 'sha256').hexdigest()


def read(path):
    return json.loads(path.read_text(encoding='utf-8-sig'))


def write(path, value):
    with path.open('x', encoding='utf-8', newline='\n') as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')


def label(t):
    return datetime.fromtimestamp(int(t), timezone.utc).isoformat(timespec='seconds').removesuffix('+00:00')


def utc_years(values):
    return (values.astype('datetime64[s]').astype('datetime64[Y]').astype(int) + 1970)


def run(archive, destination):
    manifest_path = archive / 'manifest.json'
    if sha(manifest_path) != ARCHIVE_PIN:
        raise ValueError('audit archive manifest mismatch')
    manifest = read(manifest_path)
    audit = read(AUDIT)
    destination.mkdir(exist_ok=False)
    development = destination / 'development'
    development.mkdir()
    records = {}
    for asset, row in audit['symbols'].items():
        records[asset] = {}
        for frame, meta in row['history'].items():
            source = archive / meta['parquet']
            upstream_sha = manifest['files'][meta['parquet']]['sha256']
            if upstream_sha != meta['sha256'] or sha(source) != upstream_sha:
                raise ValueError(f'audit archive drift: {asset} {frame}')
            dates = pq.read_table(source, columns=[CLOCK])[CLOCK].to_numpy()
            if len(dates) != meta['bars'] or np.any(np.diff(dates) <= 0):
                raise ValueError(f'invalid times: {asset} {frame}')
            years = utc_years(dates)
            gaps = []
            threshold = {'H1': 3 * 3600, 'H4': 12 * 3600, 'D1': 36 * 3600}[frame]
            gap_classes = Counter()
            for i in np.flatnonzero(np.diff(dates) > threshold):
                left, right = map(int, dates[i:i + 2])
                before, after = (datetime.fromtimestamp(t, timezone.utc) for t in (left, right))
                weekend = before.weekday() >= 4 and after.weekday() <= 1 and (after.date() - before.date()).days <= 3
                holiday = any((d.month, d.day) in {(12, 24), (12, 25), (12, 26), (12, 31), (1, 1), (1, 2)} for d in (before, after))
                kind = 'COMMON_HOLIDAY_ADJACENT_UNCERTIFIED' if holiday else 'WEEKEND_PATTERN' if weekend else 'UNEXPLAINED_OR_OTHER_HOLIDAY'
                gap_classes[kind] += 1
                if kind != 'WEEKEND_PATTERN':
                    gaps.append(dict(after=label(left), before=label(right), hours=(right-left)/3600, kind=kind))
            split = int(np.searchsorted(dates, STOP))
            record = dict(total=len(dates), first=label(dates[0]), last=label(dates[-1]),
                          source_sha256=upstream_sha, counts_by_year={str(y): int(n) for y, n in Counter(years).items()},
                          gap_threshold_hours=threshold/3600, gap_counts=dict(gap_classes), non_weekend_gaps=gaps,
                          locked_holdout_rows=len(dates)-split, locked_interval_indices=[split, len(dates)],
                          locked_first=label(dates[split]) if split < len(dates) else None)
            if asset in ASSETS:
                # Push the clock predicate into Parquet before making any price values available to the screen.
                price = pq.read_table(source, columns=[CLOCK, 'open', 'high', 'low', 'close'], filters=[(CLOCK, '<', STOP)])
                if not np.array_equal(price[CLOCK].to_numpy(), dates[:split]):
                    raise ValueError('development partition does not match sealed clock prefix')
                path = development / f'{asset}-{frame}.parquet'
                pq.write_table(price, path, compression='zstd')
                record.update(development_file=path.name, development_sha256=sha(path), development_rows=split)
            records[asset][frame] = record
    if sum(x['total'] for a in records.values() for x in a.values()) != 1740707:
        raise ValueError('39-series census mismatch')
    common = {str(y): {a: {f: records[a][f]['counts_by_year'].get(str(y), 0) for f in FRAMES}
                      for a in ASSETS} for y in range(2017, 2027)}
    exposure = {
        'EURUSD': 'Previously exposed in research, including later-period research. Native ATR also previously viewed.',
        'US500.cash': 'US500 research and later-period exposure recorded. Native ATR also previously viewed.',
        'XAUUSD': 'Gold research and later-period exposure recorded. Native ATR also previously viewed.',
        'GBPUSD': 'Prior S01/F5/FX research. Exact native holdout strategy PnL not established. Native ATR previously viewed.',
        'USDJPY': 'Prior R084/R085 Tokyo research. This new native PnL path is sealed. Native ATR previously viewed.',
        'EURJPY': 'No previous strategy result found in research index. Native ATR previously viewed.'}
    write(destination / 'CLOCK_CENSUS.json', dict(clock='platform wall time', series=records, six_asset_overlap=common))
    compact = {a: {f: {k: v for k, v in r.items() if k not in ('non_weekend_gaps', 'gap_counts', 'counts_by_year')}
                   for f, r in frames.items()} for a, frames in records.items()}
    path = destination / 'NATIVE_FTMO_HOLDOUT_LOCK.json'
    write(path, dict(schema='native-ftmo-partition-lock-v1', sealed_at_utc=datetime.now(timezone.utc).isoformat(),
                     status='LOCKED_HOLDOUT', cutoff_server=HOLD_DATE, dev_years=[2018, 2024], clusters=[[2018, 2020], [2021, 2024]],
                     archive_manifest_sha256=ARCHIVE_PIN, audit_sha256=sha(AUDIT), protocol_sha256=sha(PROTOCOL),
                     census_sha256=sha(destination / 'CLOCK_CENSUS.json'), series=compact, exposure=exposure,
                     previous_exposure='All 13 native symbols had aggregate ATR exposure at 36f1535. Access lock is prospective, with no fresh blind OOS claim.',
                     pre_seal_scope='clock-only census across full dataset, immutable source file hashes, price-only Development copies'))
    (destination / 'NATIVE_FTMO_HOLDOUT_LOCK.sha256').write_text(f'{sha(path)}  {path.name}\n', encoding='ascii')
    print('Sealed before research', sha(path))


if __name__ == '__main__':
    run(*map(Path, sys.argv[1:]))
