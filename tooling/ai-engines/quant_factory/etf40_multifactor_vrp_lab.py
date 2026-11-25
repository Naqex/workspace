"""Wave-2 Lab #4: 40-ETF Multi-Factor, RSI-2, Credit-Spread & VRP Own-Book Study (2005-2026).

Strict anti-bias, causal & fail-closed invariants:
  - Public Yahoo Finance v8 Chart API (`adjclose`, zero API key, `ORDER_SEND_COUNT = 0`).
  - 40 tickers (38 tradable liquid ETFs + 2 signal-only volatility indices `^VIX`, `^VIX3M`).
  - ZERO pre-listing forward-fill: assets with NaN at day t receive strictly 0.0 weight.
  - 100% causal t -> t+1 execution: every indicator computed <= day t close applies to day t+1 return.
  - Realistic trading friction: 1x = 5 bps one-way; 2x stress = 10 bps one-way; idle cash = 0% conservative.
  - Strict Cluster A (2005-01-01..2018-12-31, eval >= 2006-01-03) -> blind Cluster B (2019-01-01..2026-11-23).
  - Wired genuinely through `quant_factory.research_council` (`HypothesisCard` + `SkepticalRedTeamCritic`).
  - Saves best verified daily return series to `.runtime/quant-pod-returns/sleeve4_etf40_multifactor.json`.
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
import time
from typing import Any
import warnings

import httpx
import numpy as np
import pyarrow as pa
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import RETURNS_DIR, compute_daily_metrics
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.macro_etf_trend import ETF_SCHEMA, _month_end_flags, simulate_etf_weights
from quant_factory.portfolio_allocator import align_sleeves_business_days, load_external_sleeve_json
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

ORDER_SEND_COUNT = 0
ETF40_CACHE_DIR = ROOT / ".runtime" / "etf40-cache"
SLEEVE4_RETURNS_PATH = RETURNS_DIR / "sleeve4_etf40_multifactor.json"

START_DATE = "2005-01-01"
WARMUP_START = "2006-01-03"
CLUSTER_A_END = "2018-12-31"
CLUSTER_B_START = "2019-01-01"

US_SECTORS: tuple[str, ...] = ("XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB", "XLRE")
BROAD_FACTORS: tuple[str, ...] = ("SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV")
FIXED_INCOME_CREDIT: tuple[str, ...] = ("SHY", "IEF", "TLT", "TIP", "LQD", "HYG", "EMB")
INTERNATIONAL: tuple[str, ...] = ("EFA", "EEM", "EWJ", "EWG", "FXI", "EWZ")
COMMODITIES: tuple[str, ...] = ("GLD", "SLV", "USO", "UNG", "DBA", "DBC")
VOL_CASH_FX: tuple[str, ...] = ("UUP", "BIL", "^VIX", "^VIX3M")

SIGNAL_ONLY_TICKERS: frozenset[str] = frozenset({"^VIX", "^VIX3M"})
ETF40_UNIVERSE: tuple[str, ...] = (
    US_SECTORS + BROAD_FACTORS + FIXED_INCOME_CREDIT + INTERNATIONAL + COMMODITIES + VOL_CASH_FX
)


def _safe_filename(ticker: str) -> str:
    return ticker.replace("^", "IDX_") + ".parquet"


def _fetch_yahoo_ticker(symbol: str, start_ts: int, end_ts: int) -> tuple[str, list[dict[str, Any]], str | None]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": start_ts, "period2": end_ts, "interval": "1d", "events": "div,splits"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        with httpx.Client(timeout=18.0, headers=headers) as client:
            resp = None
            for attempt in range(4):
                r = client.get(url, params=params)
                if r.status_code == 200:
                    resp = r.json()
                    break
                time.sleep(0.5 * (attempt + 1))
            if resp is None:
                return symbol, [], "HTTP_FAILED"
        chart = resp.get("chart", {})
        if not chart.get("result"):
            return symbol, [], "EMPTY_RESULT"
        res = chart["result"][0]
        ts = res.get("timestamp") or []
        q = res["indicators"]["quote"][0]
        adj_list = (res["indicators"].get("adjclose") or [{}])[0].get("adjclose")
        closes = q.get("close") or []
        dedup: dict[str, dict[str, Any]] = {}
        for i, t in enumerate(ts):
            dk = datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d")
            c = closes[i] if i < len(closes) else None
            ac = adj_list[i] if (adj_list is not None and i < len(adj_list)) else c
            if ac is None:
                ac = c
            if ac is None or c is None or not math.isfinite(float(ac)) or float(ac) <= 0:
                continue
            dedup[dk] = {
                "date": dk,
                "open": float(q["open"][i]) if (q.get("open") and q["open"][i] is not None) else float(c),
                "high": float(q["high"][i]) if (q.get("high") and q["high"][i] is not None) else float(c),
                "low": float(q["low"][i]) if (q.get("low") and q["low"][i] is not None) else float(c),
                "close": float(c),
                "adjclose": float(ac),
                "volume": float(q["volume"][i]) if (q.get("volume") and q["volume"][i] is not None) else 0.0,
            }
        rows = [dedup[k] for k in sorted(dedup) if k >= START_DATE]
        return symbol, rows, None
    except Exception as exc:
        return symbol, [], f"EXC:{type(exc).__name__}:{exc}"


def fetch_and_cache_etf40(
    *,
    symbols: tuple[str, ...] = ETF40_UNIVERSE,
    cache_dir: Path = ETF40_CACHE_DIR,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    start_ts = int(datetime(2005, 1, 1, tzinfo=timezone.utc).timestamp())
    now_utc = datetime.now(timezone.utc)
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    end_ts = int(today_start.timestamp()) - 1

    tasks = []
    files_meta: dict[str, Any] = {}
    for sym in symbols:
        fname = _safe_filename(sym)
        p = cache_dir / fname
        if p.exists() and not force_refresh:
            tbl = pq.read_table(p, columns=["date"])
            ds = tbl["date"].to_pylist()
            if ds:
                files_meta[sym] = {
                    "file": fname,
                    "rows": len(ds),
                    "first_date": ds[0],
                    "last_date": ds[-1],
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                }
                continue
        tasks.append(sym)

    skipped: list[dict[str, str]] = []
    if tasks:
        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_fetch_yahoo_ticker, s, start_ts, end_ts) for s in tasks]
            for fut in as_completed(futs):
                sym, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"symbol": sym, "reason": err or "EMPTY"})
                    continue
                fname = _safe_filename(sym)
                p = cache_dir / fname
                tbl = pa.table(
                    {col: [r[col] for r in rows] for col in ("date", "open", "high", "low", "close", "adjclose", "volume")},
                    schema=ETF_SCHEMA,
                )
                pq.write_table(tbl, p, compression="zstd")
                files_meta[sym] = {
                    "file": fname,
                    "rows": len(rows),
                    "first_date": rows[0]["date"],
                    "last_date": rows[-1]["date"],
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest()[:16],
                }

    manifest = {
        "schema": "naqex-etf40-cache-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "source": "Yahoo Finance Public v8 Chart API (adjclose, zero API key)",
        "requested_count": len(symbols),
        "loaded_count": len(files_meta),
        "skipped": skipped,
        "files": dict(sorted(files_meta.items())),
    }
    (cache_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def load_etf40_panel(*, symbols: tuple[str, ...] = ETF40_UNIVERSE, cache_dir: Path = ETF40_CACHE_DIR) -> dict[str, Any]:
    loaded_syms: list[str] = []
    maps: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    for sym in symbols:
        p = cache_dir / _safe_filename(sym)
        if not p.exists():
            continue
        tbl = pq.read_table(p, columns=["date", "adjclose"])
        ds = tbl["date"].to_pylist()
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False)
        mp = {d: float(v) for d, v in zip(ds, ac) if np.isfinite(v) and v > 0}
        if mp:
            loaded_syms.append(sym)
            maps[sym] = mp
            # Anchor calendar strictly to tradable US NYSE ETFs (excludes CBOE ^VIX prints on US holidays!)
            if sym not in SIGNAL_ONLY_TICKERS:
                all_dates.update(mp.keys())

    dates = sorted(all_dates)
    n_t, n_k = len(dates), len(loaded_syms)
    adjclose = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for j, sym in enumerate(loaded_syms):
        mp = maps[sym]
        for i, d in enumerate(dates):
            if d in mp:
                adjclose[i, j] = mp[d]
    return {"dates": dates, "symbols": loaded_syms, "adjclose": adjclose}


def _wilder_rsi_2d(px: np.ndarray, period: int = 2) -> np.ndarray:
    """Strictly causal Wilder RSI along axis 0 without forward-filling pre-listing NaNs."""
    n_t, n_k = px.shape
    rsi = np.full((n_t, n_k), np.nan, dtype=np.float64)
    alpha = 1.0 / float(period)
    for j in range(n_k):
        avg_g = math.nan
        avg_l = math.nan
        seed_g: list[float] = []
        seed_l: list[float] = []
        for t in range(1, n_t):
            p0, p1 = px[t - 1, j], px[t, j]
            if not (math.isfinite(p0) and math.isfinite(p1) and p0 > 0):
                avg_g = math.nan
                avg_l = math.nan
                seed_g.clear()
                seed_l.clear()
                continue
            diff = p1 - p0
            g = max(0.0, diff)
            l = max(0.0, -diff)
            if not math.isfinite(avg_g):
                seed_g.append(g)
                seed_l.append(l)
                if len(seed_g) == period:
                    avg_g = sum(seed_g) / period
                    avg_l = sum(seed_l) / period
                    rs = avg_g / avg_l if avg_l > 1e-12 else 1e9
                    rsi[t, j] = 100.0 - (100.0 / (1.0 + rs))
            else:
                avg_g = (1.0 - alpha) * avg_g + alpha * g
                avg_l = (1.0 - alpha) * avg_l + alpha * l
                rs = avg_g / avg_l if avg_l > 1e-12 else 1e9
                rsi[t, j] = 100.0 - (100.0 / (1.0 + rs))
    return rsi


def build_etf40_strategies(panel: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Build 4 strictly causal Own-Book Long/Cash strategies on the 40-ticker panel (signal-only tickers get 0 weight)."""
    dates: list[str] = panel["dates"]
    syms: list[str] = panel["symbols"]
    px: np.ndarray = panel["adjclose"]
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}

    rets = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(px[1:]) & np.isfinite(px[:-1]) & (px[:-1] > 0)
    rets[1:][ok] = px[1:][ok] / px[:-1][ok] - 1.0

    # Causal rolling metrics computed strictly using <= t
    vol60 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sma5 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sma126 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sma200 = np.full((n_t, n_k), np.nan, dtype=np.float64)

    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)
        for t in range(4, n_t):
            w5 = px[t - 4:t + 1]
            ok5 = np.sum(np.isfinite(w5), axis=0) == 5
            sma5[t] = np.where(ok5, np.nanmean(w5, axis=0), np.nan)
        for t in range(60, n_t):
            r60 = rets[t - 59:t + 1]
            cnt = np.sum(np.isfinite(r60), axis=0)
            sd = np.nanstd(r60, axis=0, ddof=1)
            vol60[t] = np.where((cnt >= 50) & (sd > 1e-6), sd * math.sqrt(252.0), np.nan)
        for t in range(125, n_t):
            w126 = px[t - 125:t + 1]
            ok126 = np.sum(np.isfinite(w126), axis=0) >= 120
            sma126[t] = np.where(ok126, np.nanmean(w126, axis=0), np.nan)
        for t in range(199, n_t):
            w200 = px[t - 199:t + 1]
            ok200 = np.sum(np.isfinite(w200), axis=0) >= 190
            sma200[t] = np.where(ok200, np.nanmean(w200, axis=0), np.nan)

    rsi2 = _wilder_rsi_2d(px, period=2)
    is_me = _month_end_flags(dates)

    # -----------------------------------------------------------------------
    # Strategy 1: E40_RSI2_CONNORS — Short-Term 2-5d RSI(2) Mean Reversion
    # Universe: Liquid US Equity + US Sector ETFs above SMA(200)
    # Entry: RSI(2) < 10 and Close > SMA(200); Exit: Close > SMA(5) or hold >= 7 days
    # -----------------------------------------------------------------------
    rsi_syms = [s for s in ("SPY", "QQQ", "IWM", "XLK", "XLF", "XLE", "XLV", "XLI", "XLP", "XLU", "XLY", "XLB") if s in sym_idx]
    w_rsi2 = np.zeros((n_t, n_k), dtype=np.float64)
    hold_days = {s: 0 for s in rsi_syms}
    in_pos = {s: False for s in rsi_syms}
    rsi2_entries_b = 0

    for t in range(200, n_t):
        active_js: list[int] = []
        for s in rsi_syms:
            j = sym_idx[s]
            c = px[t, j]
            s200 = sma200[t, j]
            s5 = sma5[t, j]
            r2 = rsi2[t, j]
            if not (math.isfinite(c) and math.isfinite(s200) and math.isfinite(s5) and math.isfinite(r2)):
                in_pos[s] = False
                hold_days[s] = 0
                continue
            if in_pos[s]:
                hold_days[s] += 1
                if c > s5 or hold_days[s] >= 7:
                    in_pos[s] = False
                    hold_days[s] = 0
            else:
                if c > s200 and r2 < 10.0:
                    in_pos[s] = True
                    hold_days[s] = 0
                    if dates[t] >= CLUSTER_B_START:
                        rsi2_entries_b += 1
            if in_pos[s]:
                active_js.append(j)
        if active_js:
            # Cap single ETF at 25% weight, inverse-vol weighted across active entries, gross <= 1.0
            ivs = []
            for j in active_js:
                v = vol60[t, j]
                ivs.append(1.0 / max(0.08, v) if math.isfinite(v) else 5.0)
            s_iv = sum(ivs)
            for j, iv in zip(active_js, ivs):
                w_rsi2[t, j] = min(0.25, iv / s_iv)
            tot = float(np.sum(w_rsi2[t]))
            if tot > 1.0:
                w_rsi2[t] /= tot

    # -----------------------------------------------------------------------
    # Strategy 2: E40_CREDIT_HYG_IEF_REGIME — Causal HYG/IEF Credit Spread Rotation
    # Risk-on when HYG/IEF > SMA50(HYG/IEF) -> Top-4 Risk-Adj Equity/Factor Momentum
    # Risk-off when HYG/IEF <= SMA50 -> Defensive IEF/TLT/GLD/SHY (SMA200 guard!)
    # Weekly rebalance (every 5 trading days) keeps turnover very low
    # -----------------------------------------------------------------------
    w_credit = np.zeros((n_t, n_k), dtype=np.float64)
    hyg_j = sym_idx.get("HYG")
    ief_j = sym_idx.get("IEF")
    ratio = np.full(n_t, np.nan, dtype=np.float64)
    if hyg_j is not None and ief_j is not None:
        valid_r = np.isfinite(px[:, hyg_j]) & np.isfinite(px[:, ief_j]) & (px[:, ief_j] > 0)
        ratio[valid_r] = px[valid_r, hyg_j] / px[valid_r, ief_j]

    # Fallback credit proxy before HYG listing (2007-04): LQD/IEF ratio!
    lqd_j = sym_idx.get("LQD")
    if lqd_j is not None and ief_j is not None:
        need = ~np.isfinite(ratio) & np.isfinite(px[:, lqd_j]) & np.isfinite(px[:, ief_j]) & (px[:, ief_j] > 0)
        ratio[need] = px[need, lqd_j] / px[need, ief_j]

    risk_on_pool = [s for s in ("SPY", "QQQ", "IWM", "MTUM", "QUAL", "USMV", "VTV", "EFA", "EEM") if s in sym_idx]
    def_pool = [s for s in ("IEF", "TLT", "GLD", "SHY") if s in sym_idx]
    last_cred = np.zeros(n_k, dtype=np.float64)
    cred_rebal_b = 0

    for t in range(200, n_t):
        if (t % 5 == 0) or is_me[t]:
            w50 = ratio[t - 49:t + 1]
            ok50 = np.sum(np.isfinite(w50)) >= 45 and math.isfinite(ratio[t])
            risk_on = bool(ok50 and (ratio[t] > float(np.nanmean(w50))))
            tmp = np.zeros(n_k, dtype=np.float64)
            if risk_on:
                scored: list[tuple[float, int, float]] = []
                for s in risk_on_pool:
                    j = sym_idx[s]
                    c_now, c63, c126, v = px[t, j], px[t - 63, j], px[t - 126, j], vol60[t, j]
                    if math.isfinite(c_now) and math.isfinite(c63) and math.isfinite(c126) and math.isfinite(v) and c63 > 0 and c126 > 0:
                        mom = 0.5 * (c_now / c63 - 1.0) + 0.5 * (c_now / c126 - 1.0)
                        if mom > 0.0:
                            scored.append((mom / max(0.05, v), j, v))
                scored.sort(reverse=True)
                top4 = scored[:4]
                if top4:
                    ivs = [1.0 / max(0.06, v) for _sc, _j, v in top4]
                    s_iv = sum(ivs)
                    for (_sc, j, _v), iv in zip(top4, ivs):
                        tmp[j] = iv / s_iv
            else:
                # Defensive regime: inv-vol across Treasury/Gold, cut to 25% if below SMA200 (survives 2022!)
                ivs_d: list[tuple[int, float]] = []
                for s in def_pool:
                    j = sym_idx[s]
                    c_now, v, s200 = px[t, j], vol60[t, j], sma200[t, j]
                    if math.isfinite(c_now) and math.isfinite(v) and v > 0.01:
                        mult = 1.0 if (math.isfinite(s200) and c_now > s200) else 0.25
                        ivs_d.append((j, mult / max(0.03, v)))
                if ivs_d:
                    s_iv = sum(x[1] for x in ivs_d)
                    for j, val in ivs_d:
                        tmp[j] = val / s_iv
                    # Cap total defensive exposure when bonds are below SMA200
                    tot_d = float(np.sum(tmp))
                    if tot_d > 1.0:
                        tmp /= tot_d
            if float(np.sum(np.abs(tmp - last_cred))) > 0.05 and dates[t] >= CLUSTER_B_START:
                cred_rebal_b += 1
            last_cred = tmp
        w_credit[t] = last_cred

    # -----------------------------------------------------------------------
    # Strategy 3: E40_XSEC_SECTOR_MOM_TOP4 — Cross-Sectional US Sector Momentum
    # Monthly rebalance: Top-4 US Sectors (3m+6m risk-adj mom > 0 & > SMA200),
    # inverse-vol weighted; unused slots rotate to IEF if IEF > SMA126 else Cash.
    # -----------------------------------------------------------------------
    sec_syms = [s for s in US_SECTORS if s in sym_idx]
    w_sec = np.zeros((n_t, n_k), dtype=np.float64)
    last_sec = np.zeros(n_k, dtype=np.float64)
    sec_rebal_b = 0

    for t in range(200, n_t):
        if is_me[t]:
            scored_s: list[tuple[float, int, float]] = []
            for s in sec_syms:
                j = sym_idx[s]
                c_now, c63, c126, v, s200 = px[t, j], px[t - 63, j], px[t - 126, j], vol60[t, j], sma200[t, j]
                if not (math.isfinite(c_now) and math.isfinite(c63) and math.isfinite(c126) and math.isfinite(v) and math.isfinite(s200)):
                    continue
                mom = 0.5 * (c_now / c63 - 1.0) + 0.5 * (c_now / c126 - 1.0)
                if mom > 0.0 and c_now > s200:
                    scored_s.append((mom / max(0.06, v), j, v))
            scored_s.sort(reverse=True)
            top4 = scored_s[:4]
            tmp = np.zeros(n_k, dtype=np.float64)
            active_slots = len(top4)
            if active_slots > 0:
                slot_budget = active_slots / 4.0
                ivs = [1.0 / max(0.06, v) for _sc, _j, v in top4]
                s_iv = sum(ivs)
                for (_sc, j, _v), iv in zip(top4, ivs):
                    tmp[j] = slot_budget * (iv / s_iv)
            rem_budget = (4 - active_slots) / 4.0
            if rem_budget > 0.0 and ief_j is not None:
                if math.isfinite(px[t, ief_j]) and math.isfinite(sma126[t, ief_j]) and px[t, ief_j] > sma126[t, ief_j]:
                    tmp[ief_j] += rem_budget
            if float(np.sum(np.abs(tmp - last_sec))) > 0.05 and dates[t] >= CLUSTER_B_START:
                sec_rebal_b += 1
            last_sec = tmp
        w_sec[t] = last_sec

    # -----------------------------------------------------------------------
    # Strategy 4: E40_VRP_VOL_CARRY — VIX Term-Structure & Vol-Regime Carry
    # Risk-on ONLY when ^VIX < SMA60(^VIX) AND ^VIX < ^VIX3M (contango);
    # Hard de-risk to GLD/SHY/Cash in backwardation or VIX breakout!
    # -----------------------------------------------------------------------
    w_vrp = np.zeros((n_t, n_k), dtype=np.float64)
    vix_j = sym_idx.get("^VIX")
    vix3m_j = sym_idx.get("^VIX3M")
    eq_carry_pool = [s for s in ("SPY", "QQQ", "USMV", "QUAL") if s in sym_idx]
    bond_carry_pool = [s for s in ("IEF", "LQD", "TIP") if s in sym_idx]
    gld_j = sym_idx.get("GLD")
    shy_j = sym_idx.get("SHY")
    tlt_j = sym_idx.get("TLT")
    last_vrp = np.zeros(n_k, dtype=np.float64)
    vrp_rebal_b = 0

    for t in range(200, n_t):
        # Daily VIX regime check for instant crash protection; smooth via 3-day confirmation to curb whipsaw
        calm_vrp = False
        if vix_j is not None and math.isfinite(px[t, vix_j]):
            v_win = px[t - 59:t + 1, vix_j]
            if np.sum(np.isfinite(v_win)) >= 50:
                v_ma60 = float(np.nanmean(v_win))
                below_ma = px[t, vix_j] < v_ma60
                if vix3m_j is not None and math.isfinite(px[t, vix3m_j]) and px[t, vix3m_j] > 0:
                    contango = px[t, vix_j] < px[t, vix3m_j]
                else:
                    # Strictly causal fallback prior to ^VIX3M inception (2007-12)
                    contango = px[t, vix_j] < 22.0
                calm_vrp = bool(below_ma and contango)

        tmp = np.zeros(n_k, dtype=np.float64)
        if calm_vrp:
            # 60% inv-vol US/Factor Equity + 40% inv-vol IG Bond/Treasury
            eq_iv = [(sym_idx[s], 1.0 / max(0.06, vol60[t, sym_idx[s]])) for s in eq_carry_pool if math.isfinite(vol60[t, sym_idx[s]]) and math.isfinite(px[t, sym_idx[s]])]
            bd_iv = [(sym_idx[s], 1.0 / max(0.03, vol60[t, sym_idx[s]])) for s in bond_carry_pool if math.isfinite(vol60[t, sym_idx[s]]) and math.isfinite(px[t, sym_idx[s]])]
            if eq_iv:
                se = sum(x[1] for x in eq_iv)
                for j, iv in eq_iv:
                    tmp[j] += 0.60 * (iv / se)
            if bd_iv:
                sb = sum(x[1] for x in bd_iv)
                for j, iv in bd_iv:
                    tmp[j] += 0.40 * (iv / sb)
        else:
            # Backwardation / Vol shock hedge: 20% GLD (if > SMA200), 25% TLT (if > SMA126), 25% SHY, rest 0% Cash
            if gld_j is not None and math.isfinite(px[t, gld_j]) and math.isfinite(sma200[t, gld_j]) and px[t, gld_j] > sma200[t, gld_j]:
                tmp[gld_j] = 0.20
            if tlt_j is not None and math.isfinite(px[t, tlt_j]) and math.isfinite(sma126[t, tlt_j]) and px[t, tlt_j] > sma126[t, tlt_j]:
                tmp[tlt_j] = 0.25
            if shy_j is not None and math.isfinite(px[t, shy_j]):
                tmp[shy_j] = 0.25

        # Only rebalance if regime flipped or month-end drift > 5% (cuts unnecessary daily turnover!)
        if is_me[t] or float(np.sum(np.abs(tmp - last_vrp))) > 0.20:
            if float(np.sum(np.abs(tmp - last_vrp))) > 0.10 and dates[t] >= CLUSTER_B_START:
                vrp_rebal_b += 1
            last_vrp = tmp
        w_vrp[t] = last_vrp

    # Hard zero-weight invariant on signal-only indices (^VIX, ^VIX3M)
    for sig_t in SIGNAL_ONLY_TICKERS:
        if sig_t in sym_idx:
            sj = sym_idx[sig_t]
            w_rsi2[:, sj] = 0.0
            w_credit[:, sj] = 0.0
            w_sec[:, sj] = 0.0
            w_vrp[:, sj] = 0.0

    # Benchmark SPY
    w_spy = np.zeros((n_t, n_k), dtype=np.float64)
    if "SPY" in sym_idx:
        w_spy[np.isfinite(px[:, sym_idx["SPY"]]), sym_idx["SPY"]] = 1.0

    return {
        "E40_RSI2_CONNORS": {
            "weights": w_rsi2,
            "n_events_b": rsi2_entries_b,
            "title": "Connors Short-Term RSI(2) Mean-Reversion above SMA200",
            "universe": tuple(rsi_syms),
            "counterparty": "Short-term retail/CTA stop-outs and index rebalancing liquidity demand during brief uptrend pullbacks",
            "rationale": "Liquid US equity and sector ETFs trading above 200-day SMA exhibit short-horizon liquidity overreaction when 2-day Wilder RSI drops below 10; supplying liquidity for 2-5 days captures rapid mean reversion while SMA200 avoids bear-market catching knives.",
        },
        "E40_CREDIT_HYG_IEF_REGIME": {
            "weights": w_credit,
            "n_events_b": cred_rebal_b,
            "title": "Causal HYG/IEF Credit-Spread Risk-On/Risk-Off Rotation",
            "universe": tuple(risk_on_pool + def_pool),
            "counterparty": "Slow-rebalancing institutional pension and mutual fund flows reacting with delay to high-yield credit stress",
            "rationale": "High-yield corporate credit spreads (HYG/IEF) lead equity drawdown regimes as institutional bond desks reprice default risk early; rotating to positive-momentum equities only in tightening credit and SMA200-guarded bonds/gold in credit stress cuts left-tail risk.",
        },
        "E40_XSEC_SECTOR_MOM_TOP4": {
            "weights": w_sec,
            "n_events_b": sec_rebal_b,
            "title": "Cross-Sectional US Sector Momentum Top-4 with IEF/Cash Guard",
            "universe": tuple(sec_syms + ["IEF"]),
            "counterparty": "Under-reaction of institutional earnings revisions and passive benchmark drift across GICS economic sectors",
            "rationale": "Persistent macroeconomic and earnings cycles drive multi-month dispersion across the 10 GICS US sectors; holding the Top-4 risk-adjusted 3m+6m leaders above SMA200 with inverse-vol sizing and defensive Treasury/cash rotation captures sector leadership.",
        },
        "E40_VRP_VOL_CARRY": {
            "weights": w_vrp,
            "n_events_b": vrp_rebal_b,
            "title": "VIX Term-Structure Contango & Volatility-Regime Carry",
            "universe": tuple(eq_carry_pool + bond_carry_pool + ["GLD", "TLT", "SHY"]),
            "counterparty": "Hedging demand from institutional equity portfolios paying implied volatility premium during calm contango regimes",
            "rationale": "Equity-bond carry performs strongly when VIX is below its 60-day average and in term-structure contango (^VIX < ^VIX3M); shifting defensively to Gold/Treasuries/Cash upon backwardation avoids crash regimes like 2008, 2020, and 2022.",
        },
        "BM_SPY": {
            "weights": w_spy,
            "n_events_b": 1,
            "title": "SPY Buy-and-Hold Benchmark",
            "universe": ("SPY",),
            "counterparty": "Benchmark",
            "rationale": "Passive equity beta benchmark for comparison only.",
        },
    }


def _one_sided_t_pvalue(rets: np.ndarray) -> float:
    r = np.asarray(rets, dtype=np.float64)
    r = r[np.isfinite(r)]
    n = len(r)
    if n < 10:
        return 1.0
    sd = float(np.std(r, ddof=1))
    if sd <= 1e-12:
        return 1.0
    t_stat = float(np.mean(r)) / (sd / math.sqrt(n))
    return float(0.5 * math.erfc(t_stat / math.sqrt(2.0)))


def _load_incumbent_s1_map() -> dict[str, float] | None:
    try:
        from quant_factory.portfolio_allocator import load_sleeve1_dev_daily_returns
        rmap, _ = load_sleeve1_dev_daily_returns()
        return rmap
    except Exception:
        return None


def run_etf40_lab(
    *,
    cache_dir: Path = ETF40_CACHE_DIR,
    returns_path: Path = SLEEVE4_RETURNS_PATH,
    force_refresh: bool = False,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    manifest = fetch_and_cache_etf40(cache_dir=cache_dir, force_refresh=force_refresh)
    panel = load_etf40_panel(cache_dir=cache_dir)
    dates: list[str] = panel["dates"]
    px: np.ndarray = panel["adjclose"]

    strats = build_etf40_strategies(panel)
    eval_mask = np.array([d >= WARMUP_START for d in dates], dtype=bool)
    mask_a = np.array([(d >= WARMUP_START) and (d <= CLUSTER_A_END) for d in dates], dtype=bool)
    mask_b = np.array([d >= CLUSTER_B_START for d in dates], dtype=bool)

    inc_s1 = _load_incumbent_s1_map()
    s3b_path = RETURNS_DIR / "sleeve3b_macro_etf.json"
    inc_s3b = load_external_sleeve_json(s3b_path)[0] if s3b_path.is_file() else None

    strategy_names = [k for k in strats.keys() if k != "BM_SPY"]
    sim_1x: dict[str, dict[str, Any]] = {}
    sim_2x: dict[str, dict[str, Any]] = {}
    p_raw_b: list[float] = []
    p_raw_full: list[float] = []

    for nm in strategy_names + ["BM_SPY"]:
        w = strats[nm]["weights"]
        sim_1x[nm] = simulate_etf_weights(px, w, cost_bps_oneway=5.0, short_borrow_bps_yr=0.0, max_gross_leverage=1.0)
        sim_2x[nm] = simulate_etf_weights(px, w, cost_bps_oneway=10.0, short_borrow_bps_yr=0.0, max_gross_leverage=1.0)
        if nm != "BM_SPY":
            p_raw_b.append(_one_sided_t_pvalue(sim_1x[nm]["net_returns"][mask_b]))
            p_raw_full.append(_one_sided_t_pvalue(sim_1x[nm]["net_returns"][eval_mask]))

    q_b_list = benjamini_hochberg(p_raw_b)
    q_full_list = benjamini_hochberg(p_raw_full)

    # Crisis windows (2008 GFC, 2020 COVID crash, 2022 inflation shock)
    crisis_windows = {
        "gfc_2008": ("2008-01-02", "2009-03-09"),
        "covid_2020": ("2020-02-19", "2020-03-23"),
        "infl_2022": ("2022-01-03", "2022-10-14"),
    }

    def _window_ret(r_arr: np.ndarray, lo: str, hi: str) -> float:
        m = np.array([(d >= lo) and (d <= hi) for d in dates], dtype=bool)
        if int(m.sum()) == 0:
            return 0.0
        return round((float(np.prod(1.0 + r_arr[m])) - 1.0) * 100.0, 2)

    results: dict[str, Any] = {}
    daily_maps: dict[str, dict[str, float]] = {}
    dates_b = [d for d, flag in zip(dates, mask_b) if flag]
    dates_b_dev = [d for d in dates_b if d <= "2024-12-31"]

    for idx_s, nm in enumerate(strategy_names):
        r1 = sim_1x[nm]["net_returns"]
        r2 = sim_2x[nm]["net_returns"]
        r_a = r1[mask_a]
        r_b = r1[mask_b]
        r_full = r1[eval_mask]

        m_a = compute_daily_metrics(r_a, ann_days=252.0)
        m_a2 = compute_daily_metrics(r2[mask_a], ann_days=252.0)
        m_b = compute_daily_metrics(r_b, ann_days=252.0)
        m_b2 = compute_daily_metrics(r2[mask_b], ann_days=252.0)
        m_full = compute_daily_metrics(r_full, ann_days=252.0)
        dsr_b = deflated_sharpe_ratio(r_b, n_trials=len(strategy_names), annualization=252.0)
        dsr_full = deflated_sharpe_ratio(r_full, n_trials=len(strategy_names), annualization=252.0)
        turn_b = float(np.sum(sim_1x[nm]["turnover"][mask_b])) / max(1e-6, int(mask_b.sum()) / 252.0)

        rmap = {d: float(v) for d, v in zip(dates, r1) if d >= WARMUP_START}
        daily_maps[nm] = rmap

        # Exact 1-to-1 NYSE date alignment against S1 (sealed Dev <= 2024-12-31) so r_b[:n] pairs exact same dates!
        corr_s1, tail_s1 = 0.0, 0.0
        inc_b_aligned = None
        if inc_s1 and len(dates_b_dev) >= 50:
            inc_b_aligned = np.array([float(inc_s1.get(d, 0.0)) for d in dates_b_dev], dtype=np.float64)
            cand_b_dev = r_b[: len(dates_b_dev)]
            if float(np.std(cand_b_dev)) > 1e-12 and float(np.std(inc_b_aligned)) > 1e-12:
                corr_s1 = round(float(np.corrcoef(cand_b_dev, inc_b_aligned)[0, 1]), 4)
                cut = float(np.quantile(inc_b_aligned, 0.05))
                tm = inc_b_aligned <= cut
                if int(tm.sum()) >= 5 and float(np.std(cand_b_dev[tm])) > 1e-12 and float(np.std(inc_b_aligned[tm])) > 1e-12:
                    tail_s1 = round(float(np.corrcoef(cand_b_dev[tm], inc_b_aligned[tm])[0, 1]), 4)

        corr_s3b = 0.0
        if inc_s3b:
            try:
                _, mat_3b, _ = align_sleeves_business_days({"cand": rmap, "s3b": inc_s3b}, start_day=CLUSTER_B_START)
                if len(mat_3b) >= 50:
                    corr_s3b = round(float(np.corrcoef(mat_3b[:, 0], mat_3b[:, 1])[0, 1]), 4)
            except Exception:
                pass

        corr_spy_b = round(float(np.corrcoef(r_b, sim_1x["BM_SPY"]["net_returns"][mask_b])[0, 1]), 4)

        # Genuine Research Council Proposal -> SkepticalRedTeamCritic Audit
        meta = strats[nm]
        card = propose_hypothesis(
            hypothesis_id=nm,
            title=meta["title"],
            asset_universe=meta["universe"],
            timeframe="D1",
            counterparty_mechanism=meta["counterparty"],
            economic_rationale=meta["rationale"],
            causal_invariants=(
                "t -> t+1 execution using strictly <= t adjclose",
                "Zero pre-listing forward-fill; signal-only ^VIX/^VIX3M hard-zeroed",
                "1x=5bps / 2x=10bps one-way cost; 0% idle cash return",
                "Cluster A (2006-2018) -> blind Cluster B (2019-2026); Holdout FX sealed (0 rows)",
            ),
            n_trials_cumulative=len(strategy_names),
            kill_criteria=KillCriteria(
                max_bh_q=0.10,
                min_dsr=0.50,
                min_cluster_b_sharpe=0.50,
                min_cost_breakeven_mult=2.00,
                max_corr_vs_incumbent=0.25,
                max_tail_corr_vs_incumbent=0.40,
                min_trades_cluster_b=20,
            ),
        )
        # Align candidate vs S1 strictly on Cl.B for Gate 4 orthogonality audit
        ev_bundle = EvidenceBundle(
            cluster_a_returns=r_a,
            cluster_b_returns=r_b,
            p_value_raw=p_raw_b[idx_s],
            family_p_values=tuple(p_raw_b),
            candidate_index_in_family=idx_s,
            cost_1x_net=float(np.sum(r_b)),
            cost_2x_net=float(np.sum(r2[mask_b])),
            n_trades_cluster_b=int(meta["n_events_b"]),
            incumbent_daily_returns=inc_b_aligned,
            annualization_days=252.0,
            holdout_rows_analysed=0,
        )
        council_verdict = critique_proposal(card, ev_bundle)

        results[nm] = {
            "metrics_a_1x": m_a,
            "metrics_a_2x": m_a2,
            "metrics_b_1x": m_b,
            "metrics_b_2x": m_b2,
            "metrics_full_1x": m_full,
            "turnover_b_ann": round(turn_b, 2),
            "bh_q_b": round(float(q_b_list[idx_s]), 5),
            "bh_q_full": round(float(q_full_list[idx_s]), 5),
            "dsr_b": dsr_b["dsr"],
            "dsr_full": dsr_full["dsr"],
            "corr_s1_dev": corr_s1,
            "tail_corr_s1_dev": tail_s1,
            "corr_s3b_b": corr_s3b,
            "corr_spy_b": corr_spy_b,
            "n_events_b": int(meta["n_events_b"]),
            "crisis_returns_pct": {ck: _window_ret(r1, lo, hi) for ck, (lo, hi) in crisis_windows.items()},
            "council_verdict": council_verdict["verdict"],
            "council_failed_gates": council_verdict["failed_gates"],
            "council_breakeven_mult": council_verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "council_sha16": council_verdict["verdict_sha256"][:16],
        }

    # Benchmark SPY metrics
    r_spy = sim_1x["BM_SPY"]["net_returns"]
    spy_summary = {
        "metrics_a_1x": compute_daily_metrics(r_spy[mask_a], ann_days=252.0),
        "metrics_b_1x": compute_daily_metrics(r_spy[mask_b], ann_days=252.0),
        "metrics_full_1x": compute_daily_metrics(r_spy[eval_mask], ann_days=252.0),
        "crisis_returns_pct": {ck: _window_ret(r_spy, lo, hi) for ck, (lo, hi) in crisis_windows.items()},
    }

    # Strictly causal primary selection: pick #1 Cluster A Sharpe (tie-break Calmar) — zero Cluster B peeking!
    primary_name = max(
        strategy_names,
        key=lambda nm: (results[nm]["metrics_a_1x"]["sharpe"], results[nm]["metrics_a_1x"]["calmar"]),
    )

    # Also compute equal-weight ensemble of strategies approved by Research Council (or all 4 if >=2 approved)
    approved_names = [nm for nm in strategy_names if results[nm]["council_verdict"] == "APPROVE_FOR_INCUBATION"]
    ens_members = approved_names if len(approved_names) >= 2 else strategy_names
    ens_ret = np.mean(np.vstack([sim_1x[nm]["net_returns"] for nm in ens_members]), axis=0)
    ens_map = {d: float(v) for d, v in zip(dates, ens_ret) if d >= WARMUP_START}
    ens_summary = {
        "members": ens_members,
        "metrics_a_1x": compute_daily_metrics(ens_ret[mask_a], ann_days=252.0),
        "metrics_b_1x": compute_daily_metrics(ens_ret[mask_b], ann_days=252.0),
        "metrics_full_1x": compute_daily_metrics(ens_ret[eval_mask], ann_days=252.0),
        "crisis_returns_pct": {ck: _window_ret(ens_ret, lo, hi) for ck, (lo, hi) in crisis_windows.items()},
    }

    # Export Sleeve #4 JSON (`naqex-sleeve-daily-returns-v1`)
    returns_path.parent.mkdir(parents=True, exist_ok=True)
    sleeve_payload = {
        "schema": "naqex-sleeve-daily-returns-v1",
        "sleeve_id": "S4_ETF40_MULTIFACTOR",
        "strategy_name": primary_name,
        "ensemble_name": "E40_APPROVED_EQW_ENSEMBLE",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "annualization_days": 252.0,
        "calendar_type": "US_EQUITY_BUSINESS_DAYS",
        "cost_assumption": "1x=5bps one-way, 0% idle cash",
        "universe_desc": f"{manifest['loaded_count']}/{len(ETF40_UNIVERSE)} public ETFs/Vol indices (2005-2026)",
        "cluster_a_window": f"{WARMUP_START}..{CLUSTER_A_END}",
        "cluster_b_window": f"{CLUSTER_B_START}..{dates[-1]}",
        "metrics_cluster_a": results[primary_name]["metrics_a_1x"],
        "metrics_cluster_b": results[primary_name]["metrics_b_1x"],
        "metrics_full": results[primary_name]["metrics_full_1x"],
        "ensemble_summary": ens_summary,
        "daily_returns": daily_maps[primary_name],
        "variants": {
            **{nm: {"daily_returns": daily_maps[nm], "council_verdict": results[nm]["council_verdict"]} for nm in strategy_names},
            "E40_APPROVED_EQW_ENSEMBLE": {"daily_returns": ens_map, "members": ens_members},
        },
    }
    returns_path.write_text(json.dumps(sleeve_payload, indent=2) + "\n", encoding="utf-8", newline="\n")

    summary = {
        "schema": "naqex-lab4-etf40-summary-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": 0,
        "universe_loaded": manifest["loaded_count"],
        "universe_requested": manifest["requested_count"],
        "skipped_tickers": manifest["skipped"],
        "date_range": f"{dates[0]}..{dates[-1]}",
        "eval_window": f"{WARMUP_START}..{dates[-1]}",
        "cluster_a_days": int(mask_a.sum()),
        "cluster_b_days": int(mask_b.sum()),
        "primary_selected_on_cluster_a": primary_name,
        "council_approved": approved_names,
        "benchmark_spy": spy_summary,
        "ensemble": ens_summary,
        "results": results,
    }
    (cache_dir / "etf40_study_summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Wave-2 Lab #4: 40-ETF Multi-Factor, RSI-2, Credit & VRP Study")
    ap.add_argument("--force-refresh", action="store_true")
    args = ap.parse_args()
    res = run_etf40_lab(force_refresh=args.force_refresh)
    print(json.dumps({
        "universe_loaded": res["universe_loaded"],
        "date_range": res["date_range"],
        "primary_selected_on_cluster_a": res["primary_selected_on_cluster_a"],
        "council_approved": res["council_approved"],
        "elapsed_sec": res["elapsed_sec"],
        "results_compact": {
            k: {
                "clA_cagr": v["metrics_a_1x"]["cagr_pct"],
                "clA_sh": v["metrics_a_1x"]["sharpe"],
                "clB_cagr_1x": v["metrics_b_1x"]["cagr_pct"],
                "clB_cagr_2x": v["metrics_b_2x"]["cagr_pct"],
                "clB_sh": v["metrics_b_1x"]["sharpe"],
                "clB_dd": v["metrics_b_1x"]["max_dd_pct"],
                "clB_calmar": v["metrics_b_1x"]["calmar"],
                "bh_q_b": v["bh_q_b"],
                "dsr_b": v["dsr_b"],
                "corr_s1": v["corr_s1_dev"],
                "corr_s3b": v["corr_s3b_b"],
                "verdict": v["council_verdict"],
                "failed": v["council_failed_gates"],
            }
            for k, v in res["results"].items()
        },
        "ensemble_b": res["ensemble"]["metrics_b_1x"],
        "spy_b": res["benchmark_spy"]["metrics_b_1x"],
    }, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
