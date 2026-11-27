"""Fail-closed Holdout 2025+ guards (ZERO Python `assert` statements; immune to `python -O`).

All violations raise `HoldoutLockError`, which subclasses `ValueError` so existing
callers/tests catching `ValueError` remain 100% compatible while new callers can
catch `HoldoutLockError` explicitly.

Whenever a caller explicitly passes `allow_holdout=True`, `record_holdout_override_event`
appends a tamper-evident `RunEvent` to `tooling/run_registry/store.py` (`SQLiteRunRegistry`).
"""

from __future__ import annotations

import hashlib
import json
import math
import re
import sys
import uuid
from collections.abc import Iterable, Mapping
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Any

import numpy as np

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from tooling.run_registry.store import (  # noqa: E402
    Provenance,
    RunEvent,
    RunRecord,
    SQLiteRunRegistry,
    utc_now,
)

HOLDOUT_CUTOFF_DAY: str = "2025-01-01"
DEV_START_UTC_TS: int = int(datetime(2018, 1, 1, tzinfo=UTC).timestamp())
HOLDOUT_START_UTC_TS: int = int(datetime(2025, 1, 1, tzinfo=UTC).timestamp())
DEFAULT_REGISTRY_PATH: Path = REPO_ROOT / ".runtime" / "run_registry" / "registry.sqlite3"

_SAFE_ID_RE = re.compile(r"[^A-Za-z0-9_.:-]+")
_DOT_DATE_RE = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})(.*)$")
_ISO_DATE_RE = re.compile(r"^\d{4}-\d{2}-\d{2}$")
_ISO_DATETIME_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}[T ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:Z|z|[+-]\d{2}:?\d{2})?$"
)
_MAX_SAFE_FLOAT_TS: float = 9.0e15


class HoldoutLockError(ValueError):
    """Fail-closed exception raised on any sealed Holdout (`>= 2025-01-01`) violation.

    Inherits `ValueError` (P0-7) so legacy callers/tests catching `ValueError`
    continue to fail closed without regression.
    """


def _parse_to_utc_date(item: Any, *, context: str) -> date:
    """Strictly parse a calendar date or ISO-8601 datetime into a UTC `date`.

    Rejects numeric/boolean/None/non-ISO/invalid-calendar inputs with `HoldoutLockError`
    so lexicographical or timezone-offset tricks cannot bypass the 2025-01-01 UTC seal.
    """
    if item is None or isinstance(item, (bool, int, float, np.number, bytes, bytearray)):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: non-date value {item!r} ({type(item).__name__}) rejected"
        )
    if isinstance(item, datetime):
        return item.astimezone(UTC).date() if item.tzinfo is not None else item.date()
    if isinstance(item, date):
        return item
    if isinstance(item, np.datetime64):
        if bool(np.isnat(item)):
            raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: NaT datetime rejected")
        py_dt = item.astype("datetime64[s]").item()
        if isinstance(py_dt, datetime):
            return py_dt.astimezone(UTC).date() if py_dt.tzinfo is not None else py_dt.date()
        if isinstance(py_dt, date):
            return py_dt
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid numpy datetime {item!r}")
    if not isinstance(item, str):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: unsupported date type {type(item).__name__}: {item!r}"
        )

    text = item.strip()
    if not text:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: empty date string rejected")
    dot_match = _DOT_DATE_RE.fullmatch(text)
    if dot_match is not None:
        text = f"{dot_match.group(1)}-{dot_match.group(2)}-{dot_match.group(3)}{dot_match.group(4)}"

    if _ISO_DATE_RE.fullmatch(text):
        try:
            return date.fromisoformat(text)
        except ValueError as exc:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid calendar date {item!r}: {exc}"
            ) from exc

    if _ISO_DATETIME_RE.fullmatch(text):
        try:
            dt = datetime.fromisoformat(text)
        except ValueError as exc:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid ISO datetime {item!r}: {exc}"
            ) from exc
        return dt.astimezone(UTC).date() if dt.tzinfo is not None else dt.date()

    raise HoldoutLockError(
        f"HOLDOUT_LOCK_VIOLATION [{context}]: malformed/non-ISO date {item!r} rejected"
    )


def enforce_pre_holdout_dates(
    dates: str | date | datetime | Iterable[Any],
    *,
    context: str = "dev_research",
    cutoff_day: str = HOLDOUT_CUTOFF_DAY,
    allow_empty: bool = True,
) -> None:
    """Fail-closed guard blocking any date `>= cutoff_day` (`2025-01-01` UTC default).

    Uses explicit `if ...: raise HoldoutLockError(...)` (never Python `assert`),
    so enforcement remains active under `python -O` and `python -OO`.
    """
    cutoff_dt = _parse_to_utc_date(cutoff_day, context=f"{context}.cutoff_day")

    if dates is None or isinstance(dates, (bool, int, float, np.number, bytes, bytearray)):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid dates input {dates!r} ({type(dates).__name__})"
        )

    if isinstance(dates, (str, date, datetime, np.datetime64)):
        raw_items: list[Any] = [dates]
    else:
        try:
            raw_items = list(dates)
        except TypeError as exc:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: non-iterable dates input {dates!r}"
            ) from exc

    if not raw_items:
        if not allow_empty:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: empty date series rejected (allow_empty=False)"
            )
        return

    parsed = [_parse_to_utc_date(d, context=context) for d in raw_items]
    bad_days = [d.isoformat() for d in parsed if d >= cutoff_dt]
    if bad_days:
        raise HoldoutLockError(
            f"HOLDOUT_CONTAMINATION / HOLDOUT_LOCK_VIOLATION [{context}]: "
            f"detected {len(bad_days)} date(s) >= {cutoff_dt.isoformat()}: {bad_days[:5]}"
        )


def _check_scalar_int_ts(
    val: int,
    *,
    start_i: int | None,
    stop_i: int,
    context: str,
) -> None:
    if start_i is not None and val < start_i:
        raise HoldoutLockError(
            f"HOLDOUT_OR_RANGE_BREACH [{context}]: timestamp {val} < start_ts ({start_i})"
        )
    if val >= stop_i:
        raise HoldoutLockError(
            f"HOLDOUT_CONTAMINATION / HOLDOUT_LOCK_VIOLATION [{context}]: timestamp {val} >= stop_ts ({stop_i})"
        )


def enforce_pre_holdout_ts(
    ts_int: int | np.integer | np.ndarray | Iterable[Any],
    start_ts: int | None = None,
    stop_ts: int = HOLDOUT_START_UTC_TS,
    *,
    context: str = "dev_research",
    allow_empty: bool = False,
) -> None:
    """Fail-closed guard enforcing `[start_ts, stop_ts)` bounds on UTC epoch seconds.

    Accepts a scalar integer timestamp or a 1D array/iterable of timestamps.
    Rejects `None`, booleans, scalar floats, non-finite values, overflow values,
    and any timestamp `>= stop_ts` unconditionally with `HoldoutLockError`.
    """
    if isinstance(stop_ts, bool) or not isinstance(stop_ts, (int, np.integer)):
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid stop_ts={stop_ts!r}")
    stop_i = int(stop_ts)

    start_i: int | None = None
    if start_ts is not None:
        if isinstance(start_ts, bool) or not isinstance(start_ts, (int, np.integer)):
            raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid start_ts={start_ts!r}")
        start_i = int(start_ts)

    if ts_int is None or isinstance(ts_int, (bool, float, np.floating, str, bytes, bytearray)):
        raise HoldoutLockError(
            f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid scalar timestamp {ts_int!r} ({type(ts_int).__name__})"
        )

    if isinstance(ts_int, (int, np.integer)):
        _check_scalar_int_ts(int(ts_int), start_i=start_i, stop_i=stop_i, context=context)
        return

    if isinstance(ts_int, np.ndarray):
        arr = ts_int
    else:
        try:
            seq = list(ts_int)
        except TypeError as exc:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid timestamp input {ts_int!r}"
            ) from exc
        arr = np.asarray(seq)

    if arr.dtype == np.bool_:
        raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: boolean timestamp array rejected")
    if arr.size == 0:
        if not allow_empty:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: empty timestamp sequence rejected"
            )
        return

    if arr.ndim == 0:
        scalar = arr.item()
        if isinstance(scalar, bool) or not isinstance(scalar, (int, np.integer)):
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid 0-d timestamp {scalar!r}"
            )
        _check_scalar_int_ts(int(scalar), start_i=start_i, stop_i=stop_i, context=context)
        return

    if arr.dtype == object:
        for elem in arr.flat:
            if isinstance(elem, bool) or elem is None:
                raise HoldoutLockError(
                    f"HOLDOUT_LOCK_VIOLATION [{context}]: invalid object timestamp element {elem!r}"
                )
            if isinstance(elem, (int, np.integer)):
                _check_scalar_int_ts(int(elem), start_i=start_i, stop_i=stop_i, context=context)
            elif isinstance(elem, (float, np.floating)):
                fv = float(elem)
                if not math.isfinite(fv) or abs(fv) > _MAX_SAFE_FLOAT_TS:
                    raise HoldoutLockError(
                        f"HOLDOUT_LOCK_VIOLATION [{context}]: non-finite/overflow float timestamp {elem!r}"
                    )
                if start_i is not None and fv < float(start_i):
                    raise HoldoutLockError(
                        f"HOLDOUT_OR_RANGE_BREACH [{context}]: timestamp {fv} < start_ts ({start_i})"
                    )
                if fv >= float(stop_i):
                    raise HoldoutLockError(
                        f"HOLDOUT_CONTAMINATION / HOLDOUT_LOCK_VIOLATION [{context}]: "
                        f"timestamp {fv} >= stop_ts ({stop_i})"
                    )
            else:
                raise HoldoutLockError(
                    f"HOLDOUT_LOCK_VIOLATION [{context}]: unsupported timestamp element {elem!r}"
                )
        return

    if np.issubdtype(arr.dtype, np.floating):
        if not bool(np.all(np.isfinite(arr))):
            raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: non-finite timestamp in array")
        # Bounds-check strictly in float64 BEFORE any int64 conversion so 1e20 cannot wrap to INT64_MIN.
        min_f = float(np.min(arr))
        max_f = float(np.max(arr))
        if abs(min_f) > _MAX_SAFE_FLOAT_TS or abs(max_f) > _MAX_SAFE_FLOAT_TS:
            raise HoldoutLockError(
                f"HOLDOUT_LOCK_VIOLATION [{context}]: out-of-range float timestamp bounds [{min_f}, {max_f}]"
            )
        if start_i is not None and min_f < float(start_i):
            raise HoldoutLockError(
                f"HOLDOUT_OR_RANGE_BREACH [{context}]: min timestamp {min_f} < start_ts ({start_i})"
            )
        if max_f >= float(stop_i):
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION / HOLDOUT_LOCK_VIOLATION [{context}]: "
                f"max timestamp {max_f} >= stop_ts ({stop_i})"
            )
        return

    if np.issubdtype(arr.dtype, np.integer):
        # Use Python arbitrary-precision int directly so uint64 values > INT64_MAX cannot wrap negative.
        min_ts = int(np.min(arr))
        max_ts = int(np.max(arr))
        if start_i is not None and min_ts < start_i:
            raise HoldoutLockError(
                f"HOLDOUT_OR_RANGE_BREACH [{context}]: min timestamp {min_ts} < start_ts ({start_i})"
            )
        if max_ts >= stop_i:
            raise HoldoutLockError(
                f"HOLDOUT_CONTAMINATION / HOLDOUT_LOCK_VIOLATION [{context}]: "
                f"max timestamp {max_ts} >= stop_ts ({stop_i})"
            )
        return

    raise HoldoutLockError(f"HOLDOUT_LOCK_VIOLATION [{context}]: unsupported timestamp dtype {arr.dtype}")


def enforce_holdout_zero_rows(holdout_rows: Any, *, context: str = "dev_research") -> None:
    """Fail-closed guard ensuring `holdout_rows == 0`."""
    if isinstance(holdout_rows, bool) or holdout_rows is None:
        raise HoldoutLockError(
            f"HOLDOUT_CONTAMINATION_DETECTED [{context}]: invalid holdout_rows={holdout_rows!r}"
        )
    if int(holdout_rows) != 0:
        raise HoldoutLockError(
            f"HOLDOUT_CONTAMINATION_DETECTED [{context}]: holdout_rows={int(holdout_rows)} != 0"
        )


def _safe_registry_id(raw: str, *, prefix: str = "id", max_len: int = 120) -> str:
    cleaned = _SAFE_ID_RE.sub("_", raw.strip()).strip("_.:-")
    if not cleaned or not cleaned[0].isalnum():
        cleaned = f"{prefix}-{cleaned}" if cleaned else f"{prefix}-{uuid.uuid4().hex[:12]}"
    return cleaned[:max_len]


def record_holdout_override_event(
    *,
    caller: str,
    context: str = "allow_holdout",
    reason: str = "explicit_allow_holdout_true",
    details: Mapping[str, Any] | None = None,
    registry_path: str | Path | None = None,
    run_id: str | None = None,
    correlation_id: str | None = None,
    code_revision: str = "workspace",
) -> RunEvent:
    """Append a tamper-evident `holdout.override` RunEvent into `SQLiteRunRegistry`.

    Must be invoked whenever any caller explicitly requests `allow_holdout=True`.
    """
    reg_path = Path(registry_path) if registry_path is not None else DEFAULT_REGISTRY_PATH
    registry = SQLiteRunRegistry(reg_path)

    ts_now = utc_now()
    uid = uuid.uuid4().hex[:16]
    eff_run_id = _safe_registry_id(run_id or f"holdout-override-{uid}", prefix="ho")
    eff_corr_id = _safe_registry_id(correlation_id or f"corr-holdout-{uid}", prefix="corr")

    safe_details: dict[str, Any] = {}
    if details is not None:
        for k, v in details.items():
            safe_details[str(k)] = v

    payload: dict[str, Any] = {
        "caller": str(caller),
        "context": str(context),
        "reason": str(reason),
        "allow_holdout": True,
        "details": safe_details,
    }
    config_sha = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), default=str).encode("utf-8")
    ).hexdigest()

    prov = Provenance(
        code_revision=code_revision or "workspace",
        config_sha256=config_sha,
        source_refs=(f"caller:{caller}", f"context:{context}"),
    )
    run = RunRecord(
        run_id=eff_run_id,
        attempt_no=1,
        fence_token=f"fence-{uid}",
        project_id="quant_factory",
        run_kind="holdout_override_audit",
        mode="research",
        correlation_id=eff_corr_id,
        provenance=prov,
        created_at_utc=ts_now,
    )
    registered = registry.register_run(run)
    event = RunEvent.create(
        event_type="holdout.override",
        run=registered,
        idempotency_key=_safe_registry_id(f"ho-{eff_run_id}-{uid}", prefix="ho"),
        event_id=_safe_registry_id(f"evt-ho-{uid}", prefix="evt"),
        occurred_at_utc=ts_now,
        payload=payload,
    )
    return registry.append(event)


__all__ = [
    "DEFAULT_REGISTRY_PATH",
    "DEV_START_UTC_TS",
    "HOLDOUT_CUTOFF_DAY",
    "HOLDOUT_START_UTC_TS",
    "HoldoutLockError",
    "enforce_holdout_zero_rows",
    "enforce_pre_holdout_dates",
    "enforce_pre_holdout_ts",
    "record_holdout_override_event",
]
