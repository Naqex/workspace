"""CLI argument parser and main entrypoint for FTMO-Demo calibration probe."""

from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from exports.calibration_probe.constants import (
    DEFAULT_ENV_PATH,
    DEFAULT_FILLS_CSV,
    DEFAULT_HOT_M1_CACHE,
    DEFAULT_NEWS_CSV,
    DEFAULT_PORTABLE_DIR,
    DEFAULT_SPREAD_LOG,
    DEFAULT_SUMMARY_JSON,
    MAX_TOTAL_TRADES,
    SPREAD_SAMPLE_INTERVAL_SEC,
)
from exports.calibration_probe.models import SafetyLockError
from exports.calibration_probe.mt5_session import _connect_isolated_mt5, _teardown_isolated_mt5
from exports.calibration_probe.parsers import load_ftmo_trial_env, load_red_news_calendar
from exports.calibration_probe.reporting import summarize_calibration_and_spreads
from exports.calibration_probe.runner import CalibrationProbeRunner
from exports.calibration_probe.validators import list_running_terminal_processes


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
        print(
            json.dumps(
                {
                    "schema": summary["schema"],
                    "verdict": summary["verdict"],
                    "holdout_rows_analysed": summary["holdout_rows_analysed"],
                    "spread_log_rows_total": summary["inputs"]["spread_log_rows_total"],
                    "live_fill_legs_total": summary["inputs"]["live_fill_legs_total"],
                    "portfolio_core4": summary["portfolio_core4"],
                    "summary_json": str(args.summary_json),
                },
                indent=2,
                ensure_ascii=False,
            )
        )
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
