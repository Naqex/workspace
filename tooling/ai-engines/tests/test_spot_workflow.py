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
    def __init__(self, engine='rd-agent'):
        self.engine = engine
        self.company = str(uuid4())
        self.run = str(uuid4())
        self.project = str(uuid4())
        self.agent = str(uuid4())
        self.research_agent = str(uuid4())
        self.rows, self.keys, self.docs, self.runs = {}, {}, {}, {}
        self.writes = []
        self.agents = [{'id': self.research_agent, 'companyId': self.company, 'status': 'idle',
                        'metadata': {'naqexEngine': engine}},
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
            if key not in self.keys and body.get('allowDuplicate', False) is False:
                existing = next((row for row in self.rows.values()
                                 if row['title'] == body['title'] and row.get('parentId') == body.get('parentId')
                                 and row['status'] not in ('done', 'cancelled')), None)
                if existing:
                    self.keys[key] = existing['id']
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
        return workflow.create_graph(self.call, self.company, self.project, 'fixture',
                                     workflow='forex' if self.engine == 'forex-pilot' else 'spot')

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
        evidence = dict(run_id=source_run, provenance=provenance)
        evidence['forex_validation' if self.engine == 'forex-pilot' else 'quant_validation'] = {'fixture': True}
        receipt = dict(status='completed', delivery_status='published', engine=self.engine,
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
    def test_start_rejects_reparented_cross_company_or_wrong_worker_before_any_mutation(self):
        for change in ('parent', 'company', 'worker'):
            with self.subTest(change=change):
                client = NativeFixture(engine='forex-pilot')
                graph = client.graph()
                if change == 'parent':
                    client.rows[graph['research']]['parentId'] = str(uuid4())
                elif change == 'company':
                    client.rows[graph['research']]['companyId'] = str(uuid4())
                else:
                    client.agents[0]['metadata']['naqexEngine'] = 'rd-agent'
                client.writes.clear()
                with self.assertRaises(ValueError):
                    workflow.start_graph(client.call, graph)
                self.assertEqual(client.writes, [])

    def test_bound_research_cannot_escape_guard_by_removing_parent_or_manifest(self):
        for change in ('parent', 'manifest', 'manifest_child'):
            with self.subTest(change=change):
                client = NativeFixture(engine='forex-pilot')
                graph = client.graph()
                workflow.start_graph(client.call, graph)
                client.agent = client.research_agent
                issue = client.call('/issues/' + graph['research'])
                binding = workflow.bind_research(client, issue)
                if change == 'parent':
                    client.rows[graph['research']]['parentId'] = None
                elif change == 'manifest':
                    client.rows[graph['parent']]['description'] = 'ordinary parent'
                else:
                    profile, manifest = workflow.registered_graph(client.rows[graph['parent']])
                    manifest['paper'] = str(uuid4())
                    client.rows[graph['parent']]['description'] = workflow.block(profile['block'], manifest)
                with self.assertRaises(JobError):
                    workflow.guard_research(client, issue, binding=binding)

    def test_forex_profile_reuses_graph_lifecycle_without_changing_spot_contract(self):
        client = NativeFixture(engine='forex-pilot')
        graph = client.graph()
        self.assertEqual(graph, client.graph())
        self.assertIn('naqex-forex-workflow', client.rows[graph['parent']]['description'])
        self.assertEqual(client.rows[graph['research']]['description'], workflow.FOREX_REQUEST)
        self.assertEqual(workflow.start_graph(client.call, graph), 'started')
        self.assertEqual(workflow.start_graph(client.call, graph), 'already_started')
        issue = client.call('/issues/' + graph['research'])
        client.agent = client.research_agent
        workflow.guard_research(client, issue)
        client.rows[graph['parent']]['status'] = 'cancelled'
        with self.assertRaises(JobError):
            workflow.guard_research(client, issue)

    def test_forex_handoff_rejects_wrong_engine_receipt_tamper_and_cancel(self):
        for change in ('none', 'wrong_engine', 'receipt', 'cancel', 'tamper'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as directory:
                client = NativeFixture(engine='forex-pilot')
                graph, root = client.complete_source(directory)
                if change == 'wrong_engine':
                    client.agents[0]['metadata']['naqexEngine'] = 'rd-agent'
                if change == 'receipt':
                    path = root / 'receipt.json'
                    receipt = json.loads(path.read_text())
                    receipt['engine'] = 'rd-agent'
                    path.write_text(json.dumps(receipt))
                if change == 'cancel':
                    client.rows[graph['parent']]['status'] = 'cancelled'
                if change == 'tamper':
                    (root / 'evidence.md').write_text('changed')
                with patch('forex_research.build_report', return_value='numeric fixture report') as builder:
                    if change == 'none':
                        result = workflow.review_source(client, client.call('/issues/' + graph['review']),
                            {'artifact_root': directory}, settle_seconds=0)
                        self.assertIn('numeric fixture report', result['prompt'])
                        self.assertIn('không đề xuất tối ưu chiến lược', result['prompt'])
                        builder.assert_called_once_with({'fixture': True})
                        workflow.finish_review(client, client.call('/issues/' + graph['review']), result)
                        self.assertEqual(client.rows[graph['parent']]['status'], 'in_review')
                        self.assertEqual(client.rows[graph['paper']]['status'], 'blocked')
                    else:
                        with self.assertRaises(JobError):
                            workflow.review_source(client, client.call('/issues/' + graph['review']),
                                {'artifact_root': directory}, settle_seconds=0)
                        builder.assert_not_called()

    def test_mixed_workflow_manifests_and_swapped_graph_ids_are_rejected(self):
        client = NativeFixture()
        graph = client.graph()
        parent = client.rows[graph['parent']]
        parent['description'] += workflow.block('naqex-forex-workflow',
            {k: v for k, v in graph.items() if k in workflow.MANIFEST_KEYS})
        with self.assertRaises(JobError):
            workflow.start_graph(client.call, graph)
        client = NativeFixture()
        graph = client.graph()
        changed = dict(graph, research=graph['review'])
        with self.assertRaises(ValueError):
            workflow.start_graph(client.call, changed)

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

    def test_failed_step_reaches_owner_without_touching_reports_or_paper(self):
        for step in ('research', 'review'):
            with self.subTest(step=step):
                client = NativeFixture(engine='forex-pilot')
                graph = client.graph()
                workflow.start_graph(client.call, graph)
                client.agent = graph['research_agent'] if step == 'research' else client.agent
                client.rows[graph[step]]['status'] = 'done' if step == 'review' else 'blocked'
                before_children = {key: copy.deepcopy(client.rows[graph[key]]) for key in ('research', 'review', 'paper')}
                client.writes.clear()
                self.assertTrue(workflow.report_workflow_failure(client, client.rows[graph[step]],
                                'paperclip_unavailable', review_delivered=step == 'review'))
                parent = client.rows[graph['parent']]
                self.assertEqual((parent['status'], parent['assigneeUserId']), ('blocked', 'local-board'))
                self.assertEqual(parent['unblockDescriptor']['owner'], {'agentId': client.agent})
                for key, before in before_children.items():
                    self.assertEqual(client.rows[graph[key]], before)
                doc = client.docs[graph['parent'], 'workflow-failure-' + client.run]['body']
                self.assertIn('/issues/' + graph[step], doc)
                self.assertIn('Paper chưa chạy', doc)
                self.assertEqual('Báo cáo phản biện đã lưu' in doc, step == 'review')
                self.assertFalse(any('/heartbeat-runs/' in path for path, _, _ in client.writes))

    def test_failure_preserves_owner_changes_cancellation_and_foreign_scope(self):
        for change in ('cancelled', 'in_review', 'reassigned', 'reparented', 'company', 'manifest'):
            with self.subTest(change=change):
                client = NativeFixture()
                graph = client.graph()
                workflow.start_graph(client.call, graph)
                issue = copy.deepcopy(client.rows[graph['review']])
                parent = client.rows[graph['parent']]
                if change in ('cancelled', 'in_review'):
                    parent['status'] = change
                elif change == 'reassigned':
                    client.rows[issue['id']]['assigneeAgentId'] = str(uuid4())
                elif change == 'reparented':
                    client.rows[issue['id']]['parentId'] = str(uuid4())
                elif change == 'company':
                    parent['companyId'] = str(uuid4())
                else:
                    parent['description'] = 'ordinary parent'
                client.writes.clear()
                try:
                    self.assertFalse(workflow.report_workflow_failure(client, issue, 'failed'))
                except JobError:
                    pass
                self.assertEqual(client.writes, [])

    def test_failure_rechecks_parent_after_document_and_sanitizes_error(self):
        client = NativeFixture()
        graph = client.graph()
        workflow.start_graph(client.call, graph)
        original = client.call
        # Retain the fixture transport while simulating a cancellation during publication.
        def cancelling_api(path, body=None, method='GET'):
            result = original(path, body, method)
            if method == 'PUT':
                client.rows[graph['parent']]['status'] = 'cancelled'
            return result
        client.call = cancelling_api
        with self.assertRaises(JobError):
            workflow.report_workflow_failure(client, client.rows[graph['review']], 'secret provider response')
        self.assertEqual(client.rows[graph['parent']]['status'], 'cancelled')
        doc = client.docs[graph['parent'], 'workflow-failure-' + client.run]['body']
        self.assertIn('workflow_failed', doc)
        self.assertNotIn('secret provider response', doc)


if __name__ == '__main__':
    unittest.main()
