"""One registered exact-lot feasibility search; later data require committed freeze."""
from decimal import Decimal
import json
import subprocess
import time
import numpy as np
from prop_v26_common import *
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes
from prop_v25_risk import decide
import prop_v24_pareto as marked
from quant_core.discrete_sizing import quantity_grid, largest_feasible


def cents(value_R):
    return int(round(value_R * 15000))


def development():
    activate_runtime()
    sources = [PROTOCOL, Path(__file__), Path("tooling/ai-engines/quant_core/discrete_sizing.py"),
               Path("tooling/ai-engines/prop_v26_campaign.py"),
               Path("tooling/ai-engines/prop_v24_pareto.py"),
               Path("tooling/ai-engines/prop_v15_accounts.py"),
               Path("tooling/ai-engines/prop_v14_accounts.py")]
    sources += [Path("tooling/ai-engines/prop_v26_common.py"),
                Path("tooling/ai-engines/quant_core/job_workspace.py")]
    save("ISO-registration.json", dict(source={str(p):sha(p) for p in sources},
        head=subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip(),
        c_domain=[820000,831000],c_denominator=1_000_000,DD_cap_cents=183097,
        open_risk_cap_cents=31280,Development=[FIRST,DEV_END],later_opened=False))
    started = time.perf_counter()
    bars = {a:bars_for(a,True) for a in ("XAUUSD","EURUSD")}
    prepared, matrices = [], []
    ticks = np.arange(820000,831001,dtype=np.int64)
    for tag, order in (("OLHC","OPEN_LOW_HIGH_CLOSE"),("OHLC","OPEN_HIGH_LOW_CLOSE")):
        trades = read(V19/f"Dev-{tag}-PRIMARY-trades.json")
        assert all(FIRST <= t["entry_msc"] <= t["exit_msc"] < DEV_END for t in trades)
        readers = {a:M1ScenarioQuotes(b,order,FIRST,DEV_END) for a,b in bars.items()}
        points = marked.prepare(trades,readers)
        baseline = marked.measure(trades,points,{})
        assert abs(baseline["net_R"]-23.8524)<1e-8
        denominator = [marked.VALUE[t["asset"]]*abs(t["entry_price_units"]-t["stop_units"]) for t in trades]
        risk = [195000 if t["id"].split("|")[1].startswith("F5") else 105000 for t in trades]
        matrix = quantity_grid(ticks,denominator,risk)
        matrices.append(matrix)
        prepared.append((tag,trades,points,baseline))
    joined = np.concatenate(matrices,axis=1)

    def measure(tick,vector):
        rows, cursor = [], 0
        for tag,trades,points,baseline in prepared:
            values = vector[cursor:cursor+len(trades)]
            cursor += len(trades)
            # The frozen producer remains untouched: only its quantity provider is bound.
            by_key = {(t["id"],t["entry_msc"]):int(n) for t,n in zip(trades,values)}
            with bindings(marked,exact_quantity=lambda t,r:by_key[(t["id"],t["entry_msc"])]):
                metrics = marked.measure(trades,points,{})
            rows.append(dict(order=tag,candidate=metrics,baseline=baseline,
                equity_DD_cents=cents(metrics["equity_R_DD"]),
                max_open_risk_cents=int(round(metrics["max_open_risk_USD"]*100))))
        event("ISO_grid_vector",tick=tick,DD=[r["equity_DD_cents"] for r in rows])
        return rows

    accepts = lambda rows:all(r["equity_DD_cents"]<=183097 and r["max_open_risk_cents"]<=31280 for r in rows)
    result = largest_feasible(ticks,joined,measure,accepts)
    compressed("ISO-search",result)
    selected = result["selected"]
    cases = []
    if selected:
        for row in selected["metrics"]:
            check = decide(row["candidate"],row["baseline"])
            cases.append(dict(row,passed=check["passed"] and accepts([row]),reasons=check["reasons"]))
    passed = selected is not None and all(r["passed"] for r in cases)
    tick = result["tick"]
    weights = {k:float(Decimal(tick)/1_000_000*Decimal(str(v))) for k,v in marked.WEIGHTS.items()} if tick else None
    decision = dict(passed=passed,tick=tick,c_exact=tick/1_000_000 if tick else None,
        weights=weights,cases=cases,grid_points=result["grid_points"],
        unique_vectors=result["unique_vectors"],all_grid_plateaus_checked=True,
        monotonicity_assumed=False,seconds=time.perf_counter()-started,later_opened=False)
    save("ISO-Development-decision.json",decision)
    if passed:
        ids = sorted({t["id"] for t in prepared[0][1]})
        profile = dict(name="BASE_GUARD",gamma=None,weights={i:weights[i.split("|")[1][:2]] for i in ids})
        value = dict(schema="V26-ISO-freeze-v1",selected="P80_ISO_EXACT",profile=profile,
            weights=weights,tick=tick,sources={str(p):sha(p) for p in sources},
            decision_sha256=sha(JOB/"ISO-Development-decision.json"),
            later_history_already_exposed=True,later_prices_used_for_V26_selection=False,
            prop_qualified=False)
        with FREEZE.open("x",encoding="utf-8") as out:json.dump(value,out,indent=2)
    print(json.dumps(decision),flush=True)


def verify():
    value = read(FREEZE)
    assert value == json.loads(subprocess.check_output(["git","show","HEAD:"+FREEZE.as_posix()]))
    for path,digest in value["sources"].items():
        if sha(path)!=digest:raise ValueError("V26_FROZEN_SOURCE_CHANGED:"+path)
    if sha(JOB/"ISO-Development-decision.json")!=value["decision_sha256"]:
        raise ValueError("V26_DECISION_CHANGED")
    decision = read(JOB/"ISO-Development-decision.json")
    if decision["passed"] is not True or decision["weights"]!=value["weights"]:
        raise ValueError("V26_DEVELOPMENT_GATE_REQUIRED")
    return value


if __name__=="__main__":
    development()
