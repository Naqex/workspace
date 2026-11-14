from contextlib import ExitStack
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solo_gbp_economics as econ
import prop_portfolio_confirm as confirm
import prop_portfolio_select as select
from prop_portfolio_scan import native_bars
from prop_campaign_source import DTYPE, stamp, HOUR, Prices
from prop_portfolio_accounts import ASSETS, FIELDS, JOINT, quantity_steps, trade_money
from prop_portfolio_ticks import realize_ticks
from solo_gbp_source import CELL, START, END, digest, atomic_json


AT = stamp("2022-01-04T08:00:00")


def signal(at=AT, side="BUY", asset="GBPUSD"):
    return dict(id=CELL if asset == "GBPUSD" else econ.EUR_CELL, asset=asset,
        side=side, day="2022-01-04", decision_msc=at, stop_units=119860 if side == "BUY" else 120150,
        horizon="DAY", deadline_msc=at + 120000, deadline_kind="DAY")


def frozen_deadline(row, entry):
    return row["deadline_msc"], row["deadline_kind"]


def manifest(folder, values):
    array = np.array(values, dtype=DTYPE)
    path = Path(folder) / "fixture.ticks"
    array.tofile(path)
    return {str(AT // HOUR * HOUR): dict(path=str(path), records=len(array), sha256=digest(path))}


class SourceFenceTests(unittest.TestCase):
    def fixture(self, job):
        row = signal()
        row.pop("horizon")
        source = dict(schema="solo-gbp-source-v1", cell=CELL, job_root=str(job.absolute()),
            window={"first": START, "end_exclusive": END}, prices2024_2026_read=False,
            prior_stage0_pass=False, prior_stage0_annual={}, signals=[row], hours=[AT],
            input_pins=[], producer_pins=[])
        atomic_json(job / "registration.json", source)
        atomic_json(job / "manifest.json", {str(AT): {"fixture": True}})
        for name in ("held-path-quality.json", "h1-reconciliation.json"):
            atomic_json(job / name, {})
        proof = dict(status="SOURCE_RECONCILED", registration_sha256=digest(job / "registration.json"),
            manifest_sha256=digest(job / "manifest.json"), expected_hours=1, admitted_hours=1,
            h1_difference_count=0, empty_hours=[], held_path_issue_count=0,
            source_only=True, new_financial_outcomes_computed=False,
            same_ms_order_preserved=True, prices2024_2026_read=False)
        atomic_json(job / "source-proof.json", proof)
        return source, proof

    def patches(self):
        stack = ExitStack()
        stack.enter_context(patch.object(econ, "EXPECTED_RAW", 1))
        stack.enter_context(patch.object(econ, "EXPECTED_HOURS", 1))
        stack.enter_context(patch.object(econ, "deadline", frozen_deadline))
        return stack

    def test_incomplete_proof_denies_before_price_or_curve_reader(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(econ, "Prices") as price, \
                patch.object(econ.np, "load") as load:
            job = Path(folder)
            atomic_json(job / "source-proof.json", {"status": "SOURCE_INCOMPLETE"})
            with self.assertRaisesRegex(ValueError, "requires_SOURCE_RECONCILED"):
                econ.run(job)
            price.assert_not_called()
            load.assert_not_called()

    def test_source_bindings_quality_scope_and_deadline_are_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder, self.patches():
            job = Path(folder)
            for field, value in (("manifest_sha256", "wrong"), ("held_path_issue_count", 1),
                                 ("same_ms_order_preserved", False), ("prices2024_2026_read", True)):
                _, proof = self.fixture(job)
                proof[field] = value
                atomic_json(job / "source-proof.json", proof)
                with self.subTest(field=field), self.assertRaises(ValueError):
                    econ.validated_source(job)
            self.fixture(job)
            with patch.object(econ, "deadline", return_value=(AT + 1, "changed")), \
                    self.assertRaisesRegex(ValueError, "frozen_deadline_changed"):
                econ.validated_source(job)

    def test_source_producer_drift_denies_before_price_reads(self):
        with tempfile.TemporaryDirectory() as folder, self.patches(), \
                patch.object(econ, "Prices") as price, patch.object(econ.np, "load") as load:
            job = Path(folder)
            source, proof = self.fixture(job)
            code = job / "producer.py"
            code.write_text("frozen")
            source["producer_pins"] = [econ.source_pin(code)]
            atomic_json(job / "registration.json", source)
            proof["registration_sha256"] = digest(job / "registration.json")
            atomic_json(job / "source-proof.json", proof)
            code.write_text("changed")
            with self.assertRaisesRegex(ValueError, "source_or_producer_changed"):
                econ.run(job)
            price.assert_not_called()
            load.assert_not_called()

    def test_registration_pins_committed_code_and_inputs_before_any_arrays(self):
        with tempfile.TemporaryDirectory() as folder, self.patches(), \
                patch.object(econ, "Prices") as price, patch.object(econ.np, "load") as load:
            job = Path(folder) / "job"
            job.mkdir()
            self.fixture(job)
            code = Path(folder) / "producer.py"
            code.write_bytes(b"test\r\n")
            baseline = Path(folder) / "baseline"
            baseline.mkdir()
            for path in econ.baseline_paths(baseline).values():
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b"synthetic file, hashed but never loaded")
            with patch.object(econ, "WORKSPACE", Path(folder)), \
                    patch.object(econ, "producer_paths", return_value=[code]), \
                    patch.object(econ, "legacy_producers", return_value=[]), \
                    patch.object(econ.subprocess, "check_output", side_effect=lambda args, **kw:
                                 "abc" if args[1] == "rev-parse" else b"test\n"):
                registered = econ.register(job, baseline)
                self.assertEqual(registered["producer_commit"], "abc")
                self.assertEqual(econ.register(job, baseline), registered)
                for pin_type in ("producer", "input"):
                    path = code if pin_type == "producer" else next(iter(econ.baseline_paths(baseline).values()))
                    old = path.read_bytes()
                    path.write_bytes(b"changed")
                    with self.subTest(kind=pin_type), self.assertRaisesRegex(ValueError, "changed"):
                        econ.run(job)
                    path.write_bytes(old)
            price.assert_not_called()
            load.assert_not_called()

    def test_nested_output_link_is_rejected_before_creation(self):
        with tempfile.TemporaryDirectory() as folder, self.patches():
            job = Path(folder) / "job"
            job.mkdir()
            outside = Path(folder) / "outside"
            outside.mkdir()
            self.fixture(job)
            try:
                (job / "economics-v1").symlink_to(outside, target_is_directory=True)
            except OSError:
                self.skipTest("OS does not permit test symlink creation")
            with self.assertRaisesRegex(ValueError, "links_forbidden"):
                econ.register(job)
            self.assertEqual(list(outside.iterdir()), [])


class ExecutionAndMoneyTests(unittest.TestCase):
    def realize(self, rows, prices, **kwargs):
        with tempfile.TemporaryDirectory() as folder, \
                patch("prop_portfolio_ticks.deadline", frozen_deadline):
            return realize_ticks(rows, manifest(folder, prices), **kwargs)

    def test_EUR_default_keeps_existing_asset_recipe_and_signal_id(self):
        trades, skipped = self.realize([signal(asset="EURUSD")],
            [(AT, 120000, 120010), (AT + 120000, 120210, 120220)])
        self.assertEqual(skipped, [])
        self.assertEqual(trades[0]["asset"], "EURUSD")
        self.assertEqual(trades[0]["recipe"], "SAT1")
        self.assertEqual(trades[0]["signal_id"], f"SAT1:{AT}:BUY")

    def test_GBP_BUY_uses_ask_entry_bid_stop_and_actual_gap_quote(self):
        trades, _ = self.realize([signal()], [(AT, 120000, 120010),
            (AT + 60000, 119850, 119865), (AT + 120000, 120300, 120310)],
            asset="GBPUSD", recipe=CELL)
        row = trades[0]
        self.assertEqual((row["entry_price_units"], row["exit_price_units"]), (120010, 119850))
        self.assertEqual(row["reason"], "SL")
        self.assertEqual(row["id"], CELL)
        self.assertEqual(row["signal_id"], f"{CELL}:{AT}:BUY")

    def test_GBP_SELL_uses_bid_entry_ask_stop_and_same_ms_first_cross(self):
        trades, _ = self.realize([signal(side="SELL")], [(AT, 120000, 120010),
            (AT + 60000, 120100, 120149), (AT + 60000, 120140, 120160),
            (AT + 120000, 119800, 119810)], asset="GBPUSD", recipe=CELL)
        self.assertEqual(trades[0]["exit_price_units"], 120160)
        self.assertEqual(trades[0]["exit_quote_index"], 2)
        self.assertEqual(trades[0]["reason"], "SL")

    def test_asset_mismatch_is_rejected_instead_of_relabelled(self):
        with patch("prop_portfolio_ticks.Prices") as reader:
            with self.assertRaisesRegex(ValueError, "asset_mismatch"):
                realize_ticks([signal()], {})
            with self.assertRaisesRegex(ValueError, "unregistered"):
                realize_ticks([], {}, asset="GBPUSD", recipe="new")
            reader.assert_not_called()

    def test_GBP_does_not_inherit_EUR_validation_release(self):
        with patch("prop_portfolio_ticks.Prices") as reader, \
                patch("prop_portfolio_ticks.price_scope") as scope:
            with self.assertRaisesRegex(ValueError, "Development_only"):
                realize_ticks([signal()], {}, cutoff=END + 366 * 24 * HOUR,
                              asset="GBPUSD", recipe=CELL)
            scope.assert_not_called()
            reader.assert_not_called()

    def test_one_lot_round_trip_hand_arithmetic_and_lot_floor(self):
        for side, entry, stop, exit_price in (("BUY", 120010, 119860, 120210),
                                            ("SELL", 120000, 120150, 119800)):
            row = dict(asset="GBPUSD", side=side, entry_price_units=entry,
                       stop_units=stop, exit_price_units=exit_price, entry_msc=AT, exit_msc=AT + HOUR)
            q = quantity_steps(row, 150)
            self.assertEqual(q, 100)
            money = trade_money(row, q, "SYM_FLAT", 150)
            self.assertEqual(money["gross_usd"], 200)
            self.assertEqual(money["commission_usd"], 5)
            self.assertEqual(money["slippage_usd"], 4)
            self.assertEqual(money["swap_usd"], 0)
            self.assertEqual(money["net_usd"], 191)
            self.assertAlmostEqual(money["net_R"], 191 / 150)
            self.assertEqual(quantity_steps(row, 75.9), 50)

    def test_DAY_funding_is_verified_not_forced_to_zero(self):
        econ.assert_day_flat(AT, AT + HOUR)
        with self.assertRaisesRegex(ValueError, "rollover"):
            econ.assert_day_flat(AT, stamp("2022-01-04T22:00:00"))
        with self.assertRaisesRegex(ValueError, "rollover"):
            econ.assert_day_flat(AT, stamp("2022-01-05T01:00:00"))

    def test_standalone_GBP_does_not_extend_joint_account(self):
        self.assertEqual(ASSETS, ("XAUUSD", "EURUSD"))
        self.assertNotIn("GBPUSD", FIELDS)
        self.assertEqual(JOINT.names, ("t", "b0", "a0", "b1", "a1"))


class CohortAndCurveTests(unittest.TestCase):
    def test_entry_delta_persists_through_empty_minutes_until_next_observed_bar(self):
        with tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
            for module in (confirm, econ):
                stack.enter_context(patch.object(module, "START", AT))
                stack.enter_context(patch.object(module, "POINTS", 4))
            source = manifest(folder, [(AT, 120500, 120510), (AT, 120000, 120010),
                                       (AT + 120000, 120100, 120110)])
            trade = dict(asset="EURUSD", side="BUY", entry_msc=AT, entry_quote_index=1,
                entry_price_units=120010, exit_msc=AT + 120000, exit_quote_index=2,
                exit_price_units=120100, stop_units=119860, day="2022-01-04", signal_id="empty-minute")
            legacy, _ = confirm.curves([trade], Prices(source), "SYM_FLAT", 150)
            rebuilt, _ = confirm.curves([trade], econ.OrdinalBoundedPrices(Prices(source), [trade]),
                                         "SYM_FLAT", 150)
            corrected, receipt = econ.corrected_baseline(legacy, [trade], Prices(source),
                                                          "EURUSD", "SYM_FLAT", 150)
            for one, two in zip(corrected, rebuilt):
                np.testing.assert_allclose(one, two, rtol=0, atol=1e-10)
            self.assertEqual(receipt["changed_trades"][0]["changes"][0]["through_exclusive_msc"], AT + 120000)

    def test_baseline_boundary_delta_equals_full_clipped_rebuild_with_overlap_and_funding(self):
        base = stamp("2022-01-04T21:59:00")
        for asset, p0 in (("EURUSD", 120000), ("XAUUSD", 2000000)):
            with self.subTest(asset=asset), tempfile.TemporaryDirectory() as folder, ExitStack() as stack:
                for module in (confirm, select, econ):
                    stack.enter_context(patch.object(module, "START", base))
                    stack.enter_context(patch.object(module, "POINTS", 5))
                prices = [(base, p0 - 20, p0 - 10), (base, p0, p0 + 10),
                    (base + 15000, p0 + 20, p0 + 30),
                    (base + 30000, p0 - 100, p0 - 90), (base + 30000, p0 + 30, p0 + 40),
                    (base + 30000, p0 + 50, p0 + 60), (base + 30000, p0 + 1000, p0 + 1010),
                    (base + 60000, p0 + 20, p0 + 30),
                    (base + 120000, p0 - 200, p0 - 190), (base + 120000, p0 - 9000, p0 - 8990),
                    (base + 130000, p0 + 200, p0 + 210), (base + 130000, p0 + 9000, p0 + 9010)]
                arr = np.array(prices, dtype=DTYPE)
                source = {}
                for at in sorted(set(arr["t"] // HOUR * HOUR)):
                    part = arr[arr["t"] // HOUR * HOUR == at]
                    path = Path(folder) / f"{at}.ticks"
                    part.tofile(path)
                    source[str(at)] = dict(path=str(path), records=len(part), sha256=digest(path))
                trades = []
                for n, side, entry, entry_ix, exit_at, exit_ix in (
                        (0, "BUY", base, 1, base + 120000, 1),
                        (1, "SELL", base + 15000, 2, base + 130000, 3),
                        (2, "BUY", base + 30000, 4, base + 30000, 5)):
                    reader = Prices(source)
                    ent = reader.hour(entry // HOUR * HOUR)[entry_ix]
                    ext = reader.hour(exit_at // HOUR * HOUR)[exit_ix]
                    px = int(ent["a" if side == "BUY" else "b"])
                    trades.append(dict(asset=asset, side=side, entry_msc=entry,
                        entry_quote_index=entry_ix, exit_msc=exit_at, exit_quote_index=exit_ix,
                        entry_price_units=px, exit_price_units=int(ext["b" if side == "BUY" else "a"]),
                        stop_units=px + (-150 if side == "BUY" else 150), day="2022-01-04",
                        signal_id=f"fixture{n}", reason="DAY"))
                if asset == "XAUUSD":
                    stack.enter_context(patch.object(select, "read", return_value=trades))
                    stack.enter_context(patch.object(select, "Prices", side_effect=lambda _: Prices(source)))
                    stack.enter_context(patch.object(select, "JOB", Path(folder)))
                    legacy = select.core_curves("ASYM_FLAT")
                    def clipped_bars(reader, start, end):
                        t = next(t for t in trades if (t["entry_msc"], t["exit_msc"]) == (start, end))
                        clipped = econ.OrdinalBoundedPrices(reader, [t])
                        clipped.active = t
                        return native_bars(clipped, start, end)
                    with patch.object(select, "native_bars", side_effect=clipped_bars):
                        rebuilt = select.core_curves("ASYM_FLAT")
                    risk = 150
                else:
                    legacy, _ = confirm.curves(trades, Prices(source), "SYM_FLAT", 75)
                    rebuilt, _ = confirm.curves(trades, econ.OrdinalBoundedPrices(Prices(source), trades),
                                                 "SYM_FLAT", 75)
                    risk = 75
                corrected, receipt = econ.corrected_baseline(legacy, trades, Prices(source), asset,
                                                             "ASYM_FLAT" if asset == "XAUUSD" else "SYM_FLAT", risk)
                self.assertTrue(receipt["changed_trades"])
                self.assertEqual(receipt["terminal_cash_delta_R"], 0)
                for old, result, expected in zip(legacy, corrected, rebuilt):
                    np.testing.assert_allclose(result, expected, rtol=0, atol=1e-9)
                    self.assertEqual(old[-1], result[-1])
                wrong = [dict(t) for t in trades]
                wrong[0]["exit_price_units"] += 1
                with self.assertRaisesRegex(ValueError, "frozen_fill_quote_mismatch"):
                    econ.corrected_baseline(legacy, wrong, Prices(source), asset, "SYM_FLAT", risk)
                wrong_cash = [r.copy() for r in legacy]
                wrong_cash[0][-1] += .1
                with self.assertRaisesRegex(ValueError, "frozen_cash_bridge"):
                    econ.corrected_baseline(wrong_cash, trades, Prices(source), asset,
                                             "ASYM_FLAT" if asset == "XAUUSD" else "SYM_FLAT", risk)

    def test_raw_cost_reject_is_still_measured_with_correct_spread(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(econ, "deadline", frozen_deadline):
            source = manifest(folder, [(AT, 120000, 120010), (AT + 120000, 120210, 120220)])
            rows = econ.raw_measurements([dict(signal(), stop_units=119999)], Prices(source))
            self.assertFalse(rows[0]["passes"])
            self.assertAlmostEqual(rows[0]["raw_net_usd_per_lot"], 191)
            self.assertAlmostEqual(rows[0]["friction_price"], .00019)

    def test_unknown_endpoint_or_held_gap_never_silently_reduces_raw_cohort(self):
        for values, end, error in (
                ([(AT, 120000, 120010)], AT + 120000, "ENDPOINT_UNKNOWN"),
                ([(AT, 120000, 120010), (AT + 1200000, 120100, 120110)], AT + 1200000, "HELD_PATH_UNKNOWN")):
            with tempfile.TemporaryDirectory() as folder, patch.object(econ, "deadline", frozen_deadline):
                row = dict(signal(), deadline_msc=end, stop_units=119999)
                with self.assertRaisesRegex(ValueError, error):
                    econ.raw_measurements([row], Prices(manifest(folder, values)))

    def test_half_budget_curves_remain_normalized_to_150_and_bridge_cash(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("prop_portfolio_ticks.deadline", frozen_deadline), \
                patch.object(confirm, "START", AT), patch.object(confirm, "POINTS", 4):
            source = manifest(folder, [(AT, 120000, 120010),
                                      (AT + 60000, 120100, 120110), (AT + 120000, 120210, 120220)])
            trades, _ = realize_ticks([signal()], source, asset="GBPUSD", recipe=CELL)
            full, gaps = confirm.curves(trades, Prices(source), "SYM_FLAT", 150)
            small, _ = confirm.curves(trades, Prices(source), "SYM_FLAT", 75)
            self.assertEqual(gaps, [])
            self.assertAlmostEqual(full[0][-1], 191 / 150)
            self.assertAlmostEqual(small[0][-1], 95.5 / 150)

    def test_post_exit_same_ms_quote_cannot_change_curve_or_cash(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch("prop_portfolio_ticks.deadline", frozen_deadline), \
                patch.object(confirm, "START", AT), patch.object(confirm, "POINTS", 4):
            prices = [(AT, 120000, 120010), (AT + 60000, 119850, 119865),
                      (AT + 120000, 120210, 120220)]
            baseline = manifest(folder, prices)
            trades, _ = realize_ticks([signal()], baseline, asset="GBPUSD", recipe=CELL)
            initial, _ = confirm.curves(trades, econ.OrdinalBoundedPrices(Prices(baseline), trades),
                                        "SYM_FLAT", 150)
            changed = manifest(folder, prices[:2] + [(AT + 60000, 110000, 110010)] + prices[2:])
            trades2, _ = realize_ticks([signal()], changed, asset="GBPUSD", recipe=CELL)
            later, _ = confirm.curves(trades2, econ.OrdinalBoundedPrices(Prices(changed), trades2),
                                      "SYM_FLAT", 150)
            self.assertEqual(trades, trades2)
            for one, two in zip(initial, later):
                np.testing.assert_array_equal(one, two)

    def test_marginal_baseline_contains_EUR75_and_Gold150(self):
        def fake_metrics(curves):
            return {"terminal": float(curves[0][-1]), "daily": {"2022-01-04": float(curves[0][-1])}}
        vector = lambda n: [np.array([0., float(n)]) for _ in range(3)]
        with patch.object(econ, "metrics", side_effect=fake_metrics):
            out = econ.marginal_comparison(vector(8), vector(4), vector(10), vector(-3))
        self.assertEqual(out["baseline_A150_EUR75"]["terminal"], 7)
        self.assertEqual(out["plus_GBP75"]["terminal"], 11)

    def test_correlation_gate_uses_actual_75_dollar_curve_after_lot_floor(self):
        def fake_metrics(curves):
            return {"daily": {f"2022-01-{i+4:02}": float(v) for i, v in enumerate(curves[0])}}
        vector = lambda ns: [np.asarray(ns, dtype=float) for _ in range(3)]
        full = [3, -2, 1, -4]
        small = [1, -1, 1 / 3, -2]
        core = small
        with patch.object(econ, "metrics", side_effect=fake_metrics):
            out = econ.marginal_comparison(vector(full), vector(small), vector(core), vector([0] * 4))
        self.assertAlmostEqual(out["GBP_to_A_EUR"]["pooled"], 1)
        self.assertNotEqual(out["GBP_reference150_to_A_EUR"]["pooled"], 1)

    def test_strict_both_year_gate_and_undefined_zero_drawdown(self):
        annual = {str(y): dict(retention=.8, median_friction_over_median_natural_sl=.1,
                              economics={"net_R": 5}) for y in (2022, 2023)}
        comparison = {m: {"GBP_to_A_EUR": {"pooled": -.4},
                         "baseline_A150_EUR75": {"total_net_R": 10, "max_R_DD": 5},
                         "plus_GBP75": {"total_net_R": 20, "max_R_DD": 7}} for m in econ.MODELS}
        self.assertEqual(econ.gate_reasons(annual, comparison), [])
        annual["2022"]["economics"]["net_R"] = -.1
        annual["2023"]["economics"]["net_R"] = 20
        self.assertIn("2022:NEGATIVE_NET_R", econ.gate_reasons(annual, comparison))
        annual["2022"]["economics"]["net_R"] = 1
        comparison["SYM_FLAT"]["plus_GBP75"]["max_R_DD"] = 0
        self.assertTrue(any("UNDEFINED" in r for r in econ.gate_reasons(annual, comparison)))
        comparison["ASYM_FLAT"]["GBP_to_A_EUR"]["pooled"] = None
        self.assertIn("ASYM_FLAT:A_EUR_CORRELATION", econ.gate_reasons(annual, comparison))

    def test_annual_side_exit_and_top_trade_dependency(self):
        raw = [dict(day="2022-01-04", natural_sl_price=.002, friction_price=.00019,
                    passes=True, raw_net_usd_per_lot=-4)]
        rows = [dict(day="2022-01-04", side="BUY", reason="DAY", signal_id="fixture",
                     net_R=5, net_usd=750, gross_usd=759, commission_usd=5, slippage_usd=4, swap_usd=0)]
        annual = econ.annual_measurements(raw, rows)
        self.assertEqual(annual["2022"]["retention"], 1)
        self.assertEqual(annual["2022"]["economics"]["net_R_without_top3"], 0)
        self.assertEqual(annual["2022"]["raw_DAY_mean_net_usd_per_lot"], -4)
        self.assertIsNone(annual["2023"]["retention"])

    def test_overlap_reports_union_not_double_counted_minutes(self):
        trade = lambda a, b: {"entry_msc": AT + a * 60000, "exit_msc": AT + b * 60000}
        with patch.object(econ, "START", AT), patch.object(econ, "POINTS", 6):
            out = econ.overlap_summary([trade(0, 3)], [trade(1, 2)], [trade(2, 3)])
        self.assertEqual(out["GBP_held_minutes"], 4)
        self.assertEqual(out["GBP_minutes_also_A_or_EUR"], 3)
        self.assertEqual(out["all_assets_max_concurrent"], 3)


if __name__ == "__main__":
    unittest.main()
