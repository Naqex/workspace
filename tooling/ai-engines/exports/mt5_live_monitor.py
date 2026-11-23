"""Fail-Closed FTMO-Demo Live Telemetry Monitor (`mt5_live_monitor.py`).

Connects read-only via the `MetaTrader5` Python API to the dedicated FTMO-Demo portable
terminal (`D:\\ANNAM\\TradingWorkspace\\.runtime\\ftmo-demo-portable-1515343166\\terminal64.exe`).

ABSOLUTE SAFETY INVARIANTS:
  - Asserts `account_info().trade_mode == ACCOUNT_TRADE_MODE_DEMO`
  - Asserts `account_info().server == "FTMO-Demo"` and `login == 1515343166`
  - Refuses ANY path pointing to `C:\\Program Files\\MetaTrader 5` (Exness Real)
  - NEVER calls `mt5.order_send()` — strictly read-only telemetry logger!
  - Logs live bid/ask/spread_pts, account equity/balance/margin, open Naqex positions,
    orphan no-SL check, and `naqex_heartbeat.json` freshness every 60s to
    `.runtime/live-overnight/mt5_live_spread_log.jsonl`.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parent
REPO_ROOT = EXPORTS_DIR.parents[2]
DEFAULT_PORTABLE_ROOT = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166"
DEFAULT_TERMINAL_PATH = DEFAULT_PORTABLE_ROOT / "terminal64.exe"
DEFAULT_LOG_PATH = REPO_ROOT / ".runtime/live-overnight/mt5_live_spread_log.jsonl"

EXPECTED_SERVER = "FTMO-Demo"
EXPECTED_LOGIN = 1515343166
MAGIC_MIN = 20261120
MAGIC_MAX = 20261199
FORBIDDEN_PATH_TOKENS = ("program files\\metatrader 5", "d0e8209f77c8cf37ad8bf550e51ff075")

MONITORED_SYMBOLS = (
    "USDJPY",
    "GBPUSD",
    "EURUSD",
    "EURJPY",
    "AUDUSD",
    "USDCAD",
    "US100.cash",
    "US500.cash",
    "XAUUSD",
)


def assert_safe_terminal_path(terminal_path: Path) -> None:
    norm = str(terminal_path.resolve()).lower()
    for tok in FORBIDDEN_PATH_TOKENS:
        if tok in norm:
            raise ValueError(f"SAFETY ABORT: Refusing to connect to forbidden non-FTMO terminal: {terminal_path}")


def validate_demo_account(
    acc: Any,
    *,
    demo_trade_mode: int = 0,
    expected_server: str = EXPECTED_SERVER,
    expected_login: int = EXPECTED_LOGIN,
) -> dict[str, Any]:
    if acc is None:
        raise RuntimeError("MT5 account_info() returned None")
    if int(acc.trade_mode) != int(demo_trade_mode):
        raise RuntimeError(f"SAFETY ABORT: NOT DEMO ACCOUNT (trade_mode={acc.trade_mode})")
    if str(acc.server) != expected_server:
        raise RuntimeError(f"SAFETY ABORT: UNEXPECTED SERVER '{acc.server}' != '{expected_server}'")
    if expected_login and int(acc.login) != int(expected_login):
        raise RuntimeError(f"SAFETY ABORT: UNEXPECTED LOGIN {acc.login} != {expected_login}")
    return {
        "login": int(acc.login),
        "server": str(acc.server),
        "trade_mode": "ACCOUNT_TRADE_MODE_DEMO",
        "currency": str(acc.currency),
        "balance": round(float(acc.balance), 2),
        "equity": round(float(acc.equity), 2),
        "profit": round(float(acc.profit), 2),
        "margin": round(float(acc.margin), 2),
        "margin_free": round(float(acc.margin_free), 2),
        "leverage": int(acc.leverage),
        "trade_allowed": bool(acc.trade_allowed),
        "trade_expert": bool(acc.trade_expert),
    }


def read_heartbeat_telemetry(heartbeat_path: Path, *, now_utc_ts: int, stale_after_sec: int = 180) -> dict[str, Any]:
    if not heartbeat_path.exists():
        return {"present": False, "status": "MISSING", "age_s": None, "payload": None}
    try:
        payload = json.loads(heartbeat_path.read_text(encoding="utf-8"))
        age = max(0, int(now_utc_ts) - int(payload.get("utc_ts", 0)))
        status = "OK"
        if age > stale_after_sec or bool(payload.get("kill_switch", False)) or int(payload.get("orphan_no_sl", 0)) > 0:
            status = "CRITICAL"
        elif str(payload.get("regime", "NORMAL")) in ("AMBER_BRAKE", "RED_BRAKE"):
            status = "WARNING"
        return {"present": True, "status": status, "age_s": age, "payload": payload}
    except Exception as exc:
        return {"present": True, "status": "PARSE_ERROR", "age_s": None, "error": str(exc), "payload": None}


def collect_snapshot(
    *,
    terminal_path: Path = DEFAULT_TERMINAL_PATH,
    expected_server: str = EXPECTED_SERVER,
    expected_login: int = EXPECTED_LOGIN,
    symbols: tuple[str, ...] = MONITORED_SYMBOLS,
    portable: bool = True,
    mt5_mod: Any = None,
) -> dict[str, Any]:
    """Capture one verified FTMO-Demo telemetry snapshot (bid/ask/spread, equity, positions, heartbeat)."""
    assert_safe_terminal_path(terminal_path)
    mt5 = mt5_mod
    if mt5 is None:
        import MetaTrader5 as mt5  # type: ignore

    ok = mt5.initialize(path=str(terminal_path), portable=portable, timeout=30000)
    if not ok:
        raise RuntimeError(f"MT5 initialize failed for {terminal_path}: {mt5.last_error()}")

    try:
        acc = mt5.account_info()
        account_info = validate_demo_account(
            acc,
            demo_trade_mode=int(mt5.ACCOUNT_TRADE_MODE_DEMO),
            expected_server=expected_server,
            expected_login=expected_login,
        )
        ti = mt5.terminal_info()
        data_dir = Path(ti.data_path) if (ti and getattr(ti, "data_path", "")) else terminal_path.parent
        now_dt = datetime.now(timezone.utc)
        now_ts = int(now_dt.timestamp())

        quotes: dict[str, dict[str, Any]] = {}
        for sym in symbols:
            mt5.symbol_select(sym, True)
            si = mt5.symbol_info(sym)
            tick = mt5.symbol_info_tick(sym)
            if si is None:
                quotes[sym] = {"available": False}
                continue
            bid = float(tick.bid) if tick and tick.bid > 0 else float(si.bid)
            ask = float(tick.ask) if tick and tick.ask > 0 else float(si.ask)
            point = float(si.point) if si.point > 0 else 0.0
            spread_calc = round((ask - bid) / point, 1) if (point > 0 and ask > 0 and bid > 0) else float(si.spread)
            quotes[sym] = {
                "available": True,
                "bid": bid,
                "ask": ask,
                "spread_pts": spread_calc,
                "broker_spread_pts": int(si.spread),
                "digits": int(si.digits),
                "tick_time_utc": int(tick.time) if tick else 0,
            }

        raw_positions = mt5.positions_get() or []
        naqex_positions = []
        orphan_no_sl = 0
        for pos in raw_positions:
            magic = int(pos.magic)
            is_naqex = MAGIC_MIN <= magic <= MAGIC_MAX
            sl_val = float(pos.sl)
            if is_naqex and sl_val <= 0.0:
                orphan_no_sl += 1
            if is_naqex:
                naqex_positions.append(
                    {
                        "ticket": int(pos.ticket),
                        "symbol": str(pos.symbol),
                        "magic": magic,
                        "type": "BUY" if int(pos.type) == 0 else "SELL",
                        "volume": float(pos.volume),
                        "price_open": float(pos.price_open),
                        "sl": sl_val,
                        "tp": float(pos.tp),
                        "profit": round(float(pos.profit), 2),
                        "swap": round(float(pos.swap), 2),
                    }
                )

        hb = read_heartbeat_telemetry(data_dir / "MQL5/Files/naqex_heartbeat.json", now_utc_ts=now_ts)

        return {
            "schema": "naqex-mt5-live-telemetry-v1",
            "captured_utc": now_dt.replace(microsecond=0).isoformat(),
            "captured_utc_ts": now_ts,
            "order_send_count": 0,
            "terminal_connected": bool(ti.connected) if ti else None,
            "terminal_trade_allowed": bool(ti.trade_allowed) if ti else None,
            "terminal_build": int(ti.build) if ti else None,
            "account": account_info,
            "positions_total": len(raw_positions),
            "naqex_positions_count": len(naqex_positions),
            "orphan_no_sl": orphan_no_sl,
            "naqex_positions": naqex_positions,
            "heartbeat": hb,
            "quotes": quotes,
        }
    finally:
        mt5.shutdown()


def append_jsonl(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description="Fail-closed FTMO-Demo live spread/equity/heartbeat telemetry monitor.")
    ap.add_argument("--terminal", type=Path, default=DEFAULT_TERMINAL_PATH, help="FTMO-Demo portable terminal64.exe path.")
    ap.add_argument("--log-file", type=Path, default=DEFAULT_LOG_PATH, help="Output JSONL log path.")
    ap.add_argument("--once", action="store_true", help="Collect one snapshot and exit.")
    ap.add_argument("--daemon", action="store_true", help="Run continuously at --interval seconds.")
    ap.add_argument("--interval", type=int, default=60, help="Polling interval in seconds for --daemon mode.")
    ap.add_argument("--max-iterations", type=int, default=0, help="Optional max iterations in --daemon mode (0=infinite).")
    args = ap.parse_args(argv)

    if not args.daemon:
        args.once = True

    iteration = 0
    while True:
        iteration += 1
        snap = collect_snapshot(terminal_path=args.terminal)
        append_jsonl(args.log_file, snap)
        print(json.dumps(snap, ensure_ascii=False))
        sys.stdout.flush()
        if args.once or (args.max_iterations > 0 and iteration >= args.max_iterations):
            break
        time.sleep(max(5, int(args.interval)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
