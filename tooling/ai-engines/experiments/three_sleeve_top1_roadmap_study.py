"""3-Sleeve Top-1% Solo Quant Roadmap Study — Strictly Sealed Dev (`<= 2024-12-31`, `holdout_rows_analysed = 0`).

Evaluates the orthogonal 3-sleeve portfolio combination strictly on Development data `<= 2024-12-31`:
  - Sleeve 1 (`S1_PORT_7E_PROP`): Frozen M1 Bid/Ask `PORT_7E` (`frozen_9e_tapes_v2`, C10_NEWS_ON / Funded 1.0x & 1.25x,
    official 6-ccy Red-News `±5m`, `swap = 0`).
  - Sleeve 2 (`S2_CRYPTO_SPOT_CARRY`): Strictly causal Crypto Spot Top-15 (`D1` 15 bps / 30 bps stress) +
    Delta-Neutral Funding Carry (`2x` equity buffer, 23 bps / 46 bps pair cost + real basis MTM) loaded from
    `.runtime/crypto-spot-cache/` and sliced `< 2025-01-01` at read time.
  - Sleeve 3 (`S3_MACRO_ETF`): Long-Only `0` swap Macro ETF sleeves (`S3B` Risk-Parity Trend-Guard, `S3B` Pure
    All-Weather, `S3B` Dual Momentum from `.runtime/macro-etf-cache/`; `L7_TOP2` Macro Quad + MM17 Var Core,
    `S4` Lab #4 Multi-Factor, `SUPER_ETF_6ENG` from `.runtime/etf40-cache/`) sliced `< 2025-01-01` at read time.

Hard fail-closed invariants (ZERO Python `assert` statements; 100% enforced under `python -O`):
  - `ORDER_SEND_COUNT = 0`, `HOLDOUT_ROWS_ANALYSED = 0`.
  - Every parquet loader discards `>= 2025-01-01` BEFORE constructing any price matrix or computing returns,
    and explicitly verifies `max(dates) < "2025-01-01"` via `if ...: raise HoldoutLockError(...)`.
  - Never mutates `NATIVE_FTMO_HOLDOUT_LOCK.json` or any cached file on disk.
  - Reports pairwise daily & worst-5% tail correlations, combined Sharpe/Calmar/Max DD, starved-month rate
    (`monthly_return <= 0%`), IBKR integer-vs-fractional lot drag on Dev `<= 2024-12-31`, and honest capital
    thresholds aligned with `planning/TOP1-SOLO-QUANT-MASTER-PLAN.md` §3.2 (`< 10k` Cash/T-Bill -> `10k-25k` ETF
    -> `25k+` Crypto `CEX <= 25%` -> `50k+` Full Integer-Lot ETF -> `100k+` CME Micro Futures).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from collections.abc import Iterable, Mapping, Sequence
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np

AI_ENGINES_DIR = Path(__file__).resolve().parents[1]
if str(AI_ENGINES_DIR) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES_DIR))

from quant_core.holdout_guard import (  # noqa: E402
    HOLDOUT_CUTOFF_DAY,
    HOLDOUT_START_UTC_TS,
    HoldoutLockError,
    enforce_holdout_zero_rows,
    enforce_pre_holdout_dates,
    enforce_pre_holdout_ts,
)
from quant_core.io_utils import atomic_write_json, repo_root_from  # noqa: E402
from quant_core.metrics import (  # noqa: E402
    compute_drawdowns,
    compute_sharpe,
    deflated_sharpe_ratio_empirical,
)

ROOT = repo_root_from(__file__)

DEV_MAX_DATE: str = "2024-12-31"
HOLDOUT_START_UTC_MS: int = HOLDOUT_START_UTC_TS * 1000
ORDER_SEND_COUNT: int = 0
HOLDOUT_ROWS_ANALYSED: int = 0

DEFAULT_MACRO_ETF_CACHE: Path = ROOT / ".runtime" / "macro-etf-cache"
DEFAULT_ETF40_CACHE: Path = ROOT / ".runtime" / "etf40-cache"
DEFAULT_CRYPTO_CACHE: Path = ROOT / ".runtime" / "crypto-spot-cache"
DEFAULT_FX_RATES_PATH: Path = ROOT / "tooling" / "ai-engines" / "configs" / "ssot" / "fx_rates.json"
DEFAULT_RISK_PROFILES_PATH: Path = ROOT / "tooling" / "ai-engines" / "configs" / "ssot" / "risk_profiles.json"

MAX_CEX_GROUP_CAP: float = 0.25
OVERLAP_START_3SLEEVE: str = "2020-01-02"
OVERLAP_START_2SLEEVE: str = "2018-01-02"
DEV_TRAIN_END: str = "2022-12-31"
DEV_OOS_START: str = "2023-01-01"


# ==============================================================================
# FAIL-CLOSED PRE-HOLDOUT CUTOFF ENFORCEMENT (`-O` SAFE, ZERO `assert`)
# ==============================================================================


def enforce_dev_cutoff_strict(
    dates: Sequence[str] | Iterable[Any],
    *,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
    context: str = "three_sleeve_dev_study",
    allow_empty: bool = False,
) -> None:
    """Hard `-O`-safe guard rejecting any cutoff > `2025-01-01` or any date `>= cutoff_day`."""
    if not isinstance(cutoff_day, str) or len(cutoff_day) != 10:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid cutoff_day={cutoff_day!r}")
    try:
        parsed_cutoff = date.fromisoformat(cutoff_day)
    except ValueError as exc:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: malformed cutoff_day={cutoff_day!r}") from exc
    if parsed_cutoff > date(2025, 1, 1):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_day={cutoff_day!r} exceeds sealed 2025-01-01 boundary"
        )

    date_list = list(dates)
    if not date_list:
        if not allow_empty:
            raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: empty date sequence rejected")
        return

    enforce_pre_holdout_dates(date_list, context=context, cutoff_day=cutoff_day, allow_empty=allow_empty)

    # Explicit belt-and-suspenders check independent of helper internals (immune to python -O)
    max_iso = max(str(d)[:10] for d in date_list)
    if max_iso >= cutoff_day:
        raise HoldoutLockError(f"HOLDOUT_CONTAMINATION [{context}]: max date {max_iso!r} >= cutoff {cutoff_day!r}")


def slice_daily_map_pre_holdout(
    ret_map: Mapping[str, float],
    *,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
    context: str = "daily_map",
) -> tuple[dict[str, float], int]:
    """Slice a `YYYY-MM-DD -> float` map strictly `< cutoff_day`, returning `(dev_map, excluded_count)`."""
    if cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_day={cutoff_day!r} > {HOLDOUT_CUTOFF_DAY}")
    dev_map: dict[str, float] = {}
    excluded = 0
    for dk, val in ret_map.items():
        day_str = str(dk)[:10]
        if day_str >= cutoff_day:
            excluded += 1
            continue
        fv = float(val)
        if not math.isfinite(fv):
            raise ValueError(f"Non-finite return value at {day_str} in {context}: {val!r}")
        dev_map[day_str] = fv
    enforce_dev_cutoff_strict(sorted(dev_map.keys()), cutoff_day=cutoff_day, context=context, allow_empty=True)
    return dev_map, excluded


def _ms_to_utc_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, tz=UTC).strftime("%Y-%m-%d")


def _cutoff_to_utc_ms(cutoff_day: str) -> int:
    if cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION: cutoff_day={cutoff_day!r} > {HOLDOUT_CUTOFF_DAY}")
    dt = datetime.fromisoformat(cutoff_day).replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


# ==============================================================================
# READ-TIME PRE-HOLDOUT CACHE LOADERS (DISCARD >= 2025-01-01 BEFORE ANALYSIS)
# ==============================================================================


def load_macro_etf_dev_panel(
    *,
    cache_dir: Path = DEFAULT_MACRO_ETF_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Load 12-ETF panel from `.runtime/macro-etf-cache/` strictly sliced `< cutoff_day` at read time."""
    import pyarrow.parquet as pq
    from quant_factory.macro_etf_trend import ETF_UNIVERSE_12

    if cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [macro_etf]: cutoff_day={cutoff_day!r}")

    loaded_syms: list[str] = []
    maps: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    excluded_rows = 0

    for sym in ETF_UNIVERSE_12:
        p = Path(cache_dir) / f"{sym}.parquet"
        if not p.is_file():
            continue
        tbl = pq.read_table(p, columns=["date", "adjclose"])
        ds = tbl["date"].to_pylist()
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False)
        mp: dict[str, float] = {}
        for d_raw, v_raw in zip(ds, ac, strict=True):
            dk = str(d_raw)[:10]
            if dk >= cutoff_day:
                excluded_rows += 1
                continue
            fv = float(v_raw)
            if math.isfinite(fv) and fv > 0.0:
                mp[dk] = fv
        if mp:
            loaded_syms.append(sym)
            maps[sym] = mp
            all_dates.update(mp.keys())

    dates = sorted(all_dates)
    enforce_dev_cutoff_strict(dates, cutoff_day=cutoff_day, context="macro_etf_dev_panel")

    n_t, n_k = len(dates), len(loaded_syms)
    adjclose = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for j, sym in enumerate(loaded_syms):
        mp = maps[sym]
        for i, dk in enumerate(dates):
            if dk in mp:
                adjclose[i, j] = mp[dk]

    return {
        "dates": dates,
        "symbols": loaded_syms,
        "adjclose": adjclose,
        "excluded_post_cutoff_rows": int(excluded_rows),
        "holdout_rows_analysed": 0,
    }


def load_etf40_dev_panels(
    *,
    cache_dir: Path = DEFAULT_ETF40_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Load 40-ETF NYSE close + OHLC panels strictly sliced `< cutoff_day` at read time."""
    import pyarrow.parquet as pq
    from quant_factory.etf40_multifactor_vrp_lab import (
        ETF40_UNIVERSE,
        SIGNAL_ONLY_TICKERS,
        _safe_filename,
    )

    if cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [etf40]: cutoff_day={cutoff_day!r}")

    spy_path = Path(cache_dir) / _safe_filename("SPY")
    if not spy_path.is_file():
        raise FileNotFoundError(f"Missing SPY parquet in {cache_dir}")
    spy_tbl = pq.read_table(spy_path, columns=["date"])
    raw_spy_dates = spy_tbl["date"].to_pylist()
    nyse_dates = sorted({str(d)[:10] for d in raw_spy_dates if str(d)[:10] < cutoff_day})
    enforce_dev_cutoff_strict(nyse_dates, cutoff_day=cutoff_day, context="etf40_nyse_dates")
    d_map = {d: i for i, d in enumerate(nyse_dates)}

    tickers = list(ETF40_UNIVERSE)
    n_t, n_k = len(nyse_dates), len(tickers)
    adj_open = np.full((n_t, n_k), np.nan, dtype=np.float64)
    adj_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    excluded_rows = 0

    for j, tk in enumerate(tickers):
        p = Path(cache_dir) / _safe_filename(tk)
        if not p.is_file():
            continue
        tbl = pq.read_table(p, columns=["date", "open", "close", "adjclose"])
        ds = tbl["date"].to_pylist()
        op = tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64)
        cl = tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False).astype(np.float64)
        for d_raw, o_v, c_v, ac_v in zip(ds, op, cl, ac, strict=True):
            dk = str(d_raw)[:10]
            if dk >= cutoff_day:
                excluded_rows += 1
                continue
            idx = d_map.get(dk)
            if idx is None or not (math.isfinite(ac_v) and ac_v > 0.0):
                continue
            adj_close[idx, j] = ac_v
            if math.isfinite(o_v) and o_v > 0.0 and math.isfinite(c_v) and c_v > 0.0:
                adj_open[idx, j] = o_v * (ac_v / c_v)
            else:
                adj_open[idx, j] = ac_v

    r_cc = np.full((n_t, n_k), np.nan, dtype=np.float64)
    r_ov = np.full((n_t, n_k), np.nan, dtype=np.float64)
    r_id = np.full((n_t, n_k), np.nan, dtype=np.float64)

    ok_cc = np.isfinite(adj_close[1:]) & np.isfinite(adj_close[:-1]) & (adj_close[:-1] > 0.0)
    r_cc[1:] = np.where(ok_cc, adj_close[1:] / np.where(ok_cc, adj_close[:-1], 1.0) - 1.0, np.nan)

    ok_ov = np.isfinite(adj_open[1:]) & np.isfinite(adj_close[:-1]) & (adj_close[:-1] > 0.0)
    r_ov[1:] = np.where(ok_ov, adj_open[1:] / np.where(ok_ov, adj_close[:-1], 1.0) - 1.0, np.nan)

    ok_id = np.isfinite(adj_close) & np.isfinite(adj_open) & (adj_open > 0.0)
    r_id = np.where(ok_id, adj_close / np.where(ok_id, adj_open, 1.0) - 1.0, np.nan)

    tradable_mask = np.array([tk not in SIGNAL_ONLY_TICKERS for tk in tickers], dtype=bool)
    panel4 = {
        "dates": nyse_dates,
        "symbols": tickers,
        "adjclose": adj_close,
        "excluded_post_cutoff_rows": int(excluded_rows),
        "holdout_rows_analysed": 0,
    }
    panel7 = {
        "dates": nyse_dates,
        "tickers": tickers,
        "tradable_mask": tradable_mask,
        "adj_open": adj_open,
        "adj_close": adj_close,
        "r_cc": r_cc,
        "r_ov": r_ov,
        "r_id": r_id,
        "excluded_post_cutoff_rows": int(excluded_rows),
        "holdout_rows_analysed": 0,
    }
    return panel4, panel7


def load_crypto_spot_dev_panel(
    *,
    cache_dir: Path = DEFAULT_CRYPTO_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Load D1 50-coin Binance Spot panel strictly sliced `< cutoff_day` at read time."""
    import pyarrow.parquet as pq
    from quant_factory.crypto_causal_universe import UNIVERSE_50_SYMBOLS

    cutoff_ms = _cutoff_to_utc_ms(cutoff_day)
    iv_dir = Path(cache_dir) / "1d"
    loaded_syms: list[str] = []
    raw_tables: dict[str, dict[str, np.ndarray]] = {}
    all_ts_set: set[int] = set()
    excluded_rows = 0

    for sym in UNIVERSE_50_SYMBOLS:
        p = iv_dir / f"{sym}.parquet"
        if not p.is_file():
            continue
        tbl = pq.read_table(p, columns=["open_time_ms", "open", "high", "low", "close", "quote_volume"])
        ot_all = tbl["open_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        keep = ot_all < cutoff_ms
        excluded_rows += int(np.count_nonzero(~keep))
        if not np.any(keep):
            continue
        ot = ot_all[keep]
        loaded_syms.append(sym)
        raw_tables[sym] = {
            "t": ot,
            "o": tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64)[keep],
            "h": tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64)[keep],
            "l": tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64)[keep],
            "c": tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)[keep],
            "qv": tbl["quote_volume"].to_numpy(zero_copy_only=False).astype(np.float64)[keep],
        }
        all_ts_set.update(ot.tolist())

    timestamps = np.array(sorted(all_ts_set), dtype=np.int64)
    if timestamps.size == 0:
        raise HoldoutLockError("HOLDOUT_LOCK_VIOLATION [crypto_spot]: no pre-cutoff timestamps found")
    enforce_pre_holdout_ts(
        timestamps // 1000,
        stop_ts=cutoff_ms // 1000,
        context="crypto_spot_dev_panel",
    )
    dates = [_ms_to_utc_date(int(t)) for t in timestamps]
    enforce_dev_cutoff_strict(dates, cutoff_day=cutoff_day, context="crypto_spot_dev_panel")

    ts_to_idx = {int(t): i for i, t in enumerate(timestamps)}
    n_t, n_k = len(timestamps), len(loaded_syms)
    opens = np.full((n_t, n_k), np.nan, dtype=np.float64)
    highs = np.full((n_t, n_k), np.nan, dtype=np.float64)
    lows = np.full((n_t, n_k), np.nan, dtype=np.float64)
    closes = np.full((n_t, n_k), np.nan, dtype=np.float64)
    qvol = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        d = raw_tables[sym]
        idxs = np.array([ts_to_idx[int(t)] for t in d["t"]], dtype=np.int64)
        opens[idxs, j] = d["o"]
        highs[idxs, j] = d["h"]
        lows[idxs, j] = d["l"]
        closes[idxs, j] = d["c"]
        qvol[idxs, j] = d["qv"]

    return {
        "interval": "1d",
        "symbols": loaded_syms,
        "timestamps_ms": timestamps,
        "dates": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "quote_volume": qvol,
        "excluded_post_cutoff_rows": int(excluded_rows),
        "holdout_rows_analysed": 0,
    }


def load_crypto_funding_dev_panel(
    *,
    cache_dir: Path = DEFAULT_CRYPTO_CACHE,
    spot_panel: dict[str, Any] | None = None,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Load 20-coin Funding Rate + Perp/Spot D1 panel strictly sliced `< cutoff_day` at read time."""
    import pyarrow.parquet as pq
    from quant_factory.funding_rate_carry import PERP_UNIVERSE_20, START_DATE

    cutoff_ms = _cutoff_to_utc_ms(cutoff_day)
    funding_dir = Path(cache_dir) / "funding"
    if spot_panel is None:
        spot_panel = load_crypto_spot_dev_panel(cache_dir=cache_dir, cutoff_day=cutoff_day)
    enforce_dev_cutoff_strict(spot_panel["dates"], cutoff_day=cutoff_day, context="funding_spot_panel")
    spot_sym_idx = {s: i for i, s in enumerate(spot_panel["symbols"])}

    daily_fund_by_sym: dict[str, dict[str, float]] = {}
    perp_c_by_sym: dict[str, dict[str, float]] = {}
    perp_h_by_sym: dict[str, dict[str, float]] = {}
    spot_c_by_sym: dict[str, dict[str, float]] = {}
    spot_h_by_sym: dict[str, dict[str, float]] = {}
    loaded_syms: list[str] = []
    all_days: set[str] = set()
    excluded_rows = 0

    for sym in PERP_UNIVERSE_20:
        rp = funding_dir / "rates" / f"{sym}.parquet"
        kp = funding_dir / "perp_1d" / f"{sym}.parquet"
        if not rp.is_file():
            continue
        tbl = pq.read_table(rp, columns=["funding_time_ms", "funding_rate"])
        ft = tbl["funding_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        fr = tbl["funding_rate"].to_numpy(zero_copy_only=False).astype(np.float64)
        dsum: dict[str, float] = defaultdict(float)
        for ts, rate in zip(ft, fr, strict=True):
            if int(ts) >= cutoff_ms:
                excluded_rows += 1
                continue
            dk = _ms_to_utc_date(int(ts))
            if START_DATE <= dk < cutoff_day and math.isfinite(float(rate)):
                dsum[dk] += float(rate)
                all_days.add(dk)
        if not dsum:
            continue
        loaded_syms.append(sym)
        daily_fund_by_sym[sym] = dict(dsum)

        pc: dict[str, float] = {}
        ph: dict[str, float] = {}
        if kp.is_file():
            kt = pq.read_table(kp, columns=["open_time_ms", "high", "close"])
            for ot, hv, cv in zip(
                kt["open_time_ms"].to_numpy(zero_copy_only=False),
                kt["high"].to_numpy(zero_copy_only=False),
                kt["close"].to_numpy(zero_copy_only=False),
                strict=True,
            ):
                if int(ot) >= cutoff_ms:
                    excluded_rows += 1
                    continue
                dk = _ms_to_utc_date(int(ot))
                if dk < cutoff_day:
                    pc[dk] = float(cv)
                    ph[dk] = float(hv)
        perp_c_by_sym[sym] = pc
        perp_h_by_sym[sym] = ph

        sc: dict[str, float] = {}
        sh: dict[str, float] = {}
        if sym in spot_sym_idx:
            j = spot_sym_idx[sym]
            for dk, hv, cv in zip(
                spot_panel["dates"],
                spot_panel["high"][:, j],
                spot_panel["close"][:, j],
                strict=True,
            ):
                if dk >= cutoff_day:
                    continue
                if np.isfinite(cv) and cv > 0.0:
                    sc[dk] = float(cv)
                if np.isfinite(hv) and hv > 0.0:
                    sh[dk] = float(hv)
        spot_c_by_sym[sym] = sc
        spot_h_by_sym[sym] = sh

    dates = sorted(all_days)
    enforce_dev_cutoff_strict(dates, cutoff_day=cutoff_day, context="crypto_funding_dev_panel")
    n_t, n_k = len(dates), len(loaded_syms)

    fund_daily = np.full((n_t, n_k), np.nan, dtype=np.float64)
    perp_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    perp_high = np.full((n_t, n_k), np.nan, dtype=np.float64)
    spot_close = np.full((n_t, n_k), np.nan, dtype=np.float64)
    spot_high = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        fm = daily_fund_by_sym[sym]
        pm = perp_c_by_sym[sym]
        hm = perp_h_by_sym[sym]
        sm = spot_c_by_sym[sym]
        shm = spot_h_by_sym[sym]
        for i, dk in enumerate(dates):
            if dk in fm:
                fund_daily[i, j] = fm[dk]
            if dk in pm:
                perp_close[i, j] = pm[dk]
            if dk in hm:
                perp_high[i, j] = hm[dk]
            if dk in sm:
                spot_close[i, j] = sm[dk]
            if dk in shm:
                spot_high[i, j] = shm[dk]

    return {
        "dates": dates,
        "symbols": loaded_syms,
        "funding_daily": fund_daily,
        "perp_close": perp_close,
        "perp_high": perp_high,
        "spot_close": spot_close,
        "spot_high": spot_high,
        "excluded_post_cutoff_rows": int(excluded_rows),
        "holdout_rows_analysed": 0,
    }


# ==============================================================================
# PURE PORTFOLIO METRICS, MONTHLY STARVED-RATE & CORRELATIONS (TESTABLE OFFLINE)
# ==============================================================================


def align_daily_sleeves_business_days(
    sleeve_maps: Mapping[str, Mapping[str, float]],
    *,
    start_day: str,
    end_day: str = DEV_MAX_DATE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> tuple[list[str], np.ndarray, list[str]]:
    """Align sleeves onto Mon-Fri business days in `[start_day, end_day]`, compounding Sat/Sun into Monday."""
    if end_day >= cutoff_day or cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [align_sleeves]: end_day={end_day!r} >= cutoff_day={cutoff_day!r}"
        )
    names = list(sleeve_maps.keys())
    if not names:
        raise ValueError("sleeve_maps must not be empty")
    for nm, smap in sleeve_maps.items():
        if smap:
            enforce_dev_cutoff_strict(list(smap.keys()), cutoff_day=cutoff_day, context=f"align.{nm}")

    d0 = date.fromisoformat(start_day)
    d1 = date.fromisoformat(end_day)
    if d1 < d0:
        raise ValueError(f"Empty alignment range: {start_day}..{end_day}")

    biz_days: list[str] = []
    rows: list[list[float]] = []
    carry_factor = {nm: 1.0 for nm in names}
    cur = d0
    while cur <= d1:
        iso = cur.isoformat()
        if cur.weekday() >= 5:
            for nm in names:
                carry_factor[nm] *= 1.0 + float(sleeve_maps[nm].get(iso, 0.0))
        else:
            row = []
            for nm in names:
                r = float(sleeve_maps[nm].get(iso, 0.0))
                eff_r = carry_factor[nm] * (1.0 + r) - 1.0
                carry_factor[nm] = 1.0
                row.append(eff_r)
            biz_days.append(iso)
            rows.append(row)
        cur += timedelta(days=1)

    enforce_dev_cutoff_strict(biz_days, cutoff_day=cutoff_day, context="align_output_biz_days")
    return biz_days, np.asarray(rows, dtype=np.float64), names


def compute_monthly_returns(dates: Sequence[str], daily_returns: np.ndarray) -> dict[str, float]:
    """Compound daily returns into calendar months `YYYY-MM`."""
    if len(dates) != len(daily_returns):
        raise ValueError("dates and daily_returns must share identical length")
    by_month: dict[str, float] = {}
    for dk, r in zip(dates, daily_returns, strict=True):
        ym = str(dk)[:7]
        by_month[ym] = (1.0 + by_month.get(ym, 0.0)) * (1.0 + float(r)) - 1.0
    return dict(sorted(by_month.items()))


def compute_starved_month_stats(
    dates: Sequence[str],
    daily_returns: np.ndarray,
    *,
    low_return_threshold: float = 0.005,
) -> dict[str, Any]:
    """Compute exact starved-month (`<= 0%`) and low-income-month (`< +0.5%`) rates & max streaks."""
    monthly = compute_monthly_returns(dates, daily_returns)
    vals = [monthly[ym] for ym in sorted(monthly)]
    n_months = len(vals)
    if n_months == 0:
        return {
            "n_months": 0,
            "positive_months": 0,
            "starved_months_le_0": 0,
            "starved_month_rate_pct": 0.0,
            "low_month_rate_lt_0p5pct": 0.0,
            "max_consec_starved_months": 0,
            "win_month_rate_pct": 0.0,
            "monthly_median_pct": 0.0,
            "monthly_worst_pct": 0.0,
            "monthly_best_pct": 0.0,
        }

    starved_cnt = 0
    low_cnt = 0
    cur_streak = 0
    max_streak = 0
    for mv in vals:
        if mv <= 0.0:
            starved_cnt += 1
            cur_streak += 1
            if cur_streak > max_streak:
                max_streak = cur_streak
        else:
            cur_streak = 0
        if mv < low_return_threshold:
            low_cnt += 1

    arr = np.asarray(vals, dtype=np.float64)
    return {
        "n_months": int(n_months),
        "positive_months": int(n_months - starved_cnt),
        "starved_months_le_0": int(starved_cnt),
        "starved_month_rate_pct": round(100.0 * starved_cnt / float(n_months), 2),
        "low_month_rate_lt_0p5pct": round(100.0 * low_cnt / float(n_months), 2),
        "max_consec_starved_months": int(max_streak),
        "win_month_rate_pct": round(100.0 * (n_months - starved_cnt) / float(n_months), 2),
        "monthly_median_pct": round(100.0 * float(np.median(arr)), 2),
        "monthly_worst_pct": round(100.0 * float(np.min(arr)), 2),
        "monthly_best_pct": round(100.0 * float(np.max(arr)), 2),
    }


def compute_portfolio_metrics(
    dates: Sequence[str],
    daily_returns: np.ndarray,
    *,
    ann_days: int = 252,
    n_trials_dsr: int = 1,
    trial_sharpes: Sequence[float] | None = None,
) -> dict[str, Any]:
    """Compute balanced institutional metrics via `quant_core.metrics` + starved-month & PF stats."""
    r = np.asarray(daily_returns, dtype=np.float64)
    if r.ndim != 1 or r.size == 0 or not np.all(np.isfinite(r)):
        raise ValueError("daily_returns must be a non-empty finite 1D array")
    if len(dates) != r.size:
        raise ValueError("dates length must match daily_returns length")

    eq = np.cumprod(1.0 + r)
    yrs = float(r.size) / float(ann_days)
    cagr = (float(eq[-1]) ** (1.0 / max(yrs, 1e-6))) - 1.0 if eq[-1] > 0.0 else -1.0
    sr = compute_sharpe(r, annualization_days=ann_days, calendar_aligned=True)
    dd = compute_drawdowns(eq, initial_capital=1.0)
    calmar = (cagr / dd.dd_of_peak_frac) if dd.dd_of_peak_frac > 1e-12 else 0.0

    neg = r[r < 0.0]
    down_sd = float(np.sqrt(np.mean(neg * neg))) if neg.size > 0 else 1e-12
    sortino = (float(np.mean(r)) / max(down_sd, 1e-12)) * math.sqrt(float(ann_days))

    # Daily Winrate, RR, EV/day, and Profit Factor across active days
    active = r[np.abs(r) > 1e-12]
    wins = active[active > 0.0]
    losses = active[active < 0.0]
    gross_win = float(np.sum(wins))
    gross_loss = float(np.sum(np.abs(losses)))
    daily_pf = (gross_win / gross_loss) if gross_loss > 1e-12 else (99.0 if gross_win > 0.0 else 0.0)
    daily_wr = (float(wins.size) / float(active.size)) if active.size > 0 else 0.0
    avg_win = float(np.mean(wins)) if wins.size > 0 else 0.0
    avg_loss = float(np.mean(np.abs(losses))) if losses.size > 0 else 0.0
    daily_rr = (avg_win / avg_loss) if avg_loss > 1e-12 else 0.0

    # Monthly Profit Factor & Winrate (more meaningful across blended daily/weekly/monthly sleeves)
    monthly = compute_monthly_returns(dates, r)
    m_arr = np.asarray([monthly[ym] for ym in sorted(monthly)], dtype=np.float64)
    m_pos = m_arr[m_arr > 0.0]
    m_neg = m_arr[m_arr < 0.0]
    m_pf = (
        float(np.sum(m_pos)) / float(np.sum(np.abs(m_neg)))
        if float(np.sum(np.abs(m_neg))) > 1e-12
        else (99.0 if float(np.sum(m_pos)) > 0.0 else 0.0)
    )
    m_rr = (float(np.mean(m_pos)) / float(np.mean(np.abs(m_neg)))) if (m_pos.size > 0 and m_neg.size > 0) else 0.0

    starved = compute_starved_month_stats(dates, r)

    dsr_val: float | None = None
    if r.size >= 10 and sr.std_return > 1e-12:
        if trial_sharpes is not None and len(trial_sharpes) >= 2:
            dsr_res = deflated_sharpe_ratio_empirical(
                r,
                trial_sharpes=list(trial_sharpes),
                n_trials=max(int(n_trials_dsr), len(trial_sharpes)),
                annualization_days=ann_days,
                sharpes_are_annualized=True,
            )
            dsr_val = round(dsr_res.dsr, 4)
        elif n_trials_dsr == 1:
            dsr_res = deflated_sharpe_ratio_empirical(r, n_trials=1, annualization_days=ann_days)
            dsr_val = round(dsr_res.dsr, 4)

    return {
        "n_days": int(r.size),
        "start_day": str(dates[0]),
        "end_day": str(dates[-1]),
        "cagr_pct": round(100.0 * cagr, 2),
        "ann_vol_pct": round(100.0 * sr.std_return * math.sqrt(float(ann_days)), 2),
        "sharpe": round(sr.sharpe_annualized, 2),
        "sortino": round(sortino, 2),
        "max_dd_pct": round(100.0 * dd.dd_of_peak_frac, 2),
        "static_dd_pct": round(100.0 * dd.dd_of_initial_frac, 2),
        "calmar": round(calmar, 2),
        "total_ret_pct": round(100.0 * float(eq[-1] - 1.0), 2),
        "worst_day_pct": round(100.0 * float(np.min(r)), 2),
        "daily_winrate_pct": round(100.0 * daily_wr, 2),
        "daily_rr": round(daily_rr, 2),
        "daily_pf": round(daily_pf, 2),
        "monthly_pf": round(m_pf, 2),
        "monthly_rr": round(m_rr, 2),
        "dsr": dsr_val,
        **starved,
    }


def compute_pairwise_correlations(
    mat: np.ndarray,
    names: Sequence[str],
    *,
    tail_ref_idx: int = 0,
    tail_quantile: float = 0.05,
) -> dict[str, Any]:
    """Compute exact full-sample pairwise correlation matrix + worst-5% tail correlation against ref sleeve."""
    k = len(names)
    if mat.ndim != 2 or mat.shape[1] != k:
        raise ValueError("mat shape must match len(names)")
    full_corr: dict[str, dict[str, float]] = {}
    tail_corr: dict[str, float] = {}

    ref = mat[:, tail_ref_idx]
    q_cut = float(np.quantile(ref, tail_quantile))
    tail_mask = ref <= q_cut
    tail_count = int(np.count_nonzero(tail_mask))

    for i in range(k):
        row_map: dict[str, float] = {}
        for j in range(k):
            if i == j:
                row_map[str(names[j])] = 1.0
            else:
                si = float(np.std(mat[:, i], ddof=1))
                sj = float(np.std(mat[:, j], ddof=1))
                c = float(np.corrcoef(mat[:, i], mat[:, j])[0, 1]) if (si > 1e-12 and sj > 1e-12) else 0.0
                row_map[str(names[j])] = round(c, 4)
        full_corr[str(names[i])] = row_map

        if i == tail_ref_idx:
            tail_corr[str(names[i])] = 1.0
        elif tail_count >= 10:
            xi = mat[tail_mask, tail_ref_idx]
            yi = mat[tail_mask, i]
            both_var = np.std(xi, ddof=1) > 1e-12 and np.std(yi, ddof=1) > 1e-12
            c_t = float(np.corrcoef(xi, yi)[0, 1]) if both_var else 0.0
            tail_corr[str(names[i])] = round(c_t, 4)
        else:
            tail_corr[str(names[i])] = 0.0

    return {
        "full_sample": full_corr,
        "tail_ref_sleeve": str(names[tail_ref_idx]),
        "tail_quantile": float(tail_quantile),
        "tail_days_count": tail_count,
        "worst_5pct_tail_corr_vs_ref": tail_corr,
    }


def simulate_monthly_rebalanced_portfolio(
    dates: Sequence[str],
    mat: np.ndarray,
    weights: np.ndarray,
    rebal_costs_bps: Sequence[float],
    *,
    cex_indices: Sequence[int] = (),
    max_cex_cap: float = MAX_CEX_GROUP_CAP,
) -> tuple[np.ndarray, dict[str, Any]]:
    """Simulate causal Monthly_1st rebalanced portfolio with 2-leg cost (`sum(|Δw_i| * c_i)`) and CEX cap check."""
    w_target = np.asarray(weights, dtype=np.float64)
    if w_target.ndim != 1 or w_target.size != mat.shape[1]:
        raise ValueError("weights length must match mat columns")
    if np.any(w_target < -1e-12) or abs(float(np.sum(w_target)) - 1.0) > 1e-6:
        raise ValueError(f"weights must be non-negative and sum to 1.0, got {w_target.tolist()}")

    cex_sum = float(sum(w_target[idx] for idx in cex_indices))
    if cex_sum > max_cex_cap + 1e-6:
        raise ValueError(f"CEX_CAP_VIOLATION: combined CEX weight {cex_sum:.4f} exceeds hard cap {max_cex_cap:.4f}")

    costs_frac = np.asarray(rebal_costs_bps, dtype=np.float64) / 10_000.0
    w_cur = w_target.copy()
    out = np.zeros(len(dates), dtype=np.float64)
    prev_ym = str(dates[0])[:7]
    total_turnover = 0.0
    n_rebals = 0

    for t in range(len(dates)):
        ym = str(dates[t])[:7]
        tc = 0.0
        if t > 0 and ym != prev_ym:
            diff = np.abs(w_target - w_cur)
            total_turnover += 0.5 * float(np.sum(diff))
            tc = float(np.sum(diff * costs_frac))
            n_rebals += 1
            w_cur = w_target.copy()
            prev_ym = ym
        r_vec = mat[t]
        out[t] = float(np.dot(w_cur, r_vec)) - tc
        grown = w_cur * (1.0 + r_vec)
        gs = float(np.sum(grown))
        if gs > 1e-12:
            w_cur = grown / gs

    yrs = max(1.0, float(len(dates)) / 252.0)
    return out, {
        "cex_weight_pct": round(100.0 * cex_sum, 2),
        "rebalance_count": int(n_rebals),
        "annual_turnover_pct": round(100.0 * total_turnover / yrs, 2),
    }


def build_capital_threshold_schedule(
    usd_vnd: float,
    ibkr_audit_by_cap: Mapping[int, dict[str, Any]] | None = None,
) -> list[dict[str, Any]]:
    """Return honest Own-Book capital tiers strictly matching `TOP1-SOLO-QUANT-MASTER-PLAN.md` §3.2."""
    tiers = [
        {
            "tier_id": "TIER_0_UNDER_10K",
            "capital_range_usd": "< 10,000 USD",
            "capital_range_vnd": f"< {round(10_000 * usd_vnd / 1e6, 1):.1f} tr VND",
            "allowed_ownbook_sleeves": ["Cash / T-Bill ngan han (0% ETF, 0% Crypto)"],
            "max_cex_pct": 0.0,
            "prop_role": "FTMO 10K (so sanh song song The5ers HS 5K); uu tien hoan goc 100% + >= 2 payout that",
            "why_honest": (
                "Tranh bay phi toi thieu IBKR 0.35 USD/lenh va sai so lam tron co phieu nguyen "
                "(o 5k USD phi toi thieu va tracking error an mon alpha)."
            ),
            "ibkr_dev_audit_ref": ibkr_audit_by_cap.get(5_000) if ibkr_audit_by_cap else None,
        },
        {
            "tier_id": "TIER_1_10K_TO_25K",
            "capital_range_usd": "10,000 - 25,000 USD",
            "capital_range_vnd": (
                f"{round(10_000 * usd_vnd / 1e6, 1):.1f} - {round(25_000 * usd_vnd / 1e6, 1):.1f} tr VND"
            ),
            "allowed_ownbook_sleeves": ["Macro ETF turnover thap (S3B Risk-Parity / L7_TOP2, 0 swap, bat Fractional)"],
            "max_cex_pct": 0.0,
            "prop_role": "Chay song song PORT_7E (Prop Core) + Macro ETF Own-Book (2 nhanh lech pha)",
            "why_honest": (
                "Macro ETF turnover thap (6-10x/nam, 0 swap, luu ky IBKR) cat manh thang doi ma khong chiu rui ro CEX."
            ),
            "ibkr_dev_audit_ref": ibkr_audit_by_cap.get(10_000) if ibkr_audit_by_cap else None,
        },
        {
            "tier_id": "TIER_2_25K_TO_50K",
            "capital_range_usd": "25,000 - 50,000 USD",
            "capital_range_vnd": (
                f"{round(25_000 * usd_vnd / 1e6, 1):.1f} - {round(50_000 * usd_vnd / 1e6, 1):.1f} tr VND"
            ),
            "allowed_ownbook_sleeves": [
                "Macro ETF (S3B / L7_TOP2, >= 75% Own-Book)",
                "Crypto Spot nhan qua S2 + Funding Carry S3A (tong CEX <= 25%)",
            ],
            "max_cex_pct": 25.0,
            "prop_role": "Hoan thien bo 3 nhanh doc lap (Prop 7E + Crypto Spot/Carry + Macro ETF)",
            "why_honest": (
                "Kich hoat nhanh Crypto chi khi phan <= 25% CEX du lon (>= 6.25k USD) de chia rui ro "
                "va giu >= 75% tai san ngoai san tap trung."
            ),
            "ibkr_dev_audit_ref": ibkr_audit_by_cap.get(25_000) if ibkr_audit_by_cap else None,
        },
        {
            "tier_id": "TIER_3_50K_TO_100K",
            "capital_range_usd": "50,000 - 100,000 USD",
            "capital_range_vnd": (
                f"{round(50_000 * usd_vnd / 1e6, 1):.1f} - {round(100_000 * usd_vnd / 1e6, 1):.1f} tr VND"
            ),
            "allowed_ownbook_sleeves": [
                "Ro ETF day du lo nguyen (SUPER_ETF_6ENG / S4 + L7_TOP2, 0 swap, TE <= 50 bps/yr)",
                "Crypto Spot S2 + Funding Carry S3A (tong CEX <= 25%)",
            ],
            "max_cex_pct": 25.0,
            "prop_role": "Chay sach lo nguyen IBKR khong can Fractional; chuan bi vuot moc Crossover Own-Book vs Prop",
            "why_honest": (
                "Tu 50k USD tro len, ETF lo nguyen dat tracking error thap va chi phi giao dich < 15 bps/nam."
            ),
            "ibkr_dev_audit_ref": ibkr_audit_by_cap.get(50_000) if ibkr_audit_by_cap else None,
        },
        {
            "tier_id": "TIER_4_100K_PLUS",
            "capital_range_usd": ">= 100,000 USD",
            "capital_range_vnd": f">= {round(100_000 * usd_vnd / 1e6, 1):.1f} tr VND",
            "allowed_ownbook_sleeves": [
                "Full Macro ETF + Multi-Factor ETF (IBKR)",
                "Crypto Spot + Carry (CEX <= 25%)",
                "Xem xet CME Micro Futures (khi du margin + phi du lieu)",
            ],
            "max_cex_pct": 25.0,
            "prop_role": "Giam dan phu thuoc luat quy Prop, van hanh da nhanh doc lap kiem toan GIPS-Lite",
            "why_honest": ("Chi xem xet CME Micro Futures tu 100k USD de margin khong bop chet quan tri rui ro."),
            "ibkr_dev_audit_ref": ibkr_audit_by_cap.get(100_000) if ibkr_audit_by_cap else None,
        },
    ]
    return tiers


# ==============================================================================
# END-TO-END SEALED DEV 3-SLEEVE STUDY RUNNER
# ==============================================================================


def _load_usd_vnd_rate(fx_path: Path = DEFAULT_FX_RATES_PATH) -> float:
    if fx_path.is_file():
        data = json.loads(fx_path.read_text(encoding="utf-8"))
        val = float(data["usd_vnd"])
        if math.isfinite(val) and val > 0.0:
            return val
    return 25_765.94


def _build_sleeve1_port7e_dev(cutoff_day: str = HOLDOUT_CUTOFF_DAY) -> dict[str, Any]:
    """Replay Sleeve 1 (`PORT_7E` from `frozen_9e_tapes_v2`) strictly on Dev `<= 2024-12-31`."""
    from quant_factory.data_store import (
        assert_holdout_locked,
        build_or_load_frozen_tapes,
        load_red_news_calendar,
        load_registry,
    )
    from quant_factory.prop_engine import replay_portfolio_m1

    lock_sha = assert_holdout_locked()
    frozen = build_or_load_frozen_tapes(force_rebuild=False)
    ext_days: list[str] = list(frozen["ext_days"])
    tapes = frozen["tapes"]
    enforce_dev_cutoff_strict(ext_days, cutoff_day=cutoff_day, context="sleeve1.ext_days")

    reg = load_registry()
    base_risks = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    core7 = list(reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"])
    r7_1x = {k: base_risks[k] for k in core7}
    r7_125x = {k: base_risks[k] * 1.25 for k in core7}

    news_cal = load_red_news_calendar("red_news_official_2018_2024_6ccy")

    # 1.0x Funded Standard reference (100K avoids 0.01-lot distortion; SYMCAP 1.00%, Red-News ±5m ON)
    met_1x, ex_1x = replay_portfolio_m1(
        ext_days,
        tapes,
        r7_1x,
        100_000.0,
        profile_mode="Standard",
        max_symbol_concurrent_risk=0.010,
        red_news_cal=news_cal,
        news_pad_sec=300,
    )
    by_day_1x = {str(e["day"]): float(e["net_usd"]) / 100_000.0 for e in ex_1x}
    map_1x = {dk: by_day_1x.get(dk, 0.0) for dk in ext_days}
    enforce_dev_cutoff_strict(list(map_1x.keys()), cutoff_day=cutoff_day, context="sleeve1.map_1x")

    # 1.25x C10_NEWS_ON Funded profile (100K Standard, SYMCAP 1.25%, Red-News ±5m ON)
    met_125x, ex_125x = replay_portfolio_m1(
        ext_days,
        tapes,
        r7_125x,
        100_000.0,
        profile_mode="Standard",
        max_symbol_concurrent_risk=0.0125,
        red_news_cal=news_cal,
        news_pad_sec=300,
    )
    by_day_125x = {str(e["day"]): float(e["net_usd"]) / 100_000.0 for e in ex_125x}
    map_125x = {dk: by_day_125x.get(dk, 0.0) for dk in ext_days}
    enforce_dev_cutoff_strict(list(map_125x.keys()), cutoff_day=cutoff_day, context="sleeve1.map_125x")

    n_trades_1x = sum(1 for e in ex_1x for o in e.get("orders", []) if o.get("status") == "SIZED")
    n_trades_125x = sum(1 for e in ex_125x for o in e.get("orders", []) if o.get("status") == "SIZED")

    # Verify zero overnight swap in Sleeve 1 intraday closed trades
    swap_total = sum(float(e.get("swap_usd", 0.0)) for e in ex_1x)
    if abs(swap_total) > 1e-9:
        raise ValueError(f"Sleeve 1 expected swap_usd == 0.0, got {swap_total}")

    return {
        "holdout_lock_sha256": lock_sha,
        "tapes_binding_sha256": frozen["binding_sha256"],
        "ext_days": ext_days,
        "daily_map_1x": map_1x,
        "daily_map_125x": map_125x,
        "replay_meta_1x": {
            "n_trades": int(n_trades_1x),
            "ann_pct": float(met_1x["ann_pct"]["all"]),
            "peak_dd_pct": float(met_1x["peak_dd_pct"]),
            "calmar": float(met_1x["calmar"]),
            "swap_usd": 0.0,
        },
        "replay_meta_125x": {
            "n_trades": int(n_trades_125x),
            "ann_pct": float(met_125x["ann_pct"]["all"]),
            "peak_dd_pct": float(met_125x["peak_dd_pct"]),
            "calmar": float(met_125x["calmar"]),
            "swap_usd": 0.0,
        },
    }


def _build_sleeve2_crypto_dev(
    *,
    cache_dir: Path = DEFAULT_CRYPTO_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Replay causal Crypto Spot Top-15 + Delta-Neutral Funding Carry strictly on Dev `<= 2024-12-31`."""
    from quant_factory.crypto_causal_universe import (
        build_d1_strategies,
        causal_rolling_top_n_mask,
        simulate_spot_backtest,
    )
    from quant_factory.funding_rate_carry import build_carry_strategies, simulate_funding_carry

    spot_panel = load_crypto_spot_dev_panel(cache_dir=cache_dir, cutoff_day=cutoff_day)
    s_dates: list[str] = spot_panel["dates"]
    top15 = causal_rolling_top_n_mask(spot_panel["quote_volume"], spot_panel["close"], lookback_bars=30, top_n=15)
    top10 = causal_rolling_top_n_mask(spot_panel["quote_volume"], spot_panel["close"], lookback_bars=30, top_n=10)
    d1_strats = build_d1_strategies(spot_panel, top15, top10)

    spot_maps_1x: dict[str, dict[str, float]] = {}
    spot_maps_2x: dict[str, dict[str, float]] = {}
    spot_summaries: dict[str, Any] = {}
    for sid in ("F1_TSMOM_D1_L60_VT15", "F2_XSEC_TOP3_BTC100", "F3_DONCHIAN_D1_20_10"):
        if sid not in d1_strats:
            raise ValueError(f"Expected causal crypto strategy {sid!r} missing from build_d1_strategies()")
        _fam, w_mat = d1_strats[sid]
        sim1 = simulate_spot_backtest(spot_panel["close"], w_mat, cost_bps_oneway=15.0)
        sim2 = simulate_spot_backtest(spot_panel["close"], w_mat, cost_bps_oneway=30.0)
        spot_maps_1x[sid] = {d: float(v) for d, v in zip(s_dates, sim1["net_returns"], strict=True)}
        spot_maps_2x[sid] = {d: float(v) for d, v in zip(s_dates, sim2["net_returns"], strict=True)}
        spot_summaries[sid] = {
            "dev_1x_15bps": compute_portfolio_metrics(s_dates, sim1["net_returns"], ann_days=365),
            "dev_2x_30bps": compute_portfolio_metrics(s_dates, sim2["net_returns"], ann_days=365),
        }

    # Causal Funding-Rate Carry (2x equity buffer, real basis MTM, 23 bps / 46 bps pair cost)
    fund_panel = load_crypto_funding_dev_panel(cache_dir=cache_dir, spot_panel=spot_panel, cutoff_day=cutoff_day)
    f_dates: list[str] = fund_panel["dates"]
    carry_strats = build_carry_strategies(fund_panel)

    carry_maps_1x: dict[str, dict[str, float]] = {}
    carry_maps_2x: dict[str, dict[str, float]] = {}
    carry_summaries: dict[str, Any] = {}
    for cid in ("CARRY_TOP5_HYST_2XBUF", "CARRY_NEG_EXIT_ALL20_2XBUF", "CARRY_BTC_ETH_CONS_2XBUF"):
        buf, w_mat = carry_strats[cid]
        sim1 = simulate_funding_carry(
            fund_panel["funding_daily"],
            fund_panel["spot_close"],
            fund_panel["perp_close"],
            fund_panel["perp_high"],
            w_mat,
            spot_high=fund_panel["spot_high"],
            equity_buffer_mult=buf,
            oneway_pair_cost_bps=23.0,
            include_basis_mtm=True,
        )
        sim2 = simulate_funding_carry(
            fund_panel["funding_daily"],
            fund_panel["spot_close"],
            fund_panel["perp_close"],
            fund_panel["perp_high"],
            w_mat,
            spot_high=fund_panel["spot_high"],
            equity_buffer_mult=buf,
            oneway_pair_cost_bps=46.0,
            include_basis_mtm=True,
        )
        carry_maps_1x[cid] = {d: float(v) for d, v in zip(f_dates, sim1["net_returns"], strict=True)}
        carry_maps_2x[cid] = {d: float(v) for d, v in zip(f_dates, sim2["net_returns"], strict=True)}
        carry_summaries[cid] = {
            "dev_1x_23bps": compute_portfolio_metrics(f_dates, sim1["net_returns"], ann_days=365),
            "dev_2x_46bps": compute_portfolio_metrics(f_dates, sim2["net_returns"], ann_days=365),
            "cross_liq_events": int(sim1["cross_liq_events"]),
            "isolated_liq_events": int(sim1["isolated_liq_events"]),
            "max_cross_margin_draw_pct": float(sim1["max_cross_margin_draw_pct"]),
        }

    # Primary Sleeve 2 sub-sleeves: Spot Trend (`F1_TSMOM_D1_L60_VT15`) + Funding Carry (`CARRY_TOP5_HYST_2XBUF`)
    spot_primary_id = "F1_TSMOM_D1_L60_VT15"
    carry_primary_id = "CARRY_TOP5_HYST_2XBUF"
    spot_primary = spot_maps_1x[spot_primary_id]
    carry_primary = carry_maps_1x[carry_primary_id]
    blend_days = sorted(set(spot_primary.keys()) & set(carry_primary.keys()))
    enforce_dev_cutoff_strict(blend_days, cutoff_day=cutoff_day, context="sleeve2.blend_days")
    blend_1x = {d: 0.50 * spot_primary[d] + 0.50 * carry_primary[d] for d in blend_days}
    blend_2x = {
        d: 0.50 * spot_maps_2x[spot_primary_id][d] + 0.50 * carry_maps_2x[carry_primary_id][d] for d in blend_days
    }

    return {
        "spot_date_range": [s_dates[0], s_dates[-1], len(s_dates)],
        "funding_date_range": [f_dates[0], f_dates[-1], len(f_dates)],
        "excluded_post_cutoff_rows": int(
            spot_panel["excluded_post_cutoff_rows"] + fund_panel["excluded_post_cutoff_rows"]
        ),
        "spot_summaries": spot_summaries,
        "carry_summaries": carry_summaries,
        "spot_primary_id": spot_primary_id,
        "carry_primary_id": carry_primary_id,
        "spot_primary_map_1x": spot_primary,
        "spot_primary_map_2x": spot_maps_2x[spot_primary_id],
        "carry_primary_map_1x": carry_primary,
        "carry_primary_map_2x": carry_maps_2x[carry_primary_id],
        "blend_50_50_map_1x": blend_1x,
        "blend_50_50_map_2x": blend_2x,
    }


def _build_sleeve3_macro_etf_dev(
    *,
    macro_cache_dir: Path = DEFAULT_MACRO_ETF_CACHE,
    etf40_cache_dir: Path = DEFAULT_ETF40_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Replay Long-Only 0-swap Macro ETF sleeves (`S3B`, `L7_TOP2`, `S4`, `SUPER_ETF_6ENG`) strictly `<= 2024-12-31`."""
    from quant_factory.etf40_multifactor_vrp_lab import build_etf40_strategies
    from quant_factory.macro_etf_trend import build_macro_strategies, simulate_etf_weights
    from quant_factory.ownbook_etf_super_sleeve import (
        LAB4_APPROVED_IDS,
        SUPER_6_IDS,
        simulate_ibkr_integer_shares,
    )

    from experiments.lab7_overnight_macro_rd_loop import (
        build_lab7_candidates,
        simulate_etf_daily_or_overnight,
    )

    # Part A: 12-ETF Macro Cache (`S3B` Risk-Parity Trend-Guard, All-Weather, Dual Momentum)
    macro_panel = load_macro_etf_dev_panel(cache_dir=macro_cache_dir, cutoff_day=cutoff_day)
    m_dates: list[str] = macro_panel["dates"]
    m_strats = build_macro_strategies(macro_panel)

    etf_maps_1x: dict[str, dict[str, float]] = {}
    etf_maps_2x: dict[str, dict[str, float]] = {}
    etf_summaries: dict[str, Any] = {}

    for sid, label in (
        ("M5_VOL_PARITY_TREND_GUARD", "S3B_RISK_PARITY_TREND_GUARD"),
        ("M4_ALL_WEATHER_VOL_PARITY", "S3B_ALL_WEATHER_PURE"),
        ("M3_DUAL_MOMENTUM_TOP3", "S3B_DUAL_MOMENTUM_TOP3"),
    ):
        _fam, max_lev, w_mat = m_strats[sid]
        if float(np.nanmin(w_mat)) < -1e-12:
            raise ValueError(f"Macro ETF sleeve {label} violated Long-Only 0-swap invariant")
        sim1 = simulate_etf_weights(
            macro_panel["adjclose"], w_mat, cost_bps_oneway=5.0, short_borrow_bps_yr=0.0, max_gross_leverage=max_lev
        )
        sim2 = simulate_etf_weights(
            macro_panel["adjclose"], w_mat, cost_bps_oneway=10.0, short_borrow_bps_yr=0.0, max_gross_leverage=max_lev
        )
        eval_mask = np.array([d >= "2018-01-02" for d in m_dates], dtype=bool)
        eval_dates = [d for d, keep in zip(m_dates, eval_mask, strict=True) if keep]
        turn_yr = float(np.sum(sim1["turnover"][eval_mask])) / max(float(len(eval_dates)) / 252.0, 1e-6)
        etf_maps_1x[label] = {d: float(v) for d, v in zip(m_dates, sim1["net_returns"], strict=True)}
        etf_maps_2x[label] = {d: float(v) for d, v in zip(m_dates, sim2["net_returns"], strict=True)}
        etf_summaries[label] = {
            "source_cache": ".runtime/macro-etf-cache",
            "swap_usd": 0.0,
            "long_only": True,
            "ann_turnover_x": round(turn_yr, 2),
            "dev_2018_2024_1x_5bps": compute_portfolio_metrics(
                eval_dates, sim1["net_returns"][eval_mask], ann_days=252
            ),
            "dev_2018_2024_2x_10bps": compute_portfolio_metrics(
                eval_dates, sim2["net_returns"][eval_mask], ann_days=252
            ),
        }

    # Part B: 40-ETF NYSE Cache (`L7_TOP2`, `S4_LAB4_EQW`, `SUPER_ETF_6ENG_EQW`)
    panel4, panel7 = load_etf40_dev_panels(cache_dir=etf40_cache_dir, cutoff_day=cutoff_day)
    e_dates: list[str] = panel7["dates"]
    strats4 = build_etf40_strategies(panel4)
    cands7 = {c["id"]: c for c in build_lab7_candidates(panel7)}

    eng_w: dict[str, np.ndarray] = {}
    for sid in LAB4_APPROVED_IDS:
        eng_w[sid] = np.asarray(strats4[sid]["weights"], dtype=np.float64)
    for sid in ("L7_B1_MACRO_QUAD_REGIME", "L7_C3_MM17_VAR_MACRO_CORE"):
        eng_w[sid] = np.asarray(cands7[sid]["w"], dtype=np.float64)

    w_l7_top2: np.ndarray = np.asarray(
        0.50 * eng_w["L7_B1_MACRO_QUAD_REGIME"] + 0.50 * eng_w["L7_C3_MM17_VAR_MACRO_CORE"],
        dtype=np.float64,
    )
    w_s4_eqw: np.ndarray = np.asarray(
        np.mean([eng_w[s] for s in LAB4_APPROVED_IDS], axis=0),
        dtype=np.float64,
    )
    w_super6: np.ndarray = np.asarray(
        np.mean([eng_w[s] for s in SUPER_6_IDS], axis=0),
        dtype=np.float64,
    )

    eval_mask40 = np.array([d >= "2018-01-02" for d in e_dates], dtype=bool)
    eval_dates40 = [d for d, keep in zip(e_dates, eval_mask40, strict=True) if keep]
    idx_2018 = int(np.argmax(eval_mask40))

    for label, w_mat in (
        ("L7_TOP2_MACRO_VAR_EQW", w_l7_top2),
        ("S4_ETF40_LAB4_EQW", w_s4_eqw),
        ("SUPER_ETF_6ENG_EQW", w_super6),
    ):
        if float(np.nanmin(w_mat)) < -1e-12:
            raise ValueError(f"ETF40 sleeve {label} violated Long-Only 0-swap invariant")
        s1x = simulate_etf_daily_or_overnight(
            panel7, w_mat, mode="close_to_close", cost_bps_oneway=5.0, short_borrow_ann=0.0, max_gross=1.0
        )
        s2x = simulate_etf_daily_or_overnight(
            panel7, w_mat, mode="close_to_close", cost_bps_oneway=10.0, short_borrow_ann=0.0, max_gross=1.0
        )
        turn_yr = float(np.sum(s1x["turnover"][eval_mask40])) / max(float(len(eval_dates40)) / 252.0, 1e-6)
        etf_maps_1x[label] = {d: float(v) for d, v in zip(e_dates, s1x["net_returns"], strict=True)}
        etf_maps_2x[label] = {d: float(v) for d, v in zip(e_dates, s2x["net_returns"], strict=True)}
        etf_summaries[label] = {
            "source_cache": ".runtime/etf40-cache",
            "swap_usd": 0.0,
            "long_only": True,
            "ann_turnover_x": round(turn_yr, 2),
            "dev_2018_2024_1x_5bps": compute_portfolio_metrics(
                eval_dates40, s1x["net_returns"][eval_mask40], ann_days=252
            ),
            "dev_2018_2024_2x_10bps": compute_portfolio_metrics(
                eval_dates40, s2x["net_returns"][eval_mask40], ann_days=252
            ),
        }

    # IBKR real integer-vs-fractional lot friction audit strictly on Dev 2018-01-02..2024-12-31!
    ibkr_audit: dict[str, list[dict[str, Any]]] = {"L7_TOP2_MACRO_VAR_EQW": [], "SUPER_ETF_6ENG_EQW": []}
    for label, w_mat in (("L7_TOP2_MACRO_VAR_EQW", w_l7_top2), ("SUPER_ETF_6ENG_EQW", w_super6)):
        for cap in (5_000.0, 10_000.0, 25_000.0, 50_000.0, 100_000.0):
            for frac in (False, True):
                ibkr_audit[label].append(
                    simulate_ibkr_integer_shares(
                        e_dates,
                        panel7["adj_close"],
                        panel7["r_cc"],
                        w_mat,
                        initial_capital_usd=cap,
                        fractional_shares=frac,
                        start_idx=idx_2018,
                    )
                )

    return {
        "macro12_date_range": [m_dates[0], m_dates[-1], len(m_dates)],
        "etf40_date_range": [e_dates[0], e_dates[-1], len(e_dates)],
        "excluded_post_cutoff_rows": int(
            macro_panel["excluded_post_cutoff_rows"] + panel7["excluded_post_cutoff_rows"]
        ),
        "summaries": etf_summaries,
        "daily_maps_1x": etf_maps_1x,
        "daily_maps_2x": etf_maps_2x,
        "ibkr_dev_2018_2024_lot_audit": ibkr_audit,
    }


def run_three_sleeve_study(
    *,
    macro_cache_dir: Path = DEFAULT_MACRO_ETF_CACHE,
    etf40_cache_dir: Path = DEFAULT_ETF40_CACHE,
    crypto_cache_dir: Path = DEFAULT_CRYPTO_CACHE,
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
) -> dict[str, Any]:
    """Execute full sealed Dev (`<= 2024-12-31`) 3-sleeve portfolio roadmap study."""
    from quant_factory.portfolio_allocator import weights_erc_lw_cexcap25, weights_nco_cexcap25

    t0 = time.perf_counter()
    if cutoff_day > HOLDOUT_CUTOFF_DAY:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION: cutoff_day={cutoff_day!r} > {HOLDOUT_CUTOFF_DAY}")
    enforce_holdout_zero_rows(HOLDOUT_ROWS_ANALYSED, context="three_sleeve_study_init")

    usd_vnd = _load_usd_vnd_rate()
    s1 = _build_sleeve1_port7e_dev(cutoff_day=cutoff_day)
    s2 = _build_sleeve2_crypto_dev(cache_dir=crypto_cache_dir, cutoff_day=cutoff_day)
    s3 = _build_sleeve3_macro_etf_dev(
        macro_cache_dir=macro_cache_dir,
        etf40_cache_dir=etf40_cache_dir,
        cutoff_day=cutoff_day,
    )

    # --------------------------------------------------------------------------
    # A. 2-Sleeve Overlap (2018-01-02..2024-12-31, 7-yr Dev) -> 10k-25k USD Tier
    # --------------------------------------------------------------------------
    s2sl_maps = {
        "S1_PORT_7E_1X": s1["daily_map_1x"],
        "S3_L7_TOP2_ETF": s3["daily_maps_1x"]["L7_TOP2_MACRO_VAR_EQW"],
        "S3_S3B_RISK_PARITY": s3["daily_maps_1x"]["S3B_RISK_PARITY_TREND_GUARD"],
    }
    days_7y, mat_7y, names_7y = align_daily_sleeves_business_days(
        s2sl_maps, start_day=OVERLAP_START_2SLEEVE, end_day=DEV_MAX_DATE, cutoff_day=cutoff_day
    )
    corr_7y = compute_pairwise_correlations(mat_7y, names_7y, tail_ref_idx=0)

    r_s1_7y = mat_7y[:, 0]
    r_l7_7y = mat_7y[:, 1]
    r_s3b_7y = mat_7y[:, 2]
    r_2sl_l7, meta_2sl_l7 = simulate_monthly_rebalanced_portfolio(
        days_7y, mat_7y[:, [0, 1]], np.array([0.50, 0.50]), [0.0, 5.0]
    )
    r_2sl_s3b, meta_2sl_s3b = simulate_monthly_rebalanced_portfolio(
        days_7y, mat_7y[:, [0, 2]], np.array([0.50, 0.50]), [0.0, 5.0]
    )

    two_sleeve_7yr = {
        "window": f"{days_7y[0]}..{days_7y[-1]} ({len(days_7y)} biz days)",
        "correlations": corr_7y,
        "S1_PORT_7E_1X_ONLY": compute_portfolio_metrics(days_7y, r_s1_7y, ann_days=252),
        "S3_L7_TOP2_ONLY": compute_portfolio_metrics(days_7y, r_l7_7y, ann_days=252),
        "S3_S3B_RISK_PARITY_ONLY": compute_portfolio_metrics(days_7y, r_s3b_7y, ann_days=252),
        "COMBO_50_S1_50_L7_TOP2": {
            **compute_portfolio_metrics(days_7y, r_2sl_l7, ann_days=252),
            **meta_2sl_l7,
        },
        "COMBO_50_S1_50_S3B": {
            **compute_portfolio_metrics(days_7y, r_2sl_s3b, ann_days=252),
            **meta_2sl_s3b,
        },
    }

    # --------------------------------------------------------------------------
    # B. 3-Sleeve Overlap (2020-01-02..2024-12-31, 5-yr Dev) -> 25k+ USD Tier
    #    Sleeves: S1 Prop 7E, S2A Crypto Spot, S2B Funding Carry, S3 Macro ETF
    # --------------------------------------------------------------------------
    sleeve_maps_4 = {
        "S1_PROP_FX_IDX": s1["daily_map_1x"],
        "S2_CRYPTO_SPOT": s2["spot_primary_map_1x"],
        "S3A_FUND_CARRY": s2["carry_primary_map_1x"],
        "S3B_MACRO_ETF": s3["daily_maps_1x"]["L7_TOP2_MACRO_VAR_EQW"],
    }
    days_5y, mat_4, names_4 = align_daily_sleeves_business_days(
        sleeve_maps_4, start_day=OVERLAP_START_3SLEEVE, end_day=DEV_MAX_DATE, cutoff_day=cutoff_day
    )
    corr_4 = compute_pairwise_correlations(mat_4, names_4, tail_ref_idx=0)

    # Also compute exact 3-bucket view: S1 Prop 7E, S2 Crypto Blend (50/50 Spot+Carry), S3 Macro ETF (L7_TOP2 vs S3B)
    sleeve_maps_3_l7 = {
        "S1_PORT_7E": s1["daily_map_1x"],
        "S2_CRYPTO_SPOT_CARRY": s2["blend_50_50_map_1x"],
        "S3_MACRO_L7_TOP2": s3["daily_maps_1x"]["L7_TOP2_MACRO_VAR_EQW"],
    }
    days_3, mat_3_l7, names_3_l7 = align_daily_sleeves_business_days(
        sleeve_maps_3_l7, start_day=OVERLAP_START_3SLEEVE, end_day=DEV_MAX_DATE, cutoff_day=cutoff_day
    )
    corr_3_l7 = compute_pairwise_correlations(mat_3_l7, names_3_l7, tail_ref_idx=0)

    sleeve_maps_3_s3b = {
        "S1_PORT_7E": s1["daily_map_1x"],
        "S2_CRYPTO_SPOT_CARRY": s2["blend_50_50_map_1x"],
        "S3_MACRO_S3B_RP": s3["daily_maps_1x"]["S3B_RISK_PARITY_TREND_GUARD"],
    }
    _d3b, mat_3_s3b, names_3_s3b = align_daily_sleeves_business_days(
        sleeve_maps_3_s3b, start_day=OVERLAP_START_3SLEEVE, end_day=DEV_MAX_DATE, cutoff_day=cutoff_day
    )
    corr_3_s3b = compute_pairwise_correlations(mat_3_s3b, names_3_s3b, tail_ref_idx=0)

    # 2x cost stress matrix on exact same 5-yr overlap
    sleeve_maps_4_2x = {
        "S1_PROP_FX_IDX": s1["daily_map_1x"],  # Sleeve 1 friction stress audited separately (break-even 2.31x)
        "S2_CRYPTO_SPOT": s2["spot_primary_map_2x"],
        "S3A_FUND_CARRY": s2["carry_primary_map_2x"],
        "S3B_MACRO_ETF": s3["daily_maps_2x"]["L7_TOP2_MACRO_VAR_EQW"],
    }
    _, mat_4_2x, _ = align_daily_sleeves_business_days(
        sleeve_maps_4_2x, start_day=OVERLAP_START_3SLEEVE, end_day=DEV_MAX_DATE, cutoff_day=cutoff_day
    )

    train_mask = np.array([d <= DEV_TRAIN_END for d in days_5y], dtype=bool)
    oos_mask = np.array([d >= DEV_OOS_START for d in days_5y], dtype=bool)
    oos_days = [d for d, keep in zip(days_5y, oos_mask, strict=True) if keep]

    # Causal allocators fitted strictly on 2020-2022 (`train_mask`) with HARD CEX <= 25% cap!
    w_erc_cap25 = weights_erc_lw_cexcap25(mat_4[train_mask], sleeve_ids=names_4, single_cap=0.45)
    w_nco_cap25 = weights_nco_cexcap25(mat_4[train_mask], sleeve_ids=names_4, single_cap=0.45)
    w_fixed_40_20_40 = np.array([0.40, 0.10, 0.10, 0.40], dtype=np.float64)
    w_fixed_s3b = np.array([0.40, 0.20, 0.40], dtype=np.float64)

    # Pure Own-Book (NO Prop double-counting!): 75% Macro ETF + 12.5% Crypto Spot + 12.5% Funding Carry (CEX = 25.0%)
    w_ownbook_only = np.array([0.00, 0.125, 0.125, 0.75], dtype=np.float64)

    rebal_costs_4 = [0.0, 15.0, 23.0, 5.0]
    cex_idx_4 = (1, 2)

    portfolios_5y: dict[str, Any] = {}
    portfolio_specs = (
        ("S1_PORT_7E_ONLY", np.array([1.0, 0.0, 0.0, 0.0]), mat_4, mat_4_2x, names_4, rebal_costs_4, cex_idx_4),
        ("THREE_SLEEVE_FIXED_40_20_40_L7", w_fixed_40_20_40, mat_4, mat_4_2x, names_4, rebal_costs_4, cex_idx_4),
        ("THREE_SLEEVE_ERC_CEXCAP25_L7", w_erc_cap25, mat_4, mat_4_2x, names_4, rebal_costs_4, cex_idx_4),
        ("THREE_SLEEVE_NCO_CEXCAP25_L7", w_nco_cap25, mat_4, mat_4_2x, names_4, rebal_costs_4, cex_idx_4),
        ("OWNBOOK_ONLY_75ETF_25CRYPTO", w_ownbook_only, mat_4, mat_4_2x, names_4, rebal_costs_4, cex_idx_4),
    )

    for pid, w_vec, m1x, m2x, nms, r_bps, c_idx in portfolio_specs:
        r_full_1x, r_meta = simulate_monthly_rebalanced_portfolio(
            days_5y, m1x, w_vec, r_bps, cex_indices=c_idx, max_cex_cap=MAX_CEX_GROUP_CAP
        )
        r_full_2x, _ = simulate_monthly_rebalanced_portfolio(
            days_5y, m2x, w_vec, [2.0 * x for x in r_bps], cex_indices=c_idx, max_cex_cap=MAX_CEX_GROUP_CAP
        )
        portfolios_5y[pid] = {
            "weights_pct": {nms[i]: round(100.0 * float(w_vec[i]), 2) for i in range(len(nms))},
            **r_meta,
            "full_dev_2020_2024_1x": compute_portfolio_metrics(days_5y, r_full_1x, ann_days=252),
            "full_dev_2020_2024_2x_ob_stress": compute_portfolio_metrics(days_5y, r_full_2x, ann_days=252),
            "dev_oos_2023_2024_1x": compute_portfolio_metrics(oos_days, r_full_1x[oos_mask], ann_days=252),
            "dev_oos_2023_2024_2x_ob_stress": compute_portfolio_metrics(oos_days, r_full_2x[oos_mask], ann_days=252),
        }

    # Also evaluate 3-sleeve Fixed 40/20/40 using incumbent S3B Risk-Parity Trend-Guard
    r_3_s3b, meta_3_s3b = simulate_monthly_rebalanced_portfolio(
        days_3, mat_3_s3b, w_fixed_s3b, [0.0, 19.0, 5.0], cex_indices=(1,), max_cex_cap=MAX_CEX_GROUP_CAP
    )
    portfolios_5y["THREE_SLEEVE_FIXED_40_20_40_S3B"] = {
        "weights_pct": {names_3_s3b[i]: round(100.0 * float(w_fixed_s3b[i]), 2) for i in range(len(names_3_s3b))},
        **meta_3_s3b,
        "full_dev_2020_2024_1x": compute_portfolio_metrics(days_3, r_3_s3b, ann_days=252),
        "dev_oos_2023_2024_1x": compute_portfolio_metrics(oos_days, r_3_s3b[oos_mask], ann_days=252),
    }

    # Individual 5-yr sleeve standalone metrics on exact identical business-day grid
    individual_5y = {
        names_4[i]: compute_portfolio_metrics(days_5y, mat_4[:, i], ann_days=252) for i in range(len(names_4))
    }
    individual_5y["S2_CRYPTO_BLEND_50_50"] = compute_portfolio_metrics(days_3, mat_3_l7[:, 1], ann_days=252)
    individual_5y["S3_MACRO_S3B_RP"] = compute_portfolio_metrics(days_3, mat_3_s3b[:, 2], ann_days=252)

    # Extract concise IBKR integer vs fractional summary per capital tier on L7_TOP2
    ibkr_by_cap: dict[int, dict[str, Any]] = {}
    for row in s3["ibkr_dev_2018_2024_lot_audit"]["L7_TOP2_MACRO_VAR_EQW"]:
        cap_i = int(row["capital_usd"])
        mode_k = "fractional_on" if row["fractional_shares"] else "integer_off"
        ibkr_by_cap.setdefault(cap_i, {})[mode_k] = {
            "orders_per_yr": row["orders_per_yr"],
            "total_cost_bps_yr": row["total_cost_bps_yr"],
            "tracking_error_bps_yr": row["tracking_error_bps_yr"],
            "extra_idle_cash_pct": row["extra_idle_cash_pct"],
            "net_cagr_pct": row["net_cagr_pct"],
            "net_sharpe": row["net_sharpe"],
            "clean_without_fractional": row["clean_without_fractional"],
        }

    capital_tiers = build_capital_threshold_schedule(usd_vnd, ibkr_by_cap)

    total_excluded = int(s2["excluded_post_cutoff_rows"] + s3["excluded_post_cutoff_rows"])
    enforce_holdout_zero_rows(HOLDOUT_ROWS_ANALYSED, context="three_sleeve_study_final")

    return {
        "schema_version": "naqex-three-sleeve-top1-roadmap-v1",
        "generated_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "evidence_stage": "DEV_BACKTEST_2018_2024_STRICT_PRE_HOLDOUT_NOT_BLIND_2025",
        "dev_cutoff_day": cutoff_day,
        "dev_max_date_observed": DEV_MAX_DATE,
        "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
        "post_cutoff_cache_rows_excluded_before_analysis": total_excluded,
        "order_send_count": ORDER_SEND_COUNT,
        "usd_vnd_rate": usd_vnd,
        "holdout_lock_sha256": s1["holdout_lock_sha256"],
        "tapes_binding_sha256": s1["tapes_binding_sha256"],
        "sleeve1_prop7e": {
            "replay_meta_1x": s1["replay_meta_1x"],
            "replay_meta_125x": s1["replay_meta_125x"],
            "dev_2018_2024_1x": compute_portfolio_metrics(
                s1["ext_days"],
                np.array([s1["daily_map_1x"][d] for d in s1["ext_days"]], dtype=np.float64),
                ann_days=252,
            ),
            "dev_2018_2024_125x": compute_portfolio_metrics(
                s1["ext_days"],
                np.array([s1["daily_map_125x"][d] for d in s1["ext_days"]], dtype=np.float64),
                ann_days=252,
            ),
        },
        "sleeve2_crypto_dev": {
            "spot_date_range": s2["spot_date_range"],
            "funding_date_range": s2["funding_date_range"],
            "spot_primary_id": s2["spot_primary_id"],
            "carry_primary_id": s2["carry_primary_id"],
            "spot_summaries": s2["spot_summaries"],
            "carry_summaries": s2["carry_summaries"],
        },
        "sleeve3_macro_etf_dev": {
            "macro12_date_range": s3["macro12_date_range"],
            "etf40_date_range": s3["etf40_date_range"],
            "summaries": s3["summaries"],
            "ibkr_dev_2018_2024_lot_audit": s3["ibkr_dev_2018_2024_lot_audit"],
        },
        "two_sleeve_dev_2018_2024": two_sleeve_7yr,
        "three_sleeve_dev_2020_2024": {
            "window": (
                f"{days_5y[0]}..{days_5y[-1]} ({len(days_5y)} biz days; "
                f"train <= {DEV_TRAIN_END}, dev_oos {DEV_OOS_START}..{DEV_MAX_DATE})"
            ),
            "correlations_4sleeve": corr_4,
            "correlations_3sleeve_l7": corr_3_l7,
            "correlations_3sleeve_s3b": corr_3_s3b,
            "individual_sleeves": individual_5y,
            "portfolios": portfolios_5y,
        },
        "capital_thresholds_sec32": capital_tiers,
        "runtime_seconds": round(time.perf_counter() - t0, 3),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="3-Sleeve Top-1% Solo Quant Roadmap Study strictly on sealed Dev <= 2024-12-31."
    )
    parser.add_argument(
        "--cutoff-day",
        type=str,
        default=HOLDOUT_CUTOFF_DAY,
        help="Strict exclusive upper date cutoff (must be <= 2025-01-01).",
    )
    parser.add_argument(
        "--out-json",
        type=Path,
        default=None,
        help="Optional path to persist study summary JSON atomically.",
    )
    args = parser.parse_args(argv)

    result = run_three_sleeve_study(cutoff_day=args.cutoff_day)
    if args.out_json is not None:
        atomic_write_json(args.out_json, result, indent=2, sort_keys=False, ensure_ascii=False)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


__all__ = [
    "DEV_MAX_DATE",
    "DEV_OOS_START",
    "DEV_TRAIN_END",
    "HOLDOUT_ROWS_ANALYSED",
    "HOLDOUT_START_UTC_MS",
    "MAX_CEX_GROUP_CAP",
    "ORDER_SEND_COUNT",
    "align_daily_sleeves_business_days",
    "build_capital_threshold_schedule",
    "compute_monthly_returns",
    "compute_pairwise_correlations",
    "compute_portfolio_metrics",
    "compute_starved_month_stats",
    "enforce_dev_cutoff_strict",
    "load_crypto_funding_dev_panel",
    "load_crypto_spot_dev_panel",
    "load_etf40_dev_panels",
    "load_macro_etf_dev_panel",
    "main",
    "run_three_sleeve_study",
    "simulate_monthly_rebalanced_portfolio",
    "slice_daily_map_pre_holdout",
]


if __name__ == "__main__":
    raise SystemExit(main())
