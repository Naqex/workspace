"""Wave 4 Strictly Causal 24-Feature Meta-Labeling Matrix Builder (`v4.8.1 FINAL`).

Upgrades Lab #6 (`meta_labeler.py`, 6 coarse portfolio-aggregate features, Brier Skill = -0.004)
to 24 orthogonal, strictly causal, MQL5-replicable (`OnnxRun` / pure `.mqh`) features evaluated
at entry decision time `t_entry` using ONLY strictly closed bars (`close_ts <= t_entry`, so
`bar_ts < t_entry`) and strictly closed prior trade history (`exit_ts <= t_entry`).

Hard safety invariants:
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `DEV_CUTOFF_SEC = 1_735_689_600`,
    `holdout_rows_analysed = 0`).
  - ZERO bare `assert` statements (all guards remain active under `python -O` / `python -OO`).
  - LAZY IMPORTS ONLY for optional ML / Arrow / Pandas libraries: top-level uses stdlib + NumPy
    only so this module imports cleanly in minimal CI environments without ML packages installed.
  - Strict fail-closed rejection of poisoned inputs (`NaN`, `Inf`, `bool` disguised as numeric,
    non-positive OHLC, violated high/low geometry, negative spread, non-monotonic timestamps,
    and any date/timestamp `>= 2025-01-01`).
"""

from __future__ import annotations

import copy
import heapq
import inspect
import json
import math
import os
import re
import tempfile
import zlib
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical Schema
# ---------------------------------------------------------------------------

SCHEMA_VERSION: str = "naqex-wave4-ml-features-24-v1"
ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DATE: str = "2024-12-31"
DEV_CUTOFF_DATE: str = "2025-01-01"
DEV_CUTOFF_SEC: int = 1_735_689_600  # 2025-01-01T00:00:00Z (strict exclusive upper bound)

_EPS: float = 1e-12
_PARKINSON_DENOM_COEFF: float = 4.0 * math.log(2.0)
_TWO_PI: float = 2.0 * math.pi
_ISO_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_BROKER_SUFFIX_RE = re.compile(r"(?:\.(?:CASH|PRO|RAW|ECN|STD|MIC|MINI|A|B|C|M|I)|_[A-Z0-9]{1,4})$")

# Canonical 4 x 6 = 24 strictly causal features (order is frozen for ONNX / MQL5 parity)
FEATURE_GROUPS: dict[str, tuple[str, ...]] = {
    "A_VOLATILITY_ATR_REGIME": (
        "atr14_pct",
        "atr5_over_atr20",
        "vol_zscore_60d",
        "d1_range_over_atr14",
        "parkinson_vol_10d",
        "vol_brake_mult_causal",
    ),
    "B_TREND_BREAKOUT_STRUCTURE": (
        "adx14_causal",
        "ema20_slope_atr",
        "dist_ema50_atr",
        "breakout_zscore_20",
        "prev_bar_body_ratio",
        "prev_bar_close_loc",
    ),
    "C_MICROSTRUCTURE_COST_SESSION": (
        "spread_over_atr_ratio",
        "spread_zscore_20",
        "hour_sin_utc",
        "hour_cos_utc",
        "dow_sin",
        "is_london_ny_overlap",
    ),
    "D_PORTFOLIO_STATE_ENGINE_CONTEXT": (
        "engine_id_code",
        "asset_class_code",
        "same_dir_concurrent_count",
        "recent_10_wr_causal",
        "recent_10_avg_r_causal",
        "rolling_dd_pct_causal",
    ),
}

FEATURE_NAMES_24: tuple[str, ...] = (
    *FEATURE_GROUPS["A_VOLATILITY_ATR_REGIME"],
    *FEATURE_GROUPS["B_TREND_BREAKOUT_STRUCTURE"],
    *FEATURE_GROUPS["C_MICROSTRUCTURE_COST_SESSION"],
    *FEATURE_GROUPS["D_PORTFOLIO_STATE_ENGINE_CONTEXT"],
)

FEATURE_SPECS_24: tuple[dict[str, Any], ...] = (
    # Group A — Volatility & ATR Regime (6)
    {
        "index": 0,
        "name": "atr14_pct",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "ATR_14[k] / Close[k] over closed bars <= k",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "Wilder ATR(14) on closed D1 bar shift=1 divided by iClose(sym, PERIOD_D1, 1)",
    },
    {
        "index": 1,
        "name": "atr5_over_atr20",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "ATR_5[k] / ATR_20[k] (1.0 if ATR_20 <= eps)",
        "clip_range": [0.0, 10.0],
        "warmup_default": 1.0,
        "mql5_notes": "Wilder ATR(5) / Wilder ATR(20) on closed D1 shift=1",
    },
    {
        "index": 2,
        "name": "vol_zscore_60d",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "(atr14_pct[k] - mean_60) / std_60 (ddof=1, 0.0 if n<6 or std<=eps)",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "60-bar trailing z-score of atr14_pct on closed D1 bars",
    },
    {
        "index": 3,
        "name": "d1_range_over_atr14",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "(High[k] - Low[k]) / ATR_14[k] (1.0 if ATR_14 <= eps)",
        "clip_range": [0.0, 15.0],
        "warmup_default": 1.0,
        "mql5_notes": "(iHigh(D1,1) - iLow(D1,1)) / ATR_14[shift=1]",
    },
    {
        "index": 4,
        "name": "parkinson_vol_10d",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "sqrt(mean_{j=k-9..k}(ln(H[j]/L[j])^2) / (4*ln(2)))",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "10-bar Parkinson range volatility on closed D1 bars",
    },
    {
        "index": 5,
        "name": "vol_brake_mult_causal",
        "group": "A_VOLATILITY_ATR_REGIME",
        "formula": "clip(1 / (max(1, atr5_over_atr20) * (1 + 0.25 * max(0, vol_zscore_60d - 1.5))), 0.25, 1.0)",
        "clip_range": [0.25, 1.0],
        "warmup_default": 1.0,
        "mql5_notes": "Pure closed-form inverse-vol throttle matching 0.25x Naqex floor",
    },
    # Group B — Trend & Breakout Structure (6)
    {
        "index": 6,
        "name": "adx14_causal",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "Wilder ADX(14) on closed bars 0..k (warmup 20.0 if k<1)",
        "clip_range": [0.0, 100.0],
        "warmup_default": 20.0,
        "mql5_notes": "Wilder 14-period ADX on closed D1 shift=1",
    },
    {
        "index": 7,
        "name": "ema20_slope_atr",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "(EMA_20[k] - EMA_20[max(0, k-5)]) / (step * ATR_14[k])",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "5-bar EMA(20) velocity normalized by ATR(14) on closed D1 shift=1",
    },
    {
        "index": 8,
        "name": "dist_ema50_atr",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "(Close[k] - EMA_50[k]) / ATR_14[k]",
        "clip_range": [-15.0, 15.0],
        "warmup_default": 0.0,
        "mql5_notes": "Signed ATR distance from Close[shift=1] to EMA(50)[shift=1]",
    },
    {
        "index": 9,
        "name": "breakout_zscore_20",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "(Close[k] - mean_20(Close)) / std_20(Close) (ddof=1)",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "20-bar trailing Close z-score on closed D1 bars",
    },
    {
        "index": 10,
        "name": "prev_bar_body_ratio",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "(Close[p] - Open[p]) / (High[p] - Low[p]) on last closed bar p",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "Signed body-to-range ratio of immediately preceding closed bar",
    },
    {
        "index": 11,
        "name": "prev_bar_close_loc",
        "group": "B_TREND_BREAKOUT_STRUCTURE",
        "formula": "(Close[p] - Low[p]) / (High[p] - Low[p]) on last closed bar p",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.5,
        "mql5_notes": "Internal Bar Strength (IBS) of immediately preceding closed bar",
    },
    # Group C — Microstructure, Cost & Session (6)
    {
        "index": 12,
        "name": "spread_over_atr_ratio",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "Spread[p] / ATR_14[k] (price units / price units)",
        "clip_range": [0.0, 5.0],
        "warmup_default": 0.0,
        "mql5_notes": "Last closed bar quoted spread (Ask-Bid) divided by D1 ATR(14)",
    },
    {
        "index": 13,
        "name": "spread_zscore_20",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "(Spread[p] - mean_20(Spread)) / std_20(Spread) over trailing <=20 closed bars",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "20-bar rolling z-score of closed-bar spread",
    },
    {
        "index": 14,
        "name": "hour_sin_utc",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "sin(2*pi * ((t_entry % 86400) / 86400))",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "MathSin(2*M_PI * (double)(t_entry % 86400) / 86400.0)",
    },
    {
        "index": 15,
        "name": "hour_cos_utc",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "cos(2*pi * ((t_entry % 86400) / 86400))",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 1.0,
        "mql5_notes": "MathCos(2*M_PI * (double)(t_entry % 86400) / 86400.0)",
    },
    {
        "index": 16,
        "name": "dow_sin",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "sin(2*pi * py_weekday_utc / 7.0), Mon=0..Sun=6",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "py_dow = (dt.day_of_week + 6) % 7; MathSin(2*M_PI * py_dow / 7.0)",
    },
    {
        "index": 17,
        "name": "is_london_ny_overlap",
        "group": "C_MICROSTRUCTURE_COST_SESSION",
        "formula": "1.0 if 12 <= utc_hour < 17 else 0.0",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_notes": "Pure UTC hour check [12, 17); zero tzdata dependency",
    },
    # Group D — Portfolio State & Engine Context (6)
    {
        "index": 18,
        "name": "engine_id_code",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "Canonical PORT_9E code 1..9, or deterministic CRC32 code in [100, 999]",
        "clip_range": [0.0, 1000000.0],
        "warmup_default": 0.0,
        "mql5_notes": "Static integer ID per engine slot (E1=1..E7=7, S6=8, S7=9)",
    },
    {
        "index": 19,
        "name": "asset_class_code",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "forex=1, indices=2, metals=3, oil=4, crypto=5, other=0",
        "clip_range": [0.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "Static asset class enum matching ftmo_specs_28.json",
    },
    {
        "index": 20,
        "name": "same_dir_concurrent_count",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "Count of currently open portfolio positions with same side at t_entry",
        "clip_range": [0.0, 100.0],
        "warmup_default": 0.0,
        "mql5_notes": "Count of open positions via PositionsTotal() matching entry direction",
    },
    {
        "index": 21,
        "name": "recent_10_wr_causal",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "Win rate (net_R > 0) of last <=10 strictly closed prior trades for same engine (0.5 warmup)",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.5,
        "mql5_notes": "Ring buffer of last 10 closed deal PnL signs for engine magic",
    },
    {
        "index": 22,
        "name": "recent_10_avg_r_causal",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "Mean net_R of last <=10 strictly closed prior trades for same engine (0.0 warmup)",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_notes": "Ring buffer mean R-multiple of last 10 closed deals for engine magic",
    },
    {
        "index": 23,
        "name": "rolling_dd_pct_causal",
        "group": "D_PORTFOLIO_STATE_ENGINE_CONTEXT",
        "formula": "100 * (peak_eq - cur_eq) / peak_eq from strictly closed portfolio trades (exit_ts <= t_entry)",
        "clip_range": [0.0, 100.0],
        "warmup_default": 0.0,
        "mql5_notes": "100.0 * (peakBalance - currentBalance) / peakBalance",
    },
)

ENGINE_ID_CODES: dict[str, int] = {
    "E1_USDJPY_TOKYO": 1,
    "E2_USDJPY_EXP80": 2,
    "E3_GBPUSD_VH": 3,
    "E4_US100_SESS40": 4,
    "E5_US100_RS1130": 5,
    "E6_EURJPY_VOLCOMP": 6,
    "E7_USDJPY_NY10ET": 7,
    "S6_FX_USD_BSK": 8,
    "S7_XAU_EXP120": 9,
}

DEFAULT_ENGINE_BASE_RISK_PCT: dict[str, float] = {
    "E1_USDJPY_TOKYO": 0.1606,
    "E2_USDJPY_EXP80": 0.5894,
    "E3_GBPUSD_VH": 0.75,
    "E4_US100_SESS40": 0.50,
    "E5_US100_RS1130": 0.50,
    "E6_EURJPY_VOLCOMP": 0.50,
    "E7_USDJPY_NY10ET": 0.50,
    "S6_FX_USD_BSK": 0.50,
    "S7_XAU_EXP120": 0.50,
}

ASSET_CLASS_CODES: dict[str, int] = {
    "other": 0,
    "forex": 1,
    "indices": 2,
    "metals": 3,
    "oil": 4,
    "crypto": 5,
}

_ASSET_CLASS_ALIASES: dict[str, str] = {
    "fx": "forex",
    "forex": "forex",
    "currency": "forex",
    "index": "indices",
    "indices": "indices",
    "equity_index": "indices",
    "metal": "metals",
    "metals": "metals",
    "precious_metals": "metals",
    "oil": "oil",
    "energy": "oil",
    "commodity": "oil",
    "commodities": "oil",
    "crypto": "crypto",
    "digital": "crypto",
    "other": "other",
}

_INDEX_TOKENS: tuple[str, ...] = (
    "US100", "NAS100", "NDX", "USTEC", "US500", "SPX", "US30", "DJ30", "US2000",
    "GER40", "GER30", "DE40", "DAX", "EU50", "STOXX50", "FRA40", "CAC40",
    "UK100", "FTSE", "JP225", "JPN225", "NIKKEI", "NI225", "AUS200", "ASX200",
)
_METAL_TOKENS: tuple[str, ...] = ("XAU", "XAG", "GOLD", "SILVER", "XPT", "XPD")
_OIL_TOKENS: tuple[str, ...] = ("USOIL", "UKOIL", "WTI", "BRENT", "XTIUSD", "XBRUSD", "USOUSD", "UKOUSD")
_CRYPTO_TOKENS: tuple[str, ...] = ("BTC", "ETH", "SOL", "XRP", "LTC", "ADA", "DOGE", "BNB")
_G8_CCYS: frozenset[str] = frozenset({"USD", "EUR", "GBP", "JPY", "AUD", "CAD", "CHF", "NZD", "SEK", "NOK", "SGD"})


# ---------------------------------------------------------------------------
# Fail-Closed Normalization & Validation Helpers (ZERO Bare `assert`)
# ---------------------------------------------------------------------------


def normalize_symbol(symbol: str) -> str:
    """Normalize canonical or broker-suffixed symbol (e.g. `US100.cash` -> `US100`)."""
    if not isinstance(symbol, str) or not symbol.strip():
        raise ValueError(f"symbol must be a non-empty string, got {symbol!r}")
    norm = symbol.strip().upper()
    return _BROKER_SUFFIX_RE.sub("", norm)


def encode_engine_id(engine_id: Any) -> float:
    """Deterministically encode an engine identifier into a finite float code."""
    if isinstance(engine_id, (bool, np.bool_)):
        raise ValueError(f"POISONED_BOOL_INPUT: engine_id cannot be bool ({engine_id!r})")
    if engine_id is None:
        return 0.0
    if isinstance(engine_id, (int, np.integer)):
        iv = int(engine_id)
        if iv < 0:
            raise ValueError(f"engine_id integer code must be >= 0, got {iv}")
        return float(min(iv, 1_000_000))
    if isinstance(engine_id, (float, np.floating)):
        fv = float(engine_id)
        if not math.isfinite(fv) or fv < 0.0 or not fv.is_integer():
            raise ValueError(f"engine_id float must be a finite non-negative integer value, got {engine_id!r}")
        return float(min(int(fv), 1_000_000))
    s = str(engine_id).strip()
    if not s:
        return 0.0
    su = s.upper()
    if su in ENGINE_ID_CODES:
        return float(ENGINE_ID_CODES[su])
    # Cross-process deterministic code in [100, 999] (never collides with canonical 1..9)
    return float(100 + (zlib.crc32(su.encode("utf-8")) % 900))


def infer_asset_class(symbol: str, asset_class: str | None = None) -> str:
    """Infer canonical asset class (`forex`, `indices`, `metals`, `oil`, `crypto`, `other`)."""
    if asset_class is not None:
        if isinstance(asset_class, (bool, np.bool_)):
            raise ValueError(f"POISONED_BOOL_INPUT: asset_class cannot be bool ({asset_class!r})")
        ac_s = str(asset_class).strip().lower()
        if ac_s:
            if ac_s in _ASSET_CLASS_ALIASES:
                return _ASSET_CLASS_ALIASES[ac_s]
            raise ValueError(f"Unsupported asset_class: {asset_class!r}")
    sym = normalize_symbol(symbol)
    if any(tok in sym for tok in _OIL_TOKENS):
        return "oil"
    if any(tok in sym for tok in _INDEX_TOKENS):
        return "indices"
    if any(tok in sym for tok in _METAL_TOKENS):
        return "metals"
    if any(tok in sym for tok in _CRYPTO_TOKENS):
        return "crypto"
    if len(sym) == 6 and sym[:3] in _G8_CCYS and sym[3:] in _G8_CCYS:
        return "forex"
    return "other"


def encode_asset_class(symbol: str, asset_class: str | None = None) -> float:
    """Return canonical numeric code for the symbol's asset class."""
    cls = infer_asset_class(symbol, asset_class)
    return float(ASSET_CLASS_CODES[cls])


def _reject_bool_scalar(value: Any, *, name: str) -> None:
    if isinstance(value, (bool, np.bool_)):
        raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean {value!r} disguised as numeric")


def _validate_finite_float(value: Any, *, name: str) -> float:
    _reject_bool_scalar(value, name=name)
    if value is None or isinstance(value, (str, bytes)):
        raise ValueError(f"INVALID_NUMERIC_INPUT [{name}]: expected finite float, got {value!r}")
    try:
        fv = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_NUMERIC_INPUT [{name}]: cannot convert {value!r} to float") from exc
    if not math.isfinite(fv):
        raise ValueError(f"NON_FINITE_INPUT [{name}]: got {value!r}")
    return fv


def _validate_float_array(raw: Any, *, name: str, positive: bool = False, non_negative: bool = False) -> np.ndarray:
    """Convert numeric sequence/array to contiguous float64 while fail-closing on bool/NaN/Inf."""
    if raw is None:
        raise ValueError(f"MISSING_ARRAY [{name}]: got None")
    if isinstance(raw, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_ARRAY [{name}]: got scalar {type(raw).__name__}")

    if hasattr(raw, "to_numpy") and hasattr(raw, "dtype"):
        dtype_name = str(raw.dtype).lower()
        if dtype_name in ("bool", "boolean"):
            raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean series rejected")
        arr_raw = raw.to_numpy(copy=False)
    elif isinstance(raw, np.ndarray):
        arr_raw = raw
    else:
        seq = list(raw)
        for idx, item in enumerate(seq):
            if isinstance(item, (bool, np.bool_)):
                raise ValueError(f"POISONED_BOOL_INPUT [{name}[{idx}]]: boolean {item!r} rejected")
            if item is None:
                raise ValueError(f"NON_FINITE_INPUT [{name}[{idx}]]: got None")
        arr_raw = np.asarray(seq)

    if arr_raw.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean ndarray rejected")
    if arr_raw.dtype == object:
        for idx, item in enumerate(arr_raw.flat):
            if isinstance(item, (bool, np.bool_)):
                raise ValueError(f"POISONED_BOOL_INPUT [{name}[{idx}]]: boolean {item!r} rejected")
            if item is None or isinstance(item, (str, bytes)):
                raise ValueError(f"INVALID_NUMERIC_INPUT [{name}[{idx}]]: got {item!r}")

    try:
        arr = np.asarray(arr_raw, dtype=np.float64)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"INVALID_NUMERIC_INPUT [{name}]: cannot cast to float64") from exc

    if arr.ndim == 0:
        raise ValueError(f"INVALID_ARRAY [{name}]: expected >=1D array, got 0D")
    if arr.size > 0 and not bool(np.all(np.isfinite(arr))):
        raise ValueError(f"NON_FINITE_INPUT [{name}]: NaN or Inf detected")
    if arr.size > 0 and positive and float(np.min(arr)) <= 0.0:
        raise ValueError(f"NON_POSITIVE_INPUT [{name}]: min={float(np.min(arr))} <= 0.0")
    if arr.size > 0 and non_negative and float(np.min(arr)) < 0.0:
        raise ValueError(f"NEGATIVE_INPUT [{name}]: min={float(np.min(arr))} < 0.0")
    return np.ascontiguousarray(arr, dtype=np.float64)


def _parse_timestamp_scalar(value: Any, *, name: str) -> int:
    """Parse Unix epoch seconds, ISO string, date, datetime, or np.datetime64 into int64 UTC sec."""
    _reject_bool_scalar(value, name=name)
    if value is None:
        raise ValueError(f"MISSING_TIMESTAMP [{name}]: got None")
    if isinstance(value, (int, np.integer)):
        return int(value)
    if isinstance(value, (float, np.floating)):
        fv = float(value)
        if not math.isfinite(fv):
            raise ValueError(f"NON_FINITE_TIMESTAMP [{name}]: got {value!r}")
        if not fv.is_integer():
            return int(round(fv))
        return int(fv)
    if isinstance(value, np.datetime64):
        if np.isnat(value):
            raise ValueError(f"NON_FINITE_TIMESTAMP [{name}]: got NaT")
        sec = value.astype("datetime64[s]").astype(np.int64)
        return int(sec)
    if isinstance(value, datetime):
        dt = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
        return int(dt.astimezone(UTC).timestamp())
    if isinstance(value, date):
        dt = datetime(value.year, value.month, value.day, tzinfo=UTC)
        return int(dt.timestamp())
    if isinstance(value, str):
        s = value.strip()
        if not s:
            raise ValueError(f"EMPTY_TIMESTAMP [{name}]")
        if _ISO_DATE_ONLY_RE.fullmatch(s):
            d = date.fromisoformat(s)
            return int(datetime(d.year, d.month, d.day, tzinfo=UTC).timestamp())
        s_norm = s[:-1] + "+00:00" if s.endswith(("Z", "z")) else s
        try:
            dt = datetime.fromisoformat(s_norm)
        except ValueError as exc:
            raise ValueError(f"INVALID_TIMESTAMP [{name}]: {value!r}") from exc
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return int(dt.astimezone(UTC).timestamp())
    # Duck-typed pandas Timestamp support without importing pandas
    if hasattr(value, "timestamp") and callable(value.timestamp):
        try:
            ts_f = float(value.timestamp())
        except Exception as exc:
            raise ValueError(f"INVALID_TIMESTAMP [{name}]: {value!r}") from exc
        if not math.isfinite(ts_f):
            raise ValueError(f"NON_FINITE_TIMESTAMP [{name}]: {value!r}")
        return int(ts_f)
    raise ValueError(f"UNSUPPORTED_TIMESTAMP [{name}]: {value!r} ({type(value).__name__})")


def _parse_timestamp_array(raw: Any, *, name: str) -> np.ndarray:
    """Parse an array/sequence of timestamps into contiguous int64 UTC epoch seconds."""
    if raw is None:
        raise ValueError(f"MISSING_TIMESTAMPS [{name}]: got None")
    if isinstance(raw, (bool, np.bool_, str, bytes)):
        raise ValueError(f"INVALID_TIMESTAMPS [{name}]: scalar {type(raw).__name__} rejected")

    if hasattr(raw, "to_numpy") and hasattr(raw, "dtype"):
        dtype_name = str(raw.dtype).lower()
        if dtype_name in ("bool", "boolean"):
            raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean timestamps rejected")
        arr_raw = raw.to_numpy(copy=False)
    elif isinstance(raw, np.ndarray):
        arr_raw = raw
    else:
        seq = list(raw)
        if not seq:
            return np.empty(0, dtype=np.int64)
        return np.array([_parse_timestamp_scalar(v, name=f"{name}[{i}]") for i, v in enumerate(seq)], dtype=np.int64)

    if arr_raw.dtype == np.bool_:
        raise ValueError(f"POISONED_BOOL_INPUT [{name}]: boolean ndarray timestamps rejected")
    if arr_raw.ndim != 1:
        raise ValueError(f"INVALID_TIMESTAMPS [{name}]: expected 1D array, got shape {arr_raw.shape}")
    if arr_raw.size == 0:
        return np.empty(0, dtype=np.int64)
    if np.issubdtype(arr_raw.dtype, np.integer):
        return np.ascontiguousarray(arr_raw, dtype=np.int64)
    if np.issubdtype(arr_raw.dtype, np.floating):
        if not bool(np.all(np.isfinite(arr_raw))):
            raise ValueError(f"NON_FINITE_TIMESTAMP [{name}]: NaN/Inf detected")
        return np.ascontiguousarray(np.rint(arr_raw), dtype=np.int64)
    if np.issubdtype(arr_raw.dtype, np.datetime64):
        if bool(np.any(np.isnat(arr_raw))):
            raise ValueError(f"NON_FINITE_TIMESTAMP [{name}]: NaT detected")
        return np.ascontiguousarray(arr_raw.astype("datetime64[s]").astype(np.int64), dtype=np.int64)
    # Object / string array
    return np.array(
        [_parse_timestamp_scalar(v, name=f"{name}[{i}]") for i, v in enumerate(arr_raw.tolist())],
        dtype=np.int64,
    )


def parse_cutoff_utc_exclusive(cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE) -> int:
    """Parse `cutoff_utc` to an exclusive UTC epoch ceiling and fail-close if `> DEV_CUTOFF_SEC`.

    Date-only strings such as `"2024-12-31"` are treated as inclusive of that UTC day, so
    `"2024-12-31"` maps to exclusive ceiling `2025-01-01T00:00:00Z` (`1_735_689_600`).
    Any request for `2025-01-01` or later immediately raises `ValueError("HOLDOUT_CUTOFF_BREACH: ...")`.
    """
    _reject_bool_scalar(cutoff_utc, name="cutoff_utc")
    if isinstance(cutoff_utc, str):
        s = cutoff_utc.strip()
        if not s:
            raise ValueError("cutoff_utc must be a non-empty date/datetime string")
        if _ISO_DATE_ONLY_RE.fullmatch(s):
            d = date.fromisoformat(s)
            next_day = d + timedelta(days=1)
            excl_sec = int(datetime(next_day.year, next_day.month, next_day.day, tzinfo=UTC).timestamp())
        else:
            ts_val = _parse_timestamp_scalar(s, name="cutoff_utc")
            # Explicit ISO timestamp on/after 2025-01-01T00:00:00Z is strictly forbidden.
            if ts_val >= DEV_CUTOFF_SEC:
                raise ValueError(
                    f"HOLDOUT_CUTOFF_BREACH: cutoff_utc={cutoff_utc!r} "
                    f"(ts={ts_val}) >= DEV_CUTOFF_SEC ({DEV_CUTOFF_SEC})"
                )
            excl_sec = ts_val + 1
    elif isinstance(cutoff_utc, datetime):
        ts_val = _parse_timestamp_scalar(cutoff_utc, name="cutoff_utc")
        if ts_val >= DEV_CUTOFF_SEC:
            raise ValueError(
                f"HOLDOUT_CUTOFF_BREACH: cutoff_utc={cutoff_utc!r} "
                f"(ts={ts_val}) >= DEV_CUTOFF_SEC ({DEV_CUTOFF_SEC})"
            )
        excl_sec = ts_val + 1
    elif isinstance(cutoff_utc, date):
        next_day = cutoff_utc + timedelta(days=1)
        excl_sec = int(datetime(next_day.year, next_day.month, next_day.day, tzinfo=UTC).timestamp())
    elif isinstance(cutoff_utc, (int, np.integer)):
        iv = int(cutoff_utc)
        if iv > DEV_CUTOFF_SEC:
            raise ValueError(f"HOLDOUT_CUTOFF_BREACH: cutoff_utc={iv} > DEV_CUTOFF_SEC ({DEV_CUTOFF_SEC})")
        if iv <= 0:
            raise ValueError(f"cutoff_utc epoch seconds must be > 0, got {iv}")
        excl_sec = iv
    else:
        raise ValueError(f"Unsupported cutoff_utc type: {cutoff_utc!r} ({type(cutoff_utc).__name__})")

    if excl_sec > DEV_CUTOFF_SEC:
        raise ValueError(
            f"HOLDOUT_CUTOFF_BREACH: cutoff_utc={cutoff_utc!r} resolves to exclusive ceiling "
            f"{excl_sec} > DEV_CUTOFF_SEC ({DEV_CUTOFF_SEC}, Holdout 2025+ SEALED)"
        )
    return excl_sec


def _parse_side_scalar(value: Any, *, name: str) -> int:
    _reject_bool_scalar(value, name=name)
    if isinstance(value, (int, np.integer)):
        iv = int(value)
        if iv in (-1, 1):
            return iv
        raise ValueError(f"INVALID_SIDE [{name}]: expected +1 or -1, got {iv}")
    if isinstance(value, (float, np.floating)):
        fv = float(value)
        if not math.isfinite(fv) or fv not in (-1.0, 1.0):
            raise ValueError(f"INVALID_SIDE [{name}]: expected +1 or -1, got {value!r}")
        return int(fv)
    if isinstance(value, str):
        su = value.strip().upper()
        if su in ("LONG", "BUY", "L", "+1", "1"):
            return 1
        if su in ("SHORT", "SELL", "S", "-1"):
            return -1
    raise ValueError(f"INVALID_SIDE [{name}]: unsupported side value {value!r}")


# ---------------------------------------------------------------------------
# Bar Parsing, Causal D1 Resampling & Precomputed Forward-Only Indicators
# ---------------------------------------------------------------------------


def _infer_bar_duration_sec(ts: np.ndarray, *, from_dates_only: bool = False) -> int:
    """Deterministically infer bar duration in seconds using only early prefix bars."""
    if from_dates_only:
        return 86400
    n = ts.size
    if n < 2:
        if n == 1 and int(ts[0]) % 86400 == 0:
            return 86400
        return 60
    sample_n = min(n, 16)
    diffs = np.diff(ts[:sample_n])
    min_diff = int(np.min(diffs))
    if min_diff <= 60:
        return 60
    if min_diff <= 300:
        return 300
    if min_diff <= 900:
        return 900
    if min_diff <= 1800:
        return 1800
    if min_diff <= 3600:
        return 3600
    if min_diff <= 14400:
        return 14400
    return 86400


def _extract_flat_bars(
    raw_bars: Any,
    *,
    symbol: str,
    cutoff_sec_exclusive: int,
) -> dict[str, Any]:
    """Validate and standardize a single flat OHLC/spread bar mapping or DataFrame."""
    if hasattr(raw_bars, "columns") and hasattr(raw_bars, "__getitem__"):
        # Duck-typed pandas DataFrame support without importing pandas
        cols = {str(c): raw_bars[c] for c in raw_bars.columns}
        src: Mapping[str, Any] = cols
    elif isinstance(raw_bars, Mapping):
        src = raw_bars
    else:
        raise ValueError(f"Bars for {symbol} must be a mapping or DataFrame, got {type(raw_bars).__name__}")

    from_dates_only = False
    ts_key = None
    for cand in ("times_sec", "timestamps", "timestamp", "ts", "time"):
        if cand in src and src[cand] is not None:
            ts_key = cand
            break
    if ts_key is not None:
        ts = _parse_timestamp_array(src[ts_key], name=f"{symbol}.{ts_key}")
    elif "dates" in src and src["dates"] is not None:
        ts = _parse_timestamp_array(src["dates"], name=f"{symbol}.dates")
        from_dates_only = True
    elif "date" in src and src["date"] is not None:
        ts = _parse_timestamp_array(src["date"], name=f"{symbol}.date")
        from_dates_only = True
    else:
        raise ValueError(f"Bars for {symbol} missing timestamp column ('times_sec', 'timestamp', or 'dates')")

    n = int(ts.size)
    if n == 0:
        raise ValueError(f"Bars for {symbol} cannot be empty")
    if int(np.max(ts)) >= cutoff_sec_exclusive:
        raise ValueError(
            f"HOLDOUT_BAR_BREACH [{symbol}]: max bar ts={int(np.max(ts))} "
            f">= cutoff_sec_exclusive={cutoff_sec_exclusive}"
        )
    if n > 1 and not bool(np.all(np.diff(ts) > 0)):
        raise ValueError(f"NON_MONOTONIC_TIMESTAMPS [{symbol}]: bar timestamps must strictly increase")

    # OHLC extraction: either `quotes` [bo,bh,bl,bc,(ao,ah,al,ac)] or `open/high/low/close`
    spread_from_quotes: np.ndarray | None = None
    if "quotes" in src and src["quotes"] is not None:
        q = _validate_float_array(src["quotes"], name=f"{symbol}.quotes", positive=True)
        if q.ndim != 2 or q.shape[0] != n or q.shape[1] not in (4, 8):
            raise ValueError(f"INVALID_QUOTES_SHAPE [{symbol}]: expected ({n}, 4|8), got {q.shape}")
        o, h, lo, c = q[:, 0], q[:, 1], q[:, 2], q[:, 3]
        if q.shape[1] == 8:
            if not bool(np.all(q[:, 4:8] >= q[:, 0:4] - _EPS)):
                raise ValueError(f"CROSSED_QUOTES [{symbol}]: ask < bid detected")
            spread_from_quotes = np.maximum(0.0, q[:, 7] - q[:, 3])
    else:
        for req_col in ("open", "high", "low", "close"):
            if req_col not in src or src[req_col] is None:
                raise ValueError(f"Bars for {symbol} missing required column {req_col!r}")
        o = _validate_float_array(src["open"], name=f"{symbol}.open", positive=True)
        h = _validate_float_array(src["high"], name=f"{symbol}.high", positive=True)
        lo = _validate_float_array(src["low"], name=f"{symbol}.low", positive=True)
        c = _validate_float_array(src["close"], name=f"{symbol}.close", positive=True)
        if o.shape != (n,) or h.shape != (n,) or lo.shape != (n,) or c.shape != (n,):
            raise ValueError(f"OHLC_LENGTH_MISMATCH [{symbol}]: expected length {n}")

    # Strict OHLC geometry checks
    if bool(np.any(h < lo - _EPS)):
        raise ValueError(f"INVALID_OHLC_GEOMETRY [{symbol}]: high < low detected")
    if bool(np.any(h < np.maximum(o, c) - _EPS)):
        raise ValueError(f"INVALID_OHLC_GEOMETRY [{symbol}]: high < max(open, close) detected")
    if bool(np.any(lo > np.minimum(o, c) + _EPS)):
        raise ValueError(f"INVALID_OHLC_GEOMETRY [{symbol}]: low > min(open, close) detected")

    # Spread extraction (price units, >= 0)
    if "spread_price" in src and src["spread_price"] is not None:
        spread = _validate_float_array(src["spread_price"], name=f"{symbol}.spread_price", non_negative=True)
        if spread.shape != (n,):
            raise ValueError(f"SPREAD_LENGTH_MISMATCH [{symbol}]: expected length {n}, got {spread.shape}")
    elif "spread" in src and src["spread"] is not None:
        spread = _validate_float_array(src["spread"], name=f"{symbol}.spread", non_negative=True)
        if spread.shape != (n,):
            raise ValueError(f"SPREAD_LENGTH_MISMATCH [{symbol}]: expected length {n}, got {spread.shape}")
    elif spread_from_quotes is not None:
        spread = np.ascontiguousarray(spread_from_quotes, dtype=np.float64)
    elif "ask_close" in src and "bid_close" in src and src["ask_close"] is not None and src["bid_close"] is not None:
        ask_c = _validate_float_array(src["ask_close"], name=f"{symbol}.ask_close", positive=True)
        bid_c = _validate_float_array(src["bid_close"], name=f"{symbol}.bid_close", positive=True)
        if ask_c.shape != (n,) or bid_c.shape != (n,):
            raise ValueError(f"BID_ASK_LENGTH_MISMATCH [{symbol}]")
        if bool(np.any(ask_c < bid_c - _EPS)):
            raise ValueError(f"CROSSED_QUOTES [{symbol}]: ask_close < bid_close detected")
        spread = np.maximum(0.0, ask_c - bid_c)
    else:
        spread = np.zeros(n, dtype=np.float64)

    # Bar duration & explicit bar close timestamps
    if "bar_duration_sec" in src and src["bar_duration_sec"] is not None:
        bd_raw = src["bar_duration_sec"]
        _reject_bool_scalar(bd_raw, name=f"{symbol}.bar_duration_sec")
        if not isinstance(bd_raw, (int, np.integer)) or int(bd_raw) <= 0:
            raise ValueError(f"bar_duration_sec must be a positive int, got {bd_raw!r}")
        bar_dur = int(bd_raw)
    else:
        bar_dur = _infer_bar_duration_sec(ts, from_dates_only=from_dates_only)

    if "close_times_sec" in src and src["close_times_sec"] is not None:
        close_ts = _parse_timestamp_array(src["close_times_sec"], name=f"{symbol}.close_times_sec")
        if close_ts.shape != (n,):
            raise ValueError(f"CLOSE_TIMES_LENGTH_MISMATCH [{symbol}]")
        if bool(np.any(close_ts <= ts)):
            raise ValueError(f"INVALID_CLOSE_TIMES [{symbol}]: close_times_sec must be strictly > times_sec")
        if int(np.max(close_ts)) > cutoff_sec_exclusive:
            raise ValueError(
                f"HOLDOUT_BAR_BREACH [{symbol}]: max close_ts={int(np.max(close_ts))} > {cutoff_sec_exclusive}"
            )
    else:
        close_ts = ts + np.int64(bar_dur)

    return {
        "times_sec": ts,
        "close_times_sec": close_ts,
        "bar_duration_sec": bar_dur,
        "open": np.ascontiguousarray(o, dtype=np.float64),
        "high": np.ascontiguousarray(h, dtype=np.float64),
        "low": np.ascontiguousarray(lo, dtype=np.float64),
        "close": np.ascontiguousarray(c, dtype=np.float64),
        "spread": np.ascontiguousarray(spread, dtype=np.float64),
    }


def _resample_intraday_to_causal_d1(bars: Mapping[str, Any]) -> dict[str, Any]:
    """Causally resample M1 bars into UTC daily bars whose close_ts is `(day_bucket + 1) * 86400`.

    Each D1 bucket depends strictly on M1 bars inside that single UTC calendar day only; at trade
    entry time `t_entry`, only buckets with `close_times_sec <= t_entry` (strictly completed prior
    UTC days) are ever read, guaranteeing 0-bit leakage from intraday or future bars.
    """
    ts = bars["times_sec"]
    buckets = (ts // np.int64(86400)).astype(np.int64)
    change = np.empty(buckets.size, dtype=np.bool_)
    change[0] = True
    change[1:] = buckets[1:] != buckets[:-1]
    starts = np.flatnonzero(change)
    ends = np.empty_like(starts)
    ends[:-1] = starts[1:] - 1
    ends[-1] = buckets.size - 1

    day_starts = buckets[starts] * np.int64(86400)
    day_closes = (buckets[starts] + np.int64(1)) * np.int64(86400)
    return {
        "times_sec": day_starts,
        "close_times_sec": day_closes,
        "bar_duration_sec": 86400,
        "open": np.ascontiguousarray(bars["open"][starts], dtype=np.float64),
        "high": np.ascontiguousarray(np.maximum.reduceat(bars["high"], starts), dtype=np.float64),
        "low": np.ascontiguousarray(np.minimum.reduceat(bars["low"], starts), dtype=np.float64),
        "close": np.ascontiguousarray(bars["close"][ends], dtype=np.float64),
        "spread": np.ascontiguousarray(bars["spread"][ends], dtype=np.float64),
    }


def _prepare_symbol_streams(
    raw_entry: Any,
    *,
    symbol: str,
    cutoff_sec_exclusive: int,
) -> dict[str, Any]:
    """Prepare `(d1_bars, intraday_bars)` streams for one symbol cleanly and causally."""
    inferred_ac: str | None = None
    if isinstance(raw_entry, Mapping) and ("d1" in raw_entry or "m1" in raw_entry or "intraday" in raw_entry):
        if raw_entry.get("asset_class") is not None:
            inferred_ac = str(raw_entry["asset_class"])
        d1_raw = raw_entry.get("d1")
        m1_raw = raw_entry.get("m1") if raw_entry.get("m1") is not None else raw_entry.get("intraday")
        if d1_raw is None and m1_raw is None:
            raise ValueError(f"Asset entry for {symbol} has neither 'd1' nor 'm1'/'intraday' bars")
        m1_parsed = (
            _extract_flat_bars(m1_raw, symbol=f"{symbol}.m1", cutoff_sec_exclusive=cutoff_sec_exclusive)
            if m1_raw is not None
            else None
        )
        if d1_raw is not None:
            d1_parsed = _extract_flat_bars(d1_raw, symbol=f"{symbol}.d1", cutoff_sec_exclusive=cutoff_sec_exclusive)
        else:
            if m1_parsed is None:
                raise ValueError(f"Missing bars for {symbol}")
            d1_parsed = (
                _resample_intraday_to_causal_d1(m1_parsed)
                if m1_parsed["bar_duration_sec"] == 60
                else m1_parsed
            )
        intraday_parsed = m1_parsed if m1_parsed is not None else d1_parsed
    else:
        flat = _extract_flat_bars(raw_entry, symbol=symbol, cutoff_sec_exclusive=cutoff_sec_exclusive)
        if flat["bar_duration_sec"] == 60:
            d1_parsed = _resample_intraday_to_causal_d1(flat)
            intraday_parsed = flat
        else:
            d1_parsed = flat
            intraday_parsed = flat

    return {
        "d1": d1_parsed,
        "intraday": intraday_parsed,
        "asset_class": inferred_ac,
        "d1_indicators": _precompute_causal_d1_indicators(d1_parsed),
    }


def _wilder_atr_forward(tr: np.ndarray, period: int) -> np.ndarray:
    """Pure forward-only Wilder ATR (`out[k]` depends ONLY on `tr[0..k]`)."""
    n = tr.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    inv_p = 1.0 / float(period)
    pm1 = float(period - 1)
    run_sum = 0.0
    atr = 0.0
    for k in range(n):
        tk = float(tr[k])
        if k < period - 1:
            run_sum += tk
            out[k] = run_sum / float(k + 1)
        elif k == period - 1:
            run_sum += tk
            atr = run_sum * inv_p
            out[k] = atr
        else:
            atr = (atr * pm1 + tk) * inv_p
            out[k] = atr
    return out


def _ema_forward(c: np.ndarray, period: int) -> np.ndarray:
    """Pure forward-only EMA seeded by running SMA (`out[k]` depends ONLY on `c[0..k]`)."""
    n = c.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    alpha = 2.0 / (float(period) + 1.0)
    one_m = 1.0 - alpha
    run_sum = 0.0
    ema = 0.0
    for k in range(n):
        ck = float(c[k])
        if k < period - 1:
            run_sum += ck
            out[k] = run_sum / float(k + 1)
        elif k == period - 1:
            run_sum += ck
            ema = run_sum / float(period)
            out[k] = ema
        else:
            ema = alpha * ck + one_m * ema
            out[k] = ema
    return out


def _wilder_adx_forward(h: np.ndarray, lo: np.ndarray, c: np.ndarray, period: int = 14) -> np.ndarray:
    """Pure forward-only Wilder ADX in `[0, 100]` (`out[k]` depends ONLY on bars `0..k`)."""
    n = c.size
    out = np.empty(n, dtype=np.float64)
    if n == 0:
        return out
    out[0] = 20.0
    if n == 1:
        return out

    inv_p = 1.0 / float(period)
    pm1 = float(period - 1)

    tr_sum = 0.0
    pdm_sum = 0.0
    mdm_sum = 0.0
    atr_s = 0.0
    pdm_s = 0.0
    mdm_s = 0.0

    dx_sum = 0.0
    dx_cnt = 0
    adx = 20.0

    for k in range(1, n):
        hk = float(h[k])
        lk = float(lo[k])
        hp = float(h[k - 1])
        lp = float(lo[k - 1])
        cp = float(c[k - 1])

        tr_k = max(hk - lk, abs(hk - cp), abs(lk - cp))
        up_m = hk - hp
        dn_m = lp - lk
        pdm_k = up_m if (up_m > dn_m and up_m > 0.0) else 0.0
        mdm_k = dn_m if (dn_m > up_m and dn_m > 0.0) else 0.0

        if k < period:
            tr_sum += tr_k
            pdm_sum += pdm_k
            mdm_sum += mdm_k
            cur_atr = tr_sum / float(k)
            cur_pdm = pdm_sum / float(k)
            cur_mdm = mdm_sum / float(k)
        elif k == period:
            tr_sum += tr_k
            pdm_sum += pdm_k
            mdm_sum += mdm_k
            atr_s = tr_sum * inv_p
            pdm_s = pdm_sum * inv_p
            mdm_s = mdm_sum * inv_p
            cur_atr, cur_pdm, cur_mdm = atr_s, pdm_s, mdm_s
        else:
            atr_s = (atr_s * pm1 + tr_k) * inv_p
            pdm_s = (pdm_s * pm1 + pdm_k) * inv_p
            mdm_s = (mdm_s * pm1 + mdm_k) * inv_p
            cur_atr, cur_pdm, cur_mdm = atr_s, pdm_s, mdm_s

        if cur_atr > _EPS:
            pdi = 100.0 * (cur_pdm / cur_atr)
            mdi = 100.0 * (cur_mdm / cur_atr)
        else:
            pdi = 0.0
            mdi = 0.0
        di_sum = pdi + mdi
        dx = (100.0 * abs(pdi - mdi) / di_sum) if di_sum > _EPS else 0.0

        dx_cnt += 1
        if dx_cnt < period:
            dx_sum += dx
            adx = dx_sum / float(dx_cnt)
        elif dx_cnt == period:
            dx_sum += dx
            adx = dx_sum * inv_p
        else:
            adx = (adx * pm1 + dx) * inv_p
        out[k] = min(100.0, max(0.0, adx))
    return out


def _rolling_zscore_forward(arr: np.ndarray, window: int, *, min_obs: int = 3) -> np.ndarray:
    """Pure forward-only trailing rolling z-score (`out[k]` uses ONLY `arr[k-window+1 .. k]`)."""
    n = arr.size
    out = np.zeros(n, dtype=np.float64)
    for k in range(n):
        start = max(0, k - window + 1)
        cnt = k - start + 1
        if cnt < min_obs:
            out[k] = 0.0
            continue
        win = arr[start : k + 1]
        mean = float(np.mean(win))
        sd = float(np.std(win, ddof=1))
        if sd > _EPS:
            out[k] = (float(arr[k]) - mean) / sd
        else:
            out[k] = 0.0
    return out


def _parkinson_vol_forward(h: np.ndarray, lo: np.ndarray, window: int = 10) -> np.ndarray:
    """Pure forward-only Parkinson high-low volatility over trailing `window` bars."""
    n = h.size
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    log_hl = np.log(np.maximum(h / np.maximum(lo, _EPS), 1.0))
    sq = log_hl * log_hl
    csum = np.cumsum(sq)
    for k in range(n):
        start = max(0, k - window + 1)
        cnt = k - start + 1
        total_sq = float(csum[k] - (csum[start - 1] if start > 0 else 0.0))
        out[k] = math.sqrt(max(0.0, total_sq / (_PARKINSON_DENOM_COEFF * float(cnt))))
    return out


def _precompute_causal_d1_indicators(bars: Mapping[str, Any]) -> dict[str, np.ndarray]:
    """Precompute strictly forward-only daily indicators where index `k` uses ONLY bars `0..k`."""
    h = bars["high"]
    lo = bars["low"]
    c = bars["close"]
    n = c.size

    tr = np.empty(n, dtype=np.float64)
    tr[0] = h[0] - lo[0]
    if n > 1:
        pc = c[:-1]
        tr[1:] = np.maximum(h[1:] - lo[1:], np.maximum(np.abs(h[1:] - pc), np.abs(lo[1:] - pc)))

    atr5 = _wilder_atr_forward(tr, 5)
    atr14 = _wilder_atr_forward(tr, 14)
    atr20 = _wilder_atr_forward(tr, 20)
    ema20 = _ema_forward(c, 20)
    ema50 = _ema_forward(c, 50)
    adx14 = _wilder_adx_forward(h, lo, c, 14)

    atr14_pct = np.clip(atr14 / np.maximum(c, _EPS), 0.0, 1.0)
    atr5_over_atr20 = np.clip(np.where(atr20 > _EPS, atr5 / np.where(atr20 > _EPS, atr20, 1.0), 1.0), 0.0, 10.0)
    vol_zscore_60d = np.clip(_rolling_zscore_forward(atr14_pct, 60, min_obs=6), -10.0, 10.0)
    d1_range_over_atr14 = np.clip(
        np.where(atr14 > _EPS, (h - lo) / np.where(atr14 > _EPS, atr14, 1.0), 1.0),
        0.0,
        15.0,
    )
    parkinson_vol_10d = np.clip(_parkinson_vol_forward(h, lo, 10), 0.0, 1.0)

    # Pure causal inverse-vol brake in [0.25, 1.0]
    r_vol = np.maximum(1.0, atr5_over_atr20)
    z_exc = np.maximum(0.0, vol_zscore_60d - 1.5)
    vol_brake_mult = np.clip(1.0 / (r_vol * (1.0 + 0.25 * z_exc)), 0.25, 1.0)

    ema20_slope_atr = np.zeros(n, dtype=np.float64)
    for k in range(1, n):
        lag = min(k, 5)
        ak = float(atr14[k])
        if ak > _EPS:
            ema20_slope_atr[k] = (float(ema20[k]) - float(ema20[k - lag])) / (float(lag) * ak)
    ema20_slope_atr = np.clip(ema20_slope_atr, -10.0, 10.0)

    dist_ema50_atr = np.clip(
        np.where(atr14 > _EPS, (c - ema50) / np.where(atr14 > _EPS, atr14, 1.0), 0.0),
        -15.0,
        15.0,
    )
    breakout_zscore_20 = np.clip(_rolling_zscore_forward(c, 20, min_obs=3), -10.0, 10.0)

    return {
        "atr14": atr14,
        "atr14_pct": atr14_pct,
        "atr5_over_atr20": atr5_over_atr20,
        "vol_zscore_60d": vol_zscore_60d,
        "d1_range_over_atr14": d1_range_over_atr14,
        "parkinson_vol_10d": parkinson_vol_10d,
        "vol_brake_mult_causal": vol_brake_mult,
        "adx14_causal": adx14,
        "ema20_slope_atr": ema20_slope_atr,
        "dist_ema50_atr": dist_ema50_atr,
        "breakout_zscore_20": breakout_zscore_20,
    }


def _extract_trade_records(
    trades_df: Any,
    *,
    cutoff_sec_exclusive: int,
) -> list[dict[str, Any]]:
    """Standardize `trades_df` (DataFrame, list of dicts, or column dict) with fail-closed validation."""
    if trades_df is None:
        raise ValueError("trades_df cannot be None")

    rows_raw: list[Mapping[str, Any]]
    if hasattr(trades_df, "to_dict") and hasattr(trades_df, "columns"):
        # Duck-typed pandas DataFrame without top-level pandas import
        rows_raw = list(trades_df.to_dict(orient="records"))
    elif isinstance(trades_df, Mapping):
        if not trades_df:
            return []
        first_val = next(iter(trades_df.values()))
        if isinstance(first_val, (str, bytes, int, float, bool)):
            raise ValueError("trades_df mapping must map column names to equal-length sequences")
        n_rows = len(first_val)
        cols_dict = {str(k): list(v) for k, v in trades_df.items()}
        for col_name, col_vals in cols_dict.items():
            if len(col_vals) != n_rows:
                raise ValueError(f"Column length mismatch in trades_df for {col_name!r}: {len(col_vals)} != {n_rows}")
        rows_raw = [{k: cols_dict[k][i] for k in cols_dict} for i in range(n_rows)]
    elif isinstance(trades_df, Sequence) and not isinstance(trades_df, (str, bytes)):
        rows_raw = []
        for idx, item in enumerate(trades_df):
            if not isinstance(item, Mapping):
                raise ValueError(f"trades_df[{idx}] must be a mapping, got {type(item).__name__}")
            rows_raw.append(item)
    else:
        raise ValueError(f"Unsupported trades_df type: {type(trades_df).__name__}")

    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows_raw):
        # Symbol
        sym_raw = None
        for sk in ("symbol", "asset", "ticker"):
            if sk in row and row[sk] is not None:
                sym_raw = row[sk]
                break
        if sym_raw is None:
            raise ValueError(f"trades_df[{idx}] missing symbol/asset field")
        sym = normalize_symbol(str(sym_raw)) if isinstance(sym_raw, str) else normalize_symbol(sym_raw)

        # Entry timestamp
        entry_raw = None
        for ek in ("entry_ts", "t_entry", "entry", "entry_time", "entry_utc", "timestamp", "entry_date", "day"):
            if ek in row and row[ek] is not None:
                entry_raw = row[ek]
                break
        if entry_raw is None:
            raise ValueError(f"trades_df[{idx}] missing entry timestamp field")
        entry_ts = _parse_timestamp_scalar(entry_raw, name=f"trades_df[{idx}].entry_ts")
        if entry_ts >= cutoff_sec_exclusive:
            raise ValueError(
                f"HOLDOUT_TRADE_BREACH: trades_df[{idx}] entry_ts={entry_ts} "
                f">= cutoff_sec_exclusive={cutoff_sec_exclusive}"
            )

        # Optional exit timestamp
        exit_raw = None
        for xk in ("exit_ts", "t_exit", "exit", "exit_time", "exit_utc", "exit_date"):
            if xk in row and row[xk] is not None:
                exit_raw = row[xk]
                break
        exit_ts: int | None = None
        if exit_raw is not None:
            exit_ts = _parse_timestamp_scalar(exit_raw, name=f"trades_df[{idx}].exit_ts")
            if exit_ts < entry_ts:
                raise ValueError(f"TIME_TRAVEL_TRADE: trades_df[{idx}] exit_ts={exit_ts} < entry_ts={entry_ts}")
            if exit_ts >= cutoff_sec_exclusive:
                raise ValueError(
                    f"HOLDOUT_TRADE_BREACH: trades_df[{idx}] exit_ts={exit_ts} "
                    f">= cutoff_sec_exclusive={cutoff_sec_exclusive}"
                )

        # Side
        side_raw = None
        for dk in ("side", "direction", "dir"):
            if dk in row and row[dk] is not None:
                side_raw = row[dk]
                break
        if side_raw is None:
            raise ValueError(f"trades_df[{idx}] missing side/direction field")
        side = _parse_side_scalar(side_raw, name=f"trades_df[{idx}].side")

        # Engine ID
        eng_raw = None
        for gk in ("engine_id", "engine", "strategy_id", "magic"):
            if gk in row and row[gk] is not None:
                eng_raw = row[gk]
                break
        eng_code = encode_engine_id(eng_raw)
        eng_key = str(eng_raw).strip().upper() if eng_raw is not None and str(eng_raw).strip() else "__DEFAULT__"

        # Optional asset class
        ac_raw = row.get("asset_class")

        # Optional net_R (realized trade return in R units; ONLY read after exit_ts <= t_entry!)
        net_r_raw = None
        for rk in ("net_R", "net_r", "r_mult", "pnl_r", "return_r"):
            if rk in row and row[rk] is not None:
                net_r_raw = row[rk]
                break
        net_r: float | None = None
        if net_r_raw is not None:
            net_r = _validate_finite_float(net_r_raw, name=f"trades_df[{idx}].net_R")

        # Optional risk_pct (percent of equity per 1R, e.g. 0.50 = 0.50%)
        risk_raw = None
        for rpk in ("risk_pct", "base_risk_pct"):
            if rpk in row and row[rpk] is not None:
                risk_raw = row[rpk]
                break
        if risk_raw is not None:
            risk_pct = _validate_finite_float(risk_raw, name=f"trades_df[{idx}].risk_pct")
            if risk_pct <= 0.0 or risk_pct > 100.0:
                raise ValueError(f"INVALID_RISK_PCT [trades_df[{idx}]]: must be in (0, 100], got {risk_pct}")
        else:
            risk_pct = DEFAULT_ENGINE_BASE_RISK_PCT.get(eng_key, 0.50)

        out.append(
            {
                "orig_idx": idx,
                "symbol": sym,
                "entry_ts": entry_ts,
                "exit_ts": exit_ts,
                "side": side,
                "engine_key": eng_key,
                "engine_id_code": eng_code,
                "asset_class": ac_raw,
                "net_R": net_r,
                "risk_frac": risk_pct / 100.0,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Main Strictly Causal 24-Feature Matrix Builder
# ---------------------------------------------------------------------------


def build_causal_feature_matrix(
    bars_by_symbol: Mapping[str, Any],
    trades_df: Any,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    *,
    return_metadata: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Build the strictly causal `(n_trades, 24)` `float32` feature matrix at each trade's `t_entry`.

    Every feature at row `i` uses ONLY:
      - Strictly closed bars (`bar_close_ts <= t_entry`, hence `bar_open_ts < t_entry`),
      - Strictly prior closed trades (`exit_ts <= t_entry`; or `entry_ts < t_entry` if `exit_ts`
        is omitted) for win-rate, average-R, and realized equity drawdown,
      - Observable currently open positions (`entry_ts < t_entry < exit_ts`, plus earlier index at
        identical `entry_ts`) for `same_dir_concurrent_count`.

    Output row order matches `trades_df` 1-to-1 even if `trades_df` is unsorted.
    All guards remain active under `python -O` (zero bare `assert`).
    """
    if not isinstance(bars_by_symbol, Mapping) or not bars_by_symbol:
        raise ValueError("bars_by_symbol must be a non-empty mapping of symbol -> bar data")

    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    trades = _extract_trade_records(trades_df, cutoff_sec_exclusive=cutoff_sec_excl)

    # Validate & precompute causal forward-only series for all provided symbols
    prepared_by_sym: dict[str, dict[str, Any]] = {}
    for raw_sym, raw_bars in bars_by_symbol.items():
        norm_sym = normalize_symbol(str(raw_sym))
        prepared_by_sym[norm_sym] = _prepare_symbol_streams(
            raw_bars,
            symbol=norm_sym,
            cutoff_sec_exclusive=cutoff_sec_excl,
        )

    n_trades = len(trades)
    for tr in trades:
        if tr["symbol"] not in prepared_by_sym:
            raise ValueError(f"UNKNOWN_SYMBOL: trade symbol {tr['symbol']!r} not found in bars_by_symbol")

    x_mat = np.empty((n_trades, len(FEATURE_NAMES_24)), dtype=np.float32)

    if n_trades > 0:
        # Chronological sweep with min-heap on exit_ts guarantees O(N log N) exact causality
        order = sorted(
            range(n_trades),
            key=lambda i: (trades[i]["entry_ts"], trades[i]["engine_key"], trades[i]["orig_idx"]),
        )

        # Min-heap of active open trades with known exit_ts:
        # (exit_ts, entry_ts, engine_key, orig_idx, side, net_R, risk_frac)
        active_heap: list[tuple[int, int, str, int, int, float | None, float]] = []
        # Pending buffer for trades without exit_ts (released strictly when next t_entry > prev entry_ts)
        no_exit_pending: list[tuple[int, str, float | None, float]] = []
        open_by_side: dict[int, int] = {-1: 0, 1: 0}
        eng_recent_r: dict[str, deque[float]] = {}
        eq = 1.0
        peak_eq = 1.0

        def _commit_closed_trade(eng_k: str, nr: float | None, rf: float) -> None:
            nonlocal eq, peak_eq
            if nr is None:
                return
            dq = eng_recent_r.get(eng_k)
            if dq is None:
                dq = deque(maxlen=10)
                eng_recent_r[eng_k] = dq
            dq.append(nr)
            step_ret = max(-0.999999, nr * rf)
            eq *= 1.0 + step_ret
            if eq > peak_eq:
                peak_eq = eq

        for pos in order:
            tr = trades[pos]
            t_entry = int(tr["entry_ts"])
            sym = tr["symbol"]
            side = int(tr["side"])
            eng_key = str(tr["engine_key"])

            # 1. Close all trades whose exit_ts <= t_entry (strictly realized before entry!)
            while active_heap and active_heap[0][0] <= t_entry:
                _ex, _en, c_eng, _oidx, c_side, c_nr, c_rf = heapq.heappop(active_heap)
                open_by_side[c_side] = max(0, open_by_side[c_side] - 1)
                _commit_closed_trade(c_eng, c_nr, c_rf)

            # Release trades without exit_ts whose entry_ts < t_entry
            if no_exit_pending:
                still_same_ts: list[tuple[int, str, float | None, float]] = []
                for p_en, p_eng, p_nr, p_rf in no_exit_pending:
                    if p_en < t_entry:
                        _commit_closed_trade(p_eng, p_nr, p_rf)
                    else:
                        still_same_ts.append((p_en, p_eng, p_nr, p_rf))
                no_exit_pending = still_same_ts

            # 2. Lookup strictly closed bars (close_ts <= t_entry)
            sym_bundle = prepared_by_sym[sym]
            d1 = sym_bundle["d1"]
            ind = sym_bundle["d1_indicators"]
            intra = sym_bundle["intraday"]

            k = int(np.searchsorted(d1["close_times_sec"], t_entry, side="right")) - 1
            p = int(np.searchsorted(intra["close_times_sec"], t_entry, side="right")) - 1

            # Group A — Volatility & ATR Regime (6)
            if k >= 0:
                atr14_val = float(ind["atr14"][k])
                f_atr14_pct = float(ind["atr14_pct"][k])
                f_atr5_20 = float(ind["atr5_over_atr20"][k])
                f_vol_z60 = float(ind["vol_zscore_60d"][k])
                f_d1_rng_atr = float(ind["d1_range_over_atr14"][k])
                f_park10 = float(ind["parkinson_vol_10d"][k])
                f_vol_brake = float(ind["vol_brake_mult_causal"][k])
                # Group B (first 4 from D1)
                f_adx14 = float(ind["adx14_causal"][k])
                f_ema20_slope = float(ind["ema20_slope_atr"][k])
                f_dist_ema50 = float(ind["dist_ema50_atr"][k])
                f_brk_z20 = float(ind["breakout_zscore_20"][k])
            else:
                atr14_val = 0.0
                f_atr14_pct = 0.0
                f_atr5_20 = 1.0
                f_vol_z60 = 0.0
                f_d1_rng_atr = 1.0
                f_park10 = 0.0
                f_vol_brake = 1.0
                f_adx14 = 20.0
                f_ema20_slope = 0.0
                f_dist_ema50 = 0.0
                f_brk_z20 = 0.0

            # Group B (last 2) & Group C (first 2) from most recent strictly closed bar p
            if p >= 0:
                po = float(intra["open"][p])
                ph = float(intra["high"][p])
                pl = float(intra["low"][p])
                pc = float(intra["close"][p])
                prng = ph - pl
                if prng > _EPS:
                    f_prev_body = max(-1.0, min(1.0, (pc - po) / prng))
                    f_prev_cloc = max(0.0, min(1.0, (pc - pl) / prng))
                else:
                    f_prev_body = 0.0
                    f_prev_cloc = 0.5

                sp_arr = intra["spread"]
                sp_p = float(sp_arr[p])
                if atr14_val > _EPS:
                    f_sp_atr = max(0.0, min(5.0, sp_p / atr14_val))
                else:
                    f_sp_atr = 0.0

                sp_start = max(0, p - 19)
                sp_cnt = p - sp_start + 1
                if sp_cnt >= 3:
                    sp_win = sp_arr[sp_start : p + 1]
                    sp_sd = float(np.std(sp_win, ddof=1))
                    if sp_sd > _EPS:
                        f_sp_z20 = max(-10.0, min(10.0, (sp_p - float(np.mean(sp_win))) / sp_sd))
                    else:
                        f_sp_z20 = 0.0
                else:
                    f_sp_z20 = 0.0
            else:
                f_prev_body = 0.0
                f_prev_cloc = 0.5
                f_sp_atr = 0.0
                f_sp_z20 = 0.0

            # Group C (last 4) — Pure UTC Session & Clock Encodings (zero tzdata dependency)
            sec_of_day = t_entry % 86400
            angle_h = _TWO_PI * (float(sec_of_day) / 86400.0)
            f_hour_sin = math.sin(angle_h)
            f_hour_cos = math.cos(angle_h)
            utc_dt = datetime.fromtimestamp(t_entry, UTC)
            f_dow_sin = math.sin(_TWO_PI * (float(utc_dt.weekday()) / 7.0))
            f_overlap = 1.0 if 12 <= utc_dt.hour < 17 else 0.0

            # Group D — Portfolio State & Engine Context (6)
            f_eng_code = float(tr["engine_id_code"])
            eff_ac = tr["asset_class"] if tr["asset_class"] is not None else sym_bundle["asset_class"]
            f_ac_code = encode_asset_class(sym, eff_ac)
            f_same_dir = float(min(100, open_by_side[side]))

            dq_eng = eng_recent_r.get(eng_key)
            if dq_eng:
                wins = sum(1 for r_val in dq_eng if r_val > 0.0)
                f_rec10_wr = float(wins) / float(len(dq_eng))
                f_rec10_avgr = max(-10.0, min(10.0, float(sum(dq_eng)) / float(len(dq_eng))))
            else:
                f_rec10_wr = 0.5
                f_rec10_avgr = 0.0

            f_dd_pct = max(0.0, min(100.0, 100.0 * max(0.0, (peak_eq - eq) / max(peak_eq, _EPS))))

            row_vals = (
                f_atr14_pct,
                f_atr5_20,
                f_vol_z60,
                f_d1_rng_atr,
                f_park10,
                f_vol_brake,
                f_adx14,
                f_ema20_slope,
                f_dist_ema50,
                f_brk_z20,
                f_prev_body,
                f_prev_cloc,
                f_sp_atr,
                f_sp_z20,
                f_hour_sin,
                f_hour_cos,
                f_dow_sin,
                f_overlap,
                f_eng_code,
                f_ac_code,
                f_same_dir,
                f_rec10_wr,
                f_rec10_avgr,
                f_dd_pct,
            )
            x_mat[tr["orig_idx"], :] = np.asarray(row_vals, dtype=np.float32)

            # 3. Register current trade into active/pending state AFTER reading its own features
            ex_ts = tr["exit_ts"]
            if ex_ts is not None:
                if ex_ts > t_entry:
                    open_by_side[side] += 1
                    heapq.heappush(
                        active_heap,
                        (ex_ts, t_entry, eng_key, tr["orig_idx"], side, tr["net_R"], tr["risk_frac"]),
                    )
                else:
                    # Zero-duration trade: never counts as concurrent for itself; realized for future trades
                    no_exit_pending.append((t_entry, eng_key, tr["net_R"], tr["risk_frac"]))
            else:
                no_exit_pending.append((t_entry, eng_key, tr["net_R"], tr["risk_frac"]))

    # Final fail-closed invariants (safe under python -O)
    if x_mat.dtype != np.float32 or x_mat.shape != (n_trades, len(FEATURE_NAMES_24)):
        raise ValueError(
            f"INVALID_OUTPUT_SHAPE_OR_DTYPE: got shape={x_mat.shape} dtype={x_mat.dtype}, "
            f"expected ({n_trades}, {len(FEATURE_NAMES_24)}) float32"
        )
    if n_trades > 0 and not bool(np.all(np.isfinite(x_mat))):
        bad_cols = [FEATURE_NAMES_24[j] for j in range(x_mat.shape[1]) if not bool(np.all(np.isfinite(x_mat[:, j])))]
        raise ValueError(f"NON_FINITE_FEATURE_OUTPUT: non-finite values in columns {bad_cols}")

    if not return_metadata:
        return x_mat

    summary: dict[str, dict[str, float]] = {}
    for j, fname in enumerate(FEATURE_NAMES_24):
        if n_trades > 0:
            col = x_mat[:, j].astype(np.float64)
            summary[fname] = {
                "min": round(float(np.min(col)), 6),
                "max": round(float(np.max(col)), 6),
                "mean": round(float(np.mean(col)), 6),
                "std": round(float(np.std(col, ddof=0)), 6),
            }
        else:
            summary[fname] = {"min": 0.0, "max": 0.0, "mean": 0.0, "std": 0.0}

    metadata = {
        "schema_version": SCHEMA_VERSION,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "cutoff_utc": str(cutoff_utc),
        "cutoff_sec_exclusive": cutoff_sec_excl,
        "holdout_rows_analysed": 0,
        "n_trades": n_trades,
        "n_features": len(FEATURE_NAMES_24),
        "dtype": str(x_mat.dtype),
        "feature_names": list(FEATURE_NAMES_24),
        "feature_summary": summary,
    }
    return x_mat, metadata


# ---------------------------------------------------------------------------
# Mandatory Future-Perturbation Mutation Gate (`W4-G04`, ZERO Bare `assert`)
# ---------------------------------------------------------------------------


def _perturb_flat_bar_container(raw_bars: Any, t_probe_sec: int, factor: float) -> tuple[Any, int]:
    """Deep-copy a flat bar dict/DataFrame and multiply prices/spreads for bars with `close_ts > t_probe_sec`."""
    is_df = hasattr(raw_bars, "columns") and hasattr(raw_bars, "copy")
    out = raw_bars.copy(deep=True) if is_df else copy.deepcopy(dict(raw_bars))

    from_dates_only = False
    ts_key = None
    for cand in ("times_sec", "timestamps", "timestamp", "ts", "time"):
        if cand in out and out[cand] is not None:
            ts_key = cand
            break
    if ts_key is not None:
        ts = _parse_timestamp_array(out[ts_key], name=f"perturb.{ts_key}")
    elif "dates" in out and out["dates"] is not None:
        ts = _parse_timestamp_array(out["dates"], name="perturb.dates")
        from_dates_only = True
    elif "date" in out and out["date"] is not None:
        ts = _parse_timestamp_array(out["date"], name="perturb.date")
        from_dates_only = True
    else:
        raise ValueError("Cannot perturb bars without timestamp/dates column")

    if "close_times_sec" in out and out["close_times_sec"] is not None:
        close_ts = _parse_timestamp_array(out["close_times_sec"], name="perturb.close_times_sec")
    else:
        if "bar_duration_sec" in out and out["bar_duration_sec"] is not None:
            bar_dur = int(out["bar_duration_sec"])
        else:
            bar_dur = _infer_bar_duration_sec(ts, from_dates_only=from_dates_only)
        close_ts = ts + np.int64(bar_dur)

    # Mutate ALL bars whose close occurs strictly after t_probe_sec (includes ALL bar_ts > t_probe_sec
    # AND any currently forming bar with bar_ts <= t_probe_sec < close_ts!).
    mask = close_ts > int(t_probe_sec)
    n_mut = int(np.sum(mask))
    if n_mut == 0:
        return out, 0

    if "quotes" in out and out["quotes"] is not None:
        q = np.array(out["quotes"], dtype=np.float64, copy=True)
        q[mask, :] = q[mask, :] * float(factor)
        out["quotes"] = q

    for col in ("open", "high", "low", "close", "spread_price", "spread", "ask_close", "bid_close"):
        if col in out and out[col] is not None:
            arr = np.array(out[col], dtype=np.float64, copy=True)
            arr[mask] = arr[mask] * float(factor)
            if is_df:
                out[col] = arr
            else:
                out[col] = arr
    return out, n_mut


def perturb_bars_after_ts(
    bars_by_symbol: Mapping[str, Any],
    t_entry_sec: int,
    *,
    factor: float = 10.0,
) -> tuple[dict[str, Any], int]:
    """Deep-copy `bars_by_symbol` and multiply all prices/spreads for bars closing `> t_entry_sec` by `factor`."""
    fv = _validate_finite_float(factor, name="factor")
    if fv <= 0.0 or abs(fv - 1.0) <= _EPS:
        raise ValueError(f"perturbation factor must be > 0 and != 1.0, got {factor!r}")
    _reject_bool_scalar(t_entry_sec, name="t_entry_sec")

    perturbed: dict[str, Any] = {}
    total_mutated = 0
    for sym, entry in bars_by_symbol.items():
        if isinstance(entry, Mapping) and ("d1" in entry or "m1" in entry or "intraday" in entry):
            new_entry = dict(entry)
            for sub_key in ("d1", "m1", "h4", "intraday"):
                if sub_key in new_entry and new_entry[sub_key] is not None:
                    sub_pert, cnt = _perturb_flat_bar_container(new_entry[sub_key], int(t_entry_sec), fv)
                    new_entry[sub_key] = sub_pert
                    total_mutated += cnt
            perturbed[sym] = new_entry
        else:
            flat_pert, cnt = _perturb_flat_bar_container(entry, int(t_entry_sec), fv)
            perturbed[sym] = flat_pert
            total_mutated += cnt
    return perturbed, total_mutated


def _perturb_future_trade_outcomes(
    trades_df: Any,
    t_probe_sec: int,
    trades_parsed: Sequence[Mapping[str, Any]],
) -> Any:
    """Mutate `net_R` for all trades not yet closed at `t_probe_sec` (future entries & still-open trades)."""
    mut_indices = {
        int(tr["orig_idx"])
        for tr in trades_parsed
        if (tr["exit_ts"] is not None and int(tr["exit_ts"]) > t_probe_sec)
        or (tr["exit_ts"] is None and int(tr["entry_ts"]) > t_probe_sec)
    }
    if not mut_indices:
        return trades_df

    r_keys = ("net_R", "net_r", "r_mult", "pnl_r", "return_r")

    if hasattr(trades_df, "copy") and hasattr(trades_df, "columns"):
        df_out = trades_df.copy(deep=True)
        for rk in r_keys:
            if rk in df_out.columns:
                vals = np.array(df_out[rk].to_numpy(copy=True), dtype=np.float64)
                for idx in mut_indices:
                    if math.isfinite(vals[idx]):
                        vals[idx] = -5.0 * vals[idx] + 3.0
                df_out[rk] = vals
        return df_out

    if isinstance(trades_df, Mapping):
        out_map = {k: list(v) for k, v in trades_df.items()}
        for rk in r_keys:
            if rk in out_map:
                for idx in mut_indices:
                    if out_map[rk][idx] is not None:
                        out_map[rk][idx] = -5.0 * float(out_map[rk][idx]) + 3.0
        return out_map

    out_list: list[dict[str, Any]] = [dict(row) for row in trades_df]
    for idx in mut_indices:
        for rk in r_keys:
            if rk in out_list[idx] and out_list[idx][rk] is not None:
                out_list[idx][rk] = -5.0 * float(out_list[idx][rk]) + 3.0
    return out_list


def _invoke_builder(
    builder_fn: Callable[..., np.ndarray],
    bars_by_symbol: Mapping[str, Any],
    trades_df: Any,
    *,
    cutoff_utc: str | date | datetime | int,
    builder_kwargs: Mapping[str, Any] | None,
) -> np.ndarray:
    kwargs = dict(builder_kwargs) if builder_kwargs else {}
    sig = inspect.signature(builder_fn)
    accepts_cutoff = "cutoff_utc" in sig.parameters or any(
        p.kind == inspect.Parameter.VAR_KEYWORD for p in sig.parameters.values()
    )
    if accepts_cutoff and "cutoff_utc" not in kwargs:
        kwargs["cutoff_utc"] = cutoff_utc
    res = builder_fn(bars_by_symbol, trades_df, **kwargs)
    if isinstance(res, tuple):
        res = res[0]
    arr = np.asarray(res)
    if arr.ndim != 2:
        raise ValueError(f"builder_fn must return a 2D feature matrix, got shape {arr.shape}")
    if arr.size > 0 and not bool(np.all(np.isfinite(arr))):
        raise ValueError("builder_fn returned non-finite feature values")
    return arr


def assert_zero_future_leakage(
    builder_fn: Callable[..., np.ndarray],
    bars_by_symbol: Mapping[str, Any],
    trades_df: Any,
    *,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    perturbation_factor: float = 10.0,
    probe_indices: Sequence[int] | None = None,
    max_probes: int = 8,
    mutate_future_trades: bool = True,
    builder_kwargs: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Fail-closed `W4-G04` future-perturbation mutation verifier (ZERO bare `assert`).

    For each probe trade `i` with entry time `t_probe`:
      1. Multiplies all prices and spreads across every symbol for bars closing `> t_probe` by
         `perturbation_factor` (default `10.0x`), AND (when `mutate_future_trades=True`) mutates
         future/unclosed trade outcomes (`net_R`).
      2. Re-runs `builder_fn` and verifies bit-for-bit equality (`np.array_equal`) for EVERY trade
         row `j` with `entry_ts[j] <= t_probe`.
      3. Fails closed with `ValueError("FUTURE_LEAKAGE_DETECTED: ...")` on any single bit drift
         or if zero bars were mutated across all probes (preventing vacuous passes).
    """
    if not callable(builder_fn):
        raise ValueError("builder_fn must be callable")
    fv = _validate_finite_float(perturbation_factor, name="perturbation_factor")
    if fv <= 0.0 or abs(fv - 1.0) <= _EPS:
        raise ValueError(f"perturbation_factor must be > 0 and != 1.0, got {perturbation_factor!r}")
    _reject_bool_scalar(max_probes, name="max_probes")
    if not isinstance(max_probes, (int, np.integer)) or int(max_probes) < 1:
        raise ValueError(f"max_probes must be >= 1, got {max_probes!r}")

    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    trades_parsed = _extract_trade_records(trades_df, cutoff_sec_exclusive=cutoff_sec_excl)
    n_trades = len(trades_parsed)
    if n_trades == 0:
        raise ValueError("VACUOUS_CAUSALITY_TEST: trades_df is empty; at least 1 trade required")

    x_orig = _invoke_builder(
        builder_fn,
        bars_by_symbol,
        trades_df,
        cutoff_utc=cutoff_utc,
        builder_kwargs=builder_kwargs,
    )
    if x_orig.shape[0] != n_trades:
        raise ValueError(f"builder_fn returned {x_orig.shape[0]} rows for {n_trades} trades")

    entry_ts_arr = np.array([int(tr["entry_ts"]) for tr in trades_parsed], dtype=np.int64)
    chron_order = np.argsort(entry_ts_arr, kind="mergesort")

    if probe_indices is not None:
        chosen: list[int] = []
        for idx in probe_indices:
            _reject_bool_scalar(idx, name="probe_indices")
            ii = int(idx)
            if ii < 0 or ii >= n_trades:
                raise ValueError(f"probe index {ii} out of range [0, {n_trades - 1}]")
            if ii not in chosen:
                chosen.append(ii)
    else:
        n_pick = min(int(max_probes), n_trades)
        if n_pick == 1:
            pos_list = [0]
        else:
            # Spread probes across chronological timeline [0 .. n_trades - 1]
            pos_list = sorted({int(round(k * (n_trades - 1) / (n_pick - 1))) for k in range(n_pick)})
        chosen = [int(chron_order[p]) for p in pos_list]

    probes_tested = 0
    total_bars_mutated = 0
    probe_details: list[dict[str, Any]] = []

    for p_idx in chosen:
        t_probe = int(entry_ts_arr[p_idx])
        bars_pert, n_mut = perturb_bars_after_ts(bars_by_symbol, t_probe, factor=fv)
        if n_mut == 0:
            # Skip only if another probe mutates bars; checked globally below so test is never vacuous
            continue
        trades_pert = (
            _perturb_future_trade_outcomes(trades_df, t_probe, trades_parsed) if mutate_future_trades else trades_df
        )
        x_pert = _invoke_builder(
            builder_fn,
            bars_pert,
            trades_pert,
            cutoff_utc=cutoff_utc,
            builder_kwargs=builder_kwargs,
        )
        if x_pert.shape != x_orig.shape or x_pert.dtype != x_orig.dtype:
            raise ValueError(
                f"FUTURE_LEAKAGE_DETECTED: shape/dtype drifted under perturbation "
                f"(orig={x_orig.shape}/{x_orig.dtype}, pert={x_pert.shape}/{x_pert.dtype})"
            )

        pre_mask = entry_ts_arr <= t_probe
        orig_slice = x_orig[pre_mask]
        pert_slice = x_pert[pre_mask]
        if not np.array_equal(orig_slice, pert_slice):
            diff_pos = np.argwhere(orig_slice != pert_slice)
            r_local, c_idx = int(diff_pos[0, 0]), int(diff_pos[0, 1])
            pre_indices = np.flatnonzero(pre_mask)
            r_global = int(pre_indices[r_local])
            fname = FEATURE_NAMES_24[c_idx] if c_idx < len(FEATURE_NAMES_24) else f"col_{c_idx}"
            raise ValueError(
                f"FUTURE_LEAKAGE_DETECTED [probe_idx={p_idx}, t_probe={t_probe}]: "
                f"{len(diff_pos)} entries drifted under {fv}x future perturbation; "
                f"first mismatch at row={r_global} feature={fname!r} "
                f"(orig={orig_slice[r_local, c_idx]!r}, pert={pert_slice[r_local, c_idx]!r})"
            )

        probes_tested += 1
        total_bars_mutated += n_mut
        probe_details.append(
            {
                "probe_row": p_idx,
                "t_probe_sec": t_probe,
                "pre_rows_checked": int(np.sum(pre_mask)),
                "bars_mutated": n_mut,
                "bit_exact": True,
            }
        )

    if probes_tested == 0 or total_bars_mutated == 0:
        raise ValueError(
            "VACUOUS_CAUSALITY_TEST: zero future bars existed after any probe trade; "
            "provide bars extending strictly past at least one trade's t_entry"
        )

    return {
        "gate": "W4-G04",
        "passed": True,
        "perturbation_factor": fv,
        "mutate_future_trades": bool(mutate_future_trades),
        "probes_tested": probes_tested,
        "total_bars_mutated": total_bars_mutated,
        "bit_exact_zero_drift": True,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "probes": probe_details,
    }


# ---------------------------------------------------------------------------
# Frozen PORT_7E / PORT_9E Tape Bridge & Receipt Exporter (Lazy Imports Only)
# ---------------------------------------------------------------------------


def extract_trades_from_frozen_tapes(
    tapes: Mapping[str, Mapping[str, Any]],
    *,
    engines: Sequence[str] | None = None,
    base_risks: Mapping[str, float] | None = None,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
) -> list[dict[str, Any]]:
    """Flatten `data_store.build_or_load_frozen_tapes()['tapes']` into standardized Dev trade rows."""
    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    selected_engines = list(engines) if engines is not None else sorted(tapes.keys())
    risk_map = dict(DEFAULT_ENGINE_BASE_RISK_PCT)
    if base_risks is not None:
        for k, v in base_risks.items():
            risk_map[str(k).upper()] = _validate_finite_float(v, name=f"base_risks[{k}]")

    records: list[dict[str, Any]] = []
    for eng in selected_engines:
        if eng not in tapes:
            raise KeyError(f"Engine {eng!r} not found in tapes")
        eng_u = str(eng).upper()
        rf_pct = risk_map.get(eng_u, 0.50)
        day_map = tapes[eng]
        for dk in sorted(day_map.keys()):
            if str(dk) >= DEV_CUTOFF_DATE:
                raise ValueError(f"HOLDOUT_TRADE_BREACH: tape {eng!r} contains day {dk!r} >= {DEV_CUTOFF_DATE!r}")
            item = day_map[dk]
            row = item[0] if isinstance(item, tuple) else item
            entry_ts = _parse_timestamp_scalar(row["entry"], name=f"{eng}.{dk}.entry")
            exit_ts = _parse_timestamp_scalar(row["exit"], name=f"{eng}.{dk}.exit")
            if entry_ts >= cutoff_sec_excl or exit_ts >= cutoff_sec_excl:
                raise ValueError(
                    f"HOLDOUT_TRADE_BREACH: tape {eng!r} day {dk!r} exceeds cutoff_sec_exclusive={cutoff_sec_excl}"
                )
            net_r = _validate_finite_float(row["net_R"], name=f"{eng}.{dk}.net_R")
            records.append(
                {
                    "day": str(dk),
                    "engine_id": eng_u,
                    "symbol": normalize_symbol(str(row["asset"])),
                    "entry_ts": entry_ts,
                    "exit_ts": exit_ts,
                    "side": _parse_side_scalar(row["side"], name=f"{eng}.{dk}.side"),
                    "net_R": net_r,
                    "y_win": 1.0 if net_r > 0.0 else 0.0,
                    "risk_pct": rf_pct,
                }
            )
    records.sort(key=lambda r: (r["entry_ts"], r["engine_id"], r["symbol"]))
    return records


def build_port7e_dev_feature_bundle(
    *,
    portfolio_key: str = "PORT_7E_P28_CORE",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    verify_sha: bool = True,
    verify_causality: bool = True,
) -> dict[str, Any]:
    """Load sealed Dev `PORT_7E` trades + M1 Bid/Ask bars (lazy imports) and build `(N, 24)` `float32` matrix."""
    # Lazy imports ONLY — never executed at module import time (safe in minimal CI!)
    from quant_factory.data_store import (
        assert_holdout_locked,
        build_or_load_frozen_tapes,
        load_registry,
    )
    from quant_factory.offensive3.x13_m1_loader import load_m1_asset

    lock_sha = assert_holdout_locked()
    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    reg = load_registry()
    base_risks = {str(e["id"]).upper(): float(e["base_risk_pct"]) for e in reg["engines"]}
    engines = list(reg["frozen_portfolios"][portfolio_key]["engines"])

    frozen = build_or_load_frozen_tapes(force_rebuild=False)
    trades = extract_trades_from_frozen_tapes(
        frozen["tapes"],
        engines=engines,
        base_risks=base_risks,
        cutoff_utc=cutoff_utc,
    )
    symbols = sorted({tr["symbol"] for tr in trades})

    bars_by_symbol: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        ts_m1, q_m1, _am = load_m1_asset(sym, verify_sha=verify_sha)
        bars_by_symbol[sym] = {
            "times_sec": ts_m1,
            "quotes": q_m1,
            "bar_duration_sec": 60,
        }

    x_mat, meta = build_causal_feature_matrix(
        bars_by_symbol,
        trades,
        cutoff_utc=cutoff_utc,
        return_metadata=True,
    )
    causality_report = (
        assert_zero_future_leakage(
            build_causal_feature_matrix,
            bars_by_symbol,
            trades,
            cutoff_utc=cutoff_utc,
            perturbation_factor=10.0,
            max_probes=5,
        )
        if verify_causality
        else None
    )

    return {
        "schema_version": SCHEMA_VERSION,
        "portfolio_key": portfolio_key,
        "holdout_lock_sha256": lock_sha,
        "cutoff_utc": cutoff_utc,
        "cutoff_sec_exclusive": cutoff_sec_excl,
        "holdout_rows_analysed": 0,
        "order_send_count": ORDER_SEND_COUNT,
        "engines": engines,
        "symbols": symbols,
        "X": x_mat,
        "y": np.array([tr["y_win"] for tr in trades], dtype=np.float32),
        "net_R": np.array([tr["net_R"] for tr in trades], dtype=np.float64),
        "entry_ts": np.array([tr["entry_ts"] for tr in trades], dtype=np.int64),
        "trades": trades,
        "metadata": meta,
        "causality_proof": causality_report,
    }


def _atomic_write_json(path: Path, payload: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
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


def build_feature_spec_receipt(
    *,
    causality_proof: Mapping[str, Any] | None = None,
    port7e_proof: Mapping[str, Any] | None = None,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Assemble structured JSON receipt for Wave 1A `w4-m1-feat` audit & swarm dropbox."""
    return {
        "schema": "naqex-wave4-m1-feat-receipt-v1",
        "feature_schema_version": SCHEMA_VERSION,
        "worker": "w4-m1-feat",
        "wave": "Wave 1A (Total Offensive #4 v4.8.1 FINAL)",
        "generated_utc": datetime.now(UTC).isoformat(),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": ORDER_SEND_COUNT,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "dev_cutoff_sec": DEV_CUTOFF_SEC,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "zero_bare_asserts": True,
            "lazy_ml_imports_only": True,
        },
        "deliverables": {
            "module": "tooling/ai-engines/quant_factory/wave4/ml_features_24.py",
            "tests": "tooling/ai-engines/tests/wave4/test_wave4_ml_features.py",
        },
        "feature_count": len(FEATURE_NAMES_24),
        "dtype": "float32",
        "feature_groups": {k: list(v) for k, v in FEATURE_GROUPS.items()},
        "feature_names_24": list(FEATURE_NAMES_24),
        "feature_specs_24": list(FEATURE_SPECS_24),
        "engine_id_codes": dict(ENGINE_ID_CODES),
        "asset_class_codes": dict(ASSET_CLASS_CODES),
        "lab6_upgrade_rationale": (
            "Lab #6 (meta_labeler.py) scored Brier Skill = -0.004 <= 0 using only 6 coarse day-level "
            "portfolio-aggregate return features with intra-day trade-outcome ordering leakage. "
            "ml_features_24 upgrades to 24 strictly causal, MQL5-replicable per-entry features across "
            "Volatility/ATR, Trend/Breakout, Microstructure/Cost/Session, and exit_ts-gated Portfolio State."
        ),
        "causality_proof": dict(causality_proof) if causality_proof is not None else None,
        "port7e_dev_proof": dict(port7e_proof) if port7e_proof is not None else None,
        "test_results": dict(test_results) if test_results is not None else None,
    }


def write_feature_spec_receipt(
    receipt_path: str | Path,
    *,
    dropbox_path: str | Path | None = None,
    causality_proof: Mapping[str, Any] | None = None,
    port7e_proof: Mapping[str, Any] | None = None,
    test_results: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Write Wave 1A schema/causality receipt atomically (LF, 0 BOM) to audit & dropbox paths."""
    payload = build_feature_spec_receipt(
        causality_proof=causality_proof,
        port7e_proof=port7e_proof,
        test_results=test_results,
    )
    _atomic_write_json(Path(receipt_path), payload)
    if dropbox_path is not None:
        _atomic_write_json(Path(dropbox_path), payload)
    return payload


__all__ = [
    "ASSET_CLASS_CODES",
    "DEFAULT_ENGINE_BASE_RISK_PCT",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "ENGINE_ID_CODES",
    "FEATURE_GROUPS",
    "FEATURE_NAMES_24",
    "FEATURE_SPECS_24",
    "HOLDOUT_CUTOFF_DATE",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "SCHEMA_VERSION",
    "assert_zero_future_leakage",
    "build_causal_feature_matrix",
    "build_feature_spec_receipt",
    "build_port7e_dev_feature_bundle",
    "encode_asset_class",
    "encode_engine_id",
    "extract_trades_from_frozen_tapes",
    "infer_asset_class",
    "normalize_symbol",
    "parse_cutoff_utc_exclusive",
    "perturb_bars_after_ts",
    "write_feature_spec_receipt",
]
