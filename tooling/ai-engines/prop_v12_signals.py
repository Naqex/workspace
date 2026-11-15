"""Six fixed F5 range rejection recipes per asset, all decisions on closed bars."""
import numpy as np
from prop_v10_signals import frames, rolling, align
from quant_core.native_hourly_source import closed_frames
from quant_core.vectorized_stage0_scanner import DAY


def adx14(frame):
    high, low, close = (np.asarray(frame[n], dtype=float) for n in ("h", "l", "c"))
    out = np.full(len(high), np.nan)
    if len(high) < 28:
        return out
    up, down = np.r_[0., np.diff(high)], np.r_[0., -np.diff(low)]
    plus = np.where((up > down) & (up > 0), up, 0.)
    minus = np.where((down > up) & (down > 0), down, 0.)
    prev = np.r_[close[0], close[:-1]]
    tr = np.maximum(high-low, np.maximum(abs(high-prev), abs(low-prev)))
    def smooth(a):
        result = np.full(len(a), np.nan);result[13] = a[:14].mean()
        for i in range(14, len(a)):
            result[i] = (13*result[i-1]+a[i])/14
        return result
    atr, p, m = smooth(tr), smooth(plus), smooth(minus)
    p = np.divide(p, atr, out=np.zeros(len(p)), where=atr>0)
    m = np.divide(m, atr, out=np.zeros(len(m)), where=atr>0)
    dx = np.divide(abs(p-m), p+m, out=np.zeros(len(p)), where=p+m>0)*100
    out[26] = dx[13:27].mean()
    for i in range(27, len(high)):
        out[i] = (13*out[i-1]+dx[i])/14
    return out


def rejection_recipes(bars, asset, first, end, calendar, *, native=False):
    h1, h4, daily = closed_frames(bars) if native else frames(bars)
    result = []
    for label, frame in (("H1", h1), ("H4", h4)):
        adx = adx14(frame)
        times = frame["t"]
        allowed = np.array([first <= t < end and calendar.allowed(int(t)) for t in times])
        midpoint = (frame["h"]+frame["l"])/2
        for n in (3, 5, 10):
            context = dict(t=daily["t"], upper=rolling(daily["h"], n, "max", prior=False),
                           lower=rolling(daily["l"], n, "min", prior=False))
            upper, lower = (align(context, times, k) for k in ("upper", "lower"))
            inside = (frame["c"] > lower) & (frame["c"] < upper)
            buy = (frame["l"] < lower) & inside & (frame["c"] > midpoint)
            sell = (frame["h"] > upper) & inside & (frame["c"] < midpoint)
            use = allowed & (adx <= 25) & np.isfinite(frame["atr"]) & (buy != sell)
            ix = np.flatnonzero(use)
            if len(ix):
                _, unique = np.unique(times[ix]//DAY, return_index=True)
                ix = ix[np.sort(unique)]
            side = np.where(buy[ix], 1, -1).astype("int8")
            stop = np.where(side == 1, np.floor(frame["l"][ix]-.1*frame["atr"][ix]),
                            np.ceil(frame["h"][ix]+.1*frame["atr"][ix])).astype("int64")
            config = dict(family="F5", tf=label, n=n, adx=25, buffer=.1)
            identity = "F5:"+":".join(f"{k}={v}" for k, v in config.items() if k != "family")
            result.append(dict(id=identity, family="F5", config=config, at=times[ix], side=side, stop=stop))
    return result
