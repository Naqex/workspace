"""Calendar repricing only; entry, natural stop and all raw opportunities stay fixed."""
import numpy as np
from prop_v6_paths import ScopedPrices
from prop_v6_signals import Calendar, deadline
from prop_v7_common import *


def readers(order):
    gold = read(PARENT / "attempt-2/binary-manifest.json")
    gold.update(read(V6 / order / "gold-manifest.json"))
    eur = read(V3 / "system-eur-manifest.json")
    eur.update(read(V6 / "eur-manifest.json"))
    return dict(XAUUSD=ScopedPrices(gold, END), EURUSD=ScopedPrices(eur, END))


def reprice(trades, sources, calendar):
    result, changes = [], []
    for original in trades:
        t = dict(original)
        # Historical2022-24 calendar/source remains frozen.
        if t["entry_msc"] < FINAL:
            result.append(t)
            continue
        end, why = deadline(t, t["entry_msc"], calendar)
        source = sources[t["asset"]]
        final = source.endpoint(end) if end < END else None
        if end < END and (final is None or final[0] >= END):
            raise ValueError("V7_unresolved_registered_deadline:" + t["asset"] + ":" + t["day"])
        path, ordinal = source.path(t["entry_msc"], final[0] if final else END - 1)
        px = path["b" if t["side"] == "BUY" else "a"]
        hits = np.flatnonzero((px <= t["stop_units"] if t["side"] == "BUY" else px >= t["stop_units"])
                              & (path["t"] < end))
        if not len(hits) and final is None:
            raise ValueError("V7_true_sample_end_open_exposure:" + t["day"])
        ix = int(hits[0]) if len(hits) else int(path["t"].searchsorted(final[0]))
        reason = "SL" if len(hits) else why
        t.update(deadline_msc=end, exit_msc=int(path["t"][ix]),
                 exit_price_units=int(px[ix]), exit_quote_index=int(ordinal[ix]),
                 reason=reason, calendar_revision="V7",
                 endpoint_wait_ms=int(final[0]) - end if final else None)
        if any(t[k] != original[k] for k in ("entry_msc", "entry_price_units", "stop_units", "side")):
            raise ValueError("V7_entry_or_SL_changed")
        if any(t[k] != original[k] for k in ("deadline_msc", "exit_msc", "exit_price_units", "reason")):
            changes.append(dict(asset=t["asset"], day=t["day"], side=t["side"],
                                before={k: original[k] for k in ("deadline_msc", "exit_msc", "reason")},
                                after={k: t[k] for k in ("deadline_msc", "exit_msc", "reason")}))
        result.append(t)
    return result, changes


def prepare(order):
    verify()
    folder = JOB / order
    folder.mkdir(exist_ok=False)
    original = read(V3 / "system-trades.json") + read(V6 / order / "holdout-trades.json")
    trades, changes = reprice(original, readers(order), Calendar(read(CALENDAR), END))
    if len(trades) != len(original) or any(t["exit_msc"] >= END for t in trades):
        raise ValueError("V7_incomplete_exit")
    write_json(folder / "system-trades.json", trades)
    write_json(folder / "calendar-repricing.json", dict(
        total_trades=len(trades), holdout_trades=sum(t["entry_msc"] >= FINAL for t in trades),
        priced_exits=len(trades), unresolved=0, changes=changes, label=LABEL,
        fixed_entry_stop_and_side=True, source_semantics_unchanged=True))
    event("V7_paths_repaired", order=order, trades=len(trades), repriced=len(changes))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--order", default=ORDERS[0], choices=ORDERS)
    prepare(p.parse_args().order)
