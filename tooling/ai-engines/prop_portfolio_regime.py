"""One causal completed-D1 sizing trial; no entry, stop or exit tuning."""
from bisect import bisect_right
from collections import deque
from datetime import datetime, timezone
import numpy as np

from prop_campaign_accounts import Account, replay
from prop_campaign_source import Prices, stamp
from prop_portfolio_common import (
    JOB, V1, MODELS, ROOT, END, DAY, read, write_json, digest, event, price_scope,
)


def states(days):
    closes = deque(maxlen=50)
    averages = deque(maxlen=6)
    result = []
    for row in days:
        if row["minutes"] < 1200:
            continue
        closes.append(row["close"])
        if len(closes) < 50:
            continue
        average = sum(closes) / 50
        averages.append(average)
        if len(averages) < 6:
            continue
        slope = averages[-1] - averages[0]
        direction = (
            "BUY" if row["close"] > average and slope > 0
            else "SELL" if row["close"] < average and slope < 0 else "NEUTRAL"
        )
        result.append(dict(
            known_at=row["day"] + DAY, last_day=row["day"], close=row["close"],
            sma50=average, sma50_slope5=slope, regime=direction,
        ))
    return result


def weight_at(records, at, side):
    index = bisect_right([r["known_at"] for r in records], at) - 1
    if index < 0 or at - records[index]["known_at"] > 4 * DAY:
        return None, None
    row = records[index]
    factor = 1 if row["regime"] in ("NEUTRAL", side) else 0.5
    return factor, row


def load_daily(cutoff=END):
    price_scope(cutoff)
    root = ROOT / "gold-continuous-B2-20261113-v1/source-cache"
    manifest = read(root / "manifest.json")
    if (manifest["raw_sha256"] !=
            "d209df9a5ce871f1992eb312595ebef2c19a884c1fe0a1be6bfb76d86cf471b9"
            or manifest["byteorder"] != "little"):
        raise ValueError("D1_source_binding")
    for name in ("times.bin", "c.bin"):
        if digest(root / name) != manifest["files"][name]:
            raise ValueError("D1_source_changed")
    times = np.fromfile(root / "times.bin", dtype="<i8")
    lo, hi = np.searchsorted(times, [stamp("2021-01-01") // 1000, cutoff // 1000])
    with (root / "c.bin").open("rb") as stream:
        stream.seek(int(lo) * 4)
        closes = np.fromfile(stream, dtype="<i4", count=int(hi - lo))
    times = times[lo:hi] * 1000
    if not len(times) or times[-1] >= cutoff:
        raise ValueError("D1_price_fence")
    days, indices, counts = np.unique(times // DAY * DAY, return_index=True, return_counts=True)
    ends = np.r_[indices[1:] - 1, len(times) - 1]
    result = [
        dict(day=int(day), minutes=int(n), close=int(closes[end]))
        for day, n, end in zip(days, counts, ends)
    ]
    write_json(JOB / ("d1-dev-source.json" if cutoff == END else "d1-validation-source.json"),
               dict(start="2021-01-01", end_exclusive=cutoff, days=result,
                    pins=manifest["files"], bounded_price_read=True))
    return states(result)


def attach(trades, records):
    result = []
    for trade in trades:
        factor, state = weight_at(records, trade["decision_msc"], trade["side"])
        if factor is None:
            raise ValueError("unknown_D1_at_signal:" + trade["signal_id"])
        result.append(dict(
            trade, regime_weight=factor, regime_known_at=state["known_at"],
            d1_regime=state["regime"],
        ))
    return result


class RegimeAccount(Account):
    def __init__(self, *args, scaled=False, **kwargs):
        super().__init__(*args, **kwargs)
        self.scaled = scaled
        self.factor = 1

    def risk(self, equity):
        return self.fixed_risk * self.factor

    def action(self, kind, at, i, trades, quote, mult=0):
        if kind == "entry":
            self.factor = trades[i]["regime_weight"] if self.scaled else 1
            if self.risk(0) * 1000 < abs(
                    trades[i]["entry_price_units"] - trades[i]["stop_units"]):
                self.rejected["LOT_GRID_MIN"] += 1
                return
        super().action(kind, at, i, trades, quote, mult)


def phase1():
    records = load_daily()
    reader = Prices(read(V1 / "gold-dev-manifest-v2.json"))
    measured = {}
    for model in MODELS:
        trades = attach(read(V1 / f"paths-{model}-A0.json"), records)
        write_json(JOB / f"regime-{model}-dev-trades.json", trades)
        accounts = []
        for scaled in (False, True):
            for first, end in (("2022-01-01", "2023-01-01"),
                               ("2023-01-01", "2024-01-01"),
                               ("2022-01-01", "2024-01-01")):
                accounts.append(RegimeAccount(stamp(first), stamp(end), model, scaled=scaled))
        rows = replay(trades, reader, accounts, end=END)
        for index, row in enumerate(rows):
            row["variant"] = "A_RegimeScaled" if index >= 3 else "A_Original"
            row["period"] = ("2022", "2023", "2022-2023")[index % 3]
            row["reference_net_R"] = row["net_usd"] / 150
        measured[model] = rows
        event("D1_regime_measured", model=model, entries=len(trades))
    reasons = []
    for model, rows in measured.items():
        original, scaled = rows[2], rows[5]
        old_ratio = original["reference_net_R"] / original["max_equity_R_DD"]
        new_ratio = scaled["reference_net_R"] / scaled["max_equity_R_DD"]
        if new_ratio <= old_ratio:
            reasons.append(model + ":RETURN_DD_NOT_IMPROVED")
        if scaled["entries"] < original["entries"] * 0.95:
            reasons.append(model + ":SAMPLE_RETENTION")
    write_json(JOB / "regime-comparison.json", measured)
    decision = dict(
        selected="A_Original" if reasons else "A_RegimeScaled", reasons=reasons,
        cutoff=END, one_trial=True, prices2024_2026_read=False,
        utc=datetime.now(timezone.utc).isoformat(),
    )
    write_json(JOB / "core-decision.json", decision)
    event("D1_regime_decision", **decision)


if __name__ == "__main__":
    phase1()
