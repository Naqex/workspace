import copy
from uuid import uuid4
import unittest
from unittest.mock import patch
import json

from test_spot_workflow import NativeFixture
from studio_workflows import operate, observation_root


class StudioFixture(NativeFixture):
    def __init__(self):
        super().__init__(engine='forex-pilot')
        self.project_row = {'id': self.project, 'companyId': self.company, 'name': 'System checks'}

    def call(self, path, body=None, method='GET'):
        if path.endswith('/runs?view=recent'):
            issue = path.split('/')[2]
            return [dict(runId=key, **value) for key, value in self.runs.items()
                    if value.get('issueId') == issue]
        if path == '/companies':
            return [{'id': self.company, 'name': 'Fixture'}]
        if path == '/companies/' + self.company + '/projects':
            return [copy.deepcopy(self.project_row)]
        if path == '/projects/' + self.project:
            return copy.deepcopy(self.project_row)
        if path.startswith('/companies/' + self.company + '/issues?'):
            return list(copy.deepcopy(self.rows).values())
        return super().call(path, body, method)

    def create(self, key=None):
        return operate(self.call, dict(action='create', company=self.company, project=self.project,
                                      profile='forex', key=key or 'studio-' + str(uuid4())))


class StudioTests(unittest.TestCase):
    def test_independent_same_title_drafts_do_not_merge_or_cross_projects(self):
        client = StudioFixture()
        first = client.create()
        second = client.create()
        self.assertEqual(first['title'], second['title'])
        self.assertNotEqual(first['id'], second['id'])
        self.assertEqual(len(client.rows), 8)
        key = 'studio-' + str(uuid4())
        previous = client.create(key)
        client.project = str(uuid4())
        client.project_row['id'] = client.project
        third = client.create()
        self.assertEqual(third['project'], client.project)
        self.assertNotEqual(third['id'], first['id'])
        before = len(client.rows)
        with self.assertRaisesRegex(ValueError, '^workflow_scope$'): client.create(key)
        self.assertEqual(len(client.rows), before)
        self.assertNotEqual(previous['project'], third['project'])

    def test_draft_and_reload_are_native_idempotent_without_dispatch(self):
        client = StudioFixture()
        key = 'studio-' + str(uuid4())
        graph = client.create(key)
        self.assertTrue(graph['can_start'])
        self.assertEqual(graph, client.create(key))
        self.assertEqual(len(client.rows), 4)
        self.assertEqual(client.runs, {})
        self.assertEqual({row['status'] for row in client.rows.values()}, {'backlog', 'blocked'})
        self.assertNotIn('studio-', graph['title'])
        client.writes.clear()
        restored = operate(client.call, dict(action='get', company=client.company, parent=graph['id']))
        overview = operate(client.call, dict(action='overview'))
        self.assertEqual(restored, graph)
        self.assertEqual(overview['workflows'][0]['id'], graph['id'])
        self.assertEqual(client.writes, [])

    def test_foreign_project_or_parent_rejected_before_mutation(self):
        client = StudioFixture()
        client.project_row['companyId'] = str(uuid4())
        with self.assertRaises(ValueError): client.create()
        self.assertEqual(client.writes, [])
        client.project_row['companyId'] = client.company
        graph = client.create()
        client.writes.clear()
        for action in ('get', 'start', 'cancel'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                operate(client.call, dict(action=action, company=str(uuid4()), parent=graph['id']))
        self.assertEqual(client.writes, [])

    def test_start_rejects_changed_dependencies_and_never_resets_started_work(self):
        client = StudioFixture()
        graph = client.create()
        review = next(step['id'] for step in graph['steps'] if step['role'] == 'review')
        original = client.rows[review]['blockedByIssueIds']
        client.rows[review]['blockedByIssueIds'] = []
        client.writes.clear()
        request = dict(action='start', company=client.company, parent=graph['id'])
        with self.assertRaises(ValueError): operate(client.call, request)
        self.assertEqual(client.writes, [])
        client.rows[review]['blockedByIssueIds'] = original
        result = operate(client.call, request)
        self.assertEqual(result['status'], 'todo')
        self.assertFalse(result['can_start'])
        client.writes.clear()
        self.assertEqual(operate(client.call, request)['action'], 'not_started')
        self.assertEqual(client.writes, [])

    def test_cancel_draft_preserves_history_and_repeated_cancel_is_read_only(self):
        client = StudioFixture()
        graph = client.create()
        request = dict(action='cancel', company=client.company, parent=graph['id'])
        result = operate(client.call, request)
        self.assertEqual(result['status'], 'cancelled')
        self.assertTrue(all(row['status'] == 'cancelled' for row in client.rows.values()))
        client.writes.clear()
        self.assertFalse(operate(client.call, request)['can_cancel'])
        self.assertEqual(client.writes, [])

    def test_human_source_assignment_prevents_start_before_any_write(self):
        client = StudioFixture()
        graph = client.create()
        client.rows[graph['steps'][0]['id']]['assigneeUserId'] = 'local-board'
        client.writes.clear()
        result = operate(client.call, dict(action='start', company=client.company, parent=graph['id']))
        self.assertFalse(result['can_start'])
        self.assertEqual(result['action'], 'not_started')
        self.assertEqual(client.writes, [])

    def test_child_reparenting_and_arbitrary_commands_are_rejected(self):
        client = StudioFixture()
        graph = client.create()
        client.rows[graph['steps'][0]['id']]['parentId'] = str(uuid4())
        client.writes.clear()
        for action in ('get', 'start', 'cancel'):
            with self.subTest(action=action), self.assertRaises(ValueError):
                operate(client.call, dict(action=action, company=client.company, parent=graph['id']))
        for request in ({'action': 'shell', 'command': 'echo no'}, {'action': 'overview', 'settings': 'private'}):
            with self.assertRaises(ValueError): operate(client.call, request)
        self.assertEqual(client.writes, [])

    def test_run_history_blocks_reset_task_from_being_dispatched_again(self):
        client = StudioFixture()
        graph = client.create()
        source_id = graph['steps'][0]['id']
        run_id = str(uuid4())
        client.runs[run_id] = dict(id=run_id, companyId=client.company, issueId=source_id,
                                  agentId=client.research_agent, status='failed')
        client.writes.clear()
        result = operate(client.call, dict(action='start', company=client.company, parent=graph['id']))
        self.assertFalse(result['can_start'])
        self.assertEqual(result['action'], 'not_started')
        self.assertEqual(client.writes, [])

    def test_observation_does_not_require_valid_model_settings(self):
        with patch('pathlib.Path.read_text', return_value=json.dumps({'artifact_root': 'E:/worker-artifacts',
                                                                    'quick_model': 'opus-5.5'})):
            self.assertEqual(observation_root(), 'E:/worker-artifacts')
        for value in ('bad JSON', '[]', '{"artifact_root":"relative/path"}'):
            with patch('pathlib.Path.read_text', return_value=value):
                self.assertIsNone(observation_root())


if __name__ == '__main__':
    unittest.main()
