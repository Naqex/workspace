"""Bounded Studio controls; Paperclip remains the only task/run store."""
import json
import re
import sys

from engine_worker import JobError, ROOT, uuid
from spot_workflow import PROFILES, create_graph, registered_graph, start_graph, cancel_graph
from studio_observation import observe_step


def available_worker(api, company, engine):
    rows = [a for a in api('/companies/' + company + '/agents')
            if (a.get('metadata') or {}).get('naqexEngine') == engine]
    if len(rows) != 1 or rows[0]['status'] not in ('idle', 'running', 'error'):
        raise ValueError('worker_unavailable')
    return rows[0]['id']


def observation_root():
    # Reading/stopping native work must not depend on model preflight succeeding.
    try:
        from pathlib import Path
        settings = json.loads((ROOT / '.runtime/ai-engines/settings.json').read_text(encoding='utf-8-sig'))
        root = settings.get('artifact_root')
        return root if isinstance(root, str) and Path(root).is_absolute() else None
    except (OSError, ValueError, AttributeError):
        return None


def read_graph(api, company, parent_id, artifact_root=None):
    parent = api('/issues/' + parent_id)
    profile, manifest = registered_graph(parent)
    if parent['companyId'] != company or manifest is None:
        raise ValueError('workflow_scope')
    children = {key: api('/issues/' + manifest[key]) for key in ('research', 'review', 'paper')}
    for child in children.values():
        if (child['companyId'] != company or child.get('parentId') != parent_id
                or child.get('projectId') != parent.get('projectId')):
            raise ValueError('workflow_scope')
    source = children['research']
    steps = [{'role': key, **{field: child.get(field) for field in ('id', 'title', 'status', 'executionRunId')},
              'observation': observe_step(api, company, child,
                  profile['engine'] if key == 'research' else 'hermes', artifact_root)}
             for key, child in children.items()]
    return {
        'id': parent_id, 'company': company, 'project': parent.get('projectId'),
        'title': parent['title'], 'identifier': parent.get('identifier'), 'status': parent['status'],
        'profile': next(key for key, value in PROFILES.items() if value is profile),
        'can_start': (parent['status'] in ('backlog', 'todo') and not parent.get('assigneeAgentId')
                      and not parent.get('assigneeUserId') and source['status'] == 'backlog'
                      and not source.get('startedAt') and not source.get('assigneeAgentId')
                      and not source.get('assigneeUserId')
                      and source.get('description') == profile['request']
                      and all(s['observation']['state'] == 'not_started' for s in steps)),
        'can_cancel': parent['status'] not in ('done', 'in_review') and (
            parent['status'] != 'cancelled' or any(c['status'] not in ('done', 'cancelled') for c in children.values())),
        'steps': steps,
    }


def operate(api, request, artifact_root=None):
    if not isinstance(request, dict):
        raise ValueError('invalid_request')
    action = request.get('action')
    fields = {
        'overview': {'company', 'project'}, 'get': {'company', 'parent'},
        'create': {'company', 'project', 'profile', 'key'},
        'start': {'company', 'parent'}, 'cancel': {'company', 'parent'},
    }
    if action not in fields or set(request) - fields[action] - {'action'}:
        raise ValueError('invalid_request')
    for field in ('company', 'project', 'parent'):
        if request.get(field):
            request[field] = uuid(request[field])
    company = request.get('company')
    if action == 'overview':
        companies = [{k: c[k] for k in ('id', 'name')} for c in api('/companies')]
        if company and company not in {c['id'] for c in companies}:
            raise ValueError('workflow_scope')
        company = company or (companies[0]['id'] if len(companies) == 1 else None)
        result = {'companies': companies, 'company': company, 'projects': [], 'project': None,
                  'workflows': [], 'profiles': [{'id': key, 'title': value['title']} for key, value in PROFILES.items()]}
        if not company:
            return result
        result['projects'] = [{k: p[k] for k in ('id', 'name')} for p in api('/companies/' + company + '/projects')
                              if p['companyId'] == company]
        project = request.get('project')
        if project and project not in {p['id'] for p in result['projects']}:
            raise ValueError('workflow_scope')
        project = project or (result['projects'][0]['id'] if len(result['projects']) == 1 else None)
        result['project'] = project
        if project:
            # Recent native tasks only; this is not a second history/acceptance ledger.
            rows = api('/companies/' + company + '/issues?projectId=' + project + '&limit=200')
            for parent in sorted(rows, key=lambda r: r.get('updatedAt') or '', reverse=True):
                if parent.get('projectId') != project or parent.get('parentId') or parent['status'] == 'cancelled':
                    continue
                try:
                    _, manifest = registered_graph(parent)
                except JobError:
                    continue
                if manifest is not None:
                    result['workflows'].append({key: parent.get(key) for key in ('id', 'identifier', 'title', 'status')})
                if len(result['workflows']) == 10:
                    break
        return result
    if not company:
        raise ValueError('workflow_scope')
    if action == 'create':
        if set(request) != fields[action] | {'action'} or request['profile'] not in PROFILES:
            raise ValueError('invalid_request')
        if not isinstance(request['key'], str) or not re.fullmatch(r'studio-[a-f0-9-]{36}', request['key']):
            raise ValueError('invalid_request')
        project = api('/projects/' + request['project'])
        if project['companyId'] != company:
            raise ValueError('workflow_scope')
        graph = create_graph(api, company, project['id'], request['key'], workflow=request['profile'],
                             title=PROFILES[request['profile']]['title'])
        return read_graph(api, company, graph['parent'], artifact_root)
    if set(request) != fields[action] | {'action'}:
        raise ValueError('invalid_request')
    graph = read_graph(api, company, request['parent'], artifact_root)
    if action == 'start':
        if not graph['can_start']:
            return {**graph, 'action': 'not_started'}
        parent = api('/issues/' + graph['id'])
        profile, manifest = registered_graph(parent)
        review = api('/issues/' + manifest['review'])
        paper = api('/issues/' + manifest['paper'])
        if (review['status'] != 'blocked' or {r['id'] for r in review.get('blockedBy', [])} != {manifest['research']}
                or review.get('assigneeAgentId') != available_worker(api, company, 'hermes')
                or paper['status'] != 'blocked' or paper.get('assigneeAgentId') or paper.get('assigneeUserId')):
            raise ValueError('workflow_changed')
        start_graph(api, {'parent': graph['id'], **manifest,
                         'research_agent': available_worker(api, company, profile['engine'])})
    elif action == 'cancel':
        if graph['can_cancel']:
            cancel_graph(api, graph['id'])
    return read_graph(api, company, graph['id'], artifact_root)


def main():
    from paperclip_setup import api
    try:
        wire = sys.stdin.buffer.read(8193)
        if len(wire) > 8192:
            raise ValueError('invalid_request')
        result = operate(api, json.loads(wire), observation_root())
        print(json.dumps({'ok': True, 'result': result}, ensure_ascii=False))
    except Exception as error:
        code = error.code if isinstance(error, JobError) else str(error) if type(error) is ValueError else 'paperclip_unavailable'
        if code == 'paperclip_http_404':
            code = 'workflow_scope'
        if code not in ('invalid_request', 'workflow_scope', 'workflow_changed', 'worker_unavailable'):
            code = 'paperclip_unavailable'
        # No raw HTTP/exception/provider output crosses into the host UI.
        print(json.dumps({'ok': False, 'error': code}))
        return 2
    return 0


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    raise SystemExit(main())
