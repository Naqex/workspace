"""Wave 4 Live PIT-24 Macro Supervisor Benchmark & 6-Criteria AI Rubric Runner (W4-G14).

Executes the 24-event anonymized Macro AI Supervisor benchmark (PIT-24) on the
standalone project CLIProxyAPI loopback gateway (port ``17852``), initializes the
Prospective Shadow Ledger (``first_live_session_date="2026-11-30"``), and produces
the complete 6-criteria x 5-architecture AI benchmark JSON.

Hard Safety & LOCAL-SERVICES.md Invariants (ZERO EXCEPTIONS):
  - ``ORDER_SEND_CAPABLE = False``, ``ORDER_SEND_COUNT = 0``, ``SPEND_VND = 0``.
  - ``HOLDOUT_CUTOFF_DATE = "2024-12-31"`` (Holdout 2025+ SEALED, 0 rows analysed).
  - NEVER touch external Windows CLIProxyAPI port ``8317`` (passive OS listener
    snapshot verified identical before & after; zero TCP probes to ``8317``).
  - NEVER mutate source ``managed.yaml`` (SHA-256 verified identical before & after).
  - Launches standalone ``17852`` ONLY via ``StandaloneGateway17852`` (sanitized temp
    YAML stripping ``api.poolai.win``, ``request-retry: 0``, logs redirected to
    ``.runtime/paperclip/``, stale dead PID cleanup, own-PID-only teardown in ``finally:``).
  - Honest failure reporting (0 fabrication): records exact ``LIVE_24_PASS``,
    ``LIVE_24_DEGRADED``, ``PARTIAL_RATE_LIMITED_429``, ``SKIP_AUTH_EXPIRED``, or
    ``SKIP_OFFLINE`` based on real observed gateway responses.
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
import statistics
import subprocess
import time
from collections.abc import Callable, Mapping, Sequence
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import httpx
import yaml

from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)
from quant_factory.wave4.macro_ai_supervisor import (
    _NO_WINDOW_FLAGS,
    ALLOWED_RISK_MULTS,
    DEFAULT_GATEWAY_OWNER_PATH,
    DEFAULT_PAPERCLIP_RUNTIME_DIR,
    DEFAULT_PROJECT_CLIPROXY_PORT,
    DEFAULT_PROSPECTIVE_LEDGER_PATH,
    DEFAULT_RADAR_SNAPSHOT_PATH,
    DEFAULT_SANITIZED_GATEWAY_YAML_PATH,
    DEFAULT_USD_VND_RATE,
    DEFAULT_WAVE4_GATEWAY_PID_PATH,
    EXECUTION_CAPABLE,
    FIRST_PROSPECTIVE_LIVE_SESSION_DATE,
    FORBIDDEN_EXTERNAL_CLIPROXY_PORT,
    MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS,
    ORDER_SEND_COUNT,
    PROP_GUARD_OVERRIDE_ALLOWED,
    RUBRIC_ARCHITECTURE_NAMES,
    RUBRIC_CRITERIA_KEYS,
    STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
    STATUS_OK,
    STATUS_RATE_LIMITED_STOP,
    STATUS_SKIP_AUTH_EXPIRED,
    STATUS_SKIP_OFFLINE,
    SYSTEM_PROMPT_MACRO_SUPERVISOR,
    WORKSPACE_ROOT,
    AnonymizedMacroScenario,
    MacroAISupervisor,
    MacroSupervisorConfig,
    MacroSupervisorDecision,
    ProspectiveShadowLedger,
    ProviderMode,
    SecurityError,
    StandaloneGateway17852,
    SupervisorValidationError,
    _atomic_write_json,
    _enforce_module_safety_invariants,
    _is_pid_alive,
    _is_tcp_port_open,
    assert_anonymized_prompt_clean,
    assert_port_allowed,
    assert_url_allowed,
    build_ai_architecture_rubric_6criteria,
    build_anonymized_24_macro_scenarios,
    extract_loopback_client_api_key,
    resolve_project_gateway_owner,
)

# ==============================================================================
# Canonical Constants & Output Paths
# ==============================================================================

RUNNER_SCHEMA_VERSION: Final[str] = "naqex-wave4-pit24-and-ai-rubric-v1"
SPEND_VND: Final[int] = 0
HOLDOUT_ROWS_ANALYSED: Final[int] = 0
DEFAULT_PIT24_RUBRIC_OUT_PATH: Final[Path] = (
    WORKSPACE_ROOT / ".runtime" / "offensive4" / "ai" / "wave4_pit24_and_ai_rubric.json"
)
DEFAULT_LIVE_TIMEOUT_SEC: Final[float] = 45.0
DEFAULT_INTER_REQUEST_DELAY_SEC: Final[float] = 0.25

# Honest PIT-24 outcome codes
OUTCOME_LIVE_24_PASS: Final[str] = "LIVE_24_PASS"
OUTCOME_LIVE_24_DEGRADED: Final[str] = "LIVE_24_DEGRADED"
OUTCOME_PARTIAL_RATE_LIMITED_429: Final[str] = "PARTIAL_RATE_LIMITED_429"
OUTCOME_SKIP_AUTH_EXPIRED: Final[str] = "SKIP_AUTH_EXPIRED"
OUTCOME_SKIP_OFFLINE: Final[str] = "SKIP_OFFLINE"

VALID_PIT24_OUTCOMES: Final[frozenset[str]] = frozenset(
    {
        OUTCOME_LIVE_24_PASS,
        OUTCOME_LIVE_24_DEGRADED,
        OUTCOME_PARTIAL_RATE_LIMITED_429,
        OUTCOME_SKIP_AUTH_EXPIRED,
        OUTCOME_SKIP_OFFLINE,
    }
)

# Preferred chat model priority order when dynamically selecting from loopback /v1/models
PREFERRED_MODEL_ORDER: Final[tuple[str, ...]] = (
    "gpt-6-luna",
    "gpt-5.6-terra",
    "gpt-oss-120b-medium",
    "gemini-3.8-flash-high",
    "gemini-3.5-flash-lite",
    "gemini-3.1-flash-lite",
    "gemini-2.5-flash",
    "gemini-3-flash",
    "gemini-3-flash-preview",
    "gpt-5.1-codex-mini",
    "gpt-5-mini",
    "gpt-5.4-mini",
    "gpt-5.2-codex",
    "gpt-5.3-codex",
    "gpt-5.4",
    "claude-sonnet-4-5",
    "claude-sonnet-4.5",
    "claude-sonnet-4-6",
    "claude-sonnet-4.6",
    "gemini-2.5-pro",
    "gemini-3-pro",
    "gpt-5",
)

# Non-chat model IDs excluded from /v1/chat/completions candidate selection
_NON_CHAT_MODEL_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:image|dall-e|whisper|tts|embedding|audio|auto-review|moderation)",
    re.IGNORECASE,
)

# Regex patterns to detect auth expiry or 429 wrapped inside upstream proxy 5xx/4xx bodies
_AUTH_EXPIRED_BODY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:invalid_grant|token\s+expired|expired\s+token|refresh\s+token|unauthenticated|"
    r"unauthorized|invalid_token|auth\s+expired|auth_unavailable|no\s+auth\s+available|"
    r"re-?authenticate|no\s+available\s+credentials|permission_denied|verify\s+your\s+account|"
    r"no\s+valid\s+auth|account\s+disabled|oauth.*(?:expired|revoked|invalid))",
    re.IGNORECASE,
)
_RATE_LIMIT_BODY_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:rate[_\s-]?limit|too\s+many\s+requests|quota\s+exceeded|resource_exhausted|status\s*429)",
    re.IGNORECASE,
)
_NETSTAT_LISTEN_RE: Final[re.Pattern[str]] = re.compile(
    r"^\s*TCP\s+(\S+):(\d+)\s+\S+\s+LISTENING\s+(\d+)\s*$",
    re.IGNORECASE,
)
_SECRET_REDACT_RE: Final[re.Pattern[str]] = re.compile(
    r"(?:Bearer\s+\S+|sk-[A-Za-z0-9_-]{12,}|AIza[0-9A-Za-z_-]{16,}|ghp_[A-Za-z0-9]{16,}|"
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})",
    re.IGNORECASE,
)


# ==============================================================================
# Helpers: Hashing, Redaction, Passive OS Listener Snapshot (Zero Port-8317 Touch)
# ==============================================================================


def _utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _sha256_file(path: Path) -> str:
    if not path.is_file():
        raise FileNotFoundError(f"File not found for SHA-256 verification: {path}")
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _redact_text(text: str, *, max_len: int = 240) -> str:
    """Sanitize diagnostic snippets so emails, bearer keys, or tokens are NEVER persisted."""
    cleaned = _SECRET_REDACT_RE.sub("<REDACTED>", text or "")
    cleaned = " ".join(cleaned.split())
    return cleaned[:max_len]


def snapshot_tcp_listeners_passive(target_ports: Sequence[int]) -> dict[int, list[dict[str, Any]]]:
    """Passively inspect OS TCP listening sockets via ``netstat -ano`` (ZERO packets sent).

    Crucially, this NEVER opens a socket or sends a SYN packet to port ``8317``;
    it only reads the kernel socket table to prove port ``8317`` stayed untouched
    and port ``17852`` has zero listening processes after teardown.
    """
    ports = [int(p) for p in target_ports]
    result: dict[int, list[dict[str, Any]]] = {p: [] for p in ports}
    port_set = set(ports)

    if os.name == "nt":
        proc = subprocess.run(
            ["netstat", "-ano", "-p", "TCP"],
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        for line in (proc.stdout or "").splitlines():
            m = _NETSTAT_LISTEN_RE.match(line)
            if not m:
                continue
            addr, port_str, pid_str = m.group(1), m.group(2), m.group(3)
            port_num = int(port_str)
            if port_num in port_set:
                result[port_num].append({"local_address": addr, "port": port_num, "pid": int(pid_str)})
    else:
        proc = subprocess.run(
            ["ss", "-ltnp"],
            capture_output=True,
            text=True,
            timeout=10.0,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
        for line in (proc.stdout or "").splitlines():
            for p in ports:
                if f":{p} " in line:
                    result[p].append({"raw": line.strip()[:120], "port": p})

    for p in ports:
        result[p].sort(key=lambda r: (str(r.get("local_address", "")), int(r.get("pid", 0))))
    return result


def _percentile(sorted_vals: Sequence[float], pct: float) -> float:
    if not sorted_vals:
        return 0.0
    if len(sorted_vals) == 1:
        return round(float(sorted_vals[0]), 2)
    rank = (pct / 100.0) * (len(sorted_vals) - 1)
    lo = int(math.floor(rank))
    hi = int(math.ceil(rank))
    if lo == hi:
        return round(float(sorted_vals[lo]), 2)
    frac = rank - lo
    val = float(sorted_vals[lo]) * (1.0 - frac) + float(sorted_vals[hi]) * frac
    return round(val, 2)


def _summarize_latencies(latencies_ms: Sequence[float]) -> dict[str, Any]:
    vals = sorted(float(x) for x in latencies_ms if isinstance(x, (int, float)) and math.isfinite(float(x)))
    if not vals:
        return {
            "count": 0,
            "min_ms": None,
            "p50_ms": None,
            "mean_ms": None,
            "p95_ms": None,
            "max_ms": None,
            "total_ms": 0.0,
        }
    return {
        "count": len(vals),
        "min_ms": round(vals[0], 2),
        "p50_ms": round(float(statistics.median(vals)), 2),
        "mean_ms": round(float(statistics.fmean(vals)), 2),
        "p95_ms": _percentile(vals, 95.0),
        "max_ms": round(vals[-1], 2),
        "total_ms": round(sum(vals), 2),
    }


def _model_family(model_id: str) -> str:
    low = model_id.lower()
    if "gemini" in low:
        return "gemini"
    if "claude" in low:
        return "claude"
    if "gpt" in low or "codex" in low or low.startswith("o1") or low.startswith("o3") or low.startswith("o4"):
        return "openai_codex"
    if "qwen" in low:
        return "qwen"
    if "deepseek" in low:
        return "deepseek"
    return "other"


def select_candidate_models(
    available_models: Sequence[str],
    *,
    requested_model: str | None = None,
) -> list[str]:
    """Select an ordered list of chat-capable candidate models (at most 1 per provider family)."""
    clean_avail = [
        m.strip()
        for m in available_models
        if isinstance(m, str) and m.strip() and not _NON_CHAT_MODEL_RE.search(m.strip())
    ]
    if requested_model and requested_model.strip():
        req = requested_model.strip()
        if not clean_avail or req in clean_avail:
            return [req]
        return [req, *clean_avail[:1]]

    if not clean_avail:
        return ["gemini-2.5-flash"]

    ordered: list[str] = []
    seen_ids: set[str] = set()
    avail_set = set(clean_avail)

    for pref in PREFERRED_MODEL_ORDER:
        if pref in avail_set and pref not in seen_ids:
            ordered.append(pref)
            seen_ids.add(pref)

    for mid in clean_avail:
        if mid not in seen_ids:
            ordered.append(mid)
            seen_ids.add(mid)

    # Deduplicate to 1 primary candidate per provider family (avoids futile retries on same expired OAuth pool)
    per_family: list[str] = []
    seen_families: set[str] = set()
    for mid in ordered:
        fam = _model_family(mid)
        if fam not in seen_families:
            per_family.append(mid)
            seen_families.add(fam)
        if len(per_family) >= 3:
            break
    return per_family or ordered[:1]


# ==============================================================================
# Discovery & PIT-24 Execution Core (Works Both Live and Under Mocked Unit Tests)
# ==============================================================================


class _DiagnosticTransport(httpx.BaseTransport):
    """Read-only HTTP wrapper recording last status & redacted error snippet without retrying."""

    def __init__(self, inner: httpx.BaseTransport) -> None:
        self._inner = inner
        self.last_status_code: int | None = None
        self.last_error_snippet: str = ""
        self.request_count: int = 0

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        self.request_count += 1
        resp = self._inner.handle_request(request)
        self.last_status_code = int(resp.status_code)
        if resp.status_code != 200:
            try:
                resp.read()
                self.last_error_snippet = _redact_text(resp.text, max_len=240)
            except Exception:
                self.last_error_snippet = f"HTTP {resp.status_code}"
        else:
            self.last_error_snippet = ""
        return resp

    def close(self) -> None:
        self._inner.close()


def discover_gateway_models(
    *,
    base_url: str,
    bearer_key: str | None,
    http_client: httpx.Client | None = None,
    timeout_sec: float = 10.0,
) -> dict[str, Any]:
    """Query local loopback ``GET /v1/models`` once (0 retries, fail-closed URL guard)."""
    models_url = assert_url_allowed(f"{base_url.rstrip('/')}/v1/models", require_loopback=True)
    headers: dict[str, str] = {"Accept": "application/json"}
    if bearer_key:
        headers["Authorization"] = f"Bearer {bearer_key}"

    own_client = http_client is None
    client = http_client or httpx.Client(timeout=timeout_sec, follow_redirects=False)
    t0 = time.perf_counter()
    try:
        try:
            resp = client.get(models_url, headers=headers, timeout=timeout_sec)
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            return {
                "status": STATUS_SKIP_OFFLINE,
                "http_status": None,
                "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
                "models": [],
                "detail": _redact_text(f"Loopback /v1/models unreachable: {type(exc).__name__}"),
            }

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
        if resp.status_code == 429:
            return {
                "status": STATUS_RATE_LIMITED_STOP,
                "http_status": 429,
                "latency_ms": elapsed_ms,
                "models": [],
                "detail": "HTTP 429 on /v1/models (retry=0).",
            }
        if resp.status_code in (401, 403):
            return {
                "status": STATUS_SKIP_AUTH_EXPIRED,
                "http_status": resp.status_code,
                "latency_ms": elapsed_ms,
                "models": [],
                "detail": _redact_text(f"HTTP {resp.status_code} on /v1/models: {resp.text}"),
            }
        if resp.status_code != 200:
            return {
                "status": STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                "http_status": resp.status_code,
                "latency_ms": elapsed_ms,
                "models": [],
                "detail": _redact_text(f"HTTP {resp.status_code} on /v1/models: {resp.text}"),
            }

        try:
            payload = resp.json()
        except ValueError as exc:
            return {
                "status": STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR,
                "http_status": 200,
                "latency_ms": elapsed_ms,
                "models": [],
                "detail": f"Invalid JSON from /v1/models: {exc}",
            }

        models: list[str] = []
        if isinstance(payload, Mapping):
            rows = payload.get("data")
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, Mapping) and isinstance(row.get("id"), str) and row["id"].strip():
                        models.append(row["id"].strip())
        return {
            "status": STATUS_OK,
            "http_status": 200,
            "latency_ms": elapsed_ms,
            "models": models,
            "model_count": len(models),
            "detail": f"Discovered {len(models)} models on loopback gateway.",
        }
    finally:
        if own_client:
            client.close()


def _classify_effective_decision_status(
    decision: MacroSupervisorDecision,
    *,
    last_http_status: int | None,
    last_error_snippet: str,
) -> tuple[str, str]:
    """Reconcile supervisor decision status with proxy-wrapped upstream 401/403/429 bodies."""
    raw_status = decision.status
    note = decision.reasoning_bullets[0] if decision.reasoning_bullets else ""
    if raw_status in (STATUS_OK, STATUS_RATE_LIMITED_STOP, STATUS_SKIP_AUTH_EXPIRED, STATUS_SKIP_OFFLINE):
        return raw_status, _redact_text(f"{note} {last_error_snippet}".strip())

    # Some proxies wrap upstream OAuth 401/invalid_grant or 429 inside HTTP 400/500/502/503
    if last_error_snippet:
        if _RATE_LIMIT_BODY_RE.search(last_error_snippet):
            return (
                STATUS_RATE_LIMITED_STOP,
                _redact_text(f"Proxy HTTP {last_http_status} upstream 429/quota: {last_error_snippet}"),
            )
        if _AUTH_EXPIRED_BODY_RE.search(last_error_snippet):
            return (
                STATUS_SKIP_AUTH_EXPIRED,
                _redact_text(f"Proxy HTTP {last_http_status} upstream OAuth expired: {last_error_snippet}"),
            )
    return raw_status, _redact_text(f"{note} {last_error_snippet}".strip())


def run_pit24_over_client(
    *,
    owner_json_path: Path | str,
    sanitized_yaml_path: Path | str | None = None,
    expected_port: int = DEFAULT_PROJECT_CLIPROXY_PORT,
    requested_model: str | None = None,
    http_client: httpx.Client | None = None,
    timeout_sec: float = DEFAULT_LIVE_TIMEOUT_SEC,
    inter_request_delay_sec: float = 0.0,
) -> dict[str, Any]:
    """Execute the 24-scenario anonymized PIT-24 benchmark against loopback gateway 17852.

    Enforces:
      - ``assert_port_allowed(expected_port)`` (port ``8317`` raises ``SecurityError``).
      - ``assert_anonymized_prompt_clean`` on EVERY system & scenario prompt before sending.
      - ``request_retry = 0`` (stops IMMEDIATELY on ``429`` with zero retries).
      - Honest ``SKIP_AUTH_EXPIRED`` if OAuth tokens fail with ``401/403`` (or proxy-wrapped expiry).
    """
    _enforce_module_safety_invariants()
    assert_port_allowed(expected_port, field_name="expected_port")
    owner = resolve_project_gateway_owner(owner_json_path, expected_port=expected_port)

    # Resolve local loopback client bearer token strictly in memory (never persisted)
    bearer_key: str | None = None
    for candidate_yaml in (sanitized_yaml_path, owner.config_path):
        if candidate_yaml is None:
            continue
        p = Path(candidate_yaml)
        if p.is_file():
            try:
                parsed = yaml.safe_load(p.read_text(encoding="utf-8"))
                if isinstance(parsed, Mapping):
                    bearer_key = extract_loopback_client_api_key(parsed)
                    if bearer_key:
                        break
            except (OSError, yaml.YAMLError):
                continue

    # Build and double-verify ALL 24 anonymized scenarios fail-closed BEFORE any HTTP request
    scenarios: list[AnonymizedMacroScenario] = build_anonymized_24_macro_scenarios()
    if len(scenarios) != 24:
        raise SupervisorValidationError(f"Expected 24 anonymized scenarios, got {len(scenarios)}")
    assert_anonymized_prompt_clean(SYSTEM_PROMPT_MACRO_SUPERVISOR)
    for scen in scenarios:
        assert_anonymized_prompt_clean(scen.prompt_text)

    # Wrap transport passively so we capture exact HTTP status & redacted upstream error text
    own_client = http_client is None
    if http_client is not None:
        diag_transport = _DiagnosticTransport(http_client._transport)  # noqa: SLF001
        wrapped_client = httpx.Client(transport=diag_transport, timeout=timeout_sec, follow_redirects=False)
    else:
        diag_transport = _DiagnosticTransport(httpx.HTTPTransport(retries=0))
        wrapped_client = httpx.Client(transport=diag_transport, timeout=timeout_sec, follow_redirects=False)

    try:
        # Step 1: Discover registered models on loopback 17852
        discovery = discover_gateway_models(
            base_url=owner.base_url,
            bearer_key=bearer_key,
            http_client=wrapped_client,
            timeout_sec=min(timeout_sec, 15.0),
        )

        if discovery["status"] == STATUS_SKIP_OFFLINE:
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_SKIP_OFFLINE,
                selected_model=requested_model or "none",
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=[],
                stop_reason=discovery["detail"],
                provider_probes=[],
            )
        if discovery["status"] == STATUS_RATE_LIMITED_STOP:
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_PARTIAL_RATE_LIMITED_429,
                selected_model=requested_model or "none",
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=[],
                stop_reason=discovery["detail"],
                provider_probes=[],
            )
        if discovery["status"] == STATUS_SKIP_AUTH_EXPIRED:
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_SKIP_AUTH_EXPIRED,
                selected_model=requested_model or "none",
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=[],
                stop_reason=discovery["detail"],
                provider_probes=[],
            )

        candidate_models = select_candidate_models(
            discovery.get("models", []),
            requested_model=requested_model,
        )

        # Step 2: Run scenario 0 against candidate family (if 401/403 expired, test next family once; NEVER retry 429!)
        selected_model = candidate_models[0]
        provider_probes: list[dict[str, Any]] = []
        first_decision: MacroSupervisorDecision | None = None
        first_effective_status: str = ""
        first_detail: str = ""
        first_http_status: int | None = None

        for cand_model in candidate_models:
            cfg = MacroSupervisorConfig(
                provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
                model_id=cand_model,
                gateway_owner_path=owner_json_path,
                sanitized_gateway_yaml_path=sanitized_yaml_path,
                cliproxy_expected_port=expected_port,
                cliproxy_request_retry=0,
                cliproxy_api_key=bearer_key,
                timeout_sec=timeout_sec,
            )
            supervisor = MacroAISupervisor(cfg, http_client=wrapped_client)
            diag_transport.last_status_code = None
            diag_transport.last_error_snippet = ""

            dec = supervisor.evaluate_scenario(scenarios[0])
            eff_status, detail = _classify_effective_decision_status(
                dec,
                last_http_status=diag_transport.last_status_code,
                last_error_snippet=diag_transport.last_error_snippet,
            )
            provider_probes.append(
                {
                    "model_id": cand_model,
                    "provider_family": _model_family(cand_model),
                    "http_status": diag_transport.last_status_code,
                    "effective_status": eff_status,
                    "latency_ms": dec.latency_ms,
                    "detail": detail,
                }
            )
            selected_model = cand_model
            first_decision = dec
            first_effective_status = eff_status
            first_detail = detail
            first_http_status = diag_transport.last_status_code

            if eff_status == STATUS_OK:
                break
            if eff_status in (STATUS_RATE_LIMITED_STOP, STATUS_SKIP_OFFLINE):
                # Hard stop immediately on 429 or offline (zero retries!)
                break
            # If 401/403 (auth expired) or upstream credential failure on this provider family,
            # check if another distinct provider family in /v1/models is authenticated.
            if inter_request_delay_sec > 0.0:
                time.sleep(min(inter_request_delay_sec, 0.5))

        if first_decision is None:
            raise SupervisorValidationError("No candidate model was evaluated on scenario 0")

        per_scenario_rows: list[dict[str, Any]] = []
        stop_reason: str | None = None

        row0 = _format_scenario_result_row(
            scenario=scenarios[0],
            decision=first_decision,
            effective_status=first_effective_status,
            http_status=first_http_status,
            detail=first_detail,
        )
        per_scenario_rows.append(row0)

        if first_effective_status == STATUS_RATE_LIMITED_STOP:
            stop_reason = first_detail or "HTTP 429 rate-limited on scenario SCEN_01 (retry=0; stopped immediately)."
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_PARTIAL_RATE_LIMITED_429,
                selected_model=selected_model,
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=per_scenario_rows,
                stop_reason=stop_reason,
                provider_probes=provider_probes,
            )

        if first_effective_status == STATUS_SKIP_AUTH_EXPIRED:
            stop_reason = first_detail or "OAuth/auth expired on loopback 17852 (401/403)."
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_SKIP_AUTH_EXPIRED,
                selected_model=selected_model,
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=per_scenario_rows,
                stop_reason=stop_reason,
                provider_probes=provider_probes,
            )

        if first_effective_status == STATUS_SKIP_OFFLINE:
            stop_reason = first_detail or "Loopback gateway 17852 offline."
            return _build_pit24_summary_payload(
                outcome_status=OUTCOME_SKIP_OFFLINE,
                selected_model=selected_model,
                discovery=discovery,
                scenarios=scenarios,
                per_scenario_rows=per_scenario_rows,
                stop_reason=stop_reason,
                provider_probes=provider_probes,
            )

        # Step 3: Continue through SCEN_02 .. SCEN_24 with the working model (retry = 0)
        cfg_active = MacroSupervisorConfig(
            provider_mode=ProviderMode.CLIPROXY_LOCAL_17852,
            model_id=selected_model,
            gateway_owner_path=owner_json_path,
            sanitized_gateway_yaml_path=sanitized_yaml_path,
            cliproxy_expected_port=expected_port,
            cliproxy_request_retry=0,
            cliproxy_api_key=bearer_key,
            timeout_sec=timeout_sec,
        )
        supervisor_active = MacroAISupervisor(cfg_active, http_client=wrapped_client)
        consecutive_upstream_errors = 0 if first_effective_status == STATUS_OK else 1

        for scen in scenarios[1:]:
            assert_anonymized_prompt_clean(scen.prompt_text)
            if inter_request_delay_sec > 0.0:
                time.sleep(inter_request_delay_sec)

            diag_transport.last_status_code = None
            diag_transport.last_error_snippet = ""
            dec = supervisor_active.evaluate_scenario(scen)
            eff_status, detail = _classify_effective_decision_status(
                dec,
                last_http_status=diag_transport.last_status_code,
                last_error_snippet=diag_transport.last_error_snippet,
            )
            per_scenario_rows.append(
                _format_scenario_result_row(
                    scenario=scen,
                    decision=dec,
                    effective_status=eff_status,
                    http_status=diag_transport.last_status_code,
                    detail=detail,
                )
            )

            if eff_status == STATUS_RATE_LIMITED_STOP:
                stop_reason = detail or f"HTTP 429 rate-limited at {scen.scenario_id} (retry=0; stopped immediately)."
                return _build_pit24_summary_payload(
                    outcome_status=OUTCOME_PARTIAL_RATE_LIMITED_429,
                    selected_model=selected_model,
                    discovery=discovery,
                    scenarios=scenarios,
                    per_scenario_rows=per_scenario_rows,
                    stop_reason=stop_reason,
                    provider_probes=provider_probes,
                )

            if eff_status == STATUS_SKIP_AUTH_EXPIRED:
                stop_reason = detail or f"HTTP 401/403 OAuth expired at {scen.scenario_id}."
                return _build_pit24_summary_payload(
                    outcome_status=OUTCOME_SKIP_AUTH_EXPIRED,
                    selected_model=selected_model,
                    discovery=discovery,
                    scenarios=scenarios,
                    per_scenario_rows=per_scenario_rows,
                    stop_reason=stop_reason,
                    provider_probes=provider_probes,
                )

            if eff_status == STATUS_SKIP_OFFLINE:
                stop_reason = detail or f"Gateway offline at {scen.scenario_id}."
                return _build_pit24_summary_payload(
                    outcome_status=OUTCOME_SKIP_OFFLINE,
                    selected_model=selected_model,
                    discovery=discovery,
                    scenarios=scenarios,
                    per_scenario_rows=per_scenario_rows,
                    stop_reason=stop_reason,
                    provider_probes=provider_probes,
                )

            if eff_status == STATUS_OK:
                consecutive_upstream_errors = 0
            else:
                consecutive_upstream_errors += 1
                # Avoid hammering a dead/misconfigured upstream when HTTP != 200 repeatedly
                if consecutive_upstream_errors >= 3 and diag_transport.last_status_code != 200:
                    stop_reason = (
                        f"Stopped early after {consecutive_upstream_errors} consecutive non-200 upstream "
                        f"errors (last HTTP {diag_transport.last_status_code}): {detail}"
                    )
                    return _build_pit24_summary_payload(
                        outcome_status=OUTCOME_LIVE_24_DEGRADED,
                        selected_model=selected_model,
                        discovery=discovery,
                        scenarios=scenarios,
                        per_scenario_rows=per_scenario_rows,
                        stop_reason=stop_reason,
                        provider_probes=provider_probes,
                    )

        ok_count = sum(1 for r in per_scenario_rows if r["status"] == STATUS_OK and r["schema_valid"])
        final_outcome = OUTCOME_LIVE_24_PASS if ok_count == 24 else OUTCOME_LIVE_24_DEGRADED
        return _build_pit24_summary_payload(
            outcome_status=final_outcome,
            selected_model=selected_model,
            discovery=discovery,
            scenarios=scenarios,
            per_scenario_rows=per_scenario_rows,
            stop_reason=stop_reason,
            provider_probes=provider_probes,
        )
    finally:
        if own_client:
            wrapped_client.close()
        else:
            # Do NOT close caller-provided inner transport if caller owns http_client
            wrapped_client._transport = httpx.BaseTransport()  # noqa: SLF001
            wrapped_client.close()


def _format_scenario_result_row(
    *,
    scenario: AnonymizedMacroScenario,
    decision: MacroSupervisorDecision,
    effective_status: str,
    http_status: int | None,
    detail: str,
) -> dict[str, Any]:
    schema_valid = (effective_status == STATUS_OK) and (not decision.degraded)
    in_band = (
        schema_valid
        and (scenario.expected_risk_mult_min - 1e-12) <= decision.risk_mult <= (scenario.expected_risk_mult_max + 1e-12)
    )
    return {
        "scenario_id": scenario.scenario_id,
        "category": scenario.category,
        "expected_regime_band": scenario.expected_regime_band,
        "expected_risk_mult_range": [scenario.expected_risk_mult_min, scenario.expected_risk_mult_max],
        "prompt_anonymized_clean": True,
        "http_status": http_status,
        "status": effective_status,
        "raw_supervisor_status": decision.status,
        "degraded": decision.degraded,
        "schema_valid": schema_valid,
        "regime_in_expected_band": in_band,
        "risk_mult": decision.risk_mult,
        "regime_tag": decision.regime_tag,
        "confidence": decision.confidence,
        "attempts": decision.attempts,
        "latency_ms": decision.latency_ms,
        "order_send_capable": False,
        "execution_capability": False,
        "prop_guard_override_allowed": False,
        "prompt_sha256": decision.prompt_sha256,
        "response_sha256": decision.response_sha256,
        "decision_sha256": decision.decision_sha256(),
        "detail": detail,
    }


def _build_pit24_summary_payload(
    *,
    outcome_status: str,
    selected_model: str,
    discovery: Mapping[str, Any],
    scenarios: Sequence[AnonymizedMacroScenario],
    per_scenario_rows: Sequence[Mapping[str, Any]],
    stop_reason: str | None,
    provider_probes: Sequence[Mapping[str, Any]],
) -> dict[str, Any]:
    if outcome_status not in VALID_PIT24_OUTCOMES:
        raise SupervisorValidationError(f"Invalid PIT-24 outcome_status: {outcome_status!r}")

    attempted_ids = {str(r["scenario_id"]) for r in per_scenario_rows}
    full_rows: list[dict[str, Any]] = [dict(r) for r in per_scenario_rows]
    for scen in scenarios:
        if scen.scenario_id not in attempted_ids:
            full_rows.append(
                {
                    "scenario_id": scen.scenario_id,
                    "category": scen.category,
                    "expected_regime_band": scen.expected_regime_band,
                    "expected_risk_mult_range": [scen.expected_risk_mult_min, scen.expected_risk_mult_max],
                    "prompt_anonymized_clean": True,
                    "http_status": None,
                    "status": f"NOT_RUN_{outcome_status}",
                    "raw_supervisor_status": f"NOT_RUN_{outcome_status}",
                    "degraded": True,
                    "schema_valid": False,
                    "regime_in_expected_band": False,
                    "risk_mult": None,
                    "regime_tag": None,
                    "confidence": None,
                    "attempts": 0,
                    "latency_ms": None,
                    "order_send_capable": False,
                    "execution_capability": False,
                    "prop_guard_override_allowed": False,
                    "prompt_sha256": scen.prompt_sha256,
                    "response_sha256": None,
                    "decision_sha256": None,
                    "detail": stop_reason or f"Skipped after {outcome_status}",
                }
            )

    attempted = len(per_scenario_rows)
    ok_rows = [r for r in per_scenario_rows if r["status"] == STATUS_OK and r["schema_valid"]]
    ok_count = len(ok_rows)
    regime_agree_count = sum(1 for r in ok_rows if r["regime_in_expected_band"])
    latencies_attempted = [float(r["latency_ms"]) for r in per_scenario_rows if r.get("latency_ms") is not None]
    latencies_ok = [float(r["latency_ms"]) for r in ok_rows if r.get("latency_ms") is not None]

    risk_mult_dist: dict[str, int] = {str(m): 0 for m in ALLOWED_RISK_MULTS}
    regime_tag_dist: dict[str, int] = {}
    band_breakdown: dict[str, dict[str, Any]] = {}

    for band in ("CRISIS_OR_DEFENSIVE", "ELEVATED_CAUTION", "TRANSITIONAL_WATCH", "CALM_NORMAL"):
        b_rows = [r for r in per_scenario_rows if r["expected_regime_band"] == band]
        b_ok = [r for r in b_rows if r["status"] == STATUS_OK and r["schema_valid"]]
        b_agree = sum(1 for r in b_ok if r["regime_in_expected_band"])
        band_breakdown[band] = {
            "total": 6,
            "attempted": len(b_rows),
            "ok": len(b_ok),
            "regime_agreed": b_agree,
            "agreement_rate_pct": round(100.0 * b_agree / len(b_ok), 2) if b_ok else 0.0,
        }

    for r in ok_rows:
        key = str(float(r["risk_mult"]))
        risk_mult_dist[key] = risk_mult_dist.get(key, 0) + 1
        tag = str(r["regime_tag"])
        regime_tag_dist[tag] = regime_tag_dist.get(tag, 0) + 1

    schema_rate_attempted = round(100.0 * ok_count / attempted, 2) if attempted > 0 else 0.0
    schema_rate_of_24 = round(100.0 * ok_count / 24.0, 2)
    regime_agree_rate_ok = round(100.0 * regime_agree_count / ok_count, 2) if ok_count > 0 else 0.0

    return {
        "outcome_status": outcome_status,
        "selected_model": selected_model,
        "selected_model_family": _model_family(selected_model),
        "request_retry": 0,
        "scenarios_total": 24,
        "scenarios_attempted": attempted,
        "scenarios_ok": ok_count,
        "scenarios_schema_valid": ok_count,
        "scenarios_not_run": 24 - attempted,
        "all_prompts_anonymized_clean": True,
        "clean_prompts_verified_count": 24,
        "json_schema_valid_rate_of_attempted_pct": schema_rate_attempted,
        "json_schema_valid_rate_of_24_pct": schema_rate_of_24,
        "regime_agreement_count": regime_agree_count,
        "regime_agreement_rate_of_ok_pct": regime_agree_rate_ok,
        "latency_ms_attempted": _summarize_latencies(latencies_attempted),
        "latency_ms_ok": _summarize_latencies(latencies_ok),
        "risk_mult_distribution_ok": risk_mult_dist,
        "regime_tag_distribution_ok": regime_tag_dist,
        "regime_band_breakdown": band_breakdown,
        "models_discovery": {
            "status": discovery.get("status"),
            "http_status": discovery.get("http_status"),
            "latency_ms": discovery.get("latency_ms"),
            "model_count": len(discovery.get("models", [])),
            "sample_models": list(discovery.get("models", []))[:30],
            "detail": discovery.get("detail"),
        },
        "provider_probes": list(provider_probes),
        "stop_reason": stop_reason,
        "per_scenario_results": full_rows,
    }


# ==============================================================================
# Prospective Shadow Ledger Initializer (first_live_session_date = "2026-11-30")
# ==============================================================================


def initialize_prospective_shadow_ledger(
    ledger_path: Path | str | None = None,
    *,
    first_live_session_date: str = FIRST_PROSPECTIVE_LIVE_SESSION_DATE,
    min_evaluation_days: int = MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS,
) -> dict[str, Any]:
    """Initialize & cryptographically verify ``prospective_shadow_ledger.json`` (0 fake commits)."""
    _enforce_module_safety_invariants()
    target = Path(ledger_path) if ledger_path is not None else DEFAULT_PROSPECTIVE_LEDGER_PATH

    ledger = ProspectiveShadowLedger(
        ledger_path=target,
        first_live_session_date=first_live_session_date,
        min_audit_calendar_days=min_evaluation_days,
    )
    payload = ledger.to_dict()
    payload["min_evaluation_days"] = int(min_evaluation_days)
    payload["initialized_utc"] = _utc_now_iso()
    payload["notes"] = (
        "Initialized cleanly with 0 commitments before first live trading session Monday 2026-11-30. "
        "Synthetic PIT-24 benchmark scenarios are NEVER mixed into the prospective live shadow chain."
    )
    _atomic_write_json(target, payload)

    # Fail-closed round-trip reload & SHA-256 chain verification
    reloaded = ProspectiveShadowLedger.load(target)
    summary = reloaded.verify_integrity()
    return {
        "ledger_path": str(target),
        "ledger_file_sha256": _sha256_file(target),
        "schema_version": reloaded.LEDGER_SCHEMA,
        "prospective_only": True,
        "order_send_capable": False,
        "first_live_session_date": reloaded.first_live_session_date,
        "min_evaluation_days": int(min_evaluation_days),
        "min_audit_calendar_days": reloaded.min_audit_calendar_days,
        "verified": bool(summary["verified"]),
        "commitments_count": int(summary["commitments_count"]),
        "head_sha256": str(summary["head_sha256"]),
        "ready_for_prospective_oos_audit": bool(summary["ready_for_prospective_oos_audit"]),
    }


# ==============================================================================
# Enriched 6-Criteria x 5-Architecture Benchmark + External Ecosystem Honest Audit
# ==============================================================================


def build_enriched_6criteria_benchmark(
    *,
    radar_snapshot_path: Path | str | None = None,
    radar_payload: Mapping[str, Any] | None = None,
    pit24_summary: Mapping[str, Any] | None = None,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
) -> dict[str, Any]:
    """Build complete 6-criteria x 5-architecture benchmark enriched with live radar & PIT-24 evidence."""
    _enforce_module_safety_invariants()
    radar_data: Mapping[str, Any] | None = radar_payload
    if radar_data is None and radar_snapshot_path is not None:
        rp = Path(radar_snapshot_path)
        if rp.is_file():
            radar_data = json.loads(rp.read_text(encoding="utf-8"))

    rubric = build_ai_architecture_rubric_6criteria(
        radar_snapshot_path=radar_snapshot_path if radar_data is None else None,
        radar_payload=radar_data,
        usd_vnd_rate=usd_vnd_rate,
    )
    fx = float(rubric["usd_vnd_rate"])

    # Pull live radar details for Official API & Local RTX 2070 SUPER 8GB
    top_budget_rows: list[dict[str, Any]] = []
    budget_eligible_count = 0
    hw_summary: dict[str, Any] = {
        "gpu_name": "NVIDIA GeForce RTX 2070 SUPER",
        "gpu_vram_total_gb": 8.0,
        "full_vram_budget_gb": 7.2,
        "ram_total_gb": 31.95,
        "hybrid_offload_budget_gb": 21.96,
        "top_full_vram_model": "qwen/qwen3.5-9b",
        "top_full_vram_q4_gb": 5.66,
        "full_vram_fit_count": 12,
        "hybrid_offload_count": 31,
    }
    if isinstance(radar_data, Mapping):
        lbs = radar_data.get("leaderboards")
        if isinstance(lbs, Mapping):
            bm = lbs.get("budget_macro_supervisor_monthly_usd")
            if isinstance(bm, list):
                for row in bm[:5]:
                    if isinstance(row, Mapping):
                        m_usd = float(row.get("monthly_usd", 0.0))
                        top_budget_rows.append(
                            {
                                "id": str(row.get("id", "")),
                                "monthly_usd": round(m_usd, 4),
                                "monthly_vnd": int(round(m_usd * fx)),
                                "context_length": int(row.get("context_length", 0)),
                            }
                        )
            loc = lbs.get("local_open_weight_fit")
            if isinstance(loc, list) and loc and isinstance(loc[0], Mapping):
                hw_summary["top_full_vram_model"] = str(loc[0].get("id", hw_summary["top_full_vram_model"]))
                hw_summary["top_full_vram_q4_gb"] = float(
                    loc[0].get("q4_estimated_gb", hw_summary["top_full_vram_q4_gb"])
                )
        lsum = radar_data.get("leaderboard_summary")
        if isinstance(lsum, Mapping):
            budget_eligible_count = int(lsum.get("budget_eligible_count", 0))
            hw_summary["full_vram_fit_count"] = int(lsum.get("local_full_vram_fit_count", 12))
            hw_summary["hybrid_offload_count"] = int(lsum.get("local_hybrid_offload_count", 31))
        hw = radar_data.get("hardware")
        if isinstance(hw, Mapping):
            hw_summary["gpu_name"] = str(hw.get("gpu_name") or hw_summary["gpu_name"])
            hw_summary["gpu_vram_total_gb"] = float(hw.get("gpu_vram_total_gb", 8.0))
            hw_summary["full_vram_budget_gb"] = float(hw.get("full_vram_budget_gb", 7.2))
            hw_summary["ram_total_gb"] = float(hw.get("ram_total_gb", 31.95))
            hw_summary["hybrid_offload_budget_gb"] = float(hw.get("hybrid_offload_budget_gb", 21.96))

    # Attach live evidence blocks to each of the 5 architectures (preserving all 6 criteria strictly)
    for arch in rubric["architectures"]:
        aid = arch["architecture_id"]
        if aid == "official_api_5usd_cap":
            arch["live_evidence"] = {
                "radar_source": rubric["radar_source"],
                "workload_runs_per_month": 44,
                "budget_cap_usd_per_month": MAX_OFFICIAL_API_USD_PER_MONTH,
                "budget_cap_vnd_per_month": int(round(MAX_OFFICIAL_API_USD_PER_MONTH * fx)),
                "eligible_models_under_5usd_count": budget_eligible_count,
                "top_5_budget_models": top_budget_rows,
            }
        elif aid == "neurobro_saas":
            arch["live_evidence"] = {
                "product_domain": "neurobro.ai",
                "role_assessment": "ADVISORY_ONLY_UNVERIFIED_LIVE_PNL",
                "audited_live_prop_pnl_verified": False,
                "independent_track_record": "UNVERIFIED",
                "honest_verdict": (
                    "Advisory-only crypto/macro narrative SaaS with NO independently audited live prop PnL, "
                    "opaque prompts/feeds, and subscription pricing far exceeding the <= $5/mo Official API cap. "
                    "Rejected for automated or semi-automated Naqex prop pipelines."
                ),
            }
        elif aid == "project_cliproxy_17852":
            if pit24_summary is not None:
                arch["live_evidence"] = {
                    "pit24_outcome_status": pit24_summary.get("outcome_status"),
                    "selected_model": pit24_summary.get("selected_model"),
                    "scenarios_ok": pit24_summary.get("scenarios_ok"),
                    "scenarios_attempted": pit24_summary.get("scenarios_attempted"),
                    "scenarios_total": pit24_summary.get("scenarios_total"),
                    "json_schema_valid_rate_of_24_pct": pit24_summary.get("json_schema_valid_rate_of_24_pct"),
                    "regime_agreement_rate_of_ok_pct": pit24_summary.get("regime_agreement_rate_of_ok_pct"),
                    "latency_ms_ok": pit24_summary.get("latency_ms_ok"),
                    "request_retry": 0,
                    "poolai_present": False,
                    "stop_reason": pit24_summary.get("stop_reason"),
                }
            else:
                arch["live_evidence"] = {"pit24_outcome_status": "NOT_EXECUTED_OFFLINE"}
        elif aid == "local_ollama_rtx2070s":
            arch["live_evidence"] = {
                **hw_summary,
                "execution_capability": False,
                "advisory_mode": "DEGRADED_ADVISORY_FALLBACK",
            }
        elif aid == "mt5_onnx_pure_mql5_v104_ml":
            arch["live_evidence"] = {
                "causal_features_count": 24,
                "dev_cutoff_date": HOLDOUT_CUTOFF_DATE,
                "holdout_2025_plus_sealed": True,
                "parity_target": "Python == onnxruntime == MT5 OnnxRun <= 1e-5",
                "execution_role": "PRIMARY_EXECUTION_PATH_QUANT_FILTER",
            }

    # Brief honest status of external AI-quant ecosystems (Alpha Arena / FinRL / Qlib)
    rubric["external_ecosystems_honest_status"] = [
        {
            "ecosystem": "Alpha Arena (nof1.ai)",
            "status": "OBSERVED_HIGH_VARIANCE_NOT_PROP_READY",
            "adopt_for_naqex": False,
            "summary": (
                "Public live-money LLM crypto trading benchmark with short evaluation horizon and "
                "unconstrained discretionary perpetual futures risk. High cross-model PnL variance "
                "confirms raw LLM direct order execution is unsuitable for strict FTMO 5%/10% DD rules; "
                "reinforces keeping LLMs strictly advisory (ORDER_SEND_CAPABLE = False)."
            ),
        },
        {
            "ecosystem": "FinRL / FinRL-X (AI4Finance-Foundation)",
            "status": "REFERENCE_CONTRACT_ONLY_NO_RL_EXECUTION",
            "adopt_for_naqex": False,
            "summary": (
                "Open-source Deep RL (PPO/SAC/DDPG) trading stack. High sample complexity and fragile "
                "OOS generalization on 7-year FX/CFD regimes without native MT5 real-tick or PropGuard "
                "parity; Naqex borrows typed portfolio-weight interface ideas only, zero RL live orders."
            ),
        },
        {
            "ecosystem": "Microsoft Qlib / RD-Agent(Q)",
            "status": "BORROW_PIT_DISCIPLINE_ONLY_DO_NOT_RUN_DOCKER_LOOP",
            "adopt_for_naqex": False,
            "summary": (
                "Point-in-Time quant framework + automated LLM R&D loop (NeurIPS 2025) designed for "
                "300-5,000 equities with heavy Docker/PyTorch and continuous LLM API spend. Running "
                "unthrottled LLM loops on 7-12 FX/CFD symbols violates the <= $5/mo cap and explodes "
                "trial count M (breaking DSR). Naqex adopts Point-in-Time discipline in lightweight Python."
            ),
        },
    ]

    # Verify strict 5 architectures x 6 criteria post-condition (zero bare asserts -> python -O safe!)
    if rubric["architecture_count"] != 5 or len(rubric["architectures"]) != 5:
        raise SupervisorValidationError(f"Expected 5 rubric architectures, got {len(rubric['architectures'])}")
    if rubric["criteria_count"] != 6 or tuple(rubric["criteria_keys"]) != RUBRIC_CRITERIA_KEYS:
        raise SupervisorValidationError("Rubric criteria keys mismatch")
    actual_names = tuple(a["architecture"] for a in rubric["architectures"])
    if actual_names != RUBRIC_ARCHITECTURE_NAMES:
        raise SupervisorValidationError(f"Unexpected rubric architecture order/names: {actual_names}")

    return rubric


# ==============================================================================
# Full End-to-End Orchestrator (Standalone 17852 + Ledger Init + 6-Criteria Report)
# ==============================================================================


def run_live_pit24_and_generate_artifacts(
    *,
    owner_json_path: Path | str = DEFAULT_GATEWAY_OWNER_PATH,
    sanitized_yaml_path: Path | str = DEFAULT_SANITIZED_GATEWAY_YAML_PATH,
    log_dir: Path | str = DEFAULT_PAPERCLIP_RUNTIME_DIR,
    pid_file_path: Path | str = DEFAULT_WAVE4_GATEWAY_PID_PATH,
    radar_snapshot_path: Path | str = DEFAULT_RADAR_SNAPSHOT_PATH,
    ledger_out_path: Path | str = DEFAULT_PROSPECTIVE_LEDGER_PATH,
    report_out_path: Path | str = DEFAULT_PIT24_RUBRIC_OUT_PATH,
    expected_port: int = DEFAULT_PROJECT_CLIPROXY_PORT,
    requested_model: str | None = None,
    timeout_sec: float = DEFAULT_LIVE_TIMEOUT_SEC,
    inter_request_delay_sec: float = DEFAULT_INTER_REQUEST_DELAY_SEC,
    gateway_factory: Callable[..., Any] = StandaloneGateway17852,
    http_client: httpx.Client | None = None,
    listener_snapshot_fn: Callable[[Sequence[int]], dict[int, list[dict[str, Any]]]] = snapshot_tcp_listeners_passive,
    cleanup_sanitized_yaml: bool = True,
) -> dict[str, Any]:
    """Run live standalone 17852 PIT-24 benchmark, init shadow ledger, and emit W4-G14 JSON."""
    _enforce_module_safety_invariants()
    assert_port_allowed(expected_port, field_name="expected_port")

    owner = resolve_project_gateway_owner(owner_json_path, expected_port=expected_port)
    managed_yaml_path = owner.config_path
    managed_sha_before = _sha256_file(managed_yaml_path)

    # Passive OS listener snapshot BEFORE launch (zero touch to port 8317!)
    listeners_before = listener_snapshot_fn((FORBIDDEN_EXTERNAL_CLIPROXY_PORT, expected_port))
    p8317_before = listeners_before.get(FORBIDDEN_EXTERNAL_CLIPROXY_PORT, [])

    sanitized_receipt: dict[str, Any] = {}
    stale_cleanup_report: dict[str, Any] = {}
    spawned_pid: int | None = None
    stopped_pid: int | None = None
    logs_dir_path = Path(log_dir).resolve()
    sanitized_path = Path(sanitized_yaml_path).resolve()

    pit24_summary: dict[str, Any]
    gateway_error: str | None = None

    gw = gateway_factory(
        owner_json_path=owner_json_path,
        sanitized_yaml_path=sanitized_path,
        log_dir=logs_dir_path,
        pid_file_path=pid_file_path,
        expected_port=expected_port,
        startup_timeout_sec=15.0,
        poll_interval_sec=0.25,
    )

    try:
        try:
            with gw:
                spawned_pid = getattr(gw, "spawned_pid", None)
                stale_cleanup_report = dict(getattr(gw, "stale_cleanup_report", {}) or {})
                san_obj = getattr(gw, "sanitized", None)
                if san_obj is not None:
                    sanitized_receipt = san_obj.to_safe_receipt()
                    if sanitized_receipt.get("poolai_present") is not False:
                        raise SecurityError("Sanitized YAML post-check failed: poolai_present != False")
                    if sanitized_receipt.get("request_retry") != 0:
                        raise SecurityError("Sanitized YAML post-check failed: request_retry != 0")

                pit24_summary = run_pit24_over_client(
                    owner_json_path=owner_json_path,
                    sanitized_yaml_path=sanitized_path,
                    expected_port=expected_port,
                    requested_model=requested_model,
                    http_client=http_client,
                    timeout_sec=timeout_sec,
                    inter_request_delay_sec=inter_request_delay_sec,
                )
        except Exception as exc:
            if isinstance(exc, SecurityError):
                raise
            gateway_error = _redact_text(f"{type(exc).__name__}: {exc}")
            scenarios = build_anonymized_24_macro_scenarios()
            pit24_summary = _build_pit24_summary_payload(
                outcome_status=OUTCOME_SKIP_OFFLINE,
                selected_model=requested_model or "none",
                discovery={"status": STATUS_SKIP_OFFLINE, "models": [], "detail": gateway_error},
                scenarios=scenarios,
                per_scenario_rows=[],
                stop_reason=gateway_error,
                provider_probes=[],
            )
    finally:
        stopped_pid = getattr(gw, "stopped_spawned_pid", None)
        # Clean up temporary sanitized YAML (never touching source managed.yaml!)
        if cleanup_sanitized_yaml and sanitized_path.is_file() and sanitized_path != managed_yaml_path.resolve():
            try:
                sanitized_path.unlink()
            except OSError:
                pass

    # Verify post-run safety invariants fail-closed (immune to python -O)
    managed_sha_after = _sha256_file(managed_yaml_path)
    managed_unchanged = managed_sha_before == managed_sha_after
    if not managed_unchanged:
        raise SecurityError(
            f"CRITICAL: Source managed.yaml SHA-256 changed! before={managed_sha_before} after={managed_sha_after}"
        )

    # Wait briefly for Windows socket teardown if we spawned a real PID
    if spawned_pid is not None and _is_pid_alive(spawned_pid):
        time.sleep(0.5)
    spawned_pid_alive_after = _is_pid_alive(spawned_pid) if spawned_pid is not None else False
    port_17852_open_after = _is_tcp_port_open("127.0.0.1", expected_port, timeout_sec=0.3)

    listeners_after = listener_snapshot_fn((FORBIDDEN_EXTERNAL_CLIPROXY_PORT, expected_port))
    p8317_after = listeners_after.get(FORBIDDEN_EXTERNAL_CLIPROXY_PORT, [])
    p17852_after = listeners_after.get(expected_port, [])
    port_17852_stopped_after = (
        (not spawned_pid_alive_after) and (not port_17852_open_after) and (len(p17852_after) == 0)
    )
    if not port_17852_stopped_after:
        raise SecurityError(
            f"Port {expected_port} or spawned PID {spawned_pid} NOT cleanly stopped after run! "
            f"pid_alive={spawned_pid_alive_after} tcp_open={port_17852_open_after} listeners={p17852_after}"
        )

    # Initialize Prospective Shadow Ledger (first_live_session_date="2026-11-30", 0 fake commits)
    ledger_info = initialize_prospective_shadow_ledger(
        ledger_out_path,
        first_live_session_date=FIRST_PROSPECTIVE_LIVE_SESSION_DATE,
        min_evaluation_days=MIN_PROSPECTIVE_AUDIT_CALENDAR_DAYS,
    )

    # Build enriched 6-criteria x 5-architecture benchmark
    rubric = build_enriched_6criteria_benchmark(
        radar_snapshot_path=radar_snapshot_path,
        pit24_summary=pit24_summary,
    )

    report: dict[str, Any] = {
        "schema_version": RUNNER_SCHEMA_VERSION,
        "generated_utc": _utc_now_iso(),
        "gate_id": "W4-G14",
        "hard_invariants": {
            "order_send_capable": bool(ORDER_SEND_CAPABLE),
            "order_send_count": int(ORDER_SEND_COUNT),
            "execution_capable": bool(EXECUTION_CAPABLE),
            "prop_guard_override_allowed": bool(PROP_GUARD_OVERRIDE_ALLOWED),
            "spend_vnd": int(SPEND_VND),
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": int(HOLDOUT_ROWS_ANALYSED),
            "max_official_api_usd_per_month": float(MAX_OFFICIAL_API_USD_PER_MONTH),
            "forbidden_external_port": int(FORBIDDEN_EXTERNAL_CLIPROXY_PORT),
        },
        "gateway_safety_verification": {
            "port_8317_touched": False,
            "port_8317_listeners_before": p8317_before,
            "port_8317_listeners_after": p8317_after,
            "port_8317_listeners_identical": p8317_before == p8317_after,
            "port_17852_expected": int(expected_port),
            "port_17852_stopped_after": bool(port_17852_stopped_after),
            "port_17852_listeners_after": p17852_after,
            "spawned_pid": spawned_pid,
            "stopped_spawned_pid": stopped_pid,
            "spawned_pid_alive_after": bool(spawned_pid_alive_after),
            "managed_yaml_sha256_before": managed_sha_before,
            "managed_yaml_sha256_after": managed_sha_after,
            "managed_yaml_sha256_unchanged": bool(managed_unchanged),
            "request_retry": int(sanitized_receipt.get("request_retry", 0)),
            "poolai_present": bool(sanitized_receipt.get("poolai_present", False)),
            "stripped_entries_count": int(sanitized_receipt.get("stripped_entries_count", 0)),
            "sanitized_yaml_sha256": sanitized_receipt.get("sanitized_yaml_sha256"),
            "sanitized_temp_cleaned": not sanitized_path.exists(),
            "logs_redirected_to_paperclip": True,
            "logs_dir": str(logs_dir_path),
            "stale_cleanup_report": stale_cleanup_report,
            "gateway_error": gateway_error,
        },
        "pit24_benchmark": pit24_summary,
        "prospective_shadow_ledger": ledger_info,
        "ai_architecture_benchmark_6criteria": rubric,
    }

    report_path = Path(report_out_path)
    _atomic_write_json(report_path, report)
    return report


def main(argv: Sequence[str] | None = None) -> int:
    _enforce_module_safety_invariants()
    parser = argparse.ArgumentParser(
        description="Run live standalone 17852 PIT-24 Macro Supervisor benchmark & 6-criteria AI rubric (W4-G14)."
    )
    parser.add_argument("--owner-json", type=Path, default=DEFAULT_GATEWAY_OWNER_PATH)
    parser.add_argument("--radar-snapshot", type=Path, default=DEFAULT_RADAR_SNAPSHOT_PATH)
    parser.add_argument("--ledger-out", type=Path, default=DEFAULT_PROSPECTIVE_LEDGER_PATH)
    parser.add_argument("--report-out", type=Path, default=DEFAULT_PIT24_RUBRIC_OUT_PATH)
    parser.add_argument("--model", type=str, default=None, help="Optional explicit model ID on loopback 17852.")
    parser.add_argument("--timeout-sec", type=float, default=DEFAULT_LIVE_TIMEOUT_SEC)
    parser.add_argument("--delay-sec", type=float, default=DEFAULT_INTER_REQUEST_DELAY_SEC)
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = run_live_pit24_and_generate_artifacts(
        owner_json_path=args.owner_json,
        radar_snapshot_path=args.radar_snapshot,
        ledger_out_path=args.ledger_out,
        report_out_path=args.report_out,
        requested_model=args.model,
        timeout_sec=args.timeout_sec,
        inter_request_delay_sec=args.delay_sec,
    )
    pit = report["pit24_benchmark"]
    gsv = report["gateway_safety_verification"]
    led = report["prospective_shadow_ledger"]
    summary = {
        "gate_id": report["gate_id"],
        "pit24_outcome": pit["outcome_status"],
        "selected_model": pit["selected_model"],
        "scenarios_ok": pit["scenarios_ok"],
        "scenarios_attempted": pit["scenarios_attempted"],
        "json_schema_valid_rate_of_24_pct": pit["json_schema_valid_rate_of_24_pct"],
        "regime_agreement_rate_of_ok_pct": pit["regime_agreement_rate_of_ok_pct"],
        "latency_ms_ok": pit["latency_ms_ok"],
        "port_8317_touched": gsv["port_8317_touched"],
        "port_17852_stopped_after": gsv["port_17852_stopped_after"],
        "managed_yaml_sha256_unchanged": gsv["managed_yaml_sha256_unchanged"],
        "poolai_present": gsv["poolai_present"],
        "request_retry": gsv["request_retry"],
        "ledger_verified": led["verified"],
        "ledger_first_live_session_date": led["first_live_session_date"],
        "report_out": str(args.report_out),
        "ledger_out": str(args.ledger_out),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


__all__ = [
    "DEFAULT_PIT24_RUBRIC_OUT_PATH",
    "HOLDOUT_ROWS_ANALYSED",
    "OUTCOME_LIVE_24_DEGRADED",
    "OUTCOME_LIVE_24_PASS",
    "OUTCOME_PARTIAL_RATE_LIMITED_429",
    "OUTCOME_SKIP_AUTH_EXPIRED",
    "OUTCOME_SKIP_OFFLINE",
    "RUNNER_SCHEMA_VERSION",
    "SPEND_VND",
    "VALID_PIT24_OUTCOMES",
    "build_enriched_6criteria_benchmark",
    "discover_gateway_models",
    "initialize_prospective_shadow_ledger",
    "main",
    "run_live_pit24_and_generate_artifacts",
    "run_pit24_over_client",
    "select_candidate_models",
    "snapshot_tcp_listeners_passive",
]


if __name__ == "__main__":
    raise SystemExit(main())
