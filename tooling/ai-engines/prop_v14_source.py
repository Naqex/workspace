"""V14 metadata census and versioned raw-source admission; no provider downloads."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import zipfile
import numpy as np
import subprocess
from prop_campaign_source import ROOT

JOB=ROOT/"evidence-and-lifecycle-v14-20261115"
V13=ROOT/"path-resolution-and-dedup-v13-20261115"
FIRST=1514764800000
DEV_END=1704067200000
END=1791936000000  # 14Oct2026 00UTC, inclusive13Oct
SEED=1509494400000
ROOTS=(Path("D:/ANNAM/TradingWorkspace"),Path("E:/BACKUP-TRADINGWORKSPACE"))
DATA_SUFFIXES={".bi5",".csv",".parquet",".gz",".zip",".zst",".7z",".ticks",".bin",".db",".sqlite",".dat"}
ASSET=re.compile(r"XAUUSD|EURUSD|gold|(?:^|[/\\])eur[-_]",re.I)


def read(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open("x",encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2)


def sha(path):
    with Path(path).open("rb") as f:
        return hashlib.file_digest(f,"sha256").hexdigest()


def inventory():
    JOB.mkdir(exist_ok=True)
    records=[];errors=[];counts=Counter();archives=[]
    for root in ROOTS:
        stack=[root]
        while stack:
            folder=stack.pop()
            try:
                with os.scandir(folder) as scan:
                    for e in scan:
                        p=folder/e.name
                        s=e.stat(follow_symlinks=False)
                        if e.is_symlink() or getattr(s,"st_file_attributes",0)&1024:
                            counts["links_skipped"]+=1;continue
                        if e.is_dir(follow_symlinks=False):
                            stack.append(p);counts["folders"]+=1;continue
                        counts["files"]+=1
                        suffix=p.suffix.lower()
                        if suffix in DATA_SUFFIXES:
                            counts[suffix]+=1
                            row=dict(path=str(p),bytes=s.st_size,mtime_ns=s.st_mtime_ns)
                            if ASSET.search(str(p)) or "quantdatamanager" in str(p).lower():
                                records.append(dict(row,asset_name_hint=True))
                            if suffix in {".zip",".gz",".7z",".zst"}:
                                archives.append(row)
                if counts["folders"]%10000==0:
                    print(dict(stage="V14_metadata_inventory",**counts),flush=True)
            except OSError as exc:
                errors.append(dict(path=str(folder),error=type(exc).__name__))
        print(dict(stage="V14_root_inventory_done",root=str(root),files=counts["files"]),flush=True)
    members=[]
    for row in archives:
        p=Path(row["path"])
        if p.suffix.lower()!=".zip":
            continue
        try:
            with zipfile.ZipFile(p) as z:
                found=[dict(name=e.filename,bytes=e.file_size,encrypted=bool(e.flag_bits&1))
                       for e in z.infolist() if ASSET.search(str(p)+"/"+e.filename)]
            if found:
                members.append(dict(archive=str(p),members=found))
        except (OSError,zipfile.BadZipFile) as exc:
            errors.append(dict(path=str(p),error=type(exc).__name__))
    save("raw-source-census.json",dict(records=records,archives=archives,zip_matches=members,
        counts=dict(counts),errors=errors,price_values_decoded=False,
        observed_utc=datetime.now(timezone.utc).isoformat(),
        scope="entire D workspace and E backup; links/unreadable paths excluded explicitly"))
    print(dict(stage="V14_inventory_complete",candidate_files=len(records),archive_matches=len(members),
               errors=len(errors),largest=sorted(records,key=lambda r:-r["bytes"])[:12]),flush=True)


def csv_window(path, low, high):
    """Seek a registered sorted QDM CSV; return only requested timestamp rows."""
    with Path(path).open("rb") as f:
        header=f.readline().decode("utf-8-sig").strip().split(",")
        split_date=header[:2]==["Date","Time"]
        def key(line):
            values=line.split(b",",2)
            return b" ".join(values[:2]) if split_date and len(values)>1 else values[0]
        begin=f.tell()
        f.seek(0,2);size=f.tell()
        left,right=begin,size
        while right-left>2048:
            mid=(left+right)//2
            f.seek(mid)
            f.readline()
            pos=f.tell();line=f.readline()
            if not line or key(line)>=low:
                right=mid
            else:
                left=pos+len(line)
        f.seek(left)
        rows=[]
        while True:
            line=f.readline()
            if not line:break
            timestamp=key(line)
            if timestamp>=high:break
            if timestamp>=low:rows.append(line.decode().strip().split(","))
    if any(rows[i][0]>rows[i+1][0] for i in range(len(rows)-1)):
        raise ValueError("CSV_window_timestamp_order")
    return header,rows


def gold_split_probe():
    census=read(JOB/"raw-source-census.json")
    primary=read(JOB/"source-dev-admission.json")
    candidates=[r for r in census["records"] if r["path"].startswith(str(ROOTS[0]))
        and Path(r["path"]).name=="XAUUSD_TW-M1-No Session.csv"]
    sources=[];checks=[]
    seen=set()
    for candidate in candidates:
        if candidate["bytes"] in seen:continue
        seen.add(candidate["bytes"])
        p=Path(candidate["path"]);digest=sha(p)
        total=0
        for gap in primary["raw_checks"]:
            if gap["asset"]!="XAUUSD":continue
            low=datetime.fromtimestamp((gap["before"]+60000)/1000,timezone.utc).strftime("%Y.%m.%d %H:%M:%S").encode()
            high=datetime.fromtimestamp(gap["after"]/1000,timezone.utc).strftime("%Y.%m.%d %H:%M:%S").encode()
            header,values=csv_window(p,low,high)
            total+=len(values)
            checks.append(dict(path=str(p),before=gap["before"],after=gap["after"],rows=len(values),schema=header))
        sources.append(dict(path=str(p),sha256=digest,rows_inside_gaps=total))
    save("gold-split-date-probe.json",dict(sources=sources,checks=checks,
        additional_rows=sum(r["rows_inside_gaps"] for r in sources),
        time_label="QDM split Date/Time, UTC mapping not newly certified",validation_prices_opened=False))
    print(dict(stage="V14_split_date_probe",sources=sources),flush=True)


def longitudinal():
    """Only after committed A/B release; reuse Gold caches and cached EUR M1 export."""
    from quant_core.market_data_store import BAR
    from prop_v8_source import cache_bars
    from prop_v5_data import QDM
    from prop_v9_eurusd import ingest
    from prop_v14_campaign import DECISION
    release=read(JOB/"longitudinal-release.json");cfg=read(DECISION)
    committed=json.loads(subprocess.check_output(
        ["git","show",release["commit"]+":"+DECISION.as_posix()]))
    if cfg!=committed:raise ValueError("V14_release_drift")
    for p,digest in cfg["pins"].items():
        if sha(p)!=digest:raise ValueError("V14_source_read_frozen_code_changed:"+p)
    dev=read(JOB/"source-dev-admission.json")["assets"]
    output={}
    for asset in ("XAUUSD","EURUSD"):
        base=dev[asset]
        if sha(base["path"])!=base["sha256"]:raise ValueError("Dev_source_hash")
        old=np.memmap(base["path"],dtype=BAR,mode="r")
        if asset=="XAUUSD":
            hist,proof=cache_bars(DEV_END,1735689600000,released=True)
            p=ROOT/"prop-v4-harvest-v6-20261115/gold-holdout-m1.bin"
            seal=read(p.with_name("gold-source-proof.json"))
            if sha(p)!=seal["binary_sha256"]:raise ValueError("V6_holdout_gold_hash")
            future=np.memmap(p,dtype=BAR,mode="r")
            extra=np.concatenate([hist,future[(future["t"]>=1735689600000)&(future["t"]<END)]])
            proof=dict(historical2024=proof,holdout_path=str(p),holdout_sha256=seal["binary_sha256"])
        else:
            folder=JOB/"EURUSD-2024-2026-export";folder.mkdir(exist_ok=False)
            args=["-data","action=export","symbols=EURUSD_TW","timeframe=M1","timezone=UTC",
                "datefrom=2024.01.01","dateto=2026.10.13","outputdir="+folder.as_posix(),
                "format=Custom","cIncludeHeader=true","cHeader=DateTime,Open,High,Low,Close",
                "cFormat=[Date:yyyy.MM.dd HH:mm:ss],[Open],[High],[Low],[Close]"]
            save("EURUSD-export-request.json",dict(argv=args,cached_only=True,provider_download=False,
                release_commit=release["commit"],qdm_sha256=sha(QDM/"qdmcli.exe")))
            with (folder/"export.log").open("w") as log:
                result=subprocess.run([str(QDM/"qdmcli.exe"),*args],cwd=QDM,stdout=log,
                    stderr=subprocess.STDOUT,timeout=600,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
            files=list(folder.glob("*.csv"))
            if result.returncode or len(files)!=1:raise ValueError("V14_cached_EUR_export")
            extra=ingest(files[0],DEV_END,END)
            proof=dict(raw_path=str(files[0]),raw_sha256=sha(files[0]),rows=len(extra),cached_only=True)
        data=np.concatenate([old,extra])
        if np.any(np.diff(data["t"])<=0) or data["t"][0]<SEED or data["t"][-1]>=END:
            raise ValueError("V14_full_source_clock")
        for field in "ohlc":data["a"+field]=data["b"+field]+(338 if asset=="XAUUSD" else 10)
        p=JOB/f"{asset}-full-M1.bin";data.tofile(p)
        output[asset]=dict(path=str(p),sha256=sha(p),records=len(data),first=int(data["t"][0]),
            last=int(data["t"][-1]),extra_proof=proof,Dev_parent=base,
            source="BID_M1_WITH_FIXED_ASK_PROXY",Ask_proxy=.338 if asset=="XAUUSD" else .0001)
        print(dict(stage="V14_longitudinal_source",asset=asset,records=len(data),last=int(data["t"][-1])),flush=True)
    save("full-source-admission.json",dict(assets=output,release=release,prices2024_2026_read=True,
        cutoff_exclusive=END,no_post_cutoff_prices_loaded=True,source_certified_native_ticks=False))


def evidence():
    """Seek raw QDM and alternate cached sources at each Dev missing interval."""
    from quant_core.market_data_store import BAR, MarketDataStore
    from quant_core.gap_aware_execution import GapAwarePathIndex
    from quant_core.ftmo_execution_and_calendar import execution_schedule
    old=read(V13/"discovery.json")["rows"]
    complete=[r for r in old if r["complete_path"]]
    assert len(complete)==26
    parent=read(ROOT/"enterprise-alpha-v10-20261115/source-admission.json")
    census=read(JOB/"raw-source-census.json")
    core=set(read(V13/"decision.json")["selected"])
    events=[];all_gaps={};core_gaps={};source_bars={}
    for asset in ("XAUUSD","EURUSD"):
        source=parent["assets"][asset]
        if sha(source["path"])!=source["binary_sha256"]:raise ValueError("V10_source_drift")
        bars=np.memmap(source["path"],mode="r",dtype=BAR);source_bars[asset]=bars
        ix=GapAwarePathIndex(bars,asset=asset,schedule=execution_schedule(FIRST,DEV_END))
        z=np.load(V13/f"{asset}-path-matrix.npz")
        ends=np.array([g["after"] for g in ix.gaps])
        starts=np.array([g["before"] for g in ix.gaps])
        for row in complete:
            if row["asset"]!=asset:continue
            j,mode=row["source_cell"],row["mode"];p=f"{j}:{mode}:"
            for i in np.flatnonzero(z[f"{j}:admitted"]&z[p+"valid"]):
                entry,exit_at=int(z[f"{j}:entry_at"][i]),int(z[p+"exit_at"][i])
                crossed=np.flatnonzero((ends>entry)&(starts<exit_at))
                gaps=[ix.gaps[g] for g in crossed if ix.gaps[g]["source_uncertain"]]
                for g in gaps:
                    key=(asset,g["before"],g["after"]);all_gaps[key]=g
                    if row["id"] in core:core_gaps[key]=g
                events.append(dict(id=row["id"],asset=asset,event=int(i),entry=entry,exit=exit_at,
                    core=row["id"] in core,source_uncertain=bool(gaps),
                    gaps=[dict(before=g["before"],after=g["after"],
                               missing=g["missing"],minutes_by_kind=g["minutes_by_kind"]) for g in gaps]))
    # Only original native tick exports with explicit UTC commands are candidates for substitution.
    raw_checks=[]; additions={a:[] for a in source_bars};hashes={}
    for (asset,before,after),gap in sorted(all_gaps.items()):
        witnesses=[]
        if asset=="EURUSD":
            year=datetime.fromtimestamp(before/1000,timezone.utc).year
            directory=ROOT/f"eurusd-observed-history-v2/{year}/attempt-1"
            path=directory/"export/EURUSD_TICK_TW-TICK-No Session.csv"
            if path.exists():
                command=read(directory/"export-command.json")
                if "timezone=UTC" not in command["argv"] or "timeframe=TICK" not in command["argv"]:
                    raise ValueError("native_CSV_clock_not_UTC")
                if path not in hashes:hashes[path]=sha(path)
                low=datetime.fromtimestamp((before+60000)/1000,timezone.utc).strftime("%Y%m%d %H:%M:%S").encode()
                high=datetime.fromtimestamp(after/1000,timezone.utc).strftime("%Y%m%d %H:%M:%S").encode()
                header,values=csv_window(path,low,high)
                if header!=["DateTime","Bid","Ask","Volume"]:raise ValueError("native_tick_CSV_schema")
                witnesses.append(dict(path=str(path),sha256=hashes[path],kind="NATIVE_UTC_TICKS",
                                      quotes=len(values),first=before+60000,end=after))
                bucket={}
                for v in values:
                    t=int(datetime.strptime(v[0],"%Y%m%d %H:%M:%S.%f").replace(tzinfo=timezone.utc).timestamp()*1000)
                    if not FIRST<=t<DEV_END:raise ValueError("Dev_raw_tick_fence")
                    b,a=(int(round(float(v[k])*100000)) for k in (1,2))
                    if b<=0 or a<b:raise ValueError("native_quote_schema")
                    bucket.setdefault(t//60000*60000,[]).append((b,a))
                for t,quotes in bucket.items():
                    r=np.zeros(1,dtype=BAR);r["t"]=t
                    for k,side in enumerate(("b","a")):
                        px=[v[k] for v in quotes]
                        for f,v in zip("ohlc",(px[0],max(px),min(px),px[-1])):r[side+f]=v
                    additions[asset].append(r)
        else:
            # All identical-size backup exports stay metadata candidates; canonical D gets first read.
            candidates=[r for r in census["records"] if r["path"].startswith(str(ROOTS[0]))
                and Path(r["path"]).name=="XAUUSD_TW-M1-No Session.csv"]
            seen=set()
            for r in candidates:
                path=Path(r["path"])
                if r["bytes"] in seen:continue
                seen.add(r["bytes"])
                if path not in hashes:hashes[path]=sha(path)
                low=datetime.fromtimestamp((before+60000)/1000,timezone.utc).strftime("%Y.%m.%d %H:%M:%S").encode()
                high=datetime.fromtimestamp(after/1000,timezone.utc).strftime("%Y.%m.%d %H:%M:%S").encode()
                header,values=csv_window(path,low,high)
                accepted=header==["DateTime","Open","High","Low","Close"]
                witnesses.append(dict(path=str(path),sha256=hashes[path],kind="CACHED_QDM_M1",
                    schema=header,rows=len(values),accepted_schema=accepted))
                if accepted:
                    for v in values:
                        t=int(datetime.strptime(v[0],"%Y.%m.%d %H:%M:%S").replace(tzinfo=timezone.utc).timestamp()*1000)
                        if not FIRST<=t<DEV_END:raise ValueError("Dev_raw_M1_fence")
                        bar=np.zeros(1,dtype=BAR);bar["t"]=t
                        for f,value in zip("ohlc",v[1:]):
                            bar["b"+f]=int(round(float(value)*1000));bar["a"+f]=bar["b"+f]+338
                        additions[asset].append(bar)
        raw_checks.append(dict(asset=asset,before=before,after=after,witnesses=witnesses))
    proofs={}
    for asset,bars in source_bars.items():
        data=np.concatenate([bars,*additions[asset]]) if additions[asset] else bars.copy()
        data.sort(order="t",kind="stable")
        _,unique=np.unique(data["t"],return_index=True)
        data=data[np.sort(unique)]
        folder=JOB/f"source-dev-{asset}";folder.mkdir()
        files={}
        for name,values in [("times",data["t"]//1000)]+[(n,data["b"+n]) for n in "ohlc"]:
            p=folder/(name+".bin")
            values.astype("<i8" if name=="times" else "<i4").tofile(p);files[p.name]=sha(p)
        (folder/"manifest.json").write_text(json.dumps(dict(files=files,rows=len(data),
            raw_sha256=parent["assets"][asset]["binary_sha256"],
            parent=parent["assets"][asset],backfill_rows=len(data)-len(bars))))
        stored=MarketDataStore(folder).bars(SEED,DEV_END)
        for n in "ohlc":stored["a"+n]=stored["b"+n]+(338 if asset=="XAUUSD" else 10)
        # Keep the registered Ask model across the entire versioned derivative.
        path=JOB/f"{asset}-Dev-M1.bin";stored.tofile(path)
        proofs[asset]=dict(path=str(path),sha256=sha(path),records=len(stored),added_rows=len(stored)-len(bars),
            column_store=str(folder),Ask_proxy=.338 if asset=="XAUUSD" else .0001)
    save("source-dev-admission.json",dict(assets=proofs,raw_checks=raw_checks,
        native_csv_hashes={str(p):v for p,v in hashes.items()},validation_prices_opened=False,
        input_files_immutable=True,provider_downloads=0))
    save("path-evidence.json",dict(events=events,core_signals=sum(r["core"] for r in events),
        core_uncertain=sum(r["core"] and r["source_uncertain"] for r in events),
        core_unique_gaps=[dict(asset=k[0],**g) for k,g in core_gaps.items()],
        all_unique_gaps=len(all_gaps),source_substitution="only exact missing source timestamps, no padding",
        raw_quotes_found=sum(sum(w.get("quotes",0) for w in r["witnesses"]) for r in raw_checks)))
    print(dict(stage="V14_evidence",core=sum(r["core"] for r in events),
        uncertain=sum(r["core"] and r["source_uncertain"] for r in events),
        unique_core_gaps=len(core_gaps),added={k:v["added_rows"] for k,v in proofs.items()}),flush=True)


if __name__=="__main__":
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument("stage",choices=("inventory","evidence","gold_split_probe","longitudinal"))
    globals()[p.parse_args().stage]()
