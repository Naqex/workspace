"""Total Offensive #2 v2.5 — Read-Only 19-Gate Adversarial Siege Audit Workflow.

Executed via the Antigravity `run_workflow` tool (top-level `await` with injected
primitives: `phase`, `agent`, `parallel`, `pipeline`, `call_tool`, `log`, `args`,
and `WORKSPACES`).

Hard Invariants (Fail-Closed, python -O safe — zero bare `assert`):
  - spend_vnd = 0, OrderSend = 0, MT5_PROCS = 0 on PC Dev
  - Holdout 2025+ SEALED (holdout_rows_analysed = 0)
  - PC Dev MODE_A_OWNER_ACTIVE: never `pytest -n auto`, never root `uv run`;
    always `.runtime/quant-audit-v24/Scripts/{python,ruff,ty,pytest}.exe`
  - Zero git commits/pushes, zero file edits, zero OPSEC leaks
"""

from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from pathlib import Path

ORDER_SEND_COUNT = 0
SPEND_VND = 0
HOLDOUT_ROWS_ANALYSED = 0
ALLOWED_MODEL_TIERS = frozenset({"inherit", "flash_lite", "flash", "pro"})
SHELL_META_RE = re.compile(r"['\";`$\r\n|&<>(){}\x00]")
EXIT_OK_RE = re.compile(r"(?m)^Command exited with code 0\b")


def _require_exact_zero(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value != 0:
        raise RuntimeError(f"Invariant violation: {field_name}={value!r} must be exact integer 0 (not bool).")
    return 0


def _require_mode_a_workers(value: object) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 1 or value > 2:
        raise ValueError(f"Mode-A violation: max_workers={value!r} must be integer 1 or 2 (never bool or -n auto).")
    return value


def _require_model_tier(value: object) -> str:
    if not isinstance(value, str) or value not in ALLOWED_MODEL_TIERS:
        raise ValueError(f"Invalid model_tier={value!r}; allowed: {sorted(ALLOWED_MODEL_TIERS)}.")
    return value


def _require_safe_dir_path(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip() or SHELL_META_RE.search(value):
        raise ValueError(f"Unsafe or invalid {field_name}={value!r} (shell metacharacters rejected fail-closed).")
    return value.strip()


def _verify_verdict_against_results(verdict: dict, raw_results: list[dict]) -> None:
    _require_exact_zero(verdict.get("order_send_count"), "verdict.order_send_count")
    _require_exact_zero(verdict.get("holdout_rows_analysed"), "verdict.holdout_rows_analysed")
    passed_gates = verdict.get("passed_gates")
    if isinstance(passed_gates, bool) or not isinstance(passed_gates, int):
        raise RuntimeError(f"Verdict schema violation: passed_gates={passed_gates!r} must be int (not bool).")
    expected_passed = sum(1 for r in raw_results if r["status"] == "PASS")
    expected_failed = sorted(r["gate_id"] for r in raw_results if r["status"] != "PASS")
    expected_overall = "PASS" if (expected_passed == len(raw_results) and not expected_failed) else "FAIL"
    actual_failed = verdict.get("failed_gates")
    if not isinstance(actual_failed, list) or sorted(str(x) for x in actual_failed) != expected_failed:
        raise RuntimeError(
            f"Verdict mismatch: LLM failed_gates={actual_failed!r} != deterministic {expected_failed!r}."
        )
    if passed_gates != expected_passed:
        raise RuntimeError(f"Verdict mismatch: LLM passed_gates={passed_gates} != deterministic {expected_passed}.")
    if verdict.get("overall_status") != expected_overall:
        raise RuntimeError(
            f"Verdict mismatch: LLM overall_status={verdict.get('overall_status')!r} != {expected_overall!r}."
        )


cfg = globals().get("args")
if cfg is None:
    cfg = {}
if not isinstance(cfg, dict):
    raise ValueError("Workflow Args must be a JSON object.")

workspace_root = Path(WORKSPACES[0]).resolve() if WORKSPACES else Path.cwd().resolve()
max_workers = _require_mode_a_workers(cfg.get("max_workers", 2))
model_tier = _require_model_tier(cfg.get("model_tier", "flash"))
intel_dir = _require_safe_dir_path(cfg.get("strategy_intel_dir", "D:/ANNAM/strategy-intel"), "strategy_intel_dir")

run_x13_probe = bool(cfg.get("run_x13_probe", True))
run_gitleaks = bool(cfg.get("run_gitleaks", True))
run_submodules = bool(cfg.get("run_submodules", True))

py_exe = r".\.runtime\quant-audit-v24\Scripts\python.exe"
pytest_exe = r".\.runtime\quant-audit-v24\Scripts\pytest.exe"
gitleaks_exe = r".\.runtime\tools\gitleaks\gitleaks.exe"

GATE_RESULT_SCHEMA = {
    "type": "object",
    "properties": {
        "gate_id": {"type": "string"},
        "status": {"type": "string", "enum": ["PASS", "FAIL", "SKIPPED"]},
        "evidence": {"type": "string"},
        "remediation": {"type": "string"},
    },
    "required": ["gate_id", "status", "evidence", "remediation"],
}

VERDICT_SCHEMA = {
    "type": "object",
    "properties": {
        "overall_status": {"type": "string", "enum": ["PASS", "FAIL"]},
        "passed_gates": {"type": "integer"},
        "failed_gates": {"type": "array", "items": {"type": "string"}},
        "order_send_count": {"type": "integer"},
        "holdout_rows_analysed": {"type": "integer"},
        "summary_vi": {"type": "string"},
    },
    "required": [
        "overall_status",
        "passed_gates",
        "failed_gates",
        "order_send_count",
        "holdout_rows_analysed",
        "summary_vi",
    ],
}


def _py_cmd(code: str) -> str:
    """Wrap multi-line Python code safely for PowerShell via base64 (immune to quoting/escaping)."""
    b64 = base64.b64encode(code.strip().encode("utf-8")).decode("ascii")
    return f"{py_exe} -X utf8 -c \"import base64; exec(base64.b64decode('{b64}').decode('utf-8'))\""


def _gate_spec(
    gate_id: str,
    title: str,
    command: str,
    *,
    long_running: bool = False,
    timeout_sec: int = 300,
    enabled: bool = True,
) -> dict:
    return {
        "gate_id": gate_id,
        "title": title,
        "command": command,
        "long_running": long_running,
        "timeout_sec": timeout_sec,
        "enabled": enabled,
    }


async def _run_shell_gate(gate: dict) -> dict:
    gid = gate["gate_id"]
    if not gate["enabled"]:
        log(f"[{gid}] SKIPPED: {gate['title']}")
        return {"gate_id": gid, "title": gate["title"], "status": "SKIPPED", "output": "Disabled by workflow Args."}

    if gate["long_running"]:
        proc = await asyncio.create_subprocess_exec(
            "powershell",
            "-NoProfile",
            "-Command",
            gate["command"],
            cwd=str(workspace_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT,
        )
        try:
            raw_out, _ = await asyncio.wait_for(proc.communicate(), timeout=gate["timeout_sec"])
        except TimeoutError:
            proc.kill()
            await proc.wait()
            log(f"[{gid}] FAIL — {gate['title']} (timeout {gate['timeout_sec']}s)")
            return {
                "gate_id": gid,
                "title": gate["title"],
                "status": "FAIL",
                "output": f"Subprocess timed out after {gate['timeout_sec']}s.",
            }
        out = raw_out.decode("utf-8", errors="replace")
        status = "PASS" if proc.returncode == 0 else "FAIL"
        log(f"[{gid}] {status} (rc={proc.returncode}) — {gate['title']}")
        return {"gate_id": gid, "title": gate["title"], "status": status, "output": out[-2500:]}

    try:
        out = await call_tool(
            "run_command",
            CommandLine=gate["command"],
            WaitMsBeforeAsync=10000,
            toolSummary=f"Audit {gid} {gate['title'][:28]}",
        )
        ok = bool(EXIT_OK_RE.search(out))
        status = "PASS" if ok else "FAIL"
        log(f"[{gid}] {status} — {gate['title']}")
        return {"gate_id": gid, "title": gate["title"], "status": status, "output": out[-2500:]}
    except ToolError as exc:
        status = "SKIPPED" if getattr(exc, "denied", False) else "FAIL"
        log(f"[{gid}] {status} (ToolError: {exc.message})")
        return {"gate_id": gid, "title": gate["title"], "status": status, "output": str(exc.message)[-1500:]}


phase("Phase 1: Build 19 Mandatory Gate Specifications (Total Offensive #2 v2.5)")

# Gates G01-G05: The 5 GitHub Actions CI verification scripts (fast <10s via call_tool)
ci_gates = [
    _gate_spec("G01", "Workspace Contracts (CI 1/5)", f"{py_exe} tooling/check_workspace.py"),
    _gate_spec("G02", "GitHub Workflow Contracts (CI 2/5)", f"{py_exe} tooling/github-workflow/check.py"),
    _gate_spec(
        "G03",
        "Skill Links & Negative Triggers (CI 3/5)",
        f"{py_exe} tooling/check_skill_links.py --skills-dir .agents/skills --review-triggers",
    ),
    _gate_spec(
        "G04",
        "Strict Architecture Gate ARCH-01..10 (CI 4/5)",
        f"{py_exe} tooling/check_architecture.py --strict",
    ),
    _gate_spec(
        "G05",
        "Integrations, Education & Anti-Bloat (CI 5/5)",
        f"node tooling/integrations/doctor.mjs; if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}; "
        f"{py_exe} education/check_setup.py; if ($LASTEXITCODE -ne 0) {{ exit $LASTEXITCODE }}; "
        f"{py_exe} tooling/check_anti_bloat.py --base HEAD",
    ),
]

# Gates G06-G10: Core Factory, Immutables (+10 .ex5 SHA-256), Holdout -O Guard, quant_core 41/41, MQL5 Drift
IMMUTABLES_CODE = """
import hashlib, json, pathlib, sys

baseline_path = pathlib.Path('.tmp/offensive2_baseline_hashes.json')
if not baseline_path.is_file():
    print('IMMUTABLES_FAIL:missing_baseline_hashes_json')
    sys.exit(1)

baseline = json.loads(baseline_path.read_text(encoding='utf-8'))
bad = []
for key, spec in baseline.get('files', {}).items():
    p = pathlib.Path(spec['path'])
    if not p.is_file():
        bad.append(f'missing:{key}')
        continue
    raw = p.read_bytes()
    if len(raw) != spec.get('bytes') or hashlib.sha256(raw).hexdigest() != spec['sha256']:
        bad.append(f'sha_or_bytes_mismatch:{key}')

ex5_dir = pathlib.Path('.runtime/mt5-compiled-ex5')
ex5_files = {p.name: p for p in ex5_dir.glob('*.ex5')} if ex5_dir.is_dir() else {}
ex5_meta = baseline.get('mt5_compiled_ex5', {})
expected_ex5 = ex5_meta.get('files', [])
if len(ex5_files) != 10 or len(expected_ex5) != 10:
    bad.append(f'ex5_count={len(ex5_files)}/expected={len(expected_ex5)}')
expected_names = {entry['name'] for entry in expected_ex5}
if set(ex5_files.keys()) != expected_names:
    bad.append('ex5_name_set_mismatch')
for entry in expected_ex5:
    p = ex5_files.get(entry['name'])
    if p is None:
        bad.append(f"ex5_missing:{entry['name']}")
        continue
    raw = p.read_bytes()
    if len(raw) != entry['bytes'] or hashlib.sha256(raw).hexdigest() != entry['sha256']:
        bad.append(f"ex5_tampered:{entry['name']}")

exp_ex5 = list(pathlib.Path('tooling/ai-engines/exports').rglob('*.ex5'))
ag_bytes = pathlib.Path('AGENTS.md').stat().st_size
if len(exp_ex5) != 0:
    bad.append(f'exports_ex5={len(exp_ex5)}')
if ag_bytes != 10901:
    bad.append(f'AGENTS_bytes={ag_bytes}')

print('IMMUTABLES_OK' if not bad else 'IMMUTABLES_FAIL:' + ','.join(bad))
sys.exit(0 if not bad else 1)
"""

QUANT_CORE_41_CODE = """
import pathlib, subprocess, sys

files = sorted(str(p) for p in pathlib.Path('tooling/ai-engines/quant_core').glob('*.py'))
crlf = [f for f in files if b'\\r\\n' in pathlib.Path(f).read_bytes()]
ruff_bin = str(pathlib.Path('.runtime/quant-audit-v24/Scripts/ruff.exe'))
ty_bin = str(pathlib.Path('.runtime/quant-audit-v24/Scripts/ty.exe'))
cmds = [
    [ruff_bin, 'check', *files],
    [ruff_bin, 'format', '--check', *files],
    [ty_bin, 'check', '--extra-search-path', 'tooling/ai-engines',
     '--extra-search-path', 'projects/quant-trading/src', *files],
]
rcs = [subprocess.call(c) for c in cmds]
print(f'quant_core_count={len(files)} crlf={len(crlf)} rcs={rcs}')
sys.exit(0 if (len(files) == 41 and not crlf and all(r == 0 for r in rcs)) else 1)
"""

core_gates = [
    _gate_spec(
        "G06",
        "System Doctor Fast (10/10 & frozen_9e_tapes_v2)",
        f"{py_exe} -X utf8 tooling/ai-engines/system_doctor.py --mode fast",
        long_running=True,
        timeout_sec=120,
    ),
    _gate_spec("G07", "Immutable Hashes, AGENTS.md 10901B, WIP & 10 .ex5", _py_cmd(IMMUTABLES_CODE)),
    _gate_spec(
        "G08",
        "Holdout 2025+ Seal & python -O Fail-Closed Guards",
        f"{py_exe} -O -m pytest -o cache_dir=.tmp/pytest-wf-g08 -q "
        "tooling/ai-engines/tests/test_quant_ssot_core.py "
        "tooling/ai-engines/tests/test_lookahead_and_ledger.py",
        long_running=True,
        timeout_sec=300,
    ),
    _gate_spec(
        "G09",
        "quant_core 41/41 (ruff + format + ty + 0 CRLF)",
        _py_cmd(QUANT_CORE_41_CODE),
        long_running=True,
        timeout_sec=180,
    ),
    _gate_spec(
        "G10",
        "Active C10 MQL5 Contract Drift (0 blocking drifts)",
        f"{py_exe} -X utf8 tooling/ai-engines/quant_core/mql_contract_drift.py --check-active",
    ),
]

# Gates G11-G15: Offline Tests, Submodules, OPSEC/Gitleaks, strategy-intel 4/4, X13 Receipt
MD_HYGIENE_CODE = """
import pathlib, re, sys

targets = [
    'docs/REPO-MAP.md',
    'planning/research/README.md',
    'planning/CURRENT-CONTEXT.md',
    'tooling/workflows/README.md',
]
bad = []
for rel in targets:
    p = pathlib.Path(rel)
    if not p.is_file():
        bad.append(f'MISSING:{rel}')
        continue
    raw = p.read_bytes()
    if b'\\r\\n' in raw:
        bad.append(f'CRLF:{rel}')
    in_code = False
    for idx, ln in enumerate(raw.decode('utf-8').splitlines(), 1):
        if ln.strip().startswith('```'):
            in_code = not in_code
            continue
        if not in_code and '$' in re.sub(r'`[^`]*`', '', ln):
            bad.append(f'BARE_DOLLAR:{rel}:{idx}')

print('MD_HYGIENE_OK' if not bad else 'MD_HYGIENE_FAIL:' + ','.join(bad))
sys.exit(0 if not bad else 1)
"""

BUDGET_GATE_CODE = """
import json, pathlib, sys

errs = []
ag = pathlib.Path('AGENTS.md').stat().st_size
rm_lines = len(pathlib.Path('docs/REPO-MAP.md').read_text(encoding='utf-8').splitlines())
rr = pathlib.Path('planning/research/README.md')
rr_b = rr.stat().st_size
rr_txt = rr.read_text(encoding='utf-8')
rr_l = len(rr_txt.splitlines())
cc_b = pathlib.Path('planning/CURRENT-CONTEXT.md').stat().st_size

expected_9 = [
    'FLASHCRASH-PARETO-DEFENSE-V103-20261127.md',
    'NODE1-PRE-NFP-STAGING-AUDIT-20261127.md',
    'MULTI-FIRM-CAPITAL-OPTIMIZER-V3-20261127.md',
    'ALPHA2-UNIFIED-ENGINE-AND-PORTFOLIO-COMBINATION-20261127.md',
    'THREE-SLEEVE-TOP1-ROADMAP-AUDIT-20261127.md',
    'PROP-LIVE-TERMS-AND-BLACKFRIDAY-RADAR-20261127.md',
    'FRONTIER-UNCORRELATED-ALPHA-RADAR-20261127.md',
    'FRONTIER-AI-AGENT-AND-QUANT-TOOLING-RADAR-20261127.md',
    'STRATEGY-INTEL-CLEANROOM-PIPELINE-20261127.md',
]
if ag != 10901:
    errs.append(f'AGENTS={ag}')
if rm_lines > 100:
    errs.append(f'REPO_MAP_LINES={rm_lines}')
if rr_b >= 14500 or rr_l > 150:
    errs.append(f'RESEARCH_README={rr_b}B/{rr_l}L')
if cc_b >= 8192:
    errs.append(f'CURRENT_CONTEXT={cc_b}B')
missing = [r for r in expected_9 if r not in rr_txt]
if missing:
    errs.append('MISSING_9=' + ','.join(missing))

hc_path = pathlib.Path('.tmp/offensive2_h_contract.json')
if hc_path.is_file():
    hc = json.loads(hc_path.read_text(encoding='utf-8'))
    if len(hc.get('milestones_6', [])) != 6:
        errs.append('MILESTONES!=6')
else:
    errs.append('MISSING_H_CONTRACT')

print(f'BUDGETS AGENTS={ag}B REPO_MAP={rm_lines}L README={rr_b}B/{rr_l}L CTX={cc_b}B errs={errs}')
sys.exit(0 if not errs else 1)
"""

INTEL_4_GUARDS_CODE = f"""
import pathlib, subprocess, sys

intel_root = pathlib.Path({json.dumps(intel_dir)})
if not intel_root.is_dir():
    print(f'INTEL_DIR_MISSING:{{intel_root}}')
    sys.exit(1)

guards = [
    'scripts/common/repo_hygiene_check.py',
    'scripts/common/verify_verbatim.py',
    'scripts/common/holdout_sanitizer.py',
    'scripts/common/test_guards.py',
]
for guard in guards:
    rc = subprocess.call([sys.executable, guard], cwd=str(intel_root))
    if rc != 0:
        print(f'INTEL_GUARD_FAIL:{{guard}}:rc={{rc}}')
        sys.exit(rc)
print('INTEL_4_GUARDS_PASS')
sys.exit(0)
"""

execution_gates = [
    _gate_spec(
        "G11",
        f"Offline Unified Pytest (Mode-A -n {max_workers})",
        f'{pytest_exe} -o cache_dir=.tmp/pytest-wf-g11 -n {max_workers} --dist worksteal -m "not local_cache" -q',
        long_running=True,
        timeout_sec=600,
    ),
    _gate_spec(
        "G12",
        "Submodule & Worktree Suites (quant-trading & vi-dubber)",
        "Push-Location projects/quant-trading; try { uv run --locked ruff check src tests; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; uv run --locked pytest -n 2 -q; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE } } finally { Pop-Location }; "
        "if (Test-Path .worktrees/vi-dubber-offensive2) { Push-Location .worktrees/vi-dubber-offensive2; "
        "try { uv run --locked pytest tests/test_p13_runtime_fallbacks.py tests/test_commercial_license_guard.py -q; "
        "exit $LASTEXITCODE } finally { Pop-Location } } "
        "else { Write-Error 'MISSING_WORKTREE:.worktrees/vi-dubber-offensive2'; exit 1 }",
        long_running=True,
        timeout_sec=300,
        enabled=run_submodules,
    ),
    _gate_spec(
        "G13",
        "Layer-1 OPSEC, Zero Bare Dollar, CRLF & Gitleaks",
        f"{pytest_exe} -o cache_dir=.tmp/pytest-wf-g13 -q tooling/ai-engines/tests/test_layer1_opsec_guard.py; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        f"{_py_cmd(MD_HYGIENE_CODE)}; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        + (
            f"if (Test-Path '{gitleaks_exe}') {{ & '{gitleaks_exe}' git --redact --no-banner; "
            "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
            f"& '{gitleaks_exe}' git private_vault --redact --no-banner; exit $LASTEXITCODE }} "
            "else { Write-Error 'MISSING_BINARY:gitleaks.exe'; exit 1 }"
            if run_gitleaks
            else "Write-Output 'Gitleaks skipped by Args'"
        ),
        long_running=True,
        timeout_sec=300,
    ),
    _gate_spec(
        "G14",
        "strategy-intel 4/4 Cleanroom Guards & 1-Way Air-Gap",
        _py_cmd(INTEL_4_GUARDS_CODE),
        long_running=True,
        timeout_sec=180,
    ),
    _gate_spec(
        "G15",
        "X13 Dev-Only Probe, Strict NTP & Air-Gap Compliance",
        f"{py_exe} -X utf8 tooling/ai-engines/ops_cloud/compute_router.py probe --strict-ntp",
        long_running=True,
        timeout_sec=120,
        enabled=run_x13_probe,
    ),
]

# Gates G16-G19: Automation Platform, Front-5 Supply-Chain, Node1/Pre-Reg, Budgets & Milestones
platform_gates = [
    _gate_spec(
        "G16",
        "Self-Healing Automation, 9 CLI Subcommands & Cockpit RO",
        f"{pytest_exe} -o cache_dir=.tmp/pytest-wf-g16 -q tooling/ai-engines/tests/test_automation_platform.py; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        f"{py_exe} -X utf8 tooling/naqex_cli.py auto status --offline --json",
        long_running=True,
        timeout_sec=180,
    ),
    _gate_spec(
        "G17",
        "Front-5 External Research Supply-Chain Guards (Offline)",
        f"{pytest_exe} -o cache_dir=.tmp/pytest-wf-g17 -q "
        "tooling/ai-engines/tests/test_auto_research_radar.py "
        "tooling/ai-engines/tests/test_prop_terms_radar.py "
        "tooling/ai-engines/tests/test_strategy_intel_bridge.py",
        long_running=True,
        timeout_sec=180,
    ),
    _gate_spec(
        "G18",
        "Node1 Flat-Only Guard, Holdout v2 Pre-Reg & MT5_PROCS=0",
        f"{pytest_exe} -o cache_dir=.tmp/pytest-wf-g18 -q "
        "tooling/ai-engines/tests/test_node1_staging_guard.py "
        "tooling/ai-engines/tests/test_holdout_v2_preregistration.py; "
        "if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }; "
        "$mt5 = @(Get-Process terminal64, metatester64 -ErrorAction SilentlyContinue).Count; "
        'Write-Output "MT5_PROCS=$mt5"; if ($mt5 -ne 0) { exit 1 }',
        long_running=True,
        timeout_sec=180,
    ),
    _gate_spec("G19", "Doc Budgets, 9-Report Index & 6-Milestone Contract", _py_cmd(BUDGET_GATE_CODE)),
]

all_gates = ci_gates + core_gates + execution_gates + platform_gates
if len(all_gates) != 19:
    raise RuntimeError(f"Expected exactly 19 mandatory gates, got {len(all_gates)}.")

phase("Phase 2: Run Fast Deterministic CI & Static Gates (G01-G05 in parallel)")
r_ci = await parallel(ci_gates, _run_shell_gate)

phase("Phase 3: Run Core, Execution & Platform Gates (Mode-A sequential pipeline G06-G19)")
r_rest = await pipeline(core_gates + execution_gates + platform_gates, _run_shell_gate)

raw_results = list(r_ci) + list(r_rest)

phase("Phase 4: Adversarial Red-Team Review of Any Failed/Skipped Gates")
flagged = [r for r in raw_results if r["status"] != "PASS"]
if flagged:
    log(f"Dispatching adversarial root-cause review for {len(flagged)} non-PASS gate(s)...")
    triage_reports = await parallel(
        flagged,
        lambda item: agent(
            prompt=(
                f"Read-only adversarial audit of gate {item['gate_id']} ({item['title']}).\n"
                f"HARD RULES: Do NOT edit files, do NOT run OrderSend, do NOT access Holdout 2025+.\n"
                f"Observed status: {item['status']}\n"
                f"Tail output:\n{item['output']}\n\n"
                "Verify whether this is a true defect, missing prerequisite, or false negative, "
                "and return exact remediation in 1-2 sentences."
            ),
            schema=GATE_RESULT_SCHEMA,
            role=f"Audit {item['gate_id']}",
            workspace="inherit",
            model=model_tier,
        ),
    )
else:
    triage_reports = []
    log("All 19/19 deterministic gates PASSED cleanly; zero escalations needed.")

phase("Phase 5: Final 19-Gate Siege Verdict Synthesis (Deterministically Enforced)")
det_passed = sum(1 for r in raw_results if r["status"] == "PASS")
det_failed = sorted(r["gate_id"] for r in raw_results if r["status"] != "PASS")
det_overall = "PASS" if (det_passed == len(raw_results) and not det_failed) else "FAIL"

summary_payload = {
    "schema": "naqex-audit-19-gates-result-v1",
    "order_send_count": ORDER_SEND_COUNT,
    "spend_vnd": SPEND_VND,
    "holdout_rows_analysed": HOLDOUT_ROWS_ANALYSED,
    "mode": "MODE_A_OWNER_ACTIVE",
    "max_workers": max_workers,
    "workspace_root": os.path.basename(str(workspace_root)),
    "deterministic_totals": {
        "overall_status": det_overall,
        "passed_gates": det_passed,
        "failed_gates": det_failed,
    },
    "gates": [{k: r[k] for k in ("gate_id", "title", "status")} for r in raw_results],
    "triage": triage_reports,
}

verdict = await agent(
    prompt=(
        "Synthesize the read-only 19-gate audit summary below into a concise Vietnamese verdict.\n"
        f"HARD RULES: overall_status MUST equal {det_overall!r}, passed_gates MUST equal {det_passed}, "
        f"failed_gates MUST equal {json.dumps(det_failed)}, order_send_count=0, holdout_rows_analysed=0, "
        "zero bare currency symbols (use USD/VND), zero raw IPs/tokens/usernames.\n"
        f"Data:\n{json.dumps(summary_payload, ensure_ascii=False, indent=2)}"
    ),
    schema=VERDICT_SCHEMA,
    role="19-Gate Verdict Synthesizer",
    workspace="inherit",
    model=model_tier,
)

_verify_verdict_against_results(verdict, raw_results)

log(f"FINAL VERDICT: {verdict['overall_status']} ({verdict['passed_gates']}/19 gates passed)")
print(json.dumps({"summary": summary_payload, "verdict": verdict}, ensure_ascii=False, indent=2))
