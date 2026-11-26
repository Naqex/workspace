"""Hard-locked invariants, paths, and symbol metadata for FTMO-Demo calibration probe."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

EXPORTS_DIR = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR = EXPORTS_DIR.parent

for _p in (AI_ENGINES_DIR, EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from quant_core.io_utils import repo_root_from  # noqa: E402

REPO_ROOT = repo_root_from(__file__)

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
        "sl_min_units": 10.0,  # pips
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
        "sl_min_units": 10.0,  # pips
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
        "sl_min_units": 10.0,  # pips
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
        "pip_size": 1.0,  # 1.0 index point = 100 broker points (point=0.01)
        "contract_size": 1.0,
        "is_index": True,
        "sl_min_units": 25.0,  # index points
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
