"""C0.3b — Live Public Binance Spot + USD-M Perp Shadow Collector & Paper TCA Runner.

STRICT SAFETY BOUNDARIES:
  - OrderSend = 0, ZERO API keys, ZERO authenticated endpoints!
  - Uses ONLY public Binance Spot (/api/v3/*) and USD-M Futures (/fapi/v1/*) read-only endpoints.
  - Signal calculation uses STRICTLY CLOSED 4H/D1 bars (drops currently open forming candle)
    and delegates directly to canonical `quant_lab.unified_engine` & `quant_lab.funding_carry_v2`
    so live Shadow matches offline Backtest bit-for-bit:
      1. Exact EMA warmup parity (`valid_streak >= span`, resetting on NaN/non-positive closes).
      2. Exact rebalance deadband parity (`0.015`, matching `causal_universe.py`).
      3. `SHADOW_4H_KLINE_LIMIT = 1000` (>= 600) eliminating ~11.5% EMA(300) initialization drift.
      4. Strict 4H bar idempotency lock keyed on `last_4h_close_ms` (zero repeat fees on 5m polls).
      5. Full exited-coin MTM tracking: fetches live `mid` & L2 depth for
         `top15 | {BTCUSDT, ETHUSDT} | set(s2_prev_w.keys())`.
  - Outputs:
      - `.runtime/live-overnight/crypto_shadow_log.jsonl` (append-only JSONL telemetry)
      - `.runtime/live-overnight/crypto_shadow_latest.json` (atomic latest snapshot for Cockpit UI)
      - `.runtime/live-overnight/crypto_shadow_state.json` (persistent paper position & TCA state)
"""

from __future__ import annotations

import argparse
import json
import math
import sys
import time
from collections.abc import Mapping, Sequence
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
QUANT_LAB_SRC = ROOT / "projects" / "quant-trading" / "src"
for _p in (str(AI_ENGINES), str(QUANT_LAB_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

try:
    from quant_lab.funding_carry_v2 import compute_carry_btc_eth_live_step  # noqa: E402
    from quant_lab.unified_engine import (  # noqa: E402
        DEFAULT_SHADOW_4H_KLINE_LIMIT,
        F4EmaConfig,
        apply_deadband_step,
        causal_ema_1d,
        compute_f4_ema_step,
        update_shadow_spot_accounting,
    )
except ModuleNotFoundError:  # Fallback when projects/quant-trading submodule pin predates unified_engine.py
    DEFAULT_SHADOW_4H_KLINE_LIMIT = 1000

    @dataclass(frozen=True, slots=True)
    class F4EmaConfig:  # type: ignore[no-redef]
        btc_symbol: str = "BTCUSDT"
        fast_span: int = 24
        slow_span: int = 120
        btc_fast: int = 60
        btc_slow: int = 300
        vol_window: int = 120
        target_ann_vol: float = 0.15
        bars_per_year: float = 365.0 * 6.0
        deadband: float = 0.015
        min_recommended_history_bars: int = 600

    def causal_ema_1d(values: np.ndarray, span: int) -> np.ndarray:  # type: ignore[no-redef]
        arr = np.asarray(values, dtype=np.float64)
        out = np.full(arr.shape[0], np.nan, dtype=np.float64)
        alpha = 2.0 / (span + 1.0)
        prev = np.nan
        valid_streak = 0
        for t in range(arr.shape[0]):
            c = float(arr[t])
            if not math.isfinite(c) or c <= 0.0:
                prev = np.nan
                valid_streak = 0
                continue
            prev = c if not math.isfinite(prev) else (alpha * c + (1.0 - alpha) * prev)
            valid_streak += 1
            if valid_streak >= span:
                out[t] = prev
        return out

    def _fb_rolling_vol_1d(values: np.ndarray, window: int) -> np.ndarray:
        arr = np.asarray(values, dtype=np.float64)
        n_t = arr.shape[0]
        out = np.full(n_t, np.nan, dtype=np.float64)
        if n_t <= window:
            return out
        rets = np.full(n_t, np.nan, dtype=np.float64)
        valid = np.isfinite(arr[1:]) & np.isfinite(arr[:-1]) & (arr[:-1] > 0.0) & (arr[1:] > 0.0)
        rets[1:][valid] = arr[1:][valid] / arr[:-1][valid] - 1.0
        for t in range(window, n_t):
            win = rets[t - window + 1 : t + 1]
            if np.all(np.isfinite(win)):
                out[t] = float(np.std(win, ddof=1))
        return out

    def apply_deadband_step(  # type: ignore[no-redef]
        raw_weights: Mapping[str, float],
        prev_weights: Mapping[str, float] | None = None,
        *,
        deadband: float = 0.015,
    ) -> dict[str, float]:
        cleaned_raw = {str(k): float(v) for k, v in raw_weights.items() if float(v) > 0.0}
        raw_total = sum(cleaned_raw.values())
        if raw_total > 1.0:
            cleaned_raw = {k: v / raw_total for k, v in cleaned_raw.items()}
        if prev_weights is None or float(deadband) == 0.0:
            return dict(sorted(cleaned_raw.items()))
        cleaned_prev = {str(k): float(v) for k, v in prev_weights.items() if float(v) > 0.0}
        db = float(deadband)
        updated: dict[str, float] = {}
        for sym in sorted(set(cleaned_raw) | set(cleaned_prev)):
            cur = cleaned_raw.get(sym, 0.0)
            prv = cleaned_prev.get(sym, 0.0)
            flip = (cur == 0.0) != (prv == 0.0)
            new_w = cur if (flip or abs(cur - prv) >= db) else prv
            if new_w > 0.0:
                updated[sym] = new_w
        tot = sum(updated.values())
        if tot > 1.0:
            updated = {k: v / tot for k, v in updated.items()}
        return updated

    def compute_f4_ema_step(  # type: ignore[no-redef]
        closed_closes: Mapping[str, np.ndarray | Sequence[float]],
        eligible_symbols: Sequence[str],
        *,
        config: F4EmaConfig | None = None,
        prev_weights: Mapping[str, float] | None = None,
        round_digits: int | None = None,
    ) -> dict[str, Any]:
        cfg = config or F4EmaConfig()
        btc_raw = closed_closes.get(cfg.btc_symbol)
        if btc_raw is None:
            return {
                "btc_regime_bull": False,
                "btc_ema60": None,
                "btc_ema300": None,
                "btc_history_bars": 0,
                "ema300_drift_warning": True,
                "active_count": 0,
                "gross_exposure": 0.0,
                "weights": {},
                "raw_weights": {},
                "diagnostics": {},
                "reason": "INSUFFICIENT_BTC_BARS",
            }
        btc_arr = np.asarray(btc_raw, dtype=np.float64)
        btc_bars = int(btc_arr.shape[0]) if btc_arr.ndim == 1 else 0
        btc_ef = float(causal_ema_1d(btc_arr, cfg.btc_fast)[-1]) if btc_bars > 0 else float("nan")
        btc_es = float(causal_ema_1d(btc_arr, cfg.btc_slow)[-1]) if btc_bars > 0 else float("nan")
        if not math.isfinite(btc_ef) or not math.isfinite(btc_es):
            return {
                "btc_regime_bull": False,
                "btc_ema60": round(btc_ef, 2) if math.isfinite(btc_ef) else None,
                "btc_ema300": round(btc_es, 2) if math.isfinite(btc_es) else None,
                "btc_history_bars": btc_bars,
                "ema300_drift_warning": btc_bars < cfg.min_recommended_history_bars,
                "active_count": 0,
                "gross_exposure": 0.0,
                "weights": {},
                "raw_weights": {},
                "diagnostics": {},
                "reason": "INSUFFICIENT_BTC_BARS",
            }
        btc_bull = bool(btc_ef > btc_es)
        vt_bar = cfg.target_ann_vol / math.sqrt(cfg.bars_per_year)
        elig_unique = list(dict.fromkeys(str(s) for s in eligible_symbols))
        n_elig = max(1, len(elig_unique))
        raw: dict[str, float] = {}
        diagnostics: dict[str, dict[str, Any]] = {}
        for sym in elig_unique:
            s_raw = closed_closes.get(sym)
            if s_raw is None:
                continue
            c = np.asarray(s_raw, dtype=np.float64)
            if c.ndim != 1 or c.size == 0:
                continue
            ef_val = float(causal_ema_1d(c, cfg.fast_span)[-1])
            es_val = float(causal_ema_1d(c, cfg.slow_span)[-1])
            vol_val = float(_fb_rolling_vol_1d(c, cfg.vol_window)[-1])
            last_c = float(c[-1])
            sig_on = bool(
                btc_bull
                and math.isfinite(last_c)
                and last_c > 0.0
                and math.isfinite(ef_val)
                and math.isfinite(es_val)
                and (ef_val > es_val)
                and math.isfinite(vol_val)
                and (vol_val > 1e-6)
            )
            w_val = (vt_bar / vol_val) / float(n_elig) if sig_on else 0.0
            if w_val > 0.0:
                raw[sym] = w_val
            diagnostics[sym] = {
                "last_closed_4h": round(last_c, 6) if math.isfinite(last_c) else None,
                "ema24": round(ef_val, 6) if math.isfinite(ef_val) else None,
                "ema120": round(es_val, 6) if math.isfinite(es_val) else None,
                "vol120_ann_pct": (
                    round(vol_val * math.sqrt(cfg.bars_per_year) * 100.0, 2) if math.isfinite(vol_val) else None
                ),
                "signal_long": sig_on,
            }
        tot_raw = sum(raw.values())
        capped_raw = {k: v / tot_raw for k, v in raw.items()} if tot_raw > 1.0 else dict(raw)
        weights = apply_deadband_step(capped_raw, prev_weights, deadband=cfg.deadband)
        if round_digits is not None:
            weights = {k: round(v, round_digits) for k, v in weights.items() if round(v, round_digits) > 0.0}
            tot_r = sum(weights.values())
            if tot_r > 1.0:
                weights = {k: round(v / tot_r, round_digits) for k, v in weights.items()}
        gross_exp = sum(weights.values())
        return {
            "btc_regime_bull": btc_bull,
            "btc_ema60": round(btc_ef, 2),
            "btc_ema300": round(btc_es, 2),
            "btc_history_bars": btc_bars,
            "ema300_drift_warning": btc_bars < cfg.min_recommended_history_bars,
            "active_count": len(weights),
            "gross_exposure": round(gross_exp, 6) if round_digits is not None else gross_exp,
            "weights": weights,
            "raw_weights": capped_raw,
            "diagnostics": diagnostics,
        }

    def _fb_pos_price(val: Any) -> float | None:
        if val is None or isinstance(val, bool):
            return None
        try:
            p = float(val)
        except (TypeError, ValueError):
            return None
        return p if (math.isfinite(p) and p > 0.0) else None

    def _fb_nonneg_slip(val: Any, fallback: float) -> float:
        if val is None or isinstance(val, bool):
            return fallback
        try:
            p = float(val)
        except (TypeError, ValueError):
            return fallback
        return p if (math.isfinite(p) and p >= 0.0) else fallback

    def update_shadow_spot_accounting(  # type: ignore[no-redef]
        *,
        prev_weights: Mapping[str, float],
        prev_mids: Mapping[str, float],
        prev_equity_usd: float,
        prev_bar_close_ms: int | None,
        current_bar_close_ms: int,
        candidate_weights: Mapping[str, float],
        depth_metrics: Mapping[str, Mapping[str, Any]],
        taker_fee_bps: float = 10.0,
        fallback_slip_bps: float = 5.0,
    ) -> dict[str, Any]:
        if isinstance(current_bar_close_ms, bool) or int(current_bar_close_ms) <= 0:
            raise ValueError("current_bar_close_ms must be a positive int.")
        cur_ms = int(current_bar_close_ms)
        prev_ms = None if prev_bar_close_ms is None else int(prev_bar_close_ms)
        clean_prev = {str(k): float(v) for k, v in prev_weights.items() if float(v) > 0.0}
        clean_cand = {str(k): float(v) for k, v in candidate_weights.items() if float(v) > 0.0}
        cand_sum = sum(clean_cand.values())
        if cand_sum > 1.0 + 1e-6:
            raise ValueError("Spot candidate_weights sum exceeds 1.0.")
        if cand_sum > 1.0:
            clean_cand = {k: v / cand_sum for k, v in clean_cand.items()}
        mtm_ret = 0.0
        missing_exit_mids: list[str] = []
        for sym, w in sorted(clean_prev.items()):
            p0 = _fb_pos_price(prev_mids.get(sym))
            p1 = _fb_pos_price(depth_metrics.get(sym, {}).get("mid"))
            if p0 is not None and p1 is not None:
                mtm_ret += w * (p1 / p0 - 1.0)
            else:
                missing_exit_mids.append(sym)
        is_new_bar = (prev_ms is None) or (cur_ms > prev_ms)
        if is_new_bar:
            active_weights = clean_cand
            all_keys = sorted(set(clean_prev) | set(active_weights))
            turnover = sum(abs(active_weights.get(k, 0.0) - clean_prev.get(k, 0.0)) for k in all_keys)
            live_tca_bps = 0.0
            if turnover > 1e-9:
                w_slip = 0.0
                for k in all_keys:
                    dw = abs(active_weights.get(k, 0.0) - clean_prev.get(k, 0.0))
                    if dw > 1e-9:
                        slip_k = _fb_nonneg_slip(depth_metrics.get(k, {}).get("slip_10k_bps"), float(fallback_slip_bps))
                        w_slip += dw * (float(taker_fee_bps) + slip_k)
                live_tca_bps = w_slip / turnover
            cost_ret = turnover * (live_tca_bps / 10_000.0)
            locked_ms = cur_ms
        else:
            active_weights = clean_prev
            turnover = 0.0
            live_tca_bps = 0.0
            cost_ret = 0.0
            locked_ms = prev_ms  # type: ignore[assignment]
        return {
            "weights": active_weights,
            "equity_usd": max(0.0, float(prev_equity_usd) * (1.0 + mtm_ret - cost_ret)),
            "mtm_return": mtm_ret,
            "turnover": turnover,
            "live_tca_bps": live_tca_bps,
            "cost_return": cost_ret,
            "bar_rebalanced": is_new_bar,
            "last_4h_close_ms": locked_ms,
            "missing_exit_mids": missing_exit_mids,
        }

    def compute_carry_btc_eth_live_step(  # type: ignore[no-redef]
        funding_hist_8h: Mapping[str, Sequence[float]],
        prev_state: Mapping[str, bool] | None = None,
        *,
        symbols: tuple[str, str] = ("BTCUSDT", "ETHUSDT"),
        equity_buffer_mult: float = 2.0,
        enter_ann: float = 0.03,
        exit_ann: float = 0.0,
        min_settlements: int = 18,
        window_settlements: int = 21,
    ) -> dict[str, Any]:
        prev = dict(prev_state or {sym: False for sym in symbols})
        notional_cap = 1.0 / float(equity_buffer_mult)
        per_coin_eq_w = notional_cap / float(max(1, len(symbols)))
        new_state: dict[str, bool] = {}
        notional_w: dict[str, float] = {}
        stats: dict[str, dict[str, Any]] = {}
        for sym in symbols:
            clean_rates = [float(x) for x in funding_hist_8h.get(sym, ()) if math.isfinite(float(x))]
            if len(clean_rates) < min_settlements:
                new_state[sym] = False
                stats[sym] = {"n_settlements": len(clean_rates), "trail_7d_ann_pct": None, "active": False}
                continue
            w_tail = clean_rates[-window_settlements:]
            ann_7d = float(np.mean(w_tail)) * 3.0 * 365.0
            was_on = bool(prev.get(sym, False))
            is_on = (ann_7d > exit_ann) if was_on else (ann_7d >= enter_ann)
            new_state[sym] = is_on
            if is_on:
                notional_w[sym] = round(per_coin_eq_w, 6)
            stats[sym] = {
                "n_settlements": len(w_tail),
                "last_8h_bps": round(float(w_tail[-1]) * 10_000.0, 3),
                "trail_7d_ann_pct": round(ann_7d * 100.0, 2),
                "active": is_on,
            }
        return {
            "equity_buffer_mult": float(equity_buffer_mult),
            "state": new_state,
            "notional_weights_of_equity": notional_w,
            "gross_carry_notional_pct": round(sum(notional_w.values()) * 100.0, 1),
            "per_coin": stats,
        }

from quant_factory.crypto_causal_universe import (  # noqa: E402
    BINANCE_SPOT_BASE,
    UNIVERSE_50_SYMBOLS,
)
from quant_factory.funding_rate_carry import BINANCE_FAPI_BASE  # noqa: E402

DEFAULT_LIVE_DIR = ROOT / ".runtime" / "live-overnight"
DEFAULT_LOG_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_log.jsonl"
DEFAULT_LATEST_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_latest.json"
DEFAULT_STATE_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_state.json"

SHADOW_4H_KLINE_LIMIT: int = DEFAULT_SHADOW_4H_KLINE_LIMIT  # 1000 (>= 600) for EMA(300) warmup parity


# ==============================================================================
# ORDERBOOK DEPTH SLIPPAGE MODEL (PURE, DETERMINISTIC, UNIT-TESTABLE)
# ==============================================================================


def compute_orderbook_slippage_bps(
    bids: list[list[str | float]],
    asks: list[list[str | float]],
    notional_usd: float,
) -> dict[str, Any]:
    """Compute exact L2 VWAP execution slippage (bps vs mid) for a market buy & sell of `notional_usd`."""
    if not bids or not asks:
        return {
            "spread_bps": float("nan"),
            "buy_slip_bps": float("nan"),
            "sell_slip_bps": float("nan"),
            "depth_ok": 0.0,
        }
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    if best_bid <= 0 or best_ask <= 0 or best_ask < best_bid:
        return {
            "spread_bps": float("nan"),
            "buy_slip_bps": float("nan"),
            "sell_slip_bps": float("nan"),
            "depth_ok": 0.0,
        }
    mid = 0.5 * (best_bid + best_ask)
    spread_bps = (best_ask - best_bid) / mid * 10_000.0

    def _walk(levels: list[list[str | float]], target_usd: float) -> tuple[float, bool]:
        rem = float(target_usd)
        spent_usd = 0.0
        qty_filled = 0.0
        for px_raw, qty_raw in levels:
            px = float(px_raw)
            qty = float(qty_raw)
            if px <= 0 or qty <= 0:
                continue
            lvl_usd = px * qty
            if lvl_usd >= rem:
                q_take = rem / px
                spent_usd += rem
                qty_filled += q_take
                rem = 0.0
                break
            spent_usd += lvl_usd
            qty_filled += qty
            rem -= lvl_usd
        if qty_filled <= 0:
            return float("nan"), False
        vwap = spent_usd / qty_filled
        return vwap, (rem <= 1e-6)

    buy_vwap, buy_ok = _walk(asks, notional_usd)
    sell_vwap, sell_ok = _walk(bids, notional_usd)
    buy_slip = ((buy_vwap - mid) / mid * 10_000.0) if math.isfinite(buy_vwap) else float("nan")
    sell_slip = ((mid - sell_vwap) / mid * 10_000.0) if math.isfinite(sell_vwap) else float("nan")
    avg_oneway = (
        round(0.5 * (buy_slip + sell_slip), 3) if (math.isfinite(buy_slip) and math.isfinite(sell_slip)) else None
    )
    return {
        "best_bid": round(best_bid, 8),
        "best_ask": round(best_ask, 8),
        "mid": round(mid, 8),
        "spread_bps": round(spread_bps, 3),
        "buy_slip_bps": round(buy_slip, 3) if math.isfinite(buy_slip) else None,
        "sell_slip_bps": round(sell_slip, 3) if math.isfinite(sell_slip) else None,
        "avg_oneway_slip_bps": avg_oneway,
        "depth_ok": bool(buy_ok and sell_ok),
    }


def _causal_ema_1d(arr: np.ndarray, span: int) -> np.ndarray:
    """Delegate strictly to `quant_lab.unified_engine.causal_ema_1d` (`valid_streak >= span` parity)."""
    return causal_ema_1d(arr, span)


def build_shadow_watch_symbols(
    top15_symbols: Sequence[str],
    prev_weights: Mapping[str, float] | None = None,
) -> list[str]:
    """Return sorted watch universe: `top15 | {BTCUSDT, ETHUSDT} | set(prev_weights.keys())`.

    Guarantees coins that drop out of Top-15 still have live `mid` and L2 slippage fetched so
    their exit mark-to-market return and exit TCA are accounted accurately (never `p1 = 0.0`).
    """
    held_keys = set(prev_weights.keys()) if prev_weights else set()
    return sorted(set(top15_symbols) | {"BTCUSDT", "ETHUSDT"} | held_keys)


def compute_f4_4h_ema_live_weights(
    closed_4h_closes: Mapping[str, np.ndarray],
    top15_symbols: Sequence[str],
    *,
    prev_weights: Mapping[str, float] | None = None,
    deadband: float = 0.015,
    round_digits: int | None = None,
) -> dict[str, Any]:
    """Compute exact live causal `F4_4H_EMA_24_120_BTC` weights via canonical `quant_lab.unified_engine`."""
    cfg = F4EmaConfig(deadband=deadband)
    return compute_f4_ema_step(
        closed_4h_closes,
        top15_symbols,
        config=cfg,
        prev_weights=prev_weights,
        round_digits=round_digits,
    )


def compute_carry_btc_eth_live_weights(
    funding_hist_8h: Mapping[str, Sequence[float]],
    prev_state: Mapping[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute exact live causal `CARRY_BTC_ETH_CONS_2XBUF` weights via canonical `quant_lab.funding_carry_v2`."""
    return compute_carry_btc_eth_live_step(funding_hist_8h, prev_state=prev_state)


# ==============================================================================
# LIVE PUBLIC BINANCE COLLECTOR (ZERO API KEY, ZERO ORDERSEND)
# ==============================================================================


def _fetch_json(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> Any:
    for attempt in range(3):
        r = client.get(url, params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503):
            time.sleep(0.4 * (attempt + 1))
            continue
        raise RuntimeError(f"HTTP {r.status_code} for {url}: {r.text[:120]}")
    raise RuntimeError(f"Retries exhausted for {url}")


def select_live_top15_causal(client: httpx.Client, universe: tuple[str, ...] = UNIVERSE_50_SYMBOLS) -> list[str]:
    """Rank universe by live 30-day closed D1 quote_volume (fallback: 24h ticker quoteVolume if D1 throttled)."""
    tickers = _fetch_json(client, f"{BINANCE_SPOT_BASE}/api/v3/ticker/24hr")
    qv_24h = {t["symbol"]: float(t.get("quoteVolume", 0.0)) for t in tickers if t.get("symbol") in universe}
    # Pre-filter top 22 by 24h liquidity, then refine exact 30-day closed D1 dollar volume!
    shortlist = sorted(qv_24h.keys(), key=lambda s: qv_24h[s], reverse=True)[:22]
    vol30: dict[str, float] = {}

    def _d1_qv(sym: str) -> tuple[str, float]:
        with httpx.Client(timeout=10.0, headers={"User-Agent": "NaqexShadowRunner/1.0"}) as c2:
            rows = _fetch_json(
                c2,
                f"{BINANCE_SPOT_BASE}/api/v3/klines",
                {"symbol": sym, "interval": "1d", "limit": 32},
            )
            # Drop currently forming today bar (rows[:-1]) -> strictly closed last 30 UTC days!
            closed = rows[:-1][-30:] if len(rows) > 1 else rows
            if len(closed) < 25:
                return sym, 0.0
            return sym, float(np.mean([float(r[7]) for r in closed]))

    with ThreadPoolExecutor(max_workers=8) as pool:
        for fut in as_completed([pool.submit(_d1_qv, s) for s in shortlist]):
            s, v = fut.result()
            if v > 0:
                vol30[s] = v
    ranked = sorted(vol30.keys(), key=lambda s: (-vol30[s], s))[:15]
    if "BTCUSDT" not in ranked:
        ranked = ["BTCUSDT"] + ranked[:14]
    return ranked


def _finite_float_or_none(value: Any, *, positive_only: bool = False) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if not math.isfinite(parsed):
        return None
    if positive_only and parsed <= 0.0:
        return None
    return parsed


def collect_live_shadow_snapshot(
    *,
    state_path: Path = DEFAULT_STATE_PATH,
    log_path: Path = DEFAULT_LOG_PATH,
    latest_path: Path = DEFAULT_LATEST_PATH,
    kline_limit_4h: int = SHADOW_4H_KLINE_LIMIT,
) -> dict[str, Any]:
    """Execute one complete read-only live shadow cycle and update JSONL + latest + paper state."""
    if isinstance(kline_limit_4h, bool) or not isinstance(kline_limit_4h, int) or kline_limit_4h < 600:
        raise ValueError(
            f"kline_limit_4h must be an integer >= 600 for EMA(300) warmup parity, got {kline_limit_4h!r}."
        )

    t0 = time.perf_counter()
    now_utc = datetime.now(UTC)
    now_iso = now_utc.isoformat()

    prev_state: dict[str, Any] = {}
    if state_path.exists():
        try:
            prev_state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            prev_state = {}

    s2_prev_w: dict[str, float] = dict(prev_state.get("s2_weights", {}))
    s2_prev_mids: dict[str, float] = dict(prev_state.get("s2_mids", {}))
    s2_prev_bar_close_ms: int | None = prev_state.get("s2_last_4h_close_ms")
    s2_eq = float(prev_state.get("s2_paper_equity_usd", 10_000.0))

    with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexShadowRunner/1.0"}) as client:
        top15 = select_live_top15_causal(client)
        # Bug #5 fix: always include previously held symbols so dropped Top-15 coins get real exit MTM!
        watch_syms = build_shadow_watch_symbols(top15, s2_prev_w)

        # 1. Fetch closed 4H klines (limit >= 600, default 1000) + live L2 depth (10k/50k USD slippage)
        closed_4h: dict[str, np.ndarray] = {}
        last_4h_close_ms: dict[str, int] = {}
        depth_metrics: dict[str, dict[str, Any]] = {}

        def _fetch_coin_bundle(sym: str) -> tuple[str, np.ndarray, int, dict[str, Any]]:
            with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexShadowRunner/1.0"}) as c2:
                kl = _fetch_json(
                    c2,
                    f"{BINANCE_SPOT_BASE}/api/v3/klines",
                    {"symbol": sym, "interval": "4h", "limit": int(kline_limit_4h)},
                )
                # Drop forming unclosed bar (`kl[:-1]`)
                closed_kl = kl[:-1] if len(kl) > 1 else kl
                closes = np.array([float(r[4]) for r in closed_kl], dtype=np.float64)
                last_close_t = int(closed_kl[-1][6]) if closed_kl else 0
                ob = _fetch_json(c2, f"{BINANCE_SPOT_BASE}/api/v3/depth", {"symbol": sym, "limit": 50})
                s10k = compute_orderbook_slippage_bps(ob.get("bids", []), ob.get("asks", []), 10_000.0)
                s50k = compute_orderbook_slippage_bps(ob.get("bids", []), ob.get("asks", []), 50_000.0)
                dm = {
                    "best_bid": _finite_float_or_none(s10k.get("best_bid"), positive_only=True),
                    "best_ask": _finite_float_or_none(s10k.get("best_ask"), positive_only=True),
                    "mid": _finite_float_or_none(s10k.get("mid"), positive_only=True),
                    "spread_bps": _finite_float_or_none(s10k.get("spread_bps")),
                    "slip_10k_bps": _finite_float_or_none(s10k.get("avg_oneway_slip_bps")),
                    "slip_50k_bps": _finite_float_or_none(s50k.get("avg_oneway_slip_bps")),
                    "depth_50k_ok": bool(s50k.get("depth_ok")),
                }
                return sym, closes, last_close_t, dm

        with ThreadPoolExecutor(max_workers=8) as pool:
            futs = [pool.submit(_fetch_coin_bundle, s) for s in watch_syms]
            for fut in as_completed(futs):
                sym, closes, lct, dm = fut.result()
                closed_4h[sym] = closes
                last_4h_close_ms[sym] = lct
                depth_metrics[sym] = dm

        # 2. Fetch live USD-M Perp premiumIndex + trailing 21 x 8h funding rates for BTC & ETH
        perp_live: dict[str, Any] = {}
        funding_hist: dict[str, list[float]] = {}
        for sym in ("BTCUSDT", "ETHUSDT"):
            prem = _fetch_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/premiumIndex", {"symbol": sym})
            hist = _fetch_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate", {"symbol": sym, "limit": 24})
            funding_hist[sym] = [float(x["fundingRate"]) for x in hist]
            spot_mid = float(depth_metrics[sym]["mid"] or 0.0)
            mark_px = float(prem["markPrice"])
            basis_bps = ((mark_px - spot_mid) / spot_mid * 10_000.0) if spot_mid > 0 else 0.0
            perp_live[sym] = {
                "mark_price": round(mark_px, 4),
                "index_price": round(float(prem["indexPrice"]), 4),
                "next_funding_rate_bps": round(float(prem["lastFundingRate"]) * 10_000.0, 3),
                "next_funding_ann_pct": round(float(prem["lastFundingRate"]) * 3.0 * 365.0 * 100.0, 2),
                "spot_perp_basis_bps": round(basis_bps, 2),
            }

    # 3. Compute live causal paper target weights via canonical unified engine (with deadband parity!)
    s2_sig = compute_f4_4h_ema_live_weights(closed_4h, top15, prev_weights=s2_prev_w)
    s3a_sig = compute_carry_btc_eth_live_weights(funding_hist, prev_state.get("carry_state"))

    # 4. Update paper shadow portfolio accounting with 4H bar idempotency lock & full exited-coin MTM
    bar_close_ms = int(last_4h_close_ms.get("BTCUSDT", max(last_4h_close_ms.values(), default=0)))
    if bar_close_ms <= 0:
        raise ValueError(f"Empty or invalid closed 4H kline timestamp (last_4h_close_ms={bar_close_ms}).")
    acct = update_shadow_spot_accounting(
        prev_weights=s2_prev_w,
        prev_mids=s2_prev_mids,
        prev_equity_usd=s2_eq,
        prev_bar_close_ms=s2_prev_bar_close_ms,
        current_bar_close_ms=bar_close_ms,
        candidate_weights=s2_sig["weights"],
        depth_metrics=depth_metrics,
    )
    active_weights = acct["weights"]
    s2_eq_new = float(acct["equity_usd"])
    s2_turnover = float(acct["turnover"])
    s2_live_tca_bps = float(acct["live_tca_bps"])

    # Aggregate median/mean live L2 slippage across Top-15 (strictly finite values -> valid strict JSON)
    slips_10k = [v for s in top15 if (v := _finite_float_or_none(depth_metrics[s].get("slip_10k_bps"))) is not None]
    slips_50k = [v for s in top15 if (v := _finite_float_or_none(depth_metrics[s].get("slip_50k_bps"))) is not None]
    spreads = [v for s in top15 if (v := _finite_float_or_none(depth_metrics[s].get("spread_bps"))) is not None]

    record = {
        "schema": "naqex-crypto-shadow-telemetry-v1",
        "timestamp_utc": now_iso,
        "order_send_count": 0,
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "cycle_num": int(prev_state.get("cycle_num", 0)) + 1,
        "top15_causal_universe": top15,
        "tca_summary_top15": {
            "median_spread_bps": round(float(np.median(spreads)), 3) if spreads else None,
            "median_slip_10k_bps": round(float(np.median(slips_10k)), 3) if slips_10k else None,
            "max_slip_10k_bps": round(float(np.max(slips_10k)), 3) if slips_10k else None,
            "median_slip_50k_bps": round(float(np.median(slips_50k)), 3) if slips_50k else None,
            "max_slip_50k_bps": round(float(np.max(slips_50k)), 3) if slips_50k else None,
            "backtest_assumed_oneway_slip_bps": 5.0,
            "tca_within_budget_10k": bool(slips_10k and float(np.median(slips_10k)) <= 5.0),
        },
        "sleeve2_f4_4h_ema": {
            "btc_regime_bull": s2_sig["btc_regime_bull"],
            "btc_ema60": s2_sig["btc_ema60"],
            "btc_ema300": s2_sig["btc_ema300"],
            "active_count": len(active_weights),
            "gross_exposure": round(sum(active_weights.values()), 6),
            "weights": active_weights,
            "paper_equity_usd": round(s2_eq_new, 2),
            "cycle_turnover": round(s2_turnover, 6),
            "cycle_live_tca_bps": round(s2_live_tca_bps, 3),
            "bar_rebalanced": bool(acct["bar_rebalanced"]),
            "last_4h_close_ms": int(acct["last_4h_close_ms"]),
            "kline_limit_4h": int(kline_limit_4h),
            "missing_exit_mids": list(acct["missing_exit_mids"]),
        },
        "sleeve3a_carry_btc_eth": {
            "equity_buffer_mult": s3a_sig["equity_buffer_mult"],
            "gross_carry_notional_pct": s3a_sig["gross_carry_notional_pct"],
            "notional_weights_of_equity": s3a_sig["notional_weights_of_equity"],
            "per_coin_funding": s3a_sig["per_coin"],
            "perp_live_basis": perp_live,
        },
        "orderbook_depth_top15": {s: depth_metrics[s] for s in top15},
    }

    # Persist live finite positive mids; carry forward prior cost-basis `p0` for held coins if mid transiently absent!
    persisted_mids: dict[str, float] = {}
    for s in watch_syms:
        live_mid = _finite_float_or_none(depth_metrics[s].get("mid"), positive_only=True)
        if live_mid is not None:
            persisted_mids[s] = live_mid
        elif s in active_weights:
            prev_mid = _finite_float_or_none(s2_prev_mids.get(s), positive_only=True)
            if prev_mid is not None:
                persisted_mids[s] = prev_mid

    new_state = {
        "updated_utc": now_iso,
        "cycle_num": record["cycle_num"],
        "s2_weights": active_weights,
        "s2_last_4h_close_ms": int(acct["last_4h_close_ms"]),
        "s2_mids": persisted_mids,
        "s2_paper_equity_usd": round(s2_eq_new, 4),
        "carry_state": s3a_sig["state"],
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False, allow_nan=False) + "\n")
    latest_path.write_text(
        json.dumps(record, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    state_path.write_text(
        json.dumps(new_state, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description="C0.3b Live Public Binance Spot + Perp Shadow Collector (OrderSend=0)")
    ap.add_argument("--once", action="store_true", help="Collect one live snapshot and exit")
    ap.add_argument("--daemon", action="store_true", help="Run continuous shadow collection loop")
    ap.add_argument("--interval-sec", type=int, default=300, help="Loop interval in seconds for --daemon (default 300)")
    ap.add_argument("--max-cycles", type=int, default=0, help="Stop after N cycles (0 = unlimited)")
    args = ap.parse_args()

    if not args.daemon:
        rec = collect_live_shadow_snapshot()
        print(
            json.dumps(
                {
                    "timestamp_utc": rec["timestamp_utc"],
                    "elapsed_sec": rec["elapsed_sec"],
                    "order_send_count": rec["order_send_count"],
                    "top15": rec["top15_causal_universe"],
                    "tca_summary_top15": rec["tca_summary_top15"],
                    "sleeve2_f4_4h_ema": rec["sleeve2_f4_4h_ema"],
                    "sleeve3a_carry_btc_eth": {
                        "gross_carry_notional_pct": rec["sleeve3a_carry_btc_eth"]["gross_carry_notional_pct"],
                        "per_coin_funding": rec["sleeve3a_carry_btc_eth"]["per_coin_funding"],
                        "perp_live_basis": rec["sleeve3a_carry_btc_eth"]["perp_live_basis"],
                    },
                    "log_path": str(DEFAULT_LOG_PATH),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
        return 0

    cycles = 0
    while True:
        try:
            rec = collect_live_shadow_snapshot()
            print(
                f"[{rec['timestamp_utc']}] cycle={rec['cycle_num']} "
                f"s2_exp={rec['sleeve2_f4_4h_ema']['gross_exposure']:.3f} "
                f"rebal={rec['sleeve2_f4_4h_ema']['bar_rebalanced']} "
                f"s3a_exp={rec['sleeve3a_carry_btc_eth']['gross_carry_notional_pct']}% "
                f"med_10k_slip={rec['tca_summary_top15']['median_slip_10k_bps']}bps",
                flush=True,
            )
        except Exception as exc:
            err_rec = {
                "timestamp_utc": datetime.now(UTC).isoformat(),
                "status": "ERROR",
                "error": f"{type(exc).__name__}:{exc}",
            }
            DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with DEFAULT_LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(err_rec) + "\n")
            print(f"ERROR: {err_rec}", flush=True)
        cycles += 1
        if args.max_cycles > 0 and cycles >= args.max_cycles:
            break
        time.sleep(max(10, int(args.interval_sec)))
    return 0


__all__ = [
    "DEFAULT_LATEST_PATH",
    "DEFAULT_LIVE_DIR",
    "DEFAULT_LOG_PATH",
    "DEFAULT_STATE_PATH",
    "SHADOW_4H_KLINE_LIMIT",
    "_causal_ema_1d",
    "apply_deadband_step",
    "build_shadow_watch_symbols",
    "collect_live_shadow_snapshot",
    "compute_carry_btc_eth_live_weights",
    "compute_f4_4h_ema_live_weights",
    "compute_orderbook_slippage_bps",
    "select_live_top15_causal",
    "update_shadow_spot_accounting",
]


if __name__ == "__main__":
    raise SystemExit(main())
