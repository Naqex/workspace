"""One registered balanced policy and shared core/satellite stop budgets."""
from collections import Counter

from prop_campaign_accounts import Account
from prop_campaign_exits import quantity
from xau_h1_execution import commission, cents


def requested_risk(phase, equity_milli_usd, role="CORE", weight=1):
    if phase not in (1, 2, 3) or role not in ("CORE", "SATELLITE") or weight not in (0.5, 1):
        raise ValueError("unregistered_phase_role_or_weight")
    base = ((200, 175, 125) if role == "CORE" else (100, 100, 75))[phase - 1]
    if equity_milli_usd <= 47000000:
        base = min(base, 90)
    elif equity_milli_usd <= 48000000:
        base = min(base, 150)
    return base * weight if role == "CORE" else base


def within_open_risk_cap(existing_milli_usd, proposed_milli_usd):
    if min(existing_milli_usd, proposed_milli_usd) < 0:
        raise ValueError("nonnegative_absolute_stop_exposure_required")
    return existing_milli_usd + proposed_milli_usd <= 500000


class BalancedAccount(Account):
    """Reuse the admitted Gold replay; budget decisions never inspect exits."""
    def __init__(self, *args, scaled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.scaled = scaled
        self.role = "CORE"
        self.factor = 1
        self.day_halt = False
        self.risk_buckets = Counter()
        self.admission_records = []

    def risk(self, equity):
        return requested_risk(self.phase, equity, self.role, self.factor)

    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "reset":
            self.day_halt = False
        before = len(self.accepted)
        state = None
        if (kind == "entry" and self.start <= at < self.end and not self.breach
                and trades[i]["decision_msc"] > self.gate):
            self.role = trades[i].get("role", "CORE")
            self.factor = trades[i].get("regime_weight", 1) if self.scaled else 1
            equity = self.balance + self.floating(trades, quote)
            risk = self.risk(equity)
            if self.day_halt or self.balance - self.anchor <= -1000000:
                self.day_halt = True
                self.rejected["DAILY_REALIZED_2PCT_HALT"] += 1
                return
            try:
                q = quantity(trades[i], risk)
            except ValueError:
                self.rejected["LOT_GRID_MIN_MAX"] += 1
                return
            existing = sum(
                size * abs(trades[k]["entry_price_units"] - trades[k]["stop_units"])
                for k, (size, _) in self.active.items()
            )
            proposed = q * abs(trades[i]["entry_price_units"] - trades[i]["stop_units"])
            if not within_open_risk_cap(existing, proposed):
                self.rejected["OPEN_STOP_RISK_1PCT_CAP"] += 1
                return
            fee = cents(commission(trades[i]["entry_price_units"], q)) * 10
            projected = self.reserve_floor(trades, i, q, fee)
            if projected <= 46500000:
                self.rejected["INTERNAL_STATIC_7PCT_RESERVE"] += 1
                return
            state = dict(
                balance_milli_usd=self.balance, equity_milli_usd=equity,
                daily_anchor_milli_usd=self.anchor, role=self.role, weight=self.factor,
                risk_usd=risk, prior_stop_risk_milli_usd=existing,
                new_stop_risk_milli_usd=proposed,
                projected_stop_milli_usd=projected,
            )
        super().action(kind, at, i, trades, quote, mult)
        if self.balance - self.anchor <= -1000000:
            self.day_halt = True
        if len(self.accepted) > before:
            self.accepted[-1]["risk_state"] = state
            self.risk_buckets[str(self.accepted[-1]["risk_usd"])] += 1

    def dump(self):
        row = super().dump()
        row.update(
            risk_buckets=dict(self.risk_buckets),
            policy="V3_balanced_core200_175_125_sat100_100_75_cap1pct",
            d1_scaled=self.scaled,
            maximum_open_stop_risk_pct=max(
                ((a["risk_state"]["prior_stop_risk_milli_usd"] +
                  a["risk_state"]["new_stop_risk_milli_usd"]) / 500000
                 for a in self.accepted), default=0),
        )
        return row
