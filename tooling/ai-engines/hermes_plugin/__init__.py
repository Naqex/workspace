"""Project plugin; no changes to Hermes core or general host execution tools."""
import json
import os
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from engine_worker import Paperclip, ROOT, load_settings, uuid

ALLOWED_TOOLS = frozenset({'research_publish', 'memory', 'session_search'})


def run_directory():
    settings = load_settings(ROOT / '.runtime/ai-engines/settings.json')
    company = uuid(os.environ['PAPERCLIP_COMPANY_ID'])
    run = uuid(os.environ['PAPERCLIP_RUN_ID'])
    directory = Path(settings['artifact_root']) / company / run
    directory.mkdir(parents=True, exist_ok=True)
    return directory


def publish(args, **kwargs):
    try:
        if set(args) != {'report'}:
            raise ValueError('Only the report field is accepted')
        report = args['report']
        if not isinstance(report, str) or not 200 <= len(report) <= 20000:
            raise ValueError('Report must contain 200 to 20000 characters')
        client = Paperclip()
        issue = client.assigned_issue()
        directory = run_directory()
        if (directory / 'review-source.json').is_file() or '```naqex-review' in (issue.get('description') or ''):
            from spot_workflow import verify_review_source
            settings = load_settings(ROOT / '.runtime/ai-engines/settings.json')
            verify_review_source(client, issue, settings, directory)
        (directory / 'review.md').write_text(report, encoding='utf-8')
        client.call('/issues/' + issue['id'] + '/documents/engine-' + client.run,
                    {'title': 'Kết quả phản biện', 'format': 'markdown', 'body': report}, 'PUT')
        (directory / 'publication.json').write_text(json.dumps({
            'issue': issue['id'], 'run': client.run, 'status': 'attached',
            'strategy_qualified': False, 'execution_authorized': False,
        }), encoding='utf-8')
        return json.dumps({'status': 'attached', 'issue': issue['id']})
    except Exception:
        # Provider-visible errors must never expose credentials or API diagnostics.
        return json.dumps({'error': 'Publication failed. Check assigned task, current run and report length. Do not retry blindly.'})


def guard(tool_name, **kwargs):
    if tool_name not in ALLOWED_TOOLS:
        return {'action': 'block', 'message': 'This research pilot only permits publication, memory and session search.'}


def usage(**event):
    if not os.environ.get('PAPERCLIP_RUN_ID'):
        return  # Native connection probes have no task/run artifact scope.
    # Keep metadata only; raw requests/responses can contain task data or secrets.
    fields = ('session_id', 'api_request_id', 'model', 'response_model', 'api_duration',
              'usage', 'finish_reason', 'aux_task', 'error_type')
    row = {key: event[key] for key in fields if key in event}
    with (run_directory() / 'usage.jsonl').open('a', encoding='utf-8') as stream:
        stream.write(json.dumps(row, ensure_ascii=False) + '\n')


def register(ctx):
    ctx.register_tool(name='research_publish', toolset='naqex_research', handler=publish,
        schema={'name': 'research_publish',
                'description': 'Attach the final Vietnamese research review to your currently assigned Paperclip task. The worker marks it done only after this model turn completes. No trading authority is granted.',
                'parameters': {'type': 'object', 'properties': {'report': {'type': 'string'}},
                               'required': ['report'], 'additionalProperties': False}})
    ctx.register_hook('pre_tool_call', guard)
    ctx.register_hook('post_api_request', usage)
    ctx.register_hook('post_auxiliary_call', usage)
