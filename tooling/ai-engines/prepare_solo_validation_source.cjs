// S03 source collection only; Python owns the committed release and cohort gate.
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const {execFileSync} = require('node:child_process');
const {requestWithRecovery} = require('./dukascopy_cached_m1.cjs');
const {boundedRequests} = require('./prepare_solo_gbp_source.cjs');
const workspace = path.resolve(__dirname, '../..');
const nativeRoot = path.join(workspace, '.runtime/research-data/node_modules/dukascopy-node');
const native = require(nativeRoot);
const python = 'E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research-python/Scripts/python.exe';
const START = 1704067200000, END = 1735689600000, HOUR = 3600000;
const CELL = 'GBPUSD.SWEEP.ASIA.LONDON.DAY';
const sha = value => crypto.createHash('sha256').update(value).digest('hex');
const fileHash = file => sha(fs.readFileSync(file));
const read = file => JSON.parse(fs.readFileSync(file, 'utf8'));
const sleep = ms => new Promise(resolve => setTimeout(resolve, ms));

function canonical(value) {
  if (Array.isArray(value)) return '[' + value.map(canonical).join(',') + ']';
  if (value && typeof value === 'object') return '{' + Object.keys(value).sort()
    .map(key => JSON.stringify(key) + ':' + canonical(value[key])).join(',') + '}';
  if (typeof value === 'number' && !Number.isFinite(value)) throw Error('S03_nonfinite_json');
  return JSON.stringify(value);
}

function safeTree(target) {
  for (let item = path.resolve(target);;) {
    try {
      if (fs.lstatSync(item).isSymbolicLink()) throw Error('S03_output_links_forbidden');
    } catch (error) { if (error.code !== 'ENOENT') throw error; }
    const parent = path.dirname(item);
    if (parent === item) return;
    item = parent;
  }
}

function save(file, value) {
  safeTree(file); safeTree(file + '.tmp');
  fs.writeFileSync(file + '.tmp', JSON.stringify(value, null, 2) + '\n');
  fs.renameSync(file + '.tmp', file);
}

function append(file, value) {
  safeTree(file);
  fs.appendFileSync(file, JSON.stringify(value) + '\n');
}

function validHour(at) {
  if (!Number.isSafeInteger(at) || at % HOUR || at < START || at + HOUR > END) {
    throw Error('S03_2024_hour_required');
  }
}

function accessBlocked(error) {
  return [401, 403, 429].includes(Number(error.status ?? error.statusCode)) ||
    /(?:status\s*|HTTP\s*)(?:401|403|429)\b|\b(?:authentication|rate.?limit|waf)\b/i.test(error.message);
}

function verifyRegistrationFile(input, pythonExecutable = python) {
  const output = execFileSync(pythonExecutable, [path.join(__dirname, 'solo_validation_source.py'),
    'verify-registration', '--registration', input],
  {cwd: workspace, encoding: 'utf8', shell: false, timeout: 120000, maxBuffer: 1048576,
    stdio: ['ignore', 'pipe', 'pipe']});
  const receipt = JSON.parse(output);
  if (receipt.verified !== true || receipt.source_only !== true ||
      receipt.registration_sha256 !== fileHash(input) || typeof receipt.job_root !== 'string') {
    throw Error('S03_registration_verifier_receipt');
  }
  return receipt;
}

function validateRegistration(r, input, receipt) {
  if (!receipt || receipt.verified !== true || receipt.source_only !== true ||
      receipt.registration_sha256 !== fileHash(input) ||
      path.resolve(receipt.job_root) !== path.dirname(input) ||
      r.schema !== 'solo-validation-gbp-source-v1' || r.cell !== CELL ||
      r.window?.first !== START || r.window?.end_exclusive !== END ||
      r.prices2025_2026_read !== false || r.financial_results_computed !== false ||
      path.resolve(r.job_root) !== path.dirname(input)) throw Error('S03_registration_scope');
  const unsigned = {...r}; delete unsigned.registration_sha256;
  if (sha(canonical(unsigned)) !== r.registration_sha256) throw Error('S03_registration_self_binding');
  const expected = new Set(), identities = new Set();
  if (!Array.isArray(r.signals)) throw Error('S03_signal_census');
  for (const signal of r.signals) {
    const at = signal.decision_msc, end = signal.deadline_msc;
    validHour(at);
    const key = `${at}:${signal.side}`;
    if (signal.id !== CELL || signal.asset !== 'GBPUSD' ||
        !['BUY', 'SELL'].includes(signal.side) || !Number.isSafeInteger(signal.stop_units) ||
        signal.stop_units <= 0 || !Number.isSafeInteger(end) || end <= at || end + 60000 >= END ||
        identities.has(key)) throw Error('S03_signal_census');
    identities.add(key);
    for (let hour = at; hour <= Math.floor(end / HOUR) * HOUR; hour += HOUR) expected.add(hour);
  }
  const hours = [...expected].sort((a, b) => a - b);
  if (!Array.isArray(r.hours) || canonical(hours) !== canonical(r.hours)) throw Error('S03_hour_census');
  hours.forEach(validHour);
  if (!Array.isArray(r.missing_hours) || !r.reused || Array.isArray(r.reused) ||
      new Set(r.missing_hours).size !== r.missing_hours.length ||
      r.missing_hours.some(at => !expected.has(at) || r.reused[String(at)]) ||
      Object.keys(r.reused).some(key => String(Number(key)) !== key || !expected.has(Number(key))) ||
      hours.some(at => !r.missing_hours.includes(at) && !r.reused[String(at)])) {
    throw Error('S03_missing_reuse_partition');
  }
  const budget = r.source_budget;
  if (budget?.concurrency !== 2 || budget.pause_ms !== 300 || budget.transient_failures !== 20 ||
      budget.max_calls_per_url !== 3 || budget.deadline_seconds !== 7200) throw Error('S03_source_budget_changed');
  if (!Array.isArray(r.input_pins) || !Array.isArray(r.producer_pins) ||
      !r.producer_pins.some(pin => path.resolve(pin.path) === __filename && pin.sha256 === fileHash(__filename))) {
    throw Error('S03_downloader_producer_pin_required');
  }
  for (const pin of [...r.input_pins, ...r.producer_pins, r.release_pin]) {
    if (!pin || fileHash(pin.path) !== pin.sha256) throw Error('S03_frozen_pin_changed');
  }
  if (read(path.join(nativeRoot, 'package.json')).version !== '1.51.1') throw Error('S03_native_version_changed');
  safeTree(r.job_root);
}

function validateRaw(raw, at) {
  validHour(at);
  if (raw.timestamp !== at || raw.multiplier !== .00001 || !Array.isArray(raw.times) ||
      !Number.isFinite(raw.bid) || !Number.isFinite(raw.ask) || raw.bid <= 0 || raw.ask < raw.bid) {
    throw Error('S03_raw_hour_or_price_grid');
  }
  let stamp = at;
  for (const delta of raw.times) {
    if (!Number.isSafeInteger(delta) || delta < 0) throw Error('S03_raw_tick_clock');
    stamp += delta;
    if (!Number.isSafeInteger(stamp) || stamp >= at + HOUR) throw Error('S03_raw_tick_outside_hour');
  }
  for (const key of ['bids', 'asks', 'bidVolumes', 'askVolumes']) {
    if (!Array.isArray(raw[key]) || raw[key].length !== raw.times.length ||
        raw[key].some(value => !Number.isFinite(value))) throw Error('S03_raw_tick_shape');
  }
  if (raw.bids.some(value => !Number.isSafeInteger(value)) ||
      raw.asks.some(value => !Number.isSafeInteger(value))) throw Error('S03_raw_tick_grid');
}

function readSeals(file, expected, cache) {
  safeTree(file);
  const seals = fs.existsSync(file) ? read(file) : [];
  const seen = new Set();
  for (const row of seals) {
    const relative = path.relative(cache, path.resolve(row.raw_path));
    if (seen.has(row.at) || !expected.includes(row.at) || relative.startsWith('..') ||
        path.isAbsolute(relative)) throw Error('S03_sealed_source_scope');
    safeTree(row.raw_path);
    if (fileHash(row.raw_path) !== row.raw_sha256) throw Error('S03_sealed_source_changed');
    const raw = read(row.raw_path);
    validateRaw(raw, row.at);
    if (raw.times.length !== row.records) throw Error('S03_sealed_tick_census_changed');
    seen.add(row.at);
  }
  return seals;
}

async function download(input, dependencies = {}) {
  input = path.resolve(input);
  // No mkdir/cache/network occurs until the committed Python release gate succeeds.
  const receipt = (dependencies.verify || verifyRegistrationFile)(input);
  const r = read(input);
  validateRegistration(r, input, receipt);
  const out = path.join(r.job_root, 'source'), cache = path.join(out, 'cache');
  safeTree(cache); fs.mkdirSync(cache, {recursive: true});
  const lock = path.join(out, 'writer.lock'); safeTree(lock);
  const lockFd = fs.openSync(lock, 'wx');
  fs.writeFileSync(lockFd, JSON.stringify({pid: process.pid, input_sha256: fileHash(input)}));
  const stateFile = path.join(out, 'source-state.json'), sealedFile = path.join(out, 'sealed-hours.json');
  let state;
  try {
    safeTree(stateFile);
    const binding = fileHash(input);
    if (fs.existsSync(stateFile)) {
      state = read(stateFile);
      if (state.registration_sha256 !== binding || state.producer_sha256 !== fileHash(__filename)) {
        throw Error('S03_resume_binding_changed');
      }
      if (state.blocked_source) throw Error('S03_source_access_blocked_requires_review');
    } else {
      state = {registration_sha256: binding, producer_sha256: fileHash(__filename),
        started_at_utc: new Date().toISOString(), deadline_msc: Date.now() + 7200000,
        calls: {}, transient_failures: 0, sequence: 0};
      save(stateFile, state);
    }
    const seals = readSeals(sealedFile, r.missing_hours, cache);
    const done = new Set(seals.map(row => row.at));
    const pending = r.missing_hours.filter(at => !done.has(at));
    const emit = (stage, fields = {}) => {
      const event = {stage, sequence: ++state.sequence, utc: new Date().toISOString(),
        pid: process.pid, sealed: seals.length, expected: r.missing_hours.length, ...fields};
      save(path.join(out, 'status.json'), event); append(path.join(out, 'events.jsonl'), event);
      save(stateFile, state);
      if (!dependencies.quiet) console.log(JSON.stringify(event));
    };
    if (pending.length && (Date.now() >= state.deadline_msc || state.transient_failures >= 20)) {
      throw Error('S03_attempt_budget_exhausted_requires_new_attempt');
    }
    const fetcher = dependencies.fetcher || new native.BufferFetcher({batchSize: 1,
      pauseBetweenBatchesMs: 0, requestIntervalMs: 300,
      cacheManager: new native.CacheManager({cacheFolderPath: cache}), retryCount: 0,
      rateLimitRetryCount: 0, retryOnEmpty: false, failAfterRetryCount: true,
      wafMode: 'off', wafTokenCache: false});
    const budget = {failures: state.transient_failures, maxFailures: 20};
    const blockSource = error => {
      if (!state.blocked_source) {
        state.blocked_source = {at_utc: new Date().toISOString(), reason: error.message.slice(0, 500)};
        save(stateFile, state);
      }
    };
    // Mark the terminal response when it arrives, before a sibling can retry.
    const accessGuard = {fetch: async urls => {
      if (state.blocked_source) throw Error('S03_source_access_blocked_requires_review');
      try { return await fetcher.fetch(urls); }
      catch (error) {
        if (accessBlocked(error)) blockSource(error);
        throw error;
      }
    }};
    const bounded = boundedRequests(accessGuard, state, budget, () => save(stateFile, state));
    emit('registered_source_resumed', {pending: pending.length});
    for (let offset = 0; offset < pending.length; offset += 2) {
      const results = await Promise.allSettled(pending.slice(offset, offset + 2).map(async at => {
        validHour(at);
        const urls = native.generateUrls({instrument: 'gbpusd', timeframe: 'tick', priceType: 'bid',
          startDate: new Date(at), endDate: new Date(at + HOUR)});
        if (urls.length !== 1) throw Error('S03_one_tick_hour_required');
        const rawPath = path.join(cache, encodeURIComponent(new URL(urls[0]).pathname.replace(/^\/v1\//, '')) + '.json');
        safeTree(rawPath);
        const buffers = await requestWithRecovery(bounded, urls[0], {budget, deadline: state.deadline_msc,
          sleep: dependencies.sleep || sleep,
          cancelled: () => !!state.blocked_source || fs.existsSync(path.join(r.job_root, 'CANCEL')),
          onEvent: event => {state.transient_failures = budget.failures; emit(event.stage, event);}});
        if (buffers.length !== 1 || buffers[0].url !== urls[0]) throw Error('S03_source_URL_binding');
        const buffer = buffers[0], raw = JSON.parse(buffer.buffer.toString());
        validateRaw(raw, at);
        safeTree(rawPath);
        if (fileHash(rawPath) !== sha(buffer.buffer)) throw Error('S03_cache_byte_binding');
        return {at, raw_path: rawPath, raw_sha256: sha(buffer.buffer), records: raw.times.length,
          url: buffer.url, cache_hit: !!buffer.isCacheHit};
      }));
      for (const result of results) if (result.status === 'fulfilled') seals.push(result.value);
      seals.sort((a, b) => a.at - b.at); save(sealedFile, seals);
      const failures = results.filter(row => row.status === 'rejected').map(row => row.reason);
      const terminal = failures.find(accessBlocked);
      if (terminal) blockSource(terminal);
      state.transient_failures = budget.failures; save(stateFile, state);
      if (failures.length) {
        emit('source_batch_failed', {failures: failures.map(error => ({
          type: error.name, code: error.message.slice(0, 500)}))});
        throw terminal || failures[0];
      }
      if (offset % 20 === 0) emit('hours_sealed');
      await (dependencies.sleep || sleep)(300);
    }
    save(path.join(out, 'result.json'), {status: 'SOURCE_DOWNLOADED_NOT_ADMITTED',
      registration_sha256: binding, downloaded_hours: seals.length, reused_hours: Object.keys(r.reused).length,
      source_only: true, prices2025_2026_read: false, financial_results_computed: false});
    emit('completed'); return seals;
  } catch (error) {
    if (state && !state.blocked_source && accessBlocked(error)) {
      state.blocked_source = {at_utc: new Date().toISOString(), reason: error.message.slice(0, 500)};
    }
    append(path.join(out, 'failures.jsonl'), {utc: new Date().toISOString(), type: error.name,
      code: error.message.slice(0, 500), source_stage_only: true});
    if (state) save(stateFile, state);
    throw error;
  } finally { fs.closeSync(lockFd); fs.unlinkSync(lock); }
}

module.exports = {canonical, validHour, validateRaw, validateRegistration, verifyRegistrationFile,
  readSeals, safeTree, download};
if (require.main === module) {
  if (process.argv.length !== 3) {
    console.error('Usage: node prepare_solo_validation_source.cjs <registered S03 source registration.json>');
    process.exitCode = 1;
  } else download(process.argv[2]).catch(error => {console.error(error.message); process.exitCode = 1;});
}
