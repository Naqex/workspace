"""Isolated portable MT5 lifecycle, deal history lookup, and 5s spread snapshot capture."""

from __future__ import annotations

import importlib
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

from exports.calibration_probe.constants import (
    CORE_SYMBOLS,
    DEFAULT_PORTABLE_DIR,
    REPO_ROOT,
    SYMBOL_META,
    TERMINAL_BINARIES,
)
from exports.calibration_probe.models import RedactedCredentials, SafetyLockError
from exports.calibration_probe.validators import (
    assert_no_concurrent_mt5,
    assert_safe_portable_path,
    list_running_terminal_processes,
    tag_session_utc,
    validate_calibration_account,
)
from quant_core.io_utils import atomic_write_text


def prepare_isolated_portable_terminal(
    *,
    source_terminal_exe: Path,
    portable_root: Path = DEFAULT_PORTABLE_DIR,
    allow_trading: bool = False,
    fallback_servers_dir: Path | None = None,
) -> tuple[Path, Path]:
    """Prepare isolated portable folder for 1515343318 (binaries + public servers.dat only, ZERO accounts.dat)."""
    assert_safe_portable_path(portable_root)
    portable_root.mkdir(parents=True, exist_ok=True)
    src_exe = Path(source_terminal_exe)
    if not src_exe.is_file():
        raise SafetyLockError(f"LOCK_2_SOURCE_TERMINAL_MISSING: {src_exe}")

    for name in TERMINAL_BINARIES:
        origin = src_exe if name == "terminal64.exe" else src_exe.parent / name
        dst = portable_root / name
        if origin.is_file() and not dst.exists():
            shutil.copy2(origin, dst)

    cfg_dir = portable_root / "Config"
    cfg_dir.mkdir(exist_ok=True)
    # Copy public broker discovery (`servers.dat` / `*.srv`) ONLY — NEVER `accounts.dat`!
    candidate_dirs = [src_exe.parent / "Config"]
    if fallback_servers_dir is not None:
        candidate_dirs.append(Path(fallback_servers_dir))
    else:
        candidate_dirs.append(REPO_ROOT / ".runtime/ftmo-demo-portable-1515343166/Config")
    appdata = os.environ.get("APPDATA", "")
    if appdata:
        term_base = Path(appdata) / "MetaQuotes/Terminal"
        if term_base.is_dir():
            for child in term_base.iterdir():
                if (child / "Config").is_dir():
                    candidate_dirs.append(child / "Config")

    for d in candidate_dirs:
        if not d.is_dir():
            continue
        for item in d.glob("*"):
            if item.is_file() and (item.name.lower() == "servers.dat" or item.suffix.lower() == ".srv"):
                dst_srv = cfg_dir / item.name
                if not dst_srv.exists():
                    shutil.copy2(item, dst_srv)

    ini_path = portable_root / "connector.ini"
    ini_txt = (
        "[Common]\r\n"
        "ProxyEnable=0\r\n"
        "NewsEnable=0\r\n"
        "KeepPrivate=1\r\n"
        "\r\n"
        "[Experts]\r\n"
        f"Enabled={1 if allow_trading else 0}\r\n"
        f"AllowLiveTrading={1 if allow_trading else 0}\r\n"
        "Account=0\r\n"
        "AllowDllImport=0\r\n"
    )
    atomic_write_text(ini_path, ini_txt, encoding="utf-16", newline="")
    return portable_root / "terminal64.exe", ini_path


def capture_spread_snapshot(
    mt5: Any,
    *,
    symbols: tuple[str, ...] = CORE_SYMBOLS,
    now_utc: datetime | None = None,
    demo_trade_mode: int | None = None,
) -> dict[str, Any]:
    """Capture one `naqex-mt5-live-telemetry-v1` spread snapshot (`OrderSend = 0`) for prop_challenge_tracker."""
    mode_demo = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)) if demo_trade_mode is None else int(demo_trade_mode)
    acc = mt5.account_info()
    account_info = validate_calibration_account(acc, demo_trade_mode=mode_demo)
    ti = mt5.terminal_info()
    dt = (now_utc or datetime.now(UTC)).astimezone(UTC)
    now_ts = int(dt.timestamp())
    session = tag_session_utc(dt)

    quotes: dict[str, dict[str, Any]] = {}
    for sym in symbols:
        try:
            mt5.symbol_select(sym, True)
        except Exception:
            pass
        si = mt5.symbol_info(sym)
        tick = mt5.symbol_info_tick(sym)
        if si is None:
            quotes[sym] = {"available": False}
            continue
        bid = float(tick.bid) if (tick is not None and float(tick.bid) > 0.0) else float(getattr(si, "bid", 0.0))
        ask = float(tick.ask) if (tick is not None and float(tick.ask) > 0.0) else float(getattr(si, "ask", 0.0))
        si_point = float(getattr(si, "point", 0.0))
        point = float(si.point) if si_point > 0.0 else float(SYMBOL_META.get(sym, {}).get("point", 0.0))
        spread_px = max(0.0, ask - bid) if (ask > 0.0 and bid > 0.0) else 0.0
        mid = 0.5 * (ask + bid) if (ask > 0.0 and bid > 0.0) else 0.0
        has_valid_quote = point > 0.0 and ask > 0.0 and bid > 0.0
        spread_pts = round(spread_px / point, 1) if has_valid_quote else float(getattr(si, "spread", 0))
        spread_bps = round((spread_px / mid) * 10_000.0, 4) if mid > 0.0 else 0.0
        quotes[sym] = {
            "available": True,
            "bid": bid,
            "ask": ask,
            "spread_pts": spread_pts,
            "broker_spread_pts": int(getattr(si, "spread", 0)),
            "spread_bps": spread_bps,
            "digits": int(getattr(si, "digits", SYMBOL_META.get(sym, {}).get("digits", 5))),
            "point": point,
            "tick_time_utc": int(getattr(tick, "time", 0)) if tick is not None else 0,
        }

    raw_positions = mt5.positions_get() or []
    naqex_positions = []
    orphan_no_sl = 0
    for pos in raw_positions:
        magic = int(getattr(pos, "magic", 0))
        is_naqex = 20261120 <= magic <= 20261199
        sl_val = float(getattr(pos, "sl", 0.0))
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
                    "tp": float(getattr(pos, "tp", 0.0)),
                    "profit": round(float(getattr(pos, "profit", 0.0)), 2),
                    "swap": round(float(getattr(pos, "swap", 0.0)), 2),
                }
            )

    return {
        "schema": "naqex-mt5-live-telemetry-v1",
        "captured_utc": dt.replace(microsecond=0).isoformat(),
        "captured_utc_ts": now_ts,
        "session": session,
        "source": "ftmo_demo_calibration_probe",
        "order_send_count": 0,
        "terminal_connected": bool(ti.connected) if ti is not None else None,
        "terminal_trade_allowed": bool(ti.trade_allowed) if ti is not None else None,
        "terminal_build": int(ti.build) if ti is not None else None,
        "account": account_info,
        "positions_total": len(raw_positions),
        "naqex_positions_count": len(naqex_positions),
        "orphan_no_sl": orphan_no_sl,
        "naqex_positions": naqex_positions,
        "heartbeat": {"present": False, "status": "MISSING", "age_s": None, "payload": None},
        "quotes": quotes,
    }


def _pick_filling_mode(mt5: Any, symbol_info: Any) -> int:
    fm = int(getattr(symbol_info, "filling_mode", 0))
    if fm & 2:
        return int(getattr(mt5, "ORDER_FILLING_IOC", 1))
    if fm & 1:
        return int(getattr(mt5, "ORDER_FILLING_FOK", 0))
    return int(getattr(mt5, "ORDER_FILLING_RETURN", 2))


def _lookup_deal_details(
    mt5: Any,
    *,
    deal_ticket: int = 0,
    order_ticket: int = 0,
    position_id: int = 0,
    expected_entry_type: int | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Any | None:
    """Query MT5 history deals for exact broker fill price, commission, swap, profit & exit reason.

    Strictly filters by `expected_entry_type` (`DEAL_ENTRY_IN=0` / `DEAL_ENTRY_OUT=1`) across retries
    so a delayed broker history sync NEVER returns the `DEAL_ENTRY_IN` deal as an `EXIT` deal!
    """
    for attempt in range(20):
        candidates: list[Any] = []
        if deal_ticket > 0:
            try:
                res = mt5.history_deals_get(ticket=int(deal_ticket))
                if res:
                    candidates.extend(res)
            except Exception:
                pass
        if order_ticket > 0:
            try:
                res = mt5.history_deals_get(order=int(order_ticket))
                if res:
                    candidates.extend(res)
            except Exception:
                pass
        if position_id > 0:
            try:
                res = mt5.history_deals_get(position=int(position_id))
                if res:
                    candidates.extend(res)
            except Exception:
                pass

        if candidates:
            if expected_entry_type is not None:
                matched = [d for d in candidates if int(getattr(d, "entry", -1)) == int(expected_entry_type)]
                if matched:
                    matched.sort(key=lambda d: int(getattr(d, "ticket", 0)))
                    return matched[-1]
            else:
                candidates.sort(key=lambda d: int(getattr(d, "ticket", 0)))
                return candidates[-1]

        if attempt < 19:
            sleep_fn(0.2)
    return None


def _connect_isolated_mt5(
    *,
    creds: RedactedCredentials,
    portable_dir: Path,
    allow_trading: bool,
    mt5_mod: Any = None,
    process_lister: Callable[[], list[str]] = list_running_terminal_processes,
) -> tuple[Any, subprocess.Popen[Any] | None]:
    """Safely launch & initialize isolated portable MT5 for login 1515343318 only."""
    assert_safe_portable_path(portable_dir)
    assert_no_concurrent_mt5(process_lister)
    term_exe, ini_path = prepare_isolated_portable_terminal(
        source_terminal_exe=creds.terminal_path,
        portable_root=portable_dir,
        allow_trading=allow_trading,
    )

    proc: subprocess.Popen[Any] | None = None
    mt5: Any = mt5_mod
    if mt5 is None:
        mt5 = cast(Any, importlib.import_module("MetaTrader5"))

        startup = None
        if sys.platform == "win32":
            startup = subprocess.STARTUPINFO()
            startup.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            startup.wShowWindow = 0
        proc = subprocess.Popen(
            [str(term_exe), "/portable", f"/config:{ini_path}"],
            cwd=str(portable_dir),
            startupinfo=startup,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2.5)

    ok = False
    for attempt in range(3 if proc is not None else 1):
        ok = mt5.initialize(
            path=str(term_exe),
            login=creds.login,
            password=creds.secret_password(),
            server=creds.server,
            portable=True,
            timeout=30000,
        )
        if ok:
            break
        if attempt < 2 and proc is not None:
            time.sleep(2.0)

    if not ok:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        err = mt5.last_error()
        code = err[0] if isinstance(err, (tuple, list)) and err else err
        raise RuntimeError(f"MT5_INITIALIZE_FAILED_SANITIZED(code={code})")

    try:
        # Wait briefly for broker connection when launching a fresh portable process
        if proc is not None:
            deadline = time.monotonic() + 15.0
            while time.monotonic() < deadline:
                ti_w = mt5.terminal_info()
                acc_w = mt5.account_info()
                if ti_w is not None and getattr(ti_w, "connected", False) and acc_w is not None:
                    break
                time.sleep(0.5)

        demo_mode = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
        acc_info = validate_calibration_account(mt5.account_info(), demo_trade_mode=demo_mode)
        ti = mt5.terminal_info()
        if ti is not None and getattr(ti, "data_path", ""):
            assert_safe_portable_path(Path(ti.data_path))
        if allow_trading:
            if not acc_info.get("trade_allowed") or (ti is not None and not getattr(ti, "trade_allowed", False)):
                raise SafetyLockError(
                    "LOCK_2_TRADING_DISABLED_IN_TERMINAL: AlgoTrading/trade_allowed is False on 1515343318"
                )
    except Exception:
        try:
            mt5.shutdown()
        finally:
            if proc is not None and proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
        raise
    return mt5, proc


def _teardown_isolated_mt5(
    mt5: Any,
    proc: subprocess.Popen[Any] | None,
    ini_path: Path | None = None,
) -> None:
    try:
        mt5.shutdown()
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
        if ini_path is not None and ini_path.exists():
            try:
                ini_path.unlink()
            except OSError:
                pass
