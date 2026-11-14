from pathlib import Path
import sys
import unittest
import json
import tempfile

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from prop_campaign_source import stamp, HOUR
from prop_portfolio_scan import gap_unknown
from solo_gbp_source import CELL, START, END, census, decoded_array, compare_h1, output_root, digest, admit, held_path_quality


class InstrumentGapTests(unittest.TestCase):
    def test_us500_maintenance_does_not_hide_fx_or_gold_outage(self):
        # New York observes daylight saving: 20:15 UTC is 16:15 local.
        times = np.array([stamp("2022-07-18T20:15:00"),
                          stamp("2022-07-18T22:00:00")])
        self.assertEqual(gap_unknown(times, 0, asset="US500"), [])
        for asset in ("GBPUSD", "EURUSD", "AUDUSD", "XAUUSD"):
            with self.subTest(asset=asset):
                self.assertEqual(gap_unknown(times, 0, asset=asset),
                                 [(int(times[0]), int(times[1]))])

    def test_us500_exception_ends_at_registered_reopening(self):
        for start, end in (("20:15:00", "22:01:00"),
                           ("20:14:00", "22:00:00"),
                           ("20:15:00", "22:00:00.001"),
                           ("21:59:00", "23:00:00")):
            times = np.array([stamp("2022-07-18T" + start),
                              stamp("2022-07-18T" + end)])
            self.assertTrue(gap_unknown(times, 0, asset="US500"))

    def test_minute_bar_width_and_exact_fifteen_minute_boundary(self):
        at = stamp("2022-07-18T12:00:00")
        self.assertEqual(gap_unknown(np.array([at, at + 15 * 60000]),
                                     0, asset="GBPUSD"), [])
        self.assertEqual(gap_unknown(np.array([at, at + 17 * 60000]),
                                     60000, asset="GBPUSD"),
                         [(at + 60000, at + 17 * 60000)])
        self.assertEqual(gap_unknown(np.array([at, at + HOUR]),
                                     HOUR, asset="GBPUSD"), [])

    def test_explicit_asset_required(self):
        with self.assertRaises(TypeError):
            gap_unknown(np.array([], dtype="int64"), 0)
        with self.assertRaisesRegex(ValueError, "asset_required"):
            gap_unknown(np.array([], dtype="int64"), 0, asset="UNREGISTERED")


def raw_hour(at):
    return dict(timestamp=at, multiplier=.00001, bid=1.2, ask=1.2001,
                times=[1, 0, 1000], bids=[0, 2, -1], asks=[0, 2, -1],
                bidVolumes=[1, 2, 3], askVolumes=[1, 2, 3])


def opportunity(at):
    return dict(id=CELL, asset="GBPUSD", side="BUY", day="2022-01-04",
                decision_msc=at, deadline_msc=at + 2 * HOUR + HOUR // 2,
                deadline_kind="DAY", stop_units=119000, pass15=False)


class SourceAdmissionTests(unittest.TestCase):
    def test_census_includes_cost_rejects_and_deadline_hour(self):
        at = stamp("2022-01-04T08:00:00")
        signals, hours = census([opportunity(at)])
        self.assertEqual(len(signals), 1)
        self.assertEqual(hours, [at, at + HOUR, at + 2 * HOUR])
        self.assertNotIn("pass15", signals[0])

    def test_census_refuses_changed_asset_duplicate_and_validation_window(self):
        at = stamp("2022-01-04T08:00:00")
        for row in (dict(opportunity(at), asset="EURUSD"), opportunity(END),
                    dict(opportunity(at), deadline_msc=at)):
            with self.assertRaises(ValueError):
                census([row])
        with self.assertRaisesRegex(ValueError, "duplicate"):
            census([opportunity(at), opportunity(at)])

    def test_raw_decode_retains_same_millisecond_order_and_exact_FX_grid(self):
        at = stamp("2022-01-04T08:00:00")
        values = decoded_array(raw_hour(at), at)
        self.assertEqual(values["t"].tolist(), [at + 1, at + 1, at + 1001])
        self.assertEqual(values["b"].tolist(), [120000, 120002, 120001])
        self.assertEqual(values["a"].tolist(), [120010, 120012, 120011])

    def test_out_of_hour_prices_are_rejected_not_filtered(self):
        at = stamp("2022-01-04T08:00:00")
        raw = raw_hour(at)
        raw["times"] = [1, 0, HOUR]
        with self.assertRaisesRegex(ValueError, "not_dropped"):
            decoded_array(raw, at)
        with self.assertRaisesRegex(ValueError, "outside_Development"):
            decoded_array(raw_hour(END), END)

    def test_sidewise_H1_comparison_keeps_source_difference_explicit(self):
        at = stamp("2022-01-04T08:00:00")
        ticks = decoded_array(raw_hour(at), at)
        source = {(at, "bid"): [120000, 120002, 120000, 120001],
                  (at, "ask"): [120010, 120012, 120010, 120011]}
        self.assertEqual(compare_h1(ticks, at, source), [])
        source[(at, "ask")][-1] = 120099
        difference = compare_h1(ticks, at, source)
        self.assertEqual(len(difference), 1)
        self.assertEqual(difference[0]["side"], "ask")
        self.assertEqual(difference[0]["h1_units"][-1], 120099)
        self.assertEqual(difference[0]["tick_units"][-1], 120011)

    def test_parent_output_is_never_a_valid_new_job(self):
        with tempfile.TemporaryDirectory() as folder:
            parent = Path(folder) / "parent"
            with self.assertRaisesRegex(ValueError, "read_only"):
                output_root(parent / "new-job", parent)

    def test_admission_resume_retains_same_binary_and_marks_incomplete_source(self):
        at = stamp("2022-01-04T08:00:00")
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "new-job"
            source = job / "source/cache"
            source.mkdir(parents=True)
            raw = source / "hour.json"
            raw.write_text(json.dumps(raw_hour(at)))
            books = {}
            for side, prices in (("bid", [1.2, 1.20002, 1.2, 1.20001]),
                                  ("ask", [1.2001, 1.20012, 1.2001, 1.20011])):
                book = job / f"2022-gbpusd-{side}.json"
                book.write_text(json.dumps([dict(timestamp=at, **dict(zip(
                    ("open", "high", "low", "close"), prices)))]))
                books[f"2022-gbpusd-{side}"] = {"book": str(book)}
            registration = dict(job_root=str(job.absolute()), input_pins=[], producer_pins=[],
                hours=[at], missing_hours=[at], reused={}, h1_source_books=books,
                prior_stage0_pass=False, signals=[])
            (job / "registration.json").write_text(json.dumps(registration))
            self.assertFalse(admit(job))
            self.assertEqual(json.loads((job / "source-proof.json").read_text())["status"],
                             "SOURCE_INCOMPLETE")
            seals = [dict(at=at, raw_path=str(raw), raw_sha256=digest(raw), records=3)]
            (job / "source/sealed-hours.json").write_text(json.dumps(seals))
            self.assertTrue(admit(job))
            binary = job / f"ticks/{at}.ticks"
            before = binary.read_bytes()
            self.assertTrue(admit(job))
            self.assertEqual(binary.read_bytes(), before)
            raw.write_text('{}')
            with self.assertRaisesRegex(ValueError, "raw_source_changed"):
                admit(job)

    def test_held_quote_gap_remains_unknown_even_with_valid_hourly_extrema(self):
        at = stamp("2022-01-04T08:00:00")
        ticks = decoded_array(raw_hour(at), at)
        ticks["t"] = [at + 1, at + 31 * 60000, at + 32 * 60000]
        with tempfile.TemporaryDirectory() as folder:
            binary = Path(folder) / "ticks.bin"
            binary.write_bytes(ticks.tobytes())
            manifest = {str(at): dict(path=str(binary), sha256=digest(binary), records=3)}
            rows = [dict(day="2022-01-04", decision_msc=at,
                         deadline_msc=at + 32 * 60000)]
            issues = held_path_quality(rows, manifest)
            self.assertEqual(issues[0]["reason"], "HELD_GAP_GT15_MINUTES")
            self.assertEqual(issues[0]["gaps"], [(at + 1, at + 31 * 60000)])


if __name__ == "__main__":
    unittest.main()
