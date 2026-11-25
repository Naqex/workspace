"""Fail-Closed FTMO-Demo Secondary Calibration Probe & 5s Live Spread Recorder (`1515343318`).

Executes ONLY against the secondary FTMO Free Trial Demo account (`1515343318` on `FTMO-Demo`),
measuring real broker execution friction (market entry/exit slippage, real SL fill slippage,
realized commission, swap=0 verification) while simultaneously recording 5-second live Bid/Ask
spreads across `USDJPY`, `GBPUSD`, `EURJPY`, and `US100.cash`.

NON-NEGOTIABLE 6 HARD SAFETY LOCKS (checked before EVERY order):
  1. Credentials read strictly from local gitignored `config/ftmo_free_trial.env` (password is
     never printed, logged, serialized, or committed; redacted in `__repr__`/`__str__`).
  2. Account assertions: `trade_mode == mt5.ACCOUNT_TRADE_MODE_DEMO`, `login == 1515343318`
     (NEVER `1515343166`), `server == "FTMO-Demo"`, and isolated portable terminal path (NEVER
     `C:\\Program Files\\MetaTrader 5` or `.runtime/ftmo-demo-portable-1515343166`, and refuses
     to launch if another `terminal64.exe` instance is already running).
  3. Hard-locked `volume == 0.01`, `max_open_positions == 1`, `max_total_trades == 28`
     (`7` fills x `4` core symbols: `USDJPY`, `GBPUSD`, `EURJPY`, `US100.cash`), and mandatory
     hard SL on every order (`15-25 pips` FX / `40-80` index pts US100; mixed BUY & SELL).
  4. Red-News calendar guard (`tooling/ai-engines/exports/Files/naqex_red_news_utc.csv`):
     fail-closed if missing/empty; blocks any new entry within `+-300s` (`+-5m`) of matching
     currency news (and `+-3600s` for BoJ `EST03UTC`) or whose hold overlaps the news window.
  5. Intraday zero-swap cutoff: stops entries and hard-flattens any open position before
     `20:55 UTC` (`swap = 0`, well before `21:55-22:15 UTC` rollover).
  6. CLI execution gate: defaults strictly to `--dry-run` (`OrderSend = 0`); sends `0.01`-lot
     demo orders ONLY when explicitly invoked with `--execute-demo-1515343318-calibration`.

Also provides `--summarize` (strictly offline, `OrderSend = 0`, `holdout_rows_analysed = 0`)
comparing FTMO live spreads by symbol & session against `.runtime/hot-m1-cache` Dev M1
(`2018-2024`, `< 2025-01-01`) and computing the Realized Friction Multiplier (`P50` & `P90`
adverse slippage + live spread + commission vs Dev `1.00x` budget).
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Any, Callable

import numpy as np

EXPORTS_DIR = Path(__file__).resolve().parent
AI_ENGINES_DIR = EXPORTS_DIR.parent
REPO_ROOT = AI_ENGINES_DIR.parents[1]

for _p in (AI_ENGINES_DIR, EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_factory import prop_challenge_tracker as pct  # noqa: E402

# ---------------------------------------------------------------------------
# Hard-locked invariants (NEVER relaxed by CLI flags)
# ---------------------------------------------------------------------------
ALLOWED_DEMO_LOGIN = 1515343318
FORBIDDEN_LOGINS = frozenset({1515343166})
ALLOWED_SERVER = "FTMO-Demo"
FIXED_VOLUME_LOTS = 0.01
MAX_OPEN_POSITIONS = 1
MAX_TOTAL_TRADES = 28
TRADES_PER_SYMBOL = 7
CORE_SYMBOLS: tuple[str, ...] = ("USDJPY", "GBPUSD", "EURJPY", "US100.cash")
RED_NEWS_BLOCK_WINDOW_SEC = 300
RED_NEWS_PRE_FLATTEN_SEC = 330
RED_NEWS_HARD_BAN_SEC = 135
BOJ_ESTIMATED_PAD_SEC = 3600
HARD_FLATTEN_CUTOFF_HOUR = 20
HARD_FLATTEN_CUTOFF_MINUTE = 55
SPREAD_SAMPLE_INTERVAL_SEC = 5
PROBE_MAGIC = 20261198
HOLDOUT_START_UTC_TS = 1735689600  # 2025-01-01T00:00:00Z (strict upper bound for Dev M1)
EXPECTED_HOLDOUT_LOCK_SHA = "f0a6b43cb205535b0a959456455dc1d857a0936c06c2e51b8614fd7d772a8486"

ENV_ALLOWED_KEYS = (
    "FTMO_MT5_LOGIN",
    "FTMO_MT5_PASSWORD",
    "FTMO_MT5_SERVER",
    "FTMO_MT5_TERMINAL_PATH",
)
FORBIDDEN_PATH_TOKENS = (
    "program files\\metatrader 5",
    "program files/metatrader 5",
    "d0e8209f77c8cf37ad8bf550e51ff075",
    "ftmo-demo-portable-1515343166",
)
TERMINAL_BINARIES = ("terminal64.exe", "MetaEditor64.exe", "metatester64.exe")

DEFAULT_ENV_PATH = REPO_ROOT / "config/ftmo_free_trial.env"
DEFAULT_NEWS_CSV = REPO_ROOT / "tooling/ai-engines/exports/Files/naqex_red_news_utc.csv"
DEFAULT_SPREAD_LOG = REPO_ROOT / ".runtime/live-overnight/mt5_live_spread_log.jsonl"
DEFAULT_FILLS_CSV = REPO_ROOT / ".runtime/live-overnight/ftmo_calibration_fills_1515343318.csv"
DEFAULT_SUMMARY_JSON = REPO_ROOT / ".runtime/live-overnight/ftmo_realized_friction_summary_20261125.json"
DEFAULT_PORTABLE_DIR = REPO_ROOT / ".runtime/ftmo-demo-portable-1515343318"
DEFAULT_HOT_M1_CACHE = REPO_ROOT / ".runtime/hot-m1-cache"
DEFAULT_HOLDOUT_LOCK_JSON = REPO_ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"

SESSION_ORDER: tuple[str, ...] = ("ASIA", "LONDON", "NY_OVERLAP", "NY_AFTERNOON")

# Symbol metadata synced with FTMO-LIVE-SPECS-ALL-SYMBOLS-20261124.json & pass24_mtf_new_archetypes.py
SYMBOL_META: dict[str, dict[str, Any]] = {
    "USDJPY": {
        "cache_asset": "USDJPY",
        "point": 0.001,
        "digits": 3,
        "pip_size": 0.01,
        "contract_size": 100_000.0,
        "is_index": False,
        "sl_min_units": 10.0,   # pips
        "sl_max_units": 35.0,
        "sl_schedule_units": (15.0, 18.0, 20.0, 22.0, 25.0, 16.0, 20.0),
        "dev_comm_rt_usd_per_lot": 5.0,
        "dev_base_slip_rt_px": 0.004,
        "dev_stress_slip_rt_px": 0.009,
        "tracker_oneway_budget_bps": 1.30,
    },
    "GBPUSD": {
        "cache_asset": "GBPUSD",
        "point": 0.00001,
        "digits": 5,
        "pip_size": 0.0001,
        "contract_size": 100_000.0,
        "is_index": False,
        "sl_min_units": 10.0,   # pips
        "sl_max_units": 35.0,
        "sl_schedule_units": (15.0, 18.0, 20.0, 22.0, 25.0, 16.0, 20.0),
        "dev_comm_rt_usd_per_lot": 5.0,
        "dev_base_slip_rt_px": 0.00004,
        "dev_stress_slip_rt_px": 0.00009,
        "tracker_oneway_budget_bps": 1.50,
    },
    "EURJPY": {
        "cache_asset": "EURJPY",
        "point": 0.001,
        "digits": 3,
        "pip_size": 0.01,
        "contract_size": 100_000.0,
        "is_index": False,
        "sl_min_units": 10.0,   # pips
        "sl_max_units": 35.0,
        "sl_schedule_units": (15.0, 18.0, 20.0, 22.0, 25.0, 16.0, 20.0),
        "dev_comm_rt_usd_per_lot": 5.0,
        "dev_base_slip_rt_px": 0.004,
        "dev_stress_slip_rt_px": 0.009,
        "tracker_oneway_budget_bps": 1.50,
    },
    "US100.cash": {
        "cache_asset": "US100",
        "point": 0.01,
        "digits": 2,
        "pip_size": 1.0,        # 1.0 index point = 100 broker points (point=0.01)
        "contract_size": 1.0,
        "is_index": True,
        "sl_min_units": 25.0,   # index points
        "sl_max_units": 120.0,
        "sl_schedule_units": (40.0, 50.0, 60.0, 70.0, 80.0, 45.0, 55.0),
        "dev_comm_rt_usd_per_lot": 0.0,
        "dev_base_slip_rt_px": 2.00,
        "dev_stress_slip_rt_px": 4.00,
        "tracker_oneway_budget_bps": 2.25,
    },
}

FILLS_CSV_COLUMNS: tuple[str, ...] = (
    "utc_ts",
    "utc_iso",
    "session",
    "account_login",
    "server",
    "trade_seq",
    "position_id",
    "order_id",
    "deal_id",
    "symbol",
    "leg",
    "side",
    "position_side",
    "exit_reason",
    "volume",
    "pre_bid",
    "pre_ask",
    "pre_spread_pts",
    "pre_spread_bps",
    "expected_price",
    "fill_price",
    "sl_price",
    "adverse_slip_pts",
    "adverse_slip_bps",
    "latency_ms",
    "commission_usd",
    "commission_bps",
    "swap_usd",
    "pnl_usd",
    "retcode",
    "dry_run",
    "comment",
)


class SafetyLockError(RuntimeError):
    """Raised whenever any of the 6 fail-closed safety invariants is violated."""


# ---------------------------------------------------------------------------
# Lock 1: Redacted Credentials Loader (NEVER exposes password)
# ---------------------------------------------------------------------------
class RedactedCredentials:
    """In-memory credential container that strictly redacts passwords on formatting."""

    __slots__ = ("login", "server", "terminal_path", "_password")

    def __init__(self, *, login: int, password: str, server: str, terminal_path: Path) -> None:
        self.login = int(login)
        self._password = str(password)
        self.server = str(server)
        self.terminal_path = Path(terminal_path)

    def secret_password(self) -> str:
        return self._password

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "login": self.login,
            "server": self.server,
            "terminal_path": str(self.terminal_path),
            "password": "***REDACTED***",
        }

    def __repr__(self) -> str:
        return (
            f"RedactedCredentials(login={self.login}, server={self.server!r}, "
            f"terminal_path={str(self.terminal_path)!r}, password='***REDACTED***')"
        )

    def __str__(self) -> str:
        return self.__repr__()


def load_ftmo_trial_env(env_path: Path = DEFAULT_ENV_PATH) -> RedactedCredentials:
    """Parse gitignored `config/ftmo_free_trial.env` and assert login==1515343318 & server==FTMO-Demo."""
    p = Path(env_path)
    if not p.is_file():
        raise SafetyLockError(f"LOCK_1_MISSING_ENV_FILE: {p}")
    if p.stat().st_size > 8192:
        raise SafetyLockError("LOCK_1_ENV_FILE_TOO_LARGE")

    parsed: dict[str, str] = {}
    for raw_line in p.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, val = line.partition("=")
        k = key.strip()
        if not sep or k not in ENV_ALLOWED_KEYS:
            raise SafetyLockError(f"LOCK_1_UNEXPECTED_ENV_KEY: {k!r}")
        v = val.strip()
        if v[:1] in ('"', "'"):
            if len(v) < 2 or v[-1] != v[0]:
                raise SafetyLockError(f"LOCK_1_UNBALANCED_QUOTES_FOR_{k}")
            v = v[1:-1]
        parsed[k] = v

    for req in ("FTMO_MT5_LOGIN", "FTMO_MT5_PASSWORD", "FTMO_MT5_SERVER"):
        if not parsed.get(req):
            raise SafetyLockError(f"LOCK_1_MISSING_REQUIRED_KEY: {req}")

    if not parsed["FTMO_MT5_LOGIN"].isdigit():
        raise SafetyLockError("LOCK_1_NON_NUMERIC_LOGIN")
    login = int(parsed["FTMO_MT5_LOGIN"])
    if login in FORBIDDEN_LOGINS or login != ALLOWED_DEMO_LOGIN:
        raise SafetyLockError(
            f"LOCK_1_FORBIDDEN_LOGIN: env login={login} != required secondary demo {ALLOWED_DEMO_LOGIN}"
        )

    server = parsed["FTMO_MT5_SERVER"]
    if server != ALLOWED_SERVER:
        raise SafetyLockError(f"LOCK_1_UNEXPECTED_SERVER: {server!r} != {ALLOWED_SERVER!r}")

    term_str = parsed.get("FTMO_MT5_TERMINAL_PATH") or r"C:\Program Files\MetaTrader 5\terminal64.exe"
    return RedactedCredentials(
        login=login,
        password=parsed["FTMO_MT5_PASSWORD"],
        server=server,
        terminal_path=Path(term_str),
    )


# ---------------------------------------------------------------------------
# Session Tagging & Red-News / UTC Cutoff Helpers
# ---------------------------------------------------------------------------
def tag_session_utc(utc_dt: datetime) -> str:
    """Tag UTC timestamp into ASIA / LONDON / NY_OVERLAP / NY_AFTERNOON."""
    dt = utc_dt.astimezone(timezone.utc) if utc_dt.tzinfo else utc_dt.replace(tzinfo=timezone.utc)
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
    dt = utc_dt.astimezone(timezone.utc) if utc_dt.tzinfo else utc_dt.replace(tzinfo=timezone.utc)
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


def load_red_news_calendar(news_csv: Path = DEFAULT_NEWS_CSV) -> list[dict[str, Any]]:
    """Load `naqex_red_news_utc.csv` fail-closed (raises if missing or empty)."""
    events = pct.load_red_news_events(Path(news_csv))
    if not events:
        raise SafetyLockError(f"LOCK_4_EMPTY_OR_MISSING_RED_NEWS_CSV: {news_csv}")
    return events


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


# ---------------------------------------------------------------------------
# Terminal Isolation & Process Guard (NEVER touch Exness Real or 1515343166)
# ---------------------------------------------------------------------------
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
    ini_path.write_text(ini_txt, encoding="utf-16")
    return portable_root / "terminal64.exe", ini_path


# ---------------------------------------------------------------------------
# All 6 Hard Locks Validator
# ---------------------------------------------------------------------------
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
        raise SafetyLockError(
            f"LOCK_3_WRONG_SIDE_SL: side={side_u} entry={entry_price} sl={sl_price}"
        )

    meta = SYMBOL_META[symbol]
    dist_units = signed_dist / float(meta["pip_size"])
    if dist_units < float(meta["sl_min_units"]) - 1e-6 or dist_units > float(meta["sl_max_units"]) + 1e-6:
        raise SafetyLockError(
            f"LOCK_3_SL_OUT_OF_CALIBRATION_BAND: {symbol} dist={dist_units:.2f} "
            f"not in [{meta['sl_min_units']}, {meta['sl_max_units']}]"
        )

    min_stop_px = max(0, int(stops_level_pts)) * float(point)
    if min_stop_px > 0.0 and signed_dist < min_stop_px:
        raise SafetyLockError(
            f"LOCK_3_SL_INSIDE_BROKER_STOPS_LEVEL: dist={signed_dist:.6f} < {min_stop_px:.6f}"
        )
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
        raise SafetyLockError(
            f"LOCK_3_MAX_TOTAL_TRADES_REACHED: {total_trades_opened} >= {MAX_TOTAL_TRADES}"
        )
    if int(per_symbol_counts.get(symbol, 0)) >= TRADES_PER_SYMBOL:
        raise SafetyLockError(
            f"LOCK_3_MAX_SYMBOL_TRADES_REACHED: {symbol} count={per_symbol_counts.get(symbol, 0)} >= {TRADES_PER_SYMBOL}"
        )

    if open_positions is None:
        raise SafetyLockError("LOCK_3_POSITIONS_GET_RETURNED_NONE")
    if len(open_positions) >= MAX_OPEN_POSITIONS:
        raise SafetyLockError(
            f"LOCK_3_MAX_OPEN_POSITIONS_BREACH: open={len(open_positions)} >= {MAX_OPEN_POSITIONS}"
        )

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
            f"{blocking_news['event']} (delta={blocking_news['signed_delta_sec']}s, pad=+-{blocking_news['pad_sec']}s)"
        )

    if is_past_flatten_cutoff(now_utc, hold_lookahead_sec=hold_sec):
        raise SafetyLockError(
            f"LOCK_5_PAST_2055_UTC_CUTOFF: now={now_utc.isoformat()} hold_sec={hold_sec}"
        )

    return acct_info


# ---------------------------------------------------------------------------
# Adverse Slippage Math (Execution/Deal Side Convention)
# ---------------------------------------------------------------------------
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


# ---------------------------------------------------------------------------
# Deterministic 28-Trade Calibration Schedule (7 x 4 Core Symbols)
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class PlannedCalibrationTrade:
    seq: int
    symbol: str
    side: str
    volume: float
    sl_units: float
    hold_sec: int
    gap_sec: int


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
            gap_s = int(gap_sec_override) if gap_sec_override is not None else int(gap_cycle[(round_idx + sym_idx) % len(gap_cycle)])
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


# ---------------------------------------------------------------------------
# MUI 2: 5s Live Spread Snapshot Builder (naqex-mt5-live-telemetry-v1)
# ---------------------------------------------------------------------------
def capture_spread_snapshot(
    mt5: Any,
    *,
    symbols: tuple[str, ...] = CORE_SYMBOLS,
    now_utc: datetime | None = None,
    demo_trade_mode: int | None = None,
) -> dict[str, Any]:
    """Capture one `naqex-mt5-live-telemetry-v1` spread snapshot (`OrderSend = 0`) compatible with prop_challenge_tracker."""
    mode_demo = int(getattr(mt5, "ACCOUNT_TRADE_MODE_DEMO", 0)) if demo_trade_mode is None else int(demo_trade_mode)
    acc = mt5.account_info()
    account_info = validate_calibration_account(acc, demo_trade_mode=mode_demo)
    ti = mt5.terminal_info()
    dt = (now_utc or datetime.now(timezone.utc)).astimezone(timezone.utc)
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
        point = float(si.point) if float(getattr(si, "point", 0.0)) > 0.0 else float(SYMBOL_META.get(sym, {}).get("point", 0.0))
        spread_px = max(0.0, ask - bid) if (ask > 0.0 and bid > 0.0) else 0.0
        mid = 0.5 * (ask + bid) if (ask > 0.0 and bid > 0.0) else 0.0
        spread_pts = round(spread_px / point, 1) if (point > 0.0 and ask > 0.0 and bid > 0.0) else float(getattr(si, "spread", 0))
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
            naqex_positions.append({
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
            })

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


def append_jsonl(log_path: Path, payload: dict[str, Any]) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(payload, ensure_ascii=False) + "\n")


def append_fill_csv(csv_path: Path, row: dict[str, Any]) -> None:
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    write_header = (not csv_path.exists()) or csv_path.stat().st_size == 0
    with csv_path.open("a", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(FILLS_CSV_COLUMNS))
        if write_header:
            w.writeheader()
        clean = {col: row.get(col, "") for col in FILLS_CSV_COLUMNS}
        w.writerow(clean)


def load_existing_live_entry_counts(csv_path: Path) -> tuple[int, dict[str, int]]:
    """Count previously executed non-dry-run calibration entries so restarts NEVER exceed 28 total / 7 per symbol."""
    if not csv_path.is_file():
        return 0, {s: 0 for s in CORE_SYMBOLS}
    total = 0
    by_sym: dict[str, int] = {s: 0 for s in CORE_SYMBOLS}
    with csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
        for r in csv.DictReader(f):
            if str(r.get("dry_run", "")).strip().lower() in ("true", "1", "yes"):
                continue
            if str(r.get("leg", "")).strip().upper() != "ENTRY":
                continue
            if int(float(r.get("retcode") or 0)) != 10009:
                continue
            sym = str(r.get("symbol", "")).strip()
            total += 1
            by_sym[sym] = by_sym.get(sym, 0) + 1
    return total, by_sym


# ---------------------------------------------------------------------------
# Calibration Probe Runtime (Dry-Run default; Explicit Live Opt-In)
# ---------------------------------------------------------------------------
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
                    # Deduplicate by ticket and return latest matching deal
                    matched.sort(key=lambda d: int(getattr(d, "ticket", 0)))
                    return matched[-1]
            else:
                candidates.sort(key=lambda d: int(getattr(d, "ticket", 0)))
                return candidates[-1]

        if attempt < 19:
            sleep_fn(0.2)
    return None


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
        self.clock_fn = clock_fn or (lambda: datetime.now(timezone.utc))
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
        return dt.astimezone(timezone.utc) if dt.tzinfo else dt.replace(tzinfo=timezone.utc)

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
        for sym in CORE_SYMBOLS:
            try:
                self.mt5.symbol_select(sym, True)
            except Exception:
                pass
        deadline = time.monotonic() + float(timeout_sec)
        while True:
            all_ready = True
            for sym in CORE_SYMBOLS:
                tick = self.mt5.symbol_info_tick(sym)
                if tick is None or float(getattr(tick, "bid", 0.0)) <= 0.0 or float(getattr(tick, "ask", 0.0)) <= 0.0:
                    all_ready = False
                    break
            if all_ready or time.monotonic() >= deadline:
                break
            self.sleep_fn(0.5)

    def _get_symbol_quote(self, symbol: str, *, retries: int = 12, retry_sleep_sec: float = 0.5) -> tuple[Any, float, float, float, int]:
        self.mt5.symbol_select(symbol, True)
        si = None
        bid = ask = point = 0.0
        digits = 5
        for attempt in range(max(1, int(retries))):
            si = self.mt5.symbol_info(symbol)
            tick = self.mt5.symbol_info_tick(symbol)
            if si is not None and tick is not None:
                bid = float(tick.bid)
                ask = float(tick.ask)
                point = float(si.point)
                digits = int(si.digits)
                if bid > 0.0 and ask > 0.0 and point > 0.0:
                    return si, bid, ask, point, digits
            if attempt < retries - 1:
                self.sleep_fn(retry_sleep_sec)
        if si is None:
            raise RuntimeError(f"QUOTE_UNAVAILABLE: {symbol}")
        raise RuntimeError(f"INVALID_QUOTE: {symbol} bid={bid} ask={ask} point={point}")

    def _close_position(
        self,
        *,
        pos: Any,
        trade_seq: int,
        exit_reason: str,
        sl_price_orig: float,
    ) -> dict[str, Any]:
        """Close an open calibration position with account+volume locks and log EXIT telemetry."""
        now_dt = self._now()
        demo_mode = int(getattr(self.mt5, "ACCOUNT_TRADE_MODE_DEMO", 0))
        acc = self.mt5.account_info()
        validate_calibration_account(acc, demo_trade_mode=demo_mode)
        if self.terminal_data_path is not None:
            assert_safe_portable_path(self.terminal_data_path)

        symbol = str(pos.symbol)
        vol = validate_fixed_volume(float(pos.volume))
        pos_id = int(getattr(pos, "ticket", getattr(pos, "identifier", 0)))
        pos_side = "BUY" if int(pos.type) == 0 else "SELL"
        close_deal_side = "SELL" if pos_side == "BUY" else "BUY"

        si, bid, ask, point, _digits = self._get_symbol_quote(symbol)
        expected_px = bid if close_deal_side == "SELL" else ask
        mid = 0.5 * (bid + ask)
        spread_pts = round((ask - bid) / point, 1)
        spread_bps = round(((ask - bid) / mid) * 10_000.0, 4)

        if not self.execute_live:
            raise SafetyLockError("LOCK_6_CLOSE_CALLED_IN_DRY_RUN")

        order_type = (
            int(getattr(self.mt5, "ORDER_TYPE_SELL", 1))
            if close_deal_side == "SELL"
            else int(getattr(self.mt5, "ORDER_TYPE_BUY", 0))
        )
        req = {
            "action": int(getattr(self.mt5, "TRADE_ACTION_DEAL", 1)),
            "symbol": symbol,
            "volume": vol,
            "type": order_type,
            "position": pos_id,
            "price": expected_px,
            "deviation": 30,
            "magic": PROBE_MAGIC,
            "comment": f"NQ_CAL_EXIT_{exit_reason[:12]}",
            "type_time": int(getattr(self.mt5, "ORDER_TIME_GTC", 0)),
            "type_filling": _pick_filling_mode(self.mt5, si),
        }

        t0 = time.perf_counter()
        res = self.mt5.order_send(req)
        latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        self.order_send_count += 1

        retcode = int(getattr(res, "retcode", -1)) if res is not None else -1
        deal_id = int(getattr(res, "deal", 0)) if res is not None else 0
        order_id = int(getattr(res, "order", 0)) if res is not None else 0
        fill_px = float(getattr(res, "price", 0.0)) if res is not None else 0.0

        deal_obj = _lookup_deal_details(
            self.mt5,
            deal_ticket=deal_id,
            order_ticket=order_id,
            position_id=pos_id,
            expected_entry_type=int(getattr(self.mt5, "DEAL_ENTRY_OUT", 1)),
            sleep_fn=self.sleep_fn,
        )
        if deal_obj is not None:
            if float(getattr(deal_obj, "price", 0.0)) > 0.0:
                fill_px = float(deal_obj.price)
            deal_id = int(getattr(deal_obj, "ticket", deal_id))
            comm_usd = float(getattr(deal_obj, "commission", 0.0)) + float(getattr(deal_obj, "fee", 0.0))
            swap_usd = float(getattr(deal_obj, "swap", 0.0))
            pnl_usd = float(getattr(deal_obj, "profit", 0.0))
        else:
            comm_usd, swap_usd, pnl_usd = 0.0, float(getattr(pos, "swap", 0.0)), float(getattr(pos, "profit", 0.0))

        if fill_px > 0.0:
            slip_pts, slip_bps = compute_adverse_slippage(
                deal_side=close_deal_side,
                expected_price=expected_px,
                fill_price=fill_px,
                point=point,
            )
            notional = estimate_notional_usd(
                symbol=symbol, volume=vol, price=fill_px, usdjpy_ref=self.usdjpy_last_mid
            )
            comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
        else:
            slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

        row = {
            "utc_ts": int(now_dt.timestamp()),
            "utc_iso": now_dt.replace(microsecond=0).isoformat(),
            "session": tag_session_utc(now_dt),
            "account_login": ALLOWED_DEMO_LOGIN,
            "server": ALLOWED_SERVER,
            "trade_seq": trade_seq,
            "position_id": pos_id,
            "order_id": order_id,
            "deal_id": deal_id,
            "symbol": symbol,
            "leg": "EXIT",
            "side": close_deal_side,
            "position_side": pos_side,
            "exit_reason": exit_reason,
            "volume": vol,
            "pre_bid": bid,
            "pre_ask": ask,
            "pre_spread_pts": spread_pts,
            "pre_spread_bps": spread_bps,
            "expected_price": expected_px,
            "fill_price": fill_px,
            "sl_price": sl_price_orig,
            "adverse_slip_pts": slip_pts,
            "adverse_slip_bps": slip_bps,
            "latency_ms": latency_ms,
            "commission_usd": round(comm_usd, 4),
            "commission_bps": comm_bps,
            "swap_usd": round(swap_usd, 4),
            "pnl_usd": round(pnl_usd, 4),
            "retcode": retcode,
            "dry_run": False,
            "comment": f"EXIT_{exit_reason}",
        }
        append_fill_csv(self.fills_csv_path, row)
        if retcode == int(getattr(self.mt5, "TRADE_RETCODE_DONE", 10009)):
            self.live_exits_filled += 1
            print(
                f"[{row['utc_iso']}] EXIT #{trade_seq} {symbol} {close_deal_side} ({exit_reason}) "
                f"fill={fill_px} slip={slip_bps:+.2f}bps comm={comm_usd:+.3f} swap={swap_usd:+.3f} pnl={pnl_usd:+.2f} lat={latency_ms}ms",
                flush=True,
            )
        else:
            self.rejected_orders_count += 1
        return row

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
        now_dt = self._now()
        close_deal_side = "SELL" if pos_side == "BUY" else "BUY"
        si, bid, ask, point, _digits = self._get_symbol_quote(symbol)
        mid = 0.5 * (bid + ask)
        spread_pts = round((ask - bid) / point, 1)
        spread_bps = round(((ask - bid) / mid) * 10_000.0, 4)

        deal_obj = _lookup_deal_details(
            self.mt5,
            position_id=position_id,
            expected_entry_type=int(getattr(self.mt5, "DEAL_ENTRY_OUT", 1)),
            sleep_fn=self.sleep_fn,
        )
        reason_code = int(getattr(deal_obj, "reason", -1)) if deal_obj is not None else -1
        deal_reason_sl = int(getattr(self.mt5, "DEAL_REASON_SL", 4))
        exit_reason = "SL_HIT" if (reason_code == deal_reason_sl or reason_code == -1) else f"BROKER_CLOSE_{reason_code}"

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
        expected_px = sl_price if (exit_reason == "SL_HIT" and sl_price > 0.0) else (bid if close_deal_side == "SELL" else ask)
        if fill_px > 0.0 and expected_px > 0.0:
            slip_pts, slip_bps = compute_adverse_slippage(
                deal_side=close_deal_side,
                expected_price=expected_px,
                fill_price=fill_px,
                point=point,
            )
            notional = estimate_notional_usd(
                symbol=symbol, volume=FIXED_VOLUME_LOTS, price=fill_px, usdjpy_ref=self.usdjpy_last_mid
            )
            comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
        else:
            slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

        row = {
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
            "leg": "EXIT",
            "side": close_deal_side,
            "position_side": pos_side,
            "exit_reason": exit_reason,
            "volume": FIXED_VOLUME_LOTS,
            "pre_bid": bid,
            "pre_ask": ask,
            "pre_spread_pts": spread_pts,
            "pre_spread_bps": spread_bps,
            "expected_price": expected_px,
            "fill_price": fill_px,
            "sl_price": sl_price,
            "adverse_slip_pts": slip_pts,
            "adverse_slip_bps": slip_bps,
            "latency_ms": 0.0,
            "commission_usd": round(comm_usd, 4),
            "commission_bps": comm_bps,
            "swap_usd": round(swap_usd, 4),
            "pnl_usd": round(pnl_usd, 4),
            "retcode": int(getattr(self.mt5, "TRADE_RETCODE_DONE", 10009)),
            "dry_run": False,
            "comment": f"BROKER_{exit_reason}",
        }
        append_fill_csv(self.fills_csv_path, row)
        self.live_exits_filled += 1
        print(
            f"[{row['utc_iso']}] EXIT #{trade_seq} {symbol} {close_deal_side} (BROKER_{exit_reason}) "
            f"fill={fill_px} slip={slip_bps:+.2f}bps comm={comm_usd:+.3f} swap={swap_usd:+.3f} pnl={pnl_usd:+.2f}",
            flush=True,
        )
        return row

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
                    if find_blocking_red_news(
                        cand.symbol,
                        int(now_dt.timestamp()),
                        self.news_events,
                        window_sec=RED_NEWS_BLOCK_WINDOW_SEC,
                        hold_lookahead_sec=cand.hold_sec,
                    ) is None:
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

                # Skip if symbol already has 7 live fills
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
                        {
                            "utc_ts": int(now_dt.timestamp()),
                            "utc_iso": now_dt.replace(microsecond=0).isoformat(),
                            "session": tag_session_utc(now_dt),
                            "account_login": ALLOWED_DEMO_LOGIN,
                            "server": ALLOWED_SERVER,
                            "trade_seq": item.seq,
                            "position_id": 0,
                            "order_id": 0,
                            "deal_id": 0,
                            "symbol": item.symbol,
                            "leg": "DRYRUN_INTENT",
                            "side": item.side,
                            "position_side": item.side,
                            "exit_reason": "DRY_RUN",
                            "volume": FIXED_VOLUME_LOTS,
                            "pre_bid": bid,
                            "pre_ask": ask,
                            "pre_spread_pts": spread_pts,
                            "pre_spread_bps": spread_bps,
                            "expected_price": entry_expected,
                            "fill_price": 0.0,
                            "sl_price": sl_px,
                            "adverse_slip_pts": 0.0,
                            "adverse_slip_bps": 0.0,
                            "latency_ms": 0.0,
                            "commission_usd": 0.0,
                            "commission_bps": 0.0,
                            "swap_usd": 0.0,
                            "pnl_usd": 0.0,
                            "retcode": 0,
                            "dry_run": True,
                            "comment": f"DRYRUN_HOLD{item.hold_sec}S_SL{item.sl_units}",
                        },
                    )
                    self.dryrun_intents_logged += 1
                    total_opened += 1
                    per_sym_counts[item.symbol] = per_sym_counts.get(item.symbol, 0) + 1
                    self._record_spread()
                    continue

                # Live DEMO 1515343318 0.01-lot order with mandatory hard SL
                order_type = (
                    int(getattr(self.mt5, "ORDER_TYPE_BUY", 0))
                    if item.side == "BUY"
                    else int(getattr(self.mt5, "ORDER_TYPE_SELL", 1))
                )
                req = {
                    "action": int(getattr(self.mt5, "TRADE_ACTION_DEAL", 1)),
                    "symbol": item.symbol,
                    "volume": FIXED_VOLUME_LOTS,
                    "type": order_type,
                    "price": entry_expected,
                    "sl": sl_px,
                    "tp": 0.0,
                    "deviation": 30,
                    "magic": PROBE_MAGIC,
                    "comment": f"NQ_CAL_{item.seq:02d}_{item.side}",
                    "type_time": int(getattr(self.mt5, "ORDER_TIME_GTC", 0)),
                    "type_filling": _pick_filling_mode(self.mt5, si),
                }
                t0 = time.perf_counter()
                res = self.mt5.order_send(req)
                latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
                self.order_send_count += 1

                retcode = int(getattr(res, "retcode", -1)) if res is not None else -1
                done_code = int(getattr(self.mt5, "TRADE_RETCODE_DONE", 10009))
                deal_id = int(getattr(res, "deal", 0)) if res is not None else 0
                order_id = int(getattr(res, "order", 0)) if res is not None else 0
                fill_px = float(getattr(res, "price", 0.0)) if res is not None else 0.0

                if retcode != done_code:
                    self.rejected_orders_count += 1
                    append_fill_csv(
                        self.fills_csv_path,
                        {
                            "utc_ts": int(now_dt.timestamp()),
                            "utc_iso": now_dt.replace(microsecond=0).isoformat(),
                            "session": tag_session_utc(now_dt),
                            "account_login": ALLOWED_DEMO_LOGIN,
                            "server": ALLOWED_SERVER,
                            "trade_seq": item.seq,
                            "position_id": 0,
                            "order_id": order_id,
                            "deal_id": deal_id,
                            "symbol": item.symbol,
                            "leg": "ENTRY_REJECT",
                            "side": item.side,
                            "position_side": item.side,
                            "exit_reason": "REJECTED",
                            "volume": FIXED_VOLUME_LOTS,
                            "pre_bid": bid,
                            "pre_ask": ask,
                            "pre_spread_pts": spread_pts,
                            "pre_spread_bps": spread_bps,
                            "expected_price": entry_expected,
                            "fill_price": fill_px,
                            "sl_price": sl_px,
                            "adverse_slip_pts": 0.0,
                            "adverse_slip_bps": 0.0,
                            "latency_ms": latency_ms,
                            "commission_usd": 0.0,
                            "commission_bps": 0.0,
                            "swap_usd": 0.0,
                            "pnl_usd": 0.0,
                            "retcode": retcode,
                            "dry_run": False,
                            "comment": f"REJECT_{getattr(res, 'comment', '')}",
                        },
                    )
                    continue

                # Resolve opened position FIRST (FTMO Market Execution can return res.price == 0.0 / res.deal == 0!)
                active_pos = None
                pos_id = 0
                for _poll in range(5):
                    open_now = self.mt5.positions_get(symbol=item.symbol) or []
                    for p in open_now:
                        if int(getattr(p, "magic", 0)) == PROBE_MAGIC:
                            active_pos = p
                            pos_id = int(getattr(p, "ticket", 0))
                            break
                    if active_pos is not None:
                        break
                    self.sleep_fn(0.1)

                deal_obj = _lookup_deal_details(
                    self.mt5,
                    deal_ticket=deal_id,
                    order_ticket=order_id,
                    position_id=pos_id,
                    expected_entry_type=int(getattr(self.mt5, "DEAL_ENTRY_IN", 0)),
                    sleep_fn=self.sleep_fn,
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
                        usdjpy_ref=self.usdjpy_last_mid,
                    )
                    comm_bps = round((abs(comm_usd) / notional) * 10_000.0, 4)
                else:
                    slip_pts, slip_bps, comm_bps = 0.0, 0.0, 0.0

                append_fill_csv(
                    self.fills_csv_path,
                    {
                        "utc_ts": int(now_dt.timestamp()),
                        "utc_iso": now_dt.replace(microsecond=0).isoformat(),
                        "session": tag_session_utc(now_dt),
                        "account_login": ALLOWED_DEMO_LOGIN,
                        "server": ALLOWED_SERVER,
                        "trade_seq": item.seq,
                        "position_id": pos_id,
                        "order_id": order_id,
                        "deal_id": deal_id,
                        "symbol": item.symbol,
                        "leg": "ENTRY",
                        "side": item.side,
                        "position_side": item.side,
                        "exit_reason": "",
                        "volume": FIXED_VOLUME_LOTS,
                        "pre_bid": bid,
                        "pre_ask": ask,
                        "pre_spread_pts": spread_pts,
                        "pre_spread_bps": spread_bps,
                        "expected_price": entry_expected,
                        "fill_price": fill_px,
                        "sl_price": sl_px,
                        "adverse_slip_pts": slip_pts,
                        "adverse_slip_bps": slip_bps,
                        "latency_ms": latency_ms,
                        "commission_usd": round(comm_usd, 4),
                        "commission_bps": comm_bps,
                        "swap_usd": round(swap_usd, 4),
                        "pnl_usd": 0.0,
                        "retcode": retcode,
                        "dry_run": False,
                        "comment": f"ENTRY_SL{item.sl_units}",
                    },
                )
                self.live_entries_filled += 1
                total_opened += 1
                per_sym_counts[item.symbol] = per_sym_counts.get(item.symbol, 0) + 1
                print(
                    f"[{now_dt.replace(microsecond=0).isoformat()}] ENTRY #{total_opened}/{self.max_trades} "
                    f"{item.symbol} {item.side} 0.01 fill={fill_px} sl={sl_px} "
                    f"slip={slip_bps:+.2f}bps spread={spread_pts}pts comm={comm_usd:+.3f} lat={latency_ms}ms hold={item.hold_sec}s",
                    flush=True,
                )

                # Fail-closed check: verify hard SL is attached on open position!
                if active_pos is not None and float(getattr(active_pos, "sl", 0.0)) <= 0.0:
                    self._close_position(
                        pos=active_pos,
                        trade_seq=item.seq,
                        exit_reason="ORPHAN_NO_SL_ABORT",
                        sl_price_orig=sl_px,
                    )
                    raise SafetyLockError(f"LOCK_3_BROKER_DROPPED_SL_ON_{item.symbol}")

                # Hold window: wake every 5s to log spreads, detect SL_HIT, check 20:55 UTC & red news
                elapsed_hold = 0
                closed_already = False
                while elapsed_hold < item.hold_sec:
                    step = min(self.sample_interval_sec, item.hold_sec - elapsed_hold)
                    self.sleep_fn(step)
                    elapsed_hold += step
                    self._record_spread()

                    cur_positions = self.mt5.positions_get() or []
                    still_open = next(
                        (
                            p
                            for p in cur_positions
                            if int(getattr(p, "ticket", -1)) == pos_id
                            or (pos_id <= 0 and int(getattr(p, "magic", 0)) == PROBE_MAGIC)
                        ),
                        None,
                    )
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
                        closed_already = True
                        return self._summary_dict()

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
                    cur_positions = self.mt5.positions_get() or []
                    still_open = next(
                        (
                            p
                            for p in cur_positions
                            if int(getattr(p, "ticket", -1)) == pos_id
                            or (pos_id <= 0 and int(getattr(p, "magic", 0)) == PROBE_MAGIC)
                        ),
                        None,
                    )
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


# ---------------------------------------------------------------------------
# Offline `--summarize`: Dev M1 Spread Baselines & Realized Friction Multiplier
# ---------------------------------------------------------------------------
def assert_holdout_lock_intact(lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON) -> str:
    if not lock_path.is_file():
        raise SafetyLockError(f"HOLDOUT_LOCK_MISSING: {lock_path}")
    digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    if digest != EXPECTED_HOLDOUT_LOCK_SHA:
        raise SafetyLockError(f"HOLDOUT_LOCK_SHA_MISMATCH: {digest} != {EXPECTED_HOLDOUT_LOCK_SHA}")
    return digest


def compute_dev_m1_spread_baselines(
    *,
    hot_cache_dir: Path = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    verify_sha: bool = False,
) -> dict[str, Any]:
    """Compute Dev M1 (2018-2024, strictly < 2025-01-01, holdout_rows_analysed=0) median spreads by symbol & session."""
    import pyarrow.parquet as pq  # local import so unit tests with injected baselines stay lightweight

    lock_sha = assert_holdout_lock_intact(holdout_lock_path)
    manifest_path = Path(hot_cache_dir) / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"Missing hot M1 cache manifest: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if int(manifest.get("holdout_rows", -1)) != 0 or manifest.get("holdout_lock_sha256") != lock_sha:
        raise SafetyLockError("HOT_M1_CACHE_HOLDOUT_GUARD_MISMATCH")

    holdout_rows_analysed = 0
    max_ts_seen = 0
    by_symbol: dict[str, dict[str, Any]] = {}

    for ftmo_sym in CORE_SYMBOLS:
        meta = SYMBOL_META[ftmo_sym]
        cache_asset = str(meta["cache_asset"])
        am = manifest["assets"][cache_asset]
        folder = Path(hot_cache_dir) / am["dir"]
        scale = float(am["scale"])
        broker_point = float(meta["point"])

        ts_parts = []
        bo_parts = []
        ao_parts = []
        for year_str, ym in sorted(am["years"].items()):
            if int(year_str) >= 2025:
                raise SafetyLockError(f"HOLDOUT_YEAR_DETECTED_IN_HOT_CACHE: {year_str}")
            pq_path = folder / ym["parquet"]
            if verify_sha:
                actual_sha = hashlib.sha256(pq_path.read_bytes()).hexdigest()
                if actual_sha != ym["parquet_sha256"]:
                    raise SafetyLockError(f"HOT_CACHE_SHA_DRIFT: {cache_asset} {year_str}")
            tbl = pq.read_table(pq_path, columns=["minute", "bo", "ao"])
            ts = tbl["minute"].to_numpy().astype(np.int64) * 60
            # Strict causal holdout assertion on every row!
            n_hold = int(np.sum(ts >= HOLDOUT_START_UTC_TS))
            if n_hold > 0:
                raise SafetyLockError(f"HOLDOUT_ROWS_DETECTED: {cache_asset} {year_str} count={n_hold}")
            holdout_rows_analysed += n_hold
            if len(ts) > 0:
                max_ts_seen = max(max_ts_seen, int(ts[-1]))
            ts_parts.append(ts)
            bo_parts.append(tbl["bo"].to_numpy().astype(np.float64) / scale)
            ao_parts.append(tbl["ao"].to_numpy().astype(np.float64) / scale)

        ts_all = np.concatenate(ts_parts)
        bid_all = np.concatenate(bo_parts)
        ask_all = np.concatenate(ao_parts)
        valid = (bid_all > 0.0) & (ask_all >= bid_all)
        ts_all = ts_all[valid]
        bid_all = bid_all[valid]
        ask_all = ask_all[valid]

        spread_px = ask_all - bid_all
        mid_px = 0.5 * (ask_all + bid_all)
        spread_pts = spread_px / broker_point
        spread_bps = (spread_px / mid_px) * 10_000.0
        hours = ((ts_all // 3600) % 24).astype(np.int8)

        sess_masks = {
            "ASIA": (hours < 7) | (hours >= 21),
            "LONDON": (hours >= 7) & (hours < 12),
            "NY_OVERLAP": (hours >= 12) & (hours < 16),
            "NY_AFTERNOON": (hours >= 16) & (hours < 21),
            "OVERALL": np.ones_like(hours, dtype=bool),
        }

        sess_stats: dict[str, dict[str, Any]] = {}
        for sess_name, mask in sess_masks.items():
            cnt = int(np.sum(mask))
            if cnt == 0:
                sess_stats[sess_name] = {
                    "rows": 0,
                    "median_spread_px": 0.0,
                    "median_spread_pts": 0.0,
                    "p90_spread_pts": 0.0,
                    "median_spread_bps": 0.0,
                    "p90_spread_bps": 0.0,
                }
                continue
            sp_px = spread_px[mask]
            sp_pt = spread_pts[mask]
            sp_bp = spread_bps[mask]
            sess_stats[sess_name] = {
                "rows": cnt,
                "median_spread_px": round(float(np.median(sp_px)), 6),
                "median_spread_pts": round(float(np.median(sp_pt)), 3),
                "p90_spread_pts": round(float(np.percentile(sp_pt, 90)), 3),
                "median_spread_bps": round(float(np.median(sp_bp)), 4),
                "p90_spread_bps": round(float(np.percentile(sp_bp, 90)), 4),
            }

        med_mid = float(np.median(mid_px))
        by_symbol[ftmo_sym] = {
            "cache_asset": cache_asset,
            "dev_rows": int(len(ts_all)),
            "dev_median_mid": round(med_mid, 5),
            "sessions": sess_stats,
        }

    # Resolve Dev 1.00x total round-turn friction budgets (spread + commission + base slip)
    usdjpy_dev_mid = float(by_symbol["USDJPY"]["dev_median_mid"]) if "USDJPY" in by_symbol else 130.0
    for ftmo_sym, sym_d in by_symbol.items():
        meta = SYMBOL_META[ftmo_sym]
        ov = sym_d["sessions"]["OVERALL"]
        ref_mid = float(sym_d["dev_median_mid"])
        notional_1lot = estimate_notional_usd(
            symbol=ftmo_sym, volume=1.0, price=ref_mid, usdjpy_ref=usdjpy_dev_mid
        )
        comm_rt_bps = (float(meta["dev_comm_rt_usd_per_lot"]) / notional_1lot) * 10_000.0
        base_slip_rt_bps = (float(meta["dev_base_slip_rt_px"]) / ref_mid) * 10_000.0
        stress_slip_rt_bps = (float(meta["dev_stress_slip_rt_px"]) / ref_mid) * 10_000.0
        dev_1x_rt_bps = float(ov["median_spread_bps"]) + comm_rt_bps + base_slip_rt_bps
        dev_stress_rt_bps = float(ov["median_spread_bps"]) + comm_rt_bps + stress_slip_rt_bps
        sym_d["dev_1x_budget"] = {
            "spread_rt_bps": round(float(ov["median_spread_bps"]), 4),
            "commission_rt_bps": round(comm_rt_bps, 4),
            "base_slip_rt_bps": round(base_slip_rt_bps, 4),
            "stress_slip_rt_bps": round(stress_slip_rt_bps, 4),
            "total_1x_rt_bps": round(dev_1x_rt_bps, 4),
            "total_stress_rt_bps": round(dev_stress_rt_bps, 4),
            "tracker_budget_rt_bps": round(2.0 * float(meta["tracker_oneway_budget_bps"]), 4),
        }

    return {
        "holdout_lock_sha256": lock_sha,
        "holdout_rows_analysed": holdout_rows_analysed,
        "dev_m1_max_utc": datetime.fromtimestamp(max_ts_seen, timezone.utc).isoformat() if max_ts_seen > 0 else None,
        "by_symbol": by_symbol,
    }


def _percentile(vals: list[float], pct_val: float) -> float:
    if not vals:
        return 0.0
    return float(np.percentile(np.asarray(vals, dtype=np.float64), pct_val))


def summarize_calibration_and_spreads(
    *,
    spread_log_path: Path = DEFAULT_SPREAD_LOG,
    fills_csv_path: Path = DEFAULT_FILLS_CSV,
    summary_json_path: Path | None = DEFAULT_SUMMARY_JSON,
    hot_cache_dir: Path = DEFAULT_HOT_M1_CACHE,
    holdout_lock_path: Path = DEFAULT_HOLDOUT_LOCK_JSON,
    dev_m1_baselines: dict[str, Any] | None = None,
    verify_dev_sha: bool = False,
) -> dict[str, Any]:
    """Compute FTMO Live Spread / Dev M1 Spread ratios & Realized Friction Multiplier (OrderSend=0, holdout=0)."""
    dev_base = (
        dev_m1_baselines
        if dev_m1_baselines is not None
        else compute_dev_m1_spread_baselines(
            hot_cache_dir=hot_cache_dir,
            holdout_lock_path=holdout_lock_path,
            verify_sha=verify_dev_sha,
        )
    )
    if int(dev_base.get("holdout_rows_analysed", -1)) != 0:
        raise SafetyLockError("HOLDOUT_CONTAMINATION_DETECTED_IN_SUMMARY")

    # 1. Aggregate live spread log by symbol & session
    spread_rows = pct.load_spread_log_rows(spread_log_path)
    live_spreads: dict[str, dict[str, dict[str, list[float]]]] = {
        sym: {s: {"pts": [], "bps": [], "px": []} for s in (*SESSION_ORDER, "OVERALL")}
        for sym in CORE_SYMBOLS
    }
    logins_in_spread_log: set[int] = set()

    for row in spread_rows:
        acct = row.get("account")
        if isinstance(acct, dict) and acct.get("login"):
            logins_in_spread_log.add(int(acct["login"]))
        ts_val = int(row.get("captured_utc_ts") or 0)
        sess = str(row.get("session") or "").strip().upper()
        if sess not in SESSION_ORDER:
            sess = tag_session_utc(datetime.fromtimestamp(ts_val, timezone.utc)) if ts_val > 0 else "ASIA"
        quotes = row.get("quotes")
        if not isinstance(quotes, dict):
            continue
        for sym in CORE_SYMBOLS:
            q = quotes.get(sym)
            if not isinstance(q, dict) or not q.get("available"):
                continue
            bid = float(q.get("bid") or 0.0)
            ask = float(q.get("ask") or 0.0)
            if bid <= 0.0 or ask <= 0.0 or ask < bid:
                continue
            pt = float(q.get("point") or SYMBOL_META[sym]["point"])
            sp_px = ask - bid
            mid = 0.5 * (ask + bid)
            sp_pts = float(q.get("spread_pts")) if q.get("spread_pts") is not None else (sp_px / pt)
            sp_bps = float(q.get("spread_bps")) if q.get("spread_bps") is not None else ((sp_px / mid) * 10_000.0)
            for bucket in (sess, "OVERALL"):
                live_spreads[sym][bucket]["pts"].append(sp_pts)
                live_spreads[sym][bucket]["bps"].append(sp_bps)
                live_spreads[sym][bucket]["px"].append(sp_px)

    spread_comparison: dict[str, dict[str, Any]] = {}
    for sym in CORE_SYMBOLS:
        dev_sym = dev_base["by_symbol"][sym]
        sym_out: dict[str, Any] = {}
        for sess in (*SESSION_ORDER, "OVERALL"):
            pts_arr = live_spreads[sym][sess]["pts"]
            bps_arr = live_spreads[sym][sess]["bps"]
            dev_s = dev_sym["sessions"][sess]
            if not pts_arr:
                sym_out[sess] = {
                    "live_samples": 0,
                    "live_median_spread_pts": None,
                    "live_p90_spread_pts": None,
                    "live_median_spread_bps": None,
                    "live_p90_spread_bps": None,
                    "dev_m1_median_spread_pts": dev_s["median_spread_pts"],
                    "dev_m1_median_spread_bps": dev_s["median_spread_bps"],
                    "live_to_dev_spread_ratio_pts": None,
                    "live_to_dev_spread_ratio_bps": None,
                }
                continue
            l_med_pts = _percentile(pts_arr, 50)
            l_p90_pts = _percentile(pts_arr, 90)
            l_med_bps = _percentile(bps_arr, 50)
            l_p90_bps = _percentile(bps_arr, 90)
            d_med_pts = float(dev_s["median_spread_pts"])
            d_med_bps = float(dev_s["median_spread_bps"])
            sym_out[sess] = {
                "live_samples": len(pts_arr),
                "live_median_spread_pts": round(l_med_pts, 3),
                "live_p90_spread_pts": round(l_p90_pts, 3),
                "live_median_spread_bps": round(l_med_bps, 4),
                "live_p90_spread_bps": round(l_p90_bps, 4),
                "dev_m1_median_spread_pts": round(d_med_pts, 3),
                "dev_m1_median_spread_bps": round(d_med_bps, 4),
                "live_to_dev_spread_ratio_pts": round(l_med_pts / d_med_pts, 3) if d_med_pts > 0 else None,
                "live_to_dev_spread_ratio_bps": round(l_med_bps / d_med_bps, 3) if d_med_bps > 0 else None,
            }
        spread_comparison[sym] = sym_out

    # 2. Parse calibration fills CSV (live non-dry-run fills ONLY!)
    live_fills: list[dict[str, Any]] = []
    dryrun_rows_ignored = 0
    reject_rows = 0
    swap_nonzero_count = 0
    after_cutoff_count = 0

    if fills_csv_path.is_file():
        with fills_csv_path.open("r", encoding="utf-8", errors="replace", newline="") as f:
            for r in csv.DictReader(f):
                if str(r.get("dry_run", "")).strip().lower() in ("true", "1", "yes"):
                    dryrun_rows_ignored += 1
                    continue
                leg = str(r.get("leg", "")).strip().upper()
                if leg == "ENTRY_REJECT" or int(float(r.get("retcode") or 0)) != 10009:
                    reject_rows += 1
                    continue
                if leg not in ("ENTRY", "EXIT"):
                    continue
                ts_val = int(float(r.get("utc_ts") or 0))
                if ts_val > 0 and is_past_flatten_cutoff(datetime.fromtimestamp(ts_val, timezone.utc)):
                    after_cutoff_count += 1
                sw = float(r.get("swap_usd") or 0.0)
                if abs(sw) > 1e-6:
                    swap_nonzero_count += 1
                live_fills.append({
                    "utc_ts": ts_val,
                    "session": str(r.get("session") or ""),
                    "trade_seq": int(float(r.get("trade_seq") or 0)),
                    "position_id": str(r.get("position_id") or ""),
                    "symbol": str(r.get("symbol") or "").strip(),
                    "leg": leg,
                    "side": str(r.get("side") or "").strip().upper(),
                    "exit_reason": str(r.get("exit_reason") or "").strip().upper(),
                    "pre_spread_bps": float(r.get("pre_spread_bps") or 0.0),
                    "adverse_slip_pts": float(r.get("adverse_slip_pts") or 0.0),
                    "adverse_slip_bps": float(r.get("adverse_slip_bps") or 0.0),
                    "latency_ms": float(r.get("latency_ms") or 0.0),
                    "commission_usd": float(r.get("commission_usd") or 0.0),
                    "commission_bps": float(r.get("commission_bps") or 0.0),
                    "swap_usd": sw,
                    "pnl_usd": float(r.get("pnl_usd") or 0.0),
                })

    # 3. Compute Realized Friction Multiplier per symbol & Core-4 portfolio
    realized_friction: dict[str, dict[str, Any]] = {}
    all_mult_p50: list[float] = []
    all_mult_p90: list[float] = []
    all_latencies: list[float] = []

    for sym in CORE_SYMBOLS:
        sym_fills = [x for x in live_fills if x["symbol"] == sym]
        entries = [x for x in sym_fills if x["leg"] == "ENTRY"]
        exits = [x for x in sym_fills if x["leg"] == "EXIT"]
        sl_exits = [x for x in exits if x["exit_reason"] == "SL_HIT"]

        dev_budget = dev_base["by_symbol"][sym]["dev_1x_budget"]
        dev_1x_rt_bps = float(dev_budget["total_1x_rt_bps"])

        # Pair round-trips by position_id (falling back to trade_seq)
        ent_by_key = {(x["position_id"] or str(x["trade_seq"])): x for x in entries}
        rt_slips_signed: list[float] = []
        rt_slips_pos: list[float] = []
        rt_comm_bps: list[float] = []
        rt_spreads_bps: list[float] = []
        for ex in exits:
            k = ex["position_id"] or str(ex["trade_seq"])
            en = ent_by_key.get(k)
            if en is not None:
                s_signed = en["adverse_slip_bps"] + ex["adverse_slip_bps"]
                s_pos = max(0.0, en["adverse_slip_bps"]) + max(0.0, ex["adverse_slip_bps"])
                c_rt = en["commission_bps"] + ex["commission_bps"]
                sp_rt = 0.5 * (en["pre_spread_bps"] + ex["pre_spread_bps"])
                rt_slips_signed.append(s_signed)
                rt_slips_pos.append(s_pos)
                rt_comm_bps.append(c_rt)
                rt_spreads_bps.append(sp_rt)

        # Fallback if entries exist without paired exits yet
        if not rt_slips_signed and sym_fills:
            rt_slips_signed = [2.0 * x["adverse_slip_bps"] for x in sym_fills]
            rt_slips_pos = [2.0 * max(0.0, x["adverse_slip_bps"]) for x in sym_fills]
            rt_comm_bps = [2.0 * x["commission_bps"] for x in sym_fills]
            rt_spreads_bps = [x["pre_spread_bps"] for x in sym_fills]

        # Live spread (prefer continuous 5s spread recorder OVERALL; fallback to fill pre-trade spreads)
        ov_sp = spread_comparison[sym]["OVERALL"]
        live_sp_p50 = (
            float(ov_sp["live_median_spread_bps"])
            if ov_sp["live_median_spread_bps"] is not None
            else (_percentile(rt_spreads_bps, 50) if rt_spreads_bps else 0.0)
        )
        live_sp_p90 = (
            float(ov_sp["live_p90_spread_bps"])
            if ov_sp["live_p90_spread_bps"] is not None
            else (_percentile(rt_spreads_bps, 90) if rt_spreads_bps else 0.0)
        )

        lat_list = [x["latency_ms"] for x in sym_fills if x["latency_ms"] > 0.0]
        all_latencies.extend(lat_list)

        if not sym_fills:
            realized_friction[sym] = {
                "entries": 0,
                "exits": 0,
                "sl_exits": 0,
                "live_spread_p50_bps": round(live_sp_p50, 4) if ov_sp["live_samples"] > 0 else None,
                "live_spread_p90_bps": round(live_sp_p90, 4) if ov_sp["live_samples"] > 0 else None,
                "dev_1x_budget_rt_bps": round(dev_1x_rt_bps, 4),
                "realized_friction_multiplier_p50": None,
                "realized_friction_multiplier_p90": None,
                "status": "NO_LIVE_FILLS_YET",
            }
            continue

        slip_p50_pos = _percentile(rt_slips_pos, 50)
        slip_p90_pos = _percentile(rt_slips_pos, 90)
        slip_p50_signed = _percentile(rt_slips_signed, 50)
        slip_p90_signed = _percentile(rt_slips_signed, 90)
        comm_p50 = _percentile(rt_comm_bps, 50)

        # Conservative positive-adverse friction AND signed net friction
        realized_rt_p50_bps = live_sp_p50 + comm_p50 + slip_p50_pos
        realized_rt_p90_bps = live_sp_p90 + comm_p50 + slip_p90_pos
        realized_rt_p50_signed_bps = live_sp_p50 + comm_p50 + slip_p50_signed

        mult_p50 = realized_rt_p50_bps / max(1e-6, dev_1x_rt_bps)
        mult_p90 = realized_rt_p90_bps / max(1e-6, dev_1x_rt_bps)
        all_mult_p50.append(mult_p50)
        all_mult_p90.append(mult_p90)

        realized_friction[sym] = {
            "entries": len(entries),
            "exits": len(exits),
            "paired_roundtrips": len(rt_slips_pos),
            "sl_exits": len(sl_exits),
            "sl_adverse_slip_p50_bps": round(_percentile([x["adverse_slip_bps"] for x in sl_exits], 50), 4) if sl_exits else None,
            "sl_adverse_slip_p90_bps": round(_percentile([x["adverse_slip_bps"] for x in sl_exits], 90), 4) if sl_exits else None,
            "entry_adverse_slip_p50_bps": round(_percentile([x["adverse_slip_bps"] for x in entries], 50), 4) if entries else None,
            "exit_adverse_slip_p50_bps": round(_percentile([x["adverse_slip_bps"] for x in exits], 50), 4) if exits else None,
            "rt_adverse_slip_p50_pos_bps": round(slip_p50_pos, 4),
            "rt_adverse_slip_p90_pos_bps": round(slip_p90_pos, 4),
            "rt_adverse_slip_p50_signed_bps": round(slip_p50_signed, 4),
            "rt_adverse_slip_p90_signed_bps": round(slip_p90_signed, 4),
            "live_spread_p50_bps": round(live_sp_p50, 4),
            "live_spread_p90_bps": round(live_sp_p90, 4),
            "commission_rt_p50_bps": round(comm_p50, 4),
            "realized_rt_friction_p50_bps": round(realized_rt_p50_bps, 4),
            "realized_rt_friction_p90_bps": round(realized_rt_p90_bps, 4),
            "realized_rt_friction_p50_signed_bps": round(realized_rt_p50_signed_bps, 4),
            "dev_1x_budget_rt_bps": round(dev_1x_rt_bps, 4),
            "tracker_budget_rt_bps": round(float(dev_budget["tracker_budget_rt_bps"]), 4),
            "realized_friction_multiplier_p50": round(mult_p50, 3),
            "realized_friction_multiplier_p90": round(mult_p90, 3),
            "latency_p50_ms": round(_percentile(lat_list, 50), 2) if lat_list else None,
            "latency_p90_ms": round(_percentile(lat_list, 90), 2) if lat_list else None,
            "net_pnl_usd": round(sum(x["pnl_usd"] for x in exits), 4),
            "total_commission_usd": round(sum(x["commission_usd"] for x in sym_fills), 4),
            "total_swap_usd": round(sum(x["swap_usd"] for x in sym_fills), 4),
            "status": (
                "BREACH_ABOVE_2_0X"
                if mult_p50 > 2.0
                else ("WARN_ELEVATED_1_5X_TO_2_0X" if mult_p50 > 1.5 else "PASS_WITHIN_1_5X")
            ),
        }

    port_mult_p50 = round(float(np.mean(all_mult_p50)), 3) if all_mult_p50 else None
    port_mult_p90 = round(float(np.mean(all_mult_p90)), 3) if all_mult_p90 else None

    if not live_fills:
        overall_verdict = "PRE_TRADE_SPREAD_ONLY"
    elif swap_nonzero_count > 0 or after_cutoff_count > 0:
        overall_verdict = "COMPLIANCE_VIOLATION"
    elif port_mult_p50 is not None and port_mult_p50 > 2.0:
        overall_verdict = "BREACH_ABOVE_2_0X"
    elif port_mult_p50 is not None and port_mult_p50 > 1.5:
        overall_verdict = "WARN_ELEVATED_1_5X_TO_2_0X"
    else:
        overall_verdict = "PASS_WITHIN_1_5X"

    payload = {
        "schema": "naqex-ftmo-realized-friction-summary-v1",
        "generated_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "order_send_count": 0,
        "calibration_account_login": ALLOWED_DEMO_LOGIN,
        "server": ALLOWED_SERVER,
        "holdout_lock_sha256": dev_base["holdout_lock_sha256"],
        "holdout_rows_analysed": int(dev_base["holdout_rows_analysed"]),
        "dev_m1_max_utc": dev_base.get("dev_m1_max_utc"),
        "verdict": overall_verdict,
        "inputs": {
            "spread_log_path": str(spread_log_path),
            "spread_log_rows_total": len(spread_rows),
            "spread_log_logins_observed": sorted(logins_in_spread_log),
            "fills_csv_path": str(fills_csv_path),
            "live_fill_legs_total": len(live_fills),
            "dryrun_rows_ignored": dryrun_rows_ignored,
            "rejected_orders": reject_rows,
        },
        "compliance": {
            "swap_nonzero_count": swap_nonzero_count,
            "after_2055_utc_count": after_cutoff_count,
            "zero_swap_ok": swap_nonzero_count == 0,
            "cutoff_ok": after_cutoff_count == 0,
        },
        "portfolio_core4": {
            "symbols_with_live_fills": len(all_mult_p50),
            "realized_friction_multiplier_p50": port_mult_p50,
            "realized_friction_multiplier_p90": port_mult_p90,
            "latency_p50_ms": round(_percentile(all_latencies, 50), 2) if all_latencies else None,
            "latency_p90_ms": round(_percentile(all_latencies, 90), 2) if all_latencies else None,
            "net_pnl_usd": round(sum(x["pnl_usd"] for x in live_fills if x["leg"] == "EXIT"), 4),
            "total_commission_usd": round(sum(x["commission_usd"] for x in live_fills), 4),
            "total_swap_usd": round(sum(x["swap_usd"] for x in live_fills), 4),
        },
        "spread_vs_dev_m1": spread_comparison,
        "realized_friction_by_symbol": realized_friction,
    }

    if summary_json_path is not None:
        summary_json_path.parent.mkdir(parents=True, exist_ok=True)
        summary_json_path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    return payload


# ---------------------------------------------------------------------------
# MT5 Session Lifecycle (ONLY called when NOT `--summarize`)
# ---------------------------------------------------------------------------
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
    mt5 = mt5_mod
    if mt5 is None:
        import MetaTrader5 as mt5  # type: ignore

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


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------
def build_arg_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(
        description=(
            "Fail-closed FTMO-Demo secondary calibration probe (login 1515343318 ONLY) "
            "& 5s live spread recorder. Defaults strictly to --dry-run (OrderSend=0)."
        )
    )
    mode_grp = ap.add_mutually_exclusive_group()
    mode_grp.add_argument(
        "--dry-run",
        action="store_true",
        help="Default fail-closed dry-run mode (OrderSend=0).",
    )
    mode_grp.add_argument(
        "--execute-demo-1515343318-calibration",
        action="store_true",
        dest="execute_live",
        help="Explicitly unlock 0.01-lot demo calibration orders on secondary login 1515343318 ONLY.",
    )
    mode_grp.add_argument(
        "--spread-only",
        action="store_true",
        help="Run ONLY the 5s live spread recorder (OrderSend=0).",
    )
    mode_grp.add_argument(
        "--summarize",
        action="store_true",
        help="Offline summary mode (ZERO MT5 launch, OrderSend=0, holdout_rows_analysed=0).",
    )

    ap.add_argument("--env-file", type=Path, default=DEFAULT_ENV_PATH)
    ap.add_argument("--news-csv", type=Path, default=DEFAULT_NEWS_CSV)
    ap.add_argument("--spread-log", type=Path, default=DEFAULT_SPREAD_LOG)
    ap.add_argument("--fills-csv", type=Path, default=DEFAULT_FILLS_CSV)
    ap.add_argument("--summary-json", type=Path, default=DEFAULT_SUMMARY_JSON)
    ap.add_argument("--portable-dir", type=Path, default=DEFAULT_PORTABLE_DIR)
    ap.add_argument("--hot-cache-dir", type=Path, default=DEFAULT_HOT_M1_CACHE)
    ap.add_argument("--sample-interval-sec", type=int, default=SPREAD_SAMPLE_INTERVAL_SEC)
    ap.add_argument("--max-trades", type=int, default=MAX_TOTAL_TRADES)
    ap.add_argument("--gap-sec", type=int, default=None, help="Optional inter-trade gap override in seconds (min 60s).")
    ap.add_argument("--max-samples", type=int, default=1, help="Max samples for --spread-only (0=until duration).")
    ap.add_argument("--duration-sec", type=int, default=None, help="Optional max duration in seconds.")
    ap.add_argument("--verify-dev-sha", action="store_true")
    return ap


def main(
    argv: list[str] | None = None,
    *,
    mt5_mod: Any = None,
    process_lister: Callable[[], list[str]] = list_running_terminal_processes,
    clock_fn: Callable[[], datetime] | None = None,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> int:
    ap = build_arg_parser()
    args = ap.parse_args(argv)

    if args.max_trades > MAX_TOTAL_TRADES or args.max_trades < 1:
        raise SafetyLockError(f"LOCK_3_INVALID_MAX_TRADES: {args.max_trades} not in [1, {MAX_TOTAL_TRADES}]")

    if args.summarize:
        summary = summarize_calibration_and_spreads(
            spread_log_path=args.spread_log,
            fills_csv_path=args.fills_csv,
            summary_json_path=args.summary_json,
            hot_cache_dir=args.hot_cache_dir,
            verify_dev_sha=args.verify_dev_sha,
        )
        print(json.dumps({
            "schema": summary["schema"],
            "verdict": summary["verdict"],
            "holdout_rows_analysed": summary["holdout_rows_analysed"],
            "spread_log_rows_total": summary["inputs"]["spread_log_rows_total"],
            "live_fill_legs_total": summary["inputs"]["live_fill_legs_total"],
            "portfolio_core4": summary["portfolio_core4"],
            "summary_json": str(args.summary_json),
        }, indent=2, ensure_ascii=False))
        return 0

    creds = load_ftmo_trial_env(args.env_file)
    news_events = load_red_news_calendar(args.news_csv)
    execute_live = bool(args.execute_live)

    mt5, proc = _connect_isolated_mt5(
        creds=creds,
        portable_dir=args.portable_dir,
        allow_trading=execute_live,
        mt5_mod=mt5_mod,
        process_lister=process_lister,
    )
    try:
        runner = CalibrationProbeRunner(
            mt5=mt5,
            execute_live=execute_live,
            news_events=news_events,
            spread_log_path=args.spread_log,
            fills_csv_path=args.fills_csv,
            sample_interval_sec=args.sample_interval_sec,
            max_trades=args.max_trades,
            gap_sec_override=args.gap_sec,
            max_runtime_sec=args.duration_sec,
            terminal_data_path=args.portable_dir,
            clock_fn=clock_fn,
            sleep_fn=sleep_fn,
        )
        if args.spread_only:
            out = runner.run_spread_only(max_samples=args.max_samples, duration_sec=args.duration_sec)
        else:
            out = runner.run_calibration()
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    finally:
        _teardown_isolated_mt5(mt5, proc, ini_path=args.portable_dir / "connector.ini")


if __name__ == "__main__":
    raise SystemExit(main())
