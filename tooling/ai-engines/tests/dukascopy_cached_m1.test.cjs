const test = require('node:test');
const assert = require('node:assert/strict');
const {requestWithRecovery, getCachedM1} = require('../dukascopy_cached_m1.cjs');
const url = 'https://datafeed.dukascopy.com/v1/candles/minute/fixture';

async function fixture(errors, initial = 6, cancel = false) {
  let calls = 0;
  const waits = [], budget = {failures: initial, maxFailures: 24};
  const fetcher = {fetch: async () => {
    const failure = errors[calls++];
    if (failure) {const error = new Error(failure.message || 'fixture'); error.name = failure.name || 'Error'; throw error;}
    return ['ok'];
  }};
  let failed;
  try {await requestWithRecovery(fetcher, url, {budget, deadline: Date.now() + 10000,
    cancelled: () => cancel, sleep: async ms => waits.push(ms)});} catch (error) {failed = error;}
  return {calls, waits, budget, failed};
}

test('timeout and 5xx recover only the same day within two retries', async () => {
  const result = await fixture([{name: 'TimeoutError'}, {message: 'Request failed with status 503'}]);
  assert.equal(result.calls, 3);
  assert.deepEqual(result.waits, [10000, 20000]);
  assert.equal(result.budget.failures, 8);
  assert.equal(result.failed, undefined);
});

for (const failure of [{message: 'Request failed with status 403'},
  {message: 'Request failed with status 429'}, {message: 'Request failed with status 501'},
  {name: 'WafChallengeError', message: 'HTTP 503'}, {name: 'SyntaxError'}]) {
  test(`does not retry ${failure.message || failure.name}`, async () => {
    const result = await fixture([failure]);
    assert.equal(result.calls, 1);
    assert.equal(result.waits.length, 0);
    assert(result.failed);
  });
}

test('per-day retry and cumulative error caps cannot be reset by the caller loop', async () => {
  const result = await fixture(Array(4).fill({name: 'TimeoutError'}));
  assert.equal(result.calls, 3);
  assert(result.failed);
  const limit = await fixture([{name: 'TimeoutError'}], 23);
  assert.equal(limit.calls, 1);
  assert.equal(limit.budget.failures, 24);
  assert(limit.failed);
});

test('cancel and unsafe loader defaults stop before source access', async () => {
  const result = await fixture([], 6, true);
  assert.equal(result.calls, 0);
  assert(result.failed);
  await assert.rejects(getCachedM1({timeframe: 'm1'}, {}), /explicit_unfiltered/);
});
