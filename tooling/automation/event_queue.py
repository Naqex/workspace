"""Atomic, thread/process-safe, secret-scrubbed JSONL event queue for Naqex automation.

Default storage: `.runtime/automation/event_queue.jsonl` (never tracked in git).
Invariants:
  - `ORDER_SEND_COUNT = 0` (strictly offline; zero broker calls).
  - Zero bare `assert` statements (100% enforced under `python -O`).
  - Atomic temp + flush + fsync + `os.replace` writes guarded by an in-process
    `RLock` and a cross-process exclusive lockfile with stale-lock recovery.
  - Automatic OPSEC scrubbing of bot tokens, webhooks, API keys, DSNs,
    hardcoded local Windows user profile paths, and raw private/CGNAT IPv4 literals.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
import re
import tempfile
import threading
import time
import uuid
from collections.abc import Generator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_EVENT_QUEUE_PATH = REPO_ROOT / ".runtime" / "automation" / "event_queue.jsonl"
EVENT_SCHEMA_VERSION = "naqex-automation-event-v1"
ORDER_SEND_COUNT = 0
HOLDOUT_ROWS_ANALYSED = 0
DEFAULT_MAX_EVENTS = 2000

_SENSITIVE_ENV_VARS: tuple[str, ...] = (
    "TELEGRAM_BOT_TOKEN",
    "TELEGRAM_CHAT_ID",
    "ALERT_WEBHOOK_URL",
    "NAQEX_DEADMAN_URL",
)

# Patterns are constructed dynamically/abstractly so this module never embeds raw IPs or secrets.
_TG_BOT_TOKEN_RE = re.compile(r"(?:bot)?\b\d{6,12}:[A-Za-z0-9_-]{10,}\b")
_SENSITIVE_URL_RE = re.compile(
    r"https?://(?:api\.telegram\.org/bot[^\s'\"<>]+|"
    r"(?:discord\.com|discordapp\.com)/api/webhooks/[^\s'\"<>]+|"
    r"hooks\.slack\.com/services/[^\s'\"<>]+|"
    r"[^\s'\"<>:@]+:[^\s'\"<>@]+@[^\s'\"<>]+)"
)
_POSTGRES_DSN_RE = re.compile(r"postgres(?:ql)?://[^\s:/@<]+:[^\s/@<]{3,}@[^\s/<]+")
_GITHUB_TOKEN_RE = re.compile(r"\b(?:" + "ghp_" + r"[A-Za-z0-9]{20,}|" + "github_pat_" + r"[A-Za-z0-9_]{20,})\b")
_OPENAI_KEY_RE = re.compile(r"\b" + "sk-" + r"(?:proj-)?[A-Za-z0-9_-]{20,}\b")
_GOOGLE_API_KEY_RE = re.compile(r"\b" + "AIza" + r"[0-9A-Za-z_-]{20,}\b")
_KV_SECRET_RE = re.compile(r"(?i)([?&]|\b)((?:token|api[_-]?key|secret|password|passwd)=)[^\s&'\"<>]+")
_BEARER_SECRET_RE = re.compile(r"(?i)(Bearer\s+)[^\s'\"<>]+")
_WIN_USER_PATH_RE = re.compile(
    r"(?i)(?:[A-Z]:|/mnt/[a-z])[\\/]+Users[\\/]+(?!<|YOUR_|user\b|username\b|example\b|runneradmin\b|public\b|default\b)[A-Za-z0-9._-]+"
)
_PRIVATE_OR_CGNAT_IP_RE = re.compile(
    r"(?<![0-9.])(?!100\.64\.0\.0/10(?![0-9]))"
    r"(?:192\.168\.\d{1,3}\.\d{1,3}|"
    r"100\.(?:6[4-9]|[7-9]\d|1[01]\d|12[0-7])\.\d{1,3}\.\d{1,3}|"
    r"10\.\d{1,3}\.\d{1,3}\.\d{1,3}|"
    r"172\.(?:1[6-9]|2\d|3[01])\.\d{1,3}\.\d{1,3})(?![0-9.])"
)
_ALLOWED_SEVERITIES: frozenset[str] = frozenset({"debug", "info", "warning", "error", "critical"})

_PROCESS_LOCKS_GUARD = threading.Lock()
_PROCESS_LOCKS: dict[str, threading.RLock] = {}


class EventQueueError(RuntimeError):
    """Fail-closed error raised on invalid event queue parameters or lock timeouts."""


def utc_now_iso() -> str:
    """Return current UTC timestamp in canonical ISO-8601 `Z` format."""
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _get_thread_lock(target: Path) -> threading.RLock:
    key = str(target.resolve()).lower()
    with _PROCESS_LOCKS_GUARD:
        lock = _PROCESS_LOCKS.get(key)
        if lock is None:
            lock = threading.RLock()
            _PROCESS_LOCKS[key] = lock
        return lock


@contextlib.contextmanager
def _queue_lock(
    target: Path,
    *,
    timeout_sec: float = 10.0,
    stale_lock_sec: float = 30.0,
) -> Generator[None, None, None]:
    """Acquire both an in-process `RLock` and a cross-process sidecar lockfile."""
    if isinstance(timeout_sec, bool) or not isinstance(timeout_sec, (int, float)) or timeout_sec <= 0:
        raise ValueError(f"timeout_sec must be a positive number, got {timeout_sec!r}")
    target.parent.mkdir(parents=True, exist_ok=True)
    tlock = _get_thread_lock(target)
    lock_path = target.parent / f".{target.name}.lock"
    with tlock:
        deadline = time.monotonic() + float(timeout_sec)
        acquired = False
        while not acquired:
            try:
                fd = os.open(str(lock_path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)
                try:
                    os.write(fd, f"{os.getpid()}|{time.time():.3f}\n".encode("ascii"))
                finally:
                    os.close(fd)
                acquired = True
            except FileExistsError:
                try:
                    age = time.time() - lock_path.stat().st_mtime
                    if age >= stale_lock_sec:
                        lock_path.unlink(missing_ok=True)
                        continue
                except FileNotFoundError:
                    continue
                if time.monotonic() >= deadline:
                    raise EventQueueError(
                        f"Timed out after {timeout_sec:.2f}s waiting for queue lock: {lock_path.name}"
                    ) from None
                time.sleep(0.01)
        try:
            yield
        finally:
            lock_path.unlink(missing_ok=True)


def _atomic_write_text(path: Path, text: str) -> Path:
    """Atomically write LF-only UTF-8 text via temp file + flush + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as handle:
            temp_path = Path(handle.name)
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        for attempt in range(5):
            try:
                os.replace(temp_path, path)
                temp_path = None
                break
            except PermissionError:
                if attempt == 4:
                    raise
                time.sleep(0.01 * (attempt + 1))
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)
    return path


def _collect_env_secrets() -> list[str]:
    found: list[str] = []
    for env_name in _SENSITIVE_ENV_VARS:
        val = os.environ.get(env_name, "").strip()
        if len(val) >= 4:
            found.append(val)
    return found


def scrub_text(raw: str, *, extra_secrets: Sequence[str] = ()) -> str:
    """Scrub tokens, webhook URLs, credential DSNs, local user paths, and raw private IPs."""
    out = str(raw)
    secrets = {str(s).strip() for s in extra_secrets if str(s).strip()}
    secrets.update(_collect_env_secrets())
    for sec in sorted(secrets, key=len, reverse=True):
        out = out.replace(sec, "<REDACTED>")
    out = _SENSITIVE_URL_RE.sub("<REDACTED_URL>", out)
    out = _POSTGRES_DSN_RE.sub("<REDACTED_DSN>", out)
    out = _GITHUB_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _OPENAI_KEY_RE.sub("<REDACTED_TOKEN>", out)
    out = _GOOGLE_API_KEY_RE.sub("<REDACTED_TOKEN>", out)
    out = _TG_BOT_TOKEN_RE.sub("<REDACTED_TOKEN>", out)
    out = _KV_SECRET_RE.sub(r"\1\2<REDACTED>", out)
    out = _BEARER_SECRET_RE.sub(r"\1<REDACTED>", out)
    out = _WIN_USER_PATH_RE.sub("<USER_HOME>", out)
    out = _PRIVATE_OR_CGNAT_IP_RE.sub("<REDACTED_IP>", out)
    return out


def scrub_mapping(obj: Any, *, extra_secrets: Sequence[str] = ()) -> Any:
    """Recursively scrub secrets/OPSEC patterns from any JSON-compatible structure."""
    if obj is None or isinstance(obj, (bool, int, float)):
        return obj
    if isinstance(obj, str):
        return scrub_text(obj, extra_secrets=extra_secrets)
    if isinstance(obj, Path):
        return scrub_text(obj.as_posix(), extra_secrets=extra_secrets)
    if isinstance(obj, Mapping):
        cleaned: dict[str, Any] = {}
        for k, v in obj.items():
            key_str = scrub_text(str(k), extra_secrets=extra_secrets)
            low = key_str.lower()
            if any(tok in low for tok in ("token", "secret", "password", "passwd", "api_key", "webhook")):
                cleaned[key_str] = "<REDACTED>" if v not in (None, "", False) else v
            else:
                cleaned[key_str] = scrub_mapping(v, extra_secrets=extra_secrets)
        return cleaned
    if isinstance(obj, (list, tuple, set)):
        return [scrub_mapping(item, extra_secrets=extra_secrets) for item in obj]
    return scrub_text(str(obj), extra_secrets=extra_secrets)


@dataclass(frozen=True)
class AutomationEvent:
    """Canonical record persisted to `.runtime/automation/event_queue.jsonl`."""

    event_type: str
    source: str
    severity: str = "info"
    status: str = "recorded"
    summary: str = ""
    details: dict[str, Any] = field(default_factory=dict)
    event_id: str = field(default_factory=lambda: f"evt-{uuid.uuid4().hex[:16]}")
    ts_utc: str = field(default_factory=utc_now_iso)
    schema_version: str = EVENT_SCHEMA_VERSION
    order_send_count: int = ORDER_SEND_COUNT

    def __post_init__(self) -> None:
        if not isinstance(self.event_type, str) or not self.event_type.strip():
            raise ValueError("event_type must be a non-empty string")
        if not isinstance(self.source, str) or not self.source.strip():
            raise ValueError("source must be a non-empty string")
        if self.severity not in _ALLOWED_SEVERITIES:
            raise ValueError(f"severity must be one of {sorted(_ALLOWED_SEVERITIES)}, got {self.severity!r}")
        if isinstance(self.order_send_count, bool) or self.order_send_count != 0:
            raise ValueError(f"order_send_count must be 0 in offline automation, got {self.order_send_count!r}")

    def to_dict(self, *, extra_secrets: Sequence[str] = ()) -> dict[str, Any]:
        raw = asdict(self)
        cleaned = scrub_mapping(raw, extra_secrets=extra_secrets)
        if not isinstance(cleaned, dict):
            raise EventQueueError("Unexpected non-dict scrubbed event payload")
        cleaned["order_send_count"] = ORDER_SEND_COUNT
        return cleaned

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> AutomationEvent:
        if not isinstance(data, Mapping):
            raise ValueError("Event record must be a mapping")
        return cls(
            event_type=str(data.get("event_type", "")),
            source=str(data.get("source", "")),
            severity=str(data.get("severity", "info")).lower(),
            status=str(data.get("status", "recorded")),
            summary=str(data.get("summary", "")),
            details=dict(data.get("details", {})) if isinstance(data.get("details"), Mapping) else {},
            event_id=str(data.get("event_id") or f"evt-{uuid.uuid4().hex[:16]}"),
            ts_utc=str(data.get("ts_utc") or utc_now_iso()),
            schema_version=str(data.get("schema_version") or EVENT_SCHEMA_VERSION),
            order_send_count=int(data.get("order_send_count", 0)),
        )


def _parse_iso_utc(ts_text: str) -> datetime | None:
    if not isinstance(ts_text, str) or not ts_text.strip():
        return None
    normalized = ts_text.strip()
    if normalized.endswith("Z"):
        normalized = normalized[:-1] + "+00:00"
    try:
        dt = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    return dt.astimezone(UTC) if dt.tzinfo is not None else dt.replace(tzinfo=UTC)


class EventQueue:
    """Atomic, OPSEC-scrubbed JSONL queue at `.runtime/automation/event_queue.jsonl`."""

    def __init__(
        self,
        path: Path | str = DEFAULT_EVENT_QUEUE_PATH,
        *,
        max_events: int = DEFAULT_MAX_EVENTS,
    ) -> None:
        if isinstance(max_events, bool) or not isinstance(max_events, int) or max_events < 1:
            raise ValueError(f"max_events must be an integer >= 1, got {max_events!r}")
        self.path = Path(path)
        self.max_events = max_events

    def _read_raw_records_unlocked(self) -> list[dict[str, Any]]:
        if not self.path.is_file():
            return []
        records: list[dict[str, Any]] = []
        raw_text = self.path.read_text(encoding="utf-8", errors="replace")
        for line in raw_text.splitlines():
            stripped = line.strip()
            if not stripped:
                continue
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                records.append(parsed)
        return records

    def _write_records_unlocked(self, records: Sequence[Mapping[str, Any]]) -> None:
        lines = [json.dumps(rec, ensure_ascii=False, separators=(",", ":"), allow_nan=False) for rec in records]
        content = ("\n".join(lines) + "\n") if lines else ""
        _atomic_write_text(self.path, content)

    def append(
        self,
        event_type: str,
        *,
        source: str,
        severity: str = "info",
        status: str = "recorded",
        summary: str = "",
        details: Mapping[str, Any] | None = None,
        event_id: str | None = None,
        ts_utc: str | None = None,
        extra_secrets: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Validate, OPSEC-scrub, and atomically append a new event record."""
        event = AutomationEvent(
            event_type=event_type.strip(),
            source=source.strip(),
            severity=severity.strip().lower(),
            status=status.strip() or "recorded",
            summary=summary,
            details=dict(details) if details is not None else {},
            event_id=event_id or f"evt-{uuid.uuid4().hex[:16]}",
            ts_utc=ts_utc or utc_now_iso(),
            order_send_count=ORDER_SEND_COUNT,
        )
        payload = event.to_dict(extra_secrets=extra_secrets)
        with _queue_lock(self.path):
            records = self._read_raw_records_unlocked()
            records.append(payload)
            if len(records) > self.max_events:
                records = records[-self.max_events :]
            self._write_records_unlocked(records)
        return payload

    def append_record(
        self,
        record: Mapping[str, Any],
        *,
        extra_secrets: Sequence[str] = (),
    ) -> dict[str, Any]:
        """Validate and atomically append a mapping-shaped event record."""
        if not isinstance(record, Mapping):
            raise ValueError("record must be a mapping")
        event = AutomationEvent.from_dict(record)
        payload = event.to_dict(extra_secrets=extra_secrets)
        with _queue_lock(self.path):
            records = self._read_raw_records_unlocked()
            records.append(payload)
            if len(records) > self.max_events:
                records = records[-self.max_events :]
            self._write_records_unlocked(records)
        return payload

    def read(
        self,
        *,
        limit: int | None = None,
        event_type: str | None = None,
        source: str | None = None,
        severity: str | None = None,
        newest_first: bool = False,
    ) -> list[dict[str, Any]]:
        """Read and filter events from the queue without mutating disk state."""
        if limit is not None:
            if isinstance(limit, bool) or not isinstance(limit, int) or limit < 0:
                raise ValueError(f"limit must be a non-negative integer or None, got {limit!r}")
        if severity is not None and severity.lower() not in _ALLOWED_SEVERITIES:
            raise ValueError(f"Unknown severity filter: {severity!r}")

        records = self._read_raw_records_unlocked()
        filtered: list[dict[str, Any]] = []
        sev_lower = severity.lower() if severity is not None else None
        for rec in records:
            if event_type is not None and rec.get("event_type") != event_type:
                continue
            if source is not None and rec.get("source") != source:
                continue
            if sev_lower is not None and str(rec.get("severity", "")).lower() != sev_lower:
                continue
            filtered.append(rec)

        if newest_first:
            filtered.reverse()
            if limit is not None:
                return filtered[:limit]
            return filtered

        if limit is not None:
            if limit == 0:
                return []
            return filtered[-limit:]
        return filtered

    def prune(
        self,
        *,
        max_events: int | None = None,
        max_age_hours: float | None = None,
        now_utc: datetime | None = None,
    ) -> dict[str, int]:
        """Atomically prune older/excess records from the JSONL queue."""
        eff_max = self.max_events if max_events is None else max_events
        if isinstance(eff_max, bool) or not isinstance(eff_max, int) or eff_max < 0:
            raise ValueError(f"max_events must be an integer >= 0, got {eff_max!r}")
        if max_age_hours is not None:
            if isinstance(max_age_hours, bool) or not isinstance(max_age_hours, (int, float)) or max_age_hours < 0:
                raise ValueError(f"max_age_hours must be a non-negative number, got {max_age_hours!r}")

        ref_now = now_utc.astimezone(UTC) if now_utc is not None else datetime.now(UTC)
        cutoff = (ref_now - timedelta(hours=float(max_age_hours))) if max_age_hours is not None else None

        with _queue_lock(self.path):
            before_records = self._read_raw_records_unlocked()
            kept: list[dict[str, Any]] = []
            for rec in before_records:
                if cutoff is not None:
                    rec_dt = _parse_iso_utc(str(rec.get("ts_utc", "")))
                    if rec_dt is not None and rec_dt < cutoff:
                        continue
                kept.append(rec)
            if eff_max == 0:
                kept = []
            elif len(kept) > eff_max:
                kept = kept[-eff_max:]
            self._write_records_unlocked(kept)
            return {
                "before": len(before_records),
                "after": len(kept),
                "pruned": len(before_records) - len(kept),
                "order_send_count": ORDER_SEND_COUNT,
            }

    def count(self) -> int:
        """Return total number of valid JSONL event records currently stored."""
        return len(self._read_raw_records_unlocked())


def append_event(
    event_type: str,
    *,
    source: str,
    severity: str = "info",
    status: str = "recorded",
    summary: str = "",
    details: Mapping[str, Any] | None = None,
    path: Path | str = DEFAULT_EVENT_QUEUE_PATH,
    max_events: int = DEFAULT_MAX_EVENTS,
    extra_secrets: Sequence[str] = (),
) -> dict[str, Any]:
    """Convenience wrapper around `EventQueue(path).append(...)`."""
    return EventQueue(path=path, max_events=max_events).append(
        event_type=event_type,
        source=source,
        severity=severity,
        status=status,
        summary=summary,
        details=details,
        extra_secrets=extra_secrets,
    )


def read_events(
    *,
    path: Path | str = DEFAULT_EVENT_QUEUE_PATH,
    limit: int | None = None,
    event_type: str | None = None,
    source: str | None = None,
    severity: str | None = None,
    newest_first: bool = False,
) -> list[dict[str, Any]]:
    """Convenience wrapper around `EventQueue(path).read(...)`."""
    return EventQueue(path=path).read(
        limit=limit,
        event_type=event_type,
        source=source,
        severity=severity,
        newest_first=newest_first,
    )


def prune_events(
    *,
    path: Path | str = DEFAULT_EVENT_QUEUE_PATH,
    max_events: int = DEFAULT_MAX_EVENTS,
    max_age_hours: float | None = None,
) -> dict[str, int]:
    """Convenience wrapper around `EventQueue(path).prune(...)`."""
    return EventQueue(path=path, max_events=max_events).prune(
        max_events=max_events,
        max_age_hours=max_age_hours,
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Inspect or prune Naqex automation JSONL event queue.")
    parser.add_argument("--path", type=Path, default=DEFAULT_EVENT_QUEUE_PATH, help="Queue JSONL path")
    parser.add_argument("--tail", type=int, default=10, help="Show last N events (default: 10)")
    parser.add_argument("--prune", action="store_true", help="Prune queue using --max-events / --max-age-hours")
    parser.add_argument("--max-events", type=int, default=DEFAULT_MAX_EVENTS, help="Retention cap when pruning")
    parser.add_argument("--max-age-hours", type=float, default=None, help="Max age in hours when pruning")
    parser.add_argument("--json", action="store_true", dest="as_json", help="Emit JSON output")
    args = parser.parse_args(argv)

    queue = EventQueue(path=args.path, max_events=args.max_events)
    if args.prune:
        result = queue.prune(max_events=args.max_events, max_age_hours=args.max_age_hours)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0

    events = queue.read(limit=args.tail)
    payload = {
        "schema_version": EVENT_SCHEMA_VERSION,
        "count": queue.count(),
        "returned": len(events),
        "order_send_count": ORDER_SEND_COUNT,
        "events": events,
    }
    if args.as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"EventQueue: {payload['count']} total records (showing {payload['returned']}, OrderSend=0)")
        for ev in events:
            sev = str(ev.get("severity", "info")).upper()
            src = ev.get("source")
            etype = ev.get("event_type")
            summary = ev.get("summary", "")
            print(f"  [{ev.get('ts_utc')}] {sev} {src}:{etype} - {summary}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
