"""The only two approved Gold sizing policies; harvesting/lifecycle remain reused."""
from prop_v6_account import HarvestAccount
from prop_portfolio_accounts import quantity_steps
from prop_v7_common import POLICIES


class AuditAccount(HarvestAccount):
    def __init__(self, *args, policy="GOLD_V4", reference_side="BOTH", **kwargs):
        super().__init__(*args, **kwargs)
        if policy not in POLICIES or reference_side not in ("BOTH", "BUY", "SELL"):
            raise ValueError("unregistered_V7_policy")
        self.policy_id = policy
        self.reference_side = reference_side

    def risk_request(self, equity, role, weight):
        if not self.rolling:
            return self.fixed_risk
        if weight != 1:
            raise ValueError("V7_no_regime_overlay")
        risk = POLICIES[self.policy_id][self.phase - 1]
        return min(risk, 90) if equity <= 47000000 else min(risk, 150) if equity <= 48000000 else risk

    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "entry" and self.start <= at < self.end and not self.breach:
            t = trades[i]
            if self.policy_id != "COCORE_FIXED" and t["asset"] != "XAUUSD":
                self.rejected["EURUSD_DECOMMISSIONED"] += 1
                return
            if self.reference_side != "BOTH" and t["side"] != self.reference_side:
                self.rejected["REFERENCE_SIDE_FILTER"] += 1
                return
            if not self.rolling:
                try:
                    quantity_steps(t, self.fixed_risk)
                except ValueError:
                    self.rejected["LOT_GRID_MIN_MAX"] += 1
                    return
        super().action(kind, at, i, trades, quote, mult)

    def dump(self):
        r = super().dump()
        r.update(policy_id=self.policy_id, reference_side=self.reference_side,
                 scope_label="POST_HOLDOUT_DIAGNOSTIC_FULL_SAMPLE_2022_2026",
                 effective_end_msc=self.end, path_censor=None)
        return r
