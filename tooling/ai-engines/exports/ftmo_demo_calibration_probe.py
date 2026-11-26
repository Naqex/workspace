"""Fail-Closed FTMO-Demo Secondary Calibration Probe & 5s Live Spread Recorder (`1515343318`).

Thin backward-compatible façade delegating to `tooling/ai-engines/exports/calibration_probe/`.

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
"""

from __future__ import annotations

import sys
import types
from pathlib import Path
from typing import Any

_EXPORTS_DIR = Path(__file__).resolve().parent
_AI_ENGINES_DIR = _EXPORTS_DIR.parent
for _p in (_AI_ENGINES_DIR, _EXPORTS_DIR):
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

from exports.calibration_probe import (  # noqa: E402
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
    CalibrationProbeRunner,
    PlannedCalibrationTrade,
    RedactedCredentials,
    SafetyLockError,
    _connect_isolated_mt5,
    _lookup_deal_details,
    _percentile,
    _pick_filling_mode,
    _teardown_isolated_mt5,
    append_fill_csv,
    append_jsonl,
    assert_all_entry_locks,
    assert_holdout_lock_intact,
    assert_no_concurrent_mt5,
    assert_safe_portable_path,
    build_arg_parser,
    build_calibration_schedule,
    capture_spread_snapshot,
    compute_adverse_slippage,
    compute_dev_m1_spread_baselines,
    compute_sl_price,
    estimate_notional_usd,
    find_approaching_pre_flatten_news,
    find_blocking_red_news,
    is_past_flatten_cutoff,
    list_running_terminal_processes,
    load_existing_live_entry_counts,
    load_ftmo_trial_env,
    load_red_news_calendar,
    main,
    pct,
    prepare_isolated_portable_terminal,
    summarize_calibration_and_spreads,
    tag_session_utc,
    validate_calibration_account,
    validate_fixed_volume,
    validate_mandatory_sl,
)

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


class _SyncedFacadeModule(types.ModuleType):
    """Propagate façade attribute mutations/deletions to backing `calibration_probe` submodules."""

    _sync_prefix: str = "exports.calibration_probe"
    _facade_file: str = ""
    _deleted_targets: dict[str, set[str]]

    def _iter_sync_modules(self) -> list[types.ModuleType]:
        prefix = self._sync_prefix
        prefix_dot = f"{prefix}."
        facade_file = self._facade_file
        targets: list[types.ModuleType] = []
        for mod_name, mod in list(sys.modules.items()):
            if mod is None or mod is self:
                continue
            if mod_name == prefix or mod_name.startswith(prefix_dot):
                targets.append(mod)
                continue
            if facade_file:
                mod_file = getattr(mod, "__file__", None)
                if mod_file:
                    try:
                        if str(Path(mod_file).resolve()) == facade_file:
                            targets.append(mod)
                    except OSError:
                        pass
        return targets

    def __setattr__(self, name: str, value: Any) -> None:
        super().__setattr__(name, value)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted = getattr(self, "_deleted_targets", {}).get(name)
        for mod in self._iter_sync_modules():
            if name in mod.__dict__ or (deleted is not None and mod.__name__ in deleted):
                types.ModuleType.__setattr__(mod, name, value)
                if deleted is not None:
                    deleted.discard(mod.__name__)

    def __delattr__(self, name: str) -> None:
        super().__delattr__(name)
        if (name.startswith("__") and name.endswith("__")) or name in (
            "_sync_prefix",
            "_facade_file",
            "_deleted_targets",
        ):
            return
        deleted_map: dict[str, set[str]] = getattr(self, "_deleted_targets", {})
        recorded = deleted_map.setdefault(name, set())
        for mod in self._iter_sync_modules():
            if name in mod.__dict__:
                recorded.add(mod.__name__)
                types.ModuleType.__delattr__(mod, name)


_this_mod: Any = sys.modules.get(__name__)
if _this_mod is not None and not isinstance(_this_mod, _SyncedFacadeModule):
    _this_mod.__class__ = _SyncedFacadeModule
    types.ModuleType.__setattr__(_this_mod, "_sync_prefix", "exports.calibration_probe")
    types.ModuleType.__setattr__(_this_mod, "_facade_file", str(Path(__file__).resolve()))
    types.ModuleType.__setattr__(_this_mod, "_deleted_targets", {})

if __name__ == "__main__":
    raise SystemExit(main())
