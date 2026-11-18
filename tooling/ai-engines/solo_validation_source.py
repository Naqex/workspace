"""S03 GBP source release/census/admission; no economics or broker execution."""
import ast
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

import numpy as np

from prop_campaign_source import DTYPE, START, END, FINAL, HOUR, Prices, stamp
from prop_atlas_source import decode_grid
from prop_atlas_scan import candidates
from prop_portfolio_sources import deadline
from prop_portfolio_scan import gap_unknown
from solo_gbp_source import compare_h1

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = Path('E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research')
PARENT = Path('E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1')
JOB = ROOT / 'S03-three-asset-validation'
SOURCE_JOB = JOB / 'gbp-source'
S01 = ROOT / 'S01-gbp-confirmation-source-v2'
HISTORY = PARENT / 'fx-h1-history-v3'
PROTOCOL = WORKSPACE / 'planning/research/SOLO-THREE-ASSET-VALIDATION-PROTOCOL-20261118.md'
INCIDENT = ROOT / 'three-asset-preparation/s03-design-20261118/PRE-RELEASE-METADATA-INCIDENT.json'
CALENDAR = WORKSPACE / 'planning/research/XAUUSD-A-SESSION-CALENDAR-20261114.json'
CELL = 'GBPUSD.SWEEP.ASIA.LONDON.DAY'
WINDOW = dict(first=END, end_exclusive=FINAL)
WARMUP = stamp('2021-11-01')
BUDGET = dict(concurrency=2, pause_ms=300, transient_failures=20,
              max_calls_per_url=3, deadline_seconds=7200)
CANONICAL = {
    'result': (ROOT / 'S02-three-asset-replay/attempt-1/result.json',
        '2d56e5b50e3374b6c2e7fcb91382141f7b419248b4068789b8c6ffa13da83f65'),
    'oracle': (ROOT / 'three-asset-preparation/independent-oracle/real-audit.json',
        '010efb944b7490fb1d53f81c6937a6cf9c51ac95251a712576ae8220ec02fb73'),
    's01_registration': (S01 / 'registration.json',
        'eac66a06ccae82cc9b01ddaad561688217b39daa218aeb51927c30ec10daef01'),
    's01_source_proof': (S01 / 'source-proof.json',
        '63e8a491454e6ceeaed47798be94e840426475d0d6609e8d0a9af5fde1551ee7'),
}
FACTS = ('id', 'asset', 'side', 'day', 'decision_msc', 'stop_units',
         'deadline_msc', 'deadline_kind')
CORRECTED_HOURS = [1666094400000, 1666105200000]


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    with Path(path).open('rb') as source:
        return hashlib.file_digest(source, 'sha256').hexdigest()


def pin(path):
    path = Path(path).resolve()
    return dict(path=str(path), sha256=digest(path))


def require(value, code):
    if not value:
        raise ValueError('S03_' + code)


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'),
                                    ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def sealed(value, field):
    return dict(value, **{field: canonical_hash(value)})


def verify_self(value, field):
    require(value.get(field) == canonical_hash({k: v for k, v in value.items() if k != field}),
            field + '_changed')


def plain(path):
    path = Path(path).absolute()
    for item in (path, *path.parents):
        if item.exists() or item.is_symlink():
            require(not item.is_symlink() and not (getattr(item.lstat(), 'st_file_attributes', 0) & 0x400),
                    'output_link_forbidden')
    return path


def owned(path):
    path = plain(path)
    require(path.resolve().is_relative_to(JOB.resolve()), 'output_outside_owned_job')
    return path


def write_new(path, value):
    path = owned(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8', newline='\n') as output:
        json.dump(value, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write('\n')


def verify_pins(items):
    require(len({str(Path(x['path']).resolve()) for x in items}) == len(items), 'duplicate_pins')
    for item in items:
        require(digest(item['path']) == item['sha256'], 'bound_input_changed:' + Path(item['path']).name)


def canonical_pins():
    items = {}
    for key, (path, expected) in CANONICAL.items():
        item = pin(path)
        require(item['sha256'] == expected, 'canonical_' + key + '_changed')
        items[key] = item
    return items


def producer_paths():
    folder = WORKSPACE / 'tooling/ai-engines'
    pending = [folder / name for name in ('solo_validation_source.py', 'solo_validation_replay.py')]
    found = set()
    while pending:
        path = pending.pop()
        require(path.is_file(), 'producer_missing:' + path.name)
        if path in found:
            continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding='utf-8-sig'))):
            modules = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                       [x.name for x in node.names] if isinstance(node, ast.Import) else [])
            for name in modules:
                target = folder / (name.split('.')[0] + '.py')
                if target.is_file():
                    pending.append(target)
    found.update((PROTOCOL, CALENDAR, folder / 'prepare_solo_validation_source.cjs',
        folder / 'prepare_solo_gbp_source.cjs', folder / 'dukascopy_cached_m1.cjs',
        folder / 'tests/test_solo_validation_source.py', folder / 'tests/test_solo_validation_replay.py',
        folder / 'tests/prepare_solo_validation_source.test.cjs',
        folder / 'tests/test_solo_portfolio_accounts.py',
        folder / 'source-runtime/package.json', folder / 'source-runtime/package-lock.json'))
    require(all(p.is_file() for p in found), 'producer_closure_incomplete')
    return sorted(found)


def committed_pins(commit):
    result = []
    for path in producer_paths():
        relative = path.relative_to(WORKSPACE).as_posix()
        data = subprocess.check_output(['git', 'show', commit + ':' + relative], cwd=WORKSPACE)
        require(data.replace(b'\r\n', b'\n') == path.read_bytes().replace(b'\r\n', b'\n'),
                'commit_before_release:' + relative)
        result.append(pin(path))
    return result


def h1_metadata():
    """Use seals and S01 metadata only; do not open any H1 price book here."""
    s01 = read(CANONICAL['s01_registration'][0])
    seals_path = HISTORY / 'sealed-books.json'
    seals = read(seals_path)
    if isinstance(seals, dict):
        seals = seals.get('books', seals.get('seals', []))
    indexed = {x['book']: x for x in seals}
    require(len(indexed) == len(seals), 'duplicate_history_seal')
    old_pins = {str(Path(x['path']).resolve()): x['sha256'] for x in s01['input_pins']}
    result = []
    for year in (2021, 2022, 2023, 2024):
        for side in ('bid', 'ask'):
            name = f'{year}-gbpusd-{side}'
            if year in (2022, 2023):
                item = s01['h1_source_books'][name]
                book, proof = Path(item['book']).resolve(), Path(item['proof']).resolve()
                checksum, proof_sha = old_pins[str(book)], old_pins[str(proof)]
                count, policy = item['selectedRows'], item['sourcePolicy']
            else:
                item = indexed[name]
                require(item['instrument'] == 'gbpusd' and item['year'] == year
                        and item['priceType'] == side and item['sourcePolicy'] == 'explicit_source_H1_only',
                        'history_seal_scope')
                book, proof = HISTORY / (name + '.json'), HISTORY / (name + '-source-proof.json')
                checksum, proof_sha = item['sha256'], item['sourceProofSha256']
                count, policy = item['rows'], item['sourcePolicy']
            detail = dict(year=year, side=side, path=str(book.resolve()), sha256=checksum,
                proof_path=str(proof.resolve()), proof_sha256=proof_sha, rows=count, source_policy=policy)
            if year == 2022:
                parent_book = HISTORY / (name + '.json')
                parent_proof = HISTORY / (name + '-source-proof.json')
                card = S01 / 'correction-card.json'
                detail['correction_lineage'] = {
                    key: dict(path=str(path.resolve()), sha256=old_pins[str(path.resolve())])
                    for key, path in (('original_book', parent_book),
                                      ('original_proof', parent_proof), ('correction_card', card))}
            result.append(detail)
    return result, pin(seals_path)


def inherited_metadata():
    # The allowlist is executable source frozen with this module. Stream bytes
    # only: these are release-time identities, not historical attestations.
    from solo_validation_replay import inherited_validation_paths
    return {key: pin(path) for key, path in inherited_validation_paths().items()}


def verify_review(review_pin, producers):
    verify_pins([review_pin])
    review = read(review_pin['path'])
    require(review.get('schema') == 'solo-validation-pre-release-review-v1'
            and review.get('status') == 'PASS' and review.get('source_only') is True
            and review.get('prices2024_2026_read') is False
            and review.get('price_access_claim_scope') == 'independent_reviewer_only',
            'independent_pre_release_review_required')
    expected = {p['path']: p['sha256'] for p in producers}
    require(review.get('reviewed_producer_sha256') == expected, 'review_exact_producer_closure_required')


def release(review_receipt):
    require(not (JOB / 'source-release.json').exists(), 'release_already_exists')
    canonical = canonical_pins()
    commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=WORKSPACE, text=True).strip()
    producers = committed_pins(commit)
    review_pin = pin(review_receipt)
    verify_review(review_pin, producers)
    books, seals_pin = h1_metadata()
    opaque = inherited_metadata()
    packet = sealed(dict(schema='solo-validation-source-release-v1', job_root=str(JOB.resolve()),
        producer_commit=commit, producer_pins=producers, input_pins=[*canonical.values(), seals_pin],
        canonical_s02=canonical, h1_books=books, review_pin=review_pin, window=WINDOW,
        inherited_validation=opaque,
        inherited_identity_kind='release_time_opaque_sha256_not_historical_attestation',
        inherited_identity_access=dict(mode='stream_bytes_to_sha256_only_no_JSON_parse',
            completed_at_utc=datetime.now(timezone.utc).isoformat(),
            sizes_bytes={key: Path(item['path']).stat().st_size for key, item in opaque.items()}),
        pre_release_metadata_incident=pin(INCIDENT), campaign2024_previously_exposed=True,
        created_at_utc=datetime.now(timezone.utc).isoformat(), source_only=True,
        financial_results_computed=False, prices2025_2026_read=False,
        historical_validation_previously_exposed=True), 'release_sha256')
    write_new(JOB / 'source-release.json', packet)
    return verify_release()


def verify_release():
    path = owned(JOB / 'source-release.json')
    require(path.is_file(), 'source_release_missing')
    packet = read(path)
    verify_self(packet, 'release_sha256')
    require(packet.get('schema') == 'solo-validation-source-release-v1'
            and packet.get('job_root') == str(JOB.resolve()) and packet.get('window') == WINDOW
            and packet.get('source_only') is True and packet.get('financial_results_computed') is False
            and packet.get('prices2025_2026_read') is False, 'source_release_scope')
    require(packet['canonical_s02'] == canonical_pins(), 'source_release_canonical_identity')
    verify_pins(packet['input_pins'])
    require(packet['producer_pins'] == committed_pins(packet['producer_commit']), 'source_release_producer_changed')
    verify_review(packet['review_pin'], packet['producer_pins'])
    require(packet.get('pre_release_metadata_incident') == pin(INCIDENT)
            and packet.get('campaign2024_previously_exposed') is True, 'incident_disclosure_changed')
    books, seals_pin = h1_metadata()
    require(packet['h1_books'] == books and seals_pin in packet['input_pins'], 'source_release_H1_metadata_changed')
    require(packet.get('inherited_identity_kind') == 'release_time_opaque_sha256_not_historical_attestation'
            and packet.get('inherited_validation') == inherited_metadata(), 'inherited_release_identity_changed')
    access = packet.get('inherited_identity_access', {})
    require(access.get('mode') == 'stream_bytes_to_sha256_only_no_JSON_parse'
            and isinstance(access.get('completed_at_utc'), str)
            and access.get('sizes_bytes') == {key: Path(item['path']).stat().st_size
                for key, item in packet['inherited_validation'].items()}, 'opaque_access_receipt_changed')
    return packet


def book_rows(detail):
    """Caller verifies release first. Timestamp scope is checked before OHLC conversion."""
    year, side = detail['year'], detail['side']
    require(type(year) is int and year in (2021, 2022, 2023, 2024) and side in ('bid', 'ask'), 'H1_year_closed')
    expected_name = f'{year}-gbpusd-{side}.json'
    require(Path(detail['path']).name == expected_name, 'H1_path_scope')
    require(digest(detail['path']) == detail['sha256'] and digest(detail['proof_path']) == detail['proof_sha256'],
            'H1_seal_changed')
    proof = read(detail['proof_path'])
    require(proof.get('observedTickTimestamps') is False
            and proof.get('sourcePolicy') == detail['source_policy'], 'H1_source_proof_scope')
    if year == 2022:
        lineage = detail['correction_lineage']
        require(all(proof.get(key) == value for key, value in lineage.items())
                and proof.get('corrected_hours') == CORRECTED_HOURS
                and proof.get('tick_timestamps_observed_only_at') == CORRECTED_HOURS
                and proof.get('changed_fields') == ['open', 'high', 'low', 'close']
                and proof.get('original_volume_retained_not_tick_volume') is True
                and proof.get('independent_feed_verified') is False, 'corrected_H1_proof_lineage')
        verify_pins(list(lineage.values()))
        parent_proof = read(lineage['original_proof']['path'])
        card = read(lineage['correction_card']['path'])
        require(parent_proof.get('sourcePolicy') == 'explicit_source_H1_only'
                and parent_proof.get('observedTickTimestamps') is False
                and parent_proof.get('selectedRows') == detail['rows']
                and parent_proof.get('unavailableSources') == [], 'corrected_H1_parent_proof')
        require(card.get('schema') == 'S01-source-correction-v2'
                and [x['at'] for x in card['changes'][side]] == CORRECTED_HOURS
                and card.get('cohort_and_natural_stops_unchanged') is True
                and card.get('financial_outcomes_computed') is False, 'corrected_H1_card')
    else:
        require(proof.get('selectedRows') == detail['rows']
                and proof.get('unavailableSources') == [], 'H1_source_proof_scope')
    rows = read(detail['path'])
    require(isinstance(rows, list) and len(rows) == detail['rows'], 'H1_row_census')
    first, end = stamp(f'{year}-01-01'), stamp(f'{year+1}-01-01')
    stamps = [r['timestamp'] for r in rows]
    require(all(type(at) is int and first <= at < end and at % HOUR == 0 for at in stamps)
            and stamps == sorted(set(stamps)), 'H1_clock_or_year')
    result = {}
    for row in rows:
        at = row['timestamp']
        if at < WARMUP:
            continue
        raw_values = [Decimal(str(row[k])) * 100000 for k in ('open', 'high', 'low', 'close')]
        require(all(v.is_finite() and v == v.to_integral_value() and v > 0 for v in raw_values), 'H1_price_grid')
        values = list(map(int, raw_values))
        require(values[2] <= min(values[0], values[3]) <= max(values[0], values[3]) <= values[1], 'H1_OHLC')
        result[at] = values
    return result


def load_books(packet):
    sides = {'bid': {}, 'ask': {}}
    for detail in packet['h1_books']:
        values = book_rows(detail)
        require(not (set(values) & sides[detail['side']].keys()), 'H1_duplicate_timestamp')
        sides[detail['side']].update(values)
    require(set(sides['bid']) == set(sides['ask']), 'H1_side_timestamp_mismatch')
    hours = [[at, *b, 60] for at, b in sorted(sides['bid'].items())]
    return hours, {(at, side): values for side, rows in sides.items() for at, values in rows.items()}


def signal_census(rows, first=END, end=FINAL):
    signals, hours, seen = [], set(), set()
    for row in rows:
        at, close = row['decision_msc'], row['deadline_msc']
        require(row['id'] == CELL and row['asset'] == 'GBPUSD' and row['side'] in ('BUY', 'SELL')
                and type(at) is int and type(close) is int and at % HOUR == 0
                and first <= at < close and close + 60000 < end
                and type(row['stop_units']) is int and row['stop_units'] > 0
                and row['day'] == datetime.fromtimestamp(at / 1000, timezone.utc).date().isoformat(),
                'raw_cohort_scope_or_cutoff')
        key = (at, row['side'])
        require(key not in seen, 'duplicate_raw_signal')
        seen.add(key)
        signals.append({k: row[k] for k in FACTS})
        hours.update(range(at, close // HOUR * HOUR + HOUR, HOUR))
    require(signals and signals == sorted(signals, key=lambda r: r['decision_msc']), 'empty_or_unordered_cohort')
    return signals, sorted(hours)


def generated_signals(hours, first, end):
    require(Path.cwd().resolve() == WORKSPACE.resolve(), 'workspace_cwd_required_for_frozen_calendar')
    rows, abstentions = candidates(hours, 'GBPUSD', first=first, end=end, only_cells=[CELL])
    for row in rows:
        row['deadline_msc'], row['deadline_kind'] = deadline(row, row['decision_msc'])
    signals, census = signal_census(rows, first, end)
    return signals, census, abstentions


def register_source():
    release_packet = verify_release()
    require(not (SOURCE_JOB / 'registration.json').exists(), 'source_registration_already_exists')
    hours, _ = load_books(release_packet)
    dev, dev_hours, _ = generated_signals([r for r in hours if r[0] < END], START, END)
    old = read(CANONICAL['s01_registration'][0])
    require(dev == old['signals'] and dev_hours == old['hours'] and len(dev) == 300, 'Development_signal_prefix_changed')
    signals, census, abstentions = generated_signals(hours, END, FINAL)
    # External caches have not been admitted for this cohort. Do not claim
    # they are absent: native resume reuses only this job's sealed bytes.
    source_pins = [p for d in release_packet['h1_books'] for p in (
        dict(path=d['path'], sha256=d['sha256']), dict(path=d['proof_path'], sha256=d['proof_sha256']))]
    packet = sealed(dict(schema='solo-validation-gbp-source-v1', cell=CELL,
        job_root=str(SOURCE_JOB.resolve()), window=WINDOW, signals=signals, hours=census,
        reused={}, missing_hours=census, input_pins=source_pins,
        producer_pins=release_packet['producer_pins'], h1_source_books=release_packet['h1_books'],
        release_pin=pin(JOB / 'source-release.json'), source_budget=BUDGET,
        development_prefix_signals=300, development_prefix_verified=True,
        external_tick_cache_status='NOT_ADMITTED_UNCHECKED',
        native_owned_cache_reuse=True,
        abstentions=abstentions, source_only=True, financial_results_computed=False,
        prices2025_2026_read=False, created_at_utc=datetime.now(timezone.utc).isoformat()), 'registration_sha256')
    write_new(SOURCE_JOB / 'registration.json', packet)
    return verify_source_registration()


def verify_source_registration(registration_path=None):
    path = owned(registration_path or SOURCE_JOB / 'registration.json')
    require(path.resolve() == (SOURCE_JOB / 'registration.json').resolve(), 'source_registration_path')
    release_packet = verify_release()
    packet = read(path)
    verify_self(packet, 'registration_sha256')
    require(packet.get('schema') == 'solo-validation-gbp-source-v1' and packet.get('cell') == CELL
            and packet.get('job_root') == str(SOURCE_JOB.resolve()) and packet.get('window') == WINDOW
            and packet.get('source_only') is True and packet.get('financial_results_computed') is False
            and packet.get('prices2025_2026_read') is False and packet.get('source_budget') == BUDGET,
            'source_registration_scope')
    require(packet['release_pin'] == pin(JOB / 'source-release.json')
            and packet['producer_pins'] == release_packet['producer_pins']
            and packet['h1_source_books'] == release_packet['h1_books'], 'source_registration_release_binding')
    expected_pins = [p for d in release_packet['h1_books'] for p in (
        dict(path=d['path'], sha256=d['sha256']), dict(path=d['proof_path'], sha256=d['proof_sha256']))]
    require(packet['input_pins'] == expected_pins, 'source_registration_input_pin_census')
    signals, hours = signal_census(packet['signals'])
    require(signals == packet['signals'] and hours == packet['hours']
            and packet['reused'] == {} and packet['missing_hours'] == hours
            and packet.get('development_prefix_verified') is True
            and packet.get('development_prefix_signals') == 300, 'source_registration_census')
    verify_pins(packet['input_pins'])
    # A self-hash protects accidental edits, not a re-signed, selectively
    # shortened cohort. Recreate exactly the frozen raw recipe before download.
    bars, _ = load_books(release_packet)
    dev, dev_hours, _ = generated_signals([r for r in bars if r[0] < END], START, END)
    original = read(CANONICAL['s01_registration'][0])
    require(dev == original['signals'] and dev_hours == original['hours']
            and len(dev) == 300, 'Development_signal_prefix_changed')
    regenerated, regenerated_hours, abstentions = generated_signals(bars, END, FINAL)
    require(regenerated == packet['signals'] and regenerated_hours == hours
            and abstentions == packet['abstentions'], 'registered_raw_recipe_changed')
    return packet


def decode_hour(raw, at):
    require(type(at) is int and END <= at < FINAL and at % HOUR == 0, 'tick_hour_outside_validation')
    values = decode_grid(raw, at, 100000)
    require(len(values) == len(raw['times']), 'out_of_hour_ticks_not_dropped')
    require(all(0 < b <= a <= np.iinfo(np.int32).max
                for b, a in zip(values.bid_units, values.ask_units)), 'tick_int32_price_grid')
    result = np.empty(len(values), dtype=DTYPE)
    result['t'], result['b'], result['a'] = values.timestamps, values.bid_units, values.ask_units
    return result


def held_quality(signals, manifest):
    reader, issues = Prices(manifest, cutoff=FINAL), []
    for row in signals:
        entry, close = reader.endpoint(row['decision_msc']), reader.endpoint(row['deadline_msc'])
        if entry is None or close is None:
            issues.append(dict(day=row['day'], reason='ENTRY_OR_DEADLINE_QUOTE_UNKNOWN'))
            continue
        ticks, _ = reader.path(entry[0], close[0])
        gaps = gap_unknown(ticks['t'], 0, asset='GBPUSD')
        if gaps:
            issues.append(dict(day=row['day'], reason='HELD_GAP_GT15_MINUTES', gaps=gaps))
    return issues


def admit_source():
    registration = verify_source_registration()
    require(not (SOURCE_JOB / 'source-proof.json').exists(), 'source_admission_receipt_already_exists')
    seals_path = owned(SOURCE_JOB / 'source/sealed-hours.json')
    seals = read(seals_path) if seals_path.exists() else []
    by_hour = {r['at']: r for r in seals}
    require(len(by_hour) == len(seals) and set(by_hour) <= set(registration['hours']), 'downloaded_hour_census')
    missing = sorted(set(registration['hours']) - set(by_hour))
    if missing:
        write_new(SOURCE_JOB / 'source-incomplete.json', dict(status='SOURCE_INCOMPLETE', missing_hours=missing,
            source_only=True, financial_results_computed=False, prices2025_2026_read=False))
        return False
    packet = verify_release()
    _, expected = load_books(packet)
    manifests, mismatches, empty, checks = {}, [], [], []
    ticks_dir = owned(SOURCE_JOB / 'ticks')
    ticks_dir.mkdir(parents=True, exist_ok=True)
    for at in registration['hours']:
        seal = by_hour[at]
        raw_path = owned(seal['raw_path'])
        require(raw_path.resolve().is_relative_to((SOURCE_JOB / 'source').resolve()), 'downloaded_raw_outside_source')
        require(digest(raw_path) == seal['raw_sha256'], 'downloaded_raw_changed')
        ticks = decode_hour(read(raw_path), at)
        require(len(ticks) == seal['records'], 'downloaded_tick_census')
        target = owned(ticks_dir / f'{at}.ticks')
        content = ticks.tobytes()
        if target.exists():
            require(target.read_bytes() == content, 'existing_admitted_binary_changed')
        else:
            with target.open('xb') as stream:
                stream.write(content)
        if not len(ticks):
            empty.append(at)
        mismatches.extend(compare_h1(ticks, at, expected))
        manifests[str(at)] = dict(path=str(target.resolve()), records=len(ticks), sha256=digest(target))
        checks.append(dict(at=at, raw_sha256=seal['raw_sha256'], binary_sha256=digest(target)))
        if len(manifests) % 200 == 0:
            print(json.dumps(dict(stage='S03_source_admission', hours=len(manifests), expected=len(by_hour))), flush=True)
    issues = held_quality(registration['signals'], manifests)
    write_new(SOURCE_JOB / 'manifest.json', manifests)
    write_new(SOURCE_JOB / 'h1-reconciliation.json', dict(mismatches=mismatches, empty_hours=empty,
        original_sources_modified=False, prices2025_2026_read=False))
    write_new(SOURCE_JOB / 'held-path-quality.json', dict(issues=issues, raw_signals=len(registration['signals']),
        maximum_unregistered_gap_ms=900000, scheduled_closures_exempted=False))
    status = 'SOURCE_RECONCILED' if not mismatches and not empty and not issues else 'SOURCE_REVIEW_REQUIRED'
    proof = dict(status=status, expected_hours=len(registration['hours']), admitted_hours=len(manifests),
        paired_tick_records=sum(r['records'] for r in manifests.values()), h1_difference_count=len(mismatches),
        empty_hours=empty, held_path_issue_count=len(issues), source_checks=checks,
        registration_sha256=digest(SOURCE_JOB / 'registration.json'), manifest_sha256=digest(SOURCE_JOB / 'manifest.json'),
        same_ms_order_preserved=True, source_only=True, prop_qualified=False,
        financial_results_computed=False, prices2025_2026_read=False)
    write_new(SOURCE_JOB / 'source-proof.json', proof)
    return status == 'SOURCE_RECONCILED'


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('release', 'verify-release', 'register', 'verify-registration', 'admit'))
    parser.add_argument('--review', type=Path)
    parser.add_argument('--registration', type=Path, default=SOURCE_JOB / 'registration.json')
    args = parser.parse_args()
    try:
        if args.stage == 'release':
            require(args.review is not None, 'review_receipt_required')
            result = release(args.review)
        elif args.stage == 'verify-release':
            result = verify_release()
        elif args.stage == 'register':
            result = register_source()
        elif args.stage == 'verify-registration':
            result = verify_source_registration(args.registration)
        else:
            passed = admit_source()
            print(json.dumps(dict(source_reconciled=passed, source_only=True)))
            raise SystemExit(0 if passed else 2)
        print(json.dumps(dict(verified=True, source_only=True, job_root=result['job_root'],
            registration_sha256=digest(args.registration) if args.stage == 'verify-registration' else None)))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as error:
        print(str(error) if str(error).startswith('S03_') else 'S03_source_error:' + str(error), file=__import__('sys').stderr)
        raise SystemExit(1)
