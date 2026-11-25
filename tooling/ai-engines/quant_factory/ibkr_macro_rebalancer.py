"""Strictly Offline Dry-Run IBKR Macro ETF Rebalancer for Sleeve #3B (`OrderSend = 0`).

Generates deterministic daily/monthly target weights and IBKR BasketTrader-compatible
dry-run order tickets (CSV + JSON receipt) with 100% mathematical parity to
`quant_factory.macro_etf_trend`:
  - `M5_VOL_PARITY_TREND_GUARD` (Monthly rebalance, 1.0x Long-Only, 4 macro buckets + SMA200 25% trend guard)
  - `M1_AHL_TSMOM_LS_VOL10` (Weekly/month-end rebalance, 1.5x gross cap Long/Short Crisis Alpha)
  - `BLEND_50_M5_50_M1` (50% M5 + 50% M1 Crisis-Alpha + Risk-Parity hybrid)

HARD SAFETY INVARIANTS:
  - `ORDER_SEND_COUNT = 0`, `DRY_RUN_ONLY = True`
  - ZERO IBKR TWS / Gateway socket connections, ZERO API keys, ZERO order placement!
  - Strictly causal `<= as_of_date` market data from `.runtime/macro-etf-cache/` for `t+1` execution.
"""

from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys
from typing import Any

import numpy as np

AI_ENGINES = Path(__file__).resolve().parents[1]
ROOT = AI_ENGINES.parents[1]
if str(AI_ENGINES) not in sys.path:
    sys.path.insert(0, str(AI_ENGINES))

from quant_factory.macro_etf_trend import (
    ETF_UNIVERSE_12,
    MACRO_BUCKETS,
    MACRO_CACHE_DIR,
    build_macro_strategies,
    load_etf_panel,
)

ORDER_SEND_COUNT = 0
DRY_RUN_ONLY = True
LEGACY_MODES = (
    "M5_VOL_PARITY_TREND_GUARD",
    "M1_AHL_TSMOM_LS_VOL10",
    "BLEND_50_M5_50_M1",
)
ETF40_MODES = (
    "l7_top2",
    "s4_lab4_eqw",
    "super_etf_6eng",
)
VALID_MODES = LEGACY_MODES + ("s3b_macro",) + ETF40_MODES
IBKR_EXCHANGE_DEFAULT = "SMART"
IBKR_CURRENCY_DEFAULT = "USD"
IBKR_COMM_PER_SHARE = 0.0035
IBKR_MIN_ORDER_USD = 0.35
IBKR_MAX_ORDER_PCT = 0.01
MIN_ORDER_FEE_WARN_BPS_YR = 25.0

MODE_ANNUAL_REBAL_EVENTS: dict[str, float] = {
    "M5_VOL_PARITY_TREND_GUARD": 12.0,
    "s3b_macro": 12.0,
    "M1_AHL_TSMOM_LS_VOL10": 26.0,
    "BLEND_50_M5_50_M1": 24.0,
    "l7_top2": 12.0,
    "s4_lab4_eqw": 18.0,
    "super_etf_6eng": 18.0,
}


def compute_ibkr_tiered_commission(shares: float, price_usd: float) -> float:
    """Exact IBKR US Tiered ETF commission: $0.0035/share, $0.35 min per order, capped at 1.0% notional."""
    sh = abs(float(shares))
    notional = sh * max(float(price_usd), 0.0)
    if sh <= 1e-9 or notional <= 1e-9:
        return 0.0
    return min(max(IBKR_MIN_ORDER_USD, IBKR_COMM_PER_SHARE * sh), IBKR_MAX_ORDER_PCT * notional)


def _compute_causal_diagnostics(panel: dict[str, Any], idx: int) -> dict[str, dict[str, Any]]:
    """Compute causal per-symbol price, 60d annualized vol, SMA200, and trend-guard state at `idx`."""
    px = panel["adjclose"]
    syms = panel["symbols"]
    n_t, n_k = px.shape
    rets = np.full((n_t, n_k), np.nan, dtype=np.float64)
    ok = np.isfinite(px[1:]) & np.isfinite(px[:-1]) & (px[:-1] > 0)
    rets[1:][ok] = px[1:][ok] / px[:-1][ok] - 1.0

    diag: dict[str, dict[str, Any]] = {}
    for j, sym in enumerate(syms):
        c_now = float(px[idx, j]) if np.isfinite(px[idx, j]) else math.nan
        vol60 = math.nan
        if idx >= 60:
            r60 = rets[idx - 59:idx + 1, j]
            r60 = r60[np.isfinite(r60)]
            if len(r60) >= 50:
                sd = float(np.std(r60, ddof=1))
                if sd > 1e-6:
                    vol60 = sd * math.sqrt(252.0)
        sma200 = math.nan
        if idx >= 199:
            w200 = px[idx - 199:idx + 1, j]
            w200 = w200[np.isfinite(w200)]
            if len(w200) >= 190:
                sma200 = float(np.mean(w200))
        above_sma200 = bool(math.isfinite(c_now) and math.isfinite(sma200) and c_now > sma200)
        bucket = next((b for b, bs in MACRO_BUCKETS.items() if sym in bs), "OTHER")
        diag[sym] = {
            "bucket": bucket,
            "adjclose": round(c_now, 4) if math.isfinite(c_now) else None,
            "vol60_ann_pct": round(vol60 * 100.0, 2) if math.isfinite(vol60) else None,
            "sma200": round(sma200, 4) if math.isfinite(sma200) else None,
            "trend_guard": "ABOVE_SMA200" if above_sma200 else "BELOW_SMA200_CUT25PCT",
        }
    return diag


def _resolve_etf40_weights_and_panel(
    mode: str,
    as_of_date: str | None,
    etf40_cache_dir: Path | None = None,
) -> tuple[dict[str, Any], np.ndarray, int, str, str]:
    """Load strictly causal <= as_of_date 40-ETF weights for `l7_top2`, `s4_lab4_eqw`, or `super_etf_6eng`."""
    from quant_factory.etf40_multifactor_vrp_lab import ETF40_CACHE_DIR, load_etf40_panel
    from quant_factory.lab7_overnight_macro_rd_loop import load_etf40_ohlc_panel
    from quant_factory.ownbook_etf_super_sleeve import (
        LAB4_APPROVED_IDS,
        SUPER_6_IDS,
        build_all_9_approved_engine_weights,
    )

    cdir = etf40_cache_dir if etf40_cache_dir is not None else ETF40_CACHE_DIR
    p4_full = load_etf40_panel(cache_dir=cdir)
    p7_full = load_etf40_ohlc_panel(cache_dir=cdir)
    dates: list[str] = list(p4_full["dates"])
    if len(dates) < 253:
        raise ValueError(f"Need at least 253 trading days in ETF40 panel, got {len(dates)}")

    if as_of_date is not None:
        elig = [i for i, d in enumerate(dates) if d <= as_of_date]
        if not elig or elig[-1] < 252:
            raise ValueError(f"Insufficient causal history <= {as_of_date}")
        idx = elig[-1]
    else:
        idx = len(dates) - 1

    # Strictly truncate BOTH panels to <= idx so zero future bars can ever enter signal calculation
    p4_sub = {
        "dates": dates[: idx + 1],
        "symbols": list(p4_full["symbols"]),
        "adjclose": p4_full["adjclose"][: idx + 1],
    }
    p7_sub = {
        "dates": dates[: idx + 1],
        "tickers": list(p7_full["tickers"]),
        "tradable_mask": p7_full["tradable_mask"],
        "adj_open": p7_full["adj_open"][: idx + 1],
        "adj_close": p7_full["adj_close"][: idx + 1],
        "r_cc": p7_full["r_cc"][: idx + 1],
        "r_ov": p7_full["r_ov"][: idx + 1],
        "r_id": p7_full["r_id"][: idx + 1],
    }
    eng_w = build_all_9_approved_engine_weights(p4_sub, p7_sub)
    if mode == "l7_top2":
        w_vec = 0.50 * eng_w["L7_B1_MACRO_QUAD_REGIME"][-1] + 0.50 * eng_w["L7_C3_MM17_VAR_MACRO_CORE"][-1]
        cadence = "MONTHLY_MACRO_REGIME_PLUS_VAR_SCALE"
    elif mode == "s4_lab4_eqw":
        w_vec = sum(eng_w[s][-1] for s in LAB4_APPROVED_IDS) / float(len(LAB4_APPROVED_IDS))
        cadence = "WEEKLY_PLUS_RSI2_PULLBACK_40ETF"
    elif mode == "super_etf_6eng":
        w_vec = sum(eng_w[s][-1] for s in SUPER_6_IDS) / float(len(SUPER_6_IDS))
        cadence = "MULTI_ENGINE_6ENG_NETTED_40ETF"
    else:
        raise ValueError(f"Unknown ETF40 mode: {mode}")

    # Hard-zero non-tradable signal-only indices (^VIX, ^VIX3M)
    w_vec = np.where(p7_sub["tradable_mask"], w_vec, 0.0)
    m_path = cdir / "manifest.sha256.json"
    m_sha = hashlib.sha256(m_path.read_bytes()).hexdigest()[:16] if m_path.is_file() else "ETF40_PARQUET_CACHE"
    return p4_sub, w_vec, idx, cadence, m_sha


def generate_rebalance_plan(
    *,
    mode: str = "M5_VOL_PARITY_TREND_GUARD",
    equity_usd: float = 25_000.0,
    current_shares: dict[str, float] | None = None,
    as_of_date: str | None = None,
    min_trade_notional_usd: float = 100.0,
    allow_fractional_shares: bool = False,
    est_cost_bps_oneway: float = 5.0,
    cache_dir: Path = MACRO_CACHE_DIR,
    panel: dict[str, Any] | None = None,
    etf40_cache_dir: Path | None = None,
) -> dict[str, Any]:
    """Compute strictly causal target weights & dry-run IBKR order tickets (`OrderSend = 0`)."""
    if mode not in VALID_MODES:
        raise ValueError(f"Unsupported mode '{mode}'. Choose from {VALID_MODES}")
    if equity_usd <= 0:
        raise ValueError(f"equity_usd must be positive, got {equity_usd}")

    eff_mode = "M5_VOL_PARITY_TREND_GUARD" if mode == "s3b_macro" else mode

    if eff_mode in ETF40_MODES:
        sub_panel, w_vec, idx, rebalance_cadence, manifest_sha = _resolve_etf40_weights_and_panel(
            eff_mode, as_of_date, etf40_cache_dir=etf40_cache_dir
        )
        dates = sub_panel["dates"]
        syms = sub_panel["symbols"]
        allow_short = False
    else:
        data_panel = panel if panel is not None else load_etf_panel(symbols=ETF_UNIVERSE_12, cache_dir=cache_dir)
        dates = data_panel["dates"]
        syms = data_panel["symbols"]
        px: np.ndarray = data_panel["adjclose"]
        if len(dates) < 253:
            raise ValueError(f"Need at least 253 trading days in ETF panel, got {len(dates)}")

        if as_of_date is not None:
            eligible_indices = [i for i, d in enumerate(dates) if d <= as_of_date]
            if not eligible_indices or eligible_indices[-1] < 252:
                raise ValueError(f"Insufficient causal history <= {as_of_date}")
            idx = eligible_indices[-1]
        else:
            idx = len(dates) - 1

        # Strictly truncate panel to <= idx so zero future bars can ever enter strategy computation
        sub_panel = {
            "dates": dates[:idx + 1],
            "symbols": syms,
            "adjclose": px[:idx + 1],
        }
        strategies = build_macro_strategies(sub_panel)
        if eff_mode == "M5_VOL_PARITY_TREND_GUARD":
            w_vec = strategies["M5_VOL_PARITY_TREND_GUARD"][2][-1]
            rebalance_cadence = "MONTHLY_END_OF_MONTH"
            allow_short = False
        elif eff_mode == "M1_AHL_TSMOM_LS_VOL10":
            w_vec = strategies["M1_AHL_TSMOM_LS_VOL10"][2][-1]
            rebalance_cadence = "WEEKLY_5D_OR_MONTH_END"
            allow_short = True
        else:
            w_m5 = strategies["M5_VOL_PARITY_TREND_GUARD"][2][-1]
            w_m1 = strategies["M1_AHL_TSMOM_LS_VOL10"][2][-1]
            w_vec = 0.50 * w_m5 + 0.50 * w_m1
            rebalance_cadence = "WEEKLY_M1_PLUS_MONTHLY_M5"
            allow_short = True

        manifest_path = cache_dir / "manifest.sha256.json"
        manifest_sha = (
            hashlib.sha256(manifest_path.read_bytes()).hexdigest()[:16]
            if manifest_path.is_file()
            else "SYNTHETIC_IN_MEMORY"
        )

    held_map = {str(k).upper(): float(v) for k, v in (current_shares or {}).items()}
    diag = _compute_causal_diagnostics(sub_panel, idx)

    allocations: list[dict[str, Any]] = []
    tickets: list[dict[str, Any]] = []
    total_target_notional = 0.0
    total_gross_exposure = 0.0
    total_net_exposure = 0.0
    total_turnover_usd = 0.0
    total_ibkr_comm_usd = 0.0

    for j, sym in enumerate(syms):
        if sym.startswith("^"):
            continue
        w = float(w_vec[j]) if np.isfinite(w_vec[j]) else 0.0
        if not allow_short and w < 0.0:
            w = 0.0
        price = diag[sym]["adjclose"]
        cur_sh = held_map.get(sym, 0.0)
        if price is None or price <= 0.0:
            continue

        target_notional = equity_usd * w
        raw_target_sh = target_notional / price
        if allow_fractional_shares:
            target_sh = round(raw_target_sh, 4)
        else:
            # Truncate toward zero so gross exposure never silently exceeds target cap
            target_sh = float(int(math.trunc(raw_target_sh)))

        delta_sh = target_sh - cur_sh
        delta_notional = delta_sh * price
        actual_notional = target_sh * price

        total_target_notional += target_notional
        total_gross_exposure += abs(actual_notional) / equity_usd
        total_net_exposure += actual_notional / equity_usd

        action = "HOLD"
        if abs(delta_notional) >= min_trade_notional_usd and abs(delta_sh) > 1e-6:
            if delta_sh > 0:
                action = "COVER" if cur_sh < 0 and target_sh <= 0 else "BUY"
            else:
                action = "SHORT" if target_sh < 0 and cur_sh >= 0 else "SELL"

        alloc_row = {
            "symbol": sym,
            "bucket": diag[sym]["bucket"],
            "price_usd": price,
            "vol60_ann_pct": diag[sym]["vol60_ann_pct"],
            "sma200": diag[sym]["sma200"],
            "trend_guard": diag[sym]["trend_guard"],
            "target_weight_pct": round(w * 100.0, 2),
            "target_notional_usd": round(target_notional, 2),
            "current_shares": cur_sh,
            "target_shares": target_sh,
            "delta_shares": round(delta_sh, 4),
            "delta_notional_usd": round(delta_notional, 2),
            "action": action,
        }
        allocations.append(alloc_row)

        if action != "HOLD":
            qty = abs(delta_sh)
            ibkr_action = "BUY" if delta_sh > 0 else "SELL"
            # Limit collar +-0.30% around reference close for safe dry-run IBKR basket ticket
            lmt_px = round(price * (1.003 if ibkr_action == "BUY" else 0.997), 2)
            order_comm = compute_ibkr_tiered_commission(qty, price)
            total_ibkr_comm_usd += order_comm
            total_turnover_usd += abs(delta_notional)
            tickets.append({
                "Action": ibkr_action,
                "Quantity": int(round(qty)) if not allow_fractional_shares else round(qty, 4),
                "Symbol": sym,
                "SecType": "STK",
                "Exchange": IBKR_EXCHANGE_DEFAULT,
                "Currency": IBKR_CURRENCY_DEFAULT,
                "OrderType": "LMT",
                "LmtPrice": lmt_px,
                "TimeInForce": "DAY",
                "OrderRef": f"NAQEX_{mode}_{dates[idx]}",
                "BasketTag": f"DRYRUN_ONLY_{mode}_{dates[idx]}",
                "DryRunOnly": "TRUE",
                "Intent": action,
                "EstNotionalUSD": round(abs(delta_notional), 2),
                "EstIbkrCommUSD": round(order_comm, 4),
            })

    idle_cash_usd = max(0.0, equity_usd - sum(max(0.0, a["target_shares"] * a["price_usd"]) for a in allocations))
    est_friction_usd = total_turnover_usd * (est_cost_bps_oneway / 10_000.0)
    rebal_events_yr = MODE_ANNUAL_REBAL_EVENTS.get(mode, 12.0)
    est_annual_comm_usd = total_ibkr_comm_usd * rebal_events_yr
    est_annual_comm_drag_bps = round(1e4 * est_annual_comm_usd / equity_usd, 2)
    min_order_fee_warning = bool(est_annual_comm_drag_bps > MIN_ORDER_FEE_WARN_BPS_YR)
    fee_warning_detail = (
        f"WARNING: Estimated IBKR Tiered commission drag is {est_annual_comm_drag_bps:.1f} bps/yr "
        f"(> {MIN_ORDER_FEE_WARN_BPS_YR:.0f} bps/yr threshold at {equity_usd:,.0f} USD due to 0.35 USD min/order). "
        "Recommend switching to low-turnover `l7_top2` or `s3b_macro` with `--fractional on` until capital >= 25k-50k USD."
        if min_order_fee_warning
        else "OK: Estimated IBKR Tiered commission drag within <= 25 bps/yr budget."
    )

    return {
        "schema": "naqex-ibkr-macro-rebalance-v1",
        "generated_utc": datetime.now(timezone.utc).isoformat(),
        "order_send_count": ORDER_SEND_COUNT,
        "dry_run_only": DRY_RUN_ONLY,
        "mode": mode,
        "rebalance_cadence": rebalance_cadence,
        "allow_short": allow_short,
        "allow_fractional_shares": bool(allow_fractional_shares),
        "as_of_date": dates[idx],
        "cache_manifest_sha16": manifest_sha,
        "equity_usd": round(equity_usd, 2),
        "gross_exposure_pct": round(total_gross_exposure * 100.0, 2),
        "net_exposure_pct": round(total_net_exposure * 100.0, 2),
        "idle_cash_usd": round(idle_cash_usd, 2),
        "idle_cash_pct": round(100.0 * idle_cash_usd / equity_usd, 2),
        "turnover_notional_usd": round(total_turnover_usd, 2),
        "est_oneway_cost_usd": round(est_friction_usd, 2),
        "est_ibkr_comm_usd": round(total_ibkr_comm_usd, 2),
        "est_annual_rebal_events": rebal_events_yr,
        "est_annual_comm_drag_bps": est_annual_comm_drag_bps,
        "min_order_fee_warning": min_order_fee_warning,
        "fee_warning_detail": fee_warning_detail,
        "ticket_count": len(tickets),
        "allocations": allocations,
        "tickets": tickets,
    }


def tickets_to_ibkr_csv(plan: dict[str, Any]) -> str:
    """Serialize dry-run order tickets into legacy IBKR dry-run CSV with explicit DryRunOnly column."""
    cols = [
        "Action", "Quantity", "Symbol", "SecType", "Exchange", "Currency",
        "OrderType", "LmtPrice", "TimeInForce", "OrderRef", "DryRunOnly",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    for t in plan.get("tickets", []):
        writer.writerow({k: t[k] for k in cols})
    return buf.getvalue()


def tickets_to_ibkr_basket_csv(plan: dict[str, Any]) -> str:
    """Serialize dry-run tickets into IBKR TWS BasketTrader-compatible CSV (`OrderSend = 0`)."""
    cols = [
        "Action", "Quantity", "Symbol", "SecType", "Exchange", "Currency",
        "TimeInForce", "OrderType", "BasketTag",
    ]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n")
    writer.writeheader()
    for t in plan.get("tickets", []):
        writer.writerow({k: t[k] for k in cols})
    return buf.getvalue()


def main() -> int:
    ap = argparse.ArgumentParser(description="Naqex Multi-Mode IBKR BasketTrader Dry-Run Rebalancer (OrderSend = 0)")
    ap.add_argument("--mode", default="M5_VOL_PARITY_TREND_GUARD", choices=VALID_MODES)
    ap.add_argument("--equity", type=float, default=25_000.0, help="Legacy alias for --capital-usd")
    ap.add_argument("--capital-usd", type=float, default=None, help="Account capital in USD (overrides --equity)")
    ap.add_argument("--fractional", choices=("on", "off"), default="off", help="Allow IBKR fractional shares (default off)")
    ap.add_argument("--as-of", default=None, help="Optional YYYY-MM-DD cutoff (default latest cached date)")
    ap.add_argument("--min-trade-usd", type=float, default=100.0)
    ap.add_argument("--out-json", type=Path, default=None)
    ap.add_argument("--out-csv", type=Path, default=None)
    ap.add_argument("--out-basket-csv", type=Path, default=None, help="Write IBKR TWS BasketTrader-compatible CSV")
    args = ap.parse_args()

    cap = float(args.capital_usd) if args.capital_usd is not None else float(args.equity)
    plan = generate_rebalance_plan(
        mode=args.mode,
        equity_usd=cap,
        as_of_date=args.as_of,
        min_trade_notional_usd=args.min_trade_usd,
        allow_fractional_shares=(args.fractional == "on"),
    )
    if args.out_json:
        args.out_json.parent.mkdir(parents=True, exist_ok=True)
        args.out_json.write_text(json.dumps(plan, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    if args.out_csv:
        args.out_csv.parent.mkdir(parents=True, exist_ok=True)
        args.out_csv.write_text(tickets_to_ibkr_csv(plan), encoding="utf-8", newline="\n")
    if args.out_basket_csv:
        args.out_basket_csv.parent.mkdir(parents=True, exist_ok=True)
        args.out_basket_csv.write_text(tickets_to_ibkr_basket_csv(plan), encoding="utf-8", newline="\n")
    print(json.dumps({k: v for k, v in plan.items() if k != "allocations"}, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
