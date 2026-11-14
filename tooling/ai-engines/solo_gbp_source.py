"""S01 source-only registration and admission; no signal search or PnL writes."""
from datetime import datetime, timezone
from decimal import Decimal
import hashlib
import json
import os
from pathlib import Path
import subprocess

import numpy as np

from prop_atlas_source import decode_grid
from prop_campaign_source import DTYPE, START, END, HOUR, Prices
from prop_portfolio_scan import gap_unknown

WORKSPACE = Path(__file__).resolve().parents[2]
PARENT = Path("E:/BACKUP-TRADINGWORKSPACE/ai-engine-jobs/challenge-discovery4-20261108/execution-v1")
JOB = Path("E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S01-gbp-confirmation")
CELL = "GBPUSD.SWEEP.ASIA.LONDON.DAY"
PROTOCOL = "planning/research/SOLO-GBP-CONFIRMATION-PROTOCOL-20261115.md"
CODE = ("tooling/ai-engines/solo_gbp_source.py",
        "tooling/ai-engines/prepare_solo_gbp_source.cjs",
        "tooling/ai-engines/dukascopy_cached_m1.cjs",
        "tooling/ai-engines/prop_campaign_source.py",
        "tooling/ai-engines/prop_portfolio_scan.py",
        "tooling/ai-engines/prop_portfolio_sources.py",
        "tooling/ai-engines/prop_atlas_source.py",
        "tooling/ai-engines/index_tick_review.py",
        "tooling/ai-engines/candle_source_provenance.py")


def read(path):
    return json.loads(Path(path).read_bytes())


def digest(path):
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def atomic_json(path, value):
    path = Path(path)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False,
                                    allow_nan=False) + "\n", encoding="utf-8")
    os.replace(temporary, path)


def output_root(job, parent=PARENT):
    job = Path(job).absolute()
    if job == Path(parent).resolve() or job.resolve().is_relative_to(Path(parent).resolve()):
        raise ValueError("S01_parent_evidence_is_read_only")
    for path in (job, *job.parents):
        if path.exists():
            meta = path.lstat()
            if path.is_symlink() or getattr(meta, "st_file_attributes", 0) & 0x400:
                raise ValueError("S01_output_links_forbidden")
    return job


def census(rows):
    """Use all registered raw opportunities, including prior cost rejects."""
    signals, hours, seen = [], set(), set()
    for row in rows:
        at, end = row["decision_msc"], row["deadline_msc"]
        if (row["id"] != CELL or row["asset"] != "GBPUSD" or
                row["side"] not in ("BUY", "SELL") or
                type(at) is not int or type(end) is not int or
                not START <= at < end < END or at % HOUR):
            raise ValueError("S01_cohort_or_Development_scope")
        key = (at, row["side"])
        if key in seen:
            raise ValueError("S01_duplicate_opportunity")
        seen.add(key)
        signals.append({key: row[key] for key in
                        ("id", "asset", "side", "day", "decision_msc",
                         "stop_units", "deadline_msc", "deadline_kind")})
        hours.update(range(at, end // HOUR * HOUR + HOUR, HOUR))
    return signals, sorted(hours)


def source_pin(path):
    return {"path": str(Path(path).resolve()), "sha256": digest(path)}


def verify_pins(registration):
    for item in registration["input_pins"] + registration["producer_pins"]:
        if digest(item["path"]) != item["sha256"]:
            raise ValueError("S01_source_or_producer_changed:" + Path(item["path"]).name)


def register(job=JOB, parent=PARENT):
    job = output_root(job, parent)
    if (job / "registration.json").exists():
        previous = read(job / "registration.json")
        verify_pins(previous)
        if previous["job_root"] != str(job):
            raise ValueError("S01_registration_output_changed")
        return previous
    stage0 = parent / "prop-atlas-v2-20261114" / f"stage0-{CELL}.json"
    payload = read(stage0)
    signals, hours = census(payload["rows"])
    if len(signals) != 300 or len(hours) != 3576:
        raise ValueError("S01_inherited_census_changed")
    atlas = parent / "prop-atlas-v2-20261114"
    old_manifest = atlas / "GBPUSD-endpoint-manifest.json"
    old_seals = atlas / "missing-endpoint-source/sealed-hours.json"
    manifests = read(old_manifest)
    seals = {str(row["at"]): row for row in read(old_seals)
             if row["asset"] == "GBPUSD"}
    reused = {}
    for at in hours:
        key = str(at)
        if key in manifests:
            row = manifests[key]
            raw = seals[key]
            if digest(row["path"]) != row["sha256"] or digest(raw["rawPath"]) != raw["sha256"]:
                raise ValueError("S01_reusable_source_changed")
            reused[key] = dict(row, raw_path=raw["rawPath"], raw_sha256=raw["sha256"])
    if len(reused) != 292:
        raise ValueError("S01_inherited_reuse_census_changed")
    pins = [source_pin(p) for p in (stage0, old_manifest, old_seals)]
    h1 = {}
    history = parent / "fx-h1-history-v3"
    history_seals_path = history / "sealed-books.json"
    history_seals = read(history_seals_path)
    if isinstance(history_seals, dict):
        history_seals = history_seals.get("books", history_seals.get("seals", []))
    pins.append(source_pin(history_seals_path))
    for year in (2022, 2023):
        for side in ("bid", "ask"):
            name = f"{year}-gbpusd-{side}"
            book = history / (name + ".json")
            proof = history / (name + "-source-proof.json")
            expected = next(s for s in history_seals if s["book"] == name)
            if digest(book) != expected["sha256"] or digest(proof) != expected["sourceProofSha256"]:
                raise ValueError("S01_H1_source_seal_changed")
            detail = read(proof)
            if (detail["observedTickTimestamps"] is not False or
                    detail["sourcePolicy"] != "explicit_source_H1_only"):
                raise ValueError("S01_H1_semantics_changed")
            pins.extend((source_pin(book), source_pin(proof)))
            h1[name] = {"book": str(book), "proof": str(proof),
                        "observedTickTimestamps": False,
                        "sourcePolicy": detail["sourcePolicy"],
                        "selectedRows": detail["selectedRows"],
                        "unavailableSources": detail["unavailableSources"]}
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=WORKSPACE, text=True).strip()
    producer = []
    for relative in (*CODE, PROTOCOL):
        current = WORKSPACE / relative
        committed = subprocess.check_output(["git", "show", head + ":" + relative], cwd=WORKSPACE)
        if committed.replace(b"\r\n", b"\n") != current.read_bytes().replace(b"\r\n", b"\n"):
            raise ValueError("S01_commit_producer_before_source_launch:" + relative)
        producer.append(source_pin(current))
    package = WORKSPACE / ".runtime/research-data/node_modules/dukascopy-node"
    if read(package / "package.json")["version"] != "1.51.1":
        raise ValueError("S01_pinned_provider_version")
    producer.extend(source_pin(package / relative) for relative in ("package.json", "dist/index.js"))
    producer.append(source_pin(WORKSPACE / ".runtime/research-data/package-lock.json"))
    result = dict(schema="solo-gbp-source-v1", cell=CELL, job_root=str(job),
        created_at_utc=datetime.now(timezone.utc).isoformat(), producer_commit=head,
        window={"first": START, "end_exclusive": END}, signals=signals, hours=hours,
        reused=reused, missing_hours=[at for at in hours if str(at) not in reused],
        input_pins=pins, producer_pins=producer, h1_source_books=h1,
        prior_stage0_annual=payload["annual"], prior_stage0_pass=payload["stage0_pass"],
        prior_raw_edge_proven=False, new_financial_outcomes_computed=False,
        scope="one inherited SL-path confirmation; not an unconditional raw-edge pass",
        source_budget={"concurrency": 2, "pause_ms": 300, "transient_failures": 20,
                       "max_calls_per_url": 3, "deadline_seconds": 7200},
        prices2024_2026_read=False)
    job.mkdir(parents=True, exist_ok=True)
    with (job / "registration.json").open("x", encoding="utf-8") as output:
        json.dump(result, output, indent=2, ensure_ascii=False, allow_nan=False)
        output.write("\n")
    return result


def decoded_array(raw, at):
    if type(at) is not int or not START <= at < END or at % HOUR:
        raise ValueError("S01_tick_hour_outside_Development")
    ticks = decode_grid(raw, at, 100000)
    if len(ticks) != len(raw["times"]):
        raise ValueError("S01_out_of_hour_ticks_not_dropped")
    result = np.empty(len(ticks), dtype=DTYPE)
    result["t"], result["b"], result["a"] = ticks.timestamps, ticks.bid_units, ticks.ask_units
    if (len(result) and (np.any(result["a"] < result["b"]) or np.any(result["b"] <= 0)
                        or np.any(np.diff(result["t"]) < 0))):
        raise ValueError("S01_paired_tick_order_or_price")
    return result


def compare_h1(ticks, at, expected):
    differences = []
    for side, field in (("bid", "b"), ("ask", "a")):
        source = expected.get((at, side))
        actual = (None if not len(ticks) else
                  [int(ticks[field][0]), int(ticks[field].max()),
                   int(ticks[field].min()), int(ticks[field][-1])])
        if actual != source:
            differences.append(dict(at=at, side=side, h1_units=source,
                                    tick_units=actual, reason="source_hour_reconciliation"))
    return differences


def held_path_quality(signals, manifests):
    reader = Prices(manifests)
    issues = []
    for row in signals:
        entry = reader.endpoint(row["decision_msc"])
        exit_quote = reader.endpoint(row["deadline_msc"])
        if entry is None or exit_quote is None:
            issues.append(dict(day=row["day"], reason="ENTRY_OR_DEADLINE_QUOTE_UNKNOWN",
                               entry_known=entry is not None, deadline_known=exit_quote is not None))
            continue
        ticks, _ = reader.path(entry[0], exit_quote[0])
        gaps = gap_unknown(ticks["t"], 0, asset="GBPUSD")
        if gaps:
            issues.append(dict(day=row["day"], reason="HELD_GAP_GT15_MINUTES",
                               gaps=gaps))
    return issues


def admit(job=JOB):
    job = output_root(job)
    registration = read(job / "registration.json")
    verify_pins(registration)
    if registration["job_root"] != str(job):
        raise ValueError("S01_registration_output_changed")
    source = job / "source"
    downloaded = read(source / "sealed-hours.json") if (source / "sealed-hours.json").exists() else []
    seen = {}
    for item in downloaded:
        at = item["at"]
        if at in seen or at not in registration["missing_hours"]:
            raise ValueError("S01_source_census_or_duplicate")
        seen[at] = item
    missing = [at for at in registration["missing_hours"] if at not in seen]
    if missing:
        atomic_json(job / "source-proof.json", dict(status="SOURCE_INCOMPLETE",
            expected_hours=len(registration["hours"]), missing_hours=missing,
            new_financial_outcomes_computed=False))
        return False
    expected = {}
    for name, detail in registration["h1_source_books"].items():
        year, _, side = name.split("-")
        if year not in ("2022", "2023"):
            raise ValueError("S01_H1_price_window")
        for row in read(detail["book"]):
            at = row["timestamp"]
            if not START <= at < END:
                raise ValueError("S01_H1_price_window")
            expected[(at, side)] = [int(Decimal(str(row[k])) * 100000)
                                   for k in ("open", "high", "low", "close")]
    target = job / "ticks"
    target.mkdir(exist_ok=True)
    manifests, mismatches, empty, source_checks = {}, [], [], []
    for at in registration["hours"]:
        key = str(at)
        reused = registration["reused"].get(key)
        seal = reused or seen[at]
        raw_path = Path(seal["raw_path"])
        if not reused and not raw_path.resolve().is_relative_to(source.resolve()):
            raise ValueError("S01_new_raw_outside_owned_source_root")
        if digest(raw_path) != seal["raw_sha256"]:
            raise ValueError("S01_raw_source_changed")
        ticks = decoded_array(read(raw_path), at)
        if reused:
            path = Path(reused["path"])
            if digest(path) != reused["sha256"] or path.read_bytes() != ticks.tobytes():
                raise ValueError("S01_reused_binary_not_raw_equivalent")
        else:
            path = target / f"{at}.ticks"
            content = ticks.tobytes()
            if path.exists():
                if path.read_bytes() != content:
                    raise ValueError("S01_existing_binary_changed")
            else:
                with path.open("xb") as binary:
                    binary.write(content)
        if not len(ticks):
            empty.append(at)
        mismatches.extend(compare_h1(ticks, at, expected))
        manifests[key] = dict(path=str(path), records=len(ticks), sha256=digest(path))
        source_checks.append(dict(at=at, raw_sha256=seal["raw_sha256"],
                                  binary_sha256=manifests[key]["sha256"], reused=bool(reused)))
        if len(manifests) % 200 == 0:
            print(json.dumps({"stage": "S01_source_admission", "hours": len(manifests),
                              "total": len(registration["hours"])}), flush=True)
    atomic_json(job / "manifest.json", manifests)
    held_issues = held_path_quality(registration["signals"], manifests)
    atomic_json(job / "held-path-quality.json", dict(raw_signals=len(registration["signals"]),
        issues=held_issues, maximum_unregistered_gap_ms=15 * 60000,
        US500_maintenance_exception_applied=False, financial_results_computed=False))
    atomic_json(job / "h1-reconciliation.json", dict(mismatches=mismatches,
        empty_hours=empty, source_files_modified=False, prices2024_2026_read=False))
    status = ("SOURCE_RECONCILED" if not mismatches and not empty and not held_issues
              else "SOURCE_REVIEW_REQUIRED")
    atomic_json(job / "source-proof.json", dict(status=status,
        expected_hours=len(registration["hours"]), admitted_hours=len(manifests),
        paired_tick_records=sum(r["records"] for r in manifests.values()),
        h1_difference_count=len(mismatches), empty_hours=empty, source_checks=source_checks,
        held_path_issue_count=len(held_issues),
        registration_sha256=digest(job / "registration.json"),
        manifest_sha256=digest(job / "manifest.json"), same_ms_order_preserved=True,
        source_only=True, prop_qualified=False, new_financial_outcomes_computed=False,
        prior_stage0_pass=registration["prior_stage0_pass"], prices2024_2026_read=False))
    return status == "SOURCE_RECONCILED"


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("stage", choices=("register", "admit"))
    parser.add_argument("--job", type=Path, default=JOB)
    args = parser.parse_args()
    if args.stage == "register":
        packet = register(args.job)
        print(json.dumps({"registered": True, "signals": len(packet["signals"]),
                          "hours": len(packet["hours"]), "missing": len(packet["missing_hours"])}))
    else:
        passed = admit(args.job)
        print(json.dumps({"source_reconciled": passed, "proof": str(args.job / "source-proof.json")}))
        raise SystemExit(0 if passed else 2)
