"""Entry-only exact gate audit on sealed raw cohorts; no historical rewrites."""
from fractions import Fraction
import numpy as np
from prop_v25_common import *
from prop_v14_source import JOB as V14
from prop_v15_evidence import bars_for
from evidence_compaction import EvidenceStore


def frozen_entry_cost_units(asset, entry, spread):
    if asset == "XAUUSD":
        # Historical Stage-0 admission used unrounded entry notional. Native
        # round-trip money rounds commissions separately; do not mix contracts.
        return Fraction(spread + 400) + Fraction(14 * entry, 1000000), 1000
    return Fraction(spread + 9), 100000


def run():
    config = read(V14 / "candidate-freeze.json")
    rows = read(V14 / "development.json")["rows"]
    store = EvidenceStore(V14)
    output = []
    for asset in ("XAUUSD", "EURUSD"):
        bars = bars_for(asset, True)
        archive = store.numpy(V14 / f"{asset}-Dev-paths.npz")
        for identity in [i for i in config["candidate_A"] if i.startswith(asset + "|")]:
            row = next(r for r in rows if r["id"] == identity)
            cell = row["source_cell"]
            take = lambda key: archive[f"{cell}:{key}"]
            times, entry, stop = take("entry_at"), take("entry_price"), take("stop")
            decision, old_ratio, old_friction = take("at"), take("ratio"), take("friction")
            assert np.all((FIRST <= decision) & (decision < DEV_END))
            i = bars["t"].searchsorted(times)
            known = (i < len(bars)) & (bars["t"][np.minimum(i, len(bars)-1)] == times)
            comparisons = []
            for n in np.flatnonzero(known):
                p0, level = int(entry[n]), int(stop[n])
                distance = abs(p0-level)
                spread = int(bars["ao"][i[n]] - bars["bo"][i[n]])
                cost, scale = frozen_entry_cost_units(asset, p0, spread)
                if abs(float(cost)/scale-float(old_friction[n])) > 1e-10:
                    raise ValueError("FROZEN_FRICTION_MODEL_MISMATCH")
                for cap in (12,15):
                    old = bool(old_ratio[n] <= cap/100)
                    exact = distance > 0 and 100*cost <= cap*distance
                    comparisons.append(dict(event=int(n), decision=int(decision[n]), cap=cap,
                                            old=old, exact=exact))
            output.append(dict(id=identity, raw=len(times), entry_known=int(known.sum()),
                caps={str(cap):dict(restored=[r for r in comparisons if r["cap"]==cap and not r["old"] and r["exact"]],
                    newly_rejected=[r for r in comparisons if r["cap"]==cap and r["old"] and not r["exact"]])
                    for cap in (12,15)},
                archive_sha256=store.canonical_sha(V14 / f"{asset}-Dev-paths.npz")))
    save("baseline-exact-cost-membership.json", dict(rows=output,
        source_sha256=sha(__file__), candidate_freeze_sha256=sha(V14/"candidate-freeze.json"),
        source_semantics="same frozen spread + twice unrounded entry notional + market slippage; distinct from native money rounding",
        historical_producers_modified=False, prices2024_2026_read=False))
    print([(r["id"], r["raw"], {k:len(v["restored"]) for k,v in r["caps"].items()}) for r in output])


if __name__ == "__main__":
    run()
