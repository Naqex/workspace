const {test}=require('node:test');
const assert=require('node:assert/strict');
const {explicitHours,getCachedH1}=require('../dukascopy_cached_h1.cjs');
test('explicit H1 excludes omitted hours and keeps zero-volume listed hours',()=>{
  const raw={timestamp:0,shift:3600000,times:[0,2],opens:[0,1],highs:[0,1],lows:[0,1],closes:[0,1],volumes:[0,1]};
  assert.deepEqual(explicitHours(raw),[0,7200000]);
  assert.throws(()=>explicitHours({...raw,shift:60000}),/schema/);
  assert.throws(()=>explicitHours({...raw,times:[0,0]}),/order/);
});
test('H1 requires explicit guard flags before any network',async()=>{
  await assert.rejects(getCachedH1({timeframe:'h1'},{}),/no_hidden_auth_or_retry/);
  const cfg={instrument:'gbpusd',timeframe:'h1',dates:{from:'2025-01-01',to:'2025-02-01'},ignoreFlats:false,
    wafMode:'off',wafTokenCache:false,retryCount:0,rateLimitRetryCount:0,useCache:true};
  await assert.rejects(getCachedH1(cfg,{}),/holdout_closed/);
});
