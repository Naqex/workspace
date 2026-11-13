"""Timestamp-only quality census of admitted XAU M1; no signals or price IO."""
from array import array
from bisect import bisect_left
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import time

from eurusd_b0_source import digest, write_json

RAW_SHA = 'd209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9'
END = 1735689600


def missing_runs(present, count=840):
    if any(type(v) is not int or not 0 <= v < count for v in present):
        raise ValueError('minute_outside_quality_window')
    previous = -1
    result = []
    for index in sorted(set(present)) + [count]:
        missing = index-previous-1
        if missing > 15:
            kind = 'whole_day' if not present else 'boundary' if previous == -1 or index == count else 'interior'
            result.append(dict(start_offset_minute=previous+1, end_offset_exclusive_minute=index,
                               missing_minutes=missing, kind=kind))
        previous = index
    return result


def census(cache, raw_path, output):
    cache, raw_path, output = Path(cache), Path(raw_path), Path(output)
    output.mkdir(parents=True, exist_ok=False)
    began = time.monotonic()
    def status(stage, **fields):
        event = dict(stage=stage, utc=datetime.now(timezone.utc).isoformat(), **fields)
        write_json(output/'status.json', event)
        with (output/'events.jsonl').open('a', encoding='utf-8') as stream:
            stream.write(json.dumps(event)+'\n')
        print(json.dumps(event), flush=True)
    manifest_path = cache/'manifest.json'
    manifest = json.loads(manifest_path.read_bytes())
    if (manifest['raw_sha256'] != RAW_SHA or manifest['scope_end_exclusive'] != END
            or manifest['time_unit'] != 'UTCseconds' or manifest['rows'] != 5399878):
        raise ValueError('unadmitted_gold_timestamp_source')
    if digest(raw_path) != RAW_SHA or digest(cache/'times.bin') != manifest['files']['times.bin']:
        raise ValueError('gold_source_or_timestamp_content_changed')
    values = array('q')
    if values.itemsize != 8:
        raise ValueError('64bit_timestamp_array_required')
    with (cache/'times.bin').open('rb') as stream:
        values.fromfile(stream, manifest['rows'])
        if stream.read(1):
            raise ValueError('timestamp_trailing_data')
    if sys.byteorder != manifest['byteorder']:
        values.byteswap()
    start = int(datetime(2022, 1, 1, tzinfo=timezone.utc).timestamp())
    lo, hi = bisect_left(values, start), bisect_left(values, END)
    if hi != len(values) or any(b <= a or a % 60 or b % 60 for a, b in zip(values[lo:hi-1], values[lo+1:hi])):
        raise ValueError('gold_timestamp_order_grid_or_closed_holdout')
    status('admitted_timestamp_cache_verified', selected_rows=hi-lo, price_columns_opened=False)
    annuals, records = [], []
    for year in (2022, 2023, 2024):
        day = date(year, 1, 1)
        days = []
        while day.year == year:
            if day.weekday() < 5:
                zero = int(datetime(day.year, day.month, day.day, tzinfo=timezone.utc).timestamp())
                start, end = zero+7*3600, zero+21*3600
                a, b = bisect_left(values, start), bisect_left(values, end)
                observed = values[a:b]
                present = {(at-start)//60 for at in observed}
                runs = missing_runs(present)
                for run in runs:
                    run.update(start_utc=datetime.fromtimestamp(start+60*run['start_offset_minute'], timezone.utc).isoformat(),
                               end_exclusive_utc=datetime.fromtimestamp(start+60*run['end_offset_exclusive_minute'], timezone.utc).isoformat())
                days.append(dict(day=day.isoformat(), observed_minutes=len(present), expected_clock_minutes=840,
                    missing_minutes=840-len(present), missing_runs_gt15=runs,
                    interbar_gaps_gt15=sum(y-x > 15*60 for x, y in zip(observed, observed[1:]))))
            day += timedelta(days=1)
        row = dict(year=year, weekday_windows=len(days), expected_clock_minutes=840*len(days),
            observed_minutes=sum(d['observed_minutes'] for d in days),
            days_with_missing_run_gt15=sum(bool(d['missing_runs_gt15']) for d in days),
            empty_weekday_windows=sum(d['observed_minutes'] == 0 for d in days),
            nonempty_days_with_missing_run_gt15=sum(bool(d['missing_runs_gt15']) and d['observed_minutes'] > 0 for d in days),
            days_with_interior_missing_run_gt15=sum(any(r['kind'] == 'interior' for r in d['missing_runs_gt15']) for d in days),
            days_with_boundary_missing_run_gt15=sum(any(r['kind'] == 'boundary' for r in d['missing_runs_gt15']) for d in days),
            total_runs_gt15=sum(len(d['missing_runs_gt15']) for d in days),
            days_with_interbar_gap_gt15=sum(d['interbar_gaps_gt15'] > 0 for d in days),
            worst_missing_run_minutes=max((r['missing_minutes'] for d in days for r in d['missing_runs_gt15']), default=0))
        row['weekday_clock_coverage_pct'] = row['observed_minutes']/row['expected_clock_minutes']*100
        annuals.append(row)
        records.extend(days)
        status('year_quality_counted', year=year)
    packet = dict(schema='XAUUSD-M1-intraday-quality-2022-2024-v1', annual=annuals,
        window='07:00-inclusive/21:00-exclusive UTC; weekdays including unverified holidays',
        gap_definition='strictly more than15 consecutive absent M1 opens; separately report >15min observed interbar spacing',
        source=dict(raw_sha256=RAW_SHA, timestamp_manifest_sha256=digest(manifest_path),
            timestamp_file_sha256=digest(cache/'times.bin'), source_cache=str(cache),
            raw_path=str(raw_path), side='Bid', selected_timestamp_rows=hi-lo),
        code_sha256=digest(__file__), price_columns_opened=False, price_2025_2026_read=False,
        provider_outage_or_trading_session_coverage_certified=False, calendar_verified=False,
        Ask_or_tick_execution_admitted=False, signals_counted=False, new_strategy_backtests=0,
        wall_seconds=time.monotonic()-began)
    write_json(output/'quality-by-day.json', records)
    write_json(output/'result.json', packet)
    status('completed_timestamp_quality_only', result_sha256=digest(output/'result.json'))
    return packet


if __name__ == '__main__':
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--cache', type=Path, required=True)
    p.add_argument('--raw', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    args = p.parse_args()
    census(args.cache, args.raw, args.output)
