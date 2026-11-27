"""Alpha #2 Unified Engine & PORT_7E Portfolio Combination Study (Dev <= 2024-12-31, Holdout 2025+ SEALED).

STRICT SAFETY & ANTI-OVERFIT INVARIANTS:
  - OrderSend = 0, ZERO network calls, ZERO broker access, 0 VND.
  - Asserts `NATIVE_FTMO_HOLDOUT_LOCK.json` SHA-256 integrity.
  - Slices `.runtime/crypto-spot-cache/` AND `.runtime/crypto-1h-cache/` strictly `<= 2024-12-31`
    AT LOAD TIME before any signal, return, or statistic is computed (`holdout_rows_analysed = 0`).
  - Explicit `-O`-safe `if max_date >= "2025-01-01": raise ValueError(...)` + `enforce_pre_holdout_dates()`
    (ZERO Python `assert` security/holdout guards!).
  - Evaluates ALL `M = 8` pre-registered Alpha #2 candidates using canonical `quant_lab.unified_engine`
    and `quant_lab.funding_carry_v2`, computing empirical `DSR`, CSCV `PBO`, purged/embargoed `CPCV`,
    daily correlation `|r|` + Worst-5% Tail Correlation vs `PORT_7E` (`frozen_9e_tapes_v2`),
    and Funded starved-payout-month reduction (`60-66%` baseline -> target `< 35%`).
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import pyarrow.parquet as pq
from numba import njit

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
QUANT_LAB_SRC = ROOT / "projects" / "quant-trading" / "src"
for _p in (str(AI_ENGINES), str(QUANT_LAB_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

from quant_core.holdout_guard import enforce_pre_holdout_dates as enforce_root_pre_holdout_dates  # noqa: E402
from quant_core.metrics import (  # noqa: E402
    combinatorial_purged_cv,
    compute_pbo_cscv,
    deflated_sharpe_ratio_empirical,
)
from quant_factory.capital_optimizer.constants import (  # noqa: E402
    DD_STATIC,
    DEFAULT_DISCOUNT_RATE,
    DEFAULT_SEED,
    VARIANT_PHASE_CONFIGS,
)
from quant_factory.capital_optimizer.replay_cache import ExactTierReplayCache  # noqa: E402
from quant_factory.capital_optimizer.simulator import (  # noqa: E402
    _simulate_single_ticket_rules_numba,
    make_block_bootstrap_indices,
)
from quant_factory.capital_optimizer.summaries import summarize_single_ticket_mc  # noqa: E402
from quant_factory.crypto_1h_intraday_lab import LAB1_CACHE_DIR, TOP40_1H_SYMBOLS  # noqa: E402
from quant_factory.crypto_causal_universe import CACHE_DIR as SPOT_CACHE_DIR  # noqa: E402
from quant_factory.crypto_causal_universe import UNIVERSE_50_SYMBOLS  # noqa: E402
from quant_factory.data_store import (  # noqa: E402
    assert_holdout_locked,
    build_or_load_frozen_tapes,
    load_red_news_calendar,
    load_registry,
)
from quant_factory.eval_pipeline import deflated_sharpe_ratio, tail_correlation_report  # noqa: E402
from quant_factory.funding_rate_carry import FUNDING_CACHE_DIR, PERP_UNIVERSE_20  # noqa: E402
from quant_lab.causal_universe import causal_rolling_top_n_mask  # noqa: E402

try:
    from quant_lab.funding_carry_v2 import (  # noqa: E402
        FundingCarryConfig,
        carry_btc_eth_cons_weights,
        carry_top_k_hysteresis_weights,
        carry_v2_blend_weights,
        run_funding_carry_backtest,
    )
    from quant_lab.unified_engine import (  # noqa: E402
        F4EmaConfig,
        UnifiedSpotEngine,
        enforce_pre_holdout_dates,
    )
except ModuleNotFoundError:  # Fallback when projects/quant-trading submodule pin predates unified_engine.py
    FundingCarryConfig = None  # type: ignore[assignment,misc]
    carry_btc_eth_cons_weights = None  # type: ignore[assignment]
    carry_top_k_hysteresis_weights = None  # type: ignore[assignment]
    carry_v2_blend_weights = None  # type: ignore[assignment]
    run_funding_carry_backtest = None  # type: ignore[assignment]
    F4EmaConfig = None  # type: ignore[assignment,misc]
    UnifiedSpotEngine = None  # type: ignore[assignment,misc]

    def enforce_pre_holdout_dates(  # type: ignore[misc]
        dates: Any,
        *,
        cutoff: str = "2025-01-01",
        context: str = "portfolio_7e_plus_alpha2_study",
        allow_empty: bool = True,
    ) -> int:
        enforce_root_pre_holdout_dates(dates, cutoff_day=cutoff, context=context, allow_empty=allow_empty)
        return 0

ORDER_SEND_CAPABLE: bool = False
ORDER_SEND_COUNT: int = 0
HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
HOLDOUT_CUTOFF_MS: int = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp() * 1000)
USD_VND_RATE: float = 25_765.94
VN_CARD_FX_FEE_PCT: float = 0.025
FTMO_10K_BF_FEE_USD: float = 68.70  # 70.42 USD incl +2.5% VN card FX fee (matches C10 report)
FTMO_10K_REG_FEE_USD: float = 98.61  # 101.08 USD incl +2.5% VN card FX fee


def _ms_to_iso_date(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000.0, UTC).strftime("%Y-%m-%d")


def validate_strict_pre_holdout_dates(dates: list[str] | tuple[str, ...], *, context: str) -> int:
    """Strict `-O`-safe pre-holdout date check raising `ValueError` on any date >= `2025-01-01`."""
    if not dates:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{context}]: empty date sequence rejected.")
    max_date = max(str(d) for d in dates)
    if max_date >= HOLDOUT_CUTOFF_DAY:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{context}]: max_date {max_date!r} >= {HOLDOUT_CUTOFF_DAY!r}.")
    enforce_pre_holdout_dates(dates, cutoff=HOLDOUT_CUTOFF_DAY, context=context, allow_empty=False)
    enforce_root_pre_holdout_dates(dates, cutoff_day=HOLDOUT_CUTOFF_DAY, context=context, allow_empty=False)
    return 0


def _validate_cutoff_ms(cutoff_ms: Any, *, context: str) -> int:
    """Strictly validate `cutoff_ms` is a positive int `<= HOLDOUT_CUTOFF_MS` (rejects bool/float/Inf)."""
    if isinstance(cutoff_ms, bool) or not isinstance(cutoff_ms, (int, np.integer)):
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_ms must be an integer, got {cutoff_ms!r}.")
    val = int(cutoff_ms)
    if val <= 0 or val > HOLDOUT_CUTOFF_MS:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{context}]: cutoff_ms {val} outside (0, {HOLDOUT_CUTOFF_MS}].")
    return val


def load_dev_spot_panel_from_parquet(
    interval: str,
    *,
    symbols: tuple[str, ...],
    cache_dir: Path,
    min_date: str = "2019-01-01",
    cutoff_ms: int = HOLDOUT_CUTOFF_MS,
) -> dict[str, Any]:
    """Load OHLCV + quote_volume DataFrames sliced strictly `< 2025-01-01` at Parquet load time."""
    cutoff_i = _validate_cutoff_ms(cutoff_ms, context=f"load_dev_spot_panel:{interval}")
    min_ms = int(datetime.fromisoformat(min_date).replace(tzinfo=UTC).timestamp() * 1000)
    iv_dir = cache_dir / interval

    loaded_syms: list[str] = []
    raw: dict[str, dict[str, np.ndarray]] = {}
    all_ts: set[int] = set()

    for sym in symbols:
        p = iv_dir / f"{sym}.parquet"
        if not p.exists():
            continue
        tbl = pq.read_table(p, columns=["open_time_ms", "high", "low", "close", "quote_volume"])
        ot = tbl["open_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        mask = (ot >= min_ms) & (ot < cutoff_i)
        if not np.any(mask):
            continue
        ot_dev = ot[mask]
        if int(ot_dev[-1]) >= cutoff_i:
            raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{interval}/{sym}]: timestamp >= 2025-01-01.")
        loaded_syms.append(sym)
        raw[sym] = {
            "t": ot_dev,
            "h": tbl["high"].to_numpy(zero_copy_only=False).astype(np.float64)[mask],
            "l": tbl["low"].to_numpy(zero_copy_only=False).astype(np.float64)[mask],
            "c": tbl["close"].to_numpy(zero_copy_only=False).astype(np.float64)[mask],
            "qv": tbl["quote_volume"].to_numpy(zero_copy_only=False).astype(np.float64)[mask],
        }
        all_ts.update(ot_dev.tolist())

    if not all_ts or not loaded_syms:
        raise ValueError(f"No Dev parquet bars loaded from {iv_dir}.")

    ts_arr = np.array(sorted(all_ts), dtype=np.int64)
    if int(ts_arr[-1]) >= cutoff_i:
        raise ValueError(f"HOLDOUT_LOCK_VIOLATION [{interval}]: max timestamp >= 2025-01-01.")

    ts_map = {int(t): i for i, t in enumerate(ts_arr)}
    n_t, n_k = len(ts_arr), len(loaded_syms)
    highs = np.full((n_t, n_k), np.nan, dtype=np.float64)
    lows = np.full((n_t, n_k), np.nan, dtype=np.float64)
    closes = np.full((n_t, n_k), np.nan, dtype=np.float64)
    qvol = np.full((n_t, n_k), np.nan, dtype=np.float64)

    for j, sym in enumerate(loaded_syms):
        d = raw[sym]
        idxs = np.array([ts_map[int(t)] for t in d["t"]], dtype=np.int64)
        highs[idxs, j] = d["h"]
        lows[idxs, j] = d["l"]
        closes[idxs, j] = d["c"]
        qvol[idxs, j] = d["qv"]

    idx = pd.to_datetime(ts_arr, unit="ms", utc=True)
    dates = [_ms_to_iso_date(int(t)) for t in ts_arr]
    validate_strict_pre_holdout_dates(dates, context=f"load_dev_spot_panel:{cache_dir.name}/{interval}")

    return {
        "interval": interval,
        "symbols": loaded_syms,
        "timestamps_ms": ts_arr,
        "index": idx,
        "dates": dates,
        "high": pd.DataFrame(highs, index=idx, columns=loaded_syms),
        "low": pd.DataFrame(lows, index=idx, columns=loaded_syms),
        "close": pd.DataFrame(closes, index=idx, columns=loaded_syms),
        "quote_volume": pd.DataFrame(qvol, index=idx, columns=loaded_syms),
        "holdout_rows_analysed": 0,
    }


def load_dev_funding_panel_from_parquet(
    *,
    symbols: tuple[str, ...] = PERP_UNIVERSE_20,
    funding_dir: Path = FUNDING_CACHE_DIR,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
    min_date: str = "2020-01-01",
    cutoff_ms: int = HOLDOUT_CUTOFF_MS,
) -> dict[str, Any]:
    """Load 20-perp daily funding + Spot/Perp prices sliced strictly `< 2025-01-01` at load time."""
    cutoff_i = _validate_cutoff_ms(cutoff_ms, context="load_dev_funding_panel")
    min_ms = int(datetime.fromisoformat(min_date).replace(tzinfo=UTC).timestamp() * 1000)

    spot_d1 = load_dev_spot_panel_from_parquet(
        "1d",
        symbols=symbols,
        cache_dir=spot_cache_dir,
        min_date=min_date,
        cutoff_ms=cutoff_i,
    )
    spot_dates = spot_d1["dates"]
    spot_c_df = spot_d1["close"]
    spot_h_df = spot_d1["high"]

    daily_fund_by_sym: dict[str, dict[str, float]] = {}
    perp_c_by_sym: dict[str, dict[str, float]] = {}
    perp_h_by_sym: dict[str, dict[str, float]] = {}
    perp_qv_by_sym: dict[str, dict[str, float]] = {}
    spot_c_by_sym: dict[str, dict[str, float]] = {}
    spot_h_by_sym: dict[str, dict[str, float]] = {}
    loaded_syms: list[str] = []
    all_days: set[str] = set()

    for sym in symbols:
        rp = funding_dir / "rates" / f"{sym}.parquet"
        kp = funding_dir / "perp_1d" / f"{sym}.parquet"
        if not rp.exists():
            continue
        tbl = pq.read_table(rp, columns=["funding_time_ms", "funding_rate"])
        ft = tbl["funding_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
        fr = tbl["funding_rate"].to_numpy(zero_copy_only=False).astype(np.float64)
        mask = (ft >= min_ms) & (ft < cutoff_i)
        if not np.any(mask):
            continue
        dsum: dict[str, float] = defaultdict(float)
        for ts, rate in zip(ft[mask], fr[mask], strict=True):
            dk = _ms_to_iso_date(int(ts))
            if dk >= HOLDOUT_CUTOFF_DAY:
                raise ValueError(f"HOLDOUT_LOCK_VIOLATION [funding/{sym}]: {dk} >= {HOLDOUT_CUTOFF_DAY}.")
            if math.isfinite(float(rate)):
                dsum[dk] += float(rate)
                all_days.add(dk)
        if not dsum:
            continue
        loaded_syms.append(sym)
        daily_fund_by_sym[sym] = dict(dsum)

        pc: dict[str, float] = {}
        ph: dict[str, float] = {}
        pqv: dict[str, float] = {}
        if kp.exists():
            kt = pq.read_table(kp, columns=["open_time_ms", "high", "close", "quote_volume"])
            ot = kt["open_time_ms"].to_numpy(zero_copy_only=False).astype(np.int64)
            km = (ot >= min_ms) & (ot < cutoff_i)
            for t_ms, hv, cv, qv in zip(
                ot[km],
                kt["high"].to_numpy(zero_copy_only=False).astype(np.float64)[km],
                kt["close"].to_numpy(zero_copy_only=False).astype(np.float64)[km],
                kt["quote_volume"].to_numpy(zero_copy_only=False).astype(np.float64)[km],
                strict=True,
            ):
                dk = _ms_to_iso_date(int(t_ms))
                pc[dk] = float(cv)
                ph[dk] = float(hv)
                pqv[dk] = float(qv)
        perp_c_by_sym[sym] = pc
        perp_h_by_sym[sym] = ph
        perp_qv_by_sym[sym] = pqv

        sc: dict[str, float] = {}
        sh: dict[str, float] = {}
        if sym in spot_c_df.columns:
            for dk, hv, cv in zip(
                spot_dates,
                spot_h_df[sym].to_numpy(dtype=np.float64),
                spot_c_df[sym].to_numpy(dtype=np.float64),
                strict=True,
            ):
                if math.isfinite(float(cv)) and float(cv) > 0.0:
                    sc[dk] = float(cv)
                if math.isfinite(float(hv)) and float(hv) > 0.0:
                    sh[dk] = float(hv)
        spot_c_by_sym[sym] = sc
        spot_h_by_sym[sym] = sh

    dates = sorted(all_days)
    validate_strict_pre_holdout_dates(dates, context="load_dev_funding_panel")
    idx = pd.to_datetime(dates, utc=True)
    n_t, n_k = len(dates), len(loaded_syms)

    def _fill(src: dict[str, dict[str, float]]) -> pd.DataFrame:
        arr = np.full((n_t, n_k), np.nan, dtype=np.float64)
        for j, sym in enumerate(loaded_syms):
            m = src[sym]
            for i, dk in enumerate(dates):
                if dk in m:
                    arr[i, j] = m[dk]
        return pd.DataFrame(arr, index=idx, columns=loaded_syms)

    return {
        "dates": dates,
        "symbols": loaded_syms,
        "funding_daily": _fill(daily_fund_by_sym),
        "perp_close": _fill(perp_c_by_sym),
        "perp_high": _fill(perp_h_by_sym),
        "perp_quote_volume": _fill(perp_qv_by_sym),
        "spot_close": _fill(spot_c_by_sym),
        "spot_high": _fill(spot_h_by_sym),
        "holdout_rows_analysed": 0,
    }


def compound_intraday_to_daily_map(
    index_utc: pd.DatetimeIndex,
    bar_returns: np.ndarray,
    bar_turnover: np.ndarray,
    bar_exposure: np.ndarray,
) -> tuple[dict[str, float], float, float]:
    """Compound intraday bar returns strictly by UTC calendar day (zero lookahead)."""
    day_keys = index_utc.strftime("%Y-%m-%d").tolist()
    validate_strict_pre_holdout_dates(day_keys, context="compound_intraday_to_daily")
    by_day: dict[str, float] = {}
    for dk, r in zip(day_keys, bar_returns, strict=True):
        by_day[dk] = by_day.get(dk, 1.0) * (1.0 + float(r))
    daily_map = {dk: prod - 1.0 for dk, prod in sorted(by_day.items())}
    yrs = max(1e-6, len(daily_map) / 365.0)
    ann_to = float(np.sum(bar_turnover) / yrs)
    avg_exp = float(np.mean(bar_exposure))
    return daily_map, ann_to, avg_exp


def align_24_7_returns_to_trading_days(
    trading_days: list[str],
    crypto_daily: dict[str, float],
) -> tuple[list[str], np.ndarray]:
    """Compound 24/7 crypto daily returns onto business trading days `(d_{k-1}, d_k]` cleanly.

    Preserves 100% of weekend/holiday crypto returns without dropping or double-counting any day.
    Only returns trading days within `[min(crypto_days), max(crypto_days)]`.
    """
    validate_strict_pre_holdout_dates(trading_days, context="align_24_7.trading_days")
    c_days = sorted(crypto_daily.keys())
    validate_strict_pre_holdout_dates(c_days, context="align_24_7.crypto_days")
    c_start, c_end = c_days[0], c_days[-1]
    overlap_tdays = [d for d in sorted(trading_days) if c_start <= d <= c_end]
    if not overlap_tdays:
        return [], np.empty(0, dtype=np.float64)

    aligned = np.zeros(len(overlap_tdays), dtype=np.float64)
    c_ptr = 0
    n_c = len(c_days)
    # Skip crypto days strictly before first overlap trading day
    while c_ptr < n_c and c_days[c_ptr] < overlap_tdays[0]:
        c_ptr += 1

    for i, td in enumerate(overlap_tdays):
        prod = 1.0
        while c_ptr < n_c and c_days[c_ptr] <= td:
            prod *= 1.0 + float(crypto_daily[c_days[c_ptr]])
            c_ptr += 1
        aligned[i] = prod - 1.0

    return overlap_tdays, aligned


def compute_balanced_series_metrics(
    returns: np.ndarray,
    *,
    ann_days: float = 365.0,
) -> dict[str, Any]:
    """Compute Law-15 balanced performance metrics (Winrate, RR, EV, PF, MaxDD, Calmar, Sharpe, Streaks)."""
    r = np.asarray(returns, dtype=np.float64)
    n = len(r)
    if n < 5:
        return {
            "n_obs": n,
            "cagr_pct": 0.0,
            "ann_vol_pct": 0.0,
            "sharpe": 0.0,
            "max_dd_pct": 0.0,
            "calmar": 0.0,
            "profit_factor": 0.0,
            "winrate_pct": 0.0,
            "avg_rr": 0.0,
            "ev_per_day_bps": 0.0,
            "max_loss_streak_days": 0,
            "worst_day_pct": 0.0,
        }

    eq = np.cumprod(np.maximum(0.0, 1.0 + r))
    peak = np.maximum.accumulate(np.r_[1.0, eq])[1:]
    dd = np.where(peak > 0.0, (peak - eq) / peak, 1.0)
    max_dd = float(np.max(dd))
    yrs = n / float(ann_days)
    cagr = (float(eq[-1]) ** (1.0 / yrs) - 1.0) if (eq[-1] > 0.0 and yrs > 0.0) else -1.0
    mu = float(np.mean(r))
    sd = float(np.std(r, ddof=1)) if n > 1 else 0.0
    sharpe = (mu / sd * math.sqrt(float(ann_days))) if sd > 1e-12 else 0.0
    calmar = (cagr / max_dd) if max_dd > 1e-9 else 0.0

    pos = r[r > 1e-12]
    neg = r[r < -1e-12]
    gains = float(np.sum(pos))
    losses = float(np.sum(-neg))
    pf = (gains / losses) if losses > 1e-12 else (99.0 if gains > 0.0 else 0.0)
    active = len(pos) + len(neg)
    winrate = (100.0 * len(pos) / active) if active > 0 else 0.0
    avg_win = (gains / len(pos)) if len(pos) > 0 else 0.0
    avg_loss = (losses / len(neg)) if len(neg) > 0 else 0.0
    avg_rr = (avg_win / avg_loss) if avg_loss > 1e-12 else 0.0

    cur_s = 0
    max_s = 0
    for val in r:
        if val < -1e-12:
            cur_s += 1
            if cur_s > max_s:
                max_s = cur_s
        else:
            cur_s = 0

    return {
        "n_obs": n,
        "cagr_pct": round(cagr * 100.0, 2),
        "ann_vol_pct": round(sd * math.sqrt(float(ann_days)) * 100.0, 2),
        "sharpe": round(sharpe, 3),
        "max_dd_pct": round(max_dd * 100.0, 2),
        "calmar": round(calmar, 3),
        "profit_factor": round(pf, 3),
        "winrate_pct": round(winrate, 2),
        "avg_rr": round(avg_rr, 3),
        "ev_per_day_bps": round(mu * 10_000.0, 3),
        "max_loss_streak_days": max_s,
        "worst_day_pct": round(float(np.min(r)) * 100.0, 3),
    }


def compute_empirical_monthly_starvation(
    dates: list[str],
    daily_returns: np.ndarray,
    *,
    min_month_return_frac: float = 0.005,
) -> dict[str, Any]:
    """Compute empirical calendar-month payout starvation rate (`monthly return < threshold`).

    On a `10K` account with `50 USD` minimum payout (at `80%` split = `62.5 USD` profit = `0.625%`)
    or general `0.50%` monthly floor, tracks BOTH `<= 0%` dry months and `< min_month_return_frac`
    starved payout months plus longest consecutive dry streak!
    """
    by_ym: dict[str, float] = {}
    for dk, r in zip(dates, daily_returns, strict=True):
        ym = dk[:7]
        by_ym[ym] = by_ym.get(ym, 1.0) * (1.0 + float(r))
    months = sorted(by_ym.keys())
    m_rets = np.array([by_ym[m] - 1.0 for m in months], dtype=np.float64)
    n_m = len(m_rets)
    if n_m == 0:
        return {"n_months": 0, "pct_le_zero": 100.0, "pct_starved": 100.0, "max_dry_streak": 0}
    le_zero = m_rets <= 0.0
    starved = m_rets < float(min_month_return_frac)
    cur = 0
    mx = 0
    for is_dry in starved:
        if is_dry:
            cur += 1
            if cur > mx:
                mx = cur
        else:
            cur = 0
    return {
        "n_months": n_m,
        "mean_month_pct": round(float(np.mean(m_rets)) * 100.0, 3),
        "median_month_pct": round(float(np.median(m_rets)) * 100.0, 3),
        "pct_le_zero": round(100.0 * float(np.mean(le_zero)), 2),
        "pct_starved": round(100.0 * float(np.mean(starved)), 2),
        "max_dry_streak": mx,
    }


def evaluate_cpcv_oos_sharpe(
    returns_matrix: np.ndarray,
    candidate_names: list[str],
    *,
    n_groups: int = 6,
    k_test_groups: int = 2,
    purge_bars: int = 5,
    embargo_bars: int = 5,
    ann_days: float = 365.0,
) -> dict[str, Any]:
    """Run Lopez de Prado (2018) CPCV with strict purging & embargoing across all candidates."""
    n_obs, n_cand = returns_matrix.shape
    splits = combinatorial_purged_cv(
        n_obs,
        n_groups=n_groups,
        k_test_groups=k_test_groups,
        purge_bars=purge_bars,
        embargo_bars=embargo_bars,
    )
    per_cand_oos: dict[str, list[float]] = {name: [] for name in candidate_names}
    winner_oos_sharpes: list[float] = []

    for sp in splits:
        tr = np.asarray(sp.train_indices, dtype=np.intp)
        te = np.asarray(sp.test_indices, dtype=np.intp)
        tr_mat = returns_matrix[tr]
        te_mat = returns_matrix[te]

        tr_sd = np.std(tr_mat, axis=0, ddof=1)
        tr_sr = np.where(tr_sd > 1e-12, np.mean(tr_mat, axis=0) / np.where(tr_sd > 1e-12, tr_sd, 1.0), 0.0)
        te_sd = np.std(te_mat, axis=0, ddof=1)
        te_sr = np.where(te_sd > 1e-12, np.mean(te_mat, axis=0) / np.where(te_sd > 1e-12, te_sd, 1.0), 0.0) * math.sqrt(
            float(ann_days)
        )

        best_j = int(np.argmax(tr_sr))
        winner_oos_sharpes.append(float(te_sr[best_j]))
        for j, name in enumerate(candidate_names):
            per_cand_oos[name].append(float(te_sr[j]))

    per_cand_summary = {}
    for name, vals in per_cand_oos.items():
        arr = np.asarray(vals, dtype=np.float64)
        per_cand_summary[name] = {
            "median_oos_sharpe": round(float(np.median(arr)), 3),
            "mean_oos_sharpe": round(float(np.mean(arr)), 3),
            "min_oos_sharpe": round(float(np.min(arr)), 3),
            "pct_positive_splits": round(100.0 * float(np.mean(arr > 0.0)), 1),
        }

    w_arr = np.asarray(winner_oos_sharpes, dtype=np.float64)
    return {
        "n_splits": len(splits),
        "n_groups": n_groups,
        "k_test_groups": k_test_groups,
        "purge_bars": purge_bars,
        "embargo_bars": embargo_bars,
        "is_winner_oos_median_sharpe": round(float(np.median(w_arr)), 3),
        "is_winner_oos_mean_sharpe": round(float(np.mean(w_arr)), 3),
        "is_winner_oos_min_sharpe": round(float(np.min(w_arr)), 3),
        "is_winner_pct_positive_splits": round(100.0 * float(np.mean(w_arr > 0.0)), 1),
        "per_candidate": per_cand_summary,
    }


def _run_ftmo_10k_c10_mc(
    stage_arrays: tuple[np.ndarray, ...],
    idx_matrix: np.ndarray,
    *,
    fee_usd: float = FTMO_10K_BF_FEE_USD,
    fee_regular_usd: float = FTMO_10K_REG_FEE_USD,
) -> dict[str, Any]:
    """Run exact FTMO 2-Step Standard 10K `C10_NEWS_ON` single-ticket zero-retry MC (`DAILY_APPROX`)."""
    cfg = VARIANT_PHASE_CONFIGS["C10_NEWS_ON"]
    res = _simulate_single_ticket_rules_numba(
        idx_matrix,
        *stage_arrays,
        2,  # 2-Step FTMO
        10_000.0,
        float(fee_usd),
        float(fee_regular_usd),
        VN_CARD_FX_FEE_PCT,
        0.015,  # withdrawal fee 1.5%
        1.0,  # 100% fee refund on first payout
        0.10,  # P1 target 10%
        0.05,  # P2 target 5%
        0.05,  # 5% daily DD
        0.10,  # 10% static DD
        DD_STATIC,
        False,
        0.0,
        4,  # min 4 trading days
        0,
        0.0,
        0.80,  # 80% profit split
        10,  # bi-weekly payout cycle (10 trading days)
        50.0,  # 50 USD min payout
        False,
        float(cfg["p1_lock_trigger"]),
        float(cfg["p2_lock_trigger"]),
        float(cfg["amber_dd"]),
        float(cfg["red_dd"]),
        float(cfg["p1_ea_daily_stop"]),
        float(cfg["p2_ea_daily_stop"]),
        float(cfg["funded_ea_daily_stop"]),
        0,
        DEFAULT_DISCOUNT_RATE,
        0,  # max_retries = 0 (Law-13 single-ticket zero-retry!)
    )
    return summarize_single_ticket_mc(
        res,
        fee_usd=fee_usd,
        card_fx_fee_pct=VN_CARD_FX_FEE_PCT,
        usd_vnd_rate=USD_VND_RATE,
        horizon_days=int(idx_matrix.shape[1]),
        fee_regular_usd=fee_regular_usd,
    )


def _blend_stage_with_alpha2(
    base_stages: tuple[np.ndarray, ...],
    alpha2_ret: np.ndarray,
    *,
    cap_usd: float = 10_000.0,
    p7e_weight: float = 1.0,
    a2_risk_scale_funded: float = 1.0,
    a2_risk_scale_eval: float = 1.0,
    intraday_dd_shock_mult: float = 1.50,
) -> tuple[np.ndarray, ...]:
    """Conservatively combine `PORT_7E` M1 stage arrays with an aligned orthogonal Alpha #2 stream.

    Conservative intraday drawdown coupling:
      - Negative Alpha #2 days add `1.50x` adverse drawdown on top of `PORT_7E`'s intraday DD
        (assumes worst-case intraday overlap, never optimistic offsetting!).
      - Positive Alpha #2 days do NOT subtract from `PORT_7E`'s intraday DD peak-trough risk.
    """
    a2_r = np.asarray(alpha2_ret, dtype=np.float64)
    # 7 groups of 4 arrays: p1, p1l, p2, p2l, fn, amb, red
    scales = (
        (p7e_weight, a2_risk_scale_eval),  # p1
        (p7e_weight, a2_risk_scale_eval * 0.65),  # p1l
        (p7e_weight, a2_risk_scale_eval * 0.85),  # p2
        (p7e_weight, a2_risk_scale_eval * 0.50),  # p2l
        (p7e_weight, a2_risk_scale_funded),  # fn
        (p7e_weight, a2_risk_scale_funded * 0.65),  # amb
        (p7e_weight, a2_risk_scale_funded * 0.40),  # red
    )
    out_arrays: list[np.ndarray] = []
    for grp_i, (w7, wa2) in enumerate(scales):
        n_arr = base_stages[grp_i * 4]
        d_arr = base_stages[grp_i * 4 + 1]
        u_arr = base_stages[grp_i * 4 + 2]
        f_arr = base_stages[grp_i * 4 + 3]

        a2_usd = a2_r * cap_usd * wa2
        comb_n = n_arr * w7 + a2_usd
        # Conservative DD: add 1.5x of any negative Alpha #2 day on top of PORT_7E intraday DD
        a2_adverse_dd = np.maximum(0.0, -a2_usd) * intraday_dd_shock_mult
        comb_d = d_arr * w7 + a2_adverse_dd
        comb_u = u_arr * w7 + np.maximum(0.0, a2_usd)
        comb_f = np.where((f_arr != 0) | (np.abs(a2_usd) > 1e-6), 1, 0).astype(np.int8)
        out_arrays.extend([comb_n, comb_d, comb_u, comb_f])

    return tuple(out_arrays)


@njit(cache=True)
def _simulate_dual_account_hwm_cashflow_numba(
    idx_matrix: np.ndarray,
    n_fn: np.ndarray,
    d_fn: np.ndarray,
    n_amb: np.ndarray,
    d_amb: np.ndarray,
    n_red: np.ndarray,
    d_red: np.ndarray,
    a2_daily_ret: np.ndarray,
    ftmo_cap_usd: float,
    cex_cap_usd: float,
    min_payout_usd: float,
    amber_dd: float,
    red_dd: float,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Coupled Dual-Account Cashflow MC (`FTMO Funded PORT_7E` + `Separate CEX Own-Book Alpha #2`).

    Models physically executable, rule-compliant dual-account operation on the EXACT SAME market days:
      - Account 1 (FTMO Funded 10K `C10_NEWS_ON`, 80% split, bi-weekly 10-day cycle, >= 50 USD gross
        payout threshold matching `simulator.py:365-397`, 5% daily / 10% static DD, Amber/Red brakes,
        2.5% EA daily stop): pays independently when profitable above `ftmo_cap_usd`.
      - Account 2 (Separate Binance Own-Book at `cex_cap_usd`, 2x buffer): pays monthly cashflow ONLY
        above its High-Water-Mark (`cex_eq - cex_hwm >= min_payout_usd`), then resets equity to HWM.
      - Month payout eligibility checks gross payout eligibility (`m_ftmo_paid == 1` or combined gross
        payout `>= min_payout_usd`) so the 1.5% withdrawal rail fee never misclassifies a paid FTMO
        month (`50.00 <= gross_share < 50.76`) as dry; `cash24` still records exact net cash after fees.
    """
    n_paths, horizon = idx_matrix.shape
    ftmo_dry_m = np.zeros(n_paths, dtype=np.int32)
    dual_dry_m = np.zeros(n_paths, dtype=np.int32)
    tot_months = np.zeros(n_paths, dtype=np.int32)
    ftmo_max_streak = np.zeros(n_paths, dtype=np.int32)
    dual_max_streak = np.zeros(n_paths, dtype=np.int32)
    dual_cash_24m = np.zeros(n_paths, dtype=np.float64)

    daily_cap = ftmo_cap_usd * 0.05
    static_floor = ftmo_cap_usd * 0.90
    ea_cut = ftmo_cap_usd * 0.025

    for b in range(n_paths):
        f_alive = True
        f_bal = ftmo_cap_usd
        f_cycle_d = 0

        c_eq = cex_cap_usd
        c_hwm = cex_cap_usd

        m_days = 0
        m_ftmo_paid = 0
        m_ftmo_gross = 0.0
        cur_f_str = 0
        cur_d_str = 0
        best_f_str = 0
        best_d_str = 0
        tot_m = 0
        f_dry = 0
        d_dry = 0
        cash24 = 0.0

        for d in range(horizon):
            src = idx_matrix[b, d]
            # 1. Step FTMO Funded account (with C10_NEWS_ON Amber/Red DD brakes matching simulator.py!)
            if f_alive:
                eq_pct = (f_bal - ftmo_cap_usd) / ftmo_cap_usd
                if eq_pct <= -red_dd:
                    net = n_red[src]
                    dd = d_red[src]
                elif eq_pct <= -amber_dd:
                    net = n_amb[src]
                    dd = d_amb[src]
                else:
                    net = n_fn[src]
                    dd = d_fn[src]
                d_hit = (f_bal - dd) <= (f_bal - daily_cap) + 1e-9
                m_hit = (f_bal - dd) <= static_floor + 1e-9
                if (not d_hit) and (not m_hit) and (dd > ea_cut):
                    dd_eff = min(dd, ea_cut + ftmo_cap_usd * 0.0020)
                    net = min(net, -dd_eff)
                    d_hit = (f_bal - dd_eff) <= (f_bal - daily_cap) + 1e-9
                    m_hit = (f_bal - dd_eff) <= static_floor + 1e-9
                if d_hit or m_hit:
                    f_alive = False
                    f_bal = 0.0
                else:
                    f_bal += net
                    f_cycle_d += 1
                    if f_cycle_d >= 10:
                        prof = f_bal - ftmo_cap_usd
                        if prof > 1e-6:
                            share = prof * 0.80
                            if share >= min_payout_usd - 1e-9:
                                net_out = share * (1.0 - 0.015)
                                m_ftmo_paid = 1
                                m_ftmo_gross += share
                                if d < 504:
                                    cash24 += net_out
                                f_bal = ftmo_cap_usd
                        f_cycle_d = 0

            # 2. Step separate CEX Own-Book Alpha #2 account (strictly date-coupled!)
            if c_eq > 0.0:
                c_eq *= 1.0 + a2_daily_ret[src]
                if c_eq < 0.0:
                    c_eq = 0.0

            m_days += 1
            if m_days >= 21:
                tot_m += 1
                m_cex_pay = 0.0
                if c_eq - c_hwm >= min_payout_usd - 1e-9:
                    m_cex_pay = c_eq - c_hwm
                    c_eq = c_hwm
                    if d < 504:
                        cash24 += m_cex_pay

                if m_ftmo_paid == 0:
                    f_dry += 1
                    cur_f_str += 1
                    if cur_f_str > best_f_str:
                        best_f_str = cur_f_str
                else:
                    cur_f_str = 0

                if m_ftmo_paid == 0 and (m_ftmo_gross + m_cex_pay) < min_payout_usd - 1e-9:
                    d_dry += 1
                    cur_d_str += 1
                    if cur_d_str > best_d_str:
                        best_d_str = cur_d_str
                else:
                    cur_d_str = 0

                m_days = 0
                m_ftmo_paid = 0
                m_ftmo_gross = 0.0

        tot_months[b] = tot_m
        ftmo_dry_m[b] = f_dry
        dual_dry_m[b] = d_dry
        ftmo_max_streak[b] = best_f_str
        dual_max_streak[b] = best_d_str
        dual_cash_24m[b] = cash24

    return tot_months, ftmo_dry_m, dual_dry_m, ftmo_max_streak, dual_max_streak, dual_cash_24m


def evaluate_dual_account_cashflow(
    idx_matrix: np.ndarray,
    n_fn: np.ndarray,
    d_fn: np.ndarray,
    a2_daily_ret: np.ndarray,
    *,
    n_amb: np.ndarray | None = None,
    d_amb: np.ndarray | None = None,
    n_red: np.ndarray | None = None,
    d_red: np.ndarray | None = None,
    ftmo_cap_usd: float = 10_000.0,
    cex_cap_usd: float = 10_000.0,
    min_payout_usd: float = 50.0,
    amber_dd: float = 0.035,
    red_dd: float = 0.060,
) -> dict[str, Any]:
    """Summarize coupled Dual-Account (`FTMO Funded PORT_7E` + `CEX Own-Book Alpha #2`) monthly cashflow."""
    n_fn_c = np.ascontiguousarray(n_fn, dtype=np.float64)
    d_fn_c = np.ascontiguousarray(d_fn, dtype=np.float64)
    n_amb_c = n_fn_c if n_amb is None else np.ascontiguousarray(n_amb, dtype=np.float64)
    d_amb_c = d_fn_c if d_amb is None else np.ascontiguousarray(d_amb, dtype=np.float64)
    n_red_c = n_fn_c if n_red is None else np.ascontiguousarray(n_red, dtype=np.float64)
    d_red_c = d_fn_c if d_red is None else np.ascontiguousarray(d_red, dtype=np.float64)
    tot_m, f_dry, d_dry, f_str, d_str, cash24 = _simulate_dual_account_hwm_cashflow_numba(
        idx_matrix,
        n_fn_c,
        d_fn_c,
        n_amb_c,
        d_amb_c,
        n_red_c,
        d_red_c,
        np.ascontiguousarray(a2_daily_ret, dtype=np.float64),
        float(ftmo_cap_usd),
        float(cex_cap_usd),
        float(min_payout_usd),
        float(amber_dd),
        float(red_dd),
    )
    tot_sum = max(1, int(np.sum(tot_m)))
    f_pct = 100.0 * int(np.sum(f_dry)) / tot_sum
    d_pct = 100.0 * int(np.sum(d_dry)) / tot_sum
    return {
        "ftmo_cap_usd": ftmo_cap_usd,
        "cex_cap_usd": cex_cap_usd,
        "min_monthly_payout_usd": min_payout_usd,
        "ftmo_only_dry_months_pct": round(f_pct, 2),
        "dual_account_dry_months_pct": round(d_pct, 2),
        "dry_months_reduction_pp": round(f_pct - d_pct, 2),
        "ftmo_only_dry_streak_p50": int(np.median(f_str)),
        "dual_account_dry_streak_p50": int(np.median(d_str)),
        "dual_account_dry_streak_p95": int(np.quantile(d_str, 0.95)),
        "dual_mean_cash_24m_usd": round(float(np.mean(cash24)), 2),
        "dual_mean_cash_24m_vnd_tr": round(float(np.mean(cash24)) * USD_VND_RATE / 1_000_000.0, 2),
        "dual_med_cash_24m_usd": round(float(np.median(cash24)), 2),
        "dual_med_cash_24m_vnd_tr": round(float(np.median(cash24)) * USD_VND_RATE / 1_000_000.0, 2),
    }


def run_portfolio_7e_plus_alpha2_study(
    *,
    spot_cache_dir: Path = SPOT_CACHE_DIR,
    h1_cache_dir: Path = LAB1_CACHE_DIR,
    funding_dir: Path = FUNDING_CACHE_DIR,
    n_mc_paths: int = 5_000,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Execute full Dev-only (`<= 2024-12-31`) Alpha #2 + `PORT_7E` combination study."""
    t0 = time.perf_counter()
    lock_sha = assert_holdout_locked()

    # 1. Load frozen PORT_7E M1 tapes (strictly <= 2024-12-31)
    frozen = build_or_load_frozen_tapes(force_rebuild=False)
    ext_days = sorted(frozen["ext_days"])
    validate_strict_pre_holdout_dates(ext_days, context="study.port7e_ext_days")
    reg = load_registry()
    base_r = {e["id"]: float(e["base_risk_pct"]) / 100.0 for e in reg["engines"]}
    rn_cal = load_red_news_calendar("red_news_official_2018_2024")
    replay_cache = ExactTierReplayCache(ext_days, frozen["tapes"], base_r, rn_cal)

    c10_cfg = VARIANT_PHASE_CONFIGS["C10_NEWS_ON"]
    stages_10k_full = replay_cache.build_stage_tuple(
        capital_usd=10_000.0,
        p1_mult=float(c10_cfg["p1_mult"]),
        p1_lock_mult=float(c10_cfg["p1_lock_mult"]),
        p2_mult=float(c10_cfg["p2_mult"]),
        p2_lock_mult=float(c10_cfg["p2_lock_mult"]),
        funded_mult=float(c10_cfg["funded_mult"]),
        amber_mult=float(c10_cfg["amber_mult"]),
        red_mult=float(c10_cfg["red_mult"]),
        p1_symcap=float(c10_cfg["p1_symcap_pct"]),
        p2_symcap=float(c10_cfg["p2_symcap_pct"]),
        fn_symcap=float(c10_cfg["funded_symcap_pct"]),
        profile_mode="Standard",
        p1_news=True,
        p2_news=True,
        fn_news=True,
        friction_mult=1.0,
        steps=2,
    )
    p7e_bal_100k, p7e_nets_100k, _, _, _ = replay_cache.get_exact_tier_stage(
        capital_usd=100_000.0,
        mult=1.0,
        symcap_pct=1.0,
        profile_mode="Standard",
        use_red_news=True,
        friction_mult=1.0,
    )
    p7e_daily_ret_map = {dk: float(p7e_nets_100k[i]) / 100_000.0 for i, dk in enumerate(ext_days)}

    # 2. Load Dev-sliced (<= 2024-12-31) crypto caches: Spot 4H (50 coins), 1H (40 coins), Funding (20 perps)
    panel_4h = load_dev_spot_panel_from_parquet(
        "4h",
        symbols=UNIVERSE_50_SYMBOLS,
        cache_dir=spot_cache_dir,
        min_date="2019-01-01",
    )
    panel_1h = load_dev_spot_panel_from_parquet(
        "1h",
        symbols=TOP40_1H_SYMBOLS,
        cache_dir=h1_cache_dir,
        min_date="2021-01-01",
    )
    panel_fund = load_dev_funding_panel_from_parquet(
        symbols=PERP_UNIVERSE_20,
        funding_dir=funding_dir,
        spot_cache_dir=spot_cache_dir,
        min_date="2020-01-01",
    )

    # 3. Evaluate all M = 8 pre-registered Alpha #2 candidates through unified `quant_lab` engines
    top15_4h = causal_rolling_top_n_mask(panel_4h["quote_volume"], panel_4h["close"], lookback_bars=180, top_n=15)
    top15_1h = causal_rolling_top_n_mask(panel_1h["quote_volume"], panel_1h["close"], lookback_bars=720, top_n=15)

    eng_4h = UnifiedSpotEngine(F4EmaConfig(deadband=0.015, bars_per_year=365.0 * 6.0))
    eng_1h = UnifiedSpotEngine(
        F4EmaConfig(
            fast_span=96,
            slow_span=480,
            btc_fast=240,
            btc_slow=1200,
            vol_window=168,
            target_ann_vol=0.15,
            bars_per_year=365.0 * 24.0,
            deadband=0.02,
        )
    )

    w_4h_f4 = eng_4h.build_f4_weights(panel_4h["close"], top15_4h)
    w_4h_f3 = eng_4h.build_donchian_weights(
        panel_4h["close"],
        panel_4h["high"],
        panel_4h["low"],
        top15_4h,
        entry_window=120,
        exit_window=60,
        vol_window=120,
        bars_per_year=365.0 * 6.0,
        deadband=0.015,
    )
    w_1h_ema = eng_1h.build_f4_weights(panel_1h["close"], top15_1h)
    w_1h_don = eng_1h.build_donchian_weights(
        panel_1h["close"],
        panel_1h["high"],
        panel_1h["low"],
        top15_1h,
        entry_window=168,
        exit_window=84,
        vol_window=168,
        bars_per_year=365.0 * 24.0,
        deadband=0.02,
        btc_symbol="BTCUSDT",
        btc_fast=240,
        btc_slow=720,
    )

    w_carry_be = carry_btc_eth_cons_weights(
        panel_fund["funding_daily"], panel_fund["spot_close"], panel_fund["perp_close"]
    )
    w_carry_top5 = carry_top_k_hysteresis_weights(
        panel_fund["funding_daily"],
        panel_fund["spot_close"],
        panel_fund["perp_close"],
        panel_fund["perp_quote_volume"],
        k_max=5,
        keep_rank_limit=8,
        enter_ann=0.12,
        exit_ann=0.04,
        max_single=0.25,
        tier1_top_n=12,
        use_invvol=False,
    )
    w_carry_blend = carry_v2_blend_weights(w_carry_be, w_carry_top5, core_share=0.70, satellite_share=0.30)

    candidates_1x: dict[str, dict[str, float]] = {}
    candidates_2x: dict[str, dict[str, float]] = {}
    cand_meta: dict[str, dict[str, Any]] = {}

    spot_specs = [
        ("A2_SPOT_4H_F4_EMA", "crypto-spot-cache/4h", eng_4h, panel_4h, w_4h_f4, 365 * 6),
        ("A2_SPOT_4H_F3_DON", "crypto-spot-cache/4h", eng_4h, panel_4h, w_4h_f3, 365 * 6),
        ("A2_SPOT_1H_EMA_96_480", "crypto-1h-cache/1h", eng_1h, panel_1h, w_1h_ema, 365 * 24),
        ("A2_SPOT_1H_DON_168_84", "crypto-1h-cache/1h", eng_1h, panel_1h, w_1h_don, 365 * 24),
    ]
    for sid, src_label, eng, pnl, w_df, ppy in spot_specs:
        bt1 = eng.run_backtest(pnl["close"], w_df, fee_bps=10.0, slippage_bps=5.0, periods_per_year=ppy)["backtest"]
        bt2 = eng.run_backtest(pnl["close"], w_df, fee_bps=20.0, slippage_bps=10.0, periods_per_year=ppy)["backtest"]
        d1, to1, exp1 = compound_intraday_to_daily_map(
            pnl["index"],
            bt1["strategy_return"].to_numpy(dtype=np.float64),
            bt1["turnover"].to_numpy(dtype=np.float64),
            bt1["gross_exposure"].to_numpy(dtype=np.float64),
        )
        d2, _, _ = compound_intraday_to_daily_map(
            pnl["index"],
            bt2["strategy_return"].to_numpy(dtype=np.float64),
            bt2["turnover"].to_numpy(dtype=np.float64),
            bt2["gross_exposure"].to_numpy(dtype=np.float64),
        )
        candidates_1x[sid] = d1
        candidates_2x[sid] = d2
        cand_meta[sid] = {
            "source_cache": src_label,
            "cost_1x_bps": 15.0,
            "cost_2x_bps": 30.0,
            "annual_turnover_x": round(to1, 2),
            "avg_gross_exposure_pct": round(exp1 * 100.0, 2),
            "margin_stress": None,
        }

    carry_specs = [
        ("A2_CARRY_BTC_ETH_2X", w_carry_be),
        ("A2_CARRY_TOP5_HYST_2X", w_carry_top5),
        ("A2_CARRY_V2_BLEND_70_30", w_carry_blend),
    ]
    cfg_c1 = FundingCarryConfig(
        equity_buffer_mult=2.0,
        oneway_pair_cost_bps=20.0,
        basis_cross_slip_bps=3.0,
        exit_shock_mult=1.0,
    )
    cfg_c2 = FundingCarryConfig(
        equity_buffer_mult=2.0,
        oneway_pair_cost_bps=40.0,
        basis_cross_slip_bps=6.0,
        exit_shock_mult=2.0,
    )
    for sid, w_c in carry_specs:
        r1 = run_funding_carry_backtest(
            panel_fund["funding_daily"],
            panel_fund["spot_close"],
            panel_fund["perp_close"],
            w_c,
            perp_high=panel_fund["perp_high"],
            spot_high=panel_fund["spot_high"],
            config=cfg_c1,
        )
        r2 = run_funding_carry_backtest(
            panel_fund["funding_daily"],
            panel_fund["spot_close"],
            panel_fund["perp_close"],
            w_c,
            perp_high=panel_fund["perp_high"],
            spot_high=panel_fund["spot_high"],
            config=cfg_c2,
        )
        bt1 = r1["backtest"]
        bt2 = r2["backtest"]
        dates_f = panel_fund["dates"]
        candidates_1x[sid] = {
            dk: float(v) for dk, v in zip(dates_f, bt1["strategy_return"].to_numpy(dtype=np.float64), strict=True)
        }
        candidates_2x[sid] = {
            dk: float(v) for dk, v in zip(dates_f, bt2["strategy_return"].to_numpy(dtype=np.float64), strict=True)
        }
        yrs_f = max(1e-6, len(dates_f) / 365.0)
        cand_meta[sid] = {
            "source_cache": "crypto-spot-cache/funding+1d",
            "cost_1x_bps": 23.0,
            "cost_2x_bps": 46.0,
            "annual_turnover_x": round(float(bt1["turnover"].sum() / yrs_f), 2),
            "avg_gross_exposure_pct": round(float(bt1["gross_exposure"].mean()) * 100.0, 2),
            "margin_stress": r1["margin_stress"],
        }

    # Candidate #8: Pre-registered 50/50 Spot 4H + Carry BTC+ETH Composite (2020-2024 overlap)
    comp_days = sorted(set(candidates_1x["A2_SPOT_4H_F4_EMA"]) & set(candidates_1x["A2_CARRY_BTC_ETH_2X"]))
    validate_strict_pre_holdout_dates(comp_days, context="study.composite_days")
    candidates_1x["A2_COMPOSITE_SPOT50_CARRY50"] = {
        d: 0.50 * candidates_1x["A2_SPOT_4H_F4_EMA"][d] + 0.50 * candidates_1x["A2_CARRY_BTC_ETH_2X"][d]
        for d in comp_days
    }
    candidates_2x["A2_COMPOSITE_SPOT50_CARRY50"] = {
        d: 0.50 * candidates_2x["A2_SPOT_4H_F4_EMA"][d] + 0.50 * candidates_2x["A2_CARRY_BTC_ETH_2X"][d]
        for d in comp_days
    }
    cand_meta["A2_COMPOSITE_SPOT50_CARRY50"] = {
        "source_cache": "crypto-spot-cache/4h+funding",
        "cost_1x_bps": 19.0,
        "cost_2x_bps": 38.0,
        "annual_turnover_x": round(
            0.50 * cand_meta["A2_SPOT_4H_F4_EMA"]["annual_turnover_x"]
            + 0.50 * cand_meta["A2_CARRY_BTC_ETH_2X"]["annual_turnover_x"],
            2,
        ),
        "avg_gross_exposure_pct": round(
            0.50 * cand_meta["A2_SPOT_4H_F4_EMA"]["avg_gross_exposure_pct"]
            + 0.50 * cand_meta["A2_CARRY_BTC_ETH_2X"]["avg_gross_exposure_pct"],
            2,
        ),
        "margin_stress": cand_meta["A2_CARRY_BTC_ETH_2X"]["margin_stress"],
    }

    cand_order = list(candidates_1x.keys())
    m_total = len(cand_order)

    # 4. Build common Dev overlap matrix (2021-01-01..2024-12-31) for empirical DSR, PBO (CSCV), and CPCV!
    common_days = sorted(set.intersection(*(set(candidates_1x[s].keys()) for s in cand_order)))
    validate_strict_pre_holdout_dates(common_days, context="study.common_days_pbo_cpcv")
    ret_mat_common = np.column_stack(
        [np.array([candidates_1x[s][d] for d in common_days], dtype=np.float64) for s in cand_order]
    )
    pbo_res = compute_pbo_cscv(ret_mat_common, n_slices=16)
    cpcv_res = evaluate_cpcv_oos_sharpe(
        ret_mat_common,
        cand_order,
        n_groups=6,
        k_test_groups=2,
        purge_bars=5,
        embargo_bars=5,
        ann_days=365.0,
    )

    # Empirical daily Sharpe per candidate on common window for Bailey & Lopez de Prado DSR
    trial_daily_sharpes = []
    for j in range(m_total):
        col = ret_mat_common[:, j]
        sd = float(np.std(col, ddof=1))
        trial_daily_sharpes.append(float(np.mean(col) / sd) if sd > 1e-12 else 0.0)

    # Within-family trial Sharpes so cross-family variance (Spot vs Carry) never distorts Spot DSR!
    spot_family_idxs = [j for j, sid in enumerate(cand_order) if sid.startswith("A2_SPOT_")]
    carry_family_idxs = [j for j, sid in enumerate(cand_order) if sid.startswith("A2_CARRY_")]
    spot_family_sharpes = [trial_daily_sharpes[j] for j in spot_family_idxs]
    carry_family_sharpes = [trial_daily_sharpes[j] for j in carry_family_idxs]

    # 5. Per-candidate full-Dev metrics, DSR, CPCV, and correlation |r| + unbiased tail stats vs PORT_7E
    cand_results: dict[str, Any] = {}
    for sid in cand_order:
        d_sorted = sorted(candidates_1x[sid].keys())
        r1 = np.array([candidates_1x[sid][d] for d in d_sorted], dtype=np.float64)
        r2 = np.array([candidates_2x[sid][d] for d in d_sorted], dtype=np.float64)
        m1 = compute_balanced_series_metrics(r1, ann_days=365.0)
        m2 = compute_balanced_series_metrics(r2, ann_days=365.0)

        # Cost breakeven multiplier estimate via linear friction drag
        g1 = float(np.mean(r1))
        g2 = float(np.mean(r2))
        drag_1x = g1 - g2
        be_mult = ((g1 + drag_1x) / drag_1x) if drag_1x > 1e-12 else (9.99 if g1 > 0.0 else 0.0)

        dsr_emp_pooled = deflated_sharpe_ratio_empirical(
            r1,
            trial_sharpes=trial_daily_sharpes,
            n_trials=m_total,
            annualization_days=365,
            sharpes_are_annualized=False,
        )
        if sid.startswith("A2_SPOT_"):
            fam_trials = spot_family_sharpes
            fam_label = "SPOT_TREND_4"
        elif sid.startswith("A2_CARRY_"):
            fam_trials = carry_family_sharpes
            fam_label = "FUNDING_CARRY_3"
        else:
            fam_trials = spot_family_sharpes
            fam_label = "COMPOSITE_VS_SPOT_4"
        dsr_emp_fam = deflated_sharpe_ratio_empirical(
            r1,
            trial_sharpes=fam_trials,
            n_trials=len(fam_trials),
            annualization_days=365,
            sharpes_are_annualized=False,
        )
        dsr_proxy = deflated_sharpe_ratio(r1, n_trials=m_total, annualization=365.0)

        # Exact correlation & unbiased tail behavior on PORT_7E's OWN worst 5% days (no Berkson collider bias!)
        ov_days, a2_aligned = align_24_7_returns_to_trading_days(ext_days, candidates_1x[sid])
        p7e_ov = np.array([p7e_daily_ret_map[d] for d in ov_days], dtype=np.float64)
        if len(ov_days) >= 30 and float(np.std(a2_aligned, ddof=1)) > 1e-12 and float(np.std(p7e_ov, ddof=1)) > 1e-12:
            corr_r = float(np.corrcoef(p7e_ov, a2_aligned)[0, 1])
            tail_rep = tail_correlation_report(
                np.column_stack([p7e_ov, a2_aligned]),
                ["PORT_7E", sid],
                tail_pct=0.05,
            )
            comb_tail_corr = float(tail_rep["worst_tail_corr"]["max"])
            p7e_q05 = float(np.quantile(p7e_ov, 0.05))
            p7e_tail_mask = p7e_ov <= p7e_q05
            a2_on_p7e_worst5 = a2_aligned[p7e_tail_mask]
            p7e_on_p7e_worst5 = p7e_ov[p7e_tail_mask]
            p7e_tail_corr = (
                float(np.corrcoef(p7e_on_p7e_worst5, a2_on_p7e_worst5)[0, 1])
                if float(np.std(a2_on_p7e_worst5, ddof=1)) > 1e-12
                else 0.0
            )
            a2_mean_on_p7e_worst5_bps = float(np.mean(a2_on_p7e_worst5)) * 10_000.0
        else:
            corr_r = 0.0
            comb_tail_corr = 0.0
            p7e_tail_corr = 0.0
            a2_mean_on_p7e_worst5_bps = 0.0

        cand_results[sid] = {
            **cand_meta[sid],
            "dev_window": f"{d_sorted[0]}..{d_sorted[-1]}",
            "metrics_1x": m1,
            "metrics_2x": m2,
            "breakeven_cost_mult": round(be_mult, 2),
            "dsr_family_group": fam_label,
            "dsr_empirical_within_family": round(dsr_emp_fam.dsr, 4),
            "dsr_empirical_within_family_z": round(dsr_emp_fam.z_stat, 3),
            "dsr_empirical_pooled": round(dsr_emp_pooled.dsr, 4),
            "dsr_empirical": round(dsr_emp_fam.dsr, 4),
            "dsr_proxy": dsr_proxy["dsr"],
            "cpcv": cpcv_res["per_candidate"][sid],
            "corr_vs_port7e": round(corr_r, 4),
            "abs_corr_vs_port7e": round(abs(corr_r), 4),
            "p7e_worst5_tail_corr": round(p7e_tail_corr, 4),
            "a2_mean_bps_on_p7e_worst5_days": round(a2_mean_on_p7e_worst5_bps, 2),
            "combined_worst5_tail_corr": round(comb_tail_corr, 4),
            "overlap_trading_days_vs_port7e": len(ov_days),
            "monthly_starvation_standalone": compute_empirical_monthly_starvation(
                d_sorted, r1, min_month_return_frac=0.005
            ),
        }

    # 6. Portfolio Combination & Starved-Payout-Month Study (`PORT_7E` vs `PORT_7E + Alpha #2`)
    # Align on exact 2020-01-02..2024-12-31 Dev trading-day overlap where BOTH PORT_7E and Spot/Carry exist!
    ov_days_2020, spot4h_ov = align_24_7_returns_to_trading_days(ext_days, candidates_1x["A2_SPOT_4H_F4_EMA"])
    ov_days_carry, carry_ov = align_24_7_returns_to_trading_days(ext_days, candidates_1x["A2_CARRY_BTC_ETH_2X"])
    ov_days_comp, comp_ov = align_24_7_returns_to_trading_days(ext_days, candidates_1x["A2_COMPOSITE_SPOT50_CARRY50"])
    # Use the exact 2020-2024 common business-day index for all combination apples-to-apples comparisons
    common_td_set = set(ov_days_2020) & set(ov_days_carry) & set(ov_days_comp)
    common_td = sorted(common_td_set)
    validate_strict_pre_holdout_dates(common_td, context="study.combination_overlap_days")

    td_idx_in_ext = np.array([ext_days.index(d) for d in common_td], dtype=np.intp)
    stages_10k_ov = tuple(arr[td_idx_in_ext] for arr in stages_10k_full)

    spot_map_ov = dict(zip(ov_days_2020, spot4h_ov, strict=True))
    carry_map_ov = dict(zip(ov_days_carry, carry_ov, strict=True))
    comp_map_ov = dict(zip(ov_days_comp, comp_ov, strict=True))

    r_p7e_ov = np.array([p7e_daily_ret_map[d] for d in common_td], dtype=np.float64)
    r_spot_ov = np.array([spot_map_ov[d] for d in common_td], dtype=np.float64)
    r_carry_ov = np.array([carry_map_ov[d] for d in common_td], dtype=np.float64)
    r_comp_ov = np.array([comp_map_ov[d] for d in common_td], dtype=np.float64)

    # Full 2018-2024 baseline PORT_7E MC (verifies exact ~66% starved Funded months from C10 report!)
    idx_full = make_block_bootstrap_indices(len(ext_days), horizon=756, n_paths=n_mc_paths, seed=seed)
    mc_p7e_full = _run_ftmo_10k_c10_mc(stages_10k_full, idx_full)

    # Exact 2020-2024 apples-to-apples MC index matrix shared across all combination architectures
    idx_ov = make_block_bootstrap_indices(len(common_td), horizon=756, n_paths=n_mc_paths, seed=seed)
    mc_p7e_ov = _run_ftmo_10k_c10_mc(stages_10k_ov, idx_ov)

    # Vol-calibrated overlay scales (pre-registered: target <= 1.0x PORT_7E vol so DD stays controlled!)
    combo_specs = [
        (
            "BASE_PORT_7E_ONLY_2020_2024",
            "Incumbent PORT_7E (C10_NEWS_ON) alone on 2020-2024 overlap",
            r_p7e_ov,
            stages_10k_ov,
            "FTMO_ONLY",
        ),
        (
            "COMBO_7E_PLUS_SPOT4H_0P75X",
            "PORT_7E + 0.75x Alpha #2 Spot 4H F4 (orthogonal trend overlay, conservative 1.5x DD coupling)",
            r_p7e_ov + 0.75 * r_spot_ov,
            _blend_stage_with_alpha2(
                stages_10k_ov, r_spot_ov, p7e_weight=1.0, a2_risk_scale_funded=0.75, a2_risk_scale_eval=0.75
            ),
            "HYPOTHETICAL_COMBINED_SLEEVE_OR_DUAL_ACCOUNT",
        ),
        (
            "COMBO_7E_PLUS_CARRY2X_1P0X",
            "PORT_7E (FTMO) + 1.0x Alpha #2 Carry BTC+ETH 2x (CEX Own-Book dual-engine cashflow)",
            r_p7e_ov + 1.00 * r_carry_ov,
            _blend_stage_with_alpha2(
                stages_10k_ov, r_carry_ov, p7e_weight=1.0, a2_risk_scale_funded=1.00, a2_risk_scale_eval=1.00
            ),
            "DUAL_ACCOUNT_FTMO_PLUS_CEX_OWNBOOK",
        ),
        (
            "COMBO_7E_PLUS_COMPOSITE_1P0X",
            "PORT_7E + 1.0x Alpha #2 Composite (50% Spot 4H F4 + 50% Carry BTC+ETH 2x)",
            r_p7e_ov + 1.00 * r_comp_ov,
            _blend_stage_with_alpha2(
                stages_10k_ov, r_comp_ov, p7e_weight=1.0, a2_risk_scale_funded=1.00, a2_risk_scale_eval=1.00
            ),
            "DUAL_ACCOUNT_FTMO_PLUS_CEX_OWNBOOK",
        ),
        (
            "COMBO_7E_PLUS_SPOT_AND_CARRY_DUAL",
            "PORT_7E (1.0x) + Spot 4H F4 (0.75x) + Carry BTC+ETH 2x (1.0x) dual-sleeve cashflow",
            r_p7e_ov + 0.75 * r_spot_ov + 1.00 * r_carry_ov,
            _blend_stage_with_alpha2(
                stages_10k_ov,
                0.75 * r_spot_ov + 1.00 * r_carry_ov,
                p7e_weight=1.0,
                a2_risk_scale_funded=1.00,
                a2_risk_scale_eval=1.00,
            ),
            "DUAL_ACCOUNT_FTMO_PLUS_CEX_OWNBOOK",
        ),
    ]

    combinations: dict[str, Any] = {}
    for cid, desc, comb_daily_ret, comb_stages, exec_venue in combo_specs:
        mc_res = mc_p7e_ov if cid == "BASE_PORT_7E_ONLY_2020_2024" else _run_ftmo_10k_c10_mc(comb_stages, idx_ov)
        emp_m = compute_empirical_monthly_starvation(common_td, comb_daily_ret, min_month_return_frac=0.005)
        bal_m = compute_balanced_series_metrics(comb_daily_ret, ann_days=252.0)
        combinations[cid] = {
            "description": desc,
            "execution_venue_note": exec_venue,
            "balanced_metrics_252d": bal_m,
            "empirical_monthly_starvation": emp_m,
            "ftmo_10k_c10_mc": {
                "funded_dry_months_pct": mc_res["funded_dry_months_pct"],
                "funded_dry_streak_p50_months": mc_res["funded_dry_streak_p50_months"],
                "funded_dry_streak_p95_months": mc_res["funded_dry_streak_p95_months"],
                "monthly_pass_fail_pending": mc_res["monthly_pass_fail_pending"],
                "ev_npv_24m_usd": mc_res["ev_npv_24m_usd"],
                "ev_npv_24m_vnd_tr": mc_res["ev_npv_24m_vnd_tr"],
                "med_npv_24m_usd": mc_res["med_npv_24m_usd"],
                "med_npv_24m_vnd_tr": mc_res["med_npv_24m_vnd_tr"],
                "ev_per_fee_npv24": mc_res["ev_per_fee_npv24"],
                "p_net_le_0_24m_pct": mc_res["p_net_le_0_24m_pct"],
                "cond_med_pay1_cal_days": mc_res["cond_med_pay1_cal_days"],
                "uncond_med_pay1_cap730_days": mc_res["uncond_med_pay1_cap730_days"],
                "funded_12m_breach": mc_res["funded_12m_breach"],
                "firm_hard_breach_pct": mc_res["firm_hard_breach_pct"],
            },
        }

    # 7. Physically executable Dual-Account HWM Cashflow MC (`FTMO 10K Funded` + `Separate CEX Own-Book`)
    n_fn_ov, d_fn_ov = stages_10k_ov[16], stages_10k_ov[17]
    n_amb_ov, d_amb_ov = stages_10k_ov[20], stages_10k_ov[21]
    n_red_ov, d_red_ov = stages_10k_ov[24], stages_10k_ov[25]
    dual_kwargs: dict[str, Any] = {
        "n_amb": n_amb_ov,
        "d_amb": d_amb_ov,
        "n_red": n_red_ov,
        "d_red": d_red_ov,
        "amber_dd": float(c10_cfg["amber_dd"]),
        "red_dd": float(c10_cfg["red_dd"]),
        "ftmo_cap_usd": 10_000.0,
        "min_payout_usd": 50.0,
    }
    dual_account_cashflow = {
        "DUAL_10K_FTMO_PLUS_10K_CEX_CARRY": evaluate_dual_account_cashflow(
            idx_ov, n_fn_ov, d_fn_ov, r_carry_ov, cex_cap_usd=10_000.0, **dual_kwargs
        ),
        "DUAL_10K_FTMO_PLUS_10K_CEX_SPOT4H": evaluate_dual_account_cashflow(
            idx_ov, n_fn_ov, d_fn_ov, r_spot_ov, cex_cap_usd=10_000.0, **dual_kwargs
        ),
        "DUAL_10K_FTMO_PLUS_10K_CEX_COMPOSITE": evaluate_dual_account_cashflow(
            idx_ov, n_fn_ov, d_fn_ov, r_comp_ov, cex_cap_usd=10_000.0, **dual_kwargs
        ),
        "DUAL_10K_FTMO_PLUS_20K_CEX_COMPOSITE": evaluate_dual_account_cashflow(
            idx_ov, n_fn_ov, d_fn_ov, r_comp_ov, cex_cap_usd=20_000.0, **dual_kwargs
        ),
    }

    # Pick primary Alpha #2 by strict anti-overfit gates: within-family DSR >= 0.50, 2x Sharpe > 0.5, |r| < 0.15
    eligible_a2 = [
        sid
        for sid in cand_order
        if cand_results[sid]["dsr_empirical_within_family"] >= 0.50
        and cand_results[sid]["metrics_2x"]["sharpe"] > 0.50
        and cand_results[sid]["abs_corr_vs_port7e"] < 0.15
        and cand_results[sid]["cpcv"]["median_oos_sharpe"] > 0.50
    ]

    def _is_zero_margin_warn(sid: str) -> bool:
        ms = cand_results[sid].get("margin_stress")
        if ms is None:
            return True
        return (
            int(ms["margin_warn_days"]) == 0
            and int(ms["isolated_liq_events"]) == 0
            and int(ms["cross_liq_events"]) == 0
        )

    # Strictly prefer 0-warning, 0-liquidation conservative candidates (`A2_CARRY_BTC_ETH_2X` over altcoin warn)
    zero_warn_eligible = [sid for sid in eligible_a2 if _is_zero_margin_warn(sid)]
    primary_pool = zero_warn_eligible if zero_warn_eligible else eligible_a2
    primary_a2 = (
        max(primary_pool, key=lambda s: cand_results[s]["metrics_2x"]["calmar"])
        if primary_pool
        else max(cand_order, key=lambda s: cand_results[s]["metrics_1x"]["sharpe"])
    )

    elapsed = round(time.perf_counter() - t0, 2)
    return {
        "schema": "naqex-portfolio-7e-plus-alpha2-study-v1",
        "generated_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "evidence_stage": "DEV_BACKTEST_LE_2024_12_31_DAILY_APPROX_NOT_HOLDOUT_NOT_LIVE",
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": 0,
        "order_send_capable": ORDER_SEND_CAPABLE,
        "order_send_count": ORDER_SEND_COUNT,
        "elapsed_sec": elapsed,
        "m_total_candidates": m_total,
        "primary_alpha2_selected": primary_a2,
        "eligible_alpha2_candidates": eligible_a2,
        "data_windows": {
            "port7e_full": f"{ext_days[0]}..{ext_days[-1]} ({len(ext_days)} days)",
            "spot_4h_50coins": f"{panel_4h['dates'][0]}..{panel_4h['dates'][-1]} ({len(panel_4h['symbols'])} syms)",
            "spot_1h_40coins": f"{panel_1h['dates'][0]}..{panel_1h['dates'][-1]} ({len(panel_1h['symbols'])} syms)",
            "funding_20perps": (
                f"{panel_fund['dates'][0]}..{panel_fund['dates'][-1]} ({len(panel_fund['symbols'])} syms)"
            ),
            "common_pbo_cpcv_window": f"{common_days[0]}..{common_days[-1]} ({len(common_days)} days)",
            "combination_overlap_window": f"{common_td[0]}..{common_td[-1]} ({len(common_td)} trading days)",
        },
        "port7e_baseline_100k_1x": p7e_bal_100k,
        "port7e_full_2018_2024_mc": {
            "funded_dry_months_pct": mc_p7e_full["funded_dry_months_pct"],
            "funded_dry_streak_p50_months": mc_p7e_full["funded_dry_streak_p50_months"],
            "funded_dry_streak_p95_months": mc_p7e_full["funded_dry_streak_p95_months"],
            "monthly_pass_fail_pending": mc_p7e_full["monthly_pass_fail_pending"],
            "ev_per_fee_npv24": mc_p7e_full["ev_per_fee_npv24"],
            "ev_npv_24m_vnd_tr": mc_p7e_full["ev_npv_24m_vnd_tr"],
            "p_net_le_0_24m_pct": mc_p7e_full["p_net_le_0_24m_pct"],
            "funded_12m_breach": mc_p7e_full["funded_12m_breach"],
        },
        "anti_overfit_portfolio_suite": {
            "pbo_cscv": {
                "pbo": round(pbo_res.pbo, 4),
                "is_overfit": pbo_res.is_overfit,
                "n_slices": pbo_res.n_slices,
                "n_combinations": pbo_res.n_combinations,
                "n_trials": pbo_res.n_trials,
                "prob_oos_nonpositive_sr": round(pbo_res.prob_oos_nonpositive_sr, 4),
            },
            "cpcv": cpcv_res,
        },
        "alpha2_candidates": cand_results,
        "portfolio_combinations": combinations,
        "dual_account_cashflow_mc": dual_account_cashflow,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Alpha #2 Unified Engine + PORT_7E Combination Study (Dev <= 2024)")
    ap.add_argument("--mc-paths", type=int, default=5_000)
    ap.add_argument("--seed", type=int, default=DEFAULT_SEED)
    ap.add_argument("--out-json", type=str, default="")
    args = ap.parse_args(argv)

    res = run_portfolio_7e_plus_alpha2_study(n_mc_paths=args.mc_paths, seed=args.seed)
    if args.out_json:
        out_p = Path(args.out_json)
        out_p.parent.mkdir(parents=True, exist_ok=True)
        out_p.write_text(json.dumps(res, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps(res, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
