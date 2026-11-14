"""V3 post-mortem and fixed-budget third-sleeve audit, no new price sources."""
from collections import Counter
import numpy as np
from prop_campaign_source import read, write_json
from prop_portfolio_scan import corr, metrics
from prop_portfolio_accounts import entry_exit_fee
from prop_cocore_v4 import JOB, V3, MODELS, event


def third_gate(cell, model, correlation_eur):
    reasons = []
    f = cell["funnel"]
    if not cell["source_path_complete"]:
        reasons.append("SOURCE_PATH_INCOMPLETE_OR_H1_ONLY")
    if cell["cell"]["asset"] == "US500" and cell["cell"]["horizon"] != "DAY":
        reasons.append("TARGET_DIVIDEND_CARRY_UNVERIFIED")
    for year in ("2022", "2023"):
        if f[year]["friction_pass_rate"] < .5:
            reasons.append(year + ":FRICTION_RETENTION_LT50")
        if f[year]["scale_ratio"] is None or f[year]["scale_ratio"] > .15:
            reasons.append(year + ":MEDIAN_FRICTION_SL_GT15")
    m = cell["models"][model]
    a, b = m["net_R"]["2022"], m["net_R"]["2023"]
    if a <= 0 or b <= 0 or a + b < 6:
        reasons.append("ECONOMIC_GATE")
    c = m["correlation"]["pooled"]
    if c is None or correlation_eur is None or max(c, correlation_eur) >= .25:
        reasons.append("DUAL_CORRELATION_GATE")
    return reasons


def audit():
    atlas = read(V3 / "satellite-decision.json")
    native = read(V3 / "final-satellite-decision.json")
    cells = {c["cell"]["id"]: c for c in atlas["cells"]}
    rows = []
    for rank, name in enumerate(atlas["top10"], 1):
        c = cells[name]
        details = {}
        for model in MODELS:
            n = native["comparison"][model]
            correlation = corr(c["models"][model]["daily"], n["sleeve"]["daily"])
            reasons = third_gate(c, model, correlation)
            if name in native["selected"]:
                reasons.append("EXISTING_COCORE_NOT_THIRD")
            with np.load(V3 / f"core-curve-{model}.npz") as p:
                core = [p[k] for k in ("close", "low", "high")]
            with np.load(V3 / f"native-curve-EURUSD.SWEEP.ASIA.LONDON.DAY-{model}.npz") as p:
                eur = [p[k] for k in ("small_close", "small_low", "small_high")]
            with np.load(V3 / f"curve-{name}-{model}.npz") as p:
                third = [p[k] for k in ("small_close", "small_low", "small_high")]
            baseline = metrics([a + b for a, b in zip(core, eur)])
            combined = metrics([a + b + d for a, b, d in zip(core, eur, third)])
            marginal = (combined["total_net_R"] > baseline["total_net_R"] and
                        combined["total_net_R"] / combined["max_R_DD"] >
                        baseline["total_net_R"] / baseline["max_R_DD"])
            if not marginal:
                reasons.append("MARGINAL_NET_DD_GATE")
            details[model] = dict(
                net_R=c["models"][model]["net_R"],
                correlation_gold=c["models"][model]["correlation"]["pooled"],
                correlation_eur=correlation, marginal_improvement=marginal,
                baseline_net_R=baseline["total_net_R"],
                portfolio_net_R=combined["total_net_R"],
                baseline_DD_R=baseline["max_R_DD"],
                portfolio_DD_R=combined["max_R_DD"], reasons=reasons)
        rows.append(dict(rank=rank, id=name, cell=c["cell"], funnel=c["funnel"],
                         models=details, eligible=all(not d["reasons"] for d in details.values())))
    selected = [r["id"] for r in rows if r["eligible"]][:1]
    write_json(JOB / "third-sleeve-audit.json", dict(
        top10=rows, selected=selected, only_development2022_2023=True,
        native_eur_rank=atlas["top10"].index(native["selected"][0]) + 1,
        notes="Source/scale gates retained; no new signal/horizon or source download."))
    event("third_sleeve_audit_complete", selected=selected)


def rejections(cases, trades, v4=False):
    out = {}
    for asset in ("XAUUSD", "EURUSD"):
        rejected = Counter()
        reduced = 0
        accepted = 0
        for c in cases:
            if v4:
                for a in c["entry_audit"]:
                    if a["asset"] == asset and not a["accepted"]:
                        rejected[a["reason"]] += 1
            for a in c["accepted"]:
                t = trades[a["trade"]]
                if t["asset"] != asset:
                    continue
                accepted += 1
                base = ((200, 175, 125) if v4 or asset == "XAUUSD" else (100, 100, 75))[a["phase"] - 1]
                reduced += a["risk_usd"] < base
            if not v4:
                # Archived V3 ledgers contain accepted decisions and aggregate
                # rejects. The reproduced V3 entry audit supplies asset reasons.
                pass
        out[asset] = dict(accepted=accepted, throttled=reduced,
                          rejected=dict(rejected))
    return out


def phase0():
    cases = read(V3 / "lifecycle-ASYM_FLAT-PORTFOLIO.json")
    p2 = [c for c in cases if len(c["phase_passes"]) == 1]
    funded = [c for c in cases if len(c["phase_passes"]) == 2]
    trades = read(V3 / "system-trades.json")
    cash_rows = []
    for c in funded:
        events = []
        for a in c["accepted"]:
            if a["phase"] == 3:
                t = trades[a["trade"]]
                events.append((a["at"], 1, -entry_exit_fee(t, t["entry_price_units"], a["ounces"]), 1))
        for x in c["closed"]:
            if x["phase"] == 3:
                t = trades[x["trade"]]
                a = next(a for a in c["accepted"] if a["trade"] == x["trade"])
                amount = int(round(x["net_usd"] * 1000)) + entry_exit_fee(
                    t, t["entry_price_units"], a["ounces"])
                events.append((x["at"], 0, amount, -1))
        balance = peak = 50000000
        active = 0
        first = min(a["at"] for a in c["accepted"] if a["phase"] == 3)
        flat_peaks = {14: None, 30: None}
        for at, _, amount, change in sorted(events):
            balance += amount
            active += change
            peak = max(peak, balance)
            for days in (14, 30):
                if not active and at >= first + days * 86400000:
                    flat_peaks[days] = max(flat_peaks[days] or -float("inf"), balance / 1000)
        if abs(balance / 1000 - c["balance_usd"]) > 1e-7:
            raise ValueError("funded_cash_diagnostic_bridge")
        cash_rows.append(dict(start=c["start_msc"], max_closed_balance_usd=peak / 1000,
                              flat_peak_after_days=flat_peaks,
                              final_balance_usd=balance / 1000))
    write_json(JOB / "v3-postmortem.json", dict(
        phase2_unfinished=len(p2), phase2_positive=sum(c["balance_usd"] > 50000 for c in p2),
        phase2_negative=sum(c["balance_usd"] < 50000 for c in p2),
        phase2_zero=sum(c["balance_usd"] == 50000 for c in p2),
        phase2_rows=[dict(start=c["start_msc"], balance_usd=c["balance_usd"],
                         breach=c["first_breach"], status=c["status"]) for c in p2],
        funded_cash=cash_rows, no_new_price_data=True))
    event("V3_archived_postmortem_complete", unfinished=len(p2),
          positive=sum(c["balance_usd"] > 50000 for c in p2))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("audit", "phase0"))
    globals()[p.parse_args().stage]()
