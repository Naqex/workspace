// Pinned native provider components; no browser/auth/WAF or global configuration.
const path = require('path');
const native = require(path.resolve(__dirname, '../../.runtime/research-data/node_modules/dukascopy-node'));
const pause = ms => new Promise(resolve => setTimeout(resolve, ms));

function transient(error) {
  return error.name === 'TimeoutError' ||
    ['UND_ERR_CONNECT_TIMEOUT', 'ETIMEDOUT'].includes(error.cause?.code) ||
    (error.name === 'Error' && /(?:status |HTTP )(500|502|503|504)\b/.test(error.message));
}

async function requestWithRecovery(fetcher, url, {budget, deadline, cancelled = () => false,
    onEvent = () => {}, sleep = pause}) {
  for (let attempt = 0; ; attempt++) {
    if (cancelled()) throw Error('data_preparation_cancelled');
    if (Date.now() >= deadline) throw Error('data_preparation_deadline');
    try {
      // One URL: the native fetcher validates and flushes this response to cache.
      return await fetcher.fetch([url]);
    } catch (error) {
      if (!transient(error)) throw error;
      budget.failures++;
      onEvent({stage: 'transient_request_failure', pathname: new URL(url).pathname,
        errorType: error.name, attempt: attempt + 1, cumulativeFailures: budget.failures});
      if (attempt >= 2 || budget.failures >= budget.maxFailures) throw error;
      await sleep(10000 * (attempt + 1));
    }
  }
}

async function getCachedM1(request, options) {
  if (request.timeframe !== 'm1' || request.ignoreFlats !== false ||
      request.wafMode !== 'off' || request.wafTokenCache !== false ||
      request.retryCount !== 0 || request.rateLimitRetryCount !== 0 || !request.useCache) {
    throw Error('explicit_unfiltered_cached_M1_no_hidden_retry_or_auth_required');
  }
  const checked = native.validateConfigNode(request);
  if (!checked.isValid) throw Error('invalid_provider_configuration');
  const input = checked.input;
  const [startDate, endDate] = native.normaliseDates({instrument: input.instrument,
    startDate: input.dates.from, endDate: input.dates.to,
    timeframe: input.timeframe, utcOffset: input.utcOffset});
  if (+endDate > Date.parse('2025-01-01T00:00:00Z')) throw Error('holdout_closed');
  const urls = native.generateUrls({instrument: input.instrument, timeframe: input.timeframe,
    priceType: input.priceType, startDate, endDate});
  const fetcher = new native.BufferFetcher({batchSize: 1, pauseBetweenBatchesMs: 0,
    requestIntervalMs: 300, rateLimitRetryCount: 0,
    cacheManager: new native.CacheManager({cacheFolderPath: input.cacheFolderPath}),
    retryCount: 0, retryOnEmpty: false, failAfterRetryCount: true,
    wafMode: 'off', wafTokenCache: false, wafTokenCachePath: input.wafTokenCachePath});
  const buffers = [];
  for (let index = 0; index < urls.length; index += 2) {
    const batchUrls=urls.slice(index,index+2);
    const outcomes = await Promise.allSettled(batchUrls.map(url => {
      if(options.knownUnavailable?.has(new URL(url).pathname)) {
        const error=new Error('Previously exhausted transient request; no new source call');
        error.name='KnownUnavailableRequest';
        return Promise.reject(error);
      }
      return requestWithRecovery(fetcher, url, options);
    }));
    // Drain the whole batch before reporting failure; no orphaned request writer.
    const batch = resolveBatch(batchUrls,outcomes,options);
    buffers.push(...batch);
    options.onEvent?.({stage: 'source_days_cached', completed: Math.min(index + 2, urls.length),
      total: urls.length, cacheHits: batch.filter(item => item.isCacheHit).length});
    if (index + 2 < urls.length && batch.some(item => !item.isCacheHit)) await pause(300);
  }
  const processed = native.processData({instrument: input.instrument, requestedTimeframe: 'm1',
    bufferObjects: buffers, priceType: input.priceType, volumes: input.volumes,
    volumeUnits: input.volumeUnits, ignoreFlats: false});
  return native.formatOutput({processedData: processed.filter(([time]) => time >= +startDate && time < +endDate),
    format: input.format, timeframe: 'm1'});
}

function resolveBatch(urls,outcomes,options) {
  const buffers=[];
  for(let index=0;index<outcomes.length;index++) {
    const result=outcomes[index];
    if(result.status==='fulfilled') {buffers.push(...result.value);continue;}
    const error=result.reason;
    if(options.allowTransientGaps===true &&
       (transient(error)||error.name==='KnownUnavailableRequest') &&
       typeof options.onUnavailable==='function') {
      options.onUnavailable({pathname:new URL(urls[index]).pathname,errorType:error.name,
        reason:error.message.includes('500')?'http500':'transport_unavailable',quoteRowsInvented:0});
      continue;
    }
    throw error;
  }
  return buffers;
}

module.exports = {getCachedM1, requestWithRecovery,resolveBatch};
