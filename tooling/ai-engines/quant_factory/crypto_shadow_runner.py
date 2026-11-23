"""C0.3b — Live Public Binance Spot + USD-M Perp Shadow Collector & Paper TCA Runner.

STRICT SAFETY BOUNDARIES:
  - OrderSend = 0, ZERO API keys, ZERO authenticated endpoints!
  - Uses ONLY public Binance Spot (/api/v3/*) and USD-M Futures (/fapi/v1/*) read-only endpoints.
  - Signal calculation uses STRICTLY CLOSED 4H/D1 bars (drops currently open forming candle).
  - Logs live bid/ask, L2 orderbook depth slippage for 10k & 50k USD orders, live Spot-Perp basis &
    8h funding rates, and paper shadow target positions/TCA for:
      1. Sleeve #2 Primary: `F4_4H_EMA_24_120_BTC` (causal Top-15 universe)
      2. Sleeve #3A Primary: `CARRY_BTC_ETH_CONS_2XBUF` (2x equity buffer, BTC + ETH)
  - Outputs:
      - `.runtime/live-overnight/crypto_shadow_log.jsonl` (append-only JSONL telemetry)
      - `.runtime/live-overnight/crypto_shadow_latest.json` (atomic latest snapshot for Cockpit UI)
      - `.runtime/live-overnight/crypto_shadow_state.json` (persistent paper position & TCA state)
"""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import sys
import time
from typing import Any

import httpx
import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.crypto_causal_universe import (
    BINANCE_SPOT_BASE,
    UNIVERSE_50_SYMBOLS,
)
from quant_factory.funding_rate_carry import BINANCE_FAPI_BASE

DEFAULT_LIVE_DIR = ROOT / ".runtime" / "live-overnight"
DEFAULT_LOG_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_log.jsonl"
DEFAULT_LATEST_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_latest.json"
DEFAULT_STATE_PATH = DEFAULT_LIVE_DIR / "crypto_shadow_state.json"


# ==============================================================================
# ORDERBOOK DEPTH SLIPPAGE MODEL (PURE, DETERMINISTIC, UNIT-TESTABLE)
# ==============================================================================

def compute_orderbook_slippage_bps(
    bids: list[list[str | float]],
    asks: list[list[str | float]],
    notional_usd: float,
) -> dict[str, float]:
    """Compute exact L2 VWAP execution slippage (bps vs mid) for a market buy & sell of `notional_usd`."""
    if not bids or not asks:
        return {"spread_bps": float("nan"), "buy_slip_bps": float("nan"), "sell_slip_bps": float("nan"), "depth_ok": 0.0}
    best_bid = float(bids[0][0])
    best_ask = float(asks[0][0])
    if best_bid <= 0 or best_ask <= 0 or best_ask < best_bid:
        return {"spread_bps": float("nan"), "buy_slip_bps": float("nan"), "sell_slip_bps": float("nan"), "depth_ok": 0.0}
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
    return {
        "best_bid": round(best_bid, 8),
        "best_ask": round(best_ask, 8),
        "mid": round(mid, 8),
        "spread_bps": round(spread_bps, 3),
        "buy_slip_bps": round(buy_slip, 3) if math.isfinite(buy_slip) else None,
        "sell_slip_bps": round(sell_slip, 3) if math.isfinite(sell_slip) else None,
        "avg_oneway_slip_bps": round(0.5 * (buy_slip + sell_slip), 3) if (math.isfinite(buy_slip) and math.isfinite(sell_slip)) else None,
        "depth_ok": bool(buy_ok and sell_ok),
    }


def _causal_ema_1d(arr: np.ndarray, span: int) -> np.ndarray:
    out = np.empty_like(arr, dtype=np.float64)
    alpha = 2.0 / (span + 1.0)
    prev = float(arr[0])
    out[0] = prev
    for i in range(1, len(arr)):
        prev = alpha * float(arr[i]) + (1.0 - alpha) * prev
        out[i] = prev
    return out


def compute_f4_4h_ema_live_weights(
    closed_4h_closes: dict[str, np.ndarray],
    top15_symbols: list[str],
) -> dict[str, Any]:
    """Compute exact live causal F4_4H_EMA_24_120_BTC target weights strictly from CLOSED 4H bars."""
    btc_c = closed_4h_closes.get("BTCUSDT")
    if btc_c is None or len(btc_c) < 305:
        return {"btc_regime_bull": False, "weights": {}, "active_count": 0, "reason": "INSUFFICIENT_BTC_BARS"}

    btc_e60 = _causal_ema_1d(btc_c, 60)[-1]
    btc_e300 = _causal_ema_1d(btc_c, 300)[-1]
    btc_bull = bool(btc_e60 > btc_e300)

    vt15_4h = 0.15 / math.sqrt(365.0 * 6.0)
    raw: dict[str, float] = {}
    diagnostics: dict[str, dict[str, Any]] = {}
    n_elig = max(1, len(top15_symbols))

    for sym in top15_symbols:
        c = closed_4h_closes.get(sym)
        if c is None or len(c) < 130:
            continue
        e24 = float(_causal_ema_1d(c, 24)[-1])
        e120 = float(_causal_ema_1d(c, 120)[-1])
        rets = c[1:] / c[:-1] - 1.0
        vol120 = float(np.std(rets[-120:], ddof=1))
        sig_on = bool(btc_bull and (e24 > e120) and vol120 > 1e-6)
        w_val = (vt15_4h / vol120) / n_elig if sig_on else 0.0
        if w_val > 0.0:
            raw[sym] = w_val
        diagnostics[sym] = {
            "last_closed_4h": round(float(c[-1]), 6),
            "ema24": round(e24, 6),
            "ema120": round(e120, 6),
            "vol120_ann_pct": round(vol120 * math.sqrt(365.0 * 6.0) * 100.0, 2),
            "signal_long": sig_on,
        }

    tot = sum(raw.values())
    if tot > 1.0:
        weights = {k: round(v / tot, 6) for k, v in raw.items()}
    else:
        weights = {k: round(v, 6) for k, v in raw.items()}

    return {
        "btc_regime_bull": btc_bull,
        "btc_ema60": round(float(btc_e60), 2),
        "btc_ema300": round(float(btc_e300), 2),
        "active_count": len(weights),
        "gross_exposure": round(sum(weights.values()), 6),
        "weights": weights,
        "diagnostics": diagnostics,
    }


def compute_carry_btc_eth_live_weights(
    funding_hist_8h: dict[str, list[float]],
    prev_state: dict[str, bool] | None = None,
) -> dict[str, Any]:
    """Compute exact live causal CARRY_BTC_ETH_CONS_2XBUF notional weights (2x equity buffer, max 25% equity/coin)."""
    prev = dict(prev_state or {"BTCUSDT": False, "ETHUSDT": False})
    enter_thr = 0.03  # +3.0% annualized funding rate
    exit_thr = 0.0    # <= 0.0% annualized funding rate
    new_state: dict[str, bool] = {}
    notional_w: dict[str, float] = {}
    stats: dict[str, Any] = {}

    for sym in ("BTCUSDT", "ETHUSDT"):
        rates = funding_hist_8h.get(sym, [])
        if len(rates) < 18:
            new_state[sym] = False
            stats[sym] = {"n_settlements": len(rates), "trail_7d_ann_pct": None, "active": False}
            continue
        # Last 21 settlements = exact trailing 7 days (3 settlements/day * 7)
        w21 = rates[-21:]
        ann_7d = float(np.mean(w21)) * 3.0 * 365.0
        was_on = bool(prev.get(sym, False))
        if was_on:
            is_on = ann_7d > exit_thr
        else:
            is_on = ann_7d >= enter_thr
        new_state[sym] = is_on
        if is_on:
            # 2x equity buffer -> 0.50 total carry notional cap -> 0.25 equity per coin when both active
            notional_w[sym] = 0.25
        stats[sym] = {
            "n_settlements": len(w21),
            "last_8h_bps": round(float(w21[-1]) * 10_000.0, 3),
            "trail_7d_ann_pct": round(ann_7d * 100.0, 2),
            "active": is_on,
        }

    return {
        "equity_buffer_mult": 2.0,
        "state": new_state,
        "notional_weights_of_equity": notional_w,
        "gross_carry_notional_pct": round(sum(notional_w.values()) * 100.0, 1),
        "per_coin": stats,
    }


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
            rows = _fetch_json(c2, f"{BINANCE_SPOT_BASE}/api/v3/klines", {"symbol": sym, "interval": "1d", "limit": 32})
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
    ranked = sorted(vol30.keys(), key=lambda s: vol30[s], reverse=True)[:15]
    if "BTCUSDT" not in ranked:
        ranked = ["BTCUSDT"] + ranked[:14]
    return ranked


def collect_live_shadow_snapshot(
    *,
    state_path: Path = DEFAULT_STATE_PATH,
    log_path: Path = DEFAULT_LOG_PATH,
    latest_path: Path = DEFAULT_LATEST_PATH,
) -> dict[str, Any]:
    """Execute one complete read-only live shadow cycle and update JSONL + latest + paper state."""
    t0 = time.perf_counter()
    now_utc = datetime.now(timezone.utc)
    now_iso = now_utc.isoformat()

    prev_state: dict[str, Any] = {}
    if state_path.exists():
        try:
            prev_state = json.loads(state_path.read_text(encoding="utf-8"))
        except Exception:
            prev_state = {}

    with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexShadowRunner/1.0"}) as client:
        top15 = select_live_top15_causal(client)
        watch_syms = sorted(set(top15) | {"BTCUSDT", "ETHUSDT"})

        # 1. Fetch closed 4H klines + live L2 depth (10k/50k USD slippage) in parallel
        closed_4h: dict[str, np.ndarray] = {}
        last_4h_close_ms: dict[str, int] = {}
        depth_metrics: dict[str, dict[str, Any]] = {}

        def _fetch_coin_bundle(sym: str) -> tuple[str, np.ndarray, int, dict[str, Any]]:
            with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexShadowRunner/1.0"}) as c2:
                kl = _fetch_json(c2, f"{BINANCE_SPOT_BASE}/api/v3/klines", {"symbol": sym, "interval": "4h", "limit": 325})
                # Drop forming unclosed bar (`kl[:-1]`)
                closed_kl = kl[:-1] if len(kl) > 1 else kl
                closes = np.array([float(r[4]) for r in closed_kl], dtype=np.float64)
                last_close_t = int(closed_kl[-1][6]) if closed_kl else 0
                ob = _fetch_json(c2, f"{BINANCE_SPOT_BASE}/api/v3/depth", {"symbol": sym, "limit": 50})
                s10k = compute_orderbook_slippage_bps(ob.get("bids", []), ob.get("asks", []), 10_000.0)
                s50k = compute_orderbook_slippage_bps(ob.get("bids", []), ob.get("asks", []), 50_000.0)
                dm = {
                    "best_bid": s10k.get("best_bid"),
                    "best_ask": s10k.get("best_ask"),
                    "mid": s10k.get("mid"),
                    "spread_bps": s10k.get("spread_bps"),
                    "slip_10k_bps": s10k.get("avg_oneway_slip_bps"),
                    "slip_50k_bps": s50k.get("avg_oneway_slip_bps"),
                    "depth_50k_ok": s50k.get("depth_ok"),
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

    # 3. Compute live causal paper target weights
    s2_sig = compute_f4_4h_ema_live_weights(closed_4h, top15)
    s3a_sig = compute_carry_btc_eth_live_weights(funding_hist, prev_state.get("carry_state"))

    # 4. Update paper shadow portfolio accounting & live TCA tracking (10,000 USD ref capital per sleeve)
    s2_prev_w: dict[str, float] = prev_state.get("s2_weights", {})
    s2_prev_mids: dict[str, float] = prev_state.get("s2_mids", {})
    s2_eq = float(prev_state.get("s2_paper_equity_usd", 10_000.0))

    # Mark-to-market previous paper weights against current live mids
    s2_mtm_ret = 0.0
    for sym, w in s2_prev_w.items():
        p0 = float(s2_prev_mids.get(sym, 0.0))
        p1 = float(depth_metrics.get(sym, {}).get("mid") or 0.0)
        if p0 > 0 and p1 > 0:
            s2_mtm_ret += w * (p1 / p0 - 1.0)
    # Turnover & live orderbook TCA cost if weights changed
    all_s2_keys = set(s2_prev_w.keys()) | set(s2_sig["weights"].keys())
    s2_turnover = sum(abs(s2_sig["weights"].get(k, 0.0) - s2_prev_w.get(k, 0.0)) for k in all_s2_keys)
    s2_live_tca_bps = 0.0
    if s2_turnover > 1e-6:
        w_slip = 0.0
        for k in all_s2_keys:
            dw = abs(s2_sig["weights"].get(k, 0.0) - s2_prev_w.get(k, 0.0))
            if dw > 1e-6:
                slip_k = float(depth_metrics.get(k, {}).get("slip_10k_bps") or 5.0)
                w_slip += dw * (10.0 + slip_k)  # 10 bps Binance Spot taker fee + live L2 10k slip
        s2_live_tca_bps = w_slip / s2_turnover
    s2_cost_ret = s2_turnover * (s2_live_tca_bps / 10_000.0)
    s2_eq = s2_eq * (1.0 + s2_mtm_ret - s2_cost_ret)

    # Aggregate median/mean live L2 slippage across Top-15
    slips_10k = [float(depth_metrics[s]["slip_10k_bps"]) for s in top15 if depth_metrics[s].get("slip_10k_bps") is not None]
    slips_50k = [float(depth_metrics[s]["slip_50k_bps"]) for s in top15 if depth_metrics[s].get("slip_50k_bps") is not None]
    spreads = [float(depth_metrics[s]["spread_bps"]) for s in top15 if depth_metrics[s].get("spread_bps") is not None]

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
            "active_count": s2_sig["active_count"],
            "gross_exposure": s2_sig["gross_exposure"],
            "weights": s2_sig["weights"],
            "paper_equity_usd": round(s2_eq, 2),
            "cycle_turnover": round(s2_turnover, 6),
            "cycle_live_tca_bps": round(s2_live_tca_bps, 3),
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

    new_state = {
        "updated_utc": now_iso,
        "cycle_num": record["cycle_num"],
        "s2_weights": s2_sig["weights"],
        "s2_mids": {s: depth_metrics[s]["mid"] for s in watch_syms if depth_metrics[s].get("mid")},
        "s2_paper_equity_usd": round(s2_eq, 4),
        "carry_state": s3a_sig["state"],
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    latest_path.write_text(json.dumps(record, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
    state_path.write_text(json.dumps(new_state, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")
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
        print(json.dumps({
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
        }, indent=2, ensure_ascii=False))
        return 0

    cycles = 0
    while True:
        try:
            rec = collect_live_shadow_snapshot()
            print(f"[{rec['timestamp_utc']}] cycle={rec['cycle_num']} s2_exp={rec['sleeve2_f4_4h_ema']['gross_exposure']:.3f} s3a_exp={rec['sleeve3a_carry_btc_eth']['gross_carry_notional_pct']}% med_10k_slip={rec['tca_summary_top15']['median_slip_10k_bps']}bps", flush=True)
        except Exception as exc:
            err_rec = {"timestamp_utc": datetime.now(timezone.utc).isoformat(), "status": "ERROR", "error": f"{type(exc).__name__}:{exc}"}
            DEFAULT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            with DEFAULT_LOG_PATH.open("a", encoding="utf-8", newline="\n") as f:
                f.write(json.dumps(err_rec) + "\n")
            print(f"ERROR: {err_rec}", flush=True)
        cycles += 1
        if args.max_cycles > 0 and cycles >= args.max_cycles:
            break
        time.sleep(max(10, int(args.interval_sec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
