"""Alternate cash-posted funding oracle, every V4 admission and closed trade."""
from collections import defaultdict
from datetime import date, datetime, timedelta

from prop_campaign_accounts import PRAGUE
from prop_portfolio_review import CashOracle, checked_joint_hour
from prop_cocore_v4 import JOB, START, FINAL, HOUR, read, write_json, inputs, event
from xau_h1_execution_review import funding


def review():
    trades, readers, _ = inputs(True)
    expected = read(JOB / "validation-accounts.json")
    cases = [CashOracle(c, trades, c["cell"], cocore=True,
                        reward_days=c["reward_interval_days"]) for c in expected]
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        asset = 0 if t["asset"] == "XAUUSD" else 1
        actions[(t["entry_msc"], asset, t["entry_quote_index"])].append(("entry", i, None, None))
        actions[(t["exit_msc"], asset, t["exit_quote_index"])].append(("exit", i, None, None))
        for at, _ in funding(t["entry_msc"], t["exit_msc"]):
            actions[(at, -1, -1)].append(("swap", i, None, None))
    for j, case in enumerate(cases):
        for kind, field in (("pass", "phase_passes"), ("reward", "payouts")):
            for p in case.expected[field]:
                closed = next((c for c in case.expected["closed"] if c["at"] == p["at"]), None)
                if closed:
                    t = trades[closed["trade"]]
                    key = (p["at"], 0 if t["asset"] == "XAUUSD" else 1, t["exit_quote_index"])
                else:
                    key = (p["at"], -1, -1)
                actions[key].append((kind, None, j, p))
    day = date(2022, 1, 1)
    while day < date(2025, 1, 1):
        at = int(datetime(day.year, day.month, day.day, tzinfo=PRAGUE).timestamp() * 1000)
        if START <= at < FINAL:
            actions[(at, -1, -1)].append(("reset", None, None, None))
        day += timedelta(days=1)
    priority = dict(reset=0, swap=1, exit=2, **{"pass": 3}, reward=4, entry=5)
    keys = sorted(actions)
    cursor = 0
    last = None
    quotes = 0

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache = {}
        for case in cases:
            if case.expected["start_msc"] <= int(rows["t"][0]):
                case.segment(rows, cache)
        last = rows[-1]

    first = min(t["entry_msc"] for t in trades) // HOUR * HOUR
    for hour in range(first, FINAL, HOUR):
        rows, maps = checked_joint_hour(readers, hour, last)
        quotes += len(rows)
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            key = keys[cursor]
            at, asset, ordinal = key
            stop = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][ordinal])
            consume(rows[start:stop])
            if asset >= 0:
                last = rows[stop]
                for case in cases:
                    if case.expected["start_msc"] <= at < FINAL:
                        case.point(at, last)
            for kind, i, j, p in sorted(actions[key], key=lambda x: priority[x[0]]):
                for case in (cases if j is None else [cases[j]]):
                    case.action(kind, i, at, last, p)
            start = stop
            cursor += 1
        consume(rows[start:])
        if hour % (1000 * HOUR) == 0:
            event("V4_cash_oracle", quote_updates=quotes, hour=hour, accounts=len(cases))
    records = [c.finish() for c in cases]
    out = dict(status="PASS", accounts=len(records), records=records,
               joint_quote_updates=quotes,
               accepted=sum(r["accepted_checked"] for r in records),
               rejected=sum(r["rejected_checked"] for r in records),
               money_bridges=sum(r["costs_checked"] for r in records),
               rewards=sum(r["rewards_checked"] for r in records),
               same_implementer_alternate_arithmetic=True)
    write_json(JOB / "accounting-parity.json", out)
    event("V4_cash_oracle_passed", accounts=len(records),
          accepted=out["accepted"], rejected=out["rejected"])


if __name__ == "__main__":
    review()
