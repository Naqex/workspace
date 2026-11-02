"""Prepare a project-local Hermes profile and provision one native worker."""
import argparse
import json
from pathlib import Path
import shutil
import sys

import yaml
from engine_worker import ROOT, load_settings, gateway, uuid
from paperclip_setup import api


def prepare(settings_path):
    settings = load_settings(settings_path)
    base, _ = gateway(settings)
    home = ROOT / '.runtime/hermes/research'
    facts_files = list((home / 'installs').glob('*/facts.json'))
    if len(facts_files) != 1:
        raise ValueError('Inspect Hermes PM install selection before preparing this profile')
    facts = json.loads(facts_files[0].read_text(encoding='utf-8'))
    command = Path(facts['packages']['venv']['environment']) / 'Scripts/python.exe'
    if not command.is_file():
        raise ValueError('Prepare the pinned Hermes core through its PM first')
    # Config and plugin are reproducible; secrets stay in the ignored profile.
    plugins = home / 'plugins/naqex-research'
    plugins.mkdir(parents=True, exist_ok=True)
    for name in ('plugin.yaml', '__init__.py'):
        shutil.copyfile(ROOT / 'tooling/ai-engines/hermes_plugin' / name, plugins / name)
    # The copy is local to the home: resolve shared helpers explicitly at runtime.
    source = (plugins / '__init__.py').read_text(encoding='utf-8')
    source = source.replace("str(Path(__file__).resolve().parents[1])", repr(str(ROOT / 'tooling/ai-engines')))
    (plugins / '__init__.py').write_text(source, encoding='utf-8')
    config = {
        'model': {'default': settings['quick_model'], 'provider': 'custom',
                  'base_url': base},
        'agent': {'max_turns': 6, 'run_budget_seconds': 180,
                  'api_max_retries': 1, 'auto_recovery_cycles': 0},
        'fallback_providers': [], 'plugins': {'enabled': ['naqex-research']},
        'tools': {'tool_search': {'enabled': 'off'}},
        'auxiliary': {'transient_retries': 0,
                      'title_generation': {'enabled': False, 'model_upgrade_enabled': False},
                      'background_review': {'enabled': False}},
        'memory': {'memory_enabled': True, 'user_profile_enabled': False,
                   'memory_char_limit': 2200, 'provider': ''},
        'curator': {'enabled': False}, 'security': {'allow_lazy_installs': False},
    }
    (home / 'config.yaml').write_text(yaml.safe_dump(config, sort_keys=False), encoding='utf-8')
    cwd = home / 'workspace'
    cwd.mkdir(exist_ok=True)
    return {
        'name': 'Chuyên viên phản biện', 'title': 'Chuyên viên phản biện nghiên cứu',
        'role': 'researcher', 'adapterType': 'process',
        'adapterConfig': {
            'command': str(command), 'args': ['-u', str(ROOT / 'tooling/ai-engines/hermes_worker.py'),
                                            '--settings', str(settings_path.resolve())],
            'cwd': str(ROOT), 'timeoutSec': 240, 'graceSec': 5,
        },
        'runtimeConfig': {'heartbeat': {'enabled': False, 'wakeOnDemand': True,
                                       'maxConcurrentRuns': 1, 'maxDailyRuns': 10}},
        'permissions': {'canCreateAgents': False, 'canCreateSkills': False},
        'capabilities': 'Phản biện hồ sơ nghiên cứu, lưu bài học trong profile riêng; không đặt lệnh.',
        'metadata': {'naqexEngine': 'hermes', 'contractVersion': 1},
    }


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--company', required=True, type=uuid)
    parser.add_argument('--settings', type=Path, default=ROOT / '.runtime/ai-engines/settings.json')
    parser.add_argument('--reports-to', type=uuid)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    matches = [a for a in api('/companies/' + args.company + '/agents')
               if (a.get('metadata') or {}).get('naqexEngine') == 'hermes']
    if matches:
        raise ValueError('Hermes worker already exists; inspect it instead of replacing owner settings')
    config = prepare(args.settings)
    if args.reports_to:
        config['reportsTo'] = args.reports_to
    if args.apply:
        agent = api('/companies/' + args.company + '/agents', config, 'POST')
        print(json.dumps({'id': agent['id'], 'status': agent['status']}, ensure_ascii=False))
    else:
        print(json.dumps(config, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    sys.stdout.reconfigure(encoding='utf-8')
    main()
