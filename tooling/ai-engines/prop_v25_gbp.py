"""Registered S01 H1-only resolution diagnostic; never an exact portfolio replay."""
from contextlib import ExitStack
from copy import deepcopy
from decimal import Decimal
from fractions import Fraction
from datetime import datetime, timezone
import math
import numpy as np
import prop_atlas_scan as atlas
import prop_v24_pareto as marked
import prop_v14_accounts as cash
import prop_v15_accounts as sizing
from prop_v25_common import *
from prop_v10_source import SEED
from quant_core.native_hourly_source import PairedHourlyStore
from quant_core.market_data_store import QUOTE
from prop_v15_evidence import bars_for
from prop_v14_paths import M1ScenarioQuotes
from prop_v25_risk import decide

HOUR, DAY = 3600000, 86400000
CELL = "GBPUSD.SWEEP.ASIA.LONDON.DAY"
SOURCE = Path("E:/BACKUP-TRADINGWORKSPACE/solo-system-20261115-04e2/research/S01-gbp-confirmation-source-v2")
CARD = PROTOCOL.with_name("GBPUSD-V25-H1-DIAGNOSTIC-CARD-20261118.md")


class H1ScenarioQuotes:
    def __init__(self, bars, order):
        self.bars, self.order = bars, order

    def points(self, first, end):
        lo, hi = self.bars["t"].searchsorted([first, end], side="left")
        if hi < len(self.bars) and self.bars["t"][hi] == end:
            hi += 1
        bars = self.bars[lo:hi]
        names = "olhc" if self.order == "OLHC" else "ohlc"
        out = np.empty(4 * len(bars), dtype=QUOTE)
        out["t"] = (bars["t"][:, None] + np.array([0, HOUR // 3, 2 * HOUR // 3, HOUR - 1])).ravel()
        for side in ("b", "a"):
            out[side] = np.column_stack([bars[side + n] for n in names]).ravel()
        return out[out["t"] <= end]


def exact_pass(spread, distance, percent):
    return distance > 0 and 100 * (int(spread) + 9) <= percent * int(distance)


def source():
    index_path = ROOT / "ensemble-and-storage-v11-20261115/source-admission-v11.json"
    index = deepcopy(read(index_path)["hourly_indices"]["GBPUSD"])
    index["books"] = [b for b in index["books"] if b["last"] < DEV_END]
    bars = PairedHourlyStore(index, SEED, DEV_END).bars()
    original = bars.copy()
    card = read(SOURCE / "correction-card.json")
    proof = read(SOURCE / "source-proof.json")
    assert sha(SOURCE / "correction-card.json") == "911d3f8cce8c3ddb4df11f16fcefece15134b6e5c8341a2250372e8404df2abe"
    assert sha(SOURCE / "source-proof.json") == "63e8a491454e6ceeaed47798be94e840426475d0d6609e8d0a9af5fde1551ee7"
    assert (proof["status"] == "SOURCE_RECONCILED" and proof["expected_hours"] == proof["admitted_hours"] == 3576
            and proof["paired_tick_records"] == 25537048 and proof["h1_difference_count"] == 0 and not proof["empty_hours"])
    for side, prefix in (("bid", "b"), ("ask", "a")):
        for change in card["changes"][side]:
            i = int(bars["t"].searchsorted(change["at"]))
            assert int(bars["t"][i]) == change["at"]
            names = [prefix + n for n in "ohlc"]
            assert [int(bars[n][i]) for n in names] == change["original_units"]
            for name, value in zip(names, change["corrected_units"]):
                bars[name][i] = value
    return bars, original, dict(index_sha256=sha(index_path),
        correction_sha256=sha(SOURCE / "correction-card.json"),
        proof_sha256=sha(SOURCE / "source-proof.json"), books=index["books"])


def signals(bars):
    hours = [[int(r[n]) for n in ("t", "bo", "bh", "bl", "bc")] + [60] for r in bars]
    with bindings(atlas, START=FIRST, END=DEV_END):
        rows, abstentions = atlas.candidates(hours, "GBPUSD", first=FIRST, end=DEV_END, only_cells=[CELL])
    expected = read(SOURCE / "registration.json")["signals"]
    actual = [r for r in rows if 1640995200000 <= r["decision_msc"] < DEV_END]
    key = lambda r: (r["decision_msc"], r["side"], r["stop_units"])
    parity = dict(expected=len(expected), actual=len(actual),
                  equal=sorted(map(key, expected)) == sorted(map(key, actual)))
    return rows, parity, abstentions


def scenario_trades(rows, bars, order):
    reader = H1ScenarioQuotes(bars, order)
    trades, rejected, missing, geometry = [], [], [], []
    for row in rows:
        at = row["decision_msc"]
        i = int(bars["t"].searchsorted(at))
        end = at // DAY * DAY + 20 * HOUR
        j = int(bars["t"].searchsorted(end))
        if i >= len(bars) or j >= len(bars) or int(bars["t"][i]) != at or int(bars["t"][j]) != end:
            missing.append(dict(at=at, endpoint=end))
            continue
        buy = row["side"] == "BUY"
        entry = int(bars["ao" if buy else "bo"][i])
        distance = (entry - row["stop_units"]) * (1 if buy else -1)
        spread = int(bars["ao"][i] - bars["bo"][i])
        float_gate = distance > 0 and ((spread / 100000 + .00009) / (distance / 100000) <= .15)
        accepted = exact_pass(spread, distance, 15)
        geometry.append(dict(at=at, side=row["side"], distance=distance, spread=spread,
                             float15=float_gate, exact15=accepted, exact12=exact_pass(spread, distance, 12)))
        if not accepted:
            rejected.append(at)
            continue
        q = reader.points(at, end)
        field = "b" if buy else "a"
        hits = np.flatnonzero(q[field] <= row["stop_units"] if buy else q[field] >= row["stop_units"])
        exit_at, price, reason = end, int(q[field][-1]), "SESSION_2000_SCENARIO"
        if len(hits):
            hit = int(hits[0])
            exit_at = int(q["t"][hit])
            if hit == 0 or exit_at % HOUR == 0:
                price = min(int(q[field][hit]), row["stop_units"]) if buy else max(int(q[field][hit]), row["stop_units"])
            else:
                before, after = int(q[field][hit-1]), int(q[field][hit])
                dt = int(q["t"][hit] - q["t"][hit-1])
                elapsed = math.ceil(Fraction(abs(row["stop_units"]-before) * dt, abs(after-before)))
                exit_at = int(q["t"][hit-1]) + max(1, elapsed)
                price = row["stop_units"]
            reason = "SL"
        gap = bool(np.any(np.diff(bars["t"][i:j+1]) > HOUR))
        trades.append(dict(id="GBPUSD|S1:ASIA_SWEEP_LONDON|DAY|P0", asset="GBPUSD",
            side=row["side"], decision_msc=at, entry_msc=at, exit_msc=exit_at,
            entry_price_units=entry, exit_price_units=price, stop_units=row["stop_units"],
            deadline_msc=end, spread_units=spread, natural=distance/100000,
            reason=reason, source_uncertain=True, hourly_gap=gap, exact_intrahour_path=False))
    return trades, reader, dict(geometry=geometry, rejects=rejected, missing_endpoints=missing)


def money_bindings():
    stack = ExitStack()
    values = dict(marked.VALUE, GBPUSD=10)
    stack.enter_context(bindings(marked, VALUE=values))
    stack.enter_context(bindings(sizing, VALUE=values))
    stack.enter_context(bindings(cash, VALUE=values, SLIP=dict(cash.SLIP, GBPUSD=10)))
    return stack


def tails(trades, weight):
    values = [cash.trade_money(t, sizing.exact_quantity(t, 150*weight), "SYM_FLAT", 150)["net_R"] for t in trades]
    best = sorted(values, reverse=True)
    return dict(trades=len(values), net_R=sum(values), ExTop5=sum(values)-sum(best[:5]),
                ExTop10=sum(values)-sum(best[:10]),
                winrate=sum(v>0 for v in values)/len(values) if values else None)


def run():
    save("GBP-registration.json", dict(card_sha256=sha(CARD), code_sha256=sha(__file__),
        protocol_sha256=sha(PROTOCOL), Development=[FIRST, DEV_END], diagnostic_only=True,
        exit_change="S01 20:30 -> registered H1 20:00 scenario; not source parity"))
    bars, old, pins = source()
    rows, parity, abstentions = signals(bars)
    base_bars = {a: bars_for(a, True) for a in ("XAUUSD", "EURUSD")}
    cases = []
    for order in ("OLHC", "OHLC"):
        trades, reader, funnel = scenario_trades(rows, bars, order)
        baseline = read(V19 / f"Dev-{order}-PRIMARY-trades.json")
        readers = {a: M1ScenarioQuotes(b, "OPEN_LOW_HIGH_CLOSE" if order == "OLHC" else "OPEN_HIGH_LOW_CLOSE",
                                      FIRST, DEV_END) for a,b in base_bars.items()}
        readers["GBPUSD"] = reader
        with money_bindings():
            standalone = marked.measure(trades, marked.prepare(trades, readers), {})
            joined = baseline + trades
            points = marked.prepare(joined, readers)
            base = marked.measure(baseline, marked.prepare(baseline, readers), {})
            satellites = []
            for weight in (.25, .5):
                metrics = marked.measure(joined, points, {"S1":weight})
                check = decide(metrics, base)
                satellites.append(dict(weight=weight, conditional_marked_book=check,
                    decision="INCONCLUSIVE_PATH", gate_passed=False,
                    reasons=["H1_INTRAHOUR_PATH_NOT_CERTIFIED"], tails=tails(trades, weight)))
            annual = []
            for year in range(2018, 2024):
                cohort = [t for t in trades if datetime.fromtimestamp(t["entry_msc"]/1000,timezone.utc).year == year]
                annual.append(dict(year=year, **tails(cohort, 1)))
        cases.append(dict(order=order, standalone_scenario=standalone, annual=annual,
            satellites=satellites, float_vs_exact15_deltas=[g for g in funnel["geometry"] if g["float15"]!=g["exact15"]],
            raw=len(rows), accepted=len(trades), rejected=len(funnel["rejects"]), missing=len(funnel["missing_endpoints"])))
        compressed("GBP-"+order+"-scenario", dict(trades=trades,funnel=funnel))
    result = dict(cases=cases, signal_parity2022_2023=parity, pins=pins, abstentions=abstentions,
        status="INCONCLUSIVE_PATH", prop_qualified=False, target_calendar_certified=False,
        original20h30_replayed=False, new_price_rows_added=0, prices2024_2026_read=False)
    save("GBP-H1-diagnostic.json", result)
    import json
    print(json.dumps(dict(stage="GBP_H1_diagnostic_complete", signal_parity=parity, cases=cases)), flush=True)


if __name__ == "__main__":
    run()
