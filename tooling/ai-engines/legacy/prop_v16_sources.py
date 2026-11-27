"""Metadata discovery and honest recorded-quote coverage, never flat padding."""
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
import re
import numpy as np
from prop_v16_common import *
from quant_core.prop_lifecycle_and_parity import bindings


def census():
    import prop_v14_source as parent
    with bindings(parent,JOB=JOB,ASSET=re.compile(r"XAUUSD|EURUSD|GBPUSD|AUDUSD|US500|gold|quantdatamanager",re.I),
            DATA_SUFFIXES=parent.DATA_SUFFIXES|{".json"}):
        parent.inventory()


def identity():
    evidence=read(V15/"bridge-evidence.json")
    rows=[]
    for r in evidence["rows"]:
        if not r["source_uncertain"]:continue
        at=datetime.fromtimestamp(r["first_unknown"]/1000,timezone.utc)
        spread=338 if r["asset"]=="XAUUSD" else 10
        jump=abs(r["after_price"]-r["before_price"])
        morphology=(1<=r["missing_minutes"]<=5 and jump<=1.5*spread and
            r["screen"]["minimum_distance"]>10*spread)
        rows.append(dict(**r,year=at.year,UTC=at.isoformat(),hour=at.hour,
            endpoint_jump=jump,spread_units=spread,flat_morphology_only=morphology,
            verified_feed_continuity=False,classification=("RECORDED_ZERO_TICKS_CONDITIONAL_ENVELOPE"
                if r["envelope"].get("quotes_in_gap")==0 else "UNRESOLVED_SOURCE_COVERAGE"),
            reason=("Native export has zero quotes inside gap; endpoints/envelope do not certify a lossless broker feed."
                if r["envelope"].get("available") else
                "No admitted native tick/HTF path for this interval in V15; discovery is refreshed in V16.")))
    groups={}
    for status in ("SOURCE_ENVELOPE_EXCLUDES_SL","MODEL_LOW_RISK"):
        chosen=[r for r in rows if r["screen"]["status"]==status]
        groups[status]=dict(occurrences=len(chosen),assets=dict(Counter(r["asset"] for r in chosen)),
            years=dict(Counter(r["year"] for r in chosen)),UTC_hours=dict(Counter(r["hour"] for r in chosen)),
            gap_minutes=dict(Counter(r["missing_minutes"] for r in chosen)),
            flat_morphology=sum(r["flat_morphology_only"] for r in chosen))
    save("gap-identities.json",dict(rows=rows,groups=groups,independent_trades=len({
        (r["id"],r["entry"]) for r in rows}),strict_market_certificates=0,
        recorded_zero_tick_minutes_are_not_padded=True,source=sha(V15/"bridge-evidence.json")))
    event("V16_gap_identity_complete",groups=groups)


def native_probe():
    """Reuse source-bound binary manifests; every missing minute stays explicitly missing."""
    from prop_campaign_source import PARENT,DTYPE
    sources=dict(XAUUSD=PARENT/"attempt-2/binary-manifest.json",
        EURUSD=ROOT/"prop-portfolio-v3-20261114/system-eur-manifest.json")
    manifests={a:read(p) for a,p in sources.items()}
    rows=read(JOB/"gap-identities.json")["rows"];loaded={};out=[]
    for r in rows:
        asset=r["asset"];first=r["before"]+60000;end=r["after"];found=[];missing=0;inside=[]
        for hour in range(first//3600000*3600000,(end-1)//3600000*3600000+1,3600000):
            proof=manifests[asset].get(str(hour))
            if proof is None:missing+=1;continue
            key=asset,hour
            if key not in loaded:
                if sha(proof["path"])!=proof["sha256"]:raise ValueError("V16_native_binary_hash")
                q=np.fromfile(proof["path"],dtype=DTYPE)
                if len(q)!=proof["records"] or len(q) and (
                    q["t"][0]<hour or q["t"][-1]>=hour+3600000 or np.any(np.diff(q["t"])<0)):
                    raise ValueError("V16_native_binary_schema")
                loaded[key]=q
            q=loaded[key];sel=q[(q["t"]>=first)&(q["t"]<end)]
            inside.extend((int(v["t"]),int(v["b"]),int(v["a"])) for v in sel)
            found.append(dict(hour=hour,**proof))
        out.append(dict(asset=asset,before=r["before"],after=r["after"],sources=found,
            hours_missing=missing,quotes_inside=len(inside),quotes=inside,
            status="NO_ADMITTED_HOUR" if not found else "PARTIAL_NATIVE_COVERAGE" if missing else
                "OBSERVED_NATIVE_QUOTES" if inside else "RECORDED_ZERO_TICKS",
            feed_continuity_proven=False))
    save("native-probe.json",dict(rows=out,manifests={a:dict(path=str(p),sha256=sha(p)) for a,p in sources.items()},
        hours_decoded=len(loaded),counts=dict(Counter(r["status"] for r in out)),
        no_flat_padding=True,broker_certificate=False))
    event("V16_native_probe_complete",hours=len(loaded),counts=dict(Counter(r["status"] for r in out)))


def csv_probe():
    from prop_v14_source import csv_window
    census=read(JOB/"raw-source-census.json")
    gaps=read(JOB/"gap-identities.json")["rows"]
    unique={(r["asset"],r["before"],r["after"]):r for r in gaps}
    files=[r for r in census["records"] if Path(r["path"]).suffix.lower()==".csv" and
        any(a.lower() in Path(r["path"]).name.lower() for a in ("XAUUSD","EURUSD"))]
    checks=[];observed=[]
    for record in files:
        p=Path(record["path"]);asset="XAUUSD" if "xauusd" in p.name.lower() else "EURUSD"
        try:
            stat=p.stat()
            if (stat.st_size,stat.st_mtime_ns)!=(record["bytes"],record["mtime_ns"]):
                checks.append(dict(path=str(p),status="CHANGED_SINCE_CENSUS"));continue
            with p.open("rb") as f:header=f.readline().decode("utf-8-sig").strip().split(",")
            ticks=header==["DateTime","Bid","Ask","Volume"]
            split=header[:2]==["Date","Time"]
            bars=header[:5]==["DateTime","Open","High","Low","Close"] or \
                header[:6]==["Date","Time","Open","High","Low","Close"]
            if not ticks and not bars:
                checks.append(dict(path=str(p),status="UNSUPPORTED_SCHEMA",header=header));continue
            count=0;hits=[]
            for (a,before,after),gap in unique.items():
                if a!=asset:continue
                fmt="%Y%m%d %H:%M:%S" if ticks else "%Y.%m.%d %H:%M:%S"
                low=datetime.fromtimestamp((before+60000)/1000,timezone.utc).strftime(fmt).encode()
                high=datetime.fromtimestamp(after/1000,timezone.utc).strftime(fmt).encode()
                _,values=csv_window(p,low,high);count+=len(values)
                if not values:continue
                for v in values:
                    text=v[0]+" "+v[1] if split else v[0]
                    pattern=fmt+(".%f" if "." in text.split(" ")[-1] else "")
                    at=int(datetime.strptime(text,pattern).replace(tzinfo=timezone.utc).timestamp()*1000)
                    if not before+60000<=at<after:raise ValueError("V16_CSV_seek_interval")
                    observed.append(dict(path=str(p),asset=a,at=at,kind="TICK" if ticks else "OHLC",
                        values=v,scale=1000 if a=="XAUUSD" else 100000,
                        source_timezone_verified=False,not_admitted_without_provenance=True))
                hits.append(dict(before=before,after=after,rows=len(values)))
            checks.append(dict(path=str(p),status="BOUNDED_INTERVALS_READ",header=header,rows_in_gaps=count,
                intervals_with_rows=hits))
        except (OSError,ValueError,UnicodeError) as exc:
            checks.append(dict(path=str(p),status="READ_OR_SCHEMA_ERROR",error=str(exc)[:300]))
    save("csv-gap-probe.json",dict(files=len(files),checks=checks,observed=observed,
        observed_rows=len(observed),backfill_admitted=False,flat_padding=False,
        absence_is_not_market_continuity=True))
    event("V16_CSV_probe_complete",files=len(files),observed_rows=len(observed))


def alternate_probe():
    """Read matching hour/day tick fixtures, including session-filtered B0 views."""
    import independent_ledger_auditor as oracle
    from prop_campaign_source import DTYPE
    census=read(JOB/"raw-source-census.json")
    gaps=read(JOB/"gap-identities.json")["rows"]
    files=[]
    for r in census["records"]:
        p=Path(r["path"])
        if p.suffix!=".ticks":continue
        asset=next((a for a in ("XAUUSD","EURUSD") if a.lower() in str(p).lower()),None)
        if not asset:continue
        epoch=re.search(r"(1[0-9]{12})$",p.stem)
        try:
            if epoch:first=int(epoch[1]);end=first+3600000;dtype=DTYPE;kind="HOURLY_DERIVED_TICK_VIEW"
            elif re.fullmatch(r"\d{4}-\d{2}-\d{2}",p.stem) and "eurusd-b0" in str(p):
                first=int(datetime.strptime(p.stem,"%Y-%m-%d").replace(tzinfo=timezone.utc).timestamp()*1000)
                end=first+86400000
                dtype=np.dtype([("t","<i8"),("ordinal","<i8"),("b","<i4"),("a","<i4")])
                kind="B0_SESSION_FILTERED_VIEW_NOT_FULL_DAY"
            else:continue
        except ValueError:continue
        matching=[g for g in gaps if g["asset"]==asset and first<g["after"] and end>g["before"]+60000]
        if matching:files.append((r,asset,dtype,kind,matching))
    rows=[];observed=[]
    for record,asset,dtype,kind,matching in files:
        p=Path(record["path"])
        try:
            stat=p.stat()
            if (stat.st_size,stat.st_mtime_ns)!=(record["bytes"],record["mtime_ns"]):
                raise ValueError("SOURCE_CHANGED_SINCE_CENSUS")
            if stat.st_size%dtype.itemsize:raise ValueError("BINARY_RECORD_WIDTH")
            q=np.fromfile(p,dtype=dtype)
            if len(q) and (np.any(np.diff(q["t"])<0) or np.any(q["b"]<=0) or np.any(q["a"]<q["b"])):
                raise ValueError("TICK_SCHEMA")
            checks=[]
            for g in matching:
                use=q[(q["t"]>=g["before"]+60000)&(q["t"]<g["after"])]
                proof=oracle.audit_tick_continuity(
                    [(int(t["t"]),int(t["b"]),int(t["a"])) for t in use],
                    g["before"]+60000,g["after"],g["side"],g["level"],{})
                checks.append(dict(before=g["before"],after=g["after"],**proof))
                for t in use:observed.append(dict(asset=asset,path=str(p),at=int(t["t"]),
                    bid=int(t["b"]),ask=int(t["a"]),admitted=False))
            rows.append(dict(path=str(p),sha256=sha(p),asset=asset,kind=kind,records=len(q),checks=checks))
        except (ValueError,OSError) as exc:
            rows.append(dict(path=str(p),status="UNRESOLVED_SOURCE_FORMAT_OR_ACCESS",error=str(exc)))
    save("alternate-tick-probe.json",dict(files=len(rows),rows=rows,observed=observed,
        observed_rows=len(observed),continuity_certificates=0,
        H1_from_M1_is_not_independent_containment=True,
        archives_and_unproven_raw_formats_not_certified=True))
    event("V16_alternate_ticks_complete",files=len(rows),observed_rows=len(observed))


def admit():
    csv=read(JOB/"csv-gap-probe.json");alt=read(JOB/"alternate-tick-probe.json")
    if csv["observed_rows"] or alt["observed_rows"]:
        raise ValueError("V16_observed_rows_require_provenance_review_before_admission")
    parent=read(V14/"source-dev-admission.json")
    result=dict(schema="V16-source-admission-v1",version="V16_NO_NEW_OBSERVATIONS",
        assets=parent["assets"],parent_manifest_sha256=sha(V14/"source-dev-admission.json"),
        probes={n:sha(JOB/n) for n in ("gap-identities.json","raw-source-census.json",
            "native-probe.json","csv-gap-probe.json","alternate-tick-probe.json")},
        added_M1={"XAUUSD":0,"EURUSD":0},synthetic_observed_bars=0,
        reuse_MarketDataStore_versions_unchanged=True,
        zero_tick_minutes_padded=False,continuity_certificates=0,
        unavailable_and_unsupported_formats_remain_unknown=True)
    save("source-admission-v16.json",result)
    event("V16_source_admission",added=result["added_M1"],certificates=0)


if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser();p.add_argument("stage",choices=("census","identity","native_probe","csv_probe",
        "alternate_probe","admit"))
    globals()[p.parse_args().stage]()
