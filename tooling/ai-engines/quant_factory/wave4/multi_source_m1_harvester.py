"""Multi-Source Compliant M1 Harvester (QDM CLI -> FTMO-Demo -> HistData/TrueFX; 0 WAF bypass).

Builds the Wave 4 compliant Dev-only (`2018-2024`, `< 2025-01-01` UTC) M1 harvest pipeline for the
exact `16` remaining symbols in `seal_asset_m1.ASSET_DEFAULT_SCALES` not yet present in
`.runtime/hot-m1-cache/manifest.json`.

Hard safety invariants (Total Offensive #4 v4.8.1 FINAL — ZERO bare `assert`s, `python -O` safe):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0` (offline research/data prep ONLY).
  - `WAF_BYPASS_ATTEMPTED = False` ALWAYS (never contacts Dukascopy HTTP endpoints or bypasses WAF).
  - Hard Holdout cutoff `< 2025-01-01T00:00:00Z` enforced on every tier (`holdout_rows_analysed == 0`).
  - NEVER imports `trading_workspace_v2.qdm_cli` (avoids `psycopg` dependency in quant venv).
    Invokes `qdmcli.exe` directly via `subprocess.run(..., creationflags=_NO_WINDOW_FLAGS)`.
  - NEVER passes `broker=SQ Default` (or any `broker=` flag with whitespace) to `qdmcli.exe`,
    enforces a single-process QDM CLI file lock, and strictly uses `action=export` with
    `dateto <= 2024.12.31`.
  - Lazy `MetaTrader5` import ONLY inside Tier 2 live execution, fail-closed unless both
    `mt5_lock_held=True` and `allow_live_mt5=True` (or explicit `delegate_exporter` / injected
    mock `mt5_module`) are passed. Never launches `terminal64.exe` during dry-run or tests.
  - Honest source provenance tags preserved end-to-end into Parquet/NPZ/fragment/manifest:
      * `DUKASCOPY_TRUE_BID_ASK` (existing paired 2-side JSON only)
      * `QDM_PROVIDER_DEFAULT_SINGLE_SIDE` (never disguised as true 2-side Bid/Ask)
      * `FTMO_BID_PLUS_SPREAD` (FTMO-Demo M1 Bid + bar spread points)
      * `HISTDATA_BID_ONLY` (HistData/TrueFX free compliant FX M1)
"""

from __future__ import annotations

import argparse
import contextlib
import csv
import hashlib
import io
import json
import math
import os
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
from collections.abc import Callable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES_DIR = Path(__file__).resolve().parents[2]
ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)

from quant_factory import seal_asset_m1 as sam  # noqa: E402
from quant_factory.wave4 import (  # noqa: E402
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
)

# ==============================================================================
# Constants & Canonical Contracts
# ==============================================================================

SCHEMA_VERSION: str = "naqex-wave4-multi-source-m1-harvester-v1"
ORDER_SEND_COUNT: int = 0
WAF_BYPASS_ATTEMPTED: bool = False

DEV_START_DATE: str = "2018-01-01"
DEV_START_QDM_DATE: str = "2018.01.01"
HOLDOUT_CUTOFF_QDM_DATE: str = "2024.12.31"
DEV_START_UTC_SEC: int = sam.START_SEC
HOLDOUT_STOP_UTC_SEC: int = sam.STOP_SEC

TIER_1_QDM_CLI: str = "TIER_1_QDM_CLI"
TIER_2_FTMO_DEMO: str = "TIER_2_FTMO_DEMO"
TIER_3_HISTDATA_TRUEFX: str = "TIER_3_HISTDATA_TRUEFX"
CASCADE_ORDER: tuple[str, ...] = (
    TIER_1_QDM_CLI,
    TIER_2_FTMO_DEMO,
    TIER_3_HISTDATA_TRUEFX,
)

PROVENANCE_BY_TIER: dict[str, str] = {
    TIER_1_QDM_CLI: sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
    TIER_2_FTMO_DEMO: sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
    TIER_3_HISTDATA_TRUEFX: sam.PROVENANCE_HISTDATA_BID_ONLY,
}

DEFAULT_CACHE_DIR: Path = sam.DEFAULT_CACHE
DEFAULT_MANIFEST_PATH: Path = DEFAULT_CACHE_DIR / "manifest.json"
DEFAULT_FTMO_SPECS_PATH: Path = AI_ENGINES_DIR / "configs" / "ssot" / "ftmo_specs_28.json"
DEFAULT_WORK_ROOT: Path = ROOT / ".runtime" / "offensive4" / "m1"
DEFAULT_QDM_LOCK_PATH: Path = DEFAULT_WORK_ROOT / ".qdm_cli.lock"
DEFAULT_QDM_TIMEOUT_SEC: int = 1800

QDM_CATALOG_REL_PATH: Path = Path("internal/plugins/DataSourceDukascopy/dukascopy.csv")
QDM_LIST_HEADER: str = (
    "Symbol,Instrument,Timeframe,Timezone,Date from,Date to,Total days,Total records,Source,Data type"
)
QDM_CUSTOM_HEADER: str = "Date,Time,Open,High,Low,Close,Volume"
QDM_CUSTOM_FORMAT: str = "[Date:yyyy.MM.dd],[Time:HH:mm:ss],[Open],[High],[Low],[Close],[Volume]"

# Windows windowless subprocess flag (0 on POSIX where CPython accepts 0 cleanly)
_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

_QDM_DATE_RE = re.compile(r"^(\d{4})[.\-](\d{2})[.\-](\d{2})$")
_QDM_SYMBOL_RE = re.compile(r"^[A-Za-z0-9_.-]{3,32}$")
_SAFE_SYMBOL_RE = re.compile(r"^[A-Z0-9]{3,16}$")
_COMPACT_DT_RE = re.compile(r"^(\d{4})(\d{2})(\d{2})[ T](\d{2})(\d{2})(\d{2})?$")
_DOT_DATE_RE = re.compile(r"^(\d{4})[.\-/](\d{2})[.\-/](\d{2})$")
_HMS_TIME_RE = re.compile(r"^(\d{2}):(\d{2})(?::(\d{2}))?$")
_ISO_DT_RE = re.compile(
    r"^(\d{4})[.\-/](\d{2})[.\-/](\d{2})[ T](\d{2}):(\d{2})(?::(\d{2}))?(?:\.\d+)?(?:Z|z)?$"
)

# Max decompressed bytes per ZIP member in Tier 3 (guards against zip-bomb inputs)
_MAX_ZIP_MEMBER_BYTES: int = 256 * 1024 * 1024
_MAX_ZIP_MEMBERS: int = 64

# Canonical mapping for all 28 symbols in seal_asset_m1.ASSET_DEFAULT_SCALES:
# (qdm_instrument_code, ftmo_symbol, asset_class, point_size, histdata_fx_eligible)
CANONICAL_SYMBOL_MAP: dict[str, tuple[str, str, str, float, bool]] = {
    # 12 currently sealed in .runtime/hot-m1-cache/manifest.json
    "EURUSD": ("EURUSD", "EURUSD", "forex", 1e-5, True),
    "GBPUSD": ("GBPUSD", "GBPUSD", "forex", 1e-5, True),
    "AUDUSD": ("AUDUSD", "AUDUSD", "forex", 1e-5, True),
    "USDCAD": ("USDCAD", "USDCAD", "forex", 1e-5, True),
    "USDJPY": ("USDJPY", "USDJPY", "forex", 1e-3, True),
    "EURJPY": ("EURJPY", "EURJPY", "forex", 1e-3, True),
    "GBPJPY": ("GBPJPY", "GBPJPY", "forex", 1e-3, True),
    "US100": ("USATECHIDXUSD", "US100.cash", "indices", 1e-2, False),
    "US500": ("USA500IDXUSD", "US500.cash", "indices", 1e-2, False),
    "GER40": ("DEUIDXEUR", "GER40.cash", "indices", 1e-2, False),
    "XAUUSD": ("XAUUSD", "XAUUSD", "metals", 1e-2, False),
    "BTCUSD": ("BTCUSD", "BTCUSD", "crypto", 1e-2, False),
    # 16 remaining symbols to harvest in Wave 4
    "USDCHF": ("USDCHF", "USDCHF", "forex", 1e-5, True),
    "NZDUSD": ("NZDUSD", "NZDUSD", "forex", 1e-5, True),
    "EURGBP": ("EURGBP", "EURGBP", "forex", 1e-5, True),
    "EURAUD": ("EURAUD", "EURAUD", "forex", 1e-5, True),
    "GBPAUD": ("GBPAUD", "GBPAUD", "forex", 1e-5, True),
    "EURCAD": ("EURCAD", "EURCAD", "forex", 1e-5, True),
    "AUDJPY": ("AUDJPY", "AUDJPY", "forex", 1e-3, True),
    "CADJPY": ("CADJPY", "CADJPY", "forex", 1e-3, True),
    "CHFJPY": ("CHFJPY", "CHFJPY", "forex", 1e-3, True),
    "NZDJPY": ("NZDJPY", "NZDJPY", "forex", 1e-3, True),
    "US30": ("USA30IDXUSD", "US30.cash", "indices", 1e-2, False),
    "JP225": ("JPNIDXJPY", "JP225.cash", "indices", 1e-2, False),
    "UK100": ("GBRIDXGBP", "UK100.cash", "indices", 1e-2, False),
    "XAGUSD": ("XAGUSD", "XAGUSD", "metals", 1e-3, False),
    "USOIL": ("LIGHTCMDUSD", "USOIL.cash", "oil", 1e-3, False),
    "UKOIL": ("BRENTCMDUSD", "UKOIL.cash", "oil", 1e-3, False),
}


# ==============================================================================
# Typed Exceptions & Data Contracts
# ==============================================================================


class HarvesterError(RuntimeError):
    """Base fail-closed error for compliant M1 harvest operations."""


class QdmUnavailableError(HarvesterError):
    """Raised when `qdmcli.exe` cannot be located or executed."""


class QdmBusyError(HarvesterError):
    """Raised when another QDM GUI/CLI instance holds the single-process lock."""


class QdmLicenseError(HarvesterError):
    """Raised when QDM reports missing/expired local license."""


class Mt5LockRequiredError(HarvesterError):
    """Raised fail-closed when Tier 2 FTMO-Demo is called without `[MT5 LOCK]` authorization."""


@dataclass(frozen=True)
class SymbolHarvestSpec:
    canonical_symbol: str
    scale: int
    asset_class: str
    qdm_instrument_code: str
    qdm_symbol_name: str
    ftmo_symbol: str
    ftmo_point_size: float
    histdata_fx_eligible: bool
    eligible_tiers: tuple[str, ...]
    expected_provenance_by_tier: dict[str, str]


@dataclass(frozen=True)
class ValidatedM1Batch:
    asset: str
    tier: str
    source_provenance: str
    times_sec: np.ndarray
    bid_ohlc: np.ndarray
    ask_ohlc: np.ndarray | None
    spread_points: np.ndarray | None
    point_size: float | None
    bar_count: int
    min_ts_sec: int
    max_ts_sec: int
    min_ts_utc: str
    max_ts_utc: str
    min_price: float
    max_price: float
    nonpositive_detected: int
    nonpositive_filtered: int
    has_true_bid_ask: bool
    native_ask: bool
    ask_columns_present: bool
    waf_bypass_attempted: bool = False
    holdout_rows_analysed: int = 0
    source_detail: str = ""


@dataclass(frozen=True)
class TierAttemptRecord:
    tier: str
    status: str
    source_provenance: str
    reason: str
    waf_bypass_attempted: bool = False


@dataclass(frozen=True)
class SymbolHarvestResult:
    symbol: str
    status: str
    selected_tier: str | None
    source_provenance: str | None
    native_ask: bool
    has_true_bid_ask: bool
    bar_count: int
    max_ts_utc: str | None
    holdout_rows_analysed: int
    waf_bypass_attempted: bool
    attempts: tuple[TierAttemptRecord, ...]
    fragment: dict[str, Any] | None = None
    fragment_path: str | None = None
    npz_path: str | None = None


# ==============================================================================
# Helper Utilities (Zero Bare Asserts, Atomic I/O)
# ==============================================================================


def _utc_iso(ts_sec: int) -> str:
    return datetime.fromtimestamp(int(ts_sec), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(text)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _normalize_symbol(symbol: str) -> str:
    cleaned = str(symbol or "").strip().upper()
    if not cleaned or _SAFE_SYMBOL_RE.fullmatch(cleaned) is None:
        raise ValueError(f"Invalid canonical symbol identifier: {symbol!r}")
    return cleaned


def _parse_strict_float(raw: Any, *, label: str) -> float:
    if isinstance(raw, bool) or raw is None:
        raise ValueError(f"INVALID_NUMERIC [{label}]: bool/None rejected ({raw!r})")
    if isinstance(raw, str):
        stripped = raw.strip()
        if not stripped:
            raise ValueError(f"INVALID_NUMERIC [{label}]: empty string rejected")
        try:
            val = float(stripped)
        except ValueError as exc:
            raise ValueError(f"INVALID_NUMERIC [{label}]: cannot parse float from {raw!r}") from exc
    elif isinstance(raw, (int, float, np.integer, np.floating)):
        val = float(raw)
    else:
        raise ValueError(f"INVALID_NUMERIC [{label}]: unsupported type {type(raw).__name__}")
    if not math.isfinite(val):
        raise ValueError(f"NONFINITE_PRICE [{label}]: {val!r}")
    return val


def _parse_date_to_dot(date_str: str, *, label: str) -> tuple[date, str]:
    """Validate and convert YYYY-MM-DD / YYYY.MM.DD into `(date, 'YYYY.MM.DD')` with Holdout guard."""
    if not isinstance(date_str, str) or not date_str.strip():
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{label}]: empty/non-str date {date_str!r}")
    text = date_str.strip()
    match = _QDM_DATE_RE.fullmatch(text)
    if match is None:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{label}]: malformed date {date_str!r}")
    iso_text = f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    enforce_pre_holdout_dates(iso_text, context=label, cutoff_day="2025-01-01", allow_empty=False)
    try:
        parsed = date.fromisoformat(iso_text)
    except ValueError as exc:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{label}]: invalid calendar date {date_str!r}") from exc
    if parsed < date(2018, 1, 1):
        raise HoldoutLockError(
            f"PRE_DEV_RANGE_BREACH [{label}]: date {iso_text} is before Dev start {DEV_START_DATE}"
        )
    return parsed, f"{parsed.year:04d}.{parsed.month:02d}.{parsed.day:02d}"


# ==============================================================================
# Inventory Discovery (Exact 16 Remaining Symbols)
# ==============================================================================


def _load_ftmo_specs_optional(specs_path: Path = DEFAULT_FTMO_SPECS_PATH) -> dict[str, dict[str, Any]]:
    if not specs_path.is_file():
        return {}
    try:
        doc = json.loads(specs_path.read_text(encoding="utf-8-sig"))
    except Exception:
        return {}
    syms = doc.get("symbols") if isinstance(doc, dict) else None
    return dict(syms) if isinstance(syms, dict) else {}


def build_symbol_harvest_spec(
    symbol: str,
    *,
    ftmo_specs: Mapping[str, Mapping[str, Any]] | None = None,
) -> SymbolHarvestSpec:
    """Build canonical harvest metadata for a symbol in `seal_asset_m1.ASSET_DEFAULT_SCALES`."""
    sym_u = _normalize_symbol(symbol)
    if sym_u not in sam.ASSET_DEFAULT_SCALES:
        raise ValueError(f"Unknown symbol not in seal_asset_m1.ASSET_DEFAULT_SCALES: {sym_u!r}")
    if sym_u not in CANONICAL_SYMBOL_MAP:
        raise ValueError(f"Symbol {sym_u!r} missing from CANONICAL_SYMBOL_MAP")

    qdm_code, ftmo_sym, asset_class, point_size, histdata_ok = CANONICAL_SYMBOL_MAP[sym_u]
    if ftmo_specs is not None and sym_u in ftmo_specs:
        sp = ftmo_specs[sym_u]
        ftmo_sym = str(sp.get("ftmo_symbol", ftmo_sym))
        asset_class = str(sp.get("asset_class", asset_class))
        raw_pt = sp.get("point")
        if raw_pt is not None and not isinstance(raw_pt, bool) and float(raw_pt) > 0.0:
            point_size = float(raw_pt)

    eligible_tiers: tuple[str, ...] = (
        (TIER_1_QDM_CLI, TIER_2_FTMO_DEMO, TIER_3_HISTDATA_TRUEFX)
        if histdata_ok
        else (TIER_1_QDM_CLI, TIER_2_FTMO_DEMO)
    )
    return SymbolHarvestSpec(
        canonical_symbol=sym_u,
        scale=int(sam.ASSET_DEFAULT_SCALES[sym_u]),
        asset_class=asset_class,
        qdm_instrument_code=qdm_code,
        qdm_symbol_name=f"{qdm_code}_TW",
        ftmo_symbol=ftmo_sym,
        ftmo_point_size=float(point_size),
        histdata_fx_eligible=bool(histdata_ok),
        eligible_tiers=eligible_tiers,
        expected_provenance_by_tier={t: PROVENANCE_BY_TIER[t] for t in eligible_tiers},
    )


def discover_missing_m1_symbols(
    manifest_path: Path = DEFAULT_MANIFEST_PATH,
    *,
    scales_map: Mapping[str, int] | None = None,
    ftmo_specs_path: Path = DEFAULT_FTMO_SPECS_PATH,
    allow_missing_manifest: bool = False,
) -> dict[str, Any]:
    """Inventory exact symbols from `ASSET_DEFAULT_SCALES` missing from `manifest.json`."""
    universe = dict(scales_map) if scales_map is not None else dict(sam.ASSET_DEFAULT_SCALES)
    present_assets: set[str] = set()
    manifest_found = False

    mpath = Path(manifest_path)
    if mpath.is_file():
        manifest_found = True
        manifest = json.loads(mpath.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), dict):
            raise ValueError(f"Malformed hot M1 manifest at {mpath}")
        enforce_holdout_zero_rows(manifest.get("holdout_rows"), context="discover_missing_m1_symbols")
        present_assets = {str(k).strip().upper() for k in manifest["assets"]}
    elif not allow_missing_manifest:
        raise FileNotFoundError(f"Hot M1 cache manifest not found: {mpath}")

    ftmo_specs = _load_ftmo_specs_optional(ftmo_specs_path)
    universe_order = [str(k).strip().upper() for k in universe]
    present_in_universe = [s for s in universe_order if s in present_assets]
    missing_symbols = [s for s in universe_order if s not in present_assets]
    specs = [build_symbol_harvest_spec(s, ftmo_specs=ftmo_specs) for s in missing_symbols]

    return {
        "schema": SCHEMA_VERSION,
        "manifest_path": str(mpath),
        "manifest_found": manifest_found,
        "universe_count": len(universe_order),
        "present_count": len(present_in_universe),
        "missing_count": len(missing_symbols),
        "present_symbols": present_in_universe,
        "missing_symbols": missing_symbols,
        "missing_specs": [asdict(sp) for sp in specs],
        "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
    }


# ==============================================================================
# Shared Hard Bar Validator (All 3 Tiers)
# ==============================================================================


def validate_m1_bars(
    asset: str,
    times_sec: np.ndarray | Sequence[int],
    bid_ohlc: np.ndarray,
    *,
    tier: str,
    source_provenance: str,
    ask_ohlc: np.ndarray | None = None,
    spread_points: np.ndarray | None = None,
    point_size: float | None = None,
    filter_nonpositive: bool = False,
    waf_bypass_attempted: bool = False,
    source_detail: str = "",
) -> ValidatedM1Batch:
    """Fail-closed validation of M1 OHLC bars across all 3 compliant harvest tiers.

    Enforces:
      - `waf_bypass_attempted is False`
      - Honest `source_provenance` (single-side never labeled true Bid/Ask)
      - Monotonic minute-aligned timestamps strictly inside `[2018-01-01, 2025-01-01)` UTC
      - `0` NaN/Inf, `0` prices `<= 0` (unless `filter_nonpositive=True` quarantines `<= 0`)
      - Exact intra-bar OHLC ordering `high >= max(open, close) >= min(open, close) >= low`
      - Non-crossed `ask >= bid` whenever Ask columns exist
    """
    if waf_bypass_attempted is not False:
        raise ValueError("WAF_BYPASS_FORBIDDEN: waf_bypass_attempted MUST always be False")
    asset_u = _normalize_symbol(asset)
    if not isinstance(source_provenance, str) or source_provenance not in sam.VALID_SOURCE_PROVENANCES:
        raise ValueError(f"INVALID_SOURCE_PROVENANCE [{asset_u}]: {source_provenance!r}")

    # Enforce strict provenance honesty (never disguise single-side as true 2-side!)
    if source_provenance in sam.SINGLE_SIDE_ONLY_PROVENANCES:
        if ask_ohlc is not None:
            raise ValueError(
                f"PROVENANCE_HONESTY_VIOLATION [{asset_u}]: {source_provenance} is single-side only "
                "and must not attach ask_ohlc"
            )
        native_ask = False
        has_true_bid_ask = False
        ask_columns_present = False
    elif source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD:
        if ask_ohlc is None and (spread_points is None or point_size is None):
            raise ValueError(
                f"PROVENANCE_MISSING_SPREAD [{asset_u}]: FTMO_BID_PLUS_SPREAD requires ask_ohlc "
                "or (spread_points, point_size)"
            )
        native_ask = False
        has_true_bid_ask = False
        ask_columns_present = True
    else:
        if ask_ohlc is None:
            raise ValueError(
                f"PROVENANCE_MISSING_ASK [{asset_u}]: DUKASCOPY_TRUE_BID_ASK requires explicit ask_ohlc"
            )
        native_ask = True
        has_true_bid_ask = True
        ask_columns_present = True

    ts_raw = np.asarray(times_sec)
    if ts_raw.ndim != 1 or ts_raw.size == 0:
        raise ValueError(f"INVALID_TIMESTAMPS [{asset_u}]: expected non-empty 1D array, got shape={ts_raw.shape}")
    if ts_raw.dtype == np.bool_ or not np.issubdtype(ts_raw.dtype, np.integer):
        raise HoldoutLockError(
            f"INVALID_TIMESTAMPS [{asset_u}]: expected integer UTC epoch seconds, got dtype={ts_raw.dtype}"
        )
    ts_arr = ts_raw.astype(np.int64, copy=True)

    # Hard Holdout guard BEFORE any filtering (immune to python -O)
    enforce_pre_holdout_ts(
        ts_arr,
        DEV_START_UTC_SEC,
        HOLDOUT_STOP_UTC_SEC,
        context=f"validate_m1_bars:{asset_u}:{tier}",
        allow_empty=False,
    )
    if bool(np.any(ts_arr % 60 != 0)):
        raise ValueError(f"NON_MINUTE_ALIGNED_TIMESTAMPS [{asset_u}]: all M1 timestamps must be multiples of 60s")
    if ts_arr.size > 1 and not bool(np.all(np.diff(ts_arr) > 0)):
        raise ValueError(f"NON_MONOTONIC_TIMESTAMPS [{asset_u}]: timestamps must strictly increase without duplicates")

    b_raw = np.asarray(bid_ohlc)
    if b_raw.ndim != 2 or b_raw.shape != (ts_arr.size, 4):
        raise ValueError(
            f"INVALID_OHLC_SHAPE [{asset_u}]: bid_ohlc shape {b_raw.shape} != ({ts_arr.size}, 4)"
        )
    if b_raw.dtype == np.bool_ or not (
        np.issubdtype(b_raw.dtype, np.floating) or np.issubdtype(b_raw.dtype, np.integer)
    ):
        raise ValueError(f"INVALID_OHLC_DTYPE [{asset_u}]: bid_ohlc dtype={b_raw.dtype} rejected")
    b_arr = b_raw.astype(np.float64, copy=True)
    if not bool(np.all(np.isfinite(b_arr))):
        raise ValueError(f"NONFINITE_PRICE [{asset_u}]: NaN or Inf detected in bid_ohlc")

    sp_arr: np.ndarray | None = None
    eff_point: float | None = None
    a_arr: np.ndarray | None = None

    if spread_points is not None:
        sp_raw = np.asarray(spread_points)
        if sp_raw.ndim != 1 or sp_raw.shape != (ts_arr.size,):
            raise ValueError(
                f"INVALID_SPREAD_SHAPE [{asset_u}]: spread_points shape {sp_raw.shape} != ({ts_arr.size},)"
            )
        if sp_raw.dtype == np.bool_ or not (
            np.issubdtype(sp_raw.dtype, np.floating) or np.issubdtype(sp_raw.dtype, np.integer)
        ):
            raise ValueError(f"INVALID_SPREAD_DTYPE [{asset_u}]: spread_points dtype={sp_raw.dtype} rejected")
        sp_arr = sp_raw.astype(np.float64, copy=True)
        if not bool(np.all(np.isfinite(sp_arr))):
            raise ValueError(f"NONFINITE_SPREAD [{asset_u}]: NaN or Inf in spread_points")
        if bool(np.any(sp_arr < 0.0)):
            raise ValueError(f"NEGATIVE_SPREAD [{asset_u}]: negative spread_points detected")

    if point_size is not None:
        eff_point = _parse_strict_float(point_size, label=f"{asset_u}.point_size")
        if eff_point <= 0.0:
            raise ValueError(f"INVALID_POINT_SIZE [{asset_u}]: point_size must be > 0, got {eff_point}")

    if ask_ohlc is not None:
        a_raw = np.asarray(ask_ohlc)
        if a_raw.ndim != 2 or a_raw.shape != (ts_arr.size, 4):
            raise ValueError(
                f"INVALID_OHLC_SHAPE [{asset_u}]: ask_ohlc shape {a_raw.shape} != ({ts_arr.size}, 4)"
            )
        if a_raw.dtype == np.bool_ or not (
            np.issubdtype(a_raw.dtype, np.floating) or np.issubdtype(a_raw.dtype, np.integer)
        ):
            raise ValueError(f"INVALID_OHLC_DTYPE [{asset_u}]: ask_ohlc dtype={a_raw.dtype} rejected")
        a_arr = a_raw.astype(np.float64, copy=True)
        if not bool(np.all(np.isfinite(a_arr))):
            raise ValueError(f"NONFINITE_PRICE [{asset_u}]: NaN or Inf detected in ask_ohlc")
    elif source_provenance == sam.PROVENANCE_FTMO_BID_PLUS_SPREAD:
        if sp_arr is None or eff_point is None:
            raise ValueError(f"PROVENANCE_MISSING_SPREAD [{asset_u}]: spread_points and point_size required")
        a_arr = b_arr + (sp_arr[:, None] * eff_point)

    # Positive price guard (explicit Apr-2020 USOIL quarantine option, fail-closed by default)
    nonpos_mask = np.any(b_arr <= 0.0, axis=1)
    if a_arr is not None:
        nonpos_mask = nonpos_mask | np.any(a_arr <= 0.0, axis=1)
    nonpos_detected = int(np.sum(nonpos_mask))
    nonpos_filtered = 0
    if nonpos_detected > 0:
        bad_idx = np.flatnonzero(nonpos_mask)
        first_utc = _utc_iso(int(ts_arr[bad_idx[0]]))
        last_utc = _utc_iso(int(ts_arr[bad_idx[-1]]))
        raw_min = float(np.min(b_arr[nonpos_mask]))
        if a_arr is not None:
            raw_min = min(raw_min, float(np.min(a_arr[nonpos_mask])))
        if not filter_nonpositive:
            raise ValueError(
                f"NONPOSITIVE_PRICE_ANOMALY [{asset_u}]: detected {nonpos_detected} bar(s) with price <= 0.0 "
                f"(min_price={raw_min}, window={first_utc}..{last_utc})"
            )
        keep_mask = ~nonpos_mask
        ts_arr = ts_arr[keep_mask]
        b_arr = b_arr[keep_mask]
        if a_arr is not None:
            a_arr = a_arr[keep_mask]
        if sp_arr is not None:
            sp_arr = sp_arr[keep_mask]
        nonpos_filtered = nonpos_detected
        if ts_arr.size == 0:
            raise ValueError(f"ALL_BARS_FILTERED [{asset_u}]: 0 bars remain after filter_nonpositive")

    # Strict OHLC ordering: high >= max(open, close) >= min(open, close) >= low
    b_max_oc = np.maximum(b_arr[:, 0], b_arr[:, 3])
    b_min_oc = np.minimum(b_arr[:, 0], b_arr[:, 3])
    if bool(np.any(b_arr[:, 1] < b_max_oc)) or bool(np.any(b_arr[:, 2] > b_min_oc)):
        bad_row = int(np.flatnonzero((b_arr[:, 1] < b_max_oc) | (b_arr[:, 2] > b_min_oc))[0])
        raise ValueError(
            f"OHLC_INTEGRITY_VIOLATION [{asset_u} bid row={bad_row} ts={_utc_iso(int(ts_arr[bad_row]))}]: "
            f"expected high >= max(open,close) >= min(open,close) >= low, got {b_arr[bad_row].tolist()}"
        )

    if a_arr is not None:
        a_max_oc = np.maximum(a_arr[:, 0], a_arr[:, 3])
        a_min_oc = np.minimum(a_arr[:, 0], a_arr[:, 3])
        if bool(np.any(a_arr[:, 1] < a_max_oc)) or bool(np.any(a_arr[:, 2] > a_min_oc)):
            bad_row = int(np.flatnonzero((a_arr[:, 1] < a_max_oc) | (a_arr[:, 2] > a_min_oc))[0])
            raise ValueError(
                f"OHLC_INTEGRITY_VIOLATION [{asset_u} ask row={bad_row} ts={_utc_iso(int(ts_arr[bad_row]))}]: "
                f"got {a_arr[bad_row].tolist()}"
            )
        if bool(np.any(a_arr < b_arr)):
            bad_row = int(np.flatnonzero(np.any(a_arr < b_arr, axis=1))[0])
            raise ValueError(
                f"CROSSED_QUOTE_VIOLATION [{asset_u} row={bad_row} ts={_utc_iso(int(ts_arr[bad_row]))}]: "
                "ask < bid detected"
            )

    min_px = float(np.min(b_arr))
    max_px = float(np.max(b_arr))
    if a_arr is not None:
        min_px = min(min_px, float(np.min(a_arr)))
        max_px = max(max_px, float(np.max(a_arr)))

    return ValidatedM1Batch(
        asset=asset_u,
        tier=tier,
        source_provenance=source_provenance,
        times_sec=ts_arr,
        bid_ohlc=b_arr,
        ask_ohlc=a_arr,
        spread_points=sp_arr,
        point_size=eff_point,
        bar_count=int(ts_arr.size),
        min_ts_sec=int(ts_arr[0]),
        max_ts_sec=int(ts_arr[-1]),
        min_ts_utc=_utc_iso(int(ts_arr[0])),
        max_ts_utc=_utc_iso(int(ts_arr[-1])),
        min_price=round(min_px, 6),
        max_price=round(max_px, 6),
        nonpositive_detected=nonpos_detected,
        nonpositive_filtered=nonpos_filtered,
        has_true_bid_ask=has_true_bid_ask,
        native_ask=native_ask,
        ask_columns_present=ask_columns_present,
        waf_bypass_attempted=False,
        holdout_rows_analysed=0,
        source_detail=source_detail or f"{tier.lower()}:{source_provenance.lower()}",
    )


# ==============================================================================
# Tier 1: QuantDataManager (QDM) Direct CLI Adapter (Zero psycopg / trader import)
# ==============================================================================


def discover_qdm_executable(
    qdm_home: str | Path | None = None,
    *,
    repo_root: Path = ROOT,
    env: Mapping[str, str] | None = None,
) -> Path | None:
    """Dynamically locate local `qdmcli.exe` via explicit path, `TW_V2_QDM_HOME`, or project scan."""
    env_map = os.environ if env is None else env
    candidates: list[Path] = []

    if qdm_home is not None:
        p = Path(qdm_home)
        candidates.append(p if p.name.lower() == "qdmcli.exe" else p / "qdmcli.exe")

    env_home = str(env_map.get("TW_V2_QDM_HOME", "") or "").strip()
    if env_home:
        ep = Path(env_home)
        candidates.append(ep if ep.name.lower() == "qdmcli.exe" else ep / "qdmcli.exe")

    candidates.append(repo_root / ".runtime" / "quantdatamanager" / "qdmcli.exe")
    candidates.append(
        repo_root / "projects" / "trader" / "foundation_v2" / ".runtime" / "quantdatamanager" / "qdmcli.exe"
    )

    projects_dir = repo_root / "projects"
    if projects_dir.is_dir():
        for found in sorted(projects_dir.glob("*/foundation_v2/.runtime/quantdatamanager/qdmcli.exe")):
            candidates.append(found)

    seen: set[Path] = set()
    for cand in candidates:
        try:
            resolved = cand.resolve()
        except OSError:
            continue
        if resolved in seen:
            continue
        seen.add(resolved)
        if resolved.is_file():
            return resolved

    which_hit = shutil.which("qdmcli.exe") or shutil.which("qdmcli")
    if which_hit:
        wp = Path(which_hit).resolve()
        if wp.is_file():
            return wp
    return None


def validate_qdm_argv(argv: Sequence[str], *, require_export_only: bool = False) -> list[str]:
    """Fail-closed guard on `qdmcli.exe` command arguments.

    Enforces `projects/trader/docs/quantdatamanager.md` invariants:
      - NEVER allows `broker=...` (especially `broker=SQ Default` with whitespace, which causes
        QDM CLI 125.2692 to exit 0 without creating/exporting the symbol).
      - When `require_export_only=True`, requires `action=export`, forbids `action=update`,
        and verifies `dateto <= 2024.12.31` (fail-closed `HoldoutLockError`).
    """
    if not argv:
        raise ValueError("QDM_INVALID_ARGV: command argv must not be empty")
    tokens = [str(tok) for tok in argv]

    for tok in tokens[1:]:
        low = tok.strip().lower()
        if low.startswith("broker=") or "broker=sq default" in low:
            raise ValueError(
                f"QDM_FORBIDDEN_BROKER_ARG: never pass {tok!r} to qdmcli.exe "
                "(QDM 125.2692 silently fails with whitespace broker arguments)"
            )

    if require_export_only:
        if "action=update" in [t.strip().lower() for t in tokens[1:]]:
            raise ValueError("QDM_FORBIDDEN_ACTION: action=update is disallowed inside export command builder")
        if "action=export" not in [t.strip().lower() for t in tokens[1:]]:
            raise ValueError("QDM_EXPORT_REQUIRED: export command must explicitly include action=export")
        date_to_vals = [t.split("=", 1)[1] for t in tokens[1:] if t.lower().startswith("dateto=")]
        date_from_vals = [t.split("=", 1)[1] for t in tokens[1:] if t.lower().startswith("datefrom=")]
        if not date_to_vals:
            raise HoldoutLockError("QDM_MISSING_DATETO: export command must set dateto <= 2024.12.31")
        for dt_val in date_to_vals:
            _parse_date_to_dot(dt_val, label="qdm_argv.dateto")
        for df_val in date_from_vals:
            _parse_date_to_dot(df_val, label="qdm_argv.datefrom")

    return tokens


def build_qdm_export_command(
    executable: str | Path,
    *,
    qdm_symbol: str,
    output_dir: str | Path,
    date_from: str = DEV_START_QDM_DATE,
    date_to: str = HOLDOUT_CUTOFF_QDM_DATE,
    timeframe: str = "M1",
    timezone: str = "UTC",
    extra_args: Sequence[str] = (),
) -> list[str]:
    """Build a strictly validated `qdmcli.exe -data action=export` command (`<= 2024.12.31`)."""
    sym_clean = str(qdm_symbol or "").strip()
    if not sym_clean or _QDM_SYMBOL_RE.fullmatch(sym_clean) is None:
        raise ValueError(f"QDM_INVALID_SYMBOL: {qdm_symbol!r}")
    if timeframe.strip().upper() != "M1":
        raise ValueError(f"QDM_INVALID_TIMEFRAME: expected M1, got {timeframe!r}")
    if timezone.strip().upper() != "UTC":
        raise ValueError(f"QDM_INVALID_TIMEZONE: expected UTC, got {timezone!r}")

    d_from, d_from_dot = _parse_date_to_dot(date_from, label="qdm_export.date_from")
    d_to, d_to_dot = _parse_date_to_dot(date_to, label="qdm_export.date_to")
    if d_from > d_to:
        raise ValueError(f"QDM_INVALID_DATE_RANGE: date_from={d_from_dot} > date_to={d_to_dot}")

    out_posix = Path(output_dir).resolve().as_posix()
    argv = [
        str(Path(executable)),
        "-data",
        "action=export",
        f"symbols={sym_clean}",
        "timeframe=M1",
        "timezone=UTC",
        f"datefrom={d_from_dot}",
        f"dateto={d_to_dot}",
        f"outputdir={out_posix}",
        "format=Custom",
        "cIncludeHeader=true",
        f"cHeader={QDM_CUSTOM_HEADER}",
        f"cFormat={QDM_CUSTOM_FORMAT}",
        *[str(a) for a in extra_args],
    ]
    return validate_qdm_argv(argv, require_export_only=True)


def build_qdm_symbol_list_command(executable: str | Path) -> list[str]:
    """Build read-only `qdmcli.exe -symbol action=list` argv."""
    return validate_qdm_argv([str(Path(executable)), "-symbol", "action=list"], require_export_only=False)


def _classify_qdm_cli_error(output: str) -> str | None:
    low = output.lower()
    if "another instance of quantdatamanager is running" in low:
        return "qdm_busy"
    if "missing license" in low or "invalid license" in low or "license expired" in low:
        return "qdm_license_required"
    if re.search(r"(?im)^.*(?:\berror\b|exception|update failed|export failed|unknown symbol).*$", output):
        return "qdm_command_failed"
    return None


@contextlib.contextmanager
def _single_process_file_lock(lock_path: Path) -> Iterator[None]:
    """Fail-closed single-process file lock for QDM CLI (no concurrent QDM invocations)."""
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    fd: int | None = None
    acquired = False
    try:
        try:
            fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            acquired = True
        except FileExistsError as exc:
            raise QdmBusyError(f"QDM single-process lock already held: {lock_path}") from exc
        payload = json.dumps({"pid": os.getpid(), "utc": datetime.now(UTC).isoformat()}) + "\n"
        os.write(fd, payload.encode("utf-8"))
        os.close(fd)
        fd = None
        yield
    finally:
        if fd is not None:
            with contextlib.suppress(OSError):
                os.close(fd)
        if acquired:
            with contextlib.suppress(OSError):
                lock_path.unlink(missing_ok=True)


def read_qdm_catalog_codes(qdm_home: Path) -> dict[str, dict[str, str]]:
    """Read-only parser for installed `dukascopy.csv` inside QDM distribution (no CLI spawn)."""
    catalog_file = qdm_home / QDM_CATALOG_REL_PATH
    if not catalog_file.is_file():
        return {}
    raw = catalog_file.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("cp1252", errors="replace")
    out: dict[str, dict[str, str]] = {}
    for row in csv.reader(io.StringIO(text), delimiter=";"):
        if len(row) < 6:
            continue
        code = row[0].strip().upper()
        if not code:
            continue
        out[code] = {
            "code": code,
            "name": row[1].strip(),
            "category": row[2].strip(),
            "group": row[3].strip(),
            "tick_start": row[4].strip(),
            "minute_start": row[5].strip(),
        }
    return out


def parse_qdm_symbol_list_output(output: str) -> list[dict[str, str]]:
    """Parse stdout from `qdmcli.exe -symbol action=list`."""
    if QDM_LIST_HEADER not in output:
        raise HarvesterError("QDM_LIST_PARSE_ERROR: expected symbol list header missing from stdout")
    table = output[output.index(QDM_LIST_HEADER) :].split("Data listed.", 1)[0]
    return [dict(row) for row in csv.DictReader(io.StringIO(table))]


def parse_qdm_m1_csv(
    csv_path: Path,
    *,
    asset: str,
    filter_nonpositive: bool = False,
) -> ValidatedM1Batch:
    """Parse a QDM M1 export CSV strictly as `QDM_PROVIDER_DEFAULT_SINGLE_SIDE` (< 2025-01-01)."""
    asset_u = _normalize_symbol(asset)
    fpath = Path(csv_path)
    if not fpath.is_file():
        raise FileNotFoundError(f"QDM exported CSV not found: {fpath}")

    raw_text = fpath.read_text(encoding="utf-8-sig")
    ts_list: list[int] = []
    ohlc_list: list[tuple[float, float, float, float]] = []

    reader = csv.reader(io.StringIO(raw_text))
    for row_idx, row in enumerate(reader):
        if not row or all(not c.strip() for c in row):
            continue
        first_cell = row[0].strip().lower()
        if row_idx == 0 and (first_cell in ("date", "datetime", "time") or not first_cell[0].isdigit()):
            continue

        if len(row) >= 6:
            d_match = _DOT_DATE_RE.fullmatch(row[0].strip())
            t_match = _HMS_TIME_RE.fullmatch(row[1].strip())
            if d_match is None or t_match is None:
                raise ValueError(f"QDM_CSV_MALFORMED_DATETIME [{asset_u} row={row_idx}]: {row[:2]!r}")
            year, month, day = int(d_match.group(1)), int(d_match.group(2)), int(d_match.group(3))
            hour, minute = int(t_match.group(1)), int(t_match.group(2))
            sec = int(t_match.group(3)) if t_match.group(3) is not None else 0
            try:
                dt = datetime(year, month, day, hour, minute, sec, tzinfo=UTC)
            except ValueError as exc:
                raise ValueError(f"QDM_CSV_INVALID_CALENDAR [{asset_u} row={row_idx}]: {row[:2]!r}") from exc
            o_idx = 2
        elif len(row) >= 5:
            dt_match = _ISO_DT_RE.fullmatch(row[0].strip())
            if dt_match is None:
                raise ValueError(f"QDM_CSV_MALFORMED_DATETIME [{asset_u} row={row_idx}]: {row[0]!r}")
            year, month, day = int(dt_match.group(1)), int(dt_match.group(2)), int(dt_match.group(3))
            hour, minute = int(dt_match.group(4)), int(dt_match.group(5))
            sec = int(dt_match.group(6)) if dt_match.group(6) is not None else 0
            try:
                dt = datetime(year, month, day, hour, minute, sec, tzinfo=UTC)
            except ValueError as exc:
                raise ValueError(f"QDM_CSV_INVALID_CALENDAR [{asset_u} row={row_idx}]: {row[0]!r}") from exc
            o_idx = 1
        else:
            raise ValueError(f"QDM_CSV_MALFORMED_ROW [{asset_u} row={row_idx}]: expected >=5 cols, got {len(row)}")

        ts_sec = int(dt.timestamp())
        if ts_sec >= HOLDOUT_STOP_UTC_SEC:
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION [QDM {asset_u} row={row_idx}]: ts_utc={dt.isoformat()} >= 2025-01-01T00:00:00Z"
            )
        o_v = _parse_strict_float(row[o_idx], label=f"qdm.{asset_u}[{row_idx}].open")
        h_v = _parse_strict_float(row[o_idx + 1], label=f"qdm.{asset_u}[{row_idx}].high")
        l_v = _parse_strict_float(row[o_idx + 2], label=f"qdm.{asset_u}[{row_idx}].low")
        c_v = _parse_strict_float(row[o_idx + 3], label=f"qdm.{asset_u}[{row_idx}].close")
        ts_list.append(ts_sec)
        ohlc_list.append((o_v, h_v, l_v, c_v))

    if not ts_list:
        raise ValueError(f"QDM_CSV_EMPTY [{asset_u}]: no M1 rows found in {fpath}")

    return validate_m1_bars(
        asset_u,
        np.asarray(ts_list, dtype=np.int64),
        np.asarray(ohlc_list, dtype=np.float64),
        tier=TIER_1_QDM_CLI,
        source_provenance=sam.PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        ask_ohlc=None,
        filter_nonpositive=filter_nonpositive,
        waf_bypass_attempted=False,
        source_detail=f"qdm-cli-export:{fpath.name}",
    )


class QdmCliAdapter:
    """Direct `qdmcli.exe` subprocess adapter (no `trading_workspace_v2` / `psycopg` import)."""

    def __init__(
        self,
        qdm_home: str | Path | None = None,
        *,
        lock_path: Path = DEFAULT_QDM_LOCK_PATH,
        timeout_sec: int = DEFAULT_QDM_TIMEOUT_SEC,
        repo_root: Path = ROOT,
    ) -> None:
        self.executable: Path | None = discover_qdm_executable(qdm_home, repo_root=repo_root)
        self.home: Path | None = self.executable.parent if self.executable is not None else None
        self.lock_path = Path(lock_path)
        self.timeout_sec = int(timeout_sec)

    @property
    def available(self) -> bool:
        return self.executable is not None and self.executable.is_file()

    def run_command(
        self,
        argv: Sequence[str],
        *,
        require_export_only: bool = False,
        timeout_sec: int | None = None,
    ) -> str:
        """Execute `qdmcli.exe` directly via `subprocess.run(..., creationflags=_NO_WINDOW_FLAGS)`."""
        if not self.available or self.executable is None or self.home is None:
            raise QdmUnavailableError("qdmcli.exe not found (set TW_V2_QDM_HOME or install local QDM)")
        checked_argv = validate_qdm_argv(argv, require_export_only=require_export_only)
        eff_timeout = self.timeout_sec if timeout_sec is None else int(timeout_sec)
        with _single_process_file_lock(self.lock_path):
            proc = subprocess.run(
                checked_argv,
                cwd=str(self.home),
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=eff_timeout,
                creationflags=_NO_WINDOW_FLAGS,
            )
        stdout = str(proc.stdout or "")
        stderr = str(proc.stderr or "")
        combined = stdout + ("\n" + stderr if stderr else "")
        err = _classify_qdm_cli_error(combined)
        if err == "qdm_busy":
            raise QdmBusyError("Another instance of QuantDataManager is running")
        if err == "qdm_license_required":
            raise QdmLicenseError("QuantDataManager local license missing or expired")
        if err is not None or proc.returncode != 0 or "Exit app - ok" not in stdout:
            raise HarvesterError(f"QDM CLI failed (rc={proc.returncode}, err={err}): {combined[-400:]}")
        return stdout

    def list_cached_symbols(self, *, timeout_sec: int = 45) -> list[dict[str, str]]:
        if not self.available or self.executable is None:
            raise QdmUnavailableError("qdmcli.exe not found")
        argv = build_qdm_symbol_list_command(self.executable)
        stdout = self.run_command(argv, require_export_only=False, timeout_sec=timeout_sec)
        return parse_qdm_symbol_list_output(stdout)

    def export_symbol_m1(
        self,
        spec: SymbolHarvestSpec,
        output_dir: Path,
        *,
        date_from: str = DEV_START_QDM_DATE,
        date_to: str = HOLDOUT_CUTOFF_QDM_DATE,
        qdm_symbol_override: str | None = None,
        filter_nonpositive: bool = False,
    ) -> ValidatedM1Batch:
        """Export M1 CSV via `qdmcli.exe action=export <= 2024.12.31` and validate strictly."""
        if not self.available or self.executable is None:
            raise QdmUnavailableError("qdmcli.exe not found")
        target_dir = Path(output_dir)
        target_dir.mkdir(parents=True, exist_ok=True)
        qdm_sym = qdm_symbol_override or spec.qdm_symbol_name
        argv = build_qdm_export_command(
            self.executable,
            qdm_symbol=qdm_sym,
            output_dir=target_dir,
            date_from=date_from,
            date_to=date_to,
        )
        self.run_command(argv, require_export_only=True)

        csv_files = sorted(p for p in target_dir.glob("*.csv") if p.is_file())
        if not csv_files:
            raise HarvesterError(
                f"QDM_EXPORT_NO_CSV [{spec.canonical_symbol}]: qdmcli exited ok but produced no CSV in {target_dir}"
            )
        # Prefer exact symbol match if multiple CSVs exist
        chosen = next(
            (
                p
                for p in csv_files
                if qdm_sym.lower() in p.name.lower() or spec.qdm_instrument_code.lower() in p.name.lower()
            ),
            csv_files[0],
        )
        return parse_qdm_m1_csv(chosen, asset=spec.canonical_symbol, filter_nonpositive=filter_nonpositive)


# ==============================================================================
# Tier 2: FTMO-Demo Portable M1 Adapter (Lazy MT5 import, [MT5 LOCK] safe)
# ==============================================================================


def parse_ftmo_mt5_rates(
    rates: Any,
    *,
    asset: str,
    point_size: float,
    broker_utc_offset_hours: float = 0.0,
    filter_nonpositive: bool = False,
    source_detail: str = "ftmo-demo-portable-m1-rates",
) -> ValidatedM1Batch:
    """Convert MT5 `copy_rates_range` structured bars into validated `FTMO_BID_PLUS_SPREAD` batch."""
    asset_u = _normalize_symbol(asset)
    eff_point = _parse_strict_float(point_size, label=f"ftmo.{asset_u}.point_size")
    if eff_point <= 0.0:
        raise ValueError(f"INVALID_POINT_SIZE [FTMO {asset_u}]: {eff_point}")
    offset_sec = int(round(_parse_strict_float(broker_utc_offset_hours, label="broker_utc_offset_hours") * 3600.0))

    if rates is None:
        raise ValueError(f"FTMO_RATES_EMPTY [{asset_u}]: rates is None")

    ts_list: list[int] = []
    ohlc_list: list[tuple[float, float, float, float]] = []
    spread_list: list[float] = []

    if isinstance(rates, np.ndarray) and rates.dtype.names:
        required_cols = ("time", "open", "high", "low", "close", "spread")
        missing_cols = [c for c in required_cols if c not in rates.dtype.names]
        if missing_cols:
            raise ValueError(f"FTMO_RATES_MISSING_COLS [{asset_u}]: missing {missing_cols}")
        if rates.size == 0:
            raise ValueError(f"FTMO_RATES_EMPTY [{asset_u}]: 0 rows returned")
        ts_arr = np.asarray(rates["time"], dtype=np.int64) - np.int64(offset_sec)
        bid_arr = np.column_stack(
            [
                np.asarray(rates["open"], dtype=np.float64),
                np.asarray(rates["high"], dtype=np.float64),
                np.asarray(rates["low"], dtype=np.float64),
                np.asarray(rates["close"], dtype=np.float64),
            ]
        )
        sp_arr = np.asarray(rates["spread"], dtype=np.float64)
    else:
        rows = list(rates)
        if not rows:
            raise ValueError(f"FTMO_RATES_EMPTY [{asset_u}]: 0 rows returned")
        for idx, rec in enumerate(rows):
            if not isinstance(rec, Mapping):
                raise ValueError(f"FTMO_RATES_MALFORMED [{asset_u} row={idx}]: expected Mapping or structured array")
            raw_t = rec.get("time")
            if isinstance(raw_t, bool) or not isinstance(raw_t, (int, np.integer)):
                raise HoldoutLockError(f"FTMO_INVALID_TIME [{asset_u} row={idx}]: {raw_t!r}")
            t_utc = int(raw_t) - offset_sec
            if t_utc >= HOLDOUT_STOP_UTC_SEC:
                raise HoldoutLockError(
                    f"HOLDOUT_CONTAMINATION [FTMO {asset_u} row={idx}]: ts_utc={_utc_iso(t_utc)} >= 2025-01-01"
                )
            ts_list.append(t_utc)
            ohlc_list.append(
                (
                    _parse_strict_float(rec.get("open"), label=f"ftmo.{asset_u}[{idx}].open"),
                    _parse_strict_float(rec.get("high"), label=f"ftmo.{asset_u}[{idx}].high"),
                    _parse_strict_float(rec.get("low"), label=f"ftmo.{asset_u}[{idx}].low"),
                    _parse_strict_float(rec.get("close"), label=f"ftmo.{asset_u}[{idx}].close"),
                )
            )
            spread_list.append(_parse_strict_float(rec.get("spread"), label=f"ftmo.{asset_u}[{idx}].spread"))
        ts_arr = np.asarray(ts_list, dtype=np.int64)
        bid_arr = np.asarray(ohlc_list, dtype=np.float64)
        sp_arr = np.asarray(spread_list, dtype=np.float64)

    return validate_m1_bars(
        asset_u,
        ts_arr,
        bid_arr,
        tier=TIER_2_FTMO_DEMO,
        source_provenance=sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
        ask_ohlc=None,
        spread_points=sp_arr,
        point_size=eff_point,
        filter_nonpositive=filter_nonpositive,
        waf_bypass_attempted=False,
        source_detail=source_detail,
    )


def parse_ftmo_m1_csv(
    csv_path: Path,
    *,
    asset: str,
    point_size: float,
    broker_utc_offset_hours: float = 0.0,
    filter_nonpositive: bool = False,
) -> ValidatedM1Batch:
    """Parse an already-exported FTMO-Demo M1 CSV (`time_utc|time,open,high,low,close,spread`)."""
    asset_u = _normalize_symbol(asset)
    fpath = Path(csv_path)
    if not fpath.is_file():
        raise FileNotFoundError(f"FTMO exported CSV not found: {fpath}")
    text = fpath.read_text(encoding="utf-8-sig")
    rows_out: list[dict[str, Any]] = []
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise ValueError(f"FTMO_CSV_MISSING_HEADER [{asset_u}]: {fpath}")
    lower_map = {k.strip().lower(): k for k in reader.fieldnames if k}
    time_col = lower_map.get("time_utc") or lower_map.get("time") or lower_map.get("timestamp")
    for req in ("open", "high", "low", "close", "spread"):
        if req not in lower_map:
            raise ValueError(f"FTMO_CSV_MISSING_COL [{asset_u}]: missing {req!r} in {fpath}")
    if time_col is None:
        raise ValueError(f"FTMO_CSV_MISSING_TIME_COL [{asset_u}]: expected time_utc/time/timestamp")

    for idx, row in enumerate(reader):
        raw_t = str(row[time_col] or "").strip()
        if raw_t.isdigit():
            t_sec = int(raw_t)
        else:
            dt_match = _ISO_DT_RE.fullmatch(raw_t)
            if dt_match is None:
                raise HoldoutLockError(f"FTMO_CSV_BAD_TIME [{asset_u} row={idx}]: {raw_t!r}")
            sec_val = int(dt_match.group(6)) if dt_match.group(6) is not None else 0
            t_sec = int(
                datetime(
                    int(dt_match.group(1)),
                    int(dt_match.group(2)),
                    int(dt_match.group(3)),
                    int(dt_match.group(4)),
                    int(dt_match.group(5)),
                    sec_val,
                    tzinfo=UTC,
                ).timestamp()
            )
        rows_out.append(
            {
                "time": t_sec,
                "open": row[lower_map["open"]],
                "high": row[lower_map["high"]],
                "low": row[lower_map["low"]],
                "close": row[lower_map["close"]],
                "spread": row[lower_map["spread"]],
            }
        )
    return parse_ftmo_mt5_rates(
        rows_out,
        asset=asset_u,
        point_size=point_size,
        broker_utc_offset_hours=broker_utc_offset_hours,
        filter_nonpositive=filter_nonpositive,
        source_detail=f"ftmo-demo-csv:{fpath.name}",
    )


def parse_ftmo_m1_npz(
    npz_path: Path,
    *,
    asset: str,
    point_size: float,
    min_ts_sec: int = DEV_START_UTC_SEC,
    filter_nonpositive: bool = False,
) -> ValidatedM1Batch:
    """Parse an `.npz` exported by `ftmo_m1_exporter.py` (`ts_utc, open, high, low, close, spread_pts`)."""
    asset_u = _normalize_symbol(asset)
    fpath = Path(npz_path)
    if not fpath.is_file():
        raise FileNotFoundError(f"FTMO exported NPZ not found: {fpath}")
    eff_point = _parse_strict_float(point_size, label=f"ftmo_npz.{asset_u}.point_size")
    if eff_point <= 0.0:
        raise ValueError(f"INVALID_POINT_SIZE [FTMO NPZ {asset_u}]: {eff_point}")

    with np.load(fpath, allow_pickle=False) as z:
        required = ("ts_utc", "open", "high", "low", "close", "spread_pts")
        missing = [k for k in required if k not in z.files]
        if missing:
            raise ValueError(f"FTMO_NPZ_MISSING_KEYS [{asset_u}]: missing {missing} in {fpath.name}")
        ts_all = np.asarray(z["ts_utc"])
        if ts_all.ndim != 1 or ts_all.size == 0:
            raise ValueError(f"FTMO_NPZ_EMPTY [{asset_u}]: empty ts_utc in {fpath.name}")
        if ts_all.dtype == np.bool_ or not np.issubdtype(ts_all.dtype, np.integer):
            raise HoldoutLockError(f"FTMO_NPZ_BAD_TS_DTYPE [{asset_u}]: {ts_all.dtype}")
        ts_i64 = ts_all.astype(np.int64, copy=False)
        # Fail closed on ANY 2025+ Holdout row BEFORE slicing pre-2018 history!
        enforce_pre_holdout_ts(
            ts_i64,
            None,
            HOLDOUT_STOP_UTC_SEC,
            context=f"parse_ftmo_m1_npz:{asset_u}",
            allow_empty=False,
        )
        dev_mask = ts_i64 >= int(min_ts_sec)
        if not bool(np.any(dev_mask)):
            raise ValueError(f"FTMO_NPZ_NO_DEV_ROWS [{asset_u}]: 0 rows >= {_utc_iso(int(min_ts_sec))}")
        ts_dev = ts_i64[dev_mask]
        bid_dev = np.column_stack(
            [
                np.asarray(z["open"], dtype=np.float64)[dev_mask],
                np.asarray(z["high"], dtype=np.float64)[dev_mask],
                np.asarray(z["low"], dtype=np.float64)[dev_mask],
                np.asarray(z["close"], dtype=np.float64)[dev_mask],
            ]
        )
        sp_dev = np.asarray(z["spread_pts"], dtype=np.float64)[dev_mask]

    return validate_m1_bars(
        asset_u,
        ts_dev,
        bid_dev,
        tier=TIER_2_FTMO_DEMO,
        source_provenance=sam.PROVENANCE_FTMO_BID_PLUS_SPREAD,
        ask_ohlc=None,
        spread_points=sp_dev,
        point_size=eff_point,
        filter_nonpositive=filter_nonpositive,
        waf_bypass_attempted=False,
        source_detail=f"ftmo-demo-npz:{fpath.name}",
    )


class FtmoDemoM1Adapter:
    """Tier 2 FTMO-Demo portable M1 adapter with lazy `MetaTrader5` import & `[MT5 LOCK]` guard."""

    def __init__(
        self,
        *,
        terminal_exe: str | Path | None = None,
        expected_server: str = "FTMO-Demo",
        export_dir: Path | None = None,
        delegate_exporter: Callable[..., Any] | None = None,
        broker_utc_offset_hours: float = 0.0,
    ) -> None:
        self.terminal_exe = Path(terminal_exe) if terminal_exe is not None else None
        self.expected_server = str(expected_server)
        self.export_dir = Path(export_dir) if export_dir is not None else None
        self.delegate_exporter = delegate_exporter
        self.broker_utc_offset_hours = float(broker_utc_offset_hours)

    def _validate_portable_terminal_path(self, exe: Path) -> None:
        low = str(exe).lower().replace("\\", "/")
        if (
            "/program files/" in low
            or "/program files (x86)/" in low
            or "d0e8209f77c8cf37ad8bf550e51ff075" in low
        ):
            raise HarvesterError(
                f"FORBIDDEN_PROGRAM_FILES_MT5: refusing to touch Program Files or live terminal {exe}"
            )

    def fetch_symbol_m1(
        self,
        spec: SymbolHarvestSpec,
        *,
        date_from: str = DEV_START_DATE,
        date_to: str = HOLDOUT_CUTOFF_DATE,
        mt5_lock_held: bool = False,
        allow_live_mt5: bool = False,
        mt5_module: Any = None,
        filter_nonpositive: bool = False,
    ) -> ValidatedM1Batch:
        """Fetch M1 bars from FTMO-Demo portable MT5 or pre-exported NPZ/CSV/delegate (`< 2025-01-01`)."""
        d_from, _ = _parse_date_to_dot(date_from, label="ftmo_fetch.date_from")
        d_to, _ = _parse_date_to_dot(date_to, label="ftmo_fetch.date_to")
        if d_from > d_to:
            raise ValueError(f"FTMO_INVALID_DATE_RANGE: {d_from} > {d_to}")

        # Option A: Read pre-exported FTMO M1 NPZ (ftmo_m1_exporter schema) or CSV (zero MT5 launch!)
        if self.export_dir is not None and self.export_dir.is_dir():
            for cand_npz in (
                f"{spec.canonical_symbol}.npz",
                f"{spec.canonical_symbol.lower()}.npz",
                f"{spec.ftmo_symbol}.npz",
                f"{spec.canonical_symbol}_M1.npz",
            ):
                cand = self.export_dir / cand_npz
                if cand.is_file():
                    return parse_ftmo_m1_npz(
                        cand,
                        asset=spec.canonical_symbol,
                        point_size=spec.ftmo_point_size,
                        filter_nonpositive=filter_nonpositive,
                    )
            for cand_name in (
                f"{spec.canonical_symbol}.csv",
                f"{spec.canonical_symbol.lower()}.csv",
                f"{spec.ftmo_symbol}.csv",
                f"{spec.canonical_symbol}_M1.csv",
            ):
                cand = self.export_dir / cand_name
                if cand.is_file():
                    return parse_ftmo_m1_csv(
                        cand,
                        asset=spec.canonical_symbol,
                        point_size=spec.ftmo_point_size,
                        broker_utc_offset_hours=self.broker_utc_offset_hours,
                        filter_nonpositive=filter_nonpositive,
                    )

        # Option B: Delegate cleanly to external `[MT5 LOCK]` exporter (e.g., Wave 2A / ftmo_m1_exporter)
        if self.delegate_exporter is not None:
            if not mt5_lock_held:
                raise Mt5LockRequiredError(
                    f"MT5_LOCK_REQUIRED [{spec.canonical_symbol}]: delegate_exporter requires mt5_lock_held=True"
                )
            delegated = self.delegate_exporter(
                symbol=spec.canonical_symbol,
                ftmo_symbol=spec.ftmo_symbol,
                date_from=d_from.isoformat(),
                date_to=d_to.isoformat(),
            )
            if isinstance(delegated, ValidatedM1Batch):
                enforce_pre_holdout_ts(
                    delegated.times_sec,
                    DEV_START_UTC_SEC,
                    HOLDOUT_STOP_UTC_SEC,
                    context=f"ftmo_delegate:{spec.canonical_symbol}",
                )
                if delegated.source_provenance != sam.PROVENANCE_FTMO_BID_PLUS_SPREAD:
                    raise ValueError(
                        f"FTMO_DELEGATE_PROVENANCE_MISMATCH: expected FTMO_BID_PLUS_SPREAD, "
                        f"got {delegated.source_provenance!r}"
                    )
                return delegated
            return parse_ftmo_mt5_rates(
                delegated,
                asset=spec.canonical_symbol,
                point_size=spec.ftmo_point_size,
                broker_utc_offset_hours=self.broker_utc_offset_hours,
                filter_nonpositive=filter_nonpositive,
                source_detail="ftmo-demo-delegated-exporter",
            )

        # Option C: Direct lazy MetaTrader5 call — strictly gated by `[MT5 LOCK]` + `allow_live_mt5`
        if mt5_module is None:
            if not mt5_lock_held or not allow_live_mt5:
                raise Mt5LockRequiredError(
                    f"MT5_LOCK_REQUIRED [{spec.canonical_symbol}]: live MT5 portable access blocked "
                    "(requires mt5_lock_held=True and allow_live_mt5=True)"
                )
            if self.terminal_exe is None:
                raise HarvesterError("FTMO_TERMINAL_PATH_REQUIRED: portable terminal64.exe path not configured")
            self._validate_portable_terminal_path(self.terminal_exe)
            import MetaTrader5 as mt5  # Lazy import: never imported at module load / CI
        else:
            if not mt5_lock_held:
                raise Mt5LockRequiredError(
                    f"MT5_LOCK_REQUIRED [{spec.canonical_symbol}]: mt5_lock_held=True required even for injected mt5"
                )
            if self.terminal_exe is not None:
                self._validate_portable_terminal_path(self.terminal_exe)
            mt5 = mt5_module

        init_kwargs: dict[str, Any] = {"portable": True}
        if self.terminal_exe is not None:
            init_kwargs["path"] = str(self.terminal_exe)

        if not mt5.initialize(**init_kwargs):
            raise HarvesterError(f"FTMO_MT5_INIT_FAILED: {mt5.last_error()}")

        try:
            acct = mt5.account_info()
            if acct is None:
                raise HarvesterError("FTMO_MT5_ACCOUNT_INFO_NONE")
            demo_mode = getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)
            if getattr(acct, "trade_mode", -1) != demo_mode:
                raise HarvesterError(
                    f"FTMO_NON_DEMO_BLOCKED: refusing non-demo account trade_mode={getattr(acct, 'trade_mode', None)!r}"
                )
            server_name = str(getattr(acct, "server", "") or "")
            if self.expected_server and server_name != self.expected_server:
                raise HarvesterError(
                    f"FTMO_SERVER_MISMATCH: expected {self.expected_server!r}, got {server_name!r}"
                )

            mt5.symbol_select(spec.ftmo_symbol, True)
            s_info = mt5.symbol_info(spec.ftmo_symbol)
            if s_info is None:
                raise HarvesterError(f"FTMO_SYMBOL_UNAVAILABLE: {spec.ftmo_symbol!r}")
            eff_point = float(getattr(s_info, "point", spec.ftmo_point_size) or spec.ftmo_point_size)

            # Strictly bounded < 2025-01-01T00:00:00Z (last valid M1 bar is 2024-12-31T23:59:00Z)
            dt_from_utc = datetime(d_from.year, d_from.month, d_from.day, 0, 0, 0, tzinfo=UTC)
            dt_to_utc = datetime(d_to.year, d_to.month, d_to.day, 23, 59, 0, tzinfo=UTC)
            enforce_pre_holdout_ts(
                [int(dt_from_utc.timestamp()), int(dt_to_utc.timestamp())],
                DEV_START_UTC_SEC,
                HOLDOUT_STOP_UTC_SEC,
                context=f"ftmo_copy_rates_range:{spec.canonical_symbol}",
            )
            tf_m1 = getattr(mt5, "TIMEFRAME_M1", 1)
            rates = mt5.copy_rates_range(spec.ftmo_symbol, tf_m1, dt_from_utc, dt_to_utc)
            return parse_ftmo_mt5_rates(
                rates,
                asset=spec.canonical_symbol,
                point_size=eff_point,
                broker_utc_offset_hours=self.broker_utc_offset_hours,
                filter_nonpositive=filter_nonpositive,
                source_detail=f"ftmo-demo-portable:{spec.ftmo_symbol}",
            )
        finally:
            mt5.shutdown()


# ==============================================================================
# Tier 3: HistData / TrueFX Compliant Free FX M1 CSV/ZIP Parser
# ==============================================================================


def _parse_histdata_timestamp_utc(row: Sequence[str], *, source_timezone: str, label: str) -> tuple[int, int]:
    """Parse HistData/TrueFX row timestamp -> `(ts_utc_sec, ohlc_start_col_idx)`."""
    tz_mode = str(source_timezone or "UTC").strip().upper()
    if tz_mode == "UTC":
        tz_shift_sec = 0
    elif tz_mode == "EST_FIXED":
        # HistData.com Generic ASCII uses fixed EST (UTC-5, zero DST adjustment) -> add +5h for UTC
        tz_shift_sec = 5 * 3600
    else:
        raise ValueError(f"HISTDATA_UNSUPPORTED_TIMEZONE [{label}]: expected UTC or EST_FIXED, got {source_timezone!r}")

    c0 = row[0].strip()
    m_compact = _COMPACT_DT_RE.fullmatch(c0)
    if m_compact is not None:
        sec_v = int(m_compact.group(6)) if m_compact.group(6) is not None else 0
        dt_local = datetime(
            int(m_compact.group(1)),
            int(m_compact.group(2)),
            int(m_compact.group(3)),
            int(m_compact.group(4)),
            int(m_compact.group(5)),
            sec_v,
            tzinfo=UTC,
        )
        ts_utc = int((dt_local + timedelta(seconds=tz_shift_sec)).timestamp())
        return ts_utc, 1

    m_iso = _ISO_DT_RE.fullmatch(c0)
    if m_iso is not None:
        sec_v = int(m_iso.group(6)) if m_iso.group(6) is not None else 0
        dt_local = datetime(
            int(m_iso.group(1)),
            int(m_iso.group(2)),
            int(m_iso.group(3)),
            int(m_iso.group(4)),
            int(m_iso.group(5)),
            sec_v,
            tzinfo=UTC,
        )
        ts_utc = int((dt_local + timedelta(seconds=tz_shift_sec)).timestamp())
        return ts_utc, 1

    if len(row) >= 6:
        m_d = _DOT_DATE_RE.fullmatch(c0)
        m_t = _HMS_TIME_RE.fullmatch(row[1].strip())
        if m_d is not None and m_t is not None:
            sec_v = int(m_t.group(3)) if m_t.group(3) is not None else 0
            dt_local = datetime(
                int(m_d.group(1)),
                int(m_d.group(2)),
                int(m_d.group(3)),
                int(m_t.group(1)),
                int(m_t.group(2)),
                sec_v,
                tzinfo=UTC,
            )
            ts_utc = int((dt_local + timedelta(seconds=tz_shift_sec)).timestamp())
            return ts_utc, 2

    raise ValueError(f"HISTDATA_MALFORMED_DATETIME [{label}]: {list(row[:2])!r}")


def _parse_histdata_text_rows(
    text: str,
    *,
    asset: str,
    source_timezone: str,
    source_label: str,
) -> list[tuple[int, float, float, float, float]]:
    out: list[tuple[int, float, float, float, float]] = []
    for row_idx, line in enumerate(text.splitlines()):
        stripped = line.strip()
        if not stripped:
            continue
        delim = ";" if ";" in stripped else ","
        row = [cell.strip() for cell in stripped.split(delim)]
        if row_idx == 0 and row[0] and not row[0][0].isdigit():
            continue
        ts_utc, o_idx = _parse_histdata_timestamp_utc(
            row,
            source_timezone=source_timezone,
            label=f"histdata.{asset}.{source_label}[{row_idx}]",
        )
        if ts_utc >= HOLDOUT_STOP_UTC_SEC:
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION [HISTDATA {asset} {source_label} row={row_idx}]: "
                f"ts_utc={_utc_iso(ts_utc)} >= 2025-01-01T00:00:00Z"
            )
        if len(row) < o_idx + 4:
            raise ValueError(
                f"HISTDATA_MALFORMED_ROW [{asset} {source_label} row={row_idx}]: "
                f"expected >={o_idx + 4} cols, got {len(row)}"
            )
        o_v = _parse_strict_float(row[o_idx], label=f"histdata.{asset}[{row_idx}].open")
        h_v = _parse_strict_float(row[o_idx + 1], label=f"histdata.{asset}[{row_idx}].high")
        l_v = _parse_strict_float(row[o_idx + 2], label=f"histdata.{asset}[{row_idx}].low")
        c_v = _parse_strict_float(row[o_idx + 3], label=f"histdata.{asset}[{row_idx}].close")
        out.append((ts_utc, o_v, h_v, l_v, c_v))
    return out


def parse_histdata_m1_files(
    paths: Sequence[Path] | Path,
    *,
    asset: str,
    source_timezone: str = "UTC",
    filter_nonpositive: bool = False,
) -> ValidatedM1Batch:
    """Parse compliant HistData/TrueFX M1 CSV or ZIP files strictly as `HISTDATA_BID_ONLY`."""
    asset_u = _normalize_symbol(asset)
    path_list = [Path(paths)] if isinstance(paths, (str, Path)) else [Path(p) for p in paths]
    if not path_list:
        raise ValueError(f"HISTDATA_NO_FILES [{asset_u}]: paths must not be empty")

    parsed_rows: list[tuple[int, float, float, float, float]] = []
    source_names: list[str] = []

    for fpath in sorted(path_list):
        if not fpath.is_file():
            raise FileNotFoundError(f"HistData/TrueFX file not found: {fpath}")
        source_names.append(fpath.name)
        suffix = fpath.suffix.lower()
        if suffix == ".zip":
            with zipfile.ZipFile(fpath, "r") as zf:
                members = [
                    info
                    for info in zf.infolist()
                    if not info.is_dir() and Path(info.filename).suffix.lower() in (".csv", ".txt")
                ]
                if not members:
                    raise ValueError(f"HISTDATA_ZIP_EMPTY [{asset_u}]: no .csv/.txt members in {fpath.name}")
                if len(members) > _MAX_ZIP_MEMBERS:
                    raise ValueError(f"HISTDATA_ZIP_TOO_MANY_MEMBERS [{asset_u}]: {len(members)} > {_MAX_ZIP_MEMBERS}")
                for info in sorted(members, key=lambda m: m.filename):
                    norm_name = info.filename.replace("\\", "/")
                    if norm_name.startswith("/") or ".." in norm_name.split("/"):
                        raise ValueError(f"HISTDATA_ZIP_UNSAFE_PATH [{asset_u}]: {info.filename!r}")
                    if info.file_size > _MAX_ZIP_MEMBER_BYTES:
                        raise ValueError(
                            f"HISTDATA_ZIP_OVERSIZED [{asset_u}]: {info.filename} size={info.file_size}"
                        )
                    raw_bytes = zf.read(info)
                    text = raw_bytes.decode("utf-8-sig", errors="strict")
                    parsed_rows.extend(
                        _parse_histdata_text_rows(
                            text,
                            asset=asset_u,
                            source_timezone=source_timezone,
                            source_label=f"{fpath.name}:{info.filename}",
                        )
                    )
        elif suffix in (".csv", ".txt"):
            text = fpath.read_text(encoding="utf-8-sig")
            parsed_rows.extend(
                _parse_histdata_text_rows(
                    text,
                    asset=asset_u,
                    source_timezone=source_timezone,
                    source_label=fpath.name,
                )
            )
        else:
            raise ValueError(f"HISTDATA_UNSUPPORTED_EXT [{asset_u}]: {fpath.suffix!r} (expected .csv/.txt/.zip)")

    if not parsed_rows:
        raise ValueError(f"HISTDATA_EMPTY [{asset_u}]: 0 bars parsed from {source_names}")

    parsed_rows.sort(key=lambda r: r[0])
    ts_arr = np.asarray([r[0] for r in parsed_rows], dtype=np.int64)
    bid_arr = np.asarray([r[1:] for r in parsed_rows], dtype=np.float64)

    return validate_m1_bars(
        asset_u,
        ts_arr,
        bid_arr,
        tier=TIER_3_HISTDATA_TRUEFX,
        source_provenance=sam.PROVENANCE_HISTDATA_BID_ONLY,
        ask_ohlc=None,
        filter_nonpositive=filter_nonpositive,
        waf_bypass_attempted=False,
        source_detail=f"histdata-truefx:{','.join(source_names[:4])}",
    )


class HistDataTrueFxAdapter:
    """Tier 3 compliant local HistData/TrueFX M1 CSV/ZIP adapter (zero scraping, zero WAF bypass)."""

    def __init__(
        self,
        data_dir: str | Path | None = None,
        *,
        source_timezone: str = "UTC",
    ) -> None:
        self.data_dir = Path(data_dir) if data_dir is not None else None
        self.source_timezone = str(source_timezone)

    def find_symbol_files(self, symbol: str) -> list[Path]:
        if self.data_dir is None or not self.data_dir.is_dir():
            return []
        sym_u = _normalize_symbol(symbol)
        sym_l = sym_u.lower()
        hits: list[Path] = []
        sub_dir = self.data_dir / sym_l
        search_dirs = [sub_dir, self.data_dir] if sub_dir.is_dir() else [self.data_dir]
        for sdir in search_dirs:
            for cand in sorted(sdir.iterdir()):
                if not cand.is_file() or cand.suffix.lower() not in (".csv", ".txt", ".zip"):
                    continue
                if sdir == sub_dir or sym_l in cand.name.lower():
                    if cand not in hits:
                        hits.append(cand)
        return hits

    def load_symbol_m1(
        self,
        spec: SymbolHarvestSpec,
        *,
        filter_nonpositive: bool = False,
    ) -> ValidatedM1Batch:
        files = self.find_symbol_files(spec.canonical_symbol)
        if not files:
            raise FileNotFoundError(
                f"HISTDATA_FILES_NOT_FOUND [{spec.canonical_symbol}]: no local CSV/ZIP files in {self.data_dir}"
            )
        return parse_histdata_m1_files(
            files,
            asset=spec.canonical_symbol,
            source_timezone=self.source_timezone,
            filter_nonpositive=filter_nonpositive,
        )


# ==============================================================================
# 3-Tier Compliant Cascade Orchestrator & Dry-Run Planner
# ==============================================================================


class MultiSourceM1Harvester:
    """3-Tier compliant M1 harvester: `QDM CLI -> FTMO-Demo -> HistData/TrueFX` (`0` WAF bypass)."""

    def __init__(
        self,
        *,
        cache_dir: Path = DEFAULT_CACHE_DIR,
        manifest_path: Path | None = None,
        lock_path: Path = sam.DEFAULT_LOCK_PATH,
        work_dir: Path = DEFAULT_WORK_ROOT,
        qdm_adapter: QdmCliAdapter | None = None,
        ftmo_adapter: FtmoDemoM1Adapter | None = None,
        histdata_adapter: HistDataTrueFxAdapter | None = None,
        ftmo_specs_path: Path = DEFAULT_FTMO_SPECS_PATH,
    ) -> None:
        self.cache_dir = Path(cache_dir)
        self.manifest_path = Path(manifest_path) if manifest_path is not None else (self.cache_dir / "manifest.json")
        self.lock_path = Path(lock_path)
        self.work_dir = Path(work_dir)
        self.ftmo_specs_path = Path(ftmo_specs_path)
        self.qdm_adapter = qdm_adapter if qdm_adapter is not None else QdmCliAdapter()
        self.ftmo_adapter = ftmo_adapter if ftmo_adapter is not None else FtmoDemoM1Adapter()
        self.histdata_adapter = histdata_adapter if histdata_adapter is not None else HistDataTrueFxAdapter()

    def inventory(self, *, allow_missing_manifest: bool = False) -> dict[str, Any]:
        return discover_missing_m1_symbols(
            self.manifest_path,
            ftmo_specs_path=self.ftmo_specs_path,
            allow_missing_manifest=allow_missing_manifest,
        )

    def build_dry_run_plan(
        self,
        *,
        date_from: str = DEV_START_QDM_DATE,
        date_to: str = HOLDOUT_CUTOFF_QDM_DATE,
        allow_missing_manifest: bool = False,
    ) -> dict[str, Any]:
        """Validate inventory, QDM binary/catalog availability, and export commands without spawning MT5/QDM."""
        _, d_from_dot = _parse_date_to_dot(date_from, label="dry_run.date_from")
        _, d_to_dot = _parse_date_to_dot(date_to, label="dry_run.date_to")
        inv = self.inventory(allow_missing_manifest=allow_missing_manifest)

        qdm_exe = self.qdm_adapter.executable
        catalog = read_qdm_catalog_codes(self.qdm_adapter.home) if self.qdm_adapter.home is not None else {}
        placeholder_exe = qdm_exe if qdm_exe is not None else Path("qdmcli.exe")

        symbol_plans: list[dict[str, Any]] = []
        qdm_catalog_matched = 0
        for raw_spec in inv["missing_specs"]:
            sym = raw_spec["canonical_symbol"]
            qdm_code = raw_spec["qdm_instrument_code"]
            in_catalog = qdm_code in catalog
            if in_catalog:
                qdm_catalog_matched += 1
            export_out = self.work_dir / "qdm_exports" / sym.lower()
            cmd = build_qdm_export_command(
                placeholder_exe,
                qdm_symbol=raw_spec["qdm_symbol_name"],
                output_dir=export_out,
                date_from=d_from_dot,
                date_to=d_to_dot,
            )
            hist_files = self.histdata_adapter.find_symbol_files(sym)
            symbol_plans.append(
                {
                    "symbol": sym,
                    "scale": raw_spec["scale"],
                    "asset_class": raw_spec["asset_class"],
                    "qdm_instrument_code": qdm_code,
                    "qdm_symbol_name": raw_spec["qdm_symbol_name"],
                    "qdm_in_installed_catalog": in_catalog,
                    "qdm_minute_start": catalog[qdm_code]["minute_start"] if in_catalog else None,
                    "qdm_export_argv_valid": True,
                    "qdm_export_dateto": d_to_dot,
                    "qdm_export_has_broker_arg": any(a.lower().startswith("broker=") for a in cmd[1:]),
                    "ftmo_symbol": raw_spec["ftmo_symbol"],
                    "ftmo_tier2_status": "DELEGATED_REQUIRES_MT5_LOCK",
                    "histdata_fx_eligible": raw_spec["histdata_fx_eligible"],
                    "histdata_local_files_found": len(hist_files),
                    "cascade_tiers": list(raw_spec["eligible_tiers"]),
                    "expected_provenance_by_tier": dict(raw_spec["expected_provenance_by_tier"]),
                }
            )

        return {
            "schema": SCHEMA_VERSION,
            "mode": "DRY_RUN_PLAN_ONLY",
            "utc": datetime.now(UTC).isoformat(),
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
            "mt5_terminal_launched": False,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_rows_analysed": 0,
            "date_from": d_from_dot,
            "date_to": d_to_dot,
            "universe_count": inv["universe_count"],
            "present_count": inv["present_count"],
            "missing_count": inv["missing_count"],
            "present_symbols": inv["present_symbols"],
            "missing_symbols": inv["missing_symbols"],
            "qdm_executable_found": self.qdm_adapter.available,
            "qdm_catalog_entries_loaded": len(catalog),
            "qdm_catalog_matched_missing": qdm_catalog_matched,
            "symbol_plans": symbol_plans,
        }

    def harvest_symbol(
        self,
        symbol: str,
        *,
        date_from: str = DEV_START_QDM_DATE,
        date_to: str = HOLDOUT_CUTOFF_QDM_DATE,
        tiers: Sequence[str] | None = None,
        mt5_lock_held: bool = False,
        allow_live_mt5: bool = False,
        mt5_module: Any = None,
        filter_nonpositive: bool = False,
        seal_output: bool = True,
        write_npz: bool = True,
        fragments_dir: Path | None = None,
        npz_dir: Path | None = None,
    ) -> SymbolHarvestResult:
        """Execute 3-tier compliant cascade for one symbol, validate strictly, and optionally seal."""
        d_from, d_from_dot = _parse_date_to_dot(date_from, label=f"harvest.{symbol}.date_from")
        d_to, d_to_dot = _parse_date_to_dot(date_to, label=f"harvest.{symbol}.date_to")
        if d_from > d_to:
            raise ValueError(f"HARVEST_INVALID_DATE_RANGE [{symbol}]: {d_from_dot} > {d_to_dot}")

        ftmo_specs = _load_ftmo_specs_optional(self.ftmo_specs_path)
        spec = build_symbol_harvest_spec(symbol, ftmo_specs=ftmo_specs)
        requested_tiers = tuple(tiers) if tiers is not None else spec.eligible_tiers
        for t in requested_tiers:
            if t not in PROVENANCE_BY_TIER:
                raise ValueError(f"UNKNOWN_HARVEST_TIER: {t!r}")

        attempts: list[TierAttemptRecord] = []
        batch: ValidatedM1Batch | None = None

        for tier in requested_tiers:
            exp_prov = PROVENANCE_BY_TIER[tier]
            try:
                if tier == TIER_1_QDM_CLI:
                    batch = self.qdm_adapter.export_symbol_m1(
                        spec,
                        self.work_dir / "qdm_exports" / spec.canonical_symbol.lower(),
                        date_from=d_from_dot,
                        date_to=d_to_dot,
                        filter_nonpositive=filter_nonpositive,
                    )
                elif tier == TIER_2_FTMO_DEMO:
                    batch = self.ftmo_adapter.fetch_symbol_m1(
                        spec,
                        date_from=d_from.isoformat(),
                        date_to=d_to.isoformat(),
                        mt5_lock_held=mt5_lock_held,
                        allow_live_mt5=allow_live_mt5,
                        mt5_module=mt5_module,
                        filter_nonpositive=filter_nonpositive,
                    )
                elif tier == TIER_3_HISTDATA_TRUEFX:
                    batch = self.histdata_adapter.load_symbol_m1(
                        spec,
                        filter_nonpositive=filter_nonpositive,
                    )
                attempts.append(
                    TierAttemptRecord(
                        tier=tier,
                        status="OK",
                        source_provenance=batch.source_provenance if batch is not None else exp_prov,
                        reason="validated_m1_batch_ready",
                        waf_bypass_attempted=False,
                    )
                )
                break
            except HoldoutLockError:
                # Holdout contamination MUST NEVER be swallowed or cascaded past — hard fail closed!
                raise
            except (
                HarvesterError,
                FileNotFoundError,
                ValueError,
                OSError,
            ) as exc:
                attempts.append(
                    TierAttemptRecord(
                        tier=tier,
                        status="FAILED_CASCADE_NEXT",
                        source_provenance=exp_prov,
                        reason=f"{type(exc).__name__}: {exc}",
                        waf_bypass_attempted=False,
                    )
                )

        if batch is None:
            return SymbolHarvestResult(
                symbol=spec.canonical_symbol,
                status="UNAVAILABLE_ALL_TIERS",
                selected_tier=None,
                source_provenance=None,
                native_ask=False,
                has_true_bid_ask=False,
                bar_count=0,
                max_ts_utc=None,
                holdout_rows_analysed=0,
                waf_bypass_attempted=False,
                attempts=tuple(attempts),
            )

        frag_doc: dict[str, Any] | None = None
        frag_path_str: str | None = None
        npz_path_str: str | None = None

        if seal_output:
            fdir = Path(fragments_dir) if fragments_dir is not None else (self.cache_dir / "_fragments")
            frag_out = fdir / f"w4_m1_{spec.canonical_symbol.lower()}.json"
            npz_out: Path | None = None
            if write_npz:
                ndir = Path(npz_dir) if npz_dir is not None else (self.work_dir / "sealed_npz")
                npz_out = ndir / f"{spec.canonical_symbol}-M1-{batch.source_provenance}.npz"
            frag_doc = sam.seal_generic_m1_arrays(
                spec.canonical_symbol,
                batch.times_sec,
                batch.bid_ohlc,
                source_provenance=batch.source_provenance,
                ask_ohlc=batch.ask_ohlc,
                spread_points=batch.spread_points,
                point_size=batch.point_size,
                scale=spec.scale,
                fragment_out=frag_out,
                npz_out=npz_out,
                cache_dir=self.cache_dir,
                lock_path=self.lock_path,
                filter_nonpositive=filter_nonpositive,
                source_detail=batch.source_detail,
                waf_bypass_attempted=False,
            )
            frag_path_str = str(frag_out)
            if npz_out is not None:
                npz_path_str = str(npz_out)

        return SymbolHarvestResult(
            symbol=spec.canonical_symbol,
            status="SEALED_OK" if seal_output else "VALIDATED_OK",
            selected_tier=batch.tier,
            source_provenance=batch.source_provenance,
            native_ask=batch.native_ask,
            has_true_bid_ask=batch.has_true_bid_ask,
            bar_count=batch.bar_count,
            max_ts_utc=batch.max_ts_utc,
            holdout_rows_analysed=0,
            waf_bypass_attempted=False,
            attempts=tuple(attempts),
            fragment=frag_doc,
            fragment_path=frag_path_str,
            npz_path=npz_path_str,
        )


# ==============================================================================
# CLI Entrypoint (Defaults to Safe Offline Dry-Run)
# ==============================================================================


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Validate 16-symbol inventory, QDM binary/catalog, and export commands without launching MT5/QDM.",
    )
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST_PATH, help="Path to hot-m1-cache manifest.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE_DIR, help="Hot M1 cache root.")
    parser.add_argument("--work-dir", type=Path, default=DEFAULT_WORK_ROOT, help="Working directory for M1 harvest.")
    parser.add_argument("--histdata-dir", type=Path, default=None, help="Optional local HistData/TrueFX drop dir.")
    parser.add_argument("--date-from", type=str, default=DEV_START_QDM_DATE, help="Dev start date (>= 2018.01.01).")
    parser.add_argument("--date-to", type=str, default=HOLDOUT_CUTOFF_QDM_DATE, help="Dev end date (<= 2024.12.31).")
    parser.add_argument("--out", type=Path, default=None, help="Optional JSON output path for dry-run plan.")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    harvester = MultiSourceM1Harvester(
        cache_dir=args.cache_dir,
        manifest_path=args.manifest,
        work_dir=args.work_dir,
        histdata_adapter=HistDataTrueFxAdapter(args.histdata_dir),
    )
    plan = harvester.build_dry_run_plan(date_from=args.date_from, date_to=args.date_to)
    if args.out is not None:
        _atomic_write_json(args.out, plan)
    print(json.dumps(plan, indent=2, ensure_ascii=False))
    return 0


__all__ = [
    "CANONICAL_SYMBOL_MAP",
    "CASCADE_ORDER",
    "DEFAULT_CACHE_DIR",
    "DEFAULT_MANIFEST_PATH",
    "DEV_START_DATE",
    "DEV_START_QDM_DATE",
    "DEV_START_UTC_SEC",
    "FtmoDemoM1Adapter",
    "HOLDOUT_CUTOFF_DATE",
    "HOLDOUT_CUTOFF_QDM_DATE",
    "HOLDOUT_STOP_UTC_SEC",
    "HarvesterError",
    "HistDataTrueFxAdapter",
    "Mt5LockRequiredError",
    "MultiSourceM1Harvester",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PROVENANCE_BY_TIER",
    "QdmBusyError",
    "QdmCliAdapter",
    "QdmLicenseError",
    "QdmUnavailableError",
    "SCHEMA_VERSION",
    "SymbolHarvestResult",
    "SymbolHarvestSpec",
    "TIER_1_QDM_CLI",
    "TIER_2_FTMO_DEMO",
    "TIER_3_HISTDATA_TRUEFX",
    "TierAttemptRecord",
    "WAF_BYPASS_ATTEMPTED",
    "ValidatedM1Batch",
    "build_qdm_export_command",
    "build_qdm_symbol_list_command",
    "build_symbol_harvest_spec",
    "discover_missing_m1_symbols",
    "discover_qdm_executable",
    "parse_ftmo_m1_csv",
    "parse_ftmo_m1_npz",
    "parse_ftmo_mt5_rates",
    "parse_histdata_m1_files",
    "parse_qdm_m1_csv",
    "parse_qdm_symbol_list_output",
    "read_qdm_catalog_codes",
    "validate_m1_bars",
    "validate_qdm_argv",
]


if __name__ == "__main__":
    raise SystemExit(main())
