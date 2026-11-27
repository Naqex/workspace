"""Causal structural observations from explicitly bound, checksummed Bid M1 stores."""

import json
from pathlib import Path

import numpy as np

from quant_core.market_data_store import MarketDataStore

HOUR = 3600000


def frame(bars, step, at):
    if not len(bars):
        return []
    codes = bars["t"] // step * step
    starts = np.r_[0, np.flatnonzero(np.diff(codes)) + 1]
    ends = np.r_[starts[1:], len(bars)]
    return [
        (
            int(codes[i]) + step,
            float(bars["bo"][i]),
            float(bars["bh"][i:j].max()),
            float(bars["bl"][i:j].min()),
            float(bars["bc"][j - 1]),
        )
        for i, j in zip(starts, ends, strict=True)
        if int(codes[i]) + step <= at
        and j - i == step // 60000
        and np.array_equal(bars["t"][i:j], np.arange(codes[i], codes[i] + step, 60000))
    ]


def atr(rows):
    if len(rows) < 15:
        return None
    a = np.asarray(rows, dtype=float)
    prev = np.r_[a[0, 4], a[:-1, 4]]
    tr = np.maximum(a[:, 2] - a[:, 3], np.maximum(abs(a[:, 2] - prev), abs(a[:, 3] - prev)))
    value = tr[:14].mean()
    for x in tr[14:]:
        value = (value * 13 + x) / 14
    return float(value)


class MarketFingerprint:
    def __init__(self, bindings):
        self.bindings = json.loads(Path(bindings).read_text(encoding="utf-8-sig"))
        self.stores = {}

    def __call__(self, symbol, at, price, sl, tp):
        spec = self.bindings.get(symbol)
        if not spec:
            return dict(market_features_status="SYMBOL_BINDING_REQUIRED")
        if spec.get("time_basis") != "UTC":
            return dict(market_features_status="SOURCE_UTC_BINDING_REQUIRED")
        if symbol not in self.stores:
            self.stores[symbol] = MarketDataStore(spec["path"])
        store = self.stores[symbol]
        scale = float(spec["scale"])
        if not np.isfinite(scale) or scale <= 0:
            raise ValueError("POSITIVE_STORE_SCALE_REQUIRED")
        b = store.bars(max(at - 45 * 24 * HOUR, 0) // 1000 * 1000, at // 1000 * 1000)
        if not len(b):
            return dict(market_features_status="SOURCE_WINDOW_UNAVAILABLE")
        h1 = frame(b, HOUR, at)
        h4 = frame(b, 4 * HOUR, at)
        a1 = atr(h1)
        a4 = atr(h4)
        result = dict(
            market_features_status="CAUSAL_BID_PROXY_NOT_EXECUTABLE_BIDASK",
            source_raw_sha256=store.raw_declared_sha256,
            ATR_H1=a1 / scale if a1 else None,
            ATR_H4=a4 / scale if a4 else None,
            source_time_basis=spec.get("time_basis", "UNVERIFIED"),
            complete_H1=len(h1),
            complete_H4=len(h4),
        )
        for tf, a in (("H1", a1), ("H4", a4)):
            result["SL_ATR_" + tf] = abs(price - sl) * scale / a if sl > 0 and a else None
            result["TP_ATR_" + tf] = abs(tp - price) * scale / a if tp > 0 and a else None
        if len(h1) >= 20:
            recent = np.asarray(h1[-20:])
            result.update(
                SMA20_H1=float(recent[:, 4].mean() / scale),
                Donchian20_H1_high=float(recent[:, 2].max() / scale),
                Donchian20_H1_low=float(recent[:, 3].min() / scale),
            )
        if len(h1) >= 15:
            d = np.diff(np.asarray(h1[-15:])[:, 4])
            gain = np.maximum(d, 0).mean()
            loss = np.maximum(-d, 0).mean()
            result["RSI14_H1_simple"] = float(100 * gain / (gain + loss)) if gain + loss else 50.0
        day = at // (24 * HOUR) * (24 * HOUR)
        prev = b[(b["t"] >= day - 24 * HOUR) & (b["t"] < day)]
        asia = b[(b["t"] >= day) & (b["t"] < day + 6 * HOUR)] if at >= day + 6 * HOUR else b[:0]
        prev_ok = len(prev) == 1440 and np.array_equal(prev["t"], np.arange(day - 24 * HOUR, day, 60000))
        asia_ok = len(asia) == 360 and np.array_equal(asia["t"], np.arange(day, day + 6 * HOUR, 60000))
        result.update(
            previous_UTC_day_coverage="COMPLETE_M1_GRID" if prev_ok else "INCOMPLETE_OR_MARKET_BREAK_UNVERIFIED",
            Asian00_06_coverage="COMPLETE_M1_GRID" if asia_ok else "INCOMPLETE_OR_NOT_YET_CLOSED",
        )
        if prev_ok:
            result.update(PDH_UTC=float(prev["bh"].max() / scale), PDL_UTC=float(prev["bl"].min() / scale))
        if asia_ok:
            result.update(
                Asian00_06_high=float(asia["bh"].max() / scale),
                Asian00_06_low=float(asia["bl"].min() / scale),
            )
        return result
