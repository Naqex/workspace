"""Unified Red-News Calendar SSOT Loader, Validator, and Coverage Gap Auditor.

Handles both legacy `events_by_day: {...}` JSON calendars (`red_news_official_2018_2024.json`,
`red_news_official_2025_2026.json`), list-based `events: [...]` JSON calendars
(`red_news_official_2026_2027_multi_ccy.json`, `red_news_official_2018_2024_6ccy.json`),
and 3-column MQL5 UTC CSV feeds (`naqex_red_news_utc.csv`) without throwing `KeyError`.

Strict fail-closed validation:
  - Strict UTC ISO-8601 timestamps (`YYYY-MM-DDTHH:MM:SSZ` or `+00:00`, exact parity with `utc_ts`)
  - Allowed currencies: USD, GBP, EUR, JPY, AUD, CAD
  - Finite positive integer blackout seconds (`1 <= blackout_sec <= 86400`, excluding bool/NaN/Inf)
  - Rejects empty calendars, ambiguous dual-schema JSONs, duplicate `(utc_ts, ccy, event)` rows,
    and duplicate non-empty `event_id`/`id` keys
  - Mandatory `BACKTEST_USD32_VS_LIVE140_GAP` warning when Dev backtests use USD-only
    (`<= 35` events/yr) against multi-currency Live CSV (`~97-140` events/yr).
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import re
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

ALLOWED_CURRENCIES: frozenset[str] = frozenset({"USD", "GBP", "EUR", "JPY", "AUD", "CAD"})
ALLOWED_VERIFICATION_STATUSES: frozenset[str] = frozenset({"VERIFIED_T1", "UNKNOWN_UNVERIFIED"})

DEFAULT_BLACKOUT_SEC: int = 300
BOJ_VARIABLE_BLACKOUT_SEC: int = 3600
MAX_BLACKOUT_SEC: int = 86_400

GAP_WARNING_FLAG: str = "BACKTEST_USD32_VS_LIVE140_GAP"
PARTIAL_MACRO_GAP_FLAG: str = "DEV_6CCY_MISSING_NON_CB_MACRO_SERIES"

DEV_USD_ONLY_MAX_PER_YEAR: int = 35
LIVE_MULTI_CCY_MIN_PER_YEAR: int = 80

PROD_RED_NEWS_CSV_SHA256: str = "235722ed1821499f8d81b169418486d3a8b9c0e8911857c88fea8d2270d3dff7"
PROD_RED_NEWS_CSV_EXPECTED_EVENTS: int = 492

_MIN_VALID_UTC_TS: int = 946_684_800  # 2000-01-01T00:00:00Z
_MAX_VALID_UTC_TS: int = 2_524_608_000  # 2050-01-01T00:00:00Z
_STRICT_UTC_ISO_RE: re.Pattern[str] = re.compile(
    r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|\+00:00)$"
)


@dataclass(frozen=True)
class RedNewsEvent:
    """Canonical validated red-news calendar event record."""

    utc_ts: int
    utc_iso: str
    utc_day: str
    ccy: str
    event: str
    blackout_sec: int = DEFAULT_BLACKOUT_SEC
    event_id: str | None = None
    source_agency: str | None = None
    source_url: str | None = None
    verification_status: str = "UNKNOWN_UNVERIFIED"
    confidence: str | None = None
    local_date: str | None = None
    local_time: str | None = None
    tz_name: str | None = None
    schema_format: str = "events_list"

    def to_dict(self) -> dict[str, Any]:
        """Serialize event into a JSON-compatible dictionary."""
        return {
            "utc_ts": self.utc_ts,
            "utc_iso": self.utc_iso,
            "utc_day": self.utc_day,
            "ccy": self.ccy,
            "event": self.event,
            "blackout_sec": self.blackout_sec,
            "event_id": self.event_id,
            "source_agency": self.source_agency,
            "source_url": self.source_url,
            "verification_status": self.verification_status,
            "confidence": self.confidence,
            "local_date": self.local_date,
            "local_time": self.local_time,
            "tz_name": self.tz_name,
            "schema_format": self.schema_format,
        }


def validate_currency(ccy: Any) -> str:
    """Validate and normalize currency code against the 6 allowed currencies."""
    if not isinstance(ccy, str):
        raise ValueError(f"Currency must be a string, got {type(ccy).__name__}")
    norm = ccy.strip().upper()
    if norm not in ALLOWED_CURRENCIES:
        raise ValueError(
            f"Unsupported currency {ccy!r}; allowed={sorted(ALLOWED_CURRENCIES)}"
        )
    return norm


def validate_blackout_sec(value: Any) -> int:
    """Validate blackout window seconds as a finite integer in `[1, MAX_BLACKOUT_SEC]`."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"blackout_sec must be a finite positive number, got {value!r}")
    fval = float(value)
    if not math.isfinite(fval) or fval <= 0.0:
        raise ValueError(f"blackout_sec must be finite and > 0, got {value!r}")
    if fval > float(MAX_BLACKOUT_SEC):
        raise ValueError(
            f"blackout_sec exceeds upper bound {MAX_BLACKOUT_SEC}s: got {value!r}"
        )
    ival = int(fval)
    if fval != float(ival):
        raise ValueError(f"blackout_sec must be an integer number of seconds, got {value!r}")
    return ival


def validate_utc_ts(value: Any) -> tuple[int, str, str]:
    """Validate a Unix UTC timestamp and return `(utc_ts, canonical_utc_iso, utc_day)`."""
    if isinstance(value, bool) or not isinstance(value, int):
        raise ValueError(f"utc_ts must be an integer, got {value!r}")
    if value < _MIN_VALID_UTC_TS or value > _MAX_VALID_UTC_TS:
        raise ValueError(f"utc_ts out of plausible UTC range: {value}")
    dt = datetime.fromtimestamp(value, tz=UTC)
    return value, dt.strftime("%Y-%m-%dT%H:%M:%SZ"), dt.strftime("%Y-%m-%d")


def validate_utc_iso(
    utc_iso: Any,
    *,
    expected_ts: int | None = None,
) -> tuple[int, str, str]:
    """Validate strict UTC ISO-8601 (`YYYY-MM-DDTHH:MM:SSZ` or `+00:00`) -> `(ts, iso_z, day)`."""
    if not isinstance(utc_iso, str) or not utc_iso.strip():
        raise ValueError(f"utc_iso must be a non-empty string, got {utc_iso!r}")
    raw = utc_iso.strip()
    if not _STRICT_UTC_ISO_RE.match(raw):
        raise ValueError(
            f"utc_iso must match strict YYYY-MM-DDTHH:MM:SS(Z|+00:00) format: {raw!r}"
        )
    parse_str = f"{raw[:-1]}+00:00" if raw.endswith("Z") else raw
    try:
        dt = datetime.fromisoformat(parse_str)
    except ValueError as exc:
        raise ValueError(f"Invalid UTC ISO-8601 timestamp {raw!r}: {exc}") from exc
    if dt.tzinfo is None or dt.utcoffset() != UTC.utcoffset(None):
        raise ValueError(f"utc_iso must be strictly UTC (offset 0): {raw!r}")
    calc_ts = int(dt.timestamp())
    if calc_ts < _MIN_VALID_UTC_TS or calc_ts > _MAX_VALID_UTC_TS:
        raise ValueError(f"utc_iso timestamp out of plausible range: {raw!r}")
    if expected_ts is not None:
        if isinstance(expected_ts, bool) or not isinstance(expected_ts, int):
            raise ValueError(f"expected_ts must be int, got {expected_ts!r}")
        if calc_ts != expected_ts:
            raise ValueError(
                f"utc_iso {raw!r} (ts={calc_ts}) does not match utc_ts={expected_ts}"
            )
    canonical_iso = dt.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return calc_ts, canonical_iso, canonical_iso[:10]


def _validate_http_url(url: str | None) -> str:
    if not isinstance(url, str):
        raise ValueError(f"VERIFIED_T1 event requires valid http(s) source_url, got {url!r}")
    norm = url.strip()
    if not norm or any(ch.isspace() for ch in norm):
        raise ValueError(f"VERIFIED_T1 event requires valid http(s) source_url, got {url!r}")
    parsed = urlparse(norm)
    host = parsed.hostname or ""
    host_labels = host.split(".")
    if (
        parsed.scheme not in ("https", "http")
        or not parsed.netloc
        or "." not in host
        or any(not lbl for lbl in host_labels)
    ):
        raise ValueError(
            f"VERIFIED_T1 event requires http(s) source_url with valid host, got {url!r}"
        )
    return norm


def validate_verification_status(
    status: Any,
    *,
    source_agency: str | None = None,
    source_url: str | None = None,
) -> str:
    """Validate T1 verification status and require primary agency/URL for VERIFIED_T1."""
    if not isinstance(status, str):
        raise ValueError(f"verification_status must be a string, got {status!r}")
    norm = status.strip()
    if norm not in ALLOWED_VERIFICATION_STATUSES:
        raise ValueError(
            f"Unsupported verification_status {status!r}; "
            f"allowed={sorted(ALLOWED_VERIFICATION_STATUSES)}"
        )
    if norm == "VERIFIED_T1":
        if not source_agency or not source_agency.strip():
            raise ValueError("VERIFIED_T1 event requires non-empty source_agency")
        _validate_http_url(source_url)
    return norm


def _default_blackout_for_event(ccy: str, event_label: str, confidence: str | None) -> int:
    label_up = event_label.upper()
    if ccy == "JPY" and (
        "EST03UTC" in label_up
        or "BOJ" in label_up
        or (confidence is not None and confidence.strip().upper() == "TIME_ESTIMATED")
    ):
        return BOJ_VARIABLE_BLACKOUT_SEC
    return DEFAULT_BLACKOUT_SEC


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"Expected optional string, got {type(value).__name__}")
    stripped = value.strip()
    return stripped or None


def _parse_event_id(ev: dict[str, Any]) -> str | None:
    has_event_id = "event_id" in ev and ev["event_id"] is not None
    has_id = "id" in ev and ev["id"] is not None
    if has_event_id and has_id:
        eid_a = _optional_str(ev["event_id"])
        eid_b = _optional_str(ev["id"])
        if eid_a != eid_b:
            raise ValueError(f"Conflicting event_id={eid_a!r} vs id={eid_b!r}")
        return eid_a
    if has_event_id:
        return _optional_str(ev["event_id"])
    if has_id:
        return _optional_str(ev["id"])
    return None


def _ensure_non_empty_and_unique(events: Sequence[RedNewsEvent], *, source_label: str) -> None:
    if not events:
        raise ValueError(f"Empty red-news calendar (0 events): {source_label}")
    seen_triples: set[tuple[int, str, str]] = set()
    seen_ids: set[str] = set()
    for ev in events:
        triple = (ev.utc_ts, ev.ccy, ev.event)
        if triple in seen_triples:
            raise ValueError(
                f"Duplicate calendar event in {source_label}: "
                f"utc_iso={ev.utc_iso}, ccy={ev.ccy}, event={ev.event!r}"
            )
        seen_triples.add(triple)
        if ev.event_id is not None:
            if ev.event_id in seen_ids:
                raise ValueError(
                    f"Duplicate event_id in {source_label}: {ev.event_id!r}"
                )
            seen_ids.add(ev.event_id)


def _parse_event_dict(
    ev: dict[str, Any],
    *,
    schema_format: str,
    day_key: str | None = None,
) -> RedNewsEvent:
    if not isinstance(ev, dict):
        raise ValueError(f"Calendar event entry must be an object, got {type(ev).__name__}")

    ccy = validate_currency(ev.get("ccy"))

    raw_ts = ev.get("utc_ts")
    raw_iso = ev.get("utc_iso")
    if raw_iso is not None:
        exp_ts = raw_ts if raw_ts is not None else None
        utc_ts, utc_iso, utc_day = validate_utc_iso(raw_iso, expected_ts=exp_ts)
    elif raw_ts is not None:
        utc_ts, utc_iso, utc_day = validate_utc_ts(raw_ts)
    else:
        raise ValueError("Calendar event must provide 'utc_iso' and/or 'utc_ts'")

    if day_key is not None and day_key != utc_day:
        raise ValueError(
            f"events_by_day key {day_key!r} does not match UTC date {utc_day!r} of ts={utc_ts}"
        )

    raw_event = ev.get("event")
    if raw_event is None:
        event_label = "US_MACRO" if ccy == "USD" else f"{ccy}_MACRO"
    elif isinstance(raw_event, str) and raw_event.strip():
        event_label = raw_event.strip()
    else:
        raise ValueError(f"Invalid event label: {raw_event!r}")

    confidence = _optional_str(ev.get("confidence"))
    raw_blackout = ev.get("blackout_sec")
    blackout_sec = (
        validate_blackout_sec(raw_blackout)
        if raw_blackout is not None
        else _default_blackout_for_event(ccy, event_label, confidence)
    )

    event_id = _parse_event_id(ev)
    source_agency = _optional_str(ev.get("source_agency") or ev.get("source"))
    source_url = _optional_str(ev.get("source_url"))

    raw_verif = ev.get("verification_status")
    if raw_verif is not None:
        verification_status = validate_verification_status(
            raw_verif,
            source_agency=source_agency,
            source_url=source_url,
        )
    else:
        verification_status = "UNKNOWN_UNVERIFIED"

    return RedNewsEvent(
        utc_ts=utc_ts,
        utc_iso=utc_iso,
        utc_day=utc_day,
        ccy=ccy,
        event=event_label,
        blackout_sec=blackout_sec,
        event_id=event_id,
        source_agency=source_agency,
        source_url=source_url,
        verification_status=verification_status,
        confidence=confidence,
        local_date=_optional_str(ev.get("local_date")),
        local_time=_optional_str(ev.get("local_time")),
        tz_name=_optional_str(ev.get("tz_name")),
        schema_format=schema_format,
    )


def load_csv_events(path: str | Path) -> list[RedNewsEvent]:
    """Load and validate a 3-column UTC red-news CSV (`utc_ts,ccy,event`)."""
    csv_path = Path(path)
    if not csv_path.exists():
        raise FileNotFoundError(f"Red-news CSV not found: {csv_path}")

    events: list[RedNewsEvent] = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.reader(handle)
        header = next(reader, None)
        if header is None or [c.strip() for c in header[:3]] != ["utc_ts", "ccy", "event"]:
            raise ValueError(f"Invalid red-news CSV header in {csv_path}: {header!r}")
        for lineno, row in enumerate(reader, start=2):
            if not row or not any(cell.strip() for cell in row):
                continue
            if len(row) < 3:
                raise ValueError(f"{csv_path}:{lineno}: expected 3 columns, got {row!r}")
            try:
                ts_int = int(row[0].strip())
            except ValueError as exc:
                raise ValueError(f"{csv_path}:{lineno}: invalid utc_ts {row[0]!r}") from exc
            utc_ts, utc_iso, utc_day = validate_utc_ts(ts_int)
            ccy = validate_currency(row[1])
            label = row[2].strip()
            if not label:
                raise ValueError(f"{csv_path}:{lineno}: empty event label")
            blackout_sec = _default_blackout_for_event(ccy, label, None)
            events.append(
                RedNewsEvent(
                    utc_ts=utc_ts,
                    utc_iso=utc_iso,
                    utc_day=utc_day,
                    ccy=ccy,
                    event=label,
                    blackout_sec=blackout_sec,
                    verification_status="UNKNOWN_UNVERIFIED",
                    schema_format="csv",
                )
            )

    _ensure_non_empty_and_unique(events, source_label=str(csv_path))
    events.sort(key=lambda e: (e.utc_ts, e.ccy, e.event))
    return events


def load_calendar_events(path: str | Path) -> list[RedNewsEvent]:
    """Unified fail-closed loader for legacy `events_by_day`, list `events`, and UTC CSV."""
    cal_path = Path(path)
    if not cal_path.exists():
        raise FileNotFoundError(f"Red-news calendar file not found: {cal_path}")

    if cal_path.suffix.lower() == ".csv":
        return load_csv_events(cal_path)

    raw = json.loads(cal_path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Calendar JSON root must be an object in {cal_path}")

    has_events = "events" in raw
    has_by_day = "events_by_day" in raw
    if has_events and has_by_day:
        raise ValueError(
            f"Ambiguous dual-schema calendar in {cal_path}: contains both 'events' and 'events_by_day'"
        )

    events: list[RedNewsEvent] = []
    if has_events:
        raw_events = raw["events"]
        if not isinstance(raw_events, list):
            raise ValueError(f"'events' must be a list in {cal_path}")
        for idx, item in enumerate(raw_events):
            try:
                events.append(_parse_event_dict(item, schema_format="events_list"))
            except ValueError as exc:
                raise ValueError(f"{cal_path}: events[{idx}]: {exc}") from exc
    elif has_by_day:
        by_day = raw["events_by_day"]
        if not isinstance(by_day, dict):
            raise ValueError(f"'events_by_day' must be a dict in {cal_path}")
        for day_key, day_items in by_day.items():
            if not isinstance(day_key, str) or not isinstance(day_items, list):
                raise ValueError(
                    f"{cal_path}: invalid events_by_day entry for key {day_key!r}"
                )
            for idx, item in enumerate(day_items):
                try:
                    events.append(
                        _parse_event_dict(
                            item,
                            schema_format="events_by_day",
                            day_key=day_key,
                        )
                    )
                except ValueError as exc:
                    raise ValueError(
                        f"{cal_path}: events_by_day[{day_key!r}][{idx}]: {exc}"
                    ) from exc
    else:
        raise ValueError(
            f"Unsupported calendar schema in {cal_path}: expected 'events' or 'events_by_day'"
        )

    _ensure_non_empty_and_unique(events, source_label=str(cal_path))
    events.sort(key=lambda e: (e.utc_ts, e.ccy, e.event))
    return events


def load_calendar_events_by_day(path: str | Path) -> dict[str, list[tuple[int, str]]]:
    """Load any supported red-news calendar into legacy `{utc_day: [(utc_ts, ccy), ...]}` map."""
    grouped: dict[str, list[tuple[int, str]]] = {}
    for ev in load_calendar_events(path):
        grouped.setdefault(ev.utc_day, []).append((ev.utc_ts, ev.ccy))
    return dict(sorted(grouped.items()))


def summarize_calendar_events(events: Sequence[RedNewsEvent]) -> dict[str, Any]:
    """Compute per-year, per-currency, and verification coverage statistics."""
    by_year: dict[str, int] = {}
    by_ccy: dict[str, int] = {}
    by_year_ccy: dict[str, dict[str, int]] = {}
    verification_counts: dict[str, int] = {}

    for ev in events:
        yr = ev.utc_day[:4]
        by_year[yr] = by_year.get(yr, 0) + 1
        by_ccy[ev.ccy] = by_ccy.get(ev.ccy, 0) + 1
        yc = by_year_ccy.setdefault(yr, {})
        yc[ev.ccy] = yc.get(ev.ccy, 0) + 1
        verification_counts[ev.verification_status] = (
            verification_counts.get(ev.verification_status, 0) + 1
        )

    year_counts = list(by_year.values())
    avg_per_year = round(sum(year_counts) / len(year_counts), 2) if year_counts else 0.0
    return {
        "total_events": len(events),
        "currencies": sorted(by_ccy.keys()),
        "years": sorted(by_year.keys()),
        "by_year": dict(sorted(by_year.items())),
        "by_ccy": dict(sorted(by_ccy.items())),
        "by_year_ccy": {y: dict(sorted(d.items())) for y, d in sorted(by_year_ccy.items())},
        "avg_events_per_year": avg_per_year,
        "min_events_per_year": min(year_counts) if year_counts else 0,
        "max_events_per_year": max(year_counts) if year_counts else 0,
        "verification_counts": dict(sorted(verification_counts.items())),
    }


def _resolve_events(
    source: str | Path | Sequence[RedNewsEvent],
    *,
    role: str,
) -> list[RedNewsEvent]:
    if isinstance(source, (str, Path)):
        return load_calendar_events(source)
    events = list(source)
    _ensure_non_empty_and_unique(events, source_label=role)
    return events


def get_calendar_coverage_report(
    dev_cal: str | Path | Sequence[RedNewsEvent],
    live_csv: str | Path | Sequence[RedNewsEvent],
) -> dict[str, Any]:
    """Compare Dev backtest calendar coverage against Live CSV and emit mandatory gap warnings.

    Emits `BACKTEST_USD32_VS_LIVE140_GAP` whenever `dev_cal` uses USD-only (`<= 35` events/yr)
    while `live_csv` enforces multi-currency schedules (`~97-140` events/yr).
    """
    dev_events = _resolve_events(dev_cal, role="dev_cal")
    live_events = _resolve_events(live_csv, role="live_csv")

    dev_summary = summarize_calendar_events(dev_events)
    live_summary = summarize_calendar_events(live_events)

    # Identify live multi-currency years (e.g. 2026=97, 2027=140 across 6 ccys)
    multi_ccy_year_keys = [
        yr
        for yr, ccy_map in live_summary["by_year_ccy"].items()
        if len(ccy_map) >= 2
    ]
    ref_years = multi_ccy_year_keys if multi_ccy_year_keys else live_summary["years"]
    live_ref_counts = [live_summary["by_year"][yr] for yr in ref_years]
    live_ref_ccys: set[str] = set()
    for yr in ref_years:
        live_ref_ccys.update(live_summary["by_year_ccy"][yr].keys())

    live_ref_min = min(live_ref_counts) if live_ref_counts else 0
    live_ref_max = max(live_ref_counts) if live_ref_counts else 0
    live_ref_avg = (
        round(sum(live_ref_counts) / len(live_ref_counts), 2) if live_ref_counts else 0.0
    )

    dev_ccys = set(dev_summary["currencies"])
    dev_is_usd_only = len(dev_ccys) > 0 and dev_ccys <= {"USD"}
    live_is_multi_ccy = len(live_ref_ccys) >= 2

    warnings: list[str] = []
    if (
        dev_is_usd_only
        and dev_summary["max_events_per_year"] <= DEV_USD_ONLY_MAX_PER_YEAR
        and live_is_multi_ccy
        and live_ref_max >= LIVE_MULTI_CCY_MIN_PER_YEAR
    ):
        warnings.append(GAP_WARNING_FLAG)
    elif (
        not dev_is_usd_only
        and live_is_multi_ccy
        and live_ref_max >= LIVE_MULTI_CCY_MIN_PER_YEAR
        and dev_summary["avg_events_per_year"] < float(live_ref_max) * 0.85
    ):
        warnings.append(PARTIAL_MACRO_GAP_FLAG)

    return {
        "schema": "naqex-red-news-coverage-report-v1",
        "dev": dev_summary,
        "live": live_summary,
        "live_multi_ccy_reference": {
            "years": ref_years,
            "currencies": sorted(live_ref_ccys),
            "min_events_per_year": live_ref_min,
            "max_events_per_year": live_ref_max,
            "avg_events_per_year": live_ref_avg,
        },
        "dev_is_usd_only": dev_is_usd_only,
        "missing_currencies_in_dev": sorted(live_ref_ccys - dev_ccys),
        "coverage_ratio_vs_live_peak": (
            round(dev_summary["avg_events_per_year"] / float(live_ref_max), 4)
            if live_ref_max > 0
            else 0.0
        ),
        "warnings": warnings,
        "has_usd32_vs_live140_gap": GAP_WARNING_FLAG in warnings,
    }


def verify_production_csv_immutability(
    csv_path: str | Path,
    *,
    expected_sha256: str = PROD_RED_NEWS_CSV_SHA256,
    expected_events: int = PROD_RED_NEWS_CSV_EXPECTED_EVENTS,
) -> dict[str, Any]:
    """Verify live `naqex_red_news_utc.csv` remains LF-only, 492 events, and SHA-256 locked."""
    path = Path(csv_path)
    raw_bytes = path.read_bytes()
    actual_sha = hashlib.sha256(raw_bytes).hexdigest()
    lf_only = b"\r" not in raw_bytes
    events = load_csv_events(path)
    ok = (
        lf_only
        and actual_sha.lower() == expected_sha256.lower()
        and len(events) == expected_events
    )
    return {
        "ok": ok,
        "csv_path": str(path),
        "lf_only": lf_only,
        "sha256": actual_sha,
        "expected_sha256": expected_sha256,
        "event_count": len(events),
        "expected_events": expected_events,
    }
