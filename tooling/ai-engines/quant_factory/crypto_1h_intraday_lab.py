"""C1.1 — Lab #1: 100-Coin Crypto Universe Expansion + 1H (2021-2026) & 15m (2024-2026) Intraday Microstructure Lab.

STRICT SAFETY & ANTI-BIAS BOUNDARIES:
  - Public Binance Spot (/api/v3/klines) ONLY — zero API keys, OrderSend = 0, Holdout 2025+ FX untouched.
  - Expands cached crypto universe to 100 liquid + historical declined/delisted coins under `.runtime/crypto-1h-cache/`
    (4H 2021-2026 for up to 100 coins, 1H 2021-2026 for top 40 coins, 15m 2024-2026 for top 15 coins) with SHA manifest.
  - Strictly causal rolling 30-day dollar-volume universe selector (<= bar t) + strict t -> t+1 execution.
  - Realistic spot friction: 1x = 15 bps one-way (10 bps fee + 5 bps slip), 2x stress = 30 bps one-way + 100 bps delist haircut.
  - Strict split: Cluster A (2021-01-01..2023-12-31) -> Blind Cluster B (2024-01-01..2026-11-22) for 1H families;
    2024-01-01..2025-05-31 Dev -> 2025-06-01..2026-11-22 Blind OOS for 15m sub-study.
  - Wires ALL 12 preregistered specs across 6 intraday families through `quant_factory.research_council`
    (`HypothesisCard` + `SkepticalRedTeamCritic`, BH-FDR over m_total=12, DSR, 2x cost breakeven, corr vs Sleeve #2 F4_4H_EMA).
  - Retains ALL negative/killed results honestly!
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import threading
import time
from typing import Any

import httpx
import numpy as np
from numpy.lib.stride_tricks import sliding_window_view
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import (
    BINANCE_SPOT_BASE,
    CACHE_DIR as SPOT50_CACHE_DIR,
    PARQUET_SCHEMA,
    RETURNS_DIR,
    UNIVERSE_50_BASES,
    _apply_rebalance_deadband,
    _causal_ema_matrix,
    _compute_log_or_simple_rets,
    _iso_to_ms,
    _ms_to_date,
    _write_klines_parquet,
    causal_rolling_top_n_mask,
    compute_daily_metrics,
    simulate_spot_backtest,
)
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

LAB1_CACHE_DIR = ROOT / ".runtime" / "crypto-1h-cache"
LAB1_RETURNS_PATH = RETURNS_DIR / "sleeve_lab1_crypto_1h.json"

EXTRA_50_BASES: tuple[str, ...] = (
    "SHIB", "PEPE", "WIF", "FLOKI", "BONK", "SEI", "TIA", "STX", "IMX", "FET",
    "TAO", "WLD", "JUP", "PYTH", "ENA", "PENDLE", "ONDO", "TON", "HBAR", "QNT",
    "FLOW", "GALA", "APE", "DYDX", "GMX", "CFX", "CAKE", "1INCH", "YFI", "BAL",
    "KAVA", "ZIL", "BAT", "ZRX", "QTUM", "ICX", "ONT", "IOST", "ONE", "CELO",
    "ANKR", "STORJ", "SKL", "LRC", "ROSE", "MINA", "DASH", "ZEN", "KNC", "RVN",
)
UNIVERSE_100_BASES: tuple[str, ...] = UNIVERSE_50_BASES + EXTRA_50_BASES
UNIVERSE_100_SYMBOLS: tuple[str, ...] = tuple(f"{b}USDT" for b in UNIVERSE_100_BASES)

TOP40_1H_SYMBOLS: tuple[str, ...] = tuple(
    f"{b}USDT"
    for b in (
        "BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE", "TRX", "LINK", "LTC",
        "BCH", "DOT", "ATOM", "AVAX", "UNI", "AAVE", "FIL", "ALGO", "VET", "ICP",
        "NEAR", "ARB", "OP", "APT", "SUI", "INJ", "LDO", "SAND", "MANA", "AXS",
        "THETA", "GRT", "CRV", "RUNE", "ZEC", "EOS", "WAVES", "SHIB", "PEPE", "TON",
    )
)
TOP15_15M_SYMBOLS: tuple[str, ...] = (
    "BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT",
    "ADAUSDT", "DOGEUSDT", "TRXUSDT", "LINKUSDT", "LTCUSDT",
    "AVAXUSDT", "SUIUSDT", "NEARUSDT", "AAVEUSDT", "UNIUSDT",
)

START_1H = "2021-01-01"
CL_A_END_1H = "2023-12-31"
CL_B_START_1H = "2024-01-01"
START_15M = "2024-01-01"
CL_A_END_15M = "2025-05-31"
CL_B_START_15M = "2025-06-01"

LAB1_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.70,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.55,  # Intraday crypto shares BTC regime; require genuine incremental alpha!
    max_tail_corr_vs_incumbent=0.75,
    min_trades_cluster_b=30,
)

# Shared lightweight rate-limiter to respect Binance 6000 weight/min cleanly (weight 2 per kline req)
_RATE_LOCK = threading.Lock()
_WEIGHT_USED = 0


def _fetch_binance_klines_paced(
    symbol: str,
    interval: str,
    start_ms: int,
    end_ms: int,
) -> tuple[str, str, list[list[Any]], str | None]:
    step_map = {"4h": 4 * 3_600_000, "1h": 3_600_000, "15m": 15 * 60_000}
    step_ms = step_map[interval]
    rows: list[list[Any]] = []
    cur = start_ms
    try:
        with httpx.Client(timeout=15.0, headers={"User-Agent": "NaqexQuantLab1/1.0"}) as client:
            while cur <= end_ms:
                params = {"symbol": symbol, "interval": interval, "startTime": cur, "endTime": end_ms, "limit": 1000}
                resp = None
                for attempt in range(5):
                    r = client.get(f"{BINANCE_SPOT_BASE}/api/v3/klines", params=params)
                    used = int(r.headers.get("x-mbx-used-weight-1m", "0") or "0")
                    if used > 4800:
                        time.sleep(2.0)
                    if r.status_code == 200:
                        resp = r.json()
                        break
                    if r.status_code in (429, 418, 500, 502, 503):
                        wait_s = float(r.headers.get("Retry-After", str(1.0 * (attempt + 1))))
                        time.sleep(min(wait_s, 10.0))
                        continue
                    return symbol, interval, rows, f"HTTP_{r.status_code}:{r.text[:80]}"
                if resp is None:
                    return symbol, interval, rows, "MAX_RETRIES"
                if not resp:
                    break
                rows.extend(resp)
                last_open = int(resp[-1][0])
                if len(resp) < 1000 or last_open >= end_ms:
                    break
                cur = last_open + step_ms
        dedup = {int(r[0]): r for r in rows if start_ms <= int(r[0]) <= end_ms}
        return symbol, interval, [dedup[k] for k in sorted(dedup)], None
    except Exception as exc:
        return symbol, interval, rows, f"EXC:{type(exc).__name__}:{exc}"


def fetch_and_cache_lab1_data(
    *,
    cache_dir: Path = LAB1_CACHE_DIR,
    force_refresh: bool = False,
    max_workers: int = 8,
) -> dict[str, Any]:
    """Expand Binance Spot cache to 100 coins (4H), top 40 (1H 2021-2026), and top 15 (15m 2024-2026)."""
    cache_dir.mkdir(parents=True, exist_ok=True)
    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    end_ms = int(today_start.timestamp() * 1000) - 1
    ms_2021 = _iso_to_ms(START_1H)
    ms_2024 = _iso_to_ms(START_15M)

    # Check which of the 100 symbols exist on Binance exchangeInfo
    valid_syms = set(UNIVERSE_100_SYMBOLS)
    sym_status: dict[str, str] = {}
    try:
        with httpx.Client(timeout=15.0) as client:
            info = client.get(f"{BINANCE_SPOT_BASE}/api/v3/exchangeInfo").json()
            sym_status = {s["symbol"]: s["status"] for s in info.get("symbols", [])}
            valid_syms = {s for s in UNIVERSE_100_SYMBOLS if s in sym_status}
    except Exception:
        pass

    plan: list[tuple[str, str, int]] = []
    files_meta: dict[str, Any] = {}
    skipped: list[dict[str, str]] = []

    def _enqueue(syms: tuple[str, ...], iv: str, s_ms: int) -> None:
        iv_dir = cache_dir / iv
        iv_dir.mkdir(parents=True, exist_ok=True)
        for s in syms:
            if s not in valid_syms:
                skipped.append({"symbol": s, "interval": iv, "reason": "NOT_ON_BINANCE"})
                continue
            p = iv_dir / f"{s}.parquet"
            # Fast reuse: if 4h exists in Wave-1 .runtime/crypto-spot-cache/4h, copy/link metadata without network!
            wave1_p = SPOT50_CACHE_DIR / "4h" / f"{s}.parquet"
            if iv == "4h" and not p.exists() and wave1_p.exists() and not force_refresh:
                p.write_bytes(wave1_p.read_bytes())
            if p.exists() and not force_refresh:
                tbl = pq.read_table(p, columns=["open_time_ms"])
                ot = tbl["open_time_ms"].to_numpy()
                if len(ot) > 0:
                    files_meta[f"{iv}/{s}.parquet"] = {
                        "rows": int(len(ot)),
                        "status": sym_status.get(s, "CACHED"),
                        "first_utc": _ms_to_date(int(ot[0])),
                        "last_utc": _ms_to_date(int(ot[-1])),
                        "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                    }
                    continue
            plan.append((s, iv, s_ms))

    _enqueue(UNIVERSE_100_SYMBOLS, "4h", ms_2021)
    _enqueue(TOP40_1H_SYMBOLS, "1h", ms_2021)
    _enqueue(TOP15_15M_SYMBOLS, "15m", ms_2024)

    if plan:
        with ThreadPoolExecutor(max_workers=max_workers) as pool:
            futs = [pool.submit(_fetch_binance_klines_paced, s, iv, sms, end_ms) for s, iv, sms in plan]
            for fut in as_completed(futs):
                sym, iv, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"symbol": sym, "interval": iv, "reason": err or "EMPTY"})
                    continue
                p = cache_dir / iv / f"{sym}.parquet"
                dig = _write_klines_parquet(p, rows)
                files_meta[f"{iv}/{sym}.parquet"] = {
                    "rows": len(rows),
                    "status": sym_status.get(sym, "UNKNOWN"),
                    "first_utc": _ms_to_date(int(rows[0][0])),
                    "last_utc": _ms_to_date(int(rows[-1][0])),
                    "sha256": dig,
                }

    manifest = {
        "schema": "naqex-crypto-1h-cache-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "counts_by_interval": {
            iv: sum(1 for k in files_meta if k.startswith(f"{iv}/")) for iv in ("4h", "1h", "15m")
        },
        "skipped": skipped,
        "files": dict(sorted(files_meta.items())),
    }
    (cache_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def load_interval_panel(interval: str, symbols: tuple[str, ...], *, cache_dir: Path = LAB1_CACHE_DIR, min_date: str = START_1H) -> dict[str, Any]:
    iv_dir = cache_dir / interval
    min_ms = _iso_to_ms(min_date)
    loaded: list[str] = []
    raw: dict[str, dict[str, np.ndarray]] = {}
    all_ts: set[int] = set()
    for sym in symbols:
        p = iv_dir / f"{sym}.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p)
        ot = tbl["open_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        m = ot >= min_ms
        if not np.any(m):
            continue
        loaded.append(sym)
        raw[sym] = {
            "t": ot[m],
            "h": tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64)[m],
            "l": tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64)[m],
            "c": tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)[m],
            "qv": tbl["quote_volume"].to_numpy(zero_copy_only=False).astype(np.float64)[m],
        }
        all_ts.update(ot[m].tolist())
    ts_arr = np.array(sorted(all_ts), dtype=np.int64)
    ts_map = {int(t): i for i, t in enumerate(ts_arr)}
    n_t, n_k = len(ts_arr), len(loaded)
    highs = np.full((n_t, n_k), np.nan, dtype=np.float64)
    lows = np.full((n_t, n_k), np.nan, dtype=np.float64)
    closes = np.full((n_t, n_k), np.nan, dtype=np.float64)
    qvol = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for j, sym in enumerate(loaded):
        d = raw[sym]
        idxs = np.array([ts_map[int(t)] for t in d["t"]], dtype=np.int64)
        highs[idxs, j] = d["h"]
        lows[idxs, j] = d["l"]
        closes[idxs, j] = d["c"]
        qvol[idxs, j] = d["qv"]
    return {"interval": interval, "symbols": loaded, "timestamps_ms": ts_arr, "high": highs, "low": lows, "close": closes, "quote_volume": qvol}


def _aggregate_bars_to_daily(timestamps_ms: np.ndarray, net_r: np.ndarray, turnover: np.ndarray, exp: np.ndarray) -> tuple[list[str], np.ndarray, np.ndarray, np.ndarray]:
    # Fast vectorized grouping by UTC calendar day (ms // 86_400_000)
    day_ints = timestamps_ms // 86_400_000
    uniq_days, inv = np.unique(day_ints, return_inverse=True)
    n_d = len(uniq_days)
    d_ret = np.ones(n_d, dtype=np.float64)
    d_to = np.zeros(n_d, dtype=np.float64)
    d_ex = np.zeros(n_d, dtype=np.float64)
    d_cnt = np.zeros(n_d, dtype=np.int64)
    # Compound (1 + r) per day cleanly
    for i in range(len(net_r)):
        g = inv[i]
        d_ret[g] *= (1.0 + float(net_r[i]))
        d_to[g] += float(turnover[i])
        d_ex[g] += float(exp[i])
        d_cnt[g] += 1
    d_ret -= 1.0
    d_ex /= np.maximum(1, d_cnt)
    dates = [_ms_to_date(int(d) * 86_400_000) for d in uniq_days]
    return dates, d_ret, d_to, d_ex


def _rolling_vol_fast(rets: np.ndarray, win: int) -> np.ndarray:
    n_t, n_k = rets.shape
    ok = np.isfinite(rets)
    rz = np.where(ok, rets, 0.0)
    c = np.cumsum(ok.astype(np.int64), axis=0)
    s1 = np.cumsum(rz, axis=0)
    s2 = np.cumsum(rz * rz, axis=0)
    out = np.full((n_t, n_k), np.nan, dtype=np.float64)
    if n_t > win:
        cnt = c[win:] - c[:-win]
        m = (s1[win:] - s1[:-win]) / win
        v = np.maximum(0.0, ((s2[win:] - s2[:-win]) - win * m * m) / max(1, win - 1))
        out[win:] = np.where(cnt == win, np.sqrt(v), np.nan)
    return out


def build_1h_strategies(panel: dict[str, Any], top15: np.ndarray) -> dict[str, dict[str, Any]]:
    """Build 10 preregistered 1H microstructure strategies across Families 1-5 (100% causal <= t)."""
    closes = panel["close"]
    highs = panel["high"]
    lows = panel["low"]
    ts_ms = panel["timestamps_ms"]
    syms = panel["symbols"]
    n_t, n_k = closes.shape
    btc_i = syms.index("BTCUSDT")
    rets = _compute_log_or_simple_rets(closes)
    hours_utc = ((ts_ms // 3_600_000) % 24).astype(np.int32)

    vol24 = _rolling_vol_fast(rets, 24)
    vol168 = _rolling_vol_fast(rets, 168)   # 7d realized vol
    vol720 = _rolling_vol_fast(rets, 720)   # 30d realized vol
    ema48 = _causal_ema_matrix(closes, 48)
    ema96 = _causal_ema_matrix(closes, 96)
    ema168 = _causal_ema_matrix(closes, 168)
    ema240 = _causal_ema_matrix(closes, 240)
    ema480 = _causal_ema_matrix(closes, 480)
    ema720 = _causal_ema_matrix(closes, 720)
    ema1200 = _causal_ema_matrix(closes, 1200)

    vt15_1h = 0.15 / math.sqrt(365.0 * 24.0)
    inv_vol = np.where(np.isfinite(vol168) & (vol168 > 1e-6), vt15_1h / vol168, 0.0)
    n_elig = np.maximum(1, top15.sum(axis=1, keepdims=True))

    btc_bull_240_720 = (ema240[:, btc_i] > ema720[:, btc_i])[:, None]
    btc_bull_168_720 = (ema168[:, btc_i] > ema720[:, btc_i])[:, None]
    btc_bull_240_1200 = (ema240[:, btc_i] > ema1200[:, btc_i])[:, None]
    btc_gt_720 = (closes[:, btc_i] > ema720[:, btc_i])[:, None]

    def _cap(sig: np.ndarray, db: float = 0.02) -> np.ndarray:
        raw = np.where(sig, inv_vol, 0.0) / n_elig
        s = raw.sum(axis=1, keepdims=True)
        w = np.where(s > 1.0, raw / np.maximum(s, 1e-12), raw)
        return _apply_rebalance_deadband(w, db)

    # Prior Donchian highs/lows (strictly [t-win .. t-1])
    def _prior_max(arr: np.ndarray, w: int) -> np.ndarray:
        out = np.full_like(arr, np.nan)
        if len(arr) > w:
            sw = sliding_window_view(arr[:-1], w, axis=0)
            out[w:] = np.where(np.all(np.isfinite(sw), axis=2), np.max(sw, axis=2), np.nan)
        return out

    def _prior_min(arr: np.ndarray, w: int) -> np.ndarray:
        out = np.full_like(arr, np.nan)
        if len(arr) > w:
            sw = sliding_window_view(arr[:-1], w, axis=0)
            out[w:] = np.where(np.all(np.isfinite(sw), axis=2), np.min(sw, axis=2), np.nan)
        return out

    hi24, lo24 = _prior_max(highs, 24), _prior_min(lows, 24)
    hi72, lo36 = _prior_max(highs, 72), _prior_min(lows, 36)
    hi168, lo84 = _prior_max(highs, 168), _prior_min(lows, 84)

    # Family 1: 1H Vol-Targeted Donchian Breakouts (72/36 & 168/84 + BTC gate)
    def _run_don(hi_p: np.ndarray, lo_p: np.ndarray, gate: np.ndarray | None, start: int) -> np.ndarray:
        st = np.zeros(n_k, dtype=bool)
        w_out = np.zeros((n_t, n_k), dtype=np.float64)
        for t in range(start, n_t):
            c = closes[t]
            el = top15[t]
            g_ok = True if gate is None else bool(gate[t, 0])
            ex = (~np.isfinite(c)) | (~el) | (np.isfinite(lo_p[t]) & (c < lo_p[t])) | (not g_ok)
            en = g_ok & el & np.isfinite(c) & np.isfinite(hi_p[t]) & (c > hi_p[t])
            st = np.where(st, ~ex, en)
            if np.any(st):
                r = np.where(st, inv_vol[t], 0.0) / max(1, int(el.sum()))
                s = float(r.sum())
                w_out[t] = r / s if s > 1.0 else r
        return _apply_rebalance_deadband(w_out, 0.02)

    w_don72 = _run_don(hi72, lo36, None, 72)
    w_don168 = _run_don(hi168, lo84, btc_bull_240_720, 168)

    # Family 2: Crypto Session Microstructure (US Open Continuation 14->22 UTC & Asia-to-US Dip Reversion 13->21 UTC)
    ret6 = np.full_like(closes, np.nan)
    ret6[6:] = closes[6:] / np.where(closes[:-6] > 0, closes[:-6], np.nan) - 1.0
    ret12 = np.full_like(closes, np.nan)
    ret12[12:] = closes[12:] / np.where(closes[:-12] > 0, closes[:-12], np.nan) - 1.0
    z6 = ret6 / np.where(np.isfinite(vol168) & (vol168 > 1e-6), vol168 * math.sqrt(6.0), np.nan)
    z12 = ret12 / np.where(np.isfinite(vol168) & (vol168 > 1e-6), vol168 * math.sqrt(12.0), np.nan)

    w_us_cont = np.zeros((n_t, n_k), dtype=np.float64)
    w_asia_rev = np.zeros((n_t, n_k), dtype=np.float64)
    active_us = np.zeros(n_k, dtype=bool)
    active_ar = np.zeros(n_k, dtype=bool)
    for t in range(168, n_t):
        hr = int(hours_utc[t])
        el = top15[t]
        if hr == 13:  # 13:00 bar close = 14:00 UTC US open decision!
            active_us = el & bool(btc_bull_240_720[t, 0]) & np.isfinite(z6[t]) & (z6[t] >= 0.8)
        elif hr == 21 or hr < 13:
            active_us[:] = False
        if np.any(active_us):
            r = np.where(active_us, inv_vol[t], 0.0) / max(1, int(active_us.sum()))
            s = float(r.sum())
            w_us_cont[t] = r / s if s > 1.0 else r

        if hr == 12:  # 12:00 bar close = 13:00 UTC pre-US dip decision!
            active_ar = el & bool(btc_gt_720[t, 0]) & np.isfinite(z12[t]) & (z12[t] <= -1.5)
        elif hr == 20 or hr < 12:
            active_ar[:] = False
        if np.any(active_ar):
            r = np.where(active_ar, inv_vol[t], 0.0) / max(1, int(active_ar.sum()))
            s = float(r.sum())
            w_asia_rev[t] = r / s if s > 1.0 else r

    # Family 3: 1H EMA Trend Acceleration
    w_ema48 = _cap(top15 & btc_bull_168_720 & (ema48 > ema240), db=0.02)
    w_ema96 = _cap(top15 & btc_bull_240_1200 & (ema96 > ema480), db=0.02)

    # Family 4: 8h Funding Settlement Clock Microstructure (Pre-settle mom & Post-settle dip)
    ret4 = np.full_like(closes, np.nan)
    ret4[4:] = closes[4:] / np.where(closes[:-4] > 0, closes[:-4], np.nan) - 1.0
    ret2 = np.full_like(closes, np.nan)
    ret2[2:] = closes[2:] / np.where(closes[:-2] > 0, closes[:-2], np.nan) - 1.0
    z4 = ret4 / np.where(np.isfinite(vol168) & (vol168 > 1e-6), vol168 * 2.0, np.nan)
    z2 = ret2 / np.where(np.isfinite(vol168) & (vol168 > 1e-6), vol168 * math.sqrt(2.0), np.nan)

    w_pre_settle = np.zeros((n_t, n_k), dtype=np.float64)
    w_post_settle = np.zeros((n_t, n_k), dtype=np.float64)
    hold_post = np.zeros(n_k, dtype=np.int32)
    for t in range(168, n_t):
        hr = int(hours_utc[t])
        el = top15[t]
        # Pre-settlement hours (05->07, 13->15, 21->23 close => held across 06-08, 14-16, 22-00 UTC)
        if hr in (5, 6, 13, 14, 21, 22) and bool(btc_bull_240_720[t, 0]):
            cand = [(float(z4[t, j]), j) for j in np.flatnonzero(el) if np.isfinite(z4[t, j]) and z4[t, j] > 0.5]
            cand.sort(reverse=True)
            top5 = [j for _, j in cand[:5]]
            if top5:
                r = np.zeros(n_k, dtype=np.float64)
                for j in top5:
                    r[j] = inv_vol[t, j] / len(top5)
                s = float(r.sum())
                w_pre_settle[t] = r / s if s > 1.0 else r
        # Post-settlement dip at 01, 09, 17 bar close -> hold 4h
        hold_post = np.maximum(0, hold_post - 1)
        if hr in (1, 9, 17) and bool(btc_gt_720[t, 0]):
            dip = el & np.isfinite(z2[t]) & (z2[t] <= -1.5)
            hold_post = np.where(dip, 4, hold_post)
        act_p = (hold_post > 0) & el
        if np.any(act_p):
            r = np.where(act_p, inv_vol[t], 0.0) / max(1, int(act_p.sum()))
            s = float(r.sum())
            w_post_settle[t] = r / s if s > 1.0 else r

    # Family 5: 1H Volatility Compression Squeeze Breakout (vol24 / vol720 < 0.70)
    vol_ratio = vol24 / np.where(np.isfinite(vol720) & (vol720 > 1e-6), vol720, np.nan)
    def _run_sqz(hi_p: np.ndarray, lo_p: np.ndarray, gate: np.ndarray | None, max_hold: int) -> np.ndarray:
        hcnt = np.zeros(n_k, dtype=np.int32)
        w_out = np.zeros((n_t, n_k), dtype=np.float64)
        for t in range(720, n_t):
            c = closes[t]
            el = top15[t]
            g_ok = True if gate is None else bool(gate[t, 0])
            for j in range(n_k):
                if hcnt[j] > 0:
                    if (not np.isfinite(c[j])) or (not el[j]) or (np.isfinite(lo_p[t, j]) and c[j] < lo_p[t, j]) or hcnt[j] >= max_hold:
                        hcnt[j] = 0
                    else:
                        hcnt[j] += 1
                elif g_ok and el[j] and np.isfinite(vol_ratio[t, j]) and vol_ratio[t, j] < 0.70 and np.isfinite(hi_p[t, j]) and c[j] > hi_p[t, j]:
                    hcnt[j] = 1
            act = hcnt > 0
            if np.any(act):
                r = np.where(act, inv_vol[t], 0.0) / max(1, int(el.sum()))
                s = float(r.sum())
                w_out[t] = r / s if s > 1.0 else r
        return _apply_rebalance_deadband(w_out, 0.02)

    w_sqz24 = _run_sqz(hi24, lo24, None, 48)
    w_sqz72_btc = _run_sqz(hi72, lo36, btc_bull_240_720, 72)

    return {
        "L1_F1_1H_DON_72_36": {"fam": "F1_1H_DONCHIAN_BRK", "w": w_don72, "cp": "Stop-cascade breakout above 72h range", "rat": "72h/36h causal Donchian breakout on Top-15 1H coins captures medium intraday trend expansions with vol targeting."},
        "L1_F1_1H_DON_168_84_BTC": {"fam": "F1_1H_DONCHIAN_BRK", "w": w_don168, "cp": "Regime-gated trend breakout above 7-day range", "rat": "168h/84h Donchian breakout gated by BTC 10d/30d EMA avoids bear-market false breakouts while riding weekly trends."},
        "L1_F2_1H_US_OPEN_CONT": {"fam": "F2_1H_SESSION_FLOW", "w": w_us_cont, "cp": "US ETF/equity-hours institutional inflow continuation", "rat": "Positive pre-US 6h momentum at 14:00 UTC rides US cash/ETF institutional order flow through 22:00 UTC."},
        "L1_F2_1H_ASIA_TO_US_REV": {"fam": "F2_1H_SESSION_FLOW", "w": w_asia_rev, "cp": "Thin Asian selloff absorbed by deeper US liquidity", "rat": "Overextended Asian/EU selloffs (z <= -1.5) revert during 13:00-21:00 UTC when US liquidity desks step in."},
        "L1_F3_1H_EMA_48_240_BTC": {"fam": "F3_1H_EMA_TREND", "w": w_ema48, "cp": "Faster hourly trend-following capturing short momentum bursts", "rat": "1H EMA(48/240) gated by BTC EMA(168/720) adapts faster than 4H trend while controlling turnover via 2% deadband."},
        "L1_F3_1H_EMA_96_480_BTC": {"fam": "F3_1H_EMA_TREND", "w": w_ema96, "cp": "Multi-day hourly trend continuation across liquid majors", "rat": "1H EMA(96/480) gated by BTC EMA(240/1200) balances signal speed and transaction-cost drag on 1H bars."},
        "L1_F4_1H_PRE_SETTLE_MOM": {"fam": "F4_1H_FUNDING_CLOCK", "w": w_pre_settle, "cp": "Pre-settlement perp/spot hedging imbalance every 8h", "rat": "Pre-funding-settlement 2h windows concentrate directional rebalancing before 00:00/08:00/16:00 UTC funding snaps."},
        "L1_F4_1H_POST_SETTLE_REV": {"fam": "F4_1H_FUNDING_CLOCK", "w": w_post_settle, "cp": "Post-settlement forced unwind snapback", "rat": "Sharp post-settlement 2h liquidations (z <= -1.5) mean-revert over the following 4h in BTC bull regimes."},
        "L1_F5_1H_VOL_SQZ_BRK24": {"fam": "F5_1H_VOL_SQUEEZE", "w": w_sqz24, "cp": "Coiled intraday volatility breakout releasing trapped positioning", "rat": "24h realized vol compressed below 70% of 30d vol precedes directional 24h range expansion."},
        "L1_F5_1H_VOL_SQZ_72_BTC": {"fam": "F5_1H_VOL_SQUEEZE", "w": w_sqz72_btc, "cp": "Regime-gated volatility squeeze breakout across Top-15", "rat": "Volatility compression (<0.70x 30d vol) combined with 72h breakout and BTC uptrend targets high-convexity breakouts."},
    }


def build_15m_strategies(panel15: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build 2 preregistered 15m microstructure strategies on Top-15 coins (2024-2026 sub-study)."""
    closes = panel15["close"]
    highs = panel15["high"]
    qvol = panel15["quote_volume"]
    ts_ms = panel15["timestamps_ms"]
    syms = panel15["symbols"]
    n_t, n_k = closes.shape
    btc_i = syms.index("BTCUSDT")
    rets = _compute_log_or_simple_rets(closes)

    vol96 = _rolling_vol_fast(rets, 96)  # 24h realized vol on 15m bars
    btc_ema672 = _causal_ema_matrix(closes[:, btc_i:btc_i + 1], 672)[:, 0]  # 7d EMA on 15m bars
    vt15_15m = 0.15 / math.sqrt(365.0 * 96.0)
    inv_vol = np.where(np.isfinite(vol96) & (vol96 > 1e-6), vt15_15m / vol96, 0.0)

    # 1. US Equity Open 15m ORB (13:30-14:30 UTC box -> hold breakout until 20:30 UTC)
    mins_utc = ((ts_ms // 60_000) % 1440).astype(np.int32)
    w_orb = np.zeros((n_t, n_k), dtype=np.float64)
    box_hi = np.full(n_k, np.nan)
    box_lo = np.full(n_k, np.nan)
    in_pos = np.zeros(n_k, dtype=bool)
    for t in range(100, n_t):
        m = int(mins_utc[t])
        if m == 810:  # 13:30 UTC start of box
            box_hi = highs[t].copy()
            box_lo = panel15["low"][t].copy()
            in_pos[:] = False
        elif 810 < m < 870:
            box_hi = np.fmax(box_hi, highs[t])
            box_lo = np.fmin(box_lo, panel15["low"][t])
        elif 870 <= m < 1230:  # 14:30 -> 20:30 UTC breakout scan
            brk = np.isfinite(closes[t]) & np.isfinite(box_hi) & (closes[t] > box_hi) & (closes[t, btc_i] > btc_ema672[t])
            in_pos = in_pos | brk
            if np.any(in_pos):
                r = np.where(in_pos, inv_vol[t], 0.0) / max(1, n_k)
                s = float(r.sum())
                w_orb[t] = r / s if s > 1.0 else r
        else:
            in_pos[:] = False

    # 2. 15m Liquidation Flush Bounce (4-bar ret z < -2.5 & quote_vol > 3x 24h avg, hold 8 bars = 2h)
    ret4 = np.full_like(closes, np.nan)
    ret4[4:] = closes[4:] / np.where(closes[:-4] > 0, closes[:-4], np.nan) - 1.0
    z4 = ret4 / np.where(np.isfinite(vol96) & (vol96 > 1e-6), vol96 * 2.0, np.nan)
    ok_q = np.isfinite(qvol)
    cs_q = np.cumsum(np.where(ok_q, qvol, 0.0), axis=0)
    cs_c = np.cumsum(ok_q.astype(np.int64), axis=0)
    avg_q96 = np.full_like(qvol, np.nan)
    if n_t > 96:
        cnt = cs_c[96:] - cs_c[:-96]
        avg_q96[96:] = np.where(cnt >= 80, (cs_q[96:] - cs_q[:-96]) / np.maximum(1, cnt), np.nan)

    w_flush = np.zeros((n_t, n_k), dtype=np.float64)
    hold_f = np.zeros(n_k, dtype=np.int32)
    for t in range(100, n_t):
        hold_f = np.maximum(0, hold_f - 1)
        btc_ok = np.isfinite(btc_ema672[t]) and np.isfinite(closes[t, btc_i]) and closes[t, btc_i] > btc_ema672[t]
        if btc_ok:
            trig = np.isfinite(z4[t]) & (z4[t] <= -2.5) & np.isfinite(avg_q96[t]) & (qvol[t] >= 3.0 * avg_q96[t])
            hold_f = np.where(trig, 8, hold_f)
        act = hold_f > 0
        if np.any(act):
            r = np.where(act, inv_vol[t], 0.0) / max(1, int(act.sum()))
            s = float(r.sum())
            w_flush[t] = r / s if s > 1.0 else r

    return {
        "L1_F6_15M_US_OPEN_ORB": {"fam": "F6_15M_MICROSTRUCTURE", "w": w_orb, "cp": "US cash open 15m range expansion breakout", "rat": "15m opening-range breakout during 13:30-14:30 UTC captures institutional US equity-linked crypto directional flow."},
        "L1_F6_15M_LIQ_FLUSH_BOUNCE": {"fam": "F6_15M_MICROSTRUCTURE", "w": w_flush, "cp": "Forced 15m margin-liquidation spike absorbed by passive makers", "rat": "Extreme 1-hour price flush (z <= -2.5) with >= 3x volume surge snaps back over 2h in broader BTC uptrends."},
    }


def run_lab1(*, fetch: bool = True, cache_dir: Path = LAB1_CACHE_DIR) -> dict[str, Any]:
    t0 = time.perf_counter()
    manifest = fetch_and_cache_lab1_data(cache_dir=cache_dir) if fetch else json.loads((cache_dir / "manifest.sha256.json").read_text(encoding="utf-8"))

    # Load incumbent Sleeve #2 daily returns for orthogonality check
    inc_s2_map: dict[str, float] = {}
    s2_path = RETURNS_DIR / "sleeve2_crypto_spot.json"
    if s2_path.exists():
        inc_s2_map = json.loads(s2_path.read_text(encoding="utf-8")).get("daily_returns", {})

    panel_1h = load_interval_panel("1h", TOP40_1H_SYMBOLS, cache_dir=cache_dir, min_date=START_1H)
    top15_1h = causal_rolling_top_n_mask(panel_1h["quote_volume"], panel_1h["close"], lookback_bars=720, top_n=15)
    strats_1h = build_1h_strategies(panel_1h, top15_1h)

    panel_15m = load_interval_panel("15m", TOP15_15M_SYMBOLS, cache_dir=cache_dir, min_date=START_15M)
    strats_15m = build_15m_strategies(panel_15m)

    # Evaluate all 12 specs (10 on 1H 2021-2026 + 2 on 15m 2024-2026)
    eval_items: list[dict[str, Any]] = []
    daily_1x_map: dict[str, dict[str, float]] = {}

    for name, cfg in strats_1h.items():
        s1 = simulate_spot_backtest(panel_1h["close"], cfg["w"], cost_bps_oneway=15.0)
        s2 = simulate_spot_backtest(panel_1h["close"], cfg["w"], cost_bps_oneway=30.0)
        days, r1, to1, ex1 = _aggregate_bars_to_daily(panel_1h["timestamps_ms"], s1["net_returns"], s1["turnover"], s1["held_w"].sum(axis=1))
        _, r2, _, _ = _aggregate_bars_to_daily(panel_1h["timestamps_ms"], s2["net_returns"], s2["turnover"], s2["held_w"].sum(axis=1))
        ma = np.array([START_1H <= d <= CL_A_END_1H for d in days])
        mb = np.array([d >= CL_B_START_1H for d in days])
        eval_items.append({
            "id": name, "tf": "1h", "fam": cfg["fam"], "cp": cfg["cp"], "rat": cfg["rat"],
            "days": days, "r1": r1, "r2": r2, "ma": ma, "mb": mb,
            "mA1": compute_daily_metrics(r1[ma], to1[ma], ex1[ma]),
            "mA2": compute_daily_metrics(r2[ma], to1[ma], ex1[ma]),
            "mB1": compute_daily_metrics(r1[mb], to1[mb], ex1[mb]),
            "mB2": compute_daily_metrics(r2[mb], to1[mb], ex1[mb]),
            "mF1": compute_daily_metrics(r1, to1, ex1),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
        })
        daily_1x_map[name] = {d: float(v) for d, v in zip(days, r1)}

    for name, cfg in strats_15m.items():
        s1 = simulate_spot_backtest(panel_15m["close"], cfg["w"], cost_bps_oneway=15.0)
        s2 = simulate_spot_backtest(panel_15m["close"], cfg["w"], cost_bps_oneway=30.0)
        days, r1, to1, ex1 = _aggregate_bars_to_daily(panel_15m["timestamps_ms"], s1["net_returns"], s1["turnover"], s1["held_w"].sum(axis=1))
        _, r2, _, _ = _aggregate_bars_to_daily(panel_15m["timestamps_ms"], s2["net_returns"], s2["turnover"], s2["held_w"].sum(axis=1))
        ma = np.array([START_15M <= d <= CL_A_END_15M for d in days])
        mb = np.array([d >= CL_B_START_15M for d in days])
        eval_items.append({
            "id": name, "tf": "15m", "fam": cfg["fam"], "cp": cfg["cp"], "rat": cfg["rat"],
            "days": days, "r1": r1, "r2": r2, "ma": ma, "mb": mb,
            "mA1": compute_daily_metrics(r1[ma], to1[ma], ex1[ma]),
            "mA2": compute_daily_metrics(r2[ma], to1[ma], ex1[ma]),
            "mB1": compute_daily_metrics(r1[mb], to1[mb], ex1[mb]),
            "mB2": compute_daily_metrics(r2[mb], to1[mb], ex1[mb]),
            "mF1": compute_daily_metrics(r1, to1, ex1),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
        })
        daily_1x_map[name] = {d: float(v) for d, v in zip(days, r1)}

    m_total = len(eval_items)
    family_p_b = tuple(float(it["mB1"]["p_one_sided_nw"]) for it in eval_items)
    qb_all = benjamini_hochberg(list(family_p_b))

    results: list[dict[str, Any]] = []
    approved: list[str] = []

    for idx_i, it in enumerate(eval_items):
        days_b = [d for d, flag in zip(it["days"], it["mb"]) if flag]
        inc_b = np.array([inc_s2_map.get(d, 0.0) for d in days_b], dtype=np.float64) if inc_s2_map else None
        card = propose_hypothesis(
            hypothesis_id=it["id"],
            title=f"Lab #1 {it['fam']} ({it['tf']})",
            asset_universe=TOP40_1H_SYMBOLS[:5] if it["tf"] == "1h" else TOP15_15M_SYMBOLS[:5],
            timeframe=it["tf"],
            counterparty_mechanism=it["cp"],
            economic_rationale=it["rat"],
            causal_invariants=("causal_top15_30d_qv_le_t", "next_bar_t_plus_1_spot_only", "15bps_and_30bps_cost_tiers"),
            n_trials_cumulative=m_total,
            kill_criteria=LAB1_KILL_CRITERIA,
        )
        ev = EvidenceBundle(
            cluster_a_returns=it["r1"][it["ma"]],
            cluster_b_returns=it["r1"][it["mb"]],
            p_value_raw=float(it["mB1"]["p_one_sided_nw"]),
            family_p_values=family_p_b,
            candidate_index_in_family=idx_i,
            cost_1x_net=float(it["mB1"]["total_ret_pct"]),
            cost_2x_net=float(it["mB2"]["total_ret_pct"]),
            n_trades_cluster_b=it["n_active_days_b"],
            incumbent_daily_returns=inc_b,
            annualization_days=365.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        if verdict["verdict"] == "APPROVE_FOR_INCUBATION":
            approved.append(it["id"])
        dsr_full = deflated_sharpe_ratio(it["r1"], n_trials=m_total, annualization=365.0)
        results.append({
            "id": it["id"],
            "tf": it["tf"],
            "family": it["fam"],
            "cluster_a_1x": it["mA1"],
            "cluster_a_2x": it["mA2"],
            "cluster_b_1x": it["mB1"],
            "cluster_b_2x": it["mB2"],
            "full_1x": it["mF1"],
            "bh_q_b": round(qb_all[idx_i], 5),
            "dsr_b": verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_b": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_sleeve2_b": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "council_verdict": verdict["verdict"],
            "failed_gates": verdict["failed_gates"],
            "verdict_sha": verdict["verdict_sha256"],
        })

    # Export surviving sleeve JSON ONLY if >= 1 passes APPROVE_FOR_INCUBATION
    exported_path = None
    if approved:
        best_id = max(approved, key=lambda aid: next(r["cluster_a_1x"]["sharpe"] for r in results if r["id"] == aid))
        best_r = next(r for r in results if r["id"] == best_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "sleeve_lab1_crypto_1h",
            "strategy_name": best_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 365.0,
            "calendar_type": "24_7_calendar",
            "cost_assumption": "15 bps one-way spot friction + 100 bps delist haircut",
            "metrics_cluster_a": best_r["cluster_a_1x"],
            "metrics_cluster_b": best_r["cluster_b_1x"],
            "metrics_full": best_r["full_1x"],
            "daily_returns": daily_1x_map[best_id],
        }
        LAB1_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAB1_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(LAB1_RETURNS_PATH)

    summary = {
        "schema": "naqex-lab1-crypto-1h-intraday-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "cache_counts": manifest["counts_by_interval"],
        "loaded_1h_coins": len(panel_1h["symbols"]),
        "loaded_15m_coins": len(panel_15m["symbols"]),
        "m_total": m_total,
        "approved_count": len(approved),
        "approved_ids": approved,
        "exported_returns_path": exported_path,
        "results": results,
    }
    (cache_dir / "lab1_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="C1.1 Lab #1 Crypto 100-coin 1H & 15m Intraday Microstructure Lab")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    s = run_lab1(fetch=not args.no_fetch)
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "cache_counts": s["cache_counts"],
        "m_total": s["m_total"],
        "approved_count": s["approved_count"],
        "approved_ids": s["approved_ids"],
        "rows": [
            (r["id"], r["cluster_a_1x"]["cagr_pct"], r["cluster_a_1x"]["sharpe"], r["cluster_b_1x"]["cagr_pct"], r["cluster_b_2x"]["cagr_pct"], r["cluster_b_1x"]["sharpe"], r["bh_q_b"], r["dsr_b"], r["corr_vs_sleeve2_b"], r["council_verdict"])
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
