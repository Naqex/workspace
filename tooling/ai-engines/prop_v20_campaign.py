"""Same-source V20 Development, historical lifecycle and common-draw diagnostics."""
from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import time
import numpy as np
from prop_v20_common import *
from prop_v20_accounts import V20Account, FastV20Oracle
from prop_v19_campaign import Tape
from prop_v18_costs import cost_bindings
from prop_v18_bootstrap import draw_plan, sequence_for, MC_END, YEAR
from prop_v19_stress import summarize
from prop_v14_accounts import monthly_starts
from prop_v15_campaign import metrics
from quant_core.prop_lifecycle_and_parity import bindings


def audit(tape, sequence, row):
    import prop_v18_audit as previous
    with bindings(previous, FrictionOracle=FastV20Oracle):
        return previous.audit_path(tape, sequence, row)


def verify():
    frozen = read(FREEZE)
    import subprocess
    if json.loads(subprocess.check_output(["git", "show", "HEAD:" + FREEZE.as_posix()])) != frozen:
        raise ValueError("V20_freeze_not_committed")
    for name, digest in frozen["code_pins"].items():
        if sha(name) != digest:
            raise ValueError("V20_financial_code_changed:" + name)
    return frozen


def historical(tag, mode, pct, dev, preflight=False):
    if not dev:
        verify()
    tape = Tape(tag, mode, dev)
    end = DEV_END if dev else END
    profiles = read(JOB / "fit.json")["profiles"]
    starts = [(at, False) for at in monthly_starts(FIRST, end)] + [(FIRST, True)]
    if preflight:
        starts = starts[:1]
    prefix = ("preflight" if preflight else "Dev" if dev else "Full") + f"-{tag}-{mode}-{pct}"
    accounts, labels = [], []
    for p in profiles:
        for at, funded in starts:
            accounts.append(V20Account(at, end, "SYM_FLAT", rolling=True, standalone=funded,
                                       friction_pct=pct, profile=p))
            labels.append(dict(profile=p["name"], kind="STANDALONE_FULL" if funded else "CHALLENGE"))
    sequence = [(i, 0) for i in range(len(tape.blocks))]
    started = time.perf_counter()
    with cost_bindings(pct):
        for slot, (index, shift) in enumerate(sequence):
            tape.walk(index, shift, slot, accounts)
        rows = [dict(a.dump(), **label) for a, label in zip(accounts, labels)]
        save(prefix + "-accounts.json.gz", rows)
        checked = []
        for i, row in enumerate(rows):
            checked.append(audit(tape, sequence, row))
            if (i + 1) % 32 == 0:
                event("V20_historical_audit", case=prefix, done=i + 1, total=len(rows))
    parity = None
    if dev and not preflight:
        old = read(V19 / "O2-constraint-correction" / f"Dev-{tag}-{mode}-{pct}-accounts.json")
        old = [r for r in old if r["profile"] == "O2"]
        new = [r for r in rows if r["profile"] == "O2_UNSCALED"]
        ignored = {"profile", "policy", "V20_profile"}
        if len(old) != len(new) or any(
                {k: v for k, v in a.items() if k not in ignored} !=
                {k: v for k, v in b.items() if k not in ignored} for a, b in zip(old, new)):
            raise ValueError("V20_unscaled_O2_differs_from_V19")
        parity = dict(accounts=len(new), all_fields_equal_except_labels=True)
    summary = []
    for p in profiles:
        selected = [r for r in rows if r["profile"] == p["name"]]
        challenges = [r for r in selected if r["kind"] == "CHALLENGE"]
        waits = [next((v["at"] for v in r["phase_passes"] if v["phase"] == 2), end) - r["start_msc"]
                 for r in challenges]
        m = metrics(selected)
        summary.append(dict(profile=p["name"], **m,
            restricted_mean_months=float(np.mean(waits) / YEAR * 12),
            account_net_R_sum=sum(r["net_R"] for r in challenges),
            overlapping_start_net_R_not_additive_performance=True))
    save(prefix + "-audit.json", dict(passed=True, accounts=len(rows), checks=checked,
        source_sha256=sha(JOB / (prefix + "-accounts.json.gz")), V19_unscaled_parity=parity))
    save(prefix + "-summary.json", dict(cases=summary, accounts=len(rows),
        seconds=time.perf_counter() - started, all_full_ledgers_audited=True))
    event("V20_historical_complete", case=prefix, accounts=len(rows), seconds=time.perf_counter() - started)


def freeze():
    fit = read(JOB / "fit.json")
    cases = [r for tag in ("OLHC", "OHLC") for mode in ("PRIMARY", "STRICT") for pct in (100, 150)
             for r in read(JOB / f"Dev-{tag}-{mode}-{pct}-summary.json")["cases"]]
    ranking = [dict(profile=p, worst_static=max(r["worst_static"] for r in cases if r["profile"] == p["name"]),
                    worst_daily=max(r["worst_daily"] for r in cases if r["profile"] == p["name"]),
                    worst_completions=min(r["funded"] for r in cases if r["profile"] == p["name"]))
               for p in fit["profiles"]]
    names = [PROTOCOL, *sorted(Path("tooling/ai-engines").glob("prop_v20_*.py"))]
    value = dict(schema="V20-frozen-diagnostic-v1", fit=fit, profiles=fit["profiles"],
        Development=ranking, no_winner_selected_from_Validation=True,
        validation_already_exposed=True, prop_qualified=False,
        code_pins={str(p): sha(p) for p in names})
    with FREEZE.open("x", encoding="utf-8", newline="\n") as f:
        json.dump(value, f, indent=2)
    save("selection-freeze.json", value)
    event("V20_freeze_requires_commit", ranking=ranking)


def monte(tag, name, preflight=False):
    frozen = verify() if not preflight else dict(profiles=read(JOB / "fit.json")["profiles"])
    profile = next(p for p in frozen["profiles"] if p["name"] == name)
    tape = Tape(tag, "PRIMARY", dev=preflight)
    draws = draw_plan(tape)
    if not preflight and not np.array_equal(draws, np.load(V18 / "bootstrap-common-draws.npy")):
        raise ValueError("V20_common_draws_changed")
    label = ("preflight-MC" if preflight else "MC") + f"-{name}-{tag}"
    count = 2 if preflight else 5000
    binding = dict(profile=profile, count=count, pack_sha256=sha(V19 / ("Dev-pack" if preflight else "Full-pack") /
                    f"{tag}-PRIMARY-blocks.json"), producer_sha256=sha("tooling/ai-engines/prop_v20_accounts.py"),
                   worker_sha256=sha(__file__))
    if (JOB / (label + "-binding.json")).exists():
        if read(JOB / (label + "-binding.json")) != binding:
            raise ValueError("V20_resume_binding_changed")
    else:
        save(label + "-binding.json", binding)
    journal = JOB / (label + "-paths.jsonl")
    rows = [json.loads(v) for v in journal.read_text().splitlines()] if journal.exists() else []
    if [r["path"] for r in rows] != list(range(len(rows))):
        raise ValueError("V20_noncontiguous_MC_checkpoint")
    started = time.perf_counter()
    with journal.open("a", encoding="utf-8", newline="\n") as out, cost_bindings(100):
        for path in range(len(rows), count):
            sequence = sequence_for(tape, draws[path])
            accounts = [V20Account(FIRST, MC_END, "SYM_FLAT", rolling=True, standalone=funded,
                                   profile=profile, friction_pct=100) for funded in (False, True)]
            for slot, (index, shift) in enumerate(sequence):
                tape.walk(index, shift, slot, accounts)
            native = [a.dump() for a in accounts]
            try:
                checks = [audit(tape, sequence, r) for r in native]
            except Exception:
                save(label + f"-failed-{path}.json.gz", dict(native=native, sequence=sequence))
                raise
            c, f = native
            passes = {p["phase"]: p["at"] for p in c["phase_passes"]}
            r = dict(path=path, phase1=passes.get(1, -1), both=passes.get(2, -1), breach=c["first_breach"],
                funded_breach=f["first_breach"], daily=c["worst_daily_loss_pct"], static=c["static_loss_pct"],
                funded_payout_years=[sum(p["trader_usd"] for p in f["payouts"]
                    if FIRST + year * YEAR <= p["at"] < FIRST + (year + 1) * YEAR) for year in range(3)],
                post_challenge_payout_USD=c["trader_payout_usd"], independent_full_ledger_checks=checks,
                native_ledger_sha256=[hashlib.sha256(json.dumps(v, sort_keys=True).encode()).hexdigest() for v in native])
            out.write(json.dumps(r) + "\n"); out.flush(); rows.append(r)
            if (path + 1) % 100 == 0:
                event("V20_MC_progress", case=label, paths=path + 1, seconds=time.perf_counter() - started)
    save(label + "-summary.json", dict(**summarize(rows), profile=name, order=tag,
        mode="PRIMARY", friction=100, accounts_fully_audited=2 * len(rows),
        mean_post_challenge_payout_USD_per_elapsed_year=float(np.mean([r["post_challenge_payout_USD"] for r in rows])) / 3,
        worst_daily=max(r["daily"] for r in rows), worst_static=max(r["static"] for r in rows),
        journal_sha256=sha(journal), seconds=time.perf_counter() - started))
    event("V20_MC_complete", case=label, paths=count)


def localize():
    parent = read(Path("planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json"))
    affected = parent["gaps"]["affected"]
    totals = next(r for r in parent["reference_economics"] if
                  (r["version"], r["source"], r["friction"]) == ("V19", "PRIMARY", 100))["years"]
    strict = next(r for r in parent["reference_economics"] if
                  (r["version"], r["source"], r["friction"]) == ("V19", "STRICT", 100))["years"]
    rows = []
    for year in range(2018, 2027):
        trades = [t for t in affected if datetime.fromtimestamp(t["entry_msc"] / 1000, timezone.utc).year == year]
        total = totals[str(year)]["signals"]
        rows.append(dict(year=year, signals=total, unverified_trades=len(trades),
                         unverified_pct=100 * len(trades) / total, strict_net_R=strict[str(year)]["net_R"],
                         primary_net_R=totals[str(year)]["net_R"]))
    groups = [dict(period=label, signals=sum(r["signals"] for r in rows if lo <= r["year"] <= hi),
        unverified=sum(r["unverified_trades"] for r in rows if lo <= r["year"] <= hi),
        strict_net_R=sum(r["strict_net_R"] for r in rows if lo <= r["year"] <= hi),
        primary_net_R=sum(r["primary_net_R"] for r in rows if lo <= r["year"] <= hi))
        for label, lo, hi in (("2018-2021", 2018, 2021), ("2022-2026YTD", 2022, 2026))]
    assert sum(r["unverified_trades"] for r in rows) == 32
    assert sum(r["signals"] for r in rows) == 494
    save("gap-localization.json", dict(rows=rows, periods=groups, affected=affected,
         missing_occurrences=55, source_sha256=sha("planning/research/ASYMMETRIC-RECOVERY-V19-RESULTS-20261116.json"),
         no_price_data_read=True, no_cohort_selection=True, fixed_reference_risk_USD=150))
    event("V20_gap_localization", periods=groups)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser();p.add_argument("stage", choices=("historical", "freeze", "monte", "localize"))
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    p.add_argument("--friction", type=int, choices=(100, 150), default=100)
    p.add_argument("--dev", action="store_true");p.add_argument("--preflight", action="store_true")
    p.add_argument("--profile", default="O2_UNSCALED");a=p.parse_args()
    if a.stage == "historical":historical(a.tag,a.mode,a.friction,a.dev,a.preflight)
    elif a.stage == "monte":monte(a.tag,a.profile,a.preflight)
    elif a.stage == "freeze":freeze()
    else:localize()
