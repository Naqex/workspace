"""Single future-campaign facade for versioned FTMO assumptions and session guards."""
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP
from prop_v8_source import Calendar
from prop_v8_calendar_correction import corrected_data
from xau_h1_stage0_scan import funding_events


@dataclass(frozen=True)
class GoldCosts:
    model: str
    commission_side: Decimal = Decimal(".000007")
    market_slippage_oz: Decimal = Decimal(".20")
    limit_tp_slippage_oz: Decimal = Decimal("0")
    contract_oz: int = 100

    def swap_per_oz(self, side):
        if self.model not in ("SYM_FLAT", "ASYM_ORDER") or side not in ("BUY", "SELL"):
            raise ValueError("unregistered_cost_scenario")
        return Decimal("-.40") if self.model == "SYM_FLAT" else Decimal("-.45" if side == "BUY" else "-.05")

    def money(self, trade, ounces):
        if type(ounces) is not int or not 1 <= ounces <= 5000:
            raise ValueError("gold_lot_grid")
        p0, px = (Decimal(trade[k]) / 1000 for k in ("entry_price_units", "exit_price_units"))
        cent = lambda v: v.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)
        gross = cent((px - p0) * ounces * (1 if trade["side"] == "BUY" else -1))
        commission = sum(cent(p * ounces * self.commission_side) for p in (p0, px))
        exit_slip = self.limit_tp_slippage_oz if trade["reason"].startswith("TP") and self.model == "ASYM_ORDER" else self.market_slippage_oz
        slippage = ounces * (self.market_slippage_oz + exit_slip)
        multipliers = sum(e["multiplier"] for e in funding_events(trade["entry_msc"], trade["exit_msc"]))
        swap = ounces * self.swap_per_oz(trade["side"]) * multipliers
        net = gross - commission - slippage + swap
        return {k: float(v) for k, v in dict(gross_usd=gross, commission_usd=commission,
                                           slippage_usd=slippage, swap_usd=swap, net_usd=net).items()}


def gold_calendar(first, end):
    # Includes V8's verified 31Dec2021 correction; all other uncertainty labels survive.
    return Calendar(corrected_data(), first, end)
