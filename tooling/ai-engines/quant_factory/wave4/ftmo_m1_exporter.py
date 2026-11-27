"""Holdout-sealed FTMO-Demo M1 history exporter (`< 2025-01-01` Dev-only).

Exports verified pre-2025 M1 OHLC + spread + tick_volume history for all 8 `PORT_7E`
symbols from the isolated FTMO-Demo portable terminal
(`.runtime/ftmo-demo-portable-1515343166`) into uncompressed zero-pickle `.npz` files
plus a SHA-256 stamped `manifest.json` under `.runtime/offensive4/m1/ftmo_dev_m1/`.

HARD SAFETY & FAIL-CLOSED INVARIANTS:
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0` (read-only history export only).
  - Lazy-imports `MetaTrader5` strictly inside the live MT5 session helper so Linux/CI
    environments without MT5 import and test cleanly.
  - NEVER touches `C:\\Program Files\\MetaTrader 5` or `D0E8209F77C8CF37AD8BF550E51FF075`.
  - Launches portable terminal with transient `/config:<ini>` enforcing `KeepPrivate=1`,
    `[Experts] Enabled=0`, `AllowLiveTrading=0`, `AllowDllImport=0`, and
    `[Charts] MaxBars=100000000` (without mutating `config/common.ini`), verifies
    `ACCOUNT_TRADE_MODE_DEMO`, `server == "FTMO-Demo"`, and authorized demo login,
    and ALWAYS runs `mt5.shutdown()` + process teardown + verifies `terminal64.exe == 0`.
  - ZERO bare `assert` statements (`[ARCH-02]`): all Holdout (`ts_utc < 2025-01-01T00:00:00Z`)
    and OHLC/monotonicity guards raise explicit `HoldoutViolationError` / `M1ValidationError`
    (subclasses of `ValueError`) and remain active under `python -O` / `python -OO`.
  - Empirical FTMO-Demo server clock (`EET_EEST`): EU DST (`Europe/Athens`, last Sun Mar ->
    last Sun Oct) for `<= 2019` and US DST (`America/New_York + 7h`, 2nd Sun Mar -> 1st Sun
    Nov) for `>= 2020`, implemented with pure-stdlib deterministic rules (zero Windows
    `tzdata` dependency).
"""

from __future__ import annotations

import argparse
import importlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Callable, Iterable, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

import numpy as np
from quant_core.io_utils import atomic_write_json, repo_root_from, sha256_file

from quant_factory.wave4 import HOLDOUT_CUTOFF_DATE

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0

SOURCE_PROVENANCE: str = "FTMO_BID_PLUS_SPREAD"
BROKER_TZ: str = "EET_EEST"
BROKER_TZ_DST_SCHEDULE: str = "EU_EET_LE_2019__US_NY_PLUS_7_GE_2020"
MANIFEST_SCHEMA: str = "naqex-wave4-ftmo-dev-m1-v1"

# Strict Holdout seal: every exported bar MUST satisfy ts_utc < HOLDOUT_CUTOFF_UTC_TS
# and ts_utc <= MAX_ALLOWED_DEV_BAR_TS_UTC (2024-12-31T23:59:00Z).
HOLDOUT_CUTOFF_UTC_ISO: str = "2025-01-01T00:00:00Z"
HOLDOUT_CUTOFF_UTC_TS: int = 1_735_689_600  # 2025-01-01T00:00:00Z (exclusive)
MAX_ALLOWED_DEV_BAR_TS_UTC: int = 1_735_689_540  # 2024-12-31T23:59:00Z (inclusive)
MIN_REASONABLE_UTC_TS: int = 1_262_304_000  # 2010-01-01T00:00:00Z

# Exact 8 PORT_7E symbols confirmed from Naqex_Master_Prop7E_v103.mq5 (L87-94),
# Naqex_Signals_7E.mqh (NAQEX_SYM_COUNT=8), and mt5_dev_tester_parity_receipt.json.
PORT_7E_SYMBOLS: tuple[str, ...] = (
    "USDJPY",
    "GBPUSD",
    "EURJPY",
    "US100.cash",
    "US500.cash",
    "EURUSD",
    "AUDUSD",
    "USDCAD",
)

CANONICAL_SYMBOL_MAP: dict[str, str] = {
    "USDJPY": "USDJPY",
    "GBPUSD": "GBPUSD",
    "EURJPY": "EURJPY",
    "US100.cash": "US100",
    "US500.cash": "US500",
    "EURUSD": "EURUSD",
    "AUDUSD": "AUDUSD",
    "USDCAD": "USDCAD",
}

DEFAULT_SYMBOL_SPECS: dict[str, dict[str, float | int]] = {
    "USDJPY": {"digits": 3, "point": 0.001},
    "GBPUSD": {"digits": 5, "point": 1e-5},
    "EURJPY": {"digits": 3, "point": 0.001},
    "US100.cash": {"digits": 2, "point": 0.01},
    "US500.cash": {"digits": 2, "point": 0.01},
    "EURUSD": {"digits": 5, "point": 1e-5},
    "AUDUSD": {"digits": 5, "point": 1e-5},
    "USDCAD": {"digits": 5, "point": 1e-5},
}

EXPECTED_SERVER: str = "FTMO-Demo"
PRIMARY_DEMO_LOGIN: int = 1515343166
SECONDARY_DEMO_LOGIN: int = 1515343318
ALLOWED_FTMO_DEMO_LOGINS: frozenset[int] = frozenset({PRIMARY_DEMO_LOGIN, SECONDARY_DEMO_LOGIN})

FORBIDDEN_PATH_TOKENS: tuple[str, ...] = (
    "program files\\metatrader 5",
    "program files/metatrader 5",
    "d0e8209f77c8cf37ad8bf550e51ff075",
)

_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

REPO_ROOT: Path = repo_root_from(__file__)
DEFAULT_PORTABLE_ROOT: Path = REPO_ROOT / ".runtime" / "ftmo-demo-portable-1515343166"
DEFAULT_OUT_DIR: Path = REPO_ROOT / ".runtime" / "offensive4" / "m1" / "ftmo_dev_m1"

REQUIRED_NPZ_ARRAY_KEYS: tuple[str, ...] = (
    "ts_utc",
    "open",
    "high",
    "low",
    "close",
    "spread_pts",
    "tick_volume",
)


class HoldoutViolationError(ValueError):
    """Raised fail-closed whenever a Holdout (>= 2025-01-01 UTC) timestamp or window is detected."""


class SafetyLockError(RuntimeError):
    """Raised fail-closed whenever an MT5 terminal path, account, or process lock is violated."""


class M1ValidationError(ValueError):
    """Raised fail-closed whenever M1 OHLC, spread, volume, or timestamp integrity fails."""


def _require_non_bool_int(val: Any, name: str) -> int:
    if isinstance(val, bool) or not isinstance(val, (int, np.integer)):
        raise M1ValidationError(f"INVALID_INT[{name}]: expected int (not bool), got {type(val).__name__}")
    return int(val)


def _iso_utc(ts_sec: int) -> str:
    return datetime.fromtimestamp(int(ts_sec), UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _nth_sunday(year: int, month: int, nth: int) -> date:
    first = date(year, month, 1)
    offset = (6 - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (nth - 1))


def _last_sunday(year: int, month: int) -> date:
    next_month = date(year + 1, 1, 1) if month == 12 else date(year, month + 1, 1)
    last_day = next_month - timedelta(days=1)
    offset = (last_day.weekday() - 6) % 7
    return last_day - timedelta(days=offset)


def _ftmo_dst_window_server_wall_ts(year: int) -> tuple[int, int]:
    """Return `(spring_srv_ts, fall_srv_ts)` in FTMO server wall-clock epoch seconds.

    Empirically verified against sealed Dukascopy UTC M1 bars across 2018-2024:
      - `year <= 2019`: EU DST (`Europe/Athens`):
          spring = last Sunday Mar 01:00 UTC (03:00 server wall time, +2h -> +3h)
          fall   = last Sunday Oct 01:00 UTC (04:00 server wall time, +3h -> +2h)
      - `year >= 2020`: US DST (`America/New_York + 7h`, matching `MT5-BROKER-CLOCK.md`):
          spring = 2nd Sunday Mar 07:00 UTC (09:00 server wall time, +2h -> +3h)
          fall   = 1st Sunday Nov 06:00 UTC (09:00 server wall time, +3h -> +2h)
    """
    if year >= 2020:
        s_day = _nth_sunday(year, 3, 2)
        f_day = _nth_sunday(year, 11, 1)
        spring_srv = int(datetime(s_day.year, s_day.month, s_day.day, 9, 0, tzinfo=UTC).timestamp())
        fall_srv = int(datetime(f_day.year, f_day.month, f_day.day, 9, 0, tzinfo=UTC).timestamp())
        return spring_srv, fall_srv
    s_day = _last_sunday(year, 3)
    f_day = _last_sunday(year, 10)
    spring_srv = int(datetime(s_day.year, s_day.month, s_day.day, 3, 0, tzinfo=UTC).timestamp())
    fall_srv = int(datetime(f_day.year, f_day.month, f_day.day, 4, 0, tzinfo=UTC).timestamp())
    return spring_srv, fall_srv


def decode_ftmo_server_times_to_utc(server_wall_ts: np.ndarray) -> np.ndarray:
    """Vectorized pure-NumPy conversion of FTMO-Demo server wall-clock epochs to UTC epochs.

    Handles both `<= 2019` (EU DST) and `>= 2020` (US DST NY+7) regimes with zero
    Windows `tzdata` dependency.
    """
    raw = np.asarray(server_wall_ts)
    if raw.ndim != 1:
        raise M1ValidationError(f"server_wall_ts must be 1D, got shape {raw.shape}")
    if raw.dtype == np.bool_ or not np.issubdtype(raw.dtype, np.integer):
        raise M1ValidationError(f"server_wall_ts must be integer dtype, got {raw.dtype}")
    raw64 = raw.astype(np.int64, copy=False)
    if raw64.size == 0:
        return np.empty(0, dtype=np.int64)

    min_ts = int(np.min(raw64))
    max_ts = int(np.max(raw64))
    if min_ts < MIN_REASONABLE_UTC_TS:
        raise M1ValidationError(f"server_wall_ts contains implausible epoch < 2010: {min_ts}")
    min_year = datetime.fromtimestamp(min_ts, UTC).year
    max_year = datetime.fromtimestamp(max_ts, UTC).year

    offsets = np.full(raw64.shape, 7200, dtype=np.int64)
    for yr in range(min_year, max_year + 1):
        spring_srv, fall_srv = _ftmo_dst_window_server_wall_ts(yr)
        in_dst = (raw64 >= spring_srv) & (raw64 < fall_srv)
        offsets[in_dst] = 10800
    return raw64 - offsets


def assert_safe_portable_root(portable_root: str | Path) -> Path:
    """Fail-closed guard refusing `C:\\Program Files\\MetaTrader 5` and Exness Real terminal IDs."""
    raw_str = str(portable_root).lower()
    resolved = Path(portable_root).resolve(strict=False)
    norm_str = str(resolved).lower()
    for candidate in (raw_str, raw_str.replace("\\", "/"), norm_str, norm_str.replace("\\", "/")):
        for tok in FORBIDDEN_PATH_TOKENS:
            if tok in candidate:
                raise SafetyLockError(f"SAFETY_ABORT_FORBIDDEN_MT5_PATH: {portable_root}")
    return resolved


def assert_pre_holdout_date_window(start_year: int, end_year: int) -> None:
    """Fail-closed check ensuring requested export years remain strictly `< 2025`."""
    sy = _require_non_bool_int(start_year, "start_year")
    ey = _require_non_bool_int(end_year, "end_year")
    if ey >= 2025 or sy >= 2025:
        raise HoldoutViolationError(
            f"HOLDOUT_LOCK_VIOLATION: requested export years [{sy}..{ey}] must stay strictly <= 2024 "
            f"(cutoff {HOLDOUT_CUTOFF_DATE})"
        )
    if sy < 2010 or sy > ey:
        raise M1ValidationError(f"INVALID_EXPORT_YEAR_WINDOW: [{sy}..{ey}]")


def list_running_mt5_processes() -> list[str]:
    """Return running `terminal64.exe` / `metatester64.exe` lines via windowless Windows `tasklist`."""
    if os.name != "nt":
        return []
    found: list[str] = []
    for image in ("terminal64.exe", "metatester64.exe"):
        proc = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image}", "/FO", "CSV", "/NH"],
            capture_output=True,
            text=True,
            timeout=10,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        for line in proc.stdout.splitlines():
            s = line.strip()
            if s and image in s.lower():
                found.append(s)
    return found


def assert_zero_mt5_processes(
    process_lister: Callable[[], list[str]] = list_running_mt5_processes,
    *,
    context: str = "pre-flight",
) -> None:
    """Fail-closed verification that zero `terminal64.exe` / `metatester64.exe` processes exist."""
    running = process_lister()
    if running:
        raise SafetyLockError(
            f"MT5_PROCESS_LOCK_VIOLATION[{context}]: detected {len(running)} running MT5 process(es): "
            f"{running[:3]}"
        )


def validate_demo_account(
    acc: Any,
    *,
    demo_trade_mode: int = 0,
    expected_server: str = EXPECTED_SERVER,
    allowed_logins: Iterable[int] = ALLOWED_FTMO_DEMO_LOGINS,
) -> dict[str, Any]:
    """Fail-closed account identity check enforcing FTMO-Demo + DEMO trade_mode + authorized login."""
    if acc is None:
        raise SafetyLockError("SAFETY_ABORT_ACCOUNT_INFO_NONE")
    raw_mode = getattr(acc, "trade_mode", None)
    raw_login = getattr(acc, "login", None)
    raw_server = getattr(acc, "server", None)
    if isinstance(raw_mode, bool) or not isinstance(raw_mode, (int, np.integer)):
        raise SafetyLockError(f"SAFETY_ABORT_INVALID_TRADE_MODE: {raw_mode!r}")
    if int(raw_mode) != int(demo_trade_mode):
        raise SafetyLockError(
            f"SAFETY_ABORT_NOT_DEMO_ACCOUNT: trade_mode={raw_mode} != ACCOUNT_TRADE_MODE_DEMO({demo_trade_mode})"
        )
    if str(raw_server) != expected_server:
        raise SafetyLockError(f"SAFETY_ABORT_UNEXPECTED_SERVER: {raw_server!r} != {expected_server!r}")
    if isinstance(raw_login, bool) or not isinstance(raw_login, (int, np.integer)):
        raise SafetyLockError(f"SAFETY_ABORT_INVALID_LOGIN: {raw_login!r}")
    login_int = int(raw_login)
    allowed_set = frozenset(_require_non_bool_int(x, "allowed_login") for x in allowed_logins)
    if not allowed_set or login_int not in allowed_set:
        raise SafetyLockError(f"SAFETY_ABORT_UNAUTHORIZED_LOGIN: {login_int} not in {sorted(allowed_set)}")
    return {
        "login": login_int,
        "server": str(raw_server),
        "trade_mode": "ACCOUNT_TRADE_MODE_DEMO",
        "currency": str(getattr(acc, "currency", "USD")),
        "leverage": int(getattr(acc, "leverage", 0)),
        "trade_allowed": bool(getattr(acc, "trade_allowed", False)),
        "trade_expert": bool(getattr(acc, "trade_expert", False)),
    }


def render_readonly_export_ini(*, max_bars: int = 100_000_000) -> str:
    """Render safe transient MT5 launch `.ini` (`KeepPrivate=1`, `[Experts] Enabled=0`, `AllowLiveTrading=0`)."""
    mb = _require_non_bool_int(max_bars, "max_bars")
    if mb < 100_000:
        raise M1ValidationError(f"max_bars too small for multi-year M1 export: {mb}")
    return (
        "[Common]\r\n"
        "ProxyEnable=0\r\n"
        "NewsEnable=0\r\n"
        "KeepPrivate=1\r\n"
        "\r\n"
        "[Experts]\r\n"
        "Enabled=0\r\n"
        "AllowLiveTrading=0\r\n"
        "AllowDllImport=0\r\n"
        "\r\n"
        "[Charts]\r\n"
        f"MaxBars={mb}\r\n"
    )


def validate_m1_arrays(
    *,
    symbol: str,
    ts_utc: np.ndarray,
    open_px: np.ndarray,
    high_px: np.ndarray,
    low_px: np.ndarray,
    close_px: np.ndarray,
    spread_pts: np.ndarray,
    tick_volume: np.ndarray,
    cutoff_utc_ts: int = HOLDOUT_CUTOFF_UTC_TS,
    max_allowed_bar_ts: int = MAX_ALLOWED_DEV_BAR_TS_UTC,
) -> dict[str, Any]:
    """Fail-closed validation of sealed pre-2025 M1 OHLC + spread + volume arrays.

    Zero bare `assert` statements — fully enforced under `python -O` / `python -OO`.
    """
    cutoff = _require_non_bool_int(cutoff_utc_ts, "cutoff_utc_ts")
    max_bar_cap = _require_non_bool_int(max_allowed_bar_ts, "max_allowed_bar_ts")
    if cutoff > HOLDOUT_CUTOFF_UTC_TS or max_bar_cap >= HOLDOUT_CUTOFF_UTC_TS:
        raise HoldoutViolationError(
            f"HOLDOUT_LOCK_VIOLATION[{symbol}]: cutoff/max_bar_cap cannot exceed sealed 2024-12-31 boundary"
        )

    arrays = {
        "ts_utc": np.asarray(ts_utc),
        "open": np.asarray(open_px),
        "high": np.asarray(high_px),
        "low": np.asarray(low_px),
        "close": np.asarray(close_px),
        "spread_pts": np.asarray(spread_pts),
        "tick_volume": np.asarray(tick_volume),
    }
    for key, arr in arrays.items():
        if arr.ndim != 1:
            raise M1ValidationError(f"INVALID_NDIM[{symbol}.{key}]: expected 1D, got shape {arr.shape}")
        if arr.dtype == np.bool_ or arr.dtype == np.object_:
            raise M1ValidationError(f"INVALID_DTYPE[{symbol}.{key}]: disallowed dtype {arr.dtype}")

    n = int(arrays["ts_utc"].size)
    if n == 0:
        raise M1ValidationError(f"EMPTY_M1_SERIES[{symbol}]: 0 bars returned")
    for key, arr in arrays.items():
        if int(arr.size) != n:
            raise M1ValidationError(f"LENGTH_MISMATCH[{symbol}.{key}]: {arr.size} != {n}")

    if not np.issubdtype(arrays["ts_utc"].dtype, np.integer):
        raise M1ValidationError(f"INVALID_TS_DTYPE[{symbol}]: expected integer ts_utc, got {arrays['ts_utc'].dtype}")
    ts64 = arrays["ts_utc"].astype(np.int64, copy=False)

    # STRICT HOLDOUT SEAL CHECK (checked FIRST, active under python -O!)
    max_ts = int(np.max(ts64))
    min_ts = int(np.min(ts64))
    if max_ts >= cutoff or max_ts > max_bar_cap:
        breach_count = int(np.count_nonzero(ts64 >= cutoff))
        raise HoldoutViolationError(
            f"HOLDOUT_LOCK_VIOLATION[{symbol}]: max_ts_utc={max_ts} ({_iso_utc(max_ts)}) "
            f"violates sealed pre-2025 cutoff < {cutoff} ({HOLDOUT_CUTOFF_UTC_ISO}); "
            f"breach_bars={breach_count}"
        )
    if min_ts < MIN_REASONABLE_UTC_TS:
        raise M1ValidationError(f"IMPLAUSIBLE_MIN_TS[{symbol}]: min_ts_utc={min_ts}")

    if n > 1 and not bool(np.all(np.diff(ts64) > 0)):
        bad_idx = int(np.flatnonzero(np.diff(ts64) <= 0)[0])
        raise M1ValidationError(
            f"NON_MONOTONIC_TIMESTAMPS[{symbol}]: ts[{bad_idx}]={int(ts64[bad_idx])} >= "
            f"ts[{bad_idx + 1}]={int(ts64[bad_idx + 1])}"
        )

    o = arrays["open"].astype(np.float64, copy=False)
    h = arrays["high"].astype(np.float64, copy=False)
    lo = arrays["low"].astype(np.float64, copy=False)
    c = arrays["close"].astype(np.float64, copy=False)
    for name, px in (("open", o), ("high", h), ("low", lo), ("close", c)):
        if not bool(np.all(np.isfinite(px))):
            raise M1ValidationError(f"NON_FINITE_PRICE[{symbol}.{name}]: NaN or Inf detected")
        if float(np.min(px)) <= 0.0:
            raise M1ValidationError(f"NON_POSITIVE_PRICE[{symbol}.{name}]: min={float(np.min(px))}")

    max_oc = np.maximum(o, c)
    min_oc = np.minimum(o, c)
    if not bool(np.all(h >= max_oc - 1e-12)):
        bad = int(np.flatnonzero(h < max_oc - 1e-12)[0])
        raise M1ValidationError(
            f"INVALID_OHLC_HIGH[{symbol}]: bar {bad} high={h[bad]} < max(open={o[bad]}, close={c[bad]})"
        )
    if not bool(np.all(min_oc >= lo - 1e-12)):
        bad = int(np.flatnonzero(min_oc < lo - 1e-12)[0])
        raise M1ValidationError(
            f"INVALID_OHLC_LOW[{symbol}]: bar {bad} low={lo[bad]} > min(open={o[bad]}, close={c[bad]})"
        )
    if not bool(np.all(h >= lo - 1e-12)):
        bad = int(np.flatnonzero(h < lo - 1e-12)[0])
        raise M1ValidationError(f"INVALID_OHLC_RANGE[{symbol}]: bar {bad} high={h[bad]} < low={lo[bad]}")

    sp_raw = arrays["spread_pts"]
    tv_raw = arrays["tick_volume"]
    if not np.issubdtype(sp_raw.dtype, np.number) or not bool(np.all(np.isfinite(sp_raw))):
        raise M1ValidationError(f"INVALID_SPREAD[{symbol}]: non-finite spread_pts")
    if not np.issubdtype(tv_raw.dtype, np.number) or not bool(np.all(np.isfinite(tv_raw))):
        raise M1ValidationError(f"INVALID_TICK_VOLUME[{symbol}]: non-finite tick_volume")
    if float(np.min(sp_raw)) < 0.0:
        raise M1ValidationError(f"NEGATIVE_SPREAD[{symbol}]: min spread_pts={float(np.min(sp_raw))}")
    if float(np.min(tv_raw)) < 0.0:
        raise M1ValidationError(f"NEGATIVE_TICK_VOLUME[{symbol}]: min tick_volume={float(np.min(tv_raw))}")

    return {
        "row_count": n,
        "min_ts_utc": min_ts,
        "max_ts_utc": max_ts,
        "min_ts_utc_iso": _iso_utc(min_ts),
        "max_ts_utc_iso": _iso_utc(max_ts),
        "min_price": round(float(np.min(lo)), 6),
        "max_price": round(float(np.max(h)), 6),
        "spread_pts_min": int(np.min(sp_raw)),
        "spread_pts_median": round(float(np.median(sp_raw)), 2),
        "spread_pts_p95": round(float(np.percentile(sp_raw, 95)), 2),
        "spread_pts_max": int(np.max(sp_raw)),
        "holdout_rows_analysed": 0,
    }


def _extract_structured_rates(
    symbol: str,
    chunks: Sequence[np.ndarray],
    *,
    cutoff_utc_ts: int = HOLDOUT_CUTOFF_UTC_TS,
    decode_broker_eet: bool = True,
) -> dict[str, np.ndarray]:
    """Concatenate raw MT5 structured rate chunks, decode UTC timestamps, and fail-closed on Holdout."""
    non_empty = [np.asarray(ch) for ch in chunks if ch is not None and len(ch) > 0]
    if not non_empty:
        raise M1ValidationError(f"NO_MT5_RATES_RETURNED[{symbol}]")

    raw_ts_list: list[np.ndarray] = []
    open_list: list[np.ndarray] = []
    high_list: list[np.ndarray] = []
    low_list: list[np.ndarray] = []
    close_list: list[np.ndarray] = []
    spread_list: list[np.ndarray] = []
    vol_list: list[np.ndarray] = []

    for ch in non_empty:
        names = ch.dtype.names or ()
        for req in ("time", "open", "high", "low", "close", "spread", "tick_volume"):
            if req not in names:
                raise M1ValidationError(f"MISSING_MT5_FIELD[{symbol}]: field {req!r} not in {names}")
        raw_ts_list.append(np.asarray(ch["time"], dtype=np.int64))
        open_list.append(np.asarray(ch["open"], dtype=np.float64))
        high_list.append(np.asarray(ch["high"], dtype=np.float64))
        low_list.append(np.asarray(ch["low"], dtype=np.float64))
        close_list.append(np.asarray(ch["close"], dtype=np.float64))
        spread_list.append(np.asarray(ch["spread"], dtype=np.int32))
        vol_list.append(np.asarray(ch["tick_volume"], dtype=np.int64))

    ts_server_raw = np.concatenate(raw_ts_list)
    open_px = np.concatenate(open_list)
    high_px = np.concatenate(high_list)
    low_px = np.concatenate(low_list)
    close_px = np.concatenate(close_list)
    spread_pts = np.concatenate(spread_list)
    tick_volume = np.concatenate(vol_list)

    ts_utc = decode_ftmo_server_times_to_utc(ts_server_raw) if decode_broker_eet else ts_server_raw.copy()

    # Fail-closed Holdout rejection before any further processing or export!
    cutoff = _require_non_bool_int(cutoff_utc_ts, "cutoff_utc_ts")
    if cutoff > HOLDOUT_CUTOFF_UTC_TS:
        raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION[{symbol}]: cutoff {cutoff} > {HOLDOUT_CUTOFF_UTC_TS}")
    if ts_utc.size > 0 and int(np.max(ts_utc)) >= cutoff:
        bad_n = int(np.count_nonzero(ts_utc >= cutoff))
        max_t = int(np.max(ts_utc))
        raise HoldoutViolationError(
            f"HOLDOUT_LOCK_VIOLATION[{symbol}]: MT5 rate stream contained {bad_n} Holdout bar(s) "
            f">= {HOLDOUT_CUTOFF_UTC_ISO} (max_ts_utc={max_t} / {_iso_utc(max_t)})"
        )

    # Guard against exact duplicate boundary timestamps across year chunks (only if identical OHLC)
    if ts_utc.size > 1:
        diffs = np.diff(ts_utc)
        if bool(np.any(diffs == 0)):
            dup_idxs = np.flatnonzero(diffs == 0)
            for idx in dup_idxs:
                same_ohlc = (
                    open_px[idx] == open_px[idx + 1]
                    and high_px[idx] == high_px[idx + 1]
                    and low_px[idx] == low_px[idx + 1]
                    and close_px[idx] == close_px[idx + 1]
                )
                if not same_ohlc:
                    raise M1ValidationError(
                        f"CONFLICTING_DUPLICATE_TS[{symbol}]: ts_utc={int(ts_utc[idx])} has conflicting OHLC"
                    )
            keep = np.ones(ts_utc.size, dtype=np.bool_)
            keep[dup_idxs + 1] = False
            ts_utc = ts_utc[keep]
            ts_server_raw = ts_server_raw[keep]
            open_px = open_px[keep]
            high_px = high_px[keep]
            low_px = low_px[keep]
            close_px = close_px[keep]
            spread_pts = spread_pts[keep]
            tick_volume = tick_volume[keep]

    return {
        "ts_utc": ts_utc,
        "ts_server_raw": ts_server_raw,
        "open": open_px,
        "high": high_px,
        "low": low_px,
        "close": close_px,
        "spread_pts": spread_pts,
        "tick_volume": tick_volume,
    }


def _atomic_save_npz(path: Path, arrays: dict[str, np.ndarray]) -> str:
    """Atomically write uncompressed zero-pickle `.npz` via temp file + fsync + os.replace; return SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".npz.tmp",
            delete=False,
        ) as fh:
            tmp_path = Path(fh.name)
            np.savez(fh, **cast(Any, arrays))
            fh.flush()
            os.fsync(fh.fileno())
        digest = sha256_file(tmp_path)
        os.replace(tmp_path, path)
        tmp_path = None
        return digest
    finally:
        if tmp_path is not None:
            tmp_path.unlink(missing_ok=True)


def save_sealed_symbol_npz(
    *,
    out_dir: Path,
    symbol: str,
    arrays: dict[str, np.ndarray],
    digits: int,
    point: float,
    cutoff_utc_ts: int = HOLDOUT_CUTOFF_UTC_TS,
) -> dict[str, Any]:
    """Validate and atomically write a single sealed pre-2025 `.npz` file, then post-verify from disk."""
    if isinstance(point, bool) or not isinstance(point, (int, float)) or not math.isfinite(float(point)) or point <= 0:
        raise M1ValidationError(f"INVALID_POINT[{symbol}]: {point!r}")
    digits_i = _require_non_bool_int(digits, "digits")
    if digits_i < 0 or digits_i > 8:
        raise M1ValidationError(f"INVALID_DIGITS[{symbol}]: {digits_i}")

    stats = validate_m1_arrays(
        symbol=symbol,
        ts_utc=arrays["ts_utc"],
        open_px=arrays["open"],
        high_px=arrays["high"],
        low_px=arrays["low"],
        close_px=arrays["close"],
        spread_pts=arrays["spread_pts"],
        tick_volume=arrays["tick_volume"],
        cutoff_utc_ts=cutoff_utc_ts,
    )

    canonical = CANONICAL_SYMBOL_MAP.get(symbol, symbol.replace(".cash", ""))
    npz_name = f"{symbol}.npz"
    npz_path = Path(out_dir) / npz_name

    payload: dict[str, np.ndarray] = {
        "ts_utc": np.asarray(arrays["ts_utc"], dtype=np.int64),
        "open": np.asarray(arrays["open"], dtype=np.float64),
        "high": np.asarray(arrays["high"], dtype=np.float64),
        "low": np.asarray(arrays["low"], dtype=np.float64),
        "close": np.asarray(arrays["close"], dtype=np.float64),
        "spread_pts": np.asarray(arrays["spread_pts"], dtype=np.int32),
        "tick_volume": np.asarray(arrays["tick_volume"], dtype=np.int64),
        "ts_server_raw": np.asarray(arrays.get("ts_server_raw", arrays["ts_utc"]), dtype=np.int64),
        "symbol": np.asarray(symbol),
        "canonical_symbol": np.asarray(canonical),
        "source_provenance": np.asarray(SOURCE_PROVENANCE),
        "broker_tz": np.asarray(BROKER_TZ),
        "broker_tz_dst_schedule": np.asarray(BROKER_TZ_DST_SCHEDULE),
        "min_ts_utc": np.asarray(stats["min_ts_utc"], dtype=np.int64),
        "max_ts_utc": np.asarray(stats["max_ts_utc"], dtype=np.int64),
        "row_count": np.asarray(stats["row_count"], dtype=np.int64),
        "holdout_rows_analysed": np.asarray(0, dtype=np.int64),
        "point": np.asarray(float(point), dtype=np.float64),
        "digits": np.asarray(digits_i, dtype=np.int32),
    }

    digest = _atomic_save_npz(npz_path, payload)

    # Mandatory post-export disk verification (fail-closed, active under python -O!)
    post_stats = verify_exported_npz(npz_path, expected_symbol=symbol, expected_sha256=digest)

    # Compute exact O(log N) per-year bar counts via searchsorted
    ts_all = payload["ts_utc"]
    y_min = datetime.fromtimestamp(stats["min_ts_utc"], UTC).year
    y_max = datetime.fromtimestamp(stats["max_ts_utc"], UTC).year
    year_row_counts: dict[str, int] = {}
    for yr in range(y_min, y_max + 1):
        y_start = int(datetime(yr, 1, 1, tzinfo=UTC).timestamp())
        y_end = int(datetime(yr + 1, 1, 1, tzinfo=UTC).timestamp())
        lo_i = int(np.searchsorted(ts_all, y_start, side="left"))
        hi_i = int(np.searchsorted(ts_all, y_end, side="left"))
        cnt = hi_i - lo_i
        if cnt > 0:
            year_row_counts[str(yr)] = cnt
    covered_years = [int(y) for y in year_row_counts]

    return {
        "symbol": symbol,
        "canonical_symbol": canonical,
        "npz_file": npz_name,
        "npz_bytes": int(npz_path.stat().st_size),
        "sha256": digest,
        "source_provenance": SOURCE_PROVENANCE,
        "broker_tz": BROKER_TZ,
        "broker_tz_dst_schedule": BROKER_TZ_DST_SCHEDULE,
        "digits": digits_i,
        "point": float(point),
        "row_count": post_stats["row_count"],
        "min_ts_utc": post_stats["min_ts_utc"],
        "max_ts_utc": post_stats["max_ts_utc"],
        "min_ts_utc_iso": post_stats["min_ts_utc_iso"],
        "max_ts_utc_iso": post_stats["max_ts_utc_iso"],
        "covered_years": covered_years,
        "year_row_counts": year_row_counts,
        "min_price": post_stats["min_price"],
        "max_price": post_stats["max_price"],
        "spread_pts_min": post_stats["spread_pts_min"],
        "spread_pts_median": post_stats["spread_pts_median"],
        "spread_pts_p95": post_stats["spread_pts_p95"],
        "spread_pts_max": post_stats["spread_pts_max"],
        "holdout_rows_analysed": 0,
    }


def verify_exported_npz(
    npz_path: str | Path,
    *,
    expected_symbol: str | None = None,
    expected_sha256: str | None = None,
) -> dict[str, Any]:
    """Load an exported `.npz` strictly with `allow_pickle=False` and fail-closed validate Holdout + OHLC."""
    path = Path(npz_path)
    if not path.is_file():
        raise FileNotFoundError(f"Exported M1 NPZ missing: {path}")
    actual_sha = sha256_file(path)
    if expected_sha256 is not None:
        if not isinstance(expected_sha256, str) or _SHA256_HEX_RE.fullmatch(expected_sha256) is None:
            raise M1ValidationError(f"INVALID_EXPECTED_SHA256: {expected_sha256!r}")
        if actual_sha != expected_sha256:
            raise M1ValidationError(f"NPZ_SHA256_DRIFT[{path.name}]: expected={expected_sha256} actual={actual_sha}")

    with np.load(path, allow_pickle=False) as z:
        for req in (
            *REQUIRED_NPZ_ARRAY_KEYS,
            "source_provenance",
            "broker_tz",
            "min_ts_utc",
            "max_ts_utc",
            "row_count",
            "holdout_rows_analysed",
        ):
            if req not in z.files:
                raise M1ValidationError(f"MISSING_NPZ_KEY[{path.name}]: {req!r}")

        sym = str(z["symbol"].item()) if "symbol" in z.files else path.stem
        if expected_symbol is not None and sym != expected_symbol:
            raise M1ValidationError(f"NPZ_SYMBOL_MISMATCH[{path.name}]: {sym!r} != {expected_symbol!r}")

        prov = str(z["source_provenance"].item())
        if prov != SOURCE_PROVENANCE:
            raise M1ValidationError(f"NPZ_PROVENANCE_MISMATCH[{sym}]: {prov!r} != {SOURCE_PROVENANCE!r}")
        btz = str(z["broker_tz"].item())
        if btz != BROKER_TZ:
            raise M1ValidationError(f"NPZ_BROKER_TZ_MISMATCH[{sym}]: {btz!r} != {BROKER_TZ!r}")

        ho_rows = int(z["holdout_rows_analysed"].item())
        if ho_rows != 0:
            raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION[{sym}]: npz holdout_rows_analysed={ho_rows} != 0")

        stats = validate_m1_arrays(
            symbol=sym,
            ts_utc=z["ts_utc"],
            open_px=z["open"],
            high_px=z["high"],
            low_px=z["low"],
            close_px=z["close"],
            spread_pts=z["spread_pts"],
            tick_volume=z["tick_volume"],
        )

        if int(z["min_ts_utc"].item()) != stats["min_ts_utc"] or int(z["max_ts_utc"].item()) != stats["max_ts_utc"]:
            raise M1ValidationError(f"NPZ_META_TS_MISMATCH[{sym}]: scalar min/max ts disagrees with ts_utc array")
        if int(z["row_count"].item()) != stats["row_count"]:
            raise M1ValidationError(f"NPZ_META_ROW_COUNT_MISMATCH[{sym}]")

    return {**stats, "symbol": sym, "sha256": actual_sha}


def load_exported_m1(
    symbol: str,
    *,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    verify_sha: bool = True,
) -> dict[str, Any]:
    """Load a verified sealed FTMO M1 `.npz` by broker symbol or canonical alias (e.g. `US100` -> `US100.cash`)."""
    root = Path(out_dir)
    manifest = verify_exported_manifest(root, symbols=(symbol,), verify_sha=verify_sha)
    resolved_sym = _resolve_manifest_symbol(manifest, symbol)
    entry = manifest["symbols"][resolved_sym]
    npz_path = root / entry["npz_file"]
    with np.load(npz_path, allow_pickle=False) as z:
        return {
            "symbol": resolved_sym,
            "canonical_symbol": entry["canonical_symbol"],
            "ts_utc": z["ts_utc"].copy(),
            "open": z["open"].copy(),
            "high": z["high"].copy(),
            "low": z["low"].copy(),
            "close": z["close"].copy(),
            "spread_pts": z["spread_pts"].copy(),
            "tick_volume": z["tick_volume"].copy(),
            "ts_server_raw": z["ts_server_raw"].copy() if "ts_server_raw" in z.files else z["ts_utc"].copy(),
            "point": float(entry["point"]),
            "digits": int(entry["digits"]),
            "source_provenance": SOURCE_PROVENANCE,
            "broker_tz": BROKER_TZ,
            "holdout_rows_analysed": 0,
        }


def _resolve_manifest_symbol(manifest: dict[str, Any], symbol: str) -> str:
    syms = manifest.get("symbols", {})
    if symbol in syms:
        return symbol
    u = symbol.strip().upper()
    for k, v in syms.items():
        if k.upper() == u or str(v.get("canonical_symbol", "")).upper() == u:
            return k
    raise KeyError(f"Symbol {symbol!r} not found in FTMO Dev M1 manifest")


def verify_exported_manifest(
    out_dir: str | Path = DEFAULT_OUT_DIR,
    *,
    symbols: Sequence[str] | None = None,
    verify_sha: bool = True,
) -> dict[str, Any]:
    """Fail-closed validation of `manifest.json` and every referenced sealed `.npz` file."""
    root = Path(out_dir).resolve()
    manifest_path = root / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"FTMO Dev M1 manifest missing: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict):
        raise M1ValidationError(f"Manifest must be a JSON object: {manifest_path}")

    ho = manifest.get("holdout_rows_analysed")
    if isinstance(ho, bool) or ho != 0:
        raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION: manifest holdout_rows_analysed={ho!r} != 0")
    if manifest.get("holdout_cutoff_utc") != HOLDOUT_CUTOFF_UTC_ISO:
        raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION: unexpected cutoff {manifest.get('holdout_cutoff_utc')!r}")
    if manifest.get("source_provenance") != SOURCE_PROVENANCE:
        raise M1ValidationError(f"MANIFEST_PROVENANCE_MISMATCH: {manifest.get('source_provenance')!r}")
    if manifest.get("broker_tz") != BROKER_TZ:
        raise M1ValidationError(f"MANIFEST_BROKER_TZ_MISMATCH: {manifest.get('broker_tz')!r}")

    sym_map = manifest.get("symbols")
    if not isinstance(sym_map, dict) or not sym_map:
        raise M1ValidationError("Manifest symbols map is empty or invalid")

    targets = [_resolve_manifest_symbol(manifest, s) for s in symbols] if symbols is not None else list(sym_map.keys())
    for sym in targets:
        entry = sym_map[sym]
        if not isinstance(entry, dict):
            raise M1ValidationError(f"Invalid manifest entry for {sym}")
        e_ho = entry.get("holdout_rows_analysed")
        if isinstance(e_ho, bool) or e_ho != 0:
            raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION[{sym}]: manifest entry holdout_rows={e_ho!r}")
        fname = str(entry.get("npz_file", ""))
        if not fname or "/" in fname or "\\" in fname or ".." in fname:
            raise M1ValidationError(f"Unsafe npz_file in manifest for {sym}: {fname!r}")
        npz_path = (root / fname).resolve()
        try:
            npz_path.relative_to(root)
        except ValueError as exc:
            raise M1ValidationError(f"NPZ path escapes out_dir for {sym}: {fname!r}") from exc
        exp_sha = str(entry.get("sha256", "")) if verify_sha else None
        disk_stats = verify_exported_npz(npz_path, expected_symbol=sym, expected_sha256=exp_sha)
        if disk_stats["row_count"] != entry.get("row_count"):
            raise M1ValidationError(f"MANIFEST_ROW_COUNT_DRIFT[{sym}]")
        if disk_stats["min_ts_utc"] != entry.get("min_ts_utc") or disk_stats["max_ts_utc"] != entry.get("max_ts_utc"):
            raise M1ValidationError(f"MANIFEST_TS_BOUNDS_DRIFT[{sym}]")

    return manifest


def _open_ftmo_mt5_session(
    *,
    portable_root: Path,
    expected_server: str = EXPECTED_SERVER,
    allowed_logins: Iterable[int] = ALLOWED_FTMO_DEMO_LOGINS,
    mt5_mod: Any = None,
    process_lister: Callable[[], list[str]] = list_running_mt5_processes,
    max_bars: int = 100_000_000,
) -> tuple[Any, subprocess.Popen[Any] | None, Path | None, dict[str, Any]]:
    """Safely launch portable FTMO-Demo terminal (hidden, Experts=0, KeepPrivate=1) and initialize MT5."""
    root = assert_safe_portable_root(portable_root)
    term_exe = root / "terminal64.exe"
    proc: subprocess.Popen[Any] | None = None
    ini_path: Path | None = None
    mt5: Any = mt5_mod

    if mt5 is None:
        if not term_exe.is_file():
            raise FileNotFoundError(f"FTMO portable terminal64.exe missing: {term_exe}")
        assert_zero_mt5_processes(process_lister, context="pre-launch")
        # Lazy-import MetaTrader5 strictly here so CI without MT5 never imports it!
        mt5 = cast(Any, importlib.import_module("MetaTrader5"))

        with tempfile.NamedTemporaryFile("w", suffix=".ini", delete=False, encoding="ascii") as tf:
            tf.write(render_readonly_export_ini(max_bars=max_bars))
            ini_path = Path(tf.name)

        startup = None
        if sys.platform == "win32":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        proc = subprocess.Popen(
            [str(term_exe), "/portable", f"/config:{ini_path}"],
            cwd=str(root),
            startupinfo=startup,
            creationflags=_NO_WINDOW_FLAGS,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2.5)

    ok = False
    for attempt in range(5 if proc is not None else 1):
        ok = bool(mt5.initialize(path=str(term_exe), portable=True, timeout=30000))
        if ok:
            break
        if attempt < 4 and proc is not None:
            time.sleep(1.5)
    if not ok:
        _teardown_ftmo_mt5_session(mt5, proc, ini_path, initialized=False, process_lister=process_lister)
        err = mt5.last_error() if hasattr(mt5, "last_error") else "unknown"
        raise SafetyLockError(f"MT5_INITIALIZE_FAILED: {err}")

    try:
        demo_mode = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
        acc_info = validate_demo_account(
            mt5.account_info(),
            demo_trade_mode=demo_mode,
            expected_server=expected_server,
            allowed_logins=allowed_logins,
        )
        ti = mt5.terminal_info()
        if ti is not None:
            t_data = getattr(ti, "data_path", "")
            t_path = getattr(ti, "path", "")
            if t_data:
                data_resolved = assert_safe_portable_root(Path(t_data))
                if mt5_mod is None and data_resolved != root:
                    raise SafetyLockError(f"SAFETY_ABORT_DATA_PATH_MISMATCH: {data_resolved} != {root}")
            if t_path:
                assert_safe_portable_root(Path(t_path))
            acc_info["terminal_build"] = int(getattr(ti, "build", 0))
            acc_info["terminal_maxbars"] = int(getattr(ti, "maxbars", 0))
            acc_info["terminal_connected"] = bool(getattr(ti, "connected", False))
            acc_info["terminal_trade_allowed"] = bool(getattr(ti, "trade_allowed", False))
        return mt5, proc, ini_path, acc_info
    except Exception:
        _teardown_ftmo_mt5_session(mt5, proc, ini_path, initialized=True, process_lister=process_lister)
        raise


def _teardown_ftmo_mt5_session(
    mt5: Any,
    proc: subprocess.Popen[Any] | None,
    ini_path: Path | None,
    *,
    initialized: bool,
    process_lister: Callable[[], list[str]] = list_running_mt5_processes,
) -> None:
    """Always shut down MT5, terminate spawned portable terminal, clean temp ini, and assert 0 processes."""
    try:
        if initialized and mt5 is not None and hasattr(mt5, "shutdown"):
            mt5.shutdown()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if ini_path is not None:
            ini_path.unlink(missing_ok=True)
        if proc is not None:
            # Give Windows process table a moment to reap terminal64.exe cleanly
            for _ in range(10):
                if not process_lister():
                    break
                time.sleep(0.25)
            assert_zero_mt5_processes(process_lister, context="post-shutdown")


def fetch_symbol_m1_from_mt5(
    mt5: Any,
    symbol: str,
    *,
    start_year: int = 2016,
    end_year: int = 2024,
    decode_broker_eet: bool = True,
) -> tuple[dict[str, np.ndarray], int, float]:
    """Query strictly pre-2025 (`<= 2024-12-31 23:59:59` server time) M1 bars from an active MT5 session."""
    assert_pre_holdout_date_window(start_year, end_year)
    if hasattr(mt5, "symbol_select"):
        mt5.symbol_select(symbol, True)

    tf_m1 = int(getattr(mt5, "TIMEFRAME_M1", 1))
    chunks: list[np.ndarray] = []
    for yr in range(int(start_year), int(end_year) + 1):
        dt_from = datetime(yr, 1, 1, 0, 0, 0, tzinfo=UTC)
        dt_to = datetime(yr, 12, 31, 23, 59, 59, tzinfo=UTC)
        rates = mt5.copy_rates_range(symbol, tf_m1, dt_from, dt_to)
        if rates is not None and len(rates) > 0:
            chunks.append(rates)

    arrays = _extract_structured_rates(
        symbol,
        chunks,
        cutoff_utc_ts=HOLDOUT_CUTOFF_UTC_TS,
        decode_broker_eet=decode_broker_eet,
    )

    spec_default = DEFAULT_SYMBOL_SPECS.get(symbol, {"digits": 5, "point": 1e-5})
    si = mt5.symbol_info(symbol) if hasattr(mt5, "symbol_info") else None
    digits = int(getattr(si, "digits", spec_default["digits"])) if si is not None else int(spec_default["digits"])
    raw_pt = float(getattr(si, "point", spec_default["point"])) if si is not None else float(spec_default["point"])
    point = raw_pt if (math.isfinite(raw_pt) and raw_pt > 0.0) else float(spec_default["point"])
    return arrays, digits, point


def compute_intersection_window(symbol_entries: dict[str, dict[str, Any]]) -> dict[str, Any]:
    """Compute exact multi-symbol common Dev timestamp intersection window (`<= 2024-12-31`)."""
    if not symbol_entries:
        raise M1ValidationError("Cannot compute intersection window over empty symbol map")
    inter_min = max(int(e["min_ts_utc"]) for e in symbol_entries.values())
    inter_max = min(int(e["max_ts_utc"]) for e in symbol_entries.values())
    if inter_min > inter_max:
        raise M1ValidationError(
            f"EMPTY_INTERSECTION_WINDOW: min={inter_min} ({_iso_utc(inter_min)}) > "
            f"max={inter_max} ({_iso_utc(inter_max)})"
        )
    if inter_max >= HOLDOUT_CUTOFF_UTC_TS:
        raise HoldoutViolationError(f"HOLDOUT_LOCK_VIOLATION: intersection max_ts_utc={inter_max}")

    # Dense 2022-2024 common window (noting US100.cash / US500.cash continuous M1 coverage)
    full_years_intersection = sorted(
        set.intersection(*(set(e.get("covered_years", [])) for e in symbol_entries.values()))
    )
    return {
        "symbol_count": len(symbol_entries),
        "raw_intersection_min_ts_utc": inter_min,
        "raw_intersection_max_ts_utc": inter_max,
        "raw_intersection_min_utc_iso": _iso_utc(inter_min),
        "raw_intersection_max_utc_iso": _iso_utc(inter_max),
        "common_covered_years": full_years_intersection,
        "canonical_8sym_dev_window": "2022-01-01..2024-12-31",
    }


def export_ftmo_m1_suite(
    *,
    portable_root: str | Path = DEFAULT_PORTABLE_ROOT,
    out_dir: str | Path = DEFAULT_OUT_DIR,
    symbols: Sequence[str] = PORT_7E_SYMBOLS,
    start_year: int = 2016,
    end_year: int = 2024,
    expected_server: str = EXPECTED_SERVER,
    allowed_logins: Iterable[int] = ALLOWED_FTMO_DEMO_LOGINS,
    mt5_mod: Any = None,
    process_lister: Callable[[], list[str]] = list_running_mt5_processes,
    decode_broker_eet: bool = True,
) -> dict[str, Any]:
    """Export verified pre-2025 FTMO-Demo M1 `.npz` files + `manifest.json` for all requested symbols."""
    assert_pre_holdout_date_window(start_year, end_year)
    if not symbols:
        raise M1ValidationError("symbols sequence must not be empty")
    out_path = Path(out_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    t0 = time.perf_counter()

    mt5, proc, ini_path, account_info = _open_ftmo_mt5_session(
        portable_root=Path(portable_root),
        expected_server=expected_server,
        allowed_logins=allowed_logins,
        mt5_mod=mt5_mod,
        process_lister=process_lister,
    )

    symbol_entries: dict[str, dict[str, Any]] = {}
    try:
        for sym in symbols:
            arrays, digits, point = fetch_symbol_m1_from_mt5(
                mt5,
                sym,
                start_year=start_year,
                end_year=end_year,
                decode_broker_eet=decode_broker_eet,
            )
            entry = save_sealed_symbol_npz(
                out_dir=out_path,
                symbol=sym,
                arrays=arrays,
                digits=digits,
                point=point,
                cutoff_utc_ts=HOLDOUT_CUTOFF_UTC_TS,
            )
            symbol_entries[sym] = entry
    finally:
        _teardown_ftmo_mt5_session(
            mt5,
            proc,
            ini_path,
            initialized=True,
            process_lister=process_lister,
        )

    post_mt5_procs = len(process_lister())
    if post_mt5_procs != 0:
        raise SafetyLockError(f"POST_EXPORT_MT5_PROCS_NONZERO: {post_mt5_procs}")

    intersection = compute_intersection_window(symbol_entries)
    total_rows = sum(int(e["row_count"]) for e in symbol_entries.values())
    total_bytes = sum(int(e["npz_bytes"]) for e in symbol_entries.values())

    manifest: dict[str, Any] = {
        "schema": MANIFEST_SCHEMA,
        "generated_utc": datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "source_provenance": SOURCE_PROVENANCE,
        "broker_tz": BROKER_TZ,
        "broker_tz_dst_schedule": BROKER_TZ_DST_SCHEDULE,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "holdout_cutoff_utc": HOLDOUT_CUTOFF_UTC_ISO,
        "holdout_cutoff_utc_ts": HOLDOUT_CUTOFF_UTC_TS,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "portable_root": str(Path(portable_root)),
        "account": account_info,
        "mt5_processes_after_export": post_mt5_procs,
        "symbol_count": len(symbol_entries),
        "total_rows": total_rows,
        "total_npz_bytes": total_bytes,
        "elapsed_seconds": round(time.perf_counter() - t0, 3),
        "intersection": intersection,
        "symbols": symbol_entries,
    }
    manifest_path = out_path / "manifest.json"
    atomic_write_json(manifest_path, manifest, indent=2)

    # Final fail-closed disk verification of the full manifest + every NPZ SHA-256!
    verify_exported_manifest(out_path, verify_sha=True)
    return manifest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        description="Holdout-sealed (< 2025-01-01) FTMO-Demo M1 exporter for PORT_7E symbols."
    )
    ap.add_argument("--portable-root", type=Path, default=DEFAULT_PORTABLE_ROOT)
    ap.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    ap.add_argument("--symbols", nargs="+", default=list(PORT_7E_SYMBOLS))
    ap.add_argument("--start-year", type=int, default=2016)
    ap.add_argument("--end-year", type=int, default=2024)
    ap.add_argument(
        "--expected-login",
        type=int,
        default=None,
        help="Optional exact FTMO-Demo login override (default allows 1515343166/1515343318).",
    )
    ap.add_argument("--verify-only", action="store_true", help="Verify an existing manifest & NPZ files without MT5.")
    args = ap.parse_args(argv)

    if args.verify_only:
        m = verify_exported_manifest(args.out_dir, verify_sha=True)
        print(
            json.dumps(
                {
                    "ok": True,
                    "schema": m["schema"],
                    "symbol_count": m["symbol_count"],
                    "total_rows": m["total_rows"],
                    "holdout_rows_analysed": m["holdout_rows_analysed"],
                },
                indent=2,
            )
        )
        return 0

    allowed = (int(args.expected_login),) if args.expected_login is not None else ALLOWED_FTMO_DEMO_LOGINS
    manifest = export_ftmo_m1_suite(
        portable_root=args.portable_root,
        out_dir=args.out_dir,
        symbols=tuple(args.symbols),
        start_year=args.start_year,
        end_year=args.end_year,
        allowed_logins=allowed,
    )
    print(
        json.dumps(
            {
                "ok": True,
                "out_dir": str(args.out_dir),
                "symbol_count": manifest["symbol_count"],
                "total_rows": manifest["total_rows"],
                "holdout_rows_analysed": manifest["holdout_rows_analysed"],
                "mt5_processes_after_export": manifest["mt5_processes_after_export"],
                "intersection": manifest["intersection"],
            },
            indent=2,
        )
    )
    return 0


__all__ = [
    "ALLOWED_FTMO_DEMO_LOGINS",
    "BROKER_TZ",
    "BROKER_TZ_DST_SCHEDULE",
    "CANONICAL_SYMBOL_MAP",
    "DEFAULT_OUT_DIR",
    "DEFAULT_PORTABLE_ROOT",
    "EXPECTED_SERVER",
    "FORBIDDEN_PATH_TOKENS",
    "HOLDOUT_CUTOFF_UTC_ISO",
    "HOLDOUT_CUTOFF_UTC_TS",
    "HoldoutViolationError",
    "M1ValidationError",
    "MANIFEST_SCHEMA",
    "MAX_ALLOWED_DEV_BAR_TS_UTC",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PORT_7E_SYMBOLS",
    "SOURCE_PROVENANCE",
    "SafetyLockError",
    "assert_pre_holdout_date_window",
    "assert_safe_portable_root",
    "assert_zero_mt5_processes",
    "compute_intersection_window",
    "decode_ftmo_server_times_to_utc",
    "export_ftmo_m1_suite",
    "fetch_symbol_m1_from_mt5",
    "list_running_mt5_processes",
    "load_exported_m1",
    "render_readonly_export_ini",
    "save_sealed_symbol_npz",
    "validate_demo_account",
    "validate_m1_arrays",
    "verify_exported_manifest",
    "verify_exported_npz",
]


if __name__ == "__main__":
    raise SystemExit(main())
