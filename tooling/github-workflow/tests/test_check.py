import copy
import importlib.util
from pathlib import Path
import unittest

import yaml

BASE = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("workflow_check", BASE / "check.py")
check = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check)


class WorkflowContracts(unittest.TestCase):
    def test_owned_forms_and_missing_acceptance(self):
        for name in ("bug", "task"):
            with self.subTest(name=name):
                form = yaml.safe_load((check.ROOT / ".github/ISSUE_TEMPLATE" / f"{name}.yml").read_text(encoding="utf-8"))
                check.check_form(form)
                damaged = copy.deepcopy(form)
                damaged["body"] = [f for f in damaged["body"] if f.get("id") != "acceptance"]
                with self.assertRaises(ValueError):
                    check.check_form(damaged)

    def test_duplicate_identity_fields_rejected(self):
        form = yaml.safe_load((check.ROOT / ".github/ISSUE_TEMPLATE/bug.yml").read_text(encoding="utf-8"))
        form["body"].append(copy.deepcopy(form["body"][0]))
        with self.assertRaises(ValueError):
            check.check_form(form)

    def test_human_unknown_and_future_models(self):
        for trailers in ("", "AI-Tool: Codex\nAI-Model-Requested: unknown", "AI-Tool: Other\nAI-Model-Requested: provider/future-v2030", "AI-Tool: Codex\nAI-Model-Requested: route/high\nAI-Tool: Other\nAI-Model-Requested: new-id"):
            with self.subTest(trailers=trailers):
                check.check_trailers(f"fix: example\n\n{trailers}\n")

    def test_partial_and_empty_attribution_rejected(self):
        for trailers in ("AI-Tool: Codex", "AI-Model-Requested: unknown", "AI-Tool: Codex\nAI-Model-Requested: "):
            with self.subTest(trailers=trailers), self.assertRaises(ValueError):
                check.check_trailers(f"fix: example\n\n{trailers}\n")


if __name__ == "__main__":
    unittest.main()
