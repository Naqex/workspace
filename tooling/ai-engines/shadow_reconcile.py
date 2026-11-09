"""Reconcile a stopped capture into a separate immutable history revision.

Only ordered insertions are admissible. Original data and live lifecycle never
change; history replay is not a completed live session or trading authority.
"""
import argparse
from pathlib import Path
import time
from uuid import uuid4

import shadow_sessions as group
from scripts import mt5_observed_capture as capture,mt5_shadow_step as shadow


def quote_rows(page):
    return [tuple(row[k] for k in ('time_msc','source_time_msc','bid','ask')) for row in page['rows']]


def classify(original,revised):
    headers=lambda p:{k:v for k,v in p.items() if k not in ('rows','observed_at_msc')}
    if headers(original)!=headers(revised):raise ValueError('revision_lineage_or_scope_changed')
    before,after=quote_rows(original),quote_rows(revised)
    cursor=0
    for row in after:
        if cursor<len(before) and row==before[cursor]:cursor+=1
    if cursor!=len(before):raise ValueError('revision_removed_changed_or_reordered_quotes')
    return dict(added_ticks=len(after)-len(before),original_ticks=len(before),revised_ticks=len(after))


def stable_read(original,plan,fetch,output,index,*,clock=lambda:int(time.time()*1000)):
    batch=uuid4().hex
    for attempt in range(3):
        observations=[]
        for ordinal in (1,2):
            page=capture.validate_page(fetch(original['from_msc'],original['to_msc']),plan,
                original['from_msc'],original['to_msc'])
            received=clock()
            capture.store(output/f'{index:05d}-{batch}-{attempt}-{ordinal}.json',page)
            observations.append((page,received))
        a,b=observations
        if quote_rows(a[0])==quote_rows(b[0]):
            classify(a[0],b[0])
            return b[0],b[1],classify(original,b[0])
    raise ValueError('revision_history_not_stable_after_bounded_reads')


def stopped_source(manifest,source):
    record=capture.checked(source.parent/'launch.json')
    registered=group.validate(record['plan'],source.parent)
    matches=[item for item in registered['sessions'] if item['id']==source.name
        and Path(item['manifest_path']).resolve()==manifest.resolve()
        and item['manifest_sha256']==group.file_hash(manifest)]
    if len(matches)!=1:raise ValueError('revision_source_registration_mismatch')
    lifecycle=group.native_status(Path(registered['binary']['path']),source)
    if lifecycle['status'] not in ('failed','stopped','expired','interrupted'):
        raise ValueError('revision_requires_stopped_failed_capture')
    if (lifecycle['manifest_sha256']!=matches[0]['manifest_sha256']
            or lifecycle['binary_sha256']!=registered['binary']['sha256']
            or lifecycle['python_sha256']!=registered['python']['sha256']):
        raise ValueError('revision_lifecycle_identity_changed')
    return lifecycle


def saved_prefix(output,progress,state,plan,source):
    if (type(progress['next_index']) is not int or not 0<=progress['next_index']<=len(state['pages'])
            or len(progress['pages'])!=progress['next_index']):
        raise ValueError('revision_cursor_invalid')
    for index,digest in enumerate(progress['pages']):
        selected=capture.checked(output/'selected'/f'{index:05d}.json')
        page=capture.validate_page(selected['page'],plan.capture,
            plan.capture.from_msc+index*plan.capture.page_seconds*1000,
            min(plan.capture.from_msc+(index+1)*plan.capture.page_seconds*1000,plan.capture.to_msc))
        original=shadow.page_at(source/'capture',state,plan.capture,index)
        classify(original,page)
        if (capture.checksum(page)!=digest or type(selected['received_at_msc']) is not int
                or selected['received_at_msc']<page['observed_at_msc']):
            raise ValueError('revision_saved_prefix_changed')


def reconcile(manifest,source,output,secret_file,*,resume=False,max_seconds=600,
        fetch=None,clock=lambda:int(time.time()*1000)):
    manifest,source,output,secret_file=map(lambda p:Path(p).absolute(),(manifest,source,output,secret_file))
    for p in (manifest,source,output,secret_file):capture.require_local_tree(p)
    if output.resolve().is_relative_to(source.resolve()) or source.resolve().is_relative_to(output.resolve()):
        raise ValueError('revision_output_must_be_new_and_separate')
    if any(p.resolve().is_relative_to(output.resolve()) for p in (manifest,secret_file)):
        raise ValueError('revision_inputs_must_be_outside_output')
    if type(max_seconds) is not int or not 1<=max_seconds<=3600:raise ValueError('revision_duration_invalid')
    plan=shadow.Plan.model_validate(capture.read_json(manifest))
    if plan.continuation is not None:raise ValueError('revision_continuation_needs_separate_review')
    stopped_source(manifest,source)
    capture.require_local_tree(source/'session.lock')
    deadline=clock()+max_seconds*1000
    # Serialize only this failed session; the active sibling remains independent.
    with capture._exclusive_file_lock(source/'session.lock'),capture._exclusive_file_lock(source/'capture/writer.lock'):
        stopped_source(manifest,source)
        state,_,_=capture.load(source/'capture',plan.capture)
        identity=dict(schema_version='mt5-shadow-history-revision-v1',manifest_sha256=group.file_hash(manifest),
            source_state_sha256=capture.checksum(state),source_directory=str(source),
            script_sha256=group.file_hash(Path(__file__)),source_sha256=shadow.source_pins())
        if not resume:
            output.mkdir(exist_ok=False);capture.private_directory(output)
            for name in ('capture','observations','selected'):(output/name).mkdir()
            capture.store(output/'revision-state.json',dict(**identity,status='running',pages=[],changes=[],
                next_index=0,known_at_msc=0,execution_capability=False,continuation_eligible=False))
        with capture._exclusive_file_lock(output/'revision.lock'):
            return reconcile_locked(manifest,source,output,secret_file,plan,state,identity,deadline,fetch,clock)


def reconcile_locked(manifest,source,output,secret_file,plan,state,identity,deadline,fetch,clock):
    progress=capture.checked(output/'revision-state.json')
    if any(progress[k]!=v for k,v in identity.items()):raise ValueError('revision_inputs_changed')
    saved_prefix(output,progress,state,plan,source)
    if progress['status']=='complete':
        result=capture.checked(output/'revision.json')
        revised_state,_,_=capture.load(output/'capture',plan.capture)
        if (any(result[k]!=v for k,v in identity.items()) or revised_state['pages']!=progress['pages']
                or result['report']['capture_state_sha256']!=capture.checksum(revised_state)):
            raise ValueError('revision_completed_result_changed')
        return result
    if progress['status']!='running':raise ValueError('revision_status_invalid')
    if fetch is None:
        token=capture.read_json(secret_file)['owner_bearer']
        fetch=capture.NativeReader(plan.capture,token)
    # Resume revalidates committed pages too; a second backfill requires a new
    # revision instead of rewriting the already accepted revision prefix.
    for index in range(len(state['pages'])):
        if clock()>=deadline:raise ValueError('revision_deadline_reached_resume_same_output')
        original=shadow.page_at(source/'capture',state,plan.capture,index)
        revised,known,change=stable_read(original,plan.capture,fetch,output/'observations',index,clock=clock)
        path=output/'selected'/f'{index:05d}.json'
        if path.exists():
            selected=capture.checked(path);existing=selected['page']
            if quote_rows(existing)!=quote_rows(revised):raise ValueError('revision_orphan_page_changed')
            classify(existing,revised);revised=existing
        else:capture.store(path,dict(page=revised,received_at_msc=known))
        if index<progress['next_index']:
            progress['known_at_msc']=max(progress['known_at_msc'],known)
            continue
        change=classify(original,revised)
        progress['pages'].append(capture.checksum(revised))
        if change['added_ticks']:
            progress['changes'].append(dict(index=index,from_msc=original['from_msc'],to_msc=original['to_msc'],
                original_sha256=capture.checksum(original),revised_sha256=capture.checksum(revised),
                received_at_msc=known,**change))
        progress.update(next_index=index+1,known_at_msc=max(progress['known_at_msc'],known))
        capture.store(output/'revision-state.json',progress)
        if index%20==0:print(capture.encoded(dict(status='reconciling',pages=index+1,total_pages=len(state['pages']),
            changed_pages=len(progress['changes']),execution_capability=False)).decode().strip(),flush=True)
    ticks=0
    for index in range(len(progress['pages'])):
        page=capture.checked(output/'selected'/f'{index:05d}.json')['page']
        path=output/'capture'/f'{index:05d}.json'
        if path.exists():
            if capture.checked(path)!=page:raise ValueError('revision_materialized_page_changed')
        else:capture.store(path,page)
        ticks+=len(page['rows'])
    revised_state={**state,'pages':progress['pages'],'tick_count':ticks}
    capture.store(output/'capture/state.json',revised_state)
    capture.load(output/'capture',plan.capture)
    def frozen(start,end):
        index=(start-plan.capture.from_msc)//(plan.capture.page_seconds*1000)
        return shadow.page_at(output/'capture',revised_state,plan.capture,index)
    report=shadow.reduce_capture(output/'capture',plan,None,frozen,clock())
    if capture.checksum(capture.load(source/'capture',plan.capture)[0])!=identity['source_state_sha256']:
        raise ValueError('revision_original_capture_changed')
    if (group.file_hash(manifest)!=identity['manifest_sha256'] or shadow.source_pins()!=identity['source_sha256']
            or group.file_hash(Path(__file__))!=identity['script_sha256']):
        raise ValueError('revision_source_changed_during_read')
    report.update(qualification='reconciled_history_not_live_forward',continuation_eligible=False,
        history_as_of_msc=progress['known_at_msc'],original_source_directory=str(source))
    result=dict(**identity,status='complete',scope='only_original_consumed_prefix',
        execution_capability=False,continuation_eligible=False,strategy_qualified=False,
        requested_through_msc=state['next_from_msc'],known_at_msc=progress['known_at_msc'],
        original_ticks=state['tick_count'],revised_ticks=revised_state['tick_count'],
        added_ticks=revised_state['tick_count']-state['tick_count'],pages=len(state['pages']),
        changes=progress['changes'],report=report)
    capture.store(output/'revision.json',result)
    progress['status']='complete';capture.store(output/'revision-state.json',progress)
    return result


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('manifest','source-dir','output-dir','owner-secret-file'):parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--resume',action='store_true')
    parser.add_argument('--max-seconds',type=int,default=600,choices=range(1,3601))
    args=parser.parse_args()
    try:
        result=reconcile(args.manifest,args.source_dir,args.output_dir,args.owner_secret_file,resume=args.resume,max_seconds=args.max_seconds)
        print(capture.encoded({k:result[k] for k in ('status','pages','original_ticks','revised_ticks','added_ticks','continuation_eligible')}).decode().strip())
        return 0
    except (OSError,ValueError,RuntimeError) as error:
        print(capture.encoded(dict(status='blocked',reason=str(error),execution_capability=False)).decode().strip())
        return 2


if __name__=='__main__':raise SystemExit(main())
