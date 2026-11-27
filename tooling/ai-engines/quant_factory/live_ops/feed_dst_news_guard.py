"""Live-Ops Feed Health, US/EU DST Resolver, Extended 8-CCY+EIA News & TTL Guard.

Strictly offline, deterministic, and fail-closed:
  - ORDER_SEND_CAPABLE = False, ORDER_SEND_COUNT = 0
  - NEVER imports MetaTrader5; NEVER mutates frozen red-news calendars or production CSV.
  - ZERO bare `assert` statements ([ARCH-02]).

Core capabilities:
  1. US DST (`America/New_York`, 17:00 NY == server NY+7 midnight for FTMO/The5ers) vs
     EU DST (`Europe/Prague`, `Europe/London`, `Europe/Athens`) resolver explicitly
     proving & guarding the 2-3 week March and 1-week Oct/Nov 1-hour divergence windows.
  2. Additive 8-CCY + EIA extended calendar loader & EIA Weekly Petroleum Status Report
     holiday-shift resolver (10:30 ET Wed; US Federal Holiday Mon/Tue/Wed -> Thu 11:00 ET
     in 2018-2024 historical regime / Thu 12:00 ET in 2026-2027 eia.gov published regime).
  3. Calendar TTL Expiry Guard (`check_calendar_ttl`):
       GREEN > 14d | AMBER <= 14d and > 3d | RED <= 3d or expired/missing (fail-closed).
  4. Extended Symbol-to-Event matcher fixing `USOIL/UKOIL` (-> EIA + USD),
     `JP225` (-> JPY + USD), `XAGUSD/XAUUSD` (-> USD), and `CHF/NZD` crosses.
  5. Stale-tick, freeze-quote, and synthetic-spread spike detector (`evaluate_feed_health`).
"""

from __future__ import annotations

import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta, tzinfo
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from quant_core.red_news import (
    DEFAULT_BLACKOUT_SEC,
    MAX_BLACKOUT_SEC,
    RedNewsEvent,
    load_calendar_events,
    validate_blackout_sec,
    validate_utc_iso,
    validate_utc_ts,
)

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

TZ_NEW_YORK: str = "America/New_York"
TZ_PRAGUE: str = "Europe/Prague"
TZ_LONDON: str = "Europe/London"
TZ_ATHENS: str = "Europe/Athens"
TZ_ZURICH: str = "Europe/Zurich"
TZ_AUCKLAND: str = "Pacific/Auckland"


def _nth_weekday_of_month_raw(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _last_weekday_of_month_raw(year: int, month: int, weekday: int) -> date:
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


class _RuleBasedDstTzInfo(tzinfo):
    """Deterministic stdlib PEP-495 DST tzinfo fallback when `tzdata` is absent on Windows.

    Supports modern (2007+) statutory DST rules matching IANA `ZoneInfo` 100%:
      - `US`: 2nd Sun Mar 02:00 local -> 1st Sun Nov 02:00 local
      - `EU`: last Sun Mar 01:00 UTC -> last Sun Oct 01:00 UTC
      - `NZ`: last Sun Sep 02:00 NZST (Sat 14:00 UTC) -> 1st Sun Apr 03:00 NZDT (Sat 14:00 UTC)
    """

    def __init__(
        self,
        key: str,
        *,
        std_offset_hours: int,
        dst_delta_hours: int,
        std_name: str,
        dst_name: str,
        rule: str,
    ) -> None:
        self.key = key
        self._std_offset = timedelta(hours=std_offset_hours)
        self._dst_delta = timedelta(hours=dst_delta_hours)
        self._std_name = std_name
        self._dst_name = dst_name
        self._rule = rule

    def _is_dst_utc_naive(self, utc_naive: datetime) -> bool:
        yr = utc_naive.year
        if self._rule == "US":
            # Spring forward: 2nd Sunday in March at 02:00 local standard time
            start_utc = datetime.combine(_nth_weekday_of_month_raw(yr, 3, 6, 2), time(2, 0)) - self._std_offset
            # Fall back: 1st Sunday in November at 02:00 local daylight time
            end_utc = (
                datetime.combine(_nth_weekday_of_month_raw(yr, 11, 6, 1), time(2, 0))
                - self._std_offset
                - self._dst_delta
            )
            return start_utc <= utc_naive < end_utc
        if self._rule == "EU":
            # EU/UK statutory rule: last Sunday March 01:00 UTC -> last Sunday October 01:00 UTC
            start_utc = datetime.combine(_last_weekday_of_month_raw(yr, 3, 6), time(1, 0))
            end_utc = datetime.combine(_last_weekday_of_month_raw(yr, 10, 6), time(1, 0))
            return start_utc <= utc_naive < end_utc
        if self._rule == "NZ":
            # Southern Hemisphere (2007+): ends 1st Sun Apr 03:00 NZDT; starts last Sun Sep 02:00 NZST
            fall_utc = (
                datetime.combine(_nth_weekday_of_month_raw(yr, 4, 6, 1), time(3, 0))
                - self._std_offset
                - self._dst_delta
            )
            spring_utc = datetime.combine(_last_weekday_of_month_raw(yr, 9, 6), time(2, 0)) - self._std_offset
            return utc_naive < fall_utc or utc_naive >= spring_utc
        return False

    def _resolve_local_is_dst(self, dt: datetime) -> bool:
        loc = dt.replace(tzinfo=None)
        u_dst = loc - (self._std_offset + self._dst_delta)
        u_std = loc - self._std_offset
        valid_dst = self._is_dst_utc_naive(u_dst)
        valid_std = not self._is_dst_utc_naive(u_std)
        if valid_dst and not valid_std:
            return True
        if valid_std and not valid_dst:
            return False
        if valid_dst and valid_std:
            # Fall-back ambiguous hour: fold=0 is earlier (DST), fold=1 is later (STD)
            return dt.fold == 0
        # Spring-forward non-existent gap hour: fold=0 uses pre-transition (STD), fold=1 uses post-transition (DST)
        return dt.fold == 1

    def utcoffset(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        return self._std_offset + (self._dst_delta if self._resolve_local_is_dst(dt) else timedelta(0))

    def dst(self, dt: datetime | None) -> timedelta | None:
        if dt is None:
            return None
        return self._dst_delta if self._resolve_local_is_dst(dt) else timedelta(0)

    def tzname(self, dt: datetime | None) -> str | None:
        if dt is None:
            return self.key
        return self._dst_name if self._resolve_local_is_dst(dt) else self._std_name

    def fromutc(self, dt: datetime) -> datetime:
        if dt.tzinfo is not self:
            raise ValueError("fromutc: dt.tzinfo is not self")
        u = dt.replace(tzinfo=None)
        is_dst_now = self._is_dst_utc_naive(u)
        off = self._std_offset + (self._dst_delta if is_dst_now else timedelta(0))
        local_naive = u + off
        is_fold = (not is_dst_now) and self._is_dst_utc_naive(u - self._dst_delta)
        return local_naive.replace(tzinfo=self, fold=1 if is_fold else 0)

    def __repr__(self) -> str:
        return f"_RuleBasedDstTzInfo({self.key!r})"


_FALLBACK_TIMEZONES: dict[str, tzinfo] = {
    "UTC": UTC,
    "Etc/UTC": UTC,
    TZ_NEW_YORK: _RuleBasedDstTzInfo(
        TZ_NEW_YORK, std_offset_hours=-5, dst_delta_hours=1, std_name="EST", dst_name="EDT", rule="US"
    ),
    TZ_LONDON: _RuleBasedDstTzInfo(
        TZ_LONDON, std_offset_hours=0, dst_delta_hours=1, std_name="GMT", dst_name="BST", rule="EU"
    ),
    TZ_PRAGUE: _RuleBasedDstTzInfo(
        TZ_PRAGUE, std_offset_hours=1, dst_delta_hours=1, std_name="CET", dst_name="CEST", rule="EU"
    ),
    TZ_ZURICH: _RuleBasedDstTzInfo(
        TZ_ZURICH, std_offset_hours=1, dst_delta_hours=1, std_name="CET", dst_name="CEST", rule="EU"
    ),
    TZ_ATHENS: _RuleBasedDstTzInfo(
        TZ_ATHENS, std_offset_hours=2, dst_delta_hours=1, std_name="EET", dst_name="EEST", rule="EU"
    ),
    TZ_AUCKLAND: _RuleBasedDstTzInfo(
        TZ_AUCKLAND, std_offset_hours=12, dst_delta_hours=1, std_name="NZST", dst_name="NZDT", rule="NZ"
    ),
}

_TZ_CACHE: dict[str, tzinfo] = {}


def resolve_timezone(tz_name: str, *, prefer_fallback: bool = False) -> tzinfo:
    """Resolve an IANA timezone cleanly via `ZoneInfo`, with deterministic stdlib DST fallback.

    Guarantees `quant_factory.live_ops` imports and executes identically on Windows Python
    installations that lack the optional `tzdata` package, while failing closed on unknown zones.
    """
    if not isinstance(tz_name, str) or not tz_name.strip():
        raise ValueError(f"tz_name must be a non-empty string, got {tz_name!r}")
    norm = tz_name.strip()
    if prefer_fallback:
        fb = _FALLBACK_TIMEZONES.get(norm)
        if fb is None:
            raise ZoneInfoNotFoundError(
                f"No stdlib DST fallback defined for timezone {norm!r}; install 'tzdata' on Windows."
            )
        return fb
    cached = _TZ_CACHE.get(norm)
    if cached is not None:
        return cached
    try:
        tz: tzinfo = ZoneInfo(norm)
    except (ZoneInfoNotFoundError, ModuleNotFoundError) as exc:
        fb = _FALLBACK_TIMEZONES.get(norm)
        if fb is None:
            raise ZoneInfoNotFoundError(
                f"Timezone {norm!r} not found (install 'tzdata' on Windows for non-core zones)"
            ) from exc
        tz = fb
    _TZ_CACHE[norm] = tz
    return tz


_ZI_NEW_YORK: tzinfo = resolve_timezone(TZ_NEW_YORK)
_ZI_PRAGUE: tzinfo = resolve_timezone(TZ_PRAGUE)
_ZI_LONDON: tzinfo = resolve_timezone(TZ_LONDON)
_ZI_ATHENS: tzinfo = resolve_timezone(TZ_ATHENS)

EXTENDED_EVENT_CODES: frozenset[str] = frozenset(
    {"USD", "GBP", "EUR", "JPY", "AUD", "CAD", "CHF", "NZD", "EIA"}
)
ALLOWED_EXTENDED_VERIFICATION_STATUSES: frozenset[str] = frozenset(
    {"VERIFIED_T1", "DETERMINISTIC_PRIMARY_SCHEDULE_VERIFIED", "UNKNOWN_UNVERIFIED"}
)
EXTENDED_CALENDAR_SCHEMA: str = "naqex-red-news-extended-off3-8ccy-eia-v1"

TTL_AMBER_DAYS_DEFAULT: float = 14.0
TTL_RED_DAYS_DEFAULT: float = 3.0
DEFAULT_HARD_BAN_SEC: int = 135

_BROKER_SUFFIX_RE: re.Pattern[str] = re.compile(
    r"(?:\.(?:CASH|PRO|RAW|ECN|STD|MIC|MINI|A|B|C|M|I)|_[A-Z0-9]{1,4})$"
)

_OIL_TOKENS: tuple[str, ...] = ("USOIL", "UKOIL", "WTI", "BRENT", "XTIUSD", "XBRUSD", "USOUSD", "UKOUSD")
_JP_INDEX_TOKENS: tuple[str, ...] = ("JP225", "JPN225", "NIKKEI", "NI225", "J225")
_US_INDEX_TOKENS: tuple[str, ...] = ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "DJ30", "US2000")
_EU_INDEX_TOKENS: tuple[str, ...] = ("GER40", "GER30", "DE40", "DAX", "EU50", "STOXX50", "FRA40", "CAC40")
_UK_INDEX_TOKENS: tuple[str, ...] = ("UK100", "FTSE")
_AU_INDEX_TOKENS: tuple[str, ...] = ("AUS200", "ASX200")
_USD_METAL_CRYPTO_TOKENS: tuple[str, ...] = ("XAU", "XAG", "GOLD", "SILVER", "BTC", "ETH")
_EIGHT_CCYS: tuple[str, ...] = ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD")


@dataclass(frozen=True)
class DstSnapshot:
    """Point-in-time US vs EU DST state and broker/firm reset alignment."""

    utc_iso: str
    us_dst_active: bool
    eu_dst_active: bool
    is_dst_divergence_window: bool
    divergence_season: str
    ny_offset_hours: int
    ny_plus_7_offset_hours: int
    prague_offset_hours: int
    london_offset_hours: int
    athens_offset_hours: int
    ny_plus_7_vs_athens_delta_hours: int
    ny_plus_7_vs_prague_delta_hours: int
    london_vs_ny_delta_hours: int
    the5ers_reset_utc_hour: int
    ftmo_prague_reset_utc_hour: int
    ftmo_server_ny7_reset_utc_hour: int

    def to_dict(self) -> dict[str, Any]:
        """Serialize DST snapshot to JSON-compatible dict."""
        return {
            "utc_iso": self.utc_iso,
            "us_dst_active": self.us_dst_active,
            "eu_dst_active": self.eu_dst_active,
            "is_dst_divergence_window": self.is_dst_divergence_window,
            "divergence_season": self.divergence_season,
            "ny_offset_hours": self.ny_offset_hours,
            "ny_plus_7_offset_hours": self.ny_plus_7_offset_hours,
            "prague_offset_hours": self.prague_offset_hours,
            "london_offset_hours": self.london_offset_hours,
            "athens_offset_hours": self.athens_offset_hours,
            "ny_plus_7_vs_athens_delta_hours": self.ny_plus_7_vs_athens_delta_hours,
            "ny_plus_7_vs_prague_delta_hours": self.ny_plus_7_vs_prague_delta_hours,
            "london_vs_ny_delta_hours": self.london_vs_ny_delta_hours,
            "the5ers_reset_utc_hour": self.the5ers_reset_utc_hour,
            "ftmo_prague_reset_utc_hour": self.ftmo_prague_reset_utc_hour,
            "ftmo_server_ny7_reset_utc_hour": self.ftmo_server_ny7_reset_utc_hour,
        }


@dataclass(frozen=True)
class ExtendedRedNewsEvent:
    """Validated extended red-news event supporting 8 currencies + EIA."""

    utc_ts: int
    utc_iso: str
    utc_day: str
    ccy: str
    event: str
    blackout_sec: int = DEFAULT_BLACKOUT_SEC
    section: str = "live_2026_2027"
    source_agency: str | None = None
    source_url: str | None = None
    verification_status: str = "UNKNOWN_UNVERIFIED"
    confidence: str | None = None
    local_date: str | None = None
    local_time: str | None = None
    tz_name: str | None = None
    holiday_shifted: bool = False
    holiday_name: str | None = None

    @classmethod
    def from_red_news_event(cls, ev: RedNewsEvent, *, section: str = "base_6ccy") -> ExtendedRedNewsEvent:
        """Promote an immutable `quant_core.red_news.RedNewsEvent` without modifying it."""
        return cls(
            utc_ts=ev.utc_ts,
            utc_iso=ev.utc_iso,
            utc_day=ev.utc_day,
            ccy=ev.ccy,
            event=ev.event,
            blackout_sec=ev.blackout_sec,
            section=section,
            source_agency=ev.source_agency,
            source_url=ev.source_url,
            verification_status=ev.verification_status,
            confidence=ev.confidence,
            local_date=ev.local_date,
            local_time=ev.local_time,
            tz_name=ev.tz_name,
        )

    def to_dict(self) -> dict[str, Any]:
        """Serialize extended event to JSON-compatible dict."""
        return {
            "section": self.section,
            "local_date": self.local_date,
            "local_time": self.local_time,
            "tz_name": self.tz_name,
            "utc_ts": self.utc_ts,
            "utc_iso": self.utc_iso,
            "utc_day": self.utc_day,
            "ccy": self.ccy,
            "event": self.event,
            "blackout_sec": self.blackout_sec,
            "source_agency": self.source_agency,
            "source_url": self.source_url,
            "verification_status": self.verification_status,
            "confidence": self.confidence,
            "holiday_shifted": self.holiday_shifted,
            "holiday_name": self.holiday_name,
        }


@dataclass(frozen=True)
class CalendarTtlStatus:
    """Fail-closed calendar TTL expiry status (`GREEN > 14d`, `AMBER <= 14d`, `RED <= 3d`)."""

    status: str
    allow_new_entries: bool
    now_utc_iso: str
    overall_max_utc_iso: str | None
    min_remaining_days: float
    per_code_remaining_days: dict[str, float]
    per_code_status: dict[str, str]
    missing_codes: tuple[str, ...]
    expired_codes: tuple[str, ...]
    amber_codes: tuple[str, ...]
    red_codes: tuple[str, ...]
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class FeedHealthAssessment:
    """Fail-closed feed health assessment for stale-tick, freeze-quote, and spread spikes."""

    symbol: str
    status: str
    allow_trading: bool
    now_utc_iso: str
    tick_age_sec: float | None
    spread_points: float | None
    spread_ratio: float | None
    is_stale: bool
    is_frozen: bool
    is_spread_spike: bool
    is_invalid_quote: bool
    reasons: tuple[str, ...]


def _ensure_utc_datetime(dt: datetime, *, label: str = "utc_dt") -> datetime:
    if not isinstance(dt, datetime):
        raise ValueError(f"{label} must be a datetime, got {type(dt).__name__}")
    if dt.tzinfo is None or dt.utcoffset() is None:
        raise ValueError(f"{label} must be timezone-aware (UTC recommended), got naive datetime {dt!r}")
    return dt.astimezone(UTC)


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def _offset_hours(dt_utc: datetime, zi: tzinfo) -> int:
    off = dt_utc.astimezone(zi).utcoffset()
    if off is None:
        raise ValueError(f"Timezone {zi} returned None UTC offset")
    total_sec = int(off.total_seconds())
    if total_sec % 3600 != 0:
        raise ValueError(f"Expected whole-hour UTC offset for {zi}, got {total_sec}s")
    return total_sec // 3600


def is_us_dst(utc_dt: datetime) -> bool:
    """Return True when `America/New_York` observes Daylight Saving Time (EDT, UTC-4)."""
    dt_utc = _ensure_utc_datetime(utc_dt)
    dst_delta = dt_utc.astimezone(_ZI_NEW_YORK).dst()
    return dst_delta is not None and dst_delta.total_seconds() > 0


def is_eu_dst(utc_dt: datetime) -> bool:
    """Return True when EU/UK zones (`Europe/Prague`, `London`, `Athens`) observe summer time."""
    dt_utc = _ensure_utc_datetime(utc_dt)
    dst_delta = dt_utc.astimezone(_ZI_PRAGUE).dst()
    return dst_delta is not None and dst_delta.total_seconds() > 0


def ny_plus_7_offset_hours(utc_dt: datetime) -> int:
    """Return NY+7 broker server UTC offset (+3 in US EDT, +2 in US EST).

    Under the NY-close broker standard (FTMO/The5ers MT5 server clock), server midnight
    (00:00) ALWAYS coincides with 17:00 America/New_York (`offset = ny_offset + 7`).
    """
    dt_utc = _ensure_utc_datetime(utc_dt)
    return _offset_hours(dt_utc, _ZI_NEW_YORK) + 7


def get_dst_divergence_windows(year: int) -> dict[str, tuple[datetime, datetime]]:
    """Return exact UTC `(start, end)` boundaries of Spring & Fall US-vs-EU DST divergence."""
    if isinstance(year, bool) or not isinstance(year, int) or year < 2007 or year > 2100:
        raise ValueError(f"year must be an integer in [2007, 2100], got {year!r}")
    us_spring = datetime.combine(_nth_weekday_of_month(year, 3, 6, 2), time(7, 0), tzinfo=UTC)
    eu_spring = datetime.combine(_last_weekday_of_month(year, 3, 6), time(1, 0), tzinfo=UTC)
    eu_fall = datetime.combine(_last_weekday_of_month(year, 10, 6), time(1, 0), tzinfo=UTC)
    us_fall = datetime.combine(_nth_weekday_of_month(year, 11, 6, 1), time(6, 0), tzinfo=UTC)
    return {
        "spring": (us_spring, eu_spring),
        "fall": (eu_fall, us_fall),
    }


def resolve_dst_snapshot(utc_dt: datetime) -> DstSnapshot:
    """Resolve full US vs EU DST offsets, divergence state, and firm reset UTC hours."""
    dt_utc = _ensure_utc_datetime(utc_dt)
    us_dst = is_us_dst(dt_utc)
    eu_dst = is_eu_dst(dt_utc)

    ny_off = _offset_hours(dt_utc, _ZI_NEW_YORK)
    ny7_off = ny_off + 7
    prague_off = _offset_hours(dt_utc, _ZI_PRAGUE)
    london_off = _offset_hours(dt_utc, _ZI_LONDON)
    athens_off = _offset_hours(dt_utc, _ZI_ATHENS)

    diverged = us_dst != eu_dst
    if not diverged:
        season = "NONE"
    elif dt_utc.month <= 6:
        season = "SPRING_US_AHEAD_OF_EU"
    else:
        season = "FALL_EU_FELL_BACK_BEFORE_US"

    # 17:00 America/New_York in UTC: (17 - ny_off) % 24 -> 21 in EDT (-4), 22 in EST (-5)
    ny_close_utc_hour = (17 - ny_off) % 24
    # 00:00 Europe/Prague in UTC: (24 - prague_off) % 24 -> 22 in CEST (+2), 23 in CET (+1)
    prague_midnight_utc_hour = (24 - prague_off) % 24

    return DstSnapshot(
        utc_iso=dt_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
        us_dst_active=us_dst,
        eu_dst_active=eu_dst,
        is_dst_divergence_window=diverged,
        divergence_season=season,
        ny_offset_hours=ny_off,
        ny_plus_7_offset_hours=ny7_off,
        prague_offset_hours=prague_off,
        london_offset_hours=london_off,
        athens_offset_hours=athens_off,
        ny_plus_7_vs_athens_delta_hours=ny7_off - athens_off,
        ny_plus_7_vs_prague_delta_hours=ny7_off - prague_off,
        london_vs_ny_delta_hours=london_off - ny_off,
        the5ers_reset_utc_hour=ny_close_utc_hour,
        ftmo_prague_reset_utc_hour=prague_midnight_utc_hour,
        ftmo_server_ny7_reset_utc_hour=ny_close_utc_hour,
    )


def resolve_firm_daily_reset_utc(firm: str, utc_dt: datetime) -> dict[str, Any]:
    """Compute exact previous/next daily DD reset in UTC without confusing Athens with NY+7."""
    dt_utc = _ensure_utc_datetime(utc_dt)
    snap = resolve_dst_snapshot(dt_utc)
    firm_key = firm.strip().lower()

    if firm_key in {"the5ers", "the5ers_hs", "the5ers_hs_5k", "ny_close", "ny_plus_7"}:
        # Anchored strictly to 17:00 America/New_York (== 00:00 NY+7 server time)
        ny_local = dt_utc.astimezone(_ZI_NEW_YORK)
        today_17 = datetime.combine(ny_local.date(), time(17, 0), tzinfo=_ZI_NEW_YORK)
        if ny_local < today_17:
            next_reset_local = today_17
            prev_reset_local = datetime.combine(ny_local.date() - timedelta(days=1), time(17, 0), tzinfo=_ZI_NEW_YORK)
        else:
            prev_reset_local = today_17
            next_reset_local = datetime.combine(ny_local.date() + timedelta(days=1), time(17, 0), tzinfo=_ZI_NEW_YORK)
        prev_utc = prev_reset_local.astimezone(UTC)
        next_utc = next_reset_local.astimezone(UTC)
        return {
            "firm": firm_key,
            "anchor_rule": "17:00 America/New_York (00:00 NY+7 server midnight)",
            "anchor_tz": TZ_NEW_YORK,
            "prev_reset_utc_iso": prev_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "next_reset_utc_iso": next_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "seconds_to_next_reset": int((next_utc - dt_utc).total_seconds()),
            "reset_utc_hour": next_utc.hour,
            "athens_confusion_warning": snap.ny_plus_7_vs_athens_delta_hours != 0,
            "ny_plus_7_vs_athens_delta_hours": snap.ny_plus_7_vs_athens_delta_hours,
            "dst_snapshot": snap.to_dict(),
        }

    if firm_key in {"ftmo", "ftmo_standard", "ftmo_swing", "ftmo_prague", "prague"}:
        # FTMO daily DD resets at 00:00 Europe/Prague (CET/CEST), while MT5 server clock is NY+7!
        prague_local = dt_utc.astimezone(_ZI_PRAGUE)
        prev_local = datetime.combine(prague_local.date(), time(0, 0), tzinfo=_ZI_PRAGUE)
        next_local = datetime.combine(prague_local.date() + timedelta(days=1), time(0, 0), tzinfo=_ZI_PRAGUE)
        prev_utc = prev_local.astimezone(UTC)
        next_utc = next_local.astimezone(UTC)
        return {
            "firm": firm_key,
            "anchor_rule": "00:00 Europe/Prague (CET/CEST); MT5 server midnight is NY+7",
            "anchor_tz": TZ_PRAGUE,
            "prev_reset_utc_iso": prev_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "next_reset_utc_iso": next_utc.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "seconds_to_next_reset": int((next_utc - dt_utc).total_seconds()),
            "reset_utc_hour": next_utc.hour,
            "server_ny7_reset_utc_hour": snap.ftmo_server_ny7_reset_utc_hour,
            "server_vs_prague_delta_hours": snap.ny_plus_7_vs_prague_delta_hours,
            "athens_confusion_warning": snap.ny_plus_7_vs_athens_delta_hours != 0,
            "dst_snapshot": snap.to_dict(),
        }

    raise ValueError(f"Unsupported firm reset key: {firm!r}")


_STRATEGY_SESSION_ANCHORS: dict[str, tuple[str, str, int, int]] = {
    # strategy_id -> (anchor_tz, description, local_hour, local_minute)
    "F03": (TZ_LONDON, "London Open session anchor (08:00 Europe/London)", 8, 0),
    "F04": (TZ_NEW_YORK, "US Cash Open / NY morning session anchor (09:30 America/New_York)", 9, 30),
    "F05": (TZ_NEW_YORK, "NY 10:00 ET risk-flow anchor (10:00 America/New_York)", 10, 0),
    "F09": (TZ_NEW_YORK, "NY close / rollover boundary anchor (17:00 America/New_York)", 17, 0),
    "LONDON_OPEN": (TZ_LONDON, "London Open (08:00 Europe/London)", 8, 0),
    "NY_OPEN": (TZ_NEW_YORK, "US Equity Cash Open (09:30 America/New_York)", 9, 30),
    "NY_10ET": (TZ_NEW_YORK, "NY 10:00 ET Fix/Flow (10:00 America/New_York)", 10, 0),
    "NY_CLOSE": (TZ_NEW_YORK, "NY 17:00 ET Close / NY+7 Midnight (17:00 America/New_York)", 17, 0),
}


def resolve_strategy_session_utc(strategy_id: str, trade_date: date) -> dict[str, Any]:
    """Resolve exact UTC session timestamp for DST-sensitive strategies (`F03/F04/F05/F09`)."""
    if not isinstance(trade_date, date) or isinstance(trade_date, datetime):
        raise ValueError(f"trade_date must be a datetime.date, got {type(trade_date).__name__}")
    key = strategy_id.strip().upper()
    if key not in _STRATEGY_SESSION_ANCHORS:
        raise ValueError(f"Unknown strategy_id {strategy_id!r}; supported={sorted(_STRATEGY_SESSION_ANCHORS)}")
    tz_name, desc, hour, minute = _STRATEGY_SESSION_ANCHORS[key]
    zi = resolve_timezone(tz_name)
    local_dt = datetime.combine(trade_date, time(hour, minute), tzinfo=zi)
    utc_dt = local_dt.astimezone(UTC)
    snap = resolve_dst_snapshot(utc_dt)
    ny7_dt = utc_dt + timedelta(hours=snap.ny_plus_7_offset_hours)
    return {
        "strategy_id": key,
        "description": desc,
        "anchor_tz": tz_name,
        "local_iso": local_dt.isoformat(),
        "utc_iso": utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "utc_hour": utc_dt.hour,
        "utc_minute": utc_dt.minute,
        "ny_plus_7_server_time": ny7_dt.strftime("%Y-%m-%d %H:%M"),
        "is_dst_divergence_window": snap.is_dst_divergence_window,
        "london_vs_ny_delta_hours": snap.london_vs_ny_delta_hours,
        "ny_plus_7_vs_athens_delta_hours": snap.ny_plus_7_vs_athens_delta_hours,
    }


def _observed_fixed_us_holiday(year: int, month: int, day: int) -> date:
    raw = date(year, month, day)
    if raw.weekday() == 5:  # Saturday -> Friday
        return raw - timedelta(days=1)
    if raw.weekday() == 6:  # Sunday -> Monday
        return raw + timedelta(days=1)
    return raw


def us_federal_holidays_observed(year: int) -> dict[date, str]:
    """Return OPM observed U.S. Federal Holidays for `year` (including Juneteenth from 2021)."""
    if isinstance(year, bool) or not isinstance(year, int) or year < 2000 or year > 2100:
        raise ValueError(f"year must be an integer in [2000, 2100], got {year!r}")
    holidays: dict[date, str] = {}

    nyd = _observed_fixed_us_holiday(year, 1, 1)
    if nyd.year == year:
        holidays[nyd] = "New Year's Day"
    next_nyd = _observed_fixed_us_holiday(year + 1, 1, 1)
    if next_nyd.year == year:
        holidays[next_nyd] = "New Year's Day (Observed)"

    holidays[_nth_weekday_of_month(year, 1, 0, 3)] = "Martin Luther King Jr. Day"
    holidays[_nth_weekday_of_month(year, 2, 0, 3)] = "Presidents' Day"
    holidays[_last_weekday_of_month(year, 5, 0)] = "Memorial Day"
    if year >= 2021:
        holidays[_observed_fixed_us_holiday(year, 6, 19)] = "Juneteenth National Independence Day"
    holidays[_observed_fixed_us_holiday(year, 7, 4)] = "Independence Day"
    holidays[_nth_weekday_of_month(year, 9, 0, 1)] = "Labor Day"
    holidays[_nth_weekday_of_month(year, 10, 0, 2)] = "Columbus Day"
    holidays[_observed_fixed_us_holiday(year, 11, 11)] = "Veterans Day"
    holidays[_nth_weekday_of_month(year, 11, 3, 4)] = "Thanksgiving Day"
    holidays[_observed_fixed_us_holiday(year, 12, 25)] = "Christmas Day"
    return dict(sorted(holidays.items()))


def resolve_eia_wpsr_release(
    wednesday_date: date,
    *,
    holiday_time_et: str | None = None,
) -> tuple[date, str, bool, str | None]:
    """Resolve EIA Weekly Petroleum Status Report release date & local ET time for a week.

    Primary schedule rule (`eia.gov/petroleum/supply/weekly/schedule.php`):
      - Standard weeks: Wednesday at `10:30` `America/New_York`.
      - Weeks with a U.S. Federal Holiday observed on Monday, Tuesday, or Wednesday:
        shifted to Thursday.
        * 2018-2024 historical regime: Thursday `11:00` ET (default for `year <= 2024`).
        * 2025+ published `eia.gov` regime: Thursday `12:00` ET (default for `year >= 2025`).
    """
    if not isinstance(wednesday_date, date) or isinstance(wednesday_date, datetime):
        raise ValueError(f"wednesday_date must be a datetime.date, got {type(wednesday_date).__name__}")
    if wednesday_date.weekday() != 2:
        raise ValueError(f"wednesday_date must be a Wednesday (weekday=2), got {wednesday_date.isoformat()}")

    mon = wednesday_date - timedelta(days=2)
    tue = wednesday_date - timedelta(days=1)
    years_to_check = {mon.year, tue.year, wednesday_date.year}
    hol_map: dict[date, str] = {}
    for yr in years_to_check:
        hol_map.update(us_federal_holidays_observed(yr))

    matched_holiday: str | None = None
    for check_day in (mon, tue, wednesday_date):
        if check_day in hol_map:
            matched_holiday = hol_map[check_day]
            break

    if matched_holiday is None:
        return wednesday_date, "10:30", False, None

    release_date = wednesday_date + timedelta(days=1)
    eff_time = holiday_time_et if holiday_time_et is not None else ("11:00" if release_date.year <= 2024 else "12:00")
    return release_date, eff_time, True, matched_holiday


def _validate_extended_code(ccy: Any) -> str:
    if not isinstance(ccy, str):
        raise ValueError(f"Event code must be a string, got {type(ccy).__name__}")
    norm = ccy.strip().upper()
    if norm not in EXTENDED_EVENT_CODES:
        raise ValueError(f"Unsupported extended event code {ccy!r}; allowed={sorted(EXTENDED_EVENT_CODES)}")
    return norm


def _validate_http_url(url: str | None, *, status: str) -> str:
    if not isinstance(url, str):
        raise ValueError(f"{status} event requires valid http(s) source_url, got {url!r}")
    norm = url.strip()
    if not norm or any(ch.isspace() for ch in norm):
        raise ValueError(f"{status} event requires valid http(s) source_url, got {url!r}")
    parsed = urlparse(norm)
    host = parsed.hostname or ""
    if parsed.scheme not in ("https", "http") or not parsed.netloc or "." not in host:
        raise ValueError(f"{status} event requires http(s) source_url with valid host, got {url!r}")
    return norm


def _validate_extended_verification_status(
    status: Any,
    *,
    source_agency: str | None,
    source_url: str | None,
) -> str:
    if not isinstance(status, str):
        raise ValueError(f"verification_status must be a string, got {status!r}")
    norm = status.strip()
    if norm not in ALLOWED_EXTENDED_VERIFICATION_STATUSES:
        raise ValueError(
            f"Unsupported verification_status {status!r}; allowed={sorted(ALLOWED_EXTENDED_VERIFICATION_STATUSES)}"
        )
    if norm in ("VERIFIED_T1", "DETERMINISTIC_PRIMARY_SCHEDULE_VERIFIED"):
        if not source_agency or not source_agency.strip():
            raise ValueError(f"{norm} event requires non-empty source_agency")
        _validate_http_url(source_url, status=norm)
    return norm


def _optional_str(val: Any) -> str | None:
    if val is None:
        return None
    if not isinstance(val, str):
        raise ValueError(f"Expected optional string, got {type(val).__name__}")
    s = val.strip()
    return s or None


def _parse_extended_event(item: Any, *, expected_section: str) -> ExtendedRedNewsEvent:
    if not isinstance(item, dict):
        raise ValueError(f"Extended calendar entry must be a dict, got {type(item).__name__}")

    ccy = _validate_extended_code(item.get("ccy"))
    raw_iso = item.get("utc_iso")
    raw_ts = item.get("utc_ts")
    if raw_iso is not None:
        utc_ts, utc_iso, utc_day = validate_utc_iso(raw_iso, expected_ts=raw_ts)
    elif raw_ts is not None:
        utc_ts, utc_iso, utc_day = validate_utc_ts(raw_ts)
    else:
        raise ValueError("Extended calendar event must provide 'utc_iso' and/or 'utc_ts'")

    dt_utc = datetime.fromtimestamp(utc_ts, tz=UTC)
    if dt_utc.weekday() >= 5:
        raise ValueError(f"Extended calendar event falls on UTC weekend: {utc_iso} ({ccy})")

    section = _optional_str(item.get("section")) or expected_section
    if section != expected_section:
        raise ValueError(f"Event section mismatch: got {section!r}, expected {expected_section!r}")
    if expected_section == "dev_2018_2024" and not (2018 <= dt_utc.year <= 2024):
        raise ValueError(f"dev_2018_2024 event outside 2018-2024 window: {utc_iso}")
    if expected_section == "live_2026_2027" and dt_utc.year not in (2026, 2027):
        raise ValueError(f"live_2026_2027 event outside 2026-2027 window: {utc_iso}")
    if dt_utc.year == 2025:
        raise ValueError(f"Holdout year 2025 forbidden in additive Dev/Live calendar: {utc_iso}")

    local_date = _optional_str(item.get("local_date"))
    local_time = _optional_str(item.get("local_time"))
    tz_name = _optional_str(item.get("tz_name"))
    if local_date and local_time and tz_name:
        local_dt = datetime.strptime(f"{local_date} {local_time}", "%Y-%m-%d %H:%M").replace(
            tzinfo=resolve_timezone(tz_name)
        )
        calc_ts = int(local_dt.astimezone(UTC).timestamp())
        if calc_ts != utc_ts:
            raise ValueError(
                f"Local time {local_date} {local_time} {tz_name} resolves to ts={calc_ts}, != stored utc_ts={utc_ts}"
            )

    raw_event = item.get("event")
    if not isinstance(raw_event, str) or not raw_event.strip():
        raise ValueError(f"Invalid event label: {raw_event!r}")
    event_label = raw_event.strip()

    raw_blackout = item.get("blackout_sec", DEFAULT_BLACKOUT_SEC)
    blackout_sec = validate_blackout_sec(raw_blackout)
    if blackout_sec > MAX_BLACKOUT_SEC:
        raise ValueError(f"blackout_sec exceeds MAX_BLACKOUT_SEC: {blackout_sec}")

    source_agency = _optional_str(item.get("source_agency"))
    source_url = _optional_str(item.get("source_url"))
    verif = _validate_extended_verification_status(
        item.get("verification_status", "UNKNOWN_UNVERIFIED"),
        source_agency=source_agency,
        source_url=source_url,
    )

    holiday_shifted = bool(item.get("holiday_shifted", False))
    holiday_name = _optional_str(item.get("holiday_name"))

    return ExtendedRedNewsEvent(
        utc_ts=utc_ts,
        utc_iso=utc_iso,
        utc_day=utc_day,
        ccy=ccy,
        event=event_label,
        blackout_sec=blackout_sec,
        section=section,
        source_agency=source_agency,
        source_url=source_url,
        verification_status=verif,
        confidence=_optional_str(item.get("confidence")),
        local_date=local_date,
        local_time=local_time,
        tz_name=tz_name,
        holiday_shifted=holiday_shifted,
        holiday_name=holiday_name,
    )


def load_extended_calendar(
    path: str | Path,
    *,
    sections: Sequence[str] | None = None,
) -> list[ExtendedRedNewsEvent]:
    """Fail-closed loader for `red_news_extended_off3_8ccy_eia.json`."""
    cal_path = Path(path)
    if not cal_path.exists():
        raise FileNotFoundError(f"Extended red-news calendar not found: {cal_path}")

    raw = json.loads(cal_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Extended calendar root must be an object in {cal_path}")
    if raw.get("schema") != EXTENDED_CALENDAR_SCHEMA:
        raise ValueError(f"Unexpected extended calendar schema in {cal_path}: {raw.get('schema')!r}")

    raw_sections = raw.get("sections")
    if not isinstance(raw_sections, dict) or not raw_sections:
        raise ValueError(f"Missing or empty 'sections' object in {cal_path}")

    target_sections = list(sections) if sections is not None else ["dev_2018_2024", "live_2026_2027"]
    if not target_sections:
        raise ValueError("sections filter must not be empty")

    events: list[ExtendedRedNewsEvent] = []
    seen_keys: set[tuple[int, str, str]] = set()
    for sec_name in target_sections:
        sec_obj = raw_sections.get(sec_name)
        if not isinstance(sec_obj, dict):
            raise ValueError(f"Missing required section {sec_name!r} in {cal_path}")
        sec_events = sec_obj.get("events")
        if not isinstance(sec_events, list) or not sec_events:
            raise ValueError(f"Empty or invalid events list in section {sec_name!r} of {cal_path}")
        for idx, item in enumerate(sec_events):
            try:
                ev = _parse_extended_event(item, expected_section=sec_name)
            except ValueError as exc:
                raise ValueError(f"{cal_path}: sections.{sec_name}.events[{idx}]: {exc}") from exc
            dedup_key = (ev.utc_ts, ev.ccy, ev.event)
            if dedup_key in seen_keys:
                raise ValueError(f"Duplicate extended calendar event in {cal_path}: {dedup_key}")
            seen_keys.add(dedup_key)
            events.append(ev)

    if not events:
        raise ValueError(f"Extended red-news calendar yielded 0 events: {cal_path}")
    events.sort(key=lambda e: (e.utc_ts, e.ccy, e.event))
    return events


def load_merged_live_calendar(
    base_calendar_path: str | Path,
    extended_calendar_path: str | Path,
    *,
    include_extended_sections: Sequence[str] = ("live_2026_2027",),
) -> list[ExtendedRedNewsEvent]:
    """Read-only merge of immutable 6-CCY calendar + additive 8-CCY+EIA calendar."""
    base_events = [
        ExtendedRedNewsEvent.from_red_news_event(ev, section="base_6ccy")
        for ev in load_calendar_events(base_calendar_path)
    ]
    ext_events = load_extended_calendar(extended_calendar_path, sections=include_extended_sections)
    combined: list[ExtendedRedNewsEvent] = []
    seen: set[tuple[int, str, str]] = set()
    for ev in (*base_events, *ext_events):
        key = (ev.utc_ts, ev.ccy, ev.event)
        if key not in seen:
            seen.add(key)
            combined.append(ev)
    combined.sort(key=lambda e: (e.utc_ts, e.ccy, e.event))
    return combined


def _normalize_symbol(symbol: str) -> str:
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(f"symbol must be a non-empty string, got {symbol!r}")
    norm = symbol.strip().upper()
    norm = _BROKER_SUFFIX_RE.sub("", norm)
    return norm


def match_symbol_event_codes(symbol: str) -> frozenset[str]:
    """Map any trading symbol to the set of red-news event codes that govern it.

    Explicitly fixes blind spots on:
      - `USOIL` / `UKOIL` / `WTI` / `BRENT` -> `{"EIA", "USD"}`
      - `JP225` / `NIKKEI` -> `{"JPY", "USD"}`
      - `XAGUSD` / `XAUUSD` -> `{"USD"}` (plus any matched currency like EUR in XAUEUR)
      - All `CHF` and `NZD` FX crosses -> exact 2 currencies
    """
    u = _normalize_symbol(symbol)
    codes: set[str] = set()

    if any(tok in u for tok in _OIL_TOKENS):
        codes.update({"EIA", "USD"})
    if any(tok in u for tok in _JP_INDEX_TOKENS):
        codes.update({"JPY", "USD"})
    if any(tok in u for tok in _US_INDEX_TOKENS):
        codes.add("USD")
    if any(tok in u for tok in _EU_INDEX_TOKENS):
        codes.add("EUR")
    if any(tok in u for tok in _UK_INDEX_TOKENS):
        codes.add("GBP")
    if any(tok in u for tok in _AU_INDEX_TOKENS):
        codes.add("AUD")
    if any(tok in u for tok in _USD_METAL_CRYPTO_TOKENS):
        codes.add("USD")

    for ccy in _EIGHT_CCYS:
        if ccy in u:
            codes.add(ccy)

    return frozenset(codes)


def symbol_matches_event_code(symbol: str, event_code: str) -> bool:
    """Return True if `event_code` (currency or `EIA`/`ALL`) impacts `symbol`."""
    if not isinstance(event_code, str):
        raise ValueError(f"event_code must be a string, got {type(event_code).__name__}")
    code = event_code.strip().upper()
    if code in ("", "ALL"):
        return True
    return code in match_symbol_event_codes(symbol)


def _validate_ttl_thresholds(amber_days: float, red_days: float) -> tuple[float, float]:
    if (
        isinstance(amber_days, bool)
        or isinstance(red_days, bool)
        or not isinstance(amber_days, (int, float))
        or not isinstance(red_days, (int, float))
    ):
        raise ValueError("amber_days and red_days must be finite positive numbers")
    a = float(amber_days)
    r = float(red_days)
    if not (math.isfinite(a) and math.isfinite(r)) or r < 0.0 or a <= r:
        raise ValueError(f"Invalid TTL thresholds: require amber_days ({a}) > red_days ({r}) >= 0")
    return a, r


def check_calendar_ttl(
    events: Sequence[ExtendedRedNewsEvent | RedNewsEvent],
    *,
    now_utc: datetime,
    required_codes: Sequence[str] | None = None,
    symbol: str | None = None,
    amber_days: float = TTL_AMBER_DAYS_DEFAULT,
    red_days: float = TTL_RED_DAYS_DEFAULT,
) -> CalendarTtlStatus:
    """Fail-closed calendar TTL expiry guard (`GREEN > 14d`, `AMBER <= 14d`, `RED <= 3d`)."""
    dt_now = _ensure_utc_datetime(now_utc, label="now_utc")
    now_ts = dt_now.timestamp()
    now_iso = dt_now.strftime("%Y-%m-%dT%H:%M:%SZ")
    amber_lim, red_lim = _validate_ttl_thresholds(amber_days, red_days)

    req_set: set[str] = set()
    if required_codes is not None:
        for code in required_codes:
            req_set.add(_validate_extended_code(code))
    if symbol is not None:
        sym_codes = match_symbol_event_codes(symbol)
        if not sym_codes:
            raise ValueError(f"Unable to map symbol {symbol!r} to any event codes")
        req_set.update(sym_codes)

    if not events:
        missing = tuple(sorted(req_set))
        return CalendarTtlStatus(
            status="RED",
            allow_new_entries=False,
            now_utc_iso=now_iso,
            overall_max_utc_iso=None,
            min_remaining_days=-math.inf,
            per_code_remaining_days={},
            per_code_status={c: "RED" for c in missing},
            missing_codes=missing,
            expired_codes=missing,
            amber_codes=(),
            red_codes=missing,
            reasons=("EMPTY_CALENDAR_FAIL_CLOSED",),
        )

    max_ts_by_code: dict[str, int] = {}
    overall_max_ts = 0
    for ev in events:
        code = ev.ccy.strip().upper()
        ts = int(ev.utc_ts)
        if ts > overall_max_ts:
            overall_max_ts = ts
        if ts > max_ts_by_code.get(code, 0):
            max_ts_by_code[code] = ts

    codes_to_eval = sorted(req_set) if req_set else sorted(max_ts_by_code.keys())
    per_code_days: dict[str, float] = {}
    per_code_status: dict[str, str] = {}
    missing_codes: list[str] = []
    expired_codes: list[str] = []
    amber_codes: list[str] = []
    red_codes: list[str] = []
    reasons: list[str] = []

    for code in codes_to_eval:
        max_ts = max_ts_by_code.get(code)
        if max_ts is None:
            missing_codes.append(code)
            expired_codes.append(code)
            red_codes.append(code)
            per_code_days[code] = -math.inf
            per_code_status[code] = "RED"
            reasons.append(f"MISSING_REQUIRED_EVENT_CODE:{code}")
            continue

        rem_days = round((float(max_ts) - now_ts) / 86400.0, 6)
        per_code_days[code] = rem_days
        if rem_days <= 0.0:
            expired_codes.append(code)
            red_codes.append(code)
            per_code_status[code] = "RED"
            reasons.append(f"CALENDAR_EXPIRED:{code}:{rem_days:.2f}d")
        elif rem_days <= red_lim:
            red_codes.append(code)
            per_code_status[code] = "RED"
            reasons.append(f"CALENDAR_TTL_RED:{code}:{rem_days:.2f}d<={red_lim:.1f}d")
        elif rem_days <= amber_lim:
            amber_codes.append(code)
            per_code_status[code] = "AMBER"
            reasons.append(f"CALENDAR_TTL_AMBER:{code}:{rem_days:.2f}d<={amber_lim:.1f}d")
        else:
            per_code_status[code] = "GREEN"

    min_rem = min(per_code_days.values()) if per_code_days else -math.inf
    overall_max_iso = (
        datetime.fromtimestamp(overall_max_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ") if overall_max_ts > 0 else None
    )

    if red_codes:
        overall_status = "RED"
        allow = False
    elif amber_codes:
        overall_status = "AMBER"
        allow = True
    else:
        overall_status = "GREEN"
        allow = True

    return CalendarTtlStatus(
        status=overall_status,
        allow_new_entries=allow,
        now_utc_iso=now_iso,
        overall_max_utc_iso=overall_max_iso,
        min_remaining_days=min_rem,
        per_code_remaining_days=per_code_days,
        per_code_status=per_code_status,
        missing_codes=tuple(missing_codes),
        expired_codes=tuple(expired_codes),
        amber_codes=tuple(amber_codes),
        red_codes=tuple(red_codes),
        reasons=tuple(reasons),
    )


def is_in_red_news_window(
    symbol: str,
    utc_dt: datetime,
    events: Sequence[ExtendedRedNewsEvent | RedNewsEvent],
    *,
    default_pad_sec: int = DEFAULT_BLACKOUT_SEC,
    hard_ban_sec: int = DEFAULT_HARD_BAN_SEC,
    enforce_ttl_fail_closed: bool = True,
    amber_days: float = TTL_AMBER_DAYS_DEFAULT,
    red_days: float = TTL_RED_DAYS_DEFAULT,
) -> dict[str, Any]:
    """Evaluate extended red-news block, pre-flatten, and hard-ban windows for `symbol`."""
    dt_utc = _ensure_utc_datetime(utc_dt)
    now_ts = int(dt_utc.timestamp())
    pad_sec = validate_blackout_sec(default_pad_sec)
    ban_sec = validate_blackout_sec(hard_ban_sec)

    sym_codes = match_symbol_event_codes(symbol)
    ttl = check_calendar_ttl(
        events,
        now_utc=dt_utc,
        symbol=symbol,
        amber_days=amber_days,
        red_days=red_days,
    )

    if enforce_ttl_fail_closed and not ttl.allow_new_entries:
        return {
            "symbol": symbol,
            "matched_event_codes": sorted(sym_codes),
            "in_block_window": True,
            "in_hard_ban_window": False,
            "in_pre_flatten_window": False,
            "fail_closed_ttl_block": True,
            "ttl_status": ttl.status,
            "ttl_reasons": list(ttl.reasons),
            "active_events": [],
        }

    in_block = False
    in_hard_ban = False
    in_pre_flatten_candidate = False
    active_events: list[dict[str, Any]] = []

    for ev in events:
        if not symbol_matches_event_code(symbol, ev.ccy):
            continue
        eff_pad = max(pad_sec, int(ev.blackout_sec))
        diff = int(ev.utc_ts) - now_ts
        if abs(diff) <= eff_pad:
            in_block = True
            active_events.append(
                {
                    "utc_iso": ev.utc_iso,
                    "ccy": ev.ccy,
                    "event": ev.event,
                    "seconds_to_event": diff,
                    "effective_pad_sec": eff_pad,
                }
            )
        if abs(diff) <= ban_sec:
            in_hard_ban = True
        elif ban_sec < diff <= eff_pad:
            in_pre_flatten_candidate = True

    return {
        "symbol": symbol,
        "matched_event_codes": sorted(sym_codes),
        "in_block_window": in_block,
        "in_hard_ban_window": in_hard_ban,
        "in_pre_flatten_window": (in_pre_flatten_candidate and not in_hard_ban),
        "fail_closed_ttl_block": False,
        "ttl_status": ttl.status,
        "ttl_reasons": list(ttl.reasons),
        "active_events": active_events,
    }


def evaluate_feed_health(
    *,
    symbol: str,
    now_utc: datetime,
    last_tick_utc: datetime | None,
    bid: float,
    ask: float,
    point_size: float | None = None,
    median_spread_points: float | None = None,
    recent_mids: Sequence[float] | None = None,
    recent_tick_timestamps_utc: Sequence[datetime] | None = None,
    max_stale_sec: float = 30.0,
    amber_stale_ratio: float = 0.5,
    max_freeze_identical_ticks: int = 20,
    freeze_min_span_sec: float = 30.0,
    max_spread_multiplier: float = 4.0,
    amber_spread_multiplier: float = 2.5,
    hard_max_spread_points: float | None = None,
    is_market_open: bool = True,
) -> FeedHealthAssessment:
    """Detect stale ticks, frozen quotes, invalid quotes, and synthetic spread spikes."""
    dt_now = _ensure_utc_datetime(now_utc, label="now_utc")
    now_iso = dt_now.strftime("%Y-%m-%dT%H:%M:%SZ")
    sym_norm = _normalize_symbol(symbol)

    if not is_market_open:
        return FeedHealthAssessment(
            symbol=sym_norm,
            status="MARKET_CLOSED",
            allow_trading=False,
            now_utc_iso=now_iso,
            tick_age_sec=None,
            spread_points=None,
            spread_ratio=None,
            is_stale=False,
            is_frozen=False,
            is_spread_spike=False,
            is_invalid_quote=False,
            reasons=("MARKET_CLOSED",),
        )

    reasons: list[str] = []
    red_hit = False
    amber_hit = False
    is_stale = False
    is_frozen = False
    is_spread_spike = False
    is_invalid_quote = False

    # 1. Quote integrity check (strictly fail-closed on NaN/Inf/<=0/inverted spread)
    if (
        isinstance(bid, bool)
        or isinstance(ask, bool)
        or not isinstance(bid, (int, float))
        or not isinstance(ask, (int, float))
        or not math.isfinite(float(bid))
        or not math.isfinite(float(ask))
        or float(bid) <= 0.0
        or float(ask) <= 0.0
        or float(ask) < float(bid)
    ):
        is_invalid_quote = True
        red_hit = True
        reasons.append(f"INVALID_QUOTE:bid={bid!r},ask={ask!r}")

    # 2. Stale-tick / clock-skew check
    tick_age_sec: float | None = None
    if last_tick_utc is None:
        is_stale = True
        red_hit = True
        reasons.append("MISSING_LAST_TICK_UTC")
    else:
        dt_tick = _ensure_utc_datetime(last_tick_utc, label="last_tick_utc")
        tick_age_sec = round((dt_now - dt_tick).total_seconds(), 3)
        if tick_age_sec < -5.0:
            is_stale = True
            red_hit = True
            reasons.append(f"CLOCK_SKEW_FUTURE_TICK:{tick_age_sec:.2f}s")
        elif tick_age_sec > float(max_stale_sec):
            is_stale = True
            red_hit = True
            reasons.append(f"STALE_TICK:{tick_age_sec:.2f}s>{max_stale_sec:.1f}s")
        elif tick_age_sec > float(max_stale_sec) * float(amber_stale_ratio):
            amber_hit = True
            reasons.append(f"AGING_TICK:{tick_age_sec:.2f}s")

    # 3. Freeze-quote detector (identical consecutive mids spanning >= freeze_min_span_sec)
    if recent_mids is not None and len(recent_mids) >= max_freeze_identical_ticks:
        tail_mids = [float(x) for x in recent_mids[-max_freeze_identical_ticks:]]
        if any(not math.isfinite(x) or x <= 0.0 for x in tail_mids):
            is_invalid_quote = True
            red_hit = True
            reasons.append("INVALID_RECENT_MID_VALUES")
        else:
            ref_mid = tail_mids[0]
            all_identical = all(abs(x - ref_mid) <= 1e-12 for x in tail_mids)
            if all_identical:
                span_ok = True
                span_sec: float | None = None
                if (
                    recent_tick_timestamps_utc is not None
                    and len(recent_tick_timestamps_utc) >= max_freeze_identical_ticks
                ):
                    t_start = _ensure_utc_datetime(
                        recent_tick_timestamps_utc[-max_freeze_identical_ticks],
                        label="recent_tick_timestamps_utc[start]",
                    )
                    t_end = _ensure_utc_datetime(
                        recent_tick_timestamps_utc[-1],
                        label="recent_tick_timestamps_utc[end]",
                    )
                    span_sec = (t_end - t_start).total_seconds()
                    span_ok = span_sec >= float(freeze_min_span_sec)
                if span_ok:
                    is_frozen = True
                    red_hit = True
                    span_lbl = f"{span_sec:.1f}s" if span_sec is not None else "unbounded"
                    reasons.append(f"FREEZE_QUOTE:{max_freeze_identical_ticks}_identical_ticks_over_{span_lbl}")

    # 4. Synthetic spread spike & hard spread cap check
    spread_points: float | None = None
    spread_ratio: float | None = None
    if not is_invalid_quote and point_size is not None:
        if (
            isinstance(point_size, bool)
            or not isinstance(point_size, (int, float))
            or not math.isfinite(float(point_size))
            or float(point_size) <= 0.0
        ):
            is_invalid_quote = True
            red_hit = True
            reasons.append(f"INVALID_POINT_SIZE:{point_size!r}")
        else:
            spread_points = round((float(ask) - float(bid)) / float(point_size), 3)
            if hard_max_spread_points is not None and spread_points > float(hard_max_spread_points):
                is_spread_spike = True
                red_hit = True
                reasons.append(f"SPREAD_CAP_BREACH:{spread_points:.1f}>{hard_max_spread_points:.1f}pts")
            if median_spread_points is not None and float(median_spread_points) > 0.0:
                spread_ratio = round(spread_points / float(median_spread_points), 3)
                if spread_ratio >= float(max_spread_multiplier):
                    is_spread_spike = True
                    red_hit = True
                    reasons.append(
                        f"SYNTHETIC_SPREAD_SPIKE:{spread_points:.1f}pts={spread_ratio:.2f}x_median>={max_spread_multiplier:.1f}x"
                    )
                elif spread_ratio >= float(amber_spread_multiplier):
                    amber_hit = True
                    reasons.append(f"ELEVATED_SPREAD:{spread_points:.1f}pts={spread_ratio:.2f}x_median")

    if red_hit:
        status = "RED"
        allow = False
    elif amber_hit:
        status = "AMBER"
        allow = True
    else:
        status = "GREEN"
        allow = True

    return FeedHealthAssessment(
        symbol=sym_norm,
        status=status,
        allow_trading=allow,
        now_utc_iso=now_iso,
        tick_age_sec=tick_age_sec,
        spread_points=spread_points,
        spread_ratio=spread_ratio,
        is_stale=is_stale,
        is_frozen=is_frozen,
        is_spread_spike=is_spread_spike,
        is_invalid_quote=is_invalid_quote,
        reasons=tuple(reasons),
    )
