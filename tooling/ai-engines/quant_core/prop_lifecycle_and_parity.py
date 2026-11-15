"""Reviewed lifecycle adapter, not another copy of the historical state machine."""
from contextlib import contextmanager
from prop_v7_accounts import AuditAccount
from prop_v7_review import Oracle
from prop_v6_replay import replay
from prop_portfolio_accounts import quantity_steps


@contextmanager
def bindings(module, **values):
    old = {k: getattr(module, k) for k in values}
    try:
        for k, v in values.items():
            setattr(module, k, v)
        yield
    finally:
        for k, v in old.items():
            setattr(module, k, v)


def simulate(trades, sources, accounts, first, end, calendar):
    return replay(trades, sources, accounts, end, calendar, first=first)
