"""Check file destinations in scoped skill Markdown; no network, anchor checks or writes.

Supports inline links, reference definitions and HTML href/src. Use angle-bracket
destinations for filenames with spaces or parentheses. Scope is explicit to avoid
walking installed/vendor skills. Trigger review is an optional English heuristic.
"""
from __future__ import annotations

import argparse
from pathlib import Path
import re

from check_workspace import ROOT, check_links


def audit(root: Path, scopes: list[Path], review_triggers: bool = False) -> tuple[list[str], list[str], int]:
    errors, warnings = [], []
    skills = set()
    root = root.resolve()
    for scope in scopes:
        scope = (root / scope).resolve()
        if not scope.is_relative_to(root):
            errors.append('Skill scope escapes workspace')
        elif not scope.is_dir():
            errors.append(f'Missing skill scope: {scope.relative_to(root)}')
        else:
            skills.update(scope.rglob('SKILL.md'))
    if not skills and not errors:
        errors.append('No SKILL.md files found in the selected scopes')
    for entry in sorted(skills):
        documents = [entry]
        references = entry.parent / 'references'
        if references.is_dir():
            documents.extend(sorted(references.rglob('*.md')))
        for document in documents:
            if not document.resolve().is_relative_to(root):
                errors.append(f'Skill document escapes workspace: {document.relative_to(root)}')
                continue
            errors.extend(check_links(root, document, check_product_identity=False))
        if review_triggers:
            text = entry.read_text(encoding='utf-8')
            description = re.search(r'^description:\s*(.+)$', text, re.MULTILINE)
            if not description or not re.search(r'\b(?:not|do not|skip|rather than|verification only|use project QA)\b', description[1], re.I):
                warnings.append(f'{entry.relative_to(root)}: review negative trigger manually')
    return errors, warnings, len(skills)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=ROOT, help='Workspace boundary for relative links')
    parser.add_argument('--skills-dir', type=Path, action='append', required=True,
                        help='Explicit skill directory under root; repeat for multiple scopes')
    parser.add_argument('--review-triggers', action='store_true',
                        help='Advisory heuristic only; never a semantic routing verdict')
    args = parser.parse_args()
    errors, warnings, count = audit(args.root, args.skills_dir, args.review_triggers)
    for error in errors:
        print(f'ERROR {error}')
    for warning in warnings:
        print(f'WARNING {warning}')
    print(f'Skill links: {count} skills; {len(errors)} errors; {len(warnings)} advisory warnings.')
    return 1 if errors else 0


if __name__ == '__main__':
    raise SystemExit(main())
