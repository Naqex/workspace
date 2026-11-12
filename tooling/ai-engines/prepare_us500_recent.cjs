// Finite source-only import for the owner's named 2025-2026 research window.
const fs=require('fs'),path=require('path'),crypto=require('crypto');
const {getCachedM1}=require('./dukascopy_cached_m1.cjs');
const args=Object.fromEntries(process.argv.slice(2).reduce((out,v,i,a)=>{
  if(v.startsWith('--')) out.push([v.slice(2),a[i+1]&&!a[i+1].startsWith('--')?a[i+1]:true]);return out;
},[]));
const out=path.resolve(args.output),protocol=path.resolve(args.protocol);
const sha=p=>crypto.createHash('sha256').update(fs.readFileSync(p)).digest('hex');
if(sha(protocol)!==args['protocol-sha256'])throw Error('recent_source_protocol_binding');
fs.mkdirSync(out,{recursive:false});
const cache=path.resolve(args.cache);fs.mkdirSync(cache,{recursive:true});
const grant={id:'us500-recent-discovery-20261112',instrument:'usa500idxusd',
  from:'2025-01-01T00:00:00Z',to:'2026-11-12T00:00:00Z'};
const lock=path.join(out,'controller.lock');fs.writeFileSync(lock,String(process.pid),{flag:'wx'});
const start=Date.now(),deadline=start+1200000,budget={failures:0,maxFailures:24};
const pins=Object.fromEntries([__filename,path.join(__dirname,'dukascopy_cached_m1.cjs'),protocol,
  path.resolve(__dirname,'../../.runtime/research-data/node_modules/dukascopy-node/package.json')].map(p=>[p,sha(p)]));
const save=(name,value)=>{const p=path.join(out,name),temp=p+'.tmp';fs.writeFileSync(temp,JSON.stringify(value,null,2)+'\n');fs.renameSync(temp,p);};
let seq=0;const rows=[];
function progress(stage,fields={}){
  if(fs.existsSync(path.join(out,'CANCEL')))throw Error('recent_source_cancelled');
  if(Date.now()>deadline)throw Error('recent_source_deadline');
  const e={stage,sequence:++seq,pid:process.pid,at_utc:new Date().toISOString(),elapsed_seconds:(Date.now()-start)/1000,...fields};
  fs.appendFileSync(path.join(out,'events.jsonl'),JSON.stringify(e)+'\n');save('progress.json',e);
  fs.writeFileSync(path.join(out,'PROGRESS.md'),'# Recent US500 source import\n\n'+JSON.stringify(e,null,2)+'\n');
  if(stage!=='source_days_cached'||fields.completed%20===0||fields.completed===fields.total)process.stdout.write(JSON.stringify(e)+'\n');
}
const windows=[];
if(args.smoke){for(const day of ['2025-02-03','2026-11-10']){
  const end=new Date(Date.parse(day)+86400000).toISOString();windows.push({id:day,from:day+'T00:00:00.000Z',to:end});
}}else{
  for(let y=2025;y<=2026;y++)for(let m=0;m<12;m++){
    const from=new Date(Date.UTC(y,m,1)),to=new Date(Math.min(Date.UTC(y,m+1,1),Date.parse(grant.to)));
    if(+from<+to)windows.push({id:`${y}-${String(m+1).padStart(2,'0')}`,from:from.toISOString(),to:to.toISOString()});
  }
}
save('manifest.json',{schema:'us500-recent-source-import-v1',grant,protocol_sha256:sha(protocol),source_pins:pins,
  windows,source_only:true,strategy_simulated:false,broker_calls:0,model_calls:0});
(async()=>{try{
  for(const w of windows)for(const side of ['bid','ask']){
    progress('fetching_window',{window:w.id,side});let provenance;
    const request={instrument:'usa500idxusd',timeframe:'m1',format:'json',priceType:side,volumes:true,
      useCache:true,cacheFolderPath:cache,ignoreFlats:false,retryCount:0,rateLimitRetryCount:0,
      retryOnEmpty:false,failAfterRetryCount:true,wafMode:'off',wafTokenCache:false,
      wafTokenCachePath:path.join(out,'unused-token.json'),dates:{from:w.from,to:w.to}};
    const data=await getCachedM1(request,{researchWindow:grant,sourceCandlesOnly:true,budget,deadline,
      cancelled:()=>fs.existsSync(path.join(out,'CANCEL')),onEvent:e=>progress(e.stage,{...e,window:w.id,side}),
      onSourceProvenance:e=>{provenance=e;}});
    if(!Array.isArray(data)||!provenance||data.length!==provenance.explicitRows)throw Error('recent_source_explicit_census');
    const name=`${w.id}-${side}.json`;save(name,data);save(`${w.id}-${side}-provenance.json`,provenance);
    rows.push({window:w.id,side,from:w.from,to:w.to,path:name,rows:data.length,sha256:sha(path.join(out,name)),
      provenance_sha256:sha(path.join(out,`${w.id}-${side}-provenance.json`))});save('completed-requests.json',rows);
  }
  if(Object.entries(pins).some(([p,s])=>sha(p)!==s))throw Error('recent_source_pin_drift');
  save('result.json',{status:'source_import_completed_needs_independent_price_validation',rows,
    elapsed_seconds:(Date.now()-start)/1000,transient_failures:budget.failures,strategy_simulated:false});
  progress('completed_source_import',{requests:rows.length});
}catch(error){save('failure.json',{stage:'source_import',error_type:error.name,code:error.message,completed_requests:rows.length});
  progress('failed',{error_type:error.name,code:error.message});process.exitCode=1;
}finally{fs.rmSync(lock,{force:true});}})();
