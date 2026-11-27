"""Offline security, negative-mutant, and python -O tests for the Naqex Automation Platform.

Covers:
  - Stateless read-only Cockpit Automation API (`/api/automation/{status,events,features}`)
  - `tooling/naqex_cli.py` (`CANONICAL_PYTHONPATH` includes `"."` + all 9 `auto` subcommands)
  - Antigravity scheduled sidecar templates (`naqex-poteto-healer`, `naqex-morning-chief`)
  - 10 explicit negative mutants (Circuit Breaker 4th-failure hard trip, OPSEC token/webhook/path
    scrubbing, sidecar wildcard/`enabled`/schema rejection, Cockpit `order_send_count == 0`
    & statelessness, corrupt/missing file degradation, CLI fail-closed & offline fallback,
    façade sync, and `python -O` subprocess guard enforcement)

Safety invariants:
  - ZERO bare `assert` statements (all checks use explicit `_check()`, enforced under `python -O`)
  - ZERO hardcoded user-profile paths or raw token/webhook/IP literals (100% OPSEC-clean)
  - 100% offline & deterministic (`OrderSend = 0`, `Holdout 2025+ SEALED`)
"""

from __future__ import annotations

import ast
import copy
import io
import json
import subprocess
import sys
import threading
import urllib.request
from contextlib import redirect_stdout
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[3]
AI_ENGINES = ROOT / "tooling/ai-engines"
TOOLING_DIR = ROOT / "tooling"
for _p in (str(ROOT), str(AI_ENGINES), str(TOOLING_DIR)):
    if _p not in sys.path:
        sys.path.insert(0, _p)

import naqex_cli  # noqa: E402
from cockpit import server as cockpit_server  # noqa: E402
from cockpit.modules import automation as cockpit_auto  # noqa: E402
from ops_cloud.heroku_deadman.app import _scrub_secret_text  # noqa: E402

from tooling.automation import event_queue as eq_mod  # noqa: E402
from tooling.automation import ratchet_engine as re_mod  # noqa: E402

EXPECTED_AUTO_SUBCOMMANDS: tuple[str, ...] = (
    "status",
    "watchdog",
    "nightly",
    "qa",
    "briefing",
    "heal-scan",
    "verify-features",
    "research-radar",
    "intel-sync",
)

SIDECAR_PATHS: tuple[Path, ...] = (
    ROOT / "tooling/automation/configs/sidecars/naqex-poteto-healer/sidecar.json",
    ROOT / "tooling/automation/configs/sidecars/naqex-morning-chief/sidecar.json",
)


def _check(condition: bool, message: str) -> None:
    """Explicit -O-safe assertion helper (never stripped by `python -O`)."""
    if not condition:
        raise AssertionError(message)


def _http_get_json(url: str, *, timeout: float = 10.0) -> tuple[int, dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=timeout) as resp:
        status = int(resp.status)
        body = json.loads(resp.read().decode("utf-8"))
    return status, body


def _make_synthetic_secrets() -> dict[str, str]:
    """Build synthetic OPSEC test payloads dynamically so source code never embeds raw triggers."""
    return {
        "tg_token": "123456789" + ":" + "A" + "A" + ("x" * 34),
        "gh_token": "gh" + "p_" + ("Q" * 36),
        "openai_key": "s" + "k-" + ("W" * 36),
        "discord_webhook": "https://discord.com/api/" + "webhooks/" + ("1" * 18) + "/" + ("z" * 54),
        "pg_dsn": "post" + "gres://demo_user:secret999@db.example.invalid/naqex",
        "win_user_path": "C:" + "\\Us" + "ers\\" + "sampleperson\\Desktop\\token.txt",
        "private_ip": "192.168." + "99.42",
        "heroku_url": "https://synthetic-deadman.hero" + "kuapp.com/api/status?token=REDACTED_TEST_TOKEN",
    }


def test_zero_bare_asserts_and_stateless_cockpit_automation_module() -> None:
    """Verify ZERO bare `assert` nodes in `automation.py` & this test file, and statelessness."""
    for target in (
        ROOT / "tooling/ai-engines/cockpit/modules/automation.py",
        Path(__file__).resolve(),
    ):
        tree = ast.parse(target.read_text(encoding="utf-8"), filename=str(target))
        assert_lines = [node.lineno for node in ast.walk(tree) if isinstance(node, ast.Assert)]
        _check(not assert_lines, f"Bare assert found in {target.name} at lines {assert_lines}")

    # Verify cockpit/modules/automation.py holds ZERO mutable module-level caches or locks.
    auto_src = (ROOT / "tooling/ai-engines/cockpit/modules/automation.py").read_text(encoding="utf-8")
    _check("threading.Lock" not in auto_src, "automation.py must be stateless (no threading.Lock)")
    _check("_CACHE" not in auto_src, "automation.py must be stateless (no _CACHE globals)")
    mutable_globals = [
        name
        for name, val in vars(cockpit_auto).items()
        if not name.startswith("__") and isinstance(val, (dict, list, set))
    ]
    _check(not mutable_globals, f"automation.py must have zero mutable module globals, found: {mutable_globals}")


def test_mutant_01_circuit_breaker_trips_hard_on_4th_failure(tmp_path: Path) -> None:
    """Negative Mutant 01: Circuit Breaker MUST stay closed for attempts 1..3 and trip HARD on attempt #4."""
    q_path = tmp_path / ".runtime/automation/event_queue.jsonl"
    queue = eq_mod.EventQueue(path=q_path)
    breaker = re_mod.CircuitBreaker(max_attempts=3, event_queue=queue)

    for attempt in (1, 2, 3):
        dec = breaker.record_failure("ci:quant-core", f"synthetic failure #{attempt}")
        _check(dec.tripped is False, f"Attempt {attempt} must not trip circuit prematurely")
        _check(dec.state == re_mod.STATE_CLOSED, f"Attempt {attempt} expected CLOSED, got {dec.state}")
        _check(dec.consecutive_failures == attempt, f"Expected consecutive_failures={attempt}")
        _check(dec.order_send_count == 0, "CircuitDecision order_send_count must be 0")

    # Mutant 01a: 4th consecutive failure trips HARD into CIRCUIT_OPEN_ESCALATE_OWNER.
    dec4 = breaker.record_failure("ci:quant-core", "synthetic failure #4")
    _check(dec4.tripped is True, "4th failure MUST trip circuit breaker HARD")
    _check(dec4.state == re_mod.CIRCUIT_OPEN_ESCALATE_OWNER, f"Expected CIRCUIT_OPEN_ESCALATE_OWNER, got {dec4.state}")
    _check(dec4.allowed is False, "4th failure MUST disallow further autonomous retries")
    _check(dec4.escalate_owner is True, "4th failure MUST escalate to owner")
    _check(breaker.is_open("ci:quant-core") is True, "Circuit must remain OPEN")

    # Mutant 01b: Pre-flight guard_attempt on an open circuit MUST raise CircuitOpenError.
    raised_open = False
    try:
        breaker.guard_attempt("ci:quant-core")
    except re_mod.CircuitOpenError as exc:
        raised_open = exc.state == re_mod.CIRCUIT_OPEN_ESCALATE_OWNER
    _check(raised_open, "guard_attempt MUST raise CircuitOpenError when open")

    # Mutant 01c: Autonomous record_success CANNOT clear an open circuit without owner reset.
    raised_success_blocked = False
    try:
        breaker.record_success("ci:quant-core")
    except re_mod.CircuitOpenError:
        raised_success_blocked = True
    _check(raised_success_blocked, "record_success MUST fail closed while circuit is OPEN")

    # Explicit owner reset closes the circuit cleanly.
    reset_st = breaker.reset_circuit("ci:quant-core", owner_reason="Owner audited and fixed root cause")
    _check(reset_st.state == re_mod.STATE_CLOSED, "Owner reset must return circuit to CLOSED")
    _check(reset_st.consecutive_failures == 0, "Owner reset must zero consecutive_failures")

    # Mutant 01d: Monotonic ratchet rejects order_send_count != 0 and test-count regression.
    base = re_mod.RatchetBaseline(min_tests_passed=100, max_tests_failed=0, max_ruff_errors=0)
    bad_snap = re_mod.MetricSnapshot(tests_passed=95, ruff_errors=2, order_send_count=1)
    verdict = re_mod.evaluate_ratchet(base, bad_snap)
    _check(verdict.passed is False, "Ratchet MUST reject regressions & non-zero order_send_count")
    _check(verdict.next_baseline.min_tests_passed == 100, "Failed ratchet MUST NOT weaken baseline")


def test_mutant_02_opsec_token_webhook_and_user_path_scrubbing(tmp_path: Path) -> None:
    """Negative Mutant 02: OPSEC scrubbers MUST eliminate tokens, webhooks, DSNs, private IPs, and user paths."""
    sec = _make_synthetic_secrets()

    # 2a. Verify Cockpit automation reader scrubs injected secrets across runtime JSON & JSONL files.
    auto_dir = tmp_path / ".runtime/automation"
    ops_dir = tmp_path / ".runtime/ops-cloud"
    auto_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)

    (auto_dir / "watchdog_latest.json").write_text(
        json.dumps(
            {
                "status": "WARN",
                "telegram_bot_token": sec["tg_token"],
                "alert_webhook_url": sec["discord_webhook"],
                "detail": (
                    f"failed calling {sec['heroku_url']} from {sec['private_ip']} "
                    f"with {sec['gh_token']} and {sec['openai_key']} path={sec['win_user_path']} "
                    f"dsn={sec['pg_dsn']} Bearer REDACTED_TEST_TOKEN"
                ),
            }
        ),
        encoding="utf-8",
    )
    (ops_dir / "telegram_alert_state.json").write_text(
        json.dumps(
            {
                "status": "OK",
                "chat_id": "999888777",
                "last_error": f"telegram:{sec['tg_token']} webhook:{sec['discord_webhook']}",
            }
        ),
        encoding="utf-8",
    )
    (auto_dir / "event_queue.jsonl").write_text(
        json.dumps(
            {
                "event_type": "watchdog.alert",
                "severity": "warning",
                "summary": f"token={sec['tg_token']} path={sec['win_user_path']} ip={sec['private_ip']}",
            }
        )
        + "\n",
        encoding="utf-8",
    )

    status_payload = cockpit_auto.build_automation_status_payload(tmp_path)
    events_payload = cockpit_auto.build_automation_events_payload(tmp_path)
    serialized = json.dumps({"status": status_payload, "events": events_payload}, ensure_ascii=False)

    for label, secret_val in sec.items():
        _check(secret_val not in serialized, f"OPSEC leak in Cockpit automation payload for {label}!")
    _check("999888777" not in serialized, "chat_id must be redacted in Cockpit automation payload")
    _check(status_payload["order_send_count"] == 0, "order_send_count must stay 0")

    # 2b. Verify heroku_deadman._scrub_secret_text and event_queue.scrub_text also scrub synthetic leaks.
    raw_blob = " ".join(
        [sec["tg_token"], sec["discord_webhook"], sec["gh_token"], sec["win_user_path"], sec["private_ip"]]
    )
    scrubbed_deadman = _scrub_secret_text(raw_blob, secrets=(sec["tg_token"], sec["discord_webhook"]))
    _check(sec["tg_token"] not in scrubbed_deadman, "_scrub_secret_text leaked tg_token")
    _check(sec["discord_webhook"] not in scrubbed_deadman, "_scrub_secret_text leaked discord_webhook")

    scrubbed_eq = eq_mod.scrub_text(raw_blob)
    for label in ("tg_token", "discord_webhook", "gh_token", "win_user_path", "private_ip"):
        _check(sec[label] not in scrubbed_eq, f"event_queue.scrub_text leaked {label}")


def test_mutant_03_sidecar_templates_valid_and_reject_wildcards() -> None:
    """Negative Mutant 03: Both sidecar templates pass schema validation, and ALL wildcard grants are rejected."""
    loaded: list[dict[str, Any]] = []
    for path in SIDECAR_PATHS:
        _check(path.is_file(), f"Missing sidecar template: {path}")
        raw_bytes = path.read_bytes()
        _check(b"\r\n" not in raw_bytes, f"CRLF detected in {path.name}; must be LF-only")
        cfg = json.loads(raw_bytes.decode("utf-8"))
        ok, errs = cockpit_auto.validate_sidecar_config(cfg, source_name=path.parent.name)
        _check(ok, f"Real sidecar template {path.parent.name} failed validation: {errs}")
        _check("CRON_TZ=Asia/Ho_Chi_Minh " in cfg["args"][0], f"Missing Asia/Ho_Chi_Minh TZ in {path.parent.name}")
        _check("enabled" not in cfg, f"Forbidden 'enabled' key in {path.parent.name}")
        _check(cfg["restart_policy"] == "always", f"restart_policy must be 'always' in {path.parent.name}")
        loaded.append(cfg)

    # Confirm exact morning-chief cron schedule.
    morning_cfg = json.loads(SIDECAR_PATHS[1].read_text(encoding="utf-8"))
    _check(
        morning_cfg["args"][0] == "CRON_TZ=Asia/Ho_Chi_Minh 30 7 * * *",
        f"Unexpected morning-chief cron: {morning_cfg['args'][0]}",
    )

    # Mutant 03: Every wildcard / overbroad permission grant MUST be rejected.
    forbidden_grants = (
        "command(*)",
        "read_file(*)",
        "read_file(/)",
        "write_file(*)",
        "write_file(/)",
        "mcp(*)",
        "read_url(*)",
        "execute_url(*)",
        "allow(*)",
    )
    for bad_grant in forbidden_grants:
        mut = copy.deepcopy(loaded[0])
        mut["agent_permissions"]["access_grants"].append(bad_grant)
        ok, errs = cockpit_auto.validate_sidecar_config(mut, source_name="mutant-wildcard")
        _check(ok is False, f"Sidecar validator MUST reject wildcard grant {bad_grant!r}")
        _check(bool(errs), f"Expected non-empty error list for {bad_grant!r}")


def test_mutant_04_sidecar_rejects_enabled_key() -> None:
    """Negative Mutant 04: Sidecar validator MUST reject any `'enabled'` key (true, false, or nested)."""
    base = json.loads(SIDECAR_PATHS[0].read_text(encoding="utf-8"))
    for enabled_val in (True, False):
        mut = copy.deepcopy(base)
        mut["enabled"] = enabled_val
        ok, errs = cockpit_auto.validate_sidecar_config(mut, source_name="mutant-enabled")
        _check(ok is False, f"Sidecar validator MUST reject top-level enabled={enabled_val!r}")
        _check(any("enabled" in e.lower() for e in errs), f"Expected 'enabled' diagnostic, got {errs}")

    mut_nested = copy.deepcopy(base)
    mut_nested["agent_permissions"]["enabled"] = True
    ok_nested, _ = cockpit_auto.validate_sidecar_config(mut_nested, source_name="mutant-nested-enabled")
    _check(ok_nested is False, "Sidecar validator MUST reject nested agent_permissions.enabled")


def test_mutant_05_sidecar_rejects_bad_policy_cron_separator_and_user_paths() -> None:
    """Negative Mutant 05: Reject bad restart_policy, missing CRON_TZ or '--', relative scripts, and user paths."""
    base = json.loads(SIDECAR_PATHS[0].read_text(encoding="utf-8"))
    sec = _make_synthetic_secrets()

    for bad_policy in ("SIDECAR_RESTART_POLICY_ALWAYS", "unless-stopped", "on-failure", "never", "ALWAYS"):
        mut = copy.deepcopy(base)
        mut["restart_policy"] = bad_policy
        ok, _ = cockpit_auto.validate_sidecar_config(mut)
        _check(ok is False, f"Sidecar validator MUST reject restart_policy={bad_policy!r}")

    mut_no_tz = copy.deepcopy(base)
    mut_no_tz["args"][0] = "*/30 * * * *"
    ok_tz, _ = cockpit_auto.validate_sidecar_config(mut_no_tz)
    _check(ok_tz is False, "Sidecar validator MUST reject cron without CRON_TZ=<IANA> prefix")

    mut_no_sep = copy.deepcopy(base)
    mut_no_sep["args"] = [a for a in mut_no_sep["args"] if a != "--"]
    ok_sep, _ = cockpit_auto.validate_sidecar_config(mut_no_sep)
    _check(ok_sep is False, "Sidecar validator MUST reject args missing '--' separator")

    mut_rel_script = copy.deepcopy(base)
    mut_rel_script["args"] = [
        "CRON_TZ=Asia/Ho_Chi_Minh */30 * * * *",
        "python.exe",
        "watchdog_15m.py",
        "--",
        "Run watchdog.",
    ]
    ok_rel, _ = cockpit_auto.validate_sidecar_config(mut_rel_script)
    _check(ok_rel is False, "Sidecar validator MUST reject relative script paths in args")

    mut_camel = copy.deepcopy(base)
    mut_camel["restartPolicy"] = "always"
    ok_camel, _ = cockpit_auto.validate_sidecar_config(mut_camel)
    _check(ok_camel is False, "Sidecar validator MUST reject camelCase keys")

    mut_user_path = copy.deepcopy(base)
    mut_user_path["agent_permissions"]["access_grants"].append(f"read_file({sec['win_user_path']})")
    ok_user, _ = cockpit_auto.validate_sidecar_config(mut_user_path)
    _check(ok_user is False, "Sidecar validator MUST reject hardcoded local user home paths")


def test_mutant_06_cockpit_automation_order_send_zero_and_http_routes(tmp_path: Path) -> None:
    """Negative Mutant 06: All 3 Cockpit HTTP routes return 200 with order_send_count==0 even under hostile JSON."""
    auto_dir = tmp_path / ".runtime/automation"
    ops_dir = tmp_path / ".runtime/ops-cloud"
    cfg_dir = tmp_path / "tooling/automation/configs"
    auto_dir.mkdir(parents=True, exist_ok=True)
    ops_dir.mkdir(parents=True, exist_ok=True)
    cfg_dir.mkdir(parents=True, exist_ok=True)

    # Hostile runtime JSON attempts to inject non-zero order_send_count; top-level MUST remain 0!
    (auto_dir / "watchdog_latest.json").write_text(
        json.dumps({"status": "OK", "order_send_count": 7, "disk_free_gb": 120.5}),
        encoding="utf-8",
    )
    (auto_dir / "product_qa_latest.json").write_text(
        json.dumps({"status": "OK", "results": [{"feature_id": "cockpit_api", "passed": True}]}),
        encoding="utf-8",
    )
    (ops_dir / "node1_watchdog_state.json").write_text(
        json.dumps({"status": "OK", "ntp_offset_ms": 14.2}),
        encoding="utf-8",
    )
    (cfg_dir / "feature_map.json").write_text(
        json.dumps({"schema_version": "v1", "features": [{"id": "cockpit_api", "name": "Cockpit API"}]}),
        encoding="utf-8",
    )
    (auto_dir / "event_queue.jsonl").write_text(
        "\n".join(
            [
                json.dumps({"event_type": "ci.scan", "severity": "info", "summary": "ok"}),
                json.dumps({"event_type": "watchdog.alert", "severity": "warning", "summary": "ntp check"}),
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        st1, p_status = _http_get_json(f"{base}/api/automation/status")
        _check(st1 == 200, f"Expected 200 for /api/automation/status, got {st1}")
        _check(p_status["order_send_count"] == 0, "Top-level order_send_count MUST remain 0")
        _check(p_status["stateless"] is True, "status payload must declare stateless=True")
        _check(p_status["read_only"] is True, "status payload must declare read_only=True")
        _check(p_status["overall_status"] == "ACTIVE", f"Expected ACTIVE, got {p_status['overall_status']}")
        _check(p_status["automation"]["watchdog_latest"]["available"] is True, "watchdog_latest should be available")
        _check(p_status["ops_cloud"]["node1_watchdog_state"]["available"] is True, "node1 state should be available")
        _check(p_status["feature_map"]["feature_count"] == 1, "Expected 1 feature in feature_map summary")

        st2, p_events = _http_get_json(f"{base}/api/automation/events?limit=5&severity=warning")
        _check(st2 == 200, f"Expected 200 for /api/automation/events, got {st2}")
        _check(p_events["order_send_count"] == 0, "events order_send_count MUST be 0")
        _check(p_events["returned_count"] == 1, f"Expected 1 warning event, got {p_events['returned_count']}")
        _check(p_events["events"][0]["event_type"] == "watchdog.alert", "Unexpected filtered event")

        st3, p_feats = _http_get_json(f"{base}/api/automation/features")
        _check(st3 == 200, f"Expected 200 for /api/automation/features, got {st3}")
        _check(p_feats["order_send_count"] == 0, "features order_send_count MUST be 0")
        _check(p_feats["feature_count"] == 1, "Expected 1 feature")
        _check(
            p_feats["features"][0].get("latest_qa", {}).get("passed") is True,
            "features endpoint must overlay product_qa_latest results",
        )
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


def test_mutant_07_cockpit_graceful_degradation_missing_and_corrupt_files(tmp_path: Path) -> None:
    """Negative Mutant 07: Missing or corrupt runtime JSON/JSONL files MUST return HTTP 200 cleanly (zero 500s)."""
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    base = f"http://127.0.0.1:{port}"
    try:
        # 7a. Completely empty workspace root -> clean pending payloads.
        for ep in ("/api/automation/status", "/api/automation/events", "/api/automation/features"):
            code, data = _http_get_json(f"{base}{ep}")
            _check(code == 200, f"Empty root {ep} must return 200, got {code}")
            _check(data["order_send_count"] == 0, f"Empty root {ep} order_send_count must be 0")
            _check(data["stateless"] is True, f"Empty root {ep} must be stateless")

        _, empty_st = _http_get_json(f"{base}/api/automation/status")
        _check(empty_st["overall_status"] == "PENDING", f"Expected PENDING, got {empty_st['overall_status']}")

        # 7b. Drop truncated / malformed JSON and mixed corrupt JSONL lines -> still HTTP 200!
        auto_dir = tmp_path / ".runtime/automation"
        cfg_dir = tmp_path / "tooling/automation/configs"
        auto_dir.mkdir(parents=True, exist_ok=True)
        cfg_dir.mkdir(parents=True, exist_ok=True)
        (auto_dir / "watchdog_latest.json").write_text("{corrupt json...", encoding="utf-8")
        (cfg_dir / "feature_map.json").write_text("[broken", encoding="utf-8")
        (auto_dir / "event_queue.jsonl").write_text(
            "not-json-line\n" + json.dumps({"event_type": "ok.ev", "severity": "info"}) + "\n{bad\n",
            encoding="utf-8",
        )

        c1, st_bad = _http_get_json(f"{base}/api/automation/status")
        c2, ev_bad = _http_get_json(f"{base}/api/automation/events")
        c3, ft_bad = _http_get_json(f"{base}/api/automation/features")
        _check((c1, c2, c3) == (200, 200, 200), "Corrupt files must degrade to HTTP 200 without 500")
        _check(st_bad["automation"]["watchdog_latest"]["status"] == "malformed", "Expected malformed status")
        _check(ev_bad["returned_count"] == 1, "Valid JSONL line must survive corrupt sibling lines")
        _check(ft_bad["status"] == "malformed" and ft_bad["features"] == [], "Corrupt feature_map must degrade cleanly")
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)


def test_mutant_08_cli_rejects_unknown_and_fails_closed_when_missing_without_offline(tmp_path: Path) -> None:
    """Negative Mutant 08: CLI rejects unknown auto subcommands & fails closed (rc=2) when missing without --offline."""
    py = naqex_cli.resolve_python(ROOT)
    proc_unknown = subprocess.run(
        [py, "-X", "utf8", str(ROOT / "tooling/naqex_cli.py"), "auto", "does-not-exist"],
        cwd=str(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    _check(proc_unknown.returncode != 0, "Unknown auto subcommand MUST exit non-zero")

    # Without --offline or --dry-run, a missing automation script on empty root MUST fail closed (exit 2).
    rc_missing = naqex_cli.main(["--root", str(tmp_path), "auto", "watchdog"])
    _check(rc_missing == 2, f"Missing script without --offline/--dry-run must exit 2, got {rc_missing}")

    # With --offline, missing script degrades cleanly and exits 0.
    buf = io.StringIO()
    with redirect_stdout(buf):
        rc_offline = naqex_cli.main(["--root", str(tmp_path), "auto", "watchdog", "--offline", "--json"])
    _check(rc_offline == 0, f"Missing script with --offline must exit 0, got {rc_offline}")
    parsed = json.loads(buf.getvalue())
    _check(parsed["order_send_count"] == 0, "Offline fallback JSON must report order_send_count=0")
    _check(parsed["status"] == "offline_fallback", f"Unexpected fallback status: {parsed}")


def test_mutant_09_cli_all_9_subcommands_help_offline_dryrun_json_and_pythonpath(tmp_path: Path) -> None:
    """Negative Mutant 09: Verify '.' in CANONICAL_PYTHONPATH + all 9 exact contract auto subcommands."""
    # Check exact contract match when .tmp/offensive2_h_contract.json is present.
    contract_path = ROOT / ".tmp/offensive2_h_contract.json"
    if contract_path.is_file():
        contract = json.loads(contract_path.read_text(encoding="utf-8"))
        contract_cmds = tuple(contract["naqex_cli_auto_subcommands"])
        _check(
            contract_cmds == EXPECTED_AUTO_SUBCOMMANDS,
            f"Contract mismatch: {contract_cmds} != {EXPECTED_AUTO_SUBCOMMANDS}",
        )
    _check(
        naqex_cli.AUTO_SUBCOMMANDS == EXPECTED_AUTO_SUBCOMMANDS,
        f"naqex_cli.AUTO_SUBCOMMANDS mismatch: {naqex_cli.AUTO_SUBCOMMANDS}",
    )

    # Verify "." is in CANONICAL_PYTHONPATH and allows `import tooling.automation` from an unrelated CWD!
    _check("." in naqex_cli.CANONICAL_PYTHONPATH, "'.' MUST be in naqex_cli.CANONICAL_PYTHONPATH")
    env = naqex_cli.build_env(ROOT)
    py = naqex_cli.resolve_python(ROOT)
    imp_proc = subprocess.run(
        [
            py,
            "-X",
            "utf8",
            "-c",
            "import tooling.automation.ratchet_engine as r; print(r.ORDER_SEND_COUNT)",
        ],
        cwd=str(tmp_path),
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    _check(imp_proc.returncode == 0, f"Import from foreign CWD failed: {imp_proc.stderr}")
    _check(imp_proc.stdout.strip() == "0", f"Unexpected ORDER_SEND_COUNT output: {imp_proc.stdout!r}")

    parser = naqex_cli.make_parser()
    for subcmd in EXPECTED_AUTO_SUBCOMMANDS:
        # 9a. `build_command` forwards --offline, --dry-run, --json cleanly.
        ns, extra = parser.parse_known_args(["auto", subcmd, "--offline", "--dry-run", "--json"])
        cmd = naqex_cli.build_command(ns, extra, root=tmp_path)
        _check("--offline" in cmd, f"--offline not forwarded for {subcmd}: {cmd}")
        _check("--dry-run" in cmd, f"--dry-run not forwarded for {subcmd}: {cmd}")
        _check("--json" in cmd, f"--json not forwarded for {subcmd}: {cmd}")

        # 9b. `--help` works cleanly and exits 0 for every one of the 9 subcommands.
        help_proc = subprocess.run(
            [py, "-X", "utf8", str(ROOT / "tooling/naqex_cli.py"), "auto", subcmd, "--help"],
            cwd=str(tmp_path),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        _check(help_proc.returncode == 0, f"`auto {subcmd} --help` failed: {help_proc.stderr}")

        # 9c. `--offline --dry-run --json` exits 0 cleanly on isolated root with valid JSON & OrderSend=0.
        run_proc = subprocess.run(
            [
                py,
                "-X",
                "utf8",
                str(ROOT / "tooling/naqex_cli.py"),
                "--root",
                str(tmp_path),
                "auto",
                subcmd,
                "--offline",
                "--dry-run",
                "--json",
            ],
            cwd=str(tmp_path),
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        _check(
            run_proc.returncode == 0,
            f"`auto {subcmd} --offline --dry-run --json` exited {run_proc.returncode}: {run_proc.stderr}",
        )
        out_json = json.loads(run_proc.stdout)
        _check(out_json.get("order_send_count") == 0, f"{subcmd} JSON must report order_send_count == 0")


def test_mutant_10_facade_sync_and_subprocess_python_dash_O_enforcement(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Negative Mutant 10: Cockpit façade syncs automation routes + `python -O` subprocess enforces guards."""
    # 10a. Verify monkeypatching cockpit.server.build_automation_status_payload propagates to HTTP routes.
    monkeypatch.setattr(
        cockpit_server,
        "build_automation_status_payload",
        lambda *_a, **_kw: {"stub_auto": True, "order_send_count": 0, "stateless": True},
    )
    srv = cockpit_server.create_server(host="127.0.0.1", port=0, root=tmp_path)
    port = srv.server_address[1]
    th = threading.Thread(target=srv.serve_forever, daemon=True)
    th.start()
    try:
        code, body = _http_get_json(f"http://127.0.0.1:{port}/api/automation/status")
        _check(code == 200, f"Expected 200 on facade-patched route, got {code}")
        _check(body == {"stub_auto": True, "order_send_count": 0, "stateless": True}, f"Facade split-brain: {body}")
    finally:
        srv.shutdown()
        srv.server_close()
        th.join(timeout=5)

    # 10b. Execute real `python -O` subprocess confirming security guards stay active when __debug__ is False!
    py = naqex_cli.resolve_python(ROOT)
    dash_o_script = "\n".join(
        [
            "import json, pathlib",
            "from cockpit.modules import automation as ca",
            "from tooling.automation import event_queue as eq, ratchet_engine as re_mod",
            "if __debug__:",
            "    raise SystemExit('EXPECTED_DASH_O_MODE')",
            f"root = pathlib.Path({str(ROOT)!r})",
            "st = ca.build_automation_status_payload(root)",
            "if st['order_send_count'] != 0 or st['stateless'] is not True:",
            "    raise SystemExit('BAD_COCKPIT_AUTOMATION_STATE')",
            "base_sc = {",
            "    'builtin': 'schedule',",
            "    'restart_policy': 'always',",
            "    'display_name': 'x',",
            "    'description': 'y',",
            "    'args': ['CRON_TZ=Asia/Ho_Chi_Minh 0 7 * * *', 'agentapi', 'new-conversation', '--', 'p'],",
            "}",
            "ok_bad, _ = ca.validate_sidecar_config({**base_sc, 'enabled': True})",
            "if ok_bad:",
            "    raise SystemExit('SIDECAR_ENABLED_NOT_REJECTED_IN_DASH_O')",
            "ok_wild, _ = ca.validate_sidecar_config(",
            "    {**base_sc, 'agent_permissions': {'access_grants': ['command(*)']}}",
            ")",
            "if ok_wild:",
            "    raise SystemExit('SIDECAR_WILDCARD_NOT_REJECTED_IN_DASH_O')",
            "cb = re_mod.CircuitBreaker(max_attempts=3)",
            "for i in range(1, 4):",
            "    d = cb.record_failure('dash-o-target', f'err-{i}')",
            "    if d.tripped:",
            "        raise SystemExit('TRIPPED_TOO_EARLY')",
            "d4 = cb.record_failure('dash-o-target', 'err-4')",
            "if not d4.tripped or d4.state != re_mod.CIRCUIT_OPEN_ESCALATE_OWNER:",
            "    raise SystemExit('CIRCUIT_DID_NOT_TRIP_ON_4TH_IN_DASH_O')",
            "try:",
            "    eq.AutomationEvent(event_type='bad', source='test', order_send_count=1)",
            "    raise SystemExit('ORDER_SEND_NONZERO_ALLOWED_IN_DASH_O')",
            "except ValueError:",
            "    pass",
            "print(json.dumps({'dash_o_ok': True, 'order_send_count': st['order_send_count']}))",
        ]
    )
    proc = subprocess.run(
        [py, "-O", "-X", "utf8", "-c", dash_o_script],
        cwd=str(ROOT),
        env=naqex_cli.build_env(ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    _check(
        proc.returncode == 0,
        f"python -O subprocess guard failed (rc={proc.returncode}): {proc.stderr} {proc.stdout}",
    )
    res = json.loads(proc.stdout.strip())
    _check(res.get("dash_o_ok") is True and res.get("order_send_count") == 0, f"Unexpected -O output: {res}")
