"""Alternate integer/Fraction Stage-0 cost and endpoint audit, same implementer."""
from datetime import datetime, timedelta, timezone
from fractions import Fraction as F
from functools import lru_cache
import csv
import hashlib
from pathlib import Path
import numpy as np
from prop_campaign_source import ROOT, read, write_json, stamp

JOB = ROOT / "system-and-alpha-v9-20261115"
HOUR = 3_600_000
DTYPE = np.dtype([("t", "<i8"), ("b", "<i4"), ("a", "<i4")])


def cents(value):
    sign = 1 if value >= 0 else -1
    a = abs(value) * 100
    return F(sign * ((2 * a.numerator + a.denominator) // (2 * a.denominator)), 100)


def carry(first, end):
    d = datetime.fromtimestamp(first / 1000, timezone.utc).replace(hour=22, minute=0, second=0, microsecond=0)
    if int(d.timestamp() * 1000) <= first:
        d += timedelta(days=1)
    result = 0
    while int(d.timestamp() * 1000) <= end:
        if d.weekday() < 5:
            result += 3 if d.weekday() == 2 else 1
        d += timedelta(days=1)
    return result


def money(side, p0, px, first, end, model):
    p0, px = F(p0, 1000), F(px, 1000)
    gross = cents((px - p0) * 100 * (1 if side == "BUY" else -1))
    fee = sum(cents(p * 100 * F(7, 1000000)) for p in (p0, px))
    swap = (-40 if model == "SYM_FLAT" else -45 if side == "BUY" else -5) * carry(first, end)
    return dict(net_per_oz=float((gross - fee - 40 + swap) / 100),
                gross_per_oz=float(gross / 100), swap_per_oz=swap / 100)


class DirectQuotes:
    def __init__(self, manifest):
        self.manifest = manifest
        self.verified = set()

    @lru_cache(maxsize=96)
    def hour(self, at):
        r = self.manifest.get(str(at))
        if r is None:
            return None
        if r["path"] not in self.verified:
            with Path(r["path"]).open("rb") as f:
                if hashlib.file_digest(f, "sha256").hexdigest() != r["sha256"]:
                    raise ValueError("alternate_source_checksum")
            self.verified.add(r["path"])
        with Path(r["path"]).open("rb") as f:
            f.seek(r.get("byte_offset", 0))
            return np.fromfile(f, dtype=DTYPE, count=r["records"])

    def endpoint(self, at):
        a = self.hour(at // HOUR * HOUR)
        if a is None:
            return None
        j = int(a["t"].searchsorted(at))
        return a[j] if j < len(a) and a["t"][j] - at <= 60000 else None


def run():
    result = read(JOB / "development-stage0.json")
    sources = {
        False: DirectQuotes(read(ROOT / "prop-gold-v8-20261115/calendar-corrected/backward/OPEN_LOW_HIGH_CLOSE/manifest.json")),
        True: DirectQuotes(read(ROOT / "prop-gold-v8-20261115/full/OPEN_LOW_HIGH_CLOSE/manifest.json")),
    }
    costs, endpoints, entries = 0, 0, 0
    for r in result["raw"]:
        source = sources[r["decision_msc"] >= stamp("2022-01-01")]
        q = source.endpoint(r["decision_msc"])
        if r["status"] == "ENTRY_UNKNOWN":
            if q is not None:
                raise ValueError("unexpected_entry_unknown")
            continue
        p0 = int(q["a" if r["side"] == "BUY" else "b"])
        if p0 != r["entry_price_units"] or int(q["t"]) != r["entry_msc"]:
            raise ValueError("entry_quote_parity")
        entries += 1
        for endpoint in r["endpoints"].values():
            final = source.endpoint(endpoint["deadline_msc"])
            if endpoint["status"] != "OK":
                continue
            px = int(final["b" if r["side"] == "BUY" else "a"])
            if px != endpoint["exit_price_units"] or int(final["t"]) != endpoint["exit_msc"]:
                raise ValueError("endpoint_quote_parity")
            endpoints += 1
            for model, expected in endpoint["costs"].items():
                actual = money(r["side"], p0, px, r["entry_msc"], endpoint["exit_msc"], model)
                for key, value in actual.items():
                    if abs(value - expected[key]) > 1e-9:
                        raise ValueError("alternate_cost_parity:" + key)
                costs += 1
    output = dict(status="PASS", entries=entries, endpoints=endpoints, cost_bridges=costs,
                  independent_arithmetic=True, independent_person_or_model=False,
                  producer_sha256=hashlib.sha256((JOB / "development-stage0.json").read_bytes()).hexdigest())
    write_json(JOB / "stage0-accounting-parity.json", output)
    print(output)


def eurusd():
    result = read(JOB / "eurusd-stage0.json")
    rows = [r for r in result["raw"] if r["status"] == "OK"]
    key = lambda at: datetime.fromtimestamp(at / 1000, timezone.utc).strftime("%Y.%m.%d %H:%M:%S")
    needed = {key(r[k]) for r in rows for k in ("entry_msc", "exit_msc")}
    quotes = {}
    for source in result["source"]:
        path = Path(source["file"])
        with path.open("rb") as f:
            if hashlib.file_digest(f, "sha256").hexdigest() != source["sha256"]:
                raise ValueError("EUR_alternate_raw_hash")
        with path.open() as f:
            for r in csv.DictReader(f):
                if r["DateTime"] in needed:
                    price = F(r["Open"]) * 100000
                    if price.denominator != 1:
                        raise ValueError("EUR_alternate_grid")
                    quotes[r["DateTime"]] = int(price)
    for r in rows:
        buy = r["side"] == "BUY"
        p0 = quotes[key(r["entry_msc"])] + (10 if buy else 0)
        px = quotes[key(r["exit_msc"])] + (0 if buy else 10)
        distance = (p0 - r["stop_units"]) if buy else (r["stop_units"] - p0)
        net = (px - p0) * (1 if buy else -1) - 9
        if (r["gross_USD_per_lot"] != net + 9 or r["net_USD_per_lot"] != net or
                abs(r["natural_sl_pips"] - distance / 10) > 1e-9 or
                abs(r["raw_markout_R"] - float(F(net, distance))) > 1e-9):
            raise ValueError("EUR_alternate_unit_bridge")
    output = dict(status="PASS", trades=len(rows), direct_CSV_quotes=len(quotes),
                  same_implementer=True, native_Ask=False)
    write_json(JOB / "eurusd-accounting-parity.json", output)
    print(output)


if __name__ == "__main__":
    import sys
    eurusd() if "--eurusd" in sys.argv else run()
