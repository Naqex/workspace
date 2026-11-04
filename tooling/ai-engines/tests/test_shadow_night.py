import copy
from contextlib import nullcontext
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from uuid import uuid4

import shadow_night as night


class Crash(BaseException):
    pass


class NightTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.directory=self.root/'manager'
        self.now=100*night.shadow.HOUR_MS+10000
        self.binary=self.root/'shadow.exe';self.binary.write_bytes(b'fixture native binary')
        self.python=self.root/'python.exe';self.python.write_bytes(b'fixture interpreter')
        self.secret=self.root/'secret.json';self.secret.write_text('{"owner_bearer":"private-fixture-token"}')
        runtime=self.root/'runtime.json';runtime.write_text(json.dumps(dict(ready=True,run_id='fixture',processes={'api':dict(pid=1)})))
        offline=self.root/'offline.json';night.capture.store(offline,dict(status='passed'))
        items=[]
        self.first_to=102*night.shadow.HOUR_MS
        self.final_to=107*night.shadow.HOUR_MS-300000
        for name,end in [('a',self.first_to),('b',self.final_to)]:
            child=night.shadow.Plan.model_validate(dict(schema_version='mt5-shadow-session-v2',capture=dict(
                schema_version='mt5-observed-capture-v1',api_origin='http://127.0.0.1:8010',
                binding=dict(workspace_id='fixture',connection_id=str(uuid4()),generation=1,login='123',server='Fixture',environment='demo'),
                symbol='EURUSD',from_msc=self.now,to_msc=end,page_seconds=60),deadline_msc=end+180000,
                source_sha256=night.shadow.source_pins(),stability_policy='ordered_quotes_v1'))
            path=self.root/(name+'.json');path.write_text(child.model_dump_json())
            items.append(dict(id=name,manifest_path=str(path),manifest_sha256=night.group.file_hash(path),company=None,task=None))
        initial=self.root/'group.json';initial.write_text(json.dumps(dict(schema_version=night.group.SCHEMA,
            binary=dict(path=str(self.binary),sha256=night.group.file_hash(self.binary)),
            python=dict(path=str(self.python),sha256=night.group.file_hash(self.python)),sessions=items)))
        self.plan=night.Plan.model_validate(dict(schema_version=night.SCHEMA,run_id=str(uuid4()),root=str(self.root),
            initial_manifest=str(initial),initial_sha256=night.group.file_hash(initial),initial_output=str(self.root/'first'),
            predecessor='a',successor='next',successor_manifest=str(self.root/'next.json'),successor_output=str(self.root/'second'),
            secret_path=str(self.secret),secret_sha256=night.group.file_hash(self.secret),final_to_msc=self.final_to,
            deadline_msc=self.final_to+300000,runtime_manifest=str(runtime),runtime_run_id='fixture',
            min_free_bytes=1024*1024,max_run_bytes=32*1024*1024,volumes=[str(self.root)],
            offline_receipt=str(offline),offline_sha256=night.group.file_hash(offline),company=str(uuid4()),parent_task=str(uuid4()),
            offline_task=str(uuid4()),source_sha256=night.pins()))
        self.rows={};self.calls=[]
        self.addCleanup(patch.stopall)
        patch.object(night,'process_identity',side_effect=lambda pid:dict(pid=pid)).start()
        patch.object(night.group,'control',side_effect=self.control).start()

    def control(self,operation,output,**kwargs):
        self.calls.append((operation,str(output)))
        output=Path(output)
        if operation=='start':
            output.mkdir()
            value=night.capture.read_json(kwargs['manifest'])
            night.capture.store(output/'launch.json',dict(plan=value,manifest_sha256=night.group.file_hash(kwargs['manifest']),sessions={}))
            self.rows[str(output)]=[dict(id=i['id'],status='running',phase='poll_wait',observation=dict(pages=1,ticks=4)) for i in value['sessions']]
        if operation=='stop':
            for row in self.rows.get(str(output),[]):row['status']='stopped'
        return dict(sessions=copy.deepcopy(self.rows.get(str(output),[])))

    def manager(self,**kwargs):
        return night.Manager(self.plan,self.directory,clock=lambda:self.now,**kwargs)

    def complete_first(self,m,*,hours=True):
        self.rows[self.plan.initial_output][0]['status']='complete'
        previous=Path(self.plan.initial_output)/'a';previous.mkdir()
        night.capture.store(previous/'shadow.json',dict(hours=[{'timestamp':101*3600}] if hours else [],cumulative_hours=1 if hours else 0))

    def test_manager_restart_attaches_to_existing_native_group_without_relaunch(self):
        m=self.manager();m.step()
        again=self.manager(resume=True);again.step()
        self.assertEqual(sum(op=='start' for op,_ in self.calls),1)
        self.assertEqual(again.state['status'],'running')
        self.assertEqual(again.state['plan_sha256'],m.state['plan_sha256'])

    def test_uncertain_launch_never_creates_another_group(self):
        m=self.manager();m.state['initial_intent']=True;m.save()
        with self.assertRaisesRegex(ValueError,'uncertain_launch'):m.step()
        self.assertEqual(self.calls,[])

    def test_failed_predecessor_leaves_sibling_running_and_does_not_handoff(self):
        m=self.manager();m.step();self.rows[self.plan.initial_output][0]['status']='failed'
        m.step()
        self.assertEqual(m.state['status'],'running')
        self.assertIn('a',m.state['errors'])
        self.assertEqual(self.rows[self.plan.initial_output][1]['status'],'running')
        self.assertNotIn('successor',m.state['groups'])

    def test_missing_hour_or_missed_handoff_never_fabricates_successor(self):
        m=self.manager();m.step();self.complete_first(m,hours=False)
        m.step();self.assertIn('no_real_closed_h1',m.state['errors']['next']['reason'])
        self.assertNotIn('successor',m.state['groups'])
        m.state['errors'].clear();self.now=self.first_to+91000;m.step()
        self.assertEqual(m.state['errors']['next']['reason'],'night_handoff_window_missed')
        self.assertEqual(sum(op=='start' for op,_ in self.calls),1)

    def test_handoff_verifies_real_prefix_and_pins_original_deadline(self):
        m=self.manager();m.step();self.complete_first(m);self.now=self.first_to+31000
        with patch.object(night.shadow,'warmup',return_value={}) as warmup:m.step()
        self.assertTrue(warmup.call_args.kwargs['verify_pages'])
        child=night.shadow.Plan.model_validate(night.capture.read_json(Path(self.plan.successor_manifest)))
        self.assertEqual(child.capture.from_msc,self.first_to)
        self.assertEqual(child.capture.to_msc,self.final_to)
        self.assertEqual(child.deadline_msc,self.final_to+180000)
        self.assertTrue(m.state['handoff']['verified_before_launch'])
        self.assertEqual(self.rows[self.plan.initial_output][1]['status'],'running')

    def test_crash_after_successor_launch_recovers_without_starting_it_twice(self):
        m=self.manager();m.step();self.complete_first(m);self.now=self.first_to+31000
        original=night.capture.store;failed=False
        def fail_after_launch(path,value):
            nonlocal failed
            if path==m.path and 'successor' in value.get('groups',{}) and not failed:
                failed=True;raise Crash('fixture process death after native launch')
            return original(path,value)
        with patch.object(night.shadow,'warmup',return_value={}),patch.object(night.capture,'store',side_effect=fail_after_launch),self.assertRaises(Crash):
            m.step()
        again=self.manager(resume=True)
        with patch.object(night.shadow,'warmup',return_value={}):again.step()
        self.assertEqual(sum(op=='start' and output==self.plan.successor_output for op,output in self.calls),1)
        self.assertTrue(again.state['handoff']['verified_before_launch'])

    def test_late_manager_restart_attaches_existing_successor_after_launch_window(self):
        m=self.manager();m.step();self.complete_first(m);self.now=self.first_to+31000
        with patch.object(night.shadow,'warmup',return_value={}):m.step()
        saved=night.capture.checked(m.path);saved['groups'].pop('successor');night.capture.store(m.path,saved)
        self.now=self.first_to+300000
        again=self.manager(resume=True)
        with patch.object(night.shadow,'warmup',return_value={}):again.step()
        self.assertIn('successor',again.state['groups'])
        self.assertEqual(sum(op=='start' for op,_ in self.calls),2)

    def test_finished_native_sessions_can_reconcile_after_manager_deadline_without_restart(self):
        m=self.manager();m.step();self.complete_first(m);self.now=self.first_to+31000
        with patch.object(night.shadow,'warmup',return_value={}):m.step()
        for rows in self.rows.values():
            for row in rows:row['status']='complete'
        self.now=self.plan.deadline_msc+60000
        again=self.manager(resume=True);again.step()
        self.assertEqual(again.state['status'],'complete')
        self.assertEqual(sum(op=='start' for op,_ in self.calls),2)
        self.assertFalse(any(op=='stop' for op,_ in self.calls))

    def test_source_change_and_resource_failure_are_explicit_without_restarting(self):
        m=self.manager()
        with patch.object(night,'pins',return_value={}):
            with self.assertRaisesRegex(ValueError,'controller_source_changed'):m.step()
        with patch.object(night.shutil,'disk_usage',return_value=SimpleNamespace(free=0)):
            self.assertFalse(night.resources(self.plan)['ok'])
        self.assertEqual(self.calls,[])

    def test_optional_process_metrics_identity_error_is_unknown_not_fatal(self):
        from scripts.run_api_platform import PreflightError
        with patch.object(night.group,'alive',side_effect=PreflightError('fixture inaccessible or recycled PID')):
            value=night.process_metrics([dict(pid=987)])
        self.assertIs(value['available'],False)
        self.assertEqual(value['reason'],'process_metrics_identity_unavailable')
        self.assertEqual(value['error_type'],'PreflightError')
        m=self.manager()
        # The real runtime identity fence remains fail-closed.
        with patch.object(night,'process_identity',side_effect=PreflightError('fixture runtime identity unavailable')):
            with self.assertRaises(PreflightError):m.guard()

    def test_fatal_guard_failure_publishes_blocked_state_before_exit(self):
        from scripts.run_api_platform import PreflightError
        m=self.manager()
        with patch.object(night,'keep_awake',return_value=nullcontext()),\
                patch.object(m,'step',side_effect=PreflightError('fixture real runtime identity failure')),\
                patch.object(m,'publish') as publish,patch.object(m,'finish_tasks') as finish:
            with self.assertRaises(PreflightError):night.run(m)
        self.assertEqual(m.state['status'],'blocked')
        self.assertEqual(m.state['failure_detail']['error_type'],'PreflightError')
        publish.assert_called_once();finish.assert_called_once()

    def test_atomic_checkpoint_failure_keeps_last_good_bytes(self):
        m=self.manager();before=m.path.read_bytes();m.state['status']='new-uncommitted-state'
        with patch.object(night.capture.os,'replace',side_effect=OSError('fixture disk full')):
            with self.assertRaises(OSError):m.save()
        self.assertEqual(m.path.read_bytes(),before)
        self.assertEqual(night.capture.checked(m.path)['status'],'prepared')

    def test_publication_timeout_reconciles_after_restart_without_capture_or_secret(self):
        m=self.manager();document=None;puts=[];original=night.Publisher
        def request(path,body=None,method='GET'):
            nonlocal document
            if method=='GET':
                if document is None:raise HTTPError(path,404,'missing',{},None)
                return document.copy()
            puts.append(body);document=dict(body,latestRevisionId=str(len(puts)))
            if len(puts)==1:raise TimeoutError('committed but reply lost')
            return document.copy()
        def publisher(task,manifest):return original(task,manifest,request=request)
        with patch.object(night,'Publisher',side_effect=publisher):m.publish()
        self.assertIsNotNone(m.state['publication']['pending'])
        self.secret.unlink();Path(self.plan.initial_manifest).unlink();self.now+=1000
        again=self.manager(resume=True,read_only=True)
        with patch.object(night,'Publisher',side_effect=publisher):again.publish()
        self.assertEqual(len(puts),2)
        self.assertIsNone(again.state['publication']['pending'])
        self.assertIsNone(again.state['publication']['error'])
        self.assertEqual(self.calls,[])

    def test_stop_and_deadline_keep_scope_and_do_not_claim_flat_or_completion(self):
        m=self.manager();m.step();(self.directory/'STOP').write_text('owner stop')
        m.step();self.assertEqual(m.state['status'],'stopped')
        self.assertFalse(m.state['execution_capability'])
        self.assertTrue(all(op in ('start','status','stop') for op,_ in self.calls))
        self.assertNotIn('flat',m.state)
        (self.directory/'STOP').unlink();m.state['status']='running';self.now=self.plan.deadline_msc
        m.step();self.assertEqual(m.state['status'],'expired')
        self.assertEqual(m.plan.deadline_msc,self.now)


if __name__=='__main__':unittest.main()
