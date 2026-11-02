"""One Hermes SDK task in a native Paperclip-owned process; no CLI daemon."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time

from engine_worker import Paperclip, ROOT, clean_environment, gateway, load_settings, source_pin


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
        receipt['source_commit'] = source_pin('hermes')
        receipt['worker_sha256'] = hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
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
                            ephemeral_system_prompt=(ROOT / 'tooling/ai-engines/hermes_instructions.md').read_text(encoding='utf-8'),
                            session_id='naqex-' + client.run, session_db=database,
                            skip_context_files=True, skip_background_review=True, quiet_mode=True,
                            cwd=str(ROOT / '.runtime/hermes/research/workspace'))
            from hermes_plugin import ALLOWED_TOOLS
            names = {tool['function']['name'] if 'function' in tool else tool['name'] for tool in agent.tools}
            if not names or not names <= ALLOWED_TOOLS:
                raise ValueError('Unexpected Hermes tool inventory')
            receipt.update(status='running', model=settings['quick_model'], tools=sorted(names),
                           runtime_module=sys.modules['run_agent'].__file__)
            receipt['provider_work_started'] = True
            (directory / 'receipt.json').write_text(json.dumps(receipt, indent=2), encoding='utf-8')
            result = agent.run_conversation(prompt)
            (directory / 'final-response.md').write_text(result.get('final_response') or '', encoding='utf-8')
            receipt.update(api_calls=result.get('api_calls'), session_id=agent.session_id)
            if not result.get('completed') or not (directory / 'publication.json').is_file():
                raise RuntimeError('Hermes did not complete publication')
            agent.close()
            agent = None
        receipt['status'] = 'completed'
        client.call('/issues/' + issue['id'], {'status': 'done',
                    'comment': 'Đã lưu báo cáo phản biện. Kết quả chưa cấp quyền chạy demo hoặc tiền thật.'}, 'PATCH')
        return 0
    except Exception as error:
        receipt.update(status='failed', error_type=type(error).__name__)
        # Do not repeat a potentially completed publication or provider attempt.
        print('Hermes chưa hoàn tất. Xem receipt local; không tự chạy lại.', flush=True)
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
