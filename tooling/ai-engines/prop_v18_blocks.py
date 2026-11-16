"""Full ordered scenario quotes and events, partitioned only at flat quarters."""
from collections import defaultdict
from datetime import datetime, timezone
import numpy as np
from prop_v18_common import *
from prop_v16_paths import load
from prop_v6_replay import clocks
from prop_v5_replay import TAGGED
from prop_portfolio_accounts import joint_hour, ASSETS
from quant_core.ftmo_execution_and_calendar import gold_calendar
from prop_v18_costs import FrictionAccount

HOUR = 3600000
STRIDE = 128
TIME_FIELDS = ("decision_msc", "entry_msc", "exit_msc", "deadline_msc", "activation_time",
               "parent_deadline", "original_exit")


def quarter(at):
    d = datetime.fromtimestamp(at / 1000, timezone.utc)
    return f"{d.year}Q{(d.month - 1) // 3 + 1}"


def boundaries():
    result = []
    for year in range(2018, 2027):
        for month in (1, 4, 7, 10):
            at = int(datetime(year, month, 1, tzinfo=timezone.utc).timestamp() * 1000)
            if at < END:
                result.append(at)
    return result + [END]


def export(tag, strict):
    mode = "STRICT" if strict else "PRIMARY"
    prefix = f"{tag}-{mode}"
    trades, readers, _ = load(tag, False, strict)
    for t in trades:
        if t["entry_msc"] // 86400000 != t["exit_msc"] // 86400000:
            raise ValueError("V18_flat_seam_adapter_requires_intraday")
        q = readers[t["asset"]].hour(t["entry_msc"] // HOUR * HOUR)[t["entry_quote_index"]]
        t["spread_units"] = int(q["a"]) - int(q["b"])
        q2 = readers[t["asset"]].hour(t["exit_msc"] // HOUR * HOUR)[t["exit_quote_index"]]
        if int(q2["a"]) - int(q2["b"]) != t["spread_units"]:
            raise ValueError("V18_variable_spread_needs_per_exit_cost")
    cuts = boundaries()
    blocks = [dict(id=quarter(a), first=a, end=b, complete=b != END,
                   trades=[], operations=[]) for a, b in zip(cuts, cuts[1:])]
    by_id = {b["id"]: b for b in blocks}
    local = {}
    for i, t in enumerate(trades):
        b = by_id[quarter(t["entry_msc"])]
        if not b["first"] <= t["entry_msc"] <= t["exit_msc"] < b["end"]:
            raise ValueError("V18_cross_quarter_position")
        local[i] = len(b["trades"])
        b["trades"].append(t)
        if len(b["trades"]) >= STRIDE:
            raise ValueError("V18_stride_exhausted")
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        asset = ASSETS.index(t["asset"])
        actions[(t["entry_msc"], asset, t["entry_quote_index"])].append(("entry", i))
        actions[(t["exit_msc"], asset, t["exit_quote_index"])].append(("exit", i))
    for at, kind in clocks(FIRST, END, gold_calendar(FIRST, END)):
        actions[(at, -1, -1)].append((kind, None))
    keys = sorted(actions)
    priority = dict(reset=0, session_flat=1, exit=2, entry=3)
    cursor = count = 0
    last = None
    held = set()
    chunks = []

    def segment(rows, block):
        nonlocal last, count
        if not len(rows):
            return
        last = rows[-1]
        if not held:
            return
        chunks.append(rows.copy())
        block["operations"].append(dict(kind="segment", lo=count, hi=count + len(rows)))
        count += len(rows)

    for hour in range(FIRST, END, HOUR):
        b = by_id[quarter(hour)]
        raw, maps = joint_hour(readers, hour, last)
        rows = np.empty(len(raw), dtype=TAGGED)
        for name in raw.dtype.names:
            rows[name] = raw[name]
        for asset, indices in enumerate(maps):
            rows["src"][indices] = asset
            rows["ordinal"][indices] = np.arange(len(indices))
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            at, asset, index = keys[cursor]
            stop = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][index])
            segment(rows[start:stop], b)
            if asset >= 0:
                last = rows[stop]
            quote = {n: int(last[n]) for n in TAGGED.names} if last is not None else {n: 0 for n in TAGGED.names}
            ops = []
            for kind, i in sorted(actions[keys[cursor]], key=lambda a: priority[a[0]]):
                ops.append([kind, local[i] if i is not None else None])
                if kind == "entry":
                    held.add(i)
                elif kind == "exit":
                    held.remove(i)
            b["operations"].append(dict(kind="action", at=at, precheck=asset >= 0, quote=quote, actions=ops))
            start = stop
            cursor += 1
        segment(rows[start:], b)
        if hour + HOUR in cuts and held:
            raise ValueError("V18_nonflat_block_boundary")
        if hour % (5000 * HOUR) == 0:
            event("V18_extract", order=tag, mode=mode, hour=hour, retained_quotes=count)
    if cursor != len(keys) or held:
        raise ValueError("V18_unconsumed_events")
    p = JOB / f"{prefix}-quotes.npy"
    values = np.concatenate(chunks) if chunks else np.empty(0, dtype=TAGGED)
    with p.open("xb") as f:
        np.save(f, values)
    for b in blocks:
        b["source_unknown_trades"] = sum(t["source_uncertain"] for t in b["trades"])
        b["reference_SYM_R"] = sum(t["reference"]["SYM"]["net_R"] for t in b["trades"])
    save(f"{prefix}-blocks.json", dict(blocks=blocks, quote_path=str(p), quote_sha256=sha(p),
         trades=len(trades), retained_quotes=count, raw_M1_scenario_not_tick_feed=True,
         all_source_trade_events_preserved=True, no_swap=True, no_hard_TP=all(t["reason"] != "TP" for t in trades),
         quote_order_preserved=True, flat_boundaries=True, no_daily_PnL_aggregation=True))
    event("V18_blocks_exported", order=tag, mode=mode, trades=len(trades), quotes=count)


class BlockTape:
    def __init__(self, tag, mode):
        self.meta = read(JOB / f"{tag}-{mode}-blocks.json")
        if sha(self.meta["quote_path"]) != self.meta["quote_sha256"]:
            raise ValueError("V18_quote_pack_hash")
        # Keep the read-only mapping but avoid memmap subclass work on every field.
        self.quotes = np.asarray(np.load(self.meta["quote_path"], mmap_mode="r"))
        self.blocks = self.meta["blocks"]

    def prepared(self, index, shift, slot):
        b = self.blocks[index]
        trades = [None] * (slot * STRIDE)
        for original in b["trades"]:
            t = dict(original)
            for field in TIME_FIELDS:
                if t.get(field) is not None:
                    t[field] += shift
            trades.append(t)
        return trades

    def walk(self, index, shift, slot, accounts, *, visit=None):
        b = self.blocks[index]
        trades = self.prepared(index, shift, slot)
        for a in accounts:
            a._trades = trades
        for op in b["operations"]:
            if op["kind"] == "segment":
                rows = self.quotes[op["lo"]:op["hi"]]
                if shift:
                    rows = rows.copy()
                    rows["t"] += shift
                if visit is not None:
                    visit("segment", rows, trades, None)
                cache = {}
                for a in accounts:
                    if a.breach:
                        continue
                    if not a.active:
                        # Flat quote excursions cannot change cash/equity or policy.
                        # Reset/session/entry/exit clocks below are still dispatched.
                        continue
                    whole = a.start <= int(rows["t"][0]) and int(rows["t"][-1]) < a.end
                    local = rows if whole else rows[(rows["t"] >= a.start) & (rows["t"] < a.end)]
                    if len(local):
                        a.segment(local, trades, cache if whole else {})
                        a.last_quote = local[-1]
            else:
                at = op["at"] + shift
                quote = dict(op["quote"], t=op["quote"]["t"] + shift)
                if visit is not None:
                    visit("action", (op, at, quote), trades, slot)
                if op["precheck"]:
                    for a in accounts:
                        if a.start <= at < a.end and not a.breach:
                            a.check(at, a.floating(trades, quote))
                            a.observe_policy(at, a.balance + a.floating(trades, quote))
                for kind, i in op["actions"]:
                    identity = i + slot * STRIDE if i is not None else None
                    for a in accounts:
                        a.action(kind, at, identity, trades, quote)
        for a in accounts:
            if not a.breach and a.end >= b["end"] + shift and a.active:
                raise ValueError("V18_seam_drops_open_position")
        return trades


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tag", choices=("OLHC", "OHLC"), required=True)
    p.add_argument("--strict", action="store_true")
    a = p.parse_args()
    export(a.tag, a.strict)
