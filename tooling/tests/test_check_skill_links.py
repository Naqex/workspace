import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

TOOLING = Path(__file__).parents[1]
sys.path.insert(0, str(TOOLING))
spec = importlib.util.spec_from_file_location('check_skill_links', TOOLING / 'check_skill_links.py')
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class SkillLinkTests(unittest.TestCase):
    def make_skill(self, root, content):
        skill = root / '.agents' / 'skills' / 'fixture'
        (skill / 'references').mkdir(parents=True)
        (skill / 'SKILL.md').write_text(
            '---\nname: fixture\ndescription: Test routing; not ordinary product edits.\n---\n' + content,
            encoding='utf-8')
        return skill

    def run_cli(self, root):
        return subprocess.run([sys.executable, str(TOOLING / 'check_skill_links.py'), '--root', str(root),
                               '--skills-dir', '.agents/skills', '--review-triggers'], capture_output=True, text=True)

    def test_relocated_skill_and_reference_links_pass_without_network(self):
        with tempfile.TemporaryDirectory(prefix='Skill links ') as name:
            root = Path(name)
            skill = self.make_skill(root, '[details](<references/a file.md#section>)\n[remote](https://example.invalid)\n'
                                    '[details again][guide]\n[guide]: references/a%20file.md\n'
                                    '~~~md\n[example](missing.md)\n~~~\n`[literal](missing.md)`')
            (root / 'docs').mkdir()
            (root / 'docs' / 'contract.md').write_text('# Contract', encoding='utf-8')
            (skill / 'references' / 'a file.md').write_text('[contract](../../../../docs/contract.md)', encoding='utf-8')
            result = self.run_cli(root)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIn('1 skills; 0 errors; 0 advisory warnings', result.stdout)

    def test_missing_reference_and_escaping_destination_fail_cli(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            skill = self.make_skill(root, '[guide][missing]\n[missing]: references/gone.md')
            (skill / 'references' / 'existing.md').write_text('[escape](../../../../../outside.md)', encoding='utf-8')
            result = self.run_cli(root)
            self.assertEqual(result.returncode, 1)
            self.assertIn('broken link', result.stdout)
            self.assertIn('escapes workspace', result.stdout)

    def test_missing_scope_is_not_a_false_pass_and_trigger_review_is_advisory(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            self.assertTrue(checks.audit(root, [Path('gone')])[0])
            skill = self.make_skill(root, '')
            (skill / 'SKILL.md').write_text('---\nname: fixture\ndescription: Broad generic task.\n---', encoding='utf-8')
            errors, warnings, count = checks.audit(root, [Path('.agents/skills')], True)
            self.assertEqual((errors, count), ([], 1))
            self.assertEqual(len(warnings), 1)
            self.assertEqual(checks.audit(root, [Path('.agents/skills')])[1], [])


if __name__ == '__main__':
    unittest.main()
