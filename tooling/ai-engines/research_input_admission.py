"""Bind multi-instrument M1 fixture metadata to sealed exports and raw source.

Read-only admission for source inspection, never an OOS, fill or edge certificate.
The quarterly/product contracts remain unchanged; legacy artifacts are not edited.
"""
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
import argparse
import json
from pathlib import Path
import re
import time

from candle_source_provenance import inspect_expansion
from sealed_m1_review import digest, paired_spreads, validate_rows

SCHEMA = 'research-M1-fixture-admission-v1'
CLOCK = dict(timezone='UTC', timestamp_unit='unix_ms', bar_timestamp='open',
             duration_ms=60000, close_known_after_ms=60000)


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def instant(text):
    value = datetime.fromisoformat(text.replace('Z', '+00:00'))
    if value.utcoffset() is None or value.utcoffset().total_seconds() != 0:
        raise ValueError('request_UTC_required')
    stamp = value.timestamp()*1000
    if not stamp.is_integer() or stamp % 60000:
        raise ValueError('request_M1_boundary')
    return int(stamp)


def review_fixture(root, metadata_path, *, progress=None):
    began, cpu = time.perf_counter(), time.process_time()
    root, metadata_path = Path(root), Path(metadata_path)
    bindings = {}

    def bind(path, expected=None):
        path = Path(path).resolve()
        actual = digest(path)
        if expected is not None and actual != expected:
            raise ValueError('input_hash_binding')
        if str(path) in bindings and bindings[str(path)] != actual:
            raise ValueError('input_changed_during_review')
        bindings[str(path)] = actual
        return path

    metadata = read(bind(metadata_path))
    if (metadata.get('schema') != SCHEMA or metadata.get('clock') != CLOCK
            or metadata.get('data_role') != 'source_fixture'
            or metadata.get('exposure') not in ('previously_consumed', 'unknown')
            or metadata.get('clean_oos') is not False):
        raise ValueError('fixture_schema_clock_role_or_exposure')
    protocol = bind(metadata['protocol']['path'], metadata['protocol']['sha256'])
    manifest_path = bind(root/'manifest.json', metadata['parent_manifest_sha256'])
    result_path = bind(root/'result.json', metadata['parent_result_sha256'])
    manifest, result = read(manifest_path), read(result_path)
    if (manifest.get('holdoutRead') is not False or result.get('holdoutRead') is not False
            or manifest.get('strategySimulated') is not False
            or result.get('strategySimulated') is not False
            or manifest.get('brokerCalls') != 0 or result.get('brokerCalls') != 0
            or manifest.get('modelCalls') != 0 or result.get('modelCalls') != 0):
        raise ValueError('fixture_scope_required')
    producer = metadata.get('producer_bindings')
    if not isinstance(producer, dict) or not producer:
        raise ValueError('producer_bindings_required')
    if not manifest.get('sourcePins') or not set(manifest['sourcePins'].values()).issubset(set(producer.values())):
        raise ValueError('original_producer_snapshots_required')
    for name, sha in producer.items():
        bind(name, sha)
    raw_bindings = metadata.get('raw_bindings')
    if not isinstance(raw_bindings, dict) or not raw_bindings:
        raise ValueError('frozen_raw_bindings_required')
    used_raw = set()
    assets = metadata['assets']
    if (not assets or len({a['instrument'] for a in assets}) != len(assets)
            or len(manifest['requests']) != 2*len(assets)
            or len(result['requests']) != 2*len(assets)):
        raise ValueError('instrument_side_census')
    requests = {(r['instrument'], r['priceType']): r for r in manifest['requests']}
    seals = {r['request']: r for r in result['requests']}
    if len(requests) != 2*len(assets) or len(seals) != 2*len(assets):
        raise ValueError('duplicate_request_or_seal')
    reports = []
    for asset in assets:
        instrument = asset['instrument']
        source_meta = manifest['metadata'][instrument]
        if (asset['provider'] != 'Dukascopy' or asset['provider_symbol'] != source_meta['code']
                or not re.fullmatch('[A-Z]{3}', asset['quote_currency'])
                or not asset.get('source_use')):
            raise ValueError('provider_currency_or_source_mapping')
        if asset['kind'] == 'fx':
            if (asset['adjustment_basis'] != 'not_applicable_fx'
                    or asset['price_unit'] != 'quote_per_base'
                    or not re.fullmatch('[A-Z]{3}', asset['base_currency'])
                    or asset['provider_symbol'] != asset['base_currency']+'-'+asset['quote_currency']):
                raise ValueError('FX_units_or_adjustment')
        elif asset['kind'] == 'etf_cfd_proxy':
            if (asset['price_unit'] != 'quote_per_share_proxy'
                    or asset['adjustment_basis'] != 'unknown'
                    or asset['base_currency'] is not None
                    or not re.fullmatch(r'[A-Z0-9]+\.US-'+asset['quote_currency'], asset['provider_symbol'])):
                raise ValueError('ETF_adjustment_unverified_in_fixture')
        else:
            raise ValueError('unregistered_asset_kind')
        grid = Decimal(asset['price_grid'])
        if not grid.is_finite() or grid <= 0:
            raise ValueError('positive_grid_required')
        sides, side_reports, bounds = [], [], []
        for side in ('bid', 'ask'):
            request = requests[(instrument, side)]
            if (request['timeframe'] != 'm1' or request['ignoreFlats'] is not False
                    or request.get('utcOffset', 0) != 0):
                raise ValueError('unfiltered_UTC_M1_required')
            lower, upper = (instant(request['dates'][key]) for key in ('from', 'to'))
            if not 0 <= lower < upper <= 1735689600000:
                raise ValueError('historical_scope_holdout_closed')
            bounds.append((lower, upper))
            stem = instrument+'-'+side
            path = root/(stem+'.json')
            seal = read(bind(root/(stem+'-seal.json')))
            if seal != seals[stem]:
                raise ValueError('seal_binding')
            rows = read(bind(path, seal['sha256']))
            validate_rows(rows, lower, upper, float(grid))
            if (seal['request'], seal['rows'], seal['first'], seal['last']) != (
                    stem, len(rows), rows[0]['timestamp'], rows[-1]['timestamp']):
                raise ValueError('seal_row_census')
            days = defaultdict(list)
            for row in rows:
                days[row['timestamp']//86400000*86400000].append(row)
            kept, padding, raw_reports = [], 0, []
            for day, native_rows in days.items():
                at = datetime.fromtimestamp(day/1000, timezone.utc)
                name = (f'candles%2Fminute%2F{asset["provider_symbol"]}%2F{side.upper()}'
                        f'%2F{at.year}%2F{at.month}%2F{at.day}.json')
                raw_path = (Path(request['cacheFolderPath'])/name).resolve()
                if str(raw_path) not in raw_bindings:
                    raise ValueError('raw_source_not_registered')
                bind(raw_path, raw_bindings[str(raw_path)])
                used_raw.add(str(raw_path))
                raw = read(raw_path)
                if Decimal(str(raw['multiplier'])) != grid:
                    raise ValueError('raw_grid_binding')
                # Daily native exports must cover the complete decoder expansion.
                inspected = inspect_expansion(raw, native_rows)
                if any(not day <= row['timestamp'] < day+86400000 for row in inspected['explicit_rows']):
                    raise ValueError('raw_day_binding')
                kept.extend(inspected['explicit_rows'])
                padding += len(inspected['padding_stamps'])
                raw_reports.append(dict(path=str(raw_path), sha256=bindings[str(raw_path)],
                                        explicit_rows=len(inspected['explicit_rows'])))
            sides.append(kept)
            side_reports.append(dict(side=side, native_rows=len(rows), explicit_rows=len(kept),
                                     padding_rows=padding, raw_sources=raw_reports))
            if progress:
                progress(dict(stage='source_side_verified', instrument=instrument, side=side,
                              elapsed_seconds=time.perf_counter()-began))
        if bounds[0] != bounds[1]:
            raise ValueError('request_side_scope_alignment')
        left, right = ({r['timestamp']: r for r in rows} for rows in sides)
        common = sorted(left.keys() & right.keys())
        if not common:
            raise ValueError('no_paired_explicit_observations')
        paired_spreads([left[t] for t in common], [right[t] for t in common])
        reports.append(dict(instrument=instrument, declared_semantics=asset,
                            requested_from_ms=bounds[0][0], requested_to_ms=bounds[0][1],
                            sides=side_reports, paired_source_rows=len(common),
                            unpaired_source_rows=dict(bid=len(left)-len(common), ask=len(right)-len(common)),
                            quality_basis='full_raw_price_volume_timestamp_binding_no_fill',
                            adjustment_verified=False if asset['kind']=='etf_cfd_proxy' else None))
    if used_raw != set(raw_bindings):
        raise ValueError('registered_raw_census')
    if any(digest(Path(name)) != sha for name, sha in bindings.items()):
        raise ValueError('input_changed_before_report')
    return dict(schema=SCHEMA, status='source_fixture_verified_only', protocol_sha256=digest(protocol),
                data_role=metadata['data_role'], exposure=metadata['exposure'], clean_oos=False,
                input_bindings=bindings, assets=reports,
                validator_bindings={str(p.resolve()): digest(p) for p in (
                    Path(__file__), Path(__file__).with_name('candle_source_provenance.py'),
                    Path(__file__).with_name('sealed_m1_review.py'))},
                elapsed_seconds=time.perf_counter()-began, cpu_seconds=time.process_time()-cpu,
                network_calls=0, broker_calls=0, model_calls=0, holdout_read=False,
                limits=['No calendar completeness, publication lag, historical adjustment or long-history certificate.',
                        'M1 side endpoints are not simultaneous execution ticks or a WMR benchmark.',
                        'No clean OOS, strategy PnL, prop acceptance or execution authority.'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('root', 'metadata', 'output'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise ValueError('output_already_exists')
    report = review_fixture(args.root, args.metadata,
                            progress=lambda row: print(json.dumps(row), flush=True))
    with args.output.open('x', encoding='utf8') as stream:
        json.dump(report, stream, ensure_ascii=False, indent=2, allow_nan=False)
        stream.write('\n')
    print(json.dumps({k: report[k] for k in ('status', 'elapsed_seconds', 'cpu_seconds')}))


if __name__ == '__main__':
    main()
