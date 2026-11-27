"""Unit & contract tests for OPS-1: US/EU DST, Extended 8-CCY+EIA Calendar, TTL Guard, and Feed Health."""

from __future__ import annotations

import ast
import json
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.red_news import (  # noqa: E402
    PROD_RED_NEWS_CSV_SHA256,
    load_calendar_events,
    verify_production_csv_immutability,
)
from quant_factory.live_ops import (  # noqa: E402
    EXTENDED_EVENT_CODES,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
    ExtendedRedNewsEvent,
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
from quant_factory.live_ops import feed_dst_news_guard as dst_mod  # noqa: E402

CAL_DIR = AI_ENGINES / "configs/calendars"
EXT_CAL_PATH = CAL_DIR / "red_news_extended_off3_8ccy_eia.json"
LIVE_CSV_PATH = AI_ENGINES / "exports/Files/naqex_red_news_utc.csv"
FROZEN_6CCY_PATH = CAL_DIR / "red_news_official_2018_2024_6ccy.json"
LIVE_OPS_DIR = AI_ENGINES / "quant_factory/live_ops"


def test_safety_boundaries_no_bare_asserts_no_mt5_and_csv_immutability() -> None:
    """Enforce [ARCH-02] zero bare asserts, OrderSend=0, zero MT5 imports, and immutable live CSV."""
    assert ORDER_SEND_CAPABLE is False
    assert ORDER_SEND_COUNT == 0

    for py_file in (LIVE_OPS_DIR / "__init__.py", LIVE_OPS_DIR / "feed_dst_news_guard.py"):
        src = py_file.read_text(encoding="utf-8")
        tree = ast.parse(src, filename=str(py_file))
        bare_asserts = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        assert bare_asserts == [], f"Forbidden bare assert in {py_file}: lines {bare_asserts}"

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert "metatrader5" not in alias.name.lower()
            elif isinstance(node, ast.ImportFrom) and node.module:
                assert "metatrader5" not in node.module.lower()

    chk = verify_production_csv_immutability(LIVE_CSV_PATH)
    assert chk["ok"] is True
    assert chk["sha256"] == PROD_RED_NEWS_CSV_SHA256


def test_us_vs_eu_dst_spring_and_fall_divergence_and_athens_vs_ny7_guard() -> None:
    """Prove & guard 1-hour US/EU divergence so The5ers/F03/F04/F05/F09 NEVER confuse Athens with NY+7."""
    # 1. Normal Winter (Jan 15 2026): US EST (-5 -> NY+7=+2) == Athens EET (+2), Prague CET (+1), London GMT (0)
    win = resolve_dst_snapshot(datetime(2026, 1, 15, 12, 0, tzinfo=UTC))
    assert win.us_dst_active is False
    assert win.eu_dst_active is False
    assert win.is_dst_divergence_window is False
    assert win.divergence_season == "NONE"
    assert win.ny_plus_7_offset_hours == 2
    assert win.athens_offset_hours == 2
    assert win.prague_offset_hours == 1
    assert win.london_offset_hours == 0
    assert win.ny_plus_7_vs_athens_delta_hours == 0
    assert win.ny_plus_7_vs_prague_delta_hours == 1
    assert win.london_vs_ny_delta_hours == 5
    assert win.the5ers_reset_utc_hour == 22
    assert win.ftmo_prague_reset_utc_hour == 23

    # 2. Normal Summer (Jul 15 2026): US EDT (-4 -> NY+7=+3) == Athens EEST (+3), Prague CEST (+2), London BST (+1)
    smr = resolve_dst_snapshot(datetime(2026, 7, 15, 12, 0, tzinfo=UTC))
    assert smr.us_dst_active is True
    assert smr.eu_dst_active is True
    assert smr.is_dst_divergence_window is False
    assert smr.ny_plus_7_offset_hours == 3
    assert smr.athens_offset_hours == 3
    assert smr.prague_offset_hours == 2
    assert smr.london_offset_hours == 1
    assert smr.ny_plus_7_vs_athens_delta_hours == 0
    assert smr.ny_plus_7_vs_prague_delta_hours == 1
    assert smr.london_vs_ny_delta_hours == 5
    assert smr.the5ers_reset_utc_hour == 21
    assert smr.ftmo_prague_reset_utc_hour == 22

    # 3. Spring Gap 2026 (Mar 8 07:00Z .. Mar 29 01:00Z — 3 weeks!): US EDT while EU still Standard!
    wins_2026 = get_dst_divergence_windows(2026)
    assert wins_2026["spring"] == (
        datetime(2026, 3, 8, 7, 0, tzinfo=UTC),
        datetime(2026, 3, 29, 1, 0, tzinfo=UTC),
    )
    assert wins_2026["fall"] == (
        datetime(2026, 10, 25, 1, 0, tzinfo=UTC),
        datetime(2026, 11, 1, 6, 0, tzinfo=UTC),
    )

    spr = resolve_dst_snapshot(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    assert spr.us_dst_active is True
    assert spr.eu_dst_active is False
    assert spr.is_dst_divergence_window is True
    assert spr.divergence_season == "SPRING_US_AHEAD_OF_EU"
    assert spr.ny_plus_7_offset_hours == 3
    assert spr.athens_offset_hours == 2
    assert spr.ny_plus_7_vs_athens_delta_hours == 1  # Athens is 1h BEHIND NY+7!
    assert spr.ny_plus_7_vs_prague_delta_hours == 2  # Prague is 2h behind NY+7 instead of 1h!
    assert spr.london_vs_ny_delta_hours == 4         # London-NY gap compresses from 5h to 4h!
    assert spr.the5ers_reset_utc_hour == 21          # 17:00 EDT == 21:00Z (NOT Athens 22:00Z!)
    assert spr.ftmo_prague_reset_utc_hour == 23      # 00:00 CET == 23:00Z

    # 4. Fall Gap 2026 (Oct 25 01:00Z .. Nov 1 06:00Z — 1 week!): EU fell back while US still EDT!
    fal = resolve_dst_snapshot(datetime(2026, 10, 28, 12, 0, tzinfo=UTC))
    assert fal.us_dst_active is True
    assert fal.eu_dst_active is False
    assert fal.is_dst_divergence_window is True
    assert fal.divergence_season == "FALL_EU_FELL_BACK_BEFORE_US"
    assert fal.ny_plus_7_offset_hours == 3
    assert fal.athens_offset_hours == 2
    assert fal.ny_plus_7_vs_athens_delta_hours == 1
    assert fal.the5ers_reset_utc_hour == 21
    assert fal.ftmo_prague_reset_utc_hour == 23

    # Exact transition-minute boundaries
    assert is_us_dst(datetime(2026, 3, 8, 6, 59, tzinfo=UTC)) is False
    assert is_us_dst(datetime(2026, 3, 8, 7, 0, tzinfo=UTC)) is True
    assert is_eu_dst(datetime(2026, 3, 29, 0, 59, tzinfo=UTC)) is False
    assert is_eu_dst(datetime(2026, 3, 29, 1, 0, tzinfo=UTC)) is True
    assert is_eu_dst(datetime(2026, 10, 25, 0, 59, tzinfo=UTC)) is True
    assert is_eu_dst(datetime(2026, 10, 25, 1, 0, tzinfo=UTC)) is False
    assert is_us_dst(datetime(2026, 11, 1, 5, 59, tzinfo=UTC)) is True
    assert is_us_dst(datetime(2026, 11, 1, 6, 0, tzinfo=UTC)) is False
    assert ny_plus_7_offset_hours(datetime(2026, 10, 28, 12, 0, tzinfo=UTC)) == 3

    # Firm daily reset resolvers warn explicitly about Athens confusion during gap weeks
    t5_gap = resolve_firm_daily_reset_utc("the5ers", datetime(2026, 3, 18, 15, 0, tzinfo=UTC))
    assert t5_gap["next_reset_utc_iso"] == "2026-03-18T21:00:00Z"
    assert t5_gap["athens_confusion_warning"] is True
    ftmo_gap = resolve_firm_daily_reset_utc("ftmo", datetime(2026, 3, 18, 15, 0, tzinfo=UTC))
    assert ftmo_gap["next_reset_utc_iso"] == "2026-03-18T23:00:00Z"
    assert ftmo_gap["server_ny7_reset_utc_hour"] == 21
    assert ftmo_gap["server_vs_prague_delta_hours"] == 2

    # Strategy session anchors (F03 London vs F04/F05/F09 NY) stay pinned to true local exchanges
    f03_gap = resolve_strategy_session_utc("F03", date(2026, 3, 18))
    f04_gap = resolve_strategy_session_utc("F04", date(2026, 3, 18))
    f05_gap = resolve_strategy_session_utc("F05", date(2026, 3, 18))
    f09_gap = resolve_strategy_session_utc("F09", date(2026, 3, 18))
    assert f03_gap["utc_iso"] == "2026-03-18T08:00:00Z"  # London still GMT
    assert f04_gap["utc_iso"] == "2026-03-18T13:30:00Z"  # NY already EDT (09:30 EDT)
    assert f05_gap["utc_iso"] == "2026-03-18T14:00:00Z"  # 10:00 EDT
    assert f09_gap["utc_iso"] == "2026-03-18T21:00:00Z"  # 17:00 EDT == 00:00 NY+7
    assert f03_gap["is_dst_divergence_window"] is True


def test_extended_calendar_schema_separation_provenance_and_eia_holiday_shifts() -> None:
    """Validate additive 8-CCY+EIA JSON: Dev vs Live separation, zero 2025, SNB/RBNZ/EIA parity."""
    raw = json.loads(EXT_CAL_PATH.read_text(encoding="utf-8"))
    assert raw["strictly_separated_from_frozen_6ccy"] is True
    assert raw["holdout_2025_excluded"] is True
    assert set(raw["sections"].keys()) == {"dev_2018_2024", "live_2026_2027"}
    assert isinstance(raw["unverified_gaps"], list) and len(raw["unverified_gaps"]) >= 3

    dev_events = load_extended_calendar(EXT_CAL_PATH, sections=["dev_2018_2024"])
    live_events = load_extended_calendar(EXT_CAL_PATH, sections=["live_2026_2027"])
    all_events = load_extended_calendar(EXT_CAL_PATH)

    assert len(dev_events) == 441
    assert len(live_events) == 127
    assert len(all_events) == 568

    # Strictly zero 2025 Holdout rows
    assert all(ev.utc_day[:4] != "2025" for ev in all_events)
    assert all(2018 <= int(ev.utc_day[:4]) <= 2024 for ev in dev_events)
    assert all(ev.utc_day[:4] in ("2026", "2027") for ev in live_events)

    # Exact per-code counts
    dev_by_ccy = {c: sum(1 for e in dev_events if e.ccy == c) for c in ("CHF", "NZD", "EIA")}
    live_by_ccy = {c: sum(1 for e in live_events if e.ccy == c) for c in ("CHF", "NZD", "EIA")}
    assert dev_by_ccy == {"CHF": 28, "NZD": 48, "EIA": 365}
    assert live_by_ccy == {"CHF": 8, "NZD": 15, "EIA": 104}

    # Spot-check SNB (CHF) DST UTC conversions: Mar/Dec CET (08:30Z) vs Jun/Sep CEST (07:30Z)
    by_key = {(e.local_date, e.ccy): e for e in all_events}
    assert by_key[("2026-03-19", "CHF")].utc_iso == "2026-03-19T08:30:00Z"  # EU still CET on Mar 19!
    assert by_key[("2026-06-18", "CHF")].utc_iso == "2026-06-18T07:30:00Z"  # CEST
    assert by_key[("2026-12-10", "CHF")].utc_iso == "2026-12-10T08:30:00Z"
    assert by_key[("2027-06-24", "CHF")].verification_status == "VERIFIED_T1"

    # Spot-check RBNZ (NZD): 2018 Thu 09:00 NZT vs 2019+ Wed 14:00 NZT, 2020-03-25 cancelled, 2027 8-meeting expansion
    assert by_key[("2018-02-08", "NZD")].utc_iso == "2018-02-07T20:00:00Z"  # 09:00 NZDT (+13)
    assert by_key[("2018-08-09", "NZD")].utc_iso == "2018-08-08T21:00:00Z"  # 09:00 NZST (+12)
    assert by_key[("2019-02-13", "NZD")].utc_iso == "2019-02-13T01:00:00Z"  # 14:00 NZDT (+13)
    assert ("2020-03-25", "NZD") not in by_key  # Cancelled after 2020-03-16 emergency COVID cut
    assert sum(1 for e in live_events if e.ccy == "NZD" and e.local_date and e.local_date.startswith("2026-")) == 7
    assert sum(1 for e in live_events if e.ccy == "NZD" and e.local_date and e.local_date.startswith("2027-")) == 8

    # Spot-check EIA holiday Thursday shifts:
    # Historical 2018-2024: Memorial Day 2024 (Mon May 27) -> Thu 2024-05-30 11:00 EDT (15:00Z)
    rel_d, rel_t, shifted, hol = resolve_eia_wpsr_release(date(2024, 5, 29))
    assert (rel_d, rel_t, shifted, hol) == (date(2024, 5, 30), "11:00", True, "Memorial Day")
    assert by_key[("2024-05-30", "EIA")].utc_iso == "2024-05-30T15:00:00Z"
    assert by_key[("2024-05-30", "EIA")].holiday_shifted is True
    assert ("2024-05-29", "EIA") not in by_key

    # Juneteenth effective from 2021 (NOT a federal holiday in 2020!)
    assert date(2020, 6, 19) not in us_federal_holidays_observed(2020)
    assert date(2024, 6, 19) in us_federal_holidays_observed(2024)
    assert by_key[("2024-06-20", "EIA")].holiday_name == "Juneteenth National Independence Day"
    assert by_key[("2024-06-20", "EIA")].local_time == "11:00"

    # Live 2026-2027 eia.gov VERIFIED_T1 Thursday 12:00 ET shifts
    eia_2026_mem = by_key[("2026-05-28", "EIA")]
    assert eia_2026_mem.local_time == "12:00"
    assert eia_2026_mem.utc_iso == "2026-05-28T16:00:00Z"
    assert eia_2026_mem.verification_status == "VERIFIED_T1"
    assert eia_2026_mem.holiday_shifted is True
    assert ("2026-05-27", "EIA") not in by_key

    eia_2026_vet = by_key[("2026-11-12", "EIA")]  # Veterans Day Wed Nov 11 -> Thu Nov 12 12:00 EST (17:00Z)
    assert eia_2026_vet.utc_iso == "2026-11-12T17:00:00Z"
    assert eia_2026_vet.verification_status == "VERIFIED_T1"

    # Normal non-holiday Wednesday stays 10:30 ET
    eia_2026_norm = by_key[("2026-06-03", "EIA")]
    assert eia_2026_norm.local_time == "10:30"
    assert eia_2026_norm.utc_iso == "2026-06-03T14:30:00Z"
    assert eia_2026_norm.holiday_shifted is False

    # Thanksgiving falls on Thursday -> Wednesday release is NOT shifted!
    eia_2026_tg = by_key[("2026-11-25", "EIA")]
    assert eia_2026_tg.holiday_shifted is False
    assert eia_2026_tg.local_time == "10:30"

    # Frozen 6-ccy calendar remains completely separate and untouched
    frozen_6ccy = load_calendar_events(FROZEN_6CCY_PATH)
    assert len(frozen_6ccy) == 523


def test_calendar_ttl_guard_green_amber_red_and_missing_code_fail_closed() -> None:
    """TTL guard returns GREEN (>14d), AMBER (<=14d), and RED (<=3d / expired / missing code)."""
    ev_usd = ExtendedRedNewsEvent(
        utc_ts=int(datetime(2026, 12, 31, 13, 30, tzinfo=UTC).timestamp()),
        utc_iso="2026-12-31T13:30:00Z",
        utc_day="2026-12-31",
        ccy="USD",
        event="US_TEST",
    )
    ev_eia = ExtendedRedNewsEvent(
        utc_ts=int(datetime(2026, 12, 20, 15, 30, tzinfo=UTC).timestamp()),
        utc_iso="2026-12-20T15:30:00Z",
        utc_day="2026-12-20",
        ccy="EIA",
        event="EIA_TEST",
    )
    events = [ev_usd, ev_eia]

    # 1. > 14d remaining for both USD & EIA -> GREEN
    st_green = check_calendar_ttl(events, now_utc=datetime(2026, 12, 1, 12, 0, tzinfo=UTC), symbol="USOIL")
    assert st_green.status == "GREEN"
    assert st_green.allow_new_entries is True
    assert st_green.min_remaining_days > 14.0

    # 2. <= 14d and > 3d remaining (10d left on EIA) -> AMBER (warn, entries still allowed)
    st_amber = check_calendar_ttl(events, now_utc=datetime(2026, 12, 10, 15, 30, tzinfo=UTC), symbol="USOIL")
    assert st_amber.status == "AMBER"
    assert st_amber.allow_new_entries is True
    assert st_amber.amber_codes == ("EIA",)
    assert st_amber.per_code_status["USD"] == "GREEN"
    assert st_amber.per_code_status["EIA"] == "AMBER"

    # 3. Exactly <= 3d remaining (3.0d left on EIA) -> RED (fail-closed!)
    st_red_3d = check_calendar_ttl(events, now_utc=datetime(2026, 12, 17, 15, 30, tzinfo=UTC), symbol="USOIL")
    assert st_red_3d.status == "RED"
    assert st_red_3d.allow_new_entries is False
    assert "EIA" in st_red_3d.red_codes

    # 4. Expired (< 0d) -> RED (fail-closed!)
    st_exp = check_calendar_ttl(events, now_utc=datetime(2026, 12, 21, 0, 0, tzinfo=UTC), symbol="USOIL")
    assert st_exp.status == "RED"
    assert st_exp.allow_new_entries is False
    assert "EIA" in st_exp.expired_codes

    # 5. Missing required code (USOIL needs EIA + USD, passing USD-only fails closed!)
    st_missing = check_calendar_ttl([ev_usd], now_utc=datetime(2026, 12, 1, 0, 0, tzinfo=UTC), symbol="USOIL")
    assert st_missing.status == "RED"
    assert st_missing.allow_new_entries is False
    assert st_missing.missing_codes == ("EIA",)

    # 6. Empty calendar fails closed
    st_empty = check_calendar_ttl([], now_utc=datetime(2026, 12, 1, 0, 0, tzinfo=UTC), symbol="EURUSD")
    assert st_empty.status == "RED"
    assert st_empty.allow_new_entries is False

    # 7. Real merged live calendar (base CSV + extended 2026-2027) is GREEN across all 9 codes on 2026-11-27
    merged = load_merged_live_calendar(LIVE_CSV_PATH, EXT_CAL_PATH, include_extended_sections=("live_2026_2027",))
    st_live = check_calendar_ttl(
        merged,
        now_utc=datetime(2026, 11, 27, 12, 0, tzinfo=UTC),
        required_codes=sorted(EXTENDED_EVENT_CODES),
    )
    assert st_live.status == "GREEN"
    assert st_live.allow_new_entries is True
    assert st_live.min_remaining_days > 365.0


def test_symbol_to_event_matching_and_red_news_windows_for_oil_jp225_metals_chf_nzd() -> None:
    """Verify USOIL/UKOIL, JP225, XAG/XAU, CHF, and NZD matching & red-news blackout/hard-ban windows."""
    assert match_symbol_event_codes("USOIL") == frozenset({"EIA", "USD"})
    assert match_symbol_event_codes("USOIL.cash") == frozenset({"EIA", "USD"})
    assert match_symbol_event_codes("UKOIL.cash") == frozenset({"EIA", "USD"})
    assert match_symbol_event_codes("WTI") == frozenset({"EIA", "USD"})
    assert match_symbol_event_codes("BRENT") == frozenset({"EIA", "USD"})
    assert match_symbol_event_codes("JP225") == frozenset({"JPY", "USD"})
    assert match_symbol_event_codes("JP225.cash") == frozenset({"JPY", "USD"})
    assert match_symbol_event_codes("NIKKEI") == frozenset({"JPY", "USD"})
    assert match_symbol_event_codes("XAGUSD") == frozenset({"USD"})
    assert match_symbol_event_codes("XAUUSD.pro") == frozenset({"USD"})
    assert match_symbol_event_codes("EURCHF") == frozenset({"EUR", "CHF"})
    assert match_symbol_event_codes("NZDJPY") == frozenset({"NZD", "JPY"})
    assert match_symbol_event_codes("NZDCHF") == frozenset({"NZD", "CHF"})

    assert symbol_matches_event_code("USOIL.cash", "EIA") is True
    assert symbol_matches_event_code("USOIL.cash", "USD") is True
    assert symbol_matches_event_code("USOIL.cash", "JPY") is False
    assert symbol_matches_event_code("JP225", "JPY") is True
    assert symbol_matches_event_code("JP225", "USD") is True
    assert symbol_matches_event_code("JP225", "EIA") is False

    merged = load_merged_live_calendar(LIVE_CSV_PATH, EXT_CAL_PATH, include_extended_sections=("live_2026_2027",))

    # 1. USOIL on Memorial Day holiday Thursday 2026-05-28 12:00 EDT (16:00Z):
    #    - 4m before (15:56Z): in block + pre-flatten, NOT in hard-ban
    win_pre = is_in_red_news_window("USOIL.cash", datetime(2026, 5, 28, 15, 56, tzinfo=UTC), merged)
    assert win_pre["in_block_window"] is True
    assert win_pre["in_pre_flatten_window"] is True
    assert win_pre["in_hard_ban_window"] is False
    #    - 1m before (15:59Z): in block + hard-ban, NOT pre-flatten
    win_ban = is_in_red_news_window("USOIL.cash", datetime(2026, 5, 28, 15, 59, tzinfo=UTC), merged)
    assert win_ban["in_block_window"] is True
    assert win_ban["in_hard_ban_window"] is True
    assert win_ban["in_pre_flatten_window"] is False
    #    - Wednesday 2026-05-27 10:30 EDT (14:30Z) is NOT blocked because Memorial Day shifted EIA to Thursday!
    win_wed_clear = is_in_red_news_window("USOIL.cash", datetime(2026, 5, 27, 14, 30, tzinfo=UTC), merged)
    assert win_wed_clear["in_block_window"] is False

    # 2. JP225 blocked on BOTH BoJ (JPY, +-60m) and US NFP (USD, 2026-12-04 13:30Z)
    jp_boj = is_in_red_news_window("JP225.cash", datetime(2026, 3, 19, 3, 25, tzinfo=UTC), merged)
    assert jp_boj["in_block_window"] is True
    jp_nfp = is_in_red_news_window("JP225.cash", datetime(2026, 12, 4, 13, 30, tzinfo=UTC), merged)
    assert jp_nfp["in_block_window"] is True

    # 3. EURCHF blocked on SNB (2026-12-10 08:30Z) & NZDUSD blocked on RBNZ (2026-12-09 01:00Z = 14:00 NZDT)
    chf_snb = is_in_red_news_window("EURCHF", datetime(2026, 12, 10, 8, 30, tzinfo=UTC), merged)
    assert chf_snb["in_block_window"] is True
    nzd_rbnz = is_in_red_news_window("NZDUSD", datetime(2026, 12, 9, 1, 0, tzinfo=UTC), merged)
    assert nzd_rbnz["in_block_window"] is True
    assert datetime(2026, 12, 9, 14, 0, tzinfo=resolve_timezone("Pacific/Auckland")).astimezone(UTC) == datetime(
        2026, 12, 9, 1, 0, tzinfo=UTC
    )


def test_stale_tick_freeze_quote_and_synthetic_spread_spike_detection() -> None:
    """Verify evaluate_feed_health catches stale ticks, frozen quotes, spread spikes, and bad quotes."""
    now = datetime(2026, 11, 27, 14, 0, 0, tzinfo=UTC)

    # 1. Healthy tick -> GREEN
    ok = evaluate_feed_health(
        symbol="EURUSD",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=3),
        bid=1.08500,
        ask=1.08510,
        point_size=0.00001,
        median_spread_points=10.0,
        hard_max_spread_points=35.0,
    )
    assert ok.status == "GREEN"
    assert ok.allow_trading is True
    assert ok.spread_points == pytest.approx(10.0)
    assert ok.spread_ratio == pytest.approx(1.0)

    # 2. Aging tick (20s vs 30s limit) -> AMBER
    aging = evaluate_feed_health(
        symbol="EURUSD",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=20),
        bid=1.08500,
        ask=1.08510,
        point_size=0.00001,
        median_spread_points=10.0,
    )
    assert aging.status == "AMBER"
    assert aging.allow_trading is True
    assert aging.is_stale is False

    # 3. Stale tick (45s > 30s) -> RED fail-closed
    stale = evaluate_feed_health(
        symbol="USOIL.cash",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=45),
        bid=70.10,
        ask=70.13,
        point_size=0.01,
        median_spread_points=3.0,
    )
    assert stale.status == "RED"
    assert stale.allow_trading is False
    assert stale.is_stale is True

    # 4. Frozen quote (22 identical consecutive mids over 44 seconds) -> RED fail-closed
    freeze_ts = [now - timedelta(seconds=44 - 2 * i) for i in range(22)]
    frozen = evaluate_feed_health(
        symbol="JP225.cash",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=2),
        bid=39500.0,
        ask=39505.0,
        point_size=1.0,
        median_spread_points=5.0,
        recent_mids=[39502.5] * 22,
        recent_tick_timestamps_utc=freeze_ts,
        max_freeze_identical_ticks=20,
        freeze_min_span_sec=30.0,
    )
    assert frozen.status == "RED"
    assert frozen.allow_trading is False
    assert frozen.is_frozen is True

    # 5. Synthetic spread spike (60 pts vs 10 pt median = 6.0x >= 4.0x) -> RED fail-closed
    spike = evaluate_feed_health(
        symbol="XAUUSD",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=1),
        bid=2650.00,
        ask=2650.60,
        point_size=0.01,
        median_spread_points=10.0,
        max_spread_multiplier=4.0,
    )
    assert spike.status == "RED"
    assert spike.allow_trading is False
    assert spike.is_spread_spike is True
    assert spike.spread_ratio == pytest.approx(6.0)

    # 6. Inverted quote (ask < bid) -> RED fail-closed
    bad_q = evaluate_feed_health(
        symbol="GBPUSD",
        now_utc=now,
        last_tick_utc=now - timedelta(seconds=1),
        bid=1.27500,
        ask=1.27490,
        point_size=0.00001,
    )
    assert bad_q.status == "RED"
    assert bad_q.allow_trading is False
    assert bad_q.is_invalid_quote is True

    # 7. Market closed -> MARKET_CLOSED cleanly (not false stale alarm)
    closed = evaluate_feed_health(
        symbol="EURUSD",
        now_utc=now,
        last_tick_utc=now - timedelta(hours=12),
        bid=1.08500,
        ask=1.08510,
        is_market_open=False,
    )
    assert closed.status == "MARKET_CLOSED"
    assert closed.allow_trading is False
    assert closed.is_stale is False


def test_p1_05_stdlib_dst_fallback_parity_with_zoneinfo_and_tzdata_absent(monkeypatch: pytest.MonkeyPatch) -> None:
    """Prove 100% ZoneInfo parity for stdlib DST fallback across all transitions & absent tzdata."""
    zones = (
        "America/New_York",
        "Europe/London",
        "Europe/Prague",
        "Europe/Zurich",
        "Europe/Athens",
        "Pacific/Auckland",
    )

    # 1. Exact 100% parity against ZoneInfo (when tzdata is available) across 2018-2027 DST boundaries
    for tz_name in zones:
        zi = ZoneInfo(tz_name)
        fb = resolve_timezone(tz_name, prefer_fallback=True)
        for yr in range(2018, 2028):
            wins = get_dst_divergence_windows(yr)
            us_sp, eu_sp = wins["spring"]
            eu_fl, us_fl = wins["fall"]
            # NZ transitions: 1st Sun Apr 03:00 NZDT (Sat 14:00Z), last Sun Sep 02:00 NZST (Sat 14:00Z)
            nz_fl = datetime(yr, 4, 1, 14, 0, tzinfo=UTC) + timedelta(
                days=(6 - date(yr, 4, 1).weekday()) % 7 - 1
            )
            nz_sp_sun = date(yr, 10, 1) - timedelta(days=1)
            nz_sp_sun = nz_sp_sun - timedelta(days=(nz_sp_sun.weekday() - 6) % 7)
            nz_sp = datetime.combine(nz_sp_sun, datetime.min.time(), tzinfo=UTC) - timedelta(hours=10)

            anchors = [
                datetime(yr, 1, 15, 12, 0, tzinfo=UTC),
                datetime(yr, 7, 15, 12, 0, tzinfo=UTC),
                us_sp,
                eu_sp,
                eu_fl,
                us_fl,
                nz_fl,
                nz_sp,
            ]
            for anchor in anchors:
                for delta_min in (-90, -1, 0, 1, 30, 60, 90):
                    dt_u = anchor + timedelta(minutes=delta_min)
                    loc_zi = dt_u.astimezone(zi)
                    loc_fb = dt_u.astimezone(fb)
                    assert loc_fb.replace(tzinfo=None) == loc_zi.replace(tzinfo=None), (
                        f"UTC->local mismatch {tz_name} @ {dt_u.isoformat()}: fb={loc_fb} zi={loc_zi}"
                    )
                    assert loc_fb.utcoffset() == loc_zi.utcoffset(), f"offset mismatch {tz_name} @ {dt_u}"
                    assert loc_fb.dst() == loc_zi.dst(), f"dst mismatch {tz_name} @ {dt_u}"
                    assert loc_fb.fold == loc_zi.fold, f"fold mismatch {tz_name} @ {dt_u}"
                    assert loc_fb.tzname() == loc_zi.tzname(), f"tzname mismatch {tz_name} @ {dt_u}"

                    # Round-trip local -> UTC with both fold=0 and fold=1
                    naive_loc = loc_zi.replace(tzinfo=None)
                    for fold_v in (0, 1):
                        rt_zi = naive_loc.replace(tzinfo=zi, fold=fold_v)
                        rt_fb = naive_loc.replace(tzinfo=fb, fold=fold_v)
                        assert rt_fb.utcoffset() == rt_zi.utcoffset(), (
                            f"local->UTC offset mismatch {tz_name} @ {naive_loc} fold={fold_v}"
                        )
                        assert rt_fb.dst() == rt_zi.dst()
                        assert int(rt_fb.astimezone(UTC).timestamp()) == int(rt_zi.astimezone(UTC).timestamp())

    # 2. Simulate Windows Python completely lacking tzdata: everything MUST work cleanly without error
    def _missing_tzdata(key: str) -> ZoneInfo:
        raise ZoneInfoNotFoundError(f"Simulated missing tzdata for {key}")

    monkeypatch.setattr(dst_mod, "ZoneInfo", _missing_tzdata)
    monkeypatch.setattr(dst_mod, "_TZ_CACHE", {})
    monkeypatch.setattr(dst_mod, "_ZI_NEW_YORK", dst_mod.resolve_timezone("America/New_York"))
    monkeypatch.setattr(dst_mod, "_ZI_PRAGUE", dst_mod.resolve_timezone("Europe/Prague"))
    monkeypatch.setattr(dst_mod, "_ZI_LONDON", dst_mod.resolve_timezone("Europe/London"))
    monkeypatch.setattr(dst_mod, "_ZI_ATHENS", dst_mod.resolve_timezone("Europe/Athens"))

    snap_gap = resolve_dst_snapshot(datetime(2026, 3, 15, 12, 0, tzinfo=UTC))
    assert snap_gap.is_dst_divergence_window is True
    assert snap_gap.ny_plus_7_offset_hours == 3
    assert snap_gap.athens_offset_hours == 2
    assert snap_gap.the5ers_reset_utc_hour == 21
    assert snap_gap.ftmo_prague_reset_utc_hour == 23

    f04 = resolve_strategy_session_utc("F04", date(2026, 3, 18))
    assert f04["utc_iso"] == "2026-03-18T13:30:00Z"

    # Full 568-event extended calendar (America/New_York, Europe/Zurich, Pacific/Auckland) validates 100%!
    all_ev = load_extended_calendar(EXT_CAL_PATH)
    assert len(all_ev) == 568

    # 3. Unknown timezone still fails closed with ZoneInfoNotFoundError
    with pytest.raises(ZoneInfoNotFoundError):
        resolve_timezone("Mars/Olympus_Mons")
