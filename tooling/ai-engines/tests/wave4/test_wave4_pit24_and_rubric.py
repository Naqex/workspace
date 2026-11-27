"""Offline Unit & Local-Cache Artifact Tests for Wave 4 PIT-24 & 6-Criteria AI Rubric (W4-G14).

Covers:
  1. Offline unit tests (``-m "not local_cache"``, ``python``, ``python -O``):
     - Hard safety invariants, AST zero bare ``assert``s (``[ARCH-02]``), AST
       ``creationflags`` on every ``subprocess`` call, zero ``MetaTrader5`` import,
       zero legacy hardcoded paths, LF-only & zero BOM hygiene.
     - Fail-closed port ``8317`` blocking & chat-only candidate model selection.
     - Mocked standalone ``17852`` end-to-end runs covering:
       * ``LIVE_24_PASS`` (24/24 clean prompts, schema valid, regime agreement,
         immutable ``managed.yaml``, untouched port ``8317``, stopped ``17852``,
         initialized ``prospective_shadow_ledger.json``).
       * ``PARTIAL_RATE_LIMITED_429`` (immediate stop on HTTP 429 with 0 retries).
       * ``SKIP_AUTH_EXPIRED`` (HTTP 401, HTTP 403, and proxy-wrapped auth expiry).
     - Complete 6-criteria x 5-architecture benchmark + Alpha Arena / FinRL / Qlib status.
  2. Local-cache artifact verification (``@pytest.mark.local_cache``):
     - Validates ``.runtime/offensive4/ai/wave4_pit24_and_ai_rubric.json`` and
       ``.runtime/offensive4/ai/prospective_shadow_ledger.json``.

Uses ``unittest.TestCase`` assertions exclusively (zero bare ``assert``s) so every
check remains 100% active under ``python -O``.
"""

from __future__ import annotations

import ast
import hashlib
import json
import tempfile
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import httpx
import pytest
import yaml
from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)
from quant_factory.wave4 import macro_ai_supervisor as sup
from quant_factory.wave4 import run_macro_pit24_and_rubric as runner

RUNNER_SOURCE_PATH = Path(runner.__file__).resolve()
_SUBPROCESS_CALL_ATTRS: frozenset[str] = frozenset({"run", "Popen", "call", "check_call", "check_output"})


def _sample_radar_payload() -> dict[str, Any]:
    return {
        "schema_version": "naqex-wave4-ai-model-radar-v1",
        "workload_assumptions": {
            "supervisor_runs_per_month": 44,
            "supervisor_monthly_input_tokens": 350_000,
            "supervisor_monthly_output_tokens": 70_000,
            "budget_cap_usd_per_month": 5.0,
            "usd_vnd_rate": 25_500.0,
        },
        "hardware": {
            "gpu_name": "NVIDIA GeForce RTX 2070 SUPER",
            "gpu_vram_total_gb": 8.0,
            "full_vram_budget_gb": 7.2,
            "ram_total_gb": 31.95,
            "hybrid_offload_budget_gb": 21.96,
        },
        "leaderboard_summary": {
            "budget_eligible_count": 302,
            "local_full_vram_fit_count": 12,
            "local_hybrid_offload_count": 31,
        },
        "leaderboards": {
            "budget_macro_supervisor_monthly_usd": [
                {
                    "rank": 1,
                    "id": "qwen/qwen3.7-flash",
                    "prompt_usd_per_1m": 0.03,
                    "completion_usd_per_1m": 0.13,
                    "monthly_usd": 0.0196,
                    "monthly_vnd": 500,
                    "context_length": 1_000_000,
                },
                {
                    "rank": 2,
                    "id": "deepseek/deepseek-v4.1-flash",
                    "prompt_usd_per_1m": 0.0507,
                    "completion_usd_per_1m": 0.2028,
                    "monthly_usd": 0.0319,
                    "monthly_vnd": 814,
                    "context_length": 1_048_576,
                },
            ],
            "top_value_reasoning": [
                {
                    "rank": 1,
                    "id": "openai/gpt-6-luna-pro",
                    "prompt_usd_per_1m": 0.10,
                    "completion_usd_per_1m": 0.50,
                    "monthly_supervisor_usd": 0.07,
                }
            ],
            "local_open_weight_fit": [
                {
                    "rank": 1,
                    "id": "qwen/qwen3.5-9b",
                    "q4_estimated_gb": 5.66,
                    "q4_fit_tier": "FULL_VRAM_FIT",
                }
            ],
        },
    }


def _sample_v8_managed_yaml(*, port: int = 17852, request_retry: int = 2) -> str:
    return yaml.safe_dump(
        {
            "config-version": 8,
            "access": {"api-keys": ["local-loopback-test-key-pit24"]},
            "server": {"host": "127.0.0.1", "port": port, "max-request-body-bytes": 8388608},
            "routing": {
                "retry": {
                    "request-retry": request_retry,
                    "max-retry-interval": 5,
                    "max-retry-credentials": 1,
                },
                "strategy": "round-robin",
            },
            "api-keys": {
                "openai-compatibility": [
                    {
                        "name": "BlockedProxyA",
                        "base-url": "https://api.poolai.win/v1",
                        "keys": [{"api-key": "fake-blocked-key-1"}],
                    }
                ],
                "claude": [
                    {
                        "name": "BlockedProxyB",
                        "base-url": "https://api.poolai.win",
                        "keys": [{"api-key": "fake-blocked-key-2"}],
                    }
                ],
            },
        },
        sort_keys=False,
    )


def _write_temp_gateway_fixture(tmp_dir: Path, *, port: int = 17852) -> tuple[Path, Path, Path]:
    gw_home = tmp_dir / "gw_home"
    gw_home.mkdir(parents=True, exist_ok=True)
    fake_exe = gw_home / "cli-proxy-api.exe"
    fake_exe.write_bytes(b"FAKE_GATEWAY_BINARY")
    managed_yaml = gw_home / "managed.yaml"
    managed_yaml.write_text(_sample_v8_managed_yaml(port=port), encoding="utf-8")

    owner_json = tmp_dir / "gateway-owner.json"
    owner_json.write_text(
        json.dumps(
            {
                "port": port,
                "executable": str(fake_exe),
                "home": str(gw_home),
                "configPath": str(managed_yaml),
                "pid": 888888,
                "status": "stopped",
                "release": "v8.0.52-mock",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    radar_json = tmp_dir / "ai_model_radar_latest.json"
    radar_json.write_text(json.dumps(_sample_radar_payload(), indent=2), encoding="utf-8")
    return owner_json, managed_yaml, radar_json


def _decision_payload_for_prompt(prompt_text: str) -> str:
    if any(f"SCEN_{i:02d}" in prompt_text for i in range(1, 7)):
        rm, tag = 0.0, "CRISIS_HALT"
    elif any(f"SCEN_{i:02d}" in prompt_text for i in range(7, 13)):
        rm, tag = 0.5, "HIGH_STRESS_DEFENSIVE"
    elif any(f"SCEN_{i:02d}" in prompt_text for i in range(13, 19)):
        rm, tag = 0.75, "CAUTION_REDUCED"
    else:
        rm, tag = 1.0, "CALM_NORMAL"
    return json.dumps(
        {
            "risk_mult": rm,
            "regime_tag": tag,
            "confidence": 0.85,
            "reasoning_bullets": [
                "Cross-asset anonymized z-scores classified deterministically.",
                "Advisory multiplier only; PropGuard hard stops remain authoritative.",
            ],
            "order_send_capable": False,
        }
    )


class TestWave4Pit24AndRubricOffline(unittest.TestCase):
    """Offline mocked unit tests (run cleanly under -m 'not local_cache' and python -O)."""

    def test_01_hard_invariants_ast_creationflags_zero_bare_asserts_and_lf_hygiene(self) -> None:
        self.assertFalse(ORDER_SEND_CAPABLE)
        self.assertEqual(sup.ORDER_SEND_COUNT, 0)
        self.assertEqual(runner.SPEND_VND, 0)
        self.assertEqual(HOLDOUT_CUTOFF_DATE, "2024-12-31")
        self.assertEqual(runner.HOLDOUT_ROWS_ANALYSED, 0)
        self.assertEqual(MAX_OFFICIAL_API_USD_PER_MONTH, 5.0)
        self.assertEqual(sup.FORBIDDEN_EXTERNAL_CLIPROXY_PORT, 8317)

        raw = RUNNER_SOURCE_PATH.read_bytes()
        self.assertFalse(raw.startswith(b"\xef\xbb\xbf"), "UTF-8 BOM forbidden")
        self.assertNotIn(b"\r\n", raw, "CRLF line endings forbidden")

        src = raw.decode("utf-8")
        self.assertNotIn("mt5-ai-gateway", src)
        self.assertNotIn("mt5-tradingview-backtester", src)

        tree = ast.parse(src, filename=str(RUNNER_SOURCE_PATH))
        bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        self.assertEqual(bare_asserts, [], f"Forbidden bare asserts [ARCH-02]: {bare_asserts}")

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self.assertNotEqual(alias.name, "MetaTrader5")
            elif isinstance(node, ast.ImportFrom):
                self.assertNotEqual(node.module, "MetaTrader5")

        # AST guard: EVERY subprocess call MUST explicitly pass creationflags=
        missing_cf: list[str] = []
        sub_calls = 0
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            if (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id == "subprocess"
                and fn.attr in _SUBPROCESS_CALL_ATTRS
            ):
                sub_calls += 1
                if not any(kw.arg == "creationflags" for kw in node.keywords):
                    missing_cf.append(f"line {node.lineno}: subprocess.{fn.attr}")
        self.assertGreaterEqual(sub_calls, 1)
        self.assertEqual(missing_cf, [], f"Subprocess calls missing creationflags: {missing_cf}")

    def test_02_port_8317_hard_blocked_and_chat_model_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            owner_json, _, radar_json = _write_temp_gateway_fixture(Path(td), port=17852)
            with self.assertRaises(sup.SecurityError):
                runner.run_pit24_over_client(owner_json_path=owner_json, expected_port=8317)
            with self.assertRaises(sup.SecurityError):
                runner.run_live_pit24_and_generate_artifacts(
                    owner_json_path=owner_json,
                    radar_snapshot_path=radar_json,
                    expected_port=8317,
                )

        # Non-chat models (image/tts/embedding/auto-review) MUST be excluded
        cands = runner.select_candidate_models(
            [
                "gpt-image-2.5",
                "codex-auto-review",
                "gemini-3.1-flash-image",
                "whisper-1",
                "text-embedding-3-large",
                "gpt-6-luna",
                "gpt-5.6-terra",
                "gemini-3-flash",
                "claude-sonnet-4-6",
            ]
        )
        self.assertEqual(cands, ["gpt-6-luna", "gemini-3-flash", "claude-sonnet-4-6"])
        for m in cands:
            self.assertNotIn("image", m)
            self.assertNotIn("auto-review", m)

    def test_03_mocked_gateway_live_24_pass_end_to_end(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            owner_json, managed_yaml, radar_json = _write_temp_gateway_fixture(tmp, port=17852)
            paperclip_dir = tmp / "paperclip"
            sanitized_path = paperclip_dir / "wave4_sanitized_gateway.yaml"
            pid_file = paperclip_dir / "wave4_gateway_17852_pid.json"
            ledger_out = tmp / "prospective_shadow_ledger.json"
            report_out = tmp / "wave4_pit24_and_ai_rubric.json"
            sha_before = hashlib.sha256(managed_yaml.read_bytes()).hexdigest()

            fake_proc = MagicMock()
            fake_proc.pid = 54321
            fake_proc.poll.return_value = None
            fake_proc.returncode = 0

            post_count = 0

            def _handler(req: httpx.Request) -> httpx.Response:
                nonlocal post_count
                if req.url.path == "/v1/models":
                    return httpx.Response(
                        200,
                        json={"data": [{"id": "gpt-image-2.5"}, {"id": "gpt-6-luna"}, {"id": "gemini-3-flash"}]},
                    )
                post_count += 1
                body = json.loads(req.content.decode("utf-8"))
                user_prompt = body["messages"][1]["content"]
                # Every dispatched prompt MUST pass anti-contamination guard
                sup.assert_anonymized_prompt_clean(user_prompt)
                return httpx.Response(
                    200,
                    json={"choices": [{"message": {"content": _decision_payload_for_prompt(user_prompt)}}]},
                )

            # Simulate an external Windows 8317 listener staying completely untouched before & after
            def _fake_listeners(ports: Any) -> dict[int, list[dict[str, Any]]]:
                out: dict[int, list[dict[str, Any]]] = {int(p): [] for p in ports}
                if 8317 in out:
                    out[8317] = [{"local_address": "127.0.0.1", "port": 8317, "pid": 9999}]
                return out

            port_checks = iter([False, True, False])
            client = httpx.Client(transport=httpx.MockTransport(_handler))
            try:
                with (
                    patch.object(sup, "_is_pid_alive", return_value=False),
                    patch.object(runner, "_is_pid_alive", return_value=False),
                    patch.object(sup, "_is_tcp_port_open", side_effect=lambda *_a, **_kw: next(port_checks)),
                    patch.object(runner, "_is_tcp_port_open", side_effect=lambda *_a, **_kw: next(port_checks)),
                    patch.object(sup.subprocess, "Popen", return_value=fake_proc),
                ):
                    report = runner.run_live_pit24_and_generate_artifacts(
                        owner_json_path=owner_json,
                        sanitized_yaml_path=sanitized_path,
                        log_dir=paperclip_dir,
                        pid_file_path=pid_file,
                        radar_snapshot_path=radar_json,
                        ledger_out_path=ledger_out,
                        report_out_path=report_out,
                        http_client=client,
                        inter_request_delay_sec=0.0,
                        listener_snapshot_fn=_fake_listeners,
                    )
            finally:
                client.close()

            self.assertEqual(post_count, 24)
            fake_proc.terminate.assert_called_once()
            self.assertTrue(report_out.is_file())
            self.assertTrue(ledger_out.is_file())

            gsv = report["gateway_safety_verification"]
            self.assertFalse(gsv["port_8317_touched"])
            self.assertTrue(gsv["port_8317_listeners_identical"])
            self.assertEqual(gsv["port_8317_listeners_before"][0]["pid"], 9999)
            self.assertTrue(gsv["port_17852_stopped_after"])
            self.assertTrue(gsv["managed_yaml_sha256_unchanged"])
            self.assertEqual(gsv["managed_yaml_sha256_before"], sha_before)
            self.assertEqual(gsv["managed_yaml_sha256_after"], sha_before)
            self.assertFalse(gsv["poolai_present"])
            self.assertEqual(gsv["request_retry"], 0)
            self.assertTrue(gsv["sanitized_temp_cleaned"])
            self.assertEqual(gsv["spawned_pid"], 54321)
            self.assertEqual(gsv["stopped_spawned_pid"], 54321)

            pit = report["pit24_benchmark"]
            self.assertEqual(pit["outcome_status"], runner.OUTCOME_LIVE_24_PASS)
            self.assertEqual(pit["selected_model"], "gpt-6-luna")
            self.assertEqual(pit["scenarios_ok"], 24)
            self.assertEqual(pit["scenarios_attempted"], 24)
            self.assertEqual(pit["json_schema_valid_rate_of_24_pct"], 100.0)
            self.assertEqual(pit["regime_agreement_rate_of_ok_pct"], 100.0)
            self.assertTrue(pit["all_prompts_anonymized_clean"])
            self.assertEqual(pit["risk_mult_distribution_ok"], {"0.0": 6, "0.5": 6, "0.75": 6, "1.0": 6})

            # Prospective shadow ledger initialized & cryptographically verified
            reloaded = sup.ProspectiveShadowLedger.load(ledger_out)
            lsum = reloaded.verify_integrity()
            self.assertTrue(lsum["verified"])
            self.assertTrue(lsum["prospective_only"])
            self.assertEqual(lsum["first_live_session_date"], "2026-11-30")
            self.assertEqual(lsum["commitments_count"], 0)
            raw_ledger = json.loads(ledger_out.read_text(encoding="utf-8"))
            self.assertEqual(raw_ledger["min_evaluation_days"], 30)

    def test_04_mocked_gateway_429_stops_immediately_with_zero_retries(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            owner_json, _, _ = _write_temp_gateway_fixture(Path(td), port=17852)
            post_calls = 0

            def _handler(req: httpx.Request) -> httpx.Response:
                nonlocal post_calls
                if req.url.path == "/v1/models":
                    return httpx.Response(200, json={"data": [{"id": "gpt-6-luna"}]})
                post_calls += 1
                if post_calls <= 2:
                    body = json.loads(req.content.decode("utf-8"))
                    content = _decision_payload_for_prompt(body["messages"][1]["content"])
                    return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})
                return httpx.Response(429, json={"error": {"message": "rate limit exceeded"}})

            client = httpx.Client(transport=httpx.MockTransport(_handler))
            try:
                pit = runner.run_pit24_over_client(
                    owner_json_path=owner_json,
                    http_client=client,
                    inter_request_delay_sec=0.0,
                )
            finally:
                client.close()

            self.assertEqual(post_calls, 3, "MUST stop immediately on 429 with 0 retries!")
            self.assertEqual(pit["outcome_status"], runner.OUTCOME_PARTIAL_RATE_LIMITED_429)
            self.assertEqual(pit["scenarios_attempted"], 3)
            self.assertEqual(pit["scenarios_ok"], 2)
            self.assertEqual(pit["scenarios_not_run"], 21)
            self.assertEqual(pit["per_scenario_results"][2]["status"], sup.STATUS_RATE_LIMITED_STOP)
            self.assertEqual(pit["per_scenario_results"][3]["attempts"], 0)

    def test_05_mocked_gateway_401_403_and_wrapped_auth_unavailable_return_skip_auth_expired(self) -> None:
        cases: list[tuple[str, int, dict[str, Any]]] = [
            ("http_401", 401, {"error": {"message": "invalid_token"}}),
            ("http_403", 403, {"error": {"message": "Verify your account to continue."}}),
            (
                "http_503_auth_unavailable",
                503,
                {"error": {"message": "auth_unavailable: no auth available (providers=antigravity)"}},
            ),
        ]
        with tempfile.TemporaryDirectory() as td:
            owner_json, _, _ = _write_temp_gateway_fixture(Path(td), port=17852)
            for label, code, payload in cases:
                with self.subTest(case=label):
                    post_calls = 0

                    def _make_handler(http_code: int, body_obj: dict[str, Any]):
                        def _h(req: httpx.Request) -> httpx.Response:
                            nonlocal post_calls
                            if req.url.path == "/v1/models":
                                return httpx.Response(200, json={"data": [{"id": "gpt-6-luna"}]})
                            post_calls += 1
                            return httpx.Response(http_code, json=body_obj)

                        return _h

                    client = httpx.Client(transport=httpx.MockTransport(_make_handler(code, payload)))
                    try:
                        pit = runner.run_pit24_over_client(
                            owner_json_path=owner_json,
                            http_client=client,
                            inter_request_delay_sec=0.0,
                        )
                    finally:
                        client.close()

                    self.assertEqual(post_calls, 1, f"{label}: expected 1 attempt with 0 retries")
                    self.assertEqual(pit["outcome_status"], runner.OUTCOME_SKIP_AUTH_EXPIRED)
                    self.assertEqual(pit["scenarios_ok"], 0)
                    self.assertEqual(pit["scenarios_attempted"], 1)
                    self.assertEqual(pit["scenarios_not_run"], 23)

    def test_06_six_criteria_benchmark_completeness_and_external_ecosystems(self) -> None:
        rubric = runner.build_enriched_6criteria_benchmark(radar_payload=_sample_radar_payload())
        self.assertEqual(rubric["architecture_count"], 5)
        self.assertEqual(rubric["criteria_count"], 6)
        self.assertEqual(tuple(rubric["criteria_keys"]), sup.RUBRIC_CRITERIA_KEYS)

        by_id = {row["architecture_id"]: row for row in rubric["architectures"]}
        self.assertEqual(
            set(by_id.keys()),
            {
                "official_api_5usd_cap",
                "neurobro_saas",
                "project_cliproxy_17852",
                "local_ollama_rtx2070s",
                "mt5_onnx_pure_mql5_v104_ml",
            },
        )
        # Official API live radar pricing in USD & VND
        off_ev = by_id["official_api_5usd_cap"]["live_evidence"]
        self.assertEqual(off_ev["eligible_models_under_5usd_count"], 302)
        self.assertEqual(off_ev["top_5_budget_models"][0]["id"], "qwen/qwen3.7-flash")
        self.assertEqual(off_ev["top_5_budget_models"][0]["monthly_vnd"], 500)
        # Neurobro honest assessment (advisory-only, unverified live PnL, rejected)
        nb_ev = by_id["neurobro_saas"]["live_evidence"]
        self.assertFalse(nb_ev["audited_live_prop_pnl_verified"])
        self.assertEqual(nb_ev["role_assessment"], "ADVISORY_ONLY_UNVERIFIED_LIVE_PNL")
        self.assertEqual(by_id["neurobro_saas"]["recommended_role"], "REJECT_BLACKBOX_SAAS")
        # Local Ollama RTX 2070 SUPER 8GB with Qwen3.5-9B fit
        loc_ev = by_id["local_ollama_rtx2070s"]["live_evidence"]
        self.assertEqual(loc_ev["gpu_name"], "NVIDIA GeForce RTX 2070 SUPER")
        self.assertEqual(loc_ev["top_full_vram_model"], "qwen/qwen3.5-9b")
        self.assertFalse(loc_ev["execution_capability"])

        # External ecosystems honest status (Alpha Arena / FinRL / Qlib)
        ecos = rubric["external_ecosystems_honest_status"]
        eco_names = " | ".join(e["ecosystem"] for e in ecos)
        self.assertIn("Alpha Arena", eco_names)
        self.assertIn("FinRL", eco_names)
        self.assertIn("Qlib", eco_names)
        for eco in ecos:
            self.assertFalse(eco["adopt_for_naqex"])
            self.assertTrue(str(eco["summary"]).strip())


class TestWave4Pit24LocalCacheArtifacts(unittest.TestCase):
    """Validates generated live .runtime/offensive4/ai artifacts under @pytest.mark.local_cache."""

    @pytest.mark.local_cache
    def test_07_validate_runtime_pit24_rubric_and_prospective_shadow_ledger(self) -> None:
        report_path = runner.DEFAULT_PIT24_RUBRIC_OUT_PATH
        ledger_path = sup.DEFAULT_PROSPECTIVE_LEDGER_PATH
        if not report_path.is_file() or not ledger_path.is_file():
            pytest.skip(f"Local runtime artifacts not present yet: {report_path}")

        report = json.loads(report_path.read_text(encoding="utf-8"))
        self.assertEqual(report["gate_id"], "W4-G14")
        self.assertEqual(report["schema_version"], runner.RUNNER_SCHEMA_VERSION)

        # 1. Hard Safety Invariants
        inv = report["hard_invariants"]
        self.assertFalse(inv["order_send_capable"])
        self.assertEqual(inv["order_send_count"], 0)
        self.assertFalse(inv["execution_capable"])
        self.assertFalse(inv["prop_guard_override_allowed"])
        self.assertEqual(inv["spend_vnd"], 0)
        self.assertEqual(inv["holdout_cutoff_date"], "2024-12-31")
        self.assertTrue(inv["holdout_2025_plus_sealed"])
        self.assertEqual(inv["holdout_rows_analysed"], 0)
        self.assertEqual(inv["max_official_api_usd_per_month"], 5.0)
        self.assertEqual(inv["forbidden_external_port"], 8317)

        # 2. Gateway Safety Verification
        gsv = report["gateway_safety_verification"]
        self.assertFalse(gsv["port_8317_touched"])
        self.assertTrue(gsv["port_8317_listeners_identical"])
        self.assertTrue(gsv["port_17852_stopped_after"])
        self.assertFalse(gsv["spawned_pid_alive_after"])
        self.assertTrue(gsv["managed_yaml_sha256_unchanged"])
        self.assertEqual(gsv["managed_yaml_sha256_before"], gsv["managed_yaml_sha256_after"])
        self.assertEqual(len(gsv["managed_yaml_sha256_before"]), 64)
        self.assertEqual(gsv["request_retry"], 0)
        self.assertFalse(gsv["poolai_present"])
        self.assertTrue(gsv["logs_redirected_to_paperclip"])

        # 3. Honest PIT-24 Results
        pit = report["pit24_benchmark"]
        self.assertIn(pit["outcome_status"], runner.VALID_PIT24_OUTCOMES)
        self.assertEqual(pit["scenarios_total"], 24)
        self.assertEqual(pit["request_retry"], 0)
        self.assertTrue(pit["all_prompts_anonymized_clean"])
        self.assertEqual(pit["clean_prompts_verified_count"], 24)
        self.assertEqual(len(pit["per_scenario_results"]), 24)
        for row in pit["per_scenario_results"]:
            self.assertFalse(row["order_send_capable"])
            self.assertFalse(row["execution_capability"])
            self.assertFalse(row["prop_guard_override_allowed"])
            self.assertEqual(len(row["prompt_sha256"]), 64)
        if pit["outcome_status"] == runner.OUTCOME_LIVE_24_PASS:
            self.assertEqual(pit["scenarios_ok"], 24)
            self.assertEqual(pit["json_schema_valid_rate_of_24_pct"], 100.0)
            self.assertGreater(pit["latency_ms_ok"]["mean_ms"], 0.0)

        # 4. Prospective Shadow Ledger SHA-256 chain & contract
        reloaded = sup.ProspectiveShadowLedger.load(ledger_path)
        lsum = reloaded.verify_integrity()
        self.assertTrue(lsum["verified"])
        self.assertTrue(lsum["prospective_only"])
        self.assertEqual(lsum["first_live_session_date"], "2026-11-30")
        raw_ledger = json.loads(ledger_path.read_text(encoding="utf-8"))
        self.assertEqual(raw_ledger["min_evaluation_days"], 30)
        self.assertFalse(raw_ledger["order_send_capable"])
        self.assertEqual(report["prospective_shadow_ledger"]["first_live_session_date"], "2026-11-30")
        self.assertTrue(report["prospective_shadow_ledger"]["verified"])

        # 5. Complete 6-Criteria x 5-Architecture Benchmark + External Ecosystems
        rubric = report["ai_architecture_benchmark_6criteria"]
        self.assertEqual(rubric["architecture_count"], 5)
        self.assertEqual(rubric["criteria_count"], 6)
        self.assertEqual(tuple(rubric["criteria_keys"]), sup.RUBRIC_CRITERIA_KEYS)
        by_id = {row["architecture_id"]: row for row in rubric["architectures"]}
        self.assertFalse(by_id["neurobro_saas"]["live_evidence"]["audited_live_prop_pnl_verified"])
        self.assertEqual(by_id["local_ollama_rtx2070s"]["live_evidence"]["top_full_vram_model"], "qwen/qwen3.5-9b")
        self.assertGreater(by_id["official_api_5usd_cap"]["live_evidence"]["eligible_models_under_5usd_count"], 100)
        eco_text = " ".join(e["ecosystem"] for e in rubric["external_ecosystems_honest_status"])
        self.assertIn("Alpha Arena", eco_text)
        self.assertIn("FinRL", eco_text)
        self.assertIn("Qlib", eco_text)


if __name__ == "__main__":
    unittest.main()
