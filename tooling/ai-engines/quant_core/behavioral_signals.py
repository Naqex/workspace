"""Closed-H1 sweep/reclaim and London-clock momentum hypotheses, no outcome reads."""

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import numpy as np
from prop_v10_signals import align, frames, timing_mask

from quant_core.native_hourly_source import closed_frames

HOUR, DAY = 3600000, 86400000


def closed_atr(frame):
    h, lo, c = (np.asarray(frame[n], dtype=float) for n in ("h", "l", "c"))
    tr = np.maximum(h - lo, np.maximum(abs(h - np.r_[c[0], c[:-1]]), abs(lo - np.r_[c[0], c[:-1]])))
    out = np.full(len(c), np.nan)
    if len(c) >= 14:
        out[13] = tr[:14].mean()
        for i in range(14, len(c)):
            out[i] = (13 * out[i - 1] + tr[i]) / 14
    return out


def london_hour(at):
    return datetime.fromtimestamp(int(at) / 1000, UTC).astimezone(ZoneInfo("Europe/London")).hour


def recipes(bars, asset, first, end, *, hourly=False):
    h1, h4, daily = closed_frames(bars) if hourly else frames(bars)
    t = h1["t"]
    day = t // DAY
    opens = (t - HOUR) % DAY // HOUR
    prior_high, prior_low = (align(daily, t, n) for n in ("h", "l"))
    atr4 = align(dict(t=h4["t"], atr=closed_atr(h4)), t, "atr")
    asia_h = np.full(len(t), np.nan)
    asia_l = asia_h.copy()
    day_high = asia_h.copy()
    day_low = asia_h.copy()
    day_open = asia_h.copy()
    for d in np.unique(day):
        ix = np.flatnonzero(day == d)
        # H1 bars are known at their close. The midnight close belongs to prior day.
        current = ix[t[ix] % DAY > 0]
        if not len(current):
            continue
        day_high[current] = np.maximum.accumulate(h1["h"][current])
        day_low[current] = np.minimum.accumulate(h1["l"][current])
        day_open[current] = h1["o"][current[0]]
        asia = current[(t[current] % DAY >= HOUR) & (t[current] % DAY <= 6 * HOUR)]
        if len(asia) == 6:
            after = ix[t[ix] % DAY >= 6 * HOUR]
            asia_h[after] = max(h1["h"][asia])
            asia_l[after] = min(h1["l"][asia])
    common = (t >= first) & (t < end) & np.isfinite(h1["atr"]) & (h1["atr"] > 0)
    out = []

    def add(identity, family, use, side):
        ix = np.flatnonzero(use & common)
        if len(ix):
            _, at = np.unique(day[ix], return_index=True)
            ix = ix[np.sort(at)]
        s = side[ix]
        stops = np.where(
            s == 1,
            np.floor(h1["l"][ix] - 0.1 * h1["atr"][ix]),
            np.ceil(h1["h"][ix] + 0.1 * h1["atr"][ix]),
        ).astype("int64")
        out.append(dict(id=identity, family=family, at=t[ix].astype("int64"), side=s.astype("int8"), stop=stops))

    windows = ((opens >= 7) & (opens < 10)) | ((opens >= 13) & (opens < 15))
    midpoint = (h1["h"] + h1["l"]) / 2
    for level, hi, lo in (("PD", prior_high, prior_low), ("ASIA", asia_h, asia_l)):
        for fraction in (0.1, 0.3, 0.6):
            inside = (h1["c"] > lo) & (h1["c"] < hi)
            swept_low = h1["l"] <= lo - fraction * atr4
            swept_high = h1["h"] >= hi + fraction * atr4
            buy = swept_low & ~swept_high & inside & (h1["c"] > midpoint)
            sell = swept_high & ~swept_low & inside & (h1["c"] < midpoint)
            add(f"B2:{level}:sweep={fraction}", "B2", windows & (buy != sell), np.where(buy, 1, -1))
    if asset in ("XAUUSD", "US500"):
        clock = np.array([london_hour(at) == 15 for at in t])
        body = h1["c"] - h1["o"]
        direction = np.sign(body)
        move = h1["c"] - day_open
        width = day_high - day_low
        location = np.divide(h1["c"] - day_low, width, out=np.full(len(t), 0.5), where=width > 0)
        impulse = (
            (abs(body) >= h1["atr"])
            & (direction * move > 0)
            & np.where(direction > 0, location >= 0.75, location <= 0.25)
        )
        for timing in ("ALL", "MONTH"):
            add(f"B3:London15:impulse=1:{timing}", "B3", clock & impulse & timing_mask(t, timing), direction)
    return out
