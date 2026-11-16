"""Descriptive comparison of frozen milestones, never a new strategy search."""
from collections import Counter
from datetime import datetime, timezone
import subprocess
from prop_v18_common import *
from prop_v15_campaign import metrics

REPORTS = [
    "PROP-QUALIFICATION-CAMPAIGN-RESULTS-20261114",
    "PROP-ATLAS-V2-RESULTS-20261114",
    "PROP-PORTFOLIO-V3-RESULTS-20261114",
    "PROP-COCORE-V4-RESULTS-20261114",
    "PROP-OVERNIGHT-V5-RESULTS-20261115",
    "PROP-V4-HARVEST-V6-RESULTS-20261115",
    "PROP-GOLD-V7-RESULTS-20261115",
    "PROP-GOLD-V8-RESULTS-20261115",
    "SYSTEM-AND-ALPHA-V9-RESULTS-20261115",
    "ENTERPRISE-ALPHA-V10-RESULTS-20261115",
    "ENSEMBLE-AND-STORAGE-V11-RESULTS-20261115",
    "SL-ACTIVE-ENSEMBLE-V12-RESULTS-20261115",
    "PATH-RESOLUTION-AND-DEDUP-V13-RESULTS-20261115",
    "EVIDENCE-AND-LIFECYCLE-V14-RESULTS-20261115",
    "BRIDGE-AND-VELOCITY-V15-RESULTS-20261115",
    "GAP-IMMUNE-MULTIASSET-V16-RESULTS-20261116",
    "ADAPTIVE-VELOCITY-V17-RESULTS-20261116"]


def source(version, tag):
    return (V14 / f"{tag}-A-NEXT_QUOTE-accounts.json" if version == "V14" else
            V15 / f"Full-{tag}-sizing-accounts.json" if version == "V15" else
            (V16 if version == "V16" else V17) / f"Full-{tag}-PRIMARY-accounts.json")


def run():
    history = []
    for i, name in enumerate(REPORTS, 1):
        p = Path("planning/research") / (name + ".json")
        r = read(p)
        history.append(dict(version=f"V{i}", report=str(p), sha256=sha(p),
                            decision=r.get("decision", r.get("verdict", r.get("challenge_readiness"))),
                            engineering_only=i in (9, 10),
                            prop_qualified=r.get("prop_qualified", False),
                            not_a_fresh_independent_trial=True))
    prs = []
    for n in (78, 82, 93, 94, 95, 96):
        prs.append(json.loads(subprocess.check_output([
            "gh", "pr", "view", str(n), "--repo", "Naqex/workspace",
            "--json", "number,title,state,mergeCommit,url"], text=True)))
    cases, bindings = [], []
    for version in ("V14", "V15", "V16", "V17"):
        for tag in ("OLHC", "OHLC"):
            p = source(version, tag)
            rows = read(p)
            if version == "V15":
                rows = [r for r in rows if r["profile"] == "CUSHION"]
            rows = [r for r in rows if r["kind"] in ("CHALLENGE", "STANDALONE_FULL")]
            bindings.append(dict(version=version, order=tag, path=str(p), sha256=sha(p)))
            for cost in ("SYM", "ASYM"):
                chosen = [r for r in rows if r["cell"].startswith(cost)]
                book = next(r for r in chosen if r["kind"] == "STANDALONE_FULL")
                m = metrics(chosen)
                if m["windows"] != 105:
                    raise ValueError("V18_comparison_denominator")
                cases.append(dict(version=version, order=tag, cost=cost, **m,
                                  standalone_static=book["static_loss_pct"],
                                  standalone_daily=book["worst_daily_loss_pct"],
                                  standalone_peak_DD=book["peak_dd_pct"]))
    ranking = []
    for version in ("V14", "V15", "V16", "V17"):
        rows = [r for r in cases if r["version"] == version]
        ranking.append(dict(
            version=version, worst_completions=min(r["funded"] for r in rows),
            slowest_median=max(r["median_months"] or float("inf") for r in rows),
            primary_breaches=max(r["breaches"] for r in rows),
            worst_standalone_static=max(r["standalone_static"] for r in rows),
            worst_standalone_daily=max(r["standalone_daily"] for r in rows),
            lowest_standalone_payout=min(r["standalone_payout"] for r in rows),
            certified_paths=False, source_gate="UNRESOLVED_SOURCE_GAPS_AND_CONDITIONAL_PATH_MODEL"))
    velocity = min([r for r in ranking if r["primary_breaches"] == 0],
                   key=lambda r: (-r["worst_completions"], r["slowest_median"], r["version"]))
    allowed = [r for r in ranking if r["primary_breaches"] == 0
               and r["worst_standalone_static"] < 6 and r["lowest_standalone_payout"] > 0]
    backup = min(allowed, key=lambda r: (r["worst_standalone_static"],
                 -r["lowest_standalone_payout"], r["version"])) if allowed else None
    if velocity["version"] != "V16":
        raise ValueError("V18_path_adapter_requires_selected_version:" + velocity["version"])
    trades = read(V16 / "Full-OLHC-PRIMARY-trades.json")
    annual = {}
    for t in trades:
        y = datetime.fromtimestamp(t["decision_msc"] / 1000, timezone.utc).year
        annual.setdefault(y, dict(trades=0, reference_SYM_R=0., source_unknown=0))
        annual[y]["trades"] += 1
        annual[y]["reference_SYM_R"] += t["reference"]["SYM"]["net_R"]
        annual[y]["source_unknown"] += t["source_uncertain"]
    dev = list(range(2018, 2024))
    favorable = sorted(dev, key=lambda y: (-annual[y]["reference_SYM_R"], y))[:2]
    sideways = sorted([y for y in dev if y not in favorable],
                      key=lambda y: (abs(annual[y]["reference_SYM_R"]), y))[:2]
    save("tournament.json", dict(
        schema="V18-descriptive-tournament-v1", history=history, PRs=prs, cases=cases,
        ranking=ranking, champion=None, ultra_safe_qualified=None,
        decision="NO_QUALIFIED_CHAMPION",
        diagnostic_velocity_reference=velocity, diagnostic_funded_backup=backup,
        old_3year_Gold_A=read(Path("planning/research/XAUUSD-A-HOLIDAY-VALIDATION-RESULTS-20261114.json"))["rolling_summary"],
        old_3year_V4=read(Path("planning/research/PROP-COCORE-V4-RESULTS-20261114.json"))["comparison"],
        raw_signal_annual=annual, bindings=bindings,
        full_exposed_history_descriptive_selection=True,
        bootstrap_regimes=dict(favorable_years=favorable, sideways_years=sideways,
                               future_regime_prediction=False)))
    event("V18_tournament_complete", diagnostic=velocity["version"],
          backup=backup["version"] if backup else None, qualified_champion=None)


if __name__ == "__main__":
    run()
