"""Preview/export reviewed repo skills, optionally publish via native Paperclip API.

No engine dispatch, service startup, provider calls or direct database writes.
Apply is explicit and requires a private receipt path for backup/reconciliation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[2]
SOURCES = {
    'strategy-research': ROOT / '.agents/skills/strategy-research',
    'strategy-qualification': ROOT / '.agents/skills/strategy-qualification',
    'naqex-research-lead': ROOT / 'tooling/ai-engines/paperclip-skills/naqex-research-lead',
}


def package(root=ROOT):
    skills = []
    for slug, source in SOURCES.items():
        source = root / source.relative_to(ROOT)
        paths = [source / 'SKILL.md', *sorted((source / 'references').rglob('*.md'))]
        files = {}
        for path in paths:
            if not path.resolve().is_relative_to(source.resolve()):
                raise ValueError('package file escapes skill root')
            files[path.relative_to(source).as_posix()] = path.read_text(encoding='utf-8')
        markdown = files['SKILL.md']
        name = re.search(r'^name:\s*(.+)$', markdown, re.M)
        description = re.search(r'^description:\s*(.+)$', markdown, re.M)
        if not name or name[1] != slug or not description:
            raise ValueError('skill metadata differs from allowlisted source')
        skills.append(dict(slug=slug, name=name[1], description=description[1], files=files))
    return dict(schema='naqex-strategy-skills-bundle-v1', skills=skills)


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding='utf-8')
    temporary.replace(path)


def publish(api, bundle, company, agent_id, receipt_path):
    if receipt_path.exists():
        raise ValueError('receipt must be new; inspect the previous attempt before resuming with a new receipt')
    agent = api('/agents/' + agent_id)
    if agent.get('companyId') != company or agent.get('adapterType') != 'codex_local':
        raise ValueError('target must be the company native codex_local lead, not a process worker')
    if agent.get('status') != 'idle':
        raise ValueError('lead must be idle before changing its skill package')
    existing = api('/companies/' + company + '/skills')
    snapshot = api('/agents/' + agent_id + '/skills')
    receipt = dict(schema='naqex-strategy-skills-publication-v1', company_id=company,
                   agent_id=agent_id, status='prepared', desired_skills_before=snapshot['desiredSkills'],
                   backups=[], actions=[])
    # Collect source snapshots before the first mutation. Keep unrelated skills
    # and all existing selections; reject ambiguous/unmanaged slug collisions.
    selected = {}
    for skill in bundle['skills']:
        matches = [row for row in existing if row['slug'] == skill['slug']]
        if len(matches) > 1:
            raise ValueError('duplicate native skill slug')
        if matches:
            row = matches[0]
            if row.get('sourceType') != 'managed':
                raise ValueError('refuse to overwrite imported/upstream skill')
            selected[skill['slug']] = row
            for path in skill['files']:
                inventory = {entry['path'] for entry in row['fileInventory']}
                if path in inventory:
                    file = api(f"/companies/{company}/skills/{row['id']}/files?path={path}")
                    receipt['backups'].append(dict(skill_id=row['id'], path=path, content=file['content'],
                                                   version_id=row['currentVersionId']))
    save(receipt_path, receipt)
    keys = []
    for skill in bundle['skills']:
        slug = skill['slug']
        row = selected.get(slug)
        if row is None:
            content_hash = hashlib.sha256(skill['files']['SKILL.md'].encode()).hexdigest()
            row = api('/companies/' + company + '/skills', dict(
                name=skill['name'], slug=slug, description=skill['description'],
                markdown=skill['files']['SKILL.md'], sharingScope='company',
                idempotencyKey=f'naqex:{slug}:{content_hash}'), 'POST')
            receipt['actions'].append(dict(action='created', skill_id=row['id'], slug=slug))
            save(receipt_path, receipt)
        for path, content in skill['files'].items():
            row = api(f"/companies/{company}/skills/{row['id']}")
            inventory = {entry['path'] for entry in row['fileInventory']}
            current = api(f"/companies/{company}/skills/{row['id']}/files?path={path}") if path in inventory else None
            if current is not None and current['content'] == content:
                continue
            content_hash = hashlib.sha256(content.encode()).hexdigest()
            body = dict(path=path, content=content, expectedVersionId=row['currentVersionId'],
                        idempotencyKey=f"naqex:{slug}:{row['currentVersionId']}:{content_hash}")
            api(f"/companies/{company}/skills/{row['id']}/files", body, 'PATCH')
            receipt['actions'].append(dict(action='updated_file', skill_id=row['id'], path=path))
            save(receipt_path, receipt)
        row = api(f"/companies/{company}/skills/{row['id']}")
        for path, content in skill['files'].items():
            file = api(f"/companies/{company}/skills/{row['id']}/files?path={path}")
            if file['content'] != content:
                raise ValueError('published skill content differs; stop before assignment')
        keys.append(row['key'])
    current_agent = api('/agents/' + agent_id)
    if current_agent.get('status') != 'idle':
        raise ValueError('lead became active; stop before assignment and reconcile')
    if not set(keys).issubset(snapshot['desiredSkills']):
        api('/agents/' + agent_id + '/skills/sync', dict(mode='add', desiredSkills=keys), 'POST')
    after = api('/agents/' + agent_id + '/skills')
    if not set(keys).union(snapshot['desiredSkills']).issubset(after['desiredSkills']):
        raise ValueError('native desired skill assignment failed or removed an existing selection')
    receipt.update(status='published_and_assigned', desired_skills_after=after['desiredSkills'],
                   model_execution_verified=False)
    save(receipt_path, receipt)
    return receipt


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--bundle', type=Path, help='Export reviewed Markdown package locally; no API call')
    parser.add_argument('--company')
    parser.add_argument('--agent')
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args(argv)
    bundle = package()
    if args.bundle:
        if args.bundle.exists():
            parser.error('bundle output must be new')
        save(args.bundle, bundle)
    if args.apply:
        if not all((args.company, args.agent, args.receipt)):
            parser.error('--apply requires --company, --agent and a new --receipt')
        from paperclip_setup import api
        publish(api, bundle, args.company, args.agent, args.receipt)
    print(json.dumps(dict(skills=[dict(slug=s['slug'], files=len(s['files'])) for s in bundle['skills']],
                          applied=args.apply, model_execution_verified=False)))


if __name__ == '__main__':
    main()
