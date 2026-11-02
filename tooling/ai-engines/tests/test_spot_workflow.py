import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from uuid import uuid4

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import spot_workflow as workflow
from engine_worker import JobError


class NativeFixture:
    def __init__(self):
        self.company = str(uuid4())
        self.run = str(uuid4())
        self.project = str(uuid4())
        self.agent = str(uuid4())
        self.research_agent = str(uuid4())
        self.rows, self.keys, self.docs, self.runs = {}, {}, {}, {}
        self.writes = []
        self.agents = [{'id': self.research_agent, 'companyId': self.company, 'status': 'idle',
                        'metadata': {'naqexEngine': 'rd-agent'}},
                       {'id': self.agent, 'companyId': self.company, 'status': 'idle',
                        'metadata': {'naqexEngine': 'hermes'}}]

    def call(self, path, body=None, method='GET'):
        parts = path.strip('/').split('/')
        if method != 'GET':
            self.writes.append((path, copy.deepcopy(body), method))
        if parts[-1] == 'agents' and parts[0] == 'companies':
            return copy.deepcopy(self.agents)
        if parts[0] == 'agents':
            return copy.deepcopy(next(a for a in self.agents if a['id'] == parts[1]))
        if parts[0] == 'heartbeat-runs':
            if method == 'POST':
                self.runs[parts[1]]['status'] = 'cancelled'
            return copy.deepcopy(self.runs[parts[1]])
        if parts[0] == 'companies' and method == 'POST':
            key = body['idempotencyKey']
            if key not in self.keys:
                issue_id = str(uuid4())
                self.keys[key] = issue_id
                self.rows[issue_id] = dict(id=issue_id, companyId=self.company, createdByUserId='local-board', **body)
            return copy.deepcopy(self.rows[self.keys[key]])
        issue = self.rows[parts[1]]
        if len(parts) > 2 and parts[2] == 'documents':
            if len(parts) == 3:
                return [dict(key=k, **v) for (i, k), v in self.docs.items() if i == parts[1]]
            if method == 'PUT':
                self.docs[parts[1], parts[3]] = dict(body, companyId=self.company, issueId=parts[1], latestRevisionId=str(uuid4()))
            return copy.deepcopy(self.docs[parts[1], parts[3]])
        if method == 'PATCH':
            issue.update(body)
        result = copy.deepcopy(issue)
        result['blockedBy'] = [{'id': i} for i in issue.get('blockedByIssueIds', [])]
        return result

    def graph(self):
        return workflow.create_graph(self.call, self.company, self.project, 'fixture')

    def complete_source(self, directory):
        graph = self.graph()
        workflow.start_graph(self.call, graph)
        source_id = graph['research']
        self.rows[source_id].update(status='done')
        source_run = str(uuid4())
        self.runs[source_run] = dict(status='succeeded', companyId=self.company,
                                    agentId=self.research_agent, contextSnapshot={'issueId': source_id})
        root = Path(directory) / self.company / source_run
        root.mkdir(parents=True)
        provenance = {'strategy_qualified': False, 'execution_capability': False}
        evidence = dict(run_id=source_run, provenance=provenance, quant_validation={'fixture': True})
        receipt = dict(status='completed', delivery_status='published', engine='rd-agent',
                       run_id=source_run, issue_id=source_id, company_id=self.company, provenance=provenance)
        for prefix, filename, text in [('engine', 'report.md', 'numeric report'),
                                       ('evidence', 'evidence.md', workflow.block('json', evidence))]:
            (root / filename).write_text(text, encoding='utf-8')
            receipt['report_sha256' if prefix == 'engine' else 'evidence_sha256'] = workflow.digest(text)
            self.call('/issues/' + source_id + '/documents/' + prefix + '-' + source_run,
                      dict(body=text), 'PUT')
        (root / 'receipt.json').write_text(json.dumps(receipt), encoding='utf-8')
        return graph, root


class WorkflowTests(unittest.TestCase):
    def test_rejects_ambiguous_schema_paths_and_boolean_version(self):
        value = dict(version=1, source_issue_id=str(uuid4()))
        for text in [workflow.block('naqex-review', value) * 2,
                     workflow.block('naqex-review', dict(value, path='/tmp/report')),
                     workflow.block('naqex-review', dict(value, version=True)),
                     workflow.block('naqex-review', dict(value, source_issue_id='../report'))]:
            with self.subTest(text=text), self.assertRaises(JobError):
                workflow.parse_block(text, 'naqex-review', {'version', 'source_issue_id'})

    def test_create_and_start_are_idempotent_without_resetting_terminal_work(self):
        client = NativeFixture()
        graph = client.graph()
        self.assertEqual(graph, client.graph())
        self.assertEqual(len(client.rows), 4)
        self.assertEqual(workflow.start_graph(client.call, graph), 'started')
        self.assertEqual(workflow.start_graph(client.call, graph), 'already_started')
        for status in ('blocked', 'cancelled', 'done'):
            client.rows[graph['research']]['status'] = status
            self.assertEqual(workflow.start_graph(client.call, graph), 'already_started')
            self.assertEqual(client.rows[graph['research']]['status'], status)
        self.assertEqual(client.rows[graph['paper']]['status'], 'blocked')
        self.assertIsNone(client.rows[graph['paper']].get('assigneeAgentId'))

    def test_source_handoff_requires_native_success_scope_and_unchanged_artifacts(self):
        for mutation in ('none', 'cancelled', 'failed_run', 'cancelled_run', 'wrong_company', 'wrong_run', 'wrong_worker',
                         'hash', 'dependency', 'parent_cancelled', 'request_changed'):
            with self.subTest(mutation=mutation), tempfile.TemporaryDirectory() as temporary:
                client = NativeFixture()
                graph, root = client.complete_source(temporary)
                source = client.rows[graph['research']]
                issue = client.call('/issues/' + graph['review'])
                run = next(iter(client.runs.values()))
                if mutation == 'cancelled': source['status'] = 'cancelled'
                if mutation == 'failed_run': run['status'] = 'failed'
                if mutation == 'cancelled_run': run['status'] = 'cancelled'
                if mutation == 'wrong_company': source['companyId'] = str(uuid4())
                if mutation == 'wrong_run': run['contextSnapshot']['issueId'] = str(uuid4())
                if mutation == 'wrong_worker': client.agents[0]['metadata']['naqexEngine'] = 'hermes'
                if mutation == 'hash': (root / 'report.md').write_text('changed')
                if mutation == 'dependency': client.rows[issue['id']]['blockedByIssueIds'] = []
                if mutation == 'parent_cancelled': client.rows[graph['parent']]['status'] = 'cancelled'
                if mutation == 'request_changed': source['description'] += 'changed'
                with patch('rd_research.build_report', return_value='verified numbers'):
                    if mutation == 'none':
                        result = workflow.review_source(client, issue, {'artifact_root': temporary}, settle_seconds=0)
                        self.assertIn('verified numbers', result['prompt'])
                        self.assertEqual(result['binding']['source_issue'], graph['research'])
                    else:
                        with self.assertRaises(JobError):
                            workflow.review_source(client, issue, {'artifact_root': temporary}, settle_seconds=0)

    def test_source_revision_change_blocks_publication_even_with_same_content(self):
        with tempfile.TemporaryDirectory() as temporary, patch('rd_research.build_report', return_value='numbers'):
            client = NativeFixture()
            graph, root = client.complete_source(temporary)
            issue = client.call('/issues/' + graph['review'])
            settings = {'artifact_root': temporary}
            source = workflow.review_source(client, issue, settings)
            (root / 'review-source.json').write_text(json.dumps(source['binding']))
            client.docs[next(iter(client.docs))]['latestRevisionId'] = str(uuid4())
            with self.assertRaises(JobError):
                workflow.verify_review_source(client, issue, settings, root)

    def test_removing_review_binding_cannot_bypass_publication_guard(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            (directory / 'review-source.json').write_text('{}')
            with self.assertRaises(JobError):
                workflow.verify_review_source(None, {'description': 'ordinary task'}, {}, directory)

    def test_completion_waits_for_owner_and_never_starts_paper(self):
        client = NativeFixture()
        graph = client.graph()
        workflow.start_graph(client.call, graph)
        issue = client.call('/issues/' + graph['review'])
        workflow.finish_review(client, issue, {'binding': {}})
        self.assertEqual(client.rows[graph['parent']]['status'], 'in_review')
        self.assertEqual(client.rows[graph['parent']]['assigneeUserId'], 'local-board')
        self.assertEqual(client.rows[graph['paper']]['status'], 'blocked')
        self.assertIsNone(client.rows[graph['paper']].get('assigneeAgentId'))
        client.rows[graph['parent']]['status'] = 'cancelled'
        with self.assertRaises(JobError):
            workflow.finish_review(client, issue, {'binding': {}})
        self.assertEqual(client.rows[graph['parent']]['status'], 'cancelled')

    def test_cancel_stops_active_child_and_preserves_done_history(self):
        client = NativeFixture()
        graph = client.graph()
        run = str(uuid4())
        client.runs[run] = {'status': 'running'}
        client.rows[graph['research']].update(status='in_progress', executionRunId=run)
        client.rows[graph['review']]['status'] = 'done'
        workflow.cancel_graph(client.call, graph['parent'])
        self.assertEqual(client.runs[run]['status'], 'cancelled')
        self.assertEqual(client.rows[graph['research']]['status'], 'cancelled')
        self.assertEqual(client.rows[graph['review']]['status'], 'done')
        self.assertEqual(client.rows[graph['parent']]['status'], 'cancelled')


if __name__ == '__main__':
    unittest.main()
