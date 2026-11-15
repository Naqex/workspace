"""Checksummed read-only binary columns and bounded quote partitions."""
from functools import lru_cache
import hashlib
import json
from pathlib import Path
import numpy as np

HOUR = 3_600_000
QUOTE = np.dtype([("t", "<i8"), ("b", "<i4"), ("a", "<i4")])
BAR = np.dtype([(n, "<i8" if n == "t" else "<i4")
                for n in ("t", "bo", "bh", "bl", "bc", "ao", "ah", "al", "ac")])


class Checksums:
    """Hash once per file generation, rather than once per hour in one file."""
    def __init__(self):
        self.checked = {}
        self.bytes_hashed = 0

    def verify(self, path, expected):
        path = Path(path)
        s = path.stat()
        key = (str(path.resolve()), s.st_size, s.st_mtime_ns, expected)
        if key not in self.checked:
            with path.open("rb") as f:
                actual = hashlib.file_digest(f, "sha256").hexdigest()
            if actual != expected:
                raise ValueError("source_checksum_mismatch:" + path.name)
            self.checked[key] = True
            self.bytes_hashed += s.st_size


class MarketDataStore:
    def __init__(self, folder, checksums=None):
        self.folder = Path(folder)
        self.manifest = json.loads((self.folder / "manifest.json").read_bytes())
        self.checksums = checksums or Checksums()
        self.columns = {}
        for name in ("times", "o", "h", "l", "c"):
            path = self.folder / (name + ".bin")
            self.checksums.verify(path, self.manifest["files"][path.name])
            self.columns[name] = np.memmap(path, mode="r", dtype="<i8" if name == "times" else "<i4")
            if len(self.columns[name]) != self.manifest["rows"]:
                raise ValueError("binary_column_length")
        self.raw_declared_sha256 = self.manifest["raw_sha256"]

    def bars(self, first, end):
        if first >= end or first % 1000 or end % 1000:
            raise ValueError("invalid_millisecond_window")
        times = self.columns["times"]
        lo, hi = times.searchsorted([first // 1000, end // 1000])
        rows = np.zeros(hi - lo, dtype=BAR)
        rows["t"] = times[lo:hi] * 1000
        for n in ("o", "h", "l", "c"):
            rows["b" + n] = self.columns[n][lo:hi]
        if len(rows) and (np.any(np.diff(rows["t"]) <= 0) or np.any(rows["bl"] <= 0) or
                          np.any(rows["bl"] > np.minimum(rows["bo"], rows["bc"])) or
                          np.any(rows["bh"] < np.maximum(rows["bo"], rows["bc"]))):
            raise ValueError("OHLC_schema")
        return rows


class QuoteStore:
    def __init__(self, manifest, first, end, checksums=None):
        self.first, self.cutoff = first, end
        self.files = {int(k): v for k, v in manifest.items() if first <= int(k) < end}
        self.checksums = checksums or Checksums()

    @lru_cache(maxsize=96)
    def hour(self, at):
        if not self.first <= at < self.cutoff or at % HOUR:
            raise ValueError("quote_scope_fence")
        r = self.files[at]
        self.checksums.verify(r["path"], r["sha256"])
        if not r["records"]:
            return np.empty(0, dtype=QUOTE)
        a = np.memmap(r["path"], mode="r", dtype=QUOTE,
                      offset=r.get("byte_offset", 0), shape=(r["records"],))
        if (a["t"][0] < at or a["t"][-1] >= at + HOUR or
                np.any(np.diff(a["t"]) < 0) or np.any(a["a"] < a["b"]) or np.any(a["b"] <= 0)):
            raise ValueError("quote_schema")
        return a

    def endpoint(self, at):
        h = at // HOUR * HOUR
        if h not in self.files:
            return None
        a = self.hour(h)
        j = int(a["t"].searchsorted(at))
        return ([int(a["t"][j]), int(a["b"][j]), int(a["a"][j]), j]
                if j < len(a) and a["t"][j] - at <= 60000 else None)

    def path(self, first, end):
        if not self.first <= first <= end < self.cutoff:
            raise ValueError("path_scope_fence")
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
            raise ValueError("empty_quote_path")
        return np.concatenate(parts), np.concatenate(ordinals)
