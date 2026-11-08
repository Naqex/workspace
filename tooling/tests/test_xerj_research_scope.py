import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec=importlib.util.spec_from_file_location('xerj_scope',Path(__file__).parents[1]/'search/xerj.py')
xerj=importlib.util.module_from_spec(spec);spec.loader.exec_module(xerj)


class ResearchSearchScopeTests(unittest.TestCase):
    def test_maintained_research_and_current_context_are_opt_in(self):
        for path in ('planning/CURRENT-CONTEXT.md','planning/CONTEXT-LIFECYCLE.md',
                     'planning/research/README.md','planning/research/LOCAL-SESSION-RESULTS-20261108.md',
                     'tooling/ai-engines/STRATEGY-WORKFLOW.md','tooling/ai-engines/OBSERVABILITY.md',
                     'tooling/ai-engines/OPERATIONS.md'):
            with self.subTest(path=path):
                self.assertTrue(xerj.allowed(Path(path),research=True))
                # CodeGraph's shared source_files default keeps its existing corpus.
                self.assertFalse(xerj.allowed(Path(path)))

    def test_raw_private_history_and_holdout_do_not_enter_research_scope(self):
        for path in ('planning/research/prices.csv','planning/research/result.json',
                     'planning/research/private.sqlite3','planning/research/.env',
                     'planning/research/holdout-2025-results.md','planning/research/archive/old.md',
                     'planning/research/Archive/old.md',
                     'planning/archive/2026-11-08-context-storage-review/CURRENT-CONTEXT.snapshot.md',
                     'planning/checkpoints/ai-integrations-20261031/RECEIPT.md',
                     '.runtime/search/admin.key','.runtime/paperclip/instance.md',
                     'planning/research/../../private.md'):
            with self.subTest(path=path):self.assertFalse(xerj.allowed(Path(path),research=True))

    def test_product_corpus_unchanged_and_path_escape_rejected(self):
        self.assertTrue(xerj.allowed(Path('foundation_v2/web/src/App.jsx'),product=True,research=True))
        self.assertTrue(xerj.allowed(Path('foundation_v2/docs/FOREX-RESEARCH.md'),product=True,research=True))
        self.assertFalse(xerj.allowed(Path('foundation_v2/docs/FOREX-RESEARCH.md'),product=True))
        self.assertFalse(xerj.allowed(Path('planning/research/private.md'),product=True,research=True))
        self.assertFalse(xerj.allowed(Path.cwd()/'planning/research/README.md',research=True))

    def test_freshness_requires_research_fingerprint_and_rejects_modified_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);source=root/'report.md';source.write_text('current decision',encoding='utf-8')
            relative=Path('planning/research/report.md');manifest=root/'manifest.json'
            manifest.write_text(json.dumps(dict(files={relative.as_posix():xerj.digest(source)})),encoding='utf-8')
            with patch.object(xerj,'MANIFEST',manifest),patch.object(xerj,'source_files') as files:
                files.return_value=[(relative,source)];xerj.freshness();files.assert_called_once_with(research=True)
                source.write_text('superseded decision',encoding='utf-8')
                with self.assertRaisesRegex(RuntimeError,'stale'):xerj.freshness()

    def test_freshness_rejects_new_document_missing_from_index(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);manifest=root/'manifest.json';manifest.write_text('{"files":{}}',encoding='utf-8')
            source=root/'new.md';source.write_text('new conclusion',encoding='utf-8')
            with patch.object(xerj,'MANIFEST',manifest),patch.object(xerj,'source_files',return_value=[(Path('planning/research/new.md'),source)]):
                with self.assertRaisesRegex(RuntimeError,'stale'):xerj.freshness()


if __name__=='__main__':unittest.main()
