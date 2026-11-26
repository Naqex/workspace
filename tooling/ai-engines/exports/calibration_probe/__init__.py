"""Modular package for the fail-closed FTMO-Demo secondary calibration probe (`1515343318`)."""

from __future__ import annotations

import sys
from pathlib import Path

_EXPORTS_DIR = Path(__file__).resolve().parents[1]
_AI_ENGINES_DIR = _EXPORTS_DIR.parent
for _p in (_AI_ENGINES_DIR, _EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from exports.calibration_probe.baselines import compute_dev_m1_spread_baselines  # noqa: E402
from exports.calibration_probe.cli import build_arg_parser, main  # noqa: E402
from exports.calibration_probe.constants import (  # noqa: E402
    AI_ENGINES_DIR,
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    BOJ_ESTIMATED_PAD_SEC,
    CORE_SYMBOLS,
    DEFAULT_ENV_PATH,
    DEFAULT_FILLS_CSV,
    DEFAULT_HOLDOUT_LOCK_JSON,
    DEFAULT_HOT_M1_CACHE,
    DEFAULT_NEWS_CSV,
    DEFAULT_PORTABLE_DIR,
    DEFAULT_SPREAD_LOG,
    DEFAULT_SUMMARY_JSON,
    ENV_ALLOWED_KEYS,
    EXPECTED_HOLDOUT_LOCK_SHA,
    EXPORTS_DIR,
    FILLS_CSV_COLUMNS,
    FIXED_VOLUME_LOTS,
    FORBIDDEN_LOGINS,
    FORBIDDEN_PATH_TOKENS,
    HARD_FLATTEN_CUTOFF_HOUR,
    HARD_FLATTEN_CUTOFF_MINUTE,
    HOLDOUT_START_UTC_TS,
    MAX_OPEN_POSITIONS,
    MAX_TOTAL_TRADES,
    PROBE_MAGIC,
    RED_NEWS_BLOCK_WINDOW_SEC,
    RED_NEWS_HARD_BAN_SEC,
    RED_NEWS_PRE_FLATTEN_SEC,
    REPO_ROOT,
    SESSION_ORDER,
    SPREAD_SAMPLE_INTERVAL_SEC,
    SYMBOL_META,
    TERMINAL_BINARIES,
    TRADES_PER_SYMBOL,
)
from exports.calibration_probe.math_schedule import (  # noqa: E402
    build_calibration_schedule,
    compute_adverse_slippage,
    compute_sl_price,
    estimate_notional_usd,
)
from exports.calibration_probe.models import (  # noqa: E402
    PlannedCalibrationTrade,
    RedactedCredentials,
    SafetyLockError,
)
from exports.calibration_probe.mt5_session import (  # noqa: E402
    _connect_isolated_mt5,
    _lookup_deal_details,
    _pick_filling_mode,
    _teardown_isolated_mt5,
    capture_spread_snapshot,
    prepare_isolated_portable_terminal,
)
from exports.calibration_probe.parsers import (  # noqa: E402
    append_fill_csv,
    append_jsonl,
    load_existing_live_entry_counts,
    load_ftmo_trial_env,
    load_red_news_calendar,
)
from exports.calibration_probe.reporting import (  # noqa: E402
    _percentile,
    summarize_calibration_and_spreads,
)
from exports.calibration_probe.runner import CalibrationProbeRunner  # noqa: E402
from exports.calibration_probe.validators import (  # noqa: E402
    assert_all_entry_locks,
    assert_holdout_lock_intact,
    assert_no_concurrent_mt5,
    assert_safe_portable_path,
    find_approaching_pre_flatten_news,
    find_blocking_red_news,
    is_past_flatten_cutoff,
    list_running_terminal_processes,
    tag_session_utc,
    validate_calibration_account,
    validate_fixed_volume,
    validate_mandatory_sl,
)
from quant_factory import prop_challenge_tracker as pct  # noqa: E402

__all__ = [
    "AI_ENGINES_DIR",
    "ALLOWED_DEMO_LOGIN",
    "ALLOWED_SERVER",
    "BOJ_ESTIMATED_PAD_SEC",
    "CORE_SYMBOLS",
    "CalibrationProbeRunner",
    "DEFAULT_ENV_PATH",
    "DEFAULT_FILLS_CSV",
    "DEFAULT_HOLDOUT_LOCK_JSON",
    "DEFAULT_HOT_M1_CACHE",
    "DEFAULT_NEWS_CSV",
    "DEFAULT_PORTABLE_DIR",
    "DEFAULT_SPREAD_LOG",
    "DEFAULT_SUMMARY_JSON",
    "ENV_ALLOWED_KEYS",
    "EXPECTED_HOLDOUT_LOCK_SHA",
    "EXPORTS_DIR",
    "FILLS_CSV_COLUMNS",
    "FIXED_VOLUME_LOTS",
    "FORBIDDEN_LOGINS",
    "FORBIDDEN_PATH_TOKENS",
    "HARD_FLATTEN_CUTOFF_HOUR",
    "HARD_FLATTEN_CUTOFF_MINUTE",
    "HOLDOUT_START_UTC_TS",
    "MAX_OPEN_POSITIONS",
    "MAX_TOTAL_TRADES",
    "PROBE_MAGIC",
    "PlannedCalibrationTrade",
    "RED_NEWS_BLOCK_WINDOW_SEC",
    "RED_NEWS_HARD_BAN_SEC",
    "RED_NEWS_PRE_FLATTEN_SEC",
    "REPO_ROOT",
    "RedactedCredentials",
    "SESSION_ORDER",
    "SPREAD_SAMPLE_INTERVAL_SEC",
    "SYMBOL_META",
    "SafetyLockError",
    "TERMINAL_BINARIES",
    "TRADES_PER_SYMBOL",
    "_connect_isolated_mt5",
    "_lookup_deal_details",
    "_percentile",
    "_pick_filling_mode",
    "_teardown_isolated_mt5",
    "append_fill_csv",
    "append_jsonl",
    "assert_all_entry_locks",
    "assert_holdout_lock_intact",
    "assert_no_concurrent_mt5",
    "assert_safe_portable_path",
    "build_arg_parser",
    "build_calibration_schedule",
    "capture_spread_snapshot",
    "compute_adverse_slippage",
    "compute_dev_m1_spread_baselines",
    "compute_sl_price",
    "estimate_notional_usd",
    "find_approaching_pre_flatten_news",
    "find_blocking_red_news",
    "is_past_flatten_cutoff",
    "list_running_terminal_processes",
    "load_existing_live_entry_counts",
    "load_ftmo_trial_env",
    "load_red_news_calendar",
    "main",
    "pct",
    "prepare_isolated_portable_terminal",
    "summarize_calibration_and_spreads",
    "tag_session_utc",
    "validate_calibration_account",
    "validate_fixed_volume",
    "validate_mandatory_sl",
]
