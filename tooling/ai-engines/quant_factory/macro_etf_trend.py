"""M4.3: Sleeve #3B — 18-Year Cross-Asset Macro ETF Trend & Risk Parity (2007-2026).

Strict anti-bias & safety boundaries:
  - Public Yahoo Finance v8 chart API (zero API key, read-only) for 12 liquid macro ETFs:
    SPY, QQQ, IWM, TLT, IEF, GLD, SLV, USO, UUP, EFA, EEM, DBC.
  - Uses dividend/split-adjusted close (`adjclose`) with ZERO pre-listing forward-fill.
  - 100% causal t -> t+1 execution: signals and vol estimates computed <= day t close
    apply to day t+1 return.
  - Explicit trading friction: 1x = 5 bps one-way + 50 bps/yr short borrow on short legs;
    2x stress = 10 bps one-way + 100 bps/yr short borrow. Idle cash earns 0% conservative.
  - Strict Cluster A (2007-01-01 .. 2018-12-31) -> blind Cluster B (2019-01-01 .. 2026-11-23).
  - Crisis alpha decomposition across 2008 GFC, 2020 COVID Crash, and 2022 Inflation Shock.
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

MACRO_CACHE_DIR = ROOT / ".runtime" / "macro-etf-cache"
SLEEVE3B_RETURNS_PATH = RETURNS_DIR / "sleeve3b_macro_etf.json"

ETF_UNIVERSE_12: tuple[str, ...] = (
    "SPY", "QQQ", "IWM", "TLT", "IEF", "GLD", "SLV", "USO", "UUP", "EFA", "EEM", "DBC",
)
MACRO_BUCKETS: dict[str, tuple[str, ...]] = {
    "EQUITIES": ("SPY", "QQQ", "IWM", "EFA", "EEM"),
    "RATES": ("TLT", "IEF"),
    "METALS": ("GLD", "SLV"),
    "COMMOD_FX": ("USO", "DBC", "UUP"),
}

START_DATE = "2007-01-01"
CLUSTER_A_END = "2018-12-31"
CLUSTER_B_START = "2019-01-01"

ETF_SCHEMA = pa.schema([
    ("date", pa.string()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
    ("adjclose", pa.float64()),
    ("volume", pa.float64()),
])


def _fetch_yahoo_etf(symbol: str, start_ts: int, end_ts: int) -> tuple[str, list[dict[str, Any]], str | None]:
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}"
    params = {"period1": start_ts, "period2": end_ts, "interval": "1d", "events": "div,splits"}
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    try:
        with httpx.Client(timeout=15.0, headers=headers) as client:
            resp = None
            for attempt in range(4):
                r = client.get(url, params=params)
                if r.status_code == 200:
                    resp = r.json()
                    break
                time.sleep(0.5 * (attempt + 1))
            if resp is None:
                return symbol, [], "HTTP_FAILED"
        res = resp["chart"]["result"][0]
        ts = res.get("timestamp", [])
        q = res["indicators"]["quote"][0]
        adj = res["indicators"]["adjclose"][0]["adjclose"]
        dedup: dict[str, dict[str, Any]] = {}
        for i, t in enumerate(ts):
            dk = datetime.fromtimestamp(int(t), timezone.utc).strftime("%Y-%m-%d")
            ac = adj[i]
            c = q["close"][i]
            if ac is None or c is None or not math.isfinite(float(ac)) or float(ac) <= 0:
                continue
            dedup[dk] = {
                "date": dk,
                "open": float(q["open"][i]) if q["open"][i] is not None else float(c),
                "high": float(q["high"][i]) if q["high"][i] is not None else float(c),
                "low": float(q["low"][i]) if q["low"][i] is not None else float(c),
                "close": float(c),
                "adjclose": float(ac),
                "volume": float(q["volume"][i]) if q["volume"][i] is not None else 0.0,
            }
        rows = [dedup[k] for k in sorted(dedup) if k >= START_DATE]
        return symbol, rows, None
    except Exception as exc:
        return symbol, [], f"EXC:{type(exc).__name__}:{exc}"


def fetch_and_cache_etfs(
    *,
    symbols: tuple[str, ...] = ETF_UNIVERSE_12,
    cache_dir: Path = MACRO_CACHE_DIR,
    force_refresh: bool = False,
) -> dict[str, Any]:
    cache_dir.mkdir(parents=True, exist_ok=True)
    start_ts = int(datetime(2007, 1, 1, tzinfo=timezone.utc).timestamp())
    now_utc = datetime.now(timezone.utc)
    # Exclude today's potentially incomplete US session by stopping at yesterday 23:59:59 UTC
    today_start = datetime(now_utc.year, now_utc.month, now_utc.day, tzinfo=timezone.utc)
    end_ts = int(today_start.timestamp()) - 1

    tasks = []
    files_meta: dict[str, Any] = {}
    for sym in symbols:
        p = cache_dir / f"{sym}.parquet"
        if p.exists() and not force_refresh:
            tbl = pq.read_table(p, columns=["date"])
            ds = tbl["date"].to_pylist()
            if ds:
                files_meta[f"{sym}.parquet"] = {
                    "rows": len(ds),
                    "first_date": ds[0],
                    "last_date": ds[-1],
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }
                continue
        tasks.append(sym)

    skipped = []
    if tasks:
        with ThreadPoolExecutor(max_workers=6) as pool:
            futs = [pool.submit(_fetch_yahoo_etf, s, start_ts, end_ts) for s in tasks]
            for fut in as_completed(futs):
                sym, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"symbol": sym, "reason": err or "EMPTY"})
                    continue
                p = cache_dir / f"{sym}.parquet"
                tbl = pa.table(
                    {col: [r[col] for r in rows] for col in ("date", "open", "high", "low", "close", "adjclose", "volume")},
                    schema=ETF_SCHEMA,
                )
                pq.write_table(tbl, p, compression="zstd")
                files_meta[f"{sym}.parquet"] = {
                    "rows": len(rows),
                    "first_date": rows[0]["date"],
                    "last_date": rows[-1]["date"],
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }

    manifest = {
        "schema": "naqex-macro-etf-cache-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "source": "Yahoo Finance Public v8 Chart API (adjclose, zero API key)",
        "symbols": list(symbols),
        "skipped": skipped,
        "files": dict(sorted(files_meta.items())),
    }
    (cache_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def load_etf_panel(*, symbols: tuple[str, ...] = ETF_UNIVERSE_12, cache_dir: Path = MACRO_CACHE_DIR) -> dict[str, Any]:
    loaded_syms: list[str] = []
    maps: dict[str, dict[str, float]] = {}
    all_dates: set[str] = set()
    for sym in symbols:
        p = cache_dir / f"{sym}.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p, columns=["date", "adjclose"])
        ds = tbl["date"].to_pylist()
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False)
        mp = {d: float(v) for d, v in zip(ds, ac) if np.isfinite(v) and v > 0}
        if mp:
            loaded_syms.append(sym)
            maps[sym] = mp
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


def simulate_etf_weights(
    adjclose: np.ndarray,
    target_w: np.ndarray,
    *,
    cost_bps_oneway: float = 5.0,
    short_borrow_bps_yr: float = 50.0,
    max_gross_leverage: float = 1.5,
) -> dict[str, Any]:
    """Strictly causal t -> t+1 ETF portfolio simulator supporting Long-Only or Long/Short."""
    n_t, n_k = adjclose.shape
    tw = np.nan_to_num(target_w, nan=0.0)
    gross_row = np.sum(np.abs(tw), axis=1, keepdims=True)
    tw = np.where(gross_row > max_gross_leverage, tw * (max_gross_leverage / np.maximum(gross_row, 1e-12)), tw)

    rets = np.zeros((n_t, n_k), dtype=np.float64)
    valid = np.isfinite(adjclose[1:]) & np.isfinite(adjclose[:-1]) & (adjclose[:-1] > 0)
    rets[1:][valid] = adjclose[1:][valid] / adjclose[:-1][valid] - 1.0

    held = np.zeros_like(tw)
    held[1:] = np.where(valid, tw[:-1], 0.0)

    prev = np.zeros_like(held)
    prev[1:] = held[:-1]
    turnover = np.sum(np.abs(held - prev), axis=1)
    short_notional = np.sum(np.maximum(0.0, -held), axis=1)

    trade_cost = turnover * (cost_bps_oneway / 10_000.0)
    borrow_cost = short_notional * (short_borrow_bps_yr / 10_000.0 / 252.0)
    gross_ret = np.sum(held * rets, axis=1)
    net_ret = gross_ret - trade_cost - borrow_cost
    return {
        "net_returns": net_ret,
        "gross_returns": gross_ret,
        "turnover": turnover,
        "held_w": held,
        "gross_exposure": np.sum(np.abs(held), axis=1),
    }


def _month_end_flags(dates: list[str]) -> np.ndarray:
    flags = np.zeros(len(dates), dtype=bool)
    for i in range(len(dates) - 1):
        if dates[i][:7] != dates[i + 1][:7]:
            flags[i] = True
    if len(dates) > 0:
        flags[-1] = True
    return flags


def build_macro_strategies(panel: dict[str, Any]) -> dict[str, tuple[str, float, np.ndarray]]:
    """Build 5 classic institutional macro strategies + 2 benchmarks (returns (family, max_gross_lev, target_w))."""
    dates = panel["dates"]
    syms = panel["symbols"]
    px = panel["adjclose"]
    n_t, n_k = px.shape
    sym_idx = {s: i for i, s in enumerate(syms)}

    rets = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(px[1:]) & np.isfinite(px[:-1]) & (px[:-1] > 0)
    rets[1:][ok] = px[1:][ok] / px[:-1][ok] - 1.0

    # Strictly causal 60-day annualized volatility & 200-day SMA
    vol60 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    sma200 = np.full((n_t, n_k), np.nan, dtype=np.float64)
    for t in range(60, n_t):
        r60 = rets[t - 59:t + 1]
        cnt = np.sum(np.isfinite(r60), axis=0)
        with np.errstate(invalid="ignore"):
            sd = np.nanstd(r60, axis=0, ddof=1)
        vol60[t] = np.where((cnt >= 50) & (sd > 1e-6), sd * math.sqrt(252.0), np.nan)
    for t in range(199, n_t):
        w200 = px[t - 199:t + 1]
        ok200 = np.sum(np.isfinite(w200), axis=0) >= 190
        with np.errstate(invalid="ignore"):
            m200 = np.nanmean(w200, axis=0)
        sma200[t] = np.where(ok200, m200, np.nan)

    is_me = _month_end_flags(dates)

    # Benchmarks: SPY & 60/40 (SPY/IEF)
    w_spy = np.zeros((n_t, n_k), dtype=np.float64)
    if "SPY" in sym_idx:
        j = sym_idx["SPY"]
        w_spy[np.isfinite(px[:, j]), j] = 1.0

    w_6040 = np.zeros((n_t, n_k), dtype=np.float64)
    if "SPY" in sym_idx and "IEF" in sym_idx:
        js, ji = sym_idx["SPY"], sym_idx["IEF"]
        both = np.isfinite(px[:, js]) & np.isfinite(px[:, ji])
        w_6040[both, js] = 0.60
        w_6040[both, ji] = 0.40

    # Strategy 1 & 2: Classic Man AHL Multi-Horizon TSMOM (Long/Short & Long-Only)
    w_tsmom_ls = np.zeros((n_t, n_k), dtype=np.float64)
    w_tsmom_lo = np.zeros((n_t, n_k), dtype=np.float64)
    last_ls = np.zeros(n_k, dtype=np.float64)
    last_lo = np.zeros(n_k, dtype=np.float64)
    target_ann_vol = 0.10

    for t in range(252, n_t):
        # Weekly rebalance (every 5 trading days) reduces noise & turnover while preserving crisis agility
        if (t % 5 == 0) or is_me[t]:
            sig_ls = np.zeros(n_k, dtype=np.float64)
            sig_lo = np.zeros(n_k, dtype=np.float64)
            n_elig = 0
            for j in range(n_k):
                v = vol60[t, j]
                c_now = px[t, j]
                if not (np.isfinite(v) and v > 0.02 and np.isfinite(c_now) and c_now > 0):
                    continue
                signs = []
                for lb in (21, 63, 126, 252):
                    c_old = px[t - lb, j]
                    if np.isfinite(c_old) and c_old > 0:
                        signs.append(1.0 if (c_now / c_old - 1.0) > 0.0 else -1.0)
                if len(signs) < 3:
                    continue
                n_elig += 1
                s_avg = float(np.mean(signs))
                inv_v = target_ann_vol / v
                sig_ls[j] = s_avg * inv_v
                if s_avg > 0.0:
                    sig_lo[j] = s_avg * inv_v
            if n_elig > 0:
                # Diversify across N assets (~sqrt(N) diversification factor bounded conservatively by gross cap)
                scale_ls = sig_ls / (n_elig ** 0.70)
                g_ls = float(np.sum(np.abs(scale_ls)))
                if g_ls > 1.5:
                    scale_ls *= (1.5 / g_ls)
                last_ls = scale_ls

                scale_lo = sig_lo / (n_elig ** 0.70)
                g_lo = float(np.sum(scale_lo))
                if g_lo > 1.0:
                    scale_lo /= g_lo
                last_lo = scale_lo
        w_tsmom_ls[t] = last_ls
        w_tsmom_lo[t] = last_lo

    # Strategy 3: Cross-Asset Dual Momentum (Monthly Rebalance, Long-Only, Defensive Bond/Cash Rotation)
    w_dual_mom = np.zeros((n_t, n_k), dtype=np.float64)
    risk_syms = [s for s in ("SPY", "QQQ", "IWM", "EFA", "EEM", "GLD", "DBC") if s in sym_idx]
    def_syms = [s for s in ("IEF", "TLT") if s in sym_idx]
    last_dm = np.zeros(n_k, dtype=np.float64)
    for t in range(252, n_t):
        if is_me[t]:
            scored: list[tuple[float, int, float]] = []
            for s in risk_syms:
                j = sym_idx[s]
                c_now, c126, c252, v = px[t, j], px[t - 126, j], px[t - 252, j], vol60[t, j]
                if not (np.isfinite(c_now) and np.isfinite(c126) and np.isfinite(c252) and np.isfinite(v) and c126 > 0 and c252 > 0):
                    continue
                mom = 0.5 * (c_now / c126 - 1.0) + 0.5 * (c_now / c252 - 1.0)
                if mom > 0.0:
                    scored.append((mom / max(0.05, v), j, v))
            scored.sort(reverse=True)
            tmp = np.zeros(n_k, dtype=np.float64)
            top3 = scored[:3]
            used_slots = len(top3)
            for _sc, j, _v in top3:
                tmp[j] = 1.0 / 3.0
            # Unused slots rotate to best positive-momentum Treasury ETF (else stay in 0% cash -> avoids 2022 bond crash!)
            rem_slots = 3 - used_slots
            if rem_slots > 0 and def_syms:
                best_def = None
                for s in def_syms:
                    j = sym_idx[s]
                    c_now, c126 = px[t, j], px[t - 126, j]
                    if np.isfinite(c_now) and np.isfinite(c126) and c126 > 0:
                        m6 = c_now / c126 - 1.0
                        if m6 > 0.0 and (best_def is None or m6 > best_def[0]):
                            best_def = (m6, j)
                if best_def is not None:
                    tmp[best_def[1]] += rem_slots / 3.0
            last_dm = tmp
        w_dual_mom[t] = last_dm

    # Strategy 4 & 5: Volatility-Parity All-Weather (Pure vs Trend-Guarded SMA200)
    w_aw_pure = np.zeros((n_t, n_k), dtype=np.float64)
    w_aw_trend = np.zeros((n_t, n_k), dtype=np.float64)
    last_aw = np.zeros(n_k, dtype=np.float64)
    last_awt = np.zeros(n_k, dtype=np.float64)
    for t in range(200, n_t):
        if is_me[t]:
            tmp_p = np.zeros(n_k, dtype=np.float64)
            tmp_t = np.zeros(n_k, dtype=np.float64)
            n_active_buckets = 0
            bucket_vecs_p = []
            bucket_vecs_t = []
            for _bname, bsyms in MACRO_BUCKETS.items():
                inv_v = {}
                for s in bsyms:
                    if s in sym_idx:
                        j = sym_idx[s]
                        v = vol60[t, j]
                        if np.isfinite(v) and v > 0.02 and np.isfinite(px[t, j]):
                            inv_v[j] = 1.0 / v
                if not inv_v:
                    continue
                n_active_buckets += 1
                sv = sum(inv_v.values())
                bp = np.zeros(n_k, dtype=np.float64)
                bt = np.zeros(n_k, dtype=np.float64)
                for j, iv in inv_v.items():
                    w_in_b = iv / sv
                    bp[j] = w_in_b
                    # Trend guard: full weight if close > SMA200, else cut to 25% (protects 2022 bond+equity selloff!)
                    above = np.isfinite(sma200[t, j]) and px[t, j] > sma200[t, j]
                    bt[j] = w_in_b * (1.0 if above else 0.25)
                bucket_vecs_p.append(bp)
                bucket_vecs_t.append(bt)
            if n_active_buckets > 0:
                # Equal risk across buckets (normalize each bucket by its realized vol proxy, cap total weight <= 1.0)
                for bp, bt in zip(bucket_vecs_p, bucket_vecs_t):
                    tmp_p += bp / n_active_buckets
                    tmp_t += bt / n_active_buckets
                sp = float(tmp_p.sum())
                if sp > 1.0:
                    tmp_p /= sp
                st = float(tmp_t.sum())
                if st > 1.0:
                    tmp_t /= st
                last_aw = tmp_p
                last_awt = tmp_t
        w_aw_pure[t] = last_aw
        w_aw_trend[t] = last_awt

    return {
        "BM_SPY": ("BENCHMARK", 1.0, w_spy),
        "BM_60_40": ("BENCHMARK", 1.0, w_6040),
        "M1_AHL_TSMOM_LS_VOL10": ("TSMOM", 1.5, w_tsmom_ls),
        "M2_AHL_TSMOM_LO_VOL10": ("TSMOM", 1.0, w_tsmom_lo),
        "M3_DUAL_MOMENTUM_TOP3": ("DUAL_MOMENTUM", 1.0, w_dual_mom),
        "M4_ALL_WEATHER_VOL_PARITY": ("RISK_PARITY", 1.0, w_aw_pure),
        "M5_VOL_PARITY_TREND_GUARD": ("RISK_PARITY", 1.0, w_aw_trend),
    }


def _crisis_window(dates: list[str], r: np.ndarray, s_d: str, e_d: str) -> dict[str, Any]:
    mask = np.array([s_d <= d <= e_d for d in dates])
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
    }


def run_macro_etf_study(*, fetch: bool = True, cache_dir: Path = MACRO_CACHE_DIR, returns_out: Path = SLEEVE3B_RETURNS_PATH) -> dict[str, Any]:
    t0 = time.perf_counter()
    if fetch:
        fetch_and_cache_etfs(cache_dir=cache_dir)
    panel = load_etf_panel(cache_dir=cache_dir)
    dates = panel["dates"]
    strats = build_macro_strategies(panel)

    # Start evaluation cleanly after 252 trading-day warmup (2008-01-02 onwards -> full 18.9 yrs including 2008 GFC!)
    eval_start = "2008-01-02"
    ma = np.array([eval_start <= d <= CLUSTER_A_END for d in dates])
    mb = np.array([d >= CLUSTER_B_START for d in dates])
    mall = np.array([d >= eval_start for d in dates])

    results: dict[str, Any] = {}
    daily_1x: dict[str, dict[str, float]] = {}
    cand_names: list[str] = []

    for name, (fam, max_lev, w) in strats.items():
        sim1 = simulate_etf_weights(panel["adjclose"], w, cost_bps_oneway=5.0, short_borrow_bps_yr=50.0, max_gross_leverage=max_lev)
        sim2 = simulate_etf_weights(panel["adjclose"], w, cost_bps_oneway=10.0, short_borrow_bps_yr=100.0, max_gross_leverage=max_lev)
        exp = sim1["gross_exposure"]
        results[name] = {
            "family": fam,
            "max_gross_lev": max_lev,
            "cluster_a_1x": compute_daily_metrics(sim1["net_returns"][ma], sim1["turnover"][ma], exp[ma], ann_days=252.0),
            "cluster_a_2x": compute_daily_metrics(sim2["net_returns"][ma], sim2["turnover"][ma], exp[ma], ann_days=252.0),
            "cluster_b_1x": compute_daily_metrics(sim1["net_returns"][mb], sim1["turnover"][mb], exp[mb], ann_days=252.0),
            "cluster_b_2x": compute_daily_metrics(sim2["net_returns"][mb], sim2["turnover"][mb], exp[mb], ann_days=252.0),
            "full_1x": compute_daily_metrics(sim1["net_returns"][mall], sim1["turnover"][mall], exp[mall], ann_days=252.0),
            "crisis_alpha": {
                "gfc_2008_2009": _crisis_window(dates, sim1["net_returns"], "2008-01-02", "2009-03-09"),
                "covid_2020_crash": _crisis_window(dates, sim1["net_returns"], "2020-02-19", "2020-03-23"),
                "covid_2020_full": _crisis_window(dates, sim1["net_returns"], "2020-01-01", "2020-12-31"),
                "inflation_2022_peak_to_trough": _crisis_window(dates, sim1["net_returns"], "2022-01-03", "2022-10-14"),
                "inflation_2022_full": _crisis_window(dates, sim1["net_returns"], "2022-01-01", "2022-12-31"),
            },
        }
        daily_1x[name] = {d: float(rv) for d, rv in zip(dates, sim1["net_returns"]) if d >= eval_start}
        if fam != "BENCHMARK":
            cand_names.append(name)

    m_total = len(cand_names)
    qa_list = benjamini_hochberg([results[n]["cluster_a_1x"]["p_one_sided_nw"] for n in cand_names])
    qb_list = benjamini_hochberg([results[n]["cluster_b_1x"]["p_one_sided_nw"] for n in cand_names])
    qf_list = benjamini_hochberg([results[n]["full_1x"]["p_one_sided_nw"] for n in cand_names])
    spy_b = np.array([daily_1x["BM_SPY"][d] for d in dates if d >= CLUSTER_B_START], dtype=np.float64)

    for n, qa, qb, qf in zip(cand_names, qa_list, qb_list, qf_list):
        ra = np.array([daily_1x[n][d] for d in dates if eval_start <= d <= CLUSTER_A_END], dtype=np.float64)
        rb = np.array([daily_1x[n][d] for d in dates if d >= CLUSTER_B_START], dtype=np.float64)
        rf = np.array([daily_1x[n][d] for d in dates if d >= eval_start], dtype=np.float64)
        results[n]["bh_q_cluster_a"] = round(qa, 5)
        results[n]["bh_q_cluster_b"] = round(qb, 5)
        results[n]["bh_q_full"] = round(qf, 5)
        results[n]["dsr_cluster_a"] = deflated_sharpe_ratio(ra, n_trials=m_total, annualization=252.0)
        results[n]["dsr_cluster_b"] = deflated_sharpe_ratio(rb, n_trials=m_total, annualization=252.0)
        results[n]["dsr_full"] = deflated_sharpe_ratio(rf, n_trials=m_total, annualization=252.0)
        corr_spy = float(np.corrcoef(rb, spy_b)[0, 1]) if np.std(rb) > 1e-12 else 0.0
        results[n]["corr_vs_spy_cluster_b"] = round(corr_spy, 4)

    # Select primary strictly on Cluster A (2008-2018) by Calmar * Sharpe
    primary = max(cand_names, key=lambda n: results[n]["cluster_a_1x"]["calmar"] * max(0.0, results[n]["cluster_a_1x"]["sharpe"]))

    # Also build equal-risk blend of M1_AHL_TSMOM_LS_VOL10 + M5_VOL_PARITY_TREND_GUARD (classic Trend + All-Weather)
    blend_days = sorted(daily_1x["M1_AHL_TSMOM_LS_VOL10"].keys())
    blend_ret = {d: 0.5 * daily_1x["M1_AHL_TSMOM_LS_VOL10"][d] + 0.5 * daily_1x["M5_VOL_PARITY_TREND_GUARD"][d] for d in blend_days}
    b_arr = np.array([blend_ret[d] for d in blend_days], dtype=np.float64)
    b_ma = np.array([eval_start <= d <= CLUSTER_A_END for d in blend_days])
    b_mb = np.array([d >= CLUSTER_B_START for d in blend_days])
    blend_summary = {
        "name": "MACRO_50TSMOM_LS_50ALLWEATHER_TG",
        "cluster_a_1x": compute_daily_metrics(b_arr[b_ma], ann_days=252.0),
        "cluster_b_1x": compute_daily_metrics(b_arr[b_mb], ann_days=252.0),
        "full_1x": compute_daily_metrics(b_arr, ann_days=252.0),
        "crisis_alpha": {
            "gfc_2008_2009": _crisis_window(blend_days, b_arr, "2008-01-02", "2009-03-09"),
            "covid_2020_crash": _crisis_window(blend_days, b_arr, "2020-02-19", "2020-03-23"),
            "inflation_2022_peak_to_trough": _crisis_window(blend_days, b_arr, "2022-01-03", "2022-10-14"),
            "inflation_2022_full": _crisis_window(blend_days, b_arr, "2022-01-01", "2022-12-31"),
        },
        "dsr_cluster_b": deflated_sharpe_ratio(b_arr[b_mb], n_trials=m_total, annualization=252.0),
    }

    returns_out.parent.mkdir(parents=True, exist_ok=True)
    sleeve_payload = {
        "schema": "naqex-sleeve-daily-returns-v1",
        "sleeve_id": "sleeve3b_macro_etf",
        "strategy_name": primary,
        "blend_name": "MACRO_50TSMOM_LS_50ALLWEATHER_TG",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "annualization_days": 252.0,
        "calendar_type": "us_trading_days",
        "cost_assumption": "5 bps one-way ETF friction + 50 bps/yr short borrow (0% idle cash yield)",
        "universe_desc": "12 liquid global macro ETFs (SPY,QQQ,IWM,TLT,IEF,GLD,SLV,USO,UUP,EFA,EEM,DBC)",
        "cluster_a_window": [eval_start, CLUSTER_A_END],
        "cluster_b_window": [CLUSTER_B_START, dates[-1]],
        "metrics_cluster_a": results[primary]["cluster_a_1x"],
        "metrics_cluster_b": results[primary]["cluster_b_1x"],
        "metrics_full": results[primary]["full_1x"],
        "blend_summary": blend_summary,
        "daily_returns": daily_1x[primary],
        "variants": {
            "MACRO_50TSMOM_LS_50ALLWEATHER_TG": blend_ret,
            **daily_1x,
        },
    }
    returns_out.write_text(json.dumps(sleeve_payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    summary = {
        "schema": "naqex-sleeve3b-macro-etf-v1",
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "symbols_loaded": panel["symbols"],
        "raw_date_range": [dates[0], dates[-1], len(dates)],
        "eval_start": eval_start,
        "primary_selected_on_cluster_a": primary,
        "blend_summary": blend_summary,
        "strategies": results,
        "returns_json_path": str(returns_out),
    }
    (cache_dir / "macro_study_summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="M4.3 Sleeve #3B 18-Year Cross-Asset Macro ETF Trend & Risk Parity")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    s = run_macro_etf_study(fetch=not args.no_fetch)
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "symbols_loaded": len(s["symbols_loaded"]),
        "raw_date_range": s["raw_date_range"],
        "primary_selected_on_cluster_a": s["primary_selected_on_cluster_a"],
        "primary_a": s["strategies"][s["primary_selected_on_cluster_a"]]["cluster_a_1x"],
        "primary_b": s["strategies"][s["primary_selected_on_cluster_a"]]["cluster_b_1x"],
        "blend_summary": s["blend_summary"],
        "returns_json_path": s["returns_json_path"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
