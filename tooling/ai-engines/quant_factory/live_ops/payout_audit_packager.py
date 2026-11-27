"""Immutable White-Box Payout Audit Trail Packager & Hash-Chain Verifier (OrderSend = 0).

Mũi 3 Live-Ops Lane OPS-5: packages read-only execution and reconciliation evidence
into a deterministic, tamper-evident bundle with a cryptographic SHA-256 hash chain
and automatic white-box prop-firm compliance certification.

HARD SAFETY & OPSEC INVARIANTS (`[ARCH-02]`, `G02`, `G11`, `G12`, `G16`):
  - Strictly offline and read-only on all input files:
      `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - NEVER imports `MetaTrader5`, NEVER opens network/SSH connections, NEVER mutates
    production MT5 files, presets, or frozen calendars.
  - ZERO bare `assert` statements (`[ARCH-02]`).
  - Fail-closed immutability: refuses to overwrite an existing bundle directory;
    rejects missing/invalid SL, grid stacking, martingale lot doubling, HFT tick
    scalping, red-news hard-ban breaches, reconciliation orphans, unresolved fills,
    or tampered artifacts.
  - Strict Layer-1 OPSEC redaction mode (`redact_for_layer1=True`) masks account
    logins, broker tickets/deal IDs, IPv4/IPv6 addresses, Windows user profile paths,
    and secrets while preserving deterministic relational linkage and source SHA-256
    provenance.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

QUANT_FACTORY_DIR: Final[Path] = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR: Final[Path] = QUANT_FACTORY_DIR.parent
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.red_news import RedNewsEvent, load_calendar_events  # noqa: E402
from quant_core.tca import (  # noqa: E402
    ENTRY_EVENT_TYPES,
    EXIT_EVENT_TYPES,
    NON_FILL_EVENT_TYPES,
    VALID_FILL_EVENT_TYPES,
    canonical_payload_sha256,
    is_unresolved_record,
    load_exec_audit_csv,
    normalize_symbol_alias,
    parse_optional_strict_int,
    write_atomic_sha256_json,
)

from quant_factory.live_ops.feed_dst_news_guard import (  # noqa: E402
    ExtendedRedNewsEvent,
    load_extended_calendar,
    symbol_matches_event_code,
)

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0

MANIFEST_SCHEMA_VERSION: Final[str] = "naqex-payout-audit-manifest-v1"
CERTIFICATION_SCHEMA_VERSION: Final[str] = "naqex-payout-whitebox-cert-v1"
BLACKBOX_SUMMARY_SCHEMA_VERSION: Final[str] = "naqex-decision-blackbox-summary-v1"
EX5_ATTESTATION_SCHEMA_VERSION: Final[str] = "naqex-ex5-attestation-v1"

DEFAULT_RED_NEWS_HARD_BAN_SEC: Final[int] = 120
DEFAULT_MIN_TRADE_DURATION_SEC: Final[int] = 60
DEFAULT_MARTINGALE_LOT_JUMP_RATIO: Final[float] = 1.80
DEFAULT_MAX_CONCURRENT_SAME_SYM_MAGIC: Final[int] = 1

DEFAULT_BASE_RED_NEWS_CSV: Final[Path] = AI_ENGINES_DIR / "exports" / "Files" / "naqex_red_news_utc.csv"
DEFAULT_EXTENDED_RED_NEWS_JSON: Final[Path] = (
    AI_ENGINES_DIR / "configs" / "calendars" / "red_news_extended_off3_8ccy_eia.json"
)

_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")
_SAFE_CYCLE_ID_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,79}$")

# OPSEC redaction patterns built cleanly without embedding concrete private IPs or tokens
_IPV4_RE: Final[re.Pattern[str]] = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}(?:/\d{1,2})?\b")
_IPV6_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:\b(?:[0-9a-fA-F]{1,4}:){3,7}[0-9a-fA-F]{1,4}\b"
    r"|(?:[0-9a-fA-F]{1,4}:){1,6}:[0-9a-fA-F:]{1,20}"
    r"|::[0-9a-fA-F:]{1,20})"
)
_WIN_USER_PATH_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)([A-Z]:|/mnt/[a-z])([\\/])Users\2(?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_TAG_ID_REDACT_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(deal|ord|tk|pos|ticket|order|login|account)=([A-Za-z0-9_-]+)",
    re.IGNORECASE,
)
_LOGIN_INLINE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(account(?:_login)?|login)\s*([:=#])\s*(\d{5,12})\b",
    re.IGNORECASE,
)
_SECRET_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("GITHUB_TOKEN", re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")),
    ("OPENAI_KEY", re.compile(r"\b" + "sk-" + r"(?:proj-)?[A-Za-z0-9_-]{24,}\b")),
    ("GOOGLE_API_KEY", re.compile(r"\b" + "AIza" + r"[0-9A-Za-z_-]{30,}\b")),
    ("TELEGRAM_TOKEN", re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b")),
    ("WEBHOOK_URL", re.compile(r"https?://(?:discord\.com|discordapp\.com)/api/webhooks/\S+", re.IGNORECASE)),
    ("CRED_DSN", re.compile(r"postgres(?:ql)?://[^\s:/@<]+:[^\s/@<]{4,}@[^\s/<]+", re.IGNORECASE)),
    ("HEROKU_APP", re.compile(r"(?i)\b" + "naqex-" + "deadman-" + r"[a-z0-9-]+\b")),
    ("TG_HANDLE", re.compile(r"(?i)@?" + "naqex_" + "guard_" + r"bot\b")),
    ("KV_SECRET", re.compile(r"(?i)\b(password|passwd|api[_-]?key|token|secret|webhook)\s*([:=])\s*\S+")),
)

_REDACT_LOGIN_KEYS: Final[frozenset[str]] = frozenset(
    {
        "account_login",
        "expected_login",
        "actual_login",
        "login",
        "detected_login",
    }
)
_REDACT_LOGIN_LIST_KEYS: Final[frozenset[str]] = frozenset(
    {
        "statement_logins",
        "audit_logins",
        "logins",
    }
)
_REDACT_ID_KEYS: Final[frozenset[str]] = frozenset(
    {
        "deal_id",
        "ticket",
        "order_id",
        "position_id",
        "deal",
        "order",
        "position",
    }
)
_REDACT_SECRET_KEYS: Final[frozenset[str]] = frozenset(
    {
        "password",
        "passwd",
        "token",
        "api_key",
        "secret",
        "webhook",
        "ip",
        "wan_ip",
        "public_ip",
        "router_ip",
        "_ssh_host",
    }
)


class PayoutComplianceError(ValueError):
    """Raised when fail-closed strict packaging rejects a non-compliant payout cycle."""


@dataclass(frozen=True, slots=True)
class ClosedPositionSummary:
    """Normalized closed trade reconstructed from `naqex_exec_audit.csv`."""

    position_key: str
    symbol: str
    canonical_symbol: str
    magic: int
    side: str
    open_ts: int
    close_ts: int
    duration_sec: int
    lots: float
    entry_price: float
    sl_price: float
    pnl_usd: float | None
    exit_event_type: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path | str) -> str:
    """Stream-compute SHA-256 hex digest of a local file (strictly read-only)."""
    p = Path(path)
    h = hashlib.sha256()
    with p.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _pseudonymize_token(namespace: str, raw_value: Any) -> str:
    s = str(raw_value or "").strip()
    if not s:
        return ""
    digest = hashlib.sha256(f"NAQEX_OPSEC_REDACT|{namespace}|{s}".encode()).hexdigest()[:10]
    return f"{namespace}_{digest}"


def redact_text_for_layer1(text: str) -> str:
    """Scrub IPs, logins, broker tickets, Windows user paths, and secrets from text."""
    out = str(text)

    # Preserve RFC 6598 specification literal 100.64.0.0/10 while redacting concrete IPs
    def _replace_ipv4(match: re.Match[str]) -> str:
        tok = match.group(0)
        if tok == "100.64.0.0/10":
            return tok
        return "[REDACTED_IP]"

    out = _IPV4_RE.sub(_replace_ipv4, out)
    out = _IPV6_RE.sub("[REDACTED_IPV6]", out)
    out = _WIN_USER_PATH_RE.sub(r"\1\2Users\2<USER>", out)

    def _replace_tag_id(match: re.Match[str]) -> str:
        key = match.group(1)
        val = match.group(2)
        ns = "LOGIN" if key.lower() in ("login", "account") else "ID"
        return f"{key}={_pseudonymize_token(ns, val)}"

    out = _TAG_ID_REDACT_RE.sub(_replace_tag_id, out)

    def _replace_inline_login(match: re.Match[str]) -> str:
        key = match.group(1)
        sep = match.group(2)
        val = match.group(3)
        return f"{key}{sep}{_pseudonymize_token('LOGIN', val)}"

    out = _LOGIN_INLINE_RE.sub(_replace_inline_login, out)

    for tag, rx in _SECRET_PATTERNS:
        if tag == "KV_SECRET":
            out = rx.sub(r"\1\2[REDACTED_SECRET]", out)
        else:
            out = rx.sub(f"[REDACTED_{tag}]", out)

    return out


def redact_payload_for_layer1(obj: Any) -> Any:
    """Recursively redact sensitive fields in JSON-compatible objects for Layer-1 safety."""
    if isinstance(obj, Mapping):
        cleaned: dict[str, Any] = {}
        for raw_k, val in obj.items():
            key = str(raw_k)
            low = key.lower()
            if low in _REDACT_SECRET_KEYS:
                cleaned[key] = "[REDACTED]"
            elif low in _REDACT_LOGIN_KEYS:
                cleaned[key] = None if val in (None, "") else _pseudonymize_token("ACCT", val)
            elif low in _REDACT_LOGIN_LIST_KEYS and isinstance(val, Sequence) and not isinstance(val, (str, bytes)):
                cleaned[key] = [_pseudonymize_token("ACCT", x) for x in val if x not in (None, "")]
            elif low in _REDACT_ID_KEYS:
                cleaned[key] = "" if val in (None, "") else _pseudonymize_token("ID", val)
            else:
                cleaned[key] = redact_payload_for_layer1(val)
        return cleaned
    if isinstance(obj, list):
        return [redact_payload_for_layer1(item) for item in obj]
    if isinstance(obj, tuple):
        return [redact_payload_for_layer1(item) for item in obj]
    if isinstance(obj, str):
        return redact_text_for_layer1(obj)
    return obj


def _redact_audit_csv_bytes(raw_bytes: bytes) -> bytes:
    """Redact logins, tickets/IDs, comments, and IPs inside `naqex_exec_audit.csv` with LF output."""
    text = raw_bytes.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text, newline=""))
    fieldnames = list(reader.fieldnames or [])
    if not fieldnames:
        return b""

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    for row in reader:
        if not row or all(str(v or "").strip() == "" for v in row.values()):
            continue
        out_row: dict[str, str] = {}
        for col in fieldnames:
            val = "" if row.get(col) is None else str(row.get(col))
            low = col.strip().lower()
            if low in _REDACT_LOGIN_KEYS:
                out_row[col] = "" if not val.strip() else _pseudonymize_token("ACCT", val)
            elif low in _REDACT_ID_KEYS:
                out_row[col] = "" if not val.strip() else _pseudonymize_token("ID", val)
            elif low in _REDACT_SECRET_KEYS:
                out_row[col] = "[REDACTED]" if val.strip() else ""
            else:
                out_row[col] = redact_text_for_layer1(val)
        writer.writerow(out_row)
    return buf.getvalue().encode("utf-8")


def _write_atomic_bytes(path: Path, data: bytes) -> None:
    """Atomically write bytes via temp file + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=str(path.parent))
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _load_red_news_events_for_audit(
    *,
    red_news_calendar_path: Path | str | None = None,
    red_news_events: Sequence[RedNewsEvent | ExtendedRedNewsEvent] | None = None,
    include_default_calendars: bool = True,
) -> tuple[list[ExtendedRedNewsEvent], list[str]]:
    """Load red-news events from explicit input or workspace defaults (read-only)."""
    sources: list[str] = []
    if red_news_events is not None:
        out: list[ExtendedRedNewsEvent] = []
        for ev in red_news_events:
            if isinstance(ev, ExtendedRedNewsEvent):
                out.append(ev)
            elif isinstance(ev, RedNewsEvent):
                out.append(ExtendedRedNewsEvent.from_red_news_event(ev))
            else:
                raise ValueError(f"Unsupported red-news event type: {type(ev).__name__}")
        sources.append("in_memory_events")
        return out, sources

    loaded: list[ExtendedRedNewsEvent] = []
    if red_news_calendar_path is not None:
        cal_p = Path(red_news_calendar_path)
        if not cal_p.is_file():
            raise FileNotFoundError(f"Red-news calendar file not found: {cal_p}")
        if cal_p.suffix.lower() == ".json":
            raw_doc = json.loads(cal_p.read_text(encoding="utf-8"))
            if isinstance(raw_doc, Mapping) and raw_doc.get("schema") == "naqex-red-news-extended-off3-8ccy-eia-v1":
                loaded.extend(load_extended_calendar(cal_p))
            else:
                loaded.extend(ExtendedRedNewsEvent.from_red_news_event(e) for e in load_calendar_events(cal_p))
        else:
            loaded.extend(ExtendedRedNewsEvent.from_red_news_event(e) for e in load_calendar_events(cal_p))
        sources.append(cal_p.name)
        return loaded, sources

    if include_default_calendars:
        if DEFAULT_BASE_RED_NEWS_CSV.is_file():
            loaded.extend(
                ExtendedRedNewsEvent.from_red_news_event(e) for e in load_calendar_events(DEFAULT_BASE_RED_NEWS_CSV)
            )
            sources.append(DEFAULT_BASE_RED_NEWS_CSV.name)
        if DEFAULT_EXTENDED_RED_NEWS_JSON.is_file():
            loaded.extend(load_extended_calendar(DEFAULT_EXTENDED_RED_NEWS_JSON))
            sources.append(DEFAULT_EXTENDED_RED_NEWS_JSON.name)
    return loaded, sources


def _check_hard_sl_attached(entry_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Certify `hard_sl_attached_pct == 100.0` across all executed entry fills."""
    total_entries = len(entry_rows)
    attached = 0
    violations: list[dict[str, Any]] = []

    for idx, row in enumerate(entry_rows):
        sl_px = float(row.get("sl_price") or 0.0)
        fill_px = float(row.get("fill_price") or 0.0)
        side = str(row.get("side") or "").strip().upper()
        reason: str | None = None

        if not math.isfinite(sl_px) or sl_px <= 0.0:
            reason = "MISSING_OR_ZERO_SL"
        elif fill_px > 0.0 and side == "BUY" and sl_px >= fill_px:
            reason = "INVALID_BUY_SL_NOT_BELOW_ENTRY"
        elif fill_px > 0.0 and side == "SELL" and sl_px <= fill_px:
            reason = "INVALID_SELL_SL_NOT_ABOVE_ENTRY"

        if reason is None:
            attached += 1
        else:
            violations.append(
                {
                    "entry_index": idx,
                    "utc_ts": row.get("utc_ts"),
                    "symbol": row.get("symbol"),
                    "magic": row.get("magic"),
                    "side": side,
                    "fill_price": fill_px,
                    "sl_price": sl_px,
                    "position_id": row.get("position_id") or row.get("ticket") or "",
                    "reason": reason,
                }
            )

    pct = round((attached / total_entries) * 100.0, 4) if total_entries > 0 else 0.0
    verified = total_entries > 0 and attached == total_entries and pct == 100.0
    return {
        "verified": verified,
        "hard_sl_attached_pct": pct,
        "entries_checked": total_entries,
        "entries_with_valid_sl": attached,
        "violations": violations,
    }


def _reconstruct_positions_and_check_grid(
    fill_rows: Sequence[Mapping[str, Any]],
    *,
    max_concurrent_allowed: int = DEFAULT_MAX_CONCURRENT_SAME_SYM_MAGIC,
) -> tuple[dict[str, Any], list[ClosedPositionSummary]]:
    """Reconstruct open/closed position lifecycle and verify zero grid stacking (`<= 1`)."""
    # Sort chronologically; at identical timestamps process exits before new entries so
    # an atomic close-then-reopen does not false-positive as concurrent grid stacking.
    indexed_rows: list[tuple[int, int, int, Mapping[str, Any]]] = []
    for row_idx, row in enumerate(fill_rows):
        ev = str(row.get("event_type") or "").strip().upper()
        is_exit = ev in EXIT_EVENT_TYPES
        order_rank = 0 if is_exit else 1
        indexed_rows.append((int(row["utc_ts"]), order_rank, row_idx, row))
    indexed_rows.sort(key=lambda item: (item[0], item[1], item[2]))

    active_by_key: dict[tuple[str, int], dict[str, dict[str, Any]]] = {}
    max_concurrent_observed = 0
    grid_violations: list[dict[str, Any]] = []
    closed_positions: list[ClosedPositionSummary] = []
    anon_seq = 0

    for utc_ts, _rank, row_idx, row in indexed_rows:
        ev = str(row.get("event_type") or "").strip().upper()
        canon_sym = str(row.get("canonical_symbol") or normalize_symbol_alias(str(row.get("symbol") or "")))
        magic = int(row.get("magic") or 0)
        group_key = (canon_sym, magic)
        pos_id = str(row.get("position_id") or "").strip()
        ticket = str(row.get("ticket") or "").strip()
        order_id = str(row.get("order_id") or "").strip()
        ident = pos_id or ticket or order_id

        active_map = active_by_key.setdefault(group_key, {})

        if ev in ENTRY_EVENT_TYPES:
            if not ident:
                anon_seq += 1
                ident = f"ANON_{row_idx}_{anon_seq}"
            if ident in active_map:
                # Partial entry adding to the exact same MT5 position_id (not a second grid leg)
                active_map[ident]["lots"] = round(active_map[ident]["lots"] + float(row.get("lots") or 0.0), 6)
            else:
                active_map[ident] = {
                    "position_key": ident,
                    "symbol": str(row.get("symbol") or canon_sym),
                    "canonical_symbol": canon_sym,
                    "magic": magic,
                    "side": str(row.get("side") or "").strip().upper(),
                    "open_ts": utc_ts,
                    "lots": float(row.get("lots") or 0.0),
                    "entry_price": float(row.get("fill_price") or 0.0),
                    "sl_price": float(row.get("sl_price") or 0.0),
                }
            concurrent_now = len(active_map)
            if concurrent_now > max_concurrent_observed:
                max_concurrent_observed = concurrent_now
            if concurrent_now > max_concurrent_allowed:
                grid_violations.append(
                    {
                        "utc_ts": utc_ts,
                        "symbol": str(row.get("symbol") or canon_sym),
                        "canonical_symbol": canon_sym,
                        "magic": magic,
                        "concurrent_positions": concurrent_now,
                        "max_allowed": max_concurrent_allowed,
                        "active_position_ids": sorted(active_map.keys()),
                    }
                )
        elif ev in EXIT_EVENT_TYPES:
            matched_key: str | None = None
            if ident and ident in active_map:
                matched_key = ident
            elif len(active_map) == 1:
                matched_key = next(iter(active_map.keys()))
            elif active_map:
                # FIFO oldest open position on same (symbol, magic)
                matched_key = min(active_map.keys(), key=lambda k: active_map[k]["open_ts"])

            if matched_key is not None:
                opened = active_map[matched_key]
                is_partial_exit = ev == "PARTIAL_EXIT"
                if not is_partial_exit:
                    active_map.pop(matched_key, None)
                duration_sec = utc_ts - int(opened["open_ts"])
                closed_positions.append(
                    ClosedPositionSummary(
                        position_key=matched_key,
                        symbol=str(opened["symbol"]),
                        canonical_symbol=canon_sym,
                        magic=magic,
                        side=str(opened["side"]),
                        open_ts=int(opened["open_ts"]),
                        close_ts=utc_ts,
                        duration_sec=duration_sec,
                        lots=float(opened["lots"]),
                        entry_price=float(opened["entry_price"]),
                        sl_price=float(opened["sl_price"]),
                        pnl_usd=row.get("pnl_usd"),
                        exit_event_type=ev,
                    )
                )

    still_open_count = sum(len(m) for m in active_by_key.values())
    grid_result = {
        "verified": (max_concurrent_observed <= max_concurrent_allowed and len(grid_violations) == 0),
        "max_concurrent_positions": max_concurrent_observed,
        "max_concurrent_allowed": max_concurrent_allowed,
        "still_open_positions_at_eod": still_open_count,
        "violations": grid_violations,
    }
    return grid_result, closed_positions


def _check_zero_martingale(
    closed_positions: Sequence[ClosedPositionSummary],
    *,
    lot_jump_ratio: float = DEFAULT_MARTINGALE_LOT_JUMP_RATIO,
) -> dict[str, Any]:
    """Verify no loss-conditioned lot doubling or multi-step martingale escalation."""
    if not math.isfinite(lot_jump_ratio) or lot_jump_ratio <= 1.0:
        raise ValueError(f"lot_jump_ratio must be finite and > 1.0, got {lot_jump_ratio!r}")

    grouped: dict[tuple[str, int], list[ClosedPositionSummary]] = {}
    for pos in closed_positions:
        grouped.setdefault((pos.canonical_symbol, pos.magic), []).append(pos)

    violations: list[dict[str, Any]] = []
    max_post_loss_ratio = 0.0
    post_loss_transitions_checked = 0

    for (canon_sym, magic), seq in sorted(grouped.items()):
        ordered = sorted(seq, key=lambda p: (p.open_ts, p.close_ts, p.position_key))
        streak_start_lots: float | None = None
        consecutive_losses = 0

        for idx in range(1, len(ordered)):
            prev_pos = ordered[idx - 1]
            curr_pos = ordered[idx]
            prev_is_loss = (prev_pos.pnl_usd is not None and float(prev_pos.pnl_usd) < 0.0) or (
                prev_pos.exit_event_type == "SL_HIT"
            )
            if not prev_is_loss:
                streak_start_lots = None
                consecutive_losses = 0
                continue

            post_loss_transitions_checked += 1
            if consecutive_losses == 0:
                streak_start_lots = prev_pos.lots
            consecutive_losses += 1

            if prev_pos.lots > 0.0 and curr_pos.lots > 0.0:
                ratio = round(curr_pos.lots / prev_pos.lots, 4)
                if ratio > max_post_loss_ratio:
                    max_post_loss_ratio = ratio
                if ratio >= lot_jump_ratio:
                    violations.append(
                        {
                            "reason": "LOSS_CONDITIONED_LOT_DOUBLING",
                            "canonical_symbol": canon_sym,
                            "magic": magic,
                            "prev_position_id": prev_pos.position_key,
                            "next_position_id": curr_pos.position_key,
                            "prev_pnl_usd": prev_pos.pnl_usd,
                            "prev_lots": prev_pos.lots,
                            "next_lots": curr_pos.lots,
                            "lot_ratio": ratio,
                            "threshold_ratio": lot_jump_ratio,
                        }
                    )
                elif (
                    consecutive_losses >= 2
                    and streak_start_lots is not None
                    and streak_start_lots > 0.0
                    and curr_pos.lots > prev_pos.lots
                    and (curr_pos.lots / streak_start_lots) >= lot_jump_ratio
                ):
                    cum_ratio = round(curr_pos.lots / streak_start_lots, 4)
                    if cum_ratio > max_post_loss_ratio:
                        max_post_loss_ratio = cum_ratio
                    violations.append(
                        {
                            "reason": "CONSECUTIVE_LOSS_SOFT_MARTINGALE_ESCALATION",
                            "canonical_symbol": canon_sym,
                            "magic": magic,
                            "prev_position_id": prev_pos.position_key,
                            "next_position_id": curr_pos.position_key,
                            "consecutive_losses": consecutive_losses,
                            "streak_start_lots": streak_start_lots,
                            "next_lots": curr_pos.lots,
                            "cumulative_lot_ratio": cum_ratio,
                            "threshold_ratio": lot_jump_ratio,
                        }
                    )

    return {
        "verified": len(violations) == 0,
        "lot_jump_threshold_ratio": lot_jump_ratio,
        "post_loss_transitions_checked": post_loss_transitions_checked,
        "max_post_loss_lot_ratio": max_post_loss_ratio,
        "violations": violations,
    }


def _check_zero_hft_tick_scalping(
    closed_positions: Sequence[ClosedPositionSummary],
    *,
    min_trade_duration_sec: int = DEFAULT_MIN_TRADE_DURATION_SEC,
    require_closed_positions: bool = True,
) -> dict[str, Any]:
    """Verify minimum trade holding duration (`>= 60s` default) to rule out HFT/tick scalping."""
    if isinstance(min_trade_duration_sec, bool) or min_trade_duration_sec <= 0:
        raise ValueError(f"min_trade_duration_sec must be positive int, got {min_trade_duration_sec!r}")

    violations: list[dict[str, Any]] = []
    durations: list[int] = []

    for pos in closed_positions:
        durations.append(pos.duration_sec)
        if pos.duration_sec < 0:
            violations.append(
                {
                    "reason": "NEGATIVE_TRADE_DURATION",
                    "position_id": pos.position_key,
                    "symbol": pos.symbol,
                    "magic": pos.magic,
                    "duration_sec": pos.duration_sec,
                    "min_required_sec": min_trade_duration_sec,
                }
            )
        elif pos.duration_sec < min_trade_duration_sec:
            violations.append(
                {
                    "reason": "SUB_THRESHOLD_TICK_SCALP",
                    "position_id": pos.position_key,
                    "symbol": pos.symbol,
                    "magic": pos.magic,
                    "open_ts": pos.open_ts,
                    "close_ts": pos.close_ts,
                    "duration_sec": pos.duration_sec,
                    "min_required_sec": min_trade_duration_sec,
                }
            )

    min_observed = min(durations) if durations else None
    has_required_sample = (len(closed_positions) > 0) or (not require_closed_positions)
    return {
        "verified": (len(violations) == 0 and has_required_sample),
        "min_duration_required_sec": min_trade_duration_sec,
        "closed_positions_checked": len(closed_positions),
        "min_duration_observed_sec": min_observed,
        "violations": violations,
    }


def _check_red_news_ban_clean(
    fill_rows: Sequence[Mapping[str, Any]],
    events: Sequence[ExtendedRedNewsEvent],
    *,
    hard_ban_sec: int = DEFAULT_RED_NEWS_HARD_BAN_SEC,
    calendar_sources: Sequence[str] = (),
    enforce_red_news_ban: bool = True,
) -> dict[str, Any]:
    """Verify 0 executed fills (entries or exits) fall inside `+-120s` restricted red-news hard ban."""
    if isinstance(hard_ban_sec, bool) or hard_ban_sec <= 0:
        raise ValueError(f"hard_ban_sec must be positive int, got {hard_ban_sec!r}")

    if not enforce_red_news_ban:
        return {
            "verified": True,
            "enforced": False,
            "hard_ban_sec": hard_ban_sec,
            "fills_checked": len(fill_rows),
            "calendar_events_loaded": len(events),
            "calendar_sources": list(calendar_sources),
            "violations": [],
        }

    violations: list[dict[str, Any]] = []
    for idx, row in enumerate(fill_rows):
        fill_ts = int(row["utc_ts"])
        sym = str(row.get("symbol") or "")
        for ev in events:
            delta = fill_ts - int(ev.utc_ts)
            if abs(delta) > hard_ban_sec:
                continue
            if not symbol_matches_event_code(sym, ev.ccy):
                continue
            violations.append(
                {
                    "fill_index": idx,
                    "utc_ts": fill_ts,
                    "symbol": sym,
                    "magic": row.get("magic"),
                    "event_type": row.get("event_type"),
                    "position_id": row.get("position_id") or row.get("ticket") or "",
                    "news_utc_iso": ev.utc_iso,
                    "news_ccy": ev.ccy,
                    "news_event": ev.event,
                    "delta_sec": delta,
                    "hard_ban_sec": hard_ban_sec,
                }
            )
            break

    return {
        "verified": len(violations) == 0,
        "enforced": True,
        "hard_ban_sec": hard_ban_sec,
        "fills_checked": len(fill_rows),
        "calendar_events_loaded": len(events),
        "calendar_sources": list(calendar_sources),
        "violations": violations,
    }


def _check_reconciliation_receipt(
    receipt: Mapping[str, Any],
    *,
    actual_audit_csv_sha256: str,
    require_zero_swap: bool = True,
    require_receipt_audit_sha: bool = True,
) -> dict[str, Any]:
    """Fail-closed inspection of `daily_statement_reconciler.py` receipt JSON."""
    fail_codes: list[str] = []

    passed_flag = receipt.get("passed")
    status_str = str(receipt.get("status") or "").strip().upper()
    if passed_flag is not True or status_str not in ("PASS", "NO_TRADES"):
        fail_codes.append(f"RECONCILIATION_NOT_PASSED:status={status_str or 'MISSING'},passed={passed_flag!r}")

    summary = receipt.get("summary")
    orphans_obj = receipt.get("orphans")
    if not isinstance(summary, Mapping):
        fail_codes.append("RECONCILIATION_SUMMARY_MISSING")
        return {
            "verified": False,
            "reconciliation_orphan_count": -1,
            "orphan_audit_count": -1,
            "orphan_statement_count": -1,
            "unresolved_fill_rows": -1,
            "missing_swap_count": -1,
            "nonzero_swap_count": -1,
            "audit_sha_matched": False,
            "fail_codes": fail_codes,
        }

    sum_orphan_audit = parse_optional_strict_int(summary.get("orphan_audit_count"), field_name="orphan_audit_count")
    sum_orphan_stmt = parse_optional_strict_int(
        summary.get("orphan_statement_count"), field_name="orphan_statement_count"
    )
    unresolved_rows = parse_optional_strict_int(summary.get("unresolved_fill_rows"), field_name="unresolved_fill_rows")
    missing_swap = parse_optional_strict_int(summary.get("missing_swap_count"), field_name="missing_swap_count")
    nonzero_swap = parse_optional_strict_int(summary.get("nonzero_swap_count"), field_name="nonzero_swap_count")

    list_orphan_audit = 0
    list_orphan_stmt = 0
    if isinstance(orphans_obj, Mapping):
        ao = orphans_obj.get("audit_only")
        so = orphans_obj.get("statement_only")
        if isinstance(ao, list):
            list_orphan_audit = len(ao)
        if isinstance(so, list):
            list_orphan_stmt = len(so)

    eff_orphan_audit = max(sum_orphan_audit if sum_orphan_audit is not None else 0, list_orphan_audit)
    eff_orphan_stmt = max(sum_orphan_stmt if sum_orphan_stmt is not None else 0, list_orphan_stmt)
    if sum_orphan_audit is None or sum_orphan_stmt is None:
        fail_codes.append("RECONCILIATION_ORPHAN_COUNTS_MISSING")
    total_orphans = eff_orphan_audit + eff_orphan_stmt
    if total_orphans > 0:
        fail_codes.append(
            f"RECONCILIATION_ORPHANS_PRESENT:audit={eff_orphan_audit},statement={eff_orphan_stmt}"
        )

    if unresolved_rows is None or unresolved_rows > 0:
        fail_codes.append(f"RECONCILIATION_UNRESOLVED_FILLS:{unresolved_rows}")

    if require_zero_swap:
        if missing_swap is None or missing_swap > 0:
            fail_codes.append(f"RECONCILIATION_MISSING_SWAP:{missing_swap}")
        if nonzero_swap is None or nonzero_swap > 0:
            fail_codes.append(f"RECONCILIATION_NONZERO_SWAP:{nonzero_swap}")

    # Cross-check receipt input audit SHA-256 against the exact audit CSV being packaged (fail-closed)
    inputs_obj = receipt.get("inputs")
    raw_rec_sha = inputs_obj.get("audit_csv_sha256") if isinstance(inputs_obj, Mapping) else None
    rec_audit_sha = raw_rec_sha.strip().lower() if isinstance(raw_rec_sha, str) else ""

    if not rec_audit_sha:
        audit_sha_matched = False
        if require_receipt_audit_sha:
            fail_codes.append("AUDIT_CSV_RECEIPT_SHA_MISSING")
    elif not _SHA256_HEX_RE.fullmatch(rec_audit_sha):
        audit_sha_matched = False
        fail_codes.append("AUDIT_CSV_RECEIPT_SHA_INVALID")
    elif rec_audit_sha != actual_audit_csv_sha256.lower():
        audit_sha_matched = False
        fail_codes.append("AUDIT_CSV_RECEIPT_SHA_MISMATCH")
    else:
        audit_sha_matched = True

    return {
        "verified": len(fail_codes) == 0,
        "receipt_status": status_str,
        "reconciliation_orphan_count": total_orphans,
        "orphan_audit_count": eff_orphan_audit,
        "orphan_statement_count": eff_orphan_stmt,
        "unresolved_fill_rows": -1 if unresolved_rows is None else unresolved_rows,
        "missing_swap_count": -1 if missing_swap is None else missing_swap,
        "nonzero_swap_count": -1 if nonzero_swap is None else nonzero_swap,
        "audit_sha_matched": audit_sha_matched,
        "fail_codes": fail_codes,
    }


def summarize_decision_blackbox(path: Path | str) -> dict[str, Any]:
    """Summarize optional decision blackbox JSON summary or JSONL file/directory (read-only)."""
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Decision blackbox path not found: {p}")

    if p.is_file() and p.suffix.lower() == ".json":
        raw_bytes = p.read_bytes()
        doc = json.loads(raw_bytes.decode("utf-8"))
        if not isinstance(doc, Mapping):
            raise ValueError(f"Decision blackbox JSON summary must be an object: {p}")
        return {
            "schema": BLACKBOX_SUMMARY_SCHEMA_VERSION,
            "source_mode": "precomputed_json",
            "source_files": [{"name": p.name, "sha256": _sha256_bytes(raw_bytes), "bytes": len(raw_bytes)}],
            "summary": dict(doc),
        }

    jsonl_files: list[Path]
    if p.is_dir():
        jsonl_files = sorted(f for f in p.iterdir() if f.is_file() and f.suffix.lower() == ".jsonl")
    else:
        jsonl_files = [p]

    if not jsonl_files:
        raise ValueError(f"No .jsonl decision blackbox files found under: {p}")

    total_records = 0
    decision_counts: dict[str, int] = {}
    strategy_shas: set[str] = set()
    preset_shas: set[str] = set()
    symbols_seen: set[str] = set()
    source_files: list[dict[str, Any]] = []

    for jf in jsonl_files:
        raw_bytes = jf.read_bytes()
        source_files.append({"name": jf.name, "sha256": _sha256_bytes(raw_bytes), "bytes": len(raw_bytes)})
        for line_no, raw_line in enumerate(raw_bytes.decode("utf-8").splitlines(), start=1):
            stripped = raw_line.strip()
            if not stripped:
                continue
            try:
                rec = json.loads(stripped)
            except json.JSONDecodeError as exc:
                raise ValueError(f"Corrupted decision blackbox JSONL {jf.name}:{line_no}: {exc}") from exc
            if not isinstance(rec, Mapping):
                raise ValueError(f"Decision blackbox JSONL line must be object {jf.name}:{line_no}")
            total_records += 1
            dec = str(rec.get("decision") or "UNKNOWN").strip().upper()
            decision_counts[dec] = decision_counts.get(dec, 0) + 1
            if rec.get("strategy_sha"):
                strategy_shas.add(str(rec["strategy_sha"]).strip())
            if rec.get("preset_sha"):
                preset_shas.add(str(rec["preset_sha"]).strip())
            if rec.get("symbol"):
                symbols_seen.add(str(rec["symbol"]).strip())

    return {
        "schema": BLACKBOX_SUMMARY_SCHEMA_VERSION,
        "source_mode": "jsonl_aggregated",
        "source_files": source_files,
        "total_records": total_records,
        "fire_count": decision_counts.get("FIRE", 0),
        "blocked_count": sum(v for k, v in decision_counts.items() if k.startswith("BLOCKED")),
        "decision_counts": dict(sorted(decision_counts.items())),
        "strategy_shas": sorted(strategy_shas),
        "preset_shas": sorted(preset_shas),
        "symbols": sorted(symbols_seen),
    }


def _extract_set_preset_metadata(raw_bytes: bytes, file_name: str) -> dict[str, Any]:
    """Parse safe non-secret metadata from an MT5 `.set` preset file."""
    if raw_bytes.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw_bytes.decode("utf-16", errors="replace")
    elif raw_bytes.startswith(b"\xef\xbb\xbf"):
        text = raw_bytes.decode("utf-8-sig", errors="replace")
    else:
        text = raw_bytes.decode("utf-8", errors="replace")

    params: dict[str, str] = {}
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith(";") or "=" not in s:
            continue
        k, v = s.split("=", 1)
        params[k.strip()] = v.split("||", 1)[0].strip()

    safe_keys = (
        "InpContractSku",
        "InpBasePhaseMult",
        "InpTargetProfitPct",
        "InpAmberDdPct",
        "InpRedDdPct",
        "InpKillDailyDdPct",
        "InpKillStaticDdPct",
        "InpAllowManualHaltFile",
        "InpGuardEnableRedNews",
        "InpGuardNewsPadSec",
        "InpGuardNewsHardBanSec",
        "InpDryRunLogOnly",
        "InpGuardDryRunLogOnly",
    )
    selected = {k: params[k] for k in safe_keys if k in params}
    return {
        "file_name": file_name,
        "sha256": _sha256_bytes(raw_bytes),
        "bytes": len(raw_bytes),
        "param_count": len(params),
        "selected_params": selected,
    }


def _compute_genesis_hash(cycle_id: str) -> str:
    return hashlib.sha256(f"{MANIFEST_SCHEMA_VERSION}|{cycle_id}|GENESIS".encode()).hexdigest()


def _compute_chain_link_hash(prev_hash: str, rel_path: str, artifact_sha256: str, artifact_bytes: int) -> str:
    payload = f"{prev_hash}|{rel_path}|{artifact_sha256}|{artifact_bytes}".encode()
    return hashlib.sha256(payload).hexdigest()


def evaluate_whitebox_compliance(
    *,
    audit_csv: Path | str,
    reconcile_receipt_json: Path | str,
    red_news_calendar_path: Path | str | None = None,
    red_news_events: Sequence[RedNewsEvent | ExtendedRedNewsEvent] | None = None,
    include_default_calendars: bool = True,
    enforce_red_news_ban: bool = True,
    red_news_hard_ban_sec: int = DEFAULT_RED_NEWS_HARD_BAN_SEC,
    min_trade_duration_sec: int = DEFAULT_MIN_TRADE_DURATION_SEC,
    martingale_lot_jump_ratio: float = DEFAULT_MARTINGALE_LOT_JUMP_RATIO,
    max_concurrent_same_symbol_magic: int = DEFAULT_MAX_CONCURRENT_SAME_SYM_MAGIC,
    require_zero_swap: bool = True,
    require_closed_positions: bool = True,
    require_receipt_audit_sha: bool = True,
) -> dict[str, Any]:
    """Evaluate all white-box prop compliance assertions directly from local read-only evidence."""
    if ORDER_SEND_CAPABLE or ORDER_SEND_COUNT != 0:
        raise RuntimeError("READONLY_INVARIANT_VIOLATION: payout_audit_packager is strictly read-only")

    audit_p = Path(audit_csv)
    receipt_p = Path(reconcile_receipt_json)
    if not audit_p.is_file():
        raise FileNotFoundError(f"Execution audit CSV not found: {audit_p}")
    if not receipt_p.is_file():
        raise FileNotFoundError(f"Reconciliation receipt JSON not found: {receipt_p}")

    audit_sha = sha256_file(audit_p)
    audit_rows = load_exec_audit_csv(audit_p)
    receipt_doc = json.loads(receipt_p.read_text(encoding="utf-8"))
    if not isinstance(receipt_doc, Mapping):
        raise ValueError(f"Reconciliation receipt must be a JSON object: {receipt_p}")

    unresolved_audit_rows = [r for r in audit_rows if is_unresolved_record(r)]
    fill_rows = [
        r
        for r in audit_rows
        if (not is_unresolved_record(r))
        and str(r.get("event_type") or "").strip().upper() in VALID_FILL_EVENT_TYPES
    ]
    entry_rows = [
        r
        for r in fill_rows
        if str(r.get("event_type") or "").strip().upper() in ENTRY_EVENT_TYPES
    ]
    non_fill_rows = [
        r
        for r in audit_rows
        if (not is_unresolved_record(r))
        and str(r.get("event_type") or "").strip().upper() in NON_FILL_EVENT_TYPES
    ]

    news_events, cal_sources = _load_red_news_events_for_audit(
        red_news_calendar_path=red_news_calendar_path,
        red_news_events=red_news_events,
        include_default_calendars=include_default_calendars,
    )

    sl_check = _check_hard_sl_attached(entry_rows)
    grid_check, closed_positions = _reconstruct_positions_and_check_grid(
        fill_rows,
        max_concurrent_allowed=max_concurrent_same_symbol_magic,
    )
    martingale_check = _check_zero_martingale(closed_positions, lot_jump_ratio=martingale_lot_jump_ratio)
    hft_check = _check_zero_hft_tick_scalping(
        closed_positions,
        min_trade_duration_sec=min_trade_duration_sec,
        require_closed_positions=require_closed_positions,
    )
    red_news_check = _check_red_news_ban_clean(
        fill_rows,
        news_events,
        hard_ban_sec=red_news_hard_ban_sec,
        calendar_sources=cal_sources,
        enforce_red_news_ban=enforce_red_news_ban,
    )
    reconcile_check = _check_reconciliation_receipt(
        receipt_doc,
        actual_audit_csv_sha256=audit_sha,
        require_zero_swap=require_zero_swap,
        require_receipt_audit_sha=require_receipt_audit_sha,
    )

    fail_reasons: list[str] = []
    if unresolved_audit_rows:
        fail_reasons.append(f"UNRESOLVED_AUDIT_FILLS:{len(unresolved_audit_rows)}")
    if not sl_check["verified"]:
        if sl_check["entries_checked"] == 0:
            fail_reasons.append("NO_EXECUTED_ENTRIES_FOUND")
        else:
            fail_reasons.append(
                f"MISSING_OR_INVALID_HARD_SL:attached_pct={sl_check['hard_sl_attached_pct']}"
            )
    if not grid_check["verified"]:
        fail_reasons.append(
            f"GRID_STACKING_DETECTED:max_concurrent={grid_check['max_concurrent_positions']}"
        )
    if not martingale_check["verified"]:
        fail_reasons.append(
            f"MARTINGALE_LOT_JUMP_DETECTED:max_ratio={martingale_check['max_post_loss_lot_ratio']}"
        )
    if not hft_check["verified"]:
        if hft_check["closed_positions_checked"] == 0 and require_closed_positions:
            fail_reasons.append("NO_CLOSED_POSITIONS_FOR_DURATION_CHECK")
        else:
            fail_reasons.append(
                f"HFT_TICK_SCALPING_DETECTED:min_sec={hft_check['min_duration_observed_sec']}"
            )
    if not red_news_check["verified"]:
        fail_reasons.append(
            f"RED_NEWS_HARD_BAN_BREACH:count={len(red_news_check['violations'])}"
        )
    if not reconcile_check["verified"]:
        fail_reasons.extend(reconcile_check["fail_codes"])

    certified = len(fail_reasons) == 0
    return {
        "schema": CERTIFICATION_SCHEMA_VERSION,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "certified": certified,
        "verdict": "CERTIFIED" if certified else "REJECTED_FAIL_CLOSED",
        "fail_reasons": fail_reasons,
        "assertions": {
            "hard_sl_attached_pct": sl_check["hard_sl_attached_pct"],
            "hard_sl_verified": sl_check["verified"],
            "zero_grid_verified": grid_check["verified"],
            "zero_martingale_verified": martingale_check["verified"],
            "zero_hft_tick_scalping": hft_check["verified"],
            "red_news_ban_clean": red_news_check["verified"],
            "reconciliation_orphan_count": reconcile_check["reconciliation_orphan_count"],
            "reconciliation_verified": reconcile_check["verified"],
            "unresolved_audit_count": len(unresolved_audit_rows),
        },
        "counts": {
            "audit_total_rows": len(audit_rows),
            "audit_fill_rows": len(fill_rows),
            "audit_entry_rows": len(entry_rows),
            "audit_non_fill_rows": len(non_fill_rows),
            "closed_positions": len(closed_positions),
        },
        "details": {
            "hard_sl": sl_check,
            "zero_grid": grid_check,
            "zero_martingale": martingale_check,
            "zero_hft_tick_scalping": hft_check,
            "red_news_ban": red_news_check,
            "reconciliation": reconcile_check,
        },
    }


def package_payout_audit_bundle(
    *,
    output_dir: Path | str,
    cycle_id: str,
    audit_csv: Path | str,
    reconcile_receipt_json: Path | str,
    firm_profile: str = "FTMO_STANDARD",
    account_phase: str = "FUNDED",
    account_alias: str = "NAQEX_ACCOUNT",
    decision_blackbox_path: Path | str | None = None,
    set_preset_path: Path | str | None = None,
    preset_sha256: str | None = None,
    ex5_path: Path | str | None = None,
    ex5_sha256: str | None = None,
    red_news_calendar_path: Path | str | None = None,
    red_news_events: Sequence[RedNewsEvent | ExtendedRedNewsEvent] | None = None,
    include_default_calendars: bool = True,
    enforce_red_news_ban: bool = True,
    red_news_hard_ban_sec: int = DEFAULT_RED_NEWS_HARD_BAN_SEC,
    min_trade_duration_sec: int = DEFAULT_MIN_TRADE_DURATION_SEC,
    martingale_lot_jump_ratio: float = DEFAULT_MARTINGALE_LOT_JUMP_RATIO,
    max_concurrent_same_symbol_magic: int = DEFAULT_MAX_CONCURRENT_SAME_SYM_MAGIC,
    require_zero_swap: bool = True,
    require_closed_positions: bool = True,
    require_receipt_audit_sha: bool = True,
    redact_for_layer1: bool = True,
    created_utc: str | None = None,
    raise_on_failure: bool = False,
) -> dict[str, Any]:
    """Package immutable payout evidence bundle with deterministic SHA-256 hash chain."""
    if ORDER_SEND_CAPABLE or ORDER_SEND_COUNT != 0:
        raise RuntimeError("READONLY_INVARIANT_VIOLATION: payout_audit_packager is strictly read-only")

    clean_cycle_id = str(cycle_id or "").strip()
    if not _SAFE_CYCLE_ID_RE.fullmatch(clean_cycle_id):
        raise ValueError(f"Invalid cycle_id (must match [A-Za-z0-9][A-Za-z0-9._-]{{0,79}}): {cycle_id!r}")

    out_dir = Path(output_dir)
    manifest_path = out_dir / "payout_audit_manifest.json"
    if manifest_path.exists():
        raise FileExistsError(
            f"IMMUTABLE_BUNDLE_EXISTS: refusing to overwrite existing manifest at {manifest_path}"
        )

    audit_p = Path(audit_csv)
    receipt_p = Path(reconcile_receipt_json)
    if not audit_p.is_file():
        raise FileNotFoundError(f"Execution audit CSV not found: {audit_p}")
    if not receipt_p.is_file():
        raise FileNotFoundError(f"Reconciliation receipt JSON not found: {receipt_p}")

    # Validate optional .ex5 SHA-256 or file input
    resolved_ex5_sha: str | None = None
    ex5_name: str | None = None
    ex5_bytes_len: int | None = None
    if ex5_path is not None:
        ep = Path(ex5_path)
        if not ep.is_file():
            raise FileNotFoundError(f"EX5 binary path not found: {ep}")
        resolved_ex5_sha = sha256_file(ep)
        ex5_name = ep.name
        ex5_bytes_len = ep.stat().st_size
    if ex5_sha256 is not None:
        norm_ex5_sha = str(ex5_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(norm_ex5_sha):
            raise ValueError(f"Invalid ex5_sha256 hex digest: {ex5_sha256!r}")
        if resolved_ex5_sha is not None and resolved_ex5_sha != norm_ex5_sha:
            raise ValueError(
                f"EX5_SHA256_MISMATCH: file digest {resolved_ex5_sha} != provided {norm_ex5_sha}"
            )
        resolved_ex5_sha = norm_ex5_sha

    # Validate optional .set preset SHA-256 or file input
    resolved_preset_sha: str | None = None
    preset_meta: dict[str, Any] | None = None
    preset_raw_bytes: bytes | None = None
    if set_preset_path is not None:
        sp = Path(set_preset_path)
        if not sp.is_file():
            raise FileNotFoundError(f"Preset .set file not found: {sp}")
        preset_raw_bytes = sp.read_bytes()
        preset_meta = _extract_set_preset_metadata(preset_raw_bytes, sp.name)
        resolved_preset_sha = preset_meta["sha256"]
    if preset_sha256 is not None:
        norm_p_sha = str(preset_sha256).strip().lower()
        if not _SHA256_HEX_RE.fullmatch(norm_p_sha):
            raise ValueError(f"Invalid preset_sha256 hex digest: {preset_sha256!r}")
        if resolved_preset_sha is not None and resolved_preset_sha != norm_p_sha:
            raise ValueError(
                f"PRESET_SHA256_MISMATCH: file digest {resolved_preset_sha} != provided {norm_p_sha}"
            )
        resolved_preset_sha = norm_p_sha

    # Run white-box compliance certification directly on raw read-only evidence
    cert_raw = evaluate_whitebox_compliance(
        audit_csv=audit_p,
        reconcile_receipt_json=receipt_p,
        red_news_calendar_path=red_news_calendar_path,
        red_news_events=red_news_events,
        include_default_calendars=include_default_calendars,
        enforce_red_news_ban=enforce_red_news_ban,
        red_news_hard_ban_sec=red_news_hard_ban_sec,
        min_trade_duration_sec=min_trade_duration_sec,
        martingale_lot_jump_ratio=martingale_lot_jump_ratio,
        max_concurrent_same_symbol_magic=max_concurrent_same_symbol_magic,
        require_zero_swap=require_zero_swap,
        require_closed_positions=require_closed_positions,
        require_receipt_audit_sha=require_receipt_audit_sha,
    )

    blackbox_summary_raw: dict[str, Any] | None = None
    if decision_blackbox_path is not None:
        blackbox_summary_raw = summarize_decision_blackbox(decision_blackbox_path)

    # Prepare deterministic artifacts directory
    artifacts_dir = out_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    artifact_records: list[dict[str, Any]] = []

    def _stage_bytes_artifact(rel_path: str, data: bytes, *, source_sha256: str, kind: str) -> None:
        target = out_dir / rel_path
        _write_atomic_bytes(target, data)
        artifact_records.append(
            {
                "relative_path": rel_path,
                "kind": kind,
                "artifact_sha256": _sha256_bytes(data),
                "artifact_bytes": len(data),
                "source_sha256": source_sha256,
            }
        )

    # 1. Execution audit CSV artifact
    raw_audit_bytes = audit_p.read_bytes()
    src_audit_sha = _sha256_bytes(raw_audit_bytes)
    staged_audit_bytes = _redact_audit_csv_bytes(raw_audit_bytes) if redact_for_layer1 else raw_audit_bytes
    _stage_bytes_artifact(
        "artifacts/exec_audit_evidence.csv",
        staged_audit_bytes,
        source_sha256=src_audit_sha,
        kind="exec_audit_csv",
    )

    # 2. Statement reconciliation receipt JSON artifact
    raw_receipt_bytes = receipt_p.read_bytes()
    src_receipt_sha = _sha256_bytes(raw_receipt_bytes)
    receipt_doc = json.loads(raw_receipt_bytes.decode("utf-8"))
    staged_receipt_obj = redact_payload_for_layer1(receipt_doc) if redact_for_layer1 else receipt_doc
    staged_receipt_bytes = (
        json.dumps(staged_receipt_obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    _stage_bytes_artifact(
        "artifacts/reconciliation_receipt.json",
        staged_receipt_bytes,
        source_sha256=src_receipt_sha,
        kind="reconciliation_receipt_json",
    )

    # 3. Compliance certification JSON artifact
    staged_cert_obj = redact_payload_for_layer1(cert_raw) if redact_for_layer1 else cert_raw
    staged_cert_bytes = (
        json.dumps(staged_cert_obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    _stage_bytes_artifact(
        "artifacts/compliance_certification.json",
        staged_cert_bytes,
        source_sha256=canonical_payload_sha256(cert_raw),
        kind="whitebox_compliance_certification",
    )

    # 4. Optional decision blackbox summary artifact
    if blackbox_summary_raw is not None:
        staged_bb_obj = redact_payload_for_layer1(blackbox_summary_raw) if redact_for_layer1 else blackbox_summary_raw
        staged_bb_bytes = (
            json.dumps(staged_bb_obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
        ).encode("utf-8")
        bb_src_sha = canonical_payload_sha256(blackbox_summary_raw)
        _stage_bytes_artifact(
            "artifacts/decision_blackbox_summary.json",
            staged_bb_bytes,
            source_sha256=bb_src_sha,
            kind="decision_blackbox_summary",
        )

    # 5. Optional .set preset snapshot artifact
    if preset_raw_bytes is not None and preset_meta is not None:
        if redact_for_layer1:
            preset_text = (
                preset_raw_bytes.decode("utf-8-sig", errors="replace").replace("\r\n", "\n").replace("\r", "\n")
            )
            staged_preset_bytes = redact_text_for_layer1(preset_text).encode("utf-8")
        else:
            staged_preset_bytes = preset_raw_bytes
        _stage_bytes_artifact(
            "artifacts/preset_snapshot.set",
            staged_preset_bytes,
            source_sha256=preset_meta["sha256"],
            kind="mt5_set_preset",
        )

    # 6. Binary & preset attestation record (never copies raw .ex5 binary into Layer-1 bundle)
    attestation_doc: dict[str, Any] = {
        "schema": EX5_ATTESTATION_SCHEMA_VERSION,
        "ex5_file_name": ex5_name,
        "ex5_sha256": resolved_ex5_sha,
        "ex5_bytes": ex5_bytes_len,
        "preset_file_name": preset_meta["file_name"] if preset_meta is not None else None,
        "preset_sha256": resolved_preset_sha,
        "preset_selected_params": preset_meta["selected_params"] if preset_meta is not None else None,
    }
    staged_att_obj = redact_payload_for_layer1(attestation_doc) if redact_for_layer1 else attestation_doc
    staged_att_bytes = (
        json.dumps(staged_att_obj, indent=2, sort_keys=True, ensure_ascii=False, allow_nan=False) + "\n"
    ).encode("utf-8")
    _stage_bytes_artifact(
        "artifacts/binary_and_preset_attestation.json",
        staged_att_bytes,
        source_sha256=canonical_payload_sha256(attestation_doc),
        kind="binary_and_preset_attestation",
    )

    # Build deterministic SHA-256 hash chain over lexicographically sorted artifacts
    artifact_records.sort(key=lambda item: item["relative_path"])
    genesis_hash = _compute_genesis_hash(clean_cycle_id)
    prev_hash = genesis_hash
    hash_chain: list[dict[str, Any]] = []
    for step_idx, rec in enumerate(artifact_records):
        link_hash = _compute_chain_link_hash(
            prev_hash,
            rec["relative_path"],
            rec["artifact_sha256"],
            int(rec["artifact_bytes"]),
        )
        hash_chain.append(
            {
                "step": step_idx,
                "relative_path": rec["relative_path"],
                "kind": rec["kind"],
                "artifact_sha256": rec["artifact_sha256"],
                "artifact_bytes": rec["artifact_bytes"],
                "source_sha256": rec["source_sha256"],
                "prev_hash": prev_hash,
                "chain_hash": link_hash,
            }
        )
        prev_hash = link_hash

    ts_utc = created_utc or datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    safe_alias = redact_text_for_layer1(account_alias) if redact_for_layer1 else str(account_alias)

    manifest_body: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA_VERSION,
        "created_utc": ts_utc,
        "cycle_id": clean_cycle_id,
        "firm_profile": str(firm_profile).strip().upper(),
        "account_phase": str(account_phase).strip().upper(),
        "account_alias": safe_alias,
        "redacted_for_layer1": bool(redact_for_layer1),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "certified": bool(cert_raw["certified"]),
        "payout_ready": bool(cert_raw["certified"]),
        "verdict": cert_raw["verdict"],
        "fail_reasons": list(cert_raw["fail_reasons"]),
        "compliance_assertions": dict(cert_raw["assertions"]),
        "provenance": {
            "audit_csv_name": audit_p.name,
            "audit_csv_sha256": src_audit_sha,
            "reconcile_receipt_name": receipt_p.name,
            "reconcile_receipt_sha256": src_receipt_sha,
            "preset_sha256": resolved_preset_sha,
            "ex5_sha256": resolved_ex5_sha,
            "decision_blackbox_included": blackbox_summary_raw is not None,
        },
        "hash_chain_spec": {
            "algorithm": "SHA-256",
            "genesis_hash": genesis_hash,
            "chain_head_sha256": prev_hash,
            "artifact_count": len(hash_chain),
        },
        "hash_chain": hash_chain,
    }

    receipt_info = write_atomic_sha256_json(manifest_path, manifest_body)
    manifest_out = dict(manifest_body)
    manifest_out["report_sha256"] = receipt_info["report_sha256"]
    manifest_out["manifest_path"] = str(manifest_path)

    if raise_on_failure and not manifest_out["certified"]:
        raise PayoutComplianceError(
            "PAYOUT_COMPLIANCE_REJECTED: " + "; ".join(manifest_out["fail_reasons"])
        )

    return manifest_out


def verify_payout_audit_bundle(
    bundle_dir: Path | str,
    *,
    require_certified: bool = True,
    reject_extra_artifacts: bool = True,
) -> dict[str, Any]:
    """Independently verify manifest SHA-256, every artifact digest, and full hash chain."""
    bdir = Path(bundle_dir)
    manifest_path = bdir / "payout_audit_manifest.json"
    errors: list[str] = []

    if not manifest_path.is_file():
        return {
            "verified": False,
            "integrity_ok": False,
            "certified": False,
            "errors": ["MANIFEST_MISSING"],
        }

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "verified": False,
            "integrity_ok": False,
            "certified": False,
            "errors": [f"MANIFEST_UNREADABLE:{type(exc).__name__}"],
        }

    if not isinstance(manifest, Mapping):
        return {
            "verified": False,
            "integrity_ok": False,
            "certified": False,
            "errors": ["MANIFEST_NOT_OBJECT"],
        }

    if manifest.get("schema") != MANIFEST_SCHEMA_VERSION:
        errors.append(f"UNSUPPORTED_MANIFEST_SCHEMA:{manifest.get('schema')!r}")

    # 1. Verify embedded canonical manifest SHA-256
    recorded_report_sha = str(manifest.get("report_sha256") or "").strip().lower()
    computed_report_sha = canonical_payload_sha256(manifest)
    manifest_sha_valid = bool(recorded_report_sha) and (recorded_report_sha == computed_report_sha)
    if not manifest_sha_valid:
        errors.append("MANIFEST_SHA256_MISMATCH")

    # 2. Recompute cryptographic SHA-256 hash chain from genesis through all artifacts
    cycle_id = str(manifest.get("cycle_id") or "")
    spec = manifest.get("hash_chain_spec")
    chain = manifest.get("hash_chain")
    expected_genesis = _compute_genesis_hash(cycle_id)
    hash_chain_valid = True
    expected_rel_paths: set[str] = set()

    if not isinstance(spec, Mapping) or not isinstance(chain, list):
        hash_chain_valid = False
        errors.append("HASH_CHAIN_STRUCTURE_INVALID")
    else:
        if spec.get("genesis_hash") != expected_genesis:
            hash_chain_valid = False
            errors.append("GENESIS_HASH_MISMATCH")

        prev_hash = expected_genesis
        for idx, link in enumerate(chain):
            if not isinstance(link, Mapping):
                hash_chain_valid = False
                errors.append(f"HASH_CHAIN_LINK_NOT_OBJECT:{idx}")
                continue
            rel_path = str(link.get("relative_path") or "")
            expected_rel_paths.add(rel_path)
            # Prevent path traversal outside bundle directory
            target_path = (bdir / rel_path).resolve()
            try:
                target_path.relative_to(bdir.resolve())
            except ValueError:
                hash_chain_valid = False
                errors.append(f"PATH_TRAVERSAL_REJECTED:{rel_path}")
                continue

            if not target_path.is_file():
                hash_chain_valid = False
                errors.append(f"ARTIFACT_MISSING:{rel_path}")
                continue

            actual_bytes = target_path.read_bytes()
            actual_sha = _sha256_bytes(actual_bytes)
            actual_len = len(actual_bytes)

            if actual_sha != str(link.get("artifact_sha256") or ""):
                hash_chain_valid = False
                errors.append(f"ARTIFACT_SHA256_MISMATCH:{rel_path}")
            if actual_len != int(link.get("artifact_bytes") or -1):
                hash_chain_valid = False
                errors.append(f"ARTIFACT_BYTES_MISMATCH:{rel_path}")
            if str(link.get("prev_hash") or "") != prev_hash:
                hash_chain_valid = False
                errors.append(f"CHAIN_PREV_HASH_MISMATCH:{rel_path}")

            recomputed_link = _compute_chain_link_hash(prev_hash, rel_path, actual_sha, actual_len)
            if recomputed_link != str(link.get("chain_hash") or ""):
                hash_chain_valid = False
                errors.append(f"CHAIN_HASH_MISMATCH:{rel_path}")
            prev_hash = recomputed_link

        if prev_hash != str(spec.get("chain_head_sha256") or ""):
            hash_chain_valid = False
            errors.append("CHAIN_HEAD_SHA256_MISMATCH")
        if int(spec.get("artifact_count") or -1) != len(chain):
            hash_chain_valid = False
            errors.append("ARTIFACT_COUNT_MISMATCH")

    # 3. Check for unindexed/injected extra files inside artifacts/
    if reject_extra_artifacts:
        art_dir = bdir / "artifacts"
        if art_dir.is_dir():
            for p in sorted(art_dir.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(bdir).as_posix()
                    if rel not in expected_rel_paths:
                        hash_chain_valid = False
                        errors.append(f"UNEXPECTED_EXTRA_ARTIFACT:{rel}")

    integrity_ok = manifest_sha_valid and hash_chain_valid and len(errors) == 0
    certified_flag = manifest.get("certified") is True and manifest.get("verdict") == "CERTIFIED"
    if require_certified and not certified_flag:
        errors.append("BUNDLE_NOT_CERTIFIED")

    verified = integrity_ok and (certified_flag if require_certified else True)
    return {
        "verified": verified,
        "integrity_ok": integrity_ok,
        "manifest_sha_valid": manifest_sha_valid,
        "hash_chain_valid": hash_chain_valid,
        "certified": certified_flag,
        "cycle_id": cycle_id,
        "artifacts_verified": len(expected_rel_paths),
        "errors": errors,
        "order_send_count": ORDER_SEND_COUNT,
    }


def _build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description="Immutable White-Box Payout Audit Trail Packager & Hash-Chain Verifier (OrderSend=0)."
    )
    sub = ap.add_subparsers(dest="command", required=True)

    pkg = sub.add_parser("package", help="Package and certify a payout audit evidence bundle.")
    pkg.add_argument("--output-dir", type=Path, required=True)
    pkg.add_argument("--cycle-id", type=str, required=True)
    pkg.add_argument("--audit-csv", type=Path, required=True)
    pkg.add_argument("--reconcile-receipt", type=Path, required=True)
    pkg.add_argument("--firm-profile", type=str, default="FTMO_STANDARD")
    pkg.add_argument("--account-phase", type=str, default="FUNDED")
    pkg.add_argument("--account-alias", type=str, default="NAQEX_ACCOUNT")
    pkg.add_argument("--decision-blackbox", type=Path, default=None)
    pkg.add_argument("--set-preset", type=Path, default=None)
    pkg.add_argument("--preset-sha256", type=str, default=None)
    pkg.add_argument("--ex5-path", type=Path, default=None)
    pkg.add_argument("--ex5-sha256", type=str, default=None)
    pkg.add_argument("--red-news-calendar", type=Path, default=None)
    pkg.add_argument("--hard-ban-sec", type=int, default=DEFAULT_RED_NEWS_HARD_BAN_SEC)
    pkg.add_argument("--min-duration-sec", type=int, default=DEFAULT_MIN_TRADE_DURATION_SEC)
    pkg.add_argument("--martingale-ratio", type=float, default=DEFAULT_MARTINGALE_LOT_JUMP_RATIO)
    pkg.add_argument("--allow-nonzero-swap", action="store_true")
    pkg.add_argument("--disable-red-news-ban", action="store_true")
    pkg.add_argument("--no-redact", action="store_true", help="Disable Layer-1 OPSEC redaction (private_vault only).")

    ver = sub.add_parser("verify", help="Verify SHA-256 integrity and hash chain of an existing bundle.")
    ver.add_argument("--bundle-dir", type=Path, required=True)
    ver.add_argument("--integrity-only", action="store_true", help="Verify hash chain even if bundle is uncertified.")
    return ap


def main(argv: Sequence[str] | None = None) -> int:
    ap = _build_arg_parser()
    args = ap.parse_args(list(argv) if argv is not None else None)

    if args.command == "package":
        manifest = package_payout_audit_bundle(
            output_dir=args.output_dir,
            cycle_id=args.cycle_id,
            audit_csv=args.audit_csv,
            reconcile_receipt_json=args.reconcile_receipt,
            firm_profile=args.firm_profile,
            account_phase=args.account_phase,
            account_alias=args.account_alias,
            decision_blackbox_path=args.decision_blackbox,
            set_preset_path=args.set_preset,
            preset_sha256=args.preset_sha256,
            ex5_path=args.ex5_path,
            ex5_sha256=args.ex5_sha256,
            red_news_calendar_path=args.red_news_calendar,
            enforce_red_news_ban=not bool(args.disable_red_news_ban),
            red_news_hard_ban_sec=int(args.hard_ban_sec),
            min_trade_duration_sec=int(args.min_duration_sec),
            martingale_lot_jump_ratio=float(args.martingale_ratio),
            require_zero_swap=not bool(args.allow_nonzero_swap),
            redact_for_layer1=not bool(args.no_redact),
        )
        print(json.dumps(manifest, indent=2, ensure_ascii=False))
        return 0 if manifest["certified"] else 2

    if args.command == "verify":
        res = verify_payout_audit_bundle(
            args.bundle_dir,
            require_certified=not bool(args.integrity_only),
        )
        print(json.dumps(res, indent=2, ensure_ascii=False))
        return 0 if res["verified"] else 2

    return 2


__all__ = [
    "BLACKBOX_SUMMARY_SCHEMA_VERSION",
    "CERTIFICATION_SCHEMA_VERSION",
    "ClosedPositionSummary",
    "DEFAULT_MARTINGALE_LOT_JUMP_RATIO",
    "DEFAULT_MAX_CONCURRENT_SAME_SYM_MAGIC",
    "DEFAULT_MIN_TRADE_DURATION_SEC",
    "DEFAULT_RED_NEWS_HARD_BAN_SEC",
    "EX5_ATTESTATION_SCHEMA_VERSION",
    "MANIFEST_SCHEMA_VERSION",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PayoutComplianceError",
    "evaluate_whitebox_compliance",
    "main",
    "package_payout_audit_bundle",
    "redact_payload_for_layer1",
    "redact_text_for_layer1",
    "sha256_file",
    "summarize_decision_blackbox",
    "verify_payout_audit_bundle",
]

if __name__ == "__main__":
    raise SystemExit(main())
