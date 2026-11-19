"""Bounded MT5 spread samples labelled by a verified local-session window."""

from collections import defaultdict
from datetime import datetime, time, timedelta, timezone
from hashlib import sha256
import json
from pathlib import Path
from statistics import median
from zoneinfo import ZoneInfo


ASSETS = ("EURUSD", "GBPUSD", "AUDUSD", "USDJPY", "USDCHF", "USDCAD", "NZDUSD",
          "EURGBP", "EURJPY", "GBPJPY", "AUDJPY", "XAUUSD", "US500.cash")
WINDOWS = {
    "asia": ("Asia/Tokyo", time(9), time(15)),
    "london": ("Europe/London", time(8), time(12)),
    "ny": ("America/New_York", time(9, 30), time(15)),
    "rollover": ("America/New_York", time(16, 55), time(18, 15)),
}


def window(tag, start, duration):
    zone, opening, closing = WINDOWS[tag]
    local = start.astimezone(ZoneInfo(zone))
    lo = datetime.combine(local.date(), opening, local.tzinfo).astimezone(timezone.utc)
    hi = datetime.combine(local.date(), closing, local.tzinfo).astimezone(timezone.utc)
    if local.weekday() >= (4 if tag == "rollover" else 5) or not lo <= start < start + timedelta(seconds=duration) <= hi:
        raise ValueError(f"OUTSIDE_{tag.upper()}_SPREAD_WINDOW {lo.isoformat()}..{hi.isoformat()}")
    return dict(tag=tag, timezone=zone, from_utc_msc=int(lo.timestamp() * 1000),
                to_utc_msc=int(hi.timestamp() * 1000))


def _percentile(ordered, fraction):
    at = (len(ordered) - 1) * fraction
    whole = int(at)
    return ordered[whole] + (ordered[min(whole + 1, len(ordered) - 1)] - ordered[whole]) * (at - whole)


def combine(directories):
    """Recompute quantiles on sampled quotes, keeping each session separate."""
    import pyarrow.parquet as pq

    sources = []
    periods = []
    samples = defaultdict(lambda: defaultdict(list))
    binding = None
    for directory in directories:
        folder = Path(directory)
        report = json.loads((folder / "report.json").read_text(encoding="utf-8"))
        capture = json.loads((folder / "quote_capture.json").read_text(encoding="utf-8"))
        tagged = report["session_window"]
        start, end = (report["quote_window"][key] for key in ("started_utc_msc", "ended_utc_msc"))
        expected = window(tagged["tag"], datetime.fromtimestamp(start / 1000, timezone.utc), (end - start) / 1000)
        if (report["source"] != "NATIVE_MT5" or report["mode"] != "READ_ONLY" or
                report["actual_broker_orders"] != 0 or tagged != expected):
            raise ValueError("SESSION_CAPTURE_MUST_BE_NATIVE_READ_ONLY_AND_IN_WINDOW")
        if any(start < old_end and old_start < end for old_start, old_end in periods):
            raise ValueError("OVERLAPPING_SPREAD_CAPTURES")
        periods.append((start, end))
        current_binding = report["binding"]
        if binding is not None and current_binding != binding:
            raise ValueError("SPREAD_ACCOUNT_BINDINGS_DIFFER")
        binding = current_binding
        file = folder / "quotes.parquet"
        if sha256(file.read_bytes()).hexdigest() != capture["sha256"]:
            raise ValueError("SPREAD_PARQUET_HASH_MISMATCH")
        table = pq.read_table(file, columns=["asset", "spread", "known_at_msc"])
        if table.num_rows != capture["rows"]:
            raise ValueError("SPREAD_ROW_COUNT_MISMATCH")
        group = samples[tagged["tag"]]
        for row in table.to_pylist():
            if not start <= row["known_at_msc"] <= end:
                raise ValueError("SPREAD_QUOTE_OUTSIDE_CAPTURE")
            group[row["asset"]].append(row["spread"])
        sources.append(dict(tag=tagged["tag"], start_utc_msc=start, end_utc_msc=end, sha256=capture["sha256"]))

    statistics = {}
    for tag, grouped in samples.items():
        statistics[tag] = {}
        for asset, values in grouped.items():
            values.sort()
            statistics[tag][asset] = dict(n=len(values), unit="price", median=median(values),
                p90=_percentile(values, .90), p95=_percentile(values, .95),
                p99=_percentile(values, .99), maximum=values[-1])
    return dict(schema="FTMO-native-session-spreads-v1", binding=binding, captures=sources,
                coverage={tag: [a for a in ASSETS if a not in statistics.get(tag, {})] for tag in WINDOWS},
                sessions=statistics, complete_tick_feed_claim=False, complete_session_coverage_claim=False)
