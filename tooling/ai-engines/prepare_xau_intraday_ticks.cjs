// Existing native provider/cache only; no auth, broker, fresh holdout or hidden retry.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const ws=path.resolve(__dirname,'../..');
const native=require(path.join(ws,'.runtime/research-data/node_modules/dukascopy-node'));
const {requestWithRecovery,checkResearchWindow}=require('./dukascopy_cached_m1.cjs');
const sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const source=process.argv[2],out=path.resolve(process.argv[3]);
const census=JSON.parse(fs.readFileSync(source,'utf8'));
const diagnostic=['XAU-A0-scale-horizon-census-v1','XAU-H1-stage0-census-v1'].includes(census.schema);
const scopeStart=Date.parse('2022-01-01T00:00:00Z');
const scopeEnd=Date.parse(diagnostic?'2024-01-01T00:00:00Z':'2025-01-01T00:00:00Z');
const reused=new Map((diagnostic?census.reused_hours:[]).map(r=>[r.at,r]));
const began=Date.now(),deadline=began+3600000;
const save=(name,v)=>{const p=path.join(out,name);fs.writeFileSync(p+'.tmp',JSON.stringify(v,null,2));fs.renameSync(p+'.tmp',p);};
fs.mkdirSync(out);fs.mkdirSync(path.join(out,'cache'));
let completed=0,seals=[],events=0;
const emit=(stage,extra={})=>{const v={sequence:++events,stage,utc:new Date().toISOString(),pid:process.pid,completed,total:census.hours.length,...extra};save('status.json',v);fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(v)+'\n');console.log(JSON.stringify(v));};
const check=()=>{if(Date.now()>deadline)throw Error('source_deadline');if(fs.existsSync(path.join(out,'CANCEL')))throw Error('source_cancelled');};
const fetcher=new native.BufferFetcher({batchSize:1,pauseBetweenBatchesMs:0,requestIntervalMs:300,
 cacheManager:new native.CacheManager({cacheFolderPath:path.join(out,'cache')}),retryCount:0,rateLimitRetryCount:0,retryOnEmpty:false,failAfterRetryCount:true,wafMode:'off',wafTokenCache:false});
const budget={failures:0,maxFailures:16};
(async()=>{try{
 if(census.schema!=='XAU-A0-signal-census-v1'&&!diagnostic)throw Error('unregistered_census');
 if(new Set(census.hours).size!==census.hours.length||census.hours.some(at=>!Number.isSafeInteger(at)||at%3600000))throw Error('invalid_hour_census');
 if(diagnostic&&(census.scope_start!==scopeStart||census.scope_end_exclusive!==scopeEnd))throw Error('unregistered_diagnostic_scope');
 const requests=census.hours.map(at=>{
  const start=new Date(at),end=new Date(at+3600000);checkResearchWindow('xauusd',start,end);
  if(at<scopeStart||+end>scopeEnd)throw Error('XAU_closed_source_window');
  const urls=native.generateUrls({instrument:'xauusd',timeframe:'tick',priceType:'bid',startDate:start,endDate:end});
  if(urls.length!==1)throw Error('one_hour_URL_required');return{at,url:urls[0]};
 });
 save('registration.json',{source,census_sha256:sha(fs.readFileSync(source)),producer_sha256:sha(fs.readFileSync(__filename)),native_sha256:sha(fs.readFileSync(path.join(ws,'.runtime/research-data/node_modules/dukascopy-node/dist/index.js'))),requests});
 emit('registered');
 for(let i=0;i<requests.length;i+=2){
  check();const batch=requests.slice(i,i+2);
  const settled=await Promise.allSettled(batch.map(async r=>{
   const inherited=reused.get(r.at);
   if(inherited){
    const buffer=fs.readFileSync(inherited.rawPath);
    if(sha(buffer)!==inherited.sha256)throw Error('parent_raw_changed');
    const payload=JSON.parse(buffer.toString('utf8'));
    if(payload.timestamp!==r.at||payload.multiplier!==.001||payload.times.length!==inherited.records)throw Error('parent_raw_identity');
    return{...inherited,cache_hit:true,inherited_parent:true};
   }
   const buffers=await requestWithRecovery(fetcher,r.url,{budget,deadline,cancelled:()=>fs.existsSync(path.join(out,'CANCEL')),onEvent:e=>emit(e.stage,e)});
   if(buffers.length!==1)throw Error('one_hour_raw_buffer_required');
   const b=buffers[0],payload=JSON.parse(b.buffer.toString('utf8'));
   if(payload.multiplier!==.001||payload.timestamp!==r.at)throw Error('XAU_tick_grid_or_clock');
   const pathname=new URL(b.url).pathname;
   const rawPath=path.join(out,'cache',encodeURIComponent(pathname.replace(/^\/v1\//,''))+'.json');
   if(sha(fs.readFileSync(rawPath))!==sha(b.buffer))throw Error('raw_cache_binding');
   return{at:r.at,rawPath,sha256:sha(b.buffer),records:payload.times.length,cache_hit:Boolean(b.isCacheHit)};
  }));
  const failed=settled.find(s=>s.status==='rejected');
  for(const s of settled)if(s.status==='fulfilled'){seals.push(s.value);completed++;}
  save('sealed-hours.json',seals);
  if(failed)throw failed.reason;
  emit('hours_sealed',{last_hour:new Date(batch.at(-1).at).toISOString()});
  if(settled.some(s=>s.status==='fulfilled'&&!s.value.cache_hit))await new Promise(r=>setTimeout(r,300));
 }
 save('result.json',{status:'source_collected_pending_price_review',hours:seals,wall_seconds:(Date.now()-began)/1000,source_sha256:sha(fs.readFileSync(source)),new_holdout:false});emit('completed');
}catch(e){save('failure.json',{type:e.name,code:e.message,sealed:completed,wall_seconds:(Date.now()-began)/1000});emit('failed');process.exitCode=1;}})();
