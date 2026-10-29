import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("check_workspace", Path(__file__).parents[1] / "check_workspace.py")
checks = importlib.util.module_from_spec(spec)
spec.loader.exec_module(checks)


class WorkspaceContractsTests(unittest.TestCase):
    def test_relative_links_work_in_relocated_workspace_with_spaces(self):
        with tempfile.TemporaryDirectory(prefix="Naqex workspace ") as name:
            root = Path(name)
            (root / "docs").mkdir()
            (root / "docs" / "a file.md").write_text("# Target", encoding="utf-8")
            guide = root / "README.md"
            guide.write_text('[guide](<docs/a file.md#target>) <img src="docs/a%20file.md">', encoding="utf-8")
            self.assertEqual(checks.check_links(root, guide), [])

    def test_broken_and_escape_links_are_reported(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            guide = root / "README.md"
            guide.write_text("[missing](gone.md) [outside](../outside.md)", encoding="utf-8")
            errors = checks.check_links(root, guide)
            self.assertEqual(len(errors), 2)
            self.assertTrue(any("escapes workspace" in error for error in errors))

    def test_windows_absolute_link_is_rejected(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            guide = root / "README.md"
            guide.write_text("[machine path](D:/private/README.md)", encoding="utf-8")
            self.assertIn("local absolute link", checks.check_links(root, guide)[0])

    def test_external_links_and_code_examples_are_not_local_paths(self):
        with tempfile.TemporaryDirectory() as name:
            root = Path(name)
            guide = root / "README.md"
            guide.write_text('[web](https://example.org)\n```md\n[example](gone.md)\n```', encoding="utf-8")
            self.assertEqual(checks.check_links(root, guide), [])

    def test_topology_checks_ownership_and_gitlink_mode(self):
        modules = "\n".join(f'[submodule "{path}"]\npath = {path}\nurl = {url}' for path, url in checks.PRODUCTS.items())
        index = "\n".join(f'160000 {"a" * 40} 0\t{path}' for path in checks.PRODUCTS)
        self.assertEqual(checks.check_topology(modules, index), [])
        bad = modules.replace("https://github.com/Naqex/trader.git", "https://github.com/old/trader.git")
        self.assertTrue(any("identity" in error for error in checks.check_topology(bad, index)))
        self.assertTrue(any("pin" in error for error in checks.check_topology(modules, index.replace("160000", "100644", 1))))


if __name__ == "__main__":
    unittest.main()
