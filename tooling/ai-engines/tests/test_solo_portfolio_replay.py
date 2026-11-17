from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solo_portfolio_replay as run
from prop_campaign_source import DTYPE


def fx_trade():
    at = run.stamp("2023-06-19T09:00:00")
    return dict(
        asset="GBPUSD", role="SATELLITE", regime_weight=1,
        signal_id="GBP:one", recipe="GBPUSD.SWEEP.ASIA.LONDON.DAY",
        side="BUY", decision_msc=at, entry_msc=at + 100,
        entry_quote_index=0, entry_price_units=128184, stop_units=128064,
        exit_msc=at + 200, exit_quote_index=1, exit_price_units=128063,
        deadline_msc=at + 10 * run.HOUR, deadline_kind="DAY", reason="SL",
    )


class MemoryPrices:
    def __init__(self, rows):
        self.rows = np.array(rows, dtype=DTYPE)

    def hour(self, at):
        return self.rows

    def endpoint(self, at):
        i = int(self.rows["t"].searchsorted(at))
        if i == len(self.rows) or self.rows["t"][i] - at > 60000:
            return None
        quote = self.rows[i]
        return [int(quote["t"]), int(quote["b"]), int(quote["a"]), i]

    def path(self, first, end):
        lo = int(self.rows["t"].searchsorted(first))
        hi = int(self.rows["t"].searchsorted(end, side="right"))
        return self.rows[lo:hi], np.arange(lo, hi)


class MetadataScopeTests(unittest.TestCase):
    def manifest(self, trade):
        item = {"path": "not-opened.ticks", "sha256": "a" * 64, "records": 2}
        return {asset: {str(trade["entry_msc"] // run.HOUR * run.HOUR): item}
                for asset in run.ASSETS}

    def test_manifest_rejects_2024_before_reader_can_filter_it(self):
        with patch.object(run.Prices, "__init__") as reader:
            with self.assertRaisesRegex(ValueError, "manifest_outside_Development"):
                run.DevelopmentPrices({str(run.END): dict(path="closed", records=1, sha256="a" * 64)})
            reader.assert_not_called()

    def test_metadata_rejects_cutoff_duplicate_missing_hour_and_wrong_recipe(self):
        trade = fx_trade()
        manifests = self.manifest(trade)
        run.validate_trade_metadata([trade], manifests)
        for case in ("cutoff", "duplicate", "missing", "recipe", "future_bias"):
            with self.subTest(case=case):
                rows, sources = [dict(trade)], deepcopy(manifests)
                if case == "cutoff":
                    rows[0]["deadline_msc"] = run.END
                elif case == "duplicate":
                    rows.append(dict(trade))
                elif case == "missing":
                    sources["GBPUSD"] = {}
                elif case == "recipe":
                    rows[0]["recipe"] = "NEW_TUNED_RECIPE"
                else:
                    rows[0]["known_h4_at"] = trade["decision_msc"] + 1
                with self.assertRaises(ValueError):
                    run.validate_trade_metadata(rows, sources)

    def test_no_annual_forced_close_or_forex_rollover(self):
        trade = fx_trade()
        trade.update(entry_msc=run.stamp("2022-12-31T20:00:00"),
                     decision_msc=run.stamp("2022-12-31T20:00:00"),
                     exit_msc=run.stamp("2023-01-01T08:00:00"),
                     deadline_msc=run.stamp("2023-01-01T20:00:00"))
        with self.assertRaisesRegex(ValueError, "annual_cutoff_not_flat"):
            run.validate_trade_metadata([trade], self.manifest(trade))
        trade.update(entry_msc=run.stamp("2023-06-19T20:00:00"),
                     decision_msc=run.stamp("2023-06-19T20:00:00"),
                     exit_msc=run.stamp("2023-06-19T23:00:00"),
                     deadline_msc=run.stamp("2023-06-19T23:00:00"))
        with self.assertRaisesRegex(ValueError, "FX_not_flat_before_rollover"):
            run.validate_trade_metadata([trade], self.manifest(trade))

    def test_normalization_discards_saved_quantity_and_pnl(self):
        trade = fx_trade()
        trade.update(net_usd=10000, quantity_steps=999, risk_usd=150, regime_weight=.5)
        event = run.normalized_event(trade, "GBPUSD")
        self.assertNotIn("quantity_steps", event)
        self.assertNotIn("net_usd", event)
        self.assertNotIn("risk_usd", event)
        self.assertEqual(event["regime_weight"], 1)


class NativePathTests(unittest.TestCase):
    def test_first_stop_and_duplicate_millisecond_ordinal(self):
        trade = fx_trade()
        t = trade["entry_msc"]
        reader = MemoryPrices([(t, 128175, 128184), (t + 100, 128063, 128072),
                               (t + 100, 120000, 120009)])
        self.assertEqual(run.check_trade_path(trade, reader), 2)
        later = dict(trade, exit_quote_index=2, exit_price_units=120000)
        with self.assertRaisesRegex(ValueError, "not_first_natural_SL"):
            run.check_trade_path(later, reader)

    def test_sell_stop_uses_ask_and_gap_fill(self):
        trade = fx_trade()
        t = trade["entry_msc"]
        trade.update(side="SELL", entry_price_units=128175, stop_units=128295,
                     exit_price_units=128300)
        self.assertEqual(run.check_trade_path(
            trade, MemoryPrices([(t, 128175, 128184), (t + 100, 128291, 128300)])), 2)
        with self.assertRaisesRegex(ValueError, "exit_executable_side"):
            run.check_trade_path(dict(trade, exit_price_units=128291),
                                 MemoryPrices([(t, 128175, 128184), (t + 100, 128291, 128300)]))

    def test_deadline_quote_has_time_priority_over_stop(self):
        trade = fx_trade()
        t = trade["entry_msc"]
        trade.update(deadline_msc=t + 100, reason="DAY")
        reader = MemoryPrices([(t, 128175, 128184), (t + 100, 128063, 128072)])
        self.assertEqual(run.check_trade_path(trade, reader), 2)
        with self.assertRaisesRegex(ValueError, "not_first_natural_SL"):
            run.check_trade_path(dict(trade, reason="SL"), reader)

    def test_entry_must_be_first_quote_not_a_favorable_same_ms_successor(self):
        trade = fx_trade()
        t = trade["entry_msc"]
        reader = MemoryPrices([(t, 128175, 128184), (t, 128170, 128179),
                               (t + 100, 128063, 128072)])
        trade.update(entry_quote_index=1, entry_price_units=128179, exit_quote_index=2)
        with self.assertRaisesRegex(ValueError, "entry_not_first_native_quote"):
            run.check_trade_path(trade, reader)

    def test_time_close_cannot_hide_a_prior_stop(self):
        trade = fx_trade()
        t = trade["entry_msc"]
        trade.update(reason="DAY", deadline_msc=t + 200, exit_msc=t + 200,
                     exit_quote_index=2, exit_price_units=128200)
        reader = MemoryPrices([(t, 128175, 128184), (t + 100, 128063, 128072),
                               (t + 200, 128200, 128209)])
        with self.assertRaisesRegex(ValueError, "time_close_or_prior_SL"):
            run.check_trade_path(trade, reader)


class BindingAndOutputTests(unittest.TestCase):
    def test_canonical_identity_is_checked_before_a_quote_reader(self):
        with patch.object(run, "pin", return_value={"path": "wrong", "sha256": "0" * 64}), \
                patch.object(run, "DevelopmentPrices") as reader:
            with self.assertRaisesRegex(ValueError, "canonical_S01_identity"):
                run.inherited_inputs()
            reader.assert_not_called()

    def test_historical_hash_uses_committed_blob_and_rejects_tamper(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            path = root / "module.py"
            path.write_text("modified live source", encoding="utf-8")
            old = b"original source\n"
            pin = {"path": str(path), "sha256": hashlib.sha256(old).hexdigest()}
            with patch.object(run, "WORKSPACE", root), \
                    patch.object(run.subprocess, "check_output", return_value=old):
                run.historical_producers([pin], run.S01_COMMIT)
                with self.assertRaisesRegex(ValueError, "historical_producer_hash"):
                    run.historical_producers([dict(pin, sha256="0" * 64)], run.S01_COMMIT)
                with self.assertRaisesRegex(ValueError, "unregistered_prior_producer"):
                    run.historical_producers([pin], "arbitrary")

    def test_output_is_owned_and_never_overwrites(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "S02"
            job.mkdir()
            with patch.object(run, "JOB", job):
                with self.assertRaisesRegex(ValueError, "output_outside_owned_job"):
                    run.write_new(Path(folder) / "other.json", {})
                run.write_new(job / "receipt.json", {"preserved": True})
                with self.assertRaises(FileExistsError):
                    run.write_new(job / "receipt.json", {"preserved": False})
                self.assertEqual(run.read(job / "receipt.json"), {"preserved": True})

    def test_missing_registration_does_not_create_attempt(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "S02"
            job.mkdir()
            with patch.object(run, "JOB", job):
                with self.assertRaises(FileNotFoundError):
                    run.execute("run")
            self.assertEqual(list(job.iterdir()), [])

    def test_registration_failure_is_preserved_without_price_read(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "S02"
            job.mkdir()
            (job / "registration.json").write_text("{}")
            with patch.object(run, "JOB", job), \
                    patch.object(run, "verify_registration", side_effect=ValueError("tampered")), \
                    patch.object(run, "DevelopmentPrices") as reader:
                with self.assertRaisesRegex(ValueError, "tampered"):
                    run.execute("run")
                reader.assert_not_called()
            self.assertEqual(run.read(job / "attempt-1/failure.json")["status"], "FAILED")
            self.assertFalse((job / "attempt-1/result.json").exists())

    def test_config_tamper_is_rejected_before_lineage_and_prices(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "S02"
            job.mkdir()
            record = {"schema": "solo-three-asset-replay-registration-v1",
                      "job_root": str(job), "config": {**run.CONFIG, "capital_usd": 100000},
                      "prices2024_2026_read": False, "python_version": sys.version,
                      "numpy_version": np.__version__}
            (job / "registration.json").write_text(json.dumps(record))
            with patch.object(run, "JOB", job), patch.object(run, "inherited_inputs") as lineage:
                with self.assertRaisesRegex(ValueError, "registration_scope"):
                    run.verify_registration()
                lineage.assert_not_called()


class AccountBudgetTests(unittest.TestCase):
    def native_identity(self, spec):
        return dict(
            cell=spec["model"], start_msc=spec["start"], end_msc=spec["end"],
            rolling=spec["rolling"], assets=list(run.ASSETS),
            included_assets=spec["included_assets"], fixed_asset_risk=dict(run.RISKS),
            common_risk_usd=150, policy="fixed_asset_risk_joint_ticks",
            d1_scaled=False, include_satellite=True,
            accounting_model="legacy_accrued_funding_until_exit_one_leg_float_slip",
            reward_model="legacy_30day_80pct_flat_proxy_resets_anchor",
            target_specs_news_margin_and_forward_verified=False,
        )

    def test_exact_account_census_and_fixed_risk_api(self):
        specs = run.account_specs()
        self.assertEqual(len(specs), 108)
        self.assertEqual(sum(s["rolling"] for s in specs), 96)
        self.assertEqual(sum(s["scope"].startswith("ANNUAL_") for s in specs), 8)
        with patch.object(run, "PortfolioAccount") as account:
            run.make_accounts(specs)
        self.assertEqual(account.call_count, 108)
        for call in account.call_args_list:
            self.assertEqual(call.kwargs["fixed_asset_risk"], run.RISKS)
            self.assertEqual(call.kwargs["common_risk_usd"], 150)
            self.assertTrue(call.kwargs["track_quote_age"])
            self.assertLessEqual(call.args[1], run.END)

    def test_reordered_or_changed_specs_are_rejected_before_construction(self):
        for change in ("order", "included", "model", "mode", "start"):
            with self.subTest(change=change), patch.object(run, "PortfolioAccount") as account:
                specs = run.account_specs()
                if change == "order":
                    specs[0], specs[27] = specs[27], specs[0]
                elif change == "included":
                    specs[0]["included_assets"] = list(run.ASSETS)
                elif change == "model":
                    specs[0]["model"] = "ASYM_FLAT"
                elif change == "mode":
                    specs[0]["rolling"] = True
                else:
                    specs[0]["start"] += run.DAY
                with self.assertRaisesRegex(ValueError, "noncanonical_account_specs"):
                    run.make_accounts(specs)
                account.assert_not_called()

    def test_native_rows_cannot_be_mislabeled_as_another_system_or_policy(self):
        specs = run.account_specs()
        for field, value in (
                ("included_assets", list(run.ASSETS)), ("cell", "ASYM_FLAT"),
                ("rolling", True), ("policy", "V3_balanced_joint_ticks"),
                ("fixed_asset_risk", {"XAUUSD": 200, "EURUSD": 100, "GBPUSD": 100}),
                ("common_risk_usd", 75), ("assets", ["XAUUSD", "EURUSD"]),
                ("d1_scaled", True), ("start_msc", run.START + run.DAY)):
            with self.subTest(field=field):
                rows = [self.native_identity(spec) for spec in specs]
                rows[0][field] = value
                with self.assertRaisesRegex(ValueError, "native_account_identity"):
                    run.bind_account_rows(rows, specs)
        rows = [self.native_identity(spec) for spec in specs]
        bound = run.bind_account_rows(rows, specs)
        self.assertEqual([row["account_id"] for row in bound],
                         [spec["account_id"] for spec in specs])
        self.assertNotIn("account_id", rows[0])

    def test_common_R_not_sum_of_trade_R_and_payouts_not_pass_probability(self):
        row = dict(account_id="x", system="BASELINE_A_EUR", model="SYM_FLAT",
                   scope="CONTINUOUS_DEV", entries=2, closed_trades=2, net_usd=225,
                   portfolio_common_R=1.5, equity_DD_common_R=2,
                   peak_dd_pct=.6, static_loss_pct=.2, worst_daily_loss_pct=.1,
                   mean_net_R=1, closed=[{"net_usd": 150}, {"net_usd": 75}],
                   max_concurrency=2, maximum_open_stop_risk_pct=.45,
                   first_breach=None, rejections={}, quote_age_coverage={"path_complete": True})
        summary = run.compact_account(row)
        self.assertEqual(summary["portfolio_common_R"], 1.5)
        self.assertEqual(summary["equity_DD_usd"], 300)
        self.assertEqual(summary["Net_over_equity_DD"], .75)
        with self.assertRaisesRegex(ValueError, "common_R_accounting"):
            run.compact_account(dict(row, portfolio_common_R=2))

    def test_lifecycle_censoring_is_not_counted_as_breach(self):
        base = dict(start_msc=run.START, phase_passes=[], accepted=[], closed=[],
                    first_breach=None, payouts=[], trader_payout_usd=0)
        failed = dict(base, first_breach={"at": run.START + run.DAY})
        passed = dict(base, phase_passes=[{"at": run.START + 10 * run.DAY},
                                        {"at": run.START + 20 * run.DAY}])
        summary = run.lifecycle_summary([base, failed, passed])
        self.assertEqual(summary["phase1_passes"], 1)
        self.assertEqual(summary["both_phases_passed"], 1)
        self.assertEqual(summary["both_right_censored"], 1)
        self.assertEqual(summary["both_failed_before_completion"], 1)
        self.assertEqual(summary["both_median_days_among_completions"], 20)
        self.assertFalse(summary["probability_interpretation"])

    def test_summary_never_promotes_unknown_paths_or_negative_annual(self):
        rows = []
        for spec in run.account_specs():
            candidate = spec["system"].startswith("CANDIDATE")
            net = 200 if candidate else 100
            row = dict(self.native_identity(spec), **spec,
                       entries=1, closed_trades=1,
                       net_usd=net, portfolio_common_R=net / 150,
                       equity_DD_common_R=1, peak_dd_pct=.3,
                       static_loss_pct=.1, worst_daily_loss_pct=.1,
                       mean_net_R=net / 150, closed=[{"net_usd": net}],
                       accepted=[], max_concurrency=1, maximum_open_stop_risk_pct=.3,
                       first_breach=None, rejections={}, cash_bridge_verified=True,
                       phase_passes=[], payouts=[], trader_payout_usd=0,
                       quote_age_coverage={"path_complete": True})
            rows.append(row)
        good = run.summarize(rows)
        self.assertEqual(good["status"], "NUMERICAL_GATES_PASSED_AWAITING_INDEPENDENT_REVIEW")
        self.assertFalse(good["prop_qualified"])
        changed = deepcopy(rows)
        changed[0]["quote_age_coverage"]["path_complete"] = False
        self.assertEqual(run.summarize(changed)["status"], "INCONCLUSIVE_PATH")
        annual = next(r for r in changed if r["scope"] == "ANNUAL_2022"
                      and r["system"].startswith("CANDIDATE"))
        annual.update(net_usd=-1, portfolio_common_R=-1 / 150)
        result = run.summarize(changed)
        self.assertTrue(any(reason.startswith("NEGATIVE_ANNUAL:") for reason in result["reasons"]))
        self.assertFalse(result["historical_validation_released"])
        for invalid in ("duplicate", "reorder", "relabel"):
            with self.subTest(invalid=invalid):
                malformed = deepcopy(rows)
                if invalid == "duplicate":
                    malformed[-1] = malformed[0]
                elif invalid == "reorder":
                    malformed[0], malformed[27] = malformed[27], malformed[0]
                else:
                    malformed[0]["system"] = "CANDIDATE_A_EUR_GBP"
                with self.assertRaisesRegex(ValueError, "account_census|selector_binding"):
                    run.summarize(malformed)


if __name__ == "__main__":
    unittest.main()
