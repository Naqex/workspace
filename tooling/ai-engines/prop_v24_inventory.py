"""Metadata/source-signature inventory. Never emits credential values or opens DBs."""
from pathlib import Path
import os,re,time,subprocess
from prop_v24_common import *

SKIP={'.git','node_modules','.venv','venv','target','dist','build','__pycache__','.next'}
SOURCE={'.py','.rs','.cs','.mq4','.mq5','.pine','.ps1','.toml','.ini','.json','.yaml','.yml','.env','.bat','.cmd'}
MATCH=re.compile(r'MetaTrader5|FTMO|TW_V2_MT5|terminal_path|mt5_connector|cTrader|mt5_login',re.I)
ENV=re.compile(r'(?m)^\s*(?:export\s+)?([A-Z][A-Z0-9_]*(?:MT5|FTMO|BROKER|LOGIN|PASSWORD|SERVER|TERMINAL)[A-Z0-9_]*)\s*=')

def inventory():
    started=time.perf_counter();hits=[];bots=[];errors=[];large=0;seen=0
    roots=[Path('D:/ANNAM/TradingWorkspace'),Path('E:/BACKUP-TRADINGWORKSPACE')]
    for root in roots:
        def error(exc):errors.append(dict(path=str(exc.filename),type=type(exc).__name__))
        args=['rg','--files','--hidden','--no-ignore','--maxdepth','18',str(root)]
        for pattern in ('*.py','*.rs','*.cs','*.mq4','*.mq5','*.pine','*.ex4','*.ex5','*.ps1','*.toml','*.ini','*.json','*.yaml','*.yml','.env*','*.env','*.bat','*.cmd'):args+=['-g',pattern]
        for name in sorted(SKIP):args+=['-g','!**/'+name+'/**']
        print('Enumerating '+str(root),flush=True)
        proc=subprocess.Popen(args,stdout=subprocess.PIPE,stderr=subprocess.DEVNULL,text=True,encoding='utf-8')
        for line in proc.stdout:
                p=Path(line.strip());name=p.name;suffix=p.suffix.lower()
                if suffix in ('.mq4','.mq5','.pine','.ex4','.ex5'):bots.append(str(p))
                isenv=name.startswith('.env') or name.endswith('.env')
                if suffix not in SOURCE and not isenv:continue
                seen+=1
                try:
                    if p.is_symlink():continue
                    size=p.stat().st_size
                    if size>524288:large+=1;continue
                    raw=p.read_bytes();text=raw.decode('utf-16' if raw.startswith((b'\xff\xfe',b'\xfe\xff')) else 'utf-8-sig',errors='replace')
                    keys=sorted(set(ENV.findall(text)))
                    if MATCH.search(text) or keys:
                        hits.append(dict(path=str(p),bytes=size,credential_key_names_only=keys,
                            signatures=sorted({m.group(0) for m in MATCH.finditer(text)})[:12],values_disclosed=False))
                except (OSError,ValueError) as exc:errors.append(dict(path=str(p),type=type(exc).__name__))
                if seen%10000==0:print(dict(candidate_files=seen,matches=len(hits),seconds=time.perf_counter()-started),flush=True)
        if proc.wait() not in (0,1):errors.append(dict(path=str(root),type='RG_TRAVERSAL_ERROR'))
    history={}
    for label,path in (('workspace','.'),('Trader','projects/trader')):
        args=['git','-C',path,'log','--all','--format=%h %s','--max-count=45','--regexp-ignore-case','--extended-regexp','--grep=MT5|connector|broker']
        lines=subprocess.check_output(args,text=True,encoding='utf-8').splitlines()
        history[label]=[re.sub(r'\b\d{6,}\b','[REDACTED_ID]',s) for s in lines]
    compressed('connector-source-inventory',dict(roots=[str(p) for p in roots],candidate_files=seen,matches=hits,
        bot_paths=bots,errors=errors,skipped_large_candidate_files=large,pruned_generated_directories=sorted(SKIP),
        history=history,seconds=time.perf_counter()-started,contents_or_credentials_not_exported=True,
        source_read_only=True,DPAPI_secrets_not_decrypted=True))
    save('connector-inventory-summary.json',dict(candidate_files=seen,matches=len(hits),bot_paths=len(bots),
        errors=len(errors),skipped_large=large,seconds=time.perf_counter()-started,max_scan_depth=18,generated_directories_pruned=True))
    print(dict(candidate_files=seen,matches=len(hits),bots=len(bots),errors=len(errors)))

if __name__=='__main__':inventory()
