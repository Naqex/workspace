"""Windows-native unified command runner for Naqex TradingWorkspace.

Replaces external task-runner dependencies (such as `just`) with a zero-dependency
Python CLI that automatically resolves the bundled `.runtime/quant-audit-v24`
interpreter and canonical `PYTHONPATH`.

Subcommands:
  doctor       Run System Doctor (`--mode fast|full`)
  test-fast    Run fast local regression pytest suite
  test-full    Run full workspace pytest suite across all 5 testpaths
  audit-arch   Run Harness Engineering architecture gate (`check_architecture.py`)
  brain-index  Incremental re-index of the local Knowledge Brain
  worktree     Manage isolated `.worktrees/<name>` checkouts (`worktree_ctl.py`)
  route        Invoke 3-node compute router (`compute_router.py`)
  opsec        Run Layer-1 OPSEC guard (+ optional local Gitleaks scan)
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUNDLED_PY = ROOT / ".runtime/quant-audit-v24/Scripts/python.exe"
LOCAL_GITLEAKS = ROOT / ".runtime/tools/gitleaks/gitleaks.exe"

CANONICAL_PYTHONPATH: tuple[str, ...] = (
    "tooling/ai-engines",
    "tooling/ai-engines/legacy",
    "projects/trader/foundation_v2",
    "projects/quant-trading/src",
)

FAST_TEST_TARGETS: tuple[str, ...] = (
    "tooling/tests/test_check_architecture.py",
    "tooling/ai-engines/tests/test_layer1_opsec_guard.py",
    "tooling/ai-engines/tests/test_holdout_and_tca_guards.py",
    "tooling/ai-engines/tests/test_quant_factory_suite.py",
    "tooling/ai-engines/tests/test_pass27_suite.py",
    "tooling/ai-engines/tests/test_pass28_suite.py",
)

ALL_TESTPATHS: tuple[str, ...] = (
    "tooling/ai-engines/tests",
    "tooling/tests",
    "tooling/github-workflow/tests",
    "tooling/agent-workflow/tests",
    "tooling/run_registry/tests",
)


def resolve_python(root: Path = ROOT) -> str:
    bundled = root / ".runtime/quant-audit-v24/Scripts/python.exe"
    if bundled.is_file():
        return str(bundled)
    return sys.executable


def build_env(root: Path = ROOT) -> dict[str, str]:
    env = os.environ.copy()
    existing = env.get("PYTHONPATH", "")
    parts = [str(root / rel) for rel in CANONICAL_PYTHONPATH]
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    env["PYTHONUTF8"] = "1"
    return env


def _exec(cmd: list[str], *, root: Path = ROOT, dry_run: bool = False) -> int:
    if dry_run:
        print("DRY-RUN:", " ".join(cmd))
        return 0
    proc = subprocess.run(cmd, cwd=str(root), env=build_env(root), check=False)
    return int(proc.returncode)


def build_command(args: argparse.Namespace, extra: list[str], *, root: Path = ROOT) -> list[str]:
    py = resolve_python(root)
    cmd_name = args.command

    if cmd_name == "doctor":
        cmd = [py, "-X", "utf8", str(root / "tooling/ai-engines/system_doctor.py"), "--mode", args.mode]
        if args.as_json:
            cmd.append("--json")
        if args.skip_anti_bloat:
            cmd.append("--skip-anti-bloat")
        return cmd + extra

    if cmd_name == "test-fast":
        cmd = [py, "-X", "utf8", "-m", "pytest"]
        if args.workers and args.workers > 1:
            cmd.extend(["-n", str(args.workers), "--dist", "worksteal"])
        cmd.extend(["-o", f"cache_dir={args.cache_dir}", "-q", *FAST_TEST_TARGETS])
        return cmd + extra

    if cmd_name == "test-full":
        cmd = [
            py,
            "-X",
            "utf8",
            "-m",
            "pytest",
            "-n",
            str(args.workers),
            "--dist",
            "worksteal",
            "-o",
            f"cache_dir={args.cache_dir}",
            "-q",
        ]
        if not args.include_local_cache:
            cmd.extend(["-m", "not local_cache"])
        cmd.extend(ALL_TESTPATHS)
        return cmd + extra

    if cmd_name == "audit-arch":
        cmd = [py, "-X", "utf8", str(root / "tooling/check_architecture.py")]
        if args.strict:
            cmd.append("--strict")
        if args.as_json:
            cmd.append("--json")
        return cmd + extra

    if cmd_name == "brain-index":
        cmd = [py, "-X", "utf8", str(root / "tooling/knowledge/brain_cli.py"), "index"]
        if args.full:
            cmd.append("--full")
        return cmd + extra

    if cmd_name == "worktree":
        return [py, "-X", "utf8", str(root / "tooling/worktree_ctl.py"), *extra]

    if cmd_name == "route":
        router_path = root / "tooling/ai-engines/ops_cloud/compute_router.py"
        if not router_path.is_file():
            raise FileNotFoundError(
                f"Compute router not found at {router_path} (expected from Wave 1 L5 perf-compute-brain)."
            )
        return [py, "-X", "utf8", str(router_path), *extra]

    if cmd_name == "opsec":
        return [
            py,
            "-X",
            "utf8",
            "-m",
            "pytest",
            "-o",
            f"cache_dir={args.cache_dir}",
            "-q",
            "tooling/ai-engines/tests/test_layer1_opsec_guard.py",
            *extra,
        ]

    if cmd_name == "ruff":
        return [py, "-X", "utf8", "-m", "ruff", *extra]

    raise ValueError(f"Unsupported command: {cmd_name}")


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="naqex_cli.py",
        description="Naqex TradingWorkspace unified Windows-native command runner.",
    )
    parser.add_argument("--root", type=Path, default=ROOT, help="Workspace root override")
    parser.add_argument("--dry-run", action="store_true", help="Print resolved command without executing")
    sub = parser.add_subparsers(dest="command", required=True)

    p_doc = sub.add_parser("doctor", help="Run System Doctor (--mode fast|full)")
    p_doc.add_argument("--mode", choices=("fast", "full"), default="fast")
    p_doc.add_argument("--json", action="store_true", dest="as_json")
    p_doc.add_argument("--skip-anti-bloat", action="store_true")

    p_tf = sub.add_parser("test-fast", help="Run fast core regression tests")
    p_tf.add_argument("--workers", type=int, default=1, help="Pytest xdist worker count (default: 1 for <3s startup)")
    p_tf.add_argument("--cache-dir", default=".tmp/pytest-fast")

    p_tfull = sub.add_parser("test-full", help="Run full offline pytest suite across all 5 testpaths")
    p_tfull.add_argument("--workers", default="auto", help="Pytest xdist worker count (default: auto)")
    p_tfull.add_argument("--include-local-cache", action="store_true", help="Include @pytest.mark.local_cache tests")
    p_tfull.add_argument("--cache-dir", default=".tmp/pytest-full")

    p_arch = sub.add_parser("audit-arch", help="Run Harness Engineering architecture rules [ARCH-01..07]")
    p_arch.add_argument("--strict", action="store_true", help="Treat advisory warnings (e.g. README > 15KB) as errors")
    p_arch.add_argument("--json", action="store_true", dest="as_json")

    p_brain = sub.add_parser("brain-index", help="Run Knowledge Brain indexer")
    p_brain.add_argument("--full", action="store_true", help="Force full re-index")

    sub.add_parser("worktree", help="Delegate to tooling/worktree_ctl.py (list|create|remove|prune)")
    sub.add_parser("route", help="Delegate to tooling/ai-engines/ops_cloud/compute_router.py")

    p_opsec = sub.add_parser("opsec", help="Run Layer-1 OPSEC guard (+ optional --gitleaks)")
    p_opsec.add_argument("--gitleaks", action="store_true", help="Also run bundled local gitleaks on HEAD")
    p_opsec.add_argument("--cache-dir", default=".tmp/pytest-opsec")

    sub.add_parser("ruff", help="Run ruff via the workspace bundled Python environment (e.g. ruff check ...)")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = make_parser()
    args, extra = parser.parse_known_args(argv)
    root = args.root.resolve()

    try:
        cmd = build_command(args, extra, root=root)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    rc = _exec(cmd, root=root, dry_run=args.dry_run)
    if rc != 0:
        return rc

    if args.command == "opsec" and getattr(args, "gitleaks", False):
        gitleaks_exe = root / ".runtime/tools/gitleaks/gitleaks.exe"
        if not gitleaks_exe.is_file():
            print(f"WARNING: local gitleaks binary not found at {gitleaks_exe}", file=sys.stderr)
            return 1
        return _exec(
            [str(gitleaks_exe), "git", "--redact", "--no-banner", "--log-opts", "HEAD"],
            root=root,
            dry_run=args.dry_run,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
