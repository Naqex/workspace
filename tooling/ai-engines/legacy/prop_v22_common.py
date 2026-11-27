"""Exclusive V22 receipts; older frozen jobs remain read-only."""
from pathlib import Path
import json
from datetime import datetime,timezone
from prop_v21_common import ROOT,V19,V16,FIRST,DEV_END,END,read,sha
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as previous

V21=ROOT/'trade-forensics-behavioral-v21-20261117'
JOB=ROOT/'exhaustion-h1-align-v22-20261117'
PROTOCOL=Path('planning/research/EXHAUSTION-H1-ALIGN-V22-PROTOCOL-20261117.md')
FREEZE=PROTOCOL.with_name('EXHAUSTION-H1-ALIGN-V22-FREEZE-20261117.json')


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,default=lambda v:v.tolist())


def compressed(name,value):
    with bindings(previous,JOB=JOB):return previous.compressed(name,value)


def unpack(name,root=JOB):
    with bindings(previous,JOB=root):return previous.unpack(name)


def event(stage,**values):
    JOB.mkdir(exist_ok=True);r=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**values)
    with (JOB/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(r)+'\n')
    print(json.dumps(r),flush=True)
