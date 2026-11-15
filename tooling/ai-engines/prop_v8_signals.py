"""Two registered normalizers and the three existing sweep horizons."""
from collections import defaultdict, deque
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from statistics import median
import numpy as np
from prop_campaign_source import signals as original
from prop_atlas_scan import daily_context
from xau_h1_stage0_source import signal_features
from prop_portfolio_scan import raw_geometry
from prop_v8_common import *


def contexts(hours, first):
    hm = {r[0]: r for r in hours if r[5] == 60}
    history = deque(maxlen=20)
    out = {}
    for day in sorted({at // DAY * DAY for at in hm if at >= first}):
        group = [hm.get(day + i * HOUR) for i in range(6)]
        if any(x is None for x in group):
            continue
        width = max(x[2] for x in group) - min(x[3] for x in group)
        out[day] = dict(asian_range=width, ratio=width / median(history) if len(history) == 20 else None)
        history.append(width)
    return out


def normalize(raw, ctx, version, k):
    if version not in ("N1", "N2"):
        raise ValueError("V8_only_two_trials")
    out, rejects = [], []
    for r in raw:
        day = r["decision_msc"] // DAY * DAY
        c = ctx.get(day)
        if version == "N1" and (c is None or c["ratio"] is None or c["ratio"] > k):
            rejects.append(dict(day=r["day"], reason="COMPRESSION_OR_CONTEXT"))
            continue
        row = dict(r, variant=version)
        if version == "N2":
            buy = r["side"] == "BUY"
            extreme = r["bar_units"][2 if buy else 1]
            value = Decimal(extreme) + Decimal(r["atr_h1_before_units"]) * Decimal("-.1" if buy else ".1")
            structural = int(value.to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING))
            row["stop_units"] = max(structural, r["stop_units"]) if buy else min(structural, r["stop_units"])
        out.append(row)
    return out, rejects


def sweep(hours, first, end, calendar):
    """Same PREVDAY London H1 sweep as the frozen atlas, scoped to three IDs."""
    history, _ = daily_context(hours)
    seen, out = set(), []
    for f in signal_features(hours):
        at = f["at"]
        d = datetime.fromtimestamp(at / 1000, timezone.utc)
        day = at // DAY * DAY
        if not first <= at < end or not 8 <= d.hour <= 11 or not calendar.allowed(at):
            continue
        if f["atr_before"] is None or day not in history or day in seen:
            continue
        upper, lower = history[day]
        b = f["bar"]
        buy, sell = b[3] < lower < b[4] and b[4] > b[1], b[2] > upper > b[4] and b[4] < b[1]
        if buy == sell:
            continue
        value = Decimal(b[3] if buy else b[2]) + f["atr_before"] * Decimal("-.1" if buy else ".1")
        stop = int(value.to_integral_value(rounding=ROUND_FLOOR if buy else ROUND_CEILING))
        for name in CELLS:
            out.append(dict(id=name, recipe=name, asset="XAUUSD", side="BUY" if buy else "SELL",
                day=d.date().isoformat(), decision_msc=at, stop_units=stop,
                atr_h1_before_units=str(f["atr_before"]), horizon=name.rsplit(".", 1)[1]))
        seen.add(day)
    return out


def realize(raw, reader, calendar, cutoff, *, core=False):
    out, rejected = [], []
    for raw_row in raw:
        r = dict(raw_row, asset="XAUUSD")
        at = r["decision_msc"]
        if not calendar.allowed(at):
            rejected.append(dict(day=r["day"], reason="CALENDAR"))
            continue
        entry = reader.endpoint(at)
        if entry is None:
            rejected.append(dict(day=r["day"], reason="ENTRY_UNKNOWN"))
            continue
        p0, distance, friction, _ = raw_geometry(r, entry)
        if distance <= 0:
            rejected.append(dict(day=r["day"], reason="INVALID_STOP"))
            continue
        end, why = calendar.deadline(entry[0])
        horizon = r.get("horizon", "48H")
        target = (entry[0] // DAY * DAY + 20 * HOUR + HOUR // 2 if horizon == "DAY"
                  else entry[0] + (24 if horizon == "24H" else 48) * HOUR)
        if target < end:
            end, why = target, horizon
        final = reader.endpoint(end) if end < cutoff else None
        path_end = final[0] if final else min(end, cutoff - 1)
        path, ordinal = reader.path(entry[0], path_end)
        px = path["b" if r["side"] == "BUY" else "a"]
        crossed = np.flatnonzero((px <= r["stop_units"] if r["side"] == "BUY" else px >= r["stop_units"])
                                 & (path["t"] < end))
        j = int(crossed[0]) if len(crossed) else int(path["t"].searchsorted(final[0])) if final else None
        reason = "SL" if len(crossed) else why if final else "CENSORED" if end >= cutoff else "ENDPOINT_UNKNOWN_OPEN"
        fees = friction / distance
        r.update(entry_msc=entry[0], entry_price_units=p0, entry_quote_index=entry[3],
            deadline_msc=end, exit_msc=int(path["t"][j]) if j is not None else cutoff,
            exit_price_units=int(px[j]) if j is not None else int(px[-1]),
            exit_quote_index=int(ordinal[j]) if j is not None else -1,
            reason=reason, natural_sl=distance, friction=friction, friction_ratio=fees,
            regime_weight=1, role="CORE" if core else "SATELLITE", d1_gate=True,
            qualifies=fees <= (.12 if core else .15) and (not core or distance <= 25),
            source_kinds=sorted({reader.files[h]["source_kind"] for h in range(
                entry[0] // HOUR * HOUR, min(path_end, cutoff - 1) // HOUR * HOUR + HOUR, HOUR)
                if h in reader.files}))
        out.append(r)
    return out, rejected
