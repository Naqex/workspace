import sys
import unittest
import json
import tempfile
from copy import deepcopy
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from solo_gbp_source_correction import (HOURS, correct_book, verify_cohort, reuse_all,
    canonical_digest, validate_v2_binding, assert_plain_child, verify_refetch_unknown)
from solo_gbp_source import CELL, START, HOUR, census, admit as source_admit, decoded_array, digest


def cohort_fixture():
    rows = []
    for index in range(300):
        at = START + (index + 3) * 24 * HOUR + 8 * HOUR
        count = 11 if index < 24 else 12
        rows.append(dict(id=CELL, asset="GBPUSD", side="BUY", day=str(index),
            decision_msc=at, stop_units=119000, deadline_msc=at+(count-1)*HOUR+HOUR//2,
            deadline_kind="DAY"))
    signals, hours = census(rows)
    result = dict(original_reproduced=True, original_count=300, corrected_count=300,
                  events_added=[], events_removed=[], changes=[], source_only=True,
                  financial_outcomes=False, prices2024_2026_read=False)
    return dict(signals=signals, hours=hours), result


def reuse_fixture():
    original, result = cohort_fixture()
    original.update(reused={}, missing_hours=original["hours"][292:])
    manifest, seals, checks = {}, [], []
    for index, at in enumerate(original["hours"]):
        binary = dict(path=f"source/{at}.ticks", sha256=f"bin{at}", records=3)
        raw = dict(at=at, raw_path=f"source/{at}.json", raw_sha256=f"raw{at}")
        manifest[str(at)] = binary
        if index < 292:
            original["reused"][str(at)] = dict(binary, **raw)
        else:
            seals.append(raw)
        checks.append(dict(at=at, binary_sha256=binary["sha256"], raw_sha256=raw["raw_sha256"]))
    return original, manifest, seals, dict(source_checks=checks), result


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value), encoding="utf-8")


def refetch_fixture(folder):
    urls = ["https://jetta.dukascopy.com/v1/" + suffix for suffix in (
        "ticks/GBP-USD/2022/10/18/12", "ticks/GBP-USD/2022/10/18/15",
        "candles/hour/GBP-USD/BID/2022/10", "candles/hour/GBP-USD/ASK/2022/10")]
    result = dict(requests=[dict(url=url, status="FAILED_UNKNOWN", http_status=202,
        response_headers={"Content-Type":"text/html; charset=UTF-8"}) for url in urls],
        no_retry=True, financial_results_computed=False)
    write(folder / "fetch-results.json", result)
    for index in range(4):
        (folder / f"refetch-{index}.json").write_bytes(b"")
    return result


def book_row(at, close=1.2, volume=3):
    return dict(timestamp=at, open=1.2, high=1.21, low=1.19,
                close=close, volume=volume)


class CorrectionScopeTests(unittest.TestCase):
    def test_only_registered_hours_and_ohlc_are_changed(self):
        rows = [book_row(1666090800000), book_row(HOURS[0]),
                book_row(HOURS[1]), book_row(1666108800000)]
        replacement = {HOURS[0]: [113083, 113461, 112995, 113266],
                       HOURS[1]: [113189, 113190, 112794, 113051]}
        corrected, changes = correct_book(rows, replacement)
        self.assertEqual([row["timestamp"] for row in corrected],
                         [row["timestamp"] for row in rows])
        self.assertEqual([row["volume"] for row in corrected],
                         [row["volume"] for row in rows])
        self.assertEqual([row["at"] for row in changes], list(HOURS))
        self.assertEqual(corrected[0], rows[0])
        self.assertEqual(corrected[3], rows[3])

    def test_refuses_missing_or_extra_correction_hours(self):
        rows = [book_row(HOURS[0]), book_row(HOURS[1])]
        with self.assertRaisesRegex(ValueError, "exact_two_hours"):
            correct_book(rows, {HOURS[0]: [113083, 113461, 112995, 113266]})
        with self.assertRaisesRegex(ValueError, "exact_two_hours"):
            correct_book(rows, {HOURS[0]: [113083, 113461, 112995, 113266],
                                HOURS[1]: [113189, 113190, 112794, 113051],
                                1666108800000: [1, 2, 1, 2]})

    def test_refuses_non_ohlc_change_and_bad_ohlc(self):
        rows = [book_row(HOURS[0]), book_row(HOURS[1])]
        with self.assertRaisesRegex(ValueError, "replacement_OHLC"):
            correct_book(rows, {HOURS[0]: [1, 2, 3, 4],
                                HOURS[1]: [113189, 113190, 112794, 113051]})
        with self.assertRaisesRegex(ValueError, "registered_discrepancy_missing"):
            correct_book(rows, {HOURS[0]: [120000, 121000, 119000, 120000],
                                HOURS[1]: [113189, 113190, 112794, 113051]})

    def test_full_cohort_identity_includes_stop_side_deadline(self):
        original, result = cohort_fixture()
        verify_cohort(original, original["signals"], result)
        self.assertEqual(len(original["hours"]), 3576)
        for key, value in (("stop_units", 118999), ("side", "SELL"), ("deadline_msc", START)):
            changed = deepcopy(original["signals"])
            changed[0][key] = value
            with self.assertRaisesRegex(ValueError, "cohort_or_stop"):
                verify_cohort(original, changed, result)
        with self.assertRaisesRegex(ValueError, "cohort_or_stop"):
            verify_cohort(dict(signals=[], hours=[]), [], result)

    def test_reuse_requires_complete_unique_hash_bound_census(self):
        original, manifest, seals, proof, _ = reuse_fixture()
        self.assertEqual(len(reuse_all(original, manifest, seals, proof)), 3576)
        with self.assertRaisesRegex(ValueError, "census"):
            reuse_all(original, manifest, seals[:-1], proof)
        with self.assertRaisesRegex(ValueError, "census"):
            reuse_all(original, manifest, seals+[seals[0]], proof)
        changed = deepcopy(proof)
        changed["source_checks"][0]["raw_sha256"] = "different"
        with self.assertRaisesRegex(ValueError, "hash_lineage"):
            reuse_all(original, manifest, seals, changed)

    def test_mutated_registration_rejected_before_source_admit(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / "S01-gbp-confirmation"
            job = old.with_name("S01-gbp-confirmation-source-v2")
            reg = dict(job_root=str(job), signals=[])
            reg["registration_sha256"] = canonical_digest(reg)
            reg["signals"] = ["changed"]
            with self.assertRaisesRegex(ValueError, "self_binding"):
                validate_v2_binding(job, reg, old)

    def test_resealed_empty_cohort_and_fake_reuse_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / "S01-gbp-confirmation"
            job = old.with_name("S01-gbp-confirmation-source-v2")
            reg = dict(job_root=str(job), signals=[], hours=[], reused={str(i):{} for i in range(3576)})
            reg["registration_sha256"] = canonical_digest(reg)
            with self.assertRaisesRegex(ValueError, "exact_registered_cohort"):
                validate_v2_binding(job, reg, old)

    def test_precreated_output_child_rejected_before_reading_original(self):
        with tempfile.TemporaryDirectory() as folder:
            old = Path(folder) / "S01-gbp-confirmation"
            job = old.with_name("S01-gbp-confirmation-source-v2")
            (job / "ticks").mkdir(parents=True)
            reg, _ = cohort_fixture()
            reg.update(job_root=str(job),reused={str(at):{} for at in reg["hours"]})
            reg["registration_sha256"] = canonical_digest(reg)
            with self.assertRaisesRegex(ValueError, "output_already_exists"):
                validate_v2_binding(job, reg, old)

    def test_output_junction_flag_and_symlink_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder)
            (job / "ticks").mkdir()
            actual = (job / "ticks").lstat()
            class ReparseMetadata:
                st_file_attributes = 0x400
                st_mode = actual.st_mode
            with patch.object(Path, "lstat", return_value=ReparseMetadata()):
                with self.assertRaisesRegex(ValueError, "link_forbidden"):
                    assert_plain_child(job, "ticks")
            self.assertTrue(actual.st_mode)

    def test_unknown_refetch_requires_exact_four_empty_failed_responses(self):
        with tempfile.TemporaryDirectory() as folder:
            review = Path(folder)
            result = refetch_fixture(review)
            verify_refetch_unknown(review)
            result["requests"][0]["http_status"] = 200
            write(review / "fetch-results.json", result)
            with self.assertRaisesRegex(ValueError, "not_unknown"):
                verify_refetch_unknown(review)
            refetch_fixture(review)
            (review / "refetch-0.json").write_text("{}")
            with self.assertRaisesRegex(ValueError, "body_not_empty"):
                verify_refetch_unknown(review)

    def test_generic_admission_reuses_external_raw_binary_without_materializing(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            old = root / "original"
            old.mkdir()
            job = root / "new"
            job.mkdir()
            at = HOURS[0]
            raw = dict(timestamp=at, multiplier=.00001, bid=1.2, ask=1.2001,
                times=[1, 0, 1000], bids=[0, 2, -1], asks=[0, 2, -1],
                bidVolumes=[1, 2, 3], askVolumes=[1, 2, 3])
            raw_path = old / "raw.json"
            write(raw_path, raw)
            binary = old / "ticks.bin"
            binary.write_bytes(decoded_array(raw, at).tobytes())
            original_bytes = binary.read_bytes()
            books = {}
            pins = []
            for side, values in (("bid", [1.2,1.20002,1.2,1.20001]),
                                 ("ask", [1.2001,1.20012,1.2001,1.20011])):
                path = job / f"2022-gbpusd-{side}.json"
                write(path, [dict(timestamp=at, **dict(zip(("open","high","low","close"),values)))])
                books[f"2022-gbpusd-{side}"] = dict(book=str(path))
                pins.append(dict(path=str(path),sha256=digest(path)))
            reuse = dict(path=str(binary),records=3,sha256=digest(binary),
                         raw_path=str(raw_path),raw_sha256=digest(raw_path))
            write(job / "registration.json", dict(job_root=str(job), input_pins=pins,
                producer_pins=[],hours=[at],missing_hours=[],reused={str(at):reuse},
                h1_source_books=books,prior_stage0_pass=False,signals=[]))
            self.assertTrue(source_admit(job))
            self.assertFalse((job / "source").exists())
            self.assertEqual(list((job / "ticks").iterdir()), [])
            self.assertEqual(binary.read_bytes(), original_bytes)
            self.assertEqual(json.loads((job / "manifest.json").read_text())[str(at)]["path"], str(binary))
            raw_path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "raw_source_changed"):
                source_admit(job)


if __name__ == "__main__":
    unittest.main()
