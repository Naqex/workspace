"""Unit & SSOT contract tests for `quant_core.red_news` and all 4 red-news calendars."""

from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import pytest

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.red_news import (  # noqa: E402
    ALLOWED_CURRENCIES,
    BOJ_VARIABLE_BLACKOUT_SEC,
    DEFAULT_BLACKOUT_SEC,
    GAP_WARNING_FLAG,
    MAX_BLACKOUT_SEC,
    PARTIAL_MACRO_GAP_FLAG,
    PROD_RED_NEWS_CSV_EXPECTED_EVENTS,
    PROD_RED_NEWS_CSV_SHA256,
    RedNewsEvent,
    get_calendar_coverage_report,
    load_calendar_events,
    load_calendar_events_by_day,
    validate_blackout_sec,
    validate_currency,
    validate_utc_iso,
    validate_verification_status,
    verify_production_csv_immutability,
)

CAL_DIR = AI_ENGINES / "configs/calendars"
CAL_1824 = CAL_DIR / "red_news_official_2018_2024.json"
CAL_2526 = CAL_DIR / "red_news_official_2025_2026.json"
CAL_2627 = CAL_DIR / "red_news_official_2026_2027_multi_ccy.json"
CAL_1824_6CCY = CAL_DIR / "red_news_official_2018_2024_6ccy.json"
LIVE_CSV = AI_ENGINES / "exports/Files/naqex_red_news_utc.csv"


def test_load_all_four_calendar_jsons_zero_keyerror() -> None:
    """All 4 calendar JSONs (legacy events_by_day + list events) load cleanly with 0 KeyError."""
    e_1824 = load_calendar_events(CAL_1824)
    e_2526 = load_calendar_events(CAL_2526)
    e_2627 = load_calendar_events(CAL_2627)
    e_6ccy = load_calendar_events(CAL_1824_6CCY)

    assert len(e_1824) == 224
    assert len(e_2526) == 63  # 31 in 2025 + 32 in 2026
    assert len(e_2627) == 208
    assert len(e_6ccy) == 523

    # Verify legacy events_by_day adapter also loads all 4 calendars without KeyError
    for cal_path, expected_count in (
        (CAL_1824, 224),
        (CAL_2526, 63),
        (CAL_2627, 208),
        (CAL_1824_6CCY, 523),
    ):
        grouped = load_calendar_events_by_day(cal_path)
        assert sum(len(v) for v in grouped.values()) == expected_count

    for batch in (e_1824, e_2526, e_2627, e_6ccy):
        for ev in batch:
            assert ev.ccy in ALLOWED_CURRENCIES
            assert ev.utc_iso.endswith("Z")
            assert 0 < ev.blackout_sec <= MAX_BLACKOUT_SEC
            assert math.isfinite(ev.blackout_sec)


def test_6ccy_2018_2024_preserves_224_usd_and_verifies_t1_metadata() -> None:
    """New 6-currency 2018-2024 calendar preserves 100% of 224 USD events & carries T1 provenance."""
    frozen_usd = load_calendar_events(CAL_1824)
    multi = load_calendar_events(CAL_1824_6CCY)

    frozen_usd_ts = {ev.utc_ts for ev in frozen_usd}
    multi_usd_ts = {ev.utc_ts for ev in multi if ev.ccy == "USD"}
    assert multi_usd_ts == frozen_usd_ts
    assert len(multi_usd_ts) == 224

    by_ccy: dict[str, int] = {}
    for ev in multi:
        by_ccy[ev.ccy] = by_ccy.get(ev.ccy, 0) + 1
        assert ev.verification_status == "VERIFIED_T1"
        assert ev.source_agency is not None and len(ev.source_agency) > 0
        assert ev.source_url is not None and ev.source_url.startswith("https://")
        if ev.ccy == "JPY":
            assert ev.blackout_sec == BOJ_VARIABLE_BLACKOUT_SEC
        else:
            assert ev.blackout_sec == DEFAULT_BLACKOUT_SEC

    assert by_ccy == {
        "USD": 224,
        "EUR": 56,
        "GBP": 56,
        "JPY": 57,
        "AUD": 74,
        "CAD": 56,
    }

    # Spot-check T1 historical publication time changes and pandemic adjustments
    by_key = {(ev.utc_day, ev.ccy): ev for ev in multi}
    # ECB 13:45 CEST -> 11:45Z pre-Jul 2022 vs 14:15 CEST -> 12:15Z from 2022-07-21
    assert by_key[("2022-06-09", "EUR")].utc_iso == "2022-06-09T11:45:00Z"
    assert by_key[("2022-07-21", "EUR")].utc_iso == "2022-07-21T12:15:00Z"
    # BoC 10:00 EST -> 15:00Z in 2023 vs 09:45 EST -> 14:45Z effective 2024-01-24
    assert by_key[("2023-12-06", "CAD")].utc_iso == "2023-12-06T15:00:00Z"
    assert by_key[("2024-01-24", "CAD")].utc_iso == "2024-01-24T14:45:00Z"
    # BoE 07:00 London pandemic releases & 2022-09-22 postponement
    assert by_key[("2020-05-07", "GBP")].utc_iso == "2020-05-07T06:00:00Z"
    assert by_key[("2020-08-06", "GBP")].utc_iso == "2020-08-06T06:00:00Z"
    assert by_key[("2020-11-05", "GBP")].utc_iso == "2020-11-05T07:00:00Z"
    assert by_key[("2022-09-22", "GBP")].utc_iso == "2022-09-22T11:00:00Z"
    # RBA 2018-04-03 (first Tue of April, NOT Apr 10) & 2024 8-meeting reform
    assert ("2018-04-03", "AUD") in by_key
    assert ("2018-04-10", "AUD") not in by_key
    assert sum(1 for ev in multi if ev.ccy == "AUD" and ev.utc_day.startswith("2024-")) == 8
    # BoJ 2020 pandemic reschedules (Mar 16, Apr 27, May 22, Jul 15)
    for boj_2020_day in ("2020-03-16", "2020-04-27", "2020-05-22", "2020-07-15"):
        assert (boj_2020_day, "JPY") in by_key
        assert by_key[(boj_2020_day, "JPY")].blackout_sec == 3600

    # Verify explicit top-level unverified_gaps array documents non-guessed items
    raw_6ccy = json.loads(CAL_1824_6CCY.read_text(encoding="utf-8"))
    gaps = raw_6ccy.get("unverified_gaps")
    assert isinstance(gaps, list) and len(gaps) >= 5
    assert all(g.get("verification_status") == "UNKNOWN_UNVERIFIED" for g in gaps)


def test_coverage_report_triggers_usd32_vs_live140_gap_and_clears_on_6ccy() -> None:
    """USD-only Dev calendar vs Live CSV MUST emit BACKTEST_USD32_VS_LIVE140_GAP."""
    rep_usd = get_calendar_coverage_report(CAL_1824, LIVE_CSV)
    assert rep_usd["dev_is_usd_only"] is True
    assert rep_usd["dev"]["max_events_per_year"] == 32
    assert rep_usd["live_multi_ccy_reference"]["min_events_per_year"] == 97
    assert rep_usd["live_multi_ccy_reference"]["max_events_per_year"] == 140
    assert rep_usd["has_usd32_vs_live140_gap"] is True
    assert GAP_WARNING_FLAG in rep_usd["warnings"]
    assert rep_usd["missing_currencies_in_dev"] == ["AUD", "CAD", "EUR", "GBP", "JPY"]

    rep_6ccy = get_calendar_coverage_report(CAL_1824_6CCY, LIVE_CSV)
    assert rep_6ccy["dev_is_usd_only"] is False
    assert rep_6ccy["has_usd32_vs_live140_gap"] is False
    assert GAP_WARNING_FLAG not in rep_6ccy["warnings"]
    assert rep_6ccy["missing_currencies_in_dev"] == []
    assert PARTIAL_MACRO_GAP_FLAG in rep_6ccy["warnings"]


def test_production_csv_immutability_and_frozen_2025_2026_invariants(tmp_path: Path) -> None:
    """Production CSV keeps exact SHA 235722ed..., LF-only, 492 events; bare CR fails."""
    chk = verify_production_csv_immutability(LIVE_CSV)
    assert chk["ok"] is True
    assert chk["lf_only"] is True
    assert chk["event_count"] == PROD_RED_NEWS_CSV_EXPECTED_EVENTS == 492
    assert chk["sha256"].startswith("235722ed")
    assert chk["sha256"] == PROD_RED_NEWS_CSV_SHA256

    # Bare CR in CSV must fail lf_only check
    bare_cr_csv = tmp_path / "bare_cr.csv"
    bare_cr_csv.write_bytes(b"utc_ts,ccy,event\r1704461400,USD,US_NFP\n")
    cr_chk = verify_production_csv_immutability(
        bare_cr_csv, expected_sha256=chk["sha256"], expected_events=1
    )
    assert cr_chk["lf_only"] is False
    assert cr_chk["ok"] is False

    csv_events = load_calendar_events(LIVE_CSV)
    assert len(csv_events) == 492

    e_2526 = load_calendar_events(CAL_2526)
    e_2025 = [ev for ev in e_2526 if ev.utc_day.startswith("2025-")]
    assert len(e_2025) == 31
    # BLS cancelled Oct 2025 CPI (scheduled Nov 2025); MUST NOT fabricate a Nov 2025 CPI row
    nov_2025_cpi = [
        ev for ev in e_2025 if ev.utc_day.startswith("2025-11-") and "CPI" in ev.event
    ]
    assert nov_2025_cpi == []

    # Confirm Dec 2026 live BLS dates remain intact
    dec_2026 = {(ev.utc_iso, ev.ccy, ev.event) for ev in e_2526 if ev.utc_day.startswith("2026-12-")}
    assert ("2026-12-04T13:30:00Z", "USD", "US_NFP") in dec_2026
    assert ("2026-12-10T13:30:00Z", "USD", "US_CPI") in dec_2026


def test_fail_closed_validation_rejects_bad_timestamps_ccy_blackout_and_schema(
    tmp_path: Path,
) -> None:
    """Invalid currencies, timestamps, blackout_sec, URLs, or schemas fail closed."""
    with pytest.raises(ValueError, match="Unsupported currency"):
        validate_currency("CHF")
    with pytest.raises(ValueError, match="Currency must be a string"):
        validate_currency(123)

    # Strict ISO-8601 UTC: reject missing seconds, compact basic, week dates, fractional, non-UTC
    for bad_iso in (
        "2024-01-05 13:30:00Z",
        "2024-01-05T13:30:00",
        "2024-01-05T13:30:00+02:00",
        "2024-01-05T13:30Z",
        "20240105T133000Z",
        "2024-W01-5T13:30:00Z",
        "2024-01-05T13:30:00.000Z",
        "not-a-timestamp",
    ):
        with pytest.raises(ValueError):
            validate_utc_iso(bad_iso)
    with pytest.raises(ValueError, match="does not match utc_ts"):
        validate_utc_iso("2024-01-05T13:30:00Z", expected_ts=1704461401)

    for bad_sec in (
        0,
        -300,
        float("nan"),
        float("inf"),
        float("-inf"),
        True,
        300.5,
        "300",
        MAX_BLACKOUT_SEC + 1,
        1e308,
    ):
        with pytest.raises(ValueError):
            validate_blackout_sec(bad_sec)

    with pytest.raises(ValueError, match="Unsupported verification_status"):
        validate_verification_status("GUESSED")
    with pytest.raises(ValueError, match="requires non-empty source_agency"):
        validate_verification_status("VERIFIED_T1", source_agency=None, source_url="https://bls.gov")
    for bad_url in ("bls.gov", "https://", "https://localhost", "https://bls.gov/a b", "ftp://bls.gov"):
        with pytest.raises(ValueError, match="source_url"):
            validate_verification_status("VERIFIED_T1", source_agency="BLS", source_url=bad_url)

    # Unknown JSON schema must raise ValueError, NOT raw KeyError
    bad_schema_file = tmp_path / "bad_cal.json"
    bad_schema_file.write_text(json.dumps({"schema": "empty"}), encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported calendar schema"):
        load_calendar_events(bad_schema_file)

    # Ambiguous dual-schema JSON (both events and events_by_day) must fail closed
    dual_schema_file = tmp_path / "dual_cal.json"
    dual_schema_file.write_text(
        json.dumps({
            "events": [{"utc_iso": "2024-01-05T13:30:00Z", "ccy": "USD", "event": "US_NFP"}],
            "events_by_day": {"2024-01-05": [{"utc_ts": 1704461400, "ccy": "USD"}]},
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Ambiguous dual-schema"):
        load_calendar_events(dual_schema_file)


def test_fail_closed_rejects_duplicate_events_duplicate_ids_and_empty_calendars(
    tmp_path: Path,
) -> None:
    """Duplicate events/IDs and empty calendars MUST fail closed (never bypass gap guard)."""
    # 1. Duplicate (utc_ts, ccy, event) in JSON list must raise (blocks gap-warning inflation)
    dup_json = tmp_path / "dup_events.json"
    dup_json.write_text(
        json.dumps({
            "events": [
                {"utc_iso": "2024-01-05T13:30:00Z", "ccy": "USD", "event": "US_NFP"},
                {"utc_iso": "2024-01-05T13:30:00Z", "ccy": "USD", "event": "US_NFP"},
            ]
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate calendar event"):
        load_calendar_events(dup_json)

    # 2. Duplicate (utc_ts, ccy, event) in CSV must raise
    dup_csv = tmp_path / "dup_events.csv"
    dup_csv.write_text(
        "utc_ts,ccy,event\n1704461400,USD,US_NFP\n1704461400,USD,US_NFP\n",
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate calendar event"):
        load_calendar_events(dup_csv)

    # 3. Duplicate explicit event_id / id must raise even if timestamps differ
    dup_id_json = tmp_path / "dup_ids.json"
    dup_id_json.write_text(
        json.dumps({
            "events": [
                {"event_id": "NFP_1", "utc_iso": "2024-01-05T13:30:00Z", "ccy": "USD", "event": "US_NFP"},
                {"id": "NFP_1", "utc_iso": "2024-02-02T13:30:00Z", "ccy": "USD", "event": "US_NFP"},
            ]
        }),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="Duplicate event_id"):
        load_calendar_events(dup_id_json)

    # 4. Duplicate RedNewsEvent sequence passed directly into coverage report must also raise
    ev = RedNewsEvent(
        utc_ts=1704461400,
        utc_iso="2024-01-05T13:30:00Z",
        utc_day="2024-01-05",
        ccy="USD",
        event="US_NFP",
    )
    with pytest.raises(ValueError, match="Duplicate calendar event"):
        get_calendar_coverage_report([ev, ev], LIVE_CSV)

    # 5. Empty JSON events, empty events_by_day, header-only CSV, and empty sequence must raise
    empty_list = tmp_path / "empty_list.json"
    empty_list.write_text(json.dumps({"events": []}), encoding="utf-8")
    with pytest.raises(ValueError, match="Empty red-news calendar"):
        load_calendar_events(empty_list)

    empty_map = tmp_path / "empty_map.json"
    empty_map.write_text(json.dumps({"events_by_day": {}}), encoding="utf-8")
    with pytest.raises(ValueError, match="Empty red-news calendar"):
        load_calendar_events(empty_map)

    empty_csv = tmp_path / "empty.csv"
    empty_csv.write_text("utc_ts,ccy,event\n", encoding="utf-8")
    with pytest.raises(ValueError, match="Empty red-news calendar"):
        load_calendar_events(empty_csv)

    with pytest.raises(ValueError, match="Empty red-news calendar"):
        get_calendar_coverage_report([], LIVE_CSV)
