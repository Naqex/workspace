import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from quant_core.market_data_store import MarketDataStore, QuoteStore, QUOTE, Checksums, HOUR
from quant_core.ftmo_execution_and_calendar import GoldCosts, gold_calendar
from quant_core.prop_lifecycle_and_parity import bindings, simulate, AuditAccount
from prop_campaign_source import stamp
from prop_portfolio_accounts import trade_money


class CoreTests(unittest.TestCase):
    def test_column_integrity_and_seek_without_duplicating_cache(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            files = {}
            for name in ("times", "o", "h", "l", "c"):
                values = [60, 120, 180] if name == "times" else [1001, 1002, 1003]
                a = np.array(values, dtype="<i8" if name == "times" else "<i4")
                p = root / (name + ".bin")
                a.tofile(p)
                files[p.name] = hashlib.sha256(p.read_bytes()).hexdigest()
            (root / "manifest.json").write_text(json.dumps(dict(files=files, rows=3, raw_sha256="declared")))
            checks = Checksums()
            store = MarketDataStore(root, checks)
            rows = store.bars(120000, 180000)
            self.assertEqual(rows["bo"].tolist(), [1002])
            before = checks.bytes_hashed
            MarketDataStore(root, checks)
            self.assertEqual(checks.bytes_hashed, before)
            self.assertFalse(store.columns["times"].flags.writeable)
            # Release Windows mappings before the tamper write.
            for a in store.columns.values():
                a._mmap.close()
            changed = root / "o.bin"
            previous = changed.stat()
            changed.write_bytes(b"x" * 12)
            # The cache key tracks file generations by size/mtime. Fast Windows
            # writes can share a timestamp; declare the new fixture generation.
            os.utime(changed, ns=(previous.st_atime_ns, previous.st_mtime_ns + 1_000_000_000))
            self.assertNotEqual(changed.stat().st_mtime_ns, previous.st_mtime_ns)
            with self.assertRaisesRegex(ValueError, "checksum"):
                MarketDataStore(root, checks)

    def test_shared_quote_offset_scope_and_no_forward_fill(self):
        with tempfile.TemporaryDirectory() as folder:
            p = Path(folder) / "quotes.bin"
            np.array([(0, 100, 110), (HOUR, 101, 111)], dtype=QUOTE).tofile(p)
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest = {str(h): dict(path=str(p), records=1, byte_offset=i * QUOTE.itemsize, sha256=sha)
                        for i, h in enumerate((0, HOUR))}
            store = QuoteStore(manifest, 0, 2 * HOUR)
            self.assertEqual(store.endpoint(HOUR), [HOUR, 101, 111, 0])
            self.assertIsNone(store.endpoint(60001))
            self.assertEqual(store.path(0, HOUR)[0]["b"].tolist(), [100, 101])
            with self.assertRaisesRegex(ValueError, "scope"):
                store.hour(2 * HOUR)
            store.hour.cache_clear()

    def test_money_matches_frozen_arithmetic_on_sides_and_swaps(self):
        for side in ("BUY", "SELL"):
            for model in ("SYM_FLAT", "ASYM_ORDER"):
                t = dict(asset="XAUUSD", side=side, reason="TIME_24H",
                         entry_msc=stamp("2023-03-01T12:00:00"),
                         exit_msc=stamp("2023-03-02T12:00:00"),
                         entry_price_units=1800123, exit_price_units=1803456)
                expected = trade_money(t, 13, model, 150)
                actual = GoldCosts(model).money(t, 13)
                for field, value in actual.items():
                    self.assertAlmostEqual(value, expected[field], places=9)

    def test_tp_uses_limit_slippage_only_in_order_model(self):
        t = dict(side="BUY", reason="TP_2R", entry_msc=stamp("2023-03-01T12:00:00"),
                 exit_msc=stamp("2023-03-01T13:00:00"),
                 entry_price_units=1800000, exit_price_units=1810000)
        self.assertEqual(GoldCosts("ASYM_ORDER").money(t, 10)["slippage_usd"], 2)
        self.assertEqual(GoldCosts("SYM_FLAT").money(t, 10)["slippage_usd"], 4)

    def test_calendar_keeps_holiday_clamp_and_dec31_correction(self):
        cal = gold_calendar(stamp("2018-01-01"), stamp("2026-10-14"))
        self.assertTrue(cal.allowed(stamp("2021-12-31T12:00:00")))
        at, why = cal.deadline(stamp("2023-11-24T08:00:00"))
        self.assertLess(at, stamp("2023-11-24T20:30:00"))
        self.assertEqual(why, "HOLIDAY_FLAT")

    def test_binding_restores_on_error(self):
        import types
        module = types.SimpleNamespace(value=1)
        with self.assertRaises(RuntimeError):
            with bindings(module, value=2):
                raise RuntimeError()
        self.assertEqual(module.value, 1)

    def test_lifecycle_adapter_replays_shared_quotes_and_cash(self):
        with tempfile.TemporaryDirectory() as folder:
            first = stamp("2022-01-04")
            entry, exit_at = first + 8 * HOUR, first + 9 * HOUR
            p = Path(folder) / "quotes.bin"
            np.array([(entry, 1999900, 2000000), (exit_at, 2001000, 2001100)], dtype=QUOTE).tofile(p)
            sha = hashlib.sha256(p.read_bytes()).hexdigest()
            manifest = {str(at): dict(path=str(p), records=1, byte_offset=i * QUOTE.itemsize, sha256=sha)
                        for i, at in enumerate((entry, exit_at))}
            end = first + 10 * HOUR
            reader = QuoteStore(manifest, first, end)
            t = dict(asset="XAUUSD", role="CORE", side="BUY", decision_msc=entry-1,
                     entry_msc=entry, entry_price_units=2000000, stop_units=1990000,
                     deadline_msc=exit_at, exit_msc=exit_at, exit_price_units=2001000,
                     entry_quote_index=0, exit_quote_index=0, d1_gate=True,
                     regime_weight=1, reason="TIME_CLOSE")
            a = AuditAccount(first, end, "SYM_FLAT", rolling=False, fixed_risk=150)
            rows = simulate([t], dict(XAUUSD=reader, EURUSD=QuoteStore({}, first, end)),
                            [a], first, end, gold_calendar(first, end))
            self.assertEqual(rows[0]["closed_trades"], 1)
            self.assertAlmostEqual(rows[0]["net_usd"], GoldCosts("SYM_FLAT").money(t, 15)["net_usd"])
            self.assertTrue(rows[0]["cash_bridge_verified"])
            reader.hour.cache_clear()
