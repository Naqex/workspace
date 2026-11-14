"""Causal sleeve controls, target ratchet and funded harvesting on paired ticks."""
from collections import Counter
import numpy as np
from prop_campaign_accounts import CAPITAL
from prop_cocore_v4 import CoCoreAccount
from prop_portfolio_accounts import VALUE, SLIP, FIELDS, trade_money, quantity_steps, entry_exit_fee
from prop_v5_common import HOUR, DAY


class ColdState:
    def __init__(self):
        self.total = self.peak = self.trough = 0.
        self.cold = False

    def observe(self, net_r):
        self.total += net_r
        self.peak = max(self.peak, self.total)
        if self.cold:
            self.trough = min(self.trough, self.total)
            if self.total >= self.peak or self.total - self.trough >= 4:
                self.cold = False
        elif self.peak - self.total >= 8:
            self.cold = True
            self.trough = self.total

    @property
    def factor(self):
        return .5 if self.cold else 1.


class V5Account(CoCoreAccount):
    def __init__(self, *args, mechanism="PARENT", controller=True, **kwargs):
        super().__init__(*args, **kwargs)
        if mechanism not in ("PARENT", "D1", "D2"):
            raise ValueError("unregistered_V5_mechanism")
        self.mechanism = mechanism
        self.controller = controller
        self.cold = {a: ColdState() for a in FIELDS}
        self.current_asset = "XAUUSD"
        self.ratchet = False
        self.floor_touched = False
        self.harvest_state = "NORMAL"
        self.pending = {}
        self.operations = []
        self.forced_closes = []
        self.policy_rejects = Counter()

    def risk_request(self, equity, role, weight):
        risk = super().risk_request(equity, role, weight)
        if self.controller and self.rolling:
            if self.phase == 1 and self.ratchet:
                risk = min(risk, 90 if self.floor_touched else 125)
            elif self.phase == 2 and self.ratchet:
                risk = min(risk, 100)
        if self.mechanism == "D2":
            risk *= self.cold[self.current_asset].factor
        return risk

    def log(self, at, kind, **kw):
        self.operations.append(dict(at=int(at), phase=self.phase, kind=kind, **kw))

    def request_flat(self, at, reason):
        for i in self.active:
            self.pending.setdefault(i, (int(at), reason))
        self.log(at, reason, positions=len(self.active))

    def reward(self, at):
        before = len(self.payouts)
        super().reward(at)
        if len(self.payouts) > before:
            self.harvest_state = "NORMAL"
            self.pending.clear()
            self.log(at, "MODELED_REWARD", amount=self.payouts[-1]["trader_usd"])

    def observe_policy(self, at, equity):
        if not self.controller or not self.rolling or self.breach:
            return
        threshold = 53500000 if self.phase == 1 else 51750000
        if self.phase < 3:
            if not self.ratchet and max(equity, self.balance) >= threshold:
                self.ratchet = True
                self.log(at, "RATCHET_ARMED", equity_usd=equity / 1000)
            if self.phase == 1 and self.ratchet and not self.floor_touched and equity <= 52500000:
                self.floor_touched = True
                self.request_flat(at, "PROTECTED_FLOOR")
        elif self.funded_first is not None:
            since = self.last_payout if self.last_payout is not None else self.funded_first
            due = since + 14 * DAY
            if self.balance >= 51000000 and self.harvest_state != "PROFIT_LOCK_IDLE":
                self.harvest_state = "PROFIT_LOCK_IDLE"
                self.request_flat(at, "PROFIT_LOCK_IDLE")
            elif self.balance >= 50500000 and at >= due - 48 * HOUR and self.harvest_state == "NORMAL":
                self.harvest_state = "PRE_PAYOUT_FREEZE"
                self.log(at, "PRE_PAYOUT_FREEZE", due=due)

    def action(self, kind, at, i, trades, quote, mult=0):
        if not self.start <= at < self.end or self.breach:
            return
        old_phase = self.phase
        if kind == "session_flat":
            self.observe_policy(at, self.balance + self.floating(trades, quote))
            if self.harvest_state == "PRE_PAYOUT_FREEZE":
                self.request_flat(at, "PRE_PAYOUT_SESSION_CLOSE")
            if not self.active and self.rolling:
                self.reward(at)
            return
        if kind == "entry":
            t = trades[i]
            self.current_asset = t["asset"]
            reason = None
            if self.mechanism == "D1" and t["asset"] == "EURUSD" and not t["d1_gate"]:
                reason = "D1_ASIA_RANGE_ATR"
            if self.controller and self.harvest_state != "NORMAL":
                reason = "HARVEST_ENTRY_FREEZE"
            if self.controller and self.phase == 1 and self.floor_touched:
                risk = self.risk_request(self.balance + self.floating(trades, quote), t["role"], 1)
                q = quantity_steps(t, risk)
                fee = entry_exit_fee(t, t["entry_price_units"], q)
                if self.reserve_floor(trades, i, q, fee) <= 52500000:
                    reason = "PROTECTED_FLOOR_RESERVE"
            if reason:
                self.rejected[reason] += 1
                self.policy_rejects[reason] += 1
                return
        if kind == "exit" and i in self.pending:
            self.pending.pop(i)
        super().action(kind, at, i, trades, quote, mult)
        if kind == "exit" and self.mechanism == "D2":
            t = trades[i]
            money = trade_money(t, quantity_steps(t, 150), self.cell, 150)
            self.cold[t["asset"]].observe(money["net_R"])
        if old_phase != self.phase:
            self.cold = {a: ColdState() for a in FIELDS}
            self.ratchet = self.floor_touched = False
            self.pending.clear()
        self.observe_policy(at, self.balance + self.floating(trades, quote))

    def liquidate(self, at, i, trades, quote, reason):
        if i not in self.active:
            self.pending.pop(i, None)
            return
        t = trades[i]
        field = FIELDS[t["asset"]][0 if t["side"] == "BUY" else 1]
        actual = dict(t, exit_msc=int(at), exit_price_units=int(quote[field]), reason=reason)
        local = list(trades)
        local[i] = actual
        self.pending.pop(i, None)
        # Bypass shadow-stream update: canonical original exits update D2 later.
        old_phase = self.phase
        super().action("exit", int(at), i, local, quote)
        close = self.closed[-1]
        close["execution_override"] = dict(
            exit_msc=int(at), exit_price_units=actual["exit_price_units"], reason=reason)
        self.forced_closes.append(dict(trade=i, at=int(at), reason=reason,
                                       price_units=actual["exit_price_units"],
                                       net_usd=close["net_usd"]))
        if old_phase != self.phase:
            self.cold = {a: ColdState() for a in FIELDS}
            self.ratchet = self.floor_touched = False
            self.pending.clear()
        self.observe_policy(at, self.balance + self.floating(trades, quote))

    def segment(self, rows, trades, cache):
        if not len(rows) or self.breach:
            return
        cursor = 0
        while cursor < len(rows) and not self.breach:
            a = rows[cursor:]
            trigger = len(a)
            if self.active and self.controller and self.rolling and self.phase < 3:
                equity = np.full(len(a), self.balance + sum(self.accrued.values()), dtype="int64")
                for i, (q, _) in self.active.items():
                    t = trades[i]
                    field = FIELDS[t["asset"]][0 if t["side"] == "BUY" else 1]
                    equity += ((1 if t["side"] == "BUY" else -1) * q * VALUE[t["asset"]]
                               * (a[field].astype("int64") - t["entry_price_units"]) - q * SLIP[t["asset"]])
                if not self.ratchet:
                    hit = np.flatnonzero(equity >= (53500000 if self.phase == 1 else 51750000))
                elif self.phase == 1 and not self.floor_touched:
                    hit = np.flatnonzero(equity <= 52500000)
                else:
                    hit = []
                if len(hit):
                    trigger = int(hit[0])
            for i, (after, _) in self.pending.items():
                asset = 0 if trades[i]["asset"] == "XAUUSD" else 1
                indices = np.flatnonzero((a["src"] == asset) & (a["t"] > after))
                if len(indices):
                    trigger = min(trigger, int(indices[0]))
            if trigger == len(a):
                super().segment(a, trades, {})
                break
            part = a[:trigger + 1]
            # Cache is keyed by quantities, not interval: subsegments need a fresh map.
            super().segment(part, trades, {})
            quote = part[-1]
            at = int(quote["t"])
            if self.breach:
                break
            self.observe_policy(at, self.balance + self.floating(trades, quote))
            for i, (after, reason) in list(self.pending.items()):
                asset = 0 if trades[i]["asset"] == "XAUUSD" else 1
                if int(quote["src"]) == asset and at > after:
                    self.liquidate(at, i, trades, quote, reason)
            cursor += trigger + 1

    def dump(self):
        row = super().dump()
        if not self.rolling:
            row["canonical_unit_R_sum"] = row["net_R"]
            row["net_R"] = row["net_usd"] / self.fixed_risk
        row.update(mechanism=self.mechanism, controller=self.controller,
                   operations=self.operations, forced_closes=self.forced_closes,
                   pending_liquidations=dict(self.pending), ratchet=self.ratchet,
                   protected_floor_touched=self.floor_touched,
                   harvest_state=self.harvest_state, policy="V5")
        return row
