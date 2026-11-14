"""Existing QDM ticks for registered sleeve hours; no provider or broker IO."""
from datetime import datetime, timezone
from pathlib import Path
import numpy as np

from prop_campaign_source import Prices, DTYPE
from prop_portfolio_common import (
    ROOT, JOB, ATLAS, START, END, FINAL, HOUR, read, write_json, digest, event, price_scope,
)
from prop_portfolio_sources import deadline
from prop_portfolio_scan import raw_geometry


def collect(raw_signals, cutoff=END):
    import pandas as pd
    price_scope(cutoff)
    label = "dev" if cutoff == END else "validation"
    folder = JOB / f"eur-native-{label}-v1"
    folder.mkdir(exist_ok=False)
    needed = set()
    for row in raw_signals:
        at = row["decision_msc"]
        if not (START if cutoff == END else END) <= at < cutoff:
            raise ValueError("native_signal_scope")
        end, _ = deadline(row, at)
        needed.update(range(at // HOUR * HOUR, end // HOUR * HOUR + HOUR, HOUR))
    write_json(folder / "registration.json", dict(
        hours=sorted(needed), signals=raw_signals, cutoff=cutoff,
        purpose="exact tick confirmation of frozen EURUSD satellite only",
        prices2025_2026_read=False,
    ))
    cfg = read(ROOT / "eurusd-b0-20261113/config-attempt-1.json")
    packets = []
    for source in cfg["sources"]:
        if source["first_day"] not in (
                ("20220101", "20230101") if cutoff == END else ("20240101",)):
            continue
        if source["last_day"] >= "20250101" or digest(source["path"]) != source["sha256"]:
            raise ValueError("native_source_or_holdout")
        total = selected = 0
        for frame in pd.read_csv(source["path"], dtype=str,
                                 usecols=["DateTime", "Bid", "Ask"],
                                 chunksize=500000, engine="c"):
            dates = frame["DateTime"].str.slice(0, 8)
            if not dates.between(source["first_day"], source["last_day"]).all():
                raise ValueError("native_price_fence_before_parse")
            codes, unique = pd.factorize(frame["DateTime"].str.slice(0, 11), sort=False)
            hours = np.array([
                int(datetime.strptime(x, "%Y%m%d %H").replace(
                    tzinfo=timezone.utc).timestamp() * 1000) for x in unique
            ], dtype="<i8")
            mask = np.isin(hours[codes], list(needed))
            kept = frame.loc[mask]
            if len(kept):
                values = np.empty(len(kept), dtype=DTYPE)
                values["t"] = (
                    hours[codes[mask]]
                    + kept["DateTime"].str.slice(12, 14).astype("int64").to_numpy() * 60000
                    + kept["DateTime"].str.slice(15, 17).astype("int64").to_numpy() * 1000
                    + kept["DateTime"].str.slice(18, 21).astype("int64").to_numpy()
                )
                values["b"] = kept["Bid"].str.replace(".", "", regex=False).astype("int32")
                values["a"] = kept["Ask"].str.replace(".", "", regex=False).astype("int32")
                if (np.any(np.diff(values["t"]) < 0) or
                        np.any(values["b"] <= 0) or np.any(values["a"] < values["b"])):
                    raise ValueError("native_quote_order")
                by_hour = values["t"] // HOUR * HOUR
                starts = np.r_[0, np.flatnonzero(np.diff(by_hour)) + 1]
                ends = np.r_[starts[1:], len(values)]
                for first, last in zip(starts, ends):
                    at = int(by_hour[first])
                    with (folder / f"{at}.ticks").open("ab") as stream:
                        values[first:last].tofile(stream)
                selected += len(kept)
            total += len(frame)
            if total % 5000000 == 0:
                event("EUR_native_intake", partition=source["first_day"][:4],
                      rows=total, selected_ticks=selected)
        packets.append(dict(path=source["path"], sha256=source["sha256"],
                            rows=total, selected_ticks=selected))
    manifest = {}
    for at in sorted(needed):
        path = folder / f"{at}.ticks"
        if not path.exists():
            path.write_bytes(b"")
        manifest[str(at)] = dict(path=str(path), records=path.stat().st_size // DTYPE.itemsize,
                                 sha256=digest(path))
    write_json(folder / "manifest.json", manifest)
    write_json(folder / "source-proof.json", dict(
        sources=packets, hours=len(needed), manifest_sha256=digest(folder / "manifest.json"),
        preserves_source_order_and_same_ms=True, cutoff=cutoff, prices2025_2026_read=False,
    ))
    event("EUR_native_ready", partition=label, hours=len(needed),
          ticks=sum(p["selected_ticks"] for p in packets))
    return manifest


def realize_ticks(raw, manifest, cutoff=END):
    price_scope(cutoff)
    reader = Prices(manifest, cutoff)
    trades = []
    skipped = []
    for row in raw:
        entry = reader.endpoint(row["decision_msc"])
        if entry is None:
            skipped.append(dict(day=row["day"], reason="ENTRY_UNKNOWN"))
            continue
        p0, distance, friction, passes = raw_geometry(row, entry)
        if not passes:
            skipped.append(dict(day=row["day"], reason="FRICTION_REJECT",
                                natural_sl=distance, friction=friction))
            continue
        end, reason = deadline(row, entry[0])
        final = reader.endpoint(end)
        if final is None:
            skipped.append(dict(day=row["day"], reason="ENDPOINT_UNKNOWN"))
            continue
        ticks, ordinal = reader.path(entry[0], final[0])
        side = "b" if row["side"] == "BUY" else "a"
        prices = ticks[side]
        hit = np.flatnonzero(
            (prices <= row["stop_units"] if side == "b" else prices >= row["stop_units"])
            & (ticks["t"] < end)
        )
        index = int(hit[0]) if len(hit) else int(ticks["t"].searchsorted(final[0]))
        if len(hit):
            reason = "SL"
        trades.append(dict(
            row, asset="EURUSD", role="SATELLITE", recipe="SAT1",
            signal_id=f"SAT1:{row['decision_msc']}:{row['side']}",
            entry_msc=entry[0], entry_price_units=p0, entry_quote=entry[:3],
            entry_quote_index=entry[3], stop_units=row["stop_units"],
            deadline_msc=end, exit_msc=int(ticks["t"][index]),
            exit_price_units=int(prices[index]), exit_quote_index=int(ordinal[index]),
            natural_sl=distance, friction=friction, reason=reason, regime_weight=1,
        ))
    return trades, skipped


def prepare_dev():
    selected = read(JOB / "satellite-decision.json")["selected"]
    if selected != ["EURUSD.SWEEP.ASIA.LONDON.DAY"]:
        raise ValueError("different_sleeve_requires_registered_native_adapter")
    raw = read(ATLAS / f"stage0-{selected[0]}.json")["rows"]
    manifest = collect(raw)
    trades, skipped = realize_ticks(raw, manifest)
    write_json(JOB / "eur-satellite-dev-trades.json", trades)
    write_json(JOB / "eur-satellite-dev-funnel.json", dict(raw=len(raw), skipped=skipped,
                                                          filled=len(trades)))


if __name__ == "__main__":
    prepare_dev()
