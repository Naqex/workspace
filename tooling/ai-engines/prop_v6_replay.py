"""One chronological traversal, scoped calendars and resumable V6 account state."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np
from prop_campaign_accounts import PRAGUE
from prop_portfolio_accounts import joint_hour, ASSETS
from xau_h1_stage0_scan import funding_events
from prop_v5_replay import TAGGED, session_clock
from prop_v6_common import START, HOUR, event


def clocks(first, end, calendar):
    day = datetime.fromtimestamp(first / 1000, timezone.utc).replace(hour=0, minute=0, second=0)
    # A Prague midnight can fall on the previous UTC day. Include the next
    # local date so the sample's final UTC evening reset is not omitted.
    while int(day.timestamp() * 1000) < end + 24 * HOUR:
        at = int(day.astimezone(PRAGUE).replace(hour=0, minute=0, second=0).timestamp() * 1000)
        if first <= at < end:
            yield at, "reset"
        if day.weekday() < 5:
            clock = session_clock(calendar.events.get(day.date().isoformat(), {}))
            if clock:
                at = int(day.timestamp() * 1000) + (int(clock[:2]) * 60 + int(clock[3:])) * 60000
                if first <= at < end:
                    yield at, "session_flat"
        day += timedelta(days=1)


def replay(trades, readers, accounts, end, calendar, first=START):
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        asset = ASSETS.index(t["asset"])
        if first <= t["entry_msc"] < end:
            actions[(t["entry_msc"], asset, t["entry_quote_index"])].append(("entry", i, 0))
        if first <= t["exit_msc"] < end and t["exit_quote_index"] >= 0:
            actions[(t["exit_msc"], asset, t["exit_quote_index"])].append(("exit", i, 0))
        for f in funding_events(t["entry_msc"], min(t["exit_msc"], end - 1)):
            if first <= f["at"] < end:
                actions[(f["at"], -1, -1)].append(("swap", i, f["multiplier"]))
    for at, kind in clocks(first, end, calendar):
        actions[(at, -1, -1)].append((kind, None, 0))
    priority = dict(reset=0, swap=1, session_flat=2, exit=3, entry=4)
    keys = sorted(actions)
    cursor = 0
    last = None
    total = 0
    for a in accounts:
        a._trades = trades

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache = {}
        for a in accounts:
            if a.start <= int(rows["t"][0]) and int(rows["t"][-1]) < a.end:
                a.segment(rows, trades, cache)
        last = rows[-1]

    for hour in range(first // HOUR * HOUR, end, HOUR):
        raw, maps = joint_hour(readers, hour, last)
        rows = np.empty(len(raw), dtype=TAGGED)
        for name in raw.dtype.names:
            rows[name] = raw[name]
        for asset, indices in enumerate(maps):
            rows["src"][indices] = asset
            rows["ordinal"][indices] = np.arange(len(indices))
        total += len(rows)
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            at, asset, index = keys[cursor]
            stop = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][index])
            consume(rows[start:stop])
            if asset >= 0:
                if stop >= len(rows) or int(rows["t"][stop]) != at:
                    raise ValueError("V6_action_quote_binding")
                last = rows[stop]
                for a in accounts:
                    if a.start <= at < a.end and not a.breach:
                        a.check(at, a.floating(trades, last))
                        a.observe_policy(at, a.balance + a.floating(trades, last))
            for kind, i, mult in sorted(actions[keys[cursor]], key=lambda x: priority[x[0]]):
                for a in accounts:
                    a.action(kind, at, i, trades, last, mult)
            start = stop
            cursor += 1
        consume(rows[start:])
        if hour % (1000 * HOUR) == 0:
            event("V6_replay", hour=hour, accounts=len(accounts), quote_updates=total)
    if cursor != len(keys):
        raise ValueError("V6_unprocessed_actions")
    for a in accounts:
        if a.active and last is not None and not a.breach:
            a.check(end - 1, a.floating(trades, last))
    return [dict(a.dump(), joint_quote_updates=total) for a in accounts]
