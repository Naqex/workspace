"""Bounded metadata inventory; never treats absence of records as proof of unseen data."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re

SKIP_DIRS = {'.git', '.venv', 'node_modules', 'quantdatamanager', 'pgdata', 'pg-dist', '__pycache__'}
TAGS = ('manifest', 'inputs', 'registration', 'contract', 'preflight', 'receipt', 'session', 'review-source')
SKIP_NAMES = ('secret', 'credentials', 'auth', 'checkpoint', 'decisions', 'results', 'account-spec', 'spec.json')
PAIRS = (('first_day','last_day'), ('start_day','end_day'), ('start_date','end_date'),
         ('date_from','date_to'), ('start_utc','end_utc'), ('from_utc','to_utc'),
         ('start_time_msc','end_time_msc'), ('from_time_msc','to_time_msc'))
PRICE_KEYS = {'ticks','quotes','candles','bars','ledger','trades','results','messages','events'}


def day(value):
    if type(value) in (int,float):
        if not 0 <= value <= 4102444800000:
            return None
        if type(value) is int and 19000101 <= value <= 21001231:
            return day(str(value))
        return datetime.fromtimestamp(value if value <= 4102444800 else value/1000,
                                      timezone.utc).strftime('%Y%m%d')
    if not isinstance(value,str):
        return None
    prefix=value[:10].replace('-','').replace('.','')
    if not re.fullmatch(r'\d{8}',prefix):
        return None
    try:
        return datetime.strptime(prefix,'%Y%m%d').strftime('%Y%m%d')
    except ValueError:
        return None


def windows(value, context='', path='root'):
    found=[]
    if isinstance(value,dict):
        labels=' '.join(str(value.get(k,'')) for k in ('schema','engine','candidate','symbol','instrument_id','dataset_id'))
        context=(context+' '+labels).lower()
        if 'forex' in context or 'eurusd' in context:
            for first,last in PAIRS:
                if first in value and last in value:
                    a,b=day(value[first]),day(value[last])
                    if a and b and a <= b:
                        found.append(dict(path=path,first_day=a,last_day=b))
        for key,item in value.items():
            if key.lower() not in PRICE_KEYS and isinstance(item,(dict,list)):
                found.extend(windows(item,context,path+'.'+key))
    elif isinstance(value,list):
        for index,item in enumerate(value):
            if isinstance(item,(dict,list)):
                found.extend(windows(item,context,path+f'[{index}]'))
    return found


def audit(roots, *, max_bytes=2*1024*1024):
    records=[]; skipped=[]; inspected=0; seen=set()
    for root in roots:
        root=Path(root).resolve()
        if not root.is_dir():
            skipped.append(dict(path=str(root),reason='missing_root'))
            continue
        def walk_error(error):
            skipped.append(dict(path=str(error.filename or root),reason='unreadable_directory'))
        for directory,children,files in os.walk(root,followlinks=False,onerror=walk_error):
            allowed=[]
            for name in children:
                if name.lower() in SKIP_DIRS or name.lower().startswith('.venv'):
                    continue
                child=Path(directory,name)
                try:
                    within_root=child.resolve().is_relative_to(root)
                except OSError:
                    skipped.append(dict(path=str(child),reason='unreadable_directory_link'))
                    continue
                if not within_root:
                    skipped.append(dict(path=str(child),reason='external_directory_link_not_followed'))
                    continue
                allowed.append(name)
            children[:]=allowed
            for name in files:
                lower=name.lower()
                if not lower.endswith('.json') or not any(tag in lower for tag in TAGS) or any(tag in lower for tag in SKIP_NAMES):
                    continue
                path=Path(directory,name)
                try:
                    path=path.resolve()
                    if path in seen: continue
                    seen.add(path)
                    if not path.is_relative_to(root) or path.stat().st_size > max_bytes:
                        skipped.append(dict(path=str(path),reason='outside_root_or_size_limit'))
                        continue
                    data=path.read_bytes()
                    value=json.loads(data.decode('utf-8-sig'))
                except (OSError,ValueError,UnicodeError):
                    skipped.append(dict(path=str(path),reason='unreadable_metadata'))
                    continue
                inspected+=1
                context='forex' if any(tag in str(path).lower() for tag in ('forex','qdm','prop-strategy','prop-q1')) else ''
                ranges=windows(value,context)
                if not ranges: continue
                fixture=any(tag in str(path).lower() for tag in ('scenario-reuse-smoke','fixture'))
                schema=value.get('schema') if isinstance(value,dict) else None
                kind=('generated_fixture' if fixture else
                      'planned_registration_not_proof_of_price_exposure' if schema=='forex-historical-study-registration-v1' else
                      'registered_run' if schema=='forex-h4-development-v1' else 'exposure_or_metadata_review')
                records.append(dict(path=str(path),schema=value.get('schema') if isinstance(value,dict) else None,
                    metadata_sha256=hashlib.sha256(data).hexdigest(),kind=kind,windows=ranges))
    return dict(schema='research-consumption-audit-v1',inspected_at_utc=datetime.now(timezone.utc).isoformat(),
        roots=[str(Path(p).resolve()) for p in roots],metadata_files_inspected=inspected,records=records,
        review_required=skipped,price_series_traversed=False,outcome_values_exported=False,
        absence_of_records_proves_unseen=False,scope='configured_filesystem_metadata_only_not_external_or_unrecorded_history')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root',type=Path,action='append',required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    result=audit(args.root)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        json.dump(result,stream,indent=2)
    print(json.dumps(dict(inspected=result['metadata_files_inspected'],records=len(result['records']),
                         review_required=len(result['review_required']),unseen_proven=False)))


if __name__=='__main__': main()
