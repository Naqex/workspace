"""100% offline-mocked unit & anti-contamination tests for Wave 4 Macro AI Supervisor (W4-G14).

Runs identically under ``python``, ``python -O``, and ``pytest -m "not local_cache"`` with
ZERO live network calls, ZERO live gateway starts, ZERO touches to port 8317, and ZERO
dependencies on gitignored ``.runtime/`` caches. Uses ``unittest.TestCase`` assertions
(zero bare ``assert`` statements) so every check stays 100% active under ``python -O``.
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
import yaml
from quant_factory.wave4 import (
    HOLDOUT_CUTOFF_DATE,
    MAX_OFFICIAL_API_USD_PER_MONTH,
    ORDER_SEND_CAPABLE,
)
from quant_factory.wave4 import macro_ai_supervisor as sup

MODULE_SOURCE_PATH = Path(sup.__file__).resolve()
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
        "leaderboards": {
            "budget_macro_supervisor_monthly_usd": [
                {
                    "rank": 1,
                    "id": "qwen/qwen3.7-flash",
                    "prompt_usd_per_1m": 0.03,
                    "completion_usd_per_1m": 0.13,
                    "monthly_usd": 0.0196,
                    "monthly_vnd": 500,
                }
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
        "catalog_index": {
            "qwen/qwen3.7-flash": {
                "prompt_usd_per_1m": 0.03,
                "completion_usd_per_1m": 0.13,
                "monthly_supervisor_usd": 0.0196,
                "context_length": 1_000_000,
            },
            "anthropic/claude-haiku-5.5": {
                "prompt_usd_per_1m": 0.10,
                "completion_usd_per_1m": 0.50,
                "monthly_supervisor_usd": 0.07,
                "context_length": 1_000_000,
            },
            "openai/o3-pro": {
                "prompt_usd_per_1m": 20.0,
                "completion_usd_per_1m": 80.0,
                "monthly_supervisor_usd": 12.60,
                "context_length": 200_000,
            },
        },
    }


def _valid_llm_decision_json(
    *,
    risk_mult: float = 0.5,
    regime_tag: str = "HIGH_STRESS_DEFENSIVE",
    confidence: float = 0.84,
) -> str:
    return json.dumps(
        {
            "risk_mult": risk_mult,
            "regime_tag": regime_tag,
            "confidence": confidence,
            "reasoning_bullets": [
                "Cross-asset realized volatility ratio > 3.5x median.",
                "Bid-ask spread expansion warrants halving new risk sizing.",
            ],
            "order_send_capable": False,
        }
    )


def _sample_v8_managed_yaml(*, port: int = 17852, request_retry: int = 2) -> str:
    return yaml.safe_dump(
        {
            "config-version": 8,
            "access": {"api-keys": ["local-loopback-test-token-001"]},
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
                        "name": "ThirdPartyProxy",
                        "base-url": "https://api.poolai.win/v1",
                        "keys": [{"api-key": "fake-third-party-token-a"}],
                        "models": [{"name": "example-model-a"}],
                    }
                ],
                "claude": [
                    {
                        "name": "ThirdPartyClaude",
                        "base-url": "https://api.poolai.win",
                        "keys": [{"api-key": "fake-third-party-token-b"}],
                        "models": [{"name": "example-model-b"}],
                    }
                ],
            },
        },
        sort_keys=False,
    )


def _sample_flat_managed_yaml(*, port: int = 17852, request_retry: int = 3) -> str:
    return yaml.safe_dump(
        {
            "host": "127.0.0.1",
            "port": port,
            "request-retry": request_retry,
            "api-keys": ["local-client-key-002", "https://api.poolai.win/bad"],
            "claude-api-key": [
                {"api-key": "fake-token-c", "base-url": "https://API.POOLAI.WIN"},
            ],
            "openai-compatibility": [
                {"name": "BlockedUpstream", "base-url": "https://api.poolai.win/v1", "api-key": "fake-token-d"},
                {"name": "SafeLocalStub", "base-url": "http://127.0.0.1:11434/v1", "api-key": "local-stub"},
            ],
        },
        sort_keys=False,
    )


def _write_temp_gateway_fixture(
    tmp_dir: Path,
    *,
    port: int = 17852,
    yaml_text: str | None = None,
) -> tuple[Path, Path, Path]:
    gw_home = tmp_dir / "gateway_home"
    gw_home.mkdir(parents=True, exist_ok=True)
    fake_exe = gw_home / "cli-proxy-api.exe"
    fake_exe.write_bytes(b"FAKE_BINARY_STUB")
    managed_yaml = gw_home / "managed.yaml"
    managed_yaml.write_text(yaml_text or _sample_v8_managed_yaml(port=port), encoding="utf-8")

    owner_json = tmp_dir / "gateway-owner.json"
    owner_json.write_text(
        json.dumps(
            {
                "port": port,
                "executable": str(fake_exe),
                "home": str(gw_home),
                "configPath": str(managed_yaml),
                "pid": 999999,
                "status": "stopped",
                "release": "v8.0.52-mock",
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return owner_json, managed_yaml, fake_exe


class TestWave4MacroAISupervisor(unittest.TestCase):
    """Comprehensive offline test suite for macro_ai_supervisor.py (W4-G14)."""

    # ------------------------------------------------------------------
    # 1. Hard Invariants, AST Subprocess creationflags & Zero Bare Asserts
    # ------------------------------------------------------------------

    def test_01_hard_invariants_ast_creationflags_and_zero_bare_asserts(self) -> None:
        self.assertFalse(ORDER_SEND_CAPABLE)
        self.assertFalse(sup.ORDER_SEND_CAPABLE)
        self.assertEqual(sup.ORDER_SEND_COUNT, 0)
        self.assertFalse(sup.EXECUTION_CAPABLE)
        self.assertFalse(sup.PROP_GUARD_OVERRIDE_ALLOWED)
        self.assertEqual(HOLDOUT_CUTOFF_DATE, "2024-12-31")
        self.assertEqual(MAX_OFFICIAL_API_USD_PER_MONTH, 5.0)
        self.assertEqual(sup.FORBIDDEN_EXTERNAL_CLIPROXY_PORT, 8317)
        self.assertEqual(sup.FIRST_PROSPECTIVE_LIVE_SESSION_DATE, "2026-11-30")

        src = MODULE_SOURCE_PATH.read_text(encoding="utf-8")
        # Must NEVER hardcode legacy gateway directory paths
        self.assertNotIn("mt5-ai-gateway", src)
        self.assertNotIn("mt5-tradingview-backtester", src)

        tree = ast.parse(src, filename=str(MODULE_SOURCE_PATH))

        # [ARCH-02] Zero bare assert statements so python -O cannot strip any invariant
        bare_asserts = [n.lineno for n in ast.walk(tree) if isinstance(n, ast.Assert)]
        self.assertEqual(bare_asserts, [], f"Found bare assert lines in macro_ai_supervisor.py: {bare_asserts}")

        # AST guard: EVERY subprocess.run/Popen/call/check_call/check_output MUST pass creationflags
        subprocess_aliases: set[str] = {"subprocess"}
        direct_spawn_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == "subprocess":
                        subprocess_aliases.add(alias.asname or "subprocess")
            elif isinstance(node, ast.ImportFrom) and node.module == "subprocess":
                for alias in node.names:
                    if alias.name in _SUBPROCESS_CALL_ATTRS:
                        direct_spawn_names.add(alias.asname or alias.name)

        calls_found = 0
        missing_cf: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            fn = node.func
            call_label: str | None = None
            if (
                isinstance(fn, ast.Attribute)
                and isinstance(fn.value, ast.Name)
                and fn.value.id in subprocess_aliases
                and fn.attr in _SUBPROCESS_CALL_ATTRS
            ):
                call_label = f"{fn.value.id}.{fn.attr}"
            elif isinstance(fn, ast.Name) and fn.id in direct_spawn_names:
                call_label = fn.id
            if call_label is not None:
                calls_found += 1
                if not any(kw.arg == "creationflags" for kw in node.keywords):
                    missing_cf.append(f"line {node.lineno}: {call_label}")

        self.assertGreaterEqual(calls_found, 2, "Expected >= 2 subprocess calls (tasklist & Popen)")
        self.assertEqual(missing_cf, [], f"Subprocess calls missing creationflags: {missing_cf}")

    # ------------------------------------------------------------------
    # 2. Port 8317 Hard-Blocked Fail-Closed Across Every Entry Point
    # ------------------------------------------------------------------

    def test_02_port_8317_hard_blocked_everywhere(self) -> None:
        with self.assertRaises(sup.SecurityError):
            sup.assert_port_allowed(8317)
        with self.assertRaises(sup.SecurityError):
            sup.assert_port_allowed(True)
        with self.assertRaises(sup.SecurityError):
            sup.assert_url_allowed("http://127.0.0.1:8317/v1/chat/completions", require_loopback=True)
        with self.assertRaises(sup.SecurityError):
            sup.assert_url_allowed("https://api.poolai.win/v1/chat/completions", require_https=True)
        with self.assertRaises(sup.SecurityError):
            sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.CLIPROXY_LOCAL_17852,
                cliproxy_expected_port=8317,
            )
        with self.assertRaises(sup.SecurityError):
            sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.LOCAL_OLLAMA_ADVISORY,
                ollama_base_url="http://127.0.0.1:8317",
            )
        with self.assertRaises(sup.SecurityError):
            sup.StandaloneGateway17852(expected_port=8317)
        with self.assertRaises(sup.SecurityError):
            sup.sanitize_gateway_yaml_text(_sample_v8_managed_yaml(port=8317))
        with self.assertRaises(sup.SecurityError):
            sup.sanitize_gateway_yaml_text(_sample_flat_managed_yaml(port=8317))

        with tempfile.TemporaryDirectory() as td:
            owner_json, _, _ = _write_temp_gateway_fixture(Path(td), port=8317)
            with self.assertRaises(sup.SecurityError):
                sup.resolve_project_gateway_owner(owner_json)

    # ------------------------------------------------------------------
    # 3. YAML Sanitizer Strips api.poolai.win & Enforces request-retry: 0
    # ------------------------------------------------------------------

    def test_03_yaml_sanitizer_v8_and_flat_strips_poolai_without_mutating_source(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            # Case A: v8 nested schema matching real managed.yaml
            src_v8 = tmp / "managed_v8.yaml"
            dst_v8 = tmp / "wave4_sanitized_v8.yaml"
            raw_v8 = _sample_v8_managed_yaml(port=17852, request_retry=3)
            src_v8.write_text(raw_v8, encoding="utf-8")
            src_sha_before = hashlib.sha256(src_v8.read_bytes()).hexdigest()

            res_v8 = sup.write_sanitized_gateway_config(src_v8, dst_v8, expected_port=17852)
            src_sha_after = hashlib.sha256(src_v8.read_bytes()).hexdigest()
            self.assertEqual(src_sha_before, src_sha_after, "managed.yaml MUST NEVER be mutated!")
            self.assertFalse(res_v8.poolai_present)
            self.assertEqual(res_v8.port, 17852)
            self.assertEqual(res_v8.request_retry, 0)
            self.assertGreaterEqual(res_v8.stripped_entries_count, 2)

            written_v8 = dst_v8.read_text(encoding="utf-8")
            self.assertNotIn("api.poolai.win", written_v8.lower())
            self.assertNotIn("poolai.win", written_v8.lower())
            parsed_v8 = yaml.safe_load(written_v8)
            self.assertEqual(parsed_v8["routing"]["retry"]["request-retry"], 0)
            self.assertEqual(parsed_v8["access"]["api-keys"], ["local-loopback-test-token-001"])
            self.assertNotIn("api-keys", parsed_v8)

            # Refuses in-place overwrite
            with self.assertRaises(sup.SecurityError):
                sup.write_sanitized_gateway_config(src_v8, src_v8)

            # Case B: legacy flat schema with uppercase API.POOLAI.WIN + mixed safe/unsafe entries
            src_flat = tmp / "managed_flat.yaml"
            dst_flat = tmp / "wave4_sanitized_flat.yaml"
            src_flat.write_text(_sample_flat_managed_yaml(port=17852, request_retry=4), encoding="utf-8")
            res_flat = sup.write_sanitized_gateway_config(src_flat, dst_flat, expected_port=17852)
            self.assertFalse(res_flat.poolai_present)
            self.assertEqual(res_flat.request_retry, 0)
            self.assertGreaterEqual(res_flat.stripped_entries_count, 3)

            written_flat = dst_flat.read_text(encoding="utf-8")
            self.assertNotIn("api.poolai.win", written_flat.lower())
            parsed_flat = yaml.safe_load(written_flat)
            self.assertEqual(parsed_flat["request-retry"], 0)
            self.assertEqual(parsed_flat["api-keys"], ["local-client-key-002"])
            self.assertNotIn("claude-api-key", parsed_flat)
            self.assertEqual(len(parsed_flat["openai-compatibility"]), 1)
            self.assertEqual(parsed_flat["openai-compatibility"][0]["name"], "SafeLocalStub")

            # Non-loopback host rejected fail-closed
            bad_host_yaml = yaml.safe_dump({"host": "0.0.0.0", "port": 17852, "request-retry": 0})
            with self.assertRaises(sup.SecurityError):
                sup.sanitize_gateway_yaml_text(bad_host_yaml)

    # ------------------------------------------------------------------
    # 4. Standalone Gateway 17852 Mocked Lifecycle & Own-PID-Only Shutdown
    # ------------------------------------------------------------------

    def test_04_standalone_gateway_mocked_lifecycle_logs_stale_pid_and_own_pid_stop(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            tmp = Path(td)
            owner_json, managed_yaml, fake_exe = _write_temp_gateway_fixture(tmp, port=17852)
            paperclip_dir = tmp / "paperclip_logs"
            paperclip_dir.mkdir()
            sanitized_path = paperclip_dir / "wave4_sanitized_gateway.yaml"
            pid_file = paperclip_dir / "wave4_gateway_17852_pid.json"
            # Seed stale dead PID file before start
            pid_file.write_text(json.dumps({"pid": 777777, "port": 17852}), encoding="utf-8")

            fake_proc = MagicMock()
            fake_proc.pid = 43210
            fake_proc.poll.return_value = None
            fake_proc.returncode = 0
            popen_calls: list[dict[str, Any]] = []

            def _fake_popen(cmd: list[str], **kwargs: Any) -> MagicMock:
                popen_calls.append({"cmd": cmd, "kwargs": kwargs})
                return fake_proc

            # First check: port not open before start; second check: port open after spawn
            port_states = iter([False, True])
            with (
                patch.object(sup, "_is_pid_alive", return_value=False),
                patch.object(sup, "_is_tcp_port_open", side_effect=lambda *_a, **_kw: next(port_states)),
                patch.object(sup.subprocess, "Popen", side_effect=_fake_popen),
            ):
                with sup.StandaloneGateway17852(
                    owner_json_path=owner_json,
                    sanitized_yaml_path=sanitized_path,
                    log_dir=paperclip_dir,
                    pid_file_path=pid_file,
                    expected_port=17852,
                    startup_timeout_sec=2.0,
                    poll_interval_sec=0.01,
                ) as gw:
                    self.assertTrue(gw.stale_cleanup_report["stale_cleaned"])
                    self.assertEqual(gw.spawned_pid, 43210)
                    self.assertEqual(len(popen_calls), 1)
                    self.assertEqual(popen_calls[0]["cmd"], [str(fake_exe), "-config", str(sanitized_path)])
                    self.assertEqual(popen_calls[0]["kwargs"]["creationflags"], sup._NO_WINDOW_FLAGS)
                    self.assertEqual(gw.stdout_log_path.parent, paperclip_dir)
                    self.assertEqual(gw.stderr_log_path.parent, paperclip_dir)
                    self.assertTrue(sanitized_path.is_file())
                    self.assertNotIn("api.poolai.win", sanitized_path.read_text(encoding="utf-8").lower())
                    self.assertTrue(pid_file.is_file())

                # On __exit__: ONLY spawned fake_proc was terminated & pid file cleaned
                fake_proc.terminate.assert_called_once()
                self.assertEqual(gw.stopped_spawned_pid, 43210)
                self.assertFalse(pid_file.exists())

            # Source managed.yaml untouched
            self.assertIn("api.poolai.win", managed_yaml.read_text(encoding="utf-8"))

            # If port 17852 is already occupied, refuse to spawn or kill external listener
            with (
                patch.object(sup, "_is_pid_alive", return_value=False),
                patch.object(sup, "_is_tcp_port_open", return_value=True),
                patch.object(sup.subprocess, "Popen") as mock_popen_occupied,
            ):
                gw_occ = sup.StandaloneGateway17852(
                    owner_json_path=owner_json,
                    sanitized_yaml_path=sanitized_path,
                    log_dir=paperclip_dir,
                    pid_file_path=pid_file,
                )
                with self.assertRaises(sup.SecurityError):
                    gw_occ.start()
                mock_popen_occupied.assert_not_called()

    # ------------------------------------------------------------------
    # 5. Official API Hard <= 5.00 USD/mo Budget Enforcer
    # ------------------------------------------------------------------

    def test_05_official_api_budget_cap_blocks_over_budget_and_allows_under_cap(self) -> None:
        scenarios = sup.build_anonymized_24_macro_scenarios()
        radar = _sample_radar_payload()
        calls: list[httpx.Request] = []

        def _handler(request: httpx.Request) -> httpx.Response:
            calls.append(request)
            if request.url.host == "api.anthropic.com":
                return httpx.Response(
                    200,
                    json={
                        "content": [{"type": "text", "text": _valid_llm_decision_json(risk_mult=0.5)}],
                        "usage": {"input_tokens": 8000, "output_tokens": 1500},
                    },
                )
            return httpx.Response(
                200,
                json={
                    "choices": [{"message": {"content": _valid_llm_decision_json(risk_mult=0.5)}}],
                    "usage": {"prompt_tokens": 8000, "completion_tokens": 1500},
                },
            )

        client = httpx.Client(transport=httpx.MockTransport(_handler))
        try:
            # 1. Expensive model ($12.60/mo > $5.00 cap) MUST be blocked BEFORE any HTTP call
            cfg_exp = sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                official_vendor="openrouter",
                model_id="openai/o3-pro",
                official_api_key="test-fake-key",
            )
            sup_exp = sup.MacroAISupervisor(cfg_exp, http_client=client, radar_payload=radar)
            with self.assertRaises(sup.BudgetExceededError):
                sup_exp.evaluate_scenario(scenarios[0])
            self.assertEqual(len(calls), 0, "Over-budget model MUST NOT send any HTTP request!")

            # 2. Attempting to configure cap > 5.00 USD fails closed
            with self.assertRaises(sup.BudgetExceededError):
                sup.MacroSupervisorConfig(
                    provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                    monthly_budget_cap_usd=5.01,
                )

            # 3. Unknown unpriced model fails closed with 0 HTTP calls
            cfg_unk = sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                model_id="vendor/unlisted-expensive-model",
                official_api_key="test-fake-key",
            )
            sup_unk = sup.MacroAISupervisor(cfg_unk, http_client=client, radar_payload=radar)
            with self.assertRaises(sup.BudgetExceededError):
                sup_unk.evaluate_scenario(scenarios[0])
            self.assertEqual(len(calls), 0)

            # 4. Cumulative MTD spend near $5.00 blocks the next call with 0 HTTP calls
            near_cap_enforcer = sup.OfficialApiBudgetEnforcer(
                monthly_cap_usd=5.0,
                radar_payload=radar,
                mtd_spend_usd=4.9999,
            )
            cfg_cheap = sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                model_id="qwen/qwen3.7-flash",
                official_api_key="test-fake-key",
            )
            sup_mtd = sup.MacroAISupervisor(
                cfg_cheap, http_client=client, budget_enforcer=near_cap_enforcer
            )
            with self.assertRaises(sup.BudgetExceededError):
                sup_mtd.evaluate_scenario(scenarios[0])
            self.assertEqual(len(calls), 0)

            # 5. Cheap radar model ($0.0196/mo <= $5.00) succeeds & records exact spend
            sup_ok = sup.MacroAISupervisor(cfg_cheap, http_client=client, radar_payload=radar)
            dec = sup_ok.evaluate_scenario(scenarios[0])
            self.assertEqual(len(calls), 1)
            self.assertEqual(dec.status, sup.STATUS_OK)
            self.assertFalse(dec.degraded)
            self.assertEqual(dec.risk_mult, 0.5)
            self.assertFalse(dec.order_send_capable)
            self.assertFalse(dec.execution_capability)
            self.assertGreater(dec.estimated_cost_usd, 0.0)
            self.assertLess(dec.estimated_cost_usd, 0.01)

            # 6. Anthropic official wire format works cleanly under cap
            cfg_anth = sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                official_vendor="anthropic",
                model_id="anthropic/claude-haiku-5.5",
                official_api_key="test-fake-key",
            )
            sup_anth = sup.MacroAISupervisor(cfg_anth, http_client=client, radar_payload=radar)
            dec_anth = sup_anth.evaluate_scenario(scenarios[1])
            self.assertEqual(dec_anth.status, sup.STATUS_OK)
            self.assertEqual(len(calls), 2)
        finally:
            client.close()

    # ------------------------------------------------------------------
    # 6. CLIProxyAPI 17852: 429 & 401/403 & Offline Degrade Cleanly (retry=0)
    # ------------------------------------------------------------------

    def test_06_cliproxy_429_401_403_and_offline_degrade_with_zero_retries(self) -> None:
        scenarios = sup.build_anonymized_24_macro_scenarios()

        # Config rejects non-zero cliproxy_request_retry fail-closed
        with self.assertRaises(sup.SupervisorValidationError):
            sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.CLIPROXY_LOCAL_17852,
                cliproxy_request_retry=1,
            )

        with tempfile.TemporaryDirectory() as td:
            owner_json, _, _ = _write_temp_gateway_fixture(Path(td), port=17852)
            cfg = sup.MacroSupervisorConfig(
                provider_mode=sup.ProviderMode.CLIPROXY_LOCAL_17852,
                model_id="claude-sonnet-4.6",
                gateway_owner_path=owner_json,
                cliproxy_expected_port=17852,
                cliproxy_request_retry=0,
            )

            cases = [
                (429, sup.STATUS_RATE_LIMITED_STOP),
                (401, sup.STATUS_SKIP_AUTH_EXPIRED),
                (403, sup.STATUS_SKIP_AUTH_EXPIRED),
                (503, sup.STATUS_DEGRADED_PARSE_OR_UPSTREAM_ERROR),
            ]
            for http_code, expected_status in cases:
                with self.subTest(http_code=http_code):
                    seen_urls: list[str] = []

                    def _make_handler(code: int, urls: list[str]):
                        def _h(req: httpx.Request) -> httpx.Response:
                            urls.append(str(req.url))
                            return httpx.Response(code, json={"error": {"message": f"mock {code}"}})

                        return _h

                    client = httpx.Client(transport=httpx.MockTransport(_make_handler(http_code, seen_urls)))
                    try:
                        engine = sup.MacroAISupervisor(cfg, http_client=client)
                        dec = engine.evaluate_scenario(scenarios[0])
                        # Strictly ZERO retries -> exactly 1 HTTP request!
                        self.assertEqual(len(seen_urls), 1)
                        self.assertEqual(seen_urls[0], "http://127.0.0.1:17852/v1/chat/completions")
                        self.assertEqual(dec.status, expected_status)
                        self.assertEqual(dec.attempts, 1)
                        self.assertTrue(dec.degraded)
                        self.assertEqual(dec.risk_mult, 1.0)
                        self.assertEqual(dec.regime_tag, "NEUTRAL")
                        self.assertEqual(dec.confidence, 0.0)
                        self.assertFalse(dec.order_send_capable)
                        self.assertFalse(dec.prop_guard_override_allowed)
                    finally:
                        client.close()

            # Network/offline error -> SKIP_OFFLINE with 1 attempt
            net_calls = 0

            def _net_err(_req: httpx.Request) -> httpx.Response:
                nonlocal net_calls
                net_calls += 1
                raise httpx.ConnectError("connection refused")

            client_off = httpx.Client(transport=httpx.MockTransport(_net_err))
            try:
                dec_off = sup.MacroAISupervisor(cfg, http_client=client_off).evaluate_scenario(scenarios[0])
                self.assertEqual(net_calls, 1)
                self.assertEqual(dec_off.status, sup.STATUS_SKIP_OFFLINE)
                self.assertTrue(dec_off.degraded)
                self.assertEqual(dec_off.risk_mult, 1.0)
            finally:
                client_off.close()

            # Happy path 200 -> parsed decision + loopback Authorization header from access.api-keys
            seen_auth: list[str | None] = []

            def _ok_handler(req: httpx.Request) -> httpx.Response:
                seen_auth.append(req.headers.get("authorization"))
                content = _valid_llm_decision_json(risk_mult=0.0, regime_tag="CRISIS_HALT")
                return httpx.Response(200, json={"choices": [{"message": {"content": content}}]})

            client_ok = httpx.Client(transport=httpx.MockTransport(_ok_handler))
            try:
                dec_ok = sup.MacroAISupervisor(cfg, http_client=client_ok).evaluate_scenario(scenarios[0])
                self.assertEqual(dec_ok.status, sup.STATUS_OK)
                self.assertFalse(dec_ok.degraded)
                self.assertEqual(dec_ok.risk_mult, 0.0)
                self.assertEqual(dec_ok.regime_tag, "CRISIS_HALT")
                self.assertEqual(seen_auth, ["Bearer local-loopback-test-token-001"])
            finally:
                client_ok.close()

    # ------------------------------------------------------------------
    # 7. Local Ollama Advisory Mode & 1-Line Provider Switch
    # ------------------------------------------------------------------

    def test_07_local_ollama_advisory_mode_and_one_line_switch(self) -> None:
        scenarios = sup.build_anonymized_24_macro_scenarios()
        seen_urls: list[str] = []

        def _ollama_handler(req: httpx.Request) -> httpx.Response:
            seen_urls.append(str(req.url))
            content = _valid_llm_decision_json(risk_mult=0.75, regime_tag="CAUTION_REDUCED")
            return httpx.Response(200, json={"message": {"role": "assistant", "content": content}})

        client = httpx.Client(transport=httpx.MockTransport(_ollama_handler))
        try:
            # 1-line switch via provider_mode=ProviderMode.LOCAL_OLLAMA_ADVISORY
            engine = sup.MacroAISupervisor(
                provider_mode=sup.ProviderMode.LOCAL_OLLAMA_ADVISORY,
                model_id="qwen3.5:9b",
                http_client=client,
            )
            dec = engine.evaluate_scenario(scenarios[6])
            self.assertEqual(seen_urls, ["http://127.0.0.1:11434/api/chat"])
            self.assertEqual(dec.status, sup.STATUS_OK)
            self.assertTrue(dec.degraded, "Local Ollama must always run in degraded advisory mode")
            self.assertFalse(dec.execution_capability)
            self.assertFalse(dec.order_send_capable)
            self.assertEqual(dec.risk_mult, 0.75)
            self.assertEqual(dec.estimated_cost_usd, 0.0)
        finally:
            client.close()

    # ------------------------------------------------------------------
    # 8. Strict Typed Decision Parser Rejects Orders / Invalid Multipliers
    # ------------------------------------------------------------------

    def test_08_decision_parser_blocks_orders_overrides_and_invalid_multipliers(self) -> None:
        prompt_sha = "a" * 64
        # Invalid risk_mult values (never allow leverage > 1.0, negative, NaN, bool)
        for bad_mult in (1.25, 2.0, -0.5, 0.33, True, False, None, "0.5"):
            with self.subTest(bad_mult=bad_mult):
                raw = json.dumps(
                    {
                        "risk_mult": bad_mult,
                        "regime_tag": "CALM_NORMAL",
                        "confidence": 0.5,
                        "reasoning_bullets": ["test"],
                        "order_send_capable": False,
                    }
                )
                with self.assertRaises(sup.SupervisorValidationError):
                    sup.parse_supervisor_decision_json(
                        raw,
                        scenario_id="SCEN_TEST",
                        provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                        model_id="test",
                        prompt_sha256=prompt_sha,
                    )

        # Rogue order/PropGuard override directives MUST fail closed
        base_ok = {
            "risk_mult": 1.0,
            "regime_tag": "CALM_NORMAL",
            "confidence": 0.9,
            "reasoning_bullets": ["x"],
        }
        rogue_payloads = [
            {**base_ok, "order_send": True},
            {**base_ok, "lot_size": 0.5},
            {**base_ok, "override_propguard": True},
            {**base_ok, "action": "BUY"},
            {**base_ok, "order_send_capable": True},
        ]
        for idx, rogue in enumerate(rogue_payloads):
            with self.subTest(rogue_idx=idx):
                with self.assertRaises(sup.SupervisorValidationError):
                    sup.parse_supervisor_decision_json(
                        json.dumps(rogue),
                        scenario_id="SCEN_ROGUE",
                        provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
                        model_id="test",
                        prompt_sha256=prompt_sha,
                    )

    # ------------------------------------------------------------------
    # 9. All 24 Anonymized Prompts Clean + Negative Mutations Fail Closed
    # ------------------------------------------------------------------

    def test_09_24_anonymized_scenarios_clean_and_negative_mutations_fail_closed(self) -> None:
        scenarios = sup.build_anonymized_24_macro_scenarios()
        self.assertEqual(len(scenarios), 24)
        self.assertEqual(len({s.scenario_id for s in scenarios}), 24)

        # Verify balanced regime coverage (6 crisis, 6 caution, 6 transitional, 6 calm)
        bands = [s.expected_regime_band for s in scenarios]
        self.assertEqual(bands.count("CRISIS_OR_DEFENSIVE"), 6)
        self.assertEqual(bands.count("ELEVATED_CAUTION"), 6)
        self.assertEqual(bands.count("TRANSITIONAL_WATCH"), 6)
        self.assertEqual(bands.count("CALM_NORMAL"), 6)

        sup.assert_anonymized_prompt_clean(sup.SYSTEM_PROMPT_MACRO_SUPERVISOR)
        for scen in scenarios:
            self.assertEqual(scen.day_marker, "DAY_T")
            self.assertIn("DAY_T", scen.prompt_text)
            sup.assert_anonymized_prompt_clean(scen.prompt_text)

        # Negative mutations MUST fail closed under both python AND python -O!
        base_clean = scenarios[0].prompt_text
        contaminated_injections = [
            "2024-08-05",
            "SVB",
            "Silicon Valley Bank",
            "COVID",
            "COVID-19",
            "Aug 5 Yen carry",
            "2018",
            "2020",
            "2025",
            "2026",
            "USDJPY",
            "FOMC",
            "Bank of Japan",
            "S&P 500",
            "Nikkei",
            "Credit Suisse",
        ]
        for token in contaminated_injections:
            with self.subTest(injected_token=token):
                mutated = f"{base_clean}\nLEAKED_NOTE: {token}"
                with self.assertRaises(sup.ContaminationError):
                    sup.assert_anonymized_prompt_clean(mutated)

        # Supervisor refuses contaminated ad-hoc prompt BEFORE any HTTP call
        called = False

        def _never_called(_req: httpx.Request) -> httpx.Response:
            nonlocal called
            called = True
            return httpx.Response(200, json={})

        client = httpx.Client(transport=httpx.MockTransport(_never_called))
        try:
            engine = sup.MacroAISupervisor(
                provider_mode=sup.ProviderMode.LOCAL_OLLAMA_ADVISORY,
                http_client=client,
            )
            with self.assertRaises(sup.ContaminationError):
                engine.evaluate_prompt("On 2024-08-05 SVB shock hit USDJPY")
            self.assertFalse(called, "Contaminated prompt MUST be blocked before any network call")
        finally:
            client.close()

    # ------------------------------------------------------------------
    # 10. Prospective Shadow Ledger SHA-256 Commit & Tamper Detection
    # ------------------------------------------------------------------

    def test_10_prospective_shadow_ledger_commit_verify_and_tamper_detection(self) -> None:
        scenarios = sup.build_anonymized_24_macro_scenarios()
        dec1 = sup.parse_supervisor_decision_json(
            _valid_llm_decision_json(risk_mult=0.5, regime_tag="HIGH_STRESS_DEFENSIVE"),
            scenario_id=scenarios[0].scenario_id,
            provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
            model_id="qwen/qwen3.7-flash",
            prompt_sha256=scenarios[0].prompt_sha256,
        )
        dec2 = sup.parse_supervisor_decision_json(
            _valid_llm_decision_json(risk_mult=1.0, regime_tag="CALM_NORMAL"),
            scenario_id=scenarios[18].scenario_id,
            provider_mode=sup.ProviderMode.OFFICIAL_API_PRODUCTION,
            model_id="qwen/qwen3.7-flash",
            prompt_sha256=scenarios[18].prompt_sha256,
        )

        with tempfile.TemporaryDirectory() as td:
            ledger_file = Path(td) / "prospective_shadow_ledger.json"
            ledger = sup.ProspectiveShadowLedger(ledger_path=ledger_file)
            self.assertEqual(ledger.first_live_session_date, "2026-11-30")
            self.assertTrue(ledger.prospective_only)

            # Reject weekend Saturday 2026-11-28 & retrospective 2024-08-05
            with self.assertRaises(sup.LedgerIntegrityError):
                ledger.commit_pre_session(
                    dec1,
                    session_date="2026-11-28",
                    session_open_utc="2026-11-28T07:00:00Z",
                    committed_utc="2026-11-28T06:00:00Z",
                )
            with self.assertRaises(sup.LedgerIntegrityError):
                ledger.commit_pre_session(
                    dec1,
                    session_date="2024-08-05",
                    session_open_utc="2024-08-05T07:00:00Z",
                    committed_utc="2024-08-05T06:00:00Z",
                )

            # Reject post-open / equal-timestamp commit (retrospective contamination!)
            with self.assertRaises(sup.LedgerIntegrityError):
                ledger.commit_pre_session(
                    dec1,
                    session_date="2026-11-30",
                    session_open_utc="2026-11-30T07:00:00Z",
                    committed_utc="2026-11-30T07:00:00Z",
                )
            with self.assertRaises(sup.LedgerIntegrityError):
                ledger.commit_pre_session(
                    dec1,
                    session_date="2026-11-30",
                    session_open_utc="2026-11-30T07:00:00Z",
                    committed_utc="2026-11-30T07:05:00Z",
                )

            # Valid pre-session commits spanning >= 30 calendar days
            c1 = ledger.commit_pre_session(
                dec1,
                session_date="2026-11-30",
                session_open_utc="2026-11-30T07:00:00Z",
                committed_utc="2026-11-30T06:30:00Z",
            )
            c2 = ledger.commit_pre_session(
                dec2,
                session_date="2026-12-30",
                session_open_utc="2026-12-30T07:00:00Z",
                committed_utc="2026-12-30T06:30:00Z",
            )
            self.assertEqual(c1.prev_sha256, sup.GENESIS_SHA256)
            self.assertEqual(c2.prev_sha256, c1.sha256)
            self.assertTrue(c1.prospective_only)
            self.assertFalse(c1.order_send_capable)

            reloaded = sup.ProspectiveShadowLedger.load(ledger_file)
            summary = reloaded.verify_integrity()
            self.assertTrue(summary["verified"])
            self.assertEqual(summary["commitments_count"], 2)
            self.assertEqual(summary["calendar_span_days"], 31)
            self.assertTrue(summary["ready_for_prospective_oos_audit"])

            # Tamper checks: mutating risk_mult, committed_utc, or sha256 MUST fail closed
            raw_ledger = json.loads(ledger_file.read_text(encoding="utf-8"))
            tamper_cases: list[tuple[str, Any]] = [
                ("tamper_risk_mult", lambda d: d["commitments"][0]["decision"].__setitem__("risk_mult", 1.0)),
                (
                    "tamper_committed_utc",
                    lambda d: d["commitments"][0].__setitem__("committed_utc", "2026-11-30T06:31:00Z"),
                ),
                ("tamper_sha256", lambda d: d["commitments"][1].__setitem__("sha256", "f" * 64)),
                ("tamper_prospective_only", lambda d: d.__setitem__("prospective_only", False)),
            ]
            for name, mutator in tamper_cases:
                with self.subTest(tamper=name):
                    copy_data = json.loads(json.dumps(raw_ledger))
                    mutator(copy_data)
                    tampered_file = Path(td) / f"{name}.json"
                    tampered_file.write_text(json.dumps(copy_data), encoding="utf-8")
                    with self.assertRaises(sup.LedgerIntegrityError):
                        sup.ProspectiveShadowLedger.load(tampered_file)

    # ------------------------------------------------------------------
    # 11. 6-Criteria x 5-Architecture Comparison Rubric Completeness
    # ------------------------------------------------------------------

    def test_11_six_criteria_architecture_rubric_completeness(self) -> None:
        rubric = sup.build_ai_architecture_rubric_6criteria(radar_payload=_sample_radar_payload())
        self.assertEqual(rubric["architecture_count"], 5)
        self.assertEqual(rubric["criteria_count"], 6)
        self.assertEqual(tuple(rubric["criteria_keys"]), sup.RUBRIC_CRITERIA_KEYS)
        self.assertFalse(rubric["hard_invariants"]["order_send_capable"])
        self.assertEqual(rubric["hard_invariants"]["max_official_api_usd_per_month"], 5.0)
        self.assertEqual(rubric["hard_invariants"]["forbidden_external_port"], 8317)

        arch_names = [row["architecture"] for row in rubric["architectures"]]
        self.assertEqual(tuple(arch_names), sup.RUBRIC_ARCHITECTURE_NAMES)

        for row in rubric["architectures"]:
            self.assertFalse(row["order_send_capable"])
            self.assertGreaterEqual(row["composite_score_5"], 1.0)
            self.assertLessEqual(row["composite_score_5"], 5.0)
            crit = row["criteria"]
            self.assertEqual(set(crit.keys()), set(sup.RUBRIC_CRITERIA_KEYS))
            for key in sup.RUBRIC_CRITERIA_KEYS:
                cell = crit[key]
                self.assertGreaterEqual(float(cell["score_1_to_5"]), 1.0)
                self.assertLessEqual(float(cell["score_1_to_5"]), 5.0)
                self.assertTrue(str(cell["rating"]).strip())
                self.assertTrue(str(cell["summary"]).strip())
            cost_cell = crit["monthly_cost_usd_vnd"]
            self.assertIn("monthly_usd_range", cost_cell)
            self.assertIn("monthly_vnd_range", cost_cell)

        # Verify radar enrichment populated Official API & Local Ollama summaries
        official_row = rubric["architectures"][0]
        self.assertIn("qwen/qwen3.7-flash", official_row["criteria"]["monthly_cost_usd_vnd"]["summary"])
        ollama_row = rubric["architectures"][3]
        self.assertIn("qwen/qwen3.5-9b", ollama_row["criteria"]["monthly_cost_usd_vnd"]["summary"])
        # Verify Neurobro rejected and MT5 ONNX ranked top for execution path
        self.assertIn("Neurobro (neurobro.ai)", rubric["recommended_hybrid_stack"]["rejected"])
        self.assertEqual(rubric["recommended_hybrid_stack"]["execution_path_filter"], "MT5 ONNX / Pure-MQL5 v1.04-ML")


if __name__ == "__main__":
    unittest.main()
