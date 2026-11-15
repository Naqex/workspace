"""Registered V12 Development path screen; no validation-price access."""
from pathlib import Path
from collections import Counter
from datetime import datetime, timezone
import json
import subprocess
import time
import numpy as np
from prop_campaign_source import ROOT
from prop_v10_source import FIRST, END, SEED, sha, sources
from prop_v11_campaign import us500_source_clock, us500_proxy
from prop_v12_signals import rejection_recipes
from quant_core.market_data_store import BAR
from quant_core.native_hourly_source import PairedHourlyStore, IndexedUs500Store
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.vectorized_stage0_scanner import measure, DAY
from quant_core.vectorized_sl_active_kernel import PathIndex, replay, daily_mtm
from quant_core.zero_tuning_ensemble import mechanical_composition, cumulative_drawdown

JOB = ROOT/"sl-active-ensemble-v12-20261115"
V10 = ROOT/"enterprise-alpha-v10-20261115"
V11 = ROOT/"ensemble-and-storage-v11-20261115"
ASSETS = ("XAUUSD", "EURUSD", "GBPUSD", "AUDUSD", "US500")


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def save(name, value):
    with (JOB/name).open("x", encoding="utf-8") as stream:
        json.dump(value, stream, ensure_ascii=False, indent=2)


def load_bars(asset, index):
    if asset in ("XAUUSD", "EURUSD"):
        p = read(V10/"source-admission.json")["assets"][asset]
        if sha(p["path"]) != p["binary_sha256"]:
            raise ValueError("V10_source_hash")
        return np.memmap(p["path"], dtype=BAR, mode="r")
    store = (IndexedUs500Store(index["minute_indices"][asset], SEED, END) if asset == "US500"
             else PairedHourlyStore(index["hourly_indices"][asset], SEED, END))
    return store.bars()


def old_measurement(archive, j, row):
    fields = ("at", "entry_at", "exit_at", "deadline", "side", "entry_price", "exit_price",
              "stop", "natural", "friction", "ratio", "ok", "admitted", "years")
    m = {k:archive[f"{j}:{k}"] for k in fields}
    m.update(asset=row["asset"], recipe=row["recipe"], family=row["family"], horizon=row["horizon"])
    # Cost admission is known at entry; an observed SL can resolve a formerly missing endpoint.
    m["admitted"] = m["ratio"] <= .15
    return m


def summarize(m, result, days):
    valid, admitted = result["valid"], result["valid"] & m["admitted"]
    years = m["years"]
    annual, economics, profiles = [], {}, {}
    for model in ("SYM", "ASYM"):
        v = result["model"][model]["net_R"]
        profiles[model] = daily_mtm(m["_index"], m, result, model, days)
        if not np.isclose(profiles[model].sum(), v[admitted].sum(), atol=1e-7):
            raise ValueError("daily_mtm_cash_conservation")
        order = np.argsort(result["exit_at"][admitted], kind="stable")
        cash = v[admitted][order]
        economics[model] = dict(raw_R=float(v[valid].sum()), net_R=float(v[admitted].sum()),
            mean_R=float(v[admitted].mean()) if admitted.any() else None,
            cash_R_DD=cumulative_drawdown(cash), daily_MTM_R_DD=cumulative_drawdown(profiles[model]))
    for y in range(2018, 2024):
        raw = years == y
        good, use = raw & valid, raw & admitted
        annual.append(dict(year=y, raw=int(raw.sum()), priced=int(good.sum()), admitted=int(use.sum()),
            path_unknown=int((raw & result["path_gap"]).sum()),
            models={model:dict(raw_R=float(result["model"][model]["net_R"][good].sum()),
                              net_R=float(result["model"][model]["net_R"][use].sum()))
                    for model in ("SYM", "ASYM")}))
    clusters, reasons = [], []
    for ys in ((2018, 2019, 2020), (2021, 2022, 2023)):
        raw = np.isin(years, ys)
        good, use = raw & valid, raw & admitted
        retention = float(use.sum()/raw.sum()) if raw.any() else 0.
        ratio = float(np.median(m["friction"][good])/np.median(m["natural"][good])) if good.any() else None
        net = {model:dict(raw=float(result["model"][model]["net_R"][good].sum()),
                          admitted=float(result["model"][model]["net_R"][use].sum()))
               for model in ("SYM", "ASYM")}
        clusters.append(dict(years=list(ys), raw=int(raw.sum()), priced=int(good.sum()),
                             admitted=int(use.sum()), retention=retention, scale_ratio=ratio, net=net))
        if retention < .5: reasons.append(f"{ys[0]}:RETENTION")
        if ratio is None or ratio > .15: reasons.append(f"{ys[0]}:SCALE")
        if min(net["SYM"].values()) <= 0: reasons.append(f"{ys[0]}:ECONOMIC")
    if not valid.all(): reasons.append("PATH_OR_ENDPOINT_INCOMPLETE")
    if economics["SYM"]["mean_R"] is None or economics["SYM"]["mean_R"] < .04:
        reasons.append("MEAN_BELOW004")
    identity = "|".join((m["asset"], m["recipe"], m["horizon"], result["mode"]))
    row = dict(id=identity, asset=m["asset"], family=m["family"], recipe=m["recipe"], horizon=m["horizon"],
        mode=result["mode"], annual=annual, clusters=clusters, economics=economics,
        raw=int(len(valid)), priced=int(valid.sum()), admitted=int(admitted.sum()),
        path_unknown=int(result["path_gap"].sum()), reasons=reasons, admitted_component=not reasons,
        dual_positive=all(c["net"]["SYM"]["raw"]>0 and c["retention"]>=.5 for c in clusters),
        exits=dict(Counter(result["reason"][admitted])), complete_path=bool(valid.all()))
    return row, profiles


def run():
    JOB.mkdir(exist_ok=True)
    start = time.perf_counter()
    old_atlas = read(V11/"clock-corrected/component-atlas.json")
    old0 = np.load(V10/"raw-matrix-reviewed.npz")
    old1 = np.load(V11/"clock-corrected/native-hourly-matrix.npz")
    index = read(V11/"source-admission-v11.json")
    protocol = Path("planning/research/SL-ACTIVE-ENSEMBLE-V12-PROTOCOL-20261115.md")
    code = [Path(__file__), Path(__file__).with_name("prop_v12_signals.py"),
            Path(__file__).with_name("independent_ledger_auditor.py"),
            Path(__file__).parent/"quant_core/vectorized_sl_active_kernel.py",
            Path(__file__).parent/"quant_core/zero_tuning_ensemble.py", protocol]
    save("registration.json", dict(commit=subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip(),
        code={str(p):sha(p) for p in code}, V11_atlas=sha(V11/"clock-corrected/component-atlas.json"),
        V10_matrix=sha(V10/"raw-matrix-reviewed.npz"), V11_matrix=sha(V11/"clock-corrected/native-hourly-matrix.npz"),
        trials=2888, validation_prices_opened=False, utc=datetime.now(timezone.utc).isoformat()))
    calendar = gold_calendar(FIRST, END)
    days = np.arange(FIRST//DAY, END//DAY)
    days = days[(days+3)%7 < 5]
    all_rows, components, all_profiles = [], [], {}
    timings, source_audits = {}, {}
    for asset in ASSETS:
        tick = time.perf_counter()
        print(dict(stage="load_source", asset=asset), flush=True)
        bars = load_bars(asset, index)
        path = PathIndex(bars, asset=asset, step=3600000 if asset in ("GBPUSD","AUDUSD") else 60000,
                         closed_days=[d for d,r in calendar.events.items() if r["kind"] == "CLOSED"])
        source_audits[asset] = path.audit
        prepared = time.perf_counter()
        measurements = []
        for j, row in enumerate(old_atlas["rows"]):
            if row["asset"] == asset:
                measurements.append(old_measurement(old0 if j < 544 else old1, j if j < 544 else j-544, row))
        extra = rejection_recipes(bars, asset, FIRST, END, calendar, native=asset in ("GBPUSD","AUDUSD"))
        for recipe in extra:
            ms = measure("XAUUSD" if asset == "US500" else "EURUSD" if asset in ("GBPUSD","AUDUSD") else asset,
                         recipe, bars, calendar, FIRST, END)
            if asset == "US500":
                ms = us500_proxy(us500_source_clock(ms, bars), bars)
            for m in ms:
                m["asset"] = asset;m["admitted"] = m["ratio"] <= .15
            measurements.extend(ms)
        f5_ready = time.perf_counter()
        packed, asset_rows, kernel_seconds, profile_seconds = {}, [], 0., 0.
        for j, m in enumerate(measurements):
            m["_index"] = path
            for key in ("at","entry_at","side","entry_price","stop","natural","friction","ratio","years","deadline","admitted"):
                packed[f"{j}:{key}"] = m[key]
            for mode in (("P0","P1","P2") if m["family"] == "F5" else ("P0","P1")):
                t = time.perf_counter();r = replay(path, m, mode);kernel_seconds += time.perf_counter()-t
                t = time.perf_counter();row, profiles = summarize(m, r, days);profile_seconds += time.perf_counter()-t
                row["source_cell"] = j
                asset_rows.append(row);all_rows.append(row);all_profiles[row["id"]] = profiles
                for field in ("valid","reason","exit_at","exit_price","path_gap","activation_index","protection_price"):
                    packed[f"{j}:{mode}:{field}"] = r[field]
                for model in ("SYM","ASYM"):
                    for field in ("gross","commission","slippage","funding","net","net_R"):
                        packed[f"{j}:{mode}:{model}:{field}"] = r["model"][model][field]
                if row["admitted_component"]:
                    components.append(dict(id=row["id"],asset=asset,family=m["family"],
                                           daily=profiles["SYM"],events=m["at"]))
            if j % 40 == 0:
                print(dict(stage="path_progress", asset=asset, cells=j, total=len(measurements)), flush=True)
        np.savez_compressed(JOB/f"{asset}-path-matrix.npz", **packed)
        save(f"{asset}-rows.json", asset_rows)
        timings[asset] = dict(load_and_index=prepared-tick, F5_signal=f5_ready-prepared,
            kernel=kernel_seconds, summarize_profiles=profile_seconds, total=time.perf_counter()-tick,
            base_cells=len(measurements)-24, F5_cells=24, path_cells=len(asset_rows))
        print(dict(stage="asset_complete",asset=asset,**timings[asset]),flush=True)
    if len(all_rows) != 2888:
        raise ValueError("V12_budget_changed")
    choice = mechanical_composition(components, correlation_limit=.25)
    selected = [next(r for r in all_rows if r["id"]==identity) for identity in choice["selected"]]
    profiles = {model:sum((all_profiles[r["id"]][model] for r in selected), np.zeros(len(days)))
                for model in ("SYM","ASYM")}
    annual = []
    for y in range(2018, 2024):
        mask = days.astype("datetime64[D]").astype("datetime64[Y]").astype(int)+1970 == y
        annual.append(dict(year=y, trades=sum(next(a["admitted"] for a in r["annual"] if a["year"]==y) for r in selected),
            models={model:dict(net_R=float(profiles[model][mask].sum()),
                              daily_MTM_R_DD=cumulative_drawdown(profiles[model][mask])) for model in profiles}))
    reasons = []
    if not 4 <= len(selected) <= 8: reasons.append("K_OUTSIDE4_8")
    if not (len({r["asset"] for r in selected}) >= 2 or
            any(r["family"]=="F5" for r in selected) and any(r["family"]!="F5" for r in selected)):
        reasons.append("NO_ASSET_OR_MECHANISM_DIVERSITY")
    for ys in ((2018,2019,2020),(2021,2022,2023)):
        if sum(a["trades"] for a in annual if a["year"] in ys) < 180:
            reasons.append(f"{ys[0]}:CADENCE_BELOW60")
        for model in profiles:
            for cohort in ("raw", "admitted"):
                total = sum(c["net"][model][cohort] for r in selected for c in r["clusters"] if c["years"][0]==ys[0])
                if total <= 0: reasons.append(f"{ys[0]}:{model}:{cohort}:CLUSTER_NONPOSITIVE")
    metrics = {}
    for model, values in profiles.items():
        yearly = [a["models"][model]["net_R"] for a in annual]
        metrics[model] = dict(net_R=float(values.sum()), daily_MTM_R_DD=cumulative_drawdown(values),
                             positive_years=sum(v>0 for v in yearly), ex_best_R=sum(yearly)-max(yearly,default=0))
        if metrics[model]["positive_years"] < 5: reasons.append(model+":FEWER_THAN5_POSITIVE_YEARS")
        if metrics[model]["ex_best_R"] <= 0: reasons.append(model+":EX_BEST_NONPOSITIVE")
    save("source-path-audit.json", source_audits)
    save("discovery.json", dict(rows=all_rows, selection=choice, trials=2888, timings=timings))
    decision = dict(passed=not reasons, reasons=reasons, selected=choice["selected"], K=len(selected),
        component_admitted=len(components), dual_positive=sum(r["dual_positive"] for r in all_rows),
        annual=annual, metrics=metrics, validation="CLOSED_PENDING_FREEZE_AND_ACCOUNT_ADMISSION" if not reasons else "CANCELED_FAILED_DEV_GATE",
        lifecycle="NOT_RUN", actual_account_replayed=False, clean_OOS=False)
    save("decision.json", decision)
    np.savez_compressed(JOB/"daily-profiles.npz", days=days,
        **{f"{i}:{model}":all_profiles[row["id"]][model] for i,row in enumerate(all_rows) for model in profiles})
    save("timings.json", dict(assets=timings, total=time.perf_counter()-start,
                              kernel_total=sum(t["kernel"] for t in timings.values())))
    print(dict(stage="V12_complete", **{k:v for k,v in decision.items() if k not in ("annual","metrics","selected")}),flush=True)


if __name__ == "__main__":
    run()
