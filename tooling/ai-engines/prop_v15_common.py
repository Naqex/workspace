"""V15 frozen-tape bridge and sizing diagnostics; previous job files stay read-only."""
from pathlib import Path
from datetime import datetime,timezone
import json
from prop_v14_source import ROOT,JOB as V14,FIRST,DEV_END,END,read,sha

JOB=ROOT/"bridge-certification-and-velocity-v15-20261115"
PROTOCOL=Path("planning/research/BRIDGE-AND-VELOCITY-V15-PROTOCOL-20261115.md")
DECISION=Path("planning/research/BRIDGE-AND-VELOCITY-V15-FREEZE-20261115.json")
FACTORS=(1.,1.25,1.5,2.,2.5,3.)


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open("x",encoding="utf-8") as f:
        json.dump(value,f,ensure_ascii=False,indent=2,default=lambda x:x.item())


def event(stage,**values):
    JOB.mkdir(exist_ok=True)
    row=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**values)
    with (JOB/"events.jsonl").open("a",encoding="utf-8") as f:f.write(json.dumps(row)+"\n")
    print(row,flush=True)
