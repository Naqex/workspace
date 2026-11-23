"""Naqex Quant Factory System Doctor: single-command health, regression, anti-bloat, Holdout-lock & AI-env auditor.

Usage:
  python -X utf8 tooling/ai-engines/system_doctor.py --mode fast
  python -X utf8 tooling/ai-engines/system_doctor.py --mode full --json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
AI_ENGINES = ROOT / "tooling/ai-engines"
FOUNDATION_SRC = ROOT / "projects/trader/foundation_v2/src"
sys.path.insert(0, str(AI_ENGINES))
if FOUNDATION_SRC.exists():
    sys.path.insert(0, str(FOUNDATION_SRC))

AI_ENV_AUDIT_PS1 = Path(r"C:\Users\MIIKEY\.gemini\config\plugins\migrated-settings\skills\ai-environment-maintainer\scripts\audit-ai-environment.ps1")


def _subproc_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [str(AI_ENGINES), str(FOUNDATION_SRC)] + ([existing] if existing else [])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    return env


def _run(cmd: list[str], *, cwd: Path = ROOT, timeout: int = 180) -> tuple[int, str, float]:
    t0 = time.perf_counter()
    p = subprocess.run(cmd, cwd=str(cwd), env=_subproc_env(), capture_output=True, text=True, timeout=timeout)
    out = (p.stdout or "") + ("\n" + p.stderr if p.stderr else "")
    return p.returncode, out.strip(), round(time.perf_counter() - t0, 2)


def check_holdout_lock() -> dict:
    t0 = time.perf_counter()
    import pass5_usdjpy_tokyo as clock
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    reg_path = ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
    errors = []
    if not lock_path.exists():
        errors.append("Missing NATIVE_FTMO_HOLDOUT_LOCK.json")
    else:
        digest = hashlib.sha256(lock_path.read_bytes()).hexdigest()
        if digest != clock.LOCK_SHA:
            errors.append(f"Holdout Lock SHA mismatch: expected={clock.LOCK_SHA[:12]} got={digest[:12]}")
    if not reg_path.exists():
        errors.append("Missing PORTFOLIO-REGISTRY.json")
    else:
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        hl = reg.get("holdout_lock", {})
        if hl.get("holdout_rows_analysed", -1) != 0:
            errors.append(f"holdout_rows_analysed={hl.get('holdout_rows_analysed')} != 0")
        if hl.get("order_send_count", -1) != 0:
            errors.append(f"order_send_count={hl.get('order_send_count')} != 0")
    return {
        "name": "holdout_lock",
        "ok": not errors,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": "Holdout 2025+ SEALED (rows=0, OrderSend=0)" if not errors else "; ".join(errors),
    }


def check_index_bloat() -> dict:
    t0 = time.perf_counter()
    errors = []
    readme = ROOT / "planning/research/README.md"
    ctx = ROOT / "planning/CURRENT-CONTEXT.md"
    readme_lines = len(readme.read_text(encoding="utf-8").splitlines()) if readme.exists() else -1
    ctx_bytes = ctx.stat().st_size if ctx.exists() else -1
    if readme_lines > 150:
        errors.append(f"planning/research/README.md too long ({readme_lines} > 150 lines)")
    if ctx_bytes > 12_000:
        errors.append(f"planning/CURRENT-CONTEXT.md too large ({ctx_bytes} > 12000 B)")
    oversized = []
    # Check all branch-touched or untracked files in planning/research/ (< 900 KB prevents hitting 1 MiB anti-bloat wall)
    rc_d, diff_out, _ = _run(["git", "diff", "--name-only", "origin/main"])
    rc_u, untr_out, _ = _run(["git", "ls-files", "--others", "--exclude-standard", "planning/research"])
    candidates = set()
    if rc_d == 0:
        candidates.update(line.strip() for line in diff_out.splitlines() if line.strip().startswith("planning/research/"))
    if rc_u == 0:
        candidates.update(line.strip() for line in untr_out.splitlines() if line.strip())
    for rel in sorted(candidates):
        p = ROOT / rel
        if p.is_file() and p.stat().st_size > 900_000:
            oversized.append(f"{p.name} ({p.stat().st_size // 1024} KB)")
    if oversized:
        errors.append(f"Branch files > 900 KB in planning/research/: {', '.join(oversized)}")
    return {
        "name": "index_bloat",
        "ok": not errors,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": f"README={readme_lines}L, CURRENT-CONTEXT={ctx_bytes}B, 0 branch files > 900KB" if not errors else "; ".join(errors),
    }


def check_exports_static_audit() -> dict:
    t0 = time.perf_counter()
    import mq5_whitebox_exporter as exp
    exp_dir = AI_ENGINES / "exports"
    files = sorted(list(exp_dir.glob("*.mq5")) + list((exp_dir / "Include").glob("*.mqh")))
    errors = []
    for f in files:
        src = f.read_text(encoding="utf-8")
        res = exp.audit_open_source_mq5(src, filename=f.name)
        if res["red_flags"]:
            errors.append(f"{f.name}: red_flags={res['red_flags']}")
        if f.suffix == ".mq5" and "InpDryRunLogOnly" not in src:
            errors.append(f"{f.name}: missing InpDryRunLogOnly")
    return {
        "name": "exports_static_audit",
        "ok": not errors and len(files) >= 9,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": f"{len(files)} MQL5 files audited: 0 red flags, DryRun default ON" if not errors else "; ".join(errors),
    }


def check_derived_cache() -> dict:
    t0 = time.perf_counter()
    from quant_factory.data_store import DERIVED_CACHE_DIR, REGISTRY_PATH, _load_tapes_safe_npz, assert_holdout_locked
    from native_ftmo_monfri_seal import sha
    lock_sha = assert_holdout_locked()
    reg_sha = sha(REGISTRY_PATH) if REGISTRY_PATH.exists() else "NO_REG"
    binding = hashlib.sha256(f"{lock_sha}|{reg_sha}|v1".encode()).hexdigest()
    meta_path = DERIVED_CACHE_DIR / "frozen_9e_tapes_v1.json"
    npz_path = DERIVED_CACHE_DIR / "frozen_9e_tapes_v1.npz"
    if not (meta_path.exists() and npz_path.exists()):
        return {
            "name": "derived_cache",
            "ok": True,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": "COLD (not yet warmed; run quant_factory.build_or_load_frozen_tapes() once)",
        }
    hit = _load_tapes_safe_npz(DERIVED_CACHE_DIR, "frozen_9e_tapes_v1", binding)
    ok = hit is not None
    sz_mb = round((npz_path.stat().st_size + meta_path.stat().st_size) / (1024 * 1024), 2)
    return {
        "name": "derived_cache",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": f"WARM HIT ({sz_mb} MB, 9 engines, sha-verified)" if ok else "STALE/INVALID binding SHA",
    }


def check_workspace_contracts() -> dict:
    rc, out, sec = _run([sys.executable, str(ROOT / "tooling/check_workspace.py")])
    return {"name": "workspace_contracts", "ok": rc == 0, "seconds": sec, "detail": out.splitlines()[-1] if out else f"rc={rc}"}


def check_skill_links() -> dict:
    rc, out, sec = _run([
        sys.executable, str(ROOT / "tooling/check_skill_links.py"),
        "--skills-dir", ".agents/skills", "--review-triggers",
    ])
    m = re.search(r"(\d+)\s+errors;\s+(\d+)\s+advisory warnings", out)
    warn_count = int(m.group(2)) if m else 0
    ok = (rc == 0) and (warn_count == 0)
    return {"name": "skill_links", "ok": ok, "seconds": sec, "detail": out.splitlines()[-1] if out else f"rc={rc}"}


def check_anti_bloat() -> dict:
    rc, out, sec = _run([sys.executable, str(ROOT / "tooling/check_anti_bloat.py")])
    passed = False
    detail = out.splitlines()[-1] if out else f"rc={rc}"
    try:
        j = json.loads(out)
        passed = bool(j.get("passed"))
        detail = f"passed={passed}, checked_files={j.get('checked_files')}, violations={len(j.get('violations', []))}"
    except Exception:
        passed = (rc == 0)
    return {"name": "anti_bloat", "ok": passed, "seconds": sec, "detail": detail}


def check_ai_env() -> dict:
    if not AI_ENV_AUDIT_PS1.exists():
        return {"name": "ai_environment", "ok": True, "seconds": 0.0, "detail": "SKIPPED (global audit script not found)"}
    rc, out, sec = _run([
        "powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
        "-File", str(AI_ENV_AUDIT_PS1), "-Force",
    ])
    err_m = re.search(r"errors\s*[=:]\s*(\d+)", out, re.I)
    warn_m = re.search(r"warnings\s*[=:]\s*(\d+)", out, re.I)
    errs = int(err_m.group(1)) if err_m else (0 if rc == 0 else 1)
    warns = int(warn_m.group(1)) if warn_m else 0
    ok = (rc == 0) and (errs == 0) and (warns == 0)
    return {"name": "ai_environment", "ok": ok, "seconds": sec, "detail": f"rc={rc}, errors={errs}, warnings={warns}"}


def check_pytest(mode: str) -> dict:
    if mode == "fast":
        targets = [
            "tooling/ai-engines/tests/test_quant_factory_suite.py",
            "tooling/ai-engines/tests/test_pass27_suite.py",
            "tooling/ai-engines/tests/test_pass28_suite.py",
        ]
        cmd = [sys.executable, "-m", "pytest", "-n", "4", "-q", *targets]
    else:
        cmd = [sys.executable, "-m", "pytest", "-n", "6", "-q", "tooling/ai-engines/tests"]
    rc, out, sec = _run(cmd, timeout=240)
    summary = out.splitlines()[-1] if out else f"rc={rc}"
    return {"name": f"pytest_{mode}", "ok": rc == 0, "seconds": sec, "detail": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Naqex Quant Factory System Doctor")
    parser.add_argument("--mode", choices=("fast", "full"), default="fast")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--skip-anti-bloat", action="store_true")
    args = parser.parse_args()

    t0 = time.perf_counter()
    results = [
        check_holdout_lock(),
        check_index_bloat(),
        check_exports_static_audit(),
        check_derived_cache(),
        check_workspace_contracts(),
        check_skill_links(),
    ]
    if not args.skip_anti_bloat:
        results.append(check_anti_bloat())
    if args.mode == "full":
        results.append(check_ai_env())
    results.append(check_pytest(args.mode))

    all_ok = all(r["ok"] for r in results)
    report = {
        "mode": args.mode,
        "all_ok": all_ok,
        "total_seconds": round(time.perf_counter() - t0, 2),
        "checks": results,
    }
    if args.as_json:
        print(json.dumps(report, indent=2, ensure_ascii=False))
    else:
        print(f"Naqex System Doctor [{args.mode.upper()}] — {'PASS' if all_ok else 'FAIL'} ({report['total_seconds']}s)")
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            print(f"  [{tag}] {r['name']:<22} ({r['seconds']:>5.2f}s) | {r['detail']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
