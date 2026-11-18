"""Reuse full account lifecycle with committed V26 account-level sleeve weights."""
import argparse
import prop_v23_campaign as parent
from prop_v20_campaign import Tape as SourceTape
from prop_v26_iso import verify
from prop_v26_common import *


class Tape(SourceTape):
    def __init__(self,tag,mode,dev=False):
        frozen = verify()
        super().__init__(tag,mode,dev)
        self.profile = frozen["profile"]
        self.selected = dict(name="P80_ISO_EXACT")


def run(stage,tag,mode="PRIMARY",pct=100,preflight=False):
    activate_runtime()
    verify()
    with bindings(parent,JOB=JOB,Tape=Tape,FREEZE=FREEZE,save=save,compressed=compressed,event=event):
        if stage=="historical":parent.historical(tag,mode,pct,False,preflight)
        elif stage=="monte":parent.monte(tag,preflight)
        else:raise ValueError("V26_REGISTERED_STAGE_ONLY")


if __name__=="__main__":
    p=argparse.ArgumentParser()
    p.add_argument("stage",choices=("historical","monte"))
    p.add_argument("--tag",choices=("OLHC","OHLC"),default="OLHC")
    p.add_argument("--mode",choices=("PRIMARY","STRICT"),default="PRIMARY")
    p.add_argument("--pct",type=int,choices=(100,150),default=100)
    p.add_argument("--preflight",action="store_true")
    args=p.parse_args()
    run(args.stage,args.tag,args.mode,args.pct,args.preflight)
