"""Fixed descriptive diagnostics, not a new horizon or side-selection trial."""
from collections import Counter
from statistics import median
import numpy as np
from prop_portfolio_accounts import quantity_steps, trade_money
from prop_portfolio_scan import metrics
from prop_v7_common import *
from prop_v7_paths import readers


def med(rows):
    return median(rows) if rows else None


def describe(order):
    verify()
    folder = JOB / order
    trades = [t for t in read(folder / "system-trades.json") if t["asset"] == "XAUUSD"]
    source = readers(order)["XAUUSD"]
    h = read(V6 / "gold-seed-hours.json") + read(V6 / "gold-holdout-hours.json")
    hm = {r[0]: r for r in h if r[5] == 60}
    rows = []
    for i, t in enumerate(trades):
        day = t["decision_msc"] // DAY * DAY
        asia = [hm[day + j * HOUR] for j in range(6)]
        asian = (max(r[2] for r in asia) - min(r[3] for r in asia)) / 1000
        price = t["entry_price_units"] / 1000
        width = abs(t["entry_price_units"] - t["stop_units"]) / 1000
        atr = float(t["atr_h1_before_units"]) / 1000
        a, ordinal = source.path(t["entry_msc"], t["exit_msc"])
        px = a["b" if t["side"] == "BUY" else "a"]
        gross_r = (1 if t["side"] == "BUY" else -1) * (
            px.astype("float64") - t["entry_price_units"]) / (width * 1000)
        first_day = a["t"] <= t["entry_msc"] + 24 * HOUR
        second_day = ~first_day
        mfe = int(gross_r.argmax())
        limit = min(t["entry_msc"] + 24 * HOUR, t["exit_msc"])
        j = int(a["t"].searchsorted(limit))
        if j >= len(a) or a["t"][j] - limit > 60000:
            raise ValueError("V7_24h_diagnostic_mark_unknown:" + t["day"])
        money = {}
        q = None
        try:
            q = quantity_steps(t, 150)
        except ValueError:
            pass
        for model in MODELS:
            # UnitR is descriptive even when the $150 account cannot fit minlot.
            unit = trade_money(t, 1, model, width)
            final = trade_money(t, q, model, 150) if q else None
            at24 = dict(t, exit_msc=int(a["t"][j]), exit_price_units=int(px[j]))
            first = trade_money(at24, q, model, 150) if q else None
            money[model] = dict(
                unit_net_R=unit["net_R"], final=final, mark24=first,
                second_day_increment_R=final["net_R"] - first["net_R"] if q else None)
        rows.append(dict(
            day=t["day"], side=t["side"], entry_msc=t["entry_msc"], exit_msc=t["exit_msc"],
            reason=t["reason"], entry_price=price, asian_range=asian, natural_sl=width,
            ATR=atr, asian_price_pct=100 * asian / price, stop_price_pct=100 * width / price,
            stop_ATR=width / atr, asian_ATR=asian / atr, quantity_at150=q,
            budget_utilization_pct=100 * q * width / 150 if q else None,
            holding_hours=(t["exit_msc"] - t["entry_msc"]) / HOUR,
            has_second_day=bool(np.any(second_day)), mfe_R=float(gross_r[mfe]),
            mfe_elapsed_hours=(int(a["t"][mfe]) - t["entry_msc"]) / HOUR,
            mfe_day=1 if first_day[mfe] else 2,
            mfe_day1_R=float(gross_r[first_day].max()) if np.any(first_day) else None,
            mfe_day2_R=float(gross_r[second_day].max()) if np.any(second_day) else None,
            money=money))
        if i % 100 == 0:
            event("V7_Gold_forensics", order=order, trades=i, total=len(trades))
    annual = []
    for year in range(2022, 2027):
        rs = [r for r in rows if r["day"].startswith(str(year))]
        size_ok = [r for r in rs if r["quantity_at150"]]
        annual.append(dict(
            year=year, signals=len(rs), BUY=sum(r["side"] == "BUY" for r in rs),
            SELL=sum(r["side"] == "SELL" for r in rs), priced_exits=len(rs), exit_coverage_pct=100,
            minlot_rejected=len(rs) - len(size_ok),
            median_entry_price=med([r["entry_price"] for r in rs]),
            median_asian_range=med([r["asian_range"] for r in rs]),
            median_natural_sl=med([r["natural_sl"] for r in rs]),
            median_ATR=med([r["ATR"] for r in rs]),
            median_asian_price_pct=med([r["asian_price_pct"] for r in rs]),
            median_stop_price_pct=med([r["stop_price_pct"] for r in rs]),
            median_stop_ATR=med([r["stop_ATR"] for r in rs]),
            median_asian_ATR=med([r["asian_ATR"] for r in rs]),
            median_budget_utilization_pct=med([r["budget_utilization_pct"] for r in size_ok]),
            median_holding_hours=med([r["holding_hours"] for r in rs]),
            second_day_trades=sum(r["has_second_day"] for r in rs),
            MFE_day1_count=sum(r["mfe_day"] == 1 for r in rs),
            MFE_day2_count=sum(r["mfe_day"] == 2 for r in rs),
            median_MFE_R=med([r["mfe_R"] for r in rs]),
            reached_1R=sum(r["mfe_R"] >= 1 for r in rs),
            reached_2R=sum(r["mfe_R"] >= 2 for r in rs),
            models={model: dict(
                sides={side: dict(
                    priced_signals=sum(r["side"] == side for r in rs),
                    tradable_at150=sum(r["side"] == side for r in size_ok),
                    net_R=sum(r["money"][model]["final"]["net_R"] for r in size_ok if r["side"] == side),
                    unit_net_R=sum(r["money"][model]["unit_net_R"] for r in rs if r["side"] == side),
                    mark24_R=sum(r["money"][model]["mark24"]["net_R"] for r in size_ok if r["side"] == side),
                    day2_increment_R=sum(r["money"][model]["second_day_increment_R"] for r in size_ok if r["side"] == side))
                       for side in ("BUY", "SELL")},
                net_R=sum(r["money"][model]["final"]["net_R"] for r in size_ok),
                mean_net_R=sum(r["money"][model]["final"]["net_R"] for r in size_ok) / len(size_ok),
                gross_R=sum(r["money"][model]["final"]["gross_usd"] / 150 for r in size_ok),
                commission_R=sum(r["money"][model]["final"]["commission_usd"] / 150 for r in size_ok),
                slippage_R=sum(r["money"][model]["final"]["slippage_usd"] / 150 for r in size_ok),
                swap_R=sum(r["money"][model]["final"]["swap_usd"] / 150 for r in size_ok),
                mark24_R=sum(r["money"][model]["mark24"]["net_R"] for r in size_ok),
                day2_increment_R=sum(r["money"][model]["second_day_increment_R"] for r in size_ok))
                    for model in MODELS}))
    write_json(folder / "gold-forensics.json", dict(label=LABEL, reference_risk=150,
               MFE="favorable gross after entry spread, before commission/slippage/swap; live position path only",
               annual=annual, trades=rows))
    event("V7_Gold_forensics_complete", order=order, trades=len(rows))


def top10():
    """No new cells or outcomes; reuse the registered three Development curves."""
    audit = read(V3 / "satellite-decision.json")
    cells = {c["cell"]["id"]: c for c in audit["cells"]}
    names = [n for n in audit["top10"] if n.startswith("XAUUSD.")]
    result = []
    for name in names:
        c = cells[name]
        models = {}
        for model in MODELS:
            with np.load(V3 / f"core-curve-{model}.npz") as p:
                core = [p[k] for k in ("close", "low", "high")]
            with np.load(V3 / f"curve-{name}-{model}.npz") as p:
                sleeve = [p[k] for k in ("small_close", "small_low", "small_high")]
            a = metrics(core)
            b = metrics([u + v for u, v in zip(core, sleeve)])
            old = c["models"][model]
            models[model] = dict(
                own_full_budget_annual_net_R=old["net_R"],
                correlation_gold=old["correlation"]["pooled"],
                core_net_R=a["total_net_R"], core_DD_R=a["max_R_DD"],
                without_EUR_combined_net_R=b["total_net_R"],
                without_EUR_combined_DD_R=b["max_R_DD"],
                marginal_ratio_improved=b["total_net_R"] / b["max_R_DD"] > a["total_net_R"] / a["max_R_DD"],
                annual_positive=all(v > 0 for v in old["net_R"].values()))
        result.append(dict(rank=audit["top10"].index(name) + 1, id=name,
                           source_complete=c["source_path_complete"], funnel=c["funnel"], models=models))
    write_json(JOB / "top10-Gold-no-EUR-audit.json", dict(
        label="EXISTING_DEVELOPMENT_2022_2023_CURVES_ONLY", cells=result, new_trials=0,
        core_risk=150, extra_sleeve_risk=75, timeframe="existing H1 signal/M1 envelope screen",
        holdout_2024_2026_tested=False, active_sleeves_added=False,
        note="Same entries with three horizons; not three independent alphas or a new qualification."))
    event("V7_top10_Gold_reviewed", cells=len(result), new_trials=0)


def normalization(order):
    """Explain the two already-used budgets, without selecting another policy."""
    verify()
    fixed = [t for t in read(JOB / order / "system-trades.json")
             if t["asset"] == "XAUUSD" and t["day"].startswith("2025")]
    parent = [t for t in read(V6 / order / "holdout-trades.json")
              if t["asset"] == "XAUUSD" and t["day"].startswith("2025")]
    rows = []
    for model in MODELS:
        cases = {}
        for name, ts in (("V6_same_entries_old_calendar", parent),
                         ("V7_same_entries_fixed_calendar", fixed)):
            by_risk = {}
            for risk in (125, 150):
                money = [trade_money(t, quantity_steps(t, risk), model, risk) for t in ts]
                by_risk[str(risk)] = dict(
                    net_USD=sum(r["net_usd"] for r in money),
                    net_R=sum(r["net_R"] for r in money), signals=len(ts))
            cases[name] = by_risk
        changes = []
        for t in fixed:
            q125, q150 = quantity_steps(t, 125), quantity_steps(t, 150)
            m125, m150 = trade_money(t, q125, model, 125), trade_money(t, q150, model, 150)
            changes.append(dict(day=t["day"], side=t["side"], q125=q125, q150=q150,
                                net125=m125["net_usd"], net150=m150["net_usd"],
                                incremental_USD=m150["net_usd"] - m125["net_usd"]))
        rows.append(dict(
            model=model, cases=cases,
            calendar_delta_R_at125=cases["V7_same_entries_fixed_calendar"]["125"]["net_R"] -
                                    cases["V6_same_entries_old_calendar"]["125"]["net_R"],
            quantity_step_effects=changes, not_an_optimization=True))
    write_json(JOB / order / "2025-budget-normalization.json", dict(
        label=LABEL, risk125="existing V6 measurement/Funded budget",
        risk150="registered V7 annual reference and enhanced Funded budget",
        only_registered_budgets_compared=True, chosen_new_budget=None, models=rows))
    event("V7_2025_normalization_diagnosed", order=order)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("describe", "top10", "normalization"))
    p.add_argument("--order", default=ORDERS[0], choices=ORDERS)
    a = p.parse_args()
    top10() if a.stage == "top10" else globals()[a.stage](a.order)
