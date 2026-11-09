import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import shadow_reconcile as revision

capture=revision.capture
shadow=revision.shadow


class ReconcileTests(unittest.TestCase):
    def setUp(self):
        temp=tempfile.TemporaryDirectory();self.addCleanup(temp.cleanup)
        self.root=Path(temp.name);self.source=self.root/'group/ftmo';self.source.mkdir(parents=True)
        self.output=self.root/'revision';self.manifest=self.root/'ftmo.json';self.secret=self.root/'secret.json'
        self.secret.write_text('{"owner_bearer":"fixture-not-printed"}')
        self.plan=shadow.Plan.model_validate(dict(schema_version='mt5-shadow-session-v2',capture=dict(
            schema_version='mt5-observed-capture-v1',api_origin='http://127.0.0.1:8010',
            binding=dict(workspace_id='fixture',connection_id='492ec8a5-3938-41a3-8a26-8c0f7f59ed43',
                generation=1,login='123',server='Fixture',environment='demo'),
            symbol='EURUSD',from_msc=0,to_msc=3600000,page_seconds=60),
            deadline_msc=3690000,source_sha256=shadow.source_pins(),stability_policy='ordered_quotes_v1'))
        self.manifest.write_text(self.plan.model_dump_json())
        capture.record(self.plan.capture,self.source/'capture',resume=False,fetch=self.page,
            max_batches=60,now_msc=4000000,comparison_policy=self.plan.stability_policy)
        self.binary=self.root/'shadow.exe';self.binary.write_bytes(b'fixture')
        self.python=self.root/'python.exe';self.python.write_bytes(b'fixture python')
        group=dict(schema_version=revision.group.SCHEMA,
            binary=dict(path=str(self.binary),sha256=revision.group.file_hash(self.binary)),
            python=dict(path=str(self.python),sha256=revision.group.file_hash(self.python)),
            sessions=[dict(id='ftmo',manifest_path=str(self.manifest),
                manifest_sha256=revision.group.file_hash(self.manifest),company=None,task=None)])
        capture.store(self.source.parent/'launch.json',dict(plan=group))
        self.lifecycle=dict(status='failed',manifest_sha256=revision.group.file_hash(self.manifest),
            binary_sha256=group['binary']['sha256'],python_sha256=group['python']['sha256'])
        self.addCleanup(patch.stopall)
        patch.object(revision.group,'native_status',side_effect=lambda *args:copy.deepcopy(self.lifecycle)).start()
        self.original={str(p.relative_to(self.source)):p.read_bytes() for p in (self.source/'capture').glob('*.json')}

    def page(self,start,end):
        return dict(schema_version='mt5-tick-range-v1',status='ready',
            binding=self.plan.capture.binding.model_dump(mode='json'),symbol='EURUSD',from_msc=start,to_msc=end,
            observed_at_msc=4000000,clock={'profile':'fixture'},coverage='broker_history_unverified',
            execution_capability=False,sdk_version='fixture',
            source_sha256={'mt5_clock.py':'a'*64,'mt5_tick_capture.py':'b'*64},
            rows=[dict(time_msc=t,source_time_msc=t,bid=1.1,ask=1.1002,flags=6)
                for t in range(start+1000,end,30000)])

    def revised(self,start,end):
        page=self.page(start,end)
        if start==0:
            new={**page['rows'][0],'time_msc':2000,'source_time_msc':2000,'bid':1.0998}
            page['rows'].insert(1,new)
        return page

    def run_revision(self,**kwargs):
        return revision.reconcile(self.manifest,self.source,self.output,self.secret,
            fetch=kwargs.pop('fetch',self.revised),clock=lambda:5000000,**kwargs)

    def assert_original_unchanged(self):
        self.assertEqual(self.original,{str(p.relative_to(self.source)):p.read_bytes()
            for p in (self.source/'capture').glob('*.json')})

    def test_additions_recompute_hour_preserve_original_and_never_qualify_live(self):
        result=self.run_revision()
        self.assertEqual((result['original_ticks'],result['revised_ticks'],result['added_ticks']),(120,121,1))
        self.assertEqual(result['report']['hours'][0]['ticks'],121)
        self.assertEqual(result['report']['hours'][0]['ohlc_mid'][2],'1.1000')
        self.assertEqual(result['report']['qualification'],'reconciled_history_not_live_forward')
        self.assertFalse(result['continuation_eligible']);self.assertFalse(result['execution_capability'])
        self.assertEqual(result['known_at_msc'],5000000)
        self.assertFalse((self.output/'lifecycle.json').exists())
        self.assert_original_unchanged()
        # A complete revision is read/validated without another broker query.
        self.assertEqual(self.run_revision(resume=True,fetch=lambda *_:self.fail('unexpected read')),result)

    def test_removed_changed_reordered_quotes_rejected_and_duplicates_retained(self):
        original=self.page(0,60000)
        for mutate in (lambda rows:rows.pop(),lambda rows:rows[0].update(bid=1.0999),lambda rows:rows.reverse()):
            revised=copy.deepcopy(original);mutate(revised['rows'])
            with self.assertRaisesRegex(ValueError,'removed_changed_or_reordered'):
                revision.classify(original,revised)
        original['rows'].insert(0,copy.deepcopy(original['rows'][0]))
        revised=copy.deepcopy(original);revised['rows'].insert(0,copy.deepcopy(revised['rows'][0]))
        self.assertEqual(revision.classify(original,revised)['added_ticks'],1)
        revised['rows']=revised['rows'][2:]
        with self.assertRaisesRegex(ValueError,'removed_changed_or_reordered'):revision.classify(original,revised)

    def test_lineage_binding_source_sdk_clock_are_not_ignored(self):
        original=self.page(0,60000)
        for key,value in [('clock',{'profile':'other'}),('sdk_version','other'),
                ('source_sha256',{'mt5_clock.py':'c'*64,'mt5_tick_capture.py':'b'*64}),
                ('binding',{**original['binding'],'generation':2})]:
            revised=copy.deepcopy(original);revised[key]=value
            with self.subTest(key=key),self.assertRaisesRegex(ValueError,'lineage_or_scope'):
                revision.classify(original,revised)

    def test_unstable_reads_stop_after_three_pairs_and_preserve_all_observations(self):
        output=self.root/'observations';output.mkdir();calls=[]
        def unstable(start,end):
            calls.append(1);page=self.page(start,end)
            page['rows'][0]['bid']=1.1-len(calls)*0.00001
            return page
        with self.assertRaisesRegex(ValueError,'not_stable'):
            revision.stable_read(self.page(0,60000),self.plan.capture,unstable,output,0,clock=lambda:5000000)
        self.assertEqual(len(calls),6);self.assertEqual(len(list(output.glob('*.json'))),6)

    def test_interrupted_resume_uses_same_revision_and_reaudits_saved_prefix(self):
        calls=[]
        def interrupted(start,end):
            calls.append(start)
            if start==60000:raise OSError('fixture disconnect')
            return self.revised(start,end)
        with self.assertRaisesRegex(OSError,'disconnect'):self.run_revision(fetch=interrupted)
        self.assertEqual(capture.checked(self.output/'revision-state.json')['next_index'],1)
        selected=(self.output/'selected/00000.json').read_bytes()
        result=self.run_revision(resume=True)
        self.assertEqual(result['added_ticks'],1)
        self.assertEqual((self.output/'selected/00000.json').read_bytes(),selected)
        self.assertEqual(len(list((self.output/'observations').glob('00000-*.json'))),4)
        self.assert_original_unchanged()

    def test_resume_rejects_modified_saved_page_and_further_backfill(self):
        def interrupted(start,end):
            if start==60000:raise OSError('disconnect')
            return self.revised(start,end)
        with self.assertRaises(OSError):self.run_revision(fetch=interrupted)
        def again(start,end):
            page=self.revised(start,end)
            if start==0:page['rows'].insert(1,copy.deepcopy(page['rows'][0]))
            return page
        with self.assertRaisesRegex(ValueError,'orphan_page_changed'):self.run_revision(resume=True,fetch=again)
        path=self.output/'selected/00000.json';saved=capture.checked(path)
        saved['page']['rows'][0]['bid']=1.0997;capture.store(path,saved)
        with self.assertRaises(ValueError):self.run_revision(resume=True)

    def test_orphan_selected_page_after_crash_is_adopted_without_rewriting(self):
        store=capture.store
        def fail_progress(path,value):
            if path.name=='revision-state.json' and value.get('next_index')==1:raise OSError('crash after selected')
            return store(path,value)
        with patch.object(capture,'store',side_effect=fail_progress),self.assertRaises(OSError):self.run_revision()
        selected=(self.output/'selected/00000.json').read_bytes()
        result=self.run_revision(resume=True)
        self.assertEqual(result['added_ticks'],1)
        self.assertEqual((self.output/'selected/00000.json').read_bytes(),selected)
        self.assert_original_unchanged()

    def test_active_lifecycle_wrong_registration_and_overlapping_output_rejected(self):
        self.lifecycle['status']='running'
        with self.assertRaisesRegex(ValueError,'requires_stopped'):self.run_revision()
        self.lifecycle['status']='failed';self.lifecycle['manifest_sha256']='0'*64
        with self.assertRaisesRegex(ValueError,'lifecycle_identity'):self.run_revision()
        self.output=self.source/'revision'
        with self.assertRaisesRegex(ValueError,'new_and_separate'):self.run_revision()


if __name__=='__main__':unittest.main()
