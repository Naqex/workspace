"""Scoped extension of the frozen A and single EUR sweep, without old-guard edits."""
from bisect import bisect_right
from datetime import datetime, timezone, timedelta
from decimal import Decimal, ROUND_FLOOR, ROUND_CEILING
from xau_h1_stage0_source import signal_features, HOUR, DAY
from prop_campaign_source import signals as original_gold, START, FINAL


class Calendar:
    def __init__(self, data, end):
        self.events = {r["day"]: r for r in data["events"]}
        self.flats = []
        day = datetime(2022, 1, 1, tzinfo=timezone.utc)
        while int(day.timestamp() * 1000) < end + 8 * DAY:
            row = self.events.get(day.date().isoformat(), {})
            if row.get("flat_utc"):
                clock = row["flat_utc"]
                self.flats.append((int(day.timestamp() * 1000) +
                                   (int(clock[:2]) * 60 + int(clock[3:])) * 60000, "HOLIDAY_FLAT"))
            if day.weekday() == 4:
                self.flats.append((int(day.timestamp() * 1000) + 20 * HOUR + HOUR // 2, "FRIDAY_CLOSE"))
            day += timedelta(days=1)
        self.flats.sort()
        self.times = [r[0] for r in self.flats]

    def allowed(self, at):
        d = datetime.fromtimestamp(at / 1000, timezone.utc)
        r = self.events.get(d.date().isoformat(), {})
        return (d.weekday() < 5 and r.get("kind") != "CLOSED" and
                (not r.get("flat_utc") or d.strftime("%H:%M") < r["flat_utc"]))

    def deadline(self, at):
        if not self.allowed(at):
            raise ValueError("entry_outside_session")
        i = bisect_right(self.times, at)
        if i == len(self.flats):
            raise ValueError("calendar_missing_future_flat")
        flat, reason = self.flats[i]
        return (flat, reason) if flat < at + 48 * HOUR else (at + 48 * HOUR, "TIME_48H")


def generate(hours, asset, first, end, calendar):
    if asset == "XAUUSD":
        return [r for r in original_gold(hours, first=first, end=end)
                if r["recipe"] == "A" and calendar.allowed(r["decision_msc"])]
    if asset != "EURUSD":
        raise ValueError("V6_only_two_frozen_sleeves")
    hm = {r[0]: r for r in hours if r[5] == 60}
    seen = set()
    out = []
    for f in signal_features(hours):
        at = f["at"]
        dt = datetime.fromtimestamp(at / 1000, timezone.utc)
        if not first <= at < end or not 8 <= dt.hour <= 11 or not calendar.allowed(at):
            continue
        if f["atr_before"] is None:
            continue
        day = at // DAY * DAY
        asia = [hm.get(day + i * HOUR) for i in range(6)]
        if any(r is None for r in asia) or day in seen:
            continue
        upper, lower = max(r[2] for r in asia), min(r[3] for r in asia)
        b = f["bar"]
        buy = b[3] < lower < b[4] and b[4] > b[1]
        sell = b[2] > upper > b[4] and b[4] < b[1]
        if buy == sell:
            continue
        stop = Decimal(b[3] if buy else b[2]) + (-f["atr_before"] / 10 if buy else f["atr_before"] / 10)
        cell = "EURUSD.SWEEP.ASIA.LONDON.DAY"
        out.append(dict(id=cell, asset=asset, mechanism="SWEEP", region="ASIA",
                        window="LONDON", horizon="DAY", recipe=cell,
                        side="BUY" if buy else "SELL", decision_msc=at,
                        day=dt.date().isoformat(),
                        stop_units=int(stop.to_integral_value(
                            rounding=ROUND_FLOOR if buy else ROUND_CEILING)),
                        known_h4_at=f["bias_at"]))
        seen.add(day)
    return out


def deadline(row, entry, calendar):
    end, why = calendar.deadline(entry)
    if row.get("asset") == "EURUSD":
        session = entry // DAY * DAY + 20 * HOUR + HOUR // 2
        if session < end:
            return session, "DAY"
    return end, why
