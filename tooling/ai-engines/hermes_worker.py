"""One Hermes SDK task in a native Paperclip-owned process; no CLI daemon."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from engine_worker import JobError, Paperclip, RATE_LIMIT_MESSAGE, ROOT, clean_environment, gateway, load_settings, source_pin
from spot_workflow import review_source, verify_review_source, finish_review, report_workflow_failure


def execute(settings_path):
    client = Paperclip()
    issue = client.assigned_issue()
    prompt = issue.get('description') or ''
    if not 100 <= len(prompt) <= 20000:
        raise ValueError('Research task must contain 100 to 20000 characters')
    settings = load_settings(settings_path)
    directory = Path(settings['artifact_root']) / client.company / client.run
    directory.mkdir(parents=True, exist_ok=False)
    receipt = {'engine': 'hermes', 'run': client.run, 'issue': issue['id'], 'status': 'preflight',
               'provider_work_started': False,
               'started_at': datetime.now(timezone.utc).isoformat(),
               'input_sha256': hashlib.sha256(prompt.encode()).hexdigest(),
               'execution_authorized': False, 'strategy_qualified': False}
    start = time.perf_counter()
    agent = None
    try:
        source = review_source(client, issue, settings)
        if source is not None:
            prompt = source['prompt']
            receipt['input_sha256'] = hashlib.sha256(prompt.encode()).hexdigest()
            receipt['source'] = source['binding']
            (directory / 'review-source.json').write_text(json.dumps(source['binding'], indent=2), encoding='utf-8')
            (directory / 'dossier.md').write_text(source['dossier'], encoding='utf-8')
            client.call('/issues/' + issue['id'] + '/documents/source-' + client.run,
                        {'title': 'Nguồn và số liệu phản biện', 'format': 'markdown', 'body': source['dossier']}, 'PUT')
        receipt['source_commit'] = source_pin('hermes')
        receipt['worker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
        instructions_root = ROOT / 'tooling/ai-engines'
        instructions = ((instructions_root / 'hermes_instructions.md').read_text(encoding='utf-8')
                        + '\n\n' + (instructions_root / 'paperclip-skills/naqex-research-lead/references/owner-reporting.md').read_text(encoding='utf-8'))
        receipt['instructions_sha256'] = hashlib.sha256(instructions.encode()).hexdigest()
        memory = ROOT / '.runtime/hermes/research/memories/MEMORY.md'
        receipt['memory_sha256_before'] = hashlib.sha256(memory.read_bytes()).hexdigest() if memory.is_file() else None
        # Scope before importing Hermes: its modules cache profile/config at import.
        clean_environment()
        os.environ['HERMES_HOME'] = str(ROOT / '.runtime/hermes/research')
        os.environ['HERMES_RUNTIME_DIR'] = str(ROOT / '.runtime/hermes/tools')
        # Hermes exposes its SDK from the source checkout, outside its CLI PM shim.
        sys.path.insert(0, str(ROOT / 'projects/integrations/hermes-agent'))
        import hermes_yaml
        base, key = gateway(settings, yaml_loader=hermes_yaml.safe_load)
        from run_agent import AIAgent
        from hermes_state import SessionDB
        with SessionDB() as database:
            agent = AIAgent(model=settings['quick_model'], provider='custom', api_mode='chat_completions',
                            base_url=base, api_key=key, max_iterations=6, run_budget_seconds=180,
                            enabled_toolsets=['naqex_research', 'memory', 'session_search'],
                            ephemeral_system_prompt=instructions,
                            session_id='naqex-' + client.run, session_db=database,
                            skip_context_files=True, skip_background_review=True, quiet_mode=True,
                            cwd=str(ROOT / '.runtime/hermes/research/workspace'))
            from hermes_plugin import ALLOWED_TOOLS
            names = {tool['function']['name'] if 'function' in tool else tool['name'] for tool in agent.tools}
            if not names or not names <= ALLOWED_TOOLS:
                raise ValueError('Unexpected Hermes tool inventory')
            receipt.update(status='running', model=settings['quick_model'], tools=sorted(names),
                           runtime_module=sys.modules['run_agent'].__file__)
            if source is not None:
                verify_review_source(client, issue, settings, directory)
            receipt['provider_work_started'] = True
            (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            result = agent.run_conversation(prompt)
            (directory / 'final-response.md').write_text(result.get('final_response') or '', encoding='utf-8')
            receipt.update(api_calls=result.get('api_calls'), session_id=agent.session_id)
            if not result.get('completed') and result.get('failure_reason') in ('rate_limit', 'upstream_rate_limit'):
                raise JobError('model_rate_limited', RATE_LIMIT_MESSAGE)
            if not result.get('completed') or not (directory / 'publication.json').is_file():
                raise RuntimeError('Hermes did not complete publication')
            agent.close()
            agent = None
        if source is not None:
            verify_review_source(client, issue, settings, directory)
        client.call('/issues/' + issue['id'], {'status': 'done',
                    'comment': 'Đã lưu báo cáo phản biện. Kết quả chưa cấp quyền chạy demo hoặc tiền thật.'}, 'PATCH')
        receipt['review_delivery'] = 'published'
        finish_review(client, issue, source)
        receipt['status'] = 'completed'
        return 0
    except Exception as error:
        receipt.update(status='failed', error_type=type(error).__name__,
                       error=getattr(error, 'code', type(error).__name__))
        if receipt['error'] == 'model_rate_limited':
            receipt['operator_action'] = RATE_LIMIT_MESSAGE
        # Do not repeat a potentially completed publication or provider attempt.
        print(receipt.get('operator_action', 'Hermes chưa hoàn tất. Xem receipt local; không tự chạy lại.'), flush=True)
        if issue.get('parentId'):
            try:
                receipt['failure_delivery'] = 'published' if report_workflow_failure(
                    client, issue, receipt['error'], review_delivered=receipt.get('review_delivery') == 'published') else 'not_applicable'
            except Exception:
                receipt['failure_delivery'] = 'unavailable'
            try:
                current = client.call('/issues/' + issue['id'])
                if (current['status'] not in ('done', 'cancelled', 'blocked')
                        and current.get('assigneeAgentId') == client.agent
                        and current.get('parentId') == issue['parentId']):
                    client.call('/issues/' + issue['id'], {'status': 'blocked',
                                'unblockDescriptor': {'owner': {'agentId': client.agent}, 'action': receipt.get(
                                    'operator_action', 'Xử lý nguyên nhân lỗi trong lượt phản biện và receipt trước khi thử lại.')}}, 'PATCH')
            except Exception:
                receipt['issue_failure_delivery'] = 'unavailable'
        return 1
    finally:
        if agent is not None:
            try:
                agent.close()
            except Exception:
                receipt['cleanup_error'] = True
        receipt['seconds'] = time.perf_counter() - start
        (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    parser = argparse.ArgumentParser()
    parser.add_argument('--settings', type=Path, required=True)
    raise SystemExit(execute(parser.parse_args().settings))
