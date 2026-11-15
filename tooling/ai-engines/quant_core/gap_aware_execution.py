"""Owner-declared next-quote scenario, with missing-source uncertainty preserved."""
from collections import Counter
import numpy as np
from quant_core.vectorized_sl_active_kernel import PathIndex, replay, money


class GapAwarePathIndex(PathIndex):
    def __init__(self, bars, *, asset, schedule):
        super().__init__(bars, asset=asset, closed_days=[
            d for d, r in schedule.events.items() if r["kind"] == "CLOSED"])
        self.schedule = schedule
        unknown = np.zeros(len(bars), dtype="int64")
        self.gaps = []
        for old in self.audit["gap_records"]:
            first, after = old["before"]+self.step, old["after"]
            kinds = Counter(schedule.off_kind(t, asset) or "UNCLASSIFIED_SOURCE_GAP"
                            for t in range(first, after, self.step))
            row = dict(old, minutes_by_kind=dict(kinds),
                       source_uncertain=bool(kinds["UNCLASSIFIED_SOURCE_GAP"]))
            self.gaps.append(row)
            unknown[int(bars["t"].searchsorted(after))] = row["source_uncertain"]
        self.source_bad_prefix = np.cumsum(unknown)
        # complete() is used by the inherited execution kernel, not a source-quality certificate.
        self.bad_prefix = np.zeros(len(bars), dtype="int64")
        self.audit = dict(self.audit, gap_records=self.gaps,
            source_uncertain_gaps=int(unknown.sum()), policy=schedule.version,
            disclosure="deterministic next-quote scenario; missing extrema remain unknown")

    def source_complete(self, starts, exits):
        return self.source_bad_prefix[exits] == self.source_bad_prefix[starts]


def replay_gap_aware(index, m, mode):
    if index.step != 60000:
        raise ValueError("V13_M1_scope_only")
    b = index.bars
    original = np.asarray(m["deadline"])
    scheduled = np.array([index.schedule.target(int(e), int(d), index.asset)
                          for e, d in zip(m["entry_at"], original)], dtype="int64")
    next_indices = b["t"].searchsorted(scheduled)
    safe = np.minimum(next_indices, len(b)-1)
    available = next_indices < len(b)
    # Unknown gaps defer to a future observed open, never to a hindsight last quote.
    effective = np.where(available, b["t"][safe], scheduled)
    run = dict(m, deadline=effective)
    result = replay(index, run, mode)
    result["valid"] &= available | (result["reason"] != "HORIZON")
    end = result["reason"] == "HORIZON"
    level = np.asarray(m["stop"]).copy()
    protected = ((result["activation_index"] >= 0) &
                 (b["t"][np.maximum(result["activation_index"], 0)]+index.step <= effective))
    if mode == "P1":
        level = np.where(protected, result["protection_price"], level)
    side = np.asarray(m["side"])
    # At a time-close open, only the open is known; no endpoint high/low is read.
    crossed = end & np.where(side == 1, result["exit_price"] <= level, result["exit_price"] >= level)
    result["reason"][crossed] = np.where(protected[crossed], "PROTECT", "SL")
    starts, exits = result["entry_index"], result["exit_index"]
    active_level = np.where((mode == "P1") & (result["reason"] == "PROTECT"),
                            result["protection_price"], m["stop"])
    opening = np.where(side == 1, b["bo"][exits], b["ao"][exits])
    open_stop = np.isin(result["reason"], ["SL", "PROTECT"]) & np.where(
        side == 1, opening <= active_level, opening >= active_level)
    result["exit_at"][open_stop] = b["t"][exits[open_stop]]
    result["source_uncertain"] = ~index.source_complete(starts, exits)
    result["path_gap"] = result["source_uncertain"].copy()
    result["scheduled_deadline"] = scheduled
    result["effective_deadline"] = effective
    result["original_deadline"] = original
    result["deferred_endpoint"] = effective > scheduled
    result["endpoint_open_stop"] = crossed
    result["open_stop"] = open_stop
    result["evidence"] = np.where(result["source_uncertain"], "DECLARED_NEXT_QUOTE_SCENARIO",
                                 "SOURCE_OBSERVED_OR_SCHEDULED")
    for model in ("SYM", "ASYM"):
        v = money(index.asset, model, side, m["entry_price"], result["exit_price"],
                  m["entry_at"], result["exit_at"], result["reason"])
        v["net_R"] = np.divide(v["net"], m["natural"], out=np.zeros(len(side)),
                               where=np.asarray(m["natural"]) > 0)
        result["model"][model] = v
    return result
