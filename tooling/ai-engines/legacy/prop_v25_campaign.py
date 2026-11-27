"""Reuse the audited V23 lifecycle/oracle with frozen V25 sizing only."""
import argparse
import prop_v23_campaign as parent
from prop_v20_campaign import Tape as SourceTape
from prop_v25_risk import verify, FREEZE
from prop_v25_common import *


class Tape(SourceTape):
    def __init__(self, tag, mode, dev=False):
        frozen = verify()
        super().__init__(tag, mode, dev)
        self.profile = frozen["profile"]
        self.selected = dict(name="P80_20_ISO")


def run(stage, tag, mode="PRIMARY", pct=100, preflight=False):
    verify()
    with bindings(parent, JOB=JOB, Tape=Tape, FREEZE=FREEZE, save=save,
                  compressed=compressed, event=event):
        if stage == "historical":
            parent.historical(tag, mode, pct, False, preflight)
        elif stage == "monte":
            parent.monte(tag, preflight)
        else:
            raise ValueError("V25_registered_stage_only")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("historical", "monte"))
    parser.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    parser.add_argument("--mode", choices=("PRIMARY", "STRICT"), default="PRIMARY")
    parser.add_argument("--pct", type=int, choices=(100, 150), default=100)
    parser.add_argument("--preflight", action="store_true")
    args = parser.parse_args()
    run(args.stage, args.tag, args.mode, args.pct, args.preflight)
