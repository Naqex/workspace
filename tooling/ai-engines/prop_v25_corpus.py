"""Rank source-bound structural candidates without looking at market outcomes."""
from collections import Counter,defaultdict
from pathlib import Path
from prop_v25_common import *
from quant_core.native_paths import read_bounded, PathGuard
from quant_core.corpus_funnel import classify
from quant_core.bot_lab import SOURCE
import hashlib


def run(version=1):
    inventory = unpack("inventory-and-profiles")
    aliases = defaultdict(list)
    for row in inventory["rows"]:
        aliases[row["profile"]].append(row["path"])
    guard, classified, drifts = PathGuard(), [], []
    for key, profile in inventory["profiles"].items():
        paths = sorted(aliases[key], key=lambda p:(len(p),p))
        text = None
        chosen = paths[0]
        if profile["format"] in SOURCE:
            for path in paths:
                try:
                    raw = read_bounded(path,1048576,guard=guard)
                    if hashlib.sha256(raw).hexdigest() != profile["sha256"]:
                        drifts.append(path)
                        continue
                    text = raw.decode("utf-16" if raw.startswith((b"\xff\xfe",b"\xfe\xff")) else "utf-8-sig")
                    chosen = path
                    break
                except (OSError, ValueError, UnicodeError):
                    continue
        result = classify(profile, text, chosen)
        classified.append(dict(key=key, sha256=profile["sha256"], format=profile["format"],
                               path=chosen, aliases=paths, **result))
    clean = [r for r in classified if r["status"]=="CLEAN_STRUCTURAL_CANDIDATE"]
    # Fully deterministic, economic-outcome-free ranking. Duplicate oscillator
    # variants are not counted as independent mechanisms for research admission.
    clean.sort(key=lambda r:(-int("InpPeriodRSI" in r.get("defaults",{})),
                             -int("InpDuration" in r.get("defaults",{})),
                             -len(r["indicators"]),Path(r["path"]).name.casefold(),r["sha256"]))
    top = clean[:10]
    selected = next((r for r in top if Path(r["path"]).name.casefold()=="bullishbearish engulfing rsi.mq5"),None)
    suffix="" if version==1 else "-v2"
    compressed("corpus-classification"+suffix,dict(rows=classified, source_hash_drifts=drifts,
        source_sha256=sha(__file__),classifier_sha256=sha("tooling/ai-engines/quant_core/corpus_funnel.py"),
        scope="structural heuristics under declared defaults, not full control-flow proof"))
    summary = dict(profiles=len(classified), unique_sha256=len({r["sha256"] for r in classified}),
        formats=dict(Counter(r["format"] for r in classified)),
        statuses=dict(Counter(r["status"] for r in classified)),
        overlapping_flags=dict(Counter(f for r in classified for f in set(r["flags"]))),
        clean_structural=len(clean), top10=top, chosen_mechanisms=[selected] if selected else [],
        mechanism_count=int(selected is not None), source_hash_drift_count=len(drifts),
        binary_clean_claims=0, ranking_uses_PnL=False,
        full_strategy_execution_or_broker_safety_certified=False)
    save("corpus-funnel-summary"+suffix+".json",summary)
    event("corpus_complete",profiles=len(classified),clean=len(clean),selected=Path(selected["path"]).name if selected else None)
    return summary


if __name__=="__main__":
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument("--version",type=int,choices=(1,2),default=1)
    run(parser.parse_args().version)
