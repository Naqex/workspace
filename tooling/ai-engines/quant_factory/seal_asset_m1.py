"""Generalized M1 Bid/Ask Parquet Sealer (2018-2024 Dev ONLY; Holdout 2025+ fail-closed).

Seals raw Dukascopy M1 Bid/Ask JSON pairs (`<asset_lower>-m1-{bid,ask}-<year>.json`) into
SHA-256 verified Zstd Parquets under `.runtime/hot-m1-cache/<asset_lower>/` and writes an
isolated per-asset fragment JSON so parallel data lanes never contend on `manifest.json`.

Hard safety invariants (ZERO bare `assert` statements — `[ARCH-02]` & `python -O` safe):
  - Verifies `planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 before any work.
  - Enforces `START * 1000 <= ts_ms < STOP * 1000` (`holdout_rows == 0`) on ALL raw and
    sealed bars via explicit `HoldoutLockError` + `enforce_pre_holdout_ts()`.
  - Enforces finite positive prices (`price > 0.0` raw AND scaled `int64 > 0`); catches any
    Apr-2020 `USOIL` `<= 0` anomaly, reports exact count/window, and fails closed unless
    `--filter-nonpositive` explicitly quarantines `<= 0` bars with full audit flags.
  - Clamps tiny crossed ticks conservatively (`ask = max(ask, bid)`), preserving OHLC order.
  - `--merge-fragments <DIR>` atomically merges `_fragments/*.json` into `manifest.json`
    after verifying every asset's SHA-256, monotonic pre-2025 timestamps, and `holdout_rows == 0`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES_DIR.parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_ts,
)

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
WAF_BYPASS_ATTEMPTED: bool = False

PROVENANCE_DUKASCOPY_TRUE_BID_ASK: str = "DUKASCOPY_TRUE_BID_ASK"
PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE: str = "QDM_PROVIDER_DEFAULT_SINGLE_SIDE"
PROVENANCE_FTMO_BID_PLUS_SPREAD: str = "FTMO_BID_PLUS_SPREAD"
PROVENANCE_HISTDATA_BID_ONLY: str = "HISTDATA_BID_ONLY"

VALID_SOURCE_PROVENANCES: frozenset[str] = frozenset(
    {
        PROVENANCE_DUKASCOPY_TRUE_BID_ASK,
        PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        PROVENANCE_FTMO_BID_PLUS_SPREAD,
        PROVENANCE_HISTDATA_BID_ONLY,
    }
)
TRUE_TWO_SIDE_PROVENANCES: frozenset[str] = frozenset({PROVENANCE_DUKASCOPY_TRUE_BID_ASK})
SYNTHETIC_ASK_PROVENANCES: frozenset[str] = frozenset({PROVENANCE_FTMO_BID_PLUS_SPREAD})
SINGLE_SIDE_ONLY_PROVENANCES: frozenset[str] = frozenset(
    {
        PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE,
        PROVENANCE_HISTDATA_BID_ONLY,
    }
)

_PROVENANCE_PARQUET_TAG: dict[str, str] = {
    PROVENANCE_DUKASCOPY_TRUE_BID_ASK: "BIDASK",
    PROVENANCE_QDM_PROVIDER_DEFAULT_SINGLE_SIDE: "QDM_SINGLE",
    PROVENANCE_FTMO_BID_PLUS_SPREAD: "FTMO_BID_SPREAD",
    PROVENANCE_HISTDATA_BID_ONLY: "HISTDATA_BID",
}

DEFAULT_CACHE: Path = ROOT / ".runtime" / "hot-m1-cache"
DEFAULT_LOCK_PATH: Path = ROOT / "planning" / "research" / "NATIVE_FTMO_HOLDOUT_LOCK.json"
LOCK_SHA: str = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

DEV_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
START_SEC: int = int(datetime(2018, 1, 1, tzinfo=UTC).timestamp())
STOP_SEC: int = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
START_MS: int = START_SEC * 1000
STOP_MS: int = STOP_SEC * 1000
_YEAR_BOUNDS_SEC: dict[int, tuple[int, int]] = {
    y: (
        int(datetime(y, 1, 1, tzinfo=UTC).timestamp()),
        int(datetime(y + 1, 1, 1, tzinfo=UTC).timestamp()),
    )
    for y in DEV_YEARS
}

_APR_2020_START_SEC: int = int(datetime(2020, 4, 1, tzinfo=UTC).timestamp())
_APR_2020_STOP_SEC: int = int(datetime(2020, 5, 1, tzinfo=UTC).timestamp())
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_ASSET_RE = re.compile(r"^[A-Z0-9]{3,16}$")

# Canonical integer price scale per asset (5-digit FX=100000; JPY/Indices/Silver/Oil=1000; Gold/BTC=100)
ASSET_DEFAULT_SCALES: dict[str, int] = {
    # 5-digit FX (10 existing/new)
    "EURUSD": 100000,
    "GBPUSD": 100000,
    "AUDUSD": 100000,
    "USDCAD": 100000,
    "USDCHF": 100000,
    "NZDUSD": 100000,
    "EURGBP": 100000,
    "EURAUD": 100000,
    "GBPAUD": 100000,
    "EURCAD": 100000,
    # 3-digit JPY FX + Indices + Silver + Oil
    "USDJPY": 1000,
    "EURJPY": 1000,
    "GBPJPY": 1000,
    "AUDJPY": 1000,
    "CADJPY": 1000,
    "CHFJPY": 1000,
    "NZDJPY": 1000,
    "US100": 1000,
    "US500": 1000,
    "GER40": 1000,
    "US30": 1000,
    "JP225": 1000,
    "UK100": 1000,
    "XAGUSD": 1000,
    "USOIL": 1000,
    "UKOIL": 1000,
    # 2-digit Gold & Crypto
    "XAUUSD": 100,
    "BTCUSD": 100,
}


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
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


def _atomic_write_parquet(table: pa.Table, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            tmp = Path(fh.name)
        pq.write_table(table, tmp, compression="zstd")
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _atomic_write_npz(arrays: dict[str, np.ndarray], path: Path) -> None:
    """Atomically persist zero-pickle compressed NPZ with flush + fsync."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".npz.tmp",
            delete=False,
        ) as fh:
            np.savez_compressed(fh, **cast(Any, arrays))
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)


def _validate_provenance_flags(
    source_provenance: Any,
    *,
    has_ask_input: bool,
    has_spread_input: bool,
    asset: str,
) -> tuple[str, bool, bool, bool]:
    """Return `(provenance, native_ask, has_true_bid_ask, ask_columns_present)` fail-closed."""
    if not isinstance(source_provenance, str) or source_provenance not in VALID_SOURCE_PROVENANCES:
        raise ValueError(
            f"INVALID_SOURCE_PROVENANCE [{asset}]: expected one of {sorted(VALID_SOURCE_PROVENANCES)}, "
            f"got {source_provenance!r}"
        )
    if source_provenance in SINGLE_SIDE_ONLY_PROVENANCES:
        if has_ask_input:
            raise ValueError(
                f"PROVENANCE_MISMATCH [{asset}]: {source_provenance} is single-side only "
                "and must NEVER carry ask_ohlc or be labeled true Bid/Ask"
            )
        return source_provenance, False, False, False
    if source_provenance == PROVENANCE_FTMO_BID_PLUS_SPREAD:
        if not has_ask_input and not has_spread_input:
            raise ValueError(
                f"PROVENANCE_MISMATCH [{asset}]: {PROVENANCE_FTMO_BID_PLUS_SPREAD} requires "
                "ask_ohlc or (spread_points, point_size)"
            )
        return source_provenance, False, False, True
    if not has_ask_input:
        raise ValueError(
            f"PROVENANCE_MISMATCH [{asset}]: {PROVENANCE_DUKASCOPY_TRUE_BID_ASK} requires explicit ask_ohlc"
        )
    return source_provenance, True, True, True


def _utc_iso(ts_sec: int) -> str:
    return datetime.fromtimestamp(int(ts_sec), tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def verify_holdout_lock(
    lock_path: Path = DEFAULT_LOCK_PATH,
    expected_sha: str = LOCK_SHA,
) -> str:
    """Fail-closed verification of `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256."""
    if not lock_path.is_file():
        raise HoldoutLockError(f"Holdout lock file missing: {lock_path}")
    try:
        raw_doc = json.loads(lock_path.read_text(encoding="utf-8-sig"))
        actual_sha = _sha256_file(lock_path)
    except Exception as exc:
        raise HoldoutLockError(f"Holdout lock file unreadable or corrupt: {exc}") from exc
    if not isinstance(raw_doc, dict) or actual_sha != expected_sha:
        raise HoldoutLockError(f"Holdout lock SHA mismatch: expected={expected_sha} actual={actual_sha}")
    return actual_sha


def _normalize_asset(asset: str) -> str:
    cleaned = str(asset or "").strip().upper()
    if not cleaned or _SAFE_ASSET_RE.fullmatch(cleaned) is None:
        raise ValueError(f"Invalid asset identifier (expected 3-16 uppercase alnum chars): {asset!r}")
    return cleaned


def _resolve_scale(asset: str, scale: int | None) -> int:
    if scale is None:
        if asset not in ASSET_DEFAULT_SCALES:
            raise ValueError(f"No default scale for asset {asset!r}; pass explicit --scale <INT>")
        return ASSET_DEFAULT_SCALES[asset]
    if isinstance(scale, bool) or not isinstance(scale, int) or scale <= 0:
        raise ValueError(f"Invalid scale (must be positive int): {scale!r}")
    return scale


def _parse_side_rows(
    rows: Any,
    *,
    asset: str,
    year: int,
    side_label: str,
) -> dict[int, tuple[float, float, float, float]]:
    """Parse raw JSON OHLC rows and enforce `[START_MS, STOP_MS)` + finite floats fail-closed."""
    if not isinstance(rows, list) or not rows:
        raise ValueError(f"Empty or malformed {side_label} rows for {asset} {year}")

    year_start_ms = int(datetime(year, 1, 1, tzinfo=UTC).timestamp()) * 1000
    year_stop_ms = int(datetime(year + 1, 1, 1, tzinfo=UTC).timestamp()) * 1000

    out: dict[int, tuple[float, float, float, float]] = {}
    for idx, row in enumerate(rows):
        if not isinstance(row, (list, tuple)) or len(row) < 5:
            raise ValueError(f"Malformed {side_label} row[{idx}] for {asset} {year}: expected >=5 elements")
        ts_raw = row[0]
        if isinstance(ts_raw, bool) or not isinstance(ts_raw, (int, float)):
            raise HoldoutLockError(f"Invalid timestamp in {asset} {year} {side_label} row[{idx}]: {ts_raw!r}")
        ts_ms = int(ts_raw)
        if ts_ms >= STOP_MS:
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION [{asset} {year} {side_label}]: ts_ms={ts_ms} >= STOP_MS ({STOP_MS})"
            )
        if ts_ms < START_MS:
            raise HoldoutLockError(
                f"PRE_DEV_RANGE_BREACH [{asset} {year} {side_label}]: ts_ms={ts_ms} < START_MS ({START_MS})"
            )
        if ts_ms < year_start_ms or ts_ms >= year_stop_ms:
            raise ValueError(
                f"OUT_OF_YEAR_TIMESTAMP [{asset} {year} {side_label}]: ts_ms={ts_ms} "
                f"outside [{year_start_ms}, {year_stop_ms})"
            )
        ohlc = (float(row[1]), float(row[2]), float(row[3]), float(row[4]))
        if not all(math.isfinite(v) for v in ohlc):
            raise ValueError(f"NONFINITE_PRICE [{asset} {year} {side_label} row[{idx}]]: {ohlc!r}")
        out[ts_ms] = ohlc
    return out


def seal_asset(
    asset: str,
    raw_dir: Path,
    scale: int | None = None,
    *,
    fragment_out: Path | None = None,
    cache_dir: Path = DEFAULT_CACHE,
    lock_path: Path = DEFAULT_LOCK_PATH,
    years: Sequence[int] = DEV_YEARS,
    filter_nonpositive: bool = False,
) -> dict[str, Any]:
    """Seal 7 Dev-only (2018-2024) M1 Bid/Ask Zstd Parquets into hot cache and emit an isolated fragment JSON."""
    lock_sha = verify_holdout_lock(lock_path)
    asset_u = _normalize_asset(asset)
    asset_l = asset_u.lower()
    eff_scale = _resolve_scale(asset_u, scale)

    raw_root = Path(raw_dir)
    if not raw_root.is_dir():
        raise FileNotFoundError(f"Raw JSON directory not found: {raw_root}")

    year_tuple = tuple(int(y) for y in years)
    if not year_tuple:
        raise ValueError("years must not be empty")
    for y in year_tuple:
        if y < 2018 or y > 2024:
            raise HoldoutLockError(f"HOLDOUT_OR_RANGE_BREACH: year {y} outside sealed Dev 2018-2024")

    dst_dir = Path(cache_dir) / asset_l
    dst_dir.mkdir(parents=True, exist_ok=True)

    years_meta: dict[str, dict[str, Any]] = {}
    total_minutes = 0
    total_bytes = 0
    nonpos_detected_total = 0
    nonpos_filtered_total = 0
    crossed_total = 0
    global_min_price = math.inf
    global_max_price = -math.inf
    apr2020_summary: dict[str, Any] | None = None

    for y in year_tuple:
        bid_file = raw_root / f"{asset_l}-m1-bid-{y}.json"
        ask_file = raw_root / f"{asset_l}-m1-ask-{y}.json"
        if not bid_file.is_file():
            raise FileNotFoundError(f"Missing raw Bid JSON: {bid_file}")
        if not ask_file.is_file():
            raise FileNotFoundError(f"Missing raw Ask JSON: {ask_file}")

        bid_rows = json.loads(bid_file.read_text(encoding="utf-8"))
        ask_rows = json.loads(ask_file.read_text(encoding="utf-8"))
        b_map = _parse_side_rows(bid_rows, asset=asset_u, year=y, side_label="bid")
        a_map = _parse_side_rows(ask_rows, asset=asset_u, year=y, side_label="ask")

        common_ms = sorted(set(b_map.keys()) & set(a_map.keys()))
        if not common_ms:
            raise ValueError(f"No common Bid/Ask minutes for {asset_u} {y}")

        if common_ms[0] < START_MS or common_ms[-1] >= STOP_MS:
            raise HoldoutLockError(
                f"HOLDOUT_OR_RANGE_BREACH [{asset_u} {y}]: common_ms bounds "
                f"[{common_ms[0]}, {common_ms[-1]}] outside [{START_MS}, {STOP_MS})"
            )

        mins = np.array([ms // 60000 for ms in common_ms], dtype=np.int64)
        if len(mins) > 1 and not bool(np.all(np.diff(mins) > 0)):
            raise ValueError(f"Non-monotonic or duplicate minute timestamps in {asset_u} {y}")

        b_arr = np.array([b_map[ms] for ms in common_ms], dtype=np.float64)
        a_arr = np.array([a_map[ms] for ms in common_ms], dtype=np.float64)

        if not (bool(np.all(np.isfinite(b_arr))) and bool(np.all(np.isfinite(a_arr)))):
            raise ValueError(f"Non-finite Bid/Ask prices detected in {asset_u} {y}")

        # Strict positive-price guard (explicitly flags Apr-2020 USOIL <= 0 anomalies fail-closed)
        nonpos_mask = np.any(b_arr <= 0.0, axis=1) | np.any(a_arr <= 0.0, axis=1)
        nonpos_count = int(np.sum(nonpos_mask))
        nonpos_filtered = 0
        nonpos_window_utc: list[str] | None = None
        if nonpos_count > 0:
            bad_indices = np.flatnonzero(nonpos_mask)
            raw_min = float(min(np.min(b_arr[nonpos_mask]), np.min(a_arr[nonpos_mask])))
            first_utc = _utc_iso(int(mins[bad_indices[0]]) * 60)
            last_utc = _utc_iso(int(mins[bad_indices[-1]]) * 60)
            nonpos_window_utc = [first_utc, last_utc]
            nonpos_detected_total += nonpos_count
            if not filter_nonpositive:
                raise ValueError(
                    f"NONPOSITIVE_PRICE_ANOMALY [{asset_u} {y}]: detected {nonpos_count} bar(s) with price <= 0.0 "
                    f"(min_price={raw_min}, window={first_utc}..{last_utc}); pass --filter-nonpositive to "
                    "quarantine non-positive bars fail-closed"
                )
            keep_mask = ~nonpos_mask
            mins = mins[keep_mask]
            b_arr = b_arr[keep_mask]
            a_arr = a_arr[keep_mask]
            nonpos_filtered = nonpos_count
            nonpos_filtered_total += nonpos_filtered
            if len(mins) == 0:
                raise ValueError(f"All bars removed by --filter-nonpositive in {asset_u} {y}")

        # Enforce pre-Holdout timestamp seal via canonical guard (active under python -O)
        ts_sec = mins * 60
        enforce_pre_holdout_ts(ts_sec, START_SEC, STOP_SEC, context=f"seal_asset_m1:{asset_u}:{y}")

        # Enforce positive prices after filtering
        yr_min_bid = float(np.min(b_arr))
        yr_min_ask = float(np.min(a_arr))
        if yr_min_bid <= 0.0 or yr_min_ask <= 0.0:
            raise ValueError(f"Non-positive price survived check in {asset_u} {y}: bid={yr_min_bid}, ask={yr_min_ask}")

        # Ensure intra-bar OHLC consistency before conservative crossed-tick clamping
        b_high = np.maximum.reduce([b_arr[:, 0], b_arr[:, 1], b_arr[:, 2], b_arr[:, 3]])
        b_low = np.minimum.reduce([b_arr[:, 0], b_arr[:, 1], b_arr[:, 2], b_arr[:, 3]])
        b_arr[:, 1] = b_high
        b_arr[:, 2] = b_low
        a_high = np.maximum.reduce([a_arr[:, 0], a_arr[:, 1], a_arr[:, 2], a_arr[:, 3]])
        a_low = np.minimum.reduce([a_arr[:, 0], a_arr[:, 1], a_arr[:, 2], a_arr[:, 3]])
        a_arr[:, 1] = a_high
        a_arr[:, 2] = a_low

        # Clamp tiny crossed ticks conservatively: ask = max(ask, bid)
        crossed = int(np.sum(np.any(a_arr < b_arr, axis=1)))
        crossed_total += crossed
        a_arr = np.maximum(a_arr, b_arr)

        b_int = np.rint(b_arr * eff_scale).astype(np.int64)
        a_int = np.rint(a_arr * eff_scale).astype(np.int64)
        if int(np.min(b_int)) <= 0 or int(np.min(a_int)) <= 0:
            raise ValueError(
                f"Scaled integer price underflow <= 0 in {asset_u} {y} "
                f"(scale={eff_scale}, min_bid={yr_min_bid}, min_ask={yr_min_ask})"
            )
        if not bool(np.all(a_int >= b_int)):
            raise ValueError(f"Crossed scaled quote persisted after clamping in {asset_u} {y}")

        cols: dict[str, np.ndarray] = {"minute": mins}
        for i, name in enumerate(("bo", "bh", "bl", "bc")):
            cols[name] = b_int[:, i]
        for i, name in enumerate(("ao", "ah", "al", "ac")):
            cols[name] = a_int[:, i]

        pfile = dst_dir / f"{asset_u}-M1-BIDASK-{y}.parquet"
        _atomic_write_parquet(pa.table(cols), pfile)
        p_sha = _sha256_file(pfile)
        p_bytes = int(pfile.stat().st_size)

        yr_min_price = float(min(np.min(b_arr), np.min(a_arr)))
        yr_max_price = float(max(np.max(b_arr), np.max(a_arr)))
        global_min_price = min(global_min_price, yr_min_price)
        global_max_price = max(global_max_price, yr_max_price)

        med_spread_raw = float(np.median(a_arr[:, 0] - b_arr[:, 0]))
        med_spread_pts = float(np.median(a_int[:, 0] - b_int[:, 0]))

        yr_entry: dict[str, Any] = {
            "parquet": pfile.name,
            "parquet_sha256": p_sha,
            "minutes": int(len(mins)),
            "bytes": p_bytes,
            "min_price": round(yr_min_price, 6),
            "max_price": round(yr_max_price, 6),
            "crossed_clamped": crossed,
            "nonpositive_detected": nonpos_count,
            "nonpositive_filtered": nonpos_filtered,
            "median_spread_raw": round(med_spread_raw, 6),
            "median_spread_pts": round(med_spread_pts, 2),
        }
        if nonpos_window_utc is not None:
            yr_entry["nonpositive_window_utc"] = nonpos_window_utc

        if y == 2020:
            apr_mask = (ts_sec >= _APR_2020_START_SEC) & (ts_sec < _APR_2020_STOP_SEC)
            if bool(np.any(apr_mask)):
                apr_min = round(float(min(np.min(b_arr[apr_mask]), np.min(a_arr[apr_mask]))), 6)
                apr_mins = int(np.sum(apr_mask))
                yr_entry["apr_2020_minutes"] = apr_mins
                yr_entry["apr_2020_min_price"] = apr_min
                apr2020_summary = {
                    "minutes": apr_mins,
                    "min_price": apr_min,
                    "nonpositive_detected": nonpos_count,
                    "nonpositive_filtered": nonpos_filtered,
                }

        years_meta[str(y)] = yr_entry
        total_minutes += int(len(mins))
        total_bytes += p_bytes
        print(
            f"SEALED {asset_u:6s} {y}: {len(mins):,} mins | min_px={yr_min_price:.5f} | "
            f"med_spread={med_spread_pts:.2f} scaled_pts | crossed={crossed} | {p_bytes / 1e6:.2f} MB",
            flush=True,
        )

    fragment: dict[str, Any] = {
        "schema": "naqex-hot-m1-cache-fragment-v1",
        "utc": datetime.now(UTC).isoformat(),
        "source": "dukascopy-node-m1-bid-ask-paired",
        "source_provenance": PROVENANCE_DUKASCOPY_TRUE_BID_ASK,
        "has_true_bid_ask": True,
        "ask_columns_present": True,
        "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows": 0,
        "holdout_rows_analysed": 0,
        "asset": asset_u,
        "dir": asset_l,
        "native_Ask": True,
        "scale": eff_scale,
        "total_minutes": total_minutes,
        "total_bytes": total_bytes,
        "min_price": round(global_min_price, 6),
        "max_price": round(global_max_price, 6),
        "crossed_clamped_total": crossed_total,
        "nonpositive_detected_total": nonpos_detected_total,
        "nonpositive_filtered_total": nonpos_filtered_total,
        "nonpositive_anomaly_flagged": nonpos_detected_total > 0,
        "years": years_meta,
    }
    if apr2020_summary is not None:
        fragment["apr_2020_audit"] = apr2020_summary

    if fragment_out is not None:
        _atomic_write_json(Path(fragment_out), fragment)

    return fragment


def seal_generic_m1_arrays(
    asset: str,
    times_sec: np.ndarray | Sequence[int],
    bid_ohlc: np.ndarray,
    *,
    source_provenance: str,
    ask_ohlc: np.ndarray | None = None,
    spread_points: np.ndarray | None = None,
    point_size: float | None = None,
    scale: int | None = None,
    fragment_out: Path | None = None,
    npz_out: Path | None = None,
    cache_dir: Path = DEFAULT_CACHE,
    lock_path: Path = DEFAULT_LOCK_PATH,
    years: Sequence[int] | None = None,
    filter_nonpositive: bool = False,
    clamp_crossed_ticks: bool = False,
    source_detail: str | None = None,
    waf_bypass_attempted: bool = False,
) -> dict[str, Any]:
    """Seal Dev-only (2018-2024) M1 OHLC arrays with honest provenance into Parquet + optional NPZ + fragment JSON.

    Supports all four canonical provenance tiers without disguising single-side or spread-reconstructed
    bars as true two-side Bid/Ask:
      - `DUKASCOPY_TRUE_BID_ASK`: native_Ask=True, has_true_bid_ask=True, 8 quote columns.
      - `FTMO_BID_PLUS_SPREAD`: native_Ask=False, has_true_bid_ask=False, 8 quote columns + spread_pts.
      - `QDM_PROVIDER_DEFAULT_SINGLE_SIDE`: native_Ask=False, has_true_bid_ask=False, 4 quote columns.
      - `HISTDATA_BID_ONLY`: native_Ask=False, has_true_bid_ask=False, 4 quote columns.
    """
    if waf_bypass_attempted is not False:
        raise ValueError("WAF_BYPASS_FORBIDDEN: waf_bypass_attempted MUST be False")

    lock_sha = verify_holdout_lock(lock_path)
    asset_u = _normalize_asset(asset)
    asset_l = asset_u.lower()
    eff_scale = _resolve_scale(asset_u, scale)

    prov, native_ask, has_true_bid_ask, ask_cols_present = _validate_provenance_flags(
        source_provenance,
        has_ask_input=(ask_ohlc is not None),
        has_spread_input=(spread_points is not None and point_size is not None),
        asset=asset_u,
    )

    ts_raw = np.asarray(times_sec)
    if ts_raw.ndim != 1 or ts_raw.size == 0:
        raise ValueError(f"INVALID_TIMESTAMPS [{asset_u}]: expected non-empty 1D array, got shape={ts_raw.shape}")
    if ts_raw.dtype == np.bool_ or not np.issubdtype(ts_raw.dtype, np.integer):
        raise HoldoutLockError(
            f"INVALID_TIMESTAMPS [{asset_u}]: expected integer UTC epoch seconds, got dtype={ts_raw.dtype}"
        )
    ts_arr = ts_raw.astype(np.int64, copy=True)

    # Hard Holdout guard BEFORE any filtering (active under python -O)
    enforce_pre_holdout_ts(ts_arr, START_SEC, STOP_SEC, context=f"seal_generic_m1_arrays:{asset_u}")
    if bool(np.any(ts_arr % 60 != 0)):
        raise ValueError(f"NON_MINUTE_ALIGNED_TIMESTAMPS [{asset_u}]: all M1 timestamps must be multiples of 60s")
    if ts_arr.size > 1 and not bool(np.all(np.diff(ts_arr) > 0)):
        raise ValueError(f"NON_MONOTONIC_TIMESTAMPS [{asset_u}]: timestamps must strictly increase")

    b_raw = np.asarray(bid_ohlc)
    if b_raw.ndim != 2 or b_raw.shape != (ts_arr.size, 4):
        raise ValueError(f"INVALID_OHLC_SHAPE [{asset_u}]: bid_ohlc shape {b_raw.shape} != ({ts_arr.size}, 4)")
    if b_raw.dtype == np.bool_ or not (
        np.issubdtype(b_raw.dtype, np.floating) or np.issubdtype(b_raw.dtype, np.integer)
    ):
        raise ValueError(f"INVALID_OHLC_DTYPE [{asset_u}]: bid_ohlc dtype={b_raw.dtype} rejected")
    b_arr = b_raw.astype(np.float64, copy=True)
    if not bool(np.all(np.isfinite(b_arr))):
        raise ValueError(f"NONFINITE_PRICE [{asset_u}]: NaN/Inf detected in bid_ohlc")

    sp_arr: np.ndarray | None = None
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
            raise ValueError(f"NONFINITE_SPREAD [{asset_u}]: NaN/Inf in spread_points")
        if bool(np.any(sp_arr < 0.0)):
            raise ValueError(f"NEGATIVE_SPREAD [{asset_u}]: spread_points < 0 detected")

    if ask_ohlc is not None:
        a_raw = np.asarray(ask_ohlc)
        if a_raw.ndim != 2 or a_raw.shape != (ts_arr.size, 4):
            raise ValueError(f"INVALID_OHLC_SHAPE [{asset_u}]: ask_ohlc shape {a_raw.shape} != ({ts_arr.size}, 4)")
        if a_raw.dtype == np.bool_ or not (
            np.issubdtype(a_raw.dtype, np.floating) or np.issubdtype(a_raw.dtype, np.integer)
        ):
            raise ValueError(f"INVALID_OHLC_DTYPE [{asset_u}]: ask_ohlc dtype={a_raw.dtype} rejected")
        a_arr = a_raw.astype(np.float64, copy=True)
        if not bool(np.all(np.isfinite(a_arr))):
            raise ValueError(f"NONFINITE_PRICE [{asset_u}]: NaN/Inf detected in ask_ohlc")
    elif prov == PROVENANCE_FTMO_BID_PLUS_SPREAD:
        if (
            sp_arr is None
            or point_size is None
            or isinstance(point_size, bool)
            or not isinstance(point_size, (int, float))
            or not math.isfinite(float(point_size))
            or float(point_size) <= 0.0
        ):
            raise ValueError(f"INVALID_POINT_SIZE [{asset_u}]: valid positive point_size and spread_points required")
        a_arr = b_arr + (sp_arr[:, None] * float(point_size))

    # Strict positive-price guard (supports Apr-2020 USOIL quarantine when filter_nonpositive=True)
    nonpos_mask = np.any(b_arr <= 0.0, axis=1)
    if a_arr is not None:
        nonpos_mask = nonpos_mask | np.any(a_arr <= 0.0, axis=1)
    nonpos_detected_total = int(np.sum(nonpos_mask))
    nonpos_filtered_total = 0
    if nonpos_detected_total > 0:
        bad_indices = np.flatnonzero(nonpos_mask)
        raw_min = float(np.min(b_arr[nonpos_mask]))
        if a_arr is not None:
            raw_min = min(raw_min, float(np.min(a_arr[nonpos_mask])))
        first_utc = _utc_iso(int(ts_arr[bad_indices[0]]))
        last_utc = _utc_iso(int(ts_arr[bad_indices[-1]]))
        if not filter_nonpositive:
            raise ValueError(
                f"NONPOSITIVE_PRICE_ANOMALY [{asset_u}]: detected {nonpos_detected_total} bar(s) with price <= 0.0 "
                f"(min_price={raw_min}, window={first_utc}..{last_utc})"
            )
        keep_mask = ~nonpos_mask
        ts_arr = ts_arr[keep_mask]
        b_arr = b_arr[keep_mask]
        if a_arr is not None:
            a_arr = a_arr[keep_mask]
        if sp_arr is not None:
            sp_arr = sp_arr[keep_mask]
        nonpos_filtered_total = nonpos_detected_total
        if ts_arr.size == 0:
            raise ValueError(f"All bars removed by filter_nonpositive in {asset_u}")

    # Strict intra-bar OHLC ordering: high >= max(open, close) >= min(open, close) >= low
    b_max_oc = np.maximum(b_arr[:, 0], b_arr[:, 3])
    b_min_oc = np.minimum(b_arr[:, 0], b_arr[:, 3])
    if bool(np.any(b_arr[:, 1] < b_max_oc)) or bool(np.any(b_arr[:, 2] > b_min_oc)):
        bad_idx = int(np.flatnonzero((b_arr[:, 1] < b_max_oc) | (b_arr[:, 2] > b_min_oc))[0])
        raise ValueError(
            f"OHLC_INTEGRITY_VIOLATION [{asset_u} bid row={bad_idx}]: "
            f"high >= max(open,close) >= min(open,close) >= low violated ({b_arr[bad_idx].tolist()})"
        )

    crossed_total = 0
    if a_arr is not None:
        a_max_oc = np.maximum(a_arr[:, 0], a_arr[:, 3])
        a_min_oc = np.minimum(a_arr[:, 0], a_arr[:, 3])
        if bool(np.any(a_arr[:, 1] < a_max_oc)) or bool(np.any(a_arr[:, 2] > a_min_oc)):
            bad_idx = int(np.flatnonzero((a_arr[:, 1] < a_max_oc) | (a_arr[:, 2] > a_min_oc))[0])
            raise ValueError(
                f"OHLC_INTEGRITY_VIOLATION [{asset_u} ask row={bad_idx}]: {a_arr[bad_idx].tolist()}"
            )
        crossed_mask = np.any(a_arr < b_arr, axis=1)
        crossed_cnt = int(np.sum(crossed_mask))
        if crossed_cnt > 0:
            if not clamp_crossed_ticks:
                raise ValueError(f"CROSSED_QUOTE_VIOLATION [{asset_u}]: {crossed_cnt} bar(s) have ask < bid")
            crossed_total = crossed_cnt
            a_arr = np.maximum(a_arr, b_arr)

    # Resolve target Dev years (all strictly in 2018..2024)
    if years is not None:
        req_years = tuple(int(y) for y in years)
        if not req_years:
            raise ValueError("years must not be empty")
        for y in req_years:
            if isinstance(y, bool) or y < 2018 or y > 2024:
                raise HoldoutLockError(f"HOLDOUT_OR_RANGE_BREACH: year {y} outside sealed Dev 2018-2024")
        year_list = req_years
    else:
        year_list = tuple(
            y
            for y in DEV_YEARS
            if int(np.searchsorted(ts_arr, _YEAR_BOUNDS_SEC[y][1], side="left"))
            > int(np.searchsorted(ts_arr, _YEAR_BOUNDS_SEC[y][0], side="left"))
        )
        if not year_list:
            raise ValueError(f"No Dev 2018-2024 bars found for {asset_u}")

    dst_dir = Path(cache_dir) / asset_l
    dst_dir.mkdir(parents=True, exist_ok=True)
    parquet_tag = _PROVENANCE_PARQUET_TAG[prov]

    years_meta: dict[str, dict[str, Any]] = {}
    total_minutes = 0
    total_bytes = 0
    global_min_price = math.inf
    global_max_price = -math.inf
    apr2020_summary: dict[str, Any] | None = None

    for y in year_list:
        y_start, y_stop = _YEAR_BOUNDS_SEC[y]
        lo_i = int(np.searchsorted(ts_arr, y_start, side="left"))
        hi_i = int(np.searchsorted(ts_arr, y_stop, side="left"))
        if hi_i <= lo_i:
            raise ValueError(f"No bars available for requested year {y} in {asset_u}")

        y_ts = ts_arr[lo_i:hi_i]
        y_mins = (y_ts // 60).astype(np.int64)
        y_b = b_arr[lo_i:hi_i]
        y_a = a_arr[lo_i:hi_i] if a_arr is not None else None
        y_sp = sp_arr[lo_i:hi_i] if sp_arr is not None else None

        enforce_pre_holdout_ts(y_ts, START_SEC, STOP_SEC, context=f"seal_generic_m1_arrays:{asset_u}:{y}")

        b_int = np.rint(y_b * eff_scale).astype(np.int64)
        if int(np.min(b_int)) <= 0:
            raise ValueError(f"Scaled integer bid price underflow <= 0 in {asset_u} {y} (scale={eff_scale})")

        cols: dict[str, np.ndarray] = {"minute": y_mins}
        for i, name in enumerate(("bo", "bh", "bl", "bc")):
            cols[name] = b_int[:, i]

        yr_min_price = float(np.min(y_b))
        yr_max_price = float(np.max(y_b))
        med_spread_raw: float | None = None
        med_spread_pts: float | None = None

        if y_a is not None:
            a_int = np.rint(y_a * eff_scale).astype(np.int64)
            if int(np.min(a_int)) <= 0:
                raise ValueError(f"Scaled integer ask price underflow <= 0 in {asset_u} {y} (scale={eff_scale})")
            if not bool(np.all(a_int >= b_int)):
                raise ValueError(f"Crossed scaled quote in {asset_u} {y}")
            for i, name in enumerate(("ao", "ah", "al", "ac")):
                cols[name] = a_int[:, i]
            if y_sp is not None:
                cols["spread_pts"] = np.rint(y_sp).astype(np.int64)
            yr_min_price = min(yr_min_price, float(np.min(y_a)))
            yr_max_price = max(yr_max_price, float(np.max(y_a)))
            med_spread_raw = float(np.median(y_a[:, 0] - y_b[:, 0]))
            med_spread_pts = float(np.median(a_int[:, 0] - b_int[:, 0]))

        pfile = dst_dir / f"{asset_u}-M1-{parquet_tag}-{y}.parquet"
        _atomic_write_parquet(pa.table(cols), pfile)
        p_sha = _sha256_file(pfile)
        p_bytes = int(pfile.stat().st_size)

        global_min_price = min(global_min_price, yr_min_price)
        global_max_price = max(global_max_price, yr_max_price)

        yr_entry: dict[str, Any] = {
            "parquet": pfile.name,
            "parquet_sha256": p_sha,
            "minutes": int(y_mins.size),
            "bytes": p_bytes,
            "min_price": round(yr_min_price, 6),
            "max_price": round(yr_max_price, 6),
            "source_provenance": prov,
        }
        if med_spread_raw is not None and med_spread_pts is not None:
            yr_entry["median_spread_raw"] = round(med_spread_raw, 6)
            yr_entry["median_spread_pts"] = round(med_spread_pts, 2)

        if y == 2020:
            apr_mask = (y_ts >= _APR_2020_START_SEC) & (y_ts < _APR_2020_STOP_SEC)
            if bool(np.any(apr_mask)):
                apr_min = float(np.min(y_b[apr_mask]))
                if y_a is not None:
                    apr_min = min(apr_min, float(np.min(y_a[apr_mask])))
                apr_min = round(apr_min, 6)
                apr_mins = int(np.sum(apr_mask))
                yr_entry["apr_2020_minutes"] = apr_mins
                yr_entry["apr_2020_min_price"] = apr_min
                apr2020_summary = {
                    "minutes": apr_mins,
                    "min_price": apr_min,
                    "nonpositive_detected": nonpos_detected_total,
                    "nonpositive_filtered": nonpos_filtered_total,
                }

        years_meta[str(y)] = yr_entry
        total_minutes += int(y_mins.size)
        total_bytes += p_bytes

    npz_sha256: str | None = None
    npz_path_str: str | None = None
    if npz_out is not None:
        npz_target = Path(npz_out)
        npz_payload: dict[str, np.ndarray] = {
            "times_sec": ts_arr,
            "bid_ohlc": b_arr,
            "scale": np.array(eff_scale, dtype=np.int64),
            "holdout_rows": np.array(0, dtype=np.int64),
            "waf_bypass_attempted": np.array(False, dtype=np.bool_),
            "native_ask": np.array(native_ask, dtype=np.bool_),
            "has_true_bid_ask": np.array(has_true_bid_ask, dtype=np.bool_),
            "ask_columns_present": np.array(ask_cols_present, dtype=np.bool_),
            "asset": np.array(asset_u, dtype="<U16"),
            "source_provenance": np.array(prov, dtype="<U48"),
        }
        if a_arr is not None:
            npz_payload["ask_ohlc"] = a_arr
        if sp_arr is not None:
            npz_payload["spread_points"] = sp_arr
        _atomic_write_npz(npz_payload, npz_target)
        npz_sha256 = _sha256_file(npz_target)
        npz_path_str = str(npz_target)

    fragment: dict[str, Any] = {
        "schema": "naqex-hot-m1-cache-fragment-v1",
        "utc": datetime.now(UTC).isoformat(),
        "source": source_detail or prov.lower(),
        "source_provenance": prov,
        "has_true_bid_ask": has_true_bid_ask,
        "ask_columns_present": ask_cols_present,
        "waf_bypass_attempted": WAF_BYPASS_ATTEMPTED,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_lock_sha256": lock_sha,
        "holdout_rows": 0,
        "holdout_rows_analysed": 0,
        "asset": asset_u,
        "dir": asset_l,
        "native_Ask": native_ask,
        "scale": eff_scale,
        "total_minutes": total_minutes,
        "total_bytes": total_bytes,
        "min_price": round(global_min_price, 6),
        "max_price": round(global_max_price, 6),
        "first_ts_utc": _utc_iso(int(ts_arr[0])),
        "last_ts_utc": _utc_iso(int(ts_arr[-1])),
        "max_ts_sec": int(ts_arr[-1]),
        "crossed_clamped_total": crossed_total,
        "nonpositive_detected_total": nonpos_detected_total,
        "nonpositive_filtered_total": nonpos_filtered_total,
        "nonpositive_anomaly_flagged": nonpos_detected_total > 0,
        "years": years_meta,
    }
    if apr2020_summary is not None:
        fragment["apr_2020_audit"] = apr2020_summary
    if npz_path_str is not None and npz_sha256 is not None:
        fragment["npz_path"] = npz_path_str
        fragment["npz_sha256"] = npz_sha256

    if fragment_out is not None:
        _atomic_write_json(Path(fragment_out), fragment)

    return fragment


def _validate_year_entry_and_parquet(
    asset: str,
    year_key: str,
    ym: Any,
    asset_dir: Path,
    *,
    verify_timestamps: bool,
) -> tuple[str, int, int]:
    """Validate one year entry in a manifest/fragment against its Parquet file on disk."""
    if not isinstance(ym, dict):
        raise ValueError(f"Malformed year entry for {asset} {year_key}")
    fname = ym.get("parquet")
    exp_sha = ym.get("parquet_sha256")
    exp_mins = ym.get("minutes")
    exp_bytes = ym.get("bytes")
    if not isinstance(fname, str) or not fname or "/" in fname or "\\" in fname or ".." in fname:
        raise ValueError(f"Unsafe parquet filename for {asset} {year_key}: {fname!r}")
    if not isinstance(exp_sha, str) or _SHA256_HEX_RE.fullmatch(exp_sha) is None:
        raise ValueError(f"Invalid parquet_sha256 for {asset} {year_key}: {exp_sha!r}")
    if isinstance(exp_mins, bool) or not isinstance(exp_mins, int) or exp_mins <= 0:
        raise ValueError(f"Invalid minutes count for {asset} {year_key}: {exp_mins!r}")
    if isinstance(exp_bytes, bool) or not isinstance(exp_bytes, int) or exp_bytes <= 0:
        raise ValueError(f"Invalid bytes count for {asset} {year_key}: {exp_bytes!r}")

    pfile = asset_dir / fname
    if not pfile.is_file():
        raise FileNotFoundError(f"Missing sealed parquet on disk for {asset} {year_key}: {pfile}")
    actual_bytes = int(pfile.stat().st_size)
    if actual_bytes != exp_bytes:
        raise ValueError(f"Parquet byte mismatch for {asset} {year_key}: expected={exp_bytes} actual={actual_bytes}")
    actual_sha = _sha256_file(pfile)
    if actual_sha != exp_sha:
        raise ValueError(f"Parquet SHA-256 mismatch for {asset} {year_key}: expected={exp_sha} actual={actual_sha}")

    if verify_timestamps:
        tbl = pq.read_table(pfile, columns=["minute"])
        mins = tbl["minute"].to_numpy()
        if int(len(mins)) != exp_mins:
            raise ValueError(f"Parquet row count mismatch for {asset} {year_key}: expected={exp_mins} got={len(mins)}")
        if len(mins) > 1 and not bool(np.all(np.diff(mins) > 0)):
            raise ValueError(f"Non-monotonic minute timestamps in parquet for {asset} {year_key}")
        enforce_pre_holdout_ts(mins * 60, START_SEC, STOP_SEC, context=f"merge_fragments:{asset}:{year_key}")

    return actual_sha, exp_mins, actual_bytes


def merge_fragments(
    fragments_dir: Path,
    *,
    cache_dir: Path = DEFAULT_CACHE,
    lock_path: Path = DEFAULT_LOCK_PATH,
    verify_existing_assets: bool = True,
    required_years: Sequence[int] | None = DEV_YEARS,
) -> dict[str, Any]:
    """Atomically merge `_fragments/*.json` into `manifest.json` with full SHA-256 & Holdout verification."""
    lock_sha = verify_holdout_lock(lock_path)
    frag_root = Path(fragments_dir)
    if not frag_root.is_dir():
        raise FileNotFoundError(f"Fragments directory not found: {frag_root}")

    frag_files = sorted(p for p in frag_root.glob("*.json") if p.is_file())
    if not frag_files:
        raise ValueError(f"No fragment JSON files found in {frag_root}")

    cache_root = Path(cache_dir)
    manifest_path = cache_root / "manifest.json"
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
        if not isinstance(manifest, dict) or not isinstance(manifest.get("assets"), dict):
            raise ValueError(f"Malformed existing manifest.json: {manifest_path}")
        enforce_holdout_zero_rows(manifest.get("holdout_rows"), context="merge_fragments.existing_manifest")
        if manifest.get("holdout_lock_sha256") != lock_sha:
            raise HoldoutLockError(
                f"Existing manifest holdout_lock_sha256 mismatch: {manifest.get('holdout_lock_sha256')!r}"
            )
        assets_map: dict[str, Any] = dict(manifest["assets"])
    else:
        manifest = {
            "schema": "naqex-hot-m1-cache-v1",
            "utc": datetime.now(UTC).isoformat(),
            "holdout_lock_sha256": lock_sha,
            "holdout_rows": 0,
            "elapsed_seconds": 0.0,
            "total_bytes": 0,
            "assets": {},
        }
        assets_map = {}

    req_year_keys: list[str] | None = [str(int(y)) for y in required_years] if required_years is not None else None
    merged_assets: list[str] = []
    seen_frag_assets: dict[str, str] = {}

    for frag_path in frag_files:
        frag = json.loads(frag_path.read_text(encoding="utf-8-sig"))
        if not isinstance(frag, dict):
            raise ValueError(f"Malformed fragment JSON object: {frag_path}")
        enforce_holdout_zero_rows(frag.get("holdout_rows"), context=f"merge_fragments:{frag_path.name}")
        if frag.get("holdout_lock_sha256") != lock_sha:
            raise HoldoutLockError(f"Fragment holdout_lock_sha256 mismatch in {frag_path.name}")
        if frag.get("waf_bypass_attempted", False) is not False:
            raise ValueError(f"Fragment {frag_path.name} has forbidden waf_bypass_attempted=True")

        raw_prov = frag.get("source_provenance")
        if raw_prov is None:
            # Backward-compatible path for pre-Wave4 paired Dukascopy fragments
            if frag.get("native_Ask") is not True:
                raise ValueError(f"Fragment {frag_path.name} must have native_Ask=true")
            frag_prov = PROVENANCE_DUKASCOPY_TRUE_BID_ASK
            frag_native_ask = True
            frag_has_true_bid_ask = True
            frag_ask_cols_present = True
        else:
            if not isinstance(raw_prov, str) or raw_prov not in VALID_SOURCE_PROVENANCES:
                raise ValueError(f"Fragment {frag_path.name} has invalid source_provenance={raw_prov!r}")
            frag_prov = raw_prov
            if frag_prov == PROVENANCE_DUKASCOPY_TRUE_BID_ASK:
                if frag.get("native_Ask") is not True:
                    raise ValueError(f"Fragment {frag_path.name} ({frag_prov}) must have native_Ask=true")
                frag_native_ask = True
                frag_has_true_bid_ask = True
                frag_ask_cols_present = True
            else:
                # Fail closed against spoofing single-side or reconstructed Ask as native true Bid/Ask
                if frag.get("native_Ask") is not False:
                    raise ValueError(
                        f"PROVENANCE_SPOOF_BLOCKED [{frag_path.name}]: {frag_prov} MUST have native_Ask=false"
                    )
                if frag.get("has_true_bid_ask") is True:
                    raise ValueError(
                        f"PROVENANCE_SPOOF_BLOCKED [{frag_path.name}]: {frag_prov} MUST NOT set has_true_bid_ask=true"
                    )
                frag_native_ask = False
                frag_has_true_bid_ask = False
                frag_ask_cols_present = frag_prov == PROVENANCE_FTMO_BID_PLUS_SPREAD

        asset_u = _normalize_asset(str(frag.get("asset", "")))
        asset_dir_name = str(frag.get("dir", "")).strip()
        if asset_dir_name != asset_u.lower():
            raise ValueError(f"Fragment {frag_path.name} dir={asset_dir_name!r} != {asset_u.lower()!r}")
        scale_val = frag.get("scale")
        if isinstance(scale_val, bool) or not isinstance(scale_val, int) or scale_val <= 0:
            raise ValueError(f"Fragment {frag_path.name} invalid scale={scale_val!r}")
        min_px = frag.get("min_price")
        if min_px is not None:
            if (
                isinstance(min_px, bool)
                or not isinstance(min_px, (int, float))
                or not math.isfinite(float(min_px))
                or float(min_px) <= 0.0
            ):
                raise ValueError(f"Fragment {frag_path.name} has invalid min_price={min_px!r}")

        frag_sha = _sha256_file(frag_path)
        if asset_u in seen_frag_assets and seen_frag_assets[asset_u] != frag_sha:
            raise ValueError(f"Conflicting duplicate fragments for asset {asset_u} ({frag_path.name})")
        seen_frag_assets[asset_u] = frag_sha

        frag_years = frag.get("years")
        if not isinstance(frag_years, dict) or not frag_years:
            raise ValueError(f"Fragment {frag_path.name} missing years map")
        if req_year_keys is not None:
            missing_yrs = [yk for yk in req_year_keys if yk not in frag_years]
            if missing_yrs:
                raise ValueError(f"Fragment {frag_path.name} ({asset_u}) missing required years: {missing_yrs}")
            target_year_keys = req_year_keys
        else:
            target_year_keys = sorted(str(k) for k in frag_years)
            for yk in target_year_keys:
                yi = int(yk)
                if yi < 2018 or yi > 2024:
                    raise HoldoutLockError(f"HOLDOUT_OR_RANGE_BREACH in {frag_path.name}: year {yk}")

        asset_folder = cache_root / asset_dir_name
        clean_years: dict[str, dict[str, Any]] = {}
        for yk in target_year_keys:
            ym = frag_years[yk]
            _validate_year_entry_and_parquet(
                asset_u,
                yk,
                ym,
                asset_folder,
                verify_timestamps=True,
            )
            year_out: dict[str, Any] = {
                "parquet": ym["parquet"],
                "parquet_sha256": ym["parquet_sha256"],
                "minutes": int(ym["minutes"]),
                "bytes": int(ym["bytes"]),
            }
            for opt_k in (
                "min_price",
                "median_spread_pts",
                "crossed_clamped",
                "nonpositive_filtered",
                "source_provenance",
            ):
                if opt_k in ym:
                    year_out[opt_k] = ym[opt_k]
            clean_years[yk] = year_out

        assets_map[asset_u] = {
            "dir": asset_dir_name,
            "native_Ask": frag_native_ask,
            "has_true_bid_ask": frag_has_true_bid_ask,
            "ask_columns_present": frag_ask_cols_present,
            "source_provenance": frag_prov,
            "waf_bypass_attempted": False,
            "scale": scale_val,
            "source_manifest_sha256": frag_sha,
            "years": clean_years,
        }
        if asset_u not in merged_assets:
            merged_assets.append(asset_u)

    # Fail-closed SHA-256 verification across ALL assets in final manifest
    verified_assets = 0
    for asset_key, am in sorted(assets_map.items()):
        if not isinstance(am, dict) or not isinstance(am.get("years"), dict):
            raise ValueError(f"Malformed manifest entry for asset {asset_key}")
        if not verify_existing_assets and asset_key not in seen_frag_assets:
            continue
        folder = cache_root / str(am["dir"])
        for yk, ym in sorted(am["years"].items()):
            if int(yk) >= 2025:
                raise HoldoutLockError(f"HOLDOUT_CONTAMINATION in manifest: {asset_key} year {yk}")
            _validate_year_entry_and_parquet(
                asset_key,
                yk,
                ym,
                folder,
                verify_timestamps=(asset_key in seen_frag_assets),
            )
        verified_assets += 1

    manifest["assets"] = assets_map
    manifest["holdout_lock_sha256"] = lock_sha
    manifest["holdout_rows"] = 0
    manifest["utc"] = datetime.now(UTC).isoformat()
    manifest["total_bytes"] = int(
        sum(int(ym["bytes"]) for am in assets_map.values() for ym in am["years"].values())
    )
    _atomic_write_json(manifest_path, manifest)

    return {
        "status": "MERGED_AND_VERIFIED",
        "manifest_path": str(manifest_path),
        "merged_assets": sorted(merged_assets),
        "merged_count": len(merged_assets),
        "total_assets": len(assets_map),
        "verified_assets": verified_assets,
        "total_bytes": manifest["total_bytes"],
        "holdout_rows": 0,
        "holdout_lock_sha256": lock_sha,
        "order_send_count": ORDER_SEND_COUNT,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--seal", action="store_true", help="Seal 7 Dev (2018-2024) M1 Bid/Ask Parquets for one asset.")
    mode.add_argument(
        "--merge-fragments",
        type=Path,
        metavar="DIR",
        help="Atomically merge isolated fragment JSONs from DIR into .runtime/hot-m1-cache/manifest.json.",
    )
    parser.add_argument("--asset", type=str, help="Uppercase asset symbol (e.g. US30, USOIL, USDCHF).")
    parser.add_argument("--raw-dir", type=Path, help="Directory holding <asset_lower>-m1-{bid,ask}-<year>.json files.")
    parser.add_argument(
        "--scale",
        type=int,
        default=None,
        help="Integer price scale (100000 FX, 1000 JPY/Idx/Oil/XAG).",
    )
    parser.add_argument("--fragment-out", type=Path, default=None, help="Isolated fragment JSON output path.")
    parser.add_argument("--cache-dir", type=Path, default=DEFAULT_CACHE, help="Hot M1 cache root directory.")
    parser.add_argument(
        "--filter-nonpositive",
        action="store_true",
        help="Quarantine raw bars with price <= 0.0 (flagged in fragment metadata) instead of aborting.",
    )
    parser.add_argument(
        "--skip-existing-sha",
        action="store_true",
        help="With --merge-fragments: skip re-hashing pre-existing non-fragment assets (default verifies ALL).",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    if args.seal:
        if not args.asset or args.raw_dir is None or args.fragment_out is None:
            raise ValueError("--seal requires --asset, --raw-dir, and --fragment-out")
        res = seal_asset(
            args.asset,
            args.raw_dir,
            args.scale,
            fragment_out=args.fragment_out,
            cache_dir=args.cache_dir,
            filter_nonpositive=bool(args.filter_nonpositive),
        )
        print(
            f"SEAL_OK asset={res['asset']} minutes={res['total_minutes']} "
            f"min_price={res['min_price']} holdout_rows={res['holdout_rows']} "
            f"fragment={args.fragment_out}",
            flush=True,
        )
        return 0

    summary = merge_fragments(
        args.merge_fragments,
        cache_dir=args.cache_dir,
        verify_existing_assets=not bool(args.skip_existing_sha),
    )
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
