from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

import ftmo_spread_sessions as sessions
from ftmo_trial_runner import QuoteParquet, write


class SpreadSessionTests(unittest.TestCase):
    def test_regional_dst_and_weekend_rules(self):
        # The US spring transition precedes the UK transition.
        day = datetime(2026, 3, 12, tzinfo=timezone.utc)
        for tag, hour, minute in (("asia", 0, 0), ("london", 8, 0), ("ny", 13, 30), ("rollover", 20, 55)):
            start = day.replace(hour=hour, minute=minute)
            with self.subTest(tag=tag):
                value = sessions.window(tag, start, 180)
                self.assertEqual(value["from_utc_msc"], int(start.timestamp() * 1000))
        with self.assertRaisesRegex(ValueError, "OUTSIDE_LONDON"):
            sessions.window("london", day.replace(hour=11, minute=59), 180)
        with self.assertRaisesRegex(ValueError, "OUTSIDE_ASIA"):
            sessions.window("asia", day.replace(day=14), 180)
        with self.assertRaisesRegex(ValueError, "OUTSIDE_ROLLOVER"):
            sessions.window("rollover", day.replace(day=13, hour=21), 180)

    def capture(self, directory, start, spread_values, tag="london", account="hash"):
        directory.mkdir()
        ms = int(start.timestamp() * 1000)
        with_file = QuoteParquet(directory / "quotes.parquet")
        for i, spread in enumerate(spread_values):
            with_file.accept(dict(kind="quote", asset="XAUUSD", time_msc=ms + i, known_at_msc=ms + i,
                                  bid=2000.0, ask=2000.0 + spread))
        write(directory / "quote_capture.json", with_file.close())
        write(directory / "report.json", dict(mode="READ_ONLY", source="NATIVE_MT5", actual_broker_orders=0,
              session_window=sessions.window(tag, start, 180), binding=dict(account_hash=account),
              quote_window=dict(started_utc_msc=ms, ended_utc_msc=ms + 180000)))
        return directory

    def test_merge_recomputes_quantiles_and_checks_binding_and_duplicates(self):
        with TemporaryDirectory() as base:
            root = Path(base)
            day = datetime(2026, 11, 19, 8, tzinfo=timezone.utc)
            first = self.capture(root / "first", day, [.10])
            second = self.capture(root / "second", day.replace(minute=5), [.20, .30, .40])
            ny = self.capture(root / "ny", day.replace(hour=15), [.80], "ny")
            value = sessions.combine([first, second, ny])
            self.assertEqual(value["sessions"]["london"]["XAUUSD"]["n"], 4)
            self.assertAlmostEqual(value["sessions"]["london"]["XAUUSD"]["median"], .25)
            self.assertAlmostEqual(value["sessions"]["ny"]["XAUUSD"]["median"], .80)
            self.assertIn("EURUSD", value["coverage"]["london"])
            with self.assertRaisesRegex(ValueError, "OVERLAPPING"):
                sessions.combine([first, first])
            other = self.capture(root / "different", day.replace(minute=10), [1.0], account="other")
            with self.assertRaisesRegex(ValueError, "ACCOUNT_BINDINGS_DIFFER"):
                sessions.combine([first, other])
            file = second / "quotes.parquet"
            file.write_bytes(file.read_bytes() + b"tampered")
            with self.assertRaisesRegex(ValueError, "HASH_MISMATCH"):
                sessions.combine([second])
