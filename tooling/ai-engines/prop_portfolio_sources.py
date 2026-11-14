"""Bounded existing M1 sources and deterministic V3 endpoint-clock repair."""
from datetime import datetime, timezone
from pathlib import Path
from zoneinfo import ZoneInfo
import numpy as np

from prop_atlas_source import load_us500
from prop_atlas_scan import exit_deadline
from prop_portfolio_common import (
    ROOT, JOB, ATLAS, START, END, HOUR, DAY, read, write_json, digest, event,
)

MINUTE = 60000
NY = ZoneInfo("America/New_York")
BAR = np.dtype([(name, "<i8" if name == "t" else "<i4") for name in
                ("t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")])


def deadline(row, entry):
    end, reason = exit_deadline(row, entry)
    if row["asset"] == "US500":
        local = datetime.fromtimestamp(end / 1000, timezone.utc).astimezone(NY)
        clock = local.hour * 60 + local.minute
        if 16 * 60 + 15 <= clock < 18 * 60:
            end = int(local.replace(hour=16, minute=0, second=0,
                                    microsecond=0).timestamp() * 1000)
            reason = "SOURCE_BREAK_PRE_FLAT_1600_NY"
    if end <= entry:
        raise ValueError("no_liquid_holding_window")
    return end, reason


def merge_bars(parts):
    rows = np.concatenate(parts)
    starts = np.r_[0, np.flatnonzero(np.diff(rows["t"])) + 1]
    ends = np.r_[starts[1:] - 1, len(rows) - 1]
    result = rows[starts].copy()
    for name in ("bh", "ah"):
        result[name] = np.maximum.reduceat(rows[name], starts)
    for name in ("bl", "al"):
        result[name] = np.minimum.reduceat(rows[name], starts)
    for name in ("bc", "ac"):
        result[name] = rows[name][ends]
    if np.any(np.diff(result["t"]) <= 0):
        raise ValueError("M1_order")
    return result


def prepare_eur():
    import pandas as pd
    cfg = read(ROOT / "eurusd-b0-20261113/config-attempt-1.json")
    parts = []
    sources = []
    for source in cfg["sources"]:
        if source["first_day"] not in ("20220101", "20230101"):
            continue
        if source["last_day"] not in ("20221231", "20231231"):
            raise ValueError("EUR_development_annual_only")
        if digest(source["path"]) != source["sha256"]:
            raise ValueError("EUR_admitted_raw_changed")
        count = 0
        for frame in pd.read_csv(
                source["path"], usecols=["DateTime", "Bid", "Ask"],
                dtype=str, chunksize=500000, engine="c"):
            dates = frame["DateTime"].str.slice(0, 8)
            if not dates.between(source["first_day"], source["last_day"]).all():
                raise ValueError("EUR_price_fence_before_price_parse")
            labels = frame["DateTime"].str.slice(0, 14)
            codes, unique = pd.factorize(labels, sort=False)
            times = np.array([
                int(datetime.strptime(x, "%Y%m%d %H:%M").replace(
                    tzinfo=timezone.utc).timestamp() * 1000) for x in unique
            ], dtype="<i8")
            if np.any(np.diff(times) <= 0):
                raise ValueError("EUR_minute_clock_order")
            bid = frame["Bid"].str.replace(".", "", regex=False).astype("int32").to_numpy()
            ask = frame["Ask"].str.replace(".", "", regex=False).astype("int32").to_numpy()
            if np.any(bid <= 0) or np.any(ask < bid):
                raise ValueError("EUR_crossed_quotes")
            starts = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
            ends = np.r_[starts[1:] - 1, len(codes) - 1]
            rows = np.empty(len(starts), dtype=BAR)
            rows["t"] = times[codes[starts]]
            for prefix, values in (("b", bid), ("a", ask)):
                rows[prefix + "o"] = values[starts]
                rows[prefix + "h"] = np.maximum.reduceat(values, starts)
                rows[prefix + "l"] = np.minimum.reduceat(values, starts)
                rows[prefix + "c"] = values[ends]
            parts.append(rows)
            count += len(frame)
            if count % 5000000 == 0:
                event("EUR_paired_M1_prepare", year=source["first_day"][:4], ticks=count)
        sources.append(dict(path=source["path"], sha256=source["sha256"],
                            ticks=count, first=source["first_day"], last=source["last_day"]))
    rows = merge_bars(parts)
    if rows["t"][0] < START or rows["t"][-1] >= END:
        raise ValueError("EUR_M1_price_fence")
    path = JOB / "EURUSD-dev-m1.bin"
    rows.tofile(path)
    write_json(JOB / "EURUSD-dev-m1-source.json", dict(
        sources=sources, binary_sha256=digest(path), bars=len(rows),
        schema=BAR.descr, paired_from_same_ticks=True, no2024_2026=True,
    ))
    event("EUR_M1_ready", bars=len(rows))


def prepare_us500():
    _, reader, pins = load_us500()
    rows = np.empty(len(reader.rows), dtype=BAR)
    for i, (at, pair) in enumerate(sorted(reader.rows.items())):
        rows[i] = (at, *pair[0], *pair[1])
    path = JOB / "US500-dev-m1.bin"
    rows.tofile(path)
    write_json(JOB / "US500-dev-m1-source.json", dict(
        pins=pins, binary_sha256=digest(path), bars=len(rows),
        schema=BAR.descr, paired_M1_model=True, no2024_2026=True,
    ))
    event("US500_M1_ready", bars=len(rows))


def prepare_gold():
    root = ROOT / "gold-continuous-B2-20261113-v1/source-cache"
    manifest = read(root / "manifest.json")
    times = np.fromfile(root / "times.bin", dtype="<i8")
    if digest(root / "times.bin") != manifest["files"]["times.bin"]:
        raise ValueError("Gold_timestamps_binding")
    lo, hi = np.searchsorted(times, [START // 1000, END // 1000])
    rows = np.zeros(int(hi - lo), dtype=BAR)
    rows["t"] = times[lo:hi] * 1000
    for source, target in (("o", "bo"), ("h", "bh"), ("l", "bl"), ("c", "bc")):
        path = root / (source + ".bin")
        if digest(path) != manifest["files"][source + ".bin"]:
            raise ValueError("Gold_M1_binding")
        with path.open("rb") as stream:
            stream.seek(int(lo) * 4)
            rows[target] = np.fromfile(stream, dtype="<i4", count=int(hi - lo))
    corrections = read(ATLAS / "gold-source-corrections.json")
    for patch in corrections["patches"]:
        if START <= patch["at"] < END:
            i = int(rows["t"].searchsorted(patch["at"]))
            if rows["t"][i] != patch["at"]:
                raise ValueError("Gold_patch_minute")
            for name, value in zip(("bo", "bh", "bl", "bc"), patch["corrected"]):
                rows[name][i] = value
    path = JOB / "XAUUSD-dev-m1.bin"
    rows.tofile(path)
    write_json(JOB / "XAUUSD-dev-m1-source.json", dict(
        original_manifest_sha256=digest(root / "manifest.json"),
        corrections_sha256=digest(ATLAS / "gold-source-corrections.json"),
        binary_sha256=digest(path), bars=len(rows), schema=BAR.descr,
        bid_only=True, no_ask_invention=True, no2024_2026=True,
    ))
    event("Gold_M1_ready", bars=len(rows))


def load_m1(asset):
    packet = read(JOB / f"{asset}-dev-m1-source.json")
    path = JOB / f"{asset}-dev-m1.bin"
    if digest(path) != packet["binary_sha256"]:
        raise ValueError("M1_source_changed")
    rows = np.fromfile(path, dtype=BAR)
    if len(rows) != packet["bars"] or rows["t"][-1] >= END:
        raise ValueError("M1_scope")
    return rows


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("asset", choices=("EURUSD", "US500", "XAUUSD"))
    selected = parser.parse_args().asset
    {"EURUSD": prepare_eur, "US500": prepare_us500, "XAUUSD": prepare_gold}[selected]()
