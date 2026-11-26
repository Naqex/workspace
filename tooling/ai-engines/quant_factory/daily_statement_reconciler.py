"""Automated Daily Broker Statement vs Execution Audit Reconciler (Read-Only, OrderSend=0).

Reconciles MT5 / FTMO MetriX broker statement exports (CSV or HTML) against
`naqex_exec_audit.csv` and an optional quote tape (JSONL or CSV):

  1. Matches fills 1-to-1 across `deal_id` -> `ticket` -> `order_id` -> `position_id` -> `magic`.
  2. Flags orphan audit fills (missing on broker statement) and orphan broker statement rows
     (missing in `naqex_exec_audit.csv`), plus `login`, `magic`, `symbol`, `pnl`, and `swap` mismatches.
  3. Enriches blank `swap_usd` / `pnl_usd` / `commission_usd` on audit rows from matched broker
     statement rows BEFORE running the fail-closed post-reconciliation gate (`quant_core.tca`).
  4. Verifies `swap_usd == 0.00` (fail-closed if STILL `None`/missing, non-finite, or non-zero)
     and blocks `FILL_UNRESOLVED` fail-closed.
  5. Computes strictly causal `+1s/+10s/+60s/+5m` Markout Curve when a quote tape is supplied.
  6. Writes an atomic SHA-256 JSON receipt (`write_atomic_sha256_json`).

SAFETY INVARIANTS:
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0` (never imports `MetaTrader5`).
  - Strictly read-only on all input files; never opens network connections.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

QUANT_FACTORY_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = QUANT_FACTORY_DIR.parent
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import (  # noqa: E402
    DEFAULT_MARKOUT_HORIZONS_SEC,
    ENTRY_EVENT_TYPES,
    EXIT_EVENT_TYPES,
    NON_FILL_EVENT_TYPES,
    VALID_FILL_EVENT_TYPES,
    compute_markout_curve,
    extract_comment_tags,
    is_unresolved_record,
    load_exec_audit_csv,
    load_quote_tape,
    normalize_symbol_alias,
    parse_optional_finite_float,
    parse_optional_strict_int,
    validate_tca_post_reconcile,
    write_atomic_sha256_json,
)

SCHEMA_VERSION = "naqex-daily-statement-reconcile-v1"
ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

_MAX_STATEMENT_BYTES = 16 * 1024 * 1024
_MAX_HTML_ROWS = 50_010
_MAX_HTML_CELL_CHARS = 65_536

_NON_TRADE_TYPES: frozenset[str] = frozenset({
    "balance",
    "credit",
    "charge",
    "correction",
    "bonus",
    "commission",
    "interest",
})

_HTML_COL_ALIASES: dict[str, str] = {
    "time": "time",
    "opentime": "open_time",
    "closetime": "close_time",
    "deal": "deal_id",
    "dealid": "deal_id",
    "ticket": "ticket",
    "order": "order_id",
    "orderid": "order_id",
    "position": "position_id",
    "positionid": "position_id",
    "magic": "magic",
    "magicnumber": "magic",
    "login": "account_login",
    "account": "account_login",
    "accountlogin": "account_login",
    "symbol": "symbol",
    "item": "symbol",
    "type": "side",
    "side": "side",
    "direction": "direction",
    "entry": "direction",
    "volume": "volume",
    "size": "volume",
    "lots": "volume",
    "price": "price",
    "fillprice": "price",
    "openprice": "price",
    "closeprice": "close_price",
    "profit": "pnl_usd",
    "pnl": "pnl_usd",
    "pnlusd": "pnl_usd",
    "swap": "swap_usd",
    "swapusd": "swap_usd",
    "commission": "commission_usd",
    "commissionusd": "commission_usd",
    "fee": "fee_usd",
    "balance": "balance",
    "state": "state",
    "comment": "comment",
}

_ACCOUNT_LOGIN_RE = re.compile(r"\b(?:account|login)\s*[:#]?\s*(\d{5,12})\b", re.IGNORECASE)


def _norm_header_key(text: str) -> str:
    return re.sub(r"[^a-z0-9]", "", str(text).casefold())


def _decode_statement_bytes(raw: bytes) -> str:
    if len(raw) > _MAX_STATEMENT_BYTES:
        raise ValueError(f"STATEMENT_SIZE_LIMIT_EXCEEDED: {len(raw)} > {_MAX_STATEMENT_BYTES}")
    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw.decode("utf-16")
    try:
        return raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        m = re.search(rb"charset\s*=\s*[\"']?([\w-]+)", raw[:4096], re.IGNORECASE)
        enc = m.group(1).decode("ascii").casefold() if m else "windows-1252"
        if enc not in {"windows-1252", "windows-1251", "iso-8859-1"}:
            raise ValueError(f"UNSUPPORTED_STATEMENT_ENCODING: {enc}") from None
        return raw.decode(enc)


def _parse_optional_timestamp(raw: Any) -> int | None:
    if raw is None:
        return None
    s = str(raw).strip()
    if not s:
        return None
    # Numeric epoch seconds
    try:
        ival = parse_optional_strict_int(s, field_name="utc_ts")
        if ival is not None and ival > 0:
            return ival
    except ValueError:
        pass
    # MT5 dotted format: 2026.11.02 09:05:00 or ISO-8601
    norm = s[:10].replace(".", "-") + s[10:] if re.match(r"^\d{4}\.\d{2}\.\d{2}", s) else s
    if norm.endswith("Z"):
        norm = norm[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(norm)
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return int(dt.timestamp())


class _BoundedHtmlTableParser(HTMLParser):
    """Safe bounded stdlib HTML table extractor for MT5 statement HTML reports."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[list[str]] = []
        self.text_chunks: list[str] = []
        self._in_row = False
        self._in_cell = False
        self._current_row: list[str] = []
        self._current_cell: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t == "tr":
            self._in_row = True
            self._current_row = []
        elif t in ("td", "th") and self._in_row:
            self._in_cell = True
            self._current_cell = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in ("td", "th") and self._in_cell:
            self._in_cell = False
            self._current_row.append("".join(self._current_cell).strip())
        elif t == "tr" and self._in_row:
            self._in_row = False
            if self._current_row:
                self.rows.append(self._current_row)
                if len(self.rows) > _MAX_HTML_ROWS:
                    raise ValueError("STATEMENT_HTML_ROW_LIMIT_EXCEEDED")

    def handle_data(self, data: str) -> None:
        if len(data) > _MAX_HTML_CELL_CHARS:
            raise ValueError("STATEMENT_HTML_CELL_LIMIT_EXCEEDED")
        if self._in_cell:
            self._current_cell.append(data)
        elif data.strip():
            self.text_chunks.append(data.strip())


def _canonicalize_statement_row(raw: Mapping[str, Any], *, default_login: int | None = None) -> dict[str, Any] | None:
    """Normalize a broker statement row (from CSV or HTML) into canonical schema."""
    comment = str(raw.get("comment") or "").strip()
    tags = extract_comment_tags(comment)

    side = str(raw.get("side") or raw.get("type") or "").strip().upper()
    if side.casefold() in _NON_TRADE_TYPES:
        return None

    deal_id = str(raw.get("deal_id") or raw.get("deal") or tags.get("deal") or "").strip()
    ticket = str(raw.get("ticket") or tags.get("tk") or deal_id or "").strip()
    order_id = str(raw.get("order_id") or raw.get("order") or tags.get("ord") or "").strip()
    position_id = str(raw.get("position_id") or raw.get("position") or tags.get("pos") or "").strip()

    if not (deal_id or ticket or order_id or position_id):
        return None

    login_raw = raw.get("account_login") if "account_login" in raw else raw.get("login")
    account_login = parse_optional_strict_int(login_raw, field_name="statement.account_login")
    if account_login is None:
        account_login = default_login

    magic_raw = raw.get("magic") if "magic" in raw else tags.get("magic")
    magic = parse_optional_strict_int(magic_raw, field_name="statement.magic") or 0

    symbol = str(raw.get("symbol") or "").strip()
    direction = str(raw.get("direction") or raw.get("entry") or "").strip().upper()
    volume = parse_optional_finite_float(
        raw.get("volume") if "volume" in raw else raw.get("lots"),
        field_name="statement.volume",
    )
    price = parse_optional_finite_float(
        raw.get("price") if "price" in raw else raw.get("fill_price"),
        field_name="statement.price",
    )
    # CRITICAL P0-7: preserve blank swap/pnl as None — NEVER silently coerce "" -> 0.0!
    pnl_raw = raw.get("pnl_usd") if "pnl_usd" in raw else raw.get("profit")
    swap_raw = raw.get("swap_usd") if "swap_usd" in raw else raw.get("swap")
    comm_raw = raw.get("commission_usd") if "commission_usd" in raw else raw.get("commission")

    pnl_usd = parse_optional_finite_float(pnl_raw, field_name="statement.pnl_usd")
    swap_usd = parse_optional_finite_float(swap_raw, field_name="statement.swap_usd")
    commission_usd = parse_optional_finite_float(comm_raw, field_name="statement.commission_usd")

    ts_raw = (
        raw.get("utc_ts")
        if "utc_ts" in raw
        else (raw.get("time") or raw.get("close_time") or raw.get("open_time"))
    )
    utc_ts = _parse_optional_timestamp(ts_raw)

    return {
        "account_login": account_login,
        "deal_id": deal_id,
        "ticket": ticket,
        "order_id": order_id,
        "position_id": position_id,
        "magic": magic,
        "symbol": symbol,
        "canonical_symbol": normalize_symbol_alias(symbol),
        "side": side,
        "direction": direction,
        "volume": 0.0 if volume is None else volume,
        "price": 0.0 if price is None else price,
        "pnl_usd": pnl_usd,
        "swap_usd": swap_usd,
        "commission_usd": commission_usd,
        "utc_ts": utc_ts,
        "comment": comment,
    }


def _load_statement_csv(text: str, *, source_name: str) -> tuple[list[dict[str, Any]], int | None, int]:
    rows: list[dict[str, Any]] = []
    ignored_non_trade = 0
    lines = text.splitlines()
    reader = csv.DictReader(lines)
    for line_no, raw in enumerate(reader, start=2):
        if not raw or all(str(v or "").strip() == "" for v in raw.values()):
            continue
        norm_raw: dict[str, Any] = {}
        for k, v in raw.items():
            if k is None:
                continue
            nk = _HTML_COL_ALIASES.get(_norm_header_key(k), k.strip().lower())
            norm_raw[nk] = v
        try:
            canon = _canonicalize_statement_row(norm_raw)
        except ValueError as exc:
            raise ValueError(f"{source_name}:{line_no}: {exc}") from exc
        if canon is None:
            ignored_non_trade += 1
            continue
        rows.append(canon)
    detected_login = next((r["account_login"] for r in rows if r["account_login"] is not None), None)
    return rows, detected_login, ignored_non_trade


def _load_statement_html(text: str, *, source_name: str) -> tuple[list[dict[str, Any]], int | None, int]:
    parser = _BoundedHtmlTableParser()
    parser.feed(text)

    # Detect account login from HTML metadata rows or header text
    detected_login: int | None = None
    for row in parser.rows[:25]:
        joined = " ".join(row)
        m = _ACCOUNT_LOGIN_RE.search(joined)
        if m:
            detected_login = int(m.group(1))
            break
    if detected_login is None:
        for chunk in parser.text_chunks[:50]:
            m = _ACCOUNT_LOGIN_RE.search(chunk)
            if m:
                detected_login = int(m.group(1))
                break

    deals_rows: list[dict[str, Any]] = []
    position_rows: list[dict[str, Any]] = []
    ignored_non_trade = 0
    active_headers: list[str] | None = None
    active_section: str | None = None

    for row_idx, row in enumerate(parser.rows, start=1):
        mapped = [_HTML_COL_ALIASES.get(_norm_header_key(cell), "") for cell in row]
        mapped_set = {m for m in mapped if m}
        # Detect table header rows & distinguish Deals vs Orders vs Positions sections
        has_deal = "deal_id" in mapped_set
        has_ticket = "ticket" in mapped_set
        has_pos = "position_id" in mapped_set
        has_order = "order_id" in mapped_set
        has_state = "state" in mapped_set
        has_financials = bool(mapped_set & {"pnl_usd", "swap_usd", "commission_usd"})
        has_trade_cols = {"symbol", "side"} <= mapped_set or {"symbol", "price"} <= mapped_set

        if (has_deal or has_ticket or has_pos or has_order) and has_trade_cols:
            if has_deal:
                active_section = "deals"
            elif has_state or (has_order and not has_pos and not has_ticket and not has_financials):
                # MT5 Orders table (Open Time / Order / Symbol / Type / Volume / Price / State) — skip!
                active_section = "orders"
                active_headers = None
                continue
            elif has_pos or has_ticket or has_financials:
                active_section = "positions"
            else:
                active_section = "orders"
                active_headers = None
                continue

            # Disambiguate repeated Time/Price columns in MT5 Positions tables
            deduped: list[str] = []
            seen: dict[str, int] = {}
            for col in mapped:
                if col:
                    seen[col] = seen.get(col, 0) + 1
                    if col == "price" and seen[col] > 1:
                        deduped.append("close_price")
                    elif col == "time" and seen[col] > 1:
                        deduped.append("close_time")
                    else:
                        deduped.append(col)
                else:
                    deduped.append("")
            active_headers = deduped
            continue

        if active_headers is None or active_section not in ("deals", "positions"):
            continue
        if len(row) != len(active_headers):
            # Section separator or summary footer resets current table header
            active_headers = None
            active_section = None
            continue

        raw_dict = {hdr: val for hdr, val in zip(active_headers, row, strict=True) if hdr}
        # Skip non-trade summary rows (e.g., Balance / Total)
        side_str = str(raw_dict.get("side") or "").strip().casefold()
        if side_str in _NON_TRADE_TYPES or (side_str and side_str not in {"buy", "sell"}):
            ignored_non_trade += 1
            continue
        try:
            canon = _canonicalize_statement_row(raw_dict, default_login=detected_login)
        except ValueError as exc:
            raise ValueError(f"{source_name}:html_row_{row_idx}: {exc}") from exc
        if canon is None:
            ignored_non_trade += 1
            continue
        if active_section == "deals":
            deals_rows.append(canon)
        else:
            position_rows.append(canon)

    # Prefer Deals section when present (1:1 with entry/exit exec audit rows); fall back to Positions otherwise
    trade_rows = deals_rows if deals_rows else position_rows
    if detected_login is None:
        detected_login = next((r["account_login"] for r in trade_rows if r["account_login"] is not None), None)
    return trade_rows, detected_login, ignored_non_trade


def load_mt5_statement(statement_path: Path | str) -> dict[str, Any]:
    """Load MT5 / FTMO broker statement from CSV or HTML (strictly read-only)."""
    path = Path(statement_path)
    raw = path.read_bytes()
    file_sha256 = hashlib.sha256(raw).hexdigest()
    text = _decode_statement_bytes(raw)
    suffix = path.suffix.lower()

    is_html = suffix in {".htm", ".html"} or "<table" in text[:4096].lower()
    if is_html:
        rows, detected_login, ignored_non_trade = _load_statement_html(text, source_name=path.name)
        fmt = "html"
    else:
        rows, detected_login, ignored_non_trade = _load_statement_csv(text, source_name=path.name)
        fmt = "csv"

    return {
        "format": fmt,
        "file_name": path.name,
        "sha256": file_sha256,
        "detected_login": detected_login,
        "rows": rows,
        "ignored_non_trade_rows": ignored_non_trade,
    }


def _file_sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _direction_matches(audit_ev: str, stmt_dir: str) -> bool:
    if not stmt_dir:
        return True
    is_exit = audit_ev in EXIT_EVENT_TYPES
    is_entry = audit_ev in ENTRY_EVENT_TYPES
    sd = stmt_dir.upper()
    if is_exit and sd in {"OUT", "IN/OUT", "OUT_BY", "CLOSE"}:
        return True
    if is_entry and sd in {"IN", "OPEN"}:
        return True
    return False


# ---------------------------------------------------------------------------
# Core Reconciliation Orchestrator
# ---------------------------------------------------------------------------
def reconcile_daily_statement(
    *,
    audit_csv: Path | str,
    statement_path: Path | str,
    quote_tape_path: Path | str | None = None,
    quote_series: Mapping[str, Sequence[Mapping[str, Any]]] | Iterable[Mapping[str, Any]] | None = None,
    expected_login: int | None = None,
    allowed_magics: Iterable[int] | None = None,
    horizons_sec: Sequence[int] = DEFAULT_MARKOUT_HORIZONS_SEC,
    require_zero_swap: bool = True,
    swap_tolerance_usd: float = 0.0,
    pnl_tolerance_usd: float = 0.05,
    out_json: Path | str | None = None,
) -> dict[str, Any]:
    """Reconcile `naqex_exec_audit.csv` against MT5 statement CSV/HTML & optional quote tape."""
    if ORDER_SEND_CAPABLE or ORDER_SEND_COUNT != 0:
        raise RuntimeError("READONLY_INVARIANT_VIOLATION: daily_statement_reconciler is strictly read-only")

    audit_p = Path(audit_csv)
    stmt_p = Path(statement_path)
    quote_p = Path(quote_tape_path) if quote_tape_path is not None else None

    audit_all = load_exec_audit_csv(audit_p)
    stmt_bundle = load_mt5_statement(stmt_p)
    stmt_rows: list[dict[str, Any]] = stmt_bundle["rows"]

    allowed_magic_set = {int(m) for m in allowed_magics} if allowed_magics is not None else None

    unresolved_rows: list[dict[str, Any]] = []
    non_fill_rows: list[dict[str, Any]] = []
    audit_fills: list[dict[str, Any]] = []

    for row in audit_all:
        if is_unresolved_record(row):
            unresolved_rows.append(row)
            continue
        ev = str(row.get("event_type") or "").strip().upper()
        if ev in NON_FILL_EVENT_TYPES:
            non_fill_rows.append(row)
            continue
        if ev in VALID_FILL_EVENT_TYPES:
            audit_fills.append(row)
        else:
            non_fill_rows.append(row)

    # Check account login alignment fail-closed
    stmt_logins_set: set[int] = {int(r["account_login"]) for r in stmt_rows if r.get("account_login") is not None}
    if stmt_bundle["detected_login"] is not None:
        stmt_logins_set.add(int(stmt_bundle["detected_login"]))
    stmt_logins = sorted(stmt_logins_set)
    audit_logins = sorted({int(r["account_login"]) for r in audit_fills if r.get("account_login") is not None})

    login_mismatch = False
    login_mismatch_detail: str | None = None
    if expected_login is not None:
        if stmt_rows and (not stmt_logins or any(r.get("account_login") is None for r in stmt_rows)):
            login_mismatch = True
            login_mismatch_detail = (
                f"statement has {len(stmt_rows)} row(s) with missing account login "
                f"(expected_login={expected_login})"
            )
        elif any(x != expected_login for x in stmt_logins):
            login_mismatch = True
            login_mismatch_detail = f"statement logins {stmt_logins} != expected_login={expected_login}"
        elif any(x != expected_login for x in audit_logins):
            login_mismatch = True
            login_mismatch_detail = f"audit logins {audit_logins} != expected_login={expected_login}"
    else:
        if len(stmt_logins) > 1:
            login_mismatch = True
            login_mismatch_detail = f"multiple account logins in statement: {stmt_logins}"
        elif len(audit_logins) > 1:
            login_mismatch = True
            login_mismatch_detail = f"multiple account logins in audit: {audit_logins}"
        elif stmt_logins and audit_logins and stmt_logins != audit_logins:
            login_mismatch = True
            login_mismatch_detail = f"audit logins {audit_logins} != statement logins {stmt_logins}"

    # Build 1-to-1 statement indices (consuming matched statement indices to catch duplicates/orphans)
    used_stmt_idx: set[int] = set()
    idx_by_deal: dict[str, list[int]] = {}
    idx_by_ticket: dict[str, list[int]] = {}
    idx_by_order: dict[str, list[int]] = {}
    idx_by_pos: dict[str, list[int]] = {}

    for si, sr in enumerate(stmt_rows):
        if sr["deal_id"]:
            idx_by_deal.setdefault(sr["deal_id"], []).append(si)
        if sr["ticket"]:
            idx_by_ticket.setdefault(sr["ticket"], []).append(si)
        if sr["order_id"]:
            idx_by_order.setdefault(sr["order_id"], []).append(si)
        if sr["position_id"]:
            idx_by_pos.setdefault(sr["position_id"], []).append(si)

    def _pick_first_unused(candidates: Sequence[int], audit_ev: str, audit_sym: str) -> int | None:
        # Prefer direction + symbol match first, then any unused candidate
        for ci in candidates:
            if ci in used_stmt_idx:
                continue
            sr = stmt_rows[ci]
            if _direction_matches(audit_ev, sr["direction"]) and (
                not audit_sym or not sr["canonical_symbol"] or sr["canonical_symbol"] == audit_sym
            ):
                return ci
        for ci in candidates:
            if ci not in used_stmt_idx:
                return ci
        return None

    matched_pairs: list[dict[str, Any]] = []
    orphan_audit_rows: list[dict[str, Any]] = []
    enriched_fills: list[dict[str, Any]] = []
    magic_mismatches: list[dict[str, Any]] = []
    symbol_mismatches: list[dict[str, Any]] = []
    swap_discrepancies: list[dict[str, Any]] = []
    pnl_discrepancies: list[dict[str, Any]] = []
    swap_enriched_count = 0
    pnl_enriched_count = 0

    for ai, ar in enumerate(audit_fills):
        ev = str(ar["event_type"])
        audit_sym = str(ar["canonical_symbol"])
        matched_si: int | None = None
        match_key = ""

        if ar["deal_id"] and ar["deal_id"] in idx_by_deal:
            matched_si = _pick_first_unused(idx_by_deal[ar["deal_id"]], ev, audit_sym)
            match_key = "deal_id"
        if matched_si is None and ar["ticket"] and ar["ticket"] in idx_by_ticket:
            matched_si = _pick_first_unused(idx_by_ticket[ar["ticket"]], ev, audit_sym)
            match_key = "ticket"
        if matched_si is None and ar["order_id"] and ar["order_id"] in idx_by_order:
            matched_si = _pick_first_unused(idx_by_order[ar["order_id"]], ev, audit_sym)
            match_key = "order_id"
        if matched_si is None and ar["position_id"] and ar["position_id"] in idx_by_pos:
            matched_si = _pick_first_unused(idx_by_pos[ar["position_id"]], ev, audit_sym)
            match_key = "position_id"
        if matched_si is None and ar["magic"] > 0:
            # Fallback composite match on magic + canonical symbol + side + timestamp proximity (<= 60s)
            for si, sr in enumerate(stmt_rows):
                if si in used_stmt_idx:
                    continue
                if sr["magic"] != ar["magic"]:
                    continue
                if sr["canonical_symbol"] != audit_sym or sr["side"] != ar["side"]:
                    continue
                if sr["utc_ts"] is not None and abs(sr["utc_ts"] - int(ar["utc_ts"])) > 60:
                    continue
                if not _direction_matches(ev, sr["direction"]):
                    continue
                matched_si = si
                match_key = "magic_symbol_side_ts"
                break

        row_enriched = dict(ar)
        if matched_si is None:
            orphan_audit_rows.append({
                "audit_index": ai,
                "utc_ts": ar["utc_ts"],
                "magic": ar["magic"],
                "symbol": ar["symbol"],
                "event_type": ev,
                "deal_id": ar["deal_id"],
                "order_id": ar["order_id"],
                "position_id": ar["position_id"],
                "ticket": ar["ticket"],
            })
            enriched_fills.append(row_enriched)
            continue

        used_stmt_idx.add(matched_si)
        sr = stmt_rows[matched_si]

        # Check magic agreement when both sides supply non-zero magic
        if ar["magic"] > 0 and sr["magic"] > 0 and ar["magic"] != sr["magic"]:
            magic_mismatches.append({
                "audit_index": ai,
                "statement_index": matched_si,
                "match_key": match_key,
                "audit_magic": ar["magic"],
                "statement_magic": sr["magic"],
            })

        # Check canonical symbol agreement
        if audit_sym and sr["canonical_symbol"] and audit_sym != sr["canonical_symbol"]:
            symbol_mismatches.append({
                "audit_index": ai,
                "statement_index": matched_si,
                "match_key": match_key,
                "audit_symbol": ar["symbol"],
                "statement_symbol": sr["symbol"],
            })

        # Enrich blank swap_usd / pnl_usd / commission_usd from matched broker statement row
        if row_enriched["swap_usd"] is None and sr["swap_usd"] is not None:
            row_enriched["swap_usd"] = sr["swap_usd"]
            swap_enriched_count += 1
        elif (
            row_enriched["swap_usd"] is not None
            and sr["swap_usd"] is not None
            and abs(float(row_enriched["swap_usd"]) - float(sr["swap_usd"])) > swap_tolerance_usd
        ):
            swap_discrepancies.append({
                "audit_index": ai,
                "statement_index": matched_si,
                "match_key": match_key,
                "audit_swap_usd": row_enriched["swap_usd"],
                "statement_swap_usd": sr["swap_usd"],
            })
            # Adopt authoritative broker swap so nonzero_swap_count, total_swap_usd,
            # and post_reconcile_gate fail closed consistently.
            row_enriched["swap_usd"] = sr["swap_usd"]

        if row_enriched["pnl_usd"] is None and sr["pnl_usd"] is not None:
            row_enriched["pnl_usd"] = sr["pnl_usd"]
            pnl_enriched_count += 1
        elif (
            row_enriched["pnl_usd"] is not None
            and sr["pnl_usd"] is not None
            and abs(float(row_enriched["pnl_usd"]) - float(sr["pnl_usd"])) > pnl_tolerance_usd
        ):
            pnl_discrepancies.append({
                "audit_index": ai,
                "statement_index": matched_si,
                "match_key": match_key,
                "audit_pnl_usd": row_enriched["pnl_usd"],
                "statement_pnl_usd": sr["pnl_usd"],
            })

        if row_enriched["commission_usd"] is None and sr["commission_usd"] is not None:
            row_enriched["commission_usd"] = sr["commission_usd"]

        enriched_fills.append(row_enriched)
        matched_pairs.append({
            "audit_index": ai,
            "statement_index": matched_si,
            "match_key": match_key,
            "deal_id": sr["deal_id"] or ar["deal_id"],
            "ticket": sr["ticket"] or ar["ticket"],
            "order_id": sr["order_id"] or ar["order_id"],
            "position_id": sr["position_id"] or ar["position_id"],
            "magic": ar["magic"] or sr["magic"],
            "symbol": ar["symbol"] or sr["symbol"],
            "event_type": ev,
            "swap_usd": row_enriched["swap_usd"],
            "pnl_usd": row_enriched["pnl_usd"],
        })

    # Identify orphan broker statement rows (not matched to any audit row)
    orphan_statement_rows: list[dict[str, Any]] = []
    out_of_scope_statement_rows = 0
    for si, sr in enumerate(stmt_rows):
        if si in used_stmt_idx:
            continue
        if allowed_magic_set is not None and sr["magic"] > 0 and sr["magic"] not in allowed_magic_set:
            out_of_scope_statement_rows += 1
            continue
        orphan_statement_rows.append({
            "statement_index": si,
            "deal_id": sr["deal_id"],
            "ticket": sr["ticket"],
            "order_id": sr["order_id"],
            "position_id": sr["position_id"],
            "magic": sr["magic"],
            "symbol": sr["symbol"],
            "side": sr["side"],
            "direction": sr["direction"],
            "swap_usd": sr["swap_usd"],
            "pnl_usd": sr["pnl_usd"],
        })

    # Post-reconciliation fail-closed gate via canonical `quant_core.tca.validate_tca_post_reconcile`
    post_gate_records = [*enriched_fills, *unresolved_rows]
    try:
        gate_res = validate_tca_post_reconcile(
            post_gate_records,
            require_zero_swap=require_zero_swap,
            swap_tolerance_usd=swap_tolerance_usd,
        )
        post_reconcile_gate: dict[str, Any] = {**gate_res, "error": None}
    except ValueError as exc:
        post_reconcile_gate = {
            "passed": False,
            "records_checked": len(post_gate_records),
            "error": str(exc),
        }

    # Explicit swap counts across ALL enriched fills (entries & exits) + statement orphans
    missing_swap_count = sum(1 for r in enriched_fills if r["swap_usd"] is None)
    nonzero_swap_count = sum(
        1
        for r in enriched_fills
        if r["swap_usd"] is not None and abs(float(r["swap_usd"])) > swap_tolerance_usd
    )
    # Also detect non-zero or missing swap on orphan statement rows
    orphan_nonzero_swap = sum(
        1
        for r in orphan_statement_rows
        if r["swap_usd"] is not None and abs(float(r["swap_usd"])) > swap_tolerance_usd
    )

    # Optional strictly causal Markout Curve (+1s/+10s/+60s/+5m)
    effective_quotes: Any = quote_series
    quote_tape_sha256: str | None = None
    if effective_quotes is None and quote_p is not None:
        quote_tape_sha256 = _file_sha256(quote_p)
        effective_quotes = load_quote_tape(quote_p)

    markout_curve: dict[str, Any] | None = None
    if effective_quotes is not None and enriched_fills:
        markout_curve = compute_markout_curve(
            enriched_fills,
            effective_quotes,
            horizons_sec=horizons_sec,
        )

    # Synthesize fail-closed verdict
    fail_reasons: list[str] = []
    if unresolved_rows:
        fail_reasons.append(f"FILL_UNRESOLVED: {len(unresolved_rows)} unresolved execution row(s)")
    if login_mismatch and login_mismatch_detail:
        fail_reasons.append(f"LOGIN_MISMATCH: {login_mismatch_detail}")
    if orphan_audit_rows:
        fail_reasons.append(f"ORPHAN_AUDIT_ROWS: {len(orphan_audit_rows)} audit fill(s) missing from broker statement")
    if orphan_statement_rows:
        fail_reasons.append(
            f"ORPHAN_STATEMENT_ROWS: {len(orphan_statement_rows)} broker statement row(s) missing from exec audit"
        )
    if magic_mismatches:
        fail_reasons.append(f"MAGIC_MISMATCH: {len(magic_mismatches)} matched row(s) disagreed on magic number")
    if symbol_mismatches:
        fail_reasons.append(f"SYMBOL_MISMATCH: {len(symbol_mismatches)} matched row(s) disagreed on symbol")
    if missing_swap_count > 0:
        fail_reasons.append(f"MISSING_SWAP_USD: {missing_swap_count} closed/fill row(s) still have swap_usd=None")
    if require_zero_swap and (nonzero_swap_count > 0 or orphan_nonzero_swap > 0):
        fail_reasons.append(
            f"NONZERO_SWAP_USD: {nonzero_swap_count} enriched + {orphan_nonzero_swap} orphan row(s) have swap != 0.00"
        )
    if swap_discrepancies:
        fail_reasons.append(f"SWAP_DISCREPANCY: {len(swap_discrepancies)} audit-vs-statement swap mismatch(es)")
    if pnl_discrepancies:
        fail_reasons.append(f"PNL_DISCREPANCY: {len(pnl_discrepancies)} audit-vs-statement PnL mismatch(es)")
    if not post_reconcile_gate["passed"]:
        gate_err = str(post_reconcile_gate.get("error") or "post_reconcile_failed")
        if not any(gate_err in r for r in fail_reasons):
            fail_reasons.append(gate_err)

    if fail_reasons:
        status = "FAIL_CLOSED"
        passed = False
    elif not audit_fills and not stmt_rows:
        status = "NO_TRADES"
        passed = True
    else:
        status = "PASS"
        passed = True

    net_pnl_usd = round(
        sum(float(r["pnl_usd"]) for r in enriched_fills if r["pnl_usd"] is not None),
        2,
    )
    total_swap_usd = round(
        sum(float(r["swap_usd"]) for r in enriched_fills if r["swap_usd"] is not None),
        6,
    )

    report: dict[str, Any] = {
        "schema": SCHEMA_VERSION,
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat(),
        "readonly": True,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "status": status,
        "passed": passed,
        "fail_reasons": fail_reasons,
        "adverse_selection_warning": bool(
            markout_curve is not None and markout_curve["adverse_selection_flagged"]
        ),
        "inputs": {
            "audit_csv": audit_p.name,
            "audit_csv_sha256": _file_sha256(audit_p),
            "statement_file": stmt_bundle["file_name"],
            "statement_format": stmt_bundle["format"],
            "statement_sha256": stmt_bundle["sha256"],
            "quote_tape_file": quote_p.name if quote_p is not None else None,
            "quote_tape_sha256": quote_tape_sha256,
            "expected_login": expected_login,
            "statement_logins": stmt_logins,
            "audit_logins": audit_logins,
        },
        "summary": {
            "audit_total_rows": len(audit_all),
            "audit_fill_rows": len(audit_fills),
            "audit_non_fill_rows": len(non_fill_rows),
            "unresolved_fill_rows": len(unresolved_rows),
            "statement_trade_rows": len(stmt_rows),
            "statement_ignored_non_trade_rows": stmt_bundle["ignored_non_trade_rows"],
            "statement_out_of_scope_rows": out_of_scope_statement_rows,
            "matched_pairs": len(matched_pairs),
            "orphan_audit_count": len(orphan_audit_rows),
            "orphan_statement_count": len(orphan_statement_rows),
            "swap_enriched_count": swap_enriched_count,
            "pnl_enriched_count": pnl_enriched_count,
            "missing_swap_count": missing_swap_count,
            "nonzero_swap_count": nonzero_swap_count,
            "total_swap_usd": total_swap_usd,
            "net_pnl_usd": net_pnl_usd,
            "magic_mismatch_count": len(magic_mismatches),
            "symbol_mismatch_count": len(symbol_mismatches),
            "swap_discrepancy_count": len(swap_discrepancies),
            "pnl_discrepancy_count": len(pnl_discrepancies),
        },
        "post_reconcile_gate": post_reconcile_gate,
        "orphans": {
            "audit_only": orphan_audit_rows,
            "statement_only": orphan_statement_rows,
        },
        "discrepancies": {
            "magic_mismatches": magic_mismatches,
            "symbol_mismatches": symbol_mismatches,
            "swap_discrepancies": swap_discrepancies,
            "pnl_discrepancies": pnl_discrepancies,
            "unresolved_rows": [
                {
                    "utc_ts": r["utc_ts"],
                    "symbol": r["symbol"],
                    "event_type": r["event_type"],
                    "order_id": r["order_id"],
                    "comment": r["comment"],
                }
                for r in unresolved_rows
            ],
        },
        "matched_pairs": matched_pairs,
        "markout_curve": markout_curve,
    }

    if out_json is not None:
        receipt = write_atomic_sha256_json(out_json, report)
        report["report_sha256"] = receipt["report_sha256"]
        report["output_receipt"] = receipt

    return report


def _parse_horizons_arg(raw: str) -> tuple[int, ...]:
    parts = [p.strip() for p in raw.split(",") if p.strip()]
    if not parts:
        raise argparse.ArgumentTypeError("horizons must be a comma-separated list of positive integers")
    vals: list[int] = []
    for p in parts:
        try:
            v = int(p)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(f"invalid horizon integer: {p!r}") from exc
        if v <= 0:
            raise argparse.ArgumentTypeError(f"horizon must be > 0, got {v}")
        vals.append(v)
    return tuple(vals)


def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Read-only Automated Daily MT5 Statement (CSV/HTML) vs naqex_exec_audit.csv "
            "Reconciler & +1s/+10s/+60s/+5m Markout Curve Engine (OrderSend=0)."
        )
    )
    ap.add_argument("--audit-csv", type=Path, required=True, help="Path to naqex_exec_audit.csv")
    ap.add_argument("--statement", type=Path, required=True, help="Path to MT5/FTMO broker statement (CSV or HTML)")
    ap.add_argument("--quote-tape", type=Path, default=None, help="Optional quote tape (JSONL or CSV) for markout")
    ap.add_argument("--expected-login", type=int, default=None, help="Expected broker account login ID")
    ap.add_argument("--allowed-magics", type=str, default=None, help="Optional comma-separated in-scope magic numbers")
    ap.add_argument(
        "--horizons",
        type=_parse_horizons_arg,
        default=DEFAULT_MARKOUT_HORIZONS_SEC,
        help="Comma-separated markout horizons in seconds (default: 1,10,60,300)",
    )
    ap.add_argument(
        "--allow-nonzero-swap",
        action="store_true",
        help="Advisory mode: do not fail closed on non-zero finite swap (still fails on missing/NaN swap).",
    )
    ap.add_argument("--out-json", type=Path, default=None, help="Atomic SHA-256 JSON output report path")
    return ap


def main(argv: list[str] | None = None) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    allowed_magics: list[int] | None = None
    if args.allowed_magics:
        allowed_magics = [int(x.strip()) for x in args.allowed_magics.split(",") if x.strip()]

    report = reconcile_daily_statement(
        audit_csv=args.audit_csv,
        statement_path=args.statement,
        quote_tape_path=args.quote_tape,
        expected_login=args.expected_login,
        allowed_magics=allowed_magics,
        horizons_sec=args.horizons,
        require_zero_swap=not bool(args.allow_nonzero_swap),
        out_json=args.out_json,
    )

    summary_out = {
        "schema": report["schema"],
        "status": report["status"],
        "passed": report["passed"],
        "order_send_count": report["order_send_count"],
        "matched_pairs": report["summary"]["matched_pairs"],
        "orphan_audit_count": report["summary"]["orphan_audit_count"],
        "orphan_statement_count": report["summary"]["orphan_statement_count"],
        "unresolved_fill_rows": report["summary"]["unresolved_fill_rows"],
        "missing_swap_count": report["summary"]["missing_swap_count"],
        "nonzero_swap_count": report["summary"]["nonzero_swap_count"],
        "adverse_selection_warning": report["adverse_selection_warning"],
        "report_sha256": report.get("report_sha256"),
        "fail_reasons": report["fail_reasons"],
    }
    print(json.dumps(summary_out, indent=2, ensure_ascii=False))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
