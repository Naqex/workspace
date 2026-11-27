"""M3.1 & M3.2: Survivorship-Bias-Free Crypto Spot Sleeve #2 (50-Coin Causal Rolling Dollar-Volume Universe).

Strict anti-bias & safety boundaries:
  - Public Binance Spot read-only OHLCV (/api/v3/klines) ONLY — zero API keys, zero OrderSend.
  - Universe includes 50 coins spanning both survivors and declined/delisted historical majors
    (EOS, MKR, WAVES, NEO, XLM, ETC, FIL, ICP, ALGO, VET, COMP, SNX, SUSHI, KSM, IOTA, XTZ, etc.).
  - Zero pre-listing forward-fill; delisted coins incur exit turnover + conservative delist slippage haircut.
  - 100% causal rolling 30-day dollar-volume Top-N selector using strictly data <= bar t,
    applied to target weights at t, executed at bar t+1 (t -> t+1 causal shift).
  - Strict Cluster A (2019-01-01 .. 2023-12-31) -> blind Cluster B (2024-01-01 .. 2026-11-23) split.
  - Realistic spot friction (1x = 15 bps one-way = 10 bps fee + 5 bps slip; 2x stress = 30 bps one-way).
  - Benjamini-Hochberg FDR across full pre-registered catalog m_total + Deflated Sharpe Ratio (DSR).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime
from pathlib import Path
from statistics import NormalDist
from typing import Any, overload

import httpx
import numpy as np
import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_core.io_utils import atomic_write_json, repo_root_from, sha256_file  # noqa: E402

ROOT = repo_root_from(__file__)
QUANT_LAB_SRC = ROOT / "projects" / "quant-trading" / "src"
if str(QUANT_LAB_SRC) not in sys.path:
    sys.path.insert(0, str(QUANT_LAB_SRC))

try:
    from quant_lab.causal_universe import (  # noqa: E402
        _apply_rebalance_deadband as _quant_lab_apply_rebalance_deadband,
    )
    from quant_lab.causal_universe import (  # noqa: E402
        _causal_ema_matrix as _quant_lab_causal_ema_matrix,
    )
    from quant_lab.causal_universe import (  # noqa: E402
        causal_rolling_top_n_mask as _quant_lab_causal_rolling_top_n_mask,
    )
except ModuleNotFoundError:  # Fallback when projects/quant-trading submodule pin predates causal_universe.py
    def _quant_lab_causal_ema_matrix(closes: np.ndarray, span: int) -> np.ndarray:
        n_t, n_k = closes.shape
        out = np.full((n_t, n_k), np.nan, dtype=np.float64)
        alpha = 2.0 / (span + 1.0)
        for j in range(n_k):
            prev = np.nan
            valid_streak = 0
            for t in range(n_t):
                c = closes[t, j]
                if not np.isfinite(c) or c <= 0.0:
                    prev = np.nan
                    valid_streak = 0
                    continue
                prev = c if not np.isfinite(prev) else (alpha * c + (1.0 - alpha) * prev)
                valid_streak += 1
                if valid_streak >= span:
                    out[t, j] = prev
        return out

    def _quant_lab_apply_rebalance_deadband(raw_w: np.ndarray, deadband: float) -> np.ndarray:
        if isinstance(deadband, bool) or not math.isfinite(float(deadband)) or float(deadband) < 0.0:
            raise ValueError("deadband must be a finite float >= 0.0.")
        db = float(deadband)
        if db == 0.0:
            return raw_w.copy()
        out = np.zeros_like(raw_w)
        prev = np.zeros(raw_w.shape[1], dtype=np.float64)
        for t in range(len(raw_w)):
            cur = raw_w[t]
            flip = (cur == 0.0) != (prev == 0.0)
            upd = np.where(flip | (np.abs(cur - prev) >= db), cur, prev)
            total = float(upd.sum())
            if total > 1.0:
                upd = upd / total
            out[t] = upd
            prev = upd
        return out

    def _quant_lab_causal_rolling_top_n_mask(
        quote_volume: pd.DataFrame,
        close: pd.DataFrame,
        *,
        lookback_bars: int = 30,
        top_n: int = 15,
        min_valid_frac: float = 0.90,
    ) -> pd.DataFrame:
        if quote_volume.empty or close.empty:
            raise ValueError("quote_volume and close panels cannot be empty.")
        if not quote_volume.index.equals(close.index) or list(quote_volume.columns) != list(close.columns):
            raise ValueError("quote_volume and close must share identical index and columns.")
        if type(lookback_bars) is not int or lookback_bars < 1 or type(top_n) is not int or top_n < 1:
            raise ValueError("lookback_bars and top_n must be positive integers.")
        if isinstance(min_valid_frac, bool) or not 0.0 < float(min_valid_frac) <= 1.0:
            raise ValueError("min_valid_frac must be in (0, 1].")
        qv = quote_volume.to_numpy(dtype=np.float64, copy=False)
        cl = close.to_numpy(dtype=np.float64, copy=False)
        n_t, n_k = qv.shape
        cols = [str(col) for col in close.columns]
        mask = np.zeros((n_t, n_k), dtype=bool)
        min_req = max(1, int(math.ceil(lookback_bars * float(min_valid_frac))))
        for t in range(lookback_bars - 1, n_t):
            win = qv[t - lookback_bars + 1 : t + 1]
            valid_cnt = np.sum(np.isfinite(win) & (win > 0.0), axis=0)
            cur_ok = (
                np.isfinite(cl[t])
                & (cl[t] > 0.0)
                & np.isfinite(qv[t])
                & (qv[t] > 0.0)
                & (valid_cnt >= min_req)
            )
            if not np.any(cur_ok):
                continue
            safe = np.where(np.isfinite(win) & (win > 0.0), win, 0.0)
            mean_qv = np.where(cur_ok, np.sum(safe, axis=0) / float(lookback_bars), -1.0)
            elig_idx = np.flatnonzero(cur_ok)
            if len(elig_idx) <= top_n:
                mask[t, elig_idx] = True
            else:
                order = sorted(elig_idx.tolist(), key=lambda j: (-float(mean_qv[j]), cols[j]))
                mask[t, order[:top_n]] = True
        return pd.DataFrame(mask, index=close.index, columns=close.columns)

from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio  # noqa: E402

_STD_NORM = NormalDist(0.0, 1.0)

CACHE_DIR = ROOT / ".runtime" / "crypto-spot-cache"
RETURNS_DIR = ROOT / ".runtime" / "quant-pod-returns"
SLEEVE2_RETURNS_PATH = RETURNS_DIR / "sleeve2_crypto_spot.json"

BINANCE_SPOT_BASE = "https://api.binance.com"
START_DATE = "2019-01-01"
CLUSTER_A_END = "2023-12-31"
CLUSTER_B_START = "2024-01-01"

UNIVERSE_50_BASES: tuple[str, ...] = (
    "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "LTC",
    "BCH", "EOS", "NEO", "XLM", "ETC", "DOT", "ATOM", "AVAX", "UNI", "AAVE",
    "FIL", "ALGO", "VET", "ICP", "NEAR", "ARB", "OP", "APT", "SUI", "INJ",
    "MKR", "LDO", "SAND", "MANA", "AXS", "THETA", "GRT", "CRV", "COMP", "SNX",
    "SUSHI", "RUNE", "EGLD", "ZEC", "XTZ", "IOTA", "KSM", "WAVES", "CHZ", "ENJ",
)
UNIVERSE_50_SYMBOLS: tuple[str, ...] = tuple(f"{b}USDT" for b in UNIVERSE_50_BASES)
OLD_5_SYMBOLS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "BNBUSDT", "ADAUSDT", "SOLUSDT")

PARQUET_SCHEMA = pa.schema([
    ("open_time_ms", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("volume", pa.float64()),
    ("quote_volume", pa.float64()),
    ("trades", pa.int64()),
])


# ==============================================================================
# DATA FETCHER & PARQUET CACHE (PUBLIC READ-ONLY, ZERO API KEY)
# ==============================================================================

def _iso_to_ms(iso_date: str) -> int:
    dt = datetime.fromisoformat(iso_date).replace(tzinfo=UTC)
    return int(dt.timestamp() * 1000)


def _ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, UTC).strftime("%Y-%m-%d")


def _fetch_binance_klines_symbol(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
    *,
    timeout: float = 15.0,
) -> tuple[str, str, list[list[Any]], str | None]:
    """Download complete paginated Binance Spot klines [start_ms, end_ms] for one symbol."""
    step_ms = 86_400_000 if interval == "1d" else (4 * 3_600_000 if interval == "4h" else 3_600_000)
    rows: list[list[Any]] = []
    cur = start_ms
    try:
        with httpx.Client(timeout=timeout, headers={"User-Agent": "NaqexQuantResearch/1.0"}) as client:
            while cur <= end_ms:
                params = {
                    "symbol": symbol,
                    "interval": interval,
                    "startTime": cur,
                    "endTime": end_ms,
                    "limit": 1000,
                }
                resp = None
                for attempt in range(4):
                    r = client.get(f"{BINANCE_SPOT_BASE}/api/v3/klines", params=params)
                    if r.status_code == 200:
                        resp = r.json()
                        break
                    if r.status_code in (429, 418, 500, 502, 503):
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    return symbol, interval, rows, f"HTTP_{r.status_code}:{r.text[:100]}"
                if resp is None:
                    return symbol, interval, rows, "MAX_RETRIES_EXCEEDED"
                if not resp:
                    break
                rows.extend(resp)
                last_open = int(resp[-1][0])
                if len(resp) < 1000 or last_open >= end_ms:
                    break
                cur = last_open + step_ms
        # Deduplicate & sort strictly by open_time_ms
        dedup: dict[int, list[Any]] = {}
        for row in rows:
            ot = int(row[0])
            if start_ms <= ot <= end_ms:
                dedup[ot] = row
        ordered = [dedup[k] for k in sorted(dedup)]
        return symbol, interval, ordered, None
    except Exception as exc:
        return symbol, interval, rows, f"EXC:{type(exc).__name__}:{exc}"


def _write_klines_parquet(path: Path, rows: list[list[Any]]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    table = pa.table(
        {
            "open_time_ms": [int(r[0]) for r in rows],
            "open": [float(r[1]) for r in rows],
            "high": [float(r[2]) for r in rows],
            "low": [float(r[3]) for r in rows],
            "close": [float(r[4]) for r in rows],
            "volume": [float(r[5]) for r in rows],
            "quote_volume": [float(r[7]) for r in rows],
            "trades": [int(r[8]) for r in rows],
        },
        schema=PARQUET_SCHEMA,
    )
    pq.write_table(table, path, compression="zstd")
    return sha256_file(path)


def fetch_and_cache_universe(
    *,
    symbols: tuple[str, ...] = UNIVERSE_50_SYMBOLS,
    intervals: tuple[str, ...] = ("1d", "4h"),
    start_date: str = START_DATE,
    end_date: str | None = None,
    cache_dir: Path = CACHE_DIR,
    force_refresh: bool = False,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Fetch public Binance Spot OHLCV for all universe coins and persist Parquet + SHA-256 manifest."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    start_ms = _iso_to_ms(start_date)
    if end_date is None:
        # Use completed UTC day boundary (yesterday 23:59:59 UTC so current partial day is excluded!)
        now_utc = datetime.now(UTC)
        today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=UTC)
        end_ms = int(today_start.timestamp() * 1000) - 1
    else:
        end_ms = _iso_to_ms(end_date) + 86_400_000 - 1

    # Query exchangeInfo once to record TRADING vs BREAK/delisted status
    sym_status: dict[str, str] = {}
    try:
        with httpx.Client(timeout=15.0) as client:
            info = client.get(f"{BINANCE_SPOT_BASE}/api/v3/exchangeInfo").json()
            sym_status = {s["symbol"]: s["status"] for s in info.get("symbols", [])}
    except Exception:
        pass

    tasks: list[tuple[str, str]] = []
    manifest_files: dict[str, dict[str, Any]] = {}
    skipped: list[dict[str, str]] = []

    for iv in intervals:
        iv_dir = cache_dir / iv
        iv_dir.mkdir(parents=True, exist_ok=True)
        for sym in symbols:
            p = iv_dir / f"{sym}.parquet"
            if p.exists() and not force_refresh:
                tbl = pq.read_table(p, columns=["open_time_ms"])
                ot = tbl["open_time_ms"].to_numpy()
                if len(ot) > 0:
                    manifest_files[f"{iv}/{sym}.parquet"] = {
                        "symbol": sym,
                        "interval": iv,
                        "status": sym_status.get(sym, "CACHED"),
                        "rows": int(len(ot)),
                        "first_utc": _ms_to_date(int(ot[0])),
                        "last_utc": _ms_to_date(int(ot[-1])),
                        "sha256": sha256_file(p),
                    }
                    continue
            tasks.append((sym, iv))

    if tasks:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_fetch_binance_klines_symbol, sym, iv, start_ms, end_ms) for sym, iv in tasks]
            for fut in as_completed(futs):
                sym, iv, rows, err = fut.result()
                if err is not None or not rows:
                    skipped.append({"symbol": sym, "interval": iv, "reason": err or "EMPTY_ROWS"})
                    continue
                p = cache_dir / iv / f"{sym}.parquet"
                digest = _write_klines_parquet(p, rows)
                manifest_files[f"{iv}/{sym}.parquet"] = {
                    "symbol": sym,
                    "interval": iv,
                    "status": sym_status.get(sym, "UNKNOWN"),
                    "rows": len(rows),
                    "first_utc": _ms_to_date(int(rows[0][0])),
                    "last_utc": _ms_to_date(int(rows[-1][0])),
                    "sha256": digest,
                }

    manifest = {
        "schema": "naqex-crypto-spot-cache-v1",
        "generated_utc": datetime.now(UTC).isoformat(),
        "source": "Binance Spot Public /api/v3/klines (zero API key)",
        "requested_symbols": list(symbols),
        "start_date": start_date,
        "end_utc_ms": end_ms,
        "files_count": len(manifest_files),
        "skipped": skipped,
        "files": dict(sorted(manifest_files.items())),
    }
    mpath = cache_dir / "manifest.sha256.json"
    atomic_write_json(mpath, manifest, indent=2)
    return manifest


def load_panel_from_cache(
    interval: str,
    *,
    symbols: tuple[str, ...] = UNIVERSE_50_SYMBOLS,
    cache_dir: Path = CACHE_DIR,
) -> dict[str, Any]:
    """Load aligned OHLCV + quote_volume matrices (T x K) with NaN outside actual listing/active range."""
    iv_dir = cache_dir / interval
    loaded_syms: list[str] = []
    raw_tables: dict[str, dict[str, np.ndarray]] = {}
    all_ts_set: set[int] = set()

    for sym in symbols:
        p = iv_dir / f"{sym}.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p)
        ot = tbl["open_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        if len(ot) == 0:
            continue
        loaded_syms.append(sym)
        raw_tables[sym] = {
            "t": ot,
            "o": tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64),
            "h": tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64),
            "l": tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64),
            "c": tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64),
            "qv": tbl["quote_volume"].to_numpy(zero_copy_only=False).astype(np.float64),
        }
        all_ts_set.update(ot.tolist())

    timestamps = np.array(sorted(all_ts_set), dtype=np.int64)
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

    dates = [_ms_to_date(int(t)) for t in timestamps]
    return {
        "interval": interval,
        "symbols": loaded_syms,
        "timestamps_ms": timestamps,
        "dates": dates,
        "open": opens,
        "high": highs,
        "low": lows,
        "close": closes,
        "quote_volume": qvol,
    }


# ==============================================================================
# STRICTLY CAUSAL ROLLING 30-DAY DOLLAR-VOLUME TOP-N UNIVERSE SELECTOR
# ==============================================================================

@overload
def causal_rolling_top_n_mask(
    quote_vol: pd.DataFrame,
    closes: pd.DataFrame,
    *,
    lookback_bars: int = 30,
    top_n: int = 15,
    min_valid_frac: float = 0.90,
) -> pd.DataFrame: ...


@overload
def causal_rolling_top_n_mask(
    quote_vol: np.ndarray,
    closes: np.ndarray,
    *,
    lookback_bars: int = 30,
    top_n: int = 15,
    min_valid_frac: float = 0.90,
) -> np.ndarray: ...


def causal_rolling_top_n_mask(
    quote_vol: np.ndarray | pd.DataFrame,
    closes: np.ndarray | pd.DataFrame,
    *,
    lookback_bars: int = 30,
    top_n: int = 15,
    min_valid_frac: float = 0.90,
) -> np.ndarray | pd.DataFrame:
    """Return boolean mask (T x K) where True iff coin j is in Top-N trailing dollar volume at bar t.

    Delegates strictly to canonical `quant_lab.causal_universe.causal_rolling_top_n_mask`
    (100% causal using data <= bar t, zero pre-listing leakage), accepting both DataFrame
    and legacy 2D NumPy array inputs for full workspace caller compatibility.
    """
    if isinstance(quote_vol, pd.DataFrame) and isinstance(closes, pd.DataFrame):
        return _quant_lab_causal_rolling_top_n_mask(
            quote_vol,
            closes,
            lookback_bars=lookback_bars,
            top_n=top_n,
            min_valid_frac=min_valid_frac,
        )

    qv_arr = np.asarray(quote_vol, dtype=np.float64)
    cl_arr = np.asarray(closes, dtype=np.float64)
    if qv_arr.ndim != 2 or cl_arr.ndim != 2 or qv_arr.shape != cl_arr.shape:
        raise ValueError("quote_vol and closes must be 2D arrays with identical shapes.")
    n_t, n_k = qv_arr.shape
    if n_t == 0 or n_k == 0:
        return np.zeros((n_t, n_k), dtype=bool)

    qv_clean = np.where(np.isfinite(qv_arr) & (qv_arr > 0.0), qv_arr, np.nan)
    cl_clean = np.where(np.isfinite(cl_arr) & (cl_arr > 0.0), cl_arr, np.nan)
    cols = [f"{j:06d}" for j in range(n_k)]
    idx = pd.RangeIndex(n_t)
    mask_df = _quant_lab_causal_rolling_top_n_mask(
        pd.DataFrame(qv_clean, index=idx, columns=cols),
        pd.DataFrame(cl_clean, index=idx, columns=cols),
        lookback_bars=lookback_bars,
        top_n=top_n,
        min_valid_frac=min_valid_frac,
    )
    return mask_df.to_numpy(dtype=bool, copy=False)


# ==============================================================================
# STRICTLY CAUSAL SPOT BACKTEST ENGINE (t -> t+1, DELISTING-SAFE, COST-AWARE)
# ==============================================================================

def simulate_spot_backtest(
    closes: np.ndarray,
    target_w: np.ndarray,
    *,
    cost_bps_oneway: float = 15.0,
    delist_haircut_bps: float = 100.0,
) -> dict[str, Any]:
    """Strictly causal t -> t+1 spot long/cash backtest.

    - target_w[t] (computed from data <= t) becomes held_w[t+1] earning return closes[t+1]/closes[t] - 1.
    - Spot long/cash invariants enforced: target_w >= 0, row sum <= 1.0 + 1e-9.
    - If a held coin disappears (delisted/missing bar at t+1), position is liquidated to 0
      paying exit turnover friction + explicit conservative delist_haircut_bps penalty.
    """
    n_t, n_k = closes.shape
    tw = np.clip(np.nan_to_num(target_w, nan=0.0), 0.0, 1.0)
    row_sums = tw.sum(axis=1, keepdims=True)
    tw = np.where(row_sums > 1.0, tw / np.maximum(row_sums, 1e-12), tw)

    rets = np.zeros((n_t, n_k), dtype=np.float64)
    valid_ret = np.isfinite(closes[1:]) & np.isfinite(closes[:-1]) & (closes[:-1] > 0.0)
    rets[1:][valid_ret] = closes[1:][valid_ret] / closes[:-1][valid_ret] - 1.0

    held_w = np.zeros((n_t, n_k), dtype=np.float64)
    held_w[1:] = tw[:-1]

    # Track forced delisting exits (coin had target weight at t, but next bar close is missing!)
    delist_exit_w = np.zeros((n_t, n_k), dtype=np.float64)
    missing_next = (~valid_ret) & (tw[:-1] > 1e-12)
    delist_exit_w[1:][missing_next] = tw[:-1][missing_next]
    held_w[1:][~valid_ret] = 0.0

    prev_w = np.zeros_like(held_w)
    prev_w[1:] = held_w[:-1]
    turnover = np.sum(np.abs(held_w - prev_w), axis=1)
    cost = turnover * (cost_bps_oneway / 10_000.0) + np.sum(delist_exit_w, axis=1) * (delist_haircut_bps / 10_000.0)
    gross = np.sum(held_w * rets, axis=1)
    net = gross - cost

    return {
        "net_returns": net,
        "gross_returns": gross,
        "turnover": turnover,
        "held_w": held_w,
        "delist_exits_weight_sum": float(np.sum(delist_exit_w)),
    }


def aggregate_4h_to_daily(
    timestamps_ms: np.ndarray,
    r_4h: np.ndarray,
    turnover_4h: np.ndarray,
    exposure_4h: np.ndarray,
) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    """Compound 4H bar returns onto exact UTC calendar days."""
    day_order: list[str] = []
    day_idx: dict[str, int] = {}
    day_prod: list[float] = []
    day_to: list[float] = []
    day_exp_sum: list[float] = []
    day_cnt: list[int] = []

    for ts, rv, to, ex in zip(timestamps_ms, r_4h, turnover_4h, exposure_4h, strict=False):
        dk = _ms_to_date(int(ts))
        idx = day_idx.get(dk)
        if idx is None:
            idx = len(day_order)
            day_idx[dk] = idx
            day_order.append(dk)
            day_prod.append(1.0 + float(rv))
            day_to.append(float(to))
            day_exp_sum.append(float(ex))
            day_cnt.append(1)
        else:
            day_prod[idx] *= 1.0 + float(rv)
            day_to[idx] += float(to)
            day_exp_sum[idx] += float(ex)
            day_cnt[idx] += 1

    daily_ret = np.array([p - 1.0 for p in day_prod], dtype=np.float64)
    daily_to = np.array(day_to, dtype=np.float64)
    daily_exp = np.array([s / max(1, c) for s, c in zip(day_exp_sum, day_cnt, strict=False)], dtype=np.float64)
    return day_order, daily_ret, daily_to, daily_exp


# ==============================================================================
# 5 STRATEGY FAMILIES (PRE-REGISTERED CATALOG, 100% CAUSAL)
# ==============================================================================

def _compute_log_or_simple_rets(closes: np.ndarray) -> np.ndarray:
    rets = np.full_like(closes, np.nan, dtype=np.float64)
    valid = np.isfinite(closes[1:]) & np.isfinite(closes[:-1]) & (closes[:-1] > 0.0)
    rets[1:][valid] = closes[1:][valid] / closes[:-1][valid] - 1.0
    return rets


_causal_ema_matrix = _quant_lab_causal_ema_matrix
_apply_rebalance_deadband = _quant_lab_apply_rebalance_deadband


def build_d1_strategies(
    panel_d1: dict[str, Any],
    top15_mask: np.ndarray,
    top10_mask: np.ndarray,
) -> dict[str, tuple[str, np.ndarray]]:
    """Build D1 strategies across Families 1, 2, 3, 5 + Benchmarks (strictly data <= t)."""
    closes = panel_d1["close"]
    highs = panel_d1["high"]
    lows = panel_d1["low"]
    syms = panel_d1["symbols"]
    n_t, n_k = closes.shape
    rets = _compute_log_or_simple_rets(closes)
    btc_idx = syms.index("BTCUSDT")

    # Benchmarks
    w_btc = np.zeros((n_t, n_k), dtype=np.float64)
    w_btc[np.isfinite(closes[:, btc_idx]), btc_idx] = 1.0

    w_eq15 = np.zeros((n_t, n_k), dtype=np.float64)
    for t in range(n_t):
        elig = top15_mask[t]
        cnt = int(elig.sum())
        if cnt > 0:
            w_eq15[t, elig] = 1.0 / cnt

    # Pre-allocate strategy target weight matrices
    w_tsmom60 = np.zeros((n_t, n_k), dtype=np.float64)
    w_tsmom30 = np.zeros((n_t, n_k), dtype=np.float64)
    w_xsec3_b100 = np.zeros((n_t, n_k), dtype=np.float64)
    w_xsec5_b100 = np.zeros((n_t, n_k), dtype=np.float64)
    w_xsec3_b50 = np.zeros((n_t, n_k), dtype=np.float64)
    w_don20_10 = np.zeros((n_t, n_k), dtype=np.float64)
    w_don40_20 = np.zeros((n_t, n_k), dtype=np.float64)
    w_panic_trend = np.zeros((n_t, n_k), dtype=np.float64)
    w_panic_uncond = np.zeros((n_t, n_k), dtype=np.float64)

    don20_state = np.zeros(n_k, dtype=bool)
    don40_state = np.zeros(n_k, dtype=bool)
    panic_t_hold = np.zeros(n_k, dtype=np.int32)
    panic_u_hold = np.zeros(n_k, dtype=np.int32)

    vt15 = 0.15 / math.sqrt(365.0)
    vt20 = 0.20 / math.sqrt(365.0)

    for t in range(30, n_t):
        elig15 = top15_mask[t]
        elig10 = top10_mask[t]
        n_elig15 = max(1, int(elig15.sum()))

        # BTC macro filters (strictly <= t)
        btc_sma50_ok = (
            t >= 50
            and np.all(np.isfinite(closes[t - 49 : t + 1, btc_idx]))
            and closes[t, btc_idx] > float(np.mean(closes[t - 49 : t + 1, btc_idx]))
        )
        btc_sma100_ok = (
            t >= 100
            and np.all(np.isfinite(closes[t - 99 : t + 1, btc_idx]))
            and closes[t, btc_idx] > float(np.mean(closes[t - 99 : t + 1, btc_idx]))
        )
        btc_sma200_ok = (
            t >= 200
            and np.all(np.isfinite(closes[t - 199 : t + 1, btc_idx]))
            and closes[t, btc_idx] > float(np.mean(closes[t - 199 : t + 1, btc_idx]))
        )

        raw_t60 = np.zeros(n_k, dtype=np.float64)
        raw_t30 = np.zeros(n_k, dtype=np.float64)
        scores_60: list[tuple[float, int, float]] = []
        scores_30: list[tuple[float, int, float]] = []
        raw_d20 = np.zeros(n_k, dtype=np.float64)
        raw_d40 = np.zeros(n_k, dtype=np.float64)
        raw_pt = np.zeros(n_k, dtype=np.float64)
        raw_pu = np.zeros(n_k, dtype=np.float64)

        for j in range(n_k):
            c_now = closes[t, j]
            if not np.isfinite(c_now) or c_now <= 0.0:
                don20_state[j] = False
                don40_state[j] = False
                panic_t_hold[j] = 0
                panic_u_hold[j] = 0
                continue

            r20 = rets[t - 19:t + 1, j]
            if not np.all(np.isfinite(r20)):
                continue
            vol20 = float(np.std(r20, ddof=1))
            if vol20 <= 1e-6:
                continue

            # --- Family 1 & 2 (D1 TSMOM & XSEC on Top-15 causal universe) ---
            if elig15[j]:
                if (
                    t >= 60
                    and np.all(np.isfinite(closes[t - 49 : t + 1, j]))
                    and np.isfinite(closes[t - 60, j])
                    and closes[t - 60, j] > 0
                ):
                    sma50 = float(np.mean(closes[t - 49 : t + 1, j]))
                    ret60 = float(c_now / closes[t - 60, j] - 1.0)
                    if c_now > sma50 and ret60 > 0.0:
                        raw_t60[j] = vt15 / vol20
                        scores_60.append((ret60 / (vol20 * math.sqrt(60.0)), j, vol20))

                if (
                    t >= 30
                    and np.all(np.isfinite(closes[t - 29 : t + 1, j]))
                    and np.isfinite(closes[t - 30, j])
                    and closes[t - 30, j] > 0
                ):
                    sma30 = float(np.mean(closes[t - 29 : t + 1, j]))
                    ret30 = float(c_now / closes[t - 30, j] - 1.0)
                    if c_now > sma30 and ret30 > 0.0:
                        raw_t30[j] = vt20 / vol20
                        scores_30.append((ret30 / (vol20 * math.sqrt(30.0)), j, vol20))

            # --- Family 3 (Donchian 20/10 & 40/20 Breakout) ---
            if t >= 20 and np.all(np.isfinite(highs[t - 20:t, j])) and np.all(np.isfinite(lows[t - 10:t, j])):
                hi20 = float(np.max(highs[t - 20:t, j]))
                lo10 = float(np.min(lows[t - 10:t, j]))
                if don20_state[j]:
                    if c_now < lo10 or not elig15[j]:
                        don20_state[j] = False
                elif elig15[j] and c_now > hi20:
                    don20_state[j] = True
                if don20_state[j]:
                    raw_d20[j] = vt15 / vol20
            else:
                don20_state[j] = False

            if t >= 40 and np.all(np.isfinite(highs[t - 40:t, j])) and np.all(np.isfinite(lows[t - 20:t, j])):
                hi40 = float(np.max(highs[t - 40:t, j]))
                lo20 = float(np.min(lows[t - 20:t, j]))
                if don40_state[j]:
                    if c_now < lo20 or not elig15[j]:
                        don40_state[j] = False
                elif elig15[j] and c_now > hi40:
                    don40_state[j] = True
                if don40_state[j]:
                    raw_d40[j] = vt15 / vol20
            else:
                don40_state[j] = False

            # --- Family 5 (Liquidity-Filtered Panic Reversion on Top-10) ---
            if (
                t >= 5
                and np.all(np.isfinite(closes[t - 4 : t + 1, j]))
                and np.isfinite(closes[t - 3, j])
                and closes[t - 3, j] > 0
            ):
                sma5 = float(np.mean(closes[t - 4 : t + 1, j]))
                ret3 = float(c_now / closes[t - 3, j] - 1.0)
                z3 = ret3 / (vol20 * math.sqrt(3.0))
                coin_sma200_ok = (
                    t >= 200
                    and np.all(np.isfinite(closes[t - 199 : t + 1, j]))
                    and c_now > float(np.mean(closes[t - 199 : t + 1, j]))
                )

                # Trend-gated panic reversion
                if panic_t_hold[j] > 0:
                    if c_now > sma5 or panic_t_hold[j] >= 5 or not elig10[j]:
                        panic_t_hold[j] = 0
                    else:
                        panic_t_hold[j] += 1
                elif elig10[j] and (coin_sma200_ok or btc_sma200_ok) and z3 <= -1.5:
                    panic_t_hold[j] = 1
                if panic_t_hold[j] > 0:
                    raw_pt[j] = (vt15 / vol20) / 5.0

                # Unconditional deeper panic reversion
                if panic_u_hold[j] > 0:
                    if c_now > sma5 or panic_u_hold[j] >= 5 or not elig10[j]:
                        panic_u_hold[j] = 0
                    else:
                        panic_u_hold[j] += 1
                elif elig10[j] and z3 <= -2.0:
                    panic_u_hold[j] = 1
                if panic_u_hold[j] > 0:
                    raw_pu[j] = (vt15 / vol20) / 5.0

        def _cap_scale(arr: np.ndarray, denom: int) -> np.ndarray:
            v = arr / max(1, denom)
            s = float(v.sum())
            return v / s if s > 1.0 else v

        if np.any(raw_t60 > 0):
            w_tsmom60[t] = _cap_scale(raw_t60, n_elig15)
        if np.any(raw_t30 > 0):
            w_tsmom30[t] = _cap_scale(raw_t30, n_elig15)
        if np.any(raw_d20 > 0):
            w_don20_10[t] = _cap_scale(raw_d20, n_elig15)
        if np.any(raw_d40 > 0):
            w_don40_20[t] = _cap_scale(raw_d40, n_elig15)
        if np.any(raw_pt > 0):
            s = float(raw_pt.sum())
            w_panic_trend[t] = raw_pt / s if s > 1.0 else raw_pt
        if np.any(raw_pu > 0):
            s = float(raw_pu.sum())
            w_panic_uncond[t] = raw_pu / s if s > 1.0 else raw_pu

        if btc_sma100_ok and scores_60:
            scores_60.sort(reverse=True)
            for top_k, mat in ((3, w_xsec3_b100), (5, w_xsec5_b100)):
                sel = scores_60[:top_k]
                tmp = np.zeros(n_k, dtype=np.float64)
                for _sc, j, v20 in sel:
                    tmp[j] = (vt15 / v20) / len(sel)
                s = float(tmp.sum())
                mat[t] = tmp / s if s > 1.0 else tmp

        if btc_sma50_ok and scores_30:
            scores_30.sort(reverse=True)
            sel = scores_30[:3]
            tmp = np.zeros(n_k, dtype=np.float64)
            for _sc, j, v20 in sel:
                tmp[j] = (vt15 / v20) / len(sel)
            s = float(tmp.sum())
            w_xsec3_b50[t] = tmp / s if s > 1.0 else tmp

    return {
        "BM_BH_BTC": ("BENCHMARK", w_btc),
        "BM_CAUSAL_EQW15": ("BENCHMARK", w_eq15),
        "F1_TSMOM_D1_L60_VT15": ("TSMOM_VOL_TARGET", w_tsmom60),
        "F1_TSMOM_D1_L30_VT20": ("TSMOM_VOL_TARGET", w_tsmom30),
        "F2_XSEC_TOP3_BTC100": ("XSEC_TOPK_BTC_REGIME", w_xsec3_b100),
        "F2_XSEC_TOP5_BTC100": ("XSEC_TOPK_BTC_REGIME", w_xsec5_b100),
        "F2_XSEC_TOP3_BTC50": ("XSEC_TOPK_BTC_REGIME", w_xsec3_b50),
        "F3_DONCHIAN_D1_20_10": ("DONCHIAN_VOL_BREAKOUT", w_don20_10),
        "F3_DONCHIAN_D1_40_20": ("DONCHIAN_VOL_BREAKOUT", w_don40_20),
        "F5_PANIC_REV_D1_TREND": ("LIQUIDITY_PANIC_REVERSION", w_panic_trend),
        "F5_PANIC_REV_D1_UNCOND": ("LIQUIDITY_PANIC_REVERSION", w_panic_uncond),
    }


def build_4h_strategies(
    panel_4h: dict[str, Any],
    top15_mask_4h: np.ndarray,
    top10_mask_4h: np.ndarray,
) -> dict[str, tuple[str, np.ndarray]]:
    """Build 4H causal strategies across Families 1, 3, 4, 5 (strictly data <= bar t, with rebalance deadband)."""
    closes = panel_4h["close"]
    highs = panel_4h["high"]
    lows = panel_4h["low"]
    syms = panel_4h["symbols"]
    n_t, n_k = closes.shape
    rets = _compute_log_or_simple_rets(closes)
    btc_idx = syms.index("BTCUSDT")

    # Vectorized causal EMAs & rolling stats for fast 4H execution
    ema24 = _causal_ema_matrix(closes, 24)
    ema48 = _causal_ema_matrix(closes, 48)
    ema60 = _causal_ema_matrix(closes, 60)
    ema120 = _causal_ema_matrix(closes, 120)
    ema240 = _causal_ema_matrix(closes, 240)
    ema300 = _causal_ema_matrix(closes, 300)

    # Compute rolling 120-bar (20d) std of 4H returns strictly causally via cumulative sums
    valid_r = np.isfinite(rets)
    r_zero = np.where(valid_r, rets, 0.0)
    cs_cnt = np.cumsum(valid_r.astype(np.int64), axis=0)
    cs_sum = np.cumsum(r_zero, axis=0)
    cs_sq = np.cumsum(r_zero * r_zero, axis=0)

    def _roll_vol(win: int) -> np.ndarray:
        out = np.full((n_t, n_k), np.nan, dtype=np.float64)
        cnt = cs_cnt[win:] - cs_cnt[:-win]
        s1 = cs_sum[win:] - cs_sum[:-win]
        s2 = cs_sq[win:] - cs_sq[:-win]
        full = cnt == win
        mean = s1 / win
        var = np.maximum(0.0, (s2 - win * mean * mean) / max(1, win - 1))
        out[win:] = np.where(full, np.sqrt(var), np.nan)
        return out

    def _roll_sma(mat: np.ndarray, win: int) -> np.ndarray:
        out = np.full_like(mat, np.nan, dtype=np.float64)
        ok = np.isfinite(mat)
        c_cnt = np.cumsum(ok.astype(np.int64), axis=0)
        c_sum = np.cumsum(np.where(ok, mat, 0.0), axis=0)
        cnt = c_cnt[win:] - c_cnt[:-win]
        s1 = c_sum[win:] - c_sum[:-win]
        # Note: index t gets mean of [t-win+1 .. t]
        out[win - 1] = np.where(c_cnt[win - 1] == win, c_sum[win - 1] / win, np.nan)
        out[win:] = np.where(cnt == win, s1 / win, np.nan)
        return out

    vol120 = _roll_vol(120)
    sma180 = _roll_sma(closes, 180)
    sma300 = _roll_sma(closes, 300)
    sma6 = _roll_sma(closes, 6)
    btc_sma1200 = _roll_sma(closes[:, btc_idx:btc_idx + 1], 1200)[:, 0]

    # Rolling Donchian highs/lows (strictly [t-win .. t-1], i.e. prior completed bars before t)
    from numpy.lib.stride_tricks import sliding_window_view
    hi120_prior = np.full((n_t, n_k), np.nan, dtype=np.float64)
    lo60_prior = np.full((n_t, n_k), np.nan, dtype=np.float64)
    if n_t > 120:
        w_h = sliding_window_view(highs[:-1], 120, axis=0)
        hi120_prior[120:] = np.where(np.all(np.isfinite(w_h), axis=2), np.max(w_h, axis=2), np.nan)
        w_l = sliding_window_view(lows[:-1], 60, axis=0)
        lo60_prior[60:] = np.where(np.all(np.isfinite(w_l), axis=2), np.min(w_l, axis=2), np.nan)

    vt15_4h = 0.15 / math.sqrt(365.0 * 6.0)
    inv_vol = np.where(np.isfinite(vol120) & (vol120 > 1e-6), vt15_4h / vol120, 0.0)
    n_elig15 = np.maximum(1, top15_mask_4h.sum(axis=1, keepdims=True))

    # F1 4H TSMOM L180 (30d) & L360 (60d)
    ret180 = np.full_like(closes, np.nan)
    ret180[180:] = closes[180:] / np.where(closes[:-180] > 0, closes[:-180], np.nan) - 1.0
    ret360 = np.full_like(closes, np.nan)
    ret360[360:] = closes[360:] / np.where(closes[:-360] > 0, closes[:-360], np.nan) - 1.0

    sig_t180 = top15_mask_4h & np.isfinite(sma180) & (closes > sma180) & (ret180 > 0.0)
    sig_t360 = top15_mask_4h & np.isfinite(sma300) & (closes > sma300) & (ret360 > 0.0)

    def _norm_cap(sig: np.ndarray) -> np.ndarray:
        raw = np.where(sig, inv_vol, 0.0) / n_elig15
        s = raw.sum(axis=1, keepdims=True)
        return np.where(s > 1.0, raw / np.maximum(s, 1e-12), raw)

    w_t180 = _apply_rebalance_deadband(_norm_cap(sig_t180), 0.015)
    w_t360 = _apply_rebalance_deadband(_norm_cap(sig_t360), 0.015)

    # F4 4H Trend EMA Cross
    btc_ema_bull = (ema60[:, btc_idx] > ema300[:, btc_idx])[:, None]
    sig_e24 = top15_mask_4h & btc_ema_bull & (ema24 > ema120)
    sig_e48 = top15_mask_4h & (ema48 > ema240)
    w_e24 = _apply_rebalance_deadband(_norm_cap(sig_e24), 0.015)
    w_e48 = _apply_rebalance_deadband(_norm_cap(sig_e48), 0.015)

    # F3 4H Donchian 120/60 (stateful per coin)
    don_state = np.zeros(n_k, dtype=bool)
    w_don_raw = np.zeros((n_t, n_k), dtype=np.float64)
    for t in range(120, n_t):
        c = closes[t]
        hi = hi120_prior[t]
        lo = lo60_prior[t]
        el = top15_mask_4h[t]
        exit_cond = (~np.isfinite(c)) | (~el) | (np.isfinite(lo) & (c < lo))
        enter_cond = el & np.isfinite(c) & np.isfinite(hi) & (c > hi)
        don_state = np.where(don_state, ~exit_cond, enter_cond)
        if np.any(don_state):
            row = np.where(don_state, inv_vol[t], 0.0) / max(1, int(el.sum()))
            s = float(row.sum())
            w_don_raw[t] = row / s if s > 1.0 else row
    w_don_4h = _apply_rebalance_deadband(w_don_raw, 0.015)

    # F5 4H Panic Flush Reversion
    ret6 = np.full_like(closes, np.nan)
    ret6[6:] = closes[6:] / np.where(closes[:-6] > 0, closes[:-6], np.nan) - 1.0
    z6 = ret6 / np.where(np.isfinite(vol120) & (vol120 > 1e-6), vol120 * math.sqrt(6.0), np.nan)
    hold_cnt = np.zeros(n_k, dtype=np.int32)
    w_p4h = np.zeros((n_t, n_k), dtype=np.float64)
    for t in range(120, n_t):
        btc_ok = np.isfinite(btc_sma1200[t]) and np.isfinite(closes[t, btc_idx]) and closes[t, btc_idx] > btc_sma1200[t]
        el10 = top10_mask_4h[t]
        for j in range(n_k):
            c = closes[t, j]
            if not np.isfinite(c) or not el10[j]:
                hold_cnt[j] = 0
                continue
            if hold_cnt[j] > 0:
                if (np.isfinite(sma6[t, j]) and c > sma6[t, j]) or hold_cnt[j] >= 12:
                    hold_cnt[j] = 0
                else:
                    hold_cnt[j] += 1
            elif btc_ok and np.isfinite(z6[t, j]) and z6[t, j] <= -2.2:
                hold_cnt[j] = 1
        active = hold_cnt > 0
        if np.any(active):
            row = np.where(active, inv_vol[t] / 5.0, 0.0)
            s = float(row.sum())
            w_p4h[t] = row / s if s > 1.0 else row

    return {
        "F1_TSMOM_4H_L180_VT15": ("TSMOM_VOL_TARGET", w_t180),
        "F1_TSMOM_4H_L360_VT15": ("TSMOM_VOL_TARGET", w_t360),
        "F3_DONCHIAN_4H_120_60": ("DONCHIAN_VOL_BREAKOUT", w_don_4h),
        "F4_4H_EMA_24_120_BTC": ("4H_TREND", w_e24),
        "F4_4H_EMA_48_240": ("4H_TREND", w_e48),
        "F5_PANIC_REV_4H_FLUSH": ("LIQUIDITY_PANIC_REVERSION", w_p4h),
    }


def build_old_5coin_baseline(panel_d1: dict[str, Any]) -> dict[str, np.ndarray]:
    """Reproduce exact 2026-11-23 5-coin basket (BTC, ETH, BNB, ADA, SOL) on the same D1 panel for honest comparison."""
    syms = panel_d1["symbols"]
    closes = panel_d1["close"]
    n_t, n_k = closes.shape
    rets = _compute_log_or_simple_rets(closes)
    idxs = [syms.index(s) for s in OLD_5_SYMBOLS if s in syms]
    btc_idx = syms.index("BTCUSDT")

    w_c1 = np.zeros((n_t, n_k), dtype=np.float64)
    w_c2 = np.zeros((n_t, n_k), dtype=np.float64)
    vt15 = 0.15 / math.sqrt(365.0)

    for t in range(100, n_t):
        c1_raw = np.zeros(n_k, dtype=np.float64)
        scores = []
        btc_w100 = closes[t - 99:t + 1, btc_idx]
        btc_bull = bool(np.all(np.isfinite(btc_w100)) and closes[t, btc_idx] > float(np.mean(btc_w100)))
        n_elig = sum(1 for j in idxs if np.isfinite(closes[t - 60, j]))
        for j in idxs:
            w50 = closes[t - 49:t + 1, j]
            c60 = closes[t - 60, j]
            r20 = rets[t - 19:t + 1, j]
            if not (np.all(np.isfinite(w50)) and np.isfinite(c60) and c60 > 0 and np.all(np.isfinite(r20))):
                continue
            v20 = float(np.std(r20, ddof=1))
            if v20 <= 1e-6:
                continue
            ret60 = float(closes[t, j] / c60 - 1.0)
            if closes[t, j] > float(np.mean(w50)) and ret60 > 0.0:
                c1_raw[j] = vt15 / v20
                scores.append((ret60 / (v20 * math.sqrt(60.0)), j, v20))
        if np.any(c1_raw > 0):
            ws = c1_raw / max(1, n_elig)
            s = float(ws.sum())
            w_c1[t] = ws / s if s > 1.0 else ws
        if btc_bull and scores:
            scores.sort(reverse=True)
            top2 = scores[:2]
            tmp = np.zeros(n_k, dtype=np.float64)
            for _sc, j, v20 in top2:
                tmp[j] = (vt15 / v20) / len(top2)
            s = float(tmp.sum())
            w_c2[t] = tmp / s if s > 1.0 else tmp
    return {"OLD5_C1_TSMOM_VOL20": w_c1, "OLD5_C2_XSEC_TOP2": w_c2}


# ==============================================================================
# METRICS, BH-FDR, DSR & SLEEVE RETURN EXPORT
# ==============================================================================

def compute_daily_metrics(
    r: np.ndarray,
    turnover: np.ndarray | None = None,
    exposure: np.ndarray | None = None,
    *,
    ann_days: float = 365.0,
) -> dict[str, Any]:
    arr = np.asarray(r, dtype=np.float64)
    n = len(arr)
    if n < 30:
        return {"n_days": n, "cagr_pct": 0.0, "sharpe": 0.0, "max_dd_pct": 0.0, "calmar": 0.0, "p_one_sided": 1.0}
    eq = np.cumprod(1.0 + arr)
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    dd = (peak - eq) / np.maximum(peak, 1e-12)
    max_dd = float(np.max(dd))
    yrs = n / ann_days
    cagr = float(eq[-1] ** (1.0 / yrs) - 1.0) if eq[-1] > 0 else -1.0
    mu = float(np.mean(arr))
    sd = float(np.std(arr, ddof=1))
    sharpe = (mu / sd * math.sqrt(ann_days)) if sd > 1e-12 else 0.0
    downside = arr[arr < 0.0]
    dsd = float(np.std(downside, ddof=1)) if len(downside) > 2 else sd
    sortino = (mu / dsd * math.sqrt(ann_days)) if dsd > 1e-12 else 0.0
    calmar = (cagr / max_dd) if max_dd > 1e-9 else 0.0
    # One-sided t-stat p-value for H0: mean daily return <= 0 (with Newey-West lag-5 variance correction)
    nw_var = _newey_west_var(arr, max_lag=5)
    se_mu = math.sqrt(max(1e-18, nw_var / n))
    z_stat = mu / se_mu if se_mu > 1e-15 else 0.0
    p_val = float(1.0 - _STD_NORM.cdf(z_stat))
    out = {
        "n_days": n,
        "cagr_pct": round(cagr * 100.0, 2),
        "ann_vol_pct": round(sd * math.sqrt(ann_days) * 100.0, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_dd_pct": round(max_dd * 100.0, 2),
        "calmar": round(calmar, 3),
        "total_ret_pct": round((eq[-1] - 1.0) * 100.0, 2),
        "p_one_sided_nw": round(p_val, 5),
    }
    if turnover is not None:
        out["annual_turnover_x"] = round(float(np.sum(turnover) / max(yrs, 1e-6)), 2)
    if exposure is not None:
        out["time_in_market_pct"] = round(100.0 * float(np.mean(exposure > 1e-6)), 1)
        out["avg_gross_exposure_pct"] = round(100.0 * float(np.mean(exposure)), 1)
    return out


def _newey_west_var(r: np.ndarray, max_lag: int = 5) -> float:
    n = len(r)
    if n < 10:
        return float(np.var(r, ddof=1)) if n > 1 else 1.0
    x = r - float(np.mean(r))
    gamma0 = float(np.dot(x, x) / n)
    var = gamma0
    for lag in range(1, min(max_lag, n - 1) + 1):
        w = 1.0 - lag / (max_lag + 1.0)
        gam = float(np.dot(x[lag:], x[:-lag]) / n)
        var += 2.0 * w * gam
    return max(var, gamma0 * 0.25, 1e-15)


def run_full_study(
    *,
    fetch: bool = True,
    cache_dir: Path = CACHE_DIR,
    returns_out: Path = SLEEVE2_RETURNS_PATH,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    manifest = (
        fetch_and_cache_universe(cache_dir=cache_dir)
        if fetch
        else json.loads((cache_dir / "manifest.sha256.json").read_text(encoding="utf-8"))
    )

    panel_d1 = load_panel_from_cache("1d", cache_dir=cache_dir)
    panel_4h = load_panel_from_cache("4h", cache_dir=cache_dir)

    top15_d1 = causal_rolling_top_n_mask(panel_d1["quote_volume"], panel_d1["close"], lookback_bars=30, top_n=15)
    top10_d1 = causal_rolling_top_n_mask(panel_d1["quote_volume"], panel_d1["close"], lookback_bars=30, top_n=10)
    top15_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=15)
    top10_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=10)

    d1_strats = build_d1_strategies(panel_d1, top15_d1, top10_d1)
    h4_strats = build_4h_strategies(panel_4h, top15_4h, top10_4h)
    old5_strats = build_old_5coin_baseline(panel_d1)

    dates_d1 = panel_d1["dates"]
    mask_a_d1 = np.array([START_DATE <= d <= CLUSTER_A_END for d in dates_d1])
    mask_b_d1 = np.array([d >= CLUSTER_B_START for d in dates_d1])
    mask_all_d1 = np.array([d >= START_DATE for d in dates_d1])

    # Evaluate all strategies on unified UTC daily calendar
    results: dict[str, dict[str, Any]] = {}
    daily_series_1x: dict[str, dict[str, float]] = {}
    candidate_names: list[str] = []

    for name, (fam, w) in d1_strats.items():
        sim1 = simulate_spot_backtest(panel_d1["close"], w, cost_bps_oneway=15.0)
        sim2 = simulate_spot_backtest(panel_d1["close"], w, cost_bps_oneway=30.0)
        exp = sim1["held_w"].sum(axis=1)
        mA1 = compute_daily_metrics(sim1["net_returns"][mask_a_d1], sim1["turnover"][mask_a_d1], exp[mask_a_d1])
        mA2 = compute_daily_metrics(sim2["net_returns"][mask_a_d1], sim2["turnover"][mask_a_d1], exp[mask_a_d1])
        mB1 = compute_daily_metrics(sim1["net_returns"][mask_b_d1], sim1["turnover"][mask_b_d1], exp[mask_b_d1])
        mB2 = compute_daily_metrics(sim2["net_returns"][mask_b_d1], sim2["turnover"][mask_b_d1], exp[mask_b_d1])
        mF1 = compute_daily_metrics(sim1["net_returns"][mask_all_d1], sim1["turnover"][mask_all_d1], exp[mask_all_d1])
        results[name] = {
            "family": fam,
            "timeframe": "1d",
            "cluster_a_1x": mA1,
            "cluster_a_2x": mA2,
            "cluster_b_1x": mB1,
            "cluster_b_2x": mB2,
            "full_1x": mF1,
            "delist_exits_w": round(sim1["delist_exits_weight_sum"], 4),
        }
        daily_series_1x[name] = {
            d: float(rv) for d, rv in zip(dates_d1, sim1["net_returns"], strict=False) if d >= START_DATE
        }
        if fam != "BENCHMARK":
            candidate_names.append(name)

    for name, (fam, w) in h4_strats.items():
        sim1 = simulate_spot_backtest(panel_4h["close"], w, cost_bps_oneway=15.0)
        sim2 = simulate_spot_backtest(panel_4h["close"], w, cost_bps_oneway=30.0)
        exp1 = sim1["held_w"].sum(axis=1)
        d_days, r1_d, to1_d, ex1_d = aggregate_4h_to_daily(
            panel_4h["timestamps_ms"], sim1["net_returns"], sim1["turnover"], exp1
        )
        _, r2_d, to2_d, _ = aggregate_4h_to_daily(
            panel_4h["timestamps_ms"], sim2["net_returns"], sim2["turnover"], exp1
        )
        ma = np.array([START_DATE <= d <= CLUSTER_A_END for d in d_days])
        mb = np.array([d >= CLUSTER_B_START for d in d_days])
        mall = np.array([d >= START_DATE for d in d_days])
        results[name] = {
            "family": fam,
            "timeframe": "4h",
            "cluster_a_1x": compute_daily_metrics(r1_d[ma], to1_d[ma], ex1_d[ma]),
            "cluster_a_2x": compute_daily_metrics(r2_d[ma], to2_d[ma], ex1_d[ma]),
            "cluster_b_1x": compute_daily_metrics(r1_d[mb], to1_d[mb], ex1_d[mb]),
            "cluster_b_2x": compute_daily_metrics(r2_d[mb], to2_d[mb], ex1_d[mb]),
            "full_1x": compute_daily_metrics(r1_d[mall], to1_d[mall], ex1_d[mall]),
            "delist_exits_w": round(sim1["delist_exits_weight_sum"], 4),
        }
        daily_series_1x[name] = {d: float(rv) for d, rv in zip(d_days, r1_d, strict=False) if d >= START_DATE}
        candidate_names.append(name)

    # BH-FDR across ALL m_total pre-registered candidates & DSR (n_trials = m_total)
    m_total = len(candidate_names)
    p_a_list = [results[n]["cluster_a_1x"]["p_one_sided_nw"] for n in candidate_names]
    p_b_list = [results[n]["cluster_b_1x"]["p_one_sided_nw"] for n in candidate_names]
    p_f_list = [results[n]["full_1x"]["p_one_sided_nw"] for n in candidate_names]
    q_a_list = benjamini_hochberg(p_a_list)
    q_b_list = benjamini_hochberg(p_b_list)
    q_f_list = benjamini_hochberg(p_f_list)

    for name, qa, qb, qf in zip(candidate_names, q_a_list, q_b_list, q_f_list, strict=False):
        ser = daily_series_1x[name]
        r_a = np.array([v for d, v in sorted(ser.items()) if START_DATE <= d <= CLUSTER_A_END], dtype=np.float64)
        r_b = np.array([v for d, v in sorted(ser.items()) if d >= CLUSTER_B_START], dtype=np.float64)
        r_f = np.array([v for d, v in sorted(ser.items())], dtype=np.float64)
        results[name]["bh_q_cluster_a"] = round(qa, 5)
        results[name]["bh_q_cluster_b"] = round(qb, 5)
        results[name]["bh_q_full"] = round(qf, 5)
        results[name]["dsr_cluster_a"] = deflated_sharpe_ratio(r_a, n_trials=m_total, annualization=365.0)
        results[name]["dsr_cluster_b"] = deflated_sharpe_ratio(r_b, n_trials=m_total, annualization=365.0)
        results[name]["dsr_full"] = deflated_sharpe_ratio(r_f, n_trials=m_total, annualization=365.0)

    # Old 5-coin survivorship-biased baseline comparison over the EXACT same windows
    old5_results: dict[str, Any] = {}
    for name, w in old5_strats.items():
        sim1 = simulate_spot_backtest(panel_d1["close"], w, cost_bps_oneway=15.0)
        sim2 = simulate_spot_backtest(panel_d1["close"], w, cost_bps_oneway=30.0)
        exp = sim1["held_w"].sum(axis=1)
        old5_results[name] = {
            "cluster_a_1x": compute_daily_metrics(
                sim1["net_returns"][mask_a_d1], sim1["turnover"][mask_a_d1], exp[mask_a_d1]
            ),
            "cluster_a_2x": compute_daily_metrics(
                sim2["net_returns"][mask_a_d1], sim2["turnover"][mask_a_d1], exp[mask_a_d1]
            ),
            "cluster_b_1x": compute_daily_metrics(
                sim1["net_returns"][mask_b_d1], sim1["turnover"][mask_b_d1], exp[mask_b_d1]
            ),
            "cluster_b_2x": compute_daily_metrics(
                sim2["net_returns"][mask_b_d1], sim2["turnover"][mask_b_d1], exp[mask_b_d1]
            ),
            "full_1x": compute_daily_metrics(
                sim1["net_returns"][mask_all_d1], sim1["turnover"][mask_all_d1], exp[mask_all_d1]
            ),
        }

    # Strict Cluster A-ONLY selection (zero peeking at Cluster B!):
    # Select best single strategy on Cluster A by Calmar * Sharpe where 2x cost Sharpe > 0.70 and BH q_A < 0.10
    eligible_a = [
        n for n in candidate_names
        if results[n]["cluster_a_1x"]["sharpe"] > 0.8
        and results[n]["cluster_a_2x"]["sharpe"] > 0.6
        and results[n]["bh_q_cluster_a"] < 0.10
    ]
    if not eligible_a:
        eligible_a = sorted(candidate_names, key=lambda n: results[n]["cluster_a_1x"]["sharpe"], reverse=True)[:3]
    else:
        eligible_a = sorted(eligible_a, key=lambda n: results[n]["cluster_a_1x"]["calmar"], reverse=True)
    primary_selected = eligible_a[0]

    # Diversified Cluster-A-selected 3-family equal-weight ensemble (1 best per top distinct family)
    fam_best: dict[str, str] = {}
    for n in sorted(candidate_names, key=lambda x: results[x]["cluster_a_1x"]["sharpe"], reverse=True):
        f = results[n]["family"]
        if f not in fam_best and results[n]["cluster_a_2x"]["sharpe"] > 0.5:
            fam_best[f] = n
    ens_members = list(fam_best.values())[:3]
    common_days = sorted(set.intersection(*(set(daily_series_1x[m].keys()) for m in ens_members)))
    ens_daily = {d: float(np.mean([daily_series_1x[m][d] for m in ens_members])) for d in common_days}
    ens_arr = np.array([ens_daily[d] for d in common_days], dtype=np.float64)
    ens_ma = np.array([START_DATE <= d <= CLUSTER_A_END for d in common_days])
    ens_mb = np.array([d >= CLUSTER_B_START for d in common_days])
    ensemble_summary = {
        "members_selected_on_cluster_a": ens_members,
        "cluster_a_1x": compute_daily_metrics(ens_arr[ens_ma]),
        "cluster_b_1x": compute_daily_metrics(ens_arr[ens_mb]),
        "full_1x": compute_daily_metrics(ens_arr),
        "dsr_cluster_b": deflated_sharpe_ratio(ens_arr[ens_mb], n_trials=m_total, annualization=365.0),
    }

    # Universe coverage diagnostics (including declined/delisted coins active in Top-15 over time!)
    ever_top15 = [panel_d1["symbols"][j] for j in range(len(panel_d1["symbols"])) if bool(np.any(top15_d1[:, j]))]
    delisted_syms = [
        info["symbol"]
        for k, info in manifest.get("files", {}).items()
        if k.startswith("1d/") and info.get("status") not in ("TRADING", "CACHED")
    ]
    delisted_in_top15 = [s for s in delisted_syms if s in ever_top15]

    # Persist daily return JSON for @risk-auditor (Portfolio Allocator M5.1)
    returns_out.parent.mkdir(parents=True, exist_ok=True)
    sleeve_payload = {
        "schema": "naqex-sleeve-daily-returns-v1",
        "sleeve_id": "sleeve2_crypto_spot",
        "strategy_name": primary_selected,
        "ensemble_name": "CRYPTO_SPOT_3FAM_EQW",
        "generated_utc": datetime.now(UTC).isoformat(),
        "annualization_days": 365.0,
        "calendar_type": "24_7_calendar",
        "cost_assumption": "15 bps one-way (10 bps fee + 5 bps slip) + 100 bps delist haircut",
        "universe_desc": f"{len(panel_d1['symbols'])} Binance Spot USDT coins, causal rolling 30d dollar-volume Top-15",
        "cluster_a_window": [START_DATE, CLUSTER_A_END],
        "cluster_b_window": [CLUSTER_B_START, dates_d1[-1]],
        "metrics_cluster_a": results[primary_selected]["cluster_a_1x"],
        "metrics_cluster_b": results[primary_selected]["cluster_b_1x"],
        "metrics_full": results[primary_selected]["full_1x"],
        "ensemble_summary": ensemble_summary,
        "daily_returns": daily_series_1x[primary_selected],
        "variants": {
            "CRYPTO_SPOT_3FAM_EQW": ens_daily,
            primary_selected: daily_series_1x[primary_selected],
            **{m: daily_series_1x[m] for m in ens_members},
            "BM_BH_BTC": daily_series_1x["BM_BH_BTC"],
            "BM_CAUSAL_EQW15": daily_series_1x["BM_CAUSAL_EQW15"],
        },
    }
    atomic_write_json(returns_out, sleeve_payload, indent=2)

    summary = {
        "schema": "naqex-crypto-sleeve2-survivorship-free-v1",
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "universe_loaded_d1": len(panel_d1["symbols"]),
        "universe_loaded_4h": len(panel_4h["symbols"]),
        "date_range_d1": [dates_d1[0], dates_d1[-1], len(dates_d1)],
        "ever_in_causal_top15_count": len(ever_top15),
        "ever_in_causal_top15": ever_top15,
        "non_trading_delisted_loaded": delisted_syms,
        "delisted_entered_top15": delisted_in_top15,
        "m_total_candidates": m_total,
        "primary_selected_on_cluster_a": primary_selected,
        "ensemble_summary": ensemble_summary,
        "strategies": results,
        "old_5coin_comparison": old5_results,
        "returns_json_path": str(returns_out),
    }
    atomic_write_json(cache_dir / "study_summary.json", summary, indent=2)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M3.1 & M3.2 Survivorship-Bias-Free Crypto Spot Sleeve #2")
    ap.add_argument("--no-fetch", action="store_true", help="Use cached Parquet files without calling Binance API")
    args = ap.parse_args()
    summary = run_full_study(fetch=not args.no_fetch)
    print(json.dumps({
        "elapsed_sec": summary["elapsed_sec"],
        "universe_loaded_d1": summary["universe_loaded_d1"],
        "universe_loaded_4h": summary["universe_loaded_4h"],
        "date_range_d1": summary["date_range_d1"],
        "ever_in_causal_top15_count": summary["ever_in_causal_top15_count"],
        "delisted_entered_top15": summary["delisted_entered_top15"],
        "m_total_candidates": summary["m_total_candidates"],
        "primary_selected_on_cluster_a": summary["primary_selected_on_cluster_a"],
        "ensemble_summary": summary["ensemble_summary"],
        "returns_json_path": summary["returns_json_path"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
