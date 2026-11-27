"""Source-default SL/TP/expiry normalization on observed M1 paths only."""

import numpy as np
from prop_v14_paths import M1ScenarioQuotes, crossing

from quant_core.corpus_batch_signals import lag
from quant_core.vectorized_sl_active_kernel import PathIndex

HOUR = 3600000


def default_exits(frame, values, signal, oscillator):
    old = lag(values, 1)
    lower, upper = {"RSI": (30, 70), "CCI": (-80, 80), "MFI": (30, 70), "Stoch": (20, 80)}[oscillator]
    buy = ((values < upper) & (old > upper)) | ((values < lower) & (old > lower))
    sell = ((values > lower) & (old < lower)) | ((values > upper) & (old < upper))
    # Source skips oscillator close checks when a confirmed entry is present.
    return buy & (signal == 0), sell & (signal == 0)


def normalize_trades(bars, frame, signals, values, oscillator, at, side, natural, deadline, identity, order, asset):
    index = PathIndex(bars, asset=asset)
    reader = M1ScenarioQuotes(
        bars,
        "OPEN_HIGH_LOW_CLOSE" if order == "OHLC" else "OPEN_LOW_HIGH_CLOSE",
        int(bars["t"][0]),
        int(bars["t"][-1]) + 60000,
    )
    entry_indices = bars["t"].searchsorted(at)
    entry = np.where(side == 1, bars["ao"][entry_indices], bars["bo"][entry_indices]).astype("int64")
    stops = entry - side * natural
    targets = entry + side * natural
    end_indices = bars["t"].searchsorted(deadline)
    safe_end = np.minimum(end_indices, len(bars) - 1)
    valid = (end_indices < len(bars)) & (bars["t"][safe_end] == deadline)
    exits, prices, reasons = (
        deadline.copy(),
        np.where(side == 1, bars["bo"][safe_end], bars["ao"][safe_end]),
        np.full(len(at), "EXPIRY", dtype="<U16"),
    )
    sl = index.first(entry_indices, end_indices, stops, side=side)
    tp = index.first(entry_indices, end_indices, targets, side=side, favorable=True)
    ties = (sl == tp) & (sl < end_indices)
    choose_tp = (tp < sl) | (ties & ((side == 1) if order == "OHLC" else (side == -1)))
    hit = np.minimum(sl, tp)
    stopped = hit < end_indices
    safe = np.minimum(hit, len(bars) - 1)
    prices[stopped] = np.where(choose_tp, targets, stops)[stopped]
    # Gap-through opening fills use actual worse quote for stops.
    opening = np.where(side == 1, bars["bo"][safe], bars["ao"][safe])
    crossed = (side * (opening - stops) <= 0) & ~choose_tp & stopped
    prices[crossed] = opening[crossed]
    exits[stopped] = bars["t"][safe][stopped] + 59999
    exits[crossed] = bars["t"][safe][crossed]
    reasons[stopped] = np.where(choose_tp, "TP", "SL")[stopped]
    close_buy, close_sell = default_exits(frame, values, signals, oscillator)
    output = []
    last_exit = -1
    for i, when in enumerate(at):
        if when <= last_exit:
            continue
        if not valid[i]:
            output.append(dict(incomplete=True, reason="MISSING_EXPIRY_ENDPOINT", entry_msc=int(when)))
            continue
        if stopped[i]:
            minute = int(bars["t"][safe[i]])
            q = reader.points(minute, minute + 59999)
            field = "b" if side[i] == 1 else "a"
            level = int(targets[i] if choose_tp[i] else stops[i])
            touches = np.flatnonzero(
                side[i] * (q[field] - level) >= 0 if choose_tp[i] else side[i] * (q[field] - level) <= 0
            )
            exits[i], prices[i] = crossing(q, int(touches[0]), level, int(side[i]), limit=bool(choose_tp[i]))
        close_times = frame["t"][close_buy if side[i] == 1 else close_sell]
        j = close_times.searchsorted(when, side="right")
        if j < len(close_times) and close_times[j] < exits[i]:
            candidate = int(close_times[j])
            k = int(bars["t"].searchsorted(candidate))
            if k >= len(bars) or bars["t"][k] != candidate:
                output.append(dict(incomplete=True, reason="MISSING_OSCILLATOR_EXIT", entry_msc=int(when)))
                continue
            exits[i] = candidate
            prices[i] = bars["bo" if side[i] == 1 else "ao"][k]
            reasons[i] = "OSCILLATOR"
        k = int(bars["t"].searchsorted(exits[i] // 60000 * 60000))
        complete = bool(index.complete([entry_indices[i]], [min(k, len(bars) - 1)])[0])
        output.append(
            dict(
                id=identity,
                asset=asset,
                side="BUY" if side[i] == 1 else "SELL",
                decision_msc=int(when),
                entry_msc=int(when),
                exit_msc=int(exits[i]),
                entry_price_units=int(entry[i]),
                exit_price_units=int(prices[i]),
                stop_units=int(stops[i]),
                reason=str(reasons[i]),
                source_uncertain=not complete,
                incomplete=not complete,
                same_minute_SL_TP_ambiguous=bool(ties[i]),
            )
        )
        last_exit = int(exits[i])
    return output
