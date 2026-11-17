from copy import deepcopy
from fractions import Fraction
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solo_gbp_economics as econ
from prop_portfolio_scan import raw_geometry


class ExactGateTests(unittest.TestCase):
    def test_real_boundary_regression_and_adjacent_price_units(self):
        row = dict(asset="GBPUSD", side="BUY", stop_units=128064)
        entry = [1687165200101, 128175, 128184, 0]
        _, distance, friction, passes = raw_geometry(row, entry)
        self.assertGreater(friction / distance, .15)  # retained display-only float
        self.assertTrue(passes)
        self.assertFalse(raw_geometry(dict(row, stop_units=128065), entry)[3])
        self.assertTrue(raw_geometry(dict(row, stop_units=128063), entry)[3])

    def test_all_assets_match_independent_fraction_near_cost_boundary(self):
        count = 0
        for asset, price, spread in (("GBPUSD", 128184, 9), ("EURUSD", 110000, 12),
                                     ("AUDUSD", 70000, 6), ("US500", 4500000, 500),
                                     ("XAUUSD", 2000000, 500)):
            for side in ("BUY", "SELL"):
                buy = side == "BUY"
                bid, ask = (price - spread, price) if buy else (price, price + spread)
                # Units are derived independently from the declared per-side cost.
                cost = Fraction(spread)
                cost += (Fraction(price, 1000000) * 14 + 400 if asset == "XAUUSD"
                         else 2500 if asset == "US500" else 9)
                boundary = cost / Fraction(15, 100)
                for width in range(int(boundary) - 2, int(boundary) + 4):
                    row = dict(asset=asset, side=side,
                               stop_units=price - width if buy else price + width)
                    expected = width > spread and cost / width <= Fraction(15, 100)
                    self.assertEqual(raw_geometry(row, [0, bid, ask, 0])[3], expected,
                                     (asset, side, width, cost))
                    count += 1
        self.assertEqual(count, 60)

    def test_invalid_stop_side_is_not_rescued_by_exact_gate(self):
        for side, stop in (("BUY", 128175), ("BUY", 128184), ("SELL", 128184), ("SELL", 128175)):
            self.assertFalse(raw_geometry(dict(asset="GBPUSD", side=side, stop_units=stop),
                                          [0, 128175, 128184, 0])[3])


OLD = """def raw_geometry(row, entry):
    price = entry[2]
    valid = True
    return price, 1.0, 0.15, valid and 0.15 <= 0.15

def unrelated():
    return 1
"""
NEW = """def raw_geometry(row, entry):
    price = entry[2]
    valid = True
    cost_units = 15
    stop_units = 100
    return price, 1.0, 0.15, valid and 100 * cost_units <= 15 * stop_units

def unrelated():
    return 1
"""


class HistoricalSourceTests(unittest.TestCase):
    def fixture(self, folder):
        root = Path(folder)
        gate = root / "tooling/ai-engines/prop_portfolio_scan.py"
        gate.parent.mkdir(parents=True)
        gate.write_text(OLD, encoding="utf-8")
        external = root / "source.json"
        external.write_text("immutable external input")
        decoder = root / "decoder.js"
        decoder.write_text("unchanged decoder")
        registration = dict(producer_commit="prior",
            input_pins=[econ.source_pin(external)],
            producer_pins=[econ.source_pin(gate), econ.source_pin(decoder)])
        gate.write_text(NEW, encoding="utf-8")
        return root, gate, external, decoder, registration

    def test_only_gate_drift_accepts_pinned_historical_blob(self):
        with tempfile.TemporaryDirectory() as folder:
            root, _, _, _, registration = self.fixture(folder)
            with patch.object(econ, "WORKSPACE", root), \
                    patch.object(econ.subprocess, "check_output", return_value=OLD.encode()):
                econ.verify_source_pins_for_gate_correction(registration)
            with self.assertRaisesRegex(ValueError, "source_or_producer_changed"):
                econ.verify_pins(registration)  # legacy verifier stays strict

    def test_unrelated_code_display_geometry_and_historical_hash_are_not_bypassed(self):
        mutations = (("unrelated", NEW.replace("return 1\n", "return 2\n"), OLD),
                     ("geometry", NEW.replace("price = entry[2]", "price = entry[1]"), OLD),
                     ("signature", NEW.replace("row, entry", "row, entry, unsafe=True"), OLD),
                     ("decorator", "@changed\n" + NEW, OLD),
                     ("history", NEW, OLD.replace("return 1\n", "return 9\n")))
        for label, current, history in mutations:
            with self.subTest(label=label), tempfile.TemporaryDirectory() as folder:
                root, gate, _, _, registration = self.fixture(folder)
                gate.write_text(current, encoding="utf-8")
                with patch.object(econ, "WORKSPACE", root), \
                        patch.object(econ.subprocess, "check_output", return_value=history.encode()), \
                        self.assertRaises(ValueError):
                    econ.verify_source_pins_for_gate_correction(registration)

    def test_external_input_and_decoder_drift_still_fail(self):
        for kind in ("input", "decoder"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                root, _, external, decoder, registration = self.fixture(folder)
                (external if kind == "input" else decoder).write_text("changed")
                with patch.object(econ, "WORKSPACE", root), \
                        patch.object(econ.subprocess, "check_output", return_value=OLD.encode()), \
                        self.assertRaisesRegex(ValueError, "input_changed|producer_change"):
                    econ.verify_source_pins_for_gate_correction(registration)


class CorrectionAttemptTests(unittest.TestCase):
    def fixture(self, folder):
        job = Path(folder)
        prior = job / "economics-v1/run"
        prior.mkdir(parents=True)
        raw = [dict(decision_msc=1000000 + i * 3600000, side="BUY", stop_units=100,
                    passes=i < 287) for i in range(300)]
        raw[217].update(decision_msc=econ.GATE_SIGNAL[0], side=econ.GATE_SIGNAL[1], passes=False)
        trades = [dict(row, net_usd=i, risk_usd=150) for i, row in enumerate(raw) if row["passes"]]
        (prior / "raw.json").write_text(json.dumps(raw))
        (prior / "trades.json").write_text(json.dumps(trades))
        corrected_raw = deepcopy(raw)
        corrected_raw[217]["passes"] = True
        corrected_trades = deepcopy(trades) + [dict(corrected_raw[217], net_usd=-7, risk_usd=150)]
        return job, corrected_raw, corrected_trades

    def test_exact_membership_delta_keeps_prior_trades_even_if_added_trade_loses(self):
        with tempfile.TemporaryDirectory() as folder:
            job, raw, trades = self.fixture(folder)
            result = econ.corrected_cohort_delta(job, raw, trades)
            self.assertEqual(result["corrected_fills"], 287)
            self.assertEqual(result["added_signal"], list(econ.GATE_SIGNAL))
            self.assertTrue(result["all_prior_trade_fields_and_money_unchanged"])

    def test_unregistered_membership_raw_fact_or_prior_money_change_is_rejected(self):
        for kind in ("extra", "raw", "trade"):
            with self.subTest(kind=kind), tempfile.TemporaryDirectory() as folder:
                job, raw, trades = self.fixture(folder)
                if kind == "extra":
                    raw[299]["passes"] = True
                elif kind == "raw":
                    raw[0]["stop_units"] += 1
                else:
                    trades[0]["net_usd"] += 1
                with self.assertRaises(ValueError):
                    econ.corrected_cohort_delta(job, raw, trades)

    def test_version_output_is_explicit_and_old_directory_is_not_reused(self):
        with tempfile.TemporaryDirectory() as folder:
            self.assertEqual(econ.economics_folder(folder, 1).name, "economics-v1")
            self.assertEqual(econ.economics_folder(folder, 2).name, "economics-v2")
            for invalid in (True, 0, 3, "2"):
                with self.assertRaisesRegex(ValueError, "unregistered_economics_version"):
                    econ.economics_folder(folder, invalid)

    def test_wrong_parent_identity_stops_before_any_price_reader(self):
        with tempfile.TemporaryDirectory() as folder, patch.object(econ, "Prices") as prices:
            job = Path(folder) / "S01-gbp-confirmation-source-v2"
            for name in ("economics-v1/registration.json", "economics-v1/run/result.json",
                         "independent-review-v2/gate-diagnosis.json",
                         "independent-review-v2/review_s01_v2.py",
                         "independent-review-v2/failure-20261117T015544Z.json",
                         "independent-review-v2/audit-registration.json"):
                path = job / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text("{}")
            with self.assertRaisesRegex(ValueError, "parent_identity"):
                econ.cost_correction_parent(job)
            prices.assert_not_called()

    def test_corrected_attempt_cannot_select_different_baselines(self):
        with tempfile.TemporaryDirectory() as folder, \
                patch.object(econ, "validated_source", return_value=({}, [], {})), \
                patch.object(econ, "cost_correction_parent",
                             return_value={"baseline_root": str(Path(folder) / "frozen")}), \
                patch.object(econ, "Prices") as prices:
            with self.assertRaisesRegex(ValueError, "baseline_reselection"):
                econ.register(Path(folder) / "job", Path(folder) / "other", version=2)
            prices.assert_not_called()


if __name__ == "__main__":
    unittest.main()
