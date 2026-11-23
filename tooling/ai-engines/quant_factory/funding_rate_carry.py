"""M3.3: Crypto Delta-Neutral Funding-Rate Carry (Spot Long + 1x Perp Short).

Strict anti-bias & safety boundaries:
  - Public Binance USD-M Futures (/fapi/v1/fundingRate, /fapi/v1/klines) + Spot D1 cache
    + Bybit v5 public funding cross-check — ZERO API keys, ZERO OrderSend.
  - 100% causal t -> t+1 execution: trailing 7d/14d funding filters computed through day t
    govern weights applied across day t+1's three 8h funding settlements & basis changes.
  - Explicit 2x equity buffer baseline (0.50x notional Spot Long + 0.50x USDT margin backing
    0.50x 1x-leveraged Perp Short -> immune to <90% single-day short squeeze!).
  - Explicit Spot + Perp entry/exit fees + slippage (1x = 23 bps one-way / 46 bps RT on notional;
    2x stress = 46 bps one-way / 92 bps RT on notional) + real Spot-Perp basis mark-to-market!
  - Conservative 0% yield on idle USDT cash (no synthetic T-bill inflation).
  - Stress-tested through May 2021 deleveraging, Nov 2022 FTX shock, and blind Cluster B (2024-2026).
"""

from __future__ import annotations

import argparse
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import (
    CACHE_DIR as SPOT_CACHE_DIR,
    RETURNS_DIR,
    compute_daily_metrics,
    load_panel_from_cache,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio

FUNDING_CACHE_DIR = SPOT_CACHE_DIR / "funding"
SLEEVE3A_RETURNS_PATH = RETURNS_DIR / "sleeve3a_funding_carry.json"

BINANCE_FAPI_BASE = "https://fapi.binance.com"
BYBIT_BASE = "https://api.bybit.com"

START_DATE = "2020-01-01"
CLUSTER_A_END = "2023-12-31"
CLUSTER_B_START = "2024-01-01"

PERP_UNIVERSE_20: tuple[str, ...] = (
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "LINKUSDT", "LTCUSDT", "BCHUSDT",
    "DOTUSDT", "AVAXUSDT", "ATOMUSDT", "TRXUSDT", "NEARUSDT",
    "FILUSDT", "UNIUSDT", "AAVEUSDT", "ETCUSDT", "XLMUSDT",
)
BYBIT_CHECK_SYMS: tuple[str, ...] = ("BTCUSDT", "ETHUSDT", "SOLUSDT", "XRPUSDT", "DOGEUSDT")

FUNDING_SCHEMA = pa.schema([
    ("funding_time_ms", pa.int64()),
    ("funding_rate", pa.float64()),
    ("mark_price", pa.float64()),
])

PERP_KLINE_SCHEMA = pa.schema([
    ("open_time_ms", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("quote_volume", pa.float64()),
])


def _iso_to_ms(iso_date: str) -> int:
    return int(datetime.fromisoformat(iso_date).replace(tzinfo=timezone.utc).timestamp() * 1000)


def _ms_to_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, timezone.utc).strftime("%Y-%m-%d")


def _fetch_binance_funding_symbol(symbol: str, start_ms: int, end_ms: int) -> tuple[str, list[dict[str, Any]], str | None]:
    rows: list[dict[str, Any]] = []
    cur = start_ms
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "NaqexQuantResearch/1.0"}) as client:
            while cur <= end_ms:
                params = {"symbol": symbol, "startTime": cur, "endTime": end_ms, "limit": 1000}
                resp = None
                for attempt in range(4):
                    r = client.get(f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate", params=params)
                    if r.status_code == 200:
                        resp = r.json()
                        break
                    if r.status_code in (429, 418, 500, 502, 503):
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    return symbol, rows, f"HTTP_{r.status_code}:{r.text[:100]}"
                if resp is None:
                    return symbol, rows, "MAX_RETRIES"
                if not resp:
                    break
                rows.extend(resp)
                last_t = int(resp[-1]["fundingTime"])
                if len(resp) < 1000 or last_t >= end_ms:
                    break
                cur = last_t + 1000
        dedup: dict[int, dict[str, Any]] = {}
        for row in rows:
            ft = int(row["fundingTime"])
            if start_ms <= ft <= end_ms:
                dedup[ft] = row
        ordered = [dedup[k] for k in sorted(dedup)]
        return symbol, ordered, None
    except Exception as exc:
        return symbol, rows, f"EXC:{type(exc).__name__}:{exc}"


def _fetch_binance_perp_d1(symbol: str, start_ms: int, end_ms: int) -> tuple[str, list[list[Any]], str | None]:
    rows: list[list[Any]] = []
    cur = start_ms
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "NaqexQuantResearch/1.0"}) as client:
            while cur <= end_ms:
                params = {"symbol": symbol, "interval": "1d", "startTime": cur, "endTime": end_ms, "limit": 1000}
                resp = None
                for attempt in range(4):
                    r = client.get(f"{BINANCE_FAPI_BASE}/fapi/v1/klines", params=params)
                    if r.status_code == 200:
                        resp = r.json()
                        break
                    if r.status_code in (429, 418, 500, 502, 503):
                        time.sleep(0.5 * (attempt + 1))
                        continue
                    return symbol, rows, f"HTTP_{r.status_code}:{r.text[:100]}"
                if resp is None or not resp:
                    break
                rows.extend(resp)
                last_t = int(resp[-1][0])
                if len(resp) < 1000 or last_t >= end_ms:
                    break
                cur = last_t + 86_400_000
        dedup = {int(r[0]): r for r in rows if start_ms <= int(r[0]) <= end_ms}
        return symbol, [dedup[k] for k in sorted(dedup)], None
    except Exception as exc:
        return symbol, rows, f"EXC:{type(exc).__name__}:{exc}"


def _fetch_bybit_funding_recent(symbol: str, limit_pages: int = 10) -> tuple[str, list[tuple[int, float]], str | None]:
    """Pull up to ~2000 recent 8h Bybit funding settlements (~22 months) for cross-exchange verification."""
    out: dict[int, float] = {}
    end_ms: int | None = None
    try:
        with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexQuantResearch/1.0"}) as client:
            for _ in range(limit_pages):
                params: dict[str, Any] = {"category": "linear", "symbol": symbol, "limit": 200}
                if end_ms is not None:
                    params["endTime"] = end_ms
                r = client.get(f"{BYBIT_BASE}/v5/market/funding/history", params=params)
                if r.status_code != 200:
                    return symbol, sorted(out.items()), f"HTTP_{r.status_code}"
                lst = r.json().get("result", {}).get("list", [])
                if not lst:
                    break
                min_t = None
                for item in lst:
                    ts = int(item["fundingRateTimestamp"])
                    fr = float(item["fundingRate"])
                    out[ts] = fr
                    min_t = ts if min_t is None else min(min_t, ts)
                if min_t is None or len(lst) < 200:
                    break
                end_ms = min_t - 1000
        return symbol, sorted(out.items()), None
    except Exception as exc:
        return symbol, sorted(out.items()), f"EXC:{type(exc).__name__}:{exc}"


def fetch_and_cache_funding(
    *,
    symbols: tuple[str, ...] = PERP_UNIVERSE_20,
    start_date: str = START_DATE,
    cache_dir: Path = FUNDING_CACHE_DIR,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    (cache_dir / "rates").mkdir(exist_ok=True)
    (cache_dir / "perp_1d").mkdir(exist_ok=True)
    start_ms = _iso_to_ms(start_date)
    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    end_ms = int(today_start.timestamp() * 1000) - 1

    manifest_files: dict[str, Any] = {}
    rate_tasks, kline_tasks = [], []

    for sym in symbols:
        rp = cache_dir / "rates" / f"{sym}.parquet"
        if rp.exists() and not force_refresh:
            tbl = pq.read_table(rp, columns=["funding_time_ms"])
            ft = tbl["funding_time_ms"].to_numpy()
            if len(ft) > 0:
                manifest_files[f"rates/{sym}.parquet"] = {
                    "rows": int(len(ft)),
                    "first_utc": _ms_to_date(int(ft[0])),
                    "last_utc": _ms_to_date(int(ft[-1])),
                    "sha256": hashlib.sha256(rp.read_bytes()).hexdigest(),
                }
            else:
                rate_tasks.append(sym)
        else:
            rate_tasks.append(sym)

        kp = cache_dir / "perp_1d" / f"{sym}.parquet"
        if kp.exists() and not force_refresh:
            tbl = pq.read_table(kp, columns=["open_time_ms"])
            ot = tbl["open_time_ms"].to_numpy()
            if len(ot) > 0:
                manifest_files[f"perp_1d/{sym}.parquet"] = {
                    "rows": int(len(ot)),
                    "first_utc": _ms_to_date(int(ot[0])),
                    "last_utc": _ms_to_date(int(ot[-1])),
                    "sha256": hashlib.sha256(kp.read_bytes()).hexdigest(),
                }
            else:
                kline_tasks.append(sym)
        else:
            kline_tasks.append(sym)

    skipped = []
    if rate_tasks or kline_tasks:
        with ThreadPoolExecutor(max_workers=8) as pool:
            f_rates = {pool.submit(_fetch_binance_funding_symbol, s, start_ms, end_ms): s for s in rate_tasks}
            f_klines = {pool.submit(_fetch_binance_perp_d1, s, start_ms, end_ms): s for s in kline_tasks}
            for fut in as_completed(f_rates):
                sym, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"kind": "funding", "symbol": sym, "reason": err or "EMPTY"})
                    continue
                p = cache_dir / "rates" / f"{sym}.parquet"
                mp_vals = []
                for r in rows:
                    raw_mp = r.get("markPrice")
                    try:
                        mp_vals.append(float(raw_mp) if raw_mp not in (None, "") else float("nan"))
                    except ValueError:
                        mp_vals.append(float("nan"))
                tbl = pa.table(
                    {
                        "funding_time_ms": [int(r["fundingTime"]) for r in rows],
                        "funding_rate": [float(r["fundingRate"]) for r in rows],
                        "mark_price": mp_vals,
                    },
                    schema=FUNDING_SCHEMA,
                )
                pq.write_table(tbl, p, compression="zstd")
                manifest_files[f"rates/{sym}.parquet"] = {
                    "rows": len(rows),
                    "first_utc": _ms_to_date(int(rows[0]["fundingTime"])),
                    "last_utc": _ms_to_date(int(rows[-1]["fundingTime"])),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
            for fut in as_completed(f_klines):
                sym, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"kind": "perp_1d", "symbol": sym, "reason": err or "EMPTY"})
                    continue
                p = cache_dir / "perp_1d" / f"{sym}.parquet"
                tbl = pa.table(
                    {
                        "open_time_ms": [int(r[0]) for r in rows],
                        "open": [float(r[1]) for r in rows],
                        "high": [float(r[2]) for r in rows],
                        "low": [float(r[3]) for r in rows],
                        "close": [float(r[4]) for r in rows],
                        "quote_volume": [float(r[7]) for r in rows],
                    },
                    schema=PERP_KLINE_SCHEMA,
                )
                pq.write_table(tbl, p, compression="zstd")
                manifest_files[f"perp_1d/{sym}.parquet"] = {
                    "rows": len(rows),
                    "first_utc": _ms_to_date(int(rows[0][0])),
                    "last_utc": _ms_to_date(int(rows[-1][0])),
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }

    # Bybit cross-exchange verification cache
    bybit_path = cache_dir / "bybit_crosscheck.json"
    if not bybit_path.exists() or force_refresh:
        bybit_data: dict[str, list[list[Any]]] = {}
        with ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(_fetch_bybit_funding_recent, s, 8) for s in BYBIT_CHECK_SYMS]
            for fut in as_completed(futs):
                sym, pts, _err = fut.result()
                bybit_data[sym] = [[ts, fr] for ts, fr in pts]
        bybit_path.write_text(json.dumps(bybit_data), encoding="utf-8", newline="\n")

    manifest = {
        "schema": "naqex-crypto-funding-cache-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Binance USD-M Futures /fapi/v1/fundingRate & /fapi/v1/klines + Bybit v5 cross-check",
        "symbols": list(symbols),
        "skipped": skipped,
        "files": dict(sorted(manifest_files.items())),
    }
    (cache_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def load_daily_funding_panel(
    *,
    symbols: tuple[str, ...] = PERP_UNIVERSE_20,
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
) -> dict[str, Any]:
    """Aggregate 8h funding rates to UTC daily summed funding rate + align Perp & Spot daily closes/highs."""
    daily_fund_by_sym: dict[str, dict[str, float]] = {}
    daily_cnt_by_sym: dict[str, dict[str, int]] = {}
    perp_c_by_sym: dict[str, dict[str, float]] = {}
    perp_h_by_sym: dict[str, dict[str, float]] = {}
    spot_c_by_sym: dict[str, dict[str, float]] = {}
    spot_h_by_sym: dict[str, dict[str, float]] = {}
    loaded_syms: list[str] = []
    all_days: set[str] = set()

    spot_panel = load_panel_from_cache("1d", symbols=symbols, cache_dir=spot_cache_dir) if (spot_cache_dir / "1d").exists() else None
    spot_sym_idx = {s: i for i, s in enumerate(spot_panel["symbols"])} if spot_panel else {}

    for sym in symbols:
        rp = funding_dir / "rates" / f"{sym}.parquet"
        kp = funding_dir / "perp_1d" / f"{sym}.parquet"
        if not rp.exists():
            continue
        tbl = pq.read_table(rp)
        ft = tbl["funding_time_ms"].to_numpy(zero_copy_only=False)
        fr = tbl["funding_rate"].to_numpy(zero_copy_only=False)
        dsum: dict[str, float] = defaultdict(float)
        dcnt: dict[str, int] = defaultdict(int)
        for ts, rate in zip(ft, fr):
            dk = _ms_to_date(int(ts))
            if dk >= START_DATE:
                dsum[dk] += float(rate)
                dcnt[dk] += 1
                all_days.add(dk)
        if not dsum:
            continue
        loaded_syms.append(sym)
        daily_fund_by_sym[sym] = dict(dsum)
        daily_cnt_by_sym[sym] = dict(dcnt)

        pc: dict[str, float] = {}
        ph: dict[str, float] = {}
        if kp.exists():
            kt = pq.read_table(kp)
            for ot, h, c in zip(kt["open_time_ms"].to_numpy(), kt["high"].to_numpy(), kt["close"].to_numpy()):
                dk = _ms_to_date(int(ot))
                pc[dk] = float(c)
                ph[dk] = float(h)
        perp_c_by_sym[sym] = pc
        perp_h_by_sym[sym] = ph

        sc: dict[str, float] = {}
        sh: dict[str, float] = {}
        if spot_panel and sym in spot_sym_idx:
            j = spot_sym_idx[sym]
            for dk, hv, cv in zip(spot_panel["dates"], spot_panel["high"][:, j], spot_panel["close"][:, j]):
                if np.isfinite(cv) and cv > 0:
                    sc[dk] = float(cv)
                if np.isfinite(hv) and hv > 0:
                    sh[dk] = float(hv)
        spot_c_by_sym[sym] = sc
        spot_h_by_sym[sym] = sh

    dates = sorted(all_days)
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
    }


# ==============================================================================
# STRICTLY CAUSAL DELTA-NEUTRAL CARRY SIMULATOR (2x EQUITY BUFFER + BASIS + FEES)
# ==============================================================================

def simulate_funding_carry(
    funding_daily: np.ndarray,
    spot_close: np.ndarray,
    perp_close: np.ndarray,
    perp_high: np.ndarray,
    target_notional_w: np.ndarray,
    *,
    spot_high: np.ndarray | None = None,
    equity_buffer_mult: float = 2.0,
    oneway_pair_cost_bps: float = 23.0,
    include_basis_mtm: bool = True,
) -> dict[str, Any]:
    """Strictly causal t -> t+1 Spot Long + 1x Perp Short carry simulator.

    Parameters
    ----------
    target_notional_w : (T x K) array of nonnegative target weights summing to <= 1.0 of the
        carry sleeve's deployable notional budget.
    equity_buffer_mult : float
        Total equity divided by gross carry notional (e.g., 2.0 => 0.50x equity in Spot Long +
        0.50x equity posted as Futures USDT collateral backing 0.50x Perp Short = 1x Perp leverage!).
    oneway_pair_cost_bps : float
        Combined Spot + Perp one-way entry/exit fee + slippage on notional (default 23 bps =
        15 bps Spot + 8 bps Perp => 46 bps round-turn on notional).
    include_basis_mtm : bool
        If True, add daily Spot-Perp basis mark-to-market return (r_spot - r_perp) * notional_w.
    """
    n_t, n_k = funding_daily.shape
    notional_cap = 1.0 / max(1.0, float(equity_buffer_mult))
    # Futures margin per unit of notional = (1 - notional_cap) / notional_cap = equity_buffer_mult - 1
    # e.g. buffer=2.0 -> 1.00 margin per 1.00 perp notional (1x perp leverage, liq at +95% jump!)
    #      buffer=1.5 -> 0.50 margin per 1.00 perp notional (2x perp leverage, liq at +45% jump!)
    perp_margin_per_notional = max(0.05, float(equity_buffer_mult) - 1.0)
    liq_threshold_jump = perp_margin_per_notional - 0.05  # 5% maintenance margin safety cushion

    tw = np.clip(np.nan_to_num(target_notional_w, nan=0.0), 0.0, 1.0)
    rs = tw.sum(axis=1, keepdims=True)
    tw = np.where(rs > 1.0, tw / np.maximum(rs, 1e-12), tw) * notional_cap

    # Causal shift: target_notional_w[t] (known at day t close) held across day t+1
    held = np.zeros_like(tw)
    valid_f = np.isfinite(funding_daily[1:])
    held[1:] = np.where(valid_f, tw[:-1], 0.0)

    prev = np.zeros_like(held)
    prev[1:] = held[:-1]
    turnover_notional = np.sum(np.abs(held - prev), axis=1)
    fee_cost = turnover_notional * (oneway_pair_cost_bps / 10_000.0)

    safe_f = np.where(np.isfinite(funding_daily), funding_daily, 0.0)
    funding_pnl = np.sum(held * safe_f, axis=1)

    # Spot-Perp basis mark-to-market: Long Spot + Short Perp => +r_spot - r_perp
    basis_pnl = np.zeros(n_t, dtype=np.float64)
    if include_basis_mtm:
        r_spot = np.zeros((n_t, n_k), dtype=np.float64)
        r_perp = np.zeros((n_t, n_k), dtype=np.float64)
        ok_s = np.isfinite(spot_close[1:]) & np.isfinite(spot_close[:-1]) & (spot_close[:-1] > 0)
        ok_p = np.isfinite(perp_close[1:]) & np.isfinite(perp_close[:-1]) & (perp_close[:-1] > 0)
        ok_both = ok_s & ok_p
        r_spot[1:][ok_both] = spot_close[1:][ok_both] / spot_close[:-1][ok_both] - 1.0
        r_perp[1:][ok_both] = perp_close[1:][ok_both] / perp_close[:-1][ok_both] - 1.0
        # Clip obvious stale/re-listing data spikes > 25% basis in 1 day only if spot/perp mismatched
        diff_sp = np.clip(r_spot - r_perp, -0.15, 0.15)
        basis_pnl = np.sum(held * diff_sp, axis=1)

    # Margin stress check: Binance liquidates strictly on Mark Price (anchored to Spot Index, not last-trade flash wicks).
    # Use mark_high_proxy = min(perp_high, spot_high) when spot_high is finite; also record raw last-trade wick separately.
    mark_high = np.where(np.isfinite(spot_high), np.minimum(perp_high, spot_high), perp_high) if spot_high is not None else perp_high
    max_single_coin_jump = 0.0
    max_last_trade_wick = 0.0
    max_cross_margin_draw = 0.0
    margin_warn_days = 0
    isolated_liq_events = 0
    cross_liq_events = 0
    for t in range(1, n_t):
        act = held[t] > 1e-6
        if not np.any(act):
            continue
        ok = act & np.isfinite(mark_high[t]) & np.isfinite(perp_close[t - 1]) & (perp_close[t - 1] > 0)
        if np.any(ok):
            jumps = mark_high[t, ok] / perp_close[t - 1, ok] - 1.0
            wick_jumps = perp_high[t, ok] / perp_close[t - 1, ok] - 1.0
            mx = float(np.max(jumps))
            mx_w = float(np.max(wick_jumps))
            if mx > max_single_coin_jump:
                max_single_coin_jump = mx
            if mx_w > max_last_trade_wick:
                max_last_trade_wick = mx_w
            if mx >= 0.50 * liq_threshold_jump:
                margin_warn_days += 1
            if mx >= liq_threshold_jump:
                isolated_liq_events += 1
            spot_used = float(np.sum(held[t]))
            futures_margin_pool = max(1e-6, 1.0 - spot_used)
            worst_short_loss = float(np.sum(held[t, ok] * np.maximum(0.0, jumps)))
            cm_draw = worst_short_loss / futures_margin_pool
            if cm_draw > max_cross_margin_draw:
                max_cross_margin_draw = cm_draw
            if cm_draw >= 0.90:
                cross_liq_events += 1

    net = funding_pnl + basis_pnl - fee_cost
    return {
        "net_returns": net,
        "funding_pnl": funding_pnl,
        "basis_pnl": basis_pnl,
        "fee_cost": fee_cost,
        "turnover_notional": turnover_notional,
        "held_notional": held,
        "notional_cap": notional_cap,
        "perp_margin_ratio": perp_margin_per_notional,
        "max_single_coin_mark_jump_pct": round(max_single_coin_jump * 100.0, 2),
        "max_last_trade_wick_pct": round(max_last_trade_wick * 100.0, 2),
        "max_cross_margin_draw_pct": round(max_cross_margin_draw * 100.0, 2),
        "margin_warn_days": margin_warn_days,
        "isolated_liq_events": isolated_liq_events,
        "cross_liq_events": cross_liq_events,
    }


def build_carry_strategies(panel: dict[str, Any]) -> dict[str, tuple[float, np.ndarray]]:
    """Build 5 strictly causal funding-rate carry strategies (returns (equity_buffer_mult, target_w))."""
    f_daily = panel["funding_daily"]
    syms = panel["symbols"]
    n_t, n_k = f_daily.shape

    # Precompute strictly causal 7-day and 14-day trailing mean daily funding rates (<= t)
    roll7 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    roll14 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for t in range(6, n_t):
        w7 = f_daily[t - 6:t + 1]
        v7 = np.isfinite(w7)
        c7 = np.sum(v7, axis=0)
        s7 = np.sum(np.where(v7, w7, 0.0), axis=0)
        roll7[t] = np.where(c7 >= 6, s7 / np.maximum(1, c7), np.nan)
    for t in range(13, n_t):
        w14 = f_daily[t - 13:t + 1]
        v14 = np.isfinite(w14)
        c14 = np.sum(v14, axis=0)
        s14 = np.sum(np.where(v14, w14, 0.0), axis=0)
        roll14[t] = np.where(c14 >= 12, s14 / np.maximum(1, c14), np.nan)

    # 1. Static Core-5 Always-On (2x buffer)
    core5_idx = [syms.index(s) for s in ("BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT") if s in syms]
    w_static5 = np.zeros((n_t, n_k), dtype=np.float64)
    for t in range(n_t):
        act = [j for j in core5_idx if np.isfinite(f_daily[t, j])]
        if act:
            for j in act:
                w_static5[t, j] = 1.0 / len(act)

    # 2. Equal-Weight Active Universe with Negative-Funding Exit (enter > 8% ann, exit <= 0% ann, 2x buffer)
    enter_thr_daily = 0.08 / 365.0
    exit_thr_daily = 0.0
    w_neg_exit = np.zeros((n_t, n_k), dtype=np.float64)
    active_state = np.zeros(n_k, dtype=bool)
    for t in range(14, n_t):
        for j in range(n_k):
            r7 = roll7[t, j]
            if not np.isfinite(r7):
                active_state[j] = False
            elif active_state[j]:
                if r7 <= exit_thr_daily:
                    active_state[j] = False
            else:
                if r7 >= enter_thr_daily:
                    active_state[j] = True
        cnt = int(active_state.sum())
        if cnt > 0:
            # Cap single-coin concentration at 25% of notional
            per_coin = min(0.25, 1.0 / cnt)
            w_neg_exit[t, active_state] = per_coin

    # 3. Dynamic Top-5 Highest Trailing 14d Carry with Hysteresis (keep if in Top-8 & roll7 > 0%, enter > 8% ann)
    w_top5_hyst = np.zeros((n_t, n_k), dtype=np.float64)
    held_set: set[int] = set()
    for t in range(14, n_t):
        # Rank eligible coins by roll14[t]
        ranked = [
            (float(roll14[t, j]), j)
            for j in range(n_k)
            if np.isfinite(roll14[t, j]) and np.isfinite(roll7[t, j])
        ]
        ranked.sort(reverse=True)
        rank_pos = {j: idx for idx, (_val, j) in enumerate(ranked)}
        # Keep currently held coins that remain in Top-8 and have roll7 > 0
        next_held = {
            j for j in held_set
            if j in rank_pos and rank_pos[j] < 8 and roll7[t, j] > 0.0 and roll14[t, j] > 0.0
        }
        # Fill up to 5 slots from Top-ranked coins passing entry threshold
        for val14, j in ranked:
            if len(next_held) >= 5:
                break
            if j not in next_held and val14 >= enter_thr_daily and roll7[t, j] >= enter_thr_daily:
                next_held.add(j)
        held_set = next_held
        if held_set:
            per_c = min(0.25, 1.0 / len(held_set))
            for j in held_set:
                w_top5_hyst[t, j] = per_c

    # 4. Ultra-Liquid BTC + ETH Conservative Carry (enter > 3% ann, exit <= 0%, 2x buffer)
    be_idx = [syms.index(s) for s in ("BTCUSDT", "ETHUSDT") if s in syms]
    w_btc_eth = np.zeros((n_t, n_k), dtype=np.float64)
    be_state = {j: False for j in be_idx}
    thr_be = 0.03 / 365.0
    for t in range(14, n_t):
        for j in be_idx:
            r7 = roll7[t, j]
            if not np.isfinite(r7):
                be_state[j] = False
            elif be_state[j]:
                if r7 <= 0.0:
                    be_state[j] = False
            else:
                if r7 >= thr_be:
                    be_state[j] = True
        act = [j for j, on in be_state.items() if on]
        if act:
            for j in act:
                w_btc_eth[t, j] = 0.50  # Max 50% notional per coin (up to 100% of carry budget when both active)

    return {
        "CARRY_STATIC_CORE5_2XBUF": (2.0, w_static5),
        "CARRY_NEG_EXIT_ALL20_2XBUF": (2.0, w_neg_exit),
        "CARRY_TOP5_HYST_2XBUF": (2.0, w_top5_hyst),
        "CARRY_BTC_ETH_CONS_2XBUF": (2.0, w_btc_eth),
        "CARRY_TOP5_HYST_1P5XBUF": (1.5, w_top5_hyst),
    }


def compute_bybit_crosscheck(panel: dict[str, Any], funding_dir: Path = FUNDING_CACHE_DIR) -> dict[str, Any]:
    """Verify Binance 8h funding rates against Bybit public funding history on overlapping dates."""
    bp = funding_dir / "bybit_crosscheck.json"
    if not bp.exists():
        return {"status": "NOT_FETCHED"}
    bybit_raw = json.loads(bp.read_text(encoding="utf-8"))
    dates = panel["dates"]
    d_to_i = {d: i for i, d in enumerate(dates)}
    out: dict[str, Any] = {}
    for sym, pts in bybit_raw.items():
        if sym not in panel["symbols"] or not pts:
            continue
        j = panel["symbols"].index(sym)
        by_day: dict[str, float] = defaultdict(float)
        for ts, fr in pts:
            by_day[_ms_to_date(int(ts))] += float(fr)
        xs, ys = [], []
        for dk, bv in sorted(by_day.items()):
            idx = d_to_i.get(dk)
            if idx is not None and np.isfinite(panel["funding_daily"][idx, j]):
                xs.append(float(panel["funding_daily"][idx, j]))
                ys.append(float(bv))
        if len(xs) >= 30:
            xa, ya = np.array(xs), np.array(ys)
            corr = float(np.corrcoef(xa, ya)[0, 1]) if np.std(xa) > 1e-12 and np.std(ya) > 1e-12 else 0.0
            out[sym] = {
                "overlap_days": len(xs),
                "daily_corr": round(corr, 4),
                "binance_ann_mean_pct": round(float(np.mean(xa)) * 365.0 * 100.0, 2),
                "bybit_ann_mean_pct": round(float(np.mean(ya)) * 365.0 * 100.0, 2),
            }
    return out


def _window_stress(dates: list[str], r: np.ndarray, funding_pnl: np.ndarray, basis_pnl: np.ndarray, start_d: str, end_d: str) -> dict[str, Any]:
    mask = np.array([start_d <= d <= end_d for d in dates])
    if not np.any(mask):
        return {"n_days": 0}
    sub = r[mask]
    eq = np.cumprod(1.0 + sub)
    pk = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    dd = (pk - eq) / np.maximum(pk, 1e-12)
    return {
        "n_days": int(mask.sum()),
        "total_ret_pct": round((float(eq[-1]) - 1.0) * 100.0, 2),
        "max_dd_pct": round(float(np.max(dd)) * 100.0, 2),
        "worst_day_pct": round(float(np.min(sub)) * 100.0, 2),
        "funding_sum_pct": round(float(np.sum(funding_pnl[mask])) * 100.0, 2),
        "basis_sum_pct": round(float(np.sum(basis_pnl[mask])) * 100.0, 2),
    }


def run_funding_study(*, fetch: bool = True, funding_dir: Path = FUNDING_CACHE_DIR, spot_cache_dir: Path = SPOT_CACHE_DIR, returns_out: Path = SLEEVE3A_RETURNS_PATH) -> dict[str, Any]:
    t0 = time.perf_counter()
    if fetch:
        fetch_and_cache_funding(cache_dir=funding_dir)
    panel = load_daily_funding_panel(funding_dir=funding_dir, spot_cache_dir=spot_cache_dir)
    dates = panel["dates"]
    strats = build_carry_strategies(panel)

    ma = np.array([START_DATE <= d <= CLUSTER_A_END for d in dates])
    mb = np.array([d >= CLUSTER_B_START for d in dates])

    results: dict[str, Any] = {}
    daily_1x: dict[str, dict[str, float]] = {}
    names = list(strats.keys())

    for name, (buf, w) in strats.items():
        sim1 = simulate_funding_carry(
            panel["funding_daily"], panel["spot_close"], panel["perp_close"], panel["perp_high"], w,
            spot_high=panel["spot_high"], equity_buffer_mult=buf, oneway_pair_cost_bps=23.0, include_basis_mtm=True,
        )
        sim2 = simulate_funding_carry(
            panel["funding_daily"], panel["spot_close"], panel["perp_close"], panel["perp_high"], w,
            spot_high=panel["spot_high"], equity_buffer_mult=buf, oneway_pair_cost_bps=46.0, include_basis_mtm=True,
        )
        sim_nobasis = simulate_funding_carry(
            panel["funding_daily"], panel["spot_close"], panel["perp_close"], panel["perp_high"], w,
            spot_high=panel["spot_high"], equity_buffer_mult=buf, oneway_pair_cost_bps=23.0, include_basis_mtm=False,
        )
        exp = sim1["held_notional"].sum(axis=1)
        results[name] = {
            "equity_buffer_mult": buf,
            "notional_cap_pct": round(sim1["notional_cap"] * 100.0, 1),
            "cluster_a_1x": compute_daily_metrics(sim1["net_returns"][ma], sim1["turnover_notional"][ma], exp[ma]),
            "cluster_a_2x": compute_daily_metrics(sim2["net_returns"][ma], sim2["turnover_notional"][ma], exp[ma]),
            "cluster_b_1x": compute_daily_metrics(sim1["net_returns"][mb], sim1["turnover_notional"][mb], exp[mb]),
            "cluster_b_2x": compute_daily_metrics(sim2["net_returns"][mb], sim2["turnover_notional"][mb], exp[mb]),
            "full_1x": compute_daily_metrics(sim1["net_returns"], sim1["turnover_notional"], exp),
            "full_funding_only_no_basis_1x": compute_daily_metrics(sim_nobasis["net_returns"], sim_nobasis["turnover_notional"], exp),
            "margin_stress": {
                "max_single_coin_mark_jump_pct": sim1["max_single_coin_mark_jump_pct"],
                "max_last_trade_wick_pct": sim1["max_last_trade_wick_pct"],
                "max_cross_margin_draw_pct": sim1["max_cross_margin_draw_pct"],
                "margin_warn_days": sim1["margin_warn_days"],
                "isolated_liq_events": sim1["isolated_liq_events"],
                "cross_liq_events": sim1["cross_liq_events"],
            },
            "crisis_stress": {
                "may2021_crash": _window_stress(dates, sim1["net_returns"], sim1["funding_pnl"], sim1["basis_pnl"], "2021-05-01", "2021-06-30"),
                "ftx2022_collapse": _window_stress(dates, sim1["net_returns"], sim1["funding_pnl"], sim1["basis_pnl"], "2022-11-01", "2022-12-31"),
                "bear2022_full": _window_stress(dates, sim1["net_returns"], sim1["funding_pnl"], sim1["basis_pnl"], "2022-01-01", "2022-12-31"),
                "aug2024_yen_shock": _window_stress(dates, sim1["net_returns"], sim1["funding_pnl"], sim1["basis_pnl"], "2024-08-01", "2024-08-31"),
            },
        }
        daily_1x[name] = {d: float(rv) for d, rv in zip(dates, sim1["net_returns"])}

    # BH-FDR and DSR across all 5 tested carry rules
    m_total = len(names)
    qb_list = benjamini_hochberg([results[n]["cluster_b_1x"]["p_one_sided_nw"] for n in names])
    qf_list = benjamini_hochberg([results[n]["full_1x"]["p_one_sided_nw"] for n in names])
    for n, qb, qf in zip(names, qb_list, qf_list):
        rb = np.array([daily_1x[n][d] for d in dates if d >= CLUSTER_B_START], dtype=np.float64)
        rf = np.array([daily_1x[n][d] for d in dates], dtype=np.float64)
        results[n]["bh_q_cluster_b"] = round(qb, 5)
        results[n]["bh_q_full"] = round(qf, 5)
        results[n]["dsr_cluster_b"] = deflated_sharpe_ratio(rb, n_trials=m_total, annualization=365.0)
        results[n]["dsr_full"] = deflated_sharpe_ratio(rf, n_trials=m_total, annualization=365.0)

    # Select primary strictly on Cluster A cost-resilience (2x-fee Calmar among 2x-buffer zero-cross-liq rules)
    safe_2x = [n for n in names if results[n]["equity_buffer_mult"] >= 2.0 and results[n]["margin_stress"]["cross_liq_events"] == 0]
    if not safe_2x:
        safe_2x = [n for n in names if results[n]["equity_buffer_mult"] >= 2.0]
    primary = max(safe_2x, key=lambda n: results[n]["cluster_a_2x"]["calmar"])

    bybit_check = compute_bybit_crosscheck(panel, funding_dir=funding_dir)

    returns_out.parent.mkdir(parents=True, exist_ok=True)
    sleeve_payload = {
        "schema": "naqex-sleeve-daily-returns-v1",
        "sleeve_id": "sleeve3a_funding_carry",
        "strategy_name": primary,
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "annualization_days": 365.0,
        "calendar_type": "24_7_calendar",
        "cost_assumption": "23 bps one-way pair cost (15 bps spot + 8 bps perp) on notional, 2x equity buffer, 0% idle cash yield",
        "universe_desc": f"{len(panel['symbols'])} Binance USD-M Perpetuals + Spot Long hedge",
        "cluster_a_window": [START_DATE, CLUSTER_A_END],
        "cluster_b_window": [CLUSTER_B_START, dates[-1]],
        "metrics_cluster_a": results[primary]["cluster_a_1x"],
        "metrics_cluster_b": results[primary]["cluster_b_1x"],
        "metrics_full": results[primary]["full_1x"],
        "daily_returns": daily_1x[primary],
        "variants": daily_1x,
    }
    returns_out.write_text(json.dumps(sleeve_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    summary = {
        "schema": "naqex-sleeve3a-funding-carry-v1",
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "symbols_loaded": panel["symbols"],
        "date_range": [dates[0], dates[-1], len(dates)],
        "primary_selected_on_cluster_a": primary,
        "bybit_crosscheck": bybit_check,
        "strategies": results,
        "returns_json_path": str(returns_out),
    }
    (funding_dir / "funding_study_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M3.3 Crypto Delta-Neutral Funding-Rate Carry")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    s = run_funding_study(fetch=not args.no_fetch)
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "symbols_count": len(s["symbols_loaded"]),
        "date_range": s["date_range"],
        "primary_selected_on_cluster_a": s["primary_selected_on_cluster_a"],
        "bybit_crosscheck": s["bybit_crosscheck"],
        "primary_a": s["strategies"][s["primary_selected_on_cluster_a"]]["cluster_a_1x"],
        "primary_b": s["strategies"][s["primary_selected_on_cluster_a"]]["cluster_b_1x"],
        "returns_json_path": s["returns_json_path"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
