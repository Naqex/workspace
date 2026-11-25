"""Rank saved Development gap-crossing trades without reading market quotes."""
from collections import defaultdict

from prop_n1_screen import BASE, WORKSPACE
from prop_v14_accounts import trade_money
from prop_v15_accounts import exact_quantity
from prop_v26_common import DEV_END, FIRST, V19, read, sha
from prop_v21_common import compressed
from quant_core.job_workspace import JobWorkspace
from quant_core.prop_lifecycle_and_parity import bindings
import prop_v21_common as evidence


def identity(trade):
    return trade["id"], trade["source_event"]


def trade_index(path):
    rows = read(path)
    indexed = {identity(row): row for row in rows}
    if len(indexed) != len(rows) or any(not FIRST <= row["entry_msc"] < DEV_END for row in rows):
        raise ValueError("N1_GAP_DEV_LEDGER_INVALID")
    return indexed


def read_books():
    comparisons = defaultdict(dict)
    pins = {}
    for ordering in ("OLHC", "OHLC"):
        primary_path = V19 / f"Dev-{ordering}-PRIMARY-trades.json"
        strict_path = V19 / f"Dev-{ordering}-STRICT-trades.json"
        pins.update({path.name: sha(path) for path in (primary_path, strict_path)})
        primary, strict = trade_index(primary_path), trade_index(strict_path)
        for key, base in primary.items():
            if key not in strict:
                continue
            stressed = strict[key]
            for field in ("entry_msc", "entry_price_units", "stop_units", "asset", "side"):
                if base[field] != stressed[field]:
                    raise ValueError("N1_GAP_MATCHED_ENTRY_CHANGED")
            qty = exact_quantity(base, 150)
            money = [round(trade_money(row, qty, "SYM_FLAT", 150)["net_usd"] * 100)
                     for row in (base, stressed)]
            comparisons[(base["id"], base["entry_msc"])][ordering] = dict(
                source_event=key[1], quantity_steps=qty, primary_cents=money[0],
                strict_cents=money[1], delta_cents=money[0] - money[1],
                primary_reason=base["reason"], strict_reason=stressed["reason"],
                primary_exit=base["exit_msc"], strict_exit=stressed["exit_msc"])
    return comparisons, pins


def rank(rows, comparisons):
    intervals, occurrences = defaultdict(dict), defaultdict(int)
    for row in rows:
        if not FIRST <= row["first_unknown"] < DEV_END:
            continue
        gap = (row["asset"], row["before"], row["after"])
        key = (row["id"], row["entry"])
        if key in intervals[gap]:
            raise ValueError("N1_GAP_DUPLICATE_TRADE_OCCURRENCE")
        intervals[gap][key] = row
        occurrences[key] += 1
    ranked = []
    for (asset, before, after), matches in intervals.items():
        trades = [dict(id=key[0], entry=key[1], grouped_gaps=occurrences[key],
                       orderings=comparisons.get(key, {})) for key in sorted(matches)]
        deltas = [row["delta_cents"] for trade in trades for row in trade["orderings"].values()]
        max_delta = max(deltas) if deltas else None
        both = all(len(trade["orderings"]) == 2 for trade in trades)
        ranked.append(dict(asset=asset, before=before, after=after,
                           first_unknown=min(row["first_unknown"] for row in matches.values()),
                           missing_minutes=next(iter(matches.values()))["missing"],
                           max_trade_delta_cents=max_delta, both_orderings_present=both,
                           status="UNMATCHED" if not deltas else "PARTIAL_MATCH" if not both else
                                  "ADVERSE_DELTA" if max_delta > 0 else "NO_ADVERSE_DELTA",
                           trades=trades))
    ranked.sort(key=lambda row: (row["max_trade_delta_cents"] is None,
                                -(row["max_trade_delta_cents"] or 0),
                                row["first_unknown"], row["asset"]))
    return ranked


def main():
    source = V19 / "gap-identities.json"
    probe = V19 / "source-probe-verdict.json"
    prior = read(probe)
    comparisons, pins = read_books()
    pins.update({path.name: sha(path) for path in (source, probe)})
    if pins[source.name] != prior["bindings"][source.name]:
        raise ValueError("N1_GAP_IDENTITY_HASH_CHANGED")
    gaps = rank(read(source)["rows"], comparisons)
    runtime = JobWorkspace(BASE / "gaps", WORKSPACE)
    root = runtime.activate()
    try:
        with bindings(evidence, JOB=root):
            compressed("gap-ranking", dict(gaps=gaps, input_pins=pins,
                                           first=FIRST, cutoff_exclusive=DEV_END,
                                           reference_risk_usd=150, price_files_opened=0))
        print(root)
    finally:
        runtime.close()


if __name__ == "__main__":
    main()
