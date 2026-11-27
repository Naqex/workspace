"""Read-only paired H1 index: no synthetic M1 and no validation-year quote decoding."""

import importlib.util
import json
from decimal import Decimal
from pathlib import Path
from typing import Any

import numpy as np
import prop_v10_signals as frozen
from us500_year_source import load_year_side

from quant_core.market_data_store import BAR, Checksums
from quant_core.vectorized_stage0_scanner import DAY, HOUR


class PairedHourlyStore:
    def __init__(self, index, first, end):
        self.index = index
        self.first, self.end = first, end
        self.checks = Checksums()
        self.audit = []

    def bars(self):
        sides = {"bid": {}, "ask": {}}
        for source in self.index["books"]:
            if not self.index["first"] <= source["first"] <= source["last"] < self.index["end"]:
                raise ValueError("hourly_book_outside_registered_development")
            self.checks.verify(source["path"], source["sha256"])
            values = json.loads(Path(source["path"]).read_bytes(), parse_float=Decimal)
            if isinstance(values, dict):
                values = values.get("rows", values.get("data", []))
            if (
                len(values) != source["rows"]
                or values[0]["timestamp"] != source["first"]
                or values[-1]["timestamp"] != source["last"]
            ):
                raise ValueError("hourly_source_census")
            for row in values:
                at = row["timestamp"]
                if type(at) is not int or at % HOUR:
                    raise ValueError("hourly_timestamp_grid")
                if not self.first <= at < self.end:
                    continue
                price = []
                for name in ("open", "high", "low", "close"):
                    value = Decimal(str(row[name])) * 100000
                    if not value.is_finite() or value != value.to_integral_value():
                        raise ValueError("hourly_price_grid")
                    price.append(int(value))
                o, h, low, c = price
                if low <= 0 or low > min(o, c) or h < max(o, c):
                    raise ValueError("hourly_OHLC")
                side = sides[source["side"]]
                if at in side:
                    raise ValueError("hourly_duplicate")
                side[at] = price
        bid, ask = sides["bid"], sides["ask"]
        common = sorted(bid.keys() & ask.keys())
        missing = sorted(bid.keys() ^ ask.keys())
        self.audit = dict(
            paired_hours=len(common),
            unpaired_hours=missing,
            path_timeframe="H1_ONLY",
            synthetic_minutes=False,
            read_only=True,
        )
        out: Any = np.zeros(len(common), dtype=BAR)
        out["t"] = common
        for i, at in enumerate(common):
            if any(a < b for a, b in zip(ask[at], bid[at], strict=True)):
                raise ValueError("hourly_crossed_pair")
            for prefix, prices in (("b", bid[at]), ("a", ask[at])):
                for field, value in zip(("o", "h", "l", "c"), prices, strict=True):
                    out[prefix + field][i] = value
        return out


def closed_frames(hourly):
    hours = [[int(r[n]) for n in ("t", "bo", "bh", "bl", "bc")] for r in hourly]
    h4, daily = [], []
    for width, target, minimum in ((4 * HOUR, h4, 4), (DAY, daily, 20)):
        groups = {}
        for r in hours:
            groups.setdefault(r[0] // width * width, []).append(r)
        for at, rs in sorted(groups.items()):
            if len(rs) < minimum or width == 4 * HOUR and [r[0] for r in rs] != [at + i * HOUR for i in range(4)]:
                continue
            target.append([at, rs[0][1], max(r[2] for r in rs), min(r[3] for r in rs), rs[-1][4]])
    return frozen.frame(hours, HOUR), frozen.frame(h4, 4 * HOUR), frozen.frame(daily, DAY)


def native_recipes(hourly, asset, first, end, calendar):
    # Private module instance keeps frozen formulas intact without global monkeypatching.
    spec = importlib.util.spec_from_file_location("_v11_frozen_signal_adapter", frozen.__file__)
    if spec is None or spec.loader is None:
        raise ImportError("frozen_signal_spec_unavailable")
    module: Any = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    prepared = closed_frames(hourly)
    module.frames = lambda unused: prepared
    return module.recipes(None, asset, first, end, calendar)


class IndexedUs500Store:
    """Reuse accepted quarterly JSON in place; preserve missing native observations."""

    def __init__(self, index, first, end):
        self.index, self.first, self.end = index, first, end
        self.audit = {}

    def bars(self):
        parts = []
        for book in self.index["years"]:
            year = book["year"]
            if year not in tuple(range(2017, 2024)):
                raise ValueError("US500_V11_development_fence")
            sides = {
                side: load_year_side(
                    Path(book["root"]),
                    year=year,
                    side=side,
                    proof_sha256=book["proof_sha256"],
                    registered_years=tuple(range(2017, 2024)),
                )
                for side in ("bid", "ask")
            }
            bid, ask = sides["bid"]["rows"], sides["ask"]["rows"]
            if bid.keys() != ask.keys():
                raise ValueError("US500_accepted_pairing_changed")
            times = sorted(t for t in bid if self.first <= t < self.end)
            rows: Any = np.zeros(len(times), dtype=BAR)
            rows["t"] = times
            for i, at in enumerate(times):
                for prefix, side in (("b", bid), ("a", ask)):
                    for field, name in zip(("o", "h", "l", "c"), ("open", "high", "low", "close"), strict=True):
                        value = Decimal(str(side[at][name])) * 1000
                        if value != value.to_integral_value():
                            raise ValueError("US500_native_price_grid")
                        rows[prefix + field][i] = int(value)
            if np.any(rows["bo"] <= 0) or any(np.any(rows["a" + f] < rows["b" + f]) for f in ("o", "h", "l", "c")):
                raise ValueError("US500_native_quote_schema")
            parts.append(rows)
        result: Any = np.concatenate(parts)
        if np.any(np.diff(result["t"]) <= 0):
            raise ValueError("US500_native_order")
        self.audit = dict(
            paired_M1=len(result),
            read_only=True,
            new_source_copies=0,
            declared_unavailable=self.index["unavailable_requests"],
        )
        return result
