"""V6 historical Funded audit and continuous, checkpoint-preserving continuation."""
import pickle
from pathlib import Path
from prop_v6_common import *
from prop_v6_account import HarvestAccount
from prop_v6_paths import ScopedPrices
from prop_v6_signals import Calendar
from prop_v6_replay import replay
from prop_portfolio_accounts import quantity_steps
from prop_v6_measurement import MeasuredHarvest


class ReferenceAccount(MeasuredHarvest):
    """A fixed-risk measurement book must also respect the minimum lot."""
    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "entry" and self.start <= at < self.end:
            try:
                quantity_steps(trades[i], self.fixed_risk)
            except ValueError:
                self.rejected["LOT_GRID_MIN_MAX"] += 1
                return
        super().action(kind, at, i, trades, quote, mult)


def historical():
    JOB.mkdir(parents=True, exist_ok=True)
    if (JOB / "historical-checkpoint.pkl").exists():
        raise ValueError("V6_historical_checkpoint_already_exists")
    d = read(DECISION)
    for p in d["pins"]:
        if digest(p["path"]) != p["sha256"]:
            raise ValueError("V6_preholdout_pin_changed:" + p["path"])
    trades = read(V3 / "system-trades.json")
    readers = dict(XAUUSD=ScopedPrices(read(PARENT / "attempt-2/binary-manifest.json"), FINAL),
                   EURUSD=ScopedPrices(read(V3 / "system-eur-manifest.json"), FINAL))
    rolling = [HarvestAccount(stamp(f"{y}-{m:02d}-01"), END, model, rolling=True)
               for model in MODELS for y in (2022, 2023, 2024) for m in range(1, 13)]
    standalone = [HarvestAccount(stamp(f"{y}-{m:02d}-01"), FINAL, model,
                                 rolling=True, standalone=True)
                  for model in MODELS for y in (2022, 2023, 2024) for m in (1, 4, 7, 10)]
    cal = Calendar(read(CALENDAR), END)
    rows = replay(trades, readers, rolling + standalone, FINAL, cal)
    write_json(JOB / "historical-checkpoint-accounts.json", rows[:72])
    write_json(JOB / "standalone-funded-accounts.json", rows[72:])
    old = read(ROOT / "prop-cocore-v4-20261114/validation-accounts.json")
    checked = 0
    for r in rows[:72]:
        prior = next(a for a in old if a["start_msc"] == r["start_msc"] and
                     a["cell"] == r["cell"] and a["reward_interval_days"] == 14)
        for key in ("balance_usd", "accepted", "closed", "phase_passes", "payouts",
                    "peak_dd_pct", "static_loss_pct", "worst_daily_loss_pct", "rejections"):
            if r[key] != prior[key]:
                raise ValueError("V6_V4_checkpoint_parity:" + key)
        checked += 1
    write_json(JOB / "v4-checkpoint-parity.json", dict(
        status="PASS", accounts=checked, policy_checkpoint="2024-12-31",
        exact_cash_admissions_fills_phases_and_DD=True))
    with (JOB / "historical-checkpoint.pkl").open("wb") as f:
        pickle.dump(rolling, f)
    write_json(JOB / "historical-checkpoint-seal.json", dict(
        sha256=digest(JOB / "historical-checkpoint.pkl"),
        trades_sha256=digest(V3 / "system-trades.json"),
        accounts=len(rolling), cutoff=FINAL))
    event("V6_historical_complete", rolling=len(rolling), standalone=len(standalone))


def continuation(order="OPEN_LOW_HIGH_CLOSE"):
    check_freeze()
    seal = read(JOB / "historical-checkpoint-seal.json")
    if digest(JOB / "historical-checkpoint.pkl") != seal["sha256"]:
        raise ValueError("V6_checkpoint_binding")
    # Only the locally generated, hash-sealed pickle is loaded.
    with (JOB / "historical-checkpoint.pkl").open("rb") as f:
        accounts = pickle.load(f)
    for a in accounts:
        a.__class__ = MeasuredHarvest
    folder = JOB / order
    folder.mkdir(exist_ok=True)
    if (folder / "continuous-accounts.json").exists():
        raise ValueError("V6_no_duplicate_unchanged_evaluation")
    historical_trades = read(V3 / "system-trades.json")
    new = read(folder / "holdout-trades.json")
    trades = historical_trades + new
    if trades != sorted(trades, key=lambda t: (t["entry_msc"], t["role"] == "SATELLITE")):
        raise ValueError("V6_trade_indices_not_append_only")
    write_json(folder / "system-trades.json", trades)
    readers = dict(XAUUSD=ScopedPrices(read(folder / "gold-manifest.json"), END),
                   EURUSD=ScopedPrices(read(JOB / "eur-manifest.json"), END))
    fresh = [MeasuredHarvest(stamp(f"{y}-{m:02d}-01"), END, model, rolling=True)
             for model in MODELS for y, months in ((2025, range(1, 13)), (2026, range(1, 10)))
             for m in months]
    rows = replay(trades, readers, accounts + fresh, END, Calendar(read(CALENDAR), END), first=FINAL)
    write_json(folder / "continuous-accounts.json", rows[:72])
    write_json(folder / "fresh-accounts.json", rows[72:])
    references(order)
    event("V6_holdout_continuation_complete", scenario=order, accounts=len(rows))


def references(order):
    check_freeze()
    folder = JOB / order
    new = read(folder / "holdout-trades.json")
    readers = dict(XAUUSD=ScopedPrices(read(folder / "gold-manifest.json"), END),
                   EURUSD=ScopedPrices(read(JOB / "eur-manifest.json"), END))
    reference = []
    for asset in ("XAUUSD", "EURUSD"):
        subset = [t for t in new if t["asset"] == asset]
        books = [ReferenceAccount(stamp(f"{y}-01-01"), min(stamp(f"{y+1}-01-01"), END),
                                model, fixed_risk=125)
                 for model in MODELS for y in (2025, 2026)]
        # A continuous stream includes positions initiated in2025 and still open
        # in2026; standalone2026 books intentionally admit only2026 decisions.
        result = replay(subset, readers, books, END, Calendar(read(CALENDAR), END), first=FINAL)
        reference += [dict(r, asset=asset, year=2025 if r["start_msc"] == FINAL else 2026)
                      for r in result]
    write_json(folder / "holdout-reference-books.json", reference)
    event("V6_reference_books_complete", scenario=order, books=len(reference))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("historical", "continuation", "references"))
    p.add_argument("--order", default="OPEN_LOW_HIGH_CLOSE",
                   choices=("OPEN_LOW_HIGH_CLOSE", "OPEN_HIGH_LOW_CLOSE"))
    a = p.parse_args()
    historical() if a.stage == "historical" else globals()[a.stage](a.order)
