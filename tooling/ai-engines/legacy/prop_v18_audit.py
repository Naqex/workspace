"""Independent Decimal ledger replay on copied source-clock quote blocks."""
import numpy as np
from prop_v18_blocks import STRIDE
from prop_v18_costs import FrictionOracle


def audit_path(tape, sequence, expected):
    master = []
    for slot, (index, shift) in enumerate(sequence):
        trades = tape.prepared(index, shift, slot)
        master.extend([None] * max(0, len(trades) - len(master)))
        master[slot * STRIDE:] = trades[slot * STRIDE:]
    oracle = FrictionOracle(expected, [t if t is not None else {} for t in master])
    def event_key(row):
        close = next((c for c in reversed(expected["closed"]) if c["at"] == row["at"]), None)
        if close is None:
            return row["at"], -1, -1
        t = dict(master[close["trade"]], **close.get("execution_override", {}))
        return row["at"], 0 if t["asset"] == "XAUUSD" else 1, t["exit_quote_index"]
    passes = {event_key(r): r for r in expected["phase_passes"]}
    rewards = {event_key(r): r for r in expected["payouts"]}
    forced = {}
    for c in expected["closed"]:
        if c.get("execution_override"):
            t = master[c["trade"]]
            v = c["execution_override"]
            key = (v["exit_msc"], 0 if t["asset"] == "XAUUSD" else 1, v["exit_quote_index"])
            forced.setdefault(key, []).append(c["trade"])
    processed = set()

    def follow(key, quote):
        if key in passes:
            oracle.action("pass", None, key[0], quote, passes.pop(key))
        if key in rewards:
            reward = rewards.pop(key)
            try:
                oracle.action("reward", None, key[0], quote, reward)
            except ValueError as exc:
                raise ValueError("V18_reward_context:" + str(dict(
                    key=key, phase=oracle.phase, cash=oracle.cash, opened=oracle.open,
                    first_funded=oracle.first_funded, last_reward=oracle.last_reward,
                    reward=reward, start=expected["start_msc"]))) from exc

    def consume(rows):
        if not len(rows):
            return
        # Claimed next-observation fills must not skip an earlier same-asset quote.
        for i, (after, _) in oracle.pending.items():
            asset = 0 if oracle.trades[i]["asset"] == "XAUUSD" else 1
            if np.any((rows["src"] == asset) & (rows["t"] > after)):
                raise ValueError("V18_audit_skipped_pending_next_quote")
        oracle.segment(rows, {})

    def visit(kind, payload, trades, slot):
        if kind == "segment":
            rows = payload[(payload["t"] >= expected["start_msc"]) & (payload["t"] < expected["end_msc"])]
            if not len(rows) or oracle.breach:
                return
            events = sorted(k for k in forced if k not in processed
                            and int(rows["t"][0]) <= k[0] <= int(rows["t"][-1]))
            start = 0
            for key in events:
                found = np.flatnonzero((rows["t"] == key[0]) & (rows["src"] == key[1])
                                       & (rows["ordinal"] == key[2]))
                if not len(found):
                    continue
                j = int(found[0])
                consume(rows[start:j])
                oracle.point(key[0], rows[j])
                for i in forced[key]:
                    oracle.action("exit", i, key[0], rows[j])
                follow(key, rows[j])
                processed.add(key)
                start = j
            consume(rows[start:])
        else:
            op, at, quote = payload
            if not expected["start_msc"] <= at < expected["end_msc"] or oracle.breach:
                return
            if op["precheck"]:
                oracle.point(at, quote)
            key = (at, quote["src"], quote["ordinal"]) if op["precheck"] else (at, -1, -1)
            lifecycle_done = False
            for action, i in op["actions"]:
                if action == "entry" and not lifecycle_done:
                    follow(key, quote)
                    lifecycle_done = True
                identity = i + slot * STRIDE if i is not None else None
                oracle.action(action, identity, at, quote)
            if not lifecycle_done:
                follow(key, quote)

    for slot, (index, shift) in enumerate(sequence):
        tape.walk(index, shift, slot, [], visit=visit)
    if passes or rewards or set(forced) != processed:
        raise ValueError("V18_audit_unprocessed_lifecycle_event")
    return oracle.finish()
