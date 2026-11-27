"""Coverage evidence, with declared session breaks kept separate from gaps."""
from collections import Counter
from datetime import datetime, timezone, timedelta
import numpy as np
from prop_v6_common import *
from prop_v6_paths import ScopedPrices
from prop_portfolio_sources import BAR
from prop_portfolio_scan import gap_unknown


def inspect():
    check_freeze()
    calendar = {r["day"]: r for r in read(CALENDAR)["events"]}
    assets = []
    for asset, stem in (("XAUUSD", "gold"), ("EURUSD", "eur")):
        bars = np.fromfile(JOB / f"{stem}-holdout-m1.bin", dtype=BAR)
        days = []
        d = datetime(2025, 1, 1, tzinfo=timezone.utc)
        while int(d.timestamp() * 1000) < END:
            day = int(d.timestamp() * 1000)
            text = d.date().isoformat()
            record = calendar.get(text, {})
            lo, hi = bars["t"].searchsorted([day + 7 * HOUR, day + 21 * HOUR])
            a = bars["t"][lo:hi]
            grid = np.r_[day + 7 * HOUR, a, day + 21 * HOUR]
            gap = int(np.diff(grid).max()) / 60000
            kind = ("WEEKEND" if d.weekday() >= 5 else
                    "DECLARED_HOLIDAY_OR_EARLY" if record else
                    "UNRESOLVED_MAIN_SESSION_GAP" if gap > 15 else "MAIN_SESSION_TIMESTAMP_COMPLETE")
            days.append(dict(day=text, classification=kind, records=len(a),
                             maximum_gap_minutes=gap))
            d += timedelta(days=1)
        assets.append(dict(asset=asset, source=read(JOB / f"{stem}-source-proof.json"),
                           day_counts=dict(Counter(r["classification"] for r in days)), days=days))
    orders = []
    for order in read(DECISION)["m1_paths"]:
        folder = JOB / order
        trades = read(folder / "holdout-trades.json")
        readers = dict(XAUUSD=ScopedPrices(read(folder / "gold-manifest.json"), END),
                       EURUSD=ScopedPrices(read(JOB / "eur-manifest.json"), END))
        evidence = []
        for i, t in enumerate(trades):
            reader = readers[t["asset"]]
            finish = min(t["exit_msc"], END - 1,
                         t["deadline_msc"] if t["reason"] == "ENDPOINT_UNKNOWN_OPEN" else END - 1)
            a, _ = reader.path(t["entry_msc"], finish)
            gaps = gap_unknown(a["t"], 0)
            evidence.append(dict(
                trade=i, asset=t["asset"], day=t["day"], reason=t["reason"],
                observed_path_rows=len(a), entry_wait_ms=t["entry_msc"] - t["decision_msc"],
                endpoint_wait_ms=(t["exit_msc"] - t["deadline_msc"]
                                  if t["reason"] not in ("SL", "CENSORED", "ENDPOINT_UNKNOWN_OPEN") else None),
                unresolved_gaps=[[int(a), int(b)] for a, b in gaps],
                path_resolution=t["path_resolution"],
                complete_under_declared_path_model=not gaps and t["reason"] != "ENDPOINT_UNKNOWN_OPEN",
                exact_native_path=t["asset"] == "EURUSD" and not gaps))
        orders.append(dict(scenario=order, trades=len(trades), evidence=evidence,
                           trades_with_unresolved_gaps=sum(bool(r["unresolved_gaps"]) for r in evidence),
                           endpoint_unknown=sum(r["reason"] == "ENDPOINT_UNKNOWN_OPEN" for r in evidence),
                           right_censored=sum(r["reason"] == "CENSORED" for r in evidence),
                           native_exact_trades=sum(r["exact_native_path"] for r in evidence),
                           conditional_Gold_trades=sum(r["asset"] == "XAUUSD" for r in evidence)))
        event("V6_held_path_coverage", scenario=order,
              unknown=sum(not r["complete_under_declared_path_model"] for r in evidence))
    write_json(JOB / "holdout-path-quality.json", dict(
        assets=assets, scenarios=orders, pristine_global_OOS_certified=False,
        FTMO_quote_compliance_certified=False, tick_M1_separation=True))


if __name__ == "__main__":
    inspect()
