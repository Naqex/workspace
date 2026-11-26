"""Adverse slippage math, SL pricing, notional normalization, and deterministic 28-trade schedule."""

from __future__ import annotations

from exports.calibration_probe.constants import (
    CORE_SYMBOLS,
    FIXED_VOLUME_LOTS,
    MAX_TOTAL_TRADES,
    SYMBOL_META,
    TRADES_PER_SYMBOL,
)
from exports.calibration_probe.models import PlannedCalibrationTrade


def compute_adverse_slippage(
    *,
    deal_side: str,
    expected_price: float,
    fill_price: float,
    point: float,
) -> tuple[float, float]:
    """Return `(adverse_slip_pts, adverse_slip_bps)` using strict execution/deal side convention.

    - BUY deal (opening LONG or closing SHORT): pays Ask -> adverse when `fill_price > expected_price`.
    - SELL deal (opening SHORT or closing LONG): hits Bid -> adverse when `fill_price < expected_price`.
    Positive = adverse (worse execution); Negative = favorable price improvement.
    """
    side_u = str(deal_side).upper()
    if side_u not in ("BUY", "SELL"):
        raise ValueError(f"Unknown deal_side: {deal_side!r}")
    if expected_price <= 0.0 or fill_price <= 0.0 or point <= 0.0:
        raise ValueError(f"Non-positive price/point: exp={expected_price}, fill={fill_price}, pt={point}")
    adverse_px = (fill_price - expected_price) if side_u == "BUY" else (expected_price - fill_price)
    adverse_pts = adverse_px / point
    adverse_bps = (adverse_px / expected_price) * 10_000.0
    return round(float(adverse_pts), 3), round(float(adverse_bps), 4)


def compute_sl_price(
    *,
    symbol: str,
    side: str,
    entry_price: float,
    sl_units: float,
    digits: int,
) -> float:
    """Compute exact broker-rounded SL price from pip/index-point distance."""
    meta = SYMBOL_META[symbol]
    dist_px = float(sl_units) * float(meta["pip_size"])
    raw = (entry_price - dist_px) if side.upper() == "BUY" else (entry_price + dist_px)
    return round(float(raw), int(digits))


def estimate_notional_usd(
    *,
    symbol: str,
    volume: float,
    price: float,
    usdjpy_ref: float = 155.0,
) -> float:
    """Estimate trade USD notional for commission-in-bps normalization."""
    meta = SYMBOL_META[symbol]
    cs = float(meta["contract_size"])
    if symbol == "US100.cash":
        return max(1e-6, float(volume) * cs * float(price))
    if symbol == "USDJPY":
        return max(1e-6, float(volume) * cs)  # Base currency is USD
    if symbol == "GBPUSD":
        return max(1e-6, float(volume) * cs * float(price))  # Quote currency is USD
    if symbol == "EURJPY":
        # 1 lot EURJPY = 100,000 EUR = (100,000 * EURJPY / USDJPY) USD
        return max(1e-6, float(volume) * cs * (float(price) / max(1.0, float(usdjpy_ref))))
    return max(1e-6, float(volume) * cs * float(price))


def build_calibration_schedule(
    max_trades: int = MAX_TOTAL_TRADES,
    *,
    gap_sec_override: int | None = None,
) -> list[PlannedCalibrationTrade]:
    """Build deterministic interleaved 28-trade plan (7x4 core symbols, 14 BUY / 14 SELL, 3-6m hold, 2-3m+ gap)."""
    cap = min(MAX_TOTAL_TRADES, max(1, int(max_trades)))
    hold_cycle = (180, 240, 300, 360, 210, 270, 330)
    gap_cycle = (120, 150, 180, 135, 165, 120, 150)

    plan: list[PlannedCalibrationTrade] = []
    seq = 0
    for round_idx in range(TRADES_PER_SYMBOL):
        for sym_idx, sym in enumerate(CORE_SYMBOLS):
            seq += 1
            if seq > cap:
                return plan
            side = "BUY" if ((round_idx + sym_idx) % 2 == 0) else "SELL"
            sl_units = float(SYMBOL_META[sym]["sl_schedule_units"][round_idx])
            default_gap = int(gap_cycle[(round_idx + sym_idx) % len(gap_cycle)])
            gap_s = int(gap_sec_override) if gap_sec_override is not None else default_gap
            plan.append(
                PlannedCalibrationTrade(
                    seq=seq,
                    symbol=sym,
                    side=side,
                    volume=FIXED_VOLUME_LOTS,
                    sl_units=sl_units,
                    hold_sec=int(hold_cycle[(round_idx + sym_idx) % len(hold_cycle)]),
                    gap_sec=max(60, gap_s),
                )
            )
    return plan
