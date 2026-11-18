import unittest
import json
from pathlib import Path
import tempfile
import numpy as np
from quant_core.discrete_sizing import quantity_grid, largest_feasible
from prop_v26_iso import cents
from quant_core.job_workspace import JobWorkspace
from prop_v26_chunks import prefix


class ExactSizingTests(unittest.TestCase):
    def test_quantity_threshold_uses_integer_units(self):
        q=quantity_grid([820000,820001],[123000],[150000])
        self.assertEqual(q.tolist(),[[1],[1]])
        self.assertEqual(quantity_grid([819999],[123000],[150000]).tolist(),[[0]])

    def test_zero_or_negative_geometry_rejected(self):
        for denominator in (0,-1):
            with self.assertRaisesRegex(ValueError,"INVALID_QUANTITY"):
                quantity_grid([820000],[denominator],[150000])

    def test_nonmonotone_feasibility_reentry_is_not_missed(self):
        ticks=np.arange(1,11)
        result=largest_feasible(ticks,np.arange(10)[:,None],lambda t,q:t,lambda t:t in (1,2,8,9))
        self.assertEqual(result["tick"],9)
        self.assertEqual(result["unique_vectors"],10)
        self.assertTrue(result["all_grid_plateaus_checked"])

    def test_identical_quantity_plateau_is_measured_once(self):
        calls=[]
        r=largest_feasible(np.arange(1,6),np.array([[1],[1],[2],[2],[2]]),
                          lambda t,q:calls.append(t) or int(q[0]),lambda value:True)
        self.assertEqual(r["tick"],5)
        self.assertEqual(len(calls),2)

    def test_no_feasible_grid_point_is_not_promoted(self):
        r=largest_feasible(np.arange(1,4),np.arange(3)[:,None],lambda t,q:0,lambda value:False)
        self.assertIsNone(r["tick"])
        self.assertIsNone(r["selected"])

    def test_cent_conversion_does_not_expand_literal_cap(self):
        self.assertEqual(cents(12.206533333333333),183098)
        self.assertGreater(cents(12.206533333333333),183097)


class JobIsolationTests(unittest.TestCase):
    def test_two_worktrees_get_different_output_and_temp_roots(self):
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory)
            a=JobWorkspace(root/"jobs",root/"checkout-a")
            b=JobWorkspace(root/"jobs",root/"checkout-b")
            try:
                self.assertNotEqual(a.activate(),b.activate())
                self.assertNotEqual(a.environment()["TEMP"],b.environment()["TEMP"])
            finally:
                a.close(); b.close()

    def test_second_writer_is_blocked_and_original_can_continue(self):
        with tempfile.TemporaryDirectory() as directory:
            a=JobWorkspace(directory,directory)
            b=JobWorkspace(directory,directory)
            try:
                a.activate()
                with self.assertRaisesRegex(ValueError,"WRITER_ALREADY"):
                    b.activate()
                self.assertEqual(a.activate(),a.root)
            finally:
                a.close()
            b.activate(); b.close()

    def test_foreign_manifest_is_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            job=JobWorkspace(directory,directory)
            job.activate(); job.close()
            path=job.root/"workspace-owner.json"
            value=json.loads(path.read_text())
            value["workspace"]="foreign"
            path.write_text(json.dumps(value))
            with self.assertRaisesRegex(ValueError,"FOREIGN_JOB"):
                job.activate()
            self.assertEqual(json.loads(path.read_text())["workspace"],"foreign")

    def test_inherited_broker_and_database_settings_are_removed(self):
        with tempfile.TemporaryDirectory() as directory:
            job=JobWorkspace(directory,directory)
            try:
                env=job.environment({"PATH":"keep","TW_V2_DATABASE_URL":"never-use",
                    "TW_AI_GATEWAY_KEY":"never-use","MT5_PASSWORD":"never-use"})
                self.assertEqual(env["PATH"],"keep")
                self.assertFalse(set(env)&{"TW_V2_DATABASE_URL","TW_AI_GATEWAY_KEY","MT5_PASSWORD"})
            finally:
                job.close()

    def test_parent_path_is_rejected_before_any_directory_creation(self):
        with tempfile.TemporaryDirectory() as directory:
            job=JobWorkspace(Path(directory)/"missing"/".."/"escape",directory)
            with self.assertRaisesRegex(ValueError,"MUST_BE_LOCAL"):
                job.activate()
            self.assertFalse((Path(directory)/"missing").exists())


class ReplayResumeTests(unittest.TestCase):
    def test_missing_draw_index_cannot_be_resumed(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory)/"MC-OLHC-paths.jsonl").write_text('{"path":0}\n{"path":2}\n')
            with self.assertRaisesRegex(ValueError,"JOURNAL_INDEX"):
                prefix(Path(directory),"OLHC")

    def test_interrupted_tail_is_preserved_for_reconciliation(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/"MC-OLHC-paths.jsonl"
            text='{"path":0}\n{"path":'
            path.write_text(text)
            with self.assertRaisesRegex(ValueError,"TAIL_REQUIRES"):
                prefix(Path(directory),"OLHC")
            self.assertEqual(path.read_text(),text)
