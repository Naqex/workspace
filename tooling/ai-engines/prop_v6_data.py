"""Bounded existing-cache exports and source transforms after the committed release."""
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
import subprocess
import numpy as np
from prop_campaign_source import DTYPE
from prop_portfolio_sources import BAR, merge_bars
from prop_v6_common import *
from prop_v6_paths import scenario, ScopedPrices, realize
from prop_v6_signals import Calendar, generate
from prop_atlas_source import aggregate_minutes

QDM = Path("D:/ANNAM/TradingWorkspace/projects/mt5-tradingview-backtester/foundation_v2/.runtime/quantdatamanager")


def export():
    check_freeze()
    # One QDM invocation at a time; cached exports only, no update operation.
    for asset, symbol, timeframe in (("XAUUSD", "XAUUSD_TW", "M1"),
                                      ("EURUSD", "EURUSD_TICK_TW", "TICK")):
        folder = JOB / ("export-" + asset)
        folder.mkdir(exist_ok=False)
        args = ["-data", "action=export", f"symbols={symbol}", f"timeframe={timeframe}",
                "timezone=UTC", "datefrom=2025.01.01", "dateto=2026.10.13",
                f"outputdir={folder.as_posix()}"]
        if timeframe == "TICK":
            args += ["format=Generic tick format (comma delimited)"]
        else:
            args += ["format=Custom", "cIncludeHeader=true", "cHeader=DateTime,Open,High,Low,Close",
                     "cFormat=[Date:yyyy.MM.dd HH:mm:ss],[Open],[High],[Low],[Close]"]
        event("V6_QDM_export_started", asset=asset, timeframe=timeframe)
        with (folder / "native-private.log").open("w", encoding="utf-8") as log:
            p = subprocess.run([str(QDM / "qdmcli.exe"), *args], cwd=QDM,
                               stdout=log, stderr=subprocess.STDOUT, timeout=1800,
                               creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        files = list(folder.glob("*.csv"))
        if p.returncode or len(files) != 1:
            raise ValueError("V6_QDM_export_failed:" + asset)
        write_json(folder / "receipt.json", dict(
            argv=args, cache_only=True, update_download=False, path=str(files[0]),
            size=files[0].stat().st_size, sha256=digest(files[0])))
        event("V6_QDM_export_complete", asset=asset, bytes=files[0].stat().st_size)


def aggregate(rows):
    """Paired M1 to the original Bid H1 layout, retaining exact minute counts."""
    codes = rows["t"] // HOUR * HOUR
    starts = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
    ends = np.r_[starts[1:] - 1, len(rows) - 1]
    return [[int(codes[i]), int(rows["bo"][i]), int(high), int(low),
             int(rows["bc"][j]), int(j - i + 1)]
            for i, j, high, low in zip(starts, ends,
                np.maximum.reduceat(rows["bh"], starts), np.minimum.reduceat(rows["bl"], starts))]


def save_hours(folder, values):
    folder.mkdir(exist_ok=True)
    hours = values["t"] // HOUR * HOUR
    starts = np.r_[0, np.flatnonzero(np.diff(hours)) + 1]
    ends = np.r_[starts[1:], len(values)]
    for lo, hi in zip(starts, ends):
        with (folder / f"{int(hours[lo])}.ticks").open("ab") as f:
            values[lo:hi].tofile(f)


def manifest(folder, needed=None):
    result = {}
    for p in sorted(folder.glob("*.ticks")):
        at = int(p.stem)
        if needed is None or at in needed:
            result[str(at)] = dict(path=str(p), records=p.stat().st_size // DTYPE.itemsize,
                                  sha256=digest(p))
    return result


def ingest_gold():
    import pandas as pd
    check_freeze()
    receipt = read(JOB / "export-XAUUSD/receipt.json")
    if digest(receipt["path"]) != receipt["sha256"]:
        raise ValueError("V6_gold_export_binding")
    frame = pd.read_csv(receipt["path"], dtype=str)
    if list(frame.columns) != ["DateTime", "Open", "High", "Low", "Close"]:
        raise ValueError("V6_gold_schema")
    dates = pd.to_datetime(frame["DateTime"], format="%Y.%m.%d %H:%M:%S", utc=True)
    times = dates.array.as_unit("ms").asi8
    if np.any(times < FINAL) or np.any(times >= END) or np.any(np.diff(times) <= 0):
        raise ValueError("V6_gold_time_fence_before_prices")
    rows = np.zeros(len(frame), dtype=BAR)
    rows["t"] = times
    for source, name in (("Open", "bo"), ("High", "bh"), ("Low", "bl"), ("Close", "bc")):
        scaled = pd.to_numeric(frame[source]).to_numpy() * 1000
        if np.any(np.abs(scaled - np.rint(scaled)) > 1e-6):
            raise ValueError("V6_gold_grid")
        rows[name] = np.rint(scaled).astype("int32")
    if np.any(rows["bl"] <= 0) or np.any(rows["bl"] > np.minimum(rows["bo"], rows["bc"])) or np.any(
            rows["bh"] < np.maximum(rows["bo"], rows["bc"])):
        raise ValueError("V6_gold_OHLC")
    rows.tofile(JOB / "gold-holdout-m1.bin")
    write_json(JOB / "gold-holdout-hours.json", aggregate(rows))
    write_json(JOB / "gold-source-proof.json", dict(
        rows=len(rows), first=int(times[0]), last=int(times[-1]),
        raw_sha256=receipt["sha256"], binary_sha256=digest(JOB / "gold-holdout-m1.bin"),
        resolution="BID_ONLY_M1", ask_observed=False, native_ticks=False))
    event("V6_gold_M1_admitted", minutes=len(rows), last=int(times[-1]))


def ingest_eur():
    import pandas as pd
    check_freeze()
    receipt = read(JOB / "export-EURUSD/receipt.json")
    if digest(receipt["path"]) != receipt["sha256"]:
        raise ValueError("V6_EUR_export_binding")
    folder = JOB / "eur-native-holdout"
    folder.mkdir(exist_ok=False)
    parts = []
    total = 0
    previous = FINAL - 1
    for frame in pd.read_csv(receipt["path"], dtype=str, chunksize=500000):
        labels = frame["DateTime"].str.slice(0, 8)
        if not labels.between("20250101", "20261013").all():
            raise ValueError("V6_EUR_time_fence_before_prices")
        codes, unique = pd.factorize(frame["DateTime"].str.slice(0, 11), sort=False)
        hours = np.array([int(datetime.strptime(x, "%Y%m%d %H").replace(
            tzinfo=timezone.utc).timestamp() * 1000) for x in unique], dtype="int64")
        values = np.empty(len(frame), dtype=DTYPE)
        values["t"] = (hours[codes] + frame["DateTime"].str.slice(12, 14).astype("int64").to_numpy() * 60000
                       + frame["DateTime"].str.slice(15, 17).astype("int64").to_numpy() * 1000
                       + frame["DateTime"].str.slice(18, 21).astype("int64").to_numpy())
        for name, source in (("b", "Bid"), ("a", "Ask")):
            scaled = pd.to_numeric(frame[source]).to_numpy() * 100000
            if np.any(np.abs(scaled - np.rint(scaled)) > 1e-6):
                raise ValueError("V6_EUR_grid")
            values[name] = np.rint(scaled).astype("int32")
        if (values["t"][0] < previous or np.any(np.diff(values["t"]) < 0) or
                np.any(values["t"] < FINAL) or np.any(values["t"] >= END) or
                np.any(values["b"] <= 0) or np.any(values["a"] < values["b"])):
            raise ValueError("V6_EUR_native_sequence_or_quote")
        previous = int(values["t"][-1])
        save_hours(folder, values)
        minutes = values["t"] // 60000 * 60000
        starts = np.r_[0, np.flatnonzero(np.diff(minutes)) + 1]
        ends = np.r_[starts[1:] - 1, len(values) - 1]
        bars = np.empty(len(starts), dtype=BAR)
        bars["t"] = minutes[starts]
        for prefix, source in (("b", "b"), ("a", "a")):
            px = values[source]
            bars[prefix + "o"] = px[starts]
            bars[prefix + "h"] = np.maximum.reduceat(px, starts)
            bars[prefix + "l"] = np.minimum.reduceat(px, starts)
            bars[prefix + "c"] = px[ends]
        parts.append(bars)
        total += len(frame)
        if total % 5000000 == 0:
            event("V6_EUR_native_ingest", ticks=total, last=previous)
    rows = merge_bars(parts)
    rows.tofile(JOB / "eur-holdout-m1.bin")
    write_json(JOB / "eur-holdout-hours.json", aggregate(rows))
    m = manifest(folder)
    write_json(JOB / "eur-manifest.json", m)
    write_json(JOB / "eur-source-proof.json", dict(
        raw_sha256=receipt["sha256"], ticks=total, paired_M1=len(rows), first=int(rows["t"][0]),
        last=int(rows["t"][-1]), same_ms_order_preserved=True,
        binary_sha256=digest(JOB / "eur-holdout-m1.bin"),
        resolution="OBSERVED_PAIRED_TICKS", source="existing QDM Dukascopy cache"))
    event("V6_EUR_native_admitted", ticks=total, minutes=len(rows), last=int(rows["t"][-1]))


def prepare():
    d = check_freeze()
    cal = Calendar(read(CALENDAR), END)
    all_signals = []
    for asset, stem, seed in (("XAUUSD", "gold", "gold"), ("EURUSD", "eur", "eur")):
        h = read(JOB / f"{seed}-seed-hours.json") + read(JOB / f"{stem}-holdout-hours.json")
        if any(a[0] >= b[0] for a, b in zip(h, h[1:])):
            raise ValueError("V6_causal_hour_sequence")
        raw = generate(h, asset, FINAL, END, cal)
        write_json(JOB / f"{stem}-holdout-signals.json", raw)
        all_signals += [dict(r, asset=asset) for r in raw]
    eurreader = ScopedPrices(read(JOB / "eur-manifest.json"), END)
    eur, eur_skipped = realize([r for r in all_signals if r["asset"] == "EURUSD"], eurreader, cal, END)
    write_json(JOB / "eur-holdout-trades.json", eur)
    write_json(JOB / "eur-holdout-funnel.json", dict(raw=len(read(JOB / "eur-holdout-signals.json")),
                                                   filled=len(eur), skipped=eur_skipped))
    rows = np.fromfile(JOB / "gold-holdout-m1.bin", dtype=BAR)
    for order in d["m1_paths"]:
        folder = JOB / order
        folder.mkdir(exist_ok=False)
        save_hours(folder, scenario(rows, order, spread=d["gold_m1_ask_proxy_spread_units"]))
        m = manifest(folder)
        write_json(folder / "gold-manifest.json", m)
        gold, skipped = realize([r for r in all_signals if r["asset"] == "XAUUSD"],
                               ScopedPrices(m, END), cal, END)
        trades = sorted(gold + eur, key=lambda t: (t["entry_msc"], t["role"] == "SATELLITE"))
        write_json(folder / "holdout-trades.json", trades)
        write_json(folder / "gold-holdout-funnel.json", dict(
            raw=len(read(JOB / "gold-holdout-signals.json")), filled=len(gold), skipped=skipped,
            source_claim="conditional Bid M1 plus pre-frozen Ask spread and extremum order"))
        event("V6_paths_prepared", scenario=order, gold=len(gold), eur=len(eur))


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("stage", choices=("export", "ingest_gold", "ingest_eur", "prepare"))
    globals()[p.parse_args().stage]()
