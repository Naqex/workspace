"""Live Broker M1 Bid/Ask Tape Ingestor & Isolated Live-Vault Manager (OPS-6).

Reuses and adapts patterns from `ops_cloud/nfp_cpi_quote_collector.py` and `quant_core/tca.py`
to ingest live/demo broker quote tapes (JSONL or CSV) and broker symbol specifications JSON
into `.runtime/live-vault/<account_alias>/` with deterministic SHA-256 manifests.

HARD SAFETY & IMMUTABILITY INVARIANTS (`B5`, `H1`, `[ARCH-02]`, `G02`, `G11`, `G16`):
  - Pure offline read-only ingestor: `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - NEVER imports `MetaTrader5`, NEVER touches `quant_core/`, `Naqex_PropGuard.mqh`, `v1.01`, or `v1.03`.
  - ZERO bare `assert` statements (`[ARCH-02]`).
  - Strict Live-Vault isolation: rejects any target overlapping `.runtime/hot-m1-cache/`,
    Dev caches (`dev_cache`, `new-assets-10-cache`, `offensive3-d1-cache`), sealed Holdout `2025+`,
    `private_vault/`, `exports/`, `MQL5/`, or drive `E:`.
  - Provides `build_broker_m1_bars_from_quotes(...)` and `extract_executable_price_path(...)` so
    `live_parity_forensics.py` replays signals on TRUE BROKER M1 BID/ASK and feeds executable
    Bid/Ask paths into `quant_core.trade_forensics_classifier.excursions(...)`.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import shutil
import sys
import tempfile
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

AI_ENGINES_DIR: Final[Path] = Path(__file__).resolve().parents[2]
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.tca import (  # noqa: E402
    BENCHMARK_SPREAD_PTS,
    POINT_SIZES,
    canonical_payload_sha256,
    load_quote_tape,
    normalize_symbol_alias,
    parse_optional_finite_float,
    parse_required_finite_float,
    point_size_for_symbol,
    write_atomic_sha256_json,
)

ORDER_SEND_CAPABLE: Final[bool] = False
ORDER_SEND_COUNT: Final[int] = 0

LIVE_VAULT_MANIFEST_SCHEMA: Final[str] = "naqex-live-vault-tape-manifest-v1"
BROKER_SPECS_SCHEMA: Final[str] = "naqex-broker-symbol-specs-v1"
DEFAULT_LIVE_VAULT_ROOT: Final[Path] = WORKSPACE_ROOT / ".runtime" / "live-vault"
DEFAULT_HOT_M1_CACHE_DIR: Final[Path] = WORKSPACE_ROOT / ".runtime" / "hot-m1-cache"

_SAFE_ALIAS_RE: Final[re.Pattern[str]] = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")
_FORBIDDEN_VAULT_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?i)(?:^|[\\/])("
    r"hot-m1-cache|mt5-m1-cache|new-assets-10-cache|offensive3-d1-cache|"
    r"dev_cache|dev-cache|holdout|native_ftmo_holdout|holdout_2025|"
    r"private_vault|exports|mql5|quant_core|mt5-compiled-ex5"
    r")(?:$|[\\/])"
)
_LIVE_VAULT_SEGMENT_RE: Final[re.Pattern[str]] = re.compile(r"(?i)(?:^|[\\/])live[-_]vault(?:$|[\\/])")
_DOT_DATE_RE: Final[re.Pattern[str]] = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})(.*)$")


class LiveVaultIsolationError(ValueError):
    """Fail-closed error raised whenever a target path risks contaminating Dev/Holdout caches."""


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _is_relative_to(child: Path, parent: Path) -> bool:
    try:
        child.relative_to(parent)
        return True
    except ValueError:
        return False


def _paths_overlap(a: Path, b: Path) -> bool:
    ra = a.resolve(strict=False)
    rb = b.resolve(strict=False)
    return ra == rb or _is_relative_to(ra, rb) or _is_relative_to(rb, ra)


def validate_account_alias(account_alias: str) -> str:
    """Validate and normalize a safe `account_alias` directory name (fail-closed)."""
    if not isinstance(account_alias, str):
        raise LiveVaultIsolationError(f"account_alias must be a string, got {type(account_alias).__name__}")
    alias = account_alias.strip()
    if not alias or not _SAFE_ALIAS_RE.fullmatch(alias) or ".." in alias:
        raise LiveVaultIsolationError(
            f"INVALID_ACCOUNT_ALIAS: {account_alias!r} must match {_SAFE_ALIAS_RE.pattern} without traversal"
        )
    if _FORBIDDEN_VAULT_SEGMENT_RE.search(f"/{alias}/"):
        raise LiveVaultIsolationError(f"FORBIDDEN_ACCOUNT_ALIAS: {alias!r} collides with reserved cache name")
    return alias


def validate_live_vault_target(
    vault_root: Path | str,
    account_alias: str,
    *,
    hot_m1_cache_dir: Path | str | None = None,
    holdout_dir: Path | str | None = None,
) -> Path:
    """Validate isolated `<vault_root>/<account_alias>` target and fail closed on any overlap."""
    alias = validate_account_alias(account_alias)
    raw_root_str = str(vault_root).strip()
    if not raw_root_str:
        raise LiveVaultIsolationError("LIVE_VAULT_ROOT_EMPTY")

    # Reject raw traversal segments and forbidden drive E: before resolution
    norm_raw = raw_root_str.replace("/", "\\")
    if re.match(r"(?i)^E:(?:\\|$)", norm_raw):
        raise LiveVaultIsolationError(f"FORBIDDEN_DRIVE_E_TARGET: {raw_root_str!r}")
    if re.search(r"(^|\\)\.\.(\\|$)", norm_raw):
        raise LiveVaultIsolationError(f"PATH_TRAVERSAL_FORBIDDEN: {raw_root_str!r}")

    root_path = Path(raw_root_str)
    resolved_root = root_path.resolve(strict=False)
    resolved_root_str = str(resolved_root)

    if re.match(r"(?i)^E:(?:\\|$)", resolved_root_str):
        raise LiveVaultIsolationError(f"FORBIDDEN_DRIVE_E_RESOLVED: {resolved_root_str!r}")
    if _FORBIDDEN_VAULT_SEGMENT_RE.search(norm_raw) or _FORBIDDEN_VAULT_SEGMENT_RE.search(resolved_root_str):
        raise LiveVaultIsolationError(
            f"LIVE_VAULT_CONTAMINATION_BLOCKED: vault_root {resolved_root_str!r} overlaps Dev/Holdout/Vault boundary"
        )
    if not _LIVE_VAULT_SEGMENT_RE.search(resolved_root_str):
        raise LiveVaultIsolationError(
            f"LIVE_VAULT_SEGMENT_REQUIRED: vault_root {resolved_root_str!r} must reside under an isolated 'live-vault'"
        )

    target_dir = (resolved_root / alias).resolve(strict=False)
    if not _is_relative_to(target_dir, resolved_root):
        raise LiveVaultIsolationError(f"ACCOUNT_ALIAS_ESCAPE_BLOCKED: {target_dir} escapes {resolved_root}")

    resolved_hot = (
        Path(hot_m1_cache_dir).resolve(strict=False)
        if hot_m1_cache_dir is not None
        else DEFAULT_HOT_M1_CACHE_DIR.resolve(strict=False)
    )
    if _paths_overlap(target_dir, resolved_hot) or _paths_overlap(resolved_root, resolved_hot):
        raise LiveVaultIsolationError(
            f"HOT_M1_CACHE_CONTAMINATION_BLOCKED: {target_dir} overlaps hot-m1-cache {resolved_hot}"
        )

    if holdout_dir is not None:
        resolved_holdout = Path(holdout_dir).resolve(strict=False)
        if _paths_overlap(target_dir, resolved_holdout) or _paths_overlap(resolved_root, resolved_holdout):
            raise LiveVaultIsolationError(
                f"HOLDOUT_CONTAMINATION_BLOCKED: {target_dir} overlaps Holdout dir {resolved_holdout}"
            )

    return target_dir


def verify_zero_cache_contamination(
    account_vault_dir: Path | str,
    *,
    hot_m1_cache_dir: Path | str | None = None,
    holdout_dir: Path | str | None = None,
) -> dict[str, Any]:
    """Verify live-vault directory has zero path/symlink overlap with Dev caches or Holdout."""
    vault_path = Path(account_vault_dir).resolve(strict=False)
    hot_path = (
        Path(hot_m1_cache_dir).resolve(strict=False)
        if hot_m1_cache_dir is not None
        else DEFAULT_HOT_M1_CACHE_DIR.resolve(strict=False)
    )
    hot_overlap = _paths_overlap(vault_path, hot_path)
    holdout_overlap = False
    if holdout_dir is not None:
        holdout_overlap = _paths_overlap(vault_path, Path(holdout_dir).resolve(strict=False))
    forbidden_name = bool(_FORBIDDEN_VAULT_SEGMENT_RE.search(str(vault_path)))
    has_live_vault_seg = bool(_LIVE_VAULT_SEGMENT_RE.search(str(vault_path)))

    hot_manifest = hot_path / "manifest.json"
    hot_manifest_sha = _sha256_file(hot_manifest) if hot_manifest.is_file() else None

    clean = (not hot_overlap) and (not holdout_overlap) and (not forbidden_name) and has_live_vault_seg
    return {
        "clean": clean,
        "account_vault_dir": str(vault_path),
        "hot_m1_cache_dir": str(hot_path),
        "hot_m1_cache_overlap": hot_overlap,
        "holdout_overlap": holdout_overlap,
        "forbidden_path_segment": forbidden_name,
        "isolated_live_vault_segment": has_live_vault_seg,
        "hot_m1_cache_manifest_sha256": hot_manifest_sha,
    }


def _parse_quote_ts_ms(raw_row: Mapping[str, Any]) -> int:
    """Parse quote timestamp in UTC milliseconds from `utc_ts_ms`, `utc_ts`, `ts`, or ISO strings."""
    if "utc_ts_ms" in raw_row and raw_row.get("utc_ts_ms") not in (None, ""):
        val = parse_required_finite_float(raw_row.get("utc_ts_ms"), field_name="quote.utc_ts_ms")
        if val <= 0.0:
            raise ValueError(f"quote.utc_ts_ms must be > 0, got {val}")
        return int(round(val))

    for key in ("captured_utc_ts_ms", "ts_ms", "time_msc"):
        if key in raw_row and raw_row.get(key) not in (None, ""):
            val = parse_required_finite_float(raw_row.get(key), field_name=f"quote.{key}")
            if val <= 0.0:
                raise ValueError(f"quote.{key} must be > 0, got {val}")
            return int(round(val))

    for key in ("captured_utc_ts", "utc_ts", "ts", "timestamp", "utc_iso_ms", "utc_time"):
        raw = raw_row.get(key)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            continue
        if isinstance(raw, (int, float)) and not isinstance(raw, bool):
            fv = float(raw)
            if not math.isfinite(fv) or fv <= 0.0:
                raise ValueError(f"quote.{key} must be finite and > 0, got {raw!r}")
            return int(round(fv)) if fv >= 1.0e12 else int(round(fv * 1000.0))
        if isinstance(raw, str):
            s = raw.strip()
            try:
                fv = float(s)
                if not math.isfinite(fv) or fv <= 0.0:
                    raise ValueError(f"quote.{key} must be finite and > 0, got {raw!r}")
                return int(round(fv)) if fv >= 1.0e12 else int(round(fv * 1000.0))
            except ValueError:
                pass
            dot_m = _DOT_DATE_RE.fullmatch(s)
            if dot_m is not None:
                s = f"{dot_m.group(1)}-{dot_m.group(2)}-{dot_m.group(3)}{dot_m.group(4)}"
            if s.endswith(("Z", "z")):
                s = s[:-1] + "+00:00"
            try:
                dt = datetime.fromisoformat(s)
            except ValueError as exc:
                raise ValueError(f"quote.{key} invalid timestamp {raw!r}") from exc
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=UTC)
            ts_ms = int(round(dt.timestamp() * 1000.0))
            if ts_ms <= 0:
                raise ValueError(f"quote.{key} must resolve > 0 epoch ms, got {raw!r}")
            return ts_ms
    raise ValueError(f"Quote row missing valid timestamp field: {dict(raw_row)!r}")


def _resolve_point_from_specs(
    raw_symbol: str,
    canonical_symbol: str,
    symbol_specs: Mapping[str, Mapping[str, Any]] | None,
) -> float:
    if symbol_specs:
        for cand in (raw_symbol, canonical_symbol):
            entry = symbol_specs.get(cand)
            if isinstance(entry, Mapping):
                pt = parse_optional_finite_float(entry.get("point"), field_name="spec.point")
                if pt is not None and pt > 0.0:
                    return pt
                digits = entry.get("digits")
                if isinstance(digits, int) and not isinstance(digits, bool) and digits >= 0:
                    return 10.0 ** (-digits)
    return point_size_for_symbol(raw_symbol or canonical_symbol)


def _normalize_single_quote_tick(
    *,
    utc_ts_ms: int,
    raw_symbol: str,
    bid: float,
    ask: float,
    point: float,
    source_tier: str,
) -> dict[str, Any]:
    if not math.isfinite(bid) or not math.isfinite(ask) or bid <= 0.0 or ask < bid:
        raise ValueError(f"Invalid quote bid/ask for {raw_symbol!r}: bid={bid}, ask={ask}")
    if not math.isfinite(point) or point <= 0.0:
        raise ValueError(f"Invalid point size for {raw_symbol!r}: point={point}")
    canon = normalize_symbol_alias(raw_symbol)
    if not canon:
        raise ValueError(f"Unable to canonicalize symbol {raw_symbol!r}")
    mid = 0.5 * (bid + ask)
    spread_pts = (ask - bid) / point
    spread_bps = ((ask - bid) / mid) * 10_000.0 if mid > 0.0 else 0.0
    return {
        "utc_ts_ms": int(utc_ts_ms),
        "utc_ts": round(utc_ts_ms / 1000.0, 6),
        "symbol": raw_symbol,
        "canonical_symbol": canon,
        "bid": float(bid),
        "ask": float(ask),
        "mid": float(mid),
        "point": float(point),
        "spread_pts": round(float(spread_pts), 4),
        "spread_bps": round(float(spread_bps), 6),
        "record_tier": source_tier,
    }


def _check_quote_order_send_zero(row: Mapping[str, Any]) -> None:
    if "order_send_count" in row and row["order_send_count"] not in (None, ""):
        raw = row["order_send_count"]
        if isinstance(raw, bool):
            raise ValueError(f"NONZERO_ORDER_SEND_COUNT: invalid bool {raw!r}")
        val = int(float(str(raw).strip()))
        if val != 0:
            raise ValueError(f"NONZERO_ORDER_SEND_COUNT: quote tape row has order_send_count={val} != 0")


def parse_broker_quote_records(
    raw_records: Iterable[Mapping[str, Any]],
    *,
    symbol_specs: Mapping[str, Mapping[str, Any]] | None = None,
    deduplicate: bool = True,
) -> list[dict[str, Any]]:
    """Normalize flat, `nfp_cpi_quote_collector`, or nested `mt5_live_spread_log` quote records."""
    normalized: list[dict[str, Any]] = []
    for idx, row in enumerate(raw_records):
        if not isinstance(row, Mapping):
            raise ValueError(f"Quote record[{idx}] must be a mapping, got {type(row).__name__}")
        _check_quote_order_send_zero(row)

        nested_quotes = row.get("quotes")
        if isinstance(nested_quotes, Mapping):
            ts_ms = _parse_quote_ts_ms(row)
            tier = str(row.get("record_tier") or "LIVE_SPREAD_SNAPSHOT").strip()
            for sym_key, q in nested_quotes.items():
                if not isinstance(q, Mapping):
                    continue
                if "available" in q and not q.get("available"):
                    continue
                raw_sym = str(sym_key).strip()
                if not raw_sym:
                    continue
                bid = parse_required_finite_float(q.get("bid"), field_name=f"quotes[{raw_sym}].bid")
                ask = parse_required_finite_float(q.get("ask"), field_name=f"quotes[{raw_sym}].ask")
                pt_raw = parse_optional_finite_float(q.get("point"), field_name=f"quotes[{raw_sym}].point")
                pt = (
                    pt_raw
                    if (pt_raw is not None and pt_raw > 0.0)
                    else _resolve_point_from_specs(raw_sym, normalize_symbol_alias(raw_sym), symbol_specs)
                )
                normalized.append(
                    _normalize_single_quote_tick(
                        utc_ts_ms=ts_ms,
                        raw_symbol=raw_sym,
                        bid=bid,
                        ask=ask,
                        point=pt,
                        source_tier=tier,
                    )
                )
            continue

        raw_sym = str(row.get("symbol") or "").strip()
        if not raw_sym:
            raise ValueError(f"Quote record[{idx}] missing symbol")
        ts_ms = _parse_quote_ts_ms(row)
        bid = parse_optional_finite_float(row.get("bid"), field_name=f"quote[{idx}].bid")
        ask = parse_optional_finite_float(row.get("ask"), field_name=f"quote[{idx}].ask")
        if bid is None or ask is None:
            raise ValueError(
                f"Quote record[{idx}] for {raw_sym!r} MUST include both finite bid and ask (got bid={bid}, ask={ask})"
            )
        pt_raw = parse_optional_finite_float(row.get("point"), field_name=f"quote[{idx}].point")
        pt = (
            pt_raw
            if (pt_raw is not None and pt_raw > 0.0)
            else _resolve_point_from_specs(raw_sym, normalize_symbol_alias(raw_sym), symbol_specs)
        )
        tier = str(row.get("record_tier") or "QUOTE_ONLY").strip()
        normalized.append(
            _normalize_single_quote_tick(
                utc_ts_ms=ts_ms,
                raw_symbol=raw_sym,
                bid=bid,
                ask=ask,
                point=pt,
                source_tier=tier,
            )
        )

    normalized.sort(key=lambda r: (r["canonical_symbol"], r["utc_ts_ms"], r["bid"], r["ask"]))
    if not deduplicate:
        return normalized

    # Preserve distinct same-millisecond ticks while removing exact duplicates (SameMsTickCursor style)
    deduped: list[dict[str, Any]] = []
    seen_last_key: dict[str, tuple[int, list[tuple[int, float, float]]]] = {}
    for tick in normalized:
        sym = tick["canonical_symbol"]
        t_ms = tick["utc_ts_ms"]
        dkey = (t_ms, round(tick["bid"], 8), round(tick["ask"], 8))
        prev = seen_last_key.get(sym)
        if prev is not None and prev[0] == t_ms:
            if dkey in prev[1]:
                continue
            prev[1].append(dkey)
        else:
            seen_last_key[sym] = (t_ms, [dkey])
        deduped.append(tick)
    return deduped


def load_broker_quote_tape(
    quote_path: Path | str,
    *,
    symbol_specs: Mapping[str, Mapping[str, Any]] | None = None,
    deduplicate: bool = True,
) -> list[dict[str, Any]]:
    """Load and validate a broker quote tape CSV (`nfp_cpi`/flat) or JSONL (flat/nested)."""
    path = Path(quote_path)
    if not path.is_file():
        raise FileNotFoundError(f"Broker quote tape not found: {path}")

    suffix = path.suffix.lower()
    raw_rows: list[dict[str, Any]] = []
    if suffix == ".csv":
        with path.open("r", encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f)
            if not reader.fieldnames:
                raise ValueError(f"Empty CSV header in broker quote tape: {path}")
            for line_no, raw in enumerate(reader, start=2):
                if not raw or all(str(v or "").strip() == "" for v in raw.values()):
                    continue
                try:
                    raw_rows.append(dict(raw))
                except ValueError as exc:
                    raise ValueError(f"{path.name}:{line_no}: {exc}") from exc
        return parse_broker_quote_records(raw_rows, symbol_specs=symbol_specs, deduplicate=deduplicate)

    if suffix in (".jsonl", ".ndjson", ".json"):
        if suffix == ".json":
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
            if isinstance(doc, list):
                raw_rows = [r for r in doc if isinstance(r, Mapping)]
            elif isinstance(doc, Mapping) and isinstance(doc.get("quotes"), list):
                raw_rows = [r for r in doc["quotes"] if isinstance(r, Mapping)]
            elif isinstance(doc, Mapping):
                raw_rows = [dict(doc)]
            else:
                raise ValueError(f"Unsupported JSON quote tape structure in {path}")
        else:
            # Reuse canonical quant_core.tca.load_quote_tape for resilient JSONL loading
            raw_rows = load_quote_tape(path)
        return parse_broker_quote_records(raw_rows, symbol_specs=symbol_specs, deduplicate=deduplicate)

    raise ValueError(f"Unsupported broker quote tape extension {suffix!r} for {path}; expected .csv or .jsonl")


def load_broker_symbol_specs(specs_path: Path | str) -> dict[str, dict[str, Any]]:
    """Load broker symbol specifications JSON into canonical symbol-keyed dictionary."""
    path = Path(specs_path)
    if not path.is_file():
        raise FileNotFoundError(f"Broker symbol specs JSON not found: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, Mapping):
        raise ValueError(f"Malformed broker symbol specs JSON (expected object): {path}")

    entries: list[tuple[str, Mapping[str, Any]]] = []
    if "fx_metals_indices_specs" in doc or "core_live" in doc:
        for section in ("fx_metals_indices_specs", "core_live"):
            sec = doc.get(section)
            if isinstance(sec, Mapping):
                for sym, val in sec.items():
                    if isinstance(val, Mapping):
                        entries.append((str(sym), val))
    elif isinstance(doc.get("symbols"), Mapping):
        for sym, val in doc["symbols"].items():
            if isinstance(val, Mapping):
                entries.append((str(sym), val))
    else:
        for sym, val in doc.items():
            if isinstance(val, Mapping):
                entries.append((str(sym), val))

    normalized: dict[str, dict[str, Any]] = {}
    for raw_sym, spec in entries:
        broker_sym = str(spec.get("broker_symbol") or spec.get("symbol") or raw_sym).strip()
        if not broker_sym:
            continue
        canon = normalize_symbol_alias(broker_sym)
        digits_raw = spec.get("digits")
        digits = int(digits_raw) if isinstance(digits_raw, int) and not isinstance(digits_raw, bool) else None
        point = parse_optional_finite_float(spec.get("point"), field_name=f"{broker_sym}.point")
        if point is None:
            point = (10.0 ** (-digits)) if (digits is not None and digits >= 0) else point_size_for_symbol(broker_sym)
        cs = parse_optional_finite_float(
            spec.get("contract_size") if "contract_size" in spec else spec.get("trade_contract_size"),
            field_name=f"{broker_sym}.contract_size",
        )
        tick_size = parse_optional_finite_float(
            spec.get("tick_size") if "tick_size" in spec else spec.get("trade_tick_size"),
            field_name=f"{broker_sym}.tick_size",
        )
        tick_val = parse_optional_finite_float(
            spec.get("tick_value") if "tick_value" in spec else spec.get("trade_tick_value"),
            field_name=f"{broker_sym}.tick_value",
        )
        tick_val_loss = parse_optional_finite_float(
            spec.get("tick_value_loss") if "tick_value_loss" in spec else spec.get("trade_tick_value_loss"),
            field_name=f"{broker_sym}.tick_value_loss",
        )
        stops_raw = spec.get("stops_level") if "stops_level" in spec else spec.get("trade_stops_level")
        stops_level = int(stops_raw) if isinstance(stops_raw, int) and not isinstance(stops_raw, bool) else 0

        rec = {
            "broker_symbol": broker_sym,
            "canonical_symbol": canon,
            "digits": digits,
            "point": float(point),
            "contract_size": cs,
            "tick_size": tick_size,
            "tick_value": tick_val,
            "tick_value_loss": tick_val_loss,
            "stops_level": stops_level,
            "min_lot": parse_optional_finite_float(
                spec.get("min_lot") if "min_lot" in spec else spec.get("volume_min"),
                field_name=f"{broker_sym}.min_lot",
            ),
            "lot_step": parse_optional_finite_float(
                spec.get("lot_step") if "lot_step" in spec else spec.get("volume_step"),
                field_name=f"{broker_sym}.lot_step",
            ),
            "max_lot": parse_optional_finite_float(
                spec.get("max_lot") if "max_lot" in spec else spec.get("volume_max"),
                field_name=f"{broker_sym}.max_lot",
            ),
            "benchmark_spread_pts": BENCHMARK_SPREAD_PTS.get(broker_sym, BENCHMARK_SPREAD_PTS.get(canon)),
        }
        normalized[broker_sym] = rec
        if canon and canon not in normalized:
            normalized[canon] = rec
    return normalized


def build_broker_m1_bars_from_quotes(
    quotes: Iterable[Mapping[str, Any]],
    *,
    symbol_specs: Mapping[str, Mapping[str, Any]] | None = None,
    bar_seconds: int = 60,
) -> dict[str, list[dict[str, Any]]]:
    """Aggregate live/demo broker quotes into true Bid/Ask M1 OHLC bars per canonical symbol.

    Guarantees:
      - Strictly causal UTC minute bucketing: `bar_open_ts = (utc_ts_ms // (bar_seconds * 1000)) * bar_seconds`.
      - Preserves separate `bid_*` and `ask_*` OHLC plus spread distribution (`min/median/max/close`)
        so Python replay uses TRUE BROKER BID/ASK instead of Dukascopy proxies.
    """
    if isinstance(bar_seconds, bool) or not isinstance(bar_seconds, int) or bar_seconds <= 0:
        raise ValueError(f"bar_seconds must be a positive int, got {bar_seconds!r}")

    normalized_ticks = parse_broker_quote_records(quotes, symbol_specs=symbol_specs, deduplicate=True)
    bucket_ms = bar_seconds * 1000
    grouped: dict[str, dict[int, list[dict[str, Any]]]] = {}

    for tick in normalized_ticks:
        canon = tick["canonical_symbol"]
        bar_open_ms = (tick["utc_ts_ms"] // bucket_ms) * bucket_ms
        grouped.setdefault(canon, {}).setdefault(bar_open_ms, []).append(tick)

    result: dict[str, list[dict[str, Any]]] = {}
    for canon in sorted(grouped.keys()):
        bars: list[dict[str, Any]] = []
        buckets = grouped[canon]
        for bar_open_ms in sorted(buckets.keys()):
            ticks = buckets[bar_open_ms]
            bids = [t["bid"] for t in ticks]
            asks = [t["ask"] for t in ticks]
            mids = [t["mid"] for t in ticks]
            spreads = sorted(t["spread_pts"] for t in ticks)
            n = len(spreads)
            med_spread = spreads[n // 2] if (n % 2 == 1) else 0.5 * (spreads[n // 2 - 1] + spreads[n // 2])
            bar_open_ts = bar_open_ms // 1000
            bars.append(
                {
                    "symbol": ticks[0]["symbol"],
                    "canonical_symbol": canon,
                    "bar_open_ts": int(bar_open_ts),
                    "bar_open_ts_ms": int(bar_open_ms),
                    "bar_open_utc": datetime.fromtimestamp(bar_open_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "point": ticks[0]["point"],
                    "bid_open": float(bids[0]),
                    "bid_high": float(max(bids)),
                    "bid_low": float(min(bids)),
                    "bid_close": float(bids[-1]),
                    "ask_open": float(asks[0]),
                    "ask_high": float(max(asks)),
                    "ask_low": float(min(asks)),
                    "ask_close": float(asks[-1]),
                    "mid_open": float(mids[0]),
                    "mid_high": float(max(mids)),
                    "mid_low": float(min(mids)),
                    "mid_close": float(mids[-1]),
                    "spread_pts_min": round(float(spreads[0]), 4),
                    "spread_pts_median": round(float(med_spread), 4),
                    "spread_pts_max": round(float(spreads[-1]), 4),
                    "spread_pts_close": round(float(ticks[-1]["spread_pts"]), 4),
                    "tick_count": n,
                }
            )
        result[canon] = bars
    return result


def extract_executable_price_path(
    bars_or_quotes: Sequence[Mapping[str, Any]],
    *,
    side: int,
    start_ts_ms: int | None = None,
    end_ts_ms: int | None = None,
) -> tuple[np.ndarray, np.ndarray]:
    """Build monotonic `(times_ms, executable_prices)` path for `trade_forensics_classifier.excursions`.

    Executable liquidation convention:
      - LONG (`side == +1` / BUY): closes by selling at **Bid** (`bid` ticks or `bid_open/low/high/close`).
      - SHORT (`side == -1` / SELL): closes by buying at **Ask** (`ask` ticks or `ask_open/high/low/close`).
    """
    if side not in (-1, 1):
        raise ValueError(f"side must be +1 (BUY) or -1 (SELL), got {side!r}")

    times: list[int] = []
    prices: list[float] = []
    for row in bars_or_quotes:
        if "bar_open_ts_ms" in row or "bid_open" in row:
            t0 = int(row.get("bar_open_ts_ms") or (int(row["bar_open_ts"]) * 1000))
            if side == 1:
                pts = (
                    (t0, float(row["bid_open"])),
                    (t0 + 15_000, float(row["bid_low"])),
                    (t0 + 30_000, float(row["bid_high"])),
                    (t0 + 45_000, float(row["bid_close"])),
                )
            else:
                pts = (
                    (t0, float(row["ask_open"])),
                    (t0 + 15_000, float(row["ask_high"])),
                    (t0 + 30_000, float(row["ask_low"])),
                    (t0 + 45_000, float(row["ask_close"])),
                )
            for ts_ms, px in pts:
                if start_ts_ms is not None and ts_ms < start_ts_ms:
                    continue
                if end_ts_ms is not None and ts_ms > end_ts_ms:
                    continue
                times.append(ts_ms)
                prices.append(px)
        else:
            ts_ms = _parse_quote_ts_ms(row)
            if start_ts_ms is not None and ts_ms < start_ts_ms:
                continue
            if end_ts_ms is not None and ts_ms > end_ts_ms:
                continue
            px_val = row.get("bid") if side == 1 else row.get("ask")
            px = parse_required_finite_float(px_val, field_name="quote.executable_price")
            times.append(ts_ms)
            prices.append(px)

    if not times:
        return np.asarray([], dtype=np.int64), np.asarray([], dtype=np.float64)

    order = np.argsort(np.asarray(times, dtype=np.int64), kind="mergesort")
    t_arr = np.asarray(times, dtype=np.int64)[order]
    p_arr = np.asarray(prices, dtype=np.float64)[order]
    return t_arr, p_arr


def _write_m1_bars_npz(out_path: Path, bars: Sequence[Mapping[str, Any]]) -> str:
    """Atomically write broker M1 Bid/Ask bars to compressed `.npz` and return SHA-256."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    arrays = {
        "bar_open_ts": np.asarray([int(b["bar_open_ts"]) for b in bars], dtype=np.int64),
        "bar_open_ts_ms": np.asarray([int(b["bar_open_ts_ms"]) for b in bars], dtype=np.int64),
        "bid_open": np.asarray([float(b["bid_open"]) for b in bars], dtype=np.float64),
        "bid_high": np.asarray([float(b["bid_high"]) for b in bars], dtype=np.float64),
        "bid_low": np.asarray([float(b["bid_low"]) for b in bars], dtype=np.float64),
        "bid_close": np.asarray([float(b["bid_close"]) for b in bars], dtype=np.float64),
        "ask_open": np.asarray([float(b["ask_open"]) for b in bars], dtype=np.float64),
        "ask_high": np.asarray([float(b["ask_high"]) for b in bars], dtype=np.float64),
        "ask_low": np.asarray([float(b["ask_low"]) for b in bars], dtype=np.float64),
        "ask_close": np.asarray([float(b["ask_close"]) for b in bars], dtype=np.float64),
        "spread_pts_min": np.asarray([float(b["spread_pts_min"]) for b in bars], dtype=np.float64),
        "spread_pts_median": np.asarray([float(b["spread_pts_median"]) for b in bars], dtype=np.float64),
        "spread_pts_max": np.asarray([float(b["spread_pts_max"]) for b in bars], dtype=np.float64),
        "spread_pts_close": np.asarray([float(b["spread_pts_close"]) for b in bars], dtype=np.float64),
        "tick_count": np.asarray([int(b["tick_count"]) for b in bars], dtype=np.int64),
    }
    fd, tmp_name = tempfile.mkstemp(prefix=f".{out_path.stem}.", suffix=".npz", dir=str(out_path.parent))
    os.close(fd)
    tmp_path = Path(tmp_name)
    try:
        np.savez_compressed(tmp_path, **arrays)
        os.replace(tmp_path, out_path)
    except Exception:
        if tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise
    return _sha256_file(out_path)


def load_ingested_broker_m1_bars(account_vault_dir: Path | str, symbol: str) -> list[dict[str, Any]]:
    """Reload broker M1 Bid/Ask bars from `<account_vault_dir>/m1_bars/<SYMBOL>_m1_bidask.npz`."""
    canon = normalize_symbol_alias(symbol)
    npz_path = Path(account_vault_dir) / "m1_bars" / f"{canon}_m1_bidask.npz"
    if not npz_path.is_file():
        raise FileNotFoundError(f"Ingested broker M1 bars not found for {symbol!r}: {npz_path}")
    pt = point_size_for_symbol(canon)
    bars: list[dict[str, Any]] = []
    with np.load(npz_path) as data:
        n = len(data["bar_open_ts"])
        for i in range(n):
            bo_ts = int(data["bar_open_ts"][i])
            bo_ms = int(data["bar_open_ts_ms"][i])
            b_o, b_h, b_l, b_c = (
                float(data["bid_open"][i]),
                float(data["bid_high"][i]),
                float(data["bid_low"][i]),
                float(data["bid_close"][i]),
            )
            a_o, a_h, a_l, a_c = (
                float(data["ask_open"][i]),
                float(data["ask_high"][i]),
                float(data["ask_low"][i]),
                float(data["ask_close"][i]),
            )
            bars.append(
                {
                    "symbol": canon,
                    "canonical_symbol": canon,
                    "bar_open_ts": bo_ts,
                    "bar_open_ts_ms": bo_ms,
                    "bar_open_utc": datetime.fromtimestamp(bo_ts, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "point": pt,
                    "bid_open": b_o,
                    "bid_high": b_h,
                    "bid_low": b_l,
                    "bid_close": b_c,
                    "ask_open": a_o,
                    "ask_high": a_h,
                    "ask_low": a_l,
                    "ask_close": a_c,
                    "mid_open": 0.5 * (b_o + a_o),
                    "mid_high": 0.5 * (b_h + a_h),
                    "mid_low": 0.5 * (b_l + a_l),
                    "mid_close": 0.5 * (b_c + a_c),
                    "spread_pts_min": float(data["spread_pts_min"][i]),
                    "spread_pts_median": float(data["spread_pts_median"][i]),
                    "spread_pts_max": float(data["spread_pts_max"][i]),
                    "spread_pts_close": float(data["spread_pts_close"][i]),
                    "tick_count": int(data["tick_count"][i]),
                }
            )
    return bars


def ingest_live_broker_tape(
    *,
    account_alias: str,
    quote_tape_paths: Path | str | Sequence[Path | str],
    symbol_specs_path: Path | str | None = None,
    vault_root: Path | str | None = None,
    hot_m1_cache_dir: Path | str | None = None,
    holdout_dir: Path | str | None = None,
    bar_seconds: int = 60,
    write_m1_bars: bool = True,
) -> dict[str, Any]:
    """Ingest live/demo broker quote tapes + symbol specs into `.runtime/live-vault/<account_alias>/`.

    Verifies strict zero contamination of `.runtime/hot-m1-cache/` and Holdout `2025+`,
    copies raw tapes read-only, builds broker M1 Bid/Ask `.npz` bars, and writes a tamper-evident
    SHA-256 manifest (`live_vault_manifest.json`).
    """
    eff_vault_root = DEFAULT_LIVE_VAULT_ROOT if vault_root is None else Path(vault_root)
    account_dir = validate_live_vault_target(
        eff_vault_root,
        account_alias,
        hot_m1_cache_dir=hot_m1_cache_dir,
        holdout_dir=holdout_dir,
    )
    pre_isolation = verify_zero_cache_contamination(
        account_dir,
        hot_m1_cache_dir=hot_m1_cache_dir,
        holdout_dir=holdout_dir,
    )
    if not pre_isolation["clean"]:
        raise LiveVaultIsolationError(f"LIVE_VAULT_ISOLATION_PRECHECK_FAILED: {pre_isolation}")

    tape_paths = (
        [Path(quote_tape_paths)]
        if isinstance(quote_tape_paths, (str, Path))
        else [Path(p) for p in quote_tape_paths]
    )
    if not tape_paths:
        raise ValueError("quote_tape_paths must contain at least one broker quote tape file")
    for tp in tape_paths:
        if not tp.is_file():
            raise FileNotFoundError(f"Quote tape file not found: {tp}")

    specs_map: dict[str, dict[str, Any]] = {}
    specs_src_sha: str | None = None
    if symbol_specs_path is not None:
        sp_path = Path(symbol_specs_path)
        specs_map = load_broker_symbol_specs(sp_path)
        specs_src_sha = _sha256_file(sp_path)

    all_ticks: list[dict[str, Any]] = []
    source_file_entries: list[dict[str, Any]] = []

    raw_tapes_dir = account_dir / "tapes"
    raw_tapes_dir.mkdir(parents=True, exist_ok=True)

    for idx, tp in enumerate(tape_paths):
        ticks = load_broker_quote_tape(tp, symbol_specs=specs_map or None, deduplicate=False)
        all_ticks.extend(ticks)
        src_sha = _sha256_file(tp)
        dest_name = tp.name
        dest_path = raw_tapes_dir / dest_name
        if dest_path.exists() and _sha256_file(dest_path) != src_sha:
            dest_name = f"{tp.stem}_{idx}_{src_sha[:8]}{tp.suffix}"
            dest_path = raw_tapes_dir / dest_name
        if tp.resolve(strict=False) != dest_path.resolve(strict=False):
            shutil.copy2(tp, dest_path)
        copied_sha = _sha256_file(dest_path)
        if copied_sha != src_sha:
            raise OSError(f"SHA256_COPY_MISMATCH for {tp.name}: src={src_sha} != dst={copied_sha}")
        source_file_entries.append(
            {
                "kind": "quote_tape",
                "filename": dest_name,
                "rel_path": f"tapes/{dest_name}",
                "sha256": copied_sha,
                "bytes": dest_path.stat().st_size,
                "tick_count": len(ticks),
            }
        )

    if not all_ticks:
        raise ValueError("ZERO_QUOTES_INGESTED: broker quote tape(s) produced 0 valid Bid/Ask ticks")

    deduped_ticks = parse_broker_quote_records(all_ticks, symbol_specs=specs_map or None, deduplicate=True)
    m1_bars_by_sym = build_broker_m1_bars_from_quotes(
        deduped_ticks,
        symbol_specs=specs_map or None,
        bar_seconds=bar_seconds,
    )

    specs_artifact_entry: dict[str, Any] | None = None
    if symbol_specs_path is not None and specs_src_sha is not None:
        specs_out = account_dir / "specs" / "broker_symbol_specs.json"
        specs_receipt = write_atomic_sha256_json(
            specs_out,
            {
                "schema": BROKER_SPECS_SCHEMA,
                "account_alias": validate_account_alias(account_alias),
                "source_filename": Path(symbol_specs_path).name,
                "source_sha256": specs_src_sha,
                "symbol_count": len(specs_map),
                "symbols": specs_map,
            },
        )
        specs_artifact_entry = {
            "kind": "broker_symbol_specs",
            "rel_path": "specs/broker_symbol_specs.json",
            "source_sha256": specs_src_sha,
            "sha256": specs_receipt["file_sha256"],
            "bytes": specs_receipt["bytes"],
            "symbol_count": len(specs_map),
        }

    m1_bar_manifest: dict[str, dict[str, Any]] = {}
    m1_dir = account_dir / "m1_bars"
    for sym, bars in sorted(m1_bars_by_sym.items()):
        med_spreads = sorted(b["spread_pts_median"] for b in bars)
        mid_i = len(med_spreads) // 2
        sym_med_spread = (
            med_spreads[mid_i]
            if len(med_spreads) % 2 == 1
            else 0.5 * (med_spreads[mid_i - 1] + med_spreads[mid_i])
        )
        bar_meta: dict[str, Any] = {
            "canonical_symbol": sym,
            "bar_seconds": bar_seconds,
            "bar_count": len(bars),
            "tick_count": sum(int(b["tick_count"]) for b in bars),
            "first_bar_ts": int(bars[0]["bar_open_ts"]),
            "last_bar_ts": int(bars[-1]["bar_open_ts"]),
            "first_bar_utc": bars[0]["bar_open_utc"],
            "last_bar_utc": bars[-1]["bar_open_utc"],
            "median_spread_pts": round(float(sym_med_spread), 4),
        }
        if write_m1_bars:
            npz_path = m1_dir / f"{sym}_m1_bidask.npz"
            npz_sha = _write_m1_bars_npz(npz_path, bars)
            bar_meta["rel_path"] = f"m1_bars/{sym}_m1_bidask.npz"
            bar_meta["sha256"] = npz_sha
            bar_meta["bytes"] = npz_path.stat().st_size
        m1_bar_manifest[sym] = bar_meta

    post_isolation = verify_zero_cache_contamination(
        account_dir,
        hot_m1_cache_dir=hot_m1_cache_dir,
        holdout_dir=holdout_dir,
    )
    if not post_isolation["clean"]:
        raise LiveVaultIsolationError(f"LIVE_VAULT_ISOLATION_POSTCHECK_FAILED: {post_isolation}")
    if (
        pre_isolation["hot_m1_cache_manifest_sha256"] is not None
        and post_isolation["hot_m1_cache_manifest_sha256"] != pre_isolation["hot_m1_cache_manifest_sha256"]
    ):
        raise LiveVaultIsolationError("HOT_M1_CACHE_MANIFEST_CHANGED_DURING_INGESTION")

    manifest_payload: dict[str, Any] = {
        "schema": LIVE_VAULT_MANIFEST_SCHEMA,
        "ingested_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "account_alias": validate_account_alias(account_alias),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "isolation": {
            "verified": True,
            "hot_m1_cache_contaminated": False,
            "holdout_contaminated": False,
            "hot_m1_cache_manifest_sha256_before": pre_isolation["hot_m1_cache_manifest_sha256"],
            "hot_m1_cache_manifest_sha256_after": post_isolation["hot_m1_cache_manifest_sha256"],
        },
        "total_deduped_ticks": len(deduped_ticks),
        "symbols_ingested": sorted(m1_bars_by_sym.keys()),
        "source_files": source_file_entries,
        "symbol_specs": specs_artifact_entry,
        "m1_bars": m1_bar_manifest,
    }
    manifest_path = account_dir / "live_vault_manifest.json"
    receipt = write_atomic_sha256_json(manifest_path, manifest_payload)
    manifest_payload["report_sha256"] = receipt["report_sha256"]

    return {
        "manifest_path": str(manifest_path),
        "account_vault_dir": str(account_dir),
        "manifest": manifest_payload,
        "m1_bars_by_symbol": m1_bars_by_sym,
        "ticks_count": len(deduped_ticks),
    }


def verify_live_vault_manifest(account_vault_dir: Path | str) -> dict[str, Any]:
    """Verify canonical `report_sha256` and every file SHA-256 recorded in `live_vault_manifest.json`."""
    vault_dir = Path(account_vault_dir)
    manifest_path = vault_dir / "live_vault_manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"live_vault_manifest.json not found in {vault_dir}")

    doc = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(doc, Mapping):
        raise ValueError("Malformed live_vault_manifest.json")

    expected_report_sha = str(doc.get("report_sha256") or "")
    actual_report_sha = canonical_payload_sha256(doc)
    mismatches: list[str] = []
    if expected_report_sha != actual_report_sha:
        mismatches.append(f"REPORT_SHA256_MISMATCH: expected={expected_report_sha}, actual={actual_report_sha}")

    checked_files = 0
    for src in doc.get("source_files") or []:
        rel = str(src.get("rel_path") or "")
        p = vault_dir / rel
        if not p.is_file():
            mismatches.append(f"MISSING_SOURCE_FILE:{rel}")
            continue
        checked_files += 1
        got = _sha256_file(p)
        if got != src.get("sha256"):
            mismatches.append(f"SOURCE_SHA_MISMATCH:{rel}")

    specs = doc.get("symbol_specs")
    if isinstance(specs, Mapping) and specs.get("rel_path"):
        rel = str(specs["rel_path"])
        p = vault_dir / rel
        if not p.is_file():
            mismatches.append(f"MISSING_SPECS_FILE:{rel}")
        else:
            checked_files += 1
            if _sha256_file(p) != specs.get("sha256"):
                mismatches.append(f"SPECS_SHA_MISMATCH:{rel}")

    for sym, meta in (doc.get("m1_bars") or {}).items():
        if isinstance(meta, Mapping) and meta.get("rel_path"):
            rel = str(meta["rel_path"])
            p = vault_dir / rel
            if not p.is_file():
                mismatches.append(f"MISSING_M1_BAR_FILE:{sym}:{rel}")
            else:
                checked_files += 1
                if _sha256_file(p) != meta.get("sha256"):
                    mismatches.append(f"M1_BAR_SHA_MISMATCH:{sym}:{rel}")

    return {
        "valid": len(mismatches) == 0,
        "checked_files": checked_files,
        "report_sha256": actual_report_sha,
        "mismatches": mismatches,
    }


__all__ = [
    "BROKER_SPECS_SCHEMA",
    "DEFAULT_HOT_M1_CACHE_DIR",
    "DEFAULT_LIVE_VAULT_ROOT",
    "LIVE_VAULT_MANIFEST_SCHEMA",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "POINT_SIZES",
    "LiveVaultIsolationError",
    "build_broker_m1_bars_from_quotes",
    "extract_executable_price_path",
    "ingest_live_broker_tape",
    "load_broker_quote_tape",
    "load_broker_symbol_specs",
    "load_ingested_broker_m1_bars",
    "parse_broker_quote_records",
    "validate_account_alias",
    "validate_live_vault_target",
    "verify_live_vault_manifest",
    "verify_zero_cache_contamination",
]
