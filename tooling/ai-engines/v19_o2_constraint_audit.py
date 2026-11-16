"""Supplementary O2 contract correction, strictly Development-only fitting."""
from pathlib import Path
import json
import numpy as np
from prop_v19_common import *
from quant_core.asymmetric_covariance_optimizer import constrained_minimum_variance
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v19_campaign as campaign

FOLDER = JOB / "O2-constraint-correction"
PROTOCOL = Path("planning/research/V19-O2-CONSTRAINT-CORRECTION-20261116.md")


def write(name, value):
    FOLDER.mkdir(exist_ok=True)
    save("O2-constraint-correction/" + name, value)


def fit():
    from prop_v14_accounts import trade_money
    from prop_v15_accounts import exact_quantity
    parent = read(JOB / "Dev-fit.json")
    ids = parent["sleeves"]
    days = np.arange(np.datetime64("2018-01-01"), np.datetime64("2024-01-01"))
    days = days[np.is_busday(days)].astype("datetime64[ms]").astype("int64")
    x = np.zeros((len(days), 3))
    trades = read(V16 / "Dev-OLHC-PRIMARY-trades.json")
    for t in trades:
        if not FIRST <= t["decision_msc"] < DEV_END or t["exit_msc"] >= DEV_END:
            raise ValueError("O2_correction_Development_fence")
        at = int(days.searchsorted(t["exit_msc"] // 86400000 * 86400000))
        x[at, ids.index(t["id"])] += trade_money(t, exact_quantity(t, 150), "SYM_FLAT", 150)["net_usd"]
    result = constrained_minimum_variance(x)
    if not result["eligible"]:
        write("fit.json", dict(fit=result, profiles=[], Dev_only=True))
        return
    profiles = [dict(name=name, gamma=gamma, weights=dict(zip(ids, result["weights"])))
                for name, gamma in (("O2", None), ("O1_G035_O2", .35), ("O1_G050_O2", .5))]
    write("fit.json", dict(fit=result, profiles=profiles, sleeves=ids, Dev_only=True,
        current_source=sha(V16 / "Dev-OLHC-PRIMARY-trades.json"), earlier_heuristic=parent["O2"],
        protocol_sha256=sha(PROTOCOL), code_sha256=sha(__file__),
        optimizer_sha256=sha("tooling/ai-engines/quant_core/asymmetric_covariance_optimizer.py"),
        historical_Validation_already_exposed=True))
    event("V19_O2_constraint_fit", fit=result)


def historical(tag, mode, pct):
    fit = read(FOLDER / "fit.json")
    if not fit["profiles"]:
        return
    original_read = campaign.read
    original_job = campaign.JOB
    def supplied_read(path):
        if Path(path) == FOLDER / "Dev-fit.json":
            return fit
        return original_read(path)
    class OriginalDevTape(campaign.Tape):
        def __init__(self, tag, mode, dev=False):
            with bindings(campaign, JOB=original_job):
                super().__init__(tag, mode, True)
    with bindings(campaign, JOB=FOLDER, save=write, read=supplied_read, Tape=OriginalDevTape):
        campaign.historical(tag, mode, pct, True)


def decision():
    original = read(FREEZE)["ranking"]
    fit = read(FOLDER / "fit.json")
    ranking = []
    cases = []
    for tag in ("OLHC", "OHLC"):
        for mode in ("PRIMARY", "STRICT"):
            for pct in (100, 150):
                r = read(FOLDER / f"Dev-{tag}-{mode}-{pct}-summary.json")
                cases.extend(r["cases"])
    for profile in fit["profiles"]:
        rows = [r for r in cases if r["profile"] == profile["name"]]
        ranking.append(dict(profile=profile, worst_completions=min(r["funded"] for r in rows),
            slowest_restricted_months=max(r["restricted_mean_months"] for r in rows),
            lowest_standalone_payout=min(r["standalone_payout"] for r in rows),
            worst_daily=max(r["worst_daily"] for r in rows),
            worst_static=max(r["worst_static"] for r in rows), breaches=max(r["breaches"] for r in rows)))
    baseline = next(r for r in original if r["profile"]["name"] == "BASE_GUARD")
    approved = [r for r in ranking if r["breaches"] == 0 and
        (r["worst_completions"], -r["slowest_restricted_months"]) >
        (baseline["worst_completions"], -baseline["slowest_restricted_months"]) and
        r["worst_daily"] <= baseline["worst_daily"] and r["worst_static"] <= baseline["worst_static"]]
    selected = min(approved, key=lambda r: (-r["worst_completions"], r["slowest_restricted_months"],
                  -r["lowest_standalone_payout"], r["profile"]["name"])) if approved else baseline
    write("decision.json", dict(ranking=ranking, original_ranking=original,
        selected=selected, eligible_upgrade=bool(approved), fit_sha256=sha(FOLDER / "fit.json"),
        initial_heuristic_not_erased=True, Dev_only_selection=True,
        added_Development_cells=3, qualified_Champion=False,
        next_step="FREEZE_BEFORE_NEW_VALIDATION" if approved else "KEEP_FROZEN_BASE_GUARD"))
    event("V19_O2_constraint_decision", eligible=bool(approved), selected=selected["profile"]["name"])


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("fit", "historical", "decision"))
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    p.add_argument("--friction", type=int, choices=(100, 150), default=100)
    a = p.parse_args()
    if a.stage == "fit":
        fit()
    elif a.stage == "decision":
        decision()
    else:
        historical(a.tag, a.mode, a.friction)
