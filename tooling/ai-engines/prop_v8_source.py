"""Partition-seek Gold inputs and deterministic backward calendar; no downloads."""
from bisect import bisect_right
from datetime import date, timedelta
from functools import lru_cache
from statistics import median
import hashlib
import numpy as np
from prop_campaign_source import DTYPE
from prop_portfolio_sources import BAR
from prop_v6_paths import scenario
from prop_v6_data import aggregate
from prop_v7_paths import readers as old_readers
from prop_v8_common import *


class Calendar:
    def __init__(self, data, first, end):
        self.events = {r["day"]: r for r in data["events"]}
        self.flats = []
        d = datetime.fromtimestamp(first / 1000, timezone.utc).replace(hour=0, minute=0, second=0)
        while int(d.timestamp() * 1000) < end + 8 * DAY:
            row = self.events.get(d.date().isoformat(), {})
            if row.get("flat_utc"):
                h, m = map(int, row["flat_utc"].split(":"))
                self.flats.append((int(d.timestamp() * 1000) + h * HOUR + m * 60000, "HOLIDAY_FLAT"))
            if d.weekday() == 4:
                self.flats.append((int(d.timestamp() * 1000) + 20 * HOUR + HOUR // 2, "FRIDAY_CLOSE"))
            d += timedelta(days=1)
        self.flats.sort()
        self.times = [x[0] for x in self.flats]

    def allowed(self, at):
        d = datetime.fromtimestamp(at / 1000, timezone.utc)
        row = self.events.get(d.date().isoformat(), {})
        return d.weekday() < 5 and row.get("kind") != "CLOSED" and (
            not row.get("flat_utc") or d.strftime("%H:%M") < row["flat_utc"])

    def deadline(self, at):
        if not self.allowed(at):
            raise ValueError("V8_entry_outside_session")
        i = bisect_right(self.times, at)
        if i == len(self.flats):
            raise ValueError("V8_calendar_future_flat_missing")
        flat, kind = self.flats[i]
        return (flat, kind) if flat < at + 48 * HOUR else (at + 48 * HOUR, "TIME_48H")


def make_calendar():
    # Dates are declared calendar guards, not an inferred broker close from prices.
    old = read("planning/research/PROP-V7-SESSION-CALENDAR-20261115.json")
    rows = {}
    holidays = {
        2018: ("01-15", "02-19", "05-28", "07-04", "09-03", "11-22", "11-23"),
        2019: ("01-21", "02-18", "05-27", "07-04", "09-02", "11-28", "11-29"),
        2020: ("01-20", "02-17", "05-25", "07-03", "09-07", "11-26", "11-27"),
        2021: ("01-18", "02-15", "05-31", "07-05", "09-06", "11-25", "11-26"),
    }
    good = {2018: "03-30", 2019: "04-19", 2020: "04-10", 2021: "04-02"}
    for y in range(2017, 2023):
        for text in ("01-01", "12-25"):
            d = date.fromisoformat(f"{y}-{text}")
            observed = d - timedelta(days=1) if d.weekday() == 5 else d + timedelta(days=1) if d.weekday() == 6 else d
            for day in (d, observed):
                rows[day.isoformat()] = dict(day=day.isoformat(), kind="CLOSED", flat_utc=None)
                eve = day - timedelta(days=1)
                if eve.weekday() < 5 and eve.isoformat() not in rows:
                    rows[eve.isoformat()] = dict(day=eve.isoformat(), kind="CONSERVATIVE_EVE", flat_utc="16:58")
        if y in holidays:
            for text in holidays[y] + ("12-24", "12-31"):
                day = f"{y}-{text}"
                rows.setdefault(day, dict(day=day, kind="DECLARED_METALS_EARLY_GUARD", flat_utc="16:58"))
            gf = date.fromisoformat(f"{y}-{good[y]}")
            rows[gf.isoformat()] = dict(day=gf.isoformat(), kind="CLOSED", flat_utc=None)
            eve = (gf - timedelta(days=1)).isoformat()
            rows[eve] = dict(day=eve, kind="GOOD_FRIDAY_EVE", flat_utc="20:28")
            if y in (2018, 2019):
                day = f"{y}-07-03"
                rows[day] = dict(day=day, kind="DECLARED_METALS_EARLY_GUARD", flat_utc="16:58")
    historical = [dict(r, target_time_status="UNVERIFIED_HISTORICAL_GUARD")
                  for d, r in sorted(rows.items()) if d < "2022-01-01"]
    write_json(CALENDAR, dict(schema="V8-calendar-v1", events=historical + old["events"],
        historical_FTMO_times_certified=False, preserved_V7_2022_2026=True,
        sources=["https://www.cmegroup.com/trading/metals/files/metals-prod-guide-2020.pdf",
                 "https://www.cmegroup.com/trading-hours.html",
                 "https://ftmo.com/faq/can-i-hold-positions-overnight-or-over-the-weekend/"]))


def cache_bars(first, end, *, released=False):
    if first < START:
        if not released:
            raise ValueError("V8_backward_prices_locked")
        verify()
        if not stamp("2017-11-01") <= first < end <= BACK_END:
            raise ValueError("V8_backward_scope")
    elif not START <= first < end <= (END if released else DEV_END):
        raise ValueError("V8_development_fence")
    manifest = read(CACHE / "manifest.json")
    times = np.memmap(CACHE / "times.bin", dtype="<i8", mode="r")
    lo, hi = map(int, np.searchsorted(times, [first // 1000, end // 1000]))
    rows = np.zeros(hi - lo, dtype=BAR)
    rows["t"] = times[lo:hi] * 1000
    for name in ("o", "h", "l", "c"):
        with (CACHE / (name + ".bin")).open("rb") as f:
            f.seek(lo * 4)
            rows["b" + name] = np.fromfile(f, dtype="<i4", count=hi - lo)
    corrections = read(ROOT / "prop-atlas-v2-20261114/gold-source-corrections.json")["patches"]
    if released:
        corrections += read(PARENT / "source-v2/corrections.json")["patches"]
    applied = {}
    for p in corrections:
        if first <= p["at"] < end:
            if p["at"] in applied and applied[p["at"]] != p["corrected"]:
                raise ValueError("V8_conflicting_M1_correction")
            i = int(rows["t"].searchsorted(p["at"]))
            if i == len(rows) or rows["t"][i] != p["at"]:
                raise ValueError("V8_patch_absent")
            for name, value in zip(("bo", "bh", "bl", "bc"), p["corrected"]):
                rows[name][i] = value
            applied[p["at"]] = p["corrected"]
    if len(rows) and (np.any(np.diff(rows["t"]) <= 0) or rows["t"][0] < first or rows["t"][-1] >= end
                     or np.any(rows["bl"] <= 0) or np.any(rows["bl"] > np.minimum(rows["bo"], rows["bc"]))
                     or np.any(rows["bh"] < np.maximum(rows["bo"], rows["bc"]))):
        raise ValueError("V8_M1_schema")
    return rows, dict(parent_manifest_sha256=digest(CACHE / "manifest.json"),
        parent_raw_declared_sha256=manifest["raw_sha256"], first=first, end=end,
        seek_rows=[lo, hi], prices_outside_slice_read=False, corrections=len(applied),
        slice_sha256=hashlib.sha256(rows.tobytes()).hexdigest())


class Prices:
    def __init__(self, manifest, first, end):
        self.first, self.cutoff = first, end
        self.files = {int(k): v for k, v in manifest.items() if first <= int(k) < end}
        self.checked_files = set()

    @lru_cache(maxsize=96)
    def hour(self, at):
        if not self.first <= at < self.cutoff or at % HOUR:
            raise ValueError("V8_price_fence")
        r = self.files[at]
        if r["path"] not in self.checked_files:
            if digest(r["path"]) != r["sha256"]:
                raise ValueError("V8_binary_hash")
            self.checked_files.add(r["path"])
        with Path(r["path"]).open("rb") as f:
            f.seek(r.get("byte_offset", 0))
            a = np.fromfile(f, dtype=DTYPE, count=r["records"])
        if len(a) != r["records"] or len(a) and (
            a["t"][0] < at or a["t"][-1] >= at + HOUR or np.any(np.diff(a["t"]) < 0)
            or np.any(a["a"] < a["b"]) or np.any(a["b"] <= 0)):
            raise ValueError("V8_quote_schema")
        return a

    def endpoint(self, at):
        h = at // HOUR * HOUR
        if h not in self.files:
            return None
        a = self.hour(h)
        j = int(a["t"].searchsorted(at))
        return [int(a["t"][j]), int(a["b"][j]), int(a["a"][j]), j] if j < len(a) and a["t"][j] - at <= 60000 else None

    def path(self, first, end):
        if not self.first <= first <= end < self.cutoff:
            raise ValueError("V8_path_fence")
        parts, ordinals = [], []
        for h in range(first // HOUR * HOUR, end // HOUR * HOUR + HOUR, HOUR):
            if h not in self.files:
                continue
            a = self.hour(h)
            lo, hi = int(a["t"].searchsorted(first)), int(a["t"].searchsorted(end, side="right"))
            if hi > lo:
                parts.append(a[lo:hi])
                ordinals.append(np.arange(lo, hi))
        if not parts:
            raise ValueError("V8_empty_path")
        return np.concatenate(parts), np.concatenate(ordinals)


def prepare_source(tag, order, first, end, *, released=False):
    folder = JOB / tag / order
    folder.mkdir(parents=True, exist_ok=False)
    old_end = min(end, stamp("2025-01-01"))
    bars, proof = cache_bars(first, old_end, released=released)
    if end > old_end:
        rows = np.fromfile(V6 / "gold-holdout-m1.bin", dtype=BAR)
        rows = rows[(rows["t"] >= old_end) & (rows["t"] < end)]
        bars = np.concatenate([bars, rows])
        proof["V6_holdout_binary_sha256"] = digest(V6 / "gold-holdout-m1.bin")
    bars.tofile(folder / "bid-m1.bin")
    quotes = scenario(bars, order, spread=338)
    path = folder / "M1-quotes.bin"
    quotes.tofile(path)
    sha = digest(path)
    codes = quotes["t"] // HOUR * HOUR
    starts = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
    stops = np.r_[starts[1:], len(quotes)]
    manifest = {str(int(codes[i])): dict(path=path.as_posix(), sha256=sha,
        records=int(j - i), byte_offset=int(i * DTYPE.itemsize), source_kind="CONDITIONAL_BID_M1_ASK_PROXY")
        for i, j in zip(starts, stops)}
    # Native ticks are the owner when already admitted; fill only absent hours with M1.
    if first >= START:
        native = old_readers(order)["XAUUSD"].files
        manifest.update({str(h): dict(v, source_kind="OBSERVED_PAIRED_TICKS" if h < stamp("2025-01-01")
                                         else "CONDITIONAL_BID_M1_ASK_PROXY")
                         for h, v in native.items() if first <= h < end})
    write_json(folder / "manifest.json", manifest)
    write_json(folder / "hours.json", aggregate(bars))
    write_json(folder / "source-proof.json", dict(proof, bars=len(bars), bid_only_fallback=True,
        spread_proxy_usd_per_oz=.338, manifest_sha256=digest(folder / "manifest.json"),
        hours_by_kind=dict(__import__("collections").Counter(r["source_kind"] for r in manifest.values()))))
    event("V8_source_prepared", tag=tag, order=order, bars=len(bars))
    return bars


def readers(tag, order, first, end):
    return dict(XAUUSD=Prices(read(JOB / tag / order / "manifest.json"), first, end),
                EURUSD=Prices({}, first, end))
