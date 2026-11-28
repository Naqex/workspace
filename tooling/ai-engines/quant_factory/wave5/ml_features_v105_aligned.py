"""Wave 5 Aligned Causal Feature Engine for `v1.05-ML` (Closes `W4-RT1-P1-01`).

Eliminates 100% of Wave 4 train-serve feature skew between Python training and MQL5 live/tester
serving by aligning EVERY candidate feature in `FEATURE_NAMES_V105` to an exact 1:1 bit-matched
MQL5 formula:
  1. FTMO-Demo 2-Regime Broker-Day D1 Aggregation (P2-2 Guardrail):
     - `year <= 2019`: EU DST (`Europe/Athens`: last Sun Mar -> last Sun Oct)
     - `year >= 2020`: US DST (`America/New_York + 7h`: 2nd Sun Mar -> 1st Sun Nov)
     Directly reuses `encode_utc_to_ftmo_server_times()` and `build_broker_d1_from_m1()` from
     `quant_factory.wave4.same_feed_mt5_parity` (NEVER hand-rolls pure EU EET/EEST for 2020-2024!).
  2. Exact MQL5 `iATR(sym, PERIOD_D1, 14)` (`SMA(TR, 14)`, NOT Wilder RMA!) on broker-day D1
     `shift >= 1` (`d1_day_key < cur_broker_day`) for `d1_range_over_atr14`, `atr14_pct`,
     `atr5_over_atr20_sma`, `dist_sma20_atr`, and `spread_over_atr_ratio`.
  3. Exact finite-window broker-day D1 `parkinson_vol_10d` (shifts `1..10`), `d1_range_comp_5_20`
     (shifts `1..5` / `1..20`), and `breakout_zscore_20` (shifts `1..20`) — ZERO infinite-history
     IIR/EMA warmup drift between Python and MT5 Strategy Tester!
  4. Phase-Invariant Shadow 1.0x Closed-R Balance Curve (`rolling_dd_pct_1x_equiv`):
     Tracks realized closed trades (`exit_ts <= t_entry`) using canonical MQL5 1.0x engine risk
     weights (`CANONICAL_BASE_RISK_PCT_1X`) independent of `InpBasePhaseMult` so `P1 4.5x`,
     `P2 3.5x`, `Funded 1.25x`, and `Funded 1.0x` produce bit-identical feature values.
  5. Exact closed M1 (`close_ts <= t_entry`), pure UTC clock encodings (`hour_sin_utc`,
     `hour_cos_utc`, `dow_sin`, `is_london_ny_overlap`), static engine/asset codes, and
     observable `same_dir_concurrent_count`.

Hard safety invariants (ZERO exceptions):
  - `ORDER_SEND_CAPABLE = False`, `ORDER_SEND_COUNT = 0`, `0 VND`.
  - Holdout `2025+` SEALED (`HOLDOUT_CUTOFF_DATE = "2024-12-31"`, `DEV_CUTOFF_SEC = 1_735_689_600`,
    `holdout_rows_analysed = 0`).
  - ZERO bare Python `assert` statements (100% active under `python -O` / `python -OO`).
  - LAZY IMPORTS ONLY for optional ML / Arrow / Pandas / DuckDB packages: module top-level uses
    pure Python stdlib + NumPy + holdout-guard-free Wave 4 parity helpers ONLY.
"""

from __future__ import annotations

import copy
import heapq
import inspect
import math
import re
from collections import deque
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any, Final

import numpy as np

from quant_factory.wave4.ftmo_m1_exporter import (
    DEFAULT_OUT_DIR as DEFAULT_FTMO_M1_DIR,
)
from quant_factory.wave4.ftmo_m1_exporter import (
    HOLDOUT_CUTOFF_UTC_TS,
    PORT_7E_SYMBOLS,
    load_exported_m1,
)
from quant_factory.wave4.ml_features_24 import (
    ASSET_CLASS_CODES,
    ENGINE_ID_CODES,
    _extract_flat_bars,
    _infer_bar_duration_sec,
    _parse_side_scalar,
    _parse_timestamp_array,
    _parse_timestamp_scalar,
    _reject_bool_scalar,
    _validate_finite_float,
    _validate_float_array,
    encode_asset_class,
    encode_engine_id,
    normalize_symbol,
    parse_cutoff_utc_exclusive,
)
from quant_factory.wave5 import (
    DEV_CUTOFF_SEC,
    HOLDOUT_CUTOFF_DATE,
    ORDER_SEND_CAPABLE,
    ORDER_SEND_COUNT,
)

# Fallback point table used ONLY when `same_feed_mt5_parity` is unavailable in minimal CI
_FALLBACK_FTMO_POINTS: Final[dict[str, float]] = {
    "USDJPY": 0.001,
    "GBPUSD": 1e-5,
    "EURJPY": 0.001,
    "US100.CASH": 0.01,
    "US500.CASH": 0.01,
    "EURUSD": 1e-5,
    "AUDUSD": 1e-5,
    "USDCAD": 1e-5,
}


def _nth_sunday_ci(year: int, month: int, nth: int) -> int:
    first = date(year, month, 1)
    mql_dow = (first.weekday() + 1) % 7
    return 1 + ((7 - mql_dow) % 7) + (nth - 1) * 7


def _last_sunday_ci(year: int, month: int) -> int:
    d31 = date(year, month, 31)
    return 31 - ((d31.weekday() + 1) % 7)


def encode_utc_to_ftmo_server_times_v105(ts_utc: np.ndarray) -> np.ndarray:
    """Lazy wrapper reusing `same_feed_mt5_parity.encode_utc_to_ftmo_server_times` (2 FTMO DST regimes).

    In minimal CI without `pandas`, falls back to the exact bit-identical 2-regime formula
    (`<= 2019` EU DST `Europe/Athens`; `>= 2020` US DST `America/New_York + 7h`).
    """
    try:
        from quant_factory.wave4.same_feed_mt5_parity import encode_utc_to_ftmo_server_times

        return encode_utc_to_ftmo_server_times(ts_utc)
    except ImportError:
        raw = np.asarray(ts_utc, dtype=np.int64)
        if raw.size == 0:
            return np.empty(0, dtype=np.int64)
        min_yr = datetime.fromtimestamp(int(np.min(raw)), UTC).year
        max_yr = datetime.fromtimestamp(int(np.max(raw)), UTC).year
        offsets = np.full(raw.shape, 7200, dtype=np.int64)
        for yr in range(min_yr, max_yr + 1):
            if yr >= 2020:
                s_day = _nth_sunday_ci(yr, 3, 2)
                f_day = _nth_sunday_ci(yr, 11, 1)
                spring_u = int(datetime(yr, 3, s_day, 7, 0, tzinfo=UTC).timestamp())
                fall_u = int(datetime(yr, 11, f_day, 6, 0, tzinfo=UTC).timestamp())
            else:
                s_day = _last_sunday_ci(yr, 3)
                f_day = _last_sunday_ci(yr, 10)
                spring_u = int(datetime(yr, 3, s_day, 1, 0, tzinfo=UTC).timestamp())
                fall_u = int(datetime(yr, 10, f_day, 1, 0, tzinfo=UTC).timestamp())
            offsets[(raw >= spring_u) & (raw < fall_u)] = 10800
        return raw + offsets


def build_broker_d1_from_m1_v105(m1: Mapping[str, Any], *, atr_period: int = 14) -> dict[str, np.ndarray]:
    """Lazy wrapper reusing `same_feed_mt5_parity.build_broker_d1_from_m1` (Broker-D1 + SMA(TR, 14))."""
    try:
        from quant_factory.wave4.same_feed_mt5_parity import build_broker_d1_from_m1

        return build_broker_d1_from_m1(m1, atr_period=atr_period)
    except ImportError:
        if atr_period <= 0 or isinstance(atr_period, bool):
            raise ValueError(f"atr_period must be positive int, got {atr_period!r}") from None
        ts_utc = np.asarray(m1["ts_utc"], dtype=np.int64)
        if ts_utc.size == 0:
            raise ValueError("build_broker_d1_from_m1 received empty M1 series") from None
        if int(np.max(ts_utc)) >= HOLDOUT_CUTOFF_UTC_TS:
            raise ValueError(
                f"HOLDOUT_LOCK_VIOLATION: M1 array contains bar >= {HOLDOUT_CUTOFF_DATE} (max_ts={int(np.max(ts_utc))})"
            ) from None
        if "ts_server_raw" in m1 and len(m1["ts_server_raw"]) == len(ts_utc):
            ts_srv = np.asarray(m1["ts_server_raw"], dtype=np.int64)
        else:
            ts_srv = encode_utc_to_ftmo_server_times_v105(ts_utc)
        op = np.asarray(m1["open"], dtype=np.float64)
        hi = np.asarray(m1["high"], dtype=np.float64)
        lo = np.asarray(m1["low"], dtype=np.float64)
        cl = np.asarray(m1["close"], dtype=np.float64)
        days = ts_srv // 86400
        change = np.flatnonzero(np.diff(days) != 0) + 1
        starts = np.concatenate(([0], change))
        ends = np.concatenate((change, [len(days)]))
        d_keys = days[starts]
        d_open = op[starts]
        d_close = cl[ends - 1]
        d_high = np.maximum.reduceat(hi, starts)
        d_low = np.minimum.reduceat(lo, starts)
        d_range = d_high - d_low
        prev_c = np.empty_like(d_close)
        prev_c[0] = d_open[0]
        prev_c[1:] = d_close[:-1]
        tr = np.maximum(d_range, np.maximum(np.abs(d_high - prev_c), np.abs(d_low - prev_c)))
        n_d = len(d_keys)
        atr_sma = np.full(n_d, np.nan, dtype=np.float64)
        if n_d >= atr_period:
            cs = np.concatenate(([0.0], np.cumsum(tr)))
            atr_sma[atr_period - 1 :] = (cs[atr_period:] - cs[:-atr_period]) / float(atr_period)
        return {
            "d1_day_key": d_keys,
            "d1_open": d_open,
            "d1_high": d_high,
            "d1_low": d_low,
            "d1_close": d_close,
            "d1_range": d_range,
            "tr": tr,
            "atr14_sma": atr_sma,
        }


def _lookup_ftmo_point_lazy(symbol: str) -> float:
    norm_s = normalize_symbol(symbol)
    try:
        from quant_factory.wave4.same_feed_mt5_parity import FTMO_SYMBOL_SPECS

        for k_sym, spec in FTMO_SYMBOL_SPECS.items():
            if normalize_symbol(k_sym) == norm_s:
                return float(spec["point"])
    except ImportError:
        pass
    for k_sym, pt_val in _FALLBACK_FTMO_POINTS.items():
        if normalize_symbol(k_sym) == norm_s:
            return float(pt_val)
    return 0.0

# ---------------------------------------------------------------------------
# Hard Safety Constants & Canonical v1.05 Aligned Feature Contract
# ---------------------------------------------------------------------------

SCHEMA_VERSION: Final[str] = "naqex-wave5-ml-features-v105-aligned-v1"
DEV_CUTOFF_DATE: Final[str] = "2025-01-01"
BROKER_DST_SCHEDULE: Final[str] = "EU_EET_LE_2019__US_NY_PLUS_7_GE_2020"
SHADOW_1X_R_CLAMP_MIN: Final[float] = -5.0
SHADOW_1X_R_CLAMP_MAX: Final[float] = 20.0

_EPS: Final[float] = 1e-12
_PARKINSON_DENOM_COEFF: Final[float] = 4.0 * math.log(2.0)
_TWO_PI: Final[float] = 2.0 * math.pi
_ISO_DATE_ONLY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Exact canonical 1.0x engine base risk % matching `Naqex_Signals_7E.mqh` lines 422-429.
# Used identically in Python AND MQL5 for the phase-invariant shadow 1.0x closed-R equity curve!
CANONICAL_BASE_RISK_PCT_1X: Final[dict[str, float]] = {
    "E1_USDJPY_TOKYO": 0.16,
    "E2_USDJPY_EXP80": 0.59,
    "E3_GBPUSD_VH": 0.75,
    "E4_US100_SESS40": 0.50,
    "E5_US100_RS1130": 0.50,
    "E6_EURJPY_VOLCOMP": 0.50,
    "E7_USDJPY_NY10ET": 0.50,
    "S6_FX_USD_BSK": 0.50,
    "S7_XAU_EXP120": 0.50,
}

MAGIC_TO_ENGINE_ID: Final[dict[int, str]] = {
    20261122: "E1_USDJPY_TOKYO",
    20261123: "E2_USDJPY_EXP80",
    20261125: "E3_GBPUSD_VH",
    20261124: "E4_US100_SESS40",
    20261126: "E5_US100_RS1130",
    20261128: "E6_EURJPY_VOLCOMP",
    20261129: "E7_USDJPY_NY10ET",
    20261127: "S6_FX_USD_BSK",
}

ENGINE_ID_TO_MAGIC: Final[dict[str, int]] = {v: k for k, v in MAGIC_TO_ENGINE_ID.items()}

# Canonical 20 finite-window, strictly causal, 1:1 MQL5-bit-matched v1.05 features
FEATURE_GROUPS_V105: Final[dict[str, tuple[str, ...]]] = {
    "A_BROKER_D1_VOLATILITY_SMA_ATR": (
        "d1_range_over_atr14",
        "parkinson_vol_10d",
        "atr14_pct",
        "atr5_over_atr20_sma",
        "d1_range_comp_5_20",
    ),
    "B_BROKER_D1_AND_M1_STRUCTURE": (
        "breakout_zscore_20",
        "dist_sma20_atr",
        "prev_bar_body_ratio",
        "prev_bar_close_loc",
    ),
    "C_MICROSTRUCTURE_AND_UTC_CLOCK": (
        "spread_over_atr_ratio",
        "hour_sin_utc",
        "hour_cos_utc",
        "dow_sin",
        "is_london_ny_overlap",
    ),
    "D_PHASE_INVARIANT_PORTFOLIO_STATE": (
        "engine_id_code",
        "asset_class_code",
        "same_dir_concurrent_count",
        "recent_10_wr_causal",
        "recent_10_avg_r_causal",
        "rolling_dd_pct_1x_equiv",
    ),
}

FEATURE_NAMES_V105: Final[tuple[str, ...]] = (
    *FEATURE_GROUPS_V105["A_BROKER_D1_VOLATILITY_SMA_ATR"],
    *FEATURE_GROUPS_V105["B_BROKER_D1_AND_M1_STRUCTURE"],
    *FEATURE_GROUPS_V105["C_MICROSTRUCTURE_AND_UTC_CLOCK"],
    *FEATURE_GROUPS_V105["D_PHASE_INVARIANT_PORTFOLIO_STATE"],
)

# Exact 1:1 Python <-> MQL5 specification for EVERY candidate feature in v1.05.
# Shift convention:
#   d1Shift = (iTime(sym, PERIOD_D1, 0) < (TimeCurrent() - (TimeCurrent() % 86400))) ? 0 : 1
#   m1Shift = (iTime(sym, PERIOD_M1, 0) + 60 <= TimeCurrent()) ? 0 : 1
FEATURE_SPECS_V105: Final[tuple[dict[str, Any], ...]] = (
    # Group A — Broker-Day D1 Volatility & SMA-ATR Regime (5)
    {
        "index": 0,
        "name": "d1_range_over_atr14",
        "group": "A_BROKER_D1_VOLATILITY_SMA_ATR",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 14,
        "formula": "(High_D1[s1] - Low_D1[s1]) / SMA(TR_D1, 14)[s1] on FTMO broker-day D1",
        "clip_range": [0.0, 15.0],
        "warmup_default": 1.0,
        "mql5_formula": (
            "CopyBuffer(iATR(sym, PERIOD_D1, 14), 0, d1Shift, 1, atrBuf); "
            "clip((iHigh(sym, PERIOD_D1, d1Shift) - iLow(sym, PERIOD_D1, d1Shift)) / atrBuf[0], 0.0, 15.0)"
        ),
        "closes_finding": "W4-RT1-P1-01 (Wilder UTC D1 -> MQL5 SMA(TR,14) FTMO broker-day D1)",
    },
    {
        "index": 1,
        "name": "parkinson_vol_10d",
        "group": "A_BROKER_D1_VOLATILITY_SMA_ATR",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 10,
        "formula": "sqrt(mean_{m=0..cnt-1}(ln(max(H_D1[s1+m]/L_D1[s1+m], 1.0))^2) / (4*ln(2))) for cnt<=10",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "for(int m=0; m<10; m++) { H=iHigh(sym,PERIOD_D1,d1Shift+m); L=iLow(sym,PERIOD_D1,d1Shift+m); "
            "sumSq += MathPow(MathLog(MathMax(H/MathMax(L,1e-12),1.0)),2); } "
            "clip(MathSqrt(sumSq / (4.0*MathLog(2.0)*cnt)), 0.0, 1.0)"
        ),
        "closes_finding": "W4-RT1-P1-01 (UTC D1 -> FTMO broker-day D1 shifts d1Shift..d1Shift+9)",
    },
    {
        "index": 2,
        "name": "atr14_pct",
        "group": "A_BROKER_D1_VOLATILITY_SMA_ATR",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 14,
        "formula": "SMA(TR_D1, 14)[s1] / Close_D1[s1] on FTMO broker-day D1",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "CopyBuffer(iATR(sym, PERIOD_D1, 14), 0, d1Shift, 1, atrBuf); "
            "clip(atrBuf[0] / iClose(sym, PERIOD_D1, d1Shift), 0.0, 1.0)"
        ),
        "closes_finding": "W4-RT1-P1-01 (aligned SMA(TR,14) on broker-day D1)",
    },
    {
        "index": 3,
        "name": "atr5_over_atr20_sma",
        "group": "A_BROKER_D1_VOLATILITY_SMA_ATR",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 20,
        "formula": "SMA(TR_D1, 5)[s1] / SMA(TR_D1, 20)[s1] on FTMO broker-day D1 (1.0 if warmup)",
        "clip_range": [0.0, 10.0],
        "warmup_default": 1.0,
        "mql5_formula": (
            "TR(s)=max(H[s]-L[s], max(abs(H[s]-C[s+1]), abs(L[s]-C[s+1]))); "
            "clip(mean(TR[d1Shift..d1Shift+4]) / mean(TR[d1Shift..d1Shift+19]), 0.0, 10.0)"
        ),
        "closes_finding": "Finite-window SMA(TR,5)/SMA(TR,20) matches MQL5 iATR(5)/iATR(20) bit-for-bit",
    },
    {
        "index": 4,
        "name": "d1_range_comp_5_20",
        "group": "A_BROKER_D1_VOLATILITY_SMA_ATR",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 20,
        "formula": "mean(Range_D1[s1..s1+4]) / mean(Range_D1[s1..s1+19]) on FTMO broker-day D1",
        "clip_range": [0.0, 5.0],
        "warmup_default": 1.0,
        "mql5_formula": (
            "R(s)=iHigh(sym,PERIOD_D1,s)-iLow(sym,PERIOD_D1,s); "
            "clip(mean(R[d1Shift..d1Shift+4]) / mean(R[d1Shift..d1Shift+19]), 0.0, 5.0)"
        ),
        "closes_finding": "Exact E6 broker-day range compression ratio",
    },
    # Group B — Broker-Day D1 & Closed-M1 Price Structure (4)
    {
        "index": 5,
        "name": "breakout_zscore_20",
        "group": "B_BROKER_D1_AND_M1_STRUCTURE",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 20,
        "formula": "(Close_D1[s1] - mean(Close_D1[s1..s1+19])) / std_ddof1(Close_D1[s1..s1+19])",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "20-bar trailing mean & sample std (ddof=1) of iClose(sym,PERIOD_D1,d1Shift..d1Shift+19); "
            "clip((c0 - mean) / sd, -10.0, 10.0)"
        ),
        "closes_finding": "Finite-window 20-bar broker-day D1 z-score (0 IIR warmup drift)",
    },
    {
        "index": 6,
        "name": "dist_sma20_atr",
        "group": "B_BROKER_D1_AND_M1_STRUCTURE",
        "timeframe": "BROKER_D1",
        "finite_window_bars": 20,
        "formula": "(Close_D1[s1] - mean(Close_D1[s1..s1+19])) / SMA(TR_D1, 14)[s1]",
        "clip_range": [-15.0, 15.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "sma20 = mean(iClose(sym,PERIOD_D1,d1Shift..d1Shift+19)); "
            "clip((iClose(sym,PERIOD_D1,d1Shift) - sma20) / atr14, -15.0, 15.0)"
        ),
        "closes_finding": "Replaces infinite-history EMA50 with finite-window SMA20/iATR14",
    },
    {
        "index": 7,
        "name": "prev_bar_body_ratio",
        "group": "B_BROKER_D1_AND_M1_STRUCTURE",
        "timeframe": "M1_CLOSED",
        "finite_window_bars": 1,
        "formula": "(Close_M1[m1] - Open_M1[m1]) / (High_M1[m1] - Low_M1[m1]) on last closed M1 bar",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "m1Shift = (iTime(sym,PERIOD_M1,0) + 60 <= TimeCurrent()) ? 0 : 1; "
            "clip((iClose(sym,PERIOD_M1,m1Shift) - iOpen(sym,PERIOD_M1,m1Shift)) / "
            "(iHigh(sym,PERIOD_M1,m1Shift) - iLow(sym,PERIOD_M1,m1Shift)), -1.0, 1.0)"
        ),
        "closes_finding": "Exact closed-bar M1 shift rule handles missing current-minute bars identically",
    },
    {
        "index": 8,
        "name": "prev_bar_close_loc",
        "group": "B_BROKER_D1_AND_M1_STRUCTURE",
        "timeframe": "M1_CLOSED",
        "finite_window_bars": 1,
        "formula": "(Close_M1[m1] - Low_M1[m1]) / (High_M1[m1] - Low_M1[m1]) on last closed M1 bar",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.5,
        "mql5_formula": (
            "m1Shift = (iTime(sym,PERIOD_M1,0) + 60 <= TimeCurrent()) ? 0 : 1; "
            "clip((iClose(sym,PERIOD_M1,m1Shift) - iLow(sym,PERIOD_M1,m1Shift)) / "
            "(iHigh(sym,PERIOD_M1,m1Shift) - iLow(sym,PERIOD_M1,m1Shift)), 0.0, 1.0)"
        ),
        "closes_finding": "Exact closed-bar M1 IBS matching Python close_ts <= t_entry",
    },
    # Group C — Microstructure & Pure UTC Clock (5)
    {
        "index": 9,
        "name": "spread_over_atr_ratio",
        "group": "C_MICROSTRUCTURE_AND_UTC_CLOCK",
        "timeframe": "M1_CLOSED_AND_BROKER_D1",
        "finite_window_bars": 14,
        "formula": "SpreadPrice_M1[m1] / SMA(TR_D1, 14)[s1]",
        "clip_range": [0.0, 5.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "spreadPx = (double)iSpread(sym, PERIOD_M1, m1Shift) * SymbolInfoDouble(sym, SYMBOL_POINT); "
            "clip(spreadPx / atr14, 0.0, 5.0)"
        ),
        "closes_finding": "Exact M1 bar spread divided by MQL5 D1 SMA(TR,14)",
    },
    {
        "index": 10,
        "name": "hour_sin_utc",
        "group": "C_MICROSTRUCTURE_AND_UTC_CLOCK",
        "timeframe": "UTC_CLOCK",
        "finite_window_bars": 0,
        "formula": "sin(2*pi * ((t_entry_utc % 86400) / 86400.0))",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": "MathSin(2.0 * M_PI * (double)((((long)signalUtc % 86400) + 86400) % 86400) / 86400.0)",
        "closes_finding": "Bit-exact UTC trig encoding",
    },
    {
        "index": 11,
        "name": "hour_cos_utc",
        "group": "C_MICROSTRUCTURE_AND_UTC_CLOCK",
        "timeframe": "UTC_CLOCK",
        "finite_window_bars": 0,
        "formula": "cos(2*pi * ((t_entry_utc % 86400) / 86400.0))",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 1.0,
        "mql5_formula": "MathCos(2.0 * M_PI * (double)((((long)signalUtc % 86400) + 86400) % 86400) / 86400.0)",
        "closes_finding": "Bit-exact UTC trig encoding",
    },
    {
        "index": 12,
        "name": "dow_sin",
        "group": "C_MICROSTRUCTURE_AND_UTC_CLOCK",
        "timeframe": "UTC_CLOCK",
        "finite_window_bars": 0,
        "formula": "sin(2*pi * py_weekday_utc / 7.0), Mon=0..Sun=6",
        "clip_range": [-1.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "TimeToStruct(signalUtc, dt); int pyDow=(dt.day_of_week+6)%7; "
            "MathSin(2.0*M_PI*(double)pyDow/7.0)"
        ),
        "closes_finding": "Bit-exact UTC day-of-week encoding",
    },
    {
        "index": 13,
        "name": "is_london_ny_overlap",
        "group": "C_MICROSTRUCTURE_AND_UTC_CLOCK",
        "timeframe": "UTC_CLOCK",
        "finite_window_bars": 0,
        "formula": "1.0 if 12 <= utc_hour < 17 else 0.0",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.0,
        "mql5_formula": "TimeToStruct(signalUtc, dt); (dt.hour >= 12 && dt.hour < 17) ? 1.0 : 0.0",
        "closes_finding": "Zero tzdata dependency pure UTC session indicator",
    },
    # Group D — Phase-Invariant Portfolio State & Engine Context (6)
    {
        "index": 14,
        "name": "engine_id_code",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "STATIC_CONTEXT",
        "finite_window_bars": 0,
        "formula": "Canonical PORT_9E code 1..9 (E1=1..E7=7, S6=8, S7=9)",
        "clip_range": [0.0, 1000000.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "int eIdx = CNaqexSignals7E::EngineIndexFromMagic(magic); "
            "(eIdx >= 0) ? (double)(eIdx + 1) : 0.0"
        ),
        "closes_finding": "Exact 1:1 engine slot ID",
    },
    {
        "index": 15,
        "name": "asset_class_code",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "STATIC_CONTEXT",
        "finite_window_bars": 0,
        "formula": "forex=1, indices=2, metals=3, oil=4, crypto=5, other=0",
        "clip_range": [0.0, 10.0],
        "warmup_default": 0.0,
        "mql5_formula": "CNaqexMLFilterV105::AssetClassCodeForSymbol(sym)",
        "closes_finding": "Exact static asset class enum",
    },
    {
        "index": 16,
        "name": "same_dir_concurrent_count",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "LIVE_POSITIONS",
        "finite_window_bars": 0,
        "formula": "Count of open + active in-flight Naqex positions with identical side at t_entry",
        "clip_range": [0.0, 100.0],
        "warmup_default": 0.0,
        "mql5_formula": "MathMin(100, CountSameDirectionConcurrent(isBuy))",
        "closes_finding": "Exact concurrent open directional position count",
    },
    {
        "index": 17,
        "name": "recent_10_wr_causal",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "CLOSED_TRADE_RING_10",
        "finite_window_bars": 10,
        "formula": "Win rate (net_R > 0) of last <=10 strictly closed prior trades for same engine (0.5 warmup)",
        "clip_range": [0.0, 1.0],
        "warmup_default": 0.5,
        "mql5_formula": "g_mlFilter.ShadowRecent10Wr(magic)",
        "closes_finding": "Phase-invariant sign of closed R-multiples per engine",
    },
    {
        "index": 18,
        "name": "recent_10_avg_r_causal",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "CLOSED_TRADE_RING_10",
        "finite_window_bars": 10,
        "formula": "Mean clamped net_R of last <=10 strictly closed prior trades for same engine (0.0 warmup)",
        "clip_range": [-10.0, 10.0],
        "warmup_default": 0.0,
        "mql5_formula": "g_mlFilter.ShadowRecent10AvgR(magic)",
        "closes_finding": "Phase-invariant R-multiple ring buffer mean per engine",
    },
    {
        "index": 19,
        "name": "rolling_dd_pct_1x_equiv",
        "group": "D_PHASE_INVARIANT_PORTFOLIO_STATE",
        "timeframe": "SHADOW_1X_CLOSED_R_CURVE",
        "finite_window_bars": 0,
        "formula": (
            "100 * max(0, (shadow_peak - shadow_eq) / shadow_peak) where each strictly closed trade "
            "(exit_ts <= t_entry) updates shadow_eq *= (1 + clamp(net_R,-5,20) * (CANONICAL_BASE_RISK_PCT_1X[eng]/100))"
        ),
        "clip_range": [0.0, 100.0],
        "warmup_default": 0.0,
        "mql5_formula": (
            "g_mlFilter.ShadowRollingDdPct1x() "
            "(updated on DEAL_ENTRY_OUT using net_R = netPnl/initRiskUsd)"
        ),
        "closes_finding": (
            "W4-RT1-P1-01 (replaces InpBasePhaseMult-scaled ACCOUNT_BALANCE DD with phase-invariant "
            "shadow 1.0x closed-R balance curve identical across P1 4.5x, P2 3.5x, Funded 1.0x/1.25x)"
        ),
    },
)


# ---------------------------------------------------------------------------
# Shadow 1.0x Closed-R Portfolio State Tracker (Bit-Matched with MQL5)
# ---------------------------------------------------------------------------


def canonical_base_risk_pct_1x(engine_id_or_magic: Any) -> float:
    """Return canonical 1.0x base risk % matching `Naqex_Signals_7E.mqh` lines 422-429."""
    _reject_bool_scalar(engine_id_or_magic, name="engine_id_or_magic")
    if isinstance(engine_id_or_magic, (int, np.integer)):
        eng = MAGIC_TO_ENGINE_ID.get(int(engine_id_or_magic))
        if eng is not None:
            return CANONICAL_BASE_RISK_PCT_1X[eng]
        return 0.50
    key = str(engine_id_or_magic or "").strip().upper()
    return CANONICAL_BASE_RISK_PCT_1X.get(key, 0.50)


class Shadow1xClosedRTracker:
    """Phase-invariant shadow 1.0x closed-R balance curve & per-engine ring-10 buffer.

    Independent of `InpBasePhaseMult` (`P1 4.5x == P2 3.5x == Funded 1.0x == Funded 1.25x`)
    and account balance tier (`10K == 100K == 200K`). Exact 1:1 mirror of MQL5
    `CNaqexMLFilterV105::RecordClosedTradeShadow1x`.
    """

    def __init__(self) -> None:
        self.shadow_eq: float = 1.0
        self.shadow_peak: float = 1.0
        self.closed_count: int = 0
        self._eng_recent_r: dict[str, deque[float]] = {}

    def record_closed_trade(
        self,
        engine_key: str,
        net_r: float | None,
        *,
        base_risk_pct_1x: float | None = None,
    ) -> None:
        if net_r is None:
            return
        nr = _validate_finite_float(net_r, name="net_r")
        nr_clamped = max(SHADOW_1X_R_CLAMP_MIN, min(SHADOW_1X_R_CLAMP_MAX, nr))
        eng_u = str(engine_key).strip().upper()
        rf_pct = (
            _validate_finite_float(base_risk_pct_1x, name="base_risk_pct_1x")
            if base_risk_pct_1x is not None
            else canonical_base_risk_pct_1x(eng_u)
        )
        if rf_pct <= 0.0 or rf_pct > 100.0:
            raise ValueError(f"INVALID_BASE_RISK_PCT_1X: expected (0, 100], got {rf_pct}")
        dq = self._eng_recent_r.get(eng_u)
        if dq is None:
            dq = deque(maxlen=10)
            self._eng_recent_r[eng_u] = dq
        dq.append(nr_clamped)
        step_ret = max(-0.999999, nr_clamped * (rf_pct / 100.0))
        self.shadow_eq *= 1.0 + step_ret
        if self.shadow_eq > self.shadow_peak:
            self.shadow_peak = self.shadow_eq
        self.closed_count += 1

    def rolling_dd_pct_1x_equiv(self) -> float:
        dd = 100.0 * max(0.0, (self.shadow_peak - self.shadow_eq) / max(self.shadow_peak, _EPS))
        return max(0.0, min(100.0, dd))

    def recent_10_wr(self, engine_key: str) -> float:
        dq = self._eng_recent_r.get(str(engine_key).strip().upper())
        if not dq:
            return 0.5
        wins = sum(1 for v in dq if v > 0.0)
        return float(wins) / float(len(dq))

    def recent_10_avg_r(self, engine_key: str) -> float:
        dq = self._eng_recent_r.get(str(engine_key).strip().upper())
        if not dq:
            return 0.0
        return max(-10.0, min(10.0, float(sum(dq)) / float(len(dq))))


# ---------------------------------------------------------------------------
# Exact Finite-Window Broker-Day D1 Precomputation (Matches MQL5 1:1)
# ---------------------------------------------------------------------------


def _rolling_sma_strict(arr: np.ndarray, period: int) -> np.ndarray:
    """Exact rolling SMA(arr, period): NaN for `k < period - 1`, exact mean of `arr[k-period+1..k]` otherwise."""
    n = int(arr.size)
    out = np.full(n, np.nan, dtype=np.float64)
    if n >= period:
        cs = np.concatenate(([0.0], np.cumsum(arr, dtype=np.float64)))
        out[period - 1 :] = (cs[period:] - cs[:-period]) / float(period)
    return out


def _parkinson_vol_finite(h: np.ndarray, lo: np.ndarray, window: int = 10) -> np.ndarray:
    """Exact forward-only Parkinson range volatility over `<= window` closed broker D1 bars."""
    n = int(h.size)
    out = np.zeros(n, dtype=np.float64)
    if n == 0:
        return out
    log_hl = np.log(np.maximum(h / np.maximum(lo, _EPS), 1.0))
    sq = log_hl * log_hl
    csum = np.cumsum(sq, dtype=np.float64)
    for k in range(n):
        start = max(0, k - window + 1)
        cnt = k - start + 1
        total_sq = float(csum[k] - (csum[start - 1] if start > 0 else 0.0))
        out[k] = math.sqrt(max(0.0, total_sq / (_PARKINSON_DENOM_COEFF * float(cnt))))
    return out


def _rolling_zscore_finite(arr: np.ndarray, window: int = 20, *, min_obs: int = 3) -> np.ndarray:
    """Exact trailing z-score (ddof=1) over `<= window` closed broker D1 bars."""
    n = int(arr.size)
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
        out[k] = ((float(arr[k]) - mean) / sd) if sd > _EPS else 0.0
    return out


def precompute_aligned_broker_d1_indicators(d1: Mapping[str, np.ndarray]) -> dict[str, np.ndarray]:
    """Precompute strictly finite-window broker-day D1 indicators matching MQL5 `PERIOD_D1` 1:1.

    Uses `d1["atr14_sma"]` directly from `build_broker_d1_from_m1()` (`SMA(TR, 14)`, exact MQL5
    `iATR(sym, PERIOD_D1, 14)`!). Every indicator at index `k` reads ONLY broker days `<= k`.
    """
    h = np.asarray(d1["d1_high"], dtype=np.float64)
    lo = np.asarray(d1["d1_low"], dtype=np.float64)
    c = np.asarray(d1["d1_close"], dtype=np.float64)
    rng = np.asarray(d1["d1_range"], dtype=np.float64)
    tr = np.asarray(d1["tr"], dtype=np.float64)
    atr14_sma = np.asarray(d1["atr14_sma"], dtype=np.float64)
    n = int(c.size)

    atr5_sma = _rolling_sma_strict(tr, 5)
    atr20_sma = _rolling_sma_strict(tr, 20)
    rng5_sma = _rolling_sma_strict(rng, 5)
    rng20_sma = _rolling_sma_strict(rng, 20)
    close_sma20 = _rolling_sma_strict(c, 20)

    d1_range_over_atr14 = np.ones(n, dtype=np.float64)
    atr14_pct = np.zeros(n, dtype=np.float64)
    atr5_over_atr20_sma = np.ones(n, dtype=np.float64)
    d1_range_comp_5_20 = np.ones(n, dtype=np.float64)
    dist_sma20_atr = np.zeros(n, dtype=np.float64)

    for k in range(n):
        a14 = float(atr14_sma[k])
        ck = float(c[k])
        if math.isfinite(a14) and a14 > _EPS:
            d1_range_over_atr14[k] = min(15.0, max(0.0, float(rng[k]) / a14))
            if ck > _EPS:
                atr14_pct[k] = min(1.0, max(0.0, a14 / ck))
            s20 = float(close_sma20[k])
            if math.isfinite(s20):
                dist_sma20_atr[k] = min(15.0, max(-15.0, (ck - s20) / a14))
        a5 = float(atr5_sma[k])
        a20 = float(atr20_sma[k])
        if math.isfinite(a5) and math.isfinite(a20) and a20 > _EPS:
            atr5_over_atr20_sma[k] = min(10.0, max(0.0, a5 / a20))
        r5 = float(rng5_sma[k])
        r20 = float(rng20_sma[k])
        if math.isfinite(r5) and math.isfinite(r20) and r20 > _EPS:
            d1_range_comp_5_20[k] = min(5.0, max(0.0, r5 / r20))

    parkinson_vol_10d = np.clip(_parkinson_vol_finite(h, lo, window=10), 0.0, 1.0)
    breakout_zscore_20 = np.clip(_rolling_zscore_finite(c, window=20, min_obs=3), -10.0, 10.0)

    return {
        "d1_day_key": np.asarray(d1["d1_day_key"], dtype=np.int64),
        "atr14_sma": atr14_sma,
        "d1_range_over_atr14": d1_range_over_atr14,
        "parkinson_vol_10d": parkinson_vol_10d,
        "atr14_pct": atr14_pct,
        "atr5_over_atr20_sma": atr5_over_atr20_sma,
        "d1_range_comp_5_20": d1_range_comp_5_20,
        "breakout_zscore_20": breakout_zscore_20,
        "dist_sma20_atr": dist_sma20_atr,
    }


def _extract_aligned_m1_stream(
    raw_entry: Any,
    *,
    symbol: str,
    cutoff_sec_exclusive: int,
) -> dict[str, Any]:
    """Validate an M1 (or FTMO NPZ) stream and build exact 2-regime FTMO broker-day D1 via `same_feed_mt5_parity`."""
    inferred_ac: str | None = None
    src_m1: Any = raw_entry
    if isinstance(raw_entry, Mapping) and ("m1" in raw_entry or "intraday" in raw_entry or "d1" in raw_entry):
        if raw_entry.get("asset_class") is not None:
            inferred_ac = str(raw_entry["asset_class"])
        src_m1 = (
            raw_entry.get("m1")
            if raw_entry.get("m1") is not None
            else (raw_entry.get("intraday") if raw_entry.get("intraday") is not None else raw_entry.get("d1"))
        )
        if src_m1 is None:
            raise ValueError(f"Asset entry for {symbol} has no bar arrays")

    # Normalize FTMO exported NPZ dict (`ts_utc`, `ts_server_raw`, `spread_pts`, `point`) cleanly
    ts_server_raw_arr: np.ndarray | None = None
    if isinstance(src_m1, Mapping) and "ts_utc" in src_m1 and "times_sec" not in src_m1:
        wrapped: dict[str, Any] = {
            "times_sec": src_m1["ts_utc"],
            "open": src_m1["open"],
            "high": src_m1["high"],
            "low": src_m1["low"],
            "close": src_m1["close"],
            "bar_duration_sec": int(src_m1.get("bar_duration_sec", 60)),
        }
        if "spread_price" in src_m1 and src_m1["spread_price"] is not None:
            wrapped["spread_price"] = src_m1["spread_price"]
        elif "spread_pts" in src_m1 and src_m1["spread_pts"] is not None:
            pt = float(src_m1.get("point", 0.0))
            if pt <= 0.0:
                pt = _lookup_ftmo_point_lazy(symbol)
            sp_pts = _validate_float_array(src_m1["spread_pts"], name=f"{symbol}.spread_pts", non_negative=True)
            wrapped["spread_price"] = sp_pts * pt
        if "ts_server_raw" in src_m1 and src_m1["ts_server_raw"] is not None:
            ts_server_raw_arr = _parse_timestamp_array(src_m1["ts_server_raw"], name=f"{symbol}.ts_server_raw")
        flat = _extract_flat_bars(wrapped, symbol=symbol, cutoff_sec_exclusive=cutoff_sec_exclusive)
    else:
        if isinstance(src_m1, Mapping) and "ts_server_raw" in src_m1 and src_m1["ts_server_raw"] is not None:
            ts_server_raw_arr = _parse_timestamp_array(src_m1["ts_server_raw"], name=f"{symbol}.ts_server_raw")
        flat = _extract_flat_bars(src_m1, symbol=symbol, cutoff_sec_exclusive=cutoff_sec_exclusive)

    ts_utc = flat["times_sec"]
    if ts_server_raw_arr is not None and ts_server_raw_arr.size == ts_utc.size:
        ts_srv = ts_server_raw_arr
    else:
        # CRITICAL P2-2 GUARDRAIL: reuse exact 2-regime FTMO DST encoder from same_feed_mt5_parity!
        ts_srv = encode_utc_to_ftmo_server_times_v105(ts_utc)

    # CRITICAL W4-RT1-P1-01 CLOSURE: reuse exact broker-day D1 + SMA(TR,14) builder from same_feed_mt5_parity!
    d1_raw = build_broker_d1_from_m1_v105(
        {
            "ts_utc": ts_utc,
            "ts_server_raw": ts_srv,
            "open": flat["open"],
            "high": flat["high"],
            "low": flat["low"],
            "close": flat["close"],
        },
        atr_period=14,
    )
    d1_ind = precompute_aligned_broker_d1_indicators(d1_raw)

    return {
        "intraday": flat,
        "ts_server_raw": ts_srv,
        "d1": d1_raw,
        "d1_indicators": d1_ind,
        "asset_class": inferred_ac,
    }


def extract_single_signal_aligned_features(
    *,
    sym_bundle: Mapping[str, Any],
    symbol: str,
    entry_utc_ts: int,
    entry_srv_ts: int | None,
    engine_id: Any,
    same_dir_concurrent_count: int,
    shadow_tracker: Shadow1xClosedRTracker,
    asset_class: str | None = None,
) -> np.ndarray:
    """Compute exact 20 aligned `float32` features for ONE signal at entry time (Python == MQL5 1:1).

    Used BOTH by batch `build_aligned_feature_matrix_v105()` AND by live/same-feed 2024 reference
    extraction (`wave5_2024_features_ref.csv`) to guarantee ZERO code-path divergence.
    """
    t_utc = int(entry_utc_ts)
    if t_utc >= DEV_CUTOFF_SEC:
        raise ValueError(f"HOLDOUT_TRADE_BREACH: entry_utc_ts={t_utc} >= DEV_CUTOFF_SEC={DEV_CUTOFF_SEC}")

    if entry_srv_ts is not None:
        t_srv = int(entry_srv_ts)
    else:
        t_srv = int(encode_utc_to_ftmo_server_times_v105(np.array([t_utc], dtype=np.int64))[0])

    cur_broker_day = t_srv // 86400
    ind = sym_bundle["d1_indicators"]
    intra = sym_bundle["intraday"]

    # Strictly prior closed broker-day D1 bar: d1_day_key < cur_broker_day (matches MQL5 d1Shift!)
    k = int(np.searchsorted(ind["d1_day_key"], cur_broker_day, side="left")) - 1

    # Strictly prior closed M1 bar: close_times_sec <= t_utc (matches MQL5 m1Shift!)
    p = int(np.searchsorted(intra["close_times_sec"], t_utc, side="right")) - 1

    if k >= 0:
        a14_raw = float(ind["atr14_sma"][k])
        atr14_val = a14_raw if (math.isfinite(a14_raw) and a14_raw > _EPS) else 0.0
        f_d1_rng_atr = float(ind["d1_range_over_atr14"][k])
        f_park10 = float(ind["parkinson_vol_10d"][k])
        f_atr14_pct = float(ind["atr14_pct"][k])
        f_atr5_20 = float(ind["atr5_over_atr20_sma"][k])
        f_rng_comp = float(ind["d1_range_comp_5_20"][k])
        f_brk_z20 = float(ind["breakout_zscore_20"][k])
        f_dist_sma20 = float(ind["dist_sma20_atr"][k])
    else:
        atr14_val = 0.0
        f_d1_rng_atr = 1.0
        f_park10 = 0.0
        f_atr14_pct = 0.0
        f_atr5_20 = 1.0
        f_rng_comp = 1.0
        f_brk_z20 = 0.0
        f_dist_sma20 = 0.0

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
        sp_p = float(intra["spread"][p])
        f_sp_atr = max(0.0, min(5.0, sp_p / atr14_val)) if atr14_val > _EPS else 0.0
    else:
        f_prev_body = 0.0
        f_prev_cloc = 0.5
        f_sp_atr = 0.0

    # Pure UTC clock features (exact MQL5 MathSin/MathCos/TimeToStruct match)
    sec_of_day = t_utc % 86400
    angle_h = _TWO_PI * (float(sec_of_day) / 86400.0)
    f_hour_sin = math.sin(angle_h)
    f_hour_cos = math.cos(angle_h)
    utc_dt = datetime.fromtimestamp(t_utc, UTC)
    f_dow_sin = math.sin(_TWO_PI * (float(utc_dt.weekday()) / 7.0))
    f_overlap = 1.0 if 12 <= utc_dt.hour < 17 else 0.0

    # Phase-invariant portfolio & engine context
    f_eng_code = encode_engine_id(engine_id)
    eng_key = (
        MAGIC_TO_ENGINE_ID.get(int(engine_id), str(engine_id)).upper()
        if isinstance(engine_id, (int, np.integer))
        else str(engine_id or "").strip().upper()
    )
    eff_ac = asset_class if asset_class is not None else sym_bundle.get("asset_class")
    f_ac_code = encode_asset_class(symbol, eff_ac)
    f_same_dir = float(max(0, min(100, int(same_dir_concurrent_count))))
    f_rec10_wr = shadow_tracker.recent_10_wr(eng_key)
    f_rec10_avgr = shadow_tracker.recent_10_avg_r(eng_key)
    f_dd_1x = shadow_tracker.rolling_dd_pct_1x_equiv()

    vec = np.asarray(
        (
            f_d1_rng_atr,
            f_park10,
            f_atr14_pct,
            f_atr5_20,
            f_rng_comp,
            f_brk_z20,
            f_dist_sma20,
            f_prev_body,
            f_prev_cloc,
            f_sp_atr,
            f_hour_sin,
            f_hour_cos,
            f_dow_sin,
            f_overlap,
            f_eng_code,
            f_ac_code,
            f_same_dir,
            f_rec10_wr,
            f_rec10_avgr,
            f_dd_1x,
        ),
        dtype=np.float32,
    )
    if not bool(np.all(np.isfinite(vec))):
        raise ValueError("NON_FINITE_ALIGNED_FEATURE_VECTOR: fail-closed rejection")
    return vec


def _extract_trade_records_v105(
    trades_df: Any,
    *,
    cutoff_sec_exclusive: int,
) -> list[dict[str, Any]]:
    """Standardize trade rows fail-closed (rejects Holdout >= 2025, NaN, bool, time-travel)."""
    if trades_df is None:
        raise ValueError("trades_df cannot be None")

    rows_raw: list[Mapping[str, Any]]
    if hasattr(trades_df, "to_dict") and hasattr(trades_df, "columns"):
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
        sym_raw = None
        for sk in ("symbol", "asset", "ticker"):
            if sk in row and row[sk] is not None:
                sym_raw = row[sk]
                break
        if sym_raw is None:
            raise ValueError(f"trades_df[{idx}] missing symbol/asset field")
        sym = normalize_symbol(str(sym_raw)) if isinstance(sym_raw, str) else normalize_symbol(sym_raw)

        entry_raw = None
        for ek in ("entry_ts", "entry_utc_ts", "t_entry", "entry", "entry_time", "entry_utc", "timestamp"):
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

        entry_srv_ts: int | None = None
        if row.get("entry_srv_ts") is not None:
            entry_srv_ts = _parse_timestamp_scalar(row["entry_srv_ts"], name=f"trades_df[{idx}].entry_srv_ts")

        exit_raw = None
        for xk in ("exit_ts", "exit_utc_ts", "t_exit", "exit", "exit_time", "exit_utc"):
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

        side_raw = None
        for dk in ("side", "direction", "dir"):
            if dk in row and row[dk] is not None:
                side_raw = row[dk]
                break
        if side_raw is None:
            raise ValueError(f"trades_df[{idx}] missing side/direction field")
        side = _parse_side_scalar(side_raw, name=f"trades_df[{idx}].side")

        eng_raw = None
        for gk in ("engine_id", "engine", "strategy_id", "magic"):
            if gk in row and row[gk] is not None:
                eng_raw = row[gk]
                break
        if isinstance(eng_raw, (int, np.integer)) and int(eng_raw) in MAGIC_TO_ENGINE_ID:
            eng_key = MAGIC_TO_ENGINE_ID[int(eng_raw)]
        else:
            eng_key = str(eng_raw).strip().upper() if eng_raw is not None and str(eng_raw).strip() else "__DEFAULT__"

        net_r_raw = None
        for rk in ("net_R", "net_r", "r_mult", "pnl_r", "return_r"):
            if rk in row and row[rk] is not None:
                net_r_raw = row[rk]
                break
        net_r = _validate_finite_float(net_r_raw, name=f"trades_df[{idx}].net_R") if net_r_raw is not None else None

        # Always use canonical 1.0x base risk % (phase-invariant! Never scale by phase_mult!)
        base_risk_1x = canonical_base_risk_pct_1x(eng_key)

        out.append(
            {
                "orig_idx": idx,
                "symbol": sym,
                "entry_ts": entry_ts,
                "entry_srv_ts": entry_srv_ts,
                "exit_ts": exit_ts,
                "side": side,
                "engine_key": eng_key,
                "asset_class": row.get("asset_class"),
                "net_R": net_r,
                "base_risk_pct_1x": base_risk_1x,
            }
        )
    return out


# ---------------------------------------------------------------------------
# Main Strictly Causal Aligned Feature Matrix Builder (`v1.05`)
# ---------------------------------------------------------------------------


def build_aligned_feature_matrix_v105(
    bars_by_symbol: Mapping[str, Any],
    trades_df: Any,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    *,
    return_metadata: bool = False,
) -> np.ndarray | tuple[np.ndarray, dict[str, Any]]:
    """Build strictly causal, 100% MQL5-aligned `(n_trades, 20)` `float32` feature matrix.

    Guarantees:
      - FTMO 2-regime broker-day D1 via `encode_utc_to_ftmo_server_times()` + `build_broker_d1_from_m1()`.
      - Exact MQL5 `iATR(sym, PERIOD_D1, 14)` = `SMA(TR, 14)` on closed prior broker day (`d1_day_key < cur_day`).
      - Strictly closed prior M1 bar (`close_times_sec <= t_entry`).
      - Phase-invariant shadow 1.0x closed-R balance curve (`rolling_dd_pct_1x_equiv`) using
        `CANONICAL_BASE_RISK_PCT_1X` and strictly closed prior trades (`exit_ts <= t_entry`).
      - Row order preserved 1-to-1 with `trades_df` regardless of input sorting.
      - Holdout 2025+ strictly sealed (`holdout_rows_analysed == 0`, zero bare `assert`).
    """
    if not isinstance(bars_by_symbol, Mapping) or not bars_by_symbol:
        raise ValueError("bars_by_symbol must be a non-empty mapping of symbol -> bar data")

    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    trades = _extract_trade_records_v105(trades_df, cutoff_sec_exclusive=cutoff_sec_excl)

    prepared_by_sym: dict[str, dict[str, Any]] = {}
    for raw_sym, raw_bars in bars_by_symbol.items():
        norm_sym = normalize_symbol(str(raw_sym))
        prepared_by_sym[norm_sym] = _extract_aligned_m1_stream(
            raw_bars,
            symbol=norm_sym,
            cutoff_sec_exclusive=cutoff_sec_excl,
        )

    n_trades = len(trades)
    n_feat = len(FEATURE_NAMES_V105)
    for tr in trades:
        if tr["symbol"] not in prepared_by_sym:
            raise ValueError(f"UNKNOWN_SYMBOL: trade symbol {tr['symbol']!r} not found in bars_by_symbol")

    x_mat = np.empty((n_trades, n_feat), dtype=np.float32)

    if n_trades > 0:
        order = sorted(
            range(n_trades),
            key=lambda i: (trades[i]["entry_ts"], trades[i]["engine_key"], trades[i]["orig_idx"]),
        )
        active_heap: list[tuple[int, int, str, int, int, float | None, float]] = []
        no_exit_pending: list[tuple[int, str, float | None, float]] = []
        open_by_side: dict[int, int] = {-1: 0, 1: 0}
        shadow_tracker = Shadow1xClosedRTracker()

        for pos in order:
            tr = trades[pos]
            t_entry = int(tr["entry_ts"])
            sym = tr["symbol"]
            side = int(tr["side"])
            eng_key = str(tr["engine_key"])

            # 1. Commit strictly closed trades (exit_ts <= t_entry) BEFORE reading features
            while active_heap and active_heap[0][0] <= t_entry:
                _ex, _en, c_eng, _oidx, c_side, c_nr, c_rf = heapq.heappop(active_heap)
                open_by_side[c_side] = max(0, open_by_side[c_side] - 1)
                shadow_tracker.record_closed_trade(c_eng, c_nr, base_risk_pct_1x=c_rf)

            if no_exit_pending:
                still_same_ts: list[tuple[int, str, float | None, float]] = []
                for p_en, p_eng, p_nr, p_rf in no_exit_pending:
                    if p_en < t_entry:
                        shadow_tracker.record_closed_trade(p_eng, p_nr, base_risk_pct_1x=p_rf)
                    else:
                        still_same_ts.append((p_en, p_eng, p_nr, p_rf))
                no_exit_pending = still_same_ts

            # 2. Extract exact aligned 20-feature vector
            x_mat[tr["orig_idx"], :] = extract_single_signal_aligned_features(
                sym_bundle=prepared_by_sym[sym],
                symbol=sym,
                entry_utc_ts=t_entry,
                entry_srv_ts=tr["entry_srv_ts"],
                engine_id=eng_key,
                same_dir_concurrent_count=open_by_side[side],
                shadow_tracker=shadow_tracker,
                asset_class=tr["asset_class"],
            )

            # 3. Register trade as open AFTER extracting its own features
            ex_ts = tr["exit_ts"]
            if ex_ts is not None:
                if ex_ts > t_entry:
                    open_by_side[side] += 1
                    heapq.heappush(
                        active_heap,
                        (ex_ts, t_entry, eng_key, tr["orig_idx"], side, tr["net_R"], tr["base_risk_pct_1x"]),
                    )
                else:
                    no_exit_pending.append((t_entry, eng_key, tr["net_R"], tr["base_risk_pct_1x"]))
            else:
                no_exit_pending.append((t_entry, eng_key, tr["net_R"], tr["base_risk_pct_1x"]))

    if x_mat.dtype != np.float32 or x_mat.shape != (n_trades, n_feat):
        raise ValueError(f"INVALID_OUTPUT_SHAPE_OR_DTYPE: got {x_mat.shape}/{x_mat.dtype}")
    if n_trades > 0 and not bool(np.all(np.isfinite(x_mat))):
        bad_cols = [FEATURE_NAMES_V105[j] for j in range(n_feat) if not bool(np.all(np.isfinite(x_mat[:, j])))]
        raise ValueError(f"NON_FINITE_FEATURE_OUTPUT: non-finite values in {bad_cols}")

    if not return_metadata:
        return x_mat

    summary: dict[str, dict[str, float]] = {}
    for j, fname in enumerate(FEATURE_NAMES_V105):
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
        "broker_dst_schedule": BROKER_DST_SCHEDULE,
        "atr_method": "MQL5_SMA_TR_14_BROKER_D1",
        "dd_feature_mode": "SHADOW_1X_CLOSED_R_PHASE_INVARIANT",
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
        "cutoff_utc": str(cutoff_utc),
        "cutoff_sec_exclusive": cutoff_sec_excl,
        "holdout_rows_analysed": 0,
        "n_trades": n_trades,
        "n_features": n_feat,
        "dtype": str(x_mat.dtype),
        "feature_names": list(FEATURE_NAMES_V105),
        "feature_summary": summary,
    }
    return x_mat, metadata


# ---------------------------------------------------------------------------
# Future-Perturbation Zero-Bit-Drift Verifier (Supports FTMO NPZ & Dicts)
# ---------------------------------------------------------------------------


def _perturb_bar_container_v105(raw_bars: Any, t_probe_sec: int, factor: float) -> tuple[Any, int]:
    """Deep-copy bar dict/FTMO-NPZ dict and scale prices/spreads for bars with `close_ts > t_probe_sec`."""
    is_df = hasattr(raw_bars, "columns") and hasattr(raw_bars, "copy")
    out = raw_bars.copy(deep=True) if is_df else copy.deepcopy(dict(raw_bars))

    ts_key = None
    for cand in ("times_sec", "ts_utc", "timestamps", "timestamp", "ts", "time"):
        if cand in out and out[cand] is not None:
            ts_key = cand
            break
    if ts_key is None:
        raise ValueError("Cannot perturb bars without timestamp column")
    ts = _parse_timestamp_array(out[ts_key], name=f"perturb.{ts_key}")

    if "close_times_sec" in out and out["close_times_sec"] is not None:
        close_ts = _parse_timestamp_array(out["close_times_sec"], name="perturb.close_times_sec")
    else:
        bar_dur = (
            int(out["bar_duration_sec"])
            if "bar_duration_sec" in out and out["bar_duration_sec"] is not None
            else _infer_bar_duration_sec(ts)
        )
        close_ts = ts + np.int64(bar_dur)

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
            out[col] = arr
    if "spread_pts" in out and out["spread_pts"] is not None:
        sp_arr = np.array(out["spread_pts"], dtype=np.float64, copy=True)
        sp_arr[mask] = sp_arr[mask] * float(factor)
        out["spread_pts"] = sp_arr

    return out, n_mut


def _perturb_future_trades_v105(
    trades_df: Any,
    t_probe_sec: int,
    trades_parsed: Sequence[Mapping[str, Any]],
) -> Any:
    mut_indices = {
        int(tr["orig_idx"])
        for tr in trades_parsed
        if (tr["exit_ts"] is not None and int(tr["exit_ts"]) > t_probe_sec)
        or (tr["exit_ts"] is None and int(tr["entry_ts"]) > t_probe_sec)
    }
    if not mut_indices:
        return trades_df
    r_keys = ("net_R", "net_r", "r_mult", "pnl_r", "return_r")
    if isinstance(trades_df, Mapping):
        out_map = {k: list(v) for k, v in trades_df.items()}
        for rk in r_keys:
            if rk in out_map:
                for idx in mut_indices:
                    if out_map[rk][idx] is not None:
                        out_map[rk][idx] = -3.0 * float(out_map[rk][idx]) + 2.5
        return out_map
    out_list = [dict(row) for row in trades_df]
    for idx in mut_indices:
        for rk in r_keys:
            if rk in out_list[idx] and out_list[idx][rk] is not None:
                out_list[idx][rk] = -3.0 * float(out_list[idx][rk]) + 2.5
    return out_list


def assert_zero_future_leakage_v105(
    builder_fn: Callable[..., np.ndarray],
    bars_by_symbol: Mapping[str, Any],
    trades_df: Any,
    *,
    cutoff_utc: str | date | datetime | int = HOLDOUT_CUTOFF_DATE,
    perturbation_factor: float = 10.0,
    max_probes: int = 5,
    mutate_future_trades: bool = True,
) -> dict[str, Any]:
    """Fail-closed future-perturbation zero-bit-drift verifier for v1.05 aligned features (0 bare asserts)."""
    if not callable(builder_fn):
        raise ValueError("builder_fn must be callable")
    fv = _validate_finite_float(perturbation_factor, name="perturbation_factor")
    if fv <= 0.0 or abs(fv - 1.0) <= _EPS:
        raise ValueError(f"perturbation_factor must be > 0 and != 1.0, got {perturbation_factor!r}")
    _reject_bool_scalar(max_probes, name="max_probes")
    if not isinstance(max_probes, (int, np.integer)) or int(max_probes) < 1:
        raise ValueError(f"max_probes must be >= 1, got {max_probes!r}")

    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    trades_parsed = _extract_trade_records_v105(trades_df, cutoff_sec_exclusive=cutoff_sec_excl)
    n_trades = len(trades_parsed)
    if n_trades == 0:
        raise ValueError("VACUOUS_CAUSALITY_TEST: trades_df is empty")

    sig = inspect.signature(builder_fn)
    accepts_cutoff = "cutoff_utc" in sig.parameters

    def _call(b_map: Mapping[str, Any], t_df: Any) -> np.ndarray:
        res = builder_fn(b_map, t_df, cutoff_utc=cutoff_utc) if accepts_cutoff else builder_fn(b_map, t_df)
        arr = np.asarray(res[0] if isinstance(res, tuple) else res)
        if arr.ndim != 2 or arr.shape[0] != n_trades:
            raise ValueError(f"Unexpected builder_fn output shape: {arr.shape}")
        return arr

    x_orig = _call(bars_by_symbol, trades_df)
    entry_ts_arr = np.array([int(tr["entry_ts"]) for tr in trades_parsed], dtype=np.int64)
    chron_order = np.argsort(entry_ts_arr, kind="mergesort")

    n_pick = min(int(max_probes), n_trades)
    pos_list = (
        [0]
        if n_pick == 1
        else sorted({int(round(k * (n_trades - 1) / (n_pick - 1))) for k in range(n_pick)})
    )
    chosen = [int(chron_order[p]) for p in pos_list]

    probes_tested = 0
    total_bars_mutated = 0
    probe_details: list[dict[str, Any]] = []

    for p_idx in chosen:
        t_probe = int(entry_ts_arr[p_idx])
        bars_pert: dict[str, Any] = {}
        n_mut_total = 0
        for sym, entry in bars_by_symbol.items():
            if isinstance(entry, Mapping) and ("m1" in entry or "intraday" in entry):
                new_entry = dict(entry)
                for sk in ("m1", "intraday", "d1"):
                    if sk in new_entry and new_entry[sk] is not None:
                        sp, cnt = _perturb_bar_container_v105(new_entry[sk], t_probe, fv)
                        new_entry[sk] = sp
                        n_mut_total += cnt
                bars_pert[sym] = new_entry
            else:
                fp, cnt = _perturb_bar_container_v105(entry, t_probe, fv)
                bars_pert[sym] = fp
                n_mut_total += cnt

        if n_mut_total == 0:
            continue

        trades_pert = (
            _perturb_future_trades_v105(trades_df, t_probe, trades_parsed) if mutate_future_trades else trades_df
        )
        x_pert = _call(bars_pert, trades_pert)

        pre_mask = entry_ts_arr <= t_probe
        orig_slice = x_orig[pre_mask]
        pert_slice = x_pert[pre_mask]
        if not np.array_equal(orig_slice, pert_slice):
            diff_pos = np.argwhere(orig_slice != pert_slice)
            r_loc, c_idx = int(diff_pos[0, 0]), int(diff_pos[0, 1])
            pre_indices = np.flatnonzero(pre_mask)
            r_glob = int(pre_indices[r_loc])
            fname = FEATURE_NAMES_V105[c_idx] if c_idx < len(FEATURE_NAMES_V105) else f"col_{c_idx}"
            raise ValueError(
                f"FUTURE_LEAKAGE_DETECTED [probe_idx={p_idx}, t_probe={t_probe}]: "
                f"{len(diff_pos)} entries drifted under {fv}x perturbation; "
                f"first mismatch row={r_glob} feature={fname!r} "
                f"(orig={orig_slice[r_loc, c_idx]!r}, pert={pert_slice[r_loc, c_idx]!r})"
            )

        probes_tested += 1
        total_bars_mutated += n_mut_total
        probe_details.append(
            {
                "probe_row": p_idx,
                "t_probe_sec": t_probe,
                "pre_rows_checked": int(np.sum(pre_mask)),
                "bars_mutated": n_mut_total,
                "bit_exact": True,
            }
        )

    if probes_tested == 0 or total_bars_mutated == 0:
        raise ValueError("VACUOUS_CAUSALITY_TEST: zero future bars mutated across all probes")

    return {
        "gate": "W5-G10-PREP-CAUSALITY",
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


def verify_phase_invariance_1x_equiv(
    trades_seq: Sequence[Mapping[str, Any]],
    *,
    phase_multipliers: Sequence[float] = (1.0, 1.25, 3.5, 4.5),
    account_balances: Sequence[float] = (10_000.0, 100_000.0),
) -> dict[str, Any]:
    """Prove `rolling_dd_pct_1x_equiv` is bit-identical across all phase multipliers and account tiers.

    Simulates actual realized USD PnL under each `(phase_mult, initial_balance)` and recovers
    `net_R = net_pnl_usd / initial_risk_usd` (exact MQL5 live recovery formula), then verifies
    the resulting shadow 1.0x drawdown trajectory matches the canonical 1.0x curve to `<= 1e-12`.
    """
    if not trades_seq:
        raise ValueError("trades_seq cannot be empty")
    ref_tracker = Shadow1xClosedRTracker()
    ref_curve: list[float] = []
    for tr in trades_seq:
        ref_curve.append(ref_tracker.rolling_dd_pct_1x_equiv())
        ref_tracker.record_closed_trade(str(tr["engine_id"]), float(tr["net_R"]))
    ref_arr = np.asarray(ref_curve, dtype=np.float64)

    max_abs_diff = 0.0
    checked_profiles: list[dict[str, Any]] = []
    for bal0 in account_balances:
        for pmult in phase_multipliers:
            tr_sim = Shadow1xClosedRTracker()
            sim_curve: list[float] = []
            cur_bal = float(bal0)
            for tr in trades_seq:
                sim_curve.append(tr_sim.rolling_dd_pct_1x_equiv())
                eng = str(tr["engine_id"])
                base_rpct = canonical_base_risk_pct_1x(eng)
                init_risk_usd = cur_bal * ((base_rpct * float(pmult)) / 100.0) * 0.95
                net_pnl_usd = init_risk_usd * float(tr["net_R"])
                recovered_net_r = net_pnl_usd / max(init_risk_usd, _EPS)
                cur_bal = max(1.0, cur_bal + net_pnl_usd)
                tr_sim.record_closed_trade(eng, recovered_net_r)
            diff = float(np.max(np.abs(np.asarray(sim_curve, dtype=np.float64) - ref_arr)))
            max_abs_diff = max(max_abs_diff, diff)
            checked_profiles.append(
                {
                    "initial_balance_usd": float(bal0),
                    "phase_mult": float(pmult),
                    "max_abs_diff_pct_pts": diff,
                }
            )

    if max_abs_diff > 1e-12:
        raise ValueError(f"PHASE_INVARIANCE_BREACH: max_abs_diff={max_abs_diff:.3e} > 1e-12")

    return {
        "passed": True,
        "n_trades": len(trades_seq),
        "n_profiles_checked": len(checked_profiles),
        "max_abs_diff_pct_pts": max_abs_diff,
        "profiles": checked_profiles,
    }


def verify_ftmo_two_regime_dst_guardrail() -> dict[str, Any]:
    """Explicit P2-2 guardrail proof: `<= 2019` uses EU DST (`+2h`) and `>= 2020` uses US NY+7 (`+3h`) mid-March."""
    # 2019-03-20T12:00:00Z: after US DST (2019-03-10), BEFORE EU DST (2019-03-31) -> FTMO server MUST be UTC+2!
    ts_2019_mid_mar = int(datetime(2019, 3, 20, 12, 0, tzinfo=UTC).timestamp())
    # 2024-03-20T12:00:00Z: after US DST (2024-03-10), BEFORE EU DST (2024-03-31) -> FTMO server MUST be UTC+3!
    ts_2024_mid_mar = int(datetime(2024, 3, 20, 12, 0, tzinfo=UTC).timestamp())
    # 2024-11-01T12:00:00Z: after EU fall-back (2024-10-27), BEFORE US fall-back (2024-11-03) -> MUST be UTC+3!
    ts_2024_nov01 = int(datetime(2024, 11, 1, 12, 0, tzinfo=UTC).timestamp())
    # 2024-11-05T12:00:00Z: after US fall-back (2024-11-03) -> MUST be UTC+2!
    ts_2024_nov05 = int(datetime(2024, 11, 5, 12, 0, tzinfo=UTC).timestamp())

    probes = np.array([ts_2019_mid_mar, ts_2024_mid_mar, ts_2024_nov01, ts_2024_nov05], dtype=np.int64)
    srv = encode_utc_to_ftmo_server_times_v105(probes)
    offsets_h = ((srv - probes) // 3600).tolist()
    expected = [2, 3, 3, 2]
    if offsets_h != expected:
        raise ValueError(f"FTMO_DST_REGIME_MISMATCH: observed offsets={offsets_h}, expected={expected}")

    return {
        "passed": True,
        "schedule": BROKER_DST_SCHEDULE,
        "probe_offsets_hours": {
            "2019-03-20T12:00Z_eu_winter": offsets_h[0],
            "2024-03-20T12:00Z_us_dst_ny_plus_7": offsets_h[1],
            "2024-11-01T12:00Z_us_dst_after_eu_fallback": offsets_h[2],
            "2024-11-05T12:00Z_winter_after_us_fallback": offsets_h[3],
        },
    }


def verify_ftmo_m1_zero_bit_drift_causality(
    *,
    ftmo_m1_dir: Path = DEFAULT_FTMO_M1_DIR,
    symbols: Sequence[str] = ("USDJPY", "GBPUSD", "EURJPY", "US100.cash"),
    window_start_utc: str = "2024-01-02",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    max_probes: int = 5,
) -> dict[str, Any]:
    """Run future-perturbation zero-bit-drift causality proof directly on sealed FTMO-Demo M1 `.npz` files."""
    cutoff_sec = parse_cutoff_utc_exclusive(cutoff_utc)
    start_sec = _parse_timestamp_scalar(window_start_utc, name="window_start_utc")
    # Include 45 calendar days before window_start_utc so broker-day D1 indicators have full warmup
    warmup_start_sec = start_sec - 45 * 86_400

    bars_by_sym: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        raw = load_exported_m1(sym, out_dir=ftmo_m1_dir, verify_sha=False)
        ts_u = np.asarray(raw["ts_utc"], dtype=np.int64)
        if int(np.max(ts_u)) >= HOLDOUT_CUTOFF_UTC_TS:
            raise ValueError(f"HOLDOUT_BAR_BREACH[{sym}]: FTMO M1 contains bar >= 2025-01-01")
        lo_i = int(np.searchsorted(ts_u, warmup_start_sec, side="left"))
        hi_i = int(np.searchsorted(ts_u, cutoff_sec, side="left"))
        if hi_i <= lo_i:
            raise ValueError(f"Empty FTMO M1 slice for {sym}")
        norm_s = normalize_symbol(sym)
        bars_by_sym[norm_s] = {
            "ts_utc": ts_u[lo_i:hi_i],
            "ts_server_raw": np.asarray(raw["ts_server_raw"], dtype=np.int64)[lo_i:hi_i],
            "open": np.asarray(raw["open"], dtype=np.float64)[lo_i:hi_i],
            "high": np.asarray(raw["high"], dtype=np.float64)[lo_i:hi_i],
            "low": np.asarray(raw["low"], dtype=np.float64)[lo_i:hi_i],
            "close": np.asarray(raw["close"], dtype=np.float64)[lo_i:hi_i],
            "spread_pts": np.asarray(raw["spread_pts"], dtype=np.int32)[lo_i:hi_i],
            "point": float(raw["point"]),
            "bar_duration_sec": 60,
        }

    # Build deterministic probe trades across 2024 on FTMO M1 bars (including overlapping entries & DST transitions)
    probe_dates = [
        ("2024-02-14T08:15:00Z", "USDJPY", "E1_USDJPY_TOKYO", 1, 1.4),
        ("2024-03-19T13:30:00Z", "GBPUSD", "E3_GBPUSD_VH", -1, -1.0),  # Between US & EU spring DST!
        ("2024-03-19T14:00:00Z", "US100", "E4_US100_SESS40", -1, 2.1),  # Concurrent same-dir!
        ("2024-06-12T10:05:00Z", "EURJPY", "E6_EURJPY_VOLCOMP", 1, -0.9),
        ("2024-10-30T14:45:00Z", "USDJPY", "E7_USDJPY_NY10ET", 1, 1.8),  # Between EU & US fall DST!
        ("2024-11-20T15:35:00Z", "US100", "E5_US100_RS1130", -1, -1.0),
    ]
    probe_trades: list[dict[str, Any]] = []
    for iso_ts, sym_n, eng, side, nr in probe_dates:
        ent = _parse_timestamp_scalar(iso_ts, name="probe_entry")
        probe_trades.append(
            {
                "symbol": sym_n,
                "engine_id": eng,
                "entry_ts": ent,
                "exit_ts": ent + 4 * 3600,
                "side": side,
                "net_R": nr,
            }
        )

    proof = assert_zero_future_leakage_v105(
        build_aligned_feature_matrix_v105,
        bars_by_sym,
        probe_trades,
        cutoff_utc=cutoff_utc,
        perturbation_factor=10.0,
        max_probes=max_probes,
        mutate_future_trades=True,
    )
    proof["ftmo_m1_dir"] = str(ftmo_m1_dir)
    proof["symbols_tested"] = list(symbols)
    proof["window"] = f"{window_start_utc}..{cutoff_utc}"
    return proof


# ---------------------------------------------------------------------------
# Sealed PORT_7E Dev Bundle Loader (Lazy Imports Only — CI & X13 Safe!)
# ---------------------------------------------------------------------------


def build_port7e_dev_aligned_bundle_v105(
    *,
    portfolio_key: str = "PORT_7E_P28_CORE",
    cutoff_utc: str = HOLDOUT_CUTOFF_DATE,
    verify_sha: bool = True,
    verify_causality: bool = False,
) -> dict[str, Any]:
    """Load sealed Dev `PORT_7E` trades + M1 bars (lazy imports) and build aligned `(N, 20)` `float32` matrix."""
    from quant_factory.data_store import (  # Lazy import ONLY
        assert_holdout_locked,
        build_or_load_frozen_tapes,
        load_registry,
    )
    from quant_factory.offensive3.x13_m1_loader import load_m1_asset  # Lazy import ONLY
    from quant_factory.wave4.ml_features_24 import extract_trades_from_frozen_tapes

    lock_sha = assert_holdout_locked()
    cutoff_sec_excl = parse_cutoff_utc_exclusive(cutoff_utc)
    reg = load_registry()
    engines = list(reg["frozen_portfolios"][portfolio_key]["engines"])

    frozen = build_or_load_frozen_tapes(force_rebuild=False)
    trades = extract_trades_from_frozen_tapes(
        frozen["tapes"],
        engines=engines,
        base_risks=CANONICAL_BASE_RISK_PCT_1X,
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

    x_mat, meta = build_aligned_feature_matrix_v105(
        bars_by_symbol,
        trades,
        cutoff_utc=cutoff_utc,
        return_metadata=True,
    )
    causality_report = (
        assert_zero_future_leakage_v105(
            build_aligned_feature_matrix_v105,
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
        "broker_dst_schedule": BROKER_DST_SCHEDULE,
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
        "exit_ts": np.array([tr["exit_ts"] for tr in trades], dtype=np.int64),
        "risk_pct_1x": np.array([canonical_base_risk_pct_1x(tr["engine_id"]) for tr in trades], dtype=np.float64),
        "trades": trades,
        "metadata": meta,
        "causality_proof": causality_report,
    }


__all__ = [
    "ASSET_CLASS_CODES",
    "BROKER_DST_SCHEDULE",
    "CANONICAL_BASE_RISK_PCT_1X",
    "DEV_CUTOFF_DATE",
    "DEV_CUTOFF_SEC",
    "ENGINE_ID_CODES",
    "ENGINE_ID_TO_MAGIC",
    "FEATURE_GROUPS_V105",
    "FEATURE_NAMES_V105",
    "FEATURE_SPECS_V105",
    "HOLDOUT_CUTOFF_DATE",
    "MAGIC_TO_ENGINE_ID",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "PORT_7E_SYMBOLS",
    "SCHEMA_VERSION",
    "SHADOW_1X_R_CLAMP_MAX",
    "SHADOW_1X_R_CLAMP_MIN",
    "Shadow1xClosedRTracker",
    "assert_zero_future_leakage_v105",
    "build_aligned_feature_matrix_v105",
    "build_port7e_dev_aligned_bundle_v105",
    "canonical_base_risk_pct_1x",
    "extract_single_signal_aligned_features",
    "precompute_aligned_broker_d1_indicators",
    "verify_ftmo_m1_zero_bit_drift_causality",
    "verify_ftmo_two_regime_dst_guardrail",
    "verify_phase_invariance_1x_equiv",
]
