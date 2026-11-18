from copy import deepcopy
from pathlib import Path
import sys
import tempfile
import json
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import solo_validation_replay as run
from prop_campaign_source import DTYPE


def raw_signal(asset="GBPUSD", at=None):
    at = at or run.stamp("2024-06-19T09:00:00")
    return dict(id=f"{asset}.SWEEP.ASIA.LONDON.DAY", asset=asset, side="BUY",
                decision_msc=at, stop_units=128064, horizon="DAY", day="2024-06-19")


class MemoryPrices:
    def __init__(self, rows):
        self.rows = np.array(rows, dtype=DTYPE)

    def endpoint(self, at):
        i = int(self.rows["t"].searchsorted(at))
        if i == len(self.rows) or self.rows["t"][i] - at > 60000:
            return None
        row = self.rows[i]
        return [int(row["t"]), int(row["b"]), int(row["a"]), i]

    def hour(self, at):
        return self.rows

    def path(self, first, end):
        lo = int(self.rows["t"].searchsorted(first))
        hi = int(self.rows["t"].searchsorted(end, side="right"))
        return self.rows[lo:hi], np.arange(lo, hi)


class FenceAndBindingTests(unittest.TestCase):
    def test_release_checked_before_even_manifest_validation(self):
        with patch.object(run, "source_module", return_value=SimpleNamespace(
                verify_release=lambda: (_ for _ in ()).throw(ValueError("unreleased")))), \
                patch.object(run.Prices, "__init__") as opened:
            with self.assertRaisesRegex(ValueError, "unreleased"):
                run.ValidationPrices({}, "GBPUSD")
            opened.assert_not_called()

    def test_2025_manifest_rejected_before_reader_can_filter(self):
        with patch.object(run, "source_module", return_value=SimpleNamespace(verify_release=lambda: {})), \
                patch.object(run.Prices, "__init__") as opened:
            with self.assertRaisesRegex(ValueError, "outside_window"):
                run.ValidationPrices({str(run.FINAL): dict(path="holdout", records=2, sha256="a" * 64)}, "GBPUSD")
            opened.assert_not_called()

    def test_manifest_requires_canonical_hour_and_shape(self):
        for key, value in [(str(run.END + 1), dict(path="x", records=1, sha256="a" * 64)),
                           (str(run.END), dict(path="x", records=-1, sha256="a" * 64))]:
            with self.assertRaises(ValueError):
                run.metadata_manifest({key: value})

    def test_closed_year_source_pin_is_rejected_before_hash(self):
        pins = [{"path": str(run.PARENT / "eurusd-b0-20261113/prepared-v1" / p / "bars.json"),
                 "sha256": "a" * 64} for p in ("20211101", "20220101", "20230101", "20250101")]
        with patch.object(run, "verify_pin") as verify:
            with self.assertRaisesRegex(ValueError, "H1_source_path_census"):
                run.validate_eur_h1_pins(pins)
            verify.assert_not_called()

    def test_wrong_binary_year_path_denied_before_native_open(self):
        manifest = {str(run.END): dict(path=str(run.JOB / "gbp-source/ticks" / f"{run.FINAL}.ticks"),
                                      records=2, sha256="a" * 64)}
        with patch.object(run, "source_module", return_value=SimpleNamespace(verify_release=lambda: {})), \
                patch.object(run.Prices, "__init__") as reader:
            with self.assertRaisesRegex(ValueError, "binary_hour_filename"):
                run.ValidationPrices(manifest, "GBPUSD")
            reader.assert_not_called()

    def test_output_owned_nonoverwrite(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            with patch.object(run, "JOB", root / "job"):
                (root / "job").mkdir()
                with self.assertRaisesRegex(ValueError, "outside_owned"):
                    run.write_new(root / "outside.json", {})
                run.write_new(root / "job" / "a.json", {})
                with self.assertRaises(FileExistsError):
                    run.write_new(root / "job" / "a.json", {})

    def test_canonical_parent_rejects_before_reading_artifact(self):
        with patch.object(run, "digest", return_value="wrong"), patch.object(run, "read") as read:
            with self.assertRaisesRegex(ValueError, "canonical_S02"):
                run.canonical_s02()
            read.assert_not_called()

    def test_extension_manifest_cannot_mutate_development(self):
        item = dict(path="x", records=1, sha256="a" * 64)
        old = {str(run.START): item}
        extension = {str(run.END): item}
        self.assertEqual(run.merge_extension_manifest(old, extension), {**old, **extension})
        with self.assertRaisesRegex(ValueError, "outside_window"):
            run.merge_extension_manifest(old, {str(run.START): item})

    def test_prepared_proof_cannot_omit_artifact_or_input_pin(self):
        base = dict(status="PREPARED_PATHS_NOT_FINANCIAL_OUTCOMES", prices2025_2026_read=False,
                    source_release_sha256="seal", input_pins=[{"path": "bound", "sha256": "x"}],
                    artifact_sha256={n: "x" for n in ("trades.json", "manifests.json", "fx-funnels.json")})
        for kind in ("artifact", "input"):
            proof = deepcopy(base)
            if kind == "artifact": proof["artifact_sha256"].pop("trades.json")
            else: proof["input_pins"] = []
            with patch.object(run, "source_module", return_value=SimpleNamespace(verify_release=lambda: {})), \
                    patch.object(run, "read", return_value=proof), \
                    patch.object(run, "digest", return_value="seal"), \
                    patch.object(run, "expected_prepared_pins", return_value=base["input_pins"]):
                with self.assertRaisesRegex(ValueError, "pin_census"):
                    run.prepared_inputs()

    def test_inherited_release_requires_exact_canonical_paths(self):
        with patch.object(run, "inherited_validation_paths", return_value={"a": Path("approved")}), \
                patch.object(run, "verify_pin") as verify:
            with self.assertRaisesRegex(ValueError, "pin_census"):
                run.inherited_release_pins({"inherited_validation": {}})
            with self.assertRaisesRegex(ValueError, "path_changed"):
                run.inherited_release_pins({"inherited_validation": {
                    "a": {"path": "elsewhere", "sha256": "x"}}})
            verify.assert_not_called()

    def test_source_review_cannot_be_promoted_by_hash_alone(self):
        with patch.object(run, "read", return_value={"mismatches": [{"hour": 1}], "hours": []}):
            with self.assertRaisesRegex(ValueError, "source_review_failed"):
                run.inherited_source_semantics({"gold_source_review": "proof"}, {}, [])

    def test_gbp_pass_label_cannot_erase_detailed_source_failure(self):
        registration = dict(hours=[run.END], signals=[{}])
        manifest = {str(run.END): dict(path="x", records=1, sha256="a" * 64)}
        proof = dict(status="SOURCE_RECONCILED", registration_sha256="pin", manifest_sha256="pin",
                     expected_hours=1, admitted_hours=1, h1_difference_count=0, empty_hours=[],
                     held_path_issue_count=0, same_ms_order_preserved=True, source_only=True,
                     prices2025_2026_read=False)
        content = {"source-proof.json": proof, "manifest.json": manifest,
                   "h1-reconciliation.json": dict(mismatches=[{"at": run.END}], empty_hours=[],
                       original_sources_modified=False, prices2025_2026_read=False),
                   "held-path-quality.json": dict(issues=[], raw_signals=1,
                       maximum_unregistered_gap_ms=900000, scheduled_closures_exempted=False)}
        source = SimpleNamespace(SOURCE_JOB=Path("fixture"), verify_source_registration=lambda: registration)
        with patch.object(run, "source_module", return_value=source), \
                patch.object(run, "digest", return_value="pin"), \
                patch.object(run, "read", side_effect=lambda path: content[Path(path).name]):
            with self.assertRaisesRegex(ValueError, "source_details_failed"):
                run.admitted_gbp_source()


class RawAndOrdinalTests(unittest.TestCase):
    def reader(self, row, stop=True):
        t = row["decision_msc"]
        end = t + 60_000
        ticks = [(t + 100, 128175, 128184), (t + 200, 128063 if stop else 128200, 128072 if stop else 128209),
                 (t + 200, 120000 if stop else 128201, 120009 if stop else 128210),
                 (end, 128210, 128219)]
        return MemoryPrices(ticks), end

    def test_exact_15percent_gate_and_first_same_ms_stop(self):
        row = raw_signal()
        reader, end = self.reader(row)
        with patch.object(run, "deadline", return_value=(end, "DAY")):
            trades, funnel = run.realize_fx([row], reader, "GBPUSD")
        self.assertEqual(len(trades), 1)
        self.assertTrue(funnel[0]["passes"])
        self.assertEqual(trades[0]["exit_quote_index"], 1)
        self.assertEqual(trades[0]["exit_price_units"], 128063)

    def test_complete_funnel_keeps_rejects(self):
        row = raw_signal()
        reader, end = self.reader(row)
        reject = dict(row, stop_units=128065)
        with patch.object(run, "deadline", return_value=(end, "DAY")):
            trades, funnel = run.realize_fx([reject], reader, "GBPUSD")
        self.assertEqual(trades, [])
        self.assertEqual(funnel[0]["reason"], "FRICTION_REJECT")

    def test_time_close_uses_first_endpoint_ordinal(self):
        row = raw_signal()
        at = row["decision_msc"]
        reader = MemoryPrices([(at, 128175, 128184), (at + 60000, 128200, 128209),
                               (at + 60000, 129999, 130008)])
        with patch.object(run, "deadline", return_value=(at + 60000, "DAY")):
            trades, _ = run.realize_fx([row], reader, "GBPUSD")
        self.assertEqual(trades[0]["exit_quote_index"], 1)
        self.assertEqual(trades[0]["reason"], "DAY")

    def test_no_missing_endpoint_drop_or_fake_close(self):
        row = raw_signal()
        reader, end = self.reader(row)
        with patch.object(run, "deadline", return_value=(end + run.HOUR, "DAY")):
            with self.assertRaisesRegex(ValueError, "endpoint_unknown"):
                run.realize_fx([row], reader, "GBPUSD")

    def test_cutoff_is_denied_before_endpoint_read(self):
        row = raw_signal()
        reader, _ = self.reader(row)
        with patch.object(run, "deadline", return_value=(run.FINAL - 60000, "DAY")):
            with self.assertRaisesRegex(ValueError, "year_end_deadline"):
                run.realize_fx([row], reader, "GBPUSD")

    def test_future_outcome_fields_do_not_change_projected_event(self):
        row = raw_signal()
        reader, end = self.reader(row)
        changed = dict(row, exit_msc=run.FINAL, exit_price_units=9999999,
                       net_usd=1e9, quantity_steps=999999, reason="FUTURE")
        with patch.object(run, "deadline", return_value=(end, "DAY")):
            baseline = run.realize_fx([row], reader, "GBPUSD")
            other = run.realize_fx([changed], reader, "GBPUSD")
        self.assertEqual(baseline, other)
        self.assertNotIn("quantity_steps", baseline[0][0])

    def test_raw_census_rejects_future_context_and_years(self):
        row = raw_signal()
        at = row["decision_msc"]
        manifest = {str(at): dict(path="x", records=1, sha256="a" * 64)}
        with patch.object(run, "deadline", return_value=(at + 60000, "DAY")):
            run.validate_raw([row], "GBPUSD", manifest)
            for bad in [dict(row, known_h4_at=at + 1), dict(row, decision_msc=run.FINAL),
                        dict(row, id="NEW_RECIPE")]:
                with self.assertRaises(ValueError):
                    run.validate_raw([bad], "GBPUSD", manifest)
            with self.assertRaisesRegex(ValueError, "duplicate_raw"):
                run.validate_raw([row, row], "GBPUSD", manifest)

    def test_inherited_membership_change_is_not_silent(self):
        row = dict.fromkeys(run.s02.EVENT_FIELDS, 1)
        run.same_event_facts([row], [dict(row, net_usd=999)])
        for altered in [[], [dict(row, exit_price_units=2)]]:
            with self.assertRaisesRegex(ValueError, "membership_changed"):
                run.same_event_facts(altered, [row])


class AccountAndPrefixTests(unittest.TestCase):
    def test_exact104_and108_original_sentinels(self):
        specs = run.account_specs()
        self.assertEqual(len(specs), 104)
        self.assertEqual(sum(r["rolling"] for r in specs), 96)
        self.assertTrue(all(r["end"] == run.FINAL for r in specs))
        self.assertEqual(len(run.s02.account_specs()), 108)
        annual2022 = [s for s in run.s02.account_specs() if s["scope"] == "ANNUAL_2022"]
        self.assertTrue(all(s["end"] == run.stamp("2023-01-01") for s in annual2022))
        accounts = run.make_accounts(specs)
        self.assertTrue(all(a.fixed_asset_risk == run.RISKS for a in accounts))

    def test_sentinel_comparison_only_ignores_global_counter(self):
        old = [dict(account_id=str(i), accepted=[{"at": 1}], joint_tick_marks=5) for i in range(108)]
        got = deepcopy(old)
        got[0]["joint_tick_marks"] = 999
        run.compare_sentinels(got, old)
        got[0]["accepted"][0]["at"] = 2
        with self.assertRaisesRegex(ValueError, "prefix_changed"):
            run.compare_sentinels(got, old)

    def internal(self):
        old, new = run.s02.account_specs(), run.account_specs()
        states = [{"anchor": i, "phase_days": [str(i)], "day_halt": False} for i in range(108)]
        lookup = {s["account_id"]: st for s, st in zip(old, states)}
        extended = []
        for s in new:
            scope = "CONTINUOUS_DEV" if s["scope"] == "CONTINUOUS_2022_2024" else s["scope"]
            extended.append({} if scope == "ANNUAL_2024" else deepcopy(lookup[f"{s['model']}:{s['system']}:{scope}"]))
        common = dict(at_msc=run.END, stream={"at": run.END - 1}, coverage={"gaps": []})
        return dict(common, accounts=states), dict(common, accounts=extended + deepcopy(states)), old, new

    def test_internal_state_detects_omitted_anchor_and_truncation(self):
        args = self.internal()
        self.assertEqual(run.compare_internal(*args)["accounts"], 100)
        for mutation in ("anchor", "sentinel", "truncate", "stream"):
            ref, ext, old, new = deepcopy(args)
            if mutation == "anchor": ext["accounts"][0]["anchor"] += 1
            if mutation == "sentinel": ext["accounts"][104]["anchor"] += 1
            if mutation == "truncate": ext["accounts"].pop()
            if mutation == "stream": ext["stream"] = {"at": run.END}
            with self.assertRaises(ValueError): run.compare_internal(ref, ext, old, new)

    def test_horizon_counts_censor_fail_and_completed_groups(self):
        start = run.START
        def row(days, completed=None, breach=None):
            return dict(start_msc=start, end_msc=start + days * run.DAY,
                        phase_passes=[] if completed is None else [dict(phase=2, at=start + completed * run.DAY)],
                        first_breach=None if breach is None else {"at": start + breach * run.DAY})
        result = run.horizon_counts([row(800, 100), row(800, 500), row(800, 750),
                                    row(100), row(800, breach=200), row(800, breach=500)])
        self.assertEqual(result["365"], dict(completions=1, breach_before_completion=1,
            insufficient_followup=1, no_completion_with_full_followup=3))
        self.assertEqual(result["730"], dict(completions=2, breach_before_completion=2,
            insufficient_followup=1, no_completion_with_full_followup=1))
        self.assertEqual(result["completion_bands"], dict(up_to_365_days=1,
            over_365_up_to_730_days=1, over_730_days=1))
        self.assertEqual(run.horizon_counts([row(800)])["fit_365_days"], "NOT_DEMONSTRATED_IN_THIS_MODEL")


class OrchestrationTests(unittest.TestCase):
    def save(self, path, value):
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(value), encoding="utf-8")

    def test_prepare_preserves733_dev_and_reconciles_synthetic_extensions(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            job, oldjob = root / "job", root / "old"
            job.mkdir()
            at = run.stamp("2024-06-19T09:00:00")
            finish, _ = run.deadline(raw_signal(), at)
            def source_manifest(asset):
                manifest = {}
                for hour in range(at, finish // run.HOUR * run.HOUR + run.HOUR, run.HOUR):
                    records = []
                    if hour == at:
                        records = [(at, 2300000, 2300200), (at + 100, 2290000, 2290200)] if asset == "XAUUSD" else [
                            (at, 128175, 128184), (at + 100, 128063, 128072)]
                    if hour == finish // run.HOUR * run.HOUR:
                        records += [(finish, 128200, 128209)]
                    ticks = np.array(records, dtype=DTYPE)
                    path = root / asset / f"{hour}.ticks"
                    path.parent.mkdir(exist_ok=True)
                    ticks.tofile(path)
                    manifest[str(hour)] = dict(path=str(path), records=len(ticks), sha256=run.digest(path))
                return manifest
            fx = source_manifest("EURUSD")
            gold_source = source_manifest("XAUUSD")
            gold_source = {str(at): gold_source[str(at)]}
            oldtime = run.stamp("2023-06-19T09:00:00")
            def event(asset, i, time):
                gold = asset == "XAUUSD"
                return dict(asset=asset, role="CORE" if gold else "SATELLITE", regime_weight=1,
                    signal_id=f"{asset}:{i}", recipe="A" if gold else "SAT1" if asset == "EURUSD" else
                    "GBPUSD.SWEEP.ASIA.LONDON.DAY", side="BUY", decision_msc=time, entry_msc=time,
                    entry_quote_index=0, entry_price_units=2300200 if gold else 128184,
                    stop_units=2290200 if gold else 128064, deadline_msc=time + 2 * run.HOUR,
                    exit_msc=time + 100, exit_quote_index=1, exit_price_units=2290000 if gold else 128063,
                    reason="SL", **({"exit_policy": "A0"} if gold else {"deadline_kind": "DAY"}))
            dev = [event(a, i, oldtime) for a, count in zip(run.ASSETS, (210, 236, 287)) for i in range(count)]
            old_manifest = {str(oldtime): dict(path="unopened-dev.ticks", records=2, sha256="a" * 64)}
            self.save(oldjob / "attempt-1/trades.json", dev)
            self.save(oldjob / "attempt-1/manifests.json", {a: old_manifest for a in run.ASSETS})
            paths = {name: root / (name + ".json") for name in run.inherited_validation_paths()}
            gold_all = [run.s02.normalized_event(t, "XAUUSD") for t in dev if t["asset"] == "XAUUSD"] + [
                run.s02.normalized_event(event("XAUUSD", 211, at), "XAUUSD")]
            for model in run.MODELS: self.save(paths["gold_" + model], gold_all)
            self.save(paths["gold_original_trades"], gold_all)
            self.save(paths["gold_manifest"], gold_source)
            self.save(paths["gold_source_review"], dict(mismatches=[], hours=[dict(
                at=at, binary=gold_source[str(at)], missing_M1_minutes=[])]))
            self.save(paths["gold_corrections"], {})
            eur_raw, gbp_raw = [raw_signal("EURUSD")], [raw_signal("GBPUSD")]
            self.save(paths["eur_raw"], eur_raw)
            self.save(paths["eur_manifest"], fx)
            self.save(paths["eur_source_proof"], dict(manifest_sha256=run.digest(paths["eur_manifest"]),
                cutoff=run.FINAL, prices2025_2026_read=False, preserves_source_order_and_same_ms=True, hours=len(fx)))
            h1pins = []
            for partition in ("20211101", "20220101", "20230101", "20240101"):
                h1 = root / "eurusd-b0-20261113/prepared-v1" / partition / "bars.json"
                self.save(h1, {"synthetic": True})
                h1pins.append(run.pin(h1))
            self.save(paths["eur_signal_proof"], dict(cells=["EURUSD.SWEEP.ASIA.LONDON.DAY"],
                parameter_reselection=False, raw=1, pins=h1pins))
            self.save(paths["eur_funnel"], dict(raw=1, filled=1, skipped=[]))
            with patch.object(run, "source_module", return_value=SimpleNamespace(verify_release=lambda: {})), \
                    patch.object(run, "binary_path_scope"):
                eur, _ = run.realize_fx(eur_raw, run.ValidationPrices(fx, "EURUSD"), "EURUSD")
            self.save(paths["eur_trades"], eur)
            release = dict(inherited_validation={name: run.pin(path) for name, path in paths.items()})
            self.save(job / "source-release.json", release)
            with patch.object(run, "JOB", job), patch.object(run, "S02_JOB", oldjob), \
                    patch.object(run, "source_module", return_value=SimpleNamespace(verify_release=lambda: release)), \
                    patch.object(run, "committed_producers", return_value=[]), \
                    patch.object(run.subprocess, "check_output", return_value="synthetic\n"), \
                    patch.object(run, "canonical_s02", return_value=[]), \
                    patch.object(run, "admitted_gbp_source", return_value=(gbp_raw, fx, [])), \
                    patch.object(run, "inherited_validation_paths", return_value=paths), \
                    patch.object(run, "binary_path_scope"), patch.object(run, "PARENT", root):
                proof = run.prepare()
            prepared = run.read(job / "prepare-1/trades.json")
            self.assertEqual(prepared[:733], dev)
            self.assertEqual(len(prepared), 736)
            self.assertEqual(proof["extension_trade_census"], {"XAUUSD": 1, "EURUSD": 1, "GBPUSD": 1})
            self.assertFalse(proof["new_financial_outcomes_computed"])

    def test_prepared_registration_and_preflight_on_synthetic_native_file(self):
        with tempfile.TemporaryDirectory() as folder:
            job = Path(folder) / "job"
            oldjob = Path(folder) / "old"
            prepared = job / "prepare-1"
            prepared.mkdir(parents=True)
            self.save(job / "source-release.json", {})
            raw = raw_signal()
            at = raw["decision_msc"]
            ticks = np.array([(at, 128175, 128184), (at + 100, 128063, 128072)], dtype=DTYPE)
            binary = job / "gbp-source/ticks" / f"{at}.ticks"
            binary.parent.mkdir(parents=True)
            ticks.tofile(binary)
            record = dict(path=str(binary), records=2, sha256=run.digest(binary))
            manifest = {str(at): record}
            trade = dict(asset="GBPUSD", role="SATELLITE", regime_weight=1,
                signal_id="synthetic", recipe="GBPUSD.SWEEP.ASIA.LONDON.DAY", side="BUY",
                decision_msc=at, entry_msc=at, entry_quote_index=0, entry_price_units=128184,
                stop_units=128064, deadline_msc=at + run.HOUR, deadline_kind="DAY", reason="SL",
                exit_msc=at + 100, exit_quote_index=1, exit_price_units=128063)
            devtime = run.stamp("2023-06-19T09:00:00")
            dev = [dict(trade, signal_id=f"dev-{i}", decision_msc=devtime, entry_msc=devtime,
                        exit_msc=devtime + 100, deadline_msc=devtime + run.HOUR) for i in range(733)]
            old_manifest = {str(devtime): dict(path="unopened.ticks", records=2, sha256="a" * 64)}
            self.save(oldjob / "attempt-1/trades.json", dev)
            self.save(oldjob / "attempt-1/manifests.json", {a: old_manifest for a in run.ASSETS})
            self.save(prepared / "trades.json", dev + [trade])
            self.save(prepared / "manifests.json", {a: {**old_manifest, **manifest} for a in run.ASSETS})
            self.save(prepared / "fx-funnels.json", {})
            pin = run.pin(job / "source-release.json")
            proof = dict(status="PREPARED_PATHS_NOT_FINANCIAL_OUTCOMES", prices2025_2026_read=False,
                         source_release_sha256=pin["sha256"], input_pins=[pin], producer_pins=[],
                         producer_commit="synthetic", artifact_sha256={n: run.digest(prepared / n)
                            for n in ("trades.json", "manifests.json", "fx-funnels.json")})
            self.save(prepared / "proof.json", proof)
            source = SimpleNamespace(verify_release=lambda: {})
            with patch.object(run, "JOB", job), patch.object(run, "S02_JOB", oldjob), \
                    patch.object(run, "source_module", return_value=source), \
                    patch.object(run, "committed_producers", return_value=[]), \
                    patch.object(run.subprocess, "check_output", return_value="synthetic\n"), \
                    patch.object(run, "canonical_s02", return_value=[pin]), \
                    patch.object(run, "expected_prepared_pins", return_value=[pin]), \
                    patch.object(run, "binary_path_scope"):

                registration = run.register()
                self.assertEqual(registration["account_specs"], run.account_specs())
                self.assertEqual(run.verify_registration()[1], dev + [trade])
                check = run.s02.check_trade_path
                with patch.object(run.s02, "check_trade_path", side_effect=lambda t, r:
                    0 if t["decision_msc"] < run.END else check(t, r)):
                    finished = run.execute("preflight")
                self.assertEqual(finished["status"], "COMPLETED")
                self.assertEqual(run.read(job / "preflight-1/preflight.json")["held_tick_visits"], 2)
                # A changed prepared book must fail at its binding, before native reads.
                self.save(prepared / "trades.json", [dict(trade, stop_units=120000)])
                with patch.object(run, "ValidationPrices") as reader:
                    with self.assertRaisesRegex(ValueError, "input_hash_changed"):
                        run.verify_registration()
                    reader.assert_not_called()

    def test_run_receipts_and_prefix_comparisons_use_native_empty_account_states(self):
        # This exercises orchestration/state/output, not alpha or native execution.
        from prop_portfolio_accounts import replay as native_replay
        with tempfile.TemporaryDirectory() as folder:
            job, oldjob = Path(folder) / "job", Path(folder) / "old"
            job.mkdir()
            self.save(job / "registration.json", {})
            dev = [{"asset": "GBPUSD"} for _ in range(733)]
            manifests = {a: {} for a in run.ASSETS}
            self.save(oldjob / "attempt-1/trades.json", dev)
            self.save(oldjob / "attempt-1/manifests.json", manifests)
            readers = lambda cutoff: {a: SimpleNamespace(files={}, cutoff=cutoff) for a in run.ASSETS}
            oldrows = native_replay([], readers(run.END), run.make_accounts(run.s02.account_specs()),
                                    end=run.END, assets=run.ASSETS)
            self.save(oldjob / "attempt-1/accounts.json", run.bind(oldrows, run.s02.account_specs()))
            calls = []
            def replay_without_events(trades, quote_readers, accounts, **kwargs):
                calls.append(kwargs["end"])
                return native_replay([], readers(kwargs["end"]), accounts, **kwargs)
            with patch.object(run, "JOB", job), patch.object(run, "S02_JOB", oldjob), \
                    patch.object(run, "verify_registration", return_value=({}, dev, manifests)), \
                    patch.object(run, "ValidationPrices", return_value=SimpleNamespace()), \
                    patch.object(run.s02, "DevelopmentPrices", return_value=SimpleNamespace()), \
                    patch.object(run.s02, "check_trade_path", return_value=0), \
                    patch.object(run, "replay", side_effect=replay_without_events):
                finished = run.execute("run")
            self.assertEqual(calls, [run.END, run.FINAL])
            self.assertEqual(finished["status"], "COMPLETED")
            output = job / "attempt-1"
            self.assertEqual(len(run.read(output / "accounts.json")), 104)
            self.assertEqual(run.read(output / "internal-prefix-review.json")["accounts"], 100)
            self.assertEqual(len(run.read(output / "extended-Development-boundary.json")["accounts"]), 212)
            self.assertFalse(run.read(output / "result.json")["prop_qualified"])


if __name__ == "__main__":
    unittest.main()
