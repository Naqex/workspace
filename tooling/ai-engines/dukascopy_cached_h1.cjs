// Opt-in source H1 fixture using pinned native components; existing M1 contract stays unchanged.
const path=require('path');
const crypto=require('crypto');
const native=require(path.resolve(__dirname,'../../.runtime/research-data/node_modules/dukascopy-node'));
const {requestWithRecovery}=require('./dukascopy_cached_m1.cjs');

function explicitHours(data) {
  const columns=['times','opens','highs','lows','closes','volumes'].map(k=>data[k]);
  if(!Number.isSafeInteger(data.timestamp)||data.timestamp%3600000||data.shift!==3600000||
      columns.some(c=>!Array.isArray(c))||columns.some(c=>c.length!==columns[0].length))throw Error('explicit_H1_schema');
  let stamp=data.timestamp;
  return data.times.map((delta,i)=>{
    if(!Number.isSafeInteger(delta)||delta<0||(i>0&&delta===0))throw Error('explicit_H1_order');
    stamp+=delta*3600000;
    if(!Number.isSafeInteger(stamp))throw Error('explicit_H1_time_range');
    return stamp;
  });
}

async function getCachedH1(request,options) {
  if(request.timeframe!=='h1'||request.ignoreFlats!==false||request.wafMode!=='off'||request.wafTokenCache!==false||
      request.retryCount!==0||request.rateLimitRetryCount!==0||request.useCache!==true)throw Error('explicit_H1_no_hidden_auth_or_retry');
  const checked=native.validateConfigNode(request);
  if(!checked.isValid)throw Error('invalid_provider_configuration');
  const input=checked.input;
  const [startDate,endDate]=native.normaliseDates({instrument:input.instrument,startDate:input.dates.from,endDate:input.dates.to,timeframe:'h1',utcOffset:0});
  if(+startDate<Date.parse('2010-01-01T00:00:00Z')||+endDate>Date.parse('2025-01-01T00:00:00Z'))throw Error('registered_H1_historical_scope_holdout_closed');
  const urls=native.generateUrls({instrument:input.instrument,timeframe:'h1',priceType:input.priceType,startDate,endDate});
  const fetcher=new native.BufferFetcher({batchSize:1,pauseBetweenBatchesMs:0,requestIntervalMs:300,
    cacheManager:new native.CacheManager({cacheFolderPath:input.cacheFolderPath}),retryCount:0,rateLimitRetryCount:0,
    retryOnEmpty:false,failAfterRetryCount:true,wafMode:'off',wafTokenCache:false,wafTokenCachePath:input.wafTokenCachePath});
  const buffers=[];
  for(const url of urls){
    buffers.push(...await requestWithRecovery(fetcher,url,options));
    options.onEvent?.({stage:'source_month_cached',completed:buffers.length,total:urls.length});
  }
  const explicit=new Set();
  const sources=buffers.map(({url,buffer})=>{
    for(const at of explicitHours(JSON.parse(buffer.toString('utf8')))){
      if(explicit.has(at))throw Error('overlapping_H1_source');explicit.add(at);
    }
    return {pathname:new URL(url).pathname,sha256:crypto.createHash('sha256').update(buffer).digest('hex')};
  });
  const decoded=native.processData({instrument:input.instrument,requestedTimeframe:'h1',bufferObjects:buffers,
    priceType:input.priceType,volumes:true,volumeUnits:'millions',ignoreFlats:false});
  const nativeRows=decoded.filter(([at])=>at>=+startDate&&at<+endDate);
  const selected=nativeRows.filter(([at])=>explicit.has(at));
  options.onSource?.({sources,nativeRows:nativeRows.length,selectedRows:selected.length,paddingExcluded:nativeRows.length-selected.length,
    sourcePolicy:'explicit_source_H1_only',observedTickTimestamps:false,periodExposure:'whole_month_raw_response'});
  return selected.map(([timestamp,open,high,low,close,volume])=>({timestamp,open,high,low,close,volume}));
}
module.exports={getCachedH1,explicitHours};
