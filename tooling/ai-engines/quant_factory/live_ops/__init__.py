"""Naqex Live-Ops Guards & Diagnostics Package (strictly offline/fail-closed).

Safety boundaries:
  - ORDER_SEND_CAPABLE = False
  - ORDER_SEND_COUNT = 0
  - Zero MetaTrader5 imports; zero SSH or broker mutations.
  - Zero bare `assert` statements ([ARCH-02]).
"""

from __future__ import annotations

from quant_factory.live_ops.feed_dst_news_guard import (
    ALLOWED_EXTENDED_VERIFICATION_STATUSES,
    EXTENDED_EVENT_CODES,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    TTL_AMBER_DAYS_DEFAULT,
    TTL_RED_DAYS_DEFAULT,
    TZ_ATHENS,
    TZ_AUCKLAND,
    TZ_LONDON,
    TZ_NEW_YORK,
    TZ_PRAGUE,
    TZ_ZURICH,
    CalendarTtlStatus,
    DstSnapshot,
    ExtendedRedNewsEvent,
    FeedHealthAssessment,
    check_calendar_ttl,
    evaluate_feed_health,
    get_dst_divergence_windows,
    is_eu_dst,
    is_in_red_news_window,
    is_us_dst,
    load_extended_calendar,
    load_merged_live_calendar,
    match_symbol_event_codes,
    ny_plus_7_offset_hours,
    resolve_dst_snapshot,
    resolve_eia_wpsr_release,
    resolve_firm_daily_reset_utc,
    resolve_strategy_session_utc,
    resolve_timezone,
    symbol_matches_event_code,
    us_federal_holidays_observed,
)

__all__ = [
    "ALLOWED_EXTENDED_VERIFICATION_STATUSES",
    "CalendarTtlStatus",
    "DstSnapshot",
    "EXTENDED_EVENT_CODES",
    "ExtendedRedNewsEvent",
    "FeedHealthAssessment",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "TTL_AMBER_DAYS_DEFAULT",
    "TTL_RED_DAYS_DEFAULT",
    "TZ_ATHENS",
    "TZ_AUCKLAND",
    "TZ_LONDON",
    "TZ_NEW_YORK",
    "TZ_PRAGUE",
    "TZ_ZURICH",
    "check_calendar_ttl",
    "evaluate_feed_health",
    "get_dst_divergence_windows",
    "is_eu_dst",
    "is_in_red_news_window",
    "is_us_dst",
    "load_extended_calendar",
    "load_merged_live_calendar",
    "match_symbol_event_codes",
    "ny_plus_7_offset_hours",
    "resolve_dst_snapshot",
    "resolve_eia_wpsr_release",
    "resolve_firm_daily_reset_utc",
    "resolve_strategy_session_utc",
    "resolve_timezone",
    "symbol_matches_event_code",
    "us_federal_holidays_observed",
]
