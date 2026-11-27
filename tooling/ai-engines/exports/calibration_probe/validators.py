"""Fail-closed safety lock validators, session/cutoff helpers, and Holdout SHA guard."""

from __future__ import annotations

import math
import os
import subprocess
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from exports.calibration_probe.constants import (
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    BOJ_ESTIMATED_PAD_SEC,
    CORE_SYMBOLS,
    DEFAULT_HOLDOUT_LOCK_JSON,
    EXPECTED_HOLDOUT_LOCK_SHA,
    FIXED_VOLUME_LOTS,
    FORBIDDEN_LOGINS,
    FORBIDDEN_PATH_TOKENS,
    HARD_FLATTEN_CUTOFF_HOUR,
    HARD_FLATTEN_CUTOFF_MINUTE,
    MAX_OPEN_POSITIONS,
    MAX_TOTAL_TRADES,
    RED_NEWS_BLOCK_WINDOW_SEC,
    RED_NEWS_HARD_BAN_SEC,
    RED_NEWS_PRE_FLATTEN_SEC,
    SYMBOL_META,
    TRADES_PER_SYMBOL,
)
from exports.calibration_probe.models import SafetyLockError
from quant_core.io_utils import sha256_file
from quant_factory import prop_challenge_tracker as pct


def tag_session_utc(utc_dt: datetime) -> str:
    """Tag UTC timestamp into ASIA / LONDON / NY_OVERLAP / NY_AFTERNOON."""
    dt = utc_dt.astimezone(UTC) if utc_dt.tzinfo else utc_dt.replace(tzinfo=UTC)
    h = dt.hour
    if 7 <= h < 12:
        return "LONDON"
    if 12 <= h < 16:
        return "NY_OVERLAP"
    if 16 <= h < 21:
        return "NY_AFTERNOON"
    return "ASIA"


def is_past_flatten_cutoff(utc_dt: datetime, *, hold_lookahead_sec: int = 0) -> bool:
    """Return True if now (or now + hold_lookahead_sec) is at/past 20:55 UTC (or crosses UTC midnight)."""
    dt = utc_dt.astimezone(UTC) if utc_dt.tzinfo else utc_dt.replace(tzinfo=UTC)
    cutoff_mins = HARD_FLATTEN_CUTOFF_HOUR * 60 + HARD_FLATTEN_CUTOFF_MINUTE
    now_mins = dt.hour * 60 + dt.minute
    if now_mins >= cutoff_mins:
        return True
    if hold_lookahead_sec > 0:
        end_dt = dt + timedelta(seconds=int(hold_lookahead_sec))
        if end_dt.date() != dt.date():
            return True
        end_mins = end_dt.hour * 60 + end_dt.minute
        if end_mins >= cutoff_mins:
            return True
    return False


def find_blocking_red_news(
    symbol: str,
    now_utc_ts: int,
    news_events: list[dict[str, Any]],
    *,
    window_sec: int = RED_NEWS_BLOCK_WINDOW_SEC,
    hold_lookahead_sec: int = 0,
) -> dict[str, Any] | None:
    """Return the first matching-currency red-news event blocking `[now, now+hold_lookahead]` within `+-window_sec`."""
    if not news_events:
        raise SafetyLockError("LOCK_4_EMPTY_RED_NEWS_EVENTS")
    sym_ccys = pct._symbol_currencies(symbol)
    t_start = int(now_utc_ts)
    t_end = t_start + max(0, int(hold_lookahead_sec))
    for ev in news_events:
        if ev["ccy"] not in sym_ccys:
            continue
        pad = BOJ_ESTIMATED_PAD_SEC if "EST03UTC" in str(ev.get("event", "")).upper() else int(window_sec)
        ev_ts = int(ev["utc_ts"])
        # Interval overlap between [t_start, t_end] and [ev_ts - pad, ev_ts + pad]
        if t_end >= (ev_ts - pad) and t_start <= (ev_ts + pad):
            return {
                "utc_ts": ev_ts,
                "ccy": ev["ccy"],
                "event": ev["event"],
                "pad_sec": pad,
                "signed_delta_sec": ev_ts - t_start,
            }
    return None


def find_approaching_pre_flatten_news(
    symbol: str,
    now_utc_ts: int,
    news_events: list[dict[str, Any]],
    *,
    pre_flatten_sec: int = RED_NEWS_PRE_FLATTEN_SEC,
    hard_ban_sec: int = RED_NEWS_HARD_BAN_SEC,
) -> dict[str, Any] | None:
    """Detect upcoming matching red-news event approaching while a position is open."""
    if not news_events:
        return None
    sym_ccys = pct._symbol_currencies(symbol)
    t_now = int(now_utc_ts)
    for ev in news_events:
        if ev["ccy"] not in sym_ccys:
            continue
        ev_ts = int(ev["utc_ts"])
        signed_before = ev_ts - t_now
        if hard_ban_sec < signed_before <= pre_flatten_sec:
            return {
                "utc_ts": ev_ts,
                "ccy": ev["ccy"],
                "event": ev["event"],
                "seconds_until_news": signed_before,
            }
    return None


def assert_safe_portable_path(path: Path) -> None:
    norm = str(Path(path).resolve(strict=False)).lower()
    norm_slash = norm.replace("\\", "/")
    for tok in FORBIDDEN_PATH_TOKENS:
        if tok in norm or tok in norm_slash:
            raise SafetyLockError(f"LOCK_2_FORBIDDEN_TERMINAL_PATH: {path}")


def list_running_terminal_processes() -> list[str]:
    """Return list of running `terminal64.exe` process entries via Windows `tasklist`."""
    if os.name != "nt":
        return []
    proc = subprocess.run(
        ["tasklist", "/FI", "IMAGENAME eq terminal64.exe", "/FO", "CSV", "/NH"],
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    out: list[str] = []
    for line in proc.stdout.splitlines():
        s = line.strip()
        if s and "terminal64.exe" in s.lower():
            out.append(s)
    return out


def assert_no_concurrent_mt5(
    process_lister: Callable[[], list[str]] = list_running_terminal_processes,
) -> None:
    running = process_lister()
    if running:
        raise SafetyLockError(
            f"LOCK_2_CONCURRENT_TERMINAL64_RUNNING: detected {len(running)} active terminal64.exe process(es); "
            "refusing to launch a second MT5 terminal concurrently!"
        )


def validate_calibration_account(
    acc: Any,
    *,
    demo_trade_mode: int = 0,
) -> dict[str, Any]:
    """Lock 2: Assert Demo trade_mode, exact login 1515343318 (never 1515343166), and FTMO-Demo server."""
    if acc is None:
        raise SafetyLockError("LOCK_2_ACCOUNT_INFO_NONE")
    if int(acc.trade_mode) != int(demo_trade_mode):
        raise SafetyLockError(
            f"LOCK_2_NOT_DEMO_ACCOUNT: trade_mode={acc.trade_mode} != ACCOUNT_TRADE_MODE_DEMO({demo_trade_mode})"
        )
    login = int(acc.login)
    if login in FORBIDDEN_LOGINS:
        raise SafetyLockError(f"LOCK_2_FORBIDDEN_PRIMARY_DEMO_LOGIN: refusing to touch {login}")
    if login != ALLOWED_DEMO_LOGIN:
        raise SafetyLockError(f"LOCK_2_UNEXPECTED_LOGIN: {login} != {ALLOWED_DEMO_LOGIN}")
    server = str(acc.server)
    if server != ALLOWED_SERVER:
        raise SafetyLockError(f"LOCK_2_UNEXPECTED_SERVER: {server!r} != {ALLOWED_SERVER!r}")
    return {
        "login": login,
        "server": server,
        "trade_mode": "ACCOUNT_TRADE_MODE_DEMO",
        "currency": str(getattr(acc, "currency", "USD")),
        "balance": round(float(getattr(acc, "balance", 0.0)), 2),
        "equity": round(float(getattr(acc, "equity", 0.0)), 2),
        "profit": round(float(getattr(acc, "profit", 0.0)), 2),
        "margin": round(float(getattr(acc, "margin", 0.0)), 2),
        "margin_free": round(float(getattr(acc, "margin_free", 0.0)), 2),
        "leverage": int(getattr(acc, "leverage", 0)),
        "trade_allowed": bool(getattr(acc, "trade_allowed", False)),
        "trade_expert": bool(getattr(acc, "trade_expert", False)),
    }


def validate_fixed_volume(volume: float) -> float:
    """Lock 3a: Hard-lock lot size strictly == 0.01."""
    try:
        v = float(volume)
    except (TypeError, ValueError) as exc:
        raise SafetyLockError(f"LOCK_3_INVALID_VOLUME: {volume!r}") from exc
    if not math.isfinite(v) or abs(v - FIXED_VOLUME_LOTS) > 1e-9:
        raise SafetyLockError(f"LOCK_3_VOLUME_LOCK_BREACH: {v} != {FIXED_VOLUME_LOTS}")
    return FIXED_VOLUME_LOTS


def validate_mandatory_sl(
    *,
    symbol: str,
    side: str,
    entry_price: float,
    sl_price: float,
    point: float,
    stops_level_pts: int = 0,
) -> float:
    """Lock 3b: Enforce mandatory valid hard SL in safe calibration distance band."""
    if symbol not in SYMBOL_META:
        raise SafetyLockError(f"LOCK_3_UNSUPPORTED_SYMBOL: {symbol!r}")
    side_u = str(side).upper()
    if side_u not in ("BUY", "SELL"):
        raise SafetyLockError(f"LOCK_3_INVALID_SIDE: {side!r}")
    if not (math.isfinite(entry_price) and entry_price > 0.0):
        raise SafetyLockError(f"LOCK_3_INVALID_ENTRY_PRICE: {entry_price!r}")
    if not (math.isfinite(sl_price) and sl_price > 0.0):
        raise SafetyLockError(f"LOCK_3_MISSING_OR_ZERO_SL: sl={sl_price!r}")

    signed_dist = (entry_price - sl_price) if side_u == "BUY" else (sl_price - entry_price)
    if signed_dist <= 0.0:
        raise SafetyLockError(f"LOCK_3_WRONG_SIDE_SL: side={side_u} entry={entry_price} sl={sl_price}")

    meta = SYMBOL_META[symbol]
    dist_units = signed_dist / float(meta["pip_size"])
    if dist_units < float(meta["sl_min_units"]) - 1e-6 or dist_units > float(meta["sl_max_units"]) + 1e-6:
        raise SafetyLockError(
            f"LOCK_3_SL_OUT_OF_CALIBRATION_BAND: {symbol} dist={dist_units:.2f} "
            f"not in [{meta['sl_min_units']}, {meta['sl_max_units']}]"
        )

    min_stop_px = max(0, int(stops_level_pts)) * float(point)
    if min_stop_px > 0.0 and signed_dist < min_stop_px:
        raise SafetyLockError(f"LOCK_3_SL_INSIDE_BROKER_STOPS_LEVEL: dist={signed_dist:.6f} < {min_stop_px:.6f}")
    return float(sl_price)


def assert_all_entry_locks(
    *,
    acc: Any,
    demo_trade_mode: int,
    symbol: str,
    side: str,
    volume: float,
    entry_price: float,
    sl_price: float,
    point: float,
    stops_level_pts: int,
    open_positions: Any,
    total_trades_opened: int,
    per_symbol_counts: dict[str, int],
    now_utc: datetime,
    hold_sec: int,
    news_events: list[dict[str, Any]],
    terminal_data_path: Path | None = None,
) -> dict[str, Any]:
    """Run ALL 6 fail-closed safety locks before ANY entry order is permitted."""
    if terminal_data_path is not None:
        assert_safe_portable_path(terminal_data_path)

    acct_info = validate_calibration_account(acc, demo_trade_mode=demo_trade_mode)
    validate_fixed_volume(volume)

    if symbol not in CORE_SYMBOLS:
        raise SafetyLockError(f"LOCK_3_SYMBOL_NOT_IN_CORE4: {symbol!r}")
    if total_trades_opened >= MAX_TOTAL_TRADES:
        raise SafetyLockError(f"LOCK_3_MAX_TOTAL_TRADES_REACHED: {total_trades_opened} >= {MAX_TOTAL_TRADES}")
    sym_count = int(per_symbol_counts.get(symbol, 0))
    if sym_count >= TRADES_PER_SYMBOL:
        raise SafetyLockError(f"LOCK_3_MAX_SYMBOL_TRADES_REACHED: {symbol} count={sym_count} >= {TRADES_PER_SYMBOL}")

    if open_positions is None:
        raise SafetyLockError("LOCK_3_POSITIONS_GET_RETURNED_NONE")
    if len(open_positions) >= MAX_OPEN_POSITIONS:
        raise SafetyLockError(f"LOCK_3_MAX_OPEN_POSITIONS_BREACH: open={len(open_positions)} >= {MAX_OPEN_POSITIONS}")

    validate_mandatory_sl(
        symbol=symbol,
        side=side,
        entry_price=entry_price,
        sl_price=sl_price,
        point=point,
        stops_level_pts=stops_level_pts,
    )

    now_ts = int(now_utc.timestamp())
    blocking_news = find_blocking_red_news(
        symbol,
        now_ts,
        news_events,
        window_sec=RED_NEWS_BLOCK_WINDOW_SEC,
        hold_lookahead_sec=hold_sec,
    )
    if blocking_news is not None:
        raise SafetyLockError(
            f"LOCK_4_RED_NEWS_WINDOW_BLOCK: {symbol} near {blocking_news['ccy']} "
            f"{blocking_news['event']} (delta={blocking_news['signed_delta_sec']}s, "
            f"pad=+-{blocking_news['pad_sec']}s)"
        )

    if is_past_flatten_cutoff(now_utc, hold_lookahead_sec=hold_sec):
        raise SafetyLockError(f"LOCK_5_PAST_2055_UTC_CUTOFF: now={now_utc.isoformat()} hold_sec={hold_sec}")

    return acct_info


def assert_holdout_lock_intact(lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON) -> str:
    """Verify the sealed Holdout lock JSON exists and matches the expected SHA-256 digest."""
    if not lock_path.is_file():
        raise SafetyLockError(f"HOLDOUT_LOCK_MISSING: {lock_path}")
    digest = sha256_file(lock_path)
    if digest != EXPECTED_HOLDOUT_LOCK_SHA:
        raise SafetyLockError(f"HOLDOUT_LOCK_SHA_MISMATCH: {digest} != {EXPECTED_HOLDOUT_LOCK_SHA}")
    return digest
