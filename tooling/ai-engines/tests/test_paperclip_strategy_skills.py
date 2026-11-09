import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import paperclip_strategy_skills as skills


class NativeFixture:
    def __init__(self):
        self.agent = dict(companyId='company', adapterType='codex_local', status='idle')
        self.rows = []
        self.contents = {}
        self.desired = ['keep-existing']
        self.writes = []

    def __call__(self, path, body=None, method='GET'):
        if method != 'GET':
            self.writes.append((method,path,body))
        if path == '/agents/lead':
            return dict(self.agent)
        if path == '/agents/lead/skills':
            return dict(desiredSkills=list(self.desired))
        if path == '/agents/lead/skills/sync':
            assert body['mode']=='add'
            self.desired = list(dict.fromkeys(self.desired+body['desiredSkills']))
            return dict(desiredSkills=self.desired)
        if path == '/companies/company/skills':
            if method=='GET':
                return copy.deepcopy(self.rows)
            row = dict(id=str(len(self.rows)+1), slug=body['slug'], key='company/company/'+body['slug'],
                       sourceType='managed', currentVersionId='v1', fileInventory=[dict(path='SKILL.md')])
            self.rows.append(row)
            self.contents[(row['id'],'SKILL.md')] = body['markdown']
            return copy.deepcopy(row)
        tail = path.removeprefix('/companies/company/skills/').split('/')
        row = next(row for row in self.rows if row['id']==tail[0])
        if len(tail)==1:
            return copy.deepcopy(row)
        if method=='PATCH':
            assert body['expectedVersionId']==row['currentVersionId']
            self.contents[(row['id'],body['path'])]=body['content']
            row['currentVersionId']+='x'
            if body['path'] not in [item['path'] for item in row['fileInventory']]:
                row['fileInventory'].append(dict(path=body['path']))
            return dict(versionId=row['currentVersionId'])
        name=path.split('?path=')[1]
        return dict(content=self.contents[(row['id'],name)])


class SkillDeliveryTests(unittest.TestCase):
    def test_allowlisted_package_contains_only_reviewed_markdown(self):
        bundle=skills.package()
        self.assertEqual({item['slug'] for item in bundle['skills']},set(skills.SOURCES))
        self.assertTrue(all(path.endswith('.md') for item in bundle['skills'] for path in item['files']))

    def test_native_publication_preserves_assignments_and_rerun_is_idempotent(self):
        api=NativeFixture()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            result=skills.publish(api,skills.package(),'company','lead',root/'one.json')
            self.assertEqual(result['status'],'published_and_assigned')
            self.assertIn('keep-existing',api.desired)
            writes=len(api.writes)
            skills.publish(api,skills.package(),'company','lead',root/'two.json')
            self.assertEqual(len(api.writes),writes)
            changed=skills.package()
            changed['skills'][0]['files']['SKILL.md']+='\nReviewed update.\n'
            update=skills.publish(api,changed,'company','lead',root/'three.json')
            self.assertTrue(update['backups'])
            self.assertEqual(len(api.rows),3)

    def test_process_worker_active_lead_and_upstream_collision_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            for change in ({'adapterType':'process'}, {'status':'running'}, {'companyId':'wrong'}):
                api=NativeFixture()
                api.agent.update(change)
                with self.subTest(change=change),self.assertRaises(ValueError):
                    skills.publish(api,skills.package(),'company','lead',Path(directory)/'no.json')
                self.assertFalse(api.writes)
            api=NativeFixture()
            api.rows=[dict(id='external',slug='strategy-research',sourceType='catalog')]
            with self.assertRaisesRegex(ValueError,'upstream'):
                skills.publish(api,skills.package(),'company','lead',Path(directory)/'no.json')
            self.assertFalse(api.writes)

    def test_uncertain_write_stops_and_keeps_recovery_receipt(self):
        fixture=NativeFixture()
        def failing(path,body=None,method='GET'):
            if method=='POST':
                raise ConnectionError('unknown publication outcome')
            return fixture(path,body,method)
        with tempfile.TemporaryDirectory() as directory:
            receipt=Path(directory)/'receipt.json'
            with self.assertRaises(ConnectionError):
                skills.publish(failing,skills.package(),'company','lead',receipt)
            self.assertTrue(receipt.exists())
            self.assertFalse(fixture.writes)

    def test_version_conflict_stops_before_assignment(self):
        fixture=NativeFixture()
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            skills.publish(fixture,skills.package(),'company','lead',root/'initial.json')
            before=list(fixture.desired)
            updated=skills.package()
            updated['skills'][0]['files']['SKILL.md']+='\nChange after baseline.\n'
            writes=[]
            def conflict(path,body=None,method='GET'):
                if method!='GET':
                    writes.append((method,path))
                if method=='PATCH':
                    raise ValueError('native expectedVersionId conflict')
                return fixture(path,body,method)
            with self.assertRaisesRegex(ValueError,'expectedVersionId'):
                skills.publish(conflict,updated,'company','lead',root/'conflict.json')
            self.assertEqual(fixture.desired,before)
            self.assertEqual(len(writes),1)


if __name__=='__main__':
    unittest.main()
