"""V7's scoped traversal reuses native joint quoting and the V6 action ordering."""
from collections import defaultdict
import numpy as np
from prop_v5_replay import TAGGED
from prop_v6_replay import clocks
from prop_portfolio_accounts import joint_hour, ASSETS
from xau_h1_stage0_scan import funding_events
from prop_v7_common import *
from prop_v6_signals import Calendar


def replay(trades, sources, accounts, end=END):
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        asset = ASSETS.index(t["asset"])
        actions[(t["entry_msc"], asset, t["entry_quote_index"])].append(("entry", i, 0))
        actions[(t["exit_msc"], asset, t["exit_quote_index"])].append(("exit", i, 0))
        for f in funding_events(t["entry_msc"], t["exit_msc"]):
            actions[(f["at"], -1, -1)].append(("swap", i, f["multiplier"]))
    for at, kind in clocks(START, end, Calendar(read(CALENDAR), END)):
        actions[(at, -1, -1)].append((kind, None, 0))
    keys = sorted(actions)
    cursor = total = 0
    last = None
    priority = dict(reset=0, swap=1, session_flat=2, exit=3, entry=4)
    for c in accounts:
        c._trades = trades

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache = {}
        for c in accounts:
            if c.start <= int(rows["t"][0]) and int(rows["t"][-1]) < c.end:
                c.segment(rows, trades, cache)
        last = rows[-1]

    for hour in range(START, end, HOUR):
        raw, maps = joint_hour(sources, hour, last)
        rows = np.empty(len(raw), dtype=TAGGED)
        for name in raw.dtype.names:
            rows[name] = raw[name]
        for asset, ix in enumerate(maps):
            rows["src"][ix] = asset
            rows["ordinal"][ix] = np.arange(len(ix))
        total += len(rows)
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            at, asset, ordinal = keys[cursor]
            cut = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][ordinal])
            consume(rows[start:cut])
            if asset >= 0:
                if cut >= len(rows) or int(rows["t"][cut]) != at:
                    raise ValueError("V7_native_quote_action_binding")
                last = rows[cut]
                for c in accounts:
                    if c.start <= at < c.end and not c.breach:
                        c.check(at, c.floating(trades, last))
                        c.observe_policy(at, c.balance + c.floating(trades, last))
            for kind, i, mult in sorted(actions[keys[cursor]], key=lambda x: priority[x[0]]):
                for c in accounts:
                    c.action(kind, at, i, trades, last, mult)
            start = cut
            cursor += 1
        consume(rows[start:])
        if hour % (1000 * HOUR) == 0:
            event("V7_replay", hour=hour, accounts=len(accounts), source_updates=total)
    if cursor != len(keys):
        raise ValueError("V7_unprocessed_actions")
    return [dict(c.dump(), source_updates=total) for c in accounts]


def run(order):
    from prop_v7_accounts import AuditAccount
    from prop_v7_paths import readers
    verify()
    folder = JOB / order
    if (folder / "accounts.json").exists():
        raise ValueError("V7_existing_result_not_overwritten")
    trades = read(folder / "system-trades.json")
    starts = [stamp(f"{y}-{m:02d}-01") for y in (2022, 2023, 2024) for m in range(1, 13)]
    starts += [stamp(f"{y}-{m:02d}-01") for y, months in ((2025, range(1, 13)), (2026, range(1, 10)))
               for m in months]
    accounts = [AuditAccount(at, END, model, rolling=True, policy=policy)
                for policy in POLICIES for model in MODELS for at in starts]
    accounts += [AuditAccount(stamp(f"{y}-01-01"), END, model, rolling=True, standalone=True, policy=policy)
                 for policy in POLICIES for model in MODELS for y in range(2022, 2027)]
    accounts += [AuditAccount(stamp(f"{y}-01-01"), min(stamp(f"{y+1}-01-01"), END), model,
                              policy="GOLD_V4", fixed_risk=150, reference_side=side)
                 for model in MODELS for y in range(2022, 2027) for side in ("BOTH", "BUY", "SELL")]
    result = replay(trades, readers(order), accounts)
    if any(r["open_positions"] and not r["first_breach"] for r in result):
        raise ValueError("V7_pending_or_open_exposure")
    write_json(folder / "accounts.json", result[:342])
    write_json(folder / "funded-accounts.json", result[342:372])
    write_json(folder / "annual-reference.json", result[372:])
    event("V7_lifecycle_complete", order=order, cases=len(result), open_positions=0)


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--order", default=ORDERS[0], choices=ORDERS)
    run(p.parse_args().order)
