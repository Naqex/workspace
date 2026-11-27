"""Realtime self-updating AI Model Radar with local hardware fit & price delta tracking (W4-G13).

Hard invariants (Total Offensive #4 v4.8.1 FINAL):
  - ORDER_SEND_CAPABLE = False (OrderSend = 0, offline research/radar only, 0 VND live spend)
  - HOLDOUT_CUTOFF_DATE = "2024-12-31" (Holdout 2025+ SEALED, holdout_rows_analysed = 0)
  - MAX_OFFICIAL_API_USD_PER_MONTH = 5.0 (strict monthly Macro Supervisor API cap)
  - Never hardcodes or logs API secrets; never contacts external local proxy ports.
  - All Windows subprocess probes pass ``creationflags=_NO_WINDOW_FLAGS`` to prevent console flash.
"""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import re
import subprocess
import sys
import tempfile
import time
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import httpx

try:
    import psutil  # type: ignore[import-untyped]
except Exception:  # pragma: no cover - optional runtime dependency
    psutil = None  # type: ignore[assignment]

from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)

# ==============================================================================
# Constants & Canonical Contracts
# ==============================================================================

SCHEMA_VERSION: str = "naqex-wave4-ai-model-radar-v1"
OPENROUTER_MODELS_URL: str = "https://openrouter.ai/api/v1/models"
ARTIFICIAL_ANALYSIS_MODELS_URL: str = "https://artificialanalysis.ai/api/v2/data/llms/models"
ARTIFICIAL_ANALYSIS_ENV_VAR: str = "ARTIFICIAL_ANALYSIS_API_KEY"
HF_LIVEBENCH_URL: str = "https://huggingface.co/api/datasets/livebench/model_judgment"
HF_LMARENA_URL: str = "https://huggingface.co/api/spaces/lmarena-ai/chatbot-arena-leaderboard"

DEFAULT_HTTP_TIMEOUT_SEC: float = 15.0
SECONDARY_HTTP_TIMEOUT_SEC: float = 10.0
DEFAULT_HTTP_RETRIES: int = 1
DEFAULT_RETRY_BACKOFF_SEC: float = 0.5

# Macro Supervisor workload budget (W4-G13): 44 runs/month = 350K input + 70K output tokens
SUPERVISOR_RUNS_PER_MONTH: int = 44
SUPERVISOR_MONTHLY_INPUT_TOKENS: int = 350_000
SUPERVISOR_MONTHLY_OUTPUT_TOKENS: int = 70_000
DEFAULT_USD_VND_RATE: float = 25_500.0
DEFAULT_TOP_N: int = 15

# Windows windowless subprocess creation flag (0 on POSIX where CPython accepts 0 cleanly)
_NO_WINDOW_FLAGS: int = int(getattr(subprocess, "CREATE_NO_WINDOW", 0)) if os.name == "nt" else 0

# Local quantization memory footprints (GB per 1B parameters + fixed KV/runtime overhead)
Q4_GB_PER_BILLION: float = 0.5625  # ~4.5 bits/weight (Q4_K_M)
Q8_GB_PER_BILLION: float = 1.0625  # ~8.5 bits/weight (Q8_0)
LOCAL_RUNTIME_OVERHEAD_GB: float = 0.60

# Hardware fit classification labels
FIT_FULL_VRAM: str = "FULL_VRAM_FIT"
FIT_HYBRID_OFFLOAD: str = "HYBRID_GPU_RAM_OFFLOAD"
FIT_TOO_LARGE: str = "TOO_LARGE"

# Source health status enums
STATUS_OK: str = "OK"
STATUS_DEGRADED_MISSING_KEY: str = "DEGRADED_MISSING_KEY"
STATUS_DEGRADED_SCHEMA_CHANGED: str = "DEGRADED_SCHEMA_CHANGED"
STATUS_DEGRADED_NETWORK_ERROR: str = "DEGRADED_NETWORK_ERROR"
STATUS_DEGRADED_RATE_LIMITED: str = "DEGRADED_RATE_LIMITED"
STATUS_DEGRADED_HTTP_ERROR: str = "DEGRADED_HTTP_ERROR"
STATUS_DEGRADED_AUTH_ERROR: str = "DEGRADED_AUTH_ERROR"

_TRANSIENT_HTTP_STATUSES: frozenset[int] = frozenset({429, 500, 502, 503, 504})

_OPEN_WEIGHT_PROVIDERS: frozenset[str] = frozenset(
    {
        "allenai",
        "baidu",
        "bytedance",
        "cognitivecomputations",
        "deepseek",
        "essentialai",
        "ibm-granite",
        "inclusionai",
        "liquid",
        "meta-llama",
        "minimax",
        "mistralai",
        "moonshotai",
        "nousresearch",
        "nvidia",
        "qwen",
        "tencent",
        "thudm",
        "tngtech",
        "upstage",
        "xiaomi",
        "z-ai",
    }
)

_OPEN_WEIGHT_MODEL_TOKENS: tuple[str, ...] = (
    "gemma",
    "phi-3",
    "phi-4",
    "llama",
    "qwen",
    "deepseek",
    "mistral",
    "ministral",
    "mixtral",
    "devstral",
    "codestral",
    "granite",
    "olmo",
    "gpt-oss",
    "nemotron",
    "kimi",
    "glm-",
    "lfm-",
)

_NON_SUPERVISOR_TOKENS: tuple[str, ...] = (
    "-image",
    "image-preview",
    "guard",
    "moderation",
    "shield",
    "safeguard",
    "embed",
    "rerank",
    "whisper",
    "tts",
    "audio-only",
    "hy-mt",
    "ui-tars",
    "roleplay",
    "aion-rp",
    "mythomax",
    "slerp",
    "unslop",
    "lunaris",
    "dolphin",
    "venice",
    "bodybuilder",
)

_REASONING_NAME_TOKENS: tuple[str, ...] = (
    "reasoner",
    "thinking",
    "-r1",
    "/r1",
    "qwq",
    "/o1",
    "/o3",
    "/o4",
    "deepseek-r",
)

_CODING_NAME_TOKENS: tuple[str, ...] = (
    "coder",
    "codex",
    "codestral",
    "devstral",
    "sonnet",
    "opus",
    "deepseek-v",
    "deepseek-r",
    "qwen3",
    "qwen4",
    "gpt-5",
    "gpt-6",
    "gemini-2.5",
    "gemini-3",
    "gemini-4",
    "kimi",
    "glm-",
    "mistral-large",
)

_DEDICATED_CODING_TOKENS: tuple[str, ...] = (
    "codex",
    "coder",
    "codestral",
    "devstral",
    "sonnet",
    "opus",
)

_LIGHTWEIGHT_TIER_TOKENS: tuple[str, ...] = (
    "flash",
    "mini",
    "nano",
    "tiny",
    "lite",
    "micro",
    "small",
    "haiku",
    "air",
)

_FRONTIER_TIER_TOKENS: tuple[str, ...] = (
    "opus",
    "sonnet",
    "pro",
    "max",
    "large",
    "codex",
    "o3",
    "o4",
    "r1",
    "ultra",
    "prime",
    "neon",
    "sol",
)

_MAJOR_PROVIDERS: frozenset[str] = frozenset(
    {
        "anthropic",
        "deepseek",
        "google",
        "meta-llama",
        "mistralai",
        "moonshotai",
        "openai",
        "qwen",
        "x-ai",
        "z-ai",
    }
)

# Regex patterns for parameter size extraction
_MOE_NXMB_RE = re.compile(r"(?<![a-z0-9])(\d+)\s*x\s*(\d+(?:\.\d+)?)\s*b(?![a-z0-9])", re.IGNORECASE)
_MOE_TOTAL_ACTIVE_RE = re.compile(
    r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*b[-_\s]*a(\d+(?:\.\d+)?)\s*b(?![a-z0-9])",
    re.IGNORECASE,
)
_MOE_ACTIVE_EXPERTS_RE = re.compile(
    r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*b[-_\s]*(\d+)e(?![a-z0-9])",
    re.IGNORECASE,
)
_STD_PARAMS_RE = re.compile(r"(?<![a-z0-9])(\d+(?:\.\d+)?)\s*b(?![a-z0-9])", re.IGNORECASE)


# ==============================================================================
# Custom Fail-Closed Exceptions
# ==============================================================================


class RadarValidationError(ValueError):
    """Base fail-closed validation error for AI Model Radar payloads."""


class PoisonedPricingError(RadarValidationError):
    """Raised fail-closed when model pricing contains NaN, Inf, bool, or negative values."""


class OpenRouterSchemaError(RadarValidationError):
    """Raised fail-closed when the primary OpenRouter catalog violates strict schema contracts."""


# ==============================================================================
# Typed Data Models
# ==============================================================================


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_uint32),
        ("dwMemoryLoad", ctypes.c_uint32),
        ("ullTotalPhys", ctypes.c_uint64),
        ("ullAvailPhys", ctypes.c_uint64),
        ("ullTotalPageFile", ctypes.c_uint64),
        ("ullAvailPageFile", ctypes.c_uint64),
        ("ullTotalVirtual", ctypes.c_uint64),
        ("ullAvailVirtual", ctypes.c_uint64),
        ("ullAvailExtendedVirtual", ctypes.c_uint64),
    ]


@dataclass(frozen=True)
class HardwareProfile:
    """Detected local host compute profile and derived LLM memory budgets."""

    os_name: str
    cpu_cores: int
    ram_total_gb: float
    ram_source: str
    gpu_detected: bool
    gpu_name: str | None
    gpu_vram_total_gb: float
    gpu_vram_free_gb: float
    gpu_source: str
    full_vram_budget_gb: float
    hybrid_offload_budget_gb: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LocalFitAssessment:
    """Exact Q4/Q8 memory footprint and fit tier for an open-weight model."""

    params_b: float
    active_params_b: float | None
    is_moe: bool
    q4_estimated_gb: float
    q8_estimated_gb: float
    q4_fit_tier: str
    q8_fit_tier: str
    recommended_quant: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class NormalizedModel:
    """Validated, normalized OpenRouter model record."""

    id: str
    name: str
    provider: str
    context_length: int
    prompt_usd_per_token: float
    completion_usd_per_token: float
    prompt_usd_per_1m: float
    completion_usd_per_1m: float
    blended_usd_per_1m: float
    monthly_supervisor_usd: float
    monthly_supervisor_vnd: int
    supports_reasoning: bool
    supports_structured_outputs: bool
    supports_tools: bool
    is_free_variant: bool
    is_batch_variant: bool
    is_alias_or_beta: bool
    is_open_weight: bool
    hugging_face_id: str | None
    estimated_params_b: float | None
    active_params_b: float | None
    is_moe: bool
    modality: str
    created: int | None
    aa_intelligence_index: float | None = None
    aa_coding_index: float | None = None
    aa_math_index: float | None = None
    aa_output_tps: float | None = None


# ==============================================================================
# Strict Numeric & Pricing Validators (Fail-Closed)
# ==============================================================================


def validate_finite_non_negative_float(raw: Any, *, field_name: str, reject_zero: bool = False) -> float:
    """Validate a finite, non-negative float; fail-closed on bool, None, NaN, Inf, or negative."""
    if isinstance(raw, bool):
        raise PoisonedPricingError(f"{field_name}: boolean value {raw!r} is forbidden")
    if raw is None:
        raise PoisonedPricingError(f"{field_name}: missing/None value is forbidden")
    if isinstance(raw, (int, float)):
        val = float(raw)
    elif isinstance(raw, str):
        text = raw.strip()
        if not text:
            raise PoisonedPricingError(f"{field_name}: empty string is forbidden")
        low = text.lower()
        if low in ("true", "false"):
            raise PoisonedPricingError(f"{field_name}: boolean string {raw!r} is forbidden")
        try:
            val = float(text)
        except ValueError as exc:
            raise PoisonedPricingError(f"{field_name}: non-numeric value {raw!r}") from exc
    else:
        raise PoisonedPricingError(f"{field_name}: unsupported type {type(raw).__name__}")

    if not math.isfinite(val):
        raise PoisonedPricingError(f"{field_name}: non-finite value {raw!r} is forbidden")
    if val < 0.0:
        raise PoisonedPricingError(f"{field_name}: negative value {val!r} is forbidden")
    if reject_zero and val == 0.0:
        raise PoisonedPricingError(f"{field_name}: zero value is forbidden")
    return val


def validate_price_per_token(raw: Any, *, field_name: str = "pricing") -> float:
    """Strict fail-closed validator for USD-per-token pricing fields."""
    return validate_finite_non_negative_float(raw, field_name=field_name, reject_zero=False)


def validate_context_length(raw: Any, *, model_id: str) -> int:
    """Strict fail-closed validator for model context_length (rejects bool/NaN/negative)."""
    if raw is None:
        return 0
    if isinstance(raw, bool):
        raise PoisonedPricingError(f"{model_id}: context_length cannot be bool ({raw!r})")
    if isinstance(raw, int):
        if raw < 0:
            raise PoisonedPricingError(f"{model_id}: negative context_length ({raw})")
        return raw
    if isinstance(raw, float):
        if not math.isfinite(raw) or raw < 0.0:
            raise PoisonedPricingError(f"{model_id}: invalid context_length ({raw!r})")
        return int(raw)
    raise PoisonedPricingError(f"{model_id}: unsupported context_length type {type(raw).__name__}")


def compute_monthly_supervisor_cost_usd(
    prompt_usd_per_token: float,
    completion_usd_per_token: float,
    *,
    monthly_input_tokens: int = SUPERVISOR_MONTHLY_INPUT_TOKENS,
    monthly_output_tokens: int = SUPERVISOR_MONTHLY_OUTPUT_TOKENS,
) -> float:
    """Compute exact monthly Macro Supervisor spend for 44 runs/mo (350K in + 70K out)."""
    prompt_rate = validate_price_per_token(prompt_usd_per_token, field_name="prompt_usd_per_token")
    completion_rate = validate_price_per_token(completion_usd_per_token, field_name="completion_usd_per_token")
    in_tok = validate_finite_non_negative_float(monthly_input_tokens, field_name="monthly_input_tokens")
    out_tok = validate_finite_non_negative_float(monthly_output_tokens, field_name="monthly_output_tokens")
    cost = (in_tok * prompt_rate) + (out_tok * completion_rate)
    if not math.isfinite(cost) or cost < 0.0:
        raise PoisonedPricingError(f"Computed monthly cost is invalid: {cost!r}")
    return round(cost, 6)


def usd_to_vnd(usd_amount: float, *, usd_vnd_rate: float = DEFAULT_USD_VND_RATE) -> int:
    """Convert USD amount to integer VND using validated positive FX rate."""
    amt = validate_finite_non_negative_float(usd_amount, field_name="usd_amount")
    rate = validate_finite_non_negative_float(usd_vnd_rate, field_name="usd_vnd_rate", reject_zero=True)
    return int(round(amt * rate))


# ==============================================================================
# Local Hardware Fit Detector (Windowless nvidia-smi + RAM/CPU)
# ==============================================================================


def _detect_system_ram_gb() -> tuple[float, str]:
    """Detect total physical system RAM in GB using psutil or Windows GlobalMemoryStatusEx."""
    if psutil is not None:
        try:
            total_bytes = int(psutil.virtual_memory().total)
            if total_bytes > 0:
                return round(total_bytes / (1024.0**3), 2), "psutil"
        except Exception:
            pass

    if os.name == "nt":
        try:
            mem = _MemoryStatusEx()
            mem.dwLength = ctypes.sizeof(_MemoryStatusEx)
            if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(mem)) and mem.ullTotalPhys > 0:
                return round(float(mem.ullTotalPhys) / (1024.0**3), 2), "ctypes.GlobalMemoryStatusEx"
        except Exception:
            pass
    else:
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            phys_pages = os.sysconf("SC_PHYS_PAGES")
            if page_size > 0 and phys_pages > 0:
                return round((page_size * phys_pages) / (1024.0**3), 2), "posix.sysconf"
        except Exception:
            pass

    return 0.0, "UNAVAILABLE"


def _detect_nvidia_gpu(timeout_sec: float = 5.0) -> tuple[bool, str | None, float, float, str]:
    """Detect NVIDIA GPU name and VRAM via windowless nvidia-smi with graceful fallback."""
    try:
        proc = subprocess.run(
            ["nvidia-smi", "--query-gpu=name,memory.total,memory.free", "--format=csv,noheader,nounits"],
            capture_output=True,
            text=True,
            timeout=timeout_sec,
            check=False,
            creationflags=_NO_WINDOW_FLAGS,
        )
    except FileNotFoundError:
        return False, None, 0.0, 0.0, "NO_GPU_NVIDIA_SMI_NOT_FOUND"
    except subprocess.TimeoutExpired:
        return False, None, 0.0, 0.0, "NO_GPU_NVIDIA_SMI_TIMEOUT"
    except OSError:
        return False, None, 0.0, 0.0, "NO_GPU_OS_ERROR"

    if proc.returncode != 0 or not proc.stdout or not proc.stdout.strip():
        return False, None, 0.0, 0.0, f"NO_GPU_EXIT_{proc.returncode}"

    best_name: str | None = None
    best_total_mib: float = -1.0
    best_free_mib: float = 0.0
    for raw_line in proc.stdout.strip().splitlines():
        parts = [p.strip() for p in raw_line.split(",")]
        if len(parts) < 3:
            continue
        name = parts[0]
        try:
            total_mib = float(parts[1])
            free_mib = float(parts[2])
        except ValueError:
            continue
        if not math.isfinite(total_mib) or total_mib <= 0.0:
            continue
        if not math.isfinite(free_mib) or free_mib < 0.0:
            free_mib = 0.0
        if total_mib > best_total_mib:
            best_name = name
            best_total_mib = total_mib
            best_free_mib = min(free_mib, total_mib)

    if best_name is None or best_total_mib <= 0.0:
        return False, None, 0.0, 0.0, "NO_GPU_PARSE_EMPTY"

    return (
        True,
        best_name,
        round(best_total_mib / 1024.0, 2),
        round(best_free_mib / 1024.0, 2),
        "nvidia-smi",
    )


def compute_hardware_memory_budgets(gpu_vram_total_gb: float, ram_total_gb: float) -> tuple[float, float]:
    """Compute usable full-VRAM and hybrid GPU+RAM offload budgets in GB.

    Calibrated so an RTX 2070 SUPER (8.0 GB VRAM) / 32.0 GB RAM workstation yields:
      - ``full_vram_budget_gb = 7.20 GB`` (90% of VRAM, preserving OS/CUDA headroom)
      - ``hybrid_offload_budget_gb = 22.00 GB`` (VRAM + safe offloadable RAM leaving OS headroom)
    """
    vram = validate_finite_non_negative_float(gpu_vram_total_gb, field_name="gpu_vram_total_gb")
    ram = validate_finite_non_negative_float(ram_total_gb, field_name="ram_total_gb")

    full_vram_budget = round(vram * 0.90, 2) if vram > 0.0 else 0.0
    if ram > 12.0:
        offload_ram = (ram - 12.0) * 0.74
    else:
        offload_ram = ram * 0.45
    hybrid_budget = round(full_vram_budget + max(0.0, offload_ram), 2)
    return full_vram_budget, hybrid_budget


def detect_local_hardware() -> HardwareProfile:
    """Auto-detect local GPU, CPU core count, system RAM, and derived LLM memory budgets."""
    cpu_cores = int(os.cpu_count() or 1)
    ram_total_gb, ram_source = _detect_system_ram_gb()
    gpu_detected, gpu_name, vram_total_gb, vram_free_gb, gpu_source = _detect_nvidia_gpu()
    full_vram_budget_gb, hybrid_budget_gb = compute_hardware_memory_budgets(vram_total_gb, ram_total_gb)

    return HardwareProfile(
        os_name=platform.system() or os.name,
        cpu_cores=cpu_cores,
        ram_total_gb=ram_total_gb,
        ram_source=ram_source,
        gpu_detected=gpu_detected,
        gpu_name=gpu_name,
        gpu_vram_total_gb=vram_total_gb,
        gpu_vram_free_gb=vram_free_gb,
        gpu_source=gpu_source,
        full_vram_budget_gb=full_vram_budget_gb,
        hybrid_offload_budget_gb=hybrid_budget_gb,
    )


def classify_memory_fit(estimated_gb: float, hardware: HardwareProfile) -> str:
    """Classify an estimated model footprint (GB) against the detected hardware profile."""
    footprint = validate_finite_non_negative_float(estimated_gb, field_name="estimated_gb", reject_zero=True)
    if hardware.full_vram_budget_gb > 0.0 and footprint <= hardware.full_vram_budget_gb:
        return FIT_FULL_VRAM
    if hardware.hybrid_offload_budget_gb > 0.0 and footprint <= hardware.hybrid_offload_budget_gb:
        return FIT_HYBRID_OFFLOAD
    return FIT_TOO_LARGE


def assess_local_model_fit(
    params_b: float,
    hardware: HardwareProfile,
    *,
    active_params_b: float | None = None,
    is_moe: bool = False,
) -> LocalFitAssessment:
    """Estimate Q4_K_M and Q8_0 memory footprints and fit tiers for an open-weight model."""
    total_b = validate_finite_non_negative_float(params_b, field_name="params_b", reject_zero=True)
    q4_gb = round(total_b * Q4_GB_PER_BILLION + LOCAL_RUNTIME_OVERHEAD_GB, 2)
    q8_gb = round(total_b * Q8_GB_PER_BILLION + LOCAL_RUNTIME_OVERHEAD_GB, 2)
    q4_tier = classify_memory_fit(q4_gb, hardware)
    q8_tier = classify_memory_fit(q8_gb, hardware)

    recommended_quant: str | None
    if q8_tier == FIT_FULL_VRAM:
        recommended_quant = "Q8_0"
    elif q4_tier in (FIT_FULL_VRAM, FIT_HYBRID_OFFLOAD):
        recommended_quant = "Q4_K_M"
    else:
        recommended_quant = None

    return LocalFitAssessment(
        params_b=round(total_b, 2),
        active_params_b=round(active_params_b, 2) if active_params_b is not None else None,
        is_moe=is_moe,
        q4_estimated_gb=q4_gb,
        q8_estimated_gb=q8_gb,
        q4_fit_tier=q4_tier,
        q8_fit_tier=q8_tier,
        recommended_quant=recommended_quant,
    )


def extract_parameter_count(
    model_id: str,
    name: str,
    hugging_face_id: str | None,
) -> tuple[float | None, float | None, bool]:
    """Extract (total_params_b, active_params_b, is_moe) conservatively from model identifiers."""
    haystack = " ".join(part for part in (model_id, hugging_face_id or "", name) if part)

    # 1. Explicit <total>B-A<active>B MoE naming (e.g., gemma-4-26b-a4b, qwen3-235b-a22b)
    m_ta = _MOE_TOTAL_ACTIVE_RE.search(haystack)
    if m_ta:
        total_b = float(m_ta.group(1))
        active_b = float(m_ta.group(2))
        if 0.3 <= total_b <= 2500.0 and 0.1 <= active_b <= total_b:
            return total_b, active_b, True

    # 2. Explicit <active>B-<N>E MoE expert notation (e.g., llama-4-maverick-17b-128e -> ~400B total)
    m_ae = _MOE_ACTIVE_EXPERTS_RE.search(haystack)
    if m_ae:
        active_b = float(m_ae.group(1))
        experts = int(m_ae.group(2))
        if 0.3 <= active_b <= 500.0 and experts >= 2:
            # Conservative total-weight estimate (active + routed expert weights)
            est_total_b = round(active_b * max(2.0, experts * 0.184), 1)
            return est_total_b, active_b, True

    # 3. Explicit NxMB MoE notation (e.g., mixtral-8x7b, mixtral-8x22b)
    m_nx = _MOE_NXMB_RE.search(haystack)
    if m_nx:
        experts = int(m_nx.group(1))
        per_expert_b = float(m_nx.group(2))
        if 2 <= experts <= 256 and 0.3 <= per_expert_b <= 500.0:
            # Conservative upper estimate (~85% of N*M accounting for shared attention/embeddings)
            est_total_b = round(experts * per_expert_b * 0.85, 1)
            return est_total_b, round(per_expert_b * 2.0, 1), True

    # 4. Known large MoE aliases without explicit expert suffix in id
    low = haystack.lower()
    if "llama-4-maverick" in low:
        return 400.0, 17.0, True
    if "llama-4-scout" in low:
        return 109.0, 17.0, True
    if "deepseek-r1" in low and not any(tok in low for tok in ("distill", "7b", "8b", "14b", "32b", "70b")):
        return 671.0, 37.0, True
    if "deepseek-v3" in low and not any(tok in low for tok in ("distill", "lite")):
        return 671.0, 37.0, True

    # 5. Standard dense parameter suffix (e.g., 7b, 8b, 14b, 32b, 1.7b)
    candidates: list[float] = []
    for match in _STD_PARAMS_RE.finditer(haystack):
        val = float(match.group(1))
        if 0.3 <= val <= 2000.0:
            candidates.append(val)
    if candidates:
        return max(candidates), None, False

    return None, None, False


# ==============================================================================
# HTTP Fetch Helpers (httpx + retry=1 + Graceful Degradation)
# ==============================================================================


def _http_get_with_retry(
    client: httpx.Client,
    url: str,
    *,
    headers: Mapping[str, str] | None = None,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    retries: int = DEFAULT_HTTP_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> tuple[httpx.Response, int, float]:
    """Perform GET with bounded retry on transient network/HTTP errors."""
    max_attempts = max(1, int(retries) + 1)
    last_exc: Exception | None = None
    t0 = time.perf_counter()

    for attempt in range(1, max_attempts + 1):
        try:
            resp = client.get(url, headers=dict(headers) if headers else None, timeout=timeout_sec)
            if resp.status_code in _TRANSIENT_HTTP_STATUSES and attempt < max_attempts:
                if retry_backoff_sec > 0.0:
                    time.sleep(retry_backoff_sec)
                continue
            elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 1)
            return resp, attempt, elapsed_ms
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            last_exc = exc
            if attempt < max_attempts:
                if retry_backoff_sec > 0.0:
                    time.sleep(retry_backoff_sec)
                continue
            raise

    if last_exc is not None:  # pragma: no cover - defensive fallback
        raise last_exc
    raise httpx.RequestError(f"HTTP GET failed without response for {url}")  # pragma: no cover


def fetch_openrouter_catalog(
    *,
    client: httpx.Client | None = None,
    url: str = OPENROUTER_MODELS_URL,
    timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    retries: int = DEFAULT_HTTP_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Fetch primary OpenRouter models catalog (no auth required) with strict JSON check."""
    own_client = client is None
    active_client = client or httpx.Client(timeout=timeout_sec, follow_redirects=True)
    try:
        resp, attempts, latency_ms = _http_get_with_retry(
            active_client,
            url,
            headers={"Accept": "application/json", "User-Agent": "Naqex-Wave4-AIModelRadar/1.0"},
            timeout_sec=timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        if resp.status_code != 200:
            raise OpenRouterSchemaError(f"OpenRouter returned HTTP {resp.status_code}")
        try:
            payload = resp.json()
        except ValueError as exc:
            raise OpenRouterSchemaError(f"OpenRouter returned invalid JSON: {exc}") from exc
        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list) or len(payload["data"]) == 0:
            raise OpenRouterSchemaError("OpenRouter payload must be a JSON object with a non-empty 'data' list")
        meta = {
            "status": STATUS_OK,
            "url": url,
            "http_status": resp.status_code,
            "attempts": attempts,
            "latency_ms": latency_ms,
        }
        return payload, meta
    finally:
        if own_client:
            active_client.close()


def fetch_artificial_analysis_optional(
    *,
    client: httpx.Client | None = None,
    api_key: str | None = None,
    url: str = ARTIFICIAL_ANALYSIS_MODELS_URL,
    timeout_sec: float = SECONDARY_HTTP_TIMEOUT_SEC,
    retries: int = DEFAULT_HTTP_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> tuple[dict[str, dict[str, float]], dict[str, Any]]:
    """Fetch optional Artificial Analysis v2 benchmarks; degrade cleanly without crashing."""
    resolved_key = (api_key if api_key is not None else os.environ.get(ARTIFICIAL_ANALYSIS_ENV_VAR, "")).strip()
    if not resolved_key:
        return {}, {
            "status": STATUS_DEGRADED_MISSING_KEY,
            "url": url,
            "env_var": ARTIFICIAL_ANALYSIS_ENV_VAR,
            "records_count": 0,
            "detail": "Optional API key not set in environment; radar running on OpenRouter + public HF metadata.",
        }

    own_client = client is None
    active_client = client or httpx.Client(timeout=timeout_sec, follow_redirects=True)
    try:
        try:
            resp, attempts, latency_ms = _http_get_with_retry(
                active_client,
                url,
                headers={"x-api-key": resolved_key, "Accept": "application/json"},
                timeout_sec=timeout_sec,
                retries=retries,
                retry_backoff_sec=retry_backoff_sec,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            return {}, {
                "status": STATUS_DEGRADED_NETWORK_ERROR,
                "url": url,
                "records_count": 0,
                "error_type": type(exc).__name__,
            }

        if resp.status_code in (401, 403):
            return {}, {
                "status": STATUS_DEGRADED_AUTH_ERROR,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
            }
        if resp.status_code == 429:
            return {}, {
                "status": STATUS_DEGRADED_RATE_LIMITED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
            }
        if resp.status_code != 200:
            return {}, {
                "status": STATUS_DEGRADED_HTTP_ERROR,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
            }

        try:
            payload = resp.json()
        except ValueError:
            return {}, {
                "status": STATUS_DEGRADED_SCHEMA_CHANGED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
                "detail": "Invalid JSON body",
            }

        if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
            return {}, {
                "status": STATUS_DEGRADED_SCHEMA_CHANGED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
                "detail": "Expected top-level dict with 'data' list",
            }

        benchmarks: dict[str, dict[str, float]] = {}
        for item in payload["data"]:
            if not isinstance(item, dict):
                continue
            slug = str(item.get("slug") or item.get("name") or "").strip().lower()
            if not slug:
                continue
            evals = item.get("evaluations")
            if not isinstance(evals, dict):
                continue
            entry: dict[str, float] = {}
            for src_key, dst_key in (
                ("artificial_analysis_intelligence_index", "intelligence_index"),
                ("artificial_analysis_coding_index", "coding_index"),
                ("artificial_analysis_math_index", "math_index"),
            ):
                raw_val = evals.get(src_key)
                if raw_val is not None and not isinstance(raw_val, bool):
                    try:
                        fval = float(raw_val)
                        if math.isfinite(fval) and fval >= 0.0:
                            entry[dst_key] = round(fval, 2)
                    except (TypeError, ValueError):
                        pass
            tps_raw = item.get("median_output_tokens_per_second")
            if tps_raw is not None and not isinstance(tps_raw, bool):
                try:
                    tps = float(tps_raw)
                    if math.isfinite(tps) and tps > 0.0:
                        entry["output_tps"] = round(tps, 2)
                except (TypeError, ValueError):
                    pass
            if entry:
                benchmarks[_normalize_model_key(slug)] = entry

        if len(payload["data"]) > 0 and len(benchmarks) == 0:
            return {}, {
                "status": STATUS_DEGRADED_SCHEMA_CHANGED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "records_count": 0,
                "detail": "No valid Artificial Analysis v2 evaluation records parsed",
            }

        return benchmarks, {
            "status": STATUS_OK,
            "url": url,
            "http_status": resp.status_code,
            "attempts": attempts,
            "latency_ms": latency_ms,
            "records_count": len(benchmarks),
        }
    finally:
        if own_client:
            active_client.close()


def fetch_hf_metadata_optional(
    *,
    source_label: str,
    url: str,
    client: httpx.Client | None = None,
    timeout_sec: float = SECONDARY_HTTP_TIMEOUT_SEC,
    retries: int = DEFAULT_HTTP_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
) -> dict[str, Any]:
    """Fetch public HuggingFace LiveBench/LMArena metadata; degrade cleanly on any failure."""
    own_client = client is None
    active_client = client or httpx.Client(timeout=timeout_sec, follow_redirects=True)
    try:
        try:
            resp, attempts, latency_ms = _http_get_with_retry(
                active_client,
                url,
                headers={"Accept": "application/json", "User-Agent": "Naqex-Wave4-AIModelRadar/1.0"},
                timeout_sec=timeout_sec,
                retries=retries,
                retry_backoff_sec=retry_backoff_sec,
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.RemoteProtocolError) as exc:
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_NETWORK_ERROR,
                "url": url,
                "error_type": type(exc).__name__,
            }

        if resp.status_code == 429:
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_RATE_LIMITED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
            }
        if resp.status_code in (401, 403):
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_AUTH_ERROR,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
            }
        if resp.status_code != 200:
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_HTTP_ERROR,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
            }

        try:
            payload = resp.json()
        except ValueError:
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_SCHEMA_CHANGED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "detail": "Malformed JSON response",
            }

        if not isinstance(payload, dict) or not isinstance(payload.get("id"), str) or not payload["id"].strip():
            return {
                "source": source_label,
                "status": STATUS_DEGRADED_SCHEMA_CHANGED,
                "url": url,
                "http_status": resp.status_code,
                "attempts": attempts,
                "latency_ms": latency_ms,
                "detail": "Missing required string 'id' in HF metadata payload",
            }

        return {
            "source": source_label,
            "status": STATUS_OK,
            "url": url,
            "http_status": resp.status_code,
            "attempts": attempts,
            "latency_ms": latency_ms,
            "repo_id": payload["id"].strip(),
            "last_modified": payload.get("lastModified"),
            "sha": payload.get("sha"),
            "downloads": payload.get("downloads"),
            "likes": payload.get("likes"),
            "disabled": bool(payload.get("disabled", False)),
            "gated": bool(payload.get("gated", False)),
        }
    finally:
        if own_client:
            active_client.close()


# ==============================================================================
# OpenRouter Catalog Parsing & Normalization
# ==============================================================================


def _normalize_model_key(raw: str) -> str:
    """Normalize a model identifier/slug for fuzzy cross-source matching."""
    slug = raw.strip().lower()
    if "/" in slug:
        slug = slug.split("/", 1)[1]
    if ":" in slug:
        slug = slug.split(":", 1)[0]
    return re.sub(r"[^a-z0-9]+", "", slug)


def _is_openrouter_dynamic_router_sentinel(pricing: Mapping[str, Any]) -> bool:
    """Return True strictly for OpenRouter's documented ('-1', '-1') dynamic router sentinel."""
    raw_p = pricing.get("prompt")
    raw_c = pricing.get("completion")
    if isinstance(raw_p, bool) or isinstance(raw_c, bool):
        return False
    return str(raw_p).strip() == "-1" and str(raw_c).strip() == "-1"


def parse_openrouter_model(
    raw: Mapping[str, Any],
    *,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    aa_benchmarks: Mapping[str, Mapping[str, float]] | None = None,
) -> NormalizedModel:
    """Strictly validate and normalize a single OpenRouter model object (fail-closed)."""
    if not isinstance(raw, Mapping):
        raise OpenRouterSchemaError(f"Model record must be a mapping, got {type(raw).__name__}")

    raw_id = raw.get("id")
    if not isinstance(raw_id, str) or not raw_id.strip():
        raise OpenRouterSchemaError("Model record missing non-empty string 'id'")
    model_id = raw_id.strip()

    raw_name = raw.get("name")
    name = raw_name.strip() if isinstance(raw_name, str) and raw_name.strip() else model_id

    pricing = raw.get("pricing")
    if not isinstance(pricing, Mapping):
        raise PoisonedPricingError(f"{model_id}: missing or non-dict 'pricing'")
    if "prompt" not in pricing or "completion" not in pricing:
        raise PoisonedPricingError(f"{model_id}: pricing must include 'prompt' and 'completion'")

    prompt_tok = validate_price_per_token(pricing["prompt"], field_name=f"{model_id}.pricing.prompt")
    completion_tok = validate_price_per_token(pricing["completion"], field_name=f"{model_id}.pricing.completion")

    context_length = validate_context_length(raw.get("context_length"), model_id=model_id)

    prompt_per_1m = round(prompt_tok * 1_000_000.0, 6)
    completion_per_1m = round(completion_tok * 1_000_000.0, 6)
    blended_per_1m = round((3.0 * prompt_per_1m + completion_per_1m) / 4.0, 6)
    monthly_usd = compute_monthly_supervisor_cost_usd(prompt_tok, completion_tok)
    monthly_vnd = usd_to_vnd(monthly_usd, usd_vnd_rate=usd_vnd_rate)

    clean_id = model_id.lstrip("~")
    provider = clean_id.split("/", 1)[0].lower() if "/" in clean_id else "unknown"
    low_id = model_id.lower()
    low_name = name.lower()

    raw_params = raw.get("supported_parameters")
    supported_params: set[str] = (
        {str(p).strip().lower() for p in raw_params if isinstance(p, str)}
        if isinstance(raw_params, list)
        else set()
    )

    reasoning_obj = raw.get("reasoning")
    supports_reasoning = (
        isinstance(reasoning_obj, Mapping)
        or "reasoning" in supported_params
        or "include_reasoning" in supported_params
        or any(tok in low_id or tok in low_name for tok in _REASONING_NAME_TOKENS)
    )
    supports_structured_outputs = (
        "structured_outputs" in supported_params or "response_format" in supported_params
    )
    supports_tools = "tools" in supported_params

    raw_hf = raw.get("hugging_face_id")
    hugging_face_id = raw_hf.strip() if isinstance(raw_hf, str) and raw_hf.strip() else None

    is_open_weight = (
        hugging_face_id is not None
        or provider in _OPEN_WEIGHT_PROVIDERS
        or any(tok in low_id for tok in _OPEN_WEIGHT_MODEL_TOKENS)
    )

    est_params_b, active_params_b, is_moe = extract_parameter_count(model_id, name, hugging_face_id)

    arch = raw.get("architecture")
    modality = (
        str(arch.get("modality") or "text->text").strip().lower()
        if isinstance(arch, Mapping)
        else "text->text"
    )

    raw_created = raw.get("created")
    created: int | None = None
    if isinstance(raw_created, int) and not isinstance(raw_created, bool) and raw_created > 0:
        created = raw_created

    aa_intel: float | None = None
    aa_code: float | None = None
    aa_math: float | None = None
    aa_tps: float | None = None
    if aa_benchmarks:
        norm_key = _normalize_model_key(model_id)
        aa_rec = aa_benchmarks.get(norm_key)
        if aa_rec:
            aa_intel = aa_rec.get("intelligence_index")
            aa_code = aa_rec.get("coding_index")
            aa_math = aa_rec.get("math_index")
            aa_tps = aa_rec.get("output_tps")

    return NormalizedModel(
        id=model_id,
        name=name,
        provider=provider,
        context_length=context_length,
        prompt_usd_per_token=prompt_tok,
        completion_usd_per_token=completion_tok,
        prompt_usd_per_1m=prompt_per_1m,
        completion_usd_per_1m=completion_per_1m,
        blended_usd_per_1m=blended_per_1m,
        monthly_supervisor_usd=monthly_usd,
        monthly_supervisor_vnd=monthly_vnd,
        supports_reasoning=supports_reasoning,
        supports_structured_outputs=supports_structured_outputs,
        supports_tools=supports_tools,
        is_free_variant=low_id.endswith(":free") or (prompt_tok == 0.0 and completion_tok == 0.0),
        is_batch_variant=low_id.endswith(":batch"),
        is_alias_or_beta=model_id.startswith("~") or low_id.startswith("openrouter/"),
        is_open_weight=is_open_weight,
        hugging_face_id=hugging_face_id,
        estimated_params_b=est_params_b,
        active_params_b=active_params_b,
        is_moe=is_moe,
        modality=modality,
        created=created,
        aa_intelligence_index=aa_intel,
        aa_coding_index=aa_code,
        aa_math_index=aa_math,
        aa_output_tps=aa_tps,
    )


def parse_openrouter_catalog(
    payload: Mapping[str, Any],
    *,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    aa_benchmarks: Mapping[str, Mapping[str, float]] | None = None,
    skip_dynamic_routers: bool = True,
) -> tuple[list[NormalizedModel], list[str]]:
    """Parse and strictly validate all models in an OpenRouter catalog response.

    Fail-closed on poisoned pricing (NaN, Inf, bool, or negative prices). OpenRouter's
    documented variable-pricing meta-routers (``prompt == "-1"`` and ``completion == "-1"``)
    are cleanly excluded when ``skip_dynamic_routers=True``.
    """
    if not isinstance(payload, Mapping) or not isinstance(payload.get("data"), list) or len(payload["data"]) == 0:
        raise OpenRouterSchemaError("OpenRouter catalog must contain a non-empty 'data' list")

    models: list[NormalizedModel] = []
    excluded_dynamic_routers: list[str] = []
    seen_ids: set[str] = set()

    for raw in payload["data"]:
        if not isinstance(raw, Mapping):
            raise OpenRouterSchemaError(f"Expected dict model entry, got {type(raw).__name__}")
        raw_id = raw.get("id")
        if not isinstance(raw_id, str) or not raw_id.strip():
            raise OpenRouterSchemaError("OpenRouter entry missing non-empty string 'id'")
        model_id = raw_id.strip()
        pricing = raw.get("pricing")
        if skip_dynamic_routers and isinstance(pricing, Mapping) and _is_openrouter_dynamic_router_sentinel(pricing):
            excluded_dynamic_routers.append(model_id)
            continue
        parsed = parse_openrouter_model(raw, usd_vnd_rate=usd_vnd_rate, aa_benchmarks=aa_benchmarks)
        if parsed.id not in seen_ids:
            seen_ids.add(parsed.id)
            models.append(parsed)

    if not models:
        raise OpenRouterSchemaError("OpenRouter catalog contained 0 valid priced models after validation")

    return models, sorted(excluded_dynamic_routers)


# ==============================================================================
# 4 Structured Leaderboards
# ==============================================================================


def _is_text_generation_candidate(m: NormalizedModel) -> bool:
    """Filter out non-text-output, image-gen, guard, moderation, and roleplay models."""
    if "->text" not in m.modality and m.modality != "text":
        return False
    low = f"{m.id.lower()} {m.name.lower()}"
    return not any(tok in low for tok in _NON_SUPERVISOR_TOKENS)


def _recency_bonus(created: int | None, ref_ts: int) -> float:
    """Smooth bounded freshness score in [0.0, 1.0] favoring recent releases."""
    if created is None or created <= 0 or ref_ts <= 0:
        return 0.4
    age_days = max(0.0, (ref_ts - created) / 86_400.0)
    return round(1.0 / (1.0 + age_days / 365.0), 4)


def _context_score(ctx: int) -> float:
    """Log-scaled context score in [0.0, 1.0] saturating around 1M tokens."""
    if ctx <= 0:
        return 0.0
    return round(min(1.0, math.log2(max(1.0, ctx / 8_192.0)) / 7.0), 4)


def build_leaderboards(
    models: Sequence[NormalizedModel],
    hardware: HardwareProfile,
    *,
    budget_cap_usd: float = MAX_OFFICIAL_API_USD_PER_MONTH,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    top_n: int = DEFAULT_TOP_N,
    now_ts: int | None = None,
) -> dict[str, Any]:
    """Compute the 4 structured W4-G13 leaderboards from validated models and hardware."""
    cap_usd = validate_finite_non_negative_float(budget_cap_usd, field_name="budget_cap_usd", reject_zero=True)
    rate = validate_finite_non_negative_float(usd_vnd_rate, field_name="usd_vnd_rate", reject_zero=True)
    ref_ts = int(now_ts if now_ts is not None else time.time())
    limit = max(1, int(top_n))

    base_live = [
        m
        for m in models
        if not m.is_batch_variant and not m.is_alias_or_beta and _is_text_generation_candidate(m)
    ]

    # ------------------------------------------------------------------
    # 1. budget_macro_supervisor_monthly_usd (44 runs/mo = 350K in + 70K out, <= $5.00/mo)
    # ------------------------------------------------------------------
    budget_candidates = [
        m
        for m in base_live
        if not m.id.lower().endswith(":free")
        and m.monthly_supervisor_usd <= cap_usd
        and m.context_length >= 32_000
    ]
    if not budget_candidates:
        budget_candidates = [
            m
            for m in base_live
            if not m.id.lower().endswith(":free") and m.monthly_supervisor_usd <= cap_usd
        ]

    budget_scored: list[tuple[float, NormalizedModel]] = []
    for m in budget_candidates:
        cap_quality = 35.0
        if m.supports_structured_outputs:
            cap_quality += 22.0
        if m.supports_reasoning:
            cap_quality += 18.0
        if m.supports_tools:
            cap_quality += 8.0
        if m.provider in _MAJOR_PROVIDERS:
            cap_quality += 10.0
        cap_quality += 10.0 * _context_score(m.context_length)
        cap_quality += 7.0 * _recency_bonus(m.created, ref_ts)
        if m.aa_intelligence_index is not None:
            cap_quality += min(30.0, m.aa_intelligence_index * 0.35)

        # Strongly favor sub-$1/mo & sub-$2/mo official APIs while preserving quality
        cost_factor = 1.0 / (0.18 + m.monthly_supervisor_usd) ** 0.35
        score = round(cap_quality * cost_factor, 3)
        budget_scored.append((score, m))

    budget_scored.sort(key=lambda item: (-item[0], item[1].monthly_supervisor_usd, item[1].id))
    lb_budget = [
        {
            "rank": idx,
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "context_length": m.context_length,
            "prompt_usd_per_1m": round(m.prompt_usd_per_1m, 4),
            "completion_usd_per_1m": round(m.completion_usd_per_1m, 4),
            "monthly_usd": round(m.monthly_supervisor_usd, 4),
            "monthly_vnd": usd_to_vnd(m.monthly_supervisor_usd, usd_vnd_rate=rate),
            "budget_utilization_pct": round((m.monthly_supervisor_usd / cap_usd) * 100.0, 2),
            "within_budget_cap": True,
            "supports_reasoning": m.supports_reasoning,
            "supports_structured_outputs": m.supports_structured_outputs,
            "supports_tools": m.supports_tools,
            "aa_intelligence_index": m.aa_intelligence_index,
            "value_score": score,
        }
        for idx, (score, m) in enumerate(budget_scored[:limit], start=1)
    ]

    # ------------------------------------------------------------------
    # 2. top_value_reasoning (price-adjusted frontier reasoning picks)
    # ------------------------------------------------------------------
    reasoning_candidates = [
        m
        for m in base_live
        if m.supports_reasoning and not m.id.lower().endswith(":free") and m.context_length >= 32_000
    ]
    if not reasoning_candidates:
        reasoning_candidates = [m for m in base_live if m.supports_reasoning and not m.id.lower().endswith(":free")]

    reasoning_scored: list[tuple[float, NormalizedModel]] = []
    for m in reasoning_candidates:
        low_id = m.id.lower()
        is_lightweight = any(tok in low_id for tok in _LIGHTWEIGHT_TIER_TOKENS)
        is_frontier = any(tok in low_id for tok in _FRONTIER_TIER_TOKENS)
        frontier_quality = 40.0
        if m.provider in _MAJOR_PROVIDERS:
            frontier_quality += 18.0
        if is_frontier and not is_lightweight:
            frontier_quality += 24.0
        elif is_lightweight:
            frontier_quality -= 10.0
        if m.supports_structured_outputs:
            frontier_quality += 12.0
        if m.supports_tools:
            frontier_quality += 8.0
        frontier_quality += 14.0 * _context_score(m.context_length)
        frontier_quality += 12.0 * _recency_bonus(m.created, ref_ts)
        # Penalize tiny <8B models for frontier reasoning unless AA benchmark proves otherwise
        if m.estimated_params_b is not None and m.estimated_params_b < 8.0 and m.aa_intelligence_index is None:
            frontier_quality -= 18.0
        if m.aa_intelligence_index is not None:
            frontier_quality += min(45.0, m.aa_intelligence_index * 0.50)
        if m.aa_math_index is not None:
            frontier_quality += min(20.0, m.aa_math_index * 0.20)

        # Price-adjusted value: reward strong frontier reasoning per dollar without over-penalizing mid-tier
        price_denom = math.log2(4.0 + max(0.05, m.blended_usd_per_1m))
        score = round(frontier_quality / price_denom, 3)
        reasoning_scored.append((score, m))

    reasoning_scored.sort(key=lambda item: (-item[0], item[1].blended_usd_per_1m, item[1].id))
    lb_reasoning = [
        {
            "rank": idx,
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "context_length": m.context_length,
            "prompt_usd_per_1m": round(m.prompt_usd_per_1m, 4),
            "completion_usd_per_1m": round(m.completion_usd_per_1m, 4),
            "blended_usd_per_1m": round(m.blended_usd_per_1m, 4),
            "monthly_supervisor_usd": round(m.monthly_supervisor_usd, 4),
            "monthly_supervisor_vnd": usd_to_vnd(m.monthly_supervisor_usd, usd_vnd_rate=rate),
            "supports_structured_outputs": m.supports_structured_outputs,
            "supports_tools": m.supports_tools,
            "aa_intelligence_index": m.aa_intelligence_index,
            "aa_math_index": m.aa_math_index,
            "reasoning_value_score": score,
        }
        for idx, (score, m) in enumerate(reasoning_scored[:limit], start=1)
    ]

    # ------------------------------------------------------------------
    # 3. top_coding_audit (high-context structured coding/audit picks)
    # ------------------------------------------------------------------
    coding_candidates = [
        m
        for m in base_live
        if not m.id.lower().endswith(":free")
        and m.context_length >= 128_000
        and (m.supports_structured_outputs or m.supports_tools)
    ]
    if not coding_candidates:
        coding_candidates = [
            m
            for m in base_live
            if not m.id.lower().endswith(":free") and m.context_length >= 64_000
        ]

    coding_scored: list[tuple[float, NormalizedModel]] = []
    for m in coding_candidates:
        low_id = m.id.lower()
        is_lightweight = any(tok in low_id for tok in _LIGHTWEIGHT_TIER_TOKENS)
        is_dedicated_coding = any(tok in low_id for tok in _DEDICATED_CODING_TOKENS)
        audit_quality = 30.0
        audit_quality += 22.0 * _context_score(m.context_length)
        if m.supports_structured_outputs:
            audit_quality += 16.0
        if m.supports_tools:
            audit_quality += 10.0
        if m.supports_reasoning:
            audit_quality += 14.0
        if m.provider in _MAJOR_PROVIDERS:
            audit_quality += 10.0
        if is_dedicated_coding:
            audit_quality += 26.0
        elif any(tok in low_id for tok in _CODING_NAME_TOKENS) and not is_lightweight:
            audit_quality += 16.0
        elif is_lightweight:
            audit_quality -= 10.0
        audit_quality += 8.0 * _recency_bonus(m.created, ref_ts)
        if m.aa_coding_index is not None:
            audit_quality += min(45.0, m.aa_coding_index * 0.50)

        price_denom = math.log2(6.0 + max(0.05, m.blended_usd_per_1m))
        score = round(audit_quality / price_denom, 3)
        coding_scored.append((score, m))

    coding_scored.sort(key=lambda item: (-item[0], -item[1].context_length, item[1].id))
    lb_coding = [
        {
            "rank": idx,
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "context_length": m.context_length,
            "prompt_usd_per_1m": round(m.prompt_usd_per_1m, 4),
            "completion_usd_per_1m": round(m.completion_usd_per_1m, 4),
            "blended_usd_per_1m": round(m.blended_usd_per_1m, 4),
            "monthly_supervisor_usd": round(m.monthly_supervisor_usd, 4),
            "supports_reasoning": m.supports_reasoning,
            "supports_structured_outputs": m.supports_structured_outputs,
            "supports_tools": m.supports_tools,
            "aa_coding_index": m.aa_coding_index,
            "coding_audit_score": score,
        }
        for idx, (score, m) in enumerate(coding_scored[:limit], start=1)
    ]

    # ------------------------------------------------------------------
    # 4. local_open_weight_fit (ranked open-weight models fitting detected GPU/RAM)
    # ------------------------------------------------------------------
    seen_ow_base: set[str] = set()
    local_candidates: list[tuple[float, NormalizedModel, LocalFitAssessment]] = []
    too_large_count = 0
    unsized_open_weight_count = 0

    for m in base_live:
        if not m.is_open_weight or m.id.lower().endswith(":free"):
            continue
        base_key = m.hugging_face_id.lower() if m.hugging_face_id else m.id.lower()
        if base_key in seen_ow_base:
            continue
        seen_ow_base.add(base_key)

        if m.estimated_params_b is None:
            unsized_open_weight_count += 1
            continue

        fit = assess_local_model_fit(
            m.estimated_params_b,
            hardware,
            active_params_b=m.active_params_b,
            is_moe=m.is_moe,
        )
        if fit.q4_fit_tier == FIT_TOO_LARGE:
            too_large_count += 1
            continue

        local_score = 40.0 if fit.q4_fit_tier == FIT_FULL_VRAM else 20.0
        if fit.q8_fit_tier == FIT_FULL_VRAM:
            local_score += 3.0
        # Reward stronger parameter count within the hardware envelope (8B-9B Q4 beats 1.7B Q8)
        local_score += min(34.0, math.log2(1.0 + fit.params_b) * 8.5)
        if m.provider in _MAJOR_PROVIDERS:
            local_score += 8.0
        if m.supports_reasoning:
            local_score += 12.0
        if m.supports_structured_outputs:
            local_score += 8.0
        if m.supports_tools:
            local_score += 5.0
        local_score += 8.0 * _context_score(m.context_length)
        local_score += 8.0 * _recency_bonus(m.created, ref_ts)
        local_candidates.append((round(local_score, 3), m, fit))

    local_candidates.sort(
        key=lambda item: (
            0 if item[2].q4_fit_tier == FIT_FULL_VRAM else 1,
            -item[0],
            -item[2].params_b,
            item[1].id,
        )
    )
    lb_local = [
        {
            "rank": idx,
            "id": m.id,
            "name": m.name,
            "provider": m.provider,
            "hugging_face_id": m.hugging_face_id,
            "context_length": m.context_length,
            "estimated_params_b": fit.params_b,
            "active_params_b": fit.active_params_b,
            "is_moe": fit.is_moe,
            "q4_estimated_gb": fit.q4_estimated_gb,
            "q8_estimated_gb": fit.q8_estimated_gb,
            "q4_fit_tier": fit.q4_fit_tier,
            "q8_fit_tier": fit.q8_fit_tier,
            "recommended_quant": fit.recommended_quant,
            "supports_reasoning": m.supports_reasoning,
            "supports_structured_outputs": m.supports_structured_outputs,
            "local_fit_score": score,
        }
        for idx, (score, m, fit) in enumerate(local_candidates[:limit], start=1)
    ]

    return {
        "budget_macro_supervisor_monthly_usd": lb_budget,
        "top_value_reasoning": lb_reasoning,
        "top_coding_audit": lb_coding,
        "local_open_weight_fit": lb_local,
        "summary": {
            "budget_eligible_count": len(budget_candidates),
            "budget_cap_usd_per_month": cap_usd,
            "budget_cap_vnd_per_month": usd_to_vnd(cap_usd, usd_vnd_rate=rate),
            "reasoning_eligible_count": len(reasoning_candidates),
            "coding_audit_eligible_count": len(coding_candidates),
            "local_fitting_open_weight_count": len(local_candidates),
            "local_full_vram_fit_count": sum(1 for _, _, f in local_candidates if f.q4_fit_tier == FIT_FULL_VRAM),
            "local_hybrid_offload_count": sum(
                1 for _, _, f in local_candidates if f.q4_fit_tier == FIT_HYBRID_OFFLOAD
            ),
            "local_too_large_excluded_count": too_large_count,
            "local_unsized_open_weight_count": unsized_open_weight_count,
        },
    }


# ==============================================================================
# Price Delta Tracker
# ==============================================================================


def build_catalog_index(models: Sequence[NormalizedModel]) -> dict[str, dict[str, Any]]:
    """Create a compact per-model price index stored inside each snapshot for future diffs."""
    return {
        m.id: {
            "prompt_usd_per_1m": round(m.prompt_usd_per_1m, 6),
            "completion_usd_per_1m": round(m.completion_usd_per_1m, 6),
            "monthly_supervisor_usd": round(m.monthly_supervisor_usd, 6),
            "context_length": m.context_length,
        }
        for m in sorted(models, key=lambda x: x.id)
    }


def _pct_change(prev_val: float, curr_val: float) -> float | None:
    """Compute percentage change safely without NaN/Inf on zero baselines."""
    if prev_val == 0.0:
        return 0.0 if curr_val == 0.0 else None
    delta = ((curr_val - prev_val) / prev_val) * 100.0
    return round(delta, 2)


def compute_price_delta(
    current_index: Mapping[str, Mapping[str, Any]],
    previous_snapshot: Mapping[str, Any] | None,
    *,
    min_abs_pct_change: float = 0.01,
) -> dict[str, Any]:
    """Compare current catalog prices against a previous radar snapshot."""
    if not isinstance(previous_snapshot, Mapping):
        return {
            "has_previous_snapshot": False,
            "previous_generated_utc": None,
            "previous_model_count": 0,
            "new_models": [],
            "removed_models": [],
            "price_changes_pct": [],
            "counts": {
                "new_models": 0,
                "removed_models": 0,
                "price_changes": 0,
                "price_drops": 0,
                "price_increases": 0,
            },
        }

    prev_index = previous_snapshot.get("catalog_index")
    if not isinstance(prev_index, Mapping):
        return {
            "has_previous_snapshot": False,
            "previous_generated_utc": previous_snapshot.get("generated_utc"),
            "previous_model_count": 0,
            "new_models": [],
            "removed_models": [],
            "price_changes_pct": [],
            "warning": "PREVIOUS_SNAPSHOT_MISSING_CATALOG_INDEX",
            "counts": {
                "new_models": 0,
                "removed_models": 0,
                "price_changes": 0,
                "price_drops": 0,
                "price_increases": 0,
            },
        }

    prev_ids = {str(k) for k in prev_index}
    curr_ids = {str(k) for k in current_index}

    new_models = sorted(curr_ids - prev_ids)
    removed_models = sorted(prev_ids - curr_ids)
    common_ids = sorted(curr_ids & prev_ids)

    price_changes: list[dict[str, Any]] = []
    drops = 0
    increases = 0

    for mid in common_ids:
        prev_rec = prev_index.get(mid)
        curr_rec = current_index.get(mid)
        if not isinstance(prev_rec, Mapping) or not isinstance(curr_rec, Mapping):
            continue
        try:
            prev_p = validate_finite_non_negative_float(
                prev_rec.get("prompt_usd_per_1m"), field_name=f"prev.{mid}.prompt"
            )
            prev_c = validate_finite_non_negative_float(
                prev_rec.get("completion_usd_per_1m"), field_name=f"prev.{mid}.completion"
            )
            prev_m = validate_finite_non_negative_float(
                prev_rec.get("monthly_supervisor_usd"), field_name=f"prev.{mid}.monthly"
            )
            curr_p = validate_finite_non_negative_float(
                curr_rec.get("prompt_usd_per_1m"), field_name=f"curr.{mid}.prompt"
            )
            curr_c = validate_finite_non_negative_float(
                curr_rec.get("completion_usd_per_1m"), field_name=f"curr.{mid}.completion"
            )
            curr_m = validate_finite_non_negative_float(
                curr_rec.get("monthly_supervisor_usd"), field_name=f"curr.{mid}.monthly"
            )
        except PoisonedPricingError:
            continue

        p_pct = _pct_change(prev_p, curr_p)
        c_pct = _pct_change(prev_c, curr_c)
        m_pct = _pct_change(prev_m, curr_m)

        changed = (
            (p_pct is None and curr_p != prev_p)
            or (c_pct is None and curr_c != prev_c)
            or (m_pct is None and curr_m != prev_m)
            or (p_pct is not None and abs(p_pct) >= min_abs_pct_change)
            or (c_pct is not None and abs(c_pct) >= min_abs_pct_change)
            or (m_pct is not None and abs(m_pct) >= min_abs_pct_change)
        )
        if not changed:
            continue

        if curr_m < prev_m:
            direction = "PRICE_DROP"
            drops += 1
        elif curr_m > prev_m:
            direction = "PRICE_INCREASE"
            increases += 1
        elif prev_p == 0.0 and curr_p > 0.0:
            direction = "FREE_TO_PAID"
            increases += 1
        elif prev_p > 0.0 and curr_p == 0.0:
            direction = "PAID_TO_FREE"
            drops += 1
        else:
            direction = "MIXED"

        price_changes.append(
            {
                "id": mid,
                "direction": direction,
                "prev_prompt_usd_per_1m": round(prev_p, 6),
                "curr_prompt_usd_per_1m": round(curr_p, 6),
                "prompt_delta_pct": p_pct,
                "prev_completion_usd_per_1m": round(prev_c, 6),
                "curr_completion_usd_per_1m": round(curr_c, 6),
                "completion_delta_pct": c_pct,
                "prev_monthly_usd": round(prev_m, 6),
                "curr_monthly_usd": round(curr_m, 6),
                "monthly_delta_pct": m_pct,
            }
        )

    price_changes.sort(
        key=lambda r: (
            -(abs(r["monthly_delta_pct"]) if r["monthly_delta_pct"] is not None else 999_999.0),
            r["id"],
        )
    )

    return {
        "has_previous_snapshot": True,
        "previous_generated_utc": previous_snapshot.get("generated_utc"),
        "previous_model_count": len(prev_ids),
        "new_models": new_models,
        "removed_models": removed_models,
        "price_changes_pct": price_changes,
        "counts": {
            "new_models": len(new_models),
            "removed_models": len(removed_models),
            "price_changes": len(price_changes),
            "price_drops": drops,
            "price_increases": increases,
        },
    }


def load_previous_snapshot(path: Path | None) -> tuple[dict[str, Any] | None, str | None]:
    """Load an existing radar snapshot JSON safely for price delta comparison."""
    if path is None or not path.is_file():
        return None, None
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        return None, f"PREVIOUS_SNAPSHOT_READ_ERROR:{type(exc).__name__}"
    if not isinstance(raw, dict):
        return None, "PREVIOUS_SNAPSHOT_NOT_OBJECT"
    return raw, None


# ==============================================================================
# Atomic JSON Persistence & End-to-End Pipeline
# ==============================================================================


def atomic_write_json(path: Path, payload: Mapping[str, Any]) -> str:
    """Write JSON atomically (LF, UTF-8, allow_nan=False) and return file SHA-256."""
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    raw_bytes = text.encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()

    tmp: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb",
            dir=path.parent,
            prefix=f".{path.name}.",
            suffix=".tmp",
            delete=False,
        ) as fh:
            fh.write(raw_bytes)
            fh.flush()
            os.fsync(fh.fileno())
            tmp = Path(fh.name)
        os.replace(tmp, path)
        tmp = None
    finally:
        if tmp is not None:
            tmp.unlink(missing_ok=True)
    return digest


def run_ai_model_radar(
    *,
    output_path: Path | None = None,
    previous_snapshot_path: Path | None = None,
    usd_vnd_rate: float = DEFAULT_USD_VND_RATE,
    budget_cap_usd: float = MAX_OFFICIAL_API_USD_PER_MONTH,
    top_n: int = DEFAULT_TOP_N,
    http_client: httpx.Client | None = None,
    hardware_profile: HardwareProfile | None = None,
    artificial_analysis_api_key: str | None = None,
    openrouter_timeout_sec: float = DEFAULT_HTTP_TIMEOUT_SEC,
    secondary_timeout_sec: float = SECONDARY_HTTP_TIMEOUT_SEC,
    retries: int = DEFAULT_HTTP_RETRIES,
    retry_backoff_sec: float = DEFAULT_RETRY_BACKOFF_SEC,
    skip_dynamic_routers: bool = True,
) -> dict[str, Any]:
    """Run the full AI Model Radar pipeline and optionally write the output snapshot atomically."""
    if ORDER_SEND_CAPABLE:
        raise RadarValidationError("HARD INVARIANT VIOLATION: ORDER_SEND_CAPABLE must be False")

    rate = validate_finite_non_negative_float(usd_vnd_rate, field_name="usd_vnd_rate", reject_zero=True)
    cap_usd = validate_finite_non_negative_float(budget_cap_usd, field_name="budget_cap_usd", reject_zero=True)

    prev_path = previous_snapshot_path if previous_snapshot_path is not None else output_path
    prev_snapshot, prev_err = load_previous_snapshot(prev_path)

    hw = hardware_profile if hardware_profile is not None else detect_local_hardware()

    own_client = http_client is None
    client = http_client or httpx.Client(timeout=openrouter_timeout_sec, follow_redirects=True)
    try:
        or_payload, or_meta = fetch_openrouter_catalog(
            client=client,
            timeout_sec=openrouter_timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        aa_benchmarks, aa_meta = fetch_artificial_analysis_optional(
            client=client,
            api_key=artificial_analysis_api_key,
            timeout_sec=secondary_timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        hf_livebench_meta = fetch_hf_metadata_optional(
            source_label="hf_livebench",
            url=HF_LIVEBENCH_URL,
            client=client,
            timeout_sec=secondary_timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
        hf_lmarena_meta = fetch_hf_metadata_optional(
            source_label="hf_lmarena",
            url=HF_LMARENA_URL,
            client=client,
            timeout_sec=secondary_timeout_sec,
            retries=retries,
            retry_backoff_sec=retry_backoff_sec,
        )
    finally:
        if own_client:
            client.close()

    models, excluded_routers = parse_openrouter_catalog(
        or_payload,
        usd_vnd_rate=rate,
        aa_benchmarks=aa_benchmarks,
        skip_dynamic_routers=skip_dynamic_routers,
    )

    or_meta["raw_count"] = len(or_payload["data"])
    or_meta["valid_priced_count"] = len(models)
    or_meta["excluded_dynamic_routers_count"] = len(excluded_routers)
    or_meta["excluded_dynamic_routers"] = excluded_routers
    aa_meta["enriched_models_count"] = sum(1 for m in models if m.aa_intelligence_index is not None)

    now_dt = datetime.now(UTC)
    leaderboards = build_leaderboards(
        models,
        hw,
        budget_cap_usd=cap_usd,
        usd_vnd_rate=rate,
        top_n=top_n,
        now_ts=int(now_dt.timestamp()),
    )
    catalog_index = build_catalog_index(models)
    price_delta = compute_price_delta(catalog_index, prev_snapshot)
    if prev_err:
        price_delta["previous_snapshot_error"] = prev_err

    snapshot: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "generated_utc": now_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "hard_invariants": {
            "order_send_capable": ORDER_SEND_CAPABLE,
            "order_send_count": 0,
            "spend_vnd": 0,
            "holdout_cutoff_date": HOLDOUT_CUTOFF_DATE,
            "holdout_2025_plus_sealed": True,
            "holdout_rows_analysed": 0,
            "max_official_api_usd_per_month": MAX_OFFICIAL_API_USD_PER_MONTH,
            "cliproxy_untouched": True,
        },
        "workload_assumptions": {
            "supervisor_runs_per_month": SUPERVISOR_RUNS_PER_MONTH,
            "supervisor_monthly_input_tokens": SUPERVISOR_MONTHLY_INPUT_TOKENS,
            "supervisor_monthly_output_tokens": SUPERVISOR_MONTHLY_OUTPUT_TOKENS,
            "budget_cap_usd_per_month": cap_usd,
            "usd_vnd_rate": rate,
            "q4_gb_per_billion": Q4_GB_PER_BILLION,
            "q8_gb_per_billion": Q8_GB_PER_BILLION,
            "local_runtime_overhead_gb": LOCAL_RUNTIME_OVERHEAD_GB,
        },
        "hardware": hw.to_dict(),
        "sources": {
            "openrouter": or_meta,
            "artificial_analysis": aa_meta,
            "hf_livebench": hf_livebench_meta,
            "hf_lmarena": hf_lmarena_meta,
        },
        "leaderboards": {
            "budget_macro_supervisor_monthly_usd": leaderboards["budget_macro_supervisor_monthly_usd"],
            "top_value_reasoning": leaderboards["top_value_reasoning"],
            "top_coding_audit": leaderboards["top_coding_audit"],
            "local_open_weight_fit": leaderboards["local_open_weight_fit"],
        },
        "leaderboard_summary": leaderboards["summary"],
        "price_delta": price_delta,
        "catalog_index": catalog_index,
    }

    if output_path is not None:
        digest = atomic_write_json(output_path, snapshot)
        snapshot["_output_path"] = str(output_path)
        snapshot["_output_sha256"] = digest

    return snapshot


# ==============================================================================
# CLI Entrypoint
# ==============================================================================


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Naqex Wave 4 Realtime AI Model Radar (OpenRouter + optional AA/HF + local hardware fit)."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path(".runtime/offensive4/ai/ai_model_radar_latest.json"),
        help="Destination JSON path for the radar snapshot.",
    )
    parser.add_argument(
        "--previous",
        type=Path,
        default=None,
        help="Optional previous snapshot JSON for price delta diff (defaults to --output if present).",
    )
    parser.add_argument(
        "--usd-vnd",
        type=float,
        default=DEFAULT_USD_VND_RATE,
        help=f"USD/VND exchange rate (default: {DEFAULT_USD_VND_RATE}).",
    )
    parser.add_argument(
        "--budget-cap-usd",
        type=float,
        default=MAX_OFFICIAL_API_USD_PER_MONTH,
        help=f"Monthly Macro Supervisor budget ceiling in USD (default: {MAX_OFFICIAL_API_USD_PER_MONTH}).",
    )
    parser.add_argument(
        "--top-n",
        type=int,
        default=DEFAULT_TOP_N,
        help=f"Number of ranked entries per leaderboard (default: {DEFAULT_TOP_N}).",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = _build_arg_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    snapshot = run_ai_model_radar(
        output_path=args.output,
        previous_snapshot_path=args.previous,
        usd_vnd_rate=args.usd_vnd,
        budget_cap_usd=args.budget_cap_usd,
        top_n=args.top_n,
    )
    or_meta = snapshot["sources"]["openrouter"]
    hw = snapshot["hardware"]
    top_budget = snapshot["leaderboards"]["budget_macro_supervisor_monthly_usd"][:3]
    summary = {
        "schema_version": snapshot["schema_version"],
        "generated_utc": snapshot["generated_utc"],
        "openrouter_raw_models": or_meta["raw_count"],
        "openrouter_valid_priced_models": or_meta["valid_priced_count"],
        "hardware": {
            "gpu_name": hw["gpu_name"],
            "gpu_vram_total_gb": hw["gpu_vram_total_gb"],
            "ram_total_gb": hw["ram_total_gb"],
            "cpu_cores": hw["cpu_cores"],
            "full_vram_budget_gb": hw["full_vram_budget_gb"],
            "hybrid_offload_budget_gb": hw["hybrid_offload_budget_gb"],
        },
        "secondary_sources": {
            "artificial_analysis": snapshot["sources"]["artificial_analysis"]["status"],
            "hf_livebench": snapshot["sources"]["hf_livebench"]["status"],
            "hf_lmarena": snapshot["sources"]["hf_lmarena"]["status"],
        },
        "top3_budget_macro_supervisor": [
            {
                "rank": row["rank"],
                "id": row["id"],
                "monthly_usd": row["monthly_usd"],
                "monthly_vnd": row["monthly_vnd"],
            }
            for row in top_budget
        ],
        "output_path": snapshot.get("_output_path"),
        "output_sha256": snapshot.get("_output_sha256"),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
