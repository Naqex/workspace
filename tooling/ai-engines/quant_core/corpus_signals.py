"""Independent formula port of the reviewed closed-H1 engulfing/RSI mechanism."""

import numpy as np
from prop_v10_signals import rolling


def wilder_rsi(close, period):
    close = np.asarray(close, dtype=float)
    result = np.full(len(close), np.nan)
    if len(close) <= period:
        return result
    diff = np.diff(close)
    gain, loss = np.maximum(diff, 0), np.maximum(-diff, 0)
    up, down = gain[:period].mean(), loss[:period].mean()
    for i in range(period, len(close)):
        if i > period:
            up = (up * (period - 1) + gain[i - 1]) / period
            down = (down * (period - 1) + loss[i - 1]) / period
        result[i] = 100 * up / (up + down) if up + down else 50
    return result


def engulfing_rsi(frame):
    op, close = frame["o"], frame["c"]
    body = rolling(abs(close - op), 12, "mean", prior=False)
    trend = rolling(close, 5, "mean", prior=True)
    rsi = wilder_rsi(close, 37)
    old_o, old_c = np.r_[np.nan, op[:-1]], np.r_[np.nan, close[:-1]]
    old_mid = (old_o + old_c) / 2
    buy = (old_o > old_c) & (close - op > body) & (close > old_o) & (old_mid < trend) & (op < old_c) & (rsi < 40)
    sell = (old_o < old_c) & (op - close > body) & (close < old_o) & (old_mid > trend) & (op > old_c) & (rsi > 60)
    return np.where(buy, 1, np.where(sell, -1, 0)).astype("int8")
