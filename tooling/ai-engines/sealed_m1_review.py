"""Review a sealed quarterly M1 Bid/Ask download without repairing its data."""
from __future__ import annotations

import argparse
from datetime import date, datetime, time, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import statistics
import time as timer
from zoneinfo import ZoneInfo


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def cash_sessions(calendar: dict) -> dict[str, list[int]]:
    if calendar['schema'] != 'cash-session-calendar-v1':
        raise ValueError('calendar_schema')
    year = calendar['year']
    zone = ZoneInfo(calendar['timezone'])
    holidays = {date.fromisoformat(d) for d in calendar['holidays']}
    early = {date.fromisoformat(d): time.fromisoformat(t)
             for d, t in calendar['early_closes'].items()}
    if any(d.year != year or d.weekday() >= 5 for d in holidays | early.keys()):
        raise ValueError('calendar_date_scope')
    if holidays & early.keys():
        raise ValueError('holiday_early_close_conflict')
    result = {}
    day = date(year, 1, 1)
    while day.year == year:
        if day.weekday() < 5 and day not in holidays:
            start = datetime.combine(day, time.fromisoformat(calendar['open']), zone)
            stop = datetime.combine(day, early.get(day, time.fromisoformat(calendar['close'])), zone)
            if stop <= start:
                raise ValueError('calendar_session_order')
            result[day.isoformat()] = list(range(int(start.timestamp()*1000),
                                                int(stop.timestamp()*1000), 60000))
        day += timedelta(days=1)
    return result


def validate_rows(rows: list, lower: int, upper: int, grid: float) -> None:
    if not rows or not math.isfinite(grid) or grid <= 0:
        raise ValueError('empty_rows_or_invalid_grid')
    previous = -1
    for row in rows:
        stamp = row['timestamp']
        prices = [row[k] for k in ('open', 'high', 'low', 'close')]
        if (type(stamp) is not int or stamp % 60000 or not lower <= stamp < upper
                or stamp <= previous):
            raise ValueError('timestamp_scope_grid_or_order')
        if any(type(v) not in (int, float) or not math.isfinite(v) or v <= 0
               or abs(v/grid-round(v/grid)) > 1e-7 for v in prices):
            raise ValueError('price_finite_positive_or_grid')
        if row['low'] > min(row['open'], row['close']) or row['high'] < max(row['open'], row['close']):
            raise ValueError('ohlc_bounds')
        volume = row['volume']
        if type(volume) not in (int, float) or not math.isfinite(volume) or volume < 0:
            raise ValueError('volume_finite_nonnegative')
        previous = stamp


def paired_spreads(bid: list, ask: list) -> list[float]:
    if len(bid) != len(ask):
        raise ValueError('side_alignment')
    spreads = []
    for b, a in zip(bid, ask):
        if b['timestamp'] != a['timestamp']:
            raise ValueError('side_alignment')
        # Independent side highs/lows are not synchronous spread observations.
        for key in ('open', 'close'):
            spread = a[key]-b[key]
            if spread < -1e-9:
                raise ValueError('negative_endpoint_spread')
            spreads.append(max(0.0, spread))
    return spreads


def review(root: Path, calendar_path: Path, grid: float) -> dict:
    began = timer.perf_counter()
    calendar = json.loads(calendar_path.read_text(encoding='utf-8'))
    sessions = cash_sessions(calendar)
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
    download = json.loads((root/'result.json').read_text(encoding='utf-8'))
    if (download['status'] != 'downloaded_verified_M1_sides_needs_calendar_review'
            or download['strategySimulated'] is not False or download['holdoutRead'] is not False
            or download['brokerCalls'] != 0 or download['modelCalls'] != 0):
        raise ValueError('unexpected_download_scope_or_state')
    year = calendar['year']
    seals, stamps, spreads, row_count = [], set(), [], 0
    if len(download['requests']) != 8 or len(manifest['requests']) != 8:
        raise ValueError('quarter_count')
    instrument = None
    for q in range(1, 5):
        lower_dt = datetime(year, 3*(q-1)+1, 1, tzinfo=timezone.utc)
        upper_dt = datetime(year+1, 1, 1, tzinfo=timezone.utc) if q == 4 else datetime(year, 3*q+1, 1, tzinfo=timezone.utc)
        sides = []
        for side in ('bid', 'ask'):
            index = 2*(q-1)+(side == 'ask')
            stem = f'q{q}-{side}'
            path = root/f'{stem}.json'
            seal = json.loads((root/f'{stem}-seal.json').read_text(encoding='utf-8'))
            if seal != download['requests'][index] or seal['request'] != stem or digest(path) != seal['sha256']:
                raise ValueError('seal_binding')
            request = manifest['requests'][index]
            if request.get('ignoreFlats') is not False:
                raise ValueError('explicit_unfiltered_provider_bars_required')
            dates = request['dates']
            if (request['timeframe'] != 'm1' or request['priceType'] != side
                    or datetime.fromisoformat(dates['from'].replace('Z', '+00:00')) != lower_dt
                    or datetime.fromisoformat(dates['to'].replace('Z', '+00:00')) != upper_dt):
                raise ValueError('request_scope')
            instrument = instrument or request['instrument']
            if request['instrument'] != instrument:
                raise ValueError('instrument_changed')
            rows = json.loads(path.read_text(encoding='utf-8'))
            validate_rows(rows, int(lower_dt.timestamp()*1000), int(upper_dt.timestamp()*1000), grid)
            if (len(rows), rows[0]['timestamp'], rows[-1]['timestamp']) != (seal['rows'], seal['first'], seal['last']):
                raise ValueError('seal_metadata')
            sides.append(rows)
            seals.append(seal)
        spreads.extend(paired_spreads(*sides))
        stamps.update(r['timestamp'] for r in sides[0])
        row_count += len(sides[0])
    coverage = []
    for day, expected in sessions.items():
        missing = [t for t in expected if t not in stamps]
        coverage.append({'day': day, 'expected': len(expected), 'observed': len(expected)-len(missing),
                         'missing_utc': [datetime.fromtimestamp(t/1000, timezone.utc).isoformat() for t in missing]})
    incomplete = [d for d in coverage if d['missing_utc']]
    return {
        'schema': 'sealed-m1-review-v1', 'instrument': instrument, 'year': year,
        'status': 'cash_coverage_complete' if not incomplete else 'cash_gaps_require_protocol',
        'source_seals': seals, 'manifest_sha256': digest(root/'manifest.json'),
        'download_result_sha256': digest(root/'result.json'),
        'calendar_sha256': digest(calendar_path), 'reviewer_sha256': digest(Path(__file__)),
        'price_grid': grid, 'rows_per_side': row_count,
        'cash_sessions': len(sessions), 'full_sessions': sum(d['expected'] == 390 for d in coverage),
        'short_sessions': [d for d in coverage if d['expected'] != 390],
        'expected_cash_minutes': sum(d['expected'] for d in coverage),
        'observed_cash_minutes': sum(d['observed'] for d in coverage),
        'incomplete_sessions': incomplete, 'coverage_by_session': coverage,
        'endpoint_spread_median': statistics.median(spreads), 'endpoint_spread_max': max(spreads),
        'elapsed_seconds': timer.perf_counter()-began,
        'limits': ['Independent M1 side extrema do not establish intrabar mid or synchronous spread paths.',
                   'Cash calendar is not the CFD broker trading contract.',
                   'No prices repaired or missing minutes filled; no strategy PnL or prop certification.'],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, required=True)
    parser.add_argument('--calendar', type=Path, required=True)
    parser.add_argument('--price-grid', type=float, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('output_already_exists')
    result = review(args.root, args.calendar, args.price_grid)
    with args.output.open('x', encoding='utf-8') as stream:
        json.dump(result, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: result[k] for k in ('status', 'rows_per_side', 'cash_sessions',
                       'expected_cash_minutes', 'observed_cash_minutes', 'elapsed_seconds')}))


if __name__ == '__main__':
    main()
