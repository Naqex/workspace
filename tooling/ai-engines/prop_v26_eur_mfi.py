"""Admit observed EURUSD tick counts for six previously blocked V26 cells."""
import hashlib
import json
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import numpy as np

import prop_v26_common as common
from prop_v26_batch import CARD, deadlines
from prop_v26_common import DEV_END, FIRST, ROOT, activate_runtime, bindings, compressed, read, save, sha
from prop_v15_evidence import bars_for
from prop_v6_data import aggregate
from prop_v10_signals import frame
from quant_core.corpus_batch_signals import signals
from quant_core.ftmo_execution_and_calendar import gold_calendar
from quant_core.job_workspace import JobWorkspace
from quant_core.vectorized_sl_active_kernel import money
from quant_core.vectorized_stage0_scanner import HOUR, endpoint_indices

JOB = JobWorkspace(ROOT / "batch-exact-iso-v26-20261118" / "eur-mfi", Path(__file__).resolve().parents[2])


def source_counts(hourly):
    history = ROOT / "eurusd-observed-history-v2"
    seals = read(ROOT / "evidence-and-lifecycle-v14-20261115/source-dev-admission.json")["native_csv_hashes"]
    b0 = read(ROOT / "eurusd-b0-20261113/config-attempt-1.json")
    counts, receipts = {}, []
    for year in range(2017, 2024):
        if year < 2023:
            folder = history / str(year) / "attempt-1"
            export = read(folder / "export-command.json")
            assert {"timeframe=TICK", "timezone=UTC", f"datefrom={year}.01.01",
                    f"dateto={year}.12.31"} <= set(export["argv"])
            raw = folder / "export/EURUSD_TICK_TW-TICK-No Session.csv"
            cache = read(folder / "result.json")["hourly_cache"]
            path = Path(cache["path"])
            assert sha(path) == cache["sha256"]
            expected = seals[str(raw)] if str(raw) in seals else sha(raw)
        else:
            cfg = next(s for s in b0["sources"] if s["first_day"] == "20230101")
            path = ROOT / "historical-hours/coarse-hours-f281d454fd4040fa5a3a3cf92c447720db19d78c7c7c9b26da94e2e111c53ab3.json"
            expected = cfg["sha256"]
        data = read(path)
        body = data["payload"]
        canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()
        assert hashlib.sha256(canonical).hexdigest() == data["payload_sha256"]
        binding = body["binding"]
        assert (binding["first_day"], binding["last_day"], binding["sha256"]) == (
            f"{year}0101", f"{year}1231", expected)
        total = 0
        for row in body["hours"]:
            at = row["mid"]["timestamp"] * 1000
            count = row["ticks"]
            assert type(count) is int and count > 0 and at not in counts
            assert datetime.fromtimestamp(at / 1000, timezone.utc).year == year
            assert at <= row["first_time_msc"] <= row["last_time_msc"] < at + HOUR
            assert row["last_sequence"] - row["first_sequence"] + 1 == count
            counts[at] = (count, tuple(int(Decimal(p) * 100000) for p in row["bid"]))
            total += count
        assert total == body["ticks"]
        receipts.append(dict(year=year, cache_sha256=sha(path), source_sha256=expected, ticks=total))
    coverage = [counts.get(row[0]) for row in hourly]
    if any(count is None for count in coverage):
        return None, dict(sources=receipts, missing_hours=sum(count is None for count in coverage))
    mismatch = sum(tuple(r[1:5]) != count[1] for r, count in zip(hourly, coverage))
    return (None if mismatch else np.asarray([count[0] for count in coverage]),
            dict(sources=receipts, missing_hours=0, bid_ohlc_mismatches=mismatch, hours=len(hourly)))


def run():
    activate_runtime()
    card = read(CARD)
    save("registration.json", dict(card_sha256=sha(CARD), source_sha256=sha(__file__),
        scope="Six EURUSD MFI cells blocked at original V26 Stage-0", validation_prices=False,
        source_contract="Checksummed observed tick counts, exact hourly Bid OHLC agreement"))
    bars = bars_for("EURUSD", True)
    hourly = [row for row in aggregate(bars) if row[5] == 60]
    volume, receipt = source_counts(hourly)
    save("tick-count-admission.json", receipt)
    if volume is None:
        print(receipt, flush=True)
        return
    candles = frame(hourly, HOUR)
    flats = np.asarray(gold_calendar(FIRST, DEV_END).times, dtype="int64")
    results = []
    for profile in card["profiles"][1:]:
        if profile["oscillator"] != "MFI":
            continue
        side = signals(candles, profile["pattern"], "MFI", volume)
        use = (side != 0) & (candles["t"] >= FIRST) & (candles["t"] < DEV_END)
        decision, side = candles["t"][use].astype("int64"), side[use]
        years = decision.astype("datetime64[ms]").astype("datetime64[Y]").astype(int) + 1970
        entry, valid = endpoint_indices(bars, decision, DEV_END)
        at = bars["t"][entry]
        price = np.where(side == 1, bars["ao"][entry], bars["bo"][entry])
        spread = bars["ao"][entry] - bars["bo"][entry]
        natural = np.maximum(200, spread)
        friction = spread + 9
        accepted = 100 * friction <= 12 * natural
        retention = float(accepted.mean()) if len(at) else 0.0
        ratio = float(np.median(friction) / np.median(natural)) if len(at) else None
        reasons = []
        if retention < .5:
            reasons.append("RETENTION_BELOW50")
        if ratio is None or 100 * np.median(friction) > 12 * np.median(natural):
            reasons.append("MEDIAN_SCALE_FAIL")
        markout = []
        for horizon in (8, 4):
            end = deadlines(at, horizon, flats, False)
            exit_i, known = endpoint_indices(bars, end, DEV_END)
            known &= valid & (end >= at) & (bars["t"][exit_i] >= end)
            exit_price = np.where(side == 1, bars["bo"][exit_i], bars["ao"][exit_i])
            net = money("EURUSD", "SYM", side, price, exit_price, at,
                        np.maximum(at, bars["t"][exit_i]), np.full(len(at), "HORIZON"))["net"]
            annual = []
            for year in range(2018, 2024):
                mask = years == year
                good = mask & known
                count, priced = int(mask.sum()), int(good.sum())
                mn = float(net[good].mean()) if priced else None
                mf = float((friction[good] / 100000).mean()) if priced else None
                annual.append(dict(year=year, signals=count, priced=priced, mean_net=mn, mean_friction=mf))
                if horizon != 8:
                    continue
                if count < 40:
                    reasons.append(f"{year}:CADENCE_BELOW40")
                if mn is None or mn <= 0 or mn < mf:
                    reasons.append(f"{year}:MARKOUT_FAIL")
                if priced != count:
                    reasons.append(f"{year}:ENDPOINT_INCOMPLETE")
            markout.append(dict(hours=horizon, annual=annual))
        results.append(dict(rank=profile["rank"], file=profile["file"], asset="EURUSD", oscillator="MFI",
            pattern=profile["pattern"], resolution="M1", status="STAGE0_FAIL" if reasons else "STAGE0_PASS",
            stage0_passed=not reasons, raw_signals=len(at), reasons=reasons, markout=markout,
            trades_per_year=[r["signals"] for r in markout[0]["annual"]],
            friction_pass_rate=retention, friction_SL=ratio, clusters_R=None, net_R=None,
            max_R_DD=None, daily_correlation=None, SL_active=False))
    compressed("results", results)
    print([(r["rank"], r["status"], r["raw_signals"]) for r in results], flush=True)


if __name__ == "__main__":
    with bindings(common, JOB=JOB.root, RUNTIME=JOB):
        run()
