"""Shared USD account on interleaved admitted Gold/EUR ticks.

The existing Account owns lifecycle, resets, loss rules and rewards. This
adapter supplies instrument units, paired quote valuation and shared budgets.
"""
from collections import Counter, defaultdict
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
import numpy as np

from prop_campaign_accounts import Account, stats, utc, CAPITAL, PRAGUE
from prop_portfolio_policy import requested_risk, within_open_risk_cap
from prop_campaign_source import START, END, FINAL, HOUR, DAY
from prop_campaign_exits import funding_rate
from xau_h1_execution import cents, commission
from xau_h1_stage0_scan import funding_events

ASSETS = ("XAUUSD", "EURUSD")
FIELDS = {"XAUUSD": ("b0", "a0"), "EURUSD": ("b1", "a1")}
VALUE = {"XAUUSD": 1, "EURUSD": 10}  # milli-USD per integer price grid / quantity step
SLIP = {"XAUUSD": 200, "EURUSD": 20}
JOINT = np.dtype([("t", "<i8")] + [(n, "<i4") for n in ("b0", "a0", "b1", "a1")])


def quantity_steps(trade, risk):
    value = VALUE[trade["asset"]] * abs(trade["entry_price_units"] - trade["stop_units"])
    quantity = int(risk * 1000) // value
    if not 1 <= quantity <= (5000 if trade["asset"] == "XAUUSD" else 100000):
        raise ValueError("position_grid")
    return quantity


def entry_exit_fee(trade, price, quantity):
    if trade["asset"] == "XAUUSD":
        return cents(commission(price, quantity)) * 10
    return cents(Decimal(quantity) * Decimal(".025")) * 10


def funding_step(trade, model):
    if trade["asset"] == "XAUUSD":
        return int(round(funding_rate(trade["side"], model) * 1000))
    return -400  # declared -$40 / lot; one quantity step = .01 lot


def rounded_cent_milli(value):
    return (1 if value >= 0 else -1) * ((abs(value) + 5) // 10) * 10


def trade_money(trade, quantity, model, risk):
    sign = 1 if trade["side"] == "BUY" else -1
    gross = rounded_cent_milli(sign * quantity * VALUE[trade["asset"]] *
                               (trade["exit_price_units"] - trade["entry_price_units"]))
    fees = sum(entry_exit_fee(trade, price, quantity) for price in (
        trade["entry_price_units"], trade["exit_price_units"]))
    slippage = quantity * SLIP[trade["asset"]] * 2
    swap = quantity * funding_step(trade, model) * sum(
        e["multiplier"] for e in funding_events(trade["entry_msc"], trade["exit_msc"]))
    net = gross - fees - slippage + swap
    return dict(gross_usd=gross / 1000, commission_usd=fees / 1000,
                slippage_usd=slippage / 1000, swap_usd=swap / 1000,
                net_usd=net / 1000, net_R=net / (risk * 1000))


class PortfolioAccount(Account):
    open_cap_milli = 500000
    internal_floor_milli = 46500000
    cap_rejection = "OPEN_STOP_RISK_1PCT_CAP"
    floor_rejection = "INTERNAL_STATIC_7PCT_RESERVE"

    def __init__(self, *args, include_satellite=True, scaled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.include_satellite = include_satellite
        self.scaled = scaled
        self.day_halt = False
        self.risk_buckets = Counter()
        self.maximum_stop_exposure = 0

    def risk_request(self, equity, role, weight):
        return requested_risk(self.phase, equity, role, weight)

    def floating(self, trades, quote):
        value = 0
        for i, (q, _) in self.active.items():
            t = trades[i]
            field = FIELDS[t["asset"]][0 if t["side"] == "BUY" else 1]
            price = int(quote[field])
            if price <= 0:
                raise ValueError("active_asset_quote_unknown")
            sign = 1 if t["side"] == "BUY" else -1
            value += (sign * q * VALUE[t["asset"]] *
                      (price - t["entry_price_units"])
                      - q * SLIP[t["asset"]] + self.accrued[i])
        return value

    def reserve_floor(self, trades, new_id, q, entry_fee):
        value = self.balance - entry_fee
        positions = dict(self.active)
        positions[new_id] = (q, 0)
        for i, (size, _) in positions.items():
            t = trades[i]
            end = t.get("deadline_msc")
            if type(end) is not int or end < t["entry_msc"]:
                raise ValueError("missing_prelocked_funding_horizon")
            sign = 1 if t["side"] == "BUY" else -1
            value += sign * size * VALUE[t["asset"]] * (
                t["stop_units"] - t["entry_price_units"])
            value -= size * SLIP[t["asset"]] * 2
            value -= entry_exit_fee(t, t["stop_units"], size)
            value += min(0, funding_step(t, self.cell)) * size * sum(
                e["multiplier"] for e in funding_events(t["entry_msc"], end))
        return value

    def action(self, kind, at, i, trades, quote, mult=0):
        if at < self.start or at >= self.end or self.breach:
            return
        self.last_quote = quote
        if kind == "reset":
            self.day_halt = False
            self.daily_marks.append([at, self.balance + self.floating(trades, quote)])
            self.anchor = self.balance
            if self.rolling:
                self.reward(at)
        elif kind == "entry":
            t = trades[i]
            if t["role"] == "SATELLITE" and not self.include_satellite:
                self.rejected["SYSTEM_HAS_NO_SATELLITE"] += 1
                return
            if t["decision_msc"] < self.start or t["decision_msc"] <= self.gate:
                self.rejected["PRESTART_OR_PHASE_GATE"] += 1
                return
            if any(trades[k]["asset"] == t["asset"] and
                   trades[k]["decision_msc"] == t["decision_msc"] for k in self.active):
                self.rejected["ASSET_DECISION_COLLISION"] += 1
                return
            if self.day_halt or self.balance - self.anchor <= -1000000:
                self.day_halt = True
                self.rejected["DAILY_REALIZED_2PCT_HALT"] += 1
                return
            equity = self.balance + self.floating(trades, quote)
            weight = t.get("regime_weight", 1) if self.scaled else 1
            risk = self.risk_request(equity, t["role"], weight)
            try:
                q = quantity_steps(t, risk)
            except ValueError:
                self.rejected["LOT_GRID_MIN_MAX"] += 1
                return
            old_risk = sum(
                size * VALUE[trades[k]["asset"]] *
                abs(trades[k]["entry_price_units"] - trades[k]["stop_units"])
                for k, (size, _) in self.active.items())
            new_risk = q * VALUE[t["asset"]] * abs(t["entry_price_units"] - t["stop_units"])
            if old_risk + new_risk > self.open_cap_milli:
                self.rejected[self.cap_rejection] += 1
                return
            fee = entry_exit_fee(t, t["entry_price_units"], q)
            projected = self.reserve_floor(trades, i, q, fee)
            if projected <= self.internal_floor_milli:
                self.rejected[self.floor_rejection] += 1
                return
            if projected < max(self.anchor - 2500000, 45000000):
                self.rejected["SHARED_STOP_RESERVE"] += 1
                return
            state = dict(
                balance_milli_usd=self.balance, equity_milli_usd=equity,
                daily_anchor_milli_usd=self.anchor, role=t["role"], weight=weight,
                risk_usd=risk, prior_stop_risk_milli_usd=old_risk,
                new_stop_risk_milli_usd=new_risk, projected_stop_milli_usd=projected,
            )
            self.balance -= fee
            self.active[i] = (q, risk)
            self.accrued[i] = 0
            self.accepted.append(dict(
                trade=i, at=at, phase=self.phase, risk_usd=risk,
                ounces=q, quantity_steps=q, asset=t["asset"], risk_state=state,
            ))
            self.risk_buckets[str(risk)] += 1
            self.maximum_stop_exposure = max(self.maximum_stop_exposure, old_risk + new_risk)
            self.phase_days.add(utc(at).astimezone(PRAGUE).date().isoformat())
            self.max_concurrency = max(self.max_concurrency, len(self.active))
            if self.phase == 3 and self.funded_first is None:
                self.funded_first = at
        elif kind == "swap":
            if i in self.active:
                self.accrued[i] += self.active[i][0] * funding_step(trades[i], self.cell) * mult
        elif kind == "exit":
            if i not in self.active:
                return
            q, risk = self.active.pop(i)
            self.accrued.pop(i)
            t = trades[i]
            money = trade_money(t, q, self.cell, risk)
            self.balance += (int(round(money["net_usd"] * 1000))
                             + entry_exit_fee(t, t["entry_price_units"], q))
            self.closed.append(dict(trade=i, at=at, phase=self.phase,
                                    risk_usd=risk, net_usd=money["net_usd"],
                                    net_R=money["net_R"], costs=money))
        self.check(at, self.floating(trades, quote))
        if self.balance - self.anchor <= -1000000:
            self.day_halt = True
        if kind == "exit" and self.rolling and not self.breach:
            self.reward(at)

    def segment(self, rows, trades, cache):
        if not self.active or self.breach or not len(rows):
            return
        key = tuple(sorted((i, q) for i, (q, _) in self.active.items()))
        if key not in cache:
            values = np.zeros(len(rows), dtype="int64")
            for i, q in key:
                t = trades[i]
                buy = t["side"] == "BUY"
                field = FIELDS[t["asset"]][0 if buy else 1]
                if np.any(rows[field] <= 0):
                    raise ValueError("held_asset_missing_joint_quote")
                values += (1 if buy else -1) * q * VALUE[t["asset"]] * (
                    rows[field].astype("int64") - t["entry_price_units"])
            cache[key] = (stats(values), values)
        summary, values = cache[key]
        offset = self.balance + sum(self.accrued.values()) - sum(
            q * SLIP[trades[i]["asset"]] for i, (q, _) in self.active.items())
        if offset + summary["low"] < max(self.anchor - 2500000, 45000000):
            index = int(np.flatnonzero(offset + values < max(
                self.anchor - 2500000, 45000000))[0])
            part = stats(values[:index + 1])
            self.metrics(offset + part["low"], offset + part["high"], part["dd"])
            self.check(int(rows["t"][index]), offset + int(values[index]) - self.balance)
            return
        self.metrics(offset + summary["low"], offset + summary["high"], summary["dd"])
        self.float = offset + summary["last"] - self.balance

    def dump(self):
        if self.active:
            raise ValueError("portfolio_cutoff_not_flat")
        row = super().dump()
        row.update(include_satellite=self.include_satellite,
                   risk_buckets=dict(self.risk_buckets),
                   maximum_open_stop_risk_pct=self.maximum_stop_exposure / 500000,
                   policy="V3_balanced_joint_ticks", d1_scaled=self.scaled)
        return row


def joint_hour(readers, hour, last):
    chunks = []
    for asset_index, asset in enumerate(ASSETS):
        reader = readers[asset]
        if hour not in reader.files:
            continue
        ticks = reader.hour(hour)
        if len(ticks):
            chunks.append((asset_index, ticks))
    if not chunks:
        return np.empty(0, dtype=JOINT), [np.array([], dtype="int64") for _ in ASSETS]
    times = np.concatenate([v["t"] for _, v in chunks])
    instruments = np.concatenate([np.full(len(v), a) for a, v in chunks])
    ordinals = np.concatenate([np.arange(len(v)) for _, v in chunks])
    bid = np.concatenate([v["b"] for _, v in chunks])
    ask = np.concatenate([v["a"] for _, v in chunks])
    order = np.lexsort((ordinals, instruments, times))
    instruments, times, bid, ask = [v[order] for v in (instruments, times, bid, ask)]
    result = np.empty(len(times), dtype=JOINT)
    result["t"] = times
    maps = []
    for a, asset in enumerate(ASSETS):
        source = np.flatnonzero(instruments == a)
        maps.append(source)
        indices = np.maximum.accumulate(np.where(instruments == a, np.arange(len(times)), -1))
        known = indices >= 0
        for name, values in zip(FIELDS[asset], (bid, ask)):
            result[name] = last[name] if last is not None else 0
            result[name][known] = values[indices[known]]
    return result, maps


def replay(trades, readers, accounts, end=FINAL, progress=None):
    actions = defaultdict(list)
    for i, t in enumerate(trades):
        a = ASSETS.index(t["asset"])
        actions[(t["entry_msc"], a, t["entry_quote_index"])].append(("entry", i, 0))
        actions[(t["exit_msc"], a, t["exit_quote_index"])].append(("exit", i, 0))
        for f in funding_events(t["entry_msc"], t["exit_msc"]):
            actions[(f["at"], -1, -1)].append(("swap", i, f["multiplier"]))
    day = date(2022, 1, 1)
    while day < utc(end).date():
        at = int(datetime(day.year, day.month, day.day, tzinfo=PRAGUE).timestamp() * 1000)
        if START <= at < end:
            actions[(at, -1, -1)].append(("reset", None, 0))
        day += timedelta(days=1)
    keys = sorted(actions)
    cursor = 0
    last = None
    active = set()
    ticks_seen = 0
    for account in accounts:
        account._trades = trades
    priority = {"reset": 0, "swap": 1, "exit": 2, "entry": 3}

    def consume(rows):
        nonlocal last, ticks_seen
        if not len(rows):
            return
        cache = {}
        for account in accounts:
            if account.start <= int(rows["t"][0]) and int(rows["t"][-1]) < account.end:
                account.segment(rows, trades, cache)
        last = rows[-1]
        if active:
            ticks_seen += len(rows)

    first = min(t["entry_msc"] for t in trades) // HOUR * HOUR
    for hour in range(first, end, HOUR):
        for i in active:
            reader = readers[trades[i]["asset"]]
            if hour not in reader.files:
                raise ValueError("held_asset_tick_hour_unadmitted")
        rows, maps = joint_hour(readers, hour, last)
        j = 0
        while cursor < len(keys) and keys[cursor][0] < hour + HOUR:
            key = keys[cursor]
            at, asset, ordinal = key
            cut = int(rows["t"].searchsorted(at)) if asset < 0 else int(maps[asset][ordinal])
            consume(rows[j:cut])
            if asset >= 0:
                if rows["t"][cut] != at:
                    raise ValueError("joint_tick_ordinal")
                last = rows[cut]
                for account in accounts:
                    if account.start <= at < account.end and not account.breach:
                        account.check(at, account.floating(trades, last))
            for kind, i, mult in sorted(
                    actions[key], key=lambda r: (
                        priority[r[0]], trades[r[1]]["role"] == "SATELLITE"
                        if r[1] is not None else False)):
                for account in accounts:
                    account.action(kind, at, i, trades, last, mult)
                if kind == "entry":
                    active.add(i)
                elif kind == "exit":
                    active.remove(i)
            j = cut
            cursor += 1
        consume(rows[j:])
        if progress is not None and hour % (1000 * HOUR) == 0:
            progress("joint_tick_replay", hour=utc(hour).isoformat(), ticks=ticks_seen)
    if active:
        raise ValueError("joint_tick_replay_not_flat")
    return [dict(account.dump(), joint_tick_marks=ticks_seen) for account in accounts]
