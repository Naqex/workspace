"""Shared constants, paths, program definitions, and synchronized caches for Cockpit."""

from __future__ import annotations

import re
import sys
import threading
import types
import urllib.request
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from quant_core.io_utils import repo_root_from

COCKPIT_DIR = Path(__file__).resolve().parents[1]
STATIC_DIR = COCKPIT_DIR / "static"
AI_ENGINES = COCKPIT_DIR.parent
ROOT = repo_root_from(COCKPIT_DIR)

ORDER_SEND_COUNT = 0
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8787

_SLEEVE1_LOCK = threading.Lock()
_SLEEVE1_CACHE: tuple[dict[str, float], dict[str, Any]] | None = None
_STRESS_CACHE_LOCK = threading.Lock()
_STRESS_MD_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_HEROKU_CACHE_LOCK = threading.Lock()
_HEROKU_STATUS_CACHE: tuple[float, dict[str, Any] | None] = (0.0, None)
_SPRINT_CACHE_LOCK = threading.Lock()
_SPRINT_CACHE: dict[str, tuple[float, dict[str, Any]]] = {}
_NODE1_CACHE_LOCK = threading.Lock()
_NODE1_CACHE: dict[tuple[str, bool], tuple[float, dict[str, Any]]] = {}

VN_TZ = timezone(timedelta(hours=7))

BLACKFRIDAY_DEADLINE_ISO = "2026-11-30T09:00:00Z"
BLACKFRIDAY_DEADLINE_ICT = "30/11/2026 16:00 ICT"
BLACKFRIDAY_DEADLINE_DT = datetime(2026, 11, 30, 9, 0, 0, tzinfo=UTC)
SPRINT_CACHE_TTL_SEC = 30.0
NODE1_CACHE_TTL_SEC = 30.0
NODE1_SSH_TIMEOUT_SEC = 4.0

CORE_DEV_SPREAD_BASELINE_BPS: dict[str, float] = {
    "USDJPY": 1.30,
    "GBPUSD": 1.50,
    "EURJPY": 1.50,
    "US100.cash": 2.25,
}
_NTP_OFFSET_RE = re.compile(r"[+-]?\d+(?:\.\d+)?s\b")
_IPV4_OR_URL_RE = re.compile(r"(?:https?://\S+|\b(?:\d{1,3}\.){3}\d{1,3}\b)", re.IGNORECASE)

PROP_METRIX_PROGRAMS: dict[str, dict[str, Any]] = {
    "ftmo_free_trial_10k": {
        "id": "ftmo_free_trial_10k",
        "label": "FTMO Free Trial 10K (Swing)",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 500.0,
        "min_trading_days": 2,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_10k_p1": {
        "id": "ftmo_swing_10k_p1",
        "label": "FTMO Swing 10K — Phase 1",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 1_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_25k_p1": {
        "id": "ftmo_swing_25k_p1",
        "label": "FTMO Swing 25K — Phase 1",
        "initial_usd": 25_000.0,
        "daily_loss_usd": 1_250.0,
        "max_loss_usd": 2_500.0,
        "profit_target_usd": 2_500.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_50k_p1": {
        "id": "ftmo_swing_50k_p1",
        "label": "FTMO Swing 50K — Phase 1",
        "initial_usd": 50_000.0,
        "daily_loss_usd": 2_500.0,
        "max_loss_usd": 5_000.0,
        "profit_target_usd": 5_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_100k_p1": {
        "id": "ftmo_swing_100k_p1",
        "label": "FTMO Swing 100K — Phase 1",
        "initial_usd": 100_000.0,
        "daily_loss_usd": 5_000.0,
        "max_loss_usd": 10_000.0,
        "profit_target_usd": 10_000.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_swing_10k_p2": {
        "id": "ftmo_swing_10k_p2",
        "label": "FTMO Swing 10K — Phase 2",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": 500.0,
        "min_trading_days": 4,
        "min_profitable_day_pct": 0.0,
    },
    "ftmo_funded_10k": {
        "id": "ftmo_funded_10k",
        "label": "FTMO Funded 10K",
        "initial_usd": 10_000.0,
        "daily_loss_usd": 500.0,
        "max_loss_usd": 1_000.0,
        "profit_target_usd": None,
        "min_trading_days": 0,
        "min_profitable_day_pct": 0.0,
    },
    "the5ers_hs_5k_p1": {
        "id": "the5ers_hs_5k_p1",
        "label": "The5ers High Stakes 5K — Step 1",
        "initial_usd": 5_000.0,
        "daily_loss_usd": 250.0,
        "max_loss_usd": 500.0,
        "profit_target_usd": 400.0,
        "min_trading_days": 3,
        "min_profitable_day_pct": 0.5,
    },
    "the5ers_hs_20k_p1": {
        "id": "the5ers_hs_20k_p1",
        "label": "The5ers High Stakes 20K — Step 1",
        "initial_usd": 20_000.0,
        "daily_loss_usd": 1_000.0,
        "max_loss_usd": 2_000.0,
        "profit_target_usd": 1_600.0,
        "min_trading_days": 3,
        "min_profitable_day_pct": 0.5,
    },
}
PROP_PROGRAMS = PROP_METRIX_PROGRAMS

MIME_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".js": "application/javascript; charset=utf-8",
    ".json": "application/json; charset=utf-8",
    ".svg": "image/svg+xml",
}

EMERGENCY_CONFIRM_CODES = {
    "HALT_NEW_ENTRIES": "HALT",
    "FLATTEN_ALL": "FLATTEN",
    "RESET_NORMAL": "RESET",
}


_REGISTERED_FACADES: list[types.ModuleType] = []


def register_facade_module(mod: types.ModuleType) -> None:
    """Register a loaded `cockpit/server.py` façade (package or direct-script import)."""
    if all(existing is not mod for existing in _REGISTERED_FACADES):
        _REGISTERED_FACADES.append(mod)


def _facade_modules() -> list[types.ModuleType]:
    server_file = str((COCKPIT_DIR / "server.py").resolve())
    seen: set[int] = set()
    out: list[types.ModuleType] = []
    candidates: list[Any] = [*_REGISTERED_FACADES, sys.modules.get("cockpit.server")]
    for mod in list(sys.modules.values()):
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file:
            try:
                if str(Path(mod_file).resolve()) == server_file:
                    candidates.append(mod)
            except OSError:
                pass
    for mod in candidates:
        if isinstance(mod, types.ModuleType) and id(mod) not in seen:
            seen.add(id(mod))
            out.append(mod)
    return out


def _facade_module() -> Any | None:
    mods = _facade_modules()
    return mods[0] if mods else None


def get_urllib_request() -> Any:
    """Resolve urllib.request honoring monkeypatches on any `cockpit/server.py` façade."""
    return urllib.request


def get_heroku_status_cache() -> tuple[float, dict[str, Any] | None]:
    """Read `_HEROKU_STATUS_CACHE`, kept in sync with all `cockpit/server.py` façades."""
    return _HEROKU_STATUS_CACHE


def set_heroku_status_cache(value: tuple[float, dict[str, Any] | None]) -> None:
    """Update `_HEROKU_STATUS_CACHE` in state and all loaded `cockpit/server.py` façades."""
    global _HEROKU_STATUS_CACHE
    _HEROKU_STATUS_CACHE = value
    for mod in _facade_modules():
        types.ModuleType.__setattr__(mod, "_HEROKU_STATUS_CACHE", value)


def get_sleeve1_cache() -> tuple[dict[str, float], dict[str, Any]] | None:
    """Read `_SLEEVE1_CACHE`, kept in sync with all `cockpit/server.py` façades."""
    return _SLEEVE1_CACHE


def set_sleeve1_cache(value: tuple[dict[str, float], dict[str, Any]] | None) -> None:
    """Update `_SLEEVE1_CACHE` in state and all loaded `cockpit/server.py` façades."""
    global _SLEEVE1_CACHE
    _SLEEVE1_CACHE = value
    for mod in _facade_modules():
        types.ModuleType.__setattr__(mod, "_SLEEVE1_CACHE", value)


def get_sprint_cache() -> dict[str, tuple[float, dict[str, Any]]]:
    return _SPRINT_CACHE


def get_node1_cache() -> dict[tuple[str, bool], tuple[float, dict[str, Any]]]:
    return _NODE1_CACHE


def get_stress_md_cache() -> dict[str, tuple[float, dict[str, Any]]]:
    return _STRESS_MD_CACHE


def clear_sprint_and_node1_caches() -> None:
    """Clear in-memory 30s TTL caches for /api/blackfriday-sprint and /api/node1-summary."""
    with _SPRINT_CACHE_LOCK:
        _SPRINT_CACHE.clear()
        for mod in _facade_modules():
            val = getattr(mod, "_SPRINT_CACHE", None)
            if isinstance(val, dict):
                val.clear()
    with _NODE1_CACHE_LOCK:
        _NODE1_CACHE.clear()
        for mod in _facade_modules():
            val = getattr(mod, "_NODE1_CACHE", None)
            if isinstance(val, dict):
                val.clear()
