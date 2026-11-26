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
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TOOLING_DIR = ROOT / "tooling"
AI_ENGINES = ROOT / "tooling/ai-engines"
AI_ENGINES_LEGACY = AI_ENGINES / "legacy"
FOUNDATION_SRC = ROOT / "projects/trader/foundation_v2"
QUANT_TRADING_SRC = ROOT / "projects/quant-trading/src"

for _path in (AI_ENGINES, AI_ENGINES_LEGACY, FOUNDATION_SRC, QUANT_TRADING_SRC, TOOLING_DIR):
    if _path.exists() and str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

README_BYTE_BUDGET = 15_000
README_HARD_CEILING_BYTES = 50_000
CURRENT_CONTEXT_BYTE_BUDGET = 12_000

ALL_WORKSPACE_TESTPATHS: tuple[str, ...] = (
    "tooling/ai-engines/tests",
    "tooling/tests",
    "tooling/github-workflow/tests",
    "tooling/agent-workflow/tests",
    "tooling/run_registry/tests",
)

FAST_PYTEST_SHARDS: tuple[tuple[str, ...], ...] = (
    ("tooling/ai-engines/tests/test_holdout_and_tca_guards.py",),
    ("tooling/ai-engines/tests/test_quant_factory_suite.py",),
    (
        "tooling/ai-engines/tests/test_pass27_suite.py",
        "tooling/ai-engines/tests/test_pass28_suite.py",
    ),
    ("tooling/ai-engines/tests/test_layer1_opsec_guard.py",),
)


def _resolve_ai_env_audit_ps1() -> Path:
    env_override = os.environ.get("NAQEX_AI_ENV_AUDIT_PS1", "").strip()
    if env_override:
        return Path(env_override)
    home = Path.home()
    candidates = (
        home
        / ".gemini/config/plugins/migrated-settings/skills/ai-environment-maintainer/scripts/audit-ai-environment.ps1",
        home / ".agents/skills/ai-environment-maintainer/scripts/audit-ai-environment.ps1",
    )
    for cand in candidates:
        if cand.exists():
            return cand
    return candidates[0]


AI_ENV_AUDIT_PS1 = _resolve_ai_env_audit_ps1()


def _subproc_env() -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [
        str(AI_ENGINES),
        str(AI_ENGINES_LEGACY),
        str(FOUNDATION_SRC),
        str(QUANT_TRADING_SRC),
    ] + ([existing] if existing else [])
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    winget_links = Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/WinGet/Links"
    if winget_links.is_dir() and str(winget_links).lower() not in env.get("PATH", "").lower():
        env["PATH"] = f"{winget_links}{os.pathsep}{env.get('PATH', '')}"
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
    errors: list[str] = []
    warnings: list[str] = []
    readme = ROOT / "planning/research/README.md"
    ctx = ROOT / "planning/CURRENT-CONTEXT.md"
    readme_lines = len(readme.read_text(encoding="utf-8").splitlines()) if readme.exists() else -1
    readme_bytes = readme.stat().st_size if readme.exists() else -1
    ctx_bytes = ctx.stat().st_size if ctx.exists() else -1

    if readme_lines > 150:
        errors.append(f"planning/research/README.md too long ({readme_lines} > 150 lines)")
    if readme_bytes > README_HARD_CEILING_BYTES:
        errors.append(
            f"planning/research/README.md byte bloat critical ({readme_bytes} > {README_HARD_CEILING_BYTES} B)"
        )
    elif readme_bytes > README_BYTE_BUDGET:
        warnings.append(f"README={readme_bytes}B > {README_BYTE_BUDGET}B budget (advisory until Wave 2 compaction)")
    if ctx_bytes > CURRENT_CONTEXT_BYTE_BUDGET:
        errors.append(f"planning/CURRENT-CONTEXT.md too large ({ctx_bytes} > {CURRENT_CONTEXT_BYTE_BUDGET} B)")

    oversized = []
    # Check branch-touched or untracked files in planning/research/ (< 900 KB keeps headroom below 1 MiB wall)
    rc_d, diff_out, _ = _run(["git", "diff", "--name-only", "origin/main"])
    rc_u, untr_out, _ = _run(["git", "ls-files", "--others", "--exclude-standard", "planning/research"])
    candidates = set()
    if rc_d == 0:
        candidates.update(
            line.strip() for line in diff_out.splitlines() if line.strip().startswith("planning/research/")
        )
    if rc_u == 0:
        candidates.update(line.strip() for line in untr_out.splitlines() if line.strip())
    for rel in sorted(candidates):
        p = ROOT / rel
        if p.is_file() and p.stat().st_size > 900_000:
            oversized.append(f"{p.name} ({p.stat().st_size // 1024} KB)")
    if oversized:
        errors.append(f"Branch files > 900 KB in planning/research/: {', '.join(oversized)}")

    base_detail = f"README={readme_lines}L/{readme_bytes}B, CURRENT-CONTEXT={ctx_bytes}B, 0 branch files > 900KB"
    if errors:
        detail = "; ".join(errors)
    elif warnings:
        detail = f"{base_detail} | WARN: {'; '.join(warnings)}"
    else:
        detail = base_detail
    return {
        "name": "index_bloat",
        "ok": not errors,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": detail,
        "warnings": warnings,
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
    detail = f"{len(files)} MQL5 files audited: 0 red flags, DryRun default ON" if not errors else "; ".join(errors)
    return {
        "name": "exports_static_audit",
        "ok": not errors and len(files) >= 9,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": detail,
    }


def _resolve_tapes_binding(lock_sha: str, reg_sha: str) -> tuple[str, str, str]:
    """Use `quant_factory.data_store.compute_tapes_binding` when available; fall back cleanly to v1."""
    try:
        from quant_factory import data_store as ds

        helper = getattr(ds, "compute_tapes_binding", None)
        if callable(helper):
            res = helper(lock_sha, reg_sha)
            if isinstance(res, tuple) and len(res) >= 2:
                return str(res[0]), str(res[1]), "data_store"
            if isinstance(res, dict):
                binding = str(res.get("binding_sha256") or res.get("binding") or "")
                stem = str(res.get("stem") or "frozen_9e_tapes_v2")
                if binding:
                    return binding, stem, "data_store"
            elif isinstance(res, str) and res:
                return res, "frozen_9e_tapes_v2", "data_store"
    except Exception:
        pass
    legacy_binding = hashlib.sha256(f"{lock_sha}|{reg_sha}|v1".encode()).hexdigest()
    return legacy_binding, "frozen_9e_tapes_v1", "legacy_v1_fallback"


def check_derived_cache() -> dict:
    """Fast cryptographic SHA-256 verification of derived NPZ tape cache."""
    t0 = time.perf_counter()
    lock_path = ROOT / "planning/research/NATIVE_FTMO_HOLDOUT_LOCK.json"
    reg_path = ROOT / "planning/research/PORTFOLIO-REGISTRY.json"
    derived_dir = ROOT / ".runtime/hot-m1-cache/_derived"
    lock_sha = hashlib.sha256(lock_path.read_bytes()).hexdigest()
    reg = json.loads(reg_path.read_text(encoding="utf-8"))
    reg_sha = hashlib.sha256(json.dumps(reg.get("engines", []), sort_keys=True).encode("utf-8")).hexdigest()

    binding, stem, source = _resolve_tapes_binding(lock_sha, reg_sha)
    meta_path = derived_dir / f"{stem}.json"
    npz_path = derived_dir / f"{stem}.npz"
    if not (meta_path.exists() and npz_path.exists()):
        return {
            "name": "derived_cache",
            "ok": True,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"COLD ({stem} not yet warmed [{source}]; run quant_factory.build_or_load_frozen_tapes() once)",
        }
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    with npz_path.open("rb") as fh:
        npz_sha = hashlib.file_digest(fh, "sha256").hexdigest()
    n_eng = len(meta.get("tapes", {}))
    ok = meta.get("binding_sha256") == binding and meta.get("npz_sha256") == npz_sha and n_eng == 9
    sz_mb = round((npz_path.stat().st_size + meta_path.stat().st_size) / (1024 * 1024), 2)
    return {
        "name": "derived_cache",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": (
            f"WARM HIT ({stem}, {sz_mb} MB, {n_eng} engines, sha-verified via {source})"
            if ok
            else f"STALE/INVALID binding or npz SHA for {stem} ({source})"
        ),
    }


def check_brain_index() -> dict:
    """Verify Owner Knowledge Vault & local SQLite/Vector Brain index health (<0.05s)."""
    t0 = time.perf_counter()
    import sqlite3

    profile = ROOT / "knowledge/owner/PROFILE.md"
    db_path = ROOT / ".runtime/knowledge/brain.sqlite3"
    vec_path = ROOT / ".runtime/knowledge/brain_vec.npz"
    if not profile.exists():
        return {
            "name": "knowledge_brain",
            "ok": False,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": "Missing knowledge/owner/PROFILE.md",
        }
    if not (db_path.exists() and vec_path.exists()):
        return {
            "name": "knowledge_brain",
            "ok": True,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": "COLD (run tooling/knowledge/brain_cli.py index)",
        }
    con = sqlite3.connect(str(db_path))
    try:
        n_files = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        n_chunks = con.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
    finally:
        con.close()
    sz_mb = round((db_path.stat().st_size + vec_path.stat().st_size) / (1024 * 1024), 2)
    ok = n_files > 0 and n_chunks > 0
    return {
        "name": "knowledge_brain",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": f"READY ({n_files} files, {n_chunks} chunks, {sz_mb} MB)" if ok else "EMPTY index",
    }


def check_architecture() -> dict:
    """Run Harness Engineering architecture gate [ARCH-01..07].

    Before Wave 2 compacts `planning/research/README.md` to <= 15_000 B, runs in
    transition mode: hard-fails immediately on Wave-1-enforced rules (ARCH-03, ARCH-06,
    ARCH-07, and CURRENT-CONTEXT > 12KB) while reporting pending Wave-2 items as advisory.
    Once README <= 15_000 B, enforces full `--strict` 0-error compliance across all 7 rules.
    """
    t0 = time.perf_counter()
    import check_architecture as arch

    readme = ROOT / "planning/research/README.md"
    readme_bytes = readme.stat().st_size if readme.is_file() else 0
    strict_mode = readme_bytes <= README_BYTE_BUDGET
    report = arch.run_architecture_audit(ROOT, strict=strict_mode)
    by_rule = report["by_rule"]

    if strict_mode:
        ok = bool(report["passed"])
        if ok:
            detail = "STRICT PASS (0 errors across [ARCH-01..07])"
        else:
            nonzero = ", ".join(f"{k}={v}" for k, v in by_rule.items() if v)
            detail = f"STRICT FAIL ({report['error_count']} errors: {nonzero})"
        return {
            "name": "check_architecture",
            "ok": ok,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": detail,
        }

    hard_errors = [
        err
        for err in report["errors"]
        if err["rule"] in ("ARCH-01", "ARCH-03", "ARCH-06", "ARCH-07")
        or (err["rule"] == "ARCH-05" and err["file"].endswith("CURRENT-CONTEXT.md"))
    ]
    pending_counts = {k: v for k, v in by_rule.items() if v and k in ("ARCH-02", "ARCH-04", "ARCH-05")}
    ok = len(hard_errors) == 0
    if not ok:
        hard_summary = "; ".join(f"[{e['rule']}] {e['file']}:{e['line']}" for e in hard_errors[:5])
        detail = f"FAIL ({len(hard_errors)} hard violations: {hard_summary})"
    elif pending_counts:
        pending_str = ", ".join(f"{k}={v}" for k, v in sorted(pending_counts.items()))
        detail = f"ADVISORY (pre-Wave-2 README={readme_bytes}B>15KB; 0 hard fails; pending: {pending_str})"
    else:
        detail = "PASS (0 violations across [ARCH-01..07])"
    return {
        "name": "check_architecture",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": detail,
    }


def check_workspace_contracts() -> dict:
    """In-process workspace contracts audit (guides + submodule topology)."""
    t0 = time.perf_counter()
    import check_workspace as cw

    errors: list[str] = []
    for name in cw.GUIDES:
        errors.extend(cw.check_links(ROOT, ROOT / name))
    rc, index_out, _ = _run(["git", "-C", str(ROOT), "ls-files", "--stage"])
    if rc != 0:
        errors.append(f"git ls-files --stage failed (rc={rc})")
    else:
        errors.extend(cw.check_topology((ROOT / ".gitmodules").read_text(encoding="utf-8"), index_out))
    ok = not errors
    detail = (
        f"Workspace contracts passed: {len(cw.GUIDES)} guides, {len(cw.PRODUCTS)} pinned submodules."
        if ok
        else "; ".join(errors[:5])
    )
    return {
        "name": "workspace_contracts",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": detail,
    }


def check_skill_links() -> dict:
    """In-process skill links & negative-trigger audit."""
    t0 = time.perf_counter()
    import check_skill_links as csl

    errors, warnings, count = csl.audit(ROOT, [Path(".agents/skills")], review_triggers=True)
    ok = len(errors) == 0 and len(warnings) == 0
    detail = f"Skill links: {count} skills; {len(errors)} errors; {len(warnings)} advisory warnings."
    return {
        "name": "skill_links",
        "ok": ok,
        "seconds": round(time.perf_counter() - t0, 3),
        "detail": detail,
    }


def check_anti_bloat() -> dict:
    """In-process anti-bloat check on changed raw JSON/CSV artifacts."""
    t0 = time.perf_counter()
    import check_anti_bloat as cab

    rc, records = cab.collect_changed_records("origin/main", root=ROOT)
    if rc != 0:
        return {
            "name": "anti_bloat",
            "ok": False,
            "seconds": round(time.perf_counter() - t0, 3),
            "detail": f"git diff failed (rc={rc})",
        }
    j = cab.evaluate(records)
    passed = bool(j.get("passed"))
    detail = f"passed={passed}, raw_files={j.get('raw_files')}, failures={len(j.get('failures', []))}"
    return {"name": "anti_bloat", "ok": passed, "seconds": round(time.perf_counter() - t0, 3), "detail": detail}


def check_ai_env() -> dict:
    if not AI_ENV_AUDIT_PS1.exists():
        return {
            "name": "ai_environment",
            "ok": True,
            "seconds": 0.0,
            "detail": "SKIPPED (global audit script not found)",
        }
    rc, out, sec = _run(
        [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(AI_ENV_AUDIT_PS1),
            "-Force",
        ]
    )
    err_m = re.search(r"errors\s*[=:]\s*(\d+)", out, re.I)
    warn_m = re.search(r"warnings\s*[=:]\s*(\d+)", out, re.I)
    errs = int(err_m.group(1)) if err_m else (0 if rc == 0 else 1)
    warns = int(warn_m.group(1)) if warn_m else 0
    ok = (rc == 0) and (errs == 0) and (warns == 0)
    return {"name": "ai_environment", "ok": ok, "seconds": sec, "detail": f"rc={rc}, errors={errs}, warnings={warns}"}


def _run_pytest_shard(idx: int, targets: tuple[str, ...]) -> tuple[int, str, float]:
    cmd = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "-p",
        "no:xdist",
        "-p",
        "no:hypothesispytest",
        "-p",
        "no:anyio",
        "-p",
        "no:cacheprovider",
        "--no-header",
        "-q",
        *targets,
    ]
    return _run(cmd, timeout=180)


def check_pytest(mode: str, *, ci_offline: bool = False) -> dict:
    t0 = time.perf_counter()
    if mode == "fast":
        with ThreadPoolExecutor(max_workers=len(FAST_PYTEST_SHARDS)) as pool:
            futs = [pool.submit(_run_pytest_shard, idx, shard) for idx, shard in enumerate(FAST_PYTEST_SHARDS)]
            shard_results = [f.result() for f in futs]
        all_ok = all(rc == 0 for rc, _, _ in shard_results)
        total_passed = 0
        failures: list[str] = []
        for idx, (rc, out, _) in enumerate(shard_results):
            last_line = out.splitlines()[-1] if out else f"rc={rc}"
            m = re.search(r"(\d+)\s+passed", last_line)
            if m:
                total_passed += int(m.group(1))
            if rc != 0:
                failures.append(f"shard{idx}: {last_line}")
        elapsed = round(time.perf_counter() - t0, 2)
        summary = (
            f"{total_passed} passed across {len(FAST_PYTEST_SHARDS)} parallel shards in {elapsed:.2f}s"
            if all_ok
            else "; ".join(failures)
        )
        return {"name": "pytest_fast", "ok": all_ok, "seconds": elapsed, "detail": summary}

    cmd = [
        sys.executable,
        "-X",
        "utf8",
        "-m",
        "pytest",
        "-n",
        "auto",
        "--dist",
        "worksteal",
        "-o",
        "cache_dir=.tmp/pytest-doctor-full",
        "-q",
    ]
    if ci_offline:
        cmd.extend(["-m", "not local_cache"])
    cmd.extend(ALL_WORKSPACE_TESTPATHS)
    rc, out, sec = _run(cmd, timeout=360)
    summary = out.splitlines()[-1] if out else f"rc={rc}"
    return {"name": "pytest_full", "ok": rc == 0, "seconds": sec, "detail": summary}


def main() -> int:
    parser = argparse.ArgumentParser(description="Naqex Quant Factory System Doctor")
    parser.add_argument("--mode", choices=("fast", "full"), default="fast")
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument("--skip-anti-bloat", action="store_true")
    parser.add_argument(
        "--ci-offline", action="store_true", help="In full mode, exclude @pytest.mark.local_cache tests"
    )
    args = parser.parse_args()

    t0 = time.perf_counter()
    # Submit pytest first so the slowest parallel check starts at t=0.00s.
    tasks = [
        ("pytest", lambda: check_pytest(args.mode, ci_offline=args.ci_offline)),
        ("holdout_lock", check_holdout_lock),
        ("index_bloat", check_index_bloat),
        ("exports_static_audit", check_exports_static_audit),
        ("derived_cache", check_derived_cache),
        ("knowledge_brain", check_brain_index),
        ("workspace_contracts", check_workspace_contracts),
        ("skill_links", check_skill_links),
        ("check_architecture", check_architecture),
    ]
    if not args.skip_anti_bloat:
        tasks.append(("anti_bloat", check_anti_bloat))
    if args.mode == "full":
        tasks.append(("ai_environment", check_ai_env))

    with ThreadPoolExecutor(max_workers=min(10, len(tasks))) as pool:
        futures = [(name, pool.submit(fn)) for name, fn in tasks]
        by_name = {name: fut.result() for name, fut in futures}

    display_order = [
        "holdout_lock",
        "index_bloat",
        "exports_static_audit",
        "derived_cache",
        "knowledge_brain",
        "workspace_contracts",
        "skill_links",
        "check_architecture",
    ]
    if not args.skip_anti_bloat:
        display_order.append("anti_bloat")
    if args.mode == "full":
        display_order.append("ai_environment")
    display_order.append("pytest")
    results = [by_name[name] for name in display_order]

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
        print(
            f"Naqex System Doctor [{args.mode.upper()}] — {'PASS' if all_ok else 'FAIL'} ({report['total_seconds']}s)"
        )
        for r in results:
            tag = "PASS" if r["ok"] else "FAIL"
            print(f"  [{tag}] {r['name']:<22} ({r['seconds']:>5.2f}s) | {r['detail']}")
    return 0 if all_ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
