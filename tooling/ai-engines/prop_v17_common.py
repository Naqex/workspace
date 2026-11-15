"""V17 registered risk/session experiments; historical campaign files are inputs."""
from pathlib import Path
from datetime import datetime,timezone
import json
from prop_v16_common import ROOT,V14,V15,JOB as V16,V12,V11,FIRST,DEV_END,END,read,sha

JOB=ROOT/"adaptive-velocity-v17-20261116"
PROTOCOL=Path("planning/research/ADAPTIVE-VELOCITY-V17-PROTOCOL-20261116.md")
FREEZE=PROTOCOL.with_name("ADAPTIVE-VELOCITY-V17-FREEZE-20261116.json")


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open("x",encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2,default=lambda x:x.item())


def event(stage,**values):
    JOB.mkdir(exist_ok=True)
    row=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**values)
    with (JOB/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row)+"\n")
    print(row,flush=True)
