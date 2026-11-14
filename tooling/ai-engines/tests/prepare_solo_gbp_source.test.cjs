const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {validHour, validateRaw, boundedRequests, download} = require('../prepare_solo_gbp_source.cjs');
const native = require(path.resolve(__dirname, '../../../.runtime/research-data/node_modules/dukascopy-node'));
const HOUR = 3600000;
const at = Date.parse('2022-01-04T08:00:00Z');
const raw = hour => ({timestamp: hour, multiplier: .00001, bid: 1.2, ask: 1.2001,
  times: [1, 0], bids: [0, 1], asks: [0, 1], bidVolumes: [1, 2], askVolumes: [1, 2]});

function fixture(t, hours = [at, at + HOUR]) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'solo-gbp-source-'));
  t.after(() => {
    const relative = path.relative(path.resolve(os.tmpdir()), path.resolve(root));
    assert(!relative.startsWith('..') && !path.isAbsolute(relative));
    assert(path.basename(root).startsWith('solo-gbp-source-'));
    fs.rmSync(root, {recursive: true, force: true});
  });
  const input = path.join(root, 'registration.json');
  const registration = {schema: 'solo-gbp-source-v1', cell: 'GBPUSD.SWEEP.ASIA.LONDON.DAY',
    job_root: root, window: {first: Date.parse('2022-01-01Z'), end_exclusive: Date.parse('2024-01-01Z')},
    hours, missing_hours: hours, reused: {}, input_pins: [], producer_pins: [],
    prices2024_2026_read: false, new_financial_outcomes_computed: false,
    source_budget: {concurrency: 2, pause_ms: 300, transient_failures: 20,
      max_calls_per_url: 3, deadline_seconds: 7200}};
  fs.writeFileSync(input, JSON.stringify(registration));
  const calls = [];
  const mapping = new Map(hours.map(hour => [native.generateUrls({instrument: 'gbpusd',
    timeframe: 'tick', priceType: 'bid', startDate: new Date(hour), endDate: new Date(hour + HOUR)})[0], hour]));
  const fetcher = {fetch: async urls => {
    calls.push(urls[0]);
    const buffer = Buffer.from(JSON.stringify(raw(mapping.get(urls[0]))));
    const cache = path.join(root, 'source/cache');
    const name = encodeURIComponent(new URL(urls[0]).pathname.replace(/^\/v1\//, '')) + '.json';
    fs.writeFileSync(path.join(cache, name), buffer);
    return [{url: urls[0], buffer, isCacheHit: false}];
  }};
  return {root, input, calls, mapping, fetcher};
}

test('validation and incomplete raw timestamps fail before fetching', () => {
  assert.throws(() => validHour(Date.parse('2024-01-01Z')), /Development/);
  assert.throws(() => validHour(at + 1), /Development/);
  const value = raw(at);
  value.times[1] = HOUR;
  assert.throws(() => validateRaw(value, at), /outside_hour/);
  assert.doesNotThrow(() => validateRaw(raw(at), at));
});

test('resume preserves successful sibling, sealed bytes and same request budget', async t => {
  const f = fixture(t);
  const failedUrl = [...f.mapping.keys()][1];
  let fail = true;
  const real = f.fetcher.fetch;
  f.fetcher.fetch = async urls => {
    if (urls[0] === failedUrl && fail) {
      f.calls.push(urls[0]);
      throw Error('fixture_interruption');
    }
    return real(urls);
  };
  const options = {fetcher: f.fetcher, sleep: async () => {}, quiet: true};
  await assert.rejects(download(f.input, options), /fixture_interruption/);
  const sealedFile = path.join(f.root, 'source/sealed-hours.json');
  const first = JSON.parse(fs.readFileSync(sealedFile));
  assert.equal(first.length, 1);
  const immutable = fs.readFileSync(first[0].raw_path);
  fail = false;
  const resumed = await download(f.input, options);
  assert.equal(resumed.length, 2);
  assert.deepEqual(fs.readFileSync(first[0].raw_path), immutable);
  assert.equal(f.calls.filter(url => url !== failedUrl).length, 1);
  assert.equal(f.calls.filter(url => url === failedUrl).length, 2);
  const prior = f.calls.length;
  await download(f.input, options);
  assert.equal(f.calls.length, prior);
  assert.equal(fs.readFileSync(path.join(f.root, 'source/failures.jsonl'), 'utf8').split('\n').filter(Boolean).length, 1);
});

test('tampered sealed source is not silently refetched', async t => {
  const f = fixture(t, [at]);
  const options = {fetcher: f.fetcher, sleep: async () => {}, quiet: true};
  const [seal] = await download(f.input, options);
  fs.appendFileSync(seal.raw_path, ' ');
  await assert.rejects(download(f.input, options), /sealed_source_changed/);
  assert.equal(f.calls.length, 1);
});

test('changed registration cannot reuse completed attempt', async t => {
  const f = fixture(t, [at]);
  const options = {fetcher: f.fetcher, sleep: async () => {}, quiet: true};
  await download(f.input, options);
  const value = JSON.parse(fs.readFileSync(f.input));
  value.note = 'changed frozen request';
  fs.writeFileSync(f.input, JSON.stringify(value));
  await assert.rejects(download(f.input, options), /resume_binding_changed/);
  assert.equal(f.calls.length, 1);
});

test('a concurrent writer is refused without taking its lock', async t => {
  const f = fixture(t, [at]);
  fs.mkdirSync(path.join(f.root, 'source'), {recursive: true});
  const lock = path.join(f.root, 'source/writer.lock');
  fs.writeFileSync(lock, 'another-owned-process');
  await assert.rejects(download(f.input, {fetcher: f.fetcher, quiet: true}), /EEXIST/);
  assert.equal(fs.readFileSync(lock, 'utf8'), 'another-owned-process');
  assert.equal(f.calls.length, 0);
});

test('manual resume cannot reset the per-URL call budget', async t => {
  const f = fixture(t, [at]);
  f.fetcher.fetch = async urls => {
    f.calls.push(urls[0]);
    throw Error('fixture_interruption');
  };
  const options = {fetcher: f.fetcher, sleep: async () => {}, quiet: true};
  for (let count = 0; count < 3; count++) {
    await assert.rejects(download(f.input, options), /fixture_interruption/);
  }
  await assert.rejects(download(f.input, options), /per_URL_budget_exhausted/);
  assert.equal(f.calls.length, 3);
});

test('an in-flight failure reserves the last global failure slot', async () => {
  let calls = 0;
  const state = {calls: {}};
  const fetcher = boundedRequests({fetch: async () => {
    calls++;
    await new Promise(resolve => setImmediate(resolve));
    throw Error('fixture_failure');
  }}, state, {failures: 19, maxFailures: 20}, () => {});
  const result = await Promise.allSettled([
    fetcher.fetch(['https://example.invalid/one']),
    fetcher.fetch(['https://example.invalid/two'])]);
  assert.equal(calls, 1);
  assert.equal(result[1].reason.message, 'S01_inflight_failure_budget_limit');
});
