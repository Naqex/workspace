"""Lock 1 credentials parser, red-news calendar loader, and CSV/JSONL log I/O."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

from exports.calibration_probe.constants import (
    ALLOWED_DEMO_LOGIN,
    ALLOWED_SERVER,
    CORE_SYMBOLS,
    DEFAULT_ENV_PATH,
    DEFAULT_NEWS_CSV,
    ENV_ALLOWED_KEYS,
    FILLS_CSV_COLUMNS,
    FORBIDDEN_LOGINS,
)
from exports.calibration_probe.models import RedactedCredentials, SafetyLockError
from quant_factory import prop_challenge_tracker as pct


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


def load_red_news_calendar(news_csv: Path = DEFAULT_NEWS_CSV) -> list[dict[str, Any]]:
    """Load `naqex_red_news_utc.csv` fail-closed (raises if missing or empty)."""
    events = pct.load_red_news_events(Path(news_csv))
    if not events:
        raise SafetyLockError(f"LOCK_4_EMPTY_OR_MISSING_RED_NEWS_CSV: {news_csv}")
    return events


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
