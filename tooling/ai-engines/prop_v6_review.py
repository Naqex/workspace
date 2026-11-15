"""Alternate rational cash-posted accounting; not an independent person/model."""
from collections import defaultdict
from datetime import datetime, timezone, timedelta
import numpy as np
from prop_portfolio_review import CashOracle, checked_joint_hour, parts
from xau_h1_execution_review import funding
from prop_campaign_accounts import PRAGUE
from prop_v6_common import *
from prop_v6_signals import Calendar
from prop_v6_paths import ScopedPrices


class Oracle(CashOracle):
    def __init__(self, expected, trades):
        expected = dict(expected)
        if expected.get("path_censor"):
            expected["end_msc"] = expected["effective_end_msc"]
        local = [dict(t) for t in trades]
        for closed in expected["closed"]:
            local[closed["trade"]].update(closed.get("execution_override", {}))
        super().__init__(expected, local, expected["cell"], cocore=True, reward_days=14)
        if expected["standalone_funded"]:
            self.phase = 3
        self.frozen = False
        self.harvest = "NORMAL"
        self.requests = {}
        self.dynamic_checked = 0

    def observe(self, at):
        if self.phase != 3 or self.first_funded is None:
            return
        balance = self.realized_balance()
        since = self.last_reward if self.last_reward is not None else self.first_funded
        if balance >= 51000000 and self.harvest != "PROFIT_LOCK_IDLE":
            self.harvest = "PROFIT_LOCK_IDLE"
            self.frozen = True
            for i in self.open:
                self.requests.setdefault(i, (at, "PROFIT_LOCK_IDLE"))
        elif balance >= 50500000 and at >= since + 12 * DAY and self.harvest == "NORMAL":
            self.harvest = "PRE_PAYOUT_FREEZE"
            self.frozen = True

    def entry(self, i, at, quote):
        if self.frozen:
            if i in self.accepted:
                raise ValueError("V6_oracle_harvest_admission")
            self.rejected_checks += 1
            return
        super().entry(i, at, quote)

    def action(self, kind, i, at, quote, extra=None):
        if not self.expected["start_msc"] <= at < self.expected["end_msc"] or self.breach:
            return
        if kind == "session_flat":
            self.observe(at)
            if self.harvest == "PRE_PAYOUT_FREEZE":
                for k in self.open:
                    self.requests.setdefault(k, (at, "PRE_PAYOUT_SESSION_CLOSE"))
            return
        if kind == "exit" and i in self.open:
            closed = self.closed[i]
            override = closed.get("execution_override")
            if override:
                if i not in self.requests or self.requests[i][1] != override["reason"]:
                    raise ValueError("V6_oracle_unrequested_dynamic_exit")
                self.dynamic_checked += 1
            self.requests.pop(i, None)
        super().action(kind, i, at, quote, extra)
        if kind == "reward":
            self.harvest = "NORMAL"
            self.frozen = False
            self.requests.clear()
        self.observe(at)

    def finish(self):
        e = self.expected
        for value, field in ((self.dd, "peak_dd_pct"), (self.daily, "worst_daily_loss_pct"),
                             (self.static, "static_loss_pct")):
            if abs(value - e[field] * 500000) > 1e-6:
                raise ValueError("V6_oracle_metric:" + field)
        expected_open = {r["trade"]: r["quantity"] for r in e.get("open_positions", [])}
        if (self.open != expected_open or self.phase != e["phase"] or
                abs(self.realized_balance() - e["balance_usd"] * 1000) > 1e-6 or
                bool(self.breach) != bool(e["first_breach"])):
            raise ValueError("V6_oracle_terminal_state")
        if e.get("path_censor"):
            witness = e["path_censor"]
            t = self.trades[witness["trade"]]
            if (witness["trade"] not in self.open or t.get("reason") != "ENDPOINT_UNKNOWN_OPEN"
                    or witness["at"] != t["deadline_msc"]):
                raise ValueError("V6_oracle_invalid_censor_witness")
        return dict(start=e["start_msc"], model=self.model, phase=self.phase,
                    standalone=e["standalone_funded"], accepted=self.entry_checks,
                    rejected=self.rejected_checks, costs=self.money_checks,
                    phase_events=self.phase_checks, rewards=self.reward_checks,
                    dynamic_fills=self.dynamic_checked, cash_bridge=True,
                    dd_milli_usd=self.dd, daily_milli_usd=self.daily, static_milli_usd=self.static,
                    path_censor=e.get("path_censor"))


def clocks(first, end, calendar):
    # Independent local-date enumeration, including the final local midnight.
    d = datetime.fromtimestamp(first / 1000, timezone.utc).date()
    last = datetime.fromtimestamp(end / 1000, timezone.utc).date() + timedelta(days=1)
    while d <= last:
        at = int(datetime(d.year, d.month, d.day, tzinfo=PRAGUE).timestamp() * 1000)
        if first <= at < end:
            yield at, "reset"
        record = calendar.events.get(d.isoformat(), {})
        if d.weekday() < 5 and record.get("kind") != "CLOSED":
            clock = record.get("flat_utc") or "20:30"
            at = int(datetime(d.year, d.month, d.day, tzinfo=timezone.utc).timestamp() * 1000)
            at += (int(clock[:2]) * 60 + int(clock[3:])) * 60000
            if first <= at < end:
                yield at, "session_flat"
        d += timedelta(days=1)


def check_next_quote(reader, requested, t):
    for h in range(requested // HOUR * HOUR, t["exit_msc"] // HOUR * HOUR + 1, HOUR):
        if h not in reader.files:
            continue
        a = reader.hour(h)
        j = int(a["t"].searchsorted(requested, side="right"))
        if j < len(a):
            field = "b" if t["side"] == "BUY" else "a"
            if (int(a["t"][j]) != t["exit_msc"] or j != t["exit_quote_index"] or
                    int(a[field][j]) != t["exit_price_units"]):
                raise ValueError("V6_dynamic_exit_not_next_source_quote")
            return
    raise ValueError("V6_dynamic_exit_quote_absent")


def run(expected, trades, readers, end, first=START):
    cases = [Oracle(c, trades) for c in expected]
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        if first <= t["entry_msc"] < end:
            actions[(t["entry_msc"], 0 if t["asset"] == "XAUUSD" else 1,
                     t["entry_quote_index"])].append(("entry", i, None, None))
    for j, case in enumerate(cases):
        for i in case.accepted:
            t = case.trades[i]
            if first <= t["exit_msc"] < end and t["exit_quote_index"] >= 0:
                actions[(t["exit_msc"], 0 if t["asset"] == "XAUUSD" else 1,
                         t["exit_quote_index"])].append(("exit", i, j, None))
            for at, _ in funding(t["entry_msc"], min(t["exit_msc"], end - 1)):
                if first <= at < end:
                    actions[(at, -1, -1)].append(("swap", i, j, None))
        for kind, field in (("pass", "phase_passes"), ("reward", "payouts")):
            for p in case.expected[field]:
                if not first <= p["at"] < end:
                    continue
                c = next((r for r in case.expected["closed"] if r["at"] == p["at"]), None)
                t = case.trades[c["trade"]] if c else None
                key = (p["at"], 0 if t["asset"] == "XAUUSD" else 1,
                       t["exit_quote_index"]) if t else (p["at"], -1, -1)
                actions[key].append((kind, None, j, p))
    for at, kind in clocks(first, end, Calendar(read(CALENDAR), END)):
        actions[(at, -1, -1)].append((kind, None, None, None))
    priority = dict(reset=0, swap=1, session_flat=2, exit=3, **{"pass": 4}, reward=5, entry=6)
    keys = sorted(actions)
    cursor = 0
    last = None
    total = 0

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache = {}
        for c in cases:
            if c.expected["start_msc"] <= int(rows["t"][0]) and int(rows["t"][-1]) < c.expected["end_msc"]:
                c.segment(rows, cache)
        last = rows[-1]

    for hour in range(first // HOUR * HOUR, end, HOUR):
        rows, maps = checked_joint_hour(readers, hour, last)
        total += len(rows)
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            at, asset, index = keys[cursor]
            stop = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][index])
            consume(rows[start:stop])
            if asset >= 0:
                last = rows[stop]
                for c in cases:
                    if c.expected["start_msc"] <= at < c.expected["end_msc"]:
                        c.point(at, last)
            for kind, i, j, p in sorted(actions[keys[cursor]], key=lambda x: priority[x[0]]):
                for c in cases if j is None else [cases[j]]:
                    if kind == "exit" and i in c.requests and "execution_override" in c.closed[i]:
                        check_next_quote(readers[c.trades[i]["asset"]], c.requests[i][0], c.trades[i])
                    c.action(kind, i, at, last, p)
            start = stop
            cursor += 1
        consume(rows[start:])
        if hour % (1000 * HOUR) == 0:
            event("V6_alternate_oracle", accounts=len(cases), hour=hour, quote_updates=total)
    records = [c.finish() for c in cases]
    return dict(status="PASS", records=records, accounts=len(cases), quote_updates=total,
                accepted=sum(r["accepted"] for r in records), rejected=sum(r["rejected"] for r in records),
                costs=sum(r["costs"] for r in records), dynamic_fills=sum(r["dynamic_fills"] for r in records),
                same_implementer_alternate_arithmetic=True)


def historical():
    trades = read(V3 / "system-trades.json")
    readers = dict(XAUUSD=ScopedPrices(read(PARENT / "attempt-2/binary-manifest.json"), FINAL),
                   EURUSD=ScopedPrices(read(V3 / "system-eur-manifest.json"), FINAL))
    rows = read(JOB / "standalone-funded-accounts.json")
    result = run(rows, trades, readers, FINAL)
    write_json(JOB / "standalone-accounting-parity.json", result)
    event("V6_standalone_oracle_PASS", accounts=len(rows))


def continuation(order):
    folder = JOB / order
    trades = read(folder / "system-trades.json")
    gold = read(PARENT / "attempt-2/binary-manifest.json")
    gold.update(read(folder / "gold-manifest.json"))
    eur = read(V3 / "system-eur-manifest.json")
    eur.update(read(JOB / "eur-manifest.json"))
    readers = dict(XAUUSD=ScopedPrices(gold, END), EURUSD=ScopedPrices(eur, END))
    rows = read(folder / "continuous-accounts.json") + read(folder / "fresh-accounts.json")
    result = run(rows, trades, readers, END)
    write_json(folder / "accounting-parity.json", result)
    event("V6_continuous_oracle_PASS", scenario=order, accounts=len(rows))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("historical", "continuation"))
    p.add_argument("--order", default="OPEN_LOW_HIGH_CLOSE")
    a = p.parse_args()
    historical() if a.stage == "historical" else continuation(a.order)
