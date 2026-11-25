"""Wave-2 Cycle 4A — Lab #7: Automated RD-Agent-Q Research Loop on 21-Yr Overnight-vs-Intraday & Macro Regimes.

Executes `quant_factory.auto_research_loop.run_research_batch()` end-to-end on the cached 40-ETF
21-year NYSE dataset (`.runtime/etf40-cache/`, `2005-2026`) across `M = 10` (<= M_TOTAL_HARD_CAP = 20)
orthogonal white-box `HypothesisCard` candidates:
  - Family A (4 specs): Overnight-vs-Intraday Tug-of-War (Lou-Polk-Skouras JFE 2019) — both
    daily MOC->MOO auction capture (honest cost test), event-gated overnight dip capture, and
    persistent monthly overnight-vs-intraday L/S & Long-Only sleeves.
  - Family B (3 specs): Macro Growth/Inflation 4-Quadrant Regime Switch (`XLI/GLD`, `HYG/IEF`,
    `DBC/TLT`, `TIP/IEF`), Yield-Curve/Credit Defensive Rotation, and Dollar-Neutral Macro Pair.
  - Family C (3 specs): Volatility-Managed Cross-Asset Momentum (Moreira & Muir JF 2017) scaled
    strictly by lagged `20d` realized variance (`t-1`), leverage capped `<= 1.0x`.

STRICT ANTI-BIAS & SAFETY INVARIANTS:
  - `OrderSend = 0`, `0` API keys, FX Holdout `2025+` 100% SEALED (`assert_holdout_locked()`,
    `holdout_rows_analysed = 0`).
  - Calendar anchored strictly to NYSE trading days (`SPY.parquet`); zero pre-listing backfill;
    signal-only indices (`^VIX`, `^VIX3M`) hard-zeroed (`w == 0`).
  - Exact dividend/split-consistent overnight & intraday decomposition:
      `adj_open = open * (adjclose / close)`,
      `(1 + r_ov[t]) * (1 + r_id[t]) == adjclose[t] / adjclose[t-1]`.
  - Exact 1-to-1 NYSE date alignment for Gate 4 orthogonality vs frozen `S1` (`PORT_7E` Dev `<= 2024-12-31`)
    AND vs `S4_ETF40_MULTIFACTOR` (full blind Cl.B `2019-2026`).
  - Exports `.runtime/quant-pod-returns/sleeve6_overnight_macro_etf.json` ONLY IF a candidate achieves
    `APPROVE_FOR_INCUBATION` (`|r_S1| <= 0.15`) AND `|r_S4| <= 0.45` (selected strictly by Cluster A Sharpe!).
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import numpy as np
import pyarrow.parquet as pq

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

import hot_m1_cache as hcache
from quant_factory.auto_research_loop import DEFAULT_OUT_DIR, run_research_batch
from quant_factory.crypto_causal_universe import RETURNS_DIR, compute_daily_metrics
from quant_factory.data_store import assert_holdout_locked, build_or_load_frozen_tapes, load_registry
from quant_factory.etf40_multifactor_vrp_lab import (
    BROAD_FACTORS,
    CLUSTER_A_END,
    CLUSTER_B_START,
    COMMODITIES,
    ETF40_CACHE_DIR,
    ETF40_UNIVERSE,
    FIXED_INCOME_CREDIT,
    INTERNATIONAL,
    SIGNAL_ONLY_TICKERS,
    SLEEVE4_RETURNS_PATH,
    US_SECTORS,
    WARMUP_START,
    _safe_filename,
)
from quant_factory.eval_pipeline import deflated_sharpe_ratio
from quant_factory.macro_etf_trend import _month_end_flags
from quant_factory.prop_engine import replay_portfolio_m1

ORDER_SEND_COUNT = 0
LAB7_OUT_DIR = DEFAULT_OUT_DIR / "lab7"
LAB7_SUMMARY_PATH = ETF40_CACHE_DIR / "lab7_overnight_macro_summary.json"
SLEEVE6_RETURNS_PATH = RETURNS_DIR / "sleeve6_overnight_macro_etf.json"

MAX_CORR_VS_S1 = 0.15
MAX_CORR_VS_S4 = 0.45
SHORT_BORROW_ANN = 0.0050  # 50 bps/yr conservative institutional ETF short borrow

CRISIS_WINDOWS: tuple[tuple[str, str, str], ...] = (
    ("GFC_2008", "2008-01-02", "2009-03-09"),
    ("COVID_2020", "2020-02-19", "2020-03-23"),
    ("INFLATION_2022", "2022-01-03", "2022-10-14"),
)


def load_etf40_ohlc_panel(*, cache_dir: Path = ETF40_CACHE_DIR) -> dict[str, Any]:
    """Load 40-ticker OHLC + adjclose panel strictly anchored to NYSE (`SPY.parquet`) trading days."""
    spy_path = cache_dir / _safe_filename("SPY")
    if not spy_path.exists():
        raise FileNotFoundError(f"Missing SPY parquet in {cache_dir}")
    spy_tbl = pq.read_table(spy_path, columns=["date"])
    nyse_dates = sorted(set(spy_tbl["date"].to_pylist()))
    d_map = {d: i for i, d in enumerate(nyse_dates)}

    tickers = list(ETF40_UNIVERSE)
    n_t, n_k = len(nyse_dates), len(tickers)
    adj_open = np.full((n_t, n_k), np.nan, dtype=np.float64)
    adj_close = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, tk in enumerate(tickers):
        p = cache_dir / _safe_filename(tk)
        if not p.exists():
            continue
        tbl = pq.read_table(p, columns=["date", "open", "close", "adjclose"])
        ds = tbl["date"].to_pylist()
        op = tbl["open"].to_numpy(zero_copy_only=False).astype(np.float64)
        cl = tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)
        ac = tbl["adjclose"].to_numpy(zero_copy_only=False).astype(np.float64)
        for d, o_v, c_v, ac_v in zip(ds, op, cl, ac):
            idx = d_map.get(d)
            if idx is None or not (math.isfinite(ac_v) and ac_v > 0.0):
                continue
            adj_close[idx, j] = ac_v
            if math.isfinite(o_v) and o_v > 0.0 and math.isfinite(c_v) and c_v > 0.0:
                adj_open[idx, j] = o_v * (ac_v / c_v)
            else:
                adj_open[idx, j] = ac_v

    # Compute exact overnight (Close[t-1] -> Open[t]) and intraday (Open[t] -> Close[t]) returns
    # Zero pre-listing fill: NaN stays NaN wherever ticker was not yet listed!
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
    return {
        "dates": nyse_dates,
        "tickers": tickers,
        "tradable_mask": tradable_mask,
        "adj_open": adj_open,
        "adj_close": adj_close,
        "r_cc": r_cc,
        "r_ov": r_ov,
        "r_id": r_id,
    }


def _rolling_sma_causal(arr: np.ndarray, window: int) -> np.ndarray:
    n_t, n_k = arr.shape
    out = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(arr)
    vals = np.where(ok, arr, 0.0)
    cs_v = np.cumsum(vals, axis=0)
    cs_c = np.cumsum(ok.astype(np.int64), axis=0)
    if n_t >= window:
        sv = cs_v[window - 1 :] - np.vstack([np.zeros((1, n_k)), cs_v[:-window]])
        sc = cs_c[window - 1 :] - np.vstack([np.zeros((1, n_k), dtype=np.int64), cs_c[:-window]])
        out[window - 1 :] = np.where(sc == window, sv / float(window), np.nan)
    return out


def _rolling_vol_and_var_causal(rets: np.ndarray, window: int = 20) -> tuple[np.ndarray, np.ndarray]:
    n_t, n_k = rets.shape
    vol = np.full((n_t, n_k), np.nan, dtype=np.float64)
    var = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(rets)
    rz = np.where(ok, rets, 0.0)
    c = np.cumsum(ok.astype(np.int64), axis=0)
    s1 = np.cumsum(rz, axis=0)
    s2 = np.cumsum(rz * rz, axis=0)
    if n_t >= window:
        cnt = c[window - 1 :] - np.vstack([np.zeros((1, n_k), dtype=np.int64), c[:-window]])
        m = (s1[window - 1 :] - np.vstack([np.zeros((1, n_k)), s1[:-window]])) / float(window)
        ss = s2[window - 1 :] - np.vstack([np.zeros((1, n_k)), s2[:-window]])
        v = np.maximum(0.0, (ss - float(window) * m * m) / float(max(1, window - 1)))
        valid = (cnt == window) & (v > 1e-12)
        var[window - 1 :] = np.where(valid, v, np.nan)
        vol[window - 1 :] = np.where(valid, np.sqrt(v), np.nan)
    return vol, var


def simulate_etf_daily_or_overnight(
    panel: dict[str, Any],
    target_w: np.ndarray,
    *,
    mode: str = "close_to_close",
    cost_bps_oneway: float = 5.0,
    short_borrow_ann: float = SHORT_BORROW_ANN,
    max_gross: float = 1.0,
) -> dict[str, Any]:
    """Causal ETF simulator (`t-1` signal -> day `t` return) supporting `close_to_close` & `overnight_only`.

    In `overnight_only` mode (MOC entry at Close[t-1] -> MOO exit at Open[t]):
      - Every active overnight holding `held_w[t]` pays FULL round-trip auction turnover (`2 * |held_w[t]|`)!
    In `close_to_close` mode:
      - Pays `|held_w[t] - held_w[t-1]|` turnover * `cost_bps_oneway` + `short_borrow_ann/252` on short legs.
    Signal-only tickers (`^VIX`, `^VIX3M`) and non-listed NaN cells are HARD-ZEROED!
    """
    ac = panel["adj_close"]
    tradable = panel["tradable_mask"]
    n_t, n_k = ac.shape

    w_clean = np.where(np.isfinite(target_w) & np.isfinite(ac) & tradable[None, :], target_w, 0.0).astype(np.float64)
    gross = np.sum(np.abs(w_clean), axis=1, keepdims=True)
    scale = np.where(gross > max_gross, max_gross / np.maximum(gross, 1e-12), 1.0)
    w_clean = w_clean * scale

    held_w = np.zeros_like(w_clean)
    held_w[1:] = w_clean[:-1]

    if mode == "overnight_only":
        ret_mat = np.where(np.isfinite(panel["r_ov"]), panel["r_ov"], 0.0)
        gross_ret = np.sum(held_w * ret_mat, axis=1)
        # Enter MOC at Close[t-1] + exit MOO at Open[t] = 2x one-way auction cost per active overnight!
        turnover = 2.0 * np.sum(np.abs(held_w), axis=1)
        borrow_drag = np.zeros(n_t, dtype=np.float64)
    else:
        ret_mat = np.where(np.isfinite(panel["r_cc"]), panel["r_cc"], 0.0)
        gross_ret = np.sum(held_w * ret_mat, axis=1)
        dw = np.zeros_like(held_w)
        dw[0] = np.abs(held_w[0])
        dw[1:] = np.abs(held_w[1:] - held_w[:-1])
        turnover = np.sum(dw, axis=1)
        short_exp = np.sum(np.maximum(-held_w, 0.0), axis=1)
        borrow_drag = short_exp * (short_borrow_ann / 252.0)

    cost_drag = turnover * (cost_bps_oneway / 10_000.0)
    net_ret = np.clip(gross_ret - cost_drag - borrow_drag, -0.95, 2.0)
    return {
        "net_returns": net_ret,
        "gross_returns": gross_ret,
        "cost_drag": cost_drag + borrow_drag,
        "turnover": turnover,
        "held_w": held_w,
        "gross_exposure": np.sum(np.abs(held_w), axis=1),
    }


def _rolling_cum_log_sum(ret_mat: np.ndarray, window: int) -> np.ndarray:
    n_t, n_k = ret_mat.shape
    ok = np.isfinite(ret_mat) & (ret_mat > -0.99)
    lr = np.where(ok, np.log1p(np.where(ok, ret_mat, 0.0)), 0.0)
    cs = np.cumsum(lr, axis=0)
    cc = np.cumsum(ok.astype(np.int64), axis=0)
    out = np.full((n_t, n_k), np.nan, dtype=np.float64)
    if n_t >= window:
        s = cs[window - 1 :] - np.vstack([np.zeros((1, n_k)), cs[:-window]])
        c = cc[window - 1 :] - np.vstack([np.zeros((1, n_k), dtype=np.int64), cc[:-window]])
        out[window - 1 :] = np.where(c >= int(0.85 * window), np.expm1(s), np.nan)
    return out


def build_lab7_candidates(panel: dict[str, Any]) -> list[dict[str, Any]]:
    """Build M = 10 strictly causal white-box Lab #7 strategies across Families A, B, and C."""
    dates = panel["dates"]
    tickers = panel["tickers"]
    tradable = panel["tradable_mask"]
    ac = panel["adj_close"]
    r_cc = panel["r_cc"]
    r_ov = panel["r_ov"]
    r_id = panel["r_id"]
    n_t, n_k = ac.shape
    t_idx = {tk: i for i, tk in enumerate(tickers)}

    vol20, var20 = _rolling_vol_and_var_causal(r_cc, 20)
    sma60 = _rolling_sma_causal(ac, 60)
    sma120 = _rolling_sma_causal(ac, 120)
    sma200 = _rolling_sma_causal(ac, 200)
    month_end = _month_end_flags(dates)

    # Helpers for index lookup
    def _ix(names: tuple[str, ...]) -> list[int]:
        return [t_idx[x] for x in names if x in t_idx and tradable[t_idx[x]]]

    eq_broad = _ix(("SPY", "QQQ", "IWM", "EFA", "EEM"))
    all_trad = [j for j in range(n_k) if tradable[j]]

    # =========================================================================
    # FAMILY A: Overnight-vs-Intraday Tug-of-War (Lou-Polk-Skouras JFE 2019)
    # =========================================================================

    # A1: Daily MOC->MOO Overnight-Only ETF Basket (honest auction-cost test on SPY/QQQ/IWM/EFA/EEM)
    w_a1 = np.zeros((n_t, n_k), dtype=np.float64)
    vt10 = 0.10 / math.sqrt(252.0)
    for t in range(200, n_t):
        elig = [j for j in eq_broad if np.isfinite(ac[t, j]) and np.isfinite(sma200[t, j]) and ac[t, j] > sma200[t, j] and np.isfinite(vol20[t, j])]
        if not elig:
            continue
        raw = np.zeros(n_k, dtype=np.float64)
        for j in elig:
            raw[j] = (vt10 / max(float(vol20[t, j]), 1e-4)) / len(elig)
        s = float(np.sum(raw))
        w_a1[t] = raw / s if s > 1.0 else raw

    # A2: Selective Event-Gated Overnight Dip Capture (enter MOC->MOO ONLY after intraday flush <= -1.0 sigma!)
    w_a2 = np.zeros((n_t, n_k), dtype=np.float64)
    eq_plus_sec = _ix(BROAD_FACTORS + US_SECTORS)
    for t in range(200, n_t):
        hits = []
        for j in eq_plus_sec:
            if (
                np.isfinite(ac[t, j]) and np.isfinite(sma200[t, j]) and ac[t, j] > sma200[t, j]
                and np.isfinite(r_id[t, j]) and np.isfinite(vol20[t, j]) and vol20[t, j] > 1e-4
                and r_id[t, j] <= -1.0 * float(vol20[t, j])
            ):
                hits.append(j)
        if hits:
            inv_v = np.array([1.0 / max(float(vol20[t, j]), 1e-4) for j in hits], dtype=np.float64)
            inv_v /= np.sum(inv_v)
            for j, wt in zip(hits, inv_v):
                w_a2[t, j] = float(wt) * 0.80  # 80% notional cap on dip nights

    # A3 & A4: Lou-Polk-Skouras (JFE 2019) Persistent Overnight-minus-Intraday Spread (trailing 252d)
    cum_ov_252 = _rolling_cum_log_sum(r_ov, 252)
    cum_id_252 = _rolling_cum_log_sum(r_id, 252)
    tug_spread = cum_ov_252 - cum_id_252

    w_a3 = np.zeros((n_t, n_k), dtype=np.float64)  # Dollar-neutral L/S Top-8 Overnight vs Bot-8 Intraday
    w_a4 = np.zeros((n_t, n_k), dtype=np.float64)  # Long-Only Top-8 Overnight-Dominant + Trend Guard
    cur_a3 = np.zeros(n_k, dtype=np.float64)
    cur_a4 = np.zeros(n_k, dtype=np.float64)
    for t in range(255, n_t):
        if month_end[t]:
            valid = [j for j in all_trad if np.isfinite(tug_spread[t, j]) and np.isfinite(vol20[t, j]) and vol20[t, j] > 1e-4]
            if len(valid) >= 16:
                order = sorted(valid, key=lambda j: float(tug_spread[t, j]))
                bot8 = order[:8]
                top8 = order[-8:]
                cur_a3 = np.zeros(n_k, dtype=np.float64)
                iv_l = np.array([1.0 / float(vol20[t, j]) for j in top8])
                iv_s = np.array([1.0 / float(vol20[t, j]) for j in bot8])
                cur_a3[top8] = 0.50 * iv_l / np.sum(iv_l)
                cur_a3[bot8] = -0.50 * iv_s / np.sum(iv_s)

                # Long-Only: top-8 overnight-dominant that are ALSO above 120d SMA (vol-scaled <= 1.0)
                top_up = [j for j in top8 if np.isfinite(sma120[t, j]) and ac[t, j] > sma120[t, j]]
                cur_a4 = np.zeros(n_k, dtype=np.float64)
                if top_up:
                    raw = np.zeros(n_k, dtype=np.float64)
                    for j in top_up:
                        raw[j] = (vt10 / float(vol20[t, j])) / len(top_up)
                    s = float(np.sum(raw))
                    cur_a4 = raw / s if s > 1.0 else raw
        w_a3[t] = cur_a3
        w_a4[t] = cur_a4

    # =========================================================================
    # FAMILY B: Macro Growth/Inflation Regime Switch (XLI/GLD, HYG/IEF, DBC/TLT, TLT/IEF)
    # =========================================================================
    def _ratio_above_sma(num_tk: str, den_tk: str, win: int = 60) -> np.ndarray:
        i_n, i_d = t_idx[num_tk], t_idx[den_tk]
        rat = np.where(np.isfinite(ac[:, i_n]) & np.isfinite(ac[:, i_d]) & (ac[:, i_d] > 0.0), ac[:, i_n] / np.where(ac[:, i_d] > 0.0, ac[:, i_d], 1.0), np.nan)
        sm = _rolling_sma_causal(rat[:, None], win)[:, 0]
        return np.isfinite(rat) & np.isfinite(sm) & (rat > sm)

    cyc_up = _ratio_above_sma("XLI", "GLD", 60)
    cred_up = _ratio_above_sma("HYG", "IEF", 60)
    inf_dbc_up = _ratio_above_sma("DBC", "TLT", 60)
    inf_tip_up = _ratio_above_sma("TIP", "IEF", 60)
    yc_long_up = _ratio_above_sma("TLT", "IEF", 60)

    def _assign_bucket(w_vec: np.ndarray, t: int, bucket: tuple[str, ...], alloc: float) -> None:
        avail = [t_idx[x] for x in bucket if x in t_idx and np.isfinite(ac[t, t_idx[x]])]
        if avail:
            for j in avail:
                w_vec[j] += alloc / len(avail)

    # B1: 4-Quadrant Growth x Inflation Macro Regime Allocator (weekly rebalance)
    w_b1 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_b1 = np.zeros(n_k, dtype=np.float64)
    for t in range(120, n_t):
        if t % 5 == 0 or t == 120:
            growth_on = bool(cyc_up[t] or cred_up[t])
            infl_on = bool(inf_dbc_up[t] and inf_tip_up[t])
            cur_b1 = np.zeros(n_k, dtype=np.float64)
            if growth_on and not infl_on:      # Goldilocks
                _assign_bucket(cur_b1, t, ("SPY", "QQQ"), 0.50)
                _assign_bucket(cur_b1, t, ("IEF", "TLT"), 0.30)
                _assign_bucket(cur_b1, t, ("GLD",), 0.20)
            elif growth_on and infl_on:        # Reflation
                _assign_bucket(cur_b1, t, ("XLE", "XLB", "DBC"), 0.40)
                _assign_bucket(cur_b1, t, ("SPY", "XLI"), 0.35)
                _assign_bucket(cur_b1, t, ("GLD",), 0.25)
            elif (not growth_on) and infl_on:  # Stagflation (2022 killer!)
                _assign_bucket(cur_b1, t, ("DBC", "USO", "DBA"), 0.40)
                _assign_bucket(cur_b1, t, ("GLD", "TIP"), 0.35)
                _assign_bucket(cur_b1, t, ("UUP", "BIL", "SHY"), 0.25)
            else:                              # Deflation / Recession (2008 & 2020 killer!)
                _assign_bucket(cur_b1, t, ("TLT", "IEF"), 0.55)
                _assign_bucket(cur_b1, t, ("GLD",), 0.30)
                _assign_bucket(cur_b1, t, ("UUP", "BIL", "SHY"), 0.15)
        w_b1[t] = cur_b1

    # B2: Yield-Curve (TLT/IEF) + Credit (HYG/IEF) Defensive Regime Allocator (vol-scaled weekly)
    w_b2 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_b2 = np.zeros(n_k, dtype=np.float64)
    for t in range(120, n_t):
        if t % 5 == 0 or t == 120:
            cur_b2 = np.zeros(n_k, dtype=np.float64)
            if cred_up[t] and (not yc_long_up[t]):     # Healthy expansion -> equities + short duration + gold
                _assign_bucket(cur_b2, t, ("SPY", "USMV", "QUAL"), 0.55)
                _assign_bucket(cur_b2, t, ("GLD", "DBC"), 0.25)
                _assign_bucket(cur_b2, t, ("SHY", "BIL"), 0.20)
            elif cred_up[t] and yc_long_up[t]:         # Disinflationary rally -> balanced equity + long bond
                _assign_bucket(cur_b2, t, ("SPY", "QQQ"), 0.40)
                _assign_bucket(cur_b2, t, ("TLT", "IEF"), 0.40)
                _assign_bucket(cur_b2, t, ("GLD",), 0.20)
            elif (not cred_up[t]) and yc_long_up[t]:   # Credit stress + bond flight-to-safety (2008/2020)
                _assign_bucket(cur_b2, t, ("TLT", "IEF"), 0.60)
                _assign_bucket(cur_b2, t, ("GLD",), 0.25)
                _assign_bucket(cur_b2, t, ("UUP", "SHY"), 0.15)
            else:                                      # Credit stress + rising yields (2022 inflation)
                _assign_bucket(cur_b2, t, ("UUP", "SHY", "BIL"), 0.50)
                _assign_bucket(cur_b2, t, ("GLD", "DBC"), 0.35)
                _assign_bucket(cur_b2, t, ("TIP",), 0.15)
        w_b2[t] = cur_b2

    # B3: Dollar-Neutral Macro Regime L/S Pair (0.50 Long / -0.50 Short weekly)
    w_b3 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_b3 = np.zeros(n_k, dtype=np.float64)
    for t in range(120, n_t):
        if t % 5 == 0 or t == 120:
            growth_on = bool(cyc_up[t] and cred_up[t])
            infl_on = bool(inf_dbc_up[t] and inf_tip_up[t])
            cur_b3 = np.zeros(n_k, dtype=np.float64)
            if growth_on:
                _assign_bucket(cur_b3, t, ("XLI", "XLY", "HYG"), 0.50)
                _assign_bucket(cur_b3, t, ("XLU", "XLP", "TLT"), -0.50)
            elif infl_on:
                _assign_bucket(cur_b3, t, ("DBC", "GLD", "UUP"), 0.50)
                _assign_bucket(cur_b3, t, ("TLT", "IWM", "XLY"), -0.50)
            else:
                _assign_bucket(cur_b3, t, ("TLT", "GLD", "XLP"), 0.50)
                _assign_bucket(cur_b3, t, ("HYG", "EEM", "XLE"), -0.50)
        w_b3[t] = cur_b3

    # =========================================================================
    # FAMILY C: Volatility-Managed Cross-Asset Momentum (Moreira & Muir JF 2017)
    # =========================================================================
    # Strictly lagged 20d realized variance scaling `min(cap, target_var / var20[t])`, leverage <= 1.0x!
    target_daily_var = (0.10 ** 2) / 252.0

    # C1: Moreira-Muir Variance-Scaled Multi-Asset TSMOM (all 38 ETFs, skip-1m 12m-1m momentum, weekly)
    w_c1 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_c1 = np.zeros(n_k, dtype=np.float64)
    for t in range(255, n_t):
        if t % 5 == 0 or t == 255:
            raw = np.zeros(n_k, dtype=np.float64)
            for j in all_trad:
                if np.isfinite(ac[t - 21, j]) and np.isfinite(ac[t - 252, j]) and np.isfinite(var20[t, j]) and var20[t, j] > 1e-10:
                    mom_12_1 = ac[t - 21, j] / ac[t - 252, j] - 1.0
                    if mom_12_1 > 0.0 and ac[t, j] > sma120[t, j]:
                        # Moreira-Muir inverse-VARIANCE weight (capped per asset at 0.15)
                        raw[j] = min(0.15, (target_daily_var / float(var20[t, j])) * 0.08)
            s = float(np.sum(raw))
            cur_c1 = raw / s if s > 1.0 else raw
        w_c1[t] = cur_c1

    # C2: Moreira-Muir Variance-Managed Cross-Asset Top-6 Momentum (Bonds/Gold/Comm/FX/Equities)
    w_c2 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_c2 = np.zeros(n_k, dtype=np.float64)
    for t in range(130, n_t):
        if t % 5 == 0 or t == 130:
            scored = []
            for j in all_trad:
                if np.isfinite(ac[t, j]) and np.isfinite(ac[t - 126, j]) and np.isfinite(vol20[t, j]) and vol20[t, j] > 1e-4:
                    r126 = ac[t, j] / ac[t - 126, j] - 1.0
                    if r126 > 0.0:
                        scored.append((r126 / float(vol20[t, j]), j))
            scored.sort(reverse=True)
            top6 = [j for _, j in scored[:6]]
            cur_c2 = np.zeros(n_k, dtype=np.float64)
            if top6:
                iv = np.array([1.0 / float(vol20[t, j]) for j in top6])
                base_w = iv / np.sum(iv)
                # Compute lagged 20d variance of this candidate portfolio strictly on [t-19..t]!
                sub_r = np.where(np.isfinite(r_cc[t - 19 : t + 1, top6]), r_cc[t - 19 : t + 1, top6], 0.0)
                p_r = sub_r @ base_w
                p_var = float(np.var(p_r, ddof=1))
                mm_scale = min(1.0, target_daily_var / max(p_var, 1e-10))
                for j, bw in zip(top6, base_w):
                    cur_c2[j] = float(bw) * mm_scale
        w_c2[t] = cur_c2

    # C3: Moreira-Muir Variance-Managed Diversified Macro Core (20% SPY, 25% TLT, 20% GLD, 15% DBC, 20% UUP/IEF)
    core_map = (("SPY", 0.20), ("TLT", 0.25), ("GLD", 0.20), ("DBC", 0.15), ("UUP", 0.10), ("IEF", 0.10))
    w_c3 = np.zeros((n_t, n_k), dtype=np.float64)
    cur_c3 = np.zeros(n_k, dtype=np.float64)
    for t in range(125, n_t):
        if t % 5 == 0 or t == 125:
            raw = np.zeros(n_k, dtype=np.float64)
            for tk, base_a in core_map:
                j = t_idx[tk]
                if np.isfinite(ac[t, j]) and np.isfinite(sma120[t, j]) and ac[t, j] > sma120[t, j]:
                    raw[j] = base_a
            s_raw = float(np.sum(raw))
            if s_raw > 1e-6:
                norm_w = raw / s_raw
                active = np.where(norm_w > 0.0)[0]
                sub_r = np.where(np.isfinite(r_cc[t - 19 : t + 1, active]), r_cc[t - 19 : t + 1, active], 0.0)
                p_r = sub_r @ norm_w[active]
                p_var = float(np.var(p_r, ddof=1))
                # Moreira-Muir variance scaling capped <= s_raw (never lever above active trend budget!)
                mm_scale = min(s_raw, (target_daily_var / max(p_var, 1e-10)) * s_raw)
                cur_c3 = norm_w * min(1.0, mm_scale)
            else:
                cur_c3 = np.zeros(n_k, dtype=np.float64)
        w_c3[t] = cur_c3

    return [
        {"id": "L7_A1_OV_DAILY_MOC_MOO", "fam": "A_OVERNIGHT_TUGOFWAR", "mode": "overnight_only", "w": w_a1,
         "assets": ["SPY", "QQQ", "IWM", "EFA", "EEM"],
         "cp": "Overnight dealer inventory risk premium paid between NYSE close and next-day open",
         "rat": "Daily Close(t-1)->Open(t) vol-targeted overnight equity ETF basket tests directly whether gross overnight drift survives 5 bps / 10 bps daily round-trip auction costs."},
        {"id": "L7_A2_OV_DIP_SELECTIVE", "fam": "A_OVERNIGHT_TUGOFWAR", "mode": "overnight_only", "w": w_a2,
         "assets": ["SPY", "QQQ", "IWM", "XLK", "XLF"],
         "cp": "Forced intraday institutional/retail liquidation absorbed by overnight liquidity providers",
         "rat": "Selective Close(t-1)->Open(t) overnight capture triggered strictly after -1.0 sigma intraday selloffs above SMA200 slashes auction frequency 6x to target net overnight snapback."},
        {"id": "L7_A3_LPS_TUGOFWAR_LS", "fam": "A_OVERNIGHT_TUGOFWAR", "mode": "close_to_close", "w": w_a3,
         "assets": ["SPY", "QQQ", "GLD", "TLT", "XLE"],
         "cp": "Persistent clientele tug-of-war (Lou-Polk-Skouras JFE 2019): institutions accumulate overnight while retail chases intraday",
         "rat": "Monthly dollar-neutral L/S buys top-8 ETFs with persistent trailing 12m overnight-minus-intraday outperformance and shorts bottom-8 intraday-chased ETFs with low turnover."},
        {"id": "L7_A4_LPS_OVERNIGHT_DOM_LO", "fam": "A_OVERNIGHT_TUGOFWAR", "mode": "close_to_close", "w": w_a4,
         "assets": ["SPY", "QQQ", "GLD", "XLK", "XLV"],
         "cp": "Institutional overnight accumulation persistence across global ETFs gated by intermediate trend",
         "rat": "Monthly long-only vol-targeted basket of top-8 persistent overnight-dominant ETFs above 120d SMA harvests Lou-Polk-Skouras institutional clientele drift without daily auction bleed."},
        {"id": "L7_B1_MACRO_QUAD_REGIME", "fam": "B_MACRO_REGIME_SWITCH", "mode": "close_to_close", "w": w_b1,
         "assets": ["SPY", "TLT", "GLD", "DBC", "UUP"],
         "cp": "Slow institutional asset-allocation rebalancing across Growth x Inflation macro regime shifts",
         "rat": "4-quadrant macro switch driven strictly by causal XLI/GLD, HYG/IEF, DBC/TLT, and TIP/IEF ratios rotates into commodities/USD in stagflation and long bonds/gold in recessions."},
        {"id": "L7_B2_YC_CREDIT_DEFENSIVE", "fam": "B_MACRO_REGIME_SWITCH", "mode": "close_to_close", "w": w_b2,
         "assets": ["SPY", "TLT", "GLD", "DBC", "UUP"],
         "cp": "Bond-market credit and duration repricing leading equity drawdowns during monetary shifts",
         "rat": "Causal HYG/IEF credit-spread and TLT/IEF curve-slope regime allocator shifts dynamically between low-vol equities, long Treasuries, commodities, and USD cash."},
        {"id": "L7_B3_MACRO_REGIME_LS", "fam": "B_MACRO_REGIME_SWITCH", "mode": "close_to_close", "w": w_b3,
         "assets": ["XLI", "TLT", "DBC", "GLD", "HYG"],
         "cp": "Cross-asset dispersion between cyclical risk assets and defensive hedges across macro regimes",
         "rat": "Dollar-neutral 0.50/-0.50 weekly macro regime L/S pair matches cyclical vs defensive ETF baskets to causal growth/inflation signals for zero-beta macro alpha."},
        {"id": "L7_C1_MM17_VAR_TSMOM_38", "fam": "C_VOLMAN_MOMENTUM", "mode": "close_to_close", "w": w_c1,
         "assets": ["SPY", "TLT", "GLD", "DBC", "EFA"],
         "cp": "Behavioral trend underreaction amplified by volatility clustering (Moreira & Muir JF 2017)",
         "rat": "Inverse-variance-scaled 12m-1m cross-asset ETF momentum scales down risk automatically in high-variance regimes while keeping gross exposure strictly capped <= 1.0x."},
        {"id": "L7_C2_MM17_VAR_XSEC_TOP6", "fam": "C_VOLMAN_MOMENTUM", "mode": "close_to_close", "w": w_c2,
         "assets": ["SPY", "TLT", "GLD", "DBC", "UUP"],
         "cp": "Cross-asset capital migration into leading macro asset classes with variance-managed risk scaling",
         "rat": "Weekly Top-6 positive 6-month cross-asset ETF momentum scaled by lagged 20-day portfolio variance (Moreira & Muir JF 2017) cuts crisis drawdowns without margin borrowing."},
        {"id": "L7_C3_MM17_VAR_MACRO_CORE", "fam": "C_VOLMAN_MOMENTUM", "mode": "close_to_close", "w": w_c3,
         "assets": ["SPY", "TLT", "GLD", "DBC", "UUP"],
         "cp": "Multi-asset risk premia harvested selectively when lagged variance and trend are favorable",
         "rat": "Diversified 6-asset macro core (SPY/TLT/GLD/DBC/UUP/IEF) gated by 120d trend and scaled by lagged 20d realized variance delivers low-equity-beta orthogonal diversification."},
    ]


def _crisis_return(dates: list[str], rets: np.ndarray, start_d: str, end_d: str) -> float:
    m = np.array([start_d <= d <= end_d for d in dates], dtype=bool)
    if not np.any(m):
        return 0.0
    return round((float(np.prod(1.0 + rets[m])) - 1.0) * 100.0, 2)


def _exact_date_corr(map_a: dict[str, float], map_b: dict[str, float], start_d: str, end_d: str | None = None) -> float:
    common = sorted(d for d in map_a if d in map_b and d >= start_d and (end_d is None or d <= end_d))
    if len(common) < 20:
        return 0.0
    a = np.array([map_a[d] for d in common], dtype=np.float64)
    b = np.array([map_b[d] for d in common], dtype=np.float64)
    if float(np.std(a)) <= 1e-12 or float(np.std(b)) <= 1e-12:
        return 0.0
    c = float(np.corrcoef(a, b)[0, 1])
    return round(c if math.isfinite(c) else 0.0, 4)


def run_lab7(
    *,
    cache_dir: Path = ETF40_CACHE_DIR,
    out_dir: Path = LAB7_OUT_DIR,
    jobs_root: Path = hcache.DEFAULT_JOBS,
) -> dict[str, Any]:
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    # Load frozen S1 (PORT_7E Dev <= 2024-12-31) and S4_ETF40_MULTIFACTOR for exact 1-to-1 NYSE date correlation!
    reg = load_registry()
    warm = build_or_load_frozen_tapes(jobs_root=jobs_root, cache_dir=hcache.DEFAULT_CACHE, force_rebuild=False)
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    risks7 = {k: base_r[k] for k in reg["frozen_portfolios"]["PORT_7E_P28_CORE"]["engines"]}
    _, dev_ex7 = replay_portfolio_m1(warm["ext_days"], warm["tapes"], risks7, 10000.0, profile_mode="Swing")
    port7_daily = {e["day"]: float(e["net_usd"]) / 10000.0 for e in dev_ex7}

    s4_primary_map: dict[str, float] = {}
    s4_ens_map: dict[str, float] = {}
    if SLEEVE4_RETURNS_PATH.exists():
        s4_obj = json.loads(SLEEVE4_RETURNS_PATH.read_text(encoding="utf-8"))
        s4_primary_map = {str(k): float(v) for k, v in s4_obj.get("daily_returns", {}).items()}
        variants = s4_obj.get("variants") or {}
        ens_node = variants.get("E40_APPROVED_EQW_ENSEMBLE") or s4_obj.get("ensemble_daily_returns") or {}
        ens_raw = ens_node.get("daily_returns", ens_node) if isinstance(ens_node, dict) else {}
        s4_ens_map = {str(k): float(v) for k, v in ens_raw.items()}

    s3b_map: dict[str, float] = {}
    s3b_path = RETURNS_DIR / "sleeve3b_macro_etf.json"
    if s3b_path.exists():
        s3b_obj = json.loads(s3b_path.read_text(encoding="utf-8"))
        s3b_map = {str(k): float(v) for k, v in s3b_obj.get("daily_returns", {}).items()}

    panel = load_etf40_ohlc_panel(cache_dir=cache_dir)
    dates = panel["dates"]
    candidates = build_lab7_candidates(panel)
    cand_by_id = {c["id"]: c for c in candidates}

    ma = np.array([WARMUP_START <= d <= CLUSTER_A_END for d in dates], dtype=bool)
    mb = np.array([d >= CLUSTER_B_START for d in dates], dtype=bool)
    dates_b = [d for d, f in zip(dates, mb) if f]
    # Exact 1-to-1 NYSE prefix alignment through 2024-12-31 for Gate 4 vs S1 (PORT_7E)!
    dates_b_dev = [d for d in dates_b if d <= "2024-12-31"]
    inc_s1_b_aligned = np.array([port7_daily.get(d, 0.0) for d in dates_b_dev], dtype=np.float64)

    # Pre-simulate all 10 candidates (1x = 5 bps, 2x = 10 bps) and build formal `naqex-hypothesis-batch-v1`
    sim_cache: dict[str, dict[str, Any]] = {}
    batch_hyps: list[dict[str, Any]] = []

    for c in candidates:
        s1 = simulate_etf_daily_or_overnight(panel, c["w"], mode=c["mode"], cost_bps_oneway=5.0)
        s2 = simulate_etf_daily_or_overnight(panel, c["w"], mode=c["mode"], cost_bps_oneway=10.0)
        r1, r2 = s1["net_returns"], s2["net_returns"]
        to1, ex1 = s1["turnover"], s1["gross_exposure"]
        mA1 = compute_daily_metrics(r1[ma], to1[ma], ex1[ma], ann_days=252.0)
        mA2 = compute_daily_metrics(r2[ma], to1[ma], ex1[ma], ann_days=252.0)
        mB1 = compute_daily_metrics(r1[mb], to1[mb], ex1[mb], ann_days=252.0)
        mB2 = compute_daily_metrics(r2[mb], to1[mb], ex1[mb], ann_days=252.0)
        mF1 = compute_daily_metrics(r1[ma | mb], to1[ma | mb], ex1[ma | mb], ann_days=252.0)
        dmap = {d: float(v) for d, v in zip(dates, r1) if d >= WARMUP_START}
        sim_cache[c["id"]] = {
            "r1": r1, "r2": r2, "mA1": mA1, "mA2": mA2, "mB1": mB1, "mB2": mB2, "mF1": mF1,
            "daily_map": dmap,
            "n_active_b": int(np.sum(ex1[mb] > 1e-6)),
            "corr_s1_dev": _exact_date_corr(dmap, port7_daily, CLUSTER_B_START, "2024-12-31"),
            "corr_s3b_b": _exact_date_corr(dmap, s3b_map, CLUSTER_B_START),
            "corr_s4_primary_b": _exact_date_corr(dmap, s4_primary_map, CLUSTER_B_START),
            "corr_s4_ens_b": _exact_date_corr(dmap, s4_ens_map, CLUSTER_B_START),
            "crises": {cname: _crisis_return(dates, r1, sd, ed) for cname, sd, ed in CRISIS_WINDOWS},
        }
        batch_hyps.append({
            "hypothesis_id": c["id"],
            "title": f"Lab #7 {c['fam']}: {c['id']}",
            "asset_universe": c["assets"],
            "timeframe": "D1_OVERNIGHT" if c["mode"] == "overnight_only" else "D1_MACRO_ETF",
            "counterparty_mechanism": c["cp"],
            "economic_rationale": c["rat"],
            "causal_invariants": [
                "nyse_spy_calendar_strict_zero_prelisting_fill",
                "signal_le_t_minus_1_applied_to_t",
                "signal_only_vix_hard_zero_weight",
                "exact_1to1_nyse_date_alignment_gate4",
                "5bps_1x_and_10bps_2x_plus_50bps_short_borrow",
            ],
            "n_trials_cumulative": len(candidates),
            "kill_criteria": {
                "max_bh_q": 0.10,
                "min_dsr": 0.50,
                "min_cluster_b_sharpe": 0.50,
                "min_cost_breakeven_mult": 2.00,
                "max_corr_vs_incumbent": MAX_CORR_VS_S1,
                "max_tail_corr_vs_incumbent": 0.35,
                "min_trades_cluster_b": 30,
            },
        })

    batch_payload = {
        "schema": "naqex-hypothesis-batch-v1",
        "batch_id": "LAB7_OVERNIGHT_MACRO_RD_V1",
        "n_trials_cumulative": len(candidates),
        "hypotheses": batch_hyps,
    }

    def _eval_from_cache(spec: dict) -> dict:
        sc = sim_cache[spec["hypothesis_id"]]
        return {
            "cluster_a_returns": sc["r1"][ma],
            "cluster_b_returns": sc["r1"][mb],
            "p_value_raw": float(sc["mB1"]["p_one_sided_nw"]),
            "cost_1x_net": float(sc["mB1"]["total_ret_pct"]),
            "cost_2x_net": float(sc["mB2"]["total_ret_pct"]),
            "n_trades_cluster_b": sc["n_active_b"],
            "incumbent_daily_returns": inc_s1_b_aligned,
            "annualization_days": 252.0,
            "holdout_rows_analysed": 0,
        }

    # REAL end-to-end execution of `auto_research_loop.run_research_batch()`!
    ledger = run_research_batch(
        batch_payload,
        out_dir=out_dir,
        emit_templates=True,
        evaluator_fn=_eval_from_cache,
        seed=20261124,
    )

    results: list[dict[str, Any]] = []
    sleeve6_qualified: list[str] = []

    for v in ledger["verdicts"]:
        hid = v["hypothesis"]["hypothesis_id"]
        sc = sim_cache[hid]
        g = v["gates"]
        corr_s4_ok = abs(sc["corr_s4_primary_b"]) <= MAX_CORR_VS_S4 and abs(sc["corr_s4_ens_b"]) <= MAX_CORR_VS_S4
        is_s6_qual = (v["verdict"] == "APPROVE_FOR_INCUBATION") and corr_s4_ok
        if is_s6_qual:
            sleeve6_qualified.append(hid)
        dsr_full = deflated_sharpe_ratio(sc["r1"][ma | mb], n_trials=len(candidates), annualization=252.0)
        results.append({
            "id": hid,
            "family": cand_by_id[hid]["fam"],
            "mode": cand_by_id[hid]["mode"],
            "cluster_a_1x": sc["mA1"],
            "cluster_a_2x": sc["mA2"],
            "cluster_b_1x": sc["mB1"],
            "cluster_b_2x": sc["mB2"],
            "full_1x": sc["mF1"],
            "bh_q_b": g["G1_bh_fdr"]["bh_q"],
            "dsr_b": g["G2_dsr_and_sharpe"]["dsr_b"],
            "dsr_full": dsr_full["dsr"],
            "breakeven_cost_mult_b": g["G3_cost_stress"]["breakeven_mult"],
            "corr_vs_s1_dev": g["G4_orthogonality"]["corr_all"],
            "tail_corr_vs_s1_dev": g["G4_orthogonality"]["corr_tail_5pct"],
            "corr_vs_s3b_b": sc["corr_s3b_b"],
            "corr_vs_s4_primary_b": sc["corr_s4_primary_b"],
            "corr_vs_s4_ens_b": sc["corr_s4_ens_b"],
            "crises": sc["crises"],
            "council_verdict": v["verdict"],
            "failed_gates": v["failed_gates"],
            "orthogonal_to_s4": corr_s4_ok,
            "sleeve6_qualified": is_s6_qual,
            "verdict_sha": v["verdict_sha256"],
        })

    # Export Sleeve #6 JSON ONLY IF >= 1 candidate passes Council AND |r_S4| <= 0.45!
    # Select strictly by Cluster A Sharpe (zero Cluster B selection bias!).
    exported_path = None
    selected_s6_id = None
    if sleeve6_qualified:
        selected_s6_id = max(sleeve6_qualified, key=lambda sid: next(r["cluster_a_1x"]["sharpe"] for r in results if r["id"] == sid))
        best_r = next(r for r in results if r["id"] == selected_s6_id)
        payload = {
            "schema": "naqex-sleeve-daily-returns-v1",
            "sleeve_id": "S6_OVERNIGHT_MACRO_ETF",
            "strategy_name": selected_s6_id,
            "selection_rule": "Highest Cluster A (2006-2018) Sharpe among Council APPROVE_FOR_INCUBATION & |r_S4|<=0.45 survivors",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "annualization_days": 252.0,
            "calendar_type": "nyse_business_days_2006_2026",
            "cost_assumption": "5 bps one-way ETF friction + 50 bps/yr short borrow where applicable",
            "metrics_cluster_a": best_r["cluster_a_1x"],
            "metrics_cluster_b": best_r["cluster_b_1x"],
            "metrics_full": best_r["full_1x"],
            "corr_vs_s1_dev": best_r["corr_vs_s1_dev"],
            "corr_vs_s4_primary_b": best_r["corr_vs_s4_primary_b"],
            "corr_vs_s4_ens_b": best_r["corr_vs_s4_ens_b"],
            "daily_returns": sim_cache[selected_s6_id]["daily_map"],
        }
        SLEEVE6_RETURNS_PATH.parent.mkdir(parents=True, exist_ok=True)
        SLEEVE6_RETURNS_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8", newline="\n")
        exported_path = str(SLEEVE6_RETURNS_PATH)
    elif SLEEVE6_RETURNS_PATH.exists():
        SLEEVE6_RETURNS_PATH.unlink()

    summary = {
        "schema": "naqex-lab7-overnight-macro-rd-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "holdout_lock_sha256": lock_sha,
        "order_send_count": ORDER_SEND_COUNT,
        "holdout_rows_analysed": 0,
        "nyse_eval_days_a": int(np.sum(ma)),
        "nyse_eval_days_b": int(np.sum(mb)),
        "nyse_dev_aligned_s1_days": len(dates_b_dev),
        "m_total": len(candidates),
        "auto_loop_ledger_json": ledger["ledger_json_path"],
        "auto_loop_ledger_md": ledger["ledger_md_path"],
        "auto_loop_ledger_sha256": ledger["ledger_sha256"],
        "council_approved_ids": ledger["approved_ids"],
        "emitted_templates": ledger["emitted_templates"],
        "sleeve6_qualified_ids": sleeve6_qualified,
        "selected_sleeve6_id": selected_s6_id,
        "exported_returns_path": exported_path,
        "results": results,
    }
    LAB7_SUMMARY_PATH.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    return summary


def main() -> int:
    argparse.ArgumentParser(description="Lab #7 Automated RD-Agent-Q Research Loop on Overnight & Macro ETF Regimes").parse_args()
    s = run_lab7()
    print(json.dumps({
        "elapsed_sec": s["elapsed_sec"],
        "m_total": s["m_total"],
        "council_approved_ids": s["council_approved_ids"],
        "sleeve6_qualified_ids": s["sleeve6_qualified_ids"],
        "selected_sleeve6_id": s["selected_sleeve6_id"],
        "exported_returns_path": s["exported_returns_path"],
        "ledger_sha256": s["auto_loop_ledger_sha256"],
        "rows": [
            (
                r["id"], r["cluster_a_1x"]["cagr_pct"], r["cluster_a_1x"]["sharpe"],
                r["cluster_b_1x"]["cagr_pct"], r["cluster_b_2x"]["cagr_pct"],
                r["cluster_b_1x"]["sharpe"], r["cluster_b_1x"]["max_dd_pct"],
                r["bh_q_b"], r["dsr_b"], r["corr_vs_s1_dev"], r["corr_vs_s4_ens_b"],
                r["crises"]["INFLATION_2022"], r["council_verdict"], r["sleeve6_qualified"],
            )
            for r in s["results"]
        ],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
