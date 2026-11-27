"""Wave 4 Macro AI Supervisor Engine (W4-G14, Total Offensive #4 v4.8.1 FINAL).

Strictly advisory, fail-closed, anti-contamination Macro AI Supervisor supporting
three provider modes behind a single-line enum switch:
  1. ``CLIPROXY_LOCAL_17852``: dynamic ``.runtime/paperclip/gateway-owner.json``
     loopback gateway (``127.0.0.1:17852``), ``request-retry: 0``, fail-closed
     on ``429`` (``RATE_LIMITED_STOP``) or expired OAuth (``SKIP_AUTH_EXPIRED``),
     sanitized temp YAML blocking ``api.poolai.win`` without mutating ``managed.yaml``,
     and hard ``SecurityError`` rejection of external Windows port ``8317``.
  2. ``OFFICIAL_API_PRODUCTION``: official OpenRouter / Anthropic / OpenAI / Gemini
     HTTPS endpoints guarded by a hard ``<= 5.00 USD/month`` budget enforcer fed by
     ``.runtime/offensive4/ai/ai_model_radar_latest.json``.
  3. ``LOCAL_OLLAMA_ADVISORY``: local loopback ``http://127.0.0.1:11434`` degraded
     advisory mode (``execution_capability = False``).

Hard Safety Invariants (ZERO EXCEPTIONS):
  - ``ORDER_SEND_CAPABLE = False``, ``ORDER_SEND_COUNT = 0`` (never emits orders
    or overrides ``PropGuard`` hard stops).
  - ``HOLDOUT_CUTOFF_DATE = "2024-12-31"`` (Holdout 2025+ SEALED).
  - ``MAX_OFFICIAL_API_USD_PER_MONTH = 5.0`` (hard monthly official API ceiling).
  - ``FORBIDDEN_EXTERNAL_CLIPROXY_PORT = 8317`` (always raises ``SecurityError``).
  - ZERO bare ``assert`` statements (100% enforcement under ``python -O``).
  - ALL ``subprocess`` calls explicitly pass ``creationflags=_NO_WINDOW_FLAGS``.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import socket
import subprocess
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any, Final
from urllib.parse import urlsplit

import httpx
import yaml

from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)

# ==============================================================================
# Hard Safety Constants & Canonical Contracts
# ==============================================================================

SCHEMA_VERSION: Final[str] = "naqex-wave4-macro-ai-supervisor-v1"
ORDER_SEND_COUNT: Final[int] = 0
EXECUTION_CAPABLE: Final[bool] = False
PROP_GUARD_OVERRIDE_ALLOWED: Final[bool] = False

FORBIDDEN_EXTERNAL_CLIPROXY_PORT: Final[int] = 8317
DEFAULT_PROJECT_CLIPROXY_PORT: Final[int] = 17852
DEFAULT_OLLAMA_BASE_URL: Final[str] = "http://127.0.0.1:11434"
DEFAULT_HTTP_TIMEOUT_SEC: Final[float] = 20.0
DEFAULT_USD_VND_RATE: Final[float] = 25_500.0

# Macro Supervisor monthly workload baseline matching W4-G13 AI Model Radar
SUPERVISOR_RUNS_PER_MONTH: Final[int] = 44
SUPERVISOR_AVG_INPUT_TOKENS_PER_RUN: Final[int] = 7_955   # ~350,000 / 44
SUPERVISOR_AVG_OUTPUT_TOKENS_PER_RUN: Final[int] = 1_591  # ~70,000 / 44

# First prospective live session date (2026-11-28 is Saturday -> Monday 2026-11-30)
FIRST_PROSPECTIVE_LIVE_SESSION_DATE: Final[str] = "2026-11-30"
MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS: Final[int] = 30

# Canonical paths resolved relative to workspace root (never hardcoding legacy dirs)
QUANT_FACTORY_DIR: Final[Path] = Path(__file__).resolve().parents[1]
AI_ENGINES_DIR: Final[Path] = QUANT_FACTORY_DIR.parent
WORKSPACE_ROOT: Final[Path] = AI_ENGINES_DIR.parents[1]

DEFAULT_PAPERCLIP_RUNTIME_DIR: Final[Path] = WORKSPACE_ROOT / ".runtime" / "paperclip"
DEFAULT_GATEWAY_OWNER_PATH: Final[Path] = DEFAULT_PAPERCLIP_RUNTIME_DIR / "gateway-owner.json"
DEFAULT_SANITIZED_GATEWAY_YAML_PATH: Final[Path] = DEFAULT_PAPERCLIP_RUNTIME_DIR / "wave4_sanitized_gateway.yaml"
DEFAULT_WAVE4_GATEWAY_PID_PATH: Final[Path] = DEFAULT_PAPERCLIP_RUNTIME_DIR / "wave4_gateway_17852_pid.json"
DEFAULT_WAVE4_GATEWAY_STDOUT_LOG: Final[Path] = DEFAULT_PAPERCLIP_RUNTIME_DIR / "wave4_cliproxy_17852.out.log"
DEFAULT_WAVE4_GATEWAY_STDERR_LOG: Final[Path] = DEFAULT_PAPERCLIP_RUNTIME_DIR / "wave4_cliproxy_17852.err.log"
DEFAULT_RADAR_SNAPSHOT_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "ai" / "ai_model_radar_latest.json"
)
DEFAULT_PROSPECTIVE_LEDGER_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "ai" / "prospective_shadow_ledger.json"
)

# Windows windowless subprocess creation flag (0 on POSIX where CPython accepts 0 cleanly)
_NO_WINDOW_FLAGS: Final[int] = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

LOOPBACK_HOSTS: Final[frozenset[str]] = frozenset({"127.0.0.1", "localhost", "::1"})
BLOCKED_UPSTREAM_DOMAINS: Final[tuple[str, ...]] = ("api.poolai.win", "poolai.win")
ALLOWED_RISK_MULTS: Final[tuple[float, ...]] = (0.0, 0.5, 0.75, 1.0)
ALLOWED_REGIME_TAGS: Final[frozenset[str]] = frozenset(
    {
        "CRISIS_HALT",
        "HIGH_STRESS_DEFENSIVE",
        "CAUTION_REDUCED",
        "CALM_NORMAL",
        "NEUTRAL",
    }
)
GENESIS_SHA256: Final[str] = "0" * 64
_SHA256_HEX_RE: Final[re.Pattern[str]] = re.compile(r"^[0-9a-f]{64}$")

# Provider status codes
STATUS_OK: Final[str] = "OK"
STATUS_RATE_LIMITED_STOP: Final[str] = "RATE_LIMITED_STOP"
STATUS_SKIP_AUTH_EXPIRED: Final[str] = "SKIP_AUTH_EXPIRED"
STATUS_SKIP_OFFLINE: Final[str] = "SKIP_OFFLINE"
STATUS_SKIP_MISSING_API_KEY: Final[str] = "SKIP_MISSING_API_KEY"
STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR: Final[str] = "DEGRADED_PARSE_OR_UPSTREAM_ERROR"

# Official HTTPS API endpoints & environment variable names
OFFICIAL_API_ENDPOINTS: Final[dict[str, dict[str, str]]] = {
    "openrouter": {
        "url": "https://openrouter.ai/api/v1/chat/completions",
        "host": "openrouter.ai",
        "env_var": "OPENROUTER_API_KEY",
        "wire_format": "openai_chat",
    },
    "anthropic": {
        "url": "https://api.anthropic.com/v1/messages",
        "host": "api.anthropic.com",
        "env_var": "ANTHROPIC_API_KEY",
        "wire_format": "anthropic_messages",
    },
    "openai": {
        "url": "https://api.openai.com/v1/chat/completions",
        "host": "api.openai.com",
        "env_var": "OPENAI_API_KEY",
        "wire_format": "openai_chat",
    },
    "gemini": {
        "url": "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions",
        "host": "generativelanguage.googleapis.com",
        "env_var": "GEMINI_API_KEY",
        "wire_format": "openai_chat",
    },
}

# Forbidden order/execution override keys if an LLM attempts to emit execution directives
_FORBIDDEN_DECISION_KEYS: Final[frozenset[str]] = frozenset(
    {
        "order",
        "orders",
        "order_send",
        "ordersend",
        "place_order",
        "execute_trade",
        "side",
        "buy",
        "sell",
        "lot",
        "lots",
        "lot_size",
        "volume",
        "ticket",
        "stop_loss",
        "take_profit",
        "sl",
        "tp",
        "override_propguard",
        "disable_propguard",
        "disable_kill_switch",
        "bypass_dd_limit",
    }
)


# ==============================================================================
# Provider Mode Enum (1-Line Switch) & Fail-Closed Exceptions
# ==============================================================================


class ProviderMode(StrEnum):
    """Single-line switch selecting the Macro AI Supervisor backend."""

    CLIPROXY_LOCAL_17852 = "CLIPROXY_LOCAL_17852"
    OFFICIAL_API_PRODUCTION = "OFFICIAL_API_PRODUCTION"
    LOCAL_OLLAMA_ADVISORY = "LOCAL_OLLAMA_ADVISORY"


class MacroSupervisorError(RuntimeError):
    """Base fail-closed error for the Wave 4 Macro AI Supervisor."""


class SecurityError(MacroSupervisorError):
    """Raised fail-closed on port-8317 touch, third-party route leak, or unsafe host/path."""


class BudgetExceededError(MacroSupervisorError):
    """Raised fail-closed when Official API spend would exceed 5.00 USD/month."""


class ContaminationError(MacroSupervisorError):
    """Raised fail-closed when a prompt leaks historical dates, years, events, or tickers."""


class LedgerIntegrityError(MacroSupervisorError):
    """Raised fail-closed on Prospective Shadow Ledger tamper or retroactive commit."""


class SupervisorValidationError(MacroSupervisorError):
    """Raised fail-closed on invalid decision payload, risk_mult, or config parameters."""


# ==============================================================================
# Core Numeric, Hash & Safety Helpers (Zero Bare Asserts)
# ==============================================================================


def _enforce_module_safety_invariants() -> None:
    if ORDER_SEND_CAPABLE is not False:
        raise SecurityError(f"ORDER_SEND_CAPABLE must be strictly False, observed {ORDER_SEND_CAPABLE!r}")
    if type(ORDER_SEND_COUNT) is not int or ORDER_SEND_COUNT != 0:
        raise SecurityError(f"ORDER_SEND_COUNT must be strictly 0, observed {ORDER_SEND_COUNT!r}")
    if HOLDOUT_CUTOFF_DATE != "2024-12-31":
        raise SecurityError(f"HOLDOUT_CUTOFF_DATE tampered: {HOLDOUT_CUTOFF_DATE!r}")
    if MAX_OFFICIAL_API_USD_PER_MONTH > 5.0:
        raise SecurityError(f"MAX_OFFICIAL_API_USD_PER_MONTH exceeds 5.0: {MAX_OFFICIAL_API_USD_PER_MONTH!r}")


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def canonical_json_dumps(payload: Any) -> str:
    """Deterministic canonical JSON serialization (sorted keys, UTF-8, compact separators)."""
    return json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def canonical_payload_sha256(payload: Any) -> str:
    """Compute canonical SHA-256 hex digest over any JSON-serializable object."""
    return _sha256_text(canonical_json_dumps(payload))


def _atomic_write_text(path: Path, text: str) -> None:
    """Atomically write LF-normalized UTF-8 text via temp file + fsync + os.replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = text.replace("\r\n", "\n").replace("\r", "\n")
    tmp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="\n",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(normalized)
            fh.flush()
            os.fsync(fh.fileno())
            tmp_path = Path(fh.name)
        os.replace(tmp_path, path)
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            try:
                tmp_path.unlink()
            except OSError:
                pass
        raise


def _atomic_write_json(path: Path, payload: Any) -> None:
    _atomic_write_text(path, json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=False) + "\n")


def _require_finite_float(
    raw: Any,
    *,
    field_name: str,
    min_value: float | None = None,
    max_value: float | None = None,
    strictly_positive: bool = False,
) -> float:
    if isinstance(raw, bool) or not isinstance(raw, (int, float)):
        raise SupervisorValidationError(f"{field_name} must be a finite int/float (not bool), got {raw!r}")
    val = float(raw)
    if not math.isfinite(val):
        raise SupervisorValidationError(f"{field_name} must be finite (no NaN/Inf), got {raw!r}")
    if strictly_positive and val <= 0.0:
        raise SupervisorValidationError(f"{field_name} must be > 0, got {val}")
    if min_value is not None and val < min_value:
        raise SupervisorValidationError(f"{field_name} must be >= {min_value}, got {val}")
    if max_value is not None and val > max_value:
        raise SupervisorValidationError(f"{field_name} must be <= {max_value}, got {val}")
    return val


def _require_strict_int(
    raw: Any,
    *,
    field_name: str,
    min_value: int | None = None,
    max_value: int | None = None,
) -> int:
    if type(raw) is not int:
        raise SupervisorValidationError(f"{field_name} must be a strict int (not bool/float), got {raw!r}")
    if min_value is not None and raw < min_value:
        raise SupervisorValidationError(f"{field_name} must be >= {min_value}, got {raw}")
    if max_value is not None and raw > max_value:
        raise SupervisorValidationError(f"{field_name} must be <= {max_value}, got {raw}")
    return raw


def _normalize_utc_iso(value: datetime | str | None = None) -> str:
    if value is None:
        return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, datetime):
        if value.tzinfo is None or value.utcoffset() is None:
            raise LedgerIntegrityError(f"UTC timestamp must be timezone-aware, got naive {value!r}")
        return value.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    if isinstance(value, str):
        raw = value.strip()
        if not raw:
            raise LedgerIntegrityError("UTC timestamp string cannot be empty")
        parsed_raw = raw[:-1] + "+00:00" if raw.endswith(("Z", "z")) else raw
        try:
            dt = datetime.fromisoformat(parsed_raw)
        except ValueError as exc:
            raise LedgerIntegrityError(f"Malformed ISO-8601 timestamp {value!r}: {exc}") from exc
        if dt.tzinfo is None or dt.utcoffset() is None:
            raise LedgerIntegrityError(f"UTC timestamp must include timezone offset or 'Z': {value!r}")
        return dt.astimezone(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")
    raise LedgerIntegrityError(f"Unsupported timestamp type {type(value).__name__}")


def _parse_utc_datetime(iso_utc: str) -> datetime:
    norm = _normalize_utc_iso(iso_utc)
    return datetime.fromisoformat(norm[:-1] + "+00:00")


def _parse_iso_date(raw: str, *, field_name: str) -> date:
    if not isinstance(raw, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", raw.strip()):
        raise LedgerIntegrityError(f"{field_name} must be YYYY-MM-DD, got {raw!r}")
    try:
        return date.fromisoformat(raw.strip())
    except ValueError as exc:
        raise LedgerIntegrityError(f"Invalid calendar date for {field_name}: {raw!r}") from exc


def assert_port_allowed(port: Any, *, field_name: str = "port") -> int:
    """Fail-closed port guard: ALWAYS raises SecurityError if port == 8317 or invalid."""
    if type(port) is not int:
        raise SecurityError(f"{field_name} must be a strict int, got {port!r}")
    if port == FORBIDDEN_EXTERNAL_CLIPROXY_PORT:
        raise SecurityError(
            f"BLOCKED: port {FORBIDDEN_EXTERNAL_CLIPROXY_PORT} belongs to the external Windows CLIProxyAPI "
            "instance and MUST NEVER be touched by workspace code."
        )
    if port < 1 or port > 65535:
        raise SecurityError(f"{field_name} out of valid TCP range 1..65535: {port}")
    return port


def assert_url_allowed(
    url: str,
    *,
    require_loopback: bool = False,
    require_https: bool = False,
    allowed_hosts: frozenset[str] | None = None,
) -> str:
    """Fail-closed URL guard blocking port 8317, api.poolai.win, and unexpected hosts."""
    if not isinstance(url, str) or not url.strip():
        raise SecurityError("Endpoint URL must be a non-empty string")
    clean = url.strip()
    parsed = urlsplit(clean)
    if parsed.scheme not in ("http", "https"):
        raise SecurityError(f"Unsupported URL scheme in {clean!r}")
    if require_https and parsed.scheme != "https":
        raise SecurityError(f"HTTPS is required for official API endpoint, got {clean!r}")

    host = (parsed.hostname or "").strip().lower()
    if not host:
        raise SecurityError(f"Missing hostname in URL {clean!r}")

    for blocked in BLOCKED_UPSTREAM_DOMAINS:
        if host == blocked or host.endswith(f".{blocked}") or blocked in clean.lower():
            raise SecurityError(f"BLOCKED third-party upstream route detected in URL: {blocked}")

    try:
        port = parsed.port
    except ValueError as exc:
        raise SecurityError(f"Malformed port in URL {clean!r}: {exc}") from exc

    if port is not None:
        assert_port_allowed(port, field_name="url.port")

    if require_loopback and host not in LOOPBACK_HOSTS:
        raise SecurityError(f"Loopback host required (127.0.0.1/localhost/::1), got {host!r}")

    if allowed_hosts is not None and host not in allowed_hosts:
        raise SecurityError(f"Host {host!r} not in official allowlist {sorted(allowed_hosts)}")

    return clean


# ==============================================================================
# Dynamic Gateway-Owner Resolution & Non-Mutating YAML Sanitizer (17852)
# ==============================================================================


@dataclass(frozen=True)
class GatewayOwnerConfig:
    """Dynamically resolved project CLIProxyAPI owner metadata from gateway-owner.json."""

    port: int
    executable: Path
    home: Path
    config_path: Path
    owner_file: Path
    recorded_pid: int | None
    status: str
    release: str | None = None

    @property
    def base_url(self) -> str:
        return f"http://127.0.0.1:{self.port}"

    @property
    def chat_completions_url(self) -> str:
        return f"http://127.0.0.1:{self.port}/v1/chat/completions"

    def to_safe_dict(self) -> dict[str, Any]:
        return {
            "port": self.port,
            "executable": str(self.executable),
            "home": str(self.home),
            "config_path": str(self.config_path),
            "owner_file": str(self.owner_file),
            "recorded_pid": self.recorded_pid,
            "status": self.status,
            "release": self.release,
            "base_url": self.base_url,
        }


def resolve_project_gateway_owner(
    owner_json_path: Path | str | None = None,
    *,
    expected_port: int | None = None,
) -> GatewayOwnerConfig:
    """Resolve Trader standalone CLIProxyAPI metadata dynamically from gateway-owner.json.

    Never hardcodes static legacy paths and ALWAYS raises ``SecurityError`` if port == 8317.
    """
    _enforce_module_safety_invariants()
    path = Path(owner_json_path) if owner_json_path is not None else DEFAULT_GATEWAY_OWNER_PATH
    if not path.is_file():
        raise FileNotFoundError(f"gateway-owner.json not found: {path}")

    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SecurityError(f"Failed to read/parse gateway-owner.json ({path}): {exc}") from exc

    if not isinstance(raw, Mapping):
        raise SecurityError("gateway-owner.json root must be a JSON object")

    port = assert_port_allowed(raw.get("port"), field_name="gateway-owner.port")
    if expected_port is not None:
        exp = assert_port_allowed(expected_port, field_name="expected_port")
        if port != exp:
            raise SecurityError(f"gateway-owner.json port {port} != expected project gateway port {exp}")

    missing = [k for k in ("executable", "home", "configPath") if not isinstance(raw.get(k), str) or not raw[k].strip()]
    if missing:
        raise SecurityError(f"gateway-owner.json missing required string fields: {missing}")

    executable = Path(str(raw["executable"]).strip())
    home = Path(str(raw["home"]).strip())
    config_path = Path(str(raw["configPath"]).strip())

    raw_pid = raw.get("pid")
    recorded_pid: int | None
    if raw_pid is None:
        recorded_pid = None
    elif type(raw_pid) is int and raw_pid > 0:
        recorded_pid = raw_pid
    else:
        recorded_pid = None

    return GatewayOwnerConfig(
        port=port,
        executable=executable,
        home=home,
        config_path=config_path,
        owner_file=path,
        recorded_pid=recorded_pid,
        status=str(raw.get("status") or "unknown"),
        release=str(raw["release"]) if isinstance(raw.get("release"), str) else None,
    )


def _contains_blocked_domain(obj: Any) -> bool:
    """Return True if any string inside a nested dict/list/scalar mentions a blocked upstream domain."""
    if isinstance(obj, str):
        low = obj.lower()
        return any(dom in low for dom in BLOCKED_UPSTREAM_DOMAINS)
    if isinstance(obj, Mapping):
        return any(_contains_blocked_domain(k) or _contains_blocked_domain(v) for k, v in obj.items())
    if isinstance(obj, (list, tuple)):
        return any(_contains_blocked_domain(item) for item in obj)
    return False


def _deep_strip_blocked_entries(obj: Any, *, stats: dict[str, int], parent_key: str = "") -> Any:
    """Recursively remove any list element or dict entry targeting blocked third-party domains."""
    if isinstance(obj, list):
        kept: list[Any] = []
        for item in obj:
            if _contains_blocked_domain(item):
                stats["stripped_entries"] += 1
                if parent_key:
                    stats[f"stripped_from_{parent_key}"] = stats.get(f"stripped_from_{parent_key}", 0) + 1
                continue
            kept.append(_deep_strip_blocked_entries(item, stats=stats, parent_key=parent_key))
        return kept

    if isinstance(obj, Mapping):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            key_str = str(k)
            if _contains_blocked_domain(key_str):
                stats["stripped_entries"] += 1
                continue
            if isinstance(v, str) and _contains_blocked_domain(v):
                stats["stripped_entries"] += 1
                continue
            cleaned_v = _deep_strip_blocked_entries(v, stats=stats, parent_key=key_str)
            # Drop now-empty third-party upstream provider blocks while preserving access.api-keys
            if (
                parent_key == "api-keys"
                and isinstance(cleaned_v, list)
                and len(cleaned_v) == 0
                and key_str in ("openai-compatibility", "claude", "claude-api-key", "gemini", "codex")
            ):
                continue
            if (
                key_str in ("claude-api-key", "openai-compatibility", "gemini-api-key", "codex-api-key")
                and isinstance(cleaned_v, list)
                and len(cleaned_v) == 0
            ):
                continue
            out[key_str] = cleaned_v
        # Drop empty top-level upstream api-keys dict (distinct from access.api-keys)
        if parent_key == "" and isinstance(out.get("api-keys"), dict) and len(out["api-keys"]) == 0:
            del out["api-keys"]
        return out

    return obj


def extract_gateway_port(cfg: Mapping[str, Any]) -> int | None:
    """Extract configured listener port from either v8 (server.port) or legacy flat (port) YAML."""
    server = cfg.get("server")
    if isinstance(server, Mapping) and "port" in server:
        return assert_port_allowed(server["port"], field_name="server.port")
    if "port" in cfg:
        return assert_port_allowed(cfg["port"], field_name="port")
    return None


def extract_request_retry(cfg: Mapping[str, Any]) -> int | None:
    """Extract request-retry value from either v8 (routing.retry.request-retry) or flat YAML."""
    routing = cfg.get("routing")
    if isinstance(routing, Mapping):
        retry = routing.get("retry")
        if isinstance(retry, Mapping) and "request-retry" in retry:
            val = retry["request-retry"]
            if type(val) is int:
                return val
    if "request-retry" in cfg and type(cfg["request-retry"]) is int:
        return int(cfg["request-retry"])
    return None


def extract_loopback_client_api_key(cfg: Mapping[str, Any]) -> str | None:
    """Extract first local loopback client key in memory (never log or persist into receipts)."""
    access = cfg.get("access")
    if isinstance(access, Mapping):
        keys = access.get("api-keys")
        if isinstance(keys, list):
            for item in keys:
                if isinstance(item, str) and item.strip() and not _contains_blocked_domain(item):
                    return item.strip()
    top_keys = cfg.get("api-keys")
    if isinstance(top_keys, list):
        for item in top_keys:
            if isinstance(item, str) and item.strip() and not _contains_blocked_domain(item):
                return item.strip()
    return None


@dataclass(frozen=True)
class SanitizedGatewayResult:
    """Metadata proving sanitized temp YAML stripped blocked third-party routes safely."""

    source_yaml_path: Path | None
    output_yaml_path: Path | None
    port: int | None
    request_retry: int
    stripped_entries_count: int
    sanitized_yaml_sha256: str
    poolai_present: bool
    sanitized_yaml_text: str

    def to_safe_receipt(self) -> dict[str, Any]:
        """Receipt-safe dict (excludes raw YAML text so local client keys are never echoed)."""
        return {
            "source_yaml_path": str(self.source_yaml_path) if self.source_yaml_path else None,
            "output_yaml_path": str(self.output_yaml_path) if self.output_yaml_path else None,
            "port": self.port,
            "request_retry": self.request_retry,
            "stripped_entries_count": self.stripped_entries_count,
            "sanitized_yaml_sha256": self.sanitized_yaml_sha256,
            "poolai_present": self.poolai_present,
        }


def sanitize_gateway_yaml_text(
    raw_yaml_text: str,
    *,
    expected_port: int | None = None,
) -> SanitizedGatewayResult:
    """Sanitize CLIProxyAPI YAML text in-memory without mutating any source file.

    Handles both v8 nested (``api-keys.openai-compatibility``, ``api-keys.claude``,
    ``routing.retry.request-retry``) and legacy flat (``claude-api-key``,
    ``openai-compatibility``, ``request-retry``) schemas.
    """
    _enforce_module_safety_invariants()
    if not isinstance(raw_yaml_text, str) or not raw_yaml_text.strip():
        raise SecurityError("Source gateway YAML text must be a non-empty string")

    try:
        parsed = yaml.safe_load(raw_yaml_text)
    except yaml.YAMLError as exc:
        raise SecurityError(f"Invalid gateway YAML syntax: {exc}") from exc

    if not isinstance(parsed, Mapping):
        raise SecurityError("Gateway YAML root must be a mapping")

    # 1. Fail-closed port check (NEVER allow 8317)
    port = extract_gateway_port(parsed)
    if expected_port is not None:
        exp = assert_port_allowed(expected_port, field_name="expected_port")
        if port is not None and port != exp:
            raise SecurityError(f"Gateway YAML port {port} != expected port {exp}")

    # 2. Recursively strip all blocked third-party upstream routes (e.g. api.poolai.win)
    stats: dict[str, int] = {"stripped_entries": 0}
    sanitized: dict[str, Any] = _deep_strip_blocked_entries(dict(parsed), stats=stats, parent_key="")

    # 3. Enforce loopback bind & request-retry: 0 across both v8 and flat schemas
    is_v8 = sanitized.get("config-version") == 8 or isinstance(sanitized.get("routing"), Mapping)
    if is_v8:
        routing = dict(sanitized.get("routing") or {})
        retry = dict(routing.get("retry") or {}) if isinstance(routing.get("retry"), Mapping) else {}
        retry["request-retry"] = 0
        retry["max-retry-interval"] = 0
        routing["retry"] = retry
        sanitized["routing"] = routing

        server = dict(sanitized.get("server") or {}) if isinstance(sanitized.get("server"), Mapping) else {}
        host = str(server.get("host") or "127.0.0.1").strip().lower()
        if host not in LOOPBACK_HOSTS:
            raise SecurityError(f"Non-loopback server.host forbidden in gateway YAML: {host!r}")
        server["host"] = host
        if port is not None:
            server["port"] = port
        sanitized["server"] = server
    else:
        sanitized["request-retry"] = 0
        host = str(sanitized.get("host") or "127.0.0.1").strip().lower()
        if host not in LOOPBACK_HOSTS:
            raise SecurityError(f"Non-loopback host forbidden in gateway YAML: {host!r}")
        sanitized["host"] = host
        if port is not None:
            sanitized["port"] = port

    # 4. Serialize and verify fail-closed post-conditions (zero bare asserts -> python -O safe!)
    dumped = yaml.safe_dump(sanitized, sort_keys=False, allow_unicode=True)
    dumped_low = dumped.lower()
    for blocked in BLOCKED_UPSTREAM_DOMAINS:
        if blocked in dumped_low:
            raise SecurityError(f"Sanitized gateway YAML post-check FAILED: {blocked!r} still present!")

    reparsed = yaml.safe_load(dumped)
    if not isinstance(reparsed, Mapping):
        raise SecurityError("Sanitized gateway YAML failed round-trip parse")
    verified_port = extract_gateway_port(reparsed)
    if verified_port == FORBIDDEN_EXTERNAL_CLIPROXY_PORT:
        raise SecurityError("Sanitized gateway YAML still references forbidden port 8317")
    verified_retry = extract_request_retry(reparsed)
    if verified_retry != 0:
        raise SecurityError(f"Sanitized gateway YAML failed request-retry == 0 check, got {verified_retry!r}")

    return SanitizedGatewayResult(
        source_yaml_path=None,
        output_yaml_path=None,
        port=verified_port,
        request_retry=verified_retry,
        stripped_entries_count=stats["stripped_entries"],
        sanitized_yaml_sha256=_sha256_text(dumped),
        poolai_present=any(dom in dumped_low for dom in BLOCKED_UPSTREAM_DOMAINS),
        sanitized_yaml_text=dumped,
    )


def write_sanitized_gateway_config(
    source_yaml_path: Path | str,
    output_yaml_path: Path | str | None = None,
    *,
    expected_port: int | None = None,
) -> SanitizedGatewayResult:
    """Copy and sanitize ``managed.yaml`` into a separate temp YAML without mutating the source."""
    src = Path(source_yaml_path).resolve()
    dst = Path(output_yaml_path).resolve() if output_yaml_path is not None else DEFAULT_SANITIZED_GATEWAY_YAML_PATH
    if not src.is_file():
        raise FileNotFoundError(f"Source gateway YAML not found: {src}")
    if src == dst:
        raise SecurityError("Refusing to overwrite source managed.yaml in-place; output path must be distinct.")

    raw_text = src.read_text(encoding="utf-8")
    result = sanitize_gateway_yaml_text(raw_text, expected_port=expected_port)
    _atomic_write_text(dst, result.sanitized_yaml_text)

    # Read-back verification from disk (immune to python -O)
    written_text = dst.read_text(encoding="utf-8")
    if any(dom in written_text.lower() for dom in BLOCKED_UPSTREAM_DOMAINS):
        raise SecurityError("Disk read-back check FAILED: blocked upstream domain found in sanitized YAML")

    return SanitizedGatewayResult(
        source_yaml_path=src,
        output_yaml_path=dst,
        port=result.port,
        request_retry=result.request_retry,
        stripped_entries_count=result.stripped_entries_count,
        sanitized_yaml_sha256=_sha256_text(written_text),
        poolai_present=False,
        sanitized_yaml_text=written_text,
    )


# ==============================================================================
# Standalone Project Gateway Lifecycle Manager (Spawns & Stops ONLY Its Own PID)
# ==============================================================================


def _is_pid_alive(pid: int) -> bool:
    """Cross-platform non-invasive PID liveness check using windowless subprocess on Windows."""
    if type(pid) is not int or pid <= 0:
        return False
    if os.name == "nt":
        try:
            proc = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}", "/FO", "CSV", "/NH"],
                capture_output=True,
                text=True,
                timeout=5.0,
                check=False,
                creationflags=_NO_WINDOW_FLAGS,
            )
            return f'"{pid}"' in (proc.stdout or "")
        except OSError:
            return False
    try:
        os.kill(pid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def _is_tcp_port_open(host: str, port: int, timeout_sec: float = 0.5) -> bool:
    assert_port_allowed(port, field_name="tcp_probe_port")
    if host.lower() not in LOOPBACK_HOSTS:
        raise SecurityError(f"Refusing non-loopback TCP probe to {host!r}")
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout_sec)
        return sock.connect_ex((host, port)) == 0


def cleanup_stale_gateway_pid_file(pid_file: Path) -> dict[str, Any]:
    """Remove a stale Wave 4 PID tracking file ONLY if its recorded PID is confirmed dead."""
    if not pid_file.is_file():
        return {"found": False, "stale_cleaned": False, "pid": None}
    try:
        data = json.loads(pid_file.read_text(encoding="utf-8"))
        pid = data.get("pid") if isinstance(data, Mapping) else None
    except (OSError, ValueError):
        pid_file.unlink(missing_ok=True)
        return {"found": True, "stale_cleaned": True, "pid": None, "reason": "corrupt_pid_file"}

    if type(pid) is int and pid > 0 and _is_pid_alive(pid):
        return {"found": True, "stale_cleaned": False, "pid": pid, "alive": True}

    pid_file.unlink(missing_ok=True)
    return {"found": True, "stale_cleaned": True, "pid": pid, "alive": False}


class StandaloneGateway17852:
    """Safe context manager for standalone project CLIProxyAPI (17852) test runs.

    Safety invariants:
      - Resolves executable/home/configPath/port dynamically from ``gateway-owner.json``.
      - ALWAYS blocks port ``8317`` with ``SecurityError``.
      - Writes sanitized temp YAML blocking ``api.poolai.win`` (never mutates ``managed.yaml``).
      - Redirects stdout/stderr logs strictly into ``.runtime/paperclip/`` (away from ``E:``).
      - Cleans up stale dead PIDs before starting; refuses to kill unrelated listeners.
      - Uses ``creationflags=_NO_WINDOW_FLAGS`` on all ``subprocess`` calls.
      - Stops ONLY the exact child PID spawned by this instance inside ``finally:``.
    """

    def __init__(
        self,
        *,
        owner_json_path: Path | str | None = None,
        sanitized_yaml_path: Path | str | None = None,
        log_dir: Path | str | None = None,
        pid_file_path: Path | str | None = None,
        expected_port: int = DEFAULT_PROJECT_CLIPROXY_PORT,
        startup_timeout_sec: float = 10.0,
        poll_interval_sec: float = 0.25,
    ) -> None:
        _enforce_module_safety_invariants()
        self.expected_port = assert_port_allowed(expected_port, field_name="expected_port")
        self.owner_json_path = Path(owner_json_path) if owner_json_path is not None else DEFAULT_GATEWAY_OWNER_PATH
        self.log_dir = Path(log_dir) if log_dir is not None else DEFAULT_PAPERCLIP_RUNTIME_DIR
        self.sanitized_yaml_path = (
            Path(sanitized_yaml_path) if sanitized_yaml_path is not None else DEFAULT_SANITIZED_GATEWAY_YAML_PATH
        )
        self.pid_file_path = Path(pid_file_path) if pid_file_path is not None else DEFAULT_WAVE4_GATEWAY_PID_PATH
        self.stdout_log_path = self.log_dir / DEFAULT_WAVE4_GATEWAY_STDOUT_LOG.name
        self.stderr_log_path = self.log_dir / DEFAULT_WAVE4_GATEWAY_STDERR_LOG.name
        self.startup_timeout_sec = _require_finite_float(
            startup_timeout_sec, field_name="startup_timeout_sec", strictly_positive=True
        )
        self.poll_interval_sec = _require_finite_float(
            poll_interval_sec, field_name="poll_interval_sec", strictly_positive=True
        )

        self.owner: GatewayOwnerConfig | None = None
        self.sanitized: SanitizedGatewayResult | None = None
        self._proc: subprocess.Popen[bytes] | None = None
        self.spawned_pid: int | None = None
        self._stdout_fh: Any = None
        self._stderr_fh: Any = None
        self.stale_cleanup_report: dict[str, Any] = {}
        self.stopped_spawned_pid: int | None = None

    def start(self) -> StandaloneGateway17852:
        """Prepare sanitized config, clean stale dead PIDs, and launch project gateway on loopback."""
        _enforce_module_safety_invariants()
        self.owner = resolve_project_gateway_owner(self.owner_json_path, expected_port=self.expected_port)
        assert_port_allowed(self.owner.port, field_name="owner.port")

        # Ensure log directory stays off E: (within workspace .runtime/paperclip/ or test tempdir)
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.stale_cleanup_report = cleanup_stale_gateway_pid_file(self.pid_file_path)

        # Also detect whether gateway-owner.json's previously recorded PID is stale (informational only)
        if self.owner.recorded_pid is not None:
            self.stale_cleanup_report["owner_recorded_pid"] = self.owner.recorded_pid
            self.stale_cleanup_report["owner_recorded_pid_alive"] = _is_pid_alive(self.owner.recorded_pid)

        # Never start a competing listener if port is already occupied by an unknown/existing owner
        if _is_tcp_port_open("127.0.0.1", self.owner.port):
            raise SecurityError(
                f"Port 127.0.0.1:{self.owner.port} is already occupied; refusing to kill or share an external listener."
            )

        self.sanitized = write_sanitized_gateway_config(
            self.owner.config_path,
            self.sanitized_yaml_path,
            expected_port=self.owner.port,
        )

        if not self.owner.executable.is_file():
            raise FileNotFoundError(f"Gateway executable not found: {self.owner.executable}")

        cmd = [str(self.owner.executable), "-config", str(self.sanitized_yaml_path)]
        try:
            self._stdout_fh = self.stdout_log_path.open("ab")
            self._stderr_fh = self.stderr_log_path.open("ab")
            self._proc = subprocess.Popen(
                cmd,
                cwd=str(self.owner.home) if self.owner.home.is_dir() else str(self.log_dir),
                stdout=self._stdout_fh,
                stderr=self._stderr_fh,
                creationflags=_NO_WINDOW_FLAGS,
            )
            self.spawned_pid = int(self._proc.pid)
            _atomic_write_json(
                self.pid_file_path,
                {
                    "pid": self.spawned_pid,
                    "port": self.owner.port,
                    "sanitized_config": str(self.sanitized_yaml_path),
                    "stdout_log": str(self.stdout_log_path),
                    "stderr_log": str(self.stderr_log_path),
                    "started_utc": _normalize_utc_iso(),
                },
            )
            deadline = time.monotonic() + self.startup_timeout_sec
            while time.monotonic() < deadline:
                if self._proc.poll() is not None:
                    raise MacroSupervisorError(
                        f"Spawned gateway PID {self.spawned_pid} exited prematurely (rc={self._proc.returncode})"
                    )
                if _is_tcp_port_open("127.0.0.1", self.owner.port, timeout_sec=0.25):
                    return self
                time.sleep(self.poll_interval_sec)
            raise TimeoutError(
                f"Gateway PID {self.spawned_pid} did not open 127.0.0.1:{self.owner.port} "
                f"within {self.startup_timeout_sec}s"
            )
        except Exception:
            self.stop()
            raise

    def stop(self) -> int | None:
        """Stop ONLY the exact PID spawned by this instance (never touches port 8317 or other PIDs)."""
        stopped_pid: int | None = None
        try:
            if self._proc is not None:
                pid = int(self._proc.pid)
                if self._proc.poll() is None:
                    self._proc.terminate()
                    try:
                        self._proc.wait(timeout=5.0)
                    except subprocess.TimeoutExpired:
                        self._proc.kill()
                        self._proc.wait(timeout=5.0)
                stopped_pid = pid
                self.stopped_spawned_pid = pid
        finally:
            self._proc = None
            if self._stdout_fh is not None:
                try:
                    self._stdout_fh.close()
                except OSError:
                    pass
                self._stdout_fh = None
            if self._stderr_fh is not None:
                try:
                    self._stderr_fh.close()
                except OSError:
                    pass
                self._stderr_fh = None
            if self.spawned_pid is not None and self.pid_file_path.is_file():
                try:
                    recorded = json.loads(self.pid_file_path.read_text(encoding="utf-8"))
                    if isinstance(recorded, Mapping) and recorded.get("pid") == self.spawned_pid:
                        self.pid_file_path.unlink(missing_ok=True)
                except OSError:
                    pass
        return stopped_pid

    def __enter__(self) -> StandaloneGateway17852:
        return self.start()

    def __exit__(self, _exc_type: Any, _exc: Any, _tb: Any) -> None:
        self.stop()


# ==============================================================================
# Strict Typed Decision Output (MacroSupervisorDecision)
# ==============================================================================


@dataclass(frozen=True)
class MacroSupervisorDecision:
    """Strict bounded advisory output emitted by Macro AI Supervisor.

    Invariant: NEVER emits orders, lot sizes, or PropGuard overrides.
    """

    scenario_id: str
    provider_mode: str
    model_id: str
    status: str
    degraded: bool
    risk_mult: float
    regime_tag: str
    confidence: float
    reasoning_bullets: tuple[str, ...]
    prompt_sha256: str
    response_sha256: str
    order_send_capable: bool = False
    execution_capability: bool = False
    prop_guard_override_allowed: bool = False
    attempts: int = 1
    latency_ms: float = 0.0
    estimated_cost_usd: float = 0.0
    created_utc: str = ""

    def __post_init__(self) -> None:
        _enforce_module_safety_invariants()
        if self.order_send_capable is not False:
            raise SupervisorValidationError(
                f"order_send_capable MUST be strictly False, got {self.order_send_capable!r}"
            )
        if self.execution_capability is not False:
            raise SupervisorValidationError(
                f"execution_capability MUST be strictly False, got {self.execution_capability!r}"
            )
        if self.prop_guard_override_allowed is not False:
            raise SupervisorValidationError(
                f"prop_guard_override_allowed MUST be strictly False, got {self.prop_guard_override_allowed!r}"
            )

        if isinstance(self.risk_mult, bool) or not isinstance(self.risk_mult, (int, float)):
            raise SupervisorValidationError(f"risk_mult must be a finite float, got {self.risk_mult!r}")
        rm = float(self.risk_mult)
        if not math.isfinite(rm) or rm not in ALLOWED_RISK_MULTS:
            raise SupervisorValidationError(
                f"risk_mult MUST be strictly in {ALLOWED_RISK_MULTS}, got {self.risk_mult!r}"
            )
        object.__setattr__(self, "risk_mult", rm)

        if not isinstance(self.regime_tag, str) or self.regime_tag not in ALLOWED_REGIME_TAGS:
            raise SupervisorValidationError(
                f"regime_tag MUST be in {sorted(ALLOWED_REGIME_TAGS)}, got {self.regime_tag!r}"
            )

        conf = _require_finite_float(self.confidence, field_name="confidence", min_value=0.0, max_value=1.0)
        object.__setattr__(self, "confidence", round(conf, 6))

        if not isinstance(self.reasoning_bullets, tuple) or not (1 <= len(self.reasoning_bullets) <= 6):
            raise SupervisorValidationError("reasoning_bullets must be a tuple of 1..6 non-empty strings")
        cleaned_bullets: list[str] = []
        for idx, bullet in enumerate(self.reasoning_bullets):
            if not isinstance(bullet, str) or not bullet.strip():
                raise SupervisorValidationError(f"reasoning_bullets[{idx}] must be a non-empty string")
            cleaned_bullets.append(bullet.strip()[:280])
        object.__setattr__(self, "reasoning_bullets", tuple(cleaned_bullets))

        if not isinstance(self.prompt_sha256, str) or not _SHA256_HEX_RE.match(self.prompt_sha256):
            raise SupervisorValidationError(f"Invalid prompt_sha256: {self.prompt_sha256!r}")
        if not isinstance(self.response_sha256, str) or not _SHA256_HEX_RE.match(self.response_sha256):
            raise SupervisorValidationError(f"Invalid response_sha256: {self.response_sha256!r}")

        _require_strict_int(self.attempts, field_name="attempts", min_value=0, max_value=10)
        _require_finite_float(self.latency_ms, field_name="latency_ms", min_value=0.0)
        _require_finite_float(self.estimated_cost_usd, field_name="estimated_cost_usd", min_value=0.0)

        ts = _normalize_utc_iso(self.created_utc) if self.created_utc else _normalize_utc_iso()
        object.__setattr__(self, "created_utc", ts)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["reasoning_bullets"] = list(self.reasoning_bullets)
        return d

    def canonical_decision_payload(self) -> dict[str, Any]:
        """Deterministic core decision payload hashed for prospective SHA-256 commitments."""
        return {
            "scenario_id": self.scenario_id,
            "provider_mode": self.provider_mode,
            "model_id": self.model_id,
            "status": self.status,
            "degraded": self.degraded,
            "risk_mult": self.risk_mult,
            "regime_tag": self.regime_tag,
            "confidence": self.confidence,
            "reasoning_bullets": list(self.reasoning_bullets),
            "prompt_sha256": self.prompt_sha256,
            "response_sha256": self.response_sha256,
            "order_send_capable": False,
            "execution_capability": False,
            "prop_guard_override_allowed": False,
        }

    def decision_sha256(self) -> str:
        return canonical_payload_sha256(self.canonical_decision_payload())


def _extract_json_object(raw_text: str) -> dict[str, Any]:
    """Extract a single JSON object from plain JSON or fenced markdown output."""
    text = raw_text.strip()
    if not text:
        raise SupervisorValidationError("Empty model response text")

    fenced = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", text, flags=re.DOTALL | re.IGNORECASE)
    candidate = fenced.group(1) if fenced else text

    if not candidate.startswith("{"):
        first = candidate.find("{")
        last = candidate.rfind("}")
        if first != -1 and last > first:
            candidate = candidate[first : last + 1]

    try:
        parsed = json.loads(candidate)
    except ValueError as exc:
        raise SupervisorValidationError(f"Model response is not valid JSON object: {exc}") from exc

    if not isinstance(parsed, dict):
        raise SupervisorValidationError(f"Expected JSON object from model, got {type(parsed).__name__}")
    return parsed


def parse_supervisor_decision_json(
    raw_text: str,
    *,
    scenario_id: str,
    provider_mode: ProviderMode | str,
    model_id: str,
    prompt_sha256: str,
    attempts: int = 1,
    latency_ms: float = 0.0,
    estimated_cost_usd: float = 0.0,
    created_utc: str = "",
) -> MacroSupervisorDecision:
    """Strictly parse LLM JSON output into a validated ``MacroSupervisorDecision``."""
    data = _extract_json_object(raw_text)

    # Reject any forbidden execution / order / PropGuard override keys fail-closed
    lower_keys = {str(k).strip().lower() for k in data}
    forbidden_hits = sorted(lower_keys & _FORBIDDEN_DECISION_KEYS)
    if forbidden_hits:
        raise SupervisorValidationError(
            f"Forbidden order/execution override fields in model output: {forbidden_hits}"
        )
    raw_action = data.get("action")
    if isinstance(raw_action, str) and raw_action.strip().upper() in {"BUY", "SELL", "OPEN", "CLOSE", "ORDER"}:
        raise SupervisorValidationError(f"Forbidden trade execution action in model output: {raw_action!r}")

    if "order_send_capable" in data and data["order_send_capable"] is not False:
        raise SupervisorValidationError("Model attempted to set order_send_capable != False")

    raw_bullets = data.get("reasoning_bullets")
    if not isinstance(raw_bullets, list) or not raw_bullets:
        raise SupervisorValidationError("Model output missing non-empty 'reasoning_bullets' list")
    bullets_tuple = tuple(str(x) for x in raw_bullets[:6])

    raw_tag = str(data.get("regime_tag") or "").strip().upper()
    mode_val = provider_mode.value if isinstance(provider_mode, ProviderMode) else str(provider_mode)

    return MacroSupervisorDecision(
        scenario_id=scenario_id,
        provider_mode=mode_val,
        model_id=model_id,
        status=STATUS_OK,
        degraded=False,
        risk_mult=data.get("risk_mult"),  # type: ignore[arg-type]
        regime_tag=raw_tag,
        confidence=data.get("confidence"),  # type: ignore[arg-type]
        reasoning_bullets=bullets_tuple,
        prompt_sha256=prompt_sha256,
        response_sha256=_sha256_text(raw_text),
        order_send_capable=False,
        execution_capability=False,
        prop_guard_override_allowed=False,
        attempts=attempts,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        created_utc=created_utc,
    )


def build_degraded_neutral_decision(
    *,
    scenario_id: str,
    provider_mode: ProviderMode | str,
    model_id: str,
    status: str,
    reason: str,
    prompt_sha256: str,
    attempts: int,
    latency_ms: float = 0.0,
    estimated_cost_usd: float = 0.0,
    created_utc: str = "",
) -> MacroSupervisorDecision:
    """Build a fail-closed neutral (1.0x identity, 0.0 confidence) degraded advisory decision."""
    mode_val = provider_mode.value if isinstance(provider_mode, ProviderMode) else str(provider_mode)
    payload_stub = canonical_json_dumps(
        {
            "status": status,
            "reason": reason,
            "provider_mode": mode_val,
            "scenario_id": scenario_id,
        }
    )
    return MacroSupervisorDecision(
        scenario_id=scenario_id,
        provider_mode=mode_val,
        model_id=model_id,
        status=status,
        degraded=True,
        risk_mult=1.0,
        regime_tag="NEUTRAL",
        confidence=0.0,
        reasoning_bullets=(
            f"Degraded fail-closed fallback ({status}): {reason[:200]}",
            "Emitting NEUTRAL 1.0x advisory pass-through; deterministic PropGuard hard stops remain unchanged.",
        ),
        prompt_sha256=prompt_sha256,
        response_sha256=_sha256_text(payload_stub),
        order_send_capable=False,
        execution_capability=False,
        prop_guard_override_allowed=False,
        attempts=attempts,
        latency_ms=latency_ms,
        estimated_cost_usd=estimated_cost_usd,
        created_utc=created_utc,
    )


# ==============================================================================
# Anti-Contamination Anonymizer (24 Scenarios + Deterministic Clean Validator)
# ==============================================================================

_YEAR_RE: Final[re.Pattern[str]] = re.compile(r"(?<!\d)(?:199\d|20[0-3]\d)(?!\d)")
_ISO_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\b\d{4}[-/.]\d{1,2}[-/.]\d{1,2}\b")
_SLASH_DATE_RE: Final[re.Pattern[str]] = re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]\d{2,4}\b")
_MONTH_DATE_RE: Final[re.Pattern[str]] = re.compile(
    r"\b(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|"
    r"jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"
    r"(?:\s+\d{1,2}(?:st|nd|rd|th)?(?:\s*,?\s*\d{2,4})?|\s+\d{4})\b",
    re.IGNORECASE,
)

_FORBIDDEN_EVENT_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    ("EVENT_SVB", re.compile(r"\b(?:svb|silicon\s+valley\s+bank|signature\s+bank|first\s+republic)\b", re.I)),
    ("EVENT_CREDIT_SUISSE", re.compile(r"\b(?:credit\s+suisse|lehman|bear\s+stearns|archegos)\b", re.I)),
    ("EVENT_COVID", re.compile(r"\b(?:covid(?:-?19)?|coronavirus|sars-cov|omicron|pandemic)\b", re.I)),
    ("EVENT_AUG5_YEN", re.compile(r"\b(?:aug(?:ust)?\s*5|yen\s+carry|carry\s+trade\s+crash|black\s+monday)\b", re.I)),
    ("EVENT_GILT_BREXIT", re.compile(r"\b(?:brexit|gilt\s+crisis|mini-budget|liz\s+truss|snb\s+shock)\b", re.I)),
    ("EVENT_GEOPOLITICAL_NAMED", re.compile(r"\b(?:ukraine|russia|gaza|israel|iran|red\s+sea|suez|taiwan)\b", re.I)),
    ("EVENT_CRYPTO_NAMED", re.compile(r"\b(?:ftx|terra\s*luna|evergrande|liberation\s+day|taper\s+tantrum)\b", re.I)),
    ("EVENT_GFC", re.compile(r"\b(?:gfc|subprime|dot-com|jackson\s+hole|flash\s+crash\s+20\d\d)\b", re.I)),
)

_FORBIDDEN_ENTITY_PATTERNS: Final[tuple[tuple[str, re.Pattern[str]], ...]] = (
    (
        "ENTITY_CENTRAL_BANK",
        re.compile(
            r"\b(?:fomc|federal\s+reserve|the\s+fed|fed\s+chair|powell|boj|bank\s+of\s+japan|"
            r"ueda|kuroda|ecb|lagarde|boe|bank\s+of\s+england|rba|rbnz|boc|pboc|snb|opec|trump|biden|yellen)\b",
            re.I,
        ),
    ),
    (
        "ENTITY_TICKER_OR_CCY",
        re.compile(
            r"\b(?:usdjpy|eurusd|gbpusd|audusd|usdcad|usdchf|nzdusd|eurjpy|gbpjpy|audjpy|cadjpy|chfjpy|"
            r"xauusd|xagusd|btcusd|ethusd|us100|us500|us30|ger40|uk100|jp225|usoil|ukoil|"
            r"spx|s&p\s*500|ndx|nasdaq|dow\s+jones|djia|dxy|vix|nikkei|ftse|dax|wti|brent|"
            r"usd|eur|gbp|jpy|chf|aud|cad|nzd|cny|cnh|yen|dollar|euro|pound|gold|silver|bitcoin|ethereum)\b",
            re.I,
        ),
    ),
)


def find_contamination_violations(prompt: str) -> list[str]:
    """Return all anti-contamination violations found in ``prompt`` (empty list == clean)."""
    if not isinstance(prompt, str) or not prompt.strip():
        return ["EMPTY_OR_NON_STRING_PROMPT"]

    violations: list[str] = []
    for m in _ISO_DATE_RE.finditer(prompt):
        violations.append(f"ISO_DATE:{m.group(0)}")
    for m in _SLASH_DATE_RE.finditer(prompt):
        violations.append(f"SLASH_DATE:{m.group(0)}")
    for m in _MONTH_DATE_RE.finditer(prompt):
        violations.append(f"MONTH_DATE:{m.group(0)}")
    for m in _YEAR_RE.finditer(prompt):
        violations.append(f"YEAR:{m.group(0)}")
    for tag, rx in _FORBIDDEN_EVENT_PATTERNS:
        for m in rx.finditer(prompt):
            violations.append(f"{tag}:{m.group(0)}")
    for tag, rx in _FORBIDDEN_ENTITY_PATTERNS:
        for m in rx.finditer(prompt):
            violations.append(f"{tag}:{m.group(0)}")
    return violations


def assert_anonymized_prompt_clean(prompt: str) -> None:
    """Fail-closed anti-contamination guard (100% active under ``python -O``, zero bare asserts).

    Raises ``ContaminationError`` if ANY date, year (1990..2039, including 2018..2026),
    real historical event name (e.g. 'SVB', 'COVID', 'Aug 5 Yen'), or ticker/entity leaks.
    """
    violations = find_contamination_violations(prompt)
    if violations:
        raise ContaminationError(
            f"Prompt failed anti-contamination validation ({len(violations)} violation(s)): "
            + ", ".join(violations[:10])
        )


@dataclass(frozen=True)
class AnonymizedMacroScenario:
    """Single anonymized macro stress/calm benchmark scenario (zero dates/events/tickers)."""

    scenario_id: str
    category: str
    expected_regime_band: str
    expected_risk_mult_min: float
    expected_risk_mult_max: float
    day_marker: str
    metrics: dict[str, float]
    anonymized_narrative: str
    prompt_text: str
    prompt_sha256: str

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


SYSTEM_PROMPT_MACRO_SUPERVISOR: Final[str] = (
    "You are an offline advisory Macro Regime Risk Supervisor for a systematic prop-trading desk. "
    "You NEVER generate trades, directions, lot sizes, or PropGuard overrides. "
    "Given anonymized cross-asset z-scores and volatility ratios on DAY_T, output ONLY valid JSON "
    "matching this exact schema: "
    '{"risk_mult": <one of 0.0, 0.5, 0.75, 1.0>, '
    '"regime_tag": <one of "CRISIS_HALT", "HIGH_STRESS_DEFENSIVE", "CAUTION_REDUCED", "CALM_NORMAL", "NEUTRAL">, '
    '"confidence": <float 0.0..1.0>, '
    '"reasoning_bullets": [<1 to 4 concise strings>], '
    '"order_send_capable": false}. '
    "Use 0.0 for systemic/flash/contagion crisis halt, 0.5 for severe macro shock or elevated tail stress, "
    "0.75 for moderate caution/thin liquidity/divergence, and 1.0 for calm normal conditions."
)


def _format_anonymized_scenario_prompt(
    *,
    scenario_id: str,
    category: str,
    day_marker: str,
    metrics: Mapping[str, float],
    narrative: str,
) -> str:
    metric_lines = "\n".join(f"- {k}: {v:+.2f}" for k, v in metrics.items())
    prompt = (
        f"SCENARIO_ID: {scenario_id}\n"
        f"TIMESTAMP_TOKEN: {day_marker} SESSION_PRE_OPEN\n"
        f"ARCHETYPE: {category}\n"
        f"ANONYMIZED_CROSS_ASSET_TELEMETRY:\n{metric_lines}\n"
        f"STRUCTURAL_SUMMARY: {narrative}\n"
        "TASK: Classify the pre-session macro risk multiplier strictly in {0.0, 0.5, 0.75, 1.0} "
        "and return ONLY the JSON object specified in the system prompt."
    )
    assert_anonymized_prompt_clean(prompt)
    return prompt


_RAW_24_SCENARIO_SPECS: Final[tuple[dict[str, Any], ...]] = (
    # ---- Group A: 6 Crisis / Extreme Tail Stress Scenarios (expected 0.0..0.5) ----
    {
        "scenario_id": "SCEN_01",
        "category": "SURPRISE_RATE_HIKE_CARRY_UNWIND",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "ASSET_FX_B_return_sigma": -4.20,
            "ASSET_IDX_A_return_sigma": -3.85,
            "ASSET_RATE_D_yield_z": 3.90,
            "realized_vol_ratio_vs_20d": 4.10,
            "spread_multiple_vs_median": 5.50,
            "cross_asset_corr_z": 3.40,
        },
        "narrative": (
            "On DAY_T, CENTRAL_BANK_X delivered an unpriced policy-rate hike alongside balance-sheet tightening. "
            "Funding pair ASSET_FX_B gapped violently lower, triggering forced cross-margin deleveraging in "
            "ASSET_IDX_A with extreme bid-ask widening and severe order-book thinning."
        ),
    },
    {
        "scenario_id": "SCEN_02",
        "category": "INTRADAY_LIQUIDITY_VACUUM_DROP",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "ASSET_IDX_A_15m_sigma": -5.10,
            "ASSET_FX_B_return_sigma": -2.95,
            "orderbook_depth_z": -3.80,
            "realized_vol_ratio_vs_20d": 4.75,
            "spread_multiple_vs_median": 6.80,
            "gap_atr_multiple": 3.90,
        },
        "narrative": (
            "On DAY_T, ASSET_IDX_A suffered a rapid multi-sigma air-pocket drop during thin handover liquidity "
            "with market-maker quotes withdrawing across correlated benchmarks and spreads expanding over sixfold."
        ),
    },
    {
        "scenario_id": "SCEN_03",
        "category": "BANKING_LIQUIDITY_CONTAGION",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "BANK_SECTOR_E_return_sigma": -4.60,
            "interbank_funding_spread_z": 4.40,
            "ASSET_RATE_D_front_end_sigma": -3.70,
            "ASSET_IDX_A_return_sigma": -3.10,
            "realized_vol_ratio_vs_20d": 3.65,
            "spread_multiple_vs_median": 4.20,
        },
        "narrative": (
            "On DAY_T, multiple mid-tier institutions in BANK_SECTOR_E experienced acute deposit outflows and "
            "emergency liquidity backstop rumors; front-end rates repriced sharply lower while credit stress surged."
        ),
    },
    {
        "scenario_id": "SCEN_04",
        "category": "GEOPOLITICAL_ENERGY_SUPPLY_SHOCK",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "ASSET_COMMOD_C_return_sigma": 4.80,
            "ASSET_IDX_A_return_sigma": -3.40,
            "ASSET_FX_B_return_sigma": -2.65,
            "gap_atr_multiple": 3.60,
            "realized_vol_ratio_vs_20d": 3.85,
            "spread_multiple_vs_median": 4.90,
        },
        "narrative": (
            "On DAY_T, a sudden maritime chokepoint disruption halted primary energy transit routes. "
            "ASSET_COMMOD_C gapped sharply higher at SESSION_OPEN while risk indices and cyclical FX repriced "
            "into stagflationary stress with unstable quote feeds."
        ),
    },
    {
        "scenario_id": "SCEN_05",
        "category": "SOVEREIGN_BOND_AUCTION_DISLOCATION",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "ASSET_RATE_D_long_yield_sigma": 4.30,
            "ASSET_FX_B_return_sigma": -3.50,
            "pension_collateral_stress_z": 3.80,
            "realized_vol_ratio_vs_20d": 3.70,
            "spread_multiple_vs_median": 4.40,
            "cross_asset_corr_z": 3.10,
        },
        "narrative": (
            "On DAY_T, an unfunded fiscal expansion triggered a disorderly sovereign debt sell-off and collateral "
            "margin calls across levered liability-driven funds; CENTRAL_BANK_Y liquidity intervention is unconfirmed."
        ),
    },
    {
        "scenario_id": "SCEN_06",
        "category": "SYNCHRONIZED_GLOBAL_ACTIVITY_FREEZE",
        "expected_regime_band": "CRISIS_OR_DEFENSIVE",
        "expected_risk_mult_min": 0.0,
        "expected_risk_mult_max": 0.5,
        "metrics": {
            "ASSET_IDX_A_return_sigma": -4.90,
            "ASSET_COMMOD_C_return_sigma": -4.50,
            "funding_liquidity_z": -4.30,
            "realized_vol_ratio_vs_20d": 4.60,
            "spread_multiple_vs_median": 6.10,
            "cross_asset_corr_z": 4.00,
        },
        "narrative": (
            "On DAY_T, synchronized cross-border transport halts and emergency mobility restrictions triggered "
            "dash-for-cash liquidation across ASSET_IDX_A, ASSET_COMMOD_C, and safe-haven proxies simultaneously."
        ),
    },
    # ---- Group B: 6 Moderate / Elevated Caution Scenarios (expected 0.5..0.75) ----
    {
        "scenario_id": "SCEN_07",
        "category": "HOT_INFLATION_SURPRISE_SHOCK",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "macro_inflation_surprise_z": 2.45,
            "ASSET_RATE_D_front_end_sigma": 2.15,
            "ASSET_IDX_A_return_sigma": -1.85,
            "realized_vol_ratio_vs_20d": 2.10,
            "spread_multiple_vs_median": 2.25,
            "orderbook_depth_z": -1.60,
        },
        "narrative": (
            "On DAY_T, core consumer price momentum printed more than two standard deviations above consensus, "
            "pushing front-end policy expectations sharply higher while keeping market plumbing intact."
        ),
    },
    {
        "scenario_id": "SCEN_08",
        "category": "CENTRAL_BANK_POLICY_DIVERGENCE",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "rate_differential_shift_z": 2.30,
            "ASSET_FX_B_return_sigma": 2.05,
            "implied_vol_skew_z": 1.95,
            "realized_vol_ratio_vs_20d": 1.85,
            "spread_multiple_vs_median": 1.75,
            "cross_asset_corr_z": 1.20,
        },
        "narrative": (
            "On DAY_T, CENTRAL_BANK_X signaled higher-for-longer restraint while CENTRAL_BANK_Y unexpectedly "
            "guided toward earlier easing, widening yield differentials and driving brisk FX repricing."
        ),
    },
    {
        "scenario_id": "SCEN_09",
        "category": "HOLIDAY_THIN_LIQUIDITY_REBALANCE",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "market_volume_z": -2.40,
            "orderbook_depth_z": -2.25,
            "spread_multiple_vs_median": 2.60,
            "realized_vol_ratio_vs_20d": 1.35,
            "ASSET_FX_B_return_sigma": 0.90,
            "whipsaw_wick_ratio": 2.30,
        },
        "narrative": (
            "On DAY_T, major regional banking centers are closed for a national holiday overlapping quarter-end "
            "fixing flows; spreads are elevated with stop-run wicks despite absent fundamental catalysts."
        ),
    },
    {
        "scenario_id": "SCEN_10",
        "category": "GROWTH_PAYROLL_MISS_RISK_OFF",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "macro_labor_surprise_z": -2.20,
            "ASSET_IDX_A_return_sigma": -1.90,
            "ASSET_RATE_D_front_end_sigma": -1.85,
            "realized_vol_ratio_vs_20d": 1.95,
            "spread_multiple_vs_median": 2.05,
            "safe_haven_bid_sigma": 1.90,
        },
        "narrative": (
            "On DAY_T, aggregate employment creation missed consensus sharply with downward prior revisions, "
            "sparking growth-scare rotation out of cyclical indices into duration without credit breakdown."
        ),
    },
    {
        "scenario_id": "SCEN_11",
        "category": "TERM_PREMIUM_SUPPLY_STEEPENING",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "ASSET_RATE_D_long_yield_sigma": 2.30,
            "yield_curve_slope_z": 2.10,
            "ASSET_IDX_A_return_sigma": -1.60,
            "realized_vol_ratio_vs_20d": 1.90,
            "spread_multiple_vs_median": 1.70,
            "orderbook_depth_z": -1.35,
        },
        "narrative": (
            "On DAY_T, heavier-than-expected sovereign issuance schedules lifted long-end term premia above "
            "two sigma, pressuring duration-sensitive equity indices while FX liquidity stayed orderly."
        ),
    },
    {
        "scenario_id": "SCEN_12",
        "category": "CONTAINED_COMMODITY_SUPPLY_DISRUPTION",
        "expected_regime_band": "ELEVATED_CAUTION",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 0.75,
        "metrics": {
            "ASSET_COMMOD_C_return_sigma": 2.60,
            "ASSET_IDX_A_return_sigma": -1.15,
            "ASSET_FX_B_return_sigma": -1.25,
            "realized_vol_ratio_vs_20d": 1.75,
            "spread_multiple_vs_median": 1.85,
            "cross_asset_corr_z": 1.30,
        },
        "narrative": (
            "On DAY_T, an unplanned refinery outage lifted ASSET_COMMOD_C more than two sigma; spillover into "
            "major equity and FX benchmarks remained contained with moderate spread widening."
        ),
    },
    # ---- Group C: 6 Transitional / Watch Scenarios (expected 0.5..1.0) ----
    {
        "scenario_id": "SCEN_13",
        "category": "POST_SHOCK_VOLATILITY_DECAY",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "realized_vol_ratio_vs_20d": 1.50,
            "vol_change_vs_T_minus_2": -1.70,
            "spread_multiple_vs_median": 1.30,
            "orderbook_depth_z": -0.60,
            "ASSET_IDX_A_return_sigma": 0.85,
            "cross_asset_corr_z": 0.90,
        },
        "narrative": (
            "On DAY_T, three sessions after an earlier volatility spike, realized volatility has retraced half "
            "its expansion and liquidity depth is recovering, though aftershock headline risk persists."
        ),
    },
    {
        "scenario_id": "SCEN_14",
        "category": "PRE_SCHEDULED_RATE_DECISION_WAIT",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "implied_vol_ratio_vs_20d": 1.60,
            "realized_vol_ratio_vs_20d": 0.90,
            "spread_multiple_vs_median": 1.15,
            "ASSET_FX_B_return_sigma": 0.25,
            "orderbook_depth_z": -0.45,
            "scheduled_event_risk_z": 1.80,
        },
        "narrative": (
            "On DAY_T, CENTRAL_BANK_X announces its scheduled rate decision later in the session. "
            "Short-dated implied volatility is elevated while realized intraday movement remains compressed."
        ),
    },
    {
        "scenario_id": "SCEN_15",
        "category": "MIXED_CONFLICTING_MACRO_PRINTS",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "macro_labor_surprise_z": 1.15,
            "macro_pmi_surprise_z": -1.25,
            "ASSET_IDX_A_return_sigma": -0.35,
            "ASSET_FX_B_return_sigma": 0.45,
            "realized_vol_ratio_vs_20d": 1.20,
            "spread_multiple_vs_median": 1.20,
        },
        "narrative": (
            "On DAY_T, resilient services employment conflicted with soft manufacturing new orders, producing "
            "two-way intraday chop across rates and currencies without systemic liquidity deterioration."
        ),
    },
    {
        "scenario_id": "SCEN_16",
        "category": "OFFICIAL_FX_INTERVENTION_WATCH_ZONE",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "ASSET_FX_B_multi_quarter_z": 2.35,
            "implied_vol_skew_z": 2.10,
            "realized_vol_ratio_vs_20d": 1.40,
            "spread_multiple_vs_median": 1.45,
            "verbal_warning_intensity_z": 2.00,
            "orderbook_depth_z": -0.95,
        },
        "narrative": (
            "On DAY_T, ASSET_FX_B approaches multi-quarter extremes amid heightened verbal warnings from finance "
            "officials regarding one-sided depreciation, elevating asymmetric reversal risk."
        ),
    },
    {
        "scenario_id": "SCEN_17",
        "category": "LOCALIZED_SOVEREIGN_OUTLOOK_REVISION",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "local_sovereign_spread_z": 1.70,
            "ASSET_IDX_A_return_sigma": -0.55,
            "global_vol_ratio_vs_20d": 1.10,
            "spread_multiple_vs_median": 1.15,
            "cross_asset_corr_z": 0.65,
            "orderbook_depth_z": -0.30,
        },
        "narrative": (
            "On DAY_T, a rating agency revised a single sovereign fiscal outlook to negative; local yields "
            "widened modestly while broad international benchmarks absorbed the news calmly."
        ),
    },
    {
        "scenario_id": "SCEN_18",
        "category": "ENERGY_INVENTORY_DRAW_MUTED_FX",
        "expected_regime_band": "TRANSITIONAL_WATCH",
        "expected_risk_mult_min": 0.5,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "ASSET_COMMOD_C_return_sigma": 1.80,
            "ASSET_FX_B_return_sigma": 0.40,
            "ASSET_IDX_A_return_sigma": 0.15,
            "realized_vol_ratio_vs_20d": 1.15,
            "spread_multiple_vs_median": 1.10,
            "orderbook_depth_z": 0.10,
        },
        "narrative": (
            "On DAY_T, weekly energy stockpiles fell more than forecast, driving a localized rally in "
            "ASSET_COMMOD_C while equity and currency volatility stayed near seasonal averages."
        ),
    },
    # ---- Group D: 6 Calm / Constructive Normal Scenarios (expected 0.75..1.0) ----
    {
        "scenario_id": "SCEN_19",
        "category": "CALM_MEAN_REVERTING_RANGE",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "ASSET_IDX_A_return_sigma": 0.20,
            "ASSET_FX_B_return_sigma": -0.15,
            "realized_vol_ratio_vs_20d": 0.80,
            "spread_multiple_vs_median": 0.95,
            "orderbook_depth_z": 0.75,
            "cross_asset_corr_z": -0.30,
        },
        "narrative": (
            "On DAY_T, global sessions trade in balanced two-sided ranges with tight spreads, deep order books, "
            "low cross-asset correlation, and zero high-impact macro catalysts on the calendar."
        ),
    },
    {
        "scenario_id": "SCEN_20",
        "category": "BENIGN_INLINE_INFLATION_STEADY_GROWTH",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "macro_inflation_surprise_z": 0.10,
            "ASSET_RATE_D_front_end_sigma": 0.15,
            "ASSET_IDX_A_return_sigma": 0.45,
            "realized_vol_ratio_vs_20d": 0.85,
            "spread_multiple_vs_median": 0.98,
            "orderbook_depth_z": 0.60,
        },
        "narrative": (
            "On DAY_T, headline and core inflation matched consensus exactly alongside steady activity surveys, "
            "leaving rate expectations anchored and liquidity conditions healthy across all sleeves."
        ),
    },
    {
        "scenario_id": "SCEN_21",
        "category": "ORDERLY_LOW_VOL_TREND_CONTINUATION",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "ASSET_IDX_A_return_sigma": 0.70,
            "ASSET_FX_B_return_sigma": 0.55,
            "realized_vol_ratio_vs_20d": 0.90,
            "spread_multiple_vs_median": 0.95,
            "orderbook_depth_z": 0.50,
            "cross_asset_corr_z": 0.18,
        },
        "narrative": (
            "On DAY_T, multi-week directional trends persist smoothly without opening gaps or leverage stress; "
            "realized volatility sits modestly below its twenty-day baseline."
        ),
    },
    {
        "scenario_id": "SCEN_22",
        "category": "TELEGRAPHED_CENTRAL_BANK_HOLD",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "ASSET_RATE_D_front_end_sigma": 0.20,
            "ASSET_FX_B_return_sigma": 0.10,
            "realized_vol_ratio_vs_20d": 0.88,
            "spread_multiple_vs_median": 1.00,
            "orderbook_depth_z": 0.40,
            "policy_surprise_z": 0.05,
        },
        "narrative": (
            "On DAY_T, CENTRAL_BANK_X held policy rates unchanged with balanced data-dependent language matching "
            "prior communications; implied volatility normalized immediately after the statement."
        ),
    },
    {
        "scenario_id": "SCEN_23",
        "category": "MIDWEEK_NORMAL_LIQUIDITY_SESSION",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "market_volume_z": 0.15,
            "orderbook_depth_z": 0.55,
            "spread_multiple_vs_median": 0.92,
            "realized_vol_ratio_vs_20d": 0.85,
            "ASSET_IDX_A_return_sigma": 0.30,
            "ASSET_COMMOD_C_return_sigma": -0.20,
        },
        "narrative": (
            "On DAY_T, mid-week turnover is evenly distributed across major trading hubs with sub-median spreads, "
            "orderly price discovery, and no unscheduled macro headlines."
        ),
    },
    {
        "scenario_id": "SCEN_24",
        "category": "QUIET_CALENDAR_VOL_COMPRESSION",
        "expected_regime_band": "CALM_NORMAL",
        "expected_risk_mult_min": 0.75,
        "expected_risk_mult_max": 1.0,
        "metrics": {
            "realized_vol_ratio_vs_20d": 0.72,
            "implied_vol_ratio_vs_20d": 0.78,
            "spread_multiple_vs_median": 0.90,
            "orderbook_depth_z": 0.80,
            "ASSET_FX_B_return_sigma": 0.12,
            "cross_asset_corr_z": -0.25,
        },
        "narrative": (
            "On DAY_T, a light data calendar and steady corporate guidance keep cross-asset realized and implied "
            "volatility near cyclical lows with deep two-way liquidity."
        ),
    },
)


def build_anonymized_24_macro_scenarios() -> list[AnonymizedMacroScenario]:
    """Build 24 strictly anonymized macro stress & calm scenarios (verified clean fail-closed)."""
    _enforce_module_safety_invariants()
    if len(_RAW_24_SCENARIO_SPECS) != 24:
        raise SupervisorValidationError(f"Expected exactly 24 macro scenarios, got {len(_RAW_24_SCENARIO_SPECS)}")

    scenarios: list[AnonymizedMacroScenario] = []
    seen_ids: set[str] = set()
    for spec in _RAW_24_SCENARIO_SPECS:
        sid = str(spec["scenario_id"])
        if sid in seen_ids:
            raise SupervisorValidationError(f"Duplicate scenario_id: {sid}")
        seen_ids.add(sid)

        metrics = {str(k): round(float(v), 4) for k, v in spec["metrics"].items()}
        narrative = str(spec["narrative"])
        prompt_text = _format_anonymized_scenario_prompt(
            scenario_id=sid,
            category=str(spec["category"]),
            day_marker="DAY_T",
            metrics=metrics,
            narrative=narrative,
        )
        # Double-check both system prompt and user prompt are strictly clean
        assert_anonymized_prompt_clean(SYSTEM_PROMPT_MACRO_SUPERVISOR)
        assert_anonymized_prompt_clean(prompt_text)

        scenarios.append(
            AnonymizedMacroScenario(
                scenario_id=sid,
                category=str(spec["category"]),
                expected_regime_band=str(spec["expected_regime_band"]),
                expected_risk_mult_min=float(spec["expected_risk_mult_min"]),
                expected_risk_mult_max=float(spec["expected_risk_mult_max"]),
                day_marker="DAY_T",
                metrics=metrics,
                anonymized_narrative=narrative,
                prompt_text=prompt_text,
                prompt_sha256=_sha256_text(f"{SYSTEM_PROMPT_MACRO_SUPERVISOR}\n---\n{prompt_text}"),
            )
        )
    return scenarios


# ==============================================================================
# Official API Monthly Budget Enforcer (<= 5.00 USD/month, Radar-Backed)
# ==============================================================================


@dataclass(frozen=True)
class ModelPricingEntry:
    """Validated per-1M token pricing and projected monthly spend from AI Model Radar."""

    model_id: str
    prompt_usd_per_1m: float
    completion_usd_per_1m: float
    monthly_supervisor_usd: float
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE
    source: str = "ai_model_radar_latest.json"

    def estimate_call_usd(
        self,
        *,
        input_tokens: int = SUPERVISOR_AVG_INPUT_TOKENS_PER_RUN,
        output_tokens: int = SUPERVISOR_AVG_OUTPUT_TOKENS_PER_RUN,
    ) -> float:
        in_tok = _require_strict_int(input_tokens, field_name="input_tokens", min_value=0)
        out_tok = _require_strict_int(output_tokens, field_name="output_tokens", min_value=0)
        cost = (in_tok * self.prompt_usd_per_1m / 1_000_000.0) + (out_tok * self.completion_usd_per_1m / 1_000_000.0)
        if not math.isfinite(cost) or cost < 0.0:
            raise BudgetExceededError(f"Invalid computed per-call cost: {cost!r}")
        return round(cost, 8)


def load_radar_pricing_catalog(
    radar_snapshot_path: Path | str | None = None,
    *,
    radar_payload: Mapping[str, Any] | None = None,
) -> tuple[dict[str, ModelPricingEntry], float]:
    """Load validated model pricing index from ``ai_model_radar_latest.json`` (or an in-memory dict)."""
    payload: Mapping[str, Any]
    source_label: str
    if radar_payload is not None:
        payload = radar_payload
        source_label = "in_memory_radar_payload"
    else:
        path = Path(radar_snapshot_path) if radar_snapshot_path is not None else DEFAULT_RADAR_SNAPSHOT_PATH
        if not path.is_file():
            raise FileNotFoundError(f"AI Model Radar snapshot not found: {path}")
        raw = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(raw, Mapping):
            raise BudgetExceededError(f"Malformed AI Model Radar JSON root: {path}")
        payload = raw
        source_label = path.name

    wa = payload.get("workload_assumptions")
    usd_vnd = DEFAULT_USD_VND_RATE
    if isinstance(wa, Mapping) and "usd_vnd_rate" in wa:
        usd_vnd = _require_finite_float(wa["usd_vnd_rate"], field_name="usd_vnd_rate", strictly_positive=True)

    entries: dict[str, ModelPricingEntry] = {}

    def _register(model_id: str, item: Mapping[str, Any]) -> None:
        p_in = _require_finite_float(
            item.get("prompt_usd_per_1m"), field_name=f"{model_id}.prompt_usd_per_1m", min_value=0.0
        )
        p_out = _require_finite_float(
            item.get("completion_usd_per_1m"), field_name=f"{model_id}.completion_usd_per_1m", min_value=0.0
        )
        raw_monthly = item.get("monthly_supervisor_usd", item.get("monthly_usd"))
        if raw_monthly is not None:
            monthly = _require_finite_float(raw_monthly, field_name=f"{model_id}.monthly_supervisor_usd", min_value=0.0)
        else:
            monthly = round((0.35 * p_in) + (0.07 * p_out), 6)
        entries[model_id] = ModelPricingEntry(
            model_id=model_id,
            prompt_usd_per_1m=p_in,
            completion_usd_per_1m=p_out,
            monthly_supervisor_usd=monthly,
            usd_vnd_rate=usd_vnd,
            source=source_label,
        )

    catalog_index = payload.get("catalog_index")
    if isinstance(catalog_index, Mapping):
        for mid, rec in catalog_index.items():
            if isinstance(rec, Mapping):
                _register(str(mid), rec)

    leaderboards = payload.get("leaderboards")
    if isinstance(leaderboards, Mapping):
        for lb_rows in leaderboards.values():
            if not isinstance(lb_rows, list):
                continue
            for row in lb_rows:
                if isinstance(row, Mapping) and isinstance(row.get("id"), str):
                    mid = row["id"]
                    if mid not in entries and "prompt_usd_per_1m" in row and "completion_usd_per_1m" in row:
                        _register(mid, row)

    return entries, usd_vnd


class OfficialApiBudgetEnforcer:
    """Hard monthly spend gate (<= 5.00 USD/month) for ``OFFICIAL_API_PRODUCTION``."""

    def __init__(
        self,
        *,
        monthly_cap_usd: float = MAX_OFFICIAL_API_USD_PER_MONTH,
        radar_snapshot_path: Path | str | None = None,
        radar_payload: Mapping[str, Any] | None = None,
        mtd_spend_usd: float = 0.0,
        enforce_monthly_runrate_cap: bool = True,
        fallback_pricing: Mapping[str, ModelPricingEntry] | None = None,
    ) -> None:
        _enforce_module_safety_invariants()
        cap = _require_finite_float(monthly_cap_usd, field_name="monthly_cap_usd", strictly_positive=True)
        if cap > MAX_OFFICIAL_API_USD_PER_MONTH + 1e-12:
            raise BudgetExceededError(
                f"Configured monthly_cap_usd ({cap:.4f}) exceeds hard workspace ceiling "
                f"({MAX_OFFICIAL_API_USD_PER_MONTH:.2f} USD/month)."
            )
        self.monthly_cap_usd: float = cap
        self.mtd_spend_usd: float = _require_finite_float(mtd_spend_usd, field_name="mtd_spend_usd", min_value=0.0)
        self.enforce_monthly_runrate_cap: bool = bool(enforce_monthly_runrate_cap)
        self.usd_vnd_rate: float = DEFAULT_USD_VND_RATE
        self.catalog: dict[str, ModelPricingEntry] = {}

        if radar_payload is not None:
            self.catalog, self.usd_vnd_rate = load_radar_pricing_catalog(radar_payload=radar_payload)
        elif radar_snapshot_path is not None:
            self.catalog, self.usd_vnd_rate = load_radar_pricing_catalog(radar_snapshot_path=radar_snapshot_path)
        elif DEFAULT_RADAR_SNAPSHOT_PATH.is_file():
            self.catalog, self.usd_vnd_rate = load_radar_pricing_catalog(
                radar_snapshot_path=DEFAULT_RADAR_SNAPSHOT_PATH
            )

        if fallback_pricing:
            for k, v in fallback_pricing.items():
                self.catalog.setdefault(k, v)

    def resolve_pricing(self, model_id: str) -> ModelPricingEntry:
        """Resolve exact model pricing from AI Model Radar catalog; fail closed if unknown."""
        key = model_id.strip()
        if key in self.catalog:
            return self.catalog[key]
        # Allow unambiguous suffix match if caller omits provider prefix (e.g. 'qwen3.7-flash')
        suffix_matches = [entry for mid, entry in self.catalog.items() if mid.endswith(f"/{key}")]
        if len(suffix_matches) == 1:
            return suffix_matches[0]
        raise BudgetExceededError(
            f"Unknown model pricing for {model_id!r} in AI Model Radar catalog; refusing unpriced official API call."
        )

    def check_and_quote(
        self,
        model_id: str,
        *,
        estimated_input_tokens: int = SUPERVISOR_AVG_INPUT_TOKENS_PER_RUN,
        estimated_output_tokens: int = SUPERVISOR_AVG_OUTPUT_TOKENS_PER_RUN,
        projected_monthly_runs: int = SUPERVISOR_RUNS_PER_MONTH,
    ) -> dict[str, Any]:
        """Verify spend stays <= 5.00 USD/month before ANY network call; raises BudgetExceededError if over cap."""
        pricing = self.resolve_pricing(model_id)
        runs = _require_strict_int(projected_monthly_runs, field_name="projected_monthly_runs", min_value=1)
        call_usd = pricing.estimate_call_usd(
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
        )
        mtd_after_call_usd = round(self.mtd_spend_usd + call_usd, 8)
        runrate_monthly_usd = round(max(pricing.monthly_supervisor_usd, call_usd * runs), 6)
        effective_runrate = runrate_monthly_usd if self.enforce_monthly_runrate_cap else 0.0
        projected_monthly_usd = round(max(mtd_after_call_usd, effective_runrate), 6)

        if mtd_after_call_usd > self.monthly_cap_usd + 1e-12:
            raise BudgetExceededError(
                f"OFFICIAL_API_BUDGET_EXCEEDED: mtd_after_call=${mtd_after_call_usd:.4f} > "
                f"cap=${self.monthly_cap_usd:.2f}/month for model {model_id!r}"
            )
        if self.enforce_monthly_runrate_cap and projected_monthly_usd > self.monthly_cap_usd + 1e-12:
            raise BudgetExceededError(
                f"OFFICIAL_API_PROJECTED_MONTHLY_EXCEEDED: projected=${projected_monthly_usd:.4f}/mo > "
                f"cap=${self.monthly_cap_usd:.2f}/month for model {model_id!r}"
            )

        return {
            "model_id": pricing.model_id,
            "estimated_call_usd": call_usd,
            "mtd_spend_before_usd": round(self.mtd_spend_usd, 6),
            "mtd_spend_after_usd": mtd_after_call_usd,
            "projected_monthly_usd": projected_monthly_usd,
            "projected_monthly_vnd": int(round(projected_monthly_usd * self.usd_vnd_rate)),
            "monthly_cap_usd": self.monthly_cap_usd,
            "monthly_cap_vnd": int(round(self.monthly_cap_usd * self.usd_vnd_rate)),
            "within_budget": True,
            "pricing_source": pricing.source,
        }

    def record_spend(self, cost_usd: float) -> float:
        amt = _require_finite_float(cost_usd, field_name="cost_usd", min_value=0.0)
        new_total = round(self.mtd_spend_usd + amt, 8)
        if new_total > self.monthly_cap_usd + 1e-12:
            raise BudgetExceededError(
                f"Post-call spend ${new_total:.4f} exceeded hard monthly cap ${self.monthly_cap_usd:.2f}"
            )
        self.mtd_spend_usd = new_total
        return self.mtd_spend_usd


# ==============================================================================
# Unified Macro AI Supervisor (3 Provider Modes Behind 1-Line Switch)
# ==============================================================================


@dataclass(frozen=True)
class MacroSupervisorConfig:
    """Configuration for ``MacroAISupervisor`` with a 1-line ``provider_mode`` switch."""

    provider_mode: ProviderMode = ProviderMode.OFFICIAL_API_PRODUCTION
    model_id: str = "qwen/qwen3.7-flash"
    # Mode 1: CLIPROXY_LOCAL_17852
    gateway_owner_path: Path | str | None = None
    sanitized_gateway_yaml_path: Path | str | None = None
    cliproxy_expected_port: int = DEFAULT_PROJECT_CLIPROXY_PORT
    cliproxy_request_retry: int = 0
    cliproxy_api_key: str | None = None
    # Mode 2: OFFICIAL_API_PRODUCTION
    official_vendor: str = "openrouter"
    official_api_key: str | None = None
    monthly_budget_cap_usd: float = MAX_OFFICIAL_API_USD_PER_MONTH
    radar_snapshot_path: Path | str | None = None
    # Mode 3: LOCAL_OLLAMA_ADVISORY
    ollama_base_url: str = DEFAULT_OLLAMA_BASE_URL
    # Shared HTTP settings
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC

    def __post_init__(self) -> None:
        _enforce_module_safety_invariants()
        if not isinstance(self.provider_mode, ProviderMode):
            try:
                object.__setattr__(self, "provider_mode", ProviderMode(str(self.provider_mode)))
            except ValueError as exc:
                raise SupervisorValidationError(f"Unknown provider_mode: {self.provider_mode!r}") from exc
        assert_port_allowed(self.cliproxy_expected_port, field_name="cliproxy_expected_port")
        if self.cliproxy_request_retry != 0:
            raise SupervisorValidationError(
                f"CLIPROXY_LOCAL_17852 strictly requires request_retry == 0, got {self.cliproxy_request_retry!r}"
            )
        if self.official_vendor not in OFFICIAL_API_ENDPOINTS:
            allowed_vendors = sorted(OFFICIAL_API_ENDPOINTS)
            raise SupervisorValidationError(
                f"Unsupported official_vendor {self.official_vendor!r}; expected one of {allowed_vendors}"
            )
        cap = _require_finite_float(
            self.monthly_budget_cap_usd, field_name="monthly_budget_cap_usd", strictly_positive=True
        )
        if cap > MAX_OFFICIAL_API_USD_PER_MONTH + 1e-12:
            raise BudgetExceededError(
                f"monthly_budget_cap_usd ({cap}) cannot exceed {MAX_OFFICIAL_API_USD_PER_MONTH:.2f} USD/month"
            )
        assert_url_allowed(self.ollama_base_url, require_loopback=True)
        _require_finite_float(self.timeout_sec, field_name="timeout_sec", strictly_positive=True)


class MacroAISupervisor:
    """Fail-closed Macro AI Supervisor orchestrating all 3 provider modes behind a 1-line switch."""

    def __init__(
        self,
        config: MacroSupervisorConfig | None = None,
        *,
        provider_mode: ProviderMode | str | None = None,
        model_id: str | None = None,
        http_client: httpx.Client | None = None,
        budget_enforcer: OfficialApiBudgetEnforcer | None = None,
        radar_payload: Mapping[str, Any] | None = None,
    ) -> None:
        _enforce_module_safety_invariants()
        if config is None:
            mode = ProviderMode(provider_mode) if provider_mode is not None else ProviderMode.OFFICIAL_API_PRODUCTION
            default_model = "qwen3:8b" if mode == ProviderMode.LOCAL_OLLAMA_ADVISORY else "qwen/qwen3.7-flash"
            config = MacroSupervisorConfig(
                provider_mode=mode,
                model_id=model_id or default_model,
            )
        elif provider_mode is not None or model_id is not None:
            mode = ProviderMode(provider_mode) if provider_mode is not None else config.provider_mode
            config = MacroSupervisorConfig(
                provider_mode=mode,
                model_id=model_id or config.model_id,
                gateway_owner_path=config.gateway_owner_path,
                sanitized_gateway_yaml_path=config.sanitized_gateway_yaml_path,
                cliproxy_expected_port=config.cliproxy_expected_port,
                cliproxy_request_retry=config.cliproxy_request_retry,
                cliproxy_api_key=config.cliproxy_api_key,
                official_vendor=config.official_vendor,
                official_api_key=config.official_api_key,
                monthly_budget_cap_usd=config.monthly_budget_cap_usd,
                radar_snapshot_path=config.radar_snapshot_path,
                ollama_base_url=config.ollama_base_url,
                timeout_sec=config.timeout_sec,
            )

        self.config: MacroSupervisorConfig = config
        self._http_client: httpx.Client | None = http_client
        self._budget_enforcer: OfficialApiBudgetEnforcer | None = budget_enforcer
        self._radar_payload: Mapping[str, Any] | None = radar_payload

    def _get_budget_enforcer(self) -> OfficialApiBudgetEnforcer:
        if self._budget_enforcer is None:
            self._budget_enforcer = OfficialApiBudgetEnforcer(
                monthly_cap_usd=self.config.monthly_budget_cap_usd,
                radar_snapshot_path=self.config.radar_snapshot_path,
                radar_payload=self._radar_payload,
            )
        return self._budget_enforcer

    def evaluate_scenario(
        self,
        scenario: AnonymizedMacroScenario,
        *,
        estimated_input_tokens: int = SUPERVISOR_AVG_INPUT_TOKENS_PER_RUN,
        estimated_output_tokens: int = SUPERVISOR_AVG_OUTPUT_TOKENS_PER_RUN,
    ) -> MacroSupervisorDecision:
        """Evaluate an anonymized scenario using the configured provider mode."""
        return self.evaluate_prompt(
            prompt_text=scenario.prompt_text,
            scenario_id=scenario.scenario_id,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
        )

    def evaluate_prompt(
        self,
        prompt_text: str,
        *,
        scenario_id: str = "AD_HOC",
        estimated_input_tokens: int = SUPERVISOR_AVG_INPUT_TOKENS_PER_RUN,
        estimated_output_tokens: int = SUPERVISOR_AVG_OUTPUT_TOKENS_PER_RUN,
    ) -> MacroSupervisorDecision:
        """Evaluate an anonymized prompt after strict anti-contamination verification."""
        _enforce_module_safety_invariants()
        assert_anonymized_prompt_clean(SYSTEM_PROMPT_MACRO_SUPERVISOR)
        assert_anonymized_prompt_clean(prompt_text)
        prompt_sha = _sha256_text(f"{SYSTEM_PROMPT_MACRO_SUPERVISOR}\n---\n{prompt_text}")

        mode = self.config.provider_mode
        if mode == ProviderMode.CLIPROXY_LOCAL_17852:
            return self._call_cliproxy_local_17852(
                prompt_text=prompt_text,
                scenario_id=scenario_id,
                prompt_sha256=prompt_sha,
            )
        if mode == ProviderMode.OFFICIAL_API_PRODUCTION:
            return self._call_official_api_production(
                prompt_text=prompt_text,
                scenario_id=scenario_id,
                prompt_sha256=prompt_sha,
                estimated_input_tokens=estimated_input_tokens,
                estimated_output_tokens=estimated_output_tokens,
            )
        if mode == ProviderMode.LOCAL_OLLAMA_ADVISORY:
            return self._call_local_ollama_advisory(
                prompt_text=prompt_text,
                scenario_id=scenario_id,
                prompt_sha256=prompt_sha,
            )
        raise SupervisorValidationError(f"Unsupported provider_mode: {mode!r}")

    def _resolve_cliproxy_bearer_key(self, owner: GatewayOwnerConfig) -> str | None:
        if self.config.cliproxy_api_key:
            return self.config.cliproxy_api_key.strip()
        for candidate in (self.config.sanitized_gateway_yaml_path, owner.config_path):
            if candidate is None:
                continue
            p = Path(candidate)
            if p.is_file():
                try:
                    parsed = yaml.safe_load(p.read_text(encoding="utf-8"))
                    if isinstance(parsed, Mapping):
                        key = extract_loopback_client_api_key(parsed)
                        if key:
                            return key
                except (OSError, yaml.YAMLError):
                    continue
        return None

    def _extract_chat_content(self, payload: Mapping[str, Any], *, wire_format: str) -> str:
        if wire_format == "anthropic_messages":
            blocks = payload.get("content")
            if isinstance(blocks, list):
                texts = [str(b.get("text", "")) for b in blocks if isinstance(b, Mapping) and b.get("type") == "text"]
                joined = "\n".join(t for t in texts if t.strip())
                if joined:
                    return joined
            raise SupervisorValidationError("Anthropic response missing text content blocks")

        if wire_format == "ollama_chat":
            msg = payload.get("message")
            if isinstance(msg, Mapping) and isinstance(msg.get("content"), str):
                return msg["content"]
            # Also tolerate OpenAI-compatible Ollama response
        choices = payload.get("choices")
        if isinstance(choices, list) and choices:
            first = choices[0]
            if isinstance(first, Mapping):
                msg = first.get("message")
                if isinstance(msg, Mapping) and isinstance(msg.get("content"), str):
                    return msg["content"]
        raise SupervisorValidationError(f"Missing assistant message content in {wire_format} response")

    def _call_cliproxy_local_17852(
        self,
        *,
        prompt_text: str,
        scenario_id: str,
        prompt_sha256: str,
    ) -> MacroSupervisorDecision:
        owner = resolve_project_gateway_owner(
            self.config.gateway_owner_path,
            expected_port=self.config.cliproxy_expected_port,
        )
        url = assert_url_allowed(owner.chat_completions_url, require_loopback=True)

        headers: dict[str, str] = {"Content-Type": "application/json", "Accept": "application/json"}
        bearer = self._resolve_cliproxy_bearer_key(owner)
        if bearer:
            headers["Authorization"] = f"Bearer {bearer}"

        body = {
            "model": self.config.model_id,
            "temperature": 0.0,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_MACRO_SUPERVISOR},
                {"role": "user", "content": prompt_text},
            ],
        }

        own_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self.config.timeout_sec, follow_redirects=False)
        t0 = time.perf_counter()
        try:
            # STRICT request_retry = 0 -> EXACTLY ONE attempt, zero retry loops!
            try:
                resp = client.post(url, headers=headers, json=body, timeout=self.config.timeout_sec)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    status=STATUS_SKIP_OFFLINE,
                    reason=f"Loopback gateway {owner.port} unreachable: {type(exc).__name__}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            if resp.status_code == 429:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    status=STATUS_RATE_LIMITED_STOP,
                    reason="HTTP 429 rate-limited on loopback gateway (request_retry=0; stopping immediately).",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
            if resp.status_code in (401, 403):
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    status=STATUS_SKIP_AUTH_EXPIRED,
                    reason=f"HTTP {resp.status_code} OAuth/auth expired on loopback gateway (request_retry=0).",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
            if resp.status_code != 200:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"HTTP {resp.status_code} from loopback gateway (request_retry=0).",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            try:
                payload = resp.json()
                if not isinstance(payload, Mapping):
                    raise SupervisorValidationError("Gateway JSON response root is not an object")
                content = self._extract_chat_content(payload, wire_format="openai_chat")
                return parse_supervisor_decision_json(
                    content,
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                    estimated_cost_usd=0.0,
                )
            except (ValueError, SupervisorValidationError) as exc:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"Invalid gateway response schema: {exc}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
        finally:
            if own_client:
                client.close()

    def _call_official_api_production(
        self,
        *,
        prompt_text: str,
        scenario_id: str,
        prompt_sha256: str,
        estimated_input_tokens: int,
        estimated_output_tokens: int,
    ) -> MacroSupervisorDecision:
        # 1. Hard monthly budget enforcement BEFORE key check or any network I/O
        enforcer = self._get_budget_enforcer()
        quote = enforcer.check_and_quote(
            self.config.model_id,
            estimated_input_tokens=estimated_input_tokens,
            estimated_output_tokens=estimated_output_tokens,
        )

        # 2. Validate official HTTPS endpoint allowlist (blocks 8317 and api.poolai.win)
        vendor_spec = OFFICIAL_API_ENDPOINTS[self.config.official_vendor]
        url = assert_url_allowed(
            vendor_spec["url"],
            require_https=True,
            allowed_hosts=frozenset({vendor_spec["host"]}),
        )

        api_key = (
            self.config.official_api_key
            if self.config.official_api_key is not None
            else os.environ.get(vendor_spec["env_var"], "")
        ).strip()
        if not api_key:
            return build_degraded_neutral_decision(
                scenario_id=scenario_id,
                provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                model_id=self.config.model_id,
                status=STATUS_SKIP_MISSING_API_KEY,
                reason=f"Environment variable {vendor_spec['env_var']} is not set.",
                prompt_sha256=prompt_sha256,
                attempts=0,
                latency_ms=0.0,
                estimated_cost_usd=0.0,
            )

        wire_format = vendor_spec["wire_format"]
        if wire_format == "anthropic_messages":
            headers = {
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body: dict[str, Any] = {
                "model": self.config.model_id,
                "max_tokens": 512,
                "temperature": 0.0,
                "system": SYSTEM_PROMPT_MACRO_SUPERVISOR,
                "messages": [{"role": "user", "content": prompt_text}],
            }
        else:
            headers = {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "Accept": "application/json",
            }
            body = {
                "model": self.config.model_id,
                "temperature": 0.0,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT_MACRO_SUPERVISOR},
                    {"role": "user", "content": prompt_text},
                ],
            }

        own_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self.config.timeout_sec, follow_redirects=False)
        t0 = time.perf_counter()
        try:
            try:
                resp = client.post(url, headers=headers, json=body, timeout=self.config.timeout_sec)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    status=STATUS_SKIP_OFFLINE,
                    reason=f"Official API unreachable: {type(exc).__name__}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            if resp.status_code == 429:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    status=STATUS_RATE_LIMITED_STOP,
                    reason="HTTP 429 rate-limited by official API (retry=0).",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
            if resp.status_code in (401, 403):
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    status=STATUS_SKIP_AUTH_EXPIRED,
                    reason=f"HTTP {resp.status_code} official API auth failure.",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
            if resp.status_code != 200:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"HTTP {resp.status_code} from official API.",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            try:
                payload = resp.json()
                if not isinstance(payload, Mapping):
                    raise SupervisorValidationError("Official API JSON root is not an object")
                content = self._extract_chat_content(payload, wire_format=wire_format)
                # Compute actual cost from usage tokens if returned, else use quote estimate
                est_cost = float(quote["estimated_call_usd"])
                usage = payload.get("usage")
                if isinstance(usage, Mapping):
                    in_tok = usage.get("prompt_tokens", usage.get("input_tokens"))
                    out_tok = usage.get("completion_tokens", usage.get("output_tokens"))
                    if type(in_tok) is int and type(out_tok) is int and in_tok >= 0 and out_tok >= 0:
                        pricing = enforcer.resolve_pricing(self.config.model_id)
                        est_cost = pricing.estimate_call_usd(input_tokens=in_tok, output_tokens=out_tok)
                enforcer.record_spend(est_cost)
                return parse_supervisor_decision_json(
                    content,
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                    estimated_cost_usd=est_cost,
                )
            except (ValueError, SupervisorValidationError) as exc:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.OFFICIAL_API_PRODUCTION,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"Invalid official API response schema: {exc}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
        finally:
            if own_client:
                client.close()

    def _call_local_ollama_advisory(
        self,
        *,
        prompt_text: str,
        scenario_id: str,
        prompt_sha256: str,
    ) -> MacroSupervisorDecision:
        base = assert_url_allowed(self.config.ollama_base_url, require_loopback=True).rstrip("/")
        url = assert_url_allowed(f"{base}/api/chat", require_loopback=True)

        body = {
            "model": self.config.model_id,
            "stream": False,
            "options": {"temperature": 0.0},
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT_MACRO_SUPERVISOR},
                {"role": "user", "content": prompt_text},
            ],
        }

        own_client = self._http_client is None
        client = self._http_client or httpx.Client(timeout=self.config.timeout_sec, follow_redirects=False)
        t0 = time.perf_counter()
        try:
            try:
                resp = client.post(url, json=body, timeout=self.config.timeout_sec)
            except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
                elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY,
                    model_id=self.config.model_id,
                    status=STATUS_SKIP_OFFLINE,
                    reason=f"Local Ollama loopback unreachable: {type(exc).__name__}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            if resp.status_code != 200:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"Local Ollama returned HTTP {resp.status_code}.",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )

            try:
                payload = resp.json()
                if not isinstance(payload, Mapping):
                    raise SupervisorValidationError("Ollama JSON root is not an object")
                content = self._extract_chat_content(payload, wire_format="ollama_chat")
                parsed = parse_supervisor_decision_json(
                    content,
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY,
                    model_id=self.config.model_id,
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                    estimated_cost_usd=0.0,
                )
                # Local model is always degraded advisory mode with execution_capability=False
                return MacroSupervisorDecision(
                    scenario_id=parsed.scenario_id,
                    provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY.value,
                    model_id=parsed.model_id,
                    status=parsed.status,
                    degraded=True,
                    risk_mult=parsed.risk_mult,
                    regime_tag=parsed.regime_tag,
                    confidence=parsed.confidence,
                    reasoning_bullets=parsed.reasoning_bullets,
                    prompt_sha256=parsed.prompt_sha256,
                    response_sha256=parsed.response_sha256,
                    order_send_capable=False,
                    execution_capability=False,
                    prop_guard_override_allowed=False,
                    attempts=parsed.attempts,
                    latency_ms=parsed.latency_ms,
                    estimated_cost_usd=0.0,
                    created_utc=parsed.created_utc,
                )
            except (ValueError, SupervisorValidationError) as exc:
                return build_degraded_neutral_decision(
                    scenario_id=scenario_id,
                    provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY,
                    model_id=self.config.model_id,
                    status=STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                    reason=f"Invalid Ollama response schema: {exc}",
                    prompt_sha256=prompt_sha256,
                    attempts=1,
                    latency_ms=elapsed_ms,
                )
        finally:
            if own_client:
                client.close()


# ==============================================================================
# Prospective Shadow Ledger (Pre-Session SHA-256 Commitment + Tamper Detection)
# ==============================================================================


@dataclass(frozen=True)
class ProspectiveCommitment:
    """Immutable pre-session SHA-256 commitment entry for honest prospective AI auditing."""

    commit_seq: int
    commit_id: str
    session_date: str
    session_open_utc: str
    committed_utc: str
    first_live_session_date: str
    prospective_only: bool
    order_send_capable: bool
    prompt_sha256: str
    response_sha256: str
    decision_sha256: str
    prev_sha256: str
    sha256: str
    decision: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _compute_commitment_sha256(
    *,
    commit_seq: int,
    commit_id: str,
    session_date: str,
    session_open_utc: str,
    committed_utc: str,
    first_live_session_date: str,
    prospective_only: bool,
    order_send_capable: bool,
    prompt_sha256: str,
    response_sha256: str,
    decision_sha256: str,
    prev_sha256: str,
) -> str:
    body = {
        "commit_seq": commit_seq,
        "commit_id": commit_id,
        "session_date": session_date,
        "session_open_utc": session_open_utc,
        "committed_utc": committed_utc,
        "first_live_session_date": first_live_session_date,
        "prospective_only": prospective_only,
        "order_send_capable": order_send_capable,
        "prompt_sha256": prompt_sha256,
        "response_sha256": response_sha256,
        "decision_sha256": decision_sha256,
        "prev_sha256": prev_sha256,
    }
    return canonical_payload_sha256(body)


class ProspectiveShadowLedger:
    """Append-only pre-session SHA-256 commitment ledger (zero retrospective contamination).

    Enforces:
      - ``prospective_only = True`` and ``order_send_capable = False``.
      - ``first_live_session_date = "2026-11-30"`` (Monday after Saturday 2026-11-28).
      - ``committed_utc < session_open_utc`` strictly (rejects post-open / retrospective commits).
      - Cryptographic SHA-256 hash chain over every prompt, response, and decision.
    """

    LEDGER_SCHEMA: Final[str] = "naqex-wave4-prospective-shadow-ledger-v1"

    def __init__(
        self,
        *,
        ledger_path: Path | str | None = None,
        first_live_session_date: str = FIRST_PROSPECTIVE_LIVE_SESSION_DATE,
        min_audit_calendar_days: int = MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS,
    ) -> None:
        _enforce_module_safety_invariants()
        first_dt = _parse_iso_date(first_live_session_date, field_name="first_live_session_date")
        if first_dt.weekday() >= 5:
            raise LedgerIntegrityError(
                f"first_live_session_date ({first_live_session_date}) falls on a weekend; use a trading weekday."
            )
        self.ledger_path: Path | None = Path(ledger_path) if ledger_path is not None else None
        self.first_live_session_date: str = first_dt.isoformat()
        self.min_audit_calendar_days: int = _require_strict_int(
            min_audit_calendar_days, field_name="min_audit_calendar_days", min_value=1
        )
        self.prospective_only: bool = True
        self.commitments: list[ProspectiveCommitment] = []

    def commit_pre_session(
        self,
        decision: MacroSupervisorDecision,
        *,
        session_date: str,
        session_open_utc: datetime | str,
        committed_utc: datetime | str | None = None,
        commit_id: str | None = None,
        enforce_prospective_floor: bool = True,
        enforce_weekday_session: bool = True,
    ) -> ProspectiveCommitment:
        """Hash and commit a supervisor decision strictly BEFORE session open."""
        _enforce_module_safety_invariants()
        if not isinstance(decision, MacroSupervisorDecision):
            raise LedgerIntegrityError(f"Expected MacroSupervisorDecision, got {type(decision).__name__}")
        if decision.order_send_capable is not False or decision.execution_capability is not False:
            raise LedgerIntegrityError("Refusing to commit a decision with execution capability enabled.")

        sess_dt = _parse_iso_date(session_date, field_name="session_date")
        if enforce_weekday_session and sess_dt.weekday() >= 5:
            raise LedgerIntegrityError(
                f"session_date {session_date} is a weekend (weekday={sess_dt.weekday()}); "
                f"first live session date is {self.first_live_session_date}."
            )
        first_dt = _parse_iso_date(self.first_live_session_date, field_name="first_live_session_date")
        if enforce_prospective_floor and sess_dt < first_dt:
            raise LedgerIntegrityError(
                f"Retrospective session_date {session_date} < first_live_session_date {self.first_live_session_date}"
            )

        open_iso = _normalize_utc_iso(session_open_utc)
        commit_iso = _normalize_utc_iso(committed_utc)
        open_dt = _parse_utc_datetime(open_iso)
        commit_dt = _parse_utc_datetime(commit_iso)

        if commit_dt >= open_dt:
            raise LedgerIntegrityError(
                f"RETROSPECTIVE_COMMIT_BLOCKED: committed_utc ({commit_iso}) MUST be strictly earlier than "
                f"session_open_utc ({open_iso})."
            )

        seq = len(self.commitments) + 1
        cid = (commit_id or f"PSH-{sess_dt.strftime('%Y%m%d')}-{seq:04d}").strip()
        prev_sha = self.commitments[-1].sha256 if self.commitments else GENESIS_SHA256
        dec_dict = decision.canonical_decision_payload()
        dec_sha = canonical_payload_sha256(dec_dict)

        entry_sha = _compute_commitment_sha256(
            commit_seq=seq,
            commit_id=cid,
            session_date=sess_dt.isoformat(),
            session_open_utc=open_iso,
            committed_utc=commit_iso,
            first_live_session_date=self.first_live_session_date,
            prospective_only=True,
            order_send_capable=False,
            prompt_sha256=decision.prompt_sha256,
            response_sha256=decision.response_sha256,
            decision_sha256=dec_sha,
            prev_sha256=prev_sha,
        )

        record = ProspectiveCommitment(
            commit_seq=seq,
            commit_id=cid,
            session_date=sess_dt.isoformat(),
            session_open_utc=open_iso,
            committed_utc=commit_iso,
            first_live_session_date=self.first_live_session_date,
            prospective_only=True,
            order_send_capable=False,
            prompt_sha256=decision.prompt_sha256,
            response_sha256=decision.response_sha256,
            decision_sha256=dec_sha,
            prev_sha256=prev_sha,
            sha256=entry_sha,
            decision=dec_dict,
        )
        self.commitments.append(record)
        if self.ledger_path is not None:
            self.save(self.ledger_path)
        return record

    def verify_integrity(self) -> dict[str, Any]:
        """Recompute and verify every SHA-256 link, timestamp order, and invariant fail-closed."""
        if self.prospective_only is not True:
            raise LedgerIntegrityError("prospective_only must be strictly True")

        expected_prev = GENESIS_SHA256
        first_dt = _parse_iso_date(self.first_live_session_date, field_name="first_live_session_date")
        distinct_dates: list[date] = []

        for idx, rec in enumerate(self.commitments, start=1):
            if rec.commit_seq != idx:
                raise LedgerIntegrityError(f"Sequence gap/tamper at entry {idx}: observed commit_seq={rec.commit_seq}")
            if rec.prospective_only is not True:
                raise LedgerIntegrityError(
                    f"Entry {rec.commit_id}: prospective_only tampered ({rec.prospective_only!r})"
                )
            if rec.order_send_capable is not False:
                raise LedgerIntegrityError(f"Entry {rec.commit_id}: order_send_capable tampered")
            if rec.first_live_session_date != self.first_live_session_date:
                raise LedgerIntegrityError(f"Entry {rec.commit_id}: first_live_session_date mismatch")
            if rec.prev_sha256 != expected_prev:
                raise LedgerIntegrityError(
                    f"Hash-chain break at entry {rec.commit_id}: "
                    f"expected prev_sha256={expected_prev}, got {rec.prev_sha256}"
                )

            sess_dt = _parse_iso_date(rec.session_date, field_name=f"{rec.commit_id}.session_date")
            if sess_dt < first_dt:
                raise LedgerIntegrityError(
                    f"Entry {rec.commit_id}: session_date {rec.session_date} < {self.first_live_session_date}"
                )
            open_dt = _parse_utc_datetime(rec.session_open_utc)
            commit_dt = _parse_utc_datetime(rec.committed_utc)
            if commit_dt >= open_dt:
                raise LedgerIntegrityError(
                    f"Entry {rec.commit_id}: committed_utc ({rec.committed_utc}) >= "
                    f"session_open_utc ({rec.session_open_utc})"
                )

            if not isinstance(rec.decision, Mapping):
                raise LedgerIntegrityError(f"Entry {rec.commit_id}: decision must be a mapping")
            if rec.decision.get("order_send_capable") is not False:
                raise LedgerIntegrityError(f"Entry {rec.commit_id}: decision.order_send_capable tampered")
            if rec.decision.get("risk_mult") not in ALLOWED_RISK_MULTS:
                raise LedgerIntegrityError(f"Entry {rec.commit_id}: decision.risk_mult tampered")

            recomputed_dec_sha = canonical_payload_sha256(rec.decision)
            if recomputed_dec_sha != rec.decision_sha256:
                raise LedgerIntegrityError(
                    f"TAMPER_DETECTED in decision payload at {rec.commit_id}: "
                    f"expected {rec.decision_sha256}, recomputed {recomputed_dec_sha}"
                )

            recomputed_sha = _compute_commitment_sha256(
                commit_seq=rec.commit_seq,
                commit_id=rec.commit_id,
                session_date=rec.session_date,
                session_open_utc=rec.session_open_utc,
                committed_utc=rec.committed_utc,
                first_live_session_date=rec.first_live_session_date,
                prospective_only=rec.prospective_only,
                order_send_capable=rec.order_send_capable,
                prompt_sha256=rec.prompt_sha256,
                response_sha256=rec.response_sha256,
                decision_sha256=recomputed_dec_sha,
                prev_sha256=rec.prev_sha256,
            )
            if recomputed_sha != rec.sha256:
                raise LedgerIntegrityError(
                    f"TAMPER_DETECTED in commitment digest at {rec.commit_id}: "
                    f"expected {rec.sha256}, recomputed {recomputed_sha}"
                )

            expected_prev = rec.sha256
            if sess_dt not in distinct_dates:
                distinct_dates.append(sess_dt)

        span_days = (max(distinct_dates) - min(distinct_dates)).days + 1 if distinct_dates else 0
        return {
            "verified": True,
            "prospective_only": True,
            "first_live_session_date": self.first_live_session_date,
            "commitments_count": len(self.commitments),
            "distinct_session_dates": len(distinct_dates),
            "calendar_span_days": span_days,
            "min_audit_calendar_days": self.min_audit_calendar_days,
            "ready_for_prospective_oos_audit": span_days >= self.min_audit_calendar_days,
            "head_sha256": expected_prev,
        }

    def to_dict(self) -> dict[str, Any]:
        summary = self.verify_integrity()
        return {
            "schema_version": self.LEDGER_SCHEMA,
            "prospective_only": True,
            "order_send_capable": False,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "first_live_session_date": self.first_live_session_date,
            "min_audit_calendar_days": self.min_audit_calendar_days,
            "summary": summary,
            "commitments": [c.to_dict() for c in self.commitments],
        }

    def save(self, path: Path | str | None = None) -> Path:
        target = Path(path) if path is not None else (self.ledger_path or DEFAULT_PROSPECTIVE_LEDGER_PATH)
        payload = self.to_dict()
        _atomic_write_json(target, payload)
        return target

    @classmethod
    def load(cls, path: Path | str) -> ProspectiveShadowLedger:
        """Load and cryptographically verify a persisted Prospective Shadow Ledger fail-closed."""
        src = Path(path)
        if not src.is_file():
            raise FileNotFoundError(f"Prospective shadow ledger not found: {src}")
        try:
            raw = json.loads(src.read_text(encoding="utf-8"))
        except (OSError, ValueError) as exc:
            raise LedgerIntegrityError(f"Failed to parse ledger JSON ({src}): {exc}") from exc

        if not isinstance(raw, Mapping):
            raise LedgerIntegrityError("Ledger JSON root must be an object")
        if raw.get("prospective_only") is not True:
            raise LedgerIntegrityError("Ledger file tampered: prospective_only != True")
        if raw.get("order_send_capable") is not False:
            raise LedgerIntegrityError("Ledger file tampered: order_send_capable != False")

        ledger = cls(
            ledger_path=src,
            first_live_session_date=str(raw.get("first_live_session_date", FIRST_PROSPECTIVE_LIVE_SESSION_DATE)),
            min_audit_calendar_days=int(raw.get("min_audit_calendar_days", MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS)),
        )
        raw_commits = raw.get("commitments")
        if not isinstance(raw_commits, list):
            raise LedgerIntegrityError("Ledger JSON missing 'commitments' list")

        for item in raw_commits:
            if not isinstance(item, Mapping):
                raise LedgerIntegrityError("Each commitment entry must be an object")
            try:
                ledger.commitments.append(
                    ProspectiveCommitment(
                        commit_seq=item["commit_seq"],
                        commit_id=str(item["commit_id"]),
                        session_date=str(item["session_date"]),
                        session_open_utc=str(item["session_open_utc"]),
                        committed_utc=str(item["committed_utc"]),
                        first_live_session_date=str(item["first_live_session_date"]),
                        prospective_only=item["prospective_only"],
                        order_send_capable=item["order_send_capable"],
                        prompt_sha256=str(item["prompt_sha256"]),
                        response_sha256=str(item["response_sha256"]),
                        decision_sha256=str(item["decision_sha256"]),
                        prev_sha256=str(item["prev_sha256"]),
                        sha256=str(item["sha256"]),
                        decision=dict(item["decision"]) if isinstance(item.get("decision"), Mapping) else {},
                    )
                )
            except KeyError as exc:
                raise LedgerIntegrityError(f"Commitment entry missing required key: {exc}") from exc

        ledger.verify_integrity()
        return ledger


# ==============================================================================
# 6-Criteria x 5-Architecture Comparison Builder (W4-G14)
# ==============================================================================

RUBRIC_CRITERIA_KEYS: Final[tuple[str, ...]] = (
    "monthly_cost_usd_vnd",
    "inference_latency",
    "tos_oauth_ban_risk",
    "whitebox_auditability",
    "offline_determinism",
    "anti_contamination_integrity",
)

RUBRIC_ARCHITECTURE_NAMES: Final[tuple[str, ...]] = (
    "Official API <= 5 USD/mo",
    "Neurobro (neurobro.ai)",
    "Project CLIProxyAPI 17852",
    "Local Ollama RTX 2070S",
    "MT5 ONNX / Pure-MQL5 v1.04-ML",
)


def build_ai_architecture_rubric_6criteria(
    *,
    radar_snapshot_path: Path | str | None = None,
    radar_payload: Mapping[str, Any] | None = None,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Build structured 6-criteria comparison across all 5 AI architectures for prop trading.

    Optionally enriches Official API & Local Ollama pricing/fit rows from
    ``ai_model_radar_latest.json`` while remaining 100% deterministic offline in CI.
    """
    _enforce_module_safety_invariants()
    fx_rate = _require_finite_float(usd_vnd_rate, field_name="usd_vnd_rate", strictly_positive=True)

    # Optional enrichment from AI Model Radar snapshot (graceful offline defaults when absent)
    radar_data: Mapping[str, Any] | None = radar_payload
    radar_source = "offline_reference_baseline"
    if radar_data is None and radar_snapshot_path is not None:
        p = Path(radar_snapshot_path)
        if p.is_file():
            radar_data = json.loads(p.read_text(encoding="utf-8"))
            radar_source = str(p.name)
    elif radar_data is not None:
        radar_source = "in_memory_radar_payload"

    top_budget_model = "qwen/qwen3.7-flash"
    top_budget_usd = 0.0196
    top_reasoning_model = "openai/gpt-6-luna-pro"
    top_reasoning_usd = 0.0700
    top_local_model = "qwen/qwen3.5-9b"
    top_local_q4_gb = 5.66

    if isinstance(radar_data, Mapping):
        wa = radar_data.get("workload_assumptions")
        if (
            isinstance(wa, Mapping)
            and isinstance(wa.get("usd_vnd_rate"), (int, float))
            and not isinstance(wa["usd_vnd_rate"], bool)
        ):
            fx_rate = float(wa["usd_vnd_rate"])
        lbs = radar_data.get("leaderboards")
        if isinstance(lbs, Mapping):
            bm = lbs.get("budget_macro_supervisor_monthly_usd")
            if isinstance(bm, list) and bm and isinstance(bm[0], Mapping):
                top_budget_model = str(bm[0].get("id") or top_budget_model)
                top_budget_usd = float(bm[0].get("monthly_usd", top_budget_usd))
            vr = lbs.get("top_value_reasoning")
            if isinstance(vr, list) and vr and isinstance(vr[0], Mapping):
                top_reasoning_model = str(vr[0].get("id") or top_reasoning_model)
                top_reasoning_usd = float(vr[0].get("monthly_supervisor_usd", top_reasoning_usd))
            loc = lbs.get("local_open_weight_fit")
            if isinstance(loc, list) and loc and isinstance(loc[0], Mapping):
                top_local_model = str(loc[0].get("id") or top_local_model)
                top_local_q4_gb = float(loc[0].get("q4_estimated_gb", top_local_q4_gb))

    top_budget_vnd = int(round(top_budget_usd * fx_rate))
    top_reasoning_vnd = int(round(top_reasoning_usd * fx_rate))
    cap_vnd = int(round(MAX_OFFICIAL_API_USD_PER_MONTH * fx_rate))
    neurobro_est_usd = 29.0
    neurobro_est_vnd = int(round(neurobro_est_usd * fx_rate))

    architectures: list[dict[str, Any]] = [
        {
            "architecture": "Official API <= 5 USD/mo",
            "architecture_id": "official_api_5usd_cap",
            "recommended_role": "PRIMARY_MACRO_ADVISORY_SHADOW_AND_PROD",
            "order_send_capable": False,
            "criteria": {
                "monthly_cost_usd_vnd": {
                    "score_1_to_5": 5.0,
                    "rating": "EXCELLENT",
                    "monthly_usd_range": [round(top_budget_usd, 4), round(MAX_OFFICIAL_API_USD_PER_MONTH, 2)],
                    "monthly_vnd_range": [top_budget_vnd, cap_vnd],
                    "summary": (
                        f"44 runs/mo via {top_budget_model} costs ~${top_budget_usd:.4f}/mo "
                        f"(~{top_budget_vnd:,} VND/mo); reasoning tier {top_reasoning_model} "
                        f"~${top_reasoning_usd:.4f}/mo (~{top_reasoning_vnd:,} VND/mo); "
                        f"hard-capped <= ${MAX_OFFICIAL_API_USD_PER_MONTH:.2f}/mo ({cap_vnd:,} VND/mo)."
                    ),
                },
                "inference_latency": {
                    "score_1_to_5": 4.0,
                    "rating": "GOOD",
                    "typical_latency_ms": [800, 3500],
                    "summary": (
                        "0.8-3.5s per pre-session call; ample headroom for 2x/day macro advisory "
                        "(never in tick hot-path)."
                    ),
                },
                "tos_oauth_ban_risk": {
                    "score_1_to_5": 5.0,
                    "rating": "VERY_LOW_RISK",
                    "summary": (
                        "Official paid API key & published ToS; zero consumer-OAuth scraping "
                        "or account ban exposure."
                    ),
                },
                "whitebox_auditability": {
                    "score_1_to_5": 4.0,
                    "rating": "HIGH",
                    "summary": (
                        "Full prompt/response SHA-256 logging, strict JSON schema, bounded "
                        "risk_mult in {0,0.5,0.75,1.0}; model weights remain cloud-hosted."
                    ),
                },
                "offline_determinism": {
                    "score_1_to_5": 2.5,
                    "rating": "MODERATE_LOW",
                    "summary": (
                        "Requires internet; temperature=0 improves repeatability but cloud providers "
                        "may update weights silently (fail-closed neutral fallback)."
                    ),
                },
                "anti_contamination_integrity": {
                    "score_1_to_5": 4.0,
                    "rating": "HIGH_WITH_PROSPECTIVE_LEDGER",
                    "summary": (
                        "Historical backtests remain exposed to pretraining memory unless strictly "
                        "anonymized AND audited prospectively >= 30 calendar days via SHA-256 commitments."
                    ),
                },
            },
        },
        {
            "architecture": "Neurobro (neurobro.ai)",
            "architecture_id": "neurobro_saas",
            "recommended_role": "REJECT_BLACKBOX_SAAS",
            "order_send_capable": False,
            "criteria": {
                "monthly_cost_usd_vnd": {
                    "score_1_to_5": 2.0,
                    "rating": "EXPENSIVE_SUBSCRIPTION",
                    "monthly_usd_range": [neurobro_est_usd, 99.0],
                    "monthly_vnd_range": [neurobro_est_vnd, int(round(99.0 * fx_rate))],
                    "summary": (
                        f"Closed SaaS subscription (~${neurobro_est_usd:.0f}-${99:.0f}/mo = "
                        f"{neurobro_est_vnd:,}-{int(round(99.0 * fx_rate)):,} VND/mo), "
                        "far above <= $5/mo official API cap."
                    ),
                },
                "inference_latency": {
                    "score_1_to_5": 2.5,
                    "rating": "VARIABLE_CLOUD_AGENT",
                    "typical_latency_ms": [3000, 15000],
                    "summary": (
                        "Multi-step third-party web agent latency (3-15s+) with no SLA for "
                        "pre-session deterministic pipelines."
                    ),
                },
                "tos_oauth_ban_risk": {
                    "score_1_to_5": 3.0,
                    "rating": "VENDOR_LOCK_IN",
                    "summary": (
                        "Third-party SaaS dependency; prop firms penalize unverified third-party "
                        "black-box signal services."
                    ),
                },
                "whitebox_auditability": {
                    "score_1_to_5": 1.0,
                    "rating": "FAIL_BLACKBOX",
                    "summary": (
                        "Opaque prompts, hidden data feeds, and non-reproducible scoring fail "
                        "Naqex white-box prop auditability."
                    ),
                },
                "offline_determinism": {
                    "score_1_to_5": 1.0,
                    "rating": "FAIL_CLOUD_ONLY",
                    "summary": (
                        "Zero offline reproducibility, no pinned model hash, and no Strategy "
                        "Tester replay compatibility."
                    ),
                },
                "anti_contamination_integrity": {
                    "score_1_to_5": 1.0,
                    "rating": "FAIL_UNVERIFIABLE",
                    "summary": (
                        "Cannot enforce anonymized telemetry or verify absence of retrospective "
                        "look-ahead bias."
                    ),
                },
            },
        },
        {
            "architecture": "Project CLIProxyAPI 17852",
            "architecture_id": "project_cliproxy_17852",
            "recommended_role": "DEV_RESEARCH_ONLY_SANDBOXED",
            "order_send_capable": False,
            "criteria": {
                "monthly_cost_usd_vnd": {
                    "score_1_to_5": 4.5,
                    "rating": "ZERO_MARGINAL_DEV_COST",
                    "monthly_usd_range": [0.0, 0.0],
                    "monthly_vnd_range": [0, 0],
                    "summary": (
                        "$0.00/mo (0 VND) marginal spend on existing subscription; external "
                        "third-party api.poolai.win stripped via sanitized temp YAML."
                    ),
                },
                "inference_latency": {
                    "score_1_to_5": 3.5,
                    "rating": "MODERATE",
                    "typical_latency_ms": [1200, 6000],
                    "summary": (
                        "1.2-6.0s through loopback 127.0.0.1:17852 proxy; "
                        "request-retry: 0 prevents retry storms."
                    ),
                },
                "tos_oauth_ban_risk": {
                    "score_1_to_5": 1.5,
                    "rating": "HIGH_OAUTH_TOS_RISK",
                    "summary": (
                        "Consumer OAuth proxy carries elevated 429/expiry/ToS suspension risk if "
                        "automated in production -> Dev evaluation ONLY; port 8317 hard-blocked."
                    ),
                },
                "whitebox_auditability": {
                    "score_1_to_5": 4.0,
                    "rating": "HIGH",
                    "summary": (
                        "Workspace-owned loopback gateway with SHA-256 prompt/response logging "
                        "and non-mutating sanitized YAML audit trail."
                    ),
                },
                "offline_determinism": {
                    "score_1_to_5": 2.0,
                    "rating": "LOW",
                    "summary": (
                        "Depends on live upstream OAuth session & loopback daemon lifecycle; "
                        "degrades cleanly to NEUTRAL on 429/401/offline."
                    ),
                },
                "anti_contamination_integrity": {
                    "score_1_to_5": 4.0,
                    "rating": "HIGH_WITH_ANONYMIZER",
                    "summary": (
                        "Uses identical 24 anonymized scenarios & Prospective Shadow SHA-256 ledger; "
                        "still subject to upstream LLM pretraining cutoffs."
                    ),
                },
            },
        },
        {
            "architecture": "Local Ollama RTX 2070S",
            "architecture_id": "local_ollama_rtx2070s",
            "recommended_role": "OFFLINE_DEGRADED_ADVISORY_FALLBACK",
            "order_send_capable": False,
            "criteria": {
                "monthly_cost_usd_vnd": {
                    "score_1_to_5": 5.0,
                    "rating": "ZERO_API_COST",
                    "monthly_usd_range": [0.0, 0.0],
                    "monthly_vnd_range": [0, 0],
                    "summary": (
                        f"$0.00/mo (0 VND) API fee on owned RTX 2070 SUPER 8GB VRAM / 32GB RAM "
                        f"(e.g., {top_local_model} Q4 ~{top_local_q4_gb:.2f} GB FULL_VRAM_FIT)."
                    ),
                },
                "inference_latency": {
                    "score_1_to_5": 3.5,
                    "rating": "LOCAL_GPU_GOOD",
                    "typical_latency_ms": [1500, 5000],
                    "summary": (
                        "1.5-5.0s for 8B-9B Q4 in VRAM; degrades sharply if spilling to CPU/RAM "
                        "hybrid offload or while owner games."
                    ),
                },
                "tos_oauth_ban_risk": {
                    "score_1_to_5": 5.0,
                    "rating": "ZERO_RISK",
                    "summary": (
                        "100% local open-weight execution on 127.0.0.1:11434; zero external ToS, "
                        "OAuth, or data-leak risk."
                    ),
                },
                "whitebox_auditability": {
                    "score_1_to_5": 4.5,
                    "rating": "VERY_HIGH",
                    "summary": (
                        "Pinned local GGUF digest, full local prompt/response SHA-256 logs, "
                        "hard execution_capability=False degraded advisory mode."
                    ),
                },
                "offline_determinism": {
                    "score_1_to_5": 4.5,
                    "rating": "HIGH_OFFLINE",
                    "summary": (
                        "Works air-gapped with pinned GGUF weights and temperature=0 "
                        "(minor floating-point GPU kernel nondeterminism)."
                    ),
                },
                "anti_contamination_integrity": {
                    "score_1_to_5": 4.0,
                    "rating": "HIGH_WITH_PROSPECTIVE_LEDGER",
                    "summary": (
                        "Fixed local model cutoff + strict anonymizer + >= 30-day Prospective Shadow "
                        "SHA-256 commitments; weaker macro nuance than frontier APIs."
                    ),
                },
            },
        },
        {
            "architecture": "MT5 ONNX / Pure-MQL5 v1.04-ML",
            "architecture_id": "mt5_onnx_pure_mql5_v104_ml",
            "recommended_role": "PRIMARY_EXECUTION_PATH_QUANT_FILTER",
            "order_send_capable": False,
            "criteria": {
                "monthly_cost_usd_vnd": {
                    "score_1_to_5": 5.0,
                    "rating": "ZERO_COST",
                    "monthly_usd_range": [0.0, 0.0],
                    "monthly_vnd_range": [0, 0],
                    "summary": "$0.00/mo (0 VND) marginal runtime cost inside existing MT5 VPS terminal.",
                },
                "inference_latency": {
                    "score_1_to_5": 5.0,
                    "rating": "SUB_MILLISECOND",
                    "typical_latency_ms": [0.1, 1.0],
                    "summary": (
                        "< 1 ms float32 OnnxRun() or pure-MQL5 tree evaluation; safe inside live "
                        "tick/bar execution path."
                    ),
                },
                "tos_oauth_ban_risk": {
                    "score_1_to_5": 5.0,
                    "rating": "ZERO_RISK",
                    "summary": (
                        "Self-contained local binary/MQL5 artifact; zero external APIs, "
                        "zero OAuth, zero network calls."
                    ),
                },
                "whitebox_auditability": {
                    "score_1_to_5": 5.0,
                    "rating": "FULL_WHITEBOX",
                    "summary": (
                        "100% auditable 24 causal Dev features (<= 2024-12-31), "
                        "Python == onnxruntime == MT5 OnnxRun <= 1e-5 parity, full SHAP/tree audit."
                    ),
                },
                "offline_determinism": {
                    "score_1_to_5": 5.0,
                    "rating": "EXACT_DETERMINISTIC",
                    "summary": (
                        "Bit-reproducible offline in Python & MT5 Real-Tick Strategy Tester "
                        "with zero internet dependency."
                    ),
                },
                "anti_contamination_integrity": {
                    "score_1_to_5": 5.0,
                    "rating": "STRICT_CAUSAL_DEV_ONLY",
                    "summary": (
                        "Trained strictly on Dev <= 2024-12-31 with Holdout 2025+ sealed and zero "
                        "LLM pretraining leakage (cannot parse unstructured breaking news)."
                    ),
                },
            },
        },
    ]

    # Compute equal-weight composite averages cleanly
    for entry in architectures:
        crit = entry["criteria"]
        scores = [float(crit[k]["score_1_to_5"]) for k in RUBRIC_CRITERIA_KEYS]
        entry["composite_score_5"] = round(sum(scores) / len(scores), 3)

    ranked = sorted(architectures, key=lambda x: x["composite_score_5"], reverse=True)
    return {
        "schema_version": "naqex-wave4-ai-architecture-rubric-6criteria-v1",
        "generated_utc": _normalize_utc_iso(),
        "radar_source": radar_source,
        "usd_vnd_rate": fx_rate,
        "criteria_keys": list(RUBRIC_CRITERIA_KEYS),
        "architecture_count": len(architectures),
        "criteria_count": len(RUBRIC_CRITERIA_KEYS),
        "hard_invariants": {
            "order_send_capable": False,
            "max_official_api_usd_per_month": MAX_OFFICIAL_API_USD_PER_MONTH,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "forbidden_external_port": FORBIDDEN_EXTERNAL_CLIPROXY_PORT,
        },
        "architectures": architectures,
        "ranking_by_composite": [
            {
                "rank": i,
                "architecture": item["architecture"],
                "composite_score_5": item["composite_score_5"],
                "recommended_role": item["recommended_role"],
            }
            for i, item in enumerate(ranked, start=1)
        ],
        "recommended_hybrid_stack": {
            "execution_path_filter": "MT5 ONNX / Pure-MQL5 v1.04-ML",
            "pre_session_macro_advisory": "Official API <= 5 USD/mo",
            "offline_degraded_fallback": "Local Ollama RTX 2070S",
            "dev_only_eval_proxy": "Project CLIProxyAPI 17852",
            "rejected": ["Neurobro (neurobro.ai)"],
        },
    }


# ==============================================================================
# Strictly Offline-Safe CLI (Zero Live Orders, Zero Port 8317 Touches)
# ==============================================================================


def main(argv: Sequence[str] | None = None) -> int:
    _enforce_module_safety_invariants()
    parser = argparse.ArgumentParser(description="Wave 4 Macro AI Supervisor offline utility (W4-G14).")
    parser.add_argument("--dump-scenarios", action="store_true", help="Print the 24 anonymized scenarios as JSON.")
    parser.add_argument("--dump-rubric", action="store_true", help="Print the 6-criteria x 5-architecture rubric JSON.")
    parser.add_argument(
        "--radar-snapshot", type=Path, default=None, help="Optional path to ai_model_radar_latest.json."
    )
    parser.add_argument("--sanitize-source", type=Path, default=None, help="Optional managed.yaml path to sanitize.")
    parser.add_argument("--sanitize-output", type=Path, default=None, help="Output path for sanitized temp YAML.")
    args = parser.parse_args(list(argv) if argv is not None else None)

    if args.dump_scenarios:
        scenarios = build_anonymized_24_macro_scenarios()
        print(json.dumps([s.to_dict() for s in scenarios], indent=2, ensure_ascii=False))
        return 0

    if args.dump_rubric:
        rubric = build_ai_architecture_rubric_6criteria(radar_snapshot_path=args.radar_snapshot)
        print(json.dumps(rubric, indent=2, ensure_ascii=False))
        return 0

    if args.sanitize_source is not None:
        res = write_sanitized_gateway_config(args.sanitize_source, args.sanitize_output)
        print(json.dumps(res.to_safe_receipt(), indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 0


__all__ = [
    "ALLOWED_REGIME_TAGS",
    "ALLOWED_RISK_MULTS",
    "AnonymizedMacroScenario",
    "BLOCKED_UPSTREAM_DOMAINS",
    "BudgetExceededError",
    "ContaminationError",
    "DEFAULT_GATEWAY_OWNER_PATH",
    "DEFAULT_OLLAMA_BASE_URL",
    "DEFAULT_PROJECT_CLIPROXY_PORT",
    "DEFAULT_RADAR_SNAPSHOT_PATH",
    "DEFAULT_SANITIZED_GATEWAY_YAML_PATH",
    "EXECUTION_CAPABLE",
    "FIRST_PROSPECTIVE_LIVE_SESSION_DATE",
    "FORBIDDEN_EXTERNAL_CLIPROXY_PORT",
    "GatewayOwnerConfig",
    "HOLDOUT_CUTOFF_DATE",
    "LedgerIntegrityError",
    "MAX_OFFICIAL_API_USD_PER_MONTH",
    "MacroAISupervisor",
    "MacroSupervisorConfig",
    "MacroSupervisorDecision",
    "MacroSupervisorError",
    "ModelPricingEntry",
    "ORDER_SEND_CAPABLE",
    "ORDER_SEND_COUNT",
    "OfficialApiBudgetEnforcer",
    "PROP_GUARD_OVERRIDE_ALLOWED",
    "ProspectiveCommitment",
    "ProspectiveShadowLedger",
    "ProviderMode",
    "RUBRIC_ARCHITECTURE_NAMES",
    "RUBRIC_CRITERIA_KEYS",
    "STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR",
    "STATUS_OK",
    "STATUS_RATE_LIMITED_STOP",
    "STATUS_SKIP_AUTH_EXPIRED",
    "STATUS_SKIP_MISSING_API_KEY",
    "STATUS_SKIP_OFFLINE",
    "SYSTEM_PROMPT_MACRO_SUPERVISOR",
    "SanitizedGatewayResult",
    "SecurityError",
    "StandaloneGateway17852",
    "SupervisorValidationError",
    "assert_anonymized_prompt_clean",
    "assert_port_allowed",
    "assert_url_allowed",
    "build_ai_architecture_rubric_6criteria",
    "build_anonymized_24_macro_scenarios",
    "build_degraded_neutral_decision",
    "canonical_payload_sha256",
    "cleanup_stale_gateway_pid_file",
    "extract_gateway_port",
    "extract_request_retry",
    "find_contamination_violations",
    "load_radar_pricing_catalog",
    "parse_supervisor_decision_json",
    "resolve_project_gateway_owner",
    "sanitize_gateway_yaml_text",
    "write_sanitized_gateway_config",
]


if __name__ == "__main__":
    raise SystemExit(main())
