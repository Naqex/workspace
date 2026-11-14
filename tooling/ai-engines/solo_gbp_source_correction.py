"""Register/admit the two audited GBP H1 corrections without changing S01 rules."""
from copy import deepcopy
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import subprocess

from solo_gbp_source import (JOB as ORIGINAL, WORKSPACE, CODE, PROTOCOL, CELL,
    START, END, census, read, digest, source_pin, verify_pins, output_root,
    decoded_array, atomic_json, admit as admit_source)

JOB = ORIGINAL.with_name("S01-gbp-confirmation-source-v2")
HOURS = (1666094400000, 1666105200000)
PRICE_KEYS = ("open", "high", "low", "close")
CORRECTION_PROTOCOL = "planning/research/SOLO-GBP-SOURCE-CORRECTION-V2-20261115.md"
PRODUCER = "tooling/ai-engines/solo_gbp_source_correction.py"
REVIEW_FILES = ("DIAGNOSIS.md", "source-diagnosis.json",
    "inherited-H1-source-and-fetch-check.json", "prefetch-protocol.json",
    "prefetch-protocol-sha256.json", "fetch-results.json", "review_source.py",
    "cohort-sensitivity.py", "cohort-sensitivity/registration.json",
    "cohort-sensitivity/result.json", "cohort-sensitivity/corrected-signals.json",
    "fetch-receipt-1.json", "fetch-receipt-2.json", "fetch-receipt-3.json",
    "fetch-receipt-4.json")


def canonical_digest(value):
    """Hash a JSON value with the self-binding field omitted by the caller."""
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"),
                           ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def assert_plain_child(job, name):
    """Reject symlink/junction output children before any admission write."""
    path = Path(job) / name
    if not path.exists() and not path.is_symlink():
        return
    metadata = path.lstat()
    if path.is_symlink() or getattr(metadata, "st_file_attributes", 0) & 0x400:
        raise ValueError("S01v2_output_link_forbidden:" + name)
    if not path.is_dir():
        raise ValueError("S01v2_output_child_not_directory:" + name)


def verify_refetch_unknown(review):
    """Require the exact four failed HTTP202 empty responses before labeling UNKNOWN."""
    review = Path(review)
    result = read(review / "fetch-results.json")
    rows = result.get("requests", [])
    expected = {
        "https://jetta.dukascopy.com/v1/ticks/GBP-USD/2022/10/18/12",
        "https://jetta.dukascopy.com/v1/ticks/GBP-USD/2022/10/18/15",
        "https://jetta.dukascopy.com/v1/candles/hour/GBP-USD/BID/2022/10",
        "https://jetta.dukascopy.com/v1/candles/hour/GBP-USD/ASK/2022/10",
    }
    if (len(rows) != 4 or {row.get("url") for row in rows} != expected or
            result.get("no_retry") is not True or
            result.get("financial_results_computed") is not False):
        raise ValueError("S01v2_refetch_receipt_shape")
    if any(row.get("status") != "FAILED_UNKNOWN" or row.get("http_status") != 202 or
           row.get("response_headers", {}).get("Content-Type") != "text/html; charset=UTF-8"
           for row in rows):
        raise ValueError("S01v2_refetch_not_unknown_202_html")
    empty = sorted(review.glob("refetch-*.json"))
    if len(empty) != 4 or any(path.stat().st_size != 0 for path in empty):
        raise ValueError("S01v2_refetch_body_not_empty")
    return source_pin(review / "fetch-results.json")


def committed_producer_pins():
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    pins = []
    for relative in (*CODE, PROTOCOL, PRODUCER, CORRECTION_PROTOCOL):
        path = WORKSPACE / relative
        committed = subprocess.check_output(["git", "show", head + ":" + relative], cwd=WORKSPACE)
        if committed.replace(b"\r\n", b"\n") != path.read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("S01v2_commit_before_source_correction:" + relative)
        pins.append(source_pin(path))
    return head, pins


def verify_cohort(original, corrected, result):
    signals, hours = census(original["signals"])
    if (signals != original["signals"] or hours != original["hours"] or
            len(signals) != 300 or len(hours) != 3576 or corrected != signals or
            result.get("original_reproduced") is not True or
            result.get("original_count") != 300 or result.get("corrected_count") != 300 or
            result.get("events_added") != [] or result.get("events_removed") != [] or
            result.get("changes") != [] or result.get("source_only") is not True or
            result.get("financial_outcomes") is not False or
            result.get("prices2024_2026_read") is not False):
        raise ValueError("S01v2_full_cohort_or_stop_changed")


def correct_book(rows, replacements):
    """Replace OHLC at the two registered hours; retain timestamps/volume/other rows."""
    if set(replacements) != set(HOURS):
        raise ValueError("S01v2_exact_two_hours_required")
    corrected = deepcopy(rows)
    changes, seen = [], set()
    previous = START - 1
    for before, after in zip(rows, corrected):
        at = before["timestamp"]
        if type(at) is not int or not START <= at < END or at <= previous:
            raise ValueError("S01v2_H1_clock_or_window")
        previous = at
        if at not in replacements:
            continue
        units = replacements[at]
        if (len(units) != 4 or any(type(v) is not int or v <= 0 for v in units) or
                units[2] > min(units[0], units[3]) or units[1] < max(units[0], units[3])):
            raise ValueError("S01v2_replacement_OHLC")
        for key, value in zip(PRICE_KEYS, units):
            after[key] = float(Decimal(value) / 100000)
        old_units = [int(Decimal(str(before[key])) * 100000) for key in PRICE_KEYS]
        if old_units == units:
            raise ValueError("S01v2_registered_discrepancy_missing")
        seen.add(at)
        changes.append(dict(at=at, original_units=old_units, corrected_units=units))
    if seen != set(HOURS):
        raise ValueError("S01v2_missing_registered_H1_hour")
    # Any extra change, including volume, would invalidate the scoped correction.
    for before, after in zip(rows, corrected):
        allowed = set(PRICE_KEYS) if before["timestamp"] in HOURS else set()
        if set(before) != set(after) or any(before[key] != after[key] for key in before if key not in allowed):
            raise ValueError("S01v2_unregistered_book_change")
    return corrected, changes


def reuse_all(original, manifest, seals, proof):
    expected = {str(at) for at in original["hours"]}
    if (len(original.get("reused", {})) != 292 or
            len(original.get("missing_hours", [])) != 3284):
        raise ValueError("S01v2_source_reuse_census")
    if (set(manifest) != expected or len(seals) != len({row["at"] for row in seals}) or
            {row["at"] for row in seals} != set(original["missing_hours"])):
        raise ValueError("S01v2_source_census_changed")
    downloaded = {str(row["at"]): row for row in seals}
    checks = {str(row["at"]): row for row in proof["source_checks"]}
    if len(checks) != len(proof["source_checks"]) or set(checks) != expected:
        raise ValueError("S01v2_source_proof_census")
    reused = {}
    for key in sorted(expected, key=int):
        binary = manifest[key]
        raw = original["reused"].get(key) or downloaded[key]
        if (checks[key]["binary_sha256"] != binary["sha256"] or
                checks[key]["raw_sha256"] != raw["raw_sha256"]):
            raise ValueError("S01v2_source_hash_lineage")
        reused[key] = dict(binary, raw_path=raw["raw_path"], raw_sha256=raw["raw_sha256"])
    return reused


def register(job=JOB, original_job=ORIGINAL):
    job, original_job = output_root(job), Path(original_job).resolve()
    if job.resolve() == original_job or job.resolve().is_relative_to(original_job):
        raise ValueError("S01v2_original_job_read_only")
    if job.parent.resolve() != original_job.parent or job.name != "S01-gbp-confirmation-source-v2":
        raise ValueError("S01v2_registered_sibling_only")
    if job.exists():
        raise ValueError("S01v2_new_output_required")
    head, producers = committed_producer_pins()
    original = read(original_job / "registration.json")
    verify_pins(original)
    if (original["cell"] != CELL or original["prior_stage0_pass"] is not False or
            original["prior_raw_edge_proven"] is not False or
            original["prices2024_2026_read"] is not False):
        raise ValueError("S01v2_original_scope_or_negative_history")
    review = original_job / "source-discrepancy-review"
    refetch_pin = verify_refetch_unknown(review)
    sensitivity = read(review / "cohort-sensitivity/result.json")
    corrected_signals = read(review / "cohort-sensitivity/corrected-signals.json")
    verify_cohort(original, corrected_signals, sensitivity)
    sensitivity_registration = read(review / "cohort-sensitivity/registration.json")
    transitive_pins = []
    for pin in sensitivity_registration["pins"] + sensitivity["input_books"]:
        if digest(pin["path"]) != pin["sha256"]:
            raise ValueError("S01v2_source_sensitivity_input_changed")
        transitive_pins.append(source_pin(pin["path"]))
        if "proof_path" in pin and digest(pin["proof_path"]) != pin["proof_sha256"]:
            raise ValueError("S01v2_source_sensitivity_proof_changed")
        if "proof_path" in pin:
            transitive_pins.append(source_pin(pin["proof_path"]))
    proof = read(original_job / "source-proof.json")
    manifest = read(original_job / "manifest.json")
    mismatch = read(original_job / "h1-reconciliation.json")
    if (proof["status"] != "SOURCE_REVIEW_REQUIRED" or proof["expected_hours"] != 3576 or
            proof["admitted_hours"] != 3576 or proof["paired_tick_records"] != 25537048 or
            proof["h1_difference_count"] != 4 or proof["empty_hours"] != [] or
            proof["held_path_issue_count"] != 0 or
            proof["registration_sha256"] != digest(original_job / "registration.json") or
            proof["manifest_sha256"] != digest(original_job / "manifest.json")):
        raise ValueError("S01v2_original_source_review_changed")
    differences = {(row["at"], row["side"]): row for row in mismatch["mismatches"]}
    if (len(mismatch["mismatches"]) != 4 or len(differences) != 4 or
            set(differences) != {(at, side) for at in HOURS for side in ("bid", "ask")}):
        raise ValueError("S01v2_only_registered_four_side_differences")
    reused = reuse_all(original, manifest, read(original_job / "source/sealed-hours.json"), proof)
    replacements = {"bid": {}, "ask": {}}
    for at in HOURS:
        row = reused[str(at)]
        if digest(row["raw_path"]) != row["raw_sha256"] or digest(row["path"]) != row["sha256"]:
            raise ValueError("S01v2_corrected_hour_source_changed")
        ticks = decoded_array(read(row["raw_path"]), at)
        if ticks.tobytes() != Path(row["path"]).read_bytes():
            raise ValueError("S01v2_corrected_hour_raw_binary_parity")
        for side, field in (("bid", "b"), ("ask", "a")):
            values = [int(ticks[field][0]), int(ticks[field].max()),
                      int(ticks[field].min()), int(ticks[field][-1])]
            if values != differences[(at, side)]["tick_units"]:
                raise ValueError("S01v2_tick_reconciliation_changed")
            replacements[side][at] = values
    corrected_books, changes = {}, {}
    for side in ("bid", "ask"):
        detail = original["h1_source_books"][f"2022-gbpusd-{side}"]
        corrected_books[side], changes[side] = correct_book(read(detail["book"]), replacements[side])
        for change in changes[side]:
            if change["original_units"] != differences[(change["at"], side)]["h1_units"]:
                raise ValueError("S01v2_old_book_discrepancy_changed")
    pins = [source_pin(original_job / name) for name in
            ("registration.json", "source-proof.json", "manifest.json", "h1-reconciliation.json", "source/sealed-hours.json")]
    pins += [source_pin(review / name) for name in REVIEW_FILES]
    pins += transitive_pins
    pins += original["input_pins"]
    pins.append(refetch_pin)
    card = dict(schema="S01-source-correction-v2", registered_utc=datetime.now(timezone.utc).isoformat(),
        original_job=str(original_job), changes=changes, source_pins=pins,
        same_vendor=True, independent_feed_verified=False, FTMO_feed_verified=False,
        fresh_refetch_status="UNKNOWN_HTTP202_EMPTY_FOUR_REQUESTS",
        authority="sealed paired ticks for exactly two hours; independent integer decode parity",
        original_H1_files_unchanged=True, non_OHLC_fields_including_volume_unchanged=True,
        cohort_and_natural_stops_unchanged=True, signals=300, held_hours=3576,
        prior_stage0_pass=False, financial_outcomes_computed=False, prices2024_2026_read=False)
    # The whole correction and cohort were validated before creating output.
    job.mkdir()
    atomic_json(job / "correction-card.json", card)
    books = deepcopy(original["h1_source_books"])
    for side in ("bid", "ask"):
        name = f"2022-gbpusd-{side}"
        target = job / (name + ".json")
        atomic_json(target, corrected_books[side])
        derived = job / (name + "-source-proof.json")
        atomic_json(derived, dict(original_book=source_pin(books[name]["book"]),
            original_proof=source_pin(books[name]["proof"]), correction_card=source_pin(job / "correction-card.json"),
            corrected_hours=list(HOURS), changed_fields=list(PRICE_KEYS),
            sourcePolicy="explicit_H1_plus_registered_two_hour_tick_OHLC",
            observedTickTimestamps=False, tick_timestamps_observed_only_at=list(HOURS),
            original_volume_retained_not_tick_volume=True, independent_feed_verified=False))
        books[name].update(book=str(target), proof=str(derived),
                           sourcePolicy="explicit_H1_plus_registered_two_hour_tick_OHLC")
        pins.extend((source_pin(target), source_pin(derived)))
    lineage = dict(card=source_pin(job / "correction-card.json"),
        original_registration=source_pin(original_job / "registration.json"),
        original_source_proof=source_pin(original_job / "source-proof.json"),
        original_manifest=source_pin(original_job / "manifest.json"),
        cohort_receipt=source_pin(review / "cohort-sensitivity/result.json"),
        corrected_hours=list(HOURS), financial_results_computed=False)
    result = deepcopy(original)
    result.update(schema="solo-gbp-source-v2-two-hour-correction", job_root=str(job),
        created_at_utc=datetime.now(timezone.utc).isoformat(), producer_commit=head,
        input_pins=pins + [source_pin(job / "correction-card.json")],
        producer_pins=original["producer_pins"] + producers,
        reused=reused, missing_hours=[], h1_source_books=books, source_correction=lineage,
        correction_network_budget=0)
    # Corrected books and their derived proofs are first-class pinned inputs.
    result["input_pins"].extend(source_pin(job / name) for name in
                                 ("2022-gbpusd-bid.json", "2022-gbpusd-bid-source-proof.json",
                                  "2022-gbpusd-ask.json", "2022-gbpusd-ask-source-proof.json"))
    result["input_pins"] = sorted(result["input_pins"], key=lambda item: item["path"])
    result["registration_sha256"] = canonical_digest(result)
    atomic_json(job / "registration.json", result)
    verify_pins(result)
    return result


def validate_v2_binding(job, registration, original_job=ORIGINAL):
    """Reject mutation and unrelated output paths before generic admission."""
    job = output_root(job)
    original_job = Path(original_job).resolve()
    if (job.name != "S01-gbp-confirmation-source-v2" or
            job.parent.resolve() != original_job.parent or
            Path(registration["job_root"]).resolve() != job.resolve()):
        raise ValueError("S01v2_registered_sibling_only")
    sealed = {key: value for key, value in registration.items() if key != "registration_sha256"}
    if registration.get("registration_sha256") != canonical_digest(sealed):
        raise ValueError("S01v2_registration_self_binding")
    if (len(registration.get("signals", [])) != 300 or
            len(registration.get("hours", [])) != 3576 or
            len(set(registration["hours"])) != 3576 or
            set(registration.get("reused", {})) != {str(at) for at in registration["hours"]}):
        raise ValueError("S01v2_exact_registered_cohort_required")
    for name in ("source", "ticks"):
        assert_plain_child(job, name)
        if (job / name).exists():
            raise ValueError("S01v2_admission_output_already_exists:" + name)
    verify_pins(registration)
    lineage = registration["source_correction"]
    expected_paths = {"original_registration": original_job / "registration.json",
        "original_source_proof": original_job / "source-proof.json",
        "original_manifest": original_job / "manifest.json",
        "card": job / "correction-card.json",
        "cohort_receipt": original_job / "source-discrepancy-review/cohort-sensitivity/result.json"}
    for key, path in expected_paths.items():
        if (Path(lineage[key]["path"]).resolve() != path.resolve() or
                digest(path) != lineage[key]["sha256"]):
            raise ValueError("S01v2_correction_lineage_changed:" + key)
    original = read(original_job / "registration.json")
    verify_pins(original)
    receipt = read(expected_paths["cohort_receipt"])
    verify_cohort(original, registration["signals"], receipt)
    if (registration["hours"] != original["hours"] or
            registration["cell"] != CELL or registration["prices2024_2026_read"] is not False or
            registration["prior_stage0_pass"] is not False or
            registration["prior_raw_edge_proven"] is not False or
            registration["source_budget"] != original["source_budget"] or
            registration["prior_stage0_annual"] != original["prior_stage0_annual"] or
            registration["correction_network_budget"] != 0):
        raise ValueError("S01v2_scope_or_history_changed")
    old_proof = read(expected_paths["original_source_proof"])
    if (old_proof["status"] != "SOURCE_REVIEW_REQUIRED" or old_proof["h1_difference_count"] != 4 or
            old_proof["registration_sha256"] != digest(expected_paths["original_registration"]) or
            old_proof["manifest_sha256"] != digest(expected_paths["original_manifest"])):
        raise ValueError("S01v2_original_proof_changed")
    expected_reuse = reuse_all(original, read(expected_paths["original_manifest"]),
                              read(original_job / "source/sealed-hours.json"), old_proof)
    if registration["reused"] != expected_reuse or registration["missing_hours"] != []:
        raise ValueError("S01v2_reuse_changed")
    card = read(expected_paths["card"])
    if (Path(card["original_job"]).resolve() != original_job or
            card["same_vendor"] is not True or card["independent_feed_verified"] is not False or
            card["FTMO_feed_verified"] is not False or card["signals"] != 300 or
            card["held_hours"] != 3576 or card["cohort_and_natural_stops_unchanged"] is not True):
        raise ValueError("S01v2_correction_card_changed")
    review = original_job / "source-discrepancy-review"
    verify_refetch_unknown(review)
    for side in ("bid", "ask"):
        if registration["h1_source_books"][f"2023-gbpusd-{side}"] != original["h1_source_books"][f"2023-gbpusd-{side}"]:
            raise ValueError("S01v2_2023_book_changed")
        name = f"2022-gbpusd-{side}"
        if Path(registration["h1_source_books"][name]["book"]).resolve() != (job / (name + ".json")).resolve():
            raise ValueError("S01v2_corrected_book_outside_job")
    return original


def admit(job=JOB):
    job = output_root(job)
    registration = read(job / "registration.json")
    if (registration.get("schema") != "solo-gbp-source-v2-two-hour-correction" or
            registration["source_correction"]["corrected_hours"] != list(HOURS) or
            registration["missing_hours"] != [] or len(registration["reused"]) != 3576):
        raise ValueError("S01v2_registered_correction_required")
    validate_v2_binding(job, registration)
    passed = admit_source(job)
    # Retain strict H1 matching; only new v2 output receives explicit lineage.
    proof = read(job / "source-proof.json")
    proof["registered_source_correction"] = registration["source_correction"]
    proof["independent_feed_verified"] = False
    proof["fresh_refetch_status"] = "UNKNOWN_HTTP202_EMPTY_FOUR_REQUESTS"
    atomic_json(job / "source-proof.json", proof)
    verify_pins(registration)
    atomic_json(job / "correction-admission-receipt.json", dict(
        source_proof=source_pin(job / "source-proof.json"),
        source_correction=registration["source_correction"], strict_H1_gate_unchanged=True,
        reconciled=passed, all_original_pins_unchanged=True, financial_results_computed=False))
    return passed


if __name__ == "__main__":
    import argparse
    import json
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("register", "admit"))
    args = parser.parse_args()
    if args.stage == "register":
        result = register()
        print(json.dumps({"registered": True, "signals": len(result["signals"]),
                          "reused_hours": len(result["reused"]), "missing_hours": 0}))
    else:
        passed = admit()
        print(json.dumps({"source_reconciled": passed, "job": str(JOB)}))
        raise SystemExit(0 if passed else 2)
