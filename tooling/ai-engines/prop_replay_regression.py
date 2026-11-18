"""Compare sealed BASE_GUARD exits to same-entry Development markouts."""
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean, median

import numpy as np

from prop_n1_screen import DEVELOPMENT_YEARS, WORKSPACE, classify, verify_commit
from prop_v14_accounts import trade_money
from prop_v15_accounts import exact_quantity
from prop_v15_evidence import bars_for
from prop_v21_common import compressed, save
from prop_v26_common import DEV_END, FIRST, ROOT, V19, read, sha
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
from quant_core.vectorized_stage0_scanner import DAY, endpoint_indices
import prop_v21_common as evidence

PROTOCOL = WORKSPACE / "planning/research/PROP-REPLAY-REGRESSION-PROTOCOL-20261118.md"
BASE = ROOT / "prop-replay-regression-20261118"


def identity(trade):
    return trade["id"], trade["source_event"]


def net(trade, quantity):
    return round(trade_money(trade, quantity, "SYM_FLAT", 150)["net_usd"] * 100)


def measure(bars, primary, strict):
    deadline = int(primary["deadline_msc"])
    entry = int(primary["entry_msc"])
    if not FIRST <= entry <= deadline < DEV_END or deadline // DAY != entry // DAY:
        raise ValueError("REGRESSION_DEVELOPMENT_DEADLINE")
    qty = exact_quantity(primary, 150)
    entry_price = primary["entry_price_units"]
    side = 1 if primary["side"] == "BUY" else -1
    e = int(bars["t"].searchsorted(entry))
    if e == len(bars) or bars["t"][e] != entry or bars["ao" if side == 1 else "bo"][e] != entry_price:
        raise ValueError("REGRESSION_SEALED_ENTRY_PRICE_MISMATCH")
    lookup, found = endpoint_indices(bars, np.array([deadline]), DEV_END)
    x = int(lookup[0]); exit_at = int(bars["t"][x]); eligible = bool(found[0] and exit_at // DAY == entry // DAY)
    stop_dist = abs(entry_price - primary["stop_units"])
    record = dict(id=primary["id"], source_event=primary["source_event"], entry=entry,
                  year=datetime.fromtimestamp(entry / 1000, timezone.utc).year, deadline=deadline,
                  quantity_steps=qty, primary_net_cents=net(primary, qty), strict_net_cents=net(strict, qty),
                  primary_reason=primary["reason"], strict_reason=strict["reason"],
                  source_uncertain=primary["source_uncertain"], natural_steps=stop_dist,
                  markout_cents=None, markout_steps=None, friction_steps=None, pass_cost=False)
    if not eligible:
        return record
    exit_price = int(bars["bo" if side == 1 else "ao"][x])
    time_only = dict(primary, exit_msc=exit_at, exit_price_units=exit_price, reason="HORIZON")
    cost = trade_money(time_only, qty, "SYM_FLAT", 150)
    step_value = 1 if primary["asset"] == "XAUUSD" else 10  # milli-USD / price step / quantity step
    friction_milli = round(1000 * (cost["commission_usd"] + cost["slippage_usd"] - cost["swap_usd"]))
    spread = int(bars["ao"][e]) - int(bars["bo"][e])
    friction = spread + friction_milli / (qty * step_value)
    record.update(exit_at=exit_at, exit_price=exit_price, markout_cents=net(time_only, qty),
                  markout_steps=side * (exit_price - entry_price) - friction_milli / (qty * step_value),
                  friction_steps=friction, pass_cost=(100 * (spread * qty * step_value + friction_milli)
                  <= 12 * stop_dist * qty * step_value))
    return record


def stats(rows):
    priced = [r for r in rows if r["markout_cents"] is not None]
    return dict(raw=len(rows), priced=len(priced), coverage=len(priced) / len(rows) if rows else None,
                mean_net=mean(r["markout_steps"] for r in priced) if priced else None,
                mean_friction=mean(r["friction_steps"] for r in priced) if priced else None,
                median_scale=(median(r["friction_steps"] for r in priced) / median(r["natural_steps"] for r in priced))
                if priced else None, retention=sum(r["pass_cost"] for r in rows) / len(rows) if rows else None,
                primary_cents=sum(r["primary_net_cents"] for r in rows),
                strict_cents=sum(r["strict_net_cents"] for r in rows),
                primary_matched_cents=sum(r["primary_net_cents"] for r in priced),
                strict_matched_cents=sum(r["strict_net_cents"] for r in priced),
                time_only_cents=sum(r["markout_cents"] for r in priced),
                source_uncertain=sum(r["source_uncertain"] for r in rows))


def main():
    verify_commit(PROTOCOL)
    verify_commit(__file__)
    runtime = JobWorkspace(BASE / "exit-audit-v2", WORKSPACE)
    output = runtime.activate()
    try:
        primary = V19 / "Dev-OLHC-PRIMARY-trades.json"
        strict = V19 / "Dev-OLHC-STRICT-trades.json"
        others = [V19 / f"Dev-OHLC-{mode}-trades.json" for mode in ("PRIMARY", "STRICT")]
        admission = ROOT / "evidence-and-lifecycle-v14-20261115/source-dev-admission.json"
        with bindings(evidence, JOB=output):
            paths = [primary, strict, *others]
            save("registration.json", dict(files={p.name: sha(p) for p in [*paths, admission, PROTOCOL, Path(__file__)]},
                 first=FIRST, cutoff_exclusive=DEV_END))
            base, adverse, alt, alt_adverse = (read(p) for p in paths)
            by_strict = {identity(t): t for t in adverse}
            def binding(rows):
                return {identity(t): (t["entry_msc"], t["entry_price_units"], t["stop_units"], t["deadline_msc"],
                                      t["exit_msc"] // DAY, t["exit_price_units"], t["reason"],
                                      net(t, exact_quantity(t, 150))) for t in rows}
            if binding(base) != binding(alt) or binding(adverse) != binding(alt_adverse):
                raise ValueError("REGRESSION_V19_ECONOMICS_DIVERGE_BY_ORDERING")
            timestamp_deltas = {}
            for label, olhc, ohlc in (("PRIMARY", base, alt), ("STRICT", adverse, alt_adverse)):
                times = {identity(t): t["exit_msc"] for t in ohlc}
                differences = [abs(t["exit_msc"] - times[identity(t)]) for t in olhc]
                timestamp_deltas[label] = dict(changed=sum(d > 0 for d in differences), max_msc=max(differences))
            if set(by_strict) != {identity(t) for t in base} or len(by_strict) != len(base):
                raise ValueError("REGRESSION_V19_COHORT_MISMATCH")
            bars = {asset: bars_for(asset, True) for asset in ("EURUSD", "XAUUSD")}
            rows = [measure(bars[t["asset"]], t, by_strict[identity(t)]) for t in base]
            sleeves = {}
            for name in sorted({t["id"] for t in rows}):
                subset = [r for r in rows if r["id"] == name]
                annual = [dict(year=year, **stats([r for r in subset if r["year"] == year])) for year in DEVELOPMENT_YEARS]
                sleeves[name] = dict(total=stats(subset), annual=annual, gate_reasons=classify(annual),
                  clusters=[stats([r for r in subset if low <= r["year"] < high]) for low, high in ((2018, 2021), (2021, 2024))])
            compressed("exit-rows", rows)
            save("exit-audit.json", dict(sleeves=sleeves, total=stats(rows), exit_timestamp_deltas=timestamp_deltas,
                 registration_sha256=sha(output / "registration.json")))
            print(output, flush=True)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
