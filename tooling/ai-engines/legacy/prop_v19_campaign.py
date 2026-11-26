"""Registered V19 Dev selection, full account audit and common-draw resampling."""
from collections import defaultdict
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import json
import subprocess
import time
import numpy as np
from prop_v19_common import *
from prop_v19_accounts import V19Account, V19LedgerOracle
from prop_v18_blocks import BlockTape
from prop_v18_costs import cost_bindings
from prop_v18_bootstrap import draw_plan, sequence_for, MC_END, YEAR
from prop_v15_campaign import metrics
from prop_v14_accounts import monthly_starts
from quant_core.prop_lifecycle_and_parity import bindings


def pack(tag, mode, dev):
    import prop_v18_blocks as previous
    from prop_v19_paths import load
    folder = JOB / ("Dev-pack" if dev else "Full-pack")
    folder.mkdir(exist_ok=True)
    with bindings(previous, JOB=folder, END=DEV_END if dev else END,
                  load=lambda tag, unused, strict: load(tag, dev, strict),
                  save=lambda name, value: save(folder.name + "/" + name, value), event=event):
        previous.export(tag, mode == "STRICT")


class Tape(BlockTape):
    def __init__(self, tag, mode, dev=False):
        folder = JOB / ("Dev-pack" if dev else "Full-pack")
        self.meta = read(folder / f"{tag}-{mode}-blocks.json")
        if sha(self.meta["quote_path"]) != self.meta["quote_sha256"]:
            raise ValueError("V19_quote_pack_hash")
        self.quotes = np.asarray(np.load(self.meta["quote_path"], mmap_mode="r"))
        self.blocks = self.meta["blocks"]


def fit():
    from prop_v14_accounts import trade_money
    from prop_v15_accounts import exact_quantity
    from quant_core.asymmetric_opportunity_optimizer import inverse_volatility_weights, volatility_drag
    trades = read(V16 / "Dev-OLHC-PRIMARY-trades.json")
    if any(not FIRST <= t["decision_msc"] < DEV_END or t["exit_msc"] >= DEV_END for t in trades):
        raise ValueError("V19_fit_Dev_fence")
    ids = sorted({t["id"] for t in trades})
    dates = np.arange(np.datetime64("2018-01-01"), np.datetime64("2024-01-01"))
    dates = dates[np.is_busday(dates)]
    days = dates.astype("datetime64[ms]").astype("int64")
    x = np.zeros((len(days), len(ids)))
    for t in trades:
        q = exact_quantity(t, 150)
        money = trade_money(t, q, "SYM_FLAT", 150)
        date = t["exit_msc"] // 86400000 * 86400000
        at = int(days.searchsorted(date))
        if at >= len(days) or days[at] != date:
            raise ValueError("V19_Dev_exit_on_non_session")
        x[at, ids.index(t["id"])] += money["net_usd"]
    fitted = inverse_volatility_weights(x)
    profiles = []
    for name in ("BASE_GUARD", "O1_G035", "O1_G050", "O2", "O1_G035_O2", "O1_G050_O2"):
        weighted = "O2" in name
        if weighted and not fitted["eligible"]:
            continue
        gamma = .35 if "G035" in name else .5 if "G050" in name else None
        values = fitted["weights"] if weighted else [1.] * len(ids)
        profiles.append(dict(name=name, gamma=gamma, weights=dict(zip(ids, values))))
    save("Dev-fit.json", dict(profiles=profiles, O2=fitted, sleeves=ids,
         sessions=len(days), mean_daily_USD=x.mean(axis=0).tolist(),
         volatility_drag=volatility_drag(x.sum(axis=1) / 50000),
         source=sha(V16 / "Dev-OLHC-PRIMARY-trades.json"), fit_end_exclusive=DEV_END,
         prices_2024_to_2026_used_for_fit=False))
    event("V19_Dev_fit", profiles=[p["name"] for p in profiles], O2=fitted)


def oracle(tape, sequence, expected):
    import prop_v18_audit as previous
    with bindings(previous, FrictionOracle=V19LedgerOracle):
        return previous.audit_path(tape, sequence, expected)


def audit_all(prefix, tape, sequence, rows, pct):
    binding = dict(accounts=sha(JOB / f"{prefix}-accounts.json"),
                   oracle=sha("tooling/ai-engines/prop_v19_accounts.py"),
                   adapter=sha("tooling/ai-engines/prop_v18_audit.py"))
    manifest = JOB / f"{prefix}-audit-binding.json"
    if manifest.exists():
        if read(manifest) != binding:
            raise ValueError("V19_changed_audit_binding_requires_new_attempt")
    else:
        save(manifest.name, binding)
    path = JOB / f"{prefix}-ledger-audits.jsonl"
    done = []
    if path.exists():
        done = [json.loads(v) for v in path.read_text().splitlines()]
        if [r["row"] for r in done] != list(range(len(done))):
            raise ValueError("V19_audit_checkpoint_order")
    started = time.perf_counter()
    with path.open("a", encoding="utf-8") as f, cost_bindings(pct):
        for i in range(len(done), len(rows)):
            r = dict(row=i, **oracle(tape, sequence, rows[i]))
            f.write(json.dumps(r) + "\n")
            f.flush()
            if (i + 1) % 16 == 0:
                event("V19_historical_oracle_progress", case=prefix, done=i + 1,
                      total=len(rows), seconds=time.perf_counter() - started)
    save(f"{prefix}-audit.json", dict(passed=True, accounts=len(rows),
         independent_full_ledgers=len(rows), native_cash_bridges=len(rows),
         same_author_and_feed=True, journal_sha256=sha(path), binding=binding,
         seconds_this_attempt=time.perf_counter() - started))


def historical(tag, mode, pct, dev, *, preflight=False):
    started = time.perf_counter()
    tape = Tape(tag, mode, dev)
    end = DEV_END if dev else END
    profiles = read(JOB / "Dev-fit.json")["profiles"] if dev else [read(FREEZE)["selected_profile"]]
    starts = [(at, False) for at in monthly_starts(FIRST, end)] + [(FIRST, True)]
    if preflight:
        profiles, starts = profiles[:1], starts[:1]
    prefix = ("preflight" if preflight else "Dev" if dev else "Full") + f"-{tag}-{mode}-{pct}"
    cache = JOB / f"{prefix}-accounts.json"
    sequence = [(i, 0) for i in range(len(tape.blocks))]
    if cache.exists():
        rows = read(cache)
    else:
        accounts, labels = [], []
        for p in profiles:
            for at, funded in starts:
                accounts.append(V19Account(at, end, "SYM_FLAT", rolling=True,
                    standalone=funded, profile=p, friction_pct=pct))
                labels.append(dict(profile=p["name"], kind="STANDALONE_FULL" if funded else "CHALLENGE"))
        with cost_bindings(pct):
            for slot, (index, shift) in enumerate(sequence):
                tape.walk(index, shift, slot, accounts)
            rows = [dict(a.dump(), **label) for a, label in zip(accounts, labels)]
        save(cache.name, rows)
        event("V19_historical_native", case=prefix, accounts=len(rows), seconds=time.perf_counter() - started)
    audit_all(prefix, tape, sequence, rows, pct)
    summary = []
    for p in profiles:
        selected = [r for r in rows if r["profile"] == p["name"]]
        m = metrics(selected)
        challenges = [r for r in selected if r["kind"] == "CHALLENGE"]
        waits = [next((x["at"] for x in r["phase_passes"] if x["phase"] == 2), end) - r["start_msc"]
                 for r in challenges]
        m["restricted_mean_months"] = float(np.mean(waits) / YEAR * 12)
        summary.append(dict(profile=p["name"], **m))
    save(f"{prefix}-summary.json", dict(cases=summary, accounts=len(rows),
         all_independent_audited=True, seconds=time.perf_counter() - started))
    event("V19_historical_complete", case=prefix, results=summary,
          seconds=time.perf_counter() - started)


def select():
    fitted = read(JOB / "Dev-fit.json")
    rows = []
    bindings_found = {}
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            for pct in (100, 150):
                name = f"Dev-{tag}-{mode}-{pct}-summary.json"
                rows.extend(read(JOB / name)["cases"])
                bindings_found[name] = sha(JOB / name)
    ranking = []
    for p in fitted["profiles"]:
        cases = [r for r in rows if r["profile"] == p["name"]]
        if len(cases) != 8:
            raise ValueError("V19_incomplete_Dev_selection")
        ranking.append(dict(profile=p, worst_completions=min(r["funded"] for r in cases),
            slowest_restricted_months=max(r["restricted_mean_months"] for r in cases),
            lowest_standalone_payout=min(r["standalone_payout"] for r in cases),
            worst_daily=max(r["worst_daily"] for r in cases),
            worst_static=max(r["worst_static"] for r in cases),
            breaches=max(r["breaches"] for r in cases)))
    safe = [r for r in ranking if r["breaches"] == 0]
    best = min(safe, key=lambda r: (-r["worst_completions"], r["slowest_restricted_months"],
                                   -r["lowest_standalone_payout"], r["profile"]["name"]))
    baseline = next(r for r in ranking if r["profile"]["name"] == "BASE_GUARD")
    promotes = ((best["worst_completions"], -best["slowest_restricted_months"]) >
                (baseline["worst_completions"], -baseline["slowest_restricted_months"])
                and best["worst_daily"] <= baseline["worst_daily"]
                and best["worst_static"] <= baseline["worst_static"])
    # Keep a diagnostic selection even when improvement or source gate fails.
    files = [PROTOCOL, *sorted(Path("tooling/ai-engines").glob("prop_v19_*.py")),
             Path("tooling/ai-engines/quant_core/asymmetric_opportunity_optimizer.py")]
    frozen = dict(schema="V19-Dev-selection-v1", selected_profile=best["profile"],
        eligible_risk_improvement=promotes, prop_qualified=False, ranking=ranking,
        Dev_bindings=bindings_found, fit_sha256=sha(JOB / "Dev-fit.json"),
        code_pins={str(p): sha(p) for p in files}, seed=SEED, paths=PATHS,
        validation_already_exposed=True, no_Validation_outcome_selection=True)
    with FREEZE.open("x", encoding="utf-8") as f:
        json.dump(frozen, f, indent=2, ensure_ascii=False)
    save("selection-freeze.json", frozen)
    event("V19_selection_needs_commit", profile=best["profile"]["name"], eligible=promotes)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("pack", "fit", "preflight", "historical", "select"))
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    p.add_argument("--friction", type=int, choices=(100, 150), default=100)
    p.add_argument("--full", action="store_true")
    a = p.parse_args()
    if a.stage == "fit":
        fit()
    elif a.stage == "pack":
        pack(a.tag, a.mode, not a.full)
    elif a.stage == "select":
        select()
    else:
        historical(a.tag, a.mode, a.friction, not a.full, preflight=a.stage == "preflight")
