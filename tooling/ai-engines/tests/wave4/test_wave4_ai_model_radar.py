"""100% offline-mocked unit tests for Wave 4 AI Model Radar (W4-G13).

Runs under `python`, `python -O`, and `-m "not local_cache"` with ZERO live network calls
and ZERO live `nvidia-smi` subprocess invocations. Uses `unittest.TestCase` assertions so
every check remains active under `python -O`.
"""

from __future__ import annotations

import ast
import json
import math
import subprocess
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import patch

import httpx
from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)
from quant_factory.wave4 import ai_model_radar as radar

RADAR_SOURCE_PATH = Path(radar.__file__).resolve()


def _make_openrouter_model(
    model_id: str,
    *,
    name: str | None = None,
    prompt_per_1m: float = 0.20,
    completion_per_1m: float = 0.80,
    context_length: int = 128_000,
    reasoning: bool = False,
    structured_outputs: bool = True,
    tools: bool = True,
    hugging_face_id: str | None = None,
    modality: str = "text->text",
    created: int = 1_790_000_000,
) -> dict[str, Any]:
    params: list[str] = ["max_tokens", "temperature"]
    if structured_outputs:
        params.append("structured_outputs")
    if tools:
        params.append("tools")
    if reasoning:
        params.extend(["reasoning", "include_reasoning"])
    return {
        "id": model_id,
        "name": name or model_id,
        "context_length": context_length,
        "pricing": {
            "prompt": f"{prompt_per_1m / 1_000_000.0:.12f}",
            "completion": f"{completion_per_1m / 1_000_000.0:.12f}",
        },
        "architecture": {"modality": modality},
        "supported_parameters": params,
        "reasoning": {"mandatory": False, "default_enabled": True} if reasoning else None,
        "hugging_face_id": hugging_face_id,
        "created": created,
    }


def _sample_openrouter_payload() -> dict[str, Any]:
    return {
        "data": [
            # Dynamic OpenRouter sentinel router (-1/-1) cleanly excluded
            {
                "id": "openrouter/auto",
                "name": "OpenRouter Auto",
                "context_length": 200_000,
                "pricing": {"prompt": "-1", "completion": "-1"},
                "architecture": {"modality": "text->text"},
                "supported_parameters": ["max_tokens"],
            },
            # Ultra-cheap reasoning & structured output macro supervisor pick ($0.07/mo)
            _make_openrouter_model(
                "deepseek/deepseek-v4-flash",
                name="DeepSeek V4 Flash",
                prompt_per_1m=0.10,
                completion_per_1m=0.40,
                context_length=1_000_000,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                hugging_face_id="deepseek-ai/DeepSeek-V4-Flash",
                created=1_795_000_000,
            ),
            # Strong mid-budget coding + reasoning model ($2.10/mo <= $5.00 cap)
            _make_openrouter_model(
                "anthropic/claude-sonnet-4.6",
                name="Claude Sonnet 4.6",
                prompt_per_1m=3.00,
                completion_per_1m=15.00,
                context_length=1_000_000,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                created=1_795_000_000,
            ),
            # High-context coding specialist ($1.5925/mo)
            _make_openrouter_model(
                "openai/gpt-5.3-codex",
                name="GPT-5.3 Codex",
                prompt_per_1m=1.75,
                completion_per_1m=14.00,
                context_length=400_000,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                created=1_794_000_000,
            ),
            # Over-budget expensive reasoning model ($12.60/mo > $5.00 cap -> excluded from budget LB!)
            _make_openrouter_model(
                "openai/o3-pro",
                name="OpenAI o3-pro",
                prompt_per_1m=20.00,
                completion_per_1m=80.00,
                context_length=200_000,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                created=1_790_000_000,
            ),
            # Open-weight 8B model -> FULL_VRAM_FIT on RTX 2070 SUPER 8GB (Q4 = 5.10 GB <= 7.20 GB)
            _make_openrouter_model(
                "qwen/qwen3-8b",
                name="Qwen3 8B",
                prompt_per_1m=0.06,
                completion_per_1m=0.18,
                context_length=262_144,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                hugging_face_id="Qwen/Qwen3-8B",
                created=1_794_500_000,
            ),
            # Open-weight 14B model -> HYBRID_GPU_RAM_OFFLOAD (Q4 = 8.48 GB, > 7.20 GB and <= 22.0 GB)
            _make_openrouter_model(
                "qwen/qwen3-14b",
                name="Qwen3 14B",
                prompt_per_1m=0.08,
                completion_per_1m=0.24,
                context_length=131_072,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                hugging_face_id="Qwen/Qwen3-14B",
                created=1_794_000_000,
            ),
            # Open-weight 26B-A4B MoE -> HYBRID_GPU_RAM_OFFLOAD (total 26B -> Q4 = 15.22 GB <= 22.0 GB)
            _make_openrouter_model(
                "google/gemma-4-26b-a4b-it",
                name="Gemma 4 26B A4B",
                prompt_per_1m=0.09,
                completion_per_1m=0.30,
                context_length=262_144,
                reasoning=True,
                structured_outputs=True,
                tools=True,
                hugging_face_id="google/gemma-4-26b-a4b-it",
                created=1_795_100_000,
            ),
            # Open-weight 70B model -> TOO_LARGE (Q4 = 39.98 GB > 22.0 GB -> excluded from local fit LB)
            _make_openrouter_model(
                "meta-llama/llama-3.3-70b-instruct",
                name="Llama 3.3 70B",
                prompt_per_1m=0.30,
                completion_per_1m=0.90,
                context_length=131_072,
                reasoning=False,
                structured_outputs=True,
                tools=True,
                hugging_face_id="meta-llama/Llama-3.3-70B-Instruct",
                created=1_780_000_000,
            ),
            # Open-weight 4B model -> Q8 FULL_VRAM_FIT (Q8 = 4.85 GB <= 7.20 GB)
            _make_openrouter_model(
                "google/gemma-3-4b-it",
                name="Gemma 3 4B",
                prompt_per_1m=0.04,
                completion_per_1m=0.10,
                context_length=131_072,
                reasoning=False,
                structured_outputs=True,
                tools=False,
                hugging_face_id="google/gemma-3-4b-it",
                created=1_785_000_000,
            ),
            # Free and batch variants should not pollute paid supervisor leaderboard
            _make_openrouter_model(
                "qwen/qwen3-8b:free",
                name="Qwen3 8B Free",
                prompt_per_1m=0.0,
                completion_per_1m=0.0,
                context_length=262_144,
                reasoning=True,
                hugging_face_id="Qwen/Qwen3-8B",
            ),
            _make_openrouter_model(
                "openai/gpt-5.3-codex:batch",
                name="GPT-5.3 Codex Batch",
                prompt_per_1m=0.875,
                completion_per_1m=7.00,
                context_length=400_000,
                reasoning=True,
            ),
        ]
    }


def _rtx2070_hardware() -> radar.HardwareProfile:
    full_vram, hybrid = radar.compute_hardware_memory_budgets(8.0, 32.0)
    return radar.HardwareProfile(
        os_name="Windows",
        cpu_cores=6,
        ram_total_gb=32.0,
        ram_source="mock",
        gpu_detected=True,
        gpu_name="NVIDIA GeForce RTX 2070 SUPER",
        gpu_vram_total_gb=8.0,
        gpu_vram_free_gb=7.1,
        gpu_source="mock-nvidia-smi",
        full_vram_budget_gb=full_vram,
        hybrid_offload_budget_gb=hybrid,
    )


class TestWave4AIModelRadar(unittest.TestCase):
    """Comprehensive offline test suite for ai_model_radar.py (W4-G13)."""

    def test_hard_invariants_and_zero_ordersend(self) -> None:
        self.assertFalse(ORDER_SEND_CAPABLE)
        self.assertEqual(HOLDOUT_CUTOFF_DATE, "2024-12-31")
        self.assertEqual(MAX_OFFICIAL_API_USD_PER_MONTH, 5.0)
        self.assertEqual(radar.SUPERVISOR_RUNS_PER_MONTH, 44)
        self.assertEqual(radar.SUPERVISOR_MONTHLY_INPUT_TOKENS, 350_000)
        self.assertEqual(radar.SUPERVISOR_MONTHLY_OUTPUT_TOKENS, 70_000)
        # Ensure external local proxy port 8317 is never referenced in module source
        src = RADAR_SOURCE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("8317", src)
        self.assertNotIn("CLIProxyAPI", src)

    def test_ast_nvidia_smi_calls_always_pass_creationflags(self) -> None:
        """AST guard: every subprocess call invoking nvidia-smi MUST explicitly pass creationflags."""
        source = RADAR_SOURCE_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(RADAR_SOURCE_PATH))

        nvidia_calls: list[ast.Call] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            call_src = ast.get_source_segment(source, node) or ""
            if "nvidia-smi" in call_src and isinstance(node.func, ast.Attribute):
                if node.func.attr in ("run", "Popen", "check_output", "call", "check_call"):
                    nvidia_calls.append(node)

        self.assertGreaterEqual(len(nvidia_calls), 1, "Expected at least one subprocess call invoking nvidia-smi")
        for call in nvidia_calls:
            kw_names = {kw.arg for kw in call.keywords if kw.arg is not None}
            self.assertIn(
                "creationflags",
                kw_names,
                f"nvidia-smi subprocess call at line {call.lineno} must pass creationflags=_NO_WINDOW_FLAGS",
            )

    def test_monthly_supervisor_cost_exact_math_and_cap(self) -> None:
        """Verify 44 runs/mo = 0.35M in + 0.07M out cost math and VND conversion."""
        # Prompt $2.00/M -> 0.35 * 2.00 = $0.70; Completion $10.00/M -> 0.07 * 10.00 = $0.70 => $1.40/mo
        cost = radar.compute_monthly_supervisor_cost_usd(2.0 / 1_000_000.0, 10.0 / 1_000_000.0)
        self.assertAlmostEqual(cost, 1.40, places=6)
        self.assertEqual(radar.usd_to_vnd(cost, usd_vnd_rate=25_500.0), 35_700)

        # Boundary: exactly $5.00/mo -> $10/M prompt ($3.50) + $21.4285714286/M completion ($1.50)
        boundary = radar.compute_monthly_supervisor_cost_usd(10.0 / 1_000_000.0, 1.50 / 70_000.0)
        self.assertAlmostEqual(boundary, 5.00, places=5)

    def test_poisoned_pricing_fail_closed_rejection(self) -> None:
        """NaN, Inf, negative, bool, None, and malformed pricing MUST fail closed with ValueError."""
        poisoned_values: list[Any] = [
            float("nan"),
            float("inf"),
            float("-inf"),
            "NaN",
            "nan",
            "Infinity",
            "-Infinity",
            -0.000001,
            "-0.0001",
            -1,
            True,
            False,
            "true",
            "false",
            None,
            "",
            "not-a-number",
            {"nested": 1},
        ]
        for bad in poisoned_values:
            with self.subTest(bad=bad):
                with self.assertRaises(radar.PoisonedPricingError):
                    radar.validate_price_per_token(bad, field_name="test.prompt")

        # Poisoned pricing inside OpenRouter catalog payload must fail closed!
        for bad_prompt in ("NaN", -0.0005, True, False, "Infinity", None):
            payload = {
                "data": [
                    {
                        "id": "evil/poisoned-model",
                        "name": "Evil Model",
                        "context_length": 128_000,
                        "pricing": {"prompt": bad_prompt, "completion": "0.000001"},
                    }
                ]
            }
            with self.subTest(catalog_bad_prompt=bad_prompt):
                with self.assertRaises(radar.PoisonedPricingError):
                    radar.parse_openrouter_catalog(payload)

        # Asymmetric (-1 prompt, positive completion) is NOT a valid dynamic router -> fail-closed!
        asym_payload = {
            "data": [
                {
                    "id": "evil/asym-neg",
                    "name": "Asym Neg",
                    "context_length": 64_000,
                    "pricing": {"prompt": "-1", "completion": "0.000001"},
                }
            ]
        }
        with self.assertRaises(radar.PoisonedPricingError):
            radar.parse_openrouter_catalog(asym_payload)

        # Boolean context_length must also fail-closed
        bool_ctx_payload = {
            "data": [
                {
                    "id": "evil/bool-ctx",
                    "name": "Bool Ctx",
                    "context_length": True,
                    "pricing": {"prompt": "0.000001", "completion": "0.000002"},
                }
            ]
        }
        with self.assertRaises(radar.PoisonedPricingError):
            radar.parse_openrouter_catalog(bool_ctx_payload)

    def test_hardware_detection_mocked_rtx2070_and_no_gpu_fallback(self) -> None:
        """Verify RTX 2070 SUPER 8GB / 32GB budgets (7.2GB / 22.0GB) and graceful no-GPU fallback."""
        mock_proc = subprocess.CompletedProcess(
            args=["nvidia-smi"],
            returncode=0,
            stdout="NVIDIA GeForce RTX 2070 SUPER, 8192, 7168\n",
            stderr="",
        )
        with (
            patch.object(radar.subprocess, "run", return_value=mock_proc) as mock_run,
            patch.object(radar, "_detect_system_ram_gb", return_value=(32.0, "mock")),
            patch.object(radar.os, "cpu_count", return_value=6),
        ):
            hw = radar.detect_local_hardware()
            self.assertTrue(hw.gpu_detected)
            self.assertEqual(hw.gpu_name, "NVIDIA GeForce RTX 2070 SUPER")
            self.assertEqual(hw.gpu_vram_total_gb, 8.0)
            self.assertEqual(hw.gpu_vram_free_gb, 7.0)
            self.assertEqual(hw.ram_total_gb, 32.0)
            self.assertEqual(hw.cpu_cores, 6)
            self.assertEqual(hw.full_vram_budget_gb, 7.2)
            self.assertEqual(hw.hybrid_offload_budget_gb, 22.0)
            # Verify creationflags kwarg was actually passed at runtime
            _, kwargs = mock_run.call_args
            self.assertIn("creationflags", kwargs)

        # Exact boundary classification checks
        self.assertEqual(radar.classify_memory_fit(7.2, hw), radar.FIT_FULL_VRAM)
        self.assertEqual(radar.classify_memory_fit(7.21, hw), radar.FIT_HYBRID_OFFLOAD)
        self.assertEqual(radar.classify_memory_fit(22.0, hw), radar.FIT_HYBRID_OFFLOAD)
        self.assertEqual(radar.classify_memory_fit(22.01, hw), radar.FIT_TOO_LARGE)

        # MoE extraction check: Llama-4-Maverick 17B-128E must NOT look like a 17B dense model
        total_b, active_b, is_moe = radar.extract_parameter_count(
            "meta-llama/llama-4-maverick", "Llama 4 Maverick 17B 128E", "meta-llama/Llama-4-Maverick-17B-128E"
        )
        self.assertTrue(is_moe)
        self.assertIsNotNone(total_b)
        self.assertGreater(total_b or 0.0, 100.0)
        self.assertEqual(active_b, 17.0)
        fit_maverick = radar.assess_local_model_fit(total_b or 400.0, hw, active_params_b=active_b, is_moe=is_moe)
        self.assertEqual(fit_maverick.q4_fit_tier, radar.FIT_TOO_LARGE)

        # Graceful no-GPU fallback when nvidia-smi is missing
        with (
            patch.object(radar.subprocess, "run", side_effect=FileNotFoundError("nvidia-smi not found")),
            patch.object(radar, "_detect_system_ram_gb", return_value=(16.0, "mock")),
        ):
            hw_nogpu = radar.detect_local_hardware()
            self.assertFalse(hw_nogpu.gpu_detected)
            self.assertIsNone(hw_nogpu.gpu_name)
            self.assertEqual(hw_nogpu.gpu_vram_total_gb, 0.0)
            self.assertEqual(hw_nogpu.full_vram_budget_gb, 0.0)
            self.assertGreater(hw_nogpu.hybrid_offload_budget_gb, 0.0)

    def test_four_leaderboards_and_secondary_graceful_degradation(self) -> None:
        """Full mocked pipeline: 4 leaderboards, <= $5 cap, and clean degradation of AA/HF."""
        or_payload = _sample_openrouter_payload()

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == radar.OPENROUTER_MODELS_URL:
                return httpx.Response(200, json=or_payload)
            if url == radar.HF_LIVEBENCH_URL:
                # Simulate rate limit (429) on HF LiveBench
                return httpx.Response(429, json={"error": "rate limited"})
            if url == radar.HF_LMARENA_URL:
                # Simulate malformed JSON on HF LMArena
                return httpx.Response(200, content=b"{not valid json", headers={"content-type": "application/json"})
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            snap = radar.run_ai_model_radar(
                http_client=client,
                hardware_profile=_rtx2070_hardware(),
                artificial_analysis_api_key="",  # Missing key -> DEGRADED_MISSING_KEY
                retry_backoff_sec=0.0,
            )

        # Verify OpenRouter source & exclusion of openrouter/auto sentinel
        self.assertEqual(snap["sources"]["openrouter"]["status"], radar.STATUS_OK)
        self.assertEqual(snap["sources"]["openrouter"]["raw_count"], len(or_payload["data"]))
        self.assertEqual(snap["sources"]["openrouter"]["excluded_dynamic_routers"], ["openrouter/auto"])

        # Verify secondary graceful degradations NEVER crash the radar
        self.assertEqual(snap["sources"]["artificial_analysis"]["status"], radar.STATUS_DEGRADED_MISSING_KEY)
        self.assertEqual(snap["sources"]["hf_livebench"]["status"], radar.STATUS_DEGRADED_RATE_LIMITED)
        self.assertEqual(snap["sources"]["hf_lmarena"]["status"], radar.STATUS_DEGRADED_SCHEMA_CHANGED)

        # Verify all 4 leaderboards exist and are populated
        lbs = snap["leaderboards"]
        self.assertEqual(
            set(lbs.keys()),
            {
                "budget_macro_supervisor_monthly_usd",
                "top_value_reasoning",
                "top_coding_audit",
                "local_open_weight_fit",
            },
        )
        for lb_name, rows in lbs.items():
            self.assertGreater(len(rows), 0, f"Leaderboard {lb_name} should be non-empty")

        # Verify strict <= $5.00/mo budget cap & exact VND math on budget leaderboard
        budget_ids = {r["id"] for r in lbs["budget_macro_supervisor_monthly_usd"]}
        self.assertNotIn("openai/o3-pro", budget_ids, "Over-budget $12.60/mo model must be excluded")
        self.assertNotIn("qwen/qwen3-8b:free", budget_ids, ":free variant must be excluded")
        self.assertNotIn("openai/gpt-5.3-codex:batch", budget_ids, ":batch variant must be excluded")
        for row in lbs["budget_macro_supervisor_monthly_usd"]:
            self.assertLessEqual(row["monthly_usd"], 5.0)
            self.assertTrue(row["within_budget_cap"])
            self.assertEqual(row["monthly_vnd"], int(round(row["monthly_usd"] * 25_500.0)))

        # Verify local open-weight fit tiers (8B & 4B FULL_VRAM, 14B & 26B-A4B HYBRID, 70B TOO_LARGE excluded)
        local_by_id = {r["id"]: r for r in lbs["local_open_weight_fit"]}
        self.assertIn("qwen/qwen3-8b", local_by_id)
        self.assertEqual(local_by_id["qwen/qwen3-8b"]["q4_fit_tier"], radar.FIT_FULL_VRAM)
        self.assertEqual(local_by_id["google/gemma-3-4b-it"]["recommended_quant"], "Q8_0")
        self.assertEqual(local_by_id["qwen/qwen3-14b"]["q4_fit_tier"], radar.FIT_HYBRID_OFFLOAD)
        self.assertEqual(local_by_id["google/gemma-4-26b-a4b-it"]["q4_fit_tier"], radar.FIT_HYBRID_OFFLOAD)
        self.assertNotIn("meta-llama/llama-3.3-70b-instruct", local_by_id)
        self.assertEqual(snap["leaderboard_summary"]["local_too_large_excluded_count"], 1)

    def test_secondary_timeout_and_aa_schema_change_and_secret_non_leakage(self) -> None:
        """Verify AA schema change / timeout degradation and ensure API key NEVER leaks to output."""
        fake_secret = "aa_test_dummy_key_not_a_real_token_12345"
        or_payload = _sample_openrouter_payload()

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == radar.OPENROUTER_MODELS_URL:
                return httpx.Response(200, json=or_payload)
            if url == radar.ARTIFICIAL_ANALYSIS_MODELS_URL:
                # Verify key passed via header, return unexpected schema
                self.assertEqual(request.headers.get("x-api-key"), fake_secret)
                return httpx.Response(200, json={"unexpected_root": []})
            if url == radar.HF_LIVEBENCH_URL:
                raise httpx.ReadTimeout("simulated timeout")
            if url == radar.HF_LMARENA_URL:
                return httpx.Response(
                    200,
                    json={
                        "id": "lmarena-ai/chatbot-arena-leaderboard",
                        "lastModified": "2026-11-01T00:00:00Z",
                    },
                )
            return httpx.Response(404)

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            snap = radar.run_ai_model_radar(
                http_client=client,
                hardware_profile=_rtx2070_hardware(),
                artificial_analysis_api_key=fake_secret,
                retry_backoff_sec=0.0,
            )

        self.assertEqual(snap["sources"]["artificial_analysis"]["status"], radar.STATUS_DEGRADED_SCHEMA_CHANGED)
        self.assertEqual(snap["sources"]["hf_livebench"]["status"], radar.STATUS_DEGRADED_NETWORK_ERROR)
        self.assertEqual(snap["sources"]["hf_lmarena"]["status"], radar.STATUS_OK)

        # Ensure API key NEVER appears anywhere in serialized snapshot
        serialized = json.dumps(snap)
        self.assertNotIn(fake_secret, serialized)

    def test_openrouter_retry_once_recovers_from_transient_error(self) -> None:
        """Primary OpenRouter fetch retries once on transient network timeout and succeeds."""
        calls = {"openrouter": 0}
        or_payload = _sample_openrouter_payload()

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == radar.OPENROUTER_MODELS_URL:
                calls["openrouter"] += 1
                if calls["openrouter"] == 1:
                    raise httpx.ConnectTimeout("transient first attempt failure")
                return httpx.Response(200, json=or_payload)
            return httpx.Response(200, json={"id": "ok-meta"})

        transport = httpx.MockTransport(handler)
        with httpx.Client(transport=transport) as client:
            snap = radar.run_ai_model_radar(
                http_client=client,
                hardware_profile=_rtx2070_hardware(),
                artificial_analysis_api_key="",
                retries=1,
                retry_backoff_sec=0.0,
            )
        self.assertEqual(calls["openrouter"], 2)
        self.assertEqual(snap["sources"]["openrouter"]["attempts"], 2)
        self.assertEqual(snap["sources"]["openrouter"]["status"], radar.STATUS_OK)

    def test_price_delta_tracker_new_removed_and_price_drop(self) -> None:
        """Verify price delta detects new_models, removed_models, price_drop, and price_increase."""
        prev_snapshot = {
            "generated_utc": "2026-11-20T00:00:00Z",
            "catalog_index": {
                "deepseek/deepseek-v4-flash": {
                    "prompt_usd_per_1m": 0.20,
                    "completion_usd_per_1m": 0.80,
                    "monthly_supervisor_usd": 0.126,
                    "context_length": 1_000_000,
                },
                "anthropic/claude-sonnet-4.6": {
                    "prompt_usd_per_1m": 3.00,
                    "completion_usd_per_1m": 15.00,
                    "monthly_supervisor_usd": 2.10,
                    "context_length": 1_000_000,
                },
                "legacy/deprecated-model": {
                    "prompt_usd_per_1m": 1.00,
                    "completion_usd_per_1m": 2.00,
                    "monthly_supervisor_usd": 0.49,
                    "context_length": 32_000,
                },
            },
        }
        curr_index = {
            # 50% price drop!
            "deepseek/deepseek-v4-flash": {
                "prompt_usd_per_1m": 0.10,
                "completion_usd_per_1m": 0.40,
                "monthly_supervisor_usd": 0.063,
                "context_length": 1_000_000,
            },
            # +20% price increase
            "anthropic/claude-sonnet-4.6": {
                "prompt_usd_per_1m": 3.60,
                "completion_usd_per_1m": 18.00,
                "monthly_supervisor_usd": 2.52,
                "context_length": 1_000_000,
            },
            # Brand new model
            "qwen/qwen4-max": {
                "prompt_usd_per_1m": 1.50,
                "completion_usd_per_1m": 4.50,
                "monthly_supervisor_usd": 0.84,
                "context_length": 1_000_000,
            },
        }

        delta = radar.compute_price_delta(curr_index, prev_snapshot)
        self.assertTrue(delta["has_previous_snapshot"])
        self.assertEqual(delta["new_models"], ["qwen/qwen4-max"])
        self.assertEqual(delta["removed_models"], ["legacy/deprecated-model"])
        self.assertEqual(delta["counts"]["price_changes"], 2)
        self.assertEqual(delta["counts"]["price_drops"], 1)
        self.assertEqual(delta["counts"]["price_increases"], 1)

        changes_by_id = {c["id"]: c for c in delta["price_changes_pct"]}
        self.assertEqual(changes_by_id["deepseek/deepseek-v4-flash"]["direction"], "PRICE_DROP")
        self.assertAlmostEqual(changes_by_id["deepseek/deepseek-v4-flash"]["monthly_delta_pct"], -50.0, places=2)
        self.assertEqual(changes_by_id["anthropic/claude-sonnet-4.6"]["direction"], "PRICE_INCREASE")
        self.assertAlmostEqual(changes_by_id["anthropic/claude-sonnet-4.6"]["monthly_delta_pct"], 20.0, places=2)
        # Ensure all numeric delta values are finite (no NaN/Inf)
        for ch in delta["price_changes_pct"]:
            for key in ("prompt_delta_pct", "completion_delta_pct", "monthly_delta_pct"):
                if ch[key] is not None:
                    self.assertTrue(math.isfinite(ch[key]))

    def test_atomic_write_and_second_run_self_diff(self) -> None:
        """End-to-end offline persistence: run 1 writes snapshot, run 2 detects price drop cleanly."""
        payload_v1 = _sample_openrouter_payload()
        payload_v2 = _sample_openrouter_payload()
        # Drop deepseek-v4-flash price by 50% in run 2 and add a new model
        for item in payload_v2["data"]:
            if item["id"] == "deepseek/deepseek-v4-flash":
                item["pricing"]["prompt"] = f"{0.05 / 1_000_000.0:.12f}"
                item["pricing"]["completion"] = f"{0.20 / 1_000_000.0:.12f}"
        payload_v2["data"].append(
            _make_openrouter_model("google/gemini-4-flash", prompt_per_1m=0.15, completion_per_1m=0.60, reasoning=True)
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "ai_model_radar_latest.json"

            def _make_client(payload: dict[str, Any]) -> httpx.Client:
                def handler(request: httpx.Request) -> httpx.Response:
                    if str(request.url) == radar.OPENROUTER_MODELS_URL:
                        return httpx.Response(200, json=payload)
                    return httpx.Response(200, json={"id": "hf/public-meta", "lastModified": "2026-11-27T00:00:00Z"})

                return httpx.Client(transport=httpx.MockTransport(handler))

            with _make_client(payload_v1) as c1:
                snap1 = radar.run_ai_model_radar(
                    output_path=out_path,
                    http_client=c1,
                    hardware_profile=_rtx2070_hardware(),
                    artificial_analysis_api_key="",
                    retry_backoff_sec=0.0,
                )
            self.assertTrue(out_path.is_file())
            self.assertFalse(snap1["price_delta"]["has_previous_snapshot"])

            with _make_client(payload_v2) as c2:
                snap2 = radar.run_ai_model_radar(
                    output_path=out_path,
                    http_client=c2,
                    hardware_profile=_rtx2070_hardware(),
                    artificial_analysis_api_key="",
                    retry_backoff_sec=0.0,
                )
            self.assertTrue(snap2["price_delta"]["has_previous_snapshot"])
            self.assertEqual(snap2["price_delta"]["new_models"], ["google/gemini-4-flash"])
            self.assertEqual(snap2["price_delta"]["counts"]["price_drops"], 1)
            drop = snap2["price_delta"]["price_changes_pct"][0]
            self.assertEqual(drop["id"], "deepseek/deepseek-v4-flash")
            self.assertAlmostEqual(drop["monthly_delta_pct"], -50.0, places=2)

    def test_artificial_analysis_valid_enrichment_and_retry_exhaustion(self) -> None:
        """Verify valid AA v2 enrichment populates indexes, and OpenRouter retry exhaustion fails closed."""
        or_payload = _sample_openrouter_payload()
        aa_payload = {
            "data": [
                {
                    "slug": "claude-sonnet-4-6",
                    "name": "Claude Sonnet 4.6",
                    "evaluations": {
                        "artificial_analysis_intelligence_index": 84.5,
                        "artificial_analysis_coding_index": 89.2,
                        "artificial_analysis_math_index": 78.0,
                    },
                    "median_output_tokens_per_second": 95.4,
                }
            ]
        }

        def ok_handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == radar.OPENROUTER_MODELS_URL:
                return httpx.Response(200, json=or_payload)
            if url == radar.ARTIFICIAL_ANALYSIS_MODELS_URL:
                return httpx.Response(200, json=aa_payload)
            return httpx.Response(200, json={"id": "hf/meta", "lastModified": "2026-11-27T00:00:00Z"})

        with httpx.Client(transport=httpx.MockTransport(ok_handler)) as client:
            snap = radar.run_ai_model_radar(
                http_client=client,
                hardware_profile=_rtx2070_hardware(),
                artificial_analysis_api_key="dummy-aa-key-for-unit-test",
                retry_backoff_sec=0.0,
            )

        self.assertEqual(snap["sources"]["artificial_analysis"]["status"], radar.STATUS_OK)
        self.assertEqual(snap["sources"]["artificial_analysis"]["enriched_models_count"], 1)
        coding_by_id = {r["id"]: r for r in snap["leaderboards"]["top_coding_audit"]}
        self.assertAlmostEqual(coding_by_id["anthropic/claude-sonnet-4.6"]["aa_coding_index"], 89.2, places=2)

        # Retry exhaustion on primary OpenRouter endpoint must raise fail-closed
        attempts = {"count": 0}

        def fail_handler(request: httpx.Request) -> httpx.Response:
            attempts["count"] += 1
            raise httpx.ConnectTimeout("persistent timeout")

        with httpx.Client(transport=httpx.MockTransport(fail_handler)) as fail_client:
            with self.assertRaises(httpx.ConnectTimeout):
                radar.run_ai_model_radar(
                    http_client=fail_client,
                    hardware_profile=_rtx2070_hardware(),
                    retries=1,
                    retry_backoff_sec=0.0,
                )
        self.assertEqual(attempts["count"], 2)

    def test_cli_main_offline_mocked(self) -> None:
        """Verify CLI entrypoint prints clean summary JSON and returns exit code 0 offline."""
        or_payload = _sample_openrouter_payload()

        def handler(request: httpx.Request) -> httpx.Response:
            if str(request.url) == radar.OPENROUTER_MODELS_URL:
                return httpx.Response(200, json=or_payload)
            return httpx.Response(200, json={"id": "hf/meta"})

        with tempfile.TemporaryDirectory() as tmpdir:
            out_path = Path(tmpdir) / "radar.json"
            mock_client = httpx.Client(transport=httpx.MockTransport(handler))
            with (
                patch.object(radar.httpx, "Client", return_value=mock_client),
                patch.object(radar, "detect_local_hardware", return_value=_rtx2070_hardware()),
                patch.dict(radar.os.environ, {radar.ARTIFICIAL_ANALYSIS_ENV_VAR: ""}, clear=False),
            ):
                rc = radar.main(["--output", str(out_path), "--top-n", "5"])
            self.assertEqual(rc, 0)
            self.assertTrue(out_path.is_file())
            written = json.loads(out_path.read_text(encoding="utf-8"))
            self.assertEqual(written["schema_version"], radar.SCHEMA_VERSION)
            self.assertEqual(written["hard_invariants"]["order_send_count"], 0)
            self.assertEqual(written["hard_invariants"]["holdout_cutoff_date"], "2024-12-31")


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
