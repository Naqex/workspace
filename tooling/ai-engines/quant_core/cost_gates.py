"""Exact admission comparisons; historical accounting and display floats stay intact."""

from fractions import Fraction


def exceeds_friction_cap(friction, natural_stop, percent):
    """Inclusive cap on declared decimal inputs, without an epsilon allowance."""
    values = (friction, natural_stop, percent)
    if any(isinstance(value, bool) for value in values):
        raise ValueError("invalid_friction_cap_input")
    cost, stop, cap = (Fraction(str(value)) for value in values)
    if cost < 0 or stop <= 0 or not 0 <= cap <= 100:
        raise ValueError("invalid_friction_cap_input")
    return 100 * cost > cap * stop


def stress_market_friction_units(asset, bid_units, ask_units):
    """Immediate native SYM market round trip, in integer quote units.

    Gold commission follows the existing per-leg USD/oz rounding to 0.0001;
    compare before subtracting float prices, which loses exact grid geometry.
    This is an entry gate, with zero holding time and therefore no funding.
    """
    if type(bid_units) is not int or type(ask_units) is not int or not 0 < bid_units <= ask_units:
        raise ValueError("invalid_friction_quote")
    spread = ask_units - bid_units
    if asset == "XAUUSD":
        commission = sum((price * 7 + 50000) // 100000 for price in (bid_units, ask_units))
        return Fraction(spread + 400) + Fraction(commission, 10)
    if asset == "EURUSD":
        return Fraction(spread + 9)
    raise ValueError("unregistered_native_friction_asset")
