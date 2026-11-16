"""V19 risk requests over the existing lifecycle and independent cash oracle."""
from decimal import Decimal, ROUND_FLOOR
from prop_v18_costs import FrictionAccount, FrictionOracle
from quant_core.asymmetric_opportunity_optimizer import cushion_risk

PROFILES = ("BASE_GUARD", "O1_G035", "O1_G050", "O2", "O1_G035_O2", "O1_G050_O2")


class V19Account(FrictionAccount):
    floor_rejection = "V19_STATIC_OR_DAILY_PROJECTED_RESERVE"

    def __init__(self, *args, profile, **kwargs):
        if profile["name"] not in PROFILES or profile["gamma"] not in (None, .35, .5):
            raise ValueError("unregistered_V19_profile")
        self.profile = profile
        self.current_request = None
        super().__init__(*args, **kwargs)

    @property
    def internal_floor_milli(self):
        return max(45800000, self.anchor - 1100000)

    def risk_request(self, equity, role, weight):
        if self.current_request is None:
            raise ValueError("V19_current_sleeve_required")
        identity = self._trades[self.current_request]["id"]
        sleeve = self.profile["weights"][identity]
        if self.profile["gamma"] is not None:
            return cushion_risk(self.phase, equity, self.balance, self.profile["gamma"], sleeve)
        old = super().risk_request(equity, role, weight)
        return float((Decimal(str(old)) * Decimal(str(sleeve))).quantize(Decimal(".01"), rounding=ROUND_FLOOR))

    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "entry":
            self.current_request = i
            self._trades = trades
        try:
            return super().action(kind, at, i, trades, quote, mult)
        finally:
            if kind == "entry":
                self.current_request = None

    def dump(self):
        return dict(super().dump(), policy="V19_" + self.profile["name"],
                    V19_profile=self.profile, daily_projected_loss_reserve_pct=2.2)


class V19LedgerOracle(FrictionOracle):
    """No producer sizing helper; decimal risk, lot, reserve and ledger replay."""
    def entry(self, i, at, quote):
        self.current_target = i
        try:
            return super().entry(i, at, quote)
        finally:
            self.current_target = None

    def requested_risk(self, equity):
        p = self.e["V19_profile"]
        phase = self.phase
        gamma = p["gamma"]
        if gamma is None:
            risk = Decimal((200, 175, 125)[phase - 1]) * Decimal("1.5")
            if phase == 1 and self.cushion_active and equity > 50000000:
                risk += min(Decimal(self.cash - 50000000) / 5000, Decimal(250))
            if equity <= 46500000:
                risk = min(risk, Decimal(75))
            elif equity <= 47500000:
                risk = min(risk, Decimal(150))
        else:
            base = (Decimal(300), Decimal("262.5"), Decimal("187.5"))[phase - 1]
            ratio = max(Decimal(0), min(Decimal(1), (Decimal(equity) - 45000000) / 5000000))
            risk = base * (ratio ** Decimal(str(gamma)))
            if phase in (1, 2):
                risk += min(base, max(Decimal(0), Decimal(self.cash - 50000000)) / 10000)
        identity = self.trades[self.current_target]["id"]
        return float((risk * Decimal(str(p["weights"][identity]))).quantize(Decimal(".01"), rounding=ROUND_FLOOR))

    def policy_limits(self):
        return 1000000, max(45800000, self.anchor - 1100000)
