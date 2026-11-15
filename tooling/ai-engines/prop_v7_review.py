"""Alternate cash-posted rational accounting for both V7 policies and references."""
from collections import defaultdict
from datetime import datetime, timezone
from fractions import Fraction as F
import numpy as np
from prop_v6_review import Oracle as HarvestOracle, clocks, check_next_quote
from prop_portfolio_review import parts, cent_milli, checked_joint_hour
from prop_campaign_accounts import PRAGUE
from xau_h1_execution_review import funding
from prop_v6_signals import Calendar
from prop_v7_common import *
from prop_v7_paths import readers


class Oracle(HarvestOracle):
    def measure(self, values, times):
        if self.expected["rolling"]:
            return super().measure(values, times)
        if not len(values):
            return
        eq = values + self.cash - self.basis
        running = np.maximum.accumulate(np.r_[self.peak, eq])[1:]
        self.dd = max(self.dd, int((running - eq).max()))
        self.daily = max(self.daily, self.anchor - int(eq.min()))
        self.static = max(self.static, 50000000 - int(eq.min()))
        self.peak = int(running[-1])

    def entry(self, i, at, quote):
        t = self.trades[i]
        e = self.expected
        accepted = self.accepted.get(i)
        balance = self.realized_balance()
        equity = self.cash + self.gross_point(quote)
        ref = not e["rolling"]
        if not ref:
            # The due-date threshold can be crossed between clock actions;
            # the producer observes it on the entry's native quote as well.
            self.observe(at)
        reason = None
        if e["policy_id"] != "COCORE_FIXED" and t["asset"] != "XAUUSD":
            reason = "DECOMMISSIONED"
        if e["reference_side"] != "BOTH" and t["side"] != e["reference_side"]:
            reason = reason or "REFERENCE_SIDE"
        if self.frozen and not ref:
            reason = reason or "HARVEST"
        if t["decision_msc"] < e["start_msc"] or t["decision_msc"] <= self.gate:
            reason = reason or "PHASE_GATE"
        if not ref and any(self.trades[k]["asset"] == t["asset"] and
                           self.trades[k]["decision_msc"] == t["decision_msc"] for k in self.open):
            reason = reason or "COLLISION"
        if balance - self.anchor <= -1000000:
            self.halt = True
        if self.halt and not ref:
            reason = reason or "DAILY_HALT"
        risk = 150 if ref else ((250, 200, 150) if e["policy_id"] == "GOLD_SCALED"
                               else (200, 175, 125))[self.phase - 1]
        if not ref:
            risk = min(risk, 90) if equity <= 47000000 else min(risk, 150) if equity <= 48000000 else risk
        unit = 1 if t["asset"] == "XAUUSD" else 10
        q = int(risk * 1000) // (unit * abs(t["entry_price_units"] - t["stop_units"]))
        if not 1 <= q <= (5000 if t["asset"] == "XAUUSD" else 100000):
            reason = reason or "LOT"
        oldrisk = sum(size * (1 if self.trades[k]["asset"] == "XAUUSD" else 10) *
                      abs(self.trades[k]["entry_price_units"] - self.trades[k]["stop_units"])
                      for k, size in self.open.items())
        newrisk = q * unit * abs(t["entry_price_units"] - t["stop_units"])
        if not ref and oldrisk + newrisk > 800000:
            reason = reason or "CAP"
        money = parts(t, q, self.model)
        projected = balance - money["fee0"]
        for k, size in list(self.open.items()) + [(i, q)]:
            old = self.trades[k]
            gold = old["asset"] == "XAUUSD"
            sign = 1 if old["side"] == "BUY" else -1
            projected += sign * size * (1 if gold else 10) * (old["stop_units"] - old["entry_price_units"])
            fee = cent_milli(F(old["stop_units"], 1000) * size * F(7, 1000000)) if gold else cent_milli(F(size, 40))
            projected -= fee + size * (400 if gold else 40)
            rate = (-400 if self.model.startswith("SYM") else -450 if old["side"] == "BUY" else -50) if gold else -400
            projected += min(0, rate) * size * sum(m for _, m in funding(old["entry_msc"], old["deadline_msc"]))
        if not ref and (projected <= 46000000 or projected < max(self.anchor - 2500000, 45000000)):
            reason = reason or "RESERVE"
        if bool(accepted) != (reason is None):
            raise ValueError(f"V7_oracle_admission:{i}:{e['policy_id']}:{e['start_msc']}:{reason}")
        if accepted is None:
            self.rejected_checks += 1
            return
        if (accepted["risk_usd"] != risk or accepted["ounces"] != q or accepted["phase"] != self.phase):
            raise ValueError("V7_oracle_policy_quantity")
        if not ref:
            state = accepted["risk_state"]
            for name, value in (("balance_milli_usd", balance), ("equity_milli_usd", equity),
                                ("daily_anchor_milli_usd", self.anchor),
                                ("projected_stop_milli_usd", projected),
                                ("prior_stop_risk_milli_usd", oldrisk), ("new_stop_risk_milli_usd", newrisk)):
                if state[name] != value:
                    raise ValueError("V7_oracle_risk_state:" + name)
        self.open[i] = q
        self.charges[i] = 0
        self.components[i] = money
        asset = 0 if t["asset"] == "XAUUSD" else 2
        buy = t["side"] == "BUY"
        self.coeff[asset if buy else asset + 1] += (1 if buy else -1) * q * unit
        self.basis += (1 if buy else -1) * q * unit * t["entry_price_units"]
        self.cash -= money["fee0"] + money["slip"]
        self.days.add(datetime.fromtimestamp(at / 1000, timezone.utc).astimezone(PRAGUE).date())
        if self.phase == 3 and self.first_funded is None:
            self.first_funded = at
        self.max_stop = max(self.max_stop, oldrisk + newrisk)
        self.entry_checks += 1

    def action(self, kind, i, at, quote, extra=None):
        if self.expected["rolling"]:
            return super().action(kind, i, at, quote, extra)
        if not self.expected["start_msc"] <= at < self.expected["end_msc"]:
            return
        if kind == "reset":
            self.anchor = self.realized_balance()
        elif kind == "entry":
            self.entry(i, at, quote)
        elif kind == "swap" and i in self.open:
            charge = self.components[i]["swaps"][at]
            self.cash += charge
            self.charges[i] += charge
        elif kind == "exit" and i in self.open:
            t = self.trades[i]
            q = self.open.pop(i)
            self.charges.pop(i)
            p = self.components[i]
            asset = 0 if t["asset"] == "XAUUSD" else 2
            unit = 1 if t["asset"] == "XAUUSD" else 10
            sign = 1 if t["side"] == "BUY" else -1
            self.coeff[asset if sign == 1 else asset + 1] -= sign * q * unit
            self.basis -= sign * q * unit * t["entry_price_units"]
            self.cash += p["gross"] - p["fee1"] - p["slip"]
            if abs(self.closed[i]["net_usd"] * 1000 - p["net"]) > 1e-6:
                raise ValueError("V7_reference_cost_bridge")
            self.money_checks += 1
        self.point(at, quote)


def run(order):
    verify()
    folder = JOB / order
    trades = read(folder / "system-trades.json")
    sources = readers(order)
    expected = read(folder / "accounts.json") + read(folder / "funded-accounts.json") + read(folder / "annual-reference.json")
    cases = [Oracle(c, trades) for c in expected]
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        actions[(t["entry_msc"], 0 if t["asset"] == "XAUUSD" else 1, t["entry_quote_index"])].append(("entry", i, None, None))
    for j, c in enumerate(cases):
        for i in c.accepted:
            t = c.trades[i]
            actions[(t["exit_msc"], 0 if t["asset"] == "XAUUSD" else 1, t["exit_quote_index"])].append(("exit", i, j, None))
            for at, _ in funding(t["entry_msc"], t["exit_msc"]):
                actions[(at, -1, -1)].append(("swap", i, j, None))
        for kind, field in (("pass", "phase_passes"), ("reward", "payouts")):
            for p in c.expected[field]:
                row = next((r for r in c.expected["closed"] if r["at"] == p["at"]), None)
                t = c.trades[row["trade"]] if row else None
                key = (p["at"], 0 if t["asset"] == "XAUUSD" else 1, t["exit_quote_index"]) if t else (p["at"], -1, -1)
                actions[key].append((kind, None, j, p))
    for at, kind in clocks(START, END, Calendar(read(CALENDAR), END)):
        actions[(at, -1, -1)].append((kind, None, None, None))
    priority = dict(reset=0, swap=1, session_flat=2, exit=3, **{"pass": 4}, reward=5, entry=6)
    keys = sorted(actions)
    cursor = total = 0
    last = None

    def consume(rows):
        nonlocal last
        if not len(rows):
            return
        cache = {}
        for c in cases:
            if c.expected["start_msc"] <= int(rows["t"][0]) and int(rows["t"][-1]) < c.expected["end_msc"]:
                c.segment(rows, cache)
        last = rows[-1]

    for hour in range(START, END, HOUR):
        rows, maps = checked_joint_hour(sources, hour, last)
        total += len(rows)
        start = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            at, asset, ordinal = keys[cursor]
            cut = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][ordinal])
            consume(rows[start:cut])
            if asset >= 0:
                last = rows[cut]
                for c in cases:
                    if c.expected["start_msc"] <= at < c.expected["end_msc"]:
                        c.point(at, last)
            for kind, i, j, p in sorted(actions[keys[cursor]], key=lambda x: priority[x[0]]):
                for c in cases if j is None else [cases[j]]:
                    if kind == "exit" and i in c.requests and "execution_override" in c.closed[i]:
                        check_next_quote(sources[c.trades[i]["asset"]], c.requests[i][0], c.trades[i])
                    c.action(kind, i, at, last, p)
            start = cut
            cursor += 1
        consume(rows[start:])
        if hour % (1000 * HOUR) == 0:
            event("V7_alternate_accounting", order=order, cases=len(cases), hour=hour)
    records = [c.finish() | dict(policy=c.expected["policy_id"], rolling=c.expected["rolling"],
                               side=c.expected["reference_side"]) for c in cases]
    result = dict(status="PASS", cases=len(cases), records=records, source_updates=total,
                  admissions=sum(r["accepted"] for r in records), rejects=sum(r["rejected"] for r in records),
                  cost_bridges=sum(r["costs"] for r in records),
                  dynamic_fills=sum(r["dynamic_fills"] for r in records),
                  same_implementer_alternate_arithmetic=True)
    write_json(folder / "accounting-parity.json", result)
    event("V7_oracle_PASS", order=order, cases=len(cases))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--order", default=ORDERS[0], choices=ORDERS)
    run(p.parse_args().order)
