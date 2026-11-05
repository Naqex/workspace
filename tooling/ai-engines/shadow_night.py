"""Finite read-only handoff controller. Rust owns capture; Paperclip owns tasks.

No trading grants, model calls, runtime restart, PID kill or deadline extension.
"""
import argparse
from contextlib import contextmanager
import ctypes
from datetime import datetime,timezone,timedelta
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Literal
from uuid import UUID

import shadow_sessions as group
from shadow_watch import Publisher,stamp
from paperclip_setup import api
from scripts import mt5_observed_capture as capture,mt5_shadow_step as shadow
from scripts.run_api_platform import process_identity
from pydantic import Field,model_validator

SCHEMA='mt5-shadow-night-v1'
TERMINAL={'complete','failed','stopped','expired','interrupted','control_error'}
VN=timezone(timedelta(hours=7))


def qualified(row):
    return row.get('status') == 'complete' and (row.get('observation') or {}).get('projection_status') != 'held'


def pins():
    return {str(p):group.file_hash(p) for p in (Path(__file__).resolve(),
        group.ROOT/'tooling/ai-engines/shadow_sessions.py',group.ROOT/'tooling/ai-engines/shadow_watch.py')}


class Plan(capture.Frozen):
    schema_version: Literal['mt5-shadow-night-v1']
    run_id: UUID
    root: str
    initial_manifest: str
    initial_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    initial_output: str
    predecessor: str=Field(pattern=r'^[a-z0-9-]+$')
    successor: str=Field(pattern=r'^[a-z0-9-]+$')
    successor_manifest: str
    successor_output: str
    secret_path: str
    secret_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    final_to_msc: int=Field(ge=0,strict=True)
    deadline_msc: int=Field(ge=0,strict=True)
    runtime_manifest: str
    runtime_run_id: str
    min_free_bytes: int=Field(ge=1024*1024,strict=True)
    max_run_bytes: int=Field(ge=1024*1024,strict=True)
    volumes: list[str]=Field(min_length=1,max_length=4)
    offline_receipt: str
    offline_sha256: str=Field(pattern=r'^[0-9a-f]{64}$')
    company: UUID
    parent_task: UUID
    offline_task: UUID
    source_sha256: dict[str,str]

    @model_validator(mode='after')
    def paths(self):
        for value in (self.root,self.initial_manifest,self.initial_output,self.successor_manifest,
                self.successor_output,self.secret_path,self.runtime_manifest,self.offline_receipt,*self.volumes):
            path=Path(value)
            if not path.is_absolute():raise ValueError('night_absolute_local_path_required')
            capture.require_local_tree(path)
        a,b=Path(self.initial_output).resolve(),Path(self.successor_output).resolve()
        if a==b or a.is_relative_to(b) or b.is_relative_to(a) or self.predecessor==self.successor:
            raise ValueError('night_outputs_overlap')
        if not 30000<=self.deadline_msc-self.final_to_msc<=300000:
            raise ValueError('night_deadline_invalid')
        return self


def tree_bytes(root):
    total=0
    for directory,folders,files in os.walk(root,followlinks=False):
        for name in [*folders,*files]:capture.require_local_tree(Path(directory)/name)
        for name in files:total+=(Path(directory)/name).stat().st_size
    return total


def resources(plan):
    free={v:shutil.disk_usage(v).free for v in plan.volumes}
    size=tree_bytes(plan.root)
    return dict(observed_at_msc=int(time.time()*1000),free_bytes=free,run_bytes=size,
        ok=all(n>=plan.min_free_bytes for n in free.values()) and size<=plan.max_run_bytes)


@contextmanager
def keep_awake():
    if os.name!='nt':
        yield;return
    # A thread-scoped idle-sleep request; screen may turn off, no power setting changes.
    fn=ctypes.WinDLL('kernel32',use_last_error=True).SetThreadExecutionState
    fn.argtypes=[ctypes.c_ulong];fn.restype=ctypes.c_ulong
    if not fn(0x80000001):raise OSError('night_idle_sleep_request_failed')
    try:yield
    finally:fn(0x80000000)


def process_metrics(identities):
    try:
        owned=[i for i in identities if i and group.alive(i)]
    except (OSError,ValueError,RuntimeError) as error:
        # A terminated/recycled/inaccessible PID makes metrics unknown. It is
        # not an execution-identity decision and must not stop healthy capture.
        return dict(available=False,reason='process_metrics_identity_unavailable',error_type=type(error).__name__)
    if os.name!='nt' or not owned:return dict(available=False,reason='no_owned_windows_processes')
    ids=','.join(str(int(i['pid'])) for i in owned)
    command=f'@(Get-Process -Id @({ids}) -ErrorAction SilentlyContinue | Select-Object Id,CPU,WorkingSet64) | ConvertTo-Json -Compress'
    try:
        result=subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command],
            capture_output=True,timeout=5,creationflags=subprocess.CREATE_NO_WINDOW)
        rows=json.loads(result.stdout) if result.stdout.strip() else []
        rows=rows if isinstance(rows,list) else [rows]
        valid={i['pid'] for i in owned if group.alive(i)}
        return dict(available=result.returncode==0,rows=[r for r in rows if r['Id'] in valid],
            cpu_unit='cumulative_seconds',memory_unit='working_set_bytes',scope='owned_controller_and_shadow_processes')
    except (OSError,ValueError,RuntimeError,KeyError,TypeError,subprocess.TimeoutExpired) as error:
        return dict(available=False,reason='process_metrics_unavailable',error_type=type(error).__name__)


class Manager:
    def __init__(self,plan,directory,*,resume=False,read_only=False,clock=lambda:int(time.time()*1000)):
        self.plan,self.directory,self.clock=plan,Path(directory),clock
        self.path=self.directory/'state.json'
        if resume:
            self.state=capture.checked(self.path)
            if self.state['plan_sha256']!=capture.checksum(plan.model_dump(mode='json')):
                raise ValueError('night_plan_changed')
            if read_only:
                self.initial=self.state['initial_group'];self.first=None;return
        self.initial=capture.read_json(Path(plan.initial_manifest))
        group.validate(self.initial,Path(plan.initial_output))
        if group.file_hash(plan.initial_manifest)!=plan.initial_sha256 or len(self.initial['sessions'])!=2:
            raise ValueError('night_initial_registration_changed')
        self.predecessor=next(s for s in self.initial['sessions'] if s['id']==plan.predecessor)
        self.first=shadow.Plan.model_validate(capture.read_json(Path(self.predecessor['manifest_path'])))
        if (self.first.capture.to_msc%shadow.HOUR_MS or
                not self.first.capture.to_msc<plan.final_to_msc<plan.deadline_msc):
            raise ValueError('night_handoff_window_invalid')
        if resume:
            if self.initial!=self.state['initial_group']:raise ValueError('night_initial_group_changed')
        else:
            self.directory.mkdir(exist_ok=False);capture.private_directory(self.directory)
            self.state=dict(schema_version=SCHEMA,plan_sha256=capture.checksum(plan.model_dump(mode='json')),
                status='prepared',initial_intent=False,successor_intent=False,groups={},lanes={},
                errors={},publication={},source_sha256=plan.source_sha256,created_at_msc=clock(),initial_group=self.initial,
                execution_capability=False,model_inference_enabled=False)
            self.save()

    def save(self):
        self.state['updated_at_msc']=self.clock()
        capture.store(self.path,self.state)

    def error(self,lane,reason):
        self.state['errors'].setdefault(lane,dict(reason=reason,at_msc=self.clock()))

    def guard(self):
        if self.plan.source_sha256!=pins():raise ValueError('night_controller_source_changed')
        if group.file_hash(self.plan.secret_path)!=self.plan.secret_sha256:
            raise ValueError('night_read_credential_changed')
        runtime=capture.read_json(Path(self.plan.runtime_manifest))
        if not runtime.get('ready') or runtime.get('run_id')!=self.plan.runtime_run_id:
            raise ValueError('night_runtime_changed_or_unready')
        if any(process_identity(i['pid'])!=i for i in runtime['processes'].values()):
            raise ValueError('night_runtime_identity_changed')
        offline=capture.checked(Path(self.plan.offline_receipt))
        if group.file_hash(self.plan.offline_receipt)!=self.plan.offline_sha256 or offline.get('status')!='passed':
            raise ValueError('night_offline_gate_unverified')

    def ensure_group(self,key,manifest,output):
        intent=key+'_intent'
        if (output/'launch.json').exists():
            saved=capture.checked(output/'launch.json')
            if (saved['manifest_sha256']!=group.file_hash(manifest) or saved['plan']!=capture.read_json(manifest)):
                raise ValueError('night_existing_group_changed')
            self.state['groups'][key]=str(output)
            return
        if output.exists() or self.state[intent]:
            raise ValueError('night_uncertain_launch_requires_reconciliation')
        self.state[intent]=True;self.save()
        result=group.control('start',output,manifest=manifest,secret=Path(self.plan.secret_path))
        self.state['groups'][key]=str(output)
        self.state[key+'_launch']=result
        self.save()

    def poll(self,key):
        output=Path(self.state['groups'][key])
        rows=group.control('status',output)['sessions']
        for row in rows:
            self.state['lanes'][row['id']]=row
            if row['status'] in TERMINAL-{'complete'}:
                self.error(row['id'],row.get('reason') or row['status'])
            if (row.get('observation') or {}).get('projection_status') == 'held':
                self.error(row['id'],row['observation'].get('quality_reason') or 'shadow_quality_hold')
        return rows

    def followup(self):
        previous=Path(self.plan.initial_output)/self.plan.predecessor
        report=capture.checked(previous/'shadow.json')
        if not report['hours'] or report['cumulative_hours']<1:
            raise ValueError('night_no_real_closed_h1_to_handoff')
        plan=shadow.Plan.model_validate(dict(schema_version='mt5-shadow-session-v2',
            capture={**self.first.capture.model_dump(mode='json'),'from_msc':self.first.capture.to_msc,
                'to_msc':self.plan.final_to_msc},
            deadline_msc=min(self.plan.final_to_msc+180000,self.plan.deadline_msc),
            settle_seconds=self.first.settle_seconds,stability_policy=self.first.stability_policy,
            projection_policy=self.first.projection_policy,
            source_sha256=self.first.source_sha256,
            continuation=dict(state_dir=str(previous),report_sha256=capture.checksum(report))))
        # Verify the real completed lifecycle, report and capture prefix BEFORE launch.
        shadow.warmup(plan,Path(self.plan.successor_output)/self.plan.successor,verify_pages=True)
        registration=Path(self.plan.successor_manifest)
        raw=(plan.model_dump_json(indent=2)+'\n').encode()
        if registration.exists():
            if registration.read_bytes()!=raw:raise ValueError('night_successor_registration_changed')
        else:
            with registration.open('xb') as stream:
                stream.write(raw);stream.flush();os.fsync(stream.fileno())
        child={**self.predecessor,'id':self.plan.successor,'manifest_path':str(registration),
            'manifest_sha256':group.file_hash(registration)}
        followup={**self.initial,'sessions':[child]}
        manifest=registration.with_name(registration.stem+'-group.json')
        encoded=capture.encoded(followup)
        if manifest.exists():
            if manifest.read_bytes()!=encoded:raise ValueError('night_successor_group_changed')
        else:
            with manifest.open('xb') as stream:
                stream.write(encoded);stream.flush();os.fsync(stream.fileno())
        self.state['handoff']=dict(predecessor_report_sha256=capture.checksum(report),
            predecessor_hours=len(report['hours']),registered_at_msc=self.clock(),
            from_msc=plan.capture.from_msc,deadline_msc=plan.deadline_msc,verified_before_launch=True)
        self.ensure_group('successor',manifest,Path(self.plan.successor_output))
        self.save()

    def halt(self,reason):
        self.state['stop_requested_at_msc']=self.clock()
        outputs=set(self.state['groups'].values())|{self.plan.initial_output,self.plan.successor_output}
        for output in outputs:
            if not (Path(output)/'launch.json').exists():continue
            try:group.control('stop',Path(output))
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired):pass
        self.error('manager',reason)
        self.state['status']='stopped' if reason=='operator_stop' else 'expired' if reason=='deadline' else 'blocked'
        self.save()

    def step(self):
        if self.state['status'] in ('complete','blocked','stopped','expired'):
            return self.state
        if (self.directory/'STOP').exists():self.halt('operator_stop');return self.state
        initial_exists=(Path(self.plan.initial_output)/'launch.json').exists()
        if not initial_exists:
            if self.clock()>=self.plan.deadline_msc:self.halt('deadline');return self.state
            self.guard()
        self.ensure_group('initial',Path(self.plan.initial_manifest),Path(self.plan.initial_output))
        rows=self.poll('initial')
        predecessor=next(r for r in rows if r['id']==self.plan.predecessor)
        # A crash after spawn can leave a successor running/completed without
        # the manager's last commit. Attach it even after the launch window;
        # an absent successor must never be launched late.
        existing_successor=(Path(self.plan.successor_output)/'launch.json').exists()
        if 'successor' not in self.state['groups'] and existing_successor and qualified(predecessor):
            self.followup()
        if 'successor' in self.state['groups']:self.poll('successor')
        success=(qualified(self.state['lanes'].get(self.plan.successor,{}))
            and all(qualified(r) for r in rows) and bool(self.state.get('handoff',{}).get('verified_before_launch')))
        if success:
            self.state['status']='complete';self.save();return self.state
        if self.clock()>=self.plan.deadline_msc:self.halt('deadline');return self.state
        self.guard()
        if 'successor' not in self.state['groups'] and qualified(predecessor):
            if self.clock()>self.first.capture.to_msc+(self.first.settle_seconds+60)*1000:
                self.error(self.plan.successor,'night_handoff_window_missed')
            elif self.plan.successor not in self.state['errors']:
                try:self.followup()
                except (OSError,ValueError,RuntimeError) as error:
                    self.error(self.plan.successor,str(error) if isinstance(error,ValueError) else type(error).__name__)
        if 'successor' in self.state['groups']:self.poll('successor')
        waiting=any(r['status']=='running' for r in self.state['lanes'].values())
        if qualified(predecessor) and 'successor' not in self.state['groups'] and self.plan.successor not in self.state['errors']:
            waiting=True
        if waiting:self.state['status']='running'
        else:
            self.state['status']='blocked'
        self.save()
        return self.state

    def render(self,marker):
        lines=[marker,'# Qua đêm: trạng thái dữ liệu và bàn giao','',
            '| Nội dung | Trạng thái |','|---|---|',
            f'| Run | `{self.plan.run_id}` |',
            f'| Cập nhật / hạn chót | {stamp(self.clock())} / {stamp(self.plan.deadline_msc)} |',
            f'| Bộ theo dõi | {self.state["status"]} |',
            f'| H1 handoff | {bool(self.state.get("handoff",{}).get("verified_before_launch"))} |',
            '| Thực thi / AI trong job | Chỉ đọc; không model inference |','',
            '| Lane | Trạng thái / phase | Pages / ticks / H1 | Dữ liệu tới | Lỗi đầu tiên |',
            '|---|---|---|---|---|']
        for name,row in self.state['lanes'].items():
            obs=row.get('observation') or {}
            reason=self.state['errors'].get(name,{}).get('reason','Không')
            lines.append(f'| {name} | {row["status"]} / {row.get("phase")} | {obs.get("pages",0)} / {obs.get("ticks",0)} / {obs.get("closed_hours",0)} | {stamp(obs.get("requested_through_msc"))} | `{reason}` |')
        measure=self.state.get('resources',{})
        lines.extend(['',f'Dung lượng run: {measure.get("run_bytes","chưa đo")} bytes; free bytes: `{measure.get("free_bytes",{})}`.',
            'Offline gate: passed. Đây là coverage quan sát, không chứng nhận đủ tick, lợi nhuận hoặc 24/7.',
            'Raw flags stability không asserted trong ordered_quotes_v1. Lỗi một lane không tự restart lane khác.',
            'Nếu report quá 90 giây không đổi, đọc status/checkpoint trước khi kết luận job còn hoạt động.',
            f'Các lỗi đã ghi: `{json.dumps(self.state["errors"],ensure_ascii=False)}`',
            '',f'Checkpoint local: `{self.path}`; lệnh resume ở runbook trong thư mục run.'])
        if self.state.get('recovery'):
            lines.extend(['','## Phục hồi đã ghi nhận',self.state['recovery']['note'],
                f'Lần dừng: {stamp(self.state["recovery"]["stopped_at_msc"])}; tiếp từ checkpoint: {stamp(self.state["recovery"]["resumed_at_msc"])}.',
                'Khoảng ngắt không được tính là uptime liên tục. Dữ liệu đọc bù có thời điểm observation mới; không phát lại quyết định giao dịch.'])
        return '\n'.join(lines)+'\n'

    def publish(self):
        record=self.state['publication']
        publisher=Publisher(str(self.plan.parent_task),self.state['plan_sha256'])
        publisher.revision=record.get('revision');publisher.seen=record.get('seen',False)
        publisher.pending=record.get('pending')
        try:
            # Reconcile a previous uncertain PUT before replacing its pending body.
            if publisher.pending:
                publisher.send(publisher.pending)
                record.update(revision=publisher.revision,seen=publisher.seen,pending=publisher.pending)
                self.save()
            body=self.render(publisher.marker)
            record['pending']=body;self.save()
            publisher.send(body)
            record.update(last_success_msc=self.clock(),error=None)
        except (OSError,ValueError,RuntimeError) as error:
            record['error']=type(error).__name__
        record.update(revision=publisher.revision,seen=publisher.seen,pending=publisher.pending)
        self.save()

    def finish_tasks(self):
        for item in self.initial['sessions']:
            names=[item['id']]+([self.plan.successor] if item['id']==self.plan.predecessor else [])
            ok=all(qualified(self.state['lanes'].get(n,{})) for n in names)
            if item['task']:
                self.finish_task(item['task'],dict(status='done' if ok else 'blocked',
                    **({} if ok else dict(unblockDescriptor=dict(owner='board',action='Inspect overnight checkpoint and first error; resume only the registered session if still valid.')))),'PATCH')
        self.finish_task(str(self.plan.parent_task),dict(status='done' if self.state['status']=='complete' else 'blocked',
            **({} if self.state['status']=='complete' else dict(unblockDescriptor=dict(owner='board',action='Inspect native overnight report and local checkpoint; do not replace failed history.')))),'PATCH')

    def finish_task(self,task,body,method):
        current=api('/issues/'+task)
        if current['companyId']!=str(self.plan.company) or current.get('assigneeAgentId'):
            raise ValueError('night_task_scope_or_assignment_changed')
        # A later review/repair may resolve the work item even when this old
        # observation failed. Re-publication must not reopen that resolution.
        if current['status'] in ('done','cancelled'):
            return
        if current['status']!=body['status']:api('/issues/'+task,body,method)


def run(manager):
    with capture._exclusive_file_lock(manager.directory/'manager.lock'),keep_awake():
        manager.state['manager_identity']=process_identity(os.getpid());manager.save()
        last_measure=last_publish=0
        try:
            while True:
                manager.step()
                if time.monotonic()-last_measure>=60:
                    measure=resources(manager.plan)
                    manager.state['resources']=measure
                    if not measure['ok']:manager.halt('night_storage_headroom_exhausted')
                    identities=[manager.state['manager_identity']]
                    for output in manager.state['groups'].values():
                        record=capture.checked(Path(output)/'launch.json')
                        identities.extend(row.get(role) for row in record['sessions'].values() for role in ('supervisor','observer'))
                    measure['processes']=process_metrics(identities)
                    with (manager.directory/'resources.jsonl').open('a',encoding='utf-8') as stream:
                        stream.write(json.dumps(measure)+'\n');stream.flush();os.fsync(stream.fileno())
                    manager.save();last_measure=time.monotonic()
                terminal=manager.state['status'] in ('complete','blocked','stopped','expired')
                critical=(abs(manager.clock()-manager.first.capture.to_msc)<120000 and 'successor' not in manager.state['groups'])
                if terminal or (not critical and time.monotonic()-last_publish>=60):
                    manager.publish();last_publish=time.monotonic()
                print(json.dumps(dict(status=manager.state['status'],updated_at_msc=manager.clock(),
                    lanes={k:v['status'] for k,v in manager.state['lanes'].items()},errors=manager.state['errors'])),flush=True)
                if terminal:
                    try:manager.finish_tasks()
                    except (OSError,ValueError,RuntimeError):
                        manager.state['task_delivery']='pending';manager.save()
                    return 0 if manager.state['status']=='complete' else 2
                time.sleep(5)
        except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
            manager.state['failure_detail']=dict(error_type=type(error).__name__,reason=str(error)[:240])
            try:manager.halt(str(error) if isinstance(error,ValueError) else type(error).__name__)
            except (OSError,ValueError,RuntimeError):pass
            try:
                manager.publish();manager.finish_tasks()
            except (OSError,ValueError,RuntimeError):
                manager.state['task_delivery']='pending'
                try:manager.save()
                except (OSError,ValueError,RuntimeError):pass
            raise


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('operation',choices=('start','resume','status','stop','publish'))
    parser.add_argument('--manifest',type=Path)
    parser.add_argument('--state-dir',type=Path,required=True)
    args=parser.parse_args()
    try:
        if args.operation=='status':
            state=capture.checked(args.state_dir/'state.json')
            state['manager_alive']=group.alive(state.get('manager_identity'))
            state['native_current']={}
            for key,output in state['groups'].items():
                try:state['native_current'][key]=group.control('status',Path(output))
                except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as error:
                    state['native_current'][key]=dict(unavailable=type(error).__name__)
            print(json.dumps(state,ensure_ascii=False));return 0
        if args.operation=='stop':
            capture.require_local_tree(args.state_dir)
            with (args.state_dir/'STOP').open('a') as stream:stream.write('owner stop\n')
            return 0
        if args.manifest is None:raise ValueError('night_manifest_required')
        plan=Plan.model_validate(capture.read_json(args.manifest))
        if args.operation!='publish':
            measure=resources(plan)
            if not measure['ok']:raise ValueError('night_storage_headroom_insufficient')
        manager=Manager(plan,args.state_dir,resume=args.operation!='start',read_only=args.operation=='publish')
        if args.operation=='publish':
            with capture._exclusive_file_lock(manager.directory/'manager.lock'):
                manager.publish();manager.finish_tasks()
            return 0
        return run(manager)
    except (OSError,ValueError,RuntimeError) as error:
        print(json.dumps(dict(status='blocked',reason=str(error) if isinstance(error,ValueError) else type(error).__name__)),file=sys.stderr)
        return 2


if __name__=='__main__':raise SystemExit(main())
