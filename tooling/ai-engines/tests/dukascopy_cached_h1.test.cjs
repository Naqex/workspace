const {test}=require('node:test');
const assert=require('node:assert/strict');
const {explicitHours,getCachedH1,collectH1Buffers}=require('../dukascopy_cached_h1.cjs');
test('explicit H1 excludes omitted hours and keeps zero-volume listed hours',()=>{
  const raw={timestamp:0,shift:3600000,times:[0,2],opens:[0,1],highs:[0,1],lows:[0,1],closes:[0,1],volumes:[0,1]};
  assert.deepEqual(explicitHours(raw),[0,7200000]);
  assert.throws(()=>explicitHours({...raw,shift:60000}),/schema/);
  assert.throws(()=>explicitHours({...raw,times:[0,0]}),/order/);
});
test('partial H1 keeps known unavailable month explicit without fetching, strict mode rejects',async()=>{
  const url='https://jetta.dukascopy.com/v1/candles/hour/AUD-USD/ASK/2013/1';let calls=0;const unavailable=[];
  const fetcher={fetch:async()=>{calls++;return [{buffer:'observed'}];}};
  const options={knownUnavailable:new Set([new URL(url).pathname]),allowTransientGaps:true,onUnavailable:r=>unavailable.push(r),budget:{failures:0,maxFailures:3},deadline:Date.now()+10000};
  assert.deepEqual(await collectH1Buffers(fetcher,[url,url+'/next'],options),[{buffer:'observed'}]);
  assert.equal(calls,1);assert.equal(unavailable.length,1);assert.equal(unavailable[0].quoteRowsInvented,0);
  await assert.rejects(collectH1Buffers(fetcher,[url],{...options,allowTransientGaps:false}));
  const forbidden={fetch:async()=>{throw Error('HTTP 403');}};
  await assert.rejects(collectH1Buffers(forbidden,[url+'/auth'],options),/403/);
});
test('H1 requires explicit guard flags before any network',async()=>{
  await assert.rejects(getCachedH1({timeframe:'h1'},{}),/no_hidden_auth_or_retry/);
  const cfg={instrument:'gbpusd',timeframe:'h1',dates:{from:'2025-01-01',to:'2025-02-01'},ignoreFlats:false,
    wafMode:'off',wafTokenCache:false,retryCount:0,rateLimitRetryCount:0,useCache:true};
  const original=JSON.stringify(cfg);
  await assert.rejects(getCachedH1(cfg,{}),/holdout_closed/);
  assert.equal(JSON.stringify(cfg),original);
});
