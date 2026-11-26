"""CalibrationProbeRunner orchestrator (28 bounded 0.01-lot trades + 5s live spread logging)."""

from __future__ import annotations

import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from exports.calibration_probe.constants import (
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    CORE_SYMBOLS,
    DEFAULT_FILLS_CSV,
    DEFAULT_SPREAD_LOG,
    FIXED_VOLUME_LOTS,
    MAX_TOTAL_TRADES,
    PROBE_MAGIC,
    RED_NEWS_BLOCK_WINDOW_SEC,
    SPREAD_SAMPLE_INTERVAL_SEC,
    TRADES_PER_SYMBOL,
)
from exports.calibration_probe.math_schedule import build_calibration_schedule, compute_sl_price
from exports.calibration_probe.models import PlannedCalibrationTrade
from exports.calibration_probe.mt5_session import capture_spread_snapshot
from exports.calibration_probe.order_ops import close_calibration_position, execute_live_entry
from exports.calibration_probe.parsers import append_fill_csv, append_jsonl, load_existing_live_entry_counts
from exports.calibration_probe.telemetry import (
    build_fill_row,
    get_symbol_quote,
    record_broker_closed_exit,
    warm_up_symbols,
)
from exports.calibration_probe.validators import (
    assert_all_entry_locks,
    assert_safe_portable_path,
    find_approaching_pre_flatten_news,
    find_blocking_red_news,
    is_past_flatten_cutoff,
    validate_calibration_account,
)


class CalibrationProbeRunner:
    """Orchestrates 28 bounded 0.01-lot calibration trades + continuous 5s spread logging."""

    def __init__(
        self,
        *,
        mt5: Any,
        execute_live: bool = False,
        news_events: list[dict[str, Any]],
        spread_log_path: Path = DEFAULT_SPREAD_LOG,
        fills_csv_path: Path = DEFAULT_FILLS_CSV,
        sample_interval_sec: int = SPREAD_SAMPLE_INTERVAL_SEC,
        max_trades: int = MAX_TOTAL_TRADES,
        gap_sec_override: int | None = None,
        max_runtime_sec: int | None = None,
        terminal_data_path: Path | None = None,
        clock_fn: Callable[[], datetime] | None = None,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> None:
        self.mt5 = mt5
        self.execute_live = bool(execute_live)
        self.news_events = news_events
        self.spread_log_path = Path(spread_log_path)
        self.fills_csv_path = Path(fills_csv_path)
        self.sample_interval_sec = max(1, int(sample_interval_sec))
        self.max_trades = min(MAX_TOTAL_TRADES, max(1, int(max_trades)))
        self.gap_sec_override = gap_sec_override
        self.max_runtime_sec = max_runtime_sec
        self.terminal_data_path = terminal_data_path
        self.clock_fn = clock_fn or (lambda: datetime.now(UTC))
        self.sleep_fn = sleep_fn

        self.order_send_count = 0
        self.spread_samples_logged = 0
        self.dryrun_intents_logged = 0
        self.live_entries_filled = 0
        self.live_exits_filled = 0
        self.blocked_red_news_count = 0
        self.blocked_cutoff_count = 0
        self.rejected_orders_count = 0
        self.usdjpy_last_mid = 155.0

    def _now(self) -> datetime:
        dt = self.clock_fn()
        return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)

    def _record_spread(self) -> dict[str, Any]:
        snap = capture_spread_snapshot(
            self.mt5,
            symbols=CORE_SYMBOLS,
            now_utc=self._now(),
        )
        q_jpy = snap.get("quotes", {}).get("USDJPY", {})
        if q_jpy.get("available") and q_jpy.get("bid", 0.0) > 0.0 and q_jpy.get("ask", 0.0) > 0.0:
            self.usdjpy_last_mid = 0.5 * (float(q_jpy["bid"]) + float(q_jpy["ask"]))
        append_jsonl(self.spread_log_path, snap)
        self.spread_samples_logged += 1
        return snap

    def _warm_up_symbols(self, *, timeout_sec: float = 15.0) -> None:
        """Select all core symbols in MarketWatch and wait briefly until live Bid/Ask quotes arrive."""
        warm_up_symbols(self.mt5, sleep_fn=self.sleep_fn, timeout_sec=timeout_sec)

    def _get_symbol_quote(
        self,
        symbol: str,
        *,
        retries: int = 12,
        retry_sleep_sec: float = 0.5,
    ) -> tuple[Any, float, float, float, int]:
        return get_symbol_quote(
            self.mt5,
            symbol,
            sleep_fn=self.sleep_fn,
            retries=retries,
            retry_sleep_sec=retry_sleep_sec,
        )

    def _close_position(
        self,
        *,
        pos: Any,
        trade_seq: int,
        exit_reason: str,
        sl_price_orig: float,
    ) -> dict[str, Any]:
        """Close an open calibration position with account+volume locks and log EXIT telemetry."""
        return close_calibration_position(
            self,
            pos=pos,
            trade_seq=trade_seq,
            exit_reason=exit_reason,
            sl_price_orig=sl_price_orig,
        )

    def _record_broker_closed_exit(
        self,
        *,
        trade_seq: int,
        position_id: int,
        symbol: str,
        pos_side: str,
        sl_price: float,
    ) -> dict[str, Any]:
        """Log EXIT row when broker closed position automatically (e.g., real hard SL hit!)."""
        return record_broker_closed_exit(
            self,
            trade_seq=trade_seq,
            position_id=position_id,
            symbol=symbol,
            pos_side=pos_side,
            sl_price=sl_price,
        )

    def flatten_any_probe_positions(self, *, exit_reason: str = "EMERGENCY_FLATTEN") -> int:
        """Flatten any open positions belonging to PROBE_MAGIC when execute_live=True."""
        if not self.execute_live:
            return 0
        positions = self.mt5.positions_get() or []
        closed = 0
        for pos in positions:
            if int(getattr(pos, "magic", 0)) == PROBE_MAGIC:
                self._close_position(
                    pos=pos,
                    trade_seq=0,
                    exit_reason=exit_reason,
                    sl_price_orig=float(getattr(pos, "sl", 0.0)),
                )
                closed += 1
        return closed

    def run_spread_only(self, *, max_samples: int = 1, duration_sec: int | None = None) -> dict[str, Any]:
        """Run strictly MUI 2 (5s spread recorder, OrderSend=0)."""
        self._warm_up_symbols()
        t_start = time.monotonic()
        taken = 0
        while True:
            self._record_spread()
            taken += 1
            if max_samples > 0 and taken >= max_samples:
                break
            if duration_sec is not None and (time.monotonic() - t_start) >= duration_sec:
                break
            self.sleep_fn(self.sample_interval_sec)
        return {
            "mode": "SPREAD_ONLY",
            "order_send_count": 0,
            "spread_samples_logged": self.spread_samples_logged,
            "spread_log_path": str(self.spread_log_path),
        }

    def _find_open_position(self, pos_id: int) -> Any | None:
        cur_positions = self.mt5.positions_get() or []
        return next(
            (
                p
                for p in cur_positions
                if int(getattr(p, "ticket", -1)) == pos_id
                or (pos_id <= 0 and int(getattr(p, "magic", 0)) == PROBE_MAGIC)
            ),
            None,
        )

    def _run_hold_window(self, *, item: PlannedCalibrationTrade, pos_id: int, sl_px: float) -> bool:
        """Monitor open position during hold window; return True if 20:55 UTC cutoff terminated the run."""
        elapsed_hold = 0
        closed_already = False
        while elapsed_hold < item.hold_sec:
            step = min(self.sample_interval_sec, item.hold_sec - elapsed_hold)
            self.sleep_fn(step)
            elapsed_hold += step
            self._record_spread()

            still_open = self._find_open_position(pos_id)
            if still_open is None:
                self._record_broker_closed_exit(
                    trade_seq=item.seq,
                    position_id=pos_id,
                    symbol=item.symbol,
                    pos_side=item.side,
                    sl_price=sl_px,
                )
                closed_already = True
                break

            cur_dt = self._now()
            if is_past_flatten_cutoff(cur_dt):
                self.blocked_cutoff_count += 1
                self._close_position(
                    pos=still_open,
                    trade_seq=item.seq,
                    exit_reason="PRE_FLATTEN_UTC_CUTOFF",
                    sl_price_orig=sl_px,
                )
                return True

            if find_approaching_pre_flatten_news(item.symbol, int(cur_dt.timestamp()), self.news_events):
                self._close_position(
                    pos=still_open,
                    trade_seq=item.seq,
                    exit_reason="PRE_FLATTEN_NEWS",
                    sl_price_orig=sl_px,
                )
                closed_already = True
                break

        if not closed_already:
            still_open = self._find_open_position(pos_id)
            if still_open is not None:
                self._close_position(
                    pos=still_open,
                    trade_seq=item.seq,
                    exit_reason="TIME_EXIT",
                    sl_price_orig=sl_px,
                )
            else:
                self._record_broker_closed_exit(
                    trade_seq=item.seq,
                    position_id=pos_id,
                    symbol=item.symbol,
                    pos_side=item.side,
                    sl_price=sl_px,
                )
        return False

    def run_calibration(self, *, schedule: list[PlannedCalibrationTrade] | None = None) -> dict[str, Any]:
        """Execute full calibration schedule (or dry-run simulation) with embedded 5s spread logging."""
        plan = (
            list(schedule)
            if schedule is not None
            else build_calibration_schedule(self.max_trades, gap_sec_override=self.gap_sec_override)
        )
        demo_mode = int(getattr(self.mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
        started_mono = time.monotonic()

        # Initial identity check + MarketWatch warm-up + initial spread sample
        validate_calibration_account(self.mt5.account_info(), demo_trade_mode=demo_mode)
        if self.terminal_data_path is not None:
            assert_safe_portable_path(self.terminal_data_path)
        self._warm_up_symbols()
        self._record_spread()

        total_opened, per_sym_counts = (
            load_existing_live_entry_counts(self.fills_csv_path)
            if self.execute_live
            else (0, {s: 0 for s in CORE_SYMBOLS})
        )

        # Build pending queue (skipping symbol slots already filled on prior resumed run)
        pending: list[PlannedCalibrationTrade] = []
        planned_per_sym = dict(per_sym_counts)
        for item in plan:
            if len(pending) + total_opened >= self.max_trades:
                break
            if planned_per_sym.get(item.symbol, 0) >= TRADES_PER_SYMBOL:
                continue
            pending.append(item)
            planned_per_sym[item.symbol] = planned_per_sym.get(item.symbol, 0) + 1

        try:
            while pending and total_opened < self.max_trades:
                if self.max_runtime_sec is not None and (time.monotonic() - started_mono) >= self.max_runtime_sec:
                    break

                now_dt = self._now()
                # Pick first pending trade not currently blocked by red news (deferring blocked symbols cleanly!)
                chosen_idx: int | None = None
                for idx, cand in enumerate(pending):
                    if is_past_flatten_cutoff(now_dt, hold_lookahead_sec=cand.hold_sec):
                        continue
                    if (
                        find_blocking_red_news(
                            cand.symbol,
                            int(now_dt.timestamp()),
                            self.news_events,
                            window_sec=RED_NEWS_BLOCK_WINDOW_SEC,
                            hold_lookahead_sec=cand.hold_sec,
                        )
                        is None
                    ):
                        chosen_idx = idx
                        break

                if chosen_idx is None:
                    # Check if blocked by 20:55 UTC cutoff vs temporary red-news blackout
                    if all(is_past_flatten_cutoff(now_dt, hold_lookahead_sec=c.hold_sec) for c in pending):
                        self.blocked_cutoff_count += 1
                        self.flatten_any_probe_positions(exit_reason="PRE_FLATTEN_UTC_CUTOFF")
                        break
                    self.blocked_red_news_count += 1
                    if not self.execute_live:
                        break
                    # Wait out red-news blackout in 5s spread-recording steps
                    self.sleep_fn(self.sample_interval_sec)
                    self._record_spread()
                    continue

                item = pending.pop(chosen_idx)
                if per_sym_counts.get(item.symbol, 0) >= TRADES_PER_SYMBOL:
                    continue

                si, bid, ask, point, digits = self._get_symbol_quote(item.symbol)
                entry_expected = ask if item.side == "BUY" else bid
                sl_px = compute_sl_price(
                    symbol=item.symbol,
                    side=item.side,
                    entry_price=entry_expected,
                    sl_units=item.sl_units,
                    digits=digits,
                )
                mid = 0.5 * (bid + ask)
                spread_pts = round((ask - bid) / point, 1)
                spread_bps = round(((ask - bid) / mid) * 10_000.0, 4)

                # Run ALL 6 HARD LOCKS right before every single order!
                assert_all_entry_locks(
                    acc=self.mt5.account_info(),
                    demo_trade_mode=demo_mode,
                    symbol=item.symbol,
                    side=item.side,
                    volume=item.volume,
                    entry_price=entry_expected,
                    sl_price=sl_px,
                    point=point,
                    stops_level_pts=int(getattr(si, "trade_stops_level", 0)),
                    open_positions=self.mt5.positions_get(),
                    total_trades_opened=total_opened,
                    per_symbol_counts=per_sym_counts,
                    now_utc=now_dt,
                    hold_sec=item.hold_sec,
                    news_events=self.news_events,
                    terminal_data_path=self.terminal_data_path,
                )

                # Lock 6: Dry-run sends ZERO broker orders!
                if not self.execute_live:
                    append_fill_csv(
                        self.fills_csv_path,
                        build_fill_row(
                            now_dt=now_dt,
                            trade_seq=item.seq,
                            position_id=0,
                            order_id=0,
                            deal_id=0,
                            symbol=item.symbol,
                            leg="DRYRUN_INTENT",
                            side=item.side,
                            position_side=item.side,
                            exit_reason="DRY_RUN",
                            volume=FIXED_VOLUME_LOTS,
                            pre_bid=bid,
                            pre_ask=ask,
                            pre_spread_pts=spread_pts,
                            pre_spread_bps=spread_bps,
                            expected_price=entry_expected,
                            fill_price=0.0,
                            sl_price=sl_px,
                            adverse_slip_pts=0.0,
                            adverse_slip_bps=0.0,
                            latency_ms=0.0,
                            commission_usd=0.0,
                            commission_bps=0.0,
                            swap_usd=0.0,
                            pnl_usd=0.0,
                            retcode=0,
                            dry_run=True,
                            comment=f"DRYRUN_HOLD{item.hold_sec}S_SL{item.sl_units}",
                        ),
                    )
                    self.dryrun_intents_logged += 1
                    total_opened += 1
                    per_sym_counts[item.symbol] = per_sym_counts.get(item.symbol, 0) + 1
                    self._record_spread()
                    continue

                filled, pos_id = execute_live_entry(
                    self,
                    item=item,
                    now_dt=now_dt,
                    si=si,
                    bid=bid,
                    ask=ask,
                    point=point,
                    entry_expected=entry_expected,
                    sl_px=sl_px,
                    spread_pts=spread_pts,
                    spread_bps=spread_bps,
                    next_trade_num=total_opened + 1,
                )
                if not filled:
                    continue

                total_opened += 1
                per_sym_counts[item.symbol] = per_sym_counts.get(item.symbol, 0) + 1

                if self._run_hold_window(item=item, pos_id=pos_id, sl_px=sl_px):
                    return self._summary_dict()

                # Inter-trade gap: continue 5s spread logging while waiting
                if total_opened < self.max_trades and item.gap_sec > 0:
                    elapsed_gap = 0
                    while elapsed_gap < item.gap_sec:
                        if is_past_flatten_cutoff(self._now()):
                            self.blocked_cutoff_count += 1
                            return self._summary_dict()
                        step = min(self.sample_interval_sec, item.gap_sec - elapsed_gap)
                        self.sleep_fn(step)
                        elapsed_gap += step
                        self._record_spread()
        finally:
            if self.execute_live:
                try:
                    self.flatten_any_probe_positions(exit_reason="SHUTDOWN_FLATTEN")
                except Exception:
                    pass

        return self._summary_dict()

    def _summary_dict(self) -> dict[str, Any]:
        return {
            "mode": "LIVE_DEMO_1515343318" if self.execute_live else "DRY_RUN",
            "account_login": ALLOWED_DEMO_LOGIN,
            "server": ALLOWED_SERVER,
            "order_send_count": self.order_send_count,
            "spread_samples_logged": self.spread_samples_logged,
            "dryrun_intents_logged": self.dryrun_intents_logged,
            "live_entries_filled": self.live_entries_filled,
            "live_exits_filled": self.live_exits_filled,
            "blocked_red_news_count": self.blocked_red_news_count,
            "blocked_cutoff_count": self.blocked_cutoff_count,
            "rejected_orders_count": self.rejected_orders_count,
            "spread_log_path": str(self.spread_log_path),
            "fills_csv_path": str(self.fills_csv_path),
        }
