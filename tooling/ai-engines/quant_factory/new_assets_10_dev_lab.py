"""C2.2 — Lab #3B: 10 Brand-New Unexplored FTMO Assets Research (STRICTLY DEV < 2025-01-01 ONLY).

STRICT SEALED DEVELOPMENT & SAFETY BOUNDARIES:
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA integrity on startup (`holdout_rows_analysed == 0`).
  - Fetches public Yahoo Finance v8 D1 OHLCV with explicit cutoff `period2 < 2025-01-01T00:00:00Z`
    AND enforces `assert max_date < '2025-01-01'` BEFORE writing Parquet files into
    `.runtime/new-assets-10-cache/` (`0` API keys, `OrderSend = 0`, `0` holdout rows ever stored!).
  - Maps all 10 brand-new unexplored instruments to exact live FTMO Swing specs from
    `planning/research/FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json`:
      `USOIL.cash (CL=F), UKOIL.cash (BZ=F), XAGUSD (SI=F), USDCHF (USDCHF=X), NZDUSD (NZDUSD=X),
       EURCHF (EURCHF=X), US30.cash (^DJI), UK100.cash (^FTSE), JP225.cash (^N225), AUDJPY (AUDJPY=X)`
  - Anti-Fake-Swap Guard:
      * Pays 100% of all negative FTMO triple-rollover swaps (incl. `USOIL short -66.11`,
        `UKOIL short -233.25`, `XAGUSD -11.86`, `US30 -391.97`, `UK100 -260.59`, `JP225 -841.60`).
      * Caps point-in-time positive commodity/index roll snapshots (`UKOIL +50.76`, `USOIL +12.47`,
        `UK100 short +8.59`) at `0.0` so NO strategy hallucinates fake `+25%/yr` backwardation carry!
      * Applies real triple-Wednesday FX swap on FX pairs AND separately reports `zero_pos_swap` floor.
  - Strict split: Cluster A (`2015-01-01..2021-12-31`) -> Blind Cluster B (`2022-01-01..2024-12-31`),
    evaluating 9 pre-registered specs across 3 orthogonal families through `research_council.py`
    with `|r| < 0.15` vs frozen `PORT_7E`, `1x/2x` friction, `BH-FDR`, `DSR`, and FTMO DD safety.
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

import hot_m1_cache as hcache
from native_ftmo_monfri_seal import STOP
from quant_factory.crypto_causal_universe import RETURNS_DIR, _causal_ema_matrix, compute_daily_metrics
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.eval_pipeline import benjamini_hochberg, deflated_sharpe_ratio
from quant_factory.ftmo_swing_real_swap_lab import (
    _causal_rsi,
    _causal_sma,
    _causal_vol,
    _vol_scale_weights,
    compute_ftmo_daily_swap_frac,
    load_ftmo_symbol_specs,
)
from quant_factory.prop_engine import replay_portfolio_m1
from quant_factory.research_council import (
    EvidenceBundle,
    KillCriteria,
    critique_proposal,
    propose_hypothesis,
)

NEW10_CACHE_DIR = ROOT / ".runtime" / "new-assets-10-cache"
LAB3B_SUMMARY_PATH = NEW10_CACHE_DIR / "lab3b_new10_assets_summary.json"
LAB3B_RETURNS_PATH = RETURNS_DIR / "sleeve_new10_assets_dev.json"

YAHOO_CHART_URL = "https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"

# 10 brand-new unexplored instruments: (internal_id, yahoo_ticker, ftmo_symbol, asset_class, 1x_oneway_bps)
NEW10_CATALOG: tuple[tuple[str, str, str, str, float], ...] = (
    ("USOIL",  "CL=F",     "USOIL.cash", "COMMODITY", 3.5),
    ("UKOIL",  "BZ=F",     "UKOIL.cash", "COMMODITY", 4.0),
    ("XAGUSD", "SI=F",     "XAGUSD",     "METAL",     4.5),
    ("USDCHF", "USDCHF=X", "USDCHF",     "FX",        1.8),
    ("NZDUSD", "NZDUSD=X", "NZDUSD",     "FX",        2.0),
    ("EURCHF", "EURCHF=X", "EURCHF",     "FX",        2.2),
    ("US30",   "^DJI",     "US30.cash",  "INDEX",     1.8),
    ("UK100",  "^FTSE",    "UK100.cash", "INDEX",     2.0),
    ("JP225",  "^N225",    "JP225.cash", "INDEX",     2.5),
    ("AUDJPY", "AUDJPY=X", "AUDJPY",     "FX",        2.4),
)

NEW10_IDS: tuple[str, ...] = tuple(x[0] for x in NEW10_CATALOG)
META_BY_ID: dict[str, dict[str, Any]] = {
    aid: {"ticker": tk, "ftmo_sym": fs, "asset_class": cls, "oneway_bps": bps}
    for aid, tk, fs, cls, bps in NEW10_CATALOG
}

FETCH_START_UTC = int(datetime(2014, 1, 1, tzinfo=timezone.utc).timestamp())
# Hard Holdout cutoff: strictly < 2025-01-01T00:00:00Z!
FETCH_END_UTC = STOP - 1  # 2024-12-31T23:59:59Z

CL_A_START = "2015-01-01"
CL_A_END = "2021-12-31"
CL_B_START = "2022-01-01"
CL_B_END = "2024-12-31"

PARQUET_D1_SCHEMA = pa.schema([
    ("date", pa.string()),
    ("ts_sec", pa.int64()),
    ("open", pa.float64()),
    ("high", pa.float64()),
    ("low", pa.float64()),
    ("close", pa.float64()),
])

LAB3B_KILL_CRITERIA = KillCriteria(
    max_bh_q=0.10,
    min_dsr=0.50,
    min_cluster_b_sharpe=0.60,
    min_cost_breakeven_mult=2.00,
    max_corr_vs_incumbent=0.15,  # Strict orthogonality |r| < 0.15 vs PORT_7E
    max_tail_corr_vs_incumbent=0.35,
    min_trades_cluster_b=30,
)


def _fetch_yahoo_d1_sealed(asset_id: str, ticker: str) -> tuple[str, list[dict[str, Any]], str | None]:
    """Fetch public Yahoo Finance v8 D1 OHLC strictly < 2025-01-01 (zero holdout rows)."""
    url = YAHOO_CHART_URL.format(ticker=ticker)
    params = {
        "period1": FETCH_START_UTC,
        "period2": FETCH_END_UTC,
        "interval": "1d",
        "includePrePost": "false",
    }
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) NaqexQuantResearch/1.0"}
    try:
        with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
            resp = None
            for attempt in range(4):
                r = client.get(url, params=params)
                if r.status_code == 200:
                    resp = r.json()
                    break
                if r.status_code in (429, 500, 502, 503):
                    time.sleep(1.0 * (attempt + 1))
                    continue
                return asset_id, [], f"HTTP_{r.status_code}:{r.text[:80]}"
            if resp is None:
                return asset_id, [], "MAX_RETRIES"
        res_list = resp.get("chart", {}).get("result") or []
        if not res_list:
            return asset_id, [], "EMPTY_RESULT"
        node = res_list[0]
        ts_list = node.get("timestamp") or []
        q = (node.get("indicators", {}).get("quote") or [{}])[0]
        opens, highs, lows, closes = q.get("open", []), q.get("high", []), q.get("low", []), q.get("close", [])
        dedup: dict[str, dict[str, Any]] = {}
        for ts, o, h, l, c in zip(ts_list, opens, highs, lows, closes):
            if ts is None or c is None or o is None or h is None or l is None:
                continue
            ts_i = int(ts)
            # STRICT HOLDOUT SEAL: discard any bar >= 2025-01-01T00:00:00Z immediately!
            if ts_i >= STOP:
                continue
            dt = datetime.fromtimestamp(ts_i, timezone.utc)
            d_str = dt.strftime("%Y-%m-%d")
            if d_str >= "2025-01-01" or dt.weekday() >= 5:
                continue
            c_f, o_f, h_f, l_f = float(c), float(o), float(h), float(l)
            # Guard against 2020-04-20 negative WTI front-month close (-37.63 USD): clip to finite positive floor
            if not (math.isfinite(c_f) and c_f > 0.0 and math.isfinite(h_f) and math.isfinite(l_f)):
                continue
            dedup[d_str] = {"date": d_str, "ts_sec": ts_i, "open": o_f, "high": max(h_f, o_f, c_f), "low": max(1e-6, min(l_f, o_f, c_f)), "close": c_f}
        rows = [dedup[k] for k in sorted(dedup)]
        return asset_id, rows, None
    except Exception as exc:
        return asset_id, [], f"EXC:{type(exc).__name__}:{exc}"


def fetch_and_cache_new10_dev(*, cache_dir: Path = NEW10_CACHE_DIR, force_refresh: bool = False) -> dict[str, Any]:
    """Download & SHA-verify all 10 new unexplored assets strictly `< 2025-01-01`."""
    lock_sha = assert_holdout_locked()
    cache_dir.mkdir(parents=True, exist_ok=True)
    plan: list[tuple[str, str]] = []
    files_meta: dict[str, Any] = {}
    skipped: list[dict[str, str]] = []

    for aid, ticker, _, _, _ in NEW10_CATALOG:
        p = cache_dir / f"{aid}.parquet"
        if p.exists() and not force_refresh:
            tbl = pq.read_table(p, columns=["date", "ts_sec"])
            dates = tbl["date"].to_pylist()
            ts_a = tbl["ts_sec"].to_numpy()
            assert len(dates) > 0 and max(dates) < "2025-01-01" and int(ts_a.max()) < STOP, f"HOLDOUT_VIOLATION:{aid}"
            files_meta[f"{aid}.parquet"] = {
                "ticker": ticker,
                "rows": len(dates),
                "first_date": dates[0],
                "last_date": dates[-1],
                "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
            }
            continue
        plan.append((aid, ticker))

    if plan:
        with ThreadPoolExecutor(max_workers=5) as pool:
            futs = [pool.submit(_fetch_yahoo_d1_sealed, aid, tk) for aid, tk in plan]
            for fut in as_completed(futs):
                aid, rows, err = fut.result()
                if err or not rows:
                    skipped.append({"asset": aid, "reason": err or "EMPTY"})
                    continue
                assert max(r["date"] for r in rows) < "2025-01-01", f"HOLDOUT_VIOLATION:{aid}"
                p = cache_dir / f"{aid}.parquet"
                tbl = pa.table(
                    {
                        "date": [r["date"] for r in rows],
                        "ts_sec": [r["ts_sec"] for r in rows],
                        "open": [r["open"] for r in rows],
                        "high": [r["high"] for r in rows],
                        "low": [r["low"] for r in rows],
                        "close": [r["close"] for r in rows],
                    },
                    schema=PARQUET_D1_SCHEMA,
                )
                pq.write_table(tbl, p, compression="zstd")
                files_meta[f"{aid}.parquet"] = {
                    "ticker": META_BY_ID[aid]["ticker"],
                    "rows": len(rows),
                    "first_date": rows[0]["date"],
                    "last_date": rows[-1]["date"],
                    "sha256": hashlib.sha256(p.read_bytes()).hexdigest(),
                }

    manifest = {
        "schema": "naqex-new-assets-10-dev-cache-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "holdout_lock_sha256": lock_sha,
        "holdout_rows": 0,
        "max_allowed_date": "2024-12-31",
        "loaded_count": len(files_meta),
        "skipped": skipped,
        "files": dict(sorted(files_meta.items())),
    }
    (cache_dir / "manifest.sha256.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8", newline="\n")
    return manifest


def load_new10_panel(*, cache_dir: Path = NEW10_CACHE_DIR) -> dict[str, Any]:
    raw: dict[str, dict[str, Any]] = {}
    all_dates: set[str] = set()
    loaded_ids: list[str] = []
    for aid in NEW10_IDS:
        p = cache_dir / f"{aid}.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p)
        dates = tbl["date"].to_pylist()
        assert max(dates) < "2025-01-01", f"HOLDOUT_VIOLATION:{aid}"
        loaded_ids.append(aid)
        raw[aid] = {
            "d": dates,
            "h": tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64),
            "l": tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64),
            "c": tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64),
        }
        all_dates.update(dates)

    dates_sorted = sorted(d for d in all_dates if d < "2025-01-01")
    d_map = {d: i for i, d in enumerate(dates_sorted)}
    n_t, n_a = len(dates_sorted), len(loaded_ids)
    highs = np.full((n_t, n_a), np.nan, dtype=np.float64)
    lows = np.full((n_t, n_a), np.nan, dtype=np.float64)
    closes = np.full((n_t, n_a), np.nan, dtype=np.float64)

    for j, aid in enumerate(loaded_ids):
        r = raw[aid]
        idxs = np.array([d_map[d] for d in r["d"]], dtype=np.int64)
        highs[idxs, j] = r["h"]
        lows[idxs, j] = r["l"]
        closes[idxs, j] = r["c"]
        # Causal forward-fill strictly across regional bank holidays (e.g. UK/Japan holidays)
        for t in range(1, n_t):
            if not np.isfinite(closes[t, j]) and np.isfinite(closes[t - 1, j]):
                closes[t, j] = closes[t - 1, j]
                highs[t, j] = closes[t - 1, j]
                lows[t, j] = closes[t - 1, j]

    weekdays = np.array([datetime.fromisoformat(d).weekday() for d in dates_sorted], dtype=np.int32)
    return {
        "assets": loaded_ids,
        "dates": dates_sorted,
        "weekdays": weekdays,
        "high": highs,
        "low": lows,
        "close": closes,
    }


def simulate_new10_backtest(
    panel: dict[str, Any],
    target_w: np.ndarray,
    ftmo_specs: dict[str, dict[str, Any]],
    *,
    cost_mult: float = 1.0,
    zero_positive_swap: bool = False,
    max_gross_leverage: float = 1.5,
) -> dict[str, Any]:
    """Causal D1 simulator (`t -> t+1`) with exact FTMO Swing triple-rollover swaps & anti-fake-swap cap."""
    closes = panel["close"]
    assets = panel["assets"]
    weekdays = panel["weekdays"]
    n_t, n_a = closes.shape
    oneway_bps = np.array([META_BY_ID[a]["oneway_bps"] for a in assets], dtype=np.float64) * cost_mult

    w_clean = np.where(np.isfinite(target_w) & np.isfinite(closes), target_w, 0.0).astype(np.float64)
    gross = np.sum(np.abs(w_clean), axis=1, keepdims=True)
    scale = np.where(gross > max_gross_leverage, max_gross_leverage / np.maximum(gross, 1e-12), 1.0)
    w_clean = w_clean * scale

    held_w = np.zeros_like(w_clean)
    held_w[1:] = w_clean[:-1]

    rets = np.zeros_like(closes)
    rets[1:] = np.where(
        np.isfinite(closes[1:]) & np.isfinite(closes[:-1]) & (closes[:-1] > 0.0),
        np.clip(closes[1:] / closes[:-1] - 1.0, -0.50, 0.50),
        0.0,
    )
    price_pnl = np.sum(held_w * rets, axis=1)

    dw = np.zeros_like(held_w)
    dw[0] = np.abs(held_w[0])
    dw[1:] = np.abs(held_w[1:] - held_w[:-1])
    turnover = np.sum(dw, axis=1)
    cost_drag = np.sum(dw * (oneway_bps[None, :] / 10_000.0), axis=1)

    swap_pnl = np.zeros(n_t, dtype=np.float64)
    spec_list = [ftmo_specs[META_BY_ID[a]["ftmo_sym"]] for a in assets]
    cls_list = [META_BY_ID[a]["asset_class"] for a in assets]

    for t in range(1, n_t):
        wd = int(weekdays[t - 1])
        sw_t = 0.0
        for j in range(n_a):
            wj = float(held_w[t, j])
            if abs(wj) <= 1e-12:
                continue
            side = 1 if wj > 0.0 else -1
            px = float(closes[t - 1, j])
            # Anti-Fake-Swap Guard: NEVER credit anomalous point-in-time positive commodity/index rollovers!
            cap_pos = zero_positive_swap or (cls_list[j] in ("COMMODITY", "INDEX", "METAL"))
            sw_frac = compute_ftmo_daily_swap_frac(
                spec_list[j], px, side, wd, is_equity_index=(cls_list[j] == "INDEX"), zero_positive_swap=cap_pos
            )
            sw_t += abs(wj) * sw_frac
        swap_pnl[t] = sw_t

    net_ret = np.clip(price_pnl + swap_pnl - cost_drag, -0.95, 2.0)
    return {
        "dates": panel["dates"],
        "daily_returns": net_ret,
        "daily_price_pnl": price_pnl,
        "daily_swap_pnl": swap_pnl,
        "daily_cost_drag": cost_drag,
        "daily_turnover": turnover,
        "daily_gross_exp": np.sum(np.abs(held_w), axis=1),
        "held_w": held_w,
    }


def build_lab3b_strategies(panel: dict[str, Any], ftmo_specs: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    """Build 9 pre-registered specs across 3 orthogonal families on the 10 brand-new assets (100% causal <= t)."""
    assets = panel["assets"]
    c, h, l = panel["close"], panel["high"], panel["low"]
    n_t, n_a = c.shape
    vol20 = _causal_vol(c, 20)

    def _idxs(names: tuple[str, ...]) -> list[int]:
        return [assets.index(x) for x in names if x in assets]

    fx4 = _idxs(("USDCHF", "NZDUSD", "EURCHF", "AUDJPY"))
    fx3_pos = _idxs(("USDCHF", "EURCHF", "AUDJPY"))
    comm3 = _idxs(("USOIL", "UKOIL", "XAGUSD"))
    idx3 = _idxs(("US30", "UK100", "JP225"))
    comm_idx6 = comm3 + idx3
    pos_carry5 = _idxs(("USDCHF", "EURCHF", "AUDJPY", "USOIL", "UKOIL"))

    # --- Family 1: Vol-Targeted Trend (3 specs) ---
    sig_f1_all10 = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(65, n_t):
        if t % 5 != 0 and t > 65:
            sig_f1_all10[t] = sig_f1_all10[t - 1]
            continue
        for j in range(n_a):
            if np.isfinite(c[t, j]) and np.isfinite(c[t - 60, j]):
                sig_f1_all10[t, j] = 1.0 if c[t, j] > c[t - 60, j] else -1.0
    w_f1_all10 = _vol_scale_weights(sig_f1_all10, vol20, 0.08, 252.0)

    ema20 = _causal_ema_matrix(c, 20)
    ema60 = _causal_ema_matrix(c, 60)
    sig_f1_lo6 = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(65, n_t):
        for j in comm_idx6:
            if np.isfinite(ema20[t, j]) and np.isfinite(ema60[t, j]) and ema20[t, j] > ema60[t, j]:
                sig_f1_lo6[t, j] = 1.0
    w_f1_lo6 = _vol_scale_weights(sig_f1_lo6, vol20, 0.08, 252.0)

    sig_f1_fx4 = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(65, n_t):
        if t % 5 != 0 and t > 65:
            sig_f1_fx4[t] = sig_f1_fx4[t - 1]
            continue
        for j in fx4:
            if np.isfinite(c[t, j]) and np.isfinite(c[t - 20, j]) and np.isfinite(c[t - 60, j]):
                s20 = 1.0 if c[t, j] > c[t - 20, j] else -1.0
                s60 = 1.0 if c[t, j] > c[t - 60, j] else -1.0
                sig_f1_fx4[t, j] = 0.5 * (s20 + s60)
    w_f1_fx4 = _vol_scale_weights(sig_f1_fx4, vol20, 0.08, 252.0)

    # --- Family 2: Positive-Carry Breakout (3 specs) ---
    def _don_long_only(idxs: list[int], en_w: int = 20, ex_w: int = 10) -> np.ndarray:
        sig = np.zeros((n_t, n_a), dtype=np.float64)
        st = np.zeros(n_a, dtype=np.int32)
        for t in range(en_w + 1, n_t):
            for j in idxs:
                if not np.isfinite(c[t, j]):
                    st[j] = 0
                    continue
                hi_e = float(np.nanmax(h[t - en_w : t, j]))
                lo_x = float(np.nanmin(l[t - ex_w : t, j]))
                if st[j] == 0 and c[t, j] > hi_e:
                    st[j] = 1
                elif st[j] == 1 and c[t, j] < lo_x:
                    st[j] = 0
                sig[t, j] = float(st[j])
        return sig

    w_f2_don5 = _vol_scale_weights(_don_long_only(pos_carry5, 20, 10), vol20, 0.08, 252.0)

    ema10 = _causal_ema_matrix(c, 10)
    ema40 = _causal_ema_matrix(c, 40)
    sig_f2_fx3 = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(45, n_t):
        for j in fx3_pos:
            if np.isfinite(ema10[t, j]) and np.isfinite(ema40[t, j]) and ema10[t, j] > ema40[t, j]:
                sig_f2_fx3[t, j] = 1.0
    w_f2_fx3 = _vol_scale_weights(sig_f2_fx3, vol20, 0.08, 252.0)

    w_f2_comm3 = _vol_scale_weights(_don_long_only(comm3, 20, 10), vol20, 0.08, 252.0)

    # --- Family 3: Cross-Asset Commodity/Index Dispersion & Reversion (3 specs) ---
    sma5 = _causal_sma(c, 5)
    sma200 = _causal_sma(c, 200)
    rsi2 = _causal_rsi(c, 2)
    sig_f3_idx_rsi2 = np.zeros((n_t, n_a), dtype=np.float64)
    hold_r = np.zeros(n_a, dtype=np.int32)
    for t in range(205, n_t):
        for j in idx3:
            if hold_r[j] > 0:
                if c[t, j] > sma5[t, j] or hold_r[j] >= 7:
                    hold_r[j] = 0
                else:
                    hold_r[j] += 1
            elif np.isfinite(c[t, j]) and np.isfinite(sma200[t, j]) and c[t, j] > sma200[t, j] and np.isfinite(rsi2[t, j]) and rsi2[t, j] < 15.0:
                hold_r[j] = 1
            sig_f3_idx_rsi2[t, j] = 1.0 if hold_r[j] > 0 else 0.0
    w_f3_idx_rsi2 = _vol_scale_weights(sig_f3_idx_rsi2, vol20, 0.08, 252.0)

    sig_f3_disp = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(65, n_t):
        if t % 5 != 0 and t > 65:
            sig_f3_disp[t] = sig_f3_disp[t - 1]
            continue
        scored = []
        for j in comm_idx6:
            if np.isfinite(c[t, j]) and np.isfinite(c[t - 60, j]) and np.isfinite(vol20[t, j]) and vol20[t, j] > 1e-6:
                r60 = c[t, j] / c[t - 60, j] - 1.0
                if r60 > 0.0:
                    scored.append((r60 / (float(vol20[t, j]) * math.sqrt(60.0)), j))
        scored.sort(reverse=True)
        for _, j in scored[:2]:
            sig_f3_disp[t, j] = 1.0
    w_f3_disp = _vol_scale_weights(sig_f3_disp, vol20, 0.08, 252.0)

    sig_f3_fx4_cm = np.zeros((n_t, n_a), dtype=np.float64)
    for t in range(65, n_t):
        if t % 5 != 0 and t > 65:
            sig_f3_fx4_cm[t] = sig_f3_fx4_cm[t - 1]
            continue
        cs_map, ms_map = {}, {}
        for j in fx4:
            if not (np.isfinite(c[t, j]) and np.isfinite(c[t - 60, j]) and np.isfinite(vol20[t, j]) and vol20[t, j] > 1e-6):
                continue
            sp = ftmo_specs[META_BY_ID[assets[j]]["ftmo_sym"]]
            px = float(c[t, j])
            yl = (float(sp["swap_long"]) * float(sp["point"]) / px) * 365.0
            ys = (float(sp["swap_short"]) * float(sp["point"]) / px) * 365.0
            cs_map[j] = yl - ys
            ms_map[j] = (c[t, j] / c[t - 60, j] - 1.0) / (float(vol20[t, j]) * math.sqrt(60.0))
        if len(cs_map) >= 4:
            keys_c = sorted(cs_map, key=lambda k: cs_map[k])
            keys_m = sorted(ms_map, key=lambda k: ms_map[k])
            rc = {k: i for i, k in enumerate(keys_c)}
            rm = {k: i for i, k in enumerate(keys_m)}
            comb = sorted([(rc[j] + rm[j], j) for j in cs_map])
            sig_f3_fx4_cm[t, comb[-1][1]] = 1.0
            sig_f3_fx4_cm[t, comb[0][1]] = -1.0
    w_f3_fx4_cm = _vol_scale_weights(sig_f3_fx4_cm, vol20, 0.08, 252.0)

    return [
        {"id": "N10_F1_TSMOM_60D_ALL10", "fam": "NEW10_VOL_TARGET_TREND", "w": w_f1_all10,
         "cp": "Persistent institutional macro trend flows across 10 unexplored Energy, Metals, FX, and Global Indices",
         "rat": "60-day vol-targeted two-way TSMOM across all 10 brand-new FTMO instruments tests cross-asset trend net of exact negative oil/index/metal FTMO swaps."},
        {"id": "N10_F1_EMA_20_60_LO_COMM_IDX", "fam": "NEW10_VOL_TARGET_TREND", "w": w_f1_lo6,
         "cp": "Inflationary commodity booms and secular global equity trends avoiding punitive short-swap drag",
         "rat": "Long-only EMA(20/60) trend across Oil, Silver, US30, UK100, and JP225 eliminates catastrophic short oil (-233 pts) and short index (-760 pts) FTMO swaps."},
        {"id": "N10_F1_TSMOM_DUAL_FX4", "fam": "NEW10_VOL_TARGET_TREND", "w": w_f1_fx4,
         "cp": "Multi-horizon central-bank divergence trends across CHF, NZD, and AUDJPY crosses",
         "rat": "Dual 20d/60d vol-targeted TSMOM across USDCHF, NZDUSD, EURCHF, and AUDJPY targets orthogonal G10 FX trends uncorrelated with PORT_7E majors."},
        {"id": "N10_F2_POSCARRY_DON20_FX_OIL", "fam": "NEW10_POS_CARRY_BREAKOUT", "w": w_f2_don5,
         "cp": "Carry-aligned breakout momentum in positive-swap FX crosses and backwardated crude oil",
         "rat": "Long-only 20d/10d Donchian breakouts across AUDJPY, USDCHF, EURCHF, USOIL, and UKOIL eliminate negative overnight swaps (with oil positive carry conservatively capped at 0%)."},
        {"id": "N10_F2_POSCARRY_EMA10_40_FX3", "fam": "NEW10_POS_CARRY_BREAKOUT", "w": w_f2_fx3,
         "cp": "Risk-on carry inflows into positive-swap AUDJPY, EURCHF, and USDCHF uptrends",
         "rat": "EMA(10/40) long-only trend across the three positive-swap new FX pairs avoids negative-carry whipsaws while collecting triple-Wednesday carry."},
        {"id": "N10_F2_COMM3_DON20_LONG", "fam": "NEW10_POS_CARRY_BREAKOUT", "w": w_f2_comm3,
         "cp": "Supply-shock breakouts in WTI Crude, Brent Crude, and Spot Silver",
         "rat": "Long-only 20d/10d Donchian breakout on USOIL, UKOIL, and XAGUSD isolates physical commodity breakout convexity orthogonal to FX intraday strategies."},
        {"id": "N10_F3_IDX3_RSI2_MEAN_REV", "fam": "NEW10_CROSS_ASSET_DISPERSION", "w": w_f3_idx_rsi2,
         "cp": "Short-term panic flushes across Dow 30, FTSE 100, and Nikkei 225 inside primary uptrends",
         "rat": "Connors RSI-2 (< 15) above 200d SMA buys 2-7 day oversold global index dips net of exact negative FTMO swaps (-392 to -842 pts)."},
        {"id": "N10_F3_COMM_VS_IDX_ROTATION", "fam": "NEW10_CROSS_ASSET_DISPERSION", "w": w_f3_disp,
         "cp": "Macro inflation vs disinflation capital rotation between Energy/Metals and Global Equities",
         "rat": "Weekly long-only rotation into top-2 positive 60d risk-adjusted leaders across 3 Commodities and 3 Global Indices adapts across 2022 inflation and 2023-2024 equity rallies."},
        {"id": "N10_F3_FX4_CARRY_MOM_LS", "fam": "NEW10_CROSS_ASSET_DISPERSION", "w": w_f3_fx4_cm,
         "cp": "Relative interest-rate carry and quarterly trend divergence across AUDJPY/CHF/NZD pairs",
         "rat": "Weekly L/S top-1 vs bottom-1 composite carry+60d momentum across 4 new FX pairs builds a low-turnover relative-value G10 sleeve."},
    ]


def run_lab3b(*, fetch: bool = True, cache_dir: Path = NEW10_CACHE_DIR, jobs_root: Path = hcache.DEFAULT_JOBS) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()
    ftmo_specs = load_ftmo_symbol_specs()

    manifest = fetch_and_cache_new10_dev(cache_dir=cache_dir) if fetch else json.loads((cache_dir / "manifest.sha256.json").read_text(encoding="utf-8"))
    assert manifest.get("holdout_rows") == 0

    # Load frozen PORT_7E daily return series for strict |r| < 0.15 orthogonality gate
    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=hcache.DEFAULT_CACHE, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    _, dev_ex7 = replay_portfolio_m1(warm["ext_days"], warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_daily = {e["day"]: float(e["net_usd"]) / 10000.0 for e in dev_ex7}

    panel = load_new10_panel(cache_dir=cache_dir)
    assert panel["dates"][-1] < "2025-01-01", "HOLDOUT_CONTAMINATION_DETECTED"
    specs = build_lab3b_strategies(panel, ftmo_specs)

    eval_items: list[dict[str, Any]] = []
    daily_1x_map: dict[str, dict[str, float]] = {}

    for sp in specs:
        s1 = simulate_new10_backtest(panel, sp["w"], ftmo_specs, cost_mult=1.0, zero_positive_swap=False)
        s2 = simulate_new10_backtest(panel, sp["w"], ftmo_specs, cost_mult=2.0, zero_positive_swap=False)
        s0 = simulate_new10_backtest(panel, sp["w"], ftmo_specs, cost_mult=1.0, zero_positive_swap=True)
        days = s1["dates"]
        r1, r2, r0 = s1["daily_returns"], s2["daily_returns"], s0["daily_returns"]
        to1, ex1 = s1["daily_turnover"], s1["daily_gross_exp"]

        ma = np.array([CL_A_START <= d <= CL_A_END for d in days])
        mb = np.array([CL_B_START <= d <= CL_B_END for d in days])
        days_b = [d for d, f in zip(days, mb) if f]

        eval_items.append({
            "id": sp["id"], "fam": sp["fam"], "cp": sp["cp"], "rat": sp["rat"],
            "days": days, "days_b": days_b, "r1": r1, "r2": r2, "r0": r0, "ma": ma, "mb": mb,
            "mA1": compute_daily_metrics(r1[ma], to1[ma], ex1[ma], ann_days=252.0),
            "mA2": compute_daily_metrics(r2[ma], to1[ma], ex1[ma], ann_days=252.0),
            "mB1": compute_daily_metrics(r1[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mB2": compute_daily_metrics(r2[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mB0": compute_daily_metrics(r0[mb], to1[mb], ex1[mb], ann_days=252.0),
            "mF1": compute_daily_metrics(r1[ma | mb], to1[ma | mb], ex1[ma | mb], ann_days=252.0),
            "worst_1d_b_pct": round(float(np.min(r1[mb])) * 100.0, 2) if np.any(mb) else 0.0,
            "price_pnl_b_pct": round(float(np.sum(s1["daily_price_pnl"][mb])) * 100.0, 2),
            "swap_pnl_b_pct": round(float(np.sum(s1["daily_swap_pnl"][mb])) * 100.0, 2),
            "cost_drag_1x_b_pct": round(float(np.sum(s1["daily_cost_drag"][mb])) * 100.0, 2),
            "n_active_days_b": int(np.sum(ex1[mb] > 1e-6)),
        })
        daily_1x_map[sp["id"]] = {d: float(v) for d, v in zip(days, r1) if d >= CL_A_START}

    m_total = len(eval_items)
    family_p_b = tuple(float(it["mB1"]["p_one_sided_nw"]) for it in eval_items)
    qb_all = benjamini_hochberg(list(family_p_b))

    results: list[dict[str, Any]] = []
    approved: list[str] = []

    for idx_i, it in enumerate(eval_items):
        inc_b = np.array([port7_daily.get(d, 0.0) for d in it["days_b"]], dtype=np.float64)
        card = propose_hypothesis(
            hypothesis_id=it["id"],
            title=f"Lab #3B {it['fam']}",
            asset_universe=NEW10_IDS[:5],
            timeframe="D1",
            counterparty_mechanism=it["cp"],
            economic_rationale=it["rat"],
            causal_invariants=(
                "strict_dev_lt_2025_01_01_holdout_sealed",
                "strict_t_to_t_plus_1_execution",
                "real_ftmo_negative_swaps_charged_pos_comm_idx_capped_0",
                "1x_and_2x_spread_slippage",
            ),
            n_trials_cumulative=m_total,
            kill_criteria=LAB3B_KILL_CRITERIA,
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
            annualization_days=252.0,
            holdout_rows_analysed=0,
        )
        verdict = critique_proposal(card, ev)
        failed = list(verdict["failed_gates"])
        final_v = verdict["verdict"]
        ftmo_dd_ok = (float(it["mB1"]["max_dd_pct"]) < 10.0) and (float(it["worst_1d_b_pct"]) > -5.0)
        if not ftmo_dd_ok:
            failed.append("G_FTMO_DD_SAFETY")
            if final_v == "APPROVE_FOR_INCUBATION":
                final_v = "CONDITIONAL_RETEST"
        if final_v == "APPROVE_FOR_INCUBATION":
            approved.append(it["id"])
        dsr_full = deflated_sharpe_ratio(it["r1"][it["ma"] | it["mb"]], n_trials=m_total, annualization=252.0)
        results.append({
            "id": it["id"],
            "family": it["fam"],
            "cluster_a_1x": it["mA1"],
            "cluster_a_2x": it["mA2"],
            "cluster_b_1x": it["mB1"],
            "cluster_b_2x": it["mB2"],
            "cluster_b_zero_pos_swap": it["mB0"],
            "full_1x": it["mF1"],
            "worst_1d_b_pct": it["worst_1d_b_pct"],
            "price_pnl_b_pct": it["price_pnl_b_pct"],
            "swap_pnl_b_pct": it["swap_pnl_b_pct"],
            "cost_drag_1x_b_pct": it["cost_drag_1x_b_pct"],
            "bh_q_b": round(qb_all[idx_i], 5),
            "dsr_b": verdict["gates"]["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_b": verdict["gates"]["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_port7e_b": verdict["gates"]["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_port7e_b": verdict["gates"]["G4_orthogonality"]["corr_tail_5pct"],
            "ftmo_dd_ok": ftmo_dd_ok,
            "council_verdict": final_v,
            "failed_gates": failed,
            "verdict_sha": verdict["verdict_sha256"],
        })

    exported_path = None
    if approved:
        best_id = max(approved, key=lambda aid: next(r["cluster_a_1x"]["sharpe"] for r in results if r["id"] == aid))
        best_r = next(r for r in results if r["id"] == best_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "sleeve_new10_assets_dev",
            "strategy_name": best_id,
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 252.0,
            "calendar_type": "business_days_dev_lt_2025",
            "cost_assumption": "FTMO Swing realistic spreads + real negative triple-rollover swaps (pos commodity/index roll capped at 0)",
            "metrics_cluster_a": best_r["cluster_a_1x"],
            "metrics_cluster_b": best_r["cluster_b_1x"],
            "metrics_full": best_r["full_1x"],
            "corr_vs_port7e_b": best_r["corr_vs_port7e_b"],
            "daily_returns": daily_1x_map[best_id],
        }
        LAB3B_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        LAB3B_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(LAB3B_RETURNS_PATH)

    asset_spec_audit = {
        a: {
            "ticker": META_BY_ID[a]["ticker"],
            "ftmo_symbol": META_BY_ID[a]["ftmo_sym"],
            "asset_class": META_BY_ID[a]["asset_class"],
            "swap_long": ftmo_specs[META_BY_ID[a]["ftmo_sym"]]["swap_long"],
            "swap_short": ftmo_specs[META_BY_ID[a]["ftmo_sym"]]["swap_short"],
            "rollover3days": ftmo_specs[META_BY_ID[a]["ftmo_sym"]]["swap_rollover3days"],
            "oneway_bps": META_BY_ID[a]["oneway_bps"],
        }
        for a in panel["assets"]
    }

    summary = {
        "schema": "naqex-lab3b-new10-assets-dev-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "order_send_count": 0,
        "holdout_rows_analysed": 0,
        "max_date_analysed": panel["dates"][-1],
        "loaded_assets": panel["assets"],
        "skipped_assets": manifest.get("skipped", []),
        "asset_spec_audit": asset_spec_audit,
        "m_total": m_total,
        "approved_count": len(approved),
        "approved_ids": approved,
        "exported_returns_path": exported_path,
        "results": results,
    }
    LAB3B_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description="Lab #3B 10 Brand-New Unexplored Assets Research (Dev < 2025-01-01)")
    ap.add_argument("--no-fetch", action="store_true")
    args = ap.parse_args()
    s = run_lab3b(fetch=not args.no_fetch)
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "loaded_count": len(s["loaded_assets"]),
        "skipped": s["skipped_assets"],
        "max_date_analysed": s["max_date_analysed"],
        "approved_count": s["approved_count"],
        "approved_ids": s["approved_ids"],
        "exported_returns_path": s["exported_returns_path"],
        "rows": [
            (
                r["id"], r["cluster_a_1x"]["cagr_pct"], r["cluster_a_1x"]["sharpe"],
                r["cluster_b_1x"]["cagr_pct"], r["cluster_b_2x"]["cagr_pct"],
                r["cluster_b_1x"]["sharpe"], r["cluster_b_1x"]["max_dd_pct"],
                r["swap_pnl_b_pct"], r["corr_vs_port7e_b"], r["bh_q_b"], r["dsr_b"], r["council_verdict"],
            )
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
