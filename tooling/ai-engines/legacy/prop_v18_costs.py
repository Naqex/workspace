"""Declared spread/slippage surcharge on unchanged scenario first-passage paths."""
from contextlib import ExitStack, contextmanager
from decimal import Decimal, ROUND_CEILING
from prop_v15_accounts import V15Account, execution_bindings
from prop_v14_accounts import entry_charge as base_entry, trade_money as base_money
from quant_core.prop_lifecycle_and_parity import bindings
import independent_ledger_auditor as oracle


def surcharge(trade, quantity, pct):
    if pct not in (100, 125, 150):
        raise ValueError("V18_registered_friction_only")
    value, slip = (1, 200) if trade["asset"] == "XAUUSD" else (10, 10)
    n = quantity * (2 * slip + value * trade["spread_units"]) * (pct - 100)
    # Actual-order per-side aggregate surcharge, conservatively rounded to cents.
    return (n + 1999) // 2000 * 10


def independent_surcharge(trade, quantity, pct):
    gold = trade["asset"] == "XAUUSD"
    scale, contract = (1000, 1) if gold else (100000, 1000)
    spread_usd = Decimal(trade["spread_units"]) / scale * contract
    slip_usd = Decimal(".20") if gold else Decimal(".01")
    extra = (Decimal(pct) / 100 - 1) * quantity * (spread_usd / 2 + slip_usd)
    return int(extra.quantize(Decimal(".01"), rounding=ROUND_CEILING) * 1000)


class FrictionAccount(V15Account):
    def __init__(self, *args, friction_pct=100, **kwargs):
        if friction_pct not in (100, 125, 150):
            raise ValueError("V18_unregistered_friction")
        self.friction_pct = friction_pct
        self.extra_marked = set()
        super().__init__(*args, factor=1.5, cushion=True, **kwargs)

    def check(self, at, floating):
        # Include pending exit surcharge immediately, including the entry mark.
        for i, (q, _) in self.active.items():
            if i not in self.extra_marked:
                extra = surcharge(self._trades[i], q, self.friction_pct)
                self.accrued[i] -= extra
                floating -= extra
                self.extra_marked.add(i)
        return super().check(at, floating)

    def reserve_floor(self, trades, new_id, q, charge):
        value = super().reserve_floor(trades, new_id, q, charge)
        return value - sum(surcharge(trades[i], size, self.friction_pct)
                           for i, size in [*[(k, v[0]) for k, v in self.active.items()], (new_id, q)])

    def dump(self):
        return dict(super().dump(), friction_pct=self.friction_pct,
                    spread_stress="per-leg surcharge; frozen first-passage path",
                    surcharge_rounding="up to actual-order cent per side")


class FrictionOracle(oracle.V15LedgerOracle):
    def __init__(self, expected, trades):
        if expected["friction_pct"] not in (100, 125, 150):
            raise ValueError("V18_oracle_friction_contract")
        super().__init__(expected, trades)

    def entry(self, i, at, quote):
        super().entry(i, at, quote)
        if i in self.open:
            self.carry[i] -= independent_surcharge(self.trades[i], self.open[i], self.e["friction_pct"])

    def reserve(self, i, q):
        value = super().reserve(i, q)
        return value - sum(independent_surcharge(self.trades[k], size, self.e["friction_pct"])
                           for k, size in [*self.open.items(), (i, q)])


@contextmanager
def cost_bindings(pct):
    import prop_portfolio_accounts as portfolio
    import prop_v5_account as v5
    import prop_v6_account as v6
    original_parts = oracle.v14_parts

    def charge(t, price, q):
        return base_entry(t, price, q) + surcharge(t, q, pct)

    def money(t, q, model, risk):
        row = base_money(t, q, model, risk)
        extra = 2 * surcharge(t, q, pct)
        row.update(execution_surcharge_usd=extra / 1000,
                   net_usd=round(row["net_usd"] - extra / 1000, 2),
                   net_R=round(row["net_usd"] * 1000 - extra) / (risk * 1000))
        return row

    def parts(t, q, model):
        row = original_parts(t, q, model)
        extra = independent_surcharge(t, q, pct)
        row["net"] -= 2 * extra
        row["entry_charge"] -= extra
        return row

    with ExitStack() as stack:
        stack.enter_context(execution_bindings())
        for module in (portfolio, v5, v6):
            values = {n: v for n, v in (("entry_exit_fee", charge), ("trade_money", money))
                      if hasattr(module, n)}
            stack.enter_context(bindings(module, **values))
        stack.enter_context(bindings(oracle, v14_parts=parts))
        yield
