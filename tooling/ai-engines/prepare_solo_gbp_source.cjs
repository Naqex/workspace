// S01's frozen GBP held hours only. The parent census and prices are read-only.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const nativeRoot = path.resolve(__dirname, '../../.runtime/research-data/node_modules/dukascopy-node');
const native = require(nativeRoot);
const {requestWithRecovery} = require('./dukascopy_cached_m1.cjs');
const START = Date.parse('2022-01-01T00:00:00Z');
const END = Date.parse('2024-01-01T00:00:00Z');
const HOUR = 3600000;
const sha = bytes => crypto.createHash('sha256').update(bytes).digest('hex');
const fileHash = file => sha(fs.readFileSync(file));
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function save(file, value) {
  fs.writeFileSync(file + '.tmp', JSON.stringify(value, null, 2) + '\n');
  fs.renameSync(file + '.tmp', file);
}

function safeTree(target) {
  let item = path.resolve(target);
  for (;;) {
    if (fs.existsSync(item) && fs.lstatSync(item).isSymbolicLink()) {
      throw Error('S01_output_links_forbidden');
    }
    const parent = path.dirname(item);
    if (parent === item) break;
    item = parent;
  }
}

function validHour(at) {
  if (!Number.isSafeInteger(at) || at % HOUR || at < START || at + HOUR > END) {
    throw Error('S01_Development_hour_required');
  }
}

function validateRegistration(registration, input) {
  if (registration.schema !== 'solo-gbp-source-v1' ||
      registration.cell !== 'GBPUSD.SWEEP.ASIA.LONDON.DAY' ||
      registration.window.first !== START || registration.window.end_exclusive !== END ||
      registration.prices2024_2026_read !== false ||
      registration.new_financial_outcomes_computed !== false ||
      path.resolve(registration.job_root) !== path.dirname(path.resolve(input))) {
    throw Error('S01_registration_scope');
  }
  const all = registration.hours;
  if (!Array.isArray(all) || new Set(all).size !== all.length ||
      all.some((at, index) => index && at <= all[index - 1])) throw Error('S01_hour_census');
  all.forEach(validHour);
  const missing = registration.missing_hours;
  if (!Array.isArray(missing) || new Set(missing).size !== missing.length ||
      missing.some(at => !all.includes(at) || registration.reused[String(at)]) ||
      all.some(at => !missing.includes(at) && !registration.reused[String(at)])) {
    throw Error('S01_missing_reuse_partition');
  }
  const budget = registration.source_budget;
  if (budget.concurrency !== 2 || budget.pause_ms !== 300 || budget.transient_failures !== 20 ||
      budget.max_calls_per_url !== 3 || budget.deadline_seconds !== 7200) {
    throw Error('S01_source_budget_changed');
  }
  for (const pin of [...registration.input_pins, ...registration.producer_pins]) {
    if (fileHash(pin.path) !== pin.sha256) throw Error('S01_frozen_input_or_producer_changed');
  }
  if (read(path.join(nativeRoot, 'package.json')).version !== '1.51.1') {
    throw Error('S01_native_version_changed');
  }
  safeTree(registration.job_root);
}

function validateRaw(raw, at) {
  validHour(at);
  if (raw.timestamp !== at || raw.multiplier !== 0.00001 || !Array.isArray(raw.times)) {
    throw Error('S01_raw_hour_or_price_grid');
  }
  let atTick = at;
  for (const delta of raw.times) {
    if (!Number.isSafeInteger(delta) || delta < 0) throw Error('S01_raw_tick_clock');
    atTick += delta;
    if (!Number.isSafeInteger(atTick) || atTick >= at + HOUR) throw Error('S01_raw_tick_outside_hour');
  }
  for (const key of ['bids', 'asks', 'bidVolumes', 'askVolumes']) {
    if (!Array.isArray(raw[key]) || raw[key].length !== raw.times.length) throw Error('S01_raw_tick_shape');
  }
}

function readSeals(file, expected, cache) {
  const seals = fs.existsSync(file) ? read(file) : [];
  const seen = new Set();
  for (const row of seals) {
    const relative = path.relative(cache, path.resolve(row.raw_path));
    if (seen.has(row.at) || !expected.includes(row.at) || relative.startsWith('..') ||
        path.isAbsolute(relative) || fileHash(row.raw_path) !== row.raw_sha256) {
      throw Error('S01_sealed_source_changed');
    }
    safeTree(row.raw_path);
    const raw = read(row.raw_path);
    validateRaw(raw, row.at);
    if (raw.times.length !== row.records) throw Error('S01_sealed_tick_census_changed');
    seen.add(row.at);
  }
  return seals;
}

function boundedRequests(fetcher, state, budget, persist) {
  let inflight = 0;
  return {fetch: async urls => {
    // Every pending request can still fail. Reserve that room before retrying.
    if (budget.failures + inflight >= budget.maxFailures) {
      throw Error('S01_inflight_failure_budget_limit');
    }
    const key = new URL(urls[0]).pathname;
    if ((state.calls[key] || 0) >= 3) throw Error('S01_per_URL_budget_exhausted');
    state.calls[key] = (state.calls[key] || 0) + 1;
    persist();
    inflight++;
    try {
      return await fetcher.fetch(urls);
    } finally {
      inflight--;
    }
  }};
}

async function download(input, dependencies = {}) {
  input = path.resolve(input);
  const registration = read(input);
  validateRegistration(registration, input);
  const out = path.join(registration.job_root, 'source');
  const cache = path.join(out, 'cache');
  safeTree(cache);
  fs.mkdirSync(cache, {recursive: true});
  const lock = path.join(out, 'writer.lock');
  const lockFd = fs.openSync(lock, 'wx');
  fs.writeFileSync(lockFd, JSON.stringify({pid: process.pid, input_sha256: fileHash(input)}));
  const stateFile = path.join(out, 'source-state.json');
  const sealedFile = path.join(out, 'sealed-hours.json');
  let state;
  try {
    const binding = fileHash(input);
    if (fs.existsSync(stateFile)) {
      state = read(stateFile);
      if (state.registration_sha256 !== binding || state.producer_sha256 !== fileHash(__filename)) {
        throw Error('S01_resume_binding_changed');
      }
    } else {
      state = {registration_sha256: binding, producer_sha256: fileHash(__filename),
        started_at_utc: new Date().toISOString(), deadline_msc: Date.now() + 7200000,
        calls: {}, transient_failures: 0, sequence: 0};
      save(stateFile, state);
    }
    const seals = readSeals(sealedFile, registration.missing_hours, cache);
    const done = new Set(seals.map(row => row.at));
    const pending = registration.missing_hours.filter(at => !done.has(at));
    const emit = (stage, fields = {}) => {
      const event = {stage, sequence: ++state.sequence, utc: new Date().toISOString(),
        pid: process.pid, sealed: seals.length, expected: registration.missing_hours.length, ...fields};
      save(path.join(out, 'status.json'), event);
      fs.appendFileSync(path.join(out, 'events.jsonl'), JSON.stringify(event) + '\n');
      save(stateFile, state);
      if (!dependencies.quiet) console.log(JSON.stringify(event));
    };
    if (pending.length && (Date.now() >= state.deadline_msc || state.transient_failures >= 20)) {
      throw Error('S01_attempt_budget_exhausted_requires_explicit_new_attempt');
    }
    const fetcher = dependencies.fetcher || new native.BufferFetcher({
      batchSize: 1, pauseBetweenBatchesMs: 0, requestIntervalMs: 300,
      cacheManager: new native.CacheManager({cacheFolderPath: cache}), retryCount: 0,
      rateLimitRetryCount: 0, retryOnEmpty: false, failAfterRetryCount: true,
      wafMode: 'off', wafTokenCache: false});
    const budget = {failures: state.transient_failures, maxFailures: 20};
    const boundedFetcher = boundedRequests(fetcher, state, budget, () => save(stateFile, state));
    emit('registered_source_resumed', {pending: pending.length});
    for (let offset = 0; offset < pending.length; offset += 2) {
      const results = await Promise.allSettled(pending.slice(offset, offset + 2).map(async at => {
        validHour(at);
        const urls = native.generateUrls({instrument: 'gbpusd', timeframe: 'tick', priceType: 'bid',
          startDate: new Date(at), endDate: new Date(at + HOUR)});
        if (urls.length !== 1) throw Error('S01_one_tick_hour_required');
        const buffers = await requestWithRecovery(boundedFetcher, urls[0], {
          budget, deadline: state.deadline_msc, sleep: dependencies.sleep || sleep,
          cancelled: () => fs.existsSync(path.join(registration.job_root, 'CANCEL')),
          onEvent: event => {state.transient_failures = budget.failures; emit(event.stage, event);},
        });
        if (buffers.length !== 1) throw Error('S01_one_buffer_required');
        const buffer = buffers[0];
        if (buffer.url !== urls[0]) throw Error('S01_source_URL_binding');
        validateRaw(JSON.parse(buffer.buffer.toString()), at);
        const rawPath = path.join(cache,
          encodeURIComponent(new URL(buffer.url).pathname.replace(/^\/v1\//, '')) + '.json');
        if (fileHash(rawPath) !== sha(buffer.buffer)) throw Error('S01_cache_byte_binding');
        return {at, raw_path: rawPath, raw_sha256: sha(buffer.buffer),
          records: JSON.parse(buffer.buffer.toString()).times.length,
          url: buffer.url, cache_hit: !!buffer.isCacheHit};
      }));
      for (const result of results) if (result.status === 'fulfilled') seals.push(result.value);
      seals.sort((a, b) => a.at - b.at);
      save(sealedFile, seals);
      state.transient_failures = budget.failures;
      save(stateFile, state);
      if (results.some(row => row.status === 'rejected')) {
        throw results.find(row => row.status === 'rejected').reason;
      }
      if (offset % 20 === 0) emit('hours_sealed');
      await (dependencies.sleep || sleep)(300);
    }
    save(path.join(out, 'result.json'), {status: 'SOURCE_DOWNLOADED_NOT_ADMITTED',
      registration_sha256: binding, hours: seals.length, raw_prices2024_2026_read: false,
      financial_results_computed: false});
    emit('completed');
    return seals;
  } catch (error) {
    const failure = {utc: new Date().toISOString(), type: error.name,
      code: error.message.slice(0, 500), source_stage_only: true};
    fs.appendFileSync(path.join(out, 'failures.jsonl'), JSON.stringify(failure) + '\n');
    if (state) save(stateFile, state);
    throw error;
  } finally {
    fs.closeSync(lockFd);
    fs.unlinkSync(lock);
  }
}

module.exports = {validHour, validateRaw, validateRegistration, readSeals, boundedRequests, download};
if (require.main === module) {
  if (process.argv.length !== 3) {
    console.error('Usage: node prepare_solo_gbp_source.cjs <committed-producer registration.json>');
    process.exitCode = 1;
  } else {
    download(process.argv[2]).catch(error => {
      console.error(error.message);
      process.exitCode = 1;
    });
  }
}
