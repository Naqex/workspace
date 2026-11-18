const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const crypto = require('node:crypto');
const {canonical, validHour, validateRaw, safeTree, verifyRegistrationFile, download} = require('../prepare_solo_validation_source.cjs');
const native = require(path.resolve(__dirname, '../../../.runtime/research-data/node_modules/dukascopy-node'));
const producer = path.resolve(__dirname, '../prepare_solo_validation_source.cjs');
const hash = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const pin = file => ({path: file, sha256: hash(fs.readFileSync(file))});
const HOUR = 3600000, at = Date.parse('2024-01-04T08:00:00Z');
const raw = hour => ({timestamp: hour, multiplier: .00001, bid: 1.2, ask: 1.2001,
  times: [1, 0], bids: [0, 1], asks: [0, 1], bidVolumes: [1, 2], askVolumes: [1, 2]});

function freeze(file, value) {
  delete value.registration_sha256;
  value.registration_sha256 = hash(canonical(value));
  fs.writeFileSync(file, JSON.stringify(value));
}

function fixture(t, count = 2) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'solo-validation-source-'));
  t.after(() => {
    const resolved = path.resolve(root), temp = path.resolve(os.tmpdir());
    const relative = path.relative(temp, resolved);
    assert(relative && !relative.startsWith('..') && !path.isAbsolute(relative));
    assert(path.basename(resolved).startsWith('solo-validation-source-'));
    fs.rmSync(resolved, {recursive: true, force: true});
  });
  const hours = Array.from({length: count}, (_, i) => at + i * HOUR);
  const input = path.join(root, 'registration.json');
  const release = path.join(root, 'release.json'); fs.writeFileSync(release, '{}');
  const r = {schema: 'solo-validation-gbp-source-v1', cell: 'GBPUSD.SWEEP.ASIA.LONDON.DAY',
    job_root: root, window: {first: Date.parse('2024-01-01Z'), end_exclusive: Date.parse('2025-01-01Z')},
    signals: [{id: 'GBPUSD.SWEEP.ASIA.LONDON.DAY', asset: 'GBPUSD', side: 'BUY',
      decision_msc: at, deadline_msc: at + (count - .5) * HOUR, stop_units: 119000}],
    hours, missing_hours: hours, reused: {}, input_pins: [], producer_pins: [pin(producer)],
    prices2025_2026_read: false, financial_results_computed: false, release_pin: pin(release),
    source_budget: {concurrency: 2, pause_ms: 300, transient_failures: 20,
      max_calls_per_url: 3, deadline_seconds: 7200}};
  freeze(input, r);
  const calls = [];
  const mapping = new Map(hours.map(hour => [native.generateUrls({instrument: 'gbpusd',
    timeframe: 'tick', priceType: 'bid', startDate: new Date(hour), endDate: new Date(hour + HOUR)})[0], hour]));
  const verify = file => ({verified: true, source_only: true, job_root: root,
    registration_sha256: hash(fs.readFileSync(file))});
  const fetcher = {fetch: async urls => {
    calls.push(urls[0]);
    const buffer = Buffer.from(JSON.stringify(raw(mapping.get(urls[0]))));
    const filename = encodeURIComponent(new URL(urls[0]).pathname.replace(/^\/v1\//, '')) + '.json';
    fs.writeFileSync(path.join(root, 'source/cache', filename), buffer);
    return [{url: urls[0], buffer, isCacheHit: false}];
  }};
  const options = {verify, fetcher, sleep: async () => {}, quiet: true};
  return {root, input, r, release, calls, mapping, fetcher, options};
}

test('2025, non-hour and escaping raw timestamps are denied', () => {
  assert.throws(() => validHour(Date.parse('2025-01-01Z')), /2024_hour/);
  assert.throws(() => validHour(Date.parse('2023-12-31Z')), /2024_hour/);
  assert.throws(() => validHour(at + 1), /2024_hour/);
  assert.doesNotThrow(() => validateRaw(raw(at), at));
  assert.throws(() => validateRaw({...raw(at), times: [1, HOUR]}, at), /outside_hour/);
  assert.throws(() => validateRaw({...raw(at), bids: [0, .5]}, at), /grid/);
});

test('Python gate denial happens before cache creation or fetch', async t => {
  const f = fixture(t, 1);
  await assert.rejects(download(f.input, {...f.options, verify: () => {throw Error('release_not_committed');}}), /release_not_committed/);
  assert.equal(fs.existsSync(path.join(f.root, 'source')), false);
  assert.equal(f.calls.length, 0);
});

test('actual Python verifier rejects an unregistered path before fetch', async t => {
  const f = fixture(t, 1);
  const executable = process.platform === 'win32'
    ? 'E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research-python/Scripts/python.exe'
    : 'python3';
  const options = {...f.options, verify: input => verifyRegistrationFile(input, executable)};
  await assert.rejects(download(f.input, options), error => {
    assert.equal(error.status, 1, 'the Python verifier must execute and reject');
    assert.match(String(error.stderr), /S03_[A-Za-z_]+/);
    assert.doesNotMatch(String(error.stderr), /ModuleNotFoundError|ImportError|No such file/);
    return true;
  });
  assert.equal(fs.existsSync(path.join(f.root, 'source')), false);
  assert.equal(f.calls.length, 0);
});

test('wrong verification receipt cannot authorize file bytes', async t => {
  const f = fixture(t, 1);
  await assert.rejects(download(f.input, {...f.options, verify: () => ({verified: true,
    source_only: true, job_root: f.root, registration_sha256: '0'.repeat(64)})}), /registration_scope/);
  assert.equal(fs.existsSync(path.join(f.root, 'source')), false);
  assert.equal(f.calls.length, 0);
});

test('registration or release tampering is refused before fetching', async t => {
  const f = fixture(t, 1);
  const changed = JSON.parse(fs.readFileSync(f.input)); changed.note = 'tampered';
  fs.writeFileSync(f.input, JSON.stringify(changed));
  await assert.rejects(download(f.input, f.options), /self_binding/);
  freeze(f.input, f.r); fs.appendFileSync(f.release, ' ');
  await assert.rejects(download(f.input, f.options), /frozen_pin/);
  assert.equal(f.calls.length, 0);
});

test('raw census includes cost rejects and cannot drop or add a held hour', async t => {
  const f = fixture(t);
  f.r.signals[0].pass15 = false;
  f.r.hours = [at]; f.r.missing_hours = [at]; freeze(f.input, f.r);
  await assert.rejects(download(f.input, f.options), /hour_census/);
  f.r.hours = [at, at + HOUR]; f.r.missing_hours = f.r.hours;
  f.r.reused = {[String(at + 2 * HOUR)]: {}}; freeze(f.input, f.r);
  await assert.rejects(download(f.input, f.options), /partition/);
  assert.equal(f.calls.length, 0);
});

test('resume preserves successful sibling and does not refetch sealed bytes', async t => {
  const f = fixture(t), failedURL = [...f.mapping.keys()][1], baseFetch = f.fetcher.fetch;
  let fail = true;
  f.fetcher.fetch = async urls => {
    if (urls[0] === failedURL && fail) {f.calls.push(urls[0]); throw Error('fixture_interruption');}
    return baseFetch(urls);
  };
  await assert.rejects(download(f.input, f.options), /fixture_interruption/);
  const first = JSON.parse(fs.readFileSync(path.join(f.root, 'source/sealed-hours.json')));
  assert.equal(first.length, 1); const before = fs.readFileSync(first[0].raw_path);
  fail = false; assert.equal((await download(f.input, f.options)).length, 2);
  assert.deepEqual(fs.readFileSync(first[0].raw_path), before);
  const count = f.calls.length; await download(f.input, f.options); assert.equal(f.calls.length, count);
  const result = JSON.parse(fs.readFileSync(path.join(f.root, 'source/result.json')));
  assert.equal(result.status, 'SOURCE_DOWNLOADED_NOT_ADMITTED');
  assert.equal(result.prices2025_2026_read, false); assert.equal(result.financial_results_computed, false);
});

test('sealed byte tampering is not silently refetched', async t => {
  const f = fixture(t, 1); const [row] = await download(f.input, f.options);
  fs.appendFileSync(row.raw_path, ' ');
  await assert.rejects(download(f.input, f.options), /sealed_source_changed/);
  assert.equal(f.calls.length, 1);
});

test('a re-frozen registration cannot reset the source attempt', async t => {
  const f = fixture(t, 1); await download(f.input, f.options);
  f.r.note = 'changed'; freeze(f.input, f.r);
  await assert.rejects(download(f.input, f.options), /resume_binding_changed/);
  assert.equal(f.calls.length, 1);
});

test('concurrent writer retains its lock', async t => {
  const f = fixture(t, 1); fs.mkdirSync(path.join(f.root, 'source'), {recursive: true});
  const lock = path.join(f.root, 'source/writer.lock'); fs.writeFileSync(lock, 'owner');
  await assert.rejects(download(f.input, f.options), /EEXIST/);
  assert.equal(fs.readFileSync(lock, 'utf8'), 'owner'); assert.equal(f.calls.length, 0);
});

test('manual resume retains per-URL calls and stops after three', async t => {
  const f = fixture(t, 1);
  f.fetcher.fetch = async urls => {f.calls.push(urls[0]); throw Error('fixture_interruption');};
  for (let i = 0; i < 3; i++) await assert.rejects(download(f.input, f.options), /fixture_interruption/);
  await assert.rejects(download(f.input, f.options), /per_URL_budget_exhausted/);
  assert.equal(f.calls.length, 3);
});

test('transient server failures use three total calls, retain failure count and block further calls', async t => {
  const f = fixture(t, 1);
  f.fetcher.fetch = async urls => {f.calls.push(urls[0]); throw Error('HTTP 503');};
  await assert.rejects(download(f.input, f.options), /503/);
  assert.equal(f.calls.length, 3);
  const state = JSON.parse(fs.readFileSync(path.join(f.root, 'source/source-state.json')));
  assert.equal(state.transient_failures, 3);
  await assert.rejects(download(f.input, f.options), /per_URL_budget_exhausted/);
  assert.equal(f.calls.length, 3);
});

for (const status of [401, 403, 429]) test(`HTTP ${status} stops without retry and blocks blind resume`, async t => {
  const f = fixture(t, 1);
  f.fetcher.fetch = async urls => {f.calls.push(urls[0]); throw Error(`HTTP ${status}`);};
  await assert.rejects(download(f.input, f.options), new RegExp(String(status)));
  await assert.rejects(download(f.input, f.options), /source_access_blocked/);
  assert.equal(f.calls.length, 1);
});

for (const statuses of [[503, 429], [429, 503]]) test(`mixed batch ${statuses.join('/')} preserves terminal block and drains siblings`, async t => {
  const f = fixture(t), urls = [...f.mapping.keys()];
  let inflight = 0;
  f.fetcher.fetch = async requested => {
    f.calls.push(requested[0]); inflight++;
    try {
      await new Promise(resolve => setImmediate(resolve));
      throw Error(`HTTP ${statuses[urls.indexOf(requested[0])]}`);
    } finally { inflight--; }
  };
  await assert.rejects(download(f.input, f.options), /HTTP 429/);
  assert.equal(inflight, 0, 'every pending request must settle before returning');
  const state = JSON.parse(fs.readFileSync(path.join(f.root, 'source/source-state.json')));
  assert.equal(state.blocked_source.reason, 'HTTP 429');
  const events = fs.readFileSync(path.join(f.root, 'source/events.jsonl'), 'utf8')
    .trim().split('\n').map(line => JSON.parse(line));
  const batch = events.find(row => row.stage === 'source_batch_failed');
  assert.equal(batch.failures.length, 2);
  assert(batch.failures.some(row => row.code === 'HTTP 429'));
  const beforeResume = f.calls.length;
  await assert.rejects(download(f.input, f.options), /source_access_blocked/);
  assert.equal(f.calls.length, beforeResume);
  assert.equal(f.calls.filter(url => url === urls[statuses.indexOf(429)]).length, 1);
});

test('a terminal response cancels a sibling transient retry before it calls the source', async t => {
  const f = fixture(t), urls = [...f.mapping.keys()];
  f.fetcher.fetch = async requested => {
    f.calls.push(requested[0]);
    throw Error(requested[0] === urls[0] ? 'HTTP 503' : 'HTTP 429');
  };
  await assert.rejects(download(f.input, f.options), /HTTP 429/);
  assert.deepEqual(f.calls, urls);
  await assert.rejects(download(f.input, f.options), /source_access_blocked/);
  assert.deepEqual(f.calls, urls);
});

test('expired attempt does not reset deadline on resume', async t => {
  const f = fixture(t, 1);
  f.fetcher.fetch = async urls => {f.calls.push(urls[0]); throw Error('fixture_interruption');};
  await assert.rejects(download(f.input, f.options), /fixture_interruption/);
  const file = path.join(f.root, 'source/source-state.json'), state = JSON.parse(fs.readFileSync(file));
  state.deadline_msc = 1; fs.writeFileSync(file, JSON.stringify(state));
  await assert.rejects(download(f.input, f.options), /attempt_budget_exhausted/);
  assert.equal(f.calls.length, 1);
});

test('junction output fails before network and keeps target untouched', async t => {
  const f = fixture(t, 1), outside = path.join(f.root, 'outside'); fs.mkdirSync(outside);
  fs.symlinkSync(outside, path.join(f.root, 'source'), 'junction');
  assert.throws(() => safeTree(path.join(f.root, 'source/cache')), /links_forbidden/);
  await assert.rejects(download(f.input, f.options), /links_forbidden/);
  assert.deepEqual(fs.readdirSync(outside), []); assert.equal(f.calls.length, 0);
});
