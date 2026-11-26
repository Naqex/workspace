"""Inspect inventoried MQL source/binaries once per content hash, never run them."""
from pathlib import Path
from collections import Counter
import hashlib,time
from prop_v24_common import *
from prop_v21_common import unpack
from quant_core.bot_lab import inspect_bytes

def run():
    with bindings(compression,JOB=JOB):inventory=unpack('connector-source-inventory')
    profiles={};rows=[];failures=[];started=time.perf_counter()
    for i,name in enumerate(inventory['bot_paths']):
        p=Path(name)
        try:
            if p.is_symlink() or p.stat().st_size>16*1024*1024:raise ValueError('SYMLINK_OR_SIZE_LIMIT')
            raw=p.read_bytes();digest=hashlib.sha256(raw).hexdigest();key=digest+p.suffix.lower()
            if key not in profiles:profiles[key]=inspect_bytes(raw,p.suffix.lower())
            rows.append(dict(path=name,profile=key,format=p.suffix.lower()))
        except (OSError,ValueError,SyntaxError,UnicodeError,RecursionError) as exc:failures.append(dict(path=name,status='UNVERIFIED',error_type=type(exc).__name__))
        if (i+1)%200==0:print(dict(inspected=i+1,total=len(inventory['bot_paths']),unique=len(profiles)),flush=True)
    manifest=compressed('inventoried-bot-static-profiles',dict(rows=rows,profiles=profiles,failures=failures,
        parser_sha256=sha('tooling/ai-engines/quant_core/bot_lab.py'),binary_parser_sha256=sha('tooling/ai-engines/quant_core/binary_bot_metadata.py'),
        no_executables_run=True,no_source_copied_into_Git=True))
    flags=Counter(f['flag'] for p in profiles.values() for f in p.get('findings',[]))
    save('inventoried-bot-static-summary.json',dict(paths=len(inventory['bot_paths']),readable_paths=len(rows),
        unique_content_profiles=len(profiles),failures=len(failures),formats=dict(Counter(r['format'] for r in rows)),
        flags=dict(flags),flags_are_heuristic_not_scam_convictions=True,manifest=manifest,seconds=time.perf_counter()-started))
    print(dict(paths=len(rows),profiles=len(profiles),failures=len(failures)))

if __name__=='__main__':run()
