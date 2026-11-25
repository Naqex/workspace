"""Wave-2 Cycle 4A — Live Passive-Limit Fill-Rate & Adverse-Selection Shadow Probe for M2B_BLEND_50_FUND_50_MOM.

STRICT SAFETY BOUNDARIES:
  - OrderSend = 0, ZERO API keys, ZERO authenticated endpoints!
  - Uses ONLY public Binance USD-M Futures (/fapi/v1/*) read-only endpoints.
  - Strictly uses CLOSED 4H/1m bars and SETTLED 8h funding rates (drops forming candles).
  - Evaluates conservative strict touch-through passive fills (`low < posted_bid` for buys,
    `high > posted_ask` for sells) over trailing 5m, 15m, and 60m windows, measures 5m/15m
    post-fill adverse selection (bps), and compares effective blended Maker cost directly
    against Lab #2B's `M2 (70% fill = 6.15 bps)` hurdle.
  - Outputs:
      * `.runtime/live-overnight/crypto_maker_shadow.jsonl` (append-only telemetry)
      * `.runtime/live-overnight/crypto_maker_shadow_latest.json` (atomic snapshot)
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

from quant_factory.crypto_maker_statarb_study import TIER_M2_70_BPS
from quant_factory.crypto_statarb_pairs_lab import _normalize_dollar_neutral_weights
from quant_factory.funding_rate_carry import BINANCE_FAPI_BASE, PERP_UNIVERSE_20

DEFAULT_LIVE_DIR = ROOT / ".runtime" / "live-overnight"
DEFAULT_MAKER_LOG_PATH = DEFAULT_LIVE_DIR / "crypto_maker_shadow.jsonl"
DEFAULT_MAKER_LATEST_PATH = DEFAULT_LIVE_DIR / "crypto_maker_shadow_latest.json"

ORDER_SEND_COUNT = 0
API_KEYS_USED = 0


# ==============================================================================
# PURE DETERMINISTIC PASSIVE-LIMIT FILL & ADVERSE-SELECTION MODEL (UNIT-TESTABLE)
# ==============================================================================

def simulate_passive_limit_window(
    m1_high: np.ndarray,
    m1_low: np.ndarray,
    m1_close: np.ndarray,
    *,
    side: int,
    posted_px: float,
    horizon_bars: int,
) -> dict[str, Any]:
    """Simulate a resting passive limit order over `horizon_bars` 1m bars using strict touch-through.

    Strict touch-through (conservative queue-jump proof):
      - Buy (`side == +1`) posted at `posted_px` fills ONLY when a bar trades strictly below (`low < posted_px`).
      - Sell (`side == -1`) posted at `posted_px` fills ONLY when a bar trades strictly above (`high > posted_px`).
    Adverse selection (bps, positive = price moved AGAINST our fill):
      - Buy:  `(posted_px - close_after) / posted_px * 10000`
      - Sell: `(close_after - posted_px) / posted_px * 10000`
    """
    if side not in (-1, 1) or not math.isfinite(posted_px) or posted_px <= 0.0:
        return {"filled": False, "fill_bar": None, "adv_sel_5m_bps": None, "adv_sel_15m_bps": None}

    n = len(m1_close)
    h_lim = min(n, max(1, int(horizon_bars)))
    fill_idx: int | None = None
    for k in range(h_lim):
        if side == 1 and float(m1_low[k]) < posted_px:
            fill_idx = k
            break
        if side == -1 and float(m1_high[k]) > posted_px:
            fill_idx = k
            break

    if fill_idx is None:
        return {"filled": False, "fill_bar": None, "adv_sel_5m_bps": None, "adv_sel_15m_bps": None}

    def _adv_after(offset: int) -> float | None:
        idx = fill_idx + offset
        if idx >= n or not math.isfinite(float(m1_close[idx])):
            return None
        px_after = float(m1_close[idx])
        # Positive bps = adverse move against filled side
        adv = float(side) * (posted_px - px_after) / posted_px * 10_000.0
        return round(adv, 3)

    return {
        "filled": True,
        "fill_bar": int(fill_idx),
        "adv_sel_5m_bps": _adv_after(5),
        "adv_sel_15m_bps": _adv_after(15),
    }


def aggregate_maker_probe_metrics(
    trials: list[dict[str, Any]],
    *,
    maker_fee_bps: float = 2.0,
    taker_fee_bps: float = 5.0,
    taker_slip_bps: float = 5.0,
    m2_hurdle_bps: float = TIER_M2_70_BPS,
    m2_fill_floor: float = 0.70,
) -> dict[str, Any]:
    """Aggregate fill probability, adverse selection, and effective all-in Maker cost vs Lab #2B M2 hurdle."""
    n_tot = len(trials)
    if n_tot == 0:
        return {
            "n_trials": 0,
            "fill_rate": 0.0,
            "mean_adv_sel_5m_bps": None,
            "mean_adv_sel_15m_bps": None,
            "effective_cost_bps": round(taker_fee_bps + taker_slip_bps, 3),
            "passes_m2_hurdle": False,
        }

    filled = [t for t in trials if t.get("filled")]
    fill_rate = len(filled) / float(n_tot)
    adv5 = [float(t["adv_sel_5m_bps"]) for t in filled if t.get("adv_sel_5m_bps") is not None]
    adv15 = [float(t["adv_sel_15m_bps"]) for t in filled if t.get("adv_sel_15m_bps") is not None]
    mean_adv5 = float(np.mean(adv5)) if adv5 else 0.0
    mean_adv15 = float(np.mean(adv15)) if adv15 else None

    # Conservative cost floor: never credit negative adverse selection as free negative fees!
    adv_cost = max(0.0, mean_adv5)
    eff_bps = fill_rate * (maker_fee_bps + adv_cost) + (1.0 - fill_rate) * (taker_fee_bps + taker_slip_bps)
    return {
        "n_trials": n_tot,
        "n_filled": len(filled),
        "fill_rate": round(fill_rate, 4),
        "mean_adv_sel_5m_bps": round(mean_adv5, 3) if adv5 else None,
        "mean_adv_sel_15m_bps": round(mean_adv15, 3) if mean_adv15 is not None else None,
        "effective_cost_bps": round(eff_bps, 3),
        "m2_hurdle_bps": round(m2_hurdle_bps, 3),
        "passes_m2_hurdle": bool((fill_rate >= m2_fill_floor) and (eff_bps <= m2_hurdle_bps)),
    }


def compute_live_m2b_blend_weights(
    closed_4h_closes: dict[str, np.ndarray],
    funding_hist_8h: dict[str, list[float]],
    *,
    symbols: tuple[str, ...] = PERP_UNIVERSE_20,
    k_fund: int = 4,
    k_mom: int = 5,
    min_fund_spread_ann: float = 0.10,
) -> dict[str, Any]:
    """Compute exact live causal dollar-neutral `M2B_BLEND_50_FUND_50_MOM` target weights (CLOSED bars only)."""
    syms = [s for s in symbols if s in closed_4h_closes and len(closed_4h_closes[s]) >= 86]
    n_s = len(syms)
    if n_s < 2 * max(k_fund, k_mom):
        return {"weights": {}, "net_exposure": 0.0, "gross_exposure": 0.0, "fund_active": False, "mom_active": False}

    vols = np.zeros(n_s, dtype=np.float64)
    mom14_scores = np.zeros(n_s, dtype=np.float64)
    fund7_ann = np.full(n_s, np.nan, dtype=np.float64)

    for i, s in enumerate(syms):
        c = closed_4h_closes[s]
        rets = c[1:] / c[:-1] - 1.0
        v84 = float(np.std(rets[-84:], ddof=1))
        vols[i] = max(v84, 1e-4)
        ret14 = float(c[-1] / c[-85] - 1.0)
        mom14_scores[i] = ret14 / vols[i]
        fr = funding_hist_8h.get(s, [])
        if len(fr) >= 18:
            fund7_ann[i] = float(np.mean(fr[-21:])) * 3.0 * 365.0

    # Sleeve A: 7d Funding-Dislocation L/S (Short Top-K highest funding, Long Bot-K lowest funding)
    w_fund = np.zeros(n_s, dtype=np.float64)
    fund_active = False
    fund_spread_ann = 0.0
    valid_f = np.where(np.isfinite(fund7_ann))[0]
    if len(valid_f) >= 2 * k_fund:
        ord_f = valid_f[np.argsort(fund7_ann[valid_f])]
        bot_f = ord_f[:k_fund]
        top_f = ord_f[-k_fund:]
        fund_spread_ann = float(np.mean(fund7_ann[top_f]) - np.mean(fund7_ann[bot_f]))
        if fund_spread_ann >= min_fund_spread_ann:
            rl = np.zeros(n_s, dtype=np.float64)
            rs = np.zeros(n_s, dtype=np.float64)
            rl[bot_f] = 1.0 / vols[bot_f]
            rs[top_f] = 1.0 / vols[top_f]
            w_fund = _normalize_dollar_neutral_weights(rl, rs, target_side_gross=0.50)
            fund_active = True

    # Sleeve B: 14d Vol-Managed XSMOM (Long Top-K winners, Short Bot-K laggards)
    ord_m = np.argsort(mom14_scores)
    bot_m = ord_m[:k_mom]
    top_m = ord_m[-k_mom:]
    rl_m = np.zeros(n_s, dtype=np.float64)
    rs_m = np.zeros(n_s, dtype=np.float64)
    rl_m[top_m] = 1.0 / vols[top_m]
    rs_m[bot_m] = 1.0 / vols[bot_m]
    w_mom = _normalize_dollar_neutral_weights(rl_m, rs_m, target_side_gross=0.50)

    w_blend = 0.50 * w_fund + 0.50 * w_mom
    w_dict = {syms[i]: round(float(w_blend[i]), 6) for i in range(n_s) if abs(w_blend[i]) > 1e-6}
    return {
        "weights": w_dict,
        "fund_active": fund_active,
        "fund_spread_ann_pct": round(fund_spread_ann * 100.0, 2),
        "mom_active": True,
        "long_legs": sorted(k for k, v in w_dict.items() if v > 0),
        "short_legs": sorted(k for k, v in w_dict.items() if v < 0),
        "net_exposure": round(float(np.sum(w_blend)), 8),
        "gross_exposure": round(float(np.sum(np.abs(w_blend))), 6),
    }


# ==============================================================================
# LIVE PUBLIC BINANCE USD-M FUTURES SHADOW COLLECTOR (OrderSend = 0, 0 API KEYS)
# ==============================================================================

def _get_json(client: httpx.Client, url: str, params: dict[str, Any] | None = None) -> Any:
    for attempt in range(3):
        r = client.get(url, params=params)
        if r.status_code == 200:
            return r.json()
        if r.status_code in (429, 500, 502, 503):
            time.sleep(0.4 * (attempt + 1))
            continue
        raise RuntimeError(f"HTTP {r.status_code} for {url}: {r.text[:100]}")
    raise RuntimeError(f"Retries exhausted for {url}")


def _fetch_perp_bundle(symbol: str) -> tuple[str, dict[str, Any]]:
    with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexMakerShadowProbe/1.0"}) as client:
        k4 = _get_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/klines", {"symbol": symbol, "interval": "4h", "limit": 92})
        k1 = _get_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/klines", {"symbol": symbol, "interval": "1m", "limit": 95})
        fr = _get_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/fundingRate", {"symbol": symbol, "limit": 24})
    # Drop currently forming last bar on BOTH 4h and 1m -> strictly closed bars!
    c4 = np.array([float(row[4]) for row in k4[:-1]], dtype=np.float64)
    k1_closed = k1[:-1]
    o1 = np.array([float(row[1]) for row in k1_closed], dtype=np.float64)
    h1 = np.array([float(row[2]) for row in k1_closed], dtype=np.float64)
    l1 = np.array([float(row[3]) for row in k1_closed], dtype=np.float64)
    c1 = np.array([float(row[4]) for row in k1_closed], dtype=np.float64)
    rates = [float(row["fundingRate"]) for row in fr]
    return symbol, {"c4": c4, "o1": o1, "h1": h1, "l1": l1, "c1": c1, "rates": rates}


def run_probe_once(
    *,
    log_path: Path = DEFAULT_MAKER_LOG_PATH,
    latest_path: Path = DEFAULT_MAKER_LATEST_PATH,
    cycle_num: int = 1,
) -> dict[str, Any]:
    """Execute one live public Binance USD-M Futures passive-limit fill & adverse-selection probe."""
    t0 = time.perf_counter()
    now_utc = datetime.now(timezone.utc).isoformat()

    with httpx.Client(timeout=12.0, headers={"User-Agent": "NaqexMakerShadowProbe/1.0"}) as client:
        tickers = _get_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/ticker/bookTicker")
        prems = _get_json(client, f"{BINANCE_FAPI_BASE}/fapi/v1/premiumIndex")

    bt_map = {t["symbol"]: t for t in tickers if t.get("symbol") in PERP_UNIVERSE_20}
    prem_map = {p["symbol"]: p for p in prems if p.get("symbol") in PERP_UNIVERSE_20}

    bundles: dict[str, dict[str, Any]] = {}
    with ThreadPoolExecutor(max_workers=8) as pool:
        futs = [pool.submit(_fetch_perp_bundle, s) for s in PERP_UNIVERSE_20]
        for fut in as_completed(futs):
            sym, data = fut.result()
            bundles[sym] = data

    closed_4h = {s: bundles[s]["c4"] for s in PERP_UNIVERSE_20 if s in bundles}
    fund_hist = {s: bundles[s]["rates"] for s in PERP_UNIVERSE_20 if s in bundles}
    basket = compute_live_m2b_blend_weights(closed_4h, fund_hist)

    # Evaluate strict touch-through passive limit fills over trailing 5m / 15m / 60m windows
    # across active basket legs (and full 20-perp universe control) using live top-of-book half-spread!
    horizon_trials_basket: dict[int, list[dict[str, Any]]] = {5: [], 15: [], 60: []}
    horizon_trials_all20: dict[int, list[dict[str, Any]]] = {5: [], 15: [], 60: []}
    per_symbol_live: dict[str, dict[str, Any]] = {}

    for sym in PERP_UNIVERSE_20:
        b = bundles.get(sym)
        bt = bt_map.get(sym)
        pr = prem_map.get(sym)
        if not b or not bt:
            continue
        bid = float(bt["bidPrice"])
        ask = float(bt["askPrice"])
        mid = 0.5 * (bid + ask)
        spread_bps = ((ask - bid) / mid * 10_000.0) if mid > 0 else 0.0
        half_sp_frac = 0.5 * (ask - bid) / mid if mid > 0 else 0.0
        w_sym = float(basket["weights"].get(sym, 0.0))

        per_symbol_live[sym] = {
            "bid": bid,
            "ask": ask,
            "spread_bps": round(spread_bps, 3),
            "last_funding_bps": round(float(pr.get("lastFundingRate", 0.0)) * 10_000.0, 3) if pr else None,
            "m2b_target_weight": w_sym,
        }

        o1, h1, l1, c1 = b["o1"], b["h1"], b["l1"], b["c1"]
        n1 = len(c1)
        if n1 < 80:
            continue

        # Test multiple trailing causal start offsets so each snapshot builds rich empirical statistics
        # Reserve last 15 bars for clean 5m & 15m post-fill adverse selection measurement!
        sides_to_test = [1 if w_sym > 0 else -1] if abs(w_sym) > 1e-6 else []
        for horizon, starts in ((5, (n1 - 75, n1 - 55, n1 - 35, n1 - 21)), (15, (n1 - 75, n1 - 55, n1 - 31)), (60, (n1 - 76,))):
            for st_i in starts:
                if st_i < 0 or st_i + horizon + 15 > n1:
                    continue
                ref_mid = float(o1[st_i])
                for s_all in (1, -1):
                    px_post = ref_mid * (1.0 - half_sp_frac) if s_all == 1 else ref_mid * (1.0 + half_sp_frac)
                    res = simulate_passive_limit_window(
                        h1[st_i:], l1[st_i:], c1[st_i:], side=s_all, posted_px=px_post, horizon_bars=horizon
                    )
                    horizon_trials_all20[horizon].append(res)
                    if s_all in sides_to_test:
                        horizon_trials_basket[horizon].append(res)

    summary_basket = {f"{h}m": aggregate_maker_probe_metrics(horizon_trials_basket[h]) for h in (5, 15, 60)}
    summary_all20 = {f"{h}m": aggregate_maker_probe_metrics(horizon_trials_all20[h]) for h in (5, 15, 60)}
    spreads = [v["spread_bps"] for v in per_symbol_live.values()]

    record = {
        "schema": "naqex-crypto-maker-shadow-v1",
        "timestamp_utc": now_utc,
        "cycle_num": int(cycle_num),
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "order_send_count": ORDER_SEND_COUNT,
        "api_keys_used": API_KEYS_USED,
        "universe_count": len(per_symbol_live),
        "median_perp_spread_bps": round(float(np.median(spreads)), 3) if spreads else None,
        "m2b_blend_live_basket": basket,
        "passive_limit_probe_active_basket": summary_basket,
        "passive_limit_probe_all20_control": summary_all20,
        "per_symbol_snapshot": per_symbol_live,
    }

    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps(record) + "\n")
    tmp = latest_path.with_suffix(".tmp")
    tmp.write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8", newline="\n")
    tmp.replace(latest_path)
    return record


def main() -> int:
    ap = argparse.ArgumentParser(description="Live Public Binance USD-M Futures Passive-Limit Shadow Probe (OrderSend=0)")
    ap.add_argument("--once", action="store_true", help="Run a single probe snapshot and exit")
    ap.add_argument("--daemon", action="store_true", help="Run continuously every --interval-sec")
    ap.add_argument("--interval-sec", type=int, default=300)
    ap.add_argument("--max-cycles", type=int, default=0, help="0 = infinite in --daemon mode")
    args = ap.parse_args()

    if not args.daemon or args.once:
        rec = run_probe_once(cycle_num=1)
        print(json.dumps({
            "timestamp_utc": rec["timestamp_utc"],
            "elapsed_sec": rec["elapsed_sec"],
            "order_send_count": rec["order_send_count"],
            "median_perp_spread_bps": rec["median_perp_spread_bps"],
            "active_legs": len(rec["m2b_blend_live_basket"]["weights"]),
            "net_exposure": rec["m2b_blend_live_basket"]["net_exposure"],
            "active_basket_probe": rec["passive_limit_probe_active_basket"],
            "all20_control_probe": rec["passive_limit_probe_all20_control"],
        }, indent=2))
        return 0

    cyc = 0
    while True:
        cyc += 1
        try:
            rec = run_probe_once(cycle_num=cyc)
            p60 = rec["passive_limit_probe_active_basket"]["60m"]
            print(
                f"[{rec['timestamp_utc']}] cycle={cyc} active={len(rec['m2b_blend_live_basket']['weights'])} "
                f"fill60m={p60['fill_rate']*100:.1f}% eff60m={p60['effective_cost_bps']}bps passM2={p60['passes_m2_hurdle']}",
                flush=True,
            )
        except Exception as exc:
            print(f"[ERROR] cycle={cyc}: {type(exc).__name__}: {exc}", flush=True)
        if args.max_cycles > 0 and cyc >= args.max_cycles:
            break
        time.sleep(max(30, int(args.interval_sec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
