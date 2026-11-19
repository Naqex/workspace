import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase, mock

import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import research_inventory as inventory


class ResearchInventoryDocumentTests(TestCase):
    def test_exact_paths_and_ambiguous_basename(self):
        common = "prop-shared"
        nested = inventory.CAMPAIGN + "/" + common
        known = {nested, common, inventory.CAMPAIGN + "/gold-risk-v2"}
        by_name = {common: [nested, common], "gold-risk-v2": [inventory.CAMPAIGN + "/gold-risk-v2"]}
        self.assertEqual(inventory.private_reference("ai-engine-jobs/" + nested, known, by_name),
                         (nested, "scoped_path", ()))
        result = inventory.private_reference(common + "/manifest.json", known, by_name)
        self.assertEqual(result[1], "ambiguous_short_locator")
        self.assertCountEqual(result[2], [nested, common])
        self.assertIsNone(inventory.private_reference("gold-risk-v2-retry/manifest.json", known, by_name))
        self.assertIsNone(inventory.private_reference(
            "ai-engine-jobs/other-study/execution-v1/gold-risk-v2/", known, by_name
        ))
        self.assertIsNone(inventory.private_reference("gold-risk-v2/../manifest.json", known, by_name))

    def test_report_link_is_documentary_and_requires_exact_target(self):
        report = "planning/research/example-report.md"
        protocol = "planning/research/frozen-protocol.md"
        folder = inventory.CAMPAIGN + "/gold-risk-v2"
        text = (
            'Evidence in \x60gold-risk-v2/attempt-1\x60. '
            '[Protocol](frozen-protocol.md#scope), [Protocol](frozen-protocol.md.backup).'
        )
        with mock.patch.object(inventory, "tracked_markdown_lines", return_value=[(report, 12, text)]):
            refs, missing, ambiguous, links = inventory.document_relations("test", {report, protocol}, {folder})
        self.assertEqual(refs[folder], {(f"{report}:12", "unique_short_locator")})
        self.assertFalse(missing or ambiguous)
        self.assertEqual(links, [{"source": report, "target": protocol, "label": "protocol", "line": 12,
                                  "binding": "document_reference_only"}])

    def test_manifest_locator_is_stat_only_until_exact_pin_is_registered(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            folder = root / "prop-example"
            folder.mkdir()
            manifest = folder / "manifest.json"
            manifest.write_bytes(b"this unrecognized manifest must stay unopened")
            graph = {"metadata_bindings": [], "partitions": [], "payload_refs": [], "tracked_base": "test",
                     "private_directory_scope": [{"prefix": ".", "name_prefix": "prop-"}]}
            with mock.patch.object(inventory, "tracked_markdown_lines", return_value=[]):
                with mock.patch.object(Path, "read_bytes", side_effect=AssertionError("opened private file")):
                    result = inventory.verify_private(graph, root, {}, {}, set())
            row = result["directories"][0]
            self.assertEqual(row["status"], "artifact_locator_present")
            self.assertEqual(row["root_artifact_locators"], ["manifest.json"])
            self.assertEqual(row["verified_metadata"], [])
            self.assertEqual(row["source_run_binding_basis"], [])

    def test_known_manifest_proves_declared_roles_without_opening_references(self):
        with TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            folder = root / "prop-test"
            folder.mkdir()
            registration, outcome = folder / "registration.md", folder / "rows.json.zst"
            for path in (registration, outcome):
                path.touch()
            entries = {registration.name: "1" * 64, outcome.name: "2" * 64}
            wire = json.dumps(entries).encode()
            manifest = folder / "manifest.json"
            manifest.write_bytes(wire)
            digest = inventory.sha256(wire).hexdigest()
            report = root / "report.md"
            report.write_text(f"manifest SHA256 {digest}", encoding="utf-8")
            row = {"path": "prop-test/manifest.json", "document": "report.md", "sha256": digest,
                   "entries": {"run_input": [registration.name], "output": [outcome.name]}}
            original = Path.read_bytes

            def read(path):
                self.assertEqual(path, manifest)
                return original(path)

            with mock.patch.object(inventory, "ROOT", root), mock.patch.object(Path, "read_bytes", read):
                result = inventory.verify_document_manifests({"document_manifest_bindings": [row]}, root, {"report.md"})
            self.assertEqual(result["prop-test"]["status"], "metadata_hash_verified")
            locators = result["prop-test"]["declared_artifact_bindings"]
            self.assertEqual({x["role"] for x in locators}, {"run_input", "output"})
            self.assertTrue(all(x["present"] and not x["content_verified"] for x in locators))
