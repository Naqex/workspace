"""Fail-Closed, Pure-Stdlib TypeSafe System One (`jev-1.14.0`) Client for Naqex Workspace.

Design invariants (per `typesafe-ai` skill & Naqex fail-closed architecture):
  - ZERO external SDK dependencies (pure stdlib `urllib.request`, `json`, `os`, `time`).
  - Pinned model version (`jev-1.14.0`) — never drifts silently with moving aliases.
  - Opt-in ONLY: reads `TYPESAFE_API_KEY` from environment when explicitly invoked;
    never logs, returns, or persists credentials.
  - Fail-closed error handling: API/network/429/4xx failures raise `TypeSafeUnavailableError`
    or `TypeSafeAPIError` — NEVER coerced into `False` / "no" / safe pass.
  - Strict input sanitizer: blocks any nested key carrying credentials, broker commands,
    or sealed Holdout 2025+ data before a single byte leaves localhost.
  - `ORDER_SEND_CAPABLE = False`: zero broker/MT5/exchange imports or execution hooks.
"""

from __future__ import annotations

from collections import deque
import json
import math
import os
import re
import time
from typing import Any, Callable, Mapping
import urllib.error
import urllib.request

API_URL = "https://api.typesafe.ai/v1/systemone"
MODELS_URL = "https://api.typesafe.ai/v1/models"
DEFAULT_MODEL = "jev-1.14.0"
PRICE_PER_MTOK_USD = 0.042  # Input tokens only; output tokens are free per docs.typesafe.ai/models
MAX_PAYLOAD_BYTES = 262_144
ORDER_SEND_CAPABLE = False

FORBIDDEN_STATE_KEYS = frozenset({
    "api_key",
    "access_token",
    "authorization",
    "broker_credentials",
    "broker_request",
    "broker_action",
    "holdout_bars",
    "holdout_content",
    "future_bars",
    "future_events",
    "password",
    "private_key",
    "secret",
    "live_order",
    "order_send",
    "place_order",
    "close_position",
    "modify_order",
    "cancel_order",
    "typesafe_api_key",
})


class TypeSafeError(RuntimeError):
    """Base error for TypeSafe System One client failures."""


class TypeSafeUnavailableError(TypeSafeError):
    """Raised when `TYPESAFE_API_KEY` is missing or the service is unreachable."""


class TypeSafeAPIError(TypeSafeError):
    """Raised when TypeSafe returns HTTP 4xx/5xx or malformed JSON."""


class TypeSafeUnsafeStateError(TypeSafeError):
    """Raised when caller attempts to send forbidden credentials, broker, or holdout keys."""


def _normalize_key(key: Any) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(key).strip().lower()).strip("_")


def validate_safe_state(value: Any, *, max_bytes: int = MAX_PAYLOAD_BYTES) -> None:
    """Iteratively validate JSON safety and block forbidden secret/holdout/execution keys."""
    pending: deque[tuple[str, Any]] = deque([("state", value)])
    while pending:
        path, cur = pending.pop()
        if isinstance(cur, Mapping):
            for k, v in cur.items():
                if _normalize_key(k) in FORBIDDEN_STATE_KEYS:
                    raise TypeSafeUnsafeStateError(f"Forbidden key in TypeSafe state: {path}.{k}")
                pending.append((f"{path}.{k}", v))
        elif isinstance(cur, (list, tuple)):
            for idx, item in enumerate(cur):
                pending.append((f"{path}[{idx}]", item))
        elif isinstance(cur, float) and not math.isfinite(cur):
            raise TypeSafeUnsafeStateError(f"Non-finite float in TypeSafe state: {path}")
        elif isinstance(cur, bytes):
            raise TypeSafeUnsafeStateError(f"Raw bytes not allowed in TypeSafe state: {path}")

    try:
        encoded = json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8")
    except (TypeError, ValueError, RecursionError) as exc:
        raise TypeSafeUnsafeStateError("TypeSafe state must be finite JSON") from exc
    if len(encoded) > max_bytes:
        raise TypeSafeUnsafeStateError(f"TypeSafe state exceeds max_bytes ({len(encoded)} > {max_bytes})")


def get_api_key(env_var: str = "TYPESAFE_API_KEY") -> str:
    """Fetch API key strictly from process environment; never reads files or logs value."""
    key = os.environ.get(env_var, "").strip()
    if not key:
        raise TypeSafeUnavailableError(
            f"Missing environment variable `{env_var}`; TypeSafe calls are opt-in and fail-closed."
        )
    return key


def estimate_cost_usd(input_tokens: int) -> float:
    return round((max(0, int(input_tokens)) / 1_000_000.0) * PRICE_PER_MTOK_USD, 8)


def call_system_one(
    state: Any,
    questions: Mapping[str, Mapping[str, Any]],
    *,
    model: str = DEFAULT_MODEL,
    assets: Mapping[str, Mapping[str, Any]] | None = None,
    enable_images: bool = False,
    long_context: bool = False,
    timeout_sec: float = 25.0,
    api_key: str | None = None,
    transport: Callable[..., dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Execute one batched `POST /v1/systemone` judgment request (or invoke injected test transport).

    Returns:
      {
        "model": "<versioned_model_id>",
        "answers": { ... },
        "usage": {"input_tokens": int, "output_tokens": int},
        "latency_ms": float,
        "est_cost_usd": float,
      }
    """
    if not questions:
        raise TypeSafeAPIError("questions must contain at least one typed question")
    validate_safe_state(state)

    payload: dict[str, Any] = {
        "model": str(model or DEFAULT_MODEL),
        "state": state,
        "questions": dict(questions),
    }
    if assets:
        payload["assets"] = dict(assets)

    if transport is not None:
        t0 = time.perf_counter()
        raw = transport(payload, enable_images=enable_images, long_context=long_context, timeout_sec=timeout_sec)
        if not isinstance(raw, Mapping) or "answers" not in raw:
            raise TypeSafeAPIError("Injected TypeSafe transport returned malformed response (missing answers)")
        usage = dict(raw.get("usage") or {})
        in_tok = int(usage.get("input_tokens") or 0)
        return {
            "model": str(raw.get("model") or payload["model"]),
            "answers": dict(raw["answers"]),
            "usage": usage,
            "latency_ms": round((time.perf_counter() - t0) * 1000.0, 2),
            "est_cost_usd": estimate_cost_usd(in_tok),
        }

    key = (api_key or "").strip() or get_api_key()
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    if enable_images:
        headers["TypeSafe-Danger-Zone-Images"] = "true"
    if long_context:
        headers["TypeSafe-Danger-Zone-Long-Context"] = "true"

    req = urllib.request.Request(
        API_URL,
        data=json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    t0 = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=float(timeout_sec)) as resp:
            raw_bytes = resp.read()
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")[:300]
        if exc.code in (401, 403, 429, 502, 503, 504):
            raise TypeSafeUnavailableError(f"TypeSafe HTTP {exc.code}: {body}") from exc
        raise TypeSafeAPIError(f"TypeSafe HTTP {exc.code}: {body}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise TypeSafeUnavailableError(f"TypeSafe network/timeout error: {exc}") from exc

    latency_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    try:
        parsed = json.loads(raw_bytes.decode("utf-8"))
    except ValueError as exc:
        raise TypeSafeAPIError("TypeSafe returned invalid JSON") from exc

    if not isinstance(parsed, dict) or not isinstance(parsed.get("answers"), dict):
        raise TypeSafeAPIError("TypeSafe response missing `answers` object")

    usage = dict(parsed.get("usage") or {})
    in_tok = int(usage.get("input_tokens") or 0)
    return {
        "model": str(parsed.get("model") or payload["model"]),
        "answers": parsed["answers"],
        "usage": usage,
        "latency_ms": latency_ms,
        "est_cost_usd": estimate_cost_usd(in_tok),
    }


def extract_noul(answers: Mapping[str, Any], qid: str) -> float:
    """Strictly extract a calibrated Noul probability in [0.0, 1.0]."""
    item = answers.get(qid)
    if not isinstance(item, Mapping) or "noul" not in item:
        raise TypeSafeAPIError(f"Missing noul answer for question `{qid}`")
    val = float(item["noul"])
    if not math.isfinite(val) or val < 0.0 or val > 1.0:
        raise TypeSafeAPIError(f"Out-of-range noul probability for `{qid}`: {val}")
    return val


def classify_noul(prob: float, *, yes_threshold: float = 0.70, no_threshold: float = 0.30) -> str:
    """Map calibrated Noul probability into explicit 3-way state: YES / NO / UNCERTAIN."""
    if prob >= yes_threshold:
        return "YES"
    if prob <= no_threshold:
        return "NO"
    return "UNCERTAIN"
