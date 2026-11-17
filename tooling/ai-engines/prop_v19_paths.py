"""Causal pre-entry continuity and next-quote timeout exits; no hindsight flat."""
from collections import Counter
import numpy as np
from prop_v19_common import *
from prop_v16_paths import core_inputs, load as parent_load
from prop_v15_paths import insert_excursions, patch_plan, bind_quotes
from prop_v14_paths import build, M1ScenarioQuotes
from quant_core.gap_aware_execution import GapAwarePathIndex
from quant_core.prop_lifecycle_and_parity import bindings

MINUTE = 60000
HOUR = 3600000


def preceding_continuity(times, decision, schedule, asset, minutes=30):
    required = [at for at in range(decision // MINUTE * MINUTE - minutes * MINUTE,
                                  decision // MINUTE * MINUTE, MINUTE)
                if schedule.off_kind(at, asset) is None]
    if not required:
        return False
    positions = times.searchsorted(required)
    return bool(np.all(positions < len(times)) and np.array_equal(times[positions], required))


def timeout_request(gaps, entry, deadline):
    requests = [g["before"] + 3 * MINUTE for g in gaps if g["source_uncertain"] and
                entry <= g["before"] and g["before"] + 3 * MINUTE < g["after"] and
                g["before"] + 3 * MINUTE < deadline]
    return min(requests) if requests else None


def make(tag, dev, strict=False):
    stage = "Dev" if dev else "Full"
    mode = "STRICT" if strict else "PRIMARY"
    end = DEV_END if dev else END
    _, bars, schedule, ms, lookup, parent_skips = core_inputs(dev)
    rejected, requested = [], {}
    for identity, m in ms.items():
        asset = m["asset"]
        ix = m["_index"]
        for i, (decision, entry, deadline) in enumerate(zip(m["at"], m["entry_at"], m["deadline"])):
            if not preceding_continuity(bars[asset]["t"], int(decision), schedule, asset):
                m["admitted"][i] = False
                rejected.append(dict(id=identity, event=i, decision=int(decision), reason="PRECEDING_M1_DISCONTINUITY"))
            request = timeout_request(ix.gaps, int(entry), int(deadline))
            if request is not None:
                m["deadline"][i] = request
                requested[(identity, i)] = request
    plan = []
    if strict:
        primary = read(JOB / f"{stage}-{tag}-PRIMARY-trades.json")
        for asset, b in bars.items():
            ix = GapAwarePathIndex(b, asset=asset, schedule=schedule)
            for t in primary:
                if t["asset"] != asset:
                    continue
                for g in ix.gaps:
                    if not g["source_uncertain"] or not (g["after"] > t["entry_msc"] and g["before"] < t["exit_msc"]):
                        continue
                    at = next(v for v in range(g["before"] + MINUTE, g["after"], MINUTE)
                              if schedule.off_kind(v, asset) is None)
                    level = t["protection_price"] if t["activation_time"] is not None and t["activation_time"] <= at else t["stop_units"]
                    plan.append(dict(asset=asset, id=t["id"], entry=t["entry_msc"], exit=t["exit_msc"],
                        side=1 if t["side"] == "BUY" else -1, level=level, before=g["before"], after=g["after"],
                        source_uncertain=True, first_unknown=at, screen=dict(status="AMBIGUOUS")))
        plan = patch_plan(plan, "ALL_UNCERTIFIED")
        bars = {a: insert_excursions(b, plan, a, end)[0] for a, b in bars.items()}
        for m in ms.values():
            m["_index"] = GapAwarePathIndex(bars[m["asset"]], asset=m["asset"], schedule=schedule)
    import prop_v14_paths as parent
    with bindings(parent, END=end):
        trades, readers, missing = build(ms, "OPEN_LOW_HIGH_CLOSE" if tag == "OLHC" else "OPEN_HIGH_LOW_CLOSE", bars)
    if missing:
        raise ValueError("V19_unresolved_entry_or_path:" + str(missing[:3]))
    primary_map = {(t["id"], t["source_event"]): t for t in read(
        JOB / f"{stage}-{tag}-PRIMARY-trades.json")} if strict else {}
    for t in trades:
        before = primary_map.get((t["id"], t["source_event"]), t)["source_uncertain"]
        t.update(original_source_uncertain=before, source_uncertain=before or t["source_uncertain"],
                 feed_timeout_requested_at=requested.get((t["id"], t["source_event"])),
                 broker_certified=False, synthetic_bridge_stress=strict,
                 ex_ante_cutoff=schedule.cutoff(t["entry_msc"], t["asset"]))
    save(f"{stage}-{tag}-{mode}-trades.json", trades)
    save(f"{stage}-{tag}-{mode}-path-receipt.json", dict(
        signals=len(trades), source_uncertain=sum(t["source_uncertain"] for t in trades),
        rejected=rejected, parent_skips=parent_skips, synthetic_patches=plan,
        timeout_requests=[dict(id=k[0], event=k[1], at=v) for k, v in requested.items()],
        last_quote_hindsight_exit=False, added_source_observations=0,
        exits=dict(Counter(t["reason"] for t in trades)), known_session_guard_unchanged=True))
    event("V19_causal_paths", scope=stage, order=tag, source=mode, signals=len(trades),
          rejected=len(rejected), unknown=sum(t["source_uncertain"] for t in trades))
    return trades, readers, bars


def load(tag, dev, strict=False):
    stage, mode = ("Dev" if dev else "Full"), ("STRICT" if strict else "PRIMARY")
    trades = read(JOB / f"{stage}-{tag}-{mode}-trades.json")
    from prop_v15_evidence import bars_for
    bars = {a: bars_for(a, dev) for a in ("XAUUSD", "EURUSD")}
    end = DEV_END if dev else END
    if strict:
        plan = read(JOB / f"{stage}-{tag}-{mode}-path-receipt.json")["synthetic_patches"]
        bars = {a: insert_excursions(b, plan, a, end)[0] for a, b in bars.items()}
    readers = {a: M1ScenarioQuotes(b, "OPEN_LOW_HIGH_CLOSE" if tag == "OLHC" else "OPEN_HIGH_LOW_CLOSE", FIRST, end)
               for a, b in bars.items()}
    ids = list(read(V14 / "candidate-freeze.json")["candidate_A"])
    for t in sorted(trades, key=lambda t: (ids.index(t["id"]), t["source_event"])):
        if t["censored"]:
            continue
        spread = 338 if t["asset"] == "XAUUSD" else 10
        bid = t["exit_price_units"] if t["side"] == "BUY" else t["exit_price_units"] - spread
        readers[t["asset"]].add(t["exit_msc"], bid, bid + spread)
    old = [(t["entry_quote_index"], t["exit_quote_index"]) for t in trades]
    bind_quotes(trades, readers)
    if old != [(t["entry_quote_index"], t["exit_quote_index"]) for t in trades]:
        raise ValueError("V19_event_quote_binding_drift")
    return trades, readers, bars


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tag", choices=("OLHC", "OHLC"), default="OLHC")
    p.add_argument("--full", action="store_true")
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    make(a.tag, not a.full, a.strict)
