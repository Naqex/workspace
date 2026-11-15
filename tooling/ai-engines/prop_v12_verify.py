"""Independent accepted-source decoding, Decimal cash audit and scalar path witnesses."""
from pathlib import Path
from decimal import Decimal
import hashlib
import json
import time
import subprocess
import numpy as np
import independent_ledger_auditor as oracle
from prop_campaign_source import ROOT

JOB = ROOT/"sl-active-ensemble-v12-20261115"
OLD = ROOT/"ensemble-and-storage-v11-20261115"
V10 = ROOT/"enterprise-alpha-v10-20261115"
DAY, HOUR = 86400000, 3600000
FIRST, END, SEED = 1514764800000, 1704067200000, 1509494400000
DTYPE = np.dtype([("t","<i8")]+[(f+s,"<i4") for f in ("b","a") for s in ("o","h","l","c")])


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def sha(p):
    with Path(p).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def decoded_file(path, digest, side, scale):
    if sha(path) != digest:
        raise ValueError("independent_source_hash")
    data = json.loads(Path(path).read_bytes(), parse_float=Decimal)
    if isinstance(data, dict):
        data = data.get("rows", data.get("data", []))
    values = [r for r in data if SEED <= r["timestamp"] < END]
    out = np.zeros(len(values), dtype=DTYPE)
    for j, r in enumerate(values):
        out["t"][j] = r["timestamp"]
        for f, name in zip(("o","h","l","c"), ("open","high","low","close")):
            value = Decimal(str(r[name]))*scale
            assert value == int(value)
            out[side+f][j] = int(value)
    return out


def original_input(asset, index):
    if asset in ("XAUUSD", "EURUSD"):
        p = read(V10/"source-admission.json")["assets"][asset]
        assert sha(p["path"]) == p["binary_sha256"]
        # Own schema; no producer loader, resampling, cost or execution imports.
        return np.memmap(p["path"], dtype=DTYPE, mode="r")
    if asset in ("GBPUSD","AUDUSD"):
        by_side = {}
        for side in ("bid","ask"):
            pieces = [decoded_file(r["path"],r["sha256"],side[0],100000)
                      for r in index["hourly_indices"][asset]["books"] if r["side"] == side]
            by_side[side] = np.concatenate(pieces)
        bid, ask = by_side["bid"], by_side["ask"]
        assert np.array_equal(bid["t"],ask["t"])
        for f in ("o","h","l","c"):
            bid["a"+f] = ask["a"+f]
        return bid
    pieces = []
    for year in index["minute_indices"][asset]["years"]:
        assert 2017 <= year["year"] <= 2023
        root = Path(year["root"])
        assert sha(root/"source-observation-proof.json") == year["proof_sha256"]
        proof = read(root/"source-observation-proof.json")
        for q in range(1,5):
            sides = {}
            for side in ("bid","ask"):
                request = f"q{q}-{side}"
                seal = next(r for r in proof["output_seals"] if r["request"] == request)
                sides[side] = decoded_file(root/(request+".json"),seal["sha256"],side[0],1000)
            bid, ask = sides["bid"], sides["ask"]
            _, b, a = np.intersect1d(bid["t"],ask["t"],return_indices=True)
            joined = bid[b].copy()
            for f in ("o","h","l","c"):
                joined["a"+f] = ask["a"+f][a]
            pieces.append(joined)
    return np.concatenate(pieces)


def ledger_row(row, arrays, i, asset, mode, model):
    j = row["source_cell"];prefix = f"{j}:{mode}:"
    scale = 1000 if asset in ("XAUUSD","US500") else 100000
    quote = lambda v: str(Decimal(int(v))/Decimal(scale))
    activation = int(arrays[prefix+"activation_index"][i])
    return dict(symbol=asset,direction="BUY" if arrays[f"{j}:side"][i] == 1 else "SELL",
        entry_time=int(arrays[f"{j}:entry_at"][i]),entry_price=quote(arrays[f"{j}:entry_price"][i]),
        sl_price=quote(arrays[f"{j}:stop"][i]),exit_time=int(arrays[prefix+"exit_at"][i]),
        exit_price=quote(arrays[prefix+"exit_price"][i]),lots="1",reason=str(arrays[prefix+"reason"][i]),
        mode=mode,horizon=row["horizon"],cost_model=model,activation_index=activation)


def run():
    start = time.perf_counter()
    discovery = read(JOB/"discovery.json")
    old = read(OLD/"clock-corrected/component-atlas.json")
    index = read(OLD/"source-admission-v11.json")
    # Deterministic reviewed calendar input, not a producer deadline helper.
    calendar = read("planning/research/PROP-V8-SESSION-CALENDAR-20261115.json")
    events = {r["day"]:r for r in calendar["events"]}
    events["2021-12-31"].update(kind="NORMAL",flat_utc=None)
    flats = []
    from datetime import datetime,timezone,timedelta
    day = datetime(2017,11,1,tzinfo=timezone.utc)
    while day.year < 2025:
        base = int(day.timestamp()*1000)
        if day.weekday() == 4:
            flats.append(base+int(20.5*HOUR))
        event = events.get(day.date().isoformat(),{})
        if event.get("flat_utc"):
            h,m = map(int,event["flat_utc"].split(":"));flats.append(base+h*HOUR+m*60000)
        day += timedelta(days=1)
    old_six = set(old["decision"]["selected"])
    cash_records, path_records, max_precent_error = 0,0,0.
    samples, failures, by_asset = [], [], {}
    for asset in ("XAUUSD","EURUSD","GBPUSD","AUDUSD","US500"):
        print(dict(stage="oracle_source",asset=asset),flush=True)
        bars = original_input(asset,index)
        arrays = np.load(JOB/f"{asset}-path-matrix.npz")
        spec = dict(contract=100 if asset=="XAUUSD" else 1 if asset=="US500" else 100000,
                    scale=1000 if asset in ("XAUUSD","US500") else 100000,
                    step=HOUR if asset in ("GBPUSD","AUDUSD") else 60000,
                    closed_days=[d for d,r in events.items() if r["kind"]=="CLOSED"])
        local_cash, local_paths = 0,0
        for row in discovery["rows"]:
            if row["asset"] != asset:
                continue
            j,mode = row["source_cell"],row["mode"];prefix = f"{j}:{mode}:"
            names = [f"{j}:{k}" for k in ("side","entry_at","entry_price","stop")]
            names += [prefix+k for k in ("valid","activation_index","exit_at","exit_price","reason")]
            names += [prefix+model+":"+field for model in ("SYM","ASYM")
                      for field in ("gross","commission","slippage","funding","net")]
            data = {name:arrays[name] for name in names}
            use = np.flatnonzero(data[prefix+"valid"])
            detailed = set(map(int,use[::max(1,len(use)//2)])) if len(use) else set()
            if row["id"].rsplit("|",1)[0] in old_six:
                detailed = set(map(int,use))
            for i in use:
                trade = ledger_row(row,data,i,asset,mode,"SYM")
                activation = trade.pop("activation_index")
                if activation >= 0:
                    trade["protection_time"] = int(bars["t"][activation])+spec["step"]
                for model in ("SYM","ASYM"):
                    trade["cost_model"] = model
                    value = oracle.cash_legs(trade,model,spec)
                    for a,b in (("gross","gross"),("commission","commission"),("slippage","slippage"),
                                ("funding","swap"),("net","net")):
                        produced = float(data[prefix+model+":"+a][i])*spec["contract"]
                        # Restore floating representation noise before the cent boundary.
                        actual = oracle.cent(round(produced,8))
                        if actual != value[b]:
                            failures.append(dict(id=row["id"],i=int(i),field=a,model=model,
                                                 produced=str(actual),oracle=str(value[b])))
                    local_cash += 1
                if int(i) in detailed:
                    result = oracle.audit_trade(trade,(bars["t"],bars),spec,flats)
                    if not result["passed"]:
                        failures.append(dict(id=row["id"],i=int(i),errors=result["errors"]))
                    local_paths += 1
                    if len(samples) < 50:
                        samples.append(dict(id=row["id"],i=int(i),**trade))
        cash_records += local_cash;path_records += local_paths
        by_asset[asset] = dict(cash_cost_views=local_cash,scalar_path_checks=local_paths,
                              independently_decoded_rows=len(bars))
        print(dict(stage="oracle_asset_complete",asset=asset,**by_asset[asset],failures=len(failures)),flush=True)
    out = dict(passed=not failures,cash_cost_views=cash_records,scalar_path_checks=path_records,
        by_asset=by_asset,failures=failures[:100],failure_count=len(failures),
        sample_trades=samples,cent_comparison_exact=True,pre_cent_float_decimal_places=8,
        original_input_decoding=True,no_quant_core_accounting_import=True,
        same_implementer=True,independent_feed=False,actual_account_audited=False,
        seconds=time.perf_counter()-start,auditor_sha256=sha(Path(oracle.__file__)),
        producer_registration_sha256=sha(JOB/"registration.json"),
        disclosure="accepted V12 input sources; Gold/EUR Ask proxies preserved; not broker-native fills")
    with (JOB/"independent-audit.json").open("x",encoding="utf-8") as f:
        json.dump(out,f,ensure_ascii=False,indent=2)
    print(dict(passed=out["passed"],cash_cost_views=cash_records,scalar_paths=path_records,
               failures=len(failures),seconds=out["seconds"]),flush=True)


if __name__ == "__main__":
    run()
