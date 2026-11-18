"""Exclusive V24 receipts; preserve all previous research inputs and attempts."""
from pathlib import Path
from prop_v23_common import ROOT,V19,V22,V21,FIRST,DEV_END,END,read,sha
from prop_v21_common import compressed as parent_compressed
import prop_v21_common as compression
from quant_core.prop_lifecycle_and_parity import bindings
import json

V23=ROOT/'sleeve-ablation-and-mt5-v23-20261117'
JOB=ROOT/'pareto-mt5-bot-lab-v24-20261117'
PROTOCOL=Path('planning/research/PARETO-MT5-BOT-LAB-V24-PROTOCOL-20261117.md')

def save(name,value):
    JOB.mkdir(exist_ok=True)
    with (JOB/name).open('x',encoding='utf-8') as f:json.dump(value,f,indent=2,ensure_ascii=False)

def compressed(name,value):
    with bindings(compression,JOB=JOB):return parent_compressed(name,value)
