"""Fill row builder, quote/symbol warm-up, and broker-closed exit telemetry."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import datetime
from typing import Any

from exports.calibration_probe.constants import (
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    CORE_SYMBOLS,
    FIXED_VOLUME_LOTS,
)
from exports.calibration_probe.math_schedule import compute_adverse_slippage, estimate_notional_usd
from exports.calibration_probe.mt5_session import _lookup_deal_details
from exports.calibration_probe.parsers import append_fill_csv
from exports.calibration_probe.validators import tag_session_utc


def build_fill_row(
    *,
    now_dt: datetime,
    trade_seq: int,
    position_id: int,
    order_id: int,
    deal_id: int,
    symbol: str,
    leg: str,
    side: str,
    position_side: str,
    exit_reason: str,
    volume: float,
    pre_bid: float,
    pre_ask: float,
    pre_spread_pts: float,
    pre_spread_bps: float,
    expected_price: float,
    fill_price: float,
    sl_price: float,
    adverse_slip_pts: float,
    adverse_slip_bps: float,
    latency_ms: float,
    commission_usd: float,
    commission_bps: float,
    swap_usd: float,
    pnl_usd: float,
    retcode: int,
    dry_run: bool,
    comment: str,
) -> dict[str, Any]:
    """Assemble one canonical fill telemetry row matching `FILLS_CSV_COLUMNS`."""
    return {
        "utc_ts": int(now_dt.timestamp()),
        "utc_iso": now_dt.replace(microsecond=0).isoformat(),
        "session": tag_session_utc(now_dt),
        "account_login": ALLOWED_DEMO_LOGIN,
        "server": ALLOWED_SERVER,
        "trade_seq": trade_seq,
        "position_id": position_id,
        "order_id": order_id,
        "deal_id": deal_id,
        "symbol": symbol,
        "leg": leg,
        "side": side,
        "position_side": position_side,
        "exit_reason": exit_reason,
        "volume": volume,
        "pre_bid": pre_bid,
        "pre_ask": pre_ask,
        "pre_spread_pts": pre_spread_pts,
        "pre_spread_bps": pre_spread_bps,
        "expected_price": expected_price,
        "fill_price": fill_price,
        "sl_price": sl_price,
        "adverse_slip_pts": adverse_slip_pts,
        "adverse_slip_bps": adverse_slip_bps,
        "latency_ms": latency_ms,
        "commission_usd": round(commission_usd, 4),
        "commission_bps": commission_bps,
        "swap_usd": round(swap_usd, 4),
        "pnl_usd": round(pnl_usd, 4),
        "retcode": retcode,
        "dry_run": dry_run,
        "comment": comment,
    }


def warm_up_symbols(
    mt5: Any,
    *,
    sleep_fn: Callable[[float], None],
    timeout_sec: float = 15.0,
) -> None:
    """Select all core symbols in MarketWatch and wait briefly until live Bid/Ask quotes arrive."""
    for sym in CORE_SYMBOLS:
        try:
            mt5.symbol_select(sym, True)
        except Exception:
            pass
    deadline = time.monotonic() + float(timeout_sec)
    while True:
        all_ready = True
        for sym in CORE_SYMBOLS:
            tick = mt5.symbol_info_tick(sym)
            if tick is None or float(getattr(tick, "bid", 0.0)) <= 0.0 or float(getattr(tick, "ask", 0.0)) <= 0.0:
                all_ready = False
                break
        if all_ready or time.monotonic() >= deadline:
            break
        sleep_fn(0.5)


def get_symbol_quote(
    mt5: Any,
    symbol: str,
    *,
    sleep_fn: Callable[[float], None],
    retries: int = 12,
    retry_sleep_sec: float = 0.5,
) -> tuple[Any, float, float, float, int]:
    """Fetch a valid live quote `(symbol_info, bid, ask, point, digits)` with bounded retries."""
    mt5.symbol_select(symbol, True)
    si = None
    bid = ask = point = 0.0
    digits = 5
    for attempt in range(max(1, int(retries))):
        si = mt5.symbol_info(symbol)
        tick = mt5.symbol_info_tick(symbol)
        if si is not None and tick is not None:
            bid = float(tick.bid)
            ask = float(tick.ask)
            point = float(si.point)
            digits = int(si.digits)
            if bid > 0.0 and ask > 0.0 and point > 0.0:
                return si, bid, ask, point, digits
        if attempt < retries - 1:
            sleep_fn(retry_sleep_sec)
    if si is None:
        raise RuntimeError(f"QUOTE_UNAVAILABLE: {symbol}")
    raise RuntimeError(f"INVALID_QUOTE: {symbol} bid={bid} ask={ask} point={point}")


def record_broker_closed_exit(
    runner: Any,
    *,
    trade_seq: int,
    position_id: int,
    symbol: str,
    pos_side: str,
    sl_price: float,
) -> dict[str, Any]:
    """Log EXIT row when broker closed position automatically (e.g., real hard SL hit!)."""
    now_dt = runner._now()
    close_deal_side = "SELL" if pos_side == "BUY" else "BUY"
    _si, bid, ask, point, _digits = runner._get_symbol_quote(symbol)
    mid = 0.5 * (bid + ask)
    spread_pts = round((ask - bid) / point, 1)
    spread_bps = round(((ask - bid) / mid) * 10_000.0, 4)

    deal_obj = _lookup_deal_details(
        runner.mt5,
        position_id=position_id,
        expected_entry_type=int(getattr(runner.mt5, "DEAL_ENTRY_OUT", 1)),
        sleep_fn=runner.sleep_fn,
    )
    reason_code = int(getattr(deal_obj, "reason", -1)) if deal_obj is not None else -1
    deal_reason_sl = int(getattr(runner.mt5, "DEAL_REASON_SL", 4))
    is_sl = reason_code in (deal_reason_sl, -1)
    exit_reason = "SL_HIT" if is_sl else f"BROKER_CLOSE_{reason_code}"

    fill_px = float(getattr(deal_obj, "price", 0.0)) if deal_obj is not None else 0.0
    deal_id = int(getattr(deal_obj, "ticket", 0)) if deal_obj is not None else 0
    order_id = int(getattr(deal_obj, "order", 0)) if deal_obj is not None else 0
    comm_usd = (
        float(getattr(deal_obj, "commission", 0.0)) + float(getattr(deal_obj, "fee", 0.0))
        if deal_obj is not None
        else 0.0
    )
    swap_usd = float(getattr(deal_obj, "swap", 0.0)) if deal_obj is not None else 0.0
    pnl_usd = float(getattr(deal_obj, "profit", 0.0)) if deal_obj is not None else 0.0

    # For real SL execution, expected price is the hard SL trigger price!
    market_close_px = bid if close_deal_side == "SELL" else ask
    expected_px = sl_price if (exit_reason == "SL_HIT" and sl_price > 0.0) else market_close_px
    if fill_px > 0.0 and expected_px > 0.0:
        slip_pts, slip_bps = compute_adverse_slippage(
            deal_side=close_deal_side,
            expected_price=expected_px,
            fill_price=fill_px,
            point=point,
        )
        notional = estimate_notional_usd(
            symbol=symbol,
            volume=FIXED_VOLUME_LOTS,
            price=fill_px,
            usdjpy_ref=runner.usdjpy_last_mid,
        )
        comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
    else:
        slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

    row = build_fill_row(
        now_dt=now_dt,
        trade_seq=trade_seq,
        position_id=position_id,
        order_id=order_id,
        deal_id=deal_id,
        symbol=symbol,
        leg="EXIT",
        side=close_deal_side,
        position_side=pos_side,
        exit_reason=exit_reason,
        volume=FIXED_VOLUME_LOTS,
        pre_bid=bid,
        pre_ask=ask,
        pre_spread_pts=spread_pts,
        pre_spread_bps=spread_bps,
        expected_price=expected_px,
        fill_price=fill_px,
        sl_price=sl_price,
        adverse_slip_pts=slip_pts,
        adverse_slip_bps=slip_bps,
        latency_ms=0.0,
        commission_usd=comm_usd,
        commission_bps=comm_bps,
        swap_usd=swap_usd,
        pnl_usd=pnl_usd,
        retcode=int(getattr(runner.mt5, "TRADE_RETCODE_DONE", 10009)),
        dry_run=False,
        comment=f"BROKER_{exit_reason}",
    )
    append_fill_csv(runner.fills_csv_path, row)
    runner.live_exits_filled += 1
    print(
        f"[{row['utc_iso']}] EXIT #{trade_seq} {symbol} {close_deal_side} (BROKER_{exit_reason}) "
        f"fill={fill_px} slip={slip_bps:+.2f}bps comm={comm_usd:+.3f} swap={swap_usd:+.3f} pnl={pnl_usd:+.2f}",
        flush=True,
    )
    return row
