"""V7 alternate rational accounting with V8-scoped inputs and system admission."""
from prop_v7_review import Oracle as ParentOracle
from prop_v8_common import *
from prop_v8_source import Calendar, readers
from prop_v8_campaign import temporary_bindings


class Oracle(ParentOracle):
    def entry(self, i, at, quote):
        if self.expected["v8_system"] not in self.trades[i]["v8_systems"]:
            return
        return super().entry(i, at, quote)


def run(tag, order):
    verify()
    first, end = (BACK_START, BACK_END) if tag == "backward" else (START, END)
    folder = JOB / tag / order
    expected = read(folder / "accounts.json")
    trades = read(folder / "system-trades.json")
    calendar = Calendar(read(CALENDAR), first, end)
    import prop_v6_review as engine
    # The engine remains frozen; only documented constructor/input/observer slots differ.
    with temporary_bindings(engine, dict(Oracle=Oracle, Calendar=lambda data, cutoff: calendar,
                                        CALENDAR=CALENDAR, END=end, event=event)):
        result = engine.run(expected, trades, readers(tag, order, first, end), end, first=first)
    write_json(folder / "accounting-parity.json", result)
    event("V8_oracle_PASS", tag=tag, order=order, accounts=result["accounts"])


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--tag", choices=("full", "backward"), required=True)
    p.add_argument("--order", choices=ORDERS, default=ORDERS[0])
    a = p.parse_args()
    run(a.tag, a.order)
