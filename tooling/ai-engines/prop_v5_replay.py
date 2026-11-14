"""V5 traversal: source-tagged ticks and deterministic session-close events."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np
from prop_campaign_accounts import PRAGUE
from prop_portfolio_accounts import joint_hour, ASSETS
from xau_h1_stage0_scan import funding_events
from prop_campaign_source import Calendar, CALENDAR
from prop_v5_common import START, HOUR, DAY, event

TAGGED = np.dtype([("t","<i8"),("b0","<i4"),("a0","<i4"),
                  ("b1","<i4"),("a1","<i4"),("src","i1"),("ordinal","<i4")])


def session_clock(record):
    return None if record.get("kind") == "CLOSED" else (record.get("flat_utc") or "20:30")


def replay(trades, readers, accounts, end):
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        asset = ASSETS.index(t["asset"])
        actions[(t["entry_msc"], asset, t["entry_quote_index"])].append(("entry", i, 0))
        actions[(t["exit_msc"], asset, t["exit_quote_index"])].append(("exit", i, 0))
        for f in funding_events(t["entry_msc"], t["exit_msc"]):
            actions[(f["at"], -1, -1)].append(("swap", i, f["multiplier"]))
    day = datetime(2022,1,1,tzinfo=timezone.utc)
    calendar = Calendar(CALENDAR)
    while int(day.timestamp()*1000) < end:
        at = int(day.astimezone(PRAGUE).replace(hour=0,minute=0,second=0).timestamp()*1000)
        if START <= at < end:
            actions[(at,-1,-1)].append(("reset",None,0))
        utc0 = int(day.timestamp()*1000)
        if day.weekday()<5:
            record = calendar.events.get(day.date().isoformat(), {})
            clock = session_clock(record)
            if clock:
                close = utc0+(int(clock[:2])*60+int(clock[3:]))*60000
                actions[(close,-1,-1)].append(("session_flat",None,0))
        day += timedelta(days=1)
    priority=dict(reset=0,swap=1,session_flat=2,exit=3,entry=4)
    keys=sorted(actions); cursor=0; last=None; total=0
    for account in accounts:
        account._trades=trades

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache={}
        for a in accounts:
            if a.start<=int(rows["t"][0]) and int(rows["t"][-1])<a.end:
                a.segment(rows,trades,cache)
        last=rows[-1]

    first=min(t["entry_msc"] for t in trades)//HOUR*HOUR
    for hour in range(first,end,HOUR):
        raw,maps=joint_hour(readers,hour,last)
        rows=np.empty(len(raw),dtype=TAGGED)
        for name in raw.dtype.names:
            rows[name]=raw[name]
        for asset, indices in enumerate(maps):
            rows["src"][indices]=asset
            rows["ordinal"][indices]=np.arange(len(indices))
        total+=len(rows); start=0
        while cursor<len(keys) and keys[cursor][0]<hour+HOUR:
            at,asset,index=keys[cursor]
            stop=int(rows["t"].searchsorted(at)) if asset<0 else int(maps[asset][index])
            consume(rows[start:stop])
            if asset>=0:
                last=rows[stop]
                for a in accounts:
                    if a.start<=at<a.end and not a.breach:
                        a.check(at,a.floating(trades,last))
                        a.observe_policy(at,a.balance+a.floating(trades,last))
            for kind,i,mult in sorted(actions[keys[cursor]],key=lambda x:priority[x[0]]):
                for a in accounts:
                    a.action(kind,at,i,trades,last,mult)
            start=stop;cursor+=1
        consume(rows[start:])
        if hour%(1000*HOUR)==0:
            event("V5_tick_replay",hour=hour,accounts=len(accounts),quote_updates=total)
    return [dict(a.dump(),joint_tick_marks=total) for a in accounts]
