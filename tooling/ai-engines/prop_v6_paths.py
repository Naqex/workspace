"""Declared M1 OHLC scenarios and causal stops; never label them observed ticks."""
from functools import lru_cache
import numpy as np
from prop_campaign_source import DTYPE, HOUR, START
from prop_portfolio_scan import raw_geometry
from prop_v6_signals import deadline


def scenario(bars, order="OPEN_LOW_HIGH_CLOSE", spread=None):
    names = ("o", "l", "h", "c") if order == "OPEN_LOW_HIGH_CLOSE" else ("o", "h", "l", "c")
    if order not in ("OPEN_LOW_HIGH_CLOSE", "OPEN_HIGH_LOW_CLOSE"):
        raise ValueError("unregistered_M1_order")
    a = np.empty(len(bars) * 4, dtype=DTYPE)
    a["t"] = (bars["t"][:, None] + np.array([0, 20000, 40000, 59999])).ravel()
    a["b"] = np.column_stack([bars["b" + n] for n in names]).ravel()
    a["a"] = a["b"] + spread if spread is not None else np.column_stack(
        [bars["a" + n] for n in names]).ravel()
    if np.any(a["b"] <= 0) or np.any(a["a"] < a["b"]):
        raise ValueError("conditional_quote_geometry")
    return a


class ScopedPrices:
    """Admitted hour manifest with a V6-specific end, not the historical Prices."""
    def __init__(self, manifest, cutoff):
        self.files = {int(k): v for k, v in manifest.items() if START <= int(k) < cutoff}
        self.cutoff = cutoff

    @lru_cache(maxsize=32)
    def hour(self, at):
        from prop_campaign_source import digest
        if not START <= at < self.cutoff or at % HOUR:
            raise ValueError("V6_price_fence")
        row = self.files[at]
        if digest(row["path"]) != row["sha256"]:
            raise ValueError("V6_binary_changed")
        a = np.fromfile(row["path"], dtype=DTYPE)
        if (len(a) != row["records"] or len(a) and
                (np.any(np.diff(a["t"]) < 0) or a["t"][0] < at or a["t"][-1] >= at + HOUR
                 or np.any(a["b"] <= 0) or np.any(a["a"] < a["b"]))):
            raise ValueError("V6_binary_schema")
        return a

    def endpoint(self, at):
        hour = at // HOUR * HOUR
        if hour not in self.files:
            return None
        a = self.hour(hour)
        i = int(a["t"].searchsorted(at))
        if i == len(a) or a["t"][i] - at > 60000:
            return None
        return [int(a["t"][i]), int(a["b"][i]), int(a["a"][i]), i]

    def path(self, start, end):
        if not START <= start <= end < self.cutoff:
            raise ValueError("V6_path_fence")
        parts, ordinals = [], []
        for hour in range(start // HOUR * HOUR, end // HOUR * HOUR + 1, HOUR):
            a = self.hour(hour) if hour in self.files else np.empty(0, dtype=DTYPE)
            lo, hi = a["t"].searchsorted([start, end], side="left")
            hi = int(a["t"].searchsorted(end, side="right"))
            if hi > lo:
                parts.append(a[lo:hi])
                ordinals.append(np.arange(lo, hi))
        if not parts:
            raise ValueError("V6_empty_path")
        return np.concatenate(parts), np.concatenate(ordinals)


def realize(raw, reader, calendar, cutoff):
    out, skipped = [], []
    for r in raw:
        asset = r.get("asset", "XAUUSD")
        row = dict(r, asset=asset)
        entry = reader.endpoint(row["decision_msc"])
        if entry is None:
            skipped.append(dict(row, missing="ENTRY_UNKNOWN"))
            continue
        p0, distance, friction, passes = raw_geometry(row, entry)
        # A_Original did not add the satellite's 15% entry filter.
        if asset == "EURUSD" and not passes:
            skipped.append(dict(row, reason="FRICTION_REJECT", natural_sl=distance, friction=friction))
            continue
        if distance <= 0:
            skipped.append(dict(row, missing="INVALID_GEOMETRY"))
            continue
        end, why = deadline(row, entry[0], calendar)
        final = reader.endpoint(end) if end < cutoff else None
        observation_end = final[0] if final else min(end, cutoff - 1)
        ticks, ordinal = reader.path(entry[0], observation_end)
        px = ticks["b" if row["side"] == "BUY" else "a"]
        hit = np.flatnonzero((px <= row["stop_units"] if row["side"] == "BUY" else px >= row["stop_units"])
                             & (ticks["t"] < end))
        if len(hit):
            index = int(hit[0])
            why = "SL"
        elif final:
            index = int(ticks["t"].searchsorted(final[0]))
        else:
            index = None
            why = "CENSORED" if end >= cutoff else "ENDPOINT_UNKNOWN_OPEN"
        t = dict(row, asset=asset, role="CORE" if asset == "XAUUSD" else "SATELLITE",
                 recipe="A" if asset == "XAUUSD" else "SAT1",
                 entry_msc=entry[0], entry_price_units=p0, entry_quote=entry[:3],
                 entry_quote_index=entry[3], deadline_msc=end,
                 exit_msc=int(ticks["t"][index]) if index is not None else cutoff,
                 exit_price_units=int(px[index]) if index is not None else int(px[-1]),
                 exit_quote_index=int(ordinal[index]) if index is not None else -1,
                 reason=why, regime_weight=1, d1_gate=True,
                 natural_sl=distance, friction=friction,
                 path_resolution="CONDITIONAL_M1" if asset == "XAUUSD" else "OBSERVED_PAIRED_TICKS")
        out.append(t)
        if why == "ENDPOINT_UNKNOWN_OPEN":
            skipped.append(dict(row, missing=why))
    return out, skipped
