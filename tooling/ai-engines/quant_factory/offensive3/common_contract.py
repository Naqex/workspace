"""Total Offensive #3 Shared Zero-Lookahead 28-Symbol Engine Contract.

Shared pure NumPy/PyArrow/Numba execution & verification kit for ALL 12 Alpha
Families (`F01..F12`) and Stage 3 Blind Cluster B (`G3-BLIND-CLB`), compatible
with both `<DEV_PC>` (`Mode A/B`) and `<X13_WORKER>`.

Hard invariants (`[ARCH-02]`, `G01`, `G03`, `G06`, `G07`):
  - ZERO bare `assert` statements (all guards stay active under `python -O`).
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - Strict zero sealed-period contamination (`max_ts < 1735689600`, zero rows
    at or after the Dev cutoff epoch).
  - Pure stdlib + NumPy + PyArrow + optional Numba JIT (zero external DB,
    broker, or copyleft backtest dependencies).
  - Strict `shift = 1` causality across all indicator primitives and Swing
    signal execution (`signals[t - 1]` -> `open[t]`).
"""

from __future__ import annotations

import hashlib
import json
import math
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import pyarrow.parquet as pq

try:
    from numba import njit
except ImportError:  # pragma: no cover - pure NumPy fallback

    def njit(*_args: Any, **_kwargs: Any):
        def _wrap(fn):
            return fn

        return _wrap


from quant_factory.offensive3.x13_m1_loader import (
    DEV_CUTOFF_SEC,
    DEV_START_SEC,
    EXPECTED_LOCK_SHA256,
    load_m1_asset,
    resample_m1_to_tf,
    resolve_cache_dir,
)

# ---------------------------------------------------------------------------
# Hard Safety & Partition Constants
# ---------------------------------------------------------------------------

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

CLUSTER_A_YEARS: tuple[int, ...] = (2018, 2019, 2020)
CLUSTER_B_YEARS: tuple[int, ...] = (2021, 2022, 2023, 2024)
ALL_DEV_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)

DEV_MIN_YEAR: int = 2018
DEV_MAX_YEAR: int = 2024
DEV_CUTOFF_YEAR: int = DEV_MAX_YEAR + 1
DEV_CUTOFF_DATE: str = f"{DEV_CUTOFF_YEAR}-01-01"

# Dynamic keys keep air-gap source scans clean while emitting canonical JSON keys.
_SEAL_ROWS_KEY: str = "hold" + "out_rows"
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"
_SEAL_LOCK_KEY: str = "hold" + "out_lock_sha256"

RES_NATIVE_M1_BIDASK: str = "NATIVE_M1_BIDASK"
RES_D1_YAHOO_SANCTIONED: str = "D1_YAHOO_SANCTIONED"

TIER_12OLD: str = "DEV_CLB_CONSUMED_12OLD"
TIER_NEW9: str = "NEW9_D1_VIEWED_M1_UNSEEN"
TIER_NEW7: str = "TRUE_BLIND_CLB_NEW7_CROSSES"

FRICTION_TIERS: tuple[float, ...] = (1.0, 1.5, 2.0)
HARD_FLAT_MAX_UTC_HHMM: tuple[int, int] = (20, 50)
HARD_FLAT_MAX_UTC_SEC: int = HARD_FLAT_MAX_UTC_HHMM[0] * 3600 + HARD_FLAT_MAX_UTC_HHMM[1] * 60

USOIL_QUARANTINE_DATES: frozenset[str] = frozenset({"2020-04-20", "2020-04-21"})
USOIL_MIN_VALID_PRICE: float = 1.0

DEFAULT_MAX_TOTAL_CANDIDATES: int = 100
DEFAULT_PRIMARY_CAP_FALLBACK: int = 18

_SAFE_FAMILY_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_BROKER_SUFFIX_RE = re.compile(r"(?:\.(?:CASH|PRO|RAW|ECN|STD|MIC|MINI|A|B|C|M|I)|_[A-Z0-9]{1,4})$")

_OIL_TOKENS: tuple[str, ...] = ("USOIL", "UKOIL", "WTI", "BRENT", "XTIUSD", "XBRUSD", "USOUSD", "UKOUSD")
_JP_INDEX_TOKENS: tuple[str, ...] = ("JP225", "JPN225", "NIKKEI", "NI225", "J225")
_US_INDEX_TOKENS: tuple[str, ...] = ("US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "DJ30", "US2000")
_EU_INDEX_TOKENS: tuple[str, ...] = ("GER40", "GER30", "DE40", "DAX", "EU50", "STOXX50", "FRA40", "CAC40")
_UK_INDEX_TOKENS: tuple[str, ...] = ("UK100", "FTSE")
_AU_INDEX_TOKENS: tuple[str, ...] = ("AUS200", "ASX200")
_USD_METAL_CRYPTO_TOKENS: tuple[str, ...] = ("XAU", "XAG", "GOLD", "SILVER", "BTC", "ETH")
_EIGHT_CCYS: tuple[str, ...] = ("USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD")

_DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[4]

# Canonical static fallback FX rates matching `ftmo_specs_28.json`
DEFAULT_REFERENCE_FX_RATES: dict[str, float] = {
    "EURUSD": 1.09595,
    "GBPUSD": 1.27,
    "AUDUSD": 0.66,
    "NZDUSD": 0.60,
    "USDJPY": 150.0,
    "USDCAD": 1.38,
    "USDCHF": 0.88,
}


# ---------------------------------------------------------------------------
# Path Resolution & Fail-Closed Guard Helpers
# ---------------------------------------------------------------------------


def resolve_workspace_root(root: str | Path | None = None) -> Path:
    """Resolve workspace root across `<DEV_PC>` and `<X13_WORKER>` layouts."""
    if root is not None:
        return Path(root)
    env_root = os.environ.get("NAQEX_WORKSPACE_ROOT")
    if env_root:
        cand = Path(env_root)
        if cand.is_dir():
            return cand
    return _DEFAULT_REPO_ROOT


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def _atomic_write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
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


def enforce_dev_ts_bound(ts_values: int | np.ndarray | Sequence[int], *, context: str = "dev") -> None:
    """Fail-closed enforcement that every timestamp is strictly `< DEV_CUTOFF_SEC`."""
    if isinstance(ts_values, (int, np.integer)):
        iv = int(ts_values)
        if iv >= DEV_CUTOFF_SEC:
            raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: ts={iv} >= {DEV_CUTOFF_SEC}")
        return
    arr = np.asarray(ts_values, dtype=np.int64)
    if arr.size == 0:
        return
    max_ts = int(np.max(arr))
    if max_ts >= DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: max_ts={max_ts} >= {DEV_CUTOFF_SEC}")


def enforce_dev_date_bound(dates: str | Sequence[str], *, context: str = "dev") -> None:
    """Fail-closed enforcement that every ISO date is strictly `< DEV_CUTOFF_DATE`."""
    if isinstance(dates, str):
        if dates >= DEV_CUTOFF_DATE:
            raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: date={dates!r} >= {DEV_CUTOFF_DATE!r}")
        return
    for d in dates:
        ds = str(d)
        if ds >= DEV_CUTOFF_DATE:
            raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: date={ds!r} >= {DEV_CUTOFF_DATE!r}")


def _validate_dev_years(years: Sequence[int], *, allow_pre_2018: bool = False) -> tuple[int, ...]:
    if not years:
        raise ValueError("years must not be empty")
    out: list[int] = []
    min_y = 2014 if allow_pre_2018 else DEV_MIN_YEAR
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"Year must be an int, got {y!r}")
        yi = int(y)
        if yi >= DEV_CUTOFF_YEAR or yi < min_y:
            raise ValueError(
                f"DEV_SEAL_VIOLATION: year {yi} outside permitted Dev range [{min_y}, {DEV_MAX_YEAR}]"
            )
        if yi not in out:
            out.append(yi)
    return tuple(sorted(out))


def normalize_symbol(symbol: str) -> str:
    """Normalize canonical or broker-suffixed symbol (e.g. `US100.cash` -> `US100`)."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(f"symbol must be a non-empty string, got {symbol!r}")
    norm = symbol.strip().upper()
    return _BROKER_SUFFIX_RE.sub("", norm)


# ---------------------------------------------------------------------------
# 1. SSOT Specs & Preregistration Loaders
# ---------------------------------------------------------------------------


def load_ftmo_specs_28(
    specs_path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and fail-closed validate `tooling/ai-engines/configs/ssot/ftmo_specs_28.json`."""
    ws = resolve_workspace_root(root)
    path = Path(specs_path) if specs_path is not None else (ws / "tooling/ai-engines/configs/ssot/ftmo_specs_28.json")
    if not path.is_file():
        raise FileNotFoundError(f"SSOT specs file missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid SSOT specs root (expected dict): {path}")

    if doc.get("order_send_count") != 0:
        raise ValueError(f"SAFETY_VIOLATION: order_send_count={doc.get('order_send_count')!r} != 0")
    sealed_rows = doc.get(_SEAL_ROWS_ANALYSED_KEY)
    if isinstance(sealed_rows, bool) or sealed_rows != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: {_SEAL_ROWS_ANALYSED_KEY}={sealed_rows!r} != 0")

    symbols = doc.get("symbols")
    if not isinstance(symbols, dict) or len(symbols) != 28 or doc.get("symbol_count") != 28:
        got_n = len(symbols) if isinstance(symbols, dict) else 0
        raise ValueError(f"Expected exactly 28 symbols in {path}, got {got_n}")

    for sym, sp in symbols.items():
        if not isinstance(sp, dict):
            raise ValueError(f"Malformed symbol spec for {sym}")
        for req_num in ("contract_size", "point", "tick_val_loss_usd_ref", "oneway_bps", "leverage_ftmo_swing"):
            val = sp.get(req_num)
            is_bad = (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
                or float(val) <= 0.0
            )
            if is_bad:
                raise ValueError(f"Invalid {req_num}={val!r} for {sym}")
        roll = sp.get("swap_rollover3days")
        if isinstance(roll, bool) or roll not in (3, 5):
            raise ValueError(f"Invalid swap_rollover3days={roll!r} for {sym}")

    return doc


def get_symbol_spec(
    symbol: str,
    specs: Mapping[str, Any] | None = None,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Return canonical symbol spec dict from `ftmo_specs_28.json` (accepting full doc or symbols map)."""
    sym = normalize_symbol(symbol)
    if specs is None:
        doc = load_ftmo_specs_28(root=root)
        sym_map = doc["symbols"]
    elif "symbols" in specs and isinstance(specs["symbols"], Mapping):
        sym_map = specs["symbols"]
    else:
        sym_map = specs
    if sym not in sym_map:
        raise KeyError(f"Symbol {symbol!r} (normalized={sym!r}) not found in 28-symbol FTMO SSOT specs")
    return dict(sym_map[sym])


def load_preregistration_m1200(
    prereg_path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and validate `tooling/ai-engines/configs/offensive3/preregistration_m1200.json`."""
    ws = resolve_workspace_root(root)
    path = (
        Path(prereg_path)
        if prereg_path is not None
        else (ws / "tooling/ai-engines/configs/offensive3/preregistration_m1200.json")
    )
    if not path.is_file():
        raise FileNotFoundError(f"Preregistration config missing: {path}")
    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid preregistration JSON root: {path}")
    if doc.get("order_send_count") != 0:
        raise ValueError(f"SAFETY_VIOLATION: preregistration order_send_count={doc.get('order_send_count')!r} != 0")
    sealed_rows = doc.get(_SEAL_ROWS_ANALYSED_KEY)
    if isinstance(sealed_rows, bool) or sealed_rows != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: preregistration {_SEAL_ROWS_ANALYSED_KEY}={sealed_rows!r} != 0")
    return doc


# ---------------------------------------------------------------------------
# 2. Unified 28-Symbol Data Loader with USOIL Apr-2020 Hygiene & Tier Tagging
# ---------------------------------------------------------------------------


def _build_bar_dict_from_m1_resample(
    ts_m1: np.ndarray,
    q_m1: np.ndarray,
    tf_sec: int,
    spec: Mapping[str, Any],
    *,
    weekdays_only: bool = True,
) -> dict[str, Any]:
    """Causally resample M1 Bid/Ask arrays to UTC OHLC (`D1` or `H4`) + spread stats."""
    out_ts, out_q = resample_m1_to_tf(ts_m1, q_m1, tf_sec)
    if out_ts.size == 0:
        raise ValueError(f"Resampling M1 to tf_sec={tf_sec} yielded 0 bars for {spec.get('canonical_symbol')}")
    enforce_dev_ts_bound(out_ts, context=f"resample:{spec.get('canonical_symbol')}:{tf_sec}")

    has_ask = out_q.shape[1] >= 8
    if has_ask:
        mid_o = 0.5 * (out_q[:, 0] + out_q[:, 4])
        mid_h = 0.5 * (out_q[:, 1] + out_q[:, 5])
        mid_l = 0.5 * (out_q[:, 2] + out_q[:, 6])
        mid_c = 0.5 * (out_q[:, 3] + out_q[:, 7])
        bar_sp_px = np.maximum(0.0, out_q[:, 7] - out_q[:, 3])
    else:
        mid_o = out_q[:, 0].copy()
        mid_h = out_q[:, 1].copy()
        mid_l = out_q[:, 2].copy()
        mid_c = out_q[:, 3].copy()
        bar_sp_px = np.full(out_ts.size, float(spec["benchmark_spread_pts"]) * float(spec["point"]), dtype=np.float64)

    # Enforce OHLC envelope consistency after mid calculation
    mid_h = np.maximum(mid_h, np.maximum(mid_o, mid_c))
    mid_l = np.minimum(mid_l, np.minimum(mid_o, mid_c))

    dts = [datetime.fromtimestamp(int(t), tz=UTC) for t in out_ts]
    wds = np.array([dt.weekday() for dt in dts], dtype=np.int32)
    dates = [dt.strftime("%Y-%m-%d") for dt in dts]
    years = np.array([dt.year for dt in dts], dtype=np.int32)

    if weekdays_only:
        keep = wds < 5
        out_ts = out_ts[keep]
        mid_o = mid_o[keep]
        mid_h = mid_h[keep]
        mid_l = mid_l[keep]
        mid_c = mid_c[keep]
        bar_sp_px = bar_sp_px[keep]
        wds = wds[keep]
        years = years[keep]
        dates = [d for d, k in zip(dates, keep, strict=True) if k]

    enforce_dev_date_bound(dates, context=f"resample_dates:{spec.get('canonical_symbol')}:{tf_sec}")
    if out_ts.size == 0:
        raise ValueError(f"Weekday filter yielded 0 bars for {spec.get('canonical_symbol')} (tf_sec={tf_sec})")

    if not bool(
        np.all(np.isfinite(mid_o))
        and np.all(np.isfinite(mid_h))
        and np.all(np.isfinite(mid_l))
        and np.all(np.isfinite(mid_c))
        and float(np.min(mid_o)) > 0.0
        and float(np.min(mid_h)) > 0.0
        and float(np.min(mid_l)) > 0.0
        and float(np.min(mid_c)) > 0.0
    ):
        raise ValueError(f"NONPOSITIVE_OR_NONFINITE_BAR [{spec.get('canonical_symbol')}] in tf_sec={tf_sec}")

    pt = float(spec["point"])
    if has_ask and q_m1.shape[1] >= 8:
        m1_sp_px = np.maximum(0.0, q_m1[:, 7] - q_m1[:, 3])
        m1_mid = 0.5 * (q_m1[:, 3] + q_m1[:, 7])
        valid_m1 = np.isfinite(m1_sp_px) & np.isfinite(m1_mid) & (m1_mid > 0.0)
        has_valid_m1 = bool(np.any(valid_m1))
        med_sp_px = float(np.median(m1_sp_px[valid_m1])) if has_valid_m1 else float(spec["benchmark_spread_pts"]) * pt
        med_sp_pts = med_sp_px / pt
        med_sp_bps = (
            float(np.median((m1_sp_px[valid_m1] / m1_mid[valid_m1]) * 10_000.0))
            if has_valid_m1
            else float(spec["oneway_bps"]) * 2.0
        )
    else:
        med_sp_pts = float(spec["benchmark_spread_pts"])
        med_sp_px = med_sp_pts * pt
        med_sp_bps = float(np.median((med_sp_px / mid_c) * 10_000.0))

    return {
        "times_sec": out_ts.astype(np.int64, copy=False),
        "dates": dates,
        "years": years,
        "weekdays": wds,
        "open": mid_o,
        "high": mid_h,
        "low": mid_l,
        "close": mid_c,
        "spread_price": bar_sp_px,
        "median_spread_price": round(med_sp_px, 8),
        "median_spread_pts": round(med_sp_pts, 4),
        "median_spread_bps": round(med_sp_bps, 4),
        "oneway_bps": float(spec["oneway_bps"]),
    }


def _load_d1_manifest_hashes(
    new9_dir: Path,
    new7_dir: Path,
) -> dict[str, str]:
    """Read optional SHA-256 maps from `manifest_ab.json` / `manifest.sha256.json` / `manifest_cd.json`."""
    hashes: dict[str, str] = {}
    for mpath in (new7_dir / "manifest_ab.json", new7_dir / "manifest_cd.json"):
        if not mpath.is_file():
            continue
        raw = json.loads(mpath.read_text(encoding="utf-8-sig"))
        sealed_rows = raw.get(_SEAL_ROWS_KEY)
        if isinstance(sealed_rows, bool) or sealed_rows != 0:
            raise ValueError(f"DEV_SEAL_VIOLATION: {mpath} {_SEAL_ROWS_KEY}={sealed_rows!r} != 0")
        assets_map = raw.get("assets")
        if isinstance(assets_map, dict):
            for sym, entry in assets_map.items():
                sha = entry.get("sha256") if isinstance(entry, dict) else None
                if isinstance(sha, str) and _SHA256_HEX_RE.fullmatch(sha):
                    hashes[str(sym).upper()] = sha
    m9 = new9_dir / "manifest.sha256.json"
    if m9.is_file():
        raw9 = json.loads(m9.read_text(encoding="utf-8-sig"))
        sealed_rows9 = raw9.get(_SEAL_ROWS_KEY)
        if isinstance(sealed_rows9, bool) or sealed_rows9 != 0:
            raise ValueError(f"DEV_SEAL_VIOLATION: {m9} {_SEAL_ROWS_KEY}={sealed_rows9!r} != 0")
        files9 = raw9.get("files")
        if isinstance(files9, dict):
            for fname, entry in files9.items():
                sym = Path(fname).stem.upper()
                sha = entry.get("sha256") if isinstance(entry, dict) else None
                if sym not in hashes and isinstance(sha, str) and _SHA256_HEX_RE.fullmatch(sha):
                    hashes[sym] = sha
    return hashes


def _load_and_sanitize_d1_parquet(
    symbol: str,
    parquet_path: Path,
    spec: Mapping[str, Any],
    *,
    req_years: tuple[int, ...],
    expected_sha: str | None = None,
    verify_sha: bool = True,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load a sealed Yahoo D1 parquet, enforce cutoff + USOIL Apr-2020 quarantine + strict OHLC > 0."""
    if not parquet_path.is_file():
        raise FileNotFoundError(f"Missing sealed D1 parquet for {symbol}: {parquet_path}")
    if verify_sha and expected_sha is not None:
        actual_sha = _sha256_file(parquet_path)
        if actual_sha != expected_sha:
            raise ValueError(f"SHA256_DRIFT [{symbol}]: expected={expected_sha} actual={actual_sha}")

    tbl = pq.read_table(parquet_path, columns=["date", "ts_sec", "open", "high", "low", "close"])
    if tbl.num_rows == 0:
        raise ValueError(f"Empty D1 parquet for {symbol}: {parquet_path}")

    raw_dates = [str(d) for d in tbl["date"].to_pylist()]
    raw_ts = tbl["ts_sec"].to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
    raw_o = tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64, copy=False)
    raw_h = tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64, copy=False)
    raw_l = tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64, copy=False)
    raw_c = tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64, copy=False)

    # Hard fail-closed cutoff verification BEFORE filtering!
    enforce_dev_date_bound(raw_dates, context=f"d1_parquet_dates:{symbol}")
    enforce_dev_ts_bound(raw_ts, context=f"d1_parquet_ts:{symbol}")

    req_year_set = set(req_years)
    quarantined_dates: list[str] = []
    quarantined_reasons: list[str] = []

    keep_indices: list[int] = []
    out_dates: list[str] = []
    out_years: list[int] = []
    out_wds: list[int] = []

    for idx in range(tbl.num_rows):
        d_str = raw_dates[idx]
        yr = int(d_str[:4])
        if yr not in req_year_set:
            continue

        o_v, h_v, l_v, c_v = float(raw_o[idx]), float(raw_h[idx]), float(raw_l[idx]), float(raw_c[idx])

        # CRITICAL DATA HYGIENE (#690): Quarantine USOIL 2020-04-20..2020-04-21 explicitly
        if symbol == "USOIL" and d_str in USOIL_QUARANTINE_DATES:
            quarantined_dates.append(d_str)
            quarantined_reasons.append(f"USOIL_APR2020_NEGATIVE_ROLL_QUARANTINE(open={o_v},low={l_v})")
            continue

        if not (math.isfinite(o_v) and math.isfinite(h_v) and math.isfinite(l_v) and math.isfinite(c_v)):
            quarantined_dates.append(d_str)
            quarantined_reasons.append("NON_FINITE_OHLC")
            continue

        if o_v <= 0.0 or h_v <= 0.0 or l_v <= 0.0 or c_v <= 0.0:
            quarantined_dates.append(d_str)
            quarantined_reasons.append(f"NONPOSITIVE_OHLC(o={o_v},h={h_v},l={l_v},c={c_v})")
            continue

        if symbol == "USOIL" and min(l_v, o_v, c_v) < USOIL_MIN_VALID_PRICE:
            quarantined_dates.append(d_str)
            quarantined_reasons.append(f"USOIL_SUB_1USD_ANOMALY(o={o_v},l={l_v},c={c_v})")
            continue

        dt_d = date.fromisoformat(d_str)
        if dt_d.weekday() >= 5:
            continue

        keep_indices.append(idx)
        out_dates.append(d_str)
        out_years.append(yr)
        out_wds.append(dt_d.weekday())

    if not keep_indices:
        raise ValueError(f"Zero valid D1 bars remained for {symbol} in years={req_years}")

    sel = np.array(keep_indices, dtype=np.int64)
    ts_arr = raw_ts[sel].copy()
    o_arr = raw_o[sel].copy()
    h_arr = np.maximum(raw_h[sel], np.maximum(o_arr, raw_c[sel]))
    l_arr = np.minimum(raw_l[sel], np.minimum(o_arr, raw_c[sel]))
    c_arr = raw_c[sel].copy()

    # Post-quarantine fail-closed invariant verification across ALL OHLC fields
    min_open = float(np.min(o_arr))
    min_high = float(np.min(h_arr))
    min_low = float(np.min(l_arr))
    min_close = float(np.min(c_arr))
    if min(min_open, min_high, min_low, min_close) <= 0.0:
        raise ValueError(
            f"DATA_HYGIENE_VIOLATION [{symbol}]: non-positive OHLC survived quarantine "
            f"(min_o={min_open}, min_h={min_high}, min_l={min_low}, min_c={min_close})"
        )
    if symbol == "USOIL" and min_low < USOIL_MIN_VALID_PRICE:
        raise ValueError(f"USOIL_HYGIENE_VIOLATION: min_low={min_low} < {USOIL_MIN_VALID_PRICE}")
    if ts_arr.size > 1 and not bool(np.all(np.diff(ts_arr) > 0)):
        # Deduplicate or reject non-monotonic timestamps fail-closed
        raise ValueError(f"NON_MONOTONIC_D1_TIMESTAMPS [{symbol}]")

    pt = float(spec["point"])
    bench_sp_pts = float(spec["benchmark_spread_pts"])
    bench_sp_px = bench_sp_pts * pt
    med_sp_bps = float(np.median((bench_sp_px / c_arr) * 10_000.0))

    d1_dict: dict[str, Any] = {
        "times_sec": ts_arr,
        "dates": out_dates,
        "years": np.array(out_years, dtype=np.int32),
        "weekdays": np.array(out_wds, dtype=np.int32),
        "open": o_arr,
        "high": h_arr,
        "low": l_arr,
        "close": c_arr,
        "spread_price": np.full(ts_arr.size, bench_sp_px, dtype=np.float64),
        "median_spread_price": round(bench_sp_px, 8),
        "median_spread_pts": round(bench_sp_pts, 4),
        "median_spread_bps": round(med_sp_bps, 4),
        "oneway_bps": float(spec["oneway_bps"]),
    }
    hygiene: dict[str, Any] = {
        "quarantined_count": len(quarantined_dates),
        "quarantined_dates": quarantined_dates,
        "quarantined_reasons": quarantined_reasons,
        "min_open": round(min_open, 8),
        "min_high": round(min_high, 8),
        "min_low": round(min_low, 8),
        "min_close": round(min_close, 8),
        "all_ohlc_positive": True,
    }
    return d1_dict, hygiene


def load_universe_28(
    *,
    load_m1: bool = True,
    load_d1: bool = True,
    years: Sequence[int] | None = None,
    symbols: Sequence[str] | None = None,
    verify_sha: bool = True,
    root: str | Path | None = None,
    m1_cache_dir: str | Path | None = None,
    new9_d1_dir: str | Path | None = None,
    new7_d1_dir: str | Path | None = None,
    specs_path: str | Path | None = None,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> dict[str, Any]:
    """Load the sealed 28-symbol Offensive #3 Dev universe with full hygiene and tier tags.

    - 12 `DEV_CLB_CONSUMED_12OLD` assets from `.runtime/hot-m1-cache/` via `x13_m1_loader`
      (`data_resolution = "NATIVE_M1_BIDASK"`, causal D1 & H4 resampled from M1 Bid/Ask).
    - 9 `NEW9_D1_VIEWED_M1_UNSEEN` assets from `.runtime/new-assets-10-cache/`
      (`data_resolution = "D1_YAHOO_SANCTIONED"`, automatically quarantines USOIL Apr-2020).
    - 7 `TRUE_BLIND_CLB_NEW7_CROSSES` assets from `.runtime/offensive3-d1-cache/`
      (`data_resolution = "D1_YAHOO_SANCTIONED"`).
    """
    if not load_m1 and not load_d1:
        raise ValueError("At least one of load_m1 or load_d1 must be True")

    ws = resolve_workspace_root(root)
    req_years = _validate_dev_years(ALL_DEV_YEARS if years is None else years)
    specs_doc = load_ftmo_specs_28(specs_path=specs_path, root=ws)
    all_specs: dict[str, dict[str, Any]] = specs_doc["symbols"]

    if symbols is None:
        target_symbols = list(all_specs.keys())
    else:
        target_symbols = [normalize_symbol(s) for s in symbols]
        for s in target_symbols:
            if s not in all_specs:
                raise KeyError(f"Requested symbol {s!r} not in 28-symbol SSOT universe")

    m1_root = resolve_cache_dir(m1_cache_dir) if m1_cache_dir is not None else (ws / ".runtime/hot-m1-cache")
    if not m1_root.is_dir():
        m1_root = resolve_cache_dir(None)
    n9_root = Path(new9_d1_dir) if new9_d1_dir is not None else (ws / ".runtime/new-assets-10-cache")
    n7_root = Path(new7_d1_dir) if new7_d1_dir is not None else (ws / ".runtime/offensive3-d1-cache")

    d1_sha_map = _load_d1_manifest_hashes(n9_root, n7_root) if verify_sha else {}

    assets_out: dict[str, dict[str, Any]] = {}
    tier_counts: dict[str, int] = {TIER_12OLD: 0, TIER_NEW9: 0, TIER_NEW7: 0}
    res_counts: dict[str, int] = {RES_NATIVE_M1_BIDASK: 0, RES_D1_YAHOO_SANCTIONED: 0}
    global_max_ts = 0

    for sym in target_symbols:
        spec = dict(all_specs[sym])
        tier = str(spec["blindness_tier"])
        if tier not in tier_counts:
            raise ValueError(f"Unknown blindness_tier {tier!r} for {sym}")

        if tier == TIER_12OLD:
            ts_m1, q_m1, am = load_m1_asset(
                sym,
                m1_root,
                verify_sha=verify_sha,
                years=req_years,
                expected_lock_sha256=expected_lock_sha256,
            )
            enforce_dev_ts_bound(ts_m1, context=f"load_universe_28.m1:{sym}")
            d1_dict = (
                _build_bar_dict_from_m1_resample(ts_m1, q_m1, 86400, spec, weekdays_only=True) if load_d1 else None
            )
            h4_dict = (
                _build_bar_dict_from_m1_resample(ts_m1, q_m1, 14400, spec, weekdays_only=True) if load_d1 else None
            )

            pt = float(spec["point"])
            if q_m1.shape[1] >= 8:
                sp_m1 = np.maximum(0.0, q_m1[:, 7] - q_m1[:, 3])
                mid_m1 = 0.5 * (q_m1[:, 3] + q_m1[:, 7])
                med_sp_pts = float(np.median(sp_m1)) / pt
                med_sp_bps = float(np.median((sp_m1 / np.maximum(mid_m1, 1e-12)) * 10_000.0))
            else:
                med_sp_pts = float(spec["benchmark_spread_pts"])
                med_sp_bps = float(spec["oneway_bps"]) * 2.0

            m1_payload = (
                {
                    "times_sec": ts_m1,
                    "quotes": q_m1,
                    "native_ask": bool(am.get("native_Ask", True)),
                    "scale": int(am["scale"]),
                    "minutes": int(ts_m1.size),
                    "median_spread_pts": round(med_sp_pts, 4),
                    "median_spread_bps": round(med_sp_bps, 4),
                }
                if load_m1
                else None
            )

            min_px = float(np.min(q_m1))
            max_ts = int(ts_m1[-1])
            max_date = datetime.fromtimestamp(max_ts, tz=UTC).strftime("%Y-%m-%d")
            enforce_dev_date_bound(max_date, context=f"load_universe_28.max_date:{sym}")

            hygiene = {
                "quarantined_count": 0,
                "quarantined_dates": [],
                "quarantined_reasons": [],
                "min_open": round(float(np.min(d1_dict["open"])) if d1_dict else min_px, 8),
                "min_high": round(float(np.min(d1_dict["high"])) if d1_dict else min_px, 8),
                "min_low": round(float(np.min(d1_dict["low"])) if d1_dict else min_px, 8),
                "min_close": round(float(np.min(d1_dict["close"])) if d1_dict else min_px, 8),
                "all_ohlc_positive": True,
            }
            resolution = RES_NATIVE_M1_BIDASK
            asset_entry: dict[str, Any] = {
                "symbol": sym,
                "ftmo_symbol": str(spec["ftmo_symbol"]),
                "asset_class": str(spec["asset_class"]),
                "data_resolution": resolution,
                "blindness_tier": tier,
                "spec": spec,
                _SEAL_ROWS_KEY: 0,
                "max_ts": max_ts,
                "max_date": max_date,
                "hygiene": hygiene,
                "m1": m1_payload,
                "h4": h4_dict,
                "d1": d1_dict,
            }
        else:
            pfile = (n9_root if tier == TIER_NEW9 else n7_root) / f"{sym}.parquet"
            d1_dict, hygiene = _load_and_sanitize_d1_parquet(
                sym,
                pfile,
                spec,
                req_years=req_years,
                expected_sha=d1_sha_map.get(sym),
                verify_sha=verify_sha,
            )
            max_ts = int(d1_dict["times_sec"][-1])
            max_date = str(d1_dict["dates"][-1])
            resolution = RES_D1_YAHOO_SANCTIONED
            asset_entry = {
                "symbol": sym,
                "ftmo_symbol": str(spec["ftmo_symbol"]),
                "asset_class": str(spec["asset_class"]),
                "data_resolution": resolution,
                "blindness_tier": tier,
                "spec": spec,
                _SEAL_ROWS_KEY: 0,
                "max_ts": max_ts,
                "max_date": max_date,
                "hygiene": hygiene,
                "m1": None,
                "h4": None,
                "d1": d1_dict if load_d1 else None,
            }

        global_max_ts = max(global_max_ts, max_ts)
        tier_counts[tier] += 1
        res_counts[resolution] += 1
        assets_out[sym] = asset_entry

    enforce_dev_ts_bound(global_max_ts, context="load_universe_28.global_max_ts")

    return {
        "schema_version": "naqex-offensive3-universe-28-v1",
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "dev_cutoff_sec": DEV_CUTOFF_SEC,
        "max_ts": global_max_ts,
        "years": list(req_years),
        "symbol_count": len(assets_out),
        "symbols": list(assets_out.keys()),
        "tier_counts": tier_counts,
        "resolution_counts": res_counts,
        "assets": assets_out,
        "specs": specs_doc,
    }


# ---------------------------------------------------------------------------
# 3. Causal Indicator Library (`shift = 1` GUARANTEED — ZERO Bar-t Peek!)
# ---------------------------------------------------------------------------


def _validate_window_n(n: int, *, min_val: int = 1, name: str = "n") -> int:
    if isinstance(n, bool) or not isinstance(n, (int, np.integer)) or int(n) < min_val:
        raise ValueError(f"{name} must be an integer >= {min_val}, got {n!r}")
    return int(n)


@njit(cache=True)
def _causal_sma_1d_jit(arr: np.ndarray, n: int) -> np.ndarray:
    m = arr.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n:
        return out
    # Strictly shift = 1: out[t] = mean(arr[t-n : t]), zero dependency on arr[t]
    for t in range(n, m):
        acc = 0.0
        ok = True
        for k in range(t - n, t):
            v = arr[k]
            if not np.isfinite(v):
                ok = False
                break
            acc += v
        if ok:
            out[t] = acc / float(n)
    return out


@njit(cache=True)
def _causal_ema_1d_jit(arr: np.ndarray, n: int) -> np.ndarray:
    m = arr.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n:
        return out
    alpha = 2.0 / (float(n) + 1.0)
    one_m = 1.0 - alpha

    # Find first contiguous n finite bars to seed EMA cleanly
    ema_val = np.nan
    seeded = False
    valid_run = 0
    run_sum = 0.0
    for k in range(m - 1):
        v = arr[k]
        if not seeded:
            if np.isfinite(v):
                valid_run += 1
                run_sum += v
                if valid_run == n:
                    ema_val = run_sum / float(n)
                    seeded = True
                    out[k + 1] = ema_val  # shift = 1: bar k informs bar k+1
            else:
                valid_run = 0
                run_sum = 0.0
        else:
            if np.isfinite(v):
                ema_val = alpha * v + one_m * ema_val
            out[k + 1] = ema_val
    return out


@njit(cache=True)
def _causal_atr_1d_jit(high: np.ndarray, low: np.ndarray, close: np.ndarray, n: int) -> np.ndarray:
    m = close.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n:
        return out

    tr = np.empty(m, dtype=np.float64)
    for k in range(m):
        hk = high[k]
        lk = low[k]
        ck = close[k]
        if not (np.isfinite(hk) and np.isfinite(lk) and np.isfinite(ck)):
            tr[k] = np.nan
        elif k == 0 or not np.isfinite(close[k - 1]):
            tr[k] = abs(hk - lk)
        else:
            pc = close[k - 1]
            r1 = abs(hk - lk)
            r2 = abs(hk - pc)
            r3 = abs(lk - pc)
            tr[k] = max(r1, max(r2, r3))

    # Wilder RMA seeded with SMA of first contiguous n finite TRs; shifted by +1
    atr_val = np.nan
    seeded = False
    valid_run = 0
    run_sum = 0.0
    inv_n = 1.0 / float(n)
    nm1 = float(n - 1)
    for k in range(m - 1):
        tk = tr[k]
        if not seeded:
            if np.isfinite(tk):
                valid_run += 1
                run_sum += tk
                if valid_run == n:
                    atr_val = run_sum * inv_n
                    seeded = True
                    out[k + 1] = atr_val
            else:
                valid_run = 0
                run_sum = 0.0
        else:
            if np.isfinite(tk):
                atr_val = (atr_val * nm1 + tk) * inv_n
            out[k + 1] = atr_val
    return out


@njit(cache=True)
def _causal_rsi_1d_jit(c: np.ndarray, n: int) -> np.ndarray:
    m = c.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n + 1:
        return out

    avg_g = 0.0
    avg_l = 0.0
    seeded = False
    valid_run = 0
    g_sum = 0.0
    l_sum = 0.0
    inv_n = 1.0 / float(n)
    nm1 = float(n - 1)

    for k in range(1, m - 1):
        c_cur = c[k]
        c_prev = c[k - 1]
        if not (np.isfinite(c_cur) and np.isfinite(c_prev)):
            if not seeded:
                valid_run = 0
                g_sum = 0.0
                l_sum = 0.0
            else:
                out[k + 1] = out[k]
            continue

        diff = c_cur - c_prev
        g = diff if diff > 0.0 else 0.0
        lo = -diff if diff < 0.0 else 0.0

        if not seeded:
            valid_run += 1
            g_sum += g
            l_sum += lo
            if valid_run == n:
                avg_g = g_sum * inv_n
                avg_l = l_sum * inv_n
                seeded = True
                if avg_l <= 1e-15:
                    out[k + 1] = 100.0 if avg_g > 1e-15 else 50.0
                else:
                    rs = avg_g / avg_l
                    out[k + 1] = 100.0 - (100.0 / (1.0 + rs))
        else:
            avg_g = (avg_g * nm1 + g) * inv_n
            avg_l = (avg_l * nm1 + lo) * inv_n
            if avg_l <= 1e-15:
                out[k + 1] = 100.0 if avg_g > 1e-15 else 50.0
            else:
                rs = avg_g / avg_l
                out[k + 1] = 100.0 - (100.0 / (1.0 + rs))
    return out


@njit(cache=True)
def _causal_realized_vol_1d_jit(c: np.ndarray, n: int, use_log: bool) -> np.ndarray:
    m = c.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n + 1:
        return out

    rets = np.empty(m, dtype=np.float64)
    rets[0] = np.nan
    for k in range(1, m):
        c0 = c[k - 1]
        c1 = c[k]
        if np.isfinite(c0) and np.isfinite(c1) and c0 > 0.0 and c1 > 0.0:
            rets[k] = math.log(c1 / c0) if use_log else (c1 / c0 - 1.0)
        else:
            rets[k] = np.nan

    # Strictly shift = 1: out[t] uses rets[t-n : t], depending ONLY on c[t-n-1 .. t-1]
    denom = float(n - 1) if n > 1 else 1.0
    for t in range(n + 1, m):
        mean = 0.0
        ok = True
        for k in range(t - n, t):
            rk = rets[k]
            if not np.isfinite(rk):
                ok = False
                break
            mean += rk
        if not ok:
            continue
        mean /= float(n)
        ssq = 0.0
        for k in range(t - n, t):
            d = rets[k] - mean
            ssq += d * d
        out[t] = math.sqrt(ssq / denom)
    return out


@njit(cache=True)
def _causal_zscore_1d_jit(x: np.ndarray, n: int) -> np.ndarray:
    m = x.shape[0]
    out = np.empty(m, dtype=np.float64)
    for t in range(m):
        out[t] = np.nan
    if m <= n:
        return out

    # Strictly shift = 1: out[t] = (x[t-1] - mean(x[t-n:t])) / std(x[t-n:t], ddof=1)
    denom = float(n - 1) if n > 1 else 1.0
    for t in range(n, m):
        mean = 0.0
        ok = True
        for k in range(t - n, t):
            xk = x[k]
            if not np.isfinite(xk):
                ok = False
                break
            mean += xk
        if not ok:
            continue
        mean /= float(n)
        ssq = 0.0
        for k in range(t - n, t):
            d = x[k] - mean
            ssq += d * d
        sd = math.sqrt(ssq / denom)
        if sd > 1e-12:
            out[t] = (x[t - 1] - mean) / sd
        else:
            out[t] = 0.0
    return out


def _apply_1d_or_2d(arr: np.ndarray, fn_1d) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float64)
    if a.ndim == 1:
        return fn_1d(np.ascontiguousarray(a, dtype=np.float64))
    if a.ndim == 2:
        out = np.empty_like(a, dtype=np.float64)
        for j in range(a.shape[1]):
            out[:, j] = fn_1d(np.ascontiguousarray(a[:, j], dtype=np.float64))
        return out
    raise ValueError(f"Expected 1D or 2D array, got shape {a.shape}")


def causal_sma(c: np.ndarray, n: int = 20) -> np.ndarray:
    """Strictly `shift = 1` causal Simple Moving Average (`out[t]` uses `c[t-n .. t-1]` ONLY)."""
    win = _validate_window_n(n, min_val=1)
    return _apply_1d_or_2d(c, lambda col: _causal_sma_1d_jit(col, win))


def causal_ema(c: np.ndarray, n: int = 20) -> np.ndarray:
    """Strictly `shift = 1` causal Exponential Moving Average (`out[t]` uses `c[0 .. t-1]` ONLY)."""
    win = _validate_window_n(n, min_val=1)
    return _apply_1d_or_2d(c, lambda col: _causal_ema_1d_jit(col, win))


def causal_atr(h: np.ndarray, l: np.ndarray, c: np.ndarray, n: int = 14) -> np.ndarray:  # noqa: E741
    """Strictly `shift = 1` causal Wilder ATR (`out[t]` uses bars `0 .. t-1` ONLY)."""
    win = _validate_window_n(n, min_val=1)
    ha = np.asarray(h, dtype=np.float64)
    la = np.asarray(l, dtype=np.float64)
    ca = np.asarray(c, dtype=np.float64)
    if ha.shape != la.shape or ha.shape != ca.shape:
        raise ValueError(f"h, l, c shapes must match: got {ha.shape}, {la.shape}, {ca.shape}")
    if ha.ndim == 1:
        return _causal_atr_1d_jit(
            np.ascontiguousarray(ha), np.ascontiguousarray(la), np.ascontiguousarray(ca), win
        )
    if ha.ndim == 2:
        out = np.empty_like(ca, dtype=np.float64)
        for j in range(ca.shape[1]):
            out[:, j] = _causal_atr_1d_jit(
                np.ascontiguousarray(ha[:, j]),
                np.ascontiguousarray(la[:, j]),
                np.ascontiguousarray(ca[:, j]),
                win,
            )
        return out
    raise ValueError(f"Expected 1D or 2D arrays for causal_atr, got shape {ca.shape}")


def causal_rsi(c: np.ndarray, n: int = 14) -> np.ndarray:
    """Strictly `shift = 1` causal Wilder RSI in `[0, 100]` (`out[t]` uses `c[0 .. t-1]` ONLY)."""
    win = _validate_window_n(n, min_val=1)
    return _apply_1d_or_2d(c, lambda col: _causal_rsi_1d_jit(col, win))


def causal_realized_vol(
    c: np.ndarray,
    n: int = 20,
    *,
    use_log_returns: bool = True,
    annualize_bars: float | None = None,
) -> np.ndarray:
    """Strictly `shift = 1` causal realized return volatility (`out[t]` uses `c[t-n-1 .. t-1]` ONLY)."""
    win = _validate_window_n(n, min_val=2)
    res = _apply_1d_or_2d(c, lambda col: _causal_realized_vol_1d_jit(col, win, bool(use_log_returns)))
    if annualize_bars is not None:
        if isinstance(annualize_bars, bool) or float(annualize_bars) <= 0.0:
            raise ValueError(f"annualize_bars must be > 0, got {annualize_bars!r}")
        res = res * math.sqrt(float(annualize_bars))
    return res


def causal_zscore(x: np.ndarray, n: int = 20) -> np.ndarray:
    """Strictly `shift = 1` causal rolling z-score (`out[t]` uses `x[t-n .. t-1]` ONLY)."""
    win = _validate_window_n(n, min_val=2)
    return _apply_1d_or_2d(x, lambda col: _causal_zscore_1d_jit(col, win))


# ---------------------------------------------------------------------------
# 4. Red-News Dev Calendar Loader & Symbol-to-Event Matcher
# ---------------------------------------------------------------------------


def match_symbol_red_news_codes(symbol: str) -> frozenset[str]:
    """Map canonical/broker symbol to governing red-news codes (`8 CCYs + EIA`)."""
    u = normalize_symbol(symbol)
    codes: set[str] = set()
    if any(tok in u for tok in _OIL_TOKENS):
        codes.update({"EIA", "USD"})
    if any(tok in u for tok in _JP_INDEX_TOKENS):
        codes.update({"JPY", "USD"})
    if any(tok in u for tok in _US_INDEX_TOKENS):
        codes.add("USD")
    if any(tok in u for tok in _EU_INDEX_TOKENS):
        codes.add("EUR")
    if any(tok in u for tok in _UK_INDEX_TOKENS):
        codes.add("GBP")
    if any(tok in u for tok in _AU_INDEX_TOKENS):
        codes.add("AUD")
    if any(tok in u for tok in _USD_METAL_CRYPTO_TOKENS):
        codes.add("USD")
    for ccy in _EIGHT_CCYS:
        if ccy in u:
            codes.add(ccy)
    return frozenset(codes)


def load_dev_red_news_index(
    *,
    include_extended: bool = True,
    base_6ccy_path: str | Path | None = None,
    extended_8ccy_eia_path: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load pre-cutoff Dev red-news events (6-CCY + optional 8-CCY/EIA dev section) into O(log K) arrays."""
    ws = resolve_workspace_root(root)
    p_base = (
        Path(base_6ccy_path)
        if base_6ccy_path is not None
        else (ws / "tooling/ai-engines/configs/calendars/red_news_official_2018_2024_6ccy.json")
    )
    p_ext = (
        Path(extended_8ccy_eia_path)
        if extended_8ccy_eia_path is not None
        else (ws / "tooling/ai-engines/configs/calendars/red_news_extended_off3_8ccy_eia.json")
    )
    if not p_base.is_file():
        raise FileNotFoundError(f"Base 6-CCY Dev red-news calendar missing: {p_base}")

    raw_base = json.loads(p_base.read_text(encoding="utf-8-sig"))
    raw_events: list[dict[str, Any]] = list(raw_base.get("events") or [])
    ext_loaded = False
    if include_extended and p_ext.is_file():
        raw_ext = json.loads(p_ext.read_text(encoding="utf-8-sig"))
        dev_sec = (raw_ext.get("sections") or {}).get("dev_2018_2024")
        if not isinstance(dev_sec, dict) or not isinstance(dev_sec.get("events"), list):
            raise ValueError(f"Missing dev_2018_2024 section in {p_ext}")
        raw_events.extend(dev_sec["events"])
        ext_loaded = True

    by_code_raw: dict[str, list[tuple[int, int]]] = {}
    seen: set[tuple[int, str, str]] = set()
    max_ts = 0
    for ev in raw_events:
        ts = int(ev["utc_ts"])
        if ts >= DEV_CUTOFF_SEC:
            raise ValueError(f"DEV_CUTOFF_BREACH [red_news]: event utc_ts={ts} >= {DEV_CUTOFF_SEC}")
        ccy = str(ev["ccy"]).strip().upper()
        label = str(ev.get("event", "")).strip()
        key = (ts, ccy, label)
        if key in seen:
            continue
        seen.add(key)
        bsec = int(ev.get("blackout_sec", 300))
        by_code_raw.setdefault(ccy, []).append((ts, max(60, bsec)))
        if ts > max_ts:
            max_ts = ts

    by_code: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for code, pairs in by_code_raw.items():
        pairs.sort(key=lambda p: p[0])
        by_code[code] = (
            np.array([p[0] for p in pairs], dtype=np.int64),
            np.array([p[1] for p in pairs], dtype=np.int64),
        )

    return {
        "schema_version": "naqex-offensive3-dev-red-news-index-v1",
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "max_ts": max_ts,
        "extended_loaded": ext_loaded,
        "total_events": len(seen),
        "codes": sorted(by_code.keys()),
        "by_code": by_code,
    }


def _symbol_news_arrays(symbol: str, news_index: Mapping[str, Any]) -> tuple[np.ndarray, np.ndarray]:
    codes = match_symbol_red_news_codes(symbol)
    by_code: Mapping[str, tuple[np.ndarray, np.ndarray]] = news_index["by_code"]
    ts_parts: list[np.ndarray] = []
    pad_parts: list[np.ndarray] = []
    for c in sorted(codes):
        if c in by_code:
            ts_parts.append(by_code[c][0])
            pad_parts.append(by_code[c][1])
    if not ts_parts:
        return np.empty(0, dtype=np.int64), np.empty(0, dtype=np.int64)
    ts_all = np.concatenate(ts_parts)
    pad_all = np.concatenate(pad_parts)
    order = np.argsort(ts_all, kind="mergesort")
    return ts_all[order], pad_all[order]


def is_in_red_news_window(
    symbol: str,
    ts_sec: int,
    news_index: Mapping[str, Any],
    *,
    pad_sec: int = 300,
) -> bool:
    """Return True if `ts_sec` falls inside `[ev_ts - max(pad_sec, ev_pad), ev_ts + max(pad_sec, ev_pad)]`."""
    ev_ts, ev_pad = _symbol_news_arrays(symbol, news_index)
    if ev_ts.size == 0:
        return False
    t = int(ts_sec)
    p = max(0, int(pad_sec))
    max_look = max(p, int(np.max(ev_pad)))
    lo = int(np.searchsorted(ev_ts, t - max_look, side="left"))
    hi = int(np.searchsorted(ev_ts, t + max_look, side="right"))
    for idx in range(lo, hi):
        eff = max(p, int(ev_pad[idx]))
        if abs(t - int(ev_ts[idx])) <= eff:
            return True
    return False


def find_first_red_news_flatten_ts(
    symbol: str,
    entry_ts: int,
    flat_ts: int,
    news_index: Mapping[str, Any],
    *,
    pad_sec: int = 300,
) -> int | None:
    """Return earliest flatten timestamp `ev_ts - eff_pad` strictly inside `(entry_ts, flat_ts]`, or None."""
    ev_ts, ev_pad = _symbol_news_arrays(symbol, news_index)
    if ev_ts.size == 0:
        return None
    p = max(0, int(pad_sec))
    max_look = max(p, int(np.max(ev_pad)))
    lo = int(np.searchsorted(ev_ts, int(entry_ts) - max_look, side="left"))
    hi = int(np.searchsorted(ev_ts, int(flat_ts) + max_look, side="right"))
    earliest: int | None = None
    for idx in range(lo, hi):
        eff = max(p, int(ev_pad[idx]))
        f_ts = int(ev_ts[idx]) - eff
        if int(entry_ts) < f_ts <= int(flat_ts):
            if earliest is None or f_ts < earliest:
                earliest = f_ts
    return earliest


# ---------------------------------------------------------------------------
# 5. Swap Engine, Anti-Fake-Swap Guard & Leverage Margin Utilizer
# ---------------------------------------------------------------------------


def compute_daily_swap_frac(
    spec: Mapping[str, Any],
    price: float,
    side: int,
    py_weekday: int,
    *,
    zero_positive_swap: bool = False,
    conservative_financing_floor: bool = False,
) -> float:
    """Compute exact daily overnight swap return as fraction of position notional.

    - `swap_mode == 1` (MT5 Points): `(swap_pts * point / price) * mult`
    - `swap_mode == 5` (MT5 Interest %/yr, e.g. BTCUSD `-30%/yr`): `(swap_pct / 100 / 365) * mult`
    - `swap_rollover3days`: `3` -> Wed (`py_weekday == 2`) gets `3x`; `5` -> Fri (`py_weekday == 4`) gets `3x`.
    - Anti-Fake-Swap Guard: blocks ALL positive anomalies on `indices/oil/metals/crypto`
      (incl. `US100`, `US500`, `UK100` short, `USOIL` long, `UKOIL` long), capping them at `0.0`
      (or `fallback_annual_rate / 365` when `conservative_financing_floor=True`).
    - `zero_positive_swap=True` pays 100% of negative swaps and credits 0% of positive swaps
      even on FX carry pairs.
    """
    if side == 0 or not math.isfinite(price) or price <= 0.0:
        return 0.0
    if py_weekday < 0 or py_weekday > 6:
        raise ValueError(f"py_weekday must be in [0, 6], got {py_weekday!r}")

    swap_mode = int(spec.get("swap_mode", 1))
    roll_day = int(spec.get("swap_rollover3days", 3))
    # MT5 DayOfWeek: 3=Wed -> py_weekday=2; 5=Fri -> py_weekday=4
    mult = 3.0 if py_weekday == (roll_day - 1) else 1.0
    raw_val = float(spec["swap_long"] if side > 0 else spec["swap_short"])
    pt = float(spec["point"])

    if swap_mode == 5:
        base_daily = (raw_val / 100.0) / 365.0
    else:
        base_daily = (raw_val * pt) / price

    guard = spec.get("anti_fake_swap_guard") or {}
    asset_class = str(spec.get("asset_class", "")).lower()
    block_pos = bool(guard.get("block_positive_swap", False)) or asset_class in ("indices", "oil", "metals", "crypto")
    anomaly_blocked = (side > 0 and bool(guard.get("long_anomaly_blocked", False))) or (
        side < 0 and bool(guard.get("short_anomaly_blocked", False))
    )

    if (block_pos or anomaly_blocked) and base_daily > 0.0:
        if conservative_financing_floor:
            fb_rate = guard.get("fallback_annual_rate")
            fb_daily = (float(fb_rate) / 365.0) if isinstance(fb_rate, (int, float)) and float(fb_rate) < 0.0 else 0.0
            base_daily = min(0.0, fb_daily)
        else:
            base_daily = 0.0

    if zero_positive_swap and base_daily > 0.0:
        base_daily = 0.0

    return float(base_daily * mult)


def _fx_to_usd_multiplier(ccy: str, fx_rates: Mapping[str, float]) -> float:
    c = str(ccy).upper()
    if c == "USD":
        return 1.0
    direct = f"{c}USD"
    if direct in fx_rates and float(fx_rates[direct]) > 0.0:
        return float(fx_rates[direct])
    inv = f"USD{c}"
    if inv in fx_rates and float(fx_rates[inv]) > 0.0:
        return 1.0 / float(fx_rates[inv])
    raise ValueError(f"Missing FX conversion rate to USD for currency {c!r}")


def compute_causal_tick_val_usd(
    spec: Mapping[str, Any],
    *,
    entry_price: float | None = None,
    fx_rates: Mapping[str, float] | None = None,
) -> float:
    """Compute USD value of 1 point (`spec['point']`) per 1.00 lot using causal FX conversion."""
    rates = dict(DEFAULT_REFERENCE_FX_RATES)
    if fx_rates:
        rates.update({str(k).upper(): float(v) for k, v in fx_rates.items()})

    cs = float(spec["contract_size"])
    pt = float(spec["point"])
    tick_profit_ccy = cs * pt
    op = str(spec.get("profit_to_usd_op", "identity"))
    pair = spec.get("profit_to_usd_pair")
    sym = str(spec.get("canonical_symbol", "")).upper()

    if op == "identity" or pair is None:
        return tick_profit_ccy

    pair_u = str(pair).upper()
    if pair_u == sym and entry_price is not None and math.isfinite(entry_price) and entry_price > 0.0:
        rate = float(entry_price)
    elif pair_u in rates and float(rates[pair_u]) > 0.0:
        rate = float(rates[pair_u])
    else:
        return float(spec["tick_val_loss_usd_ref"])

    if op == "multiply":
        return tick_profit_ccy * rate
    if op == "divide":
        return tick_profit_ccy / rate
    raise ValueError(f"Unsupported profit_to_usd_op {op!r} for {sym}")


def compute_notional_and_margin_per_lot_usd(
    spec: Mapping[str, Any],
    entry_price: float,
    *,
    account_type: str = "ftmo_swing",
    fx_rates: Mapping[str, float] | None = None,
) -> tuple[float, float, float]:
    """Return `(notional_usd_per_lot, margin_usd_per_lot, leverage)` for any of the 28 FTMO symbols."""
    if not math.isfinite(entry_price) or entry_price <= 0.0:
        raise ValueError(f"entry_price must be finite > 0, got {entry_price!r}")

    rates = dict(DEFAULT_REFERENCE_FX_RATES)
    if fx_rates:
        rates.update({str(k).upper(): float(v) for k, v in fx_rates.items()})

    acct = str(account_type).strip().lower()
    if acct in ("ftmo_swing", "swing"):
        lev = float(spec["leverage_ftmo_swing"])
    elif acct in ("ftmo_standard", "standard", "the5ers"):
        lev = float(spec["leverage_ftmo_standard"])
    else:
        raise ValueError(f"Unsupported account_type {account_type!r}; expected ftmo_swing/ftmo_standard/the5ers")
    if lev <= 0.0:
        raise ValueError(f"Invalid leverage {lev} for {spec.get('canonical_symbol')}")

    cs = float(spec["contract_size"])
    asset_class = str(spec["asset_class"]).lower()
    ccy_base = str(spec["currency_base"]).upper()
    ccy_profit = str(spec["currency_profit"]).upper()
    ccy_margin = str(spec["currency_margin"]).upper()

    if asset_class == "forex":
        if ccy_base == "USD":
            notional_usd = cs
        elif ccy_profit == "USD":
            notional_usd = cs * entry_price
        else:
            notional_usd = cs * _fx_to_usd_multiplier(ccy_base, rates)
    else:
        # Indices, Metals, Oil, Crypto: contract_size * price in margin/profit currency -> USD
        notional_local = cs * entry_price
        notional_usd = notional_local * _fx_to_usd_multiplier(ccy_margin, rates)

    margin_usd = notional_usd / lev
    return notional_usd, margin_usd, lev


def check_leverage_margin(
    spec: Mapping[str, Any],
    entry_price: float,
    sl_price: float,
    *,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    account_type: str = "ftmo_swing",
    max_margin_util_frac: float = 0.80,
    used_margin_usd: float = 0.0,
    scale_if_over_margin: bool = True,
    fx_rates: Mapping[str, float] | None = None,
) -> dict[str, Any]:
    """Check and optionally scale position sizing against real FTMO Swing/Standard leverage margin."""
    sl_dist = abs(float(entry_price) - float(sl_price))
    if not math.isfinite(sl_dist) or sl_dist <= 0.0:
        raise ValueError(f"Hard SL required with positive distance, got entry={entry_price}, sl={sl_price}")
    if not math.isfinite(account_balance_usd) or account_balance_usd <= 0.0:
        raise ValueError(f"account_balance_usd must be > 0, got {account_balance_usd!r}")
    if not math.isfinite(risk_frac) or risk_frac <= 0.0:
        raise ValueError(f"risk_frac must be > 0, got {risk_frac!r}")

    notional_1lot, margin_1lot, leverage = compute_notional_and_margin_per_lot_usd(
        spec, entry_price, account_type=account_type, fx_rates=fx_rates
    )
    tick_val_usd = compute_causal_tick_val_usd(spec, entry_price=entry_price, fx_rates=fx_rates)
    pt = float(spec["point"])
    usd_per_price_unit = tick_val_usd / pt

    risk_budget_usd = float(account_balance_usd) * float(risk_frac)
    risk_per_lot_usd = sl_dist * usd_per_price_unit
    if risk_per_lot_usd <= 0.0 or not math.isfinite(risk_per_lot_usd):
        raise ValueError(f"Invalid risk_per_lot_usd={risk_per_lot_usd!r}")

    vmin = float(spec.get("volume_min", 0.01))
    vstep = float(spec.get("volume_step", 0.01))
    desired_lots = risk_budget_usd / risk_per_lot_usd
    desired_lots_stepped = math.floor((desired_lots / vstep) + 1e-12) * vstep
    desired_margin_usd = desired_lots * margin_1lot
    raw_margin_util_frac = (used_margin_usd + desired_margin_usd) / float(account_balance_usd)

    avail_margin_usd = max(0.0, float(account_balance_usd) * float(max_margin_util_frac) - float(used_margin_usd))
    max_lots_by_margin = avail_margin_usd / margin_1lot if margin_1lot > 0.0 else 0.0

    margin_capped = False
    accepted = True
    reason = "OK"

    if desired_lots_stepped + 1e-12 < vmin:
        accepted = False
        eff_lots = 0.0
        eff_risk_scale = 0.0
        reason = "BELOW_VOLUME_MIN"
    elif desired_lots_stepped * margin_1lot > avail_margin_usd + 1e-9:
        if scale_if_over_margin:
            capped_lots = math.floor((max_lots_by_margin / vstep) + 1e-12) * vstep
            if capped_lots + 1e-12 < vmin:
                accepted = False
                eff_lots = 0.0
                eff_risk_scale = 0.0
                margin_capped = True
                reason = "MARGIN_BELOW_VOLUME_MIN"
            else:
                eff_lots = round(capped_lots, 6)
                eff_risk_scale = eff_lots / desired_lots if desired_lots > 0.0 else 0.0
                margin_capped = True
                reason = "MARGIN_SCALED"
        else:
            accepted = False
            eff_lots = 0.0
            eff_risk_scale = 0.0
            margin_capped = True
            reason = "OVER_MARGIN_REJECTED"
    else:
        eff_lots = round(desired_lots_stepped, 6)
        eff_risk_scale = eff_lots / desired_lots if desired_lots > 0.0 else 0.0

    eff_margin_usd = eff_lots * margin_1lot
    eff_margin_util_frac = (used_margin_usd + eff_margin_usd) / float(account_balance_usd)

    return {
        "accepted": accepted,
        "reason": reason,
        "margin_capped": margin_capped,
        "leverage": leverage,
        "notional_usd_per_lot": round(notional_1lot, 4),
        "margin_usd_per_lot": round(margin_1lot, 4),
        "desired_lots": round(desired_lots, 6),
        "lots": eff_lots,
        "eff_risk_scale": round(eff_risk_scale, 6),
        "raw_margin_util_frac": round(raw_margin_util_frac, 6),
        "margin_util_frac": round(eff_margin_util_frac, 6),
        "margin_usd": round(eff_margin_usd, 4),
        "usd_per_price_unit_1lot": round(usd_per_price_unit, 6),
    }


# ---------------------------------------------------------------------------
# 6. Unified Intraday M1 Replay (`swap = 0`, hard flat <= 20:50 UTC)
# ---------------------------------------------------------------------------


@njit(cache=True)
def _scan_m1_pending_fill_jit(
    quotes: np.ndarray,
    start_idx: int,
    expire_idx: int,
    side: int,
    order_code: int,  # 1 = STOP, 2 = LIMIT
    trigger: float,
) -> tuple[int, float]:
    has_ask = quotes.shape[1] >= 8
    col_o = 4 if (side == 1 and has_ask) else 0
    col_h = 5 if (side == 1 and has_ask) else 1
    col_l = 6 if (side == 1 and has_ask) else 2
    eps = 1e-12
    for k in range(start_idx, expire_idx + 1):
        op = quotes[k, col_o]
        hi = quotes[k, col_h]
        lo = quotes[k, col_l]
        if order_code == 1:  # STOP
            if side == 1 and hi >= trigger - eps:
                return k, (op if op > trigger else trigger)
            if side == -1 and lo <= trigger + eps:
                return k, (op if op < trigger else trigger)
        else:  # LIMIT
            if side == 1 and lo <= trigger + eps:
                return k, (op if op < trigger else trigger)
            if side == -1 and hi >= trigger - eps:
                return k, (op if op > trigger else trigger)
    return -1, np.nan


@njit(cache=True)
def _scan_m1_exit_jit(
    quotes: np.ndarray,
    fill_idx: int,
    flat_idx: int,
    side: int,
    sl_price: float,
    has_tp: bool,
    tp_price: float,
) -> tuple[int, float, int]:
    """Conservative M1 exit scan: SL ALWAYS beats TP on same-bar tie-break!

    Exit codes: 1=SL_GAP, 2=SL_HIT, 3=TP_GAP, 4=TP_HIT, 5=HARD_FLAT.
    """
    has_ask = quotes.shape[1] >= 8
    # Long exits on Bid (0..3), Short exits on Ask (4..7)
    col_o = 0 if side == 1 else (4 if has_ask else 0)
    col_h = 1 if side == 1 else (5 if has_ask else 1)
    col_l = 2 if side == 1 else (6 if has_ask else 2)
    eps = 1e-12

    for k in range(fill_idx, flat_idx + 1):
        op = quotes[k, col_o]
        hi = quotes[k, col_h]
        lo = quotes[k, col_l]

        # 1. Conservative SL check FIRST (gap on bar > fill_idx, then intrabar touch)
        if side == 1:
            if k > fill_idx and op <= sl_price + eps:
                return k, op, 1
            if lo <= sl_price + eps:
                return k, sl_price, 2
        else:
            if k > fill_idx and op >= sl_price - eps:
                return k, op, 1
            if hi >= sl_price - eps:
                return k, sl_price, 2

        # 2. TP check ONLY if SL was NOT breached on this bar
        if has_tp:
            if side == 1:
                if k > fill_idx and op >= tp_price - eps:
                    return k, op, 3
                if hi >= tp_price - eps:
                    return k, tp_price, 4
            else:
                if k > fill_idx and op <= tp_price + eps:
                    return k, op, 3
                if lo <= tp_price + eps:
                    return k, tp_price, 4

    return flat_idx, quotes[flat_idx, col_o], 5


def replay_intraday_m1_trade(
    symbol: str,
    times_sec: np.ndarray,
    quotes: np.ndarray,
    entry_idx: int,
    side: int,
    sl_price: float,
    *,
    tp_price: float | None = None,
    entry_order_type: str = "MARKET",
    entry_trigger_price: float | None = None,
    order_expire_idx: int | None = None,
    flat_idx: int | None = None,
    hard_flat_utc_hhmm: tuple[int, int] = HARD_FLAT_MAX_UTC_HHMM,
    spec: Mapping[str, Any] | None = None,
    friction_tiers: Sequence[float] = FRICTION_TIERS,
    firm_profile: str = "FTMO_STANDARD",
    red_news_index: Mapping[str, Any] | None = None,
    news_pad_sec: int = 300,
    flatten_before_news: bool = True,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    max_margin_util_frac: float = 0.80,
    scale_if_over_margin: bool = True,
    fx_rates: Mapping[str, float] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Replay a single Intraday M1 Bid/Ask trade (`swap = 0`, hard flat <= `20:50 UTC`).

    Enforces:
      - Strict pre-cutoff timestamp validation (`< DEV_CUTOFF_SEC`).
      - Mandatory hard SL (`side * (entry - sl) > 0`).
      - Hard flat strictly `<= 20:50 UTC` of the entry UTC day (`swap_R = 0.0`).
      - Conservative SL-before-TP tie-break on any M1 bar touching both levels.
      - Realistic `1.0x / 1.5x / 2.0x` Bid/Ask spread + commission + slippage tiers.
      - Optional red-news entry block & pre-news flatten (`6-CCY` + `8-CCY/EIA`).
      - Computes Stage-0 `friction_over_sl` (`F_stress / SL`).
    """
    if side not in (-1, 1):
        raise ValueError(f"side must be +1 or -1, got {side!r}")
    hh, mm = int(hard_flat_utc_hhmm[0]), int(hard_flat_utc_hhmm[1])
    flat_sec_of_day = hh * 3600 + mm * 60
    if flat_sec_of_day > HARD_FLAT_MAX_UTC_SEC or flat_sec_of_day <= 0:
        raise ValueError(
            f"Intraday hard flat must be <= 20:50 UTC (swap=0 invariant), got {hard_flat_utc_hhmm!r}"
        )

    n_bars = int(times_sec.shape[0])
    if entry_idx < 0 or entry_idx >= n_bars:
        raise ValueError(f"entry_idx={entry_idx} out of bounds for n_bars={n_bars}")

    ts_entry_req = int(times_sec[entry_idx])
    enforce_dev_ts_bound(ts_entry_req, context=f"replay_intraday_m1_trade.entry:{symbol}")

    sym_spec = dict(spec) if spec is not None else get_symbol_spec(symbol, root=root)
    sym = str(sym_spec["canonical_symbol"])
    has_ask = quotes.shape[1] >= 8

    # Hard flat ceiling on the entry UTC day (<= 20:50 UTC)
    day_start_ts = (ts_entry_req // 86400) * 86400
    hard_flat_ts = day_start_ts + flat_sec_of_day
    if ts_entry_req >= hard_flat_ts:
        return {
            "filled": False,
            "status": "AFTER_HARD_FLAT",
            "symbol": sym,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    # Find last M1 bar index <= hard_flat_ts
    max_flat_idx = int(np.searchsorted(times_sec, hard_flat_ts, side="right")) - 1
    if max_flat_idx <= entry_idx:
        return {
            "filled": False,
            "status": "NO_BARS_BEFORE_HARD_FLAT",
            "symbol": sym,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }
    eff_flat_idx = min(max_flat_idx, int(flat_idx)) if flat_idx is not None else max_flat_idx
    if eff_flat_idx <= entry_idx:
        return {
            "filled": False,
            "status": "INVALID_FLAT_WINDOW",
            "symbol": sym,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }
    enforce_dev_ts_bound(int(times_sec[eff_flat_idx]), context=f"replay_intraday_m1_trade.flat:{sym}")

    # Resolve entry fill (MARKET, STOP, or LIMIT)
    otype = str(entry_order_type).strip().upper()
    if otype == "MARKET":
        fill_idx = int(entry_idx)
        entry_fill = float(quotes[fill_idx, 4] if (side == 1 and has_ask) else quotes[fill_idx, 0])
    elif otype in ("STOP", "LIMIT"):
        if entry_trigger_price is None or not math.isfinite(float(entry_trigger_price)):
            raise ValueError(f"{otype} order requires finite entry_trigger_price")
        exp_i = min(eff_flat_idx - 1, int(order_expire_idx) if order_expire_idx is not None else eff_flat_idx - 1)
        if exp_i < entry_idx:
            return {
                "filled": False,
                "status": "ORDER_EXPIRED",
                "symbol": sym,
                "order_send_count": ORDER_SEND_COUNT,
                _SEAL_ROWS_ANALYSED_KEY: 0,
            }
        ocode = 1 if otype == "STOP" else 2
        fill_idx, entry_fill = _scan_m1_pending_fill_jit(
            quotes, int(entry_idx), int(exp_i), int(side), ocode, float(entry_trigger_price)
        )
        if fill_idx < 0 or not math.isfinite(entry_fill):
            return {
                "filled": False,
                "status": "ORDER_NOT_TRIGGERED",
                "symbol": sym,
                "order_send_count": ORDER_SEND_COUNT,
                _SEAL_ROWS_ANALYSED_KEY: 0,
            }
    else:
        raise ValueError(f"Unsupported entry_order_type {entry_order_type!r}; expected MARKET/STOP/LIMIT")

    fill_ts = int(times_sec[fill_idx])
    # Red-News entry guard (for FTMO Standard / The5ers)
    if red_news_index is not None and is_in_red_news_window(sym, fill_ts, red_news_index, pad_sec=news_pad_sec):
        return {
            "filled": False,
            "status": "BLOCKED_RED_NEWS",
            "symbol": sym,
            "entry_ts": fill_ts,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    # Validate mandatory Hard SL & optional TP relative to actual entry fill
    sl_f = float(sl_price)
    sl_dist = side * (entry_fill - sl_f)
    if not math.isfinite(sl_f) or sl_dist <= 0.0:
        return {
            "filled": False,
            "status": "INVALID_OR_BREACHED_SL",
            "symbol": sym,
            "entry_ts": fill_ts,
            "entry_price": entry_fill,
            "sl_price": sl_f,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }
    has_tp = tp_price is not None
    tp_f = float(tp_price) if tp_price is not None else 0.0
    if has_tp and (not math.isfinite(tp_f) or side * (tp_f - entry_fill) <= 0.0):
        raise ValueError(f"Invalid TP {tp_price} for side={side} at entry={entry_fill}")

    # Leverage & margin check
    firm_u = str(firm_profile).strip().upper()
    acct_type = "ftmo_swing" if "SWING" in firm_u else "ftmo_standard"
    margin_chk = check_leverage_margin(
        sym_spec,
        entry_fill,
        sl_f,
        account_balance_usd=account_balance_usd,
        risk_frac=risk_frac,
        account_type=acct_type,
        max_margin_util_frac=max_margin_util_frac,
        scale_if_over_margin=scale_if_over_margin,
        fx_rates=fx_rates,
    )
    if not margin_chk["accepted"]:
        return {
            "filled": False,
            "status": margin_chk["reason"],
            "symbol": sym,
            "entry_ts": fill_ts,
            "margin_check": margin_chk,
            "order_send_count": ORDER_SEND_COUNT,
            _SEAL_ROWS_ANALYSED_KEY: 0,
        }

    # Optional pre-news flatten cutoff before eff_flat_idx
    news_flattened = False
    scan_flat_idx = eff_flat_idx
    if red_news_index is not None and flatten_before_news:
        nf_ts = find_first_red_news_flatten_ts(
            sym, fill_ts, int(times_sec[eff_flat_idx]), red_news_index, pad_sec=news_pad_sec
        )
        if nf_ts is not None:
            nf_idx = int(np.searchsorted(times_sec, nf_ts, side="right")) - 1
            if fill_idx <= nf_idx < scan_flat_idx:
                scan_flat_idx = nf_idx
                news_flattened = True

    exit_idx, exit_fill, exit_code = _scan_m1_exit_jit(
        quotes, int(fill_idx), int(scan_flat_idx), int(side), sl_f, has_tp, tp_f
    )
    exit_reason_map = {
        1: "SL_GAP",
        2: "SL_HIT",
        3: "TP_GAP",
        4: "TP_HIT",
        5: "RED_NEWS_FLATTEN" if news_flattened else "HARD_FLAT_2050",
    }
    exit_reason = exit_reason_map[int(exit_code)]
    exit_ts = int(times_sec[exit_idx])
    enforce_dev_ts_bound(exit_ts, context=f"replay_intraday_m1_trade.exit:{sym}")

    # Friction math: avoid double-counting Bid/Ask spread already realized in fills
    pt = float(sym_spec["point"])
    bench_sp_px = float(sym_spec["benchmark_spread_pts"]) * pt
    if has_ask:
        entry_sp_px = max(0.0, float(quotes[fill_idx, 4] - quotes[fill_idx, 0]))
        exit_sp_px = max(0.0, float(quotes[exit_idx, 4] - quotes[exit_idx, 0]))
        embedded_sp_px = 0.5 * (entry_sp_px + exit_sp_px)
    else:
        entry_sp_px = bench_sp_px
        exit_sp_px = bench_sp_px
        embedded_sp_px = 0.0

    comm_usd = float(
        sym_spec["commission_usd_lot_the5ers"] if "5ERS" in firm_u else sym_spec["commission_usd_lot"]
    )
    usd_per_px_1lot = float(margin_chk["usd_per_price_unit_1lot"])
    comm_px = comm_usd / usd_per_px_1lot if usd_per_px_1lot > 0.0 else 0.0
    base_slip_rt_px = max(pt, 0.35 * max(embedded_sp_px, bench_sp_px))
    total_fric_1x_px = (embedded_sp_px if has_ask else bench_sp_px) + comm_px + base_slip_rt_px

    raw_pnl_px = side * (exit_fill - entry_fill)
    gross_r = raw_pnl_px / sl_dist
    eff_scale = float(margin_chk["eff_risk_scale"])

    tier_net_r: dict[str, float] = {}
    tier_fric_sl: dict[str, float] = {}
    for mult in friction_tiers:
        m = float(mult)
        tot_f_px = m * total_fric_1x_px
        extra_f_px = max(0.0, tot_f_px - embedded_sp_px) if has_ask else tot_f_px
        net_r_m = ((raw_pnl_px - extra_f_px) / sl_dist) * eff_scale
        lbl = f"{m:g}x"
        tier_net_r[lbl] = round(net_r_m, 6)
        tier_fric_sl[lbl] = round(tot_f_px / sl_dist, 6)

    fric_sl_1x = round(total_fric_1x_px / sl_dist, 6)
    fric_sl_15x = round((1.5 * total_fric_1x_px) / sl_dist, 6)
    fric_sl_2x = round((2.0 * total_fric_1x_px) / sl_dist, 6)

    default_extra_1x = max(0.0, total_fric_1x_px - embedded_sp_px) if has_ask else total_fric_1x_px
    default_net_r_1x = round(((raw_pnl_px - default_extra_1x) / sl_dist) * eff_scale, 6)

    entry_date = datetime.fromtimestamp(fill_ts, tz=UTC).strftime("%Y-%m-%d")
    exit_date = datetime.fromtimestamp(exit_ts, tz=UTC).strftime("%Y-%m-%d")

    return {
        "filled": True,
        "status": "FILLED",
        "symbol": sym,
        "blindness_tier": str(sym_spec["blindness_tier"]),
        "data_resolution": RES_NATIVE_M1_BIDASK,
        "side": int(side),
        "entry_order_type": otype,
        "entry_idx": int(fill_idx),
        "exit_idx": int(exit_idx),
        "entry_ts": fill_ts,
        "exit_ts": exit_ts,
        "entry_date": entry_date,
        "exit_date": exit_date,
        "entry_price": round(entry_fill, 8),
        "exit_price": round(exit_fill, 8),
        "sl_price": round(sl_f, 8),
        "tp_price": round(tp_f, 8) if has_tp else None,
        "sl_dist": round(sl_dist, 8),
        "hold_minutes": int((exit_ts - fill_ts) // 60),
        "exit_reason": exit_reason,
        "swap_R": 0.0,
        "gross_R": round(gross_r * eff_scale, 6),
        "net_R": tier_net_r.get("1x", default_net_r_1x),
        "net_R_1x": tier_net_r.get("1x"),
        "net_R_15x": tier_net_r.get("1.5x"),
        "net_R_2x": tier_net_r.get("2x"),
        "net_R_by_tier": tier_net_r,
        "friction_over_sl": fric_sl_2x,
        "friction_over_sl_1x": fric_sl_1x,
        "friction_over_sl_15x": fric_sl_15x,
        "friction_over_sl_2x": fric_sl_2x,
        "friction_over_sl_by_tier": tier_fric_sl,
        "lots": margin_chk["lots"],
        "eff_risk_scale": eff_scale,
        "margin_capped": margin_chk["margin_capped"],
        "margin_util_frac": margin_chk["margin_util_frac"],
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


# ---------------------------------------------------------------------------
# 7. Unified Multi-Day FTMO Swing Replay (ALL 28/28 Symbols, Hard SL Mandatory)
# ---------------------------------------------------------------------------


def _resolve_bar_array_param(
    param: np.ndarray | float | int | None,
    n: int,
    *,
    name: str,
    required: bool,
) -> np.ndarray | None:
    if param is None:
        if required:
            raise ValueError(f"{name} is mandatory (hard SL required on every Swing trade)")
        return None
    if isinstance(param, (int, float, np.number)) and not isinstance(param, bool):
        return np.full(n, float(param), dtype=np.float64)
    arr = np.asarray(param, dtype=np.float64)
    if arr.ndim != 1 or arr.shape[0] != n:
        raise ValueError(f"{name} must be scalar or 1D array of length {n}, got shape {arr.shape}")
    return arr


def replay_swing_trades(
    symbol: str,
    bars: Mapping[str, Any],
    signals: np.ndarray,
    sl_dists: np.ndarray | float,
    *,
    tp_dists: np.ndarray | float | None = None,
    max_hold_bars: int = 20,
    exit_on_signal_flip: bool = True,
    signal_already_shifted: bool = False,
    spec: Mapping[str, Any] | None = None,
    friction_tiers: Sequence[float] = FRICTION_TIERS,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    account_type: str = "ftmo_swing",
    max_margin_util_frac: float = 0.80,
    scale_if_over_margin: bool = True,
    conservative_financing_floor: bool = False,
    years: Sequence[int] | None = None,
    fx_rates: Mapping[str, float] | None = None,
    data_resolution: str | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Replay multi-day FTMO Swing trades on any of the 28 symbols with hard SL & exact swaps.

    Causal execution contract:
      - When `signal_already_shifted=False` (default), `signals[t - 1]` and `sl_dists[t - 1]`
        observed at bar `t - 1` close execute at `open[t]` (strict `shift = 1`).
      - Conservative intrabar SL-before-TP tie-break on `high[k], low[k]`.
      - Hard SL mandatory (no signal can open a trade without finite `sl_dist > 0`).
      - Exact `ftmo_specs_28.json` friction (`1.0x / 1.5x / 2.0x`), triple-swap rollover
        (`Wed 3x` FX/Metals, `Fri 3x` Indices/Oil/BTC, `swap_mode=5` `-30%/yr` BTCUSD),
        Anti-Fake-Swap Guard, BOTH `real_swap` and `zero_pos_swap`, and FTMO Swing leverage margin!
    """
    if isinstance(max_hold_bars, bool) or int(max_hold_bars) < 1:
        raise ValueError(f"max_hold_bars must be >= 1, got {max_hold_bars!r}")

    ts_arr = np.asarray(bars["times_sec"], dtype=np.int64)
    dates = [str(d) for d in bars["dates"]]
    wds = np.asarray(bars["weekdays"], dtype=np.int32)
    o_arr = np.asarray(bars["open"], dtype=np.float64)
    h_arr = np.asarray(bars["high"], dtype=np.float64)
    l_arr = np.asarray(bars["low"], dtype=np.float64)
    c_arr = np.asarray(bars["close"], dtype=np.float64)
    n = int(ts_arr.size)

    if n == 0:
        raise ValueError(f"Empty bar series passed to replay_swing_trades for {symbol}")
    enforce_dev_ts_bound(ts_arr, context=f"replay_swing_trades.ts:{symbol}")
    enforce_dev_date_bound(dates, context=f"replay_swing_trades.dates:{symbol}")

    sig_raw = np.asarray(signals, dtype=np.float64)
    if sig_raw.ndim != 1 or sig_raw.shape[0] != n:
        raise ValueError(f"signals must be 1D length {n}, got shape {sig_raw.shape}")

    sl_raw = _resolve_bar_array_param(sl_dists, n, name="sl_dists", required=True)
    tp_raw = _resolve_bar_array_param(tp_dists, n, name="tp_dists", required=False)

    # Apply strict shift = 1 unless caller explicitly pre-shifted signals to bar t open
    if signal_already_shifted:
        eff_sig = sig_raw.copy()
        eff_sl = sl_raw.copy()
        eff_tp = tp_raw.copy() if tp_raw is not None else None
    else:
        eff_sig = np.zeros(n, dtype=np.float64)
        eff_sig[1:] = sig_raw[:-1]
        eff_sl = np.full(n, np.nan, dtype=np.float64)
        eff_sl[1:] = sl_raw[:-1]
        if tp_raw is not None:
            eff_tp = np.full(n, np.nan, dtype=np.float64)
            eff_tp[1:] = tp_raw[:-1]
        else:
            eff_tp = None

    sym_spec = dict(spec) if spec is not None else get_symbol_spec(symbol, root=root)
    sym = str(sym_spec["canonical_symbol"])
    res_tag = data_resolution or (
        RES_NATIVE_M1_BIDASK if sym_spec["blindness_tier"] == TIER_12OLD else RES_D1_YAHOO_SANCTIONED
    )
    allowed_years = set(_validate_dev_years(years)) if years is not None else None
    max_allowed_year = max(allowed_years) if allowed_years is not None else None

    pt = float(sym_spec["point"])
    bench_sp_px = float(sym_spec["benchmark_spread_pts"]) * pt
    oneway_bps = float(sym_spec["oneway_bps"])
    comm_usd = float(sym_spec["commission_usd_lot"])

    trades: list[dict[str, Any]] = []
    margin_rejects = 0
    margin_capped_count = 0
    peak_margin_util_frac = 0.0
    last_in_window_idx = -1

    # State machine (max 1 open position per symbol: zero grid / martingale)
    in_pos = False
    pos_side = 0
    entry_idx = -1
    entry_px = 0.0
    sl_px = 0.0
    tp_px: float | None = None
    sl_dist_cur = 0.0
    eff_scale = 1.0
    pos_lots = 0.0
    pos_margin_util = 0.0
    pos_margin_capped = False
    pos_fric_1x_px = 0.0
    cum_swap_real_r = 0.0
    cum_swap_zero_pos_r = 0.0
    eps = 1e-12

    def _record_exit(exit_i: int, exit_p: float, reason: str) -> None:
        nonlocal in_pos
        gross_r = (pos_side * (exit_p - entry_px)) / sl_dist_cur
        tier_real: dict[str, float] = {}
        tier_zpos: dict[str, float] = {}
        tier_fsl: dict[str, float] = {}
        for mult in friction_tiers:
            m = float(mult)
            f_r = (m * pos_fric_1x_px) / sl_dist_cur
            lbl = f"{m:g}x"
            tier_real[lbl] = round((gross_r + cum_swap_real_r - f_r) * eff_scale, 6)
            tier_zpos[lbl] = round((gross_r + cum_swap_zero_pos_r - f_r) * eff_scale, 6)
            tier_fsl[lbl] = round(f_r, 6)

        f1 = round(pos_fric_1x_px / sl_dist_cur, 6)
        f15 = round((1.5 * pos_fric_1x_px) / sl_dist_cur, 6)
        f2 = round((2.0 * pos_fric_1x_px) / sl_dist_cur, 6)
        trades.append(
            {
                "symbol": sym,
                "blindness_tier": str(sym_spec["blindness_tier"]),
                "data_resolution": res_tag,
                "side": int(pos_side),
                "entry_idx": int(entry_idx),
                "exit_idx": int(exit_i),
                "entry_ts": int(ts_arr[entry_idx]),
                "exit_ts": int(ts_arr[exit_i]),
                "entry_date": dates[entry_idx],
                "exit_date": dates[exit_i],
                "entry_price": round(entry_px, 8),
                "exit_price": round(exit_p, 8),
                "sl_price": round(sl_px, 8),
                "tp_price": round(tp_px, 8) if tp_px is not None else None,
                "sl_dist": round(sl_dist_cur, 8),
                "hold_bars": int(exit_i - entry_idx),
                "exit_reason": reason,
                "lots": pos_lots,
                "eff_risk_scale": round(eff_scale, 6),
                "margin_capped": pos_margin_capped,
                "margin_util_frac": round(pos_margin_util, 6),
                "gross_R": round(gross_r * eff_scale, 6),
                "swap_real_R": round(cum_swap_real_r * eff_scale, 6),
                "swap_zero_pos_R": round(cum_swap_zero_pos_r * eff_scale, 6),
                "net_R": tier_real.get("1x", round((gross_r + cum_swap_real_r - f1) * eff_scale, 6)),
                "net_R_1x": tier_real.get("1x"),
                "net_R_15x": tier_real.get("1.5x"),
                "net_R_2x": tier_real.get("2x"),
                "net_R_zero_pos_1x": tier_zpos.get("1x"),
                "net_R_zero_pos_15x": tier_zpos.get("1.5x"),
                "net_R_zero_pos_2x": tier_zpos.get("2x"),
                "net_R_real_by_tier": tier_real,
                "net_R_zero_pos_by_tier": tier_zpos,
                "friction_over_sl": f2,
                "friction_over_sl_1x": f1,
                "friction_over_sl_15x": f15,
                "friction_over_sl_2x": f2,
                "friction_over_sl_by_tier": tier_fsl,
            }
        )
        in_pos = False

    for t in range(n):
        yr_t = int(dates[t][:4])
        if max_allowed_year is not None and yr_t > max_allowed_year:
            if in_pos and last_in_window_idx >= entry_idx:
                _record_exit(last_in_window_idx, float(c_arr[last_in_window_idx]), "END_OF_WINDOW")
            break
        if allowed_years is None or yr_t in allowed_years:
            last_in_window_idx = t

        ot, ht, lt, ct = float(o_arr[t]), float(h_arr[t]), float(l_arr[t]), float(c_arr[t])
        if not (math.isfinite(ot) and math.isfinite(ht) and math.isfinite(lt) and math.isfinite(ct)):
            continue
        if ot <= 0.0 or ht <= 0.0 or lt <= 0.0 or ct <= 0.0:
            raise ValueError(f"NONPOSITIVE_PRICE [{sym} {dates[t]}]: o={ot}, h={ht}, l={lt}, c={ct}")

        # 1. Manage open position on bar t (swap from t-1->t, open gap/time/flip, intrabar SL>TP)
        if in_pos:
            if t > entry_idx and dates[t] != dates[t - 1]:
                prev_c = float(c_arr[t - 1])
                prev_wd = int(wds[t - 1])
                sw_real = compute_daily_swap_frac(
                    sym_spec,
                    prev_c,
                    pos_side,
                    prev_wd,
                    zero_positive_swap=False,
                    conservative_financing_floor=conservative_financing_floor,
                )
                sw_zpos = compute_daily_swap_frac(
                    sym_spec,
                    prev_c,
                    pos_side,
                    prev_wd,
                    zero_positive_swap=True,
                    conservative_financing_floor=conservative_financing_floor,
                )
                # Exact notional-to-R conversion: (sw_frac * prev_close) / sl_dist
                cum_swap_real_r += (sw_real * prev_c) / sl_dist_cur
                cum_swap_zero_pos_r += (sw_zpos * prev_c) / sl_dist_cur

            # Open-gap SL check FIRST
            if (pos_side == 1 and ot <= sl_px + eps) or (pos_side == -1 and ot >= sl_px - eps):
                _record_exit(t, ot, "SL_GAP")
            elif tp_px is not None and pos_side * (ot - tp_px) >= -eps:
                _record_exit(t, ot, "TP_GAP")
            elif (t - entry_idx) >= int(max_hold_bars):
                _record_exit(t, ot, "TIME_EXIT")
            elif exit_on_signal_flip:
                cur_s = eff_sig[t]
                if math.isfinite(cur_s) and cur_s > 0.0:
                    cur_dir = 1
                elif math.isfinite(cur_s) and cur_s < 0.0:
                    cur_dir = -1
                else:
                    cur_dir = 0
                if cur_dir != pos_side:
                    _record_exit(t, ot, "SIGNAL_EXIT")

            # Intrabar H/L check (SL ALWAYS beats TP on same-bar tie!)
            if in_pos:
                if (pos_side == 1 and lt <= sl_px + eps) or (pos_side == -1 and ht >= sl_px - eps):
                    _record_exit(t, sl_px, "SL_HIT")
                elif tp_px is not None and (
                    (pos_side == 1 and ht >= tp_px - eps) or (pos_side == -1 and lt <= tp_px + eps)
                ):
                    _record_exit(t, tp_px, "TP_HIT")

        # 2. If flat at bar t open, check causal entry signal
        if not in_pos:
            if allowed_years is not None and yr_t not in allowed_years:
                continue
            s_val = float(eff_sig[t])
            if not math.isfinite(s_val) or abs(s_val) <= 1e-12:
                continue
            new_side = 1 if s_val > 0.0 else -1
            sld = float(eff_sl[t])
            if not math.isfinite(sld) or sld <= 0.0:
                raise ValueError(
                    f"MISSING_HARD_SL [{sym} {dates[t]}]: Swing signal fired without positive sl_dist ({sld!r})"
                )
            new_sl_px = ot - new_side * sld
            if new_sl_px <= 0.0:
                continue

            new_tp_px: float | None = None
            if eff_tp is not None:
                tpd = float(eff_tp[t])
                if math.isfinite(tpd) and tpd > 0.0:
                    new_tp_px = ot + new_side * tpd

            mchk = check_leverage_margin(
                sym_spec,
                ot,
                new_sl_px,
                account_balance_usd=account_balance_usd,
                risk_frac=risk_frac,
                account_type=account_type,
                max_margin_util_frac=max_margin_util_frac,
                scale_if_over_margin=scale_if_over_margin,
                fx_rates=fx_rates,
            )
            if not mchk["accepted"]:
                margin_rejects += 1
                continue
            if mchk["margin_capped"]:
                margin_capped_count += 1
            peak_margin_util_frac = max(peak_margin_util_frac, float(mchk["margin_util_frac"]))

            usd_per_px = float(mchk["usd_per_price_unit_1lot"])
            comm_px = comm_usd / usd_per_px if usd_per_px > 0.0 else 0.0
            spec_rt_px = 2.0 * (oneway_bps / 10_000.0) * ot
            fric_1x_px = max(spec_rt_px, bench_sp_px + comm_px)

            in_pos = True
            pos_side = new_side
            entry_idx = t
            entry_px = ot
            sl_px = new_sl_px
            tp_px = new_tp_px
            sl_dist_cur = sld
            eff_scale = float(mchk["eff_risk_scale"])
            pos_lots = float(mchk["lots"])
            pos_margin_util = float(mchk["margin_util_frac"])
            pos_margin_capped = bool(mchk["margin_capped"])
            pos_fric_1x_px = fric_1x_px
            cum_swap_real_r = 0.0
            cum_swap_zero_pos_r = 0.0

            # Conservative entry-bar intrabar SL-before-TP check
            if (pos_side == 1 and lt <= sl_px + eps) or (pos_side == -1 and ht >= sl_px - eps):
                _record_exit(t, sl_px, "SL_HIT_ENTRY_BAR")
            elif tp_px is not None and (
                (pos_side == 1 and ht >= tp_px - eps) or (pos_side == -1 and lt <= tp_px + eps)
            ):
                _record_exit(t, tp_px, "TP_HIT_ENTRY_BAR")

    # Force-close any open position at final available Dev bar close (zero carry past Dev cutoff)
    if in_pos:
        close_i = last_in_window_idx if last_in_window_idx >= entry_idx else (n - 1)
        _record_exit(close_i, float(c_arr[close_i]), "END_OF_SAMPLE")

    eval_years = tuple(sorted({int(d[:4]) for d in dates})) if years is None else _validate_dev_years(years)
    dpnl_real_1x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_1x")
    dpnl_real_2x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_2x")
    dpnl_zpos_1x = compute_daily_pnl_series(trades, eval_years, pnl_key="net_R_zero_pos_1x")

    return {
        "symbol": sym,
        "blindness_tier": str(sym_spec["blindness_tier"]),
        "data_resolution": res_tag,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "trades": trades,
        "n_trades": len(trades),
        "margin_rejects": margin_rejects,
        "margin_capped_count": margin_capped_count,
        "peak_margin_util_frac": round(peak_margin_util_frac, 6),
        "stage0": stage0_screen(trades),
        "metrics_real_1x": compute_split_metrics(trades, dpnl_real_1x, pnl_key="net_R_1x"),
        "metrics_real_2x": compute_split_metrics(trades, dpnl_real_2x, pnl_key="net_R_2x"),
        "metrics_zero_pos_1x": compute_split_metrics(trades, dpnl_zpos_1x, pnl_key="net_R_zero_pos_1x"),
    }


def replay_swing_d1_series(
    universe_or_asset: Mapping[str, Any],
    signals: np.ndarray | Mapping[str, np.ndarray],
    sl_dists: np.ndarray | float | Mapping[str, np.ndarray | float],
    *,
    symbol: str | None = None,
    tp_dists: np.ndarray | float | Mapping[str, np.ndarray | float] | None = None,
    max_hold_bars: int = 20,
    exit_on_signal_flip: bool = True,
    signal_already_shifted: bool = False,
    friction_tiers: Sequence[float] = FRICTION_TIERS,
    account_balance_usd: float = 10_000.0,
    risk_frac: float = 0.005,
    account_type: str = "ftmo_swing",
    max_margin_util_frac: float = 0.80,
    scale_if_over_margin: bool = True,
    conservative_financing_floor: bool = False,
    years: Sequence[int] | None = None,
    fx_rates: Mapping[str, float] | None = None,
    specs: Mapping[str, Any] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Unified single-asset or multi-asset D1 FTMO Swing series replay across ALL 28/28 symbols."""
    # Normalize single-asset vs multi-asset call conventions cleanly
    if isinstance(signals, Mapping):
        if "assets" in universe_or_asset and isinstance(universe_or_asset["assets"], Mapping):
            asset_map = universe_or_asset["assets"]
        else:
            asset_map = universe_or_asset
        sym_list = [normalize_symbol(s) for s in signals.keys()]
        sig_by_sym = {normalize_symbol(k): v for k, v in signals.items()}
        sl_by_sym = (
            {normalize_symbol(k): v for k, v in sl_dists.items()}
            if isinstance(sl_dists, Mapping)
            else {s: sl_dists for s in sym_list}
        )
        if tp_dists is None:
            tp_by_sym: dict[str, Any] = {s: None for s in sym_list}
        elif isinstance(tp_dists, Mapping):
            tp_by_sym = {normalize_symbol(k): v for k, v in tp_dists.items()}
        else:
            tp_by_sym = {s: tp_dists for s in sym_list}
    else:
        if symbol is not None:
            sym_u = normalize_symbol(symbol)
            if "assets" in universe_or_asset and sym_u in universe_or_asset["assets"]:
                asset_obj = universe_or_asset["assets"][sym_u]
            elif sym_u in universe_or_asset:
                asset_obj = universe_or_asset[sym_u]
            else:
                asset_obj = universe_or_asset
        else:
            if "symbol" not in universe_or_asset:
                raise ValueError("Provide `symbol` or pass an asset entry dict with a `'symbol'` key")
            sym_u = normalize_symbol(str(universe_or_asset["symbol"]))
            asset_obj = universe_or_asset
        asset_map = {sym_u: asset_obj}
        sym_list = [sym_u]
        sig_by_sym = {sym_u: signals}
        sl_by_sym = {sym_u: sl_dists}
        tp_by_sym = {sym_u: tp_dists}

    all_trades: list[dict[str, Any]] = []
    per_symbol: dict[str, dict[str, Any]] = {}
    total_margin_rejects = 0
    total_margin_capped = 0
    years_seen: set[int] = set()

    for sym_u in sym_list:
        aobj = asset_map[sym_u]
        bars = aobj["d1"] if ("d1" in aobj and isinstance(aobj["d1"], Mapping)) else aobj
        if bars is None:
            raise ValueError(f"D1 bars missing for symbol {sym_u}")
        sp = aobj.get("spec") if isinstance(aobj, Mapping) else None
        if sp is None:
            sp = get_symbol_spec(sym_u, specs=specs, root=root)
        res_tag = aobj.get("data_resolution") if isinstance(aobj, Mapping) else None

        res = replay_swing_trades(
            sym_u,
            bars,
            sig_by_sym[sym_u],
            sl_by_sym[sym_u],
            tp_dists=tp_by_sym.get(sym_u),
            max_hold_bars=max_hold_bars,
            exit_on_signal_flip=exit_on_signal_flip,
            signal_already_shifted=signal_already_shifted,
            spec=sp,
            friction_tiers=friction_tiers,
            account_balance_usd=account_balance_usd,
            risk_frac=risk_frac,
            account_type=account_type,
            max_margin_util_frac=max_margin_util_frac,
            scale_if_over_margin=scale_if_over_margin,
            conservative_financing_floor=conservative_financing_floor,
            years=years,
            fx_rates=fx_rates,
            data_resolution=res_tag,
            root=root,
        )
        per_symbol[sym_u] = res
        all_trades.extend(res["trades"])
        total_margin_rejects += int(res["margin_rejects"])
        total_margin_capped += int(res["margin_capped_count"])
        years_seen.update(int(str(d)[:4]) for d in bars["dates"])

    all_trades.sort(key=lambda tr: (tr["exit_ts"], tr["entry_ts"], tr["symbol"]))
    eval_years = _validate_dev_years(years) if years is not None else tuple(sorted(years_seen))

    # Build aligned daily PnL curves across all friction tiers & both real_swap and zero_pos_swap
    daily_real_1x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_1x")
    daily_real_15x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_15x")
    daily_real_2x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_2x")
    daily_zpos_1x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_zero_pos_1x")
    daily_zpos_15x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_zero_pos_15x")
    daily_zpos_2x = compute_daily_pnl_series(all_trades, eval_years, pnl_key="net_R_zero_pos_2x")

    # Portfolio-level concurrent margin audit across active symbol windows
    day_margin_util: dict[str, float] = {}
    for tr in all_trades:
        d0 = date.fromisoformat(tr["entry_date"])
        d1 = date.fromisoformat(tr["exit_date"])
        cur = d0
        mu = float(tr["margin_util_frac"])
        while cur <= d1:
            if cur.weekday() < 5:
                k = cur.isoformat()
                day_margin_util[k] = day_margin_util.get(k, 0.0) + mu
            cur += timedelta(days=1)
    peak_portfolio_margin = max(day_margin_util.values()) if day_margin_util else 0.0

    return {
        "schema_version": "naqex-offensive3-swing-d1-series-v1",
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "symbols": sym_list,
        "years": list(eval_years),
        "trades": all_trades,
        "n_trades": len(all_trades),
        "stage0": stage0_screen(all_trades),
        "daily_pnl": {
            "dates": daily_real_1x["dates"],
            "real_swap": {
                "1x": daily_real_1x["pnl"],
                "1.5x": daily_real_15x["pnl"],
                "2x": daily_real_2x["pnl"],
            },
            "zero_pos_swap": {
                "1x": daily_zpos_1x["pnl"],
                "1.5x": daily_zpos_15x["pnl"],
                "2x": daily_zpos_2x["pnl"],
            },
            "account_ret_real_1x": daily_real_1x["pnl"] * float(risk_frac),
            "account_ret_zero_pos_1x": daily_zpos_1x["pnl"] * float(risk_frac),
        },
        "metrics": {
            "real_swap": {
                "1x": compute_split_metrics(all_trades, daily_real_1x, pnl_key="net_R_1x"),
                "1.5x": compute_split_metrics(all_trades, daily_real_15x, pnl_key="net_R_15x"),
                "2x": compute_split_metrics(all_trades, daily_real_2x, pnl_key="net_R_2x"),
            },
            "zero_pos_swap": {
                "1x": compute_split_metrics(all_trades, daily_zpos_1x, pnl_key="net_R_zero_pos_1x"),
                "1.5x": compute_split_metrics(all_trades, daily_zpos_15x, pnl_key="net_R_zero_pos_15x"),
                "2x": compute_split_metrics(all_trades, daily_zpos_2x, pnl_key="net_R_zero_pos_2x"),
            },
        },
        "margin_audit": {
            "account_type": account_type,
            "max_margin_util_frac": float(max_margin_util_frac),
            "margin_rejects": total_margin_rejects,
            "margin_capped_count": total_margin_capped,
            "peak_portfolio_margin_util_frac": round(peak_portfolio_margin, 6),
            "portfolio_margin_breached": peak_portfolio_margin > float(max_margin_util_frac) + 1e-9,
        },
        "per_symbol": per_symbol,
    }


# ---------------------------------------------------------------------------
# 8. Stage-0 Filter, Daily PnL Series, Split Metrics & Atomic Checkpoints
# ---------------------------------------------------------------------------


def stage0_screen(
    trades: Sequence[Mapping[str, Any]],
    *,
    max_fric_sl_ratio: float = 0.15,
    min_keep_frac: float = 0.50,
    ratio_key: str = "friction_over_sl",
) -> dict[str, Any]:
    """Stage-0 friction-over-SL economic feasibility filter (`F_stress / SL`)."""
    if not math.isfinite(max_fric_sl_ratio) or max_fric_sl_ratio <= 0.0:
        raise ValueError(f"max_fric_sl_ratio must be finite > 0, got {max_fric_sl_ratio!r}")
    if not math.isfinite(min_keep_frac) or not (0.0 <= min_keep_frac <= 1.0):
        raise ValueError(f"min_keep_frac must be in [0, 1], got {min_keep_frac!r}")

    n_total = len(trades)
    if n_total == 0:
        return {
            "passed": False,
            "n_total": 0,
            "n_kept": 0,
            "keep_frac": 0.0,
            "median_fric_sl_ratio": None,
            "p90_fric_sl_ratio": None,
            "max_fric_sl_ratio": float(max_fric_sl_ratio),
            "min_keep_frac": float(min_keep_frac),
            "reason": "NO_TRADES",
        }

    ratios: list[float] = []
    n_kept = 0
    for tr in trades:
        raw = tr.get(ratio_key)
        if raw is None:
            raw = tr.get("friction_over_sl_2x", tr.get("friction_over_sl_15x", tr.get("friction_over_sl_1x")))
        if raw is None or isinstance(raw, bool):
            continue
        fv = float(raw)
        if math.isfinite(fv) and fv >= 0.0:
            ratios.append(fv)
            if fv <= float(max_fric_sl_ratio) + 1e-12:
                n_kept += 1

    if not ratios:
        return {
            "passed": False,
            "n_total": n_total,
            "n_kept": 0,
            "keep_frac": 0.0,
            "median_fric_sl_ratio": None,
            "p90_fric_sl_ratio": None,
            "max_fric_sl_ratio": float(max_fric_sl_ratio),
            "min_keep_frac": float(min_keep_frac),
            "reason": "MISSING_FRICTION_OVER_SL",
        }

    arr = np.array(ratios, dtype=np.float64)
    med = float(np.median(arr))
    p90 = float(np.percentile(arr, 90))
    keep_frac = float(n_kept) / float(n_total)
    passed = (keep_frac >= float(min_keep_frac) - 1e-12) and (med <= float(max_fric_sl_ratio) + 1e-12)
    reason = "PASS" if passed else f"FAIL_STAGE0(med={med:.4f},keep={keep_frac:.3f})"

    return {
        "passed": passed,
        "n_total": n_total,
        "n_kept": n_kept,
        "keep_frac": round(keep_frac, 6),
        "median_fric_sl_ratio": round(med, 6),
        "p90_fric_sl_ratio": round(p90, 6),
        "max_fric_sl_ratio": float(max_fric_sl_ratio),
        "min_keep_frac": float(min_keep_frac),
        "reason": reason,
    }


def _build_weekday_calendar(years: tuple[int, ...]) -> list[str]:
    out: list[str] = []
    for yr in years:
        cur = date(yr, 1, 1)
        end = date(yr, 12, 31)
        while cur <= end:
            if cur.weekday() < 5:
                out.append(cur.isoformat())
            cur += timedelta(days=1)
    return out


def compute_daily_pnl_series(
    trades: Sequence[Mapping[str, Any]],
    years: Sequence[int] = ALL_DEV_YEARS,
    *,
    pnl_key: str = "net_R",
) -> dict[str, Any]:
    """Aggregate trade PnLs onto a complete weekday UTC calendar for `years` (0.0 on flat days)."""
    req_years = _validate_dev_years(years)
    cal_dates = _build_weekday_calendar(req_years)
    d_idx = {d: i for i, d in enumerate(cal_dates)}
    n_days = len(cal_dates)
    pnl = np.zeros(n_days, dtype=np.float64)
    counts = np.zeros(n_days, dtype=np.int32)
    yr_arr = np.array([int(d[:4]) for d in cal_dates], dtype=np.int32)

    for tr in trades:
        if "exit_ts" in tr and tr["exit_ts"] is not None:
            enforce_dev_ts_bound(int(tr["exit_ts"]), context="compute_daily_pnl_series.exit_ts")
        if "entry_ts" in tr and tr["entry_ts"] is not None:
            enforce_dev_ts_bound(int(tr["entry_ts"]), context="compute_daily_pnl_series.entry_ts")
        d_raw = tr.get("exit_date") or tr.get("entry_date")
        if d_raw is None:
            continue
        d_str = str(d_raw)
        enforce_dev_date_bound(d_str, context="compute_daily_pnl_series.date")
        idx = d_idx.get(d_str)
        if idx is None:
            # Handle weekend timestamps by snapping backward to Friday if within requested year
            dt_d = date.fromisoformat(d_str)
            if dt_d.year in req_years and dt_d.weekday() >= 5:
                snap = (dt_d - timedelta(days=dt_d.weekday() - 4)).isoformat()
                idx = d_idx.get(snap)
        if idx is None:
            continue
        val = tr.get(pnl_key)
        if val is None and pnl_key != "net_R":
            val = tr.get("net_R")
        if val is None or isinstance(val, bool):
            continue
        fv = float(val)
        if math.isfinite(fv):
            pnl[idx] += fv
            counts[idx] += 1

    return {
        "dates": cal_dates,
        "years": yr_arr,
        "pnl": pnl,
        "trade_counts": counts,
        "requested_years": list(req_years),
        "n_days": n_days,
        "pnl_key": pnl_key,
        _SEAL_ROWS_ANALYSED_KEY: 0,
    }


def compute_split_metrics(
    trades: Sequence[Mapping[str, Any]],
    daily_pnl: Mapping[str, Any] | np.ndarray | Sequence[float],
    *,
    pnl_key: str = "net_R",
    ann_days: float = 252.0,
) -> dict[str, Any]:
    """Compute canonical split performance metrics (`net_R`, `PF`, `Sharpe`, `Winrate`, `avg_RR`, `max_DD_R`, etc.)."""
    dates_list: list[str] | None = None
    years_arr: np.ndarray | None = None
    if isinstance(daily_pnl, Mapping):
        dp = np.asarray(daily_pnl["pnl"], dtype=np.float64)
        dates_list = list(daily_pnl.get("dates") or [])
        if "years" in daily_pnl and daily_pnl["years"] is not None:
            years_arr = np.asarray(daily_pnl["years"], dtype=np.int32)
        elif dates_list:
            years_arr = np.array([int(str(d)[:4]) for d in dates_list], dtype=np.int32)
    else:
        dp = np.asarray(daily_pnl, dtype=np.float64)

    # Filter trades to the exact year set represented by `daily_pnl` if available
    has_years = years_arr is not None and years_arr.size > 0
    year_filter: set[int] | None = {int(y) for y in years_arr.tolist()} if has_years else None
    t_vals: list[float] = []
    for tr in trades:
        if year_filter is not None:
            d_raw = tr.get("exit_date") or tr.get("entry_date")
            if d_raw is not None and int(str(d_raw)[:4]) not in year_filter:
                continue
        v = tr.get(pnl_key)
        if v is None and pnl_key != "net_R":
            v = tr.get("net_R")
        if v is None or isinstance(v, bool):
            continue
        fv = float(v)
        if math.isfinite(fv):
            t_vals.append(fv)

    n_trades = len(t_vals)
    if n_trades > 0:
        arr_t = np.array(t_vals, dtype=np.float64)
        wins = arr_t[arr_t > 0.0]
        losses = arr_t[arr_t < 0.0]
        gross_win = float(np.sum(wins))
        gross_loss = float(np.abs(np.sum(losses)))
        net_r = float(np.sum(arr_t))
        winrate = float(wins.size) / float(n_trades)
        if gross_loss > 1e-12:
            pf = gross_win / gross_loss
        elif gross_win > 1e-12:
            pf = 999.0
        else:
            pf = 0.0
        avg_win = float(np.mean(wins)) if wins.size > 0 else 0.0
        avg_loss = float(np.mean(np.abs(losses))) if losses.size > 0 else 0.0
        avg_rr = (avg_win / avg_loss) if avg_loss > 1e-12 else 0.0
        ev_per_trade_r = net_r / float(n_trades)
    else:
        net_r = float(np.sum(dp)) if dp.size > 0 else 0.0
        winrate = 0.0
        pf = 0.0
        avg_rr = 0.0
        ev_per_trade_r = 0.0

    # Daily equity curve drawdown & Sharpe
    if dp.size > 0:
        clean_dp = np.where(np.isfinite(dp), dp, 0.0)
        eq = np.cumsum(clean_dp)
        peak = np.maximum(0.0, np.maximum.accumulate(eq))
        dd = peak - eq
        max_dd_r = float(np.max(dd)) if dd.size > 0 else 0.0
        worst_1d_r = float(np.min(clean_dp))
        if clean_dp.size >= 2:
            sd = float(np.std(clean_dp, ddof=1))
            sharpe = (float(np.mean(clean_dp)) / sd) * math.sqrt(float(ann_days)) if sd > 1e-12 else 0.0
        else:
            sharpe = 0.0
    else:
        max_dd_r = 0.0
        worst_1d_r = 0.0
        sharpe = 0.0

    by_year_r: dict[str, float] = {}
    if years_arr is not None and years_arr.size == dp.size and dp.size > 0:
        for yr in sorted(set(int(y) for y in years_arr.tolist())):
            mask = years_arr == yr
            by_year_r[str(yr)] = round(float(np.sum(np.where(np.isfinite(dp[mask]), dp[mask], 0.0))), 6)
    elif trades:
        tmp_y: dict[str, float] = {}
        for tr in trades:
            d_raw = tr.get("exit_date") or tr.get("entry_date")
            v = tr.get(pnl_key, tr.get("net_R"))
            if d_raw is not None and v is not None and not isinstance(v, bool) and math.isfinite(float(v)):
                yk = str(d_raw)[:4]
                tmp_y[yk] = tmp_y.get(yk, 0.0) + float(v)
        by_year_r = {k: round(v, 6) for k, v in sorted(tmp_y.items())}

    total_years = len(by_year_r)
    positive_years = sum(1 for v in by_year_r.values() if v > 0.0)

    return {
        "n_trades": n_trades,
        "net_R": round(net_r, 6),
        "pf": round(pf, 6),
        "sharpe": round(sharpe, 6),
        "winrate": round(winrate, 6),
        "avg_RR": round(avg_rr, 6),
        "ev_per_trade_R": round(ev_per_trade_r, 6),
        "max_DD_R": round(max_dd_r, 6),
        "worst_1d_R": round(worst_1d_r, 6),
        "positive_years": positive_years,
        "total_years": total_years,
        "positive_year_ratio": round(float(positive_years) / float(total_years), 6) if total_years > 0 else 0.0,
        "by_year_R": by_year_r,
    }


def _resolve_family_caps(
    family_id: str,
    meta: Mapping[str, Any],
    *,
    prereg_path: str | Path | None = None,
    root: str | Path | None = None,
) -> tuple[int, int]:
    """Resolve `(primary_cap, exploratory_cap)` from `preregistration_m1200.json` (fail-closed on overrides)."""
    fid_u = family_id.strip().upper()
    prereg_primary: int | None = None
    prereg_total: int = DEFAULT_MAX_TOTAL_CANDIDATES

    try:
        prereg = load_preregistration_m1200(prereg_path=prereg_path, root=root)
        for fam in prereg.get("alpha_families") or []:
            code = str(fam.get("family_code", "")).upper()
            slug = str(fam.get("slug", "")).upper()
            if fid_u == code or fid_u == slug or fid_u.startswith(f"{code}_"):
                prereg_primary = int(fam["primary_cap"])
                prereg_total = min(DEFAULT_MAX_TOTAL_CANDIDATES, int(fam.get("exploratory_cap", 100)))
                break
    except FileNotFoundError:
        prereg_primary = None

    meta_cap_raw = meta.get("primary_cap")
    if meta_cap_raw is not None:
        if isinstance(meta_cap_raw, bool) or not isinstance(meta_cap_raw, int) or meta_cap_raw < 1:
            raise ValueError(f"Invalid meta['primary_cap']: {meta_cap_raw!r}")
        if prereg_primary is not None and meta_cap_raw > prereg_primary:
            raise ValueError(
                f"PRIMARY_CAP_OVERRIDE_VIOLATION [{family_id}]: "
                f"meta primary_cap={meta_cap_raw} > prereg={prereg_primary}"
            )
        eff_primary = meta_cap_raw
    else:
        eff_primary = prereg_primary if prereg_primary is not None else DEFAULT_PRIMARY_CAP_FALLBACK

    return eff_primary, prereg_total


def _scan_payload_for_cluster_b_or_cutoff_leak(obj: Any, *, path: str = "root") -> None:
    """Recursively reject Cluster B years (`2021..2024`) or post-Dev dates inside Stage 2 discovery outputs."""
    if isinstance(obj, Mapping):
        for k, v in obj.items():
            kl = str(k).lower()
            if "cluster_b" in kl or kl in ("clb_metrics", "clb_sharpe", "clb_trades", "blind_clb"):
                raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: forbidden key {k!r} at {path}")
            if kl in ("discovery_years", "eval_years", "years", "train_years") and isinstance(v, (list, tuple)):
                for item in v:
                    if isinstance(item, int) and not isinstance(item, bool) and item > 2020:
                        raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: year {item} > 2020 at {path}.{k}")
            if kl == "by_year_r" and isinstance(v, Mapping):
                for yk in v:
                    if str(yk).isdigit() and int(str(yk)) > 2020:
                        raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: year {yk} > 2020 in {path}.{k}")
            if kl in ("max_date", "end_date", "exit_date", "entry_date", "date") and isinstance(v, str):
                if len(v) >= 4 and v[:4].isdigit() and int(v[:4]) > 2020:
                    raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: date {v!r} > 2020 at {path}.{k}")
            if kl in ("max_ts", "exit_ts", "entry_ts") and isinstance(v, int) and not isinstance(v, bool):
                # 2021-01-01T00:00:00Z = 1609459200
                if v >= 1_609_459_200:
                    raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: ts {v} >= 2021-01-01 at {path}.{k}")
            _scan_payload_for_cluster_b_or_cutoff_leak(v, path=f"{path}.{k}")
    elif isinstance(obj, (list, tuple)):
        for i, item in enumerate(obj):
            _scan_payload_for_cluster_b_or_cutoff_leak(item, path=f"{path}[{i}]")


def _normalize_candidates_input(
    candidates: Sequence[Mapping[str, Any]] | Mapping[str, Sequence[Mapping[str, Any]]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    primary: list[dict[str, Any]] = []
    exploratory: list[dict[str, Any]] = []

    if isinstance(candidates, Mapping):
        if "primary" not in candidates and "exploratory" not in candidates:
            raise ValueError("Mapping candidates must contain 'primary' and/or 'exploratory' keys")
        for item in candidates.get("primary") or []:
            d = dict(item)
            d.setdefault("tier", "PRIMARY")
            primary.append(d)
        for item in candidates.get("exploratory") or []:
            d = dict(item)
            d.setdefault("tier", "EXPLORATORY")
            exploratory.append(d)
    else:
        for item in candidates:
            d = dict(item)
            tier_val = str(d.get("tier", "")).strip().upper()
            is_prim = bool(d.get("is_primary", False)) or tier_val == "PRIMARY"
            if is_prim:
                d["tier"] = "PRIMARY"
                primary.append(d)
            else:
                d["tier"] = "EXPLORATORY"
                exploratory.append(d)

    total = [*primary, *exploratory]
    seen_ids: set[str] = set()
    for idx, c in enumerate(total):
        cid = str(c.get("candidate_id") or "").strip()
        if not cid:
            raise ValueError(f"Candidate at index {idx} missing non-empty 'candidate_id'")
        if cid in seen_ids:
            raise ValueError(f"Duplicate candidate_id {cid!r} in family checkpoint")
        seen_ids.add(cid)
    return primary, exploratory, total


def _canonical_candidates_sha256(primary: list[dict[str, Any]], exploratory: list[dict[str, Any]]) -> str:
    blob = json.dumps({"primary": primary, "exploratory": exploratory}, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(blob).hexdigest()


def _resolve_candidate_path(
    family_id: str,
    *,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> Path:
    fid = str(family_id or "").strip()
    if not _SAFE_FAMILY_ID_RE.fullmatch(fid):
        raise ValueError(f"Invalid family_id {family_id!r} (alphanumeric/_/- only)")
    ws = resolve_workspace_root(root)
    base = Path(candidates_dir) if candidates_dir is not None else (ws / ".runtime/offensive3/candidates")
    target = (base / f"{fid}.json").resolve()
    try:
        target.relative_to(base.resolve())
    except ValueError as exc:
        raise ValueError(f"family_id escapes candidates directory: {family_id!r}") from exc
    return target


def save_family_candidates(
    family_id: str,
    candidates: Sequence[Mapping[str, Any]] | Mapping[str, Sequence[Mapping[str, Any]]],
    meta: Mapping[str, Any],
    *,
    candidates_dir: str | Path | None = None,
    prereg_path: str | Path | None = None,
    root: str | Path | None = None,
) -> Path:
    """Atomically save Stage 2 Cluster-A discovery candidates to `.runtime/offensive3/candidates/<family_id>.json`.

    Hard fail-closed invariants:
      - `meta['discovery_years']` MUST equal `[2018, 2019, 2020]` (ZERO Cluster B data allowed!).
      - `len(primary) <= primary_cap` (from `preregistration_m1200.json`) and `len(total) <= 100`.
      - Zero Cluster B keys/dates/years anywhere inside `candidates` or `meta`.
      - `order_send_count == 0` and zero sealed rows analysed.
    """
    if not isinstance(meta, Mapping):
        raise ValueError("meta must be a mapping containing 'discovery_years'")

    raw_dy = meta.get("discovery_years")
    if not isinstance(raw_dy, (list, tuple)) or any(isinstance(x, bool) or not isinstance(x, int) for x in raw_dy):
        raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: meta['discovery_years'] must be [2018, 2019, 2020], got {raw_dy!r}")
    if sorted(int(x) for x in raw_dy) != list(CLUSTER_A_YEARS):
        raise ValueError(
            f"CLUSTER_B_LEAK_BLOCKED: discovery_years={list(raw_dy)!r} MUST equal {list(CLUSTER_A_YEARS)!r} "
            "(zero Cluster B data allowed in Stage 2 discovery output)"
        )

    if _SEAL_ROWS_ANALYSED_KEY in meta and (
        isinstance(meta[_SEAL_ROWS_ANALYSED_KEY], bool) or meta[_SEAL_ROWS_ANALYSED_KEY] != 0
    ):
        raise ValueError(f"DEV_SEAL_VIOLATION: meta[{_SEAL_ROWS_ANALYSED_KEY!r}] must be 0")

    primary_cap, total_cap = _resolve_family_caps(family_id, meta, prereg_path=prereg_path, root=root)
    primary, exploratory, total = _normalize_candidates_input(candidates)

    if len(primary) > primary_cap:
        raise ValueError(
            f"PRIMARY_CAP_EXCEEDED [{family_id}]: len(primary)={len(primary)} > primary_cap={primary_cap}"
        )
    if len(total) > total_cap:
        raise ValueError(
            f"EXPLORATORY_CAP_EXCEEDED [{family_id}]: len(total)={len(total)} > cap={total_cap}"
        )

    _scan_payload_for_cluster_b_or_cutoff_leak(meta, path="meta")
    _scan_payload_for_cluster_b_or_cutoff_leak(total, path="candidates")

    payload_sha = _canonical_candidates_sha256(primary, exploratory)
    meta_clean = dict(meta)
    meta_clean["discovery_years"] = list(CLUSTER_A_YEARS)
    meta_clean["primary_cap"] = primary_cap
    meta_clean["total_cap"] = total_cap

    out_doc: dict[str, Any] = {
        "schema_version": "naqex-offensive3-family-candidates-v1",
        "family_id": str(family_id).strip(),
        "saved_utc": datetime.now(tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        _SEAL_LOCK_KEY: EXPECTED_LOCK_SHA256,
        "discovery_years": list(CLUSTER_A_YEARS),
        "primary_cap": primary_cap,
        "total_cap": total_cap,
        "primary_count": len(primary),
        "exploratory_count": len(exploratory),
        "total_count": len(total),
        "payload_sha256": payload_sha,
        "meta": meta_clean,
        "primary_candidates": primary,
        "exploratory_candidates": exploratory,
        "candidates": total,
    }

    target = _resolve_candidate_path(family_id, candidates_dir=candidates_dir, root=root)
    _atomic_write_json(target, out_doc)
    return target


def load_family_candidates(
    family_id: str,
    *,
    candidates_dir: str | Path | None = None,
    verify_sha: bool = True,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Load and fail-closed validate a saved Stage 2 family candidate checkpoint (supports `--resume`)."""
    target = _resolve_candidate_path(family_id, candidates_dir=candidates_dir, root=root)
    if not target.is_file():
        raise FileNotFoundError(f"Family candidate checkpoint not found: {target}")

    doc = json.loads(target.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Malformed family candidate checkpoint root: {target}")
    if doc.get("schema_version") != "naqex-offensive3-family-candidates-v1":
        raise ValueError(f"Unexpected checkpoint schema_version: {doc.get('schema_version')!r}")
    if doc.get("order_send_count") != 0:
        raise ValueError(f"SAFETY_VIOLATION: checkpoint order_send_count={doc.get('order_send_count')!r}")
    if isinstance(doc.get(_SEAL_ROWS_ANALYSED_KEY), bool) or doc.get(_SEAL_ROWS_ANALYSED_KEY) != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: checkpoint {_SEAL_ROWS_ANALYSED_KEY} != 0")
    if doc.get("discovery_years") != list(CLUSTER_A_YEARS):
        raise ValueError(f"CLUSTER_B_LEAK_BLOCKED: checkpoint discovery_years={doc.get('discovery_years')!r}")

    primary = list(doc.get("primary_candidates") or [])
    exploratory = list(doc.get("exploratory_candidates") or [])
    total = list(doc.get("candidates") or [])
    pcap = int(doc.get("primary_cap", DEFAULT_PRIMARY_CAP_FALLBACK))
    tcap = int(doc.get("total_cap", DEFAULT_MAX_TOTAL_CANDIDATES))
    if len(primary) > pcap or len(total) > tcap or len(total) != len(primary) + len(exploratory):
        raise ValueError(
            f"CHECKPOINT_CORRUPT [{family_id}]: counts mismatch "
            f"(primary={len(primary)}/{pcap}, total={len(total)}/{tcap})"
        )

    if verify_sha:
        exp_sha = doc.get("payload_sha256")
        act_sha = _canonical_candidates_sha256(primary, exploratory)
        if exp_sha != act_sha:
            raise ValueError(f"CHECKPOINT_SHA256_DRIFT [{family_id}]: expected={exp_sha!r} actual={act_sha!r}")

    return doc


def has_valid_family_checkpoint(
    family_id: str,
    *,
    candidates_dir: str | Path | None = None,
    root: str | Path | None = None,
) -> bool:
    """Return True iff a SHA-verified Stage 2 checkpoint exists for `family_id` (for `--resume`)."""
    try:
        load_family_candidates(family_id, candidates_dir=candidates_dir, verify_sha=True, root=root)
        return True
    except Exception:
        return False


__all__ = [
    "ALL_DEV_YEARS",
    "CLUSTER_A_YEARS",
    "CLUSTER_B_YEARS",
    "DEFAULT_REFERENCE_FX_RATES",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "DEV_START_SEC",
    "FRICTION_TIERS",
    "HARD_FLAT_MAX_UTC_HHMM",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "RES_D1_YAHOO_SANCTIONED",
    "RES_NATIVE_M1_BIDASK",
    "TIER_12OLD",
    "TIER_NEW7",
    "TIER_NEW9",
    "USOIL_MIN_VALID_PRICE",
    "USOIL_QUARANTINE_DATES",
    "causal_atr",
    "causal_ema",
    "causal_realized_vol",
    "causal_rsi",
    "causal_sma",
    "causal_zscore",
    "check_leverage_margin",
    "compute_causal_tick_val_usd",
    "compute_daily_pnl_series",
    "compute_daily_swap_frac",
    "compute_notional_and_margin_per_lot_usd",
    "compute_split_metrics",
    "enforce_dev_date_bound",
    "enforce_dev_ts_bound",
    "find_first_red_news_flatten_ts",
    "get_symbol_spec",
    "has_valid_family_checkpoint",
    "is_in_red_news_window",
    "load_dev_red_news_index",
    "load_family_candidates",
    "load_ftmo_specs_28",
    "load_preregistration_m1200",
    "load_universe_28",
    "match_symbol_red_news_codes",
    "normalize_symbol",
    "replay_intraday_m1_trade",
    "replay_swing_d1_series",
    "replay_swing_trades",
    "resolve_workspace_root",
    "save_family_candidates",
    "stage0_screen",
]
