// Bounded native tick intake for the frozen atlas's missing Development roles.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const native=require(path.resolve(__dirname,'../../.runtime/research-data/node_modules/dukascopy-node'));
const {requestWithRecovery}=require('./dukascopy_cached_m1.cjs');
const input=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]);
const census=JSON.parse(fs.readFileSync(input)),sha=b=>crypto.createHash('sha256').update(b).digest('hex');
const allowed={US500:['usa500idxusd',.001],GBPUSD:['gbpusd',.00001],AUDUSD:['audusd',.00001]};
const from=Date.parse('2022-01-01Z'),end=Date.parse('2024-01-01Z'),began=Date.now(),deadline=began+3600000;
const jobs=[];
for(const [asset,hours] of Object.entries(census)){
 if(!allowed[asset]||new Set(hours).size!==hours.length)throw Error('unregistered_endpoint_asset');
 for(const at of hours){
  if(!Number.isSafeInteger(at)||at%3600000||at<from||at+3600000>end)throw Error('closed_endpoint_window');
  const [instrument,multiplier]=allowed[asset];
  const urls=native.generateUrls({instrument,timeframe:'tick',priceType:'bid',startDate:new Date(at),endDate:new Date(at+3600000)});
  if(urls.length!==1)throw Error('one_native_hour_required');
  jobs.push({asset,at,instrument,multiplier,url:urls[0]});
 }
}
fs.mkdirSync(out);fs.mkdirSync(path.join(out,'cache'));
const save=(name,r)=>{const p=path.join(out,name);fs.writeFileSync(p+'.tmp',JSON.stringify(r,null,2));fs.renameSync(p+'.tmp',p);};
let n=0,seq=0,seals=[];
const emit=(stage,fields={})=>{const r={stage,sequence:++seq,utc:new Date().toISOString(),pid:process.pid,completed:n,total:jobs.length,...fields};save('status.json',r);fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(r)+'\n');console.log(JSON.stringify(r));};
const fetcher=new native.BufferFetcher({batchSize:1,pauseBetweenBatchesMs:0,requestIntervalMs:300,
 cacheManager:new native.CacheManager({cacheFolderPath:path.join(out,'cache')}),
 retryCount:0,rateLimitRetryCount:0,retryOnEmpty:false,failAfterRetryCount:true,wafMode:'off',wafTokenCache:false});
const budget={failures:0,maxFailures:20};
(async()=>{try{
 save('registration.json',{census_sha256:sha(fs.readFileSync(input)),producer_sha256:sha(fs.readFileSync(__filename)),jobs,
  purpose:'resolve exact missing endpoint, unchanged structural catalog',prices2024_2026_read:false});
 emit('registered');
 for(let i=0;i<jobs.length;i+=2){
  if(Date.now()>deadline||fs.existsSync(path.join(out,'CANCEL')))throw Error('source_deadline_or_cancel');
  const r=await Promise.allSettled(jobs.slice(i,i+2).map(async j=>{
   const buffers=await requestWithRecovery(fetcher,j.url,{budget,deadline,cancelled:()=>fs.existsSync(path.join(out,'CANCEL')),onEvent:e=>emit(e.stage,e)});
   if(buffers.length!==1)throw Error('one_tick_hour_buffer_required');
   const b=buffers[0],p=JSON.parse(b.buffer.toString());
   if(p.timestamp!==j.at||p.multiplier!==j.multiplier)throw Error('tick_clock_or_grid');
   const rawPath=path.join(out,'cache',encodeURIComponent(new URL(b.url).pathname.replace(/^\/v1\//,''))+'.json');
   if(sha(fs.readFileSync(rawPath))!==sha(b.buffer))throw Error('raw_cache_binding');
   return{...j,rawPath,sha256:sha(b.buffer),records:p.times.length,cache_hit:!!b.isCacheHit};
  }));
  for(const v of r)if(v.status==='fulfilled'){seals.push(v.value);n++;}
  save('sealed-hours.json',seals);
  if(r.some(v=>v.status==='rejected'))throw r.find(v=>v.status==='rejected').reason;
  if(i%20===0)emit('hours_sealed');
  await new Promise(r=>setTimeout(r,300));
 }
 save('result.json',{hours:seals,wall_seconds:(Date.now()-began)/1000});emit('completed');
}catch(e){save('failure.json',{type:e.name,code:e.message,sealed:n});emit('failed');process.exitCode=1;}})();
