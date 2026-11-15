"""Closed-bar F1–F4 atlas, fixed 136 recipes; no returns or validation reads."""
from calendar import monthrange
from datetime import date
from itertools import product
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
from prop_v6_data import aggregate
from quant_core.vectorized_stage0_scanner import HOUR, DAY


def rolling(a, n, kind, *, prior=True):
    out = np.full(len(a), np.nan)
    if len(a) < n:
        return out
    windows = sliding_window_view(np.asarray(a, dtype=float), n)
    if kind == "max":
        values = windows.max(axis=1)
    elif kind == "min":
        values = windows.min(axis=1)
    elif kind == "mean":
        values = windows.mean(axis=1)
    elif kind == "std":
        values = windows.std(axis=1)
    else:
        raise ValueError("rolling_kind")
    out[n-1:] = values
    return np.r_[np.nan, out[:-1]] if prior else out


def atr_before(frame):
    close, high, low = frame["c"], frame["h"], frame["l"]
    prev = np.r_[close[0], close[:-1]]
    true = np.maximum(high-low, np.maximum(abs(high-prev), abs(low-prev)))
    out = np.full(len(close), np.nan)
    if len(close) > 14:
        value = true[:14].mean()
        for i in range(14, len(close)):
            out[i] = value
            value = (13 * value + true[i]) / 14
    return out


def frame(rows, width):
    a = np.asarray(rows, dtype="int64")
    if not len(a):
        raise ValueError("empty_bar_frame")
    result = dict(t=a[:, 0] + width, o=a[:, 1].astype(float), h=a[:, 2].astype(float),
                  l=a[:, 3].astype(float), c=a[:, 4].astype(float))
    result["atr"] = atr_before(result)
    return result


def frames(bars):
    hours = [r for r in aggregate(bars) if r[5] == 60]
    h1 = frame(hours, HOUR)
    h4, daily = [], []
    for width, target, minimum in ((4 * HOUR, h4, 4), (DAY, daily, 20)):
        buckets = {}
        for r in hours:
            buckets.setdefault(r[0] // width * width, []).append(r)
        for at, rs in sorted(buckets.items()):
            if len(rs) < minimum or width == 4 * HOUR and [r[0] for r in rs] != [at+k*HOUR for k in range(4)]:
                continue
            target.append([at, rs[0][1], max(r[2] for r in rs), min(r[3] for r in rs), rs[-1][4]])
    return h1, frame(h4, 4 * HOUR), frame(daily, DAY)


def align(source, target_times, name):
    i = np.searchsorted(source["t"], target_times, side="right") - 1
    result = source[name][np.maximum(i, 0)].astype(float).copy()
    result[i < 0] = np.nan
    return result


def catalog(asset):
    result = []
    for tf, n, impulse, multiple in product(("H4", "D1"), range(3), (0, .5), (1, 2)):
        lookback = (10, 20, 40)[n] if tf == "H4" else (5, 10, 20)[n]
        result.append(dict(family="F1", tf=tf, n=lookback, impulse=impulse, multiple=multiple))
    for sma, pullback, structure in product((20, 40), (2, 4), (4, 8)):
        result.append(dict(family="F2", sma=sma, pullback=pullback, structure=structure))
    for n, multiple in product((7, 14), (1, 2)):
        result.append(dict(family="F3", compression="NR", n=n, multiple=multiple))
    for lookback, quantile, multiple in product((60, 120), (.10, .15), (1, 2)):
        result.append(dict(family="F3", compression="BB", n=lookback, quantile=quantile, multiple=multiple))
    if asset == "XAUUSD":
        for hour, impulse, timing, multiple in product((13, 14, 15, 16), (.5, 1), ("ALL", "WEEK", "MONTH"), (1, 2)):
            result.append(dict(family="F4", hour=hour, impulse=impulse, timing=timing, multiple=multiple))
    for r in result:
        r["id"] = r["family"] + ":" + ":".join(f"{k}={v}" for k, v in r.items() if k != "family")
    return result


def timing_mask(times, mode):
    days = times // DAY
    weekday = (days + 3) % 7
    if mode == "ALL":
        return weekday < 5
    if mode == "WEEK":
        return weekday < 2
    out = []
    for day in days:
        d = date.fromisoformat(str(np.datetime64(int(day), "D")))
        business = [n for n in range(1, monthrange(d.year, d.month)[1]+1)
                    if date(d.year, d.month, n).weekday() < 5]
        out.append(d.day in business[:2] + business[-2:])
    return np.array(out)


def recipes(bars, asset, first, end, calendar):
    h1, h4, daily = frames(bars)
    results = []
    s1, s4 = np.sign(h1["c"] - h1["o"]), np.sign(h4["c"] - h4["o"])
    h1_atr4 = align(h4, h1["t"], "atr")
    h4_atr4 = h4["atr"]
    allowed_cache = {}

    def admit(cfg, tf, buy, sell, stop_buy, stop_sell):
        times = tf["t"]
        if id(tf) not in allowed_cache:
            allowed_cache[id(tf)] = np.array([first <= t < end and calendar.allowed(int(t)) for t in times])
        choose = allowed_cache[id(tf)] & (buy != sell) & np.isfinite(stop_buy) & np.isfinite(stop_sell)
        indices = np.flatnonzero(choose)
        # One raw event/day/recipe. The rule is fixed before price outcomes.
        if len(indices):
            _, unique = np.unique(times[indices] // DAY, return_index=True)
            indices = indices[np.sort(unique)]
        side = np.where(buy[indices], 1, -1).astype("int8")
        stops = np.where(side == 1, np.floor(stop_buy[indices]), np.ceil(stop_sell[indices])).astype("int64")
        results.append(dict(id=cfg["id"], family=cfg["family"], config=cfg,
                            at=times[indices], side=side, stop=stops))

    previous_c4 = np.r_[np.nan, h4["c"][:-1]]
    for cfg in catalog(asset):
        family = cfg["family"]
        if family == "F1":
            source = h4 if cfg["tf"] == "H4" else daily
            upper = rolling(source["h"], cfg["n"], "max", prior=source is h4)
            lower = rolling(source["l"], cfg["n"], "min", prior=source is h4)
            if source is daily:
                # D1 Donchian known only after its D1 closes, applied to H4 decisions.
                upper = align(dict(t=source["t"], level=upper), h4["t"], "level")
                lower = align(dict(t=source["t"], level=lower), h4["t"], "level")
            previous_u, previous_l = np.r_[np.nan, upper[:-1]], np.r_[np.nan, lower[:-1]]
            impulse = abs(h4["c"] - h4["o"]) >= cfg["impulse"] * h4_atr4
            buy = (h4["c"] > upper) & (previous_c4 <= previous_u) & impulse
            sell = (h4["c"] < lower) & (previous_c4 >= previous_l) & impulse
            delta = cfg["multiple"] * h4_atr4
            admit(cfg, h4, buy, sell, h4["c"] - delta, h4["c"] + delta)
        elif family == "F2":
            ma = rolling(h4["c"], cfg["sma"], "mean", prior=False)
            lag = np.r_[np.full(3, np.nan), ma[:-3]]
            bias = np.where((h4["c"] > ma) & (ma > lag), 1,
                            np.where((h4["c"] < ma) & (ma < lag), -1, 0))
            known = align(dict(t=h4["t"], bias=bias), h1["t"], "bias")
            pull_buy = rolling((s1 < 0).astype(float), cfg["pullback"], "max") > 0
            pull_sell = rolling((s1 > 0).astype(float), cfg["pullback"], "max") > 0
            buy = (known == 1) & pull_buy & (h1["c"] > np.r_[np.nan, h1["h"][:-1]]) & (s1 > 0)
            sell = (known == -1) & pull_sell & (h1["c"] < np.r_[np.nan, h1["l"][:-1]]) & (s1 < 0)
            low = rolling(h1["l"], cfg["structure"], "min", prior=False)
            high = rolling(h1["h"], cfg["structure"], "max", prior=False)
            admit(cfg, h1, buy, sell, low - .1 * h1_atr4, high + .1 * h1_atr4)
        elif family == "F3":
            if cfg["compression"] == "NR":
                ranges = daily["h"] - daily["l"]
                compressed = ranges <= rolling(ranges, cfg["n"], "min", prior=False)
                context = dict(t=daily["t"], compressed=compressed.astype(float),
                               upper=daily["h"], lower=daily["l"])
                condition = align(context, h4["t"], "compressed") == 1
                upper, lower = (align(context, h4["t"], n) for n in ("upper", "lower"))
            else:
                ma = rolling(h4["c"], 20, "mean", prior=False)
                width = 4 * rolling(h4["c"], 20, "std", prior=False) / ma
                past_width = np.r_[np.nan, width[:-1]]
                threshold = np.full(len(width), np.nan)
                n = cfg["n"]
                if len(width) > n:
                    threshold[n:] = np.quantile(sliding_window_view(width[:-1], n), cfg["quantile"], axis=1)
                condition = past_width <= threshold
                upper, lower = rolling(h4["h"], 20, "max"), rolling(h4["l"], 20, "min")
            buy = condition & (h4["c"] > upper) & (s4 > 0)
            sell = condition & (h4["c"] < lower) & (s4 < 0)
            delta = cfg["multiple"] * h4_atr4
            admit(cfg, h4, buy, sell, h4["c"] - delta, h4["c"] + delta)
        else:
            hour = h1["t"] // HOUR % 24
            condition = ((hour == cfg["hour"]) & timing_mask(h1["t"], cfg["timing"]) &
                         (abs(h1["c"] - h1["o"]) >= cfg["impulse"] * h1["atr"]))
            delta = cfg["multiple"] * h1_atr4
            admit(cfg, h1, condition & (s1 > 0), condition & (s1 < 0),
                  h1["c"] - delta, h1["c"] + delta)
    return results
