"""Registered global risk scale after the unchanged V19 request and lot rules."""
from decimal import Decimal, ROUND_FLOOR
import math
from prop_v19_accounts import V19Account, V19LedgerOracle
from prop_v19_stress import ScalarPointOracleMixin


class V20Account(V19Account):
    def __init__(self, *args, profile, **kwargs):
        if (profile["name"] not in ("O2_UNSCALED", "O2_VOL", "O2_VOL_CUSHION") or
                type(profile["house_money"]) is not bool or
                not math.isfinite(profile["k"]) or not 0 < profile["k"] <= 2):
            raise ValueError("unregistered_V20_profile")
        self.v20_profile = profile
        super().__init__(*args, profile=dict(name="O2", gamma=None, weights=profile["weights"]), **kwargs)
        self.cushion = profile["house_money"]

    def risk_request(self, equity, role, weight):
        old = super().risk_request(equity, role, weight)
        return float((Decimal(str(old)) * Decimal(str(self.v20_profile["k"]))).quantize(
            Decimal(".01"), rounding=ROUND_FLOOR))

    def dump(self):
        return dict(super().dump(), policy="V20_" + self.v20_profile["name"],
                    V20_profile=self.v20_profile)


class V20LedgerOracle(V19LedgerOracle):
    def requested_risk(self, equity):
        # The parent independently reconstructs phase, cushion and sleeve risk.
        risk = super().requested_risk(equity)
        return float((Decimal(str(risk)) * Decimal(str(self.e["V20_profile"]["k"]))).quantize(
            Decimal(".01"), rounding=ROUND_FLOOR))


class FastV20Oracle(ScalarPointOracleMixin, V20LedgerOracle):
    pass
