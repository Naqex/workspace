"""Bind new source-only imports to Decimal raw decoding; never evaluate a strategy."""
import argparse
from collections import defaultdict
from datetime import datetime
import json
from pathlib import Path
import time
from urllib.parse import quote

from candle_source_provenance import inspect_expansion
from sealed_m1_review import digest, validate_rows, paired_spreads, cash_sessions
from run_us500_multiframe import save


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--import-root',type=Path,required=True)
    p.add_argument('--cache',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(); a.output.mkdir(exist_ok=False)
    began=time.perf_counter();bindings={}
    def read(path):
        bindings[str(path.resolve())]=digest(path)
        return json.loads(path.read_text(encoding='utf-8'))
    imported=read(a.import_root/'result.json'); manifest=read(a.import_root/'manifest.json')
    if (imported['status']!='source_import_completed_needs_independent_price_validation'
        or manifest['grant']['id']!='us500-recent-discovery-20261112' or len(imported['rows'])!=46):
        raise ValueError('recent_import_completed_census_required')
    rows=[]
    for window in manifest['windows']:
        name=window['id']; byside=[]
        for side in ('bid','ask'):
            rec=next(x for x in imported['rows'] if x['window']==name and x['side']==side)
            f=a.import_root/rec['path'];pr=a.import_root/f'{name}-{side}-provenance.json'
            if digest(f)!=rec['sha256'] or digest(pr)!=rec['provenance_sha256']:
                raise ValueError('recent_import_file_binding')
            native=read(f); prov=read(pr);groups=defaultdict(list)
            for r in native: groups[r['timestamp']//86400000].append(r)
            count=0
            for s in prov['sources']:
                rawpath=a.cache/(quote(s['pathname'].split('/v1/')[1],safe='')+'.json')
                if digest(rawpath)!=s['sha256']:raise ValueError('recent_raw_source_binding')
                raw=read(rawpath);day=raw['timestamp']//86400000
                checked=inspect_expansion(raw,groups.pop(day,[]),require_complete=False)
                if checked['padding_stamps'] or checked['unrepresented_explicit_rows']:
                    raise ValueError('recent_raw_native_price_volume_census')
                count+=len(checked['explicit_rows'])
            if groups or count!=len(native):raise ValueError('recent_raw_day_census')
            byside.append({r['timestamp']:r for r in native})
        common=sorted(byside[0].keys()&byside[1].keys())
        paired=[[side[t] for t in common] for side in byside]
        if not common:raise ValueError('recent_empty_month')
        lower=int(datetime.fromisoformat(window['from'].replace('Z','+00:00')).timestamp()*1000)
        upper=int(datetime.fromisoformat(window['to'].replace('Z','+00:00')).timestamp()*1000)
        for data in paired:validate_rows(data,lower,upper,.001)
        paired_spreads(*paired)
        unpaired={s:[data[t] for t in sorted(data.keys()-set(common))] for s,data in zip(('bid','ask'),byside)}
        save(a.output/f'{name}-unpaired.json',unpaired)
        for side,data in zip(('bid','ask'),paired):
            f=a.output/f'{name}-{side}.json';save(f,data)
            rows.append(dict(window=name,year=int(name[:4]),side=side,path=f.name,rows=len(data),sha256=digest(f)))
        print(json.dumps(dict(stage='month_validated',window=name,paired_rows=len(common),
            unpaired={s:len(v) for s,v in unpaired.items()},elapsed_seconds=round(time.perf_counter()-began,2))),flush=True)
    calendars={}
    for year in (2025,2026):
        f=Path(__file__).with_name('fixtures')/f'nyse-{year}.json';cal=read(f)
        save(a.output/f'nyse-{year}.json',cal);calendars[str(year)]=digest(a.output/f'nyse-{year}.json')
    if any(digest(Path(n))!=s for n,s in bindings.items()):raise ValueError('recent_source_drift')
    save(a.output/'source-proof.json',dict(schema='owner-authorized-recent-source-v1',status='raw_native_paired_prices_verified',
        grant=manifest['grant'],rows=rows,input_bindings=bindings,calendars=calendars,
        validator_sha256=digest(Path(__file__)),decoder_sha256=digest(Path(__file__).with_name('candle_source_provenance.py')),
        strategy_evaluated=False,wall_seconds=time.perf_counter()-began))


if __name__=='__main__':main()
