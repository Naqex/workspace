"""Deterministic Multi-Currency Official Red-News Calendar Builder & Validator (2018-2027).

Merges:
  1. Frozen `red_news_official_2018_2024.json` (224 USD Dev rows — NEVER modified)
  2. Frozen `red_news_official_2025_2026.json` (31 USD 2025 + 32 USD 2026 rows — NEVER modified)
  3. Primary-source `red_news_official_2026_2027_multi_ccy.json` (4 currencies: USD, GBP, EUR, JPY
     covering late-2026 Nov-Dec and full-year 2027 across FOMC, FOMC Press Conf, US NFP, US CPI,
     US PPI, US Retail Sales, US Core PCE / GDP, BoE Rate, UK CPI, ECB Rate, ECB Press Conf, BoJ Rate)

Outputs strictly sorted, `(utc_ts, ccy)`-deduplicated MQL5 CSV:
  `tooling/ai-engines/exports/Files/naqex_red_news_utc.csv` (header: `utc_ts,ccy,event`)

Strictly offline & deterministic (OrderSend = 0, Holdout 2025+ untouched).
"""

from __future__ import annotations

import argparse
import csv
from datetime import date, datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import sys
from typing import Any

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = AI_ENGINES_DIR.parents[1]
CALENDARS_DIR = AI_ENGINES_DIR / "configs/calendars"
EXPORTS_DIR = AI_ENGINES_DIR / "exports"

DEFAULT_CAL_1824 = CALENDARS_DIR / "red_news_official_2018_2024.json"
DEFAULT_CAL_2526 = CALENDARS_DIR / "red_news_official_2025_2026.json"
DEFAULT_CAL_2627 = CALENDARS_DIR / "red_news_official_2026_2027_multi_ccy.json"
DEFAULT_OUT_CSV = EXPORTS_DIR / "Files/naqex_red_news_utc.csv"

ALLOWED_CCYS = {"USD", "GBP", "EUR", "JPY", "AUD", "CAD"}
ALLOWED_CONFIDENCE = {"OFFICIAL_CONFIRMED", "OFFICIAL_TENTATIVE", "TIME_ESTIMATED"}
MAX_CSV_BYTES = 200_000


def _nth_weekday_of_month(year: int, month: int, weekday: int, nth: int) -> date:
    """Return nth weekday (Mon=0..Sun=6) of given year/month."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _last_weekday_of_month(year: int, month: int, weekday: int) -> date:
    """Return last weekday (Mon=0..Sun=6) of given year/month."""
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    offset = (last_day.weekday() - weekday) % 7
    return last_day - timedelta(days=offset)


def local_to_utc_offset_hours(tz_name: str, local_dt: datetime) -> int:
    """Deterministic UTC offset (hours) for NY/Toronto, London, Berlin, Tokyo, and Sydney."""
    y = local_dt.year
    if tz_name == "UTC":
        return 0
    if tz_name == "Asia/Tokyo":
        return 9
    if tz_name in ("America/New_York", "America/Toronto"):
        # US/Canada Eastern DST: 2nd Sunday of March 02:00 local -> 1st Sunday of November 02:00 local
        dst_start = datetime.combine(_nth_weekday_of_month(y, 3, 6, 2), datetime.min.time()).replace(hour=2)
        dst_end = datetime.combine(_nth_weekday_of_month(y, 11, 6, 1), datetime.min.time()).replace(hour=2)
        return -4 if dst_start <= local_dt < dst_end else -5
    if tz_name == "Australia/Sydney":
        # NSW Southern-Hemisphere DST: 1st Sunday of October 02:00 AEST -> 1st Sunday of April 03:00 AEDT
        dst_end_apr = datetime.combine(_nth_weekday_of_month(y, 4, 6, 1), datetime.min.time()).replace(hour=3)
        dst_start_oct = datetime.combine(_nth_weekday_of_month(y, 10, 6, 1), datetime.min.time()).replace(hour=2)
        return 10 if dst_end_apr <= local_dt < dst_start_oct else 11
    if tz_name in ("Europe/London", "Europe/Berlin"):
        base_off = 0 if tz_name == "Europe/London" else 1
        # EU/UK DST: last Sunday of March 01:00 UTC -> last Sunday of October 01:00 UTC
        start_d = _last_weekday_of_month(y, 3, 6)
        end_d = _last_weekday_of_month(y, 10, 6)
        dst_start_local = datetime.combine(start_d, datetime.min.time()).replace(hour=1 + base_off)
        dst_end_local = datetime.combine(end_d, datetime.min.time()).replace(hour=1 + base_off + 1)
        return base_off + 1 if dst_start_local <= local_dt < dst_end_local else base_off
    raise ValueError(f"Unsupported timezone name: {tz_name!r}")


def compute_utc_ts(local_date: str, local_time: str, tz_name: str) -> tuple[int, str]:
    """Convert `YYYY-MM-DD`, `HH:MM`, and `tz_name` deterministically into `(utc_ts, utc_iso)`."""
    local_dt = datetime.strptime(f"{local_date} {local_time}", "%Y-%m-%d %H:%M")
    off_h = local_to_utc_offset_hours(tz_name, local_dt)
    utc_dt = (local_dt - timedelta(hours=off_h)).replace(tzinfo=timezone.utc)
    return int(utc_dt.timestamp()), utc_dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_frozen_1824(path: Path) -> list[tuple[int, str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[int, str, str]] = []
    for day_events in data.get("events_by_day", {}).values():
        for ev in day_events:
            rows.append((int(ev["utc_ts"]), str(ev["ccy"]).strip().upper(), str(ev.get("event", "US_MACRO")).strip()))
    return rows


def _load_frozen_2526(path: Path) -> list[tuple[int, str, str]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows: list[tuple[int, str, str]] = []
    for day_events in data.get("events_by_day", {}).values():
        for ev in day_events:
            rows.append((int(ev["utc_ts"]), str(ev["ccy"]).strip().upper(), str(ev["event"]).strip()))
    return rows


def load_and_validate_multi_ccy_json(path: Path) -> tuple[list[tuple[int, str, str]], list[str]]:
    """Load `red_news_official_2026_2027_multi_ccy.json` and verify every timestamp, weekday, and schema field."""
    errors: list[str] = []
    rows: list[tuple[int, str, str]] = []
    if not path.exists():
        return rows, [f"Missing multi-ccy calendar JSON: {path}"]
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("schema") != "naqex-red-news-multi-ccy-2026-2027-v1":
        errors.append(f"Unexpected schema: {data.get('schema')!r}")
    events = data.get("events")
    if not isinstance(events, list) or not events:
        return rows, [f"Missing or empty 'events' list in {path}"]

    for idx, ev in enumerate(events):
        try:
            ldate = str(ev["local_date"]).strip()
            ltime = str(ev["local_time"]).strip()
            tz_name = str(ev["tz_name"]).strip()
            ccy = str(ev["ccy"]).strip().upper()
            label = str(ev["event"]).strip()
            conf = str(ev.get("confidence", "")).strip()
            stored_ts = int(ev["utc_ts"])
            stored_iso = str(ev["utc_iso"]).strip()
        except Exception as exc:
            errors.append(f"Event[{idx}] malformed fields: {exc}")
            continue

        if ccy not in ALLOWED_CCYS:
            errors.append(f"Event[{idx}] unsupported ccy {ccy!r}")
        if not label or "," in label or " " in label:
            errors.append(f"Event[{idx}] invalid CSV event label {label!r}")
        if conf not in ALLOWED_CONFIDENCE:
            errors.append(f"Event[{idx}] invalid confidence {conf!r}")
        if conf == "OFFICIAL_TENTATIVE" and "TENTATIVE" not in label:
            errors.append(f"Event[{idx}] OFFICIAL_TENTATIVE event must carry TENTATIVE tag: {label}")
        if conf == "TIME_ESTIMATED" and "EST" not in label:
            errors.append(f"Event[{idx}] TIME_ESTIMATED event must carry EST tag: {label}")

        calc_ts, calc_iso = compute_utc_ts(ldate, ltime, tz_name)
        if stored_ts != calc_ts or stored_iso != calc_iso:
            errors.append(
                f"Event[{idx}] {label} ({ldate} {ltime} {tz_name}): stored ({stored_ts}, {stored_iso}) != computed ({calc_ts}, {calc_iso})"
            )
        dt_utc = datetime.fromtimestamp(calc_ts, timezone.utc)
        if dt_utc.weekday() >= 5:
            errors.append(f"Event[{idx}] {label} falls on weekend UTC: {calc_iso}")
        if dt_utc.year not in (2026, 2027):
            errors.append(f"Event[{idx}] {label} outside 2026-2027 window: {calc_iso}")
        rows.append((calc_ts, ccy, label))

    return rows, errors


def merge_and_deduplicate_events(
    rows_1824: list[tuple[int, str, str]],
    rows_2526: list[tuple[int, str, str]],
    rows_2627: list[tuple[int, str, str]],
) -> tuple[list[tuple[int, str, str]], list[dict[str, Any]]]:
    """Merge all layers deterministically and deduplicate strictly by `(utc_ts, ccy)`."""
    merged: dict[tuple[int, str], list[str]] = {}
    merges_log: list[dict[str, Any]] = []

    for src_name, batch in (
        ("frozen_2018_2024", rows_1824),
        ("frozen_2025_2026", rows_2526),
        ("multi_ccy_2026_2027", rows_2627),
    ):
        for ts, ccy, label in batch:
            key = (int(ts), str(ccy).strip().upper())
            lbl = str(label).strip()
            existing = merged.setdefault(key, [])
            if lbl not in existing:
                existing.append(lbl)

    final_rows: list[tuple[int, str, str]] = []
    for (ts, ccy), labels in sorted(merged.items(), key=lambda kv: (kv[0][0], kv[0][1])):
        if len(labels) == 1:
            final_label = labels[0]
        else:
            # Join distinct simultaneous releases for the same currency (e.g., US PPI + US Retail Sales at 08:30 ET)
            final_label = "+".join(labels)
            merges_log.append({
                "utc_ts": ts,
                "utc_iso": datetime.fromtimestamp(ts, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
                "ccy": ccy,
                "merged_events": labels,
                "combined_label": final_label,
            })
        final_rows.append((ts, ccy, final_label))

    return final_rows, merges_log


def render_csv_text(rows: list[tuple[int, str, str]]) -> str:
    lines = ["utc_ts,ccy,event"]
    for ts, ccy, event in rows:
        lines.append(f"{ts},{ccy},{event}")
    return "\n".join(lines) + "\n"


def summarize_rows(rows: list[tuple[int, str, str]]) -> dict[str, Any]:
    by_year: dict[str, int] = {}
    by_year_ccy: dict[str, dict[str, int]] = {}
    by_ccy: dict[str, int] = {}
    for ts, ccy, _ in rows:
        yr = str(datetime.fromtimestamp(ts, timezone.utc).year)
        by_year[yr] = by_year.get(yr, 0) + 1
        by_ccy[ccy] = by_ccy.get(ccy, 0) + 1
        yc = by_year_ccy.setdefault(yr, {})
        yc[ccy] = yc.get(ccy, 0) + 1
    return {
        "total_rows": len(rows),
        "by_year": dict(sorted(by_year.items())),
        "by_ccy": dict(sorted(by_ccy.items())),
        "by_year_ccy": {y: dict(sorted(d.items())) for y, d in sorted(by_year_ccy.items())},
    }


def build_or_verify_calendar(
    *,
    cal_1824: Path = DEFAULT_CAL_1824,
    cal_2526: Path = DEFAULT_CAL_2526,
    cal_2627: Path = DEFAULT_CAL_2627,
    out_csv: Path = DEFAULT_OUT_CSV,
    write: bool = False,
) -> dict[str, Any]:
    """Validate sources, merge deterministically, optionally write CSV, and run full parity checks."""
    errors: list[str] = []
    rows_1824 = _load_frozen_1824(cal_1824)
    rows_2526 = _load_frozen_2526(cal_2526)
    rows_2627, json_errs = load_and_validate_multi_ccy_json(cal_2627)
    errors.extend(json_errs)

    if len(rows_1824) != 224:
        errors.append(f"Frozen 2018-2024 calendar row count drifted: {len(rows_1824)} != 224")

    merged_rows, merges_log = merge_and_deduplicate_events(rows_1824, rows_2526, rows_2627)
    csv_text = render_csv_text(merged_rows)
    csv_bytes = csv_text.encode("utf-8")

    if len(csv_bytes) >= MAX_CSV_BYTES:
        errors.append(f"Rendered CSV exceeds {MAX_CSV_BYTES} byte limit: {len(csv_bytes)}")

    # Verify strict sorting and unique (utc_ts, ccy) keys
    keys = [(r[0], r[1]) for r in merged_rows]
    if len(keys) != len(set(keys)):
        errors.append("Duplicate (utc_ts, ccy) pair detected after merge")
    tss = [r[0] for r in merged_rows]
    if tss != sorted(tss):
        errors.append("Merged CSV timestamps are not sorted ascending")

    if write and not errors:
        out_csv.parent.mkdir(parents=True, exist_ok=True)
        out_csv.write_bytes(csv_bytes)

    disk_matches = False
    if out_csv.exists():
        disk_bytes = out_csv.read_bytes().replace(b"\r\n", b"\n")
        disk_matches = (disk_bytes == csv_bytes)
        if not disk_matches:
            errors.append(f"On-disk {out_csv} does not match deterministic build output (re-run with --build)")
    else:
        errors.append(f"Output CSV missing: {out_csv}")

    # Cross-check with mql5_parity_checker.verify_red_news_csv()
    parity_res: dict[str, Any] = {}
    if out_csv.exists():
        if str(EXPORTS_DIR) not in sys.path:
            sys.path.insert(0, str(EXPORTS_DIR))
        import mql5_parity_checker as parity  # noqa: E402

        parity_res = parity.verify_red_news_csv(out_csv)
        if not parity_res.get("ok"):
            errors.extend(parity_res.get("errors", ["mql5_parity_checker.verify_red_news_csv failed"]))

    summary = summarize_rows(merged_rows)
    # Enforce 4-ccy presence in both 2026 and 2027
    for yr in ("2026", "2027"):
        ccys_in_yr = set(summary["by_year_ccy"].get(yr, {}).keys())
        missing = sorted(ALLOWED_CCYS - ccys_in_yr)
        if missing:
            errors.append(f"Year {yr} missing required currencies: {missing}")

    return {
        "schema": "naqex-red-news-build-report-v1",
        "ok": len(errors) == 0,
        "wrote_csv": bool(write and len(errors) == 0),
        "disk_matches_deterministic_build": disk_matches,
        "out_csv": str(out_csv),
        "csv_bytes": len(csv_bytes),
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "summary": summary,
        "simultaneous_merges": merges_log,
        "parity_check": parity_res,
        "errors": errors,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Build & verify deterministic 4-currency Naqex red-news CSV (2018-2027).")
    ap.add_argument("--build", action="store_true", help="Write deterministic merged CSV to exports/Files/naqex_red_news_utc.csv.")
    ap.add_argument("--verify", action="store_true", help="Verify JSON schedules and on-disk CSV parity.")
    ap.add_argument("--json", action="store_true", help="Output JSON report.")
    ap.add_argument("--out-csv", type=Path, default=DEFAULT_OUT_CSV, help="Override output CSV path.")
    args = ap.parse_args(argv)

    rep = build_or_verify_calendar(out_csv=args.out_csv, write=args.build)
    if args.json:
        print(json.dumps(rep, indent=2, ensure_ascii=False))
    else:
        status = "PASS" if rep["ok"] else "FAIL"
        print(f"Red-News Calendar Builder/Verify: {status} | rows={rep['summary']['total_rows']} | bytes={rep['csv_bytes']} | sha256={rep['csv_sha256'][:16]}...")
        for yr, ccys in rep["summary"]["by_year_ccy"].items():
            total_y = rep["summary"]["by_year"][yr]
            parts = ", ".join(f"{c}={n}" for c, n in ccys.items())
            print(f"  {yr}: {total_y:3d} rows ({parts})")
        if rep["simultaneous_merges"]:
            print(f"  Deduplicated simultaneous (utc_ts, ccy) pairs: {len(rep['simultaneous_merges'])}")
            for m in rep["simultaneous_merges"]:
                print(f"    - {m['utc_iso']} {m['ccy']}: {m['combined_label']}")
        for err in rep["errors"]:
            print(f"  ERR: {err}")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
