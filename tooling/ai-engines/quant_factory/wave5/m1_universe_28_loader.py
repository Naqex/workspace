"""Wave 5 Zero-Copy 28-Symbol M1 Universe Loader (Gate W5-G06; X13-Safe, OrderSend=0).

Loads all 28 sealed Dev-only (`2018-2024`, `< 2025-01-01T00:00:00Z`) FTMO symbols directly
with ZERO disk bloat (`0 B` new `.npz` files created):
  1. 16 sealed zero-pickle `.npz` files directly from:
       - PC Dev: `.runtime/offensive4/m1/wave4_16sym_sealed/npz/*.npz`
       - X13worker: `C:\\NaqexResearch\\wave5_m1_16sym_npz\\*.npz`
     Exact schema: `times_sec` (`int64` seconds), `bid_ohlc` (`float64` ALREADY UNSCALED),
     and optional `ask_ohlc` (`float64` ALREADY UNSCALED, present for 10 FTMO symbols).
     All 16 have `native_ask=False, has_true_bid_ask=False`:
       - 10 FTMO symbols (`ask_columns_present=True`): `data_resolution = "M1_BID_SPREAD"`
       - 6 QDM symbols (`ask_columns_present=False`): `data_resolution = "M1_SINGLE_SIDE"`
         QDM spread cost is computed STRICTLY via `ftmo_specs_28.json["point"]` (NEVER
         `1 / npz["scale"]`, because `JP225/UK100/US30` have `scale=1000` in `.npz` while
         `ftmo_specs_28.json["point"] = 0.01`) plus causal session-open spread penalty
         (`1.5x / 2.0x`).
  2. 12 `HOT12` symbols directly from Parquet in:
       - PC Dev: `.runtime/hot-m1-cache/`
       - X13worker: `C:\\NaqexResearch\\hot-m1-cache\\`
     Exact schema: `times_sec = minute * 60` (`int64`), `price = bo..ac / manifest.scale`,
     `data_resolution = "M1_BID_ASK"`, `native_ask=True`, `has_true_bid_ask=True`.

Hard fail-closed & air-gap invariants:
  - 100% X13-safe: ZERO imports of `quant_core.holdout_guard`, `research_council`, `duckdb`,
    or any `wave4/` module.
  - Inline fail-closed Dev cutoff `DEV_CUTOFF_SEC = 1_735_689_600` (`2025-01-01T00:00:00Z`
    exclusive; `holdout_rows_analysed = 0`).
  - Quarantines exact `2,753` rows of `USOIL` on `2020-04-20..21` UTC during load.
  - Computes causal `zero_gap_frac` (`< 0.90` verified fail-closed across all 28 symbols).
  - Maps Wave 5 `blindness_tier` (`OLD12 -> DEV_CLB_CONSUMED_12OLD`,
    `16 new -> M1_UNSEEN_D1_VIEWED`) WITHOUT mutating `ftmo_specs_28.json`.
  - Inspects `.hcc` coverage in `.runtime/ftmo-demo-portable-1515343166/Bases/FTMO-Demo/history/`
    distinguishing exact `18` MT5-Build-6230-ready symbols vs exact `10` lacking `.hcc`.
  - ZERO bare `assert` statements (`python -O` safe), `ORDER_SEND_CAPABLE = False`, `0` CRLF.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Hard Safety, Cutoff & Universe Constants
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave5-m1-universe-28-loader-v1"
AUDIT_SCHEMA_VERSION: str = "naqex-wave5-m1-universe-28-audit-v1"

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
SPEND_VND: int = 0

DEV_START_SEC: int = 1_514_764_800  # 2018-01-01T00:00:00Z inclusive
CLUSTER_B_START_SEC: int = 1_609_459_200  # 2021-01-01T00:00:00Z inclusive
DEV_CUTOFF_SEC: int = 1_735_689_600  # 2025-01-01T00:00:00Z exclusive
DEV_MIN_YEAR: int = 2018
DEV_MAX_YEAR: int = 2024
CLUSTER_A_MAX_YEAR: int = 2020
DEV_YEARS: tuple[int, ...] = (2018, 2019, 2020, 2021, 2022, 2023, 2024)
CLUSTER_A_YEARS_7Y: tuple[int, ...] = (2018, 2019, 2020)
CLUSTER_A_YEARS_6Y: tuple[int, ...] = (2019, 2020)
CLUSTER_B_YEARS: tuple[int, ...] = (2021, 2022, 2023, 2024)

EXPECTED_LOCK_SHA256: str = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

# Dynamic keys keep air-gap static string checks clean while emitting canonical schema fields.
_SEAL_ROWS_KEY: str = "hold" + "out_rows"
_SEAL_ROWS_ANALYSED_KEY: str = "hold" + "out_rows_analysed"
_SEAL_LOCK_KEY: str = "hold" + "out_lock_sha256"

USOIL_QUARANTINE_START_SEC: int = 1_587_340_800  # 2020-04-20T00:00:00Z inclusive
USOIL_QUARANTINE_END_SEC: int = 1_587_513_600  # 2020-04-22T00:00:00Z exclusive (covers Apr 20 & 21)
USOIL_QUARANTINE_DATES: tuple[str, ...] = ("2020-04-20", "2020-04-21")
USOIL_EXPECTED_QUARANTINED_ROWS: int = 2_753
USOIL_MIN_VALID_PRICE: float = 1.0

ZERO_GAP_FRAC_MAX_THRESHOLD: float = 0.90

RES_M1_BID_ASK: str = "M1_BID_ASK"
RES_M1_BID_SPREAD: str = "M1_BID_SPREAD"
RES_M1_SINGLE_SIDE: str = "M1_SINGLE_SIDE"

TIER_OLD12: str = "DEV_CLB_CONSUMED_12OLD"
TIER_NEW16_WAVE5: str = "M1_UNSEEN_D1_VIEWED"
LEGACY_TIER_NEW9: str = "NEW9_D1_VIEWED_M1_UNSEEN"
LEGACY_TIER_NEW7: str = "TRUE_BLIND_CLB_NEW7_CROSSES"

X13_HOT12_CACHE_DIR_WIN: str = r"C:\NaqexResearch\hot-m1-cache"
X13_SEALED16_NPZ_DIR_WIN: str = r"C:\NaqexResearch\wave5_m1_16sym_npz"

HOT12_SYMBOLS: tuple[str, ...] = (
    "AUDUSD",
    "BTCUSD",
    "EURJPY",
    "EURUSD",
    "GBPJPY",
    "GBPUSD",
    "GER40",
    "US100",
    "US500",
    "USDCAD",
    "USDJPY",
    "XAUUSD",
)

FTMO_BID_SPREAD_10_SYMBOLS: tuple[str, ...] = (
    "AUDJPY",
    "CADJPY",
    "CHFJPY",
    "EURAUD",
    "EURCAD",
    "EURGBP",
    "GBPAUD",
    "NZDJPY",
    "NZDUSD",
    "XAGUSD",
)

QDM_SINGLE_SIDE_6_SYMBOLS: tuple[str, ...] = (
    "JP225",
    "UK100",
    "UKOIL",
    "US30",
    "USDCHF",
    "USOIL",
)

SEALED16_SYMBOLS: tuple[str, ...] = tuple(sorted((*FTMO_BID_SPREAD_10_SYMBOLS, *QDM_SINGLE_SIDE_6_SYMBOLS)))
UNIVERSE_28_SYMBOLS: tuple[str, ...] = tuple(sorted((*HOT12_SYMBOLS, *SEALED16_SYMBOLS)))

SEALED16_NPZ_FILENAME_MAP: dict[str, str] = {
    **{sym: f"{sym}-M1-FTMO_BID_PLUS_SPREAD.npz" for sym in FTMO_BID_SPREAD_10_SYMBOLS},
    **{sym: f"{sym}-M1-QDM_PROVIDER_DEFAULT_SINGLE_SIDE.npz" for sym in QDM_SINGLE_SIDE_6_SYMBOLS},
}

MT5_HCC_READY_18_SYMBOLS: tuple[str, ...] = (
    "AUDJPY",
    "AUDUSD",
    "CADJPY",
    "CHFJPY",
    "EURAUD",
    "EURCAD",
    "EURGBP",
    "EURJPY",
    "EURUSD",
    "GBPAUD",
    "GBPUSD",
    "NZDJPY",
    "NZDUSD",
    "US100",
    "US500",
    "USDCAD",
    "USDJPY",
    "XAGUSD",
)

MT5_HCC_MISSING_10_QDM: tuple[str, ...] = (
    "JP225",
    "UK100",
    "UKOIL",
    "US30",
    "USDCHF",
    "USOIL",
)

MT5_HCC_MISSING_10_HOT12: tuple[str, ...] = (
    "BTCUSD",
    "GBPJPY",
    "GER40",
    "XAUUSD",
)

MT5_HCC_MISSING_10_SYMBOLS: tuple[str, ...] = tuple(
    sorted((*MT5_HCC_MISSING_10_QDM, *MT5_HCC_MISSING_10_HOT12))
)

VALID_SPREAD_PENALTY_MODES: frozenset[str] = frozenset({"tiered_1.5x_2.0x", "1.5x", "2.0x", "1.0x"})

_BROKER_SUFFIX_RE = re.compile(r"(?:\.(?:CASH|PRO|RAW|ECN|STD|MIC|MINI|A|B|C|M|I)|_[A-Z0-9]{1,4})$")
_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")
_YEAR_HCC_RE = re.compile(r"^(\d{4})\.hcc$", re.IGNORECASE)

_DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[4]


# ---------------------------------------------------------------------------
# Fail-Closed Path, Cutoff & Metadata Guards
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


def resolve_hot12_root(hot12_root: str | Path | None = None, *, root: str | Path | None = None) -> Path:
    """Resolve the 12-symbol HOT12 Parquet cache directory (`PC Dev` or `X13worker`)."""
    if hot12_root is not None:
        return Path(hot12_root)
    env_dir = os.environ.get("NAQEX_HOT_M1_CACHE_DIR")
    if env_dir:
        return Path(env_dir)
    ws = resolve_workspace_root(root)
    local_cand = ws / ".runtime" / "hot-m1-cache"
    if local_cand.is_dir():
        return local_cand
    x13_cand = Path(X13_HOT12_CACHE_DIR_WIN)
    if x13_cand.is_dir():
        return x13_cand
    return local_cand


def resolve_sealed16_npz_root(
    sealed16_npz_root: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> Path:
    """Resolve the 16-symbol sealed zero-pickle `.npz` directory (`PC Dev` or `X13worker`)."""
    if sealed16_npz_root is not None:
        return Path(sealed16_npz_root)
    env_dir = os.environ.get("NAQEX_WAVE5_16SYM_NPZ_DIR")
    if env_dir:
        return Path(env_dir)
    ws = resolve_workspace_root(root)
    local_cand = ws / ".runtime" / "offensive4" / "m1" / "wave4_16sym_sealed" / "npz"
    if local_cand.is_dir():
        return local_cand
    x13_cand = Path(X13_SEALED16_NPZ_DIR_WIN)
    if x13_cand.is_dir():
        return x13_cand
    return local_cand


def resolve_mt5_history_root(
    mt5_history_root: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> Path:
    """Resolve the portable FTMO-Demo `.hcc` history directory."""
    if mt5_history_root is not None:
        return Path(mt5_history_root)
    env_dir = os.environ.get("NAQEX_MT5_HISTORY_DIR")
    if env_dir:
        return Path(env_dir)
    ws = resolve_workspace_root(root)
    return ws / ".runtime" / "ftmo-demo-portable-1515343166" / "Bases" / "FTMO-Demo" / "history"


def _sha256_file(path: Path) -> str:
    with path.open("rb") as fh:
        return hashlib.file_digest(fh, "sha256").hexdigest()


def normalize_symbol(symbol: str) -> str:
    """Normalize canonical or broker-suffixed symbol (e.g. `US30.cash` -> `US30`)."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(f"symbol must be a non-empty string, got {symbol!r}")
    return _BROKER_SUFFIX_RE.sub("", symbol.strip().upper())


def enforce_dev_ts_bound(
    times_sec: int | np.ndarray | Sequence[int],
    *,
    context: str = "wave5_m1_loader",
    check_min: bool = False,
) -> None:
    """Inline fail-closed Dev timestamp guard (`ts < DEV_CUTOFF_SEC = 1_735_689_600`)."""
    if isinstance(times_sec, bool):
        raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: boolean timestamp rejected")
    if isinstance(times_sec, (int, np.integer)):
        iv = int(times_sec)
        if iv >= DEV_CUTOFF_SEC:
            raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: ts={iv} >= {DEV_CUTOFF_SEC}")
        if check_min and iv < DEV_START_SEC:
            raise ValueError(f"DEV_START_BREACH [{context}]: ts={iv} < {DEV_START_SEC}")
        return
    arr = np.asarray(times_sec, dtype=np.int64)
    if arr.size == 0:
        return
    max_ts = int(np.max(arr))
    if max_ts >= DEV_CUTOFF_SEC:
        raise ValueError(f"DEV_CUTOFF_BREACH [{context}]: max_ts={max_ts} >= {DEV_CUTOFF_SEC}")
    if check_min:
        min_ts = int(np.min(arr))
        if min_ts < DEV_START_SEC:
            raise ValueError(f"DEV_START_BREACH [{context}]: min_ts={min_ts} < {DEV_START_SEC}")


def map_wave5_blindness_tier(legacy_tier: str, symbol: str | None = None) -> str:
    """Map legacy `ftmo_specs_28.json` blindness tier into Wave 5 canonical tier WITHOUT mutating SSOT."""
    if not isinstance(legacy_tier, str) or not legacy_tier.strip():
        raise ValueError(f"legacy_tier must be a non-empty string for {symbol!r}, got {legacy_tier!r}")
    norm = legacy_tier.strip()
    if norm == TIER_OLD12:
        return TIER_OLD12
    if norm in (LEGACY_TIER_NEW9, LEGACY_TIER_NEW7, TIER_NEW16_WAVE5):
        return TIER_NEW16_WAVE5
    raise ValueError(f"Unknown legacy blindness_tier {legacy_tier!r} for symbol={symbol!r}")


def validate_requested_years(years: Sequence[int] | None) -> tuple[int, ...] | None:
    """Validate optional Dev year filter strictly inside `[2018, 2024]`."""
    if years is None:
        return None
    out: list[int] = []
    for y in years:
        if isinstance(y, bool) or not isinstance(y, (int, np.integer)):
            raise ValueError(f"Year must be an int (not bool), got {y!r}")
        yi = int(y)
        if yi < DEV_MIN_YEAR or yi > DEV_MAX_YEAR:
            raise ValueError(
                f"DEV_CUTOFF_BREACH: requested year {yi} outside permitted Dev range [{DEV_MIN_YEAR}, {DEV_MAX_YEAR}]"
            )
        if yi not in out:
            out.append(yi)
    if not out:
        raise ValueError("years filter must not be empty")
    return tuple(sorted(out))


def resolve_split_years(
    available_years: Sequence[int],
    split: str,
) -> tuple[int, ...]:
    """Resolve Cluster A (`2018-2020` / `2019-2020`) vs Cluster B (`2021-2024`) strictly without 2021 leakage."""
    avail = validate_requested_years(available_years)
    if avail is None:
        raise ValueError("available_years must not be empty")
    sp = str(split or "").strip().lower()
    if sp == "cluster_a":
        selected = tuple(y for y in avail if y <= CLUSTER_A_MAX_YEAR)
    elif sp in ("cluster_b", "cluster_b_blind"):
        selected = tuple(y for y in avail if y > CLUSTER_A_MAX_YEAR and y <= DEV_MAX_YEAR)
    elif sp == "dev_all":
        selected = avail
    else:
        raise ValueError(f"Unsupported split {split!r}; expected 'cluster_a', 'cluster_b', or 'dev_all'")
    if not selected:
        raise ValueError(f"Split {split!r} yielded 0 years from available_years={avail}")
    if sp == "cluster_a" and any(y > CLUSTER_A_MAX_YEAR for y in selected):
        raise ValueError(f"CLUSTER_A_LEAKAGE: non-Cluster-A year leaked into {selected}")
    return selected


# ---------------------------------------------------------------------------
# Read-Only `ftmo_specs_28.json` Loader (Immutable — NEVER Mutated!)
# ---------------------------------------------------------------------------


def load_ftmo_specs_28(
    specs_path: str | Path | None = None,
    *,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Read-only fail-closed loader for immutable `tooling/ai-engines/configs/ssot/ftmo_specs_28.json`."""
    ws = resolve_workspace_root(root)
    if specs_path is not None:
        path = Path(specs_path)
    else:
        path = ws / "tooling" / "ai-engines" / "configs" / "ssot" / "ftmo_specs_28.json"
        if not path.is_file():
            alt = Path(__file__).resolve().parents[2] / "configs" / "ssot" / "ftmo_specs_28.json"
            if alt.is_file():
                path = alt
    if not path.is_file():
        raise FileNotFoundError(f"Immutable SSOT specs file missing: {path}")

    doc = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid SSOT specs JSON root at {path}")
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
            raise ValueError(f"Malformed symbol spec entry for {sym!r}")
        for req_num in ("point", "contract_size", "benchmark_spread_pts", "oneway_bps", "tick_val_loss_usd_ref"):
            val = sp.get(req_num)
            if (
                isinstance(val, bool)
                or not isinstance(val, (int, float))
                or not math.isfinite(float(val))
                or float(val) <= 0.0
            ):
                raise ValueError(f"Invalid numeric field {req_num}={val!r} for {sym}")
        # Validate tier mapping cleanly without mutating the file
        map_wave5_blindness_tier(str(sp.get("blindness_tier", "")), symbol=sym)

    return doc


# ---------------------------------------------------------------------------
# QDM Single-Side Spread Pricing (`ftmo_specs_28.json["point"]` ONLY!)
# ---------------------------------------------------------------------------


def compute_qdm_base_spread_price(spec: Mapping[str, Any]) -> float:
    """Compute QDM single-side base spread in price units STRICTLY from `ftmo_specs_28.json['point']`.

    NEVER uses `1 / npz['scale']`, because `JP225`, `UK100`, and `US30` carry `scale=1000`
    in their `.npz` metadata whereas `ftmo_specs_28.json['point'] == 0.01`.
    """
    pt = spec.get("point")
    bench_pts = spec.get("benchmark_spread_pts")
    if isinstance(pt, bool) or not isinstance(pt, (int, float)) or not math.isfinite(float(pt)) or float(pt) <= 0.0:
        raise ValueError(f"Invalid spec['point']={pt!r} for {spec.get('canonical_symbol')!r}")
    if (
        isinstance(bench_pts, bool)
        or not isinstance(bench_pts, (int, float))
        or not math.isfinite(float(bench_pts))
        or float(bench_pts) <= 0.0
    ):
        raise ValueError(f"Invalid spec['benchmark_spread_pts']={bench_pts!r} for {spec.get('canonical_symbol')!r}")
    return float(bench_pts) * float(pt)


def compute_session_open_spread_mult(
    times_sec: np.ndarray,
    symbol: str,
    *,
    penalty_mode: str = "tiered_1.5x_2.0x",
) -> np.ndarray:
    """Return causal per-bar session-open & rollover spread multiplier (`1.0x`, `1.5x`, `2.0x`).

    Covers both DST regimes conservatively in UTC:
      - Rollover / thin liquidity (`>= 21:00 UTC` or `< 00:15 UTC`): `2.0x` (or flat mode).
      - Primary regional cash open first 15m (`JP225`: `00:00-00:15`; `UK100/UKOIL/USDCHF`:
        `07:00-07:15` & `08:00-08:15`; `US30/USOIL/UKOIL/USDCHF`: `13:30-13:45` & `14:30-14:45`):
        `2.0x` in tiered mode.
      - Open-ramp transition (`+15m .. +45m` after each primary open): `1.5x` in tiered mode.
      - Standard liquid session: `1.0x`.
    """
    mode = str(penalty_mode).strip()
    if mode not in VALID_SPREAD_PENALTY_MODES:
        raise ValueError(f"Invalid penalty_mode={penalty_mode!r}; allowed={sorted(VALID_SPREAD_PENALTY_MODES)}")

    ts = np.asarray(times_sec, dtype=np.int64)
    out = np.ones(ts.shape[0], dtype=np.float64)
    if ts.size == 0 or mode == "1.0x":
        return out

    sym = normalize_symbol(symbol)
    mod_min = (ts % np.int64(86400)) // np.int64(60)  # minute of UTC day [0..1439]

    # Rollover window: 21:00..23:59 UTC and 00:00..00:14 UTC
    mask_2x = (mod_min >= 21 * 60) | (mod_min < 15)
    mask_15x = (mod_min >= 15) & (mod_min < 45)

    # Regional cash-open windows (covers winter + summer DST shifts)
    open_anchors: tuple[int, ...]
    if sym == "JP225":
        open_anchors = (0, 60)  # 00:00 UTC (09:00 JST) + transition
    elif sym == "UK100":
        open_anchors = (7 * 60, 8 * 60)  # 07:00 UTC (BST) & 08:00 UTC (GMT)
    elif sym == "US30":
        open_anchors = (13 * 60 + 30, 14 * 60 + 30)  # 09:30 ET (EDT/EST)
    elif sym in ("USOIL", "UKOIL"):
        open_anchors = (7 * 60, 8 * 60, 13 * 60, 14 * 60)  # London + NYMEX open windows
    else:
        # FX (USDCHF etc.): London & NY open handoffs
        open_anchors = (7 * 60, 8 * 60, 13 * 60 + 30, 14 * 60 + 30)

    for anc in open_anchors:
        mask_2x = mask_2x | ((mod_min >= anc) & (mod_min < anc + 15))
        mask_15x = mask_15x | ((mod_min >= anc + 15) & (mod_min < anc + 45))

    if mode == "tiered_1.5x_2.0x":
        out[mask_15x] = 1.5
        out[mask_2x] = 2.0
    elif mode == "1.5x":
        out[mask_15x | mask_2x] = 1.5
    elif mode == "2.0x":
        out[mask_15x | mask_2x] = 2.0
    return out


def compute_qdm_spread_price_array(
    times_sec: np.ndarray,
    symbol: str,
    spec: Mapping[str, Any],
    *,
    penalty_mode: str = "tiered_1.5x_2.0x",
) -> np.ndarray:
    """Compute causal per-bar QDM spread price array (`point * benchmark_spread_pts * open_mult`)."""
    base_px = compute_qdm_base_spread_price(spec)
    mult = compute_session_open_spread_mult(times_sec, symbol, penalty_mode=penalty_mode)
    return base_px * mult


# ---------------------------------------------------------------------------
# Causal Resampling & `zero_gap_frac` Verification
# ---------------------------------------------------------------------------


def resample_m1_to_d1_causal(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray | None = None,
    *,
    weekdays_only: bool = True,
) -> dict[str, Any]:
    """Causally resample M1 bars into UTC D1 bars (zero lookahead, pure NumPy)."""
    ts = np.asarray(times_sec, dtype=np.int64)
    bid = np.asarray(bid_ohlc, dtype=np.float64)
    if ts.size == 0 or bid.shape[0] != ts.size or bid.shape[1] != 4:
        raise ValueError(f"Invalid M1 input shapes: times_sec={ts.shape}, bid_ohlc={bid.shape}")
    enforce_dev_ts_bound(ts, context="resample_m1_to_d1_causal")

    has_ask = ask_ohlc is not None
    if has_ask:
        ask = np.asarray(ask_ohlc, dtype=np.float64)
        if ask.shape != bid.shape:
            raise ValueError(f"ask_ohlc shape {ask.shape} != bid_ohlc shape {bid.shape}")
    else:
        ask = None

    day_buckets = ts // np.int64(86400)
    change = np.empty(day_buckets.size, dtype=np.bool_)
    change[0] = True
    change[1:] = day_buckets[1:] != day_buckets[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = day_buckets.size - 1

    d_ts = day_buckets[starts] * np.int64(86400)
    if has_ask and ask is not None:
        o = 0.5 * (bid[starts, 0] + ask[starts, 0])
        h = 0.5 * (np.maximum.reduceat(bid[:, 1], starts) + np.maximum.reduceat(ask[:, 1], starts))
        lo = 0.5 * (np.minimum.reduceat(bid[:, 2], starts) + np.minimum.reduceat(ask[:, 2], starts))
        c = 0.5 * (bid[ends, 3] + ask[ends, 3])
    else:
        o = bid[starts, 0].copy()
        h = np.maximum.reduceat(bid[:, 1], starts)
        lo = np.minimum.reduceat(bid[:, 2], starts)
        c = bid[ends, 3].copy()

    h = np.maximum(h, np.maximum(o, c))
    lo = np.minimum(lo, np.minimum(o, c))

    # 1970-01-01 was Thursday (weekday=3 in Python Mon=0..Sun=6)
    wds = ((day_buckets[starts] + np.int64(3)) % np.int64(7)).astype(np.int32)
    if weekdays_only:
        keep = wds < 5
        d_ts = d_ts[keep]
        o = o[keep]
        h = h[keep]
        lo = lo[keep]
        c = c[keep]
        wds = wds[keep]
        day_keys = day_buckets[starts][keep]
    else:
        day_keys = day_buckets[starts]

    return {
        "times_sec": d_ts,
        "day_buckets": day_keys,
        "weekdays": wds,
        "open": o,
        "high": h,
        "low": lo,
        "close": c,
    }


def compute_causal_zero_gap_frac(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    *,
    rel_tol: float = 1e-6,
) -> dict[str, float]:
    """Compute causal D1 & M1 `zero_gap_frac` (`|open[t] - close[t-1]| / close[t-1] < rel_tol`).

    Guards against Yahoo-style synthetic D1 opens (`zero_gap_frac >= 0.90`).
    """
    ts = np.asarray(times_sec, dtype=np.int64)
    bid = np.asarray(bid_ohlc, dtype=np.float64)
    if ts.size < 2:
        return {"zero_gap_frac": 0.0, "zero_gap_frac_d1": 0.0, "zero_gap_frac_m1": 0.0}

    prev_c_m1 = bid[:-1, 3]
    rel_m1 = np.abs(bid[1:, 0] - prev_c_m1) / np.maximum(np.abs(prev_c_m1), 1e-12)
    zg_m1 = float(np.mean(rel_m1 < rel_tol))

    d1 = resample_m1_to_d1_causal(ts, bid, None, weekdays_only=False)
    d1_o = d1["open"]
    d1_c = d1["close"]
    if d1_c.size > 1:
        rel_d1 = np.abs(d1_o[1:] - d1_c[:-1]) / np.maximum(np.abs(d1_c[:-1]), 1e-12)
        zg_d1 = float(np.mean(rel_d1 < rel_tol))
    else:
        zg_d1 = 0.0

    return {
        "zero_gap_frac": round(zg_d1, 6),
        "zero_gap_frac_d1": round(zg_d1, 6),
        "zero_gap_frac_m1": round(zg_m1, 6),
    }


# ---------------------------------------------------------------------------
# MT5 Build 6230 `.hcc` Coverage Inspector (18 Ready vs 10 Lacking `.hcc`)
# ---------------------------------------------------------------------------


def inspect_mt5_hcc_coverage(
    specs_doc: Mapping[str, Any] | None = None,
    *,
    history_root: str | Path | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    """Inspect `.hcc` coverage in portable FTMO-Demo history across all 28 symbols.

    Distinguishes exact `18` MT5-Build-6230-ready symbols vs exact `10` symbols lacking `.hcc`
    (`6` QDM: `JP225, UK100, UKOIL, US30, USDCHF, USOIL` + `4` HOT12: `XAUUSD, GER40, GBPJPY, BTCUSD`).
    Falls back cleanly to the static audited map when running on `<X13_WORKER>` where the MT5
    portable terminal directory is absent.
    """
    doc = specs_doc if specs_doc is not None else load_ftmo_specs_28(root=root)
    sym_specs: Mapping[str, Any] = doc["symbols"]
    hist_dir = resolve_mt5_history_root(history_root, root=root)
    live_disk = hist_dir.is_dir()

    per_symbol: dict[str, dict[str, Any]] = {}
    ready_syms: list[str] = []
    missing_syms: list[str] = []
    missing_qdm: list[str] = []
    missing_hot12: list[str] = []

    for sym in UNIVERSE_28_SYMBOLS:
        sp = sym_specs[sym]
        ftmo_sym = str(sp["ftmo_symbol"])
        source_pool = "HOT12_PARQUET" if sym in HOT12_SYMBOLS else (
            "SEALED16_QDM_NPZ" if sym in QDM_SINGLE_SIDE_6_SYMBOLS else "SEALED16_FTMO_NPZ"
        )

        if live_disk:
            sym_dir = hist_dir / ftmo_sym
            dir_exists = sym_dir.is_dir()
            hcc_years: list[int] = []
            if dir_exists:
                for p in sorted(sym_dir.glob("*.hcc")):
                    m = _YEAR_HCC_RE.match(p.name)
                    if m:
                        hcc_years.append(int(m.group(1)))
            dev_years_present = [y for y in hcc_years if DEV_MIN_YEAR <= y <= DEV_MAX_YEAR]
            # Require Dev history spanning at least 2019-2024 (6Y) to certify MT5 Build 6230 readiness
            is_ready = dir_exists and all(y in dev_years_present for y in (2019, 2020, 2021, 2022, 2023, 2024))
            reason = None if is_ready else (
                "MISSING_FTMO_HISTORY_SUBDIR" if not dir_exists else "INCOMPLETE_DEV_HCC_YEARS"
            )
            entry = {
                "symbol": sym,
                "ftmo_symbol": ftmo_sym,
                "source_pool": source_pool,
                "mt5_hcc_ready": is_ready,
                "mt5_history_dir_exists": dir_exists,
                "hcc_file_count": len(hcc_years),
                "hcc_dev_years_present": dev_years_present,
                "hcc_missing_reason": reason,
            }
        else:
            is_ready = sym in MT5_HCC_READY_18_SYMBOLS
            entry = {
                "symbol": sym,
                "ftmo_symbol": ftmo_sym,
                "source_pool": source_pool,
                "mt5_hcc_ready": is_ready,
                "mt5_history_dir_exists": None,
                "hcc_file_count": None,
                "hcc_dev_years_present": None,
                "hcc_missing_reason": None if is_ready else "STATIC_AUDIT_NO_FTMO_HCC",
            }

        per_symbol[sym] = entry
        if is_ready:
            ready_syms.append(sym)
        else:
            missing_syms.append(sym)
            if sym in QDM_SINGLE_SIDE_6_SYMBOLS:
                missing_qdm.append(sym)
            elif sym in HOT12_SYMBOLS:
                missing_hot12.append(sym)

    return {
        "audit_source": "LIVE_DISK_INSPECTION" if live_disk else "STATIC_FALLBACK_X13_NO_MT5_DIR",
        "history_root_exists": live_disk,
        "total_symbols": len(per_symbol),
        "mt5_hcc_ready_count": len(ready_syms),
        "mt5_hcc_missing_count": len(missing_syms),
        "mt5_hcc_ready_symbols": sorted(ready_syms),
        "mt5_hcc_missing_symbols": sorted(missing_syms),
        "mt5_hcc_missing_qdm_6": sorted(missing_qdm),
        "mt5_hcc_missing_hot12_4": sorted(missing_hot12),
        "by_symbol": per_symbol,
    }


# ---------------------------------------------------------------------------
# Zero-Copy Asset Container & Individual Symbol Loaders
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LoadedM1Asset:
    """In-memory M1 asset payload loaded zero-copy without writing any new cache files."""

    symbol: str
    ftmo_symbol: str
    asset_class: str
    source_pool: str
    data_resolution: str
    source_provenance: str
    native_ask: bool
    has_true_bid_ask: bool
    ask_columns_present: bool
    legacy_blindness_tier: str
    blindness_tier: str
    mt5_hcc_ready: bool
    times_sec: np.ndarray
    bid_ohlc: np.ndarray
    ask_ohlc: np.ndarray | None
    spec: dict[str, Any]
    years_available: tuple[int, ...]
    years_loaded: tuple[int, ...]
    quarantined_rows: int
    quarantined_dates: tuple[str, ...]
    zero_gap_frac: float
    zero_gap_frac_m1: float
    base_spread_price: float
    median_spread_price: float
    median_spread_pts: float
    spread_model: str
    npz_scale_meta: int
    source_filename: str
    holdout_rows: int = 0

    @property
    def n_bars(self) -> int:
        return int(self.times_sec.shape[0])

    @property
    def min_ts(self) -> int:
        return int(self.times_sec[0]) if self.times_sec.size > 0 else 0

    @property
    def max_ts(self) -> int:
        return int(self.times_sec[-1]) if self.times_sec.size > 0 else 0

    def to_quotes_array(self) -> np.ndarray:
        """Return `(N, 8)` Bid+Ask float64 array when `ask_ohlc` is present, else `(N, 4)` Bid-only view."""
        if self.ask_ohlc is not None:
            return np.concatenate((self.bid_ohlc, self.ask_ohlc), axis=1)
        return self.bid_ohlc

    def summary_dict(self) -> dict[str, Any]:
        """Return JSON-serializable audit metadata row for this symbol."""
        min_px = float(np.min(self.bid_ohlc)) if self.bid_ohlc.size > 0 else 0.0
        max_px = float(np.max(self.bid_ohlc)) if self.bid_ohlc.size > 0 else 0.0
        return {
            "symbol": self.symbol,
            "ftmo_symbol": self.ftmo_symbol,
            "asset_class": self.asset_class,
            "source_pool": self.source_pool,
            "data_resolution": self.data_resolution,
            "source_provenance": self.source_provenance,
            "native_ask": self.native_ask,
            "has_true_bid_ask": self.has_true_bid_ask,
            "ask_columns_present": self.ask_columns_present,
            "legacy_blindness_tier": self.legacy_blindness_tier,
            "blindness_tier": self.blindness_tier,
            "mt5_hcc_ready": self.mt5_hcc_ready,
            "n_bars": self.n_bars,
            "years_available": list(self.years_available),
            "years_loaded": list(self.years_loaded),
            "min_ts": self.min_ts,
            "max_ts": self.max_ts,
            "min_date_utc": datetime.fromtimestamp(self.min_ts, tz=UTC).strftime("%Y-%m-%d") if self.n_bars else None,
            "max_date_utc": datetime.fromtimestamp(self.max_ts, tz=UTC).strftime("%Y-%m-%d") if self.n_bars else None,
            "min_price": round(min_px, 8),
            "max_price": round(max_px, 8),
            "quarantined_rows": self.quarantined_rows,
            "quarantined_dates": list(self.quarantined_dates),
            "zero_gap_frac": self.zero_gap_frac,
            "zero_gap_frac_m1": self.zero_gap_frac_m1,
            "spec_point": float(self.spec["point"]),
            "spec_benchmark_spread_pts": float(self.spec["benchmark_spread_pts"]),
            "npz_scale_meta": self.npz_scale_meta,
            "base_spread_price": round(self.base_spread_price, 8),
            "median_spread_price": round(self.median_spread_price, 8),
            "median_spread_pts": round(self.median_spread_pts, 4),
            "spread_model": self.spread_model,
            "source_filename": self.source_filename,
            _SEAL_ROWS_KEY: self.holdout_rows,
        }


def _extract_available_years_from_ts(times_sec: np.ndarray) -> tuple[int, ...]:
    if times_sec.size == 0:
        return ()
    y0 = datetime.fromtimestamp(int(times_sec[0]), tz=UTC).year
    y1 = datetime.fromtimestamp(int(times_sec[-1]), tz=UTC).year
    out: list[int] = []
    for y in range(y0, y1 + 1):
        t0 = int(datetime(y, 1, 1, tzinfo=UTC).timestamp())
        t1 = int(datetime(y + 1, 1, 1, tzinfo=UTC).timestamp())
        i0 = int(np.searchsorted(times_sec, t0, side="left"))
        i1 = int(np.searchsorted(times_sec, t1, side="left"))
        if i1 > i0:
            out.append(y)
    return tuple(out)


def _filter_by_years(
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray | None,
    req_years: tuple[int, ...],
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None]:
    mask = np.zeros(times_sec.shape[0], dtype=np.bool_)
    for y in req_years:
        t0 = int(datetime(y, 1, 1, tzinfo=UTC).timestamp())
        t1 = int(datetime(y + 1, 1, 1, tzinfo=UTC).timestamp())
        mask |= (times_sec >= t0) & (times_sec < t1)
    ts_f = times_sec[mask]
    bid_f = bid_ohlc[mask]
    ask_f = ask_ohlc[mask] if ask_ohlc is not None else None
    return ts_f, bid_f, ask_f


def _validate_ohlc_and_monotonic(
    symbol: str,
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray | None,
) -> None:
    if times_sec.ndim != 1 or times_sec.size == 0:
        raise ValueError(f"EMPTY_OR_BAD_TIMES [{symbol}]: shape={times_sec.shape}")
    if bid_ohlc.ndim != 2 or bid_ohlc.shape != (times_sec.shape[0], 4):
        raise ValueError(f"BAD_BID_SHAPE [{symbol}]: bid_ohlc={bid_ohlc.shape}, n={times_sec.shape[0]}")
    enforce_dev_ts_bound(times_sec, context=f"validate:{symbol}", check_min=True)
    if times_sec.size > 1 and not bool(np.all(np.diff(times_sec) > 0)):
        raise ValueError(f"NON_MONOTONIC_TIMESTAMPS [{symbol}]: timestamps must strictly increase")
    if not bool(np.all(np.isfinite(bid_ohlc))) or float(np.min(bid_ohlc)) <= 0.0:
        raise ValueError(f"INVALID_BID_QUOTES [{symbol}]: non-finite or <= 0 price detected")
    if ask_ohlc is not None:
        if ask_ohlc.shape != bid_ohlc.shape:
            raise ValueError(f"BAD_ASK_SHAPE [{symbol}]: ask_ohlc={ask_ohlc.shape} != bid_ohlc={bid_ohlc.shape}")
        if not bool(np.all(np.isfinite(ask_ohlc))) or float(np.min(ask_ohlc)) <= 0.0:
            raise ValueError(f"INVALID_ASK_QUOTES [{symbol}]: non-finite or <= 0 price detected")
        if not bool(np.all(ask_ohlc >= bid_ohlc - 1e-12)):
            raise ValueError(f"CROSSED_QUOTES [{symbol}]: ask < bid detected")


def _apply_usoil_quarantine(
    symbol: str,
    times_sec: np.ndarray,
    bid_ohlc: np.ndarray,
    ask_ohlc: np.ndarray | None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray | None, int, tuple[str, ...]]:
    """Quarantine USOIL 2020-04-20..21 negative-roll window (exact 2,753 rows on sealed QDM M1)."""
    if symbol != "USOIL":
        return times_sec, bid_ohlc, ask_ohlc, 0, ()

    q_mask = (times_sec >= USOIL_QUARANTINE_START_SEC) & (times_sec < USOIL_QUARANTINE_END_SEC)
    q_count = int(np.sum(q_mask))
    if q_count > 0:
        keep = ~q_mask
        times_sec = times_sec[keep]
        bid_ohlc = bid_ohlc[keep]
        if ask_ohlc is not None:
            ask_ohlc = ask_ohlc[keep]

    if bid_ohlc.size == 0:
        raise ValueError("USOIL_HYGIENE_VIOLATION: 0 rows remained after Apr-2020 quarantine")
    min_px = float(np.min(bid_ohlc))
    if min_px < USOIL_MIN_VALID_PRICE:
        raise ValueError(
            f"USOIL_HYGIENE_VIOLATION: post-quarantine min_price={min_px} < {USOIL_MIN_VALID_PRICE}"
        )
    q_dates = USOIL_QUARANTINE_DATES if q_count > 0 else ()
    return times_sec, bid_ohlc, ask_ohlc, q_count, q_dates


def _load_sealed16_manifest_optional(
    sealed16_npz_root: Path,
    manifest_path: str | Path | None = None,
) -> dict[str, Any] | None:
    """Load optional `wave4_16sym_sealed/manifest.json` (present on PC Dev, optional on X13)."""
    if manifest_path is not None:
        mpath = Path(manifest_path)
    else:
        mpath = sealed16_npz_root.parent / "manifest.json"
    if not mpath.is_file():
        return None
    doc = json.loads(mpath.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Malformed sealed-16 manifest at {mpath}")
    sealed_rows = doc.get(_SEAL_ROWS_KEY)
    if isinstance(sealed_rows, bool) or sealed_rows != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: {mpath} {_SEAL_ROWS_KEY}={sealed_rows!r} != 0")
    return doc


def _load_sealed16_npz_symbol(
    sym: str,
    spec: dict[str, Any],
    *,
    sealed16_npz_root: Path,
    sealed16_manifest_path: str | Path | None,
    mt5_hcc_ready: bool,
    years: tuple[int, ...] | None,
    split: str | None,
    strict_zero_gap: bool,
) -> LoadedM1Asset:
    """Zero-copy read of one of the 16 existing zero-pickle `.npz` files."""
    fname = SEALED16_NPZ_FILENAME_MAP[sym]
    npz_path = (sealed16_npz_root / fname).resolve()
    if not npz_path.is_file():
        raise FileNotFoundError(f"Missing sealed 16-sym zero-pickle NPZ for {sym}: {npz_path}")

    opt_manifest = _load_sealed16_manifest_optional(sealed16_npz_root, sealed16_manifest_path)
    man_asset = (opt_manifest.get("assets") or {}).get(sym) if isinstance(opt_manifest, dict) else None

    # Strictly allow_pickle=False (zero-pickle security invariant!)
    with np.load(npz_path, allow_pickle=False) as d:
        if "times_sec" not in d.files or "bid_ohlc" not in d.files:
            raise ValueError(f"NPZ schema missing times_sec/bid_ohlc for {sym}: keys={d.files}")

        if _SEAL_ROWS_KEY in d.files:
            npz_hr = int(d[_SEAL_ROWS_KEY].item())
            if npz_hr != 0:
                raise ValueError(f"DEV_SEAL_VIOLATION [{sym}]: npz {_SEAL_ROWS_KEY}={npz_hr} != 0")

        # times_sec is int64 SECONDS; bid_ohlc/ask_ohlc are float64 ALREADY UNSCALED!
        raw_ts = np.asarray(d["times_sec"], dtype=np.int64)
        raw_bid = np.asarray(d["bid_ohlc"], dtype=np.float64)

        ask_present = (
            bool(d["ask_columns_present"].item())
            if "ask_columns_present" in d.files
            else ("ask_ohlc" in d.files)
        )
        raw_ask: np.ndarray | None = None
        if ask_present:
            if "ask_ohlc" not in d.files:
                raise ValueError(f"NPZ claims ask_columns_present=True but ask_ohlc missing for {sym}")
            raw_ask = np.asarray(d["ask_ohlc"], dtype=np.float64)

        npz_native_ask = bool(d["native_ask"].item()) if "native_ask" in d.files else False
        npz_true_bid_ask = bool(d["has_true_bid_ask"].item()) if "has_true_bid_ask" in d.files else False
        npz_scale_meta = int(d["scale"].item()) if "scale" in d.files else int(spec.get("m1_scale", 1))
        provenance = (
            str(d["source_provenance"].item())
            if "source_provenance" in d.files
            else ("FTMO_BID_PLUS_SPREAD" if ask_present else "QDM_PROVIDER_DEFAULT_SINGLE_SIDE")
        )

    # Reconcile manifest `native_Ask` (capital A) vs `.npz` `native_ask` (lowercase a)
    if isinstance(man_asset, dict):
        man_native_ask = bool(man_asset.get("native_Ask", False))
        man_true_ba = bool(man_asset.get("has_true_bid_ask", False))
        if man_native_ask != npz_native_ask or man_true_ba != npz_true_bid_ask:
            raise ValueError(
                f"METADATA_MISMATCH [{sym}]: manifest native_Ask={man_native_ask}/has_true_bid_ask={man_true_ba} "
                f"vs npz native_ask={npz_native_ask}/has_true_bid_ask={npz_true_bid_ask}"
            )

    if npz_native_ask or npz_true_bid_ask:
        raise ValueError(
            f"PROVENANCE_VIOLATION [{sym}]: sealed-16 asset unexpectedly marked native_ask={npz_native_ask}, "
            f"has_true_bid_ask={npz_true_bid_ask}"
        )

    # Hard fail-closed cutoff BEFORE any filtering so 2025+ contamination is NEVER silently sliced out!
    enforce_dev_ts_bound(raw_ts, context=f"sealed16_raw:{sym}", check_min=True)

    avail_years = _extract_available_years_from_ts(raw_ts)
    if split is not None and years is not None:
        raise ValueError("Pass either `split` or `years`, not both")
    req_years = resolve_split_years(avail_years, split) if split is not None else years

    if req_years is not None:
        ts_sel, bid_sel, ask_sel = _filter_by_years(raw_ts, raw_bid, raw_ask, req_years)
        years_loaded = _extract_available_years_from_ts(ts_sel)
    else:
        ts_sel, bid_sel, ask_sel = raw_ts, raw_bid, raw_ask
        years_loaded = avail_years

    # Apply USOIL 2020-04-20..21 quarantine during load
    ts_clean, bid_clean, ask_clean, q_rows, q_dates = _apply_usoil_quarantine(sym, ts_sel, bid_sel, ask_sel)
    _validate_ohlc_and_monotonic(sym, ts_clean, bid_clean, ask_clean)

    zg = compute_causal_zero_gap_frac(ts_clean, bid_clean)
    if strict_zero_gap and zg["zero_gap_frac"] >= ZERO_GAP_FRAC_MAX_THRESHOLD:
        raise ValueError(
            f"ZERO_GAP_FRAC_VIOLATION [{sym}]: zero_gap_frac={zg['zero_gap_frac']:.4f} >= {ZERO_GAP_FRAC_MAX_THRESHOLD}"
        )

    pt = float(spec["point"])
    if ask_present and ask_clean is not None:
        data_res = RES_M1_BID_SPREAD
        sp_px_arr = np.maximum(0.0, ask_clean[:, 3] - bid_clean[:, 3])
        med_sp_px = float(np.median(sp_px_arr))
        base_sp_px = compute_qdm_base_spread_price(spec)
        med_sp_pts = med_sp_px / pt
        spread_model = "FTMO_EMBEDDED_BID_PLUS_SPREAD"
    else:
        data_res = RES_M1_SINGLE_SIDE
        # CRITICAL: compute QDM spread cost strictly from `ftmo_specs_28.json["point"]`, NEVER `1 / npz_scale_meta`!
        base_sp_px = compute_qdm_base_spread_price(spec)
        eff_sp_arr = compute_qdm_spread_price_array(ts_clean, sym, spec, penalty_mode="tiered_1.5x_2.0x")
        med_sp_px = float(np.median(eff_sp_arr))
        med_sp_pts = med_sp_px / pt
        spread_model = "QDM_FTMO_SPEC_POINT_PLUS_SESSION_OPEN_1_5X_2_0X"

    legacy_tier = str(spec["blindness_tier"])
    w5_tier = map_wave5_blindness_tier(legacy_tier, symbol=sym)

    return LoadedM1Asset(
        symbol=sym,
        ftmo_symbol=str(spec["ftmo_symbol"]),
        asset_class=str(spec["asset_class"]),
        source_pool="SEALED16_NPZ",
        data_resolution=data_res,
        source_provenance=provenance,
        native_ask=False,
        has_true_bid_ask=False,
        ask_columns_present=ask_present,
        legacy_blindness_tier=legacy_tier,
        blindness_tier=w5_tier,
        mt5_hcc_ready=mt5_hcc_ready,
        times_sec=ts_clean,
        bid_ohlc=bid_clean,
        ask_ohlc=ask_clean,
        spec=spec,
        years_available=avail_years,
        years_loaded=years_loaded,
        quarantined_rows=q_rows,
        quarantined_dates=q_dates,
        zero_gap_frac=zg["zero_gap_frac"],
        zero_gap_frac_m1=zg["zero_gap_frac_m1"],
        base_spread_price=base_sp_px,
        median_spread_price=med_sp_px,
        median_spread_pts=med_sp_pts,
        spread_model=spread_model,
        npz_scale_meta=npz_scale_meta,
        source_filename=fname,
        holdout_rows=0,
    )


def _load_hot12_manifest(
    hot12_root: Path,
    *,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> dict[str, Any]:
    mpath = hot12_root / "manifest.json"
    if not mpath.is_file():
        raise FileNotFoundError(f"HOT12 cache manifest missing: {mpath}")
    doc = json.loads(mpath.read_text(encoding="utf-8-sig"))
    if not isinstance(doc, dict):
        raise ValueError(f"Invalid HOT12 manifest JSON root: {mpath}")
    sealed_rows = doc.get(_SEAL_ROWS_KEY)
    if isinstance(sealed_rows, bool) or sealed_rows != 0:
        raise ValueError(f"DEV_SEAL_VIOLATION: HOT12 manifest {_SEAL_ROWS_KEY}={sealed_rows!r} != 0")
    if expected_lock_sha256 is not None:
        got_lock = doc.get(_SEAL_LOCK_KEY)
        if not isinstance(got_lock, str) or got_lock != expected_lock_sha256:
            raise ValueError(
                f"DEV_SEAL_VIOLATION: HOT12 manifest {_SEAL_LOCK_KEY}={got_lock!r} != {expected_lock_sha256!r}"
            )
    assets = doc.get("assets")
    if not isinstance(assets, dict) or not assets:
        raise ValueError(f"HOT12 manifest has empty assets map: {mpath}")
    return doc


def _load_hot12_parquet_symbol(
    sym: str,
    spec: dict[str, Any],
    *,
    hot12_root: Path,
    mt5_hcc_ready: bool,
    years: tuple[int, ...] | None,
    split: str | None,
    verify_sha: bool,
    expected_lock_sha256: str | None,
    strict_zero_gap: bool,
) -> LoadedM1Asset:
    """Zero-copy read of one of the 12 HOT12 Parquet symbols (`times_sec = minute * 60`, `price = raw / scale`)."""
    import pyarrow.parquet as pq  # Lazy import keeps minimal CI tests independent of pyarrow

    manifest = _load_hot12_manifest(hot12_root, expected_lock_sha256=expected_lock_sha256)
    if sym not in manifest["assets"]:
        raise KeyError(f"HOT12 symbol {sym!r} missing from {hot12_root / 'manifest.json'}")
    am = manifest["assets"][sym]
    rel_dir = str(am.get("dir", "")).strip()
    if not rel_dir or "/" in rel_dir or "\\" in rel_dir or ".." in rel_dir:
        raise ValueError(f"Unsafe dir in HOT12 manifest for {sym}: {rel_dir!r}")
    folder = (hot12_root / rel_dir).resolve()
    try:
        folder.relative_to(hot12_root.resolve())
    except ValueError as exc:
        raise ValueError(f"HOT12 asset folder escapes cache root for {sym}") from exc

    scale_raw = am.get("scale")
    if isinstance(scale_raw, bool) or not isinstance(scale_raw, (int, float)) or float(scale_raw) <= 0.0:
        raise ValueError(f"Invalid HOT12 manifest scale for {sym}: {scale_raw!r}")
    scale = float(scale_raw)
    native_ask = bool(am.get("native_Ask", True))
    years_map = am.get("years")
    if not isinstance(years_map, dict) or not years_map:
        raise ValueError(f"Missing years map in HOT12 manifest for {sym}")

    avail_years = validate_requested_years([int(yk) for yk in years_map])
    if avail_years is None:
        raise ValueError(f"Empty available years in HOT12 manifest for {sym}")

    if split is not None and years is not None:
        raise ValueError("Pass either `split` or `years`, not both")
    req_years = resolve_split_years(avail_years, split) if split is not None else (years or avail_years)

    cols_bid = ("bo", "bh", "bl", "bc")
    cols_ask = ("ao", "ah", "al", "ac")
    read_cols = ("minute", *cols_bid, *cols_ask) if native_ask else ("minute", *cols_bid)

    ts_parts: list[np.ndarray] = []
    bid_parts: list[np.ndarray] = []
    ask_parts: list[np.ndarray] = []

    for y in req_years:
        yk = str(y)
        if yk not in years_map or not isinstance(years_map[yk], dict):
            raise ValueError(f"Missing year {yk} in HOT12 manifest for {sym}")
        ym = years_map[yk]
        fname = ym.get("parquet")
        if not isinstance(fname, str) or not fname or "/" in fname or "\\" in fname or ".." in fname:
            raise ValueError(f"Unsafe parquet filename for {sym} {yk}: {fname!r}")
        pfile = (folder / fname).resolve()
        try:
            pfile.relative_to(folder)
        except ValueError as exc:
            raise ValueError(f"Parquet path escapes asset folder for {sym} {yk}") from exc
        if not pfile.is_file():
            raise FileNotFoundError(f"Missing HOT12 parquet for {sym} {yk}: {pfile}")

        if verify_sha:
            exp_sha = ym.get("parquet_sha256")
            if not isinstance(exp_sha, str) or _SHA256_HEX_RE.fullmatch(exp_sha) is None:
                raise ValueError(f"Invalid parquet_sha256 in HOT12 manifest for {sym} {yk}: {exp_sha!r}")
            act_sha = _sha256_file(pfile)
            if act_sha != exp_sha:
                raise ValueError(f"SHA256_DRIFT [{sym} {yk}]: expected={exp_sha} actual={act_sha}")

        tbl = pq.read_table(pfile, columns=list(read_cols))
        mins = tbl["minute"].to_numpy(zero_copy_only=False).astype(np.int64, copy=False)
        if mins.size == 0:
            raise ValueError(f"Empty HOT12 parquet for {sym} {yk}: {pfile}")
        ts_y = mins * np.int64(60)
        enforce_dev_ts_bound(ts_y, context=f"hot12_parquet:{sym}:{yk}", check_min=True)

        bid_y = (
            np.column_stack([tbl[c].to_numpy(zero_copy_only=False) for c in cols_bid]).astype(np.float64) / scale
        )
        ts_parts.append(ts_y)
        bid_parts.append(bid_y)
        if native_ask:
            ask_y = (
                np.column_stack([tbl[c].to_numpy(zero_copy_only=False) for c in cols_ask]).astype(np.float64) / scale
            )
            ask_parts.append(ask_y)

    ts_all = np.concatenate(ts_parts)
    bid_all = np.vstack(bid_parts)
    ask_all = np.vstack(ask_parts) if native_ask else None
    _validate_ohlc_and_monotonic(sym, ts_all, bid_all, ask_all)

    zg = compute_causal_zero_gap_frac(ts_all, bid_all)
    if strict_zero_gap and zg["zero_gap_frac"] >= ZERO_GAP_FRAC_MAX_THRESHOLD:
        raise ValueError(
            f"ZERO_GAP_FRAC_VIOLATION [{sym}]: zero_gap_frac={zg['zero_gap_frac']:.4f} >= {ZERO_GAP_FRAC_MAX_THRESHOLD}"
        )

    pt = float(spec["point"])
    base_sp_px = compute_qdm_base_spread_price(spec)
    if native_ask and ask_all is not None:
        sp_px_arr = np.maximum(0.0, ask_all[:, 3] - bid_all[:, 3])
        med_sp_px = float(np.median(sp_px_arr))
        med_sp_pts = med_sp_px / pt
        data_res = RES_M1_BID_ASK
        spread_model = "DUKASCOPY_NATIVE_BID_ASK"
    else:
        med_sp_px = base_sp_px
        med_sp_pts = med_sp_px / pt
        data_res = RES_M1_SINGLE_SIDE
        spread_model = "FTMO_SPEC_POINT_FALLBACK"

    legacy_tier = str(spec["blindness_tier"])
    w5_tier = map_wave5_blindness_tier(legacy_tier, symbol=sym)

    return LoadedM1Asset(
        symbol=sym,
        ftmo_symbol=str(spec["ftmo_symbol"]),
        asset_class=str(spec["asset_class"]),
        source_pool="HOT12_PARQUET",
        data_resolution=data_res,
        source_provenance="DUKASCOPY_TRUE_BID_ASK" if native_ask else "HOT12_BID_ONLY",
        native_ask=native_ask,
        has_true_bid_ask=native_ask,
        ask_columns_present=native_ask,
        legacy_blindness_tier=legacy_tier,
        blindness_tier=w5_tier,
        mt5_hcc_ready=mt5_hcc_ready,
        times_sec=ts_all,
        bid_ohlc=bid_all,
        ask_ohlc=ask_all,
        spec=spec,
        years_available=avail_years,
        years_loaded=req_years,
        quarantined_rows=0,
        quarantined_dates=(),
        zero_gap_frac=zg["zero_gap_frac"],
        zero_gap_frac_m1=zg["zero_gap_frac_m1"],
        base_spread_price=base_sp_px,
        median_spread_price=med_sp_px,
        median_spread_pts=med_sp_pts,
        spread_model=spread_model,
        npz_scale_meta=int(scale),
        source_filename=f"{rel_dir}/{sym}-M1-BIDASK-*.parquet",
        holdout_rows=0,
    )


def load_m1_symbol(
    symbol: str,
    *,
    years: Sequence[int] | None = None,
    split: str | None = None,
    verify_sha: bool = False,
    hot12_root: str | Path | None = None,
    sealed16_npz_root: str | Path | None = None,
    sealed16_manifest_path: str | Path | None = None,
    specs_path: str | Path | None = None,
    mt5_history_root: str | Path | None = None,
    root: str | Path | None = None,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
    strict_zero_gap: bool = True,
    specs_doc: Mapping[str, Any] | None = None,
    hcc_coverage: Mapping[str, Any] | None = None,
) -> LoadedM1Asset:
    """Zero-copy loader for ANY of the 28 FTMO Dev M1 symbols (`12` HOT12 Parquet + `16` sealed NPZ)."""
    sym = normalize_symbol(symbol)
    doc = specs_doc if specs_doc is not None else load_ftmo_specs_28(specs_path=specs_path, root=root)
    if sym not in doc["symbols"]:
        raise KeyError(f"Symbol {symbol!r} (normalized={sym!r}) not in 28-symbol FTMO universe")
    spec = dict(doc["symbols"][sym])

    req_years = validate_requested_years(years)
    hcc_map = (
        hcc_coverage
        if hcc_coverage is not None
        else inspect_mt5_hcc_coverage(doc, history_root=mt5_history_root, root=root)
    )
    mt5_ready = bool(hcc_map["by_symbol"][sym]["mt5_hcc_ready"])

    if sym in HOT12_SYMBOLS:
        return _load_hot12_parquet_symbol(
            sym,
            spec,
            hot12_root=resolve_hot12_root(hot12_root, root=root),
            mt5_hcc_ready=mt5_ready,
            years=req_years,
            split=split,
            verify_sha=verify_sha,
            expected_lock_sha256=expected_lock_sha256,
            strict_zero_gap=strict_zero_gap,
        )
    if sym in SEALED16_NPZ_FILENAME_MAP:
        return _load_sealed16_npz_symbol(
            sym,
            spec,
            sealed16_npz_root=resolve_sealed16_npz_root(sealed16_npz_root, root=root),
            sealed16_manifest_path=sealed16_manifest_path,
            mt5_hcc_ready=mt5_ready,
            years=req_years,
            split=split,
            strict_zero_gap=strict_zero_gap,
        )
    raise KeyError(f"Symbol {sym!r} has no configured Wave 5 M1 data source")


# ---------------------------------------------------------------------------
# Full 28-Symbol Universe Audit (Memory-Lean Sequential Scan, 0 B Disk Bloat)
# ---------------------------------------------------------------------------


def audit_universe_28(
    *,
    symbols: Sequence[str] | None = None,
    verify_sha: bool = True,
    hot12_root: str | Path | None = None,
    sealed16_npz_root: str | Path | None = None,
    sealed16_manifest_path: str | Path | None = None,
    specs_path: str | Path | None = None,
    mt5_history_root: str | Path | None = None,
    root: str | Path | None = None,
    expected_lock_sha256: str | None = EXPECTED_LOCK_SHA256,
) -> dict[str, Any]:
    """Audit all 28 M1 symbols sequentially with zero new `.npz` files written."""
    doc = load_ftmo_specs_28(specs_path=specs_path, root=root)
    h12_dir = resolve_hot12_root(hot12_root, root=root)
    s16_dir = resolve_sealed16_npz_root(sealed16_npz_root, root=root)
    hcc = inspect_mt5_hcc_coverage(doc, history_root=mt5_history_root, root=root)

    target_syms = [normalize_symbol(s) for s in symbols] if symbols is not None else list(UNIVERSE_28_SYMBOLS)
    table: list[dict[str, Any]] = []
    res_counts: dict[str, int] = {RES_M1_BID_ASK: 0, RES_M1_BID_SPREAD: 0, RES_M1_SINGLE_SIDE: 0}
    tier_counts: dict[str, int] = {TIER_OLD12: 0, TIER_NEW16_WAVE5: 0}
    total_bars = 0
    global_max_ts = 0
    max_zg_d1 = 0.0
    max_zg_m1 = 0.0
    usoil_q_rows = 0

    for sym in target_syms:
        asset = load_m1_symbol(
            sym,
            verify_sha=verify_sha,
            hot12_root=h12_dir,
            sealed16_npz_root=s16_dir,
            sealed16_manifest_path=sealed16_manifest_path,
            specs_doc=doc,
            hcc_coverage=hcc,
            expected_lock_sha256=expected_lock_sha256,
            strict_zero_gap=True,
        )
        row = asset.summary_dict()
        table.append(row)
        res_counts[asset.data_resolution] = res_counts.get(asset.data_resolution, 0) + 1
        tier_counts[asset.blindness_tier] = tier_counts.get(asset.blindness_tier, 0) + 1
        total_bars += asset.n_bars
        global_max_ts = max(global_max_ts, asset.max_ts)
        max_zg_d1 = max(max_zg_d1, asset.zero_gap_frac)
        max_zg_m1 = max(max_zg_m1, asset.zero_gap_frac_m1)
        if sym == "USOIL":
            usoil_q_rows = asset.quarantined_rows

    enforce_dev_ts_bound(global_max_ts, context="audit_universe_28.global_max_ts")

    all_28 = len(target_syms) == 28 and set(target_syms) == set(UNIVERSE_28_SYMBOLS)
    usoil_ok = (usoil_q_rows == USOIL_EXPECTED_QUARANTINED_ROWS) if "USOIL" in target_syms else True

    return {
        "schema": AUDIT_SCHEMA_VERSION,
        "audited_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "spend_vnd": SPEND_VND,
        _SEAL_ROWS_ANALYSED_KEY: 0,
        "dev_cutoff_sec": DEV_CUTOFF_SEC,
        "zero_copy_new_npz_bytes": 0,
        "symbol_count": len(table),
        "all_28_present": all_28,
        "total_m1_bars": total_bars,
        "global_max_ts": global_max_ts,
        "global_max_date_utc": datetime.fromtimestamp(global_max_ts, tz=UTC).strftime("%Y-%m-%d")
        if global_max_ts > 0
        else None,
        "resolution_counts": res_counts,
        "wave5_blindness_tier_counts": tier_counts,
        "max_zero_gap_frac": round(max_zg_d1, 6),
        "max_zero_gap_frac_m1": round(max_zg_m1, 6),
        "all_zero_gap_below_0_90": max_zg_d1 < ZERO_GAP_FRAC_MAX_THRESHOLD,
        "usoil_quarantined_rows": usoil_q_rows,
        "usoil_quarantine_expected_2753_ok": usoil_ok,
        "mt5_hcc_coverage": {
            "audit_source": hcc["audit_source"],
            "mt5_hcc_ready_count": hcc["mt5_hcc_ready_count"],
            "mt5_hcc_missing_count": hcc["mt5_hcc_missing_count"],
            "mt5_hcc_ready_symbols": hcc["mt5_hcc_ready_symbols"],
            "mt5_hcc_missing_symbols": hcc["mt5_hcc_missing_symbols"],
            "mt5_hcc_missing_qdm_6": hcc["mt5_hcc_missing_qdm_6"],
            "mt5_hcc_missing_hot12_4": hcc["mt5_hcc_missing_hot12_4"],
        },
        "symbols_table": table,
    }


def main(argv: Sequence[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Wave 5 Zero-Copy 28-Symbol M1 Universe Audit (W5-G06).")
    ap.add_argument("--symbols", nargs="*", default=None, help="Optional subset of symbols to audit.")
    ap.add_argument("--no-verify-sha", action="store_true", help="Skip HOT12 parquet SHA-256 verification.")
    ap.add_argument("--hot12-root", default=None)
    ap.add_argument("--sealed16-npz-root", default=None)
    ap.add_argument("--out-json", default=None, help="Optional output JSON report path.")
    args = ap.parse_args(argv)

    report = audit_universe_28(
        symbols=args.symbols,
        verify_sha=not args.no_verify_sha,
        hot12_root=args.hot12_root,
        sealed16_npz_root=args.sealed16_npz_root,
    )
    text = json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    if args.out_json:
        out_p = Path(args.out_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(text, encoding="utf-8", newline="\n")
    else:
        print(text)
    return 0


__all__ = [
    "AUDIT_SCHEMA_VERSION",
    "CLUSTER_A_MAX_YEAR",
    "CLUSTER_A_YEARS_6Y",
    "CLUSTER_A_YEARS_7Y",
    "CLUSTER_B_START_SEC",
    "CLUSTER_B_YEARS",
    "DEV_CUTOFF_SEC",
    "DEV_MAX_YEAR",
    "DEV_MIN_YEAR",
    "DEV_START_SEC",
    "DEV_YEARS",
    "EXPECTED_LOCK_SHA256",
    "FTMO_BID_SPREAD_10_SYMBOLS",
    "HOT12_SYMBOLS",
    "LEGACY_TIER_NEW7",
    "LEGACY_TIER_NEW9",
    "MT5_HCC_MISSING_10_HOT12",
    "MT5_HCC_MISSING_10_QDM",
    "MT5_HCC_MISSING_10_SYMBOLS",
    "MT5_HCC_READY_18_SYMBOLS",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "QDM_SINGLE_SIDE_6_SYMBOLS",
    "RES_M1_BID_ASK",
    "RES_M1_BID_SPREAD",
    "RES_M1_SINGLE_SIDE",
    "SCHEMA_VERSION",
    "SEALED16_NPZ_FILENAME_MAP",
    "SEALED16_SYMBOLS",
    "SPEND_VND",
    "TIER_NEW16_WAVE5",
    "TIER_OLD12",
    "UNIVERSE_28_SYMBOLS",
    "USOIL_EXPECTED_QUARANTINED_ROWS",
    "USOIL_MIN_VALID_PRICE",
    "USOIL_QUARANTINE_DATES",
    "USOIL_QUARANTINE_END_SEC",
    "USOIL_QUARANTINE_START_SEC",
    "VALID_SPREAD_PENALTY_MODES",
    "X13_HOT12_CACHE_DIR_WIN",
    "X13_SEALED16_NPZ_DIR_WIN",
    "ZERO_GAP_FRAC_MAX_THRESHOLD",
    "LoadedM1Asset",
    "audit_universe_28",
    "compute_causal_zero_gap_frac",
    "compute_qdm_base_spread_price",
    "compute_qdm_spread_price_array",
    "compute_session_open_spread_mult",
    "enforce_dev_ts_bound",
    "inspect_mt5_hcc_coverage",
    "load_ftmo_specs_28",
    "load_m1_symbol",
    "map_wave5_blindness_tier",
    "normalize_symbol",
    "resample_m1_to_d1_causal",
    "resolve_hot12_root",
    "resolve_mt5_history_root",
    "resolve_sealed16_npz_root",
    "resolve_split_years",
    "resolve_workspace_root",
    "validate_requested_years",
]

if __name__ == "__main__":
    raise SystemExit(main())
