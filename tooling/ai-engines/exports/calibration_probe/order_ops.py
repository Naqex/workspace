"""Live demo order entry and close execution helpers with strict fail-closed guards."""

from __future__ import annotations

import time
from datetime import datetime
from typing import Any

from exports.calibration_probe.constants import FIXED_VOLUME_LOTS, PROBE_MAGIC
from exports.calibration_probe.math_schedule import compute_adverse_slippage, estimate_notional_usd
from exports.calibration_probe.models import PlannedCalibrationTrade, SafetyLockError
from exports.calibration_probe.mt5_session import _lookup_deal_details, _pick_filling_mode
from exports.calibration_probe.parsers import append_fill_csv
from exports.calibration_probe.telemetry import build_fill_row
from exports.calibration_probe.validators import (
    assert_safe_portable_path,
    validate_calibration_account,
    validate_fixed_volume,
)


def close_calibration_position(
    runner: Any,
    *,
    pos: Any,
    trade_seq: int,
    exit_reason: str,
    sl_price_orig: float,
) -> dict[str, Any]:
    """Close an open calibration position with account+volume locks and log EXIT telemetry."""
    now_dt = runner._now()
    demo_mode = int(getattr(runner.mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
    acc = runner.mt5.account_info()
    validate_calibration_account(acc, demo_trade_mode=demo_mode)
    if runner.terminal_data_path is not None:
        assert_safe_portable_path(runner.terminal_data_path)

    symbol = str(pos.symbol)
    vol = validate_fixed_volume(float(pos.volume))
    pos_id = int(getattr(pos, "ticket", getattr(pos, "identifier", 0)))
    pos_side = "BUY" if int(pos.type) == 0 else "SELL"
    close_deal_side = "SELL" if pos_side == "BUY" else "BUY"

    si, bid, ask, point, _digits = runner._get_symbol_quote(symbol)
    expected_px = bid if close_deal_side == "SELL" else ask
    mid = 0.5 * (bid + ask)
    spread_pts = round((ask - bid) / point, 1)
    spread_bps = round(((ask - bid) / mid) * 10_000.0, 4)

    if not runner.execute_live:
        raise SafetyLockError("LOCK_6_CLOSE_CALLED_IN_DRY_RUN")

    order_type = (
        int(getattr(runner.mt5, "ORDER_TYPE_SELL", 1))
        if close_deal_side == "SELL"
        else int(getattr(runner.mt5, "ORDER_TYPE_BUY", 0))
    )
    req = {
        "action": int(getattr(runner.mt5, "TRADE_ACTION_DEAL", 1)),
        "symbol": symbol,
        "volume": vol,
        "type": order_type,
        "position": pos_id,
        "price": expected_px,
        "deviation": 30,
        "magic": PROBE_MAGIC,
        "comment": f"NQ_CAL_EXIT_{exit_reason[:12]}",
        "type_time": int(getattr(runner.mt5, "ORDER_TIME_GTC", 0)),
        "type_filling": _pick_filling_mode(runner.mt5, si),
    }

    t0 = time.perf_counter()
    res = runner.mt5.order_send(req)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    runner.order_send_count += 1

    retcode = int(getattr(res, "retcode", -1)) if res is not None else -1
    deal_id = int(getattr(res, "deal", 0)) if res is not None else 0
    order_id = int(getattr(res, "order", 0)) if res is not None else 0
    fill_px = float(getattr(res, "price", 0.0)) if res is not None else 0.0

    deal_obj = _lookup_deal_details(
        runner.mt5,
        deal_ticket=deal_id,
        order_ticket=order_id,
        position_id=pos_id,
        expected_entry_type=int(getattr(runner.mt5, "DEAL_ENTRY_OUT", 1)),
        sleep_fn=runner.sleep_fn,
    )
    if deal_obj is not None:
        if float(getattr(deal_obj, "price", 0.0)) > 0.0:
            fill_px = float(deal_obj.price)
        deal_id = int(getattr(deal_obj, "ticket", deal_id))
        comm_usd = float(getattr(deal_obj, "commission", 0.0)) + float(getattr(deal_obj, "fee", 0.0))
        swap_usd = float(getattr(deal_obj, "swap", 0.0))
        pnl_usd = float(getattr(deal_obj, "profit", 0.0))
    else:
        comm_usd = 0.0
        swap_usd = float(getattr(pos, "swap", 0.0))
        pnl_usd = float(getattr(pos, "profit", 0.0))

    if fill_px > 0.0:
        slip_pts, slip_bps = compute_adverse_slippage(
            deal_side=close_deal_side,
            expected_price=expected_px,
            fill_price=fill_px,
            point=point,
        )
        notional = estimate_notional_usd(symbol=symbol, volume=vol, price=fill_px, usdjpy_ref=runner.usdjpy_last_mid)
        comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
    else:
        slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

    row = build_fill_row(
        now_dt=now_dt,
        trade_seq=trade_seq,
        position_id=pos_id,
        order_id=order_id,
        deal_id=deal_id,
        symbol=symbol,
        leg="EXIT",
        side=close_deal_side,
        position_side=pos_side,
        exit_reason=exit_reason,
        volume=vol,
        pre_bid=bid,
        pre_ask=ask,
        pre_spread_pts=spread_pts,
        pre_spread_bps=spread_bps,
        expected_price=expected_px,
        fill_price=fill_px,
        sl_price=sl_price_orig,
        adverse_slip_pts=slip_pts,
        adverse_slip_bps=slip_bps,
        latency_ms=latency_ms,
        commission_usd=comm_usd,
        commission_bps=comm_bps,
        swap_usd=swap_usd,
        pnl_usd=pnl_usd,
        retcode=retcode,
        dry_run=False,
        comment=f"EXIT_{exit_reason}",
    )
    append_fill_csv(runner.fills_csv_path, row)
    if retcode == int(getattr(runner.mt5, "TRADE_RETCODE_DONE", 10009)):
        runner.live_exits_filled += 1
        print(
            f"[{row['utc_iso']}] EXIT #{trade_seq} {symbol} {close_deal_side} ({exit_reason}) "
            f"fill={fill_px} slip={slip_bps:+.2f}bps comm={comm_usd:+.3f} "
            f"swap={swap_usd:+.3f} pnl={pnl_usd:+.2f} lat={latency_ms}ms",
            flush=True,
        )
    else:
        runner.rejected_orders_count += 1
    return row


def execute_live_entry(
    runner: Any,
    *,
    item: PlannedCalibrationTrade,
    now_dt: datetime,
    si: Any,
    bid: float,
    ask: float,
    point: float,
    entry_expected: float,
    sl_px: float,
    spread_pts: float,
    spread_bps: float,
    next_trade_num: int,
) -> tuple[bool, int]:
    """Submit a live 0.01-lot entry order, log ENTRY/REJECT row, verify hard SL, and return `(filled, pos_id)`."""
    order_type = (
        int(getattr(runner.mt5, "ORDER_TYPE_BUY", 0))
        if item.side == "BUY"
        else int(getattr(runner.mt5, "ORDER_TYPE_SELL", 1))
    )
    req = {
        "action": int(getattr(runner.mt5, "TRADE_ACTION_DEAL", 1)),
        "symbol": item.symbol,
        "volume": FIXED_VOLUME_LOTS,
        "type": order_type,
        "price": entry_expected,
        "sl": sl_px,
        "tp": 0.0,
        "deviation": 30,
        "magic": PROBE_MAGIC,
        "comment": f"NQ_CAL_{item.seq:02d}_{item.side}",
        "type_time": int(getattr(runner.mt5, "ORDER_TIME_GTC", 0)),
        "type_filling": _pick_filling_mode(runner.mt5, si),
    }
    t0 = time.perf_counter()
    res = runner.mt5.order_send(req)
    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    runner.order_send_count += 1

    retcode = int(getattr(res, "retcode", -1)) if res is not None else -1
    done_code = int(getattr(runner.mt5, "TRADE_RETCODE_DONE", 10009))
    deal_id = int(getattr(res, "deal", 0)) if res is not None else 0
    order_id = int(getattr(res, "order", 0)) if res is not None else 0
    fill_px = float(getattr(res, "price", 0.0)) if res is not None else 0.0

    if retcode != done_code:
        runner.rejected_orders_count += 1
        append_fill_csv(
            runner.fills_csv_path,
            build_fill_row(
                now_dt=now_dt,
                trade_seq=item.seq,
                position_id=0,
                order_id=order_id,
                deal_id=deal_id,
                symbol=item.symbol,
                leg="ENTRY_REJECT",
                side=item.side,
                position_side=item.side,
                exit_reason="REJECTED",
                volume=FIXED_VOLUME_LOTS,
                pre_bid=bid,
                pre_ask=ask,
                pre_spread_pts=spread_pts,
                pre_spread_bps=spread_bps,
                expected_price=entry_expected,
                fill_price=fill_px,
                sl_price=sl_px,
                adverse_slip_pts=0.0,
                adverse_slip_bps=0.0,
                latency_ms=latency_ms,
                commission_usd=0.0,
                commission_bps=0.0,
                swap_usd=0.0,
                pnl_usd=0.0,
                retcode=retcode,
                dry_run=False,
                comment=f"REJECT_{getattr(res, 'comment', '')}",
            ),
        )
        return False, 0

    # Resolve opened position FIRST (FTMO Market Execution can return res.price == 0.0 / res.deal == 0!)
    active_pos = None
    pos_id = 0
    for _poll in range(5):
        open_now = runner.mt5.positions_get(symbol=item.symbol) or []
        for p in open_now:
            if int(getattr(p, "magic", 0)) == PROBE_MAGIC:
                active_pos = p
                pos_id = int(getattr(p, "ticket", 0))
                break
        if active_pos is not None:
            break
        runner.sleep_fn(0.1)

    deal_obj = _lookup_deal_details(
        runner.mt5,
        deal_ticket=deal_id,
        order_ticket=order_id,
        position_id=pos_id,
        expected_entry_type=int(getattr(runner.mt5, "DEAL_ENTRY_IN", 0)),
        sleep_fn=runner.sleep_fn,
    )
    if deal_obj is not None:
        if pos_id <= 0:
            pos_id = int(getattr(deal_obj, "position_id", 0))
        if deal_id <= 0:
            deal_id = int(getattr(deal_obj, "ticket", 0))
        if float(getattr(deal_obj, "price", 0.0)) > 0.0:
            fill_px = float(deal_obj.price)
    if fill_px <= 0.0 and active_pos is not None and float(getattr(active_pos, "price_open", 0.0)) > 0.0:
        fill_px = float(active_pos.price_open)
    comm_usd = (
        float(getattr(deal_obj, "commission", 0.0)) + float(getattr(deal_obj, "fee", 0.0))
        if deal_obj is not None
        else 0.0
    )
    swap_usd = float(getattr(deal_obj, "swap", 0.0)) if deal_obj is not None else 0.0

    if fill_px > 0.0:
        slip_pts, slip_bps = compute_adverse_slippage(
            deal_side=item.side,
            expected_price=entry_expected,
            fill_price=fill_px,
            point=point,
        )
        notional = estimate_notional_usd(
            symbol=item.symbol,
            volume=FIXED_VOLUME_LOTS,
            price=fill_px,
            usdjpy_ref=runner.usdjpy_last_mid,
        )
        comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
    else:
        slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

    append_fill_csv(
        runner.fills_csv_path,
        build_fill_row(
            now_dt=now_dt,
            trade_seq=item.seq,
            position_id=pos_id,
            order_id=order_id,
            deal_id=deal_id,
            symbol=item.symbol,
            leg="ENTRY",
            side=item.side,
            position_side=item.side,
            exit_reason="",
            volume=FIXED_VOLUME_LOTS,
            pre_bid=bid,
            pre_ask=ask,
            pre_spread_pts=spread_pts,
            pre_spread_bps=spread_bps,
            expected_price=entry_expected,
            fill_price=fill_px,
            sl_price=sl_px,
            adverse_slip_pts=slip_pts,
            adverse_slip_bps=slip_bps,
            latency_ms=latency_ms,
            commission_usd=comm_usd,
            commission_bps=comm_bps,
            swap_usd=swap_usd,
            pnl_usd=0.0,
            retcode=retcode,
            dry_run=False,
            comment=f"ENTRY_SL{item.sl_units}",
        ),
    )
    runner.live_entries_filled += 1
    print(
        f"[{now_dt.replace(microsecond=0).isoformat()}] ENTRY #{next_trade_num}/{runner.max_trades} "
        f"{item.symbol} {item.side} 0.01 fill={fill_px} sl={sl_px} "
        f"slip={slip_bps:+.2f}bps spread={spread_pts}pts comm={comm_usd:+.3f} "
        f"lat={latency_ms}ms hold={item.hold_sec}s",
        flush=True,
    )

    # Fail-closed check: verify hard SL is attached on open position!
    if active_pos is not None and float(getattr(active_pos, "sl", 0.0)) <= 0.0:
        runner._close_position(
            pos=active_pos,
            trade_seq=item.seq,
            exit_reason="ORPHAN_NO_SL_ABORT",
            sl_price_orig=sl_px,
        )
        raise SafetyLockError(f"LOCK_3_BROKER_DROPPED_SL_ON_{item.symbol}")

    return True, pos_id
