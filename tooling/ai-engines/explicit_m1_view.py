"""Create a source-bound paired US500 M1 view from sealed exports and local raw cache."""
from collections import defaultdict
from datetime import datetime,timezone
import argparse,json,os
from pathlib import Path
import time

from candle_source_provenance import inspect_expansion
from sealed_m1_review import digest,review,paired_spreads

POLICY='paired-explicit-source-M1-v1'
PROOF_SCHEMA='explicit-source-M1-proof-v1'


def read(path):
    return json.loads(Path(path).read_text(encoding='utf8'))


def save(path,value):
    with Path(path).open('x',encoding='utf8') as stream:
        json.dump(value,stream,ensure_ascii=False,indent=2,allow_nan=False)
        stream.write('\n')


def cache_path(request,day):
    if request['instrument']!='usa500idxusd':
        raise ValueError('unregistered_explicit_source_instrument')
    date=datetime.fromtimestamp(day/1000,timezone.utc)
    name='candles%2Fminute%2FUSA500.IDX-USD%2F'+request['priceType'].upper()+f'%2F{date.year}%2F{date.month}%2F{date.day}.json'
    return Path(request['cacheFolderPath'])/name


def prepare(parent,calendar_path,protocol,output, *, progress=None,deadline_seconds=900):
    parent,calendar_path,protocol,output=map(Path,(parent,calendar_path,protocol,output))
    began,cpu=time.monotonic(),time.process_time()
    calendar=read(calendar_path)
    if calendar['year'] not in range(2013,2025):
        raise ValueError('unregistered_source_year_holdout_closed')
    if not protocol.is_file() or deadline_seconds<=0:
        raise ValueError('protocol_or_deadline_required')
    output.mkdir(exist_ok=False)
    lock=output/'controller.lock';lock.write_text(str(os.getpid()))
    sources=[Path(__file__),Path(__file__).with_name('candle_source_provenance.py'),
             Path(__file__).with_name('sealed_m1_review.py'),protocol,calendar_path]
    pins={str(path.resolve()):digest(path) for path in sources}
    (output/'source-snapshot').mkdir()
    for index,path in enumerate(sources):
        (output/'source-snapshot'/f'{index}-{path.name}').write_bytes(path.read_bytes())
    bindings={}
    quarters=[];seals=[]

    def emit(stage,**fields):
        value=dict(stage=stage,pid=os.getpid(),year=calendar['year'],utc=datetime.now(timezone.utc).isoformat(),
                   elapsed_seconds=time.monotonic()-began,**fields)
        try:(output/'progress.json').write_text(json.dumps(value,indent=2)+'\n',encoding='utf8')
        except OSError:pass
        if progress:progress(value)

    def check():
        if (output/'CANCEL').exists() or time.monotonic()-began>=deadline_seconds:
            raise RuntimeError('source_view_cancel_or_deadline')
        if any(digest(Path(path))!=sha for path,sha in pins.items()):
            raise RuntimeError('source_view_code_or_protocol_changed')

    def bind(path,expected=None):
        path=Path(path).resolve()
        sha=digest(path)
        if expected is not None and sha!=expected:
            raise ValueError('parent_changed_after_validation')
        if str(path) in bindings and bindings[str(path)]!=sha:
            raise ValueError('source_input_changed_during_preparation')
        bindings[str(path)]=sha

    try:
        emit('validating_parent_seals')
        quality=review(parent,calendar_path,.001)
        manifest=read(parent/'manifest.json')
        if quality['instrument']!='usa500idxusd' or manifest.get('sourceObservationPolicy') is not None:
            raise ValueError('requires_legacy_index_parent_not_already_transformed')
        bind(parent/'manifest.json',quality['manifest_sha256'])
        bind(parent/'result.json',quality['download_result_sha256'])
        for q in range(1,5):
            check();side_rows=[];side_reports=[]
            for side in ('bid','ask'):
                stem=f'q{q}-{side}'
                request=manifest['requests'][2*(q-1)+(side=='ask')]
                data_path=parent/f'{stem}.json'
                expected=next(seal for seal in quality['source_seals'] if seal['request']==stem)
                bind(data_path,expected['sha256']);bind(parent/f'{stem}-seal.json')
                if read(parent/f'{stem}-seal.json')!=expected:
                    raise ValueError('parent_seal_changed_after_validation')
                days=defaultdict(list)
                for row in read(data_path):days[row['timestamp']//86400000*86400000].append(row)
                explicit=[];padding=missing=0;responses=[]
                for index,(day,rows) in enumerate(sorted(days.items())):
                    check()
                    raw_path=cache_path(request,day)
                    if not raw_path.is_file():raise ValueError('source_cache_required_no_network_fallback')
                    bind(raw_path)
                    raw=read(raw_path)
                    inspected=inspect_expansion(raw,rows,require_complete=False)
                    explicit.extend(inspected['explicit_rows'])
                    padding+=len(inspected['padding_stamps'])
                    missing+=inspected['unrepresented_explicit_rows']
                    responses.append(dict(path=str(raw_path.resolve()),sha256=bindings[str(raw_path.resolve())],
                        native_rows=len(rows),explicit_rows=len(inspected['explicit_rows']),
                        removed_padding=len(inspected['padding_stamps']),
                        unrepresented_explicit_rows=inspected['unrepresented_explicit_rows']))
                    if index%15==0:emit('binding_raw_source',quarter=q,side=side,days=index+1,total_days=len(days))
                side_rows.append(explicit)
                side_reports.append(dict(side=side,native_rows=sum(len(v) for v in days.values()),
                    explicit_rows=len(explicit),removed_padding=padding,unrepresented_explicit_rows=missing,responses=responses))
            left,right=({row['timestamp']:row for row in values} for values in side_rows)
            common=set(left)&set(right)
            paired=[[row for row in rows if row['timestamp'] in common] for rows in side_rows]
            unpaired={side:[row for row in rows if row['timestamp'] not in common]
                      for side,rows in zip(('bid','ask'),side_rows)}
            if not common:raise ValueError('empty_explicit_quarter')
            paired_spreads(*paired)
            for side,rows in zip(('bid','ask'),paired):
                stem=f'q{q}-{side}';path=output/f'{stem}.json';save(path,rows)
                seal=dict(request=stem,rows=len(rows),first=rows[0]['timestamp'],last=rows[-1]['timestamp'],sha256=digest(path))
                save(output/f'{stem}-seal.json',seal);seals.append(seal)
            journal=output/f'q{q}-unpaired-explicit.json';save(journal,unpaired)
            quarters.append(dict(quarter=q,paired_rows=len(common),sides=side_reports,
                unpaired_path=journal.name,unpaired_sha256=digest(journal),
                unpaired_rows={side:len(rows) for side,rows in unpaired.items()}))
            emit('quarter_source_view_sealed',quarter=q,paired_rows=len(common))
        check()
        # No result becomes admissible until every referenced input is rechecked.
        if any(digest(Path(path))!=sha for path,sha in bindings.items()):
            raise ValueError('source_input_changed_before_seal')
        new_manifest=dict(manifest)
        new_manifest.update(sourceObservationPolicy=POLICY,sourceTransformation='paired_explicit_source_timestamp_intersection_no_fill',
            protocolSha256=digest(protocol),parentManifestPath=str(parent/'manifest.json'),
            parentManifestSha256=digest(parent/'manifest.json'),canonicalExplicitSource=True)
        save(output/'manifest.json',new_manifest)
        proof=dict(schema=PROOF_SCHEMA,status='source_explicit_prices_and_pairing_verified',
            policy=POLICY,instrument='usa500idxusd',year=calendar['year'],
            producer_sha256=digest(Path(__file__)),validator_sha256=digest(Path(__file__).with_name('candle_source_provenance.py')),
            calendar_sha256=digest(calendar_path),protocol_sha256=digest(protocol),manifest_sha256=digest(output/'manifest.json'),
            source_pins=pins,input_bindings=bindings,quarters=quarters,output_seals=seals,
            full_retained_price_binding=True,holdout_read=False,network_calls=0,broker_calls=0,model_calls=0,
            elapsed_seconds=time.monotonic()-began,cpu_seconds=time.process_time()-cpu)
        save(output/'source-observation-proof.json',proof)
        save(output/'result.json',dict(status='downloaded_verified_M1_sides_needs_calendar_review',requests=seals,
            sourceObservationPolicy=POLICY,sourceObservationProofSha256=digest(output/'source-observation-proof.json'),
            strategySimulated=False,holdoutRead=False,networkCalls=0,brokerCalls=0,modelCalls=0))
        emit('explicit_source_view_sealed',paired_rows=sum(q['paired_rows'] for q in quarters))
        return proof
    except BaseException as error:
        save(output/'failure.json',dict(error_type=type(error).__name__,quarters_completed=len(quarters),
                                       elapsed_seconds=time.monotonic()-began))
        emit('failed',error_type=type(error).__name__)
        raise
    finally:lock.unlink(missing_ok=True)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ['parent','calendar','protocol','output']:parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--deadline-seconds',type=float,default=900)
    args=parser.parse_args()
    prepare(args.parent,args.calendar,args.protocol,args.output,deadline_seconds=args.deadline_seconds,
            progress=lambda value:print(json.dumps(value),flush=True))


if __name__=='__main__':main()
