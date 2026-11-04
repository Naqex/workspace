import copy
import json
import os
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

import shadow_sessions as batch


class SessionTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.directory=self.root/'outputs'
        self.binary=self.root/'shadow.exe';self.binary.write_bytes(b'pinned shadow fixture')
        self.python=self.root/'python.exe';self.python.write_bytes(b'pinned python fixture')
        self.secret=self.root/'secret.json';self.secret.write_text('{"owner_bearer":"fixture-secret-never-logged"}')
        self.manifest=self.root/'batch.json'
        self.plan=dict(schema_version=batch.SCHEMA,
            binary=dict(path=str(self.binary),sha256=batch.file_hash(self.binary)),
            python=dict(path=str(self.python),sha256=batch.file_hash(self.python)),sessions=[])
        for name,page in [('a',5),('b',10)]:
            path=self.root/(name+'.json')
            registration=dict(schema_version='mt5-shadow-session-v2',capture=dict(schema_version='mt5-observed-capture-v1',
                api_origin='http://127.0.0.1:8010',binding=dict(workspace_id='fixture',connection_id=str(uuid4()),
                generation=1,login='123',server='Fixture',environment='demo'),symbol='EURUSD',
                from_msc=100000,to_msc=130000,page_seconds=page),deadline_msc=200000,
                source_sha256=batch.shadow.source_pins())
            path.write_text(json.dumps(registration))
            self.plan['sessions'].append(dict(id=name,manifest_path=str(path),manifest_sha256=batch.file_hash(path),company=None,task=None))
        self.manifest.write_text(json.dumps(self.plan))
        self.states={};self.spawns=[]
        self.addCleanup(patch.stopall)
        patch.object(batch,'native_status',side_effect=lambda _,p:copy.deepcopy(self.states[p.name])).start()
        patch.object(batch,'spawn',side_effect=self.spawn).start()
        patch.object(batch,'alive',return_value=False).start()

    def spawn(self,args,directory,label):
        self.spawns.append((args,label))
        name=label.split('-')[0]
        identity=dict(pid=100+len(self.spawns),created=len(self.spawns),executable=args[0])
        if label.endswith('supervisor'):
            p=directory/name;p.mkdir(exist_ok=True);(p/'lifecycle.json').write_text('{}')
            previous=self.states.get(name,{})
            self.states[name]=dict(schema_version='mt5-shadow-lifecycle-v1',status='running',health='responsive',
                execution_capability=False,incarnation=previous.get('incarnation',0)+1,
                observation=dict(pages=previous.get('observation',{}).get('pages',0)))
        return SimpleNamespace(poll=lambda:None),identity

    def start(self):
        return batch.control('start',self.directory,manifest=self.manifest,secret=self.secret)

    def test_two_configs_have_separate_native_processes_state_and_no_model_environment(self):
        with patch.dict(os.environ,{'TW_V2_DATABASE_URL':'private','OPENAI_API_KEY':'private','PROXY_TOKEN':'private'}):
            env=batch.environment()
        self.assertFalse(any(k in env for k in ('TW_V2_DATABASE_URL','OPENAI_API_KEY','PROXY_TOKEN')))
        result=self.start()
        self.assertFalse(result['execution_capability']);self.assertFalse(result['model_inference_enabled'])
        self.assertEqual([s['status'] for s in result['sessions']],['running','running'])
        self.assertNotEqual(self.spawns[0][0][self.spawns[0][0].index('--state-dir')+1],self.spawns[1][0][self.spawns[1][0].index('--state-dir')+1])
        self.assertNotIn('fixture-secret-never-logged',json.dumps(result)+(self.directory/'launch.json').read_text())

    def test_stop_resume_one_preserves_sibling_and_existing_cursor(self):
        self.start();before=batch.capture.checked(self.directory/'launch.json')['sessions']['b']
        self.states['a']['observation']['pages']=3
        calls=[]
        def stop(args,**kwargs):
            calls.append(args);self.states[Path(args[-1]).name]['status']='stopped'
            return SimpleNamespace(returncode=0)
        with patch.object(batch.subprocess,'run',side_effect=stop):
            batch.control('stop',self.directory,names=['a'])
        self.assertEqual(len(calls),1);self.assertEqual(Path(calls[0][-1]).name,'a')
        batch.control('resume',self.directory,names=['a'])
        after=batch.capture.checked(self.directory/'launch.json')
        self.assertEqual(after['sessions']['b'],before)
        self.assertEqual(self.states['a']['observation']['pages'],3)
        self.assertEqual(self.states['a']['incarnation'],2);self.assertEqual(self.states['b']['incarnation'],1)
        self.assertEqual(self.spawns[-1][0][1],'resume')

    def test_duplicate_start_running_or_completed_resume_never_launches_again(self):
        self.start()
        with self.assertRaises(FileExistsError):self.start()
        result=batch.control('resume',self.directory,names=['a'])
        self.assertEqual(result['sessions'][0]['status'],'control_error')
        self.states['a']['status']='complete'
        result=batch.control('resume',self.directory,names=['a'])
        self.assertEqual(result['sessions'][0]['reason'],'shadow_group_completed_is_not_resumable')
        self.assertEqual(len(self.spawns),2)
        with self.assertRaises(ValueError):batch.control('resume',self.directory)

    def test_changed_registration_blocks_resume_but_not_stop_without_secret(self):
        self.start();self.secret.unlink()
        Path(self.plan['sessions'][0]['manifest_path']).write_text('{}')
        with self.assertRaisesRegex(ValueError,'registration_changed'):
            batch.control('resume',self.directory,names=['a'])
        with patch.object(batch.subprocess,'run',return_value=SimpleNamespace(returncode=0)) as run:
            batch.control('stop',self.directory,names=['a'])
            self.assertEqual(run.call_count,1)
        self.assertEqual(len(self.spawns),2)

    def test_bad_identity_runtime_or_selection_fails_before_spawn(self):
        for change in ('id','manifest','binary','task'):
            plan=copy.deepcopy(self.plan)
            if change=='id':plan['sessions'][1]['id']='a'
            if change=='manifest':plan['sessions'][1]['manifest_path']=plan['sessions'][0]['manifest_path']
            if change=='binary':plan['binary']['sha256']='0'*64
            if change=='task':plan['sessions'][0]['task']=str(uuid4())
            with self.subTest(change=change),self.assertRaises(ValueError):batch.validate(plan,self.directory)
        self.start()
        with self.assertRaises(ValueError):batch.control('stop',self.directory,names=['typo'])
        self.assertEqual(len(self.spawns),2)

    def test_observer_repair_never_restarts_computation(self):
        self.plan['sessions'][0].update(task=str(uuid4()),company=str(uuid4()))
        self.manifest.write_text(json.dumps(self.plan));self.start()
        supervisor_count=sum(label.endswith('supervisor') for _,label in self.spawns)
        batch.control('observe',self.directory,names=['a'])
        self.assertEqual(sum(label.endswith('supervisor') for _,label in self.spawns),supervisor_count)
        self.assertTrue(self.spawns[-1][1].endswith('observer'))

    def test_failed_sibling_does_not_cancel_or_block_other_launch(self):
        original=self.spawn
        def fail_one(args,directory,label):
            if label=='a-supervisor':raise OSError('fixture launch failure')
            return original(args,directory,label)
        with patch.object(batch,'spawn',side_effect=fail_one):result=self.start()
        self.assertEqual([s['status'] for s in result['sessions']],['control_error','running'])
        self.assertEqual(self.states['b']['incarnation'],1)


if __name__=='__main__':unittest.main()
