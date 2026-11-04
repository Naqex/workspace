"""Launch independent finite Rust shadow sessions; no models or trading grants.

The child lifecycle owns computation. This file only pins inputs, records exact
process identities and uses the existing read-only Paperclip observer.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
from uuid import UUID

ROOT = Path(__file__).resolve().parents[2]
V2 = ROOT/'projects/trader/foundation_v2'
sys.path.insert(0, str(V2))
from scripts import mt5_observed_capture as capture, mt5_shadow_step as shadow
from scripts.run_api_platform import process_identity
from shadow_watch import status as native_status

SCHEMA = 'mt5-shadow-group-v1'
FLAGS = subprocess.CREATE_NO_WINDOW | subprocess.DETACHED_PROCESS if os.name == 'nt' else 0


def file_hash(path):
    path = Path(path)
    capture.require_local_tree(path.absolute())
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def environment():
    keep = {'SYSTEMROOT','WINDIR','TEMP','TMP','USERPROFILE','APPDATA','LOCALAPPDATA',
            'PATH','PATHEXT','COMSPEC','PROCESSOR_ARCHITECTURE','NUMBER_OF_PROCESSORS'}
    return {**{k:v for k,v in os.environ.items() if k.upper() in keep}, 'PYTHONUTF8':'1'}


def validate(plan, directory, *, inputs=True):
    if set(plan) != {'schema_version','binary','python','sessions'} or plan['schema_version'] != SCHEMA:
        raise ValueError('shadow_group_schema_invalid')
    directory = Path(directory).absolute()
    capture.require_local_tree(directory)
    for name in ('binary','python'):
        item=plan[name]
        if set(item)!={'path','sha256'} or not Path(item['path']).is_absolute():
            raise ValueError('shadow_group_runtime_invalid')
        if file_hash(item['path'])!=item['sha256']:
            raise ValueError('shadow_group_runtime_changed')
    sessions=plan['sessions']
    if not isinstance(sessions,list) or not 1<=len(sessions)<=16:
        raise ValueError('shadow_group_sessions_invalid')
    ids=set(); manifests=set(); tasks=set()
    for item in sessions:
        if (set(item)!={'id','manifest_path','manifest_sha256','company','task'}
                or not re.fullmatch(r'[a-z0-9][a-z0-9-]{0,47}',item['id']) or item['id'] in ids):
            raise ValueError('shadow_group_session_identity_invalid')
        ids.add(item['id'])
        manifest=Path(item['manifest_path'])
        capture.require_local_tree(manifest.absolute())
        if (not manifest.is_absolute() or manifest.resolve().is_relative_to(directory.resolve())
                or manifest.resolve() in manifests):
            raise ValueError('shadow_group_manifest_overlap')
        manifests.add(manifest.resolve())
        if bool(item['company'])!=bool(item['task']):
            raise ValueError('shadow_group_publication_scope_invalid')
        if item['task']:
            UUID(item['company']);UUID(item['task'])
            # One task per session keeps cancellation/status ownership clear.
            if item['task'] in tasks:raise ValueError('shadow_group_task_reused')
            tasks.add(item['task'])
        if inputs:
            if file_hash(manifest)!=item['manifest_sha256']:
                raise ValueError('shadow_group_registration_changed')
            shadow.Plan.model_validate(capture.read_json(manifest))
    return plan


def select(plan, names):
    if names and (len(set(names))!=len(names) or set(names)-{s['id'] for s in plan['sessions']}):
        raise ValueError('shadow_group_unknown_session')
    return [s for s in plan['sessions'] if not names or s['id'] in names]


def alive(identity):
    return bool(identity and process_identity(identity['pid'])==identity)


def spawn(args, directory, label):
    # Append logs across incarnations. Never truncate evidence on resume.
    with (directory/(label+'.stdout.log')).open('ab') as out, (directory/(label+'.stderr.log')).open('ab') as err:
        child=subprocess.Popen(args,cwd=ROOT,env=environment(),stdin=subprocess.DEVNULL,
            stdout=out,stderr=err,creationflags=FLAGS,close_fds=True)
    identity=process_identity(child.pid)
    if identity is None:
        raise RuntimeError('shadow_group_process_exited_during_launch')
    return child,identity


def observe(plan,item,directory,record):
    if not item['task']:
        return
    old=record['sessions'][item['id']]
    if alive(old.get('observer')):
        return
    child,identity=spawn([plan['python']['path'],'-X','utf8',str(ROOT/'tooling/ai-engines/shadow_watch.py'),
        '--binary',plan['binary']['path'],'--state-dir',str(directory/item['id']),
        '--company',item['company'],'--task',item['task']],directory,item['id']+'-observer')
    old['observer']=identity
    old['observer_status']='started'


def launch(plan,item,directory,record,secret,*,resume):
    row=record['sessions'][item['id']]
    child_dir=directory/item['id']
    if resume:
        current=native_status(Path(plan['binary']['path']),child_dir)
        if current['status']=='complete':raise ValueError('shadow_group_completed_is_not_resumable')
        if current['status']=='running' or alive(row.get('supervisor')):
            raise ValueError('shadow_group_session_already_running')
        if alive(row.get('observer')):
            raise ValueError('shadow_group_previous_observer_finishing')
    elif child_dir.exists() or row.get('launch_intent'):
        raise ValueError('shadow_group_existing_session_requires_reconciliation')
    row.update(launch_intent=True,launch_status='starting',operation='resume' if resume else 'start')
    capture.store(directory/'launch.json',record)
    child,identity=spawn([plan['binary']['path'],'resume' if resume else 'start',
        '--manifest',item['manifest_path'],'--state-dir',str(child_dir),'--python',plan['python']['path'],
        '--owner-secret-file',str(secret)],directory,item['id']+'-supervisor')
    row.update(supervisor=identity,launch_status='spawned')
    capture.store(directory/'launch.json',record)
    for _ in range(50):
        if (child_dir/'lifecycle.json').is_file():
            current=native_status(Path(plan['binary']['path']),child_dir)
            # A resume may briefly expose the previous terminal incarnation.
            if current.get('status')=='running' or child.poll() is not None:
                break
        if child.poll() is not None:raise RuntimeError('shadow_group_native_start_failed')
        time.sleep(.1)
    else:raise RuntimeError('shadow_group_lifecycle_not_ready_reconcile_existing_pid')
    row['launch_status']='native_lifecycle_available'
    capture.store(directory/'launch.json',record)
    observe(plan,item,directory,record)


def control(operation,directory,*,manifest=None,secret=None,names=None):
    directory=Path(directory).absolute()
    capture.require_local_tree(directory)
    if operation=='start':
        if manifest is None or secret is None:raise ValueError('shadow_group_start_inputs_required')
        manifest=Path(manifest).absolute();secret=Path(secret).absolute()
        capture.require_local_tree(manifest);capture.require_local_tree(secret)
        if manifest.resolve().is_relative_to(directory.resolve()) or secret.resolve().is_relative_to(directory.resolve()):
            raise ValueError('shadow_group_inputs_must_be_outside_output')
        plan=validate(capture.read_json(manifest),directory)
        if names:raise ValueError('shadow_group_start_registers_all_sessions')
        record=dict(schema_version=SCHEMA,plan=plan,manifest_sha256=file_hash(manifest),
            secret_path=str(secret),secret_sha256=file_hash(secret),
            sessions={s['id']:{} for s in plan['sessions']})
        directory.mkdir(exist_ok=False);capture.private_directory(directory)
        capture.store(directory/'launch.json',record)
    else:
        record=capture.checked(directory/'launch.json')
        if record.get('schema_version')!=SCHEMA:raise ValueError('shadow_group_record_invalid')
        plan=validate(record['plan'],directory,inputs=operation=='resume')
        secret=Path(record['secret_path'])
        if operation=='resume':
            if not names:raise ValueError('shadow_group_resume_requires_explicit_session')
            if file_hash(secret)!=record['secret_sha256']:raise ValueError('shadow_group_read_credential_changed')
    items=select(plan,names)
    results=[]
    # Child lifecycles own their execution locks. This lock only serializes CLI
    # control operations, never the duration of observation sessions.
    with capture._exclusive_file_lock(directory/'launch.lock'):
        if operation!='start':
            record=capture.checked(directory/'launch.json')
        for item in items:
            try:
                if operation in ('start','resume'):
                    launch(plan,item,directory,record,secret,resume=operation=='resume')
                elif operation=='stop':
                    result=subprocess.run([plan['binary']['path'],'stop','--state-dir',str(directory/item['id'])],
                        capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
                    if result.returncode:raise ValueError('shadow_group_stop_failed')
                elif operation=='observe':
                    observe(plan,item,directory,record)
                current=native_status(Path(plan['binary']['path']),directory/item['id'])
                results.append(dict(id=item['id'],status=current['status'],health=current.get('health'),
                    phase=current.get('phase'),reason=current.get('reason'),
                    incarnation=current.get('incarnation'),observation=current.get('observation'),
                    heartbeat_at_msc=current.get('heartbeat_at_msc'),deadline_msc=current.get('deadline_msc')))
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
                # A failed sibling never stops or restarts the others.
                record['sessions'][item['id']]['control_error']=type(error).__name__
                results.append(dict(id=item['id'],status='control_error',reason=str(error) if isinstance(error,ValueError) else type(error).__name__))
            if operation!='status':capture.store(directory/'launch.json',record)
    return dict(operation=operation,execution_capability=False,model_inference_enabled=False,sessions=results)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('start','resume','status','stop','observe'))
    parser.add_argument('--state-dir',type=Path,required=True)
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--owner-secret-file',type=Path)
    parser.add_argument('--session',action='append',dest='names')
    args=parser.parse_args()
    try:
        value=control(args.operation,args.state_dir,manifest=args.manifest,secret=args.owner_secret_file,names=args.names)
        print(json.dumps(value,ensure_ascii=False),flush=True)
        return 2 if any(s['status'] in ('control_error','failed','expired') for s in value['sessions']) else 0
    except (OSError,ValueError,RuntimeError) as error:
        print(json.dumps(dict(status='control_error',reason=str(error) if isinstance(error,ValueError) else type(error).__name__)),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
