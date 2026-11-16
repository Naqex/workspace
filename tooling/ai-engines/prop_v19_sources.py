"""Bounded V16 gap attribution and refreshed on-disk source probes."""
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from prop_v19_common import *
from prop_v15_evidence import bars_for
from prop_v16_paths import CausalFlatSchedule
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.prop_lifecycle_and_parity import bindings


def gaps():
    trades = read(V16 / "Full-OLHC-PRIMARY-trades.json")
    schedule = CausalFlatSchedule(gold_calendar(FIRST, END).events.values())
    rows, affected = [], []
    for asset in ("XAUUSD", "EURUSD"):
        bars = bars_for(asset)
        index = GapAwarePathIndex(bars, asset=asset, schedule=schedule)
        for t in trades:
            if t["asset"] != asset or not t["source_uncertain"]:
                continue
            crossings = []
            for g in index.gaps:
                if not g["source_uncertain"] or not (
                        g["after"] > t["entry_msc"] and g["before"] < t["exit_msc"]):
                    continue
                at = next(v for v in range(g["before"] + 60000, g["after"], 60000)
                          if schedule.off_kind(v, asset) is None)
                protected = t["activation_time"] is not None and t["activation_time"] <= at
                r = dict(g, asset=asset, id=t["id"], family=t["id"].split("|")[1][:2],
                         entry=t["entry_msc"], exit=t["exit_msc"], side=1 if t["side"] == "BUY" else -1,
                         level=t["protection_price"] if protected else t["stop_units"],
                         protected=protected, first_unknown=at,
                         first_unknown_UTC=datetime.fromtimestamp(at / 1000, timezone.utc).isoformat())
                rows.append(r)
                crossings.append(r)
            affected.append(dict(id=t["id"], source_event=t["source_event"], asset=asset,
                                 side=t["side"], entry_msc=t["entry_msc"], exit_msc=t["exit_msc"],
                                 entry_UTC=datetime.fromtimestamp(t["entry_msc"] / 1000, timezone.utc).isoformat(),
                                 entry_hour_UTC=t["entry_msc"] // 3600000 % 24,
                                 gaps=crossings, reference_R=t["reference"]["SYM"]["net_R"]))
    save("gap-identities.json", dict(rows=rows, affected=affected, total_signals=len(trades),
         affected_trades=len(affected), assets=dict(Counter(t["asset"] for t in affected)),
         sleeves=dict(Counter(t["id"] for t in affected)),
         entry_hours=dict(Counter(t["entry_hour_UTC"] for t in affected)),
         unique_gaps=len({(r["asset"], r["before"], r["after"]) for r in rows}),
         source=sha(V16 / "Full-OLHC-PRIMARY-trades.json"), source_certificates=0))
    event("V19_gap_attribution", signals=len(trades), affected=len(affected), occurrences=len(rows))


def census():
    import prop_v16_sources as previous
    with bindings(previous, JOB=JOB, save=save, event=event):
        previous.census()
    old = {r["path"]: r for r in read(V16 / "raw-source-census.json")["records"]}
    current = read(JOB / "raw-source-census.json")
    changes = [r for r in current["records"] if r["path"] not in old or
               (r["bytes"], r["mtime_ns"]) != (old[r["path"]]["bytes"], old[r["path"]]["mtime_ns"])]
    save("source-census-delta.json", dict(new_or_changed=changes,
         records=len(current["records"]), unchanged=len(current["records"]) - len(changes),
         errors=current["errors"], parent=sha(V16 / "raw-source-census.json"),
         current=sha(JOB / "raw-source-census.json"), any_price_decoded=False))
    event("V19_source_census", records=len(current["records"]), changed=len(changes))


def probes():
    import prop_v16_sources as previous
    with bindings(previous, JOB=JOB, save=save, event=event):
        previous.native_probe()
        previous.csv_probe()
        previous.alternate_probe()
    native = read(JOB / "native-probe.json")
    csv = read(JOB / "csv-gap-probe.json")
    alt = read(JOB / "alternate-tick-probe.json")
    observed = sum(r["quotes_inside"] for r in native["rows"]) + csv["observed_rows"] + alt["observed_rows"]
    # New observations require a separate, source-bound derived admission.
    save("source-probe-verdict.json", dict(observed_rows=observed,
         repair_ready=observed > 0, added_M1=0, continuity_certificates=0,
         higher_timeframe_does_not_reconstruct_first_passage=True,
         no_padding=True, no_new_provider_download=True,
         native_counts=native["counts"], csv_files=csv["files"], alternate_files=alt["files"],
         bindings={n: sha(JOB / n) for n in ("gap-identities.json", "raw-source-census.json",
              "native-probe.json", "csv-gap-probe.json", "alternate-tick-probe.json")}))
    event("V19_source_probe_complete", observed=observed, added_M1=0)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("stage", choices=("gaps", "census", "probes"))
    globals()[parser.parse_args().stage]()
