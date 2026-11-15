"""V16 bounded campaign; historical jobs are immutable inputs."""
from pathlib import Path
from datetime import datetime,timezone
import json
from prop_v15_common import ROOT,V14,JOB as V15,FIRST,DEV_END,END,read,sha

JOB=ROOT/"gap-immune-and-multiasset-v16-20261116"
V12=ROOT/"sl-active-ensemble-v12-20261115"
V11=ROOT/"ensemble-and-storage-v11-20261115"
PROTOCOL=Path("planning/research/GAP-IMMUNE-MULTIASSET-V16-PROTOCOL-20261116.md")
FREEZE=PROTOCOL.with_name("GAP-IMMUNE-MULTIASSET-V16-FREEZE-20261116.json")


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open("x",encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2,default=lambda x:x.item())


def event(stage,**kwargs):
    row=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**kwargs)
    JOB.mkdir(exist_ok=True)
    with (JOB/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row)+"\n")
    print(row,flush=True)
