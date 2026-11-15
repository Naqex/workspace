"""Read-only timestamp witness from already-admitted native tick hours, Dev only."""
from collections import Counter
import numpy as np
from prop_v13_campaign import JOB, ROOT, read, save
from prop_campaign_source import PARENT, DTYPE
from prop_v10_source import sha, FIRST, END

HOUR=3600000


def run():
    paths=dict(XAUUSD=PARENT/"attempt-2/binary-manifest.json",
               EURUSD=ROOT/"prop-portfolio-v3-20261114/system-eur-manifest.json")
    save("native-gap-probe-registration.json",dict(
        purpose="timestamp-only forensic witness, not source substitution or financial rerun",
        code_sha256=sha(__file__),first=FIRST,end=END,validation_prices_opened=False,
        manifests={k:dict(path=str(p),sha256=sha(p)) for k,p in paths.items()}))
    manifests={k:read(p) for k,p in paths.items()}
    gaps={}
    for row in read(JOB/"forensics.json")["rows"]:
        for event in row["events"]:
            for g in event["gaps"]:
                if g["source_uncertain"]:
                    gaps[(row["asset"],g["before"],g["after"])]=g
    evidence=[];loaded={}
    for (asset,before,after),g in sorted(gaps.items()):
        first=before+60000
        if not FIRST<=first<after<END:
            raise ValueError("Dev_only_timestamp_probe")
        missing,records,covered=0,0,0
        sources=[]
        for h in range(first//HOUR*HOUR,after//HOUR*HOUR+1,HOUR):
            if not FIRST<=h<END:
                raise ValueError("native_hour_fence")
            row=manifests[asset].get(str(h))
            if row is None:
                missing+=1;continue
            if (asset,h) not in loaded:
                if sha(row["path"])!=row["sha256"]:
                    raise ValueError("native_probe_source_hash")
                values=np.fromfile(row["path"],dtype=DTYPE)
                if len(values)!=row["records"] or len(values) and (
                    values["t"][0]<h or values["t"][-1]>=h+HOUR or np.any(np.diff(values["t"])<0)):
                    raise ValueError("native_probe_hour_schema")
                # Retain only timestamps; price values are not used to select outcomes.
                loaded[asset,h]=values["t"].copy()
            times=loaded[asset,h]
            records+=int(times.searchsorted(after)-times.searchsorted(first))
            covered+=1
            sources.append(dict(hour=h,path=row["path"],sha256=row["sha256"],records=row["records"]))
        status=("NO_ADMITTED_TICK_HOUR" if not covered else "PARTIAL_HOUR_COVERAGE" if missing else
                "NATIVE_QUOTES_EXIST_INSIDE_M1_GAP" if records else "NO_QUOTES_IN_ADMITTED_TICK_HOURS")
        evidence.append(dict(asset=asset,before=before,after=after,status=status,
            records_inside_gap=records,hours_covered=covered,hours_missing=missing,sources=sources,
            disclosure="absence in this accepted cache is not proof of broker feed completeness"))
    out=dict(rows=evidence,counts=dict(Counter(r["status"] for r in evidence)),
        native_hours_decoded=len(loaded),validation_prices_opened=False,
        price_outcomes_computed=False,producer_matrices_changed=False)
    save("native-gap-probe.json",out)
    print(dict(counts=out["counts"],native_hours_decoded=len(loaded)),flush=True)


if __name__=="__main__":
    run()
