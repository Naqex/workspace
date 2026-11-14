"""V4 sizing and admissions, with V5 harvesting restricted to Funded."""
from prop_v5_account import V5Account
from prop_cocore_v4 import CoCoreAccount
from prop_portfolio_accounts import entry_exit_fee
from prop_campaign_accounts import CAPITAL
from prop_portfolio_accounts import FIELDS, SLIP, VALUE
from prop_campaign_accounts import stats
import numpy as np


class HarvestAccount(V5Account):
    def __init__(self, *args, standalone=False, **kwargs):
        super().__init__(*args, mechanism="PARENT", controller=True, **kwargs)
        self.standalone = standalone
        if standalone:
            if not self.rolling:
                raise ValueError("standalone_requires_lifecycle")
            self.phase = 3

    def risk_request(self, equity, role, weight):
        return CoCoreAccount.risk_request(self, equity, role, weight)

    def observe_policy(self, at, equity):
        if self.phase == 3:
            super().observe_policy(at, equity)

    def segment(self, rows, trades, cache):
        if not self.rolling:
            if not self.active or not len(rows):
                return
            values = np.zeros(len(rows), dtype="int64")
            for i, (q, _) in self.active.items():
                t = trades[i]
                field = FIELDS[t["asset"]][0 if t["side"] == "BUY" else 1]
                values += (1 if t["side"] == "BUY" else -1) * q * VALUE[t["asset"]] * (
                    rows[field].astype("int64") - t["entry_price_units"])
            s = stats(values)
            offset = self.balance + sum(self.accrued.values()) - sum(
                q * SLIP[trades[i]["asset"]] for i, (q, _) in self.active.items())
            self.metrics(offset + s["low"], offset + s["high"], s["dd"])
            self.float = offset + s["last"] - self.balance
        elif self.phase < 3:
            # V5's phase1/2 tick-threshold scan is deliberately disabled.
            CoCoreAccount.segment(self, rows, trades, cache)
        else:
            super().segment(rows, trades, cache)

    def dump(self):
        if not self.active:
            out = super().dump()
        else:
            # A sample boundary is observation censoring, never a market exit.
            net = sum(r["net_usd"] for r in self.closed)
            fees = sum(entry_exit_fee(self._trades[i], self._trades[i]["entry_price_units"], q)
                       for i, (q, _) in self.active.items())
            phase_profit = sum(round((p["balance_usd"] - 50000) * 1000) for p in self.passes)
            removed = sum(round(p["gross_removed_usd"] * 1000) for p in self.payouts)
            if self.balance != CAPITAL + round(net * 1000) - fees - phase_profit - removed:
                raise ValueError("V6_censored_cash_bridge")
            out = dict(start_msc=self.start, end_msc=self.end, cell=self.cell,
                       rolling=self.rolling, phase=self.phase, phase_passes=self.passes,
                       first_breach=self.breach, accepted=self.accepted, closed=self.closed,
                       entries=len(self.accepted), closed_trades=len(self.closed),
                       balance_usd=self.balance / 1000, net_usd=net,
                       net_R=sum(r["net_R"] for r in self.closed),
                       mean_net_R=(sum(r["net_R"] for r in self.closed) / len(self.closed)
                                   if self.closed else None),
                       peak_dd_pct=self.dd / 500000, static_loss_pct=self.static / 500000,
                       worst_daily_loss_pct=self.daily / 500000,
                       max_equity_R_DD=self.dd / (self.fixed_risk * 1000) if not self.rolling else None,
                       payouts=self.payouts, trader_payout_usd=sum(p["trader_usd"] for p in self.payouts),
                       rejections=dict(self.rejected), include_satellite=self.include_satellite,
                       maximum_open_stop_risk_pct=self.maximum_stop_exposure / 500000,
                       max_concurrency=self.max_concurrency, throttled_entries=self.throttled,
                       daily_equity_marks=self.daily_marks, stale_midnight_marks=self.stale_resets,
                       operations=self.operations, forced_closes=self.forced_closes,
                       cash_bridge_verified=True, prop_qualified=False,
                       status="FAILED_MODEL_BREACH" if self.breach else "OPEN_EXPOSURE_RIGHT_CENSORED")
        out.update(policy="V4_Harvest", standalone_funded=self.standalone,
                   ratchet=False, mechanism="PARENT",
                   open_positions=[dict(trade=i, quantity=q, risk_usd=r, accrued_milli=self.accrued[i])
                                   for i, (q, r) in self.active.items()],
                   terminal_equity_usd=(self.balance + self.float) / 1000)
        return out
