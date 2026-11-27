"""Fixed sleeve ablation/conditioning; no weighting or threshold search."""

import numpy as np


def weakest_sleeve(rows):
    ids = sorted({r["id"] for r in rows})
    if not ids or any(not 2018 <= r["year"] <= 2023 for r in rows):
        raise ValueError("Dev-only sleeve selection")
    return min(
        ids,
        key=lambda identity: (
            sum(r["net_R"] for r in rows if r["id"] == identity) / sum(r["id"] == identity for r in rows),
            identity,
        ),
    )


def admitted(trade, ratio, profile):
    name = profile["name"]
    if name == "A1_DROP_WEAKEST":
        return trade["id"] != profile["drop_id"]
    if name not in ("A2_F3_EXHAUSTION90", "A2_F4_EXHAUSTION90"):
        raise ValueError("Unregistered sleeve ablation")
    family = "F3" if name == "A2_F3_EXHAUSTION90" else "F4"
    if "|" + family + ":" not in trade["id"]:
        return True
    return bool(ratio is not None and np.isfinite(ratio) and ratio <= 0.9)


def filter_blocks(blocks, decisions):
    """Retain all quote offsets/clocks/prechecks while removing rejected trades."""
    out = []
    for block in blocks:
        mapping = {i: None for i in range(len(block["trades"]))}
        kept = []
        for i, t in enumerate(block["trades"]):
            key = f"{t['id']}@{t['entry_msc']}"
            if key not in decisions:
                raise ValueError("Missing causal admission decision")
            if decisions[key]:
                mapping[i] = len(kept)
                kept.append(t)
        ops = []
        for op in block["operations"]:
            if op["kind"] == "segment":
                ops.append(op)
                continue
            actions = []
            for action, i in op["actions"]:
                if i is None:
                    actions.append([action, None])
                elif mapping[i] is not None:
                    actions.append([action, mapping[i]])
            ops.append(dict(op, actions=actions))
        out.append(dict(block, trades=kept, operations=ops))
    return out
