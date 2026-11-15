"""Finite Development selection, followed by one committed backward release."""
from collections import Counter
from statistics import median
import numpy as np
from prop_portfolio_accounts import quantity_steps, trade_money
from prop_campaign_source import signals as original
from prop_v7_accounts import AuditAccount
from prop_v8_common import *
from prop_v8_source import Calendar, prepare_source, readers
from prop_v8_signals import contexts, normalize, sweep, realize


def economics(trades, years, *, core=False, raw_counts=None):
    result = []
    for y in years:
        all_rows = [t for t in trades if t["day"].startswith(str(y))]
        allowed = [t for t in all_rows if t.get("qualifies") or not core and t.get("baseline")]
        for model in MODELS:
            budgets = {}
            for risk in (125, 150, 200):
                money, quantities, skipped = [], [], 0
                for t in allowed:
                    if t["reason"] in ("CENSORED", "ENDPOINT_UNKNOWN_OPEN"):
                        skipped += 1
                        continue
                    try:
                        q = quantity_steps(t, risk)
                    except ValueError:
                        skipped += 1
                        continue
                    money.append(trade_money(t, q, model, risk))
                    quantities.append(1 - q * t["natural_sl"] / risk)
                budgets[str(risk)] = dict(trades=len(money), unresolved_or_minlot=skipped,
                    net_R=sum(m["net_R"] for m in money),
                    mean_R=sum(m["net_R"] for m in money) / len(money) if money else None,
                    median_rounding_error_pct=100 * median(quantities) if quantities else None,
                    max_rounding_error_pct=100 * max(quantities) if quantities else None)
            raw = raw_counts.get(str(y), len(all_rows)) if raw_counts else len(all_rows)
            result.append(dict(year=y, model=model, raw=raw, normalized_before_cost=len(all_rows),
                cost_rejected=sum(t["friction_ratio"] > (.12 if core else .15) for t in all_rows),
                lot_scale_rejected=sum(t["natural_sl"] > 25 for t in all_rows) if core else 0,
                admitted=len(allowed), retained_pct=100 * len(allowed) / raw if raw else 0,
                median_sl=median([t["natural_sl"] for t in allowed]) if allowed else None,
                natural_median_sl=median([t["natural_sl"] for t in all_rows]) if all_rows else None,
                scale_ratio=median([t["friction"] for t in all_rows]) / median([t["natural_sl"] for t in all_rows]) if all_rows else None,
                endpoint_coverage_pct=100 * sum(t["reason"] not in ("CENSORED", "ENDPOINT_UNKNOWN_OPEN") for t in all_rows) / len(all_rows) if all_rows else 0,
                sides=dict(Counter(t["side"] for t in allowed)), budgets=budgets))
    return result


def gates(rows, core):
    reasons = []
    for a in rows:
        label = f"{a['year']}:{a['model']}"
        if a["endpoint_coverage_pct"] != 100:
            reasons.append(label + ":endpoint")
        if a["admitted"] < (40 if core else 20):
            reasons.append(label + ":cadence")
        if a["retained_pct"] < 50:
            reasons.append(label + ":retention")
        if a["raw"] == 0 or a["cost_rejected"] > a["raw"] / 2:
            reasons.append(label + ":cost_reject_majority")
        if a["scale_ratio"] is None or a["scale_ratio"] > (.12 if core else .15):
            reasons.append(label + ":natural_scale")
        if any(b["net_R"] <= 0 for b in a["budgets"].values()):
            reasons.append(label + ":economic")
        means = [b["mean_R"] for b in a["budgets"].values()]
        if core and (any(x is None for x in means) or max(means) - min(means) > .10):
            reasons.append(label + ":lot_invariance")
    return dict(eligible=not reasons, reasons=reasons)


def development():
    verify(dev=True)
    primary = ORDERS[0]
    prepare_source("dev", primary, START, DEV_END)
    folder = JOB / "dev" / primary
    hours = read(folder / "hours.json")
    cal = Calendar(read(CALENDAR), START, DEV_END)
    ctx = contexts(hours, START)
    ratios = [x["ratio"] for x in ctx.values() if x["ratio"] is not None]
    k = float(np.percentile(ratios, 85, method="linear"))
    raw = [dict(t, asset="XAUUSD") for t in read(ROOT / "prop-qualification-campaign-20261114/gold-dev-signals.json")
           if t["recipe"] == "A"]
    raw_counts = dict(Counter(r["day"][:4] for r in raw))
    reader = readers("dev", primary, START, DEV_END)["XAUUSD"]
    candidates = {}
    baseline, rejected = realize(raw, reader, cal, DEV_END, core=True)
    for t in baseline:
        t["qualifies"] = True
    candidates["BASELINE"] = dict(trades=baseline, economics=economics(baseline, (2022, 2023), core=True, raw_counts=raw_counts),
                                  rejected=rejected)
    for name in ("N1", "N2"):
        transformed, skipped = normalize(raw, ctx, name, k)
        trades, rejected = realize(transformed, reader, cal, DEV_END, core=True)
        rows = economics(trades, (2022, 2023), core=True, raw_counts=raw_counts)
        gate = gates(rows, True)
        candidates[name] = dict(trades=trades, economics=rows, gate=gate, normalization_skips=skipped, rejected=rejected)
    old_sweeps = read(ROOT / "prop-atlas-v2-20261114/atlas-XAUUSD-signals.json")
    sleeves = {}
    for cell in CELLS:
        rows = [t for t in old_sweeps if t["id"] == cell]
        ts, rejects = realize(rows, reader, cal, DEV_END)
        result = economics(ts, (2022, 2023), raw_counts=dict(Counter(r["day"][:4] for r in rows)))
        sleeves[cell] = dict(trades=ts, economics=result, gate=gates(result, False), rejected=rejects)
    def score(value):
        return min(a["budgets"]["150"]["net_R"] for a in value["economics"] if a["model"] == "SYM_FLAT")
    eligible = [name for name in ("N1", "N2") if candidates[name]["gate"]["eligible"]]
    chosen = max(eligible, key=lambda name: score(candidates[name])) if eligible else None
    selected_sleeves = [name for name in CELLS if sleeves[name]["gate"]["eligible"]]
    selected = max(selected_sleeves, key=lambda name: score(sleeves[name])) if chosen and selected_sleeves else None
    decision = dict(schema="V8-composition-v1", normalization=chosen, sleeve=selected,
        compression_k=k, compression_percentile=85, max_natural_sl=25, min_ounces_at125=5,
        core_friction_cap=.12, sleeve_friction_cap=.15, risk=[200,175,125], open_cap=800,
        reserve_floor=46000, core_priority=True, ratchet=False,
        dev_candidates={k: v["gate"] for k, v in candidates.items() if k != "BASELINE"},
        sleeve_candidates={k: v["gate"] for k, v in sleeves.items()},
        backward_status="LOCKED_UNTIL_COMMITTED_RELEASE_PRIOR_PROJECT_EXPOSURE",
        failed_candidate_not_tested_outside_dev=True,
        portfolio_alias_core=selected is None, control_only=chosen is None)
    write_json(folder / "candidates.json", candidates)
    write_json(folder / "sleeves.json", sleeves)
    write_json(JOB / "development.json", dict(decision=decision, candidates=candidates, sleeves=sleeves,
        ratio_calibration_days=len(ratios), no2018_2021_prices=True, no2024_2026_prices=True))
    write_json(DECISION, decision)
    event("V8_Dev_decision", normalization=chosen, sleeve=selected, k=k)


def temporary_bindings(module, values):
    """Redirect an existing runner's inputs/observer; restore all globals afterwards."""
    from contextlib import contextmanager
    @contextmanager
    def bound():
        old = {k: getattr(module, k) for k in values}
        try:
            for k, v in values.items():
                setattr(module, k, v)
            yield
        finally:
            for k, v in old.items():
                setattr(module, k, v)
    return bound()


def replay_accounts(trades, sources, accounts, calendar, first, end):
    import prop_v6_replay as engine
    with temporary_bindings(engine, {"event": event}):
        return engine.replay(trades, sources, accounts, end, calendar, first=first)


def make_accounts(first, end, systems):
    starts = []
    d = datetime.fromtimestamp(first / 1000, timezone.utc)
    while int(d.timestamp() * 1000) < end:
        if d.year == 2026 and d.month > 9:
            break
        starts.append(int(d.timestamp() * 1000))
        d = d.replace(year=d.year + 1, month=1) if d.month == 12 else d.replace(month=d.month + 1)
    years = range(year_of(first), year_of(end - 1) + 1)
    accounts = []
    for system in systems:
        for model in MODELS:
            for at in starts:
                a = AuditAccount(at, end, model, rolling=True, policy="GOLD_V4")
                a.v8_system = system
                accounts.append(a)
            for y in years:
                a = AuditAccount(stamp(f"{y}-01-01"), end, model, rolling=True, standalone=True, policy="GOLD_V4")
                a.v8_system = system
                accounts.append(a)
            for y in years:
                a = AuditAccount(stamp(f"{y}-01-01"), min(stamp(f"{y+1}-01-01"), end), model,
                                 fixed_risk=150, policy="GOLD_V4")
                a.v8_system = system
                accounts.append(a)
    return accounts


def year_of(at):
    return datetime.fromtimestamp(at / 1000, timezone.utc).year


class SystemAccount(AuditAccount):
    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "entry" and self.v8_system not in trades[i]["v8_systems"]:
            return
        return super().action(kind, at, i, trades, quote, mult)


def evaluate(tag, order):
    release = verify()
    backward = tag == "backward"
    first, end = (BACK_START, BACK_END) if backward else (START, END)
    source_first = stamp("2017-11-01") if backward else first
    prepare_source(tag, order, source_first, end, released=True)
    folder = JOB / tag / order
    hours = read(folder / "hours.json")
    calendar = Calendar(read(CALENDAR), source_first, end)
    sources = readers(tag, order, source_first, end)
    if backward:
        raw = [dict(r, asset="XAUUSD") for r in original(hours, first=first, end=end)
               if r["recipe"] == "A"]
    else:
        raw = [dict(t) for t in read(V7 / order / "system-trades.json") if t["asset"] == "XAUUSD"]
    decision = release["decision"]
    baseline, rejected = realize(raw, sources["XAUUSD"], calendar, end, core=True)
    for t in baseline:
        t["qualifies"] = True
        t["baseline"] = True
    systems = {"BASELINE": baseline}
    counts = dict(Counter(r["day"][:4] for r in raw))
    metrics = {"BASELINE": economics(baseline, range(year_of(first), year_of(end-1)+1), core=True, raw_counts=counts)}
    if decision["normalization"]:
        variant, skipped = normalize(raw, contexts(hours, first), decision["normalization"], decision["compression_k"])
        transformed, rejects = realize(variant, sources["XAUUSD"], calendar, end, core=True)
        systems["NORMALIZED"] = [t for t in transformed if t["qualifies"]]
        metrics["NORMALIZED"] = economics(transformed, range(year_of(first),year_of(end-1)+1), core=True, raw_counts=counts)
        write_json(folder / "normalization-rejections.json", dict(compression=skipped, missing=rejects))
        if decision["sleeve"]:
            cells = [s for s in sweep(hours, first, end, calendar) if s["id"] == decision["sleeve"]]
            if not backward:
                # Preserve exact pre-existing Development initialization.
                old = read(JOB / "development.json")["sleeves"][decision["sleeve"]]["trades"]
                old_raw = [dict(t) for t in old]
                cells = [r for r in cells if r["decision_msc"] >= DEV_END] + old_raw
            sleeve_trades, sleeve_rejected = realize(cells, sources["XAUUSD"], calendar, end)
            systems["PORTFOLIO"] = systems["NORMALIZED"] + [dict(t, role="SATELLITE") for t in sleeve_trades if t["qualifies"]]
            write_json(folder / "sleeve-rejections.json", sleeve_rejected)
    # Shared physical trade records keep one quote action even when systems reuse it.
    merged = {}
    for name, trades in systems.items():
        for t in trades:
            key = (t["entry_msc"], t["stop_units"], t["exit_msc"], t["side"], t.get("role", "CORE"))
            if key not in merged:
                merged[key] = dict(t, v8_systems=[])
            merged[key]["v8_systems"].append(name)
    trades = sorted(merged.values(), key=lambda t:(t["entry_msc"], t["role"] == "SATELLITE", t["stop_units"]))
    accounts = make_accounts(first, end, systems)
    for a in accounts:
        a.__class__ = SystemAccount
    rows = replay_accounts(trades, sources, accounts, calendar, first, end)
    for a, row in zip(accounts, rows):
        row["v8_system"] = a.v8_system
    write_json(folder / "system-trades.json", trades)
    write_json(folder / "accounts.json", rows)
    write_json(folder / "annual-economics.json", metrics)
    write_json(folder / "path-quality.json", dict(signals=len(raw), baseline_priced=len(baseline),
        unknown=[t["day"] for t in trades if t["reason"] == "ENDPOINT_UNKNOWN_OPEN"],
        end_open=[t["day"] for t in trades if t["reason"] == "CENSORED"], entry_rejected=rejected))
    event("V8_evaluation_complete", tag=tag, order=order, accounts=len(rows), systems=list(systems))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("development", "evaluate", "register", "release"))
    p.add_argument("--tag", choices=("full", "backward"), default="full")
    p.add_argument("--order", choices=ORDERS, default=ORDERS[0])
    a = p.parse_args()
    evaluate(a.tag, a.order) if a.stage == "evaluate" else globals()[a.stage]()
