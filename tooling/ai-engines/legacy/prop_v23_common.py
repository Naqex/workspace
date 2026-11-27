"""V23 exclusive campaign evidence and source-preserving compressed tables."""
from pathlib import Path
from datetime import datetime,timezone
import json
from prop_v22_common import ROOT,V19,V16,V21,FIRST,DEV_END,END,read,sha
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as compression

V22=ROOT/'exhaustion-h1-align-v22-20261117'
JOB=ROOT/'sleeve-ablation-and-mt5-v23-20261117'
PROTOCOL=Path('planning/research/SLEEVE-ABLATION-MT5-V23-PROTOCOL-20261117.md')
FREEZE=PROTOCOL.with_name('SLEEVE-ABLATION-MT5-V23-FREEZE-20261117.json')


def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open('x',encoding='utf-8',newline='\n') as f:
        json.dump(value,f,indent=2,ensure_ascii=False,default=lambda v:v.tolist())


def compressed(name,value):
    with bindings(compression,JOB=JOB):return compression.compressed(name,value)


def unpack(name,root=JOB):
    with bindings(compression,JOB=root):return compression.unpack(name)


def event(stage,**values):
    JOB.mkdir(exist_ok=True);r=dict(stage=stage,utc=datetime.now(timezone.utc).isoformat(),**values)
    with (JOB/'events.jsonl').open('a',encoding='utf-8') as f:f.write(json.dumps(r)+'\n')
    print(json.dumps(r),flush=True)
