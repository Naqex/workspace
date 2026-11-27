"""Single future-campaign facade for versioned FTMO assumptions and session guards."""

from bisect import bisect_right
from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import ROUND_HALF_UP, Decimal
from zoneinfo import ZoneInfo

from prop_v8_calendar_correction import corrected_data
from prop_v8_source import Calendar
from xau_h1_stage0_scan import funding_events

HOUR = 3600000
DAY = 24 * HOUR


class SessionSchedule:
    """Versioned declared guards, separate from proof that a feed had no quotes."""

    version = "V13_DECLARED_SESSION_AND_NEXT_QUOTE_V1"

    def __init__(self, events):
        self.events = {r["day"]: dict(r) for r in events}
        self.ny = ZoneInfo("America/New_York")
        self.flats = sorted(
            int(datetime.fromisoformat(day).replace(tzinfo=UTC).timestamp() * 1000)
            + (int(row["flat_utc"][:2]) * 60 + int(row["flat_utc"][3:])) * 60000
            for day, row in self.events.items()
            if row.get("flat_utc")
        )

    def off_kind(self, at, asset):
        utc = datetime.fromtimestamp(int(at) / 1000, UTC)
        local = utc.astimezone(self.ny)
        minute = local.hour * 60 + local.minute
        if (
            local.weekday() == 5
            or local.weekday() == 4
            and minute >= 1020
            or local.weekday() == 6
            and minute < (1080 if asset == "XAUUSD" else 1020)
        ):
            return "WEEKEND"
        row = self.events.get(utc.date().isoformat(), {})
        if row.get("kind") == "CLOSED":
            return "DECLARED_HOLIDAY"
        # Guards are not broker-certified closing times. Classification retains that label.
        if row.get("flat_utc") and utc.strftime("%H:%M") >= row["flat_utc"]:
            if local.hour < 18:
                return "DECLARED_EARLY_GUARD"
        if asset == "XAUUSD" and 1020 <= minute < 1080:
            return "DAILY_BREAK"
        return None

    def target(self, entry, deadline, asset):
        """No source prices/timestamps are used to anticipate a future gap."""
        j = bisect_right(self.flats, int(entry))
        if j < len(self.flats) and self.flats[j] <= deadline:
            deadline = self.flats[j]
        kind = self.off_kind(deadline, asset)
        if kind == "DAILY_BREAK":
            local = datetime.fromtimestamp(int(deadline) / 1000, UTC).astimezone(self.ny)
            return int(local.replace(hour=18, minute=0, second=0, microsecond=0).timestamp() * 1000)
        return int(deadline)


def execution_schedule(first, end):
    """Explicit opt-in; frozen V1–V12 calendar consumers keep their old semantics."""
    return SessionSchedule(gold_calendar(first, end).events.values())


@dataclass(frozen=True)
class GoldCosts:
    model: str
    commission_side: Decimal = Decimal(".000007")
    market_slippage_oz: Decimal = Decimal(".20")
    limit_tp_slippage_oz: Decimal = Decimal("0")
    contract_oz: int = 100

    def swap_per_oz(self, side):
        if self.model not in ("SYM_FLAT", "ASYM_ORDER") or side not in ("BUY", "SELL"):
            raise ValueError("unregistered_cost_scenario")
        return Decimal("-.40") if self.model == "SYM_FLAT" else Decimal("-.45" if side == "BUY" else "-.05")

    def money(self, trade, ounces):
        if type(ounces) is not int or not 1 <= ounces <= 5000:
            raise ValueError("gold_lot_grid")
        p0, px = (Decimal(trade[k]) / 1000 for k in ("entry_price_units", "exit_price_units"))

        def cent(v):
            return v.quantize(Decimal(".01"), rounding=ROUND_HALF_UP)

        gross = cent((px - p0) * ounces * (1 if trade["side"] == "BUY" else -1))
        commission = sum(cent(p * ounces * self.commission_side) for p in (p0, px))
        exit_slip = (
            self.limit_tp_slippage_oz
            if trade["reason"].startswith("TP") and self.model == "ASYM_ORDER"
            else self.market_slippage_oz
        )
        slippage = ounces * (self.market_slippage_oz + exit_slip)
        multipliers = sum(e["multiplier"] for e in funding_events(trade["entry_msc"], trade["exit_msc"]))
        swap = ounces * self.swap_per_oz(trade["side"]) * multipliers
        net = gross - commission - slippage + swap
        return {
            k: float(v)
            for k, v in dict(
                gross_usd=gross, commission_usd=commission, slippage_usd=slippage, swap_usd=swap, net_usd=net
            ).items()
        }


def gold_calendar(first, end):
    # Includes V8's verified 31Dec2021 correction; all other uncertainty labels survive.
    return Calendar(corrected_data(), first, end)
