"""Restore the owner's conditional N2 trigger; preserve the global-stop attempt."""
from collections import Counter
from prop_v8_common import *
from prop_v8_source import Calendar, readers
from prop_v8_signals import normalize, realize
from prop_v8_campaign import economics, gates

REGISTRATION = Path("planning/research/PROP-V8-N2-CORRECTION-20261115.json")


def conditional_normalize(raw, reader):
    out = []
    for r in raw:
        entry = reader.endpoint(r["decision_msc"])
        if entry is None:
            raise ValueError("N2_correction_entry_unknown")
        px = entry[2] if r["side"] == "BUY" else entry[1]
        width = abs(px-r["stop_units"])/1000
        row = normalize([r],{},"N2",0)[0][0] if width>25 else dict(r)
        row.update(variant="N2_CONDITIONAL",n2_stop_triggered=width>25)
        out.append(row)
    return out


def run():
    verify()
    cfg = read(REGISTRATION)
    head = subprocess.check_output(["git","rev-parse","HEAD"],text=True).strip()
    if json.loads(subprocess.check_output(["git","show",head+":"+REGISTRATION.as_posix()])) != cfg:
        raise ValueError("N2_semantic_correction_not_committed")
    if digest(JOB/"development.json") != cfg["original_development_sha256"]:
        raise ValueError("N2_original_development_drift")
    raw = [dict(t,asset="XAUUSD") for t in read(ROOT/"prop-qualification-campaign-20261114/gold-dev-signals.json")
           if t["recipe"]=="A"]
    source = readers("dev",ORDERS[0],START,DEV_END)["XAUUSD"]
    rows = conditional_normalize(raw,source)
    trades,rejected = realize(rows,source,Calendar(read(CALENDAR),START,DEV_END),DEV_END,core=True)
    stats = economics(trades,(2022,2023),core=True,raw_counts=dict(Counter(r["day"][:4] for r in raw)))
    result = dict(commit=head,registration=cfg,trades=trades,economics=stats,gate=gates(stats,True),
                  normalization_skips=[],rejected=rejected,triggered=sum(r["n2_stop_triggered"] for r in rows),
                  new_non_development_evaluation=False)
    write_json(JOB/"N2-semantic-correction.json",result)
    event("V8_N2_conditional_corrected_Dev_only",eligible=result["gate"]["eligible"],triggered=result["triggered"])


if __name__=="__main__":
    run()
