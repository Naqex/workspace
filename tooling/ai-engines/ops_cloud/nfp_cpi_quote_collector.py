"""Read-Only QUOTE_ONLY Collector for US NFP (04/12/2026) & US CPI (10/12/2026) — 20:30 ICT.

STRICT SAFETY INVARIANTS (NEVER VIOLATE):
- `OrderSend = 0` ALWAYS: never imports/invokes `mt5.order_send` or `mt5.order_check`.
- `record_tier` is hard-locked to `"QUOTE_ONLY"` (never conflates quote overshoots with broker SL fills).
- Outputs the exact 23-column CSV schema from `NFP-CPI-READONLY-CAPTURE-TEMPLATE.md`.
- Fail-closed preflight & capture guards:
  * Exact red-news calendar match (`f"{release_utc_ts},USD,{csv_code}"`) — rejects wrong event codes.
  * Strict NTP drift gate (`offset_ms is not None` and `abs(offset_ms) < 1000.0`).
  * Exact account login/server verification, `terminal_info.connected == True`, and strict non-None
    flat-account check (`positions_total == 0` and `orders_total == 0`).
  * Order-preserving same-millisecond tick cursor (zero same-ms drops, zero duplicates).
  * Event-appropriate default duration (`1200.0`s for US_NFP/US_CPI, `5.0`s for SMOKE_PREFLIGHT).
  * Post-capture window completeness check (`CORE4_SYMBOLS` + `IMPACT_CORE` coverage for NFP/CPI).
"""

from __future__ import annotations

import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import hashlib
import json
import logging
import math
from pathlib import Path
import re
import subprocess
import time
from typing import Any

logger = logging.getLogger(__name__)

RECORD_TIER = "QUOTE_ONLY"
ORDER_SEND_COUNT = 0
NTP_MAX_ABS_OFFSET_MS = 1000.0
MIN_EVENT_WINDOW_SPAN_SEC = 300.0
DEFAULT_RED_NEWS_CSV = Path(__file__).resolve().parents[1] / "exports/Files/naqex_red_news_utc.csv"

CORE4_SYMBOLS: tuple[str, ...] = ("US100.cash", "USDJPY", "GBPUSD", "EURJPY")
AUX4_SYMBOLS: tuple[str, ...] = ("US500.cash", "EURUSD", "AUDUSD", "USDCAD")
ALL8_SYMBOLS: tuple[str, ...] = CORE4_SYMBOLS + AUX4_SYMBOLS
WINDOW_PHASES: tuple[str, ...] = ("PRE_EVENT", "IMPACT_CORE", "POST_NORMALIZE")
EVENT_REQUIRING_IMPACT_CORE: frozenset[str] = frozenset({"US_NFP_20261204", "US_CPI_20261210"})

EVENTS: dict[str, dict[str, Any]] = {
    "US_NFP_20261204": {
        "event_id": "US_NFP_20261204",
        "csv_code": "US_NFP",
        "release_utc_ts": 1796391000,   # 2026-12-04 13:30:00 UTC = 20:30:00 ICT
        "release_iso_utc": "2026-12-04T13:30:00.000Z",
        "window_start_offset_s": -300,  # 13:25:00 UTC
        "impact_start_offset_s": -30,   # 13:29:30 UTC
        "impact_end_offset_s": 300,     # 13:35:00 UTC
        "window_end_offset_s": 900,     # 13:45:00 UTC
        "default_duration_sec": 1200.0, # 20 minutes: 20:25..20:45 ICT
    },
    "US_CPI_20261210": {
        "event_id": "US_CPI_20261210",
        "csv_code": "US_CPI",
        "release_utc_ts": 1796909400,   # 2026-12-10 13:30:00 UTC = 20:30:00 ICT
        "release_iso_utc": "2026-12-10T13:30:00.000Z",
        "window_start_offset_s": -300,
        "impact_start_offset_s": -30,
        "impact_end_offset_s": 300,
        "window_end_offset_s": 900,
        "default_duration_sec": 1200.0, # 20 minutes: 20:25..20:45 ICT
    },
    "SMOKE_PREFLIGHT": {
        "event_id": "SMOKE_PREFLIGHT",
        "csv_code": "SMOKE",
        "release_utc_ts": 0,            # Dynamically anchored to current UTC time
        "release_iso_utc": "DYNAMIC_NOW",
        "window_start_offset_s": -300,
        "impact_start_offset_s": -30,
        "impact_end_offset_s": 300,
        "window_end_offset_s": 900,
        "default_duration_sec": 5.0,    # 5 seconds ONLY for smoke preflight
    },
}

CSV_COLUMNS: tuple[str, ...] = (
    "record_tier",
    "event_id",
    "utc_ts_ms",
    "utc_iso_ms",
    "server_tick_msc",
    "local_recv_msc",
    "ntp_offset_ms",
    "account_alias",
    "server",
    "symbol",
    "bid",
    "ask",
    "mid",
    "spread_pts",
    "spread_bps",
    "point",
    "tick_flags",
    "delta_bid_pts",
    "delta_ask_pts",
    "inter_tick_gap_ms",
    "seconds_from_release",
    "window_phase",
    "order_send_count",
)


def default_duration_sec(event_id: str) -> float:
    """Return event-appropriate capture duration (1200.0s for NFP/CPI, 5.0s for SMOKE_PREFLIGHT)."""
    if event_id not in EVENTS:
        raise ValueError(f"Unknown event_id: {event_id!r}")
    return float(EVENTS[event_id]["default_duration_sec"])


def classify_window_phase(seconds_from_release: float) -> str:
    if seconds_from_release < -30.0:
        return "PRE_EVENT"
    if seconds_from_release <= 300.0:
        return "IMPACT_CORE"
    return "POST_NORMALIZE"


def verify_red_news_calendar(csv_path: Path) -> dict[str, Any]:
    """Verify both Dec-2026 BLS release timestamps and exact event codes exist in `naqex_red_news_utc.csv`."""
    csv_path = Path(csv_path)
    if not csv_path.exists():
        return {"ok": False, "reason": f"missing {csv_path}", "csv_path": str(csv_path), "found": {}}
    lines = [l.strip() for l in csv_path.read_text(encoding="utf-8-sig").splitlines() if l.strip()]
    found: dict[str, bool] = {}
    expected: dict[str, str] = {}
    for ev_id in ("US_NFP_20261204", "US_CPI_20261210"):
        ev = EVENTS[ev_id]
        needle = f"{ev['release_utc_ts']},USD,{ev['csv_code']}"
        expected[ev_id] = needle
        found[ev_id] = any(l == needle for l in lines)
    return {
        "ok": all(found.values()),
        "csv_path": str(csv_path),
        "found": found,
        "expected": expected,
    }


def is_ntp_ok(ntp: dict[str, Any] | None, max_abs_offset_ms: float = NTP_MAX_ABS_OFFSET_MS) -> bool:
    """Return True iff NTP check succeeded with finite offset strictly within `max_abs_offset_ms`."""
    if not isinstance(ntp, dict):
        return False
    if not bool(ntp.get("ok")):
        return False
    off = ntp.get("offset_ms")
    if off is None or isinstance(off, bool):
        return False
    try:
        val = float(off)
    except (TypeError, ValueError):
        return False
    if not math.isfinite(val):
        return False
    return abs(val) < float(max_abs_offset_ms)


def measure_ntp_offset_ms(ntp_host: str = "time.cloudflare.com", samples: int = 3) -> dict[str, Any]:
    """Measure Windows clock offset via `w32tm /stripchart` (read-only)."""
    try:
        proc = subprocess.run(
            ["w32tm", "/stripchart", f"/computer:{ntp_host}", f"/samples:{samples}", "/dataonly"],
            capture_output=True,
            text=True,
            timeout=12,
        )
        offsets_ms: list[float] = []
        for m in re.finditer(r"([+-]\d+(?:\.\d+)?)s", proc.stdout):
            offsets_ms.append(float(m.group(1)) * 1000.0)
        if offsets_ms:
            med = sorted(offsets_ms)[len(offsets_ms) // 2]
            return {
                "ok": abs(med) < NTP_MAX_ABS_OFFSET_MS,
                "ntp_host": ntp_host,
                "offset_ms": round(med, 2),
                "samples_ms": [round(x, 2) for x in offsets_ms],
                "threshold_ms": NTP_MAX_ABS_OFFSET_MS,
            }
        return {
            "ok": False,
            "ntp_host": ntp_host,
            "offset_ms": None,
            "threshold_ms": NTP_MAX_ABS_OFFSET_MS,
            "raw": proc.stdout.strip()[:200],
        }
    except Exception as exc:
        return {
            "ok": False,
            "ntp_host": ntp_host,
            "offset_ms": None,
            "threshold_ms": NTP_MAX_ABS_OFFSET_MS,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _extract_tick_fields(tk: Any) -> tuple[int, float, float, int]:
    """Extract `(time_msc, bid, ask, flags)` from either structured/dict tick or attribute object."""
    if isinstance(tk, dict):
        return int(tk["time_msc"]), float(tk["bid"]), float(tk["ask"]), int(tk["flags"])
    try:
        return int(tk["time_msc"]), float(tk["bid"]), float(tk["ask"]), int(tk["flags"])
    except (TypeError, KeyError, IndexError):
        return int(tk.time_msc), float(tk.bid), float(tk.ask), int(tk.flags)


def _tick_dedup_key(tm: int, bid: float, ask: float, flags: int) -> tuple[int, float, float, int]:
    return (int(tm), round(float(bid), 8), round(float(ask), 8), int(flags))


class SameMsTickCursor:
    """Deterministic, order-preserving tick cursor that preserves multiple ticks in the same millisecond.

    Queries always start at `last_msc` (inclusive). Already-emitted ticks at `last_msc` are skipped
    by exact prefix/overlap matching on `(time_msc, bid, ask, flags)`, so:
    - Every distinct (or additional) tick within the same `time_msc` is preserved (`inter_tick_gap_ms == 0`).
    - Overlapping poll windows emit zero duplicates.
    - Strictly older timestamps (`tm < last_msc`) are skipped.
    - If a snapshot fallback emitted tick `B` first and a subsequent range query returns `[A, B]`
      at the same `time_msc`, `A` is STILL emitted (zero drop), `same_ms_order_unrecoverable_count`
      is incremented, an audit event is recorded, and a WARNING is logged noting that original
      sub-millisecond arrival order was unrecoverable.
    """

    def __init__(self, initial_msc: int) -> None:
        self.last_msc: int = int(initial_msc)
        self.emitted_at_last_msc: list[tuple[int, float, float, int]] = []
        self.last_msc_had_snapshot: bool = False
        self.same_ms_order_unrecoverable_count: int = 0
        self.same_ms_order_unrecoverable_events: list[dict[str, Any]] = []

    def _record_order_unrecoverable(
        self,
        *,
        time_msc: int,
        emitted_before: list[tuple[int, float, float, int]],
        range_keys: list[tuple[int, float, float, int]],
        late_emitted_keys: list[tuple[int, float, float, int]],
        reason: str,
    ) -> None:
        self.same_ms_order_unrecoverable_count += 1
        evt = {
            "time_msc": int(time_msc),
            "reason": reason,
            "had_snapshot_fallback": bool(self.last_msc_had_snapshot),
            "emitted_before_count": len(emitted_before),
            "late_emitted_prior_count": len(late_emitted_keys),
            "emitted_before_keys": [list(k) for k in emitted_before],
            "range_keys": [list(k) for k in range_keys],
            "late_emitted_keys": [list(k) for k in late_emitted_keys],
        }
        self.same_ms_order_unrecoverable_events.append(evt)
        logger.warning(
            "SAME_MS_ORDER_UNRECOVERABLE time_msc=%d reason=%s had_snapshot=%s late_emitted=%d/%d",
            time_msc,
            reason,
            self.last_msc_had_snapshot,
            len(late_emitted_keys),
            len(range_keys),
        )

    def consume_batch(self, ticks: Any) -> list[tuple[int, float, float, int]]:
        """Consume an ordered batch from `copy_ticks_range` and return only newly observed ticks."""
        if ticks is None or len(ticks) == 0:
            return []

        same_ms: list[tuple[int, float, float, int]] = []
        newer: list[tuple[int, float, float, int]] = []
        for raw in ticks:
            tm, bid, ask, flags = _extract_tick_fields(raw)
            if tm < self.last_msc:
                continue
            if tm == self.last_msc:
                same_ms.append((tm, bid, ask, flags))
            else:
                newer.append((tm, bid, ask, flags))

        emitted_now: list[tuple[int, float, float, int]] = []

        if same_ms:
            keys = [_tick_dedup_key(*t) for t in same_ms]
            prev = self.emitted_at_last_msc
            m = len(prev)
            if m == 0:
                new_same = same_ms
                for t in new_same:
                    emitted_now.append(t)
                    self.emitted_at_last_msc.append(_tick_dedup_key(*t))
            elif len(keys) >= m and keys[:m] == prev:
                new_same = same_ms[m:]
                for t in new_same:
                    emitted_now.append(t)
                    self.emitted_at_last_msc.append(_tick_dedup_key(*t))
            elif len(keys) < m and prev[: len(keys)] == keys:
                new_same = []
            else:
                # Search for exact contiguous occurrence of `prev` inside `keys`.
                # If `match_idx > 0` (e.g., snapshot saw [B], range later returned [A, B]),
                # ticks BEFORE `match_idx` were missed earlier: emit them (deduped against prev),
                # flag original sub-ms order as unrecoverable, and realign canonical emitted order!
                match_idx = -1
                if len(keys) >= m:
                    for i in range(len(keys) - m, -1, -1):
                        if keys[i : i + m] == prev:
                            match_idx = i
                            break
                if match_idx > 0:
                    preceding_ticks = same_ms[:match_idx]
                    trailing_ticks = same_ms[match_idx + m :]
                    late_keys = [_tick_dedup_key(*t) for t in preceding_ticks]
                    self._record_order_unrecoverable(
                        time_msc=self.last_msc,
                        emitted_before=list(prev),
                        range_keys=list(keys),
                        late_emitted_keys=late_keys,
                        reason="PRIOR_SAME_MS_TICK_REVEALED_AFTER_EMIT",
                    )
                    emitted_now.extend(preceding_ticks)
                    emitted_now.extend(trailing_ticks)
                    # Canonical range order now covers every tick in `keys` so subsequent polls deduplicate cleanly.
                    self.emitted_at_last_msc = list(keys)
                    self.last_msc_had_snapshot = False
                elif match_idx == 0:
                    new_same = same_ms[m:]
                    for t in new_same:
                        emitted_now.append(t)
                        self.emitted_at_last_msc.append(_tick_dedup_key(*t))
                else:
                    # Check pure sliding-window suffix/prefix overlap (no out-of-order prefix ticks).
                    overlap = 0
                    for k in range(min(m, len(keys)), 0, -1):
                        if prev[-k:] == keys[:k]:
                            overlap = k
                            break
                    if overlap > 0:
                        new_same = same_ms[overlap:]
                        for t in new_same:
                            emitted_now.append(t)
                            self.emitted_at_last_msc.append(_tick_dedup_key(*t))
                    else:
                        # Interleaved / non-contiguous overlap (e.g. snapshot emitted C, range returns [A, B, C] or [A, C]):
                        # emit every un-emitted tick by multiset count and flag sub-ms order unrecoverable.
                        remaining_prev = Counter(prev)
                        late_emitted: list[tuple[int, float, float, int]] = []
                        late_keys_all: list[tuple[int, float, float, int]] = []
                        for t, k in zip(same_ms, keys):
                            if remaining_prev[k] > 0:
                                remaining_prev[k] -= 1
                            else:
                                late_emitted.append(t)
                                late_keys_all.append(k)
                        if late_emitted:
                            self._record_order_unrecoverable(
                                time_msc=self.last_msc,
                                emitted_before=list(prev),
                                range_keys=list(keys),
                                late_emitted_keys=late_keys_all,
                                reason="NON_CONTIGUOUS_SAME_MS_INTERLEAVING",
                            )
                            emitted_now.extend(late_emitted)
                        # Keep canonical `keys` prefix + any still-unmatched previously emitted keys
                        extra_prev: list[tuple[int, float, float, int]] = []
                        rem_in_keys = Counter(keys)
                        for pk in prev:
                            if rem_in_keys[pk] > 0:
                                rem_in_keys[pk] -= 1
                            else:
                                extra_prev.append(pk)
                        self.emitted_at_last_msc = list(keys) + extra_prev
                        self.last_msc_had_snapshot = False

        for t in newer:
            tm = t[0]
            if tm > self.last_msc:
                self.last_msc = tm
                self.emitted_at_last_msc = [_tick_dedup_key(*t)]
                self.last_msc_had_snapshot = False
                emitted_now.append(t)
            elif tm == self.last_msc:
                self.emitted_at_last_msc.append(_tick_dedup_key(*t))
                emitted_now.append(t)
            # If tm < self.last_msc inside a non-monotonic batch, skip to keep monotonic time_msc.

        return emitted_now

    def consume_snapshot(self, tk: Any) -> list[tuple[int, float, float, int]]:
        """Consume a single fallback snapshot tick from `symbol_info_tick` without duplicating."""
        if tk is None:
            return []
        tm, bid, ask, flags = _extract_tick_fields(tk)
        if tm < self.last_msc:
            return []
        key = _tick_dedup_key(tm, bid, ask, flags)
        if tm == self.last_msc:
            if key in self.emitted_at_last_msc:
                return []
            self.emitted_at_last_msc.append(key)
            self.last_msc_had_snapshot = True
            return [(tm, bid, ask, flags)]
        self.last_msc = tm
        self.emitted_at_last_msc = [key]
        self.last_msc_had_snapshot = True
        return [(tm, bid, ask, flags)]


def build_tick_row(
    *,
    event_id: str,
    release_utc_ts: int,
    server_tick_msc: int,
    server_minus_utc_ms: int,
    local_recv_msc: int,
    ntp_offset_ms: float,
    account_alias: str,
    server: str,
    symbol: str,
    bid: float,
    ask: float,
    point: float,
    tick_flags: int,
    prev_tick: dict[str, Any] | None,
) -> dict[str, Any]:
    utc_ts_ms = int(server_tick_msc - server_minus_utc_ms)
    utc_dt = datetime.fromtimestamp(utc_ts_ms / 1000.0, tz=timezone.utc)
    utc_iso_ms = utc_dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{utc_ts_ms % 1000:03d}Z"
    mid = 0.5 * (bid + ask)
    spread_pts = ((ask - bid) / point) if point > 0 else 0.0
    spread_bps = (((ask - bid) / mid) * 10000.0) if mid > 0 else 0.0
    if prev_tick is None:
        delta_bid_pts = 0.0
        delta_ask_pts = 0.0
        inter_gap_ms = 0
    else:
        delta_bid_pts = ((bid - float(prev_tick["bid"])) / point) if point > 0 else 0.0
        delta_ask_pts = ((ask - float(prev_tick["ask"])) / point) if point > 0 else 0.0
        inter_gap_ms = int(server_tick_msc - int(prev_tick["server_tick_msc"]))
    sec_from_rel = (utc_ts_ms - int(release_utc_ts) * 1000) / 1000.0
    phase = classify_window_phase(sec_from_rel)
    return {
        "record_tier": RECORD_TIER,
        "event_id": event_id,
        "utc_ts_ms": utc_ts_ms,
        "utc_iso_ms": utc_iso_ms,
        "server_tick_msc": int(server_tick_msc),
        "local_recv_msc": int(local_recv_msc),
        "ntp_offset_ms": round(float(ntp_offset_ms), 2),
        "account_alias": account_alias,
        "server": server,
        "symbol": symbol,
        "bid": round(float(bid), 6),
        "ask": round(float(ask), 6),
        "mid": round(float(mid), 6),
        "spread_pts": round(float(spread_pts), 2),
        "spread_bps": round(float(spread_bps), 4),
        "point": float(point),
        "tick_flags": int(tick_flags),
        "delta_bid_pts": round(float(delta_bid_pts), 2),
        "delta_ask_pts": round(float(delta_ask_pts), 2),
        "inter_tick_gap_ms": int(inter_gap_ms),
        "seconds_from_release": round(float(sec_from_rel), 3),
        "window_phase": phase,
        "order_send_count": ORDER_SEND_COUNT,
    }


def summarize_captured_csv(csv_path: Path) -> dict[str, Any]:
    by_sym: dict[str, list[dict[str, str]]] = {}
    total_rows = 0
    global_min_utc_ms: int | None = None
    global_max_utc_ms: int | None = None
    with csv_path.open("r", encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row["record_tier"] != RECORD_TIER:
                raise RuntimeError(
                    f"INVALID_RECORD_TIER: expected {RECORD_TIER!r}, got {row['record_tier']!r} in {csv_path}"
                )
            if int(row["order_send_count"]) != 0:
                raise RuntimeError(
                    f"NONZERO_ORDER_SEND_COUNT: expected 0, got {row['order_send_count']!r} in {csv_path}"
                )
            total_rows += 1
            utc_ms = int(row["utc_ts_ms"])
            if global_min_utc_ms is None or utc_ms < global_min_utc_ms:
                global_min_utc_ms = utc_ms
            if global_max_utc_ms is None or utc_ms > global_max_utc_ms:
                global_max_utc_ms = utc_ms
            by_sym.setdefault(row["symbol"], []).append(row)
    sym_stats: dict[str, Any] = {}
    for sym, rows in sorted(by_sym.items()):
        spreads = sorted(float(r["spread_pts"]) for r in rows)
        jumps = [max(abs(float(r["delta_bid_pts"])), abs(float(r["delta_ask_pts"]))) for r in rows]
        gaps = [int(r["inter_tick_gap_ms"]) for r in rows]
        utc_times = [int(r["utc_ts_ms"]) for r in rows]
        first_ms = min(utc_times)
        last_ms = max(utc_times)
        elapsed_span_sec = round((last_ms - first_ms) / 1000.0, 3)
        phase_counts = {ph: 0 for ph in WINDOW_PHASES}
        for r in rows:
            ph = r.get("window_phase", "")
            phase_counts[ph] = phase_counts.get(ph, 0) + 1
        sym_stats[sym] = {
            "tick_count": len(rows),
            "first_utc_ts_ms": first_ms,
            "last_utc_ts_ms": last_ms,
            "elapsed_span_sec": elapsed_span_sec,
            "spread_p50_pts": round(spreads[len(spreads) // 2], 2),
            "spread_max_pts": round(max(spreads), 2),
            "max_1tick_jump_pts": round(max(jumps), 2),
            "max_inter_tick_gap_ms": max(gaps),
            "phase_counts": phase_counts,
        }
    window_elapsed_span_sec = (
        round((global_max_utc_ms - global_min_utc_ms) / 1000.0, 3)
        if (global_min_utc_ms is not None and global_max_utc_ms is not None)
        else 0.0
    )
    return {
        "record_tier": RECORD_TIER,
        "order_send_count": ORDER_SEND_COUNT,
        "total_rows": total_rows,
        "window_first_utc_ts_ms": global_min_utc_ms,
        "window_last_utc_ts_ms": global_max_utc_ms,
        "window_elapsed_span_sec": window_elapsed_span_sec,
        "csv_sha256": hashlib.sha256(csv_path.read_bytes()).hexdigest(),
        "symbols": sym_stats,
    }


def evaluate_window_completeness(
    summary: dict[str, Any],
    *,
    event_id: str,
    symbols: tuple[str, ...] = ALL8_SYMBOLS,
    min_elapsed_span_sec: float = MIN_EVENT_WINDOW_SPAN_SEC,
) -> dict[str, Any]:
    """Post-capture completeness audit.

    For `US_NFP_20261204` and `US_CPI_20261210`:
      - Every monitored symbol must have `tick_count > 0`.
      - Every `CORE4_SYMBOLS` entry must have `tick_count > 0` AND REAL coverage across ALL 3
        window phases (`PRE_EVENT`, `IMPACT_CORE`, `POST_NORMALIZE`).
      - Window-wide AND per-Core4 elapsed time span must be `>= min_elapsed_span_sec` (default `300.0s`),
        so 1 tick per symbol in 1 single second NEVER passes as `COMPLETE`.
    For `SMOKE_PREFLIGHT`:
      - Total rows > 0 and every monitored symbol has `tick_count > 0`.
    """
    sym_stats = summary.get("symbols", {}) or {}
    total_rows = int(summary.get("total_rows", 0))
    missing_symbols = [s for s in symbols if int(sym_stats.get(s, {}).get("tick_count", 0)) <= 0]

    require_full_window = event_id in EVENT_REQUIRING_IMPACT_CORE
    missing_core4: list[str] = []
    missing_pre_event: list[str] = []
    missing_impact_core: list[str] = []
    missing_post_normalize: list[str] = []
    short_span_core4: list[str] = []

    raw_win_span = summary.get("window_elapsed_span_sec")
    window_elapsed_span_sec = float(raw_win_span) if (raw_win_span is not None and not isinstance(raw_win_span, bool)) else 0.0
    if not math.isfinite(window_elapsed_span_sec):
        window_elapsed_span_sec = 0.0

    if require_full_window:
        for s in CORE4_SYMBOLS:
            st = sym_stats.get(s)
            if not st or int(st.get("tick_count", 0)) <= 0:
                missing_core4.append(s)
                missing_pre_event.append(s)
                missing_impact_core.append(s)
                missing_post_normalize.append(s)
                short_span_core4.append(s)
                continue
            pc = st.get("phase_counts") or {}
            if int(pc.get("PRE_EVENT", 0)) <= 0:
                missing_pre_event.append(s)
            if int(pc.get("IMPACT_CORE", 0)) <= 0:
                missing_impact_core.append(s)
            if int(pc.get("POST_NORMALIZE", 0)) <= 0:
                missing_post_normalize.append(s)
            sym_span = st.get("elapsed_span_sec")
            sym_span_f = float(sym_span) if (sym_span is not None and not isinstance(sym_span, bool)) else 0.0
            if (not math.isfinite(sym_span_f)) or sym_span_f < float(min_elapsed_span_sec):
                short_span_core4.append(s)

    reasons: list[str] = []
    if total_rows <= 0:
        reasons.append("ZERO_TICKS_CAPTURED")
    if missing_symbols:
        reasons.append(f"MISSING_MONITORED_SYMBOLS:{','.join(missing_symbols)}")
    if missing_core4:
        reasons.append(f"MISSING_CORE4_SYMBOLS:{','.join(missing_core4)}")
    if missing_pre_event:
        reasons.append(f"MISSING_PRE_EVENT_COVERAGE:{','.join(missing_pre_event)}")
    if missing_impact_core:
        reasons.append(f"MISSING_IMPACT_CORE_COVERAGE:{','.join(missing_impact_core)}")
    if missing_post_normalize:
        reasons.append(f"MISSING_POST_NORMALIZE_COVERAGE:{','.join(missing_post_normalize)}")
    if require_full_window and window_elapsed_span_sec < float(min_elapsed_span_sec):
        reasons.append(
            f"INSUFFICIENT_WINDOW_ELAPSED_SPAN:{window_elapsed_span_sec:.3f}s<{float(min_elapsed_span_sec):.1f}s"
        )
    if require_full_window and short_span_core4:
        reasons.append(f"INSUFFICIENT_CORE4_ELAPSED_SPAN:{','.join(short_span_core4)}")

    complete = len(reasons) == 0
    return {
        "window_complete": complete,
        "status": "COMPLETE" if complete else "INCOMPLETE_MISSING_DATA",
        "requires_impact_core": require_full_window,
        "requires_all_three_phases": require_full_window,
        "min_elapsed_span_sec": float(min_elapsed_span_sec) if require_full_window else 0.0,
        "window_elapsed_span_sec": round(window_elapsed_span_sec, 3),
        "missing_symbols": missing_symbols,
        "missing_core4_symbols": missing_core4,
        "missing_pre_event_symbols": missing_pre_event,
        "missing_impact_core_symbols": missing_impact_core,
        "missing_post_normalize_symbols": missing_post_normalize,
        "short_span_core4_symbols": short_span_core4,
        "reasons": reasons,
    }


def _validate_non_none_zero_count(name: str, raw_val: Any) -> int:
    if raw_val is None or isinstance(raw_val, bool):
        raise RuntimeError(f"PREFLIGHT_ABORT_UNKNOWN_ACCOUNT_STATE: {name}={raw_val!r}")
    val = int(raw_val)
    if val != 0:
        raise RuntimeError(f"PREFLIGHT_ABORT_NON_FLAT: account not flat ({name}={val})")
    return val


def run_live_capture(
    *,
    terminal_exe: Path,
    event_id: str,
    out_csv: Path,
    account_alias: str = "DEMO_SECONDARY",
    symbols: tuple[str, ...] = ALL8_SYMBOLS,
    duration_sec: float | None = None,
    red_news_csv: Path | None = None,
    expected_login: int | None = None,
    expected_server: str | None = None,
    mt5_module: Any = None,
    poll_sleep_sec: float = 0.25,
    connect_wait_attempts: int = 30,
    connect_wait_sleep_s: float = 0.5,
) -> dict[str, Any]:
    """Connect read-only to an isolated MT5 terminal and capture live ticks (`OrderSend = 0`)."""
    if event_id not in EVENTS:
        raise ValueError(f"Unknown event_id: {event_id!r}")

    if expected_login is None or isinstance(expected_login, bool) or int(expected_login) <= 0:
        raise RuntimeError(
            f"PREFLIGHT_ABORT_EXPECTED_LOGIN_REQUIRED: expected_login is required (>0) for live capture, got {expected_login!r}"
        )
    if expected_server is None or not isinstance(expected_server, str) or not expected_server.strip():
        raise RuntimeError(
            f"PREFLIGHT_ABORT_EXPECTED_SERVER_REQUIRED: expected_server is required (non-empty) for live capture, got {expected_server!r}"
        )
    expected_login_int = int(expected_login)
    expected_server_str = expected_server.strip()

    ev = EVENTS[event_id]
    resolved_duration_sec = float(default_duration_sec(event_id) if duration_sec is None else duration_sec)
    if resolved_duration_sec <= 0.0:
        raise ValueError(f"duration_sec must be > 0, got {resolved_duration_sec}")

    resolved_red_news_csv = DEFAULT_RED_NEWS_CSV if red_news_csv is None else Path(red_news_csv)
    cal_chk = verify_red_news_calendar(resolved_red_news_csv)
    if not cal_chk.get("ok"):
        raise RuntimeError(
            f"PREFLIGHT_ABORT_CALENDAR: red-news calendar verification failed for {resolved_red_news_csv}: {cal_chk}"
        )

    ntp = measure_ntp_offset_ms()
    if not is_ntp_ok(ntp):
        raise RuntimeError(
            f"PREFLIGHT_ABORT_NTP: NTP offset check failed "
            f"(offset_ms={ntp.get('offset_ms')!r}, required abs(offset_ms) < {NTP_MAX_ABS_OFFSET_MS}ms): {ntp}"
        )

    if mt5_module is not None:
        mt5 = mt5_module
    else:
        import MetaTrader5 as mt5

    if not mt5.initialize(path=str(terminal_exe), portable=True):
        err = mt5.last_error()
        raise RuntimeError(f"MT5 initialize failed for {terminal_exe}: {err}")

    try:
        # Wait briefly for broker connection and account login after portable terminal launch
        attempts = max(1, int(connect_wait_attempts))
        for attempt in range(attempts):
            ti = mt5.terminal_info()
            ai = mt5.account_info()
            if ti is not None and bool(getattr(ti, "connected", False)) and ai is not None and int(getattr(ai, "login", 0) or 0) > 0:
                break
            if attempt + 1 < attempts and connect_wait_sleep_s > 0:
                time.sleep(connect_wait_sleep_s)

        ti = mt5.terminal_info()
        ai = mt5.account_info()
        if ai is None or ti is None:
            raise RuntimeError("PREFLIGHT_ABORT_MT5_INFO: MT5 account_info/terminal_info unavailable")
        if not bool(getattr(ti, "connected", False)):
            raise RuntimeError("PREFLIGHT_ABORT_DISCONNECTED: MT5 terminal is not connected to broker server")
        if bool(getattr(ti, "trade_allowed", True)):
            raise RuntimeError(
                "PREFLIGHT_ABORT_TRADE_ALLOWED: terminal_info.trade_allowed is True (or absent); "
                "trading MUST be disabled for read-only QUOTE_ONLY capture"
            )

        raw_login = getattr(ai, "login", None)
        if raw_login is None or isinstance(raw_login, bool) or int(raw_login) <= 0:
            raise RuntimeError(f"PREFLIGHT_ABORT_LOGIN: invalid account login={raw_login!r}")
        actual_login = int(raw_login)
        actual_server = str(getattr(ai, "server", "") or "")
        if not actual_server:
            raise RuntimeError("PREFLIGHT_ABORT_SERVER: MT5 account server is empty")

        if actual_login != expected_login_int:
            raise RuntimeError(
                f"PREFLIGHT_ABORT_LOGIN_MISMATCH: actual_login={actual_login} != expected_login={expected_login_int}"
            )
        if actual_server != expected_server_str:
            raise RuntimeError(
                f"PREFLIGHT_ABORT_SERVER_MISMATCH: actual_server={actual_server!r} != expected_server={expected_server_str!r}"
            )

        pos_cnt = _validate_non_none_zero_count("positions_total", mt5.positions_total())
        ord_cnt = _validate_non_none_zero_count("orders_total", mt5.orders_total())

        sym_points: dict[str, float] = {}
        for s in symbols:
            mt5.symbol_select(s, True)
            si = mt5.symbol_info(s)
            if si is None:
                raise RuntimeError(f"Symbol unavailable on Market Watch: {s}")
            sym_points[s] = float(si.point)

        # Wait briefly for ticks to populate after symbol_select, then pick freshest tick across all symbols
        freshest_msc = 0
        for attempt in range(10):
            for s in symbols:
                tk = mt5.symbol_info_tick(s)
                if tk is not None and int(tk.time_msc) > freshest_msc:
                    freshest_msc = int(tk.time_msc)
            if freshest_msc > 0:
                break
            if attempt < 9 and connect_wait_sleep_s > 0:
                time.sleep(min(0.3, connect_wait_sleep_s))
        if freshest_msc <= 0:
            raise RuntimeError("No live tick available across monitored symbols")

        now_utc_ms = int(time.time() * 1000)
        srv_minus_utc_ms = int(round((freshest_msc - now_utc_ms) / 3600000.0) * 3600000)
        release_ts = int(time.time()) if ev["release_utc_ts"] == 0 else int(ev["release_utc_ts"])
        ntp_ms = float(ntp["offset_ms"])

        out_csv.parent.mkdir(parents=True, exist_ok=True)
        cursors: dict[str, SameMsTickCursor] = {}
        for s in symbols:
            tk0 = mt5.symbol_info_tick(s)
            init_msc = (
                (int(tk0.time_msc) - 1000)
                if (tk0 is not None and int(tk0.time_msc) > 0)
                else (now_utc_ms + srv_minus_utc_ms - 5000)
            )
            cursors[s] = SameMsTickCursor(init_msc)
        prev_row: dict[str, dict[str, Any] | None] = {s: None for s in symbols}

        t_end = time.time() + resolved_duration_sec
        with out_csv.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=list(CSV_COLUMNS))
            writer.writeheader()
            while True:
                recv_ms = int(time.time() * 1000)
                for s in symbols:
                    cur = cursors[s]
                    from_dt = datetime.fromtimestamp(cur.last_msc / 1000.0, tz=timezone.utc)
                    to_dt = datetime.fromtimestamp((recv_ms + srv_minus_utc_ms + 5000) / 1000.0, tz=timezone.utc)
                    ticks = mt5.copy_ticks_range(s, from_dt, to_dt, mt5.COPY_TICKS_ALL)
                    if ticks is not None and len(ticks) > 0:
                        new_ticks = cur.consume_batch(ticks)
                    else:
                        # Fallback to current snapshot tick if copy_ticks_range returned empty
                        new_ticks = cur.consume_snapshot(mt5.symbol_info_tick(s))

                    for tm, bid, ask, flags in new_ticks:
                        row = build_tick_row(
                            event_id=event_id,
                            release_utc_ts=release_ts,
                            server_tick_msc=tm,
                            server_minus_utc_ms=srv_minus_utc_ms,
                            local_recv_msc=recv_ms,
                            ntp_offset_ms=ntp_ms,
                            account_alias=account_alias,
                            server=actual_server,
                            symbol=s,
                            bid=bid,
                            ask=ask,
                            point=sym_points[s],
                            tick_flags=flags,
                            prev_tick=prev_row[s],
                        )
                        writer.writerow(row)
                        prev_row[s] = row

                now_loop = time.time()
                if now_loop >= t_end:
                    break
                if poll_sleep_sec > 0:
                    time.sleep(min(poll_sleep_sec, max(0.0, t_end - now_loop)))

        summary = summarize_captured_csv(out_csv)
        completeness = evaluate_window_completeness(summary, event_id=event_id, symbols=symbols)
        unrec_events: list[dict[str, Any]] = []
        unrec_count = 0
        for s in symbols:
            cur = cursors[s]
            unrec_count += cur.same_ms_order_unrecoverable_count
            for ev_u in cur.same_ms_order_unrecoverable_events:
                unrec_events.append({"symbol": s, **ev_u})
        return {
            "schema": "naqex.nfp_cpi_quote_only_capture.v2",
            "captured_utc": datetime.now(timezone.utc).isoformat(),
            "status": completeness["status"],
            "window_complete": completeness["window_complete"],
            "completeness": completeness,
            "record_tier": RECORD_TIER,
            "order_send_count": ORDER_SEND_COUNT,
            "event_id": event_id,
            "account_alias": account_alias,
            "login": actual_login,
            "expected_login": expected_login_int,
            "server": actual_server,
            "expected_server": expected_server_str,
            "terminal_connected": bool(ti.connected),
            "terminal_trade_allowed": bool(getattr(ti, "trade_allowed", False)),
            "positions_total": pos_cnt,
            "orders_total": ord_cnt,
            "ntp_check": ntp,
            "red_news_calendar_check": cal_chk,
            "server_minus_utc_ms": srv_minus_utc_ms,
            "duration_sec": resolved_duration_sec,
            "same_ms_order_unrecoverable_count": unrec_count,
            "same_ms_order_unrecoverable_events": unrec_events,
            "csv_path": str(out_csv),
            "summary": summary,
        }
    finally:
        mt5.shutdown()


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Read-Only QUOTE_ONLY Collector for US NFP (04/12) & US CPI (10/12)")
    parser.add_argument("--event", choices=sorted(EVENTS.keys()), default="SMOKE_PREFLIGHT")
    parser.add_argument("--terminal-exe", type=Path, default=None)
    parser.add_argument("--out-csv", type=Path, default=None)
    parser.add_argument("--out-json", type=Path, default=None)
    parser.add_argument(
        "--duration-sec",
        type=float,
        default=None,
        help="Capture duration in seconds (default: 1200.0 for US_NFP_20261204/US_CPI_20261210, 5.0 for SMOKE_PREFLIGHT)",
    )
    parser.add_argument("--account-alias", default="DEMO_SECONDARY")
    parser.add_argument("--expected-login", type=int, default=None)
    parser.add_argument("--expected-server", type=str, default=None)
    parser.add_argument("--red-news-csv", type=Path, default=DEFAULT_RED_NEWS_CSV)
    parser.add_argument("--preflight-offline-only", action="store_true")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    resolved_dur = default_duration_sec(args.event) if args.duration_sec is None else float(args.duration_sec)

    if args.preflight_offline_only:
        cal_chk = verify_red_news_calendar(args.red_news_csv)
        ntp = measure_ntp_offset_ms()
        ntp_ok = is_ntp_ok(ntp)
        cal_ok = bool(cal_chk.get("ok"))
        preflight_ok = cal_ok and ntp_ok
        fail_reasons: list[str] = []
        if not cal_ok:
            fail_reasons.append(f"RED_NEWS_CALENDAR_FAILED:found={cal_chk.get('found')}")
        if not ntp_ok:
            fail_reasons.append(
                f"NTP_DRIFT_FAILED:offset_ms={ntp.get('offset_ms')},threshold_ms={NTP_MAX_ABS_OFFSET_MS}"
            )
        payload = {
            "status": "PREFLIGHT_OK" if preflight_ok else "PREFLIGHT_FAILED",
            "preflight_ok": preflight_ok,
            "fail_reasons": fail_reasons,
            "record_tier": RECORD_TIER,
            "order_send_count": ORDER_SEND_COUNT,
            "event_id": args.event,
            "resolved_duration_sec": resolved_dur,
            "ntp_check": ntp,
            "red_news_calendar_check": cal_chk,
            "events": {k: EVENTS[k] for k in ("US_NFP_20261204", "US_CPI_20261210")},
            "csv_columns_count": len(CSV_COLUMNS),
        }
        if args.out_json is not None:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(payload, indent=2))
        return 0 if preflight_ok else 2

    if args.terminal_exe is None or args.out_csv is None:
        raise SystemExit("--terminal-exe and --out-csv are required for live QUOTE_ONLY capture")
    if args.expected_login is None or args.expected_login <= 0 or args.expected_server is None or not args.expected_server.strip():
        raise SystemExit("--expected-login (>0) and --expected-server (non-empty) are required for live QUOTE_ONLY capture")

    try:
        rep = run_live_capture(
            terminal_exe=args.terminal_exe,
            event_id=args.event,
            out_csv=args.out_csv,
            account_alias=args.account_alias,
            duration_sec=resolved_dur,
            red_news_csv=args.red_news_csv,
            expected_login=args.expected_login,
            expected_server=args.expected_server,
        )
    except RuntimeError as exc:
        err_payload = {
            "schema": "naqex.nfp_cpi_quote_only_capture.v2",
            "captured_utc": datetime.now(timezone.utc).isoformat(),
            "status": "ABORTED_FAIL_CLOSED",
            "window_complete": False,
            "record_tier": RECORD_TIER,
            "order_send_count": ORDER_SEND_COUNT,
            "event_id": args.event,
            "resolved_duration_sec": resolved_dur,
            "expected_login": args.expected_login,
            "expected_server": args.expected_server,
            "error": str(exc),
        }
        if args.out_json is not None:
            args.out_json.parent.mkdir(parents=True, exist_ok=True)
            args.out_json.write_text(json.dumps(err_payload, indent=2) + "\n", encoding="utf-8")
        print(json.dumps(err_payload, indent=2))
        return 2

    if args.out_json is not None:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(rep, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(rep, indent=2))
    return 0 if rep.get("window_complete", False) else 2


if __name__ == "__main__":
    raise SystemExit(main())
