"""Scalar/Fraction V11 endpoint accounting and deterministic composition audit."""
from collections import defaultdict
from datetime import datetime,timezone,timedelta
from fractions import Fraction as F
from math import sqrt
from statistics import median
from pathlib import Path
import json
import time
import numpy as np
from prop_campaign_source import ROOT
from prop_v10_source import sha,FIRST,END

JOB=ROOT/"ensemble-and-storage-v11-20261115"
ATTEMPT=JOB/"clock-corrected"
DAY=86400000


def read(p):
    return json.loads(Path(p).read_text(encoding="utf-8-sig"))


def correlation(a,b):
    ma,mb=sum(a)/len(a),sum(b)/len(b)
    x,y=[v-ma for v in a],[v-mb for v in b]
    denom=sqrt(sum(v*v for v in x)*sum(v*v for v in y))
    return round(sum(u*v for u,v in zip(x,y))/denom,12) if denom else 1.


def drawdown(values):
    equity=peak=worst=0.
    for value in values:
        equity+=value
        peak=max(peak,equity)
        worst=max(worst,peak-equity)
    return worst


def run():
    start=time.perf_counter()
    atlas=read(ATTEMPT/"component-atlas.json")
    old=np.load(JOB.parent/"enterprise-alpha-v10-20261115/raw-matrix-reviewed.npz")
    new=np.load(ATTEMPT/"native-hourly-matrix.npz")
    index=read(ATTEMPT/"source-admission-v11.json")
    days=[d for d in range(FIRST//DAY,END//DAY) if (d+3)%7<5]
    day_index={d:i for i,d in enumerate(days)}
    profiles,raw_profiles,events,rows={},{},{},{}
    max_error=0.;priced=0;quote_samples=[];expected_candidates=[]
    def equal(a,b):
        nonlocal max_error
        error=abs(float(a)-float(b));max_error=max(max_error,error)
        assert error<1e-8,(a,b,error)
    for j,row in enumerate(atlas["rows"]):
        source,k=(old,j) if j<544 else (new,j-544)
        fields=("at","entry_at","exit_at","deadline","side","entry_price","exit_price",
                "stop","natural","friction","ratio","ok","admitted","years")
        m={f:source[f"{k}:{f}"] for f in fields}
        money={model:{f:source[f"{k}:{model}:{f}"] for f in
                      ("net_R","net","gross","commission","funding","funding_multipliers")}
               for model in ("SYM","ASYM")}
        np.testing.assert_array_equal(m["admitted"],m["ok"]&(m["ratio"]<=.15))
        passed=bool(m["admitted"].any()) and bool(m["ok"].all())
        if m["admitted"].any():
            passed &= sum(float(v) for v in money["SYM"]["net_R"][m["admitted"]])/int(m["admitted"].sum())>=.04
        for years in ((2018,2019,2020),(2021,2022,2023)):
            cohort=[i for i,y in enumerate(m["years"]) if int(y) in years]
            good=[i for i in cohort if m["ok"][i]]
            accepted=[i for i in cohort if m["admitted"][i]]
            passed &= bool(cohort) and len(accepted)/max(1,len(cohort))>=.5
            passed &= bool(good) and median(m["friction"][good])/median(m["natural"][good])<=.15
            passed &= sum(float(money["SYM"]["net_R"][i]) for i in good)>0
            passed &= sum(float(money["SYM"]["net_R"][i]) for i in accepted)>0
        assert bool(passed)==row["component_admitted"],row["id"]
        if passed:expected_candidates.append(row["id"])
        identity=row["id"];rows[identity]=row;events[identity]=set(map(int,m["at"]))
        raw_profile=[0.]*len(days);admit_profiles={model:[0.]*len(days) for model in money}
        for i in np.flatnonzero(m["ok"]):
            assert FIRST<=m["at"][i]<END and m["entry_at"][i]<=m["deadline"][i]<=m["exit_at"][i]<END
            assert 0<=m["exit_at"][i]-m["deadline"][i]<=60000
            raw_profile[day_index[int(m["at"][i])//DAY]]+=float(money["SYM"]["net_R"][i])
        for i in np.flatnonzero(m["admitted"]):
            for model in money:
                admit_profiles[model][day_index[int(m["at"][i])//DAY]]+=float(money[model]["net_R"][i])
        for a in row["annual"]:
            selected=[i for i in range(len(m["at"])) if m["years"][i]==a["year"] and m["admitted"][i]]
            assert len(selected)==a["admitted"]
            for model in money:
                equal(sum(float(money[model]["net_R"][i]) for i in selected),a["economics"][model]["admitted_net_R"])
        for c in row["clusters"]:
            mask=[i for i in range(len(m["at"])) if int(m["years"][i]) in c["years"]]
            ok=[i for i in mask if m["ok"][i]]
            accepted=[i for i in mask if m["admitted"][i]]
            for model in money:
                equal(sum(float(money[model]["net_R"][i]) for i in ok),c["net"][model]["raw"])
                equal(sum(float(money[model]["net_R"][i]) for i in accepted),c["net"][model]["admitted"])
        profiles[identity]=admit_profiles;raw_profiles[identity]=raw_profile
        if j<544:
            continue  # V10 Fraction receipts/source bindings are separately reverified.
        scale=1000 if row["asset"]=="US500" else 100000
        for i in np.flatnonzero(m["ok"]):
            sign=int(m["side"][i]);entry,exit_at=int(m["entry_at"][i]),int(m["exit_at"][i])
            natural=F(sign*(int(m["entry_price"][i])-int(m["stop"][i])),scale)
            gross=F(sign*(int(m["exit_price"][i])-int(m["entry_price"][i])),scale)
            if row["asset"]=="US500":
                count=max(0,exit_at//DAY-entry//DAY);commission=F(1);extra=F(3,2);funding=-2*count
            else:
                commission=F(0);extra=F(9,100000);count=0
                d=datetime.fromtimestamp(entry/1000,timezone.utc).replace(hour=22,minute=0,second=0,microsecond=0)
                finish=datetime.fromtimestamp(exit_at/1000,timezone.utc)
                while d<=finish:
                    if int(d.timestamp()*1000)>entry and d.weekday()<5:
                        count+=3 if d.weekday()==2 else 1
                    d+=timedelta(days=1)
                funding=-F(4,10000)*count
            net=gross-commission-extra+funding
            equal(natural,m["natural"][i])
            for model in money:
                for field,expected in (("gross",gross),("commission",commission),("funding",funding),
                                       ("funding_multipliers",count),("net",net),("net_R",net/natural)):
                    equal(money[model][field][i],expected)
            priced+=1
        valid=np.flatnonzero(m["ok"])
        if len(valid):
            for i in {int(valid[0]),int(valid[len(valid)//2]),int(valid[-1])}:
                quote_samples.append(dict(asset=row["asset"],side=int(m["side"][i]),
                    entry=int(m["entry_at"][i]),exit=int(m["exit_at"][i]),
                    p0=int(m["entry_price"][i]),px=int(m["exit_price"][i]),friction=float(m["friction"][i])))
    candidate_ids=sorted(r["id"] for r in atlas["candidates"])
    assert candidate_ids==sorted(expected_candidates)
    corr={(a,b):correlation(raw_profiles[a],raw_profiles[b]) for a in candidate_ids for b in candidate_ids}
    adjacency={a:set() for a in candidate_ids}
    for a in candidate_ids:
        for b in candidate_ids:
            if (rows[a]["asset"],rows[a]["family"])!=(rows[b]["asset"],rows[b]["family"]): continue
            overlap=len(events[a]&events[b])/max(1,min(len(events[a]),len(events[b])))
            if corr[a,b]>=.3 or overlap>=.5:adjacency[a].add(b)
    unseen=set(candidate_ids);groups=[]
    while unseen:
        stack=[min(unseen)];group=set()
        while stack:
            a=stack.pop()
            if a in group:continue
            group.add(a);unseen.discard(a);stack.extend(adjacency[a]-group)
        groups.append(sorted(group))
    medoids=[min(g,key=lambda a:(round(sum(1-corr[a,b] for b in g),12),a)) for g in groups]
    chosen=[]
    for a in sorted(medoids,key=lambda a:(rows[a]["asset"],rows[a]["family"],a)):
        if len(chosen)<8 and all(corr[a,b]<.3 for b in chosen):chosen.append(a)
    assert chosen==atlas["selection"]["selected"]
    compare=np.load(ATTEMPT/"ensemble-development-profiles.npz")
    annual=atlas["decision"]["annual"]
    for model in ("SYM","ASYM"):
        total=[sum(profiles[a][model][d] for a in chosen) for d in range(len(days))]
        np.testing.assert_allclose(total,compare[model],atol=1e-8,rtol=1e-10)
        equal(sum(total),atlas["decision"]["metrics"][model]["net_R"])
        equal(drawdown(total),atlas["decision"]["metrics"][model]["endpoint_R_DD"])
        for a in annual:
            values=[v for day,v in zip(days,total) if datetime.fromtimestamp(day*86400,timezone.utc).year==a["year"]]
            equal(sum(values),a["models"][model]["net_R"])
            equal(drawdown(values),a["models"][model]["endpoint_R_DD"])
    # Sample source quotes through a separate JSON/rational opening-price decoder.
    source_files=defaultdict(set)
    for sample in quote_samples:
        asset=sample["asset"]
        if asset=="US500":
            files=[]
            for y in index["minute_indices"][asset]["years"]:
                p=Path(y["root"]);proof=read(p/"source-observation-proof.json")
                files.extend(dict(path=str(p/(r["request"]+".json")),side=r["request"].split("-")[1],
                                  first=r["first"],last=r["last"]) for r in proof["output_seals"])
        else: files=index["hourly_indices"][asset]["books"]
        for at in (sample["entry"],sample["exit"]):
            for side in ("bid","ask"):
                book=next(r for r in files if r["side"]==side and r["first"]<=at<=r["last"])
                source_files[(book["path"],asset,side)].add(at)
    quotes={}
    for (file,asset,side),needed in source_files.items():
        data=json.loads(Path(file).read_bytes(),parse_float=str)
        if isinstance(data,dict):data=data.get("rows",data.get("data",[]))
        scale=1000 if asset=="US500" else 100000
        for r in data:
            if r["timestamp"] in needed:
                quotes[asset,side,r["timestamp"]]=int(F(str(r["open"]))*scale)
    for s in quote_samples:
        buy=s["side"]==1
        assert quotes[s["asset"],"ask" if buy else "bid",s["entry"]]==s["p0"]
        assert quotes[s["asset"],"bid" if buy else "ask",s["exit"]]==s["px"]
        spread=quotes[s["asset"],"ask",s["entry"]]-quotes[s["asset"],"bid",s["entry"]]
        equal(s["friction"],F(spread,1000)+F(5,2) if s["asset"]=="US500" else F(spread,100000)+F(9,100000))
    result=dict(passed=True,configurations=len(atlas["rows"]),annual_cells=len(atlas["rows"])*6,
        new_source_priced_rows=priced,source_quote_sample_records=len(quote_samples),
        scalar_medoid_selection_exact=True,K=len(chosen),both_ensemble_profiles_verified=True,
        max_abs_error=max_error,seconds=time.perf_counter()-start,
        no_actual_SL_equity_or_funded_account=True,validation_prices_opened=False,
        same_implementer_different_arithmetic=True,
        artifact_sha256={name:sha(ATTEMPT/name) for name in ("component-atlas.json","native-hourly-matrix.npz","decision.json")})
    p=ATTEMPT/"independent-oracle.json"
    if p.exists():raise ValueError("preserve_oracle_attempt")
    p.write_text(json.dumps(result,indent=2),encoding="utf-8")
    print(result,flush=True)


if __name__=="__main__":
    run()
