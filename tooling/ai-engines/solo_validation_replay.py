"""S03 fixed historical validation; every real-data path requires a sealed release."""
import ast
from collections import Counter
from copy import deepcopy
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

import numpy as np

import solo_portfolio_replay as s02
from prop_campaign_source import Prices, START, END, FINAL, HOUR, DAY, stamp
from prop_portfolio_accounts import PortfolioAccount, replay
from prop_portfolio_scan import raw_geometry
from prop_portfolio_sources import deadline
from xau_h1_stage0_scan import funding_events

WORKSPACE = Path(__file__).resolve().parents[2]
ROOT = s02.ROOT
JOB = ROOT / "S03-three-asset-validation"
PROTOCOL = WORKSPACE / "planning/research/SOLO-THREE-ASSET-VALIDATION-PROTOCOL-20261118.md"
PARENT = Path("E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1")
S02_JOB = ROOT / "S02-three-asset-replay"
S02_RESULT_SHA = "2d56e5b50e3374b6c2e7fcb91382141f7b419248b4068789b8c6ffa13da83f65"
S02_REGISTRATION_SHA = "0ef567e0a132a10553c0cdc1ee846eb5ac461cc6c90f5c81cdc3d5e3a3cbc110"
S02_ORACLE = ROOT / "three-asset-preparation/independent-oracle/real-audit.json"
S02_ORACLE_SHA = "010efb944b7490fb1d53f81c6937a6cf9c51ac95251a712576ae8220ec02fb73"
ASSETS, MODELS, SYSTEMS, RISKS = s02.ASSETS, s02.MODELS, s02.SYSTEMS, s02.RISKS
SCOPE = "S03_HISTORICAL_VALIDATION_2024"
CONFIG = {**{k: deepcopy(v) for k, v in s02.CONFIG.items()
             if k not in ("accounts", "window", "prices2024_2026_read")},
          "accounts": 104, "verification_sentinels": 108,
          "window": {"first": START, "end_exclusive": FINAL},
          "validation_first": END, "prices2025_2026_read": False,
          "scheduled_closures_exempted": False, "replay_scope": SCOPE}
read, digest, pin, require = s02.read, s02.digest, s02.pin, s02.require


def source_module():
    # Lazy import keeps ordinary fixture imports from invoking any source stage.
    import solo_validation_source
    return solo_validation_source


def safe_output(path):
    path = Path(os.path.abspath(path))
    root = Path(os.path.abspath(JOB))
    require(path.is_relative_to(root), "S03_output_outside_owned_job")
    for part in (path, *path.parents):
        if part.exists():
            meta = part.lstat()
            require(not part.is_symlink() and not getattr(meta, "st_file_attributes", 0) & 0x400,
                    "S03_output_reparse_point")
    return path


def write_new(path, value):
    with safe_output(path).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def verify_pin(item):
    require(set(item) == {"path", "sha256"} and digest(item["path"]) == item["sha256"],
            "S03_input_hash_changed")


def producer_paths():
    folder = WORKSPACE / "tooling/ai-engines"
    pending, found = [Path(__file__).resolve(), folder / "solo_validation_source.py"], set()
    while pending:
        path = pending.pop()
        if path in found:
            continue
        found.add(path)
        for node in ast.walk(ast.parse(path.read_text(encoding="utf-8-sig"))):
            names = ([node.module] if isinstance(node, ast.ImportFrom) and node.module else
                     [i.name for i in node.names] if isinstance(node, ast.Import) else [])
            for name in names:
                child = folder / (name.split(".")[0] + ".py")
                if child.exists():
                    pending.append(child)
    found.update((PROTOCOL, folder / "tests/test_solo_validation_replay.py",
                  folder / "tests/test_solo_portfolio_accounts.py"))
    return sorted(found)


def committed_producers(commit):
    result = []
    for path in producer_paths():
        relative = path.relative_to(WORKSPACE).as_posix()
        blob = subprocess.check_output(["git", "show", commit + ":" + relative], cwd=WORKSPACE)
        require(blob.replace(b"\r\n", b"\n") == path.read_bytes().replace(b"\r\n", b"\n"),
                "S03_commit_implementation_before_release:" + relative)
        result.append(pin(path))
    return result


def canonical_s02():
    """Read only the immutable S02 result and its declared historical inputs."""
    result_path = S02_JOB / "attempt-1/result.json"
    registration_path = S02_JOB / "registration.json"
    require(digest(result_path) == S02_RESULT_SHA and
            digest(registration_path) == S02_REGISTRATION_SHA and
            digest(S02_ORACLE) == S02_ORACLE_SHA, "S03_canonical_S02_identity")
    result, registration, oracle = read(result_path), read(registration_path), read(S02_ORACLE)
    require(result["config"] == s02.CONFIG and result["accounts"] == 108 and result["trades"] == 733
            and result["registration_sha256"] == S02_REGISTRATION_SHA,
            "S03_S02_scope_changed")
    require(oracle.get("status") == "CORRECTNESS_PASS_FOR_DECLARED_S02_SCOPE",
            "S03_S02_oracle_not_passed")
    # Source changes in this branch do not invalidate an old committed producer.
    for item in registration["producer_pins"]:
        path = Path(item["path"]).resolve()
        require(path.is_relative_to(WORKSPACE), "S03_old_producer_outside_workspace")
        blob = subprocess.check_output(["git", "show", registration["producer_commit"] + ":" +
                                        path.relative_to(WORKSPACE).as_posix()], cwd=WORKSPACE)
        lf = blob.replace(b"\r\n", b"\n")
        require(item["sha256"] in {hashlib.sha256(b).hexdigest()
                                   for b in (blob, lf, lf.replace(b"\n", b"\r\n"))},
                "S03_old_committed_producer_changed")
    pins = [pin(result_path), pin(registration_path), pin(S02_ORACLE)]
    for name in ("trades.json", "manifests.json", "accounts.json", "account-specs.json"):
        path = S02_JOB / "attempt-1" / name
        require(digest(path) == result["artifact_sha256"][name], "S03_S02_artifact_changed")
        pins.append(pin(path))
    return pins


def metadata_manifest(manifest, first=START, end=FINAL):
    require(isinstance(manifest, dict) and manifest, "S03_empty_manifest")
    for key, row in manifest.items():
        require(isinstance(key, str) and str(int(key)) == key and int(key) % HOUR == 0
                and first <= int(key) < end, "S03_manifest_outside_window")
        require(type(row.get("records")) is int and row["records"] >= 0
                and isinstance(row.get("path"), str) and isinstance(row.get("sha256"), str)
                and len(row["sha256"]) == 64, "S03_manifest_shape")
    return manifest


def binary_path_scope(manifest, asset):
    require(asset in ASSETS, "S03_reader_asset_required")
    validation_roots = {
        "XAUUSD": PARENT / "xauusd-a-validation-20261114/attempt-2/ticks",
        "EURUSD": PARENT / "prop-portfolio-v3-20261114/eur-native-validation-v1",
        "GBPUSD": JOB / "gbp-source/ticks",
    }
    for key, item in manifest.items():
        path = Path(item["path"]).resolve()
        if int(key) >= END:
            require(path.name == f"{key}.ticks", "S03_binary_hour_filename")
            require(path.parent == validation_roots[asset].resolve(), "S03_validation_binary_owner")
        else:
            require(path.name in (f"{key}.ticks", f"{asset}-{key}.ticks"), "S03_binary_hour_filename")
            require(path.is_relative_to(PARENT.resolve()) or path.is_relative_to(
                (ROOT / "S01-gbp-confirmation").resolve()) or path.is_relative_to(
                (ROOT / "S01-gbp-confirmation-source-v2").resolve()),
                    "S03_Development_binary_owner")


class ValidationPrices(Prices):
    def __init__(self, manifest, asset):
        source_module().verify_release()
        metadata_manifest(manifest)  # Reject 2025 metadata before the reader filters it.
        binary_path_scope(manifest, asset)
        super().__init__(manifest, cutoff=FINAL)

    def hour(self, at):
        rows = super().hour(at)
        require(not len(rows) or bool(np.all(rows["b"] > 0)), "S03_nonpositive_quote")
        return rows


def validate_raw(raw, asset, manifest):
    require(asset in ("EURUSD", "GBPUSD") and isinstance(raw, list) and raw,
            "S03_raw_asset_or_empty")
    cell = f"{asset}.SWEEP.ASIA.LONDON.DAY"
    seen = set()
    for row in raw:
        at = row.get("decision_msc")
        require(row.get("asset") == asset and row.get("id") == cell and
                row.get("side") in ("BUY", "SELL") and type(at) is int and
                END <= at < FINAL and at % HOUR == 0 and
                type(row.get("stop_units")) is int and row["stop_units"] > 0,
                "S03_raw_recipe_or_window")
        key = (at, row["side"])
        require(key not in seen, "S03_duplicate_raw_intent")
        seen.add(key)
        for name in ("known_h4_at", "bias_h4_known_at"):
            require(row.get(name) is None or type(row[name]) is int and row[name] <= at,
                    "S03_future_signal_context")
        scheduled, _ = deadline(dict(row, horizon="DAY"), at)
        require(at < scheduled and scheduled + 60000 < FINAL, "S03_year_end_deadline")
        needed = range(at // HOUR * HOUR, scheduled // HOUR * HOUR + HOUR, HOUR)
        require(all(str(h) in manifest for h in needed), "S03_raw_hour_missing")


def realize_fx(raw, reader, asset):
    """Reuse the exact gate; first SL and closes are clipped by native ordinal."""
    trades, funnel = [], []
    recipe = "SAT1" if asset == "EURUSD" else "GBPUSD.SWEEP.ASIA.LONDON.DAY"
    for row in raw:
        entry = reader.endpoint(row["decision_msc"])
        require(entry is not None, "S03_entry_unknown")
        price, distance, friction, passes = raw_geometry(row, entry)
        record = {"decision_msc": row["decision_msc"], "side": row["side"],
                  "natural_sl": distance, "friction": friction, "passes": bool(passes)}
        if not passes:
            funnel.append(dict(record, reason="FRICTION_REJECT"))
            continue
        end, why = deadline(dict(row, horizon="DAY"), entry[0])
        require(entry[0] < end and end + 60000 < FINAL, "S03_year_end_deadline")
        final = reader.endpoint(end)
        require(final is not None, "S03_endpoint_unknown")
        ticks, ordinals = reader.path(entry[0], final[0])
        keep = ((ticks["t"] > entry[0]) | (ordinals >= entry[3])) & (
            (ticks["t"] < final[0]) | (ordinals <= final[3]))
        ticks, ordinals = ticks[keep], ordinals[keep]
        require(len(ticks) and (int(ticks["t"][0]), int(ordinals[0])) == (entry[0], entry[3])
                and (int(ticks["t"][-1]), int(ordinals[-1])) == (final[0], final[3]),
                "S03_native_ordinal_bounds")
        field = "b" if row["side"] == "BUY" else "a"
        hit = np.flatnonzero((ticks[field] <= row["stop_units"] if field == "b"
                              else ticks[field] >= row["stop_units"]) & (ticks["t"] < end))
        index = int(hit[0]) if len(hit) else len(ticks) - 1
        event = dict(row, asset=asset, recipe=recipe, role="SATELLITE", regime_weight=1,
                     signal_id=f"{recipe}:{row['decision_msc']}:{row['side']}",
                     entry_msc=entry[0], entry_price_units=price, entry_quote=entry[:3],
                     entry_quote_index=entry[3], deadline_msc=end, deadline_kind=why,
                     exit_msc=int(ticks["t"][index]), exit_quote_index=int(ordinals[index]),
                     exit_price_units=int(ticks[field][index]), reason="SL" if len(hit) else why)
        require(event["entry_msc"] // DAY == event["exit_msc"] // DAY and
                not funding_events(event["entry_msc"], event["exit_msc"]), "S03_FX_overnight")
        event = s02.normalized_event(event, asset)
        s02.check_trade_path(event, reader)
        trades.append(event)
        funnel.append(dict(record, reason="FILLED", signal_id=event["signal_id"]))
    require(len(trades) + sum(r["reason"] == "FRICTION_REJECT" for r in funnel) == len(raw),
            "S03_complete_raw_funnel")
    return trades, funnel


def same_event_facts(new, old):
    """Costs/quantity are not inherited; compare every locked execution fact."""
    fields = (*s02.EVENT_FIELDS, "entry_quote")
    def facts(rows):
        return [{key: row.get(key) for key in fields} for row in rows]
    require(facts(new) == facts(old), "S03_inherited_event_or_membership_changed")


def validate_trades(trades, manifests):
    require(trades and len({t["signal_id"] for t in trades}) == len(trades), "S03_trade_census")
    for trade in trades:
        asset = trade["asset"]
        require(asset in ASSETS and trade["side"] in ("BUY", "SELL"), "S03_trade_asset")
        keys = ("decision_msc", "entry_msc", "exit_msc", "deadline_msc", "stop_units",
                "entry_price_units", "exit_price_units", "entry_quote_index", "exit_quote_index")
        require(all(type(trade[k]) is int for k in keys), "S03_trade_integer")
        decision, entry, end, planned = (trade[k] for k in keys[:4])
        require(START <= decision <= entry <= end < FINAL and entry < planned and
                planned + 60000 < FINAL and end <= planned + 60000 and entry - decision <= 60000,
                "S03_trade_time_fence")
        require(min(trade[k] for k in keys[4:7]) > 0 and
                min(trade[k] for k in keys[7:]) >= 0, "S03_trade_grid")
        require(not entry < END <= end, "S03_Development_crossing")
        if asset == "XAUUSD":
            require(trade["recipe"] == "A" and trade.get("exit_policy") == "A0" and
                    trade.get("protected_stop_units") is None and trade.get("trigger_msc") is None
                    and trade["reason"] in ("SL", "TIME_48H", "FRIDAY_CLOSE", "HOLIDAY_FLAT"),
                    "S03_Gold_original_only")
        else:
            require(trade["recipe"] == ("SAT1" if asset == "EURUSD" else
                    "GBPUSD.SWEEP.ASIA.LONDON.DAY") and trade["reason"] in
                    ("SL", "DAY", "FRIDAY_CLOSE", "HOLIDAY_FLAT") and
                    entry // DAY == end // DAY and not funding_events(entry, end), "S03_FX_recipe")
        for name in ("known_h4_at", "bias_h4_known_at"):
            require(trade.get(name) is None or type(trade[name]) is int and trade[name] <= decision,
                    "S03_future_signal_context")
        needed = set(range(entry // HOUR * HOUR, end // HOUR * HOUR + HOUR, HOUR))
        needed.add(decision // HOUR * HOUR)
        if trade["reason"] != "SL":
            needed.add(planned // HOUR * HOUR)
        require(all(str(h) in manifests[asset] for h in needed), "S03_held_hour_missing")


def account_specs():
    scopes = [("CONTINUOUS_2022_2024", START, FINAL, False),
              ("ANNUAL_2024", END, FINAL, False)] + [
        (f"MONTHLY_{year}_{month:02d}", stamp(f"{year}-{month:02d}-01"), FINAL, True)
        for year in (2022, 2023) for month in range(1, 13)]
    return [dict(account_id=f"{model}:{system}:{scope}", model=model, system=system,
                 scope=scope, start=first, end=last, rolling=rolling, included_assets=list(assets))
            for model in MODELS for system, assets in SYSTEMS.items()
            for scope, first, last, rolling in scopes]


def make_accounts(specs):
    return [PortfolioAccount(s["start"], s["end"], s["model"], rolling=s["rolling"],
            fixed_risk=150, assets=ASSETS, included_assets=tuple(s["included_assets"]),
            fixed_asset_risk=dict(RISKS), track_quote_age=True, common_risk_usd=150,
            include_satellite=True, scaled=False) for s in specs]


def bind(rows, specs):
    require(len(rows) == len(specs), "S03_account_census")
    result = []
    for row, spec in zip(rows, specs):
        s02.native_account_identity(row, spec)
        require(not any(k in row for k in ("account_id", "model", "system", "scope")),
                "S03_account_already_labeled")
        result.append(dict(row, **{k: spec[k] for k in ("account_id", "model", "system", "scope")}))
    return result


def compare_sentinels(actual, expected):
    require(len(actual) == len(expected) == 108, "S03_sentinel_census")
    for got, old in zip(actual, expected):
        filtered = lambda row: {k: v for k, v in row.items() if k != "joint_tick_marks"}
        require(filtered(got) == filtered(old), "S03_Development_prefix_changed:" + old["account_id"])
    return {"status": "PREFIX_ROWS_IDENTICAL", "accounts": 108,
            "excluded_fields": ["joint_tick_marks"], "comparison": "full nested equality"}


def compare_internal(reference, extended, old_specs, new_specs):
    require(reference["at_msc"] == extended["at_msc"] == END, "S03_checkpoint_time")
    require(len(old_specs) == len(reference["accounts"]) == 108 and
            len(new_specs) == 104 and len(extended["accounts"]) == 212,
            "S03_internal_checkpoint_census")
    old = {s["account_id"]: state for s, state in zip(old_specs, reference["accounts"])}
    count = 0
    for spec, state in zip(new_specs, extended["accounts"]):
        if spec["scope"] == "ANNUAL_2024":
            continue
        scope = "CONTINUOUS_DEV" if spec["scope"] == "CONTINUOUS_2022_2024" else spec["scope"]
        key = f"{spec['model']}:{spec['system']}:{scope}"
        require(state == old[key], "S03_internal_prefix_changed:" + key)
        count += 1
    require(count == 100 and reference["stream"] == extended["stream"] and
            reference["coverage"] == extended["coverage"], "S03_stream_prefix_changed")
    require(reference["accounts"] == extended["accounts"][104:],
            "S03_sentinel_internal_prefix_changed")
    return {"status": "INTERNAL_PREFIX_IDENTICAL", "accounts": count,
            "stream_and_coverage_equal": True, "not_a_durable_resume_checkpoint": True}


def horizon_counts(rows):
    out = {}
    for days in (365, 730):
        limit = days * DAY
        passed = sum(any(p["phase"] == 2 and p["at"] - r["start_msc"] <= limit
                         for p in r["phase_passes"]) for r in rows)
        failed = sum(r["first_breach"] is not None and
                     r["first_breach"]["at"] - r["start_msc"] <= limit and
                     not any(p["phase"] == 2 and p["at"] <= r["first_breach"]["at"]
                             for p in r["phase_passes"]) for r in rows)
        short = sum(r["end_msc"] - r["start_msc"] < limit and r["first_breach"] is None
                    and not any(p["phase"] == 2 for p in r["phase_passes"]) for r in rows)
        out[str(days)] = {"completions": passed, "breach_before_completion": failed,
                          "insufficient_followup": short,
                          "no_completion_with_full_followup": len(rows) - passed - failed - short}
    out["completion_bands"] = {"up_to_365_days": 0, "over_365_up_to_730_days": 0,
                                "over_730_days": 0}
    for row in rows:
        passed = next((p for p in row["phase_passes"] if p["phase"] == 2), None)
        if passed:
            days = (passed["at"] - row["start_msc"]) / DAY
            bucket = "up_to_365_days" if days <= 365 else "over_365_up_to_730_days" if days <= 730 else "over_730_days"
            out["completion_bands"][bucket] += 1
    out["fit_365_days"] = ("NOT_DEMONSTRATED_IN_THIS_MODEL" if not out["365"]["completions"]
                            else "OBSERVED_COMPLETION_NOT_QUALIFICATION")
    return out


def summarize(rows, trades):
    specs = account_specs()
    require(len(rows) == len(specs) == 104 and len({r["account_id"] for r in rows}) == 104,
            "S03_summary_census")
    for row, spec in zip(rows, specs):
        require(all(row[k] == spec[k] for k in ("account_id", "model", "system", "scope")),
                "S03_selector_changed")
        s02.native_account_identity(row, spec)
        require(row["cash_bridge_verified"] and row["prop_qualified"] is False,
                "S03_account_bridge_or_promotion")
    diagnostic = [s02.compact_account(r) for r in rows if not r["rolling"]]
    lifecycle = {}
    reasons = []
    for model in MODELS:
        for system in SYSTEMS:
            subset = [r for r in rows if r["model"] == model and r["system"] == system and r["rolling"]]
            require(len(subset) == 24, "S03_monthly_census")
            lifecycle[f"{model}:{system}"] = dict(s02.lifecycle_summary(subset),
                                                  horizon_counts=horizon_counts(subset))
        annual = next(r for r in diagnostic if r["model"] == model and
                      r["system"] == "CANDIDATE_A_EUR_GBP" and r["scope"] == "ANNUAL_2024")
        if annual["net_usd"] <= 0:
            reasons.append("NONPOSITIVE_VALIDATION:" + model)
        full = {r["system"]: r for r in diagnostic if r["model"] == model and
                r["scope"] == "CONTINUOUS_2022_2024"}
        a, b = (full[x]["Net_over_equity_DD"] for x in SYSTEMS)
        if a is None or b is None or b < a:
            reasons.append("NET_DD_DEGRADED:" + model)
    path_unknown = any(r["quote_age_coverage"].get("path_complete") is not True for r in rows)
    breaches = any(r["first_breach"] is not None for r in rows if r["rolling"])
    contributions = []
    for row in rows:
        if row["rolling"]:
            continue
        grouped = {}
        for closed in row["closed"]:
            trade = trades[closed["trade"]]
            year = datetime.fromtimestamp(trade["exit_msc"] / 1000, timezone.utc).year
            key = (year, trade["asset"], trade["side"])
            group = grouped.setdefault(key, dict(year=year, asset=trade["asset"], side=trade["side"],
                trades=0, gross_usd=0, commission_usd=0, slippage_usd=0, swap_usd=0, net_usd=0))
            group["trades"] += 1
            for field in ("gross_usd", "commission_usd", "slippage_usd", "swap_usd", "net_usd"):
                group[field] += closed["costs"][field]
        require(abs(sum(r["net_usd"] for r in grouped.values()) - row["net_usd"]) < 1e-6,
                "S03_contribution_cash_bridge")
        contributions.append(dict(account_id=row["account_id"], rows=list(grouped.values())))
    return dict(status="CONDITIONAL_HISTORICAL_VALIDATION", economic_reasons=reasons,
                economic_status="G2_NOT_MET" if reasons else "G2_OBSERVED_NOT_EDGE_PROOF",
                path_status="DATA_PATH_INCOMPLETE" if path_unknown else "OBSERVED_SOURCE_PATH_ONLY",
                observed_modeled_breach=breaches, diagnostic_accounts=diagnostic, lifecycle=lifecycle,
                diagnostic_contributions=contributions,
                prop_qualified=False, independent_result_review="PENDING", prices2025_2026_read=False,
                historical_validation_exposed=True, scheduled_closures_exempted=False,
                limits=s02.LIMITS[1:] + ["2024 previously exposed; not clean OOS",
                                       "maintenance schedule historical effectiveness unverified"])


def inherited_validation_paths():
    v1 = PARENT / "prop-qualification-campaign-20261114"
    v3 = PARENT / "prop-portfolio-v3-20261114"
    gold = PARENT / "xauusd-a-validation-20261114"
    return {
        **{f"gold_{m}": v1 / f"frozen-system-{m}-trades.json" for m in MODELS},
        "gold_original_trades": gold / "attempt-2/trades.json",
        "gold_manifest": gold / "attempt-2/binary-manifest.json",
        "gold_source_review": gold / "attempt-2/source-review.json",
        "gold_corrections": gold / "source-v2/corrections.json",
        "eur_raw": v3 / "eur-satellite-validation-signals.json",
        "eur_signal_proof": v3 / "eur-satellite-validation-signal-proof.json",
        "eur_trades": v3 / "eur-satellite-validation-trades.json",
        "eur_funnel": v3 / "eur-satellite-validation-funnel.json",
        "eur_manifest": v3 / "eur-native-validation-v1/manifest.json",
        "eur_source_proof": v3 / "eur-native-validation-v1/source-proof.json",
    }


def admitted_gbp_source():
    module = source_module()
    registration = module.verify_source_registration()
    folder = module.SOURCE_JOB
    proof, manifest = read(folder / "source-proof.json"), read(folder / "manifest.json")
    require(proof.get("status") == "SOURCE_RECONCILED" and
            proof.get("registration_sha256") == digest(folder / "registration.json") and
            proof.get("manifest_sha256") == digest(folder / "manifest.json") and
            proof.get("expected_hours") == proof.get("admitted_hours") == len(manifest) and
            proof.get("h1_difference_count") == 0 and proof.get("empty_hours") == [] and
            proof.get("held_path_issue_count") == 0 and proof.get("same_ms_order_preserved") is True
            and proof.get("source_only") is True and proof.get("prices2025_2026_read") is False,
            "S03_GBP_source_not_admitted")
    require(sorted(map(int, manifest)) == registration["hours"], "S03_GBP_hour_census")
    metadata_manifest(manifest, END, FINAL)
    reconciliation = read(folder / "h1-reconciliation.json")
    quality = read(folder / "held-path-quality.json")
    require(reconciliation.get("mismatches") == [] and reconciliation.get("empty_hours") == []
            and reconciliation.get("original_sources_modified") is False and
            reconciliation.get("prices2025_2026_read") is False and quality.get("issues") == []
            and quality.get("raw_signals") == len(registration["signals"])
            and quality.get("maximum_unregistered_gap_ms") == 900000 and
            quality.get("scheduled_closures_exempted") is False, "S03_GBP_source_details_failed")
    checks = proof.get("source_checks", [])
    require(len(checks) == len(manifest) and [r["at"] for r in checks] == registration["hours"]
            and all(r["binary_sha256"] == manifest[str(r["at"])]["sha256"] for r in checks)
            and proof.get("paired_tick_records") == sum(r["records"] for r in manifest.values()),
            "S03_GBP_source_checks_changed")
    names = ("registration.json", "source-proof.json", "manifest.json",
             "held-path-quality.json", "h1-reconciliation.json")
    return registration["signals"], manifest, [pin(folder / name) for name in names]


def validate_eur_h1_pins(pins):
    expected = {str((PARENT / "eurusd-b0-20261113/prepared-v1" / part / "bars.json").resolve())
                for part in ("20211101", "20220101", "20230101", "20240101")}
    require(len(pins) == 4 and {str(Path(item["path"]).resolve()) for item in pins} == expected,
            "S03_EUR_H1_source_path_census")
    for item in pins:
        verify_pin(item)


def inherited_source_semantics(paths, manifests, raw_eur):
    """Validate source-only review contracts; pinning arbitrary bytes is not admission."""
    review = read(paths["gold_source_review"])
    require(review.get("mismatches") == [] and isinstance(review.get("hours"), list),
            "S03_Gold_source_review_failed")
    reviewed = {}
    for row in review["hours"]:
        require(type(row.get("at")) is int and isinstance(row.get("binary"), dict)
                and row.get("missing_M1_minutes") == [], "S03_Gold_review_hour")
        at = str(row["at"])
        require(at not in reviewed, "S03_Gold_review_duplicate_hour")
        reviewed[at] = row["binary"]
    require(all(key in reviewed and reviewed[key] == item
                for key, item in manifests["XAUUSD"].items() if int(key) >= END),
            "S03_Gold_manifest_not_source_reviewed")
    source = read(paths["eur_source_proof"])
    require(source.get("manifest_sha256") == digest(paths["eur_manifest"]) and
            source.get("cutoff") == FINAL and source.get("prices2025_2026_read") is False and
            source.get("preserves_source_order_and_same_ms") is True and
            source.get("hours") == len(manifests["EURUSD"]), "S03_EUR_source_binding")
    signal = read(paths["eur_signal_proof"])
    require(signal.get("cells") == ["EURUSD.SWEEP.ASIA.LONDON.DAY"] and
            signal.get("parameter_reselection") is False and signal.get("raw") == len(raw_eur)
            and isinstance(signal.get("pins"), list) and signal["pins"],
            "S03_EUR_signal_source_contract")
    validate_eur_h1_pins(signal["pins"])
    funnel = read(paths["eur_funnel"])
    require(funnel.get("raw") == len(raw_eur) and type(funnel.get("filled")) is int
            and isinstance(funnel.get("skipped"), list) and
            funnel["filled"] + len(funnel["skipped"]) == len(raw_eur), "S03_EUR_funnel_contract")


def original_gold_parity(candidate, original):
    fields = ("decision_msc", "side", "entry_msc", "exit_msc", "entry_price_units",
              "exit_price_units", "stop_units", "entry_quote_index", "exit_quote_index",
              "deadline_msc", "reason")
    require(len(candidate) == len(original) and
            [[row[k] for k in fields] for row in candidate] ==
            [[row[k] for k in fields] for row in original], "S03_original_Gold_path_changed")


def inherited_release_pins(release):
    expected = inherited_validation_paths()
    pins = release.get("inherited_validation")
    require(isinstance(pins, dict) and set(pins) == set(expected),
            "S03_release_inherited_pin_census")
    for name, path in expected.items():
        item = pins[name]
        require(Path(item.get("path", "")).resolve() == path.resolve(),
                "S03_inherited_source_path_changed")
        verify_pin(item)
    return list(pins.values())


def expected_prepared_pins():
    release = source_module().verify_release()
    inherited = inherited_release_pins(release)
    _, _, gbp = admitted_gbp_source()
    return canonical_s02() + gbp + inherited + [pin(JOB / "source-release.json")]


def merge_extension_manifest(previous, extension):
    metadata_manifest(previous, START, END)
    metadata_manifest(extension, END, FINAL)
    return {**previous, **extension}


def prepared_inputs():
    source_module().verify_release()
    folder = safe_output(JOB / "prepare-1")
    proof = read(folder / "proof.json")
    require(proof.get("status") == "PREPARED_PATHS_NOT_FINANCIAL_OUTCOMES" and
            proof.get("prices2025_2026_read") is False and
            proof.get("source_release_sha256") == digest(JOB / "source-release.json"),
            "S03_preparation_scope")
    require(set(proof.get("artifact_sha256", {})) == {"trades.json", "manifests.json", "fx-funnels.json"}
            and proof.get("input_pins") == expected_prepared_pins(), "S03_preparation_pin_census")
    for item in proof["input_pins"] + proof["producer_pins"]:
        verify_pin(item)
    require(proof["producer_pins"] == committed_producers(proof["producer_commit"]),
            "S03_preparation_producer_changed")
    for name, sha in proof["artifact_sha256"].items():
        require(Path(name).name == name and digest(folder / name) == sha,
                "S03_prepared_artifact_changed")
    trades, manifests = read(folder / "trades.json"), read(folder / "manifests.json")
    dev_trades = read(S02_JOB / "attempt-1/trades.json")
    dev_manifests = read(S02_JOB / "attempt-1/manifests.json")
    require(trades[:733] == dev_trades and len(dev_trades) == 733 and
            all(t["decision_msc"] >= END for t in trades[733:]), "S03_prefix_book_changed")
    require(set(manifests) == set(ASSETS) and all(
        {k: v for k, v in manifests[a].items() if int(k) < END} == dev_manifests[a] for a in ASSETS),
        "S03_prefix_manifest_changed")
    for manifest in manifests.values():
        metadata_manifest(manifest)
    validate_trades(trades, manifests)
    return proof, trades, manifests


def prepare():
    """Materialize unchanged event paths only after source/code release, before PnL."""
    release = source_module().verify_release()
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    producers = committed_producers(head)
    canonical = canonical_s02()
    raw_gbp, gbp_manifest, gbp_pins = admitted_gbp_source()
    paths = inherited_validation_paths()
    inputs = canonical + gbp_pins + inherited_release_pins(release) + [pin(JOB / "source-release.json")]
    folder = safe_output(JOB / "prepare-1")
    folder.mkdir(exist_ok=False)
    write_new(folder / "execution-start.json", dict(pid=os.getpid(), utc=datetime.now(timezone.utc).isoformat(),
              source_release_sha256=digest(JOB / "source-release.json"), new_financial_outcomes_computed=False))
    try:
        dev = read(S02_JOB / "attempt-1/trades.json")
        dev_manifests = read(S02_JOB / "attempt-1/manifests.json")
        require(len(dev) == 733, "S03_Development_trade_count")
        gold_all = [[s02.normalized_event(t, "XAUUSD") for t in read(paths["gold_" + m])]
                    for m in MODELS]
        require(gold_all[0] == gold_all[1], "S03_Gold_models_have_different_events")
        original_gold_parity(gold_all[0], read(paths["gold_original_trades"]))
        gold_dev = [t for t in gold_all[0] if t["entry_msc"] < END]
        require(gold_dev == [t for t in dev if t["asset"] == "XAUUSD"],
                "S03_Gold_Development_changed")
        gold_extension = [t for t in gold_all[0] if t["entry_msc"] >= END]
        full_gold_manifest = metadata_manifest(read(paths["gold_manifest"]))
        gold_extension_manifest = {k: v for k, v in full_gold_manifest.items() if int(k) >= END}
        eur_manifest = metadata_manifest(read(paths["eur_manifest"]), END, FINAL)
        raw_eur = read(paths["eur_raw"])
        inherited_source_semantics(paths, {"XAUUSD": gold_extension_manifest, "EURUSD": eur_manifest}, raw_eur)
        validate_raw(raw_eur, "EURUSD", eur_manifest)
        validate_raw(raw_gbp, "GBPUSD", gbp_manifest)
        eur, eur_funnel = realize_fx(raw_eur, ValidationPrices(eur_manifest, "EURUSD"), "EURUSD")
        old_eur = [s02.normalized_event(t, "EURUSD") for t in read(paths["eur_trades"])]
        same_event_facts(eur, old_eur)
        gbp, gbp_funnel = realize_fx(raw_gbp, ValidationPrices(gbp_manifest, "GBPUSD"), "GBPUSD")
        extension = sorted(gold_extension + eur + gbp, key=lambda t: (
            t["entry_msc"], ASSETS.index(t["asset"]), t["entry_quote_index"], t["signal_id"]))
        trades = dev + extension
        manifests = {a: merge_extension_manifest(dev_manifests[a], m) for a, m in zip(
            ASSETS, (gold_extension_manifest, eur_manifest, gbp_manifest))}
        validate_trades(trades, manifests)
        readers = {a: ValidationPrices(m, a) for a, m in manifests.items()}
        visits = sum(s02.check_trade_path(t, readers[t["asset"]]) for t in extension)
        for item in inputs:
            verify_pin(item)
        require(producers == committed_producers(head), "S03_prepare_source_changed")
        write_new(folder / "trades.json", trades)
        write_new(folder / "manifests.json", manifests)
        write_new(folder / "fx-funnels.json", {"EURUSD": eur_funnel, "GBPUSD": gbp_funnel})
        proof = dict(status="PREPARED_PATHS_NOT_FINANCIAL_OUTCOMES", producer_commit=head,
                     producer_pins=producers, input_pins=inputs,
                     source_release_sha256=digest(JOB / "source-release.json"),
                     development_trades_unchanged=733, extension_trades=len(extension),
                     raw_FX_counts={"EURUSD": len(raw_eur), "GBPUSD": len(raw_gbp)},
                     extension_trade_census=dict(Counter(t["asset"] for t in extension)),
                     checked_native_path_visits=visits, new_financial_outcomes_computed=False,
                     prices2025_2026_read=False, EUR_membership_unchanged=True,
                     artifact_sha256={name: digest(folder / name) for name in
                                      ("trades.json", "manifests.json", "fx-funnels.json")})
        write_new(folder / "proof.json", proof)
        return proof
    except BaseException as error:
        write_new(folder / "failure.json", dict(status="FAILED", utc=datetime.now(timezone.utc).isoformat(),
                  type=type(error).__name__, error=str(error), new_financial_outcomes_computed=False))
        raise


def register():
    proof, trades, manifests = prepared_inputs()
    require(canonical_s02(), "S03_missing_parent")
    path = safe_output(JOB / "registration.json")
    if path.exists():
        return verify_registration()[0]
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    producers = committed_producers(commit)
    result = dict(schema="solo-three-asset-validation-financial-v1", job_root=str(safe_output(JOB)),
                  created_utc=datetime.now(timezone.utc).isoformat(), producer_commit=commit,
                  producer_pins=producers, input_pins=proof["input_pins"] + [pin(JOB / "prepare-1" / n)
                    for n in ("proof.json", "trades.json", "manifests.json", "fx-funnels.json")],
                  config=CONFIG, source_release_sha256=digest(JOB / "source-release.json"),
                  account_specs=account_specs(), sentinel_specs=s02.account_specs(),
                  trade_census=dict(Counter(t["asset"] for t in trades)),
                  manifest_hours={a: len(m) for a, m in manifests.items()},
                  python_version=sys.version, numpy_version=np.__version__,
                  prices2025_2026_read=False, new_financial_outcomes_computed=False,
                  strategy_parameters_changed=False, prop_qualified=False)
    write_new(path, result)
    return result


def verify_registration():
    source_module().verify_release()
    row = read(safe_output(JOB / "registration.json"))
    require(row.get("schema") == "solo-three-asset-validation-financial-v1" and
            row.get("job_root") == str(safe_output(JOB)) and row.get("config") == CONFIG and
            row.get("account_specs") == account_specs() and row.get("sentinel_specs") == s02.account_specs()
            and row.get("prices2025_2026_read") is False and row.get("prop_qualified") is False
            and row.get("python_version") == sys.version and row.get("numpy_version") == np.__version__,
            "S03_financial_registration_scope")
    require(row["source_release_sha256"] == digest(JOB / "source-release.json"), "S03_release_changed")
    for item in row["input_pins"] + row["producer_pins"]:
        verify_pin(item)
    require(row["producer_pins"] == committed_producers(row["producer_commit"]),
            "S03_financial_producer_changed")
    proof, trades, manifests = prepared_inputs()
    expected_inputs = proof["input_pins"] + [pin(JOB / "prepare-1" / n)
        for n in ("proof.json", "trades.json", "manifests.json", "fx-funnels.json")]
    require(row["input_pins"] == expected_inputs and
            row["trade_census"] == dict(Counter(t["asset"] for t in trades)) and
            row["manifest_hours"] == {a: len(m) for a, m in manifests.items()},
            "S03_financial_input_census")
    canonical_s02()
    return row, trades, manifests


def report_text(summary):
    lines = ["# S03 — unchanged portfolio historical validation", "",
             "Conditional observed-source results; not Challenge qualification or clean OOS.",
             "", "|Model|System|Scope|Net USD|Equity DD USD|Worst daily %|",
             "|---|---|---|---:|---:|---:|"]
    for r in summary["diagnostic_accounts"]:
        lines.append(f"|{r['model']}|{r['system']}|{r['scope']}|{r['net_usd']:.2f}|"
                     f"{r['equity_DD_usd']:.2f}|{r['worst_daily_loss_pct']:.4f}|")
    lines += ["", "|Model/System|P1|P2|P2 within365days|Proxy payout events|",
              "|---|---:|---:|---:|---:|"]
    for name, r in summary["lifecycle"].items():
        lines.append(f"|{name}|{r['phase1_passes']}|{r['both_phases_passed']}|"
                     f"{r['horizon_counts']['365']['completions']}|{r['reward_proxy_events']}|")
    lines += ["", f"Economics: {summary['economic_status']}; path: {summary['path_status']}.",
              "Overlapping monthly starts are not independent trials or pass probabilities.", ""]
    return "\n".join(lines)


def execute(action):
    require(action in ("preflight", "run"), "S03_action")
    registration, trades, manifests = verify_registration()
    folder = safe_output(JOB / ("preflight-1" if action == "preflight" else "attempt-1"))
    folder.mkdir(exist_ok=False)
    identity = dict(pid=os.getpid(), action=action, started_utc=datetime.now(timezone.utc).isoformat(),
                    registration_sha256=digest(JOB / "registration.json"), prices2025_2026_read=False,
                    new_financial_outcomes_computed=action == "run")
    write_new(folder / "execution-start.json", identity)
    events = safe_output(folder / "events.jsonl")
    with events.open("x", encoding="utf-8"):
        pass
    def progress(stage, **fields):
        event = dict(utc=datetime.now(timezone.utc).isoformat(), stage=stage, **fields)
        with events.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps(event) + "\n")
        print(json.dumps(event), flush=True)
    try:
        readers = {a: ValidationPrices(m, a) for a, m in manifests.items()}
        visits = 0
        for index, trade in enumerate(trades):
            visits += s02.check_trade_path(trade, readers[trade["asset"]])
            if (index + 1) % 100 == 0:
                progress("path_preflight", checked=index + 1, total=len(trades))
        preflight = dict(status="NATIVE_PATHS_CHECKED", trades=len(trades), held_tick_visits=visits,
                         scheduled_closures_exempted=False, prices2025_2026_read=False)
        write_new(folder / "preflight.json", preflight)
        if action == "preflight":
            result = preflight
        else:
            old_specs = s02.account_specs()
            old_accounts = make_accounts(old_specs)
            dev_trades = trades[:733]
            require(dev_trades == read(S02_JOB / "attempt-1/trades.json"), "S03_prefix_book_changed")
            dev_manifests = read(S02_JOB / "attempt-1/manifests.json")
            require(all({k: v for k, v in manifests[a].items() if int(k) < END} == dev_manifests[a]
                        for a in ASSETS), "S03_prefix_manifest_changed")
            reference_snapshots = []
            progress("Development_reference_started", accounts=108)
            ref_rows = replay(dev_trades, {a: s02.DevelopmentPrices(m) for a, m in dev_manifests.items()},
                              old_accounts, end=END, assets=ASSETS, progress=progress,
                              checkpoints=(END,), checkpoint_callback=reference_snapshots.append)
            old_rows = read(S02_JOB / "attempt-1/accounts.json")
            reference_review = compare_sentinels(bind(ref_rows, old_specs), old_rows)
            specs = account_specs()
            all_specs = specs + old_specs
            snapshots = []
            progress("Historical_continuation_started", reported=104, sentinels=108)
            all_rows = replay(trades, readers, make_accounts(all_specs), end=FINAL, assets=ASSETS,
                              replay_scope=SCOPE, progress=progress, checkpoints=(END,),
                              checkpoint_callback=snapshots.append)
            require(len(reference_snapshots) == len(snapshots) == 1, "S03_checkpoint_census")
            sentinel_review = compare_sentinels(bind(all_rows[104:], old_specs), old_rows)
            internal_review = compare_internal(reference_snapshots[0], snapshots[0], old_specs, specs)
            rows = bind(all_rows[:104], specs)
            summary = summarize(rows, trades)
            write_new(folder / "trades.json", trades)
            write_new(folder / "manifests.json", manifests)
            write_new(folder / "account-specs.json", specs)
            write_new(folder / "accounts.json", rows)
            write_new(folder / "sentinel-accounts.json", bind(all_rows[104:], old_specs))
            write_new(folder / "prefix-review.json", dict(reference=reference_review, extended=sentinel_review))
            write_new(folder / "internal-prefix-review.json", internal_review)
            write_new(folder / "Development-boundary-reference.json", reference_snapshots[0])
            write_new(folder / "extended-Development-boundary.json", snapshots[0])
            write_new(folder / "summary.json", summary)
            with safe_output(folder / "REPORT.md").open("x", encoding="utf-8") as stream:
                stream.write(report_text(summary))
            result = dict(schema="solo-three-asset-validation-result-v1", status=summary["status"],
                          config=CONFIG, accounts=104, sentinel_accounts=108, trades=len(trades),
                          economic_status=summary["economic_status"], path_status=summary["path_status"],
                          prop_qualified=False, independent_result_review="PENDING",
                          historical_validation_exposed=True, prices2025_2026_read=False)
        verify_registration()
        result["registration_sha256"] = identity["registration_sha256"]
        result["artifact_sha256"] = {p.name: digest(p) for p in folder.iterdir()
                                     if p.is_file() and p.name != "events.jsonl"}
        write_new(folder / "result.json", result)
        finish = dict(identity, finished_utc=datetime.now(timezone.utc).isoformat(), status="COMPLETED",
                      result_sha256=digest(folder / "result.json"), numerical_status=result["status"])
        write_new(folder / "execution-finish.json", finish)
        progress("completed", status=result["status"])
        return finish
    except BaseException as error:
        write_new(folder / "failure.json", dict(identity, failed_utc=datetime.now(timezone.utc).isoformat(),
                  status="FAILED", error_type=type(error).__name__, error=str(error)))
        raise


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("prepare", "register", "preflight", "run"))
    action = parser.parse_args().action
    result = prepare() if action == "prepare" else register() if action == "register" else execute(action)
    print(json.dumps({"action": action, "status": result.get("status", "REGISTERED")}))
